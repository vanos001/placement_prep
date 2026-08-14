# Asymmetric Encryption

Asymmetric (public-key) cryptography uses mathematically related key pairs: a **public key** that can be shared freely and a **private key** that must be kept secret. This solves the fundamental key distribution problem of symmetric encryption—two parties can communicate securely without ever sharing a secret in advance. However, asymmetric operations are 100–1000x slower than symmetric ones, so in practice, asymmetric crypto is used to exchange a symmetric key, which then encrypts the actual data.

## RSA (Rivest–Shamir–Adleman)

RSA, published in 1977, relies on the computational difficulty of factoring the product of two large prime numbers.

### Key Generation
1. Choose two large primes *p* and *q*
2. Compute *n = p × q* (the modulus)
3. Compute Euler's totient *φ(n) = (p-1)(q-1)*
4. Choose public exponent *e* (typically 65537)
5. Compute private exponent *d* ≡ *e⁻¹ mod φ(n)*

**Public key:** (n, e) — **Private key:** (n, d)

### Encryption, Decryption, and Signing

| Operation | Formula | Purpose |
|-----------|---------|---------|
| **Encryption** | *c = m^e mod n* | Anyone can encrypt with the public key |
| **Decryption** | *m = c^d mod n* | Only the private key holder can decrypt |
| **Signing** | *s = m^d mod n* | Private key holder signs a message |
| **Verification** | *m = s^e mod n* | Anyone can verify with the public key |

