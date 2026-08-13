# Networking Interview Questions

> Comprehensive networking questions with detailed answers, follow-ups, and common mistakes.

---

## Q1: Explain the OSI model.

**Answer:**

```
┌─────────────────────────────────────────────────────────┐
│                    OSI MODEL                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 7: APPLICATION                                   │
│  ├── Protocols: HTTP, FTP, SMTP, DNS, SSH              │
│  ├── Data unit: Data                                    │
│  └── Function: User-facing services                     │
│                                                         │
│  Layer 6: PRESENTATION                                  │
│  ├── Function: Encryption, compression, encoding        │
│  ├── SSL/TLS operates here                              │
│  └── Data format conversion (ASCII, JPEG)               │
│                                                         │
│  Layer 5: SESSION                                       │
│  ├── Function: Session management, authentication       │
│  ├── Establishes/maintains/terminates sessions          │
│  └── Examples: NetBIOS, RPC                             │
│                                                         │
│  Layer 4: TRANSPORT                                     │
│  ├── Protocols: TCP, UDP                                │
│  ├── Data unit: Segment (TCP) / Datagram (UDP)          │
│  ├── Function: End-to-end delivery, flow control        │
│  └── Port numbers, reliability                          │
│                                                         │
│  Layer 3: NETWORK                                       │
│  ├── Protocols: IP, ICMP, ARP, OSPF                    │
│  ├── Data unit: Packet                                  │
│  ├── Function: Routing, logical addressing              │
│  └── Routers operate here                               │
│                                                         │
│  Layer 2: DATA LINK                                     │
│  ├── Protocols: Ethernet, Wi-Fi, PPP                   │
│  ├── Data unit: Frame                                   │
│  ├── Function: MAC addressing, error detection          │
│  └── Switches operate here                              │
│                                                         │
│  Layer 1: PHYSICAL                                      │
│  ├── Media: Cables, radio waves, fiber                 │
│  ├── Data unit: Bits                                    │
│  ├── Function: Raw bit transmission                     │
│  └── Hubs, repeaters operate here                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Follow-up questions:**
- "What is the difference between OSI and TCP/IP model?"
- "Which layer does a firewall operate at?"
- "Where does NAT operate?"

---

## Q2: What is the difference between TCP and UDP?

**Answer:**

| Aspect | TCP | UDP |
|--------|-----|-----|
| Connection | Connection-oriented | Connectionless |
| Reliability | Guaranteed delivery | Best-effort |
| Ordering | Ordered | No ordering |
| Flow Control | Yes (sliding window) | No |
| Congestion Control | Yes | No |
| Header Size | 20-60 bytes | 8 bytes |
| Speed | Slower (overhead) | Faster |
| Use Cases | HTTP, email, file transfer | DNS, gaming, streaming, VoIP |

```
TCP Three-Way Handshake:
  Client → Server: SYN (seq=x)
  Server → Client: SYN-ACK (seq=y, ack=x+1)
  Client → Server: ACK (ack=y+1)
  Connection established!

TCP Four-Way Termination:
  Client → Server: FIN
  Server → Client: ACK
  Server → Client: FIN
  Client → Server: ACK
  Connection closed!

UDP Header:
  ┌──────────┬──────────┐
  │ Src Port │ Dst Port │
  ├──────────┼──────────┤
  │ Length   │ Checksum │
  └──────────┴──────────┘
  Simple, minimal overhead
```

**Follow-up questions:**
- "When would you choose UDP over TCP?"
- "What is TCP congestion control?"
- "What happens if a TCP packet is lost?"

---

## Q3: Explain DNS resolution.

**Answer:**

```
DNS Resolution Flow:
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Client  │────→│ Recursive    │────→│ Root DNS     │
│          │     │ Resolver     │     │ Server       │
└──────────┘     │ (ISP)        │     └──────┬───────┘
                 └──────┬───────┘            │
                        │                    │ .com → TLD server
                        │         ┌──────────▼───────┐
                        │         │ TLD DNS Server    │
                        │         │ (.com)            │
                        │         └──────────┬───────┘
                        │                    │
                        │         ┌──────────▼───────┐
                        │         │ Authoritative    │
                        │         │ DNS Server       │
                        │         │ (google.com)     │
                        │         └──────────┬───────┘
                        │                    │
                        ◄────────────────────┘
                        IP address returned

