# Redis Pub/Sub

Redis Pub/Sub is a message broadcasting primitive built into Redis since version 2.0 (2010). It provides a publish/subscribe pattern where publishers send messages to "channels" and subscribers receive messages from channels they've subscribed to. This page covers the architecture, the message delivery guarantees, the pattern subscription feature, and the production limitations that drove Redis Streams' introduction.

## The Architecture

```text
Publisher 1 → PUBLISH news "Hello" →  ┌─────────────────────┐
                                       │  Redis Server        │
                                       │  - Channel "news"    │
                                       │  - Channel "events"  │
                                       │  - Pattern: news.*    │
                                       └─────────────────────┘
                                                ↓
                              Subscribers receive the message
                              on channels they've SUBSCRIBE'd to.
```

Redis Pub/Sub has no broker-side state other than the list of subscribers per channel. There is no message persistence — a subscriber that's offline when a message is published will miss it.

## The Commands

### SUBSCRIBE / UNSUBSCRIBE

```bash
# Subscribe to one or more channels (blocks the client)
redis-cli
> SUBSCRIBE news events
Reading messages... (press Ctrl-C to quit)
1) "subscribe"
2) "news"
3) (integer) 1
1) "subscribe"
2) "events"
3) (integer) 2

# Now the client is in "subscribe mode" — it only receives SUBSCRIBE/UNSUBSCRIBE
# acks and published messages.

# To unsubscribe from one channel:
> UNSUBSCRIBE news

# To unsubscribe from all:
> UNSUBSCRIBE
```

### PUBLISH

```bash
# Publish a message to the "news" channel
redis-cli PUBLISH news "Breaking: Redis 8.0 released!"
# Returns the number of subscribers that received the message (integer)
```

The return value of PUBLISH is the count of subscribers that received the message. If the count is 0, no one was listening; the message is lost.

### PSUBSCRIBE / PUNSUBSCRIBE

Pattern subscription uses glob patterns to match multiple channels:

```bash
# Subscribe to all channels matching "news.*"
> PSUBSCRIBE news.*
1) "psubscribe"
2) "news.*"
3) (integer) 1

# When a publisher sends to "news.tech":
1) "pmessage"
2) "news.*"            ← the pattern that matched
3) "news.tech"         ← the actual channel name
4) "Hello"             ← the message payload
```

Patterns use Redis's globbing: `*` matches any chars, `?` matches one char, `[abc]` matches a/b/c.

## The Delivery Model

Redis Pub/Sub uses **fire-and-forget** delivery:

1. The publisher sends `PUBLISH channel message` to Redis.
2. Redis iterates over all subscribers of the channel.
3. For each subscriber, Redis writes the message to its connection's output buffer.
4. Redis returns the subscriber count to the publisher.

There is no:
- **Persistence**: messages aren't stored on disk. A subscriber that connects after a publish will miss the message.
- **Acknowledgment**: Redis doesn't track which subscribers received the message.
- **Redelivery**: if a subscriber's TCP connection breaks during delivery, the message is lost.

For a chat application, this means: a user who disconnects and reconnects will miss any messages sent during the disconnection.

## Performance Characteristics

Redis Pub/Sub is very fast:
- Publish throughput: ~100K messages/sec per Redis instance.
- Subscriber fan-out: O(N) where N is the subscriber count (Redis iterates the list).
- Latency: <1 ms per message (in-memory, no disk I/O).

For high-fanout scenarios (10K+ subscribers per channel), Redis's per-subscriber write slows linearly. If a single subscriber's TCP buffer is full, Redis blocks — affecting all subscribers.

## Limitations

1. **No persistence**: subscribers miss messages during disconnection.
2. **No consumer groups**: every subscriber gets every message (no load-balanced distribution).
3. **No retries**: failed delivery means the message is lost.
4. **Blocking subscriber**: while subscribed, the client can only receive SUBSCRIBE-related responses, not other Redis commands.
5. **No backlog**: there's no "last N messages" buffer for new subscribers to read.

