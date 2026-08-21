# Trino (formerly PrestoSQL)

Trino is an open-source distributed SQL query engine, originally developed at Facebook in 2012 as Presto, renamed Trino in 2020 after a community fork. Trino is designed for ad-hoc analytical queries across federated data sources (multiple databases, object storage, file formats), without moving data. This page covers the architecture, the federated query model, the cost-based optimizer, and the production use cases.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Coordinator (single, HA via standby)                       │
│  - Parses SQL, generates plan                               │
│  - Optimizes plan (rule-based + cost-based)                │
│  - Schedules tasks on workers                              │
│  - Merges results from workers                            │
└─────────────────────────────────────────────────────────────┘
        │                              │
        │ task assignment              │ result fetch
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Worker 1             │    │  Worker 2             │
│  - Reads from data    │    │  - Reads from data    │
│    sources            │    │    sources             │
│  - Executes plan      │    │  - Executes plan      │
│    stages             │    │    stages              │
└──────────────────────┘    └──────────────────────┘
        │                              │
        ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Data Sources (via connectors)                              │
│  - Hive (HDFS, S3, Parquet)                                │
│  - MySQL, PostgreSQL, Oracle, etc.                          │
│  - Kafka, Elasticsearch, etc.                              │
└─────────────────────────────────────────────────────────────┘
```

The coordinator is the brain; workers do the execution. Data sources are accessed via "connectors" — pluggable modules that know how to read from a specific source.

## Connectors: Federated Queries

Trino's key feature: query across multiple data sources in a single SQL statement.

```sql
-- Join data from Hive (S3) and PostgreSQL
SELECT 
    h.user_id, 
    h.event_type, 
    u.country
FROM hive.events h
JOIN postgres.users u ON h.user_id = u.id
WHERE h.date >= '2024-01-01';

-- Union across multiple PostgreSQL shards
SELECT * FROM postgres_eu.users
UNION ALL
SELECT * FROM postgres_us.users
UNION ALL
SELECT * FROM postgres_apac.users;
```

A connector exposes:
- **Schemas**: logical grouping (e.g., databases in PostgreSQL).
- **Tables**: queryable objects (e.g., PostgreSQL tables, Hive tables, Kafka topics).
- **Statistics**: row count, column stats — used by the cost-based optimizer.
- **Pushdown**: which predicates the connector can evaluate (e.g., `WHERE date > X` pushed down to PostgreSQL).

Trino's connectors are widely deployed:
- **Hive connector**: reads Parquet, ORC, Avro from S3/HDFS.
- **PostgreSQL/MySQL/Oracle/etc.**: federated queries to transactional DBs.
- **Kafka**: queries Kafka topics as tables (each topic = a table, each message = a row).
- **Iceberg/Delta Lake/Hudi**: reads lakehouse table formats.
- **Elasticsearch**: queries ES indices.
- **Cassandra, MongoDB, Redis**: NoSQL databases.

## The Query Plan

Trino's optimizer produces a distributed plan:

```text
SQL: SELECT region, SUM(amount) FROM hive.orders WHERE date > '2024-01-01' GROUP BY region;

Coordinator's plan:
  Stage 0 (root, single worker): FINAL PROJECT
    ↑ receives partial aggregates
  Stage 1 (parallel, N workers): LOCAL AGGREGATE per partition
    ↑ receives data from Stage 2
  Stage 2 (parallel, N workers): SCAN hive.orders WHERE date > '2024-01-01'
    ↑ pushes filter to Hive (Parquet predicate pushdown)
    ↓ emits (region, amount) tuples
  ↓ hash partition by region
  ↑ Stage 1 receives partial aggregates per region
  ↑ Stage 0 combines partial aggregates
  → returns to client
```

Each stage runs on multiple workers; intermediate results are shuffled between stages via Trino's network protocol.

## Cost-Based Optimization

Trino's optimizer uses statistics:
- **Table statistics**: row count, file count, size.
- **Column statistics**: min/max, distinct count, null count, average length.

With statistics, the optimizer:
- **Picks join order**: small table as the build side (in-memory hash table).
- **Picks join distribution**: broadcast (small side) or partitioned (both large).
- **Picks scan paths**: Parquet for column pruning, ORC for predicate pushdown.

```sql
-- After ANALYZE
ANALYZE hive.orders;  -- collects statistics
-- The optimizer now picks the best join order for:
SELECT * FROM hive.orders o JOIN hive.users u ON o.user_id = u.id;
```

## The Memory Model

Trino's memory is managed per-query:
- **General pool**: shared across all queries. Reserved for hash joins, aggregations.
- **Reserved pool**: per-query limit (default 30% of cluster). Prevents a single query from OOMing the cluster.

```text
-- Per-query memory limit
SET SESSION query_max_memory_per_node = '1GB';

