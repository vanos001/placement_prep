# Chapter 60: Number Theory

## Prerequisites

- Modular arithmetic basics
- Prime numbers and divisibility
- Recursion
- Matrix multiplication basics

## Interview Frequency: ★★★

Number theory appears in interviews at companies that deal with cryptography, security, or mathematical modeling. **Google** and **Meta** occasionally test modular arithmetic. **Amazon** tests basic GCD/LCM. Cryptography companies (**Cloudflare**, **Coinbase**, **crypto startups**) heavily test these concepts. Competitive programming interviews at **ByteDance** and **Yandex** frequently include number theory.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Fast Exponentiation | ★★★★ | All companies | Easy-Medium |
| Extended Euclid | ★★★ | Google, crypto companies | Medium |
| CRT | ★★ | Crypto, competitive programming | Medium |
| Euler's Totient | ★★ | Crypto, Google | Medium |
| Modular Inverse | ★★★★ | All companies (combinatorics) | Easy-Medium |
| Diophantine Equations | ★★ | Google, math-heavy | Medium |
| Matrix Exponentiation | ★★★ | Google, ByteDance | Medium |
| Lucas Theorem | ★★ | Competitive programming | Medium |
| Miller-Rabin | ★★ | Crypto, Google | Medium-Hard |

---

## 60.1 Fast Exponentiation (Binary Exponentiation)

Computing `a^n mod m` in O(log n) time by expressing n in binary.

### Key Idea

```
a^n = a^(2^k1 + 2^k2 + ...) = a^(2^k1) × a^(2^k2) × ...
```

We can compute `a^(2^k)` by repeated squaring.

### When to Use

- Any computation requiring `a^n mod m`
- Computing Fibonacci numbers via matrix exponentiation
- Discrete logarithm problems

### Complete Implementation

```cpp
#include <iostream>
#include <cassert>

// Iterative binary exponentiation
long long powerMod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    
    while (exp > 0) {
        if (exp & 1) {
            result = (__int128)result * base % mod;
        }
        base = (__int128)base * base % mod;
        exp >>= 1;
    }
    
    return result;
}

// Recursive version
long long powerModRecursive(long long base, long long exp, long long mod) {
    if (exp == 0) return 1;
    if (exp == 1) return base % mod;
    
    long long half = powerModRecursive(base, exp / 2, mod);
    long long result = (__int128)half * half % mod;
    
    if (exp & 1) {
        result = (__int128)result * base % mod;
    }
    
    return result;
}

int main() {
    long long mod = 1e9 + 7;
    
    // 2^10 mod 1e9+7 = 1024
    assert(powerMod(2, 10, mod) == 1024);
    
    // 3^13 mod 1000000007
    std::cout << "3^13 mod 1e9+7 = " << powerMod(3, 13, mod) << "\n";
    
    // Large exponent
    std::cout << "2^100 mod 1e9+7 = " << powerMod(2, 100, mod) << "\n";
    
    // Test with __int128 for overflow safety
    long long big = 1e18;
    std::cout << "10^18 squared mod 1e9+7 = " 
              << powerMod(big, 2, mod) << "\n";
    
    return 0;
}
```

### Overflow Safety

When `mod` can be up to ~10^18, multiplying two numbers can overflow `long long`. Use `__int128` (GCC/Clang) or implement modular multiplication:

```cpp
// Safe modular multiplication without __int128
long long mulMod(long long a, long long b, long long mod) {
    long long result = 0;
    a %= mod;
    while (b > 0) {
        if (b & 1) result = (result + a) % mod;
        a = (a + a) % mod;
        b >>= 1;
    }
    return result;
}
```

---

## 60.2 Extended Euclidean Algorithm

The **Extended Euclidean Algorithm** finds integers x, y such that:

```
ax + by = gcd(a, b)
```

This is the foundation for computing modular inverses and solving linear Diophantine equations.

### Complete Implementation

