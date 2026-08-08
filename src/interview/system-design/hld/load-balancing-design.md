# Load Balancing Design

## What is Load Balancing?

A load balancer distributes incoming network traffic across multiple backend servers to ensure no single server bears too much demand. It improves responsiveness, availability, and resource utilization.

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         [Server 1]    [Server 2]    [Server 3]
         CPU: 30%      CPU: 45%      CPU: 35%
```

## Why Load Balancing?

| Without Load Balancer | With Load Balancer |
|----------------------|-------------------|
| Single point of failure | High availability |
| Limited throughput | Scales horizontally |
| Uneven resource use | Even distribution |
| Downtime during deploys | Zero-downtime deploys |

## Load Balancing Algorithms

### 1. Round Robin
```
Request 1 → Server A
Request 2 → Server B
Request 3 → Server C
Request 4 → Server A  (cycle repeats)
```

- **How**: Cycles through servers sequentially
- **Pros**: Simple, fair distribution
- **Cons**: Ignores server capacity/load
- **Use when**: All servers have equal capacity

### 2. Weighted Round Robin
```
Server A (weight=5): gets 5/10 requests
Server B (weight=3): gets 3/10 requests
Server C (weight=2): gets 2/10 requests
```

- **How**: Assigns weights based on server capacity
- **Pros**: Accounts for different server specs
- **Cons**: Weights are static, don't reflect real-time load
- **Use when**: Servers have different capacities

### 3. Least Connections
```
Server A: 10 active connections → pick
Server B: 25 active connections
Server C: 15 active connections
```

- **How**: Routes to the server with fewest active connections
- **Pros**: Adapts to real-time load
- **Cons**: Doesn't account for connection duration
- **Use when**: Requests have varying processing times

### 4. Least Response Time
```
Server A: avg 50ms → pick (fastest)
Server B: avg 120ms
Server C: avg 80ms
```

- **How**: Routes to the server with lowest average response time
- **Pros**: Accounts for both load and network latency
- **Cons**: Can oscillate, more overhead to track
- **Use when**: Response time is critical

### 5. IP Hash
```
hash(client_ip) % num_servers = server_index
Client 192.168.1.1 → hash → Server A (always)
Client 192.168.1.2 → hash → Server B (always)
```

- **How**: Hash of client IP determines server
- **Pros**: Same client always goes to same server (sticky)
- **Cons**: Uneven distribution if IPs are clustered
- **Use when**: Session affinity is needed without cookies

### 6. Consistent Hashing
```
        ┌──────────────────┐
        │    Hash Ring     │
        │   ┌──A──┐        │
        │  ╱       ╲       │
        │ S1       S2      │
        │  ╲       ╱       │
        │   └──B──┘        │
        └──────────────────┘
Request hashes to point on ring → nearest server clockwise
```

- **How**: Maps both servers and requests to positions on a hash ring
- **Pros**: Minimal redistribution when servers are added/removed
- **Cons**: More complex to implement
- **Use when**: Distributed caching, consistent routing

### Algorithm Comparison

| Algorithm | Load Aware | Session Affinity | Complexity | Best For |
|-----------|-----------|-----------------|------------|----------|
| Round Robin | ❌ | ❌ | Low | Equal servers |
| Weighted RR | Partial | ❌ | Low | Unequal capacity |
| Least Conn | ✅ | ❌ | Medium | Varying request times |
| Least RT | ✅ | ❌ | Medium | Latency-sensitive |
| IP Hash | ❌ | ✅ | Low | Session persistence |
| Consistent Hash | ❌ | ✅ | High | Distributed cache |

## L4 vs L7 Load Balancing

### Layer 4 (Transport Layer)
```
Client → L4 LB → Backend
         (TCP/UDP level, no content inspection)
```

- **Operates on**: IP address + port
- **Speed**: Very fast (minimal processing)
- **Decisions**: Based on network info only
- **Use cases**: Database load balancing, gaming servers
- **Examples**: AWS NLB, HAProxy (TCP mode), Linux IPVS

### Layer 7 (Application Layer)
```
Client → L7 LB → Backend
         (HTTP headers, URL, cookies, content)
