# Chapter 73: Linear Algebra for Programming

## Prerequisites
- Basic math (algebra, arithmetic)
- Matrix operations

## Interview Frequency: ★★

Linear algebra appears in matrix exponentiation, graph algorithms, and optimization problems. **Google** and competitive programming interviews occasionally test matrix operations.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Matrix multiplication | ★★★ | Easy | Foundation |
| Matrix exponentiation | ★★★★ | Medium | Fibonacci, recurrences |
| Gaussian elimination | ★★ | Medium | Linear systems |
| Determinant | ★★ | Medium | Invertibility, volume |
| Modular matrix ops | ★★ | Medium | Competitive programming |

---

## Definition

A **matrix** is a rectangular array of numbers. **Matrix multiplication** combines two matrices to produce a third. **Matrix exponentiation** raises a matrix to a power efficiently using repeated squaring.

## Motivation

- **Recurrences**: Fibonacci, k-step recurrences solved in O(k³ log n)
- **Graph algorithms**: Count paths of length k, compute reachability
- **Optimization**: Linear systems, least squares
- **Competitive programming**: Counting problems with state transitions

## Intuition

Matrix exponentiation is like "fast-forwarding" a recurrence. Instead of computing step by step (O(n)), we jump ahead by squaring the transition matrix (O(log n)).

---

## 73.1 Matrix Operations

### Matrix Multiplication

For matrices A (n×p) and B (p×m), C = A·B where C[i][j] = Σ_k A[i][k] · B[k][j].

```cpp
#include <iostream>
#include <vector>

using Matrix = std::vector<std::vector<long long>>;
const long long MOD = 1e9 + 7;

Matrix multiply(const Matrix& a, const Matrix& b) {
    int n = a.size(), m = b[0].size(), p = b.size();
    Matrix c(n, std::vector<long long>(m, 0));
    for (int i = 0; i < n; i++)
        for (int k = 0; k < p; k++)
            for (int j = 0; j < m; j++)
                c[i][j] = (c[i][j] + a[i][k] * b[k][j]) % MOD;
    return c;
}
```

### Matrix Exponentiation

```cpp
Matrix power(Matrix base, long long exp) {
    int n = base.size();
    Matrix result(n, std::vector<long long>(n, 0));
    for (int i = 0; i < n; i++) result[i][i] = 1; // Identity

    while (exp > 0) {
        if (exp & 1) result = multiply(result, base);
        base = multiply(base, base);
        exp >>= 1;
    }
    return result;
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Multiply (n×n) | O(n³) | O(n²) |
| Power (n×n, exp=e) | O(n³ log e) | O(n²) |

---

## 73.2 Applications

### Fibonacci via Matrix Exponentiation

```
[F(n+1)]   [1 1] [F(n)  ]
[F(n)  ] = [1 0] [F(n-1)]
```

```cpp
long long fibonacci(long long n) {
    if (n <= 1) return n;
    Matrix M = {{1, 1}, {1, 0}};
    Matrix Mn = power(M, n);
    return Mn[0][1];
}
```

### Count Paths of Length K

```cpp
long long countPaths(const std::vector<std::vector<int>>& adj, int k,
                     int start, int end) {
    int n = adj.size();
    Matrix M(n, std::vector<long long>(n, 0));
    for (int i = 0; i < n; i++)
        for (int j : adj[i]) M[i][j] = 1;
    Matrix Mk = power(M, k);
    return Mk[start][end];
}
```

### K-Step Recurrence

For F(n) = a₁F(n-1) + a₂F(n-2) + ... + aₖF(n-k):

```
[F(n)  ]   [a₁ a₂ ... aₖ] [F(n-1)]
[F(n-1)]   [1  0  ... 0 ] [F(n-2)]
[  ... ] = [0  1  ... 0 ] [  ... ]
[F(n-k+1)] [0  0  ... 1 ] [F(n-k)]
```

---

## 73.3 Gaussian Elimination

Solve Ax = b in O(n³).

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>

std::vector<double> gaussianElimination(std::vector<std::vector<double>> A,
                                         std::vector<double> b) {
    int n = A.size();

    for (int col = 0; col < n; col++) {
        int maxRow = col;
        for (int row = col + 1; row < n; row++)
            if (std::abs(A[row][col]) > std::abs(A[maxRow][col]))
                maxRow = row;
        std::swap(A[col], A[maxRow]);
        std::swap(b[col], b[maxRow]);

        for (int row = col + 1; row < n; row++) {
            double factor = A[row][col] / A[col][col];
            for (int j = col; j < n; j++)
                A[row][j] -= factor * A[col][j];
            b[row] -= factor * b[col];
        }
    }

    std::vector<double> x(n);
    for (int i = n - 1; i >= 0; i--) {
        x[i] = b[i];
        for (int j = i + 1; j < n; j++)
            x[i] -= A[i][j] * x[j];
        x[i] /= A[i][i];
    }
    return x;
}

int main() {
    std::vector<std::vector<double>> A = {{2, 1}, {1, 3}};
    std::vector<double> b = {5, 7};
    auto x = gaussianElimination(A, b);
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "x = " << x[0] << ", y = " << x[1] << "\n";
    return 0;
}
```

