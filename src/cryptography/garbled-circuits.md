# Garbled Circuits — Yao's Protocol

Yao's garbled circuit protocol, introduced in 1986 and refined in countless follow-ups, is the foundational two-party secure-computation primitive. Given a Boolean circuit `C` for a function `f`, one party (the *garbler*) *encrypts* `C` gate-by-gate into an opaque *garbled circuit* `G(C)` that can be evaluated only by someone holding the appropriate input *wire labels*. The other party (the *evaluator*) obtains its own input labels via oblivious transfer (so the garbler cannot know which input it evaluated) and the garbler's labels directly (since the garbler knows its own input). The evaluator decrypts through the circuit layer-by-layer, ending with a label on the output wire that maps to `f(x, y)`. This page covers the construction in detail, the three key optimisations — **point-and-permute**, **free-XOR**, and **half-gates** — that together reduce garbled-circuit cost from one AES per gate row to roughly *two AES per AND gate*, the OT mechanism for input delivery, and cut-and-choose for malicious security.

## The Setting and the Threat Model

Two parties, garbler `G` and evaluator `E`, hold secret inputs `x \\in \\{0,1\\}^\\ell` and `y \\in \\{0,1\\}^\\ell`. They want to learn `f(x, y)` for some public Boolean function `f`. Yao's protocol provides *semi-honest* security against both: each party learns nothing beyond `f(x, y)` assuming the other party follows the protocol. The standard upgrade to malicious security — Lindell-Pinkas cut-and-choose — is covered later.

Two primitives underpin the construction:

- **Symmetric encryption** — a key-derive function `\\mathsf{E}(k, i)` that takes a key `k` and a tweak `i` and produces a pseudorandom value. The canonical choice is fixed-key AES with the tweak used as the message, sometimes called "the garbling scheme of Bellare–Hoang–Rogaway" or the *optimised* scheme.
- **1-out-of-2 Oblivious Transfer (OT)** — the primitive by which `E` learns exactly one of two labels offered by `G` while `G` cannot tell which. See [Oblivious Transfer](./oblivious-transfer.md) for the protocol; for this page we treat OT as a black box that takes `(m_0, m_1)` and an index bit `b` and returns `m_b` without leaking `b`.

## The Garbled Circuit Construction

### Wire Labels

For every wire `w` in the circuit `C`, the garbler picks two random strings `L_w^0, L_w^1` of length `\\kappa` bits (the security parameter, typically 128). `L_w^0` is the "zero" label; `L_w^1` is the "one" label. The invariant maintained during evaluation is: at every wire, the evaluator holds exactly one of `L_w^0, L_w^1` — specifically `L_w^{v}` where `v` is the actual bit flowing through `w` on the inputs `(x, y)` — but does *not* know which one. (Until the output wire, where the labels are paired with their bit values explicitly so the output can be read.)

### Garbled Gates

Consider an AND gate `g = (a, b, c)` with input wires `a, b` and output wire `c`. The truth table has 4 rows: `(0,0) \\to 0, (0,1) \\to 0, (1,0) \\to 0, (1,1) \\to 1`. The garbler encrypts each output label under the pair of input labels that index the row:

```
Row (0,0):  Enc(L_a^0, L_b^0; L_c^0)   # eval gets L_c^0 if holds L_a^0 AND L_b^0
Row (0,1):  Enc(L_a^0, L_b^1; L_c^0)
Row (1,0):  Enc(L_a^1, L_b^0; L_c^0)
Row (1,1):  Enc(L_a^1, L_b^1; L_c^1)   # only this row's plaintext is L_c^1
```

