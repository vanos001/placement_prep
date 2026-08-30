# The Adaptive Radix Tree (ART)

When the index lives in RAM, every tree level costs a cache miss instead of a disk seek, and the B+tree's page-shaped nodes stop being an asset. The Adaptive Radix Tree (Leis, Kemper, Neumann, ICDE 2013) answers with three ideas: node types that grow with occupancy (Node4/Node16/Node48/Node256), lazy expansion, and path compression. The result is a trie whose height depends on the key length in bytes — at most 8 inner levels for fixed 8-byte keys — rather than on row count, and whose space tracks the key set's information content. ART became the index of the TUM HyPer engine and ships in systems such as DuckDB.

This page dissects those internals. The companion [Bw-Tree and ART survey](bwtree-art.md) weighs ART against the Bw-tree for flash-era hardware and runs an occupancy simulation against B+trees, and [index-advanced.md](index-advanced.md) places both in the wider index-family landscape; here we go one level deeper into node layouts, the Node48 indirection, compression mechanics, and the height bound.

---

## Cache misses replaced disk seeks, and B+trees kept the wrong instincts

A disk-era B+tree maximizes fanout so that a 3-4 level tree covers billions of rows: one node per page, one page read per level. In main memory the same design misfires, because touching one node means one cache miss (~100 ns from DRAM) while a cache line is only 64 bytes. A fat node spans dozens of lines, so a "single" level visit degenerates into several misses, and binary search inside a fat node chases pointers across lines. Rao and Ross's cache-conscious B+trees (SIGMOD 2000) attack exactly this by shrinking nodes to fit a line and trading fanout back for height.

Tries side-step the fanout-vs-height trade-off. A radix tree consumes `s` key bits per level (the **span**), so its height is `ceil(k/s)` for `k`-bit keys — independent of how many keys are stored. The ART paper quantifies the contrast for 32-bit keys: a binary span (`s = 1`) yields 32 levels, while a span of 8 yields 4; and a radix tree is shallower than a balanced binary search tree once `n > 2^(k/s)`. Height no longer depends on `n`, which is why tries appeal when the key is short and fixed — the primary-key case in OLTP engines.

The catch is span economics. Span 8 means one of 256 possible children per node, and the naive layout — a 256-entry pointer array per node — spends 2 KB whether the node holds 3 children or 250. With millions of inner nodes, that is bandwidth, TLB pressure, and cache waste; shrink the span to save space and the tree deepens again. ART keeps span 8 and instead makes each node only as large as its occupancy requires.

## Four node types, one growth rule

Every ART inner node stores its children indexed by key byte, in one of four layouts chosen by current count:

```text
       5th child                  17th child                    49th child
Node4 ────────────▶ Node16 ────────────▶ Node48 ─────────────▶ Node256
+---------------+  +---------------+  +------------------+  +------------------+
| keys  sorted  |  | keys  sorted  |  | childIdx [256]   |  | children [256]   |
| kids parallel |  | kids parallel |  |  byte -> slot #  |  |  one 8-byte slot |
| linear scan   |  | binary search |  | slots  [<=48 ptr]|  |  per key byte    |
| (<=4 entries) |  | / SIMD compare|  | two array reads  |  | single array read|
+---------------+  +---------------+  +------------------+  +------------------+
  ~40 B of payload    ~144 B of payload    256 B + 48x8 B       256 x 8 B = 2 KB
                                           = ~640 B
```

The growth rule is purely local. Inserting a child into a full node converts that node in place — Node4 to Node16, Node16 to Node48, Node48 to Node256 — and nothing else in the tree is touched: no rotations, no splits cascading to the root, no global reorganization. Because children are kept in byte order at every level, a left-to-right leaf walk yields byte-sorted keys, so range scans, prefix lookups, MIN, and MAX are natural (given keys whose byte order matches their logical order — more on that below). Node16 earns its keep through vectorized search: the paper notes its 16 sorted key bytes can be probed "with parallel comparisons using SIMD instructions," which turns the membership check into a handful of instructions.

## Node48: one byte of indirection per key byte

Node48 is the design's most quoted trick. Between 17 and 48 children, keeping key bytes sorted is no longer cheap to maintain — every insert shifts up to 47 entries — yet a full 256-pointer array would waste 1.5-2 KB on a node that is barely a fifth full. The paper's answer: stop storing keys explicitly, and use a 256-element array that is indexed by the key byte directly; each occupied entry holds the slot number of the child pointer in a second array of up to 48 pointers. Lookup is two array reads; the unused slots carry an empty marker (the reference implementation uses an `EMPTY` sentinel in the index array).

