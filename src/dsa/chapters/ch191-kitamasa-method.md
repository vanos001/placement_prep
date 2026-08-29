# The Kitamasa Method: Linear Recurrences Without Matrix Exponentiation

Given an order-k linear recurrence `a_n = c_1 a_(n-1) + ... + c_k a_(n-k)`, matrix
exponentiation (Chapter 174) computes `a_n` in `O(k^3 log n)` via the companion
matrix. The Kitamasa method instead raises the polynomial `x` to the n-th power
**modulo the characteristic polynomial**: `O(k^2 log n)` with schoolbook
polynomial multiplication, `O(k log k log n)` with FFT/NTT. This page works out
the identity behind the substitution, exact step counts, and failure modes.

## Replace the Matrix With a Remainder

Work in the quotient ring `R[x]/(f(x))`, where `f` is the characteristic
polynomial of the recurrence. Inside the ring, its definition becomes:

```text
f(x) = x^k - c_1 x^(k-1) - c_2 x^(k-2) - ... - c_k

reduction rule:   x^k = c_1 x^(k-1) + c_2 x^(k-2) + ... + c_k
```

This is the same shift-operator rule that the companion matrix of Chapter 174
encodes in matrix form; we simply never build the matrix. The claim is:

> **Theorem.** Let `r(x) = r_0 + r_1 x + ... + r_(k-1) x^(k-1)` be the remainder of
> `x^n` modulo `f(x)`. Then `a_n = r_0 a_0 + r_1 a_1 + ... + r_(k-1) a_(k-1)`.

```text
Proof. Define phi(g) = sum_i g_i * a_i (dot the coefficients with the initial terms).
1. phi(x^j * f) = a_(j+k) - c_1 a_(j+k-1) - ... - c_k a_j = 0  for every j >= 0:
   that expression is exactly the recurrence defining a_(j+k).
2. By linearity phi vanishes on every multiple of f, so phi is constant on
   residue classes modulo f.
3. Induction on n. For n >= k:
   a_n = c_1 a_(n-1) + ... + c_k a_(n-k)          (recurrence definition)
       = phi( c_1 x^(n-1) + ... + c_k x^(n-k) )   (induction + step 2)
       = phi( x^n mod f ).                        (differs by x^(n-k)*f; step 2)
```

## A Hand Check With Fibonacci

`F(n) = F(n-1) + F(n-2)`, `F(0) = 0`, `F(1) = 1`, so `f(x) = x^2 - x - 1` and the
reduction rule is `x^2 = x + 1`. Reducing `x^n` by hand:

| n  | x^n mod (x^2 - x - 1) | dot with (F(0), F(1)) = (0, 1) | F(n) |
|----|-----------------------|--------------------------------|------|
| 0  | 1                     | 0                              | 0    |
| 1  | x                     | 1                              | 1    |
| 2  | 1 + x                 | 1                              | 1    |
| 3  | 1 + 2x                | 2                              | 2    |
| 4  | 2 + 3x                | 3                              | 3    |
| 5  | 3 + 5x                | 5                              | 5    |

The remainder regenerates the sequence in its own coefficients: for `n >= 1`,
`x^n = F(n-1) + F(n) * x`, so `a_n` is the coefficient of `x` in the remainder --
a special case of the theorem, since the initial vector (0, 1) picks it out.

## The Algorithm: Square-and-Shift in R[x]/(f)

Computing `x^n mod f` is plain MSB-first binary exponentiation: square `r` for
every bit of n, and for every set bit also multiply by `x` (shift up one degree
and fold the top coefficient), starting from `r = 1`. Exact step counts, which
the demo verifies: `bit_length(n)` squarings -- one of them squares the seed
`1` -- and `popcount(n)` shifts. Schoolbook costs:

- Square: `k^2` multiplications for the product plus at most `(k-1) * k` to fold
  coefficients of degree `>= k` back down (synthetic division, top degree first):
  under `2k^2` per step. Shift: one multiplication by each `c_i`, i.e. `O(k)`.
- Total: `O(k^2 log n)` modular multiplications, `O(k)` stored coefficients;
  with NTT multiplication the step becomes `O(k log k)`, i.e. `O(k log k log n)`.

## The Cost Ledger

| Approach                     | Per step   | Total            | Requirements                        |
|------------------------------|------------|------------------|-------------------------------------|
| Iterate the recurrence       | O(k)       | O(n)             | none; viable only for small n       |
| Matrix exponentiation        | O(k^3)     | O(k^3 log n)     | any linear transition               |
| Kitamasa, schoolbook mulmod  | O(k^2)     | O(k^2 log n)     | monic characteristic polynomial     |
| Kitamasa, NTT/FFT mulmod     | O(k log k) | O(k log k log n) | NTT-friendly modulus or 3-prime CRT |
| Bostan-Mori (2021)           | ~2 M(k)    | O(M(k) log n)    | field (exact division)              |

Here `M(k)` is one polynomial multiplication. With `n = 10^18` (60 bits):

- `k = 100`: matrix ~ `100^3 * 60 = 6.0 * 10^7` multiplications vs schoolbook
  Kitamasa ~ `100^2 * 60 = 6.0 * 10^5`: one hundred times less, with `O(k)`
  memory instead of `O(k^2)`.
