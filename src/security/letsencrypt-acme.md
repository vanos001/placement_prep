# Let's Encrypt and the ACME Protocol

Let's Encrypt is a free, automated, open Certificate Authority run by the Internet Security Research Group (ISRG). It has issued more than 500 million certificates and is the CA behind ~60% of HTTPS sites on the web. The reason it's *free, automated, and short-lived* is **ACME** — RFC 8555, the protocol designed alongside Let's Encrypt and standardized in 2019. This page covers the ACME objects, the three challenge types, the role of the account key, the rate limits that shape production deployments, and how Let's Encrypt compares to commercial CAs.

## The ACME resource model

ACME is a RESTful API over HTTPS where every request is JWS-signed by the client. The resource model has six object types:

```
Account  (one per client; bound to an asymmetric key pair)
  └── Order  (a request for a cert; has status, identifiers, expires)
        └── Authorization  (one per identifier; has status, challenges[])
              └── Challenge  (HTTP-01 | DNS-01 | TLS-ALPN-01 | ...)
                    [status: pending -> processing -> valid/invalid]
        └── Certificate  (returned once all authorizations are valid)
```

Each object has a URL returned by the server. Clients do not invent URLs — they're discovered through the directory endpoint and `Location` headers on responses.

| Object         | Created by   | Key fields                                          |
|----------------|--------------|-----------------------------------------------------|
| Account        | Client       | status, contact[], orders, termsOfServiceAgreed     |
| Order          | Client       | status, expires, identifiers[], authorizations[], finalize, certificate |
| Authorization  | Server       | status, expires, identifier, wildcard, challenges[] |
| Challenge      | Server       | status, type, token, url, error                     |
| Certificate    | Server       | chain of PEM certs returned at the order's cert URL |

### Object state machines

```
Order:        pending -> ready -> processing -> valid  (or -> invalid)
Authorization:pending -> processing -> valid  (or -> invalid)
Challenge:    pending -> processing -> valid  (or -> invalid)
Account:      valid  -> deactivated -> revoked
                  (or) -> unknown (deletion)
```

A subtle RFC 8555 detail: the server *tells the client* which state to move to via the `status` field; the client does not write status. The client "advances" challenges by POSTing an empty JSON `{}` (with a signature) to the challenge URL.

## The account key

The account key is the client's identity. It's an asymmetric keypair (ECDSA P-256, RSA-2048+, or Ed25519) whose private key you store locally — typically in `/etc/letsencrypt/accounts/.../private_key.json` for certbot. Every ACME request is signed with this key.

A new account registration (the `newAccount` endpoint) sends the public key in the JWS header's `jwk` field and an optional `contact` list (e.g., `mailto:ops@example.com`). Subsequent requests reference the account via the server-assigned `kid` URL in the JWS header instead of `jwk`. The two modes are mutually exclusive:

- **`jwk` mode** — for the very first `newAccount`/`revocation` requests when no `kid` exists yet.
- **`kid` mode** — for all subsequent requests; the JWS header includes `"kid": "https://acme-v02.api.letsencrypt.org/acme/acct/12345"`.

### JWS nonce replay protection

Every ACME JWS carries a `nonce` header. The server issues nonces via the `newNonce` endpoint and a `Replay-Nonce` HTTP header on every response. A nonce is single-use; reusing it returns `urn:ietf:params:acme:error:badNonce`. The full JWS protected header for an authenticated request:

```json
{
  "alg": "ES256",
  "kid": "https://acme-v02.api.letsencrypt.org/acme/acct/12345",
  "nonce": "0001agkijTQ3X9_ZH-...",
  "url": "https://acme-v02.api.letsencrypt.org/acme/order/123/abc"
}
```

## End-to-end issuance flow

