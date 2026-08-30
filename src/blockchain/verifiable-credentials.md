# Verifiable Credentials and Decentralized Identity

The default web identity model gives every service its own account store and pushes the burden of linking those accounts onto centralized identity providers (Google, Apple, Microsoft) that can observe, restrict, or revoke access at will. The W3C Verifiable Credentials (VC) and Decentralized Identifier (DID) stack inverts that shape: the user holds cryptographically signed claims in a wallet, and anyone can check those claims against the issuer's public key without calling the issuer. This page covers the data model, DID syntax and resolution, proof formats and selective disclosure, revocation and governance, real deployments, and the places where the model is weaker than the marketing suggests.

## The Identity Problem

Three failure modes motivated the redesign:

| Failure mode | Consequence |
|--------------|-------------|
| **Siloed accounts** | Every service re-runs enrollment, password reset, and support; users maintain hundreds of credentials |
| **Password reuse** | One breach cascades across services that share the password |
| **Centralized IdPs** | Federation (SAML, OIDC) concentrates a surveillance and censorship point in one provider; the IdP sees every login and can deplatform |

SAML and OIDC both center the *provider*: the identity provider issues assertions about the user and remains in the loop forever. The self-sovereign identity (SSI) movement, articulated in Christopher Allen's "Path to Self-Sovereign Identity" ten principles (2016), proposed flipping control: the subject holds their own identifier and credentials. It is fair to state the criticism openly -- much of SSI's rhetoric ("sovereignty", "users own their identity") is ideology rather than engineering. The testable claim is narrower: for some trust relationships, a signed-claim wallet model is cheaper, more private, and more available than an online IdP. Where that claim fails, SSI degenerates into OIDC with extra steps -- which is exactly how some did:web deployments behave.

## W3C Verifiable Credentials Data Model 2.0

The VC Data Model 2.0 (W3C Recommendation) defines a JSON data structure and four roles:

| Role | Acts as | Example |
|------|---------|---------|
| **Issuer** | Asserts claims about a subject and signs them | University, government registry, employer |
| **Holder** | Stores credentials, generates presentations | The user's wallet (may not be the subject) |
| **Subject** | Entity the claims are about | Identified by `credentialSubject.id` |
| **Verifier** | Checks proofs and decides whether to trust the claims | Age gate, employer, customs officer |

A *verifiable credential* is a tamper-evident set of claims signed by the issuer. A *verifiable presentation* is a holder-signed envelope bundling one or more credentials (or derived subsets of them); presentation, not the credential itself, is what flows to verifiers. That separation is what lets a holder prove "I am over 18" without handing over the full birth-date credential.

A minimal VC (v2.0 uses `validFrom`/`validUntil`; v1.0 used `issuanceDate`):

```json
{
  "@context": [
    "https://www.w3.org/ns/credentials/v2",
    "https://www.w3.org/ns/credentials/examples/v2"
  ],
  "type": ["VerifiableCredential", "ExampleDegreeCredential"],
  "issuer": "did:example:university-123",
  "validFrom": "2025-01-15T09:00:00Z",
  "credentialSubject": {
    "id": "did:example:holder-777",
    "degree": { "type": "BachelorDegree", "name": "BSc Computer Science" }
  },
  "proof": {
    "type": "DataIntegrityProof",
    "cryptosuite": "eddsa-rdfc-2022",
    "verificationMethod": "did:example:university-123#key-1",
    "proofPurpose": "assertionMethod",
    "proofValue": "z58DAdFfa9SkqZMVPxAQp..."
  }
}
```

The model spec is deliberately thin: `@context` for vocabulary, `type` for semantics, `issuer`, dates, `credentialSubject`, and an optional `proof`. Everything else (schemas, status, refresh) is an extension point. Verification is a pipeline, not a single check:

```text
                VC verification pipeline

  presented VC/VP
        |
        v
  [1] syntax + @context check ....... well-formed? known vocabularies?
        |
        v
  [2] resolve issuer DID ............ did:example:university-123
        |                             -> DID document -> verificationMethod
        v
  [3] verify cryptographic proof .... recompute hash over canonical form,
        |                             check signature by the referenced key
        v
  [4] temporal + schema checks ...... validFrom/validUntil window,
        |                             credentialSchema validation
        v
  [5] status check .................. bitstring status list: revoked?
        |
        v
  [6] application policy ............ holder == subject? issuer trusted
        |                             for this claim type? disclosures OK?
        v
  accept / reject
```