- `k = 1000`: `6.0 * 10^10` vs `6.0 * 10^7`; the NTT route does ~
  `1000 * 10 * 60 = 6.0 * 10^5` butterfly-scale work. The matrix route loses;
  this is the regime the method was built for.

Fiduccia's 1985 analysis costs this exact algorithm
`3 M(d) floor(log N) + O(d log N)` ring operations; Bostan-Mori reduce the
constant to about `2 M(d) log N` by transposing the algorithm so the order halves
each level (1.625x faster in the FFT model). The asymptotic class is unchanged.

## Runnable Demo: F(10^6) mod 1e9+7

Order `k = 2`, schoolbook mulmod, cross-checked against fast doubling. Pure Python stdlib.

```python
# Kitamasa (polynomial exponentiation) vs fast doubling for Fibonacci (k = 2).
# a_n = a_{n-1} + a_{n-2}, a_0 = 0, a_1 = 1; f(x) = x^2 - x - 1 -> x^2 = x + 1.
# Pure Python stdlib only.

MOD = 10**9 + 7
C1, C2 = 1, 1  # x^2 = C1*x + C2

def mulmod(a, b, mod):
    # product of two degree-<2 polys, then fold x^2 back down (O(k^2) in general)
    p0 = (a[0] * b[0]) % mod
    p1 = (a[0] * b[1] + a[1] * b[0]) % mod
    p2 = (a[1] * b[1]) % mod
    return [(p0 + p2 * C2) % mod, (p1 + p2 * C1) % mod]   # stored [const, x-coeff]

def shift1(a, mod):
    # multiply by x in R[x]/(f): r0*x + r1*x^2 -> r1*C2 + (r0 + r1*C1)*x; O(k)
    return [(a[1] * C2) % mod, (a[0] + a[1] * C1) % mod]

def kitamasa_fib(n, mod):
    # MSB-first square-and-shift; F(n) is the x-coefficient of x^n mod f
    r = [1, 0]
    squares = shifts = 0
    for i in range(n.bit_length() - 1, -1, -1):
        r = mulmod(r, r, mod); squares += 1
        if (n >> i) & 1:
            r = shift1(r, mod); shifts += 1
    return r, squares, shifts

def fib_fast_doubling(n, mod):
    def fd(n):
        if n == 0:
            return (0, 1)
        a, b = fd(n >> 1)
        c = (a * ((2 * b - a) % mod)) % mod
        d = (a * a + b * b) % mod
        return (d, (c + d) % mod) if n & 1 else (c, d)
    return fd(n)[0]

N = 10**6
r, squares, shifts = kitamasa_fib(N, MOD)
kit, fd = r[1] % MOD, fib_fast_doubling(N, MOD)
small_ok = all(kitamasa_fib(n, MOD)[0][1] == fib_fast_doubling(n, MOD) for n in range(30))

print("n                  = %d" % N)
print("modulus            = %d" % MOD)
print("bit_length(n)      = %d   -> squarings = bit_length" % N.bit_length())
print("squarings          = %d" % squares)
print("x-shifts           = %d   (popcount(%d) = %d)" % (shifts, N, bin(N).count("1")))
print("reduced poly       = %d + %d*x   (x^n mod (x^2 - x - 1))" % (r[0], r[1]))
print("kitamasa F(n)      = %d" % kit)
print("fast-doubling F(n) = %d" % fd)
print("match              = %s" % (kit == fd))
print("agree n = 0..29    = %s" % small_ok)
```

```text
n                  = 1000000
modulus            = 1000000007
bit_length(n)      = 20   -> squarings = bit_length
squarings          = 20
x-shifts           = 7   (popcount(1000000) = 7)
reduced poly       = 616309404 + 918091266*x   (x^n mod (x^2 - x - 1))
kitamasa F(n)      = 918091266
fast-doubling F(n) = 918091266
match              = True
agree n = 0..29    = True
```

The step counts confirm the ledger: 20 squarings = `bit_length(10^6)`, 7 shifts
= `popcount(10^6)`; `F(10^6)` is the x-coefficient of the reduced polynomial.

## Off-By-Ones and Failure Modes

- **Which coefficient is the answer.** Not "the top coefficient": it is the dot
  product of the whole remainder with `a_0 ... a_(k-1)`. For Fibonacci the
  x-coefficient works only because the initial vector is (0, 1).
- **Sign convention.** If the recurrence is written
  `a_n + d_1 a_(n-1) + ... + d_k a_(n-k) = 0`, then `c_i = -d_i`; deriving the
  reduction rule directly from the recurrence avoids the flip.
- **Reduce after every shift.** Multiplying by `x` must fold the escaped top
  coefficient immediately. A first draft of the demo's `shift1` swapped the
  constant and x-coefficients and produced `match = False`; a wrong reduction
  rule yields plausible garbage, not crashes, so keep an independent check.
