# Chapter 172: Möbius Function and Inversion

## 1. Introduction

The **Möbius function** μ(n) is one of the most important functions in number theory and combinatorics. Combined with **Möbius inversion**, it provides a powerful technique for converting between sums over divisors and sums over multiples — a technique that appears frequently in competitive programming, combinatorics, and analytic number theory.

The Möbius function is the cornerstone of **inclusion-exclusion over divisibility** and connects deeply to **Dirichlet convolution**, **multiplicative functions**, and the **Riemann zeta function**.

### Why Should You Care?

- **GCD Counting**: Count pairs (i, j) with gcd(i, j) = k efficiently.
- **Coprime Counting**: Count pairs (i, j) with gcd(i, j) = 1.
- **Inclusion-Exclusion**: Handle divisibility constraints elegantly.
- **Dirichlet Convolution**: Understand the algebraic structure of arithmetic functions.
- **Competitive Programming**: Appears in ICPC, Codeforces, and Project Euler problems.

---

## 2. Multiplicative Functions

### 2.1 Definition

An arithmetic function f(n) is **multiplicative** if:

\\[f(1) = 1 \quad \text{and} \quad f(a \cdot b) = f(a) \cdot f(b) \text{ whenever } \gcd(a, b) = 1\\]

It is **completely multiplicative** if f(a · b) = f(a) · f(b) for all a, b (no coprimality requirement).

### 2.2 Examples

| Function | Formula | Multiplicative? |
|----------|---------|----------------|
| Identity ε(n) | ε(1) = 1, ε(n) = 0 for n > 1 | Yes (completely) |
| Constant 1(n) | 1 for all n | Yes |
| Identity id(n) | n | Yes (completely) |
| Euler's totient φ(n) | Count of integers ≤ n coprime to n | Yes |
| Divisor count d(n) | Number of divisors of n | Yes |
| Divisor sum σ(n) | Sum of divisors of n | Yes |
| **Möbius μ(n)** | See below | **Yes** |
| Liouville λ(n) | (-1)^{Ω(n)} | Yes (completely) |

### 2.3 Why Multiplicativity Matters

If f is multiplicative, it's completely determined by its values on prime powers:

\\[f(p_1^{e_1} \cdot p_2^{e_2} \cdots p_k^{e_k}) = f(p_1^{e_1}) \cdot f(p_2^{e_2}) \cdots f(p_k^{e_k})\\]

This means we can compute f(n) from the prime factorization of n in O(√n) or faster with a sieve.

---

## 3. The Möbius Function

### 3.1 Definition

The Möbius function μ(n) is defined as:

\\[\mu(n) = \begin{cases} 1 & \text{if } n = 1 \\ (-1)^k & \text{if } n \text{ is a product of } k \text{ distinct primes} \\ 0 & \text{if } n \text{ has a squared prime factor} \end{cases}\\]

Equivalently:
- μ(1) = 1
- μ(n) = (-1)^k if n = p₁ · p₂ · ... · pₖ (distinct primes)
- μ(n) = 0 if p² | n for any prime p

### 3.2 Values

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|----|----|-----|
| μ(n) | 1 | -1 | -1 | 0 | -1 | 1 | -1 | 0 | 0 | 1 | -1 | 0 |

Note: μ(6) = μ(2·3) = (-1)² = 1, μ(12) = μ(4·3) = 0 (since 4 = 2²).

### 3.3 Key Property

The Möbius function satisfies:

\\[\sum_{d | n} \mu(d) = \begin{cases} 1 & \text{if } n = 1 \\ 0 & \text{if } n > 1 \end{cases}\\]

This is the fundamental identity that makes Möbius inversion work.

**Proof sketch**: For n = p₁^{e₁} · p₂^{e₂} · ... · pₖ^{eₖ}, the sum only gets contributions from d that are products of distinct primes (μ(d) ≠ 0). By inclusion-exclusion:

