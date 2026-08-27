# Centroid Decomposition

Centroid decomposition tears a tree into O(log n) nested pieces by
repeatedly deleting a centroid -- a vertex whose removal leaves no piece
bigger than half the tree. The survey in
[Tree Techniques](./tree-techniques.md) covers the concept, pseudocode,
and where it beats HLD or DSU on tree;
[Chapter 107](../chapters/ch107-hld-centroid-applications.md) shows the
HLD applications. This page covers what those pages skip: why a centroid
always exists, why the depth is O(log n), the LCA-on-path property that
makes path counting exact, and an executable build plus brute-force
validator.

## Centroids Exist, and There Are at Most Two

A centroid of an n-vertex tree is a vertex v such that every component of
T - v has at most floor(n/2) vertices. Existence proof (potential
argument): start at any vertex v. If some component of T - v holds more
than n/2 vertices, walk into it. Every component you can reach from the
new vertex is a strict subset of the component you just left, so the size
of the largest > n/2 component strictly decreases with each step. The
sizes are positive integers, so the walk stops, and it can only stop at a
vertex with no component above n/2 -- a centroid. There can be at most
two, and if there are two they are adjacent, joined by an edge whose
removal splits the tree into exactly n/2 + n/2.

## The Decomposition and Its Depth

The build is four lines: find a centroid of the current component, record
it, delete it, recurse on each remaining piece. Two consequences fall out
of the size bound:

- Depth: a piece at recursion depth d has at most n / 2^d vertices, and
  pieces of size >= 1 force 2^d <= n, so the centroid tree height is at
  most floor(log2(n)) -- the deepest cut of a 12-vertex tree below is 3.
- Build cost: at every depth the active pieces are vertex-disjoint, so
  one level costs O(n) DFS work; O(n log n) total to build the whole
  structure.

```text
original tree (12 nodes)          its centroid tree (depth in parens)

        0                                2 (0)
       / \                            /   |   \
      1   2                          1    7    8   (1)
      |   / \                       / \  /|\   / \
      3  4   5                    3   0 4 9 10 5   11  (2)
        /|\   \                      |   |
       6 7    8                      6   +-- (3) under 4

removing 2 first splits into {0,1,3}, {4,6,7,9,10}, {5,8,11}:
largest piece 5 <= floor(12/2) = 6. max depth 3 = floor(log2(12)).
```

## The LCA-on-Path Property

The property that powers every application: for any two vertices u, v,
the LCA of u and v in the CENTROID tree lies on the u-v path in the
ORIGINAL tree. Proof: let c be that LCA; when c was removed, u and v were
still in one component (otherwise their CT paths would have already
diverged and c would not be their CT ancestor). If the u-v path avoided
c, all its vertices would stay inside ONE component of comp - c, and u,
v would share a deeper centroid-tree ancestor -- contradicting c being
their LCA. Hence the path passes through c, and

    dist(u, v) = dist(u, c) + dist(c, v)

splits every path at exactly one centroid. Equivalently: every u-v path
is counted once, at the earliest-removed centroid on it.

## Path Counting Mechanics

Counting pairs at distance exactly k: process centroids in removal
order. At centroid c, collect distance profiles of each subtree hanging
off c (BFS limited to the live component), then count cross-subtree pairs
with d1 + d2 = k. Two details decide correct vs wrong:

1. Seed the accumulator with the centroid itself, {0: 1}, so paths with
   an endpoint at c (for example every edge when k = 1) are counted.
2. Pairs inside ONE subtree must not count: hash profiles incrementally
   and add subtree t against only the subtrees processed before it.

Complexity: every vertex appears in exactly one component per level, so
profile collection is O(n) per level and O(n log n) overall with hashing;
a sort + two-pointer per centroid gives the classic O(n log^2 n). The
"paths with maximum edge weight <= w" variant buckets edges by weight and
adds them incrementally -- the counting core is identical. Persisting all
profiles costs O(n log n) memory; keeping them transient costs O(n).

## Reference Implementation

Iterative build (no recursion-depth surprises) plus the counting routine,
validated on 200 random trees and, for path counts, against a brute-force
BFS pair count. Real output (Python 3.12) follows the code.

