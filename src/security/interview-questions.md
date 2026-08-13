# Security Interview Questions

## Fundamentals

### Q1: What is the CIA Triad and why is it important?

**Answer**: The CIA Triad consists of:
- **Confidentiality**: Data is accessible only to authorized parties (encryption, access control)
- **Integrity**: Data is accurate and unmodified (hashing, digital signatures)
- **Availability**: Systems are accessible when needed (redundancy, DDoS protection)

It's the foundation of information security. Every security control maps to one or more of these principles. When designing systems, evaluate how each component supports or threatens CIA.

### Q2: What's the difference between vulnerability, threat, and risk?

**Answer**:
- **Vulnerability**: A weakness that can be exploited (e.g., unpatched software, SQL injection)
- **Threat**: A potential danger that could exploit a vulnerability (e.g., attacker, malware)
- **Risk**: The likelihood and impact of a threat exploiting a vulnerability

`Risk = Likelihood × Impact`

You can't eliminate all vulnerabilities, but you can reduce risk by reducing likelihood (patching, monitoring) or impact (encryption, backups).

### Q3: Explain defense in depth.

**Answer**: Defense in depth uses multiple layers of security controls so that if one fails, others still provide protection. Layers include: physical security, network security (firewalls, IDS), host security (OS hardening, antivirus), application security (input validation, authentication), and data security (encryption, access controls). Example: A web app has a WAF, input validation, parameterized queries, and least-privilege database access — even if one layer is bypassed, others prevent exploitation.

### Q4: What is the principle of least privilege?

**Answer**: Grant only the minimum permissions necessary to perform a task. This limits the blast radius if an account is compromised. Implementation: default deny policies, role-based access, time-limited access, just-in-time provisioning, regular access reviews. Example: A reporting service gets read-only access to specific tables, not admin access to the entire database.

## Authentication & Authorization

### Q5: Compare session-based and token-based authentication.

**Answer**:
- **Session-based**: Server stores session state (Redis/DB). Client holds session ID in cookie. Easy to revoke (delete session). Requires shared session store for scaling.
- **Token-based (JWT)**: Token contains all claims. Stateless — no server-side storage. Harder to revoke (need blacklist). Works well across microservices.

Use sessions for traditional web apps, tokens for APIs and microservices. Many modern apps use both: sessions for the web frontend, tokens for API clients.

### Q6: How does OAuth 2.0 work and when should you use it?

**Answer**: OAuth 2.0 lets third-party apps access user resources without sharing credentials. The authorization code flow: (1) App redirects user to auth server, (2) User authenticates and consents, (3) Auth server sends authorization code back, (4) App exchanges code for access token, (5) App uses token to access API. Use OAuth when you need delegated access (e.g., "Login with Google", third-party API access). Use OIDC (on top of OAuth) for authentication ("Sign in with Google").

### Q7: What is RBAC vs ABAC?

**Answer**: RBAC assigns permissions based on roles (Admin, Editor, Viewer). Simple to implement and manage. ABAC evaluates attributes dynamically (user.department, resource.classification, time_of_day). More flexible but complex. Many systems combine both: RBAC for coarse-grained access, ABAC for fine-grained policies.

## Web Security

### Q8: How would you prevent SQL injection?

**Answer**: 
1. **Parameterized queries / Prepared statements** (primary defense) — separates SQL code from data
2. **ORMs** (SQLAlchemy, Hibernate) — use parameterization under the hood
3. **Input validation** — whitelist expected formats
4. **Least privilege** — database user with minimal permissions
5. **WAF** — additional layer, not primary defense
6. **Stored procedures** — parameterized by design

Never use string concatenation for SQL queries. Always parameterize user input.

### Q9: Explain XSS and how to prevent it.

**Answer**: XSS injects malicious scripts into web pages. Types: stored (in database), reflected (in URL), DOM-based (client-side). Prevention: (1) Output encoding/escaping (HTML entities, JavaScript escaping), (2) Content Security Policy (CSP) headers, (3) HTTPOnly cookies (prevent JS access), (4) Input validation, (5) Use frameworks that auto-escape (React, Jinja2). CSP is the strongest defense — even if XSS succeeds, the browser won't execute unauthorized scripts.

