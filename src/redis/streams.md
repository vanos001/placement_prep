# Redis Streams

Redis Streams are a durable, append-only log data structure introduced in Redis 5.0 (2017). They address the persistence and consumer-group limitations of Redis Pub/Sub by providing:
- Persistent messages (stored on disk via AOF/RDB).
- Consumer groups (load-balanced consumption across multiple consumers).
- Message IDs and acknowledgment (at-least-once delivery).
- Backlog replay (new consumers can read old messages).

This page covers the data model, the consumer group protocol, the comparison to Kafka, and the production use cases.

## The Data Model

A Redis Stream is an append-only log of entries. Each entry has:

- **ID**: a monotonic timestamp-based ID like `1692616800000-0` (milliseconds-sequence).
- **Fields**: a list of key-value pairs (like a Hash):
  ```text
  1692616800000-0
    user_id: 42
    event: login
    ip: 10.0.0.1
  ```

```bash
# Add an entry to the "events" stream
redis-cli XADD events '*' user_id 42 event login ip 10.0.0.1
# Returns the auto-generated ID, e.g., "1692616800000-0"

# The '*' tells Redis to auto-generate the ID based on the current time.

# Read entries from the beginning
redis-cli XRANGE events - +
# Returns all entries with their IDs and fields.
```

## Commands

### XADD

```bash
# Add an entry
XADD events '*' user_id 42 event login

# Add with explicit ID (must be greater than the last)
XADD events 1692616800000-1 user_id 42 event login

# Add with a maximum length (trims old entries to keep the stream bounded)
XADD events MAXLEN ~ 1000 '*' user_id 42 event login
# The ~ means approximate trimming (cheaper).
```

### XREAD

```bash
# Read from the beginning (one read, not blocking)
XREAD COUNT 10 STREAMS events 0

# Read from the latest (block until new entries arrive)
XREAD BLOCK 0 STREAMS events $
# The $ means "only entries added after this command".
# BLOCK 0 means block forever.
```

### XLEN

```bash
# Count entries
XLEN events
# Returns the count, e.g., (integer) 1234
```

### XRANGE / XREVRANGE

```bash
# Read entries with ID between [a, b]
XRANGE events 1692616800000-0 1692616900000-0

# Read in reverse (newest first)
XREVRANGE events + - COUNT 10
```

### XTRIM

```bash
# Trim to a maximum length (in-place)
XTRIM events MAXLEN ~ 1000

# Trim by time (entries older than 24 hours)
XTRIM events MINID = 1692530400000
```

## Consumer Groups

A consumer group is a logical group of consumers that share a stream's entries. Each entry is delivered to exactly one consumer in the group.

```bash
# Create a consumer group for the "events" stream
# Start reading from the beginning ('0') or the latest ('$')
XGROUP CREATE events mygroup 0

# A consumer reads new (unprocessed) messages
XREADGROUP GROUP mygroup consumer-1 COUNT 10 STREAMS events >
# The '>' means "messages never delivered to any consumer in this group".

# After processing, the consumer acknowledges
XACK events mygroup 1692616800000-0
# Returns 1 if acknowledged, 0 if the message wasn't pending.

# List pending (unacked) messages
XPENDING events mygroup
# Returns: (total pending, smallest ID, largest ID, [consumer pending counts])

# Re-claim messages that have been pending for too long (consumer crashed)
XAUTOCLAIM events mygroup consumer-2 60000 0
# Claims messages pending for >60 seconds.
```

The consumer group protocol:
1. Consumer reads with `>` — gets new (unprocessed) messages.
2. Consumer processes the message.
3. Consumer acks with `XACK`.
4. If the consumer crashes before acking, the message stays "pending".
5. Another consumer (or the same on restart) uses `XAUTOCLAIM` or `XCLAIM` to take ownership of pending messages.

This gives **at-least-once** delivery: messages are never lost, but may be delivered twice (if the consumer crashes mid-processing).

## Persistence

Streams are persisted via Redis's standard mechanisms:
- **RDB**: periodic snapshot. On restart, the stream is restored to the last snapshot.
- **AOF**: every XADD is appended to the AOF log. On restart, the AOF is replayed.

For exactly-once semantics (no duplicates), Redis Streams doesn't directly support it — the application must deduplicate via ID tracking. Redis's `XACK` is what marks a message as processed; the application must handle duplicates from at-least-once delivery.

## Performance

Redis Streams performance:
- XADD throughput: ~100K entries/sec per Redis instance.
- XREAD latency: ~0.1 ms (no disk I/O for reads from memory).
- AOF fsync: every write is fsync'd, so throughput is bounded by disk I/O (~10K/sec on NVMe SSD).
- Memory: ~100 bytes per entry (ID + fields, small entries).