```
Client                                                 Let's Encrypt API
  | 1. GET /directory                                                    |
  | <---- directory with newNonce, newAccount, newOrder URLs              |
  | 2. HEAD /newNonce                                                    |
  | <---- Replay-Nonce header                                            |
  | 3. POST /newAccount  (JWS signed with jwk, contact=mailto:...)        |
  | <---- 201 Created, Location: acct URL, kid returned                  |
  | 4. POST /newOrder   {identifiers: [{type:dns, value:example.com}]}   |
  | <---- 201 Created, order URL + authorizations[] URLs + finalize URL  |
  | 5. POST /authz/123   (empty payload, signed)                          |
  | <---- 200 OK, identifier + challenges[] (http-01, dns-01, ...)       |
  | 6. Choose challenge; satisfy it (drop token at /.well-known/...);    |
  |    POST /chall/abc  (empty {} payload) -> server sets processing     |
  | <---- 200 OK, challenge status=processing                            |
  |       ... server polls the challenge URL (HTTP GET to /.well-known)   |
  | <---- (after verify) challenge status=valid                          |
  | 7. POST /finalize-order  {csr: base64url(der CSR)}                   |
  | <---- 200 OK, order status=processing                                |
  | 8. Retry-as-needed (sleep + poll order URL)                          |
  | <---- 200 OK, order status=valid, certificate URL                    |
  | 9. POST-as-GET /cert/abc  (signed JWS, empty payload)                |
  | <---- 200 OK, application/pem-certificate-chain                      |
  |    -- leaf + intermediate(s) concatenated                            |
```

The "POST-as-GET" idiom (step 9) is an ACME quirk: GET requests aren't signed, so RFC 8555 mandates that *every read* be a POST with an empty payload (`{}`) so the JWS signature authenticates the request.

## The three challenges

### HTTP-01

The CA proves domain control by fetching `http://<domain>/.well-known/acme-challenge/<token>` over port 80 and verifying it equals `token + "." + thumbprint(account_key)`.

The `token` is provided by the server in the challenge object. The `key authorization` value is `<token>.<base64url(JWK_thumbprint)>` — the SHA-256 hash of the JWK. The client must serve exactly this string at the well-known URL.

Constraints:
- Only works on port 80 (not 443, not 8080).
- Server follows redirects up to 10 hops; the first hop must be to `http://` (not `https://`).
- Domain must be a hostname (not a wildcard).
- No IPv6-only domains: the verifier fetches both A and AAAA records.

### DNS-01

The client publishes a TXT record at `_acme-challenge.<domain>` whose value is `base64url(SHA-256(<token>.<thumbprint>))`. The CA queries public DNS.

```
_acme-challenge.example.com.  IN TXT  "kGM8Nf1JYfF9...base64url encoded..."
```

Constraints:
- Works for wildcards (`*.example.com`) — the only ACME challenge type that does.
- TXT record may be multiple strings (DNS TXT records can be split into ≤255-char chunks); CA reconstructs them.
- Slow propagation: Cloudflare/Route53 publish fast, but slower authoritative servers can take minutes to reflect updates, which is why ACME clients retry with backoff.
- The CA queries authoritative DNS (often via Google's `8.8.8.8` or Cloudflare's `1.1.1.1`), not the domain's own resolver.

### TLS-ALPN-01 (RFC 8737)

The client terminates TLS on port 443 of the target domain with a special ALPN protocol `acme-tls/1` and presents a self-signed certificate whose Subject Alternative Name `otherName` field contains `SHA-256(<token>.<thumbprint>)`. The CA connects, negotiates `acme-tls/1` via the TLS handshake, and validates the SAN `otherName`.

```
Client                                              Let's Encrypt
  | TLS ClientHello, ALPN=[acme-tls/1]                   |
  | ---------------------------------------------------> |
  | TLS ServerHello, ALPN=acme-tls/1, self-signed cert   |
  | <--------------------------------------------------- |
  |                                                       | inspect SAN otherName,
  |                                                       | compare to expected hash
  |                                                       | -> mark challenge valid
```

