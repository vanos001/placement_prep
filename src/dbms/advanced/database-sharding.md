# Database Sharding

Database sharding is the practice of partitioning a database's data across multiple servers (shards), each holding a subset of the data. Sharding is the horizontal-scaling solution for databases whose workload exceeds a single server's capacity. This page covers the partitioning strategies (hash, range, directory), the routing layer (shard-aware proxy), cross-shard transactions, and the production trade-offs vs. other scaling approaches (replicas, federation, NewSQL).

## Why Shard

A single database server hits limits on:
- **CPU**: query processing saturates the server's cores.
- **Memory**: working set doesn't fit in RAM; cache hit rate drops.
- **Disk I/O**: random reads saturate the disk's IOPS.
- **Network**: bandwidth saturated by read/write traffic.

For each, sharding distributes the load: each shard has its own CPU, memory, disk, and network. A 4-shard cluster can handle ~4× the workload of a single server.

## Partitioning Strategies

### Hash Partitioning

Each row's partition is determined by `hash(key) % N`, where N is the number of shards:

```sql
-- Conceptually (DynamoDB-style)
PK: user_id (hash key)
shard_id = hash(user_id) % N
```

Pros:
- Even distribution (if the hash function is good).
- Adding shards requires consistent hashing to minimize reassignment.

Cons:
- Range queries (`WHERE user_id BETWEEN 100 AND 200`) hit all shards.
- No "natural" ordering — adjacent keys may be on different shards.

### Range Partitioning

Each shard holds a contiguous range of keys:

```sql
shard 0: user_id 0-9999
shard 1: user_id 10000-19999
shard 2: user_id 20000-29999
```

Pros:
- Range queries (`WHERE user_id BETWEEN 100 AND 200`) hit one shard.
- Easy to add a new shard: split an existing range.

Cons:
- Hot ranges (e.g., the latest user IDs) overload one shard.
- Rebalancing requires moving data between shards.

### Directory Partitioning

A lookup table maps each key to a shard:

```text
shard_map:
  user_1 → shard_0
  user_2 → shard_3
  user_3 → shard_1
  ...
```

Pros:
- Any partitioning scheme can be encoded (e.g., geo-based: EU users on EU shard).
- Adding/removing shards is a metadata change, not a data migration.

Cons:
- The lookup table is a SPOF unless replicated.
- Every read/write requires a lookup.

This is the basis of Vitess (for MySQL), CockroachDB's range metadata, and TiKV's PD.

## The Routing Layer

Clients don't talk directly to shards; they go through a router that maps keys to shards:

```text
Client → Router (shard-aware proxy) → Shard 0/1/2/3
```

The router:
- Maintains the shard map (often cached).
- Routes queries based on the partition key.
- For cross-shard queries, fans out to multiple shards and merges results.

Production routers:
- **Vitess** (MySQL): vtgate is the router, vttablet is the per-shard proxy.
- **CockroachDB**: the SQL layer is the router; it translates SQL to per-range KV ops.
- **TiDB**: the TiDB nodes are routers; TiKV is the storage layer.
- **MongoDB**: mongos is the router; mongod is the per-shard storage.

## Cross-Shard Transactions

A transaction touching multiple shards must coordinate:

```text
T1 writes to shard_0 (user_1's balance)
T1 writes to shard_2 (user_3's balance)
T1 must commit atomically across both shards → 2PC
```

The standard approach is **two-phase commit (2PC)**:
1. T1's coordinator sends PREPARE to each shard.
2. Each shard locks the rows and responds OK or FAIL.
3. If all OK, coordinator sends COMMIT; each shard commits and unlocks.
4. If any FAIL, coordinator sends ABORT.

2PC's overhead: 2 RTTs per shard, plus lock hold time. For OLTP workloads, this is acceptable (most transactions touch one shard). For workloads where many transactions touch multiple shards, sharding may not be the right approach.

Alternative: **Saga pattern** (compensating transactions, eventual consistency). Used when 2PC is too slow; see [TCC page](../backend/patterns/tcc.md).

## Rebalancing

When data distribution or load shifts, shards need rebalancing:
- A shard becomes too big → split into two.
- A shard becomes too hot → move some keys to another shard.
- A new shard is added → some keys move to it.

