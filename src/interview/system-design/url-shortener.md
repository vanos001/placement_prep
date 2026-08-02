# Design a URL Shortener

> **Difficulty:** ⭐⭐ | **Asked at:** Google, Amazon, Meta, Microsoft | **Time:** 45 minutes

## 🎯 Problem Statement

Design a URL shortening service like TinyURL or bit.ly that:
- Shortens long URLs to compact aliases
- Redirects short URLs to original URLs
- Handles high traffic with low latency

---

## Step 1: Requirements

### Functional Requirements
1. Given a long URL, generate a short, unique URL
2. Given a short URL, redirect to the original long URL
3. Users can optionally set custom short URLs
4. Links expire after a configurable time (default: 5 years)
5. Users can view click analytics (click count, referrers, geography)

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Availability | 99.99% |
| Latency (redirect) | < 100ms |
| Throughput | 100M URLs/day created |
| Read:Write ratio | 100:1 (redirects far exceed creation) |
| Durability | URLs never lost |

### Capacity Estimation

```
Write: 100M URLs/day = ~1,160 writes/sec
Read:  100:1 ratio = ~116,000 reads/sec
Peak:  2x average = ~2,320 writes/sec, ~232,000 reads/sec

Storage (5 years):
  100M × 365 × 5 = 182.5B records
  182.5B × 500 bytes = ~91 TB

Bandwidth:
  Write: 1,160 × 500B = ~580 KB/s
  Read: 116,000 × 500B = ~58 MB/s

Cache (80/20 rule - 20% of URLs get 80% of traffic):
  Daily active URLs: ~20M unique
  Cache size: 20M × 500B = ~10 GB
```

---

## Step 2: High-Level Design

### Architecture

```
┌──────────┐     ┌──────────────┐     ┌───────────────┐
│  Client  │────→│ Load Balancer│────→│  API Servers  │
└──────────┘     └──────────────┘     └───────┬───────┘
                                              │
                    ┌─────────────────────────┼────────────────┐
                    │                         │                │
              ┌─────▼──────┐          ┌──────▼───────┐  ┌────▼─────┐
              │   Cache    │          │   Database   │  │Analytics │
              │  (Redis)   │          │ (PostgreSQL) │  │  (Kafka) │
              └────────────┘          └──────────────┘  └──────────┘
```

### API Design

```
POST /api/v1/urls
  Body: { "long_url": "https://example.com/very/long/path", 
          "custom_alias": "my-link",        // optional
          "expires_in_days": 365 }          // optional, default 1825
  Response: { "short_url": "https://short.ly/abc123",
              "expires_at": "2026-08-02T00:00:00Z" }

GET /{short_code}
  Response: 301 Redirect → long_url
  (Use 301 for permanent, 302 for temporary — affects browser caching)

GET /api/v1/urls/{short_code}/analytics
  Response: { "total_clicks": 12345,
              "unique_visitors": 8901,
              "clicks_by_date": { "2025-01-01": 100, ... },
              "top_referrers": { "google.com": 500, ... },
              "top_countries": { "US": 3000, "IN": 2000, ... } }
```

### Database Schema

```sql
CREATE TABLE urls (
    id            BIGSERIAL PRIMARY KEY,
    short_code    VARCHAR(10) UNIQUE NOT NULL,
    long_url      TEXT NOT NULL,
    user_id       BIGINT REFERENCES users(id),
    created_at    TIMESTAMP DEFAULT NOW(),
    expires_at    TIMESTAMP,
    is_custom     BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_short_code ON urls(short_code);
CREATE INDEX idx_expires_at ON urls(expires_at);

CREATE TABLE click_events (
    id            BIGSERIAL PRIMARY KEY,
    short_code    VARCHAR(10) NOT NULL,
    clicked_at    TIMESTAMP DEFAULT NOW(),
    ip_address    INET,
    user_agent    TEXT,
    referrer      TEXT,
    country_code  VARCHAR(2)
);

CREATE INDEX idx_click_code ON click_events(short_code);
CREATE INDEX idx_click_time ON click_events(clicked_at);
```

---

## Step 3: Deep Dive

### URL Shortening Algorithm

**Approach 1: Hash + Truncate**
```python
import hashlib
import base64

def generate_short_code(long_url, length=7):
    hash_bytes = hashlib.md5(long_url.encode()).digest()
    short_code = base64.urlsafe_b64encode(hash_bytes).decode()[:length]
    return short_code

# Problem: Collision possible
# Solution: Check DB, if collision → append counter or use different hash
```

