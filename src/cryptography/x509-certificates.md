# X.509 Certificates

X.509 is the ITU-T standard for public key certificates, defined in RFC 5280 and updated by RFC 6818. Every HTTPS, IPsec, S/MIME, and code-signing deployment uses X.509 certificates to bind a public key to an identity. This page covers the wire format, the field model, the extension system, and the RFC 5280 path validation algorithm — the exact rules your browser, OS trust store, and `openssl verify` all run.

## ASN.1, DER, and PEM

A certificate is defined by an ASN.1 schema. The full schema for a Certificate lives in RFC 5280 §4.1:

```
Certificate ::= SEQUENCE {
    tbsCertificate       TBSCertificate,
    signatureAlgorithm   AlgorithmIdentifier,
    signatureValue       BIT STRING
}

TBSCertificate ::= SEQUENCE {
    version         [0]  EXPLICIT Version DEFAULT v1,
    serialNumber         CertificateSerialNumber,
    signature            AlgorithmIdentifier,
    issuer               Name,
    validity             Validity,
    subject              Name,
    subjectPublicKeyInfo SubjectPublicKeyInfo,
    issuerUniqueID  [1]  IMPLICIT UniqueIdentifier OPTIONAL,  -- v2+
    subjectUniqueID [2]  IMPLICIT UniqueIdentifier OPTIONAL,  -- v2+
    extensions      [3]  EXPLICIT Extensions OPTIONAL          -- v3+
}
```

The key concept is that `tbsCertificate` ("to-be-signed") is the actual content of the certificate, and `signatureValue` is the CA's signature over the DER encoding of `tbsCertificate`. Verifying a certificate means re-deriving the TBS bytes, hashing them, and checking the CA's signature with its public key.

There are two encodings you'll meet in the wild:

- **DER** (Distinguished Encoding Rules) — binary, canonical, single accepted form. Used on the wire and in `*.der` files.
- **PEM** — base64 of DER wrapped in `-----BEGIN CERTIFICATE-----` / `-----END CERTIFICATE-----` armor. Multiple PEM blocks can be concatenated into one file (a chain).

```python
# Round-trip a PEM <-> DER in Python (pure stdlib)
import base64

def pem_to_der(pem_text: str) -> bytes:
    body_lines = []
    for line in pem_text.splitlines():
        if line.startswith("-----"):
            continue
        body_lines.append(line.strip())
    return base64.b64decode("".join(body_lines))

def der_to_pem(der_bytes: bytes, label: str = "CERTIFICATE") -> str:
    b64 = base64.b64encode(der_bytes).decode("ascii")
    chunks = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    return f"-----BEGIN {label}-----\n" + "\n".join(chunks) + f"\n-----END {label}-----\n"
```

Because DER is canonical (there is exactly one valid byte stream per ASN.1 value), byte-equal hash comparisons of `tbsCertificate` are safe and form the basis for things like the TLS 1.3 `CertificateVerify` message.

## Distinguished Names

`Name` in the schema is an `X.501` `DistinguishedName` — a sequence of Relative Distinguished Names (RDNs). Each RDN is itself a set of attribute-value pairs.

```
Name        ::= RDNSequence
RDNSequence ::= SEQUENCE OF RelativeDistinguishedName
RelativeDistinguishedName ::= SET SIZE (1..MAX) OF AttributeTypeAndValue
AttributeTypeAndValue ::= SEQUENCE { type OID, value ANY }
```

Common attribute OIDs:

| Attribute | OID                | Example value                |
|-----------|-------------------|------------------------------|
| CN        | 2.5.4.3           | `api.example.com`            |
| C         | 2.5.4.6           | `US`                         |
| O         | 2.5.4.10          | `Let's Encrypt`              |
| OU        | 2.5.4.11          | `R3`                         |
| ST        | 2.5.4.8           | `California`                 |
| L         | 2.5.4.7           | `San Francisco`              |

