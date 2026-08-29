# Planar Separator Theorems: Divide and Conquer on Planar Graphs

On a general graph, divide-and-conquer stalls at the first split: cutting an n-vertex graph into two comparable halves can cost Theta(n) vertices, and the recurrence T(n) = 2T(n/2) + Theta(n) spends its whole budget on the cuts. Planar graphs are different. Euler's formula caps m <= 3n - 6, which rules out expanders, and the 1979 theorem of Lipton and Tarjan converts that into an algorithmic lever: every planar graph splits into three pieces A, B, C with no edge between A and B, each of A and B holding at most 2n/3 vertices, and |C| <= 2 sqrt(2n) ~ 2.83 sqrt(n). This page works through the statement and its weighted form, the BFS-level proof shape, the grid graphs that make the bound tight, Frederickson's r-divisions, and the two headline applications: exact shortest paths and PTASs. For the survey-level summary already in this book, see [Advanced Graph Theory](ch155-advanced-graph-theory.md) (section 155.2); this page goes deeper and adds a runnable separator check.

## 1. The theorem in its two working forms

**Theorem (Lipton-Tarjan 1979).** The vertices of any n-vertex planar graph can be partitioned into three sets A, B, C such that no edge joins A to B, neither A nor B contains more than 2n/3 vertices, and C contains at most 2 sqrt(2n) vertices. An O(n)-time algorithm finds such a partition. (Bound and running time are taken verbatim from the paper's abstract.)

| Form | Guarantee | Typical use |
|---|---|---|
| Vertex separator | separator C with <= 2 sqrt(2n) vertices; sides <= 2n/3 | divide-and-conquer |
| Weighted separator | same size bound; each side holds <= 2W/3 of any nonnegative vertex weights W | r-divisions, Baker's scheme |
| H-minor-free graphs | separator of <= c(H) sqrt(n) vertices for fixed excluded minor H | nonplanar generalization |
| Grid lower bound | balanced separator of the h x h grid needs Omega(h) = Omega(sqrt(n)) vertices | shows tightness |

Two reading notes. First, the 2n/3 balance is the standard choice because T(n) = T(a n) + T(b n) + O(sqrt(n)) with a, b <= 2/3 solves to O(n): the separators on one root-to-leaf path of the recursion form the series sqrt(n) (1 + 2^(-1/2) + 2^(-1) + ...) which converges, so cutting costs O(sqrt(n)) per algorithm. Any fixed balance alpha < 1 works with worse constants. Second, "small separator" does not mean "optimal cut": the theorem guarantees a cut of the right size in linear time, while finding the smallest balanced separator is NP-hard (it generalizes minimum bisection).

## 2. Why planarity forces a sqrt(n) separator

Planar graphs "grow in area, not volume". In the h x h grid (n = h^2), BFS from a corner has level k equal to the anti-diagonal i + j = k: the frontier expands in one dimension while the explored region expands in two. Deleting one middle level removes only h = sqrt(n) vertices yet splits the grid cleanly. An expander forbids exactly this: in a good expander every small set has an outsized boundary, which the grid refuses to provide.

```text
BFS from the top-left corner of an 8 x 8 grid; the cell shows d(s, v) = i + j:

  0  1  2  3  4  5  6  7
  1  2  3  4  5  6  7  8
  2  3  4  5  6  7  8  9
  3  4  5  6  7  8  9 10
  4  5  6  7  8  9 10 11
  5  6  7  8  9 10 11 12
  6  7  8  9 10 11 12 13
  7  8  9 10 11 12 13 14

Level k = anti-diagonal i + j = k; sizes go 1, 2, ..., 8, 7, ..., 1. Deleting
one diagonal leaves the shallow levels and the deep levels with zero edges
between them: any edge changes d(s, .) by at most 1.
```

The grid is the worst case, not an artifact: Lipton and Tarjan note that grids make the sqrt(n) bound best possible. Sketch of why Omega(h) is unavoidable: the grid contains h vertex-disjoint rows and h vertex-disjoint columns, so by Menger's theorem any left-to-right or top-to-bottom cut costs at least h vertices, and a diagonal cut has to sweep past the fat middle levels, which hold Theta(h) vertices. Section 4 makes the diagonal case concrete and measurable.

## 3. Proof sketch: BFS levels and the Jordan-curve argument

1. BFS from any root r gives levels L_0..L_D. Invariant: every edge joins the same or adjacent levels, so removing one level always separates shallower levels from deeper ones.
2. If some level L_k has |L_k| <= sqrt(2n) and at most 2n/3 vertices on each side of it, then C = L_k is the separator. Done.
3. Otherwise every cheap level is badly placed; juggling level groups (weight = size) shows the levels alone cannot finish, and the BFS tree must have two long arms of small level-weight.
4. Find a non-tree edge (u, v) whose endpoints sit at compatible radii on two arms of the BFS tree. The tree paths r..u and r..v plus the edge (u, v) form a fundamental cycle C. Because G is planar, C is a Jordan curve in the embedding: every other vertex is strictly inside or strictly outside.
5. Choose (u, v) so that C has at most sqrt(2n) vertices and at most 2n/3 on each side. Then C is the separator. The weighted version runs the same argument on level weights instead of counts.

```text
          r
        /   \            tree paths (BFS arms)
      P1     P2
      /       \
     u --(u,v)-- v       one non-tree edge closes the cycle

 C = P1 + (u,v) + reversed(P2). In the plane embedding C is a Jordan curve:

     ( outside: <= 2n/3 vertices )
     +-----------------------+
     |          C            |
     |    ( inside:          |
     |      <= 2n/3 )        |
     +-----------------------+

 |C| <= 2 sqrt(2n)  =>  C is a valid separator.
```

What breaks on nonplanar graphs: a cycle in a general graph separates nothing, since edges can pass "through" it, so step 5 collapses. The idea survives for any fixed excluded minor -- that is the Alon-Seymour-Thomas theorem, O(sqrt(n)) separators for H-minor-free graphs -- and it is why the result extends to bounded-genus graphs but not to random 3-regular expanders, whose balanced separators need Theta(n) vertices.

## 4. Runnable check: a BFS-level separator on grids

The demo builds an h x h grid, runs BFS from corner s = (0, 0), and takes the separator to be the first level whose shallow cumulative count crosses n/3. By the adjacent-level invariant no edge joins levels < k to levels > k, so the cut is sound by construction -- and the code re-verifies both soundness facts the slow way: zero shallow-to-deep edges (full edge scan), and BFS from s in G - S failing to reach the opposite corner t = (h-1, h-1), whose BFS tree is the second of the "two corner trees".

```python
# BFS-level separator demo on an h x h grid graph (pure stdlib).
from collections import deque


def grid_graph(h):
    n = h * h
    adj = [[] for _ in range(n)]
    for i in range(h):
        for j in range(h):
            v = i * h + j
            for di, dj in ((1, 0), (0, 1)):
                x, y = i + di, j + dj
                if x < h and y < h:
                    w = x * h + y
                    adj[v].append(w)
                    adj[w].append(v)
    return n, adj


def bfs(adj, src):
    dist = [-1] * len(adj)
    dist[src] = 0
    q = deque([src])
    while q:
        v = q.popleft()
        for w in adj[v]:
            if dist[w] < 0:
                dist[w] = dist[v] + 1
                q.append(w)
    return dist


def level_separator(n, adj, s, t):
    """BFS levels from corner s; first level whose shallow sum crosses n/3."""
    dist = bfs(adj, s)
    levels = [[] for _ in range(max(dist) + 1)]
    for v in range(n):
        levels[dist[v]].append(v)
    k, below = 0, 0
    while below < n / 3.0:
        below += len(levels[k])
        k += 1
    k -= 1  # separator = level k; shallow side = levels < k
    S = set(levels[k])
    A = [v for v in range(n) if dist[v] < k]
    C = [v for v in range(n) if dist[v] > k]
    # check 1: no edge joins the shallow side to the deep side
    bad = sum(1 for v in A for w in adj[v] if dist[w] > k)
    # check 2: G - S really splits s from t (BFS avoiding S)
    seen = bfs([[] if v in S else adj[v] for v in range(n)], s)
    split = seen[t] < 0
    return S, A, C, bad, split


def main():
    print("h     n=hh   |S|  sqrt(n)  |S|/sqrt(n)  |S|/(2sqrt(2n))  "
          "max side frac  s-t split  A-C edges")
    for h in (16, 32, 64):
        n, adj = grid_graph(h)
        s, t = 0, h * h - 1  # top-left and bottom-right corners
        S, A, C, bad, split = level_separator(n, adj, s, t)
        r1 = len(S) / (n ** 0.5)
        r2 = len(S) / (2 * (2 * n) ** 0.5)
        frac = max(len(A), len(C)) / n
        print("%-5d %-6d %-4d %-8.1f %-12.3f %-16.3f %-14.4f %-10s %d"
              % (h, n, len(S), n ** 0.5, r1, r2, frac, split, bad))


main()
```

Output (executed; byte-identical across two runs):

```text
h     n=hh   |S|  sqrt(n)  |S|/sqrt(n)  |S|/(2sqrt(2n))  max side frac  s-t split  A-C edges
16    256    13   16.0     0.812        0.287            0.6445         True       0
32    1024   26   32.0     0.812        0.287            0.6572         True       0
64    4096   52   64.0     0.812        0.287            0.6636         True       0
```

Reading the numbers. |S| / sqrt(n) is 0.8125 at every scale because the crossing level sits at k ~ h sqrt(2/3); the ratio converges to sqrt(2/3) ~ 0.8165, and the found separator is ~3.5x smaller than the theorem's worst-case allowance 2 sqrt(2n) (the constant-0.287 column). Balance holds strictly, not just up to O(sqrt(n)) slack: the shallow side has < n/3 vertices by the pre-crossing invariant, the deep side <= 2n/3 by the post-crossing invariant (max side frac creeps toward but stays under 0.6667). The verification columns never budge: zero shallow-to-deep edges and a genuine s-t disconnection after deleting S.

## 5. r-Divisions: separators as a preprocessing primitive

Applying the separator theorem recursively -- stopping when pieces are small, and gluing cut vertices into every piece they touch -- yields a division with controlled boundary. Frederickson (1987) formalized this and used it as a shortest-path engine:

| Parameter | Value | Why it matters |
|---|---|---|
| Number of pieces | O(n/r) | one precomputation per piece |
| Vertices per piece | <= r | piece-local work is cheap |
| Boundary vertices per piece | O(sqrt(r)) | duplicated into every piece they touch |
| Total boundary vertices | O(n/sqrt(r)) | the global "interface" size |

```text
Stop recursing when pieces have ~ r vertices; carry boundary vertices (o)
into every adjacent piece:

 +--------+o+--------+
 | piece  |o| piece  |
 |   A    |o|   B    |
 +--o-----+o+----o---+
    o     boundary   o
 +--o-----+o+----o---+
 | piece  |o| piece  |
 |   C    |o|   D    |
 +--------+o+--------+
```

The two knobs r and sqrt(r) make divide-and-conquer tunable: local work is O(piece size) per piece, and global coordination only ever happens through the O(n/sqrt(r)) boundary vertices. Choosing r ~ log^c(n) or r ~ n^(1/2) turns one lemma into a family of algorithms.

## 6. Application: exact shortest paths faster than Dijkstra

Baseline: planar graphs have m <= 3n - 6, so Dijkstra with a binary heap runs in O(n log n) -- already near-linear, which raises the bar for anything fancier. The verified progress line:

| Method | Time | Notes |
|---|---|---|
| Dijkstra, binary heap | O(n log n) | nonnegative weights |
| Henzinger-Klein-Rao 1994 | O~(n^(4/3)) | best before FR (per FR's own abstract) |
| Fakcharoenphol-Rao 2001 | O(n log^3 n) | real weights, negatives allowed; also improved query and dynamic variants |
| Later refinements | down to O(n log^2 n / log log n) | planar digraph SSSP, per later citing literature |

The Fakcharoenphol-Rao machinery is r-divisions taken to their logical conclusion: precompute, inside each piece, all-pairs distances between its O(sqrt(r)) boundary vertices; the per-piece tables have a monotone (staircase/Monge) structure that lets a Bellman-Ford-style pass over the compressed boundary graph run in near-linear total time instead of running Dijkstra per piece. The same compressed structure answers exact s-t distance queries much faster than rerunning Dijkstra -- an exact distance oracle with O(n)-scale space -- and supports dynamic updates. Be precise about the theorem statement: the 2001 preprocessing bound is O(n log^3 n), not linear time, and the algorithm is exact (it is the approximate-oracle literature that later traded exactness for speed). Shortest paths are where the weighted separator and the boundary story pay off together: pieces exchange information only through the O(n/sqrt(r)) interface counted in Section 5.

## 7. Application: PTASs from shifted BFS layers

Baker (1994, J. ACM 41(1)) turned the level structure into approximation schemes for NP-hard problems (independent set, vertex cover, dominating set, and more) on planar graphs. For maximization problems: fix k, compute BFS layers from any root, and delete every (k+1)-th layer; each remaining component spans at most k consecutive layers, which caps its treewidth at k, so exact DP on a width-k decomposition solves everything in 2^O(k) * n total. Then shift: run this for each offset j = 0..k and keep the best. Every vertex is deleted in exactly one offset, so some offset loses at most a 1/(k+1) fraction of the optimum -- a (1 - 1/(k+1)) approximation in n * 2^O(k) time, i.e. a PTAS as k grows with 1/epsilon.

Separators give the complementary divide-and-conquer flavor: cut O(sqrt(n)) vertices away, solve the O(n)-vertex pieces recursively, and spend extra effort on the boundary -- the shape behind planar PTASs and the bidimensionality pipeline (see [Parameterized Algorithms](ch148-parameterized-algorithms.md)). Planarity does not make these problems easy -- they stay NP-hard -- it makes them approximable at any fixed precision in polynomial time.

## 8. The treewidth connection: planar graphs are Theta(sqrt(n))-wide

Recursively deleting separators and keeping each separator as a bag yields a tree decomposition of width O(sqrt(n)) for any planar graph (the constant depends on the schedule; refinements tighten it). The grid gives the matching lower bound: the h x h grid has treewidth exactly h, and every balanced separator of it costs Omega(h). So planar treewidth is Theta(sqrt(n)) -- the single most reused fact in planar algorithm design. Consequences: any problem solvable in 2^O(w) * n on a width-w decomposition gives 2^O(sqrt(n)) * n^{O(1)} algorithms on planar graphs (Independent Set, Vertex Cover, Dominating Set and friends; the decomposition side is in [Bridge, Trees and Treewidth](ch109-bridge-trees-treewidth.md)). Baker's scheme (Section 7) is the same statement read backwards: delete one layer and what remains genuinely has small treewidth. Spectral tie-in: planar graphs cannot have a large spectral gap, because a thin cut contradicts Cheeger-type inequalities; expanders sit at the other extreme -- see [Spectral Graph Theory](ch154-spectral-graph-theory.md).

## 9. Pitfalls worth rehearsing

| Pitfall | Reality |
|---|---|
| "The separator is O(log n) like a balanced BST" | It is Theta(sqrt(n)); grids force Omega(sqrt(n)) |
| "Any sparse graph has one" | Needs planarity or a fixed excluded minor; expanders need Theta(n) |
| "The theorem finds a small optimal cut" | It guarantees size and balance in O(n) time; optimizing is NP-hard |
| "Planar implies sublinear-time algorithms" | You still touch all n vertices; the win is in recursion depth and preprocessing structure |
| "Planar problems are polynomial" | NP-hardness persists; separators buy PTASs and 2^O(sqrt(n)) FPT, not polytime exactness |

## 10. References

1. R. J. Lipton and R. E. Tarjan, "A Separator Theorem for Planar Graphs," SIAM J. Appl. Math. 36(2):177-189, 1979. https://doi.org/10.1137/0136016 -- Crossref-verified; landing page 403s to curl (SIAM bot-block); abstract cross-checked on OpenAlex, including the O(n)-time construction.
2. R. J. Lipton and R. E. Tarjan, "Applications of a Planar Separator Theorem," SIAM J. Comput. 9(3):615-627, 1980. https://doi.org/10.1137/0209046 -- Crossref-verified; landing page 403s to curl.
3. G. N. Frederickson, "Fast Algorithms for Shortest Paths in Planar Graphs, with Applications," SIAM J. Comput. 16(6):1004-1022, 1987. https://doi.org/10.1137/0216064 -- Crossref-verified; landing page 403s to curl. (The r-division paper is SICOMP, not J. Algorithms.)
4. J. Fakcharoenphol and S. Rao, "Planar graphs, negative weight edges, shortest paths, and near linear time," Proc. 42nd IEEE FOCS, 2001. https://doi.org/10.1109/SFCS.2001.959897 -- Crossref-verified; IEEE landing returns a 202 challenge to curl; abstract verified via Semantic Scholar (O(n log^3 n), real weights, query/dynamic variants).
5. J. Fakcharoenphol and S. Rao, "Planar graphs, negative weight edges, shortest paths, and near linear time," J. Comput. Syst. Sci. 73(5), 2006 (journal version). https://doi.org/10.1016/j.jcss.2005.05.007 -- DOI resolves 200.
6. B. S. Baker, "Approximation algorithms for NP-complete problems on planar graphs," J. ACM 41(1):153-180, 1994. https://doi.org/10.1145/174644.174650 -- Crossref-verified; landing page 403s to curl (ACM bot-block).
7. N. Alon, P. Seymour and R. Thomas, "A separator theorem for nonplanar graphs," J. Amer. Math. Soc. 3(4):801-808, 1990. https://doi.org/10.1090/s0894-0347-1990-1065053-0 -- DOI resolves 200 (ams.org).
