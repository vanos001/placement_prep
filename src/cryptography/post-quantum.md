# Post-Quantum Cryptography

Quantum computing poses an existential threat to the public-key cryptography that secures most of the internet. While large-scale quantum computers capable of breaking current encryption do not yet exist, the principle of **"harvest now, decrypt later"** means that data encrypted today with vulnerable algorithms can be stored and decrypted in the future. Organizations handling long-lived sensitive data must start preparing now.

## The Quantum Threat

Two quantum algorithms threaten specific classes of cryptographic primitives:

| Quantum Algorithm | Threatens | Impact |
|-------------------|-----------|--------|
| **Shor's Algorithm** | RSA, ECDSA, ECDH, Diffie-Hellman | Can factor integers and compute discrete logarithms in polynomial time. Breaks all widely used public-key crypto. |
| **Grover's Algorithm** | Symmetric encryption (AES), Hash functions (SHA-256) | Provides quadratic speedup for brute-force search. AES-128 has effective security of 64 bits against quantum attack. |

### What survives?

| Algorithm Type | Quantum Resistance | Notes |
|---------------|-------------------|-------|
| **AES-256** | Yes (128-bit effective security) | Double key size to maintain security level |
| **SHA-256/SHA-3** | Yes (128-bit collision resistance) | Adequate; SHA-384/512 for higher margins |
| **ChaCha20** | Yes | Double key size for equivalent security |
| **HMAC** | Yes | Depends on underlying hash function |
| **Argon2id** | Yes | Increase parameters to compensate for Grover's speedup |
| **RSA** | **Broken** | Shor's algorithm factors n efficiently |
| **ECC (all curves)** | **Broken** | Shor's algorithm solves ECDLP |
| **DHE/ECDHE** | **Broken** | Shor's algorithm solves the discrete log problem |

**Key takeaway:** Symmetric crypto and hash functions survive with increased parameters. Public-key crypto is fundamentally broken by Shor's algorithm.

## Post-Quantum Algorithm Families

Post-quantum cryptography (PQC) relies on mathematical problems that are believed to be hard for both classical and quantum computers.

### Lattice-Based Cryptography

Based on the hardness of lattice problems (shortest vector problem, learning with errors). These are the most mature and practical PQC candidates.

- **ML-KEM (Module-Lattice-Based Key Encapsulation Mechanism):** Formerly known as CRYSTALS-Kyber. Standardized by NIST in FIPS 203 (2024). Provides key encapsulation for key exchange.
- **ML-DSA (Module-Lattice-Based Digital Signature Algorithm):** Formerly CRYSTALS-Dilithium. Standardized by NIST in FIPS 204 (2024). Provides digital signatures.

**Performance:** ML-KEM is fast—key generation, encapsulation, and decapsulation are competitive with ECDH on modern hardware. Key sizes are larger than ECC (~1 KB vs. ~64 bytes for public keys).

### Hash-Based Cryptography

Based on the security of hash functions. Only viable for signatures (not encryption). The security relies solely on collision resistance of the underlying hash.

- **SLH-DSA (Stateless Hash-Based Digital Signature Algorithm):** Formerly SPHINCS+. Standardized by NIST in FIPS 205 (2024). Stateless, meaning no need to track state across signatures. Larger signatures (~40 KB) but provides a conservative, well-understood security foundation.

**Use case:** Situations where algorithmic diversity is valued—SLH-DSA's security relies only on hash functions, not on lattice problems.

### Code-Based Cryptography

Based on the difficulty of decoding random linear codes (the syndrome decoding problem). The most well-studied PQC problem with a 40+ year research history.

- **Classic McEliece:** A KEM based on binary Goppa codes. Very large public keys (~1 MB) but small ciphertexts. Not selected as a NIST standard (due to key size) but recommended as a backup.

### Multivariate Polynomial Cryptography

Based on the difficulty of solving systems of multivariate quadratic equations over finite fields. Not selected by NIST for standardization (concerns about parameter sizes and maturity) but remains an active research area.

## NIST PQC Standardization

