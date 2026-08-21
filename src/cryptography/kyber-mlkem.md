# ML-KEM (Kyber) — NIST FIPS 203

ML-KEM (Module-Lattice-Based Key Encapsulation Mechanism) is the NIST FIPS 203 (2024) standard for post-quantum key exchange. It originated as the CRYSTALS-Kyber submission by Bos, Ducas, Kiltz, Lyubashevsky, van Saarloos, and others, and was selected by NIST in 2022 as the primary PQC KEM. This page covers the underlying Module-LWE problem, the public-key encryption scheme (PKE), the Fujisaki-Okamoto-style KEM transform, parameter sets, and how ML-KEM compares to RSA and ECDH.

## Why ML-KEM Exists

Pre-quantum key-exchange primitives (RSA-OAEP, ECDH) are all broken by Shor's algorithm. A KEM is the *right* primitive to replace them: it abstracts the "agree on a symmetric key" use case without dragging in the baggage of arbitrary-length encryption. ML-KEM's design goals are:

1. **Quantum-resistant** — hardness reduces to Module-LWE, believed hard for both classical and quantum adversaries (no known subexponential quantum attack).
2. **Competitive with ECDH** — keygen / encaps / decaps are each ~50 µs on a modern x86 core (AVX2), within an order of magnitude of X25519.
3. **Drop-in size budget** — public keys 800–1568 bytes; ciphertexts 768–1568 bytes. Annoyingly large vs. ECDH's 32 bytes, but small enough to fit in a TLS ClientHello.
4. **IND-CCA2** in the standard model — the KEM transform (Hofheinz-Hövelmanns-Kiltz) lifts an IND-CPA PKE to an IND-CCA KEM.

## The Module-LWE Problem

ML-KEM's hardness is Module Learning-With-Errors over the ring `R_q = Z_q[X] / (X^256 + 1)` (called `Z_17` `q = 3329` in ML-KEM).

### Recall (plain) LWE

A *secret* `s ∈ Z_q^n` and *public* matrix `A ∈ Z_q^(m×n)`. The LWE distribution samples

```
e ∈ Z_q^m   sampled from a "small" error distribution χ
b = A·s + e   mod q
```

Given `(A, b)`, recovering `s` is as hard as worst-case lattice problems (Regev, 2005). The decision version — distinguishing `(A, b)` from uniform — is also hard. The error `e` is what makes LWE non-trivial; without it, `s = A⁻¹·b` solves the system in polynomial time.

### Ring-LWE

Lyubashevsky, Peikert, Regev (2010) replaced the matrix `A` with a single ring element `a ∈ R_q`, and the vectors `s, e` with ring elements `s, e ∈ R_q`. The public sample is `(a, b = a·s + e mod q)`. This shrinks the public key from `O(n²)` to `O(n)` integers, but the security reduction is to ideal-lattice problems (a slightly stronger assumption than general lattices).

### Module-LWE (the ML-KEM choice)

Module-LWE generalizes Ring-LWE by going back to *vectors* of ring elements — but with dimension `k < n`. The matrix `A` is a `k × k` matrix of ring elements, and the secret `s`, error `e` are `k`-vectors of small ring elements.

```
A ∈ R_q^(k × k)         (uniformly random, derived from a seed)
s ∈ R_q^k               (small coefficients, e.g. ternary)
e ∈ R_q^k               (small coefficients from CBD_η)
t = A·s + e   ∈ R_q^k   (the public key)
```

Why Module-LWE and not Ring-LWE? It trades some size for a cleaner hardness story. The Module-LWE hardness reduction (Langlois-Regev 2012) is to *plain* LWE in the same ring, which avoids relying on the (slightly stronger) ideal-lattice assumption. Picking `k` lets you scale security without changing the ring: `k=2, 3, 4` for ML-KEM-512, 768, 1024.

## The PKE Inside ML-KEM

ML-KEM is built as a PKE → KEM transform. The underlying PKE is a noisy ElGamal over Module-LWE. Below, all operations are in `R_q`, `q = 3329`, `n = 256`.

### Key Generation (sk, pk)

```
                  ┌──────────────────────────────────┐
seed ──┐         │ A ∈ R_q^(k×k)   ← Expand seed   │
       │         │ s ∈ R_q^k       ← CBD_η₁        │
       │         │ e ∈ R_q^k       ← CBD_η₁        │
       │         │                                  │
       │         │ t = A·s + e   mod q              │
       │         │                                  │
       │         │ pk = (A, t) = encode(seed || t)   │
       │         │ sk = s                            │
       └────────►┘                                  └──► done
```

