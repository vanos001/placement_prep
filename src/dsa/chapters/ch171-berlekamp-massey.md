# Chapter 171: Berlekamp-Massey Algorithm

## 1. Introduction

The **Berlekamp-Massey (BM) algorithm** finds the shortest **Linear Feedback Shift Register (LFSR)** that generates a given sequence, or equivalently, finds the **minimal linear recurrence** from the first few terms of a sequence.

In competitive programming, this is incredibly powerful: if you can compute the first ~2k terms of a sequence defined by a linear recurrence of order k, the BM algorithm can **discover the recurrence**, which you can then use to compute the *n*-th term in O(k² log n) time using matrix exponentiation.

### Why Should You Care?

- **Pattern Discovery**: Given only the first few values of a sequence, BM finds the recurrence that generates it.
- **Efficient Computation**: Once you have a recurrence of order *k*, compute any term in O(k² log n).
- **Competitive Programming**: Problems requiring O(n) computation can often be reduced to O(k² log n) where k is small.
- **Versatility**: Works for any sequence satisfying a linear recurrence over any field.

---

## 2. Problem Definition

### 2.1 Linear Recurrences

A sequence {a₀, a₁, a₂, ...} satisfies a **linear recurrence of order k** if:

\\[a_n = c_1 \cdot a_{n-1} + c_2 \cdot a_{n-2} + \cdots + c_k \cdot a_{n-k} \quad \text{for all } n \geq k\\]

**Examples**:
- Fibonacci: aₙ = aₙ₋₁ + aₙ₋₂ (order 2)
- Tribonacci: aₙ = aₙ₋₁ + aₙ₋₂ + aₙ₋₃ (order 3)
- Powers of 2: aₙ = 2·aₙ₋₁ (order 1)
- Constant sequence: aₙ = aₙ₋₁ (order 1)

### 2.2 The BM Problem

**Input**: The first 2k terms of a sequence: a₀, a₁, ..., a_{2k-1}.

**Output**: The coefficients c₁, c₂, ..., cₖ of the minimal linear recurrence.

### 2.3 Connection Polynomial

The recurrence is encoded as a **connection polynomial**:

\\[C(x) = 1 - c_1 x - c_2 x^2 - \cdots - c_k x^k\\]

The sequence satisfies the recurrence iff the generating function S(x) = Σ aᵢxⁱ obeys:

\\[C(x) \cdot S(x) \equiv P(x) \pmod{x^n}\\]

where P(x) is a polynomial of degree < k.

---

## 3. Motivation and Intuition

### 3.1 The Power of Discovery

Consider this sequence: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, ...

BM discovers: **aₙ = aₙ₋₁ + aₙ₋₂** (Fibonacci recurrence, order 2).

Now you can compute the 10¹⁸-th Fibonacci number in O(log n) time using matrix exponentiation!

### 3.2 Why 2k Terms?

A recurrence of order k has k coefficients. Each term gives one linear equation. To uniquely determine k unknowns, you need at least k equations. But you also need to verify correctness, so 2k terms provide k equations plus k verification points.

More precisely: 2k terms are both necessary and sufficient to uniquely determine the minimal LFSR.

### 3.3 Connection to Error-Correcting Codes

The algorithm was originally developed by Elwyn Berlekamp (1968) for decoding BCH codes, and later simplified by James Massey (1969) for general LFSR synthesis. The same algorithm finds applications in:
- Decoding Reed-Solomon codes
- Cryptanalysis of stream ciphers
- Finding polynomial fits for sequences

---

## 4. Background: LFSRs and Minimal Polynomials

### 4.1 Linear Feedback Shift Register

An LFSR of length k maintains k cells. At each step:
1. Output: weighted sum of all cells
2. Shift: all cells move right
3. Input: the output goes into the leftmost cell

For a recurrence aₙ = c₁aₙ₋₁ + c₂aₙ₋₂ + ... + cₖaₙ₋ₖ, the feedback coefficients are c₁, c₂, ..., cₖ.

### 4.2 Minimal Polynomial

The **minimal polynomial** of a sequence is the lowest-degree polynomial C(x) such that:

\\[\sum_{j=0}^{\deg(C)} C[j] \cdot a_{i-j} = 0 \quad \text{for all valid } i\\]

where C[0] = 1. The degree of the minimal polynomial equals the length of the shortest LFSR.

### 4.3 Discrepancy

The **discrepancy** at position i is:

\\[d_i = \sum_{j=0}^{L} C[j] \cdot a_{i-j}\\]

