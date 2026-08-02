# System Design Framework: Universal Approach

## 🎯 The 4-Step Framework

Use this framework for **any** system design question:

```
┌─────────────────────────────────────────────────────────┐
│            SYSTEM DESIGN FRAMEWORK                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  STEP 1: REQUIREMENTS (5 min)                           │
│  ├── Functional requirements (what it does)             │
│  ├── Non-functional requirements (how it performs)      │
│  ├── Constraints & assumptions                          │
│  └── Capacity estimation                                │
│                                                         │
│  STEP 2: HIGH-LEVEL DESIGN (10 min)                     │
│  ├── Core components                                    │
│  ├── Data flow                                          │
│  ├── API design                                         │
│  └── Database schema (high-level)                       │
│                                                         │
│  STEP 3: DEEP DIVE (20 min)                             │
│  ├── Detailed component design                          │
│  ├── Database schema (detailed)                         │
│  ├── Scaling strategy                                   │
│  ├── Bottleneck identification & resolution             │
│  └── Monitoring & reliability                           │
│                                                         │
│  STEP 4: TRADE-OFFS & WRAP-UP (10 min)                  │
│  ├── Pros/cons of key decisions                         │
│  ├── Alternative approaches                             │
│  ├── Future improvements                                │
│  └── Summary                                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Step 1: Requirements (5 minutes)

### Functional Requirements

Ask: **"What does the system need to do?"**

```
Example (URL Shortener):
✅ Users can create short URLs from long URLs
✅ Users are redirected when visiting short URLs
✅ Users can customize short URL aliases
✅ Links expire after a configurable time
✅ Users can view analytics (click counts)

❌ Out of scope:
- User authentication (assume handled elsewhere)
- Payment processing
- Mobile app design
```

**Tip:** Start with 3-5 core features. Ask the interviewer which ones to focus on.

### Non-Functional Requirements

Ask: **"How should the system perform?"**

```
Availability:    99.99% uptime (52 min downtime/year)
Latency:         < 100ms for redirects
Throughput:      100M URLs created/day
Consistency:     Eventual consistency OK for analytics
Durability:      URLs should not be lost
Scalability:     Handle 10x traffic spikes
```

### Capacity Estimation

```
Traffic:
- 100M URLs created/day = ~1,160 URLs/sec
- 10:1 read:write ratio = ~11,600 reads/sec
- Peak: 2x average = ~2,320 writes/sec, ~23,200 reads/sec

Storage:
- Each URL record: ~500 bytes (long URL + short code + metadata)
- 100M/day × 365 days × 5 years = 182.5B records
- 182.5B × 500 bytes = ~91 TB

Bandwidth:
- Write: 1,160 × 500 bytes = ~580 KB/s
- Read: 11,600 × 500 bytes = ~5.8 MB/s
```

---

## Step 2: High-Level Design (10 minutes)

### Draw the Architecture

```
┌──────────┐     ┌──────────────┐     ┌───────────────┐
│  Client  │────→│ Load Balancer│────→│  API Servers  │
└──────────┘     └──────────────┘     └───────┬───────┘
                                              │
                    ┌─────────────────────────┼────────────────┐
                    │                         │                │
              ┌─────▼──────┐          ┌──────▼───────┐  ┌────▼─────┐
              │   Cache    │          │   Database   │  │  Queue   │
              │  (Redis)   │          │ (PostgreSQL) │  │ (Kafka)  │
              └────────────┘          └──────────────┘  └──────────┘
```

### API Design

```
POST /api/v1/urls
  Request:  { "long_url": "https://...", "custom_alias": "my-link", "expires_at": "..." }
  Response: { "short_url": "https://short.ly/abc123", "created_at": "..." }

GET /{short_code}
  Response: 301 Redirect to long URL

GET /api/v1/urls/{short_code}/analytics
  Response: { "total_clicks": 1234, "clicks_by_date": {...}, "referrers": {...} }

DELETE /api/v1/urls/{short_code}
  Response: { "status": "deleted" }
```

### Database Schema (High-Level)

```sql
-- Core table
urls (
    id            BIGINT PRIMARY KEY,
    short_code    VARCHAR(10) UNIQUE NOT NULL,
    long_url      TEXT NOT NULL,
    user_id       BIGINT,
    created_at    TIMESTAMP,
    expires_at    TIMESTAMP,
    click_count   BIGINT DEFAULT 0
)

