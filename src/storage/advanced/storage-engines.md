# Storage Engine Internals: LSM, Filters, Learned Structures, and Log-Structured Storage

> Builds on [../sstable.md](../sstable.md), [../lsm-compaction.md](../lsm-compaction.md), [../wal.md](../wal.md), and [../bitcask.md](../bitcask.md). This file covers the LSM amplification trilemma in depth, advanced filter structures (cuckoo, quotient, learned bloom), Bε/fractal trees, WAL/journaling/CoW internals, and snapshot mechanisms.

## LSM Tree Amplification Trilemma

### The Three Amplifications

Every LSM engine trades off between **write amplification (WA)**, **read amplification (RA)**, and **space amplification (SA)**. You cannot minimize all three simultaneously.

```
                   Write Amp
                      ▲
                      │
              Leveled  │  Tiered
                ●     │    ●
                      │
              FIFO    │  Universal
                ●─────│────●
                      │
        ──────────────┼─────────────→ Read Amp
                      │
                    Space Amp (depends on compaction)
```

**Write Amplification** = bytes written to storage / bytes written by client. For RocksDB leveled compaction with L=7 levels and size ratio r=10:

- Each key is rewritten L times (once per level during compaction).
- WA ≈ L × r = 7 × 10 = 70 is the naive upper bound.
- In practice, WA ≈ 10-30 for leveled with good tuning.
- For size-tiered: WA ≈ T-1 where T is the fanout (typically 4-10, so WA ≈ 3-9). Lower WA but higher RA.
- For universal (RocksDB's tiered variant): WA between leveled and size-tiered.

**Read Amplification** = number of SST files checked for a point lookup:

- Leveled: RA = number of levels + number of L0 files ≈ 7 + 4 = 11.
- Size-tiered: RA = number of runs at all levels ≈ 25-100.
- FIFO: RA = 1 (only check newest run, but no range queries).

**Space Amplification** = (live data + garbage) / live data:

- Leveled: SA ≈ 10% (size ratio r, one level may be ~r× the next).
- Size-tiered: SA ≈ T-1 (with T=10, SA ≈ 9, meaning 10× live data on disk). Very wasteful.
- Universal: SA between the two.

### Tuning the Trilemma

| Tuning Knob | Reduces | Increases | Typical Setting |
-------------|---------|-----------|-----------------|
| Increase `write_buffer_size` | WA (fewer flushes) | RA (larger L0) | 64-256 MB |
| Increase `max_write_buffer_number` | WA | Memory usage | 2-4 |
| Decrease `l0_compaction_trigger` | RA (fewer L0 files) | WA (more frequent compaction) | 4 (default) |
| Increase `level_compaction_dynamic_level_bytes` | SA | WA | true (RocksDB default) |
| Use `kCompactionStyleUniversal` | WA | SA, RA | Write-heavy workloads |
| Use `kCompactionStyleFIFO` | WA, SA | RA | Time-series / append-only |

## Advanced Filter Structures

### Bloom Filter Recap

A Bloom filter of size *m* bits with *k* hash functions and *n* inserted elements has false positive rate:

```
FPR ≈ (1 - e^(-k·n/m))^k

Optimal k = (m/n) · ln(2)
Optimal m = -n·ln(FPR) / (ln(2))²

For 1% FPR:  m/n ≈ 9.6 bits/element, k = 7
For 0.1% FPR: m/n ≈ 14.4 bits/element, k = 10
```

Standard Bloom filters are fast (~10-50 ns per query) but have three problems: (1) FPR scales with n, (2) cannot delete, (3) no support for skewed query distributions.

### Cuckoo Filter

A cuckoo filter (Fan et al., 2014) uses a compact hash table with partial-key cuckoo hashing. It supports **deletion** (unlike Bloom) and achieves better space efficiency at low FPRs.

```
Structure: array of buckets, each bucket holds b fingerprints (typically b=4)
Each fingerprint: f bits (e.g., f=8 for 2-3% FPR)

Insert(key):
  fp = fingerprint(hash(key))           // e.g., low 8 bits
  i1 = hash(key)
  i2 = i1 XOR hash(fp)                  // partial-key kick
  // Try to place fp in bucket[i1] or bucket[i2]
  // If both full, kick out existing entry and reinsert (cuckoo path)
  // Max displacement: 500 (then table is too full → resize)

Lookup(key):
  fp = fingerprint(hash(key))
  return fp ∈ bucket[i1] OR fp ∈ bucket[i2]

Delete(key):
  fp = fingerprint(hash(key))
  if fp ∈ bucket[i1]: remove
  elif fp ∈ bucket[i2]: remove
```

| Property | Bloom | Cuckoo |
----------|-------|--------|
| Space (1% FPR) | ~9.6 bits/element | ~7.1 bits/element |
| Space (0.1% FPR) | ~14.4 bits/element | ~9.9 bits/element |
| Supports delete | No (counting Bloom at 2× cost) | Yes |
| Lookup speed | ~k memory accesses | ~2 memory accesses |
| Worst-case insert | O(1) | O(log n) — cuckoo kick chains |
| Load factor | N/A | ~95% (b=4) |

### Quotient Filter

A quotient filter (Bender et al., 2011) divides a hash into **quotient** (bucket index) and **remainder** (stored value). Uses run-length encoding within a metadata bit array (3 bits per slot: occupied, run-start, continuation).

```
Hash h = (q, r)  where q = h / 2^r_bits, r = h mod 2^r_bits

Bit array per slot:
  occupied[q] = 1 if some key hashes to bucket q
  run_start[q] = 1 if slot q starts a cluster run
  continuation[q] = 1 if slot q continues a run

Metadata: 3 bits per slot → 1.5 bytes per slot
With r_bits = 8: 1.5 + 1.0 = 2.5 bytes per slot
```

Quotient filters are **cache-friendly**: a block of 64 slots fits in a cache line. They support fast linear scans (useful for range queries in block-based tables). Used in **Apache Arrow** and research systems.

### Learned Bloom Filters

A learned bloom filter (Kraska et al., SIGMOD 2018) replaces the hash functions with a **machine-learned model** (e.g., a small neural network or decision tree) that predicts membership probability, backed by a standard Bloom filter for the false positives.

```
Architecture:
  query(key)
    p = model.predict(key)          // 0.0 to 1.0, ~O(1) with small model
    if p < τ: return false           // model says "definitely not"
    return bloom_filter.check(key)   // fallback for ambiguous cases

  // Model learns the key distribution → can be much smaller than Bloom
  // If model has 0% FPR in the low-p region, Bloom only needs to handle
  // the hard cases → much smaller Bloom filter

  Sandwich variant:
    if model(key) < τ₁: return false
    if bloom.check(key) == false: return false  // middle Bloom
    if model(key) > τ₂: return true
    return bloom2.check(key)            // second small Bloom for remaining FPs
```

In practice, learned bloom filters show promise for **skewed key distributions** (e.g., time-series where recent keys are queried more often). If the distribution is uniform, they don't outperform standard Bloom. Open challenges: model retraining cost, adversarial distributions, and the overhead of model evaluation vs a few hash computations.

## Bε Trees and Fractal Trees

### B-Tree Merge Problem

B-trees require an in-place update: write a value → seek to leaf → read-modify-write the leaf → possibly split up the tree. Each update touches O(log_B N) pages, each requiring a random I/O.

### Buffer Trees / Bε Trees

A **Bε tree** (Bender, Farach-Colton, et al.) buffers updates at internal nodes and flushes them down during a merge. Each internal node has a **buffer** of pending operations.

```
Bε tree node:
  children[0..B]
  keys[0..B-1]     // pivot keys
  buffer[]           // pending operations (inserts, deletes, updates)
  buffer_max = B^ε   // buffer capacity, ε > 0 (typically ε = 0.5)

Insert(key, value):
  Root receives operation into root.buffer
  When root.buffer is full (B^ε ops):
    Sort buffer, flush ops to appropriate children
    Children receive ops, may cascade flushes downward

Amortized I/O per insert: O((1/B^ε) · log_B N)
  For B=100, ε=0.5: O((1/10) · log N) = one I/O every ~10 inserts
```

The key insight: by buffering B^ε operations before flushing, each flush amortizes the I/O cost over B^ε operations. A Bε tree achieves **O((1/B^ε) · log_B N)** I/Os per operation for both inserts and point queries, which is much better than B-trees for write-heavy workloads.

### Fractal Tree Indexes (TokuDB)

**TokuDB** (acquired by Percona, now Percona TokuDB) implemented fractal trees — a commercial variant of Bε trees. Key innovations:

- **Message passing**: Each buffered operation is a "message" that flows down the tree. Messages can be **inserts, deletes, or even user-defined function applications** (e.g., increment).
- **Full-text search indexing**: Fractal trees enabled fast updates to inverted indexes (avoiding B-tree page splits on the posting list).
- **Compression**: Internal nodes are compressed (fractal prefix compression) to increase effective branching factor.
- **Performance**: TokuDB claimed 10-100× higher write throughput than InnoDB for write-heavy workloads.

TokuDB is now largely superseded by RocksDB/MyRocks (which uses LSM trees instead), but the Bε/fractal tree ideas remain important in theory and in systems like **TokuMX** and research prototypes.

| Property | B-Tree | Bε / Fractal Tree | LSM Tree |
----------|--------|--------------------|----------| 
| Point query | O(log_B N) I/Os | O(log_B N) I/Os | O(L + log_F M) files checked |
| Range query | Excellent (in-order) | Good (merge buffers during scan) | Good (merge from each level) |
| Insert | O(log_B N) I/Os | O((1/B^ε)·log_B N) amortized | O(1) amortized (memtable) |
| Write amplification | 1 (in-place) | ~1 (amortized flush) | L to L+1 levels |
| Space amplification | Minimal (in-place) | Minimal | Moderate (depends on compaction) |

## WAL, Journaling, Copy-on-Write, and Snapshots

### WAL (Write-Ahead Log) Deep Dive

As covered in [../wal.md](../wal.md), WAL guarantees durability before data pages are flushed. Two key implementation details for interviews:

**Group commit**: Instead of fsync-ing after every transaction, batch multiple transactions and issue a single fsync. PostgreSQL and MySQL both use group commit. The WAL buffer is flushed when either: (a) the buffer is full, (b) a transaction commits and requests durability, or (c) a timeout expires.

```
Group commit timeline:
  T1: begin, write WAL records
  T2: begin, write WAL records  
  T1: commit → request fsync
  T2: commit → request fsync  (piggybacks on T1's fsync)
  fsync() fires → both T1 and T2 are durable in one syscall
```

**WAL vs journaling**: WAL logs logical operations (before/after images) applied to data structures. Journaling (filesystem level) logs physical block writes (ext4 JBD2, XFS). The key difference: WAL is at the database/application level and describes logical changes; journaling is at the block level and describes raw block content.

### Copy-on-Write (CoW) Filesystems

ZFS and Btrfs use copy-on-write: every write creates a new block rather than overwriting in place. This has profound implications:

```
CoW write path:
  1. Allocate new block(s)
  2. Write data to new blocks
  3. Update metadata tree (new root block)
  4. Atomically update superblock to point to new root

Advantages:
  - No torn writes (old blocks remain valid until root switch)
  - Snapshots are O(1) — just retain the old root pointer
  - Write ordering doesn't matter (blocks can be written in any order)

Disadvantages:
  - Write amplification (metadata rewritten for every write)
  - Fragmentation (new blocks are not adjacent to old)
  - GC / defragmentation needed to reclaim old blocks
```

### Snapshots and Incremental Snapshots

**Copy-on-Write snapshots** (ZFS, Btrfs): Free — just create a new filesystem root that shares all blocks with the current root. Blocks are only copied when modified (CoW). Cost: O(1) to create, O(changed blocks) over time.

**Log-structured snapshots** (LVM, Ceph RBD): LVM snapshots use a **copy-on-write exception store**: when a block in the origin is about to be written, the old block is copied to the snapshot's exception store. This is the reverse of CoW filesystems — the snapshot gets the old data, not the new.

```
LVM snapshot mechanism:
  Origin volume: [A][B][C][D][E]
  Write to block C:
    1. Copy C_old to snapshot exception store
    2. Write C_new to origin
  Snapshot reads: exception store for C, origin for A,B,D,E

Incremental snapshot (Ceph RBD, LVM2):
  Snap_0: full (baseline)
  Snap_1: delta(Snap_0 → Snap_1) = {blocks changed between 0 and 1}
  Snap_2: delta(Snap_1 → Snap_2)

  To reconstruct Snap_2: apply delta_01, then delta_12 to Snap_0
```

**Incremental snapshot efficiency**: Only changed blocks are transferred, making them ideal for backup to remote storage. Ceph RBD uses rbd export-diff/import-diff to send only changed extents. The RBD diff format includes a bitmap of changed object ranges.

> **Interview Angle**: "How does ZFS achieve both snapshots and checksums without performance degradation?" ZFS stores a 256-bit checksum (fletcher4 or SHA-256) per block in the parent block's pointer (Merkle tree). Snapshots are free (retain old root). The main cost is write amplification from CoW (every write updates the parent blocks up to the root). ZFS mitigates this with the **ARC** (Adaptive Replacement Cache) and **recordsize** tuning.