The byte arithmetic explains why the middle ground wins. Node48 costs 256 index bytes plus at most 48 × 8-byte pointers ≈ 640 bytes; Node256 costs 2 KB; a hypothetical sorted Node48 with explicit keys would pay both the search cost and the shift cost. The indirection spends exactly one byte per possible key byte — the minimum needed to answer "which slot, if any, owns this byte?" in constant time. Our demo below prints the root node grown to `Node48 (20 children via 256-byte index)`, and the histogram shows Node256 appearing only where a node genuinely crosses 49 children.

## Path compression and lazy expansion

Adaptive fanout alone does not fix long keys: a trie that spends one inner node per byte still allocates a chain for every byte of every key. ART adds two complementary techniques. **Lazy expansion** creates inner nodes only when at least two leaf nodes must be distinguished — a unique key needs no inner node at all, and a key that is a prefix of another (like `cafe` and `cafeteria`) simply parks its value on a node that also has children. **Path compression** removes all one-way nodes (no value, single child), so chains of single-child nodes collapse.

What happens to the removed bytes? The paper gives two variants. The **pessimistic** form stores at each inner node a partial-key vector containing the keys of the removed one-way nodes; lookups compare it against the search key before descending. The **optimistic** form stores only the count of skipped bytes, lets lookups skip them blindly, and compensates by comparing the full key when a leaf is finally reached — catching any "wrong turn." Both guarantee every inner node has at least two children. ART ships a hybrid: a constant 8-byte vector per node, switching to the optimistic strategy when a path exceeds it, which bounds node size while avoiding the leaf check in the common case.

```text
keys: https://db.example.org/art/paper, /art/code, /index   (23-byte shared prefix)

BEFORE: one node per byte                    AFTER: pessimistic path compression
root                                         root
 |-h                                          |-h
 | |-t                                        | '-[pkey="ttps://db.example.org/"]
 |   |-t  ... 32 one-way Node4 nodes          |   |-a
 |   |-s  in a chain, depth = 33              |   | '-[pkey="rt/"]
 |   |-:                                      |   |   |-p-- [pkey="aper"] leaf
 |   ...                                      |   |   '-c-- [pkey="ode"]  leaf
 |   |-g                                      |   '-i---- [pkey="ndex"] leaf
 |   |-/                                      (URL branch: 5 node levels, 32 bytes)
 |   |-(a|i)  first real branch
```

Without compression, inner-node count is proportional to key length and worst-case space per key is unbounded — the paper's Table II makes precisely this argument against the Generalized Prefix Tree and the Linux kernel radix tree, which lack path compression. (Linux later moved the page cache to the maple tree; see [kernel data structures](../../linux/kernel/data-structures.md).) With compression, stored bytes track the key set's branching structure: our demo collapses 409 inner nodes to 7 on a fixed 92-key set, leaving the 91 leaf-carrying nodes untouched.

## Height bound and binary-comparable keys

For fixed-length 8-byte keys the arithmetic is stark: 64 bits / 8 bits per level = at most 8 inner-node levels, plus one leaf dereference. Every level visit touches one small node — Node4 is ~40 bytes of payload, Node48 ~640 — so worst-case lookup cost is a handful of cache misses regardless of whether the table holds a thousand rows or a billion. The same bound is what makes ART a good fit for compiled query plans, where the index probe is inlined into machine code and every miss is on the critical path.

Range scans over non-string types need byte order to match logical order. The ART paper dedicates a section to **binary-comparable key transformations**: unsigned integers serialize big-endian, signed integers flip the sign bit, IEEE floats flip sign and exponent bits, and so on, so that byte-lexicographic order equals numeric order. HyPer applies this "for all built-in types so that range scan, prefix lookup, minimum, and maximum operations work as expected." The transformation is a one-time cost per probe and is the standard toll for any byte-oriented index, ART included.

## Demo: adaptive growth and path compression on a fixed key set

The script builds the same byte-trie twice — once with one node per byte, once after collapsing one-way chains into `pkey` vectors (pessimistic compression, verified on lookup). Node48 is emulated faithfully: a 256-entry byte-to-slot table with `EMPTY = 0xFF` markers over a growable pointer array. Depth counts inner-node levels (root = 1), so an uncompressed 32-byte key sits 33 levels deep.