**Important:** RSA should never be used for raw encryption of arbitrary messages. In practice, RSA is used with **OAEP padding** (Optimal Asymmetric Encryption Padding, RFC 8017) for encryption and **PSS padding** (Probabilistic Signature Scheme) for signing. Never use textbook RSA (PKCS#1 v1.5 padding for encryption is also vulnerable to padding oracle attacks—prefer OAEP).

## Elliptic Curve Cryptography (ECC)

ECC is based on the algebraic structure of elliptic curves over finite fields. The core problem is the **Elliptic Curve Discrete Logarithm Problem (ECDLP)**: given points *P* and *Q* on a curve, find the scalar *k* such that *Q = kP*.

### Curves

| Curve | Domain | Key Size | Notes |
|-------|--------|----------|-------|
| **P-256 (secp256r1)** | NIST | 256 bits | Most widely deployed; used in TLS, JWT |
| **P-384** | NIST | 384 bits | Higher security level |
| **Curve25519** | CFRG | 256 bits | Designed by Daniel Bernstein; fast, constant-time |
| **Curve448** | CFRG | 448 bits | Higher-security variant of Curve25519 |
| **secp256k1** | Koblitz | 256 bits | Used by Bitcoin/Ethereum |

### ECDH (Elliptic Curve Diffie-Hellman)

ECDH allows two parties to derive a shared secret without ever transmitting it:

1. Alice generates key pair: private key *a*, public key *A = aG* (where *G* is the base point)
2. Bob generates key pair: private key *b*, public key *B = bG*
3. Alice computes shared secret: *S = aB = abG*
4. Bob computes shared secret: *S = bA = baG*

Both derive the same secret *S* without ever transmitting *a* or *b*.

### ECDSA (Elliptic Curve Digital Signature Algorithm)

ECDSA provides signatures using elliptic curves. It produces (r, s) signature components. ECDSA is used in TLS certificates, code signing, and Bitcoin.

### Ed25519 (Edwards-curve Digital Signature)

Ed25519 is a modern signature scheme based on Curve25519 in Edwards form. It offers several advantages over ECDSA:

- **Deterministic signatures** (no need for a random nonce—eliminates a class of catastrophic failures)
- **Faster** (uses Ed25519 operations that are simpler than ECDSA)
- **Smaller keys and signatures** (64-byte signatures vs. 72+ bytes for ECDSA P-256)
- **More resistant to side-channel attacks** (constant-time operations)

Ed25519 is used in OpenSSH, Signal Protocol, TLS 1.3 (when EdDSA cipher suites are negotiated), and many software supply chain tools (Sigstore, SLSA).

## Diffie-Hellman Key Exchange

The original Diffie-Hellman protocol (1976) operates in the multiplicative group of integers modulo a prime:

1. Alice and Bob agree on a large prime *p* and generator *g* (public parameters)
2. Alice picks random *a*, sends *A = g^a mod p*
3. Bob picks random *b*, sends *B = g^b mod p*
4. Alice computes *s = B^a mod p = g^(ab) mod p*
5. Bob computes *s = A^b mod p = g^(ba) mod p*

Both arrive at the same shared secret. An eavesdropper who sees *A*, *B*, *g*, and *p* cannot feasibly compute *g^(ab)*.

**Important:** Use **ephemeral** DH (DHE or ECDHE) for forward secrecy. Static DH does not provide forward secrecy—if the private key is compromised, all past communications can be decrypted.

## Key Size Comparison

| Security Level | RSA Key Size | ECC Key Size |
|---------------|-------------|-------------|
| 80-bit | 1024 bits (insecure) | 160 bits |
| 128-bit | 3072 bits | 256 bits (P-256) |
| 192-bit | 7680 bits | 384 bits (P-384) |
| 256-bit | 15360 bits | 512 bits (P-521) |

An ECC key of 256 bits provides security comparable to a 3072-bit RSA key. This dramatic size difference translates to faster computations, smaller certificates, and less bandwidth.

## Performance Comparison

| Operation | RSA-2048 | RSA-4096 | Ed25519 | P-256 (ECDH) |
|-----------|----------|---------|---------|--------------|
| Key Generation | Slow | Very Slow | Very Fast | Moderate |
| Signing | Moderate | Slow | Very Fast | Moderate |
| Verification | Fast | Moderate | Very Fast | Moderate |
| Key Size | 256 bytes | 512 bytes | 64 bytes | 64 bytes |
| Signature Size | 256 bytes | 512 bytes | 64 bytes | ~72 bytes |

ECC operations are significantly faster for signing and produce much smaller signatures. This makes ECC ideal for constrained environments (IoT, mobile) and high-throughput scenarios (TLS at scale).

## When to Use Which

| Scenario | Recommended |
|----------|------------|
| TLS key exchange | ECDHE with X25519 or P-256 |
| TLS signatures | ECDSA P-256 or Ed25519 |
| SSH keys | Ed25519 (not RSA) |
| JWT signing | Ed25519 or ECDSA P-256 (not HMAC with RSA) |
| Email encryption (S/MIME) | RSA (legacy compatibility) |
| Code signing | ECDSA or Ed25519 |
| Long-term identity keys | RSA-4096 or P-384 (for 20+ year validity) |

## Code Example: ECDH Key Exchange in Python

```python
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# --- Alice's side ---
alice_private = X25519PrivateKey.generate()
alice_public = alice_private.public_key()

# Alice sends her public key to Bob (serialize to bytes for transport)
alice_pub_bytes = alice_public.public_bytes(
    encoding=...,
    format=...,
)

# --- Bob's side ---
bob_private = X25519PrivateKey.generate()
bob_public = bob_private.public_key()

# Bob sends his public key to Alice
bob_pub_bytes = bob_public.public_bytes(
    encoding=...,
    format=...,
)

# --- Both sides derive the same shared secret ---
# Alice's computation:
shared_secret_alice = alice_private.exchange(bob_public)
# Bob's computation:
shared_secret_bob = bob_private.exchange(alice_public)

assert shared_secret_alice == shared_secret_bob

# Derive a usable key from the shared secret using HKDF
def derive_key(shared_secret: bytes, context: bytes = None) -> bytes:
    """Derives a 256-bit AES key using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=context or b"handshake-key",
    )
    return hkdf.derive(shared_secret)

aes_key_alice = derive_key(shared_secret_alice, b"session-key:v1")
aes_key_bob = derive_key(shared_secret_bob, b"session-key:v1")
assert aes_key_alice == aes_key_bob

print(f"Shared AES key: {aes_key_alice.hex()}")
# Both Alice and Bob now have the same 256-bit AES key
# and can use it for symmetric encryption (e.g., AES-GCM)
```

## References

- NIST SP 800-56B — RSA cryptography recommendations
- NIST SP 800-186 — Recommendations for elliptic curve cryptography
- RFC 7748 — Elliptic Curves for Security (X25519, X448)
- RFC 8032 — Edwards-Curve Digital Signature Algorithm (EdDSA)
- RFC 8017 — PKCS#1 v2.2 (RSA OAEP/PSS)

## Interview Questions

1. **How does RSA encryption work conceptually? What is the relationship between the public and private keys?**
2. **Why are ECC keys much shorter than RSA keys for equivalent security?**
3. **What is forward secrecy? How does ECDHE provide it?**
4. **What are the advantages of Ed25519 over ECDSA?**
5. **Why should you never use RSA without padding (textbook RSA)?**
6. **Explain the Diffie-Hellman key exchange. What information is public and what is private?**
7. **In TLS 1.3, why is RSA key exchange no longer supported?**
8. **When would you choose RSA over ECC in a real-world system?**
9. **What happens if two parties reuse the same DH parameters with the same keys?**
10. **How would you design a key rotation strategy for asymmetric keys?**
