# HTTP Fundamentals

HTTP (HyperText Transfer Protocol) is the foundation of the World Wide Web. Understanding HTTP is essential for web development — every API call, page load, and asset fetch uses HTTP under the hood.

## What is HTTP?

HTTP is an application-layer protocol for transmitting hypermedia documents. It follows a **client-server model**:

- The **client** (usually a browser) sends a **request**
- The **server** processes the request and sends a **response**

Key characteristics:
- **Stateless** — each request is independent; the server doesn't remember previous requests (state is managed via cookies, tokens, etc.)
- **Text-based** (HTTP/1.1) — headers are human-readable ASCII text
- **Extensible** — new headers and methods can be added
- **Connection-oriented** (typically over TCP) — reliable, ordered delivery

## HTTP Messages

### Request Structure

```
GET /api/users?page=1 HTTP/1.1
Host: example.com
Accept: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
User-Agent: Mozilla/5.0
Connection: keep-alive

```

Components:
- **Request line** — method, path with query string, HTTP version
- **Headers** — metadata about the request
- **Empty line** — separates headers from body
- **Body** (optional) — data sent to the server (POST, PUT, PATCH)

### Response Structure

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 42
Cache-Control: max-age=3600
Date: Wed, 21 Oct 2025 07:28:00 GMT

{"users": [{"id": 1, "name": "John"}]}
```

Components:
- **Status line** — HTTP version, status code, reason phrase
- **Headers** — metadata about the response
- **Empty line** — separates headers from body
- **Body** (optional) — the response content

## HTTP Methods

### GET

Retrieves a resource. Should be **safe** (no side effects) and **idempotent** (multiple identical requests have the same effect as one).

```
GET /api/users/1 HTTP/1.1
```

- No request body
- Response body contains the resource
- Cacheable by default

### POST

Submits data to create a new resource or trigger an operation. **Not** idempotent — multiple identical requests may create multiple resources.

```
POST /api/users HTTP/1.1
Content-Type: application/json

{"name": "John", "email": "john@example.com"}
```

- Has a request body
- Typically returns `201 Created` for resource creation
- Not cacheable by default

### PUT

Replaces a resource entirely. **Idempotent** — multiple identical requests have the same effect.

```
PUT /api/users/1 HTTP/1.1
Content-Type: application/json

{"name": "John Updated", "email": "john@new.com"}
```

- Sends the complete resource representation
- If the resource doesn't exist, it may create it (depends on API design)
- Returns `200 OK` or `204 No Content`

### PATCH

Partially modifies a resource. May or may not be idempotent.

```
PATCH /api/users/1 HTTP/1.1
Content-Type: application/json

