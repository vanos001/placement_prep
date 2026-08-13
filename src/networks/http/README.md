# HTTP Overview

## Overview

The **Hypertext Transfer Protocol (HTTP)** is the foundation of data communication on the World Wide Web. It defines how messages are formatted and transmitted between clients (browsers) and servers. From the first version in 1991 to the modern HTTP/3, HTTP has evolved to become faster, more efficient, and more secure.

Understanding HTTP is essential for web development, system design, and networking interviews. It's the most widely used application protocol on the Internet.

## Detailed Explanation

### What is HTTP?

HTTP is an **application-layer protocol** that follows a **client-server request-response model**:

```mermaid
sequenceDiagram
    participant C as Client (Browser)
    participant S as Web Server
    
    C->>S: HTTP Request (GET /index.html)
    S->>C: HTTP Response (200 OK + HTML)
    
    C->>S: HTTP Request (GET /style.css)
    S->>C: HTTP Response (200 OK + CSS)
    
    C->>S: HTTP Request (GET /script.js)
    S->>C: HTTP Response (200 OK + JS)
```

### HTTP Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Stateless** | Each request is independent (no memory of previous requests) |
| **Connectionless** (HTTP/1.0) | New connection per request (HTTP/1.1 changed this) |
| **Media independent** | Can transfer any type of data (HTML, JSON, images, video) |
| **Text-based** | Human-readable headers (HTTP/1.x, HTTP/2 uses binary framing) |

### HTTP Message Format

#### Request

```
GET /index.html HTTP/1.1
Host: www.example.com
User-Agent: Mozilla/5.0
Accept: text/html
Accept-Language: en-US
Connection: keep-alive

[optional body]
```

| Part | Description |
|------|-------------|
| **Request line** | Method, URI, HTTP version |
| **Headers** | Key-value metadata |
| **Empty line** | Separates headers from body |
| **Body** | Optional data (POST, PUT) |

#### Response

```
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1234
Date: Mon, 01 Jan 2024 00:00:00 GMT
Server: nginx

<html>...</html>
```

| Part | Description |
|------|-------------|
| **Status line** | HTTP version, status code, reason |
| **Headers** | Key-value metadata |
| **Empty line** | Separates headers from body |
| **Body** | Response data |

### HTTP Methods

```mermaid
graph TD
    A["HTTP Methods"] --> B["Safe (no side effects)"]
    A --> C["Unsafe (modifies state)"]
    A --> D["Idempotent (same result if repeated)"]
    A --> E["Non-idempotent"]
    
    B --> B1["GET - Retrieve resource"]
    B --> B2["HEAD - Headers only"]
    B --> B3["OPTIONS - Available methods"]
    
    C --> C1["POST - Create resource"]
    C --> C2["PUT - Replace resource"]
    C --> C3["DELETE - Remove resource"]
    C --> C4["PATCH - Partial update"]
    
    D --> D1["GET, HEAD, OPTIONS"]
    D --> D2["PUT, DELETE"]
    
    E --> E1["POST, PATCH"]
```

| Method | Purpose | Safe | Idempotent | Has Body |
|--------|---------|------|------------|----------|
| **GET** | Retrieve resource | ✓ | ✓ | No |
| **HEAD** | Headers only (no body) | ✓ | ✓ | No |
| **POST** | Create resource / submit data | ✗ | ✗ | Yes |
| **PUT** | Replace resource entirely | ✗ | ✓ | Yes |
| **PATCH** | Partial update | ✗ | ✗ | Yes |
| **DELETE** | Remove resource | ✗ | ✓ | Optional |
| **OPTIONS** | Available methods (CORS) | ✓ | ✓ | No |
| **TRACE** | Loop-back test | ✓ | ✓ | No |
| **CONNECT** | Establish tunnel (HTTPS) | ✗ | ✗ | No |

### HTTP Status Codes

