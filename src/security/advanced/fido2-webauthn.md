# FIDO2 / WebAuthn: Phishing-Resistant Authentication from First Principles

Passwords authenticate by replaying a shared secret, so anything that can phish the
user can replay it. FIDO2 replaces the secret with a per-site public/private keypair
that never leaves the authenticator: a credential captured on one origin is
cryptographically useless on another. **WebAuthn** is the W3C browser API the relying
party (RP) talks to; **CTAP2** is the FIDO Alliance protocol the client platform uses
to reach the authenticator over USB, NFC, or BLE -- for the password/session landscape this replaces, see
[authentication](../authentication.md).

## The two-layer stack

```text
+--------------------+ WebAuthn +--------------------------+ CTAP2 +------------------+
| Relying party (web)| <------> | Client platform          | <---> | Authenticator    |
| navigator          |          | (browser / OS WebAuthn)  | USB   | security key,    |
| .create()/.get()   |          | mediates UI, checks      | NFC   | phone, secure    |
| verifies signatures|          | origin, encodes CBOR     | BLE   | enclave, TPM     |
+--------------------+          +--------------------------+       +------------------+
```

WebAuthn defines the JS surface, ceremonies, and data structures; CTAP2 defines the
wire protocol to roaming authenticators: `authenticatorMakeCredential` /
`authenticatorGetAssertion` CBOR commands, transport framing, user-verification
helpers. A platform authenticator (Touch ID, Windows Hello) implements both layers
internally; the browser enforces origin/consent rules identically either way.

## Credential model: one keypair per RP ID, and why phishing dies

At registration the authenticator generates a fresh keypair scoped to a single
**RP ID**. The private key is non-exportable -- generated inside the secure element,
it only ever emits signatures. The RP ID must be a registrable domain suffix of the
origin's domain (`login.example.com` may use `example.com`; `example.com.evil.io` may not).
The browser will not offer a credential outside its RP ID: nothing to approve.

```text
Attacker scenario                 Password              FIDO2 / WebAuthn
--------------------------------  --------------------  -------------------------
evil.io mimics example.com        typed secret replayed    RP ID mismatch: browser
                                                           never releases the key
real-time MITM relay (Evilginx)   secret relayed         origin in signed
                                  works verbatim         clientDataJSON; relay
                                                         cannot forge the bytes
```

The signature covers `authenticatorData || SHA-256(clientDataJSON)`. The server --
not the browser -- checks origin and challenge inside `clientDataJSON`: the browser
guarantees the fields are filled honestly; the RP enforces that they match its records.

## Authenticator data and clientDataJSON: the signed bytes

```text
byte  0-31   rpIdHash          SHA-256 of the RP ID (server re-derives, compares)
byte  32     flags             bitfield, table below
byte  33-36  signatureCounter  uint32 big-endian; may be 0 if unsupported
byte  37+    attestedCredentialData  [registration only, when AT=1]
               16 B  AAGUID     authenticator model identifier
               2 B   credIdLen  credential ID length, big-endian
               n B   credentialId, followed by CBOR COSE_Key (algorithm + key material)
byte  ...    extensions        CBOR map, only when ED=1
```

| Flag | Bit | Meaning | Server policy question |
|------|-----|---------|------------------------|
| UP (User Present) | 0 | User physically touched the device | Require always |
| UV (User Verified) | 2 | Biometric/PIN verified identity | Require for step-up / high value |
| BE (Backup Eligible) | 3 | Credential may sync to cloud | Track for passkey management |
| BS (Backup State) | 4 | Credential currently in a backup | Detect single- vs multi-device |
| AT (Attested) | 6 | Attested credential data included | Parse AAGUID + public key |
| ED (Extensions) | 7 | Extension data present | Parse or reject per policy |

UP vs UV is a classic interview distinction: presence proves *a human is at the
device*; verification proves *the right human*; reject UV=0 assertions when UV was
required, as the demo does.

Per ceremony the browser also assembles, e.g.
`{"type":"webauthn.create","challenge":"9B9B...","origin":"https://example.com","crossOrigin":false}`.
RP verification checks: `type` matches the ceremony, `challenge` equals the issued
nonce (anti-replay), `origin` equals the RP's own origin (anti-phishing/anti-MITM), and
`crossOrigin` false unless iframes are allowed. The signature makes these checks tamper-proof.

## Ceremonies: registration, then authentication

```text
REGISTRATION (credentials.create)            AUTHENTICATION (credentials.get)
RP -> browser: challenge, user, RP ID        RP -> browser: challenge, allowCreds
browser -> authn: authenticatorMakeCredential  browser -> authn: getAssertion
authn: generate keypair; require UP/UV       authn: pick cred by RP ID; unlock;
authn: returns attObj (fmt + attStmt +        increment counter
  authData(AT=1))                            authn: assertion: authData(UP|UV,
browser -> RP: cdJSON + attObj               counter) + signature
RP: check challenge/origin/flags             RP: verify sig over authData||
RP: store credentialId + public key          hash(cdJSON); UP/UV; counter; origin
```

Registration stores the public key and credential ID; no secret crosses the wire.
Each login is a fresh challenge signed with the stored key -- nothing replayable.

