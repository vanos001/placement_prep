# Chapter 167: FFT and NTT — Fast Polynomial Operations

## 1. Definition

The **Fast Fourier Transform (FFT)** is an algorithm that computes the Discrete Fourier Transform (DFT) and its inverse in O(n log n) time, reducing the naive O(n²) approach. The **Number Theoretic Transform (NTT)** is the modular arithmetic analogue of FFT, operating over finite fields instead of complex numbers.

Together, they enable fast **polynomial multiplication**, **convolution**, and a wide range of combinatorial computations.

## 2. Motivation

Consider multiplying two polynomials of degree n:

```
A(x) = a₀ + a₁x + a₂x² + ... + aₙxⁿ
B(x) = b₀ + b₁x + b₂x² + ... + bₙxⁿ
```

The product C(x) = A(x) · B(x) has degree 2n, and computing each coefficient naively takes O(n) time, giving O(n²) overall. For n = 10⁶, this is 10¹² operations — far too slow.

FFT reduces this to **O(n log n)** by exploiting the fact that polynomial multiplication in the **coefficient domain** corresponds to **pointwise multiplication** in the **frequency domain**.

### When Do We Need This?

- Multiplying very large integers (arbitrary precision)
- Counting problems involving convolution (e.g., number of ways to sum to k)
- String matching with wildcards
- Subset sum variants
- Generating functions in combinatorics

## 3. Intuition: The Core Idea

### Polynomials Have Two Representations

| Representation | Description |
|---|---|
| **Coefficient form** | A(x) = [a₀, a₁, ..., aₙ] |
| **Point-value form** | {(x₀, A(x₀)), (x₁, A(x₁)), ..., (xₙ, A(xₙ))} |

**Key insight**: Multiplying two polynomials in point-value form is O(n) — just multiply the values at each point. The expensive part is converting between representations.

### FFT = Fast conversion between forms

1. **Evaluate** A and B at n carefully chosen points → O(n log n) each
2. **Multiply** pointwise → O(n)
3. **Interpolate** back to coefficient form → O(n log n)

The "carefully chosen points" are the **nth roots of unity**: complex numbers ω where ωⁿ = 1.

## 4. Mathematical Foundations

### 4.1 Roots of Unity

The **nth root of unity** is:

```
ωₙ = e^(2πi/n) = cos(2π/n) + i·sin(2π/n)
```

The n nth roots of unity are: ωₙ⁰, ωₙ¹, ωₙ², ..., ωₙⁿ⁻¹

**Critical properties:**
- ωₙⁿ = 1 (periodicity)
- ωₙ^(n/2) = -1 (cancellation lemma)
- ωₙ^(2k) = ωₙ/₂^k (reduction lemma)
- Sum of all nth roots = 0

### 4.2 Discrete Fourier Transform (DFT)

Given polynomial A(x) = Σ aⱼxʲ evaluated at ωₙ⁰, ωₙ¹, ..., ωₙⁿ⁻¹:

```
A(ωₙᵏ) = Σⱼ₌₀ⁿ⁻¹ aⱼ · ωₙ^(jk)    for k = 0, 1, ..., n-1
```

This is a matrix-vector multiplication: **y = F · a**, where F is the Fourier matrix F[j,k] = ωₙ^(jk).

### 4.3 The Butterfly Operation

The key recursive step splits A(x) by even/odd indices:

```
A(x) = A_even(x²) + x · A_odd(x²)
```

Where:
- A_even(x) = a₀ + a₂x + a₄x² + ... (even-indexed coefficients)
- A_odd(x) = a₁ + a₃x + a₅x² + ... (odd-indexed coefficients)

Evaluating at ωₙᵏ:
```
A(ωₙᵏ) = A_even(ωₙ/₂ᵏ) + ωₙᵏ · A_odd(ωₙ/₂ᵏ)
A(ωₙ^(k+n/2)) = A_even(ωₙ/₂ᵏ) - ωₙᵏ · A_odd(ωₙ/₂ᵏ)
```

