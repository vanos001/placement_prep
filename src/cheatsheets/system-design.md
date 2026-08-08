# System Design Cheat Sheet

## Interview Framework (45 min)

```
1. Requirements (5 min)     → Functional + Non-functional + Constraints
2. Estimation (3 min)       → QPS, storage, bandwidth
3. High-Level Design (10 min) → Core components + data flow
4. Deep Dive (20 min)       → Critical paths, bottlenecks, trade-offs
5. Wrap Up (7 min)          → Monitoring, failure modes, scaling
```

---

## Back-of-Envelope Numbers

### Latency Numbers Every Engineer Should Know

| Operation | Latency | Notes |
|-----------|---------|-------|
| L1 cache reference | 0.5 ns | Fastest, on-chip |
| L2 cache reference | 7 ns | On-chip |
| Branch misprediction | 5 ns | Pipeline flush cost |
| L3 cache reference | 15 ns | Shared across cores |
| Mutex lock/unlock | 17 ns | Synchronization cost |
| Main memory (RAM) | 100 ns | Local DRAM |
| SSD random read | 150 μs | ~1000× slower than RAM |
| HDD random read | 10 ms | ~100,000× slower than RAM |
| Same datacenter RTT | 0.5 ms | Within same region |
| Cross-continent RTT | 150 ms | US to Europe |

### Time Conversions

| Duration | Seconds |
|----------|---------|
| 1 minute | 60 |
| 1 hour | 3,600 |
| 1 day | 86,400 |
| 1 month (30 days) | 2,592,000 |
| 1 year | 31,536,000 |

### Quick Capacity Estimation Formulas

```
QPS = Total Requests / Seconds in Time Period
Peak QPS = Average QPS × Peak Factor (typically 2-3×)

Storage = Records × Record Size × Retention Period
Daily Storage = Records/Day × Record Size

Bandwidth = QPS × Average Response Size

Read:Write Ratio: Typical web app = 10:1 to 100:1
```

### Common Capacity Examples

| Scenario | Calculation | Result |
|----------|------------|--------|
| 1M users, 10 reads/day | 1M × 10 / 86,400 | ~116 QPS |
| 1 KB × 1M records/day | 1 KB × 1M | ~1 GB/day = ~365 GB/year |
| 100M users, 5 writes/day | 100M × 5 / 86,400 | ~5,800 QPS writes |
| 10 KB response × 10K QPS | 10 KB × 10,000 | ~100 MB/s bandwidth |

### Storage Capacity Reference

| Unit | Bytes | Example |
|------|-------|---------|
| 1 KB | 10³ | A tweet |
| 1 MB | 10⁶ | A photo |
| 1 GB | 10⁹ | A movie |
| 1 TB | 10¹² | 1000 movies |
| 1 PB | 10¹⁵ | Netflix daily data |
| 1 EB | 10¹⁸ | All US academic libraries |

---

## Key Formulas

### Throughput & Capacity

```
QPS = Total Requests / Time (seconds)
Peak QPS = Avg QPS × Peak Multiplier (2-5×)

Storage (bytes) = Records × Record Size
Storage (daily) = New Records/Day × Record Size
Storage (total) = Daily × Retention Days

Bandwidth (bytes/s) = QPS × Response Size

Connections = QPS × Avg Connection Duration (seconds)
```

### Availability

```
Availability = Uptime / (Uptime + Downtime)

  99%     = 3.65 days/year downtime
  99.9%   = 8.76 hours/year downtime
  99.99%  = 52.6 min/year downtime
  99.999% = 5.26 min/year downtime

Serial components:   A_total = A1 × A2 × A3
Parallel components: A_total = 1 - (1-A1)(1-A2)

Example: 3 nodes each 99.9% in parallel:
  A = 1 - (1-0.999)³ = 1 - 0.000000001 = 99.999999999%
```

### Caching

```
Cache Hit Ratio = Cache Hits / Total Requests
Effective Backend Load = Total QPS × (1 - Hit Ratio)

Cache Size = Working Set Size (if it fits)
If working set > cache: use LRU eviction

Memcached: ~100K QPS per instance, ~1ms latency
Redis: ~100K QPS per instance, supports persistence

TTL (Time To Live):
  - Hot data: 5-15 minutes
  - Semi-static: 1-24 hours
  - Static: 1+ days
```