where `Enc(k_1, k_2; m)` is a double-encryption: `m` encrypted under both `k_1` and `k_2`, e.g. as `Enc_{k_1}(Enc_{k_2}(m))`. (Modern schemes use a single hash: `m \\oplus H(k_1, k_2, gate_id)` for the row's "outer" encryption, see *half-gates* below.)

The four ciphertexts are sent to the evaluator in *random order* — the evaluator does not know which row corresponds to which `(a_v, b_v)` value. Given `L_a^{v_a}` and `L_b^{v_b}`, the evaluator tries to decrypt every ciphertext; exactly one decrypts to a valid `L_c^{v}`. In the original scheme this "trial decryption" required a *padding* tag (e.g. an MAC or a known prefix) so the evaluator could identify the correct row.

### Point-and-Permute Optimisation

The trial-decryption step is wasteful: on average each AND gate evaluation costs 2.5 AES calls (one for the obvious row, plus one each for the three wrong rows until we hit the right one). The **point-and-permute** trick (Beaver, Micali, Rogaway, 1990) fixes this: append a *select bit* (also called a *colour bit*) `s \\in \\{0,1\\}` to each wire label, chosen uniformly at random per wire, so that `s(L_w^0) \\ne s(L_w^1)`. The garbler sorts the 4 gate ciphertexts by `(s(L_a^{v_a}), s(L_b^{v_b}))` rather than by `(v_a, v_b)` itself. The evaluator, knowing only the select bits of the labels it holds, can index the right row directly: zero trial decryption, exactly one AES per gate.

```
Garbled AND gate (point-and-permute), wire a: s_a = 0 for v=0, s_a = 1 for v=1
                                  wire b: s_b = 1 for v=0, s_b = 0 for v=1
                                  wire c: pick s_c uniformly at random

  Truth table indexed by (s_a, s_b):
  (s_a=0, s_b=1):   Enc(L_a^0, L_b^0; L_c^0)
  (s_a=0, s_b=0):   Enc(L_a^0, L_b^1; L_c^0)
  (s_a=1, s_b=1):   Enc(L_a^1, L_b^0; L_c^0)
  (s_a=1, s_b=0):   Enc(L_a^1, L_b^1; L_c^1)   <- here we attach s_c = (1-v_c)
                                                  XOR  s_c2  (point bits)
```

After point-and-permute the per-gate cost is 4 AES invocations (one per row, computed by the garbler) plus 1 AES for the evaluator to decrypt its row. Each ciphertext also carries a small MAC for integrity in malicious settings.

### Free-XOR Optimisation

The **free-XOR** trick (Kolesnikov & Schneider, 2008) makes XOR gates literally free — no ciphertexts, no AES calls, no communication. The idea: choose a wire-wise random global *XOR difference* `\\Delta`, and let `L_w^1 = L_w^0 \\oplus \\Delta` on every wire. Now an XOR gate `c = a \\oplus b` produces output labels that are simply the bitwise XOR of the input labels:

```
L_c^0 = L_a^0 XOR L_b^0          L_c^1 = L_a^0 XOR L_b^1
       = L_a^0 XOR L_b^0                = L_a^1 XOR L_b^0
       (matches c=0 for v_a XOR v_b=0) (matches c=1)
```

The XOR is computed locally by the evaluator — no communication, no ciphertext. The garbler must keep `\\Delta` secret and ensure every wire's pair has the same `\\Delta`; an attacker who recovers `\\Delta` learns the global select bit on every wire, which breaks security. In practice free-XOR is universally used because AES-NI makes XOR much cheaper than symmetric encryption; non-XOR-friendly circuits like AES evaluation (not the AES cipher itself, but Yao's garbled AES) benefit dramatically: AES is roughly 50% XOR gates, and free-XOR halves the cost of evaluating each XOR.

### Half-Gate Optimisation

The **half-gate** trick (Zahur, Rosulek, Evans, Eurocrypt 2015) cuts the cost of an AND gate from 4 to 2 ciphertexts — currently the asymptotic optimum (Rose-Lecuyer-Vaikuntanathan lower bound). The construction splits an AND `c = a \\wedge b` into two halves, each computing a one-input "AND-with-constant":

