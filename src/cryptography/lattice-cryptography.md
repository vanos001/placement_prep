# Lattice Cryptography Foundations

Lattice cryptography is the family of cryptographic schemes whose security reduces to the hardness of *worst-case* problems on high-dimensional lattices. It is the substrate of NIST's primary post-quantum standards (ML-KEM, ML-DSA) and the active research substrate for the past 20 years. This page covers the geometry of lattices, the central hard problems (SVP, CVP, GapSVP, SIVP), the two average-case distributions that drove the field (SIS and LWE), the worst-case to average-case reductions of Regev (2005) and Ajtai (1996), the Ring/Module variants, and why lattices are *still* believed hard for quantum computers.

## What Is a Lattice?

A lattice `Λ` is a discrete subgroup of `R^n`. Equivalently, it is the set of integer linear combinations of a set of linearly independent vectors `B = {b_1, ..., b_k}`:

```
Λ = {  Σ a_i · b_i   :   a_i ∈ Z  }

            ⎡ |  |     |   ⎤       ⎡ b_1,1 ⋯ b_1,n ⎤
   B   =    ⎢ b_1 b_2 ⋯ b_k ⎥  =    ⎢ ⋮    ⋱  ⋮    ⎥
            ⎣ |  |     |   ⎦       ⎣ b_k,1 ⋯ b_k,n ⎦
```

The matrix `B ∈ R^(n × k)` is a *basis* of the lattice; `k` is the *rank*. If `k = n`, the lattice is *full-rank*. Every lattice has infinitely many bases — they are related by right-multiplication by a unimodular integer matrix `U ∈ GL_k(Z)` (so `det(U) = ±1`). The *determinant* `det(Λ) := |det(B)|` is basis-invariant.

```
    2D lattice example:
                                       ●
                       ●        ●
                              ●
                ●                              ●
   origin ● ─────────●─────────●─────────●──────────► b_1 axis
                       ●        ●
                              ●
                                       ●
                       ●        ●
                              ●
                              ▲
                              └──► b_2 axis
```

The shortest nonzero vector in `Λ` is the *first successive minimum* `λ_1(Λ)`. The successive minima `λ_1, λ_2, ..., λ_n` are the radii of the smallest balls containing `i` linearly independent lattice vectors.

## The Hard Problems

### Shortest Vector Problem (SVP)

Given a basis `B` for `Λ`, find `v ∈ Λ \ {0}` with `‖v‖ = λ_1(Λ)`.

SVP is NP-hard under randomized reductions (Ajtai 1998 — via GapSVP, which is the approximation variant). The decisional version (GapSVP): given `B` and `d`, distinguish `λ_1 ≤ d` from `λ_1 ≥ γ·d` for an approximation factor `γ`.

### Closest Vector Problem (CVP)

Given `B` and a target `t ∈ R^n`, find `v ∈ Λ` with `‖t - v‖` minimal. CVP is at least as hard as SVP.

### Shortest Independent Vectors Problem (SIVP)

Given `B`, find `n` linearly independent `v_1, ..., v_n ∈ Λ` with `max(‖v_i‖) ≤ γ·λ_n(Λ)`. SIVP is the problem that the LWE reduction ultimately starts from.

### Short Integer Solution (SIS)

*Average-case* problem (Ajtai 1996). Given `A ∈ Z_q^(n × m)` (uniformly random with `m > n log q`), find *nonzero* `z ∈ Z^m` such that:

```
A · z ≡ 0   (mod q)
‖z‖_∞ ≤ β    (or some other norm bound)
```

SIS is hard *on average* for random `A`. Ajtai's theorem: solving SIS on average is at least as hard as approximating SIVP on *worst-case* lattices with approximation factor `γ = Õ(n)`.

### Learning With Errors (LWE)

Regev (2005). Given `A ∈ Z_q^(m × n)` and `b = A·s + e mod q` where `s ∈ Z_q^n` is a uniform secret and `e ∈ Z_q^m` has small coefficients (each drawn from an error distribution `χ`, typically a discrete Gaussian), recover `s`. The decisional version: distinguish `(A, b = A·s + e)` from `(A, u)` with `u` uniform.

LWE is *average-case* hard. Regev's theorem (next section) gives the worst-case reduction.

## Regev's Worst-Case to Average-Case Reduction

Theorem (Regev 2005): *If there exists a polynomial-time algorithm that solves decisional LWE for secret distribution uniform in `Z_q^n` and error distribution `D_{αq}` (a discrete Gaussian with width `αq < q`), then there exists a quantum algorithm that solves GapSVP_γ and SIVP_γ on every `n`-dimensional lattice with `γ = Õ(n/α)` in polynomial time.*

