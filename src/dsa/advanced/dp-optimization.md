# DP Optimization Techniques

Beyond the standard divide-and-conquer and CHT covered in [Ch 86](../chapters/ch86-dp-optimization.md) and [Ch 117](../chapters/ch117-monotone-queue-optimization.md), this file covers the full arsenal: Knuth optimization, Aliens trick (parametric search), Li Chao tree, monotone queue optimization, Monge arrays, SMAWK, min-plus convolution, subset convolution (SOS DP), Walsh-Hadamard transform, Möbius transform, and zeta transform.

---

## Knuth Optimization

### Applicable Recurrence

\\[dp[i][j] = \min_{k < j} (dp[i-1][k] + C(k, j))\\]

where $C$ satisfies the **quadrangle inequality** (QI) and **monotonicity of optima**:

\\[\text{opt}[i][j-1] \leq \text{opt}[i][j] \leq \text{opt}[i+1][j]\\]

### Quadrangle Inequality

A cost function $C$ satisfies QI if for all $a \leq b \leq c \leq d$:

\\[C(a, c) + C(b, d) \leq C(a, d) + C(b, c)\\]

This is equivalent to $C$ being **Monge** (see below). Many natural cost functions satisfy this: distance metrics, tree-based costs, and concave/convex costs in many cases.

### Algorithm

```
for i = 1 to n:
    dp[i][i] = 0
    opt[i][i] = i
for len = 2 to n:
    for i = 0 to n - len:
        j = i + len
        dp[i][j] = INF
        for k = opt[i][j-1] to min(opt[i+1][j], j-1):
            val = dp[i][k] + dp[k][j] + C(i, j)
            if val < dp[i][j]:
                dp[i][j] = val
                opt[i][j] = k
```

**Complexity**: $O(n^2)$ instead of $O(n^3)$. The search range for $k$ is narrowed by the monotonicity of optima.

### Classic Application: Optimal BST

Construct a BST for $n$ keys with given access frequencies, minimizing expected search cost. The cost function satisfies QI, so Knuth optimization applies. This is one of the few $O(n^2)$ optimal BST algorithms.

---

## Aliens Trick (Parametric Search)

### Problem

You have a DP where the objective is to **minimize cost** with a constraint on the **number of segments/transitions** (e.g., "partition array into at most $k$ segments minimizing total cost"). The Aliens trick converts the constrained problem into an unconstrained one with a **penalty parameter** $\lambda$.

### Method

1. **Binary search** on a parameter $\lambda > 0$.
2. At each $\lambda$, solve the **unconstrained** DP: $dp[i] = \min(dp[j] + C(j+1, i) - \lambda)$ (subtract $\lambda$ per segment).
3. The unconstrained solution tends to use **more segments** when $\lambda$ is small and **fewer segments** when $\lambda$ is large.
4. Find $\lambda^*$ such that the unconstrained solution uses exactly $k$ segments.
5. The original answer is $\text{unconstrained}(\lambda^*) + k \cdot \lambda^*$.

### Convexity Requirement

The function $f(k) = $ minimum cost using exactly $k$ segments must be **convex** (or concave, depending on the problem). This ensures the binary search works: the number of segments is a non-increasing function of $\lambda$.

### Pseudocode

```
function aliens_trick(k, cost_func):
    lo, hi = 0, BIG  # binary search on lambda
    while hi - lo > EPS:
        lam = (lo + hi) / 2
        segments, total_cost = dp_with_penalty(lam)
        if segments <= k:
            hi = lam   # too few segments, reduce penalty
        else:
            lo = lam   # too many segments, increase penalty
    # Now solve with lo to get the answer
    segments, total_cost = dp_with_penalty(lo)
    return total_cost + k * lo
```

**Complexity**: $O(\log C \cdot T)$ where $C$ is the range of costs and $T$ is the time for the unconstrained DP. If the unconstrained DP is $O(n)$ (e.g., with CHT or monotone queue), total is $O(n \log C)$.

> **Interview Angle**: "Partition an array into exactly $k$ contiguous subarrays minimizing the maximum sum." Use Aliens trick: binary search on the maximum allowed sum (which is the $\lambda$), check if it's possible to partition into $\leq k$ subarrays. $O(n \log S)$ where $S$ is the sum range. This is a special case where the unconstrained DP is greedy.

