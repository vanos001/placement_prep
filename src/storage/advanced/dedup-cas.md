# Deduplication and Content-Addressable Storage

> Related: [../blobdb.md](../blobdb.md) (RocksDB BlobDB). Deduplication and content-addressable storage (CAS) are fundamental to backup systems, container registries, blockchain, and distributed build caches.

## Deduplication Fundamentals

### Why Dedup?

Deduplication eliminates redundant copies of data. In practice, dedup ratios vary enormously by workload:

| Workload | Typical Dedup Ratio | Reason |
----------|-------------------|--------|
| Virtual machine images | 10-30× | Same OS base, similar installed software |
| Backup (incremental) | 5-20× | Most blocks unchanged between backups |
| Email archive | 3-5× | Attachments forwarded, quoted replies |
| Source code repositories | 2-5× | Forks, branches, vendored dependencies |
| Encrypted data | ~1× | Encryption makes identical data look random |
| Media (photos/video) | ~1× | Already compressed, low redundancy |

### Chunking Strategies

Dedup systems split data into **chunks** and store only unique chunks. The chunking strategy is the single most important design decision.

**Fixed-size chunking**:

```
File: [AAAA|BBBB|CCCC|DDDD|EEEE]
       chunk0 chunk1 chunk2 chunk3 chunk4

Simple, O(1) per chunk.
Problem: insert 1 byte at start → every chunk boundary shifts → no dedup.
```

**Variable-size (content-defined) chunking**:

```
Rolling hash (Rabin fingerprint):
  window of W bytes, compute rolling hash H
  If H mod D == target: chunk boundary

  min_chunk = 8 KB, max_chunk = 64 KB, target_avg = 32 KB

File:   [AABCA|DEFGHIJKL|MN|OPQR...ST|UVW...]
        chunk0    chunk1      chunk2  chunk3

Insert 1 byte at start:
  [XAABC|A|DEFGHIJKL|MN|OPQR...ST|UVW...]
  Most chunks unchanged → high dedup on small modifications
```

The Rabin fingerprint is computed with a sliding window: H_new = ((H_old - byte_out × base^(W-1)) × base + byte_in) mod P. This is O(1) per byte position. The polynomial P is typically chosen to avoid collisions (e.g., a large prime).

### Chunking Trade-offs

| Parameter | Smaller | Larger |
-----------|---------|--------|
| Chunk size | Better granularity, more metadata | Fewer chunks, less metadata |
| Dedup ratio | Higher (smaller units match) | Lower (more data in each chunk) |
| Metadata overhead | Larger index | Smaller index |
| Random I/O for reassembly | More seeks | Fewer seeks |

Typical production settings: average chunk 32 KB – 1 MB depending on workload. Backup systems (Veeam, Data Domain) use 16-64 KB. Container registries (Docker) use the layer model (effectively whole-file chunking).

### Fingerprinting

Each chunk is identified by a cryptographic hash of its content:

```
fingerprint(chunk) = SHA-256(chunk)  // 256 bits, ~0 collision probability

Index entry: { hash → (volume_id, offset, size) }

Collision risk with SHA-256: 2^(-128) for birthday paradox with 2^128 chunks
  → negligible (2^128 chunks = 10^38 bytes at 1 KB/chunk)

Some systems use a two-level approach:
  weak_hash = Rabin/xxHash (fast, 64-bit) for quick comparison
  strong_hash = SHA-256 (slow, 256-bit) for verification
```

## Content-Addressable Storage (CAS)

### CAS Model

In a CAS system, data is addressed by its **content hash**, not by a human-chosen name. The store guarantees: `get(put(data)) == data`.

```
CAS Operations:
  store(data) → hash = SHA-256(data)
    if hash in index: increment refcount, return hash
    else: write data to storage, add to index, return hash

  retrieve(hash) → data
    verify: SHA-256(data) == hash  (integrity check)
    return data

  delete(hash):
    decrement refcount
    if refcount == 0: mark for garbage collection
```

### Real CAS Systems

