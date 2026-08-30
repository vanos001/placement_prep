# SMAWK: Row Minima in Totally Monotone Matrices

Many dynamic programs reduce, layer by layer, to one primitive: given an `n x m`
matrix whose entries come from an oracle, report one minimizing column index per
row. Evaluated naively this costs `n*m` oracle calls, but for the matrices produced
by concave DP cost functions the SMAWK algorithm of Aggarwal, Klawe, Moran, Shor,
and Wilber needs only `O(n + m)` calls. It is the fastest known way to exhaust a DP
layer whose transition cost is Monge, complementing the divide-and-conquer
optimization in [DP Optimization Techniques](dp-optimization.md) and the convex hull
trick in [Convex Hull Trick](convex-hull-trick.md). See
[Ch 86: DP Optimization](../chapters/ch86-dp-optimization.md) for where such layers
appear, and [Aliens Trick](aliens-trick.md) for the parametric alternative when the
segment count itself is constrained.

---

## 1. The Row-Minima Problem

**Oracle model.** The matrix is not stored; a procedure `A(i, j)` returns one entry,
and the only cost that matters is the number of calls. For a DP layer

```text
dp[j] = min over i of ( dp[i] + w(i, j) )
```

the transition surface is the matrix: rows index predecessors `i`, columns index
targets `j` (or the transpose; Monge-ness survives transposition). One SMAWK pass
per layer pins down every optimal predecessor. A naive scan touches all `n*m` cells;
for `n = 10^5` states that is `10^10` calls, while SMAWK performs about 10-12
evaluations per row on the quadratic cost of Section 5.

```text
        j = 0   1   2   3   4            one argmin per row
    i=0 [ .   .  [x]  .   . ]   --->  argmin(0) = 2
    i=1 [ .  [x]  .   .   . ]   --->  argmin(1) = 1
    i=2 [ .   .  [x]  .   . ]   --->  argmin(2) = 2
    i=3 [ .   .   .  [x]  . ]   --->  argmin(3) = 3
              ^ totally monotone: these column indices never decrease
```

## 2. Monge Matrices and Total Monotonicity

**Monge (quadrangle inequality).** `A` is Monge if for all `i < i'` and `j < j'`:

```text
A[i][j] + A[i'][j'] <= A[i][j'] + A[i'][j]
```

i.e. the advantage of an earlier column over a later one, `A[.][j] - A[.][j']`,
never decreases as the row index grows. This is exactly the quadrangle inequality
that Knuth-style interval DP requires (see [dp-optimization.md](dp-optimization.md)).

**Totally monotone (TM).** `A` is totally monotone if for `i < i'` and `j < j'`:

```text
A[i][j'] < A[i][j]   implies   A[i'][j'] < A[i'][j]
```

If a later column strictly beats an earlier one in some row, it beats it in every
deeper row. With ties broken toward the leftmost index, this is precisely the
property the argmin bookkeeping needs.

**Monge implies TM.** Monge says `A[i][j'] - A[i][j] <= A[i'][j'] - A[i'][j]`: the
later column's advantage is non-decreasing down the rows, so once it wins strictly
at row `i` it wins at every `i' > i`. Every Monge matrix is therefore TM, and TM
survives submatrices, row/column deletion, and transposition.

**Monotone argmins.** In a TM matrix the leftmost argmin column is non-decreasing
from row to row; both the recursion and the interleave step rely on this.

**Worked cost.** For prefix sums `S` and `w(i, j) = (S[j] - S[i])^2 + C` with `S`
strictly increasing, the Monge defect is

```text
w(i,j) + w(i',j') - w(i,j') - w(i',j) = -2 (S[i'] - S[i]) (S[j'] - S[j]) <= 0
```

so the matrix is Monge, hence TM, hence SMAWK-eligible.

## 3. The SMAWK Algorithm

Aggarwal, Klawe, Moran, Shor, and Wilber, *Geometric applications of a
matrix-searching algorithm*, Algorithmica 1987. The algorithm inspects `O(n + m)`
cells, uses only comparisons, and assumes nothing beyond total monotonicity.

### Step 1: REDUCE -- prune columns with a stack scan

Walk the columns left to right keeping a stack of survivors. An incoming column `c`
pops the top `s` whenever the test row -- the row whose position equals the current
stack size minus one -- strictly prefers `c`. Push `c` only if the stack still has
room below the row count.

```text
Matrix A[i][j] = 3 - j  (every row prefers the rightmost column)

      c0  c1  c2  c3
r0 [   3   2   1   0 ]
r1 [   3   2   1   0 ]
r2 [   3   2   1   0 ]

scan c0: stack [0]
scan c1: test r0: A[0][0]=3 > A[0][1]=2 -> pop 0; push 1 -> stack [1]
scan c2: test r0: A[0][1]=2 > A[0][2]=1 -> pop 1; push 2 -> stack [2]
scan c3: test r0: A[0][2]=1 > A[0][3]=0 -> pop 2; push 3 -> stack [3]

final stack [3]: the argmin of every row is column 3 -- nothing was lost
```

Every pop and every skipped push is safe:

