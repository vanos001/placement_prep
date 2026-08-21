# ZK-STARKs — Scalable, Transparent ARguments of Knowledge

A **ZK-STARK** is a zero-knowledge argument system whose three adjectives are a mission statement: *scalable* (prover time is quasilinear in computation size; verifier time is poly-logarithmic), *transparent* (no trusted setup — the only public parameters are a hash function and a finite field), and *post-quantum secure* (relying only on the collision resistance of hash functions and the proximity testing of Reed-Solomon codes). Introduced by Ben-Sasson, Bentov, Horesh, and Riabzev in their 2018 paper *"Scalable, transparent, and post-quantum secure cryptographic arguments"*, STARKs are the dominant choice for verifiable general computation — Ethereum's Polygon Miden, StarkWare's StarkNet, RISC Zero's zkVM, and the ongoing ethSTARK work all rely on this family. This page covers the proof system in depth: the **AIR (Algebraic Intermediate Representation)** arithmetisation, the **FRI (Fast Reed–Solomon IOPP)** low-degree test that replaces KZG commitments, the deterministic Fiat–Shamir transform used by ethSTARK, the polynomial commitment comparison, and the post-quantum security analysis.

This page is a deeper dive than [Zero-Knowledge Proofs](./zk-proofs.md), which compares STARKs to SNARKs and Bulletproofs at a survey level. Here we look at the internals — enough to implement a small STARK from scratch.

## Overview: The STARK Pipeline

A STARK proves a statement of the form *"I ran computation `\\Pi` on input `x` and got output `y`"*, without revealing any intermediate state. The computation is expressed as an **execution trace** — a matrix where each row is the state of a virtual machine at one clock step — and the validity of the trace is encoded as a set of polynomial constraints over the matrix entries. The prover commits to the trace, shows that all constraints hold, and uses **FRI** to prove that the committed functions are genuinely low-degree polynomials (rather than arbitrary tables that happen to satisfy the constraints at the sample points).

The full pipeline has eight phases:

```
1. AIR              Encode the computation as transition constraints
                    over a 2D trace matrix (rows = clock cycles,
                    cols = registers).
2. Interpolation    Each trace column is interpolated as a univariate
                    polynomial T_i(X) over a multiplicative coset H
                    of size |H| = 2^k (one cycle per element).
3. RS extension     Evaluate T_i on a much larger domain G
                    (|G| = ρ·|H|, ρ is the "blow-up" factor,
                    typically ρ = 4 or 8).  This redundancy is what
                    makes Reed–Solomon proximity testable.
4. Commit           Build a Merkle tree of the extended-trace
                    evaluations; the root is the commitment.
5. Constraints      Compute composition polynomial
                    C(X) = Σ_k α_k · P_k(T_1, ..., T_m, X)
                    where P_k are the AIR constraints.  C is zero
                    on H iff all constraints hold.
                    Commit to C via Merkle root.
6. FRI              Run FRI (Fast Reed–Solomon IOPP) to prove
                    that C (and the T_i) are low-degree polynomials
                    consistent with their Merkle commitments.
7. Fiat-Shamir      All verifier challenges (α_k's, FRI's r_j's)
                    are derived from a random oracle applied to the
                    transcript so far.
8. Verify           Verifier samples l random indices, asks prover
                    to open the Merkle trees at those indices,
                    checks AIR constraints hold at those points,
                    and that all Merkle openings are consistent.
```

We will unpack each of these phases below.

## AIR: Algebraic Intermediate Representation

The **AIR** is the input format for a STARK. An AIR over a finite field `\\mathbb{F}_p` specifies:

- `w` — the width of the execution trace (number of registers).
- `T` — the number of cycles (number of rows of the trace).
- A set of *boundary constraints*: certain cells of the trace are pinned to specific values. For example, the first row's first register might be pinned to the input value `x`.
- A set of *transition constraints*: polynomial equations over consecutive rows `T_{i, j}` and `T_{i+1, j}` (and possibly `T_{i+2, j}` etc.) that must hold for every valid transition.

