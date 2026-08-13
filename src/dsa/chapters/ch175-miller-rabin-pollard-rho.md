# Chapter 175: Miller-Rabin and Pollard Rho

## 1. Introduction

**Miller-Rabin** is a probabilistic primality test that determines whether a number is prime with high accuracy in O(k log² n) time. **Pollard Rho** is a probabilistic factorization algorithm that finds a non-trivial factor of a composite number in expected O(n^{1/4}) time. Together, they form the backbone of modern primality testing and integer factorization.

### Why Should You Care?

- **Primality Testing**: Quickly determine if a large number (up to 10^18) is prime.
- **Integer Factorization**: Decompose a number into its prime factors.
- **RSA Cryptography**: The security of RSA relies on the difficulty of factoring large semiprimes.
- **Competitive Programming**: Problems involving prime factorization of large numbers.
- **Number Theory**: Foundation for many number-theoretic algorithms.

---

## 2. Background: Primality Testing

### 2.1 Trial Division

The simplest approach: check divisibility by all integers from 2 to √n.

**Time complexity**: O(√n).

For n = 10^18, √n = 10^9 — too slow.

### 2.2 Fermat's Little Theorem

If p is prime and gcd(a, p) = 1, then:
\\[a^{p-1} \equiv 1 \pmod{p}\\]

**Fermat primality test**: Pick random a, check if a^{n-1} ≡ 1 (mod n). If not, n is composite.

**Problem**: Carmichael numbers (like 561 = 3 × 11 × 17) pass the Fermat test for all a coprime to n, yet are composite.

---

## 3. Miller-Rabin Primality Test

### 3.1 Core Idea

Miller-Rabin strengthens Fermat's test by also checking for non-trivial square roots of 1 modulo n.

**Key fact**: If p is an odd prime and x² ≡ 1 (mod p), then x ≡ 1 or x ≡ -1 (mod p).

### 3.2 Mathematical Foundation

Write n - 1 = 2^s · d where d is odd.

