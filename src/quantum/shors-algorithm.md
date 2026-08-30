# Shor's Algorithm: Factoring via Quantum Order Finding

Shor's algorithm (FOCS 1995; journal version [Shor 1997]) factors an n-bit integer N in time polynomial in n on a quantum computer -- the one known result that takes widely deployed public-key cryptosystems (RSA, Diffie-Hellman, ECC) from "hard" to "broken in principle." The quantum part of the algorithm does exactly one thing: it finds the order of a number modulo N using the quantum Fourier transform. Everything else -- gcds, continued fractions, verification -- is classical number theory. This page works the full pipeline: the factoring-to-order-finding reduction, phase estimation on the modular-multiplication unitary U|y> = |xy mod N>, why modular exponentiation dominates the gate count, published resource estimates for RSA-2048, and an honest account of what hardware has actually factored (15 and 21, compiled). Prerequisites: gates and phase estimation warmups in [Quantum Fundamentals](quantum-fundamentals.md); the exponential-vs-quadratic speedup contrast with [Grover's Search](grovers-search.md).

## Factoring reduces to order finding

Given an odd composite N, pick a random a with 2 <= a <= N-2:

```text
 pick random a in [2, N-2]
        |
 gcd(a, N) > 1 ? --yes--> done: g = gcd(a, N) is a factor (classical luck)
        | no (a is coprime to N)
 quantum: find r = the order of a mod N      <-- the ONLY quantum step
        |
 r odd, or a^(r/2) = -1 (mod N) ? --yes--> rerun with a fresh a
        | no
 gcd(a^(r/2) - 1, N) and gcd(a^(r/2) + 1, N) --> nontrivial factor of N
```

Why this works: if r is the order of a mod N, then a^r = 1 (mod N), so

```text
 a^r - 1 = (a^(r/2) - 1) * (a^(r/2) + 1)  =  0 (mod N)
```

N divides the product but divides neither factor alone (a^(r/2) = +1 would contradict minimality of r; a^(r/2) = -1 is the rerun case). Since N is an odd composite with at least two prime factors, each gcd above must pick up a strict subset of them -- a nontrivial factor. For an RSA-style modulus N = p*q, at least half of the coprime choices of a land in the good case, so a constant expected number of reruns suffices (the number theory is worked out in [Nielsen & Chuang, Appendix 4] and in the [Ekert-Jozsa survey]).

Worked micro-example, N = 21, a = 2: 2^6 = 64 = 1 (mod 21) and no smaller positive exponent works, so r = 6. Then 2^3 = 8, gcd(8-1, 21) = 7 and gcd(8+1, 21) = 3: the factors 7 and 3. The whole trick is computing r.

Classically, order finding is no easier than factoring: factor N and you can compute the order of any a from the factorizations of p-1 and q-1; conversely the reduction above turns an order-finding oracle into a factoring machine. The two problems stand or fall together, and the best classical methods (the general number field sieve) are subexponential, not polynomial. What the quantum computer changes is that order finding, hard classically, is polynomial quantum mechanically.

## Quantum order finding: phase estimation on U|y> = |xy mod N>

Fix a coprime to N and define U_a|y> = |a*y mod N>. U_a is a permutation of the n-qubit basis states; on each orbit of the map y -> a*y it cycles with period r, so its eigenstates are orbit superpositions with eigenvalues e^(2*pi*i*s/r), s = 0 .. r-1. The phases s/r encode the order. Quantum phase estimation (QPE) reads them out:

```text
   m ~ 2n phase qubits                        n work qubits (values mod N)
  |0> --H--H--...--H--o------o---------o------ inverse QFT -- measure c
                      |      |         |      (m qubits)    c ~ s*2^m/r
  |1> ----------------U^1----U^2---U^(2^(m-1))---------
        U^(2^j) multiplies the work register by a^(2^j) mod N
```

The state evolves in three moves:

```text
 1. Hadamards:      (1/sqrt(2^m)) * sum_x |x> |1>
 2. controlled U's: (1/sqrt(2^m)) * sum_x |x> |a^x mod N>
 3. QFT^-1:         period-r structure in x -> peaks at c = s * 2^m / r
```

Step 2 is where the physics does the work: the second register now holds a sequence periodic in x with period r. The inverse QFT over Z_(2^m) turns that periodicity into constructive interference at multiples of 2^m/r -- the same mechanism as any Fourier period detection, executed coherently on a superposition of all x at once. Note the work register starts in |1>, which is not an eigenstate of U_a but a superposition over orbit eigenstates; QPE on such a state samples the eigenphases s/r, which is exactly what we want -- no eigenstate preparation needed.

Two accuracy facts (both from [Nielsen & Chuang, Chapter 5]):

- With probability >= 4/pi^2 ~ 0.405, the measured c satisfies |c/2^m - s/r| <= 1/2^(m+1).
- With m >= 2n phase qubits, distinct fractions s/r (r <= N < 2^n) are separated by more than 1/2^m, so the continued-fraction expansion of c/2^m recovers s/r exactly, in lowest terms.

The classical post-processing is then: expand c/2^m as a continued fraction, walk its convergent denominators q, test k = q, 2q, 3q, ... until a^k = 1 (mod N) -- that k is r, verifiable in microseconds with modular exponentiation. The recovered fraction can be s/r with a common factor g = gcd(s, r) > 1, in which case the convergents return r/g and the small multiples of it; if g is large the run is wasted and you simply rerun. The probability that a random s is coprime to r is phi(r)/r, which decays only like 1/log log r, so the expected number of quantum runs stays constant -- a handful in practice. Total success probability per run is roughly 0.405 * phi(r)/r * P(r even and a^(r/2) != -1) ~ a few tenths: repetition is priced into the algorithm, and every candidate r is checked classically before it is believed.

## Modular exponentiation: the dominant cost

Write n = log2(N). Computing a^x mod N on the superposed exponent x uses square-and-multiply: the controlled U^(2^j) blocks are n-bit modular multiplications by precomputed constants a^(2^j) mod N, giving ~m*n = O(n^2) modular multiplications. Each one is built from reversible adders, comparators and swaps -- [Vedral, Barenco and Ekert (1996)] supply the elementary networks -- costing O(n) to O(n^2) gates apiece. Modular exponentiation therefore lands at O(n^3) gates, while the inverse QFT over m = 2n qubits is only O(n^2) (reducible to O(n log n) with approximation). Arithmetic, not the Fourier transform, is the cost center of Shor's algorithm -- a point people routinely get backwards.

Space is the scarcer resource. [Beauregard (2003)] minimized it and the abstract states the result directly: the circuit "uses 2n+3 qubits and O(n^3 lg(n)) elementary quantum gates in a depth of O(n^3)". Two ideas buy the savings: the exponent is streamed one bit at a time into a single control qubit that is measured immediately (the semiclassical inverse QFT of Griffiths-Niu, which replaces the m-qubit phase register with one recycled qubit), and the modular multiplication is carried out in place with uncomputed ancillas, so the whole circuit fits in 2n+3 qubits. For RSA-2048 (n = 2048) that is 2*2048 + 3 = 4,099 logical qubits -- before any error correction.

## Resource estimates for RSA-2048

Only numbers traceable to the cited papers appear below:

| Estimate (source)                            | Circuit model                | Logical cost                    | Full-machine estimate              |
|----------------------------------------------|------------------------------|---------------------------------|------------------------------------|
| Textbook order finding (Nielsen & Chuang ch.5; Vedral-Barenco-Ekert 1996) | n work qubits + ~2n phase qubits + ancillas | O(n^3) gates | -- |
| Beauregard 2003, n-bit N                     | 2n+3 qubits, semiclassical QFT | O(n^3 lg n) gates, O(n^3) depth | --                                  |
| Gidney & Ekeraa 2019, RSA-2048               | surface code, p = 10^-3, 1 microsecond cycle | --          | 20 million noisy qubits, ~8 hours   |
| Gidney 2025, RSA-2048                        | updated surface-code layout  | --                              | < 1 million noisy qubits, < 1 week  |

