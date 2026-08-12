# Chapter 176: Chinese Remainder Theorem

## 1. Definition

The **Chinese Remainder Theorem (CRT)** is a fundamental result in number theory that provides a way to solve systems of simultaneous congruences with pairwise coprime moduli. Given a system:

```
x ≡ a₁ (mod m₁)
x ≡ a₂ (mod m₂)
...
x ≡ aₖ (mod mₖ)
```

where m₁, m₂, ..., mₖ are pairwise coprime (gcd(mᵢ, mⱼ) = 1 for i ≠ j), CRT guarantees a **unique solution** modulo M = m₁ · m₂ · ... · mₖ.

## 2. Motivation

### The Core Problem

Suppose you know:
- A number leaves remainder 2 when divided by 3
- A number leaves remainder 3 when divided by 5
- A number leaves remainder 2 when divided by 7

What is the smallest such number? CRT tells us there is exactly one answer modulo 3 × 5 × 7 = 105, and gives us a constructive method to find it.

### Why Should Programmers Care?

1. **Large number arithmetic**: Represent a large number as remainders modulo several primes, perform operations on each component independently, then reconstruct.
2. **Competitive programming**: Many problems reduce to "count something modulo 10⁹ + 7" — but sometimes the modulus isn't prime, and CRT lets you split into prime-power moduli.
3. **Cryptography**: RSA and secret sharing schemes rely on CRT.
4. **Garner's algorithm**: Efficient mixed-radix reconstruction used in NTT-based polynomial multiplication with arbitrary moduli.

## 3. Intuition: The Remainder Clock

Think of each congruence as a "clock" with mᵢ positions. The value aᵢ tells you where the hand points on clock i. CRT says: if the clock sizes are coprime, the combination of hand positions uniquely identifies a time within the full cycle M = m₁ · m₂ · ... · mₖ.

**Why coprimality matters**: If two clocks share a factor, some combinations become impossible or ambiguous. For example, x ≡ 1 (mod 4) and x ≡ 3 (mod 6) — checking x = 1, 5, 9, 13... against mod 6: 1→1, 5→5, 9→3 ✓. But if we had x ≡ 1 (mod 4) and x ≡ 2 (mod 6), there's no solution because gcd(4,6) = 2 and 1 ≢ 2 (mod 2).

## 4. Formal Statement

### 4.1 Existence and Uniqueness

**Theorem**: Let m₁, m₂, ..., mₖ be pairwise coprime positive integers, and let a₁, a₂, ..., aₖ be arbitrary integers. Then the system of congruences

```
x ≡ aᵢ (mod mᵢ)   for i = 1, 2, ..., k
```

has a unique solution modulo M = m₁ · m₂ · ... · mₖ.

### 4.2 Constructive Proof

Let Mᵢ = M / mᵢ. Since gcd(Mᵢ, mᵢ) = 1 (because all mⱼ for j ≠ i are coprime to mᵢ), there exists an inverse tᵢ such that:

```
Mᵢ · tᵢ ≡ 1 (mod mᵢ)
```

Then the solution is:

```
x = Σᵢ aᵢ · Mᵢ · tᵢ  (mod M)
```

**Verification**: For any j, when we compute x mod mⱼ:
- For i ≠ j: Mᵢ contains mⱼ as a factor, so aᵢ · Mᵢ · tᵢ ≡ 0 (mod mⱼ)
- For i = j: aⱼ · Mⱼ · tⱼ ≡ aⱼ · 1 ≡ aⱼ (mod mⱼ)

Therefore x ≡ aⱼ (mod mⱼ) for all j. ✓

## 5. Step-by-Step Walkthrough

### Example: Solve the system

```
x ≡ 2 (mod 3)
x ≡ 3 (mod 5)
x ≡ 2 (mod 7)
```

**Step 1**: Compute M = 3 × 5 × 7 = 105

**Step 2**: Compute Mᵢ for each equation:
- M₁ = 105 / 3 = 35
- M₂ = 105 / 5 = 21
- M₃ = 105 / 7 = 15

**Step 3**: Find modular inverses tᵢ:
- t₁: 35 · t₁ ≡ 1 (mod 3) → 35 mod 3 = 2, so 2 · t₁ ≡ 1 (mod 3) → t₁ = 2 (since 2·2 = 4 ≡ 1)
- t₂: 21 · t₂ ≡ 1 (mod 5) → 21 mod 5 = 1, so 1 · t₂ ≡ 1 (mod 5) → t₂ = 1
- t₃: 15 · t₃ ≡ 1 (mod 7) → 15 mod 7 = 1, so 1 · t₃ ≡ 1 (mod 7) → t₃ = 1