* A popped column lost a strict comparison at its own stack row, so by TM it loses
  in every deeper row, and the column one stack slot below it already beat or tied
  it in every shallower row. Nobody's leftmost argmin is popped.
* A column skipped because the stack is full is dominated, in every row, by the
  current top, which sits earlier. It cannot be a leftmost argmin.

After the scan the stack holds at most `min(n, m)` columns and still contains every
row's leftmost argmin.

### Step 2: recurse on even rows, interleave odd rows

```text
n rows, m cols
      |
      v  REDUCE (stack scan) -> stack S, |S| <= min(n, m), all argmins kept
      |
      +-- recurse on even rows 0, 2, 4, ... against S
      |
      +-- interleave: odd row r scans only the stack columns between
          argmin(rows[r-1]) and argmin(rows[r+1])  (monotone argmins bound it)
```

The odd rows are cheap: monotone argmins bracket each odd row's argmin between the
already-known argmins of its neighboring even rows, and the union of the bands is
linear in the column count. The row count halves at every level while per-level work
stays linear, giving `O(n + m)` evaluations for `n <= m` and
`O(m * (1 + log(n/m)))` in general.

### Pseudocode

```text
function solve(rows, cols):                  # fills out[r] = argmin column
    if |rows| = 1:                           # base case: one scan
        out[rows[0]] = argmin over cols
        return
    stack = []
    for c in cols (left to right):           # REDUCE
        while stack non-empty and
              A(rows[|stack|-1], stack.top) > A(rows[|stack|-1], c):
            stack.pop()
        if |stack| < |rows|:
            stack.push(c)
    solve(rows at even positions, stack)     # recurse
    for each odd position t in rows:         # interleave
        lo = out[rows[t-1]]
        hi = out[rows[t+1]]  if a next even row exists  else stack.last
        out[rows[t]] = argmin of stack columns in [lo, hi]
```

Strict comparisons everywhere keep the earliest column on equality, so the output
matches a left-to-right brute-force scan exactly.

## 4. Comparison with Other DP-Speedup Tools

| Technique | Problem shape | Requirement | Evaluations / time | Typical use |
| --- | --- | --- | --- | --- |
| SMAWK | `n x m` cost matrix per DP layer | total monotonicity (Monge suffices) | `O(n + m)` oracle calls | concave 1D/1D layers, geometry, line breaking |
| Divide-and-conquer optimization | `dp[i][j] = min dp[i-1][k] + C(k, j)` | argmin monotone in `j` for fixed `i` | `O(n*m*log m)` comparisons | pairwise DP layers, weaker property than TM |
| Knuth optimization | interval DP over split points `k` | quadrangle inequality + monotone optima | `O(n^2)` time | optimal BST, matrix chain, interval merging |
| Naive layer scan | any matrix | none | `O(n*m)` calls | baseline when no structure is available |

Divide-and-conquer optimization needs only monotone argmins but pays a log factor
and requires the previous layer; SMAWK needs the full TM property but is linear and
layer-independent. Knuth optimization lives on interval matrices where the row and
column sets differ in kind. When the cost is concave the views meet: a 1D/1D layer
solved by divide-and-conquer in `O(n log n)` drops to `O(n)` with SMAWK.

## 5. Applications

**Concave-cost 1D/1D DP.** With prefix sums `S[j]` and cost
`w(i, j) = (S[j] - S[i])^2 + C`, the layer `dp[j] = min over i < j of dp[i] + w(i, j)`
penalizes squared deviation from a segment mean plus a fixed segment overhead. This
is the objective behind optimal piecewise-constant segmentation, variance-minimizing
data splitting, and the concave least-weight subsequence problem of Wilber (1988).
The cost is Monge by Section 2, so each layer costs `O(n)` oracle calls applied to
the transposed transition surface, versus `O(n^2)` naively.

**Optimal segmentation.** Tuning `C` to a target segment count solves constrained
piecewise fitting; paired with the parametric sweep in
[Aliens Trick](aliens-trick.md) it handles "at most k segments" without a `k * n^2`
table.

**Sequence alignment and RNA structure.** Alignment matrices carry a shifted Monge
property (Monge after a row-dependent shift), the online DP for RNA secondary
structure of Larmore and Schieber (1991) is built on SMAWK-style matrix searching,
and Russo (2012) catalogs the Monge structure of alignment scores.

**Computational geometry.** The original paper applies the technique to farthest
points from convex polygon vertices and minimum-area enclosing polygons; optimal
line breaking (paragraph justification) is a concave-cost 1D/1D DP solved the same
way.

## 6. Python Demo

The script implements SMAWK with a counting oracle, runs it on the
`w(i, j) = (S[j] - S[i])^2 + C` matrix for `n = 64, 256, 1024`, checks every argmin
against brute force, and reports evaluation counts. A stress round with randomized
sizes and offsets guards against tie-handling bugs.

