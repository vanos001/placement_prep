# Chapter 174: Matrix Exponentiation

## 1. Introduction

**Matrix exponentiation** is a powerful technique for solving linear recurrences in O(k³ log n) time, where k is the order of the recurrence and n is the term index. By expressing a recurrence relation as a matrix multiplication, we can use fast matrix exponentiation (binary exponentiation on matrices) to compute the n-th term efficiently.

### Why Should You Care?

- **Fibonacci in O(log n)**: Compute F(10^18) without iterating through all terms.
- **Counting Paths**: Count paths of length exactly n in a graph.
- **Competitive Programming**: A staple technique for problems involving linear recurrences.
- **Dynamic Programming Optimization**: Speed up DP with linear transitions from O(n) to O(k³ log n).
- **String Problems**: Count strings of length n avoiding certain patterns.

---

## 2. Motivation: From Recurrence to Matrix

### 2.1 The Problem with Naive Recursion

Consider the Fibonacci sequence:
```
F(0) = 0, F(1) = 1
F(n) = F(n-1) + F(n-2)
```

Computing F(n) naively is O(n) with iteration or O(2^n) with naive recursion. For n = 10^18, both are impossible.

### 2.2 The Key Insight

We can express the recurrence as a matrix equation:

```
[F(n)  ]   = [1  1] × [F(n-1)]
[F(n-1)]     [1  0]   [F(n-2)]
```

Therefore:
```
[F(n)  ]   = [1  1]^(n-1) × [F(1)]
[F(n-1)]     [1  0]          [F(0)]
```

Computing M^(n-1) via binary exponentiation takes O(k³ log n) time, where k = 2 for Fibonacci.

---

## 3. Matrix Multiplication

### 3.1 Definition

Given matrices A (m × k) and B (k × n), their product C = A × B is an m × n matrix where:

\\[C_{ij} = \sum_{p=0}^{k-1} A_{ip} \cdot B_{pj}\\]

### 3.2 Properties

- **Associative**: (AB)C = A(BC)
- **Distributive**: A(B+C) = AB + AC
- **NOT commutative**: AB ≠ BA in general
- **Identity**: AI = IA = A

### 3.3 Complexity

Multiplying two k × k matrices: O(k³).

---

## 4. Binary Exponentiation on Matrices

### 4.1 Algorithm

To compute M^n:

```
function mat_pow(M, n):
    result = Identity matrix of same size
    while n > 0:
        if n is odd:
            result = result × M
        M = M × M
        n = n / 2
    return result
```

### 4.2 Complexity

- Matrix multiplication: O(k³) for k × k matrices.
- Binary exponentiation: O(log n) multiplications.
- **Total: O(k³ log n)**.

---

## 5. Building the Transition Matrix

### 5.1 General Method

For a linear recurrence of order k:
```
f(n) = c₁·f(n-1) + c₂·f(n-2) + ... + cₖ·f(n-k)
```

The transition matrix T is:

```
T = [c₁  c₂  c₃  ...  cₖ]
    [1   0   0   ...  0 ]
    [0   1   0   ...  0 ]
    [   ...              ]
    [0   0   ...  1   0 ]
```

And:
```
[f(n)  ]         [f(k)  ]
[f(n-1)]  = T^(n-k) × [f(k-1)]
[ ...  ]         [ ...  ]
[f(n-k+1)]       [f(1)  ]
```

### 5.2 Example: Tribonacci

```
T(n) = T(n-1) + T(n-2) + T(n-3)
T(0) = 0, T(1) = 0, T(2) = 1
```

Transition matrix:
```
[1  1  1]
[1  0  0]
[0  1  0]
```

To find T(n):
```
[T(n)  ]       [T(2)]   [1]
[T(n-1)] = M^(n-2) × [T(1)] = M^(n-2) × [0]
[T(n-2)]       [T(0)]   [0]
```

---

## 6. Step-by-Step Walkthrough

### 6.1 Computing F(10)

Fibonacci: F(n) = F(n-1) + F(n-2), F(0)=0, F(1)=1.

**Step 1**: Define transition matrix.
```
M = [1  1]
    [1  0]
```

