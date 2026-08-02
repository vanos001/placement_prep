# System Design Cheat Sheet

## Interview Framework (45 min)

```
1. Requirements (5 min)     → Functional + Non-functional + Constraints
2. Estimation (3 min)       → QPS, storage, bandwidth
3. High-Level Design (10 min) → Core components + data flow
4. Deep Dive (20 min)       → Critical paths, bottlenecks, trade-offs
5. Wrap Up (7 min)          → Monitoring, failure modes, scaling
```

## Back-of-Envelope Numbers

| Resource | Latency | Throughput |
|----------|---------|-----------|
| L1 cache | 0.5 ns | - |
| L2 cache | 7 ns | - |
| RAM | 100 ns | - |
| SSD | 150 μs | 100K IOPS |
| HDD | 10 ms | 200 IOPS |
| Same DC network | 0.5 ms | - |
| Cross-continent | 150 ms | - |

| Time | Seconds |
|------|---------|
| 1 day | 86,400 |
| 1 month | 2.6M |
| 1 year | 31.5M |

```
1 million users × 10 reads/day = ~116 QPS
1 KB × 1M/day = 1 GB/day = ~365 GB/year
```

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

## Caching Strategies

| Strategy | Write Path | Read Path | Consistency |
|----------|-----------|-----------|-------------|
| Cache-aside | App → DB, invalidate cache | App → Cache → DB | Eventual |
| Write-through | App → Cache → DB | App → Cache | Strong |
| Write-back | App → Cache → (async) DB | App → Cache | Risk of loss |
| Refresh-ahead | Background refresh | App → Cache | Near real-time |

## Load Balancing

```
L4 (Transport): TCP/UDP level, fast, no content inspection
L7 (Application): HTTP level, content-aware, routing by path/header

Algorithms: Round Robin, Weighted, Least Connections, IP Hash, Consistent Hash
Health Checks: Active (periodic probe) + Passive (error monitoring)
```

## Availability Math

```
99.9%  = 8.76 hours/year downtime
99.99% = 52.6 min/year downtime
99.999% = 5.26 min/year downtime

Serial:  A_total = A1 × A2 × A3
Parallel: A_total = 1 - (1-A1)(1-A2)
```

## Consistency Patterns

| Pattern | Latency | Consistency | Use Case |
|---------|---------|-------------|----------|
| Strong | High | Linearizable | Banking, inventory |
| Eventual | Low | Converges | Social media, feeds |
| Read-your-writes | Low | Per-user | User profiles |
| Monotonic reads | Low | No going back | Timelines |

## Data Storage Choices

| Need | Choice |
|------|--------|
| ACID, relations | PostgreSQL, MySQL |
| Massive writes, wide columns | Cassandra, HBase |
| Document store | MongoDB, DynamoDB |
| Key-value (fast) | Redis, Memcached |
| Graph | Neo4j, Dgraph |
| Search | Elasticsearch |
| Time series | InfluxDB, TimescaleDB |
| Object/blob | S3, GCS |

## Common Design Patterns

```
CQRS: Separate read/write models
Event Sourcing: Store events, not state
Saga: Distributed transactions with compensating actions
Circuit Breaker: Fail fast on downstream failures
Bulkhead: Isolate critical resources
Rate Limiting: Token bucket, sliding window, leaky bucket
```

## API Design

```
REST: Resources, HTTP verbs, stateless
gRPC: Protobuf, streaming, internal services
GraphQL: Client-driven queries, single endpoint

Versioning: URL path (/v1/), header, query param
Pagination: Cursor-based (stable), Offset-based (simple)
Rate Limiting: Per-user, per-IP, token bucket
```

## Checklist Before Wrapping Up

- [ ] Handle failures (what if X goes down?)
- [ ] Data consistency model explained
- [ ] Monitoring and alerting discussed
- [ ] Security considerations (auth, encryption)
- [ ] Cost estimation roughed out
- [ ] Future scaling path mentioned