Production systems automate this:
- **CockroachDB**: range splits when a range exceeds 512 MB; the new range is moved to a less-loaded node.
- **TiKV**: region splits at 96 MB; PD schedules the rebalance.
- **Vitess**: VReplication moves data between shards with online schema migration.

Rebalancing is expensive: moving 1 TB of data between shards takes hours (limited by network and disk). Production systems throttle rebalancing to avoid impacting foreground traffic.

## Common Patterns

### Pattern 1: Hash shard by user ID

```sql
-- Shard by user_id (uniform distribution)
shard_id = hash(user_id) % N
```

Best for: user-facing workloads where each user's data is independent.

### Pattern 2: Range shard by time

```sql
-- Shard by created_at (range partitioning)
shard_2024_01: rows with created_at in January 2024
shard_2024_02: rows with created_at in February 2024
```

Best for: time-series workloads (logs, metrics). Old shards can be archived or dropped.

### Pattern 3: Geo shard by region

```sql
shard_us_east: rows with region='us-east'
shard_eu_west: rows with region='eu-west'
```

Best for: globally distributed apps where latency matters (EU users hit the EU shard).

## Sharding vs. Other Scaling Approaches

| Approach | Read scaling | Write scaling | Strong consistency | Operational complexity |
|----------|---------------|----------------|---------------------|-------------------------|
| Replicas (read replicas) | High | None | Yes (leader-follower) | Low |
| Federation (functional split) | Medium | Medium | Yes | Medium |
| Sharding | Linear | Linear | Yes (with 2PC) | High |
| NewSQL (CockroachDB, Spanner) | Linear | Linear | Yes (native) | Medium |

Replicas are the first scaling step — they scale reads without code changes. Sharding is the next step — it scales writes but requires application changes (shard-aware queries). NewSQL combines sharding with strong consistency, removing the 2PC overhead.

## Common Pitfalls

1. **Choosing a bad shard key.** A shard key with low cardinality (e.g., a status field with 3 values) can't be used for sharding. A shard key with hot spots (e.g., auto-incrementing IDs) creates hot shards.

2. **Forgetting about cross-shard joins.** A `JOIN users ON ... orders` where users and orders are on different shards requires fan-out and merge. Most SQL databases don't support cross-shard joins natively; the application must implement them.

3. **Not planning for shard splits.** A shard that grows to 1 TB must be split. Splitting requires re-balancing all data, which takes hours. Plan splits in advance.

4. **Forgetting the router is a SPOF.** If the router goes down, no queries work. Make the router HA (multiple instances, load-balanced).

5. **Forgetting that 2PC across shards has high overhead.** A transaction touching 5 shards has 5× the 2PC overhead. Minimize cross-shard transactions by designing the schema so most transactions touch one shard.

6. **Underestimating the complexity of operational tasks.** Backups, schema migrations, and reindexing must be done per-shard. A 100-shard cluster has 100 backup jobs.

## Comparison: Sharded MySQL vs. CockroachDB

| Aspect | Vitess (sharded MySQL) | CockroachDB (native sharding) |
|--------|------------------------|--------------------------------|
| Sharding scheme | Hash or range, manual | Range, automatic |
| Cross-shard transactions | 2PC via vtgate | Native (HLC + 2PC) |
| Rebalancing | VReplication (manual) | Automatic (range splits) |
| Schema migration | Per-shard, with tooling | Cluster-wide, online |
| Operational maturity | 10+ years of MySQL tooling | 5+ years of CockroachDB tooling |
| Best for | Existing MySQL workloads scaling | Greenfield deployments needing SQL + scaling |

Vitess is the migration path for existing MySQL deployments that need sharding. CockroachDB is for greenfield deployments that want SQL with sharding built-in.

## References

- [Vitess documentation](https://vitess.io/docs/)
- [CockroachDB: Sharding architecture](https://www.cockroachlabs.com/docs/stable/architecture/overview.html)
- [TiDB architecture](https://docs.pingcap.com/tidb/stable/tidb-architecture)
- [MongoDB sharding documentation](https://www.mongodb.com/docs/manual/sharding/)
- Jeremy Cole, "[Database Sharding at GitHub](https://github.blog/2021-09-09-sharding-github-database/)" (GitHub blog 2021)
- [DynamoDB sharding design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- [Sharding patterns (Microsoft Azure)](https://learn.microsoft.com/en-us/azure/architecture/best-practices/data-partitioning-strategies)
