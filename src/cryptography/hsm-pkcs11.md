# Hardware Security Modules (HSMs) and PKCS#11

A Hardware Security Module is a physically tamper-resistant compute device whose sole job is to generate, store, and use cryptographic keys without ever exposing the key material on a general-purpose bus. The defining property is *key custody*: a private key generated inside an HSM cannot be extracted in plaintext by any software on the host, even by the kernel or a root user. You can ask the HSM to sign, decrypt, or wrap data with that key, but you cannot ask it to hand you the raw bytes. Everything else — the form factor, the API, the certification level, the throughput — varies.

The interface that most production code actually talks to is **PKCS#11**, an OASIS standard first published by RSA Laboratories in 1995 (v1.0) and now at v3.1 (2023). It is the lingua franca of cryptographic tokens: the same C API drives a $50 YubiKey, a $5,000 PCIe card from Thales, a rack-mounted network HSM from Utimaco, and a cloud HSM in AWS. Understanding PKCS#11 lets you write portable crypto code that survives vendor churn.

## HSM Types and Form Factors

HSMs divide cleanly along two axes: *how they attach to the host* and *what certification level they target*.

### Attachment

```
  +-------------------------------------------------------------+
  |                       Host server                            |
  |                                                             |
  |   Network HSM            PCIe HSM           USB HSM         |
  |   (Thales Luna Network,  (Thales Luna PCIe,  (YubiHSM 2,    |
  |    Utimaco SecurityServer (Atos Trustway,     Nitrokey    |
  |    Se-Series)            Gemalto SafeNet)     HSM)         |
  |        |                       |                  |        |
  |        | TCP/TLS (PKCS#11      | PCIe driver      | USB    |
  |        | proxy or proprietary  | (vendor ioctl    | (CCID  |
  |        | client)               | + PKCS#11)        |  or    |
  |        |                       |                  | vendor)|
  +--------|-----------------------|------------------|--------+
           |                       |                  |
   +-------v--------+    +---------v------+   +-------v-----+
   | Rack-mounted    |    | PCIe card      |   | USB token   |
   | appliance,      |    | with onboard    |   | with smart   |
   | redundant PSUs, |    | crypto ASIC +   |   | card chip    |
   | tamper switches |    | battery-backed |   | (CCID/CTAP)  |
   +-----------------+    | RAM for keys   |   +--------------+
                          +----------------+
```

Network HSMs are appliances that live in a data center rack and accept PKCS#11 over a TCP/TLS proxy (or a vendor protocol like Thales's STC). The latency is in the hundreds of microseconds to low milliseconds, so they work well for asymmetric operations (RSA-2048 sign ~1-3 ms) but poorly for bulk symmetric encryption. PCIe HSMs sit directly on the host's bus and shave an order of magnitude off the latency, which matters for high-throughput TLS termination (say, a CDN edge that does 50,000 RSA-2048 handshakes per second). USB tokens like YubiHSM 2 are dirt cheap and aimed at developers and small deployments — they handle maybe 100-200 ECDSA operations per second but cost under $700.

### FIPS 140-3 certification

NIST FIPS 140-3 (which replaced FIPS 140-2 in 2017, with the transition formally closing in 2026) defines four security levels that an HSM may be validated against. The level is a procurement requirement for U.S. federal systems, and many financial regulators (PCI DSS, Common Criteria, eIDAS) point at it as well.

| Level | Physical | Logical | Identity | Typical target |
|-------|----------|---------|----------|----------------|
| 1     | No requirements | Software-only OK | None tested | Software libraries |
| 2     | Pick-resistant locks | Role-based auth | No hardware | Cheap tokens |
| 3     | Tamper-evident enclosure | Identity-based auth, M-of-N | Trusted path | PCIe HSMs, YubiHSM 2 |
| 4     | Tamper-*responsive* (zeroizes keys on intrusion), environmental monitoring | Dual control, trusted channel | Strong identity | Network HSMs (Thales, Utimaco) |

