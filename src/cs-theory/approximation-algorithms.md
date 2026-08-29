# Approximation Algorithms

When an optimization problem is NP-hard, exact polynomial algorithms are off the table (see
[Complexity Classes](complexity-classes.md) for the P/NP background -- not re-derived here).
Approximation algorithms are the complexity theorist's answer: run in polynomial time, but attach
a *provable* bound on distance from optimal -- a contract that holds on every input, unlike a
heuristic's benchmark score. This page covers the definitions and scheme hierarchy, the classic
algorithms with their proofs (vertex cover, metric TSP, set cover, load balancing), hardness of
approximation, and the knapsack FPTAS as the canonical rounding construction. C++/Java
implementations and interview drills live in
[Chapter 145: Approximation Algorithms](../dsa/chapters/ch145-approximation-algorithms.md);
[Approximation and FPT](../dsa/advanced/approximation-fpt.md) covers the parameterized side
(kernelization, treewidth).

## 1. Ratio Definitions and the PTAS/FPTAS/APX Hierarchy

A **rho-approximation** for a minimization problem is a polynomial-time algorithm A with, for
every instance I: `ALG(I) <= rho * OPT(I)`, rho >= 1. For maximization the common convention is
`ALG(I) >= rho * OPT(I)` with 0 < rho <= 1 (max cut 0.878); the alternative quotes a factor >= 1
(OPT/ALG = 16/11). Both appear -- say which one you mean; OPT is the true optimum, never an
estimate.

| Scheme | Runtime shape | Dependence on 1/eps | Flagship example |
|---|---|---|---|
| PTAS | poly(n) for fixed eps | arbitrary, e.g. n^(f(1/eps)) | Euclidean TSP (Arora) |
| EPTAS | f(1/eps) * n^c | separated from n | planar-graph variants |
| FPTAS | n^c / eps^d | polynomial in 1/eps | 0/1 knapsack |
| APX | constant factor | none (fixed ratio) | vertex cover (2) |

The containment chain is exact poly = FPTAS subset EPTAS subset PTAS subset APX subset NP-hard
optimization (knapsack additionally has an exact pseudo-polynomial DP, O(nW)). A PTAS reaches
(1+eps) for every eps > 0 but may run in n^(f(1/eps)) -- useless at eps = 0.01; an FPTAS is
polynomial in both n and 1/eps; APX-hard problems (vertex cover, max-3SAT) have no PTAS unless
P = NP. The most useful existence filter: **strongly** NP-hard problems (hard even with
polynomially bounded numbers, via 3-partition) admit neither a pseudo-polynomial DP nor an
FPTAS unless P = NP; weakly NP-hard ones like knapsack can have both.

## 2. Vertex Cover: The Greedy 2-Approximation

Pick a minimum set of vertices touching every edge. Algorithm: scan edges in any order; whenever
an edge has both endpoints uncovered, add *both*. The edges where the algorithm pays share no
endpoints -- they form a maximal matching M. Any cover must include an endpoint of every edge of
M, and those endpoints are disjoint, so OPT >= |M|; the algorithm outputs exactly the 2|M|
endpoints, hence ALG = 2|M| <= 2 OPT -- and the proof locates the tightness: any maximal matching
can be forced to be half of a minimum cover.

```python
# Vertex cover: maximal-matching 2-approx vs exact optimum (seeded, stdlib only).
import random
from itertools import product

def approx_vc(n, edges):
    covered = set()
    for u, v in edges:
        if u not in covered and v not in covered:
            covered |= {u, v}
    return len(covered)

def exact_vc(n, edges):
    masks = [(1 << u) | (1 << v) for u, v in edges]
    for k in range(n + 1):
        for bits in range(1 << n):
            if bin(bits).count("1") == k and all(bits & m for m in masks):
                return k

rng = random.Random(7)
print("G(n,p) random graphs, ratio = approx / OPT:")
print("  n  edges  approx  OPT  ratio")
for n, p in [(10, 0.30), (12, 0.40), (14, 0.30)]:
    edges = [(u, v) for u, v in product(range(n), repeat=2) if u < v and rng.random() < p]
    a, o = approx_vc(n, edges), exact_vc(n, edges)
    print(" {:>3} {:>6} {:>7} {:>4} {:>6.3f}".format(n, len(edges), a, o, a / o))

print("Tight case: k disjoint paths P3 (a-b-c); OPT = 1 per P3, greedy pays 2:")
for k in (1, 3, 5):
    edges = [(3 * i + j, 3 * i + j + 1) for i in range(k) for j in (0, 1)]
    a, o = approx_vc(3 * k, edges), exact_vc(3 * k, edges)
    print("  k={}: approx={}, OPT={}, ratio={:.3f}".format(k, a, o, a / o))
```

