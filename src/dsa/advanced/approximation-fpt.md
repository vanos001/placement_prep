# Approximation Algorithms and Fixed-Parameter Tractability

Many real-world optimization problems are NP-hard. [Basic approximation algorithms](../chapters/ch145-approximation-algorithms.md) and [FPT basics](../chapters/ch148-parameterized-algorithms.md) are covered elsewhere. This file covers the advanced landscape: PTAS/FPTAS schemes, kernelization, parameterized complexity classes, treewidth, tree decomposition, graph minors, planar graph algorithms, and separator theorems.

---

## Approximation Schemes

### PTAS (Polynomial-Time Approximation Scheme)

A PTAS for a minimization problem is an algorithm that, for any $ε > 0$, produces a solution within a factor $(1 + ε)$ of optimal, running in time polynomial in $n$ (but potentially exponential in $1/ε$). Formally, the running time is $O(n^{f(1/ε)})$.

**Example — Knapsack PTAS**: Scale item values to reduce the number of distinct values, then use DP. For a $(1-ε)$-approximation, round each value $v_i$ down to $v_i' = \lfloor v_i / K \rfloor$ where $K = \epsilon \\max v_i / n$. This reduces the DP state space.

### FPTAS (Fully Polynomial-Time Approximation Scheme)

An FPTAS runs in time polynomial in **both** $n$ and $1/ε$: $O(n^a / ε^b)$ for constants $a, b$.

**Example — Knapsack FPTAS**: 
```
function knapsack_fptas(items, capacity, epsilon):
    V_max = max(item.value for item in items)
    K = epsilon * V_max / n
    for each item:
        item.scaled_value = floor(item.value / K)
    # Run standard DP on scaled values
    dp[w] = max scaled value achievable with capacity w
    # Standard 0/1 knapsack DP in O(n * capacity)
    return items selected by DP
```
**Complexity**: $O(n / \epsilon)$ value states $×$ $O(n)$ items = $O(n^2 / \epsilon)$. This is polynomial in both $n$ and $1/\epsilon$.

### EPTAS and PTAS Hierarchy

- **PTAS**: Time $O(n^{f(1/\epsilon)})$. Exponential dependence on $1/\epsilon$.
- **EPTAS** (Efficient PTAS): Time $f(1/\epsilon) · n^{O(1)}$. The exponential part is separated from $n$.
- **FPTAS**: Time $O(n^{O(1)} / \epsilon^{O(1)})$. Fully polynomial.

| Scheme | Time | Knapsack | TSP (metric) | Vertex Cover |
--------|------|----------|-------------|-------------|
| PTAS | $n^{f(1/\epsilon)}$ | Yes | Yes (Arora) | Yes (via FPT) |
| EPTAS | $f(1/\epsilon) · n^c$ | Yes | No | Open |
| FPTAS | $n^c / \epsilon^d$ | Yes | No | No (unless P=NP) |

---

## Fixed-Parameter Tractability (FPT)

### Core Idea

A problem parameterized by $k$ is **FPT** if it can be solved in time $f(k) · n^{O(1)}$ where $f$ is a function depending only on $k$ (not $n$). This means the "combinatorial explosion" is confined to the parameter.

### Key Parameterized Problems

| Problem | Parameter | FPT Algorithm | Time |
---------|-----------|--------------|------|
| Vertex Cover | Solution size $k$ | Bounded Search Tree | $O(2^k · n)$ |
| $k$-Path | Path length $k$ | Color-Coding | $O(2^k · n)$ |
| Feedback Vertex Set | Solution size $k$ | Iterative Compression | $O(2^k · n^2)$ |
| $k$-Clique | Clique size $k$ | Enumerate $\binom{n}{k}$ | $O(n^k)$ (W[1]-hard) |
| Dominating Set | Solution size $k$ | Bounded Search Tree | $O(c^k · n)$ |

### Parameterized Complexity Classes

```
FPT ⊆ W[1] ⊆ W[2] ⊆ ... ⊆ XP

FPT:  f(k) * poly(n)
W[1]: f(k) * poly(n) but likely NOT FPT (e.g., k-Clique)
W[2]: f(k) * poly(n) (e.g., Dominating Set parameterized by k)
XP:  n^{f(k)} (polynomial for each fixed k, but k in the exponent)
```

**W[1]-hard**: The parameterized analog of NP-hardness. $k$-Clique is W[1]-complete, meaning an FPT algorithm for $k$-Clique would imply FPT = W[1] (believed false).

---

## Kernelization

### Definition

A **kernelization** is a polynomial-time algorithm that transforms an instance $(x, k)$ into an equivalent instance $(x', k')$ where $k' \leq k$ and $|x'| \leq f(k)$ for some function $f$. The reduced instance is called a **kernel**.

