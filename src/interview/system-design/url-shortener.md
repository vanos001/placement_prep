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

### Redirect Semantics: 301, 302, 307, 308 — A Cost-Benefit Table

The Step 4 table below compresses this to two rows; the full answer needs all four codes, because the choice silently decides what gets cached and therefore what your system is allowed to change later. RFC 9110 defines the family: "The 3xx (Redirection) class of status code indicates that further action needs to be taken by the user agent in order to fulfill the request" [1]. The load-bearing sentences:

- **301** — "the target resource has been assigned a new permanent URI and any future references to this resource ought to use one of the enclosed URIs," and — the operationally fatal one — "A 301 response is heuristically cacheable; i.e., unless otherwise indicated by the method definition or explicit cache controls (see Section 4.2.2 of [CACHING])" [1]. "Heuristically cacheable" is why 301 *removes you from your own system*: browsers and intermediaries are invited to pin the mapping and never return. Per-click analytics survives only on cache misses (computed: at a 90% browser cache-hit rate you observe ~10% of clicks, so 20K logged clicks in an hour implies ~200K real ones); the target can no longer be edited for anyone who already cached it; and the expirations from Step 1 become unenforceable for that audience.
- **302** — temporary by definition: "Since the redirection might be altered on occasion, the client ought to continue to use the target URI for future requests" [1]. Not heuristically cacheable — every click comes back. Analytics stay exact; the price is 100% of traffic on your edge.
- **307/308** — the method-preserving pair: 307 says "the user agent MUST NOT change the request method if it performs an automatic redirection to that URI," and 308 is its permanent, heuristically-cacheable sibling [1]. For plain GET redirects they behave like 302/301 respectively; they matter when API clients POST *through* short links — the 301/302 notes explicitly permit a user agent to flip POST to GET "for historical reasons" [1].

| Code | Method preserved | Browser caches | Per-click analytics | Target editable | Expiry enforceable |
|------|-----------------|----------------|---------------------|-----------------|--------------------|
| 301 | No (may flip POST→GET) | Yes | Only on cache miss | No — burned in | No |
| 302 | No (may flip POST→GET) | No | Every click | Yes | Yes |
| 307 | Yes | No | Every click | Yes | Yes |
| 308 | Yes | Yes | Only on cache miss | No — burned in | No |

This is why real shorteners split: **301 for max-cache** (destination never changes; re-resolving every click is pure waste) and **302 for analytics/editable/expiring links**. Both are defensible; picking 301 per-link and wanting analytics later is not recoverable.

**The Referer you never see.** RFC 9110 also decides what happens to the clicker's headers: when automatically following a redirect, the user agent should resend the request after removing "resource-specific header fields, including (but not limited to) Referer, Origin, Authorization, and Cookie" [1]. Two consequences: destination sites usually see shortener traffic as *direct* (the original referrer is stripped at the hop), and the shortener itself becomes the last party holding full click context — which is why referrer data is simultaneously a product feature here and a privacy obligation.

**The CDN decision.** Three escalating architectures: (1) *redirect at edge* — the CDN caches the 30x response itself, keyed by host+path; browsers won't cache a 302, but with explicit `Cache-Control` your edge can cache it for seconds-to-minutes, absorbing spikes while keeping analytics nearly complete; (2) *lookup at edge* — an edge worker resolves the code from an edge-resident KV store; a full global push is only affordable for the hot subset; (3) *302-to-resolver* — the edge always asks your resolver fleet: maximal control, minimal cache benefit. Step 2's design is (3) with a Redis L1; production systems typically mix (1) for the hot prefix of links and (3) for the long tail.

### Abuse, Safety, and the Operational Underbelly