This is the **butterfly** — one operation gives us two values.

## 5. The FFT Algorithm

### 5.1 Recursive Implementation

```
FFT(a[0..n-1]):
    if n == 1: return a
    
    ωₙ = e^(2πi/n)
    ω = 1
    
    a_even = [a[0], a[2], ..., a[n-2]]
    a_odd  = [a[1], a[3], ..., a[n-1]]
    
    y_even = FFT(a_even)
    y_odd  = FFT(a_odd)
    
    for k = 0 to n/2 - 1:
        t = ω · y_odd[k]
        y[k]       = y_even[k] + t
        y[k + n/2] = y_even[k] - t
        ω = ω · ωₙ
    
    return y
```

**Time**: T(n) = 2T(n/2) + O(n) = O(n log n)

### 5.2 Iterative Implementation (In-Place)

The recursive approach has overhead from function calls and memory allocation. The iterative version uses **bit-reversal permutation** to reorder elements, then applies butterflies bottom-up.

**Bit-reversal**: For n = 8, indices 0-7 in binary are:
```
000 → 000 (0)
001 → 100 (4)
010 → 010 (2)
011 → 110 (6)
100 → 001 (1)
101 → 101 (5)
110 → 011 (3)
111 → 111 (7)
```

After bit-reversal, we process levels from bottom (size 2) to top (size n), applying butterflies at each level.

## 6. Inverse FFT

To convert back from point-value to coefficient form:

```
IFFT(y) = (1/n) · FFT(conjugate(y))_conjugated
```

Or equivalently, use ωₙ⁻¹ instead of ωₙ and divide by n.

**Verification**: The Fourier matrix F satisfies F⁻¹ = (1/n) · F* (conjugate transpose).

## 7. NTT — Number Theoretic Transform

### 7.1 Why NTT?

FFT uses complex numbers, which introduce floating-point errors. For problems requiring exact modular arithmetic (e.g., computing answers mod 10⁹+7), we need NTT.

### 7.2 Modular Roots of Unity

Instead of e^(2πi/n), we use a **primitive root** g of a prime p.

If p = c·n + 1 for some integer c, and g is a primitive root mod p, then:

```
ωₙ = g^c mod p
```

is a primitive nth root of unity in the modular sense: ωₙⁿ ≡ 1 (mod p) and ωₙᵏ ≢ 1 for 0 < k < n.

### 7.3 Common NTT Primes

| Prime p | p - 1 factorization | Max n | Primitive root g |
|---|---|---|---|
| 998244353 | 2²³ × 7 × 17 | 2²³ = 8388608 | 3 |
| 1004535809 | 2²¹ × 479 | 2²¹ = 2097152 | 3 |
| 469762049 | 2²⁶ × 7 | 2²⁶ = 67108864 | 3 |

### 7.4 NTT Algorithm

Identical to FFT, but with:
- Complex arithmetic replaced by modular arithmetic
- ωₙ = g^((p-1)/n) mod p
- Division by n replaced by multiplication by n⁻¹ mod p

### 7.5 Convolution with Arbitrary Modulus

When the modulus m is not NTT-friendly, use **CRT (Chinese Remainder Theorem)**:
1. Choose two NTT-friendly primes p₁, p₂ with p₁·p₂ > m · n
2. Compute convolution mod p₁ and mod p₂
3. Combine using CRT to get result mod m

Or use **three-NTT** for even larger ranges.

## 8. Polynomial Multiplication Walkthrough

### Example: Multiply A(x) = 1 + 2x + 3x² and B(x) = 4 + 5x + 6x²

**Naive approach** (coefficient domain):
```
C(x) = A(x)·B(x)
c₀ = 1·4 = 4
c₁ = 1·5 + 2·4 = 13
c₂ = 1·6 + 2·5 + 3·4 = 28
c₃ = 2·6 + 3·5 = 27
c₄ = 3·6 = 18
Result: 4 + 13x + 28x² + 27x³ + 18x⁴
```

