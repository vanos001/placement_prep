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

## 🔗 Cross-References

- [Key-Value Store](./kv-store.md) — Similar distributed storage concepts
- [Architecture Concepts](../../cheatsheets/architecture.md) — Replication, consistency
- [OS Questions](../os-questions.md) — File systems, I/O scheduling
- [DBMS Questions](../dbms-questions.md) — Storage engine internals
