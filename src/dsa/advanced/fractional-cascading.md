# Fractional Cascading: One Binary Search, Many Lists

Binary search answers one question about one list for O(log n) comparisons, and everyone
pays that happily — once. Plenty of systems then pay it again, and again, for the same
key: the layers of a range tree each hold a sorted list and a rectangle query touches one
list per layer, a router matches one header field against many sorted range lists, an
LSM read consults several sorted runs. The query value is identical, the lists differ,
and k independent binary searches multiply the one cost nobody wants multiplied.

Fractional cascading, the two-part Algorithmica study Chazelle and Guibas published in
1986, removes the multiplication: one binary search, then a constant number of
comparisons per list — O(log n + k) total, on O(n) space. The
[searching chapter](../chapters/ch65-searching-expanded.md) states the bound as an
overview; this page builds the machinery underneath it. The core move sounds reckless:
store only half the cross-references a naive design would want, and prove the loss never
costs more than one comparison per level. Worth having open beside this page:
[SMAWK](smawk.md) eliminates the per-row search outright on totally monotone matrices,
and the [PRAM model](pram-computational-model.md) prices searching vs pointer-chasing
in parallel.

## 1. One Key, k Sorted Lists

Fix k sorted lists holding n keys in total, and a query value q; the task is the
successor position of q in every list — the first element >= q — because that is what
bracket the trade space. Store the lists separately: O(n) space, but a query runs k
binary searches, O(k log(n/k)) comparisons in the equal-size worst case. Merge everything
into one sorted list and annotate each of its n items with k positions — where q's
successor would sit in each source list: the query becomes one binary search plus k table
reads, O(log n + k), but every item now carries k numbers, O(kn) space. The annotation is
precisely the expensive half, and it is what a range tree with a sorted list per node
cannot afford to pay per level.

Fractional cascading keeps the merged design's query shape and the separate design's
space. The enabling observation: a pointer held only sparsely is as good as a pointer to
every level — its target drifts at most one position per hop, and one comparison per hop
detects and repairs the drift.

## 2. Bridges: Every Second Element Climbs One Level

Build catalogs bottom-up. The bottom catalog is the bottom list itself; each catalog one
level up merges its own list with every second element of the catalog below, and every
item stores two numbers: `pL`, the successor position of its value in its own list, and
`down`, the successor position of its value in the catalog below. Elements copied up from
below — bridge copies, starred in the diagrams — point at their own twins; native list
elements point at the first catalog element at or above their value. A +inf sentinel
ends every catalog, so "q is past everything" cascades without special cases.

```text
     M1 :  ...   47     58     58*    76     77*    |s|
           pL     3      4      4      5      6      6
           down   4      4      4      6      6      9
                  |      |      |             |
                  v      v      v             v
     M2 :  ...   44  58  63     77     90    |s|
                 3   4   5      6      7     8     <- M2 indices

     lands on its own twin. The sentinel's down entry points past
```

Why is one comparison per hop enough? Sampled elements sit exactly two positions apart,
so from any landing slot c in the catalog below, the last sampled element below c sits at
index c-1 or c-2. That element also lives in the current catalog as a bridge copy, and it
must be smaller than q — otherwise the binary search would have landed on it instead.
So q's true successor below starts at index c-1 or c (the item at c already satisfies
value >= q), which leaves exactly
two candidates: c-1 and c; one comparison settles which, and the correction is exact.

## 3. Linear Space from a Geometric Tail

The sampling is what keeps the structure small. Catalog i holds all of its own list plus
half the catalog below it, a quarter of the one below that, an eighth of the next:
|M_i| <= |L_i| + |L_{i+1}|/2 + |L_{i+2}|/4 + ... . Summing over all levels and regrouping
by source list, each L_j contributes |L_j| x (1 + 1/2 + 1/4 + ...) = 2|L_j|, so the whole
cascade stores at most 2n items. The demo's three lists hold 21 keys; its three catalogs
hold 8 + 10 + 12 real items plus three sentinels, comfortably inside the bound. Copy
every element instead of every second one and the identical sum degenerates toward the
merged design's O(kn) — the term that kills it. The "fractional" in the name is not
decoration: the fraction is the entire space argument, thinning below 1/d for degree-d
catalog graphs (Section 5).

