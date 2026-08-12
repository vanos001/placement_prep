# Redis Patterns & Internals

## Caching Patterns

### Cache-Aside (Lazy Loading)
```
Read:  App → Cache → (miss) → DB → Cache → App
Write: App → DB → Invalidate Cache
```
Most common pattern. App manages cache explicitly.

### Write-Through
```
Write: App → Cache → DB
Read:  App → Cache → (always hit)
```
Cache always has latest data. Higher write latency.

### Write-Back (Write-Behind)
```
Write: App → Cache → (async) → DB
```
Fast writes. Risk of data loss if cache crashes before flushing.

## Eviction Policies

| Policy | Behavior | Use Case |
|---|---|---|
| `noeviction` | Return error on full cache | Critical data, never lose |
| `allkeys-lru` | Evict least recently used | General purpose |
| `volatile-lru` | Evict LRU from keys with TTL | Mixed cache + persistent |
| `allkeys-lfu` | Evict least frequently used | Long-term cache |
| `volatile-ttl` | Evict shortest TTL first | Short-lived cache |

## Persistence

### RDB (Snapshot)
```
save 900 1      # Save if ≥1 key changed in 900 seconds
save 300 10     # Save if ≥10 keys changed in 300 seconds
```
Point-in-time snapshots. Compact. Possible data loss between snapshots.

### AOF (Append-Only File)
```
appendonly yes
appendfsync everysec  # fsync every second
```
Logs every write operation. More durable. Larger files. AOF rewrite for compaction.

### Comparison
| Aspect | RDB | AOF |
|---|---|---|
| Durability | Possible data loss (between snapshots) | Max 1 second loss |
| Recovery | Fast (load snapshot) | Slower (replay log) |
| File size | Compact | Larger (can rewrite) |
| Fork | Yes (blocks briefly on large datasets) | Yes (rewrite) |

## Redis Cluster

```
Client → Cluster (16384 hash slots)
         ├── Node A (slots 0-5460)    [master + replica]
         ├── Node B (slots 5461-10922) [master + replica]
         └── Node C (slots 10923-16383) [master + replica]
```

- Automatic sharding by CRC16(key) % 16384
- Each master has at least one replica
- Automatic failover (Sentinel or Cluster mode)
- Resharding without downtime

## Distributed Locks

```bash
# Acquire lock (SET NX + EX)
SET lock:resource "unique-token" NX EX 30

# Release lock (Lua script for atomicity)
EVAL "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end" 1 lock:resource "unique-token"
```

## Rate Limiting

```bash
# Sliding window with sorted sets
ZADD rate:user:1 <timestamp> <unique-id>
ZREMRANGEBYSCORE rate:user:1 0 <timestamp - window>
ZCARD rate:user:1
# If count > limit → reject
```

## Interview Questions

**Q: What is the difference between Redis and Memcached?**
A: Redis supports rich data structures (lists, sets, sorted sets, hashes, streams), persistence (RDB/AOF), replication, Lua scripting, pub/sub. Memcached is simpler (key-value only), multithreaded, no persistence. Redis is more feature-rich; Memcached is simpler for basic caching.

**Q: How does Redis achieve high performance?**
A: (1) In-memory storage, (2) single-threaded event loop (no locks), (3) efficient data structures (ziplist, intset, skiplist), (4) I/O multiplexing (epoll), (5) pipeline/batch operations. Single-threaded avoids context switching; event loop handles concurrency.

**Q: How do you handle Redis running out of memory?**
A: (1) Set `maxmemory`, (2) configure eviction policy (LRU/LFU), (3) use TTLs on cached keys, (4) shard across cluster, (5) monitor memory usage, (6) compress values, (7) use hashes instead of many small keys (more memory efficient).

## References

- [Redis Documentation](https://redis.io/docs/)
- [Redis Patterns and Best Practices](https://redis.io/docs/management/patterns/)
