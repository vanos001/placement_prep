# HBase Architecture

Apache HBase is an open-source distributed NoSQL database, modeled after Google's Bigtable (2006) and built on top of Hadoop HDFS. Originally developed at Powerset (acquired by Microsoft) in 2007, HBase was donated to Apache in 2008. It is designed for random read/write access to large datasets (billions of rows, millions of columns) stored on HDFS. This page covers the architecture, the region server model, the storage layout, and the comparison to Cassandra.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  HBase Master (single, HA via ZooKeeper)                   │
│  - Manages region assignment to RegionServers              │
│  - Balances load                                              │
│  - Schema management (table create/alter/drop)              │
└─────────────────────────────────────────────────────────────┘
        │                              │
        │ region assignment            │ ZooKeeper watches
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  RegionServer 1       │    │  RegionServer 2       │
│  - Holds regions A, B │    │  - Holds regions C, D │
│  - Reads/writes HDFS   │    │  - Reads/writes HDFS   │
│  - WAL + MemStore      │    │  - WAL + MemStore      │
└──────────────────────┘    └──────────────────────┘
        │                              │
        ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│  HDFS (underlying storage)                                  │
│  - RegionServer's WAL files                                │
│  - HFiles (sorted, immutable)                              │
└─────────────────────────────────────────────────────────────┘
```

Three roles:
- **HBase Master**: stateless coordinator. Manages metadata (which RegionServer hosts which region). Doesn't serve queries.
- **RegionServer**: serves reads/writes for a set of regions. Each region is a contiguous range of one table's data.
- **ZooKeeper**: cluster coordination. Tracks which RegionServers are alive; the Master uses it for leader election.

## The Data Model

HBase stores data in a sparse, multidimensional sorted map:

```text
(Table, RowKey, ColumnFamily, ColumnQualifier, Timestamp) → Value

Example:
  RowKey: "user:42"
  ColumnFamily: "info"
  Columns:
    info:name (timestamp 1692616800000) → "Alice"
    info:email (timestamp 1692616800000) → "alice@example.com"
  ColumnFamily: "activity"
  Columns:
    activity:login (timestamp 1692616800) → true
    activity:login (timestamp 1692616700) → true
```

The (RowKey, ColumnFamily, ColumnQualifier, Timestamp) tuple uniquely identifies a cell. Multiple versions per cell are kept (multi-version support).

## Regions

A table is divided into "regions", each holding a contiguous range of row keys:

```text
Table: users
  Region 1: rowkeys ["a"-"f")
  Region 2: rowkeys ["f"-"m")
  Region 3: rowkeys ["m"-"z")
```

Each region is hosted by exactly one RegionServer at a time. A region can split (when it grows too large) or merge (when adjacent regions are small).

The default region size is 1-10 GB. Smaller regions mean more regions per server (more parallelism) but more metadata overhead.

## The Write Path

```text
1. Client writes a row.
2. Client locates the RegionServer for the row's region (via ZooKeeper + Master).
3. Client sends the write to the RegionServer.
4. RegionServer:
   a. Appends to the WAL (Write-Ahead Log) on HDFS (durable).
   b. Updates the MemStore (in-memory sorted map).
   c. Acknowledges to client.
5. When MemStore is full (default 128 MB):
   a. Flush to a new HFile on HDFS.
   b. MemStore is cleared.
```

The WAL is replicated to HDFS (3 replicas by default), so it survives RegionServer failure. On RegionServer restart, the WAL is replayed to restore the MemStore.

## The Read Path

```text
1. Client reads a row.
2. RegionServer consults:
   a. Block cache (in-memory cache of recently read blocks).
   b. MemStore (recent writes not yet flushed).
   c. HFiles on HDFS (older data).
3. Merge the latest version of each cell across all sources.
4. Return to client.
```

For a row with multiple HFiles, the read merges them — slow if there are many files. The compaction process merges HFiles.

## Compaction

Like Cassandra, HBase compacts HFiles to reduce read amplification:

- **Minor compaction**: merges a few small HFiles into one. Frequent, low cost.
- **Major compaction**: merges ALL HFiles for a region into one. Less frequent, high cost. Also drops deleted/expired versions.

Major compaction is resource-intensive (re-reads and re-writes the whole region). Production deployments often schedule it during low-traffic windows.

## Bloom Filters

Each HFile has an optional Bloom filter — a probabilistic data structure that says "this key is definitely not in this file" or "this key may be in this file":

```text
Without Bloom filter:
  Read key K → check all HFiles for K (slow with many files).

