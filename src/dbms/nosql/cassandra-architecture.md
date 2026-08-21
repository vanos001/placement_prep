# Cassandra Architecture

Apache Cassandra is an open-source distributed NoSQL database, originally developed at Facebook in 2008 and open-sourced the same year. It is designed for high write throughput, multi-datacenter replication, and linear horizontal scalability, with eventual consistency. This page covers the architecture, the partitioning model (consistent hashing), the replication strategy, the commit log, and the comparison to other NoSQL databases.

## The Architecture

Cassandra is a peer-to-peer cluster — there is no master node. Every node is equal:

```text
┌─────────────────────────────────────────────────────────────┐
│  Cluster (a logical grouping of N nodes)                   │
│                                                              │
│  Node 1 (replica for tokens A, B, C)                       │
│  Node 2 (replica for tokens B, C, D)                       │
│  Node 3 (replica for tokens C, D, E)                       │
│  ...                                                         │
│  Node N (replica for tokens ..., A, B)                      │
│                                                              │
│  Each node:                                                  │
│    - Holds some data (the primary for some tokens)         │
│    - Holds replicas (for tokens owned by other nodes)        │
│    - Knows the cluster topology (via gossip)                 │
└─────────────────────────────────────────────────────────────┘
```

There is no master, no leader, no coordinator (a "coordinator node" is chosen per query, but it's a transient role).

## Consistent Hashing and Token Ring

Cassandra uses consistent hashing to distribute data:

```text
The keyspace is divided into "tokens" (range [MinToken, MaxToken]).
Each node owns a contiguous range of tokens.

Token ring (simplified):
  MinToken ──────────────── MaxToken
       Node 1      Node 2     Node 3     Node 4
       │           │           │           │
       A-D         D-G         G-J         J-M

A row with partition key K is placed on the node that owns K's hash.
  hash(K) = D → Node 1 (owns A-D).
  hash(K) = F → Node 2 (owns D-G).
```

When a new node joins, it takes over a range from an existing node (splitting the ring). When a node leaves, its range is merged into a neighbor. Only the affected range moves.

### Virtual Nodes (vnodes)

Cassandra 1.2 (2013) added "virtual nodes" — each physical node owns many small token ranges instead of one large one. Default: 256 vnodes per node.

Benefits:
- A node joining/leaving affects a small slice of multiple existing nodes (not one big slice).
- Better load balancing (no need to manually assign token ranges).
- Heterogeneous nodes (a faster node can have more vnodes).

Trade-off: data is more scattered; reads may touch more nodes.

## Replication Strategies

Cassandra replicates data across multiple nodes for fault tolerance:

### SimpleStrategy

Replication factor N means data is on N consecutive nodes in the ring (in token order).

```text
RF=3, Node 1 owns token A:
  Primary: Node 1
  Replica 1: Node 2 (next in ring)
  Replica 2: Node 3 (next-next in ring)
```

Used for single-datacenter clusters. Simple but doesn't respect datacenter boundaries.

### NetworkTopologyStrategy

Replication factor is specified per datacenter:

```sql
CREATE KEYSPACE my_ks WITH replication = {
  'class': 'NetworkTopologyStrategy',
  'us_east': 3,    -- 3 replicas in US-East
  'eu_west': 2,    -- 2 replicas in EU-West
  'ap_south': 2    -- 2 replicas in AP-South
};
```

Within each datacenter, replicas are placed on different racks (for fault tolerance against rack failures).

This is the standard for multi-datacenter deployments.

## The Write Path

Cassandra's write path is highly optimized:

```text
1. Client sends write to any node (the "coordinator").
2. Coordinator hashes the partition key, finds the primary node.
3. Coordinator sends the write to all replicas (parallel).
4. Each replica:
   a. Appends to commit log (on disk; durable).
   b. Writes to memtable (in memory; indexed by partition key).
   c. Acknowledges back to coordinator.
5. Coordinator waits for a configurable number of acks (consistency level).
6. Coordinator returns success to client.
```

The write is durable as soon as it's in the commit log. The memtable is read for queries; when full, it's flushed to an SSTable on disk (a "sorted string table").

## The Read Path

Reads are more complex than writes:

```text
1. Client sends read to any node (the "coordinator").
2. Coordinator hashes the partition key, finds the primary node.
3. Coordinator sends read to the replicas (parallel).
4. Each replica returns:
   a. The data from its memtable (in-memory).
   b. The data from its SSTables (on disk, with row cache).
5. Coordinator compares results:
   a. If they match → return.
   b. If they differ → read repair: pick the latest, write back to all replicas.
6. Return result to client.
```

The "read repair" is Cassandra's anti-entropy mechanism: replicas that are behind catch up on every read. This makes Cassandra eventually consistent (with tunable consistency).

## Consistency Levels

The client chooses a consistency level (CL) per query:

- `ONE`: wait for 1 replica's ack.
- `QUORUM`: wait for ⌈(RF/2) + 1⌉ replicas' acks.
- `ALL`: wait for all replicas' acks.
- `LOCAL_QUORUM`: quorum within the local datacenter.
- `EACH_QUORUM`: quorum in each datacenter.
- `LOCAL_ONE`: 1 ack from local datacenter.

For writes:
- CL=ONE is fast but can lose data on failure (1 of N replicas has the write).
- CL=QUORUM ensures that a subsequent read at QUORUM sees the write (≥2f+1 replicas acked, ≥2f+1 read, intersection ≥ f+1).

For reads:
- CL=ONE is fast but may return stale data (one replica might not have the latest write).
- CL=QUORUM returns the latest write (by timestamp).

The "strong consistency" formula: write at QUORUM, read at QUORUM.

## The Commit Log and SSTable

### Commit Log

An append-only log of all writes. On a node restart, the commit log is replayed to restore the memtable state. The commit log is on a separate disk for higher throughput (sequential writes).

### SSTable

An immutable on-disk file containing sorted rows. Once written, an SSTable doesn't change. New writes go to the memtable; old SSTables stay.

### Compaction

The compaction process merges multiple SSTables into one:
- Reads each SSTable (in key order).
- For each key, picks the latest value (by timestamp).
- Writes a new, merged SSTable.
- Deletes the old SSTables.

Compaction reduces read amplification (fewer SSTables to check) and reclaims space (deleted rows are dropped).

Cassandra has multiple compaction strategies:
- **SizeTieredCompactionStrategy**: groups SSTables of similar size. Good for write-heavy workloads.
- **LeveledCompactionStrategy**: levels of SSTables; each level is sorted. Better read performance, more write amplification.
- **TimeWindowCompactionStrategy**: groups by time window. Good for time-series.

## Production Performance

Cassandra's published performance on a 6-node cluster:
- Write throughput: 1M writes/sec (with RF=3).
- Read latency (CL=ONE): 1-5 ms.
- Read latency (CL=QUORUM): 5-20 ms.
- Storage per node: ~1 TB typical, up to ~10 TB.

For comparison: MongoDB sharded cluster ~500K writes/sec; HBase ~100K writes/sec. Cassandra's strength is raw write throughput.

## Production Use Cases

### Time-series Logging

```sql
CREATE TABLE events (
  user_id text,
  event_time timestamp,
  event_type text,
  properties map<text, text>,
  PRIMARY KEY ((user_id), event_time)
) WITH CLUSTERING ORDER BY event_time DESC;

-- Partition key is (user_id); clustering key is event_time.
-- Each user's events are in one partition, sorted by time.
```

The partition key is hashed → user's events go to one node, in time-sorted order.

### Activity Feed (Instagram-style)

```sql
CREATE TABLE activity_feed (
  user_id text,
  feed_id timeuuid,
  activity text,
  PRIMARY KEY ((user_id), feed_id)
) WITH CLUSTERING ORDER BY feed_id DESC;

-- Read the latest 50 activities for a user
SELECT * FROM activity_feed WHERE user_id = 'alice' LIMIT 50;
```

### Counter Tables

```sql
CREATE TABLE counters (
  id text PRIMARY KEY,
  count counter
);

-- Atomic counter increment
UPDATE counters SET count = count + 1 WHERE id = 'page_views';
```

Cassandra's counters are eventually consistent; concurrent increments are merged via timestamps.

## Common Pitfalls

1. **Choosing a partition key with too high cardinality.** A partition key per user (1M users) → 1M partitions → too many small SSTables. Choose a key with bounded cardinality per node (e.g., user_id with ~10K users per partition).

2. **Choosing a partition key with too low cardinality.** A single partition key (e.g., all users) → one giant partition that doesn't fit on one node. Use a more granular key.

3. **Forgetting that Cassandra's schema is "CQL" (Cassandra Query Language), not SQL.** CQL looks like SQL but is much more restrictive (no JOINs across tables, no aggregates other than count).

4. **Forgetting that tombstones (deletes) are real writes.** A `DELETE` writes a tombstone marker; reads must skip tombstoned rows. Too many tombstones slow reads. Use TTL for time-bounded data (auto-expires) instead of explicit deletes.

5. **Forgetting that CL=QUORUM doesn't mean "consistent" with concurrent writes.** Two clients writing the same key at QUORUM both succeed; the latest timestamp wins (last-writer-wins). Use LWT (lightweight transactions) for true serializability, at a 4× latency cost.

6. **Forgetting that repairs must run periodically.** If a replica is down during a write, it may have stale data when it comes back. Run `nodetool repair` periodically (typically weekly) to bring replicas in sync.

## Comparison to Other NoSQL DBs

| Aspect | Cassandra | MongoDB | DynamoDB | HBase |
|--------|-----------|---------|----------|-------|
| Sharding | Consistent hashing | mongos router | AWS-managed | Region server |
| Consistency | Tunable (per query) | Strong (default) | Tunable | Strong |
| Replication | Per-datacenter RF | Replica sets | AWS-managed | HDFS replication |
| Write throughput | Very high | Medium | Very high (AWS) | Medium |
| Best for | Time-series, write-heavy | Flexible queries | Cloud-managed | Hadoop ecosystem |

Cassandra excels at write-heavy workloads with multi-datacenter replication. MongoDB is more flexible for queries. DynamoDB is the AWS-managed option.

## References

- Lakshman & Malik, "[Cassandra: A Decentralized Structured Storage System](https://www.cs.cornell.edu/projects/ladis2009/papers/lakshman-ladis2009.pdf)" (LADIS 2009)
- [Apache Cassandra documentation](https://cassandra.apache.org/doc/latest/)
- [Cassandra Architecture documentation](https://cassandra.apache.org/doc/latest/cassandra/architecture/)
- [Cassandra Compaction strategies](https://cassandra.apache.org/doc/latest/cassandra/operating/compaction.html)
- [Cassandra Consistency Levels](https://cassandra.apache.org/doc/latest/cassandra/developing/data-density.html)
- [DataStax: Cassandra Best Practices](https://docs.datastax.com/en/cassandra-oss/3.0/cassandra/operations/)
- [LWN: Cassandra overview (2020)](https://lwn.net/Articles/820130/)