\\[\sum_{d|n} \mu(d) = \sum_{S \subseteq \{p_1, ..., p_k\}} (-1)^{|S|} = (1-1)^k = 0\\]

---

## 4. Möbius Inversion

### 4.1 The Theorem

If f and g are arithmetic functions related by:

\\[g(n) = \sum_{d | n} f(d)\\]

Then:

\\[f(n) = \sum_{d | n} \mu(d) \cdot g\left(\frac{n}{d}\right) = \sum_{d | n} \mu\left(\frac{n}{d}\right) \cdot g(d)\\]

### 4.2 Proof

Starting from g(n) = Σ_{d|n} f(d):

\\[\sum_{d|n} \mu(d) \cdot g\left(\frac{n}{d}\right) = \sum_{d|n} \mu(d) \sum_{e | \frac{n}{d}} f(e)\\]

Let m = de, so m | n and d | m:

\\[= \sum_{m|n} f(m) \sum_{d | \frac{m}{?}} \mu(d)\\]

More carefully, substitute m = n/(de) → the inner sum becomes Σ_{d|(n/e)} μ(d) = [n/e = 1] = [e = n].

\\[= f(n)\\]

### 4.3 General Form (Dirichlet Inversion)

If:
\\[g(n) = \sum_{d|n} f(d) \cdot h\left(\frac{n}{d}\right)\\]

And h has a Dirichlet inverse h⁻¹, then:
\\[f(n) = \sum_{d|n} g(d) \cdot h^{-1}\left(\frac{n}{d}\right)\\]

Möbius inversion is the special case h = 1 (constant function), where h⁻¹ = μ.

### 4.4 Intuition: Inclusion-Exclusion over Divisors

Think of g(n) as "counting with overcounting" — every divisor of n contributes. Möbius inversion "subtracts out" the overcounting, analogous to inclusion-exclusion:

- Start with all multiples (positive contribution)
- Subtract those divisible by each prime (negative)
- Add back those divisible by pairs of primes (positive)
- Continue...

This is exactly what μ encodes: the alternating sign based on the number of prime factors.

---

## 5. Dirichlet Convolution

### 5.1 Definition

The **Dirichlet convolution** of two arithmetic functions f and g is:

\\[(f * g)(n) = \sum_{d|n} f(d) \cdot g\left(\frac{n}{d}\right)\\]

### 5.2 Properties

1. **Commutativity**: f * g = g * f
2. **Associativity**: (f * g) * h = f * (g * h)
3. **Identity**: f * ε = f (where ε is the identity: ε(1) = 1, ε(n) = 0)
4. **Inverses**: Every f with f(1) ≠ 0 has a Dirichlet inverse f⁻¹
5. **Multiplicativity**: If f and g are multiplicative, so is f * g

### 5.3 Important Identities

| Identity | Meaning |
|----------|---------|
| 1 * μ = ε | Möbius is the inverse of the constant function |
| φ * 1 = id | Euler's totoid: Σ_{d|n} φ(d) = n |
| φ = id * μ | Möbius inversion of the above |
| d = 1 * 1 | Divisor count is 1 convolved with itself |
| σ = id * 1 | Divisor sum |

### 5.4 Computing Dirichlet Convolutions

For two multiplicative functions f, g, their convolution h = f * g is multiplicative and:

\\[h(p^e) = \sum_{i=0}^{e} f(p^i) \cdot g(p^{e-i})\\]

This allows computing h(n) from the prime factorization of n.

---

## 6. Computing the Möbius Function

### 6.1 Sieve Method (Linear Sieve)

The most efficient way to compute μ(n) for all n up to N is using a linear sieve:

```cpp
vector<int> mobius_sieve(int n) {
    vector<int> mu(n + 1, 0);
    vector<int> primes;
    vector<bool> is_composite(n + 1, false);
    
    mu[1] = 1;
    for (int i = 2; i <= n; i++) {
        if (!is_composite[i]) {
            primes.push_back(i);
            mu[i] = -1;  // prime: μ(p) = -1
        }
        for (int p : primes) {
            if (i * p > n) break;
            is_composite[i * p] = true;
            if (i % p == 0) {
                mu[i * p] = 0;  // p² divides i*p
                break;
            } else {
                mu[i * p] = -mu[i];  // flip sign
            }
        }
    }
    return mu;
}
```

