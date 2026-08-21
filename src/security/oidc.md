# OpenID Connect (OIDC)

OpenID Connect (OIDC) is an identity layer built on top of OAuth 2.0, standardized by the OpenID Foundation in 2014 ( OIDC Core 1.0 ). It adds an ID Token (a signed JWT) to the OAuth 2.0 authorization flow, providing authentication in addition to OAuth's authorization. This page covers the protocol, the ID Token structure, the discovery and metadata endpoints, and the relationship between OIDC and OAuth 2.0.

## The OIDC vs OAuth 2.0 Distinction

OAuth 2.0 (RFC 6749) is an authorization framework: it defines how a client obtains an access token that grants permission to access a resource. It does **not** define how the resource server authenticates the user.

OIDC adds authentication on top:

- **OAuth 2.0**: client gets `access_token` → can call API as user.
- **OIDC**: client gets `access_token` + `id_token` → can call API as user AND know who the user is.

The `id_token` is a JWT (JSON Web Token) signed by the OpenID Provider (OP), containing claims about the user (subject, email, name, etc.).

## The Authorization Code Flow with PKCE

The most common OIDC flow for web apps and mobile apps:

```text
1. Client → OP: Redirect to https://op.example.com/authorize
   Query:  response_type=code
            client_id=...
            redirect_uri=https://app.example.com/callback
            scope=openid profile email
            state=<random>
            nonce=<random>
            code_challenge=<hash-of-verifier>
            code_challenge_method=S256

2. User authenticates to OP (e.g., password + MFA).

3. OP → Client: Redirect to redirect_uri
   Query:  code=<authorization-code>
            state=<echoed-from-step-1>

4. Client → OP: POST https://op.example.com/token
   Body:   grant_type=authorization_code
            code=<code>
            redirect_uri=<echoed>
            client_id=...
            code_verifier=<verifier>

5. OP verifies code + code_verifier (must match the challenge).
   OP returns:
   {
     "access_token": "...",
     "id_token": "<JWT>",
     "refresh_token": "...",  // optional, if offline_access scope
     "expires_in": 3600,
     "token_type": "Bearer"
   }
```

The `code_challenge` / `code_verifier` pair (PKCE, RFC 7636) prevents an attacker who intercepts the authorization code (e.g., via a malicious app on the same device) from exchanging it for tokens. The client sends `code_challenge = SHA256(code_verifier)` in step 1; the OP requires `code_verifier` in step 4 and validates that `SHA256(code_verifier) == code_challenge`.

PKCE is mandatory for mobile and SPA clients (per OAuth 2.1 draft) and recommended for all clients.

## The ID Token

The `id_token` is a JWT with three parts:

```text
eyJhbGciOiJSUzI1NiIsImtpZCI6Ik...  ← header
.eyJpc3MiOiJodHRwczovL29wLmV4...  ← payload (claims)
.SflKxwRJSMeKKpadsTiopQRSTUVWXYZ  ← signature
```

Decoded header:
```json
{
  "alg": "RS256",
  "kid": "key-1",
  "typ": "JWT"
}
```

Decoded payload (the ID Token claims):
```json
{
  "iss": "https://op.example.com",
  "sub": "alice123",
  "aud": "client-123",
  "exp": 1692620400,
  "iat": 1692616800,
  "nonce": "abc123",
  "auth_time": 1692616700,
  "acr": "urn:mace:incommon:iap:silver",
  "amr": ["mfa", "pwd"],
  "email": "alice@example.com",
  "email_verified": true,
  "name": "Alice Adams",
  "picture": "https://op.example.com/alice.png"
}
```

Standard OIDC claims:

