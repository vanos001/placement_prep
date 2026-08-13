# Index Tuning and Best Practices

## Overview

Index tuning is the process of **selecting, creating, and maintaining indexes** to optimize database query performance. The right indexes can speed up queries by orders of magnitude; the wrong ones waste storage, slow down writes, and may not even be used.

## The Index Selection Problem

### What to Index

**Rule of Thumb**: Index columns that appear in:
1. `WHERE` clauses (filtering)
2. `JOIN` conditions (joining tables)
3. `ORDER BY` clauses (sorting)
4. `GROUP BY` clauses (aggregation)
5. `SELECT` columns (for covering indexes)

### What NOT to Index

- Small tables (full scan is fast)
- Columns rarely used in queries
- Columns with very low selectivity (e.g., boolean)
- Columns frequently updated (index maintenance overhead)
- Tables with heavy write loads (be selective)

## Selectivity and Cardinality

### Selectivity

Selectivity = (number of distinct values) / (total number of rows)

```
High selectivity: email column (most values unique)
  1M rows, 999K unique → selectivity = 0.999
  → Excellent for indexing

Low selectivity: gender column (2 values)
  1M rows, 2 unique → selectivity = 0.000002
  → Poor for B-Tree indexing (consider bitmap)
```

### Rule of Thumb

Index a column if the query returns **less than 10-15%** of the total rows. For higher percentages, a full table scan is usually cheaper.

## Analyzing Query Plans

### EXPLAIN and EXPLAIN ANALYZE

```sql
-- Show query plan (estimated)
EXPLAIN SELECT * FROM users WHERE email = 'alice@example.com';

-- Show query plan with actual execution stats
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'alice@example.com';
```

### Reading Query Plans

```
Seq Scan on users  (cost=0.00..15405.00 rows=1 width=528)
  Filter: (email = 'alice@example.com'::text)
  Rows Removed by Filter: 999999

-- This shows a sequential scan (no index used)
-- rows=1 means planner expects 1 matching row
```

### Common Scan Types

| Scan Type | When | Cost |
|---|---|---|
| Seq Scan | No index, or index not selective enough | O(n) |
| Index Scan | Index used, fetches from heap | O(log n + k) |
| Index Only Scan | Index contains all needed columns | O(log n + k) |
| Bitmap Index Scan | Multiple conditions, index combines | O(log n + k) |

## Index Usage Patterns

### 1. Single Column Index

```sql
CREATE INDEX idx_users_email ON users(email);

-- Used for:
SELECT * FROM users WHERE email = 'alice@example.com';
SELECT * FROM users WHERE email LIKE 'alice%';
SELECT * FROM users WHERE email IS NULL;
```

### 2. Composite Index (Multi-Column)

```sql
CREATE INDEX idx_users_name_age ON users(last_name, first_name, age);

-- Used for (leftmost prefix):
SELECT * FROM users WHERE last_name = 'Smith';
SELECT * FROM users WHERE last_name = 'Smith' AND first_name = 'John';
SELECT * FROM users WHERE last_name = 'Smith' AND first_name = 'John' AND age = 30;

-- NOT used for:
SELECT * FROM users WHERE first_name = 'John';  -- Skips leftmost column
SELECT * FROM users WHERE age = 30;  -- Skips leftmost columns
```

### 3. Covering Index

```sql
CREATE INDEX idx_users_covering ON users(email) INCLUDE (name, phone);

-- Index-only scan (no heap access)
SELECT name, phone FROM users WHERE email = 'alice@example.com';
```

## Index Maintenance

### Rebuilding Indexes

Indexes become fragmented over time:

```sql
-- PostgreSQL: Rebuild index
REINDEX INDEX idx_users_email;

-- Rebuild without locking
REINDEX INDEX CONCURRENTLY idx_users_email;

-- MySQL: Optimize table
OPTIMIZE TABLE users;
```

### Monitoring Index Usage

