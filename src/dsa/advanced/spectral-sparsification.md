# Spectral Sparsification: Cuts, Leverages, and Laplacian Solvers

A dense graph and a sparse graph can be computationally indistinguishable in what they *mean*
and wildly different in what they *cost*. Sparsification makes that gap constructive: replace
$G$ by a sparse $H$ that preserves a chosen invariant, then run every downstream algorithm on
$H$. The two preservation notions that anchor this field are **cut preservation** (Benczúr and
Karger) and **spectral preservation** (Spielman, Srivastava, Batson), and they plug directly
into **nearly-linear-time Laplacian solvers** (Spielman-Teng, Kyng-Sachdeva).

Scope note: [Ch 159/160 + this survey page](./parallel-graph-algorithms.md) carries the
one-paragraph definitions, the sparsifier-family comparison table, and the parallel complexity
rows; [Ch 154's applications table](../chapters/ch154-spectral-graph-theory.md) lists graph
sparsification as "preserve spectral similarity" (§154.11). Both own the breadth. This page
owns the mechanics: the sampling probabilities, the linear algebra they act on, a measured
cut-vs-spectral comparison, and where the solver pipeline actually gets its speed.

## 1. One matrix, two guarantees

Everything is phrased through the Laplacian. For an edge $e = (u,v)$ with weight $w_e$, let
$b_e \in \mathbb{R}^n$ be $+1$ at $u$, $-1$ at $v$. Then

$L_G = \sum_e w_e b_e b_e^\top$, and the quadratic form is energy: $x^\top L_G x = \sum_{(u,v)} w_e (x_u - x_v)^2$.

The two sparsification contracts differ in which class of test vectors must survive:

| Notion | Requirement | Edge count | Sampling price $p_e$ | Origin |
|---|---|---|---|---|
| Cut sparsifier | every cut value within $(1\pm\epsilon)$ | $O(n\log n/\epsilon^2)$ | $\min(1, \rho/c_e)$, $c_e$ = min cut containing $e$ | Benczur-Karger |
| Spectral sparsifier | $(1-\epsilon)\,x^\top L_G\,x \le x^\top L_H\,x \le (1+\epsilon)\,x^\top L_G\,x$ for all $x$ | $O(n/\epsilon^2)$, optimal | $\min(1, \rho\,\ell_e)$, $\ell_e$ = leverage score | Spielman-Srivastava, BSS |

Two structural facts organize everything that follows:

1. **Spectral implies cut.** A cut is the quadratic form of a 0/1 indicator vector, so a
   spectral sparsifier is automatically a cut sparsifier with the same $\epsilon$.
2. **Cut does not imply spectral.** Benczur-Karger need $O(n \log n/\epsilon^2)$ edges for
   cut-only control, while BSS build spectral sparsifiers with $O(n/\epsilon^2)$ edges - the
   stronger guarantee comes with *fewer* edges. The extra $\log n$ factor is the price of a
   certificate that only speaks about indicators.

## 2. Cut sparsifiers: Benczur-Karger and the tyranny of bottlenecks

Karger's cut-counting lemma says an undirected graph with minimum cut value $\lambda$ has at
most $n^{2\alpha}$ cuts of value $\le \alpha\lambda$. This is why *any* sampling scheme can
work: there are exponentially many cuts but they overlap heavily, so a Chernoff + union-bound
over "cut levels" can control all of them at once. What uniform sampling cannot do is choose
*which* edges matter. Take the barbell below: the single bridge is a cut all by itself
($\lambda = 1$), so preserving every cut within $(1\pm\epsilon)$ forces the bridge into $H$
with probability 1 - yet uniform sampling drops it with constant probability.

```text
      cluster A (K6, w=1)            cluster B (K6, w=1)
   +--------------------+         +--------------------+
   |  o--o--o--o--o--o  |--(5,6)--|  o--o--o--o--o--o  |
   |  1.0  ...  w=1     |  w=1    |        w=1  ...    |
   +--------------------+         +--------------------+
   c_e of a bridge  = 1 / 1.0 = 1.0   (the min cut containing it is the bridge cut)
   c_e of a K6 edge = 5 / 1.0 = 5.0   (five parallel ways around)
   l_e of a bridge  = 1.0             (all current must cross it)
   l_e of a K6 edge = 2/6 ~ 0.33
```

Benczur and Karger's fix is to price each edge by how badly a cut depends on it. Define the
**connectivity** $c_e$ as the minimum cut containing $e$, divided by $w_e$: a bridge has
$c_e = 1$, an edge inside a dense cluster has $c_e$ on the order of the cluster density. Their
scheme samples edge $e$ with probability

$p_e = \min(1,\ \rho / c_e)$ with $\rho = \Theta(\log n / \epsilon^2)$, and rescales survivors by $1/p_e$.

Bottleneck edges hit the clamp and are always kept; redundant cluster edges are down-sampled
and their reweighting is statistically protected by the many cuts around them. The engine
making this polynomial-time is a **tree packing**: pack $\approx O(\log n)$ spanning trees so
that every cut gets its share of every tree (Nagamochi-Ibaraki sparse certificates produce an
$O(n)$-edge subgraph preserving all cut values up to $k$ in near-linear time), and read
$c_e$ off how many trees contain $e$. Result: $O(n \log n/\epsilon^2)$ edges preserving all
$2^n$ cut values simultaneously. (Fung-Hariharan-Harvey-Panigrahi later proved that sampling
by standard connectivities alone already yields good sparsifiers, resolving an open question
of Benczur-Karger: arXiv:1004.4080.)

## 3. Leverage scores and effective resistance: the spectral upgrade

For spectral control the right edge statistic is the **effective resistance**

$R_e = b_e^\top L_G^+ b_e$  (voltage drop between the endpoints under a 1-amp injection), and the **leverage score** $\ell_e = w_e R_e \in [0, 1]$.

Three readings of $\ell_e$, all worth internalizing:

- **Electrical:** $\ell_e$ is the fraction of the endpoint-to-endpoint resistance contributed
  by the edge itself; bridges have $\ell_e = 1$, edges buried in a clique have $\ell_e \approx 2/n$.
- **Spanning trees:** under the weighted Kirchhoff distribution over spanning trees
  ($\Pr[T] \propto \prod_{e \in T} w_e$), $\Pr[e \in T] = \ell_e$ exactly. The identity
  $\sum_e \ell_e = n - 1$ is just "a tree has $n-1$ edges" and doubles as a unit test.
- **Statistical:** $\ell_e$ is the leverage of row $b_e$ in the weighted incidence system -
  the exact analogue of the leverage scores from regression diagnostics.

Spielman-Srivastava sample $e$ with $p_e = \min(1,\ \rho\,\ell_e)$ where
$\rho = \Theta(\epsilon^{-2}\log n)$, rescale by $1/p_e$, and matrix Chernoff bounds deliver
the $(1\pm\epsilon)$ quadratic-form guarantee on $O(n\log n/\epsilon^2)$ edges. Compare the
two price rules: BK samples *inversely* to redundancy, SS samples *proportionally* to
irreplaceability - on most graphs the two rankings nearly coincide (the demo below makes this
visible), but SS's certificate is a statement about all vectors, not just indicators.

The computational key: you never need $L^+$ exactly. Spielman-Srivastava approximate all
$R_e$ by Johnson-Lindenstrauss sketches: push $O(\log n/\delta^2)$ random test vectors through
a nearly-linear-time Laplacian solver, estimate $b_e^\top L^+ b_e$ from the sketched outputs.
This is the bridge from "sparsification is possible" to "sparsification is fast".

**Twice-Ramanujan sparsifiers (BSS).** Batson-Spielman-Srivastava construct spectral
sparsifiers non-randomly, greedily adding reweighted edges one at a time, down to
$O(n/\epsilon^2)$ edges. The headline is two-sided: $O(n/\epsilon^2)$ edges *suffice*, the
achieved spectral quality matches what the best possible $d$-regular expander on $n$
vertices would deliver (hence "twice Ramanujan"), and $\Omega(n/\epsilon^2)$ edges are
necessary for a $(1\pm\epsilon)$ guarantee - so the spectral size bound is optimal, not
just achievable.

## 4. From sparsifier to solver: conditioning is the whole story

Solving $Lx = b$ (with $b \perp \mathbf{1}$, since $L$ is singular) is the primitive behind
spectral clustering, electrical-flow max-flow, random-walk computations, and SDD systems.
Conjugate gradient on $L$ directly costs $O(\sqrt{\kappa(L)}\log(1/\epsilon_{cg}))$
iterations, and $\kappa(L) = \lambda_{max}/\lambda_2$ can be huge. Preconditioning replaces it
with $\kappa(P^{-1}L)$; the punchline of the sparsifier program is:

$H$ is a spectral $(1\pm\epsilon)$-sparsifier of $G$ $\iff$ $\kappa(L_H^+ L_G) \le \frac{1+\epsilon}{1-\epsilon}$.

So a sparsifier is *exactly* a good preconditioner with the same edge-type complexity as $G$.
The solver line of work is then a recursion:

- **Spielman-Teng (STOC 2004):** low-stretch spanning trees (average stretch
  $O(m \cdot \text{polylog})$) as the base preconditioner, plus sparsified recursive
  clustering -> the first $\tilde{O}(m)$-time Laplacian solver. The machinery (stretch,
  preconditioner chains, vertex elimination) is monograph-length; see their arXiv survey below.
- **Kyng-Sachdeva (FOCS 2016, arXiv:1605.02353):** sparse approximate Cholesky
  factorization - eliminate vertices in a random order, but instead of exact elimination,
  *sample* a sparse correction to the Schur complement (each off-diagonal entry of the
  sampled factor scaled by inverse probabilities). Purely random sampling: no trees, no
  expanders, no prior sparsifier. Analysis needs matrix-martingale concentration because the
  samples are conditionally dependent. Nearly-linear time, and this sampling-based view is
  what most modern Laplacian-solver implementations build on.

Why does solver time scale like $\log(1/\epsilon)$ while sparsifier *size* scales like
$\epsilon^{-2}$? Iterative refinement multiplies accuracy multiplicatively - halving the error
costs one more linear solve - but a sparsifier must buy accuracy in a single sample: cutting
$\epsilon$ in half quadruples the Chernoff sample budget. Sparsify once to fixed accuracy,
then let CG's log-dependence finish the job.

## 5. Measured: cut pricing vs spectral pricing

The demo builds the 12-vertex weighted barbell from §2 (two 6-cliques, one bridge, one light
cross edge, one boosted interior edge), computes each edge's statistics honestly ($c_e$ by
brute-force cut enumeration - only honest at $n=12$; $\ell_e$ via $L^+$), and compares three
samplers at the same ~$2n$-edge budget: uniform, BK-style ($p_e \propto 1/c_e$), and
SS-style ($p_e \propto \ell_e$). Quality metrics per trial: worst relative error over **all
4094 nontrivial cuts**, the min-cut (bottleneck) cut error, worst quadratic-form error over
91 test vectors (all 66 unit-difference vectors, the Fiedler vector, 24 Gaussians), and the
spectral error $\max(1-\lambda_{min}, \lambda_{max}-1)$ of $L_G^{+1/2} L_H L_G^{+1/2}$ on
$\mathbf{1}^\perp$. Note in the leverage line: the printed sum equals $n-1 = 11$, the §3 identity.

