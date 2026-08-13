# Authentication

## Overview

Authentication is the process of verifying the identity of a user, system, or entity. It answers the question: "Who are you?" This is distinct from authorization, which determines "What can you do?"

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│   User   │────▶│Authentication│────▶│Authorization │
│          │     │  "Who are you?"│     │"What can you do?"│
└──────────┘     └──────────────┘     └──────────────┘
```

## Authentication Factors

Authentication methods are categorized by the type of evidence they require:

```
┌─────────────────────────────────────────────┐
│           Authentication Factors             │
├─────────────────┬───────────────────────────┤
│ Something You   │ Something You             │
│ Know            │ Have                      │
│ • Password      │ • Hardware token          │
│ • PIN           │ • Phone (SMS/app)         │
│ • Security Q    │ • Smart card              │
├─────────────────┼───────────────────────────┤
│ Something You   │ Somewhere You             │
│ Are             │ Are                       │
│ • Fingerprint   │ • IP address              │
│ • Face ID       │ • Geolocation             │
│ • Retina scan   │ • Network location        │
└─────────────────┴───────────────────────────┘
```

- **Single-factor**: One method (e.g., password only)
- **Two-factor (2FA)**: Two methods (e.g., password + SMS code)
- **Multi-factor (MFA)**: Two or more different types of factors

## Password-Based Authentication

### How Passwords Are Stored

Passwords should **never** be stored in plaintext. The standard approach:

```
User registers:    password ──▶ hash(password + salt) ──▶ store(hash, salt)
User logs in:      password ──▶ hash(password + salt) ──▶ compare with stored hash
```

```python
import bcrypt

# Registration
def register_user(username, password):
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    store_in_db(username, hashed)

# Login
def login(username, password):
    stored_hash = get_from_db(username)
    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
        return create_session(username)
    raise AuthenticationError("Invalid credentials")
```

### Password Policies

```python
import re

