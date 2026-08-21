# Secure Multi-Party Computation (MPC)

Secure multi-party computation (MPC) lets `n` mutually-distrusting parties jointly compute a function `f(x_1, ..., x_n)` of their private inputs while revealing *only* the output — nothing about any individual input beyond what the output already implies. The question was posed by Yao in 1982 as the *millionaires' problem*: two billionaires want to learn who is richer without disclosing their wealth. Since then, MPC has graduated from a theoretical curiosity to production infrastructure: it backs privacy-preserving analytics at Google, ad-conversion measurement across ad platforms, threshold custody at every major crypto exchange, and the BEPSE / Visa-Eagle-ACME systems for fraud detection across banks. This page covers the four canonical constructions — Yao's garbled circuits, the GMW protocol, the BGW protocol, and the SPDZ family — explains how secret sharing and oblivious transfer fit in, and gives the engineering trade-offs that determine which protocol to use in which setting.

## The MPC Model

A secure computation problem is specified by `(n, t, f, x_1..x_n)` where:

- `n` parties `P_1, ..., P_n` each hold a private input `x_i`.
- The adversary controls up to `t` parties and behaves either *semi-honestly* (follows the protocol, tries to learn more from the transcript) or *maliciously* (deviates arbitrarily).
- The function `f` is to be computed so that no party learns more than `f(x_1, ..., x_n)`, computed with respect to a simulator that has only the party's input and the output.

Two threshold regimes dominate:

- **Honest majority** (`t < n/2`): achievable with information-theoretic security (BGW, CCD).
- **Dishonest majority** (`t < n`): requires computational assumptions; the gold standard is SPDZ and its successors.

The semi-honest case is dramatically cheaper than the malicious case, and almost all production MPC pipelines use either semi-honest protocols with separate cut-and-choose / MAC verification bolted on, or pre-processing models where the expensive parts (multiplication triples, Beaver shares) are generated offline.

## Secret Sharing: The Foundation

Every MPC protocol reduces to how arithmetic values are distributed among parties. Two sharing schemes underlie almost everything that follows.

### Shamir Secret Sharing

For `n` parties tolerating `t` corruptions, the dealer picks a random polynomial `f(X) \in \mathbb{F}_p[X]` of degree `t` with `f(0) = s` and gives `f(i)` to party `P_i`. Any `t+1` parties can reconstruct `s` by Lagrange interpolation; any `t` or fewer learn *nothing* about `s`. The key properties:

- **Addition is local**: if `P_i` holds `f(i)` and `g(i)` for shares of `s, s'`, then `f(i) + g(i)` is a share of `s + s'`. No interaction.
- **Multiplication is non-local**: `f(X)g(X)` has degree `2t`, so re-sharing to reduce the degree back to `t` requires interaction. This is the central difficulty of BGW.

```python
# Shamir secret sharing (n=5, t=2), illustrative
import random, sympy
p = sympy.nextprime(2**64)

def share(s, n, t, p):
    coeffs = [s] + [random.randrange(p) for _ in range(t)]
    return [(i, horner(coeffs, i, p)) for i in range(1, n+1)]

def reconstruct(shares, p):
    # Lagrange interpolation at X = 0
    secret = 0
    for i, (xi, yi) in enumerate(shares):
        num = den = 1
        for j, (xj, _) in enumerate(shares):
            if i == j: continue
            num = (num * (-xj)) % p
            den = (den * (xi - xj)) % p
        secret = (secret + yi * pow(den, -1, p) * num) % p
    return secret % p
```

### Additive (a.k.a. CN) Sharing

The simplest scheme: pick `r_1, ..., r_{n-1} \\in \mathbb{F}_p` uniformly at random, set `r_n = s - \sum_{i<n} r_i \mod p`, and give `r_i` to `P_i`. Any `n-1` shares are statistically uniform; reconstruction is just summation. This is what SPDZ uses internally. Multiplication requires a *triple* `(a, b, c)` with `c = ab` shared among the parties; see SPDZ below.

## Yao's Garbled Circuits (2-Party, Boolean)