**FFT approach**:
1. Pad to length 8 (next power of 2 ≥ 6)
2. Evaluate A and B at 8th roots of unity
3. Multiply pointwise: C(ωₖ) = A(ωₖ) · B(ωₖ)
4. IFFT to get coefficients

The result is the same: [4, 13, 28, 27, 18, 0, 0, 0].

## 9. Applications

### 9.1 Large Integer Multiplication

To multiply two large numbers, treat their digits as polynomial coefficients:

```
1234 × 5678
→ A(x) = 4 + 3x + 2x² + x³  (digits reversed)
→ B(x) = 8 + 7x + 6x² + 5x³
→ C(x) = A(x)·B(x) via FFT
→ Propagate carries in C's coefficients
```

**Time**: O(n log n) where n is the number of digits.

### 9.2 String Matching with Wildcards

Given text T of length n and pattern P of length m (with wildcard `*` matching any character), find all positions where P matches.

**Approach**:
```
Score(j) = Σᵢ (T[j+i] - P[i])² · P[i] · T[j+i]

For non-wildcard positions, this equals 0 when P matches T at position j.
Expand: Σ T[j+i]²·P[i] - 2·Σ T[j+i]·P[i]² + Σ P[i]³

Each sum is a convolution, computable via FFT in O(n log n).
```

### 9.3 Counting Subset Sums

Given a set of n positive integers, count the number of subsets that sum to k for all k from 0 to S (total sum).

**Approach**: Use generating functions.
```
For each element aᵢ, multiply the polynomial by (1 + x^aᵢ).
The coefficient of x^k in the product is the answer for sum k.
```

Using divide-and-conquer with FFT: O(S log S log n).

### 9.4 Convolution in Combinatorics

Many counting problems reduce to convolution:

- **Number of ways** to partition n into two parts from sets A and B: C[k] = Σ A[i]·B[k-i]
- **Binomial coefficient** computation
- **Catalan numbers** via generating functions

## 10. Complexity Analysis

| Operation | Naive | FFT/NTT |
|---|---|---|
| Polynomial multiplication | O(n²) | O(n log n) |
| Large integer multiplication | O(n²) | O(n log n) |
| Convolution | O(n²) | O(n log n) |
| String matching with wildcards | O(nm) | O(n log n) |

**Space**: O(n) for the iterative version.

**Precision**: FFT has floating-point errors (typically 10⁻⁹ for n ≤ 10⁶). NTT is exact modulo p.

## 11. Code

### 11.1 C++ — Iterative FFT

```cpp
#include <bits/stdc++.h>
using namespace std;

typedef complex<double> cd;
const double PI = acos(-1);

void fft(vector<cd>& a, bool invert) {
    int n = a.size();
    
    // Bit-reversal permutation
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1)
            j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }
    
    // Butterfly operations
    for (int len = 2; len <= n; len <<= 1) {
        double ang = 2 * PI / len * (invert ? -1 : 1);
        cd wlen(cos(ang), sin(ang));
        for (int i = 0; i < n; i += len) {
            cd w(1);
            for (int j = 0; j < len / 2; j++) {
                cd u = a[i + j];
                cd v = a[i + j + len / 2] * w;
                a[i + j] = u + v;
                a[i + j + len / 2] = u - v;
                w *= wlen;
            }
        }
    }
    
    if (invert) {
        for (cd& x : a) x /= n;
    }
}

vector<int> multiply(vector<int> const& a, vector<int> const& b) {
    vector<cd> fa(a.begin(), a.end()), fb(b.begin(), b.end());
    int n = 1;
    while (n < (int)(a.size() + b.size()))
        n <<= 1;
    fa.resize(n);
    fb.resize(n);
    
    fft(fa, false);
    fft(fb, false);
    for (int i = 0; i < n; i++)
        fa[i] *= fb[i];
    fft(fa, true);
    
    vector<int> result(n);
    for (int i = 0; i < n; i++)
        result[i] = round(fa[i].real());
    return result;
}

int main() {
    vector<int> a = {1, 2, 3};
    vector<int> b = {4, 5, 6};
    vector<int> c = multiply(a, b);
    // c = {4, 13, 28, 27, 18}
    for (int x : c) cout << x << " ";
    cout << endl;
    return 0;
}
```

