# HTTP and HTTPS

## Introduction

The **Hypertext Transfer Protocol (HTTP)** is the foundation of the World Wide Web. Defined initially in RFC 1945 (HTTP/1.0) and refined in RFC 9110–9114 (HTTP/1.1, HTTP/2, HTTP/3), HTTP is an application-layer protocol for transmitting hypermedia documents. **HTTPS** adds a TLS encryption layer for security. Understanding HTTP is essential for Linux administrators who manage web servers (Nginx, Apache, Caddy), reverse proxies, load balancers, and API endpoints.

## HTTP Request and Response

HTTP is a **request-response** protocol: a client sends a request, and a server returns a response.

### Request Structure

```http
GET /api/users?page=1 HTTP/1.1
Host: api.example.com
User-Agent: curl/8.4.0
Accept: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
Connection: keep-alive
```

| Component | Description |
|-----------|-------------|
| **Request line** | Method + URI + HTTP version |
| **Headers** | Key-value metadata (Host, User-Agent, Accept, etc.) |
| **Empty line** | Separates headers from body |
| **Body** | Optional data (POST/PUT/PATCH) |

### Response Structure

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: 256
Cache-Control: max-age=3600
Server: nginx/1.24.0
Date: Mon, 15 Jan 2024 12:00:00 GMT
Connection: keep-alive