Yao's protocol is the foundation of all two-party boolean MPC. One party (the *garbler*) encrypts a Boolean circuit gate-by-gate into a *garbled circuit*; the other party (the *evaluator*) obliviously obtains the input wire labels corresponding to its own input and decrypts the circuit gate by gate.

```
        Garbler (input x)                    Evaluator (input y)
        ==============                      ==================

   (1)  Construct garbled circuit C'
        Pick 2 random labels per wire,
        encrypt each gate's truth table
        under the input labels.
        Send C' to evaluator.            -->   (2) Receive C'.
                                                   Needs labels for y.
   (3)  Engage in 1-out-of-2 OT for
        each input bit of y, playing OT
        sender with the two labels for
        that wire as the messages.      -->   (4) Receive the label for
                                                   each bit of y via OT.
                                                   Never learns x's labels;
                                                   garbler never learns y.

                                             (5) Evaluate C' gate by gate,
                                                 obtaining the output wire
                                                 label for each gate's output.
                                             (6) Translate output label to
                                                 bit, share with garbler.

   Both parties now hold f(x,y).
```

The detailed construction, optimizations (free-XOR, half-gate, point-and-permute), and cut-and-choose for malicious security are covered in [Garbled Circuits](./garbled-circuits.md). The key point for this page: Yao scales to *two parties*, is naturally Boolean, and is the basis for most "fast-asymmetric" MPC systems (where one party does the heavy lifting). For three or more parties, GMW or BGW are usually better.

## The GMW Protocol (Multi-Party, Boolean)

Goldreich, Micali, and Wigderson (1987) generalised Yao's idea to `n` parties. Each input bit `x_i` is *additively* shared among all `n` parties: `P_j` holds `x_{i,j}` with `\bigoplus_j x_{i,j} = x_i`. XOR gates are free: each party locally XORs their shares. AND gates require interaction via oblivious transfer.

### An AND Gate in GMW

Consider parties `P_1, ..., P_n` holding shares `a_j, b_j` of bits `a, b` so that `a = \bigoplus_j a_j`, `b = \bigoplus_j b_j`. To compute a sharing of `c = ab`:

```
For each pair (i, j), i < j, run a 1-out-of-4 OT in which
  P_i (OT sender) offers four messages
    m_{a_i, b_i} = a_i*b_i  XOR  (a "trapdoor" piece r_{ij})
  P_j (OT receiver) picks the index (a_j, b_j) and recovers
    m_{a_i, b_i}  XOR  (something chosen by P_i)

Concretely: P_j receives (a_i * b_j) XOR r_{ij}, i.e., one of
the cross-terms. After all pairwise OTs, each party sums up
(XOR) their share:
  c_i = a_i b_i  XOR  XOR_{j<i} r_{ji}  XOR  XOR_{j>i} (a_i b_j XOR r_{ij})
                                              ^^^ what P_i got from OT with P_j

This satisfies  c = XOR_i c_i  =  XOR_i (a_i b_i)  XOR  XOR_{i<j} (a_i b_j XOR a_j b_i)
                                  =  ab.
```

The cost of one AND gate is `n(n-1)/2` instances of 1-out-of-4 OT. With OT extension (see [Oblivious Transfer](./oblivious-transfer.md)), this amortises to a handful of symmetric hash operations per AND gate. The GMW protocol is **round-linear in the circuit depth**: each layer of AND gates needs one round of communication. This is fine for shallow circuits but prohibitive for deep ones — the modern trend is to batch rounds via *gate scheduling* or use arithmetic sharing (BGW/SPDZ) which has fewer rounds per multiplication when combined with Beaver triples.

### The BGW Protocol (Honest Majority, Arithmetic)

Ben-Or, Goldwasser, and Wigderson (1988) — and independently Chaum, Crépeau, and Damgård (CCD) — gave the first *information-theoretically* secure MPC protocol tolerating `t < n/3` corruptions (BGW broadcast) or `t < n/2` (BGW without broadcast, assuming private channels). It uses Shamir secret sharing over `\mathbb{F}_p`, where `p > n` so each party gets a distinct evaluation point `1, 2, ..., n`.