```
c = a ∧ b = (a ∧ (b ⊕ r)) ⊕ (r ∧ a)

where r is a fresh random bit known to the garbler.
```

Each "half-gate" `a \\wedge (\\text{const})` can be garbled with **one ciphertext** per half-gate by exploiting the known constant: with two of these half-gates we garble the full AND with `2 \\times 1 = 2` ciphertexts. The trick relies on free-XOR (so the cost difference is free) and on the garbler knowing `r` but the evaluator not — which is achievable because the *output* of the first half-gate is masked with `r \\wedge a` in a way that cancels out.

```
Half-gate sub-circuit for  a AND b:

  Step 1:  Garbler picks random r.  Evaluator gets L_b^v (v = b's true value).
  Step 2:  Compute "a AND r"  via half-gate H1 (garbler knows r, evaluator knows
           a label and r's label modified by free-XOR tricks; produces share
           of (a AND r)).
  Step 3:  Compute "a AND (b XOR r)"  via half-gate H2 (evaluator can compute
           L_b^v XOR L_b^{v'} using free-XOR if garbler releases a constant-time
           "modified b" label; produces share of (a AND (b XOR r))).
  Step 4:  XOR the two half-gate outputs  -> share of (a AND b).
```

The full derivation is subtle (see the original paper); the punchline is:

| Optimization | Ciphertexts per AND | Notes |
|--------------|----------------------|-------|
| Naive Yao | 4 | trial decryption needed |
| Point-and-permute | 4 | no trial decryption |
| + Free-XOR | 4 (XOR is free) | XOR gates have zero cost |
| + Half-gates | 2 | current optimum |

After half-gates, the dominant per-gate cost is the AES invocation. Modern garbling schemes such as **BHR-dual** (Bellare-Hoang-Rogaway) and **privacy-free** (Zhu et al., 2015, for one-sided output) push the constant further. State-of-the-art Yao protocols (the *ObliVM*, *emp-toolkit*, and *TinyGarble* libraries) achieve around 100 ns per garbled AND on a single core with AES-NI — meaning a 1-billion-AND-gate circuit garbles in ~100 seconds.

### Putting It Together: A Worked Mini-Example

Consider evaluating `f(x, y) = (x AND y) XOR x` for 1-bit inputs. The circuit has one AND gate and one XOR gate:

```
              y ----+
                    |    
              x ----+----[AND g1]----+----[XOR g2]----> out
                    |                |
                    +----------------+
```

Garbler picks labels: `L_x^0 = 0x.....0A`, `L_x^1 = L_x^0 XOR Δ`, `L_y^0 = ...B`, `L_y^1 = L_y^0 XOR Δ`, `L_out^0, L_out^1`, all 16 bytes, all with select bits.

```
Garbled AND g1 (free-XOR + half-gates):
  Row 0:  ct_g1_0 = Enc(L_x^0, L_y^0 ; L_out1^0)   (where L_out1 is the AND half-share wire)
  Row 1:  ct_g1_1 = Enc(L_x^0, L_y^1 ; ...)         -- only 2 ciphertexts (half-gate)

XOR gate g2:  FREE (no ciphertexts; evaluator computes L_out = L_g1_out XOR L_x^v).
```

Garbler sends `(ct_g1_0, ct_g1_1, output_mapping, ⊕-tweak)` to evaluator. Evaluator engages 1-out-of-2 OT with garbler for label `L_y^{v_y}` where `v_y` is the evaluator's input bit. Garbler just sends `L_x^{v_x}` directly (its own input). Evaluator decrypts row of g1, gets `L_g1_out^v`, then XORs with `L_x^{v_x}` to get `L_out^v`. Looks up `v` in the output mapping -> gets the output bit. Total communication: 2 ciphertexts + 2 input labels + 1 OT message ≈ 100 bytes. Total computation: ~5 AES calls on each side.

## Input Labels and Oblivious Transfer