**Time**: O(N), **Space**: O(N)

### 6.2 Single Value

To compute μ(n) for a single n:

```python
def mobius(n):
    """Compute μ(n) via trial division. O(√n)."""
    if n == 1:
        return 1
    
    count = 0
    d = 2
    while d * d <= n:
        if n % d == 0:
            n //= d
            count += 1
            if n % d == 0:  # d² divides original n
                return 0
        else:
            d += 1
    
    if n > 1:
        count += 1
    
    return (-1) ** count
```

---

## 7. Applications

### 7.1 Counting Coprime Pairs

**Problem**: Count pairs (i, j) with 1 ≤ i ≤ n, 1 ≤ j ≤ m, gcd(i, j) = 1.

**Solution using Möbius**:

\\[\text{count} = \sum_{i=1}^{n} \sum_{j=1}^{m} [\gcd(i,j) = 1]\\]

Using the identity Σ_{d|gcd(a,b)} μ(d) = [gcd(a,b) = 1]:

\\[= \sum_{i=1}^{n} \sum_{j=1}^{m} \sum_{d|\gcd(i,j)} \mu(d)\\]

\\[= \sum_{d=1}^{\min(n,m)} \mu(d) \cdot \left\lfloor \frac{n}{d} \right\rfloor \cdot \left\lfloor \frac{m}{d} \right\rfloor\\]

This is O(min(n, m)) with the sieve, or O(√n) with prefix sums of μ and grouping by floor values.

### 7.2 Counting Pairs with GCD = k

**Problem**: Count pairs (i, j) with 1 ≤ i ≤ n, 1 ≤ j ≤ m, gcd(i, j) = k.

**Solution**: Substitute i' = i/k, j' = j/k:

\\[\text{count} = \sum_{d=1}^{\min(n/k, m/k)} \mu(d) \cdot \left\lfloor \frac{n}{kd} \right\rfloor \cdot \left\lfloor \frac{m}{kd} \right\rfloor\\]

### 7.3 Sum of GCDs

**Problem**: Compute Σ_{i=1}^{n} Σ_{j=1}^{m} gcd(i, j).

**Solution**: Group by g = gcd(i, j):

\\[\sum_{g=1}^{\min(n,m)} g \cdot \sum_{d=1}^{\min(n/g, m/g)} \mu(d) \cdot \left\lfloor \frac{n}{gd} \right\rfloor \cdot \left\lfloor \frac{m}{gd} \right\rfloor\\]

### 7.4 Euler's Totient via Möbius

\\[\varphi(n) = n \cdot \sum_{d|n} \frac{\mu(d)}{d} = \sum_{d|n} \mu(d) \cdot \frac{n}{d}\\]

### 7.5 LCM Sum

**Problem**: Compute Σ_{i=1}^{n} Σ_{j=1}^{n} lcm(i, j).

Using lcm(i,j) = i·j / gcd(i,j), group by g = gcd(i,j):

\\[= \sum_{g=1}^{n} \frac{1}{g} \sum_{\substack{i \leq n, j \leq n \\ \gcd(i,j) = g}} i \cdot j\\]

After substitution and Möbius inversion, this becomes tractable.

---

## 8. Step-by-Step Walkthrough

### Example: Count coprime pairs (i, j) with 1 ≤ i, j ≤ 6

We want: Σ_{i=1}^{6} Σ_{j=1}^{6} [gcd(i,j) = 1]

**Method 1: Direct enumeration**

All 36 pairs. Non-coprime pairs share a factor:
- gcd = 2: (2,2),(2,4),(2,6),(4,2),(4,4),(4,6),(6,2),(6,4),(6,6) — 9 pairs
- gcd = 3: (3,3),(3,6),(6,3),(6,6) — 4 pairs
- gcd = 6: (6,6) — 1 pair