In August 2024, NIST finalized three post-quantum cryptographic standards:

| Standard | Former Name | Type | FIPS |
|----------|------------|------|------|
| **ML-KEM** | CRYSTALS-Kyber | Key Encapsulation | FIPS 203 |
| **ML-DSA** | CRYSTALS-Dilithium | Digital Signature | FIPS 204 |
| **SLH-DSA** | SPHINCS+ | Digital Signature | FIPS 205 |

Additionally, NIST is running a **fourth round** to standardize additional KEM algorithms (e.g., BIKE, HQC, ML-KEM variants) for diversity.

### Migration Strategy

The recommended approach is **hybrid cryptography**—combining classical and post-quantum algorithms in a single handshake. This provides defense-in-depth: the connection is secure if either algorithm remains unbroken.

```
TLS 1.3 hybrid handshake:
  Classical: ECDHE (X25519) — secure today, vulnerable to quantum
  Post-quantum: ML-KEM-768 — quantum-resistant

  Shared secret = H(ECDHE_secret || ML-KEM_secret)
```

Google, Cloudflare, Apple, and other major players have already deployed hybrid key exchange in production (e.g., Chrome uses X25519+ML-KEM-768 for Google services).

### Migration Checklist

1. **Inventory cryptographic assets:** Catalog all algorithms, key types, and certificate chains in use
2. **Assess data sensitivity:** Identify data with long confidentiality requirements (medical records, state secrets, IP)
3. **Enable hybrid key exchange:** Deploy ML-KEM alongside classical ECDHE in TLS (many libraries now support this)
4. **Plan certificate migration:** Larger key sizes mean larger certificates and handshakes; assess infrastructure impact
5. **Test with PQC libraries:** Use `liboqs`, `oqs-provider` for OpenSSL, or the `cryptography` library's PQ support
6. **Monitor NIST guidance:** Standards are evolving; the landscape will mature through 2025-2030

### Code Example: ML-KEM Key Encapsulation (Conceptual)

```python
# Using the OQS (Open Quantum Safe) Python wrapper
# pip install liboqs-python

from oqs import KeyEncapsulation

# Key generation (server side)
kem = KeyEncapsulation("ML-KEM-768")
public_key = kem.generate_keypair()

# Encapsulation (client side, using server's public key)
kem_client = KeyEncapsulation("ML-KEM-768")
ciphertext, shared_secret_client = kem_client.encap_secret(public_key)

# Decapsulation (server side, using its private key)
shared_secret_server = kem.decap_secret(ciphertext)

assert shared_secret_client == shared_secret_server
# Both sides now share a secret that is quantum-resistant
```

## References

- NIST FIPS 203 — ML-KEM (Module-Lattice-Based Key Encapsulation)
- NIST FIPS 204 — ML-DSA (Module-Lattice-Based Digital Signature)
- NIST FIPS 205 — SLH-DSA (Stateless Hash-Based Digital Signature)
- NIST Post-Quantum Cryptography Standardization — https://csrc.nist.gov/projects/post-quantum-cryptography
- NSA CNSA 2.0 Suite — Quantum-resistant algorithm requirements
- Open Quantum Safe (OQS) — https://openquantumsafe.org/

## Interview Questions

1. **What quantum algorithm threatens RSA and ECC? Explain the threat at a high level.**
2. **Why does AES-256 survive quantum attacks while RSA-2048 does not?**
3. **What is "harvest now, decrypt later"? Why does it matter for data encrypted today?**
4. **What are the three NIST post-quantum cryptographic standards? What does each provide?**
5. **What is hybrid cryptography? Why is it recommended for the transition period?**
6. **How would you plan a migration from classical to post-quantum cryptography for a production system?**
7. **What is the performance impact of post-quantum algorithms compared to classical ones?**
8. **Why are lattice-based algorithms the primary NIST standard for KEM, while hash-based algorithms are used for signatures?**
9. **What is Grover's algorithm's impact on symmetric encryption?**
10. **How soon do organizations need to migrate to post-quantum cryptography? What factors affect the timeline?**