For each input wire `w` belonging to the garbler, the garbler simply sends `L_w^{x_w}` directly — there is no privacy risk because the garbler already knows its own input. For each input wire belonging to the *evaluator*, however, the garbler cannot just send `L_w^{y_w}` because it would reveal `y_w` to the garbler. The parties run a 1-out-of-2 OT: garbler plays OT sender with `(L_w^0, L_w^1)`, evaluator plays OT receiver with choice bit `y_w`, and at the end of the OT the evaluator holds `L_w^{y_w}` and the garbler holds no information about `y_w`.

The cost of these input OTs is `\\ell` OTs per evaluation, where `\\ell` is the evaluator's input length. With the **OT extension** of Ishai-Kilian-Nissim-Petrovic (2003), the amortised cost of `\\ell` OTs is `\\ell` symmetric hash calls after a one-time `\\kappa = 128` public-key base-OT setup. Concretely: `\\ell = 2^{20}` evaluator input bits → 4 MiB of hash work after the ~128 base-OTs.

## Cut-and-Choose for Malicious Security

The semi-honest protocol has an obvious attack: a malicious garbler can construct a *malformed* garbled circuit that computes a function `f' \\ne f` of `x, y`, leaking more than `f(x, y)`. The cut-and-choose paradigm (Lindell-Pinkas, 2007) is the canonical defence:

```
1. Garbler prepares s statistical copies of the garbled circuit,
   each using fresh randomness (independent wire labels and Δ).
                    -->  s × work, s × ciphertext.
2. Evaluator picks a random subset of size s/2 to "open": the
   garbler reveals the randomness for these and the evaluator
   checks they match f.
3. For the remaining s/2 circuits, the evaluator runs the
   semi-honest protocol on each.
4. The parties take a majority vote on the output across the
   s/2 evaluations.

Failure probability: the garbler "gets lucky" with probability
2^{-s/2} that exactly the un-opened half were cheating.
```

The naive overhead is `s \\times` the work and communication, where `s \\approx 40` (for `2^{-40}` cheating probability) is the rule of thumb. Subsequent work — *cut-and-choose with fast evaluation* (Asharov-Lindell-Schneider-Zohner), *leakage-resilient cut-and-choose* (Shelat-Vaikuntanathan, 2013), and the *batched* approach of Brandão-Terelius — reduces the overhead to ~2-3×. The state-of-the-art *TinyTable* / *sieve* (Doerner-shelat-Vaikuntanathan, 2017) line of work drives the constant close to 1.

A more efficient alternative for many scenarios is the *SPDZ-MAC* approach: ensure correctness by tagging every intermediate value with a *verifiable MAC* shared between garbler and evaluator. The end-of-protocol MAC check catches any deviation. This is what modern *BDOZ / TinyOT* protocols do.

## Performance Numbers (Modern Yao)

To calibrate expectations, on a 2024-class x86 with AES-NI, modern garbling schemes achieve:

| Metric | Value |
|--------|-------|
| Garbling throughput (one core) | ~25 M AND gates/sec |
| Evaluation throughput (one core) | ~30 M AND gates/sec |
| Communication per AND gate | ~32 bytes (2 ciphertexts of 16 bytes each, point-and-permute + half-gates) |
| Garbling a full AES-128 circuit (~6000 AND gates) | ~3 ms wall-clock |
| End-to-end Yao with `2^{20}`-bit evaluator input | ~10 ms evaluation + ~50 ms OT extension |

These numbers come from `emp-toolkit` (Chong Hee-Wang et al.) and the `frunken-bbs` (Zhu et al.) benchmarks. In the 2-party setting for asymmetric workloads — where one party does the heavy lifting, like a server evaluating a private model against a client's input — Yao scales well past a billion AND gates per minute with enough parallelism.

## Frequently Asked Questions

