# ML-DSA (Dilithium) — NIST FIPS 204

ML-DSA (Module-Lattice-Based Digital Signature Algorithm) is the NIST FIPS 204 (2024) standard for post-quantum signatures. It originated as CRYSTALS-Dilithium by Ducas, Kiltz, Lyubashevsky, Schwabe, and others, and was selected by NIST in 2022 as the primary PQC signature scheme. This page covers the Module-SIS problem, the Fiat-Shamir-with-aborts paradigm, the commitment/challenge/response structure, parameter sets, and a comparison with RSA, ECDSA, and EdDSA.

## Why ML-DSA Exists

Pre-quantum signatures — RSA-PSS, ECDSA, Ed25519 — are all broken by Shor's algorithm. A post-quantum replacement must:

1. **Reduce to a quantum-hard problem.** ML-DSA reduces to Module-SIS (a.k.a. Module-SIS over `Z_q[X]/(X^256+1)`).
2. **Be fast enough to use in TLS, X.509, code signing.** A signature of 2.5 KB is annoying for X.509 chains; 40 KB (SLH-DSA) is unusable for many use cases.
3. **Have deterministic signing with strong unforgeability under chosen-message attack (SUF-CMA).**
4. **Avoid RNG dependence in signing.** Dilithium is deterministic — no RFC 6979-style nonce hash needed, because the "nonce" is derived from the message and secret key, and rejection sampling removes the bias.

Dilithium (the name) refers to the *dilithium crystal* from Star Trek — a fictional power source — chosen by the designers as a memorable, untrademarked name.

## The Module-SIS Problem

The Module-Short-Integer-Solution problem over the ring `R_q = Z_q[X]/(X^256+1)` is: given `A ∈ R_q^(k×n)` sampled uniformly, find a *nonzero* short vector `z ∈ R_q^n` such that

```
A · z ≡ 0   mod q
```

where "short" means the `ℓ₂` (or `ℓ_∞`) norm of `z` (interpreted as a vector of integers in `Z^256`) is below a bound `B`.

Recall the plain Short Integer Solution (SIS): given `A ∈ Z_q^(m×n)`, find nonzero `z ∈ {-1,0,1}^m` (or low-norm) with `A·z = 0 mod q`. SIS is the *average-case* dual of LWE; both reduce from worst-case lattice problems (SIS from SIVP, LWE from GapSVP).

Ring-SIS shrinks the matrix `A` to a ring element. Module-SIS is a vectorized version: a `k × n` matrix of ring elements, with the secret `z ∈ R_q^n` a vector of small ring elements. The same hardening story as Module-LWE applies — the security reduces to plain SIS without depending on ideal-lattice assumptions.

### Why SIS gives signatures

A SIS-based signature scheme works as a σ-protocol with Fiat-Shamir:

- Public key: a random matrix `A` (short description via seed) and a vector `t = A·(s_1, s_2)ᵀ` where `s_1, s_2` are short secrets.
- Signing: prover samples short `y` (the commitment), computes challenge `c` (from `y, message`), computes response `z = y + c·s_1`. To reveal `s_1` from `z = y + c·s_1` where `y` is uniform, the verifier learns nothing; to forge a signature without `s_1` you'd have to solve SIS.

The catch: `z = y + c·s_1` is *not* short in general — adding a random `s_1` shifts the distribution away from uniform. Lyubashevsky's **Fiat-Shamir with aborts** solves this via rejection sampling.

## Fiat-Shamir with Aborts

The construction is due to Lyubashevsky (2009, 2012). The idea is simple but powerful: **sometimes reject the signature and re-sample `y`**. Rejection sampling is the price of zero-knowledge.

```
Signature of message μ with secret s_1:

  loop:
    y ← sample_short()                    # commitment
    w = A·y                               # first-round "commitment" value
    c = H(μ || w)   ∈ R_q                 # challenge, derived via Fiat-Shamir
    z = y + c·s_1                         # response

    if ‖z‖_∞ > γ_2 - β:                   # too big — REJECT, retry
      continue

    # Optional: use a "hint" h so verification can recover the high bits
    return (z, h, c)
```

The math of rejection: for a uniformly-random `c·s_1` of width `β`, the sum `y + c·s_1` has the same distribution as `y` *except* within `β` of the rejection boundary `γ_2 - β`. Conditioning on acceptance, the marginal distribution of `z` is statistically close to the distribution of `y` — which is uniform over the "short" set — independent of `s_1`. This is what gives zero-knowledge.

The "with aborts" idea is: it's fine to restart (we lose ~50% of attempts on average, but never produce a too-large `z` that would leak `s_1`). The expected number of trials is constant (typically 2–7) per signature.

