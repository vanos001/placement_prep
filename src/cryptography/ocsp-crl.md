# OCSP and CRL — Certificate Revocation

Once a CA issues a certificate, things change. Private keys get stolen, employees leave, hosts get compromised, certs get mis-issued. Revocation is the PKI mechanism that lets a CA say "this certificate is no longer valid before its notAfter date." Two protocols dominate: **CRL** (RFC 5280 §5) — a periodically published signed list of revoked serials — and **OCSP** (RFC 6960) — an online query-response protocol. Both have serious operational flaws, and the ecosystem has spent 25 years patching them with stapling, must-staple, and CRLite.

## CRL — Certificate Revocation List

A CRL is a signed, dated list of revoked certificates, published by the issuer.

```
CertificateList ::= SEQUENCE {
    tbsCertList          TBSCertList,
    signatureAlgorithm   AlgorithmIdentifier,
    signatureValue       BIT STRING
}

TBSCertList ::= SEQUENCE {
    version            Version OPTIONAL,        -- v2 = 1
    signature          AlgorithmIdentifier,
    issuer             Name,
    thisUpdate         Time,
    nextUpdate         Time OPTIONAL,
    revokedCertificates SEQUENCE OF SEQUENCE {
        userCertificate  CertificateSerialNumber,
        revocationDate    Time,
        crlEntryExtensions Extensions OPTIONAL
    } OPTIONAL,
    crlExtensions      [0] EXPLICIT Extensions OPTIONAL
}
```

The issuer field of a CRL must match the issuer of the revoked certificates. CRL signatures are verified against the issuer's certificate, just like leaf certificate signatures. The `nextUpdate` field tells the client when a newer CRL will be available — clients SHOULD refuse to use a CRL past `nextUpdate`.

### CRL entry extensions

The most common entry extensions:

| Extension         | OID        | Purpose                                            |
|-------------------|------------|----------------------------------------------------|
| CRL Reason        | 2.5.29.21  | Why revoked: keyCompromise (1), CACompromise (2), affiliationChanged (3), superseded (4), cessationOfOperation (5), certificateHold (6), removeFromCRL (8), privilegeWithdrawn (9), AACompromise (10) |
| Invalidity Date   | 2.5.29.24  | When the cert became invalid (may predate revocation date) |
| Certificate Issuer | 2.5.29.29 | For indirect CRLs — DN of the actual issuer      |

### Full vs Delta CRLs

A **full CRL** contains every still-revoked serial the issuer has ever revoked. As a CA's customer base grows, the full CRL grows monotonically. By 2025 a major commercial CA's full CRL can be 50–500 MB. Fetching that on every TLS handshake is absurd.

A **delta CRL** (RFC 5280 §5.6.1) contains only the *new* revocations since a `base` CRL was issued. The client fetches the (large) base CRL once, then periodically fetches small delta CRLs and merges them locally. Delta CRLs use two extensions to coordinate:

```
CRLNumber            ::= INTEGER     -- monotonically increasing
BaseCRLNumber        ::= INTEGER     -- present on delta CRLs: which base this delta is relative to
deltaCRLIndicator    ::= BaseCRLNumber  (OID 2.5.29.27, critical)
```

A delta CRL is identified by the presence of the critical `deltaCRLIndicator` extension containing the `BaseCRLNumber` of the full CRL it's relative to. A delta CRL is invalid without that base in the client's cache.

### Indirect CRLs

Normally the CRL issuer == the certificate issuer. An **indirect CRL** is one issued by a different entity — useful when one CA delegates revocation to a shared service. The CRL's `crlExtensions` must contain the critical `indirectCRL` extension (OID 2.5.29.28, boolean true). When true, the verifier looks at each revoked entry's `Certificate Issuer` extension to figure out which CA actually revoked that serial.

## OCSP — Online Certificate Status Protocol

OCSP (RFC 6960, formerly RFC 2560) lets a client ask "is this specific serial revoked?" and get back a signed, real-time answer.

### Request

```
OCSPRequest ::= SEQUENCE {
    tbsRequest  TBSRequest,
    optionalSignature [0] EXPLICIT Signature OPTIONAL
}
TBSRequest ::= SEQUENCE {
    version            [0] EXPLICIT INTEGER DEFAULT v1,
    requestorName      [1] EXPLICIT GeneralName OPTIONAL,
    requestList                SEQUENCE OF Request,
    requestExtensions  [2] EXPLICIT Extensions OPTIONAL
}
Request ::= SEQUENCE {
    reqCert    CertID,
    singleRequestExtensions [0] EXPLICIT Extensions OPTIONAL
}
CertID ::= SEQUENCE {
    hashAlgorithm   AlgorithmIdentifier,
    issuerNameHash  OCTET STRING,    -- hash of issuer DN
    issuerKeyHash   OCTET STRING,    -- hash of issuer public key (BIT STRING contents)
    serialNumber    CertificateSerialNumber
}
```