**Key theorem**: A problem is FPT if and only if it has a kernel (not necessarily polynomial).

### Polynomial Kernels

A **polynomial kernel** has $|x'| = O(k^c)$ for some constant $c$. Not all FPT problems have polynomial kernels (under standard complexity assumptions).

### Example: Vertex Cover Kernel

**Reduction rules**:
1. If any vertex has degree $\geq k + 1$, include it in the cover (reduce $k$, remove it and neighbors).
2. If any vertex has degree 0, remove it.
3. If an edge exists, both endpoints have degree $\leq k$.

After applying these rules, if $k \geq 0$ and edges remain, every vertex has degree $1$ to $k$. Since each vertex in the cover covers at most $k$ edges and there are $\leq k^2$ remaining edges (else rule 1 applies), the kernel has at most $k^2$ vertices.

**Kernel size**: $O(k^2)$ vertices. This is a polynomial kernel.

### Crown Reduction

A powerful kernelization technique. A **crown** is a set of vertices $C$ (the "crown") plus a set $H$ (the "head") such that: (1) there are no edges within $C$, (2) every vertex in $C$ has exactly one neighbor in $H$, and (3) $H$ has a matching into $C$. When a crown is found, we can include $H$ in the vertex cover and remove $C \cup H$.

---

## Treewidth and Tree Decomposition

### Definition

A **tree decomposition** of a graph $G = (V, E)$ is a pair $(T, \{X_i\}_{i \in I})$ where $T$ is a tree and each $X_i \subseteq V$ is a "bag," satisfying:
1. **Coverage**: Every vertex of $G$ is in at least one bag.
2. **Edge coverage**: Every edge $(u, v)$ of $G$ is contained in some bag.
3. **Connectedness**: For every vertex $v$ of $G$, the set of bags containing $v$ forms a connected subtree of $T$.

The **width** of the decomposition is $\max_i |X_i| - 1$. The **treewidth** $\text{tw}(G)$ is the minimum width over all tree decompositions.

### Examples

```
Tree (tw=1):         Cycle (tw=2):        Grid (tw=min(m,n)):
    a                   a--b               a--b--c
   / \                 |  |               |  |  |
  b   c                d--c               d--e--f
                         |  |               |  |  |
                         f--e               g--h--i

Tree decomp for cycle:      Tree decomp for tree:
  {a,b,c} -- {b,c,d}         {a,b,c} -- {c,e} -- {e,f}
     |          |
  {a,f,e} -- {e,d,f}
  Width = 2 (3-1)
```

### Algorithms on Bounded Treewidth

Many NP-hard problems become **linear-time** on graphs of bounded treewidth, solved via **dynamic programming on the tree decomposition**.

| Problem | Time on tw=$w$ | Notes |
---------|---------------|-------|
| Vertex Cover | $O(2^w \cdot n)$ | DP state: subset of bag |
| 3-Coloring | $O(3^w \cdot n)$ | DP state: color assignment to bag |
| Hamiltonian Path | $O(w! \cdot n)$ | Order within each bag |
| Steiner Tree | $O(3^w \cdot n)$ | DP state: which terminals in subtree |
| Max Independent Set | $O(2^w \cdot n)$ | Classic nice tree decomposition DP |

### Nice Tree Decomposition

A "nice" tree decomposition is a rooted binary tree where each bag is one of four types:
- **Leaf**: $X_i = \emptyset$.
- **Introduce**: $X_i = X_j \cup \{v\}$ where $j$ is the child.
- **Forget**: $X_i = X_j \setminus \{v\}$ where $j$ is the child.
- **Join**: $X_i = X_j = X_k$ where $j, k$ are the two children.

Any tree decomposition can be converted to a nice one with at most $4n$ bags in $O(nw)$ time.

### Computing Treewidth

Finding the treewidth of a graph is NP-hard in general. However:
- **Planar graphs**: $O(2^{O(\sqrt{n})})$ via branch decomposition (Bodlaender).
- **Bounded-degree graphs**: $O(f(w) \cdot n)$ for constant maximum degree.
- **Heuristics**: Minimum degree ordering, minimum fill-in, chordal completion.
- **Exact**: Bodlaender's algorithm runs in $O(f(w) \cdot n)$ but with an enormous $f(w)$ (not practical).

> **Interview Angle**: "How would you solve vertex cover on a graph that's 'almost a tree'?" Describe treewidth: trees have tw=1, and vertex cover is $O(2^w \cdot n)$. If the graph is a tree plus a few cross-edges, the treewidth is small and the problem is tractable.

---

## Graph Minors and the Robertson-Seymour Theorem

### Graph Minors

A graph $H$ is a **minor** of $G$ if $H$ can be obtained from a subgraph of $G$ by contracting edges. Denoted $H \preceq G$.

