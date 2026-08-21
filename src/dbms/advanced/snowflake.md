# Snowflake Architecture

Snowflake is a cloud-native data warehouse, launched in 2014 by ex-Oracle engineers (Benoît Dageville, Thierry Cruanes, Marcin Żukowski). It is a columnar, MPP, ANSI SQL database built on AWS (and now also GCP and Azure). The architecture is unique in separating compute (warehouse) from storage (cloud object storage), allowing independent scaling of each. This page covers the three-layer architecture, the multi-cluster shared-data model, and the metadata service.

## The Three Layers

```text
┌─────────────────────────────────────────────────────────┐
│  Services Layer (control plane)                         │
│  - Authentication, access control                       │
│  - Metadata service (Database catalog, table info)     │
│  - Transaction manager (concurrency control)            │
│  - Query optimizer (Cascades-style)                    │
└─────────────────────────────────────────────────────────┘
        │                              │
        │ metadata RPCs                │ query plan distribution
        ▼                              ▼
┌────────────────────────┐    ┌────────────────────────────┐
│  Compute Layer          │    │  Storage Layer              │
│  (a.k.a. warehouse)     │    │  - AWS S3 / GCS / Azure Blob │
│  - N EC2/GCE/Azure VMs  │    │  - Immutable file storage   │
│  - Each VM has local     │    │  - Per-table file format     │
│    SSD cache            │    │    (Snowflake micro-partitions)│
│  - Local cache of file  │    │                              │
│    data from S3         │    └────────────────────────────┘
└────────────────────────┘
```

The three layers are independently scalable. The compute layer (warehouse) can be sized from 1 to N VMs; the storage layer scales automatically with data volume; the services layer is a fixed-size cluster.

## The Compute Layer: Multi-Cluster Shared-Data

A Snowflake warehouse is a "multi-cluster" group of VMs. Each VM is a "compute node" with:
- Multiple CPU cores (typically 8-32 per node).
- Local SSD for caching.
- Network connection to S3 (via AWS VPC).

The warehouse is "multi-cluster" in the sense that you can run multiple warehouses simultaneously. A common pattern:

- `WH_LOAD` (large): for daily ETL loads.
- `WH_QUERY` (medium): for analyst queries.
- `WH_API` (small): for low-latency API queries.

Each warehouse has its own compute nodes; queries in one warehouse don't compete with queries in another. Billing is per-second per-warehouse.

## The Storage Layer: Micro-Partitions

Snowflake stores data in S3 (or equivalent) as **micro-partitions**. Each micro-partition is:
- ~16 MB compressed (50-500 MB uncompressed, depending on data).
- A columnar format (similar to Parquet but proprietary).
- Contains the data for a contiguous range of rows of one table.

```text
Table: orders (1B rows, ~50 columns)
Micro-partitions: 1B / ~50K rows per partition = 20K partitions
Each partition: ~16 MB compressed
Total storage: 320 GB (compressed)

Each partition has:
  - Min/max values per column (for pruning)
  - Distinct value count per column (for selectivity estimation)
  - Null count per column
  - Bloom filter for high-cardinality columns
```

When a query scans `WHERE order_date > '2026-01-01'`, the optimizer uses the partition's min/max of `order_date` to skip partitions that don't contain matching rows. For a 1-year date range, ~1/52 of partitions match — eliminating 98% of scan work.

## The Services Layer: Global Metadata

The services layer holds:
- **Catalog**: which tables exist, their schemas, file locations in S3.
- **Access control**: per-user permissions, role hierarchy.
- **Metadata**: micro-partition stats (min/max, distinct counts).
- **Query optimizer**: parses SQL, generates the distributed plan.
- **Transaction manager**: snapshot isolation + OCC for write transactions.

This layer is built on FoundationDB (Snowflake open-sourced their metadata layer design in a SIGMOD 2020 paper). FoundationDB provides the serializable transaction layer that backs Snowflake's metadata.

## Query Execution

A SQL query in Snowflake:

1. **Parse + Optimize**: the services layer parses the SQL and generates a distributed plan via a Cascades-style optimizer.
2. **Distribute**: the services layer sends the plan to the compute nodes.
3. **Execute**: each compute node scans its assigned micro-partitions (locally cached or fetched from S3).
4. **Shuffle**: intermediate results (e.g., for joins) are shuffled between compute nodes via the warehouse's internal network.
5. **Aggregate + Return**: the final results are aggregated and returned to the user.

```text
SELECT region, SUM(amount) FROM orders WHERE date > '2026-01-01' GROUP BY region;
   ↓
Plan:
  Stage 1 (all compute nodes):
    For each micro-partition assigned to this node:
      Filter rows: date > '2026-01-01'
      Local aggregate: sum(amount) GROUP BY region (local partial)
      Send partial aggregates to Stage 2
  Stage 2 (single node, partitioned by region):
    Combine partial aggregates
    Return final results
```

