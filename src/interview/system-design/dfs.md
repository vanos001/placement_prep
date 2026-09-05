# Design a Distributed File System

> **Difficulty:** ⭐⭐⭐⭐ | **Asked at:** Google (GFS), Amazon (S3), Meta (HDFS) | **Time:** 45 minutes

## 🎯 Problem Statement

Design a distributed file system like GFS (Google File System) or HDFS that:
- Stores petabytes of data across thousands of machines
- Provides high availability and durability
- Supports large file reads and appends
- Handles node failures transparently

---

## Step 1: Requirements

### Functional Requirements
1. Create, read, delete files
2. Append to files (write-once, append-many)
3. Support for large files (GB to TB)
4. Consistent reads after writes
5. Namespace management (directories)

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Storage capacity | Petabytes |
| File size | GB to TB |
| Throughput | GB/s aggregate |
| Durability | 99.999999999% (11 nines) |
| Availability | 99.99% |
| Consistency | Strong (after write acknowledged) |

---

## Step 2: High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                   DISTRIBUTED FILE SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐     ┌──────────────────────────────────────────┐ │
│  │  Client  │────→│           Master Node                    │ │
│  │ Library  │     │  • Namespace management                  │ │
│  └────┬─────┘     │  • Chunk location mapping                │ │
│       │           │  • Chunk allocation                       │ │
│       │           │  • Garbage collection                     │ │
│       │           └────────────────┬─────────────────────────┘ │
│       │                            │                            │
│       │           Metadata         │ Chunk locations            │
│       │           (in-memory)      │                            │
│       │                            │                            │
│  ┌────▼────────────────────────────▼──────────────────────────┐│
│  │                    CHUNK SERVERS                            ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │ Chunk    │  │ Chunk    │  │ Chunk    │  │ Chunk    │  ││
│  │  │ Server 1 │  │ Server 2 │  │ Server 3 │  │ Server N │  ││
│  │  │          │  │          │  │          │  │          │  ││
│  │  │ Chunk A  │  │ Chunk A  │  │ Chunk B  │  │ Chunk C  │  ││
│  │  │ (primary)│  │(replica) │  │ (primary)│  │(replica) │  ││
│  │  │ Chunk C  │  │ Chunk B  │  │ Chunk D  │  │ Chunk A  │  ││
│  │  │(replica) │  │(replica) │  │          │  │(replica) │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 3: Deep Dive

### File Chunking

```
Large File → Fixed-Size Chunks (64 MB each)

Example: 1 GB file
├── Chunk 0: bytes 0 - 67,108,863
├── Chunk 1: bytes 67,108,864 - 134,217,727
├── ...
└── Chunk 15: bytes 1,006,632,960 - 1,073,741,823

Each chunk:
├── Stored as a file on chunk server's local filesystem
├── Has a unique 64-bit chunk handle
├── Replicated 3 times (on different racks)
└── 64 MB size chosen for:
    ├── Large enough to minimize metadata
    ├── Small enough for quick replication
    └── Aligns with typical read patterns
```

### Master Node Design

```
Master Responsibilities:
├── Namespace management (file → chunk mapping)
├── Chunk management (chunk → server mapping)
├── Chunk lease management (primary selection)
├── Garbage collection
└── Re-replication (when chunks are under-replicated)

Master Data Structures (in-memory):
┌─────────────────────────────────────────────┐
│  File Namespace:                            │
│  /dir1/file.txt → [chunk_0, chunk_1, ...]   │
│                                             │
│  Chunk Table:                               │
│  chunk_0 → {                                │
│    version: 5,                              │
│    primary: server_2,                       │
│    replicas: [server_1, server_3, server_7],│
│    lease_expiry: 2025-01-01T00:06:00       │
│  }                                          │
└─────────────────────────────────────────────┘

Persistence:
├── Operation Log (WAL) — All mutations logged
├── Checkpoint — Periodic snapshot of state
├── On recovery: Replay log from last checkpoint
└── Log replicated to backup master
```

### Read Flow

```
Client wants to read file.txt, offset 100MB:

1. Client → Master: "Where are chunks for file.txt?"
2. Master → Client: "Chunk 1 is on servers [S2, S5, S8]"
3. Client caches chunk locations
4. Client → Nearest Chunk Server (S5): "Read chunk 1, offset 32MB"
5. S5 → Client: [data]

Client Library Logic:
├── Divide (file, offset) → (chunk_index, offset_within_chunk)
├── Check cache for chunk locations
├── If cache miss → ask master
├── Read from nearest replica
└── Verify checksums on read
```