If dᵢ = 0 for all i, the LFSR correctly generates the entire sequence. A nonzero discrepancy means the LFSR needs updating.

---

## 5. The Berlekamp-Massey Algorithm

### 5.1 Core Idea

BM maintains the current best LFSR (connection polynomial C) and iterates through the sequence. At each step:

1. **Compute discrepancy**: Does the current LFSR correctly predict a[i]?
2. **If zero**: The LFSR works for this term. Continue.
3. **If nonzero**: Update C to eliminate the discrepancy, possibly increasing LFSR length.

### 5.2 The Update Step

When a discrepancy d is found at position i:

1. Save the current C as T.
2. Compute correction coefficient: c = d / b (where b is a stored "previous discrepancy").
3. Update: C = C - c · x^m · B (where B is a stored "previous C" and m is a step counter).
4. If the LFSR length needs to increase (2L ≤ i), update L, B, b, and reset m.

The key mathematical insight: the update C → C - c · x^m · B creates a new polynomial that has zero discrepancy at position i, while preserving zero discrepancies at all previously problematic positions.

### 5.3 Pseudocode

```
BERLEKAMP_MASSEY(a[0..n-1]):
    C = [1]           // Connection polynomial, C[0] = 1
    B = [1]           // Previous C (for update reference)
    L = 0             // Current LFSR length
    m = 1             // Steps since last length change
    b = 1             // Previous discrepancy
    
    for i = 0 to n-1:
        // Compute discrepancy d = Σ C[j] * a[i-j]
        d = a[i]
        for j = 1 to L:
            d += C[j] * a[i - j]
        
        if d == 0:
            m = m + 1
            continue
        
        // Discrepancy found: update C
        T = C
        c = d / b
        
        // Ensure C has room for the update
        while |C| < |B| + m:
            append 0 to C
        
        // C = C - c * x^m * B
        for j = 0 to |B| - 1:
            C[j + m] = C[j + m] - c * B[j]
        
        if 2 * L <= i:
            L = i + 1 - L
            B = T
            b = d
            m = 1
        else:
            m = m + 1
    
    return C   // C[0] = 1; recurrence: a[n] = -C[1]*a[n-1] - ... - C[L]*a[n-L]
```

---

## 6. Step-by-Step Walkthrough

### Example: Fibonacci Sequence

**Input**: s = [0, 1, 1, 2, 3, 5, 8, 13]

**Expected output**: C = [1, -1, -1], meaning aₙ = aₙ₋₁ + aₙ₋₂

---

**Initialization**: C = [1], B = [1], L = 0, m = 1, b = 1

**i = 0**: s[0] = 0
- d = s[0] = 0 (no inner loop since L=0)
- d == 0 → m = 2, continue

**i = 1**: s[1] = 1
- d = s[1] = 1 (no inner loop since L=0)
- d ≠ 0 → Discrepancy!
- T = [1], c = 1/1 = 1
- Resize C to |B| + m = 1 + 2 = 3: C = [1, 0, 0]
- j=0: C[2] -= 1 × B[0] = 1 → C[2] = -1
- C = [1, 0, -1]
- Check: 2L = 0 ≤ i = 1? **Yes!**
  - L = 1 + 1 - 0 = **2**
  - B = T = [1], b = 1, m = 1

**State**: C = [1, 0, -1], L = 2. This says aₙ = aₙ₋₂.

**i = 2**: s[2] = 1
- d = s[2] + C[1]×s[1] = 1 + 0×1 = 1
- d ≠ 0 → Discrepancy!
- T = [1, 0, -1], c = 1/1 = 1
- Resize C to max(3, 1+1) = 3: no change
- j=0: C[1] -= 1 × B[0] = 1 → C[1] = -1
- C = [1, -1, -1]
- Check: 2L = 4 ≤ i = 2? **No.**
  - m = 2

**State**: C = [1, -1, -1], L = 2. This says aₙ = aₙ₋₁ + aₙ₋₂. **Fibonacci!**

**i = 3**: s[3] = 2
- d = s[3] + C[1]×s[2] + C[2]×s[1] = 2 + (-1)×1 + (-1)×1 = 0 ✓
- m = 3, continue

**i = 4**: s[4] = 3
- d = 3 + (-1)×2 + (-1)×1 = 0 ✓
- m = 4, continue

**i = 5**: s[5] = 5
- d = 5 + (-1)×3 + (-1)×2 = 0 ✓
- m = 5, continue

