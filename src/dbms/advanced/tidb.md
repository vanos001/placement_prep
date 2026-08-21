# TiDB Architecture

TiDB is an open-source distributed SQL database created by PingCAP in 2015. It is MySQL-compatible at the wire protocol level and horizontally scalable for both OLTP and analytical workloads (HTAP). The architecture separates compute (TiDB nodes), storage (TiKV nodes), and analytical processing (TiFlash nodes) — a design that lets each layer scale independently. This page covers the layered architecture, the Percolator-inspired transaction model, the HTAP dual-storage design, and the differences from MySQL and CockroachDB.

## The Layered Architecture

A TiDB cluster has four logical components:

```text
┌──────────────────────────────────────────────────────────────────┐
│  TiDB nodes (stateless)                                          │
│  - Parse SQL, plan, optimize (Cascades-style)                    │
│  - Distribute execution across TiKV/TiFlash                       │
│  - Speak MySQL wire protocol                                     │
└──────────────────────────────────────────────────────────────────┘
            │                            │
            │ OLTP reads/writes          │ OLAP scans
            ▼                            ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  TiKV nodes (Raft)        │    │  TiFlash nodes (columnar)│
│  - Range-partitioned KV   │    │  - Vectorized execution │
│  - Multi-Raft replicated  │    │  - Columnar storage     │
│  - LSM-tree storage engine │    │  - Strongly consistent  │
└──────────────────────────┘    └──────────────────────────┘
            ▲
            │
┌──────────────────────────┐
│  PD (Placement Driver)   │
│  - Cluster metadata       │
│  - Region assignment      │
│  - Timestamp oracle       │
└──────────────────────────┘
```

- **TiDB nodes**: stateless SQL servers. They speak MySQL wire protocol, parse SQL, and produce distributed execution plans. A TiDB cluster typically runs 5-20 TiDB nodes behind a load balancer.
- **TiKV nodes**: stateful storage. Each region is a Raft group with 3 replicas spread across TiKV nodes. The storage engine is RocksDB with LSM-tree semantics.
- **TiFlash nodes**: stateful columnar replicas. Each region in TiKV has a corresponding columnar replica in TiFlash, kept strongly consistent via Raft learner replicas.
- **PD (Placement Driver)**: the metadata and scheduling service. PD assigns timestamps for transactions, tracks region placement, and triggers region splits/merges/balances.

## Region and Range Partitioning

TiKV uses **range partitioning** (not hash). Each region is a contiguous key range:

```text
Keyspace:
[00, 100)   → Region 1 (leader on TiKV-A)
[100, 200)  → Region 2 (leader on TiKV-B)
[200, 300)  → Region 3 (leader on TiKV-C)
...
```

A `PUT key=150` is routed by TiDB to Region 2's leader on TiKV-B. Reads follow the same routing.

Regions split when they exceed 96 MB (default). The split is a Raft decision: the existing region commits a "split" entry that defines the new boundary, and the new region is born.

Range partitioning has a trade-off: hot keys (e.g., a counter at key `K`) concentrate writes on one region. TiKV's solution is **pre-splitting** at table creation:

```sql
CREATE TABLE orders (id INT PRIMARY KEY, ...) SPLIT BY ANCHOR VALUES BETWEEN (?) AND (?);
-- Creates N pre-split regions, distributing load from the start.
```

For auto-incrementing primary keys, range partitioning creates a hot spot at the "end" of the range. The common workaround is to use **sharded auto-increment** — generate IDs that hash to spread across regions:

```sql
CREATE TABLE orders (
  id BIGINT SHARD_ROW_ID_BITS 4 PRIMARY KEY,  -- 4 bits of hash
  ...
);
```

This combines a logical auto-increment with bit-sharding, so 16 regions are written to in parallel.

## The Transaction Model: Percolator

TiDB's transaction protocol is based on Google's Percolator (Peng & Dabek, OSDI 2010), a system originally designed for incremental index updates on Bigtable. Percolator's design:

1. **Single timestamp oracle (PD)**: every transaction gets a unique monotonically increasing timestamp from PD. PD is the only component that needs to be highly available for timestamps.

2. **Write-intent model**: writes are stored as "primary" locks first, then "secondary" locks. The transaction commits when the primary lock is committed; secondaries are cleaned up asynchronously.

3. **Two-phase**:
   - **Phase 1 (Prewrite)**: client writes data + a primary lock + secondary locks for each key. If any key already has a conflicting lock, the transaction aborts.
   - **Phase 2 (Commit)**: client writes a commit record for the primary lock. The transaction is now durable. Client then writes commit records for the secondary locks.

```text
Prewrite phase:
  Key K1: data, primary_lock=<T0, K1>
  Key K2: data, primary_lock=<T0, K1>  ← points to primary's lock
  Key K3: data, primary_lock=<T0, K1>

Commit phase:
  Key K1: commit_T0  ← transaction is now committed
  Key K2: commit_T0  ← (asynchronous, lazy)
  Key K3: commit_T0
```

If the client crashes after Prewrite but before Commit, the transaction is "stuck" until another transaction tries to read K1/K2/K3 and triggers resolution:

- The reader sees the primary_lock on K1.
- Reader checks if the primary commit record exists.
- If yes: the transaction was committed, resolve secondaries.
- If no: the transaction was aborted (roll back).

This lazy resolution means a Percolator-style transaction can leave locks for hours if no one reads them. Production deployments run background "lock cleanup" processes that scan for stale locks.

## PD as the Timestamp Oracle

PD is a single Raft cluster (3-5 nodes) that provides:

1. **Monotonically increasing timestamps**: every `get_ts()` call returns a unique value. PD batches these (every ~1 ms, it returns a single timestamp N for all callers in that batch), so throughput is bounded by 1,000 timestamps/sec/region.