For higher throughput (1M+/sec), use Kafka. Redis Streams is for moderate-throughput, low-latency pub/sub with persistence.

## Production Use Cases

### Event Sourcing

```python
# Append an event
redis.xadd('orders', {'order_id': 123, 'event': 'created', 'customer': 'alice'})

# Replay events from the beginning
events = redis.xrange('orders', '-', '+')
for event_id, fields in events:
    apply_event(fields)
```

Streams are an event sourcing store — the source of truth is the log, not the current state.

### Task Queue

```python
# Producer adds tasks
redis.xadd('tasks', {'task': 'send_email', 'recipient': 'alice@example.com'})

# Consumer group processes tasks
while True:
    messages = redis.xreadgroup('mygroup', 'consumer-1', {'tasks': '>'}, count=10, block=5000)
    for message in messages:
        process_task(message[1]['task'])
        redis.xack('tasks', 'mygroup', message[0])
```

This is the standard pattern for a Redis-based task queue (an alternative to Celery, Sidekiq, etc.).

### Real-time Analytics

```python
# Each user event is added to a per-user stream
redis.xadd(f'events:user:{user_id}', {'event': 'login', 'timestamp': now()})

# Aggregation: count logins per user in the last hour
stream = f'events:user:{user_id}'
messages = redis.xrange(stream, start='-', count=10000)
logins_last_hour = sum(1 for _, m in messages if m['event'] == 'login' and int(m['timestamp']) > now() - 3600)
```

### Live Notifications with Persistence

```python
# User subscribes to notifications stream
# (Server-side: each user has a stream; the user's client reads from it)
messages = redis.xread({f'notifications:{user_id}': '$'}, block=30000)
for message in messages:
    send_to_client(message)
    redis.xack(f'notifications:{user_id}', 'users', message[0])
```

Unlike Pub/Sub (where disconnect = missed messages), Streams lets the user reconnect and read all unread messages.

## Comparison to Kafka

| Aspect | Redis Streams | Kafka |
|--------|---------------|-------|
| Persistence | Yes (AOF/RDB) | Yes (log on disk) |
| Throughput | 100K/sec | 1M+/sec |
| Latency | <1 ms | ~5 ms |
| Consumer groups | Yes | Yes |
| Message ordering | Per-stream (single Redis instance) | Per-partition |
| Replay | Yes (XRANGE) | Yes (seek to offset) |
| Multi-broker replication | No (Redis Cluster shards streams) | Yes |
| Best for | Low-latency, moderate-throughput | High-throughput logs |

Redis Streams are simpler than Kafka (no brokers, no ZooKeeper, no consumer offset management). For small-to-medium workloads, Redis Streams is often sufficient.

## Common Pitfalls

1. **Forgetting that streams can grow unboundedly.** Without XTRIM, the stream grows forever. Use `MAXLEN ~ N` on XADD for bounded streams.

2. **Forgetting that messages are at-least-once, not exactly-once.** A consumer that crashes after processing but before XACK will re-process the message on restart. Idempotency is the application's responsibility.

3. **Forgetting that XREADGROUP with `>` only returns new messages.** To re-process pending (unacked) messages, use `XPENDING` + `XCLAIM` or `XAUTOCLAIM`.

4. **Forgetting that the consumer group's "last delivered ID" is updated only on XREADGROUP with `>`.** Other reads (XRANGE, XREAD) don't update the group's position.

5. **Forgetting that Redis Cluster shards streams.** A stream's key (the stream name) hashes to a slot. All operations on a stream must go to the slot's owner. Use hash tags (`events:{user_id}`) to keep related streams on the same slot.

6. **Forgetting that XADD with `MAXLEN ~ N` is approximate.** The actual length may be up to a few percent more than N. Use `MAXLEN = N` for exact trimming (slower).

## References

- [Redis Streams documentation](https://redis.io/docs/latest/develop/data-types/streams/)
- [Redis XADD command](https://redis.io/commands/xadd/)
- [Redis XREADGROUP command](https://redis.io/commands/xreadgroup/)
- [Redis XPENDING command](https://redis.io/commands/xpending/)
- Salvatore Sanfilippo, "[Redis Streams: 5.0 release notes](https://redis.io/docs/about/releases/)"""
- [Redis Streams vs Kafka (Redis blog)](https://redis.com/blog/redis-streams-vs-apache-kafka/)
- [LWN: Redis Streams (2018)](https://lwn.net/Articles/750830/)
