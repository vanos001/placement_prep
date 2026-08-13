# Chapter 138: Formula Handbook

## Quick Reference for Interview Formulas

---

## 138.1 Purpose and How to Use This Chapter

This chapter is a **condensed reference** of mathematical formulas frequently encountered in DSA interviews and competitions. Each section includes the formula, when to use it, and a quick example.

**How to use:**
1. **Before interview:** Skim for pattern recognition
2. **During contest:** Quick lookup for formulas you've forgotten
3. **While studying:** Verify your derivations

---

## 138.2 Combinatorics

### Permutations

**Formula:** P(n, r) = n! / (n - r)!

**When to use:** Counting arrangements where order matters.

**Example:** How many ways to arrange 3 books from 5? P(5,3) = 5!/(5-3)! = 60

```cpp
long long perm(int n, int r) {
    long long result = 1;
    for (int i = n; i > n - r; i--) result *= i;
    return result;
}
```

```python
def perm(n, r):
    result = 1
    for i in range(n, n - r, -1):
        result *= i
    return result
```

### Combinations

**Formula:** C(n, r) = n! / (r! × (n - r)!)

**When to use:** Counting selections where order doesn't matter.

**Example:** Choose 3 items from 10: C(10,3) = 120

```cpp
// Precompute Pascal's triangle
const int MAXN = 1001;
const long long MOD = 1e9 + 7;
long long C[MAXN][MAXN];

void precompute() {
    for (int i = 0; i < MAXN; i++) {
        C[i][0] = C[i][i] = 1;
        for (int j = 1; j < i; j++)
            C[i][j] = (C[i-1][j-1] + C[i-1][j]) % MOD;
    }
}
```

```python
from math import comb  # Python 3.8+

# Or precompute Pascal's triangle
def precompute_comb(n, mod=10**9+7):
    C = [[0] * (n+1) for _ in range(n+1)]
    for i in range(n+1):
        C[i][0] = C[i][i] = 1
        for j in range(1, i):
            C[i][j] = (C[i-1][j-1] + C[i-1][j]) % mod
    return C
```

```java
// Precompute Pascal's triangle
long[][] C = new long[MAXN][MAXN];
void precompute() {
    for (int i = 0; i < MAXN; i++) {
        C[i][0] = C[i][i] = 1;
        for (int j = 1; j < i; j++)
            C[i][j] = (C[i-1][j-1] + C[i-1][j]) % MOD;
    }
}
```

### Stars and Bars

**Formula:** Number of ways to distribute n identical items into k bins = C(n + k - 1, k - 1)

**When to use:** Counting solutions to x₁ + x₂ + ... + xₖ = n where xᵢ ≥ 0.

**Example:** Distribute 5 identical balls into 3 boxes: C(5+3-1, 3-1) = C(7,2) = 21

**Variant (positive):** If each xᵢ ≥ 1, then C(n-1, k-1).

### Catalan Numbers

**Formula:** Cₙ = C(2n, n) / (n + 1)

**Sequence:** 1, 1, 2, 5, 14, 42, 132, 429, ...

**When to use:**
- Valid parenthesizations of n pairs
- Number of full binary trees with n+1 leaves
- Non-crossing partitions
- Monotonic lattice paths below diagonal

**Example:** Number of valid expressions with 3 pairs of parentheses: C₃ = 5

```cpp
long long catalan(int n) {
    long long result = 1;
    for (int i = 0; i < n; i++) {
        result = result * (2 * n - i) / (i + 1);
    }
    return result / (n + 1);
}
```

```python
from math import comb

def catalan(n):
    return comb(2 * n, n) // (n + 1)
```

### Derangements

**Formula:** D(n) = (n - 1) × (D(n - 1) + D(n - 2))

**Base cases:** D(0) = 1, D(1) = 0

**Sequence:** 1, 0, 1, 2, 9, 44, 265, ...

**When to use:** Counting permutations where no element appears in its original position.

**Example:** D(4) = 9 (ways to arrange 4 letters so no one gets their own)

### Inclusion-Exclusion Principle

**Formula:**
```
|A₁ ∪ A₂ ∪ ... ∪ Aₙ| = Σ|Aᵢ| - Σ|Aᵢ ∩ Aⱼ| + Σ|Aᵢ ∩ Aⱼ ∩ Aₖ| - ... + (-1)^(n+1)|A₁ ∩ ... ∩ Aₙ|
```

**When to use:** Counting with "at least one" or "none" constraints.

**Example:** How many numbers from 1-100 are divisible by 2, 3, or 5?
```
|A₂ ∪ A₃ ∪ A₅| = 50 + 33 + 20 - 16 - 10 - 6 + 3 = 74
```