The `issuerNameHash` and `issuerKeyHash` are hashes (usually SHA-1, though SHA-256 is preferred today) of the issuer's DN and public key — this is how the OCSP responder knows which CA issued the cert without the client sending the full certificate. The serial is sent in plaintext.

### Response

```
OCSPResponse ::= SEQUENCE {
    responseStatus      OCSPResponseStatus,
    responseBytes   [0] EXPLICIT ResponseBytes OPTIONAL
}
ResponseBytes ::= SEQUENCE {
    responseType   OID,    -- id-pkix-ocsp-basic = 1.3.6.1.5.5.7.48.1.1
    response   OCTET STRING  -- DER of BasicOCSPResponse
}
BasicOCSPResponse ::= SEQUENCE {
    tbsResponseData   ResponseData,
    signatureAlgorithm AlgorithmIdentifier,
    signature          BIT STRING,
    certs [0] [0] EXPLICIT SEQUENCE OF Certificate OPTIONAL
}
ResponseData ::= SEQUENCE {
    version           [0] EXPLICIT INTEGER DEFAULT v1,
    responderID           ResponderID,    -- byName or byKey
    producedAt             GeneralizedTime,
    responses              SEQUENCE OF SingleResponse,
    responseExtensions [1] EXPLICIT Extensions OPTIONAL
}
SingleResponse ::= SEQUENCE {
    certID                   CertID,
    certStatus               CertStatus,
    thisUpdate               GeneralizedTime,
    nextUpdate         [0]   GeneralizedTime OPTIONAL,
    singleExtensions   [1]   EXPLICIT Extensions OPTIONAL
}
CertStatus ::= CHOICE {
    good        [0] IMPLICIT NULL,
    revoked     [1] IMPLICIT RevokedInfo,
    unknown     [2] IMPLICIT UnknownInfo
}
```

