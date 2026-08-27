# Aliens Trick: Lagrangian Relaxation on DP

Many optimization DPs carry a side constraint "use exactly (or at most)
k pieces / transitions / selected items"; adding a counter dimension
costs a factor of k. The aliens trick (also called WQS binary search or
parametric search) removes the counter dimension, charging a scalar
penalty lambda per used piece, then binary searches on lambda. This page
covers the mechanics tutorials usually skip: why convexity holds, why the
answer is exact even with integer lambda, and the tie-breaking rule that
separates accepted submissions from wrong answers. The survey table in
[DP Optimization](./dp-optimization.md) and the walkthrough in
[Chapter 116](../chapters/ch116-alien-trick-parametric.md) give the recipe; this page goes deeper.

## The Constrained Family

Let F(k) be the minimum cost of a solution using exactly k pieces:
split an array into k contiguous pieces minimizing the sum of squared
piece sums; pick k intervals covering points, minimizing covered length
plus a fixed charge per interval (IOI 2016 "aliens", see References);
spend k balls over n targets maximizing expected payoff (CF 739E). The
plain DP keeps state (position, pieces used) in O(n^2 k) or worse; we
want the k-dependence gone.

## The Penalized Problem and Its Slopes

For a penalty lambda >= 0 define

    G(lambda) = min over k of ( F(k) + lambda * k )

which an ordinary counter-free DP computes: every transition that starts a
new piece adds lambda. If F is convex, the set of optimal k at a given
lambda is a contiguous range and the largest optimal piece count is
non-increasing in lambda -- pieces cost cash, so expensive pieces shrink
the count. G is piecewise linear in lambda; on the stretch where counts
k in [k_lo, k_hi] are optimal, each such k's line touches G.
Write d_k = F(k) - F(k-1) for the increments. Count k is optimal at lambda
exactly when d_k <= -lambda <= d_(k+1), so the "slope band" of count k is
the lambda-interval [-d_(k+1), -d_k]. Integer costs give integer d_k, so
every band contains an integer lambda, and inside the band the identity

    F(k) = G(lambda) - lambda * k

reconstructs the constrained answer from the unconstrained DP.

## Why F Is Convex: The Exchange Argument

For the sum-of-squared-pieces cost with non-negative entries, splitting a
piece with sum s = x + y into two pieces changes the cost by

    x^2 + y^2 - (x + y)^2 = -2 * x * y <= 0,

so more pieces never cost more (F is non-increasing), and the saving 2xy
shrinks as pieces get smaller: the first extra split harvests the fattest
savings. That shrinking marginal saving is exactly convexity: d_k is
non-decreasing in k. The rigorous route for general piece costs is the
quadrangle inequality on w(j, i) (the concave Monge condition) -- the same
hypothesis behind Knuth optimization; see the Knuth section of
[DP Optimization](./dp-optimization.md) for the QI definition. Given QI,
an uncrossing/exchange argument shows F(k-1) + F(k+1) >= 2 * F(k): glue
the optimal (k-1)- and (k+1)-partitions, re-cut each along the other's
boundaries, and QI guarantees a k-partition no worse than their average.
If your cost does not provably satisfy QI, verify convexity numerically --
the demo below checks the increments on every random instance.

## Binary Search on Lambda

Predicate P(lambda) := "the penalized DP with penalty lambda uses >= k
pieces". With the max-count tie-break described below, P is monotone:
true for small lambda, false for large. Search integers in [0, C], C a
bound on the largest slope (the total cost range works).

Why the last True probe is exact: let lam* be the largest lambda with P
true. P true at lam* means some optimal count is >= k, i.e. d_k <= -lam*;
any lambda' > lam* has all optimal counts < k, forcing -lam* <= d_(k+1).
Together: d_k <= -lam* <= d_(k+1), so k is optimal at lam* and
G(lam*) - lam* * k equals F(k) exactly. The binary search always probes
lam* itself (standard last-True invariant), so there is no rounding and
no epsilon: the trick is exact on integers. Complexity is O(T_dp * log C)
with T_dp the penalized DP cost; the transition above is a min over
lines, so the inner DP is O(n) with the convex hull trick -- see
[Convex Hull Trick](./convex-hull-trick.md) -- giving O(n log C) total,
or O(n log C log n) when the inner DP carries a log factor.

