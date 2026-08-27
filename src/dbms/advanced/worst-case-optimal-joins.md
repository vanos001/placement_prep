# Worst-Case Optimal Joins (AGM Bound & Leapfrog Triejoin)

Every production optimizer plans joins **pairwise**: pick an order, hash-join
two relations, feed the result into the next. This page covers the result that
broke that assumption: on cyclic queries, *any* binary plan can do
asymptotically more work than the join requires, while worst-case optimal
(WCOJ) algorithms provably do not. The gap is not a tuning artifact -- it is a
sqrt(m)-factor separation that shows up on triangle counts, graph pattern
matching, and self-joins over skewed relations. The survey-level version of
this material is in [Query Optimizers](query-optimizers.md); the motivating
workload is in [Graph Databases](graph-databases.md).

## Where binary-join plans pay double

Triangle count over one directed edge relation `E`:

```text
Q(x,y,z) := E(x,y), E(y,z), E(z,x)

E(x,y) join E(y,z) on y  -> intermediate I(x,y,z)   [materialized]
I(x,y,z) join E(z,x)     -> triangles
```

The first join produces **every path of length 2**: `sum over y of
indeg(y)*outdeg(y)`. One hub vertex of degree `d` contributes `d*d`
intermediates. With `d ~ m` (m = edge count) the intermediate is `Theta(m^2)`
-- while the triangle count can be zero. Optimizers never see it coming:
cardinality estimation assumes attribute independence, which is maximally
false on graph edges.

```text
     hub skew: why the intermediate explodes
  in          hub         out
  a1 -->.    .---.    .--> b1      every (ai, hub, bj) pair becomes an
  ... -->+--> ( 0 ) -->+-- ...      intermediate tuple BEFORE the third
  ad -->'    '---'    '--> bd      join checks whether bj -> ai exists
        d tuples  d tuples    =>  d*d tuples, almost all of them dead
```

## The AGM bound: output size before running anything

Atserias, Grohe, Marx (FOCS 2008; TODS 2013) bound the output of any full join
via a **fractional edge cover**: give each relation weight `w_i <= 1` so every
attribute's incident weights sum to at least 1; then the output size is at
most the product of `|R_i|^w_i`. For the triangle query the cover puts weight
1/2 on each edge (each variable covered exactly once):

```text
AGM(triangle) = m^(1/2) * m^(1/2) * m^(1/2) = m^(3/2)
```

Worth memorizing:

- **Tight**: instances achieving `m^(3/2)` exist (a clique on `sqrt(m)`
  vertices; each edge relation has m tuples).
- A `k`-clique query has bound `m^(k/2)`, while a binary left-deep plan can
  pay `m^(k-1)` in intermediates -- the gap grows with cycle length.
- AGM bounds the **final output** only. Binary plans can exceed it on an
  intermediate before the last join ever runs.

Ngo, Porat, Re, Rudolph (PODS 2012; JACM 2018) then built the first algorithm
whose *runtime* matches the bound; "Skew Strikes Back" (arXiv 1310.3314) is
the readable survey of that line.

## Generic join: bind one variable at a time

WCOJ algorithms abandon pairwise plans. Process **variables in a fixed
order**; at each step, the candidate values for the next variable are the
intersection of what every relation containing it allows. For the triangle
with order x, y, z: candidates for y given x are `E(x,.)` intersect `E(.,y)`
-- so a heavy vertex with no common neighbors costs one intersection probe,
not `d*d` dead tuples. No intermediate join result is ever materialized: each
partial binding is either extended or abandoned. Runtime then depends on how
efficiently you intersect, which is where the trie comes in.

## Leapfrog Triejoin internals

Veldhuizen's Leapfrog Triejoin (LogicBlox; arXiv 1210.0481) makes Generic
Join concrete:

1. Store each relation as a **trie** keyed by variable order -- in practice
   nested sorted arrays, not pointer nodes.
2. At depth d, every relation constraining the current variable positions a
   trie iterator at the node for the binding so far.