By inclusion-exclusion: non-coprime = 9 + 4 - 1 = 12 (subtract gcd=6 counted twice)
Wait, let me just count directly:

Pairs with gcd > 1:
gcd=2: (2,2),(2,4),(2,6),(4,2),(4,4),(4,6),(6,2),(6,4),(6,6) — 9
gcd=3: (3,3),(3,6),(6,3),(6,6) — 4
gcd=6: (6,6) — 1

By inclusion-exclusion on "divisible by 2 or 3":
|D₂| = 9, |D₃| = 4, |D₂∩D₃| = |D₆| = 1
|D₂ ∪ D₃| = 9 + 4 - 1 = 12

Coprime pairs = 36 - 12 = **24**.

**Method 2: Möbius formula**

\\[\text{count} = \sum_{d=1}^{6} \mu(d) \cdot \left\lfloor \frac{6}{d} \right\rfloor^2\\]

μ(1) = 1: contribution = 1 × 36 = 36
μ(2) = -1: contribution = -1 × 9 = -9
μ(3) = -1: contribution = -1 × 4 = -4
μ(4) = 0: contribution = 0
μ(5) = -1: contribution = -1 × 1 = -1
μ(6) = 1: contribution = 1 × 1 = 1

Total = 36 - 9 - 4 - 1 + 1 = **24** ✓

### Verifying the Σ μ(d) identity

For n = 6 = 2 × 3:
- μ(1) = 1
- μ(2) = -1
- μ(3) = -1
- μ(6) = 1
- Sum: 1 - 1 - 1 + 1 = 0 ✓

---

## 9. Implementation

### 9.1 C++ Implementation

```cpp
#include <vector>
#include <numeric>
using namespace std;

const int MAXN = 1e7 + 5;

// Linear sieve for Möbius function
struct MobiusSieve {
    vector<int> mu;
    vector<int> primes;
    vector<bool> is_composite;
    
    MobiusSieve(int n) : mu(n + 1, 0), is_composite(n + 1, false) {
        mu[1] = 1;
        for (int i = 2; i <= n; i++) {
            if (!is_composite[i]) {
                primes.push_back(i);
                mu[i] = -1;
            }
            for (int p : primes) {
                if (1LL * i * p > n) break;
                is_composite[i * p] = true;
                if (i % p == 0) {
                    mu[i * p] = 0;
                    break;
                } else {
                    mu[i * p] = -mu[i];
                }
            }
        }
    }
};

/**
 * Count coprime pairs (i, j) with 1 ≤ i ≤ n, 1 ≤ j ≤ m.
 * Time: O(min(n, m)) with precomputed μ
 */
long long count_coprime_pairs(int n, int m, const vector<int>& mu) {
    long long ans = 0;
    for (int d = 1; d <= min(n, m); d++) {
        ans += (long long)mu[d] * (n / d) * (m / d);
    }
    return ans;
}

/**
 * Count pairs with gcd = k.
 * Time: O(min(n/k, m/k)) with precomputed μ
 */
long long count_pairs_gcd_k(int n, int m, int k, const vector<int>& mu) {
    n /= k; m /= k;
    return count_coprime_pairs(n, m, mu);
}

/**
 * Sum of gcd(i, j) for 1 ≤ i ≤ n, 1 ≤ j ≤ m.
 * Time: O(min(n, m))
 */
long long sum_of_gcd(int n, int m, const vector<int>& mu) {
    long long ans = 0;
    for (int g = 1; g <= min(n, m); g++) {
        long long cnt = 0;
        for (int d = 1; d <= min(n / g, m / g); d++) {
            cnt += (long long)mu[d] * (n / (g * d)) * (m / (g * d));
        }
        ans += g * cnt;
    }
    return ans;
}

/**
 * Efficient sum of gcd using grouping.
 * O(√n) per value of g using floor division trick.
 */
long long sum_of_gcd_fast(int n, int m, const vector<int>& mu,
                           const vector<long long>& mu_prefix) {
    // mu_prefix[i] = Σ_{d=1}^{i} μ(d)
    long long ans = 0;
    int lim = min(n, m);
    for (int g = 1; g <= lim; g++) {
        int nn = n / g, mm = m / g;
        // Σ_{d=1}^{min(nn,mm)} μ(d) * (nn/d) * (mm/d)
        // Group by nn/d and mm/d
        long long sub = 0;
        int r;
        for (int l = 1; l <= min(nn, mm); l = r + 1) {
            r = min(nn / (nn / l), mm / (mm / l));
            sub += (mu_prefix[r] - mu_prefix[l - 1]) * (nn / l) * (mm / l);
        }
        ans += g * sub;
    }
    return ans;
}

/**
 * Euler's totient via Möbius: φ(n) = Σ_{d|n} μ(d) * (n/d)
 * For a single value. O(√n).
 */
long long euler_totient_mobius(long long n) {
    if (n == 1) return 1;
    
    long long result = n;
    long long temp = n;
    
    for (long long p = 2; p * p <= temp; p++) {
        if (temp % p == 0) {
            result = result / p * (p - 1);  // φ formula
            while (temp % p == 0) temp /= p;
        }
    }
    if (temp > 1) result = result / temp * (temp - 1);
    
    return result;
}

/**
 * Count numbers in [1, n] coprime to a given set of primes.
 * Uses Möbius-style inclusion-exclusion.
 * Time: O(2^k) where k = number of primes.
 */
long long count_coprime_to_primes(long long n, const vector<int>& primes) {
    int k = primes.size();
    long long ans = 0;
    
    for (int mask = 0; mask < (1 << k); mask++) {
        long long prod = 1;
        int bits = 0;
        for (int i = 0; i < k; i++) {
            if (mask & (1 << i)) {
                prod *= primes[i];
                bits++;
            }
        }
        if (bits % 2 == 0)
            ans += n / prod;
        else
            ans -= n / prod;
    }
    return ans;
}
```