Output (real run of the block above):

```text
G(n,p) random graphs, ratio = approx / OPT:
  n  edges  approx  OPT  ratio
  10     18       8    7  1.143
  12     25      10    7  1.429
  14     34      12    8  1.500
Tight case: k disjoint paths P3 (a-b-c); OPT = 1 per P3, greedy pays 2:
  k=1: approx=2, OPT=1, ratio=2.000
  k=3: approx=6, OPT=3, ratio=2.000
  k=5: approx=10, OPT=5, ratio=2.000
```

Random graphs land far below the bound; disjoint P3s hit it exactly -- 2 is tight. State of the
art: algorithms reach 2 - O(1/sqrt(log n)) (Karakostas); Dinur-Safra prove NP-hardness below
1.3606, and below 2 - eps under the Unique Games Conjecture (Khot-Regev). The LP relaxation with
0.5-rounding gives the same factor 2 (LP machinery:
[Chapter 151](../dsa/chapters/ch151-linear-programming.md)); that LP's integrality gap approaches
2 -- on K_n, OPT = n - 1 while the LP optimum is n/2.

## 3. Metric TSP: Double-Tree (2x) and Christofides (1.5x)

Metric TSP: complete graph, weights satisfying w(u,v) <= w(u,x) + w(x,v); the triangle inequality
is what makes the problem approximable. The non-metric case is catastrophic (section 3.1).

**Double-tree**: build an MST, walk around it depth-first (each tree edge traversed twice),
shortcut repeated vertices. Shortcutting never lengthens a metric tour; the walk costs
2 * MST <= 2 * OPT (deleting one edge of the optimal tour leaves a spanning tree).

**Christofides** (1976; independently Serdyukov) reaches 1.5:

```text
 1. MST T                                  cost <= OPT
 2. S = odd-degree vertices of T           |S| is even
 3. min-weight perfect matching M on S     cost <= OPT/2
 4. T + M: all degrees even -> Eulerian multigraph
 5. Euler tour + shortcut -> Hamiltonian cycle, ALG <= OPT + OPT/2
```

Why step 3 holds: list S in the order the optimal tour visits it and pair alternately --
(s1,s2),(s3,s4),... and (s2,s3),(s4,s5),...,(sn,s1). These two perfect matchings on S each cost
at most their corresponding tour sub-paths (triangle inequality), and together they charge every
tour edge at most once, so the cheaper one costs <= OPT/2; the min-weight matching is at most
that. Step 4 uses the parity fact that a graph has an even number of odd-degree vertices;
matching exactly the odd ones restores even degrees everywhere. Karlin, Klein and Oveis Gharan
broke the 45-year-old barrier with a randomized 1.5 - 10^-36 approximation (STOC 2021) --
vanishing, but proof that 1.5 is not a wall; no PTAS for metric TSP is known.

### 3.1 Non-metric TSP: Not Approximable At All

Sahni-Gonzalez (1976): for any polynomially bounded computable ratio rho(n), TSP with arbitrary
weights admits no rho(n)-approximation unless P = NP. Gap reduction from Hamiltonian Cycle: set
w = 1 on edges of G and w = rho(n) * n + 1 on non-edges; a Hamiltonian cycle costs exactly n,
any other tour uses a non-edge and costs > rho(n) * n, and a rho(n)-approximation must return
cost <= rho * OPT, distinguishing the cases in polynomial time. Moral: triangle inequality is
not cosmetic; without it, hardness of approximation is total.

## 4. Set Cover: Greedy and the ln(n) Threshold

Given universe U and a set family, pick the fewest sets covering U. Greedy: repeatedly take the
set covering the most still-uncovered elements. Let k* = OPT. While any optimal set still has
uncovered elements, some set covers >= 1/k* of what remains, so
u_next <= u (1 - 1/k*) <= u e^(-1/k*): after t * k* picks, <= n e^(-t) remain. Greedy therefore
uses at most k*(ln n + 1) sets; Chvatal sharpens this to the harmonic number H(d), d = largest
set size. The bound is essentially tight -- Feige (1998) proved no (1 - eps) ln n approximation
exists unless NP has quasi-polynomial algorithms (NP subset of n^(O(log log n))): algorithm and
hardness meet at ln n. Scale check: for |U| = 10^6, ln n ~ 13.8 -- "asymptotically bad" yet
behaving like a small constant.

## 5. Load Balancing: List Scheduling and LPT

