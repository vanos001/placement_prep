# Design a Rate Limiter

> **Difficulty:** ⭐⭐ | **Asked at:** Google, Amazon, Stripe, Cloudflare | **Time:** 30-40 minutes

## 🎯 Problem Statement

Design a rate limiter that:
- Limits the number of requests a client can make within a time window
- Works across distributed servers
- Supports different rate limiting rules
- Has minimal impact on request latency

---

## Step 1: Requirements

### Functional Requirements
1. Limit requests based on client ID (API key, IP, user)
2. Support multiple rate limit rules (e.g., 100 req/min, 1000 req/hour)
3. Return appropriate HTTP 429 responses when limit exceeded
4. Provide headers indicating remaining quota

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Latency overhead | < 1ms per request |
| Availability | 99.99% (fail-open if limiter down) |
| Accuracy | ±1% of actual count |
| Throughput | 1M+ requests/sec |

---

## Step 2: High-Level Design

### Where to Place the Rate Limiter

```
Option 1: Client-side (unreliable — client can bypass)
Option 2: API Gateway (recommended — centralized)
Option 3: Application-level (flexible but per-server)

Recommended: API Gateway level
┌──────────┐     ┌──────────────┐     ┌───────────────┐
│  Client  │────→│ API Gateway  │────→│  API Servers  │
└──────────┘     │ + Rate Limit │     └───────────────┘
                 └──────┬───────┘
                        │
                 ┌──────▼───────┐
                 │  Rate Limit  │
                 │   Store      │
                 │  (Redis)     │
                 └──────────────┘
```

---

## Step 3: Deep Dive — Rate Limiting Algorithms

### 1. Token Bucket

```
Concept:
├── Bucket holds tokens (max = bucket_size)
├── Tokens added at fixed rate (refill_rate)
├── Each request consumes 1 token
└── If no tokens → reject request

Parameters:
├── bucket_size: Maximum burst capacity
└── refill_rate: Tokens added per second

Example: bucket_size=10, refill_rate=2/sec
├── Allows burst of 10 requests
├── Sustained rate: 2 requests/sec
```

```python
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def allow_request(self):
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def _refill(self):
        now = time.time()
        tokens_to_add = (now - self.last_refill) * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
```

**Pros:** Simple, allows bursts, memory efficient
**Cons:** Doesn't enforce strict window limits

### 2. Sliding Window Log

```
Concept:
├── Keep a log of all request timestamps
├── For each new request, count requests in past window
├── If count >= limit → reject
└── Remove expired entries

Example: limit=5 requests/minute
Timestamps: [10:00:01, 10:00:15, 10:00:30, 10:00:45, 10:00:50]
New request at 10:01:02 → Remove 10:00:01 → Count=4 → Allow
New request at 10:01:05 → Count=5 → Reject
```

```python
class SlidingWindowLog:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self.log = []  # sorted list of timestamps

    def allow_request(self):
        now = time.time()
        window_start = now - self.window

        # Remove expired entries
        self.log = [ts for ts in self.log if ts > window_start]

        if len(self.log) < self.limit:
            self.log.append(now)
            return True
        return False
```

**Pros:** Very accurate, no boundary issues
**Cons:** High memory usage (stores every timestamp)

### 3. Sliding Window Counter (Recommended) ✅

```
Concept:
├── Combine fixed window counter with sliding window
├── Weight previous window's count based on overlap
└── Much more memory efficient than log

Example: limit=10 requests/minute
Previous window (10:00-10:01): 8 requests
Current window (10:01-10:02): 3 requests
Current time: 10:01:20 (20/60 = 33% into current window)

Weighted count = 8 × (1 - 0.33) + 3 = 5.36 + 3 = 8.36
8.36 < 10 → Allow request
```

```python
class SlidingWindowCounter:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds

    def allow_request(self, key):
        now = time.time()
        current_window = int(now / self.window)
        previous_window = current_window - 1
        position_in_window = (now % self.window) / self.window

        prev_count = redis.get(f"{key}:{previous_window}") or 0
        curr_count = redis.get(f"{key}:{current_window}") or 0

        weighted_count = prev_count * (1 - position_in_window) + curr_count

        if weighted_count < self.limit:
            redis.incr(f"{key}:{current_window}")
            redis.expire(f"{key}:{current_window}", self.window * 2)
            return True
        return False
```