```

- **Operates on**: HTTP headers, URL, cookies, payload
- **Speed**: Slower (must parse HTTP)
- **Decisions**: Content-based routing
- **Use cases**: Web applications, API gateways
- **Examples**: AWS ALB, Nginx, Envoy, HAProxy (HTTP mode)

### L4 vs L7 Comparison

| Feature | L4 | L7 |
|---------|----|----|
| Speed | Faster | Slower |
| Content inspection | No | Yes |
| URL-based routing | No | Yes |
| SSL termination | Pass-through | Can terminate |
| Cookie handling | No | Yes |
| WebSocket support | Yes (TCP) | Yes (HTTP upgrade) |
| Cost | Lower | Higher |

### L7 Routing Examples
```
/api/v1/users/*    → User Service
/api/v1/orders/*   → Order Service
/static/*          → CDN / Static Servers
*.websocket        → WebSocket Servers
```

## Health Checks

Health checks ensure traffic is only sent to healthy servers.

### Types of Health Checks

| Type | How | Detects |
|------|-----|---------|
| **TCP** | Can we connect to port? | Server down |
| **HTTP** | GET /health returns 200? | App crash, dependency failure |
| **Custom** | Checks DB, cache, disk | Deep health issues |

### Health Check Configuration
```
Interval:     10 seconds (check every 10s)
Timeout:      5 seconds (mark unhealthy if no response in 5s)
Threshold:    3 (3 consecutive failures → unhealthy)
Recovery:     2 (2 consecutive successes → healthy)
```

### Health Check Endpoint Design
```json
// GET /health
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "disk": "ok"
  },
  "uptime": 86400
}
```

**Best Practices**:
- Use shallow health checks for load balancing (fast)
- Use deep health checks for monitoring (comprehensive)
- Include dependency status in health endpoint
- Don't make health checks too expensive

## Sticky Sessions

Sticky sessions (session affinity) ensure a user's requests go to the same server.

### Methods

| Method | How | Pros | Cons |
|--------|-----|------|------|
| **Cookie-based** | LB sets cookie with server ID | Reliable | Requires L7 |
| **IP-based** | Hash client IP | Works at L4 | IP changes break it |
| **App-level** | App tracks session | Flexible | App complexity |

### Problems with Sticky Sessions
- Uneven load distribution
- Server failure loses all sessions
- Harder to scale down
- Violates stateless architecture principle

**Better Alternative**: Store sessions in external store (Redis)
```
Client → LB → Any Server → Redis (session store)
```

## Load Balancer in Practice

### Common Load Balancer Solutions

| Solution | Type | L4/L7 | Use Case |
|----------|------|-------|----------|
| **Nginx** | Software | L7 (+ L4) | Web server + LB |
| **HAProxy** | Software | L4 + L7 | High-performance LB |
| **Envoy** | Software | L4 + L7 | Service mesh proxy |
| **AWS ALB** | Managed | L7 | HTTP/HTTPS workloads |
| **AWS NLB** | Managed | L4 | TCP/UDP, ultra-low latency |
| **Cloudflare** | CDN + LB | L7 | Global load balancing |
| **F5** | Hardware | L4 + L7 | Enterprise on-prem |

### Multi-tier Load Balancing
```
                    ┌──────────────┐
                    │ DNS-based    │  (geo-distributed)
                    │ Global LB    │
                    └──────┬───────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │Regional │  │Regional │  │Regional │
        │L4 LB    │  │L4 LB    │  │L4 LB    │
        └────┬────┘  └────┬────┘  └────┬────┘
          ┌──┴──┐      ┌──┴──┐      ┌──┴──┐
          ▼     ▼      ▼     ▼      ▼     ▼
        [App] [App]  [App] [App]  [App] [App]
```

## Interview Tips

1. **Start with requirements** — "What's the traffic pattern? Read-heavy or write-heavy?"
2. **Choose algorithm based on use case** — Don't default to round robin
3. **Explain the "why"** — "Least connections because request processing times vary"
4. **Consider failure scenarios** — "What happens when a server goes down?"
5. **Mention health checks** — Always include health checking in your design
6. **Discuss sticky sessions trade-off** — "We'd prefer stateless, but if needed..."
7. **Think about SSL termination** — Where does TLS end?
8. **Consider multi-region** — "For global users, we'd use DNS-based geo-routing"

## Common Mistakes

- ❌ Forgetting health checks
- ❌ Using sticky sessions without discussing trade-offs
- ❌ Not considering the load balancer as a single point of failure
- ❌ Ignoring SSL/TLS termination
- ❌ Choosing L7 when L4 would suffice (adding unnecessary latency)

## Cross-References

- [Scalability](./scalability.md) — Horizontal scaling requires load balancing
- [Availability](./availability.md) — LB is key to high availability
- [Caching Strategy](./caching-strategy.md) — Consistent hashing for cache distribution
- [API Design](./api-design.md) — Rate limiting at the LB level
- [Security Design](./security-design.md) — SSL termination, DDoS protection
- [Cloud Kubernetes Services](../../../cloud/kubernetes/services.md)
- [Networks HTTP](../../../networks/http/rest.md)
- [Rate Limiter](../rate-limiter.md)
