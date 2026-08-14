# Cryptographic Hashing

Cryptographic hash functions are fundamental primitives that map arbitrary-length input to a fixed-length output (the digest or hash). They are the workhorses of data integrity, password storage, digital signatures, and message authentication. Unlike encryption, hashing is a **one-way** operation—you cannot recover the input from the hash.

## Properties of Cryptographic Hash Functions

A secure cryptographic hash function must satisfy three properties:

| Property | Definition | Example |
|----------|-----------|---------|
| **Preimage resistance (one-wayness)** | Given a hash *h*, it is computationally infeasible to find any message *m* such that *H(m) = h* | Given a SHA-256 output, you cannot find a string that produces it |
| **Second preimage resistance** | Given a message *m₁*, it is infeasible to find a different message *m₂* such that *H(m₁) = H(m₂)* | An attacker cannot substitute a modified file that hashes to the same value |
| **Collision resistance** | It is infeasible to find any two distinct messages *m₁ ≠ m₂* such that *H(m₁) = H(m₂)* | Two different documents should never produce the same hash |

**Note the difference:** Second preimage resistance is about a *specific* message; collision resistance is about *any* pair of messages. Collision resistance implies second preimage resistance, which implies preimage resistance.

Additional desirable properties include the **avalanche effect** (a small change in input produces a radically different output) and **pseudorandomness** (the output is indistinguishable from random).

## SHA-256 and SHA-3

| Algorithm | Output Size | Block Size | Speed | Status |
|-----------|-------------|-----------|-------|--------|
| **SHA-1** | 160 bits | 512 bits | Fast | **Broken** — collision found (SHAttered, 2017). Never use. |
| **SHA-256** | 256 bits | 512 bits | Fast | Secure; widely used. Standard in TLS, code signing, blockchain. |
| **SHA-384** | 384 bits | 1024 bits | Fast | Secure; used in some government applications |
| **SHA-512** | 512 bits | 1024 bits | Fast | Secure; faster than SHA-256 on 64-bit platforms |
| **SHA-3-256** | 256 bits | 1088 bits (Keccak) | Slower | Secure; structurally different from SHA-2 (sponge construction) |

**SHA-256** is the de facto standard and is used virtually everywhere. **SHA-3** (based on the Keccak algorithm, winner of the NIST SHA-3 competition) uses a fundamentally different construction (sponge vs. Merkle-Damgård) and provides a defense-in-depth if a structural weakness is found in SHA-2.

**When to use SHA-3 over SHA-256:** When you need algorithmic diversity (defense-in-depth against a hypothetical SHA-2 break), or when using SHAKE (SHA-3 extendable output functions) for custom-length output.

## HMAC (Hash-based Message Authentication Code)

HMAC provides both integrity **and** authenticity by combining a hash function with a secret key. It is specified in RFC 2104.

### Construction

```
HMAC(K, m) = H((K' ⊕ opad) || H((K' ⊕ ipad) || m))
```

Where:
- *K* is the secret key (padded to block size if shorter, hashed if longer)
- *ipad* = 0x36 repeated (inner padding)
- *opad* = 0x5C repeated (outer padding)
- *||* is concatenation

### Use Cases

| Use Case | Example |
|----------|---------|
| API authentication | HMAC-SHA256 with API secret key to sign requests |
| JWT HS256 tokens | HMAC-SHA256 for symmetric JWT signing |
| Message integrity | Verifying webhook payloads (e.g., GitHub webhooks) |
| MAC for encrypted messages | When using AES-CBC (encrypt-then-MAC) |

**Key insight:** HMAC is secure even if the underlying hash function has some weaknesses (proven security reduction). This makes it remarkably robust.

## Password Hashing

**Never use a plain hash function (SHA-256, MD5) for password storage.** These are too fast—an attacker with a GPU can compute billions of hashes per second. Password hashing requires **adaptive** functions that are deliberately slow and memory-hard to resist brute-force and rainbow-table attacks.

### Comparison Table

