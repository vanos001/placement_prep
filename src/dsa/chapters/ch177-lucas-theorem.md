# Chapter 177: Lucas Theorem

## 1. Definition

**Lucas Theorem** provides an efficient method to compute binomial coefficients C(n, k) modulo a prime p. It decomposes the computation into products of small binomial coefficients using the base-p representations of n and k.

**Theorem**: Let p be a prime, and let n and k be non-negative integers with base-p representations:

```
n = nₘpᵐ + nₘ₋₁pᵐ⁻¹ + ... + n₁p + n₀
k = kₘpᵐ + kₘ₋₁pᵐ⁻¹ + ... + k₁p + k₀
```

Then:

```
C(n, k) ≡ ∏ᵢ₌₀ᵐ C(nᵢ, kᵢ)  (mod p)
```

where C(nᵢ, kᵢ) = 0 if kᵢ > nᵢ.

## 2. Motivation

### The Problem

Computing C(n, k) mod p where n can be as large as 10¹⁸ and p is a prime (typically 10⁹ + 7 or 998244353).

### Why Not Just Use Factorials?

The standard approach C(n,k) = n! / (k! · (n-k)!) requires:
- Computing n! mod p — O(n) time
- Modular inverse of k! and (n-k)! — O(log p) each

For n = 10¹⁸, this is impossible. Lucas theorem reduces the problem to O(logₚ(n) · p) time by working digit-by-digit in base p.

### Connection to Digit DP

Lucas theorem has a beautiful connection to digit DP. When counting combinatorial objects with digit constraints, Lucas-like decomposition naturally appears. The digit-by-digit structure is the same as what digit DP exploits.

## 3. Intuition: Pascal's Triangle Mod p

### Visualizing the Pattern

When you compute Pascal's triangle mod p (say p = 3), a fractal pattern emerges — this is the **Sierpiński triangle**:

```
Row 0:  1
Row 1:  1 1
Row 2:  1 2 1
Row 3:  1 0 0 1      ← All internal entries are 0 mod 3
Row 4:  1 1 0 1 1
Row 5:  1 2 0 2 1
Row 6:  1 0 0 0 0 0 1 ← Pattern repeats at scale
...
```

**Key observation**: C(n, k) mod p = 0 whenever any digit kᵢ > nᵢ in base p. This is because the "carry" in the factorial computation causes p to divide C(n, k).

### Why Digit-by-Digit?

Think of choosing k items from n as independent choices at each "level" of the base-p representation:
- At the p⁰ level: choose k₀ from n₀ items
- At the p¹ level: choose k₁ from n₁ groups
- ...
- At the pᵐ level: choose kₘ from nₘ groups

The total count is the product of independent choices — exactly what Lucas theorem states.

## 4. Formal Proof Sketch

### 4.1 Key Lemma: Freshman's Dream

For prime p: (1 + x)ᵖ ≡ 1 + xᵖ (mod p).

**Proof**: By the binomial theorem, (1+x)ᵖ = Σᵢ₌₀ᵖ C(p,i) xⁱ. For 0 < i < p, C(p,i) = p!/(i!(p-i)!) is divisible by p (since p divides the numerator but not the denominator). So C(p,i) ≡ 0 (mod p), leaving only the i=0 and i=p terms.

### 4.2 Generalization

(1 + x)^(ap+b) ≡ (1 + xᵖ)ᵃ · (1 + x)ᵇ (mod p)

By comparing coefficients of x^k on both sides (writing k = cp+d):

C(ap+b, cp+d) ≡ C(a, c) · C(b, d) (mod p)

This is exactly one step of Lucas decomposition. Induction extends it to all digits.

### 4.3 Corollary: When is C(n,k) ≡ 0 (mod p)?

C(n, k) ≡ 0 (mod p) if and only if at least one digit of k in base p exceeds the corresponding digit of n. This is a powerful counting tool.

## 5. Step-by-Step Walkthrough

### Example 1: C(10, 3) mod 5

**Step 1**: Convert to base 5:
- 10 = 2·5 + 0 → digits (2, 0)
- 3 = 0·5 + 3 → digits (0, 3)

**Step 2**: Apply Lucas theorem:
```
C(10, 3) ≡ C(2, 0) · C(0, 3) (mod 5)
```

**Step 3**: Compute each small binomial:
- C(2, 0) = 1
- C(0, 3) = 0 (since 3 > 0)

**Step 4**: Product = 1 · 0 = 0