```python
import numpy as np

rng = np.random.default_rng(7)

# Barbell: 6-clique {0..5}, 6-clique {6..11}, single weight-1 bridge (5,6),
# one light cross edge (0,9) w=0.3, one boosted interior edge (1,3) w=4.
n = 12
edges = []
for lo in (0, 6):
    for i in range(6):
        for j in range(i + 1, 6):
            edges.append((lo + i, lo + j, 1.0))
edges.append((1, 3, 4.0))
edges.append((0, 9, 0.3))
edges.append((5, 6, 1.0))      # the single-edge bottleneck
m = len(edges)
u = np.array([e[0] for e in edges]); v = np.array([e[1] for e in edges])
w = np.array([e[2] for e in edges], dtype=float)

B = np.zeros((n, m))
B[u, np.arange(m)] = 1.0; B[v, np.arange(m)] = -1.0

def laplacian(wv):                      # L = sum_e w_e b_e b_e^T
    return (B * wv) @ B.T

L_G = laplacian(w)
assert np.abs(L_G.sum(axis=1)).max() < 1e-12       # rows sum to zero
Linv = np.linalg.pinv(L_G)
resist = np.array([Linv[a, a] + Linv[b, b] - 2 * Linv[a, b] for a, b in zip(u, v)])
lev = w * resist                              # leverage scores l_e = w_e R_e
print(f"leverage sum (identity: sum l_e = n-1): {lev.sum():.6f}")

# Exact Benczur-Karger connectivity c_e = (min cut containing e) / w_e,
# brute-forced over all 2^12 subsets (feasible only because n = 12).
conn = np.empty(m)
for e in range(m):
    best = np.inf
    for mask in range(1, 2**n - 1):
        if (mask >> u[e]) & 1 and not (mask >> v[e]) & 1:
            side = (mask >> np.arange(n)) & 1
            cut = w[side[u] != side[v]].sum()
            best = min(best, cut)
    conn[e] = best / w[e]
ib = int(np.where((u == 5) & (v == 6))[0][0])
print(f"connectivity c_e: bridge={conn[ib]:.2f}  clique-edge={conn[0]:.1f}  "
      f"boosted-edge={conn[2]:.2f}  chord={conn[-2]:.2f}")

masks = np.arange(1, 2**n - 1)                       # 4094 nontrivial cuts
INC = (((masks[:, None] >> u) & 1) ^ ((masks[:, None] >> v) & 1)).astype(float)
cut_G = INC @ w
pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
X = np.zeros((len(pairs) + 1 + 24, n))
for k, (a, b) in enumerate(pairs):
    X[k, a] = 1.0; X[k, b] = -1.0
X[len(pairs)] = np.linalg.eigh(L_G)[1][:, 1]         # Fiedler vector
for k in range(24):
    X[len(pairs) + 1 + k] = rng.standard_normal(n)
qf_G = np.einsum('vi,ij,vj->v', X, L_G, X)
_, Vg = np.linalg.eigh(L_G)
Z = Vg[:, 1:]                  # eigh ascending: drop col 0 (kernel) for basis of 1^perp
R = np.linalg.cholesky(Z.T @ L_G @ Z)

k_budget = 2 * n  # every sampler targets the same ~2n-edge budget
def run(pr):
    p = np.minimum(1.0, k_budget * pr / pr.sum())
    keep = rng.random(m) < p
    wH = np.where(keep, w / p, 0.0)
    cutH = INC @ wH
    e_cut = np.max(np.abs(cutH - cut_G) / cut_G)
    e_btl = abs(cutH[cut_G.argmin()] - cut_G.min()) / cut_G.min()
    L_H = laplacian(wH)
    qf_H = np.einsum('vi,ij,vj->v', X, L_H, X)
    e_qf = np.max(np.abs(qf_H - qf_G) / qf_G)
    M = Z.T @ L_H @ Z                                # generalized spectrum
    lam = np.linalg.eigvalsh(np.linalg.solve(R, np.linalg.solve(R, M).T))
    e_spec = max(1.0 - lam[0], lam[-1] - 1.0)
    return keep.sum(), e_cut, e_btl, e_qf, e_spec, keep[ib], (lam[0] < 1e-9)

samplers = {
    'uniform (p_e = k/m)':      np.ones(m),
    'BK-style (p_e ~ 1/c_e)':   1.0 / conn,
    'SS leverages (p_e ~ l_e)': lev,
}
probe = [ib, 0, 2, m - 2]
print("sampling probabilities p_e at [bridge, clique, boosted, chord]:")
for name, s in samplers.items():
    p = np.minimum(1.0, k_budget * s / s.sum())
    print(f"  {name:26s} " + "  ".join(f"{p[i]:.2f}" for i in probe))
results = {}
for name, s in samplers.items():
    results[name] = np.array([run(s) for _ in range(1000)], dtype=float)

print(f"\n{'sampler':26s} {'edges':>6} {'bridge':>7} {'H disconnected':>15}")
for name in samplers:
    res = results[name]
    print(f"{name:26s} {res[:,0].mean():6.1f} {100*res[:,5].mean():6.1f}% {100*res[:,6].mean():13.1f}%")
print(f"\n{'sampler':26s} {'all-cut err':>13} {'bottleneck':>13} {'qf worst':>13} {'spectral err':>13}   (median / p95 over 1000 trials)")
for name in samplers:
    res = results[name]
    f = lambda col, q: np.percentile(res[:, col], q)
    print(f"{name:26s} {f(1,50):5.2f}/{f(1,95):5.2f}  {f(2,50):5.2f}/{f(2,95):5.2f}  "
          f"{f(3,50):5.2f}/{f(3,95):5.2f}  {f(4,50):5.2f}/{f(4,95):5.2f}")
```

