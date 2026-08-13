# Appendix G: Mathematics Handbook

Quick reference for the mathematical formulas and properties you need for DSA interviews.

---

## 1. Logarithm Properties

| Property | Formula | Example |
|----------|---------|---------|
| Product | log(ab) = log(a) + log(b) | log(6) = log(2) + log(3) |
| Quotient | log(a/b) = log(a) - log(b) | log(2) = log(6) - log(3) |
| Power | log(aⁿ) = n·log(a) | log(8) = 3·log(2) |
| Change of base | logₐ(b) = log(b)/log(a) | log₂(8) = log(8)/log(2) |
| Base relationship | logₐ(b) = 1/logᵦ(a) | log₂(8) = 1/log₈(2) |
| Identity | logₐ(a) = 1 | log₂(2) = 1 |
| Zero | logₐ(1) = 0 | log₂(1) = 0 |
| Inverse | a^(logₐ(b)) = b | 2^(log₂(8)) = 8 |

### Common Values

| Expression | Value |
|------------|-------|
| log₂(1) | 0 |
| log₂(2) | 1 |
| log₂(4) | 2 |
| log₂(8) | 3 |
| log₂(16) | 4 |
| log₂(32) | 5 |
| log₂(64) | 6 |
| log₂(128) | 7 |
| log₂(256) | 8 |
| log₂(512) | 9 |
| log₂(1024) | 10 |
| log₂(10⁶) | ~20 |
| log₂(10⁹) | ~30 |
| log₂(n) | ~30 for n = 10⁹ |

### Useful Approximations