**Step 4**: Compute x:
```
x = 2 · 35 · 2 + 3 · 21 · 1 + 2 · 15 · 1
x = 140 + 63 + 30 = 233
x = 233 mod 105 = 23
```

**Step 5**: Verify:
- 23 mod 3 = 2 ✓
- 23 mod 5 = 3 ✓
- 23 mod 7 = 2 ✓

### Dry Run Table

| i | aᵢ | mᵢ | Mᵢ | Mᵢ mod mᵢ | tᵢ (inverse) | aᵢ · Mᵢ · tᵢ |
|---|----|----|----|-----------|-------------|---------------|
| 1 | 2  | 3  | 35 | 2         | 2           | 140           |
| 2 | 3  | 5  | 21 | 1         | 1           | 63            |
| 3 | 2  | 7  | 15 | 1         | 1           | 30            |

Sum = 233, mod 105 = **23**

## 6. Garner's Algorithm

While the standard CRT formula works, **Garner's algorithm** computes the mixed-radix representation, which is often more efficient and avoids potential overflow issues with large moduli.

### Idea

Represent x in mixed-radix form:

```
x = v₁ + v₂·m₁ + v₃·m₁·m₂ + v₄·m₁·m₂·m₃ + ...
```

where 0 ≤ vᵢ < mᵢ. This is essentially a variable-base number system.

### Algorithm

For each i from 1 to k:
```
vᵢ = (aᵢ - v₁ - v₂·m₁ - ... - vᵢ₋₁·m₁·...·mᵢ₋₂) · (m₁·m₂·...·mᵢ₋₁)⁻¹  (mod mᵢ)
```

We precompute all pairwise inverses cᵢⱼ = mⱼ⁻¹ (mod mᵢ) for j < i.

### Garner's Algorithm Walkthrough

Same example: x ≡ 2 (mod 3), x ≡ 3 (mod 5), x ≡ 2 (mod 7)

**Precompute inverses:**
- c₂₁ = m₁⁻¹ (mod m₂) = 3⁻¹ (mod 5) = 2 (since 3·2 = 6 ≡ 1 mod 5)
- c₃₁ = m₁⁻¹ (mod m₃) = 3⁻¹ (mod 7) = 5 (since 3·5 = 15 ≡ 1 mod 7)
- c₃₂ = m₂⁻¹ (mod m₃) = 5⁻¹ (mod 7) = 3 (since 5·3 = 15 ≡ 1 mod 7)

**Compute coefficients:**
- v₁ = a₁ mod m₁ = 2 mod 3 = 2
- v₂ = (a₂ - v₁) · c₂₁ mod m₂ = (3 - 2) · 2 mod 5 = 2
- v₃ = ((a₃ - v₁) · c₃₁ - v₂) · c₃₂ mod m₃ = ((2 - 2) · 5 - 2) · 3 mod 7 = (-2) · 3 mod 7 = -6 mod 7 = 1

**Reconstruct:**
x = v₁ + v₂·3 + v₃·3·5 = 2 + 6 + 15 = 23 ✓

## 7. Code Implementations

### 7.1 C++ — Standard CRT

```cpp
#include <bits/stdc++.h>
using namespace std;

// Extended GCD: returns gcd(a, b) and finds x, y such that ax + by = gcd(a,b)
long long ext_gcd(long long a, long long b, long long &x, long long &y) {
    if (b == 0) {
        x = 1; y = 0;
        return a;
    }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

// Modular inverse of a mod m (assumes gcd(a,m) = 1)
long long mod_inv(long long a, long long m) {
    long long x, y;
    ext_gcd(a, m, x, y);
    return (x % m + m) % m;
}

// Chinese Remainder Theorem
// Returns {x, M} where x is the solution mod M
// a[] = remainders, m[] = moduli, n = number of equations
pair<long long, long long> crt(long long a[], long long m[], int n) {
    long long M = 1;
    for (int i = 0; i < n; i++) M *= m[i];

    long long x = 0;
    for (int i = 0; i < n; i++) {
        long long Mi = M / m[i];
        long long ti = mod_inv(Mi % m[i], m[i]);
        x = (x + a[i] * Mi % M * ti % M) % M;
    }
    return {(x + M) % M, M};
}

int main() {
    long long a[] = {2, 3, 2};
    long long m[] = {3, 5, 7};
    auto [x, M] = crt(a, m, 3);
    cout << "x = " << x << " (mod " << M << ")" << endl;
    // Output: x = 23 (mod 105)
    return 0;
}
```

