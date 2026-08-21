# FoundationDB Architecture Deep Dive

FoundationDB (FDB) is a distributed key-value store, originally developed by Apple (2010-2015) and continued by Apple after acquisition in 2015. It is the storage layer for Apple's iCloud, Snowflake's metadata service, and many financial-trading platforms. The architecture combines a transactional key-value layer with a Calvin-style deterministic transaction log and a separation between transaction processing (resolver) and storage (storage servers). This page covers the layered architecture, the deterministic transaction ordering, and the production deployment patterns that distinguish FDB from CockroachDB and Spanner.

## The Layered Architecture

FDB has six logical roles, each running as a separate process:

```text
┌──────────────────────────────────────────────────────────────────┐
│  Client (application, with FDB client library embedded)         │
│  - Caches resolver addresses                                     │
│  - Sends transaction requests directly to roles                 │
└──────────────────────────────────────────────────────────────────┘
        │                         │                       │
        │ reads                   │ commit txn             │ get txn
        │                         │                       │ status
        ▼                         ▼                       ▼
┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ Storage      │    │ Resolver (was   │    │ Proxies             │
│ Servers (SS) │    │ "Sequencer")    │    │ (transaction       │
│ - Hold data  │    │ - Orders txns  │    │  coordinators)     │
│ - per shard  │    │ - Sequencer     │    │ - 5+ per cluster    │
│ - LSM tree   │    │   batches txns  │    │ - Paxos for HA      │
└──────────────┘    └──────────────────┘    └─────────────────────┘
        ▲                         ▲
        │ read batches            │ write batches
        │                         │
        ▼                         │
┌──────────────────────────┐     │
│ TLogs (Transaction Logs) │
│ - Paxos-replicated WAL    │
│ - Per-region pair         │
└──────────────────────────┘
```

- **Proxies**: transaction coordinators. A client's transaction commit goes to a proxy, which validates the read version, gets a commit version from the resolver, and writes the commit batch to TLogs. Proxies are Paxos-replicated for HA (typically 5 per cluster).
- **Resolver (formerly "Sequencer")**: assigns commit versions (timestamps) and detects conflicts. It's the single point of transaction ordering — Calvin-style determinism.
- **TLogs (Transaction Logs)**: the durable write-ahead log. Each region has its own set of TLogs (Paxos-replicated for HA within the region).
- **Storage Servers (SS)**: hold the actual data, sharded by key range. Each shard is replicated 3× via Paxos within a region.
- **Master**: the cluster's leader, elected by a quorum of coordinators. The Master assigns the other roles (Proxy, Resolver, TLog). It's not on the data path.
- **Cluster Controllers**: bootstrap services that tell clients how to reach the Master.

