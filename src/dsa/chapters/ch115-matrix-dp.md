# Chapter 115: Matrix DP (Matrix Exponentiation)

## Prerequisites
- Matrix operations (multiplication, identity)
- Dynamic programming with linear recurrences
- Binary exponentiation (exponentiation by squaring)

## Interview Frequency: ★★
## Google, Meta, Amazon — optimizing linear recurrences

---

## 115.1 What Is Matrix DP?

**Matrix DP** (also called **Matrix Exponentiation**) is a technique that uses
matrix exponentiation to compute terms of a **linear recurrence relation** in
O(k³ log n) time instead of O(n) or O(n·k) time.

**Core Idea:** Express a linear recurrence as a matrix-vector multiplication, then
use binary exponentiation to compute the n-th power of the transformation matrix.

### When Does It Apply?

Matrix DP works when:
1. The recurrence is **linear** (each term is a linear combination of previous terms)
2. The recurrence has **constant coefficients** (coefficients don't change with n)
3. You need to compute the **n-th term** for very large n (e.g., n = 10^18)

**Common applications:**
- Fibonacci numbers
- Tribonacci and k-step recurrences
- Counting paths of length n in a graph
- DP with small state space and large number of steps

---

## 115.2 Motivation: From O(n) to O(log n)

**Standard Fibonacci:**
```
F(0) = 0, F(1) = 1
F(n) = F(n-1) + F(n-2)
```

**Naive approach:** Iterate from 2 to n → O(n) time.

**What if n = 10^18?** O(n) is too slow. But we can express the recurrence as:

```
[F(n+1)]   [1 1] [F(n)  ]
[F(n)  ] = [1 0] [F(n-1)]
```

So:
```
[F(n+1)]   [1 1]^n   [1]
[F(n)  ] = [1 0]   * [0]
```

The matrix power can be computed in O(log n) using binary exponentiation.

---

## 115.3 Intuition: Transformation Matrices

Think of a matrix as a **transformation** that maps a state vector to the next state.

**State vector:** [F(n), F(n-1)]
**Transformation:** Multiply by M = [[1,1],[1,0]] to get [F(n+1), F(n)]

Applying the transformation n times gives M^n. Since matrix multiplication is
associative, we can compute M^n using repeated squaring:
- M^1 = M
- M^2 = M · M
- M^4 = M^2 · M^2
- M^8 = M^4 · M^4
- ...

Only O(log n) multiplications are needed.

### Visualizing the Recurrence as a Graph

A linear recurrence can be viewed as a **weighted directed graph** where:
- Each node represents a "state" (e.g., the last k values)
- Edges represent transitions between states
- The weight of a path of length n gives the n-th term

Matrix exponentiation counts paths of length n in this graph.

---

## 115.4 Formal Explanation

### Linear Recurrence Definition

A **k-th order linear recurrence** has the form:

```
f(n) = c₁·f(n-1) + c₂·f(n-2) + ... + cₖ·f(n-k)
```

with initial values f(0), f(1), ..., f(k-1).

### Transformation Matrix

The state vector is [f(n), f(n-1), ..., f(n-k+1)].

The transformation matrix M is a k×k matrix:

```
    [c₁  c₂  c₃  ...  cₖ]
M = [1    0   0  ...   0 ]
    [0    1   0  ...   0 ]
    [...                   ]
    [0    0   0  ...  1  0]
```

Then:
```
[f(n+1)]        [f(n)    ]
[f(n)  ]   = M · [f(n-1)  ]
[...    ]        [...      ]
[f(n-k+2)]      [f(n-k+1)]
```

### Computing f(n)

```
[f(n)]         [f(k-1)]
[f(n-1)] = M^(n-k+1) · [f(k-2)]
[...  ]                [...    ]
[f(n-k+1)]             [f(0)  ]
```

**Time:** O(k³ · log n) for the matrix power, where k is the order of the recurrence.

---

## 115.5 Step-by-Step: Fibonacci

**Recurrence:** F(n) = F(n-1) + F(n-2), F(0) = 0, F(1) = 1

**State vector:** [F(n), F(n-1)]

**Transformation matrix:**
```
M = [1  1]
    [1  0]
```

**To compute F(10):**

1. M^1 = [[1,1],[1,0]]
2. M^2 = M·M = [[2,1],[1,1]]
3. M^4 = M^2·M^2 = [[5,3],[3,2]]
4. M^8 = M^4·M^4 = [[34,21],[21,13]]
5. M^10 = M^8·M^2 = [[89,55],[55,34]]

F(10) = M^10[0][1] = 55 ✓

---

## 115.6 Dry Run: Tribonacci

**Recurrence:** T(n) = T(n-1) + T(n-2) + T(n-3), T(0)=0, T(1)=0, T(2)=1

**State vector:** [T(n), T(n-1), T(n-2)]

**Transformation matrix:**
```
M = [1  1  1]
    [1  0  0]
    [0  1  0]
```

**To compute T(10):**

M^(10-2+1) = M^9

Let's compute step by step:
```
M^1 = [[1,1,1],[1,0,0],[0,1,0]]
M^2 = M·M = [[2,2,1],[1,1,1],[1,0,0]]
M^4 = M^2·M^2 = [[6,5,4],[4,4,3],[2,2,1]]
M^8 = M^4·M^4 = [[64,54,44],[44,38,32],[22,18,16]]
M^9 = M^8·M^1 = [[130,108,88],[88,76,60],[44,38,32]]
```

Initial vector: [T(2), T(1), T(0)] = [1, 0, 0]

T(10) = M^9[0][0] · 1 + M^9[0][1] · 0 + M^9[0][2] · 0 = 130 ✓

---

## 115.7 Implementation in C++

```cpp
#include <iostream>
#include <vector>

const long long MOD = 1e9 + 7;
using Matrix = std::vector<std::vector<long long>>;

Matrix multiply(const Matrix& a, const Matrix& b) {
    int n = a.size();
    int m = b[0].size();
    int p = b.size();
    Matrix c(n, std::vector<long long>(m, 0));
    for (int i = 0; i < n; i++)
        for (int k = 0; k < p; k++)
            for (int j = 0; j < m; j++)
                c[i][j] = (c[i][j] + a[i][k] * b[k][j]) % MOD;
    return c;
}

Matrix power(Matrix base, long long exp) {
    int n = base.size();
    Matrix result(n, std::vector<long long>(n, 0));
    for (int i = 0; i < n; i++) result[i][i] = 1;  // Identity
    while (exp > 0) {
        if (exp & 1) result = multiply(result, base);
        base = multiply(base, base);
        exp >>= 1;
    }
    return result;
}

// Fibonacci: F(n) = F(n-1) + F(n-2)
long long fibonacci(long long n) {
    if (n <= 1) return n;
    Matrix M = {{1, 1}, {1, 0}};
    Matrix Mn = power(M, n);
    return Mn[0][1];
}

// General linear recurrence: f(n) = c1*f(n-1) + c2*f(n-2) + ... + ck*f(n-k)
long long linearRecurrence(const std::vector<long long>& coeffs,
                           const std::vector<long long>& init, long long n) {
    int k = coeffs.size();
    if (n < (long long)k) return init[n];

    // Build transformation matrix
    Matrix M(k, std::vector<long long>(k, 0));
    for (int j = 0; j < k; j++) M[0][j] = coeffs[j];
    for (int i = 1; i < k; i++) M[i][i-1] = 1;

    // Compute M^(n-k+1)
    Matrix Mn = power(M, n - k + 1);

    // Multiply by initial state vector [f(k-1), f(k-2), ..., f(0)]
    long long result = 0;
    for (int j = 0; j < k; j++)
        result = (result + Mn[0][j] * init[k-1-j]) % MOD;
    return result;
}

int main() {
    // Fibonacci
    std::cout << "F(10) = " << fibonacci(10) << "\n";
    std::cout << "F(50) = " << fibonacci(50) << "\n";

    // Tribonacci: f(n) = f(n-1) + f(n-2) + f(n-3)
    std::vector<long long> coeffs = {1, 1, 1};
    std::vector<long long> init = {0, 0, 1};
    for (int i = 0; i <= 10; i++)
        std::cout << "T(" << i << ") = " << linearRecurrence(coeffs, init, i) << "\n";

    // Custom: f(n) = 2*f(n-1) + 3*f(n-2), f(0)=1, f(1)=1
    std::vector<long long> c2 = {2, 3};
    std::vector<long long> init2 = {1, 1};
    for (int i = 0; i <= 8; i++)
        std::cout << "Custom(" << i << ") = " << linearRecurrence(c2, init2, i) << "\n";

    return 0;
}
```

---

## 115.8 Implementation in Python

```python
MOD = 10**9 + 7

def mat_mult(A, B):
    """Multiply two matrices modulo MOD."""
    n, p, m = len(A), len(B), len(B[0])
    C = [[0] * m for _ in range(n)]
    for i in range(n):
        for k in range(p):
            for j in range(m):
                C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % MOD
    return C

def mat_pow(M, exp):
    """Compute M^exp using binary exponentiation."""
    n = len(M)
    # Identity matrix
    result = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    while exp > 0:
        if exp & 1:
            result = mat_mult(result, M)
        M = mat_mult(M, M)
        exp >>= 1
    return result

def fibonacci(n):
    """Compute F(n) using matrix exponentiation."""
    if n <= 1:
        return n
    M = [[1, 1], [1, 0]]
    Mn = mat_pow(M, n)
    return Mn[0][1]

def linear_recurrence(coeffs, init, n):
    """
    Compute f(n) for a general linear recurrence:
    f(n) = coeffs[0]*f(n-1) + coeffs[1]*f(n-2) + ... + coeffs[k-1]*f(n-k)
    """
    k = len(coeffs)
    if n < k:
        return init[n]

    # Build transformation matrix
    M = [[0] * k for _ in range(k)]
    for j in range(k):
        M[0][j] = coeffs[j]
    for i in range(1, k):
        M[i][i-1] = 1

    # Compute M^(n-k+1)
    Mn = mat_pow(M, n - k + 1)

    # Multiply by initial vector [f(k-1), f(k-2), ..., f(0)]
    result = 0
    for j in range(k):
        result = (result + Mn[0][j] * init[k-1-j]) % MOD
    return result


# Examples
print(f"F(10) = {fibonacci(10)}")
print(f"F(50) = {fibonacci(50)}")

# Tribonacci
coeffs = [1, 1, 1]
init = [0, 0, 1]
for i in range(11):
    print(f"T({i}) = {linear_recurrence(coeffs, init, i)}")

# Custom recurrence: f(n) = 2*f(n-1) + 3*f(n-2)
c2 = [2, 3]
init2 = [1, 1]
for i in range(9):
    print(f"Custom({i}) = {linear_recurrence(c2, init2, i)}")
```

---

## 115.9 Implementation in Java

```java
public class MatrixDP {
    static final long MOD = 1_000_000_007;

    static long[][] multiply(long[][] a, long[][] b) {
        int n = a.length, p = b.length, m = b[0].length;
        long[][] c = new long[n][m];
        for (int i = 0; i < n; i++)
            for (int k = 0; k < p; k++)
                for (int j = 0; j < m; j++)
                    c[i][j] = (c[i][j] + a[i][k] * b[k][j]) % MOD;
        return c;
    }

    static long[][] matPow(long[][] base, long exp) {
        int n = base.length;
        long[][] result = new long[n][n];
        for (int i = 0; i < n; i++) result[i][i] = 1; // Identity
        while (exp > 0) {
            if ((exp & 1) == 1) result = multiply(result, base);
            base = multiply(base, base);
            exp >>= 1;
        }
        return result;
    }

    static long fibonacci(long n) {
        if (n <= 1) return n;
        long[][] M = {{1, 1}, {1, 0}};
        long[][] Mn = matPow(M, n);
        return Mn[0][1];
    }

    static long linearRecurrence(long[] coeffs, long[] init, long n) {
        int k = coeffs.length;
        if (n < k) return init[(int)n];

        long[][] M = new long[k][k];
        for (int j = 0; j < k; j++) M[0][j] = coeffs[j];
        for (int i = 1; i < k; i++) M[i][i-1] = 1;

        long[][] Mn = matPow(M, n - k + 1);

        long result = 0;
        for (int j = 0; j < k; j++)
            result = (result + Mn[0][j] * init[k-1-j]) % MOD;
        return result;
    }

    public static void main(String[] args) {
        System.out.println("F(10) = " + fibonacci(10));
        System.out.println("F(50) = " + fibonacci(50));

        long[] coeffs = {1, 1, 1};
        long[] init = {0, 0, 1};
        for (int i = 0; i <= 10; i++)
            System.out.println("T(" + i + ") = " + linearRecurrence(coeffs, init, i));
    }
}
```

---

## 115.10 Complexity Analysis

| Approach | Time | Space |
|---|---|---|
| Naive iteration | O(n · k) | O(k) |
| Matrix exponentiation | **O(k³ · log n)** | O(k²) |

Where k is the order of the recurrence (size of state vector).

**When to use Matrix DP:**
- n is very large (10^12, 10^18)
- k is small (typically ≤ 10-20)
- MOD is given (common in competitive programming)

**When NOT to use Matrix DP:**
- n is small (< 10^6) → just iterate
- k is very large (> 100) → k³ log n may be worse than O(n·k)

---

## 115.11 Counting Paths in Graphs

**Problem:** Count the number of walks of length n from node i to node j in a graph.

**Solution:** Let A be the adjacency matrix. Then A^n[i][j] = number of walks of
length n from i to j.

```cpp
// Count walks of length n in a graph
long long countWalks(const std::vector<std::vector<int>>& adj, int n,
                     int start, int end) {
    int V = adj.size();
    Matrix A(V, std::vector<long long>(V, 0));
    for (int i = 0; i < V; i++)
        for (int j : adj[i])
            A[i][j]++;

    Matrix An = power(A, n);
    return An[start][end];
}
```

**Example:** In a graph with edges 0→1, 1→2, 2→0 (cycle):
- A = [[0,1,0],[0,0,1],[1,0,0]]
- A^3 = [[1,0,0],[0,1,0],[0,0,1]] (identity, each node returns to itself in 3 steps)

---

## 115.12 Matrix DP with State Compression

Sometimes the DP state has multiple dimensions, but the total number of states is
small. We can **flatten** the state into a vector and build a transformation matrix.

**Example:** Count number of binary strings of length n with no two consecutive 1s.

**States:**
- State 0: last bit is 0
- State 1: last bit is 1

**Transitions:**
- 0 → 0 (append 0): allowed
- 0 → 1 (append 1): allowed
- 1 → 0 (append 0): allowed
- 1 → 1 (append 1): NOT allowed

**Transformation matrix:**
```
M = [1  1]   (from 0: can go to 0 or 1)
    [1  0]   (from 1: can only go to 0)
```

This is the same as Fibonacci! The count is F(n+2).

---

## 115.13 Practice Problems

1. **Fibonacci (SPOJ FIBOSUM):** Compute sum of Fibonacci numbers in a range
2. **Tribonacci:** Compute T(n) for large n
3. **SPOJ MPOW:** Matrix power
4. **Count paths of length n** in a directed graph
5. **Binary strings without consecutive 1s** for large n
6. **Number of ways to tile** a 2×n grid with dominoes (Fibonacci variant)

---

## 115.14 Interview Questions

1. **Q:** When would you use matrix exponentiation over simple iteration?
   **A:** When n is very large (e.g., 10^18) and the recurrence order k is small
   (e.g., ≤ 20). Matrix exponentiation computes the answer in O(k³ log n) time.

2. **Q:** How do you construct the transformation matrix for a given recurrence?
   **A:** The first row contains the recurrence coefficients. Each subsequent row
   shifts the state by one position (identity pattern below the first row).

3. **Q:** Can matrix exponentiation handle non-linear recurrences?
   **A:** No. The recurrence must be linear (each term is a linear combination of
   previous terms). Non-linear terms (like f(n-1)·f(n-2)) cannot be expressed as
   matrix multiplication.

4. **Q:** How do you handle modulo arithmetic with matrix exponentiation?
   **A:** Take the modulo at each step of the matrix multiplication to prevent
   overflow. This works because (a·b) mod m = ((a mod m)·(b mod m)) mod m.

---

## 115.15 Advanced: Matrix Exponentiation for DP Transitions

**Problem:** A DP has states 0 to S-1. Each step, you transition from state i to
state j with some cost. After n steps, what is the total cost?

**Solution:** Build a transformation matrix T where T[i][j] = transition cost from
i to j. The answer is T^n[start][end].

This generalizes to:
- **Weighted paths:** T[i][j] = weight of edge i→j
- **Probabilities:** T[i][j] = probability of transitioning i→j
- **Counting:** T[i][j] = number of ways to transition i→j

---

## 115.16 Related Topics

| Topic | Chapter | Connection |
|---|---|---|
| Binary Exponentiation | Ch. 06 | Core technique behind matrix power |
| Linear Algebra | Math Ch. | Matrix operations |
| DP Optimization | Ch. 114 | Reducing DP complexity |
| Graph Algorithms | Ch. 50-60 | Path counting via adjacency matrix |
| Alien Trick | Ch. 116 | Another DP optimization |

---

## Summary

| Application | Matrix Size | Time |
|---|---|---|
| Fibonacci | 2×2 | O(log n) |
| k-step recurrence | k×k | O(k³ log n) |
| Count paths of length n | V×V | O(V³ log n) |
| State compression DP | S×S | O(S³ log n) |

**Key Takeaway:** Matrix exponentiation converts O(n) iteration into O(log n) by
expressing the recurrence as a matrix power. It's the go-to technique for linear
recurrences with very large n and small state space.
