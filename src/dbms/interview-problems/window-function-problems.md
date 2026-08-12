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