**Step 2**: Compute M^9 (since we start from [F(1), F(0)]).
```
M^1 = [1  1]    M^2 = [2  1]
      [1  0]          [1  1]

M^4 = M^2 × M^2 = [5  3]
                    [3  2]

M^8 = M^4 × M^4 = [34  21]
                    [21  13]

M^9 = M^8 × M = [55  34]
                  [34  21]
```

**Step 3**: Apply to initial vector.
```
[F(10)]   = M^9 × [F(1)]   = [55  34] × [1]   = [55]
[ F(9)]           [F(0)]     [34  21]   [0]     [34]
```

**Result**: F(10) = 55. ✓

### 6.2 Dry Run: M^9 Computation

```
Binary of 9 = 1001

result = I = [1  0]
             [0  1]
base = M = [1  1]
           [1  0]

Step 1: n=9 (odd)
  result = I × M = M = [1  1]
                        [1  0]
  base = M² = [2  1]
              [1  1]
  n = 4

Step 2: n=4 (even)
  base = M⁴ = [5  3]
              [3  2]
  n = 2

Step 3: n=2 (even)
  base = M⁸ = [34  21]
              [21  13]
  n = 1

Step 4: n=1 (odd)
  result = [1  1] × [34  21] = [55  34]
           [1  0]   [21  13]   [34  21]
  n = 0

Done! M⁹ = [55  34]
            [34  21]
```

---

## 7. Applications

### 7.1 Fibonacci with Arbitrary Modulus

Compute F(n) mod p for large n:

```python
def fib_mod(n, mod):
    if n <= 1:
        return n
    def mat_mul(A, B):
        return [[(A[0][0]*B[0][0] + A[0][1]*B[1][0]) % mod,
                 (A[0][0]*B[0][1] + A[0][1]*B[1][1]) % mod],
                [(A[1][0]*B[0][0] + A[1][1]*B[1][0]) % mod,
                 (A[1][0]*B[0][1] + A[1][1]*B[1][1]) % mod]]
    
    def mat_pow(M, p):
        result = [[1, 0], [0, 1]]
        while p > 0:
            if p & 1:
                result = mat_mul(result, M)
            M = mat_mul(M, M)
            p >>= 1
        return result
    
    M = mat_pow([[1, 1], [1, 0]], n)
    return M[0][1]  # F(n) is in position [0][1]
```

### 7.2 Counting Paths of Length n

Given an adjacency matrix A of a graph, A^n[i][j] gives the number of paths of length exactly n from node i to node j.

**Example**: Graph with 3 nodes, edges: 0→1, 1→2, 2→0, 1→1.

```
A = [0  1  0]
    [0  1  1]
    [1  0  0]

A² = [0  1  1]
     [1  1  1]
     [0  1  0]

Number of paths of length 2 from 0 to 2: A²[0][2] = 1.
Path: 0→1→2.
```

### 7.3 Counting Strings

**Problem**: Count binary strings of length n that don't contain "11" as a substring.

**States**: 
- State 0: last character is 0
- State 1: last character is 1

**Transitions**:
- From state 0: can append 0 (→ state 0) or 1 (→ state 1)
- From state 1: can append 0 (→ state 0) only

**Transition matrix**:
```
T = [1  1]   (from state 0: to 0 and to 1)
    [1  0]   (from state 1: to 0 only)
```

Wait — this is the Fibonacci matrix! Indeed, the count of valid strings of length n is F(n+2).

### 7.4 DP with Linear Transitions

Any DP of the form:
```
dp[i] = Σ cⱼ · dp[i - j]   for j = 1..k
```

can be solved with matrix exponentiation if k is small and n is large.

**Example**: Count ways to climb stairs with steps of size 1, 2, or 3.
```
dp[i] = dp[i-1] + dp[i-2] + dp[i-3]
```

Transition matrix (3×3):
```
[1  1  1]
[1  0  0]
[0  1  0]
```

### 7.5 Linear Recurrences with Extra Terms

If the recurrence has constant terms:
```
f(n) = 2·f(n-1) + 3·f(n-2) + 5
```

Add a dummy state for the constant:
```
[f(n)  ]   [2  3  5]   [f(n-1)]
[f(n-1)] = [1  0  0] × [f(n-2)]
[1     ]   [0  0  1]   [1     ]
```

---

