# Log-Structured Merge Trees (LSM Trees)

## Overview

A Log-Structured Merge Tree (LSM tree) is a data structure optimized for **write-heavy workloads**. Instead of updating data in-place (like B-trees), LSM trees buffer writes in memory and periodically flush them to disk as sorted, immutable files. This converts random I/O into sequential I/O, making writes extremely fast at the cost of potentially slower reads.

LSM trees power many modern databases: **RocksDB** (Facebook), **LevelDB** (Google), **Cassandra**, **HBase**, **ScyllaDB**, **CockroachDB** (via RocksDB/Pebble), and **TiKV** (via RocksDB).

## Detailed Explanation

### Why LSM Trees?

```mermaid
flowchart TD
    A["B-Tree Write Problem"] --> B["Each write = random I/O<br/>(find page, update in-place)"]
    B --> C["On HDD: ~10ms per write<br/>On SSD: ~100μs per write"]
    C --> D["LSM Solution:<br/>Buffer in memory, write sequentially"]

    style A fill:#ffcdd2
    style D fill:#c8e6c9
```

| Workload | B-Tree | LSM Tree |
|----------|--------|----------|
| **Write-heavy** | Slow (random I/O) | Fast (sequential I/O) |
| **Read-heavy** | Fast (O(log N) tree) | Slower (check multiple levels) |
| **Mixed** | Good | Good with tuning |
| **Space** | Some fragmentation | Higher amplification during compaction |

### LSM Tree Architecture

```mermaid
flowchart TD
    subgraph Memory["In-Memory"]
        WAL2["WAL<br/>(durability)"] --> MT["Memtable<br/>(sorted, in-memory)"]
    end

    subgraph Disk["On-Disk"]
        L0["Level 0<br/>SSTables (overlapping)"]
        L1["Level 1<br/>SSTables (non-overlapping)"]
        L2["Level 2<br/>SSTables (non-overlapping)"]
        L0 --> L1
        L1 --> L2
    end

    MT -->|"Flush when full"| L0
    L0 -->|"Compaction"| L1
    L1 -->|"Compaction"| L2

    style Memory fill:#e1f5fe
    style Disk fill:#fff3e0
```

### Components in Detail

#### 1. Memtable

The memtable is an in-memory sorted data structure that absorbs all incoming writes.

```mermaid
flowchart TD
    A["Write: SET key=5, value='hello'"] --> B["Append to WAL"]
    B --> C["Insert into Memtable"]
    C --> D{"Memtable full?<br/>(e.g., 64MB)"}
    D -->|No| E["Continue accepting writes"]
    D -->|Yes| F["Freeze memtable → Immutable Memtable"]
    F --> G["Flush to disk as SSTable"]
    G --> H["Create new empty memtable"]

    style C fill:#c8e6c9
    style G fill:#e1f5fe
```

**Common memtable implementations:**

| Data Structure | Pros | Cons | Used By |
|---------------|------|------|---------|
| **Skip List** | O(log N) insert/lookup, lock-free variants | Higher memory overhead | RocksDB, LevelDB |
| **Red-Black Tree** | O(log N), cache-friendly | Harder to make concurrent | Some custom engines |
| **Sorted Array** | Cache-friendly, compact | O(N) insert | Rarely used |
| **Hash Table** | O(1) lookup | Not sorted → bad for range scans | Redis (for dict) |

```mermaid
flowchart LR
    subgraph SkipList["Skip List (RocksDB default)"]
        direction TB
        HEAD --> L1["Level 3: HEAD → 50 → NIL"]
        HEAD --> L2["Level 2: HEAD → 10 → 30 → 50 → NIL"]
        HEAD --> L3["Level 1: HEAD → 5 → 10 → 20 → 30 → 40 → 50 → NIL"]
    end

    style SkipList fill:#e1f5fe
```

#### 2. SSTable (Sorted String Table)

An SSTable is an immutable, sorted file on disk containing key-value pairs.

```mermaid
flowchart TB
    subgraph SSTable["SSTable Structure"]
        direction TB
        DATA["Data Block 1<br/>key1:val1, key2:val2, ..."]
        DATA2["Data Block 2<br/>key101:val101, ..."]
        IDX["Index Block<br/>key1→Block1 offset<br/>key101→Block2 offset"]
        FILTER["Bloom Filter<br/>(probabilistic membership)"]
        META["Footer<br/>(index block offset, magic number)"]

        DATA --> DATA2
        DATA2 --> IDX
        IDX --> FILTER
        FILTER --> META
    end

    style DATA fill:#e1f5fe
    style IDX fill:#fff3e0
    style FILTER fill:#c8e6c9
    style META fill:#ffcdd2
```

