# Homomorphic Encryption

Homomorphic Encryption (HE) is a family of public-key encryption schemes that let an untrusted server compute on ciphertexts *without ever decrypting them*. Given `Enc(m₁)` and `Enc(m₂)`, anyone holding the public key can produce `Enc(m₁ + m₂)` or `Enc(m₁ · m₂)`. The private key holder alone can later decrypt the result to recover `f(m₁, m₂)` for the function `f` evaluated during the homomorphic operations. This chapter covers the math, the schemes (BGV, BFV, CKKS), Gentry's bootstrapping trick, the noise budget that governs how much computation is possible, and where HE shows up in production today.

## A Taxonomy: Partial, Somewhat, and Fully Homomorphic

Encryption schemes have always supported *some* homomorphic property. RSA is multiplicatively homomorphic: `RSA(m₁) · RSA(m₂) mod n = RSA(m₁ · m₂ mod n)`. ElGamal is also multiplicatively homomorphic. Paillier is *additively* homomorphic: `E(m₁) · E(m₂) mod n² = E(m₁ + m₂)`. Each of these is *partially* homomorphic — they support exactly one operation.

A *somewhat* homomorphic encryption (SHE) scheme supports both addition and multiplication, but only a bounded number of multiplications before the ciphertext becomes undecryptable. A *fully* homomorphic encryption (FHE) scheme supports arbitrary computations — addition, multiplication, branching (via multiplication by 0/1 masks), arbitrary-depth circuits.

The first FHE scheme was Craig Gentry's, in his 2009 Stanford PhD thesis. Before Gentry, the consensus was that FHE was probably impossible. After Gentry, it was merely very slow.

```text
   Partial HE      Somewhat HE          Fully HE
   ──────────      ───────────          ────────
   RSA, Paillier   BGV, BFV, CKKS      Gentry 2009 (bootstrapped)
   +  or  ·        +  and  ·            arbitrary circuits
   unbounded       bounded mult.       unbounded depth (via refresh)
```

## The LWE and RLWE Foundations

Modern HE schemes are built on the Learning With Errors (LWE) problem and its ring variant (RLWE). The secret is a vector `s ∈ Z_q^n`. A ciphertext is a pair `(a, b)` where `a ← Z_q^n` is uniformly random and `b = ⟨a, s⟩ + 2·m + e` for a small noise term `e` sampled from a Gaussian (typically standard deviation ~3–8). Decryption computes `b - ⟨a, s⟩ = 2·m + e mod q`. Since `e` is small, rounding to the nearest even number recovers `m`.

The 2·m multiplier means we are using the low bits of `b - ⟨a, s⟩` to encode the message; the noise occupies the same low bits, but only as a small perturbation.

Ring-LWE replaces vectors with polynomials in `R_q = Z_q[x]/(x^N + 1)` for `N` a power of 2. The secret is a polynomial `s ∈ R_q`, the public mask is a uniformly random `a ∈ R_q`, and a ciphertext is `(a, b)` with `b = a·s + 2·m(x) + e(x)`. The polynomial arithmetic is O(N log N) via NTT (Number Theoretic Transform), making RLWE practical: a single ciphertext encrypts an N-element plaintext vector.

## Homomorphic Addition

Addition is trivial and noiseless up to a small growth. Given two ciphertexts `c₁ = (a₁, b₁)` and `c₂ = (a₂, b₂)` encrypting `m₁` and `m₂`, the componentwise sum `c_add = (a₁ + a₂, b₁ + b₂)` decrypts to:

```text
Dec(c_add) = (b₁ + b₂) - ⟨a₁ + a₂, s⟩
           = (2·m₁ + e₁) + (2·m₂ + e₂)
           = 2·(m₁ + m₂) + (e₁ + e₂)
```

This is exactly a valid ciphertext for `m₁ + m₂` with noise `e₁ + e₂`. Noise grows additively (each addition adds noise; in the worst case `n` additions of magnitude-`σ` noise produce noise of magnitude `√n · σ`).

## Homomorphic Multiplication

Multiplication is where the trouble starts. The product of two LWE ciphertexts is, by bilinearity:

```text
b₁ · b₂ = (a₁·s + 2·m₁ + e₁)(a₂·s + 2·m₂ + e₂)
        = a₁a₂·s² + 2·a₁·s·m₂ + 2·a₂·s·m₁ + 2·m₁·m₂ + (cross noise)
```