3. A **leapfrog seek** binary-searches the lagging iterator past the current
   leader, alternating until all iterators agree on a value. One seek can
   skip millions of non-matching values.

```text
trie for E(x,y), edges {a->1, a->7, b->1, c->7}:
(root)
  a -- [1] [7]        depth 1 = x values (sorted array, bisectable)
  b -- [1]            depth 2 = y values under each x
  c -- [7]

leapfrog on x: iter1 heads [a b c], iter2 heads [a c]
  leader a; iter2 already at a -> emit a; advance both
  leader b; iter2 seeks past c -> exhausted for b (binary search, 1 probe)
```

Published guarantee: `O(AGM(Q,D) * q * log n)` for full conjunctive queries
(q = query size), worst-case optimal for strictly finer instance classes than
NPRR requires. Trie construction costs `O(m log m)` up front, which is why
systems that ship LFTJ keep tries as a persistent access method rather than
building them per query.

## Measured on a skewed graph

The script counts triangles three ways on a 100-edge graph engineered for hub
skew (31 nodes; hub 0 has 30 in- and 30 out-edges, plus two 5-cliques and
leaves): naive triple loop, the classic binary hash-join plan, and a leapfrog
triejoin that counts every seek step.

```python
# Demo: worst-case optimal (leapfrog triejoin) vs binary-join plans on a skewed graph.
# Query: triangle count  R(x,y), R(y,z), R(z,x)  over directed edge relation R.
import bisect

E = set()
for base in (1, 6):                              # two 5-cliques, ordered pairs
    for i in range(5):
        for j in range(5):
            if i != j:
                E.add((base + i, base + j))
for i in range(1, 11):                           # hub node 0 <-> clique nodes
    E.add((0, i)); E.add((i, 0))
for leaf in range(11, 31):                       # hub <-> 20 pendant leaves
    E.add((0, leaf)); E.add((leaf, 0))
E = sorted(E)
nodes = sorted({v for e in E for v in e})
eset = set(E)
out_adj = {v: sorted(b for (a, b) in E if a == v) for v in nodes}
indeg = {v: sum(1 for (a, b) in E if b == v) for v in nodes}

naive_checks = triangles = 0                     # baseline 1: triple loop
for x in nodes:
    for y in nodes:
        if (x, y) not in eset:
            continue
        for z in nodes:
            naive_checks += 1
            if (y, z) in eset and (z, x) in eset:
                triangles += 1

intermediate = bin_triangles = 0                 # baseline 2: hash-join plan
for (x, y) in E:
    for z in out_adj[y]:
        intermediate += 1
        if (z, x) in eset:
            bin_triangles += 1

tries = {}                                       # tries keyed (x,y),(y,z),(z,x)
for key in ("xy", "yz", "zx"):
    t = {}
    for (a, b) in E:
        t.setdefault(a, []).append(b)
    tries[key] = {k: sorted(v) for k, v in t.items()}

seeks = 0

def leapfrog(lists):                             # intersect sorted lists
    global seeks
    k = len(lists)
    if any(len(L) == 0 for L in lists):
        return []
    pos, out = [0] * k, []
    p = max(range(k), key=lambda i: lists[i][0])
    while True:
        thr = lists[p][pos[p]]
        exhausted, aligned = False, True
        for i in range(k):
            if i == p:
                continue
            j = bisect.bisect_left(lists[i], thr, pos[i]); seeks += 1
            if j >= len(lists[i]):
                exhausted = True; break
            pos[i] = j
            if lists[i][j] > thr:
                thr, p, aligned = lists[i][j], i, False; break
        if exhausted:
            break
        if aligned:
            out.append(thr)
            pos[p] += 1
            if pos[p] >= len(lists[p]):
                break
    return out

lftj_triangles = 0
for x in leapfrog([sorted(tries["xy"]), sorted(tries["zx"])]):
    for y in leapfrog([tries["xy"].get(x, []), sorted(tries["yz"])]):
        for z in leapfrog([tries["yz"].get(y, []), tries["zx"].get(x, [])]):
            lftj_triangles += 1

print(f"graph: {len(nodes)} nodes, {len(E)} directed edges")
print(f"triangles: naive={triangles} binary-join={bin_triangles} lftj={lftj_triangles}")
print(f"naive triple-loop candidate checks : {naive_checks}")
print(f"binary plan intermediate (x,y,z)   : {intermediate}  (hub node 0 alone: {indeg[0] * len(out_adj[0])})")
print(f"leapfrog triejoin seek steps       : {seeks}")
print(f"AGM bound for this instance |E|^3/2: {len(E) ** 1.5:.0f}")
```

