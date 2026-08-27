# Bw-Tree and ART: Index Structures for New Hardware

Two ICDE 2013 papers attacked the same weakness: the B+tree, designed in 1970 around slow
disks and uncontended memory, charges costs modern hardware stopped charging. Microsoft's
**Bw-tree** (Levandoski, Lomet, Sengupta) kept the B+tree shape but rebuilt its update and
concurrency model around a CAS-enabled indirection table; TUM's **ART** (Leis, Kemper,
Neumann) kept the trie shape but rebuilt its nodes so each level costs one cache line. This
page goes deep on both and runs a node-distribution experiment.

## The hardware tax a 1970 index pays

Three assumptions in the classic B+tree had become liabilities. Latch crabbing takes a latch at
every level, so the root bottlenecks on cache-line ping-pong, not key comparisons. In-place
mutation rewrites a 16 KB page to add one entry, the shape flash erase blocks handle worst. And
one fixed fanout ignores clustered distributions. The Bw-tree attacks the first two; ART the third.

## The Bw-tree: pages that are never mutated in place

### The mapping table and the delta chain

The Bw-tree's central object is a **mapping table**: a hash table mapping stable logical page
IDs (PIDs) to physical locations. Pages — *base pages* — are immutable images; every
modification prepends a **delta record** whose `next` pointer captures the previous head.
Installing a delta is a single compare-and-swap on the page's mapping entry, swinging it from
the old head to the new delta. Nobody latches anything; correctness rides on that one word.

```text
mapping table (entry per logical page, updated only by CAS)

  PID 7004 ------------>  [ delta: INSERT key=52 | next ] <-- new head (CAS lands here)
                                        |
                                        v
                          [ delta: SPLIT (SMO record) | next ]
                                        |
                                        v
                          [ BASE PAGE: sorted entries + free slots | next=NULL ]

  reader:  resolve PID -> walk deltas -> apply them over the base image
  writer:  build delta record -> CAS(mapping[PID], old_head, new_delta)
  retired: old heads and consolidated base pages freed later by epoch GC
```

A reader that resolved the PID just before a CAS still holds the old head — fine, because the
old chain stays readable until GC proves nobody can reach it. Reads need no latches at all.

### Logical SMOs: structural changes as delta records

Splits and merges are **structure modification operations (SMOs)**, encoded as delta records
rather than synchronous tree surgery:

- **Split**: the overflowing child installs a *split delta* describing the new right sibling
  and separator; a second delta links the sibling into the parent. A reader arriving through a
  stale parent follows the split delta's sibling pointer — the "inconsistent" intermediate
  state is readable instead of fenced off.
- **Merge**: an underflowing pair gets a *merge delta*; a merged-away level is deleted by a
  *root removal* SMO.
- **Consolidation** is deliberately not an SMO: any thread observing a long chain may build a
  fresh base page from base plus deltas and CAS it in, steering only new arrivals.

Each SMO is a few pointer-sized installs instead of a latch-held multi-page rewrite, so a
root-to-leaf modification never blocks a reader on an unrelated page — the property latch
crabbing can only approximate.

### Reclamation: epoch-based garbage collection

Retiring chain heads is the quiet half of the design. An **epoch manager** registers each
active thread in an epoch; a node installed in epoch N is freed only when every thread has left
the epochs in which it was reachable. Readers never block on reclamation, but slow readers
stretch the memory floor.

### Why this shape suits flash

The original paper paired the Bw-tree with a log-structured storage layer (LLAMA): installs
and consolidations append variable-length page images to a log instead of rewriting fixed pages
in place — the write shape flash wants. The same decoupling lets a page live partly in DRAM,
partly on device.

### The 2018 reality check

Wang, Pavlo, Lim, Leis, Zhang, Kaminsky, and Andersen re-engineered the design in "Building a
Bw-Tree Takes More Than Just Buzz Words" (SIGMOD 2018), measuring it against a plain B+tree
with *optimistic latch coupling* (version counters; readers validate instead of lock). The
punchline: the latch-free Bw-tree was **slower** — indirection, delta-chain traversal, and
GC/consolidation cost more than a well-tuned latch protocol. Lock-freedom is a technique, not a
performance guarantee.

## ART: a trie whose nodes fit cache lines

### Adaptive node sizes