Reading the table top to bottom is reading the field's real progress: circuit-level costs are polynomial and modest (thousands of logical qubits); physical costs are enormous because each logical qubit and each logical T gate is purchased with error-corrected physical hardware. [Fowler et al. (2012)] established the surface-code machinery these estimates assume -- a code with the highest practical threshold, "about 1%", needing only nearest-neighbor interactions -- and the overhead accounting (2d^2 physical qubits per logical qubit at distance d, the p_L = 0.1 * (100*p)^((d+1)/2) suppression law, magic-state distillation for T gates) is worked through with simulations in [Quantum Error Correction](quantum-error-correction.md). A thousand-fold physical-to-logical overhead is the difference between a circuit diagram and a data center.

## NISQ-era status: 15, 21, and everything in between

Honesty requires a short list. The complete Shor algorithm -- including a real quantum order-finding subroutine -- has been demonstrated only on toy inputs, always compiled (instance-specific shortcuts replacing the general circuit):

- [Vandersypen et al. (2001), Nature]: seven spin-1/2 nuclei in a liquid-state NMR molecule; the abstract reports "an implementation of the simplest instance of Shor's algorithm: factorization of N=15 (whose prime factors are 3 and 5)".
- [Lucero et al. (2012)]: a nine-element superconducting processor ran "a three-qubit compiled version of Shor's algorithm to factor the number 15, and successfully find the prime factors 48% of the time" -- the first solid-state demonstration.
- [Martin-Lopez et al. (2012), Nature Photonics]: a photonic processor recycled one qubit n times ("the total number of qubits is one third of that required in the standard protocol") and ran "a two-photon compiled algorithm to factor N=21", with output "distinguishable from noise, in contrast to previous demonstrations".

No quantum device has ever factored an integer that a laptop could not factor instantly; RSA-2048 awaits machines with millions of physical qubits and deep fault-tolerant operation. The gap is not the algorithm -- it is that QPE requires coherent interference across a circuit with O(n^3) gates, and noise kills interference long before depth 10^9 on uncorrected hardware. That is why the error-correction page, not this one, describes the actual bottleneck for cryptographic-scale factoring.

## Post-quantum motivation

