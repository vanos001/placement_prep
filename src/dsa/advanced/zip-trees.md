# Zip Trees: A Skip List That Pretends to Be a Tree

Three randomized structures solve the same problem — keep a dynamic ordered set at
$O(\log n)$ depth so adversarial input never reaches the balance decisions. A treap
([Ch 104](../chapters/ch104-cartesian-tournament-trees.md)) flips a uniform priority per
node and rebalances with rotations; a skip list ([Ch 74](../chapters/ch74-skip-lists.md))
flips a coin per node and maintains express lanes above a sorted list. The zip tree of
Tarjan, Levy, and Timmel [1][2] observes these are two drawings of one coin: give a BST
*geometric* ranks instead of uniform priorities, allow ties, and the tree *is* a skip
list read sideways — and updates become two path merges, **zip** and **unzip**, instead
of rotation case analysis. This page covers the rank law and tie rule behind the
isomorphism, zip/unzip step by step, the $1.5\lg n$ depth bound, the zip-zip refinement,
and a runnable demo whose rank coins are consumed lazily, the pay-as-you-flip discipline
reservoir samplers use ([streaming-sampling](streaming-sampling.md)).

## 1. One Coin, Three Structures

A treap insists its priorities are tie-free, forcing updates through a rotation sewing
machine. A skip list insists level $k{+}1$ is a fair sample of level $k$. The zip tree
stores a random *rank* per node, heap-ordered with ties allowed — the two older
structures fall out as readings of the same object:

```text
zip tree (key:rank)                  isomorphic skip list
                                     L2:    4:2 ──────── 6:2      <- equal-rank run
            4:2                      L1:    2:1 ── 4:2 ── 6:2
           /    \                    L0: 1:0 ── 2:1 ── 3:0 ── 4:2 ── 5:0 ── 6:2 ── 7:0
        2:1      6:2
       /   \    /   \                     item e is in the level-k list
     1:0  3:0  5:0  7:0                    iff rank(e) >= k
```

The correspondence is exact: per [2], "given a zip tree, the isomorphic skip list
contains item $e$ in the level-$k$ sublist if and only if $e$ has rank at least $k$." A
right-child edge to an equal-rank node is the level-$k$ express lane; walking a right
spine enumerates the lane contents — which is why zip merges two subtrees by walking two
spines. The skip list's per-level coin and the tree's rank draw are the same geometric
variable: the tree is the compact encoding, one rank instead of a stack of pointers.

## 2. Ranks: Heads Until the First Tail

Ranks are drawn once at insert: flip a fair coin until the first tail and count the
heads, so "the rank of a node is non-negative integer $k$ with probability $1/2^{k+1}$"
[2] — geometric with mean 1, the law of a perfect BST's node heights. Theorem 1 of [2]:
expected root rank at most $\lg n + 3$, so the tree needs only $\lg\lg n + O(1)$ bits
w.h.p., versus the $\Theta(\lg n)$ bits a treap's near-uniform priorities need [1].

The heap condition is deliberately asymmetric — the whole trick. From [2]: "the parent
of a node has rank greater than that of its left child and no less than that of its
right child," ties toward smaller keys. Left children *strictly* decrease rank; right
children may tie, so equal-rank nodes chain rightward (the run $4{:}2 \to 6{:}2$ above),
each run one skip-list lane. Ties are not tolerated by the structure; they are the
structure, at a cost Section 5 prices and Section 6 refunds.

## 3. Zip: Two Spines, Zero Rotations

Deletion shows the machinery in its purest form: take "the right spine of the left
subtree of $x$ and the left spine of the right subtree of $x$" and zip them "in
non-increasing rank order, breaking a tie in favor of the smaller key" [2] — a merge,
not a rotation sequence:

```text
delete 4:2 -- zip the two spines it leaves behind
  P (right spine of 4.left): 2:1 -> 3:0     Q (left spine of 4.right): 6:2 -> 5:0
  merge top-down, higher rank wins, ties -> smaller key:
    6:2 vs 2:1 -> 6:2 wins, keeps 7:0, recurse left | 2:1 vs 5:0 -> 2:1 wins
    3:0 vs 5:0 -> rank tie, 3:0 wins, 5:0 attaches right
  result: 6:2 over 2:1, 7:0; 2:1 over 1:0, 3:0; 3:0's right child 5:0
```

