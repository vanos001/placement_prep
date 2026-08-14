# Linear Algebra for Programmers

Linear algebra is fundamental to computer graphics, machine learning, search engines, and data science. This chapter covers the essentials needed for technical interviews.

---

## Vectors

A vector is an ordered list of numbers. In programming, it's typically represented as an array.

**Key operations:**

| Operation | Definition | Complexity |
|-----------|-----------|------------|
| Addition | `c[i] = a[i] + b[i]` | O(n) |
| Scalar multiplication | `c[i] = k * a[i]` | O(n) |
| Dot product | `sum(a[i] * b[i])` | O(n) |
| Cross product | `(a₂b₃ - a₃b₂, a₃b₁ - a₁b₃, a₁b₂ - a₂b₁)` | O(1) |
| Magnitude | `sqrt(sum(a[i]²))` | O(n) |
| Cosine similarity | `dot(a,b) / (||a|| * ||b||)` | O(n) |

**Interview application:** Cosine similarity is used in recommendation systems, document similarity, and embedding-based search.

---

## Matrices

A matrix is a 2D array of numbers. Key operations:

### Matrix Multiplication

For matrices A (m×n) and B (n×p), the result C (m×p):

```
C[i][j] = sum(A[i][k] * B[k][j]) for k = 0 to n-1
```

**Time complexity:** O(m × n × p). This is the core of neural network computations.

```python
def matmul(A, B):
    m, n = len(A), len(A[0])
    n2, p = len(B), len(B[0])
    assert n == n2
    C = [[0] * p for _ in range(m)]
    for i in range(m):
        for j in range(p):
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
    return C
```

### Transpose

Swap rows and columns. A^T[i][j] = A[j][i]. O(m × n).

### Identity Matrix

Diagonal matrix with 1s on diagonal. A × I = A. Used in transformations.

---

## Determinants

The determinant is a scalar value computed from a square matrix:

- **2×2:** `det([[a,b],[c,d]]) = ad - bc`
- **Larger:** Recursive expansion by minors (Laplace expansion)

**Properties:**
- `det(AB) = det(A) × det(B)`
- `det(A^T) = det(A)`
- If det = 0, the matrix is **singular** (not invertible)
- Determinant gives the scaling factor of the transformation

---

## Eigenvalues and Eigenvectors

For a square matrix A, if `Av = λv` for some non-zero vector v, then:
- `λ` is an **eigenvalue**
- `v` is an **eigenvector**

**Intuition:** Eigenvectors are directions that don't change when the transformation is applied — they only get scaled by the eigenvalue.

**Applications in interviews:**
- **PageRank:** Google's original algorithm uses the dominant eigenvector of the link matrix
- **PCA:** Principal Component Analysis finds eigenvectors of the covariance matrix for dimensionality reduction
- **Spectral clustering:** Uses eigenvalues of the graph Laplacian
- **Markov chains:** Steady-state distribution is an eigenvector

---

## Applications

| Domain | Application | Linear Algebra Concept |
|--------|------------|----------------------|
| Machine Learning | Neural networks, linear regression | Matrix multiplication, gradients |
| Computer Graphics | Transformations, rotation, projection | Transformation matrices |
| Search Engines | PageRank | Eigenvectors |
| Recommendation | Collaborative filtering | Matrix factorization (SVD) |
| Data Science | PCA, t-SNE | Eigenvalues, matrix decomposition |
| Computer Vision | Image processing, CNNs | Convolution as matrix operation |
| Cryptography | Lattice-based crypto | Lattice reduction |

---

## Interview Questions

### Beginner

**Q: What is the dot product and what does it represent geometrically?**
The dot product of two vectors equals the product of their magnitudes times the cosine of the angle between them: `a · b = ||a|| ||b|| cos(θ)`. If the dot product is 0, the vectors are orthogonal. If positive, they point in similar directions; if negative, opposite directions.

**Q: When would you use a matrix vs a 2D array?**
Mathematically, matrices follow specific rules (multiplication, transposition, inverse). 2D arrays are just data structures. Use matrices when performing linear algebra operations; use 2D arrays for general tabular data.

### Intermediate

**Q: Why is matrix multiplication O(n³) and can it be faster?**
Naive multiplication is O(n³) for n×n matrices. Strassen's algorithm achieves O(n^2.807), and Coppersmith-Winograd achieves O(n^2.373). However, constants are large, so Strassen is only practical for very large matrices. In practice, BLAS-optimized libraries use cache-friendly blocking strategies.

**Q: What is a singular matrix and why does it matter?**
A singular matrix has determinant zero and is not invertible. In practice, this means the system of equations has no unique solution. In ML, singular matrices cause problems in linear regression (normal equations) and require regularization.

### Advanced

**Q: Explain SVD and its applications.**
Singular Value Decomposition factors any matrix A (m×n) into `A = UΣV^T` where U is m×m orthogonal, Σ is m×n diagonal (singular values), and V is n×n orthogonal. Applications include: recommender systems (matrix factorization), dimensionality reduction, image compression, noise reduction, and solving ill-conditioned linear systems.

---

## References

- Gilbert Strang, *Introduction to Linear Algebra*
- 3Blue1Brown, *Essence of Linear Algebra* (YouTube)
- [MIT OpenCourseWare 18.06](https://ocw.mit.edu/courses/mathematics/18-06-linear-algebra-spring-2010/)
