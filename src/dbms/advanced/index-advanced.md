# Advanced Index Structures

Beyond the classic B+ tree and hash index, modern databases employ a range of advanced index structures optimized for specific workloads — from latch-free B-trees to ML-learned indexes and adaptive radix trees. This chapter covers the next generation of index structures.

## Learned Indexes

### The Core Idea

The key insight of learned indexes (Kraska et al., SIGMOD 2018): **an index is a model**. A B+ tree maps a key to a position using a tree of comparisons. A learned index trains a machine learning model (typically a simple neural network or piecewise linear function) to predict the position of a key directly.

```
B+ Tree:                Learned Index:
key → [compare, branch]  key → model.predict(key) → position
       × height levels         × 1 function evaluation
```

### FITing-Tree (Fully Indexing Tree)

The FITing-Tree (Galakatos et al., SIGMOD 2019) is a practical learned index that divides the key space into segments, each with a linear model (slope + intercept):

```python
class FITingTree:
    def __init__(self, data, max_error=8):
        self.models = []  # list of (slope, intercept, start_pos, end_pos)
        self.build(data, max_error)
    
    def build(self, data, max_error):
        # Greedily extend a linear model until max_error is exceeded
        i = 0
        while i < len(data):
            # Fit linear regression on data[i:j]
            j = extend_until_error_exceeds(data, i, max_error)
            slope, intercept = linear_fit(data[i:j])
            self.models.append((slope, intercept, i, j))
            i = j
    
    def lookup(self, key):
        # Binary search over model segments, then predict position
        seg = binary_search_segments(self.models, key)
        pos = seg.slope * key + seg.intercept
        # Search in [pos - error, pos + error] in the data array
        return exponential_search(data, pos, key)
```

**Performance**: For sorted data with uniform or linear distributions, FITing-Trees achieve **1.5-3x fewer cache misses** than B+ trees and are more compact. For highly skewed or multi-modal data, the advantage shrinks.

### ALEX (Adaptive Learned Index)

ALEX (Ding et al., SIGMOD 2020) addresses the key limitations of earlier learned indexes: it supports **insertions** efficiently and adapts to workload changes.

- **Gapped array** at each node: leaves have extra space between elements (like a B+ tree page with fill factor), allowing in-place inserts without immediate restructuring.
- **Model-based internal nodes**: Each internal node uses a linear model to route keys to the correct child.
- **Self-tuning**: When a node becomes too full, it splits (like B+ tree). When models become inaccurate, they are retrained.
- **Comparison with B+ tree**: ALEX matches or beats B+ tree on point lookups and range queries, and significantly outperforms on insert-heavy workloads where the adaptive model reduces tree height.

### Challenges with Learned Indexes

1. **Distribution shifts**: If the key distribution changes (e.g., time-series data with new patterns), models become stale. ALEX addresses this with periodic retraining.
2. **Concurrency**: Read-only learned indexes are straightforward; supporting concurrent inserts with learned models is an open research area (ALEX supports single-threaded inserts).
3. **Variable-length keys**: Most learned indexes assume fixed-size numeric keys. Handling strings requires dimensionality reduction or separate string handling.
4. **Build time**: Training the model can be slower than bulk-loading a B+ tree.

> **Interview Angle**: "What is a learned index and when would you use one?" — Explain the key-to-position model analogy, FITing-Tree segments, ALEX for writes, and practical limitations (concurrency, distribution shift).

## Bw-Tree (Latch-Free B-Tree)

The Bw-Tree (Levandoski, Lomet, Sengupta, VLDB 2013; used in **Azure SQL Database** and **SQL Server**) is a **latch-free** B+ tree that uses **compare-and-swap (CAS)** instead of latches (read/write locks) for concurrency control.

### Architecture