### 9.2 Python Implementation

```python
def mobius_sieve(n):
    """
    Compute Möbius function μ(1..n) using linear sieve.
    
    Returns: list mu where mu[i] = μ(i) for 0 ≤ i ≤ n.
    Time: O(n), Space: O(n)
    """
    mu = [0] * (n + 1)
    is_composite = [False] * (n + 1)
    primes = []
    
    mu[1] = 1
    for i in range(2, n + 1):
        if not is_composite[i]:
            primes.append(i)
            mu[i] = -1
        
        for p in primes:
            if i * p > n:
                break
            is_composite[i * p] = True
            if i % p == 0:
                mu[i * p] = 0
                break
            else:
                mu[i * p] = -mu[i]
    
    return mu


def mobius(n):
    """
    Compute μ(n) for a single n via trial division.
    Time: O(√n)
    """
    if n == 1:
        return 1
    
    count = 0
    d = 2
    while d * d <= n:
        if n % d == 0:
            n //= d
            count += 1
            if n % d == 0:
                return 0  # squared prime factor
        else:
            d += 1
    
    if n > 1:
        count += 1
    
    return (-1) ** count


def count_coprime_pairs(n, m, mu):
    """
    Count pairs (i, j) with 1 ≤ i ≤ n, 1 ≤ j ≤ m, gcd(i, j) = 1.
    
    Σ_{d=1}^{min(n,m)} μ(d) * floor(n/d) * floor(m/d)
    
    Time: O(min(n, m))
    """
    ans = 0
    for d in range(1, min(n, m) + 1):
        ans += mu[d] * (n // d) * (m // d)
    return ans


def count_pairs_gcd_k(n, m, k, mu):
    """Count pairs with gcd(i, j) = k."""
    return count_coprime_pairs(n // k, m // k, mu)


def sum_of_gcd(n, m, mu):
    """
    Compute Σ_{i=1}^{n} Σ_{j=1}^{m} gcd(i, j).
    
    Time: O(min(n, m) * √(min(n, m)))
    """
    ans = 0
    for g in range(1, min(n, m) + 1):
        nn, mm = n // g, m // g
        cnt = 0
        for d in range(1, min(nn, mm) + 1):
            cnt += mu[d] * (nn // d) * (mm // d)
        ans += g * cnt
    return ans


def sum_of_gcd_fast(n, m, mu):
    """
    Compute Σ_{i=1}^{n} Σ_{j=1}^{m} gcd(i, j) using grouping.
    
    Time: O(√n * √n) = O(n) but with much better constants.
    """
    # Prefix sum of μ
    mu_prefix = [0] * (len(mu))
    for i in range(1, len(mu)):
        mu_prefix[i] = mu_prefix[i - 1] + mu[i]
    
    ans = 0
    lim = min(n, m)
    for g in range(1, lim + 1):
        nn, mm = n // g, m // g
        sub = 0
        l = 1
        while l <= min(nn, mm):
            r = min(nn // (nn // l), mm // (mm // l))
            sub += (mu_prefix[r] - mu_prefix[l - 1]) * (nn // l) * (mm // l)
            l = r + 1
        ans += g * sub
    return ans


def euler_totient_mobius(n):
    """Compute φ(n) using the formula φ(n) = n * Π_{p|n} (1 - 1/p)."""
    if n == 1:
        return 1
    result = n
    temp = n
    p = 2
    while p * p <= temp:
        if temp % p == 0:
            result = result // p * (p - 1)
            while temp % p == 0:
                temp //= p
        p += 1
    if temp > 1:
        result = result // temp * (temp - 1)
    return result
```

