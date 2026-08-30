# K Shortest Paths: Ranking the Deviations from Optimal

Dijkstra returns one route and stops. Many systems need the ranked menu instead of the
argmin: the candidate detours a failover controller keeps warm, the alternatives a transit
app shows before the rider rejects the first itinerary, the near-optimal alignments a
pipeline re-scores with side information. Eppstein opens his paper on exactly this
motivation — compute several short paths, then let criteria the graph never knew about pick
among them.

The runner-up usually shares most of its edges with the winner, so deleting the best path
and re-running Dijkstra destroys the routes you want. Every method below is built on the
deviation primitive: keep a prefix of a known-good path, block the one edge it took next,
recompute the suffix. Yen organizes deviations into a ranking loop for loopless paths;
Eppstein compiles them into one implicit structure that emits paths in constant amortized
time each. The flow view of the disjoint-pair variant lives in
[Network Flow Algorithms](network-flow.md), the DP problems Eppstein lists as applications
are the layered view of [DP Optimization Techniques](dp-optimization.md), and
[Parallel Graph Algorithms](parallel-graph-algorithms.md) shows the parallelize-the-inner-
loop pattern that fits Yen's independent spur Dijkstras within a round.

## 1. The Ranking Problem and Its Variants

**Statement.** Given a digraph with edge lengths, a source `s`, a target `t`, and an integer
`k`, list `k` `s-t` paths in nondecreasing total length. The variants differ in what "path"
allows, and the split drives everything else: a walk may repeat vertices, a loopless path
may not. With nonnegative lengths the cheapest walk is automatically simple — excising a
cycle never increases cost — so `k = 1` collapses the two; `k > 1` does not, since a walk
can pay for a cycle excursion and still rank second.

With negative lengths the walk ranking degenerates outright: lapping a negative cycle lowers
cost without bound, so "k best walks" has no answer. Loopless ranking stays finite even
then; everything below assumes nonnegative lengths.

## 2. Yen's Spur Mechanism

Yen keeps `A`, the accepted paths in cost order, plus a pool of candidates. To extract path
`i + 1`, scan each vertex of the last accepted path `P` as a spur node: take the prefix up
to it as the root, cut the edge every accepted path sharing that root takes out of the spur
node, ban the root's earlier vertices, and run Dijkstra from the spur node to `t`; the
cheapest tail glued to the root is one candidate. The pool minimum joins `A`, and `k - 1`
rounds rank the rest. The completeness invariant: any loopless path `Q` not yet accepted
shares a longest prefix with some accepted path up to a vertex `v`, leaves `v` by an edge no
accepted path sharing that prefix uses, and its suffix is legal under the same bans — so
the pool always holds a candidate at least as cheap as `Q`, and deviation enumeration is
exact, not heuristic. Each round costs at most `n - 1` spur Dijkstras of `O(m + n log n)`,
hence the standard directed bound `O(k n (m + n log n))`.

```text
P1 = A-B-D-E-F-G-H (cost 17 = 1+2+5+2+2+1+2), spur node E at index 3

     A --1--> B --2--> D --5--> E ==2==> F --2--> G --1--> H    P1
                               |
                             cut E->F      tail: Dijkstra from E to H
                               |           in G minus edge (E,F), with
                               v           root vertices {A,B,D} banned
                          tail = E-G-H (cost 8 + 4 = 12)

     candidate = root + tail = A-B-D-E-G-H, cost 8 + 12 = 20  -> path #2
```

Lawler's 1972 k-best framework sharpens the loop: a candidate that first deviates from its
parent at position `j` only produces differing descendants at positions `>= j`, so each
branch rescans just its own suffix; Martins and Pascoal's 2003 implementation builds on
that refinement, reusing computed quantities across rounds.

## 3. Eppstein: Sidetracks and Constant Time per Path