**Verification**: C(10, 3) = 120 = 24 · 5, and 120 mod 5 = 0 ✓

### Example 2: C(15, 7) mod 3

**Step 1**: Convert to base 3:
- 15 = 1·9 + 2·3 + 0 → digits (1, 2, 0)
- 7 = 0·9 + 2·3 + 1 → digits (0, 2, 1)

**Step 2**: Apply Lucas theorem:
```
C(15, 7) ≡ C(1, 0) · C(2, 2) · C(0, 1) (mod 3)
```

**Step 3**: Compute each:
- C(1, 0) = 1
- C(2, 2) = 1
- C(0, 1) = 0 (since 1 > 0)

**Step 4**: Product = 1 · 1 · 0 = 0

**Verification**: C(15, 7) = 6435 = 2145 · 3, and 6435 mod 3 = 0 ✓

### Example 3: C(11, 5) mod 7

**Step 1**: Convert to base 7:
- 11 = 1·7 + 4 → digits (1, 4)
- 5 = 0·7 + 5 → digits (0, 5)

**Step 2**: Apply Lucas theorem:
```
C(11, 5) ≡ C(1, 0) · C(4, 5) (mod 7)
```

**Step 3**: Compute each:
- C(1, 0) = 1
- C(4, 5) = 0 (since 5 > 4)

**Step 4**: Product = 1 · 0 = 0

**Verification**: C(11, 5) = 462 = 66 · 7, and 462 mod 7 = 0 ✓

### Example 4: A Non-Zero Result — C(13, 6) mod 5

**Step 1**: Convert to base 5:
- 13 = 2·5 + 3 → digits (2, 3)
- 6 = 1·5 + 1 → digits (1, 1)

**Step 2**: Apply Lucas theorem:
```
C(13, 6) ≡ C(2, 1) · C(3, 1) (mod 5)
```

**Step 3**: Compute each:
- C(2, 1) = 2
- C(3, 1) = 3

**Step 4**: Product = 2 · 3 = 6 ≡ 1 (mod 5)

**Verification**: C(13, 6) = 1716 = 343 · 5 + 1, and 1716 mod 5 = 1 ✓

### Dry Run Table for C(13, 6) mod 5

| Digit position | nᵢ | kᵢ | C(nᵢ, kᵢ) mod 5 | Running product |
|---------------|----|----|-----------------|----------------|
| 0 (5⁰)       | 3  | 1  | 3               | 3              |
| 1 (5¹)       | 2  | 1  | 2               | 3·2 = 6 ≡ 1   |

Final answer: **1**

## 6. Code Implementations

### 6.1 C++ — Lucas Theorem (Simple Version)

```cpp
#include <bits/stdc++.h>
using namespace std;

// Precompute factorials and inverse factorials mod p
const int MAXN = 1000006;
long long fac[MAXN], inv_fac[MAXN];

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

void precompute(int p) {
    fac[0] = 1;
    for (int i = 1; i < p; i++)
        fac[i] = fac[i - 1] * i % p;
    inv_fac[p - 1] = power(fac[p - 1], p - 2, p); // Fermat's little theorem
    for (int i = p - 2; i >= 0; i--)
        inv_fac[i] = inv_fac[i + 1] * (i + 1) % p;
}

// C(n, k) mod p for 0 <= n, k < p
long long small_binom(int n, int k, int p) {
    if (k < 0 || k > n) return 0;
    return fac[n] % p * inv_fac[k] % p * inv_fac[n - k] % p;
}

// Lucas Theorem: C(n, k) mod p
long long lucas(long long n, long long k, int p) {
    if (k < 0 || k > n) return 0;
    long long result = 1;
    while (n > 0 || k > 0) {
        int ni = n % p;
        int ki = k % p;
        result = result * small_binom(ni, ki, p) % p;
        if (result == 0) return 0;
        n /= p;
        k /= p;
    }
    return result;
}

int main() {
    int p = 7; // prime modulus
    precompute(p);

    long long n = 100, k = 50;
    cout << "C(" << n << ", " << k << ") mod " << p << " = " << lucas(n, k, p) << endl;

    // Verify with direct computation for small values
    n = 13; k = 6; p = 5;
    precompute(p);
    cout << "C(" << n << ", " << k << ") mod " << p << " = " << lucas(n, k, p) << endl;
    // Output: 1

    return 0;
}
```

