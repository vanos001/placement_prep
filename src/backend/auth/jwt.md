# JSON Web Tokens (JWT)

## What Is a JWT?

A **JSON Web Token (JWT)** is a compact, URL-safe token format for securely transmitting claims between two parties. JWTs are self-contained — the token itself carries all the information needed for verification, so the server doesn't need to look up the token in a database.

JWTs are defined by [RFC 7519](https://tools.ietf.org/html/rfc7519) and are the most widely used token format in modern authentication systems.

---

## JWT Structure

A JWT consists of three Base64URL-encoded parts separated by dots:

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEyMyIsIm5hbWUiOiJKb2huIERvZSJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
|___________Header____________|______________Payload________________|________________Signature________________|
```

### Header

Describes the token type and signing algorithm.

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

| Field | Description |
|-------|-------------|
| `alg` | Signing algorithm (HS256, RS256, ES256, etc.) |
| `typ` | Token type (always "JWT") |
| `kid` | Key ID — identifies which key was used (useful for key rotation) |

### Payload

Contains **claims** — statements about the entity (typically the user) and metadata.

```json
{
  "sub": "user-123",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "admin",
  "iat": 1700000000,
  "exp": 1700003600,
  "iss": "https://auth.example.com",
  "aud": "https://api.example.com"
}
```

### Registered Claims

| Claim | Name | Description |
|-------|------|-------------|
| `sub` | Subject | Who the token is about (user ID) |
| `iss` | Issuer | Who issued the token |
| `aud` | Audience | Who the token is intended for |
| `exp` | Expiration | When the token expires (Unix timestamp) |
| `nbf` | Not Before | Token is invalid before this time |
| `iat` | Issued At | When the token was issued |
| `jti` | JWT ID | Unique identifier for the token (prevents replay) |

### Signature

The signature ensures the token hasn't been tampered with. It's computed over the header and payload:

```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret
)
```

---

## Signing Algorithms

### Symmetric: HMAC (HS256, HS384, HS512)

```mermaid
flowchart LR
    ISS[Issuer] -->|sign with secret| JWT[JWT]
    VER[Verifier] -->|verify with same secret| JWT
    ISS -.->|shared secret| VER
```

- **HS256**: HMAC with SHA-256. One shared secret for signing and verification.
- **Pros**: Fast, simple.
- **Cons**: Both parties need the secret. If the verifier is compromised, an attacker can forge tokens.
- **Use case**: Internal services where you control both sides.

### Asymmetric: RSA (RS256, RS384, RS512)

```mermaid
flowchart LR
    ISS[Issuer] -->|sign with private key| JWT[JWT]
    VER[Verifier] -->|verify with public key| JWT
    ISS -.->|private key - secret| ISS
    ISS -.->|public key - shared| VER
```

- **RS256**: RSA with SHA-256. Private key signs, public key verifies.
- **Pros**: Only the issuer needs the private key. Public key can be widely distributed.
- **Cons**: Slower than HMAC. Key management is more complex.
- **Use case**: Third-party auth servers (Auth0, Okta), public APIs.

### Asymmetric: ECDSA (ES256, ES384, ES512)

- **ES256**: ECDSA with P-256 curve and SHA-256.
- **Pros**: Same security as RSA with smaller key sizes (256-bit EC ≈ 3072-bit RSA). Faster signing.
- **Cons**: Less tooling support than RSA.
- **Use case**: Mobile/IoT where bandwidth and computation matter.

### Algorithm Comparison

| Algorithm | Type | Key Size | Signature Size | Speed |
|-----------|------|----------|---------------|-------|
| HS256 | Symmetric | 256 bit | 32 bytes | Fastest |
| RS256 | Asymmetric (RSA) | 2048+ bit | 256 bytes | Slow |
| ES256 | Asymmetric (ECDSA) | 256 bit | 64 bytes | Fast |

---

## Refresh Tokens

Access tokens are short-lived (minutes to hours). **Refresh tokens** are long-lived credentials used to obtain new access tokens without re-authenticating the user.

### Token Lifecycle

```mermaid
flowchart TD
    LOGIN[User logs in] --> AT[Access Token - 15 min]
    LOGIN --> RT[Refresh Token - 7 days]
    AT -->|expires| REFRESH[Use Refresh Token]
    REFRESH --> NEWAT[New Access Token]
    REFRESH --> NEWRT[New Refresh Token - rotation]
    NEWAT --> USE[API calls]
    USE -->|expires| REFRESH2[Use new Refresh Token]
    RT -->|expired or revoked| LOGIN2[Re-authenticate]