### 9.3 Java Implementation

```java
import java.util.*;

public class MobiusInversion {
    
    /**
     * Linear sieve for Möbius function.
     * Time: O(n), Space: O(n)
     */
    static int[] mobiusSieve(int n) {
        int[] mu = new int[n + 1];
        boolean[] isComposite = new boolean[n + 1];
        List<Integer> primes = new ArrayList<>();
        
        mu[1] = 1;
        for (int i = 2; i <= n; i++) {
            if (!isComposite[i]) {
                primes.add(i);
                mu[i] = -1;
            }
            for (int p : primes) {
                if ((long) i * p > n) break;
                isComposite[i * p] = true;
                if (i % p == 0) {
                    mu[i * p] = 0;
                    break;
                } else {
                    mu[i * p] = -mu[i];
                }
            }
        }
        return mu;
    }
    
    /**
     * Compute μ(n) for a single n. O(√n).
     */
    static int mobius(long n) {
        if (n == 1) return 1;
        int count = 0;
        for (long d = 2; d * d <= n; d++) {
            if (n % d == 0) {
                n /= d;
                count++;
                if (n % d == 0) return 0;
            }
        }
        if (n > 1) count++;
        return (count % 2 == 0) ? 1 : -1;
    }
    
    /**
     * Count coprime pairs (i, j) with 1 ≤ i ≤ n, 1 ≤ j ≤ m.
     */
    static long countCoprimePairs(int n, int m, int[] mu) {
        long ans = 0;
        for (int d = 1; d <= Math.min(n, m); d++)
            ans += (long) mu[d] * (n / d) * (m / d);
        return ans;
    }
    
    /**
     * Count pairs with gcd = k.
     */
    static long countPairsGcdK(int n, int m, int k, int[] mu) {
        return countCoprimePairs(n / k, m / k, mu);
    }
    
    /**
     * Sum of gcd(i, j) for 1 ≤ i ≤ n, 1 ≤ j ≤ m.
     */
    static long sumOfGcd(int n, int m, int[] mu) {
        long ans = 0;
        int lim = Math.min(n, m);
        for (int g = 1; g <= lim; g++) {
            int nn = n / g, mm = m / g;
            long cnt = 0;
            for (int d = 1; d <= Math.min(nn, mm); d++)
                cnt += (long) mu[d] * (nn / d) * (mm / d);
            ans += g * cnt;
        }
        return ans;
    }
    
    /**
     * Euler's totient via Möbius: φ(n) = n * Π_{p|n} (1 - 1/p).
     */
    static long eulerTotient(long n) {
        if (n == 1) return 1;
        long result = n;
        for (long p = 2; p * p <= n; p++) {
            if (n % p == 0) {
                result = result / p * (p - 1);
                while (n % p == 0) n /= p;
            }
        }
        if (n > 1) result = result / n * (n - 1);
        return result;
    }
    
    /**
     * Count numbers in [1, n] coprime to all primes in the set.
     * Inclusion-exclusion over 2^k subsets.
     */
    static long countCoprimeToPrimes(long n, int[] primes) {
        int k = primes.length;
        long ans = 0;
        for (int mask = 0; mask < (1 << k); mask++) {
            long prod = 1;
            int bits = 0;
            for (int i = 0; i < k; i++) {
                if ((mask & (1 << i)) != 0) {
                    prod *= primes[i];
                    bits++;
                }
            }
            if (bits % 2 == 0) ans += n / prod;
            else ans -= n / prod;
        }
        return ans;
    }
}
```