This is no longer an LWE ciphertext — it contains `s²` and `s·m` cross terms. The standard relinearization trick: precompute `s²` encrypted under the public key (this is the "evaluation key" or "relinearization key"), and after multiplication, replace the `s²` term with the encryption of `s²` times the appropriate factors, returning the ciphertext to a degree-1 form in `s`. The resulting ciphertext is a valid LWE encryption of `m₁ · m₂`, but the noise has grown quadratically — from `σ` to roughly `σ · √N · B` where `B` is the magnitude of the message coefficients.

```text
Noise after mul of two ciphertexts with noise σ₁, σ₂:
   σ_new ≈ σ₁ · σ₂ · N   (in the worst case)

Each multiplication roughly squares the noise. After d multiplications
(deep circuit), noise is σ^(2^d). This is the SHE barrier.
```

## The Noise Budget and Modulus Switching

Every ciphertext carries a "noise budget" — the ratio between the noise level and the modulus `q`. When noise exceeds `q/2`, decryption returns garbage. A scheme with modulus `q = 2^60` and initial noise `2^15` has a budget of 45 bits.

The crucial trick that makes modern SHE schemes usable is **modulus switching**. After each multiplication, instead of keeping the ciphertext at modulus `q`, we rescale to `q' = q / 2`. The noise is multiplied by `q'/q = 1/2`, halving it. The plaintext message, encoded in the high bits of `q`, is preserved.

```text
Before mul: noise = 2^15,  modulus = 2^60,  budget = 45 bits
After mul:  noise = 2^30,  modulus = 2^60,  budget = 30 bits
After mod-switch: noise = 2^29, modulus = 2^59, budget = 30 bits  (preserved!)
```

By choosing a chain of moduli `q_0 > q_1 > ... > q_L` and modulus-switching after each multiplication, we trade modulus bits for noise bits. A chain of length `L` supports `L` multiplications before the budget runs out. This is the **leveled FHE** model — fix the circuit depth in advance and choose the parameters accordingly.

## Gentry's Bootstrapping

Gentry's breakthrough was *bootstrapping*: a way to refresh a noisy ciphertext into a fresh one, at the cost of running the decryption circuit *homomorphically*. The key observation: the decryption function `Dec(c, s)` is itself a low-depth circuit (polynomial in `n`). If our scheme can evaluate its own decryption circuit, we can take a nearly-exhausted ciphertext `c`, encrypt the secret key `s` as `Enc(s)` (the "bootstrapping key"), and then evaluate `Dec(c, ·)` homomorphically — the output is a fresh ciphertext encrypting the same plaintext `m`, but with reduced noise.

The circular security assumption is: encrypting the secret key as part of the public key (`s` encrypted under itself) does not break the scheme. This is unproven in general but has held up under 15+ years of cryptanalysis and is now widely assumed.

```text
                       ┌──────────────┐
   c (noisy)  ───────► │  Evaluate     │ ───► c' (fresh)
                       │  Dec(c, ·)   │      same plaintext m
   Enc(s)    ───────► │  homomorph.  │      small noise
                       └──────────────┘

   Requires: scheme can evaluate its own Dec.
             Assumes: circular security (Enc(s) is safe).
```

Bootstrapping is the FHE equivalent of garbage collection — it caps the noise at a fixed ceiling, allowing arbitrary-depth circuits. The cost is enormous: each bootstrapping call is 100×–10000× slower than a single homomorphic multiplication. This is the bootstrapping bottleneck.

## The Major Schemes

Three families of FHE schemes are in active use, each with a different trade-off:

```text
Scheme   Plaintext     Output      Noise model       Typical use
──────   ─────────     ──────      ───────────       ────────────
BGV      Integer       Exact       Multiplicative   Binary circuits
BFV      Integer       Exact       Multiplicative   Arithmetic mod p
CKKS     Real/Complex  Approximate Rescaling-based  ML, stats
FHEW     Binary        Exact       Fast bootstrap   Boolean circuits
TFHE     Binary        Exact       Programmable BS  Comparison-heavy
```

**BGV** (Brakerski-Gentry-Vaikuntanathan, 2012) introduced scale-invariant noise growth and modulus switching. The plaintext is an integer ring `Z_p[x]/(x^N + 1)` (SIMD packing via Chinese Remainder Theorem on the plaintext ring).

**BFV** (Brakerski-Fan-Vercauteren, 2012) is the simplest to implement; it has the same noise-growth profile as BGV but a cleaner message-encoding scheme. BFV is the canonical "exact integer FHE" scheme — your ciphertext decrypts to the same integer you encrypted, with no approximation error.

