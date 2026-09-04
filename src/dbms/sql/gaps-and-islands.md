# Gaps and Islands: Streaks, Sessions, and Interval Merging in SQL

Gaps-and-islands is the family of problems where rows form runs — consecutive
login days, events within 30 minutes, prices that stay flat, machines that
stay down — and the query must collapse each run into one row or measure it.
Every encoding is the same two-step trick (find where a run starts; number the
runs), and every interview variant — streaks, sessionization, free-slot
finding, deduplication, interval merging — is that trick in disguise.

Window-function prerequisites are in [Window Functions](./window-functions.md);
the analytical-product angle (cohorts, funnels) is in
[Cohort Analysis](../../data-engineering/cohort-analysis.md).

## The core trick: start-of-group + running sum

Given ordered rows and a predicate "new run starts here," materialize a flag,
then accumulate it. The cumulative sum is **constant on every row of the same
run**, which turns an unbounded run into an ordinary GROUP BY key.

```sql
-- Classic: longest streak of consecutive days per user
WITH d AS (
  SELECT user_id, event_date::date AS day
  FROM logins
  GROUP BY user_id, event_date::date          -- dedupe same-day logins
),
flagged AS (
  SELECT user_id, day,
         CASE WHEN day = lag(day) OVER w + INTERVAL '1 day'
              THEN 0 ELSE 1 END AS is_start
  FROM d
  WINDOW w AS (PARTITION BY user_id ORDER BY day)
),
islands AS (
  SELECT user_id, day,
         sum(is_start) OVER (PARTITION BY user_id ORDER BY day) AS grp
  FROM flagged
)
SELECT user_id, count(*) AS streak_len, min(day), max(day)
FROM islands
GROUP BY user_id, grp;
```

Why it works: `is_start = 1` exactly on each run's first row, so the running
sum increases by one per run — every row inside run *k* gets `grp = k`.
The pattern is pure math on orderings: no self-joins, no recursion, one sort.

**The date-arithmetic variant** deserves memorization because it appears when
`LAG` is unavailable or too clever for the audience: for *gaps of exactly one
unit* (consecutive days, consecutive integers), `day - ROW_NUMBER()` is
constant within an island, because both advance by 1 per row inside a run and
diverge by 2 across a gap:

```sql
SELECT user_id, min(day), max(day)
FROM (SELECT user_id, day,
             day - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) AS grp
      FROM logins) x
GROUP BY user_id, grp;
```

It fails the moment gaps are *variable* ("within 30 minutes") — then only the
flag-and-accumulate form applies. Knowing which variant fits which gap
definition is a real interview discriminator.

## Sessionization: gaps defined by inactivity

A session is a maximal run of events where consecutive events are within
θ (typically 30 minutes). Same trick, threshold predicate instead of
equality:

```sql
WITH t AS (
  SELECT user_id, event_ts,
         lag(event_ts) OVER (PARTITION BY user_id ORDER BY event_ts) AS prev_ts
  FROM events
),
marked AS (
  SELECT user_id, event_ts,
         CASE WHEN event_ts - prev_ts <= interval '30 minutes'
              THEN 0 ELSE 1 END AS is_start
  FROM t
),
sessions AS (
  SELECT user_id, event_ts,
         sum(is_start) OVER (PARTITION BY user_id ORDER BY event_ts) AS session_no
  FROM marked
)
SELECT user_id,
       session_no,
       min(event_ts) AS started_at,
       max(event_ts) AS last_event,
       count(*)      AS events,
       max(event_ts) - min(event_ts) AS duration
FROM sessions
GROUP BY user_id, session_no;
```

Notes that separate a senior answer from a junior one:

- **Sessions can merge retroactively.** Stream processors (Flink
  *session windows*, Spark Structured Streaming *session windows*) keep the
  last session per key open and *merge* windows when a late event bridges the
  gap; the batch SQL above is "final view" only. Discussing why streaming
  session windows must re-emit merged windows (they are data-driven, not
  time-sliced like tumbling windows) shows systems depth — see
  [Stream Processing](../../data-engineering/stream-processing.md).
- **Tie handling.** Two events at the same timestamp: `ORDER BY event_ts` is
  non-deterministic; add a tiebreaker column (`event_id`) or the session
  boundaries become unstable between runs.
- **Timezone and clock skew.** Client timestamps arriving out of order across
  the θ boundary flip sessions; production pipelines order by server-side
  ingestion time or use watermarks.

## The other islands: from start/end events, not predicates

When runs are given as *state intervals* — machine down/up events, price
changes, user flags — the "start" is not derivable from comparing neighbors;
you need the **current state** and its running count of flips:

```sql
-- Merge overlapping maintenance windows [start, end) into islands
WITH bounds AS (
  SELECT machine_id, ts, kind,
         sum(CASE WHEN kind = 'down' THEN 1 ELSE -1 END) OVER (
             PARTITION BY machine_id ORDER BY ts, kind) AS depth
  FROM maintenance_events
),
edge AS (
  SELECT machine_id, ts, kind, depth,
         lag(depth) OVER (PARTITION BY machine_id ORDER BY ts) AS prev_depth
  FROM bounds
)
SELECT machine_id, min(ts) FILTER (WHERE kind = 'down' AND depth = 1) AS down_at,
       max(ts) FILTER (WHERE kind = 'up'   AND depth = 0) AS up_at
FROM edge
GROUP BY machine_id, depth;
```