With Bloom filter:
  Read key K → check Bloom filter per file.
  If Bloom says "definitely not", skip the file.
  If Bloom says "may be", do the file read.
```

Bloom filters reduce read amplification by ~10× for random reads.

## ZooKeeper Coordination

HBase uses ZooKeeper for:
- **RegionServer tracking**: each RegionServer registers with ZK; if it dies, ZK notifies the Master.
- **Master election**: ZK picks one Master; the standby takes over on failure.
- **Region assignment**: the Master writes region assignments to ZK; clients read from ZK (cached).

Without ZK, HBase can't operate. ZK must be highly available (3+ nodes).

## Production Performance

HBase's published performance on a 10-node cluster:
- Write throughput: 100K writes/sec.
- Read latency (random key): 5-20 ms.
- Storage: 10+ TB per node (limited by HDFS capacity).

For comparison: Cassandra on similar hardware does 1M writes/sec. HBase's slower throughput is the cost of strong consistency and HDFS-based durability.

## Production Use Cases

### Time-series at Scale

HBase is widely used for time-series storage where data is in HDFS anyway (Hadoop ecosystem):
- OpenTSDB: a time-series database built on HBase.
- Apache Phoenix: a SQL layer on HBase.

### Bigtable-style Workloads

HBase shines for "Bigtable-like" workloads: billions of rows, millions of columns per row, random read/write access. Examples:
- Web crawler URL state.
- Social media user profiles.
- IoT sensor data.

### Hadoop Integration

HBase integrates with Hadoop MapReduce and Spark:
- MapReduce can read HBase tables as input.
- MapReduce can write to HBase as output.
- Spark can read HBase tables as DataFrames.

This makes HBase a natural choice when you already have a Hadoop cluster and want random access to the data.

## Comparison to Cassandra

| Aspect | HBase | Cassandra |
|--------|-------|-----------|
| Architecture | Master + RegionServers + ZK | P2P (no master) |
| Consistency | Strong (default) | Tunable |
| Replication | HDFS-level | Per-datacenter RF |
| Storage | HDFS (HFile) | Local disk (SSTable) |
| Write throughput | Medium (~100K/sec) | Very high (~1M/sec) |
| Best for | Hadoop ecosystem, strong consistency | High write throughput, multi-DC |

HBase's strength is the Hadoop ecosystem integration; Cassandra's is raw write throughput and multi-DC.

## Common Pitfalls

1. **Forgetting that HBase requires HDFS.** If you don't already have HDFS, you must set it up. This is significant infrastructure.

2. **Forgetting that ZooKeeper must be highly available.** HBase depends on ZK; if ZK is down, HBase is down. Run 3+ ZK nodes.

3. **Forgetting that major compaction is expensive.** Schedule major compaction during low-traffic windows (nights or weekends). Disable auto-major-compaction in production.

4. **Forgetting that the Block cache is per-RegionServer.** A region's data isn't in another RegionServer's cache. Cache hit rate depends on the access pattern.

5. **Forgetting that HBase schema design is critical.** The ColumnFamily + RowKey design affects performance dramatically. A bad design can make queries 100× slower.

6. **Forgetting that region hot-spotting can occur.** If all writes go to one region (e.g., a counter at the same row key), that RegionServer is overloaded. Use salting or hashing to spread writes.

## References

- Chang et al., "[Bigtable: A Distributed Storage System for Structured Data](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/)" (OSDI 2006) — HBase's inspiration
- [Apache HBase documentation](https://hbase.apache.org/book.html)
- [HBase Architecture documentation](https://hbase.apache.org/book.html#arch.overview)
- [HBase RegionServer](https://hbase.apache.org/book.html#regions.arch)
- [HBase + Hadoop integration](https://hbase.apache.org/book.html#mapreduce)
- [Apache Phoenix (SQL on HBase)](https://phoenix.apache.org/)
- [OpenTSDB (time-series on HBase)](http://opentsdb.net/)
- [LWN: HBase overview (2019)](https://lwn.net/Articles/796030/)