```python
# Compact ART: adaptive node growth (4/16/48/256), pessimistic path
# compression, lazy expansion. Fixed key set, deterministic, stdlib only.
import bisect

EMPTY = 0xFF  # Node48 child-index marker: "no child at this byte"

class Node:
    __slots__ = ("pkey", "val", "keys", "kids", "index")
    def __init__(self):
        self.pkey, self.val, self.keys, self.kids, self.index = b"", None, [], [], None

def kind(n):
    if not n.kids: return "leaf"
    if n.index is not None: return "Node48"
    return "Node256" if len(n.kids) == 256 else ("Node4" if len(n.kids) <= 4 else "Node16")

def items(n):
    if n.index is not None:
        return [(b, n.kids[s]) for b in range(256) if (s := n.index[b]) != EMPTY]
    if len(n.kids) == 256:
        return [(b, c) for b, c in enumerate(n.kids) if c is not None]
    return list(zip(n.keys, n.kids))

def find_child(n, b):
    if n.index is not None:                        # Node48: two array lookups
        s = n.index[b]
        return None if s == EMPTY else n.kids[s]
    if len(n.kids) == 256: return n.kids[b]        # Node256: one direct access
    i = bisect.bisect_left(n.keys, b)              # Node4/Node16: binary search
    return n.kids[i] if i < len(n.keys) and n.keys[i] == b else None

def add_child(n, b, c, growth):
    if n.index is not None and len(n.kids) == 48:  # Node48 full -> spill to Node256
        growth["48->256"] += 1
        kids = [None] * 256
        for j in range(256):
            if (s := n.index[j]) != EMPTY: kids[j] = n.kids[s]
        n.keys, n.index, n.kids = [], None, kids
    if n.index is not None:                        # Node48: claim a pointer slot
        n.kids.append(c); n.index[b] = len(n.kids) - 1
    elif len(n.kids) == 256:
        n.kids[b] = c
    else:                                          # Node4/Node16: keep sorted
        i = bisect.bisect_left(n.keys, b)
        n.keys.insert(i, b); n.kids.insert(i, c)
        if len(n.kids) == 17:                      # -> Node48: byte index over slots
            growth["16->48"] += 1
            n.index = [EMPTY] * 256
            for j, k in enumerate(n.keys): n.index[k] = j
        elif len(n.kids) == 5:
            growth["4->16"] += 1

def insert(root, key, growth):
    n = root
    for b in key:
        c = find_child(n, b)
        if c is None:
            c = Node(); add_child(n, b, c, growth)
        n = c
    n.val = "v"                                    # lazy expansion: no leaf chain

def set_child(n, b, c):
    if n.index is not None: n.kids[n.index[b]] = c
    elif len(n.kids) == 256: n.kids[b] = c
    else: n.kids[n.keys.index(b)] = c

def compress(n):                                   # collapse one-way chains
    for b in [bb for bb, _ in items(n)]:
        c = find_child(n, b); skipped = b""
        while c.val is None and len(c.kids) == 1:  # one-way: no value, single child
            skipped += bytes([c.keys[0]]); c = c.kids[0]
        compress(c)
        c.pkey = skipped
        set_child(n, b, c)

def stats(root):
    hist = {"Node4": 0, "Node16": 0, "Node48": 0, "Node256": 0, "leaf": 0}
    def rec(n, d):
        hist[kind(n)] += 1
        return max([rec(c, d + 1) for _, c in items(n)] or [d])
    return hist, rec(root, 1)

def lookup(root, key):                             # works for both variants
    n, i = root, 0
    while True:
        if key[i:i + len(n.pkey)] != n.pkey: return False  # verify skipped bytes
        i += len(n.pkey)
        if i == len(key): return n.val is not None
        n = find_child(n, key[i])
        if n is None: return False
        i += 1

keys  = [bytes([97 + i]) + b"-alpha" for i in range(20)]       # 20 root branches
keys += [b"blob:%c/doc" % (65 + i) for i in range(60)]         # forces a Node256
keys += [b"mid:%c" % c for c in b"abcdefg"]                    # forces a Node16
keys += [b"cafe", b"cafeteria"]                                # prefix pair (lazy)
keys += [b"https://db.example.org/art/paper",
         b"https://db.example.org/art/code",
         b"https://db.example.org/index"]                      # 23-byte shared prefix

root, growth = Node(), {"4->16": 0, "16->48": 0, "48->256": 0}
for k in keys: insert(root, k, growth)
h1, d1 = stats(root)
compress(root)
h2, d2 = stats(root)
row = lambda h: " ".join(f"{k}={h[k]}" for k in h)
print(f"inserted {len(keys)} fixed keys, {len(set(keys))} unique")
print("uncompressed trie :", row(h1), f"max-depth={d1}")
print("path compressed   :", row(h2), f"max-depth={d2}")
print("inner nodes removed:", sum(h1[k] for k in ('Node4', 'Node16', 'Node48', 'Node256'))
      - sum(h2[k] for k in ('Node4', 'Node16', 'Node48', 'Node256')))
print("growth events     :", growth)
print(f"root after inserts: {kind(root)} ({len(items(root))} children via 256-byte index)")
print(f"lookups: {sum(lookup(root, k) for k in keys)}/{len(keys)} found; "
      f"'cafe' + 'cafeteria' both found: {lookup(root, b'cafe') and lookup(root, b'cafeteria')}; "
      f"absent key rejected: {not lookup(root, b'caf\\xc3\\xa9')}")
```