```cpp
#include <iostream>
#include <tuple>
#include <cassert>

// Returns {gcd, x, y} such that ax + by = gcd(a, b)
std::tuple<long long, long long, long long> extGcd(long long a, long long b) {
    if (b == 0) return {a, 1, 0};
    
    auto [g, x1, y1] = extGcd(b, a % b);
    long long x = y1;
    long long y = x1 - (a / b) * y1;
    
    return {g, x, y};
}

// Verify: ax + by = gcd
void verify(long long a, long long b) {
    auto [g, x, y] = extGcd(a, b);
    assert(a * x + b * y == g);
    assert(g == std::__gcd(a, b));
    std::cout << a << "*" << x << " + " << b << "*" << y << " = " << g << "\n";
}

int main() {
    verify(35, 15);  // 35*1 + 15*(-2) = 5
    verify(99, 78);  // 99*(-11) + 78*14 = 3
    verify(17, 13);  // gcd = 1, modular inverse exists
    
    return 0;
}
```

### Geometric Interpretation

The extended GCD finds a point on the line `ax + by = gcd(a, b)`. All solutions are:

```
x = x0 + k * (b/g)
y = y0 - k * (a/g)
```

for any integer k, where (x0, y0) is one particular solution.

---

## 60.3 Chinese Remainder Theorem (CRT)

**CRT** solves a system of simultaneous congruences:

```
x ≡ a₁ (mod m₁)
x ≡ a₂ (mod m₂)
...
x ≡ aₖ (mod mₖ)
```

If the moduli are pairwise coprime, there exists a unique solution modulo `M = m₁ × m₂ × ... × mₖ`.

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <tuple>
#include <numeric>
#include <cassert>

std::tuple<long long, long long, long long> extGcd(long long a, long long b) {
    if (b == 0) return {a, 1, 0};
    auto [g, x1, y1] = extGcd(b, a % b);
    return {g, y1, x1 - (a / b) * y1};
}

// Modular inverse using extended GCD
long long modInverse(long long a, long long m) {
    auto [g, x, y] = extGcd(a, m);
    if (g != 1) return -1; // No inverse
    return (x % m + m) % m;
}

// Solve x ≡ a1 (mod m1) and x ≡ a2 (mod m2)
// Returns {x, m1*m2} or {-1, -1} if no solution
std::pair<long long, long long> crtPair(long long a1, long long m1, 
                                         long long a2, long long m2) {
    auto [g, x, y] = extGcd(m1, m2);
    
    if ((a2 - a1) % g != 0) return {-1, -1}; // No solution
    
    long long lcm = m1 / g * m2;
    long long factor = (a2 - a1) / g;
    long long solution = (a1 + m1 * ((factor * x % (m2 / g) + (m2 / g)) % (m2 / g))) % lcm;
    
    return {(solution + lcm) % lcm, lcm};
}

// General CRT for multiple congruences
std::pair<long long, long long> crt(const std::vector<long long>& a, 
                                     const std::vector<long long>& m) {
    long long result = a[0], mod = m[0];
    
    for (int i = 1; i < (int)a.size(); i++) {
        auto [x, newMod] = crtPair(result, mod, a[i], m[i]);
        if (x == -1) return {-1, -1};
        result = x;
        mod = newMod;
    }
    
    return {result, mod};
}

int main() {
    // Example: x ≡ 2 (mod 3), x ≡ 3 (mod 5), x ≡ 2 (mod 7)
    // Solution: x = 23 (mod 105)
    
    std::vector<long long> a = {2, 3, 2};
    std::vector<long long> m = {3, 5, 7};
    
    auto [x, mod] = crt(a, m);
    std::cout << "x = " << x << " (mod " << mod << ")\n";
    
    // Verify
    assert(x % 3 == 2);
    assert(x % 5 == 3);
    assert(x % 7 == 2);
    
    std::cout << "Verification: " << x << " % 3 = " << x % 3 << "\n";
    std::cout << "Verification: " << x << " % 5 = " << x % 5 << "\n";
    std::cout << "Verification: " << x << " % 7 = " << x % 7 << "\n";
    
    return 0;
}
```

---

## 60.4 Euler's Totient Function

**Euler's totient function** φ(n) counts the number of integers from 1 to n that are coprime to n.

### Properties

```
φ(p) = p - 1  (for prime p)
φ(p^k) = p^k - p^(k-1) = p^(k-1) * (p - 1)
φ(m * n) = φ(m) * φ(n)  if gcd(m, n) = 1
φ(n) = n * ∏(p | n) (1 - 1/p)
```

### Euler's Theorem

If gcd(a, n) = 1, then:
```
a^φ(n) ≡ 1 (mod n)
```

This generalizes Fermat's Little Theorem (which states a^(p-1) ≡ 1 mod p for prime p).

```cpp
#include <iostream>
#include <vector>
#include <numeric>

