# Funnel Analysis and Event-Stream SQL

A funnel is an ordered, time-bounded sequence of steps ("land → view
product → add to cart → pay") measured per user; the analysis reports how
many users reach each step and where they drop. It looks like a simple
GROUP BY and is not: steps must occur **in order**, within an **attribution
window**, per **session or per user**, and event duplicates or out-of-order
timestamps silently inflate conversion. This page is the SQL toolkit — the
timestamp-comparison pattern, the engine-native funnels, and the exact
places the naive versions lie.

Companion pages: [Cohort Analysis](../../data-engineering/cohort-analysis.md)
(retention triangles — the funnel's sibling metric),
[Gaps and Islands](./gaps-and-islands.md) (sessionization prerequisite),
and [Window Function Problems](../interview-problems/window-function-problems.md)
(the interview-problem format).

## Defining the funnel precisely

Three parameters decide the answer, and disagreement about them is the
#1 reason two teams' "conversion rate" differs:

1. **Scope**: per user ever, per user per session, or per user per
   acquisition cohort. Session scoping needs sessionization first
   ([the 30-minute-gap technique](./gaps-and-islands.md)).
2. **Ordering**: strict (step k+1 must happen after step k) — always true
   for funnels — plus whether *interleaving* is allowed (step 2 before an
   earlier step-1 repeat? multiple step-2 events?). The standard: first
   qualifying occurrence of each step after the previous step's first
   qualifying occurrence.
3. **Window**: total attribution window from step 1 ("converts within 24h")
   or a per-step gap limit ("next step within 30 minutes"). These give
   different numbers, and mixing them is the classic subtle bug.

## The workhorse pattern: first-occurrence timestamps + chained comparisons

One scan, one aggregation, no self-joins — this is the pattern to internalize:

```sql
WITH steps AS (
  SELECT
    user_id, session_id, step_no, event_ts,
    -- first occurrence of each step inside the session
    min(event_ts) FILTER (WHERE step_no = 1) AS t1,
    min(event_ts) FILTER (WHERE step_no = 2) AS t2,
    min(event_ts) FILTER (WHERE step_no = 3) AS t3,
    min(event_ts) FILTER (WHERE step_no = 4) AS t4
  FROM funnel_events
  GROUP BY user_id, session_id
),
funnel AS (
  SELECT *,
    t1 IS NOT NULL
      AND t2 > t1 AND t2 <= t1 + interval '30 minutes' AS reached_2,
    t2 > t1
      AND t3 > t2 AND t3 <= t2 + interval '30 minutes' AS reached_3,
    t3 > t2
      AND t4 > t3 AND t4 <= t3 + interval '30 minutes' AS reached_4
  FROM steps
)
SELECT count(*)                                             AS entered,
       count(*) FILTER (WHERE reached_2)                    AS step2,
       count(*) FILTER (WHERE reached_3)                    AS step3,
       count(*) FILTER (WHERE reached_4)                    AS step4,
       round(100.0 * count(*) FILTER (WHERE reached_4) / count(*), 2) AS conv_pct
FROM funnel;
```

Why this shape wins:

- **`min(event_ts) FILTER (WHERE ...)`** collapses each step to one
  timestamp before any ordering logic runs — duplicates and repeated steps
  can no longer multiply rows (the
  [fan-out trap](../interview-problems/interview-traps.md) at funnel scale).
- **The chained predicate encodes both order and window** (`t2 > t1 AND
  t2 <= t1 + window`); each step's eligibility is relative to the previous
  *qualified* step, which is the definition, not an approximation.
- **One GROUP BY, then arithmetic** — the plan is scan → hash aggregate →
  filter, linear in events, and every drop-off percentage is derivable in
  the outer SELECT.

**The ordered-window subtlety:** the query above allows step 3 to occur
anywhere after step 2 within 30 minutes — but step 2's own timestamp is
fixed as its *first* occurrence. If a user's first step-2 event was
premature (page loaded in background), the funnel may under-credit them.
Strictly-correct per-step chaining is an *ordered search*, which is where
the recursive formulation below comes in.

## Strict ordered search: the recursive formulation

The GROUP-BY pattern anchors each step to its *first* occurrence, which is
the right 95% answer. The strictly-correct per-step walk ("next qualified
step after the previous qualified step") is a search, and its honest
portable expression is a recursive CTE — note what each recursion carries:

```sql
WITH RECURSIVE ordered AS (
  SELECT user_id, session_id, step_no AS target, event_ts
  FROM funnel_events
  WHERE step_no BETWEEN 1 AND 4
),
walk AS (
  -- anchor: the first step-1 event per session
  SELECT user_id, session_id, event_ts AS t, 1 AS depth
  FROM ordered WHERE target = 1
  UNION ALL
  -- step: the next event that is exactly the next step, within the window
  SELECT o.user_id, o.session_id, o.event_ts, w.depth + 1
  FROM ordered o
  JOIN walk w
    ON  o.user_id    = w.user_id
    AND o.session_id = w.session_id
    AND o.target     = w.depth + 1
    AND o.event_ts   >  w.t
    AND o.event_ts   <= w.t + interval '30 minutes'
)
SELECT user_id, session_id, max(depth) AS deepest_step
FROM walk
GROUP BY user_id, session_id;
```

It is correct and teachable, and also the slowest shape on the page —
per-session recursive walks defeat set-based execution, which is precisely
why warehouse engines ship native funnels instead. In an interview, show
the GROUP-BY pattern first, present this only when the "strict next-qualified-
step" semantics are demanded, and say the cost sentence.

## Engine-native funnels: ClickHouse `windowFunnel` and friends

```sql
-- ClickHouse: deepest consecutive step reached within a sliding window
SELECT
  windowFunnel(1800)(                        -- window in seconds
    toUInt32(event_ts),                      -- monotonically comparable time
    step_no = 1,
    step_no = 2,
    step_no = 3,
    step_no = 4
  ) AS depth,
  count() AS users
FROM funnel_events
GROUP BY user_id, session_id
HAVING depth > 0;
```

`windowFunnel` implements the ordered search natively: it returns the
largest `k` such that conditions 1..k fired in order within the sliding
window (see [ClickHouse parametric aggregate functions](https://clickhouse.com/docs/reference/functions/aggregate-functions/parametric-functions)).
The same family exists in analytics warehouses (e.g.,
[Pinot](../../data-engineering/pinot.md) and Druid funnel extensions,
Adobe/Amplitude-style products) because funnels over billions of events are
a warehouse workload first and an OLTP-side query second — the SQL pattern
above is for when you must express it portably.

## What silently corrupts funnels

| Corruption | Effect | Fix |
|---|---|---|
| Duplicate events (client retry) | Steps counted twice; conversion > 100% in per-step version | Dedup by event id, or aggregate first-occurrences before chaining |
| Unordered comparison (`t1 AND t2 AND t3`, no `>` chains) | Out-of-order events "convert" | Chain `t_{k+1} > t_k` — the comparison is the definition |
| No window | Same-session and next-week events both convert | Encode the attribution window per the metric's contract |
| Bot/employee traffic | Conversions that never were | Filter lists, second-level heuristics before the funnel |
| Timezone/day boundary bucketing | Same funnel, different daily numbers per team | Fix the bucketing rule (UTC vs local) next to the query |
| Session crossers (midnight) | Sessions split; funnel fragments | Sessionize on inactivity, not calendar days |

## From funnel to retention: the analytic pair

Funnels answer "where do users stop?", cohorts answer "do users come
back?" — and both reduce to the same machinery: bucket events by identity +
time, then count qualifying occurrences per bucket per period. The natural
extension of this page's pattern to retention triangles is worked out in
[Cohort Analysis](../../data-engineering/cohort-analysis.md); churn is its
negation (a cohort member with no qualifying event in the observation
window — computed with the same FILTER aggregation).

## Performance notes

- **Aggregate before you join**: everything above stays in one scan; the
  anti-pattern is step-per-query (four subqueries joined on user), which
  multiplies IO and reintroduces fan-out.
- **Pre-filter events** to funnel steps (`WHERE step_no BETWEEN 1 AND 4`)
  before the window/aggregate step — event tables are the widest input.
- **Pre-aggregate at scale**: session-scoped funnels over billions of
  events belong in the warehouse as materialized per-session step
  timestamps, refreshed incrementally (streaming session windows handle the
  live edge — [Stream Processing](../../data-engineering/stream-processing.md)).
- **Deduplication choice**: exact (`ROW_NUMBER` on event id, one extra
  sort) vs probabilistic ([sketches](../advanced/sketch-algorithms.md)) for
  approximate dashboards.

## Interview questions

1. **Write a 3-step funnel with a 30-minute per-step window.** The
   first-occurrence + chained-comparison pattern above; say "sessionized,
   ordered, windowed, deduped" explicitly — those four words are what the
   interviewer is listening for.
2. **Why `FILTER (WHERE ...)` instead of four subqueries?** One scan, one
   aggregation; no fan-out; the plan stays linear. (Also: `FILTER` is
   standard SQL — portable across Postgres, SQLite, DuckDB, Spark.)
3. **A user triggers step 3 before step 2 by timestamp. Convert?** No —
   the chained comparisons require strictly increasing qualified times;
   out-of-order events are ignored by construction. If the interviewer
   pushes ("what if clock skew?"), discuss server-side timestamps and
   watermark ordering.
4. **How would you make this dashboard update in near-real-time?**
   Streaming sessionization + incremental per-session step materialization
   (Kafka/Flink) with the batch query as the backfill/corrector — the
   lambda pattern; see [Kafka Streams](../../distributed/messaging/kafka-streams.md).

## Key Takeaways

- A funnel is ordered + windowed + scoped + deduped; get all four
  parameters into the query explicitly or the numbers are fiction.
- First-occurrence timestamps via `min(...) FILTER (WHERE ...)` plus
  chained comparisons is the portable, one-scan implementation.
- Engine-native funnels (`windowFunnel` in ClickHouse) implement the
  ordered search at warehouse scale; portable SQL is the fallback, not the
  default at billions of events.
- The failure modes are duplicates, missing windows, and unordered
  comparisons — all invisible at small test-data scale.

## Cross-References

- [Cohort Analysis](../../data-engineering/cohort-analysis.md) — retention triangles and churn.
- [Gaps and Islands](./gaps-and-islands.md) — sessionization used to scope funnels.
- [Window Function Problems](../interview-problems/window-function-problems.md) — adjacent interview problems.
- [Sketch Algorithms](../advanced/sketch-algorithms.md) — approximate distinct counts at dashboard scale.
- [Kafka Streams](../../distributed/messaging/kafka-streams.md) — the streaming side of live funnels.

## References

- PostgreSQL Documentation, "[Aggregate Functions: GROUPING and FILTER](https://www.postgresql.org/docs/current/functions-aggregate.html)" — `FILTER` clause semantics used throughout.
- ClickHouse Documentation, "[Parametric Aggregate Functions](https://clickhouse.com/docs/reference/functions/aggregate-functions/parametric-functions)" — `windowFunnel(window)(timestamp, cond...)` semantics.
- M. Kleppmann, *Designing Data-Intensive Applications*, O'Reilly, 2017, Chapter 11 — event streams and stream/table duality behind session-scoped analytics.
