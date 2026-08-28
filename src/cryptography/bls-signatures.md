# BLS Signatures

BLS signatures (Boneh, Lynn, Shacham, 2001) are the only widely deployed signature scheme whose signatures can be *aggregated*: a thousand signatures from a thousand different keys collapse into one short signature that verifies in a single check. That one property is why Ethereum's consensus layer, drand, Chia, and DFINITY all run on BLS. The cost is a far more expensive primitive underneath: the bilinear pairing.

## The Bilinear Pairing, Informally

A pairing is a map between elliptic-curve groups with one special algebraic property:

```text
bilinear map  e : G1 x G2 -> GT     (all three groups of prime order r)

  e(P1 + P2, Q)  = e(P1, Q) * e(P2, Q)     (additive notation in G1/G2)
  e(P, Q1 + Q2)  = e(P, Q1) * e(P, Q2)
  e(a*P, b*Q)    = e(P, Q)^(a*b)           <- the money property

non-degenerate:   e(P1, P2) != 1_GT  (the map is not trivially constant)
efficient:        computable without knowing a or b (Miller loop + final
                  exponentiation; the pairing is public infrastructure)
```

Think of `e` as a *remote exponentiator*: you cannot multiply `H(m)` by someone else's secret `sk`, but `e(H(m), sk*P2)` reveals the result of that multiplication in the target group — exactly what the verification check `e(H(m), PK) == e(sigma, P2)` exploits. BLS12-381 uses an *asymmetric* (type-3) pairing: G1 and G2 are different groups with no efficient isomorphism between them. G1 elements live on a curve over a 381-bit prime field (cheap, 48-byte points); G2 elements live over the degree-2 extension Fp2 (96-byte points, slower arithmetic). The toy demo at the bottom of this page uses a *symmetric* model (G1 = G2) because the algebra is identical — do not carry that symmetry into real designs. Pairings also power zk-SNARK verification (Groth16, PLONK); that side is covered in [zk-proofs](./zk-proofs.md).

## The Core Scheme

```text
KeyGen:   sk    <- random scalar in [1, r)          (r = subgroup order)
SkToPk:   PK    = sk * P2                           (P2 = generator of G2)
Sign:     sigma = sk * H(m)                         (H(m) in G1, hash-to-curve)
Verify:   check e(H(m), PK) == e(sigma, P2)

  e(H(m), sk*P2)  =  e(H(m), P2)^sk  ==  e(sk*H(m), P2)     (bilinearity)
```

Verification is one pairing equation — two evaluations, or one *product of pairings* `e(sigma, P2) * e(H(m)^-1, PK) == 1` sharing a single final exponentiation. There is no nonce: signing is deterministic, and a signature is just the hash of the message scaled by the secret key.

The standard instantiation is the BLS12-381 curve, chosen so the pairing stays fast while the discrete log stays hard. A frequent point of confusion: **BLS12-381 is not a 255-bit field** — the *base field* p is 381 bits; it is the *subgroup order* r that is a 255-bit prime.

```text
BLS12-381 (embedding degree 12; z = -0xd201000000010000)
  p = (z-1)^2 (z^4 - z^2 + 1) / 3 + z      381-bit base field prime
  r = z^4 - z^2 + 1                        255-bit subgroup order (G1 and G2)
  G1: order-r subgroup of E(Fp)  : y^2 = x^3 + 4
  G2: order-r subgroup of E'(Fp2): y^2 = x^3 + 4(u+1),  Fp2 = Fp[u]/(u^2+1)
  security target ~128 bits; ~117-120 bits under the exTNFS finite-field
  attacks (accepted trade for pairing speed)
```