---

## Convex Hull Trick (CHT)

Covered in [Ch 86](../chapters/ch86-dp-optimization.md). Key advanced points:

### Dynamic CHT (Li Chao Tree)

When lines are added in arbitrary order (not sorted by slope), a standard deque-based CHT fails. The **Li Chao tree** handles arbitrary line insertion and point queries in $O(\log C)$ per operation, where $C$ is the coordinate range.

---

## Li Chao Tree

### Concept

Maintain a set of lines $y = mx + b$. Support: (1) insert a line, (2) query the minimum value at a given $x$-coordinate.

### Structure

A segment tree over the $x$-domain. Each node covers an interval $[l, r]$ and stores the line that is **best at the midpoint** of that interval.

```
function insert(node, line, l, r):
    mid = (l + r) / 2
    at_l = line.eval(l) vs node.line.eval(l)
    at_mid = line.eval(mid) vs node.line.eval(mid)
    at_r = line.eval(r) vs node.line.eval(r)
    if at_mid >= node.line.eval(mid):  # new line worse at mid
        if at_l < node.line.eval(l) or at_r < node.line.eval(r):
            # new line is better at an endpoint
            if at_l < node.line.eval(l):
                insert(node.left, node.line, l, mid)
            else:
                insert(node.right, node.line, mid+1, r)
            node.line = line
    else:  # new line better at mid
        if at_l >= node.line.eval(l) and at_r >= node.line.eval(r):
            # new line dominates everywhere
            node.line = line
        else:
            if at_l > node.line.eval(l):
                insert(node.left, node.line, l, mid)
            else:
                insert(node.right, node.line, mid+1, r)
            node.line = line

function query(node, x, l, r):
    if l == r: return node.line.eval(x)
    mid = (l + r) / 2
    if x <= mid:
        return min(node.line.eval(x), query(node.left, x, l, mid))
    else:
        return min(node.line.eval(x), query(node.right, x, mid+1, r))
```

### Complexity

- Insert: $O(\log C)$ amortized (each insert may traverse $O(\log C)$ nodes).
- Query: $O(\log C)$.
- Space: $O(C)$ in the worst case for the tree, but typically far less.

### Advanced: Line Container (Dynamic CHT)

When $x$-coordinates are queried in increasing order and lines are added in order of decreasing slope, a simple deque works in $O(1)$ amortized (the standard CHT). The Li Chao tree is for the general case.

---

## Divide and Conquer DP

### Applicable Recurrence

\\[dp[i][j] = \min_{k < i} (dp[k][j-1] + C(k, i))\\]

where the optimal $k$ for $(i, j)$ is a non-decreasing function of $i$ (for fixed $j$). This is the **monotone opt** property, weaker than Knuth's requirement.

### Algorithm

```
function compute(dp, j, lo, hi, opt_lo, opt_hi):
    if lo > hi: return
    mid = (lo + hi) // 2
    best_k = opt_lo
    best_val = INF
    for k = opt_lo to min(mid - 1, opt_hi):
        val = dp[k][j-1] + C(k, mid)
        if val < best_val:
            best_val = val
            best_k = k
    dp[mid][j] = best_val
    compute(dp, j, lo, mid - 1, opt_lo, best_k)
    compute(dp, j, mid + 1, hi, best_k, opt_hi)
```

**Complexity**: $O(k n \log n)$ for $k$ layers and $n$ positions. This is the go-to optimization when Knuth doesn't apply but monotone opt holds.

---

## Monotone Queue Optimization

Covered in [Ch 117](../chapters/ch117-monotone-queue-optimization.md) and [Ch 188](../chapters/ch188-monotonic-queue-dp.md). The key advanced application is when the DP transition is:

\\[dp[i] = \min_{j} (dp[j] + f(j, i))\\]

where $f$ has a structure allowing the candidates to be pruned with a monotone queue (e.g., $f(j, i) = (\text{prefix}[i] - \text{prefix}[j])^2$ for convex hull trick, or $f(j, i) = g(j)$ with a sliding window constraint).

---

## Monge Arrays and SMAWK

### Monge Property

A matrix $A$ is **Monge** if for all $i < k$ and $j < l$:

\\[A[i][j] + A[k][l] \leq A[i][l] + A[k][j]\\]