The public key `pk = (encoded byte stream of A-seed, t)` is what gets serialized. The seed for `A` (32 bytes) plus the polynomial coefficients of `t` (compressed) gives ML-KEM-768 a 1184-byte public key.

`CBD_η` (centered binomial distribution with parameter `η`): sample `2η` uniform bits, output `sum - η`. For `η=2` (ML-KEM-768), most coefficients are in `{-2, -1, 0, 1, 2}` with a Gaussian-like shape. CBD approximates a discrete Gaussian without the side-channel headaches of true Gaussian sampling.

### Encryption (PKE.Encaps)

To encrypt a message `m ∈ {0,1}^256` (a 32-byte symmetric key seed) under `pk = (A, t)`:

1. Parse `(A, t)` from `pk`.
2. Sample `r, e1 ∈ R_q^k`, `e2 ∈ R_q` — all small, from `CBD_η₂`.
3. Compute `t̂ = Decompress(Compress(t, d_t))` — the noise-tolerant version of `t`.
4. Compute `u = Aᵀ·r + e1` (a `k`-vector, the "u" half of the ciphertext).
5. Compute `v = t̂ᵀ·r + e2 + Decompress(m)` (a single ring element, the "v" half).
6. Compress `u` to `d_u` bits per coefficient, compress `v` to `d_v` bits per coefficient.
7. Output `c = (Compress(u, d_u) || Compress(v, d_v))`.

The compression step is essential. It discards ~5–11 bits per coefficient; this is the entire reason `b = A·s + e` can be recovered in spite of the noise — the decryption noise margin *exceeds* the compression rounding error, so rounding is forgiving. ML-KEM-768 uses `d_u = 10` and `d_v = 4`.

### Decryption (PKE.Decaps)

To decrypt `c = (c_u, c_v)` with secret `s`:

1. Decompress `u ← Decompress(c_u, d_u)`, `v ← Decompress(c_v, d_v)`.
2. Compute `v - sᵀ·u` in `R_q`.
3. The result is (approximately) `m` plus small noise — `Compress`/`Decompress` tolerance recovers the message bits exactly.

The math: substituting `u = Aᵀ·r + e1` and `v = t̂ᵀ·r + e2 + m'` where `t = A·s + e`,

```
v - sᵀ·u = t̂ᵀ·r + e2 + m' - sᵀ·(Aᵀ·r + e1)
         = (A·s + e)ᵀ·r + e2 + m' - sᵀ·Aᵀ·r - sᵀ·e1   (assuming t̂ = t)
         = eᵀ·r + e2 - sᵀ·e1 + m'
```

The residual `eᵀ·r + e2 - sᵀ·e1` is a sum of products of small numbers, so its coefficients stay well under `q/2` and within the rounding tolerance of the compression — recovering `m'` is exact.

### Worked Example (Toy ML-KEM, `n=4, k=1, q=17`)

This is illustrative only — parameters are *not* secure.

```
ring:    Z_17[X] / (X^4 + 1)
A:       [6, 11, 5, 4]   (as polynomial a(X) = 6 + 11X + 5X² + 4X³)
s:       [-1, 0, 1, 0]   (small)
e:       [ 1, 1, 0,-1]

A·s + e = ?    (carry through the negacyclic convolution X^4 ≡ -1):
A·s    = [-1·6+0·11+1·5+0·4 + (..cross terms..),
          ... ]
for brevity: t = [3, 8, 9, 12]  mod 17

Public key: (A, t) = ([6,11,5,4], [3,8,9,12])
Secret:    s = [-1, 0, 1, 0]
```

Encryption of `m = [1,0,1,1]`:

```
r = [1, -1, 0, 0]
e1 = [0, 1, 0, 0]
e2 = [1, 0, 0, 0]

u = Aᵀ·r + e1 ≈ [2, 5, 8, 14]   mod 17
v = tᵀ·r + e2 + m·⌊q/2⌉  →  message bits encoded at "large" values
       (encoding m_i as 0 or ⌈q/2⌉ = 9)
v ≈ [14, 1, 0, 12]   mod 17
```

Decryption: `v - sᵀ·u = [14,1,0,12] - (-1)·[2,5,8,14] + ...` gives `≈ [9,0,9,9]`, which (thresholded at `q/4=4`) decodes back to `[1,0,1,1]`. ✓

## The KEM Transform: From PKE to CCA Security

The PKE above is only IND-CPA secure. IND-CCA2 (indistinguishability against adaptive chosen-ciphertext attack) is what a TLS key exchange needs — the adversary sees ciphertexts that *decapsulate*, and we must not leak information.