**i = 6**: s[6] = 8
- d = 8 + (-1)×5 + (-1)×3 = 0 ✓
- m = 6, continue

**i = 7**: s[7] = 13
- d = 13 + (-1)×8 + (-1)×5 = 0 ✓
- m = 7, continue

**Result**: C = [1, -1, -1] → **aₙ = aₙ₋₁ + aₙ₋₂** ✓

---

## 7. Implementation

### 7.1 C++ Implementation

```cpp
#include <vector>
#include <algorithm>
using namespace std;

const int MOD = 1e9 + 7;

long long modpow(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

long long inv(long long a, long long mod) {
    return modpow(a, mod - 2, mod);
}

/**
 * Berlekamp-Massey algorithm.
 * 
 * Given the first n terms of a sequence over Z/pZ, finds the shortest
 * linear recurrence that generates the sequence.
 * 
 * Returns connection polynomial C where C[0] = 1 and the recurrence is:
 *   a[i] = -C[1]*a[i-1] - C[2]*a[i-2] - ... - C[k]*a[i-k]
 * 
 * Time: O(n * k), where k is the recurrence order.
 * For finding the recurrence: O(n^2) worst case.
 */
vector<int> berlekamp_massey(vector<int> s, int mod = MOD) {
    int n = s.size();
    vector<int> C = {1}, B = {1};
    int L = 0, m = 1, b = 1;
    
    for (int i = 0; i < n; i++) {
        // Compute discrepancy
        int d = s[i];
        for (int j = 1; j <= L; j++) {
            d = (d + 1LL * C[j] * s[i - j]) % mod;
        }
        
        if (d == 0) {
            m++;
            continue;
        }
        
        // Save current C
        auto T = C;
        
        // Correction coefficient
        int c = 1LL * d * inv(b, mod) % mod;
        
        // C = C - c * x^m * B
        while ((int)C.size() < (int)B.size() + m) {
            C.push_back(0);
        }
        for (int j = 0; j < (int)B.size(); j++) {
            C[j + m] = (C[j + m] - 1LL * c * B[j] % mod + mod) % mod;
        }
        
        if (2 * L <= i) {
            L = i + 1 - L;
            B = T;
            b = d;
            m = 1;
        } else {
            m++;
        }
    }
    
    return C;
}

/**
 * Use the recurrence found by BM to compute a[n].
 * 
 * Given connection polynomial C (from BM) and initial terms a[0..k-1],
 * computes a[n] using matrix exponentiation.
 * 
 * Time: O(k^2 * log n)
 */
long long compute_nth_term(vector<int>& C, vector<int>& init, 
                            long long n, int mod = MOD) {
    int k = (int)C.size() - 1;  // recurrence order
    
    if (n < (int)init.size()) return init[n];
    
    // Build companion matrix
    // M = [[-C[1], -C[2], ..., -C[k]],
    //      [1,     0,     ..., 0    ],
    //      [0,     1,     ..., 0    ],
    //      ...
    //      [0,     0,     ..., 1, 0 ]]
    
    auto mat_mult = [&](vector<vector<long long>>& A, 
                         vector<vector<long long>>& B) {
        int sz = A.size();
        vector<vector<long long>> R(sz, vector<long long>(sz, 0));
        for (int i = 0; i < sz; i++)
            for (int j = 0; j < sz; j++)
                for (int l = 0; l < sz; l++)
                    R[i][j] = (R[i][j] + A[i][l] * B[l][j]) % mod;
        return R;
    };
    
    auto mat_pow = [&](vector<vector<long long>> M, long long p) {
        int sz = M.size();
        vector<vector<long long>> R(sz, vector<long long>(sz, 0));
        for (int i = 0; i < sz; i++) R[i][i] = 1;
        while (p > 0) {
            if (p & 1) R = mat_mult(R, M);
            M = mat_mult(M, M);
            p >>= 1;
        }
        return R;
    };
    
    // Build transition matrix
    vector<vector<long long>> M(k, vector<long long>(k, 0));
    for (int j = 0; j < k; j++)
        M[0][j] = (mod - C[j + 1]) % mod;
    for (int i = 1; i < k; i++)
        M[i][i - 1] = 1;
    
    // M^n * [a[k-1], a[k-2], ..., a[0]]^T
    auto Mn = mat_pow(M, n - k + 1);
    
    long long result = 0;
    for (int j = 0; j < k; j++)
        result = (result + Mn[0][j] * init[k - 1 - j]) % mod;
    
    return result;
}

/**
 * Combined: find recurrence and compute a[n].
 */
long long find_and_compute(vector<int> s, long long n, int mod = MOD) {
    auto C = berlekamp_massey(s, mod);
    int k = (int)C.size() - 1;
    vector<int> init(s.begin(), s.begin() + k);
    return compute_nth_term(C, init, n, mod);
}
```