**Pros:** Memory efficient, accurate, smooth
**Cons:** Slightly more complex

### 4. Fixed Window Counter

```
Concept:
├── Divide time into fixed windows (e.g., per minute)
├── Count requests in current window
├── If count >= limit → reject
└── Reset count at window boundary

Example: limit=5 requests/minute
Window [10:00-10:01]: 1,2,3,4,5 → 6th request REJECTED
Window [10:01-10:02]: Counter resets → requests allowed
```

**Pros:** Simple, memory efficient
**Cons:** Burst at window boundary (2x limit possible)

### 5. Leaky Bucket

```
Concept:
├── Requests enter a queue (bucket)
├── Processed at fixed rate (leak rate)
├── If queue full → reject
└── Smooths out traffic spikes

Parameters:
├── queue_size: Maximum queue length
└── leak_rate: Requests processed per second
```

**Pros:** Smooth output rate, prevents bursts
**Cons:** Doesn't allow legitimate bursts, queue delays

---

### Algorithm Comparison

| Algorithm | Accuracy | Memory | Burst Handling | Complexity |
|-----------|----------|--------|---------------|------------|
| Token Bucket | Good | O(1) | Allows bursts | Low |
| Sliding Window Log | Excellent | O(n) | Strict | Medium |
| Sliding Window Counter | Very Good | O(1) | Smooth | Medium |
| Fixed Window | Fair | O(1) | Boundary issue | Low |
| Leaky Bucket | Good | O(n) | No bursts | Low |

**Recommendation:** Sliding Window Counter for most use cases.

---

### Distributed Rate Limiting with Redis

```
Challenge: Multiple API servers need consistent rate limiting

Solution: Centralized Redis store

┌──────────┐  ┌──────────┐  ┌──────────┐
│ Server 1 │  │ Server 2 │  │ Server 3 │
└─────┬────┘  └─────┬────┘  └─────┬────┘
      │             │             │
      └─────────────┼─────────────┘
                    │
              ┌─────▼─────┐
              │   Redis   │
              │ (Central) │
              └───────────┘

Redis Implementation (Atomic):
-- Lua script for atomic check-and-increment
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = tonumber(redis.call('GET', key) or '0')

if current >= limit then
    return 0  -- rejected
else
    redis.call('INCR', key)
    redis.call('EXPIRE', key, window)
    return 1  -- allowed
end

Response Headers:
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1704067260
Retry-After: 30  (only when rate limited)
```

### Rate Limiting Rules

```yaml
# Example rule configuration
rules:
  - name: "api_general"
    key: "client_id"
    limit: 100
    window: 60  # seconds

  - name: "login_attempts"
    key: "ip_address"
    limit: 5
    window: 300  # 5 minutes

  - name: "expensive_operation"
    key: "user_id"
    limit: 10
    window: 3600  # 1 hour

  - name: "global_limit"
    key: "global"
    limit: 1000000
    window: 1  # 1 million req/sec global
```

---

## Step 4: Trade-offs

### Fail-Open vs Fail-Closed
| Strategy | When Limiter Down | Risk |
|----------|------------------|------|
| Fail-Open | Allow all requests | Abuse possible |
| Fail-Closed | Reject all requests | Service outage |

**Recommendation:** Fail-open with monitoring alerts.

### Centralized vs Local Rate Limiting
| Approach | Consistency | Latency | Complexity |
|----------|------------|---------|------------|
| Centralized (Redis) | Strong | +1ms network | Medium |
| Local (per-server) | Weak | ~0ms | Low |

**Recommendation:** Centralized for accuracy, local for very latency-sensitive paths.

## 🔗 Cross-References

- [Key-Value Store](./kv-store.md) — Redis design for rate limit counters
- [URL Shortener](./url-shortener.md) — Rate limiting to prevent abuse
- [Architecture Concepts](../../cheatsheets/architecture.md) — Distributed systems fundamentals
- [Networking Questions](../network-questions.md) — HTTP status codes, headers
