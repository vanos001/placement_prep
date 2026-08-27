# Sigstore: Signing Without Key Custody

Every code-signing system before Sigstore asked developers the same question:
"here is a private key - guard it for years." Sigstore inverts that. It binds a
signature to an **OIDC identity** (your GitHub login, your CI workflow) using
an **ephemeral key** that exists for minutes, and records every signature in a
public, append-only **transparency log**. Nothing long-lived to leak, no key
ceremonies, and a globally auditable record of who signed what and when. This
page covers the key-management problem, the keyless flow, what such a
signature does and does not prove, production verification policy, and the
Merkle math under the log - with an executable inclusion proof. Signing
primitives are in [Digital Signatures](../cryptography/digital-signatures.md);
build-side guarantees that pair with signing are in
[SBOM and SLSA](./sbom-slsa.md); the tool landscape survey is in
[Software Supply Chain](./software-supply-chain.md).

## The Key-Management Problem

Classic code signing concentrates risk in one long-lived secret:

- **Keys outlive people and teams.** A release key minted in 2019 still
  signs 2026 releases, through job changes, laptop turnover, and CI migration.
- **Leakage is unrecoverable.** Once a signing key escapes, every past and
  future signature is suspect; revocation lists barely help, and you cannot
  retroactively untrust millions of already-signed artifacts. One theft
  mints unlimited valid updates - hence attackers targeting vendor keys.
- **Ceremony does not scale.** Serious keys live in HSMs or EV tokens behind
  access policies - fine for an OS vendor's monthly release, unworkable for a
  monorepo producing hundreds of artifacts per hour. And GPG's web of trust,
  the public-key distribution answer, asked users to attend key-signing
  parties; twenty-five years on, most consumers verify no signatures at all.

## Sigstore's Answer: Identity Instead of Custody

Sigstore is a Linux Foundation project with three cooperating services and
a CLI. **Fulcio** is a certificate authority that watches OIDC identity
tokens (GitHub, Google, Microsoft, or any configured provider) and signs
X.509 certificates binding that identity to a fresh public key - valid for
**10 minutes**, with the private key generated per signing event and then
discarded. **Rekor** is an append-only, tamper-evident transparency log of
signatures and metadata, built on a verifiable Merkle data structure, with
a public instance at `rekor.sigstore.dev`. **Cosign** is the CLI: it signs
container images and blobs, attaches signatures and attestations to OCI
registries as referrers, and verifies with policy checks.

```text
      SIGNER (CI workflow or human)             SIGSTORE PUBLIC INFRASTRUCTURE
      -----------------------------             --------------------------------
  1. authenticate via OIDC  --ID token------>   Fulcio CA: verifies token, issues
                                                X.509 cert: SAN = identity, 10-min
                                                lifetime, chain to Fulcio root
  2. generate ephemeral keypair in memory       (the key never touches disk)
  3. sign the artifact digest with it
  4. submit signature + cert  ----------->    Rekor: appends entry, returns
                                                inclusion promise + timestamp
  5. push artifact; attach signature, cert, and Rekor bundle as OCI referrer
      VERIFIER
      -------------------------------------------
  6. fetch artifact + bundle (or verify fully offline from the bundle)
  7. verify cert chain to the Fulcio root (trust root distributed via TUF)
  8. policy: cert identity + OIDC issuer match expectations?
  9. verify Rekor inclusion proof against the signed tree head
  10. verify artifact digest against signature -> allow / deny
```

**What the signature proves and what it does not.** A keyless signature
attests: *at time T, OAuth identity I (issued by provider P) held the key
that made this signature, and the event is publicly logged.* It does **not**
prove the code is safe or malware-free, and it does not prove the artifact
was built from any particular source revision (that is SLSA provenance's
job). It does not even prove "I" means what you assume unless you pin the
issuer: `deployer@example.com` at Google and at GitHub are different claims
(unverified email claims are attacker-controllable on some providers).

## Verification Policies in Production

Verification is where sloppy policy leaks. The load-bearing cosign flags:

```text
cosign verify ghcr.io/org/app:1.4.2 \
  --certificate-identity-regexp \
      "^https://github.com/org/app/.github/workflows/release.yml@refs/tags/v" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

- **Pin the OIDC issuer, always.** Without `--certificate-oidc-issuer`, any
  account on any supported provider whose email string matches your identity
  check satisfies the policy.
- **Prefer exact identity, or scope regexes tightly.** A GitHub Actions
  identity is the workflow URI including ref, so policy can demand "release
  workflow on a tag ref only", excluding pull-request forks and feature
  branches. Keyless signatures default to a Rekor *bundle* (cert chain +
  inclusion proof + signed tree head), so air-gapped verification needs no
  Rekor connectivity at verify time.
- **Enforce at admission, not in docs.** Sigstore's policy-controller or
  Kyverno can reject wrongly-identified images at deploy time.

## Why a Transparency Log? Merkle Trees, Inclusion Proofs, Gossip

A CA without a public log can misissue silently: Fulcio could hand an
attacker a certificate for `release-eng@example.com`, who signs a valid
artifact, and nobody would ever know. The log changes the economics: every
signature - forged or not - is publicly recorded before it is useful, so
misissuance becomes evidentiary rather than undetectable. This is the
argument that reformed the web PKI after 2011, standardized in RFC 9162
(Certificate Transparency v2). Three Merkle constructions, all SHA-256,
carry the guarantees:

```text
MTH({})     = SHA-256()
MTH({d[0]}) = SHA-256(0x00 || d[0])                 leaf hash
MTH(D[n])   = SHA-256(0x01 || MTH(D[0:k]) || MTH(D[k:n]))
              with k = largest power of two < n     interior node
inclusion proof:   sibling hashes along one leaf-to-root path; a verifier
                   recomputes the root from leaf + path in O(log n)
consistency proof: proof that an older root is a prefix of the newer tree,
                   i.e. the log only ever appends
```

Inclusion proofs answer "is my signature in the log?"; consistency proofs
answer "is the log still append-only?"; and **gossip** - verifiers and
monitors comparing the signed tree heads they have each seen - is what would
expose an operator showing different history views to different clients.
RFC 9162 notes gossip is an active research area "not defined here"; in
practice the ecosystem leans on public monitors auditing the log.

## Worked Example: Building and Verifying an Inclusion Proof

The script builds an RFC 9162-style tree over five entries (not a power of
two, exercising the unbalanced split rule), proves one leaf, and rejects a
tampered leaf:

```python
from hashlib import sha256 as H   # RFC 9162 HASH is SHA-256

def leaf(d):    return H(b"\x00" + d).digest()      # MTH({d[0]}) = HASH(0x00 || d)
def node(l, r): return H(b"\x01" + l + r).digest()  # MTH(D[n]) = HASH(0x01||L||R)
def split(lo, hi):  # k = largest power of two smaller than (hi - lo)
    return lo + (1 << ((hi - lo - 1).bit_length() - 1))

def subtree(lo, hi):                      # pure subtree hash, no proof side effects
    if hi - lo == 1: return leaves[lo]
    k = split(lo, hi)
    return node(subtree(lo, k), subtree(k, hi))

def build_proof(lo, hi, m, acc):          # RFC 9162 PATH(): deepest sibling first
    if hi - lo == 1: return
    k = split(lo, hi)
    if m < k:
        build_proof(lo, k, m, acc); acc.append(subtree(k, hi))
    else:
        build_proof(k, hi, m, acc); acc.append(subtree(lo, k))

def verify(lh, m, n, mth, path):          # RFC 9162 section 2.1.3.2, verbatim
    fn, sn, r = m, n - 1, lh
    for p in path:
        if sn == 0: return False
        if (fn & 1) or fn == sn:          # right child, or last leaf of a subtree
            r = node(p, r)
            if not (fn & 1):              # shift until LSB(fn) set or fn == 0
                while fn and not (fn & 1): fn >>= 1; sn >>= 1
        else:
            r = node(r, p)
        fn >>= 1; sn >>= 1
    return sn == 0 and r == mth

entries = [b"entry 1 | sig=MEUCIQ | oidc=ci-bot@example.com",
           b"entry 2 | sig=MEQCiA | oidc=ci-bot@example.com",
           b"entry 3 | sig=MEUCIR | oidc=release-eng@example.com",
           b"entry 4 | sig=MEQCIB | oidc=ci-bot@example.com",
           b"entry 5 | sig=MEUCIQ | oidc=qa-gate@example.com"]
leaves = [leaf(e) for e in entries]
root = subtree(0, len(entries))
proof = []
build_proof(0, len(entries), 4, proof)    # prove the 5th entry (index 4)
print(f"log entries: {len(entries)} (unbalanced: not a power of two)")
print(f"Merkle Tree Hash (root): {root.hex()}")
print(f"inclusion proof for index 4: {len(proof)} sibling hash(es)")
print(f"  proof[0]: {proof[0].hex()}")
print("verify index 4: recomputed root == log root ->",
      verify(leaves[4], 4, len(entries), root, proof))
