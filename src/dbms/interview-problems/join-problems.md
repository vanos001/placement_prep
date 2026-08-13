# SQL Join Interview Problems

Joins combine rows based on a relationship. Interviewers test whether you can
choose the right join, preserve unmatched rows, handle duplicates and nulls,
and explain the cost of the query.

## Join types

| Join | Keeps |
|---|---|
| `INNER JOIN` | Matching rows from both sides |
| `LEFT JOIN` | Every left row plus matching right rows |
| `RIGHT JOIN` | Every right row plus matching left rows |
| `FULL OUTER JOIN` | Every row from both sides |
| `CROSS JOIN` | Cartesian product |
| Self join | A table joined to itself |

## Customers with and without orders

```sql
SELECT c.customer_id, c.name, o.order_id
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL;
```

Do not move the right-side filter into `WHERE` accidentally:

```sql
-- Preserves customers without a qualifying order
SELECT c.customer_id, o.order_id
FROM customers c
LEFT JOIN orders o
  ON o.customer_id = c.customer_id
 AND o.status = 'paid';
```

A predicate on `o.status` in `WHERE` would remove null-extended rows and behave
like an inner join.

## Semi-join and anti-join

Use `EXISTS` when you only need to know whether a related row exists:

```sql
SELECT c.customer_id
FROM customers c
WHERE EXISTS (
  SELECT 1 FROM orders o
  WHERE o.customer_id = c.customer_id
    AND o.created_at >= CURRENT_DATE - INTERVAL '30 days'
);
```

Use `NOT EXISTS` for an anti-join. It usually communicates intent more safely
than `NOT IN`, whose null semantics can produce surprising results.

## Many-to-many joins

A many-to-many relationship needs a junction table:

```sql
SELECT s.student_id, s.name, c.course_id, c.title
FROM students s
JOIN student_courses sc ON sc.student_id = s.student_id
JOIN courses c ON c.course_id = sc.course_id;
```

If you expected one row per student but get duplicates, identify which join
relationship is one-to-many and aggregate or rank deliberately.

## Join performance

The optimizer may choose nested-loop, hash, or merge join based on estimates,
indexes, ordering, and relation sizes. Performance questions require the
actual plan:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...;
```

Useful checks:

- Index join keys used for selective nested loops.
- Statistics are current enough for cardinality estimates.
- Hash joins fit memory or spill predictably.
- A merge join can benefit from existing ordering.
- Functions or casts on join columns **do** prevent index use (unless a matching expression index exists).
- Filters are pushed down without changing outer-join semantics.

## Interview questions

**Why did a LEFT JOIN become an INNER JOIN?**

A `WHERE` predicate on a nullable right-side column removes the null-extended
rows. Put the predicate in the `ON` clause when unmatched left rows must stay.

**How do you find duplicate relationships?**

Group by the supposed unique join key and use `HAVING COUNT(*) > 1`; then inspect
constraints and data model rather than applying `DISTINCT` blindly.

**EXISTS versus JOIN?**

Use `EXISTS` for an existence predicate when right-side columns are not needed.
A join may multiply rows unless the relationship is known to be unique.

**How do nulls affect `NOT IN`?**

If the subquery contains null, three-valued logic can make comparisons unknown.
`NOT EXISTS` with an explicit correlation is usually safer.

## Cross-references

- [SQL](../sql/README.md)
- [Query optimization](../query-processing/optimization.md)
- [Join algorithms](../query-processing/joins.md)
- [Indexes](../indexing/README.md)
- [Window function problems](./window-function-problems.md)

## References

- [PostgreSQL table expressions and joins](https://www.postgresql.org/docs/current/queries-table-expressions.html)
- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [PostgreSQL planner statistics](https://www.postgresql.org/docs/current/planner-stats.html)