### 11.2 C++ — NTT (mod 998244353)

```cpp
#include <bits/stdc++.h>
using namespace std;

const int MOD = 998244353;
const int G = 3;  // primitive root

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

void ntt(vector<int>& a, bool invert) {
    int n = a.size();
    
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1)
            j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }
    
    for (int len = 2; len <= n; len <<= 1) {
        int wlen = power(G, (MOD - 1) / len, MOD);
        if (invert) wlen = power(wlen, MOD - 2, MOD);
        for (int i = 0; i < n; i += len) {
            int w = 1;
            for (int j = 0; j < len / 2; j++) {
                int u = a[i + j];
                int v = (long long)a[i + j + len / 2] * w % MOD;
                a[i + j] = (u + v) % MOD;
                a[i + j + len / 2] = (u - v + MOD) % MOD;
                w = (long long)w * wlen % MOD;
            }
        }
    }
    
    if (invert) {
        int n_inv = power(n, MOD - 2, MOD);
        for (int& x : a)
            x = (long long)x * n_inv % MOD;
    }
}

vector<int> multiply(vector<int> const& a, vector<int> const& b) {
    vector<int> fa(a.begin(), a.end()), fb(b.begin(), b.end());
    int n = 1;
    while (n < (int)(a.size() + b.size()))
        n <<= 1;
    fa.resize(n);
    fb.resize(n);
    
    ntt(fa, false);
    ntt(fb, false);
    for (int i = 0; i < n; i++)
        fa[i] = (long long)fa[i] * fb[i] % MOD;
    ntt(fa, true);
    
    return fa;
}
```

### 11.3 Python — FFT

```python
import cmath
import math

def fft(a, invert=False):
    n = len(a)
    if n == 1:
        return a
    
    # Bit-reversal permutation
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    
    # Butterfly operations
    length = 2
    while length <= n:
        ang = 2 * math.pi / length * (-1 if invert else 1)
        wlen = complex(math.cos(ang), math.sin(ang))
        for i in range(0, n, length):
            w = 1+0j
            for j in range(length // 2):
                u = a[i + j]
                v = a[i + j + length // 2] * w
                a[i + j] = u + v
                a[i + j + length // 2] = u - v
                w *= wlen
        length <<= 1
    
    if invert:
        for i in range(n):
            a[i] /= n
    return a

def multiply(a, b):
    n = 1
    while n < len(a) + len(b):
        n <<= 1
    fa = [complex(x, 0) for x in a] + [0j] * (n - len(a))
    fb = [complex(x, 0) for x in b] + [0j] * (n - len(b))
    
    fft(fa, False)
    fft(fb, False)
    for i in range(n):
        fa[i] *= fb[i]
    fft(fa, True)
    
    return [round(fa[i].real) for i in range(n)]

# Example
a = [1, 2, 3]
b = [4, 5, 6]
print(multiply(a, b))  # [4, 13, 28, 27, 18, 0, 0, 0]
```

### 11.4 Python — NTT

```python
MOD = 998244353
G = 3

def power(base, exp, mod):
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result

def ntt(a, invert=False):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    
    length = 2
    while length <= n:
        wlen = power(G, (MOD - 1) // length, MOD)
        if invert:
            wlen = power(wlen, MOD - 2, MOD)
        for i in range(0, n, length):
            w = 1
            for j in range(length // 2):
                u = a[i + j]
                v = a[i + j + length // 2] * w % MOD
                a[i + j] = (u + v) % MOD
                a[i + j + length // 2] = (u - v + MOD) % MOD
                w = w * wlen % MOD
        length <<= 1
    
    if invert:
        n_inv = power(n, MOD - 2, MOD)
        for i in range(n):
            a[i] = a[i] * n_inv % MOD

def multiply_ntt(a, b):
    n = 1
    while n < len(a) + len(b):
        n <<= 1
    fa = a[:] + [0] * (n - len(a))
    fb = b[:] + [0] * (n - len(b))
    
    ntt(fa, False)
    ntt(fb, False)
    for i in range(n):
        fa[i] = fa[i] * fb[i] % MOD
    ntt(fa, True)
    return fa

# Example
print(multiply_ntt([1, 2, 3], [4, 5, 6]))  # [4, 13, 28, 27, 18, 0, 0, 0] mod 998244353
```