A shortener is a machine for laundering the appearance of a URL: a trusted domain, an opaque code space (Step 3's random key pool makes unpredictability a *feature*), and a redirect that fires before any content is seen. That combination is a magnet for phishing and malware, so safety is a pipeline, not a checklist item.

**URL reputation checking.** The standard reference is Google Safe Browsing: "a Google service that lets client applications check URLs against Google's constantly updated lists of unsafe web resources. Examples of unsafe web resources are social engineering sites (phishing and deceptive sites) and sites that host malware or unwanted software" [2]. Its documented use case — "Prevent users from posting links to known infected pages from your site" [2] — is exactly the shortener's creation path. One licensing subtlety is interview-relevant: "The Safe Browsing API is for non-commercial use only. If you need to use APIs to detect malicious URLs for commercial purposes - meaning 'for sale or revenue-generating purposes' - please refer to the Web Risk API" [2] — a commercial shortener buys a reputation product, not the free browser API. Pipeline placement follows the QPS asymmetry: check *synchronously at creation* (writes are ~100× rarer than redirects) and *asynchronously at redirect* (sampled, or only for codes not recently seen) — a per-redirect vendor lookup would multiply your hottest path's latency.

**Rate limiting by identity.** Creation is limited per API key (quota, tier, and billing hang off the key); anonymous creation gets much lower per-IP ceilings, because anonymous bulk shortening is the classic spam-campaign shape. The redirect path is throttled only coarsely (per-IP at the edge) — it is 100:1 hotter, and its real protection is caching, not rejection. Algorithm selection lives in [Rate Limiter](./rate-limiter.md).

**Spam takedown workflow.** Detection sources (user reports, reputation-vendor hits, heuristics on the target URL) feed a review queue; the action on confirmed abuse is **deactivate, don't delete**: flip the mapping's active flag and serve an interstitial (or 410) rather than silently 404ing — deletion also destroys the audit trail an appeal or investigation needs. Every takedown carries a recorded decision, an owner, and an appeal SLA, because a blocked legitimate campaign is a customer-trust incident, and the false-positive rate is the metric that governs how aggressive auto-takedown can be.

**Custom domains and certificates.** Enterprise links live on `brand.co`, meaning one TLS-termination fleet presenting tens of thousands of certificates via SNI. Manual cert management cannot survive that; ACME automation can — Let's Encrypt's objective is to "make it possible to set up an HTTPS server and have it automatically obtain browser-trusted certificates without any human intervention," proving control via challenges such as "Provisioning a DNS record under example.com, or Provisioning an HTTP resource under a well-known URI" [3]; RFC 8555 states the guarantee: "Challenges provide the server with assurance that an account holder is also the entity that controls an identifier" [4]. Note the convergence: the ACME challenge *is* your domain-ownership verification at onboarding — a customer who can complete it for `brand.co` has demonstrated exactly the DNS control the platform needs. The failure mode is silent: a mistyped CNAME makes the challenge fail and kills `https://brand.co/launch` with a TLS error, so onboarding is a provisioning state machine with retries, per-domain status in the customer dashboard, and alerts on renewal failure.

### Analytics Without Killing the Read Path

Step 2 already strands click events in Kafka; the discipline that makes the separation honest is: **the redirect path performs exactly one O(1) read (the mapping lookup) and zero writes.** Everything else is a side channel that may fall behind or lose data without the redirect noticing — analytics is never inline.

**Fire-and-forget click events.** The resolver emits `(short_code, ts, ip, ua, referrer, geo)` to the event stream and returns the redirect immediately. Back-pressure policy is explicit: if the broker is unavailable or overloaded, *sample or drop* — never queue indefinitely in front of the user-facing path. Click analytics is estimated data; mapping correctness is not. This event → durable log → derived views pattern is [stream processing](../../data-engineering/stream-processing.md) in miniature.

**Async aggregation into rollups.** Consumers aggregate into per-link daily rollups — `(link_id, date) → clicks`, plus dimension slices (referrer, country, device). The arithmetic of why: at the case study's 43.2B raw events/day (computed: 500K/s × 86,400 s), dashboards over raw events pay per-query scan costs; rollups are bounded by links × dimensions (computed worst case: 1M active links × 200 country codes = 200M rows/day ≈ **216× smaller** than the raw stream; realistic links have <5 countries each). The [real-world case study](./real-world/url-shortener.md) shows the ClickHouse end of this pipeline.

**Unique vs raw clicks.** "Click count" is two different numbers: *raw clicks* (every event) and *unique clicks* (distinct users). Uniqueness needs an identity — user id (rarely available on the anonymous redirect path), a cookie, or a salted hash of IP+UA — plus a dedup window, giving the key `(link_id, user_or_ip_hash, window)`. Salt matters: the shortener must not become a re-identifiable record of who clicked what, so hash with a rotated salt and accept that uniqueness becomes approximate across rotations. Exact daily distinct counts over billions of events are unaffordable; cardinality estimators trade ~2% error for constant memory — see [Probabilistic Data Structures](./probabilistic-data-structures.md).

**Why zero writes on the read path.** Three tempting regressions, all interview red flags: (1) a synchronous `INCR clicks:{code}` couples redirect latency to the counter store's fate; (2) per-click writes turn the viral link's key into a single contention point; (3) any analytics outage becomes a redirect outage. State the contract instead: analytics may lag by seconds (the freshness SLO is a product decision — the case study picks 5s); the redirect may not lag at all.

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

## 📚 References

1. RFC 9110, *HTTP Semantics* — Sections 15.4 (Redirection 3xx), 15.4.2 (301), 15.4.3 (302), 15.4.8 (307), 15.4.9 (308) — <https://www.rfc-editor.org/rfc/rfc9110> — fetched in full this session; all quoted sentences verbatim.
2. Google Safe Browsing documentation — <https://developers.google.com/safe-browsing> — fetched this session; service description, "Prevent users from posting links..." use case, and the non-commercial-use clause (with its Web Risk pointer) quoted verbatim from the same page.
3. Let's Encrypt, "How It Works" — <https://letsencrypt.org/how-it-works/> — fetched this session; the ACME objective and the two challenge examples quoted verbatim.
4. RFC 8555, *Automatic Certificate Management Environment (ACME)* — Section 8 (Identifier Validation Challenges) — <https://www.rfc-editor.org/rfc/rfc8555> — fetched this session; the challenges sentence quoted verbatim.

*Note:* no academic DOI could be verified for this expansion — Crossref bibliographic queries for URL-shortening measurement studies returned only unrelated entries this session, so none is cited.

## 🔗 Cross-References

- [ID Generation](./hld/id-generation.md) — the birthday-bound collision math behind short-code space sizing (linked, not re-derived here)
- [Rate Limiter](./rate-limiter.md) — Protect the URL shortener from abuse
- [Key-Value Store](./kv-store.md) — Deep dive on distributed storage
- [URL Shortener Case Study](./real-world/url-shortener.md) — bit.ly-class production numbers for this same design
- [Caching Concepts](../../cheatsheets/architecture.md) — Caching strategies
- [Database Questions](../dbms-questions.md) — SQL vs NoSQL trade-offs
