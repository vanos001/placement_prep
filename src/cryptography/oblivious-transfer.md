# Oblivious Transfer (OT)

Oblivious transfer (OT) is a two-party primitive that, despite its almost paradoxical narrowness, is *complete* for secure computation: every multi-party computation can be reduced to OTs alone (Kilian, 1991). In its standard 1-out-of-2 form (EGL, 1985), a sender holds `(m_0, m_1)` and a receiver holds a choice bit `b \\in \\{0, 1\\}`; after the protocol the receiver learns `m_b` (and nothing about `m_{1-b}`), while the sender learns nothing about `b`. This page covers Rabin's original OT, the 1-out-of-2 / 1-out-of-n variants, the Naor-Pinkas DDH-based construction, the **OT extension** of Ishai-Kilian-Nissim-Petrovic (IKNY, 2003) that reduces an arbitrary number of OTs to a constant number of base-OTs plus symmetric crypto, the **random OT correlation** that powers modern MPC, and the recent **VOLE / silent-OT** family. The aim is to give a working cryptographer enough to implement, benchmark, and choose between OT schemes in production.

## The Setting and the Threat Model

Two parties: a sender `S` and a receiver `R`. They communicate over an authenticated channel; the adversary may corrupt either party. The security properties are:

- **Sender security (privacy)**: `R`'s view is simulatable from `m_b` alone (so `R` learns nothing about `m_{1-b}`).
- **Receiver choice-privacy**: `S`'s view is independent of `b` (so `S` cannot tell which `R` chose).

OT comes in two main flavours:

- **Rabin's original OT** (1981): receiver gets `m` with probability `1/2`; sender does not know whether the receiver got it.
- **EGL 1-out-of-2 OT (the de-facto standard)**: receiver chooses exactly one of two messages.
- **1-out-of-n OT** and **k-out-of-n OT**: natural generalisations; 1-out-of-n OT is reducible to 1-out-of-2 OT with `\\log n` overhead per OT.

There is also the **random OT (ROT)** variant in which `(m_0, m_1)` are uniformly random, `b` is uniformly random, and the parties want ROT instances for use as MPC pre-processing. Almost all modern MPC systems bootstrap from ROT: the ROT instances are precomputed in bulk and consumed later as Beaver triples or garbled-circuit input labels.

## Rabin's Original OT (1981)

In Rabin's original construction (the *Rabin-OT*), the receiver gets `m` with probability `1/2`. The construction is built on the difficulty of factoring. The sender generates an RSA modulus `n = pq` and picks `m \\in \\mathbb{Z}_n`. R picks a random `x \\in \\mathbb{Z}_n^*` and sends `a = x^2 \\mod n` to `S`. With probability `1/2` (namely, when `x` is a non-square, which `S` cannot detect), `R` can compute a square root `y` of `a` different from `x` by combining what `S` provides with `x`. If `R` succeeds, then `y \\neq x` and `gcd(x - y, n)` yields a non-trivial factor of `n`, which `R` can use to decrypt `m`. If `R` cannot, `R` learns nothing about `m`. The sender never learns which happened.

This is awkward to use because of the probabilistic delivery; the EGL form below is what one wants in practice.

## EGL 1-out-of-2 OT

Even, Goldreich, and Lempel (1985) gave the cleaner "1-out-of-2 OT" (also called "2-1 OT" or just "OT") that has become the standard form. We state it here in the common OT protocol syntax:

```
Functionality F_OT:
  Input  : S holds (m_0, m_1); R holds b ∈ {0,1}.
  Output : R learns m_b; S learns nothing about b.
            R learns nothing about m_{1-b}.
```

The Naor-Pinkas (2001) DDH-based protocol is the standard instantiation:

### Naor-Pinkas OT (2001)

Let `\\mathbb{G}` be a cyclic group of prime order `q` where the Decisional Diffie-Hellman (DDH) problem is hard. The sender picks a random `C \\in \\mathbb{G}` (the *common reference* element); R picks a random `k \\in \\mathbb{Z}_q` and computes `PK = g^k`, plus either `PK_0 = PK` (if `b = 0`) or `PK_0 = g^r / PK` for random `r` (if `b = 1`). R sends `PK_0` to S; S can compute `PK_1 = C / PK_0` (so that `PK_0 \\cdot PK_1 = C`).

For each bit value `i \\in \\{0,1\\}`, S picks a fresh random `r_i`, computes `g^{r_i}`, and uses `PK_i^{r_i}` as the encryption key for `m_i`. Concretely:

```
Naor-Pinkas OT (semi-honest; full version adds ZK proofs):

  S holds (m_0, m_1);  R holds choice b.
  ----------
  Setup : C ← random generator element; sent to S.
  Round 1 (R -> S):
    k ←$ Z_q ;  pick r uniformly
    if b == 0:  PK_0 = g^k         (k is "the" DH secret for index 0)
    else:       PK_0 = C * g^(-k)  (k2 is "the" DH secret for index 1; PK_1 = g^k)
    send PK_0
  S derives PK_1 = C * PK_0^{-1}.
  Round 2 (S -> R):
    for i in {0, 1}:
      r_i ←$ Z_q
      C_i = g^{r_i}
      enc_i = m_i  XOR  H( (PK_i)^{r_i} )     # H is a hash, modelled as RO
    send (C_0, enc_0, C_1, enc_1)
  R computes  dec_b = enc_b  XOR  H( (C_b)^{k} )   # since (C_b)^k = g^{r_b k} = (PK_b)^{r_b}
                  = m_b.
  R cannot compute H((C_{1-b})^{r_{1-b}}) because that would
  require knowing k2 such that PK_{1-b} = g^{k2}, which by
  DDH it does not.
```

Sender privacy (privacy of `m_{1-b}`) follows from DDH: from R's view, `PK_{1-b}` is a group element whose discrete log R does not know, so the Diffie-Hellman triple `(g, PK_{1-b}, C_{1-b})` looks uniformly random. Receiver choice-privacy (`S` cannot tell `b`) follows because both `PK_0 = g^k` (when `b = 0`) and `PK_0 = C / g^k` (when `b = 1`) are uniformly random elements — the distributions are identical.

The cost: one round of communication, `O(1)` group exponentiations on each side. For Curve25519 (~0.1 ms per scalar mult in software, ~50 μs with AVX-512) this is roughly `50 + 50 = 100 \\mu s` per OT — fast for a handful of OTs, but if your MPC needs `2^{20}` OTs, you would pay ~100 seconds. This is where OT extension comes in.

## 1-out-of-n OT

The 1-out-of-n OT functionality generalises: sender holds `(m_0, ..., m_{n-1})`, receiver picks `i \\in [n]`, learns `m_i`. The most efficient constructions for `n = 2^\\ell` use `\\ell` 1-out-of-2 OTs in parallel: encode `i` as `\\ell` bits, and for each bit position use 1-out-of-2 OT to obliviously select between pairs of intermediate values that are constructed by the sender from the original messages. The Naor-Pinkas extension (2001) achieves `O(\\ell)` sender work for `n = 2^\\ell`. Concrete improvements (Tavarayi, Trifonov, etc.) shave constants further.

For very large `n` and few OTs, the *private-information-retrieval* family (Chor, Goldreich, Kushilevitz, Sudan, 1995) gives poly-logarithmic-cost OT, at the cost of multi-server assumptions or stronger computational hypotheses.

## OT Extension (IKNY, 2003)

The killer-optimisation in modern OT is **OT extension** (Ishai, Kilian, Nissim, Petrank, 2003), universally called "IKNY". It reduces the public-key cost of `N` OTs to just `\\kappa = 128` public-key base-OTs plus `O(N)` symmetric hash operations. The result: OT is essentially free in bulk.

### The Idea

In the base-OT phase, the parties run `\\kappa` instances of Naor-Pinkas OT. The receiver uses a *random* choice bit `b_j` for each OT, and the sender uses *random* pairs `(x_j^0, x_j^1)` as messages. So the parties end up sharing a `\\kappa \\times \\kappa` bit-matrix `T` (the "Naor-Pinkas seed" in the IKNY notation) where `T[j][i] = x_j^{b_j} \\cdot (-1)^{b_j} \\cdot y_j` (something like that, depending on which formulation; the key point is that the columns of `T` are "rows of OTs" shared between sender and receiver). Then they "stretch" these base-OT correlations to produce as many extended OTs as desired.

### The IKNY Construction (Sketch)

Let `q_0, q_1 \\in \\{0,1\\}^{\\kappa}` be the two messages for an extended OT instance; `c \\in \\{0,1\\}` be the receiver's choice bit. The sender picks a random `\\Delta \\in \\{0,1\\}^{\\kappa}` and uses it as a *global MAC key* (kept secret from the receiver). The construction:

```
IKNY OT extension (one extended OT among N):

  Base-OT setup (one-time):
    - Run κ Naor-Pinkas OTs in the opposite direction (R is sender).
    - Receiver R learns κ random choice bits b = (b_1,...,b_κ) and the
      corresponding messages x_j^(b_j) for each j.  Sender S learns
      (x_j^0, x_j^1) for each j.  (Note R does NOT know x_j^(1-b_j).)

  Per extended OT (one of N):
    - R picks random y ∈ {0,1}^κ.
      For c = 0:  set t_j = y_j ⊕ (b_j * (y_j))              i.e. t = y (unchanged)
      For c = 1:  set t_j = ¬y_j ⊕ (b_j * (y_j ⊕ ¬y_j))     i.e. t = y ⊕ b
      Send t to S.
    - S computes  for each j:
        q_j^0 = H(j, t_j  ⊕ (Δ_j * (j-th bit of stuff)))
        q_j^1 = H(j, t_j ⊕ Δ_j ⊕ ...)
      (The construction ensures the receiver can compute H(j, y)
       from the appropriate x_j^(b_j) it learned in base-OT.)
    - S's two messages for this OT are:
        m_0 = q^0 XOR (correlation mask from base-OT j^0 side)
        m_1 = q^1 XOR (correlation mask from base-OT j^1 side)
    - R recovers m_c = q^c XOR (correlation mask it can compute).
```

The formal treatment is more careful than the sketch; the punchline is:

- **Cost of N extended OTs**: `O(\\kappa)` base-OTs (one-time) + `O(N \\kappa)` symmetric operations (essentially `N` AES / hash invocations per OT, with `\\kappa = 128` amortising to ~4 hash calls per OT after IKNY optimisations and the KKNMS / KKOT follow-ups).
- **Communication**: `O(N \\kappa)` bits = 16 bytes per OT — i.e. 1 MB for `2^{20}` OTs.

Modern OT extension libraries (`emp-ot`, `libOTe`, `aby OT module`) achieve `10^7$ OTs / sec / core` on commodity hardware. For the practitioners reading this: the bottleneck of modern Yao-based 2-PC and GMW is rarely OT itself; it's the symmetric-cost *garbling* and the *network latency*.

## Random OT and the OT Correlation

The **random OT (ROT)** correlation is the building block that makes MPC protocols like GMW and SPDZ pre-processing clean. In ROT, both `m_0, m_1` and `b` are uniformly random (not chosen by the parties). After ROT, the receiver knows `b` and `m_b` (but not `m_{1-b}`), and the sender knows both `m_0, m_1` (but not `b`).

```
F_ROT:
  Sample (m_0, m_1, b) ← uniform.
  S learns (m_0, m_1);  R learns (b, m_b).
```

ROT is what comes out of OT extension essentially "for free" (no per-OT cost beyond the symmetric step). Concrete MPC protocols consume ROTs in bulk:

- **GMW**: each AND gate between two parties needs one 1-out-of-4 OT. This can be built from 2 ROTs (Nielsen et al., 2015). So one ROT per AND gate per pair of parties.
- **Beaver triple generation in SPDZ^Mascot** (Keller et al., 2018): one Beaver triple = 1 ROT (the trick is the "triple-merging" of Couteau et al., 2021). So `N` triples = `N` ROTs + small verification overhead.
- **Garbled circuits**: each evaluator-input bit needs a 1-out-of-2 OT in *chosen*-message form, but chosen-message OT reduces to ROT with one extra round (Asharov-Lindell-Schneider-Zohner "GOTP" technique, 2013).