m identical machines, jobs p_1..p_n, minimize makespan. List Scheduling (Graham 1966): send each
job to the least-loaded machine; the problem is online in this form (see
[Online Algorithms](../dsa/chapters/ch146-online-algorithms.md)). Bound: (2 - 1/m) OPT. Proof:
let j be the last job placed, L its machine's pre-arrival load, S total work, so ALG = L + p_j.
Since j took the *minimum* load, L <= (S - p_j)/m, hence
ALG <= S/m + (1 - 1/m) p_j <= OPT + (1 - 1/m) OPT = (2 - 1/m) OPT, because both the average
load S/m and the largest job p_j are lower bounds on OPT -- the two anchors of nearly every
scheduling analysis. LPT (sort descending, then list-schedule; Graham 1969) improves this to
(4/3 - 1/(3m)) OPT, tight for m = 2: jobs {3,3,2,2,2} give LPT makespan 7 vs OPT 6, ratio
7/6 = 4/3 - 1/6. Makespan scheduling is strongly NP-hard (3-partition): no FPTAS unless P = NP.

## 6. Hardness of Approximation: Gap Reductions and PCP

NP-completeness kills exact solutions; hardness of approximation shows even *closeness* is hard.
The workhorse is the gap reduction:

```text
  input x --poly--> instance G(x)      if x in L:     OPT(G(x)) = a
                                       if x not in L: OPT(G(x)) >= b,  b/a = rho
  a rho-approximator returns <= rho*OPT <= a  iff x in L  =>  L in P  =>  P = NP
```

The **PCP theorem** (Arora-Safra 1992; Arora-Lund-Motwani-Sudan-Szegedy 1998) starts the
cascade: every NP statement has a proof spot-checkable by reading a *constant* number of bits --
correct proofs always accepted, any wrong claim rejected with constant probability. That constant
gap on proofs becomes a constant gap between satisfiable and unsatisfiable-looking instances;
repetition amplifies it; reductions propagate it to concrete problems (max-3SAT, vertex cover
1.3606, set cover ln n via Feige). One sentence to keep: PCP turns "verifying a proof" into
"amplifying a gap". Read the table's conditional column carefully -- UGC hardness rests on a
stronger, unproven assumption than P != NP; flagging which assumption a hardness result needs
is itself an interview signal.

| Problem | Best known ratio | Hardness (conditional) | Technique |
|---|---|---|---|
| Vertex Cover | 2 - O(1/sqrt(log n)) | >= 1.3606 (P != NP); 2 - eps (UGC) | matching / LP rounding |
| Set Cover | H_n ~ ln n | (1 - eps) ln n | greedy |
| Metric TSP | 1.5 - 10^-36 (randomized) | > 1 by a small constant; no PTAS known | MST + matching |
| TSP (non-metric) | none | no rho(n) at all unless P = NP | -- |
| 0/1 Knapsack | 1 + eps (FPTAS) | weakly NP-hard only | value scaling + DP |
| Max Cut | 0.8786 of OPT | 16/17 under UGC | SDP + rounding |

## 7. Knapsack FPTAS: Rounding Done Right

0/1 knapsack has an exact DP in O(nW) (W = capacity) -- pseudo-polynomial, exponential in the
input length of W. The FPTAS (Ibarra-Kim 1975) shrinks the value space by scaling:
K = eps * vmax / n, v_i' = floor(v_i / K); the DP then has <= n * vmax / K = n^2 / eps states and
runs in O(n^3 / eps), independent of W. Why at most 1 + eps is lost: rounding down costs < K
per item, < nK = eps * vmax total; OPT >= vmax (take the single most valuable item), so the
scaled optimum corresponds to a feasible solution of value >= OPT - eps * vmax >= (1 - eps) OPT.

```python
# 0/1 knapsack: FPTAS (value scaling + DP) vs exact DP (seeded, stdlib only).
import random

def knap_exact(wt, val, W):
    best = [0] * (W + 1)
    for w, v in zip(wt, val):
        for c in range(W, w - 1, -1):
            best[c] = max(best[c], best[c - w] + v)
    return best[W]

def knap_fptas(wt, val, W, eps):
    n, vmax = len(val), max(val)
    K = eps * vmax / n
    scaled = [int(v / K) for v in val]
    vsum = sum(scaled)
    INF = W + 1
    dp = [INF] * (vsum + 1)  # dp[s] = min weight with scaled value exactly s
    dp[0] = 0
    for w, s in zip(wt, scaled):
        for t in range(vsum, s - 1, -1):
            dp[t] = min(dp[t], dp[t - s] + w)
    best = max(s for s in range(vsum + 1) if dp[s] <= W)
    return best * K, vsum + 1

rng = random.Random(42)
wt = [rng.randint(1, 60) for _ in range(24)]
val = [rng.randint(1, 100) for _ in range(24)]
W = sum(wt) // 3
opt = knap_exact(wt, val, W)
print("24 items, capacity={}, vmax={}: exact DP OPT={}".format(W, max(val), opt))
print("  eps    states  FPTAS    OPT/ALG   guarantee (1+eps)")
for eps in (0.5, 0.2, 0.1, 0.05, 0.02):
    v, st = knap_fptas(wt, val, W, eps)
    print("  {:<6} {:>6} {:>8.1f} {:>9.6f} {:>13.3f}".format(eps, st, v, opt / v, 1 + eps))
```

