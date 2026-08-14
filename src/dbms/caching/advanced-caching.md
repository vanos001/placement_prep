# Advanced Caching Strategies

## Cache Hierarchy

Caching exists at every layer of a system. Understanding the full hierarchy helps you place data at the right level to minimize latency and maximize hit rates.

```
Request Path (latency increases with distance from CPU)

CPU L1 Cache         ~1ns      (per core, 32-64 KB)
    ↓ miss
CPU L2 Cache         ~4ns      (per core, 256 KB - 1 MB)
    ↓ miss
CPU L3 Cache         ~12ns     (shared, 4-64 MB)
    ↓ miss
Application Cache    ~100ns-1μs (in-process, e.g., Caffeine, Guava)
    ↓ miss
Distributed Cache    ~1-5ms    (Redis, Memcached)
    ↓ miss
Database             ~5-50ms   (PostgreSQL, MySQL with disk I/O)
    ↓ miss
CDN / Edge Cache     ~10-100ms (CloudFront, Cloudflare, for static content)
```

Each layer has a different tradeoff between speed, capacity, and consistency:

| Layer | Latency | Capacity | Eviction | Consistency |
-------|---------|----------|----------|-------------|
| CPU Cache | ~1-12ns | KB-MB | Hardware (LRU-like) | Hardware-coherent |
| Application Cache | ~100ns-1μs | MB-GB | LRU, LFU, TTL | In-process, immediate |
| Distributed Cache | ~1-5ms | GB-TB | LRU, LFU, TTL | Eventual (configurable) |
| CDN | ~10-100ms | TB-PB | TTL, purge | Eventual (seconds-minutes) |

## Cache Stampede Prevention

A cache stampede (also called thundering herd or dog-pile) occurs when a popular cache key expires and many concurrent requests simultaneously miss the cache, all hitting the backend at once.

### Problem

```
Time →
Request 1: cache miss → fetch from DB (slow)
Request 2: cache miss → fetch from DB (slow)  ← all hitting DB simultaneously
Request 3: cache miss → fetch from DB (slow)
...
Request 100: cache miss → fetch from DB (crashes it)
```

### Solutions

**1. Locking (single-flight / request coalescing)**

Only one request populates the cache for a given key; others wait.

```java
// Guava Cache with CacheLoader (built-in single-flight)
LoadingCache<String, User> cache = CacheBuilder.newBuilder()
    .expireAfterWrite(10, TimeUnit.MINUTES)
    .build(new CacheLoader<String, User>() {
        public User load(String key) {
            return db.query("SELECT * FROM users WHERE id = ?", key);
        }
    });
// Concurrent calls for the same key → single DB query
```

Redis: use `SET key value NX EX ttl` (set-if-not-exists) or RedLock for distributed locking.

**2. Probabilistic early expiration**

Each request, before using a cached value, has a small probability (e.g., 1%) of treating it as expired and refreshing it proactively.

```
if (cache.contains(key)) {
    if (random() < 0.01) {  // 1% chance
        // Refresh asynchronously
        asyncRefresh(key);
    }
    return cache.get(key);
}
```

**3. Stale-while-revalidate**

Serve the stale value while asynchronously refreshing:

```
value = cache.get(key);
if (value.isStale()) {
    asyncRefresh(key);  // Don't block the request
}
return value;
```

| Approach | Latency Impact | Complexity | Best For |
----------|---------------|------------|----------|
| Locking | Blocked requests wait | Low (Guava built-in) | Single-process, hot keys |
| Probabilistic | None (async) | Low | Distributed, moderate hotness |
| Stale-while-revalidate | None (async) | Medium | High-traffic, tolerance for stale data |

## Cache Penetration Prevention

Cache penetration occurs when requests for **non-existent data** (keys that will never exist in the database) bypass the cache and hit the database every time. An attacker can exploit this to DDoS the database.

### Solutions

**1. Null caching (cache empty results)**

```java
value = cache.get(key);
if (value == null) {
    value = db.query(key);
    if (value == null) {
        cache.set(key, NULL_MARKER, shortTTL);  // Cache the miss for 2-5 minutes
    } else {
        cache.set(key, value, normalTTL);
    }
}
```

Tradeoff: if the data is later created in the database, it won't appear until the null cache entry expires. Use a short TTL (2-5 minutes) for null entries.

**2. Bloom filter**

A probabilistic data structure that tests set membership with zero false negatives and a controllable false positive rate.

