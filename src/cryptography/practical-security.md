# Practical Web Security

This chapter covers the essential security practices every web developer must understand. These are not optional nice-to-haves—they are baseline requirements for building production applications. Most OWASP Top 10 vulnerabilities result from failing to implement these fundamentals.

## Secure Cookie Attributes

Cookies are a primary attack vector for session hijacking. Configure them correctly:

```http
Set-Cookie: session_id=abc123; \
  Secure; \
  HttpOnly; \
  SameSite=Strict; \
  Path=/; \
  Domain=.example.com; \
  Max-Age=3600
```

| Attribute | Purpose | Default | Recommendation |
|-----------|---------|---------|---------------|
| **Secure** | Cookie is only sent over HTTPS | Off | **Always set** |
| **HttpOnly** | Cookie is inaccessible to JavaScript (prevents XSS theft) | Off | **Always set for session cookies** |
| **SameSite=Strict** | Cookie is only sent for same-site requests | None | **Strict for login; Lax for general** |
| **SameSite=Lax** | Cookie sent for top-level navigations but not cross-site requests | None | Good default for most cookies |
| **Path** | Limits cookie to a specific path | Current path | Set to `/` for session cookies |
| **Domain** | Limits cookie to a specific domain (and subdomains) | Exact host | Omit unless explicitly sharing across subdomains |
| **Max-Age** | Cookie expiration in seconds | Session (browser close) | Set reasonable expiry; short for sensitive sessions |

**Common mistake:** Developers set `Secure` but forget `HttpOnly`. An XSS attack can still steal the session cookie via `document.cookie`.

## CSRF Protection (Cross-Site Request Forgery)

CSRF tricks a user's browser into making authenticated requests to your application without their knowledge. For example, if a user is logged into `bank.com` and visits `evil.com`, a malicious page can submit a form to `bank.com/transfer` using the user's cookies.

### Defense: Anti-CSRF Tokens

```python
# Flask example with Flask-WTF
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(32)
csrf = CSRFProtect(app)

# Every form now automatically includes a CSRF token:
# <input type="hidden" name="csrf_token" value="...">
```

### Defense: SameSite Cookie Attribute

`SameSite=Strict` or `SameSite=Lax` on session cookies prevents the browser from sending cookies with cross-origin requests, effectively blocking most CSRF attacks. This is now the default in modern browsers.

### Defense: Verify Origin Header

For API endpoints (especially those using Bearer tokens), verify the `Origin` or `Referer` header matches your expected domain:

```python
from flask import request, abort

@app.before_request
def verify_origin():
    allowed_origins = {"https://app.example.com", "https://admin.example.com"}
    origin = request.headers.get("Origin")
    if request.method == "POST" and origin not in allowed_origins:
        abort(403)
```

## XSS Prevention (Cross-Site Scripting)

XSS allows attackers to inject malicious scripts into pages viewed by other users. Three types exist:

| Type | Vector | Example |
|------|--------|---------|
| **Stored XSS** | Malicious input stored in the database and rendered to other users | Forum post with `<script>steal_cookie()</script>` |
| **Reflected XSS** | Malicious input in URL parameters reflected back in the response | Search page echoing `?q=<script>alert(1)</script>` |
| **DOM-based XSS** | Client-side JavaScript processes untrusted data unsafely | `innerHTML = location.hash.slice(1)` |

### Defense: Output Encoding/Escaping

**The single most effective XSS defense is context-aware output encoding.** Escape all user-supplied data based on where it appears in the HTML:

- **HTML body:** HTML entity encoding (`<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;`)
- **HTML attributes:** Attribute encoding + quotes
- **JavaScript:** JSON encoding or `\u` escaping
- **URLs:** URL encoding
- **CSS:** CSS escaping (rarely needed; avoid injecting user input into CSS)

In modern frameworks (React, Angular, Vue), output encoding is automatic by default for JSX expressions and template bindings. **Never** use `dangerouslySetInnerHTML` (React) or `[innerHTML]` (Angular) with user-supplied content.

### Defense: Content Security Policy (CSP)

CSP is an HTTP response header that restricts which resources the browser can load, effectively blocking most XSS attacks:

```http
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://cdn.example.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  connect-src 'self' https://api.example.com;
  font-src 'self' https://fonts.gstatic.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self'
```

| Directive | Purpose |
|-----------|---------|
| `default-src 'self'` | Fallback for all resource types: only same-origin |
| `script-src` | Controls JavaScript sources; avoid `'unsafe-inline'` |
| `style-src` | Controls CSS sources |
| `img-src` | Controls image sources |
| `connect-src` | Controls fetch/XHR/WebSocket targets |
| `frame-ancestors 'none'` | Prevents framing (clickjacking defense) |
| `base-uri 'self'` | Prevents base tag injection |

**Recommended approach:** Start with a restrictive policy and use `Content-Security-Policy-Report-Only` to log violations before enforcing.

