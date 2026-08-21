# HAProxy

HAProxy (High Availability Proxy) is an open-source L4/L7 load balancer and reverse proxy, originally developed by Willy Tarreau in 2001. It's the workhorse of many high-traffic websites (GitHub, Reddit, Stack Overflow, Airbnb) for TCP/HTTP load balancing, SSL termination, and traffic routing. This page covers the architecture, the configuration model, the load balancing algorithms, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  HAProxy Process (single-threaded event loop, or multi-proc)│
│  - Listens on multiple frontends (ports)                   │
│  - Routes to backends (groups of servers)                  │
│  - Health checks backends                                  │
│  - Logs access (syslog)                                    │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ client request              │ proxied request
        ▼                              ▼
┌──────────────────┐    ┌──────────────────────┐
│  Client (browser)  │    │  Backend server 1   │
└──────────────────┘    ┌──────────────────────┐
                          │  Backend server 2   │
                          └──────────────────────┘
```

HAProxy is single-process by default (event loop), but can run multi-process (since 1.5) or multi-threaded (since 1.8, the recommended mode for modern hardware).

## The Configuration Model

HAProxy's configuration is in `haproxy.cfg`:

```haproxy
# Global settings
global
    log /dev/log local0
    maxconn 10000
    user haproxy
    group haproxy
    daemon

# Default settings
defaults
    mode http
    log global
    option httplog
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    retries 3

# Frontend (incoming HTTP)
frontend http-in
    bind *:80
    default_backend app-servers
    
    # Path-based routing
    acl is_api path_beg /api/
    use_backend api-servers if is_api
    
    # Host-based routing
    acl is_www hdr(host) -i www.example.com
    use_backend www-servers if is_www

# Backends
backend app-servers
    balance roundrobin
    option httpchk GET /health
    server app1 10.0.0.1:8080 check
    server app2 10.0.0.2:8080 check
    server app3 10.0.0.3:8080 check

backend api-servers
    balance leastconn
    option httpchk GET /api/health
    server api1 10.0.0.4:8080 check
    server api2 10.0.0.5:8080 check
```

Key concepts:
- **frontend**: defines a listener (bind to a port, route to backends).
- **backend**: defines a group of servers and how to balance.
- **ACL**: Access Control List — conditional rules for routing.
- **server**: an individual backend server.

## Load Balancing Algorithms

HAProxy supports multiple algorithms:

### Round Robin (default)

Cycles through servers in order. Each server gets 1/N of requests.

```text
Request 1 → server1
Request 2 → server2
Request 3 → server3
Request 4 → server1 (cycle back)
```

Best when all servers are equally powerful.

### Least Connection

Sends to the server with the fewest active connections. Best for variable-duration requests.

```text
server1: 5 active connections
server2: 3 active connections  ← picked
server3: 5 active connections
```

### Source IP Hash

Hashes the client's IP to a server. The same client always goes to the same server (session affinity).

```text
client IP 1.2.3.4 → server2 (always)
client IP 5.6.7.8 → server1 (always)
```

Useful for applications that don't share session state (sticky sessions).

### URI Hash

Hashes the request URI to a server. The same URL always goes to the same server — useful for caching (each cache server has a unique set of URLs).

### Random

Picks a random server. Useful for testing or when the workloads are uniform.

## Health Checks

HAProxy checks backends periodically:

```haproxy
backend app-servers
    option httpchk GET /health
    http-check expect status 200
    server app1 10.0.0.1:8080 check inter 2s rise 2 fall 3
```

- `inter 2s`: check every 2 seconds.
- `rise 2`: 2 successful checks → mark as up.
- `fall 3`: 3 failed checks → mark as down.

If a server is marked down, HAProxy stops sending it traffic. When it recovers, traffic resumes.

Active checks (HTTP/TCP): HAProxy makes a request to the server.
Passive checks: if a real request fails (e.g., connection refused), the server is marked down.

## SSL Termination

HAProxy can terminate TLS at the edge:

```haproxy
frontend https-in
    bind *:443 ssl crt /etc/ssl/certs/mycert.pem
    # The cert PEM file must include both the certificate and the private key.
    
    # HTTP/2 (multiplexing)
    alpn h2,http/1.1
    
    default_backend app-servers
```

HAProxy's SSL stack uses OpenSSL (or BoringSSL via patch). Modern HAProxy (2.4+) supports TLS 1.3, ALPN, and SNI for multiple certs on one port.

## SSL Passthrough (TCP Mode)

For end-to-end encryption, HAProxy can pass TLS through without terminating:

```haproxy
frontend https-passthrough
    mode tcp
    bind *:443
    default_backend tls-servers
    
backend tls-servers
    mode tcp
    balance source  # sticky by source IP
    option ssl-hello-chk  # checks if server speaks TLS
    server s1 10.0.0.1:443 check
    server s2 10.0.0.2:443 check