### 7.2 C++ — Garner's Algorithm

```cpp
#include <bits/stdc++.h>
using namespace std;

long long mod_inv(long long a, long long m) {
    long long x, y;
    // Extended GCD
    function<long long(long long, long long, long long&, long long&)> ext_gcd =
        [&](long long a, long long b, long long &x, long long &y) -> long long {
        if (b == 0) { x = 1; y = 0; return a; }
        long long x1, y1;
        long long g = ext_gcd(b, a % b, x1, y1);
        x = y1; y = x1 - (a / b) * y1;
        return g;
    };
    ext_gcd(a, m, x, y);
    return (x % m + m) % m;
}

// Garner's algorithm: returns x mod M
// a[] = remainders, m[] = moduli (pairwise coprime), n = count
long long garner(long long a[], long long m[], int n) {
    // Precompute inverses c[i][j] = m[j]^-1 mod m[i] for j < i
    vector<vector<long long>> c(n, vector<long long>(n, 0));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < i; j++)
            c[i][j] = mod_inv(m[j] % m[i], m[i]);

    vector<long long> v(n);
    for (int i = 0; i < n; i++) {
        v[i] = a[i];
        for (int j = 0; j < i; j++) {
            v[i] = (v[i] - v[j]) * c[i][j] % m[i];
            if (v[i] < 0) v[i] += m[i];
        }
    }

    // Reconstruct x from mixed-radix form
    long long x = 0, mult = 1;
    for (int i = 0; i < n; i++) {
        x = (x + v[i] * mult) % (mult * m[i]);
        mult *= m[i];
    }
    return x;
}

int main() {
    long long a[] = {2, 3, 2};
    long long m[] = {3, 5, 7};
    cout << "x = " << garner(a, m, 3) << endl;
    // Output: x = 23
    return 0;
}
```

### 7.3 C++ — CRT with Non-Coprime Moduli (Generalized CRT)

```cpp
#include <bits/stdc++.h>
using namespace std;

// Extended GCD
long long ext_gcd(long long a, long long b, long long &x, long long &y) {
    if (b == 0) { x = 1; y = 0; return a; }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1; y = x1 - (a / b) * y1;
    return g;
}

// Generalized CRT: works even when moduli are NOT coprime
// Returns {x, lcm} or {-1, -1} if no solution
pair<long long, long long> generalized_crt(vector<long long> a, vector<long long> m) {
    long long x = a[0], lcm = m[0];
    for (size_t i = 1; i < m.size(); i++) {
        // Solve: x + lcm * t ≡ a[i] (mod m[i])
        // => lcm * t ≡ (a[i] - x) (mod m[i])
        long long diff = (a[i] - x) % m[i];
        if (diff < 0) diff += m[i];

        long long g, s, t_dummy;
        g = ext_gcd(lcm, m[i], s, t_dummy);

        if (diff % g != 0) return {-1, -1}; // No solution

        // t = diff/g * s mod (m[i]/g)
        long long mod_new = m[i] / g;
        long long t_val = ((diff / g) % mod_new * (s % mod_new + mod_new) % mod_new) % mod_new;

        x = x + lcm * t_val;
        lcm = lcm / g * m[i]; // lcm = lcm(lcm, m[i])
        x = ((x % lcm) + lcm) % lcm;
    }
    return {x, lcm};
}

int main() {
    // Example with non-coprime moduli
    vector<long long> a = {2, 3, 8};
    vector<long long> m = {3, 6, 11};
    auto [x, lcm] = generalized_crt(a, m);
    if (x == -1) cout << "No solution" << endl;
    else cout << "x = " << x << " (mod " << lcm << ")" << endl;
    return 0;
}
```

### 7.4 Python — Standard CRT

