# Code-Based Cryptography

Code-based cryptography derives its security from the *hardness of decoding random linear codes*. It is the oldest family in the post-quantum landscape — the McEliece cryptosystem (1978) predates RSA in its current form, and after 45+ years of cryptanalysis it remains unbroken in its conservative-parameter regime. NIST selected Classic McEliece as a fourth-round alternative KEM (alongside ML-KEM) and selected BIKE and HQC as fourth-round candidates for additional standardization. This page covers the syndrome decoding problem, the McEliece and Niederreiter cryptosystems, the Classic McEliece spec, quasi-cyclic codes (BIKE, HQC), and a comparison with lattice-based schemes.

## Linear Codes and the Syndrome Decoding Problem

A *linear code* `C` over the field `F_q` is a linear subspace of `F_q^n` of dimension `k` (so `|C| = q^k`). Any such code can be described by:

- A *generator matrix* `G ∈ F_q^(k × n)`, so `C = {u·G : u ∈ F_q^k}`.
- A *parity-check matrix* `H ∈ F_q^((n-k) × n)`, so `C = {x ∈ F_q^n : H·xᵀ = 0}`.

The two descriptions are equivalent: rows of `H` span the orthogonal complement of the row span of `G`.

The *syndrome* of a received word `y ∈ F_q^n` (relative to a parity-check matrix `H`) is `s = H·yᵀ ∈ F_q^(n-k)`. The syndrome of a *codeword* is zero. The syndrome of `y = c + e` (a codeword plus an error `e`) is `H·eᵀ`. So decoding `y` to find the nearest codeword is equivalent to: given `s = H·yᵀ`, find a minimum-weight `e ∈ F_q^n` with `H·eᵀ = s`. This is the **Syndrome Decoding Problem (SDP)**.

### SDP (Decisional Form)

Given `H ∈ F_q^((n-k) × n)` (uniformly random), a target syndrome `s`, and a weight bound `w`, decide whether there exists `e ∈ F_q^n` with `‖e‖_0 ≤ w` and `H·eᵀ = s`.

### Berlekamp-McEliece-Rumsey-Rodemich-Welsh hardness

Berlekamp, McEliece, van Tilborg (1978) proved that the syndrome decoding problem is **NP-hard** (under randomized reductions). The reduction goes from Three-Dimensional Matching. This is the foundational hardness result for all of code-based cryptography.

Consequences:

1. **Worst-case hardness**, not just average-case (like LWE/SIS).
2. **No known polynomial-time quantum algorithm.** Unlike factoring/discrete-log, there is no quantum speedup for SDP beyond the quadratic Grover.
3. **No "structured-instance" reduction.** Unlike LWE, the worst-case to average-case reduction story is weaker; the random codes used in McEliece are *not* believed to be the hardest instances, just hard-on-average enough.

### Information-set decoding (ISD) — the dominant attack

The best known attack on a random code's SDP is **Information-Set Decoding** (Prange 1962, Lee-Brickell 1988, Stern-Dumer, May-Meurer-Thomae, Becker-Joux-May-Meurer, May-Thomae-Finiasz-Schwabe, …). The state-of-the-art variants (MMT, BJMM, KMP) achieve roughly:

```
   c_ISD  ≈  0.494·(n - k)·log(q) / log(n)   ≈   ⎯ work factor ⎯
```

For McEliece parameters `(n, k, t)` over `F_2`, the security log-2 cost is well-modeled by the "Bernstein-Lange-Peters (BLP) bound" (2011). For Classic McEliece `mceliece348864`, the BLP bound gives ≈ 2^139 operations classical, ≈ 2^135 quantum (using Grover on the inner search) — both well above the NIST Level 1 requirement of 2^143 gates (classical).

## The McEliece Cryptosystem (1978)

The McEliece cryptosystem is the original code-based public-key encryption scheme. It uses Goppa codes — a class of *structured* algebraic-geometry codes — disguised via a random-looking generator matrix.

### Setup

Pick a Goppa code `C` with parameters `(n, k, t)` over `F_2`:
- `n = 2^m` (the code length; for the standard binary Goppa, `m = log_2(n)` is the degree of the field extension).
- `k` is the dimension.
- `t` is the number of errors that the code's decoder can correct.