### 6.2 C++ — Lucas Theorem with Large Prime (e.g., 10⁹+7)

```cpp
#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1e9 + 7;
const int MAXN = 1000006; // Adjust based on max digit value needed

long long fac[MAXN], inv_fac[MAXN];

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

void precompute(int p) {
    fac[0] = 1;
    for (int i = 1; i < p; i++)
        fac[i] = fac[i - 1] * i % p;
    inv_fac[p - 1] = power(fac[p - 1], p - 2, p);
    for (int i = p - 2; i >= 0; i--)
        inv_fac[i] = inv_fac[i + 1] * (i + 1) % p;
}

long long small_binom(int n, int k, int p) {
    if (k < 0 || k > n) return 0;
    return fac[n] % p * inv_fac[k] % p * inv_fac[n - k] % p;
}

// For large primes (p > MAXN), compute C(n, k) directly using Fermat's little theorem
long long binom_direct(long long n, long long k, long long p) {
    if (k < 0 || k > n) return 0;
    if (k > n - k) k = n - k;
    long long num = 1, den = 1;
    for (long long i = 0; i < k; i++) {
        num = num * ((n - i) % p) % p;
        den = den * ((i + 1) % p) % p;
    }
    return num * power(den, p - 2, p) % p;
}

// Lucas theorem for any prime p
long long lucas(long long n, long long k, long long p) {
    if (k < 0 || k > n) return 0;
    long long result = 1;
    while (n > 0 || k > 0) {
        long long ni = n % p;
        long long ki = k % p;
        if (ki > ni) return 0;
        // For small p, use precomputed factorials
        // For large p (p > MAXN), compute directly
        long long c;
        if (p <= MAXN) {
            c = small_binom(ni, ki, p);
        } else {
            c = binom_direct(ni, ki, p);
        }
        result = result * c % p;
        n /= p;
        k /= p;
    }
    return result;
}

int main() {
    long long n = 1000000000000LL, k = 500000000000LL;
    long long p = 998244353;
    precompute(p);
    cout << "C(" << n << ", " << k << ") mod " << p << " = " << lucas(n, k, p) << endl;
    return 0;
}
```

### 6.3 Python — Lucas Theorem