Real output (executed, Python 3.12):

```text
inserted 92 fixed keys, 92 unique
uncompressed trie : Node4=409 Node16=1 Node48=1 Node256=1 leaf=91 max-depth=33
path compressed   : Node4=7 Node16=1 Node48=1 Node256=1 leaf=91 max-depth=5
inner nodes removed: 402
growth events     : {'4->16': 3, '16->48': 2, '48->256': 1}
root after inserts: Node48 (20 children via 256-byte index)
lookups: 92/92 found; 'cafe' + 'cafeteria' both found: True; absent key rejected: True
```

Read the histogram as three results in one. The four node types all appear, and the growth counters show the ladder firing exactly where occupancy crossed 5, 17, and 49 children. Compression removes 402 of 412 inner nodes while the leaf count (91 — every key except `cafe`, which is a proper prefix of `cafeteria`) stays fixed, confirming that compression only removes value-less one-way nodes. Max depth drops 33 to 5, and all 92 lookups plus the prefix pair succeed against the compressed tree.

## ART versus B+tree and hash indexes

| Dimension | B+tree | ART | Hash index |
| ---------- | ---------- | ---------- | ---------- |
| Height driver | row count `n` (fanout fixed) | key bytes: <= 8 levels for 8-byte keys | none (1-2 probes typical) |
| Point lookup | log(n)/log(F) node hops; fat nodes cost extra misses | <= 8 small-node hops + leaf verify | single probe + chain |
| Range scan / MIN / MAX | native, ordered leaves | native, byte-ordered leaves | absent — needs a second ordered structure |
| Prefix lookup | awkward (full-key compares) | native — trie is a prefix machine | absent |
| Insert/delete work | splits/merges can cascade to root | local node growth; no rebalance | occasional rehash |
| Memory per key | fill-factor bounds, fat nodes | adaptive node sizes; compression trims chains | lowest for pure point workloads |
| Concurrency story | mature latch crabbing | Optimistic Lock Coupling / ROWEX (DaMoN 2016) | mature, simpler structures |

The table's honest summary: ART wins when keys are short-to-medium, shared prefixes are common, and ordered operations matter; hash indexes win pure point-lookup workloads with no ordering needs; B+trees remain the safe default for disk-resident data and huge variable-length keys. Learned indexes are a fourth bet entirely — see [alex-learned-indexes.md](alex-learned-indexes.md) for the data-adaptive alternative.

## Production trail