- log₂(n) ≈ 30 for n ≈ 10⁹
- log₂(n) ≈ 20 for n ≈ 10⁶
- log₂(n!) ≈ n·log₂(n) (Stirling's approximation)
- log₂(Fibonacci(n)) ≈ n·log₂(φ) ≈ 0.694n

---

## 2. Modular Arithmetic

### Basic Properties

Let `a mod m` denote the remainder when `a` is divided by `m`.

```
(a + b) mod m = ((a mod m) + (b mod m)) mod m
(a - b) mod m = ((a mod m) - (b mod m) + m) mod m
(a × b) mod m = ((a mod m) × (b mod m)) mod m
(a / b) mod m = (a × b⁻¹) mod m  (where b⁻¹ is modular inverse)
```

### Modular Inverse

The modular inverse of `a` modulo `m` exists if and only if `gcd(a, m) = 1`.

**Using Fermat's Little Theorem** (when m is prime):
```
a⁻¹ ≡ a^(m-2) mod m
```

**Using Extended Euclidean Algorithm:**
```
ax + my = 1  →  x is the modular inverse of a mod m
```

```cpp
// Modular exponentiation
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

// Modular inverse (when mod is prime)
long long mod_inverse(long long a, long long mod) {
    return power(a, mod - 2, mod);
}

// Modular inverse (general, using Extended Euclidean)
long long mod_inverse_general(long long a, long long m) {
    long long m0 = m, y = 0, x = 1;
    if (m == 1) return 0;
    while (a > 1) {
        long long q = a / m;
        long long t = m;
        m = a % m;
        a = t;
        t = y;
        y = x - q * y;
        x = t;
    }
    if (x < 0) x += m0;
    return x;
}
```

### Common Modular Constants

```
MOD = 10^9 + 7  (prime, most common in competitive programming)
MOD = 998244353  (prime, used in NTT)
MOD = 10^9 + 9  (prime)
```

### Modular Arithmetic Pitfalls

```cpp
// WRONG: subtraction can go negative
int diff = (a - b) % MOD;
// FIX:
int diff = ((a - b) % MOD + MOD) % MOD;

// WRONG: multiplication can overflow
int prod = (a * b) % MOD;
// FIX:
long long prod = (1LL * a * b) % MOD;

// WRONG: division doesn't work
int div = (a / b) % MOD;
// FIX: use modular inverse
int div = (1LL * a * mod_inverse(b, MOD)) % MOD;
```

---

## 3. GCD and LCM

### Euclidean Algorithm

```cpp
// Recursive
long long gcd(long long a, long long b) {
    return b == 0 ? a : gcd(b, a % b);
}

// Iterative
long long gcd(long long a, long long b) {
    while (b) { a %= b; swap(a, b); }
    return a;
}

// C++17
#include <numeric>
long long g = gcd(a, b);  // C++17
long long l = lcm(a, b);  // C++17
```

### Properties

```
gcd(a, 0) = a
gcd(a, b) = gcd(b, a mod b)
gcd(a, b) = gcd(a - b, b)  (if a > b)
lcm(a, b) = a * b / gcd(a, b)
lcm(a, b) = a / gcd(a, b) * b  (avoids overflow)
gcd(a, lcm(b, c)) = lcm(gcd(a, b), gcd(a, c))
lcm(a, gcd(b, c)) = gcd(lcm(a, b), lcm(a, c))
```

### Extended Euclidean Algorithm

Finds x, y such that ax + by = gcd(a, b).

```cpp
long long ext_gcd(long long a, long long b, long long& x, long long& y) {
    if (b == 0) { x = 1; y = 0; return a; }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}
```

---

## 4. Combinatorics

### Factorials and Binomial Coefficients

```cpp
const int MAXN = 1000001;
const int MOD = 1e9 + 7;

long long fact[MAXN], inv_fact[MAXN];

void precompute() {
    fact[0] = 1;
    for (int i = 1; i < MAXN; i++)
        fact[i] = fact[i-1] * i % MOD;
    inv_fact[MAXN-1] = power(fact[MAXN-1], MOD-2, MOD);
    for (int i = MAXN-2; i >= 0; i--)
        inv_fact[i] = inv_fact[i+1] * (i+1) % MOD;
}

long long C(int n, int r) {
    if (r < 0 || r > n) return 0;
    return fact[n] % MOD * inv_fact[r] % MOD * inv_fact[n-r] % MOD;
}

long long P(int n, int r) {
    if (r < 0 || r > n) return 0;
    return fact[n] % MOD * inv_fact[n-r] % MOD;
}
```

### Formulas

| Formula | Expression |
|---------|------------|
| C(n, r) | n! / (r! × (n-r)!) |
| P(n, r) | n! / (n-r)! |
| C(n, r) | C(n, n-r) |
| C(n, r) | C(n-1, r-1) + C(n-1, r) (Pascal's identity) |
| C(n, 0) + C(n, 1) + ... + C(n, n) | 2ⁿ |
| C(n, 0) - C(n, 1) + C(n, 2) - ... | 0 |
| C(n, 0)² + C(n, 1)² + ... + C(n, n)² | C(2n, n) |

### Stars and Bars

The number of ways to distribute `n` identical items into `k` distinct bins:

```
With empty bins allowed: C(n + k - 1, k - 1)
Without empty bins: C(n - 1, k - 1)
```

### Catalan Numbers

```
C₀ = 1
Cₙ = C(2n, n) / (n + 1) = Σ(Cᵢ × Cₙ₋ᵢ₋₁) for i = 0 to n-1

C₀ = 1, C₁ = 1, C₂ = 2, C₃ = 5, C₄ = 14, C₅ = 42

Applications:
- Number of valid parentheses expressions of length 2n
- Number of full binary trees with n+1 leaves
- Number of monotonic paths in an n×n grid
- Number of triangulations of a convex polygon with n+2 sides
```

### Inclusion-Exclusion Principle

```
|A ∪ B| = |A| + |B| - |A ∩ B|
|A ∪ B ∪ C| = |A| + |B| + |C| - |A∩B| - |A∩C| - |B∩C| + |A∩B∩C|
```

---

## 5. Probability Rules

### Basic Rules

```
P(A ∪ B) = P(A) + P(B) - P(A ∩ B)
P(A ∩ B) = P(A) × P(B|A) = P(B) × P(A|B)
P(A|B) = P(A ∩ B) / P(B)  (Bayes' theorem)
P(A') = 1 - P(A)
```

### Independence

```
A and B are independent iff P(A ∩ B) = P(A) × P(B)
```

### Expected Value

```
E[X] = Σ xᵢ × P(X = xᵢ)
E[X + Y] = E[X] + E[Y]  (linearity)
E[cX] = c × E[X]
E[XY] = E[X] × E[Y]  (if X, Y independent)
```

### Variance

```
Var(X) = E[X²] - (E[X])²
Var(X + Y) = Var(X) + Var(Y)  (if independent)
Var(cX) = c² × Var(X)
```

---

## 6. Common Summations

### Arithmetic Series

```
1 + 2 + 3 + ... + n = n(n+1)/2
a + (a+d) + (a+2d) + ... + (a+(n-1)d) = n(2a + (n-1)d)/2
```

### Geometric Series

```
1 + r + r² + ... + rⁿ = (rⁿ⁺¹ - 1)/(r - 1)  (r ≠ 1)
1 + 2 + 4 + ... + 2ⁿ = 2ⁿ⁺¹ - 1
1 + 1/2 + 1/4 + ... = 2  (infinite series, |r| < 1)
```

### Power Sums

```
Σ i     = n(n+1)/2
Σ i²    = n(n+1)(2n+1)/6
Σ i³    = (n(n+1)/2)²
Σ i⁴    = n(n+1)(2n+1)(3n²+3n-1)/30
```

### Other Useful Sums

```
Σ 1/i (harmonic) ≈ ln(n) + γ  (γ ≈ 0.5772)
Σ i × rⁱ = (r - (n+1)rⁿ⁺¹ + nrⁿ⁺²)/(1-r)²
Σ C(n,i) = 2ⁿ
Σ C(n,2i) = Σ C(n,2i+1) = 2ⁿ⁻¹
Σ i × C(n,i) = n × 2ⁿ⁻¹
```

### Sigma Notation Shortcuts

```
Σ (i=1 to n) of constant c = cn
Σ (i=1 to n) of i = n(n+1)/2
Σ (i=0 to n) of 2ⁱ = 2ⁿ⁺¹ - 1
Σ (i=1 to n) of 1/i ≈ ln(n)
```

---

## 7. Master Theorem

For recurrences of the form: T(n) = aT(n/b) + f(n)

where a ≥ 1, b > 1, and f(n) is asymptotically positive.

### Case 1: f(n) = O(n^(logᵦa - ε)) for some ε > 0

```
T(n) = Θ(n^(logᵦa))
```

The recursion tree is dominated by the leaves.

### Case 2: f(n) = Θ(n^(logᵦa) × logᵏn) for k ≥ 0

```
T(n) = Θ(n^(logᵦa) × log^(k+1)n)
```

All levels contribute equally. Most common: k=0, so T(n) = Θ(n^(logᵦa) × log n).

### Case 3: f(n) = Ω(n^(logᵦa + ε)) for some ε > 0, and af(n/b) ≤ cf(n) for some c < 1

```
T(n) = Θ(f(n))
```

The recursion tree is dominated by the root.

### Common Recurrences

| Recurrence | Solution | Algorithm |
|------------|----------|-----------|
| T(n) = 2T(n/2) + O(n) | O(n log n) | Merge sort |
| T(n) = T(n/2) + O(1) | O(log n) | Binary search |
| T(n) = 2T(n/2) + O(1) | O(n) | Tree traversal |
| T(n) = T(n/2) + O(n) | O(n) | Median of medians |
| T(n) = 2T(n/2) + O(n log n) | O(n log²n) | |
| T(n) = T(n-1) + O(n) | O(n²) | Selection sort |
| T(n) = 2T(n-1) + O(1) | O(2ⁿ) | Tower of Hanoi |
| T(n) = T(n-1) + T(n-2) + O(1) | O(φⁿ) | Fibonacci |
| T(n) = 4T(n/2) + O(n) | O(n²) | |
| T(n) = 3T(n/4) + O(n log n) | O(n log n) | |

---

## 8. Number Theory

### Prime Numbers

- A prime p > 1 has exactly two divisors: 1 and p
- Fundamental theorem of arithmetic: every integer > 1 has a unique prime factorization
- There are approximately n/ln(n) primes up to n

### Sieve of Eratosthenes

```cpp
vector<int> sieve(int n) {
    vector<bool> is_prime(n + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i * i <= n; i++) {
        if (is_prime[i]) {
            for (int j = i * i; j <= n; j += i) {
                is_prime[j] = false;
            }
        }
    }
    vector<int> primes;
    for (int i = 2; i <= n; i++) {
        if (is_prime[i]) primes.push_back(i);
    }
    return primes;
}
```

### Euler's Totient Function

φ(n) = count of integers in [1, n] coprime to n.

```
φ(p) = p - 1  (p is prime)
φ(pᵏ) = pᵏ - pᵏ⁻¹
φ(ab) = φ(a) × φ(b)  (if gcd(a,b) = 1)
φ(n) = n × Π(1 - 1/p)  for all prime factors p of n
```

```cpp
int phi(int n) {
    int result = n;
    for (int p = 2; p * p <= n; p++) {
        if (n % p == 0) {
            while (n % p == 0) n /= p;
            result -= result / p;
        }
    }
    if (n > 1) result -= result / n;
    return result;
}
```

### Euler's Theorem

```
a^φ(n) ≡ 1 (mod n)  if gcd(a, n) = 1
```

Special case (Fermat's Little Theorem):
```
a^(p-1) ≡ 1 (mod p)  if p is prime and gcd(a, p) = 1
```

### Chinese Remainder Theorem

Given pairwise coprime moduli m₁, m₂, ..., mₖ, the system:
```
x ≡ a₁ (mod m₁)
x ≡ a₂ (mod m₂)
...
x ≡ aₖ (mod mₖ)
```
has a unique solution modulo M = m₁ × m₂ × ... × mₖ.

---

## 9. Matrix Exponentiation

Used to solve linear recurrences in O(k³ log n) time.

```cpp
typedef vector<vector<long long>> Matrix;

Matrix multiply(Matrix& A, Matrix& B, long long mod) {
    int n = A.size();
    Matrix C(n, vector<long long>(n, 0));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % mod;
    return C;
}

Matrix power(Matrix base, long long exp, long long mod) {
    int n = base.size();
    Matrix result(n, vector<long long>(n, 0));
    for (int i = 0; i < n; i++) result[i][i] = 1; // identity
    while (exp > 0) {
        if (exp & 1) result = multiply(result, base, mod);
        base = multiply(base, base, mod);
        exp >>= 1;
    }
    return result;
}

// Example: Fibonacci
// [F(n+1), F(n)] = [[1,1],[1,0]]^n × [F(1), F(0)]
long long fibonacci(long long n, long long mod) {
    if (n == 0) return 0;
    Matrix base = {{1, 1}, {1, 0}};
    Matrix result = power(base, n - 1, mod);
    return result[0][0]; // F(n)
}
```

---

## 10. Geometry Formulas

### Distance

```
Euclidean: d = √((x₂-x₁)² + (y₂-y₁)²)
Manhattan: d = |x₂-x₁| + |y₂-y₁|
Chebyshev: d = max(|x₂-x₁|, |y₂-y₁|)
Minkowski: d = (|x₂-x₁|^p + |y₂-y₁|^p)^(1/p)
```

### Area

```
Triangle: A = ½|base × height|
Triangle (Heron's): A = √(s(s-a)(s-b)(s-c)), s = (a+b+c)/2
Triangle (cross product): A = ½|x₁(y₂-y₃) + x₂(y₃-y₁) + x₃(y₁-y₂)|
Circle: A = πr²
Polygon (Shoelace): A = ½|Σ(xᵢyᵢ₊₁ - xᵢ₊₁yᵢ)|
```

### Cross Product

```
2D: cross(A, B) = A.x × B.y - A.y × B.x
If cross > 0: B is counter-clockwise from A
If cross < 0: B is clockwise from A
If cross = 0: A and B are collinear
```

### Point in Polygon

Use ray casting: count intersections of a horizontal ray from the point with polygon edges. Odd = inside, even = outside.

---

## 11. Bit Manipulation

### Common Operations

```cpp
// Check if bit i is set
bool is_set(int n, int i) { return (n >> i) & 1; }

// Set bit i
int set_bit(int n, int i) { return n | (1 << i); }

// Clear bit i
int clear_bit(int n, int i) { return n & ~(1 << i); }

// Toggle bit i
int toggle_bit(int n, int i) { return n ^ (1 << i); }

// Clear lowest set bit
int clear_lowest(int n) { return n & (n - 1); }

// Get lowest set bit
int lowest_bit(int n) { return n & (-n); }

// Count set bits
int popcount(int n) { return __builtin_popcount(n); }

// Number of trailing zeros
int ctz(int n) { return __builtin_ctz(n); }

// Number of leading zeros
int clz(int n) { return __builtin_clz(n); }

// Check if power of 2
bool is_power_of_2(int n) { return n > 0 && (n & (n-1)) == 0; }
```

### Subset Enumeration

```cpp
// Enumerate all subsets of a set
int mask = (1 << n) - 1;  // full set
for (int subset = mask; subset; subset = (subset - 1) & mask) {
    // process subset
}
```

### Bitmask DP State

```cpp
// Visit all nodes exactly once (TSP-like)
// dp[mask][i] = min cost to visit nodes in mask, ending at i
// Transition: dp[mask | (1<<j)][j] = min(dp[mask][i] + dist[i][j])
```

---

## 12. Fast Exponentiation

```cpp
// Binary exponentiation
long long power(long long base, long long exp, long long mod = 1e18) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}
```

**Complexity:** O(log exp) time, O(1) space.

---

## 13. Derangements

A permutation where no element appears in its original position.

```
D(n) = (n-1) × (D(n-1) + D(n-2))
D(0) = 1, D(1) = 0, D(2) = 1, D(3) = 2, D(4) = 9
```

---

## 14. Stirling Numbers

### Second Kind: S(n, k)

Number of ways to partition n elements into k non-empty subsets.

```
S(n, k) = k × S(n-1, k) + S(n-1, k-1)
S(n, 0) = 0, S(0, 0) = 1
```

### First Kind: s(n, k)

Number of permutations of n elements with exactly k cycles.

---

## 15. Common Mathematical Identities

```
a² - b² = (a+b)(a-b)
(a+b)² = a² + 2ab + b²
(a-b)² = a² - 2ab + b²
a³ + b³ = (a+b)(a² - ab + b²)
a³ - b³ = (a-b)(a² + ab + b²)
(a+b)³ = a³ + 3a²b + 3ab² + b³
De Moivre's: (cos θ + i sin θ)ⁿ = cos(nθ) + i sin(nθ)
```

---

*Keep this handbook handy during practice. You'll naturally memorize the formulas you use most.*
