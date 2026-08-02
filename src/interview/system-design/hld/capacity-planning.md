# Capacity Planning and Estimation

## What is Capacity Planning?

Capacity planning is estimating the resources (servers, storage, bandwidth) needed to support a system at scale. In interviews, this is often the first step after requirements clarification.

## Back-of-the-Envelope Estimation

Quick, approximate calculations to size a system.

### Key Numbers to Know

| Unit | Value | Example |
|------|-------|---------|
| 1 KB | 1,000 bytes | Short text message |
| 1 MB | 1,000 KB | High-res photo |
| 1 GB | 1,000 MB | SD movie |
| 1 TB | 1,000 GB | 1000 movies |
| 1 PB | 1,000 TB | Netflix daily data |

| Time | Seconds |
|------|---------|
| 1 day | 86,400 |
| 1 month | 2,592,000 |
| 1 year | 31,536,000 |

### Common Conversions
```
1 million = 10^6
1 billion = 10^9
1 trillion = 10^12

1 KB = 10^3 bytes
1 MB = 10^6 bytes
1 GB = 10^9 bytes
1 TB = 10^12 bytes
```

## QPS Estimation

### Formula
```
QPS = Total Requests per Day / Seconds per Day

Example:
- 100 million users
- 10% are DAU (Daily Active Users) = 10 million DAU
- Each user makes 10 requests/day
- Total requests = 10M × 10 = 100M requests/day
- QPS = 100M / 86,400 ≈ 1,157 QPS
- Peak QPS = 2 × avg QPS ≈ 2,314 QPS
```

### Peak vs Average QPS
```
Average QPS: Total requests / Total seconds
Peak QPS: Usually 2-3x average (depends on traffic pattern)

Traffic pattern examples:
- Social media: Peak in evening (3-5x average)
- E-commerce: Peak during sales (10x+ average)
- Enterprise SaaS: Peak during work hours (2x average)
```

### QPS Benchmarks

| System | QPS | Notes |
|--------|-----|-------|
| Single server | 1,000-10,000 | Depends on complexity |
| Single database | 10,000-100,000 | Simple queries |
| Redis | 100,000+ | In-memory |
| Nginx | 100,000+ | Static content |
| CDN | Millions | Edge caching |

## Storage Estimation

### Formula
```
Storage = Data per item × Items per day × Retention days

Example (Twitter):
- 500 million tweets/day
- Average tweet: 300 bytes (text) + 1 KB (metadata) = 1.3 KB
- Media: 20% of tweets have images (500 KB avg)
  - Media per day: 100M × 500 KB = 50 TB/day
- Text per day: 500M × 1.3 KB = 650 GB/day
- Total per day: ~50.65 TB/day
- 5-year storage: 50.65 TB × 365 × 5 ≈ 92 PB
```

### Storage Estimation Example

```
Problem: Design Instagram
- 500 million DAU
- Each user uploads 2 photos per day
- Average photo: 2 MB

Storage per day:
500M × 2 × 2 MB = 2,000 TB = 2 PB per day

Storage per year:
2 PB × 365 = 730 PB per year

With replication (3x):
730 PB × 3 = 2.19 EB per year
```

## Bandwidth Estimation

### Formula
```
Bandwidth = QPS × Average Response Size

Example:
- 10,000 QPS
- Average response: 10 KB
- Bandwidth = 10,000 × 10 KB = 100 MB/s = 800 Mbps
```

### Bandwidth Estimation Example

```
Problem: Design YouTube
- 1 billion video views per day
- Average video: 50 MB
- Average video length: 5 minutes

Bandwidth:
1B views × 50 MB / 86,400 seconds = 578 GB/s = 4.6 Tbps

With CDN (90% offload):
4.6 Tbps × 10% = 460 Gbps origin bandwidth
```

## Server Estimation

### Formula
```
Servers = Peak QPS / QPS per server

Example:
- Peak QPS: 10,000
- Each server handles: 1,000 QPS
- Servers needed: 10,000 / 1,000 = 10 servers
- With redundancy: 10 × 2 = 20 servers
```

## Memory Estimation

### Cache Size
```
Cache = Daily Active Users × Data per user × Cache hit ratio

Example:
- 10 million DAU
- User profile: 1 KB
- 80% of users accessed daily
- Cache 20% of active users (hot data)

Cache size = 10M × 1 KB × 20% = 2 GB
```

## Real-World Estimation Examples

### Example 1: URL Shortener