```
Before querying:
  if (!bloomFilter.mightContain(key)) {
      return null;  // Definitely doesn't exist, skip cache + DB
  }
  // Might exist, check cache then DB
```

| Bloom Filter Property | Value |
|----------------------|-------|
| False negatives | Zero (never says "not in set" for items that are in it) |
| False positives | Configurable (e.g., 1% at 10 bits per element) |
| Space | ~10 bits per element (1% FPR) |
| Lookup | O(k) hash evaluations, ~O(1) |
| Deletion | Not supported natively (use Counting Bloom Filter) |

For a system with 100M user IDs, a Bloom filter with 1% false positive rate requires ~125 MB — stored in memory, checked before cache and DB.

**3. Request validation**

Reject obviously invalid requests at the API gateway level (invalid ID format, out-of-range values). This prevents the request from reaching any cache or database.

## Cache Warming Strategies

Cache warming pre-populates the cache before serving traffic, avoiding a cold-start storm.

| Strategy | How | When | Use Case |
----------|-----|------|----------|
| **Static preload** | Script reads DB and populates cache at startup | Deploy, restart | Read-heavy, predictable keys |
| **Traffic replay** | Replay production traffic against the new cache | Deploy | Most realistic warming |
| **Background refresh** | Scheduled job refreshes hot keys | Continuous | Time-sensitive data (prices, leaderboards) |
| **Lazy warming** | Let the first requests populate the cache (natural) | Always | Acceptable cold-start latency |

For Redis: use `MGET` or a Lua script to bulk-load data. For application caches: pre-compute on startup.

Example background refresh for a leaderboard:

```
// Every 30 seconds, refresh the top 100 users
@Scheduled(fixedRate = 30000)
public void warmLeaderboard() {
    List<User> top100 = db.queryTopUsers(100);
    redis.set("leaderboard:top100", top100, TTL_5_MIN);
}
```

## Cache Invalidation Strategies

> "There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

### Time-Based (TTL)

The simplest strategy: set an expiration time and let the cache handle it.

| TTL Value | Use Case |
-----------|----------|
| 1-5 seconds | Real-time data (stock prices, counters) |
| 5-60 minutes | Session data, user profiles, product info |
| 1-24 hours | Configuration, reference data, catalog |
| 24+ hours | Static content, rarely-changing data |

### Event-Based

Invalidate the cache when the underlying data changes.

```
Write Path:
1. Update the database
2. Publish event to message bus (Kafka, Redis Pub/Sub)
3. Cache subscribers receive event and delete the cache key
```

```java
// On data update
db.update(user);
redis.del("user:" + user.getId());
// Or: redis.publish("cache:invalidate", "user:" + user.getId());
```

Advantage: near-immediate consistency. Disadvantage: requires the write path to be aware of all cache keys (can miss keys with complex queries).

### Versioned / Cache-Aside with Version Tag

Store a version number with the data. Increment the version on write; the cache key includes the version.

```
Cache key: "user:123:v5"

On read: get version from DB or metadata store, check cache for "user:123:v5"
On write: increment version to v6, write to DB
Next read: checks "user:123:v6" → cache miss → fetch from DB → cache
Old "user:123:v5" expires naturally via TTL (fallback)
```

This avoids the need to actively invalidate — old versions simply become unreachable.

### Write-Through vs. Write-Behind

| Strategy | Write Path | Read Path | Consistency | Use Case |
----------|-----------|-----------|-------------|----------|
| **Cache-Aside** | Write to DB, invalidate cache | Check cache, miss → DB → populate cache | Eventual | Most common |
| **Write-Through** | Write to cache AND DB synchronously | Check cache, always hit (if write-through) | Strong | Low-write, strong consistency needed |
| **Write-Behind** | Write to cache, async write to DB | Always hit | Weak | High-write, tolerates data loss |
| **Refresh-Ahead** | Write to DB, invalidate cache | Cache proactively refreshes before expiry | Near-real-time | Predictable access patterns |

## Multi-Layer Cache Consistency

When caching at multiple layers (application + distributed + CDN), invalidation must propagate correctly.

```
Client → CDN → Load Balancer → Application (local cache) → Redis → Database
```

### Invalidation Order (Bottom-Up)

When data changes, invalidate **bottom-up**: distributed cache first, then CDN.