| Function | Adaptive? | Memory-Hard | GPU/ASIC Resistant | OWASP Recommendation |
|----------|-----------|------------|-------------------|----------------------|
| **bcrypt** | Yes (cost factor) | Partially (4 KB) | Moderate | Acceptable; widely supported |
| **scrypt** | Yes (cost + memory) | Yes (configurable) | Good | Acceptable |
| **Argon2id** | Yes (time + memory + parallelism) | Yes | Best | **Preferred** |
| **PBKDF2** | Yes (iterations) | No | Poor | Legacy only; avoid for new systems |

### Salt and Pepper

- **Salt:** A unique, random value generated per password. Stored alongside the hash in the database. Prevents rainbow table attacks and ensures identical passwords hash differently.
- **Pepper:** A secret value added to the password *before* hashing, stored separately from the database (e.g., in a config file or KMS). Protects against database compromise alone.

```python
# Salt and pepper workflow
salt = os.urandom(16)           # Per-user, stored in DB
pepper = load_from_kms()        # Global, stored separately
password_hash = argon2id(salt + password + pepper)
```

### Code Examples in Python

#### Password Hashing with Argon2id

```python
import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Create a hasher with OWASP-recommended parameters
ph = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,      # Number of parallel threads
    hash_len=32,        # Output hash length
    salt_len=16,        # Salt length
)

def hash_password(password: str) -> str:
    """Hash a password with Argon2id. Returns the full encoded hash (includes salt)."""
    return ph.hash(password)

def verify_password(password: str, hash_str: str) -> bool:
    """Verify a password against a stored hash. Returns True if valid."""
    try:
        return ph.verify(hash_str, password)
    except VerifyMismatchError:
        return False

# Usage
stored_hash = hash_password("my_secure_password_123!")
# $argon2id$v=19$m=65536,t=3,p=4$salt...$hash...

is_valid = verify_password("my_secure_password_123!", stored_hash)
# True
```

#### HMAC-SHA256 for Message Authentication

```python
import hmac
import hashlib

def create_hmac(key: bytes, message: bytes) -> bytes:
    """Create an HMAC-SHA256 tag for a message."""
    return hmac.new(key, message, hashlib.sha256).digest()

def verify_hmac(key: bytes, message: bytes, expected_tag: bytes) -> bool:
    """Verify an HMAC-SHA256 tag using constant-time comparison."""
    computed_tag = hmac.new(key, message, hashlib.sha256).digest()
    return hmac.compare_digest(computed_tag, expected_tag)

# Usage
secret_key = b"webhook_secret_key_abc123"
payload = b'{"event": "push", "repo": "my-project"}'
tag = create_hmac(secret_key, payload)
print(f"HMAC tag: {tag.hex()}")

# Verification (what the server does)
is_valid = verify_hmac(secret_key, payload, tag)
```

## Hash Length Extension Attacks

Merkle-Damgård hash functions (SHA-256, SHA-512, MD5) are vulnerable to **hash length extension attacks**. If an attacker knows *H(m)* and the length of *m*, they can compute *H(m || padding || extension)* without knowing *m*. This allows forging valid hashes for modified messages.

**Mitigation:** Use HMAC (which is not vulnerable to length extension) or switch to SHA-3 (sponge construction). This is why you should never do `HMAC(K, m)` as `H(K || m)`—always use the proper HMAC construction.

## References

- NIST FIPS 180-4 — SHA-3 Standard
- NIST SP 800-107 — Revised recommendations for hash functions
- NIST SP 800-63B — Password storage (Section 5.1.1.2)
- RFC 2104 — HMAC specification
- OWASP Password Storage Cheat Sheet

## Interview Questions

1. **What are the three properties of a cryptographic hash function? Explain each with an example.**
2. **Why should you never use SHA-1? What happened to it?**
3. **What is the difference between SHA-256 and SHA-3? When would you use one over the other?**
4. **Why is HMAC-SHA256 preferred over SHA-256 for message authentication?**
5. **Why should you never store passwords as plain SHA-256 hashes?**
6. **Compare bcrypt, scrypt, and Argon2. Which does OWASP recommend and why?**
7. **What is a salt? What problem does it solve? What problem does it *not* solve?**
8. **Explain the hash length extension attack. Which hash families are vulnerable?**
9. **What is the difference between a salt and a pepper? Why might you use both?**
10. **How would you implement a secure password reset mechanism?**
