# Cryptography for Software Engineers

## Why Cryptography Matters

Every software engineer interacts with cryptography daily, whether they realize it or not. HTTPS connections, password storage, API authentication tokens, encrypted database fields, and secure cookie flags all rely on cryptographic primitives. Understanding *how* these work—and more importantly, *how they fail*—is essential for building secure systems.

A developer who doesn't understand cryptography is a developer who will accidentally store passwords in plaintext, use ECB mode for encryption, skip certificate validation, or roll their own crypto. These are not hypothetical failures—they are the root causes behind many of the most damaging data breaches in history.

## Core Pillars

### Symmetric Encryption

Symmetric encryption uses the **same key** for both encryption and decryption. It is fast and efficient, making it the workhorse for encrypting large volumes of data. The dominant modern algorithm is **AES** (Advanced Encryption Standard), standardized by NIST in FIPS 197.

| Algorithm | Key Sizes | Use Case |
|-----------|-----------|----------|
| AES-128 | 128 bits | General-purpose encryption |
| AES-256 | 256 bits | High-security applications, classified data |
| ChaCha20 | 256 bits | Mobile/streaming (no hardware AES support) |

### Asymmetric Encryption

Asymmetric (public-key) cryptography uses a **key pair**: a public key for encryption/verification and a private key for decryption/signing. It solves the key distribution problem inherent in symmetric encryption but is orders of magnitude slower.

| Algorithm | Use Case |
|-----------|----------|
| RSA | Key exchange, digital signatures, legacy systems |
| ECDSA | Code signing, TLS certificates |
| Ed25519 | Fast signatures, SSH, software supply chain |
| X25519 (ECDH) | Key exchange in TLS 1.3 |

### Hashing

Cryptographic hash functions produce a fixed-size digest from arbitrary input. They are deterministic, one-way, and collision-resistant. They are *not* encryption—you cannot reverse a hash to recover the original input.

Common uses include integrity verification, password storage (via adaptive hashing), digital signatures, and data deduplication.

### Key Management

Key management is often the hardest part of a cryptographic system. Securely generating, storing, rotating, and revoking keys is critical. Best practices include:

- **Use a KMS** (AWS KMS, HashiCorp Vault, Google Cloud KMS) for key storage
- **Rotate keys regularly**—compromise of one key should limit blast radius
- **Separate duties**—different keys for encryption, signing, and authentication
- **Never hardcode keys** in source code or configuration files

## The CIA Triad

Cryptography directly supports all three pillars of information security:

| CIA Pillar | Cryptographic Mechanism |
|------------|------------------------|
| **Confidentiality** | Encryption (symmetric & asymmetric) |
| **Integrity** | Hash functions, HMAC, digital signatures |
| **Availability** | Not directly provided, but integrity protects against DoS via data corruption |

A useful mnemonic: encryption hides the message, hashing proves the message hasn't changed, and signatures prove *who* sent the message.

## Threat Model Basics

Before choosing any cryptographic primitive, you must define your threat model:

1. **What are you protecting?** (Data at rest, data in transit, authentication credentials)
2. **Who is the adversary?** (Script kiddies, nation-states, insider threats)
3. **What are the attacker's capabilities?** (Network access, physical access, quantum computing)
4. **What is the expected lifetime of the data?** (Session tokens vs. medical records)

A common mistake is applying military-grade cryptography when the real vulnerability is an unpatched server or a phishing email. Cryptography is one layer of defense—never the only one.

## Standards and References

| Standard/Org | Relevance |
|--------------|-----------|
| **NIST FIPS 197** | AES specification |
| **NIST SP 800-132** | Key management guidelines |
| **NIST SP 800-63B** | Digital identity guidelines (password storage) |
| **RFC 5116** | AES-CCM and AES-GCM authenticated encryption |
| **RFC 8446** | TLS 1.3 protocol specification |
| **OWASP Cheat Sheet Series** | Practical cryptographic guidance for developers |
| **OWASP Top 10** | Most critical web application security risks |

## Interview Questions

1. **What is the difference between encryption and hashing? When would you use each?**
2. **Explain symmetric vs. asymmetric encryption. Why do we still need both?**
3. **What is the CIA triad? How does cryptography support each pillar?**
4. **What is a threat model? Walk me through how you'd create one for a web application.**
5. **Why should you never roll your own cryptographic algorithm?**
6. **What is key rotation, and why is it important?**
7. **How would you store user passwords securely in a database?**
8. **What is authenticated encryption, and why is it preferable to encryption without authentication?**
9. **Explain the difference between confidentiality, integrity, and authenticity.**
10. **A junior developer proposes storing API keys in a config file committed to the repository. How do you explain why this is a problem and suggest alternatives?**

## Next Steps

- [Symmetric Encryption](./symmetric-encryption.md) — AES, modes of operation, and authenticated encryption
- [Asymmetric Encryption](./asymmetric-encryption.md) — RSA, ECC, and key exchange
- [Hashing](./hashing.md) — Cryptographic hashes, HMAC, and password hashing
- [TLS](./tls.md) — Transport Layer Security deep dive
- [Digital Signatures](./digital-signatures.md) — Signing, verification, and certificates
- [PKI](./pki.md) — Public Key Infrastructure and certificate management
- [Practical Security](./practical-security.md) — Secure coding for web applications
- [Post-Quantum Cryptography](./post-quantum.md) — Preparing for the quantum threat