### Q10: What is CSRF and how do you prevent it?

**Answer**: CSRF tricks authenticated users into performing unwanted actions by exploiting the browser's automatic cookie inclusion. Prevention: (1) CSRF tokens (synchronizer pattern), (2) SameSite cookie attribute (Strict or Lax), (3) Check Origin/Referer headers, (4) Require re-authentication for sensitive actions. SameSite cookies in modern browsers provide strong default protection.

### Q11: What is SSRF and why is it dangerous?

**Answer**: SSRF makes the server send requests to unintended locations. Attackers can access internal services, cloud metadata endpoints (169.254.169.254), and internal APIs. Prevention: validate and whitelist URLs, block internal IP ranges, disable HTTP redirects, use a dedicated URL-fetching service with network restrictions.

## Cryptography

### Q12: When should you use symmetric vs asymmetric encryption?

**Answer**: Symmetric (AES): fast, used for bulk data encryption. Requires secure key distribution. Asymmetric (RSA, ECC): slower, used for key exchange, digital signatures, encrypting small data. In practice, use hybrid encryption: asymmetric encrypts a symmetric key, symmetric encrypts the data. TLS uses this pattern.

### Q13: What is forward secrecy?

**Answer**: Forward secrecy ensures that compromise of long-term keys doesn't compromise past sessions. Achieved using ephemeral Diffie-Hellman key exchange — each session gets a unique key that's discarded after use. TLS 1.3 mandates forward secrecy. Without it, recorded encrypted traffic can be decrypted if the private key is later compromised.

### Q14: Why use bcrypt/Argon2 instead of SHA-256 for passwords?

**Answer**: SHA-256 is designed to be fast — a GPU can compute billions per second, making brute-force feasible. bcrypt, scrypt, and Argon2 are intentionally slow and memory-hard, making brute-force impractical. Argon2id won the Password Hashing Competition and is recommended. It's configurable for time cost, memory cost, and parallelism.

### Q15: What is a digital signature and how does it work?

**Answer**: A digital signature provides authentication, integrity, and non-repudiation. Process: (1) Hash the message, (2) Encrypt the hash with the sender's private key (the signature), (3) Send message + signature. Verification: (1) Hash the received message, (2) Decrypt the signature with sender's public key, (3) Compare hashes. If they match, the message is authentic and unmodified.

## System Design & Architecture

### Q16: How would you design an authentication system for a microservices architecture?

**Answer**: 
1. **Centralized auth service** handles login, token issuance
2. **JWT tokens** with short expiry (15 min) for API access
3. **Refresh tokens** with longer expiry (7 days) for token renewal
4. **API gateway** validates tokens before routing to services
5. **Service-to-service** auth using client credentials grant or mTLS
6. **Token revocation** via blacklist in Redis
7. **Key rotation** with JWKS endpoint for public keys

### Q17: How do you secure a REST API?

**Answer**:
1. **Authentication**: OAuth 2.0 / JWT tokens
2. **Authorization**: RBAC/ABAC with scopes
3. **Rate limiting**: Prevent abuse and brute force
4. **Input validation**: Schema validation, type checking
5. **HTTPS**: Encrypt all traffic (TLS 1.3)
6. **CORS**: Restrict cross-origin access
7. **Security headers**: CSP, HSTS, X-Frame-Options
8. **Logging & monitoring**: Audit trail, anomaly detection
9. **API versioning**: Deprecate insecure old versions
10. **Error handling**: Don't leak internal details

### Q18: How would you handle a security breach?

**Answer**:
1. **Contain**: Isolate affected systems, revoke compromised credentials
2. **Assess**: Determine scope, what data was accessed/modified
3. **Eradicate**: Remove the attack vector (patch, fix vulnerability)
4. **Recover**: Restore from backups if needed, verify integrity
5. **Notify**: Inform affected users, comply with regulations (GDPR 72h)
6. **Learn**: Post-mortem, update security controls, improve monitoring
7. **Document**: Maintain incident report for compliance and future reference