For addition gates: each party locally adds shares; the resulting polynomial has degree `t` (correct degree).

For multiplication gates: each party `P_i` locally computes `c_i = a_i \cdot b_i`, the product of their shares. The product polynomial `a(X) \cdot b(X)` has degree `2t`, so `\{c_i\}` are evaluations of a degree-`2t` polynomial. To recover shares of `ab` with degree `t`, parties perform a **degree-reduction step**: each `P_i` reshares `c_i` as the value of a fresh degree-`t` polynomial `d_i(X)` evaluated at the other parties' indices, and each `P_j` computes a Lagrange-weighted sum `\sum_i \lambda_i d_i(j)` of all the received shares. The result is a share of `ab` in the original degree-`t` scheme.

```
BGW multiplication (degree reduction):
  Input : parties hold deg-t shares a_i, b_i of a, b
  Step 1: each P_i computes c_i = a_i * b_i  (locally)
          -> {c_i} are shares of (a*b) under deg-2t poly
  Step 2: P_i Shamir-shares c_i to all parties with deg-t:
          sends d_{i,j} = d_i(j) to P_j   where d_i(0) = c_i
  Step 3: P_j computes new_share = sum_i lambda_i * d_{i,j}
          (the lambda_i are the Lagrange coefficients at 0
           for indices 1..n restricted to a degree-t committee)
  Result: {new_share_j} is a deg-t sharing of a*b.
```