## 4. The Walk, Counted in Probes

A query binary-searches the top catalog once, then follows one `down` pointer and spends
one comparison per level. The q = 44 run below drifts twice; the comparison catches it.

```python
INF = float("inf")

def bsearch_pos(vals, q):
    "First index with vals[idx] >= q; 1 probe per loop pass."
    lo, hi, probes = 0, len(vals), 0
    while lo < hi:
        mid = (lo + hi) // 2
        probes += 1
        if vals[mid] < q: lo = mid + 1
        else: hi = mid
    return lo, probes

L = [
    [10, 21, 37, 42, 58, 71, 89],     # level 0 (top)
    [15, 21, 33, 47, 58, 76],         # level 1
    [8, 21, 29, 44, 58, 63, 77, 90],  # level 2 (bottom)
]
M = [None] * 3
M[2] = [(v, bsearch_pos(L[2], v)[0], -1, False) for v in L[2]]
M[2].append((INF, len(L[2]), -1, False))
for i in (1, 0):
    below = M[i + 1]
    sampled = [below[t] for t in range(0, len(below) - 1, 2)]
    entries = sorted([(v, False) for v in L[i]] + [(s[0], True) for s in sampled])
    bvals = [it[0] for it in below]
    M[i] = [(v, bsearch_pos(L[i], v)[0], bsearch_pos(bvals, v)[0], br)
            for (v, br) in entries]
    M[i].append((INF, len(L[i]), len(below), False))

def fmt(v): return "s" if v == INF else str(v)
def rep(i, pL):
    return "past end" if pL == len(L[i]) else "%s @ %d" % (fmt(L[i][pL]), pL)

print("catalogs (every second real item of the row below seeds the row above;")
print("* = bridge copy, s = +inf sentinel; each item stores pL and down):")
for i in (2, 1, 0):
    print("  M%d : %s" % (i, " ".join(fmt(it[0]) + ("*" if it[3] else "") for it in M[i])))
print()

def cascade(q):
    "One binary search at the top, then one pointer + one comparison per level."
    j, probes = bsearch_pos([it[0] for it in M[0]], q)
    answers, arrive = [], j
    for i in range(3):
        v, pL, down, _ = M[i][arrive]
        answers.append(pL)
        where = ("binsearch M0 -> idx %d = %s (%d probes)" % (arrive, fmt(v), probes)
                 if i == 0 else "hop to M%d idx %d" % (i, arrive))
        print("  %s;  L%d: first >= %d is %s" % (where, i, q, rep(i, pL)))
        if i == 2: break
        c, verdict = down, "stay"
        if down > 0:
            probes += 1
            if M[i + 1][down - 1][0] >= q:
                c, verdict = down - 1, "drift"
        print("    down=%d, cmp M%d[%d] = %s vs %d -> %s"
              % (down, i + 1, down - 1, fmt(M[i + 1][down - 1][0]), q, verdict))
        arrive = c
    return answers, probes

rows, naive_total, fc_total = [], 0, 0
for q in [21, 44, 92]:
    print("q = %d" % q)
    ans, fc = cascade(q)
    nav = 0
    for i in range(3):
        p, npr = bsearch_pos(L[i], q)
        nav += npr
        assert p == ans[i], (q, i, p, ans[i])
    rows.append((q, nav, fc)); naive_total += nav; fc_total += fc
    print()

print("probe counts (mid-element comparisons over the same 3 queries):")
print("     q   naive  cascading")
for q, nav, fc in rows:
    print("  %4d  %6d  %9d" % (q, nav, fc))
print("  total  %6d  %9d" % (naive_total, fc_total))
print("all answers agree with 3 independent binary searches")
```