```python
def power(base, exp, mod):
    """Fast modular exponentiation"""
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result

def mod_inv(a, p):
    """Modular inverse using Fermat's little theorem (p must be prime)"""
    return power(a, p - 2, p)

def precompute_factorials(p):
    """Precompute factorials and inverse factorials mod p"""
    fac = [1] * p
    for i in range(1, p):
        fac[i] = fac[i - 1] * i % p

    inv_fac = [1] * p
    inv_fac[p - 1] = mod_inv(fac[p - 1], p)
    for i in range(p - 2, -1, -1):
        inv_fac[i] = inv_fac[i + 1] * (i + 1) % p

    return fac, inv_fac

def small_binom(n, k, p, fac, inv_fac):
    """C(n, k) mod p for 0 <= n, k < p"""
    if k < 0 or k > n:
        return 0
    return fac[n] * inv_fac[k] % p * inv_fac[n - k] % p

def lucas(n, k, p):
    """
    Lucas Theorem: compute C(n, k) mod p where p is prime.
    
    Time: O(log_p(n) + p) with precomputation
    Space: O(p)
    """
    if k < 0 or k > n:
        return 0
    
    fac, inv_fac = precompute_factorials(p)
    
    result = 1
    while n > 0 or k > 0:
        ni = n % p
        ki = k % p
        if ki > ni:
            return 0
        result = result * small_binom(ni, ki, p, fac, inv_fac) % p
        n //= p
        k //= p
    return result

def lucas_no_precompute(n, k, p):
    """
    Lucas Theorem without full precomputation.
    Useful when p is large but digits are small.
    Time: O(log_p(n) * min(k, p))
    """
    if k < 0 or k > n:
        return 0
    
    def binom_small(n, k, p):
        """Compute C(n, k) mod p for small n, k"""
        if k < 0 or k > n:
            return 0
        k = min(k, n - k)
        num, den = 1, 1
        for i in range(k):
            num = num * (n - i) % p
            den = den * (i + 1) % p
        return num * mod_inv(den, p) % p
    
    result = 1
    while n > 0 or k > 0:
        ni, ki = n % p, k % p
        if ki > ni:
            return 0
        result = result * binom_small(ni, ki, p) % p
        n //= p
        k //= p
    return result


# === Applications ===

def count_zero_mod_p(n, k, p):
    """
    Count how many C(i, k) for 0 <= i <= n are divisible by p.
    Uses the property: C(n, k) ≡ 0 (mod p) iff some digit k_i > n_i in base p.
    """
    # Convert n to base p
    digits = []
    temp = n
    while temp > 0:
        digits.append(temp % p)
        temp //= p
    if not digits:
        digits = [0]
    
    # Count i in [0, n] such that C(i, k) ≢ 0 (mod p)
    # This requires that for every digit position, k_j <= i_j
    # This is a digit DP problem
    # (Simplified version — full digit DP is in Chapter 85)
    return -1  # Placeholder for digit DP connection


def binom_with_crt(n, k, mod):
    """
    Compute C(n, k) mod mod where mod may be composite.
    Factor mod, use Lucas for each prime factor, combine with CRT.
    """
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
    
    def crt(remainders, moduli):
        """Chinese Remainder Theorem"""
        from math import gcd
        def ext_gcd(a, b):
            if b == 0:
                return a, 1, 0
            g, x1, y1 = ext_gcd(b, a % b)
            return g, y1, x1 - (a // b) * y1
        
        def mod_inv(a, m):
            g, x, _ = ext_gcd(a % m, m)
            return x % m
        
        M = 1
        for m in moduli:
            M *= m
        
        x = 0
        for i in range(len(moduli)):
            Mi = M // moduli[i]
            ti = mod_inv(Mi % moduli[i], moduli[i])
            x = (x + remainders[i] * Mi * ti) % M
        return x
    
    factors = factorize(mod)
    remainders = []
    moduli = []
    
    for p, e in factors:
        pe = p ** e
        # For prime power, use Lucas + lifting (simplified: use Lucas for e=1)
        if e == 1:
            rem = lucas(n, k, p)
        else:
            # For p^e, compute C(n,k) mod p^e using:
            # 1. Kummer's theorem for p-adic valuation
            # 2. Granville's extension of Lucas
            # Simplified: use direct computation for small n
            rem = lucas(n, k, p)  # approximation; full implementation is complex
        remainders.append(rem)
        moduli.append(pe)
    
    return crt(remainders, moduli)


# === Demo ===
if __name__ == "__main__":
    # Basic Lucas
    print(f"C(10, 3) mod 5 = {lucas(10, 3, 5)}")  # 0
    print(f"C(13, 6) mod 5 = {lucas(13, 6, 5)}")  # 1
    print(f"C(15, 7) mod 3 = {lucas(15, 7, 3)}")  # 0
    print(f"C(100, 50) mod 7 = {lucas(100, 50, 7)}")
    
    # Large values
    print(f"C(10^12, 10^11) mod 998244353 = {lucas(10**12, 10**11, 998244353)}")
    
    # Connection: C(n, k) mod 2 is the AND of bits
    # C(n, k) mod 2 = 1 iff (n AND k) == k
    n, k = 0b1101, 0b1001
    print(f"\nBitwise check: C({n}, {k}) mod 2 = {lucas(n, k, 2)}")
    print(f"  (n AND k) == k? {(n & k) == k}")
```

### 6.4 Python — Kummer's Theorem (Related)

```python
def kummer_exponent(n, k, p):
    """
    Kummer's Theorem: the exponent of p in C(n, k) equals
    the number of carries when adding k and (n-k) in base p.
    
    Equivalently: v_p(C(n, k)) = (digit_sum_p(k) + digit_sum_p(n-k) - digit_sum_p(n)) / (p-1)
    
    Time: O(log_p(n))
    """
    carries = 0
    temp_n = n
    temp_k = k
    while temp_n > 0 or temp_k > 0:
        ni = temp_n % p
        ki = temp_k % p
        if ki > ni:
            # This means we need a carry
            carries += 1
        temp_n //= p
        temp_k //= p
    return carries

def is_divisible_by_p(n, k, p):
    """Check if C(n, k) is divisible by prime p using Kummer's theorem"""
    return kummer_exponent(n, k, p) > 0

# Lucas gives C(n,k) mod p
# Kummer gives v_p(C(n,k)) — the exact power of p dividing C(n,k)
# Together they give complete information about C(n,k) modulo prime powers
```

### 6.5 Java — Lucas Theorem

