# Rate Limiting Pattern

## Overview

A rate limiter caps how many requests a caller can make in a time window. The
mechanism is more interesting than it looks: "cap" can mean *reject the
excess*, *queue the excess*, or *shape the traffic into a smooth stream*, and
the algorithm choice determines which one you get.

Rate limiting serves four goals at once:

1. **Protect a downstream** — keep a service from being overloaded by a
   single noisy client.
2. **Enforce fairness** — make sure one tenant can't starve another.
3. **Enforce billing tiers** — "100 requests/minute on the free plan,
   10 000 on Pro".
4. **Defend against abuse** — brute-force login attempts, scraping, DDoS.

All four share the same primitives. This page covers the five algorithms,
how to make them work in a distributed system, and the response contract a
client should see.

## The Five Algorithms

### Token Bucket

A bucket holds up to `capacity` tokens. Refill rate is `refill_tokens_per_second`.
Each request consumes one token. If the bucket is empty, the request is
rejected (or queued, depending on the limiter's policy).

```
   capacity = 10, refill = 2 tokens/s
   ─────────────────────────────────
   t=0    : bucket = [10/10] tokens
   t=0    : 8 requests → 8 consumed, bucket = [2/10]
   t=0.5  : refill 1 token → bucket = [3/10]
   t=1.0  : 3 requests → all admitted, bucket = [0/10]
   t=1.5  : 1 request → rejected (bucket empty)
```

Two properties make token bucket the most common choice:

- **Burst tolerance.** A client that has been idle accumulates tokens up to
  `capacity` and can spend them all at once. A burst of `capacity` is
  always allowed; sustained rate is `refill`.
- **Cheap.** Each request is O(1) — decrement a counter, occasionally
  refill.

```python
import time, threading

class TokenBucket:
    def __init__(self, capacity: float, refill_per_sec: float):
        self.capacity = capacity
        self.refill = refill_per_sec
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self.last
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill)
        self.last = now

    def allow(self, n: int = 1) -> bool:
        with self.lock:
            self._refill(time.monotonic())
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False
```

The subtle correctness issue: the refill must be computed lazily (on the
next `allow()`) using the elapsed time, not as a periodic background thread.
A periodic thread would wake up 1000 s after the bucket went idle and add
2000 tokens at once, which would be wrong (the cap is `capacity`, but the
scheduler delay hides the timing).

### Leaky Bucket

A leaky bucket is a queue with a constant drain rate. Requests enter the
queue; a worker drains one request every `1/rate` seconds. If the queue is
full, the request is rejected.

```
   capacity = 10, drain rate = 2 requests/s
   ────────────────────────────────────────
   t=0    : queue = []
   t=0    : 8 requests enqueued → queue = [8 items]
   t=0.5  : drain 1 → queue = [7]
   t=1.0  : drain 1 → queue = [6]
   t=1.5  : 10 more requests arrive → only 4 fit → 6 rejected
   t=2.0  : drain 1 → queue = [9]
```

The contrast with token bucket is sharp:

| Property            | Token bucket                | Leaky bucket                  |
| ------------------- | --------------------------- | ----------------------------- |
| Allows bursts       | Yes, up to `capacity`        | No, output is constant rate   |
| Output rate         | Variable (limited by caller) | Constant (limited by limiter) |
| Typical use         | APIs, billing                | Traffic shaping               |
| Implementation      | Counter, lazy refill         | FIFO queue + worker           |

Leaky bucket is the right choice when the downstream is sensitive to bursts
— e.g., a low-throughput API that handles bursts badly. Token bucket is the
default for most public APIs.

### Fixed Window

A counter that resets at the start of each window (e.g. each minute on the
minute). Each request within the window increments the counter; when the
counter exceeds the limit, requests are rejected.

```
   limit = 5 reqs/min, window aligned to wall clock
   ────────────────────────────────────────────────
   t=00:00    requests 1..5 → all admitted
   t=00:00:30 request 6 → rejected
   t=01:00    window resets → requests 1..5 admitted again
```

Cheap (one counter per client per window) but has a **double-spike problem**:
a client that fires 5 requests at 00:59 and 5 more at 01:00 has made 10
requests in 1 s — twice the intended limit — because each request falls
into a different window. For most abuse-prevention use cases this is
acceptable; for billing it's a bug.

### Sliding Window Log

Keep a timestamped log of every request within the window. On each new
request, drop entries older than `window_seconds` and count what remains.

```
   limit = 5 reqs/min, window = 60 s
   ────────────────────────────────────────────────
   t=00:00:00   log = []                      → admit, log = [00:00:00]
   t=00:00:10   log = [00:00:00]              → admit, log = [..., 00:00:10]
   t=00:00:20   log = [00:00:00, 00:00:10]    → admit, ...
   ...
   t=00:00:50   log = [00:00:00..00:00:40]    → admit (count=5)
   t=00:01:00   log = [00:00:00..00:00:50]    → still 5 entries → reject
   t=00:01:01   log drops 00:00:00 → count=4   → admit
```

Sliding window log gives a perfectly accurate count — no double-spike bug —
but the memory cost is O(limit) per client. At 1000 requests/min/key and 1 M
keys, that's a billion entries. Generally too expensive without compaction.

### Sliding Window Counter

A hybrid that approximates the sliding window with two fixed windows. Keep
the current window's count and the previous window's count; the estimate is
a weighted blend:

```
   estimate = current_count
              + previous_count * (window_size - time_into_current) / window_size
```

If a request arrives 45 s into a 60 s window, the previous window
contributes `prev × (60 - 45) / 60 = prev × 0.25` to the estimate. This
caps the over-count error at the previous window's full size and avoids the
double-spike bug.

```
   limit = 5 reqs/min
   ────────────────────────────────────────────────────────────────────────
   At t = 00:00:45  (45 s into the current window):
     current_count = 4
     previous_count = 5
     estimate = 4 + 5 * (60 - 45) / 60 = 4 + 5 * 0.25 = 5.25
     limit = 5 → request rejected (estimate > 5)

   At t = 00:01:00 (window rolls over; previous becomes 5, current becomes 0)
     current_count = 0
     previous_count = 5
     estimate = 0 + 5 * (60 - 0) / 60 = 5
     limit = 5 → request admitted (estimate = limit exactly)
```

Memory is O(2 counters per client per window) — dramatically cheaper than
the log. The Cloudflare rate limiter is built on a sliding window counter
variant, as is Stripe's. This is the recommended default for a distributed
limiter.

## Distributed Rate Limiting

A rate limiter on a single node is easy. A rate limiter that's consistent
across a 100-node fleet is harder: every request must consult shared state.

### The naive approach: shared counter

Pseudocode:

```python
count = redis.incr(key)
if count == 1:
    redis.expire(key, 60)
if count > limit:
    return HTTP_429
```

This *works* but has two issues:

1. **Race on expiry.** Between `incr` returning 1 and `expire` running, the
   process could crash and leave a key without a TTL — it would live
   forever, never resetting. Use `INCR ... EX 60` (Redis 7+) or a Lua
   script to make it atomic.
2. **Hot key.** Every request hits the same Redis shard for a hot client.
   At 100k RPS this saturates a single Redis node.

### The Redis + Lua script

The atomic primitive is a single Lua script executed in Redis's eval:
`EVALSHA` makes it a one-round-trip operation.

```lua
-- sliding-window-counter.lua
local key      = KEYS[1]
local now_ms   = tonumber(ARGV[1])
local window_ms= tonumber(ARGV[2])
local limit    = tonumber(ARGV[3])
local cur_win  = math.floor(now_ms / window_ms)
local prev_win = cur_win - 1
local hkey     = key .. ":" .. cur_win
local phkey    = key .. ":" .. prev_win

local cur = tonumber(redis.call('HGET', hkey, 'count') or '0')
local prev = tonumber(redis.call('GET', phkey) or '0')

-- Estimate.
local elapsed = now_ms - cur_win * window_ms
local weight = (window_ms - elapsed) / window_ms
local estimate = cur + (prev * weight)

if estimate >= limit then
    return 0  -- reject
end

-- Increment current window; record prev on the way out.
redis.call('HINCRBY', hkey, 'count', 1)
redis.call('EXPIRE', hkey, math.ceil(window_ms * 2 / 1000))
return 1  -- admit
```

Round-trips per request: one (`EVALSHA`). Atomicity: guaranteed (Redis
scripts run atomically). Correctness: sliding-window-counter approximation,
which is good enough for ~99% of rate-limiting use cases.

The official Redis documentation recommends this family of scripts. The
GitHub `redis-cell` module implements token bucket in Lua for exactly this
purpose.

### Sharding and the local-cache trick

The hot-key problem is real at scale. Two mitigations:

1. **Shard the key.** For a per-tenant limit, hash the tenant ID to a shard
   and route to a specific Redis node. Each node holds its own slice; no
   node sees all the traffic.
2. **Local cache with periodic refresh.** Each application instance keeps a
   local token bucket and *samples* the global Redis counter every N ms
   (e.g. 100 ms) to realign. Between samples, the local bucket admits
   requests optimistically; if the local bucket and the global counter
   disagree, the local one is throttled. This reduces Redis load by ~1000×.

Stripe's blog describes this pattern as a "limiter cache" — local optimistic
admission with a global source of truth.

### API gateways

Most teams shouldn't write their own. AWS API Gateway, Kong, Envoy, and
Cloudflare all ship rate limiters that handle the distributed state, the
sharding, and the response contract for you. The trade-off is
configurability: a custom limiter can implement any algorithm (e.g. one
that grants 10 000 requests/min to Pro users and 100 to Free users, with
different algorithms per tier). A gateway limiter is usually
token-bucket-only and configured via a YAML file.

AWS API Gateway throttles by default — every deployed REST API has a
per-stage burst limit and a steady-state rate limit. These are token-bucket
limiters, with `burst` = bucket capacity and `rate` = refill rate. The
documentation calls them "throttling" but the underlying algorithm is
exactly token bucket.

## The 429 Response and Retry-After

When a request is rejected, the response **must** be `429 Too Many Requests`
with a `Retry-After` header. RFC 6585 defines the status; RFC 7231 defines
the header. The header is either seconds or an HTTP-date:

```
   HTTP/1.1 429 Too Many Requests
   Content-Type: application/json
   Retry-After: 30
   X-RateLimit-Limit: 100
   X-RateLimit-Remaining: 0
   X-RateLimit-Reset: 1700000000

   {"error": "rate_limited", "retry_after_seconds": 30}
```

The de facto `X-RateLimit-*` headers (popularised by Twitter and adopted
by Stripe, GitHub, and others) tell the client the limits and the reset
time. They're not standardised, but they're universal enough that every
well-behaved API client understands them.

The contract on the client side: **respect `Retry-After`**. If the client
retries immediately, it's just DDOSing you. If it retries after the
specified delay, the system recovers. Stripe's documentation explicitly
calls this out: clients that retry early get progressively longer
`Retry-After` values.

A few edge cases:

- **What to do with `Retry-After: 0`?** Some implementations send 0 to mean
  "try immediately". The safer reading is RFC 7231's, which says the value
  is in seconds, so `0` means "no delay required" — but treat it as a
  minimum of 1 s anyway.
- **HTTP-date format**: `Retry-After: Wed, 21 Oct 2025 07:28:00 GMT`. Less
  common than seconds; some clients mishandle it.
- **What to do when the header is missing?** Fall back to exponential
  backoff. Treat the 429 as a transient failure.

## Algorithm Comparison

```
   Algorithm          Mem/req   Bursty   Accurate   Distributed-friendly
   ─────────────────────────────────────────────────────────────────────────
   Token bucket       O(1)      yes      approx     yes (single counter)
   Leaky bucket       O(1)      no       exact      yes
   Fixed window       O(1)      no       approx     yes (single counter)
   Sliding window log O(n)      yes      exact      no (high cardinality)
   Sliding window cnt O(1)      yes      approx     yes (two counters)
```

Pick by the use case:

- **Public API with per-tenant quotas** → sliding window counter (Redis +
  Lua). Stripe, Cloudflare.
- **Ingress to a downstream that dislikes bursts** → leaky bucket.
- **Anti-abuse on a single endpoint** (e.g. login attempts per IP) →
  sliding window log; the small cardinality makes the log affordable.
- **Edge DDoS protection** → token bucket per source IP, sampled globally;
  the goal is to drop the bulk of the abuse, not to count exactly.

## Common Pitfalls

1. **Counting on a single-node Redis.** Every hot client hammers one Redis
   shard. Shard by tenant ID, or use the local-cache trick.
2. **Forgetting atomicity.** Two `INCR` + `EXPIRE` calls in sequence are a
   race. Always use a Lua script or a single pipeline.
3. **Returning 503 instead of 429.** A 503 means "I'm broken"; a 429 means
   "you're going too fast". The client response differs — clients retry a
   503 indefinitely, but back off on a 429.
4. **No `Retry-After` header.** A 429 without one invites clients to retry
   at whatever rate they like.
5. **Limiting only at the edge.** If your edge rate-limits at 1000 RPS but
   your downstream can only handle 100 RPS per shard, the edge limiter
   doesn't help a per-shard overload. Limit at every layer.
6. **Burst vs steady state confusion.** Token bucket's `capacity` is the
   burst, `refill` is the steady state. Picking a high capacity with a low
   refill means "I tolerate a single burst but the sustained rate is low";
   the reverse means "no bursts but a high steady rate". They're not
   interchangeable.

## Interview Questions

### Q: Why is the token bucket the most popular algorithm?

It's the only one that admits bursts while enforcing a sustained rate, and
it's O(1) per request with two state variables (token count, last refill
time). APIs that allow a client to "warm up" — make an idle client's first
few requests succeed — want this behaviour. The fact that it maps to one
Redis `INCR` (or one Lua script) makes it cheap to distribute.

