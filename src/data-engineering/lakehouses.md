# Data Lakehouses

A data lakehouse combines the **flexibility of data lakes** (schema-on-read, multiple formats) with the **governance and ACID guarantees of data warehouses** (transactions, schema enforcement, time travel). It is the dominant architecture for modern analytical platforms.

## The Problem It Solves

| Approach | Strengths | Weaknesses |
|---|---|---|
| **Data Warehouse** | ACID, schema enforcement, fast SQL | Expensive, rigid, limited to structured data |
| **Data Lake** | Cheap, flexible, any format | No ACID, no transactions, data consistency issues |
| **Data Lakehouse** | ACID + flexibility + cost efficiency | Newer ecosystem, some operational complexity |

## Core Table Formats

### Apache Iceberg

Open table format originally developed at Netflix. Supports schema evolution, hidden partitioning, and time travel.

```sql
-- Iceberg: time travel query
SELECT * FROM orders VERSION AS OF TIMESTAMP '2024-06-01 00:00:00';

-- Schema evolution (no rewrite needed)
ALTER TABLE orders ADD COLUMN discount DOUBLE;
```

Key features: hidden partitioning (partition spec is metadata, not exposed in queries), snapshot isolation, and schema evolution without data rewrites.

### Delta Lake

Developed by Databricks. Extends Parquet with a transaction log (`_delta_log/`) that records every commit as a JSON file with file-level operations.

```python
# Delta Lake: upsert (merge)
delta_table.alias("target").merge(
    source_df.alias("source"),
    "target.id = source.id"
).whenMatchedUpdateAll() \
 .whenNotMatchedInsertAll() \
 .execute()
```

### Apache Hudi

Developed at Uber. Optimized for streaming upserts with built-in file compaction and indexing.

```python
# Hudi: write streaming upserts
hudi_options = {
    'hoodie.table.name': 'orders',
    'hoodie.datasource.write.recordkey.field': 'order_id',
    'hoodie.datasource.write.partitionpath.field': 'date',
    'hoodie.datasource.write.table.type': 'MERGE_ON_READ'
}
df.write.format("hudi").options(**hudi_options).mode("append").save("/data/orders_hudi")
```

## Comparison

| Feature | Iceberg | Delta Lake | Hudi |
|---|---|---|---|
| **Origin** | Netflix | Databricks | Uber |
| **File format** | Parquet, ORC, Avro | Parquet | Parquet, ORC |
| **Schema evolution** | Full (add, drop, rename, reorder) | Add, rename | Limited |
| **Partition evolution** | Yes (hidden partitioning) | Manual | Yes |
| **Time travel** | Snapshot ID, timestamp | Version, timestamp | Timeline |
| **Upsert optimization** | Good | Good | Excellent (MOR/COW) |
| **Engine support** | Spark, Flink, Trino, Snowflake, BigQuery | Spark, Databricks, Trino | Spark, Flink |
| **Community** | Apache, broad vendor support | Linux Foundation, Databricks | Apache, Uber origin |

## ACID on Data Lakes

All three formats provide ACID by using a **transaction log** — an append-only sequence of metadata files:

- **Atomicity** — each commit is an atomic operation in the log; failed writes leave no trace
- **Consistency** — readers see a consistent snapshot (isolated from concurrent writes)
- **Isolation** — optimistic concurrency control with conflict detection on commit
- **Durability** — the log is stored in durable storage (cloud object storage)

## Interview Questions

**Q1: What problem does a data lakehouse solve compared to a traditional data lake?**
A: Data lakes lack ACID transactions, schema enforcement, and time travel, leading to data quality issues and corruption. Lakehouse formats (Iceberg, Delta, Hudi) add a transaction log layer on top of object storage, providing these guarantees without sacrificing the cost and flexibility of data lakes.

**Q2: How does Apache Iceberg achieve hidden partitioning?**
A: Iceberg stores partition specifications as table metadata, not as physical directory structure. Queries automatically apply partition filters based on predicates — users write `WHERE date = '2024-01-01'` and Iceberg routes to the correct partition. This allows partition evolution (changing partition scheme) without rewriting data or breaking queries.

**Q3: What is the difference between COPY-ON-WRITE and MERGE-ON-READ?**
A: COW (used by Delta, Hudi COW tables) writes a complete new file for each update, keeping read performance optimal. MOR (Hudi) writes updates to log files and merges them during compaction or at read time, offering faster writes but slightly slower reads. COW suits batch workloads; MOR suits streaming upserts.

**Q4: When would you choose Delta Lake over Iceberg?**
A: Choose Delta when your stack is Databricks/Spark-heavy — Delta has the deepest integration there, with built-in optimized writes, change data feed, and serverless SQL. Choose Iceberg when you need multi-engine support (Trino, Snowflake, BigQuery), advanced schema/partition evolution, or vendor-neutral portability.

## Cross-References

- [Data Formats](data-formats.md) — Parquet, ORC, Avro underlying formats
- [Batch Processing](batch-processing.md) — Spark integration with lakehouse formats
- [Stream Processing](stream-processing.md) — Real-time writes with ACID
- [Data Quality](data-quality.md) — Quality checks in lakehouse pipelines

## References

- [Apache Iceberg](https://iceberg.apache.org/)
- [Delta Lake](https://delta.io/)
- [Apache Hudi](https://hudi.apache.org/)
- [Lakehouse Architecture — Databricks](https://www.databricks.com/glossary/data-lakehouse)