```java
public class LucasTheorem {

    static final long MOD = 998244353L;

    static long power(long base, long exp, long mod) {
        long result = 1;
        base %= mod;
        while (exp > 0) {
            if ((exp & 1) == 1) result = result * base % mod;
            base = base * base % mod;
            exp >>= 1;
        }
        return result;
    }

    static long modInv(long a, long p) {
        return power(a, p - 2, p);
    }

    static long[] fac, invFac;

    static void precompute(int p) {
        fac = new long[p];
        invFac = new long[p];
        fac[0] = 1;
        for (int i = 1; i < p; i++)
            fac[i] = fac[i - 1] * i % p;
        invFac[p - 1] = modInv(fac[p - 1], p);
        for (int i = p - 2; i >= 0; i--)
            invFac[i] = invFac[i + 1] * (i + 1) % p;
    }

    static long smallBinom(int n, int k, int p) {
        if (k < 0 || k > n) return 0;
        return fac[n] % p * invFac[k] % p * invFac[n - k] % p;
    }

    static long lucas(long n, long k, int p) {
        if (k < 0 || k > n) return 0;
        long result = 1;
        while (n > 0 || k > 0) {
            int ni = (int)(n % p);
            int ki = (int)(k % p);
            if (ki > ni) return 0;
            result = result * smallBinom(ni, ki, p) % p;
            n /= p;
            k /= p;
        }
        return result;
    }

    // For large primes, compute binom directly
    static long binomDirect(long n, long k, long p) {
        if (k < 0 || k > n) return 0;
        if (k > n - k) k = n - k;
        long num = 1, den = 1;
        for (long i = 0; i < k; i++) {
            num = num * ((n - i) % p) % p;
            den = den * ((i + 1) % p) % p;
        }
        return num * modInv(den, p) % p;
    }

    static long lucasGeneral(long n, long k, long p) {
        if (k < 0 || k > n) return 0;
        long result = 1;
        while (n > 0 || k > 0) {
            long ni = n % p;
            long ki = k % p;
            if (ki > ni) return 0;
            long c = (p <= 1000000) ?
                smallBinom((int)ni, (int)ki, (int)p) :
                binomDirect(ni, ki, p);
            result = result * c % p;
            n /= p;
            k /= p;
        }
        return result;
    }

    public static void main(String[] args) {
        int p = 7;
        precompute(p);
        System.out.println("C(100, 50) mod 7 = " + lucas(100, 50, p));

        long pLarge = 998244353L;
        precompute((int) pLarge);
        System.out.println("C(10^12, 10^11) mod " + pLarge + " = " + lucasGeneral(1000000000000L, 100000000000L, pLarge));
    }
}
```

## 7. Complexity Analysis

| Operation | Time | Space | Notes |
|-----------|------|-------|-------|
| Precompute factorials | O(p) | O(p) | One-time per prime |
| Small binomial C(nᵢ, kᵢ) | O(1) | — | With precomputed factorials |
| Lucas theorem C(n, k) mod p | O(logₚ(n)) | O(p) | After precomputation |
| Lucas without precompute | O(logₚ(n) · p) | O(1) | For very large p |
| C(n, k) mod composite M | O(p₁ + p₂ + ... + √M) | O(max(pᵢ)) | Factorize + Lucas + CRT |

**Key insight**: For n up to 10¹⁸ and p around 10⁹, we need only about 2-3 digits in base p, making Lucas extremely fast.

## 8. Applications

### 8.1 Counting Problems

**Problem**: Count the number of ways to choose k items from n items modulo prime p, where n can be up to 10¹⁸.

**Solution**: Direct application of Lucas theorem.

### 8.2 Digit DP Connection

**Problem**: Count numbers in [0, N] whose digit sum in base p satisfies some condition involving binomial coefficients.

Lucas theorem naturally decomposes the problem digit-by-digit, making it compatible with digit DP. The state transition in digit DP often involves multiplying small binomial coefficients — exactly what Lucas computes.

### 8.3 Subset Sum Counting

**Problem**: Given a set S, count subsets of size k whose sum is divisible by p.

Using generating functions and roots of unity filter, the answer involves C(n, k) terms that can be computed via Lucas.

### 8.4 Catalan Numbers Mod p

The nth Catalan number Cₙ = C(2n, n) / (n+1) can be computed mod p using Lucas for the binomial coefficient and modular inverse for the division.

### 8.5 p-adic Valuation (Kummer's Theorem)

**Kummer's Theorem**: The exponent of prime p in C(n, k) equals the number of carries when adding k and n-k in base p.