// Compute φ(n) using factorization
long long eulerTotient(long long n) {
    long long result = n;
    for (long long p = 2; p * p <= n; p++) {
        if (n % p == 0) {
            while (n % p == 0) n /= p;
            result -= result / p;
        }
    }
    if (n > 1) result -= result / n;
    return result;
}

// Sieve for computing φ for all numbers up to n
std::vector<int> sieveTotient(int n) {
    std::vector<int> phi(n + 1);
    std::iota(phi.begin(), phi.end(), 0);
    
    for (int p = 2; p <= n; p++) {
        if (phi[p] == p) { // p is prime
            for (int i = p; i <= n; i += p) {
                phi[i] -= phi[i] / p;
            }
        }
    }
    
    return phi;
}

int main() {
    // Compute φ for specific numbers
    for (int n : {1, 2, 6, 10, 12, 100}) {
        std::cout << "φ(" << n << ") = " << eulerTotient(n) << "\n";
    }
    
    std::cout << "\nSieve-based totients up to 20:\n";
    auto phi = sieveTotient(20);
    for (int i = 1; i <= 20; i++) {
        std::cout << "φ(" << i << ") = " << phi[i] << "\n";
    }
    
    // Verify Euler's theorem: 2^φ(7) ≡ 1 (mod 7)
    // φ(7) = 6, 2^6 = 64, 64 mod 7 = 1 ✓
    long long n = 7, a = 2;
    long long phin = eulerTotient(n);
    long long result = 1;
    for (long long i = 0; i < phin; i++) result = result * a % n;
    std::cout << "\n2^φ(7) mod 7 = " << result << "\n";
    
    return 0;
}
```

---

## 60.5 Modular Inverse

The **modular inverse** of a modulo m is a number `a⁻¹` such that `a × a⁻¹ ≡ 1 (mod m)`.

### Methods

| Method | Condition | Time |
|---|---|---|
| Fermat's Little Theorem | m is prime | O(log m) |
| Extended GCD | gcd(a, m) = 1 | O(log m) |
| Euler's Theorem | gcd(a, m) = 1 | O(log m + φ(m)) |

```cpp
#include <iostream>
#include <vector>
#include <cassert>

long long powerMod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = (__int128)result * base % mod;
        base = (__int128)base * base % mod;
        exp >>= 1;
    }
    return result;
}

std::tuple<long long, long long, long long> extGcd(long long a, long long b) {
    if (b == 0) return {a, 1, 0};
    auto [g, x1, y1] = extGcd(b, a % b);
    return {g, y1, x1 - (a / b) * y1};
}

// Method 1: Fermat's Little Theorem (m must be prime)
long long modInverseFermat(long long a, long long m) {
    return powerMod(a, m - 2, m);
}

// Method 2: Extended GCD (gcd(a, m) = 1)
long long modInverseExtGcd(long long a, long long m) {
    auto [g, x, y] = extGcd(a, m);
    if (g != 1) return -1;
    return (x % m + m) % m;
}

// Precompute inverses for 1..n mod p (O(n))
std::vector<int> precomputeInverses(int n, int p) {
    std::vector<int> inv(n + 1);
    inv[1] = 1;
    for (int i = 2; i <= n; i++) {
        inv[i] = (long long)(p - p / i) * inv[p % i] % p;
    }
    return inv;
}

