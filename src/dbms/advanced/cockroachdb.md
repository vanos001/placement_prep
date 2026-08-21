# CockroachDB Architecture

CockroachDB is an open-source, distributed SQL database created by Cockroach Labs (founded 2015 by Spencer Kimball, Peter Mattis, and others, all ex-Googlers). The design goal is "survivable, scalable, strongly consistent SQL" — a database that handles region-wide failures, scales horizontally, and provides serializable transactions. It is the open-source system most directly inspired by Google Spanner, with the key difference that CockroachDB uses Hybrid Logical Clocks (HLC) instead of TrueTime. This page covers the range/partition model, the Multi-Raft storage layer, the distributed transaction protocol, and the SQL query execution layer.

## The Range Model

CockroachDB's data is stored as an ordered keyspace of (key, value, timestamp) triples. The keyspace is split into **ranges**, each ~512 MB by default:

```text
Keyspace:
  /table/1/row/1 ... /table/1/row/1000     ← Range 1
  /table/1/row/1001 ... /table/1/row/2000   ← Range 2
  /table/1/row/2001 ... /table/2/row/500    ← Range 3
  ...
```

Each range is a Raft group with 3 (or 5) replicas on different nodes. The range's "leaseholder" (a variant on the Raft leader) serves reads and writes for that range.

Why ranges and not tables/partitions? Because CockroachDB uses a global keyspace, every table's rows are interleaved (e.g., `/table/1/row/42` is between `/table/1/row/41` and `/table/1/row/43` regardless of the row's source). This enables **multi-region locality**: rows from different tables can be placed in the same range and replicated to the same region.

## SQL and the Keyspace

CockroachDB SQL tables are mapped to the keyspace via a primary key encoding:

```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    name TEXT,
    region STRING
) PARTITION BY LIST (region) (
    PARTITION us_east VALUES IN ('us-east'),
    PARTITION us_west VALUES IN ('us-west'),
    PARTITION eu VALUES IN ('eu')
);
```

The `PARTITION BY LIST` directive maps rows to different ranges based on the `region` column. CockroachDB can then pin each partition to a specific set of nodes (region-locality).

Without partitioning, all rows of a table are interleaved and ranges are placed wherever the cluster has space. With partitioning, CockroachDB's **zone configs** determine which nodes host each partition's ranges.

## The Multi-Raft Layer

Each range is a Raft group. With 100,000 ranges and 3 replicas each, a 30-node CockroachDB cluster has ~10,000 ranges per node and ~3,000 leader leases per node.

The Multi-Raft implementation batches heartbeats: instead of 100,000 individual heartbeat RPCs per second, CockroachDB coalesces them into one RPC per node pair per tick (every 50 ms by default). This drops the heartbeat traffic from 100,000 RPCs/sec to ~30/sec per node.

Each range's Raft state machine is implemented in Go, using the `etcd-io/raft` library. The Raft log is stored in Pebble (CockroachDB's LSM-tree storage engine, a fork of RocksDB-style storage with bug fixes and improvements).

## The Storage Layer: Pebble

Pebble is CockroachDB's storage engine, an LSM-tree. Each Raft replica's committed entries are applied to a Pebble instance, which writes to a local SSD.

```text
Raft committed log entries
    │
    ▼
Apply to Pebble (LSM)
    │
    ▼
Local SSD
```

Pebble is the unit of storage. Each node has one Pebble instance holding all the ranges' data. The cluster's data is the union of all nodes' Pebble instances, with replication provided by Raft.

## The Leaseholder and Reads

CockroachDB's leaseholder is a refinement of Raft's leader. While the Raft leader is the only one that can append log entries, the leaseholder is the one that can serve reads at a particular timestamp.

The lease is time-based (default 9 seconds, renewable). As long as the lease is valid, the leaseholder can serve reads locally without consulting followers. When the lease expires or the leaseholder fails, a new replica becomes the leaseholder (via Raft leader election).

For follower reads (a feature since 19.x), CockroachDB lets a follower replica serve reads at a timestamp `T` such that:
- `T <= lease_end_of_previous_leaseholder` — i.e., the follower can prove no newer write could have happened.
- This is the "follower reads" feature, which is critical for multi-region reads: a EU client can read from an EU replica, avoiding the cross-region round-trip.

## Distributed Transactions

A transaction touches one or more ranges. CockroachDB's protocol:

```text
Client begins transaction, gets timestamp T0.
Client writes to ranges R1, R2, R3.
  Each range's leaseholder writes a "write intent" with key=K, value=V,
  timestamp=T0, and a "PROVISIONAL" status.
Client commits:
  Picks the range with the lowest ID as the "coordinator".
  Coordinator commits itself (via Raft).
  Coordinator asynchronously resolves other ranges' intents to COMMITTED.
Client returns OK.
```

If the client crashes mid-transaction, the unresolved intents are detected by other transactions that hit them and are resolved (committed or rolled back) based on the coordinator's state.