The critical distinction at Level 3 is that the keys must be wrapped with a key-encryption key when they leave the boundary, and at Level 4 the device actively detects physical or environmental tamper (drilling, voltage glitching, temperature) and *actively destroys* the key material. Level 4 devices have epoxy-encapsulated chips, mesh sensors on the PCB, and battery-backed RAM that is shorted on a tamper event.

## The PKCS#11 API

PKCS#11 exposes a C interface (`pkcs11.h` from OASIS) and a model that has aged remarkably well since 1995. The mental model is layered: a *slot* contains a *token*, a token holds *objects*, and operations on objects are parameterized by *mechanisms*. Every function name starts with `C_` (e.g., `C_OpenSession`, `C_GenerateKeyPair`, `C_Sign`).

```
   Application
       |
       v
+-----------------+
|  PKCS#11        |     slots   tokens   objects   mechanisms
|  shared library |     ------  -------  --------  -----------
|  (libsofthsm2,  |     [0][1]   [0]      CKO_DATA    CKM_RSA_PKCS
|   libyubihsm,   |                        CKO_CERT    CKM_RSA_PKCS_KEY_PAIR_GEN
|   libcknfast)   |                        CKO_SECRET_KEY   CKM_AES_CBC
|                 |                        CKO_PRIVATE_KEY  CKM_AES_GCM
|                 |                                     CKM_ECDSA
+-----------------+                                     CKM_SHA256
       |
       v
   HSM hardware (or software emulation, in the case of SoftHSM2)
```

### Slots and tokens

A **slot** is a logical port on the PKCS#11 module — typically one slot per physical reader or HSM partition. Each slot can hold a **token** — the cryptographic device present in that slot. A token has a label, a serial number, and (most importantly) a state. A token can be *not present* (smartcard removed), *present but uninitialized*, or *present and initialized* (with a SO pin and a user pin).

Tokens are typically *session-aware* — the HSM distinguishes between a "read-only public session" (you can read public objects like certificates) and a "read-write authenticated session" (you can do private-key operations, create objects, generate keys). A login is required to transition from public to authenticated state.

### Objects

Every piece of data inside a token is an object identified by a 64-bit handle. Each object has a class (`CKO_DATA`, `CKO_CERTIFICATE`, `CKO_PUBLIC_KEY`, `CKO_PRIVATE_KEY`, `CKO_SECRET_KEY`) and a set of attributes (`CKA_LABEL`, `CKA_VALUE`, `CKA_MODULUS`, etc.). Two attributes matter most for the threat model:

- `CKA_SENSITIVE` — the object's value cannot be read in plaintext from the token, ever, by any session. This is the property that makes the HSM an HSM. Once set true, it cannot be unset.
- `CKA_EXTRACTABLE` — the object can be wrapped (encrypted under a wrapping key) and exported from the token. Setting this to `false` means the key is *non-exportable* — the only way to migrate it is to never migrate it; you must use it where it lives.

Most production policies set `CKA_SENSITIVE = true` and `CKA_EXTRACTABLE = false` on the master key and rely on backups via a wrapping key (a separate key that is itself sensitive) for DR.

### Mechanisms

A mechanism (`CKM_*`) names a specific cryptographic algorithm and parameterization. PKCS#11 v3.1 defines over 400 of them — from `CKM_RSA_PKCS` (RSA with PKCS#1 v1.5 padding) to `CKM_AES_GCM`, `CKM_ECDSA`, `CKM_SHA512_HMAC`, `CKM_EDDSA`, and the various NIST SP 800-208 post-quantum candidates added in v3.1 (`CKM_ML_KEM_768`, `CKM_ML_DSA_65`).

The pattern for using a mechanism is always the same: initialize an operation (`C_SignInit`), feed data (`C_SignUpdate` or one-shot `C_Sign`), and finalize (`C_SignFinal`). Multi-step is for streaming; one-shot is for short messages.

## Key Generation Inside the HSM

The single most valuable property of an HSM is that keys can be born inside it. A typical RSA key pair generation:

```c
CK_OBJECT_HANDLE pubHandle = 0, privHandle = 0;
CK_BBOOL cktrue = CK_TRUE;
CK_ULONG bits = 2048;
CK_BYTE publicExponent[] = {0x01, 0x00, 0x01};   /* 65537 */
CK_ATTRIBUTE pubTemplate[] = {
    { CKA_MODULUS_BITS,    &bits,            sizeof(bits)       },
    { CKA_PUBLIC_EXPONENT, publicExponent,   sizeof(publicExponent) },
    { CKA_VERIFY,          &cktrue,          sizeof(cktrue)     },
    { CKA_EXTRACTABLE,    &ckfalse,         sizeof(ckfalse)    },
};
CK_ATTRIBUTE privTemplate[] = {
    { CKA_SENSITIVE,      &cktrue,          sizeof(cktrue)     },
    { CKA_SIGN,           &cktrue,          sizeof(cktrue)     },
    { CKA_EXTRACTABLE,    &ckfalse,         sizeof(ckfalse)    },
    { CKA_TOKEN,           &cktrue,          sizeof(cktrue)     }, /* persist */
};
CK_MECHANISM mech = { CKM_RSA_PKCS_KEY_PAIR_GEN, NULL, 0 };
C_GenerateKeyPair(session, &mech,
                   pubTemplate,  sizeof(pubTemplate)/sizeof(pubTemplate[0]),
                   privTemplate, sizeof(privTemplate)/sizeof(privTemplate[0]),
                   &pubHandle, &privHandle);
```

After this call, the private key material exists only inside the HSM. The host receives an opaque 64-bit *handle* — not the key. The host can ask the HSM to sign something using `C_Sign(session, &privHandle, data, ...)` but it can never call `C_GetAttributeValue(session, privHandle, {CKA_VALUE})` and get the private exponent back; the HSM refuses with `CKR_ATTRIBUTE_SENSITIVE`.