### 7.2 Python Implementation

```python
def berlekamp_massey(s, mod=10**9 + 7):
    """
    Berlekamp-Massey algorithm.
    
    Given sequence s over Z/modZ, finds the shortest linear recurrence.
    
    Returns connection polynomial C where C[0] = 1 and:
        a[n] = -C[1]*a[n-1] - C[2]*a[n-2] - ... - C[k]*a[n-k]
    
    Time: O(n * k) where k is the recurrence order.
    """
    n = len(s)
    C = [1]  # connection polynomial
    B = [1]  # previous C
    L = 0    # current LFSR length
    m = 1    # steps since last length change
    b = 1    # previous discrepancy
    
    for i in range(n):
        # Compute discrepancy
        d = s[i] % mod
        for j in range(1, L + 1):
            d = (d + C[j] * s[i - j]) % mod
        
        if d == 0:
            m += 1
            continue
        
        # Discrepancy found
        T = C[:]
        c = d * pow(b, mod - 2, mod) % mod
        
        # C = C - c * x^m * B
        while len(C) < len(B) + m:
            C.append(0)
        for j in range(len(B)):
            C[j + m] = (C[j + m] - c * B[j]) % mod
        
        if 2 * L <= i:
            L = i + 1 - L
            B = T
            b = d
            m = 1
        else:
            m += 1
    
    return C


def compute_nth_term(C, init, n, mod=10**9 + 7):
    """
    Compute a[n] using the recurrence from BM and initial terms.
    
    Args:
        C: connection polynomial from berlekamp_massey
        init: initial terms [a[0], a[1], ..., a[k-1]]
        n: index to compute
        mod: modulus
    
    Returns: a[n] mod mod
    Time: O(k^2 * log n)
    """
    k = len(C) - 1
    
    if n < len(init):
        return init[n] % mod
    
    # Build companion matrix
    def mat_mult(A, B):
        sz = len(A)
        R = [[0] * sz for _ in range(sz)]
        for i in range(sz):
            for j in range(sz):
                for l in range(sz):
                    R[i][j] = (R[i][j] + A[i][l] * B[l][j]) % mod
        return R
    
    def mat_pow(M, p):
        sz = len(M)
        R = [[int(i == j) for j in range(sz)] for i in range(sz)]
        while p > 0:
            if p & 1:
                R = mat_mult(R, M)
            M = mat_mult(M, M)
            p >>= 1
        return R
    
    # Companion matrix
    M = [[0] * k for _ in range(k)]
    for j in range(k):
        M[0][j] = (-C[j + 1]) % mod
    for i in range(1, k):
        M[i][i - 1] = 1
    
    Mn = mat_pow(M, n - k + 1)
    
    result = 0
    for j in range(k):
        result = (result + Mn[0][j] * init[k - 1 - j]) % mod
    
    return result


def find_and_compute(s, n, mod=10**9 + 7):
    """Find recurrence and compute a[n] in one call."""
    C = berlekamp_massey(s, mod)
    k = len(C) - 1
    init = s[:k]
    return compute_nth_term(C, init, n, mod)
```

### 7.3 Java Implementation

