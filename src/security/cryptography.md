# Cryptography

## Overview

Cryptography is the practice and study of techniques for securing communication and data in the presence of adversaries. It forms the backbone of modern security, enabling confidentiality, integrity, authentication, and non-repudiation.

```
┌─────────────────────────────────────────────┐
│              Cryptography                    │
├─────────────┬───────────────┬───────────────┤
│ Symmetric   │  Asymmetric   │    Hashing    │
│ Encryption  │  Encryption   │               │
├─────────────┼───────────────┼───────────────┤
│ AES         │ RSA           │ SHA-256       │
│ ChaCha20    │ ECC           │ SHA-3         │
│ DES (broken)│ Diffie-Hellman│ bcrypt        │
└─────────────┴───────────────┴───────────────┘
```

## Symmetric Encryption

Same key encrypts and decrypts. Fast, but requires secure key distribution.

```
┌──────────┐                    ┌──────────┐
│  Sender  │  Shared Secret Key │ Receiver │
│          │◀──────────────────▶│          │
│          │                    │          │
│ Plaintext│  Key + Algorithm   │Ciphertext│
│    │     │                    │    │     │
│    ▼     │                    │    ▼     │
│ Encrypt  │                    │ Decrypt  │
│    │     │                    │    │     │
│    ▼     │                    │    ▼     │
│Ciphertext│ ──channel──▶      │Plaintext │
└──────────┘                    └──────────┘
```

### AES (Advanced Encryption Standard)

AES is the standard symmetric encryption algorithm, operating on 128-bit blocks with 128, 192, or 256-bit keys.

#### AES Modes of Operation

```
┌─────────────────────────────────────────────┐
│              AES Modes                       │
├──────────┬──────────────────────────────────┤
│ ECB      │ Electronic Codebook              │
│          │ Each block encrypted independently│
│          │ ⚠️ Identical blocks → identical   │
│          │    ciphertext (INSECURE)          │
├──────────┼──────────────────────────────────┤
│ CBC      │ Cipher Block Chaining            │
│          │ Each block XORed with previous   │
│          │ Requires IV, sequential           │
├──────────┼──────────────────────────────────┤
│ CTR      │ Counter Mode                     │
│          │ Turns AES into stream cipher     │
│          │ Parallelizable, random access    │
├──────────┼──────────────────────────────────┤
│ GCM      │ Galois/Counter Mode              │
│          │ CTR + authentication tag         │
│          │ ✅ Authenticated encryption       │
│          │ ✅ Recommended for most uses      │
└──────────┴──────────────────────────────────┘
```

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_aes_gcm(key, plaintext, associated_data=None):
    """Encrypt using AES-256-GCM (recommended)."""
    # Generate random 96-bit nonce (never reuse with same key!)
    nonce = os.urandom(12)
    
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    
    return nonce + ciphertext  # Prepend nonce for storage

def decrypt_aes_gcm(key, nonce_and_ciphertext, associated_data=None):
    """Decrypt using AES-256-GCM."""
    nonce = nonce_and_ciphertext[:12]
    ciphertext = nonce_and_ciphertext[12:]
    
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)

# Usage
key = AESGCM.generate_key(bit_length=256)
plaintext = b"Sensitive data to encrypt"
aad = b"context-info"  # Associated authenticated data

