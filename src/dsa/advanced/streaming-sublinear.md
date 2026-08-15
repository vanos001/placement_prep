# Streaming and Sublinear Algorithms

When data is too large to store (streaming) or too expensive to read entirely (sublinear), we must compute answers using limited resources. Building on [Ch 147](../chapters/ch147-streaming-algorithms.md) and [Ch 79](../chapters/ch79-probabilistic-ds.md), this file covers advanced streaming models (turnstile, sliding window), the AMS sketch, streaming quantiles, frequency moments, and the world of sublinear algorithms including property testing and local algorithms.

---

## Streaming Models

### Insertion-Only Streams

Each element $(i, v)$ either inserts value $v$ for item $i$ or is a simple item from a universe $[n]$. This is the simplest model: items arrive one at a time, and we can only store sublinear space.

### Turnstile Streams

The most general standard model: each update is $(i, \Delta)$ where $\Delta \in \mathbb{Z}$ (can be positive or negative). The frequency of item $i$ at time $t$ is $f_i = \sum_{\tau \leq t, \text{item}(\tau) = i} \Delta_\tau$.

```
Stream: (3, +5), (7, +2), (3, -1), (7, -2), (3, +3)
Frequencies: f[3] = 7, f[7] = 0, all others = 0
```

Frequencies can be **negative**. Many sketches (Count-Min, AMS) work naturally in the turnstile model. Count-Sketch and AMS give strong guarantees here.

### Sliding-Window Streams

Answer queries over only the **most recent** $W$ elements. The window slides forward with each new element. The challenge: expiring elements must be removed, but we cannot store the entire window.

**Exponential histogram technique (Datar-Gionis-Indyk-Motwani 2002)**:
- Maintain blocks of exponentially increasing sizes: $1, 1, 2, 2, 4, 4, 8, 8, \ldots$
- Each block stores its timestamp and aggregate (sum, count, etc.).
- When two blocks of the same size are adjacent, merge them.
- To answer a query, sum all blocks that are fully within the window, and adjust the partial boundary block.

**Complexity**: $O(\frac{1}{\epsilon} \log W)$ space for a $(1+\epsilon)$-approximation of the sum. $O(\frac{1}{\epsilon^2} \log W)$ for basic counting queries.

---

## Heavy Hitters

### Problem

Find all items whose frequency exceeds $\epsilon N$ where $N$ is the total stream length (in insertion model) or total absolute frequency (in turnstile model).

### Count-Min Sketch (Review)

See [Ch 79](../chapters/ch79-probabilistic-ds.md) for the basics. The Count-Min sketch uses $d$ hash functions mapping to a $w$-wide table. Query: $\hat{f}_i = \min_j \text{table}[j][h_j(i)]$.

**Guarantees**: $\hat{f}_i \geq f_i$ always (one-sided error), and $\hat{f}_i \leq f_i + \epsilon N$ with probability $\geq 1 - \delta$, where $w = \lceil e/\epsilon \rceil$ and $d = \lceil \ln(1/\delta) \rceil$. Space: $O(\frac{1}{\epsilon} \log \frac{1}{\delta})$.

### AMS Sketch (Alon-Matias-Szegedy)

Maintains an estimate of the **$F_2$ moment** (sum of squared frequencies): $F_2 = \sum_i f_i^2$.

```
Initialize: Z[j] = 0 for j = 1..d
g[j] = random sign in {-1, +1} for j = 1..d

On update (i, delta):
    for j = 1 to d:
        Z[j] += g[j](i) * delta

Estimate F2 = median(Z[j]^2 for j = 1..d)  # median of means
```

**Guarantees**: The estimate is within $\epsilon F_2$ with probability $\geq 2/3$ (boostable via median). Space: $O(1/\epsilon^2)$.

### Heavy Hitters via AMS + Count-Min

1. Use a Count-Min sketch to identify candidate heavy hitters (all items with $\hat{f}_i \geq \epsilon N/2$).
2. Verify candidates using a second, independent Count-Min sketch or AMS sketch.