int main() {
    long long m = 1e9 + 7;
    
    // Verify: a * a^(-1) ≡ 1 (mod m)
    for (long long a : {2, 3, 7, 13, 123456789}) {
        long long inv1 = modInverseFermat(a, m);
        long long inv2 = modInverseExtGcd(a, m);
        
        assert(inv1 == inv2);
        assert((__int128)a * inv1 % m == 1);
        
        std::cout << a << "^(-1) mod " << m << " = " << inv1 << "\n";
    }
    
    // Precompute inverses
    auto inv = precomputeInverses(10, m);
    std::cout << "\nPrecomputed inverses mod " << m << ":\n";
    for (int i = 1; i <= 10; i++) {
        std::cout << i << "^(-1) = " << inv[i] << "\n";
    }
    
    return 0;
}
```

### Using Modular Inverse for Division

```
(a / b) mod m = (a × b⁻¹) mod m
```

This is essential for computing `nCr mod p`:

```
nCr mod p = n! × (r!)⁻¹ × ((n-r)!)⁻¹ mod p
```

---

## 60.6 Linear Diophantine Equations

A **linear Diophantine equation** `ax + by = c` has integer solutions if and only if `gcd(a, b) | c`.

```cpp
#include <iostream>
#include <tuple>

std::tuple<long long, long long, long long> extGcd(long long a, long long b) {
    if (b == 0) return {a, 1, 0};
    auto [g, x1, y1] = extGcd(b, a % b);
    return {g, y1, x1 - (a / b) * y1};
}

// Solve ax + by = c
// Returns {x, y, has_solution}
// If has_solution, (x, y) is a particular solution
std::tuple<long long, long long, bool> diophantine(long long a, long long b, 
                                                     long long c) {
    auto [g, x0, y0] = extGcd(a, b);
    
    if (c % g != 0) return {0, 0, false};
    
    long long x = x0 * (c / g);
    long long y = y0 * (c / g);
    
    return {x, y, true};
}

// Find all solutions in range [xMin, xMax]
// General solution: x = x0 + k*(b/g), y = y0 - k*(a/g)
// For x in [xMin, xMax]: k in [(xMin - x0) * g / b, (xMax - x0) * g / b]

int main() {
    // 3x + 5y = 1
    auto [x, y, ok] = diophantine(3, 5, 1);
    if (ok) {
        std::cout << "3*(" << x << ") + 5*(" << y << ") = " 
                  << 3*x + 5*y << "\n";
    }
    
    // 6x + 4y = 10
    auto [x2, y2, ok2] = diophantine(6, 4, 10);
    if (ok2) {
        std::cout << "6*(" << x2 << ") + 4*(" << y2 << ") = " 
                  << 6*x2 + 4*y2 << "\n";
    }
    
    // No solution: 6x + 4y = 7 (gcd(6,4)=2 does not divide 7)
    auto [x3, y3, ok3] = diophantine(6, 4, 7);
    std::cout << "6x + 4y = 7 has " << (ok3 ? "" : "no ") << "solution\n";
    
    return 0;
}
```

---

## 60.7 Matrix Exponentiation

**Matrix exponentiation** computes the n-th power of a matrix in O(k³ log n) time, where k is the matrix dimension. This enables solving linear recurrences in O(k³ log n).

### Classic Application: Fibonacci in O(log n)

```
[f(n+1)]   [1 1]   [f(n)]
[f(n)  ] = [1 0] × [f(n-1)]
```

So `[f(n+1), f(n)]^T = M^n × [f(1), f(0)]^T` where M = [[1,1],[1,0]].

```cpp
#include <iostream>
#include <vector>
#include <array>
#include <cassert>

using Matrix = std::vector<std::vector<long long>>;
const long long MOD = 1e9 + 7;

Matrix multiply(const Matrix& a, const Matrix& b) {
    int n = a.size(), m = b[0].size(), p = b.size();
    Matrix c(n, std::vector<long long>(m, 0));
    
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < p; k++) {
            for (int j = 0; j < m; j++) {
                c[i][j] = (c[i][j] + (__int128)a[i][k] * b[k][j]) % MOD;
            }
        }
    }
    
    return c;
}