2. **Region metadata**: PD knows which region owns which key range, and which TiKV nodes host each replica. TiDB nodes query PD (with caching) to route requests.

3. **Scheduling**: PD triggers region splits (when a region is too large), region merges (when too small), and leader transfers (to balance load).

PD's availability is critical: without PD, new transactions cannot get timestamps and the database blocks. PD's Raft cluster ensures PD survives node failures.

## TiFlash: Columnar Replicas for HTAP

TiFlash is the columnar storage layer for OLAP workloads:

```text
TiKV Region 1 (row store)         TiFlash Region 1 (column store)
  Row: (id=1, name='a')            Chunk: { id: [1, 2, 3, ...] }
  Row: (id=2, name='b')                     { name: ['a','b','c',...] }
  Row: (id=3, name='c')                     { ... }
  ...                                     ...
```

TiFlash regions are **Raft learner replicas** of the corresponding TiKV regions. They receive Raft log entries from the leader and apply them to the columnar store, but they don't vote in Raft elections. This means:

- Writes: TiKV leader replicates to TiKV followers (voters) AND TiFlash learners. TiKV's commit quorum doesn't include TiFlash, so TiFlash lag doesn't block writes.
- Reads: TiFlash serves reads locally with strong consistency because it has the same Raft log applied.

TiFlash's columnar format is faster for analytical scans: a `SELECT SUM(price) FROM orders` is 10-100× faster on TiFlash than on TiKV.

## The SQL Optimizer

TiDB's SQL optimizer is a Cascades-style optimizer (~300 rules, similar to Microsoft SQL Server's). It supports:

- Join reordering (Bushy joins, not just left-deep).
- Predicate pushdown (filters pushed to scan operators).
- Aggregate pushdown (partial aggregates computed at TiKV/TiFlash).
- Index selection (clustered index, secondary indexes, covering indexes).

The optimizer is pluggable: plan hints (`SELECT /*+ HASH_JOIN(t1, t2) */ ...`) override optimizer choices, and the plan is visible via `EXPLAIN`.

## MySQL Compatibility

TiDB's wire protocol is MySQL's, so:

- Existing MySQL drivers (`mysql2` in Ruby, `mysql-connector` in Java, `pymysql` in Python) work without modification.
- Most MySQL SQL dialect is supported (with some exceptions like `LOCK TABLES`).
- Stored procedures (MySQL's PL/SQL-like syntax) work.

What doesn't work:
- MySQL's `InnoDB`-specific features (`SELECT ... FOR UPDATE` skips locked rows, while TiDB blocks).
- Some MySQL performance schema views (TiDB has its own `information_schema`).
- Cross-database queries (TiDB has a single database per cluster).

## Comparison to MySQL and CockroachDB

| Aspect | TiDB | MySQL (InnoDB) | CockroachDB |
|--------|------|-----------------|-------------|
| Wire protocol | MySQL | MySQL | PostgreSQL |
| Scaling | Horizontal (multi-region) | Vertical (single node) | Horizontal |
| Storage | LSM-tree (RocksDB) | B+ tree (InnoDB) | LSM-tree (Pebble) |
| Tx protocol | Percolator (2PC + lock) | 2PL (per-row) | HLC + SSI |
| HTAP | Yes (TiFlash) | No | No (separate OLAP) |
| Region partitioning | Range | N/A (single node) | Range |
| Single-region latency | ~5 ms (no PD round-trip cached) | ~1 ms | ~10 ms |
| License | Apache 2.0 | GPL/Commercial | BSL→Apache 2.0 |

## Common Pitfalls

1. **Pre-splitting is critical for high-write tables.** Without pre-splitting, all writes funnel into one region until it splits (which can take minutes under heavy load). Always pre-split tables that will receive >1,000 writes/sec.

2. **Auto-increment primary keys are anti-patterns.** They create a hot region at the "end" of the keyspace. Use `SHARD_ROW_ID_BITS` or random UUIDs to spread writes.

3. **PD is a SPOF for timestamps.** If PD is unavailable, the cluster stops accepting new transactions. Use a 3-5 node PD cluster and monitor it aggressively.

4. **TiFlash write amplification is high.** Every TiKV write is also applied to TiFlash's columnar store, which has higher write amplification (typically 30-50×) than TiKV (10-20×). Don't enable TiFlash for tables that are write-heavy and rarely scanned.

5. **Percolator locks can pile up.** A long-running transaction's locks block other transactions that try to write the same keys. Set `max-txn-ttl` (default 1 hour) appropriately; transactions that exceed this are rolled back automatically.

6. **The MySQL optimizer's cost model differs from TiDB's.** A query plan that's fast on MySQL (which has InnoDB statistics) may be slow on TiDB (which has different cost assumptions for cross-region RPCs). Re-analyze plans after migration.

## References

- [TiDB: Distributed SQL Database](https://docs.pingcap.com/tidb/stable/overview)
- Peng & Dabek, "[Large-Scale Incremental Processing Using Distributed Transactions and Notifications](https://www.usenix.org/legacy/events/osdi10/tech/full_papers/Peng.pdf)" (OSDI 2010) — Percolator paper
- [TiDB Architecture documentation](https://docs.pingcap.com/tidb/stable/tidb-architecture)
- [TiKV: The Distributed Key-Value Store](https://tikv.org/docs/5.4/concepts/overview/)
- [TiFlash: Real-Time HTAP](https://docs.pingcap.com/tidb/stable/tiflash-overview)
- [PD: Placement Driver](https://docs.pingcap.com/tidb/stable/tidb-scheduling)
- Source code: [pingcap/tidb](https://github.com/pingcap/tidb), [tikv/tikv](https://github.com/tikv/tikv)