---

## 73.4 Matrix Determinant

Compute determinant via Gaussian elimination (product of pivots).

```cpp
long long determinant(Matrix A) {
    int n = A.size();
    long long det = 1;
    for (int col = 0; col < n; col++) {
        int pivot = col;
        for (int row = col + 1; row < n; row++)
            if (std::abs(A[row][col]) > std::abs(A[pivot][col]))
                pivot = row;
        if (pivot != col) { std::swap(A[col], A[pivot]); det = -det; }
        if (A[col][col] == 0) return 0;
        det = det * A[col][col] % MOD;
        // Eliminate below (for modular: use modular inverse)
    }
    return det;
}
```

---

## 73.5 Modular Matrix Operations

For competitive programming, compute matrix operations modulo a prime.

```cpp
long long modPow(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

long long modInverse(long long a, long long mod) {
    return modPow(a, mod - 2, mod);
}
```

---

## Python Implementation

```python
import sys

def mat_mult(A, B, mod=10**9+7):
    n, m, p = len(A), len(B[0]), len(B)
    C = [[0]*m for _ in range(n)]
    for i in range(n):
        for k in range(p):
            for j in range(m):
                C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % mod
    return C

def mat_pow(M, exp, mod=10**9+7):
    n = len(M)
    result = [[1 if i==j else 0 for j in range(n)] for i in range(n)]
    while exp > 0:
        if exp & 1:
            result = mat_mult(result, M, mod)
        M = mat_mult(M, M, mod)
        exp >>= 1
    return result

def fibonacci(n):
    if n <= 1: return n
    M = [[1,1],[1,0]]
    return mat_pow(M, n)[0][1]

print(f"F(10) = {fibonacci(10)}")
print(f"F(50) = {fibonacci(50)}")
```

## Java Implementation

```java
public class MatrixOps {
    static final long MOD = 1_000_000_007;

    static long[][] multiply(long[][] a, long[][] b) {
        int n = a.length, m = b[0].length, p = b.length;
        long[][] c = new long[n][m];
        for (int i = 0; i < n; i++)
            for (int k = 0; k < p; k++)
                for (int j = 0; j < m; j++)
                    c[i][j] = (c[i][j] + a[i][k] * b[k][j]) % MOD;
        return c;
    }

    static long[][] power(long[][] base, long exp) {
        int n = base.length;
        long[][] result = new long[n][n];
        for (int i = 0; i < n; i++) result[i][i] = 1;
        while (exp > 0) {
            if ((exp & 1) == 1) result = multiply(result, base);
            base = multiply(base, base);
            exp >>= 1;
        }
        return result;
    }

    static long fibonacci(long n) {
        if (n <= 1) return n;
        long[][] M = {{1,1},{1,0}};
        return power(M, n)[0][1];
    }

    public static void main(String[] args) {
        System.out.println("F(10) = " + fibonacci(10));
        System.out.println("F(50) = " + fibonacci(50));
    }
}
```

---

## Exercises

1. **Tribonacci**: Compute F(n) for the recurrence F(n) = F(n-1) + F(n-2) + F(n-3) using matrix exponentiation.

2. **Count paths**: Given an adjacency matrix, count the number of walks of length exactly k from node 0 to node n-1.

3. **Determinant mod p**: Compute the determinant of an n×n matrix modulo a prime p.

4. **System of equations**: Solve a system of 3 linear equations using Gaussian elimination.

5. **Matrix inverse**: Implement matrix inverse using Gauss-Jordan elimination.

---

## Interview Questions

1. **Q: How do you compute Fibonacci in O(log n)?**
   A: Use matrix exponentiation. [[1,1],[1,0]]^n gives F(n+1) and F(n). Repeated squaring computes the power in O(log n) matrix multiplications, each O(1) for 2×2 matrices.

2. **Q: When is matrix exponentiation applicable?**
   A: When the recurrence is linear (each term is a linear combination of previous terms). The transition matrix encodes the recurrence, and raising it to the n-th power gives the n-th term.

3. **Q: What's the time complexity of Gaussian elimination?**
   A: O(n³) for an n×n system. The forward elimination is O(n³), back substitution is O(n²).

4. **Q: How do you count paths of length k in a graph?**
   A: Raise the adjacency matrix to the k-th power. Entry (i,j) of A^k gives the number of walks of length k from i to j.

---

## Cross-References
- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md) — Matrix exponentiation as a DP optimization
- [Chapter 82: Advanced Shortest Paths](ch82-advanced-shortest-paths.md) — Floyd-Warshall uses matrix operations
- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — Adjacency matrix representation

---

## Summary

| Operation | Time | Application |
|---|---|---|
| Matrix multiply | O(n³) | Foundation |
| Matrix power | O(n³ log k) | Recurrences, path counting |
| Gaussian elimination | O(n³) | Linear systems |
| Determinant | O(n³) | Volume, invertibility |