Matrix powerMatrix(Matrix base, long long exp) {
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

// Fibonacci: F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2)
long long fibonacci(long long n) {
    if (n <= 1) return n;
    
    Matrix M = {{1, 1}, {1, 0}};
    Matrix Mn = powerMatrix(M, n);
    
    // Mn × [F(1), F(0)]^T = [F(n+1), F(n)]^T
    return Mn[0][1]; // This is F(n)
}

// General linear recurrence: f(n) = c1*f(n-1) + c2*f(n-2) + ... + ck*f(n-k)
// Matrix: [f(n), f(n-1), ..., f(n-k+1)]^T = M × [f(n-1), f(n-2), ..., f(n-k)]^T
// M = [[c1, c2, ..., ck],
//      [1,  0,  ..., 0 ],
//      [0,  1,  ..., 0 ],
//      ...
//      [0,  0,  ..., 0 ]]

long long linearRecurrence(const std::vector<long long>& coeffs,
                           const std::vector<long long>& init,
                           long long n) {
    int k = coeffs.size();
    if (n < k) return init[n];
    
    // Build transition matrix
    Matrix M(k, std::vector<long long>(k, 0));
    for (int j = 0; j < k; j++) M[0][j] = coeffs[j];
    for (int i = 1; i < k; i++) M[i][i-1] = 1;
    
    Matrix Mn = powerMatrix(M, n - k + 1);
    
    // Multiply by initial values
    long long result = 0;
    for (int j = 0; j < k; j++) {
        result = (result + (__int128)Mn[0][j] * init[k - 1 - j]) % MOD;
    }
    
    return result;
}

int main() {
    // Fibonacci
    std::cout << "F(10) = " << fibonacci(10) << "\n"; // 55
    std::cout << "F(50) = " << fibonacci(50) << "\n";
    
    // Tribonacci: f(n) = f(n-1) + f(n-2) + f(n-3)
    // f(0)=0, f(1)=0, f(2)=1
    std::vector<long long> tribCoeffs = {1, 1, 1};
    std::vector<long long> tribInit = {0, 0, 1};
    
    std::cout << "\nTribonacci:\n";
    for (int i = 0; i <= 10; i++) {
        std::cout << "T(" << i << ") = " 
                  << linearRecurrence(tribCoeffs, tribInit, i) << "\n";
    }
    
    return 0;
}
```

### Matrix Exponentiation Applications

| Problem | Matrix Size | Time |
|---|---|---|
| Fibonacci | 2×2 | O(log n) |
| k-step recurrence | k×k | O(k³ log n) |
| Count paths of length n in graph | V×V | O(V³ log n) |
| Linear transformation composition | k×k | O(k³ log n) |

---

## 60.8 Lucas Theorem

**Lucas Theorem** computes `C(n, r) mod p` for prime p and potentially large n, r.

### Theorem

If `n = n_k * p^k + ... + n_1 * p + n_0` and `r = r_k * p^k + ... + r_1 * p + r_0` (base-p representations), then:

```
C(n, r) ≡ ∏ C(n_i, r_i) (mod p)
```

### When to Use

- n and r are very large (up to 10^18), but p is small (up to 10^6)
- Computing nCr mod prime for competitive programming

```cpp
#include <iostream>
#include <vector>
#include <cassert>

const long long MOD = 1e9 + 7;

long long powerMod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = (__int128)result * base % mod;
        base = (__int128)base * base % mod;
        exp >>= 1;
    }
    return result;
}

// Precompute factorials and inverse factorials
class Combinatorics {
    std::vector<long long> fact, invFact;
    long long mod;
    
public:
    Combinatorics(int n, long long mod) : fact(n + 1), invFact(n + 1), mod(mod) {
        fact[0] = 1;
        for (int i = 1; i <= n; i++) fact[i] = (__int128)fact[i-1] * i % mod;
        invFact[n] = powerMod(fact[n], mod - 2, mod);
        for (int i = n - 1; i >= 0; i--) invFact[i] = (__int128)invFact[i+1] * (i+1) % mod;
    }
    
    long long nCr(int n, int r) {
        if (r < 0 || r > n) return 0;
        return (__int128)fact[n] * invFact[r] % mod * invFact[n-r] % mod;
    }
};

// Lucas Theorem: C(n, r) mod p
long long lucasTheorem(long long n, long long r, long long p) {
    if (r == 0) return 1;
    
    Combinatorics comb(p, p); // Precompute up to p-1
    
    long long result = 1;
    while (n > 0 || r > 0) {
        int ni = n % p, ri = r % p;
        if (ri > ni) return 0;
        result = (__int128)result * comb.nCr(ni, ri) % p;
        n /= p;
        r /= p;
    }
    
    return result;
}