```python
# Centroid decomposition on random trees, checked against brute force:
# (1) every removal leaves components of size <= n_component // 2,
# (2) centroid-tree depth <= floor(log2(n)),
# (3) distance-exactly-k path counts match per-pair BFS counting.
from math import log2, floor
import random

def random_tree(n, seed):
    rng, adj = random.Random(seed), [[] for _ in range(n)]
    for v in range(1, n):
        p = rng.randrange(0, v)          # bushy random recursive tree
        adj[p].append(v); adj[v].append(p)
    return adj

def component(adj, removed, start):
    seen, stack = {start}, [start]
    while stack:
        v = stack.pop()
        for u in adj[v]:
            if u not in removed and u not in seen:
                seen.add(u); stack.append(u)
    return seen

def centroid_of(adj, comp):
    """Vertex whose removal leaves every piece <= len(comp) // 2."""
    n, start = len(comp), next(iter(comp))
    order, parent, stack = [], {start: None}, [start]
    while stack:
        v = stack.pop(); order.append(v)
        for u in adj[v]:
            if u in comp and u != parent.get(v):
                parent[u] = v; stack.append(u)
    size = {v: 1 for v in order}
    for v in reversed(order):
        if parent[v] is not None:
            size[parent[v]] += size[v]
    for v in order:
        biggest = n - size[v]            # piece away from the DFS root
        for u in adj[v]:
            if u in comp and u != parent[v]:
                biggest = max(biggest, size[u])
        if biggest <= n // 2:
            return v
    raise AssertionError("centroid not found (impossible)")

def decompose(adj, n):
    removed, ct_parent, depth, chrono = set(), [-1] * n, [0] * n, []
    max_depth, worst_slack = 0, 0
    queue = [(frozenset(range(n)), None)]
    while queue:
        comp, cpar = queue.pop()
        c, m = centroid_of(adj, comp), len(comp)
        d = 0 if cpar is None else depth[cpar] + 1
        ct_parent[c], depth[c] = cpar, d
        chrono.append(c)
        max_depth = max(max_depth, d)
        removed.add(c)
        done = {c}
        for u in adj[c]:
            if u not in removed and u not in done:
                nodes = frozenset(component(adj, removed, u))
                done |= nodes
                worst_slack = max(worst_slack, len(nodes) - m // 2)
                queue.append((nodes, c))
    return ct_parent, depth, chrono, max_depth, worst_slack

def count_paths_k(adj, n, k, chrono):
    """Pairs with dist(u,v) == k: at each centroid (in removal order),
    hash per-subtree distance profiles, count cross-subtree pairs."""
    removed, ans = set(), 0
    for c in chrono:
        total = {0: 1}                   # the centroid itself: endpoint d=0
        for u in adj[c]:
            if u in removed:
                continue
            local = {}
            stack = [(u, c, 1)]
            while stack:
                v, par, d = stack.pop()
                if d > k:
                    continue
                local[d] = local.get(d, 0) + 1
                for w in adj[v]:
                    if w not in removed and w != par:
                        stack.append((w, v, d + 1))
            for d, cnt in local.items():
                ans += total.get(k - d, 0) * cnt   # cross-subtree pairs
            for d, cnt in local.items():
                total[d] = total.get(d, 0) + cnt
        removed.add(c)
    return ans

def brute_paths(adj, n, k):
    ans = 0
    for s in range(n):
        dist = [-1] * n
        dist[s], q = 0, [s]
        for v in q:
            for u in adj[v]:
                if dist[u] < 0:
                    dist[u] = dist[v] + 1; q.append(u)
        ans += sum(1 for t in range(s + 1, n) if dist[t] == k)
    return ans

if __name__ == "__main__":
    print("checks 1+2: 200 random trees, n = 2..64")
    worst_slack, deepest_gap = 0, 0
    for seed in range(200):
        n = 2 + seed % 63
        _, _, _, max_depth, slack = decompose(random_tree(n, seed), n)
        assert slack <= 0, (seed, slack)      # comp size <= m // 2 always
        bound = floor(log2(n))
        assert max_depth <= bound, (n, max_depth, bound)
        worst_slack = max(worst_slack, -slack)
        deepest_gap = max(deepest_gap, bound - max_depth)
    print("  every component <= m//2, depth <= floor(log2(n)): OK")
    print(f"  largest size margin below bound: {worst_slack},"
          f"  largest depth gap below bound: {deepest_gap}")
    print()
    print("check 3: distance-exactly-k path counts vs brute force")
    for seed in range(3):
        n = 12 + seed * 3
        adj = random_tree(n, 1000 + seed)
        _, _, chrono, _, _ = decompose(adj, n)
        rows = [(k, count_paths_k(adj, n, k, chrono), brute_paths(adj, n, k))
                for k in range(1, min(6, n))]
        for k, a, b in rows:
            print(f"  n={n:>2} k={k}: centroid={a:>3} brute={b:>3}"
                  f"  {'OK' if a == b else 'FAIL'}")
        allmatch = all(count_paths_k(adj, n, k, chrono) == brute_paths(adj, n, k)
                       for k in range(1, n))
        print(f"  n={n}: all k in 1..{n-1} match: {allmatch}")
```