Real output (Python 3.12):

```text
catalogs (every second real item of the row below seeds the row above;
* = bridge copy, s = +inf sentinel; each item stores pL and down):
  M2 : 8 21 29 44 58 63 77 90 s
  M1 : 8* 15 21 29* 33 47 58 58* 76 77* s
  M0 : 8* 10 21 21* 33* 37 42 58 58* 71 76* 89 s

q = 21
  binsearch M0 -> idx 2 = 21 (4 probes);  L0: first >= 21 is 21 @ 1
    down=2, cmp M1[1] = 15 vs 21 -> stay
  hop to M1 idx 2;  L1: first >= 21 is 21 @ 1
    down=1, cmp M2[0] = 8 vs 21 -> stay
  hop to M2 idx 1;  L2: first >= 21 is 21 @ 1

q = 44
  binsearch M0 -> idx 7 = 58 (4 probes);  L0: first >= 44 is 58 @ 4
    down=6, cmp M1[5] = 47 vs 44 -> drift
  hop to M1 idx 5;  L1: first >= 44 is 47 @ 3
    down=4, cmp M2[3] = 44 vs 44 -> drift
  hop to M2 idx 3;  L2: first >= 44 is 44 @ 3

q = 92
  binsearch M0 -> idx 12 = s (4 probes);  L0: first >= 92 is past end
    down=11, cmp M1[10] = s vs 92 -> drift
  hop to M1 idx 10;  L1: first >= 92 is past end
    down=9, cmp M2[8] = s vs 92 -> drift
  hop to M2 idx 8;  L2: first >= 92 is past end

probe counts (mid-element comparisons over the same 3 queries):
     q   naive  cascading
    21      10          6
    44       9          6
    92       8          6
  total      27         18
all answers agree with 3 independent binary searches
```

At k = 3 the win is a third of the probes; the asymptotics matter more. Each extra list
adds a full O(log(n/k)) to the naive query but one comparison to the cascade, so the gap
grows linearly in k — and the top search runs over M_0, barely larger than the biggest
input list.

## 5. Bounds and Trade-offs

| Strategy | Space | Query: successor of one q in all k lists | Preprocess |
| --- | --- | --- | --- |
| k independent binary searches | O(n) | O(k log(n/k)) | sort each list |
| full merge, k positions per item | O(kn) | O(log n + k) | k-way merge + annotate |
| fractional cascading | O(n), <= 2n items | O(log n + k) | k bottom-up half-merges |

The general form replaces the path of lists with a **catalog graph**: every vertex holds
a sorted list, a query walks a path in the graph, and each vertex augments its list with
a fraction below 1/d of each out-neighbor's catalog, d the degree bound. Hops cost a
constant number of comparisons, a path of length k answers in O(log n + k), and space
stays linear — point-location structures run exactly this with the catalog graph being
the subdivision's search tree. The dynamic variant is the hard half, developed later:
balanced trees, a gradual B-tree-like fraction rule, and order-maintenance labels buy
O(log n) updates and O(log n + k log log n) queries, with discrepancy-sensitive
refinements due to Atallah, Blanton, Goodrich, and Polu [5].

## 6. Where It Pays Off

Computational geometry is the native habitat. Layered range trees attach a sorted list to
every node and a rectangle query visits one list per layer; bridging adjacent layers turns
O(log^2 n + k) queries into O(log n + k), the optimization the
[geometry chapter](../chapters/ch161-adv-geometry.md) records in its range-tree table.
Edelsbrunner, Guibas, and Stolfi's point-location structure for monotone subdivisions
binary-searches a family of left-to-right polygonal paths where each test is itself a
binary search among path vertices; cascading the inner searches brings queries to
O(log n) on O(n) space [3]. Half-plane range reporting over nested convex layers reaches
O(log n + h) for h reported points.