The merge preserves the invariant by construction: both spines were already rank-sorted,
keys in $P$ all precede keys in $Q$, and only spine nodes are relinked while side subtree
pointers stay frozen. The cost is "one plus the number of nodes on the two zipped paths"
[2]; by Theorem 3 of [2], deleting a rank-$k$ node walks an expected $(3/2)k + 2$ spine
nodes with a Chernoff tail — updates pay in proportion to the deleted rank.

## 4. Unzip: Insertion Run Backwards

Insertion is the time-reversal. Descend to the first node $y$ the newcomer can legally
displace — the first $y$ with $\mathrm{rank}(y) \le \mathrm{rank}(x)$, strict when
$y.key < x.key$. From $y$ the rest of the path is *unzipped* into a $P$ path of smaller
keys and a $Q$ path of larger keys, each relinked into a lane with side subtrees frozen —
exactly the two spines a later deletion re-zips. The newcomer takes $y$'s place; the
operation writes $O(k)$ pointers and nothing below the displaced path moves.

| Structure | Per-node randomness | Update move | Expected depth / search | Rank bits (w.h.p.) |
|---|---|---|---|---|
| Treap [6] | uniform priority | rotations | $2\ln n \approx 1.39\lg n$ | $\Theta(\lg n)$ |
| Zip tree [1][2] | geometric, mean 1 | zip / unzip | $1.5\lg n$ | $\lg\lg n + O(1)$ |
| Zip-zip tree [4][5] | adjusted geometric | zip / unzip | $\le 1.3863\lg n - 1 + o(1)$ | $O(\lg\lg n)$ |
| Skip list, $p=\tfrac12$ [5] | coin per level | lane splicing | $\approx (1/p)\lg_{1/p} n = 2\lg n$ | 2 pointers |
| Splay tree [7] | none, adaptive | splaying rotations | $O(\lg n)$ amortized | none |

No-rotation is not merely aesthetic. Rotations are the case-analysis multiplier in
treap and RB-tree code, while zip/unzip are each a single loop over two lists — updates
"avoid some pointer changes" [1]. Two spines that only shrink from the top, side subtrees
never re-parented mid-merge, is also the shape of an operation an optimistic-concurrency
scheme can reason about locally, which is why the zip tree descends from concurrent-set
structures.

## 5. Expected Depth: Ancestor Counting, and the 8%

Depth = number of ancestors, split into *low* (smaller key) and *high* (larger key).
Theorem 2's proof is two-coin counting [2]: reading candidate low ancestors in decreasing
key order, each survives the rank threshold exactly when its coin stays heads long
enough, so for rank $k$ the expected low ancestors are at most $k+1$ and high ancestors
at most $k/2$ (Lemmas 2-3, exponential tails). Layering under Theorem 1: expected depth
at most $(3/2)\lg n + O(1)$ and $O(c\lg n)$ with probability $1 - 1/n^c$.
Search is the same number — ranks are never consulted — so search is $O(\log n)$ w.h.p.
Against a treap's $2\ln n$, the paper's admission: "allowing rank ties as we do thus
costs about 8% in average depth (and search time) but allows much more compact
representation of priorities" [2].

## 6. Zip-Zip Trees: Paying the 8% Back

Gila, Goodrich, and Tarjan revisit the rank law in "Zip-Zip Trees" [3][4]. The
tie-break that builds lanes also biases small keys toward the top; their variants fix
this while keeping zip/unzip untouched: expected depth at most $1.3863\lg n - 1 + o(1)$,
treap-exact, with $O(\lg\lg n)$ metadata bits w.h.p. [4]. The same paper ships a
just-in-time variant at expected $O(1)$ bits per node and partial persistence at $O(n)$
overhead.

## 7. Demo: Twenty Keys, Rank Coins, and Two Spine Zips

The script implements the paper's operations: geometric ranks from fair-coin flips,
insertion by unzipping the search path, deletion by zipping the two orphaned spines, and
an auditor asserting BST plus heap order after every change (fixed 20 keys, seed 7).