### 11.5 Java — Iterative FFT

```java
import java.util.*;

public class FFT {
    static class Complex {
        double re, im;
        Complex(double re, double im) { this.re = re; this.im = im; }
        Complex add(Complex o) { return new Complex(re + o.re, im + o.im); }
        Complex sub(Complex o) { return new Complex(re - o.re, im - o.im); }
        Complex mul(Complex o) {
            return new Complex(re * o.re - im * o.im, re * o.im + im * o.re);
        }
        Complex div(double d) { return new Complex(re / d, im / d); }
    }
    
    static void fft(Complex[] a, boolean invert) {
        int n = a.length;
        for (int i = 1, j = 0; i < n; i++) {
            int bit = n >> 1;
            for (; (j & bit) != 0; bit >>= 1) j ^= bit;
            j ^= bit;
            if (i < j) { Complex tmp = a[i]; a[i] = a[j]; a[j] = tmp; }
        }
        for (int len = 2; len <= n; len <<= 1) {
            double ang = 2 * Math.PI / len * (invert ? -1 : 1);
            Complex wlen = new Complex(Math.cos(ang), Math.sin(ang));
            for (int i = 0; i < n; i += len) {
                Complex w = new Complex(1, 0);
                for (int j = 0; j < len / 2; j++) {
                    Complex u = a[i + j];
                    Complex v = a[i + j + len / 2].mul(w);
                    a[i + j] = u.add(v);
                    a[i + j + len / 2] = u.sub(v);
                    w = w.mul(wlen);
                }
            }
        }
        if (invert) for (int i = 0; i < n; i++) a[i] = a[i].div(n);
    }
    
    static int[] multiply(int[] a, int[] b) {
        int n = 1;
        while (n < a.length + b.length) n <<= 1;
        Complex[] fa = new Complex[n], fb = new Complex[n];
        for (int i = 0; i < n; i++) {
            fa[i] = new Complex(i < a.length ? a[i] : 0, 0);
            fb[i] = new Complex(i < b.length ? b[i] : 0, 0);
        }
        fft(fa, false);
        fft(fb, false);
        for (int i = 0; i < n; i++) fa[i] = fa[i].mul(fb[i]);
        fft(fa, true);
        int[] res = new int[n];
        for (int i = 0; i < n; i++) res[i] = (int) Math.round(fa[i].re);
        return res;
    }
    
    public static void main(String[] args) {
        int[] result = multiply(new int[]{1, 2, 3}, new int[]{4, 5, 6});
        System.out.println(Arrays.toString(result)); // [4, 13, 28, 27, 18, 0, 0, 0]
    }
}
```

## 12. Dry Run: FFT Butterfly Operations

For n = 4, polynomials a = [1, 2, 3, 4]:

**Step 1: Bit-reversal**
```
Index: 0(00), 1(01), 2(10), 3(11)
Reversed: 0(00), 2(01), 1(10), 3(11)
After: [1, 3, 2, 4]
```

**Step 2: Length 2 butterflies**
```
ω₄ = i, wlen for len=2: ω₂ = -1
Pair (0,1): u=1, v=3·1=3 → [1+3, 1-3] = [4, -2]
Pair (2,3): u=2, v=4·1=4 → [2+4, 2-4] = [6, -2]
Result: [4, -2, 6, -2]
```

**Step 3: Length 4 butterflies**
```
wlen = ω₄ = i
Pair (0,2): u=4, v=6·1=6 → [4+6, 4-6] = [10, -2]
Pair (1,3): u=-2, v=-2·i=-2i → [-2+(-2i), -2-(-2i)] = [-2-2i, -2+2i]
Result: [10, -2-2i, -2, -2+2i]
```