encrypted = encrypt_aes_gcm(key, plaintext, aad)
decrypted = decrypt_aes_gcm(key, encrypted, aad)
assert decrypted == plaintext
```

**Why GCM over CBC?**
- GCM provides authenticated encryption (confidentiality + integrity)
- CBC only provides confidentiality; needs separate MAC (HMAC)
- GCM is parallelizable; CBC is not for encryption
- CBC is vulnerable to padding oracle attacks if not implemented carefully

## Asymmetric Encryption

Uses a key pair: public key encrypts, private key decrypts. Solves key distribution problem.

```
┌──────────┐                    ┌──────────┐
│  Sender  │  Receiver's Public │ Receiver │
│          │       Key          │          │
│          │◀───────────────────│          │
│          │                    │          │
│ Plaintext│  Public Key        │Ciphertext│
│    │     │                    │    │     │
│    ▼     │                    │    ▼     │
│ Encrypt  │                    │ Decrypt  │
│    │     │  (Private Key)     │    │     │
│    ▼     │                    │    ▼     │
│Ciphertext│ ──channel──▶      │Plaintext │
└──────────┘                    └──────────┘
```

### RSA

RSA is based on the difficulty of factoring large prime numbers.

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# Generate RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048  # Minimum recommended: 2048 bits
)

public_key = private_key.public_key()

# Encrypt with public key
def rsa_encrypt(public_key, plaintext):
    ciphertext = public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

# Decrypt with private key
def rsa_decrypt(private_key, ciphertext):
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext

# Usage
message = b"Hello, RSA!"
encrypted = rsa_encrypt(public_key, message)
decrypted = rsa_decrypt(private_key, encrypted)

# Serialize keys
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.BestAvailableEncryption(b"password")
)

public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
```

### ECC (Elliptic Curve Cryptography)

ECC provides equivalent security to RSA with smaller key sizes.

```
Key Size Comparison for Equivalent Security:
┌───────────┬──────────┬──────────┐
│ RSA (bits)│ ECC (bits│ Ratio    │
├───────────┼──────────┼──────────┤
│ 1024      │ 160      │ 6.4x     │
│ 2048      │ 224      │ 9.1x     │
│ 3072      │ 256      │ 12x      │
│ 15360     │ 512      │ 30x      │
└───────────┴──────────┴──────────┘

ECC: Same security, much smaller keys → faster operations
```

```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

# Generate ECC key pair
private_key = ec.generate_private_key(ec.SECP256R1())  # P-256 curve
public_key = private_key.public_key()

# ECDH key exchange (derive shared secret)
def ecdh_exchange(private_key, peer_public_key):
    shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
    return shared_key  # Use this as symmetric key

# ECDSA signing
def ecdsa_sign(private_key, message):
    signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    return signature

def ecdsa_verify(public_key, message, signature):
    try:
        public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False
```

### Diffie-Hellman Key Exchange

Allows two parties to establish a shared secret over an insecure channel.

```
┌──────────┐                           ┌──────────┐
│  Alice    │                           │   Bob    │
│          │                           │          │
│ a = random│    Public: g, p          │ b = random│
│ A = g^a  │◀─────── g, p ───────────▶│ B = g^b  │
│   mod p  │                           │  mod p   │
│          │    Exchange A and B       │          │
│          │◀─────── B ───────────────▶│          │
│          │──────── A ──────────────▶│          │
│          │                           │          │
│ s = B^a  │    Both compute s         │ s = A^b  │
│  mod p   │    (same value!)          │  mod p   │
└──────────┘                           └──────────┘

Attacker sees: g, p, A, B
Cannot compute s without a or b (discrete log problem)
```

## Hashing

One-way functions that produce a fixed-size output (digest) from arbitrary input.

### Properties of Cryptographic Hashes

```
1. Deterministic: same input → same output
2. Fast to compute
3. Pre-image resistant: can't reverse hash to get input
4. Small change → completely different hash (avalanche effect)
5. Collision resistant: hard to find two inputs with same hash
```

### SHA-2 and SHA-3

```python
import hashlib

# SHA-256
data = b"Hello, World!"
sha256_hash = hashlib.sha256(data).hexdigest()
print(f"SHA-256: {sha256_hash}")
# Output: dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f

# SHA-512
sha512_hash = hashlib.sha512(data).hexdigest()

# SHA-3 (Keccak)
sha3_hash = hashlib.sha3_256(data).hexdigest()

# Different inputs produce completely different hashes
print(hashlib.sha256(b"Hello, World!").hexdigest())
print(hashlib.sha256(b"Hello, World?").hexdigest())
# Completely different outputs despite 1 character difference
```

