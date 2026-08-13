# Query Optimization Problems

## Reading Execution Plans

```sql
EXPLAIN ANALYZE
SELECT e.name, d.department_name
FROM employees e
JOIN departments d ON e.department_id = d.id
WHERE e.salary > 50000;
```

Key metrics in execution plans:
- **Seq Scan**: Full table scan (bad for large tables with selective filter)
- **Index Scan**: Uses index (good)
- **Index Only Scan**: All needed columns in index (best)
- **Nested Loop**: Good for small datasets
- **Hash Join**: Good for medium datasets
- **Merge Join**: Good for large sorted datasets

## Common Optimization Patterns

### 1. Missing Index

```sql
-- Slow: Seq scan on 1M rows
SELECT * FROM orders WHERE customer_id = 123;

-- Fix: Add index
CREATE INDEX idx_orders_customer ON orders(customer_id);
```

### 2. SELECT * vs Specific Columns

```sql
-- Bad: fetches all columns
SELECT * FROM users WHERE id = 1;

-- Better: only needed columns
SELECT name, email FROM users WHERE id = 1;

-- Best: covering index
CREATE INDEX idx_users_name_email ON users(id) INCLUDE (name, email);
```

### 3. N+1 Query Problem

```sql
-- Bad: 1 query for orders + N queries for items
SELECT * FROM orders;
-- Then for each order:
SELECT * FROM order_items WHERE order_id = ?;

-- Better: JOIN
SELECT o.*, oi.*
FROM orders o
JOIN order_items oi ON o.id = oi.order_id;

-- Better: IN clause
SELECT * FROM order_items WHERE order_id IN (SELECT id FROM orders);
```

### 4. Subquery vs JOIN

```sql
-- Correlated subquery (slow: runs for each row)
SELECT * FROM employees e
WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept = e.dept);

-- Better: JOIN with pre-computed average
SELECT e.* FROM employees e
JOIN (SELECT dept, AVG(salary) as avg_sal FROM employees GROUP BY dept) d
ON e.dept = d.dept AND e.salary > d.avg_sal;
```

### 5. LIKE with Leading Wildcard

```sql
-- Bad: Can't use index
SELECT * FROM users WHERE name LIKE '%smith';

-- If frequent, use full-text search
CREATE INDEX idx_users_name_fts ON users USING gin(to_tsvector('english', name));
```

## Index Strategy

### When to Create an Index
- High-cardinality columns (many unique values)
- Columns in WHERE, JOIN, ORDER BY, GROUP BY
- Selective queries (< 10% of rows returned)

### When NOT to Create an Index
- Small tables (< 1000 rows)
- Low-cardinality columns (boolean, status with few values)
- Frequently updated columns (index maintenance cost)
- Wide columns (index size too large)

### Composite Index Order

```sql
-- Index on (a, b, c) can serve:
-- WHERE a = 1
-- WHERE a = 1 AND b = 2
-- WHERE a = 1 AND b = 2 AND c = 3
-- But NOT: WHERE b = 2 (without a)

-- Rule: most selective column first, or match query patterns
```

## Interview Questions

**Q: How would you optimize a slow query?**
A: (1) Run EXPLAIN ANALYZE, (2) check for full table scans, (3) add appropriate indexes, (4) avoid SELECT *, (5) check for N+1 queries, (6) consider denormalization, (7) check if caching helps.

**Q: What is a covering index?**
A: An index that contains all columns needed by the query. The database can answer the query from the index alone without touching the table. Created with `INCLUDE` clause or by adding columns to the index.

**Q: Explain the N+1 query problem and how to fix it.**
A: Fetching a list of items (1 query), then fetching related data for each item (N queries). Fix with: JOIN, IN clause, eager loading (ORM), or batch loading (DataLoader in GraphQL).

## References

- [Use The Index, Luke — Markus Winand](https://use-the-index-luke.com/)
- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
