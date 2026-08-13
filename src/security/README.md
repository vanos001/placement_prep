# Security & Cryptography

## Overview

Security is a critical concern for every software engineer. Understanding security principles, attack vectors, and defensive mechanisms is essential for building robust systems. This section covers the fundamental concepts of security and cryptography that are commonly tested in technical interviews and essential in real-world software development.

## The CIA Triad

The CIA Triad is the foundational model of information security, consisting of three core principles:

```
┌─────────────────────────────────────┐
│           CIA Triad                 │
│                                     │
│    Confidentiality                  │
│         ▲                           │
│        / \                          │
│       /   \                         │
│      /     \                        │
│     /       \                       │
│    /         \                      │
│   Integrity ←── Availability        │
│                                     │
└─────────────────────────────────────┘
```

### Confidentiality

Confidentiality ensures that information is accessible only to authorized individuals.

- **Encryption**: Transform data so only authorized parties can read it
- **Access Control**: Restrict who can access what resources
- **Authentication**: Verify the identity of users
- **Data Classification**: Label data by sensitivity level

**Example**: Encrypting database connections with TLS, using role-based access to limit data exposure.

### Integrity

Integrity ensures that information is accurate, complete, and unaltered.

- **Hashing**: Detect unauthorized modifications
- **Digital Signatures**: Verify data origin and integrity
- **Checksums**: Validate data hasn't been corrupted
- **Version Control**: Track and audit changes

**Example**: Using SHA-256 hashes to verify file integrity, digital signatures on software packages.

### Availability

Availability ensures that systems and data are accessible when needed.

- **Redundancy**: Eliminate single points of failure
- **Load Balancing**: Distribute traffic across servers
- **DDoS Protection**: Defend against denial-of-service attacks
- **Disaster Recovery**: Restore systems after failures

**Example**: Multi-region deployments, CDN for static assets, auto-scaling groups.

## Attack Surfaces

An attack surface is the sum of all points where an unauthorized user can try to enter or extract data from a system.

### Network Attack Surface

```
Internet
    │
    ▼
┌─────────────┐
│   Firewall   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Load Balancer│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Web Server  │ ◄── HTTP headers, TLS config, ports
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Application  │ ◄── Input fields, API endpoints, auth
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Database    │ ◄── Queries, stored procedures, access
└─────────────┘
```

**Key concerns**: Open ports, unpatched services, misconfigured firewalls, unencrypted traffic.

### Software Attack Surface

- **Input fields**: Forms, URL parameters, headers, cookies
- **API endpoints**: REST, GraphQL, WebSocket connections
- **File uploads**: Images, documents, executables
- **Third-party dependencies**: Libraries with known vulnerabilities
- **Configuration files**: Exposed secrets, debug modes

### Human Attack Surface

- **Social engineering**: Phishing, pretexting, baiting
- **Insider threats**: Malicious or negligent employees
- **Physical access**: Unauthorized entry to facilities
- **Credential theft**: Password reuse, weak passwords

## Defense in Depth

Defense in depth is a security strategy that employs multiple layers of controls.

```
┌─────────────────────────────────────────┐
│ Layer 1: Physical Security              │
│ ┌─────────────────────────────────────┐ │
│ │ Layer 2: Network Security           │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ Layer 3: Host Security          │ │ │
│ │ │ ┌─────────────────────────────┐ │ │ │
│ │ │ │ Layer 4: Application Sec    │ │ │ │
│ │ │ │ ┌─────────────────────────┐ │ │ │ │
│ │ │ │ │ Layer 5: Data Security  │ │ │ │ │
│ │ │ │ └─────────────────────────┘ │ │ │ │
│ │ │ └─────────────────────────────┘ │ │ │
│ │ └─────────────────────────────────┘ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Principle**: If one layer fails, other layers still provide protection.

## Security Principles

### Principle of Least Privilege

Grant only the minimum permissions necessary to perform a task.

```python
# Bad: Admin access for a read-only report
class ReportService:
    def generate_report(self):
        db = connect(username="admin", password="admin_pass")
        return db.query("SELECT * FROM sales")

# Good: Read-only access with specific tables
class ReportService:
    def generate_report(self):
        db = connect(username="report_reader", password="...")
        return db.query("SELECT date, amount FROM sales WHERE date > ?", [last_month])
```

### Zero Trust Architecture

Never trust, always verify — regardless of network location.

```
Traditional: "Inside the network? You're trusted."
Zero Trust:  "Every request must be authenticated and authorized."
```

**Core tenets**:
1. Verify explicitly (authenticate and authorize every access)
2. Use least privilege access
3. Assume breach (minimize blast radius)

### Security by Design

Build security into the system from the beginning, not as an afterthought.

- Threat modeling during design phase
- Secure defaults (deny by default)
- Fail secure (deny access on error, don't grant it)
- Keep it simple (complexity breeds vulnerabilities)

## Common Security Threats

| Threat | Description | Impact |
|--------|-------------|--------|
| SQL Injection | Inject malicious SQL via user input | Data breach, data loss |
| XSS | Inject malicious scripts in web pages | Session hijacking, defacement |
| CSRF | Trick users into unwanted actions | Unauthorized transactions |
| Man-in-the-Middle | Intercept communications | Data theft, impersonation |
| DDoS | Overwhelm systems with traffic | Service unavailability |
| Ransomware | Encrypt data for extortion | Data loss, financial damage |
| Supply Chain | Compromise dependencies | Widespread vulnerability |

## Topics in This Section

- [Authentication](authentication.md) - How systems verify identity
- [Authorization](authorization.md) - How systems control access
- [Web Security](web-security.md) - OWASP Top 10 and web vulnerabilities
- [Cryptography](cryptography.md) - Encryption, hashing, and digital signatures
- [Secrets Management](secrets-management.md) - Managing keys and credentials
- [Interview Questions](interview-questions.md) - Security interview preparation

## Interview Tips

1. **Think like an attacker**: Understand how systems can be exploited
2. **Defense in depth**: Always propose multiple layers of protection
3. **Trade-offs**: Security vs. usability, security vs. performance
4. **Real-world examples**: Reference actual breaches and how they were exploited
5. **Practical knowledge**: Know how to implement security controls in code

## Key Takeaways

- Security is everyone's responsibility, not just the security team
- The CIA Triad guides all security decisions
- Defense in depth means multiple layers of protection
- Security by design is cheaper than security as an afterthought
- Understand both attacks and defenses for interviews