### Why this gives signatures — the verification trap

To forge a signature `(z, c, h)` on a new message `μ`, an attacker needs to produce `z`, `c` such that `A·z = c·t + w'` where `w'` is consistent with the hint `h`, and `c = H(μ || w')` (Fiat-Shamir's hash binding). The probability of solving this without knowing `s_1` reduces to SIS: producing *short* `z` with `A·z ≡ something derived from c·t`.

```
        Verification flow:
  ┌──────────────────────────────────────────────────────────────┐
  │  Input:  μ, sig=(z, h, c)                                     │
  │  Step 1:  c' = H(μ || w_hat), where                            │
  │             w_hat = A·z - c·t   recomputed from hint h          │
  │  Step 2:  Check c' == c                                          │
  │  Step 3:  Check ‖z‖_∞ ≤ γ_2 - β  (the bound we enforced)        │
  │  Step 4:  Check the hint h is well-formed                        │
  │  Step 5:  If all checks pass, ACCEPT                            │
  └──────────────────────────────────────────────────────────────────┘
```

If the attacker could produce `(z, c)` such that `A·z = c·t + w` for a fresh `c`, they'd have a short `z` with `A·z - c·t = w` having a consistent hint. This is the SIS instance: the difference between two short vectors landing on `c·t`. The hardness bound translates to SIS, which reduces to worst-case lattice problems (SIVP).

## The ML-DSA Key Generation

```
seed  ← {0,1}^256          (32 random bytes)
ρ     ← SHAKE-256(seed || 1)   (seed for A, a k×l matrix of ring elements)
K     ← SHAKE-256(seed || 2)   (used to re-derive s_1, s_2 in sign-time)
s_1   ← sample from CBD or uniform-ternary in R_q^l       (secret)
s_2   ← sample from CBD or uniform-ternary in R_q^k       (secret)
t     = A·s_1 + s_2 ∈ R_q^k                                 (public)

pk = (ρ, t_1, t_0)            ← ρ plus "high bits" t_1 and "low bits" t_0 of t
sk = (ρ, K, s_1, s_2, t_0)
```

The vector `t` is split into high (`t_1`) and low (`t_0`) halves because:
- Publishing only `t_1` of `t` shrinks the public key.
- During signing, we need to use the *low bits* `t_0` (along with the hint `h`) so the verifier (who only has `t_1`) can still recover the high bits of `w` consistent with `t`.

The decomposition `t = t_1 · 2^d + t_0` with `d=13` keeps `t_1` small enough for the public key while `t_0` (kept secret) handles the remainder.

## Signing in Detail

```
Sign(sk, M):
  ρ, K, s_1, s_2, t_0 ← sk
  A = Expand(ρ)                  # k × l matrix in NTT domain

  μ = SHAKE-256(r ‖ M)            # 384-bit message digest; r = K || ρ || ... 
                                  # see FIPS 204 §7.4.2 for exact construction

  retry loop:
    y ← sample_y()                # uniform in S'_γ1, ||y||_∞ < γ_1
    w_1 = HighBits(A·y)           # take the top bits of each coefficient

    c ← H(μ ‖ w_1)               # challenge in the "challenge set" — small ring element
    c^NTT ← NTT(c)               # transform for fast multiplication

    z = y + c·s_1                # in coefficient form
    if ‖z‖_∞ ≥ γ_2 - β:
      continue                   # reject and retry

    # Compute the hint h
    r_0 = LowBits(w - c·s_2)
    if ‖r_0‖_∞ ≥ γ_2 - β:
      continue                   # reject and retry

    h = MakeHint(r_0, w - c·s_2) # needed by the verifier to reconstruct w_1 from w
    if # of non-zero positions in h > ω:
      continue                   # reject — too many hints would blow up the signature

    return σ = (z, h, c)
```

Two rejection conditions:
1. `‖z‖_∞ ≥ γ_2 - β` — the response z must stay short.
2. `‖r_0‖_∞ ≥ γ_2 - β` — the low bits `r_0 = LowBits(w - c·s_2)` must stay small enough that the hint `h` works.
3. Hint count ≤ `ω` — caps the size of the hint vector.

The **hint** is a crucial optimization. Without it, the verifier would have to compute the *exact* `w = A·y` from `z` (since `w ≈ A·z - c·t`), but `t` is only known up to its high bits (`t_1`). The hint `h` is a sparse binary vector indicating which coefficients need a +1 correction to make `HighBits(w_computed) = w_1`. This trick is the central innovation that lets ML-DSA keep both small public keys *and* small signatures.

## Verification in Detail

```
Verify(pk, M, σ = (z, h, c)):
  ρ, t_1, _ ← pk

  A = Expand(ρ)

  μ = SHAKE-256(r ‖ M)
  c' = H(μ ‖ w_1_recomputed)

  # Step 1: re-derive w_1 using the hint
  # z^NTT, c^NTT
  z^NTT ← NTT(z)
  c^NTT ← NTT(c)
  w_approx = A·z^NTT - t_1 · 2^d · c^NTT   # in NTT domain
  w_coeff = InvNTT(w_approx)
  w_1_recomputed = UseHint(h, w_coeff)    # apply the +1 corrections at the hint positions

  # Step 2: check c is correct
  if c' != c:
    reject
  if ‖z‖_∞ ≥ γ_2 - β:
    reject
  if # of non-zero positions in h > ω:
    reject
  accept
```

The trick: knowing `t_1` (the *high bits* of `t`), `A`, and the response `z`, the verifier computes `A·z - t_1·2^d·c = A·(y + c·s_1) - t·c + t_0·c = A·y + c·(s_1·A - t) + t_0·c = w - c·s_2 + t_0·c`. The hint then recovers the *high bits* of `w` from this noisy quantity, which gives back the `w_1` that the signer committed to.

## ML-DSA Parameter Sets (FIPS 204)

| Parameter set | `n` | `(k, ℓ)` | `q`    | `(γ_1, γ_2)` | d | β | pk (B) | sig (B) | Security |
|---------------|-----|----------|--------|---------------|---|---|--------|---------|----------|
| ML-DSA-44     | 256 | (4, 4)   | 8380417| (2^17, 2^16)  | 13| 78| 1312   | 2420    | AES-128  |
| ML-DSA-65     | 256 | (6, 5)   | 8380417| (2^19, 2^17)  | 18| 88| 1952   | 3293    | AES-192  |
| ML-DSA-87     | 256 | (8, 7)   | 8380417| (2^19, 2^17)  | 18|120| 2592   | 4595    | AES-256  |

Notes on the parameters:

- `q = 8380417 = 2^23 - 2^13 + 1`. This prime has the form needed for a fast NTT over a 256-element ring (`q ≡ 1 mod 2^8`), AND was chosen such that `q` itself is large enough to fit the wide commitments `γ_1` needed for high rejection-sampling acceptance probability. The dilithium prime is one of the few primes that gives both a clean NTT and a wide enough modulus for the commitment width.
- `ω` (the hint sparsity cap) is 80 for ML-DSA-44 and 55, 75 for ML-DSA-65/87 respectively.
- The "domain separator" hash prefix `r = SHAKE-256(ρ || K || ...)` ensures the message digest `μ` is tied to the specific key.

## Comparison to RSA / ECDSA / EdDSA

| Scheme       | pk size | sig size | Sign (µs) | Verify (µs) | Hard problem            | Quantum |
|--------------|---------|----------|-----------|-------------|--------------------------|---------|
| RSA-2048     | 256 B   | 256 B    | 2700      | 50          | Factoring                | broken  |
| ECDSA P-256  | 33 B    | 64 B     | 130       | 320         | ECDLP                    | broken  |
| Ed25519      | 32 B    | 64 B     | 50        | 1500 (batched: 1.5×)  | ECDLP          | broken  |
| ML-DSA-44    | 1312 B  | 2420 B   | 240       | 90          | Module-SIS               | safe    |
| ML-DSA-65    | 1952 B  | 3293 B   | 350       | 130         | Module-SIS               | safe    |
| ML-DSA-87    | 2592 B  | 4595 B   | 500       | 200         | Module-SIS               | safe    |
| SLH-DSA-128f | 32 B    | 17088 B  | 12000     | 12000       | SHA-3 collision          | safe    |

(Sources: pq-crystals benchmarks; FIPS 204 spec; FIPS 205 spec.)

Notable: ML-DSA *verifies faster than Ed25519* in single-signature mode. The cost tradeoff is bytes: an ML-DSA-65 signature is ~50× the size of Ed25519's. For X.509 certificate chains this is the dominant overhead; for code-signing protocols (e.g., package signatures) it's fine.

## Implementation Notes

Reference implementations:

- `pq-crystals/dilithium` (https://github.com/pq-crystals/dilithium-round3) — the canonical AVX2 implementation
- `liboqs` (https://openquantumsafe.org) — production wrapper
- `oqs-provider` for OpenSSL 3.x — exposes ML-DSA through the standard `EVP_PKEY` API

Key implementation concerns:

1. **Constant-time rejection sampling.** The decision `‖z‖_∞ ≥ γ_2 - β` must not leak timing. Naive implementations can leak acceptance probability per attempt.
2. **The `SHAKE` seed-expansion.** `A`, `s_1`, `s_2`, `y` are all derived from SHAKE-128 / SHAKE-256. These are the dominant cost — a sign operation runs ~5 KB of SHAKE input.
3. **NTT-domain arithmetic.** All matrix-vector products happen in NTT form. Dilithium's `q = 2^23 - 2^13 + 1` admits a 256-element NTT using a primitive root `g = 1757193` (per FIPS 204 Appendix A).
4. **Verification batchedness.** Dilithium verification is *not* naturally batchable like Ed25519, because each verification involves a separate hash.

## Standards Status and Real-World Use

ML-DSA was standardized in **FIPS 204 (August 2024)** alongside FIPS 203 (ML-KEM) and FIPS 205 (SLH-DSA). The NIST PQC migration guidance recommends:

- **ML-DSA-65** as the default (Level III security) for general-purpose signatures.
- **ML-DSA-87** for higher assurance.
- Hybrid deployment (e.g., ML-DSA-65 + Ed25519) during the transition period; standardized in IETF drafts (`draft-ietf-lamps-pq-hybrid-x509`).

Production deployments: Cloudflare's code signing (2024+), AWS KMS (2024), Signal's PQXDH (uses ML-KEM, not ML-DSA — they kept Ed25519 for signatures due to bandwidth). Many TLS certificate authorities (DigiCert, Sectigo, Let's Encrypt) are planning ML-DSA / hybrid certificate issuance in 2025–2026.

The NSA's CNSA 2.0 suite mandates ML-DSA-65 (or higher) for new national-security systems starting 2030.

## References

- NIST FIPS 204 (final), *Module-Lattice-Based Digital Signature Standard*, August 2024 — https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.pdf
- Ducas, Kiltz, Lyubashevsky, Pépin, Schwabe, Seiler, Stehlé, *CRYSTALS-Dilithium: A Lattice-Based Digital Signature Scheme*, TCHES 2018 — https://eprint.iacr.org/2017/633
- Lyubashevsky, *Fiat-Shamir with Aborts: Applications to Lattice and Factoring-Based Signatures*, ASIACRYPT 2009 — https://www.iacr.org/archive/asiacrypt2009/59120559/59120559.pdf
- Lyubashevsky, *Lattice Signatures without Trapdoors*, EUROCRYPT 2012 — https://eprint.iacr.org/2011/189
- NIST PQC standardization project — https://csrc.nist.gov/projects/post-quantum-cryptography
- NIST IR 8413 (Round 3 PQC status report) — https://nvlpubs.nist.gov/nistpubs/ir/2022/NIST.IR.8413.pdf
- CRYSTALS-Dilithium reference implementation — https://github.com/pq-crystals/dilithium
- Schwabe et al., *Post-Quantum WireGuard*, S&P 2021 — https://eprint.iacr.org/2020/1222
- Bellare, Neven, *Multi-Signatures in the Plain Public-Key Model*, CCS 2006 (RSA-FDH attack model reference) — https://eprint.iacr.org/2006/172
- Langlois, Regev, *Worst-case to Average-case Reductions for Module-Lattices*, 2013 — https://eprint.iacr.org/2012/506
- NSA CNSA 2.0 — https://media.defense.gov/2022/Sep/07/2003071834/-1/-1/0/CSA_CNSA_2.0_ALGORITHMS_.PDF

## Interview Questions

1. **What is the Module-SIS problem, and why is it appropriate for signatures while Module-LWE is used for encryption?**
2. **Walk through the Fiat-Shamir-with-aborts paradigm. Why is rejection sampling necessary, and what does it achieve for zero-knowledge?**
3. **What is the "hint" in Dilithium signatures, and why is it needed? What happens if you remove it?**
4. **Dilithium's signing time has a small probability of restarting. Estimate the expected number of iterations and explain the security implications.**
5. **Why does Dilithium use `q = 2^23 - 2^13 + 1`? What two properties does this prime give?**
6. **Compare ML-DSA-65 with Ed25519: bytes, signing speed, verification speed. What are the practical trade-offs for a code-signing deployment?**
7. **Describe how a malicious implementation could leak the secret key via the rejection sampling timing.**
8. **Dilithium is deterministic. Why is this safer than ECDSA with a random nonce, and what failure mode did ECDSA's randomness have (e.g., Sony PS3)?**
9. **What is the difference between ML-DSA, Falcon, and SLH-DSA? When would you pick one over the others?**
10. **How would you deploy hybrid ML-DSA-65 + Ed25519 in an X.509 chain? What bytes change in a certificate?**