For fixed-length byte keys, a trie lookup is one node visit per key byte — O(k), independent
of the key count n. The problem with textbook tries is node size: a 256-way array node costs
2048 pointer bytes whether it holds 2 children or 250. ART lets every node adapt to its actual
child count, across four types:

| Type | Layout (no header) | Children | Inline bytes |
|---|---|---|---|
| Node4 | 4x 1-byte key + 4x 8-byte pointer | up to 4 | 36 |
| Node16 | 16x 1-byte key + 16x 8-byte pointer | up to 16 | 144 |
| Node48 | 256x 1-byte child index + 48x 8-byte pointer | up to 48 | 640 |
| Node256 | 256x 8-byte direct pointers | up to 256 | 2048 |

Node4/16 search their few keys linearly; Node48 uses the 1-byte array as a lookup table from
key byte to child slot (why 49-255 children force the 16x bigger Node256); Node256 is the
classic direct-indexed array. Production implementations scan Node16 with a single SIMD
compare; the DaMoN 2016 follow-up measures these node-search strategies and the
synchronization schemes built on them.

### Path compression and lazy leaf expansion

Two more ideas make ART viable for long keys. **Path compression** collapses chains of
single-child nodes, storing the skipped byte prefix so a lookup skips whole levels in one
comparison — pessimistically as the full prefix, or hybrid-style as the prefix length plus a
bounded inline slice (10 bytes in their evaluation). **Lazy leaf expansion** creates an inner
node only when two keys actually diverge below it; a lone key hangs directly off the compressed
path. Together they make ART's memory track the key set's information content, not key length
times a fixed fanout.

### Concurrency and adoption

ART is the index of the TUM group's HyPer main-memory engine and its successor Umbra. "The
ART of Practical Synchronization" (DaMoN 2016) describes the production recipe: optimistic
latches — readers grab a version, traverse lock-free, retry on version change. That convergence
is instructive: both designs ended up betting on optimistic validation, but only ART kept
per-node cache-line economics.

## Choosing between them

| Dimension | B+tree | Bw-tree | ART |
|---|---|---|---|
| Native medium | disk pages | DRAM + log-structured flash | DRAM only |
| Write path | in-place page write, WAL, splits via latches | delta record + CAS on mapping table | in-place node writes; grow Node4->16->48->256 |
| Read path | O(log n) fat-node hops | walk delta chain over base image | O(k), one small node per key byte |
| Concurrency model | latch crabbing / B-link / optimistic coupling | lock-free CAS + epoch GC | optimistic latches with version retry |
| Range scan | native: linked leaves | native: leaf chain | native: sorted 1-byte parts per node |
| Space overhead | fixed fanout; ~69% fill under random keys | delta chains + mapping entries | per-node headers + prefixes; adapts to skew |
| Shipped in | nearly every RDBMS | SQL Server Hekaton (in-memory OLTP) | HyPer, Umbra |

Disk-resident systems keep B+trees, main-memory engines prefer ART, and the Bw-tree is the
cautionary tale whose ideas outlived the structure itself.

## Experiment: ART node types vs fixed-fanout B+tree occupancy

