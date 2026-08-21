# OAuth 2.0 Internals

OAuth 2.0 is the industry-standard authorization framework, defined in RFC 6749 (2012). It allows a user to grant a third-party application access to their resources on another service (e.g., "let this app access my Google Drive") without sharing their password. This page covers the framework, the grant types (flows), the token model, and the production security considerations.

## The Four Roles

```text
┌────────────────┐                ┌──────────────────┐
│ Resource Owner  │                │  Client (app)     │
│  (the user)      │ ←──────────→  │                   │
└────────────────┘                └──────────────────┘
                                            │
                                            │ authorization request
                                            ▼
                            ┌──────────────────────────┐
                            │ Authorization Server       │
                            │  (OAuth provider, e.g.,   │
                            │   Google, Auth0)           │
                            └──────────────────────────┘
                                            │
                                            │ access token
                                            ▼
                            ┌──────────────────────────┐
                            │ Resource Server            │
                            │  (API provider)            │
                            └──────────────────────────┘
```

- **Resource Owner**: the user who owns the resources.
- **Client**: the third-party application that wants to access the user's resources.
- **Authorization Server**: issues access tokens after the user authorizes.
- **Resource Server**: hosts the user's resources; accepts access tokens.

These can be on the same service (Google is both Authorization Server and Resource Server for Google Drive) or split (Auth0 as Authorization Server, your API as Resource Server).

## Grant Types (Flows)

OAuth 2.0 defines multiple grant types for different scenarios:

### 1. Authorization Code (the standard flow)

For web apps and native apps:

```text
1. User clicks "Sign in with Google" on the client.
2. Client redirects to: https://accounts.google.com/oauth/authorize
   ?client_id=...
   &redirect_uri=https://app.example.com/callback
   &response_type=code
   &scope=openid+email
   &state=CSRF_TOKEN
   &code_challenge=PKCE_CHALLENGE  ← required for SPA/mobile

3. User logs in to Google and authorizes.
4. Google redirects back to: https://app.example.com/callback?code=AUTH_CODE&state=CSRF_TOKEN

5. Client exchanges the auth code for tokens:
   POST https://oauth2.googleapis.com/token
   client_id=...
   client_secret=...  ← not used with PKCE
   code=AUTH_CODE
   grant_type=authorization_code
   code_verifier=PKCE_VERIFIER

6. Authorization Server returns:
   {
     "access_token": "...",
     "id_token": "...",  ← if OIDC
     "refresh_token": "...",  ← if offline_access
     "expires_in": 3600,
     "token_type": "Bearer"
   }
```

The two-step (code → token) is critical: the access token never goes through the browser (which might leak it via referrer headers, history, etc.).

### 2. Client Credentials

For machine-to-machine (no user involvement):

```text
POST https://oauth.example.com/token
grant_type=client_credentials
client_id=...
client_secret=...
scope=read:orders

Response: { "access_token": "...", "expires_in": 3600 }
```

Used for service-to-service authentication (no user). The "client" is a service account.

### 3. Refresh Token Grant

To get a new access token without re-authenticating the user:

```text
POST https://oauth.example.com/token
grant_type=refresh_token
refresh_token=...
client_id=...

Response: { "access_token": "...", "expires_in": 3600, "refresh_token": "..." }
```

Refresh tokens are long-lived (days to months); access tokens are short-lived (minutes). The client uses the refresh token to get new access tokens.

### 4. (Deprecated) Implicit Grant

For SPAs that couldn't keep a secret (pre-PKCE):

```text
GET https://oauth.example.com/authorize
response_type=token  ← access token returned in URL fragment
```

