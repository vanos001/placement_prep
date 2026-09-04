# Value Window Functions: FIRST_VALUE, LAST_VALUE, NTH_VALUE and Frame Traps

Aggregate window functions *summarize* a frame; the three **value functions**
— `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE` — *read one specific row* of it.
That difference is exactly where the bugs live: because the functions'
answers depend on which row the frame currently ends at, a frame chosen for
aggregate convenience silently breaks them. `LAST_VALUE` returning the
current row is not an engine quirk — it is the documented consequence of the
default frame, and every interview answer that fixes it by reflex, without
saying why the default exists, is missing the point.

The full frame model (ROWS/RANGE/GROUPS bounds, peer groups, EXCLUDE) is in
[Window Functions](./window-functions.md); this page covers only what the
value functions do to it and vice versa. Session and streak queries that feed
these functions are in [Gaps and Islands](./gaps-and-islands.md).

## The frame contract

PostgreSQL's documentation defines the trio compactly: `first_value` returns
the value "evaluated at the row that is the first row of the window frame,"
`last_value` at the last row, `nth_value(value, n)` at the *n*-th row
"counting from 1," returning NULL "if there is no such row." The critical
sentence follows: these functions "consider only the rows within the 'window
frame', which by default contains the rows from the start of the partition
through the last peer of the current row. This is likely to give unhelpful
results for last_value and sometimes also nth_value."

Why is the default *correct* for aggregates but wrong for `LAST_VALUE`?
Because the standard built the default frame — `RANGE BETWEEN UNBOUNDED
PRECEDING AND CURRENT ROW` — for **running** aggregates: a running total must
include the current row and everything before it. Under that frame,
`LAST_VALUE`'s "last row of the frame" is the current row (or, with
duplicate ORDER BY keys, the last *peer* of the current row). The function
does exactly what it is told; the frame was designed for a different
question.

## The LAST_VALUE bug and its two fixes

Concretely (verified shape):

```sql
CREATE TABLE events (k text, v int);
INSERT INTO events VALUES ('a',10),('a',20),('a',30),('b',5);

SELECT k, v,
       last_value(v) OVER (PARTITION BY k ORDER BY v) AS lv_default,
       last_value(v) OVER (PARTITION BY k ORDER BY v
           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS lv_fixed,
       first_value(v) OVER (PARTITION BY k ORDER BY v DESC) AS fv_desc
FROM events;
```

| k | v | lv_default | lv_fixed | fv_desc |
|---|---|---|---|---|
| a | 10 | 10 | 30 | 30 |
| a | 20 | 20 | 30 | 30 |
| a | 30 | 30 | 30 | 30 |
| b | 5  | 5  | 5  | 5  |

`lv_default` equals `v` on every row — the bug. Two idiomatic fixes:

1. **Widen the frame**: `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED
   FOLLOWING` makes "last row of the frame" mean "last row of the
   partition." Microsoft's own `LAST_VALUE` documentation demonstrates this
   trap with an example that "returns 0" under the default frame, noting
   "The default range is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
   and that a frame ending at `UNBOUNDED FOLLOWING` is required.
2. **Flip the sort**: `FIRST_VALUE(x) OVER (ORDER BY ts DESC)` — the
   first row of a frame that always *starts* at the partition's beginning is
   stable under the default frame, so this form needs no explicit frame and
   works on every engine that has `FIRST_VALUE` at all. It is the portable
   fix.

For `PARTITION BY` questions the two fixes are equivalent; for frames that
grow incrementally (events arriving in order), only the flipped sort answers
"latest value *so far*" without rewriting the frame per row.

Both fixes need a **deterministic ORDER BY**: two events at the same
timestamp make "last" ambiguous, and the winner can change between runs. Add
a tiebreaker column (`ORDER BY ts, id`) — the same discipline as in
[Gaps and Islands](./gaps-and-islands.md).

## NTH_VALUE: NULL is an answer, not an error

`NTH_VALUE(x, n)` returns NULL while the frame holds fewer than *n* rows —
the documented "no such row" case. This makes early rows of a growing frame
semantically honest but visually confusing:

```sql
SELECT k, v,
       nth_value(v, 2) OVER (PARTITION BY k ORDER BY v) AS nv2_growing,
       nth_value(v, 2) OVER (PARTITION BY k ORDER BY v
           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS nv2_full
FROM events;
-- k='a': nv2_growing = NULL, 20, 20   (frame has 1, 2, 3 rows)
-- k='b': nv2_full    = NULL           (partition has only 1 row)
```

If NULLs are unwanted, `COALESCE` them — but recognize that the NULL *means*
"the frame had not reached row 2 yet," which is sometimes the information you
want (e.g., flagging partitions too small for a "second-best" statistic).

The standard also defines `FROM FIRST` / `FROM LAST` direction options and
`RESPECT NULLS` / `IGNORE NULLS` null treatment for the value functions.
Support is wildly uneven (matrix below): PostgreSQL explicitly documents that
"the standard's FROM FIRST or FROM LAST option for nth_value is not
implemented: only the default FROM FIRST behavior is supported" (the FROM
LAST result is achieved by reversing the ORDER BY), and SQLite rejects
`FROM LAST` syntax outright.

## RESPECT/IGNORE NULLS: forward and backward fill

`IGNORE NULLS` turns the trio into the workhorses of **as-of** analytics:
last observation carried forward (LOCF), next observation carried backward,
and price/rate interpolation along event time. Where supported:

```sql
-- Last known price as of each tick (engines with IGNORE NULLS):
SELECT ts, price,
       last_value(price IGNORE NULLS) OVER (
           ORDER BY ts
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS last_known
FROM ticks;
```

Note the frame must end at `CURRENT ROW` for LOCF — a *forward-looking*
frame (`UNBOUNDED FOLLOWING`) would leak future prices into the past, the
window-function version of lookahead bias. Backward fill is the mirror:
`first_value(price IGNORE NULLS) OVER (ORDER BY ts ROWS BETWEEN CURRENT ROW
AND UNBOUNDED FOLLOWING)`.

Support matrix (verified against vendor docs):

| capability | PostgreSQL | MySQL / MariaDB | SQL Server | SQLite |
|---|---|---|---|---|
| FIRST_VALUE / LAST_VALUE | ✓ | ✓ | ✓ | ✓ |
| NTH_VALUE | ✓ | ✓ | ✗ (absent from its analytic-functions list) | ✓ |
| IGNORE NULLS | ✗ (documented unimplemented) | MariaDB: undocumented | ✓ 2022+ | ✗ |
| FROM LAST | ✗ | MariaDB: no syntax | — (no NTH_VALUE) | ✗ |

When `IGNORE NULLS` is unavailable, the portable LOCF idiom builds a
"current observation id" with an aggregate that skips NULLs, then reads the
observation's first value inside it:

```sql
SELECT ts, price,
       first_value(price) OVER (PARTITION BY grp ORDER BY ts) AS last_known
FROM (
    SELECT ts, price,
           count(price) OVER (ORDER BY ts) AS grp   -- COUNT skips NULLs
    FROM ticks
) t;
-- (09:00,10) (09:01,10) (09:02,10) (09:03,12) (09:04,12) — verified
```

Why it works: `count(price)` increments only on observed values, so every
row since the *k*-th observation shares `grp = k`; `FIRST_VALUE` within that
group is the most recent observation. The window functions must live on two
plan layers because a window function cannot consume another window
function's output in the same SELECT — the nesting is mandatory, not stylistic.
The deeper as-of toolkit (temporal joins, exclusion constraints) is in
[Temporal SQL Patterns](./temporal-sql-patterns.md).

## Frames as instruments: ROWS vs RANGE vs GROUPS in one paragraph