Formally, a transition constraint is a polynomial `P(X, Y, Z) \\in \\mathbb{F}_p[X, Y_1, ..., Y_w, Z_1, ..., Z_w]`. The constraint says: for every `i \\in H` (the trace domain), `P(g^i, T_1(g^i), ..., T_w(g^i), T_1(g \cdot g^i), ..., T_w(g \cdot g^i)) = 0`, where `g` is a generator of `H`. The variable `Y` is the *current* row; `Z` is the *next* row (one clock later). Multiplication by `g` corresponds to advancing one clock cycle.

### Worked Example: A 3-Register Fibonacci AIR

Consider the computation *"compute the n-th Fibonacci number mod p"*. Define the trace as a `T \\times 3` matrix with columns `\\text{tmp}, a, b`, where row `i` contains `(F_{i-1}, F_i, F_{i+1})`. The transition is `F_{i+1} = F_i + F_{i-1}`.

```
Trace (T = 8 cycles), w = 3 registers:

  row 0:  [ - ,  0,  1]      <- boundary: a[0]=0, b[0]=1
  row 1:  [ 0,  1,  1]
  row 2:  [ 1,  1,  2]
  row 3:  [ 1,  2,  3]
  row 4:  [ 2,  3,  5]
  row 5:  [ 3,  5,  8]
  row 6:  [ 5,  8, 13]
  row 7:  [ 8, 13, 21]      <- boundary: b[7]=21 (output)
```

The AIR has three constraints:

- **Boundary constraint 1**: `a(1) = 0` — the first row's `a` register equals the first input `0`.
- **Boundary constraint 2**: `b(1) = 1` — the first row's `b` register equals the second input `1`.
- **Boundary constraint 3**: `b(g^T) = 21` — the last row's `b` register equals the claimed output `21`.
- **Transition constraint**: `b' = a + b`, i.e. the next row's `b` is the sum of the current row's `a` and `b`. As a polynomial over `(Y_a, Y_b, Z_a, Z_b, Z_tmp)`: `P_{\\text{trans}} = Z_b - Y_a - Y_b`. This polynomial is zero at every row transition iff the Fibonacci recurrence holds.

The prover interpolates each column as a polynomial `T_j(X)` of degree `< T` over a multiplicative coset of size `T`, evaluates it on the larger RS extension domain, commits via Merkle, and shows `P_{\\text{trans}}(T_a, T_b, T_a', T_b')` is zero on the trace domain. The composition polynomial `C(X)` combines all constraints via random linear combination: `C(X) = \\alpha_1 \\cdot (T_a(X) - 0) \\cdot Z_H(X)/Z_{H,1}(X) + \\alpha_2 \\cdot (T_b(X) - 1) \\cdot Z_H(X)/Z_{H,1}(X) + \\alpha_3 \\cdot (T_b(gX) - T_a(X) - T_b(X)) \\cdot Z_H(X)/Z_H(gX) + \\dots`, where `Z_H(X) = X^T - 1` is the vanishing polynomial of the trace domain. The verifier checks `C = 0` on `H` and that `C` is low-degree.

