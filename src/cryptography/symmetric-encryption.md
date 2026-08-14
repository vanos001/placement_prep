# Symmetric Encryption

Symmetric encryption uses a single shared secret key for both encryption and decryption. It is the foundation of bulk data encryption and is used everywhere—TLS record layers, encrypted databases, full-disk encryption, and VPN tunnels. The Advanced Encryption Standard (AES), selected by NIST in 2001 (FIPS 197), is the dominant algorithm today.

## Block Ciphers vs. Stream Ciphers

| Property | Block Cipher | Stream Cipher |
|----------|-------------|---------------|
| **Operation** | Encrypts fixed-size blocks (128 bits for AES) | Encrypts one byte/bit at a time |
| **Padding** | Required (PKCS#7) | Not required |
| **Parallelism** | Highly parallelizable (CTR mode) | Sequential (though ChaCha20 uses blocks internally) |
| **Examples** | AES, DES (deprecated), Camellia | ChaCha20, RC4 (broken, never use) |

**AES** operates on 128-bit blocks regardless of key size. **ChaCha20** (from the ChaCha family designed by Daniel Bernstein) is a stream cipher that operates on 512-bit blocks internally and is preferred when hardware AES acceleration is unavailable (e.g., mobile devices).

## AES Key Sizes and Modes

### Key Sizes

AES supports three key sizes, all operating on 128-bit blocks:

| Key Size | Security Level | Notes |
|----------|---------------|-------|
| AES-128 | 128-bit | Sufficient for most applications; recommended by NIST through 2030 |
| AES-192 | 192-bit | Rarely used; intermediate option |
| AES-256 | 256-bit | Highest security; required for classified data (NSA Suite B) |

### Modes of Operation

A block cipher alone cannot encrypt messages longer than one block. **Modes of operation** specify how to repeatedly apply the block cipher's single-block operation to securely transform data larger than a single block.

#### ECB (Electronic Codebook) — Never Use This

```
Block 1 → AES → Ciphertext 1
Block 2 → AES → Ciphertext 2
Block 3 → AES → Ciphertext 3
```

Each block is encrypted independently with the same key. Identical plaintext blocks produce identical ciphertext blocks, revealing patterns. The classic "ECB Penguin" demonstrates this: an encrypted image of a penguin still looks like a penguin. **ECB provides no semantic security and should never be used.**

#### CBC (Cipher Block Chaining)

```
IV ⊕ Plaintext 1 → AES → Ciphertext 1
Ciphertext 1 ⊕ Plaintext 2 → AES → Ciphertext 2
Ciphertext 2 ⊕ Plaintext 3 → AES → Ciphertext 3
```

Each plaintext block is XORed with the previous ciphertext block before encryption. An **Initialization Vector (IV)** is used for the first block. CBC provides semantic security *only* if the IV is unpredictable (random). However, CBC alone does **not** provide authentication—an attacker can flip bits in the ciphertext (bit-flipping attack). Always pair CBC with an HMAC (encrypt-then-MAC).

#### CTR (Counter Mode)

```
Counter 0 → AES → Keystream 0 ⊕ Plaintext 1 → Ciphertext 1
Counter 1 → AES → Keystream 1 ⊕ Plaintext 2 → Ciphertext 2
```

Converts the block cipher into a stream cipher by encrypting a counter and XORing the result with plaintext. **No padding needed**, fully parallelizable for encryption and decryption. However, CTR alone provides no authentication and the counter/nonce must **never repeat** with the same key.

#### GCM (Galois/Counter Mode) — Recommended

GCM combines CTR mode encryption with a GHASH authentication tag. It provides **confidentiality and integrity** (authenticated encryption with associated data, or AEAD). This is the mode used in TLS 1.3, IPsec, and most modern protocols.

**Critical requirements:**
- The 96-bit nonce must **never repeat** with the same key
- Generating >2^32 ciphertext blocks with a single key/nonce pair is catastrophic
- Most libraries handle nonce generation, but verify this

## IV/Nonce Requirements

| Mode | IV/Nonce Requirement |
|------|---------------------|
| ECB | None (which is one reason it's broken) |
| CBC | 128-bit IV, must be **unpredictable** (random, not sequential) |
| CTR | Nonce must **never repeat** with the same key |
| GCM | 96-bit nonce, must **never repeat** with the same key |

Reusing a nonce in CTR or GCM mode is catastrophic. In GCM, nonce reuse leaks the XOR of two plaintexts and allows forgery of the authentication tag. Generate nonces from a cryptographic random number generator (e.g., `os.urandom` or the `secrets` module in Python).

## Key Derivation

You should almost never use a raw password as an encryption key. Key derivation functions (KDFs) stretch low-entropy passwords into high-entropy keys while adding computational cost to slow brute-force attacks.

| KDF | Memory-Hard | Parallelism-Resistant | Status |
|-----|------------|----------------------|--------|
| **PBKDF2** | No | No | NIST approved (SP 800-132); widely supported but less resistant to GPU attacks |
| **scrypt** | Yes | Yes | Memory-hard; designed to resist ASIC/GPU attacks |
| **Argon2id** | Yes | Yes | Winner of Password Hashing Competition (PHC, 2015); recommended by OWASP |

**Argon2id** is the current best practice for password hashing and key derivation from passwords.

## Code Example: AES-GCM Encryption/Decryption in Python

```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# AES-GCM authenticated encryption
def encrypt(key: bytes, plaintext: bytes, associated_data: bytes = None) -> tuple:
    """
    Encrypts plaintext using AES-256-GCM.
    Returns (nonce, ciphertext_with_tag).
    """
    aesgcm = AESGCM(key)
    # Generate a 96-bit (12-byte) random nonce
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce, ciphertext

def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes = None) -> bytes:
    """
    Decrypts ciphertext using AES-256-GCM.
    Raises InvalidTag if authentication fails.
    """
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
    return plaintext

# Usage
key = AESGCM.generate_key(bit_length=256)  # 32-byte key
message = b"This is a confidential message"
aad = b"transaction:v1"  # Authenticated (but not encrypted) metadata

nonce, ciphertext = encrypt(key, message, aad)
print(f"Nonce: {nonce.hex()}")
print(f"Ciphertext: {ciphertext.hex()}")

plaintext = decrypt(key, nonce, ciphertext, aad)
print(f"Decrypted: {plaintext.decode()}")  # "This is a confidential message"
```

### Key Derivation from Password

```python
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.backends import default_backend

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derives a 256-bit AES key from a password using Argon2id."""
    kdf = Argon2id(
        salt=salt,
        length=32,
        time_cost=3,       # Number of iterations
        memory_cost=65536, # 64 MB
        parallelism=4,
        backend=default_backend(),
    )
    return kdf.derive(password.encode())

salt = os.urandom(16)
key = derive_key_from_password("my_strong_password_123!", salt)
```

## References

- NIST FIPS 197 — AES specification
- NIST SP 800-38D — GCM mode specification
- NIST SP 800-63B — Password storage guidelines
- RFC 5116 — Authenticated encryption with AES-CCM and AES-GCM
- OWASP Password Storage Cheat Sheet

## Interview Questions

1. **Why is ECB mode insecure? Give a concrete example of how it leaks information.**
2. **What is the difference between CBC and CTR mode? What are the trade-offs?**
3. **What happens if you reuse a nonce in AES-GCM? Why is this dangerous?**
4. **What is authenticated encryption (AEAD)? Why is it preferred over "encrypt-then-MAC"?**
5. **Compare PBKDF2, scrypt, and Argon2. When would you use each?**
6. **How would you encrypt a field in a database column? What mode and key derivation would you use?**
7. **What is the difference between a nonce and an IV?**
8. **Why is AES-128 considered sufficient when AES-256 exists?**
9. **A developer is using AES-CBC without authentication. What attacks are possible?**
10. **How would you implement key rotation for data encrypted at rest?**