```python
from math import gcd

def ext_gcd(a, b):
    """Extended GCD: returns (g, x, y) such that a*x + b*y = g = gcd(a,b)"""
    if b == 0:
        return a, 1, 0
    g, x1, y1 = ext_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

def mod_inv(a, m):
    """Modular inverse of a mod m"""
    g, x, _ = ext_gcd(a % m, m)
    if g != 1:
        raise ValueError(f"No inverse: gcd({a}, {m}) = {g}")
    return x % m

def crt(remainders, moduli):
    """
    Chinese Remainder Theorem
    Returns (x, M) where x is the unique solution mod M
    remainders and moduli are lists of equal length
    moduli must be pairwise coprime
    """
    assert len(remainders) == len(moduli)
    n = len(remainders)

    M = 1
    for m in moduli:
        M *= m

    x = 0
    for i in range(n):
        Mi = M // moduli[i]
        ti = mod_inv(Mi % moduli[i], moduli[i])
        x = (x + remainders[i] * Mi * ti) % M

    return x, M


def garner(remainders, moduli):
    """
    Garner's algorithm for CRT
    Returns the solution x
    """
    n = len(remainders)
    # Precompute inverses
    c = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i):
            c[i][j] = mod_inv(moduli[j] % moduli[i], moduli[i])

    v = [0] * n
    for i in range(n):
        v[i] = remainders[i]
        for j in range(i):
            v[i] = (v[i] - v[j]) * c[i][j] % moduli[i]

    # Reconstruct
    x, mult = 0, 1
    for i in range(n):
        x = (x + v[i] * mult) % (mult * moduli[i])
        mult *= moduli[i]
    return x


def generalized_crt(remainders, moduli):
    """
    Generalized CRT: works with non-coprime moduli
    Returns (x, lcm) or (None, None) if no solution
    """
    x, lcm = remainders[0], moduli[0]
    for i in range(1, len(moduli)):
        diff = (remainders[i] - x) % moduli[i]
        g, s, _ = ext_gcd(lcm, moduli[i])

        if diff % g != 0:
            return None, None

        mod_new = moduli[i] // g
        t_val = ((diff // g) * (s % mod_new)) % mod_new

        x = x + lcm * t_val
        lcm = lcm // g * moduli[i]
        x %= lcm
    return x, lcm


# === Demo ===
if __name__ == "__main__":
    # Standard CRT
    x, M = crt([2, 3, 2], [3, 5, 7])
    print(f"CRT: x = {x} (mod {M})")  # x = 23 (mod 105)

    # Garner's
    x = garner([2, 3, 2], [3, 5, 7])
    print(f"Garner: x = {x}")  # x = 23

    # Generalized CRT (non-coprime)
    x, lcm = generalized_crt([2, 3, 8], [3, 6, 11])
    print(f"Generalized CRT: x = {x} (mod {lcm})")

    # Application: large number represented as remainders
    # Represent 10^18 as (10^18 mod p1, 10^18 mod p2, 10^18 mod p3)
    big = 10**18
    primes = [998244353, 1000000007, 1000000009]
    rems = [big % p for p in primes]
    result, _ = crt(rems, primes)
    print(f"Reconstruct {big}: got {result}")  # Should be 10^18
```

### 7.5 Python — Application: Counting with Non-Prime Modulus

```python
def crt_counting(modulus, factors):
    """
    When modulus is not prime, split computation into prime powers,
    solve each independently, then combine with CRT.
    
    Example: compute C(n, k) mod m where m = p1^e1 * p2^e2 * ...
    """
    # Placeholder: the actual computation would be done mod each factor
    # then combined via CRT
    pass

def count_with_crt(n, k, mod):
    """
    Compute C(n, k) mod mod using CRT if mod is composite.
    For prime mod, just use Lucas theorem or direct computation.
    """
    from math import isqrt

    def factorize(m):
        factors = []
        d = 2
        while d * d <= m:
            if m % d == 0:
                e = 0
                while m % d == 0:
                    m //= d
                    e += 1
                factors.append((d, e))
            d += 1
        if m > 1:
            factors.append((m, 1))
        return factors

    def binom_prime_power(n, k, p, e):
        """Compute C(n, k) mod p^e using Lucas + lifting"""
        pe = p ** e
        # For e=1, use Lucas theorem
        if e == 1:
            return binom_mod_prime(n, k, p)
        # For higher powers, use Granville's extension or direct computation
        # Simplified: direct computation for small n
        if n < 10000:
            result = 1
            for i in range(k):
                result = result * (n - i) % pe
                result = result * mod_inv(i + 1, pe) % pe
            return result
        return binom_mod_prime(n, k, p)  # fallback

    def binom_mod_prime(n, k, p):
        """C(n, k) mod p using Lucas theorem"""
        if k < 0 or k > n:
            return 0
        result = 1
        while n > 0 or k > 0:
            ni = n % p
            ki = k % p
            if ki > ni:
                return 0
            # C(ni, ki) mod p — small enough to compute directly
            c = 1
            for j in range(ki):
                c = c * (ni - j) % p
                c = c * mod_inv(j + 1, p) % p
            result = result * c % p
            n //= p
            k //= p
        return result

    factors = factorize(mod)
    remainders = []
    moduli = []
    for p, e in factors:
        pe = p ** e
        remainders.append(binom_prime_power(n, k, p, e))
        moduli.append(pe)

    result, _ = crt(remainders, moduli)
    return result
```

