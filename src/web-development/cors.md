# CORS (Cross-Origin Resource Sharing)

CORS is a security mechanism that allows controlled access to resources from different origins. It's one of the most commonly misunderstood web security topics and a frequent source of developer frustration.

## Same-Origin Policy

The **Same-Origin Policy (SOP)** is the fundamental security model of the web. It restricts how a document or script loaded from one origin can interact with a resource from another origin.

### What is an Origin?

An origin is defined by the combination of three components:

- **Protocol** (scheme) — `http`, `https`, `ftp`
- **Hostname** (domain) — `example.com`, `api.example.com`
- **Port** — `80`, `443`, `3000`

```
http://example.com:80/path
      │           │   │
   protocol    host port
```

Two URLs are **same-origin** if and only if all three components match exactly.

### Same-Origin Examples

| URL A | URL B | Same Origin? | Reason |
|-------|-------|-------------|--------|
| `http://example.com` | `http://example.com/page` | ✅ Yes | Same protocol, host, port |
| `http://example.com` | `https://example.com` | ❌ No | Different protocol |
| `http://example.com` | `http://api.example.com` | ❌ No | Different host |
| `http://example.com:80` | `http://example.com:8080` | ❌ No | Different port |

### What SOP Restricts

- **XHR/Fetch requests** — cannot make AJAX requests to different origins
- **DOM access** — `iframe.contentWindow.document` is blocked cross-origin
- **Cookie access** — cookies are domain-specific

### What SOP Does NOT Restrict

- `<script src="...">` — loading JavaScript from any origin (this enables JSONP)
- `<link href="...">` — loading CSS from any origin
- `<img src="...">` — loading images from any origin
- `<form action="...">` — submitting forms to any origin
- `<video>`, `<audio>`, `<object>`, `<embed>` — loading media from any origin

These are **"write"** operations — you can send data to other origins. The restriction is on **"reading"** responses from other origins.

## What is CORS?

CORS is a mechanism that uses additional HTTP headers to tell browsers to give a web application running at one origin access to selected resources from a different origin. It relaxes the same-origin policy in a controlled way.

A web application makes a **cross-origin HTTP request** when it requests a resource from a different origin than its own. CORS allows the server to declare who can access its resources.

## Types of CORS Requests

### Simple Requests

A request is "simple" if it meets ALL of these criteria:

- **Method** — `GET`, `HEAD`, or `POST`
- **Headers** — only safe headers: `Accept`, `Accept-Language`, `Content-Language`, `Content-Type`
- **Content-Type** — only `application/x-www-form-urlencoded`, `multipart/form-data`, or `text/plain`
- **No event listeners** on `XMLHttpRequestUpload`
- **No `ReadableStream`** in the request

Simple requests are sent directly to the server. The browser includes the `Origin` header, and the server responds with `Access-Control-Allow-Origin`. If the header doesn't match, the browser blocks the response from JavaScript.

```
# Request
GET /api/data HTTP/1.1
Host: api.example.com
Origin: https://myapp.com

# Response
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://myapp.com
Content-Type: application/json

{"data": "value"}
```

### Preflight Requests

For non-simple requests, the browser sends a **preflight** request — an `OPTIONS` request that asks the server if the actual request is allowed:

```
# Preflight request
OPTIONS /api/data HTTP/1.1
Host: api.example.com
Origin: https://myapp.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: Content-Type, Authorization

# Preflight response
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://myapp.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

After the preflight succeeds, the browser sends the actual request:

```
# Actual request
PUT /api/data HTTP/1.1
Host: api.example.com
Origin: https://myapp.com
Content-Type: application/json
Authorization: Bearer token123

{"update": "data"}
```

### Why Preflight Exists

The preflight mechanism ensures the server explicitly opts in to receiving cross-origin requests with non-simple characteristics. Without it, existing servers could receive unexpected cross-origin requests (e.g., `PUT` with `Content-Type: application/json`) that they weren't designed to handle, potentially causing security issues.

## Access-Control Headers

### Response Headers (Server → Browser)

#### Access-Control-Allow-Origin

```
Access-Control-Allow-Origin: https://example.com
Access-Control-Allow-Origin: *
```

- Specifies which origin(s) can access the resource
- `*` allows any origin (but NOT with credentials)
- Must be a single origin or `*`, not a comma-separated list
- The browser checks this against the request's `Origin` header

#### Access-Control-Allow-Methods

```
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
```

Specifies which HTTP methods are allowed. Only relevant for preflight responses.

#### Access-Control-Allow-Headers

```
Access-Control-Allow-Headers: Content-Type, Authorization, X-Custom-Header
```

Specifies which non-simple headers the client can send. Only relevant for preflight responses.

#### Access-Control-Allow-Credentials

```
Access-Control-Allow-Credentials: true
```

Indicates whether the response can be exposed when the request includes credentials (cookies, HTTP auth). When this is `true`:

- `Access-Control-Allow-Origin` cannot be `*` — must be a specific origin
- The request must be made with `credentials: 'include'` (fetch) or `withCredentials: true` (XHR)

#### Access-Control-Expose-Headers

```
Access-Control-Expose-Headers: X-Custom-Header, X-Request-Id
```

By default, only "safe" response headers are accessible to JavaScript in a cross-origin response. This header exposes additional headers.

#### Access-Control-Max-Age

```
Access-Control-Max-Age: 86400
```

How long (in seconds) the preflight response can be cached. Reduces the number of preflight requests.

### Request Headers (Browser → Server)

#### Origin

```
Origin: https://myapp.com
```

Always sent automatically by the browser in cross-origin requests. Indicates the origin of the request.

#### Access-Control-Request-Method

```
Access-Control-Request-Method: PUT
```

Sent in preflight requests to indicate which method will be used in the actual request.

#### Access-Control-Request-Headers

```
Access-Control-Request-Headers: Content-Type, Authorization
```

Sent in preflight requests to indicate which non-simple headers will be used in the actual request.

## Common CORS Errors and Solutions

### Error: "No 'Access-Control-Allow-Origin' header is present"

**Cause:** The server doesn't include the `Access-Control-Allow-Origin` header.

**Solution:** Configure the server to include the header:

```javascript
// Express.js
const cors = require('cors');
app.use(cors()); // Allow all origins