### Write Flow (Append)

```
Client wants to append data to file.txt:

1. Client → Master: "Which chunk for file.txt append?"
2. Master: "Chunk 3, primary=S1, replicas=[S2, S3]"
   (If no primary exists, Master grants lease to one replica)

3. Client → Primary (S1): "Append this data"
4. Primary:
   a. Assigns serial number to write
   b. Writes locally
   c. Forwards to replicas: "Write this data with serial #X"
   d. Waits for all replicas to acknowledge
   e. Returns success to client

Consistency:
├── Primary determines write order
├── All replicas apply in same order
├── If primary fails → new primary elected
├── Serial numbers ensure ordering
```

### Replication Strategy

```
Replication Factor = 3

Placement Policy:
├── Different racks (survives rack failure)
├── Different power domains
├── Spread across failure domains

Replica Placement:
  ┌──── Rack 1 ────┐  ┌──── Rack 2 ────┐  ┌──── Rack 3 ────┐
  │  Chunk Server  │  │  Chunk Server  │  │  Chunk Server  │
  │  Replica A     │  │  Replica B     │  │  Replica C     │
  └────────────────┘  └────────────────┘  └────────────────┘

Re-replication Triggers:
├── Chunk server goes down
├── Replica corrupted (checksum mismatch)
├── Disk failure
└── Replication factor changed

Priority:
├── Under-replicated chunks > re-replicating
├── Recent chunks > old chunks
├── Blocking client operations > background
```

### Consistency Model

```
GFS Consistency Guarantees:
├── Defined: All replicas agree, client sees what it wrote
├── Consistent: All replicas agree, but client may see stale
├── Undefined: Replicas may disagree

After a successful write:
├── Serial successful writes → Defined
├── Concurrent successful writes → Consistent but undefined
├── Failed write → Inconsistent

Why "append" instead of "overwrite":
├── Append is idempotent (can retry safely)
├── Append is atomic at record level
├── No need for distributed locking
└── Fits MapReduce/HDFS workloads (write-once, read-many)
```

### Checksumming

```
Data Integrity:
├── Each 64KB block has a 32-bit checksum
├── Checksums stored in separate file on chunk server
├── On write: compute checksum, store with data
├── On read: verify checksum, return error if mismatch

Checksum Verification:
┌─────────────────────────────────────────────┐
│  Read Request                               │
│  ├── Read data block (64 KB)                │
│  ├── Read corresponding checksum            │
│  ├── Compute checksum of read data          │
│  ├── Compare: match → return data           │
│  └── Mismatch → read from replica           │
└─────────────────────────────────────────────┘

Background Scanning:
├── Periodically scan all chunks
├── Detect silent corruption (bit rot)
├── Re-replicate if corruption found
└── Runs during low-traffic periods
```

### Garbage Collection

```
When a file is deleted:
1. Master marks file as deleted (tombstone)
2. Actual deletion happens lazily (GC)

GC Process:
├── Master scans namespace periodically
├── Files with tombstones older than 3 days → remove
├── Orphaned chunks (no file reference) → delete
├── Chunk servers report their chunks → master identifies orphans

Why Lazy Deletion:
├── Simple (no distributed delete protocol)
├── Safe (undo possible within grace period)
├── Efficient (batch deletion)
└── Background (doesn't block operations)
```

### Metadata: The Single Most Load-Bearing Decision

Every architecture decision above is downstream of one question: where does metadata live, and how big does it get? GFS's answer — a single master keeping everything in memory — is still the reference design: "The master stores three major types of metadata: the file and chunk namespaces, the mapping from files to chunks, and the locations of each chunk's replicas. All metadata is kept in the master's memory" [1]. In-memory metadata is not a luxury: "Since metadata is stored in memory, master operations are fast. Furthermore, it is easy and efficient for the master to periodically scan through its entire state in the background" [1] — that scan *is* the garbage collection, re-replication, and rebalancing machinery. A master that must query metadata from disk or from peers cannot do full-state scans, and a DFS without them needs three subsystems to replace it.