### HMAC (Hash-based Message Authentication Code)

HMAC combines a hash function with a secret key for message authentication.

```
HMAC(K, m) = H((K ⊕ opad) || H((K ⊕ ipad) || m))

Where:
  K = secret key
  m = message
  ipad = 0x36 repeated
  opad = 0x5C repeated
  H = hash function (SHA-256, etc.)
```

```python
import hmac
import hashlib

def create_hmac(key, message):
    """Create HMAC-SHA256."""
    return hmac.new(key, message, hashlib.sha256).hexdigest()

def verify_hmac(key, message, expected_mac):
    """Verify HMAC using constant-time comparison."""
    computed_mac = hmac.new(key, message, hashlib.sha256).digest()
    return hmac.compare_digest(computed_mac, bytes.fromhex(expected_mac))

# Usage for API authentication
api_secret = b"my-api-secret-key"
request_body = b'{"amount": 100}'
signature = create_hmac(api_secret, request_body)

# Server verifies
is_valid = verify_hmac(api_secret, request_body, signature)
```

## Digital Signatures

Digital signatures provide authentication, integrity, and non-repudiation.

```
Signing:
┌──────────┐                    ┌──────────┐
│  Sender  │                    │          │
│          │   Message + Private Key      │
│          │                    │          │
│ Message ─┼──▶ Hash ──▶ Sign with        │
│          │     │     Private Key        │
│          │     │         │              │
│          │     ▼         ▼              │
│          │   Digest   Signature         │
└──────────┘   (sent together)

Verification:
┌──────────┐                    ┌──────────┐
│ Receiver │                    │          │
│          │   Message + Public Key + Sig  │
│          │                    │          │
│ Message ─┼──▶ Hash ──▶ Verify with       │
│          │     │     Public Key          │
│          │     │         │              │
│          │     ▼         ▼              │
│          │   Digest   Match? → Valid     │
└──────────┘
```

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

def sign_message(private_key, message):
    """Create a digital signature."""
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature

def verify_signature(public_key, message, signature):
    """Verify a digital signature."""
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False

# Usage
private_key = rsa.generate_private_key(65537, 2048)
public_key = private_key.public_key()

