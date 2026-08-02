# Back-of-the-Envelope Estimation

## Overview

Back-of-the-envelope estimation is the art of making quick, rough calculations to size a system during a design interview. These estimates help you determine the number of servers, database size, bandwidth requirements, and storage needs. The goal isn't precision — it's demonstrating structured thinking and comfort with numbers.

## The Approach

1. **Clarify assumptions** — DAU, requests per user, data sizes
2. **Estimate traffic** — QPS, peak QPS
3. **Estimate storage** — data per day, per year
4. **Estimate bandwidth** — bytes per second
5. **Estimate compute** — servers needed

## Numbers Every Engineer Should Know

### Powers of 2

| Power | Approximate | Full Value |
|-------|-------------|------------|
| 2^10 | 1 thousand | 1,024 |
| 2^20 | 1 million | 1,048,576 |
| 2^30 | 1 billion | 1,073,741,824 |
| 2^40 | 1 trillion | 1,099,511,627,776 |

### Time Conversions

| Unit | Seconds |
|------|---------|
| 1 minute | 60 |
| 1 hour | 3,600 |
| 1 day | 86,400 |
| 1 month | 2,592,000 (~2.5M) |
| 1 year | 31,536,000 (~31.5M) |

### Latency Numbers

| Operation | Latency |
|-----------|---------|
| L1 cache reference | 0.5 ns |
| L2 cache reference | 7 ns |
| RAM reference | 100 ns |
| SSD random read | 150 μs |
| HDD random read | 10 ms |
| Round trip within same datacenter | 0.5 ms |
| Round trip CA to Netherlands | 150 ms |

### Common Data Sizes

| Item | Size |
|------|------|
| 1 character (ASCII) | 1 byte |
| 1 character (UTF-8) | 1–4 bytes |
| Integer (32-bit) | 4 bytes |
| Long (64-bit) | 8 bytes |
| UUID | 16 bytes |
| SHA-256 hash | 32 bytes |
| Tweet (280 chars) | ~280 bytes |
| Typical web page | ~2 MB |
| High-res photo | ~3 MB |
| 1 min HD video | ~50 MB |
| 1 hour HD video | ~3 GB |

## Estimation Template

### Example: Design Twitter

**Step 1: Clarify assumptions**
- DAU: 200 million
- Tweets per user per day: 2 (average)
- Feed reads per user per day: 10
- Tweet size: 280 bytes + 50 bytes metadata = 330 bytes ≈ 0.5 KB
- Media (images): 10% of tweets include an image (1 MB avg)

**Step 2: Traffic estimation**

```
Write QPS = 200M × 2 / 86,400 ≈ 4,600 tweets/s
Peak write QPS = 4,600 × 3 ≈ 14,000 tweets/s

Read QPS = 200M × 10 / 86,400 ≈ 23,000 feed reads/s
Peak read QPS = 23,000 × 3 ≈ 70,000 feed reads/s
```

**Step 3: Storage estimation**

```
Daily tweet storage = 4,600 × 86,400 × 0.5 KB ≈ 200 MB/day
Yearly tweet storage = 200 MB × 365 ≈ 73 GB/year

Daily image storage = 4,600 × 86,400 × 0.1 × 1 MB ≈ 40 GB/day
Yearly image storage = 40 GB × 365 ≈ 14.6 TB/year

5-year storage = 73 GB × 5 + 14.6 TB × 5 ≈ 73 TB
```

**Step 4: Bandwidth estimation**

```
Write bandwidth = 4,600 × 0.5 KB ≈ 2.3 MB/s
Read bandwidth = 23,000 × 10 KB (feed page) ≈ 230 MB/s
Peak read bandwidth = 70,000 × 10 KB ≈ 700 MB/s
```

**Step 5: Server estimation**

```
Each server handles ~10,000 QPS (typical web server)
Application servers = 70,000 / 10,000 = 7 servers
With redundancy: 7 × 3 = 21 servers
```

## Common Estimation Patterns

### QPS Estimation

```
QPS = DAU × actions_per_user_per_day / 86,400
Peak QPS = QPS × 3 (typical peak factor)
```

### Storage Estimation

```
Daily storage = QPS × seconds_per_day × data_size_per_item
Yearly storage = Daily storage × 365
N-year storage = Yearly storage × N
```

### Database Estimation

```
Rows = DAU × rows_per_user_per_day × 365 × years
Row size = sum of all column sizes
Total DB size = Rows × Row size × 1.2 (index overhead)
```

### Cache Estimation

