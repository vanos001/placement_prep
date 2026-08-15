# Parallel, External-Memory, and Spectral Graph Algorithms

When data doesn't fit in cache (external memory), when we have many cores (parallel), or when spectral methods give better approximations (spectral), standard algorithms must be rethought. Building on [Ch 159](../chapters/ch159-external-memory.md), [Ch 160](../chapters/ch160-parallel-algorithms.md), and [Ch 154](../chapters/ch154-spectral-graph-theory.md), this file covers cache-oblivious algorithms, the work-span model, PRAM, work stealing, parallel prefix/sorting, spectral sparsification, graph sparsification, Laplacian solvers, and parallel/distributed/streaming/dynamic/spectral graph algorithms.

---

## External-Memory and Cache-Oblivious Algorithms

### I/O Complexity Model (Aggarwal-Vitter)

- **Main memory**: Size $M$ words.
- **Disk block**: Size $B$ words.
- **I/O cost**: Number of block transfers between disk and memory.
- **Input size**: $N$ words.

**Scanning** $N$ items: $       ext{scan}(N) = O(N/B)$ I/Os.
**Sorting** $N$ items: $        ext{sort}(N) = O(\frac{N}{B} \log_{M/B} \frac{N}{B})$ I/Os.

### Cache-Oblivious Algorithms

A cache-oblivious algorithm is designed **without knowing** $M$ or $B$, yet achieves near-optimal I/O on **any** memory hierarchy level. The key insight: use recursive divide-and-conquer that naturally adapts to all cache sizes simultaneously.

### Cache-Oblivious Matrix Transposition

```
function transpose(A, n):
    if n <= THRESHOLD: naive transpose
    # Divide into 4 quadrants
    # Swap A[0:n/2][n/2:n] with A[n/2:n][0:n/2]
    transpose(A[0:n/2][0:n/2], n/2)      # top-left
    transpose(A[n/2:n][n/2:n], n/2)      # bottom-right
    # Recursively swap off-diagonal blocks
```

**I/O complexity**: $O(N/B \cdot \log(M/B))$ — optimal for matrix transpose.

### Cache-Oblivious Matrix Multiplication

Uses recursive 2x2 block decomposition (essentially the "naive" approach, but the recursion handles all cache levels):

```
function matmul_oblivious(A, B, C, n):
    if n <= THRESHOLD:
        C += A * B  (naive triple loop)
        return
    half = n // 2
    matmul_oblivious(A[TL], B[TL], C[TL], half)
    matmul_oblivious(A[TR], B[BL], C[TL], half)
    matmul_oblivious(A[TL], B[TR], C[TR], half)
    matmul_oblivious(A[TR], B[BR], C[TR], half)
    # ... 4 more recursive calls for bottom half
```

**I/O complexity**: $O(N/B \cdot \sqrt{M/B})$ — near-optimal (optimal is $O(N/B \cdot (M/B)^{0.5 - \epsilon})$ via Strassen).

### Funnel Sort (Cache-Oblivious Sorting)

**I/O complexity**: $O(\frac{N}{B} \log_{M/B} \frac{N}{B})$ — matches the lower bound, even without knowing $M$ or $B$. Uses a binary merge tree where each merge is done in a cache-oblivious "funnel" structure.

---

## Parallel Algorithms: Work-Span Model

### The Model

- **Work** $W$: Total number of operations (sequential running time). Analogous to $O(n \log n)$ for sorting.
- **Span** $D$ (depth/parallelism): Length of the longest dependency chain. Analogous to $O(\log^2 n)$ for parallel merge sort.
- **Running time on $P$ processors**: $O(W/P + D)$.
- **Parallelism**: $W/D$ — the maximum useful number of processors.

### PRAM (Parallel Random Access Machine)

The theoretical model for parallel computation: $P$ processors share a common memory, each step takes $O(1)$ time.