## W3C DID Core

A DID is a URI with three colon-separated parts plus an optional fragment: `did:method:method-specific-id`. The fragment selects a specific key inside the document (`...#key-1`). Resolving a DID yields a **DID document**: a JSON-LD object containing `verificationMethod` entries (public keys), purpose bindings such as `authentication` and `assertionMethod`, and `service` endpoints. The document is the seam of the whole stack -- proofs reference a verification method by DID URL, and verifiers resolve that URL to get the signing key. Nothing in the spec forces the backing registry to be a blockchain: it can be a ledger, DNS plus HTTPS, or the identifier itself (did:key).

| Method | Anchor / resolution | Trust base | Trade-offs |
|--------|---------------------|------------|------------|
| `did:key` | The identifier *is* the public key | None (self-certifying) | No rotation, no services; good for tests and ephemeral IDs |
| `did:web` | `did.json` at an HTTPS domain | DNS + TLS certificate authority | Easy ops, but re-centralizes trust in CAs and registrars |
| `did:ion` | Sidetree protocol operations batched to Bitcoin | Bitcoin anchoring + IPFS content addressing | Ledger-grade censorship resistance; heavier infrastructure |
| `did:pkh` | Blockchain account addresses (e.g. Ethereum) | The attached chain's consensus | Ties identity to chain keys; useful for wallet-native flows |

The obvious criticism is fragmentation. The DID spec registries list well over a hundred methods, each with its own resolver, and wallet/verifier support is a compatibility matrix rather than a guarantee. Two ecosystems that pick different methods cannot verify each other's credentials without resolvers for both. Defenders answer that the DID document output is uniform; critics answer that in practice did:web and did:key are absorbing most deployment traffic anyway, so the long tail is dead weight.

## Proofs, Selective Disclosure, and Zero Knowledge

How a proof binds to a DID, per the securing specifications:

| Spec | Mechanism | Status |
|------|-----------|--------|
| **Data Integrity** + cryptosuites (`eddsa-rdfc-2022`) | Canonicalize the document, sign the hash; `proof.type: DataIntegrityProof` | W3C Recommendation track |
| `Ed25519Signature2020` | Pre-Data-Integrity Ed25519 cryptosuite, still in wide wallet use | Legacy, deprecated by the above |
| **VC-JOSE-COSE** ("Securing Verifiable Credentials using JOSE and COSE") | Wrap credentials in JWT/SD-JWT or CWT payloads | W3C Working Draft |

Selective disclosure has two competing designs:

- **BBS signatures** (IRTF CFRG draft; also a W3C Data Integrity BBS cryptosuite draft): a pairing-based multi-message signature. The holder derives an *unlinkable* proof revealing a chosen subset of signed messages; presentations cannot be correlated back to the issuer's signature.
- **SD-JWT** (IETF OAuth working group draft): the issuer signs salted hashes of each claim; the holder discloses only the claims a verifier needs by attaching the salted values. Simpler and JOSE-native, but derived presentations remain linkable to the original signature.

Zero-knowledge predicates go further: prove `birthdate <= 2007-01-01` (or `salary >= X`) without revealing the input, using BBS-derived proofs or zk-SNARK circuits over committed claims. The SNARK machinery itself -- trusted setup or transparent setups, prover cost, succinct verification -- is the same technology that powers validity rollups; see [ZK Rollups](./zk-rollups.md).

## Status, Trust Registries, Governance

Revocation in the W3C stack is issuer-published state, not a phone-home API. The **Bitstring Status List** spec (W3C Recommendation) has the issuer publish a compressed bitstring (one bit per credential, RLE-compressed); each credential carries `statusListIndex` and `statusPurpose` (`revocation`, `suspension`), and verifiers fetch the list and check the bit. Privacy caveat: the issuer sees who fetches the list, and a per-credential bitstring can leak which index flipped when; defenders batch credentials into large shared lists to blunt timing correlation.

Two governance questions the cryptography cannot answer:

1. **Who is a legitimate issuer?** A valid signature proves the issuer's key, not the issuer's authority. Deployments solve this with trust registries: the EU's EBSI maintains a trusted-issuer registry; government schemes publish authoritative lists verifiers download.
2. **Who anchors the DID method?** The method specification is the governance document: did:web's registry is the DNS+CA system, did:ion's is Bitcoin plus the Sidetree protocol rules, a private ledger method's is its consortium.

