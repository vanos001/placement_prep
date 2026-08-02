# Security in System Design

## Why Security Matters in HLD

Security is not an afterthought — it must be designed into the architecture from the beginning. A single breach can cost millions and destroy user trust.

## Authentication vs Authorization

```
Authentication: "Who are you?" (Identity verification)
Authorization:  "What can you do?" (Permission checking)

Example:
AuthN: User provides username + password → Verified as Alice
AuthZ: Alice can read her own orders but not Bob's orders
```

### Authentication Methods

| Method | How It Works | Use Case | Security Level |
|--------|-------------|----------|----------------|
| **Session-based** | Server stores session, client has cookie | Traditional web apps | Medium |
| **Token-based (JWT)** | Client stores token, server validates | APIs, SPAs, mobile | Medium-High |
| **OAuth 2.0** | Delegated auth via third party | "Login with Google" | High |
| **API Keys** | Simple string in header | Service-to-service | Low-Medium |
| **mTLS** | Mutual certificate verification | Internal services | Very High |
| **SAML** | XML-based federation | Enterprise SSO | High |

## OAuth 2.0

### OAuth 2.0 Flow (Authorization Code)

```
1. User clicks "Login with Google"
2. App redirects to Google (with client_id, redirect_uri, scope)
3. User logs in to Google, grants permission
4. Google redirects back with authorization code
5. App exchanges code for access token (server-to-server)
6. App uses access token to access Google APIs

┌──────┐     ┌──────────┐     ┌──────────┐
│ User │────→│   App    │────→│  Google  │
│      │     │          │     │  OAuth   │
│      │←────│          │←────│  Server  │
└──────┘     └──────────┘     └──────────┘
  Login        Code exchange    Auth code
               Access token
```

### OAuth 2.0 Grant Types

| Grant Type | Flow | Use Case |
|-----------|------|----------|
| **Authorization Code** | Code → Token exchange | Web apps (most secure) |
| **Authorization Code + PKCE** | Code with challenge | Mobile/SPA apps |
| **Client Credentials** | Direct token | Service-to-service |
| **Device Code** | User code on device | Smart TV, CLI tools |
| **Implicit** | Direct token (deprecated) | Legacy SPAs |

### OAuth Scopes
```
scope=read:user    → Can read user profile
scope=read:email   → Can read email
scope=repo         → Can access repositories
scope=write:repos  → Can create/modify repos
```

## JWT (JSON Web Tokens)

### JWT Structure
```
Header.Payload.Signature

Header: {"alg": "RS256", "typ": "JWT"}
Payload: {"sub": "user123", "name": "Alice", "role": "admin", "exp": 1700000000}
Signature: RSASHA256(header + "." + payload, privateKey)
```

### JWT Best Practices

```
✅ Store in HttpOnly cookie (not localStorage)
✅ Use short expiration (15 min for access token)
✅ Use refresh tokens for long sessions
✅ Validate signature on every request
✅ Include minimal claims (don't put sensitive data)
✅ Use RS256 (asymmetric) for multi-service
✅ Implement token revocation for logout

❌ Don't store sensitive data in payload (base64, not encrypted)
❌ Don't use long expiration
❌ Don't skip signature validation
❌ Don't use "none" algorithm
```

### Access Token + Refresh Token Pattern
```
Access Token:  Short-lived (15 min), used for API calls
Refresh Token: Long-lived (7 days), used to get new access tokens

Flow:
1. Login → Access token + Refresh token
2. API call → Use Access token
3. Access token expires → Use Refresh token to get new Access token
4. Refresh token expires → Re-login
```

## Encryption

### Encryption at Rest
Data stored on disk is encrypted.

```
Database: AES-256 encryption for sensitive columns
Files: Encrypted before storage (S3 SSE, GCS encryption)
Backups: Encrypted with separate keys
```

### Encryption in Transit
Data moving between systems is encrypted.

```
Client ←──HTTPS/TLS──→ Load Balancer ←──TLS──→ App Server ←──TLS──→ Database
```

### TLS/SSL
```
1. Client connects to server
2. Server sends certificate (public key)
3. Client verifies certificate with CA
4. Client generates session key, encrypts with server's public key
5. Server decrypts with private key
6. Both use session key for symmetric encryption
```

### Hashing (for passwords)
```
Password → bcrypt/scrypt/Argon2 → Hash stored in DB

Never store plain text passwords!
Never use MD5/SHA for passwords (too fast, vulnerable to brute force)
```

## API Security

### Rate Limiting
```
Per IP: 100 requests/minute
Per User: 1000 requests/hour
Per API Key: 10000 requests/day

Implementation: Token bucket or sliding window at API Gateway
```

