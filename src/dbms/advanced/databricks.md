# Databricks Architecture

Databricks is a cloud-native data platform, founded in 2013 by the original creators of Apache Spark (Matei Zaharia, Reynold Xin, Ali Ghodsi, et al.). It began as a Spark-as-a-service company but has evolved into a full lakehouse platform: data warehouse (Databricks SQL), data engineering (Databricks Workflows), ML (Databricks ML), and governance (Unity Catalog). This page covers the architecture, the Photon execution engine, the Delta Lake storage format, and the serverless SQL offering.

## The Lakehouse Architecture

Databricks markets itself as a "lakehouse": the openness of a data lake (S3-compatible storage, multiple file formats) with the management of a data warehouse (transactions, schema, governance).

```text
┌────────────────────────────────────────────────────────────────┐
│  Databricks Control Plane (per-workspace, managed)              │
│  - Workspace metadata (notebooks, dashboards, jobs)            │
│  - Unity Catalog (table schemas, access control)                │
│  - Cluster manager (auto-scaling, auto-termination)            │
└────────────────────────────────────────────────────────────────┘
        │                              │
        │ API calls                    │ query / job dispatch
        ▼                              ▼
┌─────────────────────────┐    ┌─────────────────────────────────┐
│  Compute clusters        │    │  Storage layer (S3 / GCS / Azure)│
│  (Databricks "clusters") │    │  - Delta Lake (transactional    │
│  - "All-purpose" for     │    │    Parquet-like format)          │
│    interactive notebooks  │    │  - Unity Catalog metadata        │
│  - "Jobs" for batch ETL   │    │  - Workspace's own metadata      │
│  - "SQL warehouses" for   │    └─────────────────────────────────┘
│    SQL analytics          │
│  - Photon-enabled         │
└──────────────────────────┘
```

The control plane is managed by Databricks (multi-tenant SaaS). The compute clusters and storage live in the customer's cloud account (single-tenant for compute/storage, multi-tenant for the control plane).

## Photon: The C++ Execution Engine

Until 2020, Databricks used the JVM-based Spark engine. Photon (announced 2020, generally available 2021) is a native C++ execution engine that replaces Spark's JVM layer for SQL and DataFrame queries.

Key Photon improvements:
- **Vectorized execution** (similar to other modern databases — see [Vectorized Execution](./vectorized-execution.md)). SIMD instructions for filter/project/aggregate.
- **No JVM overhead**: ~30% memory reduction (no JVM object headers, no GC pressure).
- **Native code**: tighter inner loops, no JIT warmup.

Benchmark: Photon is 3-4× faster than Spark 3.0 on TPC-DS for the same hardware. Databricks SQL Warehouses use Photon by default since 2021.

## Delta Lake: The Storage Format

Delta Lake is an open-source storage layer (Apache 2.0) that adds ACID transactions to Parquet files on object storage. A Delta table is a directory in S3/GCS/Azure containing:

- **Data files**: Parquet files (~1 GB each, partitioned by user-specified columns).
- **Transaction log**: a `_delta_log/` directory with JSON files describing each transaction.

```text
my_delta_table/
├── part-00001-abc.parquet
├── part-00002-def.parquet
├── part-00003-ghi.parquet
└── _delta_log/
    ├── 00000000000000000000.json   ← initial commit
    ├── 00000000000000000001.json   ← second transaction
    ├── 00000000000000000002.json   ← third transaction
    └── ...
```

Each transaction's JSON entry describes:
- The action: `add`, `remove`, `meta`, `protocol`, `commitInfo`.
- The affected file(s).
- The operation that triggered the transaction.

To read a table at time T, the reader applies the transaction log from start to T and gets the set of valid files. This is the "snapshot" — the state of the table as of a specific transaction.

## Delta Lake's Optimistic Concurrency

Multiple writers can attempt to commit at the same time. The protocol:

1. Writer W reads the current log version (say, v=42).
2. W computes its changes (e.g., insert 1000 rows → create a new Parquet file).
3. W tries to commit: write `00000000000000000043.json` (the next version after 42).
4. If successful, the commit is durable.
5. If another writer beat W to v=43, W must re-read at v=43, recompute its changes (since the data may have changed), and retry.

This is optimistic concurrency control. For workloads with low conflict (the common case), it's fast (no locks held during the write). For high-conflict workloads, it can retry many times.

## Z-Ordering and Liquid Clustering

To support efficient range queries, Delta Lake provides:

- **Z-Ordering** (deprecated, replaced by Liquid Clustering): rearranges the data files so that rows with similar values in Z-order columns are physically adjacent. A range query on those columns skips most files.
- **Liquid Clustering** (since 2023): a more adaptive clustering that automatically re-clusters as data is added. Doesn't require the user to pre-define clustering columns.

```sql
-- Create a table with Liquid Clustering on (customer_id, order_date)
CREATE TABLE orders (
  order_id BIGINT,
  customer_id BIGINT,
  order_date DATE,
  ...
) USING DELTA
CLUSTER BY (customer_id, order_date);

-- A query filtering on customer_id will skip most files
SELECT * FROM orders WHERE customer_id = 42;
```