String-typed attributes use `UTF8String`, `PrintableString` (only ASCII letters, digits, and a few symbols), or `IA5String`. Modern CAs issue `UTF8String` for everything except `C` (which must be `PrintableString` per RFC 5280 §4.1.2.6). Mismatched encoding has bitten real systems: iOS at one point rejected certificates whose `Organization` field used `UTF8String` where `PrintableString` was expected.

**Important:** The Subject `CN` is *not* how modern clients match the hostname. Browsers since 2017 ignore the CN entirely and rely exclusively on `SubjectAltName`. CN-based matching was deprecated by RFC 2818 in 2000 but kept working for compatibility until Chrome 58 killed it.

## Validity Period

`Validity` is a `SEQUENCE { notBefore Time, notAfter Time }`. `Time` is a `CHOICE` between `UTCTime` (two-digit year, valid 1950–2049) and `GeneralizedTime` (four-digit year). RFC 5280 §4.1.2.5 mandates:

- Years < 50 → UTCTime interpreted as 20xx
- Years 50 ≤ y < 150 → GeneralizedTime

A certificate valid through 2047 uses `UTCTime`; one valid in 2049 or later uses `GeneralizedTime`. Let's Encrypt certs are 90 days, well inside `UTCTime` range.

## SubjectPublicKeyInfo

`SubjectPublicKeyInfo ::= SEQUENCE { algorithm AlgorithmIdentifier, subjectPublicKey BIT STRING }`. The `algorithm` field is an OID identifying the key type (e.g., `1.2.840.113549.1.1.1` for RSA, `1.2.840.10045.2.1` for EC). The `BIT STRING` wraps an algorithm-specific encoding (an RSAPublicKey or ECPoint).

## Extensions (X.509 v3)

v3 extensions are the workhorse of modern PKI. Without them, a certificate is just a key with a name; with them, it expresses purpose, CA status, name constraints, and revocation endpoints.

| Extension                  | OID                  | Critical? | Purpose                                    |
|----------------------------|----------------------|-----------|--------------------------------------------|
| Subject Key Identifier     | 2.5.29.14            | no        | Hash of subject public key (chain building) |
| Authority Key Identifier   | 2.5.29.35            | no        | Identifies the signing CA's key             |
| Subject Alt Name           | 2.5.29.17            | yes*      | DNS/email/IP identities                     |
| Basic Constraints          | 2.5.29.19            | yes       | Is this a CA? Path length?                 |
| Name Constraints           | 2.5.29.30            | yes       | Subtree allow/deny for subordinate CAs      |
| Key Usage                  | 2.5.29.15            | yes       | digitalSignature/keyEncipherment/etc.       |
| Extended Key Usage         | 2.5.29.37            | no        | serverAuth/clientAuth/codeSigning/…        |
| CRL Distribution Points    | 2.5.29.31            | no        | URLs to fetch CRL                          |
| Authority Info Access      | 1.3.6.1.5.5.7.1.1    | no        | OCSP URL + CA Issuer URL                   |
| Certificate Policies       | 2.5.29.32            | no        | CA/B Forum policy OIDs                     |

(*) RFC 5280 §4.2.1.6 says SAN SHOULD be critical when Subject is empty, and MAY be critical otherwise. In practice CA/Browser Forum Baseline Requirements require SAN critical=true.

### Basic Constraints

```
BasicConstraints ::= SEQUENCE {
    cA                BOOLEAN DEFAULT FALSE,
    pathLenConstraint INTEGER (0..MAX) OPTIONAL
}
```

This is the single most important field for distinguishing a CA from a leaf. A leaf certificate with `CA:TRUE` would let an attacker sign arbitrary subordinate certificates — this is the heart of the 2009 Comodo / 2011 DigiNotar / 2015 Lenovo Superfish incidents. Modern auditors and browsers reject any leaf with `basicConstraints.cA=true` outside the explicitly trusted chain, and CA programs require this extension to be marked critical.

`pathLenConstraint` is the maximum number of non-self-issued intermediate CAs that may follow this CA in a chain. A CA with `pathLen=0` can issue leaves but not sub-CAs. A CA with `pathLen=1` can issue a sub-CA that can issue leaves, and so on.

### Subject / Authority Key Identifier