| PRAM Variant | Conflict Resolution | Notes |
|-------------|---------------------|-------|
| EREW | No concurrent reads or writes | Most restrictive |
| CREW | Concurrent reads OK, no concurrent writes | Common model |
| CRCW | Concurrent reads and writes allowed | Must specify write rule (common/ARBITRARY/PRIORITY) |

### Parallel Prefix Sum (Scan)

```
# Up-sweep (reduce)
for d = 0 to log2(n) - 1:
    parallel for i = 0 to n-1 step 2^(d+1):
        data[i + 2^(d+1) - 1] += data[i + 2^d - 1]

# Down-sweep (distribute)
data[n-1] = 0
for d = log2(n) - 1 down to 0:
    parallel for i = 0 to n-1 step 2^(d+1):
        temp = data[i + 2^d - 1]
        data[i + 2^d - 1] = data[i + 2^(d+1) - 1]
        data[i + 2^(d+1) - 1] += temp
```

**Work**: $O(n)$. **Span**: $O(\log n)$. This is the building block for countless parallel algorithms.

### Parallel Sorting

- **Parallel merge sort**: Work $O(n \log n)$, span $O(\log^2 n)$.
- **Parallel quicksort**: Expected work $O(n \log n)$, span $O(\log n)$ expected (but $O(n)$ worst case).
- **Sample sort**: Work $O(n \log n)$, span $O(\log n)$ expected. Pick $P-1$ splitters from a random sample, partition, sort each bucket.

---

## Work Stealing

### Problem

In dynamic multithreading, different parallel tasks may have vastly different amounts of work. Static assignment leads to load imbalance. **Work stealing** is a dynamic scheduling strategy where idle processors "steal" tasks from busy processors.

### Algorithm

- Each processor has a **double-ended queue** (deque) of tasks.
- The owning processor pushes/pops from the **bottom** (LIFO — good for locality).
- Thieves steal from the **top** (FIFO).

```
# Owned processor: push
function push(task):
    deque.bottom_push(task)

# Owned processor: pop
function pop():
    if deque is empty: return EMPTY
    return deque.bottom_pop()

# Thief processor: steal
function steal():
    if deque is empty: return EMPTY
    return deque.top_pop()  # CAS-based, non-blocking
```

### Analysis (Blumofe-Leiserson)

**Theorem**: A work-stealing scheduler executes a computation with work $W$ and span $D$ on $P$ processors in expected time $O(W/P + D)$.

The proof uses a potential function argument: each steal reduces the "potential" and the total potential is bounded by $O(W \cdot D / P)$.

### Implementations

- **Cilk**: The original work-stealing runtime (MIT).
- **Intel TBB**: Uses work stealing with task-based parallelism.
- **Go runtime**: Uses work stealing for goroutine scheduling.
- **Rust rayon**: Work-stealing thread pool.

---

## Spectral Graph Algorithms

### The Graph Laplacian

For a weighted graph $G$ with adjacency matrix $A$ and degree matrix $D$:

\\[L = D - A\\]

The **normalized Laplacian** is $\mathcal{L} = I - D^{-1/2} A D^{-1/2}$.

**Properties**:
- $L$ is symmetric positive semidefinite.
- The smallest eigenvalue is $\lambda_1 = 0$ with eigenvector $\mathbf{1}$ (the all-ones vector).
- The number of zero eigenvalues equals the number of connected components.
- The second-smallest eigenvalue $\lambda_2$ (the **algebraic connectivity** or **Fiedler value**) measures how well-connected the graph is.

### Spectral Partitioning

The **Fiedler vector** (eigenvector for $\lambda_2$) gives a partition: assign each vertex to one of two groups based on the sign of its component in the Fiedler vector.

**Cheeger's inequality**: $\frac{\lambda_2}{2} \leq h(G) \leq \sqrt{2\lambda_2}$ where $h(G)$ is the Cheeger constant (minimum edge expansion). This connects the spectral gap to the quality of the partition.

### Spectral Sparsification

**Spectral sparsifier**: A subgraph $H$ of $G$ on $O(n / \epsilon^2)$ edges such that for all vectors $x$:

\\[(1-\epsilon) x^T L_G x \leq x^T L_H x \leq (1+\epsilon) x^T L_G x\\]

This means $H$ preserves all quadratic forms of the Laplacian, which implies it preserves cut values, random walk mixing times, effective resistances, and much more.

**Spielman-Srivastava algorithm (2008)**:
1. Compute effective resistances $R_e$ for all edges (using the Laplacian pseudoinverse $L^+$).
2. Sample each edge $e$ with probability $p_e = \min(1, w_e R_e \cdot c \log n / \epsilon^2)$.
3. Scale sampled edges by $1/p_e$.

**Size**: $O(n \log n / \epsilon^2)$ edges. Later improved to $O(n / \epsilon^2)$ by Batson, Spielman, Srivastava (BSS matrix sparsification).

### Graph Sparsification

Beyond spectral sparsification, there are several notions:

| Type | Preserves | Size | Method |
------|-----------|------|--------|
| Cut sparsifier | All cuts $\pm \epsilon$ | $O(n \log n / \epsilon^2)$ | Benczur-Karger (strong random sampling) |
| Spectral sparsifier | Quadratic forms | $O(n / \epsilon^2)$ | Spielman-Srivastava, BSS |
| Spanner | Distances $\leq t$ | $O(n^{1+1/t})$ | Greedy (Baswana-Sen) |
| Flow sparsifier | All s-t flows | $O(n)$ | Moyles-Thompson, due to think in terms of treewidth |

### Laplacian Solvers

**Problem**: Solve $Lx = b$ where $L$ is the graph Laplacian and $b$ is a vector. This is the key subroutine in spectral graph algorithms, max-flow, and more.

#### Preconditioned Conjugate Gradient (PCG)

Use a low-stretch spanning tree as a preconditioner. Achlioptas et al. showed that the spectral gap of the tree preconditioner gives convergence in $O(\sqrt{m \log n \log(1/\epsilon)})$ iterations.

#### Spielman-Teng Solver (2004)

The breakthrough: solve Laplacian systems in $\tilde{O}(m)$ time (near-linear).

**Approach**:
1. Compute a **low-stretch spanning tree** $T$.
2. Build a **two-level preconditioner**: use $T$ as a coarse solver and the off-tree edges for correction.
3. Apply **multigrid**: recursively build preconditioners at coarser levels.
4. Use PCG with this multilevel preconditioner.

**Complexity**: $O(m \log^{O(1)} n \log(1/\epsilon))$ — nearly linear in the number of edges.

#### Modern Laplacian Solvers

- **Kyng-Sachdeva (2016)**: $O(m \log^{1/2} n \log(1/\epsilon))$ using recursive sparsification.
- **Cohen, Kyng, Pachocki, Peng, Rao (2017)**: $O(m \log^{1/3} n \log(1/\epsilon))$ using a chain of sparsifiers.
- **Current best**: $O(m \log^{o(1)} n)$ — approaching the $O(m)$ barrier.

### Applications of Laplacian Solvers

- **Max-flow**: Madry's $\tilde{O}(m^{10/7})$ max-flow algorithm uses a Laplacian solver as a subroutine.
- **Electrical flows**: The solution $x = L^+ b$ is the electrical flow when $b$ is a unit source-sink vector.
- **Graph partitioning**: Spectral partitioning via the Fiedler vector.
- **Random walks**: PageRank and personalized PageRank can be accelerated.
- **Clique/minor testing**: Used in parameterized algorithms.

---

## Parallel/Distributed/Streaming/Dynamic Graph Algorithms

### Parallel Graph Algorithms

