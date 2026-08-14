# FFT and Polynomial Operations: Practical Guide

This chapter provides a practical, interview-oriented overview of FFT/NTT. For the full mathematical treatment and complete implementations, see Chapter 167 (FFT and NTT).

---

## Why FFT Matters

Polynomial multiplication via the naive O(n^2) method fails when n reaches 10^5. FFT reduces this to O(n log n) by transforming between coefficient and point-value representations. This is not just an academic curiosity — it appears in:

- **Convolution problems:** counting pairs with sum k, string matching via convolution, image processing
- **Big integer multiplication:** multiplying numbers with millions of digits
- **Combinatorics:** generating function multiplication, partition counting

---

## DFT/FFT Intuition

### The Key Insight

A polynomial of degree n-1 is uniquely determined by its values at n distinct points. So:

1. **Evaluate** A(x) and B(x) at n points → O(n) per point naively, but FFT evaluates at **roots of unity** in O(n log n)
2. **Multiply** pointwise → O(n)
3. **Interpolate** back to coefficients → O(n log n) via inverse FFT

### Roots of Unity

The n-th roots of unity are `w_k = e^(2πik/n)` for k = 0, 1, ..., n-1. They satisfy:
- `w_n^n = 1` (they lie on the unit circle)
- Symmetry: `w_n^(k + n/2) = -w_n^k` (this is what FFT exploits)

### Cooley-Tukey (Divide and Conquer FFT)

Split polynomial into even-indexed and odd-indexed coefficients. Recursively compute FFT of each half, then combine using the butterfly operation. The symmetry of roots of unity means the two recursive calls share computation, giving the O(n log n) speedup.

```
A(x) = A_even(x^2) + x * A_odd(x^2)
```

Evaluate at roots of unity: the even part uses the (n/2)-th roots of unity, and the odd part uses the same (n/2)-th roots of unity, shifted by a factor.

**Complexity:** O(n log n) time, O(n) space (in-place variant).

---

## Number Theoretic Transform (NTT)

FFT uses floating-point complex numbers, causing precision issues for large integer results. NTT replaces complex roots of unity with integers in a finite field GF(p).

**Requirements:** A primitive n-th root of unity `g` modulo prime `p` exists when `p = k*n + 1` (typically `n` is a power of 2).

Common moduli:

| Modulus | Max degree | Primitive root |
|---|---|---|
| 998244353 = 119 * 2^23 + 1 | 2^23 | 3 |
| 1004535809 = 479 * 2^21 + 1 | 2^21 | 3 |
| 469762049 = 7 * 2^26 + 1 | 2^26 | 3 |

For degrees exceeding a single modulus, use **CRT to combine results** from multiple moduli (garner's algorithm).

---

## Applications in Practice

### 1. Polynomial Multiplication

The direct application. Pad both polynomials to length >= n + m, run NTT on each, multiply pointwise, inverse NTT.

### 2. Convolution

Given arrays `a[0..n-1]` and `b[0..m-1]`, compute `c[k] = sum(a[i] * b[k-i])`. This IS polynomial multiplication.

**Classic problem:** Given an array, count pairs (i, j) where `a[i] + a[j] = k`. Build polynomial A where `A[x]` = count of x in the array. Then `A^2`'s coefficient of x^k gives the answer.

### 3. String Matching via Convolution

Convert pattern to values {0, 1, -1} and text similarly. The convolution reveals alignment positions.

### 4. Bitset Convolution (Subset Sum)

Use FFT to compute the number of subsets summing to each value — essentially multiplying generating functions.

---

## Quick Decision: FFT or Naive?

| n | Method |
|---|---|
| n <= 5000 | Naive O(n^2) |
| 5000 < n <= 10^6 | NTT with single modulus |
| n > 10^6 | NTT with multiple moduli + CRT |

---

## Interview Questions

1. **Multiply two polynomials of degree 10^5.** Describe the FFT-based approach. What is the time complexity?

2. **Why can't we always use NTT instead of FFT?** Discuss the modulus constraints and the degree limitation.

3. **Count pairs (i, j) in an array where a[i] + a[j] = k.** Design the convolution-based O(n log n) solution.

4. **How does FFT achieve O(n log n) when evaluating a polynomial at n points naively takes O(n^2)?** Explain the divide-and-conquer structure.

5. **What happens if the polynomial degree is not a power of 2?** Explain zero-padding and why it works.

6. **Explain the relationship between convolution and polynomial multiplication.** Why are they the same operation?

7. **How would you multiply two 10^6-digit integers?** Describe the approach using NTT.

8. **What precision issues arise with FFT using floating-point arithmetic?** How does NTT avoid them? When might NTT fail?