**Q1: Why is Yao limited to 2 parties?**
A: Yao's protocol is built around a *1-out-of-2 OT* exchange between a single garbler and a single evaluator. Generalising to `n` parties requires either (a) someone to garble a circuit with `n` evaluator-side inputs but only one garbler (so security collapses if that garbler colludes with any other party), or (b) each party garbles for each other party (`n(n-1)` garbled circuits, with `O(n^2)` overhead). The GMW protocol (see [MPC](./secure-multiparty-computation.md)) is the standard generalisation; it uses Boolean additive sharing instead of garbling, and runs a 1-out-of-4 OT between every pair of parties for every AND gate.

**Q2: What exactly does free-XOR require?**
A: A single wire-wise global XOR difference `\\Delta` shared across all wires, kept secret from the evaluator, and chosen uniformly at random. The "XOR-friendliness" of the underlying encryption scheme is also required: specifically, the garbling scheme must satisfy `Enc(k_1, k_2; m_1 \\oplus m_2) = Enc(k_1 \\oplus \\Delta, k_2; m_1) \\oplus Enc(k_1, k_2 \\oplus \\Delta; m_2)` in some appropriate algebraic sense — the formal treatment is in the *flexXOR* and *half-and-half* line of work. In practice, fixed-key AES with a tweakable hash satisfies this.

**Q3: How does cut-and-choose interact with free-XOR?**
A: It's subtle. The naive "garble s independent circuits" approach has each circuit use its own `\\Delta`, which is fine. But more sophisticated variants (Asharov-Lindell, 2014) reuse `\\Delta` across the s circuits to save bandwidth — and that re-use weakens the cut-and-choose argument because the cheater only needs to "find one `\\Delta` consistent with a malicious circuit", which it can do offline. The trick is to use a *single* `\\Delta` for both halves of the cut-and-choose but to add a *cheat-detection* layer via "two-output" Yao (where both parties get the output) so that a malformed circuit is detectable by either party.

