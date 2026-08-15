# Distributed Databases & NewSQL

This chapter covers the design of modern distributed SQL databases that aim to combine the scalability of NoSQL with the consistency and SQL interface of traditional RDBMS. We examine FoundationDB, TiDB, YugabyteDB, and the HTAP architecture paradigm.

## FoundationDB

### Architecture

FoundationDB (FDB, now open-source under Apache 2.0, used as the foundation of **Apple CloudKit**) is a **distributed key-value store** that provides **ACID transactions** with **serializable isolation** over a shared-nothing cluster. Its architecture is notable for its strict **layering**: a minimal KV core provides transactions, and all higher-level functionality (SQL, document, graph) is built as a **layer on top**.

```
┌─────────────────────────────────────────┐
│          Application Layer             │
│  (Record Layer, Document Layer, etc.)   │
├─────────────────────────────────────────┤
│          FoundationDB Core             │
│  Distributed KV with ACID transactions  │
│  (Proxies, Resolvers, Storage, Logs)    │
└─────────────────────────────────────────┘
```

### Core Components

| Component | Role | Count | Fault Tolerance |
-----------|------|-------|----------------|
| **Coordinator** | Cluster metadata, sequencer assignments | 5 (quorum of 3) | Paxos | 
| **Sequencer** | Assigns transaction commit versions | 1-3 per cluster | Failover via Paxos |
| **Proxy** | Transaction resolution, conflict detection | 1 per transaction | Stateless | 
| **Resolver** | Detects write-write conflicts | Multiple | Stateless |
| **Storage Server** | Stores key ranges (shards) | Many | Replicated (3x) via Raft |
| **Log Server** | Persistent write-ahead log for storage | Many | Replicated | 

### Transaction Protocol

FDB uses **optimistic concurrency control** with a sequencer-based commit protocol:

1. **Read phase**: Client reads from storage replicas at a given **read version** (obtained from a proxy).
2. **Write phase**: Client buffers writes locally.
3. **Commit**: 
   - Proxy obtains a **commit version** from the sequencer (guaranteed > all previous commit versions).
   - Proxy sends the transaction's reads + writes to resolvers.
   - Resolvers check for **write-write conflicts** with other committed/committing transactions.
   - If no conflicts, proxy responds with commit version. Client pushes writes to storage servers.

**Key property**: The sequencer provides a **strict total order** on commit versions, which guarantees serializability. No distributed locking or deadlock detection needed.

### Data Modeling with the Record Layer

FDB's **Record Layer** (open-sourced by Apple) provides a typed, schemaful API on top of the KV store:
- Schemas defined in protobuf
- Automatic index maintenance (secondary indexes, value indexes)
- Tuple packing: multi-attribute keys are packed into FDB tuples using a type-aware encoding
- The Record Layer is how **Apple** stores iCloud data on FoundationDB

> **Interview Angle**: "How does FoundationDB achieve serializable transactions at scale?" — Explain the sequencer-assigned commit versions, optimistic conflict detection via resolvers, and the separation between the KV core and layers. Mention it handles billions of keys per cluster.

## TiDB

### Architecture

TiDB (PingCAP) is a **NewSQL** database with a clear separation of compute and storage:

```
┌──────────────┐     ┌──────────────┐
│  TiDB Server │     │  TiDB Server │   (SQL parsing, optimization, execution)
│  (PD client) │     │  (PD client) │   Stateful, but SQL-layer is stateless
├──────────────┤     ├──────────────┤
│       TiKV Cluster         │        (Raft-based KV store)
│  ┌────┐ ┌────┐ ┌────┐       │
│  │KV  │ │KV  │ │KV  │       │
│  └────┘ └────┘ └────┘       │
├─────────────────────────────┤
│  PD (Placement Driver)      │   (Metadata, shard scheduling, timestamp)
└─────────────────────────────┘
```

### Key Components

- **TiDB Server**: Stateless SQL layer. Parses SQL, optimizes (via a Cascades-based optimizer), and executes distributed queries. Scales horizontally.
- **TiKV**: Distributed KV store based on **RocksDB** + **Raft** (using the `raft-rs` library). Data is partitioned into **Regions** (~96MB each) with 3 replicas per region.
- **PD (Placement Driver)**: Central metadata service (3-node Raft cluster). Manages region placement, load balancing, and provides **Percolator-style timestamps** (via a TSO — Timestamp Oracle).

### TiDB Transaction Model (Percolator)

TiDB uses **Google Percolator** (Peng et al., 2010) for distributed transactions:

1. **Timestamp Oracle (TSO)**: PD assigns monotonically increasing timestamps. Each transaction gets a `start_ts`.
2. **Prewrite**: For each key written, write a **primary lock** (for one key) and **secondary locks** (for other keys) at the write's location. Locks carry the transaction's `start_ts`.
3. **Commit**: Acquire `commit_ts` from TSO. Write the commit timestamp to the primary lock location. This makes the primary key visible.
4. **Cleanup**: Secondary locks are resolved lazily by readers (roll forward if committed, roll back if not).