Sketch of the reduction (each arrow is a reduction; the lower arrow is *quantum*):

```
   GapSVP_γ  on  ⎯⎯⎯⎯⎯⎯⎯⎯⎯►  worst-case
   SIVP_γ     ⎯⎯⎯⎯⎯⎯⎯⎯⎯►  lattice problem
                 ⬇   (Regev: with a quantum step — solve a lattice problem via LWE)
                 ⬇
                 ⬇
   LWE_{n,q,α}  average-case   ←—— if we can solve this on average, we get
                                    a quantum worst-case solver above
```

The quantum step is the *decisional* piece: given the ability to solve LWE in the average case, Regev constructs a quantum circuit that, with one call to the LWE solver, decides GapSVP / SIVP. This is the *only* quantum step in the chain — classical reductions carry the rest.

The reduction goes via the "discrete Gaussian sampling" primitive: the algorithm picks a Gaussian sample near a lattice point; this is the *same* primitive that the BKZ 2.0 lattice-reduction algorithm uses internally, and its quantum speedup (via amplitude amplification) is what makes the reduction go through.

### Implications

1. **No "structured" weakness.** LWE is hard on average *if and only if* the worst-case lattice problems are hard. There is no "structured" lattice family that is easy.
2. **No classical attack shortcuts.** Even if classical algorithms improved on GapSVP/SIVP, LWE would remain hard up to that improvement.
3. **Quantum attack would need to beat lattice problems.** A *quantum* algorithm that solves LWE directly would imply a *quantum* algorithm for worst-case lattice problems, which is the central open question.

## Ring-LWE and Module-LWE

### Ring-LWE (Lyubashevsky, Peikert, Regev 2010)

The plain-LWE public key `(A, b)` with `A ∈ Z_q^(n × n)` has size `O(n² log q)`. For `n = 256, q = 3329`, that's 256²·12 ≈ 770 KB — far too large for practical use.

Ring-LWE shrinks the matrix `A` to a single ring element `a ∈ R_q := Z_q[X]/(f(X))` for some monic irreducible `f` of degree `n`. The sample becomes `(a, b = a·s + e mod q)` with `s, e ∈ R_q` small. The key is `O(n log q)` integers.

The catch: Ring-LWE's hardness reduces to *ideal-lattice* problems (worst-case on ideal lattices of `R`), which are slightly *stronger* assumptions than worst-case over all lattices. The Ring-LWE reduction (LPR10) is to approximate-SVP on ideal lattices of `R`.

### Module-LWE (Langlois-Regev 2012)

Module-LWE interpolates between Ring-LWE and plain LWE. The matrix `A` becomes a `k × k` matrix of ring elements, and the secret `s, e` become `k`-vectors of ring elements. The public-key size is `O(k²·n log q)` — quadratic in `k` but linear in `n`. Picking `k = 2, 3, 4` lets you scale security while keeping the same ring.

The Module-LWE hardness reduction (Langlois-Regev 2012) is to *plain* LWE in the same ring — *not* to ideal-lattice problems. This is the structural reason ML-KEM uses Module-LWE rather than Ring-LWE: it gives a security story closer to the original Regev reduction.

### Why `X^256 + 1`?

The polynomial `X^256 + 1` is *cyclotomic* (it is the 512th cyclotomic polynomial `Φ_512(X)`). Cyclotomic rings have:

- A fast *Number-Theoretic Transform* (the analog of FFT in `Z_q`) — `q ≡ 1 mod 2n` admits a primitive `2n`-th root of unity.
- Clean algebraic structure that simplifies the security proof.
- Self-duality: the negacyclic convolution `X^256 ≡ -1 mod (X^256 + 1)` makes the convolution well-behaved.

For Kyber, `q = 3329 ≡ 1 mod 256`, which permits a 256-element NTT. For Dilithium, `q = 8380417 = 2^23 - 2^13 + 1 ≡ 1 mod 256` similarly.

## The Best Known Attack: BKZ

Lattice reduction algorithms try to find short vectors in a given basis. The most-used is **BKZ** (block-Korkine-Zolotarev) introduced by Schnorr-Euchner 1994, refined as BKZ 2.0 by Chen-Nguyen 2011.

```
                BKZ block size β vs. log_2 cost
                ─────────────────────────────────
                β = 60    →  ~2^40  ops  (toy instances)
                β = 100   →  ~2^80  ops
                β = 200   →  ~2^140 ops
                β = 400   →  ~2^280 ops
                β = 560   →  ~2^385 ops  (Kyber-768 claim)
                β = 800   →  ~2^550 ops  (Dilithium-87 claim)
```

