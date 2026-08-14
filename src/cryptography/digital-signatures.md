# Digital Signatures

Digital signatures provide **authenticity** (prove who sent a message), **integrity** (prove the message wasn't tampered with), and **non-repudiation** (the signer cannot deny having signed). They are a cornerstone of modern security, underpinning TLS certificates, code signing, software distribution, email authentication, and blockchain transactions.

## How Digital Signatures Work

A digital signature scheme consists of three algorithms:

1. **Key Generation:** Create a key pair (public + private). The private key is kept secret; the public key is distributed freely.
2. **Sign:** The signer hashes the message, then encrypts the hash with their private key. The result is the signature.
3. **Verify:** Anyone with the signer's public key can decrypt the signature to recover the hash, recompute the hash from the message, and compare them. If they match, the signature is valid.

```
Signing:
  Message → Hash Function → Hash → Sign(private_key) → Signature

Verification:
  Message → Hash Function → Hash ←——→ Decrypt(public_key, Signature) → Hash'
  Compare: Hash == Hash' → Valid | Invalid
```

**Critical point:** You don't encrypt the message—you encrypt (or operate on) the **hash** of the message. This ensures constant-time signature generation regardless of message size and binds the signature to the exact message content.

## Signature Algorithms

### RSA Signatures (RSASSA-PSS)

RSA signatures work by performing a private-key RSA operation on a padded hash of the message.

- **Use PSS padding** (Probabilistic Signature Scheme, RFC 8017)—it is provably secure in the random oracle model.
- **Avoid PKCS#1 v1.5 signatures** for new systems—PSS is strictly stronger.
- RSA signatures are large (key size in bytes) and slower to generate than ECC signatures.

| Key Size | Signature Size |
|----------|---------------|
| RSA-2048 | 256 bytes |
| RSA-4096 | 512 bytes |

### ECDSA (Elliptic Curve Digital Signature Algorithm)

ECDSA produces signatures using elliptic curve mathematics. It is widely deployed but has subtle pitfalls:

- **Requires a high-quality random nonce per signature.** A reused or predictable nonce leaks the private key (this is exactly what happened with the PlayStation 3 ECDSA key leak).
- Signature size depends on the curve but is typically 2× the field element size (e.g., ~72 bytes for P-256).

| Curve | Signature Size | Notes |
|-------|---------------|-------|
| P-256 (secp256r1) | ~72 bytes | Most common; used in TLS, JWT (ES256) |
| P-384 | ~104 bytes | Higher security |
| secp256k1 | ~72 bytes | Bitcoin/Ethereum |

### Ed25519 (Edwards-Curve Digital Signature)

Ed25519 (RFC 8032) is a modern signature scheme based on Curve25519 in twisted Edwards form. It addresses ECDSA's nonce-reuse problem by using a **deterministic nonce** derived from the message and private key via HMAC-SHA512.

| Property | Ed25519 | ECDSA (P-256) |
|----------|---------|--------------|
| **Signature size** | 64 bytes | ~72 bytes |
| **Public key size** | 32 bytes | 64 bytes |
| **Nonces** | Deterministic (safe) | Random (dangerous if reused) |
| **Side-channel resistance** | Constant-time | Varies by implementation |
| **Speed (sign)** | Very fast | Moderate |
| **Speed (verify)** | Very fast | Moderate |

**Ed25519 is the recommended choice for new systems** unless you need NIST P-curve compliance for regulatory reasons.

## Certificate Signing

A TLS certificate is essentially a digital signature binding a public key to an identity (domain name, organization). A Certificate Authority (CA) signs the certificate using its private key. The CA's public key is distributed via the root certificate in trust stores.

```
Certificate = {
    Subject: "api.example.com",
    Public Key: <server's public key>,
    Validity: 2024-01-01 to 2025-01-01,
    Issuer: "Let's Encrypt Authority X3",
    ...
}
Signed by: Let's Encrypt's private key
```

Anyone who trusts the CA can verify the certificate's signature, establishing that the CA vouches for the binding between the domain and the public key.

## Certificate Transparency (CT)

Certificate Transparency (RFC 6962) is a public, append-only log of all publicly issued TLS certificates. It solves two problems:

1. **Detecting mis-issued certificates:** If a CA issues a certificate for your domain without your knowledge, it appears in the CT log and you can detect it.
2. **Surveillance of CA behavior:** Anyone can audit what certificates a CA has issued, making it harder for CAs to act maliciously.

Modern browsers **require** CT log inclusion for publicly trusted certificates. Google Chrome requires at least two SCTs (Signed Certificate Timestamps) from different CT logs.

## Code Signing

Code signing uses digital signatures to establish the provenance and integrity of software:

- **Executables and binaries** (Windows Authenticode, macOS code signing)
- **Container images** (cosign, Notary, OCI image signatures)
- **Packages and artifacts** (npm packages, Python wheels, Maven JARs)
- **Firmware updates** (secure boot chains)

**Software supply chain security** has become critical. Tools like **Sigstore** (used by cosign) provide a free, transparent code signing infrastructure that stores signatures in a Merkle tree backed by a CT log.

**Key principle:** The private signing key must be tightly controlled. Many supply chain attacks (SolarWinds, Codecov) involved compromised signing keys. Best practices include:

- Use hardware security modules (HSMs) for signing keys
- Implement signing workflows with multiple approvers
- Use short-lived signing certificates
- Verify signatures during CI/CD pipelines

## References

- RFC 8032 — Edwards-Curve Digital Signature Algorithm (EdDSA)
- RFC 8017 — PKCS#1 v2.2 (RSA PSS)
- RFC 6962 — Certificate Transparency
- NIST FIPS 186-5 — Digital Signature Standard (DSS)
- NIST SP 800-186 — Elliptic curve cryptography recommendations
- OWASP Secure Coding Practices

## Interview Questions

1. **How does a digital signature provide authenticity, integrity, and non-repudiation?**
2. **Why does Ed25519 use deterministic nonces? What problem does this solve?**
3. **What is the difference between RSA-PSS and PKCS#1 v1.5 signatures? Which should you use?**
4. **Explain the relationship between TLS certificates and digital signatures.**
5. **What is Certificate Transparency? Why is it important?**
6. **How would you verify the signature of a downloaded software package?**
7. **What are the risks of reusing a nonce in ECDSA?**
8. **How does code signing work? What are the security considerations for managing signing keys?**
9. **Compare RSA-2048, ECDSA P-256, and Ed25519 for signing API responses. Which would you choose and why?**
10. **What is a supply chain attack? How do digital signatures help prevent them?**