For a "witness" a:
1. Compute x = a^d mod n.
2. If x ≡ 1 or x ≡ n-1, the test is inconclusive (n might be prime).
3. Otherwise, repeatedly square x up to s-1 times:
   - If x ≡ n-1 at any point, inconclusive.
   - If x ≡ 1 after squaring (but wasn't n-1 before), n is composite (found a non-trivial square root of 1).
4. If we never see x ≡ n-1, n is composite.

### 3.3 The Algorithm

```
function miller_rabin(n, k):
    if n < 2: return false
    if n == 2 or n == 3: return true
    if n is even: return false

    # Write n-1 = 2^s * d
    s = 0, d = n - 1
    while d is even:
        d //= 2
        s += 1

    # Test k witnesses
    for i = 1 to k:
        a = random(2, n-2)
        x = pow(a, d, n)

        if x == 1 or x == n-1:
            continue

        for r = 1 to s-1:
            x = (x * x) % n
            if x == n-1:
                break
        else:
            return false  # composite

    return true  # probably prime
```

### 3.4 Witness Selection

For n < 2^64, testing against specific witnesses gives a **deterministic** result:

| Range | Witnesses | Source |
|-------|-----------|--------|
| n < 2,047 | {2} | — |
| n < 1,373,653 | {2, 3} | — |
| n < 9,080,191 | {31, 73} | — |
| n < 25,326,001 | {2, 3, 5} | — |
| n < 3,215,031,751 | {2, 3, 5, 7} | — |
| n < 4,759,123,141 | {2, 7, 61} | — |
| n < 1,122,004,669,633 | {2, 13, 23, 1662803} | — |
| n < 2^64 | {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37} | Deterministic |

For competitive programming, using the set {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37} is sufficient for all 64-bit integers.

---

## 4. Step-by-Step Walkthrough

### 4.1 Example: Is 561 prime?

561 = 3 × 11 × 17 (Carmichael number).

n - 1 = 560 = 2^4 × 35, so s = 4, d = 35.

**Test with a = 2**:
```
x = 2^35 mod 561 = 263
263 ≠ 1 and 263 ≠ 560

r=1: x = 263² mod 561 = 166, 166 ≠ 560
r=2: x = 166² mod 561 = 67,  67 ≠ 560
r=3: x = 67² mod 561 = 1,    1 ≠ 560

We reached x=1 without seeing 560 → COMPOSITE!
```

Even though 561 is a Carmichael number, Miller-Rabin correctly identifies it as composite.

### 4.2 Example: Is 104729 prime?

n - 1 = 104728 = 2^3 × 13091, so s = 3, d = 13091.

**Test with a = 2**:
```
x = 2^13091 mod 104729 = 36639
36639 ≠ 1 and 36639 ≠ 104728

r=1: x = 36639² mod 104729 = 104728 ≡ n-1 ✓

Inconclusive → probably prime.
```

Test with more witnesses → all inconclusive → **PRIME**. ✓

### 4.3 Dry Run: Miller-Rabin for n = 221

221 = 13 × 17 (composite).

n - 1 = 220 = 2^2 × 55, so s = 2, d = 55.

**Test with a = 2**:
```
x = 2^55 mod 221 = 128
128 ≠ 1, 128 ≠ 220

r=1: x = 128² mod 221 = 30, 30 ≠ 220

Loop ends, x never became n-1 → COMPOSITE! ✓
```

---

## 5. Pollard Rho Factorization

### 5.1 Motivation

Miller-Rabin tells us IF n is composite, but not WHAT its factors are. Pollard Rho finds a non-trivial factor.

### 5.2 Birthday Paradox Insight

If n has a factor p, and we generate random numbers mod n, the probability that two numbers are congruent mod p is approximately 1/√p after √p samples (birthday paradox). We can detect this using gcd.

### 5.3 Floyd's Cycle Detection

Use the function f(x) = (x² + c) mod n to generate a pseudo-random sequence:
```
x₀, x₁ = f(x₀), x₂ = f(x₁), ...
```

Maintain two pointers:
- **Tortoise**: moves one step (x = f(x))
- **Hare**: moves two steps (x = f(f(x)))

Periodically compute gcd(|tortoise - hare|, n). If 1 < gcd < n, we found a factor.

### 5.4 The Algorithm

```
function pollard_rho(n):
    if n is even: return 2
    if is_prime(n): return n

    while true:
        c = random(1, n-1)
        x = random(2, n-1)
        y = x
        d = 1

        while d == 1:
            x = (x*x + c) % n      # tortoise
            y = (y*y + c) % n      # hare
            y = (y*y + c) % n      # hare
            d = gcd(|x - y|, n)

        if d != n: return d
        # Otherwise, try different c
```

### 5.5 Complexity

**Expected time**: O(n^{1/4}) per factor found.

For n = 10^18, n^{1/4} ≈ 31623 — very fast.

---

## 6. Full Factorization

To completely factorize n:

```
function factorize(n, factors):
    if n == 1: return
    if is_prime(n):
        factors.append(n)
        return
    d = pollard_rho(n)
    factorize(d, factors)
    factorize(n / d, factors)
```

### 6.1 Example: Factorize 100

```
factorize(100):
  100 is not prime
  pollard_rho(100) → 2
  factorize(2): 2 is prime → [2]
  factorize(50):
    50 is not prime
    pollard_rho(50) → 2
    factorize(2): 2 is prime → [2]
    factorize(25):
      25 is not prime
      pollard_rho(25) → 5
      factorize(5): 5 is prime → [5]
      factorize(5): 5 is prime → [5]
    → [2, 5, 5]
  → [2, 2, 5, 5]

Result: 100 = 2² × 5²
```

---

## 7. Applications

### 7.1 RSA Cryptography

RSA relies on:
1. Choose two large primes p, q.
2. Compute n = p × q.
3. The public key is (n, e), private key involves p, q.

**Security**: Factoring n to find p, q is hard for large n (2048+ bits). Pollard Rho is too slow for such numbers but works for smaller semiprimes.

### 7.2 Competitive Programming

**Problem**: Given n (up to 10^18), find its prime factorization.

**Solution**: Miller-Rabin for primality + Pollard Rho for factorization.

### 7.3 Euler's Totient

φ(n) requires prime factorization. With Pollard Rho:
```
φ(n) = n × Π(1 - 1/p) for each distinct prime p dividing n
```

### 7.4 Divisor Count / Sum

Number of divisors: d(n) = Π(eᵢ + 1) for n = Π pᵢ^{eᵢ}.
Sum of divisors: σ(n) = Π(pᵢ^{eᵢ+1} - 1)/(pᵢ - 1).

Both require factorization.

---

## 8. Complexity Analysis

| Algorithm | Time | Space |
|-----------|------|-------|
| Miller-Rabin (k witnesses) | O(k log² n) | O(1) |
| Miller-Rabin (deterministic, 64-bit) | O(log² n) | O(1) |
| Pollard Rho (expected) | O(n^{1/4}) | O(1) |
| Full factorization | O(n^{1/4} · log n) | O(log n) |

---

## 9. Code Implementations

### 9.1 C++ — Miller-Rabin + Pollard Rho

```cpp
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
typedef __int128 lll;  // For 128-bit multiplication

ll mul(ll a, ll b, ll mod) {
    return (lll)a * b % mod;
}

ll power(ll base, ll exp, ll mod) {
    ll result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = mul(result, base, mod);
        base = mul(base, base, mod);
        exp >>= 1;
    }
    return result;
}

bool miller_test(ll d, ll n, ll a) {
    ll x = power(a, d, n);
    if (x == 1 || x == n - 1) return true;

    while (d != n - 1) {
        x = mul(x, x, n);
        d *= 2;
        if (x == 1) return false;
        if (x == n - 1) return true;
    }
    return false;
}

bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;

    ll d = n - 1;
    while (d % 2 == 0) d /= 2;

    // Deterministic for n < 2^64
    vector<ll> witnesses = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (ll a : witnesses) {
        if (a >= n) break;
        if (!miller_test(d, n, a)) return false;
    }
    return true;
}

ll pollard_rho(ll n) {
    if (n % 2 == 0) return 2;
    if (is_prime(n)) return n;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<ll> dist(2, n - 1);

    while (true) {
        ll c = dist(rng);
        ll x = dist(rng), y = x;
        ll d = 1;

        while (d == 1) {
            x = (mul(x, x, n) + c) % n;
            y = (mul(y, y, n) + c) % n;
            y = (mul(y, y, n) + c) % n;
            d = __gcd(abs(x - y), n);
        }

        if (d != n) return d;
    }
}

void factorize(ll n, vector<ll>& factors) {
    if (n == 1) return;
    if (is_prime(n)) {
        factors.push_back(n);
        return;
    }
    ll d = pollard_rho(n);
    factorize(d, factors);
    factorize(n / d, factors);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll n;
    cin >> n;

    // Primality test
    cout << n << (is_prime(n) ? " is prime\n" : " is not prime\n");

    // Factorization
    vector<ll> factors;
    factorize(n, factors);
    sort(factors.begin(), factors.end());

    cout << "Factorization: ";
    for (ll f : factors) cout << f << " ";
    cout << "\n";

    return 0;
}
```

### 9.2 Python — Miller-Rabin + Pollard Rho

```python
import random
from math import gcd

def power_mod(base, exp, mod):
    """Compute (base^exp) % mod efficiently."""
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = (result * base) % mod
        base = (base * base) % mod
        exp >>= 1
    return result

def miller_test(d, n, a):
    """Single Miller-Rabin witness test."""
    x = power_mod(a, d, n)
    if x == 1 or x == n - 1:
        return True
    while d != n - 1:
        x = (x * x) % n
        d *= 2
        if x == 1:
            return False
        if x == n - 1:
            return True
    return False

def is_prime(n):
    """Deterministic Miller-Rabin for n < 2^64."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    d = n - 1
    while d % 2 == 0:
        d //= 2

    witnesses = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for a in witnesses:
        if a >= n:
            break
        if not miller_test(d, n, a):
            return False
    return True

def pollard_rho(n):
    """Find a non-trivial factor of n."""
    if n % 2 == 0:
        return 2
    if is_prime(n):
        return n

    while True:
        c = random.randrange(1, n)
        x = random.randrange(2, n)
        y = x
        d = 1

        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = gcd(abs(x - y), n)

        if d != n:
            return d

def factorize(n):
    """Return list of prime factors of n (with repetition)."""
    if n == 1:
        return []
    if is_prime(n):
        return [n]
    d = pollard_rho(n)
    return factorize(d) + factorize(n // d)

if __name__ == "__main__":
    n = int(input())
    print(f"{n} {'is prime' if is_prime(n) else 'is not prime'}")

    factors = sorted(factorize(n))
    print(f"Factorization: {' '.join(map(str, factors))}")
```

### 9.3 Java — Miller-Rabin + Pollard Rho

```java
import java.util.*;
import java.math.BigInteger;

public class MillerRabinPollardRho {

    static long mul(long a, long b, long mod) {
        return BigInteger.valueOf(a).multiply(BigInteger.valueOf(b))
                .mod(BigInteger.valueOf(mod)).longValue();
    }

    static long power(long base, long exp, long mod) {
        long result = 1;
        base %= mod;
        while (exp > 0) {
            if ((exp & 1) == 1)
                result = mul(result, base, mod);
            base = mul(base, base, mod);
            exp >>= 1;
        }
        return result;
    }

    static boolean millerTest(long d, long n, long a) {
        long x = power(a, d, n);
        if (x == 1 || x == n - 1) return true;

        while (d != n - 1) {
            x = mul(x, x, n);
            d *= 2;
            if (x == 1) return false;
            if (x == n - 1) return true;
        }
        return false;
    }

    static boolean isPrime(long n) {
        if (n < 2) return false;
        if (n == 2 || n == 3) return true;
        if (n % 2 == 0) return false;

        long d = n - 1;
        while (d % 2 == 0) d /= 2;

        long[] witnesses = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
        for (long a : witnesses) {
            if (a >= n) break;
            if (!millerTest(d, n, a)) return false;
        }
        return true;
    }

    static long pollardRho(long n) {
        if (n % 2 == 0) return 2;
        if (isPrime(n)) return n;

        Random rng = new Random();
        while (true) {
            long c = rng.nextLong() % (n - 1) + 1;
            long x = rng.nextLong() % (n - 2) + 2;
            long y = x;
            long d = 1;

            while (d == 1) {
                x = (mul(x, x, n) + c) % n;
                y = (mul(y, y, n) + c) % n;
                y = (mul(y, y, n) + c) % n;
                d = gcd(Math.abs(x - y), n);
            }

            if (d != n) return d;
        }
    }

    static long gcd(long a, long b) {
        while (b != 0) {
            long t = b;
            b = a % b;
            a = t;
        }
        return a;
    }

    static void factorize(long n, List<Long> factors) {
        if (n == 1) return;
        if (isPrime(n)) {
            factors.add(n);
            return;
        }
        long d = pollardRho(n);
        factorize(d, factors);
        factorize(n / d, factors);
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        long n = sc.nextLong();

        System.out.println(n + (isPrime(n) ? " is prime" : " is not prime"));

        List<Long> factors = new ArrayList<>();
        factorize(n, factors);
        Collections.sort(factors);

        System.out.print("Factorization: ");
        for (long f : factors) System.out.print(f + " ");
        System.out.println();
    }
}
```

---

## 10. Optimizations

### 10.1 Modular Multiplication

For numbers up to 10^18, multiplying two such numbers can overflow 64-bit integers. Solutions:

1. **__int128** (GCC): `return (__int128)a * b % mod;`
2. **BigInteger** (Java): `BigInteger.valueOf(a).multiply(BigInteger.valueOf(b)).mod(...)`
3. **Russian peasant multiplication**:
```cpp
ll mul(ll a, ll b, ll mod) {
    ll result = 0;
    a %= mod;
    while (b > 0) {
        if (b & 1) result = (result + a) % mod;
        a = (a * 2) % mod;
        b >>= 1;
    }
    return result;
}
```

### 10.2 Pre-check Small Primes

Before running Miller-Rabin, check divisibility by small primes (2, 3, 5, 7, 11, 13, ...) to quickly eliminate composites:

```cpp
bool is_prime(ll n) {
    if (n < 2) return false;
    for (ll p : {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37})
        if (n % p == 0) return n == p;
    // ... continue with Miller-Rabin
}
```

### 10.3 Brent's Modification

Instead of Floyd's cycle detection, use Brent's variant which is ~36% faster:

```cpp
ll brent(ll n, ll x0, ll c) {
    ll x = x0, y = x0, d = 1;
    ll power = 1, lam = 1;

    while (d == 1) {
        x = (mul(x, x, n) + c) % n;
        if (power == lam) {
            y = x;
            power *= 2;
            lam = 0;
        }
        lam++;
        d = __gcd(abs(x - y), n);
    }
    return d;
}
```

---

## 11. Common Pitfalls

1. **Overflow in multiplication**: Always use 128-bit or BigInteger for modular multiplication with large numbers.
2. **Deterministic witnesses**: Using too few witnesses may give false positives for certain ranges.
3. **Pollard Rho infinite loop**: If n is prime, Pollard Rho never finds a factor — always check primality first.
4. **Base case in factorize**: Forgetting n == 1 leads to infinite recursion.
5. **Random seed**: Not seeding the RNG can cause Pollard Rho to fail on certain inputs.

---

## 12. Comparison with Other Algorithms

| Algorithm | Type | Time | Best For |
|-----------|------|------|----------|
| Trial Division | Deterministic | O(√n) | Small n (≤ 10^12) |
| Miller-Rabin | Probabilistic | O(k log² n) | Primality testing |
| Pollard Rho | Probabilistic | O(n^{1/4}) | Finding one factor |
| Pollard p-1 | Probabilistic | O(B log n) | Smooth factors |
| ECM | Probabilistic | O(exp(...)) | Medium-sized factors |
| GNFS | Probabilistic | Sub-exponential | Very large n |

---

## 13. Exercises

### Basic
1. Implement Miller-Rabin and test it on numbers up to 10^6 (compare with sieve).
2. Implement Pollard Rho and factorize 1000000007 × 998244353.
3. Count the number of primes in a given range using Miller-Rabin.

### Intermediate
4. Compute Euler's totient φ(n) for n up to 10^18 using Pollard Rho.
5. Find the number of divisors of n (up to 10^18).
6. Implement Brent's modification of Pollard Rho and benchmark against Floyd's.

### Advanced
7. Solve a competitive programming problem requiring factorization of numbers up to 10^18.
8. Implement the p-1 factorization method and compare with Pollard Rho.
9. Use Miller-Rabin + Pollard Rho to compute the Möbius function μ(n) for large n.

---

## 14. Interview Questions

1. **Q**: What is the error probability of Miller-Rabin with k witnesses?
   **A**: At most 4^{-k}. With 10 witnesses, the error probability is less than 10^{-6}.

2. **Q**: Is Miller-Rabin deterministic?
   **A**: For 64-bit integers, yes — specific witness sets give guaranteed correct results. For arbitrary precision, it's probabilistic.

3. **Q**: How does Pollard Rho find factors?
   **A**: It uses a pseudo-random sequence and the birthday paradox. If n has a factor p, two values in the sequence will collide mod p after ~√p steps, detected via gcd.

4. **Q**: What's the expected time for Pollard Rho?
   **A**: O(n^{1/4}) per factor. For a 64-bit number, this is about 31,623 iterations — very fast.

5. **Q**: When would you use Pollard Rho vs trial division?
   **A**: Trial division for n ≤ 10^12, Pollard Rho for n up to 10^18. Beyond that, more sophisticated methods (ECM, GNFS) are needed.

6. **Q**: How do you handle modular multiplication overflow?
   **A**: Use __int128 in C++, BigInteger in Java, or Russian peasant multiplication.

---

## 15. Cross-References

- **Chapter 60 (Number Theory)**: GCD, modular arithmetic, Euler's totient.
- **Chapter 63 (Randomized Algorithms)**: Probabilistic algorithms and analysis.
- **Chapter 172 (Möbius Function)**: Requires prime factorization.
- **Chapter 7 (Hashing)**: Birthday paradox and collision probability.
- **Chapter 163 (Advanced Mathematics)**: Applications in cryptography.

---

## 16. Summary

Miller-Rabin and Pollard Rho are the standard tools for primality testing and integer factorization in competitive programming and practice:

- **Miller-Rabin**: O(k log² n) primality test, deterministic for 64-bit integers.
- **Pollard Rho**: O(n^{1/4}) expected time for finding a factor.
- **Combined**: Full factorization of numbers up to 10^18 in milliseconds.

Key implementation details:
1. Handle modular multiplication overflow (use 128-bit integers).
2. Use deterministic witnesses for 64-bit range.
3. Always check primality before calling Pollard Rho.
4. Recursively factorize until all factors are prime.

These algorithms are essential for problems involving large number arithmetic, cryptography, and number-theoretic computations.