**SSTable on-disk format (simplified, RocksDB):**

```
┌─────────────────────────────────┐
│ Data Block 0                    │  ← Sorted key-value pairs
│  [key_len][key][val_len][val]   │     with prefix compression
│  ...                            │
├─────────────────────────────────┤
│ Data Block 1                    │
│  ...                            │
├─────────────────────────────────┤
│ Meta Block: Bloom Filter        │  ← "Is key X in this SSTable?"
├─────────────────────────────────┤
│ Meta Block: Properties          │  ← Smallest/largest key, count
├─────────────────────────────────┤
│ Index Block                     │  ← Maps last key of each data block
├─────────────────────────────────┤
│ Footer (fixed size)             │  ← Points to index block
└─────────────────────────────────┘
```

#### 3. Write Path (Putting It All Together)

```mermaid
sequenceDiagram
    participant C as Client
    participant WAL2 as WAL
    participant MT as Memtable
    participant L0 as Level 0 SSTables
    participant L1 as Level 1 SSTables

    C->>WAL2: SET user:1001 → "Alice"
    WAL2->>WAL2: Append to WAL file, fsync
    WAL2->>MT: Insert into memtable (skip list)
    Note over MT: Memtable is 63MB...

    C->>WAL2: SET user:1002 → "Bob" (memtable now 64MB!)
    WAL2->>MT: Insert triggers flush
    MT->>L0: Freeze memtable, write SSTable to L0
    Note over MT: Create new empty memtable
    L0->>L0: Now has 3 SSTables (overlapping keys)
    L0->>L1: Compaction: merge L0 SSTables into L1
```

#### 4. Read Path

Reads are more complex because data may be in the memtable, any L0 SSTable, or any level below:

```mermaid
flowchart TD
    A["Read: GET key=1001"] --> B["Check Memtable"]
    B -->|Found| Z["Return value"]
    B -->|Not found| C["Check Immutable Memtable (if any)"]
    C -->|Found| Z
    C -->|Not found| D["Check Level 0 SSTables (newest first)"]
    D -->|Found| Z
    D -->|Not found| E["Check Level 1 SSTables"]
    E -->|Found| Z
    E -->|Not found| F["Check Level 2..."]
    F -->|Not found| G["Return NOT FOUND"]

    style Z fill:#c8e6c9
    style G fill:#ffcdd2
```

**Optimizations for reads:**

```mermaid
flowchart TD
    A["Read Optimizations"] --> B["Bloom Filters<br/>Skip SSTables that definitely<br/>don't contain the key"]
    A --> C["Block Cache<br/>Cache hot data blocks in memory"]
    A --> D["Key Hints / Index<br/>Binary search within SSTable"]
    A --> E["Fence Pointers<br/>Sparse index for block lookup"]

    style B fill:#c8e6c9
    style C fill:#e1f5fe
    style D fill:#fff3e0
    style E fill:#fff3e0
```

#### 5. Bloom Filters

A Bloom filter is a probabilistic data structure that answers "Is this key *definitely not* in the SSTable?" with zero false negatives:

```mermaid
flowchart LR
    A["Key 'alice'"] --> B["Hash functions:<br/>h1=3, h2=7, h3=11"]
    B --> C["Set bits 3, 7, 11<br/>in Bloom filter"]
    C --> D["Lookup 'alice':<br/>Check bits 3, 7, 11"]
    D --> E{"All set?"}
    E -->|Yes| F["Maybe in SSTable<br/>(could be false positive)"]
    E -->|No| G["Definitely NOT in SSTable<br/>(zero false negatives)"]

    style F fill:#fff3e0
    style G fill:#c8e6c9
```

| Property | Value |
|----------|-------|
| False positive rate | ~1% with 10 bits/key |
| False negative rate | 0 (guaranteed) |
| Used for | Avoiding unnecessary SSTable reads |
| RocksDB default | 10 bits per key |

#### 6. Range Queries and Iterators

LSM trees support efficient range scans via **merge iterators** that walk all levels simultaneously:

```mermaid
flowchart TD
    A["Range scan: WHERE key BETWEEN 100 AND 200"] --> B["Create MergeIterator"]
    B --> C["Sub-iterator: Memtable"]
    B --> D["Sub-iterator: L0-SST1"]
    B --> E["Sub-iterator: L0-SST2"]
    B --> F["Sub-iterator: L1-SST3"]
    B --> G["Sub-iterator: L2-SST4"]

    C --> H["Priority Queue<br/>(min-heap by key)"]
    D --> H
    E --> H
    F --> H
    G --> H

    H --> I["Yield keys in sorted order<br/>(skipping duplicates/tombstones)"]

    style H fill:#fff3e0
    style I fill:#c8e6c9
```

### Tombstones (Deletions)

LSM trees are append-only, so deletions are handled with **tombstone markers**:

```mermaid
sequenceDiagram
    participant C as Client
    participant MT as Memtable
    participant SST as SSTable

    C->>MT: DELETE key=1001
    MT->>MT: Insert tombstone: key=1001 → TOMBSTONE

    Note over MT: Later, during compaction...
    MT->>SST: Merge: if key=1001 has tombstone<br/>and exists in older SSTable,<br/>remove both entries
```

**Problem:** Tombstones consume space until compaction runs. A "range tombstone" (`DELETE WHERE key BETWEEN 100 AND 200`) is more efficient than individual tombstones.

### LSM in Different Databases

```mermaid
flowchart TD
    subgraph LevelDB["LevelDB (Google)"]
        direction TB
        L1[Single-threaded compaction]
        L2[Level-based compaction only]
        L3[Two memtables (active + immutable)]
    end

    subgraph RocksDB["RocksDB (Facebook)"]
        direction TB
        R1[Multi-threaded compaction]
        R2[Level-based + Universal + FIFO]
        R3[Column families]
        R4[Prefix Bloom filters]
        R5[Block cache + compressed cache]
    end

    subgraph Cassandra["Cassandra"]
        direction TB
        C1[LSM per table]
        C2[Size-tiered + Leveled + TWCS]
        C3[Partition-level sorting]
    end

    style LevelDB fill:#e1f5fe
    style RocksDB fill:#c8e6c9
    style Cassandra fill:#fff3e0
```

| Feature | LevelDB | RocksDB | Cassandra |
|---------|---------|---------|-----------|
| **Compaction** | Level-based only | 3 strategies | 3 strategies |
| **Concurrency** | Single compaction thread | Multi-threaded | Multi-threaded |
| **Column Families** | No | Yes | Tables |
| **Bloom Filters** | Yes | Yes (prefix too) | Yes |
| **Compression** | Snappy | LZ4, Zstd, Snappy | LZ4, Snappy |
| **Transactions** | No | Optimistic txn | Lightweight txn |
| **Merge Operators** | No | Yes | No |

## Cross-References

- [Compaction](./compaction.md) — Strategies for merging and cleaning SSTables
- [Database Engines](./engines.md) — How LSM engines compare to B-tree engines
- [WAL](./wal.md) — The durability layer that precedes the memtable
- [Key-Value Stores](../nosql/key-value.md) — LSM trees are the backbone of KV stores
- [Column-family Stores](../nosql/column-family.md) — Cassandra and HBase use LSM trees
- [B-Tree](../indexing/b-tree.md) — The alternative to LSM for read-heavy workloads

## Interview Questions

### Beginner

**Q: What is an LSM tree?**
A: An LSM tree is a write-optimized data structure that buffers writes in an in-memory sorted structure (memtable), then periodically flushes it to disk as an immutable sorted file (SSTable). Reads check the memtable first, then SSTables from newest to oldest.

**Q: Why are LSM trees faster for writes than B-trees?**
A: B-trees update data in-place, requiring random I/O to find and modify the correct page. LSM trees buffer writes in memory and flush them sequentially to disk, converting random I/O to sequential I/O, which is much faster especially on HDDs.

**Q: What is a memtable?**
A: A memtable is an in-memory sorted data structure (usually a skip list) that buffers incoming writes. When it reaches a size threshold, it's frozen and flushed to disk as an SSTable, and a new empty memtable is created.

### Intermediate