{"email": "john@new.com"}
```

- Sends only the fields to update
- More efficient than PUT for partial updates

### DELETE

Removes a resource. **Idempotent** — deleting a resource multiple times has the same effect.

```
DELETE /api/users/1 HTTP/1.1
```

- Returns `200 OK`, `204 No Content`, or `202 Accepted`
- Idempotent — deleting the same resource twice is the same as once

### HEAD

Identical to GET but returns only headers, no body. Used to check if a resource exists or to get metadata without downloading the content.

```
HEAD /api/users/1 HTTP/1.1
```

### OPTIONS

Describes the communication options for a target resource. Used in CORS preflight requests.

```
OPTIONS /api/users HTTP/1.1
```

### TRACE

Performs a message loop-back test. Rarely used and often disabled for security reasons.

### CONNECT

Establishes a tunnel to the server, typically for HTTPS through an HTTP proxy.

## Status Codes

### 1xx — Informational

- **100 Continue** — server received headers, client should send body
- **101 Switching Protocols** — server is switching protocols (WebSocket upgrade)
- **103 Early Hints** — preload resources before final response

### 2xx — Success

- **200 OK** — standard success response
- **201 Created** — resource created successfully (POST)
- **202 Accepted** — request accepted for processing, not yet completed
- **204 No Content** — success, no response body (DELETE)
- **206 Partial Content** — range request succeeded (used for video streaming, resumable downloads)

### 3xx — Redirection

- **301 Moved Permanently** — resource has a new permanent URL
- **302 Found** — temporary redirect (historically ambiguous about method change)
- **303 See Other** — redirect with GET (POST → GET pattern)
- **304 Not Modified** — resource hasn't changed (conditional request, use cached version)
- **307 Temporary Redirect** — temporary redirect, preserves HTTP method
- **308 Permanent Redirect** — permanent redirect, preserves HTTP method (unlike 301)

### 4xx — Client Errors

- **400 Bad Request** — malformed request syntax
- **401 Unauthorized** — authentication required (misnamed — it's about authentication, not authorization)
- **403 Forbidden** — server understood but refuses to authorize
- **404 Not Found** — resource doesn't exist
- **405 Method Not Allowed** — HTTP method not supported for this resource
- **408 Request Timeout** — server timed out waiting for the request
- **409 Conflict** — request conflicts with current state (e.g., duplicate resource)
- **413 Payload Too Large** — request body exceeds server limit
- **415 Unsupported Media Type** — media type not supported
- **422 Unprocessable Entity** — request is well-formed but semantically invalid
- **429 Too Many Requests** — rate limited

### 5xx — Server Errors

- **500 Internal Server Error** — generic server error
- **501 Not Implemented** — method not supported by the server
- **502 Bad Gateway** — upstream server returned an invalid response
- **503 Service Unavailable** — server is temporarily overloaded or down
- **504 Gateway Timeout** — upstream server didn't respond in time

## HTTP Headers

### Request Headers

```
Host: example.com                    # Required in HTTP/1.1
Accept: application/json             # What content types the client accepts
Accept-Encoding: gzip, deflate, br   # Supported compression
Accept-Language: en-US, en;q=0.9     # Preferred languages
Authorization: Bearer <token>        # Authentication credentials
Cookie: session=abc123               # Cookies
User-Agent: Mozilla/5.0...           # Client identification
Referer: https://example.com/page    # Previous page URL
Content-Type: application/json       # Media type of request body
Content-Length: 42                    # Size of request body
If-None-Match: "etag-value"          # Conditional: send if ETag doesn't match
If-Modified-Since: Wed, 21 Oct...    # Conditional: send if modified since date
Cache-Control: no-cache              # Caching directives
Connection: keep-alive               # Connection management
```

### Response Headers

```
Content-Type: application/json; charset=utf-8  # Media type of response
Content-Length: 42                               # Size of response body
Content-Encoding: gzip                           # Compression used
Cache-Control: max-age=3600, public              # Caching directives
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4" # Entity tag for caching
Last-Modified: Wed, 21 Oct 2025 07:28:00 GMT    # Last modification date
Set-Cookie: session=abc; HttpOnly; Secure        # Set a cookie
Location: /api/users/2                           # Redirect URL or new resource URL
Access-Control-Allow-Origin: *                   # CORS header
Date: Wed, 21 Oct 2025 07:28:00 GMT             # When response was generated
Server: nginx                                     # Server software
Vary: Accept-Encoding                             # Headers that affect caching
X-Request-Id: abc-123                            # Request tracing
```

### Caching Headers

**Cache-Control** is the primary caching directive:

```
Cache-Control: max-age=3600          # Cache for 3600 seconds
Cache-Control: no-cache              # Must revalidate before using cache
Cache-Control: no-store              # Don't cache at all
Cache-Control: public                # Can be cached by CDNs
Cache-Control: private               # Only cache in browser, not CDNs
Cache-Control: must-revalidate       # Must check with server when stale
Cache-Control: immutable             # Resource will never change (use with max-age)
```

**ETag** and **Last-Modified** enable conditional requests:

```
# Server sends ETag
ETag: "abc123"

# Client sends conditional request
If-None-Match: "abc123"

# Server responds 304 if unchanged
HTTP/1.1 304 Not Modified
```

## HTTP/1.1 vs HTTP/2 vs HTTP/3

### HTTP/1.1

The workhorse of the web for over 15 years.

**Characteristics:**
- **Text-based** protocol
- **Persistent connections** (keep-alive) — reuse TCP connections
- **Pipelining** — send multiple requests without waiting for responses (rarely implemented due to head-of-line blocking)
- **One request per TCP connection** at a time (with pipelining disabled)
- **Header compression** — none (headers sent as plain text on every request)

**Limitations:**
- **Head-of-line blocking** — a slow response blocks all subsequent responses
- **No multiplexing** — browsers open 6-8 TCP connections per domain to work around this
- **Header overhead** — headers are sent uncompressed with every request
- **No server push** — server can only respond to requests

### HTTP/2

Major upgrade focused on performance.

**Key Features:**

1. **Binary framing** — messages are split into binary-encoded frames, more efficient to parse
2. **Multiplexing** — multiple requests and responses over a single TCP connection, interleaved as frames
3. **Header compression (HPACK)** — uses a static table, dynamic table, and Huffman encoding to compress headers
4. **Stream prioritization** — clients can indicate which resources are more important
5. **Server push** — server can proactively send resources the client hasn't requested yet
6. **Single connection** — one TCP connection per origin, reducing overhead

```
HTTP/2 Connection
├── Stream 1 (GET /index.html)
│   ├── HEADERS frame
│   └── DATA frame
├── Stream 2 (GET /style.css)
│   ├── HEADERS frame
│   └── DATA frame
└── Stream 3 (GET /script.js)
    ├── HEADERS frame
    └── DATA frame