```

### Implementation Pattern

```python
# Token refresh endpoint
@app.route('/auth/refresh', methods=['POST'])
def refresh():
    refresh_token = request.cookies.get('refresh_token')

    # Verify the refresh token
    payload = verify_refresh_token(refresh_token)
    if not payload:
        return jsonify({'error': 'Invalid refresh token'}), 401

    # Check if token has been revoked (token family tracking)
    if is_token_revoked(payload['jti']):
        # Potential token theft — revoke entire family
        revoke_token_family(payload['family'])
        return jsonify({'error': 'Token reuse detected'}), 401

    # Issue new token pair (rotation)
    new_access = create_access_token(payload['sub'])
    new_refresh = create_refresh_token(payload['sub'], payload['family'])

    # Revoke old refresh token
    revoke_token(payload['jti'])

    response = jsonify({'access_token': new_access})
    response.set_cookie('refresh_token', new_refresh,
                        httponly=True, secure=True, samesite='Strict')
    return response
```

---

## JWT Security

### XSS (Cross-Site Scripting)

If an attacker injects JavaScript into your page, they can steal tokens stored in `localStorage` or `sessionStorage`.

**Mitigations**:
- Store tokens in `HttpOnly` cookies (not accessible to JavaScript).
- Use Content Security Policy (CSP) headers.
- Sanitize all user input.
- Use frameworks that auto-escape output (React, Vue).

### CSRF (Cross-Site Request Forgery)

If tokens are in cookies, an attacker can make the victim's browser send authenticated requests.

**Mitigations**:
- `SameSite=Strict` or `SameSite=Lax` cookies.
- CSRF tokens (anti-CSRF tokens in forms).
- Check `Origin` and `Referer` headers.
- Use `SameSite=Strict` for API cookies.

### JWT-Specific Attacks

#### Algorithm Confusion (`alg: none`)

An attacker changes the header to `{"alg": "none"}` and strips the signature.

**Mitigation**: Never accept `none` as an algorithm. Whitelist allowed algorithms on the server.

```python
# VULNERABLE: accepts any algorithm
payload = jwt.decode(token, options={"verify_signature": False})

# SECURE: whitelist algorithms
payload = jwt.decode(token, public_key, algorithms=["RS256"])
```

#### Key Confusion (HS256 vs RS256)

An attacker uses the RSA public key as an HMAC secret to forge tokens.

**Mitigation**: Always specify the expected algorithm. Never use the same key for different algorithms.

#### Token Theft

If an access token is stolen, it's valid until it expires.

**Mitigations**:
- Short expiration times (15 minutes).
- Refresh token rotation with reuse detection.
- Token binding (tie token to client fingerprint).
- Store in `HttpOnly` cookies, not `localStorage`.

---

## Token Storage Best Practices

| Storage Method | XSS | CSRF | Persistence | Recommendation |
|---------------|-----|------|-------------|----------------|
| `localStorage` | ❌ Vulnerable | ✅ Safe | ✅ Persists | ❌ Avoid for auth tokens |
| `sessionStorage` | ❌ Vulnerable | ✅ Safe | ❌ Tab-scoped | ❌ Avoid for auth tokens |
| `HttpOnly` Cookie | ✅ Safe | ❌ Needs protection | ✅ Persists | ✅ Use for refresh tokens |
| In-memory variable | ✅ Safe | ✅ Safe | ❌ Lost on refresh | ✅ Use for access tokens |
| `HttpOnly` + `SameSite=Strict` | ✅ Safe | ✅ Safe | ✅ Persists | ✅ Best for refresh tokens |

### Recommended Pattern for SPAs

```javascript
// Access token: in-memory (JavaScript variable)
let accessToken = null;

// Refresh token: HttpOnly cookie (set by server)
// Login response sets: Set-Cookie: refresh_token=xxx; HttpOnly; Secure; SameSite=Strict

async function fetchWithAuth(url, options = {}) {
  // Attach access token
  options.headers = {
    ...options.headers,
    'Authorization': `Bearer ${accessToken}`
  };

  let response = await fetch(url, options);

  // If 401, try refreshing
  if (response.status === 401) {
    const refreshResult = await fetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include'  // Send refresh token cookie
    });

    if (refreshResult.ok) {
      const data = await refreshResult.json();
      accessToken = data.access_token;
      options.headers['Authorization'] = `Bearer ${accessToken}`;
      response = await fetch(url, options);
    } else {
      // Redirect to login
      window.location.href = '/login';
    }
  }

  return response;
}
```

---

## JWT vs Session Cookies

| Aspect | JWT | Session Cookies |
|--------|-----|-----------------|
| State | Stateless (self-contained) | Stateful (server stores session) |
| Scalability | No server-side storage needed | Requires shared session store |
| Revocation | Hard (until expiry) | Easy (delete from store) |
| Payload | Can carry user claims | Only session ID |
| Size | Larger (~800+ bytes) | Small (~20-50 bytes) |
| Validation | Cryptographic (local) | Database lookup (network) |

**Use JWT when**: Microservices (stateless validation), mobile apps, public APIs.
**Use sessions when**: Server-rendered web apps, need instant revocation, simplicity is priority.

---

## Implementation Example

### Generating and Verifying JWTs (Python)

```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-256-bit-secret"  # In production, use env var
ALGORITHM = "HS256"

