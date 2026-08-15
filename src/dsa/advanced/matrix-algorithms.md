# Fast Matrix Multiplication and Randomized Linear Algebra

Matrix multiplication is the computational backbone of graph algorithms ([shortest paths](../chapters/ch82-advanced-shortest-paths.md), transitive closure), [DP](../chapters/ch115-matrix-dp.md), [linear algebra](../chapters/ch73-linear-algebra.md), and machine learning. This file covers the frontier: Strassen, Coppersmith-Winograd, rectangular multiplication, tensor methods, randomized linear algebra, and sketching.

---

## Strassen's Algorithm

### The Breakthrough

Strassen (1969) showed that two $n \times n$ matrices can be multiplied in $O(n^{\log_2 7}) \approx O(n^{2.807})$ instead of $O(n^3)$. The key insight: multiplying two $2 \times 2$ matrices requires only **7 multiplications** instead of 8, at the cost of more additions.

### The 7 Products

For $C = A \times B$ where $A, B, C$ are $2 \times 2$:

$$M_1 = (A_{11} + A_{22})(B_{11} + B_{22})$$
$$M_2 = (A_{21} + A_{22}) \cdot B_{11}$$
$$M_3 = A_{11} \cdot (B_{12} - B_{22})$$
$$M_4 = A_{22} \cdot (B_{21} - B_{11})$$
$$M_5 = (A_{11} + A_{12}) \cdot B_{22}$$
$$M_6 = (A_{21} - A_{11}) \cdot (B_{11} + B_{12})$$
$$M_7 = (A_{12} - A_{22}) \cdot (B_{21} + B_{22})$$

Then: $C_{11} = M_1 + M_4 - M_5 + M_7$, $C_{12} = M_3 + M_5$, $C_{21} = M_2 + M_4$, $C_{22} = M_1 - M_2 + M_3 + M_6$.

### Implementation

```
function strassen(A, B, n):
    if n <= THRESHOLD:
        return naive_multiply(A, B)  # fall back to O(n^3)
    # Pad to even dimensions if necessary
    half = n // 2
    # Partition A and B into quadrants A11, A12, A21, A22, etc.
    M1 = strassen(A11 + A22, B11 + B22, half)
    M2 = strassen(A21 + A22, B11, half)
    M3 = strassen(A11, B12 - B22, half)
    M4 = strassen(A22, B21 - B11, half)
    M5 = strassen(A11 + A12, B22, half)
    M6 = strassen(A21 - A11, B11 + B12, half)
    M7 = strassen(A12 - A22, B21 + B22, half)
    # Combine
    C11 = M1 + M4 - M5 + M7
    C12 = M3 + M5
    C21 = M2 + M4
    C22 = M1 - M2 + M_3 + M6
    return combine(C11, C12, C21, C22)
```

### Practical Notes

- **Cutoff**: In practice, switch to naive multiplication for $n \leq 64$ or $n \leq 128$. The constant overhead of Strassen's additions makes it slower for small matrices.
- **Numerical stability**: Strassen is less numerically stable than naive multiplication. Use with care for floating-point matrices.
- **Cache efficiency**: Strassen can be combined with blocking for cache-friendly implementations.

---

## Coppersmith-Winograd and Beyond

### The Exponent Roadmap

The matrix multiplication exponent $\omega$ is defined as the infimum of real numbers $c$ such that $n \times n$ matrix multiplication can be done in $O(n^c)$ time.

| Algorithm | Year | Exponent | Practical? |
-----------|------|----------|------------|
| Naive | — | 3.000 | Yes | 
| Strassen | 1969 | 2.807 | Yes |
| Pan | 1978 | 2.796 | No |
| Bini et al. | 1979 | 2.780 | No |
| Schönhage | 1981 | 2.522 | No |
| Strassen (laser method) | 1986 | 2.479 | No |
| Coppersmith-Winograd | 1990 | 2.376 | No |
| Stothers | 2010 | 2.374 | No |
| Vassilevska-Williams | 2012 | 2.373 | No |
| Alman-Williams | 2021 | 2.372 | No |

### Coppersmith-Winograd Idea

The CW algorithm uses a **laser method**: construct a tensor that represents a matrix multiplication-like operation with fewer multiplications than expected, then iteratively "squash" this tensor to get closer to the optimal exponent. The analysis involves combinatorial optimization over tensors.

**Why not practical?** The CW algorithm has enormous constant factors (the exponent improvement from 2.807 to 2.373 comes with constants that make it slower than Strassen for all feasible matrix sizes). However, it's theoretically significant for understanding the computational complexity of matrix multiplication.

### The $\omega = 2$ Conjecture

It is conjectured that $\omega = 2$ (matrix multiplication is essentially as fast as matrix addition), but proving this remains a major open problem. The best current bound is $\omega > 2$.

---

## Rectangular Matrix Multiplication

### Problem

Multiply an $n \times n^{\alpha}$ matrix by an $n^{\alpha} \times n$ matrix. The exponent depends on the shape parameter $\alpha$.

### Known Results

For the product $A_{n \times m} \cdot B_{m \times n}$:
- $m = n$: $O(n^\omega)$
- $m = 1$: $O(n^2)$ (column-vector times row-vector)
- Intermediate cases follow from the **rectangular MM conjecture**: the time is $n^{2 + o(1)}$ for $m = n^{o(1)}$.

### Applications

- **Boolean matrix multiplication**: Compute $A \cdot B$ over the Boolean semiring (OR-AND). If $AB[i][j] = \bigvee_k (A[i][k] \wedge B[k][j])$. Fast rectangular MM improves triangle detection and transitive closure.
- **Sparse matrix multiplication**: When the middle dimension $m$ is much smaller than $n$.