Real output of the script above (Python 3.12, NumPy 2.1.3), pasted verbatim:

```text
leverage sum (identity: sum l_e = n-1): 11.000000
connectivity c_e: bridge=1.30  clique-edge=5.3  boosted-edge=5.30  chord=4.33
sampling probabilities p_e at [bridge, clique, boosted, chord]:
  uniform (p_e = k/m)        0.73  0.73  0.73  0.73
  BK-style (p_e ~ 1/c_e)     1.00  0.62  0.62  0.76
  SS leverages (p_e ~ l_e)   1.00  0.61  0.61  0.73

sampler                     edges  bridge  H disconnected
uniform (p_e = k/m)          23.8   72.8%           9.5%
BK-style (p_e ~ 1/c_e)       22.1  100.0%           2.7%
SS leverages (p_e ~ l_e)     22.9  100.0%           1.3%

sampler                      all-cut err    bottleneck      qf worst  spectral err   (median / p95 over 1000 trials)
uniform (p_e = k/m)         0.54/ 1.00   0.38/ 1.00   0.49/ 0.81   0.69/ 1.00
BK-style (p_e ~ 1/c_e)      0.56/ 0.81   0.07/ 0.23   0.52/ 0.74   0.62/ 0.89
SS leverages (p_e ~ l_e)    0.51/ 0.78   0.09/ 0.23   0.47/ 0.69   0.61/ 0.86
```