| Claim | Meaning |
|-------|---------|
| `iss`       | Issuer URL (the OP's identifier) |
| `sub`       | Subject identifier (unique per user per OP) |
| `aud`       | Audience (the client_id of the intended recipient) |
| `exp`       | Expiration time (Unix timestamp) |
| `iat`       | Issued at time |
| `nonce`     | Echoed from step 1; prevents replay |
| `auth_time` | When the user authenticated (Unix timestamp) |
| `acr`       | Authentication Context Class Reference (level of auth) |
| `amr`       | Authentication Methods References (e.g., ["mfa", "pwd"]) |
| `email`     | User's email |
| `email_verified` | Whether the email was verified |
| `name`      | Display name |
| `picture`   | Avatar URL |

The ID Token is signed by the OP using its private key (RS256 is the most common algorithm). Clients verify the signature using the OP's public key, obtained from the OP's discovery endpoint.

## Discovery and JWKS

OIDC defines a standard discovery mechanism. The OP publishes its configuration at `https://op.example.com/.well-known/openid-configuration`:

```json
{
  "issuer": "https://op.example.com",
  "authorization_endpoint": "https://op.example.com/authorize",
  "token_endpoint": "https://op.example.com/token",
  "userinfo_endpoint": "https://op.example.com/userinfo",
  "jwks_uri": "https://op.example.com/.well-known/jwks.json",
  "response_types_supported": ["code", "id_token"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "subject_types_supported": ["public", "pairwise"],
  "id_token_signing_alg_values_supported": ["RS256", "ES256"],
  "scopes_supported": ["openid", "profile", "email", "offline_access"]
}
```

Clients fetch this document once at startup and use it to discover the OP's endpoints and supported algorithms.

The `jwks_uri` points to the OP's JSON Web Key Set (JWKS) — a JSON document containing the public keys the OP uses to sign tokens:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "key-1",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "kid": "key-2",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

Each ID Token's `kid` header identifies which key was used; the client fetches the JWKS and finds the matching key.

## Key Rotation

Production OPs rotate signing keys periodically (e.g., monthly). The rotation process:

1. OP generates a new key pair.
2. OP adds the new public key to JWKS (alongside the old key).
3. OP starts signing new ID Tokens with the new key.
4. OP removes the old key from JWKS after all issued ID Tokens with the old key have expired (typically 24 hours).

Clients must re-fetch the JWKS periodically (e.g., every hour) to pick up new keys. If a client has a stale JWKS cache and tries to validate a token signed with a new key, validation fails. Most OIDC libraries handle this automatically.

## The Userinfo Endpoint

The ID Token contains claims, but the user's profile data may change between token issuance and use. The `userinfo_endpoint` is a REST endpoint where the client can exchange an access token for the current user's claims:

```http
GET /userinfo HTTP/1.1
Host: op.example.com
Authorization: Bearer <access_token>
```

Response (JSON):
```json
{
  "sub": "alice123",
  "email": "alice@example.com",
  "email_verified": true,
  "name": "Alice Adams",
  "picture": "https://op.example.com/alice.png"
}
```

The userinfo endpoint is OPTIONAL per OIDC Core. Many OPs provide it; many apps use the ID Token's claims directly without calling userinfo (the ID Token is signed, so its claims are trusted; userinfo is for fresh data).

## The Implicit Flow (Deprecated)

OIDC also defined the "Implicit Flow" where the ID Token is returned directly in the redirect URL (no code exchange). This was designed for browser-only SPAs that couldn't keep a secret. With PKCE now mandatory and refresh tokens being safe to store in SPAs, the Implicit Flow is deprecated in OAuth 2.1 and the OIDC Best Current Practice.

## OIDC vs SAML

| Aspect | OIDC | SAML 2.0 |
|--------|------|----------|
| Encoding | JSON / JWT | XML |
| Discovery | `.well-known/openid-configuration` | Metadata URL or out-of-band |
| Browser flow | Authorization Code + PKCE | Web Browser SSO |
| API auth | Bearer tokens | Awkward (SAMLBearer) |
| Mobile apps | Excellent (PKCE) | Awkward |
| Enterprise deployment | Newer, growing | Mature, dominant in enterprise |
| IdP-initiated SSO | Awkward | Native |
| Modern libraries | JSON-native (everywhere) | XML-heavy |

For new deployments, OIDC is the recommended choice. For existing enterprise SSO, SAML remains dominant.

## Production OpenID Providers

- **Auth0** (Okta): cloud-hosted, dev-friendly.
- **Keycloak** (Red Hat): open-source, Java-based.
- **Okta**: cloud-hosted, enterprise-focused.
- **Microsoft Entra ID** (formerly Azure AD): Microsoft's cloud IdP.
- **Google Identity Platform**: cloud-hosted.
- **Authentik** (open-source, Python): newer alternative to Keycloak.
- **Ory** (open-source, Go): cloud-native, more opinionated.

## Common Pitfalls

1. **Not using PKCE.** Without PKCE, an attacker who intercepts the authorization code (e.g., via a malicious app's custom URL handler on mobile) can exchange it for tokens. Always use PKCE.

2. **Verifying only the JWT signature, not the claims.** A token signed by the OP is "authentic", but if `aud` doesn't match your client_id or `exp` is in the past, it's not valid for your app.

3. **Forgetting to validate `nonce`.** The `nonce` claim in the ID Token must match the `nonce` you sent in step 1. Without this, a token issued for a different session can be replayed.

4. **Using `id_token` for API authorization.** The ID Token is for the client to identify the user; it's not for the resource server. Use the `access_token` for API calls.

5. **Trusting claims without `email_verified`.** The `email` claim may be the user's email but is not verified unless `email_verified: true`. Don't trust unverified emails for password resets or sensitive operations.

6. **Storing access tokens in localStorage.** SPAs that store tokens in localStorage are vulnerable to XSS attacks that exfiltrate tokens. Use HttpOnly cookies with backend-mediated OAuth, or follow the BCP for SPA token handling.

## References

- [OpenID Connect Core 1.0 specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [OpenID Connect Discovery](https://openid.net/specs/openid-connect-discovery-1_0.html)
- [OAuth 2.0 PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [OAuth 2.1 (draft)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)
- [Auth0 OIDC documentation](https://auth0.com/docs/authenticate/protocols/openid-connect-protocol)
- [Keycloak documentation](https://www.keycloak.org/documentation)
- [OAuth 2.0 Security Best Current Practice (RFC 9700)](https://datatracker.ietf.org/doc/html/rfc9700)