**CKKS** (Cheon-Kim-Kim-Song, 2017) is the scheme of choice for ML workloads. It supports *approximate* arithmetic on real numbers. The plaintext is encoded as a complex (or real) vector; multiplication rescales by a factor `Δ` (the scaling factor, typically 2^40). Each rescale drops `log₂ Δ` bits of precision. After `L` multiplications, precision is exhausted. CKKS sacrifices the "exact decryption" property but gains 10–100× performance on real-valued computations. It is the scheme used by most encrypted-ML demos.

## Worked Example: BFV in Microsoft SEAL

```python
from seal import (
    EncryptionParameters, SchemeType, SEALContext,
    KeyGenerator, Encryptor, Decryptor, Evaluator, BatchEncoder,
    CoeffModulus, PlainModulus, Plaintext, Ciphertext,
)

# 1) Parameters: poly modulus degree N, plaintext prime p, bit-sizes for q chain
params = EncryptionParameters(SchemeType.BFV)
params.set_poly_modulus_degree(8192)
params.set_plain_modulus(PlainModulus.Batching(8192, 20))   # 20-bit plaintext prime
params.set_coeff_modulus(CoeffModulus.BFVDefault(8192))     # ~218-bit q

ctx = SEALContext(params)
keygen = KeyGenerator(ctx)
public_key, secret_key = keygen.public_key(), keygen.secret_key()
relin_keys = keygen.relin_keys()                            # relinearization key

encryptor = Encryptor(ctx, public_key)
evaluator = Evaluator(ctx)
decryptor = Decryptor(ctx, secret_key)
encoder = BatchEncoder(ctx)

# 2) Encode two integer vectors (each up to 8192 slots)
v1 = [3, 1, 4, 1, 5, 9, 2, 6, 0, 0, 0, 0]
v2 = [2, 7, 1, 8, 2, 8, 1, 8, 0, 0, 0, 0]
p1, p2 = Plaintext(), Plaintext()
encoder.encode(v1, p1)
encoder.encode(v2, p2)

c1, c2 = Ciphertext(), Ciphertext()
encryptor.encrypt(p1, c1)
encryptor.encrypt(p2, c2)

# 3) Homomorphic element-wise sum (noise grows additively)
c_add = Ciphertext()
evaluator.add(c1, c2, c_add)

# 4) Homomorphic element-wise product (noise grows quadratically,
#    then relinearize to keep the ciphertext in 2-component form)
c_mul = Ciphertext()
evaluator.multiply(c1, c2, c_mul)
evaluator.relinearize_inplace(c_mul, relin_keys)

# 5) Decrypt and decode
p_out = Plaintext()
decryptor.decrypt(c_add, p_out)
print("add:", encoder.decode_int32(p_out)[:8])     # [5, 8, 5, 9, 7, 17, 3, 14]

decryptor.decrypt(c_mul, p_out)
print("mul:", encoder.decode_int32(p_out)[:8])     # [6, 7, 4, 8, 10, 72, 2, 48]
```

The crucial point: the server holding only the public key and the ciphertexts `c1`, `c2` ran `add` and `multiply` and never saw the plaintext vectors. The owner of the private key learns only the *result* — not the inputs, if you arrange the protocol so.

## Performance Reality Check

As of 2024, on a modern Xeon, single-threaded timings for CKKS at N=2^16 with a multiplicative depth of L=4:

| Operation | Time |
|---|---|
| Encryption | 0.3 ms |
| Decryption | 0.1 ms |
| Homomorphic add | 0.02 ms |
| Homomorphic mul (before relinearize) | 0.5 ms |
| Relinearize | 1.5 ms |
| Rescale (mod-switch in CKKS) | 0.1 ms |
| Bootstrapping (CKKS) | ~6–10 seconds |
| Bootstrapping (TFHE, programmable) | ~10–30 ms |

The bootstrapping gap is what divides practical FHE use into two regimes. *Leveled* FHE (no bootstrapping) — fixed-depth circuits, a few hundred multiplications deep — runs at usable speeds for ML inference of small models: encrypted logistic regression or a few-layer MLP takes 10ms–1s per inference. Bootstrapped FHE for deep circuits is still 1000–10000× slower than plaintext compute.

## Applications

