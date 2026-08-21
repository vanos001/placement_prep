# Threshold Signatures (FROST)

Threshold signatures are a class of cryptographic schemes where `t` of `n` participants must cooperate to produce a valid signature. The signature is indistinguishable from one produced by a single signer — observers cannot tell that threshold signing was used. This page covers the threshold signing model, the FROST protocol (the most popular modern threshold Schnorr scheme), the relationship to multi-signature and Shamir secret sharing, and the production use cases (cryptocurrency wallets, MPC custody, government systems).

## The Threshold Model

A threshold signature scheme with parameters `(t, n)`:
- `n` participants hold shares of a single private key.
- Any subset of `t` or more participants can produce a signature.
- Fewer than `t` participants cannot produce a signature, even with unlimited computation.
- The corresponding public key is a single key, indistinguishable from a normal one.

The classic example is a "2-of-3" custody wallet: three signers hold key shares; any two can sign, but one alone cannot. The signed transaction looks identical to one signed by a single-key wallet.

## Comparison to Alternatives

| Scheme | Signature size | Signers visible | Threshold |
|--------|-----------------|-----------------|-----------|
| Single-sign | 1× | 1 | t=1, n=1 |
| Multisig (Bitcoin) | N× (one per signer) | N | Any t of N |
| Threshold (FROST) | 1× | Looks like 1 | Any t of N |
| Shamir Secret Sharing | Requires reconstruction | — | t of n to reconstruct |

