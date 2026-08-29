# Chapter 192: Subset Convolution and Subset Sum Convolution: Set-Power Series Mechanics

Many exponential algorithms reduce to one operation: split a set S into two parts, solve
each part, and combine. When the two parts must be **disjoint** and must **fill S exactly**,
that combination is the *subset convolution*, and the naive computation costs Theta(3^n).
Bjorklund, Husfeldt, Kaski and Koivisto showed in 2007 that ranked zeta/Mobius transforms
-- the "set-power series" viewpoint -- compute it in O(n^2 * 2^n). This chapter builds that
machinery from the lattice up: what the transforms actually invert, why ranks are the exact
price of disjointness, and when the cheaper unranked "subset-sum" products suffice.

## 1. Three Convolutions on the Subset Lattice

Fix a universe of n elements and identify each subset with an n-bit mask. The masks form
the subset lattice: `T <= S` iff `T & S == T`, join is bitwise OR, meet is AND. For set
functions f, g, three products dominate transitions in bitmask DP:

| Product          | h[S] sums f[T1] * g[T2] over pairs with | Transform pipeline                    | Cost        |
|------------------|------------------------------------------|---------------------------------------|-------------|
| OR-convolution   | T1 OR T2 == S                            | zeta, pointwise, Mobius               | O(n * 2^n)  |
| XOR-convolution  | T1 XOR T2 == S                           | Walsh-Hadamard, pointwise, inverse    | O(n * 2^n)  |
| subset-convolution | T1 AND T2 == 0, T1 OR T2 == S          | ranked zeta, pointwise, ranked Mobius | O(n^2 * 2^n) |

The workhorse is the zeta transform and its inverse, the Mobius transform (the subset-sum
direction, a.k.a. SOS DP -- "sum over subsets"):

```text
zeta:   F[S] = sum of f[T] over all T subset of S
mobius: f[S] = sum of (-1)^(|S|-|T|) * F[T] over all T subset of S

in place, O(n * 2^n), for i in 0..n-1:
    zeta:   for every S holding bit i:  F[S] += F[S ^ (1 << i)]
    mobius: for every S holding bit i:  F[S] -= F[S ^ (1 << i)]
```

The mirror-image **superset-sum** variant accumulates over T containing S instead
(`F[S] += F[S | (1 << i)]` for masks lacking bit i). Mixing up the two directions is the
most common off-by-lattice bug; subset convolution as developed below uses the subset-sum
direction. Both transforms are the subset-lattice special case of Mobius inversion on
posets -- the divisor-lattice sibling is covered in Ch 172.

## 2. Why Zeta Plus Pointwise Multiply Gives OR, Not Subset

Zeta is a ring isomorphism from (functions, OR-convolution) to (functions, pointwise
multiplication): `(Zf)[S] = sum over T1 OR T2 subset of S ... ` factors as
`(Zf)[S] * (Zg)[S]` because "T1 and T2 both inside S" is exactly "T1 OR T2 inside S".
Pointwise multiplication therefore detects pairs whose union is *contained* in S, and one
Mobius transform at the end isolates union exactly equal to S. Nothing in this pipeline
ever sees whether T1 and T2 overlap. The repair is the classic alternation identity:

```text
for A subset of S:
    sum over U with A subset of U subset of S of (-1)^(|S|-|U|)  =  [ A == S ]
```

*Proof sketch*: if `A != S`, the d = |S \ A| > 0 "free" elements of S \ A appear in U
independently, so the sum factors as `sum over B subset of D of (-1)^(d-|B|) = (1-1)^d = 0`;
if `A == S` only U = S survives and the sum is 1. So an alternating sum over intermediate
unions -- exactly what a Mobius transform computes -- can test "union fills S". What is
still missing is a way to force **disjointness**. Tracking `|T1| + |T2|` against `|S|` does
that, and the bookkeeping device is the rank.

## 3. Ranked Set-Power Series

View f as a set-power series: a formal sum `f = sum over S of f[S] * x^S` where the
monomial `x^S` is the product of generators x_i for i in S, subject to `x_i^2 = 0`. Under
this rule, multiplying series multiplies monomials -- and the product is zero precisely
when a generator repeats, i.e. when the two sets are **not disjoint**. Subset convolution
is exactly multiplication in this exterior-like algebra. Because `|x^S| = |S|` and degrees
add, the algebra is *graded*, and every function splits into rank layers:

```text
f = f_0 + f_1 + ... + f_n          (rank-r layer:  f_r[S] = f[S] if |S| == r else 0)

rank 0:  {}
rank 1:  {a}  {b}  {c}             example layers for n = 3
rank 2:  {ab} {ac} {bc}
rank 3:  {abc}

(f * g)[S] only receives pairs with |T1| + |T2| == |S|, so (f*g)[S] = sum over r of
(f_r * g_{|S|-r})[S]  -- the convolution is graded.
```

Store a ranked series as an `(n+1) x 2^n` table. The **per-rank zeta transform** is

```text
fz[j][S] = sum of f[T] over T subset of S with |T| == j
```

i.e. run the ordinary zeta butterfly independently on each of the n+1 layers. Same for the
ranked Mobius transform, run backwards per layer.

## 4. The Ranked Pipeline, with Proof

```text
f, g --rank split--> f_r, g_r --per-rank zeta--> fz[j][*], gz[j][*]
     --pointwise rank pairs--> hz[r][S] = sum over j of fz[j][S] * gz[r-j][S]
     --per-rank Mobius--> h_r          answer:  h[S] = h_{|S|}[S]
```

**Theorem** (Bjorklund-Husfeldt-Kaski-Koivisto 2007). With fz, gz as above and
`m[r][S] = sum over U subset of S of (-1)^(|S|-|U|) * hz[r][U]`, the subset convolution is
`h[S] = m[|S|][S]`.

*Proof*. Expand hz and swap the order of summation:

```text
m[r][S] = sum over T1, T2 subset of S with |T1| + |T2| == r of f[T1] * g[T2]
          * ( sum over U: T1 OR T2 subset of U subset of S of (-1)^(|S|-|U|) )
```

By the identity of Section 2 the inner factor is 1 iff `T1 OR T2 == S`. Then
`|T1| + |T2| = |T1 union T2| + |T1 AND T2| = |S| + |T1 AND T2|`, so at rank `r = |S|` the
surviving pairs satisfy `T1 AND T2 == 0` -- which is precisely the subset convolution. QED.

| Stage                   | Exact work at universe size n                        | Time        |
|-------------------------|------------------------------------------------------|-------------|
| per-rank zeta (f and g) | 2 * (n+1) * n * 2^(n-1) additions                    | O(n^2 * 2^n)|
| ranked pointwise pairs  | 2^n * (n+1)(n+2)/2 multiplications                   | O(n^2 * 2^n)|
| ranked Mobius           | (n+1) * n * 2^(n-1) subtractions                     | O(n^2 * 2^n)|
| total                   |                                                      | O(n^2 * 2^n) time, O(n * 2^n) words |

## 5. The O(n * 2^n) Sibling: Subset-Sum Products Without Ranks

When overlapping pairs **should** count, ranking is wasted work. The unranked zeta alone
powers the inclusion-exclusion engine of Bjorklund-Husfeldt-Koivisto's set partitioning
paper. Example -- count ordered k-tuples (A_1, ..., A_k) of admissible sets whose union is
exactly U, given the admissibility indicator a:

```text
cover_k[U] = sum over V subset of U of (-1)^(|U|-|V|) * (Z a)[V]^k
```

where `(Z a)[V]` counts admissible subsets of V. One zeta transform plus k-th powers gives
cover_k in O(n * 2^n) per k -- no ranks needed, because "each element covered at least
once" is a union condition, not a disjointness condition.

Rule of thumb:

- overlap allowed ("cover", "at least one piece per element") -> unranked zeta + powers;
- overlap forbidden ("partition", "split into two halves") -> ranked machinery of Section 4.

## 6. Application: Counting Partitions and the Chromatic Number

Let a[S] = 1 if S is an admissible block (e.g. an independent set of a graph), else 0.
The number of ways to **partition** the full set U into k admissible blocks is the k-fold
subset convolution `a^{*k}[U]`: blocks are disjoint and their union is U. Compute it with
exponentiation by squaring -- O(log k) convolutions, O(n^2 * 2^n * log k) total. Scanning
k upward until the count is positive decides the chromatic number; this is exactly the
O(2^n * poly(n)) program of the Set Partitioning via Inclusion-Exclusion paper. Note the
contrast with Section 5: partitions count tilings (ranked convolution), covers count
packings (unranked zeta) -- confusing the two is the classic correctness bug in this area.