```
Bw-Tree Node (in memory):
┌──────────────────────────┐
│ PID (page identifier)    │  ← immutable logical page ID
│ ┌──────────────────────┐ │
│ │ Delta Record Chain   │ │  ← app-only, no in-place updates
│ │  (delta → delta → ..)│ │
│ └──────────────────────┘ │
│ Base Node (full page)    │  ← immutable snapshot
└──────────────────────────┘

Mapping Table (thread-safe hash table):
  PID → physical pointer (to base or latest delta)
```

**Key principles:**
- **No in-place updates**: All modifications are prepended as **delta records** linked off the base node. A delta might be an insert, delete, or split/update operation.
- **CAS on mapping table**: To install a delta, a thread CAS-updates the mapping table entry from `old_ptr → new_delta_ptr`. No latches needed — concurrent readers follow the pointer chain.
- **Consolidation**: Periodically, a background thread **consolidates** the delta chain into a new base node, then CAS-updates the mapping table to point to the consolidated base.
- **SMR (Structure Modification Records)**: Splits and merges are encoded as deltas that are installed via CAS, making structural changes lock-free.

### Delta Record Types

| Delta Type | Purpose |
|-----------|---------|
| Insert record | Add a new key-value pair |
| Delete record | Mark a key as deleted |
| Update record | Modify a value in-place |
| Split SMR | Record a node split (new child PIDs) |
| Remove SMR | Record a node removal (merge) |
| Abort record | Mark a failed split attempt |

### Performance Characteristics

- **Read path**: Follow mapping table → follow delta chain → check base node. Short chains (1-3 deltas) give near B+ tree read performance. Long chains degrade, so consolidation frequency matters.
- **Write path**: CAS to install delta (typically 1-2 atomic operations). Extremely fast for low-contention workloads.
- **Memory**: Delta chains consume more memory than in-place updates. The mapping table is a hash table mapping PID → pointer, adding ~16 bytes per page.

> **Interview Angle**: "How does the Bw-Tree avoid latches?" — Explain delta records, the mapping table, CAS-based updates, consolidation, and SMRs. Mention it's used in Azure SQL Database.

## Adaptive Radix Tree (ART)

The Adaptive Radix Tree (Leis, Kemper, Neumann, ICDE 2013) is a **cache-optimized trie** that adapts its node size to the number of children. It combines the **O(k) worst-case lookup** of tries with the **cache efficiency** of B+ trees.

### Node Types

ART nodes adapt to the current fan-out, choosing the smallest representation:

| Node Type | Children | Size | When Used |
|-----------|-----------|------|-----------|
| **Node4** | ≤ 4 | 56 bytes | Sparse nodes |
| **Node16** | ≤ 16 | 128 bytes | Moderate fan-out |
| **Node48** | ≤ 48 | 256 bytes | Dense-ish (indirection array) |
| **Node256** | ≤ 256 | 1088 bytes | Full fan-out (direct array) |

```
Node4:   [key0, ptr0, key1, ptr1, key2, ptr2, ...]  (linear search, 4 entries)
Node16:  [keys[16], children[16]]  (SIMD comparison via _mm_cmpeq_epi8)
Node48:  [index[256], children[48]]  (O(1) indirection, index maps byte→slot)
Node256: [children[256]]  (O(1) direct lookup by byte value)
```

### Lookup

```
lookup(node, key, depth):
    if node is leaf:
        return node.value if node.key == key else NOT_FOUND
    byte = key[depth]  # next byte of the key
    child = node.find_child(byte)  # depends on node type
    if child is NULL: return NOT_FOUND
    return lookup(child, key, depth + 1)
```

**Key insight**: Node4 uses linear search (4 comparisons — faster than binary search for n≤4). Node16 uses **SIMD parallel comparison** (`_mm_cmpeq_epi8` + `_mm_movemask_epi8`) to find the matching child in a single instruction. Node48 and Node256 use O(1) array indexing.

### Performance

ART matches or outperforms B+ trees on point lookups and range queries for **in-memory workloads**:
- Point lookups: ~100-200ns (vs. B+ tree ~200-500ns due to fewer cache misses)
- Memory overhead: 20-30% more than a compact B+ tree for random keys, but less for skewed distributions
- Used in: **HyPer/Umbra**, **Hyper**, and several in-memory key-value stores