BGW multiplication needs 2 rounds and `O(n^2 \log n)` field operations; with batching (Gennaro-Rabin-Rabin improvements, Beaver's circuit randomisation) this drops to `O(\log n)` rounds overall. The honest-majority assumption is essential: with `t \ge n/2`, the polynomial `a(X) \cdot b(X)` of degree `2t \ge n` is no longer uniquely determined by the `n` evaluations, so degree reduction fails.

## Comparison of Approaches

| Protocol | Parties | Sharing | Adversary | Security | Cost model | Typical use |
|----------|---------|---------|-----------|----------|------------|-------------|
| Yao (GC) | 2 | boolean | semi-honest (extendable) | computational | OT + symmetric crypto per AND gate | 2-party circuits, asymmetric workloads |
| GMW | n | boolean, additive | semi-honest / malicious | computational | 1-out-of-4 OT per AND gate per pair | Multi-party boolean, shallow circuits |
| BGW | n | Shamir, arithmetic | honest-majority | information-theoretic | 2 rounds per mult; `O(n^2)` comm per gate | Privacy-preserving statistics, low-bandwidth |
| SPDZ | n | additive, arithmetic | dishonest majority | computational | one triple per mult (offline) + MAC check | Production-grade, dishonest-majority |

## The Dishonest-Majority Model: SPDZ

The SPDZ protocol (pronounced "Speedz"; Damgård, Pastro, Smart, Zakarias, 2012) is the workhorse of modern dishonest-majority MPC. Its architecture cleanly separates the work into an *offline* phase (slow, generates correlated randomness) and an *online* phase (fast, consumes it).

### SPDZ Triple Generation (Offline)

The offline phase produces *multiplication triples*: shared triples `(a, b, c)` with `c = ab` where `a, b` are uniformly random and unknown to any party. The standard realisation is *somewhat homomorphic encryption* (HE): one party encrypts `a` and `b` under a Paillier-like scheme, computes `Enc(c) = Enc(a) \cdot Enc(b)` using the homomorphism, and shares `Enc(c)` (after fresh masking) for online use. Each triple is tagged with a *information-theoretic MAC* `\gamma_a, \gamma_b, \gamma_c` shared so that any adversary who lifts a share is caught with overwhelming probability by the MAC check at the end of the protocol.

### SPDZ Online Multiplication

Given a shared triple `(a, b, c)` and shared inputs `x, y` to multiply, Beaver's trick reduces multiplication to opening two values:

1. Open `\rho = x - a` and `\sigma = y - b`. Both `\rho` and `\sigma` are random masks, so opening them reveals nothing about `x, y` (since `a, b` were uniformly random).
2. Compute `z = xy = c + \rho b + \sigma a + \rho\sigma` locally on shares.

Because `(a, b, c)` was shared as a triple with MAC, the final MAC check at protocol-end catches any deviation. The online cost per multiplication is *one round* and `O(n^2)` field-element openings — independent of the original sharing.

### Comparison: GMW + OT vs SPDZ

GMW with malicious-secure OT extension (the *TinyOT* / *SPDZ^MASCOT* family) does Boolean circuits; SPDZ does arithmetic. For a circuit that is mostly additions and multiplications on field elements (like a deep neural net's matrix-vector products), SPDZ is several× faster. For bit-level operations (comparisons, AES, hash functions), GMW with active-security OT extension is usually better. Production systems often *interoperate the two*: a high-level SPDZ computation drops into a Yao-garbled AES sub-circuit for hash invocations.

## Applications

### Private Set Intersection (PSI)

PSI computes `A \cap B` where Alice has `A` and Bob has `B` — and neither learns anything outside the intersection. The most efficient PSI protocols (Chandran et al., 2021) work by Alice garbling a Bloom filter or a cuckoo-hash structure and Bob evaluating it via OT — essentially an asymmetric Yao protocol with O(n log n) OT calls rather than O(n) on a circuit of size O(n^2). PSI powers privacy-preserving ad attribution (Google's Ads Hub prototype, Meta's PSI for ad measurement), contact discovery (Signal's private contact discovery, with SE scribble^s), and federal-government data sharing.

### Privacy-Preserving Machine Learning

MPC for ML inference is dominated by two paradigms:

- **2-party (Yao)**: CryptGPU (Tan et al., 2022), CrypTFlow (Rathee et al., 2020), Delphi (Mireshghallah et al., 2020). One party (server) holds the model; the other (client) holds the input. Garble the model once; the client evaluates with one round of OT for its input. Throughput on a ResNet-50 is in the tens of inferences per second per GPU.
- **3-party (BGW-style, honest majority)**: SecureNN (Wagh et al., 2018), ABY3 (Mohassel & Rindal, 2018). Three non-colluding data centres share the computation; no party alone can reconstruct. Order-of-magnitude faster than 2-party, at the cost of requiring three mutually-suspicious operators.

### Threshold Signing & MPC Custody

Every major exchange's cold wallet uses threshold signing: a private ECDSA or EdDSA key is shared among `t-of-n` HSMs (or co-located servers in different regions) using FROST, GG18, or CMP20 (cf. [Threshold Signatures](./threshold-signatures.md)). Signing requires a small MPC protocol — typically 2-3 rounds — to compute the nonce and signature share without ever reconstructing the private key. The blockchain sees a single normal signature; the threshold structure is invisible.

## Pitfalls in Production

A few non-obvious traps that bite real deployments:

1. **Triple-generation cost**: most SPDZ throughput collapses to *triple generation*, not the online protocol. Many "fast MPC" benchmarks assume an offline buffer full of triples; in steady state that buffer must be refilled continuously by an HE-based background worker.
2. **Reactive compositions**: signing `\Rightarrow` validation `\Rightarrow` signing is fine; *branching* on a secret-shared condition (a `mux`) requires an oblivious choice protocol that costs a multiplication and an extra round. Many "obvious" circuit translations blow up by 10× because of this.
3. **Dishonest-majority MAC check is amortised over the whole computation, not per-multiplication**: a single deviating multiplication is detected only when the final MAC check runs. A *fault-injection* adversary can do real damage (corrupt output, signed transaction) before the check fires. For high-stakes signing, protocols like SPDZ^k (Keller et al.) add a "early-abort" sub-protocol that catches deviations after every few multiplications.
4. **OT extension's wall-clock floor**: even with IKNY OT extension, the per-OT cost is dominated by hash invocations, and they are not free. For a 1-billion-AND-gate circuit (one AES evaluation is ~6000 AND gates), expect ~50 ms / AES at 3 GHz with 1 Gbps link — fast, but the *base-OT* phase that bootstraps OT extension needs ~128 public-key operations and cannot be parallelised past the round complexity of the base OT.

## Frequently Asked Questions

**Q1: Why is honest-majority MPC information-theoretically secure while dishonest-majority is not?**
A: In Shamir-style secret sharing with `t < n/2`, the shares are uniformly random conditioned on the secret, so even computationally unbounded adversaries learn nothing. With `t \ge n/2`, however, an adversary controlling half the parties can reconstruct intermediate values during multiplication (since the degree-2t polynomial `a(X) b(X)` is over-determined by `> 2t` evaluations). Dishonest-majority protocols must therefore use computational tools (OT, encryption, MACs) to mask intermediate values, which requires assumptions like DDH, LWE, or hash-collision resistance.

**Q2: What does "Beaver triple" mean, and why is it so central?**
A: Donald Beaver (1991) introduced the technique of pre-computing `(a, b, c=ab)` triples where `a, b` are random, unknown field elements shared among parties. To multiply `x, y`, parties open `\rho = x-a`, `\sigma = y-b` and locally compute `xy = c + \rho b + \sigma a + \rho\sigma`. The triple is consumed once; the round cost is one round-trip. Almost every modern arithmetic MPC protocol (SPDZ, Overdrive, MASCOT, ABY3) is structured as "compute Beaver triples somehow, then use them in the same way Beaver described."

**Q3: What's the role of oblivious transfer in MPC?**
A: OT is *complete* for MPC: any secure computation can be reduced to OTs alone (Kilian 1991). Concretely, every AND-gate in GMW needs 1-out-of-4 OT per pair of parties; every input-wire label of the evaluator in Yao needs a 1-out-of-2 OT. OT extension (Ishai-Kilian-Nissim-Petrovic 2003) makes OT cheap enough (a few hash calls per OT after a one-time 128 base-OT setup) that OT is no longer the bottleneck. See [Oblivious Transfer](./oblivious-transfer.md) for the construction.

**Q4: What's the state of the art on malicious security without honest majority?**
A: SPDZ remains the reference. The latest work (Keller-Rosulek-Scholl, *pseudo-random OT correlation / VOLE*, Eurocrypt 2022) reframes the triple-generation step as generating pseudorandom *vector-OLE correlations*; this gives roughly 5× throughput over classic SPDZ MASCOT. Other directions: silent-OT (Boyle et al., 2019) which compresses the offline phase with LPN-style codes, and the *evil-Morty* line of maliciously-secure Yao-garbling work that pushes cut-and-choose down to a constant factor overhead.

**Q5: How does MPC interact with hardware enclaves (SGX, TEE)?**
A: Enclaves promise to "compute on plaintext in a tamper-resistant box" — a strict improvement in throughput for a single trusted party. In practice, production systems use enclaves to *accelerate MPC*: e.g., one party holds shares in plaintext inside an enclave and computes a sub-circuit without communication. The combination (called *hTEE-MPC* or *Tandem*, see [Intel SGX](./intel-sgx.md)) gets close-to-native throughput for the inner computation at the cost of trusting the enclave's attestation, side-channel resistance, and rollback protection. The general pattern is: do as much as possible inside enclaves, use MPC to *cross-check* enclave outputs among mutually-suspicious enclave vendors.

**Q6: How big a circuit can MPC actually handle today?**
A: State-of-the-art 2-party systems (CrypTFlow2, CryptGPU, Piranha) handle billion-gate circuits in ~30 seconds on a single GPU. 3-party honest-majority (ABY3, Piranha) reaches ~10–100× that. PSI protocols handle set sizes of `2^28` in single-digit seconds on commodity hardware. Threshold signing (FROST, CMP) signs in 50–200 ms regardless of input size because the "circuit" is one ECDSA computation.

## Cross-References

- [Garbled Circuits](./garbled-circuits.md) — Yao's protocol in depth, including free-XOR and half-gate optimizations.
- [Oblivious Transfer](./oblivious-transfer.md) — the primitive underlying Yao and GMW; OT extension.
- [Threshold Signatures (FROST)](./threshold-signatures.md) — production MPC for signing.
- [Zero-Knowledge Proofs](./zk-proofs.md) — ZK is dual to MPC in important ways; ZK proofs are often built as MPC protocols with one of two parties collapsed.
- [Intel SGX](./intel-sgx.md) — hardware enclaves as an alternative and accelerator for MPC.

## Further Reading

- **A Pragmatic Introduction to Secure Multi-Party Computation** (Evans, Kolesnikov, Rosulek; now in *Foundations and Trends in Privacy and Security*) — the standard textbook-level survey, free online.
- **"Secure Multiparty Computation" lecture notes by Yehuda Lindell** (Bar-Ilan, ePrint 2020/1400) — short, rigorous, complete with proofs.
- **ABY framework (Demmler, Schneider, Zohner, 2015)** — the canonical mixed-protocol (arithmetic/boolean/Yao) MPC framework with full source code, the basis of most modern academic comparisons.
- **MP-SPDZ framework by Marcel Keller** — production-grade reference implementation of every major MPC protocol flavour, MIT licensed.
- **Manticore and MOTION frameworks** — open-source MPC libraries suitable for benchmarking new protocols.

## References

- Yao, A. C.-C. — *"Protocols for Secure Computations"* (1982), FOCS. The millionaires' problem and the first 2-party garbled-circuit protocol. https://www.cs.cmu.edu/~gongseg/yao-1982.pdf
- Goldreich, O., Micali, S., Wigderson, A. — *"How to Play ANY Mental Game"* (1987), STOC. The GMW multi-party protocol with OT-based multiplication. https://www.wisdom.weizmann.ac.il/~oded/gmw.html
- Ben-Or, M., Goldwasser, S., Wigderson, A. — *"Completeness Theorems for Non-Cryptographic Fault-Tolerant Distributed Computation"* (1988), STOC. The BGW protocol: information-theoretic MPC with honest majority. https://doi.org/10.1145/62212.62213
- Chaum, D., Crépeau, C., Damgård, I. — *"Multiparty Unconditionally Secure Protocols"* (1988), STOC. The CCD protocol, independently of BGW. https://doi.org/10.1145/62212.62214
- Beaver, D. — *"Efficient Multiparty Protocols Using Circuit Randomization"* (1991), CRYPTO. The Beaver triple technique. https://link.springer.com/chapter/10.1007/3-540-46775-5
- Damgård, I., Pastro, V., Smart, N., Zakarias, S. — *"Multiparty Computation from Somewhat Homomorphic Encryption"* (2012), CRYPTO. The SPDZ protocol. https://eprint.iacr.org/2011/565
- Keller, M., Rosulek, P., Scholl, M. — *"Pseudo-Random Correlations and VOLE: Applications to MPC and Beyond"* (2022), EUROCRYPT. The vOLE / silent-OT family. https://eprint.iacr.org/2022/1035
- Ishai, Y., Kilian, J., Nissim, K., Petrank, E. — *"Extending Oblivious Transfers Efficiently"* (2003), CRYPTO. OT extension, the workhorse that makes Yao and GMW practical. https://doi.org/10.1007/978-3-540-45146-4_2
- Mohassel, P., Rindal, P. — *"ABY3: A Mixed Protocol Framework for Machine Learning"* (2018), CCS. Three-party honest-majority MPC for ML. https://eprint.iacr.org/2018/403
- Boyle, E., Couteau, G., Gilboa, N., Ishai, Y., Kohl, L., Scholl, M. — *"Efficient Pseudorandom Correlation Generators: Silent OT Extension and More"* (2019), CRYPTO. Silent-OT / LPN-based triple generation. https://eprint.iacr.org/2019/1088
- Chandran, N., Gupta, D., Rindal, P., et al. — *"Fast Secure Computation of Set Intersection*" and follow-ups (2021), CCS. State-of-the-art PSI. https://eprint.iacr.org/2021/1243
- Lindell, Y. — *"Secure Multiparty Computation (MPC)*", Communications of the ACM 2020 — accessible survey of applications and theory. https://doi.org/10.1145/3378126
- Evans, D., Kolesnikov, V., Rosulek, M. — *"A Pragmatic Introduction to Secure Multi-Party Computation"*, Foundations and Trends in Privacy and Security vol. 3 (2018). https://eprint.iacr.org/2020/300
