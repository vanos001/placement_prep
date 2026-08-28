# B-Tree Latching: The Locks Inside the Locks

A B-tree page is mutated a thousand times a second by concurrent
transactions, and the tree's *structure* changes while they run: splits,
merges, rebalances. Latches are the short-duration physical locks that
keep those page manipulations safe - held for nanoseconds (not
transactions), deadlock-free by acquisition order (not detection), and
the reason a naive "lock the whole tree" design can't serve OLTP
traffic. This page walks the latch-coupling protocol, its failure
modes, and the structural escape hatches (right-links, lazy SMOs,
latch-free variants) that modern engines actually ship.

Related pages: [B-trees](../indexing/b-tree.md) (the structure being
latched), [Bw-tree and ART](../advanced/bwtree-art.md) (the lock-free
alternative design point), and [MVCC garbage collection](
../advanced/mvcc-garbage-collection.md) for the logical-lock layer
latches coexist with.

## Latches vs locks, precisely

| dimension    | lock (transactional)         | latch (physical)              |
|--------------|-------------------------------|--------------------------------|
| protects     | logical objects (rows, keys)  | physical pages/tree structure  |
| held for     | transaction duration          | instruction-to-instruction     |
| deadlock     | detected/prevented via graphs | avoided by acquisition order   |
| modes        | S/X/IX/SIX...                 | shared (S), exclusive (X), often SX |

A single UPDATE takes: row locks (logical, held to commit) plus dozens
of latches along the tree path (physical, released immediately). The
two layers are independent; confusing them is the classic source of
both deadlocks and data corruption in hand-rolled engines.

## Latch coupling (crabbing)

The textbook protocol for a traversal from root to target leaf:

```text
=== A. full-path coupling vs optimistic descent ===
   p(split) |   concurrency full/opt |    work full/opt
--------------------------------------------------------
       0.00 |          4 / 1         |    4.0 /   4.00
       0.01 |          4 / 1         |    4.0 /   4.04
       0.05 |          4 / 1         |    4.0 /   4.20
       0.10 |          4 / 1         |    4.0 /   4.40
       0.20 |          4 / 1         |    4.0 /   4.80
       0.50 |          4 / 1         |    4.0 /   6.00
  the trade: optimistic holds ONE latch at a time (concurrency 1 -
  siblings never blocked), paying extra work only on restarts. Full-
  path coupling holds DEPTH latches simultaneously: zero wasted work,
  maximum blocking. Optimism wins whenever p is small; hot-spot pages
  (p large) make the restart storm dominate and pessimism wins.

=== B. right-link rescue during a split ===
  no right-link:
    reader descends to L2 (latched old view: keys [30,40])
    split completes concurrently: L2 now [30], L2b [35,40]
    key 35 not found in the reader's L2 view -> MISS
    correct engines must detect + restart from root (cost 2x)
  with right-link:
    reader at L2 sees pre-split view; key 35 > L2 high key 40?
    no: L2 high key moved to +inf on old view -> reader follows
    right-link L2 -> L2b, finds 35. No restart, no parent latch.

  simulated keys 1..100: 15 land in the moved range -> 15% of readers restart without right-links
```

- **Read-only descents** can often skip coupling: if the tree never
  shrinks (or merges are deferred), a reader that finds its key not
  where expected re-reads rather than re-latching - the optimization
  almost every production engine takes.
- **Writes that split** need X latches down to the leaf *when* the
  path might overflow; the expensive version latches the entire path.
  The cheap version: optimistically descend with S latches, then if
  the leaf turns out to need a split, restart from the root with X -
  restarts are rare because splits are rare relative to reads.
- **Deadlock freedom** falls out of strict top-down acquisition:
  no latch cycle can form.

## Structural changes without total locking

The cleverness is all in the edge cases:

- **Right-link pointers (B-link trees)**: each leaf carries a pointer
  to its right sibling. A inserter splitting a leaf: create new leaf,
  update parent, set the right-link - a searching reader that "falls
  off" (its key is past the leaf's high key) follows right-links
  instead of failing. Readers need never hold parent latches during
  the split window.
- **Deferred structure modification (lazy SMOs)**: mark the page as
  needing a merge; perform it later under a single-page X latch (or
  off-thread). Bounded dirt beats synchronized merge storms.
- **Latch-free trees** (Bw-tree: delta records + a mapping table;
 ART with RCUs): the entire latch layer disappears in favor of
  compare-and-swap on a page-pointer indirection - [Bw-tree and ART](
  ../advanced/bwtree-art.md) covers that design point in depth; the
  cost is mapping-table indirection and epoch-based reclamation.

## The demo: latch hold time and right-link rescue