### Misra-Gries Algorithm

A deterministic algorithm for heavy hitters in the insertion model. Maintain at most $k = \lceil 1/\epsilon \rceil$ counters.

```
function misra_gries(stream, epsilon):
    k = ceil(1 / epsilon)
    counters = {}  # item -> count
    for item in stream:
        if item in counters:
            counters[item] += 1
        elif len(counters) < k:
            counters[item] = 1
        else:
            for key in list(counters.keys()):
                counters[key] -= 1
                if counters[key] == 0:
                    del counters[key]
    # counters now contain estimates (may have false positives)
    return {item: count for item, count in counters.items()}
```

**Guarantees**: For any item $i$, $\hat{f}_i \geq f_i - \epsilon N$. Space: $O(1/\epsilon)$.

---

## Distinct Counting

### Problem

Estimate the number of distinct elements in a stream: $|\{i : f_i > 0\}|$.

### HyperLogLog

See [Ch 79](../chapters/ch79-probabilistic-ds.md) for details. Uses the position of the leftmost 1-bit in hashed values. Space: $O(1/\epsilon^2)$ registers, accuracy: $\epsilon / \sqrt{m}$ with $m$ registers.

### K-Minimum Values

Maintain the $k$ smallest hashed values seen. The distinct count is estimated as $\hat{n} = (k - 1) / \text{max\_hash}$. Space: $O(k)$.

---

## Frequency Moments

### The $F_k$ Problem

For a frequency vector $f = (f_1, \ldots, f_n)$, the $k$-th frequency moment is:

\\[F_k = \sum_{i=1}^{n} f_i^k\\]

- $F_0$: Number of distinct elements.
- $F_1$: Total count (trivially computable).
- $F_2$: Collision/square-sum (AMS sketch).
- $F_\infty$: Maximum frequency (heavy hitters).

### AMS for $F_2$

As described above. Uses $O(\epsilon^{-2} \log(1/\delta))$ space.

### $F_k$ for $k > 2$

For even $k$, the AMS approach generalizes: maintain $\sum_j g_j(i) \cdot f_i^{k/2}$ using $p$-stable random variables. Space: $O(\epsilon^{-2})$ for a $(1+\epsilon)$-approximation.

### The $F_0$ Estimation

HyperLogLog gives $O(1/\epsilon^2)$ space for a $(1+\epsilon)$-approximation of $F_0$.

### Lower Bounds

- $F_0$ requires $\Omega(1/\epsilon^2)$ space (Chakrabarti et al.).
- $F_2$ requires $\Omega(1/\epsilon^2)$ space.
- For $k \geq 3$, the exact space complexity is still open in some cases.

---

## Streaming Quantiles

### Problem