```text
checks 1+2: 200 random trees, n = 2..64
  every component <= m//2, depth <= floor(log2(n)): OK
  largest size margin below bound: 0,  largest depth gap below bound: 2

check 3: distance-exactly-k path counts vs brute force
  n=12 k=1: centroid= 11 brute= 11  OK
  n=12 k=2: centroid= 14 brute= 14  OK
  n=12 k=3: centroid= 16 brute= 16  OK
  n=12 k=4: centroid= 13 brute= 13  OK
  n=12 k=5: centroid=  8 brute=  8  OK
  n=12: all k in 1..11 match: True
  n=15 k=1: centroid= 14 brute= 14  OK
  n=15 k=2: centroid= 24 brute= 24  OK
  n=15 k=3: centroid= 23 brute= 23  OK
  n=15 k=4: centroid= 21 brute= 21  OK
  n=15 k=5: centroid= 15 brute= 15  OK
  n=15: all k in 1..14 match: True
  n=18 k=1: centroid= 17 brute= 17  OK
  n=18 k=2: centroid= 32 brute= 32  OK
  n=18 k=3: centroid= 47 brute= 47  OK
  n=18 k=4: centroid= 38 brute= 38  OK
  n=18 k=5: centroid= 16 brute= 16  OK
  n=18: all k in 1..17 match: True
```

The k = 1 rows are the regression that matters: an earlier draft omitted
the {0: 1} seed and reported 0 paths of length 1 instead of n - 1.

## Where It Sits Among Tree Tools

HLD answers path AGGREGATES with updates by decomposing into chains; the
comparison table in [Tree Techniques](./tree-techniques.md) contrasts the
two, and [Chapter 107](../chapters/ch107-hld-centroid-applications.md) is
the HLD reference. Centroid decomposition owns problems about ALL paths
(counting, nearest marked vertex, distance statistics), where its O(log n)
ancestor structure per vertex is the tool. Subtree-aggregate questions for
every node (distinct colors, mode) belong to DSU on tree or small-to-large
-- same page, separate sections. The structure is STATIC: edge updates
force an O(n log n) rebuild, and for fully dynamic forests you want the
link-cut trees and Euler-tour trees of
[Dynamic Trees](./dynamic-trees.md). Batch queries over a small vertex
subset map to virtual trees (also in Tree Techniques), not to centroids.

## Failure Modes

- Same-subtree double counting: pairs inside one subtree of a centroid
  are counted again at a deeper centroid, so cross-subtree bookkeeping is
  mandatory (incremental profile hashing above, or subtract local counts).
- Missing the d = 0 endpoint: all paths THROUGH the centroid with an
  endpoint at the centroid vanish; symptom: k = 1 counts come out 0.
- Recomputing sizes without the removed set: the DFS leaks across
  centroid boundaries, the "centroid" is wrong, and the recursion can
  revisit components forever.
- Deep recursion in the build: a path-like 10^5-vertex tree blows the
  Python/C stack at depth floor(log2 n) -- the depth is fine, but the
  per-level DFS must be iterative on adversarial shapes.
- Persisting per-centroid profiles for all levels costs O(n log n)
  memory; allocate O(n) scratch per level instead unless queries need it.

## References

- [cp-algorithms: Centroid decomposition](https://cp-algorithms.com/graph/centroid_decomposition.html)
- [USACO Guide: Centroid Decomposition module](https://usaco.guide/plat/centroid)
- [IOI 2011 "Race" (classic centroid application, oj.uz mirror)](https://oj.uz/problem/view/IOI11_race)
- [IOI 2011 official competition materials (PDF)](https://ioinformatics.org/files/ioi2011.pdf)
- [CSES "Fixed-Length Paths II" (path counting with centroids)](https://cses.fi/problemset/task/2131)