**Performance**: Percolator adds significant write overhead (2 RPCs per key: prewrite + commit). TiDB mitigates this with **1PC for single-region transactions** and **async commit** (where the client doesn't wait for secondary lock resolution).

### TiFlash (HTAP)

**TiFlash** is a columnar storage engine that replicates data from TiKV via Raft Learner replicas. It provides **real-time analytics** (HTAP) by:
- Maintaining columnar copies of row-oriented TiKV data
- Supporting **MPP (Massively Parallel Processing)** execution for analytical queries
- Reading at a specific snapshot to avoid interfering with OLTP

## YugabyteDB

### Architecture

YugabyteDB is a **distributed SQL database** that combines the **CockroachDB-style distributed architecture** with the **PostgreSQL wire protocol and query layer**:

```
┌──────────────────────────────────────┐
│         YSQL (PostgreSQL-compatible) │  → pg_protocol, SQL parser, planner
│         YCQL (Cassandra-compatible)  │  → Cassandra-style API
│         YEDIS (Redis-compatible)     │  → Redis API
├──────────────────────────────────────┤
│         DocDB (distributed storage)   │  → LSM-tree based, Raft replication
└──────────────────────────────────────┘
```

### Design Choices

| Aspect | YugabyteDB | CockroachDB | TiDB |
--------|-----------|-------------|------|
| SQL compatibility | PostgreSQL wire protocol | Custom SQL | MySQL compatibility |
| Storage engine | DocDB (custom LSM) | RocksDB | RocksDB (TiKV) |
| Consensus | Raft (per shard) | Raft (per range) | Raft (per region) |
| Isolation | Serializable (SSI) | Serializable (SSI) | Snapshot Isolation (default) |
| Clock | Hybrid Logical Clock (HLC) | HLC | TSO (centralized) |
| HTAP | YCQL columnar (early) | Not built-in | TiFlash |
| Topology | Per-region (AZ-aware) | Per-region | Per-region |

### DocDB Internals

DocDB is a **document-oriented** storage engine built on LSM trees. Each row is stored as a **document** (a collection of key-value pairs), enabling flexible schemas:
- **Primary key columns** are encoded into the DocDB key
- **Non-key columns** are stored as sub-keys within the document
- This allows **partial document updates** without reading the full row

## Distributed SQL: The NewSQL Landscape

### NewSQL Design Principles

NewSQL systems aim to provide:
1. **SQL interface** with relational semantics
2. **Horizontal scalability** (scale-out, not scale-up)
3. **ACID transactions** with serializable or snapshot isolation
4. **High availability** via replication and automatic failover

### Comparison of Distributed SQL Systems

| System | SQL Dialect | Sharding | Transactions | Replication | Strength |
--------|------------|----------|-------------|-------------|----------|
| **CockroachDB** | PostgreSQL-like | Range-based (automatic) | Serializable (SSI) | Raft (3+ replicas) | Cloud-native, ease of ops |
| **TiDB** | MySQL-compatible | Range-based (Regions) | SI (Percolator) | Raft + PD | MySQL migration path |
| **YugabyteDB** | PostgreSQL wire protocol | Hash/sharding | Serializable | Raft | PostgreSQL compatibility |
| **Spanner** | GoogleSQL | Range-based | Serializable (TrueTime) | Paxos | Global scale, strongest consistency |
| **Aurora** | PostgreSQL/MySQL | Log-isolated storage | Serializable (1PC/2PC) | 6 copies (3 AZs, quorum) | Cloud-managed, minimal ops |
| **OceanBase** | MySQL/Oracle compatible | Range-based (partition) | Serializable | Paxos | Financial-grade (Alipay) |
| **FoundationDB** | KV (layers add SQL) | Range-based | Serializable (sequencer) | Raft | Ultra-reliable foundation layer |

## HTAP (Hybrid Transactional/Analytical Processing)

### The Problem

Traditionally, organizations maintain separate OLTP and OLAP systems with ETL pipelines between them:

```
OLTP DB (MySQL, PostgreSQL) → ETL (nightly) → OLAP DB (Redshift, Snowflake)
     ↑ real-time latency                                           ↑ stale data
```

HTAP aims to serve **both transactional and analytical queries on the same real-time data** without ETL.

### HTAP Architecture Patterns

| Pattern | Mechanism | Latency | Example |
---------|-----------|---------|----------|
| **Columnar replica** | Raft learners replicate row data into columnar store | Near real-time (seconds) | TiDB + TiFlash |
| **Shared-nothing dual engine** | OLTP and OLAP nodes read from same storage | Real-time | SingleStore |
| **Log-structured columnar** | Single engine with both row and column formats | Real-time | SAP HANA |
| **Delta lake integration** | OLTP writes to delta, OLAP reads merged snapshot | Minutes | Databricks Delta Lake |
| **Materialized views** | Async maintained columnar MVs on OLTP data | Near real-time | ClickHouse + PostgreSQL (via materialized) |

### Challenges in HTAP

1. **Resource contention**: Analytical queries are CPU/memory intensive and can starve OLTP transactions. Mitigation: resource isolation (separate node pools, cgroups, QoS).
2. **Data freshness**: Columnar replicas lag behind the row-store by seconds to minutes. For strict freshness requirements, this is unacceptable.
3. **Storage cost**: Maintaining both row and column copies doubles storage. Mitigation: share storage layer (Aurora-style) or use tiered storage.
4. **Consistency**: Analytical queries reading from a replica might see stale data. TiFlash solves this by reading at a specific timestamp consistent with the TiDB transaction.

> **Interview Angle**: "What is HTAP and what are the key challenges?" — Explain the traditional OLTP/OLAP separation, the HTAP vision, replication-based architectures (TiFlash), and the fundamental tension between OLTP latency and OLAP throughput. Mention resource isolation and freshness as practical concerns.

## References

- Lomet, D. et al. "FoundationDB: A Distributed Unordered Key-Value Store." ACM SIGMOD, 2022.
- Peng, D. et al. "Large-Scale Incremental Processing Using Distributed Transactions and Notifications." OSDI, 2010. (Percolator)
- Corbett, J. et al. "Spanner: Google's Globally Distributed Database." OSDI, 2012.
- Liu, M. et al. "TiDB: A Raft-based HTAP Database." PVLDB, 2020.