| Problem | Sequential | Parallel Work | Parallel Span |
---------|-----------|---------------|---------------|
| BFS | $O(m + n)$ | $O(m + n)$ | $O(\sqrt{n} \cdot \log n)$ or $O(D \cdot \log n)$ |
| SSSP | $O(m + n \log n)$ | $O(m \log n)$ | $O(D \cdot \log n)$ | 
| MST | $O(m \log n)$ | $O(m \log n)$ | $O(\log^2 n)$ (Borůvka parallel) |
| Connected Components | $O(m + n)$ | $O(m \alpha(n))$ | $O(\log^2 n)$ |
| Max-Flow | $O(m \sqrt{n})$ | $O(m \sqrt{n})$ | polylog (near-optimal) |

### Borůvka's Algorithm (Parallel MST)

```
while |components| > 1:
    parallel for each component c:
        find cheapest edge from c to another component
    add all such edges (some may conflict; resolve arbitrarily)
    merge components
```

**Work**: $O(m \log n)$. **Span**: $O(\log n)$ rounds (each round halves the number of components). Total span: $O(\log^2 n)$.

### Distributed Graph Algorithms

In the **CONGEST model**, each node can send $O(\log n)$ bits per round to each neighbor.

| Problem | Rounds | Notes |
---------|--------|-------|
| BFS/SSSP | $O(D)$ | Optimal (D = diameter) |
| MST | $\tilde{O}(\sqrt{n})$ | Ghaffari-Kuhn (2018), near-optimal |
| Connected Components | $\tilde{O}(\sqrt{n})$ | Near-optimal |
| Max-Cut | $O(\log n)$ | 2-approximation |

### Dynamic Graph Algorithms

Maintain a graph property under edge insertions and deletions. See [dynamic-trees.md](dynamic-trees.md) for detailed coverage of forest structures. Key results for general graphs:

| Property | Update | Query |
----------|--------|--------|
| Connectivity (HDLT) | $O(\log^2 n)$ | $O(\log n / \log \log n)$ |
| Bipartiteness | $O(\sqrt{n})$ | $O(1)$ |
| Spanner | $O(\text{polylog } n)$ | $O(1)$ |
| Spectral properties | $O(\text{polylog } n)$ | $O(\text{polylog } n)$ |

---

## Comparison: Graph Algorithm Paradigms

```
                | External Memory | Parallel (P procs) | Distributed | Streaming
----------------|------------------|--------------------|-------------|----------
BFS            | O(sort(m))       | O(m/P + D log n)   | O(D) rounds | O(n log n)
SSSP           | O(sort(m))       | O(m log n / P)     | O(D log n)  | N/A
MST            | O(sort(m))       | O(m log n / P)     | O(sqrt(n))  | O(n log n)
Connected Comp | O(sort(m))       | O(m alpha(n)/P)    | O(sqrt(n))  | O(n alpha(n))
Laplacian Solve| O(m log n / B)   | O(m log^c n / P)   | Open        | O(n polylog n)
```

> **Interview Angle**: "How would you find connected components in a graph that doesn't fit in memory?" Describe external-memory BFS: use BFS level by level, sorting the frontier at each level (each BFS level is an external sort). Total I/O: $O(\text{sort}(m)) = O(\frac{m}{B} \log_{M/B} \frac{m}{B})$. For parallel: Borůvka's algorithm with $O(\log^2 n)$ span.

## Further Reading

- [Ch 159: External Memory Algorithms](../chapters/ch159-external-memory.md) — external memory basics
- [Ch 160: Parallel Algorithms](../chapters/ch160-parallel-algorithms.md) — parallel algorithms basics
- [Ch 154: Spectral Graph Theory](../chapters/ch154-spectral-graph-theory.md) — spectral methods
- [Ch 156: Dynamic Graph Algorithms](../chapters/ch156-dynamic-graph-algorithms.md) — dynamic connectivity/MST
- Frigo, Leiserson, Prokop, Ramachandran, "Cache-Oblivious Algorithms" (1999)
- Spielman & Teng, "Nearly-Linear Time Algorithms for Graph Partitioning, Graph Sparsification, and Solving Linear Systems" (2004)
- Blelloch, "Programming Parallel Algorithms" (1996) — work-span model tutorial
