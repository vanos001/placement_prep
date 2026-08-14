# Security Trade-offs

Security decisions are often framed as a tension between protection and productivity. The best security architecture makes the secure choice the easy choice—but achieving that requires deliberate trade-off analysis.

## Authentication Approaches: Session vs JWT vs OAuth

### Comparison Table

| Dimension | Server-Side Sessions | JWT (JSON Web Token) | OAuth 2.0 / OIDC |
|-----------|----------------------|---------------------|------------------|
| Storage | Server (memory, Redis, DB) | Client-side (token) | Delegated to identity provider |
| Scalability | Requires shared session store | Stateless (self-contained) | Delegated (scales with IdP) |
| Revocation | Immediate (delete session) | Difficult (wait for expiry or maintain blocklist) | Revocation endpoint at IdP |
| Size | Small (session ID) | Larger (encoded claims) | Depends on token type |
| Mobile Support | Requires persistent cookies | Works natively (Authorization header) | Designed for it |
| Security | Session ID not exposed to client | Token contains sensitive data (use RT only in HTTP-only cookie) | Delegates trust to IdP |

### When to Choose Each
- **Sessions**: When you need immediate revocation (admin logout, compromised accounts), simple server-rendered apps, when statelessness is not a requirement.
- **JWT**: Stateless microservices where each service can verify tokens independently, mobile APIs, when you want to avoid a shared session store.
- **OAuth 2.0/OIDC**: When you need third-party login (Google, GitHub), enterprise SSO (SAML), or want to delegate authentication entirely.

### Key Trade-off
Stateless authentication (JWT) trades revocation speed for scalability. Stateless is not stateless if you add a token blocklist—then you need a shared store, negating the original benefit.

---

## Encryption at Rest vs In Transit

### Encryption at Rest
Protects data stored on disk, in databases, in backups.

| Aspect | Details |
|--------|---------|
| Mechanism | AES-256 encryption of storage volumes, column-level encryption, field-level encryption in application |
| Key Management | Critical: KMS (AWS KMS, HashiCorp Vault), key rotation policies |
| Performance Impact | Minimal with hardware acceleration (AES-NI), higher for field-level |
| Compliance | Required by GDPR, HIPAA, PCI-DSS, SOC 2 |

### Encryption in Transit
Protects data moving between systems (client-server, server-server, service-service).

| Aspect | Details |
|--------|---------|
| Mechanism | TLS 1.3, mTLS for service mesh |
| Certificate Management | Let's Encrypt (automated), internal CA, cert-manager |
| Performance Impact | Minimal with TLS session resumption, hardware offload |
| Vulnerability | Man-in-the-middle attacks if improperly configured |

### Key Trade-off
Encryption adds latency (negligible with modern hardware) and operational complexity (key management, certificate rotation). The trade-off is almost always worth it—unencrypted data is a compliance and reputational risk. The real decision is where to encrypt (volume-level vs. field-level) and who manages the keys.

---

## RBAC vs ABAC

### Role-Based Access Control (RBAC)
Permissions assigned to roles; users assigned to roles.

| Aspect | Details |
|--------|---------|
| Model | User → Role → Permission |
| Simplicity | High (easy to audit and understand) |
| Flexibility | Low (cannot express fine-grained conditions) |
| Management | Low overhead (add/remove users from roles) |
| Example | `editor` role can `edit` and `view` articles |

### Attribute-Based Access Control (ABAC)
Permissions determined by attributes of the user, resource, action, and environment.

| Aspect | Details |
|--------|---------|
| Model | IF (user.department == resource.department) AND (resource.classification == "internal") THEN allow |
| Simplicity | Low (complex policy languages) |
| Flexibility | High (express any condition) |
| Management | High overhead (policy versioning, testing) |
| Example | Users can edit documents only if they are in the same department AND the document is not marked as final |

### When to Choose Each
- **RBAC**: Most applications (80%+ of access control needs), when permissions follow clear organizational roles.
- **ABAC**: Multi-tenant SaaS with complex sharing rules, healthcare (role + patient relationship), document-level permissions that depend on multiple attributes.

### Practical Approach
Most systems combine both: RBAC for coarse-grained access, ABAC for edge cases. This avoids the complexity of pure ABAC while retaining flexibility where needed.