Output (real run of the block above):

```text
24 items, capacity=193, vmax=98: exact DP OPT=869
  eps    states  FPTAS    OPT/ALG   guarantee (1+eps)
  0.5       598    859.5  1.011004         1.500
  0.2      1508    863.2  1.006700         1.200
  0.1      3026    866.1  1.003377         1.100
  0.05     6061    867.3  1.001960         1.050
  0.02    15174    868.6  1.000453         1.020
```

Measured ratios sit far below the guarantee and improve smoothly as states are added -- typical
FPTAS behavior. Contrast vertex cover: strongly NP-hard, so no scaling trick can rescue it; the
weak/strong NP-hardness line from section 1 is what separates these two problems.

## 8. What Interviews Actually Ask

- "NP-hard problem in production -- what do you do?" Expected shape: exact solver (ILP/DP) for
  small inputs, an approximation algorithm with a stated ratio for scale, a heuristic baseline
  measured *against* the approximation; "just use a heuristic" with no reference guarantee is
  the weak answer.
- Ratios worth knowing cold: vertex cover 2, Christofides 1.5, set cover ln n, knapsack FPTAS,
  list scheduling 2 - 1/m, LPT 4/3 - 1/(3m). Better than exotic ratios: proving one -- the
  maximal-matching and averaging-load arguments above are three lines each on a whiteboard.
- "PTAS vs FPTAS?" then "why can't vertex cover have an FPTAS?" (strong NP-hardness, unless
  P = NP); "why is non-metric TSP different?" (any polynomial ratio would decide Hamiltonian
  Cycle, section 3.1). Deeper drills: [Chapter 145](../dsa/chapters/ch145-approximation-algorithms.md);
  max cut derandomization and other randomized techniques in
  [Chapter 63: Randomized Algorithms](../dsa/chapters/ch63-randomized-algorithms.md).

## References

1. Vazirani, *Approximation Algorithms* (Springer) -- <https://link.springer.com/book/10.1007/3-540-29112-1>
2. Williamson & Shmoys, *The Design of Approximation Algorithms* (Cambridge UP; free PDF at designofapproxalgs.com) -- <https://www.cambridge.org/core/books/design-of-approximation-algorithms/88E0AEAEFF2382681A103EEA572B83C6>
3. Christofides (1976), *Worst-Case Analysis of a New Heuristic for the Travelling Salesman Problem*, GSIA Report 388; republished in Operations Research Forum (2022) -- <https://doi.org/10.1007/s43069-021-00101-z>
4. Graham (1969), *Bounds on Multiprocessing Timing Anomalies*, SIAM J. Appl. Math. 17(2) -- <https://doi.org/10.1137/0117039>
5. Chvatal (1979), *A Greedy Heuristic for the Set-Covering Problem*, Math. of OR 4(3) -- <https://doi.org/10.1287/moor.4.3.233>
6. Feige (1998), *A Threshold of ln n for Approximating Set Cover*, J. ACM 45(4) -- <https://doi.org/10.1145/285055.285059>
7. Sahni & Gonzalez (1976), *P-Complete Approximation Problems*, J. ACM 23(3) -- <https://doi.org/10.1145/321958.321975>
8. Ibarra & Kim (1975), *Fast Approximation Algorithms for the Knapsack and Sum of Subset Problems*, J. ACM 22(4) -- <https://doi.org/10.1145/321879.321881>
9. Karlin, Klein & Oveis Gharan, *A (Slightly) Improved Approximation Algorithm for Metric TSP*, STOC 2021 -- <https://arxiv.org/abs/2007.01409>
10. Arora, Lund, Motwani, Sudan & Szegedy (1998), *Proof Verification and the Hardness of Approximation Problems*, J. ACM 45(3) -- <https://doi.org/10.1145/273865.273901>
11. Cormen, Leiserson, Rivest & Stein, *Introduction to Algorithms*, 4th ed. (chapters 34-35) -- <https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/>