## Ceremony verification, byte by byte (toy harness)

The demo builds both ceremonies with real field layouts, uses HMAC-SHA256 as the
stand-in signature (real input `authData || SHA-256(clientDataJSON)` preserved), and
runs server-side verification including negative cases.

```python
"""Toy WebAuthn ceremony harness: HMAC-SHA256 stands in for ES256 (input shape authData || SHA256(cdJSON))."""
import hashlib, hmac, json
RP_ID, ORIGIN = "example.com", "https://example.com"
UP, UV, AT = 0x01, 0x04, 0x40                    # authenticator-data flag bits
HMAC_KEY = b"toy-es256-private-key"              # stand-in key material
def auth_data(rp_id, flags, counter, cred_id=None, cred_pub=None):
    out = hashlib.sha256(rp_id.encode()).digest()   # rpIdHash (32B)
    out += bytes([flags])                           # flags (1B)
    out += counter.to_bytes(4, "big")               # signatureCounter (4B BE)
    if flags & AT:                                  # attestedCredentialData
        out += bytes(16)                            # AAGUID (toy: zeros)
        out += len(cred_id).to_bytes(2, "big")      # credentialIdLength (2B BE)
        out += cred_id + bytes([0xA2, 0x01, 0x02, 0x03, 0x26]) + cred_pub  # COSE_Key EC2/ES256
    return out
def client_data(cd_type, challenge, origin=ORIGIN, cross_origin=False):
    return json.dumps({"type": cd_type, "challenge": challenge, "origin": origin,
                       "crossOrigin": cross_origin}, separators=(",", ":")).encode()
def signature(authd, client_json):
    return hmac.new(HMAC_KEY, authd + hashlib.sha256(client_json).digest(), hashlib.sha256).digest()
def verify(sig, authd, cd_json): return hmac.compare_digest(sig, signature(authd, cd_json))
def check(name, ok, why="OK"):
    print(f"{name:<36} {'PASS' if ok else 'REJECT':<7} {'' if ok else why}")

# ---- registration ceremony (webauthn.create) ------------------------------
chal = bytes([0x9B] * 32).hex()                      # server nonce
authd_r = auth_data(RP_ID, UP | UV | AT, counter=0,
                    cred_id=b"cred-0001", cred_pub=b"65-pub")
cd_r = client_data("webauthn.create", chal); sig_r = signature(authd_r, cd_r)
check("reg: rpIdHash matches RP ID", authd_r[:32] == hashlib.sha256(RP_ID.encode()).digest())
check("reg: signature verifies", hmac.compare_digest(sig_r, signature(authd_r, cd_r)))
check("reg: UP+UV flags set", (authd_r[32] & (UP | UV)) == (UP | UV),
      f"flags=0x{authd_r[32]:02x} missing user presence/verification")
check("reg: AT flag + credential present", bool(authd_r[32] & AT))
check("reg: origin binding", json.loads(cd_r)["origin"] == ORIGIN)
cd_phish = client_data("webauthn.create", chal, origin="https://example.com.evil.io")
check("reg: phishing origin", verify(sig_r, authd_r, cd_phish),
      "origin=example.com.evil.io != expected https://example.com")
prev = 0
for ctr, label in [(42, "auth: login #1"), (43, "auth: login #2"),
                   (43, "auth: login #3 (rollback)")]:
    authd_a = auth_data(RP_ID, UP | UV, counter=ctr)
    cd_a = client_data("webauthn.get", chal); count = int.from_bytes(authd_a[33:37], "big")
    check(label, verify(signature(authd_a, cd_a), authd_a, cd_a)
          and bool(authd_a[32] & UV) and count > prev,
          "" if count > prev else "counter did not advance -> possible cloned authenticator")
    prev = max(prev, count)
check("auth: UV flag missing", bool(auth_data(RP_ID, UP, counter=44)[32] & UV),
      "UP set but UV=0 -> user verification not proven; reject if UV required")
```

Real output (the phishing, rollback, and UV rejections are the interesting lines):

```text
reg: rpIdHash matches RP ID          PASS    
reg: signature verifies              PASS    
reg: UP+UV flags set                 PASS    
reg: AT flag + credential present    PASS    
reg: origin binding                  PASS    
reg: phishing origin                 REJECT  origin=example.com.evil.io != expected https://example.com
auth: login #1                       PASS    
auth: login #2                       PASS    
auth: login #3 (rollback)            REJECT  counter did not advance -> possible cloned authenticator
auth: UV flag missing                REJECT  UP set but UV=0 -> user verification not proven; reject if UV required
```