## 8. Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| Matrix multiplication (k×k) | O(k³) | O(k²) |
| Matrix exponentiation | O(k³ log n) | O(k²) |
| Total for recurrence | O(k³ log n) | O(k²) |

For Fibonacci (k=2): O(8 log n) = O(log n).
For order-10 recurrence: O(1000 log n).

---

## 9. Code Implementations

### 9.1 C++ — Matrix Exponentiation

```cpp
#include <bits/stdc++.h>
using namespace std;

typedef long long ll;
typedef vector<vector<ll>> Matrix;

const ll MOD = 1e9 + 7;

Matrix matMul(const Matrix& A, const Matrix& B) {
    int n = A.size(), m = B[0].size(), p = B.size();
    Matrix C(n, vector<ll>(m, 0));
    for (int i = 0; i < n; i++)
        for (int k = 0; k < p; k++)
            for (int j = 0; j < m; j++)
                C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % MOD;
    return C;
}

Matrix matPow(Matrix M, ll power) {
    int n = M.size();
    Matrix result(n, vector<ll>(n, 0));
    for (int i = 0; i < n; i++) result[i][i] = 1; // Identity

    while (power > 0) {
        if (power & 1)
            result = matMul(result, M);
        M = matMul(M, M);
        power >>= 1;
    }
    return result;
}

ll fibonacci(ll n) {
    if (n <= 1) return n;
    Matrix M = {{1, 1}, {1, 0}};
    Matrix R = matPow(M, n);
    return R[0][1]; // F(n)
}

// General linear recurrence: f(n) = c[0]*f(n-1) + c[1]*f(n-2) + ...
ll linearRecurrence(vector<ll>& coeffs, vector<ll>& init, ll n) {
    int k = coeffs.size();
    if (n < k) return init[n];

    // Build transition matrix
    Matrix T(k, vector<ll>(k, 0));
    for (int j = 0; j < k; j++) T[0][j] = coeffs[j];
    for (int i = 1; i < k; i++) T[i][i-1] = 1;

    Matrix R = matPow(T, n - k + 1);

    ll result = 0;
    for (int j = 0; j < k; j++)
        result = (result + R[0][j] * init[k - 1 - j]) % MOD;
    return result;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Fibonacci
    ll n;
    cin >> n;
    cout << fibonacci(n) << "\n";

    // General recurrence example: Tribonacci
    // T(n) = T(n-1) + T(n-2) + T(n-3), T(0)=0, T(1)=0, T(2)=1
    vector<ll> coeffs = {1, 1, 1};
    vector<ll> init = {0, 0, 1};
    cout << linearRecurrence(coeffs, init, n) << "\n";

    return 0;
}
```

### 9.2 Python — Matrix Exponentiation

```python
def mat_mul(A, B, mod):
    """Multiply two matrices A and B modulo mod."""
    n, m, p = len(A), len(B[0]), len(B)
    C = [[0] * m for _ in range(n)]
    for i in range(n):
        for k in range(p):
            for j in range(m):
                C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % mod
    return C

def mat_pow(M, power, mod):
    """Compute M^power modulo mod using binary exponentiation."""
    n = len(M)
    result = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    while power > 0:
        if power & 1:
            result = mat_mul(result, M, mod)
        M = mat_mul(M, M, mod)
        power >>= 1
    return result

def fibonacci(n, mod=10**9+7):
    """Compute F(n) modulo mod in O(log n)."""
    if n <= 1:
        return n
    M = [[1, 1], [1, 0]]
    R = mat_pow(M, n, mod)
    return R[0][1]

def linear_recurrence(coeffs, init, n, mod=10**9+7):
    """
    Compute f(n) where f(n) = sum(coeffs[i] * f(n-1-i)).
    coeffs: [c1, c2, ..., ck]
    init: [f(0), f(1), ..., f(k-1)]
    """
    k = len(coeffs)
    if n < k:
        return init[n] % mod

    # Build transition matrix
    T = [[0] * k for _ in range(k)]
    for j in range(k):
        T[0][j] = coeffs[j] % mod
    for i in range(1, k):
        T[i][i-1] = 1

    R = mat_pow(T, n - k + 1, mod)

    result = 0
    for j in range(k):
        result = (result + R[0][j] * init[k - 1 - j]) % mod
    return result

if __name__ == "__main__":
    n = int(input())
    MOD = 10**9 + 7
    print(fibonacci(n, MOD))

    # Tribonacci: T(n) = T(n-1) + T(n-2) + T(n-3)
    coeffs = [1, 1, 1]
    init = [0, 0, 1]
    print(linear_recurrence(coeffs, init, n, MOD))
```