```
1. Update database
2. Invalidate Redis key
3. Publish invalidation event
4. Application caches pick up event → invalidate local cache
5. CDN purge (API call to Cloudflare/CloudFront)
```

Why bottom-up? If you invalidate CDN first, subsequent requests hit Redis (which still has old data) and re-populate the CDN with stale content.

### Common Pitfall: Re-population Between Layers

```
1. Invalidate Redis
2. Before CDN purge completes, a request hits CDN → miss
3. Request goes to application → local cache miss
4. Application reads from Redis → miss → reads from DB → gets NEW data
5. Application writes new data to Redis
6. But CDN was not yet purged, so the NEXT request hits CDN (stale)
7. Eventually CDN expires, but there's an inconsistency window
```

Mitigation: use short TTLs at the CDN layer, purge CDN first with synchronous confirmation, or use versioned cache keys that make stale entries unreachable.

## References
- [Redis Documentation — Cache Patterns](https://redis.io/docs/manual/patterns/)
- [System Design Interview — Caching](https://bytebytego.com/)
- [Guava Cache Explained](https://github.com/google/guava/wiki/CachesExplained)

## Interview Questions

### Q1: How would you prevent a cache stampede?
**Answer**: A cache stampede happens when a hot key expires and many concurrent requests all miss the cache and hit the backend simultaneously. Solutions: (1) **Single-flight / request coalescing**: ensure only one request fetches from the backend for a given key; others wait. Guava's `LoadingCache` does this built-in. In distributed systems, use Redis `SET NX` as a distributed lock. (2) **Probabilistic early expiration**: with 1% probability per request, treat the cached value as expired and refresh it asynchronously before TTL actually expires. (3) **Stale-while-revalidate**: serve the stale value to the client while refreshing in the background. I'd combine approaches: use request coalescing for the hot path and stale-while-revalidate as a fallback.

### Q2: What is a Bloom filter and how is it used in caching?
**Answer**: A Bloom filter is a space-efficient probabilistic data structure for set membership testing. It uses k hash functions and a bit array. It has **zero false negatives** (if it says an element is not in the set, it definitely isn't) but a controllable false positive rate (e.g., 1%). In caching, I'd place a Bloom filter in front of the cache and database for read-heavy workloads with many non-existent keys. If the Bloom filter says a key doesn't exist, I return immediately without checking cache or DB, preventing cache penetration. For 100M keys with 1% false positive rate, it requires ~125 MB of memory — negligible compared to the cache and DB load it prevents.

### Q3: Explain cache-aside, write-through, and write-behind patterns.
**Answer**: **Cache-aside** (lazy loading): on read, check cache → miss → fetch from DB → store in cache. On write, update DB and invalidate cache. Most common pattern. **Write-through**: on write, update cache AND DB synchronously. Reads always hit the cache (if the key exists). Provides strong consistency but adds write latency. **Write-behind** (write-back): on write, update cache immediately, write to DB asynchronously (batched). Best write performance but risks data loss on crash. I'd use cache-aside as the default, write-through for data that must be strongly consistent (e.g., account balance), and write-behind only for high-throughput append-only data where some loss is tolerable (e.g., analytics counters).

### Q4: How do you handle cache invalidation across multiple layers?
**Answer**: With application cache, Redis, and CDN, I invalidate **bottom-up**: (1) update the database, (2) invalidate the Redis key, (3) publish an invalidation event so application instances clear their local caches, (4) purge the CDN via API call. This order is critical — if I purge CDN first but Redis still has old data, new requests will fetch from Redis and re-populate the CDN with stale content. I'd also use versioned cache keys as a safety net: include a data version in the key, so stale entries at any layer become unreachable when the version increments. For the CDN layer, I set short TTLs (5-15 minutes) as a final fallback.

### Q5: What is cache warming and when is it necessary?
**Answer**: Cache warming pre-populates the cache before serving traffic. It's necessary when: (1) **Cold start after deploy**: all cache is empty, and a traffic surge would overwhelm the backend. (2) **Predictable hot data**: leaderboards, featured products, configuration — pre-load these at startup. (3) **Time-sensitive data**: stock prices, scores — background jobs refresh on a schedule. Without warming, the first requests after a restart experience high latency and can cause cascading failures. I'd implement it as a startup hook that loads the top-N most-accessed keys from the database into the cache, and a scheduled job for continuous warming of time-sensitive data. For critical services, I'd also warm the CDN with a traffic replay from production logs.