```

The backend sees the original TLS connection (HAProxy is a TCP proxy). Useful when the backend needs the original TLS context (e.g., for client cert authentication).

## Layer 4 vs. Layer 7

HAProxy can run in either mode:

### TCP (Layer 4)

```haproxy
mode tcp
```

HAProxy proxies the TCP stream byte-by-byte, without parsing the application protocol. Faster (~1 Gbps per core), no application awareness.

### HTTP (Layer 7)

```haproxy
mode http
```

HAProxy parses HTTP, can do path/host routing, header rewriting, cookie insertion. Slower (~500 Mbps per core), full application awareness.

For most modern web applications, Layer 7 is preferred (more features). For pure TCP load balancing (e.g., database), Layer 4.

## Production Performance

HAProxy's published performance (single process, modern CPU):
- HTTP/1.1 throughput: ~100K req/sec per core.
- HTTP/2 throughput: ~150K req/sec per core.
- TCP throughput: ~5-10 Gbps per core.
- Latency overhead: ~100 µs per request.

For higher throughput, run HAProxy with multiple worker threads (`nbthread 8` on an 8-core machine).

## Production Use Cases

### Layer 7 Load Balancer

```haproxy
frontend web
    bind *:80
    bind *:443 ssl crt /etc/ssl/mycert.pem alpn h2,http/1.1
    mode http
    default_backend app-servers

backend app-servers
    mode http
    balance leastconn
    option httpchk GET /health
    server s1 10.0.0.1:8080 check
    server s2 10.0.0.2:8080 check
```

### SSL Termination with HTTP/2

```haproxy
frontend https-in
    bind *:443 ssl crt /etc/ssl/mycert.pem alpn h2,http/1.1
    http-request redirect scheme https unless { ssl_fc }
    default_backend app-servers
```

### Database Load Balancer (TCP)

```haproxy
frontend pg-in
    mode tcp
    bind *:5432
    default_backend pg-servers

backend pg-servers
    mode tcp
    option pgsql-check -u postgres
    balance source  # sticky by client IP (for PostgreSQL connection state)
    server pg1 10.0.0.1:5432 check
    server pg2 10.0.0.2:5432 check
```

### Rate Limiting

```haproxy
backend app-servers
    # Rate limit: max 10 req/sec per IP
    stick-table type ip size 100k expire 10s store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny if { sc_http_req_rate(0) gt 10 }
    server s1 10.0.0.1:8080 check
```

The stick-table tracks per-IP request rates; HAProxy denies over the threshold.

## Comparison to Nginx and Envoy

| Aspect | HAProxy | Nginx | Envoy |
|--------|---------|-------|-------|
| Origin | 2001 | 2002 | 2016 |
| L4 (TCP) | Yes | Yes (stream) | Yes |
| L7 (HTTP) | Yes | Yes | Yes |
| SSL termination | Yes | Yes | Yes |
| HTTP/2 | Yes (1.8+) | Yes | Yes |
| Dynamic config | Reload | Reload | xDS (hot reload) |
| Stats | Built-in | Requires modules | Built-in |
| Best for | Load balancing | Edge proxy, content serving | Service mesh |

HAProxy is the canonical load balancer; Nginx is more feature-rich (content serving); Envoy is the modern choice with dynamic config.

## Common Pitfalls

1. **Forgetting that long single connections monopolize a worker.** HAProxy's single-threaded event loop can be blocked by a slow client. Use multi-threading (`nbthread N`).

2. **Forgetting that the default `maxconn` is low.** Default is 10000; raise to 100000+ for high-traffic sites.

3. **Forgetting that health check failures take down traffic.** A flapping server causes intermittent 503s. Tune `rise` and `fall` to debounce.

4. **Forgetting that SSL termination uses significant CPU.** For 100 Gbps of TLS, HAProxy needs significant CPU. Use crypto offload (e.g., Intel QAT).

5. **Forgetting that the hot-reload has a brief window.** HAProxy's reload is graceful (zero-downtime), but there's a brief overlap of old and new processes. Use multiple HAProxy instances for HA.

6. **Forgetting that stick-tables are per-process.** In multi-process mode, stick-tables don't share. Use `peers` for cross-process sharing.

## References

- [HAProxy documentation](http://docs.haproxy.org/)
- [HAProxy Configuration Manual](http://docs.haproxy.org/2.8/configuration.html)
- [HAProxy: Load balancing algorithms](http://docs.haproxy.org/2.8/configuration.html#balance)
- [HAProxy: Health checks](http://docs.haproxy.org/2.8/configuration.html#5.2-check)
- [HAProxy: SSL termination](http://docs.haproxy.org/2.8/configuration.html#5.1-crt)
- [HAProxy: Multi-threading](http://docs.haproxy.org/2.8/configuration.html#4.2-nbthread)
- Tarreau, "[Making HAProxy 1.5 fast](https://www.haproxy.com/blog/making-haproxy-1-5-fast)" (HAProxy blog)
- [LWN: HAProxy overview (2020)](https://lwn.net/Articles/816130/)