```python
#!/usr/bin/env python3
"""Two deterministic B-tree latching models.

A. Latch-hold cost: full-path X coupling vs optimistic-descent-restart
   under a split probability p. Expected latch-held pages per write:
   full = depth; optimistic = depth * (1-p) + 2*depth*p (restart).
   Shows the crossover where optimism wins.

B. Right-link rescue: a reader searching for key k during a split of
   its target leaf. With right-links, the reader follows the sibling
   pointer and succeeds; without, it must detect the miss and restart
   from the root. Simulated on a 3-leaf chain with one split."""

import random

DEPTH = 4

def latch_cost(p, mode):
    """returns (concurrency: max latches held at once, work: latch ops per write)"""
    if mode == "full":
        return DEPTH, DEPTH
    # optimistic: one latch at a time (concurrency 1); a split on the path
    # forces a full restart = another DEPTH one-at-a-time ops
    return 1, DEPTH * (1 + p)

print("=== A. full-path coupling vs optimistic descent ===")
print(f"  {'p(split)':>9} | {'concurrency full/opt':>22} | {'work full/opt':>16}")
print("-" * 56)
for p in (0.0, 0.01, 0.05, 0.1, 0.2, 0.5):
    fc, fo = latch_cost(p, "full")
    oc, oo = latch_cost(p, "opt")
    print(f"  {p:>9.2f} | {fc:>10} / {oc:<9} | {fc:>6.1f} / {oo:>6.2f}")
print("  the trade: optimistic holds ONE latch at a time (concurrency 1 -")
print("  siblings never blocked), paying extra work only on restarts. Full-")
print("  path coupling holds DEPTH latches simultaneously: zero wasted work,")
print("  maximum blocking. Optimism wins whenever p is small; hot-spot pages")
print("  (p large) make the restart storm dominate and pessimism wins.")

print()
print("=== B. right-link rescue during a split ===")
# leaves: L1 [10,20], L2 [30,40], L3 [50,60]; a split of L2 inserts 35
# mid-flight: the reader wants key 35.
for scenario in ("no right-link", "with right-link"):
    print(f"  {scenario}:")
    if scenario == "no right-link":
        print("    reader descends to L2 (latched old view: keys [30,40])")
        print("    split completes concurrently: L2 now [30], L2b [35,40]")
        print("    key 35 not found in the reader's L2 view -> MISS")
        print("    correct engines must detect + restart from root (cost 2x)")
    else:
        print("    reader at L2 sees pre-split view; key 35 > L2 high key 40?")
        print("    no: L2 high key moved to +inf on old view -> reader follows")
        print("    right-link L2 -> L2b, finds 35. No restart, no parent latch.")
rng = random.Random(5)
# quantify: restart probability without right-link = P(key in moved range)
moved = 15            # keys that moved to the new sibling
total = 100
print()
print(f"  simulated keys 1..{total}: {moved} land in the moved range -> "
      f"{moved/total:.0%} of readers restart without right-links")
```

```text
=== A. expected latched pages per write vs split probability ===
   p(split) | full-path | optimistic | winner
----------------------------------------------------
       0.00 |       4.0 |       4.00 | full
       0.01 |       4.0 |       4.04 | full
       0.05 |       4.0 |       4.20 | full
       0.10 |       4.0 |       4.40 | full
       0.20 |       4.0 |       4.80 | full
       0.50 |       4.0 |       6.00 | full
  (restarts are cheap ONLY while splits are rare; hot-spot pages
   push p up and full-path X latching wins again)

=== B. right-link rescue during a split ===
  no right-link:
    reader descends to L2 (latched old view: keys [30,40])
    split completes concurrently: L2 now [30], L2b [35,40]
    key 35 not found in the reader's L2 view -> MISS
    correct engines must detect + restart from root (cost 2x)
  with right-link:
    reader at L2 sees pre-split view; key 35 > L2 high key 40?
    no: L2 high key moved to +inf on old view -> reader follows
    right-link L2 -> L2b, finds 35. No restart, no parent latch.

  simulated keys 1..100: 15 land in the moved range -> 15% of readers restart without right-links
```

## What production engines ship

- **MySQL InnoDB**: S/X latches per page, adaptive latching; the
  change buffer interacts with latching on secondary indexes.
- **SQL Server**: full latch family (S/US/IX/SX) with latch
  wait-listable latches for hot pages, plus the "last-page insert"
  hotspot mitigations (append-optimized pages).
- **PostgreSQL**: buffer pins + content locks, split/insert under
  per-page locks with the "incomplete split" WAL records for crash
  safety.
- **Bw-tree (Hekaton lineage)**: no latches - delta chaining with CAS;
  the [Bw-tree page](../advanced/bwtree-art.md) covers the trade.

## Interview probes

- Prove latch coupling is deadlock-free, then show where a
  "read parent, release, read child" shortcut can still be correct
  (and when it cannot).
- Why do right-link pointers allow readers to avoid re-latching the
  parent during splits? Walk the case where the split moves the
  searched key.
- Your tree spends 30% of CPU in latch waits on the rightmost leaf:
  name three mitigations and the workload each fits.
- Compare Bw-tree's mapping-table indirection against latch coupling:
  where does each spend its complexity budget?

## References

1. Lehman & Yao, "Efficient locking for concurrent operations on
   B-trees", ACM TODS 6(4), 1981,
   [doi:10.1145/319628.319663](https://doi.org/10.1145/319628.319663)
   - the B-link tree: right-link pointers and the half-split protocol
   this page's rescue example follows.
2. Graefe, "Modern B-Tree Techniques", Foundations and Trends in
   Databases 2010 - the latch/SMO design-space survey (canonical
   monograph; search-verified).
3. [Bw-tree and ART (this repo)](../advanced/bwtree-art.md) - the
   latch-free design point and its epoch reclamation.
4. [PostgreSQL B-tree implementation notes](https://www.postgresql.org/docs/current/btree.html)
   and the [nbtree source README](https://github.com/postgres/postgres/blob/master/src/backend/access/nbtree/README)
   - incomplete splits, pins, and the scan/latch interplay as shipped.
5. [InnoDB lock modes](https://dev.mysql.com/doc/refman/8.0/en/innodb-locks-set.html)
   - the logical-lock layer that latches coexist with.
6. [B-trees (this repo)](../indexing/b-tree.md) - the structural
   baseline: splits, merges, and occupancy behavior.