Running totals over `(100, 100, 200)` differ by mode: `ROWS ... CURRENT ROW`
yields `(100, 200, 400)` — each tie consumed one at a time — while the
default `RANGE` frame absorbs ties into peer groups and yields `(200, 200,
400)` (verified over SQLite). The value functions see this too:
`NTH_VALUE(x, 2)` over tied values is ambiguous under RANGE because peer
groups, not rows, are the frame's currency. `GROUPS BETWEEN 1 PRECEDING AND
CURRENT ROW` over the same data gives `(200, 200, 400)` with clean "previous
value's whole group" semantics — the mode built for duplicated timestamps.
The full model, including the EXCLUDE clause, is in
[Window Functions](./window-functions.md); the practical summary here is
that **the frame mode changes which row is "the last row"**, so it changes
`LAST_VALUE`/`NTH_VALUE` answers, not just aggregate answers.

## Rolling aggregates: calendar frames vs row frames

A "7-day rolling average" written as `ROWS BETWEEN 6 PRECEDING AND CURRENT
ROW` averages 7 *physical rows* — wrong whenever days are missing from the
data. The calendar-correct form uses a RANGE distance:

```sql
SELECT day, revenue,
       avg(revenue) OVER (ORDER BY day
           RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW) AS avg_7d
FROM daily_revenue;
```

Support: PostgreSQL 11+ (its release notes describe exactly this: RANGE
mode "to use PRECEDING and FOLLOWING to select rows having grouping values
within plus or minus the specified offset"); SQL Server rejects distance
bounds in RANGE outright ("You can't use RANGE with ... PRECEDING or ...
FOLLOWING" in the OVER-clause reference); MariaDB documents that "RANGE
frames do not support DATE or DATETIME arithmetic" while supporting numeric
distances; SQLite supports numeric RANGE distances. On engines without
calendar frames, the fallback is a self-join over a date range or a calendar
table — never a ROWS frame pretending days are dense.

## What the planner does: sorts, indexes, spills

Every window function needs input sorted by `(PARTITION BY..., ORDER BY...)`
— see the execution internals in
[Window Functions](./window-functions.md) for the buffer-and-emit mechanics
and the spill risk when a partition exceeds memory. The value-function
specifics:

- **Sort sharing.** Functions sharing one window specification share one
  sort; specifications whose keys are prefixes of each other can also share
  (MariaDB documents the prefix rule explicitly — sort once by the longer
  key and both functions consume it). Mixing orderings re-sorts per distinct
  ordering.
- **Index-matched input order.** When an index's leading columns match the
  window's partition/order keys, the planner can read rows pre-sorted and
  skip the sort entirely; PostgreSQL 13's incremental sorting extends this
  to partial matches — "if an intermediate query result is known to be
  sorted by one or more leading keys of a required sort ordering, the
  additional sorting can be done considering only the remaining keys, if the
  rows are sorted in batches that have equal leading keys." An index whose
  key order matches the window spec — `(user_id, ts)` for
  `PARTITION BY user_id ORDER BY ts` — therefore converts a 100M-row window
  sort into a plain scan for per-user queries.
- **Run-condition pushdown.** PostgreSQL 15 optimizes window queries whose
  filters can be evaluated during the window pass — "improve the performance
  of window functions that use row_number(), rank(), dense_rank() and
  count()" — so `WHERE rn <= 1` on top of `ROW_NUMBER()` filters early
  instead of after a full partition pass; value functions are frame-dependent
  and benefit less.
- **Frame shape drives cost.** Frames that only grow (`UNBOUNDED PRECEDING
  ... CURRENT ROW`) let the engine stream; frames that add *and* drop rows
  per step either maintain a removable buffer or re-aggregate. The
  invertibility economics are in [Window Functions](./window-functions.md).

## Interview Problems

### Problem 1 — Latest event per user

*Schema:* `logins(user_id, ts, ip)`. "Return each user's most recent login."
Worked solutions, best first:

```sql
-- (a) FIRST_VALUE with flipped sort: value functions answer "which row",
--     one pass, no self-join; ties broken by a deterministic second key.
SELECT DISTINCT user_id,
       first_value(ts)  OVER w AS last_ts,
       first_value(ip)  OVER w AS last_ip
FROM logins
WINDOW w AS (PARTITION BY user_id ORDER BY ts DESC, ip);