---

## 10. Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| Sieve μ(1..N) | O(N) | O(N) |
| Single μ(n) | O(√n) | O(1) |
| Coprime pairs (n, m) | O(min(n,m)) | O(N) sieve |
| Coprime pairs with grouping | O(√n) | O(N) sieve |
| Sum of gcd | O(min(n,m) · √min(n,m)) | O(N) sieve |
| Sum of gcd (fast) | O(√n · √n) | O(N) sieve |

### Optimization: Grouping by Floor Values

For sums of the form Σ_{d=1}^{n} f(d) · ⌊n/d⌋, we can group consecutive values of d with the same ⌊n/d⌋:

```
for (int l = 1, r; l <= n; l = r + 1) {
    r = n / (n / l);
    // All d in [l, r] have the same floor(n/d)
    ans += (prefix[r] - prefix[l-1]) * (n / l);
}
```

This reduces O(n) to O(√n) since there are at most 2√n distinct values of ⌊n/d⌋.

---

## 11. Advanced Applications

### 11.1 Counting with Multiple GCD Constraints

**Problem**: Count triples (a, b, c) with 1 ≤ a, b, c ≤ n and gcd(a, b, c) = 1.

\\[\text{count} = \sum_{d=1}^{n} \mu(d) \cdot \left\lfloor \frac{n}{d} \right\rfloor^3\\]

### 11.2 Inclusion-Exclusion on LCM

**Problem**: Count pairs (a, b) with 1 ≤ a ≤ n, 1 ≤ b ≤ n, lcm(a, b) = n.

Using lcm(a,b) = ab/gcd(a,b), this becomes:

\\[\sum_{\substack{d | n \\ d^2 | n}} \mu(n/d^2) \cdot \text{(some divisor function)}\\]

### 11.3 Dirichlet Series and Analytic Number Theory

The Möbius function has the Dirichlet series:

\\[\sum_{n=1}^{\infty} \frac{\mu(n)}{n^s} = \frac{1}{\zeta(s)}\\]

where ζ(s) is the Riemann zeta function. This connection is fundamental in analytic number theory.

### 11.4 Square-Free Counting

Count square-free numbers up to n:

\\[Q(n) = \sum_{d=1}^{\lfloor\sqrt{n}\rfloor} \mu(d) \cdot \left\lfloor \frac{n}{d^2} \right\rfloor\\]

---

## 12. Exercises

### Easy

1. **Compute μ**: Calculate μ(n) for n = 1, ..., 30.

2. **Coprime pairs**: How many pairs (i, j) with 1 ≤ i, j ≤ 10 have gcd(i, j) = 1?

3. **Verify identity**: Verify Σ_{d|n} μ(d) = 0 for n = 12.