{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
```

## HTTP Methods

| Method | Purpose | Body? | Idempotent | Safe | RFC |
|--------|---------|-------|------------|------|-----|
| **GET** | Retrieve resource | No | Yes | Yes | 9110 §9.3.1 |
| **HEAD** | Like GET, no body returned | No | Yes | Yes | 9110 §9.3.2 |
| **POST** | Create resource / submit data | Yes | No | No | 9110 §9.3.3 |
| **PUT** | Replace resource entirely | Yes | Yes | No | 9110 §9.3.4 |
| **PATCH** | Partial update | Yes | No | No | 5789 |
| **DELETE** | Remove resource | Optional | Yes | No | 9110 §9.3.5 |
| **OPTIONS** | Describe communication options | Optional | Yes | Yes | 9110 §9.3.7 |
| **TRACE** | Loop-back test | No | Yes | Yes | 9110 §9.3.8 |
| **CONNECT** | Establish tunnel (for HTTPS proxy) | No | No | No | 9110 §9.3.6 |

**Practical examples with curl:**

```bash
# GET request
$ curl -v https://api.example.com/users/1
> GET /users/1 HTTP/2
> Host: api.example.com
> User-Agent: curl/8.4.0
> Accept: */*
>
< HTTP/2 200
< content-type: application/json
< content-length: 52
<
{"id": 1, "name": "Alice", "email": "alice@example.com"}

# POST with JSON body
$ curl -X POST https://api.example.com/users \
    -H "Content-Type: application/json" \
    -d '{"name": "Charlie", "email": "charlie@example.com"}'

# PUT to replace a resource
$ curl -X PUT https://api.example.com/users/1 \
    -H "Content-Type: application/json" \
    -d '{"name": "Alice Smith", "email": "alice.smith@example.com"}'

# PATCH for partial update
$ curl -X PATCH https://api.example.com/users/1 \
    -H "Content-Type: application/json" \
    -d '{"email": "newalice@example.com"}'

# DELETE
$ curl -X DELETE https://api.example.com/users/1

# HEAD request (headers only)
$ curl -I https://example.com/
HTTP/2 200
content-type: text/html; charset=UTF-8
content-length: 1256
server: nginx/1.24.0

# OPTIONS (check allowed methods)
$ curl -X OPTIONS https://api.example.com/users -v
< HTTP/2 200
< allow: GET, POST, HEAD, OPTIONS
```

## HTTP Status Codes

Status codes indicate the result of a request. They are grouped into five classes:

```mermaid
graph TB
    subgraph "HTTP Status Code Classes"
        A["<b>1xx Informational</b><br>Request received, continue"]
        B["<b>2xx Success</b><br>Request accepted"]
        C["<b>3xx Redirection</b><br>Further action needed"]
        D["<b>4xx Client Error</b><br>Bad request"]
        E["<b>5xx Server Error</b><br>Server failed"]
    end
```

### Common Status Codes

| Code | Name | Meaning | Typical Cause |
|------|------|---------|---------------|
| **101** | Switching Protocols | Upgrading to WebSocket | `Upgrade: websocket` header |
| **200** | OK | Success | Normal response |
| **201** | Created | Resource created | Successful POST |
| **204** | No Content | Success, no body | Successful DELETE |
| **301** | Moved Permanently | Resource permanently moved | URL change |
| **302** | Found | Temporary redirect | Temporary URL |
| **304** | Not Modified | Use cached version | `If-None-Match` / `If-Modified-Since` |
| **400** | Bad Request | Malformed request | Invalid JSON, missing parameters |
| **401** | Unauthorized | Authentication required | Missing or invalid token |
| **403** | Forbidden | Access denied | Valid auth but insufficient permissions |
| **404** | Not Found | Resource doesn't exist | Wrong URL |
| **405** | Method Not Allowed | HTTP method not supported | POST to a read-only endpoint |
| **408** | Request Timeout | Client too slow | Slow connection |
| **409** | Conflict | Resource conflict | Duplicate creation |
| **429** | Too Many Requests | Rate limited | API throttling |
| **500** | Internal Server Error | Unhandled exception | Application bug |
| **502** | Bad Gateway | Upstream error | Proxy can't reach backend |
| **503** | Service Unavailable | Temporarily overloaded | Maintenance or overload |
| **504** | Gateway Timeout | Upstream timeout | Backend too slow |

```bash
# Check status code only
$ curl -s -o /dev/null -w "%{http_code}\n" https://example.com/
200

# Follow redirects and show all status codes
$ curl -L -v https://example.com/old-page 2>&1 | grep "< HTTP"
< HTTP/1.1 301 Moved Permanently
< HTTP/2 200

# Check a specific error
$ curl -s -w "\n%{http_code}" https://api.example.com/protected
{"error": "Unauthorized", "message": "Invalid token"}
401
```

## HTTP Headers

### Request Headers

```bash
# Common request headers set by curl
$ curl -v https://example.com/ \
    -H "Accept: text/html" \
    -H "Accept-Language: en-US" \
    -H "Cache-Control: no-cache" \
    -H "If-None-Match: \"abc123\"" \
    -H "Authorization: Bearer token123"

# Set a custom User-Agent
$ curl -A "Mozilla/5.0 (X11; Linux x86_64) Custom/1.0" https://example.com/

# Send cookies
$ curl -b "session=abc123; theme=dark" https://example.com/
```

### Response Headers

```bash
# View all response headers
$ curl -I https://example.com/
HTTP/2 200
content-type: text/html; charset=UTF-8
content-length: 1256
date: Mon, 15 Jan 2024 12:00:00 GMT
server: nginx/1.24.0
cache-control: public, max-age=3600
etag: "abc123"
strict-transport-security: max-age=31536000; includeSubDomains
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
content-security-policy: default-src 'self'
```

## HTTPS and TLS

HTTPS = HTTP over TLS (Transport Layer Security). TLS provides:
- **Encryption**: Prevents eavesdropping
- **Authentication**: Verifies server identity via certificates
- **Integrity**: Prevents tampering

### TLS Handshake (TLS 1.3)

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Client->>Server: ClientHello<br>Supported TLS versions, cipher suites<br>Key share (ECDHE)
    Server->>Client: ServerHello<br>Selected cipher suite, key share<br>Certificate, CertificateVerify<br>Finished
    Note over Client: Verify certificate<br>Derive session keys
    Client->>Server: Finished
    Note over Client,Server: Encrypted HTTP traffic begins
```

**TLS 1.3 improvements over 1.2:**
- 1-RTT handshake (vs 2-RTT)
- 0-RTT resumption (reduced latency)
- Removed insecure cipher suites (RC4, 3DES, RSA key exchange)
- Encrypted certificate exchange

```bash
# Test TLS with openssl
$ openssl s_client -connect example.com:443 -tls1_3
CONNECTED(00000003)
---
Certificate chain
 0 s:CN=example.com
   i:C=US, O=Let's Encrypt, CN=R3
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIFazCCBFOgAwIBAgISA...
-----END CERTIFICATE-----
---
SSL handshake has read 3521 bytes and written 409 bytes
Verification: OK
---
New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
Protocol: TLSv1.3
```

### curl with HTTPS

```bash
# Default: verify certificates
$ curl https://example.com/

# Show TLS details
$ curl -v https://example.com/ 2>&1 | grep -E "SSL|TLS|certificate"

# Skip certificate verification (NEVER in production)
$ curl -k https://self-signed.example.com/

# Use specific CA bundle
$ curl --cacert /etc/ssl/certs/ca-certificates.crt https://example.com/

# Client certificate authentication
$ curl --cert client.pem --key client-key.pem https://api.example.com/

# Check certificate expiry
$ curl -vI https://example.com/ 2>&1 | grep "expire date"
*  expire date: Apr 15 12:00:00 2024 GMT
```

## HTTP/1.1

The workhorse of the web for over two decades.

**Key features:**
- **Persistent connections** (`Connection: keep-alive`): Reuse TCP connections
- **Pipelining**: Send multiple requests without waiting (rarely used due to head-of-line blocking)
- **Chunked transfer encoding**: Stream data without knowing content length
- **Host header**: Required (enables virtual hosting)

**Limitations:**
- Text-based protocol (parsing overhead)
- Head-of-line blocking at the application layer
- One request per TCP connection at a time (without pipelining)

```bash
# HTTP/1.1 request with keep-alive
$ curl --http1.1 -v https://example.com/
> GET / HTTP/1.1
> Host: example.com
> Connection: keep-alive
>
< HTTP/1.1 200 OK
< Connection: keep-alive
< Content-Type: text/html
```

## HTTP/2

Defined in RFC 9113, HTTP/2 was derived from Google's SPDY protocol. It addresses HTTP/1.1's performance limitations.

**Key features:**
- **Binary framing**: Messages are split into binary frames (not text)
- **Multiplexing**: Multiple requests/responses over a single TCP connection
- **Header compression**: HPACK algorithm reduces redundant headers
- **Server push**: Server can proactively send resources (deprecated in practice)
- **Stream prioritization**: Weighted dependency trees

```mermaid
graph LR
    subgraph "HTTP/1.1 -- Multiple Connections"
        C1["Connection 1<br>GET /index.html"]
        C2["Connection 2<br>GET /style.css"]
        C3["Connection 3<br>GET /app.js"]
    end

    subgraph "HTTP/2 -- Single Connection"
        S["TCP Connection"]
        S --> F1["Stream 1: GET /index.html"]
        S --> F2["Stream 3: GET /style.css"]
        S --> F3["Stream 5: GET /app.js"]
    end
```

```bash
# Test HTTP/2 support
$ curl --http2 -v https://example.com/ 2>&1 | grep "HTTP/2"
< HTTP/2 200

# ALPN negotiation (HTTP/2 over TLS)
$ openssl s_client -connect example.com:443 -alpn h2,http/1.1 2>&1 | grep "ALPN"
ALPN protocol: h2

# Check if server supports HTTP/2
$ curl -sI https://example.com/ | head -1
HTTP/2 200

# Wireshark filter for HTTP/2 frames
# http2.streamid == 1
# http2.type == 1 (HEADERS)
# http2.type == 0 (DATA)
```

## HTTP/3 (QUIC)

HTTP/3 (RFC 9114) runs over **QUIC** (RFC 9000) instead of TCP. QUIC is a UDP-based transport protocol that eliminates TCP's head-of-line blocking.

**Key advantages:**
- **0-RTT connection establishment** (with cached keys)
- **No head-of-line blocking**: Independent streams don't block each other
- **Connection migration**: Survives IP address changes (Wi-Fi → cellular)
- **Built-in TLS 1.3**: Encryption is mandatory and integrated
- **Improved congestion control**: Better loss recovery

```mermaid
graph TB
    subgraph "HTTP/2 over TCP+TLS"
        H2["HTTP/2 Frames"] --> TLS["TLS 1.2/1.3"]
        TLS --> TCP["TCP"]
        TCP --> IP2["IP"]
    end

    subgraph "HTTP/3 over QUIC"
        H3["HTTP/3 Frames"] --> QUIC["QUIC<br>(UDP-based, built-in TLS 1.3)"]
        QUIC --> UDP["UDP"]
        UDP --> IP3["IP"]
    end
```

```bash
# Test HTTP/3 support (requires curl with QUIC support)
$ curl --http3 -v https://cloudflare.com/ 2>&1 | grep "HTTP/3"
< HTTP/3 200

# Check with ngtcp2 or quiche clients
$ openssl s_client -connect cloudflare.com:443 -quic -alpn h3

# Verify UDP port 443 is open (QUIC uses UDP)
$ ss -ulnp | grep :443
```

**Connection comparison:**

| Feature | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---------|----------|--------|--------|
| Transport | TCP | TCP | QUIC (UDP) |
| Multiplexing | No (pipelining) | Yes | Yes |
| HOL Blocking | Application layer | TCP layer | None |
| Header Compression | None | HPACK | QPACK |
| TLS | Optional | Optional | Mandatory |
| 0-RTT | No | No (TLS) | Yes |
| Connection Migration | No | No | Yes |

## Reverse Proxies and Load Balancing

### Nginx as Reverse Proxy

```nginx
# /etc/nginx/conf.d/proxy.conf
upstream backend {
    least_conn;
    server 10.0.0.1:8080 weight=3;
    server 10.0.0.2:8080;
    server 10.0.0.3:8080 backup;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Test Nginx configuration
$ nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful

# Reload without downtime
$ nginx -s reload
```

## Caching

```bash
# Check cache headers
$ curl -sI https://example.com/ | grep -i cache
cache-control: public, max-age=3600
etag: "abc123"
last-modified: Mon, 15 Jan 2024 12:00:00 GMT

# Conditional request (only fetch if changed)
$ curl -H "If-None-Match: \"abc123\"" -v https://example.com/
< HTTP/2 304
< etag: "abc123"

# Force no-cache
$ curl -H "Cache-Control: no-cache" -H "Pragma: no-cache" https://example.com/
```

## HTTP Authentication

```bash
# Basic authentication
$ curl -u username:password https://api.example.com/protected
# Or encoded:
$ curl -H "Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=" https://api.example.com/

# Bearer token (JWT/OAuth)
$ curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..." https://api.example.com/

# API key in header
$ curl -H "X-API-Key: abc123" https://api.example.com/

# Digest authentication
$ curl --digest -u username:password https://api.example.com/
```

## Debugging HTTP with curl

```bash
# Verbose output (full request/response)
$ curl -v https://example.com/

# Show timing information
$ curl -w "\n\
    DNS:        %{time_namelookup}s\n\
    Connect:    %{time_connect}s\n\
    TLS:        %{time_appconnect}s\n\
    TTFB:       %{time_starttransfer}s\n\
    Total:      %{time_total}s\n\
    HTTP code:  %{http_code}\n\
    Size:       %{size_download} bytes\n" \
    -o /dev/null -s https://example.com/

# Output:
# DNS:        0.012s
# Connect:    0.045s
# TLS:        0.123s
# TTFB:       0.234s
# Total:      0.456s
# HTTP code:  200
# Size:       1256 bytes

# Send multiple requests (load testing)
$ for i in $(seq 1 100); do
    curl -s -o /dev/null -w "%{http_code}\n" https://example.com/
done | sort | uniq -c
    100 200

# Use httpie (more readable alternative to curl)
$ http GET https://api.example.com/users
HTTP/2.0 200 OK
content-type: application/json

[
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
]
```

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [RFC 9113 — HTTP/2](https://www.rfc-editor.org/rfc/rfc9113)
- [RFC 9114 — HTTP/3](https://www.rfc-editor.org/rfc/rfc9114)
- [RFC 9000 — QUIC: A UDP-Based Multiplexed and Secure Transport](https://www.rfc-editor.org/rfc/rfc9000)
- [MDN HTTP Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP)
- [curl Documentation](https://curl.se/docs/)
- [HTTP/2 Explained (Daniel Stenberg)](https://daniel.haxx.se/http2/)
- [Let's Encrypt — Free TLS Certificates](https://letsencrypt.org/)

## Related Topics

- [TLS](./tls.md) — TLS/SSL encryption in detail
- [DNS](./dns.md) — Name resolution for HTTP requests
- [OSI Model](./osi-model.md) — HTTP at the application layer
- [Packet Capture](./packet-capture.md) — Analyzing HTTP traffic with Wireshark
- [VPN](./vpn.md) — Tunneling HTTP traffic
- [Network Troubleshooting](./troubleshooting.md) — Debugging HTTP connectivity

## HTTP Cookies

Cookies are small pieces of data stored by the browser and sent with every request to the same domain.

```bash
# Send cookies
curl -b "session=abc123; theme=dark" https://example.com/

# Save cookies from response
curl -c /tmp/cookies.txt https://example.com/login \
    -d "user=admin&pass=secret"

# Use saved cookies
curl -b /tmp/cookies.txt https://example.com/dashboard

# View Set-Cookie headers
curl -v https://example.com/ 2>&1 | grep -i set-cookie
# < set-cookie: session=abc123; Path=/; HttpOnly; Secure; SameSite=Strict
```

### Cookie Attributes

| Attribute | Purpose |
|---|---|
| `Path` | URL path scope |
| `Domain` | Domain scope |
| `Expires` / `Max-Age` | Lifetime |
| `Secure` | HTTPS only |
| `HttpOnly` | Not accessible via JavaScript |
| `SameSite` | Cross-site request control (`Strict`, `Lax`, `None`) |

## HTTP Content Negotiation

Clients and servers negotiate content type, encoding, and language:

```bash
# Request specific content type
curl -H "Accept: application/json" https://api.example.com/users

# Request compressed response
curl -H "Accept-Encoding: gzip, deflate, br" https://example.com/

# Request specific language
curl -H "Accept-Language: en-US, en;q=0.9, zh-CN;q=0.8" https://example.com/
```

## WebSockets

WebSocket provides full-duplex communication over a single TCP connection, upgraded from HTTP.

```bash
# WebSocket handshake (HTTP Upgrade)
curl -v -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
     -H "Sec-WebSocket-Version: 13" \
     https://example.com/ws

# HTTP/1.1 101 Switching Protocols
```

```python
# Python WebSocket client
import websockets
import asyncio

async def main():
    async with websockets.connect('wss://example.com/ws') as ws:
        await ws.send('Hello')
        response = await ws.recv()
        print(response)

asyncio.run(main())
```

## Server-Sent Events (SSE)

SSE allows servers to push events to clients over HTTP:

```bash
curl -N -H "Accept: text/event-stream" https://example.com/events
# data: {"time": "2024-01-15T12:00:00Z"}
# event: update
# data: {"status": "processing"}
```

## gRPC (HTTP/2-based)

gRPC uses HTTP/2 for high-performance RPC:

```bash
grpcurl -plaintext -d '{"id": 1}' \
    localhost:50051 mypackage.MyService/GetUser
```

## HTTP Security Headers

```bash
curl -sI https://example.com/ | grep -iE 'strict-transport|x-frame|x-content|content-security|referrer-policy|permissions-policy'
# strict-transport-security: max-age=31536000; includeSubDomains; preload
# x-frame-options: SAMEORIGIN
# x-content-type-options: nosniff
# content-security-policy: default-src 'self'
# referrer-policy: strict-origin-when-cross-origin
# permissions-policy: camera=(), microphone=()
```

### Nginx Security Headers

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=()" always;
```

## HTTP Rate Limiting

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_req_status 429;
        }
    }
}
```

## HTTP Compression

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript text/xml;

# Brotli (better compression)
brotli on;
brotli_comp_level 6;
brotli_types text/plain text/css application/json application/javascript;
```

```bash
# Test compression
curl -H "Accept-Encoding: gzip, deflate, br" -v https://example.com/ 2>&1 | grep -i content-encoding
# < content-encoding: br
```

## HTTP/2 Server Configuration

### Nginx HTTP/2

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # gRPC proxy
    location /mypackage.MyService/ {
        grpc_pass grpc://backend:50051;
    }
}
```

### Caddy (Automatic HTTPS)

```
example.com {
    reverse_proxy backend:8080
    # HTTP/3 enabled by default
    # TLS automatic via Let's Encrypt
}
```
