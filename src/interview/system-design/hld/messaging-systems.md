# Messaging and Async Processing

## Why Async Processing?

Synchronous processing blocks the caller until completion. Async processing decouples producers and consumers, improving responsiveness, reliability, and scalability.

```
Synchronous:
Client → App → Process → DB → Response (client waits 5s)

Asynchronous:
Client → App → Queue → Response (instant)
                ↓
           Worker → Process → DB (takes 5s, but client doesn't wait)
```

## Message Queues

### What is a Message Queue?
A buffer that stores messages between producers and consumers.

```
[Producer] → ┌─────────────────┐ → [Consumer 1]
              │   Message Queue │ → [Consumer 2]
              │  ┌───┬───┬───┐ │ → [Consumer 3]
              │  │ M1│ M2│ M3│ │
              │  └───┴───┴───┘ │
              └─────────────────┘
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Producer** | Sends messages to queue |
| **Consumer** | Reads and processes messages |
| **Queue** | Buffer that stores messages |
| **Message** | Unit of data (JSON, Protobuf, etc.) |
| **ACK** | Acknowledgment that message was processed |
| **DLQ** | Dead Letter Queue for failed messages |
| **TTL** | Time-to-live for messages |

### Popular Message Queue Technologies

| Technology | Type | Throughput | Ordering | Use Case |
|-----------|------|-----------|----------|----------|
| **RabbitMQ** | Traditional MQ | Medium | Per-queue | Task queues, RPC |
| **Apache Kafka** | Distributed log | Very high | Per-partition | Event streaming, logs |
| **Amazon SQS** | Managed queue | High | Best-effort | Simple async tasks |
| **Redis Streams** | Log-based | High | Per-stream | Lightweight streaming |
| **Apache Pulsar** | Multi-tenant | Very high | Per-partition | Multi-tenant streaming |
| **ZeroMQ** | Library (no broker) | Extremely high | N/A | Low-latency, embedded |

### RabbitMQ vs Kafka

| Feature | RabbitMQ | Kafka |
|---------|----------|-------|
| Model | Push-based | Pull-based |
| Message retention | Until consumed | Configurable (days/forever) |
| Ordering | Per-queue | Per-partition |
| Consumer model | Competing consumers | Consumer groups |
| Throughput | ~50K msg/sec | Millions msg/sec |
| Replay | No | Yes (offset-based) |
| Best for | Task queues, RPC | Event streaming, logs |

```
RabbitMQ:
Producer → Exchange → Queue → Consumer (message deleted after ACK)

Kafka:
Producer → Topic → Partition → Consumer Group (message retained)
              └── Partition 2 → Consumer 2
```

## Pub/Sub (Publish-Subscribe)

### How Pub/Sub Works
```
                    ┌──────────────┐
[Publisher A] ────→│              │──→ [Subscriber 1]
                   │  Pub/Sub    │──→ [Subscriber 2]
[Publisher B] ────→│  Topic      │──→ [Subscriber 3]
                   └──────────────┘
```

- Publishers send messages to a **topic**
- All subscribers to that topic receive the message
- Publishers don't know about subscribers (decoupling)

### Queue vs Pub/Sub

| Aspect | Queue | Pub/Sub |
|--------|-------|---------|
| Consumers | One consumer per message | All subscribers get copy |
| Pattern | Point-to-point | Broadcast |
| Use case | Task distribution | Event notification |
| Example | Process one order | Notify all services of order event |

### When to Use Pub/Sub

- **Event notifications**: "User signed up" → notify email, analytics, CRM
- **Real-time updates**: Chat messages, live feeds
- **Fan-out**: Distribute work to multiple consumers
- **Microservices communication**: Decoupled service-to-service

## Event-Driven Architecture

### What is Event-Driven?
Components communicate through events rather than direct calls.

```
Traditional (Request-Response):
App → Order Service → Payment Service → Inventory Service
         (waits)          (waits)           (returns)

Event-Driven:
App → Order Service → emits "OrderCreated" event
                           ↓
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Payment Service  Inventory   Notification
        (processes)      Service     Service
                         (processes) (notifies)
```

### Event Sourcing

Store all state changes as a sequence of events.

```
Traditional (State Storage):
Account: { balance: 100 }

Event Sourcing:
Events: [
  { type: "AccountCreated", amount: 0 },
  { type: "Deposit", amount: 150 },
  { type: "Withdrawal", amount: 50 }
]
Current state: replay events → balance: 100
```

**Benefits**:
- Complete audit trail
- Can reconstruct any point-in-time state
- Events are immutable
- Easy to add new projections/read models

**Drawbacks**:
- Complex to implement
- Event schema evolution is hard
- Queries require read models (CQRS)

### CQRS (Command Query Responsibility Segregation)

Separate write model (commands) from read model (queries).

```
Commands (Write) → Event Store → Event Handlers → Read DB (optimized for queries)
                                                         ↓