**Q4: How does half-gate lower-bound-optimal performance compare to the theoretical minimum?**
A: Rose-Lecuyer-Vaikuntanathan (Crypto 2014) proved that any garbling scheme that satisfies *privacy* and *authenticity* (the two natural security properties of a garbled circuit) needs *at least* 2 ciphertexts per AND gate. Half-gates matches this lower bound. There is no 1-ciphertext-per-AND scheme without relaxing some security property. Privacy-free garbling (where only the garbler's output is published; the evaluator does not see the output) can hit 1 ciphertext per AND — but that's a different security definition, suitable only for one-sided Yao.

**Q5: What is the OT cost in practice?**
A: With IKNY OT extension (see [Oblivious Transfer](./oblivious-transfer.md)), generating `N` OTs costs ~128 base-OTs (each one public-key, ~1 ms) plus `4N` symmetric hash calls. At 100 M hash calls/sec (SHA-256 with SHA-NI) and `\\kappa = 128` bits, `2^{20}` OTs cost ~5 ms after the base-OT setup. So for a Yao protocol with `\\ell = 2^{20}` evaluator-input bits and a circuit with `\\sim 10^6` AND gates, OT is a fraction of a percent of the cost; the dominant term is the garbling itself.

**Q6: What about deterministic versus randomised garbling?**
A: Modern garbling schemes are *deterministic* given a fixed random tape (this is critical for cut-and-choose to make sense — if the garbler could commit to two different randomnesses the evaluator would catch it only probabilistically). The Bellare-Hoang-Rogaway *gadgets-gadgets-gadgets* line of work formalises this as a **garbling scheme** primitive with formal *privacy*, *authenticity*, and *obliviousness* definitions. Treating garbling as a first-class primitive lets one compose it with other protocols (commitment, ZK) cleanly.

## Cross-References

- [Secure Multi-Party Computation](./secure-multiparty-computation.md) — broader MPC context, including the GMW and SPDZ alternatives.
- [Oblivious Transfer](./oblivious-transfer.md) — the underlying primitive for evaluator-input delivery and the OT extension that makes Yao practical.
- [Threshold Signatures](./threshold-signatures.md) — for `n \\ge 3` parties, threshold signing is usually a better fit than Yao.
- [Zero-Knowledge Proofs](./zk-proofs.md) — ZK proofs of statement about a Yao circuit, often useful for malicious-security upgrades.

## Further Reading

- **Bellare, Hoang, Rogaway — "Garbling Schemes"** (2012) — formalises the garbling primitive; the foundational reference for modern garbled circuit design.
- **"The Tweebox Tutorial on Yao's Garbled Circuits"** by Mike Rosulek — a free, hands-on tutorial that implements a tiny Yao protocol in Python with all three optimisations.
- **emp-toolkit** (https://github.com/emp-toolkit) — the de facto open-source reference implementation of state-of-the-art Yao (and GMW).
- **ABY framework** (Demmler, Schneider, Zohner, 2015) — a C++ library that implements Yao, GMW, and arithmetic sharing with conversions between them.

## References

- Yao, A. C.-C. — *"How to Generate and Exchange Secrets"* (1986), FOCS. The foundational paper that introduced garbled circuits. https://doi.org/10.1109/SFCS.1986.25
- Beaver, D., Micali, S., Rogaway, P. — *"The Round Complexity of Secure Protocols"* (1990), STOC. Introduces point-and-permute. https://doi.org/10.1145/100216.100287
- Bellare, M., Hoang, V. T., Rogaway, P. — *"Foundations of Garbled Circuits"* (2012), CCS. Formal definition of garbling schemes; basis of all modern analysis. https://doi.org/10.1145/2382196.2382279
- Kolesnikov, V., Schneider, T. — *"Improved Garbled Circuit: Free XOR Gates and Applications"* (2008), ICALP. The free-XOR optimisation. https://doi.org/10.1007/978-3-540-70583-3_28
- Zahur, S., Rosulek, M., Evans, D. — *"Two Halves Make a Whole: Reducing Data Transfer in Garbled Circuits using Half-Gates"* (2015), EUROCRYPT. The half-gate optimisation, matching the lower bound. https://eprint.iacr.org/2014/756
- Rose, L., Lecuyer, R., Vaikuntanathan, V. — *"Limits on Garbled Circuits"*, (formal lower bound; Lugrin, Rose, Schröder, 2018). https://eprint.iacr.org/2018/904
- Lindell, Y., Pinkas, B. — *"An Efficient Protocol for Secure Two-Party Computation in the Presence of Malicious Adversaries"* (2007), EUROCRYPT. Cut-and-choose for Yao. https://doi.org/10.1007/978-3-540-72540-4_7
- Asharov, G., Lindell, Y., Schneider, T., Zohner, M. — *"More Efficient Garbled Circuit Construction"* (2014). Cut-and-choose with reduced overhead. https://eprint.iacr.org/2014/080
- Ishai, Y., Kilian, J., Nissim, K., Petrank, E. — *"Extending Oblivious Transfers Efficiently"* (2003), CRYPTO. OT extension that makes Yao scalable. https://doi.org/10.1007/978-3-540-45146-4_2
- Zhu, R., Huang, Y. — *"Faster Garbled Circuit Implementation"* (2017). Modern benchmarks for BHR-dual, privacy-free, and half-gate garbling. https://eprint.iacr.org/2017/323
- Zahur, S., Rosulek, M. — *"Three Halves Make a Whole: Fast Private Set Intersection using Half-Gates"* (2021), EUROCRYPT. Application of half-gates to PSI. https://eprint.iacr.org/2021/929
- Demmler, C., Schneider, T., Zohner, M. — *"ABY — A Framework for Efficient Mixed-Protocol Secure Two-Party Computation"* (2015), NDSS. Reference implementation. https://doi.org/10.14722/ndss.2015.23113