### Tries in Databases

Beyond ART, tries appear in several database contexts:
- **Prefix tries for string indexing**: ART is the leading approach for in-memory string workloads
- **Suffix trees/arrays for substring search**: Used in full-text search indexes
- **Merkle tries (Merkle Patricia Trie)**: Used in **FoundationDB**'s key-value layer and **Ethereum's** state trie — content-addressed, enabling efficient comparison of database snapshots

## LSM-Based Indexes

Traditional B+ tree indexes are built on top of LSM-tree storage (see [../internals/lsm-trees.md](../internals/lsm-trees.md)). However, several specialized index structures are designed specifically for the LSM paradigm:

### Partitioned Indexes in LSM Trees

In a standard LSM tree, the primary index is the sorted run (SSTable). Secondary indexes face a challenge: when a primary key is updated, all secondary indexes must also be updated. Approaches:

| Approach | Mechanism | Tradeoff |
|----------|-----------|----------|
| **In-SSTable index** | Secondary index stored within each SSTable | Consistent, but point lookups require checking all levels |
| **Materialized view** | Separate LSM tree for each secondary index | Write amplification: 1 primary + k secondary LSM trees |
| **Index in memtable only** | Secondary index maintained in memtable, materialized during compaction | Fast writes, but reads scan memtable + all SSTables |
| **LoKI (Lazy Key-Index)** | Store (key → position) index, lazily resolved | Low write amp, read amplification depends on hit rate |

### Bloom Filters as Indexes

Bloom filters are technically **negative indexes** — they can definitively say "this key does NOT exist" (no false negatives), but may have false positives. In LSM trees, each SSTable has a Bloom filter that avoids unnecessary disk reads:

```
Lookup key K:
  for each level in [memtable, L0, L1, ... Ln]:
    for each SSTable in level:
      if sstable.bloom_filter.might_contain(K):  # O(k) hash lookups
        actual_search(sstable, K)                   # I/O only if might exist
```

### Packed Indexes and Fractional Cascading

For point lookups across sorted runs, **fractional cascading** (Chazelle & Guibas, 1986) can reduce the cost of searching through multiple sorted levels: each level stores pointers to the corresponding positions in the next level, allowing binary search to "cascade" through levels with O(log n) total comparisons instead of O(k log n) for k levels. Research systems like **RocksDB's** prefix bloom filters apply a similar idea.

## Comparison Table

| Index | Lookup | Insert | Range Query | Memory | Concurrency | Used In |
|-------|--------|--------|-------------|--------|-------------|----------|
| B+ Tree | O(log n) | O(log n) | O(log n + k) | Low | Latches | PostgreSQL, MySQL |
| Learned (FITing) | O(1) pred + search | O(n) rebuild | Good | Very Low | Research |
| ALEX | O(log n) | O(log n) amortized | Good | Low | Single-threaded | Research |
| Bw-Tree | O(log n) | O(1) amortized (delta) | O(log n + k) | Medium | Lock-free (CAS) | SQL Server, Azure SQL |
| ART | O(k) key bytes | O(k) | O(k + result) | Medium | Latches | Umbra, Redis on Flash |
| LSM+Bloom | O(log n) avg | O(1) memtable | O(log n + k) | Low | Latches | RocksDB, Cassandra |

## References

- Kraska, T. et al. "The Case for Learned Index Structures." SIGMOD, 2018.
- Galakatos, A. et al. "The Design and Implementation of the FITing-Tree." SIGMOD, 2019.
- Ding, J. et al. "ALEX: An Upsdatable Adaptive Learned Index." SIGMOD, 2020.
- Levandoski, J. et al. "The Bw-Tree: A B-tree for New Hardware Platforms." VLDB, 2013.
- Leis, V. et al. "The Adaptive Radix Tree: ARTful Indexing for Main-Memory Databases." ICDE, 2013.