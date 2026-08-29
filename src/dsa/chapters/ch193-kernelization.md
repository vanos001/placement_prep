# Chapter 193: Kernelization: The Preprocessing Engine of Parameterized Algorithms

Every serious solver preprocesses -- SAT clauses simplified, ILP rows stripped --
but ordinary preprocessing is folklore: nobody can say how small the output is.
**Kernelization** is preprocessing with a
warranty: the reduction runs in polynomial time and the result provably has size
bounded by a function of the parameter alone. It is the bridge between
[parameterized algorithms](ch148-parameterized-algorithms.md) and practice (advanced
survey: [approximation and FPT techniques](../advanced/approximation-fpt.md));
background on NP/P lives in [complexity classes](../../cs-theory/complexity-classes.md).

---

## 193.1 The Contract of a Kernel

A parameterized problem has instances `(x, k)` where `k` is a numeric parameter
(budget, solution size, treewidth). A **kernelization** is a polynomial-time
algorithm mapping `(x, k)` to `(x', k')` such that:

1. `(x, k)` is a YES-instance **iff** `(x', k')` is (two-sided; heuristic pruning
   only hopes to preserve YES cases),
2. `k' <= k`,
3. `|x'| <= g(k)` for a computable function `g` -- size is input length (for
   graphs: vertices plus edges).

The output `(x', k')` is the **kernel**; if `g(k)` is a polynomial, the problem
admits a **polynomial kernel**.

**Kernel iff FPT.** For a decidable parameterized problem with infinitely many YES
and NO instances, the problem is FPT (solvable in `f(k) * n^c`) **iff** it has a
kernel: run the FPT algorithm with an increasing size cutoff until it halts on its
own, and hard-code the finitely many answers below it. Kernelization is not an
optional extra for FPT problems -- it is what they all do, admitted or not.

```text
 input (x, k), |x| = n huge              kernel (x', k'), |x'| <= g(k)
 +--------------------------+           +----------------------------+
 |  KERNELIZER              |---------> |  tiny but equivalent       |
 |  poly time, GUARANTEED   |           |  k' <= k, same YES/NO      |
 +--------------------------+           +----------------------------+
                any search on the kernel now costs poly(n) + 2^O(g(k))
                -- preprocessing with a warranty, not with crossed fingers
```

---

## 193.2 The Buss Kernel for Vertex Cover

**VERTEX COVER(k)**: does graph `G` have a cover of at most `k` vertices? Three
reduction rules, each with a three-line soundness proof:

- **R1 (degree rule).** If `deg(v) > k`, put `v` in the cover, delete it,
  `k := k - 1`. *Why:* a cover without `v` must contain all `deg(v) > k` neighbors.
- **R2 (isolate rule).** Delete degree-0 vertices. *Why:* they cover nothing.
- **R3 (edge budget).** If more than `k^2` edges remain, answer NO: after R1 every
  degree is `<= k`, so any `k` vertices cover at most `k * k` edges.