A binary Goppa code with parameters `(n, k, t)` corrects up to `t` errors per codeword; the standard constructions have `k ≈ n - m·t`. The matrix `G` (a generator matrix for the Goppa code) is a structured `k × n` matrix.

### Key Generation

```
Generate key:
   G         ← generator matrix for a Goppa code C
   S         ← random invertible k × k matrix over F_2          (the "scrambler")
   P         ← random n × n permutation matrix
   G_pub = S · G · P                                              (the public key matrix)
   sk = (G, S, P)                                                 (private key)
```

The public key `G_pub` looks like a *random* generator matrix, because the structure of the Goppa code has been disguised by `S` (a row-mixing matrix) and `P` (a column permutation). Public key size: `k · n` bits. For Classic McEliece `(3488, 2720, 64)`, that's `2720 · 3488 ≈ 9.5 Mbit ≈ 1.18 MB`.

### Encryption

```
   Input:  message m ∈ F_2^k   (length-k bitstring)
   Choose: e ∈ F_2^n with weight t  (i.e., exactly t ones scattered across n bits)
   y = m · G_pub + e                                             (ciphertext)
   Output: ciphertext y
```

Encryption is one matrix-vector multiplication plus adding a weight-`t` error vector. It is extremely fast.

### Decryption

```
   y' = y · P^{-1}              (undo the permutation)
        = m · S · G · P · P^{-1} + e · P^{-1}
        = (m · S) · G + e'         where weight(e') = weight(e) ≤ t
   m' = decode_Goppa(y')        (correct up to t errors)
        = m · S                  (decode gives the codeword, i.e., the message-after-scrambling)
   m = m' · S^{-1}               (unscramble)
```