**Private Information Retrieval (PIR).** A client wants to fetch row `i` from a server's database without revealing `i`. With FHE, the client encrypts a selection vector `e_i` (1 at position `i`, 0 elsewhere), sends it to the server, the server computes the inner product of `e_i` with the database columns, returns one ciphertext per column. SealPIR (Microsoft Research, 2018) and OnionPIR layer optimizations (ciphertext packing, recursive retrieval) to bring 1MB database retrieval down to ~1 second over the wire.

**Encrypted ML Inference.** CKKS supports encrypted linear algebra: matrix-vector multiply, convolution, ReLU (via polynomial approximation). Cryptonets (2016) demonstrated encrypted MNIST inference; CryptoNets-CKKS pushes this to encrypted inference of small transformers. Throughput is ~10–1000× slower than plaintext — fine for high-sensitivity, low-frequency queries (medical diagnosis on encrypted patient records, anti-money-laundering scoring on encrypted transactions).

**Private Set Intersection (PSI).** Two parties each hold a set and want to learn the intersection without revealing anything else. HE-based PSI encrypts one party's set, the other party does homomorphic multiplications with polynomials that vanish on its own elements, and returns the result. Achieves bandwidth O(√n) per party, much better than the O(n) baseline.

**Cloud key management.** Conclave (Microsoft, 2021) and similar systems combine HE with secure enclaves (Intel SGX) to reduce the trust placed in either alone.

## Common Pitfalls

1. **Treating CKKS as exact.** CKKS ciphertexts decrypt to *approximate* plaintexts; the error is bounded but nonzero. Naively subtracting two CKKS ciphertexts that encode nearly-equal values can produce nonsense — this is the "CKKS disaster" of 2019 (Li and Micciancio). For exact comparison, use BFV or TFHE.

2. **Parameter selection without a noise budget.** Pick `q` too small and the circuit will fail mid-computation. Use the noise-flooding estimator in SEAL or `lcu_estimator.py` in OpenFHE rather than guessing.

3. **Forgetting relinearization.** After multiplication, the ciphertext is quadratic in `s` (size 3 instead of size 2). Relinearization uses the relinearization key to drop it back to linear. Skipping it doubles memory and halves throughput.

4. **Ignoring rotation keys.** SIMD-packed operations need "rotation keys" (galois keys) to shift elements within a ciphertext. Generating all N rotations costs significant key material — often gigabytes. Decide which rotations you need up front.

5. **Assuming FHE is the right tool.** For two-party computation on bounded inputs, MPC (Garbled circuits, GMW, SPDZ) is typically 10–100× faster. FHE's strength is the *one-way, no-interaction* model — perfect for asymmetric workloads like PIR.

6. **Trusting bootstrapping to be cheap.** Even with TFHE's programmable bootstrapping (10 ms), bootstrapping after every NAND gate is a 10000× slowdown over plaintext. Most circuits only bootstrap every few layers, not after every gate.

## References

- Craig Gentry, "[A Fully Homomorphic Encryption Scheme](https://crypto.stanford.edu/craig/craig-thesis.pdf)" (PhD thesis, Stanford 2009)
- Zvika Brakerski, Craig Gentry, Vinod Vaikuntanathan, "[Fully Homomorphic Encryption without Bootstrapping](https://eprint.iacr.org/2011/277)" (2011) — BGV
- Junwoo Chung, Zvika Brakerski, "[An FHE Primer](https://homomorphic-encryption.org/wp-content/uploads/2018/01/FHE-Primer.pdf)" (2021)
- Jung Hee Cheon, Andrey Kim, Miran Kim, Yongsoo Song, "[Homomorphic Encryption for Arithmetic of Approximate Numbers](https://eprint.iacr.org/2016/421)" (CKKS, 2017)
- [Microsoft SEAL 4.1 documentation](https://www.microsoft.com/en-us/research/project/microsoft-seal/)
- [OpenFHE: Open-Source FHE Library](https://openfhe.org) — successor to PALISADE, BFV/BGV/CKKS/TFHE all in one
- Ilaria Chillotti, Nicolas Gama, Mariya Georgieva, Malika Izabachène, "[TFHE: Fast Fully Homomorphic Encryption Library](https://tfhe.github.io/tfhe/)" (2016–2024)
- Sameer Wagh, "[Piranha: A GPU Platform for Cryptographic Computation](https://eprint.iacr.org/2022/347)" (2022) — 10–100× GPU acceleration of FHE
- Hao Chen, Ilaria Chillotti, Yongsoo Song, "[Secure Quantized Inference on FHE](https://eprint.iacr.org/2022/933)"
- Microsoft Research, "[SealPIR: A Computational PIR library](https://github.com/microsoft/SealPIR)"