-- Cluster-wide memory limit (in config)
query.max-memory=100GB
query.max-memory-per-node=8GB
```

If a query exceeds the limit, it's killed with "Query exceeded distributed memory limit".

## Production Performance

Trino's typical performance on a 10-worker cluster (16-core CPU, 64 GB RAM each):

| Query | Data size | Latency |
|-------|-----------|---------|
| Scan + aggregate | 1 TB Parquet | 30 sec |
| Two-table join | 100 GB + 1 GB | 5 sec |
| Three-table join | 100 GB each | 1 min |
| Federated (Hive + PostgreSQL) | 1 TB Hive, 1 GB PG | 35 sec |

Trino is slower than ClickHouse or Druid for single-table aggregations (Trino has more overhead per operator), but excels at federated queries and ad-hoc joins.

## Production Use Cases

### Ad-hoc Analytics on Data Lake

Trino is the standard for ad-hoc SQL on S3 data lakes:

```sql
-- Query 30 days of events from S3
SELECT event_type, count(*) FROM hive.events 
WHERE date >= date '2024-01-01' AND date < date '2024-02-01'
GROUP BY event_type
ORDER BY 2 DESC;
```

### Federated Queries

Combine data from multiple transactional DBs without ETL:

```sql
-- Customer orders (in PostgreSQL) joined with billing (in MySQL)
SELECT c.name, count(o.id) as order_count
FROM postgres.customers c
JOIN mysql.orders o ON c.id = o.customer_id
GROUP BY c.name
ORDER BY order_count DESC;
```

### Lakehouse Queries

Query Iceberg/Delta Lake tables with full ACID semantics:

```sql
SELECT * FROM iceberg.orders WHERE status = 'shipped';
```

### Interactive Dashboards

Tools like Superset, Tableau, Looker connect to Trino via JDBC. End-users write SQL that Trino executes across federated sources.

## Comparison to Spark SQL

| Aspect | Trino | Spark SQL |
|--------|-------|-----------|
| Latency | Sub-second to minutes | Minutes to hours |
| Best for | Ad-hoc queries, dashboards | ETL, batch processing |
| Resource model | Cluster always on | Per-job (cluster starts/stops) |
| Memory | Per-query limits | Per-executor limits |
| Fault tolerance | Query restarts on failure | Query restarts via DAG scheduler |
| Federated queries | First-class | Limited (JDBC source) |
| Production users | Netflix, LinkedIn, Airbnb | Many data teams |

Trino is for interactive; Spark is for batch. They're complementary — Spark writes the data; Trino queries it.

## Common Pitfalls

1. **Forgetting that Trino is for ad-hoc, not high-concurrency.** Trino's per-query overhead is high; 100s of concurrent queries overwhelm the cluster.

2. **Forgetting to collect statistics.** Without statistics, the optimizer picks bad plans (e.g., wrong join order). Run `ANALYZE` periodically.

3. **Forgetting that joins across federated sources are slow.** A Hive + PostgreSQL join requires Trino to fetch the PostgreSQL data; for large PostgreSQL tables, this is slow.

4. **Forgetting the memory limits.** A query that exceeds `query_max_memory_per_node` fails. Tune the limits based on the workload.

5. **Forgetting to use the right connector for the file format.** Use the Iceberg connector for Iceberg tables (not Hive); the Hive connector doesn't support Iceberg's partition evolution.

6. **Forgetting to enable dynamic filtering.** Dynamic filtering pushes a join's filter to the source, dramatically reducing scan size. Set `enable_dynamic_filtering = true`.

## References

- [Trino documentation](https://trino.io/docs/current/)
- Setty et al., "[Presto: SQL on Everything](https://trino.io/papers/presto-sigmod-2019.pdf)" (SIGMOD 2019)
- [Trino GitHub repository](https://github.com/trinodb/trino)
- [Trino: The Definitive Guide (O'Reilly book)](https://www.starburst.io/wp-content/uploads/2020/11/OReilly-Trino-The-Definitive-Guide-2020-11.pdf)
- [PrestoSQL → Trino rename announcement](https://trino.io/blog/2020/12/27/announcing-trino.html)
- [Trino vs Spark SQL comparison](https://www.starburst.io/blog/trino-vs-spark-sql/)
- [LWN: Trino overview (2021)](https://lwn.net/Articles/872812/)
