# Redis Advanced Patterns

## Overview

Beyond basic caching, Redis is used for distributed coordination, messaging, analytics, and more. This document covers the internals and tradeoffs of advanced patterns that come up frequently in system design interviews.

> **Relation to other docs:** For basic patterns (cache-aside, write-through, basic locks, rate limiting), see [patterns-and-internals.md](./patterns-and-internals.md). For the data structures these patterns build on, see [data-structures.md](./data-structures.md).

## Distributed Locks: Redlock Algorithm

The basic `SET key NX EX` lock (covered in [patterns-and-internals.md](./patterns-and-internals.md)) has a single-node failure mode: if the node crashes before the lock expires, no other client can acquire it until the TTL expires, and clock drift between client and server can cause the lock to be held too long or released too early.

### Redlock (by Salvatore Sanfilippo)

Redlock uses **N independent Redis instances** (N = 5 recommended) to acquire the lock:

```
1. Get current time T1
2. Try SET lock:token NX PX validity_time on ALL N instances
   (acquire with a unique token, not just a value)
3. Get current time T2
4. Calculate time_spent = T2 - T1
5. If acquired from MAJORITY (≥ (N/2)+1) instances
   AND time_spent < validity_time:
      → Lock acquired
      → Actual TTL = validity_time - time_spent
   Else:
      → Release lock on all instances (even those that succeeded)
      → Lock NOT acquired
```

### Redlock Pros and Cons

| Aspect | Argument |
--------|----------|
| **Pro: Safety** | Lock can only be held by one client as long as a majority of instances don't fail simultaneously. Clock drift is bounded by the time_spent check. |
| **Pro: Availability** | As long as a majority of instances are reachable, locks can be acquired. Tolerates up to floor(N/2) failures. |
| **Con: Complexity** | 5+ Redis instances to manage. Client must handle partial failures gracefully. |
| **Con: Fencing** | If a client's GC pause exceeds the TTL, another client may acquire the lock. A fencing token (monotonically increasing, issued by a separate service like ZooKeeper) is needed to prevent stale clients from writing. |
| **Con: Martin Kleppmann's critique** | Argues that Redlock relies on synchronous time bounds and that distributed systems should use consensus (Raft, Paxos) for locks. Salvatore (antirez) responded that for practical deployments with bounded GC pauses, Redlock is sufficient. |

### Practical Recommendation

For most production systems, a **single Redis instance with `SET NX EX` + retry** is sufficient. Use Redlock only when: (1) the lock protects a critical resource where correctness is worth the complexity, and (2) you need to survive a single Redis node failure. For truly safety-critical locks, consider etcd or ZooKeeper (which use Raft/ZAB for consensus).

## Rate Limiting: Sliding Window with Sorted Sets

The sliding window rate limiter provides smooth rate limiting (no "burst at boundary" problem of fixed windows) using sorted sets:

```bash
# Window: 60 seconds, limit: 100 requests per user

# Remove entries older than 60 seconds
ZREMRANGEBYSCORE rate:user:42 -inf <(current_timestamp - 60000)

# Count remaining entries
COUNT = ZCARD rate:user:42

# If under limit, add new entry
if COUNT < 100:
    ZADD rate:user:42 <current_timestamp_millis> <unique_request_id>
    # Allow request
else:
    # Reject request
```

### Performance Concerns

| Concern | Mitigation |
---------|-----------|
| **Memory per user** | Each request adds a sorted set entry (~64 bytes). Cleaned by `ZREMRANGEBYSCORE` on each request. |
| **Sorted set size** | Bounded to at most `limit` entries per user. |
| **Timestamp precision** | Use millisecond timestamps for sub-second windows. |
| **Race condition** | The ZREMRANGEBYSCORE + ZCARD + ZADD sequence is not atomic. Use a Lua script. |

### Alternative: Token Bucket with INCR

Simpler but less precise — uses a string counter reset at fixed intervals:

```bash
# Atomic rate limit check via Lua
EVAL "
  local current = redis.call('INCR', KEYS[1])
  if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
  end
  if current > tonumber(ARGV[2]) then
    return 0  -- rejected
  end
  return 1  -- allowed
" 1 rate:user:42 60 100
```

This is a **fixed window** counter (resets every 60s), not a true sliding window. Simpler, less memory, but allows 2x burst at window boundaries.