The idea also left geometry: Lakshman and Stiliadis's policy-based packet forwarding
searches one header field across many sorted range lists via the same cascaded search —
the niche was routers, not maps [4]. Limits are real: Chazelle and Liu show the trick
does not lift to higher-dimensional intersection searching unchanged [6], and dynamic
bounds carry heavy constants — part of why LSM engines facing the same k-sorted-runs
lookup reach for bloom filters and heap-ordered merges, as the packed-index discussion
in [Advanced Indexing](../../dbms/advanced/index-advanced.md) notes. Static or
batch-rebuilt workloads get the full O(log n + k).

## 7. Interview Q&A

**Q: Why not just build the fully merged, fully annotated structure and eat the space?**
Because the annotation is per item per level: a path of k lists costs k numbers per
merged item, O(kn), and branching catalog graphs multiply that per branch. Fractional
cascading caps the cascade at 2n items regardless of k. The full merge remains right
when k is tiny and fixed; for k = 2 it is the same structure with fatter entries.

**Q: What actually breaks if you copy every third element instead of every second?**
With a 1/r sample, up to r-1 unsampled elements can hide between the pointer's landing
place and the truth, so each hop costs up to r-1 comparisons and the query becomes
O(log n + kr) — fine on a plain path. The constraint bites in catalog graphs: a vertex
of degree d must sample below a 1/d fraction for linear space, and per-hop cost grows as
the fraction thins; branching structures trade comparisons per hop for total size.

**Q: Sketch why the one-comparison correction is always safe.**
Landing at slot c, the last sampled element below c sits at index c-1 or c-2 (samples are
two apart). It also lives in the current catalog as a bridge copy, and it must be smaller
than q, or the search above would have landed on it. So q's true successor below starts
after index c-2 and at most at c: exactly two candidates, and one comparison decides.
The corrected position is exact, so nothing compounds.

## 8. References

1. B. Chazelle, L. J. Guibas. *Fractional Cascading: I. A Data Structuring Technique.* Algorithmica 1(1-4):133-162, 1986. [doi:10.1007/BF01840440](https://doi.org/10.1007/BF01840440)
2. B. Chazelle, L. J. Guibas. *Fractional Cascading: II. Applications.* Algorithmica 1(1-4):163-191, 1986. [doi:10.1007/BF01840441](https://doi.org/10.1007/BF01840441)
3. H. Edelsbrunner, L. J. Guibas, J. Stolfi. *Optimal Point Location in a Monotone Subdivision.* SIAM Journal on Computing 15(2):317-340, 1986. [doi:10.1137/0215023](https://doi.org/10.1137/0215023)
4. T. V. Lakshman, D. Stiliadis. *High-Speed Policy-Based Packet Forwarding Using Efficient Multi-Dimensional Range Matching.* ACM SIGCOMM '98, 203-214, 1998. [doi:10.1145/285237.285283](https://doi.org/10.1145/285237.285283)
5. M. J. Atallah, M. Blanton, M. T. Goodrich, S. Polu. *Discrepancy-Sensitive Dynamic Fractional Cascading, Dominated Maxima Searching, and 2-d Nearest Neighbors in Any Minkowski Metric.* WADS 2007, LNCS 4619, 114-126. [doi:10.1007/978-3-540-73951-7_11](https://doi.org/10.1007/978-3-540-73951-7_11)
6. B. Chazelle, F. Liu. *Lower Bounds for Intersection Searching and Fractional Cascading in Higher Dimensions.* Journal of Computer and System Sciences 68(2):269-284, 2004. [doi:10.1016/j.jcss.2003.07.003](https://doi.org/10.1016/j.jcss.2003.07.003)
7. G. S. Lueker. *A Data Structure for Orthogonal Range Queries.* 19th Annual Symposium on Foundations of Computer Science (FOCS 1978), IEEE. [doi:10.1109/SFCS.1978.1](https://doi.org/10.1109/SFCS.1978.1)