### 9.3 Java — Matrix Exponentiation

```java
import java.util.*;

public class MatrixExponentiation {
    static final long MOD = 1_000_000_007;

    static long[][] matMul(long[][] A, long[][] B) {
        int n = A.length, m = B[0].length, p = B.length;
        long[][] C = new long[n][m];
        for (int i = 0; i < n; i++)
            for (int k = 0; k < p; k++)
                for (int j = 0; j < m; j++)
                    C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % MOD;
        return C;
    }

    static long[][] matPow(long[][] M, long power) {
        int n = M.length;
        long[][] result = new long[n][n];
        for (int i = 0; i < n; i++) result[i][i] = 1;

        while (power > 0) {
            if ((power & 1) == 1)
                result = matMul(result, M);
            M = matMul(M, M);
            power >>= 1;
        }
        return result;
    }

    static long fibonacci(long n) {
        if (n <= 1) return n;
        long[][] M = {{1, 1}, {1, 0}};
        long[][] R = matPow(M, n);
        return R[0][1];
    }

    static long linearRecurrence(long[] coeffs, long[] init, long n) {
        int k = coeffs.length;
        if (n < k) return init[(int)n] % MOD;

        long[][] T = new long[k][k];
        for (int j = 0; j < k; j++) T[0][j] = coeffs[j] % MOD;
        for (int i = 1; i < k; i++) T[i][i-1] = 1;

        long[][] R = matPow(T, n - k + 1);

        long result = 0;
        for (int j = 0; j < k; j++)
            result = (result + R[0][j] * init[k - 1 - j]) % MOD;
        return result;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        long n = sc.nextLong();
        System.out.println(fibonacci(n));

        // Tribonacci
        long[] coeffs = {1, 1, 1};
        long[] init = {0, 0, 1};
        System.out.println(linearRecurrence(coeffs, init, n));
    }
}
```

### 9.4 C++ — Count Paths of Length n

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
typedef vector<vector<ll>> Matrix;
const ll MOD = 1e9 + 7;

Matrix matMul(const Matrix& A, const Matrix& B) {
    int n = A.size(), m = B[0].size(), p = B.size();
    Matrix C(n, vector<ll>(m, 0));
    for (int i = 0; i < n; i++)
        for (int k = 0; k < p; k++)
            for (int j = 0; j < m; j++)
                C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % MOD;
    return C;
}

Matrix matPow(Matrix M, ll power) {
    int n = M.size();
    Matrix result(n, vector<ll>(n, 0));
    for (int i = 0; i < n; i++) result[i][i] = 1;
    while (power > 0) {
        if (power & 1) result = matMul(result, M);
        M = matMul(M, M);
        power >>= 1;
    }
    return result;
}

// Count paths of length exactly n from node u to node v
ll countPaths(const vector<vector<int>>& adj, int u, int v, ll n) {
    int sz = adj.size();
    Matrix M(sz, vector<ll>(sz, 0));
    for (int i = 0; i < sz; i++)
        for (int j : adj[i])
            M[i][j]++;

    Matrix R = matPow(M, n);
    return R[u][v];
}
```

---

## 10. Advanced Applications

### 10.1 Matrix Exponentiation with Modulo

Always apply modulo after each multiplication to prevent overflow. For competitive programming, MOD is typically 10^9 + 7.

### 10.2 Large Matrix Size

For k up to ~100, O(k³ log n) is still feasible. For k = 100 and log n = 60:
- 100³ × 60 = 60,000,000 operations — fast enough.

For k = 500, it becomes 500³ × 60 = 7.5 billion — too slow. Use other techniques.

### 10.3 Exponentiating Sum Matrices

To compute Σ(i=1 to n) M^i, use the doubling technique:

```
S(n) = M + M² + ... + M^n

If n is even:
  S(n) = S(n/2) + M^(n/2) × S(n/2) = (I + M^(n/2)) × S(n/2)

If n is odd:
  S(n) = S(n-1) + M^n