**The counterintuitive persistence choice.** Namespace and file-to-chunk mapping are logged persistently (the operation log is "the only persistent record of metadata" and "a logical time line that defines the order of concurrent operations" [1]); chunk locations are not: "The master does not store chunk location information persistently. Instead, it asks each chunkserver about its chunks at master startup and whenever a chunkserver joins the cluster" [1]. The reasoning is a design lesson in itself: a chunkserver is the only authority on what is actually on its disks, so a persisted location map would be a cache that can silently go wrong (disk dies, replica deleted) and need an invalidation protocol anyway. Persist what the master *owns*; poll what the world *owns*.

**The capacity math.** "The master maintains less than 64 bytes of metadata for each 64 MB chunk" and "the file namespace data typically requires less then [sic] 64 bytes per file because it stores file names compactly using prefix compression" [1]. Run the numbers: 100M files at ~64–150 bytes of namespace plus ~10 chunks each puts the whole system's metadata in the low tens of gigabytes — one machine's RAM. GFS measured it in production: master metadata of "only tens of MBs, or about 100 bytes per file on average" [1]. The same arithmetic at 10B files is well over a terabyte — one machine's RAM no more — and the fix is not more disks but sharding the *namespace itself* (a metadata cluster partitioning the directory tree by path, with subtree operations like snapshot becoming multi-shard transactions). Hadoop hit the same wall: the NameNode "keeps an image of the entire file system namespace and file Blockmap in memory" [2], which is why its scaling ceiling was famous.

**The namespace structure.** "GFS logically represents its namespace as a lookup table mapping full pathnames to metadata. With prefix compression, this table can be efficiently represented in memory. Each node in the namespace tree (either an absolute file name or an absolute directory name) has an associated read-write lock" [1], and master operations take locks down the path — acquired in a consistent total order: "they are first ordered by level in the namespace tree and lexicographically within the same level" [1]. That is how one master serializes concurrent creates and snapshots without coarse global locks. Contrast an object store: a flat key space with no tree, no rename-in-place, and metadata trivially sharded by hash (see [Object Storage](../../storage/object-storage.md)). The hierarchy is exactly what resists sharding — a subtree operation can span every shard.

### Consistency Spectrum: From GFS to POSIX

GFS deliberately did not offer POSIX, and its record-append semantics show how much machinery relaxation buys. The guarantee: "A record append causes data (the 'record') to be appended atomically at least once even in the presence of concurrent mutations, but at an offset of GFS's choosing" [1]. At-least-once means side effects: "In addition, GFS may insert padding or record duplicates in between. They occupy regions considered to be inconsistent and are typically dwarfed by the amount of user data" [1]. Clients absorb it: "Each record prepared by the writer contains extra information like checksums so that its validity can be verified. A reader can identify and discard extra padding and record fragments using the checksums," and where duplicates matter, filters "them out using unique identifiers in the records" [1]. Consistency enforcement pushed into a shared application library — the file system provides durability and ordering; the *meaning* of records is the application's problem.

HDFS sits one step stricter: single-writer, write-once. "HDFS supports write-once-read-many semantics on files" [2] — no concurrent append, no record-at-offset ambiguity, so no dedup library needed. Its durability machinery is the classic log-plus-image pair: "The NameNode uses a transaction log called the EditLog to persistently record every change that occurs to file system metadata," while "the entire file system namespace, including the mapping of blocks to files and file system properties, is stored in a file called the FsImage" [2]. Modern cloud-native systems go back toward POSIX: JuiceFS documents "full POSIX compatibility, it allows almost all kinds of object storage to be used as massive local disks" [3] — possible because it splits the layers: "JuiceFS separates 'data' and 'metadata' storage. Files are split into chunks and stored in object storage like Amazon S3. The corresponding metadata can be stored in various databases such as Redis, MySQL, TiKV, and SQLite" [3]. The spectrum in one line: the more your file system promises (POSIX > write-once > at-least-once appends), the more metadata machinery must sit in front of dumb chunk storage.

**Where the chunk size comes from.** GFS's 64 MB was not arbitrary — the paper gives three reasons: "First, it reduces clients' need to interact with the master... Second, since on a large chunk, a client is more likely to perform many operations on a given chunk, it can reduce network overhead by keeping a persistent TCP connection to the chunkserver over an extended period of time. Third, it reduces the size of the metadata stored on the master" [1]. HDFS moved to "a typical block size used by HDFS is 128 MB" [2]. Modern all-SSD systems often shrink it — the trade is symmetric: bigger chunks mean less metadata and fewer master round trips but coarser placement granularity (a hot 64 MB chunk pins its three replicas; load balancing cannot split it) and more internal fragmentation on small files; smaller chunks balance better but the 64-bytes-per-chunk constant starts to dominate master memory. The right interview question: what is your file-size distribution and hot-spot profile?