```sql
-- PostgreSQL: Find unused indexes
SELECT 
    schemaname, tablename, indexname,
    idx_scan AS times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Find index bloat
SELECT 
    schemaname, tablename, indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Auto-Explain Slow Queries

```sql
-- PostgreSQL: Log slow queries with plans
SET log_min_duration_statement = 1000;  -- Log queries > 1 second
SET autoexplain.log_min_duration = 1000;
SET autoexplain.log_analyze = true;
```

## Index Tuning Methodology

### Step 1: Identify Slow Queries

```sql
-- PostgreSQL: Top queries by total time
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

### Step 2: Analyze Query Plans

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) 
SELECT * FROM orders 
WHERE customer_id = 12345 
ORDER BY order_date DESC 
LIMIT 10;
```

### Step 3: Identify Missing Indexes

Look for:
- Seq Scan on large tables
- High "Rows Removed by Filter"
- Sort operations that could use an index
- Nested loops with high row counts

### Step 4: Create and Test Indexes

```sql
-- Create index
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date DESC);

-- Test with EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 12345 ORDER BY order_date DESC LIMIT 10;

-- Should now show Index Scan instead of Seq Scan
```

### Step 5: Monitor and Adjust

```sql
-- Check if index is being used
SELECT idx_scan FROM pg_stat_user_indexes 
WHERE indexrelid = 'idx_orders_customer_date'::regclass;
```

## Advanced Index Tuning

### Partial Indexes

```sql
-- Only index active users
CREATE INDEX idx_active_users ON users(email) WHERE active = true;

-- Only index recent orders
CREATE INDEX idx_recent_orders ON orders(customer_id, order_date) 
WHERE order_date > '2023-01-01';
```

### Expression Indexes

```sql
-- Index on lowercased email
CREATE INDEX idx_users_lower_email ON users(lower(email));

-- Index on extracted year
CREATE INDEX idx_orders_year ON orders(extract(year FROM order_date));

-- Used by:
SELECT * FROM users WHERE lower(email) = 'alice@example.com';
```

### Index-Only Scans

```sql
-- Include all columns needed by the query
CREATE INDEX idx_orders_covering ON orders(customer_id, order_date) 
INCLUDE (total_amount, status);