A key innovation in the past 5 years is **silent OT** (Boyle et al., CRYPTO 2019). The observation: ROT instances are *correlated* (the sender's two messages are random but related through some structure), and one can use LPN-style coding to expand a few "real" base-OTs into millions of pseudorandom ones with very little communication. The result: silent-OT generation cost scales *sub-linearly* in `N` (specifically `O(\\sqrt{N})` communication and `O(N)` computation), with `N = 10^9` ROTs in seconds on a single workstation.

## VOLE: Vector Oblivious Line-Vector Evaluation

A generalisation of ROT called **VOLE** (Vector Oblivious Linear Evaluation, Doerner-Shelat 2017, Schoppmann et al. 2019) is the hottest modern direction:

```
F_VOLE:
  S holds (x, M_1)  where x ∈ F_p and M_1 ∈ F_p^ℓ.
  R holds (a, b)    where a, b ∈ F_p^ℓ, with b = a*x + M_0 - M_1   for some M_0.
  Both parties "know" the relation  b = a*x + (delta for some delta S holds).
```

VOLE is ROT generalised to vector spaces; one VOLE of length `\\ell` gives `\\ell` correlated OTs. The construction of VOLE from LPN codes (Boyle et al.) gives `N` VOLEs in `O(N)` computation but `O(\\sqrt{N})` communication. This is the underlying machinery of the *Keller-Rosulek-Scholl VOLE* work (Eurocrypt 2022) and the *wormhole-VOLE* optimisation.

The practical consequence: SPDZ *triple generation* — historically the dominant cost of dishonest-majority MPC — has been reduced by 5-10× compared to naive MASCOT (Keller et al., 2018) just by switching to silent-OT / VOLE-based triple generation. Production systems like the *MOTION* framework and the *ABY3 / MP-SPDZ* libraries now ship VOLE-based backends.

## 1-out-of-n OT and k-out-of-n OT

For the 1-out-of-2 OT, the cost is `O(1)` exponentiations. For the 1-out-of-n OT, the cost is `O(\\log n)` 1-out-of-2 OTs using the Naor-Pinkas 1-out-of-n construction (2001), or `O(n)` 1-out-of-2 OTs using the trivial parallelisation. The 1-out-of-n OT is most-used in private-information-retrieval (PIR), where a client wants to retrieve item `i` from a database of `n` items without revealing `i` to the server.

The 2-out-of-3 OT (and other k-out-of-n) is useful in some MPC protocols where multiple labels per wire are needed; constructions follow from 1-out-of-n with care.

## Frequently Asked Questions

**Q1: What is the difference between OT and oblivious PRF (OPRF)?**
A: An OPRF is a *symmetric* primitive: the client provides an input `x`, the server evaluates `F_k(x)` for a secret key `k`, and the client receives `F_k(x)` while learning nothing about `k`. OT is *asymmetric*: the server holds two messages and the client picks one. OPRFs are typically built on top of OT (or on top of Diffie-Hellman-based OPRF) and used in PSI, OPaque PAKE, and similar applications.

**Q2: Why is OT "complete" for MPC?**
A: Kilian's 1991 theorem shows that any secure computation can be polynomially reduced to OT — both in the semi-honest and malicious settings. The construction uses OT-based secret-sharing (Beaver's *multiparty computation from OT*): each AND gate in a Boolean circuit is reduced to a 1-out-of-4 OT, and from there to two 1-out-of-2 OTs. The theorem shows OT *exists* and OT *is universal*; the practical instantiations follow this circuit-by-circuit reduction.

**Q3: How does the active-secure OT work?**
A: The Naor-Pinkas protocol above is secure against *semi-honest* adversaries. Upgrading to malicious security requires: (a) the receiver must *prove* it constructed `PK_0, PK_1` correctly (i.e. that one of them is the genuine DH public-key); (b) the sender must *prove* the ciphertexts are well-formed (the `C_i` are random group elements, the `enc_i` follow the protocol). The first is typically done with a Schnorr-style proof of knowledge of `k`; the second with a Chaum-Pedersen-like proof that `(g, PK_i, C_i, PK_i^{r_i})` is a valid Diffie-Hellman tuple. The overhead is roughly 2× the semi-honest cost.

**Q4: What is the OT cost in modern Yao?**
A: For `\\ell = 2^{20}` evaluator input bits, the OT-extension cost is ~5 ms in software (one-time base-OT of 128 Naor-Pinkas OTs, ~10 ms; bulk extension, ~1 ms / 10^6 OTs). For comparison, garbling a 1-million-AND-gate circuit takes ~50 ms. So in Yao, OT is rarely the bottleneck. In GMW, OT can be the bottleneck because the per-AND-gate cost is one OT — but with OT extension it's still cheap: `10^6$ ANDs `\\to` `10^6$ OTs `\\to` `1` second.

**Q5: Are OTs post-quantum?**
A: The DDH-based Naor-Pinkas OT is *not* post-quantum — Shor's algorithm breaks DDH on a sufficient quantum computer. To get post-quantum OT, one uses LWE-based constructions (Peikert-Rosenfeld 2006, «-then-something like the BDGMV PRF-based OT). LWE-based OT extension is also possible: the *QB-OT* work of Doerner-Shelat (2017) gives a post-quantum OT extension with the same asymptotic cost as IKNY. The post-quantum-MPC community has converged on LWE-based VOLE as the standard primitive; see the *Quarks/Onyx/Spook* line of work.

**Q6: What's the practical throughput of OT extension in 2024?**
A: On a 2024-class Xeon with AES-NI and AVX-512: ~`3 \\times 10^7` OTs / sec / core for 1-out-of-2 OT in `libOTe`. VOLE-based silent-OT pre-processing gets `10^9` ROTs in a few seconds. The network bandwidth is the bottleneck at scale: 16 bytes / OT × `10^9` = 16 GB, which is multiple seconds on a 10 Gbps link. Modern systems get around this with silent-OT: the *silent* part means the communication is `O(\\sqrt N)` instead of `O(N)`.

