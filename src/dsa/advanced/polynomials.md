# Polynomials and Generating Functions

Beyond the FFT/NTT fundamentals in [Ch 167](../chapters/ch167-fft-ntt.md) and [fft-and-polynomial.md](../chapters/fft-and-polynomial.md), this file covers generating functions, formal power series, Bluestein's FFT for arbitrary lengths, multipoint evaluation, polynomial interpolation, Berlekamp-Massey for linear recurrences, and Kitamasa's method.

---

## Generating Functions

### Ordinary Generating Functions (OGF)

For a sequence $a_0, a_1, a_2, \ldots$, the OGF is:

\[A(x) = \sum_{n=0}^{\infty} a_n x^n\]

**Key operations**:
- **Convolution** (product of OGFs): If $C(x) = A(x) \cdot B(x)$, then $c_n = \sum_{k=0}^{n} a_k b_{n-k}$.
- **Partial sums**: $\sum_{k=0}^{n} a_k$ has OGF $A(x) / (1-x)$.
- **Shift right**: $0, a_0, a_1, \ldots$ has OGF $x A(x)$.

### Exponential Generating Functions (EGF)

\[A(x) = \sum_{n=0}^{\infty} a_n \frac{x^n}{n!}\]

**Key property**: The product of two EGFs corresponds to the **labeled product** (shuffle product). If $A(x)$ counts structures of type $\alpha$ and $B(x)$ counts type $\beta$, then $A(x) \cdot B(x)$ counts ways to partition a labeled set into an $\alpha$-structure and a $\beta$-structure.

**Classic example**: The EGF for permutations with $k$ cycles (Stirling numbers of the first kind) is $\frac{(-\log(1-x))^k}{k!}$. The EGF for partitions of $n$ into $k$ blocks (Stirling numbers of the second kind) is $\frac{(e^x - 1)^k}{k!}$.

### Applications

- **Counting combinatorial objects**: Derive closed-form or recurrence formulas.
- **Expected values**: EGFs of probability distributions.
- **Solving recurrences**: Convert a recurrence to a functional equation in the generating function, solve algebraically, extract coefficients.

---

## Formal Power Series (FPS)

### Algebra of FPS

A formal power series $A(x) = \sum_{n \geq 0} a_n x^n$ is treated as a formal algebraic object without worrying about convergence. All operations (addition, multiplication, division, composition, inversion) are defined algebraically.

### Key Operations