The "core-SVP" model (Becker et al., ASIACRYPT 2016) counts single-call operations of the *sieving subroutine* in BKZ: the cost of a single SVP call in dimension `β` is `2^0.292·β` (classical) or `2^0.265·β` (quantum, using Grover for the inner search). This is the basis of the security estimates in the FIPS 203 and FIPS 204 specs.

### BKZ: an outline

```
input:  a basis B = {b_1, ..., b_n}
output: a basis whose Gram-Schmidt lengths {‖b_i*‖} are nearly geometric
        (this is what "reduced" means in lattice theory)

repeat until converged:
  for i in 1..n - block_size + 1:
    sub = {b_i, ..., b_{i+block_size-1}}
    sub = ExactSVP(sub)                    ← exponential in block_size
    for j in i..i+block_size-1:
      B = size_reduce(B, j)                 ← polynomial
```

The cost is dominated by the ExactSVP calls. Modern BKZ uses **sieving** (the General Sieve Kernel, G6K; see eprint 2019/1111) for the SVP oracle; this is what produces the `2^0.292·β` count.

## The Quantum Question

There is no *known* polynomial-time quantum algorithm for SVP/SIVP/GAP-SVP/CVP on general lattices. The best quantum algorithms are:

- **Grover + best classical SVP**: gives a quadratic speedup on the sieving subroutine (reducing `2^0.292·β` to `2^0.265·β`). The security estimators in FIPS 203/204 *do* account for this — the post-quantum security level is computed *after* the Grover speedup.
- **Kuperberg's algorithm** on hidden-shift (if a particular *structured* lattice has a hidden-shift symmetry) — this is the basis for the *only* known subexponential attacks, which apply to *some* (not all) ideal-lattice problems with algebraic structure (specifically primal-RLWE over cyclotomic rings of certain smooth orders).

There is no known subexponential quantum algorithm for **Module-LWE** or **Module-SIS** with `q` prime and the standard parameter regimes used in ML-KEM / ML-DSA. The belief that lattice problems resist quantum attack rests on this:

1. The reductions Regev 2005 + Langlois-Regev 2012 show that breaking average-case LWE gives a quantum algorithm for *worst-case* lattice problems.
2. After 30 years of effort, no subexponential quantum algorithm for SVP / SIVP is known.
3. The *worst-case* lattice problems have no "structured" instances in the relevant regime that admit shortcuts.

### What *could* break lattice crypto

Hypothetical future attacks that would weaken the lattice story:

1. A subexponential quantum algorithm for SVP / SIVP / GapSVP on general lattices.
2. A subexponential attack on Module-LWE / Module-SIS via algebraic structure (e.g., a polynomial-time NTRU-style attack on ideal lattices extended to module lattices).
3. An improvement to BKZ-block-size-vs-cost beyond `2^0.265·β` (currently this is `2^0.207·β` conjectured for a new "lattice sieving with hypercube" framework, still exponential).
4. Better lattice reduction beyond BKZ 2.0 (active research area; e.g., LLL-style algorithms in the average case).

This is why NIST standardized *multiple* PQC families (lattice, hash, code) — defense in depth.

## Worked Example: LWE in Dimension 2

Let `q = 17, n = 2, m = 4`. Generate `A, s, e`:

```
A = ⎡ 5  3 ⎤     s = ⎡ 1 ⎤     e = ⎡ 1 ⎤
    ⎢ 7  1 ⎥         ⎢   ⎥         ⎢-1⎥
    ⎢ 2  9 ⎥         ⎣ 0 ⎦         ⎢ 0⎥
    ⎣ 4  6 ⎦                      ⎣ 1⎦
                                      (mod 17)
b = A·s + e = ⎡5·1 + 3·0 + 1 ⎤ = ⎡ 6 ⎤
              ⎢7·1 + 1·0 - 1 ⎥   ⎢ 6 ⎥
              ⎢2·1 + 9·0 + 0 ⎥   ⎢ 2 ⎥   (mod 17)
              ⎣4·1 + 6·0 + 1 ⎦   ⎣ 5 ⎦
```

Public: `(A, b)`. Secret: `s = (1, 0)`. To recover `s` *without* the error `e`, you'd solve `A·s = b mod 17`, which is `s = A⁻¹·b mod 17` — easy. With the error added (here `e = (1, -1, 0, 1)`, three of four components nonzero), the system is over-determined AND inconsistent — the error turns the linear system into a noisy one, and recovering `s` requires solving a closest-vector problem (CVP), which is NP-hard in general.

The whole of lattice cryptography is just: "what's the largest `n`, smallest `q`, smallest error width `α` such that recovering `s` from `(A, A·s + e)` is intractable?"