DNS Record Types:
├── A: Maps domain to IPv4 address
├── AAAA: Maps domain to IPv6 address
├── CNAME: Alias for another domain
├── MX: Mail server for domain
├── NS: Name server for domain
├── TXT: Text record (SPF, verification)
├── SOA: Start of Authority (zone info)
└── PTR: Reverse DNS (IP → domain)

Caching:
├── Browser cache → OS cache → Recursive resolver cache
├── TTL (Time To Live) determines cache duration
└── Reduces DNS queries significantly
```

**Follow-up questions:**
- "What is a DNS amplification attack?"
- "What is DNS over HTTPS (DoH)?"
- "How does DNS load balancing work?"

---

## Q4: What happens when you type a URL in the browser?

**Answer:**

```
1. URL Parsing
   └── Extract protocol, domain, path, query string

2. DNS Resolution
   └── Domain → IP address (cache → recursive → root → TLD → authoritative)

3. TCP Connection
   └── Three-way handshake (SYN → SYN-ACK → ACK)

4. TLS Handshake (if HTTPS)
   ├── Client sends supported cipher suites
   ├── Server sends certificate + chosen cipher
   ├── Client verifies certificate (CA chain)
   ├── Key exchange (Diffie-Hellman)
   └── Encrypted session established

5. HTTP Request
   ├── GET /path HTTP/1.1
   ├── Host: example.com
   ├── Headers (cookies, accept, user-agent)
   └── Body (if POST/PUT)

6. Server Processing
   ├── Load balancer → Application server
   ├── Process request (route, business logic)
   ├── Database queries if needed
   └── Generate response

7. HTTP Response
   ├── HTTP/1.1 200 OK
   ├── Headers (content-type, cache-control, set-cookie)
   └── Body (HTML, JSON, etc.)

8. Browser Rendering
   ├── Parse HTML → DOM tree
   ├── Parse CSS → CSSOM tree
   ├── Combine → Render tree
   ├── Layout (calculate positions)
   ├── Paint (draw pixels)
   └── Composite (layer composition)

9. Additional Requests
   ├── CSS, JS, images (triggered by HTML parsing)
   ├── May open parallel connections (HTTP/1.1: 6 per domain)
   └── HTTP/2: Multiplexing over single connection
```

---

## Q5: Explain HTTP/1.1 vs HTTP/2 vs HTTP/3.

**Answer:**

| Feature | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---------|----------|--------|--------|
| Protocol | TCP | TCP | QUIC (UDP) |
| Multiplexing | No (head-of-line blocking) | Yes (single connection) | Yes |
| Header Compression | No | HPACK | QPACK |
| Server Push | No | Yes (deprecated in Chrome 2022) | Yes (rarely used) |
| Connection | One per request (keep-alive) | Single multiplexed | Single multiplexed |
| TLS | Optional | Often used | Built-in |

```
HTTP/1.1 Problem (Head-of-Line Blocking):
  Request 1 → [waiting...] → Response 1
  Request 2 → [waiting...] → Response 2  (blocked by request 1!)

HTTP/2 Solution (Multiplexing):
  Single Connection:
  Stream 1: → Req1 → ───────── Resp1 →
  Stream 2: → Req2 → ── Resp2 →
  Stream 3: → Req3 → ──── Resp3 →
  All streams share one connection, no blocking!

HTTP/3 (QUIC):
  ├── Built on UDP (faster connection setup)
  ├── Built-in TLS 1.3
  ├── No head-of-line blocking at transport level
  ├── Connection migration (survives IP change)
  └── 0-RTT connection establishment
```

---

## Q6: What is a REST API?

**Answer:**

**REST** (Representational State Transfer) is an architectural style for designing web services.

```
REST Principles:
├── Stateless: Each request contains all needed info
├── Client-Server: Separation of concerns
├── Cacheable: Responses can be cached
├── Uniform Interface: Standard methods (GET, POST, PUT, DELETE)
├── Layered System: Client doesn't know if talking to end server
└── Code on Demand: Server can send executable code (optional)

