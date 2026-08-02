# Caching Strategy Design

## What is Caching?

Caching stores frequently accessed data in a **fast-access storage layer** to reduce latency and database load. It's one of the most impactful optimizations in system design.

```
Without Cache:  Client → App → Database (10ms)
With Cache:     Client → App → Cache (0.1ms) ✓ hit
                             → Database (10ms) ✗ miss
```

## Where to Cache?

```
┌─────────────────────────────────────────────────┐
│ Client-Side Cache (Browser, Mobile)             │ ← Fastest
├─────────────────────────────────────────────────┤
│ CDN Cache (Edge Locations)                      │
├─────────────────────────────────────────────────┤
│ Load Balancer Cache (Reverse Proxy)             │
├─────────────────────────────────────────────────┤
│ Application Cache (Redis, Memcached)            │
├─────────────────────────────────────────────────┤
│ Database Cache (Query Cache, Buffer Pool)       │ ← Slowest cache
├─────────────────────────────────────────────────┤
│ Database                                        │
└─────────────────────────────────────────────────┘
```

### Caching Layers

| Layer | Technology | Latency | Use Case |
|-------|-----------|---------|----------|
| Client | Browser cache, localStorage | 0ms | Static assets, API responses |
| CDN | Cloudflare, CloudFront | 5-20ms | Static files, images, videos |
| Application | Redis, Memcached | 0.5-2ms | Session, computed data, DB results |
| Database | Buffer pool, query cache | 2-5ms | Frequent queries |

## Caching Strategies

### 1. Cache-Aside (Lazy Loading)

The most common pattern. Application manages the cache.

```
Read:
1. Check cache → hit? Return cached data
2. Cache miss → Read from DB
3. Store result in cache
4. Return data

Write:
1. Write to DB
2. Invalidate (delete) cache entry
```

```python
def get_user(user_id):
    # 1. Check cache
    cached = redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    
    # 2. Cache miss - read from DB
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)
    
    # 3. Store in cache with TTL
    redis.setex(f"user:{user_id}", 3600, json.dumps(user))
    
    return user

def update_user(user_id, data):
    # 1. Write to DB
    db.execute("UPDATE users SET ... WHERE id = ?", user_id, data)
    
    # 2. Invalidate cache
    redis.delete(f"user:{user_id}")
```

**Pros**: Only caches data that's actually requested, cache failures don't break the system
**Cons**: Cache miss is slow (two round trips), stale data possible

### 2. Write-Through

Write to cache and DB simultaneously.

```
Write:
1. Write to cache
2. Cache writes to DB (synchronously)
3. Return success

Read:
1. Read from cache (always a hit for written data)
```

```python
def update_user(user_id, data):
    # Write to cache, which syncs to DB
    redis.set(f"user:{user_id}", json.dumps(data))
    db.execute("UPDATE users SET ... WHERE id = ?", user_id, data)
    return data

def get_user(user_id):
    # Always read from cache
    return json.loads(redis.get(f"user:{user_id}"))
```

**Pros**: Cache is always fresh, reads are always fast
**Cons**: Write latency (two writes), most written data may never be read

### 3. Write-Behind (Write-Back)

Write to cache immediately, flush to DB asynchronously.

```
Write:
1. Write to cache (fast)
2. Return success immediately
3. Cache asynchronously flushes to DB

Read:
1. Read from cache
```

**Pros**: Very fast writes, can batch DB writes
**Cons**: Risk of data loss if cache crashes before flush, complex implementation

### 4. Read-Through

Cache itself fetches data from DB on miss (cache acts as data source).

```
Read:
1. Application reads from cache
2. On miss, cache fetches from DB
3. Cache stores and returns data
```

**Pros**: Simpler application code, cache is the single data source
**Cons**: Requires cache library support, first read is slow

### Strategy Comparison

| Strategy | Read Speed | Write Speed | Consistency | Complexity | Data Loss Risk |
|----------|-----------|-------------|-------------|------------|----------------|
| Cache-Aside | Fast (hit) | Normal | Eventual | Low | Low |
| Write-Through | Always fast | Slower | Strong | Medium | None |
| Write-Behind | Always fast | Very fast | Eventual | High | Yes |
| Read-Through | Fast (hit) | Normal | Eventual | Medium | Low |

## Cache Invalidation

> "There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

### Invalidation Strategies

#### 1. TTL (Time-To-Live)
```python
redis.setex("user:123", 3600, data)  # Expires in 1 hour
```
- Simple and effective
- Data is stale until TTL expires
- Choose TTL based on staleness tolerance

#### 2. Event-Based Invalidation
```python
# When data changes
def on_user_update(user_id):
    redis.delete(f"user:{user_id}")
    # Or publish event for distributed invalidation
    pubsub.publish("cache:invalidate", f"user:{user_id}")
```
- Immediate invalidation
- Requires event system
- Works across distributed caches

#### 3. Version-Based Invalidation
```python
# Cache key includes version
cache_key = f"user:{user_id}:v{user_version}"
# Old version automatically becomes orphan
```
- No explicit delete needed
- Old entries expire naturally via TTL

