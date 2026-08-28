# Maple Tree & XArray — Inside the Kernel's Index Trees

Two index structures now carry most of the kernel's scalar-keyed data: the
XArray, which stores pointer arrays keyed by a single `unsigned long` index,
and the maple tree, which stores values over *non-overlapping ranges*. They
are not merely "better hash tables" — both are built around the same
contraction: readers must walk the structure with no lock at all (RCU), so
every piece of type information has to be smuggled into pointer bits, and
every mutation must leave the tree walkable by readers that arrived before
the change.

This page is the internals-and-cost deep dive. The API-level tour
(`xa_store`, `radix_tree_insert`, the IDR) lives in
[data structures](../data-structures.md), and the page-cache consumer view —
`address_space.i_pages` — lives in the [page cache](page-cache.md); the
os-level [memory internals](../../../os/advanced/memory-internals.md)
sketch still shows the pre-conversion `radix_tree_root` field shape, a
useful reminder of what changed in 4.20. Here we descend into node
layouts, pointer encoding, locking contracts, and worked complexity
numbers.

## Part 1 — Entries are pointers: the shared encoding trick

Both structures face the same constraint: an RCU reader loads a `void *`
from a slot array with no lock held and no way to validate it afterward.
The only safe move is to make the *value itself* carry its own type in the
low bits. Both trees reserve the low two bits for this purpose.

| Low-bit pattern | Meaning in XArray | Meaning in maple tree |
|-----------------|-------------------|------------------------|
| `00` | normal pointer (must be 4-byte aligned) | pointer to a child node or stored value |
| `01` | internal entry (sibling, retry, zero, error) | parent pointer / node metadata |
| `10` | value entry (`xa_mk_value`, ≤ `LONG_MAX`) | reserved for internal use |
| `11` | tagged pointer (`xa_tag_pointer`) | node-type bits + flags |

The XArray's internal entries are numbered by `xa_mk_internal()`: values
0–62 are *sibling entries* (multi-index ranges share one real value),
256 is the *retry entry* (`XA_RETRY_ENTRY`, emitted when a node a reader
was traversing gets replaced), 257 is the *zero entry* (`XA_ZERO_ENTRY`,
created by `xa_reserve()`), and negative values encode stored `errno`s.
Two consequences follow from this encoding, and both show up in code
review:

- You cannot store `IS_ERR()` pointers — the error encoding would collide
  with internal entries. Errors travel via `xa_err()`, not as entries.
- You cannot store unaligned or function pointers. Kernel objects from
  `kmalloc()`/`alloc_page()` are safe; arbitrary user pointers are not.

The maple tree plays the same game with a different payload: the node
*type* is stored in bits 3–6 of the node pointer itself, so a reader that
dereferences a slot first decodes the type, then chooses the node layout.
A removed node's `->parent` is set to point at itself — readers that
loaded the node before deletion detect this self-pointer and restart,
which is how a node can be recycled for the RCU callback without ever
confusing a concurrent walk.

## Part 2 — XArray internals: a 64-way trie with marks

An XArray is a trie over the index: each node holds `XA_CHUNK_SIZE = 64`
slots, so every level consumes 6 index bits. A 32-bit index needs at most
5 levels; the common page-cache case for a 1 GiB file needs 3 (worked
numbers in Part 5). The root is inline: a single entry stored in
`xa_head` skips node allocation entirely, so a sparse small file costs
zero auxiliary memory.

### Marks

Each entry carries three user-visible marks (`XA_MARK_0/1/2`), stored as
per-node bitmaps and *replicated upward*: a node's mark bit is the OR of
its subtree's bits. The page cache uses the three marks as
dirty/writeback/error tags (the old `PAGECACHE_TAG_*` radix-tree tags
became these marks), and `filemap`'s writeback iterators then find the
next dirty index without scanning clean ranges. Two internal marks ride
the same bitmaps: `XA_PRESENT` (slot occupied) and `XA_FREE_MARK`
(used by allocating XArrays to track free indices). Setting or clearing a
mark costs O(height) with propagation; `xa_marked()` answers
"any entry marked at all?" in O(1) from the root bitmap.

### Multi-index entries

`xa_store_range()` stores one entry across a contiguous index range; the
trie collapses that range into a *sibling* pattern — one real entry plus
sibling entries pointing at it. A 2 MiB folio in the page cache covers
512 page indexes but occupies one trie slot group instead of 512 leaf
slots; [page types & folios](page-types.md) covers why that matters for
memory overhead. The arithmetic is in Part 5: for a 1 GiB file, large
folios shrink the node population from 4161 nodes to 9.