### Input Validation
```
✅ Validate all input (type, length, format)
✅ Use parameterized queries (prevent SQL injection)
✅ Sanitize HTML output (prevent XSS)
✅ Validate file uploads (type, size, content)
✅ Use allowlists over blocklists
```

### Common Attacks and Mitigations

| Attack | How It Works | Mitigation |
|--------|-------------|------------|
| **SQL Injection** | Inject SQL via user input | Parameterized queries, ORM |
| **XSS** | Inject scripts in web pages | Input sanitization, CSP headers |
| **CSRF** | Trick user into making requests | CSRF tokens, SameSite cookies |
| **DDoS** | Flood with traffic | Rate limiting, CDN, WAF |
| **Man-in-the-Middle** | Intercept communication | TLS, certificate pinning |
| **Brute Force** | Try all passwords | Rate limiting, account lockout |
| **Replay Attack** | Re-send valid request | Nonces, timestamps, one-time tokens |

### Security Headers
```
Strict-Transport-Security: max-age=31536000  (HSTS)
Content-Security-Policy: default-src 'self'  (CSP)
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

## Authorization Models

### RBAC (Role-Based Access Control)
```
User → Role → Permissions

Alice → Admin → [read, write, delete]
Bob → Editor → [read, write]
Charlie → Viewer → [read]
```

### ABAC (Attribute-Based Access Control)
```
Policy: Allow if (user.department == "engineering" AND resource.classification != "top-secret")

More flexible than RBAC, but more complex
```

### ReBAC (Relationship-Based Access Control)
```
Allow if user.is_owner(resource) OR user.is_friend(resource.owner)

Used by: Google Zanzibar (powers Google Docs sharing)
```

## Secrets Management

### What are Secrets?
- Database passwords
- API keys
- Encryption keys
- OAuth client secrets
- TLS certificates

### Secrets Management Best Practices

```
❌ Don't: Store secrets in code, config files, or environment variables
✅ Do: Use secrets management tools

Tools:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
```

### Secrets Rotation
```
Automatic rotation:
- Database passwords: Every 30 days
- API keys: Every 90 days
- TLS certificates: Before expiry (automated via Let's Encrypt)
```

## Network Security

### Network Segmentation
```
┌─────────────────────────────────────────┐
│              VPC                         │
│  ┌──────────────────────────────────┐  │
│  │  Public Subnet                   │  │
│  │  [Load Balancer] [Bastion Host]  │  │
│  └────────────────┬─────────────────┘  │
│                   │                     │
│  ┌────────────────┴─────────────────┐  │
│  │  Private Subnet                  │  │
│  │  [App Servers] [DB] [Cache]      │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Security Groups / Firewall Rules
```
Load Balancer: Allow 80, 443 from 0.0.0.0/0
App Servers: Allow 8080 from LB only
Database: Allow 5432 from App Servers only
Cache: Allow 6379 from App Servers only
```

## Security in Depth (Defense in Depth)

```
Layer 1: CDN/WAF → DDoS protection, bot filtering
Layer 2: Load Balancer → TLS termination, rate limiting
Layer 3: API Gateway → Authentication, authorization
Layer 4: Application → Input validation, business logic
Layer 5: Database → Encryption, access control
Layer 6: Infrastructure → Network segmentation, monitoring
```

## Interview Tips

1. **Always mention security** — "We need to secure this system..."
2. **Discuss auth early** — "How will users authenticate?"
3. **Mention specific mechanisms** — "JWT for API auth, OAuth for third-party"
4. **Consider encryption** — "TLS in transit, AES-256 at rest"
5. **Discuss rate limiting** — "Token bucket at API gateway"
6. **Include input validation** — "Parameterized queries, input sanitization"
7. **Think about secrets** — "Vault for secrets management"
8. **Consider compliance** — "GDPR, SOC2, HIPAA if applicable"

## Common Mistakes

- ❌ Storing passwords in plain text
- ❌ Using MD5/SHA for password hashing
- ❌ JWT in localStorage (XSS vulnerable)
- ❌ No rate limiting
- ❌ Ignoring input validation
- ❌ Hardcoded secrets in code
- ❌ No HTTPS (or mixed content)
- ❌ Overly permissive CORS

## Cross-References

- [API Design](./api-design.md) — Authentication and rate limiting
- [Availability](./availability.md) — DDoS protection
- [Load Balancing](./load-balancing-design.md) — SSL termination
- [Monitoring](./monitoring-observability.md) — Security logging
- [Consistency Tradeoffs](./consistency-tradeoffs.md) — Security vs usability
- [Networks Security](../../networks/security/ssl.md)
- [Cloud VPC](../../cloud/aws/vpc.md)
- [DBMS Transactions](../../dbms/transactions/acid.md)