### Q19: Design a system for managing API keys at scale.

**Answer**:
1. **Generation**: Cryptographically random keys with prefix for identification
2. **Storage**: Store hashed keys (SHA-256) — never store plaintext
3. **Distribution**: Show key only once at creation, provide secure download
4. **Scoping**: Associate keys with permissions, rate limits, IP restrictions
5. **Rotation**: Support multiple active keys, seamless rotation
6. **Revocation**: Immediate revocation capability, propagate to all services
7. **Monitoring**: Track usage per key, alert on anomalies
8. **Expiration**: TTL-based expiration, renewal workflow

## Scenario-Based Questions

### Q20: You discover a SQL injection vulnerability in production. What do you do?

**Answer**:
1. **Immediate**: Deploy a WAF rule to block the specific attack pattern
2. **Short-term**: Patch the vulnerable code with parameterized queries
3. **Assess**: Check logs for exploitation attempts, determine if data was accessed
4. **Rotate**: Change database credentials, invalidate affected sessions
5. **Scan**: Check all similar code paths for the same vulnerability
6. **Long-term**: Implement automated SAST/DAST scanning, code review requirements
7. **Notify**: If data was compromised, follow breach notification procedures

### Q21: A developer accidentally committed AWS keys to a public GitHub repo. What's your response?

**Answer**:
1. **Immediately** rotate the compromised keys (AWS IAM console)
2. **Check** CloudTrail logs for unauthorized API calls since the keys were exposed
3. **Revoke** any resources created by unauthorized access
4. **Remove** the secrets from git history (BFG Repo-Cleaner or `git filter-branch`)
5. **Scan** for other secrets in the repository
6. **Implement** pre-commit hooks and secret scanning (gitleaks)
7. **Enable** GitHub secret scanning alerts
8. **Document** the incident and update security training

### Q22: How would you implement SSO for an organization with 50 internal applications?

**Answer**:
1. **Identity Provider**: Deploy an IdP (Okta, Azure AD, Keycloak)
2. **Protocol**: Use OIDC for modern apps, SAML for legacy apps
3. **Directory**: Sync with existing directory (Active Directory/LDAP)
4. **MFA**: Enforce MFA for all users (TOTP, WebAuthn)
5. **Provisioning**: SCIM for automated user provisioning/deprovisioning
6. **Session management**: Centralized session with configurable timeout
7. **Migration**: Gradual rollout — start with low-risk apps
8. **Monitoring**: Audit login events, detect anomalies

### Q23: How do you ensure data security in a multi-tenant SaaS application?

**Answer**:
1. **Tenant isolation**: Row-level security, separate schemas, or separate databases
2. **Access control**: Include tenant_id in every query, middleware validation
3. **Encryption**: Encrypt data at rest (per-tenant keys) and in transit
4. **Network isolation**: VPC peering, private endpoints for enterprise tenants
5. **Audit logging**: Per-tenant audit trails
6. **Data residency**: Region-specific storage for compliance (GDPR)
7. **Testing**: Automated tests for cross-tenant access prevention
8. **Backup isolation**: Tenant-scoped backup and restore capabilities

## Rapid-Fire Questions

| Question | Answer |
|----------|--------|
| HTTPS vs HTTP? | HTTPS adds TLS encryption. Always use HTTPS. |
| Salt vs Pepper? | Salt is per-user, stored with hash. Pepper is global, stored separately (e.g., in config). |
| Symmetric vs Asymmetric key size? | 256-bit symmetric ≈ 3072-bit asymmetric (RSA). |
| JWT vs Session? | JWT for APIs/stateless. Session for web apps/stateful. |
| OAuth vs OIDC? | OAuth for authorization. OIDC adds authentication. |
| Encryption vs Hashing? | Encryption is reversible (with key). Hashing is one-way. |
| TLS vs SSL? | SSL is deprecated. TLS 1.2+ is current standard. |
| CSP header? | Controls which resources browser can load. Prevents XSS. |
| CORS? | Controls which origins can access your API. |
| HSTS? | Forces browsers to use HTTPS. Prevents downgrade attacks. |