Shor's algorithm breaks RSA and Diffie-Hellman (order finding in Z*_N), ECC and ECDSA (the same reduction solves discrete logarithms in elliptic-curve groups). It does not break symmetric cryptography: AES and SHA-2 face only Grover's quadratic speedup, whose cost accounting lives in [Grover's Search](grovers-search.md) and is already priced into key-size guidance. The asymmetric break is why NIST standardized lattice-based key exchange and signatures: Module-LWE, the hardness assumption behind [ML-KEM / Kyber](../cryptography/kyber-mlkem.md), has no known subexponential quantum attack of any kind, Shor's or otherwise. The operational consequence -- migrate long-lived secrets now because traffic recorded today can be decrypted by a future cryptographically-relevant quantum computer -- is the subject of [Post-Quantum Cryptography](../cryptography/post-quantum.md).

## Demo: the classical half, and a real 3-qubit phase estimation

Part A runs the full classical side for N=21 and N=35: given noisy QPE outcomes c = round(s * 2^m / r_true) + jitter, it recovers the order by continued fractions (including the "s shares a factor with r" case, and an honest failure), then splits N with gcds. Part B is a genuine quantum simulation: a 128-amplitude statevector implements QPE on U|y> = |7y mod 15> with 3 control qubits and 4 work qubits -- Hadamards, controlled modular multiplications by 7^(2^j) mod 15, and a matrix inverse QFT -- then the same continued-fraction post-processing turns each measurement outcome into the order.

```python
# Shor's algorithm, simulated end to end on a classical machine (pure stdlib).
# Part A: noisy period measurements -> continued fractions -> factors (N=21, 35).
# Part B: a real 3-qubit quantum phase estimation run (128-amplitude statevector)
#         for order finding on N=15, a=7 -> order 4 -> gcd(7^2 +- 1, 15) = 3, 5.
import math, cmath

def convergents(num, den):
    """Denominators of the continued-fraction convergents of num/den."""
    out, p0, q0, p1, q1 = [], 0, 1, 1, 0           # seeds h_-2,h_-1 = 0,1; k_-2,k_-1 = 1,0
    while den:
        a = num // den
        p0, p1 = p1, a * p1 + p0
        q0, q1 = q1, a * q1 + q0
        out.append(q1)
        num, den = den, num - a * den
    return out

def order_from_phase(c, m, a, N, kmax):
    """Classical post-processing: recover the order of a mod N from outcome c/2^m."""
    for d in convergents(c, 1 << m):              # candidate denominators
        if not 0 < d <= kmax:
            continue
        for k in (d, 2 * d, 3 * d, 4 * d):        # s may share a factor with r
            if k <= kmax and pow(a, k, N) == 1:
                return k
    return None

def factors_from_order(a, r, N):
    """The classical half: even r and a^(r/2) != -1 (mod N) give gcd factors."""
    h = pow(a, r // 2, N)
    return math.gcd(h - 1, N), math.gcd(h + 1, N)

print("Part A: noisy period measurements -> continued fractions -> factors")
print("  (c = round(s * 2^m / r_true) + jitter; post-processing sees only c)")
for N, a, m, cases in ((21, 2, 10, ((1, 0), (5, -1), (2, 1))),
                       (35, 2, 11, ((5, 0), (7, 1), (6, -1)))):
    r_true = next(k for k in range(1, 4 * N) if pow(a, k, N) == 1)
    print("N=%d, a=%d, true order r=%d, m=%d phase qubits" % (N, a, r_true, m))
    for s, off in cases:
        c = round(s * (1 << m) / r_true) + off
        r = order_from_phase(c, m, a, N, 4 * N)
        if r and r % 2 == 0 and pow(a, r // 2, N) != N - 1:
            f1, f2 = factors_from_order(a, r, N)
            print("  s=%d off=%+d  c=%4d -> r=%2d, gcd(a^(r/2)-1,N)=%d, gcd(a^(r/2)+1,N)=%d"
                  % (s, off, c, r, f1, f2))
        else:
            print("  s=%d off=%+d  c=%4d -> unusable (s not coprime to r): rerun"
                  % (s, off, c))

print()
print("Part B: quantum phase estimation on U|y> = |7y mod 15>, 3 control qubits")
m, M, A = 3, 15, 7
mult = [pow(A, 1 << j, M) for j in range(m)]      # 7^(2^j) mod 15 = 7, 4, 1
nw = 4                                            # work qubits: values 0..15
psi = [0j] * (1 << m) * (1 << nw)                 # 128 complex amplitudes
psi[1] = 1.0                                      # control |000>, work |1>
psi = [sum(psi[c * 16 + y] * (-1) ** bin(c & d).count("1")   # Hadamards on
           for c in range(1 << m)) / math.sqrt(1 << m)         # the 3 controls
       for d in range(1 << m) for y in range(1 << nw)]
for c in range(1 << m):                           # controlled-U^(2^j) blocks:
    g = 1
    for j in range(m):
        if (c >> j) & 1:
            g = g * mult[j] % M                   # work -> |7^x y mod 15>
    buf = [0j] * (1 << nw)
    for y in range(1 << nw):
        buf[g * y % M] += psi[c * 16 + y]
    psi[c * 16:c * 16 + 16] = buf
psi = [sum(psi[c * 16 + y] * cmath.exp(-2j * math.pi * d * c / (1 << m))
           for c in range(1 << m)) / math.sqrt(1 << m)   # inverse QFT on control
       for d in range(1 << m) for y in range(1 << nw)]
probs = [sum(abs(psi[d * 16 + y]) ** 2 for y in range(1 << nw))
         for d in range(1 << m)]
print("control outcome c   P(c)    c/8 as fraction   recovered order r")
for c, p in enumerate(probs):
    if p > 1e-9:
        r = None if c == 0 else order_from_phase(c, m, A, M, M)
        print("  c=%d             %.4f     s/4 with s=%d      %s"
              % (c, p, c // 2, "s=0: rerun" if c == 0 else r))
h = pow(A, 2, M)
print("order r=4, a^(r/2) = 7^2 = %d mod 15:  gcd(7^2-1,15)=%d  gcd(7^2+1,15)=%d"
      % (h, math.gcd(h - 1, M), math.gcd(h + 1, M)))
```

Real output:

```text
Part A: noisy period measurements -> continued fractions -> factors
  (c = round(s * 2^m / r_true) + jitter; post-processing sees only c)
N=21, a=2, true order r=6, m=10 phase qubits
  s=1 off=+0  c= 171 -> r= 6, gcd(a^(r/2)-1,N)=7, gcd(a^(r/2)+1,N)=3
  s=5 off=-1  c= 852 -> r= 6, gcd(a^(r/2)-1,N)=7, gcd(a^(r/2)+1,N)=3
  s=2 off=+1  c= 342 -> r= 6, gcd(a^(r/2)-1,N)=7, gcd(a^(r/2)+1,N)=3
N=35, a=2, true order r=12, m=11 phase qubits
  s=5 off=+0  c= 853 -> r=12, gcd(a^(r/2)-1,N)=7, gcd(a^(r/2)+1,N)=5
  s=7 off=+1  c=1196 -> r=12, gcd(a^(r/2)-1,N)=7, gcd(a^(r/2)+1,N)=5
  s=6 off=-1  c=1023 -> unusable (s not coprime to r): rerun

Part B: quantum phase estimation on U|y> = |7y mod 15>, 3 control qubits
control outcome c   P(c)    c/8 as fraction   recovered order r
  c=0             0.2500     s/4 with s=0      s=0: rerun
  c=2             0.2500     s/4 with s=1      4
  c=4             0.2500     s/4 with s=2      4
  c=6             0.2500     s/4 with s=3      4
order r=4, a^(r/2) = 7^2 = 4 mod 15:  gcd(7^2-1,15)=3  gcd(7^2+1,15)=5
```

What to notice: Part B's control register peaks exactly at c = s * 2^m/r (the eigenphases are exact multiples of 1/4 here, so the peaks are perfectly sharp); the s = 0 outcome is pure waste and forces a rerun, which is the phi(r)/r repetition factor made visible; and c = 4 recovers the order only through the "try multiples of the convergent denominator" step because s = 2 is not coprime to r = 4. Every line of the quantum part is textbook QPE -- no shortcuts, no baked-in answers.

## Interview-style derivations

> **"Why does the first register need m = 2n qubits?"**

The measurement c pins down s/r only if no two admissible fractions are closer than the measurement error. Two distinct fractions s/r and s'/r' with r, r' <= N differ by at least 1/N^2 in absolute value. With m = 2n, 2^m >= N^2, so the QPE error 1/2^(m+1) < 1/(2N^2) straddles at most one admissible fraction, and the continued-fraction reconstruction is unique. With m = n the fractions collide and the post-processing fails silently -- the most common implementation bug.

> **"Where exactly does the speedup come from?"**

Finding r classically means evaluating a^x mod N for enough x to detect periodicity -- exponential in n in the worst case (and order finding is equivalent to factoring). The quantum circuit evaluates a^x mod N for all 2^m values of x in superposition with O(n^3) gates, and the QFT converts the periodicity into measurable peaks. The exponential win is the interference step: not "trying all x in parallel" (measurement would return a random pair), but keeping only the Fourier components shared by every period.

> **"What is the total success probability, and what do you do on failure?"**

Per run: >= 4/pi^2 ~ 0.405 that c is within 1/2 of s*2^m/r; phi(r)/r that gcd(s, r) = 1; >= 1/2 (for N = p*q) that r is even and a^(r/2) != -1. Multiply: a constant, roughly 0.1-0.4. On any failure you learn it immediately and classically (the gcd splits N or it does not; a^r = 1 or it does not), so you just rerun with a fresh a -- expected total runs O(1). Failure is detectable, which is what makes "constant expected repetitions" a usable bound.

## Where this fits in this book

[Quantum Fundamentals](quantum-fundamentals.md) builds the gate model and the QFT/QPE machinery this page applies; [Grover's Search](grovers-search.md) covers the *other* cryptanalytic speedup -- quadratic, optimal, and survivable with bigger keys -- and the oracle-model caveats that also apply here; [Quantum Error Correction](quantum-error-correction.md) explains why the logical circuits above cost millions of physical qubits; [ML-KEM / Kyber](../cryptography/kyber-mlkem.md) and [Post-Quantum Cryptography](../cryptography/post-quantum.md) describe the migration that Shor's 30-year-old algorithm is still forcing.

## References

1. P. W. Shor. "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer." SIAM J. Comput. 26(5):1484-1509, 1997 (journal version of the FOCS 1995 paper). <https://doi.org/10.1137/S0097539795293172>
2. A. Ekert, R. Jozsa. "Quantum computation and Shor's factoring algorithm." Rev. Mod. Phys. 68:733-753, 1996. <https://doi.org/10.1103/RevModPhys.68.733>
3. V. Vedral, A. Barenco, A. Ekert. "Quantum Networks for Elementary Arithmetic Operations." Phys. Rev. A 54:147-153, 1996. <https://arxiv.org/abs/quant-ph/9511018>
4. S. Beauregard. "Circuit for Shor's algorithm using 2n+3 qubits." Quantum Information & Computation 3(2):175-185, 2003. <https://arxiv.org/abs/quant-ph/0205095>
5. M. A. Nielsen, I. L. Chuang. "Quantum Computation and Quantum Information," 10th anniversary ed., Chapter 5 and Appendix 4. Cambridge University Press, 2010.
6. A. G. Fowler, M. Mariantoni, J. M. Martinis, A. N. Cleland. "Surface codes: Towards practical large-scale quantum computation." Phys. Rev. A 86:032324, 2012. <https://arxiv.org/abs/1208.0928>
7. C. Gidney, M. Ekeraa. "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits." Quantum 5:433, 2021. <https://doi.org/10.22331/q-2021-04-15-433>
8. C. Gidney. "How to factor 2048 bit RSA integers with less than a million noisy qubits." 2025. <https://arxiv.org/abs/2505.15917>
9. L. M. K. Vandersypen, M. Steffen, G. Breyta, C. S. Yannoni, M. H. Sherwood, I. L. Chuang. "Experimental realization of Shor's quantum factoring algorithm using nuclear magnetic resonance." Nature 414:883-887, 2001. <https://arxiv.org/abs/quant-ph/0112176>
10. E. Martin-Lopez, A. Laing, T. Lawson, R. Alvarez, X.-Q. Zhou, J. L. O'Brien. "Experimental realization of Shor's quantum factoring algorithm using qubit recycling." Nature Photonics 6:773-776, 2012. <https://doi.org/10.1038/nphoton.2012.259>
11. J. A. Lucero et al. "Computing prime factors with a Josephson phase qubit quantum processor." 2012. <https://arxiv.org/abs/1202.5707>