```mermaid
graph TD
    A["Status Codes"] --> B["1xx Informational"]
    A --> C["2xx Success"]
    A --> D["3xx Redirection"]
    A --> E["4xx Client Error"]
    A --> F["5xx Server Error"]
    
    B --> B1["100 Continue"]
    B --> B2["101 Switching Protocols"]
    
    C --> C1["200 OK"]
    C --> C2["201 Created"]
    C --> C3["204 No Content"]
    
    D --> D1["301 Moved Permanently"]
    D --> D2["302 Found"]
    D --> D3["304 Not Modified"]
    D --> D4["307 Temporary Redirect"]
    
    E --> E1["400 Bad Request"]
    E --> E2["401 Unauthorized"]
    E --> E3["403 Forbidden"]
    E --> E4["404 Not Found"]
    E --> E5["405 Method Not Allowed"]
    E --> E6["429 Too Many Requests"]
    
    F --> F1["500 Internal Server Error"]
    F --> F2["502 Bad Gateway"]
    F --> F3["503 Service Unavailable"]
    F --> F4["504 Gateway Timeout"]
```

| Code | Name | Meaning |
|------|------|---------|
| **200** | OK | Request succeeded |
| **201** | Created | Resource created (POST) |
| **204** | No Content | Success, no body returned |
| **301** | Moved Permanently | Resource moved to new URL |
| **302** | Found | Temporary redirect |
| **304** | Not Modified | Use cached version |
| **307** | Temporary Redirect | Same method, different URL |
| **400** | Bad Request | Invalid request syntax |
| **401** | Unauthorized | Authentication required |
| **403** | Forbidden | Server refuses to authorize |
| **404** | Not Found | Resource doesn't exist |
| **405** | Method Not Allowed | HTTP method not supported |
| **429** | Too Many Requests | Rate limited |
| **500** | Internal Server Error | Server-side error |
| **502** | Bad Gateway | Upstream server error |
| **503** | Service Unavailable | Server overloaded/maintenance |
| **504** | Gateway Timeout | Upstream server timeout |

### HTTP Headers

#### Request Headers

```
Host: www.example.com              # Required in HTTP/1.1
User-Agent: Mozilla/5.0            # Client software
Accept: text/html                  # Accepted content types
Accept-Language: en-US             # Preferred language
Accept-Encoding: gzip, deflate     # Accepted compression
Connection: keep-alive             # Connection management
Authorization: Bearer token123     # Authentication
Cookie: session=abc123             # Cookies
Content-Type: application/json     # Body content type (POST)
Content-Length: 42                  # Body length
```

#### Response Headers

```
Content-Type: text/html            # Response content type
Content-Length: 1234                # Response body length
Content-Encoding: gzip             # Compression used
Cache-Control: max-age=3600        # Caching policy
ETag: "abc123"                     # Resource version
Set-Cookie: session=xyz; HttpOnly  # Set cookie
Server: nginx                      # Server software
Date: Mon, 01 Jan 2024 00:00 GMT   # Response timestamp
Location: /new-url                 # Redirect URL (3xx)
Access-Control-Allow-Origin: *     # CORS header
```

### HTTP Versions

```mermaid
graph LR
    A["HTTP/0.9<br/>(1991)"] --> B["HTTP/1.0<br/>(1996)"]
    B --> C["HTTP/1.1<br/>(1997)"]
    C --> D["HTTP/2<br/>(2015)"]
    D --> E["HTTP/3<br/>(2022)"]
    
    A -->|"Simple GET"| B
    B -->|"Headers, POST"| C
    C -->|"Persistent, pipelining"| D
    D -->|"Multiplexing, binary"| E
    E -->|"QUIC-based"| F["Future"]
    
    style C fill:#4CAF50,color:#fff
    style D fill:#2196F3,color:#fff
    style E fill:#FF9800,color:#fff
```