## Unity Catalog: Centralized Governance

Unity Catalog (since 2022) is Databricks' centralized metadata and governance layer:

- **Catalogs**: top-level containers (e.g., `prod`, `dev`).
- **Schemas** (a.k.a. databases): within a catalog.
- **Tables**: within a schema.
- **Views, functions, AI models**: within a schema.

Each object has a unified access control (SQL GRANT/REVOKE), audit logs, and column-level masking. The catalog is itself a metastore backed by an internal Databricks database (multi-region, HA).

## Databricks SQL Warehouses

Databricks SQL Warehouses are the SQL compute layer (the "Databricks SQL" product). Key features:

- **Serverless** (since 2023): no provisioning; queries start in <1 second.
- **Photon**: native vectorized execution.
- **Result cache**: query results cached for 24 hours.
- **Auto-scaling**: the warehouse scales based on concurrent queries.

Pricing: per-DPU-second (a DPU is roughly 1 vCPU-hour). Serverless warehouses are billed at a premium over classic "all-purpose" clusters but eliminate provisioning overhead.

## Databricks Workflows

Databricks Workflows (formerly Databricks Jobs) is the orchestration layer:

```python
# Define a workflow with multiple tasks
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

w.jobs.create(
    name="daily_etl",
    tasks=[
        Task(task_key="extract", notebook_task=NotebookTask(notebook_path="/etl/extract")),
        Task(task_key="transform", depends_on=[TaskDependency(task_key="extract")],
             notebook_task=NotebookTask(notebook_path="/etl/transform")),
        Task(task_key="load", depends_on=[TaskDependency(task_key="transform")],
             notebook_task=NotebookTask(notebook_path="/etl/load")),
    ],
    schedule=CronSchedule(quartz_cron_expression="0 0 1 * * ?"),  # daily at 1am
)
```

Each task is a notebook or a Python script; tasks can be chained with dependencies. Databricks Workflows is similar to Apache Airflow but runs natively on Databricks clusters.

## Databricks ML

Databricks ML (Databricks Runtime ML, "MLR") adds ML libraries to the cluster:
- Pre-installed: PyTorch, TensorFlow, scikit-learn, XGBoost.
- Pre-installed: Hugging Face transformers, LangChain.
- Pre-installed: MLflow for experiment tracking.

For LLM training, Databricks ML includes DeepSpeed, Megatron-LM, and a managed version of Unity Catalog for model versioning.

## Comparison to Snowflake

| Aspect | Databricks | Snowflake |
|--------|-----------|----------|
| Storage format | Delta Lake (open) | Micro-partitions (proprietary) |
| Compute layer | Spark + Photon (managed) | Snowflake warehouses |
| Open data | Yes (read Delta from any tool) | Yes (Unistore for Iceberg, but limited) |
| ML tools | Strong (DLT, MLflow, ML runtime) | Stronger (Snowpark ML) |
| Serverless SQL | Yes (since 2023) | Yes (since 2021) |
| Pricing | Per-DBU-hour (per-cluster) | Per-second per-warehouse |

Both have moved toward each other: Snowflake has added ML and open formats (Iceberg support); Databricks has added Photon and serverless SQL. The distinction is blurring.

## Common Pitfalls

1. **Forgetting that Photon isn't free.** Photon clusters are billed at a premium (1.5-2× the cost of non-Photon). For simple Spark jobs, non-Photon is cheaper.

2. **Mixing all-purpose clusters and SQL warehouses.** All-purpose clusters have higher per-DBU pricing than SQL warehouses. For SQL-only workloads, use SQL warehouses.

3. **Forgetting that Delta Lake is open-source.** You can read Delta tables from Apache Spark, Trino, Presto, etc. — not just Databricks. Databricks' commercial value is in the management, not the format.

4. **Treating Unity Catalog as just a metastore.** It also provides row-level and column-level access control, audit logs, and lineage. Use these features; they're not extra cost.

5. **Forgetting that "Z-Ordering" requires a re-write of the data.** Re-clustering on Z-Order columns is a full table rewrite — expensive for large tables. Use Liquid Clustering instead (incremental).

6. **Using all-purpose clusters for production jobs.** All-purpose clusters have higher pricing and no SLA. Use "Jobs clusters" for production ETL (lower price, SLA-backed).

## References

- Zaharia et al., "[Apache Spark: A Unified Engine for Big Data Processing](https://www.cs.berkeley.edu/~matei/papers/2010/nsdi_spark.pdf)" (NSDI 2010)
- [Databricks documentation](https://docs.databricks.com/)
- [Photon: Databricks Native Execution Engine](https://www.databricks.com/blog/2020/09/09/introducing-photon-our-next-generation-vectorized-query-engine.html)
- [Delta Lake protocol specification](https://github.com/delta-io/delta/blob/master/PROTOCOL.md)
- [Unity Catalog documentation](https://docs.databricks.com/data-governance/unity-catalog/index.html)
- [Databricks Serverless SQL](https://www.databricks.com/product/databricks-sql/serverless)
- [Delta Lake GitHub](https://github.com/delta-io/delta)
