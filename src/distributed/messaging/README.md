# Messaging Systems

## Overview

Messaging systems enable **asynchronous communication** between distributed components. Instead of direct calls (synchronous), components exchange messages through a middleware layer. This decouples producers from consumers, enabling scalability, reliability, and flexibility.

## Why Messaging?

```mermaid
graph TD
    subgraph "Synchronous (Direct Call)"
        S1[Service A] -->|"Wait..."| S2[Service B]
        S2 -->|"Response"| S1
        Note1["A is blocked until B responds"]
    end
    
    subgraph "Asynchronous (Message Queue)"
        P[Producer] -->|"Send"| Q[Queue]
        Q -->|"Deliver"| C[Consumer]
        Note2["P continues immediately"]
    end
```

| Benefit | Description |
|---------|-------------|
| **Decoupling** | Producers and consumers are independent |
| **Scalability** | Add consumers to handle load |
| **Reliability** | Messages persist until processed |
| **Buffering** | Handle traffic spikes |
| **Fan-out** | One message to multiple consumers |

## Messaging Patterns

```mermaid
graph TD
    M[Messaging Patterns] --> Q["Point-to-Point (Queue)"]
    M --> PS[Pub/Sub]
    M --> RR[Request-Reply]
    
    Q --> Q1["One producer, one consumer"]
    PS --> PS1["One producer, many consumers"]
    RR --> RR1["Synchronous over async"]
```

### Point-to-Point (Queue)

```mermaid
graph LR
    P1[Producer 1] --> Q[Queue]
    P2[Producer 2] --> Q
    Q --> C1[Consumer 1]
    Q --> C2[Consumer 2]
    
    Note["Each message processed by exactly one consumer"]
```

### Pub/Sub

```mermaid
graph LR
    P[Producer] --> T[Topic]
    T --> C1[Consumer 1]
    T --> C2[Consumer 2]
    T --> C3[Consumer 3]
    
    Note["Each message delivered to all subscribers"]
```

### Request-Reply

```mermaid
sequenceDiagram
    participant C as Client
    participant Q as Request Queue
    participant S as Server
    participant R as Reply Queue
    
    C->>Q: Send request (correlation_id=123)
    Q->>S: Deliver request
    S->>R: Send reply (correlation_id=123)
    R->>C: Deliver reply
```

## Delivery Guarantees

### At-Most-Once

```mermaid
sequenceDiagram
    participant P as Producer
    participant Q as Queue
    participant C as Consumer
    
    P->>Q: Send message
    Q->>C: Deliver
    C->>C: Process (may fail)
    Note over C: No retry if processing fails
    C-->>Q: No ACK needed
```

- Message may be lost if consumer crashes during processing
- Simplest to implement
- Use when: data loss is acceptable (telemetry, logs)

### At-Least-Once

```mermaid
sequenceDiagram
    participant P as Producer
    participant Q as Queue
    participant C as Consumer
    
    P->>Q: Send message
    Q->>C: Deliver
    C->>C: Process
    alt Processing succeeds
        C->>Q: ACK
        Q->>Q: Delete message
    else Processing fails
        Note over C: No ACK sent
        Q->>C: Redeliver
        C->>C: Process again (may duplicate)
        C->>Q: ACK
    end
```

- Messages may be processed multiple times
- Consumer must be **idempotent**
- Use when: duplicates are tolerable or can be handled

### Exactly-Once

```mermaid
sequenceDiagram
    participant P as Producer
    participant Q as Queue
    participant C as Consumer
    
    P->>Q: Send message (idempotent producer)
    Q->>C: Deliver (with dedup info)
    C->>C: Process
    C->>Q: ACK (with transaction)
    Q->>Q: Mark processed (idempotent)
    
    Note over P,Q: No duplicates regardless of failures
```

- Messages processed exactly once
- Hardest to implement
- Requires coordination between producer, queue, and consumer
- Use when: financial transactions, order processing

### Comparison

| Guarantee | Duplicates | Data Loss | Complexity | Use Case |
|-----------|-----------|-----------|------------|----------|
| **At-most-once** | No | Possible | Low | Telemetry |
| **At-least-once** | Possible | No | Medium | Logs, events |
| **Exactly-once** | No | No | High | Financial |

## Message Ordering

```mermaid
graph TD
    subgraph "Ordered Queue"
        M1["Message 1"] --> M2["Message 2"]
        M2 --> M3["Message 3"]
        Note1["Processed in order"]
    end
    
    subgraph "Partitioned Ordering"
        P1["Partition 1: M1→M2→M3"]
        P2["Partition 2: M4→M5→M6"]
        Note2["Ordered within partition"]
    end
```

| Ordering | Description | Trade-off |
|----------|-------------|-----------|
| **Global** | All messages in order | Low throughput |
| **Partition** | Ordered within partition | High throughput |
| **None** | No ordering guarantee | Highest throughput |

## Dead Letter Queues

Messages that can't be processed are moved to a dead letter queue (DLQ):

```mermaid
graph LR
    P[Producer] --> Q[Main Queue]
    Q --> C[Consumer]
    C -->|Processing fails\nafter N retries| DLQ[Dead Letter Queue]
    DLQ --> D[Debug/Manual Review]
```

## Message Priority

```mermaid
graph TD
    subgraph "Priority Queue"
        H["High Priority"] --> C[Consumer]
        M["Medium Priority"] --> C
        L["Low Priority"] --> C
    end
```

## Interview Questions

1. **What are the main messaging patterns?**
   - Point-to-point (queue): one consumer per message. Pub/sub: all subscribers get each message. Request-reply: synchronous communication over async messaging.

2. **Explain the delivery guarantees.**
   - At-most-once: fire-and-forget, may lose messages. At-least-once: retry until ACK, may duplicate. Exactly-once: processed exactly once (hardest, requires coordination).

3. **When would you use a message queue vs. direct API calls?**
   - Queue: when you need decoupling, buffering, async processing, or fan-out. Direct calls: when you need immediate response, simple request-reply.

4. **What is a dead letter queue?**
   - A queue for messages that can't be processed after multiple retries. Used for debugging, manual review, or reprocessing.

5. **How do you handle message ordering?**
   - Global ordering: single partition (limited throughput). Partition ordering: messages with same key go to same partition (good balance). No ordering: highest throughput.

6. **What is idempotency and why is it important for messaging?**
   - An operation is idempotent if applying it multiple times has the same effect as once. Important because at-least-once delivery may process messages multiple times.

## Common Mistakes

- Not handling **duplicate messages** — assume at-least-once delivery
- Ignoring **message ordering** requirements
- Not using **dead letter queues** — poison messages block the queue
- Making consumers **stateful** — makes scaling and recovery harder
- Not setting **message TTL** — queues grow unbounded
- Forgetting about **backpressure** — fast producers overwhelm slow consumers

## Summary

Messaging systems enable asynchronous, decoupled communication in distributed systems. The choice between queues and pub/sub depends on whether messages should be processed once or by many. Delivery guarantees (at-most-once, at-least-once, exactly-once) trade off between simplicity and reliability. Proper handling of ordering, dead letters, and idempotency is essential for robust systems.

## Cross-References

- [Message Queues](queues.md) — Queue implementations and reliability
- [Apache Kafka](kafka.md) — Distributed streaming platform
- [RabbitMQ](rabbitmq.md) — Traditional message broker
- [Pub/Sub Patterns](pubsub.md) — Publish-subscribe patterns
- [Stream Processing](../mapreduce/streaming.md) — Processing message streams
- [Circuit Breakers](../microservices/circuit-breakers.md) — Handling consumer failures