Multisig (e.g., Bitcoin's `CHECKMULTISIG`) includes all signers' public keys and signatures in the transaction, bloating it. Threshold signing produces a single signature that's indistinguishable from single-sig — smaller transactions, less blockchain bloat, privacy for the signer set.

Shamir Secret Sharing reconstructs the secret before signing, exposing it to whoever runs the reconstruction. Threshold signing never reconstructs — the signing is done via MPC (multi-party computation), and the secret stays distributed.

## FROST: The Modern Threshold Schnorr Protocol

FROST (Flexible Round-Optimized Schnorr Threshold signatures) was introduced by Komlo and Goldberg in 2020 (IACR ePrint 2020/852). It builds on Schnorr signatures and uses two rounds of communication among the threshold signers.

### Setup (Distributed Key Generation - DKG)

The n participants collectively generate a key pair without anyone ever holding the full private key:

1. Each participant `i` generates a random polynomial `f_i(x) = sum_{j=0}^{t-1} a_{i,j} * x^j` of degree `t-1` with random coefficients.
2. Each `i` sends `f_i(j)` to participant `j` (via a private channel).
3. Each `j` computes their key share: `s_j = sum_i f_i(j)`.
4. The public key is `Y = sum_i a_{i,0} * G` (where `G` is the generator of the elliptic curve).
5. Each `i` also publishes commitments `C_{i,k} = a_{i,k} * G` for `k = 0..t-1`. These let participants verify that the share they received is consistent with the polynomial.

The "secret" `s = sum_i f_i(0) = sum_i a_{i,0}` is never computed by anyone; only its shares `s_j` are. The public key `Y = s * G` can be computed without knowing `s`.

### Signing (two rounds)

To sign a message `m` with threshold `t`:

**Round 1 (commitment)**:
1. Each of the `t` signers picks a random nonce `d_i` and `e_i`, computes `D_i = d_i * G` and `E_i = e_i * G`.
2. Each signer broadcasts `(D_i, E_i)` to all other signers.
3. Each signer also broadcasts a proof that they know `d_i` and `e_i` (a Schnorr-like proof).

**Round 2 (response)**:
1. The aggregator computes the binding values `ρ = H1(m, list of D_i and E_i)`.
2. Each signer computes their per-signer nonce: `R_i = D_i + ρ * E_i`.
3. The aggregate `R = sum_i R_i` is the signature's `R` component.
4. Each signer computes their response: `z_i = d_i + ρ * e_i + c * λ_i * s_i` where `c = H2(m, R, Y)` is the challenge and `λ_i` is the Lagrange coefficient for signer `i`.
5. Each signer broadcasts `z_i` to the aggregator.

**Aggregation**:
1. The aggregator computes `z = sum_i z_i`.
2. The signature is `(R, z)`.
3. Verification: `z * G == R + c * Y`.

The signature `(R, z)` is a standard Schnorr signature on the message `m` with public key `Y`. Any standard Schnorr verifier accepts it; they cannot tell it was produced by a threshold scheme.

### Security of FROST

FROST's security proof assumes:
- The discrete log problem is hard.
- The hash function H1, H2 are modeled as random oracles.
- At most `t-1` participants are malicious (Byzantine).
- Round 1 commitments are binding (the binding value `ρ` prevents signers from changing their nonce after seeing others' nonces).

The protocol resists:
- **Nonce reuse attacks**: a signer cannot reuse a nonce across sessions (the binding value differs).
- **Malicious aggregator**: the aggregator cannot forge a signature that wasn't actually signed by the threshold (the per-signer `z_i` are individually verifiable).
- **Concurrent signing sessions**: FROST supports concurrent sessions on the same key with distinct messages, each producing a valid signature.

## Production Use Cases

### Cryptocurrency custody

The dominant production use: exchanges and custodians (Coinbase Custody, Anchorage, Fireblocks) use threshold signatures to custody customer funds without exposing the full private key:

- A 2-of-3 threshold: signer 1 on a hardware wallet (in a vault), signer 2 on a server, signer 3 on a backup HSM. Any two can sign a withdrawal; one alone cannot.
- A 3-of-5 threshold for larger funds: more redundancy, slower operations.

The threshold scheme ensures that compromising one signer doesn't compromise the funds. The single-signature appearance reduces on-chain fees (no multisig script).

### MPC wallets (ZenGo, Fireblocks, Lit)

Mobile cryptocurrency wallets use threshold signing to split the key between the user's phone and the wallet provider's server. The user authenticates via biometrics; the server signs its share; the combined signature moves the funds. If the phone is stolen, the thief cannot sign without the server's cooperation.

### Government systems

Some classified systems use threshold cryptography for nuclear launch authorization (a famous 2-of-3 or 3-of-5 pattern). The exact protocols are classified, but the principle is the same.

### HSM-backed signing

Hardware Security Modules (HSMs) from Yubico, Thales, and Entrust support threshold signing internally — the HSM holds multiple key shares and requires multiple operators to approve a signing operation. The threshold is enforced by the hardware.

## Comparison to Other Threshold Schemes

| Scheme | Year | Sig type | Rounds | t-of-n | Production users |
|--------|------|-----------|--------|--------|---------------------|
| Shamir + Schnorr | 1979+ | Schnorr | 3 (DKG + commit + sign) | Any | Rare |
| GG18 | 2018 | ECDSA | 4 | Any | Fireblocks, BitGo |
| CMP20 | 2020 | ECDSA | 3 | Any | Anchorage, Coinbase |
| FROST | 2020 | Schnorr | 2 | Any | Mobile wallets, Zcash |
| FROST2 | 2022 | Schnorr | 2 | Any | Newer deployments |

The ECDSA-based schemes (GG18, CMP20) are more complex because ECDSA signatures require an inverse computation that's awkward in MPC. FROST, being Schnorr-based, is simpler and faster.

For Bitcoin (which uses ECDSA and now also Schnorr via Taproot), FROST is the modern choice. For Ethereum (which uses ECDSA only), CMP20 is the production threshold scheme.

## Common Pitfalls

1. **Forgetting that DKG must run over an authenticated channel.** If an attacker can intercept DKG messages, they can substitute their own shares and effectively control the key. Use TLS or pre-shared authentication.

2. **Storing key shares insecurely.** Each signer's key share is as sensitive as a private key. If a signer's share leaks, the threshold drops (e.g., 2-of-3 becomes 1-of-2 if one share leaks). Use HSMs or OS keyrings.

3. **Reusing nonces across sessions.** FROST's security depends on each signer using a fresh random nonce per session. A signer who reuses a nonce across two sessions leaks their key share (similar to the ECDSA k-reuse attack).

4. **Not verifying commitments in Round 1.** A malicious signer can submit a commitment they don't actually know the discrete log of, breaking the protocol. Always verify the proof of knowledge in Round 1.

5. **Trusting the aggregator with raw `z_i`.** The aggregator receives individual `z_i` values; a malicious aggregator could combine them incorrectly. Each signer should send `z_i` to all other signers, not just the aggregator.

6. **Using a non-uniform nonce generation.** If nonces are generated with a biased random number generator (e.g., `Math.random()`), the bias can leak the key share over many sessions. Use `crypto_random` or derive the nonce deterministically from `H(secret_seed || session_id)`.

7. **Forgetting that FROST requires at least 2 signers.** A "1-of-1 FROST" is just a standard Schnorr signature; using FROST for single-signature use cases adds complexity without benefit.

## References

- Komlo & Goldberg, "[FROST: Flexible Round-Optimized Schnorr Threshold signatures](https://eprint.iacr.org/2020/852)" (IACR ePrint 2020/852)
- [BIP 340: Schnorr signatures for Bitcoin](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki)
- [BIP 327: MuSig2 (related multi-sig scheme)](https://github.com/bitcoin/bips/blob/master/bip-0327.mediawiki)
- [Zcash FROST implementation](https://github.com/ZcashFoundation/frost)
- [Threshold Networks Corporation (TACo) documentation](https://docs.threshold.network/)
- Gennaro & Goldfeder, "[Multi-party ECDSA](https://eprint.iacr.org/2020/852)" (CMP20 paper, IACR 2020)
- [LWN: Threshold signatures and cryptocurrency custody (2022)](https://lwn.net/Articles/905889/)
- [Fireblocks: How MPC works](https://www.fireblocks.com/blog/what-is-mpc/)