| Quantity | Group / field | Compressed size | Uncompressed |
|---|---|---|---|
| G1 point (E over Fp) | 381-bit field | 48 B | 96 B |
| G2 point (E' over Fp2) | Fp2 = Fp[u]/(u²+1) | 96 B | 192 B |
| GT element (pairing target) | Fp12 | 576 B | 576 B |
| Scalar (mod r) | 255-bit | 32 B | 32 B |

Whichever group the *signature* lands in, the scheme can be tuned: signatures in G1 (48 B) with keys in G2 (96 B), or the reverse. That choice is the "min-sig vs min-PK" knob the IETF draft formalizes as separate ciphersuites.

## Signature Aggregation and the Pairing Budget

Aggregation is plain group addition. Given signatures `sigma_i = sk_i * H(m_i)`, anyone — a blockchain aggregator, a relay, a browser — computes `sigma = sum(sigma_i)`. The check that ties it to all keys:

```text
CoreAggregateVerify((PK_1..PK_n), (m_1..m_n), sigma):
  group the n messages into l distinct messages m_1..m_l
  per distinct message: sum the public keys signing it
  check:  product_i e(H(m_i), PK_sum_i)  ==  e(sigma, P2)
```

Because verification counts pairings, and pairings are two to three orders of magnitude more expensive than an Ed25519 point multiplication, the *shape* of your verification matters more than anything else:

| Verification path | Pairings | Why |
|---|---|---|
| CoreVerify (single signer) | 2 | one equation, both sides |
| AggregateVerify, n distinct messages | n + 1 | one pairing per distinct message |
| FastAggregateVerify, n signers, same message | 2 | sum keys first, then CoreVerify |
| PopVerify (key registration) | 2 | one equation |

All variants reduce to `n + 1` Miller loops and one shared final exponentiation in an optimized product-pairing implementation. The "fast" in FastAggregateVerify is structural: identical messages (the common case in consensus) collapse the per-signer pairings into one — the whole reason consensus protocols obsess over "everyone signs the same data".

## Rogue Keys: The Attack and Three Defenses

Aggregation as written above has a hole. An attacker who registers a public key *constructed* rather than *generated* can hijack the aggregate.

```text
Rogue-key attack (no key validation):
  victim's key:      PK_v = sk_v * P2          (sk_v unknown to attacker)
  attacker picks:    a*  (own scalar)
  attacker submits:  PK* = a**P2 - PK_v        (point arithmetic only!)
  aggregate key:     PK* + PK_v = a**P2        <- secret a* is KNOWN
  forge, no victims involved:
      sigma* = a* * H(m)  for any m
  verify:  e(H(m), PK* + PK_v) = e(H(m), a**P2) = e(a**H(m), P2) = e(sigma*, P2)
  => VALID for any message, under the attacker's sole control
```

The IETF draft (`draft-irtf-cfrg-bls-signature`) defines three schemes that close this, each with a different trade:

| Scheme | Rogue-key defense | Aggregate verify | Messages | Ciphersuite suffix |
|---|---|---|---|---|
| Basic | require all messages distinct | n + 1 pairings | distinct only | `_NUL_` |
| Message augmentation | sign over the concatenation of PK and m | n + 1 pairings | any | `_AUG_` |
| Proof of possession | validate PoP at registration | 2 pairings (same msg) | any | `_POP_` |

- **Basic** kills the attack *socially*: the algebra above needs attacker and victim to sign the *same* message, so `AggregateVerify` rejects duplicate messages. Cheap, but it forbids the same-message fast path.
- **Message augmentation** binds each signature to the signer's key: `sigma_i = sk_i * H(PK_i || m_i)`. The attacker's `PK*` changes its own hash, so precomputed forgeries no longer line up.
- **Proof of possession** (PoP) is the strongest and the one Ethereum uses: before a key may participate in aggregation, its owner must present `proof = sk * H_pubkey(PK)`. Verifying `e(H_pubkey(PK), PK) == e(proof, P2)` proves knowledge of `sk` — a rogue key `PK* = a**P2 - PK_v` has an owner who *cannot* produce that proof, because its "secret" `a* - sk_v` is unknown even to the attacker. The demo below runs exactly this check on toy numbers.

## What Ethereum Actually Runs

The eth2 beacon chain pins the IETF draft's **proof-of-possession** family with ciphersuite `BLS_SIG_BLS12381G2_XMD:SHA-256_SSWU_RO_POP_` — note `G2`: messages hash to G2, so *signatures are 96-byte G2 points and public keys are 48-byte G1 points* (`BLSSignature = Bytes96`, `BLSPubkey = Bytes48` in the phase0 spec). The spec defines six `bls.*` interface functions — `Sign`, `Verify`, `Aggregate`, `AggregateVerify`, `FastAggregateVerify`, `KeyValidate` — and uses them asymmetrically:

```text
attestation path (the hot one, ~7,500+ attestations per epoch):
  validators v0..vN of a committee all sign the SAME data
  v_i:        sigma_i = bls.Sign(sk_i, data)                (G2 point)
  aggregator: sigma_agg = bls.Aggregate(sigma_0..sigma_N)   (G2 addition)
              one SignedAggregateAndProof on the wire
  beacon chain: bls.FastAggregateVerify([pk_0..pk_N], data, sigma_agg)
                check e(H(data), sum(pk_i)) == e(sigma_agg, P1)  <- 2 pairings

single-signer paths (bls.Verify, 2 pairings each): block proposal
  signature, RANDAO reveal, voluntary exit, proposer slashing headers

deposits = the PoP ceremony:
  the deposit signature over (pubkey, withdrawal_credentials, amount) is a
  proof of possession -- the spec comments it is "not checked by the deposit
  contract", so the chain enforces PoP before adding the validator
```

One nuance worth knowing for interviews: the eth2 spec text (phase0) cites **draft-irtf-cfrg-bls-signature-04**, while the draft series has since advanced in the IRTF editor's copy (the CFRG GitHub mirror is at -07). What the chain runs is fixed by the spec's pin, so the precise statement is "eth2 uses draft-04 with the POP suite". Aggregate verification failures are consensus-failure risks, which is why `KeyValidate` (subgroup checks, non-identity) runs on every key before pairing math — see [consensus mechanisms](../blockchain/consensus-mechanisms.md) for where these aggregates sit in the bigger O(n²)→O(n) picture.

## Hash-to-Curve

BLS signs arbitrary bytes, but `sk * H(m)` needs H(m) to be a *curve point*. Naive "hash then increment x until y is on the curve" works but is non-constant-time and awkward to specify, so the IETF standardized hash-to-curve as RFC 9380, which the BLS draft invokes:

- **expand_message_xmd** with SHA-256 stretches the message into uniformly hashed field elements, seeded by a domain separation tag — for eth2 that DST is the full ciphersuite name `BLS_SIG_BLS12381G2_XMD:SHA-256_SSWU_RO_POP_`.
- **Simplified SWU** (SSWU) maps the field element to a point on an isogenous curve; for BLS12-381 G1 that is an 11-isogeny map onto E: y² = x³ + 4, an indirection chosen because the isogenous curve has a cheaper map.
- **Clearing the cofactor** maps into the order-r subgroup; RFC 9380's BLS12-381 suites pick the effective cofactor `h_eff = 0xd201000000010001` specifically to enable Scott's fast cofactor-clearing method. The `RO` vs `NU` suffix distinguishes random-oracle (hash_to_curve) from non-uniform (encode_to_curve) encodings; BLS suites use RO.

## Threshold BLS

BLS thresholds almost trivially because there is no nonce to coordinate: split `sk` into shares `sk_i` via Shamir over the scalar field, each participant signs `sigma_i = sk_i * H(m)` (exactly a normal BLS signature), and any t shares reconstruct `sigma = sum(lambda_i * sigma_i)` with Lagrange coefficients `lambda_i`. The result is indistinguishable from a single-key signature, and verification is unchanged. Compared to threshold Schnorr (FROST) you save a round of communication — no nonce commitments — at the price of pairing costs. Details: [threshold signatures](./threshold-signatures.md).

## Toy Algebra: Rogue Key vs Proof of Possession

Pure-Python simulation over a tiny safe-prime field: the toy pairing `e(h^x, h^y) = h^(xy)` is bilinear and non-degenerate like the real thing, and the attacker's code never needs a discrete log, exactly as in a 255-bit group.

```python
import hashlib
from math import prod

# Toy BLS algebra over F_p^*. p = 10007 is a safe prime (p-1 = 2*q, q = 5003
# prime); G = <HBASE> has prime order q. Toy pairing e(h^x, h^y) = h^(x*y) is
# bilinear, non-degenerate, computable only because q is tiny (brute-force
# dlog). A real pairing does this on 255-bit groups via Miller loops, with no
# discrete logs at all. Illustrates the ALGEBRA, not cryptographic security.

p, q = 10007, 5003

HBASE = pow(5, 2, p)   # 5 is a primitive root mod 10007 -> HBASE has order q
PAIR_CALLS = 0

def dl(x):                           # toy-world dlog (the pairing's "engine")
    for j in range(q):
        if pow(HBASE, j, p) == x % p:
            return j
    raise ValueError("not in <HBASE>")

def e(a, b):                         # e(h^x, h^y) = h^(x*y): bilinear
    global PAIR_CALLS
    PAIR_CALLS += 1
    return pow(HBASE, (dl(a) * dl(b)) % q, p)

def hash_pt(msg):                    # toy hash-to-curve: H(m) = h^t
    t = int.from_bytes(hashlib.sha256(msg).digest(), "big") % q
    return pow(HBASE, t, p)

def keygen(seed):
    sk = int.from_bytes(hashlib.sha256(seed).digest(), "big") % q
    return sk, pow(HBASE, sk, p)

def sign(sk, msg):
    return pow(hash_pt(msg), sk, p)

# A. honest single-signer round trip: e(H(m), PK) == e(sigma, P)
sk_a, pk_a = keygen(b"validator-A")
msg = b"block-root-42"
sigma = sign(sk_a, msg)
print("A. honest single-signer verify:",
      "VALID" if e(hash_pt(msg), pk_a) == e(sigma, HBASE) else "INVALID")

# B. aggregate 8 signatures over 8 DISTINCT messages: n+1 pairings
keys = [keygen(("validator-%d" % i).encode()) for i in range(8)]
msgs = [("attestation-%d" % i).encode() for i in range(8)]
agg = prod(sign(sk_i, m_i) for (sk_i, _), m_i in zip(keys, msgs)) % p
PAIR_CALLS = 0
rhs = prod(e(hash_pt(m_i), pk_i) for (_, pk_i), m_i in zip(keys, msgs)) % p
ok = e(agg, HBASE) == rhs
print("B. AggregateVerify, 8 distinct msgs:", "VALID" if ok else "INVALID",
      "| pairings used:", PAIR_CALLS, "(n + 1 = 9)")

# C. rogue-key attack when same-message aggregation is unprotected
a_star = 777                                    # attacker's own scalar
pk_rogue = pow(HBASE, a_star, p) * pow(pk_a, -1, p) % p   # = h^(a*-sk_a)
forged = pow(hash_pt(msg), a_star, p)           # attacker forges the whole agg
PAIR_CALLS = 0
ok = e(forged, HBASE) == e(hash_pt(msg), pk_a) * e(hash_pt(msg), pk_rogue) % p
print("C. rogue-key forge on shared msg:", "VALID (attack succeeds)" if ok else "INVALID",
      "| attacker's dlog use: none")

# D. basic scheme: distinct-message rule kills the same forge
ok = e(forged, HBASE) == e(hash_pt(msg), pk_a) * e(hash_pt(msgs[3]), pk_rogue) % p
print("D. same forge vs distinct-msg rule:", "VALID" if ok else "INVALID")

# E. proof of possession: rogue key cannot register
def pop_prove(sk, pk):                          # PopProve: sign H(PK)
    return pow(hash_pt(str(pk).encode()), sk, p)

def pop_verify(pk, proof):                      # e(H(PK), PK) == e(proof, P)
    return e(hash_pt(str(pk).encode()), pk) == e(proof, HBASE)

best = pow(hash_pt(str(pk_rogue).encode()), a_star, p)    # attacker's best try
print("E. PoP on rogue key:",
      "VALID" if pop_verify(pk_rogue, best) else "INVALID (registration rejected)")
print("   PoP on honest key:",
      "VALID" if pop_verify(pk_a, pop_prove(sk_a, pk_a)) else "INVALID")

# F. PoP-protected fast aggregation, same message: 2 pairings
pk_agg = prod(pow(HBASE, sk_i, p) for sk_i, _ in keys) % p
sig_agg = prod(sign(sk_i, msg) for sk_i, _ in keys) % p
PAIR_CALLS = 0
ok = e(hash_pt(msg), pk_agg) == e(sig_agg, HBASE)
print("F. FastAggregateVerify, 8 signers, same msg:", "VALID" if ok else "INVALID",
      "| pairings used:", PAIR_CALLS, "(independent of n)")
```

Output (real run, 0.06 s):

```text
A. honest single-signer verify: VALID
B. AggregateVerify, 8 distinct msgs: VALID | pairings used: 9 (n + 1 = 9)
C. rogue-key forge on shared msg: VALID (attack succeeds) | attacker's dlog use: none
D. same forge vs distinct-msg rule: INVALID
E. PoP on rogue key: INVALID (registration rejected)
   PoP on honest key: VALID
F. FastAggregateVerify, 8 signers, same msg: VALID | pairings used: 2 (independent of n)
```

Read panel C against the attack walkthrough above: `pk_rogue = h^(a*-sk_a)` is built by pure multiplication, the forged aggregate verifies for the attacker's own message, and no discrete log was consulted. Panels D and E are the two defenses on the same numbers.

## BLS vs Ed25519 vs ECDSA

| Property | BLS12-381 (BLS sig) | Ed25519 | ECDSA P-256 |
|---|---|---|---|
| Signature size | 96 B (eth2) / 48 B (G1 suites) | 64 B | 64 B |
| Public key size | 48 B (eth2) / 96 B (G1 suites) | 32 B | 32-33 B |
| Verify cost (relative) | ~1 pairing-based equation, ~ms class | ~100 us, batchable | ~250 us |
| Aggregate many sigs -> one | Yes, native | No (MuSig2 = interactive) | No |
| Deterministic signing | Yes (no nonce) | Yes (RFC 8032) | No (k-reuse fatal) |
| Misuse resistance | High | High | Low |
| Post-quantum | No | No | No |

BLS loses on raw speed everywhere — a single pairing costs roughly an order of magnitude more than an Ed25519 verification — and wins wherever *one* verifier must check *many* signers. The decision rule: single-signer protocols (SSH, TLS client certs, package signing) belong on Ed25519 ([Ed25519 deep dive](./ed25519.md)); many-signer consensus belongs on BLS.

## Where It Runs

- **Ethereum consensus**: every validator attestation, block proposal, and deposit since the Beacon Chain genesis — the aggregation rules above.
- **drand / League of Entropy**: threshold BLS randomness beacons — each round's randomness is a threshold-BLS signature on a counter, uniform by the random-oracle behavior of hash-to-curve.
- **Chia** signs every transaction with BLS and aggregates for block space; **DFINITY** uses threshold BLS for consensus and randomness.

## References

1. D. Boneh, B. Lynn, H. Shacham, "Short Signatures from the Weil Pairing", ASIACRYPT 2001, LNCS 2248 — <https://doi.org/10.1007/3-540-45682-1_30> (extended version: Journal of Cryptology 17(4), 2004, DOI 10.1007/s00145-004-0314-9)
2. IRTF CFRG, "BLS Signature Scheme", Internet-Draft `draft-irtf-cfrg-bls-signature` (eth2 pins version -04; series tracked at) — <https://datatracker.ietf.org/doc/draft-irtf-cfrg-bls-signature/>
3. A. Faz-Hernandez, S. Scott, N. Sullivan, R. S. Wahby, C. A. Wood, "Hashing to Elliptic Curves", RFC 9380 — <https://www.rfc-editor.org/rfc/rfc9380.html>
4. zkcrypto, "BLS12-381" curve reference implementation and parameter notes — <https://github.com/zkcrypto/bls12_381>
5. Ethereum, "Consensus Specifications — Phase 0 Beacon Chain" (BLS interface, deposit PoP, indexed attestation rules) — <https://github.com/ethereum/consensus-specs/blob/master/specs/phase0/beacon-chain.md>