## The Tie-Breaking Trap: Counting vs Cost

At one lambda several counts can tie for the optimum; which one the DP
reports depends on tie-breaking, and this is where most wrong submissions
die. Two rules make it bulletproof. First, among minimum-cost solutions
track the MAXIMUM piece count (compare pairs (cost, count)
lexicographically): then "count >= k" is the clean monotone predicate.
With a min-count tie-break a probe can report a small optimal count while
a larger one coexists, and the search walks into the wrong half. Second,
only trust the candidate at the LAST True probe. Candidates from smaller
lambdas are not F(k): at lambda = 0 in the sweep below the formula gives
52 while the true F(3) is 66. Taking a min over all candidates
under-estimates -- this exact bug appeared while preparing the demo on
this page, and the validator caught it.

Flat regions of F (a zero increment d_k = 0) put several counts in one
band; the max-count convention still reports the band's right edge, so
the identity still returns F(k) without uniqueness of the optimum.

## Worked Example

Array a = [3, 1, 4, 1, 5], cost = sum of squared piece sums, gives
F(1..5) = 196, 100, 66, 58, 52 with increments -96, -34, -8, -6:
non-decreasing, so convex. Target k = 3:

```text
pieces (max-count) chosen by G(lambda) for a = [3,1,4,1,5]

  5 |**            lambda = 0
  4 |  *           lambda = 8    (increment d_4 = -8 reaches -lambda)
  3 |   *********  lambda in 9..34   <-- k = 3 band
  2 |            ******          lambda in 35..96
  1 |                  *****     lambda >= 97
    +-------------------------------> lambda
    0   8        34      96
```

Real output of the sweep, the answer check, and the randomized validator
(400 random arrays, every k, against a brute-force layered DP):

```text
a = [3, 1, 4, 1, 5]  F[k] for k=1..5: [196, 100, 66, 58, 52]
increments d[k]: [-96, -34, -8, -6]  convex (non-decreasing): True
lambda sweep (penalty lam added per piece), target k = 3:
lam   G(lam)   pieces(max)   verdict        cand = G - lam*3
0         52      5          pieces >= 3      52
10        96      3          pieces >= 3      66
30       156      3          pieces >= 3      66
33       165      3          pieces >= 3      66
34       168      3          pieces >= 3      66   <- lam*
35       170      2          pieces < 3      -
40       180      2          pieces < 3      -
aliens answer F(3) = 66  brute force F(3) = 66  match: True
randomized validator (arrays len 1..9 of values 0..9, every k):
trials=400 arrays, mismatches=0 ALL OK
```

The cand column shows the trap: at lambda = 0 the formula gives 52; only lam* = 34 yields the true 66.

## Reference Implementation