### 7.6 Java — Standard CRT

```java
public class ChineseRemainderTheorem {

    // Extended GCD: returns gcd(a, b), sets x, y such that ax + by = gcd
    static long[] extGcd(long a, long b) {
        if (b == 0) return new long[]{a, 1, 0};
        long[] r = extGcd(b, a % b);
        long g = r[0], x1 = r[1], y1 = r[2];
        return new long[]{g, y1, x1 - (a / b) * y1};
    }

    static long modInv(long a, long m) {
        long[] r = extGcd(a % m, m);
        return ((r[1] % m) + m) % m;
    }

    // Standard CRT: returns {solution, modulus}
    static long[] crt(long[] remainders, long[] moduli) {
        int n = remainders.length;
        long M = 1;
        for (long m : moduli) M *= m;

        long x = 0;
        for (int i = 0; i < n; i++) {
            long Mi = M / moduli[i];
            long ti = modInv(Mi % moduli[i], moduli[i]);
            x = (x + remainders[i] * Mi % M * ti % M) % M;
        }
        return new long[]{(x + M) % M, M};
    }

    // Garner's algorithm
    static long garner(long[] remainders, long[] moduli) {
        int n = remainders.length;
        long[][] c = new long[n][n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < i; j++)
                c[i][j] = modInv(moduli[j] % moduli[i], moduli[i]);

        long[] v = new long[n];
        for (int i = 0; i < n; i++) {
            v[i] = remainders[i];
            for (int j = 0; j < i; j++) {
                v[i] = ((v[i] - v[j]) * c[i][j]) % moduli[i];
                if (v[i] < 0) v[i] += moduli[i];
            }
        }

        long x = 0, mult = 1;
        for (int i = 0; i < n; i++) {
            x = (x + v[i] * mult) % (mult * moduli[i]);
            mult *= moduli[i];
        }
        return x;
    }

    public static void main(String[] args) {
        long[] a = {2, 3, 2};
        long[] m = {3, 5, 7};

        long[] result = crt(a, m);
        System.out.println("CRT: x = " + result[0] + " (mod " + result[1] + ")");

        long g = garner(a, m);
        System.out.println("Garner: x = " + g);
    }
}
```

## 8. Complexity Analysis

| Algorithm | Time Complexity | Space Complexity | Notes |
|-----------|----------------|-----------------|-------|
| Standard CRT | O(k · log(max(mᵢ))) | O(k) | k = number of congruences |
| Garner's Algorithm | O(k² · log(max(mᵢ))) | O(k²) | Precomputes pairwise inverses |
| Generalized CRT | O(k · log(max(mᵢ))) | O(1) | Incrementally merges equations |

Where the log factor comes from the extended GCD computation.

**Overflow warning**: In standard CRT, the product M = m₁ · m₂ · ... · mₖ can overflow 64-bit integers for large inputs. Garner's algorithm avoids this by working modulo each mᵢ individually.

## 9. Applications

### 9.1 Large Number Arithmetic

Represent a number N as a tuple (N mod p₁, N mod p₂, ..., N mod pₖ) where pᵢ are distinct primes. Addition and multiplication work component-wise:

```
(a₁, a₂, ..., aₖ) + (b₁, b₂, ..., bₖ) = ((a₁+b₁) mod p₁, ..., (aₖ+bₖ) mod pₖ)
```

Reconstruct the actual result with CRT when needed. This is the foundation of **Schönhage–Strassen** and **Harvey–van der Hoeven** multiplication algorithms.