### Locking contract

The normal API hides two synchronization layers — an internal `xa_lock`
spinlock for writers and RCU for readers — and the documentation states
the split explicitly:

| Operation class | Lock taken | Examples |
|-----------------|------------|----------|
| read-only, no lock | none | `xa_empty()`, `xa_marked()` |
| read-only | RCU read lock | `xa_load()`, `xa_find()`, `xa_for_each()`, `xa_get_mark()` |
| mutation | `xa_lock` internally | `xa_store()`, `xa_erase()`, `xa_cmpxchg()`, `xa_alloc()`, `xa_reserve()`, `xa_set_mark()` |
| mutation, caller holds lock | none (assumed) | `__xa_store()`, `__xa_insert()`, `__xa_alloc()`, `__xa_set_mark()` |

The `_bh()` and `_irq()` variants pick the lock-disabling flavor; the
`__` variants exist so a caller already holding `xa_lock` (e.g., inside a
search that then updates) avoids reacquiring. Every mutating call also
takes a `gfp_t`: node allocation happens under the call, and passing
`GFP_NOWAIT` is legal — the store then fails cleanly with `-ENOMEM`
rather than sleeping, which is what page-cache reclaim paths rely on.
Initialization flags complete the contract: `XA_FLAGS_ALLOC` turns the
array into an ID allocator (`xa_alloc()` hands out the lowest free
index; `XA_FLAGS_ALLOC1` keeps index 0 reserved), and
`XA_FLAGS_LOCK_IRQ`/`XA_FLAGS_LOCK_BH` fix the lock flavor for the array's
lifetime.

### The xa_state advanced API

`XA_STATE(xas, xa, index)` declares a *cursor* on the stack. Unlike the
one-shot normal API, an `xa_state` walks the tree incrementally —
`xas_load()`, `xas_store()`, `xas_next()`, `xas_find()` — composing
operations without restarting from the root. Two rules make it safe:

1. If you drop the protecting lock (or RCU read section) mid-walk, call
   `xas_pause()` first; the next operation revalidates the cursor.
2. Every advanced-API result must pass through `xas_retry()`: if the tree
   handed you a retry entry, the node you were walking was replaced and
   the operation restarts. Forgetting this is the classic XArray bug.

The normal API is implemented in terms of the advanced one, and the
advanced API is GPL-exported only.

## Part 3 — Maple tree internals: ranges, gaps, and 256-byte nodes

The maple tree stores values over ranges — index `i` hits the value whose
`[min, max]` contains `i` — and can additionally answer *where is the
first gap of at least N?*, which is exactly the question
`get_unmapped_area()` asks. Nodes are 256 bytes, tuned so one node
occupies a quarter of a 4 KiB page and a hot subtree fits in a handful of
cache lines.

| Node type (`enum maple_type`) | Role | 64-bit layout | Size |
|-------------------------------|------|----------------|------|
| `maple_dense` | few entries, no pivots | 31 slots (`MAPLE_NODE_SLOTS`) | 256 B |
| `maple_leaf_64` | leaf: pivots + values | 16 slots (`MAPLE_RANGE64_SLOTS`) | 256 B |
| `maple_range_64` | internal: pivots + child pointers | 16 slots | 256 B |
| `maple_arange_64` | internal with gap array | 10 slots + `gap[10]` | 240 B |
| `maple_copy` | writer-side staging, not in tree | scratch union | — |

`range_64` nodes carry `pivot[15]` plus `slot[16]` and a one-byte
`maple_metadata` (slot count). `arange_64` nodes trade two slots for the
`gap[]` array: each slot records the largest free gap in its subtree, so
`mas_empty_area()` can descend straight toward a big-enough hole instead
of bisecting pivot-by-pivot. This is the structural feature the rbtree +
cached-hole scheme used for VMAs was approximating by hand.

### Writer strategies and the mas_* state machine

Writes are staged: `enum store_type` names the transformations the writer
may apply — `wr_new_root`, `wr_exact_fit`, `wr_append`, `wr_slot_store`,
`wr_node_store`, `wr_split_store`, `wr_rebalance`, `wr_spanning_store` —
and a `maple_copy` structure holds the old/new node set until the
transaction commits. Nothing halfway-assembled is ever published to
readers.

The user-facing side is a cursor, mirroring `xa_state`:

```c
MA_STATE(mas, &mm->mm_mt, addr, addr - 1);  /* cursor over [start, end] */
mas_walk(&mas);            /* find entry containing mas->index */
mas_store_gfp(vma, &mas, GFP_KERNEL);
mas_preallocate(&mas, vma, GFP_KERNEL);     /* cannot-fail stores later */
mas_find(&mas, ULONG_MAX);                  /* continue iteration */
mas_empty_area(&mas, min, max, size);       /* gap search */
mas_pause(&mas);                            /* drop RCU, resume later */
```

`mas_preallocate()` exists because a page-fault path that must insert a
VMA cannot tolerate a late `-ENOMEM` after it has already done side
effects — reserve nodes up front, then mutate. The mm subsystem wraps the
cursor in `struct vma_iterator` and drives it through `vma_iter_*`
helpers. Iteration is bidirectional (`mas_find_rev()`,
`mas_for_each_rev()`), and the maple tree header points Rust-side users
at `rust/kernel/maple_tree.rs` — the in-tree Rust bindings for the same
cursor API — which is how Rust drivers reach VMA storage.

### RCU contract

Readers run under `rcu_read_lock()` with no tree lock. Writers serialize
on the tree's `ma_lock` spinlock (or an external lock you attach at
`mt_init_flags()` time); deleted nodes keep their self-pointing `->parent`
until an RCU grace period frees them. [RCU](../sync/rcu.md) explains the
grace-period machinery; the maple tree's contribution is that node
recycling is the *only* thing it needs from RCU — no per-read copy, no
seqlock retry loop on the fast path.

## Part 4 — Why VMA storage moved, and what locking remains

Before 6.1, a process's VMAs were tracked by three cooperating
structures: the `mm->mmap` red-black tree (lookup by address), the
per-VMA `vm_rb` back-pointer (cached tree node), and the free-gap cache
(`mm->cached_hole_size`, hints for `get_unmapped_area()`). Every
`munmap` edge case had to keep three views consistent, and lookups took
the process-wide `mmap_lock` for reading.

The 6.1 conversion collapsed all of this into one maple tree per
`mm_struct` (`mm->mm_mt`). The locking now forms three layers:

```text
 user threads faulting / mprotect()ing
        |
        v
 mmap_lock (rw_semaphore) ---------- coarse: writer exclusion,
        |                            reader RCU-era fast path
        v
 maple tree  ma_lock (spinlock) ----- publish node mutations
        |            + RCU readers   walk without any lock
        v
 per-VMA locks (vma->vm_lock.seqcount) --- one VMA at a time,
        |                                  fault path only (6.4+)
        v
 VMA contents (page tables, rmap)
```

The maple tree alone did not remove `mmap_lock` contention — that came
from *per-VMA locks* (merged in 6.4): each VMA gained a lock/seqcount so
a page fault can `rcu_read_lock()`, look up the VMA in the maple tree,
and lock just that VMA, never touching `mmap_lock` for reads. (The
mmap_lock rwsem itself and the VMA lifecycle are covered in
[mmap](mmap.md).) What the
maple tree contributes is a range index that is safe to walk under RCU —
the property the rbtree never had, because rbtree rebalancing rewrites
nodes a concurrent reader may be holding. By 2026 the per-VMA lock code
became unconditional in all kernel builds, closing the scalability
chapter that began with the maple tree merge.

## Part 5 — The cost model, with worked numbers

The script below models both structures from their geometry constants
(no timing, pure arithmetic). It computes: VMA-storage costs for rbtree
vs maple tree, XArray node counts for a 1 GiB page-cache index tree
under 4 KiB pages vs 2 MiB folios, and the interval-lookup comparison
that motivates range trees at all.

