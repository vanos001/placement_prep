# Window Function Interview Problems

Window functions calculate a value across related rows without collapsing the
rows like `GROUP BY`. They are essential for ranking, running totals, session
analysis, time comparisons, and top-per-group problems.

## Core syntax

```sql
function(value) OVER (
  PARTITION BY group_columns
  ORDER BY order_columns
  ROWS BETWEEN ... AND ...
)
```

- `PARTITION BY` creates independent windows.
- `ORDER BY` defines sequence inside each partition.
- The frame controls which ordered rows contribute to the result.
- `ROW_NUMBER`, `RANK`, and `DENSE_RANK` differ when values tie.

## Top row per group

```sql
WITH ranked AS (
  SELECT e.*, ROW_NUMBER() OVER (
    PARTITION BY department_id ORDER BY salary DESC, employee_id
  ) AS rn
  FROM employees e
)
SELECT *
FROM ranked
WHERE rn = 1;
```

Use `ROW_NUMBER` when exactly one row is required; use `RANK` when ties should
share a rank and produce multiple rows.

## Running totals and moving windows

```sql
SELECT account_id, posted_at, amount,
       SUM(amount) OVER (
         PARTITION BY account_id
         ORDER BY posted_at, transaction_id
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS balance_delta
FROM transactions;

SELECT day, revenue,
       AVG(revenue) OVER (
         ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       ) AS seven_day_average
FROM daily_revenue;
```

Always define a deterministic tie-breaker. A timestamp alone may not order two
rows committed at the same time.

## Previous and next row

```sql
SELECT user_id, event_time, event_type,
       LAG(event_time) OVER (
         PARTITION BY user_id ORDER BY event_time
       ) AS previous_time,
       LEAD(event_type) OVER (
         PARTITION BY user_id ORDER BY event_time
       ) AS next_type
FROM user_events;
```

Use `LAG` for deltas and retention, `LEAD` for next-state analysis, and
`FIRST_VALUE`/`LAST_VALUE` carefully with an explicit frame.

## Gaps and islands

To group consecutive activity into sessions, compare an event with its previous
event, mark a break, and cumulative-sum the break flag:

```sql
WITH marked AS (
  SELECT e.*,
         CASE WHEN event_time - LAG(event_time) OVER (
           PARTITION BY user_id ORDER BY event_time
         ) > INTERVAL '30 minutes' THEN 1 ELSE 0 END AS new_session
  FROM events e
), grouped AS (
  SELECT marked.*,
         SUM(new_session) OVER (
           PARTITION BY user_id ORDER BY event_time
         ) AS session_id
  FROM marked
)
SELECT user_id, session_id, MIN(event_time), MAX(event_time), COUNT(*)
FROM grouped
GROUP BY user_id, session_id;
```

The interval syntax varies by database; explain the idea independently of the
vendor syntax.

## Common traps

- Filtering a window result in `WHERE` in the same query level; use a CTE or
  subquery because the window is evaluated after `WHERE`.
- Using `RANK` when the requirement is exactly one row.
- Omitting a deterministic tie-breaker.
- Assuming `LAST_VALUE` means the last row in the partition without setting a
  frame ending at `UNBOUNDED FOLLOWING`.
- Ignoring null ordering and database-specific defaults.
- Sorting large partitions without an appropriate access path or memory budget.

## Deduplication: keep one row per key

The most production-used window trick: pick the surviving row per key when
"duplicate" means equal business keys but different technical rows
(late-arriving CDC events, double-submits, source-system re-emits):

```sql
WITH deduped AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY user_id, product_id          -- business key
           ORDER BY updated_at DESC, event_id DESC   -- newest wins, deterministic
         ) AS rn
  FROM inventory_changes
)
SELECT * FROM deduped WHERE rn = 1;
```

This is a *top-1 per group* — the same machinery as the ranking problems
above — but in a different costume, and interviews use the costume to check
whether you recognize it. Note what it is *not*: it does not enforce
uniqueness (write-time constraints do that — see
[Indexes in SQL](../sql/indexes.md)); it repairs a batch or a report.