### Failure Handling as the Core Feature

A DFS is failure-handling machinery with a file API on top. At thousands of disks, a disk dying is a daily background event, and every mechanism below exists because of that base rate.

**Primary-lease mutations.** For each chunk, the master grants one replica a lease as primary; the primary assigns a serial order to mutations and all replicas follow it — ordering without a consensus round per write. The lease is a time-bounded lock (see [Leases](../../distributed/advanced/leases.md)), which buys liveness (the master can reclaim a stalled primary) at the price of lease-expiration races (see [Distributed Locks and Fencing Tokens](../../distributed/fundamentals/distributed-locks.md)); the replication modes it rides on are catalogued in [Database Replication Strategies](../../dbms/advanced/replication-strategies.md).

**Shadow masters: read availability without consensus.** "Moreover, 'shadow' masters provide read-only access to the file system even when the primary master is down. They are shadows, not mirrors, in that they may lag the primary slightly, typically fractions of a second" [1] — and the subtle part: "since file content is read from chunkservers, applications do not observe stale file content. What could be stale within short windows is file metadata" [1]. Shadows replicate only the operation log, not per-write consensus — a deliberate trade of metadata freshness for read availability. A modern design would reach for Raft instead (see [Raft](../../dbms/distributed/raft.md)); note what GFS bought by skipping it.

**Liveness, heartbeats, and re-replication priority.** "Each DataNode sends a Heartbeat message to the NameNode periodically" [2], and the dead-node timeout is deliberately slow: "The time-out to mark DataNodes dead is conservatively long (over 10 minutes by default) in order to avoid replication storm caused by state flapping of DataNodes" [2]. Once a node is declared dead, GFS re-replicates by priority: "Each chunk that needs to be re-replicated is prioritized based on several factors. One is how far it is from its replication goal. For example, we give higher priority to a chunk that has lost two replicas than to a chunk that has lost only one," live files beat recently deleted ones, and "we boost the priority of any chunk that is blocking client progress" [1]. Replication urgency is a scheduler, not a boolean.

**Checksumming and lazy repair.** "A chunk is broken up into 64 KB blocks. Each has a corresponding 32 bit checksum" [1]. Repair happens on read: "If a block does not match the recorded checksum, the chunkserver returns an error to the requestor and reports the mismatch to the master. In response, the requestor will read from other replicas, while the master will clone the chunk from another replica" [1] — corruption is caught at the first reader and fixed by the master, with background scanning as the safety net for cold data.

**The colocation insight.** GFS/HDFS are really *block stores for compute*: MapReduce and Spark schedule tasks onto nodes holding the chunk rather than shipping data over the network — HDFS is explicit: "To minimize global bandwidth consumption and read latency, HDFS tries to satisfy a read request from a replica that is closest to the reader" [2]. An object store inverts this: it is an HTTP blob service for everything, and locality is irrelevant because the network *is* the fabric (see [Object Storage](../../storage/object-storage.md), and the consumer side in [MapReduce](../../distributed/mapreduce/mapreduce.md)). That one difference explains most of the interface divergence: DFS exposes offsets and appends for compute that reads sequentially; object stores expose keys and ranges for clients that are remote anyway.

---

## Step 4: Trade-offs

### Single Master vs Distributed Master
| Approach | Pros | Cons |
|----------|------|------|
| Single master | Simple, consistent | SPOF, scalability limit |
| Distributed master | No SPOF, scalable | Complex, consensus needed |

**GFS choice:** Single master with shadow/backup masters.

### Chunk Size: 64MB vs Smaller
| Size | Pros | Cons |
|------|------|------|
| 64 MB | Less metadata, fewer master lookups | Internal fragmentation |
| 4 KB | No waste | Huge metadata, many lookups |

**Choice:** 64 MB — metadata fits in master memory, sequential reads efficient.

### Replication Factor: 3 vs Erasure Coding
| Approach | Storage Overhead | Durability | Read Performance |
|----------|-----------------|------------|------------------|
| 3x replication | 200% | High | Fast (any replica) |
| Erasure coding (e.g., RS 6+3) | 50% | Very high | Slower (reconstruction) |

**Choice:** 3x for hot data (fast reads), erasure coding for cold data (storage savings).

## Interview Problems