Eppstein fixes the target `t`, builds the shortest-path tree `T` toward it, and calls every
edge outside `T` a sidetrack. Sidetrack `(u, v)` has nonnegative excess
`delta(u, v) = w(u, v) + d(v, t) - d(u, t)`, the cost of leaving the tree at `u`. Every
`s-t` walk is the tree walk with sidetracks spliced in, and its length is `d(s, t)` plus the
deltas used — so ranking walks is ranking sidetrack sequences by total delta.

```text
d(v) = cheapest v->t cost; T = each vertex's cheapest hop toward t
    s --2--> a --3--> b --1--> c --3--> t   d(s)=9  d(a)=7  d(b)=4  d(c)=3  d(t)=0

sidetracks (edges outside T), delta(u,v) = w(u,v) + d(v) - d(u):

    a -> c  w=5 : delta = 5 + 3 - 7 = 1     b -> t  w=6 : delta = 6 + 0 - 4 = 2

any s-t walk = tree walk with sidetracks spliced in; cost = d(s,t) + sum of deltas:

    no sidetrack      s-a-b-c-t    9 + 0 = 9    (the tree path itself)
    sidetrack a->c    s-a-c-t      9 + 1 = 10
    sidetrack b->t    s-a-b-t      9 + 2 = 11
```

The structure makes those sequences enumerable in sorted order without materializing them.
Per vertex `v`, `H_out(v)` heaps the sidetracks leaving `v` by delta; `H_T(v)` persistently
merges `H_out(v)` with the `H_T` of `v`'s tree children, so the whole tree of heaps costs
`O(log n)` new nodes per tree edge rather than one heap per vertex. Paths then form a
heap-ordered DAG `D(G)` with `O(m + n log n)` vertices and out-degree at most 4; Frederickson's
k-smallest algorithm on heap-ordered trees pops the answers in constant time per path. From
the paper: the basic construction is `O(m + n log n + k log k)`, refined to
`O(m + n log n + k)` implicit, and `O(m + n + k)` when a shortest-path tree comes free.

The output is implicit — a path's length is available in constant time, and writing its
edges costs time proportional to its length, the fine print separating this from Yen's
per-path enumerations. A source-to-every-vertex variant costs `O(m + n log n + kn)`; the
paper's applications are all DP-shaped: knapsack, sequence alignment, genealogy.

## 4. Bounds at a Glance, and the Disjoint-Pair Variant

| Algorithm | Enumerates | Loop structure | Cost |
| --- | --- | --- | --- |
| Dijkstra (heap) | single cheapest path | one pass | `O(m + n log n)` |
| Yen 1971 | k cheapest loopless paths | `k-1` rounds x `<= n-1` spur Dijkstras | `O(k n (m + n log n))` |
| Eppstein 1998 | k cheapest walks | preprocess once, then output | `O(m + n log n + k)` implicit |
| Suurballe 1974 / Suurballe-Tarjan 1984 | cheapest disjoint pair | two Dijkstra passes, transformed costs | iterates for R disjoint paths |

The disjoint-pair problem asks for two edge- or vertex-disjoint `s-t` paths minimizing total
length — the ranked menu compressed to its two load-bearing entries, which is why failover
analysis keeps returning to it. Suurballe runs Dijkstra once, applies Johnson-style reduced
costs `w'(u,v) = w(u,v) + d(u) - d(v) >= 0` — nonnegative because `d(v) <= d(u) + w(u,v)` —
runs Dijkstra again with the first path's edges reversed at zero cost, and cancels edges the
passes traverse in opposite directions; Suurballe and Tarjan's 1984 paper sharpens the
method. The transform shifts every `s-t` path by the constant `-d(t)`; the whole computation is
min-cost flow of value 2 under unit vertex capacities — the same machinery as
[Min-Cost Max-Flow](../chapters/ch169-min-cost-max-flow.md).

## 5. Worked Demo: Yen on a Fixed Digraph

The script ranks `k = 4` loopless paths on a fixed 8-node, 13-edge digraph and prints the
deviation scan of the round that selects path #2. Deterministic: fixed edge list, value-
sorted heap, lexicographic tie-breaks.