-- This query can use index-only scan
SELECT order_date, total_amount, status 
FROM orders 
WHERE customer_id = 12345;
```

## Common Index Anti-Patterns

### 1. Over-Indexing

```
Problem: Too many indexes on a table
Impact: Slower INSERT/UPDATE/DELETE, more storage, slower backups
Solution: Remove unused indexes, use covering indexes
```

### 2. Index on Every Column

```
Problem: Each column gets its own index
Impact: Wastes space, optimizer may choose wrong index
Solution: Use composite indexes, covering indexes
```

### 3. Not Considering Write Patterns

```
Problem: Heavy indexing on write-heavy tables
Impact: Writes become slow
Solution: Be selective, consider partial indexes
```

### 4. Ignoring Index Order

```
Problem: Composite index on (A, B) but queries filter on B alone
Impact: Index not used for B-only queries
Solution: Create separate index on B, or reorder composite index
```

### 5. Not Updating Statistics

```
Problem: Stale statistics lead to poor index choices
Impact: Optimizer chooses Seq Scan when Index Scan is better
Solution: Run ANALYZE regularly, enable autovacuum
```

## Interview Questions

### Beginner

**Q1: How do you know if a query needs an index?**
A: Run EXPLAIN ANALYZE. If you see Seq Scan on a large table and the query filters on a column, consider adding an index. Also check if the query returns a small percentage of rows (<10-15%).

**Q2: What is the difference between EXPLAIN and EXPLAIN ANALYZE?**
A: EXPLAIN shows the estimated query plan without executing. EXPLAIN ANALYZE actually executes the query and shows real timing, row counts, and buffers. Use EXPLAIN ANALYZE for accurate analysis.

**Q3: When should you NOT create an index?**
A: On small tables, low-selectivity columns, frequently updated columns, or write-heavy tables where the index maintenance cost outweighs the read benefit.

### Intermediate

**Q4: What is a covering index?**
A: An index that contains all columns needed by a query, allowing an index-only scan without accessing the heap. Created using INCLUDE clause: `CREATE INDEX ... ON table(col) INCLUDE (other_cols)`.

**Q5: How do you find unused indexes?**
A: Query `pg_stat_user_indexes` for indexes with `idx_scan = 0`. These indexes are never used by queries and waste space and write performance.

**Q6: What is the impact of indexes on write performance?**
A: Each INSERT must update all indexes on the table. UPDATE must update indexes on changed columns. DELETE must mark index entries as deleted. More indexes = slower writes. The impact can be 2-5x slowdown for heavily indexed tables.

### Advanced / FAANG-Level

**Q7: You have a table with 100M rows. A critical query takes 30 seconds. How do you tune it?**
A: (1) EXPLAIN ANALYZE to identify the bottleneck. (2) Check for Seq Scan — add appropriate index. (3) Check for Sort — add index on ORDER BY columns. (4) Check for Nested Loop — consider composite index to avoid repeated lookups. (5) Consider covering index for index-only scan. (6) Consider table partitioning if the query filters by time range. (7) Consider materialized view for complex aggregations. (8) Check for outdated statistics — run ANALYZE.

**Q8: Design an indexing strategy for a social media platform with 1B users and queries like "get recent posts from users I follow."**
A: (1) Index on follows(follower_id, following_id) for finding who I follow. (2) Composite index on posts(user_id, created_at DESC) for getting recent posts per user. (3) Consider a materialized view or cache for the feed (pre-computed). (4) For real-time feeds, use a fan-out-on-write approach with a pre-computed feed table. (5) Use covering indexes for common query patterns. (6) Partition posts table by time range.

**Q9: A query uses a composite index on (A, B, C) but the optimizer chooses a different plan. What could be wrong?**
A: (1) Statistics are stale — run ANALYZE. (2) The query filters on B without A — index can't be used efficiently. (3) Correlation between columns — planner overestimates selectivity. (4) Index is fragmented — run REINDEX. (5) Work_mem is too low for the sort needed. (6) Random page cost is too high — adjust for SSD. (7) The planner prefers parallel scan over index scan for large result sets.

## Common Mistakes

1. **Not using EXPLAIN ANALYZE** — Always verify that your indexes are actually being used.

2. **Creating indexes without analyzing query patterns** — Index the queries you actually run, not every column.

3. **Ignoring index bloat** — Fragmented indexes waste space and slow scans. Monitor and rebuild.

4. **Not considering composite index order** — Leftmost prefix rule: (A, B, C) can satisfy queries on A, (A, B), or (A, B, C), but not B alone or C alone.

5. **Over-indexing small tables** — A table with 1000 rows doesn't need indexes. Full scan is fast.

## Summary

| Aspect | Detail |
|---|---|
| Goal | Optimize query performance with minimal overhead |
| Key tools | EXPLAIN ANALYZE, pg_stat_statements, pg_stat_user_indexes |
| Index selection | High-selectivity columns in WHERE/JOIN/ORDER BY |
| Maintenance | Monitor usage, rebuild when fragmented |
| Anti-patterns | Over-indexing, ignoring write impact, stale statistics |

## Cross-References

- [B+ Tree](./b-plus-tree.md) — Most common index structure
- [Composite Index](./composite-index.md) — Multi-column indexes
- [Covering Index](./covering-index.md) — Index-only scans
- [Clustered vs Non-Clustered](./clustered-vs-nonclustered.md) — Physical ordering
- [Hash Index](./hash-index.md) — For exact lookups


## Cross References

- [Query Optimization](../query-processing/optimization.md)
- [B+ Tree](b-plus-tree.md)
- [Composite Index](composite-index.md)
- [Execution Plans](../query-processing/execution-plans.md)