```python
import random
random.seed(7)
class Node:
    def __init__(self, key, rank):
        self.key, self.rank, self.left, self.right = key, rank, None, None

OPS = {"flips": 0, "visits": 0, "unzip": 0, "zip": 0}
def draw_rank():                       # heads before the first tail: geometric, mean 1
    r = 0
    while r < 64 and random.getrandbits(1):
        r += 1
    OPS["flips"] += r + 1
    return r
def zip_spines(a, b):                  # merge a,b (keys(a) < keys(b)); rank tie -> a
    if a is None or b is None:
        return a or b
    if a.rank >= b.rank:               # tie goes to a: smaller keys win ties
        a.right = zip_spines(a.right, b)
        OPS["zip"] += 1
        return a
    b.left = zip_spines(a, b.left)
    OPS["zip"] += 1
    return b
def insert(root, key):                 # descend, unzip the path below, attach
    x = Node(key, draw_rank())
    path, y = [], root
    while y is not None and (y.rank > x.rank or
                             (y.rank == x.rank and y.key < x.key)):
        path.append(y)
        y = y.left if key < y.key else y.right
        OPS["visits"] += 1
    P, Q = [], []
    while y is not None:               # split the rest of the search path by key
        (P if y.key < key else Q).append(y)
        y = y.right if y.key < key else y.left
        OPS["unzip"] += 1
    for i in range(len(P) - 1):        # re-chain the two lanes; every other
        P[i].right = P[i + 1]          # subtree pointer is left untouched
    for i in range(len(Q) - 1):
        Q[i].left = Q[i + 1]
    if P: P[-1].right = None
    if Q: Q[-1].left = None
    x.left, x.right = (P[0] if P else None), (Q[0] if Q else None)
    if not path:
        return x
    if key < path[-1].key: path[-1].left = x
    else: path[-1].right = x
    return root
def delete(root, key):                 # search, then zip the two spines x leaves
    parent, x = None, root
    while x.key != key:                # demo assumes the key exists
        parent, x = x, x.left if key < x.key else x.right
        OPS["visits"] += 1
    new = zip_spines(x.left, x.right)
    if parent is None:
        return new
    if key < parent.key: parent.left = new
    else: parent.right = new
    return root
def search(root, key):                 # plain BST search: ranks are never consulted
    node = root
    while node is not None:
        OPS["visits"] += 1
        if node.key == key:
            return node
        node = node.left if key < node.key else node.right
    return None
def audit(root):                       # assert BST order + heap order; collect stats
    out = []
    def walk(n, lo, hi, d):
        assert lo < n.key < hi and (not n.left or n.rank > n.left.rank) \
            and (not n.right or n.rank >= n.right.rank)
        out.append((n.key, n.rank, d))
        if n.left:  walk(n.left, lo, n.key, d + 1)
        if n.right: walk(n.right, n.key, hi, d + 1)
    walk(root, float("-inf"), float("inf"), 0)
    return out
KEYS = [50, 30, 70, 20, 40, 60, 80, 10, 45, 65, 75, 85,
        35, 55, 15, 25, 5, 90, 42, 68]
root = None
for k in KEYS:
    root = insert(root, k)
pairs = sorted(audit(root))
print("seed 7, inserted %d keys; entries are key:rank@depth" % len(KEYS))
for i in range(0, len(pairs), 5):
    print("   " + "   ".join("%2d:r%d@d%d" % p for p in pairs[i:i + 5]))
ds = [p[2] for p in pairs]
hist = "  ".join("d%d:%d" % (d, ds.count(d)) for d in range(max(ds) + 1))
print("depth histogram:", hist)
print("invariants OK: BST order; rank(x) > rank(x.left); rank(x) >= rank(x.right)")
for k in (42, 60, 20):
    root = delete(root, k)
audit(root)
print("deleted 42, 60, 20 by zipping their spines; invariants OK; n = %d"
      % len(audit(root)))
hits = sum(1 for k in KEYS if k not in (42, 60, 20) and search(root, k) is not None)
miss = sum(1 for k in (42, 60, 20) if search(root, k) is None)
print("search: %d/17 remaining keys found; %d/3 deleted keys correctly absent"
      % (hits, miss))
print("ops: coin flips %d, node visits %d, unzip relinks %d, zip relinks %d, total %d"
      % (OPS["flips"], OPS["visits"], OPS["unzip"], OPS["zip"], sum(OPS.values())))
```