The access token was returned in the URL fragment (not query string, so it's not sent in referrer). But the token was visible to JavaScript, vulnerable to XSS.

OAuth 2.1 deprecates this flow; use Authorization Code + PKCE instead.

### 5. (Deprecated) Resource Owner Password Credentials

For trusted first-party apps:

```text
POST https://oauth.example.com/token
grant_type=password
username=user@example.com
password=...
client_id=...
```

The client sees the user's password — only acceptable for first-party clients. OAuth 2.1 deprecates this.

## PKCE (Proof Key for Code Exchange)

PKCE (RFC 7636) prevents authorization code interception:

```text
1. Client generates a random code_verifier (e.g., 43-128 chars).
2. Client computes code_challenge = SHA256(code_verifier) (or just code_verifier for plain).
3. Client sends code_challenge in the authorization request.
4. Authorization Server stores the code_challenge with the auth code.
5. Client receives the auth code.
6. Client sends the auth code + code_verifier to the token endpoint.
7. Authorization Server verifies SHA256(code_verifier) == code_challenge.
   If yes, returns tokens.
```

Without PKCE: an attacker who intercepts the auth code (e.g., from the redirect URL) can exchange it for tokens. With PKCE: the attacker doesn't have the code_verifier, so the exchange fails.

PKCE is mandatory for SPAs and mobile apps since OAuth 2.1. Recommended for all clients.

## Scopes

Scopes define what the access token can do:

```text
GET https://oauth.example.com/authorize?scope=read:orders+write:orders
```

Common scope patterns:
- `read:resource`, `write:resource`: per-resource access.
- `openid`, `profile`, `email`: OIDC scopes for user identity.
- `offline_access`: request a refresh token.
- `admin`: elevated privileges (rare; usually per-resource).

The resource server validates the token's scopes per request:
```python
@require_scope("write:orders")
def create_order():
    ...
```

## Bearer Tokens

OAuth 2.0 access tokens are "bearer" tokens — anyone with the token can use it. The token is sent in the `Authorization` header:

```http
GET /api/orders HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGc...
```

Bearer tokens have security implications:
- If intercepted, the attacker can use them until they expire.
- TLS is required; without it, the token is exposed.
- Tokens should be short-lived (1 hour max) to limit damage.

Alternatives: DPoP (Demonstrating Proof-of-Possession), mutual TLS bound tokens. These bind the token to a specific client (a public key or certificate), preventing use by interceptors.

## Token Validation

The resource server must validate the access token. Two approaches:

### Local Validation (JWT)

If the access token is a JWT signed by the authorization server, the resource server validates locally:
1. Parse the JWT.
2. Verify the signature (using the server's public key from JWKS).
3. Check `iss`, `aud`, `exp`, `iat`.
4. Check scopes (custom claim).

Fast (~1 ms), no network call. But: can't revoke (the token is valid until exp).

### Introspection (RFC 7662)

If the access token is opaque (random string), the resource server calls the authorization server's introspection endpoint:

```http
POST /introspect HTTP/1.1
Authorization: Basic ...
token=...

Response: {
  "active": true,
  "scope": "read:orders",
  "client_id": "myapp",
  "username": "alice",
  "exp": 1692620400
}
```

Slower (~50 ms network round-trip), but supports immediate revocation.

## Production Use Cases

### "Sign in with X"

The most common OAuth flow: users sign into your app using their Google/Facebook/GitHub accounts. Your app gets an access token to read the user's profile (or post on their behalf).

### Service-to-Service Auth

Microservices authenticate to each other via client credentials:
- Service A requests a token with `client_credentials` grant.
- Service B validates the token via JWT or introspection.

This is the basis of OAuth-based service mesh authentication (e.g., SPIFFE, OIDC tokens in mTLS).

### API Access for Third Parties

A platform (e.g., GitHub) exposes APIs; third-party apps request access via OAuth. Users authorize specific scopes; the third-party gets an access token for those scopes only.

## Common Pitfalls

1. **Forgetting PKCE for SPAs/mobile.** Without PKCE, the auth code can be intercepted. Always use PKCE for these clients.

2. **Forgetting that bearer tokens need TLS.** Without TLS, the token is exposed. Always use HTTPS for OAuth.

3. **Forgetting that access tokens expire.** The client must handle expired tokens (HTTP 401) by refreshing.

4. **Forgetting that refresh tokens are sensitive.** A leaked refresh token gives long-term access. Store refresh tokens securely (not in localStorage for SPAs).

5. **Forgetting to validate the `state` parameter.** The state protects against CSRF; the client must verify the state matches the one it sent.

6. **Forgetting to use the `aud` claim.** A token issued for client A shouldn't be accepted by client B. Validate the `aud` claim in the resource server.

7. **Confusing OAuth with OpenID Connect.** OAuth is authorization; OIDC is authentication built on top of OAuth. If you need to know "who the user is", use OIDC (the `id_token`).

## References

- [RFC 6749: OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7636: PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [RFC 7662: OAuth 2.0 Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662)
- [RFC 8252: OAuth 2.0 for Native Apps](https://datatracker.ietf.org/doc/html/rfc8252)
- [OAuth 2.1 (draft, the consolidated spec)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)
- [OAuth 2.0 Security Best Current Practice (RFC 9700)](https://datatracker.ietf.org/doc/html/rfc9700)
- [OAuth playground (OAuth.com)](https://www.oauth.com/playground/)
- [LWN: OAuth 2.0 overview (2020)](https://lwn.net/Articles/815575/)