```python
import random


class Cost:
    def __init__(self, S, C):
        self.S, self.C, self.evals = S, C, 0

    def cell(self, i, j):  # oracle: w(i, j) = (S[j] - S[i])**2 + C
        self.evals += 1
        d = self.S[j] - self.S[i]
        return d * d + self.C


def smawk_argmins(n, m, cost):
    """Argmin column of every row of an n x m totally monotone matrix."""
    out = [0] * n

    def solve(rows, cols):
        if len(rows) == 1:
            r = rows[0]
            best, bval = cols[0], cost.cell(r, cols[0])
            for c in cols[1:]:
                v = cost.cell(r, c)
                if v < bval:
                    best, bval = c, v
            out[r] = best
            return
        stack = []  # REDUCE: surviving columns
        for c in cols:
            while stack:
                r = rows[len(stack) - 1]
                if cost.cell(r, stack[-1]) > cost.cell(r, c):
                    stack.pop()
                else:
                    break
            if len(stack) < len(rows):
                stack.append(c)
        solve(rows[::2], stack)  # recurse on even rows
        for t in range(1, len(rows), 2):  # interleave odd rows
            r = rows[t]
            lo = out[rows[t - 1]]
            hi = out[rows[t + 1]] if t + 1 < len(rows) else stack[-1]
            band = [c for c in stack if lo <= c <= hi]
            best, bval = band[0], cost.cell(r, band[0])
            for c in band[1:]:
                v = cost.cell(r, c)
                if v < bval:
                    best, bval = c, v
            out[r] = best

    solve(list(range(n)), list(range(m)))
    return out


def brute_argmins(S, C):
    out = []
    for i in range(len(S)):
        vals = [(S[j] - S[i]) ** 2 + C for j in range(len(S))]
        out.append(vals.index(min(vals)))
    return out


def make_S(n, rng):
    S = [0]
    for _ in range(n - 1):
        S.append(S[-1] + rng.randint(1, 9))
    return S


print("SMAWK row minima on w(i,j) = (S[j]-S[i])^2 + C, S strictly increasing")
print("%6s %8s %12s %12s %9s %7s %5s" %
      ("n", "C", "smawk evals", "brute n^2", "evals/n", "ratio", "ok"))
for n in (64, 256, 1024):
    S = make_S(n, random.Random(1000 + n))
    cost = Cost(S, 7)
    got = smawk_argmins(n, n, cost)
    ok = "OK" if got == brute_argmins(S, 7) else "MISMATCH"
    print("%6d %8d %12d %12d %9.2f %7.5f %5s" %
          (n, 7, cost.evals, n * n, cost.evals / n, cost.evals / (n * n), ok))

passed = 0
for t in range(5):
    rng = random.Random(7000 + t)
    n = rng.randint(33, 61)
    S = make_S(n, rng)
    C = rng.randint(0, 20)
    if smawk_argmins(n, n, Cost(S, C)) == brute_argmins(S, C):
        passed += 1
print("stress: %d/5 random instances (n=33..61, random C) matched brute force"
      % passed)
```

Output (real run, Python 3.11):

```text
SMAWK row minima on w(i,j) = (S[j]-S[i])^2 + C, S strictly increasing
     n        C  smawk evals    brute n^2   evals/n   ratio    ok
    64        7          663         4096     10.36 0.16187    OK
   256        7         2765        65536     10.80 0.04219    OK
  1024        7        11203      1048576     10.94 0.01068    OK
stress: 5/5 random instances (n=33..61, random C) matched brute force
```

The `evals/n` column stays near 11 while `n` grows 16-fold -- the linear constant in
action -- and the ratio against brute force falls like `1/n`, from 0.16 at `n = 64`
to 0.011 at `n = 1024`. At `n = 1024` SMAWK touches 11,203 cells where the naive
scan touches 1,048,576.

## 7. References

1. A. Aggarwal, M. M. Klawe, S. Moran, P. Shor, R. Wilber. *Geometric applications
   of a matrix-searching algorithm.* Algorithmica 2(1-4):195-208, 1987.
   [doi:10.1007/BF01840359](https://doi.org/10.1007/BF01840359)
2. R. Wilber. *The concave least-weight subsequence problem revisited.* Journal of
   Algorithms 9(3):418-425, 1988.
   [doi:10.1016/0196-6774(88)90032-6](https://doi.org/10.1016/0196-6774(88)90032-6)
3. L. L. Larmore, B. Schieber. *On-line dynamic programming with applications to the
   prediction of RNA secondary structure.* Journal of Algorithms 12(3):490-515, 1991.
   [doi:10.1016/0196-6774(91)90016-R](https://doi.org/10.1016/0196-6774(91)90016-R)
4. Z. Galil, R. Giancarlo. *Speeding up dynamic programming with applications to
   molecular biology.* Theoretical Computer Science 64(1):107-118, 1989.
5. L. M. S. Russo. *Monge properties of sequence alignment.* Theoretical Computer
   Science 423:30-49, 2012.
6. D. Eppstein. *The SMAWK algorithm and totally monotone matrices.* Lecture notes,
   UC Irvine, 2007.

Cross-references: [DP Optimization Techniques](dp-optimization.md) covers Knuth
optimization and the Monge/SMAWK interface; [Convex Hull Trick](convex-hull-trick.md)
handles the linear-cost special case in `O(1)` amortized per transition;
[Aliens Trick](aliens-trick.md) pairs with SMAWK for segment-count constraints.