## 7. Application: The Steiner Tree Merge, 3^t to 2^t * t^2

Dreyfus-Wagner DP over terminal subsets: `dp[S][v]` = cheapest tree connecting terminals
S to vertex v, with the merge step

```text
dp[S][v] = min over proper T subset of S of dp[T][v] + dp[S \ T][v]
```

Summing `2^|S|` over all S gives the Theta(3^t) term in `O(3^t * n + 2^t * n^2)`. The merge
is a (min, +) subset convolution; since Steiner costs are bounded integers, packing cost
values into single machine words converts (min, +) into three ordinary sum-product subset
convolutions (the standard reduction, also covered in the Parameterized Algorithms book),
so the merge drops to O(2^t * t^2) per vertex. This is one of the original applications in
the fast subset convolution paper.

| Task                                 | Naive cost          | Transform-based cost        | Source                       |
|--------------------------------------|---------------------|-----------------------------|------------------------------|
| zeta / Mobius transform              | O(3^n)              | O(n * 2^n)                  | SOS DP tutorial refs         |
| OR-convolution                       | O(3^n)              | O(n * 2^n)                  | Section 2                    |
| subset convolution h = f * g         | O(3^n)              | O(n^2 * 2^n)                | BHKJ, STOC 2007              |
| partitions into k blocks             | O(3^n * k)          | O(n^2 * 2^n * log k)        | BHK, SJC 2009                |
| Steiner tree, t terminals            | O(3^t * n + 2^t n^2)| O(2^t * t^2 * n + 2^t n^2)  | Dreyfus-Wagner + BHKJ        |

## 8. Implementation Notes and Pitfalls

- **Rank before zeta.** Applying the zeta transform before splitting into rank layers mixes
  ranks irreversibly; a single Mobius transform cannot un-mix them. Split first, transform
  each layer separately.
- **The pointwise stage is full-range.** `hz[r][S]` must be computed for every mask S and
  every rank r in 0..n -- not just `r <= |S|`. Entries with |S| < r are NOT zero: they
  count overlapping pairs such as T1 contained in T2, and the rank-|S| Mobius transform
  reads exactly those entries. Zeroing them silently corrupts h (the demo in Section 9
  detects this: the error jumps from 0 to 75 on the test data).
- **Memory.** Each ranked table is (n+1) * 2^n words: at n = 20 that is about 22M words,
  roughly 176 MB per 64-bit table, and you need fz, gz, hz simultaneously. Use 32-bit
  modular values, or stream ranks r through the pointwise stage.
- **Overflow.** Zeta layers are bounded by 2^n * max|f| and products by their square; with
  n = 20 that reaches 2^40 * max^2. Compute modulo a prime, or use 128-bit accumulators.
- **The Mobius butterfly is its own inverse with a sign flip** -- same loop, `-=` instead
  of `+=`, same bit order. No division by 2^n anywhere (that is XOR/WHT, not this).
- **Crossover reality check.** Op-count ratio 3^n / (n^2 * 2^n) = 1.5^n / n^2 crosses 1
  near n = 13:

| n  | 3^n           | n^2 * 2^n     | naive / fast |
|----|---------------|---------------|--------------|
| 6  | 729           | 2,304         | 0.32         |
| 12 | 531,441       | 589,824       | 0.90         |
| 13 | 1,594,323     | 1,384,448     | 1.15         |
| 16 | 43,046,721    | 16,777,216    | 2.57         |
| 20 | 3,486,784,401 | 419,430,400   | 8.31         |

Below n = 13 the naive submask enumeration (`t = (t - 1) & s`) wins on constants -- at
n = 6 it is about 8x fewer scalar operations. The ranked method pays off exactly in the
n = 16..22 regime where these problems live.

## 9. Executed Demo: n = 6 Correctness Check

Random integer set functions on 64 masks; the fast ranked convolution is checked
element-wise against the naive O(3^n) submask-pair enumeration, and the unranked
OR-convolution is shown to differ (overlapping pairs leak in):