```python
#!/usr/bin/env python3
"""Deterministic cost model: rbtree vs maple tree for VMA storage, and
XArray node counts for page-cache index trees. Pure stdlib, no timing."""

# ---- maple/rbtree geometry (64-bit kernel, from include/linux/maple_tree.h) --
MAPLE_RANGE64_SLOTS = 16   # leaf_64 and range_64: 16 slots, 256-byte nodes
MAPLE_ARANGE64_SLOTS = 10  # arange_64 internal nodes (with gap arrays)
MAX_MAP_COUNT_DEFAULT = 65530  # kernel default per-process VMA cap


def rbtree_height(n):
    """Height of a perfect binary search tree with n nodes: ceil(log2(n+1)).
    This is the MINIMUM possible pointer-chase depth for any balanced BST;
    a red-black tree's true worst case is ~2x this (2*log2(n+2))."""
    h, cap = 0, 0
    while cap < n:
        h += 1
        cap = 2 ** h - 1
    return h


def maple_height_and_nodes(n, leaf_slots=MAPLE_RANGE64_SLOTS,
                           child_slots=MAPLE_RANGE64_SLOTS - 1):
    """Minimal height and node count for n entries; leaf holds leaf_slots
    entries, each internal node fans out to child_slots children."""
    leaves = -(-n // leaf_slots)
    if leaves == 1:
        return 1, 1
    height, nodes, children = 1, leaves, leaves
    while children > child_slots:
        children = -(-children // child_slots)
        nodes += children
        height += 1
    return height, nodes + 1


def xa_node_count(n_entries, chunk=64):
    """XArray node count for n single-index entries (XA_CHUNK_SIZE=64)."""
    if n_entries <= chunk:
        return 1
    nodes, level = 1, n_entries          # root holds 64 children
    while level > chunk:
        level = -(-level // chunk)
        nodes += level
    return nodes


print("1) VMA storage: rbtree vs maple tree (worked numbers)")
print(f"{'VMAs':>7} | {'rbtree height':>13} | {'rbtree derefs*':>14} | "
      f"{'maple height':>12} | {'maple nodes':>11} | {'maple bytes**':>12}")
for n in (100, 1_000, 6_000, MAX_MAP_COUNT_DEFAULT):
    rh = rbtree_height(n)
    mh, mn = maple_height_and_nodes(n)
    print(f"{n:>7} | {rh:>13} | {rh:>14} | {mh:>12} | {mn:>11} | {mn*256:>12}")
print("   *  = node reads per lookup (perfect-tree bound), one pointer-chase each")
print("   ** = maple node footprint, 256 B per node (range64/leaf64)")

print()
print("2) Page cache XArray: 1 GiB file index tree (XA_CHUNK_SIZE = 64)")
pages_4k = 1024 * 1024 * 1024 // 4096
pages_2m = 1024 * 1024 * 1024 // (2 * 1024 * 1024)
n4 = xa_node_count(pages_4k)
print(f"   4 KiB pages : {pages_4k} entries -> {n4} xa_nodes "
      f"(3 levels: 1 root, 64 mid, 4096 leaves)")
print(f"   2 MiB folios: {pages_2m} entries  -> {xa_node_count(pages_2m)} xa_nodes")
print(f"   delta       : multi-index entries collapse {pages_4k // pages_2m}x")
print(f"   rbtree for the same 1 GiB: {pages_4k} nodes x ~(48 B node + 2 links)")

print()
print("3) Interval lookup: find the VMA containing an address, 1024 ranges")
starts = list(range(0, 1024 * 4096, 4096))          # disjoint 4 KiB ranges
linear_hits = 0
probes = 0
for q in range(0, 1024 * 4096, 4096 * 7 + 3):       # deterministic probes
    probes += 1
    for s in starts:
        linear_hits += 1
        if s > q:
            break
lo, hi = 0, len(starts)
bisect_hits = 0
for q in range(0, 1024 * 4096, 4096 * 7 + 3):
    l, h = 0, len(starts)
    while l < h:
        bisect_hits += 1
        m = (l + h) // 2
        if starts[m] <= q:
            l = m + 1
        else:
            h = m
print(f"   probes = {probes}, linear-scan comparisons = {linear_hits}, "
      f"bisect comparisons = {bisect_hits}")
print(f"   ratio = {linear_hits / bisect_hits:.1f}x fewer node touches "
      f"(binary search ~ log2(1024) = 10)")
```

Output (executed; byte-for-byte as produced):

```text
1) VMA storage: rbtree vs maple tree (worked numbers)
   VMAs | rbtree height | rbtree derefs* | maple height | maple nodes | maple bytes**
    100 |             7 |              7 |            1 |           8 |         2048
   1000 |            10 |             10 |            2 |          69 |        17664
   6000 |            13 |             13 |            3 |         403 |       103168
  65530 |            16 |             16 |            4 |        4392 |      1124352
   *  = node reads per lookup (perfect-tree bound), one pointer-chase each
   ** = maple node footprint, 256 B per node (range64/leaf64)

2) Page cache XArray: 1 GiB file index tree (XA_CHUNK_SIZE = 64)
   4 KiB pages : 262144 entries -> 4161 xa_nodes (3 levels: 1 root, 64 mid, 4096 leaves)
   2 MiB folios: 512 entries  -> 9 xa_nodes
   delta       : multi-index entries collapse 512x
   rbtree for the same 1 GiB: 262144 nodes x ~(48 B node + 2 links)

3) Interval lookup: find the VMA containing an address, 1024 ranges
   probes = 147, linear-scan comparisons = 75411, bisect comparisons = 1471
   ratio = 51.3x fewer node touches (binary search ~ log2(1024) = 10)
```