SKI is `160-bit SHA-1` of the BIT STRING contents of the subject public key (per RFC 5280 §4.2.1.2). AKI is the SKI of the issuing CA's key. The pair forms the linkage used during chain building: given a leaf, the verifier looks for a CA whose SKI matches the leaf's AKI.

### Subject Alternative Name

```
GeneralName ::= CHOICE {
    otherName                 [0]  AnotherName,
    rfc822Name                [1]  IA5String,    -- email
    dNSName                   [2]  IA5String,    -- hostname
    uniformResourceIdentifier [6]  IA5String,    -- URI
    iPAddress                 [7]  OCTET STRING, -- 4 or 16 bytes
    ...
}
```

For a website cert the SAN is a list of `dNSName`s. A wildcard `*.example.com` is allowed exactly one label per RFC 6125 — `*.*.example.com` is invalid. Each SAN must be FQDN-form and limited to 253 chars.

### Name Constraints

A CA can restrict what its subordinates may issue. The extension format:

```
NameConstraints ::= SEQUENCE {
    permittedSubtrees [0] GeneralSubtrees OPTIONAL,
    excludedSubtrees  [1] GeneralSubtrees OPTIONAL
}
GeneralSubtree ::= SEQUENCE {
    base    GeneralName,
    minimum [0] BaseDistance DEFAULT 0,
    maximum [1] BaseDistance OPTIONAL
}
```

A `dNSName` constraint of `.example.com` matches `www.example.com` and `a.b.example.com` but not `example.com` itself (the leading dot is a "subtree of" marker). A constraint without a leading dot matches the host itself and any subdomain. Constraints are evaluated per `GeneralName` type — a `directoryName` constraint does not affect `dNSName` SANs.

This is the mechanism that lets an enterprise run an internal CA whose certs are only valid inside `corp.acme.com` and would be rejected even if a browser were tricked into trusting it.

## Certificate Chain Validation — RFC 5280 §6.1

Path validation is the algorithm every conforming client must run. Given a *trust anchor* (root CA cert in the trust store) and a *certification path* (a sequence `[leaf, intermediate_1, …, intermediate_n]` ending at the root), validation proceeds in three phases.

### Inputs

```
Inputs to algorithm (RFC 5280 §6.1.1):
  (a)  prospective certification path of length n
  (b)  trust anchor:  { trusted CA name, CA public key, (optional) signature alg }
  (c)  current date / time
  (d)  user-initial-policy-set (certificate policies to honor)
  (e)  (optional) explicit policy indicator
```

### State variables

```
State                       Initialized to:
  - candidateCerts         := the path, indexed 1..n (1 = leaf)
  - policy_tree            := root node for cert 1's policy set
  - explicit_policy        := (n+1)   ; countdown to enforce policy
  - inhibit_anyPolicy      := (n+1)
  - policy_mapping        := (n+1)
  - working_public_key    := trust anchor public key
  - working_issuer_name    := trust anchor subject DN
  - working_max_path_length:= n       ; decremented per non-self-issued CA
  - max_path_length        := n
```

### Phase 1: Basic certificate processing (per certificate i = 1..n)

For each certificate in the chain, the algorithm checks:

1. **Signature** — Verify cert i's signature using `working_public_key` and `working_issuer_name`.
2. **Validity period** — `notBefore ≤ currentTime ≤ notAfter`.
3. **Name chaining** — `cert[i].issuer == cert[i-1].subject` (after RFC 5280 name comparison, which is case-insensitive and LDAPv3-compliant).
4. **Policy processing** — Update the policy tree (see §6.1.3 f-g).
5. **Critical-extensions check** — All critical extensions must be recognized by the verifier. Unknown critical ext → reject.
6. **Verify name constraints** (when cert i is not self-issued) — Apply permitted/excluded subtrees to the next cert's SANs.
7. **Verify certificate policies** — Map policies, inhibit anyPolicy, etc.

### Phase 2: Prepare for next certificate (when not the last)

