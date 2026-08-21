# HDFS Internals

The Hadoop Distributed File System (HDFS) is the file system component of Apache Hadoop, designed in 2006 to store very large files (multi-GB to TB) across thousands of commodity servers. It is the basis of the entire Hadoop ecosystem (Hive, Spark, Presto, HBase all read from HDFS) and remains the dominant storage layer for big-data workloads on-premise. This page covers the NameNode/DataNode split, the block report protocol, the read and write paths, and the modernization efforts (federation, erasure coding, observer NameNode) that have kept HDFS relevant in the cloud era.

## The Two-Tier Architecture

HDFS is split into two services:

```text
┌────────────────────────────────────────────────────────┐
│                 NameNode (master)                      │
│   • Maintains file → block → DataNode mapping         │
│   • Single active instance (with Standby for HA)      │
│   • In-memory metadata (~150 bytes per file/block)     │
│   • Receives block reports + heartbeats from DataNodes │
└────────────────────────────────────────────────────────┘
            ▲                          ▲
            │ block reports            │ heartbeats (3 sec)
            │ (every 6 hours)          │
            │                          │
┌───────────┴──────────────┐  ┌────────┴──────────────┐
│    DataNode 1            │  │     DataNode 2        │
│  • Stores blocks locally │  │  • Stores blocks locally
│  • Serves read/write RPCs│  │  • Serves read/write RPCs
│  • Pipelines writes      │  │  • Pipelines writes   │
└──────────────────────────┘  └───────────────────────┘
```

The NameNode is the **single metadata store**. Every file open, every block location, every DataNode state lives in the NameNode's memory. A typical NameNode with 64 GB of RAM can track ~100 million blocks.

The DataNodes are **dumb storage**. They store blocks as files on local disk, serve reads, pipeline writes, and report state to the NameNode. They have no shared state with each other.

## Files, Blocks, and Replicas

HDFS stores files as a sequence of **blocks** (default 128 MB each). Each block is replicated to 3 DataNodes by default:

```text
File: /data/orders-2026.parquet (384 MB)
   │
   ▼
Blocks: B0 (128 MB)  B1 (128 MB)  B2 (128 MB)
   │                  │             │
   ▼                  ▼             ▼
Replicas:           Replicas:      Replicas:
B0 @ DN1, DN2, DN3  B1 @ DN2, DN3, DN4  B2 @ DN3, DN4, DN5
```

The replication factor is configurable per file (`-setrep 5 /path` raises the rep factor to 5). For "hot" data (frequently read), more replicas reduce hot-spot load; for "cold" data (rarely read), fewer replicas save disk.

The default block size of 128 MB is a trade-off:
- Large blocks → fewer blocks per file → less NameNode memory used.
- Small blocks → more parallel reads per file → better scan throughput.

A 1 TB file at 128 MB blocks has 8,192 blocks; at 64 MB blocks, 16,384 blocks. The NameNode memory cost per block (~150 bytes) means a 1 TB file at 128 MB blocks costs 1.2 MB of NameNode RAM — fine. A 1 TB file at 4 KB blocks would cost 384 MB of NameNode RAM — unusable.

## The Block Report Protocol

Each DataNode sends a **block report** to the NameNode every 6 hours (configurable). The report lists every block the DataNode has, with block IDs and lengths. The NameNode uses this to:

1. Discover new DataNodes (the first block report after startup).
2. Detect missing replicas (block X is on DN1, DN2, but not DN3 as the metadata says).
3. Detect over-replicated blocks (block Y has 4 replicas but the target is 3).
4. Detect corrupt blocks (a DataNode reports a CRC mismatch).

Between block reports, the NameNode relies on DataNode heartbeats (every 3 seconds). A DataNode that misses ~10 heartbeats (30 seconds) is declared dead, and the NameNode re-replicates its blocks to other DataNodes.

## Write Path

When a client writes a file to HDFS:

```text
1. Client calls create() on NameNode. NameNode records the file in metadata,
   returns a unique file ID and a list of DataNodes to write to.
2. Client opens a TCP connection to the first DataNode (the "pipeline head").
3. Client writes data in 64 KB packets (default packet size).
4. Each packet flows through the pipeline: DN1 → DN2 → DN3, with each DN
   sending an ack back upstream.
5. When the block fills (128 MB), the client closes the block, asks the NameNode
   for the next block's DataNodes, repeats.
6. When the file closes, the client calls close() on the NameNode. The NameNode
   waits for the DataNodes to ack the final block, then marks the file
   "complete".
```

The pipeline is the key to throughput: data flows in one direction (write), acks flow in the other (read), and the client doesn't have to wait for each DataNode to ack individually. The trade-off is failure: if DN2 fails mid-write, the pipeline breaks and the client must rebuild it.

## Read Path

Reads are simpler:

```text
1. Client calls open() on NameNode. NameNode returns the list of (block, replica
   DataNodes) for the file.
2. Client opens a TCP connection to the closest replica DataNode for each block
   (closest = same rack, same node if possible).
3. Client reads data, advances through blocks as needed.
4. Client calls close() when done.
```

"Closest" is determined by the network topology that the NameNode knows. HDFS assumes a tree topology: `/default-rack/dn-1` vs `/default-rack/dn-2` are same-rack; `/rack-1/dn-3` is different-rack. Reads prefer same-rack, then same-node, then cross-rack.

## NameNode HA and the Standby

A single NameNode is a single point of failure. The HDFS HA solution (since 2.x) uses two NameNodes: an Active and a Standby:

- Both NameNodes read the same edit log from a shared storage (QJM — Quorum Journal Manager, or NFS).
- The Active writes edits to the shared log; the Standby reads them and applies them to its in-memory state.
- Failover uses ZooKeeper for leader election: when the Active fails, the Standby takes over after verifying it has applied all log entries.

The QJM is a 3-node (or 5-node) quorum of JournalNodes that replicate the edit log. The Active must get majority ack from JournalNodes before declaring a write committed. This is essentially a tiny Paxos cluster for the edit log.

## Federation

A single NameNode hits scalability limits:
- Memory: ~100M blocks per 64 GB NameNode RAM.
- Throughput: ~70,000 operations/sec per NameNode.

**Federation** (HDFS 0.23+) splits the namespace across multiple independent NameNodes. Each NameNode owns a subset of the namespace (e.g., `/user`, `/data`, `/tmp` are different NameNodes). There is no shared state; clients must know which NameNode owns which path.

Federation is invisible to legacy Hadoop clients (which assume a single NameNode) — they need updated configurations to use it.

## Erasure Coding

HDFS 3.x added **erasure coding** as an alternative to replication. A file stored with RS-6-3 erasure coding has 6 data + 3 parity blocks (9 total); the storage cost is 9/6 = 150% vs replication's 300%. The trade-off is CPU on read/write and a higher failure tolerance (can lose any 3 of 9 blocks).

Erasure-coded files cannot be appended and have higher read latency (reconstructing a missing block requires reading from multiple DataNodes). HDFS picks the layout based on the file's write pattern: append-only files get replication; write-once files get erasure coding.

## The Observer NameNode

The "Observer NameNode" feature (HDFS 3.4+, 2024) provides **read scaling**: a NameNode that follows the Active's edit log and serves reads at a stale-but-consistent snapshot. This is similar to a "read replica" in databases.

The Observer is consistent within a session: a client that reads from the Observer sees a monotonic view (no going backward in time). It can lag the Active by seconds to minutes, depending on the edit-log replication rate.

This is the basis for serving reads from local Observers in multi-region HDFS deployments — avoiding cross-region round-trips to the Active.

## Common Pitfalls

1. **Small files.** HDFS is optimized for large files. Storing 10 million 1 KB files costs 1.5 GB of NameNode RAM (10M × 150 bytes/block), most of which is wasted. Use [HAR files](https://hadoop.apache.org/docs/current/hadoop-archives/HadoopArchives.html) or [SequenceFile](https://hadoop.apache.org/docs/current/api/org/apache/hadoop/io/SequenceFile.html) to pack many small files into one big one.

2. **Setting `dfs.replication=1` in production.** This eliminates the redundancy HDFS provides. A single disk failure takes the data with it. Always use replication=3 (or erasure coding).

3. **Not tuning `dfs.blocksize`.** The default 128 MB is for Hive/Spark workloads. For Impala/Presto, larger blocks (256 MB or 512 MB) reduce scan-planning overhead. For MapReduce with small mappers, smaller blocks (64 MB) increase parallelism.

4. **Trusting the local network for read affinity.** HDFS's rack awareness assumes a single L2 switch per rack. Modern datacenters have multiple L2 switches per rack; HDFS may route reads cross-switch, adding latency. Use [BlockPlacementPolicy](https://hadoop.apache.org/docs/current/api/org/apache/hadoop/net/BlockPlacementPolicy.html) subclasses to customize.

5. **Forgetting that `hdfs fsck` is read-only.** Many operators expect `fsck` to repair problems, but it only reports them. Use `hdfs dfsadmin -recovery` or the Web UI for actual repair.

6. **The Standby NameNode is not a load balancer.** It cannot serve reads (it only maintains state for failover). Use the Observer NameNode for read scaling.

## References

- [HDFS Architecture documentation](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [HDFS Federation](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/Federation.html)
- [HDFS Erasure Coding](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HDFSErasureCoding.html)
- [HDFS High Availability](https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HDFSHighAvailabilityWithNFS.html)
- [HDFS Observer NameNode (CloudNYU)](https://www.youtube.com/watch?v=cloud-nyu-observer-nn)
- [Apache Hadoop source code](https://github.com/apache/hadoop)
- Konstantin Shvachko, "[The Hadoop Distributed File System](https://research.google/pubs/pub36022/)" (MSST 2010)