forged = leaf(b"entry 5 | sig=DEADBEEF | oidc=ci-bot@example.com")
print("verify tampered leaf at index 4 ->", verify(forged, 4, len(entries), root, proof))
```

Executed output (Python 3.12):

```text
log entries: 5 (unbalanced: not a power of two)
Merkle Tree Hash (root): 70e07c27a0075045f701663a91fae5a01a0f8eb2a8549447d8af7b6670aa2b1d
inclusion proof for index 4: 1 sibling hash(es)
  proof[0]: d6a2bbf68ef9c270e77306c2b2ed323e7894deeff2300153f04168cf7e4ad9b8
verify index 4: recomputed root == log root -> True
verify tampered leaf at index 4 -> False
```

One sibling hash proves membership for entry 5 because the unbalanced tree
makes it the sole leaf of its subtree (`fn == sn` in the RFC algorithm);
deeper leaves need up to 3 siblings. Verification costs O(log n) instead of
downloading the whole log. Two details are load-bearing: the domain-
separation prefixes (`0x00` leaves, `0x01` nodes) prevent a leaf hash from
being reinterpreted as an interior node, and the loop tracks the remaining
subtree size `sn` - the naive "index bits" fold breaks on unbalanced trees.

## Against the Classic Alternatives

| Aspect | GPG-style key signing | Sigstore keyless |
|--------|------------------------|-------------------|
| Signing key lifetime | Years; guarded (or leaked) for years | Minutes; generated per event |
| Identity binding | Self-asserted email/UID on the key | OIDC-verified identity in an X.509 cert |
| Trust root distribution | Web of trust / manual key exchange | Fulcio root, rotated via TUF |
| Revocation story | Publish revocation cert; hope it propagates | Wait ten minutes; the key no longer exists |
| Public accountability | Keyservers; effectively unaudited | Every signature in an append-only log |
| Developer experience | Keygen, passphrases, expiry management | OAuth login (or nothing, in CI) |

Two adjacent ecosystems solve problems Sigstore deliberately does not, and
compose with it. **TUF (The Update Framework)** protects repository metadata
with roles, key thresholds, offline root keys, expiry, and rollback
protection; Sigstore's own clients fetch their Fulcio/Rekor trust material
from a TUF root. **Notary v2 / Notation** standardizes registry-native
signature envelopes for OCI artifacts with conventional PKI certificates -
the choice for enterprises exchanging signed artifacts with their own CAs.

## Adoption Reality

- **The public good instance is production infrastructure.**
  `fulcio.sigstore.dev` and `rekor.sigstore.dev` run as a free centralized
  service (the public Rekor advertises a 99.5% availability SLO with an
  on-call), accepting Google, Microsoft, and GitHub identities.
- **Ecosystems absorbed it silently.** npm generates Sigstore-backed
  provenance on publish; GitHub's artifact attestations are issued through
  the public instance; PyPI's trusted publishing is OIDC-based and attaches
  Sigstore-verifiable attestations. Most users have verified one without
  knowing it.
- **Private instances and keyed signing.** Fulcio and Rekor are open source
  and self-hostable (the scaffolding project packages a private deployment),
  but your private Fulcio root is only as trustworthy as its operations, and
  you inherit log ops, key rotation, and monitoring that the public instance
  amortizes. `cosign sign --key` covers OIDC-less environments.

## Failure Modes and Sharp Edges

- **Policy regression to "any signature".** Verifying that something is
  signed without identity + issuer pinning reduces the guarantee to
  "someone, somewhere, once signed this."
- **Log writes are on the signing path.** Keyless signing requires a Rekor
  entry; a down log stops releases. Decide whether that is a feature (no
  unlogged signatures) or an availability risk.
- **Ten-minute certs and stale trust roots.** Short certificate lifetime
  limits the blast radius of a stolen ephemeral key but says nothing about
  what was signed - pair with provenance ([SBOM and SLSA](./sbom-slsa.md)).
  Offline bundles check against an embedded trust root; keep it fresh (TUF).

## References

1. [Sigstore Documentation](https://docs.sigstore.dev/) - project overview, quickstarts, verification cheat sheet
2. [Fulcio Overview](https://docs.sigstore.dev/fulcio/overview/) - OIDC-bound X.509 certificates valid for 10 minutes
3. [Rekor Overview](https://docs.sigstore.dev/rekor/overview/) - append-only transparency log, public instance, auditor tooling
4. [Cosign on GitHub](https://github.com/sigstore/cosign) - sign/verify flags, keyless bundles, offline verification
5. [RFC 9162: Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html) - Merkle Tree Hash, inclusion and consistency proofs, gossip
