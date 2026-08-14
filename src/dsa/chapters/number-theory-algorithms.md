# Number Theory Algorithms Toolkit

A practical reference for the number theory algorithms most frequently encountered in technical interviews and competitive programming. For deeper mathematical treatment, see Chapter 60 (Number Theory).

---

## Modular Arithmetic Operations

All operations are performed modulo `m`. Key rules:

- `(a + b) % m = ((a % m) + (b % m)) % m`
- `(a * b) % m = ((a % m) * (b % m)) % m`
- `(a - b) % m = ((a % m) - (b % m) + m) % m`  (add m to avoid negative)
- `(a / b) % m` requires modular inverse (see below)

**Critical:** Use `long long` for intermediate products to avoid overflow: `(a % m) * (b % m)` can overflow `int` even when `a, b < m`.

---

## Extended Euclidean Algorithm & Modular Inverse

The extended Euclidean algorithm finds `x, y` such that `ax + by = gcd(a, b)`. When `gcd(a, m) = 1`, `x` is the modular inverse of `a` modulo `m`.

```cpp
long long modInverse(long long a, long long m) {
    long long g, x, y;
    auto extGcd = [&](auto& self, long long a, long long b, long long& x, long long& y) -> long long {
        if (b == 0) { x = 1; y = 0; return a; }
        long long x1, y1;
        long long g = self(self, b, a % b, x1, y1);
        x = y1;
        y = x1 - (a / b) * y1;
        return g;
    };
    g = extGcd(extGcd, a, m, x, y);
    if (g != 1) return -1; // inverse doesn't exist
    return ((x % m) + m) % m;
}
```

**Python shortcut:** `pow(a, -1, m)` in Python 3.8+ computes modular inverse using the same algorithm.

**Complexity:** O(log min(a, m)).

---

## Binary (Fast) Exponentiation

Computes `a^b % m` in O(log b) by repeatedly squaring.

```python
def power(a, b, m):
    result = 1
    a %= m
    while b > 0:
        if b & 1:
            result = result * a % m
        a = a * a % m
        b >>= 1
    return result
```

**Complexity:** O(log b) time, O(1) space. This is the workhorse of all modular computation.

---

## Chinese Remainder Theorem (CRT)

Given congruences `x = a_i (mod m_i)` where all `m_i` are coprime, find `x`.

```python
def crt(remainders, moduli):
    """Solve x = remainders[i] (mod moduli[i]) for all i. Returns (x, M)."""
    from math import gcd
    x, M = 0, 1
    for r, m in zip(remainders, moduli):
        g = gcd(M, m)
        if (r - x) % g != 0:
            return None  # No solution
        # Merge x = a (mod M) and x = r (mod m)
        lcm = M * m // g
        inv = pow(M // g, -1, m // g)
        x = (x + (r - x) // g * inv % (m // g) * M) % lcm
        M = lcm
    return (x, M)
```

**Complexity:** O(k log M) for k congruences. Generalized CRT works even when moduli aren't coprime.

---

## Euler's Totient Function

`phi(n)` counts integers in [1, n] coprime to n. Key properties:

- `phi(p) = p - 1` for prime `p`
- `phi(p^k) = p^k - p^(k-1)`
- `phi(ab) = phi(a) * phi(b)` when `gcd(a, b) = 1` (multiplicative)
- `sum(phi(d) for d | n) = n`

```cpp
int eulerPhi(int n) {
    int result = n;
    for (int p = 2; (long long)p * p <= n; p++) {
        if (n % p == 0) {
            while (n % p == 0) n /= p;
            result -= result / p;
        }
    }
    if (n > 1) result -= result / n;
    return result;
}
```

**Complexity:** O(sqrt(n)). Can compute `phi(1..n)` for all values in O(n log log n) using a sieve.

---

## Sieve of Eratosthenes

```cpp
vector<int> sieve(int n) {
    vector<int> primes, isPrime(n + 1, 1);
    isPrime[0] = isPrime[1] = 0;
    for (int i = 2; i <= n; i++) {
        if (isPrime[i]) {
            primes.push_back(i);
            for (long long j = (long long)i * i; j <= n; j += i)
                isPrime[j] = 0;
        }
    }
    return primes;
}
```

**Complexity:** O(n log log n) time, O(n) space. For ranges up to 10^12, use **segmented sieve** — process blocks of size sqrt(R) one at a time.