### Database

```
Read Replicas: Read capacity = Primary + N × Replica capacity
  Primary handles writes + reads
  Replicas handle reads only

Sharding: Write capacity = N × Single shard capacity
  Shard key determines distribution
  Cross-shard queries are expensive

Index: B-tree lookup = O(log N), ~3-4 disk reads
  Hash index: O(1) lookup, good for exact matches

Connection Pool: ~100-500 connections per DB instance
  Don't open new connection per request!
```

### Rate Limiting

```
Token Bucket:
  - Bucket size = B tokens
  - Refill rate = R tokens/second
  - Max burst = B requests
  - Sustained rate = R requests/second

Leaky Bucket:
  - Processes at fixed rate
  - Smooths bursty traffic
  - Queue size = B

Sliding Window:
  - Counts requests in last W seconds
  - More accurate than fixed window
  - Memory: O(W × unique_keys)
```

---

## Scaling Patterns

| Pattern | When | Trade-off |
|---------|------|-----------|
| Vertical | Simple, early stage | Single point of failure |
| Horizontal | Need redundancy/throughput | Complexity, consistency |
| Database Sharding | Write-heavy, large data | Cross-shard queries hard |
| Read Replicas | Read-heavy | Replication lag |
| Caching | Repeated reads | Cache invalidation |
| CDN | Static content, global | Cost, cache staleness |
| Async (Queues) | Bursty traffic | Eventual consistency |
| Consistent Hashing | Distributed caching/storage | Complexity |

### When to Use What

```
Read-heavy (10:1 read:write):
  → Caching + Read Replicas

Write-heavy:
  → Sharding + Message Queues (async writes)

Global users:
  → CDN + Multi-region deployment

Real-time requirements:
  → WebSockets + In-memory stores (Redis)

Large file storage:
  → Object storage (S3) + CDN
```

---

## Caching Strategies

| Strategy | Write Path | Read Path | Consistency |
|----------|-----------|-----------|-------------|
| Cache-aside | App → DB, invalidate cache | App → Cache → DB | Eventual |
| Write-through | App → Cache → DB | App → Cache | Strong |
| Write-back | App → Cache → (async) DB | App → Cache | Risk of loss |
| Refresh-ahead | Background refresh | App → Cache | Near real-time |

```
Cache-aside (most common):
  Read:  Check cache → miss? → read DB → populate cache
  Write: Write DB → invalidate cache

Write-through:
  Read:  Check cache (always populated)
  Write: Write cache → write DB (synchronous)

Write-back:
  Read:  Check cache (always populated)
  Write: Write cache → async flush to DB (risk of loss)
```

### Cache Invalidation Patterns

```
TTL-based:      Cache expires after N seconds. Simple, may serve stale.
Event-driven:   Publish change event → consumers invalidate cache. Complex, real-time.
Version-based:  Cache key includes version/hash. Automatic invalidation.
Write-through:  Write to cache and DB simultaneously. Strong consistency.
```

---

## Load Balancing

```
L4 (Transport): TCP/UDP level, fast, no content inspection
L7 (Application): HTTP level, content-aware, routing by path/header

Algorithms:
  Round Robin:       Equal distribution (ignores server load)
  Weighted RR:       Proportional to server capacity
  Least Connections: Route to least loaded server
  IP Hash:           Same client → same server (session affinity)
  Consistent Hash:   Minimal redistribution when servers change

Health Checks:
  Active:  Periodic probe every 5-10 seconds
  Passive: Monitor error rates from actual traffic
  Unhealthy threshold: 3-5 consecutive failures
```

---

## Consistency Patterns

| Pattern | Latency | Consistency | Use Case |
|---------|---------|-------------|----------|
| Strong | High | Linearizable | Banking, inventory |
| Eventual | Low | Converges | Social media, feeds |
| Read-your-writes | Low | Per-user | User profiles |
| Monotonic reads | Low | No going back | Timelines |
| Causal | Medium | Cause-effect order | Comments, replies |

```
Strong:    All reads return most recent write. Slow, blocks on network.
Eventual:  Reads may return stale data. Fast, high availability.
Causal:    If A happens before B, all nodes see A before B.
```