message = b"Transfer $1000 to Alice"
signature = sign_message(private_key, message)
is_valid = verify_signature(public_key, message, signature)
```

## Certificates and PKI

### Public Key Infrastructure (PKI)

```
┌─────────────────────────────────────────────┐
│              PKI Hierarchy                    │
│                                              │
│              ┌──────────┐                    │
│              │ Root CA  │ (self-signed)      │
│              └────┬─────┘                    │
│                   │                          │
│         ┌─────────┼─────────┐                │
│         ▼         ▼         ▼                │
│    ┌────────┐ ┌────────┐ ┌────────┐         │
│    │Interm. │ │Interm. │ │Interm. │         │
│    │  CA 1  │ │  CA 2  │ │  CA 3  │         │
│    └───┬────┘ └───┬────┘ └───┬────┘         │
│        │          │          │               │
│    ┌───┼───┐  ┌───┼───┐  ┌───┼───┐         │
│    ▼   ▼   ▼  ▼   ▼   ▼  ▼   ▼   ▼         │
│   C1   C2  C3 C4  C5  C6 C7  C8  C9         │
│  (End-entity certificates)                   │
└─────────────────────────────────────────────┘
```

### X.509 Certificate Contents

```
┌─────────────────────────────────────┐
│         X.509 Certificate            │
├─────────────────────────────────────┤
│ Version: v3                          │
│ Serial Number: 0x1234...            │
│ Issuer: CN=Let's Encrypt            │
│ Validity:                            │
│   Not Before: 2024-01-01            │
│   Not After: 2024-04-01             │
│ Subject: CN=example.com             │
│ Subject Public Key Info:            │
│   Algorithm: RSA 2048-bit           │
│   Public Key: 0xABCDEF...           │
│ Extensions:                          │
│   Subject Alt Name: example.com     │
│   Key Usage: Digital Signature      │
│ Signature Algorithm: SHA256-RSA     │
│ Signature: 0x987654...              │
└─────────────────────────────────────┘
```

## TLS Handshake

The TLS handshake establishes a secure connection between client and server.

```
┌──────────┐                           ┌──────────┐
│  Client  │                           │  Server  │
│          │                           │          │
│          │  1. ClientHello           │          │
│          │  (TLS version, ciphers,   │          │
│          │   random)                 │          │
│          │──────────────────────────▶│          │
│          │                           │          │
│          │  2. ServerHello           │          │
│          │  (chosen cipher, random)  │          │
│          │◀──────────────────────────│          │
│          │                           │          │
│          │  3. Certificate           │          │
│          │  (server's cert chain)    │          │
│          │◀──────────────────────────│          │
│          │                           │          │
│          │  4. Verify certificate    │          │
│          │  (check CA, validity)     │          │
│          │                           │          │
│          │  5. ClientKeyExchange     │          │
│          │  (pre-master secret,      │          │
│          │   encrypted with server's │          │
│          │   public key)             │          │
│          │──────────────────────────▶│          │
│          │                           │          │
│          │  Both derive session keys │          │
│          │  from pre-master secret   │          │
│          │                           │          │
│          │  6. ChangeCipherSpec      │          │
│          │──────────────────────────▶│          │
│          │                           │          │
│          │  7. Finished (encrypted)  │          │
│          │◀──────────────────────────│          │
│          │                           │          │
│          │  Encrypted communication  │          │
│          │◀─────────────────────────▶│          │
```

### Forward Secrecy

Forward secrecy ensures that compromise of long-term keys doesn't compromise past sessions.

```
Without Forward Secrecy:
  Attacker records traffic → later gets server's private key
  → can decrypt ALL past traffic

With Forward Secrecy (Ephemeral DH):
  Each session uses unique ephemeral keys
  Server private key compromise → can't decrypt past sessions
  (ephemeral keys are discarded after session)
```

**TLS 1.3** mandates forward secrecy by removing static RSA key exchange.

## Password Hashing

Regular cryptographic hashes (SHA-256) are **too fast** for password hashing. Password hashing functions are intentionally slow.

### bcrypt

```python
import bcrypt

def hash_password(password):
    """Hash password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)  # Cost factor (2^12 iterations)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

def verify_password(password, hashed):
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# bcrypt automatically handles salt (stored in hash)
# $2b$12$LJ3m4ys1bQ2R5vQ5vQ5vQeK8p1q2w3e4r5t6y7u8i9o0p1a2s3d4
#  $   $  $  $  salt (22 chars)      hash (31 chars)
#  |   |  |  |
#  |   |  |  algorithm id
#  |   |  cost factor (2^12 = 4096 iterations)
#  |   version
#  algorithm identifier
```

### scrypt

```python
import hashlib

def hash_password_scrypt(password, salt=None):
    """Hash password with scrypt."""
    if salt is None:
        salt = os.urandom(32)
    
    hashed = hashlib.scrypt(
        password.encode('utf-8'),
        salt=salt,
        n=2**14,  # CPU/memory cost (must be power of 2)
        r=8,      # Block size
        p=1       # Parallelization
    )
    return salt + hashed

# scrypt is memory-hard (resistant to GPU/ASIC attacks)
```

### Argon2 (Recommended)

```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,   # 64MB memory usage
    parallelism=4,       # Number of threads
    hash_len=32,         # Length of hash
    salt_len=16          # Length of salt
)

def hash_password_argon2(password):
    return ph.hash(password)

def verify_password_argon2(password, hash):
    try:
        return ph.verify(hash, password)
    except Exception:
        return False

# Rehash if parameters have changed
def check_and_rehash(password, hash):
    if ph.check_needs_rehash(hash):
        new_hash = ph.hash(password)
        return True, new_hash
    return False, hash
```

### Password Hashing Comparison

```
┌───────────┬──────────┬──────────┬──────────┬──────────┐
│ Algorithm │ CPU      │ Memory   │ GPU      │ Recommend│
│           │ Intensive│ Hard     │ Resist   │          │
├───────────┼──────────┼──────────┼──────────┼──────────┤
│ bcrypt    │ ✅       │ ❌       │ Moderate │ ✅ Good  │
│ scrypt    │ ✅       │ ✅       │ ✅       │ ✅ Good  │
│ Argon2id  │ ✅       │ ✅       │ ✅       │ ✅ Best  │
│ PBKDF2    │ ✅       │ ❌       │ ❌       │ ⚠️ OK   │
│ SHA-256   │ ❌       │ ❌       │ ❌       │ ❌ Never │
└───────────┴──────────┴──────────┴──────────┴──────────┘
```

## Key Derivation Functions (KDF)

```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

# PBKDF2 - Password-based key derivation
def derive_key_from_password(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,  # OWASP recommendation
    )
    return kdf.derive(password.encode())

# HKDF - Key derivation from high-entropy input
def derive_keys(master_secret, info, length=32):
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=None,
        info=info.encode(),
    )
    return hkdf.derive(master_secret)
```

## Interview Questions

### Q1: When would you use symmetric vs asymmetric encryption?

**Answer**: Symmetric encryption (AES) for bulk data encryption — it's fast and efficient. Asymmetric encryption (RSA/ECC) for key exchange, digital signatures, and encrypting small amounts of data. In practice, they're combined: asymmetric encrypts a symmetric key, symmetric encrypts the data (hybrid encryption). TLS uses this pattern.

### Q2: What is forward secrecy and why is it important?

**Answer**: Forward secrecy ensures that compromising the server's long-term private key doesn't allow decryption of past sessions. Each session uses ephemeral Diffie-Hellman keys that are discarded after use. TLS 1.3 mandates forward secrecy. Without it, an attacker who records encrypted traffic and later obtains the private key can decrypt everything.

### Q3: Why not use SHA-256 for password hashing?

**Answer**: SHA-256 is designed to be fast, making it vulnerable to brute-force and rainbow table attacks. A modern GPU can compute billions of SHA-256 hashes per second. Password hashing functions (bcrypt, scrypt, Argon2) are intentionally slow and memory-hard, making brute-force attacks impractical. They also incorporate salts automatically.

### Q4: Explain the difference between encryption, hashing, and encoding.

**Answer**: 
- **Encryption**: Two-way, requires a key, provides confidentiality (AES, RSA)
- **Hashing**: One-way, no key, provides integrity/fingerprinting (SHA-256, bcrypt)
- **Encoding**: Two-way, no key, data format conversion (Base64, UTF-8) — not security

### Q5: What is a nonce and why is it important?

**Answer**: A nonce (number used once) is a random value used once in cryptographic communication. It prevents replay attacks and ensures uniqueness. In AES-GCM, reusing a nonce with the same key completely breaks security. In TLS, nonces prevent replay of captured packets.

### Q6: How does HTTPS work?

**Answer**: HTTPS = HTTP + TLS. The TLS handshake: (1) Client and server agree on TLS version and cipher suite, (2) Server sends its certificate (containing public key), (3) Client verifies certificate against trusted CAs, (4) Key exchange (ECDHE) establishes shared secret, (5) Both derive session keys, (6) All further communication is encrypted with session keys. TLS 1.3 reduced this to 1-RTT.

### Q7: What is the difference between AES-CTR and AES-GCM?

**Answer**: Both use counter mode for encryption. AES-GCM adds Galois Message Authentication Code (GMAC), providing authenticated encryption — it detects tampering. AES-CTR alone only provides confidentiality. Always prefer GCM (or another AEAD mode) unless you have a specific reason not to.
