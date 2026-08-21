# YugabyteDB Architecture

YugabyteDB is an open-source distributed SQL database built by Yugabyte, founded in 2016 by former Facebook engineers (Kannan Muthukkaruppan, Karthik Ranganathan, and others). It is designed as a "cloud-native" PostgreSQL-compatible database with horizontal write scalability, multi-region active-active deployment, and ACID transactions across geo-distributed nodes. The architecture combines a transactional PostgreSQL-compatible query layer over a sharded Raft-replicated key-value store ("DocDB"). This page covers the architecture, the transaction model, the PostgreSQL compatibility layer, and how YugabyteDB differs from CockroachDB and Spanner.

## The Two-Layer Architecture

YugabyteDB separates concerns into two layers:

```text
┌────────────────────────────────────────────────────────────┐
│  YSQL / YCQL — PostgreSQL/Cassandra-compatible SQL layer   │
│  - Parser, planner, optimizer (PostgreSQL forked)           │
│  - Per-shard query execution                                  │
│  - Stored procedures, prepared statements, etc.             │
└────────────────────────────────────────────────────────────┘
                  │ RPC (per-shard)
                  ▼
┌────────────────────────────────────────────────────────────┐
│  YB-TServer (Tablet Server)                                  │
│  - Tablets (a.k.a. shards): ~128 GB each                    │
│  - Each tablet is a Raft group of 3-5 replicas              │
│  - RocksDB / DocDB storage engine                            │
│  - Handles writes, multi-key transactions                    │
└────────────────────────────────────────────────────────────┘
                  │
                  ▼
                (Per-tablet Raft log + LSM tree)
```

The top layer is a fork of PostgreSQL's SQL parser and planner — it speaks the PostgreSQL wire protocol and supports most PostgreSQL features. The bottom layer is a custom storage engine ("DocDB") built on RocksDB.

## Tablets and Sharding

YugabyteDB shards data by hash or range. The default for primary keys is **hash sharding** (via a consistent hash), which distributes writes evenly across tablets:

```text
INSERT INTO orders (id, customer_id, total) VALUES (1, 42, 99.99);
   │
   ▼
hash(1) = 0x3F7A2 → tablet #5
   │
   ▼
Tablet #5's leader (say, YB-TServer 3)
   │
   ▼
Raft commit to all 3 replicas of tablet #5
```

Range sharding is also supported, which lets range queries (`WHERE id BETWEEN 1 AND 100`) be served by a contiguous set of tablets. Most workloads use hash sharding for write scalability and range sharding for time-series workloads.

Tablets split when they exceed a configurable size (default ~10 GB, much smaller than CockroachDB's 512 MB). The smaller tablet size lets YugabyteDB achieve higher write throughput per tablet (RocksDB's compaction is more efficient with smaller tablets).

## The Transaction Layer

YugabyteDB's transaction protocol is similar to Spanner's:

```text
1. Client picks a transaction TS via HLC (Hybrid Logical Clock).
2. Client writes provisional values to each tablet's leader.
   Each tablet's leader writes the provisional value to its Raft log.
3. Client picks a "coordinator tablet" (often the first write's tablet).
4. Coordinator commits the transaction (writes a commit record to its Raft log).
5. Other tablets resolve their provisional values to "committed" asynchronously.
```

The protocol differs from CockroachDB's in two ways:
1. **No commit-wait**: YugabyteDB uses HLC with a "strictly bounded clock skew" assumption (typically 100-500 ms bound), enforced by the cluster's NTP/chrony configuration. This avoids the per-transaction 4-7 ms commit-wait that Spanner pays for TrueTime uncertainty.
2. **Per-tablet provisional records**: rather than tracking intents in a single global table, each tablet maintains its own provisional records. This is more distributed but requires more cross-tablet coordination during recovery.

## Hybrid Logical Clocks (HLC)

YugabyteDB's HLC combines a physical clock with a logical counter:

```go
type HLC struct {
    PhysicalMS uint64  // milliseconds since epoch
    Logical    uint64  // logical counter
}

func (h *HLC) Update(remote HLC) {
    phys := max(h.PhysicalMS, remote.PhysicalMS, now())
    if phys == h.PhysicalMS && phys == remote.PhysicalMS {
        h.Logical = max(h.Logical, remote.Logical) + 1
    } else if phys == h.PhysicalMS {
        h.Logical = max(h.Logical, remote.Logical)
    } else if phys == remote.PhysicalMS {
        h.Logical = remote.Logical + 1
    } else {
        h.Logical = 0
    }
    h.PhysicalMS = phys
}
```

HLC guarantees:
- If transaction T1 causally precedes T2, then HLC(T1) < HLC(T2).
- Concurrent transactions may have HLCs that compare differently on different nodes; this is handled by the transaction's read-write conflict resolution.

The clock requires bounded clock skew: YugabyteDB assumes the clock skew across nodes is less than `--max_clock_skew_usecs` (default 500 ms = 500,000 µs). The cluster alerts if skew exceeds this.

