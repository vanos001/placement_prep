# SQL Interview Rounds

SQL rounds evaluate database design ability, query optimization, and analytical thinking. They appear in data engineering, backend, analytics, and SRE interviews.

## Common Round Formats

| Format | Duration | Focus |
|--------|----------|-------|
| Schema Design | 30-45 min | ER diagrams, normalization, indexing |
| Query Writing | 20-30 min | JOINs, subqueries, aggregations |
| Optimization | 20-30 min | EXPLAIN plans, indexing strategies |
| Analytical | 30-45 min | Window functions, CTEs, business metrics |

## Schema Design

Interviewers present a business scenario and ask you to design tables.

**Example:** Design a schema for a ride-sharing app.

```sql
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rides (
    ride_id BIGINT PRIMARY KEY,
    rider_id BIGINT REFERENCES users(user_id),
    driver_id BIGINT REFERENCES users(user_id),
    start_location GEOGRAPHY,
    end_location GEOGRAPHY,
    fare DECIMAL(10,2),
    status VARCHAR(20) CHECK (status IN ('requested','in_progress','completed','cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rides_rider ON rides(rider_id, created_at);
CREATE INDEX idx_rides_driver ON rides(driver_id, status);
```

**Tips:** Discuss normalization vs denormalization trade-offs. Explain index choices. Mention partitioning for large tables.

## Window Functions

Window functions are the most frequently tested advanced SQL topic.

**Pattern 1: Running totals**
```sql
SELECT order_date, amount,
    SUM(amount) OVER (ORDER BY order_date) AS running_total
FROM orders;
```

**Pattern 2: Rank with gaps**
```sql
SELECT employee_id, department, salary,
    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank
FROM employees;
```

**Pattern 3: Year-over-year growth**
```sql
SELECT year, revenue,
    LAG(revenue) OVER (ORDER BY year) AS prev_revenue,
    (revenue - LAG(revenue) OVER (ORDER BY year)) * 100.0
        / LAG(revenue) OVER (ORDER BY year) AS yoy_growth_pct
FROM annual_revenue;
```

| Function | Skips Ties? | Tie Handling |
|----------|-------------|--------------|
| ROW_NUMBER() | No | Each row gets unique number |
| RANK() | Yes | Same rank, next rank skips |
| DENSE_RANK() | No | Same rank, no skip |

## Common Table Expressions (CTEs)

CTEs improve readability and enable recursive queries.

```sql
WITH monthly_active AS (
    SELECT DATE_TRUNC('month', login_date) AS month,
           COUNT(DISTINCT user_id) AS mau
    FROM user_logins
    GROUP BY 1
),
prev_month AS (
    SELECT month, LAG(mau) OVER (ORDER BY month) AS prev_mau
    FROM monthly_active
)
SELECT m.month, m.mau, p.prev_mau,
    (m.mau - p.prev_mau) * 100.0 / NULLIF(p.prev_mau, 0) AS growth_pct
FROM monthly_active m
JOIN prev_month p ON m.month = p.month;
```

## Optimization Patterns

- Add indexes on columns in WHERE, JOIN, and ORDER BY clauses.
- Use covering indexes to avoid table lookups.
- Avoid SELECT ; specify only needed columns.
- Use EXPLAIN ANALYZE to identify sequential scans.
- Prefer UNION ALL over UNION when duplicates are acceptable.
- Use LIMIT early in subqueries to reduce intermediate result size.

## Practice Questions

**Q1:** Find the second-highest salary per department.
```sql
SELECT department, salary
FROM (
    SELECT department, salary,
           DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rnk
    FROM employees
) ranked
WHERE rnk = 2;
```

**Q2:** Find users who logged in on 3 consecutive days.
```sql
WITH numbered AS (
    SELECT user_id, login_date,
           DATE(login_date) - INTERVAL '1 day' * 
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS grp
    FROM (SELECT DISTINCT user_id, DATE(login_date) AS login_date FROM logins) d
)
SELECT user_id, MIN(login_date) AS streak_start, COUNT(*) AS streak_days
FROM numbered
GROUP BY user_id, grp
HAVING COUNT(*) >= 3;
```

## Cross-references

- [Technical interview preparation](./technical-interview.md)
- [Online assessments](./online-assessment.md)
- [Database internals](../dbms/)