## Pub/Sub vs Streams for Messaging

| Aspect | Pub/Sub | Streams |
--------|---------|---------|
| **Persistence** | None — messages are fire-and-forget | Durable — stored in radix tree + listpacks |
| **Consumer groups** | No | Yes (XREADGROUP, XACK, XPENDING) |
| **Replay** | No — missed messages are gone | Yes — consumers can read from any ID |
| **Backpressure** | No — slow consumers are dropped | Yes — PEL (Pending Entries List) tracks unacknowledged messages |
| **Ordering** | Within a channel, but no guarantee for slow consumers | Guaranteed within a stream |
| **Use case** | Real-time notifications (chat, config updates) | Event sourcing, job queues, audit logs |
| **Max consumers** | Unlimited (no state) | Limited by PEL memory |

### When to Use Streams

```bash
# Producer
XADD events * type order_created order_id 42 user_id alice

# Consumer group
XGROUP CREATE events mygroup $ MKSTREAM
XREADGROUP GROUP mygroup consumer1 COUNT 1 BLOCK 5000 STREAMS events >

# Acknowledge processing
XACK events mygroup 1609459200000-0

# Check pending (not yet acked)
XPENDING events mygroup
```

Streams are the recommended choice for any durable messaging pattern. Pub/Sub should only be used for ephemeral notifications where message loss is acceptable.

## Lua Scripting for Atomic Operations

Redis is single-threaded for command execution. A Lua script runs **atomically** — no other client can execute commands between the script's start and end.

### Common Pattern: Check-And-Set

```lua
-- Transfer balance atomically
local from_balance = redis.call('GET', KEYS[1])
if tonumber(from_balance) >= tonumber(ARGV[1]) then
    redis.call('DECRBY', KEYS[1], ARGV[1])
    redis.call('INCRBY', KEYS[2], ARGV[1])
    return 1  -- success
else
    return 0  -- insufficient funds
end
```

### Lua Scripting Limits

| Limit | Value | Implication |
|-------|-------|-------------|
| **Max script execution time** | 5 seconds (default, `lua-time-limit`) | Long scripts block all other clients |
| **Script cache** | Scripts are SHA1-cached; use `EVALSHA` for efficiency | Don't pass large scripts repeatedly |
| **No access to external services** | Can't make HTTP calls, read files | All data must come from Redis |
| **Replication** | Scripts are replicated as effects (whole-script replication), not as individual commands | Side effects (random, time) may differ on replica |

### Best Practice

```bash
# Load script, get SHA1
SCRIPT LOAD "local v=redis.call('GET',KEYS[1]); redis.call('SET',KEYS[1],v+1); return v"
# Returns: 4e6d8fc7...

# Execute by SHA (avoids sending full script over network)
EVALSHA 4e6d8fc7... 1 counter
```

## Bitmap and HyperLogLog Use Cases

### Bitmap: User Engagement Tracking

```bash
# Track daily active users (user IDs 0 to N)
SETBIT active:2024-01-15 42 1    # user 42 was active
SETBIT active:2024-01-15 1001 1  # user 1001 was active

# Check if user was active
GETBIT active:2024-01-15 42       # returns 1

# Count active users
BITCOUNT active:2024-01-15

# Bitwise OR: users active in any of 3 days
BITOP OR active:3day  active:2024-01-15 active:2024-01-16 active:2024-01-17
BITCOUNT active:3day

# Memory: 1 bit per user → 10M users = ~1.25 MB per day
```

**Limitation:** Bitmaps are efficient when user IDs are dense (0 to N). Sparse IDs waste memory. For sparse data, use Sets instead.

### HyperLogLog: Cardinality Estimation

```bash
# Add elements (O(1) per element, ~12 KB fixed memory)
PFADD pageviews:home user1 user2 user3

# Get estimated count (standard error: 0.81%)
PFCOUNT pageviews:home  # returns ~3

# Merge: union cardinality of two HyperLogLogs
PFMERGE pageviews:home:3day pageviews:home:day1 pageviews:home:day2
PFCOUNT pageviews:home:3day
```

| Property | Value |
----------|-------|
| Memory | Fixed ~12 KB per key (16384 registers × 6 bits) |
| Error rate | ~0.81% standard error |
| Operations | ADD, COUNT, MERGE |
| Cannot | Remove elements, get individual members |