// Or configure specific origins
app.use(cors({
  origin: 'https://myapp.com',
  credentials: true
}));
```

### Error: "The value of the 'Access-Control-Allow-Origin' header must not be '*' when credentials flag is true"

**Cause:** Request includes credentials but server responds with `*`.

**Solution:** Set the specific origin instead of `*`:

```javascript
app.use(cors({
  origin: 'https://myapp.com', // specific origin, not *
  credentials: true
}));
```

### Error: "Request header field content-type is not allowed by Access-Control-Allow-Headers"

**Cause:** The preflight response doesn't include `Content-Type` in `Access-Control-Allow-Headers`.

**Solution:**

```javascript
app.use(cors({
  origin: 'https://myapp.com',
  allowedHeaders: ['Content-Type', 'Authorization']
}));
```

### Error: "Method PUT is not allowed by Access-Control-Allow-Methods"

**Cause:** The preflight response doesn't allow the HTTP method being used.

**Solution:**

```javascript
app.use(cors({
  origin: 'https://myapp.com',
  methods: ['GET', 'POST', 'PUT', 'DELETE']
}));
```

## CORS Configuration Patterns

### Allow Multiple Origins

```javascript
const allowedOrigins = ['https://app.com', 'https://admin.com'];

app.use(cors({
  origin: function(origin, callback) {
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  }
}));
```

### Dynamic Origin with Pattern

```javascript
app.use(cors({
  origin: function(origin, callback) {
    if (!origin || /\.example\.com$/.test(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed'));
    }
  }
}));
```

### Nginx Configuration

```nginx
location /api/ {
    # Allow specific origin
    add_header 'Access-Control-Allow-Origin' 'https://myapp.com' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
    add_header 'Access-Control-Max-Age' 86400 always;

    # Handle preflight
    if ($request_method = 'OPTIONS') {
        return 204;
    }

    proxy_pass http://backend;
}
```

## CORS vs Other Cross-Origin Techniques

### CORS vs JSONP

| Aspect | CORS | JSONP |
|--------|------|-------|
| HTTP Methods | All methods | GET only |
| Error Handling | Proper HTTP status codes | No error handling |
| Security | More secure | Vulnerable to XSS |
| Headers | Custom headers supported | No custom headers |
| Browser Support | All modern browsers | Legacy only |

### CORS vs Proxy

Instead of dealing with CORS, you can proxy requests through your own server:

```
Browser → Your Server → External API
```

- No CORS issues (same-origin request to your server)
- Adds latency (extra hop)
- Hides API keys from the client
- Useful when you can't modify the external server

### CORS with Credentials

```javascript
// Fetch API
fetch('https://api.example.com/data', {
  credentials: 'include', // send cookies
  headers: {
    'Content-Type': 'application/json'
  }
});

// XMLHttpRequest
const xhr = new XMLHttpRequest();
xhr.open('GET', 'https://api.example.com/data');
xhr.withCredentials = true; // send cookies
xhr.send();
```

When `credentials: 'include'` is used, the server MUST respond with:
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Origin: <specific-origin>` (not `*`)

## Security Implications

### Overly Permissive CORS

Using `Access-Control-Allow-Origin: *` or reflecting any origin effectively disables the same-origin policy. While convenient for public APIs, this can expose users to:

- **CSRF-like attacks** — malicious sites can make authenticated requests
- **Data theft** — malicious sites can read responses from authenticated endpoints

### Best Practices

- **Whitelist origins** — only allow specific, trusted origins
- **Don't reflect Origin blindly** — validate against a known list
- **Use credentials carefully** — only when needed, with specific origins
- **Restrict methods and headers** — only allow what's necessary
- **Set appropriate max-age** — balance caching with flexibility

### CORS Doesn't Prevent...

CORS is enforced by the browser. It doesn't prevent:

- Server-to-server requests (no browser involved)
- Requests from non-browser clients (curl, Postman, mobile apps)
- The request from being sent — only the response from being read by JavaScript

## Key Interview Points

- The same-origin policy compares protocol, hostname, and port
- CORS relaxes the same-origin policy with server consent
- Simple requests (GET/POST with simple headers) don't need preflight
- Non-simple requests trigger an OPTIONS preflight request
- `Access-Control-Allow-Origin: *` cannot be used with credentials
- CORS is browser-enforced — it doesn't protect against non-browser clients
- Preflight responses can be cached with `Access-Control-Max-Age`
- Common errors stem from missing headers, method restrictions, or credential mismatches