Real output (Python 3.12, deterministic graph):

```text
graph: 31 nodes, 100 directed edges
triangles: naive=240 binary-join=240 lftj=240
naive triple-loop candidate checks : 3100
binary plan intermediate (x,y,z)   : 1170  (hub node 0 alone: 900)
leapfrog triejoin seek steps       : 491
AGM bound for this instance |E|^3/2: 1000
```

Reading it: the binary plan's *first* join already materializes 1170
candidates -- above the AGM bound of 1000 for the whole join -- and 900 come
from the single hub. The triejoin never builds that intermediate: 491 seeks,
no memory for any intermediate. The gap is modest at 100 edges; it grows as
sqrt(m) because the binary plan's intermediate scales like d^2 while the bound scales like m^(3/2).

## Who actually ships it

Verified status (mid-2026) -- folklore here is unreliable; several sources
claim DuckDB runs WCOJ, which the DuckPGQ paper contradicts: it names WCOJ
over an adjacency index as a *future direction*, and DuckDB core joins remain
binary hash joins.

| System | Status | What it runs |
|---|---|---|
| LogicBlox | Production since ~2014 | LFTJ over tries, original Veldhuizen deployment |
| Umbra (HyPer successor) | Production research system | Generic join alongside binary joins, cost-based switch per subplan |
| Kuzu | Production | Multiway worst-case optimal join on its ASP join operator |
| DuckDB core | Not implemented | Binary hash joins only; DuckPGQ extension names WCOJ as future work |
| EmptyHeaded | Research | Generic Join for graph analytics; started the practical evaluations |

The paper to quote is Umbra's (Freitag, Bandle, Schmidt, Kemper, Neumann,
PVLDB 2020): worst-case optimal generic join integrated into a real
compile-and-vectorize engine, selected against binary plans by cost. Their
finding matches the demo -- WCOJ wins when intermediates blow up (cycles,
self-joins, skew), binary plans still win on plain acyclic joins, which is why
nobody replaced hash joins outright. "Free Join" (SIGMOD 2023) unifies both
paradigms under one plan space.

## Interview angle

- "Why can't the optimizer just pick a better order?" -- On cyclic queries
  *every* binary order pays `Theta(m^(k-1))` on adversarial instances; the
  problem is the pairwise model, not the ordering.
- "When would you turn WCOJ off?" -- Acyclic queries with good estimates:
  hash joins pipeline and vectorize better, trie construction is pure
  overhead.
- "AGM of a 4-clique over equal relations of size m?" -- `m^2`, versus up to
  `m^3` of intermediates for a left-deep plan.

## References

1. Atserias, Grohe, Marx - Size Bounds and Query Plans for Relational Joins (TODS 2013): <https://doi.org/10.1145/2428736.2428738>
2. Ngo, Porat, Re, Rudolph - Worst-case Optimal Join Algorithms (JACM 2018, journal version of PODS 2012): <https://doi.org/10.1145/3180143>
3. Veldhuizen - Leapfrog Triejoin: a worst-case optimal join algorithm: <https://arxiv.org/abs/1210.0481>
4. Freitag et al. - Adopting Worst-Case Optimal Joins in Relational Database Systems (PVLDB 2020, Umbra): <https://www.vldb.org/pvldb/vol13/p1891-freitag.pdf>
5. Wang, Willsey, Suciu - Free Join: Unifying Worst-Case Optimal and Traditional Joins (SIGMOD 2023): <https://arxiv.org/abs/2301.10841>
