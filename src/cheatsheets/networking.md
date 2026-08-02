# Networking Cheatsheet

## 🌐 OSI Model

| Layer | Name | Unit | Protocols | Devices |
|-------|------|------|-----------|---------|
| 7 | Application | Data | HTTP, FTP, DNS, SMTP | — |
| 6 | Presentation | Data | SSL/TLS, JPEG, ASCII | — |
| 5 | Session | Data | NetBIOS, RPC | — |
| 4 | Transport | Segment | TCP, UDP | — |
| 3 | Network | Packet | IP, ICMP, ARP | Router |
| 2 | Data Link | Frame | Ethernet, Wi-Fi | Switch |
| 1 | Physical | Bits | Cables, Radio | Hub |

## 🔄 TCP vs UDP

| | TCP | UDP |
|---|-----|-----|
| Connection | Connection-oriented | Connectionless |
| Reliability | Guaranteed | Best-effort |
| Ordering | Ordered | No ordering |
| Speed | Slower | Faster |
| Use | HTTP, FTP, email | DNS, gaming, streaming |

## 🤝 TCP Handshake

```
Three-Way:
  Client → SYN → Server
  Client ← SYN-ACK ← Server
  Client → ACK → Server

Four-Way Termination:
  Client → FIN → Server
  Client ← ACK ← Server
  Client ← FIN ← Server
  Client → ACK → Server
```

## 🌍 DNS

```
Resolution: Client → Recursive Resolver → Root → TLD → Authoritative

Record Types:
A: Domain → IPv4
AAAA: Domain → IPv6
CNAME: Alias → Domain
MX: Domain → Mail server
NS: Domain → Name server
TXT: Text (SPF, verification)
PTR: IP → Domain (reverse)
```

## 🔐 HTTPS / TLS

```
TLS 1.3 Handshake (1-RTT):
  Client → ClientHello (cipher suites, key share)
  Server → ServerHello (chosen cipher, certificate, key share)
  Client verifies certificate → Encrypted session begins

TLS 1.3 vs 1.2:
  1-RTT vs 2-RTT, 0-RTT resumption, removed weak ciphers
```

## 📡 HTTP Versions

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|----------|--------|--------|
| Protocol | TCP | TCP | QUIC (UDP) |
| Multiplexing | No | Yes | Yes |
| Header Compression | No | HPACK | QPACK |
| Server Push | No | Yes | Yes |
| TLS | Optional | Often | Built-in |

## 🔄 REST API

```
Methods: GET (read), POST (create), PUT (update full),
         PATCH (update partial), DELETE (delete)

Status Codes:
  2xx: Success (200 OK, 201 Created, 204 No Content)
  3xx: Redirect (301 Moved, 302 Found, 304 Not Modified)
  4xx: Client Error (400 Bad Request, 401 Unauthorized,
       403 Forbidden, 404 Not Found)
  5xx: Server Error (500 Internal, 502 Bad Gateway, 503 Unavailable)
```

## ⚖️ Load Balancing

```
L4 (Transport): Routes by IP+port, fast
L7 (Application): Routes by HTTP headers/URL, flexible

Algorithms:
  Round Robin: Rotate through servers
  Least Connections: Server with fewest connections
  IP Hash: Same client → same server (sticky)
  Weighted: More powerful servers get more traffic
```

## 🌐 WebSocket

```
Full-duplex, persistent connection over TCP
Upgrade from HTTP via handshake
Use: Real-time chat, gaming, live updates, notifications

vs HTTP:
  HTTP: Request → Response → Close
  WebSocket: Bidirectional, persistent
```

## 🍪 Cookies vs Sessions vs Tokens

```
Cookie: Client-side, sent with requests, size limit
Session: Server-side, identified by session ID
Token (JWT): Self-contained, stateless, includes claims
```

## 📋 URL Components

```
https://www.example.com:443/path/to/page?key=value#section
  |       |           |   |           |         |
protocol subdomain   port path       query    fragment
```

## ⚡ Quick Facts

- **NAT**: Maps private → public IP (PAT uses ports)
- **ARP**: Maps IP → MAC address
- **DHCP**: Auto-assigns IP addresses
- **ICMP**: ping (echo), traceroute (TTL exceeded)
- **CDN**: Edge servers cache content closer to users
- **VPN**: Encrypted tunnel over public internet
- **CORS**: Browser security for cross-origin requests
- **gRPC**: HTTP/2 + Protocol Buffers, fast internal APIs
- **GraphQL**: Client-specified queries, single endpoint
- **SSL Pinning**: Hardcode expected certificate (prevents MITM)

## 🔗 Cross-References

- [Networking Interview Questions](../interview/network-questions.md) — Detailed answers
- [Networking Revision](../revision/networks.md) — Quick summary
- [Architecture Cheatsheet](./architecture.md) — Distributed systems networking