-- Analytics table (append-only)
click_events (
    id            BIGINT PRIMARY KEY,
    short_code    VARCHAR(10),
    clicked_at    TIMESTAMP,
    ip_address    VARCHAR(45),
    user_agent    TEXT,
    referrer      TEXT
)
```

---

## Step 3: Deep Dive (20 minutes)

### Pick 2-3 Components to Deep Dive

**Always ask:** "Which component would you like me to dive deeper into?"

Common deep-dive topics:
1. **Data Storage** — Sharding, replication, indexing
2. **Caching** — Strategy, invalidation, consistency
3. **Scaling** — Horizontal scaling, load balancing
4. **Reliability** — Failover, redundancy, monitoring

### Deep Dive: Caching Strategy

```
Cache-Aside Pattern (most common):
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │────────→│   App    │────────→│ Database │
└──────────┘         │  Server  │         └──────────┘
                     └────┬─────┘
                          │
                     ┌────▼─────┐
                     │  Cache   │
                     │ (Redis)  │
                     └──────────┘

Read Path:
1. Check cache → Hit? Return cached data
2. Cache miss → Query database
3. Store result in cache → Return data

Write Path:
1. Write to database
2. Invalidate cache (delete key)
3. Next read will fetch fresh data from DB

Cache Eviction:
- LRU (Least Recently Used) — default for most cases
- TTL (Time To Live) — for time-sensitive data
```

### Deep Dive: Database Sharding

```
Sharding by Short Code (Hash-based):
┌─────────────────────────────────────────┐
│           Hash Function                 │
│     shard_id = hash(short_code) % N     │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐
│Shard0│ │Shard1│ │Shard2│ │Shard3│
│ a-f  │ │ g-l  │ │ m-r  │ │ s-z  │
└──────┘ └──────┘ └──────┘ └──────┘

Pros: Even distribution, simple routing
Cons: Range queries hard, resharding complex
```

### Deep Dive: Scaling

```
Horizontal Scaling:
├── Stateless API servers behind load balancer
├── Database read replicas for read-heavy workloads
├── Cache cluster (Redis Cluster)
└── Message queue for async processing

Load Balancing:
├── L4 (TCP) — Fast, simple
├── L7 (HTTP) — Content-aware routing
├── Algorithms: Round Robin, Least Connections, IP Hash
└── Health checks every 5-10 seconds
```

---

## Step 4: Trade-offs & Wrap-up (10 minutes)

### Discuss Key Trade-offs

```
"I chose [Decision A] over [Decision B] because:

Decision: SQL vs NoSQL
├── SQL chosen for: ACID compliance, complex queries
├── Trade-off: Harder to scale horizontally
└── Mitigation: Read replicas, connection pooling

Decision: Cache-aside vs Write-through
├── Cache-aside chosen for: Simpler, better for read-heavy
├── Trade-off: Possible stale data
└── Mitigation: Short TTL, cache invalidation on write

Decision: Synchronous vs Async processing
├── Async chosen for: Click analytics
├── Trade-off: Eventual consistency
└── Acceptable: Analytics don't need real-time accuracy"
```

### Mention Future Improvements

```
"If I had more time, I would consider:
1. Geographic distribution with multi-region deployment
2. Rate limiting to prevent abuse
3. Analytics with real-time streaming (Kafka + Flink)
4. A/B testing framework for URL aliases
5. Machine learning for spam detection"
```

---

## 📋 System Design Checklist

Use this checklist to ensure you cover everything:

```
Requirements:
□ Functional requirements defined
□ Non-functional requirements quantified
□ Capacity estimated (traffic, storage, bandwidth)
□ Out of scope items listed

High-Level Design:
□ Core components identified
□ Data flow diagram drawn
□ API endpoints designed
□ Database schema outlined

Deep Dive:
□ Database design (schema, indexing, sharding)
□ Caching strategy (what to cache, TTL, invalidation)
□ Scaling approach (horizontal, vertical, auto-scaling)
□ Reliability (replication, failover, monitoring)
□ Security (authentication, encryption, rate limiting)

Trade-offs:
□ Key decisions justified
□ Alternatives discussed
□ Bottlenecks identified and addressed
□ Future improvements mentioned
```

## 🎯 Common Mistakes to Avoid

1. **Jumping to solution** without understanding requirements
2. **Over-engineering** — Don't design for Google scale if it's a startup
3. **Ignoring non-functional requirements** — Availability and latency matter
4. **Not drawing diagrams** — Visual communication is essential
5. **Staying too abstract** — Dive into specifics when asked
6. **Not discussing trade-offs** — Every decision has pros and cons
7. **Forgetting operational concerns** — Monitoring, alerting, deployment

## 🔗 Cross-References

- [URL Shortener](./url-shortener.md) — Example of applying this framework
- [Architecture Concepts](../../cheatsheets/architecture.md) — Quick reference for all concepts
- [Architecture Questions](../arch-questions.md) — Interview questions on architecture
- [Coding Framework](../coding/framework.md) — Similar structured approach for coding