---

## Zero Trust vs Perimeter Security

### Perimeter Security (Castle-and-Moat)
Trust everything inside the network boundary; verify at the edge.

| Aspect | Details |
|--------|---------|
| Model | Firewall/NAT protects the perimeter; internal traffic is trusted |
| Assumption | Threats come from outside |
| Weakness | Lateral movement (once inside, everything is accessible) |
| Simplicity | Historically simpler to implement |

### Zero Trust
Never trust, always verify—every request is authenticated and authorized regardless of origin.

| Aspect | Details |
|--------|---------|
| Model | Every request authenticated, encrypted, authorized with least privilege |
| Assumption | Threats can come from anywhere (including inside) |
| Strength | Limits blast radius of compromise |
| Complexity | High (identity-aware proxies, mTLS, micro-segmentation, device trust) |
| Components | Identity verification, device health checks, micro-segmentation, encrypted traffic, continuous monitoring |

### Key Trade-offs
| Dimension | Perimeter | Zero Trust |
|-----------|-----------|-----------|
| Implementation Cost | Lower (firewalls, VPNs) | Higher (mTLS, identity platforms, service mesh) |
| Operational Complexity | Lower | Higher (policy management, certificate rotation) |
| Security Against Lateral Movement | Weak | Strong |
| Developer Experience | VPN-based access (friction) | Identity-based access (transparent) |
| Best For | Small organizations, legacy systems | Cloud-native, distributed systems, regulated industries |

---

## Security vs Convenience Trade-offs

This is the meta-trade-off that underpins all security decisions.

### Common Tensions

| Security Measure | Convenience Cost | When to Accept |
|-----------------|-----------------|----------------|
| Multi-factor authentication | Extra login step | Always for sensitive accounts |
| Short token expiry (15 min) | Frequent re-authentication | Production/admin systems |
| Rotation of secrets every 30 days | Operational overhead | Production credentials |
| Network policies restricting all egress | Complex allow-lists | Production (dev can be more permissive) |
| Code review requirement for prod deploys | Slower deployment cycle | Always (automate to reduce friction) |
| Dependency scanning in CI | Build time increase | Always (automate, set severity thresholds) |
| mTLS for all service communication | Certificate management burden | Production service mesh |

### The Right Balance
The goal is not to maximize security or maximize convenience—it is to make secure practices convenient:

- **Automate**: Use tools like cert-manager, HashiCorp Vault, and CI/CD security scanning so security is enforced by default, not by willpower.
- **Tier Risk**: Apply stricter controls to production and sensitive data; relax controls for development environments with clear isolation.
- **Shift Left**: Catch security issues in development (linters, pre-commit hooks, dependency scanning) rather than in production (WAFs, runtime monitoring).

---

## Interview Questions

1. **"How would you design authentication for a microservices architecture?"**
   Use OAuth 2.0/OIDC with a centralized identity provider. Each service validates JWTs independently (stateless). Use mTLS for service-to-service communication. Store refresh tokens in an HTTP-only, secure, SameSite cookie for web clients.

2. **"When would you choose ABAC over RBAC?"**
   When permissions cannot be expressed as static roles—for example, a document management system where access depends on the user's department, the document's classification, and the time of day. RBAC is simpler and sufficient for most applications.

3. **"What is the trade-off between security and developer productivity in a CI/CD pipeline?"**
   More security gates (dependency scanning, SAST, manual approval) slow deployments. The solution is to automate security checks so they do not block developers, use fast tools (parallelized scans), and tier checks (critical checks block, informational checks report).

4. **"Why is JWT revocation hard, and how would you solve it?"**
   JWTs are self-contained and stateless, so the server cannot revoke them without a shared blocklist (adding state). Solutions: short access token expiry (15 min) + refresh token rotation, maintain a token blocklist in Redis with TTL matching token expiry, or use opaque tokens with introspection ( sacrificing statelessness).

5. **"Explain zero trust to a non-technical stakeholder."**
   Instead of a castle with one front gate (perimeter security), zero trust is like an office building where every door requires a key card—no matter if you are entering from outside or moving between rooms. It limits damage if someone gets past any single checkpoint.
