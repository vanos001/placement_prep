# Classic SQL Interview Problems

## Second Highest Salary

```sql
-- Method 1: Subquery
SELECT MAX(salary) FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);

-- Method 2: DENSE_RANK
SELECT salary FROM (
  SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) as rn
  FROM employees
) WHERE rn = 2;

-- Method 3: OFFSET (PostgreSQL)
SELECT DISTINCT salary FROM employees
ORDER BY salary DESC LIMIT 1 OFFSET 1;
```

## Nth Highest Salary

```sql
-- Using DENSE_RANK
SELECT salary FROM (
  SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) as rn
  FROM employees
) WHERE rn = N;

-- Using correlated subquery
SELECT DISTINCT salary FROM employees e1
WHERE N - 1 = (
  SELECT COUNT(DISTINCT salary) FROM employees e2
  WHERE e2.salary > e1.salary
);
```

## Find Duplicate Records

```sql
-- Find duplicate emails
SELECT email, COUNT(*) as cnt
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Find all rows with duplicates
SELECT * FROM users
WHERE email IN (
  SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1
);

-- Delete duplicates (keep lowest id)
DELETE FROM users WHERE id NOT IN (
  SELECT MIN(id) FROM users GROUP BY email
);
```

## Top N Per Group

```sql
-- Top 3 highest-paid employees per department
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY department_id ORDER BY salary DESC
  ) as rn
  FROM employees
) WHERE rn <= 3;

-- Using DENSE_RANK (handles ties)
SELECT * FROM (
  SELECT *, DENSE_RANK() OVER (
    PARTITION BY department_id ORDER BY salary DESC
  ) as rn
  FROM employees
) WHERE rn <= 3;
```

## Running Totals

```sql
-- Running total of sales
SELECT date, amount,
  SUM(amount) OVER (ORDER BY date) as running_total
FROM sales;

-- Running total per category
SELECT category, date, amount,
  SUM(amount) OVER (PARTITION BY category ORDER BY date) as running_total
FROM sales;
```

## Gaps and Islands

```sql
-- Find gaps in sequential IDs
SELECT id + 1 as gap_start,
  next_id - 1 as gap_end
FROM (
  SELECT id, LEAD(id) OVER (ORDER BY id) as next_id
  FROM sequences
) WHERE next_id - id > 1;

-- Islands: consecutive sequences
SELECT MIN(id) as island_start, MAX(id) as island_end
FROM (
  SELECT id, id - ROW_NUMBER() OVER (ORDER BY id) as grp
  FROM sequences
) GROUP BY grp;
```

## Year-Over-Year Growth

```sql
SELECT year, revenue,
  LAG(revenue) OVER (ORDER BY year) as prev_year,
  ROUND((revenue - LAG(revenue) OVER (ORDER BY year)) * 100.0
        / LAG(revenue) OVER (ORDER BY year), 2) as growth_pct
FROM yearly_revenue;
```

## Consecutive Days Login

```sql
-- Find users who logged in 3+ consecutive days
SELECT user_id FROM (
  SELECT user_id, login_date,
    login_date - INTERVAL ROW_NUMBER() OVER (
      PARTITION BY user_id ORDER BY login_date
    ) DAY as grp
  FROM logins
) GROUP BY user_id, grp
HAVING COUNT(*) >= 3;
```

## Interview Questions

**Q: What is the difference between RANK, DENSE_RANK, and ROW_NUMBER?**
A: `ROW_NUMBER`: unique sequential number (1,2,3,4). `RANK`: gaps after ties (1,2,2,4). `DENSE_RANK`: no gaps (1,2,2,3). Use `DENSE_RANK` for "Nth highest" problems.

**Q: How do you find the median in SQL?**
A: Using PERCENTILE_CONT(0.5) within group (ORDER BY salary). Or: row_number approach where the middle row(s) are selected based on count.

## References

- [LeetCode SQL Problems](https://leetcode.com/problemset/database/)
- [SQL Window Functions — Use The Index, Luke](https://use-the-index-luke.com/sql/window-functions)