-- (b) LAST_VALUE with explicit frame — the canonical trap demo:
SELECT DISTINCT user_id,
       last_value(ts) OVER (PARTITION BY user_id ORDER BY ts, ip
           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_ts
FROM logins;

-- (c) ROW_NUMBER + filter (the general Top-N form):
SELECT user_id, ts, ip FROM (
    SELECT *, row_number() OVER (PARTITION BY user_id
                                 ORDER BY ts DESC, ip) AS rn
    FROM logins) ranked
WHERE rn = 1;
-- (d) PostgreSQL-only: SELECT DISTINCT ON (user_id) user_id, ts, ip
--     FROM logins ORDER BY user_id, ts DESC, ip;
```

The discriminating answer: (a) and (b) return *values*, so a `DISTINCT`
collapses the per-row output; (c) returns whole *rows* and generalizes to
Top-N; (d) is PostgreSQL's projection shorthand. A candidate who writes
`last_value(...)` without a frame and "verifies" it on a single-user dataset
has reproduced the exact production bug this page exists for.

### Problem 2 — Fill missing prices (LOCF)

*Schema:* `prices(ts, symbol, price)` with NULLs where the feed gapped.
"Produce a complete series, carrying the last known price forward — and say
what your query does at the start of each symbol's history."

```sql
-- Portable (no IGNORE NULLS needed):
SELECT ts, symbol,
       first_value(price) OVER (PARTITION BY symbol, grp ORDER BY ts) AS filled
FROM (
    SELECT ts, symbol, price,
           count(price) OVER (PARTITION BY symbol ORDER BY ts) AS grp
    FROM prices
) t;
```

Worked answer: `count(price)` ignores NULLs, so it numbers observations
within each symbol; every gapped row inherits its observation's group, and
`FIRST_VALUE` returns that observation's price. Rows *before any observation*
have `grp = 0` and fill with NULL — a boundary worth stating unprompted, and
the reason trading pipelines seed series with a prior close (the as-of join
alternative in [Temporal SQL Patterns](./temporal-sql-patterns.md) handles
this by construction). On engines with `IGNORE NULLS` (SQL Server 2022+),
`last_value(price IGNORE NULLS) OVER (PARTITION BY symbol ORDER BY ts ROWS
BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` does the same in one layer.

### Problem 3 — Top-1 per group without LIMIT-in-join tricks

*Question:* "For each department, the highest-paid employee — name and
salary — but the table has duplicates on salary and you may not use the
`JOIN ... ON x = (SELECT max(...))` trick."

```sql
SELECT DISTINCT department,
       first_value(name)   OVER w AS top_name,
       first_value(salary) OVER w AS top_salary
FROM employees
WINDOW w AS (PARTITION BY department ORDER BY salary DESC, name);
```

Points that separate strong answers: the deterministic tiebreaker
(`salary DESC, name`) makes the pick reproducible; `DISTINCT` is the
honest cost of value functions returning one value per *row*; and unlike
the correlated `max()` trick, this runs in one sorted pass. If the question
wants "all employees tied for the top," that is `rank() = 1` — a ranking
function question, not a value-function one. The pathological inverse —
"highest salary *among others*" — is `EXCLUDE CURRENT ROW` territory
([Window Functions](./window-functions.md)).

### Problem 4 — First-touch and last-touch session attribution

*Schema:* `events(user_id, ts, channel)`, sessions defined by 30-minute
inactivity (sessionization recipe in
[Gaps and Islands](./gaps-and-islands.md) produces `session_id` per event).
"Attribute each session's conversions to first-touch and last-touch
channels."

```sql
SELECT user_id, session_id,
       first_value(channel) OVER (PARTITION BY user_id, session_id
           ORDER BY ts, event_id) AS first_touch,
       first_value(channel) OVER (PARTITION BY user_id, session_id
           ORDER BY ts DESC, event_id DESC) AS last_touch,
       min(ts) OVER (PARTITION BY user_id, session_id) AS started_at,
       max(ts) OVER (PARTITION BY user_id, session_id) AS ended_at
FROM sessions;
```

Worked answer: both touches come from `FIRST_VALUE` — last-touch flips the
sort rather than trusting `LAST_VALUE` under the default frame; note the
*double* tiebreaker (`ts DESC, event_id DESC`) because a session's boundary
events routinely share timestamps and first/last must not swap between runs.
`min`/`max` over the full partition need no frame care (aggregates over the
whole partition are frame-independent with no ORDER BY). A last answer that
uses bare `LAST_VALUE(channel) OVER (ORDER BY ts)` returns each row's own
channel — the bug again, now with attribution money attached. Marketing
queries like this are why the flipped-sort idiom deserves muscle memory.

## Key Takeaways

- Value functions read the frame, not the partition: the default frame
  (`RANGE UNBOUNDED PRECEDING .. CURRENT ROW`) exists for running
  aggregates and makes bare `LAST_VALUE` return the current row — by
  specification, everywhere.
- Two fixes: explicit `UNBOUNDED FOLLOWING` frame, or `FIRST_VALUE` over a
  reversed ORDER BY. The second is portable and needs no frame syntax.
- `NTH_VALUE` returns NULL while the frame is shorter than *n* — an honest
  "not yet," not a bug; `IGNORE NULLS` and `FROM LAST` are standard options
  with patchy support (PostgreSQL: neither; SQL Server: IGNORE NULLS only
  since 2022, and no NTH_VALUE at all).
- The frame *mode* (ROWS/RANGE/GROUPS) changes which row is "last" when
  values tie; duplicated timestamps require tiebreakers or GROUPS semantics.
- LOCF without IGNORE NULLS: `count(value)` over time builds an observation
  id; `FIRST_VALUE` per id carries it forward — two plan layers, portable,
  lookahead-free.
- Performance is about the sort: matching indexes (with PG 13+ incremental
  sort for prefixes), shared window specifications, and frames that only
  grow.

## Cross-References

- [Window Functions](./window-functions.md) — the full frame model, EXCLUDE clause, execution internals, sort sharing.
- [Gaps and Islands](./gaps-and-islands.md) — sessionization that produces the partition keys these functions consume.
- [Statistical SQL](./statistical-sql.md) — percentiles and distributions, the aggregate cousins of value lookups.
- [Temporal SQL Patterns](./temporal-sql-patterns.md) — as-of joins and interval semantics for event-time questions.
- [Interview Traps](../interview-problems/interview-traps.md) — nondeterminism and tie-handling failure shapes.
- [Window Function Problems](../interview-problems/window-function-problems.md) — ranked Top-N and cumulative problems that pair with these.

## References

- PostgreSQL Documentation, "[Window Functions](https://www.postgresql.org/docs/current/functions-window.html)" — value-function definitions, the default-frame warning, and the unimplemented IGNORE NULLS / FROM LAST note.
- Microsoft Learn, "[FIRST_VALUE (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/functions/first-value-transact-sql)" and "[LAST_VALUE (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/functions/last-value-transact-sql)" — required ORDER BY, the default-frame example, and SQL Server 2022 IGNORE NULLS support.
- Microsoft Learn, "[OVER Clause (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/queries/select-over-clause-transact-sql)" — ROWS/RANGE-only grammar, default frame, and the RANGE distance-bound limitation; "[Analytic Functions (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/functions/analytic-functions-transact-sql)" — function list (no NTH_VALUE).
- SQLite Documentation, "[Window Functions](https://www.sqlite.org/windowfunctions.html)" — frame-spec grammar (GROUPS, EXCLUDE), value functions as the frame-dependent exceptions, no null-treatment support.
- MariaDB Documentation, "[Window Functions Overview](https://mariadb.com/kb/en/window-functions/)" and "[NTH_VALUE](https://mariadb.com/kb/en/nth_value/)" — default frame, no GROUPS/exclusion, no RANGE date arithmetic, sort-sharing rules.
- PostgreSQL 11 Release Notes, "[Window functions](https://www.postgresql.org/docs/11/release-11.html)" — RANGE distance bounds, GROUPS mode, frame exclusion; PostgreSQL 13 Release Notes — incremental sorting; PostgreSQL 15 Release Notes — window run-condition optimizations.
- A. Eisenberg, J. Melton, K. Kulkarni, F. Michels, "SQL:2003 Has Been Published," ACM SIGMOD Record 33(1), 2004. [DOI: 10.1145/974121.974142] — the standard edition that introduced window functions and frames.
- F. Zemke, "What's New in SQL:2011," ACM SIGMOD Record 41(1), 2012. [DOI: 10.1145/2206869.2206883] — the framing-options baseline PostgreSQL 11 implemented against.
- I. Ben-Gan, *Microsoft SQL Server 2012: High-Performance T-SQL Using Window Functions*, Microsoft Press, 2012 — the canonical treatment of value functions, frames, and the LAST_VALUE idiom.