Real deployments to know by name:

- **EU eIDAS 2.0 / EUDI Wallet**: Regulation (EU) 2024/1183 obliges member states to offer every citizen a European Digital Identity Wallet able to receive qualified electronic attestations of attributes; EBSI provides cross-border issuer registries and schema infrastructure. This is the largest mandated VC deployment.
- **Mobile driver licenses (ISO/IEC 18013-5)**: the adjacent, non-W3C standard. An mDL stores an ISO mdoc (CBOR-encoded, device-bound via the phone's secure enclave) and shares selected claims over BLE/NFC via a QR handshake. US states roll these out under AAMVA governance. The standards world is converging on SD-JWT/mdoc alignment for wallet interoperability.

## Limitations

An honest accounting:

- **Key recovery is the hard problem.** Losing a wallet loses credentials; sovereignty means self-custody. Mitigations (social recovery, MPC shares, custodial wallets backed by OIDC logins) each give back some centralization. A did:key without rotation keys is a usability trap.
- **Wallet security** replaces IdP security with consumer endpoint security: consent-screen phishing ("sign this presentation"), malware-stealed seed phrases, and confusing multi-party flows are the new attack surface.
- **Correlation leakage.** A long-lived `credentialSubject.id` used across verifiers is a tracking cookie with a signature. Pairwise DIDs and unlinkable proofs (BBS) help, but issuer signatures embedded in SD-JWT-style presentations remain linkable, and status-list fetches leak back to issuers.
- **Adoption economics.** Verifiers only accept credentials they legally or commercially must; issuers only issue where demand exists. This cold-start loop is why the first real wave is government-mandated (EU wallet, mDLs) rather than organic.

## Hands-On Demo: a Toy Credential with a Lamport Signature

Real wallets use Ed25519 or ECDSA via crypto libraries. To see the *verification pipeline* with pure stdlib Python, the demo below uses a Lamport one-time signature: the public key is the set of SHA-256 digests of 512 secret values (two per message bit); signing publishes the preimage for each bit of the message digest. Hash-based signatures have a second relevance: they rely only on preimage resistance, which is why the same family (as one-time schemes hardened into trees, e.g. SPHINCS+) anchors post-quantum signatures. Note what the demo makes obvious: the signature is 8 KiB for a 32-byte message -- the price of hash-based signing.

```python
import hashlib
import json

def h(b):
    return hashlib.sha256(b).digest()

def derive_keypairs(seed, n_bits=256):
    """Deterministically derive one Lamport key pair per message bit."""
    return [(
        h(seed + b"lamport" + i.to_bytes(4, "big") + b"\x00"),
        h(seed + b"lamport" + i.to_bytes(4, "big") + b"\x01"),
    ) for i in range(n_bits)]

def public_key(pairs):
    """Lamport public key: digests of every secret value (512 entries)."""
    return [(h(sk0), h(sk1)) for sk0, sk1 in pairs]

def sign(digest, pairs):
    """Publish one secret preimage per bit of the 32-byte digest."""
    return [pairs[i * 8 + bit][(byte >> (7 - bit)) & 1]
            for i, byte in enumerate(digest) for bit in range(8)]

def verify(digest, sig, pk):
    """Every published value must hash to the matching public digest."""
    for i, byte in enumerate(digest):
        for bit in range(8):
            idx = i * 8 + bit
            if h(sig[idx]) != pk[idx][(byte >> (7 - bit)) & 1]:
                return False
    return True

SEED = b"placement-prep demo seed"
pairs = derive_keypairs(SEED)
pk = public_key(pairs)
did_doc = {
    "@context": ["https://www.w3.org/ns/did/v1"],
    "id": "did:example:issuer-001",
    "verificationMethod": [{
        "id": "did:example:issuer-001#key-1",
        "type": "ToyLamportVerificationMethod",
        "publicKey": pk,
    }],
}

credential = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiableCredential", "ToyCourseCredential"],
    "issuer": "did:example:issuer-001",
    "issuanceDate": "2025-01-15T09:00:00Z",
    "credentialSubject": {"id": "did:example:holder-777",
                          "course": "verifiable-credentials",
                          "result": "pass"},
}

canonical = json.dumps(credential, sort_keys=True, separators=(",", ":"))
digest = h(canonical.encode())
sig = sign(digest, pairs)
vm = did_doc["verificationMethod"][0]
print("[1] issuer DID:", did_doc["id"])
print("[2] canonical credential:", canonical[:64], "...")
print("[3] sha256 digest:", digest.hex())
print("[4] Lamport signature:", len(sig), "x 32-byte values =", len(sig) * 32, "bytes")
print("[5] resolved", did_doc["id"], "-> verification method #key-1,", len(vm["publicKey"]) * 2, "public digests")
print("[6] verify signature against DID document:", "PASS" if verify(digest, sig, vm["publicKey"]) else "FAIL")

tampered = json.loads(canonical)
tampered["credentialSubject"]["result"] = "fail"
tampered_digest = h(json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode())
print("[7] tampered credential (result: pass->fail) + original signature:",
      "PASS" if verify(tampered_digest, sig, vm["publicKey"]) else "FAIL (expected)")

attacker_pk = public_key(derive_keypairs(b"attacker seed"))
print("[8] original credential verified with attacker key:", "PASS" if verify(digest, sig, attacker_pk) else "FAIL (expected)")
```

Run output (seeded, deterministic):

```text
[1] issuer DID: did:example:issuer-001
[2] canonical credential: {"@context":["https://www.w3.org/2018/credentials/v1"],"credenti ...
[3] sha256 digest: ab9036cde9e984babd56c7788e5f7886bb920af45fc0fbffb918b8f5594d408c
[4] Lamport signature: 256 x 32-byte values = 8192 bytes
[5] resolved did:example:issuer-001 -> verification method #key-1, 512 public digests
[6] verify signature against DID document: PASS
[7] tampered credential (result: pass->fail) + original signature: FAIL (expected)
[8] original credential verified with attacker key: FAIL (expected)
```

The steps mirror the pipeline diagram above: canonicalize, hash, sign, resolve the issuer DID, verify -- and the tamper tests fail exactly as a flipped claim must.

## Interview Questions

### Q1: Why does the VC model separate credential from presentation?

The credential is the issuer's signed claim set; the presentation is the holder's signed envelope that bundles or derives from credentials. This separation gives the holder agency (choose what to reveal, derive predicates), protects privacy (verifier sees a proof, not the source document), and keeps the issuer out of the loop at verification time -- no IdP phone-home, unlike OIDC token introspection or SAML artifact resolution.

### Q2: A verifier receives a VC with a valid signature. Is it trustworthy?

No. Validity proves the claims were signed by the issuer's key, nothing more. The verifier must still: resolve the DID and confirm the verification method is authorized for `assertionMethod`; check temporal validity (`validFrom`/`validUntil`); check status (revocation bitstring); and apply policy -- is this issuer *authorized* to assert this claim type (trust registry), and is the presenter the subject (holder binding)? Signature validity is step 3 of a six-step pipeline.

## Related Topics

- [Decentralized Infrastructure](./decentralized-infra.md) -- IPFS, DHTs, and the DID overview this page expands
- [ZK Rollups](./zk-rollups.md) -- SNARK/STARK machinery behind zero-knowledge predicates
- [JWT Internals](../security/jwt-internals.md) -- JOSE primitives SD-JWT and VC-JOSE-COSE build on
- [SAML 2.0](../security/saml.md) -- the IdP-centric assertion model VCs replace
- [X.509 Certificates](../cryptography/x509-certificates.md) -- the issuer-centric signed-claims ancestor

## References

1. W3C, "Verifiable Credentials Data Model v2.0" -- https://www.w3.org/TR/vc-data-model-2.0/
2. W3C, "Decentralized Identifiers (DIDs) v1.0" -- https://www.w3.org/TR/did-core/
3. W3C, "Bitstring Status List v1.0" -- https://www.w3.org/TR/vc-bitstring-status-list/
4. W3C, "Securing Verifiable Credentials using JOSE and COSE" -- https://www.w3.org/TR/vc-jose-cose/
5. W3C, "Data Integrity BBS Cryptosuites v1.0 (draft)" -- https://www.w3.org/TR/vc-di-bbs/
6. IETF OAuth WG, "OAuth Selective Disclosure for JWTs (SD-JWT)" -- https://github.com/oauth-wg/oauth-selective-disclosure-jwt
7. AAMVA, "Driver License and Identification Card Standards" (mDL / ISO 18013-5) -- https://www.aamva.org/identity/driver-license-and-identification-card-standards
8. European Commission, "European Digital Identity Wallet" -- https://digital-strategy.ec.europa.eu/en/policies/eu-digital-identity-wallet