1. If `basicConstraints.cA == FALSE` → fail. (Leaf certs cannot sign.)
2. Decrement `max_path_length` if cert i is not self-issued.
3. If `pathLenConstraint` exists and is smaller than `max_path_length`, set `max_path_length := pathLenConstraint`.
4. Update `working_public_key` and `working_issuer_name` for the next iteration.
5. Apply name constraints from this certificate to subsequent certs.
6. Process `policyMappings` extension.

### Phase 3: Wrap-up

1. If `inhibit_anyPolicy > 0` or `explicit_policy == 0`, fail if `anyPolicy` is the only valid policy and anyPolicy was inhibited.
2. If `explicit_policy` says "explicit policy required" and no policy in user-initial-policy-set matches → fail.
3. The path is valid if and only if all the above checks succeed.

### Worked example

```
Chain:
  Root CA (self-signed, in trust store)
   └─ Intermediate CA (pathLen=0)
       └─ Leaf: *.api.acme.com (serverAuth EKU)

Validation walkthrough:
  cert[1] = Leaf
    - Verify sig with Intermediate's key   ✓
    - Validity window: 2024-01-01..2024-04-01, today 2024-02-15  ✓
    - issuer == Intermediate subject       ✓
    - BasicConstraints.cA == FALSE         ✓ (leaf)
    - SAN includes *.api.acme.com          ✓ (matches hostname)
    - EKU contains serverAuth              ✓
    - No name constraints violated         ✓
  cert[2] = Intermediate
    - Verify sig with Root's key           ✓
    - Validity window ok                   ✓
    - issuer == Root subject               ✓
    - BasicConstraints.cA == TRUE          ✓
    - pathLenConstraint = 0; max_path_length was 1 → becomes 0
    - SKI == leaf's AKI                    ✓
  cert[3] = Root (trust anchor)
    - Self-signed, pre-trusted             ✓
  Wrap-up: explicit_policy default, no policies required → PASS
```

A subtle but commonly-missed detail: name comparison uses **LDAPv3 distinguished name** rules, which are case-insensitive and ignore leading/trailing whitespace. So `CN=api.example.com` and `CN=API.Example.Com` are the same DN. Hostname comparison inside `dNSName` SAN is governed separately by RFC 6125 — also case-insensitive, but it follows IDNA2008 for internationalized names.

## Path Building

RFC 5280 specifies path *validation*, not path *building*. Building is finding the path in the first place — a hard, often NP-hard-feeling search. The most-cited approach is the "AIA chasing" method (RFC 4325 §6.2, refined by RFC 5280 §6.2.2):

```
1. Start from leaf.
2. Look at leaf.issuer and leaf.AKI.
3. Search local intermediate pool for a cert whose
   subject == leaf.issuer AND SKI == leaf.AKI.
4. If multiple match, recurse on each (depth-first).
5. If none match locally, look at leaf AIA extension's
   "caIssuers" URL; fetch the referenced cert(s) over HTTP
   and continue.
6. Stop when a cert's issuer matches a trust anchor.
```