```
Requirements:
- 100 million new URLs per month
- 10:1 read:write ratio
- URLs stored for 5 years

Estimations:

Write QPS:
100M / 30 days / 86,400 seconds ≈ 38 QPS

Read QPS:
38 × 10 = 380 QPS

Storage (5 years):
- Each URL: 500 bytes (short URL + long URL + metadata)
- 100M × 12 months × 5 years = 6 billion URLs
- 6B × 500 bytes = 3 TB

Bandwidth:
- Read: 380 × 500 bytes = 190 KB/s (negligible)
- Write: 38 × 500 bytes = 19 KB/s (negligible)

Servers:
- Write: 38 QPS → 1 server
- Read: 380 QPS → 1 server
- With redundancy: 4 servers total
```

### Example 2: Twitter

```
Requirements:
- 500 million DAU
- Each user views 100 tweets/day
- Each user creates 2 tweets/day
- 20% of tweets have media

Estimations:

Tweet Creation QPS:
500M × 2 / 86,400 ≈ 11,574 QPS

Tweet Read QPS:
500M × 100 / 86,400 ≈ 578,704 QPS

Storage per day:
- Text: 1B tweets × 300 bytes = 300 GB
- Media: 200M × 500 KB = 100 TB
- Total: ~100 TB/day

Cache (for timeline):
- Cache 10% of daily tweets
- 100M tweets × 1 KB = 100 GB

Bandwidth:
- Read: 578K × 1 KB = 578 MB/s = 4.6 Gbps
- Media: 578K × 20% × 500 KB = 57.8 GB/s = 462 Gbps (CDN offload)
```

### Example 3: Chat System (WhatsApp)

```
Requirements:
- 1 billion users
- 10% DAU = 100 million DAU
- Each user sends 40 messages/day
- Average message: 100 bytes

Estimations:

Message QPS:
100M × 40 / 86,400 ≈ 46,296 QPS

Storage per day:
100M × 40 × 100 bytes = 400 GB/day
5-year storage: 400 GB × 365 × 5 = 730 TB

Connections:
- 100M concurrent connections (long-lived WebSocket)
- Each server handles 100K connections
- Servers: 100M / 100K = 1,000 servers

Bandwidth:
- 46K × 100 bytes = 4.6 MB/s (text only)
- With media: significantly higher
```

## Estimation Framework

### Step-by-Step Process

```
1. Clarify Requirements
   - DAU/MAU
   - Read/write ratio
   - Data retention
   - Latency requirements

2. Estimate Traffic
   - Write QPS = DAU × actions per user / 86,400
   - Read QPS = Write QPS × read:write ratio
   - Peak QPS = 2-3 × Average QPS

3. Estimate Storage
   - Data per item
   - Items per day
   - Retention period
   - Replication factor

4. Estimate Bandwidth
   - QPS × Average response size
   - Consider CDN offload

5. Estimate Servers
   - Peak QPS / QPS per server
   - Add redundancy (2x)

6. Estimate Memory/Cache
   - Working set size
   - Cache hit ratio target
```

## Common Gotchas

### Don't Forget
- **Replication**: 3x storage for redundancy
- **Peak traffic**: 2-3x average QPS
- **Growth rate**: 20-50% year-over-year
- **Overhead**: Indexes, metadata, logs add 20-50%
- **Compression**: Text compresses 3-5x

### Quick Sanity Checks
```
- Is QPS reasonable for a single server? (1K-10K typical)
- Is storage in the right order of magnitude?
- Does bandwidth make physical sense?
- Are numbers consistent with each other?
```

## Interview Tips

1. **Always estimate first** — It shows systematic thinking
2. **Round numbers** — 1,157 QPS → "roughly 1,200 QPS"
3. **State assumptions** — "Assuming 10% of users are DAU..."
4. **Use whiteboard** — Write numbers as you calculate
5. **Double-check units** — KB vs MB vs GB can make huge differences
6. **Consider growth** — "Current 1K QPS, but expecting 10K in 2 years"
7. **Mention specific numbers** — "Redis can handle 100K QPS, so one instance suffices"
8. **Don't over-precise** — Rough estimates are fine, exact numbers aren't the point

## Common Mistakes

- ❌ Not stating assumptions
- ❌ Confusing units (KB vs MB)
- ❌ Forgetting about replication
- ❌ Not considering peak traffic
- ❌ Over-engineering for billions when you have thousands
- ❌ Forgetting about growth rate

## Cross-References

- [Scalability](./scalability.md) — How to scale based on estimates
- [Database Design](./database-design.md) — Storage and QPS drive DB choice
- [Caching Strategy](./caching-strategy.md) — Cache sizing based on working set
- [Load Balancing](./load-balancing-design.md) — Server count determines LB setup
- [Data Intensive](./data-intensive.md) — Large-scale data storage
- [Estimation](../estimation.md)
- [Latency Numbers](../latency-numbers.md)
- [Cloud EC2](../../cloud/aws/ec2.md)