This works because the Goppa decoder corrects up to `t` errors, and `weight(e) = t` was enforced at encryption time. Permutation doesn't change weight, so `e'` is also weight-`t`. The decoder returns the closest codeword, which is `m · S · G`. Multiplying on the right by `S^{-1}` recovers `m`.

### Worked example (toy, `n = 7, k = 4, t = 1` over `F_2`)

Take the [7,4,3] Hamming code as a stand-in for a Goppa code (it has a similar parity-check structure):

```
G = ⎡1 0 0 0 1 1 0⎤
    ⎢0 1 0 0 1 0 1⎥
    ⎢0 0 1 0 0 1 1⎥
    ⎣0 0 0 1 1 1 1⎦      (Hamming's standard generator)

Pick S, P:
S = ⎡1 1 0 0⎤     P = identity (toy)
    ⎢0 1 0 0⎥
    ⎢0 0 1 0⎥
    ⎣0 0 0 1⎦

G_pub = S · G  = ⎡1 1 0 0 0 1 1⎤
                 ⎢0 1 0 0 1 0 1⎥
                 ⎢0 0 1 0 0 1 1⎥
                 ⎣0 0 0 1 1 1 1⎦

Secret: G, S; Public: G_pub; Permutation: identity (toy only)
```

Encrypt `m = [1, 0, 0, 0]`:

```
   m · G_pub = [1, 1, 0, 0, 0, 1, 1]    (a codeword of G_pub)
   e = [0, 0, 0, 0, 0, 1, 0]             (weight 1)
   y = [1, 1, 0, 0, 0, 0, 1]             (one bit flipped)
```

Decrypt (P = identity, so y' = y):

```
   y' is one bit away from a codeword of G. The Hamming decoder picks the closest codeword.
   syndrome(y') = H · y'ᵀ = [0,1,1] (binary) → position 6 is wrong.
   After correction: m' = [1, 1, 0, 0, 0, 1, 1] = (m · S) · G
   m · S = first 4 bits = [1, 1, 0, 0]
   m = (m·S) · S^{-1} = [1, 0, 0, 0]  ✓
```

Real Goppa codes have parameters like `n = 3488, k = 2720, t = 64` (Classic McEliece `mceliece348864`).

## The Niederreiter Variant (1986)

Niederreiter observed that you can build the dual system: use the *parity-check matrix* `H` instead of the generator, and a syndrome `s = H·eᵀ` as the ciphertext.

```
   KeyGen: H_pub = S · H · P      (scramble the parity-check matrix)
   Encrypt: choose e of weight t; s = H_pub · eᵀ  (syndrome = ciphertext)
   Decrypt: e' = (P^{-1} · S^{-1} · s)ᵀ then unscramble the permutation; recover e
```

This is *equivalent* to McEliece in security (Li-Dawson 2004) but with a different algebraic structure. Crucially, the ciphertext is *just the syndrome* — much shorter than a McEliece ciphertext, which has length `n`. Niederreiter's structure is what Classic McEliece uses.

## Classic McEliece — NIST Candidate

Classic McEliece (Bernstein, Chou, Lange, Niederhagen, Püschel, Schwabe, Virdick, Willems) is a Niederreiter-style KEM over binary Goppa codes. It uses the FO transform for CCA security (just like ML-KEM does).

### Parameters

| Name                 | `n`  | `m`  | `t`  | `k`   | pk size (bytes) | ct size (bytes) | Security |
|----------------------|------|------|------|-------|-----------------|-----------------|----------|
| mceliece348864       | 3488 | 12   | 64   | 2720  | 261,120         | 128             | AES-128  |
| mceliece460896       | 4608 | 12   | 96   | 3456  | 524,160         | 188             | AES-192  |
| mceliece6688128      | 6688 | 13   | 128  | 5024  | 1,044,992       | 240             | AES-256  |
| mceliece6960119      | 6960 | 13   | 119  | 5413  | 1,044,992       | 222             | AES-256  |
| mceliece8192128      | 8192 | 13   | 128  | 6144  | 1,367,520       | 240             | AES-256  |

Note the **massive public keys** — 261 KB to 1.37 MB! And the **tiny ciphertexts** — 128 to 240 bytes — smaller than ML-KEM's.

Why NIST didn't pick Classic McEliece as the primary KEM standard:

1. **The 1 MB public key is too large for general TLS use.** It blows up the ClientHello.
2. **Performance** is asymmetric: encryption is fast, but key generation is slow (~10 ms per key, due to the cost of generating a Goppa code's structure). This doesn't play well with short-lived session keys.
3. **The remaining flexibility** — McEliece is one specific choice of code (binary Goppa); NIST wanted ML-KEM for the broad ecosystem and Classic McEliece as a conservative fallback.

What NIST *did* pick: Classic McEliece was put on the "additional KEM" track — a slow-track standardization to keep a non-lattice-based KEM available in case Module-LWE turns out to have weaknesses.

## Quasi-Cyclic Codes: BIKE and HQC

The McEliece public key is huge because binary Goppa codes have *no* compact representation — you must serialize the entire `k × n` generator/parity-check matrix. Modern variants use *structured* codes that have a compact representation but still resist known attacks.

### Quasi-Cyclic (QC) Structure

A code is *quasi-cyclic* if its generator/parity-check matrix is composed of circulant blocks. A circulant matrix is fully described by its first row (the rest are rotations of it). So a QC parity-check matrix built from `r × r` circulant blocks has a compact description of size `O(r)` rather than `O(r²)`.

The cryptographic question is whether QC structure weakens SDP. The Tiontze-Vasseur-Wenger-Zémor (TWMZ) 2024 attack on QC-MDPC codes (which broke some BIKE parameter sets) is the latest in a series of attacks exploiting this structure. BIKE was modified in response to these attacks by increasing parameters; it is currently in NIST Round 4 with the new "BIKE-2L" parameter sets.

### BIKE (Bit-flipping Key Encapsulation)

BIKE uses *Moderate-Density Parity-Check* (MDPC) codes — codes with a sparse (but not maximum-density) parity-check matrix. Decryption uses a *bit-flipping decoder*: iterate over positions of the syndrome, flip the bit that contributes most to the current syndrome mismatches, until the syndrome is zero.

```
   BIKE structure:
   - H is a block matrix [H_0 | H_1] where H_0, H_1 are r×r circulant sparse matrices
   - the secret is the set of weight-d "support" of each H_i
   - the ciphertext is the syndrome s = H · eᵀ where e is a weight-t/2 vector
   - decryption uses a black-gray-black (BGB) bit-flipping decoder
```

BIKE's main remaining cryptanalytic concern is the timing of the decoder — the bit-flipping decoder is *inherently* variable-time, leading to a class of attacks ("reaction attacks") that can recover the secret by submitting malformed ciphertexts and observing decapsulation timing. Modern BIKE implements constant-time decoders (the "early-exit trick" of Sendrier-Vasseur) to mitigate this, but it remains a thorn.

### HQC (Hamming Quasi-Cyclic)

HQC is a different design: instead of using a decoder as a primitive, it uses *any* decoder for a Reed-Muller code (which has known efficient decoders) and adds the randomness via a *multiplicative* structure with a *decoding-capacity check*. HQC's construction is in the *randomized decoding* family.

HQC was selected by NIST in March 2025 for standardization as an additional PQC KEM (alongside ML-KEM).

### Performance comparison

| Scheme              | pk (bytes) | ct (bytes) | Keygen | Encaps | Decaps |
|---------------------|------------|------------|--------|--------|--------|
| X25519              | 32         | 32         | 21 µs  | 52 µs  | 117 µs |
| ML-KEM-768          | 1184       | 1088       | 33 µs  | 47 µs  | 39 µs  |
| BIKE-3-Level-3      | 2309       | 2309       | 100 µs | 130 µs | 750 µs |
| HQC-128             | 2249       | 4497       | 50 µs  | 60 µs  | 80 µs  |
| Classic McEliece 348864 | 261,120| 128        | 13 ms  | 100 µs | 60 µs  |

(Source: BIKE Round-4 spec; HQC Round-4 spec; Classic McEliece Round-4 spec. Numbers vary by platform.)

Notable:

- Classic McEliece has the *slowest* key generation and the *fastest* encryption/decryption.
- BIKE's decapsulation is dominated by the variable-time bit-flipping decoder.
- HQC's symmetric-key size balance is between ML-KEM and BIKE.

## Why Use Code-Based Crypto?

The argument for including a code-based KEM in the PQC portfolio:

1. **Decades of cryptanalysis.** McEliece has survived 45+ years of attack. The "conservative" stance is: if you can afford the 1 MB public key, McEliece is the safest bet.
2. **Different hardness assumption.** Lattice crypto reduces to SVP/SIVP; code-based reduces to SDP. A breakthrough in lattice reduction would leave code-based untouched.
3. **No quantum algorithm improvement.** ISD attacks see only a quadratic Grover speedup, and there is no known quantum analog of algebraic lattice structure that could give subexponential speedups.
4. **Asymmetric performance for specific use cases.** Long-lived keys (e.g., a root CA's McEliece public key, published once and used for years) justify the 1 MB key cost in exchange for the tiny ciphertexts and fast encryption.

## Open Problems in Code-Based Crypto

1. **Whether Goppa codes can be distinguished from random codes.** The current McEliece security argument assumes *indistinguishability* of Goppa matrices. No efficient distinguisher is known for the parameter regimes Classic McEliece uses.
2. **ISD improvements.** The BLP bound (used by Classic McEliece) is asymptotic; better ISD variants keep shrinking the security margin. Current Classic McEliece parameters have a 30+ bit security margin above the NIST Level requirements.
3. **QC structure.** The TWMZ attack on QC-MDPC is the most recent structural attack. BIKE's parameter sets were updated in response. The crypto community is uncertain how much more structure there is to exploit.
4. **Decoder side-channels.** BIKE's bit-flipping decoder remains the most serious implementation concern; constant-time decoders exist but cost performance.

## Worked Example: BIKE-style syndrome bit-flipping

Consider a tiny BIKE-like setup with `r = 8, t = 4`:

```
H_0 = [1 0 1 0 0 1 0 0]   (weight 3)
H_1 = [0 1 0 0 1 0 1 0]   (weight 3)
H = [H_0 | H_1]   (a 1 × 16 sparse parity-check, conceptually a 2-block circulant)

Secret key: positions of the 1s in H_0 and H_1.
Error e: weight-2 vector — say, a 1 in position 0 and a 1 in position 12.
   syndrome s = H · eᵀ  =  H_0[0] · 1 + H_1[12 mod 8] · 1 = ...
                                  (depends on circulant rotation)

Bit-flipping decode:
  for each position i in [0, 16):
    counters[i] = # of unsatisfied parity checks that involve position i
  flip position i* with max counter
  recompute syndrome, repeat
```

In real BIKE, the bit-flipping is wrapped in a "Black-Gray-Black" (BGB) trick to handle the parity check distribution, and uses multiple decoder rounds with different selection rules.

## References

- McEliece, *A Public-Key Cryptosystem Based On Algebraic Coding Theory*, DSN Progress Report 1978 — https://ipnpr.jpl.nasa.gov/progress_report2/42-44/44N.PDF
- Berlekamp, McEliece, van Tilborg, *On the Inherent Intractability of Certain Coding Problems*, IEEE Trans. Info. Theory, 24(3), May 1978 — https://doi.org/10.1109/TIT.1978.1055873
- Niederreiter, *Knapsack-type cryptosystems and algebraic coding theory*, Problems of Control and Information Theory, 15(2):159-166, 1986 — https://www.math.tugraz.at/~cabo/BCH/
- Classic McEliece NIST Round-4 submission — https://classic.mceliece.org/spec.html
- BIKE NIST Round-4 specification — https://bikesuite.org/
- HQC NIST Round-4 specification — https://pqc-hqc.org/
- Bernstein, Lange, Peters, *Smaller decoding exponents: collision decoding is faster*, FSE 2012 (BLP ISD bound) — https://eprint.iacr.org/2010/577
- May, Meurer, Thomae, *Decoding Random Linear Codes in `O(2^0.054n)`*, ASIACRYPT 2011 (MMT ISD bound) — https://www.iacr.org/archive/asiacrypt2011/70730119/70730119.pdf
- Becker, Joux, May, Meurer, *Decoding Random Linear Codes in `O(2^0.054n)`*, EUROCRYPT 2012 (BJMM bound) — https://eprint.iacr.org/2012/026
- Sendrier, Vasseur, *Sampling the spectrum of QC-LDPC coded modulations*, 2020; *On the Complexity of the BJMM Decoding algorithm: the improved ISD for linear codes*, IEEE Trans. Info. Theory 2018 — for BIKE timing attacks: https://eprint.iacr.org/2019/1468
- Wenger, Vasseur, Zémor, *A simpler algorithm for finding short vectors in quasi-cyclic lattices*, 2024 (TWMZ QC attack) — https://eprint.iacr.org/2024/071
- NIST PQC Round 4 status report (2022) — https://csrc.nist.gov/CSRC/media/Publications/nistir/8413/final/documents/nistir8413.pdf
- NIST IR 8528 (Status of Round 4 candidates, 2025) — https://csrc.nist.gov/pubs/nistir/8528/final

## Interview Questions

1. **State the Syndrome Decoding Problem. What is its complexity class, and what is the foundational hardness result?**
2. **Walk through McEliece encryption. Why does the Goppa decoder recover the message in spite of the error `e`?**
3. **What is the Niederreiter variant, and what advantage does it offer over McEliece?**
4. **Why is Classic McEliece's public key so large (~1 MB) compared to ML-KEM-768's 1.2 KB? What could be done to reduce it?**
5. **Explain the ISD family of attacks. What is the BLP bound, and why is it important for parameter selection?**
6. **Describe the structure of a quasi-cyclic code. What compactness does it buy you, and what attack does the structure open you up to?**
7. **What is the BIKE decoder's bit-flipping approach, and what side-channel attack does it expose?**
8. **Compare McEliece to BIKE to HQC on parameters, performance, and security assumptions.**
9. **Why does NIST standardize code-based KEMs alongside lattice-based ones? What's the defense-in-depth argument?**
10. **The McEliece system has survived 45+ years of cryptanalysis. Does this mean it's safer than lattice-based crypto? Why or why not?**