---

## Miller-Rabin Primality Test

Probabilistic primality test. For 64-bit integers, testing witnesses {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37} is deterministic.

```cpp
using ull = unsigned long long;

ull modMul(ull a, ull b, ull m) {
    return (__uint128_t)a * b % m; // GCC extension for 128-bit
}

ull modPow(ull a, ull b, ull m) {
    ull r = 1; a %= m;
    for (; b; b >>= 1) {
        if (b & 1) r = modMul(r, a, m);
        a = modMul(a, a, m);
    }
    return r;
}

bool millerRabin(ull n, ull a) {
    if (n % a == 0) return n == a;
    ull d = n - 1; int r = 0;
    while (d % 2 == 0) d /= 2, r++;
    ull x = modPow(a, d, n);
    if (x == 1 || x == n - 1) return true;
    for (int i = 0; i < r - 1; i++) {
        x = modMul(x, x, n);
        if (x == n - 1) return true;
    }
    return false;
}

bool isPrime(ull n) {
    if (n < 2) return false;
    for (ull a : {2,3,5,7,11,13,17,19,23,29,31,37})
        if (!millerRabin(n, a)) return false;
    return true;
}
```

**Complexity:** O(k log^3 n) for k witnesses. Deterministic for n < 3.3 * 10^24 with the witness set above.

---

## Pollard's Rho Factorization

```cpp
ull pollardRho(ull n) {
    if (n % 2 == 0) return 2;
    ull x = rand() % (n - 2) + 2, y = x, c = rand() % (n - 1) + 1;
    ull d = 1;
    auto f = [&](ull x) { return (modMul(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x); y = f(f(y));
        d = __gcd(x > y ? x - y : y - x, n);
    }
    return d == n ? pollardRho(n) : d;
}

vector<ull> factorize(ull n) {
    if (n <= 1) return {};
    if (isPrime(n)) return {n};
    ull d = pollardRho(n);
    auto left = factorize(d), right = factorize(n / d);
    left.insert(left.end(), right.begin(), right.end());
    return left;
}
```

**Complexity:** O(n^(1/4) polylog(n)) expected. Combined with Miller-Rabin for base case, gives full factorization.

---

## Matrix Exponentiation

Compute the k-th term of a linear recurrence in O(n^3 log k) using matrix power. For Fibonacci: `F(k) = M^k[0][1]` where `M = [[1,1],[1,0]]`.

```python
def mat_mul(A, B, mod):
    n = len(A)
    C = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % mod
    return C

def mat_pow(M, p, mod):
    n = len(M)
    result = [[int(i==j) for j in range(n)] for i in range(n)]  # identity
    while p > 0:
        if p & 1:
            result = mat_mul(result, M, mod)
        M = mat_mul(M, M, mod)
        p >>= 1
    return result

def fibonacci(k, mod=10**9+7):
    if k <= 1: return k
    M = [[1,1],[1,0]]
    return mat_pow(M, k-1, mod)[0][0]
```

**Complexity:** O(d^3 log k) for a recurrence of order d. Works for any linear recurrence.

---

## Interview Questions

1. **Compute (a/b) mod m for large a, b.** When does the modular inverse not exist? How do you handle it?

2. **Find the last k digits of 2^1000.** Use binary exponentiation. What modulus do you use?

3. **Given `n` equations `x = a_i (mod m_i)`, find the smallest non-negative `x`.** Implement CRT. What if two moduli share a factor?

4. **How many integers in [1, n] are coprime to n?** Compute phi(n) and explain its connection to Euler's theorem.

5. **Is 10^18 + 3 prime?** Explain why trial division fails and describe Miller-Rabin.

6. **Find the 10^18-th Fibonacci number mod 10^9 + 7.** Use matrix exponentiation. What is the time complexity?

7. **Factorize n = 10^15 + 37.** Describe the algorithm. Why is Pollard's Rho faster than trial division?

8. **Count the number of primes in [L, R] where L, R can be up to 10^12.** Describe the segmented sieve approach.

9. **Given a linear recurrence a(n) = 7*a(n-1) - 3*a(n-2), find a(10^9) mod m.** How do you set up the matrix?

10. **Why is `(a * b) % m` dangerous when a, b, m are up to 10^18?** Explain the overflow issue and solutions (__int128, mulmod).