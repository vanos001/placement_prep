# Latency Numbers Every Programmer Should Know

## Overview

Jeff Dean's famous latency numbers are the foundation for back-of-the-envelope calculations in system design interviews. Knowing these numbers helps you reason about where bottlenecks occur, which optimizations matter, and how to design systems that meet latency requirements.

## The Numbers (2024 Estimates)

### CPU & Memory

| Operation | Latency | Human Analogy |
|-----------|---------|---------------|
| L1 cache reference | 0.5 ns | — |
| L2 cache reference | 7 ns | — |
| Branch mispredict | 5 ns | — |
| Mutex lock/unlock | 17 ns | — |
| Main memory reference (RAM) | 100 ns | — |
| Compress 1KB with Snappy | 3 μs | — |
| Compress 1KB with Zstd | 10 μs | — |
| Send 2KB over 1 Gbps network | 20 μs | — |

### Disk & Storage

| Operation | Latency | Notes |
|-----------|---------|-------|
| SSD random read | 150 μs | 1000x faster than HDD |
| SSD sequential read (1MB) | 500 μs | — |
| HDD random read | 10 ms | Mechanical seek + rotation |
| HDD sequential read (1MB) | 2 ms | — |
| Read 1 MB from SSD | 1 ms | — |
| Read 1 MB from HDD | 20 ms | — |
| Read 1 MB from memory | 0.25 ms | — |
| Read 1 MB from SSD (NVMe) | 0.3 ms | NVMe is much faster |

### Network

| Operation | Latency |
|-----------|---------|
| Round trip within same datacenter | 0.5 ms |
| Round trip within same city | 2 ms |
| Round trip CA to Netherlands | 150 ms |
| Round trip CA to Singapore | 200 ms |
| Round trip CA to Australia | 180 ms |
| TCP handshake | ~1 RTT |
| TLS handshake | ~2 RTT |
| HTTP request (no TLS) | ~1 RTT + server processing |
| HTTPS request (new conn) | ~3 RTT + server processing |
| HTTPS request (reuse conn) | ~1 RTT + server processing |

### Serialization

| Operation | Latency (per KB) |
|-----------|-----------------|
| Protobuf serialize | 1–5 μs |
| JSON serialize | 10–50 μs |
| Protobuf deserialize | 2–10 μs |
| JSON deserialize | 20–100 μs |

### Database Operations

| Operation | Latency |
|-----------|---------|
| Redis GET/SET | 0.1–0.5 ms |
| MySQL simple query (indexed) | 0.5–2 ms |
| MySQL complex query (join) | 5–50 ms |
| PostgreSQL simple query | 0.5–3 ms |
| MongoDB find (indexed) | 1–5 ms |
| Elasticsearch query | 5–50 ms |
| Cassandra read (local) | 1–5 ms |
| S3 GET (small object) | 10–100 ms |

## Visual Comparison

The key insight is the **orders of magnitude** difference between operations:

```
L1 cache reference          0.5 ns   ▏
L2 cache reference            7 ns   ▏
RAM reference               100 ns   ▏▎
SSD random read           150 μs     ▏▎▌
HDD random read            10 ms     ▏▎▌▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊
Round trip same DC          0.5 ms   ▏▎▌▊
Round trip cross-continent  150 ms   ▏▎▌▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊
```

## The Ratios That Matter

| Comparison | Ratio |
|-----------|-------|
| RAM vs SSD | 1,000x faster |
| SSD vs HDD | 100x faster |
| RAM vs HDD | 100,000x faster |
| Same-DC vs Cross-continent | 300x slower |
| L1 vs RAM | 200x slower |
| Sequential vs Random (SSD) | ~3x faster |
| Sequential vs Random (HDD) | ~100x faster |

## Practical Implications

### Why Caching Works
```
RAM read:    100 ns
SSD read:  150,000 ns (150 μs)
HDD read: 10,000,000 ns (10 ms)

Cache hit (RAM) is 1,500x faster than SSD, 100,000x faster than HDD
```

### Why Indexing Matters
```
Indexed query:    1 ms
Full table scan: 100 ms–10 s (depending on table size)

Index lookup is 100–10,000x faster
```

### Why Connection Pooling Matters
```
TCP handshake:     1 RTT (~0.5ms same DC)
TLS handshake:     2 RTT (~1ms same DC)
Pooled connection: 0 ms (reuse)

Connection pooling saves 1–2ms per request
```

### Why CDN Matters
```
Cross-continent fetch: 150–200 ms
CDN edge hit:          5–20 ms

CDN is 10–40x faster for static content
```

### Why Compression Matters
```
Compress 1KB (Snappy):  3 μs
Send 1KB over network:  20 μs

Compression adds ~3μs but reduces network transfer time
Worth it for payloads > 1KB on slow links
```

### Why Batching Matters
```
1000 individual Redis GETs: 1000 × 0.5ms = 500ms
1 batched Redis MGET:       1 × 0.5ms   = 0.5ms

Batching is 1000x more efficient
```

## The "1 ms" Rule of Thumb

A single server can do a lot in 1 ms:

- Execute ~1 million simple instructions
- Read from RAM ~10,000 times
- Read from SSD ~6 times
- Read from HDD ~0.1 times
- Make 1–2 round trips within the same datacenter
- Serialize/deserialize ~100 Protobuf messages

**Design implication:** If your service has a 100ms latency budget, you can afford:
- ~100 RAM reads
- ~10 SSD reads
- ~1 network round trip within DC
- ~1 database query (indexed)
- Plenty of CPU computation

## Latency Budget Example

For a user-facing API with 200ms target:

| Component | Budget | Operation |
|-----------|--------|-----------|
| Load balancer | 1 ms | Routing |
| Authentication | 5 ms | Token validation (cached) |
| Business logic | 10 ms | CPU-bound processing |
| Cache lookup | 2 ms | Redis GET |
| Database query | 10 ms | Indexed query (cache miss) |
| External API call | 50 ms | Third-party service |
| Serialization | 5 ms | JSON/Protobuf encoding |
| Network | 10 ms | Internal service calls |
| Buffer | 107 ms | Headroom for spikes |
| **Total** | **200 ms** | — |

## Interview Tips

1. **Know the order-of-magnitude differences** — RAM is 1000x faster than SSD, SSD is 100x faster than HDD
2. **Use the numbers to justify design decisions** — "We use caching because RAM access is 100,000x faster than disk"
3. **Calculate latency budgets** — break down the total latency into component budgets
4. **Mention the "tail at scale"** — fan-out amplifies latency (100 services × p99 = high page-level latency)
5. **Don't memorize exact numbers** — know the ratios (RAM vs SSD vs HDD, same-DC vs cross-continent)
6. **Round to make math easy** — RAM ≈ 100ns, SSD ≈ 150μs, HDD ≈ 10ms

## Key Takeaways

- RAM is ~100ns, SSD is ~150μs, HDD is ~10ms. Know these cold.
- Same-datacenter round trip is ~0.5ms; cross-continent is ~150ms.
- These ratios justify caching (RAM > SSD > HDD), indexing, connection pooling, CDNs, and batching.
- A 1ms budget allows ~10K RAM reads, ~6 SSD reads, or ~1 network round trip.
- Build latency budgets for your system design to ensure you meet SLAs.

## Cross-References

- [Estimation](./estimation.md)
- [Latency vs Throughput](./latency-vs-throughput.md)
- [Performance vs Scalability](./performance-vs-scalability.md)
- [Caching Strategy](./hld/caching-strategy.md)
- [Storage: SSD vs HDD](../../storage/ssd.md)