---

## 138.3 Number Theory

### Euler's Totient Function

**Formula:** φ(n) = n × ∏(1 - 1/p) for all prime factors p of n

**Properties:**
- φ(p) = p - 1 for prime p
- φ(pᵏ) = pᵏ - pᵏ⁻¹
- φ(mn) = φ(m) × φ(n) if gcd(m,n) = 1

**When to use:** Counting numbers ≤ n that are coprime to n. Also used in Euler's theorem.

```cpp
int phi(int n) {
    int result = n;
    for (int i = 2; i * i <= n; i++) {
        if (n % i == 0) {
            while (n % i == 0) n /= i;
            result -= result / i;
        }
    }
    if (n > 1) result -= result / n;
    return result;
}
```

```python
def phi(n):
    result = n
    p = 2
    while p * p <= n:
        if n % p == 0:
            while n % p == 0:
                n //= p
            result -= result // p
        p += 1
    if n > 1:
        result -= result // n
    return result
```

### Modular Inverse

**Formula:** a⁻¹ ≡ a^(p-2) (mod p) when p is prime (Fermat's Little Theorem)

**When to use:** Division under modulo. Computing C(n,k) mod p.

```cpp
long long power(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

long long modInverse(long long a, long long p) {
    return power(a, p - 2, p);
}
```

```python
def power(base, exp, mod):
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result

def mod_inverse(a, p):
    return power(a, p - 2, p)
```

### GCD and LCM

**GCD Formula:** gcd(a, b) = gcd(b, a % b)

**LCM Formula:** lcm(a, b) = a × b / gcd(a, b)

```cpp
// C++: use __gcd(a, b) or std::gcd (C++17)
long long gcd(long long a, long long b) {
    while (b) { a %= b; swap(a, b); }
    return a;
}

long long lcm(long long a, long long b) {
    return a / gcd(a, b) * b; // divide first to avoid overflow
}
```

```python
from math import gcd

def lcm(a, b):
    return a // gcd(a, b) * b
```

### Chinese Remainder Theorem (CRT)

**Formula:** Given x ≡ aᵢ (mod mᵢ) for coprime mᵢ, x is unique mod M = ∏mᵢ

**When to use:** Solving systems of congruences.

**Example:** x ≡ 2 (mod 3), x ≡ 3 (mod 5), x ≡ 2 (mod 7) → x = 23 (mod 105)

### Fermat's Little Theorem

**Formula:** a^(p-1) ≡ 1 (mod p) for prime p and gcd(a, p) = 1

**Corollary:** a^p ≡ a (mod p)

**When to use:** Computing large powers mod prime, finding modular inverse.

### Extended Euclidean Algorithm

**Finds:** x, y such that ax + by = gcd(a, b)

**When to use:** Finding modular inverse when modulus is not prime.

```cpp
long long extgcd(long long a, long long b, long long& x, long long& y) {
    if (b == 0) { x = 1; y = 0; return a; }
    long long g = extgcd(b, a % b, y, x);
    y -= a / b * x;
    return g;
}
```

```python
def extgcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x, y = extgcd(b, a % b)
    return g, y, x - (a // b) * y
```

---

## 138.4 Sequences and Series

### Arithmetic Sequence

**Sum:** S = n(a₁ + aₙ) / 2 = n × (2a₁ + (n-1)d) / 2

**n-th term:** aₙ = a₁ + (n-1)d

**When to use:** Sum of evenly spaced numbers.

### Geometric Sequence

**Sum:** S = a(rⁿ - 1) / (r - 1) for r ≠ 1

**Infinite sum:** S = a / (1 - r) for |r| < 1

**n-th term:** aₙ = a₁ × r^(n-1)

### Fibonacci Numbers

**Recurrence:** F(n) = F(n-1) + F(n-2), F(0) = 0, F(1) = 1

**Closed form (Binet's):** F(n) ≈ φⁿ / √5 where φ = (1 + √5) / 2

**Matrix form:**
```
[F(n+1), F(n)] = [1, 1] ^ n
                  [1, 0]
```

```cpp
// Matrix exponentiation for Fibonacci - O(log n)
struct Matrix {
    long long a[2][2];
    Matrix() { memset(a, 0, sizeof(a)); }
    Matrix operator*(const Matrix& other) const {
        Matrix result;
        for (int i = 0; i < 2; i++)
            for (int j = 0; j < 2; j++)
                for (int k = 0; k < 2; k++)
                    result.a[i][j] = (result.a[i][j] + a[i][k] * other.a[k][j]) % MOD;
        return result;
    }
};

long long fib(long long n) {
    Matrix base = {{{1, 1}, {1, 0}}};
    Matrix result = {{{1, 0}, {0, 1}}};
    while (n > 0) {
        if (n & 1) result = result * base;
        base = base * base;
        n >>= 1;
    }
    return result.a[0][1];
}
```

```python
def fib_matrix(n, mod=10**9+7):
    """Fibonacci in O(log n) using matrix exponentiation."""
    def mat_mul(A, B):
        return [
            [(A[0][0]*B[0][0] + A[0][1]*B[1][0]) % mod,
             (A[0][0]*B[0][1] + A[0][1]*B[1][1]) % mod],
            [(A[1][0]*B[0][0] + A[1][1]*B[1][0]) % mod,
             (A[1][0]*B[0][1] + A[1][1]*B[1][1]) % mod]
        ]
    
    result = [[1, 0], [0, 1]]
    base = [[1, 1], [1, 0]]
    while n > 0:
        if n & 1:
            result = mat_mul(result, base)
        base = mat_mul(base, base)
        n >>= 1
    return result[0][1]
```

### Harmonic Numbers

**Formula:** H(n) = 1 + 1/2 + 1/3 + ... + 1/n ≈ ln(n) + γ

Where γ ≈ 0.5772 (Euler-Mascheroni constant)

**When to use:** Expected value calculations, coupon collector problem.

### Triangular Numbers

**Formula:** T(n) = n(n+1)/2

**When to use:** Sum of first n natural numbers, Gauss's formula.

### Sum of Squares

**Formula:** Σk² = n(n+1)(2n+1)/6

### Sum of Cubes

**Formula:** Σk³ = [n(n+1)/2]² = T(n)²

---

## 138.5 Probability

### Bayes' Theorem

**Formula:** P(A|B) = P(B|A) × P(A) / P(B)

**When to use:** Updating probabilities with new evidence.

**Example:** Disease test with 99% accuracy, 1% prevalence. If positive, P(disease) = ?

```
P(disease|+) = P(+|disease) × P(disease) / P(+)
             = 0.99 × 0.01 / (0.99 × 0.01 + 0.01 × 0.99)
             = 0.50
```

### Linearity of Expectation

**Formula:** E[X + Y] = E[X] + E[Y] (always, even if dependent)

**When to use:** Computing expected values of sums of random variables.

**Example:** Expected sum of two dice = E[die1] + E[die2] = 3.5 + 3.5 = 7

### Birthday Paradox

**Formula:** P(at least one collision among n people) ≈ 1 - e^(-n²/(2d))

Where d = number of possible birthdays (365).

**Key insight:** With ~23 people, collision probability > 50%.

### Coupon Collector Problem

**Formula:** E[coupons to collect all n] = n × H(n) ≈ n ln(n)

**When to use:** Expected time to see all states, expected iterations until all elements covered.

### Geometric Distribution

**Formula:** E[trials until first success] = 1/p

**When to use:** Expected number of coin flips until heads.

---

## 138.6 Graph Theory

### Euler's Formula (Planar Graphs)

**Formula:** V - E + F = 2

Where V = vertices, E = edges, F = faces (including outer face).

**Corollary for planar graphs:** E ≤ 3V - 6

### Handshaking Lemma

**Formula:** Σ deg(v) = 2|E|

**When to use:** Relating degrees to edge count. Useful for proving properties.

### Trees

**Properties:**
- |E| = |V| - 1
- Connected and acyclic
- Unique path between any two vertices
- Adding any edge creates exactly one cycle

### DAG Paths

**Formula:** Number of paths from u to v = DP on topological order

```cpp
// Count paths in DAG
vector<int> topoSort(vector<vector<int>>& adj, int n) {
    vector<int> in_degree(n, 0), order;
    for (int u = 0; u < n; u++)
        for (int v : adj[u]) in_degree[v]++;
    queue<int> q;
    for (int i = 0; i < n; i++)
        if (in_degree[i] == 0) q.push(i);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : adj[u])
            if (--in_degree[v] == 0) q.push(v);
    }
    return order;
}

long long countPaths(vector<vector<int>>& adj, int n, int src, int dst) {
    auto order = topoSort(adj, n);
    vector<long long> dp(n, 0);
    dp[src] = 1;
    for (int u : order)
        for (int v : adj[u])
            dp[v] += dp[u];
    return dp[dst];
}
```

---

## 138.7 Bit Manipulation

| Operation | Expression | Use Case |
|---|---|---|
| Check bit i | `x & (1 << i)` | Test if bit set |
| Set bit i | `x \| (1 << i)` | Turn on bit |
| Clear bit i | `x & ~(1 << i)` | Turn off bit |
| Toggle bit i | `x ^ (1 << i)` | Flip bit |
| Lowest set bit | `x & (-x)` | Isolate LSB |
| Clear lowest | `x & (x - 1)` | Remove LSB |
| Count set bits | `__builtin_popcount(x)` | Population count |
| Check power of 2 | `x && !(x & (x-1))` | Single bit set |

---

## 138.8 Modular Arithmetic Rules

| Rule | Formula |
|---|---|
| Addition | (a + b) % m = ((a % m) + (b % m)) % m |
| Subtraction | (a - b) % m = ((a % m) - (b % m) + m) % m |
| Multiplication | (a × b) % m = ((a % m) × (b % m)) % m |
| Division | (a / b) % m = (a × b⁻¹) % m |
| Power | aⁿ % m via binary exponentiation |
| Inverse | b⁻¹ = b^(m-2) % m (prime m) |

**Common pitfalls:**
- Always use `long long` for intermediate products
- Apply mod after every operation, not just at the end
- `(a - b) % m` can be negative in C++; add m before modding

---

## 138.9 Common Recurrences

| Recurrence | Solution | Algorithm |
|---|---|---|
| T(n) = T(n/2) + O(1) | O(log n) | Binary search |
| T(n) = 2T(n/2) + O(n) | O(n log n) | Merge sort |
| T(n) = T(n/2) + O(n) | O(n) | Median finding |
| T(n) = 2T(n/2) + O(1) | O(n) | Tree traversal |
| T(n) = T(n-1) + T(n-2) | O(φⁿ) | Naive Fibonacci |
| T(n) = T(n-1) + O(1) | O(n) | Linear scan |

---

## 138.10 Exercises

### Exercise 1: Modular Combination
Compute C(100, 50) mod (10⁹ + 7). Implement using Fermat's little theorem for modular inverse.

### Exercise 2: Catalan Application
How many valid sequences of 5 pairs of parentheses exist? Compute C₅ using the formula and verify by enumeration.

### Exercise 3: Expected Value
A fair coin is flipped until heads appears. What's the expected number of flips? Use the geometric distribution formula.

### Exercise 4: Euler's Totient
Compute φ(360). Prime factorize 360 and apply the formula.

### Exercise 5: CRT
Solve: x ≡ 1 (mod 3), x ≡ 4 (mod 5), x ≡ 6 (mod 7). Find the smallest positive x.

---

## 138.11 Interview Questions

### Q1: How do you compute nCr mod p efficiently?
**A:** Precompute factorials and inverse factorials up to n. Then C(n,r) = fact[n] × invFact[r] × invFact[n-r] mod p. Compute inverse factorials using Fermat's little theorem: invFact[n] = fact[n]^(p-2) mod p.

### Q2: When does inclusion-exclusion apply?
**A:** When counting elements in unions of sets. The principle alternates adding and subtracting intersections. Common in counting problems with "at least one" or "none" constraints.

### Q3: What's the relationship between GCD and LCM?
**A:** gcd(a,b) × lcm(a,b) = a × b. This is useful because computing one gives you the other for free.

### Q4: How do you handle negative modular results in C++?
**A:** After subtraction, add the modulus before taking mod: `((a - b) % m + m) % m`. In Python, `%` always returns non-negative, so this isn't needed.

---

## 138.12 Cross-References

| Topic | Related Chapter |
|---|---|
| Modular Arithmetic | Chapter 80 |
| Combinatorics | Chapter 82 |
| Number Theory | Chapter 84 |
| Graph Theory | Chapter 40 |
| Matrix Exponentiation | Chapter 86 |
| Probability | Chapter 88 |
| Bit Manipulation | Chapter 10 |

---

## Summary

| Section | Key Formulas |
|---|---|
| Combinatorics | P(n,r), C(n,r), Stars & Bars, Catalan, Derangements |
| Number Theory | Euler's Totient, Modular Inverse, GCD/LCM, CRT, Fermat's |
| Sequences | Arithmetic, Geometric, Fibonacci, Harmonic |
| Probability | Bayes, Linearity, Birthday, Coupon Collector |
| Graph Theory | Euler's formula, Handshaking, Trees, DAG paths |
| Bit Manipulation | Set/clear/toggle/isolate bits |
| Modular Arithmetic | Add, sub, mul, div, power rules |

**Key Insight:** These formulas are tools, not memorization targets. Understand **when** to apply each one, and you'll recognize patterns in interview problems quickly.