**P1 (mid) — "Why is rename metadata-only in a real file system but a copy-and-delete in an object store?"**
Expected: a file system's namespace is a tree of path entries; rename edits two entries under the parents' locks and is atomic and O(1) — GFS's namespace read-write locks with the level-then-lexicographic ordering exist precisely to serialize this against concurrent creates and snapshots [1]. The chunk data never moves. In an object store, keys are opaque flat strings and "directories" are naming conventions over prefixes; no operation atomically re-keys objects, so rename degrades to list-by-prefix + copy every object + delete — megabytes of network I/O for what felt like free, and a crash midway leaves a split namespace. Rubric: junior says "it's just faster"; mid names the tree vs flat-keyspace difference; senior describes the failure window of copy-based rename and mentions metadata engines (JuiceFS-style [3]) that restore atomic rename by putting a real metadata layer in front of object storage.

**P2 (senior) — "Design listing for a store with 10B keys/objects."**
Expected: the answer depends on the namespace model. Flat keyspace (object store / KV): keys held in lexicographic order, list = range scan with a continuation token, O(page) per request — this is why object stores list beautifully. Snapshot consistency is the trap: a long listing concurrent with writes yields a moving view; solutions include bounded snapshot windows, generation markers, or replaying the op log. Hot prefixes throttle: all list load landing on one shard needs prefix splitting. Hierarchical tree (DFS): a directory listing is a subtree lookup on the master — fast per directory, but the single master's memory and scan rate become the ceiling at 10B files, forcing namespace sharding (the section above). Rubric: junior proposes pagination only; mid addresses concurrent-write consistency; senior ties the listing model back to namespace architecture and shard placement.

## References

1. Ghemawat, S.; Gobioff, H.; Leung, S.-T. "The Google File System." *Proc. 19th ACM SIGOPS Symposium on Operating Systems Principles (SOSP '03)*, pp. 29–43. DOI: [10.1145/945445.945450](https://doi.org/10.1145/945445.945450) — Crossref-verified this session (title/authors/venue checked at api.crossref.org); full PDF fetched from <https://static.googleusercontent.com/media/research.google.com/en//archive/gfs-sosp2003.pdf> (linked from <https://research.google/pubs/the-google-file-system/>, both HTTP 200); all quoted sentences verbatim from the fetched PDF.
2. Apache Hadoop, "HDFS Architecture Guide" — <https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html> — fetched in full this session (HTTP 200); EditLog/FsImage, write-once-read-many, heartbeat timeout, block size, and replica-selection statements quoted verbatim.
3. JuiceFS documentation, "Introduction" — <https://juicefs.com/docs/community/introduction/> — fetched this session (HTTP 200); the POSIX-compatibility and data/metadata-separation sentences quoted verbatim.

*Note:* Bigtable (OSDI '06, USENIX) has no ACM DOI; its USENIX abstract page (<https://www.usenix.org/legacy/events/osdi06/tech/chang.html>, fetched this session — HTTP 200 with a full browser UA; the same URL returns 403 to a bare `Mozilla/5.0` UA) verified title/authors/venue/pages bibliographically only, and no claims in this chapter draw on it.

## 🔗 Cross-References

- [Key-Value Store](./kv-store.md) — Similar distributed storage concepts
- [Architecture Concepts](../../cheatsheets/architecture.md) — Replication, consistency
- [OS Questions](../os-questions.md) — File systems, I/O scheduling
- [DBMS Questions](../dbms-questions.md) — Storage engine internals
- [Object Storage](../../storage/object-storage.md) — the flat-namespace sibling; why S3-style stores are not file systems
- [Database Replication Strategies](../../dbms/advanced/replication-strategies.md) — sync/async/semi-sync modes behind chunk replication
- [Leases](../../distributed/advanced/leases.md) — the time-bounded lock behind primary-lease mutations
- [Raft](../../dbms/distributed/raft.md) — what a modern metadata service would use instead of a replicated local op log
- [Distributed Locks and Fencing Tokens](../../distributed/fundamentals/distributed-locks.md) — the lease-expiration race chunk leases must survive
- [Erasure Coding](../../storage/erasure-coding.md) — the 3×-replication alternative from Step 4, in depth
- [Ceph CRUSH](../../storage/ceph-crush.md) — placement without a persisted location map
- [Haystack / SeaweedFS](../../storage/haystack-seaweedfs.md) — metadata minimization taken further for billions of small files
- [MapReduce](../../distributed/mapreduce/mapreduce.md) — the compute-locality consumer that made DFS a block store