```
Cache size = Daily_active_data × item_size
Rule of thumb: cache 20% of data that serves 80% of traffic
```

### Bandwidth Estimation

```
Bandwidth = QPS × average_response_size
Peak bandwidth = Peak QPS × average_response_size
```

## Capacity Planning Examples

### Example 1: Design a Chat System (WhatsApp-scale)

**Assumptions:**
- 500M DAU
- Each user sends 40 messages/day
- Each message = 100 bytes
- Each user reads 200 messages/day

**Calculations:**
```
Write QPS = 500M × 40 / 86,400 ≈ 231,000 msg/s
Read QPS = 500M × 200 / 86,400 ≈ 1,157,000 msg/s

Storage/day = 231,000 × 86,400 × 100 bytes ≈ 2 TB/day
Storage/year = 2 TB × 365 ≈ 730 TB/year
5-year storage ≈ 3.6 PB

Bandwidth (write) = 231,000 × 100 bytes ≈ 23 MB/s
Bandwidth (read) = 1,157,000 × 100 bytes ≈ 116 MB/s
```

### Example 2: Design a Video Streaming Service (YouTube-scale)

**Assumptions:**
- 2B DAU
- Each user watches 5 videos/day
- Average video = 50 MB (after compression)
- 500 hours of video uploaded per minute

**Calculations:**
```
Read QPS = 2B × 5 / 86,400 ≈ 116,000 video starts/s
Upload rate = 500 hours/min = 8.3 hours/s
Storage per minute = 500 hours × 60 min × 50 MB = 1.5 TB/min
Storage per day = 1.5 TB × 60 × 24 ≈ 2.16 PB/day
Storage per year ≈ 788 PB/year

CDN bandwidth = 116,000 × 50 MB / avg_duration
             = 116,000 × 50 MB / 300s ≈ 19.3 TB/s
```

### Example 3: Design a Rate Limiter

**Assumptions:**
- 100M DAU
- Each user makes 100 API calls/day
- Rate limit check latency: < 1ms
- Need to store counters for 1 hour window

**Calculations:**
```
QPS = 100M × 100 / 86,400 ≈ 116,000 checks/s
Peak QPS = 116,000 × 3 ≈ 350,000 checks/s

Unique keys = 100M (one per user)
Counter size = 8 bytes (key) + 8 bytes (count) = 16 bytes
Memory needed = 100M × 16 bytes ≈ 1.6 GB

Redis throughput: ~100K ops/s per instance
Redis instances needed = 350,000 / 100,000 ≈ 4 instances
```

## Server Sizing Rules of Thumb

| Component | Typical Capacity |
|-----------|-----------------|
| Web server (Nginx) | 50K–100K concurrent connections |
| Application server | 1K–10K QPS (depends on logic) |
| MySQL (single node) | 5K–10K QPS (simple queries) |
| Redis (single node) | 100K–200K ops/s |
| Kafka (single broker) | 100K–500K messages/s |
| Elasticsearch (single node) | 2K–10K queries/s |
| SSD IOPS | 10K–100K IOPS |
| HDD IOPS | 100–200 IOPS |
| Network (1 Gbps) | ~125 MB/s |
| Network (10 Gbps) | ~1.25 GB/s |

## Interview Tips

1. **Always start with assumptions** — "Let me assume 100M DAU..."
2. **Round aggressively** — 86,400 ≈ 100,000; 365 ≈ 400
3. **Show your work** — the process matters more than the answer
4. **Use powers of 10** — makes mental math easy
5. **State units clearly** — "200 MB/day" not just "200"
6. **Cross-check your answer** — does 3.6 PB for chat storage sound reasonable? (WhatsApp stores ~100B messages/day)
7. **Don't forget peak traffic** — 3x average is a common multiplier
8. **Mention replication** — multiply storage by replication factor (typically 3x)

## Key Takeaways

- Back-of-the-envelope estimation demonstrates structured thinking, not precision.
- Follow the template: assumptions → QPS → storage → bandwidth → servers.
- Know the key numbers: time conversions, data sizes, latency benchmarks.
- Round aggressively and use powers of 10 for mental math.
- Always include peak traffic (3x average) and replication factor (3x storage).
- Cross-check your answers against known real-world systems.

## Cross-References

- [Latency Numbers](./latency-numbers.md)
- [Capacity Planning](./hld/capacity-planning.md)
- [Performance vs Scalability](./performance-vs-scalability.md)
- [Framework](./framework.md)
- [Cloud Overview](../../cloud/overview.md)