The **timestamp precedence rule**: when a transaction reads a key and finds an unresolved intent, it must wait for the intent to be resolved. The intent's commit timestamp determines whether the read sees the value or not.

## HLC and the Read-Write Conflict Resolution

CockroachDB uses Hybrid Logical Clocks (HLC) for timestamp assignment. The HLC timestamp is `(physical_clock, logical_counter)`:

- The physical clock part is the wall time.
- The logical counter is incremented when the physical clock would collide.

HLC guarantees: if transaction T1 causally precedes T2, then HLC(T1) < HLC(T2). This is the property that ensures distributed consistency under clock skew.

For concurrent transactions (no causal relationship), HLC doesn't guarantee ordering — but CockroachDB uses the **timestamp precedence rule**: if T1 has a lower HLC than T2, T1 is considered to have "happened before" T2 for serializability purposes.

## Serializable Snapshot Isolation

CockroachDB defaults to **Serializable Snapshot Isolation (SSI)** (not the weaker Snapshot Isolation that PostgreSQL and most databases use). This means:

- Reads see a snapshot at timestamp T0.
- Writes are timestamped at T0.
- The transaction commits only if no other transaction has written to any key this transaction read, with a higher HLC than T0.

If a conflict is detected, CockroachDB restarts the transaction at a higher timestamp (this is called "transaction restart"). Under high contention, restarts can cascade — a known limitation of SSI.

For workloads that tolerate weaker isolation, CockroachDB offers `READ COMMITTED` (since 22.x). This is implemented as a snapshot read with re-execution on detected conflicts.

## The SQL Layer

CockroachDB SQL is PostgreSQL-compatible at the wire protocol level:

- Uses the `pgwire` protocol (the same as PostgreSQL's).
- Supports the same SQL dialect for the most part.
- Uses the `pgx` driver, JDBC, and `psycopg2` directly.

Internally, CockroachDB has its own SQL parser (built with `goyacc` and a hand-written lexer), a Cascades-style query optimizer, and a vectorized execution engine (the latter since 20.x). The SQL layer compiles queries into a distributed plan that runs across multiple ranges' leaseholders.

## Comparison to Spanner

| Aspect | Spanner | CockroachDB |
|--------|---------|-------------|
| Time abstraction | TrueTime (GPS+atomic clocks) | HLC (no special hardware) |
| Commit-wait | Yes (4-7 ms typical) | No (commit-wait is unnecessary with HLC) |
| Cross-group tx | 1 extra RTT for 2PC | 1 extra RTT for 2PC + 1 RTT for intent resolution |
| Paxos variant | Multi-Paxos with leader leases | Multi-Raft with leader leases |
| Storage | Bigtable-style SSTable | Pebble (LSM-tree) |
| SQL | Custom (Spanner SQL) | PostgreSQL-compatible |
| Open source | No | Yes (BSL, transitioning to Apache 2.0) |

The HLC vs. TrueTime trade-off: HLC requires no special hardware but pays an extra RTT for cross-group transactions. For workloads that span groups frequently, Spanner is faster. For workloads that touch few groups per transaction, CockroachDB is comparable.

## Common Pitfalls

1. **Foreign keys without indexes.** CockroachDB enforces FK constraints with reads on the parent table; without an index on the parent's PK, each insert into the child table scans the parent. Always index FK columns.

2. **Cross-range transactions on hot keys.** A counter that 1000 clients increment simultaneously causes transaction restarts under SSI. Use `SELECT ... FOR UPDATE` to serialize, or shard the counter across multiple rows.

3. **Forgetting follower reads.** A read in region EU that hits a US-East leaseholder pays the cross-region RTT (~100 ms). Use `SET LOCALITY REGIONAL BY TABLE` and follower reads to serve reads locally.

4. **Schema changes during high write load.** CockroachDB schema changes are online but can cause backpressure on the affected table's ranges. Schedule schema changes during low-traffic windows.

5. **Trusting the default 9-second lease.** A leaseholder that's slow to respond can stall the range for the lease duration. Tune `kv.raft_leader_lease_duration` based on observed RTT.

## References

- [CockroachDB Architecture documentation](https://www.cockroachlabs.com/docs/stable/architecture/overview.html)
- [CockroachDB: The Resilience of Geo-Distributed OLTP](https://research.google/pubs/pub47755/) (SIGMOD 2017)
- [CockroachDB: Hybrid Logical Clocks](https://www.cockroachlabs.com/blog/time-and-ordering-in-cocroachdb/)
- [CockroachDB: Multi-Raft and Range Splitting](https://www.cockroachlabs.com/blog/scaling-raft/)
- [Pebble storage engine](https://github.com/cockroachdb/pebble)
- [CockroachDB source code](https://github.com/cockroachdb/cockroach)
- [CockroachDB: Distributed SQL at Scale (paper)](https://dl.acm.org/doi/10.1145/3310312)
