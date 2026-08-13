# SQL Window Functions

## Overview

**Window functions** perform calculations across a set of rows related to the current row, without collapsing them into a single output row (unlike GROUP BY). They "look through a window" of related rows while preserving individual row detail. Introduced in SQL:2003, they are essential for analytics and ranking queries.

## Syntax

```sql
function_name(args) OVER (
    [PARTITION BY partition_columns]
    [ORDER BY sort_columns [ASC|DESC]]
    [frame_clause]
)
```

- **PARTITION BY**: Divides rows into groups (like GROUP BY, but doesn't collapse)
- **ORDER BY**: Defines the order within each partition
- **frame_clause**: Defines which rows in the partition to include

## Window Function vs GROUP BY

```sql
-- GROUP BY: collapses rows
SELECT department, AVG(salary) FROM Employees GROUP BY department;
-- Result: one row per department

-- Window function: preserves all rows
SELECT name, department, salary,
    AVG(salary) OVER (PARTITION BY department) AS dept_avg
FROM Employees;
-- Result: all employee rows, each with department average
```

```mermaid
graph LR
    subgraph "GROUP BY"
        G1["3 rows in Engineering"] --> G2["1 row: avg = 75000"]
    end
    subgraph "Window Function"
        W1["3 rows in Engineering"] --> W2["3 rows, each with avg = 75000"]
    end

    style G2 fill:#ffcdd2
    style W2 fill:#c8e6c9
```

## Ranking Functions

### ROW_NUMBER()

Assigns a unique sequential integer to each row within a partition.

```sql
SELECT name, department, salary,
    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS row_num
FROM Employees;

-- Result:
-- name    | department   | salary | row_num
-- Alice   | Engineering  | 90000  | 1
-- Bob     | Engineering  | 80000  | 2
-- Carol   | Engineering  | 75000  | 3
-- Dave    | Science      | 85000  | 1
-- Eve     | Science      | 70000  | 2
```

### RANK()

Assigns a rank with **gaps** for ties.

```sql
SELECT name, salary,
    RANK() OVER (ORDER BY salary DESC) AS rnk
FROM Employees;
-- If two employees tie for rank 2, next is rank 4 (gap)
```

### DENSE_RANK()

Assigns a rank **without gaps** for ties.

```sql
SELECT name, salary,
    DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rnk
FROM Employees;
-- If two employees tie for rank 2, next is rank 3 (no gap)
```

### Ranking Comparison

```sql
SELECT name, salary,
    ROW_NUMBER() OVER (ORDER BY salary DESC) AS row_num,
    RANK()       OVER (ORDER BY salary DESC) AS rnk,
    DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rnk
FROM (VALUES ('A', 90000), ('B', 80000), ('C', 80000), ('D', 70000)) AS t(name, salary);
```

| name | salary | row_num | rnk | dense_rnk |
|---|---|---|---|---|
| A | 90000 | 1 | 1 | 1 |
| B | 80000 | 2 | 2 | 2 |
| C | 80000 | 3 | 2 | 2 |
| D | 70000 | 4 | 4 | 3 |

### NTILE(n)

Divides rows into `n` approximately equal groups (buckets).

```sql
SELECT name, salary,
    NTILE(4) OVER (ORDER BY salary DESC) AS quartile
FROM Employees;
-- Quartile 1 = top 25%, Quartile 4 = bottom 25%
```

## Aggregate Window Functions

All standard aggregates work as window functions.

```sql
SELECT
    name, department, salary,
    SUM(salary) OVER () AS company_total,
    SUM(salary) OVER (PARTITION BY department) AS dept_total,
    AVG(salary) OVER (PARTITION BY department) AS dept_avg,
    COUNT(*) OVER (PARTITION BY department) AS dept_count,
    MIN(salary) OVER (PARTITION BY department) AS dept_min,
    MAX(salary) OVER (PARTITION BY department) AS dept_max
FROM Employees;
```

## Value / Offset Functions

### LAG()

Access data from a **previous** row.

```sql
SELECT name, salary,
    LAG(salary) OVER (ORDER BY salary) AS prev_salary,
    salary - LAG(salary) OVER (ORDER BY salary) AS diff
FROM Employees;

-- With default value and offset
SELECT name, hire_date, salary,
    LAG(salary, 2, 0) OVER (PARTITION BY department ORDER BY hire_date) AS salary_2_ago
FROM Employees;
-- LAG(column, offset, default)
```

### LEAD()

Access data from the **next** row.

```sql
SELECT name, salary,
    LEAD(salary) OVER (ORDER BY salary) AS next_salary,
    LEAD(salary) OVER (ORDER BY salary) - salary AS diff
FROM Employees;
```

### FIRST_VALUE()

Get the **first** value in the window frame.

```sql
SELECT name, department, salary,
    FIRST_VALUE(name) OVER (PARTITION BY department ORDER BY salary DESC) AS highest_paid
FROM Employees;
```

### LAST_VALUE()

Get the **last** value in the window frame.

```sql
-- CAREFUL: default frame is ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
-- To get the actual last value, specify the full frame:
SELECT name, department, salary,
    LAST_VALUE(salary) OVER (
        PARTITION BY department
        ORDER BY salary
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS dept_max_salary
FROM Employees;
```

### NTH_VALUE()

Get the **nth** value in the window frame.

```sql
SELECT name, department, salary,
    NTH_VALUE(salary, 2) OVER (
        PARTITION BY department
        ORDER BY salary DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS second_highest
FROM Employees;
```

## Window Frame Clause

The frame defines which rows are included in the window for each row.

### Frame Types

```sql
-- ROWS: Physical offset (specific number of rows)
ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW  -- explicit ROWS frame (default is RANGE)
ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING  -- sliding window of 3

-- RANGE: Logical offset (based on ORDER BY values)
RANGE BETWEEN INTERVAL '30' DAY PRECEDING AND CURRENT ROW
RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW

-- GROUPS: Groups of identical ORDER BY values
GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW
```

### Default Frame

```sql
-- If ORDER BY is specified:
-- Default frame: RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
-- This means "all rows from the start of partition up to and including the current row"

-- If ORDER BY is NOT specified:
-- Default frame: ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
-- This means "all rows in the partition" (entire partition)
```

### Practical Frame Examples

```sql
-- 3-day moving average
SELECT date, revenue,
    AVG(revenue) OVER (
        ORDER BY date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS moving_avg_3d
FROM DailyRevenue;

-- Running total
SELECT date, revenue,
    SUM(revenue) OVER (ORDER BY date) AS running_total
FROM DailyRevenue;

-- Percentage of total
SELECT name, salary,
    salary * 100.0 / SUM(salary) OVER () AS pct_of_total
FROM Employees;

-- Year-to-date total
SELECT month, revenue,
    SUM(revenue) OVER (
        PARTITION BY year
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS ytd_total
FROM MonthlyRevenue;
```

## Named Windows (WINDOW Clause)

Define reusable window specifications.

```sql
SELECT name, department, salary,
    ROW_NUMBER() OVER dept_window AS row_num,
    RANK() OVER dept_window AS rnk,
    SUM(salary) OVER dept_window AS running_total
FROM Employees
WINDOW dept_window AS (PARTITION BY department ORDER BY salary DESC);
```

## Common Interview Patterns

### Top-N per Group

```sql
-- Top 3 earners per department
SELECT * FROM (
    SELECT name, department, salary,
        ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
    FROM Employees
) ranked
WHERE rn <= 3;
```

### Running Total / Cumulative Sum

```sql
SELECT date, amount,
    SUM(amount) OVER (ORDER BY date) AS running_total
FROM Transactions;
```

### Year-over-Year Growth

```sql
SELECT year, revenue,
    LAG(revenue) OVER (ORDER BY year) AS prev_year,
    (revenue - LAG(revenue) OVER (ORDER BY year)) * 100.0 /
    LAG(revenue) OVER (ORDER BY year) AS yoy_growth_pct
FROM YearlyRevenue;
```

### Gap and Islands

```sql
-- Find consecutive login streaks (islands)
SELECT user_id, MIN(login_date) AS streak_start, MAX(login_date) AS streak_end,
    COUNT(*) AS streak_length
FROM (
    SELECT user_id, login_date,
        login_date - INTERVAL '1 day' * ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS grp
    FROM Logins
) t
GROUP BY user_id, grp;
```

### Percentile / Median

```sql
-- Median salary per department
SELECT DISTINCT department,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) OVER (PARTITION BY department) AS median_salary
FROM Employees;

-- Alternative using ROW_NUMBER
SELECT department, AVG(salary) AS median
FROM (
    SELECT department, salary,
        ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary) AS rn,
        COUNT(*) OVER (PARTITION BY department) AS cnt
    FROM Employees
) t
WHERE rn IN (FLOOR((cnt + 1) / 2.0), CEIL((cnt + 1) / 2.0))
GROUP BY department;
```

## Interview Questions

### Beginner

**Q1: What is the difference between GROUP BY and window functions?**
A: GROUP BY collapses rows into summary rows (one per group). Window functions compute a value for each row while keeping all rows. GROUP BY reduces rows; window functions preserve them.

**Q2: What is the difference between ROW_NUMBER, RANK, and DENSE_RANK?**
A: ROW_NUMBER assigns unique sequential numbers (no ties). RANK assigns the same rank to ties, with gaps (1,2,2,4). DENSE_RANK assigns the same rank to ties, without gaps (1,2,2,3).

**Q3: What does PARTITION BY do in a window function?**
A: It divides the result set into partitions (groups). The window function is applied independently within each partition. It's like GROUP BY for window functions — but doesn't collapse rows.

### Intermediate

**Q4: What is the default window frame and why does it matter?**
A: With ORDER BY: `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. Without ORDER BY: `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`. This matters for LAST_VALUE — with the default frame and ORDER BY, LAST_VALUE returns the current row's value (not the actual last). Always specify the frame explicitly for LAST_VALUE.

**Q5: Write a query to find the second highest salary per department.**
A:
```sql
SELECT * FROM (
    SELECT name, department, salary,
        DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rnk
    FROM Employees
) ranked
WHERE rnk = 2;
```

**Q6: How do you calculate a running total that resets each month?**
A:
```sql
SELECT date, revenue,
    SUM(revenue) OVER (
        PARTITION BY DATE_TRUNC('month', date)
        ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS monthly_running_total
FROM DailyRevenue;
```

### Advanced / FAANG-Level

**Q7: Explain the difference between ROWS, RANGE, and GROUPS frame types.**
A:
- **ROWS**: Physical row count. `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` = exactly 3 rows regardless of values.
- **RANGE**: Logical value range. `RANGE BETWEEN 100 PRECEDING AND CURRENT ROW` = all rows where value is within 100 of current row. Ties (same ORDER BY value) are all included.
- **GROUPS**: Count of distinct ORDER BY value groups. `GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW` = current group plus one group before.

Key difference: ROWS is deterministic, RANGE depends on data values, GROUPS depends on distinct value groups.

**Q8: Optimize a query that uses 10 window functions on a 100M-row table.**
A: Strategies:
1. **Single pass**: If multiple window functions share the same PARTITION BY and ORDER BY, they execute in one pass. Group them with a named WINDOW clause.
2. **Reduce data first**: Filter rows before the window function (CTE or subquery)
3. **Materialized intermediate results**: For very complex calculations, materialize intermediate results
4. **Index on partition/order columns**: Helps with sorting
5. **Avoid unnecessary frames**: Use ROWS instead of RANGE when possible (deterministic, faster)
6. **Parallel execution**: Ensure the database can parallelize window function computation

## Common Mistakes

- Forgetting that window functions execute after WHERE, GROUP BY, HAVING
- Using LAST_VALUE without specifying the frame (default frame gives wrong results)
- Confusing ROW_NUMBER with RANK (ROW_NUMBER never has ties)
- Not understanding that PARTITION BY doesn't reduce rows
- Using window functions in WHERE directly (wrap in subquery/CTE first)
- Overusing window functions when GROUP BY would be simpler and faster

## Summary

| Function | Purpose | Ties Handling |
|---|---|---|
| ROW_NUMBER | Unique sequential number | No ties (unique) |
| RANK | Rank with gaps | Same rank, with gaps |
| DENSE_RANK | Rank without gaps | Same rank, no gaps |
| NTILE | Divide into n buckets | Approximate equal size |
| LAG | Previous row value | N/A |
| LEAD | Next row value | N/A |
| FIRST_VALUE | First in frame | N/A |
| LAST_VALUE | Last in frame | N/A |
| NTH_VALUE | Nth in frame | N/A |
| Aggregates | SUM, AVG, COUNT, MIN, MAX | Over window |

## Cross-References

- [SQL Overview](README.md) — SQL fundamentals
- [CTEs](ctes.md) — Combining CTEs with window functions
- [Subqueries](subqueries.md) — Window functions in subqueries
- [Indexes](indexes.md) — Indexing for window function performance
- [Query Tuning](../indexing/tuning.md) — Optimizing analytical queries