The key insight: every role is on the data path EXCEPT the Master and Cluster Controllers. A Master failure triggers a new election, but in-flight transactions continue to commit (the proxies know each other's addresses).

## The Transaction Protocol

A client transaction has two phases:

### Phase 1: Read (lazy)

The client reads keys by sending requests directly to Storage Servers. The SS returns the value at the requested version (the client picked the read version at transaction start). The SS doesn't track the read — there's no read lock.

This is unusual: most transactional databases hold read locks or maintain a read-set for serializability. FDB's model is **optimistic serializability**: the read is recorded in the client's local read-set, and the resolver validates the read-set at commit time.

### Phase 2: Commit

```text
1. Client sends write batch + read set to a Proxy.
2. Proxy sends read set + write set to the Resolver.
3. Resolver:
   a. Picks a commit version V_new (monotonically increasing).
   b. For each read in the read set, check if it's been written by another
      transaction at version > V_client_read_version. If so, conflict.
   c. Returns commit decision (commit at V_new, or conflict) to the Proxy.
4. Proxy writes the commit batch to TLogs (Paxos-replicated).
5. TLogs ack; Proxy returns commit success to client.
6. TLogs asynchronously stream commits to Storage Servers.
```

The protocol's key property: the **commit version is monotonic across the cluster**. Every transaction's commit version is unique and ordered. Storage Servers apply commits in version order, so each SS's state is consistent.

## Conflict Detection

The resolver maintains a per-key write history: for each key, the version of the most recent write. When a transaction commits, the resolver checks:

- For each key K in the transaction's read set: was K written by any transaction between V_client_read_version and V_new? If yes, conflict.
- For each key K in the transaction's write set: was K written by any transaction with version < V_new that committed after this transaction's read? (This is automatically detected by the version comparison.)

The conflict detection is O(read_set_size × log N) per transaction, where N is the size of the resolver's write history. For typical workloads (read set < 100 keys), this is fast — ~10-100 µs per transaction.

## Sharding and Movement

FDB shards the keyspace by key range. Each shard is held by 3 Storage Servers (Paxos-replicated). Shards split when they exceed ~100 MB (configurable).

```text
Shard 1: [key_a, key_b)     held by SS1, SS2, SS3
Shard 2: [key_b, key_c)     held by SS4, SS5, SS6
Shard 3: [key_c, key_d)     held by SS1, SS7, SS8
...
```

Shard ownership is tracked in the Master's "metadata" (itself Paxos-replicated). When a client wants to read key K, it asks the Master for the SS list of K's shard (cached locally thereafter).

When a shard splits, the Master updates the metadata and the old SSs continue serving reads until the new SSs have caught up via TLog replay. This is the "split-brain recovery" mechanism that lets FDB shard without coordination with clients.

## The TLog Pipeline

TLogs are the WAL. They:

1. Receive commit batches from Proxies.
2. Replicate each batch via Paxos to a quorum of TLogs (typically 3 within a region).
3. Stream committed batches asynchronously to Storage Servers.

A commit is durable once the TLog quorum acks. Storage Servers are best-effort — if an SS is slow, the TLog retains the commit until the SS catches up.

For multi-region deployments, FDB uses "satellite TLogs" — additional TLogs in a remote region that asynchronously receive commits. The remote region's SSs read from these satellite TLogs, providing read locality at the cost of replication lag.

## The Deterministic Ordering Aspect

FDB's transaction ordering is **deterministic** in the Calvin sense: the resolver's decision is the source of truth for transaction order, and every replica (including remote regions) applies transactions in the same order.

This is different from CockroachDB, where each replica's Raft group independently decides transaction order via 2PC + HLC. FDB's design centralizes ordering, which simplifies conflict detection but creates the resolver as a scaling ceiling.

Production FDB clusters use a single resolver process per cluster. The resolver can sequence ~100k transactions/sec (the original Calvin paper's limit). For higher throughput, FDB's "sharded resolver" (since FDB 6.3) splits the conflict detection across multiple resolver processes by key range.

## FDB's "Layer" Model

FDB's API is bare-bones: a transactional key-value store with `get`, `get_range`, `set`, `clear`, and `commit`. Higher-level data models (relational, document, graph) are implemented as **layers** on top:

- **The Record Layer** (open-sourced 2018): a relational layer with tables, indexes, and query planning. Used by Apple for many internal services and Snowflake's metadata.
- **Document Layer** (less common): a document model on top of the key-value store.
- **IndexedDB-style** layers: ad-hoc indexes built on top of the KV store by applications.

Layers do not require FDB changes — they're pure client libraries. This is a deliberate design choice: FDB stays simple, layers handle complexity.

## Comparison to CockroachDB and Spanner

| Aspect | FoundationDB | CockroachDB | Spanner |
|--------|-------------|-------------|---------|
| Tx ordering | Resolver (centralized) | HLC + SSI (decentralized) | TrueTime + 2PC |
| Conflict detection | Read set + write history | SSI restart | Commit-wait |
| Storage engine | LSM (custom) | Pebble (LSM) | Custom SSTable |
| Sharding | Range-based, ~100 MB | Range-based, ~512 MB | Range-based, ~4 GB |
| SQL support | Via Record Layer (library) | Native (PostgreSQL) | Native (custom) |
| Open source | Yes (Apache 2.0, since 2018) | Yes (BSL → Apache 2.0) | No |
| Multi-region | Satellite TLogs + remote SS | Zone configs | TrueTime + leader lease |
| Best for | KV workloads, iCloud-scale | SQL apps needing PG | SQL apps needing Google infra |

FDB's advantage is raw KV throughput: a single FDB cluster can do 1M+ writes/sec, far higher than CockroachDB or Spanner. The disadvantage is no native SQL — applications either use the KV API directly or pay the complexity tax of the Record Layer.

## Common Pitfalls

1. **Forgetting the read set must include all keys read.** If a transaction reads a key but doesn't include it in the commit's read set, the conflict detector misses it and serializability breaks. FDB's client library handles this automatically; custom code that bypasses the library may break this.

2. **Long-running transactions.** FDB's default transaction timeout is 5 seconds; transactions that exceed this are aborted. Long transactions fill the resolver's write history, slowing conflict detection.

3. **Single-shard hot keys.** A hot key (e.g., a counter) saturates the SS holding that shard. FDB doesn't auto-rebalance hot keys; design keys to spread load.

4. **Layer-specific bugs.** A bug in the Record Layer (e.g., a bad index lookup) propagates to the application. Test layers as carefully as the database itself.

5. **Misconfigured satellite TLogs.** A multi-region FDB with 1 satellite TLog has a single point of failure for cross-region commit durability. Use 3 satellite TLogs per remote region.

## References

- [FoundationDB documentation](https://apple.github.io/foundationdb/)
- Zlokapa et al., "[FoundationDB: A Distributed Key-Value Store](https://www.eecs.harvard.edu/~margo/cs261/papers/foundationdb.pdf)" (SOSP 2021 retrospective)
- [FoundationDB Record Layer](https://github.com/FoundationDB/fdb-record-layer)
- [FoundationDB source code](https://github.com/apple/foundationdb)
- [Apple iCloud on FoundationDB (Apple talk)](https://www.youtube.com/watch?v=iw4人心okfQ)
- [Snowflake on FoundationDB (SIGMOD 2020)](https://www.snowflake.com/wp-content/uploads/2020/09/...)
- [LWN: "FoundationDB's approach to distributed transactions" (2018)](https://lwn.net/Articles/753940/)