int main() {
    long long p = 7;
    
    // C(10, 3) mod 7
    // C(10, 3) = 120, 120 mod 7 = 1
    std::cout << "C(10, 3) mod 7 = " << lucasTheorem(10, 3, p) << "\n";
    
    // C(100, 50) mod 7
    std::cout << "C(100, 50) mod 7 = " << lucasTheorem(100, 50, p) << "\n";
    
    // Large n: C(10^18, 10^17) mod 7
    long long bigN = 1000000000000000000LL;
    long long bigR = 100000000000000000LL;
    std::cout << "C(10^18, 10^17) mod 7 = " << lucasTheorem(bigN, bigR, p) << "\n";
    
    return 0;
}
```

---

## 60.9 Miller-Rabin Primality Test

**Miller-Rabin** is a probabilistic primality test. For a composite number, the probability of incorrectly declaring it prime is at most 4^(-k) after k rounds.

### How It Works

For n > 2, write n-1 = 2^r × d where d is odd.

For each witness a:
1. Compute x = a^d mod n
2. If x == 1 or x == n-1, continue to next witness
3. Square x up to r-1 times. If x == n-1, continue
4. Otherwise, n is composite

### Deterministic for Small n

Using witnesses {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}, Miller-Rabin is deterministic for n < 3.3 × 10^24.

```cpp
#include <iostream>
#include <vector>
#include <cassert>

long long powerMod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = (__int128)result * base % mod;
        base = (__int128)base * base % mod;
        exp >>= 1;
    }
    return result;
}

bool millerRabin(long long n, long long a) {
    if (n % a == 0) return n == a;
    
    long long d = n - 1;
    int r = 0;
    while (d % 2 == 0) {
        d /= 2;
        r++;
    }
    
    long long x = powerMod(a, d, n);
    if (x == 1 || x == n - 1) return true;
    
    for (int i = 0; i < r - 1; i++) {
        x = (__int128)x * x % n;
        if (x == n - 1) return true;
    }
    
    return false;
}

bool isPrime(long long n) {
    if (n < 2) return false;
    if (n < 4) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    
    // Deterministic witnesses for n < 3.3 * 10^24
    std::vector<long long> witnesses = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    
    for (long long a : witnesses) {
        if (a >= n) break;
        if (!millerRabin(n, a)) return false;
    }
    
    return true;
}

int main() {
    // Test known primes
    std::vector<long long> primes = {2, 3, 5, 7, 11, 13, 97, 1000000007};
    for (long long p : primes) {
        assert(isPrime(p));
        std::cout << p << " is prime\n";
    }
    
    // Test known composites
    std::vector<long long> composites = {4, 6, 8, 9, 15, 21, 100, 561}; // 561 = 3*11*17 (Carmichael)
    for (long long c : composites) {
        assert(!isPrime(c));
        std::cout << c << " is composite\n";
    }
    
    // Large prime
    long long bigPrime = 100000000000000003LL;
    std::cout << bigPrime << " is " << (isPrime(bigPrime) ? "prime" : "composite") << "\n";
    
    return 0;
}
```

### Complexity

| Aspect | Value |
|---|---|
| Time per witness | O(log n) |
| Number of witnesses | O(log n) for probabilistic, O(1) for deterministic (bounded n) |
| Total time | O(k log n) where k = number of witnesses |
| Error probability | ≤ 4^(-k) |

---

## Summary

| Algorithm | Key Insight | Time | Use Case |
|---|---|---|---|
| Binary Exponentiation | Repeated squaring | O(log n) | a^n mod m |
| Extended Euclid | Back-substitute GCD steps | O(log n) | ax + by = gcd |
| CRT | Combine modular equations | O(k log M) | System of congruences |
| Euler's Totient | Count coprimes | O(√n) | Euler's theorem |
| Modular Inverse | a^(p-2) mod p | O(log p) | Division in modular arithmetic |
| Diophantine | Extended GCD + scaling | O(log n) | Integer solutions |
| Matrix Exponentiation | Repeated matrix squaring | O(k³ log n) | Linear recurrences |
| Lucas Theorem | Digit-by-digit combination | O(log_p n) | nCr mod p |
| Miller-Rabin | Witness-based primality | O(k log n) | Primality testing |

### When NOT to Use Number Theory

| Situation | Why Not | Better Alternative |
|---|---|---|
| Simple divisibility | Overkill | Direct modulo check |
| Small primes only | Sieve is simpler | Sieve of Eratosthenes |
| No modular arithmetic needed | Unnecessary complexity | Basic math |
| Floating-point sufficient | Exact arithmetic is slower | Standard math library |
| Non-prime modulus | Fermat's little theorem doesn't apply | Extended GCD for inverse |

### Number Theory Trade-offs

| Technique | Pro | Con |
|---|---|---|
| Binary exponentiation | O(log n), simple | Overflow risk with large mod |
| Extended GCD | Works for non-prime mod | More complex than Fermat |
| CRT | Combines modular equations | Requires pairwise coprime moduli |
| Sieve totient | O(n) for all φ values | O(n) space |
| Matrix exponentiation | Solves linear recurrences | O(k³) per multiplication |
| Miller-Rabin | Fast primality test | Probabilistic (error negligible) |
| Lucas Theorem | Handles huge n | Only works for prime modulus |

---

## 60.10 Segmented Sieve

Generate primes in range [L, R] where R can be large but R-L is small.

```cpp
#include <iostream>
#include <vector>
#include <cmath>