HTTP Methods:
  GET    /users          → List all users
  GET    /users/123      → Get user 123
  POST   /users          → Create new user
  PUT    /users/123      → Update user 123 (full)
  PATCH  /users/123      → Update user 123 (partial)
  DELETE /users/123      → Delete user 123

Status Codes:
  2xx Success:  200 OK, 201 Created, 204 No Content
  3xx Redirect: 301 Moved, 302 Found, 304 Not Modified
  4xx Client:   400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found
  5xx Server:   500 Internal Error, 502 Bad Gateway, 503 Unavailable
```

---

## Q7: What is a load balancer?

**Answer:**

A **load balancer** distributes incoming traffic across multiple servers.

```
Types:
├── L4 (Transport Layer)
│   ├── Routes based on IP + port
│   ├── Fast, doesn't inspect content
│   └── Examples: AWS NLB, HAProxy (TCP mode)
│
└── L7 (Application Layer)
    ├── Routes based on HTTP headers, URL, cookies
    ├── Can do SSL termination, content-based routing
    └── Examples: AWS ALB, Nginx, Envoy

Algorithms:
├── Round Robin: Rotate through servers
├── Least Connections: Send to server with fewest connections
├── IP Hash: Same client → same server (session affinity)
├── Weighted Round Robin: More powerful servers get more traffic
└── Random: Simple, effective with homogeneous servers

Health Checks:
├── Periodic probes (every 5-10 seconds)
├── HTTP check: GET /health → 200 OK
├── TCP check: Can establish connection
└── Unhealthy server removed from rotation
```

---

## Q8: What is HTTPS? How does TLS work?

**Answer:**

**HTTPS** = HTTP + TLS (Transport Layer Security) for encrypted communication.

```
TLS 1.3 Handshake (1-RTT):
  Client → Server:
    ClientHello
    ├── Supported TLS versions
    ├── Cipher suites
    ├── Key share (Diffie-Hellman)
    └── Random number

  Server → Client:
    ServerHello
    ├── Chosen cipher suite
    ├── Key share
    ├── Certificate
    └── Finished

  Client verifies:
    ├── Certificate chain (CA → Intermediate → Server)
    ├── Certificate not expired
    ├── Domain matches
    └── Revocation status (OCSP)

  Both derive session keys → Encrypted communication begins

TLS 1.3 vs 1.2:
├── 1-RTT vs 2-RTT handshake
├── 0-RTT resumption (reduced latency)
├── Removed insecure ciphers
└── Mandatory forward secrecy
```

---

## Q9: What is a CDN?

**Answer:**

**CDN (Content Delivery Network)** is a distributed network of servers that delivers content from locations closest to the user.

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  User    │────→│  CDN Edge    │────→│  Origin      │
│ (India)  │     │  (Mumbai)    │     │  Server (US) │
└──────────┘     └──────────────┘     └──────────────┘
                     Cache HIT: ~20ms
                     Cache MISS: ~200ms (fetch from origin)

CDN Benefits:
├── Reduced latency (content closer to users)
├── Reduced origin load (95%+ cache hit rate)
├── DDoS protection (distributed traffic)
├── High availability (multiple edge locations)
└── Bandwidth cost reduction

CDN Use Cases:
├── Static assets (images, CSS, JS)
├── Video streaming
├── Software downloads
├── API acceleration
└── Dynamic content (with edge computing)
```

---

## Q10: What are WebSockets?

**Answer:**

**WebSocket** provides full-duplex, persistent communication over a single TCP connection.

```
WebSocket Upgrade:
  Client → Server:
    GET /chat HTTP/1.1
    Upgrade: websocket
    Connection: Upgrade
    Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==

  Server → Client:
    HTTP/1.1 101 Switching Protocols
    Upgrade: websocket
    Connection: Upgrade
    Sec-WebSocket-Accept: HSmrc0sMlYUkAGmm5OPpG2HaGWk=

  Connection upgraded to WebSocket!

WebSocket vs HTTP:
  HTTP:    Client → Request → Response → Closed
  WebSocket: Client ←→ Server (bidirectional, persistent)

Use Cases:
├── Real-time chat
├── Live notifications
├── Gaming
├── Collaborative editing
├── Live dashboards
└── IoT data streams
```