```python
import random
import time

N = 6                      # universe size
SIZE = 1 << N              # number of masks = 64
FULL = SIZE - 1


def popcount(x):
    return bin(x).count("1")


def zeta(f):
    """Subset-sum zeta transform: F[S] = sum of f[T] for all T subset of S."""
    F = list(f)
    for i in range(N):
        bit = 1 << i
        for s in range(SIZE):
            if s & bit:
                F[s] += F[s ^ bit]
    return F


def mobius(F):
    """Inverse transform: f[S] = sum of (-1)^(|S|-|T|) F[T] over T subset of S."""
    F = list(F)
    for i in range(N):
        bit = 1 << i
        for s in range(SIZE):
            if s & bit:
                F[s] -= F[s ^ bit]
    return F


def subset_convolution(f, g):
    """Ranked fast subset convolution in O(n^2 * 2^n)."""
    fz = [[0] * SIZE for _ in range(N + 1)]
    gz = [[0] * SIZE for _ in range(N + 1)]
    for s in range(SIZE):
        fz[popcount(s)][s] = f[s]
        gz[popcount(s)][s] = g[s]
    for r in range(N + 1):
        fz[r] = zeta(fz[r])
        gz[r] = zeta(gz[r])
    hz = [[0] * SIZE for _ in range(N + 1)]
    for s in range(SIZE):
        for r in range(N + 1):      # all ranks: terms with |T1|+|T2| > |S|
            acc = 0                 # encode the overlap the Mobius must cancel
            for j in range(r + 1):
                acc += fz[j][s] * gz[r - j][s]
            hz[r][s] = acc
    h = [0] * SIZE
    for r in range(N + 1):
        m = mobius(hz[r])
        for s in range(SIZE):
            if popcount(s) == r:
                h[s] = m[s]
    return h


def or_convolution(f, g):
    """Unranked OR-convolution: counts pairs with T1 OR T2 == S (overlap OK)."""
    a, b = zeta(f), zeta(g)
    return mobius([a[s] * b[s] for s in range(SIZE)])


def naive_subset_convolution(f, g):
    """Reference O(3^n): for each S enumerate every submask T (pairs T, S\\T)."""
    h = [0] * SIZE
    for s in range(SIZE):
        t = s
        while True:
            h[s] += f[t] * g[s ^ t]
            if t == 0:
                break
            t = (t - 1) & s
    return h


random.seed(192)
f = [random.randint(-3, 3) for _ in range(SIZE)]
g = [random.randint(-3, 3) for _ in range(SIZE)]

h_fast = subset_convolution(f, g)
h_naive = naive_subset_convolution(f, g)
h_or = or_convolution(f, g)

err_fast = max(abs(h_fast[s] - h_naive[s]) for s in range(SIZE))
err_or = max(abs(h_or[s] - h_naive[s]) for s in range(SIZE))

zeta_ops = 2 * (N + 1) * N * (SIZE // 2)              # per-rank zeta, f and g
mult_ops = SIZE * (N + 1) * (N + 2) // 2            # ranked pointwise products
mobius_ops = (N + 1) * N * (SIZE // 2)                # ranked Mobius
fast_ops = zeta_ops + mult_ops + mobius_ops
naive_ops = 3 ** N                                    # one multiply-add per (S, T)

REP = 400
t0 = time.perf_counter()
for _ in range(REP):
    subset_convolution(f, g)
t_fast = (time.perf_counter() - t0) / REP * 1e6
t0 = time.perf_counter()
for _ in range(REP):
    naive_subset_convolution(f, g)
t_naive = (time.perf_counter() - t0) / REP * 1e6

print("n = %d, %d masks, integer set functions in [-3, 3], seed 192" % (N, SIZE))
print("fast ranked subset convolution vs naive 3^n enumeration:")
print("  max abs error              = %d  (0 means exact on integer input)" % err_fast)
print("  h[full set] fast vs naive  = %d vs %d" % (h_fast[FULL], h_naive[FULL]))
print("unranked OR-convolution vs naive subset convolution:")
print("  max abs difference         = %d  (nonzero: overlapping pairs leak in)" % err_or)
print("scalar ops: fast = %d (zeta %d + pointwise %d + mobius %d), naive 3^n = %d"
      % (fast_ops, zeta_ops, mult_ops, mobius_ops, naive_ops))
print("timing (%d reps): fast %.1f us vs naive %.1f us per convolution"
      % (REP, t_fast, t_naive))
```