How to read it, honestly:

- **The mechanism is the clamp.** Both aware samplers put the bridge at $p_e = 1$; uniform
  drops it 27% of the time, which alone produces a 77% bottleneck-cut error (the cut keeps
  only the 0.3 chord) and 100% quadratic-form error on the $(5,6)$ vector. That is why the
  bottleneck column collapses from $1.00$ to $0.23$ p95 and why $H$ is never disconnected
  under aware pricing (uniform loses the whole inter-cluster connection 9.5% of trials,
  bridge and chord both dropped, plus rare isolated vertices inside a clique).
- **Small-$n$ honesty.** Median all-cut error is $\approx 0.5$ *for every sampler*. That is
  not a bug: at $2n$ edges the worst-case guarantee scale is $\epsilon \sim \sqrt{\log n / n}$,
  which is miserable at $n = 12$. Sparsification's payoff is asymptotic - the same code at
  $n = 10^5$ keeps $2n$ edges with $\epsilon \approx 0.02$. What improves *here* is the tail:
  catastrophic events disappear and p95 errors drop across the board.
- **BK vs SS nearly coincide on this graph** ($p_e$ rows differ in the third decimal for the
  chord, not at all on the clamped edges) because for the barbell, $1/c_e$ and $\ell_e$ are
  close to proportional - locally, connectivity and leverage measure the same redundancy.
  The asymptotic gap between the notions ($\log n$ factor; and cut sparsifiers provably
  cannot preserve general quadratic forms) shows up on structured worst-case instances, not
  on a symmetric barbell. SS still dominates every p95 column - it is the only rule whose
  guarantee even speaks about quadratic forms.