---

## Q11-30: Quick-Fire Questions

**Q11: What is NAT?**
Network Address Translation: Maps private IP to public IP. Allows multiple devices to share one public IP. Types: Static, Dynamic, PAT (Port Address Translation).

**Q12: What is a subnet?**
Division of a network into smaller networks. Subnet mask determines network vs host portion. Example: 255.255.255.0 (/24) = 254 usable hosts.

**Q13: What is ARP?**
Address Resolution Protocol: Maps IP address to MAC address. Broadcasts ARP request, target responds with MAC.

**Q14: What is DHCP?**
Dynamic Host Configuration Protocol: Automatically assigns IP addresses, subnet mask, gateway, DNS. Lease-based.

**Q15: What is a firewall?**
Network security device that filters traffic based on rules. Types: Packet filtering, stateful inspection, application layer (WAF).

**Q16: What is a VPN?**
Virtual Private Network: Encrypted tunnel over public internet. Provides privacy, security, and remote access.

**Q17: What is ICMP?**
Internet Control Message Protocol: Used for diagnostics. Examples: ping (echo request/reply), traceroute (TTL exceeded).

**Q18: What is a reverse proxy?**
Server that sits in front of web servers, forwards client requests. Benefits: Load balancing, SSL termination, caching, security.

**Q19: What is CORS?**
Cross-Origin Resource Sharing: Browser security mechanism. Allows/restricts web pages from making requests to different domains. Controlled by response headers.

**Q20: What is a cookie vs session vs token?**
Cookie: Stored on client, sent with requests. Session: Stored on server, identified by session ID. Token (JWT): Self-contained, stateless, includes claims.

**Q21: What is HTTP caching?**
Browser/proxy stores responses. Cache-Control headers: max-age, no-cache, no-store. ETags for conditional requests (304 Not Modified).

**Q22: What is gRPC?**
Remote Procedure Call framework by Google. Uses HTTP/2 and Protocol Buffers. Fast, strongly typed, supports streaming. Used for microservice communication.

**Q23: What is GraphQL?**
Query language for APIs. Client specifies exact data needed. Single endpoint. Avoids over-fetching/under-fetching. Trade-off: Complexity, caching harder.

**Q24: What is a message queue?**
System for async communication between services. Examples: Kafka, RabbitMQ, SQS. Benefits: Decoupling, buffering, reliability.

**Q25: What is TCP congestion control?**
Mechanism to prevent network congestion. Algorithms: Slow start, congestion avoidance, fast retransmit, fast recovery. Window-based.

**Q26: What is the difference between a switch and a router?**
Switch: Layer 2, forwards frames based on MAC address, within a network. Router: Layer 3, forwards packets based on IP address, between networks.

**Q27: What is IPv4 vs IPv6?**
IPv4: 32-bit, 4.3B addresses, dotted decimal. IPv6: 128-bit, 340 undecillion addresses, hexadecimal. IPv6 adds: auto-configuration, no NAT needed, better security.

**Q28: What is a socket?**
Endpoint for communication. Combination of IP address + port. Types: Stream (TCP), Datagram (UDP). API: bind, listen, accept, connect, send, recv.

**Q29: What is SSL pinning?**
Client hardcodes expected certificate/public key. Prevents MITM attacks even if CA is compromised. Trade-off: Certificate rotation complexity.

**Q30: What is HTTP keep-alive?**
Reuses TCP connection for multiple HTTP requests. Reduces overhead of TCP handshake + TLS negotiation. Default in HTTP/1.1.

## 🔗 Cross-References

- [Networking Cheatsheet](../cheatsheets/networking.md) — Quick reference for all networking concepts
- [Networking Revision](../revision/networks.md) — Quick summary before interviews
- [System Design](./system-design/README.md) — Networking concepts in distributed systems
- [Architecture Questions](./arch-questions.md) — Microservices, API design