## SQL Injection Prevention

SQL injection occurs when user input is concatenated directly into SQL queries. It can lead to data theft, authentication bypass, and full database compromise.

### Vulnerable Code

```python
# DANGEROUS — Never do this
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

An attacker can input `admin' OR '1'='1` to bypass authentication.

### Defense: Parameterized Queries (Prepared Statements)

```python
# SAFE — Parameterized query
cursor.execute(
    "SELECT * FROM users WHERE username = %s AND password_hash = %s",
    (username, password_hash)
)
```

The database driver handles escaping, making SQL injection impossible. This applies to all database access layers:

| Language | Library |
|----------|---------|
| Python | `psycopg2` (PostgreSQL), `sqlite3` (SQLite) |
| Java | JDBC `PreparedStatement` |
| Node.js | `pg` library parameterized queries |
| Go | `database/sql` prepared statements |
| PHP | PDO prepared statements |

### Defense: ORM

Object-relational mappers (SQLAlchemy, Django ORM, Hibernate, Prisma) generate parameterized queries by default and are safe from SQL injection—provided you don't fall back to raw SQL.

## OWASP Top 10 (2021)

| # | Category | Description | Primary Defense |
|---|----------|-------------|-----------------|
| A01 | **Broken Access Control** | Unauthorized access to resources, privilege escalation | Authorization checks on every request; deny by default |
| A02 | **Cryptographic Failures** | Weak or misconfigured encryption, exposed sensitive data | Use TLS; encrypt at rest; proper key management |
| A03 | **Injection** | SQL, NoSQL, OS command injection | Parameterized queries; input validation; least privilege DB user |
| A04 | **Insecure Design** | Flawed architecture and business logic | Threat modeling; security requirements; abuse case analysis |
| A05 | **Security Misconfiguration** | Default credentials, open cloud storage, verbose errors | Hardening checklists; infrastructure as code; disable defaults |
| A06 | **Vulnerable Components** | Using libraries with known vulnerabilities | Software composition analysis (SCA); keep dependencies updated |
| A07 | **Auth Failures** | Weak passwords, credential stuffing, session management | MFA; rate limiting; secure session handling |
| A08 | **Data Integrity Failures** | Insecure deserialization, unsigned updates | Code signing; input validation; integrity checks |
| A09 | **Logging/Monitoring Failures** | Insufficient logging, no alerting on attacks | Centralized logging; SIEM; alerting on suspicious patterns |
| A10 | **SSRF** | Server-Side Request Forgery | Allowlists for outbound URLs; disable unnecessary URL schemes |

## Secure Coding Checklist

- [ ] **TLS everywhere:** Enforce HTTPS; redirect HTTP to HTTPS; enable HSTS
- [ ] **Password hashing:** Use Argon2id (or bcrypt); never store plaintext or plain hashes
- [ ] **Secure cookies:** `Secure; HttpOnly; SameSite=Strict` on all session cookies
- [ ] **CSRF tokens:** On all state-changing endpoints (or rely on SameSite)
- [ ] **Output encoding:** Context-aware escaping for all user-supplied data
- [ ] **CSP header:** Restrict script, style, and other resource sources
- [ ] **Parameterized queries:** Never concatenate user input into SQL
- [ ] **Input validation:** Validate type, length, format on server side
- [ ] **Dependency scanning:** Use Snyk, Dependabot, or OWASP Dependency-Check
- [ ] **Least privilege:** Minimal permissions for service accounts and database users
- [ ] **Logging:** Log authentication events, access control failures, and security-relevant actions
- [ ] **Secrets management:** Use environment variables or a secrets manager; never commit secrets to VCS
- [ ] **Error handling:** Return generic errors to users; detailed errors only in logs

## References

- OWASP Top 10 (2021) — https://owasp.org/Top10/
- OWASP Cross-Site Scripting Cheat Sheet
- OWASP SQL Injection Prevention Cheat Sheet
- OWASP Cookie Security Cheat Sheet
- OWASP Content Security Policy Cheat Sheet
- NIST SP 800-63B — Digital Identity Guidelines
- RFC 6797 — HTTP Strict Transport Security (HSTS)

## Interview Questions

1. **What are the secure cookie attributes? Why is each one important?**
2. **Explain how CSRF works and how to prevent it.**
3. **What is the difference between stored and reflected XSS? How do you prevent both?**
4. **What is Content Security Policy? How would you configure it for a web application?**
5. **What is SQL injection? Show an example of a vulnerable query and how to fix it.**
6. **Walk me through the OWASP Top 10. Which three are most critical for a SaaS application?**
7. **What is the principle of least privilege? How do you apply it in a web application?**
8. **How would you handle secrets management in a CI/CD pipeline?**
9. **What is HSTS? Why is it important? What is the preload list?**
10. **A user reports that their account was compromised. What security controls would you audit?**