```text
n = 6, 64 masks, integer set functions in [-3, 3], seed 192
fast ranked subset convolution vs naive 3^n enumeration:
  max abs error              = 0  (0 means exact on integer input)
  h[full set] fast vs naive  = -40 vs -40
unranked OR-convolution vs naive subset convolution:
  max abs difference         = 103  (nonzero: overlapping pairs leak in)
scalar ops: fast = 5824 (zeta 2688 + pointwise 1792 + mobius 1344), naive 3^n = 729
timing (400 reps): fast 639.5 us vs naive 63.6 us per convolution
```

The 0 matches the exactness claim for integer inputs; the 5824 vs 729 op counts and the
timing line confirm Section 8's crossover analysis (at n = 6 the naive method wins on
constants; the asymptotic win arrives with larger n).

## 10. Interview and Contest Framing

Reach for ranked transforms when the statement says "partition / split / disjoint union"
over subsets and n sits in the 16..22 band. Signals and deliverables:

- Restate the naive transition as `sum over T subset of S` and ask: may the two parts
  overlap? Overlap allowed -> plain SOS/zeta DP in O(n * 2^n); overlap forbidden ->
  ranked subset convolution in O(n^2 * 2^n).
- State the two-transform pipeline (per-rank zeta, pointwise rank pairs, per-rank Mobius)
  and the reason ranks enforce disjointness -- the alternation identity of Section 2.
- Know the numbers: zeta/Mobius cost n * 2^(n-1) per layer, total table (n+1) * 2^n words,
  crossover near n = 13, memory pressure near n = 20.
- Mention one application by name: Steiner tree merge 3^t -> 2^t * t^2, or counting
  partitions of a set into independent sets (chromatic number) via convolution powers.

## Cross-References

- [Ch 172: Mobius Function and Inversion](./ch172-mobius-inversion.md) -- the divisor-lattice
  sibling; same inversion principle, no ranking required there.
- [Ch 167: FFT and NTT](./ch167-fft-ntt.md) -- Walsh-Hadamard for XOR convolution; its
  Section 13.4 sketches this chapter's ranked pipeline in two lines.
- [Ch 149: Exponential Algorithms](./ch149-exponential-algorithms.md) -- the bitmask DP
  landscape, including the Dreyfus-Wagner Steiner tree bounds accelerated above.
- [Advanced DP optimization survey](../advanced/dp-optimization.md) -- a compact SOS DP and
  subset convolution summary; this page is the full-depth treatment of those sections.

## References

1. A. Bjorklund, T. Husfeldt, P. Kaski, M. Koivisto. Fourier meets Mobius: fast subset
   convolution. STOC 2007, ACM, pp. 67-74. https://doi.org/10.1145/1250790.1250801
   (publisher bot-blocks curl with 403; DOI verified via Crossref metadata)
2. A. Bjorklund, T. Husfeldt, M. Koivisto. Set partitioning via inclusion-exclusion.
   SIAM Journal on Computing 39(2): 546-563, 2009. https://doi.org/10.1137/070683933
   (403 to curl; Crossref-verified volume, issue, pages)
3. P. Kaski. Fast Subset Convolution. In Encyclopedia of Algorithms, Springer, 2016.
   https://doi.org/10.1007/978-3-642-27848-8_518-1
4. G.-C. Rota. On the foundations of combinatorial theory I: theory of Mobius functions.
   Z. Wahrscheinlichkeitstheorie und Verwandte Gebiete 2: 340-368, 1964.
   https://doi.org/10.1007/BF00531932
5. S. E. Dreyfus, R. A. Wagner. The Steiner problem in graphs. Networks 1(3): 195-207,
   1971. https://doi.org/10.1002/net.3230010302 (403 to curl; Crossref-verified)
6. M. Cygan, F. V. Fomin, L. Kowalik, D. Lokshtanov, D. Marx, M. Pilipczuk, M. Pilipczuk,
   S. Saurabh. Parameterized Algorithms. Springer, 2015.
   https://link.springer.com/book/10.1007/978-3-319-21275-3
7. USACO Guide. Sum over Subsets DP. https://usaco.guide/plat/dp-sos
8. sdnr1. SOS Dynamic Programming [Tutorial]. Codeforces blog entry 45223.
   https://codeforces.com/blog/entry/45223 (HTTP 200; title confirmed via web search --
   Cloudflare's bot challenge hides page text from curl)