### Q: How does a sliding window counter avoid the fixed-window double-spike?

A fixed window counts requests in [t, t+W) and resets at t+W. A client can
make `limit` requests at t+W-ε and `limit` more at t+W+ε — twice the limit
in 2 ε. The sliding window counter blends the previous and current windows
weighted by the elapsed time into the current window, so a request at t+W+ε
sees `current_count + prev_count × (W - ε) / W ≈ prev_count × 1` — it's
still near the limit and gets rejected.

### Q: How would you implement rate limiting in a global load-balanced API
without a single point of truth?

Three patterns: (1) **sharded Redis** with consistent hashing by tenant ID —
each tenant's limiter lives on one node, eliminating cross-node contention;
(2) **local + global** with periodic realignment — local token bucket
admits optimistically, samples global Redis every N ms to correct drift;
(3) **session-based** — a sticky session routes a client to one node, and
that node's local limiter is authoritative for the session. (1) is the
cleanest, (2) is the most scalable, (3) breaks if sessions aren't sticky.

### Q: What's the difference between rate limiting and throttling?

The terms are sometimes used interchangeably, but "throttling" tends to
mean *delaying* excess requests (the leaky-bucket behaviour) while "rate
limiting" tends to mean *rejecting* them (the token-bucket behaviour). AWS
API Gateway uses "throttling" for both because the underlying algorithm is
token bucket, which rejects rather than delays.

