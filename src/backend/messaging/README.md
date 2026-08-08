# Messaging Systems

Messaging systems enable asynchronous communication between services, decoupling producers from consumers and enabling resilient, scalable architectures.

## In This Section

- [Apache Kafka](./kafka.md) — Distributed event streaming platform
- [RabbitMQ](./rabbitmq.md) — Traditional message broker
- [Redis](./redis.md) — In-memory data structure store
- [NATS](./nats.md) — Lightweight, high-performance messaging

## When to Use Messaging

- **Decoupling** — Services don't need to know about each other
- **Buffering** — Handle traffic spikes without dropping messages
- **Fan-out** — Deliver the same message to multiple consumers
- **Ordering** — Guarantee processing order (Kafka partitions)
- **Durability** — Persist messages for replay and recovery

## Comparison

| Feature | Kafka | RabbitMQ | Redis | NATS |
|---------|-------|----------|-------|------|
| Model | Log | Queue/Exchange | Pub/Sub + Streams | Subject-based |
| Durability | Disk | Memory + Disk | Optional (AOF/RDB) | JetStream |
| Throughput | Very High | Medium | Very High | Very High |
| Ordering | Per-partition | Per-queue | N/A | Per-subject |
| Replay | Yes | No | Streams only | JetStream |
| Latency | Low ms | Low ms | Sub-ms | Sub-ms |
