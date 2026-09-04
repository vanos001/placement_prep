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

## Directory-Based Sharding in Depth

The three strategies above answer "where does key *k* live?" three ways:
**compute** it (hash), **navigate** to it (range), or **look it up**
(directory). The directory deserves its own treatment because it is the only
one that can express *arbitrary* placement — geo rules (EU users on EU shards),
per-tenant isolation, VIP tenants on dedicated hardware — and the only one
where adding a shard is pure metadata: the directory starts assigning new keys
to it, and no old key is remapped.

The price is that the directory is itself a distributed system:

- **Extra hop.** Every first touch of a key needs a lookup. Production
  directories are cached aggressively (client-side and router-side), and the
  lookup is only paid on cold keys; key access is Zipfian, so steady-state hit
  rates are high. The hop you cannot cache away is the lookup right after a
  move, when routes churn.
- **HA and consistency.** A single-node directory is a SPOF; production
  directories are consensus-replicated (ZooKeeper, etcd — see
  [etcd](../../cloud/etcd.md)) and become the correctness anchor of the whole
  cluster: directory entries must change atomically with data moves, or the
  directory *lies* (see "Shard Metadata Correctness" below).
- **Two implementation shapes.** A *computed* directory — a deterministic
  function of the key (hash, bit-reversal) — costs nothing per query but can
  only change by remapping keys. A *stored* directory — a real table mapping
  key → shard — can encode any placement, but must itself be replicated and
  kept transactional with the data it points to.

Who actually does this:

- **Vitess** formalizes both shapes as vindexes: Functional vindexes
  pre-establish the column-value → keyspace-ID mapping "typically through an
  algorithmic function," while Lookup vindexes store the mapping in a lookup
  table — literally a directory — with `consistent_lookup_unique` variants
  that keep the map and the data in sync across shard moves.
- **MongoDB** keeps a directory at chunk granularity: config servers "store
  the metadata for a sharded cluster" including the list of chunks on every
  shard, and every mongos consults (a cache of) that map to route.

The tradeoff in one sentence: hash and range make placement *computable* and
fast but rigid; a directory makes placement *arbitrary* and elastic, but
inserts a second distributed system between the client and the data.

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

## Virtual Shards and Vnodes

Direct key→node mappings make every topology change a repartition, so every
mature design inserts an indirection layer: map keys to a **large fixed number
of virtual shards** (vnodes, buckets, slots, regions), and map virtual shards
to physical nodes as *metadata*:

```text
key --hash--> bucket 0..16383 (fixed forever) --routing table--> node (changes freely)
```

The consequences compound:

- **Steady-state rebalance = moving vnode ownership.** A node joining steals
  roughly 1/(N+1) of the vnode space from every other node — small, parallel,
  throttled moves instead of a big-bang repartition; a node leaving is the
  reverse.
- **Splitting a hot shard = reassigning part of its vnodes**, not redesigning
  the key space.
- **The vnode becomes the unit of migration, throttling, and correctness.**
  This is exactly MongoDB's chunk, TiKV's region (96 MiB Raft groups — see
  [TiDB Internals](./tidb-internals.md)), CockroachDB's range, and Redis
  Cluster's 16,384 hash slots (slot = CRC16(key) mod 16384).

Vnode count is a real tradeoff. Too few: balance is coarse — one hot vnode is
one unmovable hotspot, and every move is huge. Too many: the metadata table
grows, and per-vnode bookkeeping (heartbeats, consensus groups) eats memory.
It is the same granularity argument as choosing shuffle-partition counts in
distributed query execution — see
[Distributed Query Execution](./distributed-query-execution.md). The
assignment math that minimizes disruption when the vnode space itself must
change is [consistent hashing](../../distributed/partitioning/consistent-hashing.md)
(and its minimal-disruption cousin, jump consistent hashing); the machinery
that moves the *data* behind an ownership change is the migration protocol in
[Online Resharding and Shard Migration](./online-resharding.md).

## Routing Tiers: Proxy, Smart Client, or Coordinator

Someone must hold the vnode→node table and answer "where does this query go?"
Three production tiers:

| Tier | Who holds the map | Examples | Extra hop | Core tradeoff |
|---|---|---|---|---|
| Stateless proxy | router process | mongos, Vitess vtgate, TiDB server | yes (1) | one place to upgrade and audit; a proxy fleet to run; clients stay dumb |
| Smart client / driver | the client library | Redis Cluster clients (learn the slot map, self-heal on redirect) | no | every language reimplements routing; stale maps until refresh; upgrades require client deploys |
| Coordinator per node | every server node | CockroachDB, TiDB (any node accepts any query) | no | metadata ships everywhere; every node is trusted with the full map |