---

## Data Storage Choices

| Need | Choice | Why |
|------|--------|-----|
| ACID, relations | PostgreSQL, MySQL | Complex queries, joins |
| Massive writes, wide columns | Cassandra, HBase | Horizontal write scaling |
| Document store | MongoDB, DynamoDB | Flexible schema |
| Key-value (fast) | Redis, Memcached | Sub-ms latency |
| Graph | Neo4j, Dgraph | Relationship queries |
| Search | Elasticsearch | Full-text search |
| Time series | InfluxDB, TimescaleDB | Aggregations over time |
| Object/blob | S3, GCS | Large files, cheap storage |
| Message queue | Kafka, RabbitMQ | Async processing |
| Cache | Redis, Memcached | Fast reads |

---

## Common Design Patterns

```
CQRS:            Separate read/write models for different scaling needs
Event Sourcing:  Store events, not state — replay to reconstruct
Saga:            Distributed transactions with compensating actions
Circuit Breaker: Fail fast on downstream failures (Hystrix pattern)
Bulkhead:        Isolate critical resources from failures
Rate Limiting:   Token bucket, sliding window, leaky bucket
Retry + Backoff: Exponential backoff with jitter
Idempotency:     Same request produces same result (safe retries)
```

---

## API Design

```
REST:      Resources, HTTP verbs, stateless, cacheable
gRPC:      Protobuf, streaming, internal services, type-safe
GraphQL:   Client-driven queries, single endpoint, no over-fetching

Versioning:  URL path (/v1/), header, query param
Pagination:  Cursor-based (stable, scalable) vs Offset-based (simple, can skip)
Rate Limit:  Per-user, per-IP, token bucket (X-Rate-Limit headers)
```

### REST Best Practices

```
GET    /users          → List users (with pagination)
GET    /users/{id}     → Get single user
POST   /users          → Create user
PUT    /users/{id}     → Full update
PATCH  /users/{id}     → Partial update
DELETE /users/{id}     → Delete user

Status codes: 200 OK, 201 Created, 400 Bad Request,
              401 Unauthorized, 403 Forbidden, 404 Not Found,
              429 Too Many Requests, 500 Internal Server Error
```

---

## Message Queue Patterns

```
Point-to-Point:   One producer, one consumer (task queue)
Publish-Subscribe: One producer, many consumers (event broadcast)
Fan-out:          One message → multiple queues → multiple consumers
Dead Letter Queue: Failed messages go here for retry/analysis

At-most-once:     Fire and forget, may lose messages
At-least-once:    Retry until acknowledged, may duplicate
Exactly-once:     Hardest, requires idempotency (Kafka transactions)
```

---

## Security Checklist

```
Authentication:  OAuth2, JWT, API keys (for services)
Authorization:   RBAC (role-based), ABAC (attribute-based)
Encryption:      TLS 1.3 in transit, AES-256 at rest
Input Validation: SQL injection, XSS, command injection
Rate Limiting:   Prevent abuse and DDoS
Secrets:         Vault, AWS Secrets Manager, env variables
CORS:            Restrict cross-origin requests
```

---

## Monitoring & Observability

```
Metrics:   CPU, memory, disk, network, QPS, latency, error rate
Logging:   Structured logs (JSON), centralized (ELK, CloudWatch)
Tracing:   Distributed tracing (Jaeger, Zipkin, X-Ray)
Alerting:  PagerDuty, OpsGenie — alert on SLA violations

Key SLIs:
  - Latency: p50, p95, p99
  - Error rate: 5xx / total requests
  - Throughput: QPS
  - Availability: successful requests / total

RED Method (for services):
  Rate:      Requests per second
  Errors:    Error rate
  Duration:  Latency distribution

USE Method (for resources):
  Utilization: % of resource used
  Saturation:  Queue depth
  Errors:      Error count
```

---

## Checklist Before Wrapping Up

- [ ] Handle failures (what if X goes down?)
- [ ] Data consistency model explained
- [ ] Monitoring and alerting discussed
- [ ] Security considerations (auth, encryption)
- [ ] Cost estimation roughed out
- [ ] Future scaling path mentioned
- [ ] Bottlenecks identified and addressed
- [ ] Trade-offs of key decisions explained