**Approach 2: Base62 Encoding of Auto-Increment ID**
```python
CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def id_to_short_code(id):
    if id == 0:
        return CHARS[0]
    code = []
    while id > 0:
        code.append(CHARS[id % 62])
        id //= 62
    return ''.join(reversed(code))

# ID 12345 → short code "3d7"
# Pros: No collision, deterministic
# Cons: Predictable (security concern), requires distributed ID generation
```

**Approach 3: Pre-Generated Key Service (Recommended)**
```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Key Service   │────→│   Key Store     │────→│  API Server  │
│ (generates keys │     │ (available keys)│     │ (assigns key │
│  in batches)    │     │                 │     │  to URL)     │
└─────────────────┘     └─────────────────┘     └──────────────┘

- Pre-generate millions of random 7-char keys (Base62)
- Store in DB table: keys(code, is_used)
- API server fetches batch of 1000 unused keys
- When batch runs low, fetch more
- Pros: No collision, not predictable, fast
```

### Caching Strategy

```
Cache Design (Redis):
├── Key: short_code
├── Value: long_url
├── TTL: 24 hours (refreshed on access)
├── Eviction: LRU
└── Size: ~10 GB for hot URLs

Read Path:
1. Client → GET /abc123
2. API Server → Check Redis cache
3. Cache HIT → Return 301 redirect (fast path)
4. Cache MISS → Query PostgreSQL
5. Store in Redis → Return 301 redirect

Write Path:
1. Client → POST /api/v1/urls
2. API Server → Generate short code
3. Write to PostgreSQL
4. Write to Redis cache
5. Return short URL

Cache Invalidation:
- On URL deletion: Delete from Redis
- On URL update: Delete from Redis (lazy reload)
- TTL expiration: Automatic cleanup
```

### Database Scaling

```
Read Replicas:
┌──────────────┐
│   Primary    │──── Writes
│  (PostgreSQL)│
└──────┬───────┘
       │ Replication
  ┌────┼────┬────────┐
  │    │    │        │
┌─▼─┐┌─▼─┐┌─▼─┐  ┌──▼──┐
│R1 ││R2 ││R3 │  │ R4  │  ← Reads (4 replicas)
└───┘└───┘└───┘  └─────┘

Sharding Strategy (if needed at scale):
- Shard by short_code hash
- Consistent hashing for even distribution
- Cross-shard queries avoided by design
```

### Handling Expired URLs

```
Approach 1: Lazy Cleanup (Recommended)
- On read: Check expires_at → If expired, return 404 + delete
- Background job: Periodically scan and delete expired URLs
- Pros: Simple, no extra infrastructure
- Cons: Stale data in DB until accessed

Approach 2: TTL-based (Redis handles expiration)
- Set Redis TTL = expires_at - now()
- Background job cleans PostgreSQL
- Pros: Automatic expiration in cache
- Cons: Two systems to manage
```

---

## Step 4: Trade-offs

### 301 vs 302 Redirect
| Code | Meaning | Browser Behavior | Use Case |
|------|---------|-----------------|----------|
| 301 | Permanent | Caches redirect | SEO, permanent links |
| 302 | Temporary | Always asks server | Analytics, temporary links |

**Recommendation:** Use 302 if you need accurate analytics (every request hits your server).

### Hash vs Sequential ID
| Approach | Pros | Cons |
|----------|------|------|
| Hash + Truncate | No extra service | Collision possible |
| Sequential ID | No collision | Predictable, requires distributed ID |
| Pre-generated keys | No collision, secure | Extra service to maintain |

### Synchronous vs Async Analytics
| Approach | Pros | Cons |
|----------|------|------|
| Synchronous write | Simple, immediate | Slows down redirect |
| Async (Kafka) | Fast redirect, decoupled | Eventual consistency |

**Recommendation:** Async — redirect should be as fast as possible.

---

## 🔍 Monitoring & Reliability

```
Key Metrics to Monitor:
├── Redirect latency (p50, p95, p99)
├── Cache hit ratio (target: > 95%)
├── URL creation rate
├── Error rate (4xx, 5xx)
├── Database connection pool usage
└── Kafka consumer lag

Alerting:
├── Redirect latency p99 > 200ms → Warning
├── Cache hit ratio < 90% → Investigate
├── Error rate > 1% → Critical
└── Database replication lag > 5s → Warning
```

## 🔗 Cross-References

- [Rate Limiter](./rate-limiter.md) — Protect the URL shortener from abuse
- [Key-Value Store](./kv-store.md) — Deep dive on distributed storage
- [Caching Concepts](../../cheatsheets/architecture.md) — Caching strategies
- [Database Questions](../dbms-questions.md) — SQL vs NoSQL trade-offs