Real output:

```text
seed 7, inserted 20 keys; entries are key:rank@depth
    5:r1@d1   10:r1@d2   15:r0@d4   20:r1@d3   25:r0@d5
   30:r1@d4   35:r0@d5   40:r0@d6   42:r2@d0   45:r2@d1
   50:r0@d3   55:r0@d4   60:r2@d2   65:r0@d4   68:r1@d3
   70:r0@d4   75:r0@d5   80:r0@d6   85:r0@d7   90:r0@d8
depth histogram: d0:1  d1:2  d2:2  d3:3  d4:5  d5:3  d6:2  d7:1  d8:1
invariants OK: BST order; rank(x) > rank(x.left); rank(x) >= rank(x.right)
deleted 42, 60, 20 by zipping their spines; invariants OK; n = 17
search: 17/17 remaining keys found; 3/3 deleted keys correctly absent
ops: coin flips 31, node visits 136, unzip relinks 28, zip relinks 6, total 201
```

The tree shows the theory's fingerprints. Root 42 carries rank 2 near the
$\lg 20 \approx 4.3$ scale, 20 coin draws bought ranks summing to 11, and the deepest
node 90 sits at depth 8 — below the rank-2 ceiling because rank-0 ties chain rightward
($80{:}0 \to 85{:}0 \to 90{:}0$), the tie cost made visible. All 201 counted operations
were visits, flips, or spine relinks.

## 8. Interview Q&A

**Q: Treap priorities must be distinct, yet zip tree ranks collide freely. What replaces
uniqueness?**
A: A lexicographic rule. Heap order is on rank with ties toward smaller keys: strict
decrease across left edges, non-strict across right edges. Given (key, rank) pairs the
shape is still unique, and ties form rightward runs — which the isomorphism reads as
skip-list lanes, not ambiguity.

**Q: When does the zip tree beat the treap, and when does it lose?**
A: It wins on metadata and update traffic: $\lg\lg n + O(1)$-bit ranks w.h.p. versus
$\Theta(\lg n)$ priorities, and updates rewrite only the unzipped/zipped path rather
than rotating — fewer pointer changes [1]. It loses ~8% expected search depth to rank
ties. For per-key priorities a treap is the more direct tool, or use zip-zip (Section 6).

## References

1. R. E. Tarjan, C. Levy, S. Timmel, "Zip Trees," *ACM Transactions on Algorithms* 17(4):1-12, 2021. <https://doi.org/10.1145/3476830>
2. R. E. Tarjan, C. C. Levy, S. Timmel, "Zip Trees," *Algorithms and Data Structures* (WADS 2019), LNCS, pp. 566-577, 2019. <https://doi.org/10.1007/978-3-030-24766-9_41>
3. O. Gila, M. T. Goodrich, R. E. Tarjan, "Zip-Zip Trees: Making Zip Trees More Balanced, Biased, Compact, or Persistent," WADS 2023, LNCS, pp. 474-492. <https://doi.org/10.1007/978-3-031-38906-1_31>
4. O. Gila, M. T. Goodrich, R. E. Tarjan, "Zip-Zip Trees: Making Zip Trees More Balanced, Biased, Compact, or Persistent," *Algorithmica* 88(3), 2026. <https://doi.org/10.1007/s00453-025-01364-2>
5. W. Pugh, "Skip lists: a probabilistic alternative to balanced trees," *Communications of the ACM* 33(6):668-676, 1990. <https://doi.org/10.1145/78973.78977>
6. R. Seidel, C. R. Aragon, "Randomized search trees," *Algorithmica* 16(4/5):464-497, 1996. <https://doi.org/10.1007/BF01940876>
7. D. D. Sleator, R. E. Tarjan, "Self-adjusting binary search trees," *Journal of the ACM* 32(3):652-686, 1985. <https://doi.org/10.1145/3828.3835>