def create_access_token(user_id: str, expires_delta: timedelta = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": expire,
        "iss": "https://auth.example.com",
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer="https://auth.example.com",
            options={"require": ["exp", "iss", "sub"]}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {e}")
```

### JWT with RSA (Production)

```python
# Generate keys (one-time)
# openssl genrsa -out private.pem 2048
# openssl rsa -in private.pem -pubout -out public.pem

from cryptography.hazmat.primitives import serialization

with open("private.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

with open("public.pem", "rb") as f:
    public_key = f.read()

# Sign with private key
token = jwt.encode(payload, private_key, algorithm="RS256")

# Verify with public key
decoded = jwt.decode(token, public_key, algorithms=["RS256"])
```

---

## Interview Questions

1. **What is a JWT and what are its three parts?**
   A JWT is a compact token format for securely transmitting claims. It has three Base64URL-encoded parts: (1) Header (algorithm, type), (2) Payload (claims like sub, exp, iss), (3) Signature (cryptographic proof of integrity).

2. **What is the difference between HS256 and RS256?**
   HS256 is symmetric — the same secret signs and verifies. RS256 is asymmetric — a private key signs, a public key verifies. Use HS256 for internal services (faster, simpler). Use RS256 when the verifier shouldn't have the signing key (third-party auth, public APIs).

3. **How do you prevent JWT algorithm confusion attacks?**
   Always whitelist allowed algorithms on the server: `algorithms=["RS256"]`. Never accept `alg: none`. Never let the token's `alg` header dictate which algorithm the server uses — the server should enforce its own policy.

4. **Where should you store JWTs in a browser application?**
   Access tokens: in memory (JavaScript variable) — short-lived, not persisted. Refresh tokens: in `HttpOnly`, `Secure`, `SameSite=Strict` cookies — not accessible to JavaScript (XSS-safe), protected against CSRF by SameSite.

5. **What is refresh token rotation and why is it important?**
   Each time a refresh token is used, the server issues a new one and invalidates the old. If an attacker steals and uses a refresh token, the legitimate user's next refresh attempt will fail (token reuse detected), alerting the server to revoke the entire token family.

6. **How do you revoke a JWT?**
   JWTs are stateless — they're valid until they expire. To revoke: (1) Use short expiration + refresh tokens. (2) Maintain a server-side blocklist (Redis) of revoked JTIs. (3) Use a token version number in the user record — increment to invalidate all tokens.

7. **What is the `sub` claim in a JWT?**
   The `sub` (subject) claim identifies who the token is about — typically the user ID. It's a registered claim per RFC 7519 and should be a stable, unique identifier (not an email, which can change).

8. **Explain the difference between JWT and session cookies.**
   JWTs are stateless (self-contained, no server storage) and ideal for microservices/mobile. Sessions are stateful (server stores session data, lookup required) and ideal for server-rendered apps. JWTs are harder to revoke; sessions are easy to invalidate.

9. **What is the `exp` claim and how should you set it?**
   The `exp` (expiration) claim is a Unix timestamp after which the token is invalid. Access tokens: 15-60 minutes. Refresh tokens: 7-30 days. Always set `exp` — tokens without expiration are a security risk.

10. **How would you implement JWT in a microservices architecture?**
    The auth service issues JWTs signed with RS256. Each microservice has the public key and verifies tokens locally (no network call to auth service). Use an API gateway to validate tokens before routing. Short-lived access tokens (5 min) with refresh token rotation.

11. **What is the `aud` claim and why does it matter?**
    The `aud` (audience) claim specifies who the token is intended for. The resource server should verify that its own identifier is in the `aud` claim. This prevents a token issued for Service A from being used with Service B.

12. **How do you handle JWT key rotation?**
    Include a `kid` (Key ID) in the JWT header. The server maintains multiple public keys and uses `kid` to select the right one. When rotating: generate a new key pair, start signing with the new private key, keep the old public key for verification until all old tokens expire.