Equivalently, the "row minima are non-decreasing in column index": if $\text{argmin}_j A[i][j] = j_i^*$, then $j_i^* \leq j_{i+1}^*$.

### SMAWK Algorithm

Computes all row minima of a totally monotone matrix (a generalization of Monge) in $O(n + m)$ time for an $n \times m$ matrix (assuming $O(1)$ element access). This is the fastest known algorithm for this problem.

```
function smawk(rows, cols):
    if len(rows) == 0: return {}
    # Reduce: remove dominated columns
    reduced_cols = reduce_cols(rows, cols)
    # Recursive step: solve on odd-indexed rows
    odd_rows = rows[1::2]
    odd_ans = smawk(odd_rows, reduced_cols)
    # Interpolate: fill in even-indexed rows
    ans = {}
    for i, row in enumerate(rows):
        if i % 2 == 1:
            ans[row] = odd_ans[row]
        else:
            lo = ans[rows[i-1]] if i > 0 else reduced_cols[0]
            hi = ans[rows[i+1]] if i+1 < len(rows) else reduced_cols[-1]
            ans[row] = argmin_j in [lo..hi] A[row][j]
    return ans
```

**Complexity**: $O(n + m)$ for $n$ rows and $m$ columns. The reduction step eliminates at least half the columns.

### Applications

- **Divide and conquer DP with Monge costs**: SMAWK gives $O(n)$ per layer instead of $O(n \log n)$.
- **Optimal binary search trees**: $O(n \log n)$ or $O(n)$ with SMAWK.

---

## Min-Plus Convolution

### Problem

Given two arrays $a[0..n]$ and $b[0..n]$, compute:

\\[c[k] = \min_{i+j=k} (a[i] + b[j])\\]


This is the discrete analog of the infimal convolution and appears in shortest paths, DP, and optimization.

### Brute Force

$O(n^2)$: enumerate all pairs $(i, j)$ with $i + j = k$.

### Acceleration via Concavity

If $a$ and $b$ are **concave** ($a[i+1] - a[i] \leq a[i] - a[i-1]$), then min-plus convolution runs in $O(n)$ using a variant of SMAWK or the "concave convolution" algorithm.

### General Case

No $O(n^{2-\epsilon})$ algorithm is known for general min-plus convolution. It is conjectured to require $n^{2-o(1)}$ time (related to the min-plus matrix multiplication conjecture).

---

## Subset Convolution

### Problem

Given two functions $f, g: 2^{[n]} \to \mathbb{R}$, compute:

\\[(f * g)[S] = \sum_{T \subseteq S} f[T] \cdot g[S \setminus T]\\]


### Brute Force

$O(3^n)$: for each $S$, enumerate all subsets $T$.

### Fast Subset Convolution: $O(n \cdot 2^n)$

**Key idea**: Use **rank** (number of set bits) to separate contributions. Define $f_r[S] = f[S]$ if $|S| = r$, else $0$. Then:

\\[(f * g)[S] = \sum_{r=0}^{|S|} (f_r \ast g_{|S|-r})[S]\\]

where $\ast$ is the **pointwise product** (not subset convolution). The Hadamard (pointwise) product is easy: multiply entry-by-entry.

**Algorithm**:
1. For each rank $r$, compute the **zeta transform** (SOS DP) of $f_r$ and $g_r$: $\hat{f}_r$ and $\hat{g}_r$.
2. Pointwise multiply: $\hat{h}_r[S] = \sum_{j=0}^{r} \hat{f}_j[S] \cdot \hat{g}_{r-j}[S]$.
3. **Möbius transform** (inverse SOS DP) of each $\hat{h}_r$ to get $h_r$.
4. Combine: $h[S] = h_{|S|}[S]$.

**Complexity**: $O(n^2 \cdot 2^n)$ for the rank separation step, $O(n \cdot 2^n)$ for each zeta/Möbius transform, totaling $O(n^2 \cdot 2^n)$. With careful implementation this is $O(n^2 \cdot 2^n)$.

---

## SOS DP (Sum Over Subsets) / Zeta Transform

### Problem

Given $f: 2^{[n]} \to \mathbb{R}$, compute the **zeta transform**:

\\[F[S] = \sum_{T \subseteq S} f[T]\\]


and the **Möbius transform** (inverse):