Given a stream of $N$ numbers, find the $\phi$-quantile (the $\phi N$-th smallest element) or answer rank queries (\"how many elements are $\leq x$?\").

### Greenwald-Khanna Algorithm

Maintains a set of **tuples** $(v, g, \Delta)$ where $v$ is a value, $g$ is the gap from the previous tuple, and $\Delta$ is the maximum possible gap from the previous tuple. Invariant: for any $\epsilon$, at most $\epsilon N$ elements can be between consecutive tuples.

**Complexity**: $O(\frac{1}{\epsilon} \log(\epsilon N))$ space. $O(\log(1/\epsilon))$ per update.

### KLL Sketch (Karnin-Lang-Medina)

The state-of-the-art streaming quantile sketch. Maintains a compact summary that allows $\epsilon$-accurate quantile queries.

**Complexity**: $O(\frac{1}{\epsilon} \log \log(1/\epsilon))$ space — provably optimal up to constants. Much smaller than Greenwald-Khanna in practice.

---

## Sublinear Algorithms

Sublinear algorithms read only a sublinear fraction of the input and produce an approximate answer. They are used for **property testing** and **estimation** on massive datasets.

### Property Testing

**Problem**: Given oracle access to an object (e.g., a graph via edge-detection queries, a function via evaluation queries), determine whether the object has a property $P$ or is "far" from having $P$.

**Definition**: An algorithm is a **property tester** for property $P$ if:
- If the input has $P$, it accepts with probability $\geq 2/3$.
- If the input is $\epsilon$-far from every object with $P$ (at least $\epsilon n^2$ edge modifications needed for graph properties), it rejects with probability $\geq 2/3$.

### Graph Property Testing

Test graph properties by querying a random sample of vertices/edges.

| Property | Query Model | Queries Needed |
----------|-------------|----------------|
| Bipartiteness | Adjacency list | $\tilde{O}(\sqrt{n}/\epsilon^3)$ |
| $k$-colorability | Adjacency list | $\tilde{O}(n / \epsilon^{O(k)})$ |
| Triangle-freeness | Adjacency list | $\tilde{O}(n / \epsilon^{O(1)})$ |
| Connectivity | Adjacency list | $\tilde{O}(n^{1/2} / \epsilon^4)$ |

### Linearity Testing

Test whether a function $f: \mathbb{F}_2^n \to \mathbb{F}_2$ is linear (i.e., $f(x \oplus y) = f(x) \oplus f(y)$). The **BLR linearity test**:

1. Pick random $x, y \in \mathbb{F}_2^n$.
2. Check if $f(x) \oplus f(y) = f(x \oplus y)$.
3. If the test passes, accept; else reject.

**Guarantee**: If $f$ is $\epsilon$-far from linear, the test rejects with probability $\geq \epsilon/3$. Uses only 3 queries!

### Local Algorithms

A **local algorithm** computes $f(x)$ for a specific input $x$ by examining only a small neighborhood of $x$. The running time depends on the **locality** (size of the neighborhood examined) rather than the global input size.

**Applications**: Distributed computing (each node decides its output based on its local neighborhood), LDPC decoding, property testing.

### Sublinear-Time Approximate Counting

Estimate the size of a set by sampling. For example, estimate the number of triangles in a graph by sampling edges and checking for common neighbors.

**Algorithm**: Sample $O(1/(\epsilon^2 \hat{p}))$ edges uniformly, where $\hat{p}$ is an estimate of the triangle density. For each sampled edge $(u,v)$, estimate $|N(u) \cap N(v)|$. Average and scale.

---

## Comparison Table

| Problem | Streaming Space | Sublinear Queries | Notes |
---------|----------------|-------------------|-------|
| Heavy Hitters ($F_\infty$) | $O(1/\epsilon \log(1/\delta))$ | — | Count-Min Sketch |
| Distinct Elements ($F_0$) | $O(1/\epsilon^2)$ | $O(1/\epsilon^2)$ | HyperLogLog |
| $F_2$ moment | $O(1/\epsilon^2)$ | — | AMS Sketch |
| Quantiles | $O(\frac{1}{\epsilon} \log \log \frac{1}{\epsilon})$ | — | KLL Sketch |
| Graph bipartiteness | — | $\tilde{O}(\sqrt{n}/\epsilon^3)$ | Property testing |
| Linearity testing | — | $O(1)$ | BLR test |
| Triangle counting | — | $\tilde{O}(n / \epsilon^2)$ | Edge sampling |

> **Interview Angle**: "Design a system to count distinct users visiting a website per day, using minimal memory." Answer: HyperLogLog with 12 KB gives ~1.6% error for up to $2^{32}$ distinct users. Explain the register-based structure and harmonic mean estimation.

## Further Reading

- [Ch 79: Probabilistic DS](../chapters/ch79-probabilistic-ds.md) — Count-Min, Bloom filters, HyperLogLog basics
- [Ch 147: Streaming Algorithms](../chapters/ch147-streaming-algorithms.md) — streaming fundamentals
- Alon, Matias, Szegedy, "The Space Complexity of Approximating the Frequency Moments" (1999) — the AMS paper
- Goldreich, *Introduction to Property Testing* (2017) — comprehensive property testing reference