| Version | Year | Key Features | Transport |
|---------|------|--------------|-----------|
| **HTTP/0.9** | 1991 | GET only, no headers | TCP |
| **HTTP/1.0** | 1996 | Headers, methods, status codes | TCP |
| **HTTP/1.1** | 1997 | Persistent connections, pipelining, chunked | TCP |
| **HTTP/2** | 2015 | Multiplexing, HPACK, server push, binary | TCP + TLS |
| **HTTP/3** | 2022 | QUIC, 0-RTT, connection migration | QUIC (UDP) |

### HTTP vs HTTPS

```
HTTP:   http://example.com    Port 80   Plaintext
HTTPS:  https://example.com   Port 443  Encrypted (TLS)

HTTPS = HTTP + TLS (Transport Layer Security)

Security provided:
  - Encryption (confidentiality)
  - Authentication (server identity via certificates)
  - Integrity (tamper detection)
```

### HTTP Connection Management

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    
    Note over C,S: HTTP/1.0 (new connection per request)
    C->>S: TCP handshake
    C->>S: GET /page.html
    S->>C: Response
    C->>S: TCP close
    
    C->>S: TCP handshake (new!)
    C->>S: GET /style.css
    S->>C: Response
    C->>S: TCP close
    
    Note over C,S: HTTP/1.1 (persistent connections)
    C->>S: TCP handshake
    C->>S: GET /page.html
    S->>C: Response
    C->>S: GET /style.css (same connection!)
    S->>C: Response
    C->>S: GET /script.js (same connection!)
    S->>C: Response
    C->>S: TCP close (when done)
```

## Example: HTTP Request-Response

### Browser Request

```http
GET /api/users HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/json
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
```

### Server Response

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Content-Length: 256
Cache-Control: no-cache
Date: Mon, 01 Jan 2024 12:00:00 GMT
Server: nginx/1.24.0
X-Request-Id: abc-123-def

{
  "users": [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"}
  ],
  "total": 2
}
```

### Using curl

```bash
# GET request
$ curl -v https://api.example.com/users

# POST request with JSON body
$ curl -X POST https://api.example.com/users \
    -H "Content-Type: application/json" \
    -d '{"name": "Charlie", "email": "charlie@example.com"}'

# With headers
$ curl -H "Authorization: Bearer token123" \
    -H "Accept: application/json" \
    https://api.example.com/users
```

### Using Python requests

```python
import requests

# GET request
response = requests.get('https://api.example.com/users')
print(response.status_code)  # 200
print(response.json())        # {'users': [...]}

# POST request
data = {'name': 'Charlie', 'email': 'charlie@example.com'}
response = requests.post('https://api.example.com/users', json=data)
print(response.status_code)  # 201

# With headers
headers = {'Authorization': 'Bearer token123'}
response = requests.get('https://api.example.com/users', headers=headers)
```

## Interview Questions

### Q1: What is HTTP and what are its key characteristics?
**A:** HTTP is an application-layer protocol for transferring hypermedia. Key characteristics: (1) Client-server model; (2) Stateless — each request is independent; (3) Text-based headers (HTTP/1.x); (4) Media independent — can transfer any data type; (5) Request-response model; (6) Uses TCP (HTTP/1.x, HTTP/2) or QUIC (HTTP/3).

### Q2: What are the HTTP methods and their purposes?
**A:** **GET** — retrieve resource (safe, idempotent); **POST** — create resource/submit data; **PUT** — replace entire resource (idempotent); **PATCH** — partial update; **DELETE** — remove resource (idempotent); **HEAD** — headers only; **OPTIONS** — available methods (CORS preflight).

### Q3: What is the difference between HTTP and HTTPS?
**A:** HTTPS = HTTP + TLS. HTTP is plaintext on port 80; HTTPS is encrypted on port 443. HTTPS provides: (1) **Encryption** — prevents eavesdropping; (2) **Authentication** — server identity via certificates; (3) **Integrity** — tamper detection. Modern best practice: always use HTTPS.

### Q4: Explain HTTP status code categories.
**A:** **1xx** — Informational (100 Continue, 101 Switching Protocols); **2xx** — Success (200 OK, 201 Created); **3xx** — Redirection (301 Moved Permanently, 304 Not Modified); **4xx** — Client Error (400 Bad Request, 404 Not Found); **5xx** — Server Error (500 Internal Server Error, 503 Service Unavailable).