Each stage runs in parallel across compute nodes. Snowflake's vectorized execution (similar to other modern databases — see [Vectorized Execution](./vectorized-execution.md)) keeps the per-stage throughput high.

## Caching

Snowflake has two cache layers:

1. **Local SSD cache** on each compute node. When a query scans a micro-partition, the partition is cached on the compute node's local SSD. Subsequent queries to the same partition hit the cache (sub-ms latency) instead of fetching from S3 (~5-10 ms).

2. **Result cache** in the services layer. The result of every query is cached for 24 hours. Identical queries (same SQL, same data version) return the cached result in ~100 ms.

The cache layers are critical for cost: Snowflake charges per-second per-warehouse. A workload that benefits from caching can use a smaller (cheaper) warehouse; a workload that scans fresh data needs a larger warehouse.

## The Time Travel and Fail-Safe Features

Snowflake's "Time Travel" lets you query historical data:

```sql
SELECT * FROM orders AT (TIMESTAMP => '2026-01-01 12:00:00');
```

This returns the table's state as of 2026-01-01 12:00. The data is preserved by Snowflake's micro-partition immutability: when a row is updated, the old micro-partition is marked as "deleted" but kept in S3 for the configured time-travel period (default 1 day for Standard, 90 days for Enterprise).

"Fail-safe" extends time-travel by an additional 7 days, even after time-travel expires. This is for disaster recovery: even if a user accidentally drops a table, Snowflake can restore it from fail-safe.

## Cloning and Data Sharing

Snowflake's micro-partition immutability enables cheap clones:

```sql
CREATE DATABASE prod_clone CLONE prod;
```

The clone is metadata-only — it doesn't copy the micro-partitions in S3. The clone shares the original's data; writes to the clone create new micro-partitions (the original's are unchanged). This is the same as ZFS's snapshot-on-write, applied to a database.

**Data sharing**: Snowflake can share a database with another Snowflake account without copying the data. The shared account has read-only access to specific tables; the data stays in the provider's account. This is the basis for Snowflake's "Data Marketplace" — providers publish data, consumers query it directly.

## Comparison to Other Warehouses

| Aspect | Snowflake | BigQuery | Redshift |
|--------|-----------|---------|----------|
| Storage layer | S3 (separate) | Colossus (proprietary) | EBS (with cluster-local) |
| Compute layer | Multi-cluster VMs | Serverless (per-query) | Cluster (provisioned) |
| Billing | Per-second per-cluster | Per-TB scanned | Per-node-per-hour |
| Separation of compute/storage | Yes (full) | Yes (full) | Partial (cluster has local storage) |
| Snapshot cost | Metadata-only (cheap) | Snapshot is metadata | Snapshot copies data (expensive) |
| Open source | No | No | No |

Snowflake's "fully separated" compute/storage is more flexible than Redshift's "cluster with local storage" — you can run multiple warehouses on the same data without copying. BigQuery's serverless model is more flexible still (no provisioning), but has higher per-query costs for steady workloads.

## Common Pitfalls

1. **Forgetting to scale warehouses down.** A warehouse left running bills 24/7. Snowflake's "auto-suspend" feature suspends a warehouse after N minutes of inactivity (default 60s), but the operator must configure it.

2. **Treating Snowflake as a transactional DB.** Snowflake supports ACID transactions but is designed for analytical workloads. Single-row inserts are slow (each insert creates a new micro-partition). Batch inserts.

3. **Forgetting that the result cache is per-user.** Each user's queries have their own result cache; another user's identical query doesn't hit the cache (privacy reasons). For shared queries, use a shared role.

4. **Using too-large warehouses.** A "Large" warehouse (16 compute nodes) is faster than a "Small" (1 node), but only for queries that parallelize. For single-row queries, the larger warehouse is no faster — wasted spend.

5. **Forgetting that clones share data.** A clone shares the original's micro-partitions in S3. If you delete the original, the clone becomes a "real" copy (the partitions are now owned by the clone). This can be expensive.

6. **Forgetting that data sharing is one-directional.** The provider's account owns the data; the consumer's account has read-only access. The consumer cannot write to the shared table.

## References

- Warke et al., "[Snowflake's Elastic Data Warehouse](https://dl.acm.org/doi/10.1145/3183713.3183719)" (SIGMOD 2017)
- [Snowflake documentation](https://docs.snowflake.com/)
- [Snowflake's FoundationDB metadata layer (SIGMOD 2020)](https://www.snowflake.com/wp-content/uploads/2020/09/SIGMOD-FDB.pdf)
- [Snowflake architecture whitepaper](https://www.snowflake.com/wp-content/uploads/2020/09/Snowflake-Architecture-Whitepaper.pdf)
- Marcin Żukowski, "[Snowflake design talk (Snowflake Summit 2021)](https://www.youtube.com/watch?v=Architecture)"
- [Snowflake multi-cluster shared-data paper](https://www.snowflake.com/wp-content/uploads/2020/09/SnowflakeMultiClusterSharedDataArchitecture.pdf)