HyperLogLog is perfect for: unique visitor counts, distinct product views, cardinality of any set where approximate results are acceptable.

## Geospatial Queries

Redis geospatial commands use a **sorted set** under the hood, where scores are 52-bit geohash-encoded latitude/longitude values:

```bash
GEOADD locations 13.361389 38.115556 "Sicily"
GEOADD locations 15.087269 37.502669 "Palermo"

# Find locations within 100 km
GEORADIUS locations 13.361389 38.115556 100 km WITHCOORD WITHDIST

# Distance between two points
GEODIST locations "Sicily" "Palermo" km
```

Internals:
- Each location is stored as a sorted set member with a geohash score
- `GEORADIUS` converts the radius to a geohash range and uses `ZRANGEBYSCORE` + distance filtering
- Time complexity: O(log N + M) where M = results returned
- Geohash precision: ~1.1 km at 6 characters, ~0.1 km at 7 characters
- Redis uses a 52-bit geohash (26 bits lat + 26 bits lon)

## Interview Questions

**Q: What are the problems with a single-node Redis lock (`SET NX EX`)?**
A: (1) If the Redis node crashes, the lock is lost until TTL expires (or held forever if no TTL). (2) If the client's GC pause exceeds the TTL, another client may acquire the lock, and both proceed — a fencing token is needed to prevent this. (3) Clock drift between client and Redis can cause the lock to expire early or late. (4) Network partition can prevent lock release.

**Q: Explain the Redlock algorithm. Is it safe?**
A: Redlock acquires the lock on N=5 independent Redis instances. A client must acquire the lock on a majority (≥3) of instances within a validity time window. If successful, it holds the lock for `validity_time - time_spent`. It's debated: Martin Kleppmann argues it's unsafe because it relies on timing assumptions. Salvatore (antirez) counters that with bounded GC pauses and proper TTLs, it's safe enough for practical use. The pragmatic answer: use single-node `SET NX EX` for most cases, Redlock for critical resources, and etcd/ZooKeeper for distributed consensus-critical locks.

**Q: How would you implement a sliding window rate limiter in Redis? What are the alternatives?**
A: Sliding window: sorted set where score = timestamp, member = request ID. On each request, remove expired entries (`ZREMRANGEBYSCORE`), count remaining (`ZCARD`), and add new entry if under limit — wrapped in Lua for atomicity. Alternatives: (1) **Fixed window counter** (INCR + EXPIRE) — simpler but allows 2x burst at boundaries. (2) **Token bucket** (store tokens + last_refill_time, refill on each request) — smooth rate, but more complex. (3) **Leaky bucket** (queue + constant drain rate) — smooth output rate.

**Q: When would you use Redis Streams instead of a message queue like Kafka?**
A: Use Streams when: (1) you're already using Redis (no extra infrastructure), (2) message volume is moderate (millions/day, not millions/sec), (3) consumer groups with acknowledgment are needed, (4) the use case is within a single application or data center. Use Kafka when: (1) you need multi-datacenter replication, (2) message volume is very high, (3) you need exactly-once semantics with Kafka transactions, (4) you need long-term message retention (weeks/months).

**Q: Why are Lua scripts atomic in Redis, and what's the downside?**
A: Redis is single-threaded for command execution. A Lua script runs to completion before any other command is processed, guaranteeing atomicity. The downside: a long-running script blocks all other clients (default 5s limit). This makes Lua unsuitable for long computations, network calls, or operations that may take variable time. Keep scripts short and fast.

**Q: How does Redis store geospatial data internally?**
A: Redis stores geospatial data as a sorted set. Each location is a sorted set member, and the score is a 52-bit geohash encoding of the latitude and longitude (26 bits each). `GEORADIUS` converts the query radius to a geohash range, uses `ZRANGEBYSCORE` to find candidates, then filters by exact haversine distance. This gives O(log N + M) performance.

## References

- [Redlock vs Martin Kleppmann debate](https://antirez.com/news/101)
- [Redis Streams](https://redis.io/docs/data-types/streams/)
- [Redis Lua Scripting](https://redis.io/docs/interact/programmability/eval-intro/)
- [Redis Geospatial](https://redis.io/docs/data-types/geospatial/)
- [Redis HyperLogLog](https://redis.io/docs/data-types/hyperloglogs/)