```python
# Aliens trick: split array (non-negative ints) into exactly k contiguous
# pieces minimizing sum of (piece sum)^2. Validated against brute-force DP.
INF = float('inf')

def solve_penalized(a, lam):
    """Min cost + lam*(#pieces); returns (cost, max_pieces) at optimum."""
    n, pre = len(a), [0]
    for x in a: pre.append(pre[-1] + x)
    cost, count = [0.0] + [INF] * n, [0] * (n + 1)
    for i in range(1, n + 1):
        best, bestc = INF, 0
        for j in range(i):
            if cost[j] < INF:
                c = cost[j] + (pre[i] - pre[j]) ** 2 + lam
                if c < best or (c == best and count[j] + 1 > bestc):
                    best, bestc = c, count[j] + 1   # max-count tie-break
        cost[i], count[i] = best, bestc
    return cost[n], count[n]

def aliens(a, k, lam_hi):
    """Binary search integer lambda. Predicate: pieces(lam) >= k. The LAST
    lambda satisfying it is the right edge of k's slope band, so
    F(k) = G(lam*) - lam* * k exactly (see page text)."""
    lo, hi, best = 0, lam_hi, None
    while lo <= hi:
        lam = (lo + hi) // 2
        g, cnt = solve_penalized(a, lam)
        if cnt >= k:
            best = g - lam * k      # overwrite: last True probe is lam*
            lo = lam + 1
        else:
            hi = lam - 1
    return best

def brute_f(a):
    """F[k] = min cost with exactly k pieces, layered DP. O(n^3)."""
    n, pre = len(a), [0]
    for x in a: pre.append(pre[-1] + x)
    dp = [[INF] * (n + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    for i in range(1, n + 1):
        for k in range(1, i + 1):
            for j in range(k - 1, i):
                if dp[k - 1][j] < INF:
                    v = dp[k - 1][j] + (pre[i] - pre[j]) ** 2
                    dp[k][i] = min(dp[k][i], v)
    return [dp[k][n] for k in range(1, n + 1)]

if __name__ == "__main__":
    a = [3, 1, 4, 1, 5]
    F = brute_f(a)
    d = [F[i] - F[i - 1] for i in range(1, len(F))]
    print("a =", a, " F[k] for k=1..5:", [int(v) for v in F])
    print("increments d[k]:", [int(x) for x in d],
          " convex (non-decreasing):",
          all(d[i] <= d[i + 1] for i in range(len(d) - 1)))
    print("lambda sweep (penalty lam added per piece), target k = 3:")
    print("lam   G(lam)   pieces(max)   verdict        cand = G - lam*3")
    for lam in [0, 10, 30, 33, 34, 35, 40]:
        g, cnt = solve_penalized(a, lam)
        verdict = "pieces >= 3" if cnt >= 3 else "pieces < 3"
        cand = int(g - lam * 3) if cnt >= 3 else "-"
        note = "   <- lam*" if lam == 34 else ""
        print(f"{lam:<4}  {g:>6.0f}      {cnt}          {verdict}      {cand}{note}")
    ans = aliens(a, 3, 200)
    print("aliens answer F(3) =", int(ans), " brute force F(3) =", int(F[2]),
          " match:", ans == F[2])
    print("randomized validator (arrays len 1..9 of values 0..9, every k):")
    import random
    random.seed(34)
    trials, bad = 400, 0
    for _ in range(trials):
        n = random.randint(1, 9)
        arr = [random.randint(0, 9) for _ in range(n)]
        Fb = brute_f(arr)
        db = [Fb[i] - Fb[i - 1] for i in range(1, len(Fb))]
        if any(db[i] > db[i + 1] for i in range(len(db) - 1)):
            print("CONVEXITY VIOLATION", arr, db)   # never fires below
        for k in range(1, n + 1):
            if aliens(arr, k, sum(arr) ** 2 + 1) != Fb[k - 1]:
                bad += 1
                print("MISMATCH", arr, k)
    print(f"trials={trials} arrays, mismatches={bad}",
          "ALL OK" if bad == 0 else "FAILED")
```

The randomized block doubles as a convexity check: no increment violation printed in 400 arrays, matching the QI argument above.

## Failure Modes

- Non-convex F (cost fails QI): the predicate stops being monotone and the
  search can land on a lambda where k is not optimal. Re-check the cost
  hypothesis or fall back to the O(n^2 k) DP.
- Min over candidates instead of last-True: under-estimates (52 vs 66
  above); the identity holds only inside the band.
- Min-count tie-break: a probe may say "3 pieces" while a 5-piece optimum
  coexists at the same cost, flipping the search direction.
- Reconstructing the partition: rerun the penalized DP at the final lambda
  and backtrack the max-count optimum; another lambda gives a valid
  partition of the wrong length.
- "At most k" variants: report the candidate for the largest count <= k
  seen during the search; with maximization objectives F can grow in k,
  so derive every sign on paper first.
- Real-valued lambda needs ~50 bisection steps and epsilon-safe counts;
  prefer integer slopes via cost rescaling.
- Lambda range too small: if lam_hi < -d_k every probe stays True and the
  recorded candidate belongs to some k' > k; the total cost range works.

## References

- [IOI 2016 problem "aliens" (statement, oj.uz mirror)](https://oj.uz/problem/view/IOI16_aliens)
- [IOI 2016 official competition materials (PDF)](https://ioinformatics.org/files/ioi2016.pdf)
- [Codeforces 739E "Gosha is hunting" (two-parameter aliens variant)](https://codeforces.com/contest/739/problem/E)
- [Codeforces 802O "April Fools' Problem (hard?)"](https://codeforces.com/contest/802/problem/O)
- [USACO Guide, module "Lagrangian Relaxation"](https://usaco.guide/adv/lagrange)
