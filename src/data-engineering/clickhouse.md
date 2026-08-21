# ClickHouse

ClickHouse is an open-source columnar database management system, originally developed at Yandex in 2009 and open-sourced in 2016. It is optimized for analytical queries (OLAP) on large datasets, achieving 100-1000× the throughput of traditional databases for aggregations and scans. ClickHouse is widely used for analytics dashboards, log analysis, telemetry, and ad-hoc querying of large datasets. This page covers the columnar storage model, the merge tree engine, the vectorized execution, and the production deployment patterns.

## The Columnar Model

Traditional databases (PostgreSQL, MySQL) store rows: each row's columns are contiguous in storage. ClickHouse stores columns: each column's values are contiguous.

```text
Row-oriented (PostgreSQL):
  Row 1: [id=1, name='Alice', age=30, country='US']
  Row 2: [id=2, name='Bob', age=25, country='UK']
  ...

Column-oriented (ClickHouse):
  Column id:    [1, 2, 3, 4, ...]
  Column name:  ['Alice', 'Bob', ...]
  Column age:   [30, 25, ...]
  Column country: ['US', 'UK', ...]
```

For analytical queries (e.g., `SELECT avg(age) FROM users WHERE country = 'US'`), columnar storage:
- Reads only the `age` and `country` columns (not the unused `id`, `name`).
- Compresses each column independently (numeric columns get 5-10× compression; string columns get 2-5×).
- Enables SIMD-vectorized aggregation (4-32 floats per instruction).

For a 1B-row table with 10 columns, a query reading 2 columns reads 200 MB (columnar) vs 5 GB (row-oriented) — 25× less I/O.

## The MergeTree Engine

The MergeTree is ClickHouse's primary storage engine:

```sql
CREATE TABLE events (
    date Date,
    user_id UInt32,
    event_type String,
    properties Map(String, String)
) ENGINE = MergeTree
PARTITION BY toYYYYMM(date)
ORDER BY (date, user_id, event_type);
```

Key concepts:
- **PARTITION BY**: how data is partitioned (typically by date). Partitions can be dropped (e.g., `ALTER TABLE events DROP PARTITION 202401`).
- **ORDER BY**: the sort order of the primary key. Used for fast lookup by these columns.
- **Data parts**: each partition has multiple parts; parts are merged in the background.

```text
events table:
  Partition 202401/
    Part 202401_1_5/ (merged from parts 1-5)
      primary.idx (sparse primary index)
      date.bin (column 'date' compressed)
      user_id.bin (column 'user_id' compressed)
      ...
    Part 202401_6/ (not yet merged)
  Partition 202402/
    Part 202402_1_3/
```

Each part is independent. Queries can use multiple parts; the merger runs in the background to combine them.

## The Sparse Primary Index

ClickHouse's primary index is sparse: it stores one entry per N rows (default 8192), not per row. This makes the index small (~1 MB for 1B rows) and cache-friendly.

```text
For ORDER BY (date, user_id, event_type):
  primary.idx contents:
    (date=2024-01-01, user_id=1, event_type='login')     → marks 0-8191
    (date=2024-01-01, user_id=1, event_type='logout')    → marks 8192-16383
    (date=2024-01-01, user_id=2, event_type='login')     → marks 16384-24575
    ...

Query: WHERE date = '2024-01-01' AND user_id = 2
  → binary search the primary index → finds mark 16384
  → reads 8192 rows starting at mark 16384
  → filters the 8192 rows by exact predicate
```

For 1B rows: 1B / 8192 = 122K index entries. Each entry is ~16 bytes → 2 MB of index, fits in L2 cache.

## Vectorized Execution

ClickHouse's execution engine processes data in blocks (typically 8192 rows per block) and uses SIMD for the heavy lifting:

```text
SELECT sum(amount) FROM orders WHERE date > '2024-01-01'

Per-block execution:
  1. Read block of 8192 rows.
  2. Filter: SIMD compare date > '2024-01-01' → 8192-bit mask.
  3. Gather: select amount values where mask is set → ~6000 values.
  4. Sum: SIMD sum of 6000 amounts.
  5. Accumulate into per-thread partial sum.
```

The SIMD instructions (AVX2 on x86, NEON on ARM) process 8 floats per instruction. For 6000 floats, that's 750 instructions, executed in microseconds.

## Aggregations

ClickHouse's aggregation is partitioned:
1. Each thread processes a subset of rows.
2. Per-thread hash table aggregates the rows.
3. At the end, the per-thread hash tables are merged into a single result.

For `SELECT user_id, count() FROM events GROUP BY user_id`:
1. Thread 0 processes rows 0-1M, builds local hash table of (user_id, count).
2. Thread 1 processes rows 1M-2M, builds local hash table.
3. ... N threads.
4. Merge N local hash tables into one.