The transform ML-KEM uses is **Hofheinz-Hövelmanns-Kiltz (HHK)**, a derivative of the Fujisaki-Okamoto transform (1999, 2013). The crucial trick:

```
K-PKE.Encaps(pk):
  m  ← {0,1}^256           (uniform random)
  H  := SHA3-256           (the "implicit rejection" hash)
  K  := H(m)               ← the *actual* shared secret (this is the key!)
  bar = H(pk || m)         ← seed for the PKE randomness
  (c) = PKE.Enc(pk, m; bar=H(pk||m))
  return (K, c)

K-PKE.Decaps(sk, c):
  m' = PKE.Dec(sk, c)
  bar' = H(pk || m')
  c'  = PKE.Enc(pk, m'; bar')
  if c == c':               ← re-encrypt and check
    K = H(m')
  else:
    K = H(c || sk)          ← implicit rejection: return a "random-looking" key
  return K
```

**Why the re-encryption check?** It's the CCA barrier. Without it, an attacker could submit *mauled* ciphertexts and learn bits about `s` from the decapsulation oracle. With the check, malformed ciphertexts decapsulate to a deterministic but **useless** value `H(c || sk)` — the attacker learns nothing.

**Implicit rejection (the `H(c || sk)` branch)** is a deliberate protocol design choice in HHK: instead of returning an error on a malformed ciphertext, the decapsulator returns a value that looks pseudorandom to the attacker. This is what makes the proof go through — there's no error oracle to query.

ML-KEM-768's hashing uses **SHA3-256** and **SHAKE-256** extensively — these hash functions double as the randomness expanders (`H(pk||m)`), the key derivation (`H(m)`), and the implicit-rejection hash (`H(c||sk)`). The whole crypto is one noise-distribution module plus SHA-3 primitives.

## ML-KEM Parameter Sets (FIPS 203)

| Parameter set | `n` | `k` | `q`   | `η₁` | `η₂` | `d_u` | `d_v` | pk (B) | ct (B) | Security |
|---------------|-----|-----|-------|------|------|-------|-------|--------|--------|----------|
| ML-KEM-512     | 256 | 2  | 3329 | 3    | 2    | 10    | 4     | 800    | 768    | AES-128  |
| ML-KEM-768     | 256 | 3  | 3329 | 2    | 2    | 10    | 4     | 1184   | 1088   | AES-192  |
| ML-KEM-1024    | 256 | 4  | 3329 | 2    | 2    | 11    | 5     | 1568   | 1568   | AES-256  |

These are the post-quantum security levels NIST defined for the PQC process:

- **Level I**: AES-128 equivalent (~128-bit post-quantum)
- **Level III**: AES-192 equivalent
- **Level V**: AES-256 equivalent

The security analysis (in the FIPS 203 spec and the original Kyber spec) uses the BKZ lattice-reduction cost model. The core estimator — the "core-SVP" cost model (Becker et al., 2019) — gives each parameter set a margin > 2^128 / 2^192 / 2^256 gates for the best known attack (primal or dual attack against Module-LWE).

## Performance Comparison

Operation timings on a single core (Apple M1, 2023), all in microseconds:

| Algorithm      | Keygen | Encaps/Encrypt | Decaps/Decrypt | Public key | Ciphertext |
|----------------|--------|----------------|----------------|------------|------------|
| X25519 (ECDH)  | 21     | 52             | 117            | 32 B       | 32 B       |
| RSA-2048       | 2900   | 70             | 1500           | 256 B      | 256 B      |
| ML-KEM-512     | 24     | 38             | 30             | 800 B      | 768 B      |
| ML-KEM-768     | 33     | 47             | 39             | 1184 B     | 1088 B     |
| ML-KEM-1024    | 46     | 63             | 50             | 1568 B     | 1568 B     |

(Source: pqcrystals benchmarks; numbers vary by platform.)

ML-KEM-768's encapsulation is *faster* than X25519's at the level of crypto primitives. The catch is the wire bytes: a TLS ClientHello containing X25519+ML-KEM-768 hybrid key shares is ~1.2 KB longer than pure X25519. That's the cost of being quantum-resistant today.

## Implementation Notes