\\[f[S] = \sum_{T \subseteq S} (-1)^{|S|-|T|} F[T]\\]


### Standard SOS DP

```
# Zeta transform: F[S] = sum_{T subseteq S} f[T]
F = copy(f)
for i = 0 to n-1:
    for S = 0 to 2^n - 1:
        if S & (1 << i):
            F[S] += F[S ^ (1 << i)]

# Mobius transform: inverse
f = copy(F)
for i = 0 to n-1:
    for S = 0 to 2^n - 1:
        if S & (1 << i):
            f[S] -= f[S ^ (1 << i)]
```

**Complexity**: $O(n \cdot 2^n)$ for each transform.

### Walsh-Hadamard Transform (WHT)

The Walsh-Hadamard transform is the **analog of FFT over $\mathbb{F}_2^n$**. It operates on functions $f: \{0,1\}^n \to \mathbb{R}$ and uses the XOR convolution structure.

\\[(f \oplus g)[S] = \sum_{T} f[T] \cdot g[S \oplus T]\\]


```
# Forward Walsh-Hadamard Transform
for len = 1 to 2^n, len *= 2:
    for i = 0 to 2^n - 1 step len:
        for j = 0 to len/2 - 1:
            u = f[i+j], v = f[i+j+len/2]
            f[i+j] = u + v
            f[i+j+len/2] = u - v

# Inverse: same as forward, then divide by 2^n
```

**Complexity**: $O(n \cdot 2^n)$ — same as SOS DP but for XOR convolution.

### Möbius Inversion on the Subset Lattice

The **Möbius function** of the subset lattice is $\mu(T, S) = (-1)^{|S|-|T|}$ for $T \subseteq S$. The zeta transform is the forward direction and the Möbius transform is the inverse. This is a special case of Möbius inversion on posets (covered in [Ch 172](../chapters/ch172-mobius-inversion.md)).

### Applications

- **Counting subsets with property $P$**: Use inclusion-exclusion via Möbius transform.
- **Set partition DP**: Partition a set into groups with constraints.
- **Graph coloring on subsets**: Count valid colorings of induced subgraphs.

> **Interview Angle**: "Count the number of ways to choose a subset of items where no two chosen items conflict." Model as a sum over independent sets using inclusion-exclusion and Möbius transform on the subset lattice. The zeta/Möbius transforms compute the necessary counts in $O(n \cdot 2^n)$.

---

## Technique Comparison

| Technique | Reduces From | To | Condition | Key Requirement |
-----------|-------------|-----|-----------|-----------------|
| Knuth | $O(n^3)$ | $O(n^2)$ | QI + monotone opt | Quadrangle inequality |
| Divide & Conquer DP | $O(n^2 k)$ | $O(nk \log n)$ | Monotone opt | opt[i][j] non-decreasing in i |
| SMAWK | $O(nm)$ | $O(n+m)$ | Total monotonicity | Monge/totally monotone |
| Aliens Trick | Constrained | Unconstrained + binary search | Convexity of objective | $f(k)$ convex/concave |
| CHT (deque) | $O(n^2)$ | $O(n)$ | Lines sorted by slope, queries sorted | Monotone insertion/query |
| Li Chao Tree | $O(n^2)$ | $O(n \log C)$ | None | Arbitrary line insertion/query |
| Subset Conv. | $O(3^n)$ | $O(n^2 2^n)$ | None (always works) | Rank separation |
| SOS DP | $O(n 2^n)$ | $O(n 2^n)$ | None (this IS the fast method) | Zeta/Möbius transforms |

## Further Reading

- [Ch 86: DP Optimization](../chapters/ch86-dp-optimization.md) — CHT, divide & conquer DP
- [Ch 116: Aliens Trick](../chapters/ch116-alien-trick-parametric.md) — parametric search for DP
- [Ch 117: Monotone Queue Optimization](../chapters/ch117-monotone-queue-optimization.md) — monotone queue for DP
- [Ch 188: Monotonic Queue DP](../chapters/ch188-monotonic-queue-dp.md) — advanced MQ DP
- [Ch 118: Bitset DP](../chapters/ch118-bitset-dp.md) — bitset-accelerated DP
- Aggarwal, Park, "Notes on Insertion and Deletion in a Li Chao Segment Tree" — practical Li Chao variants