## Summary: Why Lattices Resist Quantum

| Property | Consequence |
|----------|-------------|
| Worst-case to average-case reduction (Regev 2005, Langlois-Regev 2012) | No "easy structured" lattice instances; if LWE is weak, all lattices are weak |
| No known subexponential quantum attack on SVP / SIVP | Quantum advantage over classical is bounded to a quadratic (Grover) factor |
| Core-SVP cost model accounts for the Grover speedup | FIPS 203/204 security claims are *post-quantum* by construction |
| Best practical attack: BKZ 2.0 with G6K sieving | Cost `2^0.292·β` classical, `2^0.265·β` quantum, on a single SVP call in dimension β |
| 30+ years of cryptanalysis with no polynomial breakthrough | Long track record; lattice problems are believed fundamentally hard |

## References

- Regev, *On Lattices, Learning with Errors, Random Linear Codes, and Journaling*, JACM 2009; STOC 2005 — https://cseweb.ucsd.edu/~daniele/papers/LWEJ.pdf
- Ajtai, *Generating Hard Instances of Lattice Problems*, STOC 1996 — https://www.cs.sjsu.edu/faculty/pollett/271-F2007/Notes/ajtai.pdf and follow-up: Ajtai, *The Shortest Vector Problem in L_2 is NP-hard for Randomized Reductions*, STOC 1998 — https://doi.org/10.1145/276698.276705
- Lyubashevsky, Peikert, Regev, *On Ideal Lattices and Learning with Errors over Rings*, JACM 2013; EUROCRYPT 2010 — https://eprint.iacr.org/2012/230
- Langlois, Regev, *Worst-case to Average-case Reductions for Module-Lattices*, J. Math. Crypt. 2014 — https://eprint.iacr.org/2012/506
- Peikert, *A Decade of Lattice Cryptography*, Foundations and Trends in TCS 2016 — https://eprint.iacr.org/2015/939
- Micciancio, Regev, *Lattice-based Cryptography*, in *Post-Quantum Cryptography* (Bernstein-Buchmann-Dahmen Eds.), Springer 2009 — https://cseweb.ucsd.edu/~daniele/LatticeSurvey/
- Chen, Nguyen, *BKZ 2.0: Better Lattice Security Estimates*, ASIACRYPT 2011 — https://www.iacr.org/archive/asiacrypt2011/70730119/70730119.pdf
- Becker, Ducas, Laarhoven, *The General Sieve Kernel and New Records in Lattice Reduction*, ASIACRYPT 2016 (G6K) — https://eprint.iacr.org/2019/1111
- Aggarwal, Joux, Prakash, Santha, *A New Public-Key Cryptosystem via Mersenne Numbers*, CRYPTO 2018 (sieving costs discussion) — https://eprint.iacr.org/2017/1038
- Peikert, *Lattice Cryptography for the Internet*, PQCrypto 2014 (CCA-secure KEM from Ring-LWE) — https://eprint.iacr.org/2014/070
- Alkim, Ducas, Pöppelmann, Schwabe, *Post-quantum Key Exchange — A New Hope*, USENIX Security 2016 (the first real-world Ring-LWE deployment) — https://eprint.iacr.org/2015/1092
- Kuperberg, *Subexponential-Time Quantum Algorithm for the Hidden Subgroup Problem*, J. Algorithms 2005 — https://www.scottaaronson.com/papers/kuperberg.pdf (the hidden-shift algorithm motivating cyclotomic-ring concerns)
- The Lattice Estimator (Python tool for BKZ cost estimation) — https://github.com/malb/lattice-estimator

## Interview Questions

1. **Define a lattice. What is the determinant of a lattice, and why is it basis-invariant?**
2. **State the SVP, CVP, and SIVP problems. Which is hardest, and which is the one that the LWE reduction ultimately starts from?**
3. **Explain Regev's worst-case to average-case reduction. What is the role of the quantum step?**
4. **What does the core-SVP cost model say about the cost of a single SVP call in dimension β, both classically and quantumly?**
5. **Why is the cyclotomic polynomial `X^256 + 1` chosen for Ring/Module-LWE? What property of `q = 3329` is needed for the NTT?**
6. **Contrast Ring-LWE, Module-LWE, and plain LWE: in security reduction, public-key size, and parameter scaling.**
7. **What is BKZ? What does "block size" mean, and what is the relationship between block size and security?**
8. **Could a future quantum algorithm break lattice cryptography? What would it have to do?**
9. **Why does lattice cryptography survive Grover's algorithm when RSA does not survive Shor's?**
10. **Explain what "worst-case to average-case reduction" buys you that other PQC families (e.g., code-based, multivariate) do not have.**
