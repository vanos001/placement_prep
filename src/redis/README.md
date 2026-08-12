# Redis Overview

## Data Structures

| Type | Use Case | Example |
|---|---|---|
| **String** | Cache, counter, session | `SET user:1 '{"name":"Alice"}'` |
| **List** | Queue, recent items | `LPUSH queue task1` |
| **Set** | Tags, unique items | `SADD tags python web` |
| **Sorted Set** | Leaderboard, ranking | `ZADD leaderboard 100 alice` |
| **Hash** | Object fields | `HSET user:1 name Alice age 30` |
| **Stream** | Event log, messaging | `XADD events * type click page /home` |
| **HyperLogLog** | Cardinality estimation | `PFADD visitors user1 user2` |
| **Bitmap** | Feature flags, bitfields | `SETBIT flags:1 0 1` |

## Key Commands

```bash
# Strings
SET key value [EX 3600]     # Set with TTL
GET key
INCR counter                # Atomic increment
MGET key1 key2              # Multi-get

# Lists
LPUSH queue item            # Push to head
RPOP queue                  # Pop from tail (queue behavior)
LRANGE queue 0 -1           # Get all

# Sets
SADD myset member1
SISMEMBER myset member1
SINTER set1 set2            # Intersection
SUNION set1 set2            # Union

# Sorted Sets
ZADD leaderboard 100 alice
ZRANGE leaderboard 0 -1 WITHSCORES
ZRANK leaderboard alice     # Position

# Hashes
HSET user:1 name Alice age 30
HGET user:1 name
HGETALL user:1

# Streams
XADD events * type click page /home
XREAD COUNT 10 STREAMS events 0
```

## References

- [Redis Documentation](https://redis.io/docs/)
- [Redis University](https://university.redis.com/)