Real libraries (OpenSSL, BoringSSL, GnuTLS, NSS, Go's `crypto/x509`) implement AIA chasing with a cache and a depth limit to prevent loops. Go's `x509.Verify` historically did *not* do AIA chasing; you must supply intermediates via `VerifyOptions.Intermediates`. OpenSSL does chase AIA when configured, and BoringSSL added it in Chrome.

## Common pitfalls in the wild

- **Cross-signed roots** — When a CA rotates its root, it gets another root to cross-sign the new key so old clients still trust it. This means the *same* subject+SPKI can appear under two trust anchors. Path validation must accept any valid path, and verifiers cache by SPKI+serial to avoid "which root?" ambiguity.
- **Distinguished name encoding drift** — A re-issued intermediate with the same DN but encoded differently (e.g., `PrintableString` → `UTF8String`) breaks the issuer/subject name comparison check.
- **Critical AIA extension** — Some legacy CAs mark AIA critical, which is wrong and forces verifiers to either implement AIA or reject. RFC 5280 §4.2.2.1 says AIA MUST NOT be critical.
- **Negative serial numbers** — RFC 5280 §4.1.2.2 says serials must be positive and ≤ 20 bytes; non-conformant certs have been rejected by macOS Secure Transport.

## Verifying a chain with the `cryptography` library

```python
import datetime
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key


def load_pem(path: str) -> x509.Certificate:
    with open(path, "rb") as f:
        return x509.load_pem_x509_certificate(f.read())


def verify_signature(child: x509.Certificate, issuer: x509.Certificate) -> bool:
    """Verify child is signed by issuer's private key (using issuer pubkey)."""
    issuer_pub = issuer.public_key()
    try:
        issuer_pub.verify(
            child.signature,
            child.tbs_certificate_bytes,
            padding.PKCS1v15() if child.signature_hash_algorithm else padding.PKCS1v15(),
            child.signature_hash_algorithm or hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def check_chain(leaf: x509.Certificate, intermediates, trust_anchors):
    """RFC 5280 §6.1 (simplified) chain validation."""
    now = datetime.datetime.now(datetime.timezone.utc)
    pool = list(intermediates) + list(trust_anchors)
    current = leaf
    chain = [current]

    for _ in range(10):  # bounded depth
        # Validity window
        if not (current.not_valid_before_utc <= now <= current.not_valid_after_utc):
            return False, f"expired/not-yet-valid: {current.subject.rfc4514()}"

        # Find issuer: subject matches current.issuer, and signature verifies
        issuer = None
        for cand in pool:
            if cand.subject == current.issuer and verify_signature(current, cand):
                issuer = cand
                break
        if issuer is None:
            return False, "no issuer found"
        chain.append(issuer)
        current = issuer

        # Stop when we land on a trust anchor
        if any(current == t for t in trust_anchors):
            # Also check BasicConstraints on intermediates we walked through
            for c in chain[1:-1]:
                bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
                if not bc.ca:
                    return False, f"non-CA in chain: {c.subject.rfc4514()}"
            return True, "valid"
    return False, "chain too long"
```

This is a simplified validator — it omits the policy tree, name constraints, and the `pathLenConstraint` decrement loop. The `cryptography` library exposes those primitives via `x509.verification` in recent versions, and `truststore` (Python's stdlib-backed system trust wrapper) hooks into the OS verifier directly.

## References

- RFC 5280 — Internet X.509 Public Key Infrastructure Certificate and CRL Profile — https://www.rfc-editor.org/rfc/rfc5280
- RFC 6818 — Updates to the Internet X.509 PKI Certificate and CRL Profile — https://www.rfc-editor.org/rfc/rfc6818
- RFC 6125 — Service Identification and Authentication Validation — https://www.rfc-editor.org/rfc/rfc6125
- OpenSSL `x509` command manpage — https://www.openssl.org/docs/manmaster/man1/openssl-x509.html
- NIST PKI Program documentation — https://csrc.nist.gov/projects/pki-certificate-management
- ITU-T X.509 (the base standard) — https://www.itu.int/rec/T-REC-X.509
- CA/Browser Forum Baseline Requirements — https://cabforum.org/baseline-requirements-documents/
- Python `cryptography` X.509 docs — https://cryptography.io/en/latest/x509/
- RFC 4325 — Authority Info Access chasing rationale (historical) — https://www.rfc-editor.org/rfc/rfc4325

## Interview Questions

1. **What's the difference between DER and PEM, and why does OpenSSL accept both?**
2. **What does the `cA` bit in Basic Constraints do, and what attack does marking it critical prevent?**
3. **Walk through the three phases of RFC 5280 path validation. What state does each phase mutate?**
4. **Why do modern browsers ignore the Subject CN and only look at SAN?**
5. **How does AIA chasing help during path building? What's its failure mode?**
6. **What's `pathLenConstraint`, and what real-world failure does it prevent?**
7. **Given a leaf with `KeyUsage = keyEncipherment` only, would TLS 1.3 work? Why or why not?**
8. **Name two ways that name-comparison can fail between an issuer and subject DN.**
9. **How would a `NameConstraints` extension on a CA cause a downstream leaf to be rejected?**
10. **Explain how cross-signed roots complicate path building.**