HyPer is the origin story: the ART paper reports integrating ART into HyPer for TPC-C end-to-end, noting the engine "originally" shipped "a red-black tree and a hash table" before ART arrived with both compression optimizations. The follow-up DaMoN 2016 paper documents the production shape: ART is HyPer's default index, tuple IDs ride inside child pointers via pointer-tagging, and synchronization uses Optimistic Lock Coupling or ROWEX rather than lock-free machinery. DuckDB's documentation likewise describes ART as its index type, created by `CREATE INDEX` and persisted with the database (see the [DuckDB indexes doc](https://duckdb.org/docs/current/sql/indexes.html)).

The design space around ART is active. HOT (Binna et al., SIGMOD 2018) re-partitions children to cut trie height for skewed key distributions; the HyPer lineage's out-of-core successor explores how latching and buffer management change once indexes spill from RAM. The durable lesson is architectural: ART wins not by one trick but by stacking span-8 tries, occupancy-matched nodes, and compression so each fixes what the previous one costs.

## Interview questions

**Q: Why does ART need Node48 at all — why not jump from Node16 straight to Node256?**
Between 17 and 48 children, a sorted key array becomes expensive to maintain (every insert shifts entries), while a 256-pointer array wastes ~2 KB on a node that is under 20 percent full. Node48 spends 256 index bytes (one per possible key byte) plus at most 48 eight-byte pointers — about 640 bytes — and still answers "which child owns this byte?" in two array reads. It is the minimal constant-time layout for that occupancy band, and the demo's growth counter shows it firing only where occupancy actually crossed 17.

**Q: Explain optimistic versus pessimistic path compression. What breaks if lookups skip bytes without checking?**
Pessimistic compression stores the skipped bytes as a partial-key vector and compares them during descent, so a mismatch aborts early. Optimistic compression stores only the count, skips blindly, and verifies the full key at the leaf — a lookup that took a "wrong turn" inside skipped bytes is caught only there, after wasted work. Correctness survives because one-way nodes never carry values, so no key can legitimately end inside a skipped region; the leaf check is what converts silent misdirection into a clean miss. ART's hybrid keeps an 8-byte vector and falls back to the optimistic form for longer runs, bounding node size.

**Q: Your table holds 100 million rows keyed by fixed 8-byte integers. Bound ART's worst-case lookup in cache misses and compare it to a B+tree.**
ART descends at most 8 inner nodes (64 key bits / 8 bits per level) plus one leaf: nine node touches, each a small node fitting one or two cache lines, so roughly 9-12 misses independent of `n`. A B+tree tuned for cache lines (64-byte nodes) has fanout near 4, so height is around log4(10^8) ≈ 13-14 misses; a page-sized B+tree is only 3-4 levels but each level smears over dozens of cache lines, costing comparable or worse in misses. That arithmetic — height from key length, not row count — is the core of the paper's argument.

**Q: Name two situations where you would not pick ART.**
First, workloads of long, mostly unshared keys (random UUIDs, long URLs with unique tails): path compression cannot help what never branches, leaf storage keeps whole keys, and space grows with total key bytes — a hash index or a B+tree with prefix truncation is friendlier. Second, pure point-lookup caches with no range or prefix needs: a well-tuned hash table probes fewer lines than even 8 trie levels, so ART's ordered operations buy nothing there. A close third: keys whose byte order contradicts logical order (negative integers, floats) require the binary-comparable transformation, which is easy to get subtly wrong.

## References

1. V. Leis, A. Kemper, T. Neumann. "The Adaptive Radix Tree: ARTful Indexing for Main-Memory Databases." ICDE 2013. [doi:10.1109/ICDE.2013.6544812](https://doi.org/10.1109/ICDE.2013.6544812) — open PDF: <https://db.in.tum.de/~leis/papers/ART.pdf>
2. V. Leis, F. Scheibner, A. Kemper, T. Neumann. "The ART of Practical Synchronization." DaMoN 2016. [doi:10.1145/2933349.2933352](https://doi.org/10.1145/2933349.2933352)
3. A. Kemper, T. Neumann. "HyPer: A hybrid OLTP&OLAP main memory database system based on virtual memory snapshots." ICDE 2011. [doi:10.1109/ICDE.2011.5767867](https://doi.org/10.1109/ICDE.2011.5767867)
4. D. R. Morrison. "PATRICIA — Practical Algorithm to Retrieve Information Coded in Alphanumeric." JACM 1968. [doi:10.1145/321479.321481](https://doi.org/10.1145/321479.321481)
5. J. Rao, K. A. Ross. "Making B+-trees cache conscious in main memory." SIGMOD 2000. [doi:10.1145/342009.335449](https://doi.org/10.1145/342009.335449)
6. R. Binna, E. Zangerle, M. Pichl, G. Specht, V. Leis. "HOT: A Height Optimized Trie Index for Main-Memory Database Systems." SIGMOD 2018. [doi:10.1145/3183713.3196896](https://doi.org/10.1145/3183713.3196896)
7. [Bw-Tree and ART: Index Structures for New Hardware](bwtree-art.md) — sibling survey; Bw-tree mechanics and the ART-vs-B+tree occupancy experiment
8. [Advanced Index Structures](index-advanced.md) — index families: LSM trees, learned indexes, buffer-compatible trees
9. [ALEX Learned Indexes](alex-learned-indexes.md) — the learned-index alternative to classic tree indexes
10. [Kernel Data Structures](../../linux/kernel/data-structures.md) — the Linux radix tree/xarray lineage ART's Table II compares against