The `depth` counter (net open intervals) plus `FILTER` aggregates isolate the
entering and leaving edges of each merged island — this is **interval
union** done in SQL, and it correctly handles nested intervals
(depth goes 1, 2, 1, 0) that break the naive "merge with previous row"
approach. The full temporal toolkit (overlap predicates, exclusion
constraints, half-open interval discipline) is in
[Temporal SQL Patterns](./temporal-sql-patterns.md).

## Free-slot finding: islands of the complement

"Find free meeting slots ≥ 30 minutes in [09:00, 18:00]" is the *complement*
islands problem: first build the booked islands, then `LEAD` the gaps:

```sql
WITH booked AS (
  SELECT ts AS s, end_ts AS e FROM meetings
),
gaps AS (
  SELECT e AS gap_start,
         lead(s) OVER (ORDER BY s) AS gap_end
  FROM booked
)
SELECT gap_start, gap_end, gap_end - gap_start AS free
FROM gaps
WHERE gap_end - gap_start >= interval '30 minutes'
UNION ALL
SELECT interval '09:00', min(s), min(s) - interval '09:00' FROM booked   -- head gap
UNION ALL
SELECT max(e), interval '18:00', interval '18:00' - max(e) FROM booked;  -- tail gap
```

The head/tail gaps are exactly the rows a `LEAD`-only solution silently loses
— a textbook [interview trap](../../failure-modes/common-failures.md)
in miniature: boundary cases are where interval SQL breaks.

## Performance: what the plan does and when to avoid the pattern

All encodings require the window sort: `O(N log N)` CPU plus a sort spill
risk on large partitions (see the sort/spool discussion in
[Execution Plans](../query-processing/execution-plans.md)). Practical
guidance:

- **Sort once, reuse.** Multiple window functions over the same
  `PARTITION BY/ORDER BY` share one sort; mixing orderings re-sorts. Keep the
  frame default (`RANGE UNBOUNDED PRECEDING..CURRENT ROW`) or force `ROWS` —
  `RANGE` frames on ties can force extra buffering in some engines
  (details in [Window Functions](./window-functions.md)).
- **Reduce before windowing.** Deduplicate (`GROUP BY user_id, day`) and
  filter before the window step: window cost scales with *rows*, and raw
  event tables are the widest input you have.
- **Recursive CTEs are the wrong tool** for streaks — they give one row per
  recursive step (`O(N)` context switches) and lose to the single sort + scan
  by an order of magnitude. Recursion earns its keep on *graph* traversal
  (see [Hierarchical Queries](./hierarchical-queries.md)), not on ordered
  runs.
- **When data is huge, don't do it in SQL at all.** Sessionization over
  billions of events is embarrassingly parallel after partitioning by
  `user_id`; a map-side hash keyed by user with a small state machine
  (or a streaming session window) beats a global sort. Knowing the SQL form
  *and* the scale at which to abandon it is the complete answer.

## Key Takeaways

- Every gaps-and-islands problem reduces to: flag run starts → running-sum a
  stable group key → aggregate per island.
- `day - ROW_NUMBER()` handles only fixed-size gaps; flag-and-accumulate
  handles any "within θ" predicate.
- Same-timestamp ties and boundary gaps (head/tail) are where correct-looking
  queries go wrong; session *merging* in streaming engines exists precisely
  because batch SQL computes only the final view.
- Interval-union via net-depth counters handles nested intervals that
  neighbor-comparison misses; window sorts dominate cost — reduce before
  windowing, and hand off to stream processors at real scale.

## Cross-References

- [Window Functions](./window-functions.md) — LAG/LEAD, frames, sort-sharing semantics.
- [Temporal SQL Patterns](./temporal-sql-patterns.md) — overlap predicates, as-of joins, exclusion constraints.
- [Hierarchical Queries](./hierarchical-queries.md) — when recursion is the right tool instead.
- [Cohort Analysis](../../data-engineering/cohort-analysis.md) — retention analytics built on top of sessionization.
- [Stream Processing](../../data-engineering/stream-processing.md) — session windows as streaming state.

## References

- Itzik Ben-Gan, *Microsoft SQL Server 2012: High-Performance T-SQL Using Window Functions*, Microsoft Press, 2012 — the canonical treatment of gaps-and-islands, start-of-group technique, and frame semantics (Ben-Gan coined the "gaps and islands" framing in his SQL Server Magazine series).
- Itzik Ben-Gan, *T-SQL Querying*, Microsoft Press, 2015 — production-grade variants including sessionization and interval packing.
- PostgreSQL Documentation, "[Window Function Processing](https://www.postgresql.org/docs/current/tutorial-window.html)" and "[Window Functions](https://www.postgresql.org/docs/current/functions-window.html)" — evaluation order and frame rules.
- Apache Flink Documentation, "[Windows](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/operators/windows/)" — session windows with merging semantics for the streaming contrast.
- Apache Spark, "[Structured Streaming Programming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)" — session-window support and late-data handling.