## Read-Replicas and Geo-Distribution

YugabyteDB's geo-distribution model has two parts:

1. **Preferred regions**: Each tablet can have a preferred region where the Raft leader is pinned. Writes go to the leader's region; reads from the leader stay in the region.
2. **Read replicas**: A tablet can have additional followers in other regions that serve read traffic (with staleness up to the last Raft-applied index). These are non-voting replicas that don't participate in Raft quorums.

This is the basis for active-active multi-region deployments:

```text
Region US-East:
  - Leaders for tablet #1, #5, #9, ...
  - Followers for tablet #2, #6, #10, ...

Region US-West:
  - Leaders for tablet #2, #6, #10, ...
  - Followers for tablet #1, #5, #9, ...

Region EU:
  - Followers for all tablets (read-only region)
```

Writes go to the leader's region, so a write to tablet #1 goes to US-East. Reads can be served by any replica (with staleness for follower reads).

## PostgreSQL Compatibility

YugabyteDB's SQL layer is forked from PostgreSQL's source (typically lagging 1-2 major versions). Compatibility features:

- The wire protocol is `libpq` — drivers for Python (`psycopg2`), Java (JDBC), Go (`lib/pq`), and others work unchanged.
- The SQL dialect is PostgreSQL's — most queries that work on PostgreSQL work on YugabyteDB.
- Stored procedures (PL/pgSQL), triggers, user-defined types, and most other PostgreSQL features work.

Known incompatibilities:
- Index-only scans require reading from the LSM tree (no PostgreSQL-style heap visibility checks).
- Some PostgreSQL extensions (e.g., PostGIS) work; others (e.g., `pg_stat_activity` internals) may differ.
- The optimizer is PostgreSQL's planner; YugabyteDB adds custom cost functions that account for cross-tablet RPC costs.

## YCQL (Cassandra-compatible API)

YugabyteDB also offers YCQL — a Cassandra-compatible API. The same underlying data can be queried via YSQL (PostgreSQL) or YCQL (Cassandra). The YCQL API is useful for Cassandra workloads that need transactions (Cassandra's lightweight transactions are limited to a single partition).

## Comparison to CockroachDB

| Aspect | YugabyteDB | CockroachDB |
|--------|------------|-------------|
| Wire protocol | PostgreSQL (libpq) | PostgreSQL (libpq) |
| Storage engine | RocksDB-based DocDB | Pebble (LSM) |
| Tablet size | ~10 GB | ~512 MB |
| Sharding default | Hash | Range |
| Time abstraction | HLC (bounded skew) | HLC (unbounded skew) |
| Commit-wait | No (relies on bounded skew) | No (HLC) |
| Multi-region | Preferred regions + read replicas | Zone configs |
| License | Apache 2.0 | BSL → Apache 2.0 |

The big practical difference is tablet size: YugabyteDB's smaller tablets mean faster rebalancing and more granular load distribution, but more Raft groups to manage. CockroachDB's larger tablets mean fewer groups (less Raft overhead) but slower rebalancing.

## Common Pitfalls

1. **Clock skew breaks correctness.** YugabyteDB's HLC requires bounded skew. A cluster where NTP fails for >30 seconds can drift by minutes, and the database may halt or produce incorrect results. Always monitor `yb-master` clock skew alerts.

2. **Default tablet count vs. cluster size.** A new cluster starts with 1 tablet per node, which means writes funnel through one Raft group per node until splits happen. Pre-split large tables by hash into N tablets at creation time.

3. **PostgreSQL feature gaps.** YugabyteDB lags PostgreSQL's release cycle by 1-2 versions. Features in PostgreSQL 16 may not appear in YugabyteDB until 6-12 months later. Check the version-compatibility matrix.

4. **Index-only scans are not "free".** Unlike PostgreSQL's heap-visibility optimization, YugabyteDB must check the LSM tree's MVCC metadata for every index-only scan, adding 100-200 µs of overhead.

5. **Cross-tablet transactions are slow.** A transaction touching 10 tablets pays 10 Raft commits in parallel (best case) plus a 2PC coordination overhead. Keep transactions within a single tablet (via primary key design) when possible.

## References

- [YugabyteDB Architecture documentation](https://docs.yugabyte.compreview/preview/architecture/)
- Ranganathan et al., "[YugabyteDB: The Geo-Distributed SQL Database](https://www.yugabyte.com/yugabytedb-paper/)" (SIGMOD 2022)
- [YugabyteDB: How HLC works](https://docs.yugabyte.compreview/preview/architecture/docdb/transactions/transaction-monotonic-clock/)
- [YugabyteDB source code](https://github.com/yugabyte/yugabyte-db)
- [Comparison: YugabyteDB vs CockroachDB](https://www.yugabyte.com/blog/yugabytedb-vs-cockroachdb-comparison/)
- [PostgreSQL compatibility matrix](https://docs.yugabyte.compreview/preview/yugabyte-platform/overview/postgres-compatibility/)