### Q5: What is HTTP statelessness and how do applications maintain state?
**A:** HTTP is stateless — each request is independent, no memory of previous requests. Applications maintain state via: (1) **Cookies** — stored on client, sent with each request; (2) **Sessions** — server-side storage linked by session ID; (3) **Tokens** (JWT) — self-contained authentication; (4) **URL parameters** — state in URL.

### Q6: What is the difference between GET and POST?
**A:** **GET** — retrieves data, safe (no side effects), idempotent (repeatable), parameters in URL, cacheable, limited URL length. **POST** — creates/submits data, not safe, not idempotent, body contains data, not cacheable by default, no size limit. Use GET for reading, POST for creating/modifying.

### Q7: What are HTTP headers?
**A:** Headers are key-value pairs in HTTP requests/responses that provide metadata. Request headers: Host, User-Agent, Accept, Authorization, Cookie. Response headers: Content-Type, Cache-Control, Set-Cookie, Server. Headers control caching, authentication, content negotiation, and connection management.

### Q8: How has HTTP evolved from 1.0 to HTTP/3?
**A:** **HTTP/1.0** — new connection per request. **HTTP/1.1** — persistent connections, pipelining, chunked encoding. **HTTP/2** — multiplexing (multiple requests on one connection), binary framing, HPACK header compression, server push. **HTTP/3** — QUIC (UDP-based), 0-RTT connection, connection migration, no head-of-line blocking.

## Common Mistakes

1. **Confusing HTTP and HTTPS**: HTTP is plaintext, HTTPS is encrypted. Always use HTTPS in production. Browsers now warn on HTTP pages.

2. **Not understanding statelessness**: HTTP has no memory. Each request must contain all necessary information (authentication, session ID). Don't assume the server remembers previous requests.

3. **Using GET for mutations**: GET should be safe (no side effects). Don't use GET to delete resources or modify data. Use POST, PUT, PATCH, or DELETE.

4. **Not knowing status code categories**: 2xx = success, 4xx = client error, 5xx = server error. Don't return 200 for errors or 500 for client mistakes.

5. **Confusing 301 and 302 redirects**: 301 = permanent (search engines update), 302 = temporary (search engines keep original). Use 301 for domain changes, 302 for temporary maintenance.

6. **Not understanding idempotency**: GET, PUT, DELETE are idempotent (repeatable without additional effect). POST is not idempotent (each request may create a new resource).

7. **Forgetting the Host header**: HTTP/1.1 requires the Host header. Without it, the server doesn't know which virtual host to serve. This was optional in HTTP/1.0.

## Summary

| Aspect | Detail |
|--------|--------|
| **Protocol** | Application layer, request-response |
| **Stateless** | Yes (cookies/sessions for state) |
| **Methods** | GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS |
| **Status codes** | 1xx-5xx (informational to server error) |
| **Versions** | HTTP/1.0, HTTP/1.1, HTTP/2, HTTP/3 |
| **Security** | HTTPS (HTTP + TLS) |
| **Transport** | TCP (HTTP/1.x, HTTP/2), QUIC/UDP (HTTP/3) |

HTTP is the backbone of the web. Understanding its methods, status codes, headers, and evolution is essential for web development and networking.

## Cross-References

- [HTTP/1.1](http1.md) — Persistent connections, pipelining
- [HTTP/2](http2.md) — Multiplexing, binary framing
- [HTTP/3](http3.md) — QUIC-based HTTP
- [HTTPS](https.md) — TLS handshake, certificates
- [QUIC Protocol](quic.md) — Transport for HTTP/3
- [WebSocket](websocket.md) — Full-duplex communication
- [REST](rest.md) — RESTful API design
- [gRPC](grpc.md) — gRPC on HTTP/2
- [DNS Overview](../dns/README.md) — DNS resolves hostnames for HTTP