## Cross-References

- [Secure Multi-Party Computation](./secure-multiparty-computation.md) — MPC uses OT for Beaver triple generation and for input-wire labels in Yao.
- [Garbled Circuits](./garbled-circuits.md) — Yao protocols use OT to deliver evaluator-input labels without leaking the evaluator's input.
- [Zero-Knowledge Proofs](./zk-proofs.md) — ZK proofs reduce to OT in many constructions (Σ-protocols and the Blum Hamiltonian-cycle protocol use OT).

## Further Reading

- **"Secure Multi-Party Computation" lecture notes by Yehuda Lindell** (ePrint 2020/1400), chapter on OT.
- **`libOTe` library (R. E. Hu, A. J. Maatouk et al.)** — the de facto C++ reference for high-performance OT, including semi-honest / active OT, IKNY extension, silent OT, and VOLE.
- **`emp-ot` (Samee Zahur, Xiao Wang, et al.)** — high-performance OT extension as used in `emp-toolkit`.
- **MOTION framework** — open-source MPC framework with multiple protocols (Yao, GMW, BGW) and OT backends.

## References

- Rabin, M. O. — *"How to Exchange Secrets by Oblivious Transfer"* (1981), Harvard Tech Report TR-81. The original probabilistic OT. https://eprint.iacr.org/2005/106
- Even, S., Goldreich, O., Lempel, A. — *"A Randomized Protocol for Signing Contracts"* (1985), Communications of the ACM. The 1-out-of-2 OT definition. https://doi.org/10.1145/3979.3982
- Naor, M., Pinkas, B. — *"Efficient Oblivious Transfer Protocols"* (2001), SODA. The DDH-based OT construction. https://dl.acm.org/doi/10.5555/365411.365452
- Ishai, Y., Kilian, J., Nissim, K., Petrank, E. — *"Extending Oblivious Transfers Efficiently"* (2003), CRYPTO. The OT extension (IKNY). https://doi.org/10.1007/978-3-540-45146-4_2
- Beaver, D. — *"Correlated Pseudorandomness and the Complexity of Private Computation"* (1996), STOC. Foundation for OT-based MPC and pre-processing. https://doi.org/10.1145/237814.237851
- Kilian, J. — *"Founding Cryptography on Oblivious Transfer"* (1988), STOC. Shows OT is complete for MPC. https://doi.org/10.1145/62212.62231
- Nielsen, J. B., Nordholt, P. S., Orlandi, C., Burra, S. S. — *"A New Approach to Practical Active-Secure Two-Party Computation"* (2012), CRYPTO. Active-secure OT extension. https://eprint.iacr.org/2011/691
- Keller, M., Orsini, E., Scholl, P. — *"MASCOT: Faster Maliciously Secure Two-Party Computation"* (2016), CCS. SPDZ pre-processing via OT extension. https://eprint.iacr.org/2016/450
- Boyle, E., Couteau, G., Gilboa, N., Ishai, Y., Kohl, L., Scholl, M. — *"Efficient Pseudorandom Correlation Generators: Silent OT Extension and More"* (2019), CRYPTO. Silent OT. https://eprint.iacr.org/2019/1088
- Schoppmann, P., Raykova, M., et al. — *"Multi-Party Generation of the BLS Signature"* (2019). VOLE for SPDZ pre-processing. https://eprint.iacr.org/2019/1144
- Keller, M., Rosulek, P., Scholl, M. — *"Pseudo-Random Correlations and VOLE"* (2022), EUROCRYPT. The VOLE / silent-OT family formalised. https://eprint.iacr.org/2022/1035
- Doerner, J. P., Shelat, A. — *"Dueling Secures MPC: Efficient Computation with High Integrity"* (2017), IEEE S&P. Pseudorandom correlation-based construction. https://eprint.iacr.org/2017/1070
- Peikert, C., Rosenfeld, B., Vaikuntanathan, V. — *"OT from LWE Revisited"*. LWE-based post-quantum OT. https://eprint.iacr.org/2017/212
- Chor, B., Goldreich, O., Kushilevitz, E., Sudan, M. — *"Private Information Retrieval"* (1995), FOCS. PIR from OT. https://doi.org/10.1109/SFCS.1995.492461
- Asharov, G., Lindell, Y., Schneider, T., Zohner, M. — *"More Efficient Garbled Circuit Construction"* (2014). Chosen-message OT from ROT. https://eprint.iacr.org/2014/080
