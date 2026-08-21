# MongoDB Sharding

MongoDB sharding is the horizontal-scaling mechanism for MongoDB, distributing data across multiple replica sets called "shards". Each shard holds a subset of the collection's data; a "mongos" router routes queries to the appropriate shards. This page covers the sharding architecture, the shard key, the balancer, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  mongos (router) — multiple instances, stateless           │
│  - Receives queries from clients                             │
│  - Routes to the appropriate shard(s)                        │
│  - Merges results                                            │
└─────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Shard 1 (replica set)│    │  Shard 2 (replica set)│
│  - Primary + 2 replicas│    │  - Primary + 2 replicas│
│  - Holds chunks A-M    │    │  - Holds chunks N-Z    │
└──────────────────────┘    └──────────────────────┘
        ▲
        │ cluster metadata (config servers)
┌──────────────────────────────────────────────────────────┐
│  Config Server Replication Set (CSRS)                     │
│  - Tracks chunk → shard assignment                       │
│  - Tracks cluster metadata                               │
└──────────────────────────────────────────────────────────┘
```

Three roles:
- **mongos**: stateless router. Clients connect to mongos, which routes queries.
- **Shard**: a replica set holding a subset of the data. Each shard has a primary and N replicas.
- **Config Server**: a special replica set (CSRS) holding cluster metadata: which chunks are on which shards, the shard key ranges, the balancer state.

## The Shard Key

The shard key is a field (or compound field) that determines which shard a document goes to. The choice of shard key is the most important decision in MongoDB sharding — it can't be changed easily (since MongoDB 4.2, you can reshard a collection, but it's expensive).

```javascript
// Enable sharding on a database
sh.enableSharding("mydb");

// Choose the shard key for a collection
sh.shardCollection("mydb.orders", { "customer_id": 1, "order_date": 1 });
// "1" means ascending; the compound key is (customer_id, order_date).
```

Documents are partitioned by ranges of the shard key. MongoDB creates "chunks" of contiguous shard key ranges, each ~64 MB by default. Chunks are placed on shards.

```text
Shard 1 holds chunks:
  [MinKey, 1000)
  [2000, 3000)
  [5000, 6000)

Shard 2 holds chunks:
  [1000, 2000)
  [3000, 4000)
  [6000, MaxKey)
```

A query `WHERE customer_id = 1234` is routed to the shard holding the chunk containing 1234 (in this case, Shard 2). A query `WHERE customer_id > 4000` is routed to all shards (broadcast).

## Hashed vs. Ranged Shard Keys

Two types of shard keys:

### Ranged Shard Key (default)

```javascript
sh.shardCollection("mydb.orders", { "order_id": 1 });
```

Documents are partitioned by ranges. Adjacent keys are in the same chunk. Pros: range queries hit one shard. Cons: hot inserts (e.g., auto-incrementing IDs) overload one shard.

### Hashed Shard Key

```javascript
sh.shardCollection("mydb.orders", { "order_id": "hashed" });
```

Documents are partitioned by hash of the key. Adjacent keys are in different chunks. Pros: even distribution of inserts (no hot shard). Cons: range queries hit all shards.

For auto-incrementing IDs (e.g., timestamps), use hashed. For sequential but bounded ranges (e.g., customer IDs), use ranged.

## The Balancer

The balancer is a background process that runs on the config server (since MongoDB 3.4). It periodically checks chunk distribution and migrates chunks between shards to balance:

```text
1. Balancer wakes up (every few seconds).
2. Checks if any shard has > 8 chunks more than the average.
3. If yes, picks the chunk to migrate (usually the most-recently-modified chunk).
4. Initiates migration:
   a. Source shard sends the chunk's data to the destination shard.
   b. Destination shard replicates the data to its replicas.
   c. Once all replicas are in sync, the config server updates the chunk→shard mapping.
   d. Source shard deletes its copy.
5. Sleeps, repeats.
```

Migration is online — the chunk is queryable throughout. The "transfer" phase takes seconds (depends on chunk size and network); the "delete" phase takes longer (the source waits for in-flight queries to finish).

## Query Routing

The mongos router has the chunk→shard map (cached from the config server). For each query:

- **Targeted query** (uses shard key in predicate): routes to the shards holding matching chunks. Returns merged results.
- **Broadcast query** (no shard key in predicate): routes to ALL shards, merges results.

```javascript
// Targeted: hits 1 shard
db.orders.find({ customer_id: 1234 });