The tiers differ most in how **staleness** behaves. A proxy refreshes its
metadata centrally: mongos "tracks what data is on which shard by caching the
metadata from the config servers," and re-fetches when a shard reports the
route it used is out of date. A smart client heals itself: a node that
receives a key it no longer owns replies with a redirect for that slot, and
the client updates its map and retries (Redis Cluster's MOVED redirect); while
a slot is mid-migration the protocol uses a temporary redirect so clients do
not cache a route that is about to change again. A coordinator-tier node
refreshes from replicated descriptors and forwards to the new owner — the
redirect never leaves the cluster.

Tier choice follows trust and latency budgets: proxies dominate where many
heterogeneous clients exist (polyglot services, legacy apps that must not know
about sharding); smart clients where an extra hop is unacceptable (caches,
latency-sensitive reads); coordinator tiers where the storage system already
replicates full metadata to every node anyway.

## Shard Metadata Correctness: Stale Routes, Handoffs, Fencing

The routing table is a **cache of the truth**, and the truth lives in the
metadata plane (config servers, PD, the topology service). Every routing
failure decomposes into "the route lagged the data":

- **Read on the old owner.** A client with a stale route reads a row that has
  already been copied out. If the move used copy-then-cutover with dual-write
  or quiesce (the standard handoff, detailed in
  [Online Resharding](./online-resharding.md)), the old owner is still current
  — the stale read is a stale *route*, not stale data. The cost is one
  redirect, not corruption.
- **Write on the old owner.** The dangerous case: if the old owner still
  accepts writes after ownership flipped, both shards accept writes to the
  same key — split-brain. The defense is the **fencing epoch**: metadata
  changes bump a version number, every operation carries the version it
  believed, and a node whose version is behind rejects the operation and
  triggers a metadata refresh. MongoDB makes the version check explicit —
  shard and router "must have the same version of the chunks metadata. If the
  metadata is not up-to-date, the operation fails with the StaleConfig error
  and the metadata refresh process is triggered" — and TiKV region epochs and
  CockroachDB range generations are the same idea one layer down. The general
  primitive is the fencing token (see
  [Distributed Locks and Fencing Tokens](../../distributed/fundamentals/fencing-tokens.md)).
- **Two-phase handoff, from the router's seat.** Phase 1 (copy): the old owner
  is still authoritative; the new owner is a follower; routes are unchanged.
  Phase 2 (cutover): a metadata transaction flips ownership atomically and
  bumps the epoch; in-flight operations carrying the old epoch are rejected or
  redirected; clients refresh and retry. The window of wrong answers is thus
  bounded by one round trip plus one metadata refresh — *not* by the duration
  of the copy, which can run for hours.

The design-review question to ask of any sharded system: **what version does a
routing decision carry, and what does a node do when it learns its version is
behind?** If the answer is "nothing — it trusts its local map," you do not
have a routing tier; you have a split-brain in waiting.

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

Alternative: **Saga pattern** (compensating transactions, eventual consistency). Used when 2PC is too slow; see [TCC page](../../backend/patterns/tcc.md).

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
- [Vitess: Vindexes](https://vitess.io/docs/20.0/reference/features/vindexes/) — functional vs. lookup vindexes and consistent lookup variants.
- [CockroachDB: Sharding architecture](https://www.cockroachlabs.com/docs/stable/architecture/overview.html)
- [TiDB architecture](https://docs.pingcap.com/tidb/stable/tidb-architecture)
- [MongoDB sharding documentation](https://www.mongodb.com/docs/manual/sharding/)
- [MongoDB: Config Servers](https://www.mongodb.com/docs/manual/core/sharded-cluster-config-servers/), [Query Router (mongos)](https://www.mongodb.com/docs/manual/core/sharded-cluster-query-router/), and [Sharded Cluster Metadata](https://www.mongodb.com/docs/manual/core/sharded-cluster-metadata/) — the chunk directory, mongos metadata caching, and the StaleConfig version check.
- [Redis Cluster: scaling and hash slots](https://redis.io/docs/latest/operate/oss_and_stack/management/scaling/) — 16,384 slots, slot redirects, client slot-map learning.
- Jeremy Cole, "[Database Sharding at GitHub](https://github.blog/2021-09-09-sharding-github-database/)" (GitHub blog 2021)
- [DynamoDB sharding design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- [Sharding patterns (Microsoft Azure)](https://learn.microsoft.com/en-us/azure/architecture/best-practices/data-partitioning-strategies)
