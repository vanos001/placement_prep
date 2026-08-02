# Networking - Quick Revision

> 📌 Last-minute revision before interviews. Scan these points quickly.

---

## OSI Model (7 Layers)

- **7 Application**: HTTP, FTP, DNS, SMTP
- **6 Presentation**: SSL/TLS, encryption, compression
- **5 Session**: Session management, authentication
- **4 Transport**: TCP, UDP, ports, segments
- **3 Network**: IP, ICMP, ARP, routing, packets
- **2 Data Link**: Ethernet, Wi-Fi, MAC, frames
- **1 Physical**: Cables, radio, bits

## TCP vs UDP

- **TCP**: Connection-oriented, reliable, ordered, slow (HTTP, email, FTP)
- **UDP**: Connectionless, unreliable, fast (DNS, gaming, streaming, VoIP)
- **TCP handshake**: SYN → SYN-ACK → ACK (3-way)
- **TCP termination**: FIN → ACK → FIN → ACK (4-way)
- **Congestion control**: Slow start, congestion avoidance, fast retransmit

## DNS

- **Resolution**: Client → Recursive Resolver → Root → TLD → Authoritative
- **Records**: A (IPv4), AAAA (IPv6), CNAME (alias), MX (mail), NS (nameserver)
- **Caching**: Browser → OS → Resolver, TTL-based

## HTTP

- **Methods**: GET (read), POST (create), PUT (update), PATCH (partial), DELETE
- **Status**: 2xx (success), 3xx (redirect), 4xx (client error), 5xx (server error)
- **HTTP/1.1**: Persistent connections, no multiplexing
- **HTTP/2**: Multiplexing, HPACK, server push, single TCP connection
- **HTTP/3**: QUIC (UDP), built-in TLS 1.3, 0-RTT, no head-of-line blocking

## HTTPS / TLS

- **TLS 1.3**: 1-RTT handshake, 0-RTT resumption, mandatory forward secrecy
- **Certificate**: CA chain verification, domain validation
- **SSL Pinning**: Hardcode expected cert (prevents MITM)

## URL Components

```
https://www.example.com:443/path?key=value#fragment
protocol | subdomain | port | path | query | fragment
```

## WebSocket

- Full-duplex, persistent connection over TCP
- Upgrade from HTTP via handshake
- Use: Real-time chat, gaming, live updates, notifications
- vs HTTP: HTTP is request-response, WebSocket is bidirectional

## REST API

- Stateless, uniform interface, cacheable
- CRUD: GET/POST/PUT/DELETE
- Status codes: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found, 500 Internal Error

## Load Balancing

- **L4**: Transport layer, routes by IP+port, fast
- **L7**: Application layer, routes by HTTP headers/URL, flexible
- **Algorithms**: Round Robin, Least Connections, IP Hash, Weighted

## Key Protocols

- **NAT**: Private → Public IP mapping
- **ARP**: IP → MAC address resolution
- **DHCP**: Auto IP assignment
- **ICMP**: Diagnostics (ping, traceroute)
- **gRPC**: HTTP/2 + Protocol Buffers, fast internal APIs
- **GraphQL**: Client-specified queries, single endpoint

## Key Concepts

- **CDN**: Edge servers cache content closer to users
- **VPN**: Encrypted tunnel over public internet
- **CORS**: Browser cross-origin security
- **Cookie**: Client-side, sent with requests
- **Session**: Server-side, identified by session ID
- **JWT**: Self-contained token, stateless
- **Reverse proxy**: Sits in front of servers, handles SSL, load balancing, caching
- **Firewall**: Filters traffic based on rules (packet filtering, stateful, WAF)

## 🔗 Cross-References

- [Networking Cheatsheet](../cheatsheets/networking.md) — Detailed reference
- [Networking Interview Questions](../interview/network-questions.md) — Full Q&A
