# Networking Build-It-Yourself Projects

## 1. Build TCP

Implement the full TCP state machine from RFC 793: connection establishment (three-way handshake), data transfer with sequence/acknowledgment numbers, connection teardown (four-way close with FIN/ACK), and the TIME_WAIT state. Implement retransmission with a retransmission timer and exponential backoff, sliding window flow control (receiver-advertised window), and a basic congestion control algorithm (slow start and congestion avoidance with a congestion window). Run over a TUN/TAP device to send/receive raw IP packets.

**Key concepts**: TCP 11-state machine, three-way handshake, four-way close, sequence number arithmetic (wrapping), retransmission timeout (RTO) with Jacobson/Karels algorithm, sliding window, congestion window (cwnd), slow start threshold (ssthresh). **Complexity**: Advanced (5-7 weeks). **References**: RFC 793, RFC 5681 (TCP congestion control), TCP Illustrated Vol. 1 (Stevens), lwIP source, `seastar` networking stack.

## 2. Build HTTP/1.1

Implement an HTTP/1.1 server supporting request parsing (method, URI, headers, body with Content-Length and chunked transfer encoding), response generation (status line, headers, body), all standard methods (GET, HEAD, POST, PUT, DELETE, OPTIONS), persistent connections (Connection: keep-alive), and basic middleware (logging, routing). Support pipelining (multiple requests on one connection).

**Key concepts**: HTTP request/response format, header parsing, Content-Length vs chunked encoding, persistent connections, HTTP methods and status codes, URI routing, connection lifecycle. **Complexity**: Beginner-Intermediate (2-3 weeks). **References**: RFC 7230/7231, `hyper` source (Rust), `http-parser` (Joyent), Nginx HTTP module structure.

## 3. Build HTTP/2

Implement an HTTP/2 frame parser (9 frame types: DATA, HEADERS, PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE, PING, GOAWAY, WINDOW_UPDATE), stream multiplexing (multiple logical streams over one TCP connection with stream IDs), HPACK header compression (static/dynamic tables, Huffman encoding), and flow control per stream. Build a minimal client and server that can serve multiple concurrent requests over a single connection.

**Key concepts**: Binary framing layer, stream multiplexing, stream state machine, HPACK (header field compression with static/dynamic tables), flow control (connection-level and stream-level), stream priorities. **Complexity**: Advanced (5-6 weeks). **References**: RFC 7540 (HTTP/2), RFC 7541 (HPACK), `nghttp2` source, Go `net/http` HTTP/2 support, `h2o` server.

## 4. Build a DNS Resolver

Implement a stub DNS resolver that sends DNS queries over UDP to recursive resolvers (8.8.8.8, 1.1.1.1), parses DNS response messages (header, question, answer, authority, additional sections), and supports A, AAAA, CNAME, MX, and NS record types. Add a local cache with TTL-based expiration. Support recursive resolution by following CNAME chains. Implement fallback to TCP for truncated responses (>512 bytes).

**Key concepts**: DNS wire format (header flags, labels, name compression via pointers), UDP query/response, TTL-based caching, CNAME resolution chain, record types, root hints for full recursion. **Complexity**: Beginner (2-3 weeks). **References**: RFC 1035, `c-ares` source, `trust-dns-resolver`, `unbound` source, `dnsdist`.

## 5. Build a Reverse Proxy

Build a reverse proxy that accepts incoming HTTP connections, forwards requests to a pool of backend servers, and relays responses back to clients. Implement connection pooling to the backends (keep-alive connections, max-idle timeouts), basic load balancing (round-robin or least-connections), TLS termination (accept HTTPS, forward HTTP to backends), and health checks (periodic GET to a health endpoint, remove unhealthy backends from the pool).

**Key concepts**: HTTP proxying, connection pooling, load balancing algorithms, TLS termination (X.509 cert parsing, TLS handshake), health checking (active/passive), HTTP header forwarding (X-Forwarded-For, X-Real-IP). **Complexity**: Intermediate (3-4 weeks). **References**: Nginx `ngx_http_proxy_module`, Envoy proxy architecture, HAProxy source, Caddy reverse proxy.

## 6. Build a Load Balancer

Implement a Layer 4 (TCP) load balancer that accepts client connections and distributes them to backend servers. Support multiple algorithms: round-robin, weighted round-robin, least-connections, and consistent-hashing. Implement health checks (TCP connect probe, HTTP GET probe) with configurable intervals and failure thresholds. Track connection state and drain connections gracefully when removing a backend.

**Key concepts**: L4 load balancing, connection tracking, health check state machine, weighted distribution, graceful drain, connection limits, TCP proxying (splice/sendfile for kernel-level forwarding). **Complexity**: Intermediate (3-4 weeks). **References**: HAProxy architecture, IPVS (Linux Virtual Server), Envoy L4 filter, `maglev` hash-based load balancer paper.

> **Interview Angle**: Networking projects demonstrate that you understand what happens below `http.get()`. A candidate who has implemented the TCP state machine can debug connection issues, understand packet captures, and explain why a load balancer behaves a certain way — all critical for backend and infrastructure roles.