DFT of [1,2,3,4] = [10, -2-2i, -2, -2+2i] ✓

## 13. Variants and Extensions

### 13.1 Multidimensional FFT
Apply 1D FFT along each dimension. Used for 2D convolution (image processing).

### 13.2 Chirp Z-Transform
Evaluate polynomial at arbitrary geometric sequence of points, not just roots of unity. Reduces to convolution via FFT.

### 13.3 Walsh-Hadamard Transform (XOR Convolution)
Replace roots of unity with {1, -1}. Used for XOR-based convolutions:
```
C[k] = Σᵢ A[i] · B[i ⊕ k]
```

### 13.4 Subset Convolution
For computing C[S] = Σ_{T⊆S} A[T] · B[S\T], use ranked transforms with O(2ⁿ · n²) complexity.

## 14. Common Pitfalls

1. **Forgetting to round**: FFT results are floating-point; always round to nearest integer.
2. **Insufficient precision**: For large n or large coefficients, use long double or NTT.
3. **Wrong padding**: Result of degree-n × degree-m multiplication needs n+m+1 coefficients. Pad FFT to next power of 2 ≥ n+m+1.
4. **Modulus not NTT-friendly**: Use CRT with multiple primes for arbitrary moduli.
5. **Off-by-one in indexing**: Polynomial coefficient a₀ is the constant term.

## 15. Exercises

1. **Basic**: Multiply (1 + x + x²) and (1 - x + x²) using FFT. Verify manually.
2. **Medium**: Given n integers, count pairs (i,j) where a[i] + a[j] = k. Solve in O(S log S).
3. **Hard**: Implement large integer multiplication using FFT. Handle negative numbers and carry propagation.
4. **Challenge**: Given a string with wildcards, find all occurrences of a pattern. Implement using FFT.
5. **Challenge**: Compute the number of ways to partition a set of n items into subsets with given sizes using generating functions and FFT.

## 16. Interview Questions

1. **Q**: What is the time complexity of polynomial multiplication using FFT?
   **A**: O(n log n), where n is the degree of the result polynomial.

2. **Q**: Why do we need NTT instead of FFT?
   **A**: FFT uses floating-point arithmetic, which introduces precision errors. NTT operates in modular arithmetic, giving exact results — critical for competitive programming and cryptographic applications.

3. **Q**: What are the requirements for a prime to support NTT?
   **A**: The prime p must satisfy p = c·2^k + 1 for some c, k, so that 2^k divides p-1, allowing a primitive 2^k-th root of unity to exist.

4. **Q**: How would you multiply two polynomials modulo 10⁹+7?
   **A**: 10⁹+7 is not NTT-friendly. Use three NTT-friendly primes (e.g., 998244353, 1004535809, 469762049), compute the result mod each, then combine via CRT.

5. **Q**: Give an application of FFT outside of polynomial multiplication.
   **A**: String matching with wildcards — transform the matching condition into a series of convolutions, each computable in O(n log n) via FFT.

## 17. Cross-References

- **Chapter 60: Number Theory** — Modular arithmetic, primitive roots, CRT
- **Chapter 71: Combinatorics** — Generating functions, counting problems
- **Chapter 73: Linear Algebra** — Matrix multiplication, eigendecomposition
- **Chapter 40: Rolling Hash** — Alternative approach to string matching
- **Chapter 86: DP Optimization** — Some DP optimizations use convolution
- **Chapter 163: Advanced Mathematics** — Abstract algebra, ring theory foundations

## 18. Further Reading

- [CP-Algorithms: FFT](https://cp-algorithms.com/algebra/fft.html)
- [CP-Algorithms: NTT](https://cp-algorithms.com/algebra/fft-modular.html)
- *Introduction to Algorithms* (CLRS), Chapter 30 — Polynomials and the FFT
- "Competitive Programming 3" by Steven Halim — FFT section