Constraints:
- Works on port 443, no HTTP request made.
- Requires the client to terminate TLS on the target host (can't be satisfied via a generic webserver; need a special listener like `acme-tls-alpn-proxy` or `certbot --preferred-challenges tls-alpn-01`).
- Wildcards not supported.

## Worked example: minimal HTTP-01 client

```python
import base64
import hashlib
import json
import time
import urllib.request
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.hashes import SHA256


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def jwk_thumbprint(jwk: dict) -> str:
    """RFC 7638 thumbprint: SHA-256 of the canonical JSON of {e,kty,n} or {crv,kty,x,y}."""
    canonical = json.dumps(jwk, separators=(",", ":"), sort_keys=True).encode()
    return b64url(hashlib.sha256(canonical).digest())


def account_public_jwk(priv: ec.EllipticCurvePrivateKey) -> dict:
    """RFC 7517 JWK for a P-256 key."""
    nums = priv.public_key().public_numbers()
    return {
        "crv": "P-256",
        "kty": "EC",
        "x": b64url(nums.x.to_bytes(32, "big")),
        "y": b64url(nums.y.to_bytes(32, "big")),
    }


def key_authorization(token: str, jwk: dict) -> str:
    return f"{token}.{jwk_thumbprint(jwk)}"


def http01_well_known_path(token: str, jwk: dict) -> str:
    """The full path the CA will GET to satisfy HTTP-01."""
    return f"/.well-known/acme-challenge/{token}", key_authorization(token, jwk)


# --- end-to-end at a high level (signing omitted for brevity) ---

def issue_cert_http01(domain: str, account_priv: ec.EllipticCurvePrivateKey,
                      directory_url: str = "https://acme-v02.api.letsencrypt.org/directory"):
    jwk = account_public_jwk(account_priv)

    # 1. Fetch the directory to discover endpoint URLs
    directory = json.load(urllib.request.urlopen(directory_url))

    # 2. Create an account (JWS with jwk header, not kid, since none exists)
    #    -- skipped: signed POST to directory["newAccount"], returns Location header

    # 3. Place an order
    #    -- signed POST to directory["newOrder"] with body:
    new_order_body = {
        "identifiers": [{"type": "dns", "value": domain}],
    }
    # server response: {status:"pending", authorizations:["https://.../authz/123"], finalize:"https://.../finalize/abc"}

    # 4. Fetch the authorization to learn challenge tokens
    # authz = signed POST to the authorization URL with empty payload {}
    #   -> {status:"pending", identifier:{type:"dns", value:domain},
    #       challenges:[{type:"http-01", token:"random-token-here", url:"https://.../chall/abc"}]}

    http01_challenge = None  # would be filled from authz
    token = ""               # extracted from http01_challenge
    path, content = http01_well_known_path(token, jwk)
    # 5. Operator now serves `content` at `http://<domain><path>`.
    #    In real clients this is done by writing the file or running a temp HTTP server.

    # 6. Tell the server to verify: POST {} to http01_challenge["url"]
    #    -> server status: pending -> processing -> valid (poll the URL)

    # 7. Build a CSR (omitted), POST to order's finalize URL
    #    -> order status: processing -> valid

    # 8. POST-as-GET to order["certificate"] URL to download PEM chain
    return jwk, path, content, new_order_body
```

The exact JWS signing is deliberately not shown here — it's ~40 lines of base64url + DER + ECDSA code that conflates the conceptual flow. Real clients use libraries like `acme` (Python, the same lib certbot uses) or `acme-client`/`golang.org/x/crypto/acme`.

## Rate limits (Let's Encrypt production)

These are the most-asked limits. They evolve — the authoritative source is https://letsencrypt.org/docs/rate-limits/.

| Limit                              | Value (2024)                          | Notes                                       |
|------------------------------------|----------------------------------------|----------------------------------------------|
| Certificates per Registered Domain | 50 / week                              | "Registered Domain" = eTLD+1, e.g., `example.com` covers `a.example.com`, `b.example.com` |
| Duplicate certificates             | 5 / week                               | Identical set of names                       |
| Failed validations                 | 5 / account / hostname / hour          | Failed HTTP-01, DNS-01, etc.                 |
| Pending authorizations             | 300 / account                          | Authorizations not yet satisfied             |
| New orders                         | 300 / 300s (rolling)                   | Hard limit on order creation                 |
| New registrations per IP           | 10 / 3 hours                           | Slows farming                                |
| New orders per IP                  | 1000 / 3 hours                         | Slows automation abuse                       |

For staging, all these limits are much higher (e.g., 30,000 / week per registered domain) — use `https://acme-staging-v02.api.letsencrypt.org/directory` for testing.

A common operational mistake is hitting the "Duplicate certificate" limit by re-issuing the same cert repeatedly from cron. The fix is to renew only when the cert is within 30 days of expiry (which is what certbot's `--deploy-hook` and systemd timer do by default).

## Wildcard certificates

A wildcard cert (`*.example.com`) covers exactly one label (`a.example.com` works, `b.c.example.com` doesn't, `example.com` itself doesn't — you must request both `*.example.com` and `example.com` as separate SANs in the same order).

Per ACME spec, wildcard identifiers get a different challenge type — they **must** be DNS-01. The reason is HTTP-01 has no way to prove control of `*.example.com` since you'd need to demonstrate control of every possible subdomain simultaneously. With DNS-01, control of the zone apex proves control of all its subdomains.

Wildcard is requested in the order:

```json
{
  "identifiers": [
    {"type": "dns", "value": "*.example.com"},
    {"type": "dns", "value": "example.com"}
  ]
}
```

The corresponding authorization object has `"wildcard": true` for the first identifier. The `_acme-challenge` TXT record is published at `_acme-challenge.example.com` (not `*._acme-challenge`).

## Let's Encrypt vs commercial CAs

| Property                    | Let's Encrypt                       | Commercial CA (DigiCert, Sectigo, GlobalSign)            |
|-----------------------------|--------------------------------------|-----------------------------------------------------------|
| Domain validation (DV)      | Free, automated                       | Usually paid, sometimes manual                            |
| OV (Organization Validation)| Not offered                          | Offered; CA verifies org identity via Dun & Bradstreet   |
| EV (Extended Validation)     | Not offered                          | Being deprecated by CA/Browser Forum (Chrome dropped EV UI in 2019) |
| Wildcard                    | Free (DNS-01 only)                   | Paid; usually DNS or HTTP proof                          |
| Multi-domain (SAN)          | 100 SANs per cert                     | Varies; pricing per SAN                                   |
| Validity                    | 90 days                              | 1 year (397 days post-2025 Baseline Requirements cap)    |
| Customer support            | Community forum only                 | Phone/email SLAs                                          |
| Insurance / warranty         | None                                 | $10K–$1.5M per cert                                       |
| Internal CA / private PKI    | No (publicly trusted only)           | Some offer private CA managed services                    |
| Code signing / S/MIME         | No                                   | Yes (separate products)                                   |

The choice usually comes down to: do you need *organizational identity* in the cert (use OV from a commercial CA) or just *domain control* (Let's Encrypt is fine)? For 95% of web workloads, DV suffices and Let's Encrypt is operationally simpler.

## Operational notes

- **CAA records**: Let's Encrypt respects DNS CAA records (RFC 8659). If you publish `caa issueletsencrypt.org`, only Let's Encrypt may issue; `caa issue ";"` blocks all CAs. Useful for defense-in-depth against mis-issuance.
- **Account key rotation**: ACME supports `key change` (RFC 8555 §7.3.5) — POST a JWS signed by both the old and new keys. certbot has `--account-key-rotate`; do this if a key is compromised.
- **Revocation**: ACME clients can revoke their own certs via the `revocation` endpoint. Let's Encrypt only allows revocation by the cert's subscriber (account holder) or the issuing CA, not third parties.
- **External account binding (EAB)**: For some CAs (notably ZeroSSL), new accounts require an HMAC binding to a pre-shared MAC key. Used by some private CAs to gate account creation.

## References

- RFC 8555 — Automatic Certificate Management Environment (ACME) — https://www.rfc-editor.org/rfc/rfc8555
- RFC 8737 — ACME-TLS-ALPN challenge — https://www.rfc-editor.org/rfc/rfc8737
- RFC 8659 — DNS CAA Resource Record — https://www.rfc-editor.org/rfc/rfc8659
- RFC 7638 — JSON Web Key (JWK) Thumbprint — https://www.rfc-editor.org/rfc/rfc7638
- RFC 7515 — JSON Web Signature (JWS) — https://www.rfc-editor.org/rfc/rfc7515
- Let's Encrypt documentation — https://letsencrypt.org/docs/
- Let's Encrypt rate limits — https://letsencrypt.org/docs/rate-limits/
- Let's Encrypt "How it works" — https://letsencrypt.org/how-it-works/
- certbot documentation — https://eff-certbot.readthedocs.io/
- ACME working group archives — https://datatracker.ietf.org/group/acme/documents/
- Python `acme` library (certbot's ACME client) — https://github.com/certbot/certbot/tree/master/acme
- ISRG engineering blog — https://letsencrypt.org/blog/

## Interview Questions

1. **Explain the difference between `jwk` and `kid` JWS headers in ACME. When is each used?**
2. **Why does ACME require POST-as-GET for read operations instead of plain GET?**
3. **Walk through HTTP-01 challenge. What value is served at the well-known URL, and how is it computed?**
4. **Why must wildcard certificates be validated via DNS-01 and not HTTP-01?**
5. **What is the role of the nonce in ACME, and what happens on replay?**
6. **You're hitting "duplicate certificate" rate limits. What's the operational fix?**
7. **Compare Let's Encrypt 90-day certs to a commercial CA's 1-year certs. What are the security and operational tradeoffs?**
8. **What is TLS-ALPN-01, and what server-side changes does it require?**
9. **How does a CAA record interact with ACME issuance?**
10. **What does `key change` mean in ACME, and when would you use it?**