```python
import heapq

# Fixed 8-node weighted digraph: (u, v, cost)
EDGES = [
    ("A", "B", 1), ("A", "C", 4), ("B", "C", 5), ("B", "D", 2),
    ("C", "D", 12), ("C", "E", 10), ("D", "E", 5), ("D", "F", 11),
    ("E", "F", 2), ("E", "G", 8), ("F", "G", 3), ("F", "H", 14),
    ("G", "H", 4),
]
W = {(u, v): w for u, v, w in EDGES}
ADJ = {}
for u, v, w in EDGES:
    ADJ.setdefault(u, []).append((v, w))
SRC, DST, K = "A", "H", 4

def dijkstra(spur, banned_v, banned_e):
    "Cheapest spur->DST path skipping banned vertices and (u, v) edges."
    dist, pred, pq = {spur: 0}, {}, [(0, spur)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == DST:
            break
        for v, w in ADJ.get(u, []):
            if v in banned_v or (u, v) in banned_e:
                continue
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v], pred[v] = nd, u
                heapq.heappush(pq, (nd, v))
    if DST not in dist:
        return None
    walk = [DST]
    while walk[-1] != spur:
        walk.append(pred[walk[-1]])
    return tuple(walk[::-1])

def cost(p):
    return sum(W[u, v] for u, v in zip(p, p[1:]))

fmt = "-".join
A = [dijkstra(SRC, set(), set())]    # accepted paths, in nondecreasing cost
pool, seen, rows, second = [], set(), [], None
for _ in range(K - 1):
    P, scanning = A[-1], len(A) == 1
    for i in range(len(P) - 1):      # spur nodes: every vertex of P but DST
        spur, root = P[i], P[: i + 1]
        cut = tuple(sorted((Q[i], Q[i + 1]) for Q in A if Q[: i + 1] == root))
        tail = dijkstra(spur, set(root[:-1]), set(cut))
        label = "cut " + " ".join("%s->%s" % e for e in cut)
        cand = None if tail is None else root[:-1] + tail
        c = cost(cand) if cand else None
        if scanning:
            rows.append((spur, label, cand, c))
        if cand and (c, cand) not in seen:
            seen.add((c, cand))
            pool.append((c, cand))
    pool.sort()
    c, cand = pool.pop(0)
    A.append(cand)
    if len(A) == 2:
        second = (c, cand)

print("Yen's algorithm: k = 4 shortest loopless paths, A -> H")
for r, p in enumerate(A, 1):
    print("  #%d cost %2d: %s" % (r, cost(p), fmt(p)))
print()
print("deviation scan of round 1 (the round that selects path #2):")
for spur, label, cand, c in rows:
    if cand is None:
        print("  spur %s  %-10s dead end" % (spur, label))
    else:
        print("  spur %s  %-10s cand %-14s cost %2d%s"
              % (spur, label, fmt(cand), c,
                 "   <== minimum" if (c, cand) == second else ""))
```

Real output (Python 3.12):

```text
Yen's algorithm: k = 4 shortest loopless paths, A -> H
  #1 cost 17: A-B-D-E-F-G-H
  #2 cost 20: A-B-D-E-G-H
  #3 cost 21: A-B-D-F-G-H
  #4 cost 23: A-C-E-F-G-H

deviation scan of round 1 (the round that selects path #2):
  spur A  cut A->B   cand A-C-E-F-G-H    cost 23
  spur B  cut B->D   cand A-B-C-E-F-G-H  cost 25
  spur D  cut D->E   cand A-B-D-F-G-H    cost 21
  spur E  cut E->F   cand A-B-D-E-G-H    cost 20   <== minimum
  spur F  cut F->G   cand A-B-D-E-F-H    cost 24
  spur G  cut G->H   dead end
```

One scan of six spur nodes produced deviations at three depths: #2 leaves `P1` at `E` with
four edges shared, #3 at `D`, #4 at the very first edge. Brute force enumerates 21 loopless
`s-t` paths here and agrees with the ranking; rounds 2 and 3 added nothing new — every
deviation off the accepted paths was already pooled, which is the pool doing its job:
candidates persist across rounds, so a repeated scan contributes only what is new.