### Robertson-Seymour Theorem (Graph Minor Theorem)

**Theorem**: In any infinite set of graphs, there exist two graphs $G, H$ such that $G$ is a minor of $H$. Equivalently, for any minor-closed graph family $\mathcal{F}$ (if $G \in \mathcal{F}$ and $H \preceq G$ then $H \in \mathcal{F}$), there is a **finite set of forbidden minors** $\mathcal{H}_1, \ldots, \mathcal{H}_k$ such that $G \in \mathcal{F}$ iff no $\mathcal{H}_i$ is a minor of $G$.

### Consequences

- **Planarity**: A graph is planar iff it excludes $K_5$ and $K_{3,3}$ as minors (Kuratowski's theorem, a special case of R-S).
- **Bounded treewidth**: Graphs excluding $K_t$ as a minor have treewidth $O(t \sqrt{\log t})$.
- **Testing $H$-minors**: For a fixed graph $H$, testing whether $H$ is a minor of $G$ can be done in $O(f(H) \cdot n^3)$ time (Robertson-Seymour). This is FPT with parameter $|H|$.

### Grid Minor Theorem

**Theorem**: For any graph $G$ excluding $K_t$ as a minor, the treewidth of $G$ is $O(t \sqrt{\log t} \cdot \sqrt{\text{tw}(G)})$. This deep result connects excluded minors to treewidth and is used in many algorithmic applications.

---

## Planar Graph Algorithms

### Planar Separator Theorem (Lipton-Tarjan)

**Theorem**: Every $n$-vertex planar graph has a separator of size $O(\sqrt{n})$ that partitions the graph into two parts each with at most $2n/3$ vertices.

### Applications

The separator theorem enables **divide-and-conquer** algorithms on planar graphs:
- **Planar shortest paths**: $O(n \log^2 n)$ or $O(n \log n)$ using separators + Dijkstra.
- **Planar max-flow**: $O(n \log n)$ or $O(n \log^2 n)$.
- **Planar minimum cut**: $O(n \log n)$.

### Geometric Separators

For $d$-dimensional geometric graphs (e.g., intersection graphs of balls in $\mathbb{R}^d$), a separator of size $O(n^{1-1/d})$ exists. The $d=2$ case recovers the planar separator. For $d=3$: $O(n^{2/3})$.

### Branch Decomposition

A **branch decomposition** of a graph is a ternary tree where leaves correspond to edges. The **width** is the maximum number of vertices shared between the two sides of any internal node's partition. The optimal branchwidth is closely related to treewidth: $\text{bw}(G) \leq \text{tw}(G) + 1 \leq \lfloor 3/2 \cdot \text{bw}(G) \rfloor$.

---

## Comparison Table

| Technique | Problem Class | Key Parameter | Complexity | Key Insight |
-----------|--------------|---------------|------------|-------------|
| PTAS | Optimization | $\epsilon$ | $n^{f(1/\epsilon)}$ | Scales input, rounds values |
| FPTAS | Optimization | $\epsilon$ | poly$(n, 1/\epsilon)$ | Knapsack-type DP with rounding |
| Bounded Search Tree | Exact (FPT) | Solution size $k$ | $O(c^k \cdot n)$ | Branch on choices, bound depth |
| Color-Coding | Exact (FPT) | Path/structure size | $O(e^k \cdot n)$ | Random coloring + DP |
| Iterative Compression | Exact (FPT) | Solution size $k$ | $O(c^k \cdot n^2)$ | Extend solution one vertex at a time |
| Kernelization | Reduction | $k$ | poly$(n)$, output $f(k)$ | Reduce instance to $O(k^c)$ size |
| Treewidth DP | Exact (FPT) | Treewidth $w$ | $O(c^w \cdot n)$ | DP on tree decomposition bags |
| Separator | Divide & Conquer | Planarity | $O(n^{1-1/d})$ split | Recursive on subproblems |

## Further Reading

- [Ch 145: Approximation Algorithms](../chapters/ch145-approximation-algorithms.md) — approximation basics
- [Ch 148: Parameterized Algorithms](../chapters/ch148-parameterized-algorithms.md) — FPT fundamentals
- [Ch 109: Treewidth and Bridge Trees](../chapters/ch109-bridge-trees-treewidth.md) — treewidth applications
- [Ch 96: NP and Approximation](../chapters/ch96-np-approximation.md) — NP-hardness and approximability
- Cygan et al., *Parameterized Algorithms* (2015) — the FPT textbook
- Williamson & Shmoys, *The Design of Approximation Algorithms* (2011) — comprehensive approximation reference
- Robertson & Seymour, "Graph Minors" series (1983-2004) — the monumental graph minor theory