| Operation | Formula | FFT Complexity |
-----------|---------|----------------|
| Multiplication | $C = A \cdot B$ (convolution) | $O(n \log n)$ |
| Division | $Q = A / B$ where $B[0] \neq 0$ | $O(n \log n)$ (Newton's method) |
| Inverse | $B^{-1}$ where $B[0] = 1$ | $O(n \log n)$ |
| Sqrt | $S^2 = A$ where $A[0] = 1$ | $O(n \log n)$ |
| $\exp(A)$ | $E = e^A$ where $A[0] = 0$ | $O(n \log n)$ |
| $\ln(A)$ | $L = \ln A$ where $A[0] = 1$ | $O(n \log n)$ |
| Power $A^k$ | Via $e^{k \ln A}$ | $O(n \log n)$ |

### Newton's Method for FPS Inversion

To find $B^{-1}$ given $B$ (with $B[0] = 1$), use Newton iteration:

\[B_{i+1}^{-1} = B_i^{-1} \cdot (2 - B \cdot B_i^{-1}) \pmod{x^{2^{i+1}}}

Starting with $B_0^{-1} = 1$, each iteration doubles the number of correct coefficients. Total work: $O(n \log n)$ (geometric series of FFT costs).

---

## Polynomial Multiplication: FFT, NTT, Bluestein

### Cooley-Tukey FFT

The standard $O(n \log n)$ polynomial multiplication via FFT over complex numbers. Covered in [Ch 167](../chapters/ch167-fft-ntt.md). Works for any power-of-2 length (zero-pad shorter polynomials).

### NTT (Number Theoretic Transform)

FFT over a finite field $\mathbb{F}_p$ where $p$ is a prime with a primitive $n$-th root of unity. Common moduli:

- $998244353 = 119 \cdot 2^{23} + 1$: primitive root $g = 3$, supports $n = 2^{23}$.
- $1004535809 = 479 \cdot 2^{21} + 1$: for products needing larger moduli.
- $469762049 = 7 \cdot 2^{26} + 1$: for very large transforms.

NTT is exact (no floating-point errors) and typically 2-3x faster than complex FFT in practice.

### Bluestein's FFT

**Problem**: Standard FFT/NTT require $n$ to be a power of 2 (or to have suitable prime factorization). Bluestein's algorithm handles **arbitrary** polynomial lengths.

**Key idea**: Use the chirp-z transform. The product $c_k = \sum_{j} a_j b_{k-j}$ is equivalent to a convolution with a specific sequence involving powers of a quadratic:

\[c_k = z^{k^2/2} \sum_{j} (a_j \cdot z^{-j^2/2}) \cdot z^{(k-j)^2/2}

This converts a length-$n$ convolution into a length-$m$ convolution where $m = 2n - 1$ (chosen to be a power of 2 or suitable for NTT).

```
function bluestein_multiply(A, B):
    n = len(A) + len(B) - 1
    m = next_power_of_2(2*n - 1)
    # Precompute chirp sequence
    W = [omega^(i*i % (2*m)) for i in range(m)]  # omega = primitive root
    W_inv = [omega^(-i*i % (2*m)) for i in range(m)]
    # Pad A and B with chirp factors
    A_pad = [A[i] * W_inv[i] for i in range(len(A))] + [0]*(m - len(A))
    B_pad = [B[i] * W_inv[i] for i in range(len(B))] + [0]*(m - len(B))
    # Convolve using standard FFT/NTT
    C = circular_convolution(A_pad, B_pad)
    # Multiply by W to get the result
    result = [C[k] * W[k] for k in range(n)]
    return result
```

**Complexity**: $O(n \log n)$ where $n$ is the output length. The constant factor is roughly 3x that of standard FFT (three FFT calls + precomputation).

---

## Multipoint Evaluation

### Problem

Given a polynomial $A(x)$ of degree $n$ and $m$ points $x_1, \ldots, x_m$, compute $A(x_1), A(x_2), \ldots, A(x_m)$.

### Naive

$O(nm)$: evaluate at each point separately via Horner's method.

### Fast Algorithm: $O((n+m) \log^2(n+m))$

1. **Build a product tree**: A binary tree where the root stores $\prod_{i=1}^{m} (x - x_i)$, internal nodes store products of their children's polynomials, and leaves store $(x - x_i)$.

```
       (x-x1)(x-x2)(x-x3)(x-x4)    (product of all)
       /                          \
  (x-x1)(x-x2)              (x-x3)(x-x4)   (products of halves)
  /         \                /         \
(x-x1)    (x-x2)        (x-x3)     (x-x4)  (leaves)
```

2. **Remainder tree**: Starting with $A$ at the root, compute $A \bmod P_v$ for each node $v$ by going down the tree. At leaves, $A \bmod (x - x_i) = A(x_i)$ (constant polynomial).

**Complexity**: Building the product tree is $O(m \log^2 m)$ (each level does $O(m \log m)$ work in polynomial multiplications). The remainder tree is also $O(m \log^2 m)$ for the same reason. If $m \approx n$, total is $O(n \log^2 n)$.

---

## Polynomial Interpolation

### Problem

Given $n$ points $(x_1, y_1), \ldots, (x_n, y_n)$, find the unique polynomial $A(x)$ of degree $< n$ passing through all points.

### Lagrange Interpolation

\[A(x) = \sum_{i=1}^{n} y_i \cdot \prod_{j \neq i} \frac{x - x_j}{x_i - x_j}

Naive: $O(n^2)$. With prefix/suffix products at consecutive integer points: $O(n)$.

### Fast Interpolation: $O(n \log^2 n)$

The dual of multipoint evaluation. Uses the same product tree, but constructs the polynomial by combining Lagrange basis polynomials bottom-up.

**Key formula**: If $P = P_L \cdot P_R$ (left and right halves), and we know the interpolant on the left half $A_L$ and right half $A_R$:

\[A = A_L \cdot P_R \cdot (P_R^{-1} \bmod P_L) + A_R \cdot P_L \cdot (P_L^{-1} \bmod P_R)

This requires polynomial inversion and modular multiplication at each level, giving $O(n \log^2 n)$ total.

---

## Berlekamp-Massey Algorithm

### Problem

Given a sequence $s_0, s_1, \ldots, s_{n-1}$, find the **shortest linear recurrence** (LFSR) that generates it:

\[s_i = c_1 s_{i-1} + c_2 s_{i-2} + \cdots + c_L s_{i-L} \quad \text{for } i \geq L

### Algorithm

Maintain the current best recurrence $C$ and a "previous best" $B$ from before the last discrepancy.

```
function berlekamp_massey(s):
    # s = [s_0, s_1, ..., s_{n-1}]
    C = [1]  # current connection polynomial
    B = [1]  # previous connection polynomial
    L = 0    # current recurrence length
    m = 1    # shift counter
    b = 1    # previous discrepancy
    for n = 0 to len(s)-1:
        # Compute discrepancy
        d = s[n]
        for i = 1 to L:
            d += C[i] * s[n - i]
        d %= MOD
        if d == 0:
            m += 1
        elif 2*L <= n:
            # Need to update L
            T = copy(C)
            coeff = d * mod_inverse(b) % MOD
            # C = C - coeff * x^m * B
            extend C to length len(B) + m with zeros
            for i = 0 to len(B)-1:
                C[i + m] = (C[i + m] - coeff * B[i]) % MOD
            L = n + 1 - L
            B = T
            b = d
            m = 1
        else:
            coeff = d * mod_inverse(b) % MOD
            extend C to length len(B) + m with zeros
            for i = 0 to len(B)-1:
                C[i + m] = (C[i + m] - coeff * B[i]) % MOD
            m += 1
    return C[1:], L  # recurrence coefficients and length
```

**Complexity**: $O(n^2)$ naively, $O(n \log n)$ with FFT-based polynomial operations.

### Applications

- **Finding the $k$-th term** of a linear recurrence: combine with Kitamasa or linear recurrence exponentiation.
- **Recovering polynomials from evaluations**: If $s_n = P(n)$ for a polynomial $P$ of degree $d$, the recurrence has length $d+1$.
- **CP applications**: Finding patterns in sequences, generating function manipulation.

---

## Linear Recurrences and Kitamasa

### Problem

Given a linear recurrence $s_n = \sum_{i=1}^{L} c_i s_{n-i}$ and initial values $s_0, \ldots, s_{L-1}$, compute $s_k$ for a large $k$ (e.g., $k = 10^{18}$).

### Matrix Exponentiation

The standard approach: represent the recurrence as a matrix and compute $M^k$ in $O(L^3 \log k)$ using [matrix exponentiation](../chapters/ch174-matrix-exponentiation.md).

### Kitamasa's Method: $O(L^2 \log k)$

A direct polynomial-based method that avoids matrix multiplication.

**Key idea**: Any term $s_n$ can be expressed as $s_n = \sum_{i=0}^{L-1} a_i(n) \cdot s_i$ where the coefficients $a_i(n)$ follow a specific polynomial structure. The polynomial $x^n \bmod C(x)$ (where $C(x) = x^L - c_1 x^{L-1} - \cdots - c_L$) encodes the coefficients.

```
function kitamasa(c, s, k):
    # c = [c_1, c_2, ..., c_L] recurrence coefficients
    # s = [s_0, s_1, ..., s_{L-1}] initial values
    # Compute x^k mod C(x) using binary exponentiation
    result_poly = [1]  # represents x^0
    base_poly = [0, 1]  # represents x^1
    while k > 0:
        if k & 1:
            result_poly = poly_mod(multiply(result_poly, base_poly), C)
        base_poly = poly_mod(multiply(base_poly, base_poly), C)
        k >>= 1
    # result_poly[i] is the coefficient of s_i in the answer
    answer = sum(result_poly[i] * s[i] for i in range(L)) % MOD
    return answer
```

**Complexity**: $O(L^2 \log k)$ (each polynomial multiplication and mod is $O(L^2)$, and there are $O(\log k)$ iterations). With FFT-based polynomial operations: $O(L \log L \log k)$.

### Berlekamp-Massey + Kitamasa Combination

In competitive programming, a common pattern is:
1. Given a sequence, run Berlekamp-Massey to find the minimal recurrence ($O(n^2)$ or $O(n \log n)$).
2. Use the recurrence + Kitamasa to compute the $k$-th term ($O(L^2 \log k)$).

This handles problems where the recurrence is not given but must be discovered.

> **Interview Angle**: "Given the first 20 terms of a sequence defined by an unknown linear recurrence, find the $10^{18}$-th term." Answer: (1) Berlekamp-Massey to find the recurrence, (2) Kitamasa to compute the distant term. Total: $O(L^2 \log k)$ where $L$ is the recurrence order.

---

## Comparison Table

| Technique | Problem | Complexity | Notes |
-----------|---------|------------|-------|
| FFT (complex) | Polynomial mult. | $O(n \log n)$ | Floating-point, power-of-2 |
| NTT | Polynomial mult. | $O(n \log n)$ | Exact, needs suitable prime |
| Bluestein | Arbitrary-length mult. | $O(n \log n)$ | 3x FFT overhead |
| Newton's method | FPS inverse/sqrt/exp/ln | $O(n \log n)$ | Iterative doubling |
| Multipoint eval | Evaluate at $m$ points | $O(n \log^2 n)$ | Product + remainder tree |
| Interpolation | Reconstruct from points | $O(n \log^2 n)$ | Dual of multipoint eval |
| Berlekamp-Massey | Find linear recurrence | $O(n^2)$ or $O(n \log n)$ | LFSR synthesis |
| Kitamasa | $k$-th term of recurrence | $O(L^2 \log k)$ | Better than $O(L^3 \log k)$ matrix |
| Matrix exp. | $k$-th term of recurrence | $O(L^3 \log k)$ | Simple but slower for large $L$ |

## Further Reading

- [Ch 167: FFT/NTT](../chapters/ch167-fft-ntt.md) — FFT/NTT fundamentals
- [Ch 171: Berlekamp-Massey](../chapters/ch171-berlekamp-massey.md) — BM algorithm basics
- [fft-and-polynomial.md](../chapters/fft-and-polynomial.md) — polynomial operations
- [Ch 174: Matrix Exponentiation](../chapters/ch174-matrix-exponentiation.md) — matrix method for recurrences
- Herbert S. Wilf, *generatingfunctionology* — the standard generating functions reference