## 6. Interview Q&A

**Q: Why not delete the best path's edges and run Dijkstra again for the second-best?**
Because the true runner-up reuses most of those edges — in the demo, #2 shares four of its
six edges with #1, and #4 differs from #1 only at the first hop. Deleting the whole path
over-constrains the search and can return a far worse route or none at all; Yen removes one
edge per spur and keeps the shared prefix, which is why the pool stays tight around the
optimum.

**Q: You must show 10 alternatives per user query on a 2M-edge road graph. Yen or Eppstein?**
If queries repeat against one destination, build Eppstein's structure once in
`O(m + n log n + k)` and answer in constant amortized time per path; Yen would redo
`O(k n (m + n log n))` work per query. Catches: Eppstein's output is walks, so human-facing
routes need the loopless variant, and the implicit output pays per edge on display.

**Q: Where exactly does the loopless assumption earn its keep?**
With nonnegative lengths, walk ranking is well-defined but admits cycle excursions — a
"route" that laps a junction — useless for display and unbounded in count with zero-cost
cycles. Negative cycles make walk ranking meaningless outright, while loopless ranking stays
finite but inherits Dijkstra's nonnegativity requirement inside every spur call.

**Q: How does Suurballe's pair relate to min-cost flow, and why do reduced costs work?**
A disjoint pair is two units of flow with unit vertex capacities, so min-cost flow solves
it; Suurballe specializes the successive-shortest-path view, each Dijkstra finding the next
augmenting path. The transform `w'(u,v) = w(u,v) + d(u) - d(v)` is nonnegative by the
shortest-distance inequality and shifts every `s-t` path by the same constant; cancelling
opposing edges turns the union of two walks into two genuinely disjoint paths at the same
total cost.

## 7. References

1. J. Y. Yen. *Finding the K Shortest Loopless Paths in a Network.* Management Science
   17(11):712-716, 1971. [doi:10.1287/mnsc.17.11.712](https://doi.org/10.1287/mnsc.17.11.712)
2. E. L. Lawler. *A Procedure for Computing the K Best Solutions to Discrete Optimization Problems and Its Application to the Shortest Path Problem.* Management Science 18(7):401-405, 1972. [doi:10.1287/mnsc.18.7.401](https://doi.org/10.1287/mnsc.18.7.401)
3. D. Eppstein. *Finding the k Shortest Paths.* Proceedings 35th FOCS, 154-165, 1994.
   [doi:10.1109/SFCS.1994.365697](https://doi.org/10.1109/SFCS.1994.365697)
4. D. Eppstein. *Finding the k Shortest Paths.* SIAM Journal on Computing 28(2):652-673,
   1998. [doi:10.1137/S0097539795290477](https://doi.org/10.1137/S0097539795290477)
5. J. W. Suurballe. *Disjoint Paths in a Network.* Networks 4(2):125-145, 1974.
   [doi:10.1002/net.3230040204](https://doi.org/10.1002/net.3230040204)
6. J. W. Suurballe, R. E. Tarjan. *A Quick Method for Finding Shortest Pairs of Disjoint
   Paths.* Networks 14(2):325-336, 1984.
   [doi:10.1002/net.3230140209](https://doi.org/10.1002/net.3230140209)
7. E. Q. V. Martins, M. M. B. Pascoal. *A New Implementation of Yen's Ranking Loopless Paths Algorithm.* 4OR 1(2), 2003. [doi:10.1007/s10288-002-0010-2](https://doi.org/10.1007/s10288-002-0010-2)
8. E. Q. V. Martins, M. M. B. Pascoal, J. L. E. Santos. *Deviation Algorithms for Ranking
   Shortest Paths.* International Journal of Foundations of Computer Science 10(3):247-261,
   1999. [doi:10.1142/S0129054199000186](https://doi.org/10.1142/S0129054199000186)
