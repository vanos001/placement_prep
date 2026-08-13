# Redis Interview Questions

**Q: What are the eviction policies in Redis?**
A: `noeviction` (error on full), `allkeys-lru` (evict least recently used), `volatile-lru` (LRU on keys with TTL), `allkeys-lfu` (least frequently used), `volatile-ttl` (shortest TTL first). `allkeys-lru` is the most common for caching.

**Q: What is the difference between RDB and AOF?**
A: RDB = point-in-time snapshots (compact, fast recovery, possible data loss). AOF = logs every write (more durable, max 1s loss with default `everysec` policy — configurable via `appendfsync`; `always` = no loss, `no` = up to ~30s loss; larger files). Can use both together. RDB for backups, AOF for durability.

**Q: How does Redis Sentinel work?**
A: Sentinel monitors Redis master/replica instances. If master is down, Sentinel promotes a replica to master and updates clients. Provides: monitoring, notification, automatic failover. Requires at least 3 Sentinels for quorum.

**Q: What is a Redis pipeline?**
A: Batching multiple commands into a single network round-trip. Instead of send→wait→send→wait, send all commands at once, receive all responses. Reduces network latency significantly (10x-100x for many small commands).

**Q: How do you use Redis as a message broker?**
A: (1) Pub/Sub for real-time fanout (no persistence, fire-and-forget), (2) Lists for reliable queues (LPUSH + BRPOP), (3) Streams for durable messaging with consumer groups (XADD + XREADGROUP). Use Streams for production; Pub/Sub for real-time notifications.

## References

- [Redis Documentation](https://redis.io/docs/)
- [Redis University](https://university.redis.com/)