| System | Hash Algorithm | Use Case | Scale |
--------|---------------|----------|-------|
| Git | SHA-1 (migrating to SHA-256) | Source control | Billions of objects |
| Docker Registry | SHA-256 | Container image layers | Billions |
| IPFS | SHA-256 (multihash) | Decentralized file sharing | Petabyte |
| Nix store | SHA-256 | Reproducible builds | Millions of paths |
| Btrfs dedup | same as Btrfs checksum | Filesystem dedup | Per-filesystem |
| Restic | SHA-256 | Backup | Petabyte |

### Git's Object Model (CAS in Practice)

Git is a pure content-addressable object store. Every object (blob, tree, commit, tag) is stored as `<type> <size>\0<content>` compressed with zlib, addressed by SHA-1 hash.

```
$ git cat-file -p 3b18e512dba79e4c8300dd08aeb37f8e728b8dad
tree 6cf73f7b8e...\n
The hash = SHA-1("tree 6cf73f7b8e...\n" + tree_entry_list)

Objects are stored loose (one file per object) or packed (multiple objects
in a packfile with delta compression).
```

Git's packfiles use **delta compression**: objects that are similar (e.g., file v1 and file v2 with one line changed) are stored as a delta from a base object. This is a form of dedup at the byte level, on top of the object-level CAS.

## Garbage Collection in Dedup Systems

### Reference Counting vs Mark-and-Sweep

```
Reference counting (Git, Nix, Restic):
  Each chunk has a refcount
  Increment on new reference, decrement on delete
  Problem: cycles (rare in dedup, common in general GC)
  Advantage: O(1) reclamation of unreferenced chunks

Mark-and-sweep (used in some backup systems):
  1. Start from all known roots (snapshots, active files)
  2. Traverse and mark all reachable chunks
  3. Sweep: delete all unmarked chunks
  Advantage: handles cycles naturally
  Disadvantage: requires full scan, needs pause or concurrent implementation
```

### Lock-Free Chunk Reference in Distributed CAS

In distributed systems, reference counting must handle concurrent operations:

```
Distributed CAS store operation:
  1. Client computes hash = SHA-256(chunk)
  2. Client sends (hash, chunk) to storage node
  3. Storage node:
     a. Acquire lock on hash bucket (or use CAS on refcount)
     b. If hash exists: atomic increment refcount → done
     c. If hash not exists: write chunk, set refcount=1 → done

  The critical section is small (one atomic CAS on refcount),
  so lock contention is minimal even with many clients.
```

## Immutable Storage

### Immutability Guarantees

An immutable store guarantees that once data is written, it cannot be modified. This is trivially achieved by CAS (content address = identity; modifying content changes the address).

Benefits:
- **No locks needed for reads**: Readers never see partial writes.
- **No write-write conflicts**: Concurrent writes to the same logical key create different versions.
- **Caching is trivial**: Content never changes, so cache entries never invalidate.
- **Auditability**: Complete history of all data versions.

### Append-Only and Write-Once-Read-Many (WORM)

```
Append-only: New data can be added, but existing data cannot be modified.
  Examples: Kafka log segments, LSM SSTables, blockchain

WORM (Write Once, Read Many): Each address is written exactly once.
  Examples: CD-R, tape (WORM mode), compliance archives

Log-structured merge (LSM) SSTables are append-only by design.
Updates are written as new entries, old entries removed by compaction.
```

### Versioning in Object Storage

S3 supports object versioning: each PUT creates a new version. Deletes create a **delete marker** (a zero-byte version with a delete flag). Old versions are retained until explicitly deleted or expired by a lifecycle policy.

```
S3 versioning timeline:
  PUT obj (v1) → visible, latest=v1
  PUT obj (v2) → v1 still exists, latest=v2
  DELETE obj → v2 still exists, latest=delete_marker
  GET obj → 404 (delete marker hides v2)
  GET obj?versionId=v2 → returns v2
  DELETE obj?versionId=v2 → v2 permanently removed
```

> **Interview Angle**: "Design a deduplication system for VM backups." (1) Content-defined chunking with 64 KB average chunk size. (2) SHA-256 fingerprinting with a two-level index: RAM bloom filter for hot fingerprints, on-disk hash table for the full index. (3) Chunk storage on object store (S3) with refcount in metadata DB. (4) Incremental backup: read previous backup's chunk list, compute rolling hash on new data, only upload new chunks. (5) GC: mark-and-sweep from active snapshots. Expect 10-20× dedup ratio, dominated by unchanged OS/filesystem blocks.