```java
import java.util.*;

public class BerlekampMassey {
    
    static final int MOD = 1_000_000_007;
    
    static long modpow(long base, long exp, int mod) {
        long result = 1;
        base %= mod;
        while (exp > 0) {
            if ((exp & 1) == 1) result = result * base % mod;
            base = base * base % mod;
            exp >>= 1;
        }
        return result;
    }
    
    /**
     * Berlekamp-Massey algorithm.
     * Returns connection polynomial C where C[0] = 1.
     * Recurrence: a[n] = -C[1]*a[n-1] - ... - C[k]*a[n-k]
     */
    static int[] berlekampMassey(int[] s, int mod) {
        int n = s.length;
        List<Integer> C = new ArrayList<>(List.of(1));
        List<Integer> B = new ArrayList<>(List.of(1));
        int L = 0, m = 1, b = 1;
        
        for (int i = 0; i < n; i++) {
            // Compute discrepancy
            long d = s[i];
            for (int j = 1; j <= L; j++)
                d = (d + (long) C.get(j) * s[i - j]) % mod;
            
            if (d == 0) { m++; continue; }
            
            // Save current C
            List<Integer> T = new ArrayList<>(C);
            
            // Correction coefficient
            long c = d * modpow(b, mod - 2, mod) % mod;
            
            // C = C - c * x^m * B
            while (C.size() < B.size() + m) C.add(0);
            for (int j = 0; j < B.size(); j++) {
                long val = (C.get(j + m) - c * B.get(j) % mod + mod) % mod;
                C.set(j + m, (int) val);
            }
            
            if (2 * L <= i) {
                L = i + 1 - L;
                B = T;
                b = (int) d;
                m = 1;
            } else {
                m++;
            }
        }
        
        return C.stream().mapToInt(Integer::intValue).toArray();
    }
    
    /**
     * Compute a[n] using recurrence from BM and initial terms.
     * Time: O(k^2 * log n)
     */
    static long computeNthTerm(int[] C, int[] init, long n, int mod) {
        int k = C.length - 1;
        if (n < init.length) return init[(int) n];
        
        // Matrix operations
        long[][] matMult(long[][] A, long[][] B) {
            int sz = A.length;
            long[][] R = new long[sz][sz];
            for (int i = 0; i < sz; i++)
                for (int j = 0; j < sz; j++)
                    for (int l = 0; l < sz; l++)
                        R[i][j] = (R[i][j] + A[i][l] * B[l][j]) % mod;
            return R;
        }
        
        long[][] matPow(long[][] M, long p) {
            int sz = M.length;
            long[][] R = new long[sz][sz];
            for (int i = 0; i < sz; i++) R[i][i] = 1;
            while (p > 0) {
                if ((p & 1) == 1) R = matMult(R, M);
                M = matMult(M, M);
                p >>= 1;
            }
            return R;
        }
        
        // Companion matrix
        long[][] M = new long[k][k];
        for (int j = 0; j < k; j++)
            M[0][j] = ((mod - C[j + 1]) % mod);
        for (int i = 1; i < k; i++)
            M[i][i - 1] = 1;
        
        long[][] Mn = matPow(M, n - k + 1);
        
        long result = 0;
        for (int j = 0; j < k; j++)
            result = (result + Mn[0][j] * init[k - 1 - j]) % mod;
        
        return result;
    }
}
```

---

## 8. Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| Finding recurrence | O(n · k) | O(n) |
| Computing a[n] via matrix exp | O(k² · log n) | O(k²) |
| **Combined** | **O(n · k + k² · log n)** | **O(k²)** |

Where n = number of input terms, k = recurrence order.

### When is BM Useful?

| Scenario | Traditional | With BM |
|----------|-------------|---------|
| Fibonacci F(10¹⁸) | O(10¹⁸) impossible | O(log 10¹⁸) ≈ 60 |
| Custom recurrence, k=10, n=10¹⁵ | O(10¹⁵) impossible | O(100 · log 10¹⁵) ≈ 5000 |
| Sequence with k=100, n=10⁹ | O(10⁹) TLE | O(10000 · 30) ≈ 300K |

---

## 9. Applications in Competitive Programming

### 9.1 Counting Problems with State DP

Many counting problems have DP solutions where the state at step n depends on a fixed number of previous states. If you can compute the first 2k values, BM finds the recurrence.

**Example**: Count the number of ways to tile a 2×n board with dominoes.
- Compute first few values: 1, 1, 2, 3, 5, 8, ...
- BM discovers: aₙ = aₙ₋₁ + aₙ₋₂ (Fibonacci!)
- Now compute for any n in O(log n).

### 9.2 Linear Recurrences with Large Modulus

BM works over any field, including GF(2) (for XOR-based recurrences) and large prime fields.

### 9.3 Finding Patterns in Sequences

Given an online judge problem where you need to compute f(n) for large n:
1. Compute f(0), f(1), ..., f(200) using the naive/DP approach.
2. Run BM to find the recurrence.
3. Use matrix exponentiation for the target n.

### 9.4 XOR Convolutions

In GF(2), BM finds the shortest LFSR for binary sequences, useful in problems involving XOR operations.

---

## 10. Complete Example: Solving a Problem

**Problem**: Define f(n) = number of binary strings of length n that don't contain "11" as a substring. Compute f(10^18) mod 10^9+7.

**Step 1**: Compute first values manually.
- f(0) = 1 (empty string)
- f(1) = 2 ("0", "1")
- f(2) = 3 ("00", "01", "10")
- f(3) = 5 ("000", "001", "010", "100", "101")
- f(4) = 8
- f(5) = 13

