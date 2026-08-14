# Correlated Subqueries

A correlated subquery references columns from the outer query and is **re-evaluated for each row** processed by the outer query. Understanding the performance difference between correlated and uncorrelated subqueries—and when to rewrite them—is essential for writing efficient SQL.

## Correlated vs Uncorrelated

| Aspect | Uncorrelated | Correlated |
|---|---|---|
| References outer query | No | Yes |
| Execution | Evaluated once | Evaluated per outer row |
| Independence | Can run standalone | Depends on outer row |
| Performance | Typically O(1) subquery evals | O(N) subquery evals (N+1 problem) |

## Examples

### Correlated: Find employees earning above their department average

```sql
SELECT e.name, e.department, e.salary
FROM employees e
WHERE e.salary > (
    SELECT AVG(e2.salary)
    FROM employees e2
    WHERE e2.department = e.department  -- correlated reference
);
```

This executes the inner query once for **every row** in `employees`. With 10,000 employees, that is 10,000 subquery executions.

### Uncorrelated: Find employees earning above the company average

```sql
SELECT name, salary
FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees);
```

The inner query executes **once** and its result is used for all outer rows.

## Rewriting to Joins

Correlated subqueries often have equivalent join-based rewrites that are significantly faster because they allow the optimizer to use hash or merge join strategies:

```sql
-- Original correlated subquery
SELECT e.name, e.department, e.salary
FROM employees e
WHERE e.salary > (
    SELECT AVG(e2.salary)
    FROM employees e2
    WHERE e2.department = e.department
);

-- Rewrite 1: JOIN with pre-aggregated subquery
SELECT e.name, e.department, e.salary
FROM employees e
JOIN (
    SELECT department, AVG(salary) AS dept_avg
    FROM employees
    GROUP BY department
) d ON e.department = d.department
WHERE e.salary > d.dept_avg;

-- Rewrite 2: Window function (often most efficient)
SELECT name, department, salary
FROM (
    SELECT name, department, salary,
           AVG(salary) OVER (PARTITION BY department) AS dept_avg
    FROM employees
) sub
WHERE salary > dept_avg;
```

## EXISTS and NOT EXISTS

`EXISTS` with a correlated subquery is a **semi-join** — it returns true as soon as the subquery finds one matching row, making it efficient:

```sql
-- Customers who have placed at least one order
SELECT c.name
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.customer_id
);

-- Customers with NO orders (anti-join)
SELECT c.name
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.customer_id
);
```

Most modern optimizers automatically convert `EXISTS`/`NOT EXISTS` to semi-joins and anti-joins internally.

## Performance Considerations

- **Index the correlated column** — the inner query filters on `e2.department = e.department`; an index on `department` eliminates full scans
- **Check `EXPLAIN`** — verify the optimizer decorrelates the subquery (converts to a join plan)
- **Prefer window functions** for intra-row comparisons — single pass over data
- **Avoid correlated subqueries in SELECT** — each one executes per row:

```sql
-- BAD: two correlated subqueries per row
SELECT name,
    (SELECT COUNT(*) FROM orders o WHERE o.emp_id = e.emp_id) AS order_count,
    (SELECT SUM(amount) FROM orders o WHERE o.emp_id = e.emp_id) AS total_amount
FROM employees e;

-- GOOD: single lateral join or window function
SELECT e.name, o.order_count, o.total_amount
FROM employees e
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS order_count, SUM(amount) AS total_amount
    FROM orders o WHERE o.emp_id = e.emp_id
) o ON true;
```

## Interview Questions

**Q1: Why are correlated subqueries typically slower?**
A: Because they execute once for each row of the outer query (O(N) evaluations). Each execution may involve a full or partial scan unless indexed. Uncorrelated subqueries evaluate once (O(1)), and join rewrites allow the optimizer to choose hash or merge joins.

**Q2: When is a correlated subquery actually efficient?**
A: With `EXISTS`/`NOT EXISTS` — the subquery short-circuits on the first match. If there is an index on the correlated column, each lookup is O(log N), and the optimizer often converts these to semi-joins anyway.

**Q3: How does the query optimizer handle correlated subqueries?**
A: Modern optimizers attempt **subquery decorrelation** (unnesting): they rewrite correlated subqueries into equivalent joins (semi-join for EXISTS, anti-join for NOT EXISTS, LEFT JOIN for scalar correlated). When decorrelation fails (complex predicates, LIMIT, aggregates), the optimizer falls back to nested loop evaluation.

**Q4: Rewrite this correlated subquery using a window function:**
```sql
SELECT * FROM products p
WHERE price = (SELECT MAX(price) FROM products p2 WHERE p2.category = p.category);
```
A:
```sql
SELECT * FROM (
    SELECT *, MAX(price) OVER (PARTITION BY category) AS cat_max
    FROM products
) sub
WHERE price = cat_max;
```

## Cross-References

- [Subqueries](subqueries.md) — General subquery types and patterns
- [Joins](joins.md) — Join strategies that replace subqueries
- [Window Functions](window-functions.md) — Modern alternative to correlated subqueries
- [Indexes](indexes.md) — Indexing correlated columns for performance
- [Query Planner](../query-planner.md) — How the optimizer decorrelates subqueries

## References

- [PostgreSQL: Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html)
- [MySQL: Optimizing Subqueries](https://dev.mysql.com/doc/refman/8.0/en/optimizing-subqueries.html)