---

## Tensor Algorithms

### Tensor Rank

A **rank-$r$ decomposition** of a 3-tensor $T$ expresses it as $T = \sum_{i=1}^{r} u_i \otimes v_i \otimes w_i$ where $u_i, v_i, w_i$ are vectors. The **tensor rank** of $T$ is the minimum such $r$.

### Connection to Matrix Multiplication

Matrix multiplication of $n \times n$ matrices corresponds to a specific 3-tensor (the "matrix multiplication tensor") with rank $r$. If this tensor has rank $r$, then MM can be done with $r$ scalar multiplications. Strassen corresponds to finding a rank-7 decomposition of the $2 \times 2$ MM tensor (instead of the naive rank 8).

### Border Rank

The **border rank** $\underline{\text{rank}}(T)$ is the minimum $r$ such that $T$ can be approximated arbitrarily well by rank-$r$ tensors. Border rank can be strictly less than rank, and the laser method of Coppersmith-Winograd works with border rank.

---

## Randomized Linear Algebra

### Low-Rank Approximation

Given an $m \times n$ matrix $A$, find a rank-$k$ approximation $\tilde{A}$ minimizing $\|A - \tilde{A}\|_F$ (Frobenius norm). The optimal solution is given by the top-$k$ SVD, but computing it costs $O(\min(mn^2, m^2n))$.

### Randomized SVD

**Idea**: Multiply $A$ by a random matrix $\Omega$ of size $n \times (k+p)$ (where $p$ is oversampling), then compute the SVD of the much smaller $A\Omega$.

```
function randomized_svd(A, k, p=10):
    m, n = A.shape
    Omega = random_gaussian(n, k + p)
    Y = A @ Omega                    # O(mn(k+p))
    Q, R = QR(Y)                    # O(m(k+p)^2)
    B = Q.T @ A                     # O(mn(k+p))
    U_hat, S, Vt = SVD(B, k)        # O(n(k+p)^2)
    U = Q @ U_hat                   # O(mk^2)
    return U, S, Vt
```

**Complexity**: $O(mnk + (m+n)(k+p)^2)$ — much faster than full SVD when $k \ll \min(m,n)$. Provides a $(1 + \epsilon)$ approximation with high probability.

### Applications

- **Recommender systems**: Low-rank approximation of the user-item matrix.
- **Dimensionality reduction**: PCA via randomized SVD.
- **Image compression**: Approximate a matrix with a low-rank factorization.

---

## Sketching

### Frequency Estimation

Given a data stream of items, estimate the frequency of each item using sublinear space.

### Count Sketch

Maintain a $d \times w$ array of counters initialized to zero. For each item $x$, choose $d$ hash functions $h_i$ (mapping to $[0, w)$) and sign functions $s_i$ (mapping to $\{-1, +1\}$), and update:

$$\text{count}[i][h_i(x)] \mathrel{+}= s_i(x)


To estimate the frequency of $x$: take the **median** of $|\text{count}[i][h_i(x)]|$ over all $d$ rows.

**Guarantees**: With $w = O(1/\epsilon^2)$ and $d = O(\log(1/\delta))$, the estimate is within $\epsilon \|f\|_2$ with probability $1 - \delta$. Space: $O(\log(1/\delta) / \epsilon^2)$.

### Linear Sketching for Regression

To solve $\min_x \|Ax - b\|_2$ approximately, compute a sketch $SA$ and $Sb$ where $S$ is a random matrix with sub-Gaussian entries. Then solve $\min_x \|SAx - Sb\|_2$ on the sketched system. If $S$ has $O(d/\epsilon^2)$ rows (where $d$ is the numerical rank of $A$), the solution is a $(1+\epsilon)$ approximation.

### Sketching for Matrix Multiplication

To estimate $AB$, compute $SA$ and $SB$ where $S$ is a sketching matrix. Then $(SA)(SB)$ approximates $AB$ in the sense that $(SA)(SB) \approx S(AB)$. This is used in distributed settings where $A$ and $B$ are on different machines.

---

## Comparison Table

| Method | Problem | Complexity | Randomized? | Practical |
--------|---------|------------|-------------|-----------|
| Naive MM | $n \times n$ MM | $O(n^3)$ | No | Yes |
| Strassen | $n \times n$ MM | $O(n^{2.81})$ | No | Yes (with cutoff) |
| CW / VWW | $n \times n$ MM | $O(n^{2.37})$ | No | No |
| Rect. MM | $n \times m$ MM | Varies | No | Special cases |
| Randomized SVD | Low-rank approx. | $O(mnk)$ | Yes | Yes |
| Count Sketch | Freq. estimation | $O(1)$ update, $O(d)$ query | Yes | Yes |
| Linear Sketch | Regression | $O(nd^2)$ | Yes | Yes |

> **Interview Angle**: "How would you multiply two billion-by-billion matrices?" Describe the hierarchy: practical Strassen with a cutoff to naive, potentially GPU-based. For truly massive matrices, discuss block decomposition, distributed Strassen, and randomized sketching. Note that CW-class algorithms are purely theoretical.

## Further Reading

- [Ch 73: Linear Algebra](../chapters/ch73-linear-algebra.md) — standard linear algebra for CS
- [Ch 174: Matrix Exponentiation](../chapters/ch174-matrix-exponentiation.md) — matrix power for recurrences
- Strassen, "Gaussian Elimination is not Optimal" (1969)
- Coppersmith & Winograd, "Matrix Multiplication via Arithmetic Progressions" (1990)
- Woodruff, "Sketching as a Tool for Numerical Linear Algebra" (2014) — survey of randomized LA
- Alman & Williams, "A Refined Laser Method and Faster Matrix Multiplication" (2021)