Queries (Read) → Read DB ← ──────────────────────────────┘
```

## Backpressure

When consumers can't keep up with producers.

```
Producer: 10,000 msg/sec
Consumer: 1,000 msg/sec (max)
Queue: GROWING → memory issues → crash
```

### Backpressure Strategies

| Strategy | How | Trade-off |
|----------|-----|-----------|
| **Queue size limit** | Reject when full | Messages lost |
| **Rate limiting** | Throttle producer | Slower ingestion |
| **Buffering** | Spill to disk when full | Disk I/O overhead |
| **Load shedding** | Drop low-priority messages | Quality of service |
| **Scaling consumers** | Auto-scale based on lag | Cost, complexity |

### Consumer Lag Monitoring

```
Producer offset: 1,000,000
Consumer offset: 995,000
Lag: 5,000 messages → Consumer is behind
```

## Message Delivery Guarantees

### At-Most-Once
```
Producer → Queue → Consumer (ACK after receive, may not process)
```
- Messages may be lost
- No duplicates
- Fast, simple
- Use case: Logging, metrics

### At-Least-Once
```
Producer → Queue → Consumer → Process → ACK
                                  ↓ (fails before ACK)
                             Re-delivered → Process again
```
- Messages never lost
- May be processed multiple times (idempotent processing needed)
- Most common choice
- Use case: Order processing, notifications

### Exactly-Once
```
Producer → Queue → Consumer → Process → Dedup → ACK
```
- Never lost, never duplicated
- Hardest to achieve
- Requires idempotency + deduplication
- Use case: Financial transactions

| Guarantee | Lost Messages | Duplicates | Complexity |
|-----------|--------------|------------|------------|
| At-most-once | Possible | No | Low |
| At-least-once | No | Possible | Medium |
| Exactly-once | No | No | High |

## Message Queue Patterns

### Dead Letter Queue (DLQ)
```
Main Queue → Consumer (fails 3 times) → DLQ
                                         ↓
                                    Manual review / Alert
```

### Priority Queue
```
┌─────────────────────────┐
│     Priority Queue      │
│ ┌───┐ ┌───┐ ┌───┐     │
│ │ P1│ │ P2│ │ P2│     │
│ │   │ │   │ │   │     │
│ └───┘ └───┘ └───┘     │
└─────────────────────────┘
P1 (high priority) processed first
```

### Delayed Queue
```
Producer → Delay Queue (wait 5 min) → Main Queue → Consumer
```

### Request-Reply (RPC over Queue)
```
Client → Request Queue → Server
Client ← Reply Queue ← Server
```

## Real-World Examples

### Uber's Messaging Architecture
- Kafka for event streaming (ride events, location updates)
- Real-time processing for matching drivers and riders
- Event sourcing for ride state machine

### Netflix's Event Processing
- Kafka for data pipeline (billions of events/day)
- Apache Flink for real-time processing
- Event-driven microservices

### LinkedIn's Kafka
- Originally built at LinkedIn
- Handles 7+ trillion messages/day
- Powers activity feeds, metrics, logging

## Interview Tips

1. **Identify async opportunities** — "Sending email doesn't need to block the response"
2. **Choose the right technology** — "Kafka for event streaming, SQS for simple tasks"
3. **Discuss delivery guarantees** — "At-least-once with idempotent processing"
4. **Mention DLQ** — "Failed messages go to DLQ for investigation"
5. **Consider backpressure** — "What happens if consumers can't keep up?"
6. **Think about ordering** — "Do we need ordered processing? Per-partition ordering in Kafka"
7. **Discuss idempotency** — "Workers must be idempotent since messages may be delivered twice"
8. **Monitor consumer lag** — "Alert if lag exceeds 10K messages"

## Common Mistakes

- ❌ Using sync processing for everything
- ❌ Not handling message failures (no DLQ)
- ❌ Ignoring ordering requirements
- ❌ Not making consumers idempotent
- ❌ Over-engineering with Kafka when SQS would suffice
- ❌ Not monitoring consumer lag

## Cross-References

- [Scalability](./scalability.md) — Async processing enables horizontal scaling
- [Availability](./availability.md) — Queues improve fault tolerance
- [Consistency Tradeoffs](./consistency-tradeoffs.md) — Eventual consistency in async systems
- [Monitoring](./monitoring-observability.md) — Monitor queue depth, consumer lag
- [Notification Service LLD](../lld/notification-service.md) — Implementation example