**Q: Explain the read path in an LSM tree. How can reads be slow?**
A: A read must check: (1) the memtable, (2) immutable memtable, (3) L0 SSTables (may have overlapping keys), (4) L1+ SSTables. In the worst case, this means checking many files. Optimizations include Bloom filters (skip SSTables that don't contain the key), block cache (cache hot blocks), and compaction (merge levels to reduce files).

**Q: What is a Bloom filter and how does it help LSM reads?**
A: A Bloom filter is a probabilistic set membership data structure with zero false negatives. Each SSTable has a Bloom filter. Before reading from an SSTable, the engine checks the Bloom filter — if it says "not present," the SSTable is skipped entirely. This eliminates most unnecessary I/O for point lookups.

**Q: How do deletions work in an LSM tree?**
A: Deletions insert a **tombstone marker** instead of actually removing data. The tombstone propagates through levels during compaction. When the tombstone reaches the bottom level and all older versions of the key have been compacted away, the tombstone itself can be removed.

### Advanced (FAANG-Level)

**Q: What are the three types of read amplification in LSM trees, and how do you minimize each?**
A:
1. **Read amplification from multiple levels**: A point lookup may check O(L) levels. Mitigated by Bloom filters (check each level with ~1 false positive rate).
2. **Read amplification within a level**: Binary search within an SSTable reads O(log B) blocks. Mitigated by block index cache and fence pointers.
3. **Read amplification from merging**: Range scans must merge-sort across all levels. Mitigated by compaction (fewer overlapping files per level).

Total read amplification ≈ O(L × log B) for point lookups with Bloom filters, where L = number of levels, B = block size.

**Q: Design a system to handle 1 million writes/second with LSM trees. What tunings would you make?**
A:
- **Large memtable** (256MB+) to reduce flush frequency
- **Multiple memtables** (pipeline memtable in RocksDB) for concurrent writes
- **Larger L0 size** before triggering compaction to absorb write bursts
- **Rate limiter** on compaction to prevent I/O stalls
- **Direct I/O** to bypass OS page cache (avoid double buffering)
- **Separate WAL disk** (NVMe) from data disk
- **Disable WAL** for non-durable workloads (e.g., cache)
- **Universal compaction** (better for write-heavy) instead of leveled

**Q: Explain the LSM-tree write amplification problem. How does leveled compaction reduce it compared to size-tiered?**
A: Write amplification = total bytes written to disk / bytes written by application. In **size-tiered compaction**, when L0 fills, all L0 SSTables are merged into L1 — but L1 may already have SSTables, causing cascading merges. Worst case: O(N) per level. In **leveled compaction**, each level has a size limit (L1 = 10× L0, L2 = 10× L1). When L1 overflows, only one SSTable is merged into L2, and only the overlapping SSTables in L2 are rewritten. This limits write amplification to ~O(level_size_ratio × num_levels) ≈ 10-30×, much better than size-tiered for large datasets.

## Common Mistakes

1. **Ignoring write amplification**: LSM trees can have 10-30x write amplification. On SSDs, this affects lifespan. Monitor with `rocksdb.stats` in RocksDB.

2. **Forgetting about tombstone accumulation**: In delete-heavy workloads, tombstones accumulate until compaction reaches the bottom level. Range tombstones are more efficient than individual tombstones.

3. **Assuming LSM reads are always slow**: With Bloom filters and block cache, point lookups in LSM trees are often as fast as B-trees. Range scans are where LSM trees pay the price.

4. **Not tuning compaction**: Default compaction settings are rarely optimal. Write-heavy workloads need different tuning (larger L0, universal compaction) than read-heavy (leveled compaction, smaller levels).

5. **Disabling WAL without understanding the risk**: Disabling WAL improves write throughput by ~2x but means uncommitted memtable data is lost on crash. Only safe for ephemeral data or when replication provides durability.

## Summary and Revision Notes

- **LSM tree** = WAL + Memtable + SSTables (sorted, immutable files on disk)
- **Write path**: WAL → Memtable → Flush to L0 SSTable → Compaction merges levels
- **Read path**: Memtable → L0 (newest) → L1 → L2 → ... (use Bloom filters to skip)
- **Memtable**: In-memory sorted structure (skip list); frozen and flushed when full
- **SSTable**: Immutable sorted file with data blocks, index, Bloom filter
- **Compaction**: Merges SSTables across levels; reclaims space, removes tombstones
- **Bloom filters**: Probabilistic "definitely not in this SSTable" → skip unnecessary reads
- **Tombstones**: Mark deletions; removed during compaction
- **Write amplification**: Key tradeoff — LSM trades write amplification for write throughput
- **RocksDB**: Most popular LSM engine; supports level-based, universal, and FIFO compaction
- **LevelDB**: Simpler predecessor by Google; single-threaded compaction


## Cross References

- [B-Tree](../dbms/indexing/b-tree.md)
- [Compaction](../dbms/internals/compaction.md)
- [WAL](../dbms/internals/wal.md)
- [SSD](../storage/ssd.md)
- [Write Policies](../arch/memory-hierarchy/write-policies.md)