```

This runs in O(k³ log n).

### 10.4 Problems with Multiple States

Some problems have states that aren't directly a linear recurrence. The key is identifying the state vector and transition matrix.

**Example**: Count sequences of length n using digits 0-9 where no two adjacent digits differ by more than 2.

- State: last digit (0-9), so k = 10.
- Transition: T[i][j] = 1 if |i-j| ≤ 2, else 0.
- Answer: sum of all entries in T^(n-1) × initial vector.

---

## 11. Common Pitfalls

1. **Wrong matrix orientation**: Ensure the transition matrix multiplies the state vector correctly.
2. **Off-by-one**: M^(n-k+1) vs M^n — check the base case alignment.
3. **Identity matrix**: For n = 0 or base cases, return the identity, not M^0.
4. **Overflow**: Always use modular arithmetic for large n.
5. **Non-linear recurrences**: Matrix exponentiation only works for linear recurrences. f(n) = f(n-1)² is NOT linear.

---

## 12. When to Use Matrix Exponentiation

| Condition | Suitable? |
|-----------|-----------|
| Linear recurrence | ✅ Yes |
| Constant coefficients | ✅ Yes |
| Large n (up to 10^18) | ✅ Yes |
| Small order k (≤ ~200) | ✅ Yes |
| Non-linear recurrence | ❌ No |
| Variable coefficients | ❌ No |
| Large k (≥ 500) | ⚠️ Marginal |

---

## 13. Exercises

### Basic
1. Compute F(10^18) mod 10^9+7 using matrix exponentiation.
2. Count the number of binary strings of length n without consecutive 1s.
3. Compute the n-th Tribonacci number.

### Intermediate
4. Count paths of length n in a given directed graph.
5. Solve: f(n) = 3f(n-1) + 2f(n-2) + f(n-3), with f(0)=1, f(1)=2, f(2)=3.
6. Count ternary strings of length n without "00" or "11" as substrings.

### Advanced
7. Compute Σ(i=1 to n) F(i) using matrix exponentiation.
8. Solve a recurrence with matrix coefficients.
9. Count the number of ways to tile a 2×n board with 1×2 dominoes.

---

## 14. Interview Questions

1. **Q**: What is the time complexity of matrix exponentiation?
   **A**: O(k³ log n), where k is the size of the transition matrix and n is the exponent.

2. **Q**: Can you compute Fibonacci in O(1) space?
   **A**: Yes, using the doubling formulas: F(2k) = F(k)(2F(k+1) - F(k)), F(2k+1) = F(k)² + F(k+1)². This avoids explicit matrix storage.

3. **Q**: When does matrix exponentiation NOT apply?
   **A**: When the recurrence is non-linear (e.g., f(n) = f(n-1)²), has variable coefficients, or when k is too large for O(k³) to be feasible.

4. **Q**: How do you handle recurrences with constant terms?
   **A**: Add a dummy state that's always 1. For f(n) = 2f(n-1) + 5, use a 2×2 matrix with the constant in an extra row/column.

5. **Q**: What's the relationship between matrix exponentiation and DP?
   **A**: Matrix exponentiation is "DP with exponentiation by squaring." Any DP with fixed-size state and linear transitions can be expressed as matrix multiplication.

---

## 15. Cross-References

- **Chapter 2 (Mathematical Foundations)**: Modular arithmetic, recurrence relations.
- **Chapter 30 (DP Fundamentals)**: Understanding linear recurrences from a DP perspective.
- **Chapter 73 (Linear Algebra for Programming)**: Matrix operations and properties.
- **Chapter 171 (Berlekamp-Massey)**: Finding the minimal polynomial of a linear recurrence.
- **Chapter 167 (FFT/NTT)**: Alternative for polynomial multiplication problems.

---

## 16. Summary

Matrix exponentiation converts linear recurrences into matrix power problems, enabling O(k³ log n) computation for arbitrarily large n. The technique requires:

1. A **linear recurrence** with constant coefficients.
2. A **small order** k (typically ≤ 200).
3. A correctly constructed **transition matrix**.

The approach is universally applicable to Fibonacci-like sequences, counting problems with finite state, and path counting in graphs. Combined with modular arithmetic, it's one of the most powerful tools in competitive programming.
