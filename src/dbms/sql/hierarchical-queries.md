# Hierarchical Queries

Hierarchical (recursive) queries traverse tree-structured data — organizational charts, category trees, bill of materials, comment threads. Different databases provide different syntax, but the patterns are universal.

## Data Models for Hierarchies

| Model | Structure | Example | Typical Query
|---|---|---|---|
| Adjacency List | Each row stores `parent_id` | `employees.manager_id` | Recursive CTE
| Materialized Path | Store full path (e.g., `/1/4/9/`) | Categories | `LIKE '/1/4/%'` or `@>` in PostgreSQL
| Nested Sets | Store `lft`/`rgt` bounds | File systems | `BETWEEN lft AND rgt` |
| Closure Table | Separate table of all ancestor-descendant pairs | Any hierarchy | Simple JOIN

## Recursive CTEs (Standard SQL)

Recursive CTEs are the ANSI SQL standard for adjacency list traversal:

```sql
-- Org chart: find all descendants of manager_id = 5
WITH RECURSIVE org_tree AS (
    -- Base case: the root node
    SELECT employee_id, name, manager_id, 1 AS level
    FROM employees
    WHERE employee_id = 5

    UNION ALL

    -- Recursive case: join children
    SELECT e.employee_id, e.name, e.manager_id, t.level + 1
    FROM employees e
    JOIN org_tree t ON e.manager_id = t.employee_id
)
SELECT * FROM org_tree;
```

### Aggregating Up a Hierarchy

```sql
-- Roll up salary costs to each manager
WITH RECURSIVE hierarchy AS (
    SELECT employee_id, name, manager_id, salary, 0 AS depth
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.name, e.manager_id, e.salary, h.depth + 1
    FROM employees e JOIN hierarchy h ON e.manager_id = h.employee_id
)
SELECT h.employee_id, h.name, h.depth,
       (SELECT SUM(salary) FROM hierarchy sub WHERE sub.employee_id = h.employee_id
        OR sub.manager_id = h.employee_id) AS total_cost
FROM hierarchy h;
```

## Oracle: CONNECT BY

Oracle provides `CONNECT BY` syntax, which some find more intuitive:

```sql
SELECT employee_id, name, manager_id, LEVEL
FROM employees
CONNECT BY PRIOR employee_id = manager_id
START WITH manager_id IS NULL;
```

| Feature | Recursive CTE | CONNECT BY |
|---|---|---|
| Standard | ANSI SQL | Oracle-only |
| Direction | Any (change JOIN) | `PRIOR` column side determines direction |
| Cycle detection | Manual (`CYCLE` clause) | `NOCYCLE` keyword |
| Ordering | Explicit `ORDER BY` | `ORDER SIBLINGS BY` |

## Materialized Path Pattern

```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name TEXT,
    path TEXT  -- e.g., '/1/4/9/'
);

-- All descendants of category 4
SELECT * FROM categories WHERE path LIKE '/1/4/%';

-- Ancestors (PostgreSQL array ops)
SELECT * FROM categories
WHERE '/1/4/9/' LIKE path || '%';
```

Materialized paths make subtree queries fast (index on `path`) but updates are expensive when a node moves.

## Performance Tips

- **Index the parent column** — critical for recursive CTE performance
- **Limit depth** — add `WHERE level <= N` to prevent runaway recursion
- **Beware cycles** — use `CYCLE` clause (PostgreSQL/ISO SQL) or `NOCYCLE` (Oracle) to detect circular references
- **Consider closure tables** for frequent hierarchy queries — precomputed ancestor pairs eliminate recursion at query time

## Interview Questions

**Q1: What is a recursive CTE and when do you need one?**
A: A recursive CTE references itself in the `FROM` clause of a UNION ALL. It has a base case (anchor member) and a recursive case that joins to the CTE itself. Used whenever data has parent-child relationships — org charts, comment threads, bill of materials.

**Q2: How do you prevent infinite recursion in a hierarchical query?**
A: Use the `CYCLE` clause (PostgreSQL) to mark visited rows and stop recursion: `CYCLE employee_id SET is_cycle USING path`. Alternatively, add a depth limit (`WHERE level <= 100`) as a safety bound.

**Q3: Compare adjacency list vs nested sets for a product category tree with frequent reads and rare updates.**
A: Nested sets are excellent for read-heavy hierarchies — subtree queries use `BETWEEN lft AND rgt` (range scan on B-tree). However, inserts and moves require recalculating bounds for the entire subtree (O(N) update). For a category tree with rare updates, nested sets may outperform adjacency list for deep subtree reads.

**Q4: How would you find the shortest path between two nodes in a graph using SQL?**
A: Use a recursive CTE that tracks visited nodes and the path length, stopping when the target is reached:

```sql
WITH RECURSIVE bfs AS (
    SELECT start_node, ARRAY[start_node], 0 AS dist
    UNION ALL
    SELECT e.to_node, path || e.to_node, dist + 1
    FROM edges e JOIN bfs ON e.from_node = bfs.current
    WHERE e.to_node != ALL(path)  -- avoid cycles
)
SELECT path, dist FROM bfs WHERE current = target_node
ORDER BY dist LIMIT 1;
```

## Cross-References

- [CTEs](ctes.md) — Non-recursive CTEs and general patterns
- [Window Functions](window-functions.md) — Level-based calculations in hierarchies
- [Subqueries](subqueries.md) — Correlated subqueries for parent lookups
- [Query Planner](../query-planner.md) — How optimizers handle recursive CTEs

## References

- [PostgreSQL: Recursive Queries](https://www.postgresql.org/docs/current/queries-with.html)
- [Oracle: Hierarchical Queries](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Hierarchical-Queries.html)
- [SQL Antipatterns — Bill Karwin](https://www.sqlantiPatterns.com/) (Chapter on Trees)