// Targeted: hits shards containing [1000, 2000)
db.orders.find({ customer_id: { $gte: 1000, $lt: 2000 } });

// Broadcast: hits all shards
db.orders.find({ total: { $gt: 100 } });
```

Broadcasts are slower (N shards in parallel + merge). For OLTP workloads, design the schema so most queries are targeted.

## Shard Key Selection Patterns

### Pattern 1: Hashed key for high-write workloads

```javascript
sh.shardCollection("logs.events", { "_id": "hashed" });
```

For event/log ingestion where writes are uniformly distributed, hashed shard keys spread load.

### Pattern 2: Compound key for tenant isolation

```javascript
sh.shardCollection("mydb.orders", { "tenant_id": 1, "order_id": 1 });
```

For multi-tenant SaaS: each tenant's data is on a contiguous range. Queries scoped to one tenant hit one shard.

### Pattern 3: Time-range shard for archival

```javascript
sh.shardCollection("logs.events", { "timestamp": 1 });
```

For time-series: each chunk is a contiguous time range. Old chunks can be moved to cheaper shards or dropped.

## Zones

Zones (formerly "tag-aware sharding") let you pin chunks to specific shards:

```javascript
// Create a zone for EU customers on the EU shard
sh.addShardTag("shard-eu", "EU");
sh.addTagRange("mydb.users", { region: "EU" }, { region: "EU\x00" }, "EU");

// EU customer documents go to shard-eu.
```

This is useful for:
- **Data residency**: EU customer data must be in the EU.
- **Hot/cold tiering**: hot data on SSD shards, cold data on HDD shards.
- **Geographic locality**: customers near a datacenter query the local shard.

## Production Performance

MongoDB sharding performance on a 4-shard cluster:
- Write throughput: 4× single-shard throughput (~50K writes/sec).
- Read throughput: 4× single-shard throughput.
- Cross-shard query latency: 2-5× single-shard (broadcast + merge).
- Migration time: ~1 minute per 1 GB chunk (network-bound).

For comparison: Cassandra's sharding is automatic and doesn't need a balancer; MongoDB's is more manual but more flexible.

## Common Pitfalls

1. **Choosing a monotonically increasing shard key (ranged).** Auto-incrementing IDs or timestamps cause all inserts to go to the same shard (the one holding the "max" range). Use hashed shard keys for monotonic data.

2. **Choosing a low-cardinality shard key.** A field with 3 distinct values can have only 3 chunks; the balancer can't distribute beyond 3 shards. Use high-cardinality fields.

3. **Forgetting that the shard key is part of the unique index.** A unique index must include the shard key as a prefix (otherwise, uniqueness can't be enforced across shards).

4. **Forgetting that changing the shard key requires "resharding".** MongoDB 4.2+ supports resharding, but it's expensive (full data migration). Choose carefully upfront.

5. **Forgetting that broadcasts are slow.** A `find({ non_shard_key_field: ... })` hits all shards. Add an index on the non-shard field, but the broadcast cost remains.

6. **Forgetting that the balancer competes with foreground traffic.** During migrations, the source shard serves queries and sends data to the destination. For high-write workloads, schedule migrations during low-traffic windows.

## Comparison to Cassandra

| Aspect | MongoDB Sharding | Cassandra |
|--------|-------------------|-----------|
| Sharding scheme | Range or hash of shard key | Hash (consistent hashing) |
| Balancer | Central (config server) | None (consistent hashing distributes) |
| Routing | mongos router | Client-side (every node knows the ring) |
| Failure model | Shard is a replica set | Each node has its own data |
| Best for | Flexible queries, multi-tenant | Write-heavy, simple key access |

MongoDB gives more query flexibility (range queries, joins); Cassandra gives higher write throughput and simpler operations.

## References

- [MongoDB Sharding documentation](https://www.mongodb.com/docs/manual/sharding/)
- [MongoDB: Choose a Shard Key](https://www.mongodb.com/docs/manual/core/sharding-choose-a-shard-key/)
- [MongoDB: Balancer](https://www.mongodb.com/docs/manual/core/sharding-balancer-administration/)
- [MongoDB 4.2: Reshard a collection](https://www.mongodb.com/blog/post/resharding-a-collection-in-mongodb-42)
- [MongoDB Zones](https://www.mongodb.com/docs/manual/core/tag-aware-sharding/)
- [MongoDB Architecture (MongoDB blog)](https://www.mongodb.com/blog/post/mongodb-architecture)
- [LWN: MongoDB sharding (2019)](https://lwn.net/Articles/796030/)