- **Modulus choice.** Schoolbook mulmod needs no inverses, so any modulus works --
  a real advantage over Berlekamp-Massey and Bostan-Mori, which need a field.
  The NTT route wants a prime such as 998244353; for 1e9+7 use three NTT primes
  with CRT, or split coefficients low/high for floating-point FFT (products sum
  up to k terms of size up to (m-1)^2; mind the error bound).
- **One term per run.** The algorithm returns a single `a_n`. For a window
  `a_N ... a_(N+k-1)`, repeat per index or use the Bostan-Mori MSB-first variant,
  which returns a slice of consecutive terms in one pass.
- **Wrong polynomial.** Reduce by the polynomial of the recurrence you actually
  want. A minimal polynomial recovered by Berlekamp-Massey (Chapter 171) is
  valid too -- it divides the characteristic polynomial, so remainders only
  get shorter.

## Provenance: The Name and the Published Record

"Kitamasa method" is competitive-programming folklore naming: community tutorials
(Justice_Hui, demoralizer) teach it under this label, and KACTL ships it as
`LinearRecurrence.h`, header comment "Faster than matrix multiplication", time
`O(n^2 log k)`. The scholarly record contradicts the folklore's "Kitamasa, 1967"
attribution: no such journal paper is verifiable in any index consulted, and the
Bostan-Mori bibliography (the modern reference on this problem) never mentions
the name. What the record does contain:

- C. M. Fiduccia: "The n-th power of a companion matrix" (Allerton, 1982), then
  "An efficient formula for linear recurrences", SIAM J. Comput. 14(1):106-112,
  1985 (DOI 10.1137/0214008) -- the polynomial remainder method in full; it
  computes u_N as the inner product of `x^N mod Gamma(x)` with the initial
  vector. Bostan-Mori call it the state of the art from 1985 onward, and note
  D. Knuth sketched the same idea in 1981 TAOCP corrections, crediting R. Brent.
- A. Bostan and R. Mori, "A Simple and Fast Algorithm for Computing the N-th
  Term of a Linearly Recurrent Sequence", FPSAC 2021; preprint arXiv:2008.08822:
  the ~2 M(d) log N improvement and applications to polynomial modular
  exponentiation, matrix powering, and high-order lifting.

For interviews, the honest framing: "the polynomial exponentiation method (often
called Kitamasa in competitive programming; published as Fiduccia's algorithm)".

## Practice Ladder

1. Reimplement the demo from scratch, then compute `F(10^18) mod 998244353`.
2. Recover an order-100 recurrence from 200 terms (Berlekamp-Massey), then
   compute `a_(10^18)` schoolbook.
3. Derive fast doubling by squaring `x^n = F(n-1) + F(n) x` in `R[x]/(x^2-x-1)`
   -- the two algorithms are the same object at different heights.
4. Count length-`10^18` walks on an order-50 transition via Chapter 174 and via
   Kitamasa; compare operation counts.

## Cross-References

- [Chapter 174: Matrix Exponentiation](./ch174-matrix-exponentiation.md) -- the O(k^3 log n) baseline this method undercuts.
- [Chapter 171: Berlekamp-Massey](./ch171-berlekamp-massey.md) -- recover the recurrence and a minimal polynomial from observed terms.
- [Chapter 167: FFT and NTT](./ch167-fft-ntt.md) -- fast polynomial multiplication, turning the O(k^2) step into O(k log k).
- [Polynomials and Generating Functions](../advanced/polynomials.md) -- generating-function view and a survey-level Kitamasa section.

## References

1. Justice_Hui, "[Tutorial] Easy Introduction to Kitamasa Method", Codeforces blog entry 88760. <https://codeforces.com/blog/entry/88760> (HTTP 200)
2. demoralizer, "[Tutorial] Solving Linear Recurrences with various methods, Including O(N logN logK) using FFT", Codeforces blog entry 97627. <https://codeforces.com/blog/entry/97627> (HTTP 200)
3. KACTL, `LinearRecurrence.h` (L. Bicsi), KTH Competitive Programming Template Library. <https://github.com/kth-competitive-programming/kactl/blob/main/content/numerical/LinearRecurrence.h> (HTTP 200)
4. A. Bostan and R. Mori, "A Simple and Fast Algorithm for Computing the N-th Term of a Linearly Recurrent Sequence", FPSAC 2021. Preprint <https://arxiv.org/abs/2008.08822> (HTTP 200); published version <https://mathexp.eu/bostan/publications/BoMo21.pdf> (HTTP 200)
5. C. M. Fiduccia, "An efficient formula for linear recurrences", SIAM J. Comput. 14(1):106-112, 1985, DOI 10.1137/0214008. <https://doi.org/10.1137/0214008> (DOI resolves via HTTP 302; publisher page returns 403 to non-browser clients)
6. cp-algorithms, "Fibonacci Numbers" (fast doubling). <https://cp-algorithms.com/algebra/fibonacci-numbers.html> (HTTP 200)
7. Nayuki, "Fast Fibonacci algorithms". <https://www.nayuki.io/page/fast-fibonacci-algorithms> (HTTP 200)
8. Wikipedia, "Constant-recursive sequence". <https://en.wikipedia.org/wiki/Constant-recursive_sequence> (HTTP 200)