4. **φ via μ**: Compute φ(12) using the formula φ(n) = Σ_{d|n} μ(d) · (n/d).

### Medium

5. **Codeforces Problem**: Given n, compute Σ_{i=1}^{n} Σ_{j=1}^{n} gcd(i, j) mod 10⁹+7.

6. **Counting with constraints**: Count pairs (a, b) with 1 ≤ a ≤ n, 1 ≤ b ≤ n, and gcd(a, b) is a perfect square.

7. **LCM sum**: Compute Σ_{i=1}^{n} Σ_{j=1}^{n} lcm(i, j) mod 10⁹+7.

8. **Dirichlet convolution**: Prove that if f is multiplicative, then Σ_{d|n} μ(d) · f(d) is also multiplicative.

### Hard

9. **Generalized Möbius**: Define μₖ(n) for k-th power free numbers. How does the sieve change?

10. **Mobius on intervals**: Compute Σ_{i=l}^{r} μ(i) for arbitrary intervals [l, r] up to 10¹².

11. **Prime counting**: Use the identity Σ_{d|n} μ(d) = [n=1] to derive a sieve for counting primes (Meissel-Lehmer method).

12. **Dirichlet inverse**: Given a multiplicative function f, compute its Dirichlet inverse f⁻¹ using μ and convolution.

---

## 13. Interview Questions

1. **Q**: What is the Möbius function and what are its key values?
   **A**: μ(1) = 1, μ(n) = (-1)^k if n is a product of k distinct primes, μ(n) = 0 if n has a squared prime factor.

2. **Q**: State the Möbius inversion formula.
   **A**: If g(n) = Σ_{d|n} f(d), then f(n) = Σ_{d|n} μ(d) · g(n/d).

3. **Q**: How do you count coprime pairs up to n?
   **A**: Σ_{d=1}^{n} μ(d) · ⌊n/d⌋². Can be optimized to O(√n) using floor division grouping.

4. **Q**: What is the relationship between Möbius function and Euler's totient?
   **A**: φ(n) = Σ_{d|n} μ(d) · (n/d), and also Σ_{d|n} φ(d) = n.

5. **Q**: How do you compute μ(n) for all n up to N?
   **A**: Use a linear sieve in O(N) time. For each prime p, μ(p) = -1. For each composite, use μ(i·p) = -μ(i) if p∤i, else μ(i·p) = 0.

---

## 14. Common Mistakes

1. **Forgetting μ(1) = 1**: The base case is often overlooked.

2. **Not handling the zero case**: μ(n) = 0 for non-square-free n. Many implementations forget to check for squared factors.

3. **Off-by-one in loops**: The sum Σ_{d|n} goes over all divisors, not just 1 to n.

4. **Integer overflow**: Products like μ(d) · ⌊n/d⌋ · ⌊m/d⌋ can overflow 32-bit integers. Use long long.

5. **Wrong direction**: g(n) = Σ_{d|n} f(d) means summing f over DIVISORS of n, not multiples.

6. **Modular arithmetic with μ**: μ can be -1, so remember to handle negative values when taking modular results.

---

## 15. Cross-References

- **Chapter 60: Number Theory** — Primes, factorization, Euler's totient
- **Chapter 71: Combinatorics** — Inclusion-exclusion principle
- **Chapter 163: Advanced Mathematics for Algorithms** — Dirichlet series and generating functions
- **Chapter 73: Linear Algebra for Programming** — Matrix representations of multiplicative functions
- **Chapter 151: Linear Programming** — LP relaxation of integer counting problems

---

## 16. Further Reading

- Apostol, T. M. (1976). *Introduction to Analytic Number Theory*. Springer.
- Hardy, G. H., & Wright, E. M. (2008). *An Introduction to the Theory of Numbers*. Oxford.
- cp-algorithms: [Möbius Function](https://cp-algorithms.com/algebra/mobius-function.html)
- Project Euler — Problems involving gcd and coprime counting