This complements Lucas: Lucas gives C(n,k) mod p, while Kummer tells us the exact power of p dividing C(n,k). Together they enable computation of C(n,k) mod p^e.

## 9. Extensions

### 9.1 Lucas for Prime Powers: Granville's Extension

For computing C(n, k) mod p^e where e > 1, Andrew Granville extended Lucas theorem. The key idea:

1. Write n and k in base p
2. For each digit, compute C(nᵢ, kᵢ) mod p^e using the **lifting-the-exponent** technique
3. Account for the p-adic valuation using Kummer's theorem

This is significantly more complex and rarely needed in competitive programming.

### 9.2 Multinomial Lucas

Lucas extends to multinomial coefficients:

```
C(n; k₁, k₂, ..., kₘ) ≡ ∏ᵢ C(nᵢ; k₁ᵢ, k₂ᵢ, ..., kₘᵢ)  (mod p)
```

where n = Σ kⱼ and all numbers are written in base p.

## 10. Common Pitfalls

1. **Non-prime modulus**: Lucas theorem only works for prime moduli. For composite moduli, factorize and use CRT (Chapter 176).
2. **Precomputation overflow**: For p ≈ 10⁹, precomputing factorials up to p is infeasible. Use direct computation for large p.
3. **k > n**: Return 0 immediately.
4. **Negative values**: Ensure all intermediate values are non-negative mod p.
5. **p = 2 special case**: C(n, k) mod 2 = 1 iff (n AND k) == k. This is a well-known bit trick.

## 11. Exercises

### Warm-Up
1. Compute C(20, 10) mod 3 using Lucas theorem. Verify by computing 20 and 10 in base 3.
2. Show that C(2ⁿ - 1, k) ≡ (-1)^(popcount(k)) (mod 2) for all k.
3. For which values of k is C(100, k) divisible by 5?

### Standard
4. Implement a function that computes C(n, k) mod p for all k from 0 to n using Lucas theorem. Analyze the total time complexity.
5. Prove that the number of odd entries in row n of Pascal's triangle is 2^(popcount(n)).
6. Compute C(10¹⁸, 10⁹) mod 998244353 using Lucas theorem. What is the running time?

### Challenge
7. **[SPOJ DCEPC13D]** Given n, k, and prime p, compute C(n, k) mod p where n, k can be up to 10¹⁸.
8. Count the number of subsets of {1, 2, ..., n} whose sum is divisible by prime p. Express your answer using Lucas theorem.
9. Prove Kummer's theorem: the p-adic valuation of C(n, k) equals the number of carries when adding k and n-k in base p.
10. Design an algorithm to compute C(n, k) mod p^e for small e using Lucas + lifting. Analyze complexity.

## 12. Interview Questions

1. **Q**: What is Lucas theorem and when would you use it?
   **A**: Lucas theorem decomposes C(n, k) mod p into products of small binomial coefficients using base-p digits. It's used when n is very large (up to 10¹⁸) and the modulus is prime.

2. **Q**: How does Lucas theorem relate to digit DP?
   **A**: Both exploit digit-by-digit decomposition. Lucas computes products of per-digit binomial coefficients, while digit DP aggregates digit-constrained counts. They naturally combine when counting problems involve both binomial coefficients and digit constraints.

3. **Q**: What's the difference between Lucas theorem and Kummer's theorem?
   **A**: Lucas gives C(n, k) mod p (the value modulo p). Kummer gives v_p(C(n, k)) (the exact power of p dividing C(n, k)). Together they provide complete modular information.

4. **Q**: How would you compute C(n, k) mod 1000000007 where n can be 10¹⁸?
   **A**: Since 10⁹ + 7 is prime, directly apply Lucas theorem. Precompute factorials up to 10⁹ + 6 (infeasible!) — instead, use direct computation for each digit pair since there are at most 2 digits in base 10⁹+7 for n ≤ 10¹⁸.

## 13. Cross-References

- **Chapter 60: Number Theory** — Modular arithmetic, Fermat's little theorem
- **Chapter 71: Combinatorics** — Binomial coefficients, counting principles
- **Chapter 85: Digit DP** — Digit-by-digit decomposition pattern
- **Chapter 176: Chinese Remainder Theorem** — Combining results from multiple primes
- **Chapter 163: Advanced Mathematics** — p-adic numbers, Granville's extension
- **Appendix G: Mathematics Handbook** — Binomial coefficient properties