Randomness for the key comes from the HSM's onboard TRNG (true random number generator) — usually a ring-oscillator or quantum-noise source that has been FIPS-tested to be uninfluenced by the host's RNG state. This is a real defense: if your host RNG is compromised (as Debian's was in 2008, or OpenSSL CVE-2007-6755), keys generated in software are compromised. Keys generated inside a Level 3+ HSM are not.

## Key Wrapping and Export

For backup, key migration, or key ceremonies, you sometimes *must* move a key out of one HSM into another. PKCS#11 supports this with **wrapping**: the source HSM encrypts the key under a *wrapping key* (typically an AES-256 key or an RSA public key) and emits the ciphertext to the host. The ciphertext can be shipped to the destination HSM, where the corresponding unwrapping key decrypts it directly into a new sensitive object. The key material is never visible to the host as plaintext.

The relevant mechanisms are `CKM_AES_KEY_WRAP` (RFC 3394, the standard NIST key-wrap with integrity padding), `CKM_RSA_PKCS_OAEP` for RSA-based wrapping, and `CKM_NIST_KYBER_*` (added in v3.1) for post-quantum-safe key transport.

A common DR pattern with two HSMs is:

```
   HSM A (primary)                  HSM B (DR site)
   -----------                      ---------------
   1. Generate KEK (AES-256,        1. Generate KEK (AES-256,
      CKA_EXTRACTABLE=false)            CKA_EXTRACTABLE=false)
   2. Export KEK_A's public wrap   1. Wrap KEK_B under KEK_A's
      component (KEK_A_pub) ->         public half (KEK_A_pub) ->
      host                             host -> load into HSM A
                                       as a "wrap key"
   3. Generate master signing key
      (non-exportable)
   4. Wrap master under KEK_B_pub
      (imported from B) -> ciphertext
                                       2. Unwrap ciphertext under
                                          KEK_B_priv -> new master
                                          object (non-extractable)
```

The KEKs themselves are non-exportable; the only thing that ever crosses the network is wrapped ciphertext. To split knowledge further, the KEK is often generated using "M-of-N smartcard quorum" (KRA — Key Recovery Agents) where `M` of `N` smartcards must be present in the HSM before a wrap operation succeeds.

## Comparison to Software Crypto

| Property              | Software (OpenSSL/libsodium)   | HSM (PKCS#11)                |
|-----------------------|--------------------------------|------------------------------|
| Key material location | Host RAM/disk                 | HSM-internal sealed storage  |
| Key exposure on host  | Yes, any root/ptrace process  | Never (no `CKA_VALUE` reads) |
| Random source         | Host `/dev/urandom`/`getrandom` | HSM TRNG (FIPS-tested)        |
| Key gen audit trail   | None                          | HSM firmware logs every op   |
| Throughput (RSA-2048) | 10,000/s/core                 | 1,000-50,000/s (device dep.) |
| Cost                  | Free                          | $700 (YubiHSM) to $50k+       |
| Tamper resistance     | None                          | Level 1-4 per FIPS 140-3     |
| Side-channel defense  | None                          | Constant-time HW + masking   |

The non-trivial caveat is that *using* an HSM is slower and more fragile than software crypto. Every sign operation is a round-trip into the HSM; for a 50,000 TPS TLS termination workload, you may need a $40,000 PCIe card per host just to match what OpenSSL does in software for free. HSMs make sense when the threat model includes the host being compromised (a root-level attacker who could otherwise dump the private key) or when compliance (PCI DSS, government) mandates it.

## Common Pitfalls

1. **Treating `CKA_EXTRACTABLE=true` keys as if they live in the HSM.** If the attribute is true, an attacker who gets an authenticated HSM session can wrap the key out. Sensitive long-lived keys should always be both `CKA_SENSITIVE=true` and `CKA_EXTRACTABLE=false`.

2. **Using the SO (Security Officer) PIN in production code.** The SO pin is the administrator credential used for token initialization and PIN reset. Production applications should log in with the user pin only. Treat the SO pin like a root password.

3. **Storing the user pin on the host disk in plaintext.** This is the most common production failure: the application has the PKCS#11 user pin in `/etc/app.conf`, so anyone with root on the host can do anything the HSM allows. Use an OS-level secret store (Linux keyring, AWS Secrets Manager) and constrain what that pin can authorize.

4. **Ignoring the HSM clock.** HSMs have an onboard RTC, and you can constrain a key with `CKA_START_DATE`/`CKA_END_DATE`. If the host date is wrong, the key won't work; if the HSM clock is wrong, the same is true. NTP the HSM, and verify its clock as part of monitoring.

5. **Assuming `libsofthsm2` is a substitute for a real HSM in production.** SoftHSM2 is a PKCS#11 software emulation used for testing. It implements the API correctly but provides *none* of the hardware protections. Code that targets SoftHSM2 in dev and a real HSM in production is fine; using SoftHSM2 in production is a security regression.

6. **Not testing key backup before you need it.** DR with HSMs is *hard*. If your only HSM catches fire, every `CKA_EXTRACTABLE=false` key on it is gone forever. Test your key ceremony end-to-end at least once per year.

## References

- OASIS PKCS#11 Technical Committee, "[PKCS #11 v3.1 Base Specification](https://docs.oasis-open.org/pkcs11/pkcs11-base/v3.1/os/pkcs11-base-v3.1-os.html)" (2023)
- NIST, "[FIPS 140-3: Cryptographic Module Security Requirements](https://csrc.nist.gov/pubs/fips/140-3/upd1/final)" (2025 update)
- NIST, "[FIPS 140-3 Implementation Guidance](https://csrc.nist.gov/projects/cryptographic-module-validation-program/standards)" (CMVP)
- Thales, "[Luna Network HSM 7 Administration Guide](https://docs.thalesgroup.com/docs/luna_network_hsm_7_administration_guide.pdf)"
- Yubico, "[YubiHSM 2 User Guide](https://docs.yubico.com/hardware/yubihsm-2/hardware/yubihsm-2-user-guide.html)"
- Utimaco, "[SecurityServer Se-Series Product Brief](https://www.utimaco.com/products/hardware-security-modules/general-purpose-hsm/securityserver-se-series)"
- OpenSC, "[SoftHSM2 (PKCS#11 software HSM, for development)](https://github.com/opendnssec/SoftHSMv2)"
- OpenSSL project, "[How to use PKCS#11 engines and providers](https://github.com/OpenSC/libp11)"
- RFC 3394, "[Advanced Encryption Standard (AES) Key Wrap Specification](https://www.rfc-editor.org/rfc/rfc3394)"