```

**Multiplexing in action:**
All three resources load simultaneously over one connection, with frames interleaved. No more blocking.

**Server Push:**
```
Client: GET /index.html
Server: PUSH_PROMISE /style.css (I know you'll need this)
Server: PUSH_PROMISE /script.js (and this too)
Server: DATA /index.html
Server: DATA /style.css
Server: DATA /script.js
```

Server push is being deprecated in some implementations (Chrome removed it) because it's hard to use correctly and often hurts performance.

**HTTP/2 Limitations:**
- Still over TCP — TCP head-of-line blocking still exists
- If one packet is lost, ALL streams are blocked until it's retransmitted
- TLS is not technically required but all major browsers require it

### HTTP/3

The next evolution, built on **QUIC** (a UDP-based transport protocol).

**Key Changes:**

1. **QUIC instead of TCP** — UDP-based transport developed by Google
2. **No TCP head-of-line blocking** — each stream is independently reliable
3. **Built-in TLS 1.3** — encryption is mandatory, not optional
4. **0-RTT connection establishment** — previously connected clients can send data immediately
5. **Connection migration** — connections survive IP address changes (e.g., WiFi to cellular)

```
HTTP/1.1 over TCP  →  HTTP/2 over TCP  →  HTTP/3 over QUIC (UDP)
```

**Why QUIC Matters:**

With HTTP/2 over TCP, if a packet for stream 3 is lost, streams 1 and 2 are also blocked. With HTTP/3 over QUIC, only stream 3 is blocked — streams 1 and 2 continue normally.

**Connection Establishment:**

```
TCP + TLS 1.2:  3 round trips (SYN, TLS handshake)
TCP + TLS 1.3:  2 round trips (SYN, TLS handshake)
QUIC:           1 round trip (includes TLS)
QUIC 0-RTT:     0 round trips (for known servers)
```

### Comparison Table

| Feature | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---------|----------|--------|--------|
| Protocol | Text | Binary | Binary |
| Transport | TCP | TCP | QUIC (UDP) |
| Multiplexing | No | Yes | Yes |
| Header compression | No | HPACK | QPACK |
| Server push | No | Yes (deprecated) | Yes |
| HOL blocking | Connection-level | TCP-level | Stream-level |
| TLS required | No | De facto | Yes (mandatory) |
| Connection setup | 1-3 RTT | 1-3 RTT | 0-1 RTT |
| IP migration | No | No | Yes |

## HTTPS

HTTPS is HTTP over TLS (Transport Layer Security). It provides:

- **Encryption** — data is encrypted between client and server
- **Authentication** — the client can verify the server's identity via certificates
- **Integrity** — data cannot be tampered with in transit

### TLS Handshake (TLS 1.3)

```
Client → Server: ClientHello (supported ciphers, key shares)
Server → Client: ServerHello (selected cipher, key share, certificate, finished)
Client → Server: Finished
# Handshake complete, application data flows
```

TLS 1.3 reduced the handshake to 1 round trip (0-RTT for resumption).

### HTTP Strict Transport Security (HSTS)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

Tells the browser to only access the site via HTTPS for the specified duration, even if the user types `http://`.

## Content Negotiation

The client and server negotiate the format of the response:

```
# Client preferences
Accept: application/json, text/html;q=0.9
Accept-Encoding: gzip, br
Accept-Language: en-US, en;q=0.9, zh-CN;q=0.8

# Server response
Content-Type: application/json; charset=utf-8
Content-Encoding: gzip
Content-Language: en-US
Vary: Accept, Accept-Encoding
```

## Connection Management

### Keep-Alive

HTTP/1.1 uses persistent connections by default. The `Connection: keep-alive` header (or `Connection: close` to opt out) controls this.

### Timeouts

Servers and proxies have idle timeout settings. Keep-alive connections may be closed after a period of inactivity. Clients should handle `Connection reset` gracefully.

## Key Interview Points

- HTTP is stateless — state is managed via cookies, tokens, or session IDs
- GET is safe and idempotent; POST is neither; PUT and DELETE are idempotent
- 301 vs 302 vs 307 vs 308 — know the method-preserving behavior differences
- 401 is about authentication; 403 is about authorization
- HTTP/2 introduced multiplexing, binary framing, and header compression
- HTTP/3 uses QUIC (UDP) to eliminate TCP head-of-line blocking
- 304 Not Modified enables conditional requests with ETag/Last-Modified
- Cache-Control directives control browser and CDN caching behavior
- HTTPS provides encryption, authentication, and integrity
- HSTS forces browsers to use HTTPS
