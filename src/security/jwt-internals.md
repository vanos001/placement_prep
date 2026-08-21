# JWT Internals

JSON Web Tokens (JWT, RFC 7519) are a compact, URL-safe token format for representing claims between two parties. They are the foundation of OAuth 2.0 access tokens, OIDC ID tokens, and many session-token implementations. This page covers the structure, the JSON Web Signature (JWS) layer, the JSON Web Encryption (JWE) layer, and the security considerations that have made JWTs both ubiquitous and a frequent source of vulnerabilities.

## The Three-Part Structure

A JWS JWT has three base64url-encoded parts separated by dots:

```text
eyJhbGciOiJSUzI1NiIsImtpZCI6ImtleS0xIn0.eyJzdWIiOiJhbGljZSIsImlhdCI6MTY5MjYxNjgwMH0.SflKxwRJ...
└─────────────── header ──────────┘ └────────── payload ──────────┘ └─ signature ─┘
```

The header and payload are JSON objects base64url-encoded. The signature depends on the algorithm:

- **HMAC (HS256, HS384, HS512)**: `signature = HMAC-SHA(key, header || "." || payload)`. Symmetric key; signer and verifier share the same secret.
- **RSASSA-PKCS1-v1_5 (RS256, RS384, RS512)**: `signature = RSAPrivateKey.sign(SHA256(header || "." || payload))`. Asymmetric; signer holds private key, verifier uses public key.
- **ECDSA (ES256, ES384, ES512)**: elliptic curve signatures. Asymmetric.
- **RSASSA-PSS (PS256, PS384, PS512)**: probabilistic RSA signature. Asymmetric.
- **EdDSA (EdDSA)**: Ed25519 signature. Asymmetric.
- **none** (RFC 7519, but disabled in practice): no signature. Used for testing only.

## The Header

The header is a JSON object describing how the token was signed:

```json
{
  "alg": "RS256",
  "kid": "key-1",
  "typ": "JWT"
}
```

- `alg`: the signing algorithm.
- `kid`: key ID, used to look up the right verification key.
- `typ`: token type (almost always "JWT").

Other header fields include `cty` (content type, for nested JWTs) and `x5u`/`x5c` (X.509 certificate URL/embedded).

## The Payload (Claims)

The payload contains claims — JSON name/value pairs about the user, the token, and the issuer. Standard claims (RFC 7519):

| Claim | Abbrev | Meaning |
|-------|--------|---------|
| `iss`     | issuer | Issuer URL or identifier |
| `sub`     | subject | Subject (user) identifier |
| `aud`     | audience | Intended recipient (client_id) |
| `exp`     | expiration | Expiration time (Unix timestamp) |
| `nbf`     | not before | Validity start time |
| `iat`     | issued at | Issuance time |
| `jti`     | JWT ID | Unique token identifier (for revocation) |

OIDC adds user-identity claims (`email`, `name`, `picture`) and authentication claims (`nonce`, `auth_time`, `amr`).

Custom claims can be anything:

```json
{
  "iss": "https://api.example.com",
  "sub": "user-12345",
  "aud": "client-67890",
  "exp": 1692620400,
  "iat": 1692616800,
  "jti": "9c2f3a7e-1b5d-4f8e-9c0a-2b3c4d5e6f7a",
  "scope": "read:orders write:orders",
  "roles": ["admin", "billing"],
  "company_id": 42
}
```

## Signature Verification

The verifier reconstructs the signed message (`header || "." || payload`), looks up the verification key by `kid`, and verifies the signature:

```python
import jwt  # PyJWT

public_key = jwks_client.get_signing_key(header["kid"]).key
try:
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],  # CRITICAL: whitelist the algorithm
        audience="client-67890",
        issuer="https://api.example.com",
    )
except jwt.InvalidTokenError as e:
    raise AuthError(e)
```

The `algorithms=` parameter is critical: by default, many libraries accept whatever algorithm the header declares, which is the "alg: none" attack vector. Always whitelist the algorithms your application expects.

## The `alg: none` Attack

The most famous JWT vulnerability: an attacker changes the header to `{"alg": "none"}` and removes the signature. A vulnerable library skips signature verification and accepts the token.

```text
Original:
eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZG1pbiJ9.SflKxwRJ...

Forged (alg=none, no signature):
eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.
                  ↑───────────┘   ↑
                  alg=none        empty signature
```

Libraries that don't whitelist algorithms will accept this and authenticate as admin. Mitigation: always pass `algorithms=["RS256", ...]` to verify.

This attack affected early versions of `node-jsonwebtoken`, `python-jwt`, and `java-jwt`. Most have been fixed; new code must use the explicit algorithm whitelist.

## The `alg: HS256` Confusion Attack

If a server accepts both HS256 (symmetric) and RS256 (asymmetric) tokens, an attacker can forge an HS256 token using the server's RS256 public key as the HMAC secret:

```text
1. Server's RS256 public key is publicly known (from JWKS).
2. Attacker creates header: {"alg": "HS256", "kid": "key-1"}.
3. Attacker creates payload: {"sub": "admin", ...}.
4. Attacker computes: signature = HMAC-SHA256(public_key, header.payload).
5. Server uses public_key (the RS256 verification key) as HMAC secret,
   verifies the signature — match!
```

This works because the server's verification code uses the same key for both algorithms. Mitigation: never accept both HS256 and RS256 on the same endpoint, and explicitly tag which key is for which algorithm.

## The JSON Web Encryption (JWE) Layer

JWE (RFC 7516) encrypts the payload instead of signing it. The token has five parts:

```text
eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..HKBhXM...sfaJw.5VyZq1...tKWcC.kn0...
└─ protected header ─┘ └─ encrypted key ─┘ └─ IV ─┘ └─ ciphertext ─┘ └─ tag ┘
```

JWE tokens are encrypted with a Content Encryption Key (CEK), which is itself encrypted with a Key Encryption Key (KEK). The KEK is either a shared secret (direct mode), an RSA public key, an ECDH-derived key, or a key wrapped by another symmetric key.

JWE tokens are used when the claims must be confidential (e.g., a JWT carrying a credit card number to a payment processor). They are uncommon in OIDC because the ID Token's claims are not sensitive (sub, email, name).

JWE is rarely used in production. Most "JWT" tokens are JWS (signed, not encrypted). When encryption is needed, TLS is the standard layer.

## JWT vs Reference Tokens

A JWT is a **self-contained** token: the verifier can extract all claims without contacting the issuer. This is great for performance and offline validation but bad for revocation (a stolen token is valid until `exp`).

A **reference token** is an opaque string (e.g., `abc123`). The verifier must send it to the issuer's introspection endpoint to learn what it grants. This enables immediate revocation but adds latency.

Production systems use a hybrid:
- Access tokens: short-lived JWTs (5 minutes). If stolen, they expire fast.
- Refresh tokens: long-lived reference tokens (30 days). Revocable via the introspection endpoint.

## Token Revocation

JWTs cannot be revoked without contacting the issuer. Workarounds:

1. **Short expiration**: 5-minute access tokens. Stolen tokens become useless quickly.
2. **Revocation list**: the issuer publishes a list of revoked `jti`s; verifiers check against it.
3. **Reference tokens**: use a reference token instead, revocable via the introspection endpoint.
4. **Token binding** (RFC 8471, deprecated): bind the token to the TLS session, so a stolen token from a different TLS session is invalid.

## Production Use Cases

- **OAuth 2.0 access tokens**: most OPs issue JWTs as access tokens (Auth0, Keycloak, Okta).
- **OIDC ID tokens**: always JWTs.
- **Session tokens**: some web apps use JWTs as session cookies. The trade-off: stateless (no DB lookup) vs. revocable (hard). Most production session systems use opaque session IDs + DB lookup.
- **API auth**: JWTs with `scope` claims are common for API authorization.
- **Microservice auth**: service-to-service authentication with short-lived JWTs (SPIFFE, AWS IAM Roles for Service Accounts).

## Common Pitfalls

1. **Accepting `alg: none`.** Always whitelist algorithms explicitly.

2. **Accepting multiple algorithms with shared keys.** Don't use the same key for HS256 and RS256 — the confusion attack gives an attacker the signing key.

3. **Long-lived JWTs without revocation.** A 24-hour access token is too long if it can be stolen. Use 5-minute access tokens + refresh tokens.

4. **Putting sensitive data in the payload.** JWT payloads are base64-encoded (not encrypted). Anyone with the token can read the payload. Use JWE for sensitive data, or don't put it in a JWT at all.

5. **Not validating `aud`.** A token issued for client A may be valid for client B if you don't check `aud`. Always verify `aud` matches your client_id.

6. **Trusting `iat` over `exp`.** The `iat` (issued at) tells you when the token was created; `exp` tells you when it expires. Use `exp` for validity, not `iat + some-duration`.

7. **Clock skew issues.** If your server's clock is 60 seconds ahead of the issuer's, tokens with `exp` in the future look expired. Allow a clock skew (e.g., 30 seconds) in the validation library.

8. **JWTs as session tokens in cookies.** A JWT in a cookie is vulnerable to CSRF unless used with `SameSite=Strict` or `SameSite=Lax` and proper CSRF tokens. The HttpOnly flag prevents JS access but doesn't prevent CSRF.

## References

- [RFC 7519: JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [RFC 7515: JSON Web Signature (JWS)](https://datatracker.ietf.org/doc/html/rfc7515)
- [RFC 7516: JSON Web Encryption (JWE)](https://datatracker.ietf.org/doc/html/rfc7516)
- [JWT.io — interactive JWT debugger](https://jwt.io)
- [PyJWT (Python library)](https://github.com/jpadilla/pyjwt)
- [JWT Best Current Practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725)
- [Critical vulnerabilities in JSON Web Token libraries](https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/) (Auth0 blog)
- [OWASP JWT cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