The simulation inserts 200k random 32-bit keys two ways: ART-style dict nodes grown exactly
per the 4/16/48/256 boundaries over the 4 key bytes, versus order-64 B+tree leaves with 50/50
splits. Fixed-length keys keep path compression out of the picture, isolating node-size
adaptation.
```python
import random
from bisect import bisect_left, insort

# ART-like adaptive trie over fixed-length 4-byte int keys.
# ART rule: a node holding n children is a Node4 (n<=4), Node16 (n<=16),
# Node48 (n<=48) or Node256 (n<=256); growing dicts per node preserves
# the exact type-boundary behaviour.

def classify(n):
    if n == 0: return "leaf"
    if n <= 4: return "Node4"
    if n <= 16: return "Node16"
    if n <= 48: return "Node48"
    return "Node256"

random.seed(42)
keys = random.sample(range(2**32), 200_000)

root = {}
for k in keys:
    node = root
    for byte in k.to_bytes(4, "big"):
        node = node.setdefault(byte, {})

counts, depth_sum, depth_max = {}, 0, 0

def walk(node, d):
    global depth_sum, depth_max
    t = classify(len(node))
    counts[t] = counts.get(t, 0) + 1
    if not node:                      # leaf slot: all 4 key bytes consumed
        depth_sum += d
        depth_max = max(depth_max, d)
    else:
        for c in node.values():
            walk(c, d + 1)

walk(root, 0)
avg_depth = depth_sum / len(keys)

# Fixed-fanout B+tree: order-64 leaves, 50/50 split on overflow.
ORDER = 64
boundaries = []                      # highest key of each bounded leaf
leaves = [[]]
for k in keys:
    i = bisect_left(boundaries, k)
    insort(leaves[i], k)
    if len(leaves[i]) > ORDER:
        mid = ORDER // 2 + 1
        right = leaves[i][mid:]
        leaves[i] = leaves[i][:mid]
        if i < len(boundaries):      # left half keeps a boundary; add right's
            boundaries[i] = leaves[i][-1]
            boundaries.insert(i + 1, right[-1])
        else:                        # right half is the new catch-all leaf
            boundaries.append(leaves[i][-1])
        leaves.insert(i + 1, right)

fills = [len(l) for l in leaves]
avg_fill = sum(fills) / len(fills) / ORDER
btree_levels, cap = 1, ORDER
while cap < len(keys):
    cap *= ORDER
    btree_levels += 1

print(f"keys inserted              : {len(keys):,} (random 32-bit ints)")
print(f"ART inner-node type counts : {counts}")
print(f"ART leaf depth             : avg {avg_depth:.2f} bytes, max {depth_max}")
print(f"B+tree (order {ORDER}) leaf count : {len(fills):,}")
print(f"B+tree avg leaf occupancy  : {avg_fill*100:.1f}% (theory ~69.3% for random keys)")
print(f"B+tree levels              : {btree_levels} node visits per lookup")
```

Output (executed, Python 3.12):

```text
keys inserted              : 200,000 (random 32-bit ints)
ART inner-node type counts : {'Node256': 257, 'Node4': 248809, 'leaf': 200000, 'Node16': 12428}
ART leaf depth             : avg 4.00 bytes, max 4
B+tree (order 64) leaf count : 4,474
B+tree avg leaf occupancy  : 69.8% (theory ~69.3% for random keys)
B+tree levels              : 3 node visits per lookup
```

Three readings. First, the trie is bottom-heavy: root plus the 256 second-level nodes
saturate into Node256 (257 of them), while nearly all depth-3 nodes hold 1-4 children —
248,809 Node4s, zero Node48s. A fixed 256-way trie would spend 2048 bytes per node there; ART
spends 36. Second, leaf depth is pinned at 4 because the keys are fixed-length; with strings,
path compression pushes the average down. Third, the B+tree's 69.8% occupancy lands on Knuth's
ln(2) = 69.3% random-insert equilibrium — the B+tree tunes *how full* its nodes are, ART tunes
*how big* they are. (Caveat: node types only, not bytes.)

## What interviewers probe on this pair

- **"How does the Bw-tree avoid latches?"** Build delta, CAS the mapping entry; old-head
  readers stay correct; epoch GC decides when the old chain dies.
- **"Did latch-freedom win?"** No — the 2018 re-engineering showed optimistic latch coupling
  beating the lock-free Bw-tree on its own benchmarks.

## Cross-References

- [Advanced Index Structures](./index-advanced.md) — survey of Bw-tree, ART, LSM, learned indexes
- [B-Trees](../indexing/btrees.md) — disk-era B+tree mechanics this page builds on
- [Learned Indexes](./learned-indexes.md) — the third answer to the same hardware shift

## References

- Levandoski, Lomet, Sengupta. "The Bw-Tree: A B-tree for New Hardware Platforms." ICDE 2013. https://doi.org/10.1109/ICDE.2013.6544834
- Wang et al. "Building a Bw-Tree Takes More Than Just Buzz Words." SIGMOD 2018. https://doi.org/10.1145/3183713.3196895
- Leis, Kemper, Neumann. "The Adaptive Radix Tree: ARTful Indexing for Main-Memory Databases." ICDE 2013. https://doi.org/10.1109/ICDE.2013.6544812
- Leis, Scheibner, Kemper, Neumann. "The ART of Practical Synchronization." DaMoN 2016. https://doi.org/10.1145/2933349.2933352
- Microsoft Learn. "Indexes for memory-optimized tables" (Hekaton's Bw-tree indexes). https://learn.microsoft.com/en-us/sql/relational-databases/in-memory-oltp/indexes-for-memory-optimized-tables