def validate_password(password):
    """Enforce password complexity requirements."""
    errors = []
    
    if len(password) < 12:
        errors.append("Password must be at least 12 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("Must contain uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("Must contain lowercase letter")
    if not re.search(r'[0-9]', password):
        errors.append("Must contain digit")
    if not re.search(r'[!@#$%^&*]', password):
        errors.append("Must contain special character")
    
    # Check against common passwords
    if password in load_common_passwords():
        errors.append("Password is too common")
    
    return errors
```

**Modern best practices**:
- Minimum 12+ characters (length > complexity)
- Check against breached password databases (HaveIBeenPwned)
- Allow passphrases (correct-horse-battery-staple)
- Rate limit login attempts
- Account lockout after repeated failures

## Multi-Factor Authentication (MFA)

### TOTP (Time-Based One-Time Password)

Used by Google Authenticator, Authy, etc.

```
┌────────┐                    ┌────────┐
│ Server │  Shared Secret (K) │ Client │
│        │◀──────────────────▶│ (App)  │
│        │                    │        │
│ Compute│   TOTP(K, T) = ?   │Compute │
│  HMAC  │                    │ HMAC   │
└────────┘                    └────────┘

T = current time / 30 seconds
OTP = HMAC-SHA1(K, T) truncated to 6 digits
```

```python
import hmac
import hashlib
import struct
import time

def generate_totp(secret, time_step=30, digits=6):
    """Generate TOTP code."""
    # Calculate time counter
    counter = int(time.time()) // time_step
    
    # Convert counter to bytes
    counter_bytes = struct.pack('>Q', counter)
    
    # Calculate HMAC-SHA1
    hmac_hash = hmac.new(secret, counter_bytes, hashlib.sha1).digest()
    
    # Dynamic truncation
    offset = hmac_hash[-1] & 0x0F
    code = struct.unpack('>I', hmac_hash[offset:offset+4])[0]
    code &= 0x7FFFFFFF
    code = code % (10 ** digits)
    
    return str(code).zfill(digits)

def verify_totp(secret, provided_code, time_step=30):
    """Verify TOTP with a window of ±1 step."""
    for offset in [-1, 0, 1]:
        counter = (int(time.time()) // time_step) + offset
        expected = generate_totp_with_counter(secret, counter)
        if hmac.compare_digest(expected, provided_code):
            return True
    return False
```

### WebAuthn / FIDO2

Modern passwordless authentication using hardware keys or biometrics.

```
Registration Flow:
┌──────┐    ┌──────────┐    ┌──────────┐
│User  │───▶│ Relying  │───▶│Authenticator│
│      │    │ Party    │    │(Device/Bio)│
└──────┘    └──────────┘    └──────────┘
   1. Register      2. Challenge
   4. Store cred    3. Sign challenge
                     + Create keypair
```

**Advantages**: Phishing-resistant, no shared secrets, public-key based.

## Session-Based Authentication

Traditional web authentication using server-side sessions.

```
┌────────┐                    ┌────────┐
│ Browser │──1. Login────────▶│ Server │
│         │◀──2. Set-Cookie───│        │
│         │   (session_id)    │        │
│         │                   │ Session│
│         │──3. Request──────▶│ Store  │
│         │   Cookie:         │(Redis/ │
│         │   session_id      │ DB)    │
│         │◀──4. Response─────│        │
└────────┘                    └────────┘
```

```python
from flask import Flask, session, request
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    if verify_credentials(username, password):
        session['user_id'] = get_user_id(username)
        session['role'] = get_user_role(username)
        session.permanent = True
        app.permanent_session_lifetime = timedelta(hours=1)
        return redirect('/dashboard')
    
    return 'Invalid credentials', 401

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', user=session['user_id'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
```

**Session security considerations**:
- Generate session IDs with cryptographic randomness
- Set `HttpOnly`, `Secure`, `SameSite` flags on cookies
- Implement session expiration (idle and absolute)
- Regenerate session ID after login (prevent fixation)
- Store sessions server-side (Redis, database)

## Token-Based Authentication (JWT)

### JWT Structure

```
eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjN9.SflKxwRJSMeKKF2QT4fwpM

│  Header  │  .  │  Payload  │  .  │ Signature │
│ (alg,typ)│     │ (claims)  │     │ (verify)  │
```

**Header**:
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload** (claims):
```json
{
  "sub": "1234567890",
  "name": "John Doe",
  "iat": 1516239022,
  "exp": 1516242622,
  "iss": "my-app",
  "aud": "my-api",
  "roles": ["user", "admin"]
}
```

### JWT Implementation

```python
import jwt
import datetime
from functools import wraps

SECRET_KEY = "your-secret-key"  # Use env variable in production

def create_access_token(user_id, roles, expires_delta=timedelta(hours=1)):
    """Create a JWT access token."""
    payload = {
        'sub': str(user_id),
        'roles': roles,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expires_delta,
        'iss': 'my-application',
        'jti': str(uuid.uuid4())  # Unique token ID for revocation
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def create_refresh_token(user_id, expires_delta=timedelta(days=7)):
    """Create a long-lived refresh token."""
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'exp': datetime.utcnow() + expires_delta,
        'jti': str(uuid.uuid4())
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=['HS256'],
            issuer='my-application'
        )
        
        # Check if token is revoked
        if is_token_revoked(payload['jti']):
            raise jwt.InvalidTokenError("Token has been revoked")
        
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {e}")

def require_auth(f):
    """Decorator for protecting routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return {'error': 'Token missing'}, 401
        
        try:
            payload = verify_token(token)
            request.user = payload
        except AuthenticationError as e:
            return {'error': str(e)}, 401
        
        return f(*args, **kwargs)
    return decorated

def require_role(role):
    """Decorator for role-based access."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if role not in request.user.get('roles', []):
                return {'error': 'Insufficient permissions'}, 403
            return f(*args, **kwargs)
        return decorated
    return decorator
```

### JWT vs Sessions

| Aspect | JWT | Sessions |
|--------|-----|----------|
| Storage | Client-side | Server-side |
| Scalability | Stateless, easy | Requires shared store |
| Revocation | Hard (blacklist) | Easy (delete session) |
| Size | Larger (carries claims) | Small (just ID) |
| Security | Signature verified | Server-side lookup |
| Best for | APIs, microservices | Traditional web apps |

### Access Token + Refresh Token Pattern

```
┌────────┐         ┌────────┐         ┌────────┐
│ Client │──1.Login▶│ Auth   │         │ Resource│
│        │◀────────│ Server │         │ Server  │
│        │ access  │        │         │         │
│        │ +refresh│        │         │         │
│        │         │        │         │         │
│        │──2.API──┼────────┼────────▶│         │
│        │ call +  │        │         │         │
│        │ access  │        │         │         │
│        │ token   │        │         │         │
│        │         │        │         │         │
│        │──3.Refresh┼──────▶│         │         │
│        │ (when   │◀───────│         │         │
│        │ expired)│ new    │         │         │
│        │         │ access │         │         │
└────────┘         └────────┘         └────────┘
```

## OAuth 2.0

OAuth 2.0 is an authorization framework that enables third-party applications to access resources on behalf of a user.

### OAuth 2.0 Roles

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Resource │     │ Authorization│     │   Client     │
│  Owner   │────▶│   Server     │◀────│  Application │
│ (User)   │     │              │     │              │
└──────────┘     └──────┬───────┘     └──────┬───────┘
                        │                     │
                        ▼                     │
                 ┌──────────────┐             │
                 │  Resource    │◀────────────┘
                 │  Server      │  (with access token)
                 │  (API)       │
                 └──────────────┘
```

### Authorization Code Flow (Most Common)

```
┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│Client│    │Auth Server│    │Resource  │    │  User    │
│  App │    │          │    │  Server  │    │ (Browser)│
└──┬───┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
   │             │               │               │
   │  1. Redirect to auth server │               │
   │─────────────────────────────┼──────────────▶│
   │             │               │               │
   │             │  2. User logs in & consents   │
   │             │◀──────────────────────────────│
   │             │               │               │
   │             │  3. Redirect back with        │
   │             │     authorization code        │
   │◀────────────┼───────────────┼───────────────│
   │             │               │               │
   │  4. Exchange code for token │               │
   │────────────▶│               │               │
   │             │               │               │
   │  5. Access token + refresh  │               │
   │◀────────────│               │               │
   │             │               │               │
   │  6. API call with token     │               │
   │─────────────┼──────────────▶│               │
   │             │               │               │
   │  7. Protected resource      │               │
   │◀────────────┼───────────────│               │
```

```python
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)

# Register OAuth provider
google = oauth.register(
    name='google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'}
)

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/callback/google')
def google_callback():
    token = google.authorize_access_token()
    user_info = google.parse_id_token(token)
    
    # Find or create user
    user = find_or_create_user(
        email=user_info['email'],
        name=user_info['name'],
        provider='google'
    )
    
    session['user_id'] = user.id
    return redirect('/dashboard')
```

### OAuth 2.0 Grant Types

| Grant Type | Use Case | Security Level |
|-----------|----------|----------------|
| Authorization Code | Web apps with backend | High |
| Authorization Code + PKCE | Mobile/SPA | High |
| Client Credentials | Service-to-service | High |
| Device Code | Smart TV, CLI tools | Medium |
| ~~Implicit~~ | ~~SPAs~~ (deprecated) | ~~Low~~ |
| ~~Password~~ | ~~First-party apps~~ (deprecated) | ~~Low~~ |

## OpenID Connect (OIDC)

OIDC is an identity layer on top of OAuth 2.0 that adds authentication.

```
OAuth 2.0:    "Here's an access token" (authorization)
OIDC:         "Here's who you are" + "Here's an access token" (authentication + authorization)
```

**Key additions**:
- **ID Token**: JWT containing user identity claims
- **UserInfo Endpoint**: API to get user profile
- **Standard Scopes**: `openid`, `profile`, `email`, `address`, `phone`

```python
# ID Token structure
{
    "iss": "https://accounts.google.com",
    "sub": "110169484474386276334",
    "aud": "your-client-id",
    "exp": 1618884473,
    "iat": 1618880873,
    "email": "user@example.com",
    "name": "John Doe",
    "picture": "https://...",
    "email_verified": true
}
```

## Single Sign-On (SSO)

SSO allows users to authenticate once and access multiple applications.

### SAML-Based SSO

```
┌──────┐    ┌──────────┐    ┌──────────┐
│ User │    │ Service  │    │Identity  │
│      │    │ Provider │    │ Provider │
│      │    │  (SP)    │    │  (IdP)   │
└──┬───┘    └────┬─────┘    └────┬─────┘
   │             │               │
   │ 1. Access   │               │
   │────────────▶│               │
   │             │               │
   │             │ 2. SAML Authn │
   │             │    Request    │
   │◀────────────┼──────────────▶│
   │             │               │
   │ 3. Login    │               │
   │─────────────┼──────────────▶│
   │             │               │
   │ 4. SAML Response            │
   │◀────────────┼───────────────│
   │   (with assertion)          │
   │             │               │
   │ 5. Access granted           │
   │────────────▶│               │
```

## Interview Questions

### Q1: What's the difference between authentication and authorization?

**Answer**: Authentication verifies identity ("who are you?"), authorization determines access ("what can you do?"). Authentication happens first. Example: Logging in is authentication; accessing admin panel is authorization.

### Q2: Why are JWTs stateless? What are the trade-offs?

**Answer**: JWTs are stateless because all user information is contained in the token itself (in the payload), verified by signature. The server doesn't need to look up session state. 

**Advantages**: Scalability (no shared session store), works across services, self-contained.

**Disadvantages**: Can't revoke tokens easily (need a blacklist), token size is larger, payload is visible (not encrypted by default), can't update claims without re-issuing.

### Q3: How does OAuth 2.0 differ from OpenID Connect?

**Answer**: OAuth 2.0 is an **authorization** framework — it lets apps get limited access to user resources. OIDC is an **authentication** layer built on top of OAuth 2.0 — it adds identity verification via ID tokens and a UserInfo endpoint. Use OAuth 2.0 when you need API access; use OIDC when you need to know who the user is.

### Q4: Explain the authorization code flow with PKCE.

**Answer**: PKCE (Proof Key for Code Exchange) prevents authorization code interception attacks. The client generates a random `code_verifier`, creates a `code_challenge` (SHA-256 hash), sends the challenge with the auth request, then sends the original verifier when exchanging the code for a token. The server verifies the challenge matches.

```
Client generates: code_verifier = random_string
                  code_challenge = SHA256(code_verifier)

Auth request:     ?code_challenge=...&code_challenge_method=S256
Token exchange:   &code_verifier=original_random_string
```

### Q5: How would you implement "remember me" functionality?

**Answer**: Use a long-lived refresh token stored in a secure, HttpOnly cookie. The access token has a short lifetime (15-60 min). When it expires, the refresh token gets a new access token. Store refresh token hashes server-side for revocation. Set `Secure`, `HttpOnly`, `SameSite=Strict` flags.

### Q6: What happens if a JWT signing key is compromised?

**Answer**: An attacker can forge valid tokens. Immediate response: rotate the signing key, invalidate all existing tokens (if using a blacklist), force re-authentication. Prevention: use strong keys, rotate regularly, use asymmetric keys (RS256) so only the auth server has the private key, implement token revocation lists.

### Q7: How do you prevent session fixation attacks?

**Answer**: Regenerate the session ID immediately after successful authentication. This prevents an attacker from setting a known session ID before the user authenticates.

```python
@app.route('/login', methods=['POST'])
def login():
    if verify_credentials(request.form):
        session.regenerate()  # Critical: new session ID after login
        session['user_id'] = user.id
```

### Q8: Compare symmetric vs asymmetric JWT signing.

**Answer**: 
- **HS256 (symmetric)**: Same secret signs and verifies. Fast. Risky if multiple services need the secret.
- **RS256 (asymmetric)**: Private key signs, public key verifies. Only auth server has private key. Safer for microservices. Slower.

Use RS256 when multiple services verify tokens. Use HS256 for single-service applications.