The rules cascade: forcing a vertex shrinks `k`, pushing more vertices over the R1
threshold, so R1 is reapplied until it fires no more. Then at most `k` vertices
were forced (all must sit in one cover), at most `k^2` edges remain, hence at most
`2k^2` non-isolated vertices: a kernel with `k + 2k^2` vertices and `k^2` edges --
the classic **Buss kernel** ([Buss and Goldsmith 1993](https://doi.org/10.1137/0222038)).
The famous "2k vertices" figure needs Section 193.4's crown/LP machinery on top.

---

## 193.3 Demo: Buss Kernel on Random Graphs

The script implements R1-R3 on one deterministic star plus four random `G(n, p)`
instances, printing verdicts, forced sets, kernel sizes, and `2k'^2` bound checks.

```python
import random

def build_gnp(n, p, rng):
    adj = {v: set() for v in range(n)}
    for u in range(n):
        for v in range(u + 1, n):
            if rng.random() < p:
                adj[u].add(v); adj[v].add(u)
    return adj, sum(len(s) for s in adj.values()) // 2

def buss_kernel(adj, k):
    live = {v for v in adj if adj[v]}              # R2: drop isolated
    forced = []
    while True:                                    # R1: force degree > k
        hot = next((v for v in live if len(adj[v] & live) > k), None)
        if hot is None: break
        live.remove(hot); forced.append(hot); k -= 1
        if k < 0: return "NO", forced, set(), 0, -1
    ke = sum(len(adj[v] & live) for v in live) // 2
    if ke > k * k: return "NO", forced, set(), 0, k    # R3: edge budget
    kern = {v for v in live if adj[v] & live}      # R2: drop new isolates
    return ("KERNEL" if kern else "YES"), forced, kern, ke, k

rng = random.Random(48)
adj = {0: set(range(1, 41)), **{v: {0} for v in range(1, 41)}}   # star
cases = [("star n=41", adj, 40, 3)]
for name, n, p, k in [("G(60, 0.15)", 60, 0.15, 6), ("G(200, 0.01)", 200, 0.01, 15),
                      ("G(500, 0.001)", 500, 0.001, 12), ("G(30, 0.5)", 30, 0.5, 10)]:
    a, m = build_gnp(n, p, rng)
    cases.append((name, a, m, k))

print("%-14s %5s %6s %4s | %-6s %6s %5s %6s %3s | %s" % (
    "instance", "n", "m", "k", "result", "forced", "kn", "ke", "k'", "kn<=2k'^2"))
print("-" * 76)
for name, a, m, k in cases:
    verdict, forced, kern, ke, kf = buss_kernel(a, k)
    ok = "n/a" if verdict != "KERNEL" else str(len(kern) <= 2 * kf * kf)
    print("%-14s %5d %6d %4d | %-6s %6d %5d %6d %3d | %s" % (
        name, len(a), m, k, verdict, len(forced), len(kern), ke, kf, ok))
```

Output (verbatim):

```text
instance           n      m    k | result forced    kn     ke  k' | kn<=2k'^2
----------------------------------------------------------------------------
star n=41         41     40    3 | YES         1     0      0   2 | n/a
G(60, 0.15)       60    240    6 | NO          7     0      0  -1 | n/a
G(200, 0.01)     200    181   15 | KERNEL      0   163    181  15 | True
G(500, 0.001)    500    133   12 | KERNEL      0   207    133  12 | True
G(30, 0.5)        30    234   10 | NO         11     0      0  -1 | n/a
```

- **star n=41**: degree 40 > 3 forces the center; no edges remain -- preprocessing
  solved the instance outright with an empty kernel.
- **G(60, 0.15), G(30, 0.5)**: R1 forces more high-degree vertices than the budget
  allows -- itself a NO certificate, no branching needed.
- **G(200, 0.01), G(500, 0.001)**: genuine kernels (R3 quiet: 181 <= 225 and
  133 <= 144; bound kept: 163 <= 450, 207 <= 288); a `2^k` search is viable.
---

## 193.4 From O(k^2) to 2k Vertices: Crowns and the LP

**Crown reduction.** A *crown* is a pair `(H, C)` of vertex sets where `C` is
independent, every neighbor of `C` lies in `H` (so `N(C) = H`), and `H` has a
matching into `C`:

```text
     head H = {v1, v2}        crown C = {c1, c2, c3, c4} (independent)
        ^    ^                    |      |      |      |
        |    +--------------------+------+      |      |
        +-> each c in C has ALL neighbors in H; H matched into C (Hall)
     RULE: put H in the cover, delete H + C, k := k - |H|
```

*Why it works:* the matching forces `|H| <= |C|`, so paying `|H|` is never worse
than covering the matching edges. The **Crown Lemma** (Hall's theorem on the
bipartite double cover) yields a crown, in polynomial time, in any graph of minimum
degree >= 1 with more than `3 * max-degree` vertices; interleaved with R1-R3,
crowns drive the kernel toward `3k` ([approximation algorithms](ch145-approximation-algorithms.md)).

**Nemhauser-Trotter LP kernel.** The Vertex Cover LP (`x_v` in `[0,1]`, minimize
the sum subject to `x_u + x_v >= 1` per edge) has half-integral optima: every
`x_v` in `{0, 1/2, 1}` ([Nemhauser and Trotter 1975](https://doi.org/10.1007/bf01580444)).
Fix the `x = 1` vertices into the cover, delete the `x = 0` vertices, keep the
`x = 1/2` core with budget `k'`; since the LP value is `|core|/2`, a YES-instance
leaves a core of at most `2k'` vertices -- a kernel with **2k vertices and 2k^2
edges**, found twenty years before parameterized complexity had a name.

---

## 193.5 A Field Guide to Kernels

| Problem | Parameter | Kernel | Where it comes from |
|---|---|---|---|
| Vertex Cover | solution size k | 2k vertices, 2k^2 edges | crown reduction, Nemhauser-Trotter LP |
| Feedback Vertex Set (undirected) | solution size k | linear, in linear time | suppression + erase-and-compress; Iwata ICALP 2017 |
| Max-SAT, plain | k = clauses satisfiable | none, unless NP in coNP/poly | meta-theorem (Section 193.6) |
| Max-SAT, above guarantee | k above the m/2 baseline | FPT, Mahajan-Raman 1999 | above-guarantee parameterization |
| Dominating Set | solution size k | none, unless NP in coNP/poly | meta-theorem |

- **Parameter choice flips kernelability.** Plain Max-SAT has no polynomial kernel,
  but [Mahajan and Raman 1999](https://doi.org/10.1006/jagm.1998.0996)
  re-parameterized it *above the trivial guarantee* (any assignment satisfies at
  least half the clauses) and made it FPT. Reparameterization is the cheapest
  kernelization there is.
- **Feedback Vertex Set sketch.** The undirected FVS kernel suppresses degree-2
  vertices (contract the path, remember it) and exploits how a small solution
  interacts with cycles; modern erase-and-compress kernels are linear, and
  [Iwata](https://arxiv.org/abs/1608.01463) computes one in linear *time*.

---

## 193.6 Kernel Lower Bounds: When Preprocessing Cannot Win

**Distillation.** Bodlaender, Downey, Fellows, and Hermelin
([2009](https://doi.org/10.1016/j.jcss.2009.04.001)) asked: can `t` instances of an
NP-hard problem be compressed into ONE instance of size `poly(max k_i, log t)`
answering the OR of them all? If a problem OR-distills into a parameterized problem
with a poly kernel, coNP is contained in `NP/poly`; Fortnow and Santhanam
([2011](https://doi.org/10.1016/j.jcss.2010.06.007)) strengthened the conclusion to
**NP contained in coNP/poly** -- a polynomial-hierarchy collapse disbelieved on the
scale of P = NP. Hence the meta-theorem:

> If the unparameterized version of a problem is NP-hard and it has a polynomial
> kernel, then NP is contained in coNP/poly. Dominating Set, Clique, plain
> Max-SAT, and friends therefore have no polynomial kernel under standard
> assumptions.

**OR-cross-composition.** Bodlaender, Jansen, and Kratsch
([2014](https://doi.org/10.1137/120880240)) turned distillation into a per-problem
weapon: take `t` instances of an NP-hard source problem, pad them to equal size,
glue them into one instance whose parameter is only `poly(max k_i, log t)`:

```text
 t source instances x1..xt, padded to equal size s   (schematic)

 +---------+---------+---------+---------+
 |   x1    |  dead   |  dead   |  dead   |    blocks speak through a
 +---------+---------+---------+---------+    connector gadget; an OR-gadget
 |  dead   |   x2    |  dead   |  dead   |    makes the composed instance
 +---------+---------+---------+---------+    YES iff SOME block says YES
 |  dead   |  dead   |   xt    |  dead   |    parameter p(y) is only
 +---------+---------+---------+---------+    poly(max p(xi), log t)
```

If a target problem Q accepts such a composition, Q has no polynomial kernel --
one construction retires the question. When lower bounds bite, the literature
offers exponential-size kernels, restricted graph classes, and structural
parameters (treewidth, deletion distance) where the obstruction dissolves.

**Traps.** Do not credit Buss with the 2k-vertex kernel (that is crowns/LP; Buss
gives `k + 2k^2`); do not call kernelization heuristic (rules carry soundness
proofs and a worst-case size bound); and remember kernel size counts total input
length -- vertices plus edges.

---

## 193.7 References

1. M. Cygan, F. V. Fomin, L. Kowalik, D. Lokshtanov, D. Marx, M. Pilipczuk, M. Pilipczuk, S. Saurabh. *Parameterized Algorithms*. Springer, 2015. <https://link.springer.com/book/10.1007/978-3-319-21275-3>
2. H. L. Bodlaender, R. G. Downey, M. R. Fellows, D. Hermelin. On problems without polynomial kernels. *J. Comput. Syst. Sci.* 75(8), 2009. <https://doi.org/10.1016/j.jcss.2009.04.001>
3. L. Fortnow, R. Santhanam. Infeasibility of instance compression and succinct PCPs for NP. *J. Comput. Syst. Sci.* 77(1), 2011. <https://doi.org/10.1016/j.jcss.2010.06.007>
4. H. L. Bodlaender, B. M. P. Jansen, S. Kratsch. Kernelization lower bounds by cross-composition. *SIAM J. Discrete Math.* 28(1), 2014. <https://doi.org/10.1137/120880240>
5. G. L. Nemhauser, L. E. Trotter Jr. Vertex packings: structural properties and algorithms. *Math. Program.* 6(1), 1975. <https://doi.org/10.1007/bf01580444>
6. S. Mahajan, R. Raman. Parameterizing above guaranteed values: MaxSat and MaxCut. *J. Algorithms* 31(2), 1999. <https://doi.org/10.1006/jagm.1998.0996>
7. J. F. Buss, J. Goldsmith. Nondeterminism within P^*. *SIAM J. Comput.* 22(3), 1993. <https://doi.org/10.1137/0222038>
8. Y. Iwata. Linear-time kernelization for Feedback Vertex Set. ICALP 2017. <https://arxiv.org/abs/1608.01463>