std::vector<long long> segmentedSieve(long long L, long long R) {
    int limit = std::sqrt(R) + 1;
    std::vector<bool> isPrimeSmall(limit + 1, true);
    std::vector<long long> primes;
    
    // Sieve for small primes
    for (int i = 2; i <= limit; i++) {
        if (isPrimeSmall[i]) {
            primes.push_back(i);
            for (int j = i * i; j <= limit; j += i)
                isPrimeSmall[j] = false;
        }
    }
    
    // Segmented sieve for [L, R]
    std::vector<bool> isPrime(R - L + 1, true);
    
    for (long long p : primes) {
        long long start = std::max(p * p, (L + p - 1) / p * p);
        for (long long j = start; j <= R; j += p)
            isPrime[j - L] = false;
    }
    
    if (L == 1) isPrime[0] = false;
    
    std::vector<long long> result;
    for (long long i = 0; i <= R - L; i++)
        if (isPrime[i]) result.push_back(L + i);
    
    return result;
}

int main() {
    auto primes = segmentedSieve(1000000000LL, 1000000100LL);
    std::cout << "Primes in [10^9, 10^9+100]:\n";
    for (long long p : primes) std::cout << p << " ";
    std::cout << "\n";
    return 0;
}
```

---

## 60.11 Wilson's Theorem

A number p > 1 is prime if and only if (p-1)! ≡ -1 (mod p).

This is a primality test (not practical for large p, but theoretically important).

---

## 60.12 Pollard's Rho Algorithm (Overview)

A probabilistic algorithm for integer factorization. Expected time O(n^{1/4}) to find a factor.

**Key idea**: Use a pseudorandom sequence and Floyd's cycle detection to find a non-trivial factor via GCD.

**Used for**: Factoring large numbers, RSA cryptanalysis.

---

### Pollard's Rho Implementation

```cpp
#include <iostream>
#include <random>
#include <chrono>
#include <numeric>

long long mulmod(long long a, long long b, long long mod) {
    return (__int128)a * b % mod;
}

long long powerMod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = mulmod(result, base, mod);
        base = mulmod(base, base, mod);
        exp >>= 1;
    }
    return result;
}

long long pollardRho(long long n) {
    if (n % 2 == 0) return 2;
    
    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    long long x = rng() % (n - 2) + 2;
    long long y = x;
    long long c = rng() % (n - 1) + 1;
    long long d = 1;
    
    while (d == 1) {
        x = (mulmod(x, x, n) + c) % n;
        y = (mulmod(y, y, n) + c) % n;
        y = (mulmod(y, y, n) + c) % n;
        d = std::gcd(std::abs(x - y), n);
    }
    
    return d == n ? -1 : d;
}

int main() {
    long long n = 1000000007LL * 998244353LL; // Product of two primes
    long long factor = pollardRho(n);
    std::cout << "Factor of " << n << ": " << factor << "\\n";
    std::cout << "Other factor: " << n / factor << "\\n";
    return 0;
}
```