### Cache Stampede Problem

When a popular cache entry expires, many requests simultaneously hit the DB.

```
T=0: Cache entry expires
T=0.1: 1000 requests → all miss → all hit DB → DB overload
```

**Solutions**:

| Solution | How | Trade-off |
|----------|-----|-----------|
| **Locking** | First request locks, others wait | Adds latency |
| **Probabilistic early refresh** | Refresh before expiry probabilistically | Complex |
| **Background refresh** | Async refresh before TTL expires | Extra process |
| **Stale-while-revalidate** | Serve stale, refresh async | Brief staleness |

```python
def get_with_lock(key):
    data = redis.get(key)
    if data:
        return json.loads(data)
    
    # Try to acquire lock
    lock_key = f"lock:{key}"
    if redis.set(lock_key, "1", nx=True, ex=5):
        try:
            data = db.query(...)
            redis.setex(key, 3600, json.dumps(data))
            return data
        finally:
            redis.delete(lock_key)
    else:
        # Wait and retry
        time.sleep(0.1)
        return get_with_lock(key)
```

## CDN (Content Delivery Network)

### How CDN Works
```
User (Tokyo) → CDN Edge (Tokyo) → Cache hit? → Return
                                → Cache miss → Origin (US) → Cache → Return
```

### What to Cache at CDN
| Content Type | Cache? | TTL |
|-------------|--------|-----|
| Static assets (JS, CSS, images) | ✅ | Days/weeks |
| API responses (public) | ✅ | Minutes |
| User-specific data | ❌ | — |
| Dynamic content | ❌ | — |

### CDN Invalidation
- **Purge**: Explicitly remove from all edge locations
- **TTL-based**: Wait for expiry
- **Versioned URLs**: `/app.v2.js` instead of `/app.js`

## Cache Eviction Policies

When cache is full, which entries to remove?

| Policy | How | Best For |
|--------|-----|----------|
| **LRU** (Least Recently Used) | Remove least recently accessed | General purpose |
| **LFU** (Least Frequently Used) | Remove least frequently accessed | Stable access patterns |
| **FIFO** (First In First Out) | Remove oldest entry | Simple, time-based |
| **TTL** (Time-To-Live) | Remove expired entries | Time-sensitive data |
| **Random** | Remove random entry | When all entries are equal |

**Redis default**: LRU approximation (allkeys-lru)

## Distributed Caching

### Memcached vs Redis

| Feature | Memcached | Redis |
|---------|-----------|-------|
| Data structures | Key-value only | Strings, lists, sets, hashes, sorted sets |
| Persistence | No | Yes (RDB, AOF) |
| Clustering | Client-side | Built-in (Redis Cluster) |
| Pub/Sub | No | Yes |
| Lua scripting | No | Yes |
| Memory efficiency | Better | Slightly more overhead |
| Use case | Simple caching | Complex data, pub/sub, queues |

### Cache Topologies

#### Single Cache Server
```
[App1] → [Redis] ← [App2]
```
Simple but single point of failure

#### Cache Cluster
```
[App] → [Redis Cluster]
         ├── Node 1 (slots 0-5460)
         ├── Node 2 (slots 5461-10922)
         └── Node 3 (slots 10923-16383)
```
Scales horizontally, data partitioned by hash slots

#### Multi-tier Cache
```
[App] → [Local Cache (L1)] → [Redis (L2)] → [DB]
         Guava/Caffeine        Distributed
```
L1 for ultra-fast access, L2 for shared cache

## Real-World Examples

### Facebook's Memcached Architecture
- Trillions of items cached
- McSqueal for DB replication to cache
- Memcache pools by workload
- Regional caching with cross-region invalidation

### Twitter's Cache Strategy
- Redis for timeline cache
- Memcached for user data
- Cache-aside for most reads
- Write-through for critical data

## Interview Tips

1. **Always mention cache** — It's expected in any HLD discussion
2. **Choose strategy based on read/write ratio** — Read-heavy → cache-aside
3. **Discuss invalidation** — "We'll use TTL of 1 hour + event-based invalidation"
4. **Consider cache stampede** — Mention locking or early refresh
5. **Think about cache size** — What's the working set size?
6. **Don't cache everything** — Some data changes too frequently
7. **Mention specific technology** — "Redis with allkeys-lru eviction"
8. **Discuss failure modes** — "If Redis goes down, we fall back to DB"

## Common Mistakes

- ❌ Caching without considering invalidation strategy
- ❌ Not setting TTL (cache grows forever)
- ❌ Caching user-specific data at CDN
- ❌ Ignoring cache stampede for hot keys
- ❌ Using cache as primary data store (without persistence)
- ❌ Not monitoring cache hit rate

## Cross-References

- [Scalability](./scalability.md) — Caching is key to scaling reads
- [Database Design](./database-design.md) — Cache reduces DB load
- [Consistency Tradeoffs](./consistency-tradeoffs.md) — Caching introduces eventual consistency
- [Monitoring](./monitoring-observability.md) — Monitor cache hit rates
- [LRU Cache LLD](../lld/cache-lld.md) — Implementation details