The counter deserves honesty about its limits: it exists to catch key duplication (a
clone cannot know the honest device's next value), but it is optional -- devices
returning 0 forever give none, synced passkeys typically omit monotonic counters, and
rollback can follow backup/restore: step up and re-verify rather than auto-lockout.

## Attestation: proving the authenticator, at a privacy cost

Attestation is the registration-time signature proving *what kind of device it is*,
via an attestation certificate chain -- the same trust problem as chains in [PKI](../../cryptography/pki.md).

| Conveyance | What the RP gets | Privacy / ops trade-off |
|------------|------------------|-------------------------|
| `none` | No attestation statement | Browser default; strongest privacy, zero device trust |
| `indirect` | Anonymized/derived statement | Balances signal against tracking protection |
| `direct` | Real attestation cert + AAGUID | Device model exposed to RP; trust-store upkeep |
| `enterprise` | Non-anonymized, targeted AAGUIDs | Orgs auditing their own key fleet only |

Wire formats (`fmt` in the attestation object): `packed` (common FIDO one), `tpm`,
`android-key`, `android-safetynet`, `fido-u2f` (legacy), `apple` (anonymous per-RP).
Per-device certs make users trackable across sites: `none` is the sensible consumer
default, `direct` belongs to regulated/enterprise flows, many RPs skip it entirely.

## CTAP2: transports and the pinUvAuth protocol

| Transport | Physical layer | Notes |
|-----------|----------------|-------|
| `usb` | HID (FIDO frames over USB HID) | Dominant for security keys |
| `nfc` | ISO 14443 / ISO 7816 APDUs | Tap-to-sign; short sessions, weak PIN UX |
| `ble` | Bluetooth GATT | Rare now; mostly FIDO-U2F heritage |
| `internal` | Platform authenticator | Touch ID / Windows Hello; no CTAP wire visible |
| `hybrid` | QR + BLE proximity, data via tunnel | Passkey cross-device sign-in (caBLE) |

When a command requires user verification but the device has no built-in biometric,
platform and authenticator run the **pinUvAuthProtocol**: a P-256 (COSE ES256) key
agreement establishes a shared secret so the PIN never crosses the wire, and an
HMAC-SHA-256 `pinUvAuth` tag authenticates the exchange. Version 2 is current;
version 1 is legacy with weaker entropy handling. A bounded retry counter (CTAP2.1)
reboots or bricks the device after repeated PIN failures -- anti-brute-force by design.

## Discoverable credentials and passkeys

A **non-discoverable** credential leaves only a key handle on the device: the server
must name it in `allowCredentials`. A **discoverable** credential (resident key) is
stored on the authenticator with the user handle, enabling username-less login.

**Passkeys** are discoverable credentials that sync: iCloud Keychain, Google Password
Manager, and password managers replicate encrypted credential material across devices
-- removing the single-device point of failure, at the cost of the non-exportability
story. The BE/BS flags let a server distinguish a synced passkey
from a device-bound key and enforce policy ("bank accounts require BS=0 device-bound
credentials"). The `hybrid` transport lets a phone sign for a laptop: scan a QR, BLE
proves proximity (a remote phisher cannot relay it), the ceremony tunnels over the
network; RP ID rules still apply, so cross-device does not reopen phishing.

## Algorithms: ES256 is the floor, not the ceiling

| COSE alg | Name | Status in practice |
|----------|------|--------------------|
| -7 | ES256 (P-256 ECDSA, SHA-256) | Mandatory baseline; universal |
| -8 | EdDSA (Ed25519) | Optional; rare in roaming hardware; see [Ed25519](../../cryptography/ed25519.md) |
| -257 | RS256 (RSASSA-PKCS1-v1_5) | Common in platform authenticators (Windows Hello) |

ES256 dominates for historical (U2F) and practical reasons: tiny keys and signatures
fit BLE/NFC budgets. Ed25519 signatures are smaller and deterministic (no k-nonce
catastrophes) but adoption is thin -- advertise a list, not one answer. RS256 exists
because some TPMs only do RSA; PKCS1-v1_5 is compatibility, not choice.

## Account recovery: the unsolved edge

FIDO2 secures *authentication*, not *recovery*. A user who loses the only passkey
falls back to exactly the channels FIDO meant to replace: email magic links, SMS,
support-desk checks. Guidance that survives interviews: enroll multiple credentials
(one synced passkey plus one hardware key in a drawer), make recovery a separate
high-friction, rate-limited ceremony, and never let it silently delete the strongest
credential. Passkeys move the phishable password's risk to the recovery path.

## Interview angles

- Origin binding lives in `clientDataJSON` (server-checked); RP ID binding in `rpIdHash` (browser-enforced).
- Walk an Evilginx-style MITM relay and identify which byte the attacker cannot forge.
- Design passkey policy from BE/BS: which accounts may use synced credentials?
- When is `direct` attestation justified, and what does it leak?

## References

1. W3C, "Web Authentication: An API for accessing Public Key Credentials" (Level 3) -- https://w3c.github.io/webauthn/
2. FIDO Alliance, "Client to Authenticator Protocol (CTAP) 2.1" -- https://fidoalliance.org/specs/fido-v2.1-ps-20210615/fido-client-to-authenticator-protocol-v2.1-ps-20210615.html
3. MDN Web Docs, "Web Authentication API" -- https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API
4. MDN Web Docs, "PublicKeyCredentialCreationOptions" (transports incl. `hybrid`) -- https://developer.mozilla.org/en-US/docs/Web/API/PublicKeyCredentialCreationOptions
5. Passkeys Directory (RP adoption index) -- https://passkeys.directory/