Reading the numbers:

- **Fan-out beats height.** At the default per-process VMA cap (65530),
  a 16-way maple tree bottoms out at height 4 — four dependent cache
  lines per lookup — while even a *perfect* binary tree needs 16 levels,
  and a real red-black tree can run up to about twice that because
  red-black balance permits a path up to 2·log₂(n+2) long. Height is the
  dominant lookup cost because each level is a dependent load.
- **Node count is a memory story, not just a speed story.** 4392 fixed
  256-byte nodes cost ~1.1 MiB per worst-case process. The equivalent
  rbtree at one node per VMA is ~65530 × 64 B ≈ 4.2 MiB of
  individually-allocated nodes, each a separate `kmalloc` — see
  [slab allocator](slab-allocator.md) for why 4392 carve-outs from one
  dedicated cache (`maple_node_cache`) are friendlier than 65530
  pointer-chase-prone allocations.
- **Multi-index entries are the folio payoff.** The same 1 GiB indexed
  with 2 MiB folios needs 9 nodes instead of 4161 — a 512× collapse —
  and each lookup still lands in 3 levels or fewer.
- **The interval-lookup row is the "why a tree at all" baseline**: a
  linear scan over 1024 ranges burns 75411 comparisons where the tree
  does 1471 — and the maple tree additionally answers *find a gap ≥ N*
  via `gap[]`, which binary search cannot do without extra descent.

## Part 6 — Choosing between them, and the classic pitfalls

| Requirement | Use | Why |
|-------------|-----|-----|
| index → pointer, dense or sparse keys | XArray | O(1)-ish fan-out per 6 bits, RCU reads, marks for writeback-style tagging |
| non-overlapping ranges, gap search, nearest-neighbor iteration | maple tree | pivot ranges per node, `gap[]` for free-space search, bidirectional cursors |
| small integer ID allocation | XArray with `XA_FLAGS_ALLOC` (`xa_alloc`) | lowest-free-index allocation with internal free tracking |
| cannot-fail insertion in a fault path | either, with preallocation | `mas_preallocate()` / `xa_reserve()` (reserve creates zero entries visible only via the advanced API) |

Pitfalls worth knowing before a kernel interview or a real patch:

1. Storing `ERR_PTR()` values in an XArray is a bug — errors are encoded
   as internal entries; check `xa_is_err()`/`xa_err()` on *returns*,
   never store error pointers.
2. Marks are exactly three. You cannot invent a fourth tag; if you need
   more, encode them in the stored object. Erasing an entry clears all
   its marks as a side effect.
3. Advanced-API walks must check `xas_retry()` after every operation;
   a retry entry means your node was replaced under RCU.
4. `xa_store()` with `GFP_KERNEL` may sleep for node allocation — do not
   call it from atomic context; use `GFP_NOWAIT` and handle `-ENOMEM`,
   or preallocate with `xa_reserve()`.
5. Maple tree values in `0..4096` with low bits `10` are reserved for
   internal use; user pointers are fine, but small magic integers need
   `xa_mk_value()` round-tripping.
6. The maple tree's value proposition is *ranges + RCU*, not raw
   single-key lookup: for plain `index → object` maps the XArray is
   simpler and just as fast.

## Self-check

1. Why can't an XArray store an `IS_ERR()` pointer, mechanically?
2. What makes a maple tree walk safe under RCU while an rbtree walk is not?
3. Where does the "2×" in the red-black height caveat come from?
4. How does `gap[]` in `arange_64` nodes change gap search from binary
   search?
5. What did per-VMA locks add that the 6.1 maple conversion alone did
   not deliver?
6. Name the three page-cache writeback states carried by XArray marks.

## References

- [XArray documentation](https://docs.kernel.org/core-api/xarray.html) — entry encodings, marks, locking table (kernel docs)
- [Maple Tree documentation](https://docs.kernel.org/core-api/maple_tree.html) — authoritative node-size and API description (kernel docs)
- [LWN: The XArray data structure](https://lwn.net/Articles/745073/) — design rationale for the radix-tree successor
- [LWN: Introducing the Maple Tree](https://lwn.net/Articles/901714/) — Liam Howlett's walkthrough of node types and store strategies
- [LWN: mm: Make per-VMA locks available in all builds](https://lwn.net/Articles/1070499/) — the mmap_lock scalability endgame built on maple+RCU