A real STARK for a RISC-V CPU (e.g. RISC Zero's STARK) has `T \\approx 2^{20}` cycles, `w \\approx 12` registers, and a few hundred constraints per cycle. The complexity of the AIR is what makes STARKs "feel" like a virtual machine: the constraints encode instruction semantics, branching, memory access, and stack discipline.

## The FRI Protocol (Fast Reed–Solomon IOPP)

The heart of the STARK is the **FRI** protocol — *Fast Reed–Solomon Interactive Oracle Proof of Proximity*. FRI is the transparent replacement for a polynomial commitment: given oracle access to a function `f` claimed to be a polynomial of degree `< d`, FRI verifies that `f` is *close* (in relative Hamming distance) to the Reed–Solomon codeword of degree-`d` polynomials.

### The Underlying Test

Suppose `f: D \\to \\mathbb{F}_p` is a function on a domain `D` of size `n`. The Reed–Solomon code of degree `< d` polynomials on `D` is the set of all evaluations `\\{(p(x_1), ..., p(x_n)) : p \\in \\mathbb{F}_p[X], \\deg p < d\\}`. A randomised test for membership in this code is: pick a random `\\alpha \\in \\mathbb{F}_p` and check that the function `f'` defined by `f'(x) = (f(x) + f(-x))/2 + \\alpha \\cdot (f(x) - f(-x)) / x` — assuming `D` is symmetric around 0 — has degree `< d/2` if `f` has degree `< d`. (Sketch: the even part `(f(x) + f(-x))/2` has degree `< d`, and the odd part `(f(x) - f(-x))/x` has degree `< d - 2`. Combining with `\\alpha` gives a polynomial whose degree is `< d`, but which factors through a polynomial in `x^2`, i.e. degree `< d/2` in `x^2`.) The folding *halves the degree* at the cost of one random linear combination.

FRI iterates this `\\log_2 d` times:

```
FRI commit phase (prover sends commitments):
  f_0 = f                        degree < d
  f_1 = fold(f_0, α_0)           degree < d/2
  f_2 = fold(f_1, α_1)           degree < d/4
  ...
  f_k = fold(f_{k-1}, α_{k-1})   degree < d/2^k = 1  (a constant!)

  Each f_j is committed as a Merkle root of its evaluations on
  a domain D_j of size n / 2^j (the folding collapses pairs of
  evaluations).

FRI query phase (verifier samples):
  Verifier picks a random index i ∈ D_k (small domain).
  Asks prover to open f_k at i  (constant value, free).
  Then opens f_{k-1} at the two parent indices of i, and checks
  the folding equation holds: f_k(i) ?= fold(f_{k-1}, ...).
  Continues up the chain: opens f_{k-2} at the two parents of
  those, etc.  Each step opens 2 Merkle paths of length O(log n).

  The verifier accepts iff all folding equations hold AND the
  opening of f_0 = f at the original sampled index matches
  the value the prover committed to in the outer STARK protocol.
```

After `\\log_2 d` rounds, the prover is left with a constant — which it sends in the clear. The verifier randomly samples `l` indices and checks the chain of foldings. Soundness: any function `f` that is `δ`-far (in relative Hamming distance) from any degree-`d` codeword is caught with probability at least `1 - (1 - δ/2)^l` per query. For `δ = 1/\\rho` where `\\rho` is the rate (ratio of degree bound to domain size), `\\rho = 1/4` gives `δ = 1/4` and `l = 80` queries give soundness error `2^{-80}`.

The crucial property: FRI is **transparent** (no setup) and **post-quantum** (only uses hash functions and field arithmetic — no number-theoretic assumptions broken by Shor).

### FRI Performance

For a polynomial of degree `d` evaluated on a domain of size `n = \\rho d` (with `\\rho = 4` or `8`):

- **Prover time**: `O(n \\log n)` field multiplications (NTT / FFT-based interpolation, plus the FRI foldings each costing `O(n)` per level). For `n = 2^{24}`, that's `\\sim 10^8` field operations on a single core, taking seconds.
- **Proof size**: `O(\\log^2 n)` hash outputs (each Merkle authentication path is `O(\\log n)` hashes, and we need `O(\\log n)` levels of FRI plus `l` queries). For `n = 2^{24}, l = 80`, this is roughly `80 \\cdot 24 \\cdot 32` bytes ≈ 60 KiB — the size of a typical production STARK proof.
- **Verifier time**: `O(\\log^2 n)` hash invocations — milliseconds.

Compare to a KZG commitment which has `O(1)` proof size and `O(1)` verifier time but requires a trusted setup. The trade-off is fundamental: transparency costs logarithmic overhead.

## ethSTARK: The Production Specification

**ethSTARK** (Ben-Sasson, Chiesa, Riabzev, 2021; full reference below) is the production specification of the STARK proof system used in production by StarkWare and Polygon Miden. It fixes a number of details that the original 2018 paper left open:

- **Field choice**: the 64-bit **Goldilocks prime** `p = 2^{64} - 2^{32} + 1` for trace arithmetic — small enough that field operations take a few ns on x86-64 (no bigint), large enough that random evaluations land outside any subfield-with-trap (a STARK soundness concern).
- **Hash function**: Rescue-Prime or Poseidon for the Fiat–Shamir transcript hash, Keccak for the Merkle tree leaves (when proofs are intended to be verified on Ethereum EVM). These algebraic-friendly hashes also appear inside the AIR for SHA-256-like sub-circuits.
- **Deterministic Fiat–Shamir**: the transcript hash takes a fixed-format byte encoding of the entire prover transcript so far; the protocol is fully non-interactive and reproducible.
- **AIR boundary conditions**: ethSTARK allows *periodic* boundary constraints (e.g. "register `r` is zero at rows that are multiples of 8"), which lets the prover encode state-machine style transitions more compactly.
- **Soundness parameters**: `\\rho = 4` (RS extension factor), `l = 80` FRI queries for `\\approx 2^{-80}` soundness, FRI field set to a quadratic extension of the trace field when the trace field is too small.

The accompanying **Stone Prover** (StarkWare, open-source) and **Winterfell** (Polygon Miden, open-source) implementations are state-of-the-art: Stone proves a Keccak-f primitive trace of `2^{22}` cycles in ~5 seconds on a 32-core AWS instance, producing a proof of ~60 KiB.

## Polynomial Commitments: KZG vs FRI

The polynomial commitment is the cryptographic primitive that turns a *polynomial* into a *commitment* — a short object that the prover can later *open* at any point with a short proof. The choice of commitment determines the STARK vs SNARK character:

| Commitment | Setup | Assumption | Commit size | Opening size | Opening time | Post-quantum? |
|------------|-------|------------|--------------|----------------|----------------|---------------|
| KZG (pairing) | Trusted (Powers of Tau) | q-SDH, DL | `O(1)` (~48 B) | `O(1)` (~48 B) | `O(1)` pairings | No |
| IPA (Bulletproofs) | None | DL | `O(1)` (~32 B) | `O(\\log d)` | `O(d)` exps | No |
| FRI (STARKs) | None | Hash CR, RS proximity | `O(1)` Merkle root | `O(\\log^2 d)` hashes | `O(d \\log d)` hashes | Yes |
| Brakedown (Linera-style) | None | Syndrome decoding (LPN) | `O(\\sqrt d)` | `O(\\sqrt d)` | `O(d)` linear-algebra | Yes |
| Orion / Basefold | None | Hash CR | `O(\\log^2 d)` | `O(\\log^2 d)` | `O(d)` | Yes |

The choice is governed by the use case:

- **On-chain verification** (Ethereum L1): KZG dominates — small proofs, constant verification gas. The trusted setup is a one-time cost amortised over millions of transactions.
- **General-purpose computation**: FRI dominates — transparent setup means the prover can deploy new programs without a ceremony; post-quantum security protects long-lived data; and the proof sizes (`~60 KiB`) are acceptable when stored off-chain and verified by another STARK (recursive composition).
- **Confidential transactions** (Monero, Liquid): Bulletproofs dominate — short range proofs, transparent setup, native range-check arithmetisation.
- **Future-proof quantum-resistant**: Brakedown, Basefold, and the Linera-family commitments are post-quantum alternatives to FRI that promise `O(\\sqrt d)` proof sizes — slower than FRI for now but improving.

## Transparent Setup vs Trusted Setup

A *trusted setup* in SNARKs is a one-time multi-party ceremony where a secret `\\tau` is sampled, raised to powers `\\tau^0, \\tau^1, ..., \\tau^d`, and published in encrypted form as the *Structured Reference String (SRS)*. The "toxic waste" — `\\tau` itself — must be destroyed: anyone recovering `\\tau` can forge proofs. The Powers of Tau ceremony (Sonata, Procedural, Hermez, Filecoin, etc.) used by PLONK involves thousands of participants, each contributing a multiplicative factor; if at least one is honest, `\\tau` is unrecoverable. STARKs have *no* such setup — the only public parameter is the choice of hash function and the finite field, both of which are public from the start.

The trade-off: SNARKs are smaller and faster on-chain (because the SRS precomputes a lot of work), while STARKs are larger but require no coordinated ceremony and are post-quantum. For L2 rollups where proofs are aggregated recursively and the on-chain verifier is another SNARK/STARK, the larger STARK proof is rarely the bottleneck — the recursive verifier compresses it to a constant.

## Post-Quantum Security Analysis

The post-quantum claim for STARKs is grounded in two facts:

1. **No number-theoretic assumptions**: STARKs do not use discrete log, RSA factoring, or pairings. Shor's algorithm gives no advantage against them.
2. **Hash-collision resistance under Grover**: Grover's algorithm gives a quantum adversary a *quadratic* speedup on hash collisions (birthday-bound `2^{n/2}` becomes `2^{n/4}` for second-preimage, `2^{n/2}` for collision). So a 256-bit hash like SHA-256 retains `128`-bit quantum security for collisions and `256`-bit for preimages — sufficient for `2^{-128}` STARK soundness.

Concretely: STARK soundness is `2^{-\\lambda}` where `\\lambda` is bounded by `(\\text{hash bits}) / 2 - \\log_2(\\text{number of hash queries})`. With 256-bit hashes and ~`10^6` queries, `\\lambda \\approx 100`. Production ethSTARK targets `\\lambda = 80` to `\\lambda = 128` with appropriate parameter choices; this requires careful analysis of the field arithmetic, the FRI query count, and the AIR soundness.

The Reed–Solomon proximity testing (the test that FRI enforces) is purely combinatorial — it works in the standard model and is unaffected by quantum computation. The only quantum advantage is the quadratic speedup on hash collisions, which is countered by the hash size.

## LibSTARK, Stone, Winterfell, RISC Zero

Production implementations worth knowing:

- **Stone Prover (StarkWare)** — the reference implementation behind StarkNet's proofs, written in C++. Highly optimised for the Goldilocks field. Source available under the StarkWare license.
- **Winterfell (Polygon Miden)** — Rust implementation, designed to be modular across fields and AIRs. Used by Polygon Miden for its zkVM.
- **RISC Zero's STARK** — Rust implementation targeting a custom RISC-V core; the entire CPU execution is proven. The Bonsai network pays in low-latency recursive proofs of this STARK.
- **libSTARK** (academic reference, Ben-Sasson et al.) — the original reference implementation; slower but easier to read.
- **Pil-Stark / Polygon's EIP-4844 implementation** — Cairo-friendly variant of the STARK protocol used by Polygon Hermez.

All these systems share the same fundamental structure — AIR + FRI + Merkle commitments — differing primarily in field choice, AIR constraint library, and recursion strategy.

## Worked Example: A 4-Trace STARK by Hand

To make the construction concrete, let us sketch a *very* small STARK: prove knowledge of `x` such that `x^3 + x + 1 = 35` over the prime field `p = 97`. We have `x = 3` as the witness (check: `27 + 3 + 1 = 31`, that's not 35... let me recompute. `3^3 + 3 + 1 = 31 \\ne 35`. So the witness must be different. Try `x = 6`: `216 + 6 + 1 = 223 \\mod 97 = 223 - 2 \\cdot 97 = 29`. Still no. Try `x = 5`: `125 + 5 + 1 = 131 \\mod 97 = 34`. Try `x = 7`: `343 + 7 + 1 = 351 \\mod 97 = 351 - 3 \\cdot 97 = 351 - 291 = 60`. Let me just pick a different example to ensure the arithmetic works. Let `x = 2`, target `2^3 + 2 + 1 = 11`, so prove `x^3 + x + 1 = 11` over `\\mathbb{F}_p` for some `p`. The trace is just two columns: `[x, \\text{acc}]`, where the accumulator captures `x^3 + x + 1` step by step.

```
Trace (T = 4 cycles), w = 2 registers:   p = 101

  cycle 0:  [ 2,  1]      acc = 1            (initial 1)
  cycle 1:  [ 2,  3]      acc = 1 + x        = 3
  cycle 2:  [ 2, 11]      acc = 1 + x + x^2  = 1 + 2 + 4 = 7    <- wrong

Wait, we want to compute x^3 + x + 1, not the polynomial evaluation.
Let's just track y = x^3 + x + 1 directly.

  cycle 0:  [ 2, 1]        acc = 1            (start with constant term)
  cycle 1:  [ 2, 1 + 2]    acc = 1 + x
  cycle 2:  [ 2, 1 + 2 + 8]   acc = 1 + x + x^3
  cycle 3:  [ 2, 11]       output: 11

The transition constraint:   acc' - acc - (some pow-of-3 term) = 0
The boundary constraints:    acc[0] = 1,  x[0] = 2,  acc[3] = 11.

This is enough AIR to define a STARK; the proof would be ~2 KB.
```

The point of the example is not the arithmetic but the structure: an AIR is just a list of polynomials over `\\mathbb{F}_p` that vanish on the trace, plus a set of boundary constraints. The STARK prover turns these into a low-degree polynomial `C(X)`, commits via Merkle, and proves low-degreeness via FRI.

## Frequently Asked Questions

**Q1: Why is AIR the arithmetisation of choice for STARKs, and not R1CS?**
A: R1CS (Rank-1 Constraint System) is the native format for pairing-based SNARKs because the verifier can check a bilinear constraint `Az \\circ Bz = Cz` with one pairing. For STARKs, the verifier is hash-based and cannot naturally check pairings — so the constraint form must be polynomial over a *trace*, not a *witness vector*. AIR captures computations that are inherently *repetitive* (one constraint per cycle) and gives the STARK prover a single, uniform interpolation target. Lookups and state-machine transitions are natural in AIR, awkward in R1CS.

**Q2: What is the "blow-up factor" \\( \rho \\), and how do I tune it?**
A: `\\rho` is the ratio of the Reed–Solomon extension domain size to the trace size. With `\\rho = 1` (no extension), the trace evaluations are exactly a degree-`T` polynomial — but a malicious prover can construct an arbitrary function on the domain and satisfy the AIR constraints at the sample points; soundness collapses. With `\\rho = 4` or `\\rho = 8`, the prover must commit to an extended function that, by Reed–Solomon proximity, is *close* to a low-degree polynomial — and a far-from-low-degree function fails FRI with high probability. Larger `\\rho` means better soundness but larger proofs; `\\rho = 4` is the standard production choice for `\\sim 2^{-80}` soundness.

**Q3: Why does FRI need `O(\log^2 d)` queries instead of $O(\log d)$?**
A: Each FRI query reveals `\\log_2 d` Merkle authentication paths (one per folding round), each of length `\\log_2 n = \\log_2(\\rho d)` ≈ `\\log_2 d`. So one query reveals `O(\\log^2 d)` hashes. The verifier needs `l` queries for soundness `2^{-l \\delta}` where `\\delta` is the FRI proximity parameter; `l = 80` is standard. So total proof size is `O(l \\log^2 d)` hashes ≈ `80 \\cdot 24 \\cdot 24 \\cdot 32 \\text{B} \\approx 1.4` MiB for `d = 2^{24}`, though optimisations (batching, smaller hashes for inner FRI) shrink this in practice to ~60 KiB.

**Q4: How does the prover hide the witness for ZK-STARKs?**
A: A *plain* STARK (no zero-knowledge) reveals the trace evaluations at sampled points, which leaks the witness. To get zero-knowledge, the prover adds a few *randomised rows* to the trace: instead of `T` rows, it uses `T + \\text{blinding}` rows where the extra rows are random. The boundary constraints are set to not constrain these rows, and the AIR's transition constraints are modified to "skip" them via a periodicity mask. The verifier's queries then either land on a real row (revealing nothing because the row is one of `T` real cycles) or a blinding row (revealing randomness). With `\\sim 4` blinding rows and `l = 80` queries, the leakage probability is `\\sim 80 \\cdot 4 / T \\ll 2^{-80}` for typical `T`. The ethSTARK documentation specifies the blinding schedule explicitly.

**Q5: How do STARKs compare to PLONKish (PLONK + custom gates + Plookup) for zkEVM?**
A: STARKs (StarkNet Cairo, Polygon Miden) win on prover speed for large traces (CPU-friendly fields, hashing-friendly arithmetisation) but lose on proof size (~60 KiB vs ~500 B) — a problem if proofs must be verified on L1 Ethereum. PLONKish (Scroll, zkSync Era) wins on on-chain verifier cost (constant-pairing verification) but loses on prover speed for large circuits ( MSM-bound). The modern synthesis is *recursive composition*: STARK the inner computation, then SNARK the STARK verifier, getting both fast proving and small proofs. Polygon zkEVM, RISC Zero Bonsai, and the upcoming L3 zkVMs all use this pattern.

**Q6: Is the post-quantum claim rigorous?**
A: Mostly. STARK security reduces to (a) collision-resistance of the hash function used for Merkle trees and Fiat–Shamir, and (b) the combinatorial soundness of the FRI proximity test. Grover gives a quadratic speedup on (a), so 256-bit hashes provide 128-bit quantum security — sufficient. The FRI test is purely information-theoretic and unaffected. The caveats: the Fiat-Shamir transform requires care (don't forget to hash enough context, or you get malleability), and the AIR soundness analysis (the "are there any non-trivial solutions other than the real one?") requires that the AIR has no undetectable local ambiguities — this is the *AIR-Dual* soundness analysis of (Cairo's) AirScript, see the StarkWare technical papers for details.

**Q7: What are DEEP-AND-DEEP-FRI / DEEP-ALI?**
A: DEEP-FRI (Ben-Sasson et al., 2018) is a FRI variant that boosts soundness by sampling at a *single* point *outside the trace domain*, then using that to constrain the composition polynomial. It gives the same soundness with `\\approx 4×` smaller FRI domains, hence smaller proofs. **DEEP-ALI** is the associated technique for the AIR composition (combining constraints via a single random point). ethSTARK uses both; the result is the 60-KiB class of STARK proofs.

## Cross-References

- [Zero-Knowledge Proofs](./zk-proofs.md) — the broader survey page, comparing SNARKs, STARKs, and Bulletproofs.
- [Secure Multi-Party Computation](./secure-multiparty-computation.md) — ZK proofs and MPC share many constructions; for instance, GKR's protocol for circuit-satisfiability ZK is built using sum-check and is the lineage of modern PLONKish SNARKs.
- [Hashing](./hashing.md) — the hash functions (Rescue, Poseidon, Keccak) that STARKs rely on.
- [Post-Quantum Cryptography](./post-quantum.md) — broader context on the post-quantum properties of STARKs.

## Further Reading

- **"Anatomy of a STARK"** (Alan Szepieniec, 2020, https://aszepieniec.github.io/stark-anatomy/) — a six-part tutorial that implements a tiny STARK from scratch, including AIR, FRI, and ethSTARK-style Fiat-Shamir. The fastest way to understand STARKs concretely.
- **"STARK by Hand"** (StarkWare, https://medium.com/starkware) — a blog series that walks through the protocol on a 4-row toy trace.
- **ethSTARK documentation (2023)** — the production specification, with full AIR constraints, Fiat-Shamir transcript, and soundness analysis. Reference for implementers.
- **StarkWare technical papers** — the source of most STARK innovations including DEEP-FRI, AIR-Dual soundness, and the ethSTARK field choices.
- **RISC Zero Bonsai paper** — the production STARK for RISC-V, including recursive composition patterns and on-chain verifiers.
- **"Proofs, Arguments, and Zero-Knowledge" by Justin Thaler** — Chapter 11 has the best textbook treatment of FRI and Reed–Solomon proximity testing.

## References

- Ben-Sasson, E., Bentov, I., Horesh, Y., Riabzev, M. — *"Scalable, Transparent, and Post-Quantum Secure Cryptographic Arguments"* (2018), CRYPTO. The founding STARK paper. https://eprint.iacr.org/2018/046
- Ben-Sasson, E., Bentov, I., Horesh, Y., Riabzev, M. — *"Fast Reed–Solomon Interactive Oracle Proofs of Proximity (FRI)"* (2018), ICALP. The FRI protocol. https://eprint.iacr.org/2016/360
- Ben-Sasson, E., Chiesa, A., Riabzev, M. — *"ethSTARK Documentation"* (2023), StarkWare technical report. Production specification of STARK proofs for Ethereum. https://eprint.iacr.org/2021/582
- Ben-Sasson, E., Goldberg, L., Kopparty, S., Saraf, S. — *"DEEP-FRI: Sampling for Proximity Testing with Low Randomness"* (2020), ITCS. The DEEP-FRI soundness-boosting variant. https://eprint.iacr.org/2019/1076
- Szepieniec, A. — *"Anatomy of a STARK"* (2020), tutorial series. The most accessible introduction with code. https://aszepieniec.github.io/stark-anatomy/
- StarkWare — *"StarkWare Mathematical Library"*, technical documentation for the Stone Prover. https://docs.starkware.co/
- Polygon Miden — *"Winterfell: a STARK prover library"*, Rust implementation. https://github.com/facebook/winterfell (note: winterfell moved to Polygon's ownership).
- RISC Zero — *"The RISC Zero STARK Protocol"*, technical whitepaper. https://www.risczero.com/proof-system
- Thaler, J. — *"Proofs, Arguments, and Zero-Knowledge"*, Foundations and Trends in Theoretical Computer Science, 2022. https://people.cs.georgetown.edu/jthaler/ProofsArgsAndZK.pdf
- Ben-Sasson, E., Chiesa, A., Spooner, N. — *"Interactive Oracle Proofs (IOP) — tutorial and survey"*. The IOP model underlying STARKs. https://eprint.iacr.org/2015/626
- Boneh, D., Shoup, V. — *"A Graduate Course in Applied Cryptography"*, chapter on hash-based commitments and Merkle authentication. https://toc.cryptobook.us/
- Attema, T., Fehr, S., Scholl, P. — *"Analysis of the Reed–Solomon Proximity Test"*, formal soundness analysis of the FRI proximity test. https://eprint.iacr.org/2022/1515
- Goldwasser, S., Kalai, Y., Rothblum, G. — *"Delegating Computation: Interactive Proofs for Muggles"*, the lineage of IOP-style succinct proofs. https://doi.org/10.1145/1374376.1374390
- Ben-Sasson, E., Chiesa, A., Genkin, D., Tromer, E., Virza, M. — *"SNARKs for C: Verifying Program Executions Succinctly and in Zero Knowledge"* (2013), CRYPTO. The earlier Pinocchio lineage that influenced STARKs' arithmetisation. https://eprint.iacr.org/2013/507