### 9.2 NTT with Arbitrary Modulus

NTT requires the modulus to be of the form c · 2ᵏ + 1. For arbitrary moduli (e.g., 10⁹ + 7):

1. Choose NTT-friendly primes p₁, p₂, p₃ (e.g., 998244353, 1004535809, 469762049)
2. Perform NTT mod each pᵢ independently
3. Combine results using CRT

### 9.3 Competitive Programming: Counting with Composite Modulus

When asked to compute combinatorial quantities mod M where M is composite:

1. Factor M = p₁^e₁ · p₂^e₂ · ... · pₖ^eₖ
2. Compute the answer mod each pᵢ^eᵢ using appropriate techniques
3. Combine with CRT

### 9.4 Secret Sharing (Asmuth-Bloom Scheme)

CRT-based threshold secret sharing:
- Choose coprime moduli m₁ < m₂ < ... < mₙ
- Encode secret S as x = S + r · m₀ where m₀ < m₁ and r is random
- Share i gets x mod mᵢ
- Any k shares can reconstruct x via CRT, then recover S = x mod m₀

## 10. Common Pitfalls and Edge Cases

1. **Non-coprime moduli**: Standard CRT requires pairwise coprimality. Use generalized CRT otherwise.
2. **Overflow**: M = ∏ mᵢ can overflow. Use Garner's algorithm or work with __int128 / big integers.
3. **Negative remainders**: Ensure all remainders are in [0, mᵢ) before applying CRT.
4. **Single congruence**: Trivially returns a₁ mod m₁ — handle this edge case.
5. **Empty system**: Convention is x = 0 mod 1 (identity element).

## 11. Exercises

### Warm-Up
1. Solve: x ≡ 1 (mod 4), x ≡ 2 (mod 5), x ≡ 3 (mod 7). Verify your answer.
2. Solve: x ≡ 0 (mod 2), x ≡ 0 (mod 3), x ≡ 1 (mod 5). What is the smallest positive x?

### Standard
3. Given n congruences with pairwise coprime moduli, implement an O(n log²(max mᵢ)) solution using Garner's algorithm.
4. Prove that if m₁, ..., mₖ are pairwise coprime, then the map x ↦ (x mod m₁, ..., x mod mₖ) is a bijection from Z/MZ to Z/m₁Z × ... × Z/mₖZ.
5. Use CRT to compute C(10⁶, 5×10⁵) mod 1000000007 · 998244353. (Hint: compute mod each prime separately.)

### Challenge
6. **[POI 2006]** A sequence a₁, ..., aₙ satisfies a system of congruences aᵢ ≡ rᵢ (mod mᵢ). Find the number of valid sequences modulo some prime.
7. Implement polynomial interpolation using CRT: given polynomial evaluations at k points, reconstruct the polynomial coefficients mod M.
8. Design a CRT-based hash function for strings that avoids collisions with high probability using multiple prime moduli.

## 12. Interview Questions

1. **Q**: What is CRT and when would you use it in programming?
   **A**: CRT solves systems of congruences with coprime moduli. In programming, it's used for large number arithmetic (splitting into prime moduli), NTT with arbitrary moduli, and counting with composite moduli.

2. **Q**: What happens if the moduli are not coprime?
   **A**: A solution exists if and only if aᵢ ≡ aⱼ (mod gcd(mᵢ, mⱼ)) for all pairs. The generalized CRT handles this by incrementally merging equations.

3. **Q**: Compare standard CRT with Garner's algorithm.
   **A**: Standard CRT is O(k log m) but risks overflow from M = ∏mᵢ. Garner's is O(k² log m) but works modulo each mᵢ individually, avoiding overflow. Garner's is preferred for competitive programming.

4. **Q**: How would you compute C(n,k) mod M where M is not prime?
   **A**: Factor M into prime powers, compute C(n,k) mod each prime power (using Lucas theorem for primes, Granville's extension for prime powers), then combine with CRT.

## 13. Cross-References

- **Chapter 60: Number Theory** — GCD, modular arithmetic, modular inverse foundations
- **Chapter 167: FFT and NTT** — NTT with arbitrary modulus via CRT
- **Chapter 177: Lucas Theorem** — Computing binomial coefficients mod primes
- **Chapter 71: Combinatorics** — Counting problems requiring modular arithmetic
- **Appendix G: Mathematics Handbook** — Modular arithmetic reference