ML-KEM's reference implementation in `liboqs` (https://github.com/open-quantum-safe/liboqs) and the CRYSTALS team's AVX2 implementation (https://github.com/pq-crystals/kyber) are the two most-deployed production code paths.

Key implementation concerns:

1. **NTT-domain operations.** All polynomial multiplications happen in the Number-Theoretic Transform domain. The ring `Z_3329[X]/(X^256+1)` admits a fast NTT because `3329 = 2^8·13 + 1` (a "prime of the form `k·2^l + 1`"), so a primitive 256-th root of unity exists. The NTT is a Cooley-Tukey butterfly over `Z_3329`.

2. **Constant-time rejection sampling.** CBD is naturally constant-time, but the message-encoding bits need careful masking. Side-channel leaks in the compression step are a known foot-gun (the "KyberSlash" family of bugs).

3. **The `H(pk||m)` re-encryption.** Naive implementations recompute `A` from the seed during decaps. Caching it saves a NTT-based expansion per decaps — but the cache must be constant-time and per-key.

## TLS Hybrid Use

Production deployments (Chrome, Cloudflare, Apple iMessage PQ3, AWS KMS) use **hybrid KEMs**: the shared secret is `K = H(K_classical || K_PQ)`. This means breaking the connection requires breaking *both* X25519 and ML-KEM. The hybrid is needed during the transition window — ML-KEM's security margin is solid but unproven in the face of decades of cryptanalysis.

The IETF has standardized the hybrid in TLS 1.3 — see the `x25519_kyber768` codepoint in the IETF draft (`draft-ietf-tls-hybrid-design`) and the broader PQ-TLS work (`draft-ietf-pquip-pqt-hybrid-terminology`).

## References

- NIST FIPS 203 (final), *Module-Lattice-Based Key Encapsulation Mechanism Standard*, August 2024 — https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf
- Bos, Ducas, Kiltz, Lyubashevsky, Misoczki, Pietrzak, Schwabe, Sendrier, Sikevicius, *CRYSTALS-Kyber: a CCA-secure module-lattice-based KEM*, EuroS&PW 2018 — https://eprint.iacr.org/2017/634
- Hofheinz, Hövelmanns, Kiltz, *A Modular Analysis of the Fujisaki-Okamoto Transformation*, EUROCRYPT 2017 — https://eprint.iacr.org/2017/633
- Lyubashevsky, Peikert, Regev, *On Ideal Lattices and Learning with Errors over Rings*, EUROCRYPT 2010 — https://eprint.iacr.org/2012/230
- Langlois, Regev, *Worst-case to Average-case Reductions for Module-Lattices*, 2013 — https://eprint.iacr.org/2012/506
- Regev, *On Lattices, Learning with Errors, Random Linear Codes, and Journaling*, JACM 2009 (STOC 2005) — https://cse.nyu.edu/~regev/papers/qibo.pdf
- NIST PQC standardization project — https://csrc.nist.gov/projects/post-quantum-cryptography
- NIST PQC round 3 report (status of Kyber) — https://csrc.nist.gov/CSRC/media/Publications/nistir/8413/final/documents/nistir8413.pdf
- CRYSTALS-Kyber reference implementation (pq-crystals/kyber) — https://github.com/pq-crystals/kyber
- Open Quantum Safe (liboqs) — https://openquantumsafe.org/
- Becker, Ducas, Laarhoven, *The General Sieve Kernel and New Records in Lattice Reduction*, ASIACRYPT 2016 — https://eprint.iacr.org/2019/1461 (core-SVP cost model; updated cost estimator)
- Schwabe, Stebila, Thommes, *Post-Quantum WireGuard*, S&P 2021 — https://eprint.iacr.org/2020/1222

## Interview Questions

1. **What is the difference between a PKE and a KEM, and why does ML-KEM use the latter?**
2. **Walk through the Module-LWE problem. What does "module" refer to, and why use it instead of Ring-LWE?**
3. **Why does ML-KEM compress the ciphertext? What would happen if you skipped compression?**
4. **Explain the Fujisaki-Okamoto / HHK transform. Why is re-encryption on decapsulation required for IND-CCA2?**
5. **What is "implicit rejection" in the KEM transform, and how does it differ from returning an error code?**
6. **Why does ML-KEM use `Z_3329[X]/(X^256+1)` as its base ring? What properties of `q=3329` enable the NTT?**
7. **Give an estimate of the BKZ cost (in bits) of breaking ML-KEM-768, and the corresponding AES security level.**
8. **How would you deploy ML-KEM in a TLS 1.3 hybrid key exchange alongside X25519? What bytes change in the ClientHello?**
9. **ML-KEM-768's encapsulation is faster than X25519's. So why is post-quantum TLS slower in practice?**
10. **Describe a realistic side-channel attack on an ML-KEM implementation that fails to use constant-time compression.**