## References

- Cloudflare: *Rate Limiting with Redis and Lua* — describes the
  sliding-window-counter approach and the production deployment story.
  https://blog.cloudflare.com/counting-things-a-lot-of-different-things/
- Stripe API documentation: *Rate Limits* — covers the response contract,
  the `X-RateLimit-*` headers, and the tiered approach.
  https://docs.stripe.com/api/rate_limits
- AWS API Gateway Developer Guide: *Throttle API requests using account-level
  and API-level throttling* — the configuration of burst vs steady-state,
  the underlying token bucket, and the response headers.
  https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html
- Redis documentation: *Pattern: Rate limiter* — the official walkthrough
  of the fixed-window and sliding-window Lua scripts, including atomic
  `INCR + EXPIRE` and the use of `EVALSHA` for single-round-trip checks.
  https://redis.io/commands/incr/
- RFC 6585: *Additional HTTP Status Codes* — defines `429 Too Many
  Requests`. https://www.rfc-editor.org/rfc/rfc6585
- RFC 9110: *HTTP Semantics* — defines the `Retry-After` header field
  semantics (formerly RFC 7231).
  https://www.rfc-editor.org/rfc/rfc9110#name-retry-after
- Kong Gateway documentation: *Rate Limiting plugin* — the configuration
  knobs for an off-the-shelf API-gateway limiter, useful as a reference
  design.
  https://docs.konghq.com/hub/kong-inc/rate-limiting/

## Related Topics

- [Circuit Breaker Deep Dive](./circuit-breaker-deep.md) — the failure-side
  counterpart: a rate limiter protects the server; a circuit breaker
  protects the client.
- [Bulkhead Deep Dive](./bulkhead-deep.md) — per-tenant bulkheads are the
  concurrency counterpart to per-tenant rate limits.
- [API Gateway](../api/api-gateway.md) — where rate limiting usually lives
  in a microservices architecture.
- [Retry and Timeout Patterns](./retry-timeout.md) — the client-side
  companion; how to retry against a 429 correctly.
- [Backpressure Pattern](./backpressure-pattern.md) — the in-process
  equivalent: limit *this* process's production when its consumer can't
  keep up.