## Month-over-month with LAG: the edge cases are the question

```sql
WITH monthly AS (
  SELECT date_trunc('month', order_ts) AS month,
         sum(amount) AS revenue
  FROM orders
  GROUP BY 1
),
with_prev AS (
  SELECT month, revenue,
         LAG(revenue) OVER (ORDER BY month) AS prev_revenue
  FROM monthly
)
SELECT month, revenue, prev_revenue,
       CASE
         WHEN prev_revenue IS NULL  THEN NULL                -- first month
         WHEN prev_revenue = 0      THEN NULL                -- div-by-zero guard
         ELSE round(100.0 * (revenue - prev_revenue) / prev_revenue, 1)
       END AS mom_pct
FROM with_prev;
```

The interviewer is not testing the formula; they are testing the guards.
Zero denominators (a no-revenue month), NULL on the first row, and
*missing months* (LAG crosses a gap and pairs December with October) are
the three standard answers. The missing-month fix is calendar sparsening —
join against a generated month series before the LAG.

## Median without PERCENTILE_CONT

Engines without `PERCENTILE_CONT` (and some versions' plans for it) compute
medians with ordered windows:

```sql
WITH r AS (
  SELECT salary,
         ROW_NUMBER() OVER (ORDER BY salary)  AS rn,
         COUNT(*)  OVER ()                    AS n
  FROM salaries
)
SELECT round(avg(salary), 2) AS median
FROM r
WHERE rn IN ((n + 1) / 2, (n + 2) / 2);   -- middle row, or both middles
```

The `IN` trick with integer division handles both parities: odd n picks one
row, even n averages the two middle rows. `COUNT(*) OVER ()` (an empty
window spec — the *entire partition* frame) is worth pointing out
explicitly; interviewers listen for it. Per-group medians: add
`PARTITION BY department` to both window functions and filter
`rn BETWEEN (n+1)/2 AND (n+2)/2` — say "between," not "in," or even-length
groups lose their upper middle.

## LAST_VALUE: the default-frame bug, live

```sql
-- WRONG: returns the current row's value for every row
SELECT user_id, event_time,
       LAST_VALUE(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS last_seen
FROM events;

-- RIGHT: frame must extend to partition end
SELECT user_id, event_time,
       LAST_VALUE(event_time) OVER (
         PARTITION BY user_id ORDER BY event_time
         ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
       ) AS last_seen
FROM events;
```

Why the first query "runs fine": with an ORDER BY, the default frame is
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, so the window *ends at
the current row* — LAST_VALUE sees a window whose last row is the current
row. The fix generalizes (FIRST_VALUE is frame-safe by accident,
LAST_VALUE is not), and the full frame-mode mechanics — including the
RANGE-ties variant that makes even the "RIGHT" version group same-
timestamp rows — are in
[Window Functions](../sql/window-functions.md) and
[SQL Interview Traps](./interview-traps.md).

## Interview questions

**Window function versus GROUP BY?**

`GROUP BY` reduces rows into one row per group. A window function preserves the
rows and adds a calculation based on related rows.

**How do you find the second-highest salary per department?**

Partition by department, rank salaries with `DENSE_RANK`, then filter for rank
2. Choose `ROW_NUMBER` only if ties must be broken.

**How do you calculate month-over-month growth?**

Aggregate revenue by month first, use `LAG(revenue)` over month order, then
compute `(current - previous) / previous` with a zero/null guard.

## Cross-references

- [SQL](../sql/README.md)
- [Query processing](../query-processing/README.md)
- [Indexes](../indexing/README.md)
- [Transactions](../transactions/README.md)
- [PostgreSQL advanced features](../postgresql/advanced-features.md)

## References

- [PostgreSQL window functions](https://www.postgresql.org/docs/current/tutorial-window.html)
- [PostgreSQL SELECT processing order](https://www.postgresql.org/docs/current/sql-select.html)
- [SQL standard overview](https://www.iso.org/standard/76583.html)