These limitations drove the introduction of Redis Streams (5.0, 2017), which adds persistence and consumer groups.

## Production Use Cases

### Real-time chat

```python
# Each user subscribes to their personal channel
redis.subscribe(f"user:{user_id}:messages")

# Sending a message
redis.publish(f"user:{recipient_id}:messages", json.dumps({"from": user_id, "text": "Hello"}))
```

### Live notifications

```python
# Web server publishes notifications
redis.publish("notifications", json.dumps({"user_id": 42, "type": "new_message"}))

# Long-polling clients subscribe and return when a message arrives
def long_poll(user_id):
    pubsub = redis.pubsub()
    pubsub.subscribe(f"notifications:{user_id}")
    for message in pubsub.listen():
        return message["data"]
```

### Distributed cache invalidation

When a write changes cached data, publish an invalidation message:

```python
# On write
redis.set("user:42", new_value)
redis.publish("cache:invalidate", json.dumps({"key": "user:42"}))

# On each app server, a background subscriber listens and clears local cache:
def cache_listener():
    pubsub = redis.pubsub()
    pubsub.psubscribe("cache:invalidate")
    for message in pubsub.listen():
        key = json.loads(message["data"])["key"]
        local_cache.delete(key)
```

This is the standard pattern for cache-coherence across multiple app servers.

## Comparison to Other Pub/Sub Systems

| Aspect | Redis Pub/Sub | Redis Streams | Kafka | RabbitMQ |
|--------|---------------|---------------|-------|----------|
| Persistence | No | Yes | Yes | Optional |
| Consumer groups | No | Yes | Yes | Yes |
| Replay | No | Yes | Yes | No |
| Throughput | 100K/sec | 100K/sec | 100K+/sec | 50K/sec |
| Latency | <1 ms | <1 ms | ~5 ms | ~5 ms |
| Best for | Real-time push, cache invalidation | Durable pub/sub | High-throughput logs | Routing, queue semantics |

Redis Pub/Sub is for ephemeral broadcasts where missing messages is OK. Redis Streams is for durable pub/sub. Kafka is for high-throughput, multi-consumer logs.

## Common Pitfalls

1. **Forgetting that messages are lost on disconnect.** A subscriber that restarts misses messages during the restart. Use Redis Streams if persistence matters.

2. **Forgetting that subscribers can't issue other Redis commands.** A client in `SUBSCRIBE` mode is blocked; only SUBSCRIBE-related commands work. Use a separate connection for other Redis operations.

3. **Forgetting that PUBLISH is fire-and-forget.** The publisher doesn't know if subscribers actually processed the message — only that Redis sent it to their connection's buffer.

4. **Using PSUBSCRIBE with high-cardinality patterns.** `*` matches every channel; with 1K channels and one subscriber per pattern, every publish checks all patterns. Slow.

5. **Forgetting that a slow subscriber blocks Redis.** If one subscriber's TCP buffer fills, Redis blocks on the write — affecting all other subscribers and all other Redis commands.

6. **Confusing Pub/Sub with Redis's `BLPOP`/`BLMOVE` queue commands.** The latter are point-to-point queues (one consumer gets each message); Pub/Sub is broadcast (every subscriber gets every message).

## References

- [Redis Pub/Sub documentation](https://redis.io/docs/interact/pubsub/)
- [Redis SUBSCRIBE command](https://redis.io/commands/subscribe/)
- [Redis PUBLISH command](https://redis.io/commands/publish/)
- [Redis PSUBSCRIBE command](https://redis.io/commands/psubscribe/)
- [Redis Streams (the durable alternative)](https://redis.io/docs/latest/develop/data-types/streams/)
- [Redis Pub/Sub performance benchmarks](https://redis.io/docs/reference/optimization/latency/)
- [LWN: Redis internals (2018)](https://lwn.net/Articles/750830/)