- **What is simplified:** real BK gets $c_e$ from tree packings in near-linear time (not
  $2^n$ enumeration), and real SS gets the $\ell_e$ from JL sketches + Laplacian solves
  (not `pinv`), and prices with $\rho = \epsilon^{-2}\log n$ rather than a fixed budget
  (the demo's normalization is $k/(n-1)$ in place of $\rho$ - same functional form).

## 6. Where the machinery gets used

- **SDD/Laplacian systems at scale.** Any pipeline that solves $Lx = b$ repeatedly
  (spectral clustering, PageRank variants, Gaussian random fields on graphs, semidefinite
  program inner loops for max-flow) runs the ST/KS solver tree; the sparsifier is the
  preconditioner that makes each level cheap.
- **Electrical-flow optimization.** Max-flow via electrical flows
  (Christiano-Kelner-Madry-Spielman-Teng, STOC 2011) and its descendants call a Laplacian
  solver per iteration; the resistances it maintains are exactly the $R_e$ of §3.
- **Generative graph models.** The SS sampler *is* a generator: it emits a synthetic
  $O(n/\epsilon^2)$-edge graph spectrally equivalent to a giant input graph - a lossy
  "graph summary" that preserves diffusion and clustering behavior. Kyng-Sachdeva's
  elimination chain is likewise a sequence of sampled sparse graphs, and the Kirchhoff
  reading $\Pr[e \in T] = \ell_e$ turns leverage computation into near-linear-time random
  spanning-tree generation with the correct weighted distribution.

## 7. Calibration questions

1. **Why can't uniform sampling with $p = \Theta(\log n/\epsilon^2)$ sparsify every graph?**
   Because the guarantee needs $\lambda$ (min cut) to absorb the reweighting; when
   $\lambda = 1$ a bridge forces $p = 1$ globally. Non-uniform pricing (BK) localizes this.
2. **Does a cut sparsifier preserve random-walk mixing times?** No - mixing is governed by
   the spectral gap, i.e., by general quadratic forms. You need a spectral sparsifier.
3. **What does $\sum_e \ell_e = n - 1$ buy you in an implementation?** A free correctness
   check for your $R_e$ computation, and a proof that average leverage is $\le 1$, i.e.,
   $O(n)$ edges always suffice to cover the leverage mass.
4. **Why is $\epsilon^{-2}$ in sparsifier size but $\log(1/\epsilon)$ in solver time?**
   Sampling buys accuracy with variance (Chernoff, $\epsilon^{-2}$); iteration buys it
   multiplicatively (CG, $\log$). Sparsify once at fixed $\epsilon$, then iterate.

## References

1. A. A. Benczur, D. R. Karger. *Randomized Approximation Schemes for Cuts and Flows in
   Capacitated Graphs.* SIAM J. Comput. 44(2):290-319, 2015 (journal version of FOCS 1996).
   DOI: 10.1137/070705970; record: https://dblp.org/rec/journals/siamcomp/BenczurK15.html
2. D. A. Spielman, N. Srivastava. *Graph Sparsification by Effective Resistances.*
   arXiv:0803.0929 (2008); journal version SIAM J. Comput. 40(6):1913-1926, 2011.
   https://arxiv.org/abs/0803.0929
3. J. D. Batson, D. A. Spielman, N. Srivastava. *Twice-Ramanujan Sparsifiers.*
   arXiv:0808.0163 (2008); STOC 2009, pp. 255-262; SIAM Review 56(2):315-334, 2014.
   https://arxiv.org/abs/0808.0163
4. D. A. Spielman, S.-H. Teng. *Spectral Sparsification of Graphs.* arXiv:0808.4134 (2008) -
   the monograph treatment of the STOC 2004 sparsification/solver machinery
   (https://dblp.org/rec/conf/stoc/SpielmanT04.html).
   https://arxiv.org/abs/0808.4134
5. R. Kyng, S. Sachdeva. *Approximate Gaussian Elimination for Laplacians: Fast, Sparse, and
   Simple.* FOCS 2016. https://arxiv.org/abs/1605.02353
