# NULL Semantics in SQL

NULL is not a value — it represents **unknown or missing information**. SQL's three-valued logic (TRUE, FALSE, UNKNOWN) makes NULL behave counterintuitively, and misunderstanding it is a common source of bugs in queries and application code.

## Three-Valued Logic

Every comparison or logical operation involving NULL yields **UNKNOWN** (not TRUE, not FALSE):

| Expression | Result |
|---|---|
| `NULL = NULL` | UNKNOWN |
| `NULL <> NULL` | UNKNOWN |
| `NULL > 5` | UNKNOWN |
| `NULL AND TRUE` | UNKNOWN |
| `NULL AND FALSE` | FALSE |
| `NULL OR TRUE` | TRUE |
| `NULL OR FALSE` | UNKNOWN |
| `NOT NULL` | UNKNOWN |

The key insight: `NULL AND FALSE` is FALSE (not UNKNOWN) because AND requires all operands to be TRUE. `NULL OR TRUE` is TRUE because OR needs only one TRUE operand.

## NULL vs Empty String

`NULL` means the value is unknown or not applicable. An empty string (`''`) is a known value — the string of zero length. They are distinct:

```sql
-- PostgreSQL (strict behavior)
SELECT NULL = '';           -- NULL (UNKNOWN)
SELECT NULL IS NULL;        -- TRUE
SELECT '' IS NULL;          -- FALSE
SELECT '' IS NOT NULL;      -- TRUE
```

> **Oracle exception:** Oracle treats `''` as NULL by default (`VARCHAR2` semantics). This is non-standard and a common source of confusion when migrating queries.

## NULL in WHERE Clauses

The WHERE clause only returns rows where the condition evaluates to **TRUE**. Rows where the condition is UNKNOWN (due to NULL) are excluded:

```sql
SELECT * FROM products WHERE price > 100;
-- Excludes rows where price IS NULL

-- To include NULLs, handle explicitly:
SELECT * FROM products WHERE price > 100 OR price IS NULL;
```

## NULL in Aggregates

Aggregate functions generally **ignore NULL** values:

```sql
CREATE TABLE sales (amount INT);
INSERT INTO sales VALUES (100), (200), NULL, (300);

SELECT COUNT(*) FROM sales;        -- 4 (counts all rows)
SELECT COUNT(amount) FROM sales;   -- 3 (ignores NULL)
SELECT SUM(amount) FROM sales;     -- 600 (ignores NULL)
SELECT AVG(amount) FROM sales;     -- 200.0 (600 / 3, not 600 / 4)
```

| Function | Ignores NULL? | Notes |
|---|---|---|
| `COUNT(*)` | No | Counts rows |
| `COUNT(col)` | Yes | Counts non-NULL values |
| `SUM`, `AVG`, `MIN`, `MAX` | Yes | Operates on non-NULL values |
| `GROUP_CONCAT` / `STRING_AGG` | Yes | Excludes NULL |

## NULL in JOINs and NOT IN

A critical pitfall: `NOT IN` with a subquery containing NULLs returns **zero rows**:

```sql
-- If ANY value in the subquery is NULL, the entire result is empty
SELECT name FROM customers
WHERE id NOT IN (SELECT customer_id FROM orders);
-- Returns no rows if orders.customer_id has ANY NULL

-- Safe alternatives:
SELECT name FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);
```

The reason: `NOT IN (1, 2, NULL)` becomes `id <> 1 AND id <> 2 AND id <> NULL`. Since `id <> NULL` is UNKNOWN, the entire AND expression is UNKNOWN for every row.

## COALESCE and NULLIF

```sql
-- COALESCE: first non-NULL value
SELECT COALESCE(nickname, first_name, 'Unknown') AS display_name
FROM users;

-- NULLIF: returns NULL if two values are equal
SELECT NULLIF(status, 'pending') AS resolved_status
FROM orders;  -- returns NULL when status is 'pending'
```

## Interview Questions

**Q1: Why does `NULL = NULL` return UNKNOWN, not TRUE?**
A: Because NULL represents unknown information. If two values are both unknown, you cannot determine whether they are equal. Treating NULL = NULL as TRUE would incorrectly conflate distinct unknowns. Use `IS NULL` / `IS NOT NULL` to check for NULL.

**Q2: Why does `NOT IN` with NULLs return no rows?**
A: `NOT IN (1, 2, NULL)` expands to `col <> 1 AND col <> 2 AND col <> NULL`. The last condition is UNKNOWN, making the entire AND expression UNKNOWN. Since WHERE filters on TRUE only, no rows pass. Use `NOT EXISTS` instead.

**Q3: What is the difference between `COUNT(*)` and `COUNT(column)`?**
A: `COUNT(*)` counts all rows regardless of NULLs. `COUNT(column)` counts only rows where that column is not NULL. This distinction matters when columns contain NULL values — `COUNT(*)` may be larger.

**Q4: How does NULL affect UNIQUE constraints?**
A: In most databases (PostgreSQL, MySQL, SQL Server), multiple NULL values **are allowed** in a UNIQUE column — NULLs are not considered equal to each other. The exception is some interpretations of the SQL standard. This means a UNIQUE index on `email` will allow multiple rows with `email = NULL`.

## Cross-References

- [Subqueries](sql/subqueries.md) — NOT IN with NULLs pitfall
- [Correlated Subqueries](sql/correlated-subqueries.md) — EXISTS handles NULLs safely
- [Joins](sql/joins.md) — NULL behavior in outer joins
- [Normalization](normalization/1nf.md) — NULL and first normal form
- [Transactions](transactions/acid.md) — NULL in write operations

## References

- [PostgreSQL: Null Handling](https://www.postgresql.org/docs/current/functions-comparison.html)
- [SQL NULLs — Wikipedia](https://en.wikipedia.org/wiki/Null_(SQL))
- [NULLs and Three-Valued Logic — use-the-index-luke.com](https://use-the-index-luke.com/sql/no-null)