**Step 2**: Run BM on [1, 2, 3, 5, 8, 13].
BM discovers: C = [1, -1, -1], so f(n) = f(n-1) + f(n-2).

**Step 3**: Compute f(10^18) using matrix exponentiation with the companion matrix.

```cpp
// After BM gives C = [1, -1, -1]:
// f(n) = f(n-1) + f(n-2)
// Companion matrix: [[1,1],[1,0]]
// [f(n)]   = [[1,1]^(n-1) * [f(1)]
//  [f(n-1]]   [1,0]]         [f(0)]
```

This runs in O(log n) time!

---

## 11. Exercises

### Easy

1. **Verify**: Run BM on the sequence [1, 3, 7, 15, 31, 63]. What recurrence does it find?

2. **Powers**: Given the sequence [1, 2, 4, 8, 16, 32], what does BM return?

3. **Constant**: What does BM return for the sequence [5, 5, 5, 5, 5]?

### Medium

4. **Tribonacci**: Given [0, 0, 1, 1, 2, 4, 7, 13, 24, 44], verify BM finds aₙ = aₙ₋₁ + aₙ₋₂ + aₙ₋₃.

5. **Codeforces Problem**: Given a sequence where a[n] = 3a[n-1] - a[n-2] + 2a[n-3], use BM to discover the recurrence from the first 10 terms, then compute a[10^18].

6. **GF(2) BM**: Implement BM for binary sequences (field = GF(2)). What does it return for [1, 0, 1, 1, 0, 1, 1, 0]?

### Hard

7. **Sparse Recurrence**: If the true recurrence has order k but with many zero coefficients (e.g., aₙ = aₙ₋₁₀₀), how many terms does BM need?

8. **Noise Sensitivity**: If one term in the sequence is wrong, how does BM behave? Modify BM to handle noisy data (list decoding).

9. **Multi-dimensional BM**: Extend BM to 2D sequences a[i][j] satisfying a 2D linear recurrence.

---

## 12. Interview Questions

1. **Q**: What is the minimum number of terms BM needs to find a recurrence of order k?
   **A**: 2k terms. This is both necessary and sufficient.

2. **Q**: Can BM work with non-prime moduli?
   **A**: BM requires a field (for computing inverses). For composite moduli, you need to work modulo prime factors and combine with CRT.

3. **Q**: How does BM relate to the extended Euclidean algorithm?
   **A**: BM can be viewed as computing the continued fraction expansion of a rational function, similar to how extended GCD works for integers.

4. **Q**: What happens if the sequence doesn't satisfy any linear recurrence?
   **A**: BM will return a polynomial of degree n/2, which fits the data but has no predictive power.

5. **Q**: Can BM be used for polynomial interpolation?
   **A**: Yes! Given n points, BM on the sequence of values can find the generating function, which encodes the polynomial.

---

## 13. Common Mistakes

1. **Not enough terms**: You need at least 2k terms for BM to find an order-k recurrence. Compute generously.

2. **Modular arithmetic**: Always use modular arithmetic throughout. The discrepancy computation and update must be mod p.

3. **Interpreting C**: Remember C[0] = 1, and the recurrence is a[n] = -C[1]·a[n-1] - C[2]·a[n-2] - ... (note the negation).

4. **Sequence starting point**: BM works on a[0], a[1], .... Make sure your initial terms are correctly indexed.

5. **Using BM when the recurrence is known**: If you already know the recurrence, skip BM and go directly to matrix exponentiation.

---

## 14. Cross-References

- **Chapter 115: Matrix DP** — Matrix exponentiation for linear recurrences
- **Chapter 60: Number Theory** — Modular arithmetic and field operations
- **Chapter 73: Linear Algebra for Programming** — Companion matrices and eigenvalues
- **Chapter 163: Advanced Mathematics for Algorithms** — Generating functions
- **Chapter 86: DP Optimization Techniques** — Optimizing DP with recurrences

---

## 15. Further Reading

- Berlekamp, E. R. (1968). *Algebraic Coding Theory*. McGraw-Hill.
- Massey, J. L. (1969). "Shift-register synthesis and BCH decoding." *IEEE Transactions on Information Theory*.
- cp-algorithms: [Berlekamp-Massey Algorithm](https://cp-algorithms.com/algebra/linear-recurrances.html)
- Erickson, J. "Algorithms" — Chapter on Algebraic Algorithms