Three states: `good`, `revoked` (with revocation date + reason), and `unknown` (the responder doesn't know — common during CA responder outages).

### Building a real OCSP request with cryptography + urllib

```python
import base64
import datetime
import hashlib
import json
import urllib.request
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, ec, rsa
from cryptography.x509.ocsp import OCSPRequestBuilder, load_der_ocsp_response


def fetch_ocsp(leaf_pem: bytes, issuer_pem: bytes) -> dict:
    leaf = x509.load_pem_x509_certificate(leaf_pem)
    issuer = x509.load_pem_x509_certificate(issuer_pem)

    # 1. Discover the OCSP URL from leaf's AIA extension
    aia = leaf.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
    ocsp_urls = [desc.access_location.value
                 for desc in aia
                 if desc.access_method == x509.AuthorityInformationAccessOID.OCSP]
    if not ocsp_urls:
        raise RuntimeError("no OCSP URL in AIA")
    url = ocsp_urls[0]

    # 2. Build the OCSP request (CertID is auto-derived from issuer + serial)
    builder = OCSPRequestBuilder().add_certificate(leaf, issuer, hashes.SHA1())
    # SHA-1 here is the hash of the issuer DN/key, not the message digest; SHA-1 is the
    # most widely supported CertID hash algorithm even in 2024 because the input is a
    # public value (the issuer's DN and SPKI), not a secret.
    req = builder.build()
    der_req = req.public_bytes(serialization.Encoding.DER)

    # 3. POST it (OCSP requests are POST with DER body, application/ocsp-request)
    http = urllib.request.Request(
        url,
        data=der_req,
        headers={"Content-Type": "application/ocsp-request"},
    )
    with urllib.request.urlopen(http, timeout=10) as resp:
        der_resp = resp.read()

    # 4. Parse and verify
    ocsp = load_der_ocsp_response(der_resp)
    if ocsp.response_status.name != "SUCCESSFUL":
        return {"status": str(ocsp.response_status)}

    # Find our cert's status
    for single in ocsp.responses:
        if (single.issuer_name_hash == hashlib.sha1(
                issuer.subject.public_bytes()).digest()
                and single.serial_number == leaf.serial_number):
            return {
                "cert_status": single.certificate_status.name,
                "this_update": single.this_update_utc.isoformat(),
                "next_update": (single.next_update_utc.isoformat()
                                 if single.next_update_utc else None),
            }
    return {"status": "no matching serial in OCSP response"}


def verify_ocsp_signature(ocsp_response, issuer_cert):
    """Verify the OCSP response was signed by the issuer (or a delegated responder)."""
    signer = issuer_cert.public_key()
    sig = ocsp_response.signature
    tbs = ocsp_response.tbs_response_bytes
    try:
        if isinstance(signer, rsa.RSAPublicKey):
            signer.verify(sig, tbs, padding.PKCS1v15(),
                          ocsp_response.signature_hash_algorithm)
        elif isinstance(signer, ec.EllipticCurvePublicKey):
            signer.verify(sig, tbs,
                          ec.ECDSA(ocsp_response.signature_hash_algorithm))
        return True
    except Exception:
        return False
```

A subtle but critical verification step: **the OCSP responder's signature must be checked against a key the client trusts**. That key is either (a) the issuer CA's own key (the responder cert contains an EKU with `id-kp-OCSPSigning`, OID 1.3.6.1.5.5.7.3.9, and is signed by the issuer), or (b) a delegated responder. For delegated responders, RFC 6960 §4.2.2.2 mandates the responder's cert contain the `id-pkix-ocsp-nocheck` extension (OID 1.3.6.1.5.5.7.48.1.5), which tells the client "don't try to recurse to OCSP-check this responder's cert."

## OCSP Stapling (TLS Status Request)

The fundamental problem with both OCSP and CRL is latency: every TLS handshake would need an extra round trip to the CA's responder or a multi-megabyte CRL fetch. **OCSP stapling** (RFC 6066 §8, the `status_request` TLS extension) flips this around — the server fetches the OCSP response, caches it, and *staples* it to its TLS handshake:

```
Client                                                Server
  |  ClientHello + status_request                      |
  |  ------------------------------------------------> |
  |                                                    | fetch OCSP from responder
  |                                                    | (cached, refreshed before nextUpdate)
  |  ServerHello + Certificate + CertificateStatus     |
  |  <------------------------------------------------ |
  |  verify OCSP signature using issuer key            |
  |  check certID serial == server cert serial         |
  |  check thisUpdate <= now <= nextUpdate              |
  |  handshake continues                               |
```

Stapling trades client-side network cost for server-side fetch. Servers must refresh before `nextUpdate` to avoid serving stale stapled responses. nginx, Apache, HAProxy, Caddy, Envoy, and `ssl_certificate` in OpenSSL all support it.

A multi-staple extension (`status_request_v2`, RFC 6961) lets the server staple multiple responses (one per intermediate) so the client gets revocation status for the whole chain. Deployment is rare; most servers staple only the leaf.

## Must-Staple (RFC 7633)

Stapling is opt-in: clients request it via TLS extension, and the server responds if it has a fresh response. There's a hard failure mode here — if the client requests status and the server has none, most clients proceed anyway. This is the **soft-fail** behavior.

**OCSP must-staple** (RFC 7633, extension OID 1.3.6.1.5.5.7.1.24, named `tls-feature`) is a certificate-side fix: the leaf cert asserts "I MUST be presented with a valid stapled OCSP response." Clients that honor must-staple will hard-fail a connection to a server that doesn't staple. The extension encodes a list of TLS extension OIDs the cert must be used with — the only one in use is `5` (status_request).

```
id-pe-tlsfeature OBJECT IDENTIFIER ::= { id-pe 24 }
TLSFeatures ::= SEQUENCE OF TLSFeature
TLSFeature ::= INTEGER { status_request(5), status_request_v2(17) }
```

Let's Encrypt started issuing must-staple in 2020. Activation is a single command-line flag (`--must-staple` in certbot, `--features` in acme.sh). The operational contract: if you enable must-staple, your web server must fetch and rotate OCSP responses or clients that check will refuse to connect. Browsers that respect it today include Firefox and (for EV) Chrome.

## The revocation void

The phrase "revocation doesn't work" became common after the 2011 "Revocation is Broken" paper (Lang, B., et al.) and Ryan Hurst's "Revocation Doesn't Work" post. The fundamental problem:

1. **Soft-fail by default.** Browsers don't hard-fail when OCSP/CRL fetch fails (because they can't — too many CAs run flaky responders, and aggressive hard-fail would break too many TLS connections). An attacker who can MITM OCSP can just block the request.
2. **Privacy.** OCSP leaks which sites you visit to the CA. The EFF's "Decentralized SSL Observatory" paper documented this.
3. **Replay.** A cached OCSP response is valid until `nextUpdate`; an attacker who steals one "good" response can serve it to a victim even after the cert is revoked, until the cached response expires.

This is the **revocation void**: the gap between when a cert is revoked and when a typical client learns of it. For a 90-day Let's Encrypt cert with 10-day OCSP `nextUpdate`, an attacker can have up to 10 days of grace. For a 1-year commercial cert with weekly CRL updates, the void can be 7 days.

The pragmatic workarounds:

- **CRLite** (Mozilla, 2018–): Pushes Bloom filters of revoked serials to Firefox clients. False positives are resolved by OCSP. Turns O(N) fetches into a single ~1 MB filter push.
- **CRLSets** (Chrome): Hand-curated, hard-revoked list of certs pushed by Google. Small, fast, incomplete — covers only the worst incidents (DigiNotar, Symantec, etc.).
- **Short-lived certs (Let's Encrypt 90-day / 7-day experiment)**: if certs expire faster than the revocation void, revocation matters less. The 2024 "6-day certificate" Baseline Requirements change is rooted in this argument.
- **Must-staple + stapling**: pushes the "freshness" burden to the server, which has business incentive to keep it working.

## CRL vs OCSP — operational comparison

| Property                  | CRL                            | OCSP                              |
|---------------------------|--------------------------------|-----------------------------------|
| Fetch unit                | Whole list (KB–MB)             | Per-certificate (~1 KB)          |
| Freshness                 | Up to `nextUpdate` (days)      | Up to `nextUpdate` (hours–days)  |
| Client cost               | One large fetch, cached        | One network round trip per cert  |
| Server cost               | Static file, CDN-friendly      | Signed response per request       |
| Privacy                   | No leak (client fetches file)  | Leaks serials to CA/responder     |
| Fail-closed behavior      | Almost never used              | Almost never used (soft-fail)     |
| Caching-friendly          | Yes                            | Yes, but freshness concerns       |
| Works through firewalls   | HTTP yes, HTTPS sometimes      | HTTP/HTTPS, often blocked by corp proxies |

## Common operational mistakes

- **Setting `nextUpdate` too far out** to save bandwidth on your responder → long revocation void.
- **Reusing the same responder cert across multiple CAs** without indirect OCSP support → clients reject on key-id mismatch.
- **Serving stale OCSP responses after a CA key rollover** → clients fetch the *new* issuer's responder, but the server hasn't refreshed.
- **Stapling only the leaf** and forgetting intermediates → the `status_request_v2` MultiCertStatusRequest extension is honored by Chrome but most servers ignore it.
- **Allowing the OCSP responder to be a SPOF** → when Let's Encrypt's OCSP responder had an outage in 2020, every Let's Encrypt-stapling nginx that needed refresh during the window served stale or failed.

## References

- RFC 5280 §5 — Certificate Revocation List (CRL) profile — https://www.rfc-editor.org/rfc/rfc5280#section-5
- RFC 6960 — X.509 Internet PKI OCSP — https://www.rfc-editor.org/rfc/rfc6960
- RFC 6961 — TLS Multiple Certificate Status Request extension — https://www.rfc-editor.org/rfc/rfc6961
- RFC 7633 — X.509 OCSP-stapling tls-feature extension — https://www.rfc-editor.org/rfc/rfc7633
- RFC 6066 §8 — TLS `status_request` extension (OCSP stapling) — https://www.rfc-editor.org/rfc/rfc6066#section-8
- Let's Encrypt — "Revocation" documentation — https://letsencrypt.org/docs/revoking/
- Let's Encrypt — OCSP responder architecture blog — https://letsencrypt.org/2023/07/10/retiring-tls1-0-1-1.html (and the engineering blog series at https://letsencrypt.org/blog/)
- Mozilla CRLite engineering writeup — https://blog.mozilla.org/security/2020/01/07/crlite-part-2-end-to-end-design-of-a-bloom-filter-based-pki-system/
- Chrome CRLSets documentation — https://www.chromium.org/Home/chromium-security/crlsets/
- NIST SP 800-57 Part 1 Rev 5 — Key Management (covers revocation policy) — https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final
- Python `cryptography` OCSP module — https://cryptography.io/en/latest/x509/ocsp/

## Interview Questions

1. **What's in a CertID, and why does OCSP use a hash of the issuer DN instead of the full issuer name?**
2. **Walk through OCSP stapling end-to-end. Who fetches the response, when, and how does the client verify it?**
3. **What does must-staple change about a TLS deployment, and what happens if a must-staple cert is served without a stapled response?**
4. **Explain the revocation void. Why is soft-fail the default in browsers?**
5. **Difference between full and delta CRLs — when would you use each?**
6. **How does an indirect CRL differ from a normal CRL, and what extension must it carry?**
7. **What is `id-kp-OCSPSigning` and `id-pkix-ocsp-nocheck`? Why does the latter exist?**
8. **Name three approaches browsers take to mitigate the revocation void.**
9. **Why is OCSP-soft-fail vulnerable to blocking attacks, and how does must-staple fix that?**
10. **A CA rotates its root key. What happens to all previously issued OCSP responses for certs issued under the old root?**