The merge is done in a tree structure (log N levels of merging), keeping memory usage low.

## Performance: ClickHouse vs. Other Databases

| Database | 1B rows, sum aggregation | Type |
|----------|---------------------------:|------|
| PostgreSQL | ~300 seconds | Row-based |
| MySQL | ~280 seconds | Row-based |
| Snowflake (medium warehouse) | ~10 seconds | Columnar |
| BigQuery | ~5 seconds | Columnar |
| ClickHouse (single node, NVMe) | ~2 seconds | Columnar |
| ClickHouse (cluster, 4 nodes) | ~0.5 seconds | Columnar |

ClickHouse's single-node performance is competitive with cloud data warehouses because of:
- Sparse primary index (small, cache-friendly).
- Columnar compression (less I/O).
- Vectorized execution (SIMD).
- No transaction overhead (writes are append-only).

## Distributed ClickHouse

For datasets that exceed a single node, ClickHouse Cluster shards data across multiple nodes:

```sql
CREATE TABLE events_distributed AS events_local
ENGINE = Distributed(cluster_name, db, events_local, rand());

-- Distributed table on each node:
CREATE TABLE events_local AS events
ENGINE = MergeTree ...;

-- Insert goes through the distributed table:
INSERT INTO events_distributed VALUES ...
-- The distributed table fans out to the local tables on each node.
```

The distributed table is a "view" that fans out queries to local tables:
- For aggregations, each node aggregates locally; the distributed table merges the local results.
- For joins, the data may need to be redistributed (broadcast or shuffle).

ClickHouse's cluster is loosely coupled: nodes communicate via ZooKeeper (or ClickHouse Keeper, a ZooKeeper replacement) for cluster metadata.

## Production Use Cases

### Real-time Analytics Dashboards

ClickHouse serves real-time dashboards with sub-second queries over billions of rows. Companies like Cloudflare, Uber, and Bloomberg use ClickHouse for their internal analytics.

### Log Analysis

ClickHouse is a popular backend for log aggregation:
- Vector or Fluent Bit writes logs to ClickHouse.
- Grafana queries ClickHouse for dashboards.

```sql
CREATE TABLE logs (
    timestamp DateTime,
    level String,
    message String,
    service String,
    host String
) ENGINE = MergeTree
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (service, timestamp);
```

### Event Tracking

For application event tracking (clicks, views, conversions):

```sql
CREATE TABLE events (
    user_id UInt64,
    event_type LowCardinality(String),  -- enum-like, compressed
    timestamp DateTime,
    properties String
) ENGINE = MergeTree
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (user_id, timestamp);
```

### Time Series

ClickHouse's high ingestion rate (1M+ rows/sec per node) makes it suitable for time series from IoT, monitoring, etc.

## Common Pitfalls

1. **Using ClickHouse for transactional workloads.** ClickHouse doesn't support per-row UPDATE/DELETE efficiently (mutations are heavy). Use a transactional DB for OLTP; replicate to ClickHouse for analytics.

2. **Forgetting to set the ORDER BY carefully.** The ORDER BY is the primary key; queries not using its prefix are slow. Design the ORDER BY around the most common query patterns.

3. **Forgetting that high-cardinality columns hurt compression.** A column with 1M distinct values (e.g., user IDs) compresses poorly. Use LowCardinality(String) for enum-like columns.

4. **Forgetting that joins are expensive in ClickHouse.** JOIN in ClickHouse materializes both sides; for large joins, use a Dictionary (a pre-loaded lookup table).

5. **Forgetting that inserts should be batched.** Each insert creates a new "part"; too many parts cause "too many parts" errors. Use Buffer tables or batch inserts.

6. **Forgetting that ClickHouse has eventual consistency for new inserts.** A query immediately after an insert may not see the new data; wait for the merge or use `OPTIMIZE TABLE ... FINAL`.

## References

- [ClickHouse documentation](https://clickhouse.com/docs/en/intro/)
- [ClickHouse GitHub repository](https://github.com/ClickHouse/ClickHouse)
- Alexey Milovidov, "[How ClickHouse processes queries](https://clickhouse.com/docs/en/operations/internal/" (ClickHouse blog)
- [ClickHouse MergeTree documentation](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/mergetree/)
- [ClickHouse Performance Guide](https://clickhouse.com/docs/en/operations/monitoring/)
- [ClickHouse vs. Snowflake comparison](https://clickhouse.com/blog/clickhouse-vs-snowflake/)
- [LWN: ClickHouse overview (2020)](https://lwn.net/Articles/820133/)
