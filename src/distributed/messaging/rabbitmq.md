# RabbitMQ

## Overview

RabbitMQ is an open-source **message broker** that implements the Advanced Message Queuing Protocol (AMQP). Originally developed by Rabbit Technologies in 2007, it's widely used for task queues, microservice communication, and asynchronous processing. Unlike Kafka's log-based model, RabbitMQ is a traditional broker that routes messages through exchanges to queues.

## Architecture

```mermaid
graph TD
    P[Producer] --> E[Exchange]
    E -->|"Route"| Q1[Queue 1]
    E -->|"Route"| Q2[Queue 2]
    E -->|"Route"| Q3[Queue 3]
    Q1 --> C1[Consumer 1]
    Q2 --> C2[Consumer 2]
    Q3 --> C3[Consumer 3]
```

## Core Components

### Exchanges

Exchanges receive messages from producers and route them to queues based on rules:

```mermaid
graph TD
    subgraph "Exchange Types"
        D[Direct Exchange] --> D1["Route by exact routing key"]
        F[Fanout Exchange] --> F1["Broadcast to all bound queues"]
        T[Topic Exchange] --> T1["Route by pattern matching"]
        H[Headers Exchange] --> H1["Route by message headers"]
    end
```

### Direct Exchange

```mermaid
graph LR
    P[Producer] -->|"routing_key=#quot;error#quot;"| E[Direct Exchange]
    E -->|"error"| Q1[Error Queue]
    E -->|"info"| Q2[Info Queue]
    E -->|"warning"| Q3[Warning Queue]
```

### Fanout Exchange

```mermaid
graph LR
    P[Producer] --> E[Fanout Exchange]
    E --> Q1[Queue 1]
    E --> Q2[Queue 2]
    E --> Q3[Queue 3]
    
    Note["All queues receive all messages"]
```

### Topic Exchange

```mermaid
graph LR
    P[Producer] -->|"routing_key=#quot;order.created.us#quot;"| E[Topic Exchange]
    E -->|"order.*"| Q1[Order Queue]
    E -->|"*.created.*"| Q2[Created Queue]
    E -->|"order.#"| Q3[All Orders Queue]
```

**Pattern matching**:
- `*` matches exactly one word
- `#` matches zero or more words

### Headers Exchange

```python
# Route by message headers
channel.basic_publish(
    exchange='headers-exchange',
    routing_key='',  # Ignored for headers exchange
    body=message,
    properties=pika.BasicProperties(
        headers={'format': 'pdf', 'type': 'report'}
    )
)

# Queue binding with headers
channel.queue_bind(
    exchange='headers-exchange',
    queue='pdf-queue',
    arguments={'x-match': 'all', 'format': 'pdf'}
)
```

## Message Flow

```mermaid
sequenceDiagram
    participant P as Producer
    participant E as Exchange
    participant Q as Queue
    participant C as Consumer
    
    P->>E: Publish message (routing_key, properties, body)
    E->>E: Route based on exchange type
    E->>Q: Deliver to matching queue
    Q->>Q: Persist message
    Q->>C: Deliver message
    C->>C: Process message
    C->>Q: ACK (or NACK)
    Q->>Q: Remove message (on ACK)
```

## Acknowledgments

```mermaid
graph TD
    subgraph "Auto ACK"
        A1[Message delivered] --> A2[Immediately removed from queue]
        A2 -.->|"Consumer crashes"| A3[Message lost!]
    end
    
    subgraph "Manual ACK"
        M1[Message delivered] --> M2[Consumer processes]
        M2 -->|"Success"| M3[ACK → Removed]
        M2 -->|"Failure"| M4[NACK → Requeued]
    end
```

### Consumer Acknowledgment Example

```python
def callback(ch, method, properties, body):
    try:
        process_message(body)
        # ACK: message processed successfully
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        # NACK: requeue for retry
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True
        )

channel.basic_consume(queue='tasks', on_message_callback=callback)
```

## Prefetch (QoS)

```python
# Process one message at a time
channel.basic_qos(prefetch_count=1)

# Process up to 10 messages concurrently
channel.basic_qos(prefetch_count=10)
```

```mermaid
graph TD
    subgraph "prefetch_count=1"
        Q1[Queue] -->|"Send 1"| C1[Consumer]
        C1 -->|"ACK"| Q1
        Q1 -->|"Send next"| C1
        Note1["Slow but fair"]
    end
    
    subgraph "prefetch_count=10"
        Q2[Queue] -->|"Send 10"| C2[Consumer]
        Note2["Fast but may overwhelm"]
    end
```

## Dead Letter Exchange (DLX)

```mermaid
graph LR
    P[Producer] --> Q[Main Queue]
    Q -->|"Reject/TTL expired"| DLX[Dead Letter Exchange]
    DLX --> DLQ[Dead Letter Queue]
    DLQ --> D[Debug/Manual Review]
```

```python
# Declare DLX
channel.exchange_declare(exchange='dlx', exchange_type='direct')

# Declare main queue with DLX
channel.queue_declare(
    queue='main-queue',
    arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dlq',
        'x-message-ttl': 60000,  # 60 seconds TTL
        # Note: there is no `x-max-retries` argument in RabbitMQ. To limit retries,
        # track delivery count in the message's `x-death` header (set when a message
        # is dead-lettered) and/or use `x-delivery-limit` (quorum queues only).
        'x-delivery-limit': 3,  # quorum queues only — number of redelivery attempts
    }
)
```

## Clustering and High Availability

```mermaid
graph TD
    subgraph "RabbitMQ Cluster"
        N1[Node 1] <--> N2[Node 2]
        N2 <--> N3[Node 3]
        N3 <--> N1
    end
    
    subgraph "Queue Mirroring"
        Q1["Queue (Master) on Node 1"]
        Q2["Queue (Mirror) on Node 2"]
        Q3["Queue (Mirror) on Node 3"]
    end
```

### Quorum Queues (Recommended)

```mermaid
graph TD
    subgraph "Quorum Queue"
        L["Leader (Node 1)"] --> F1["Follower (Node 2)"]
        L --> F2["Follower (Node 3)"]
    end
    
    P[Producer] --> L
    C[Consumer] --> L
    
    Note["Majority must ACK for durability"]
```

## RabbitMQ vs. Kafka

| Aspect | RabbitMQ | Kafka |
|--------|----------|-------|
| **Model** | Message broker | Distributed log |
| **Routing** | Exchanges + bindings | Topic partitions |
| **Retention** | Until consumed | Time/key-based |
| **Replay** | No | Yes |
| **Throughput** | Moderate (~50K/sec) | Very high (~millions/sec) |
| **Ordering** | Per-queue | Per-partition |
| **Use case** | Task queues, RPC | Event streaming, data pipelines |
| **Protocol** | AMQP, MQTT, STOMP | Custom binary protocol |

## Interview Questions

1. **What is RabbitMQ and how does it differ from Kafka?**
   - RabbitMQ is a traditional message broker using exchanges and queues. Kafka is a distributed commit log. RabbitMQ deletes messages after consumption; Kafka retains them. RabbitMQ is better for task queues; Kafka for event streaming.

2. **Explain the exchange types in RabbitMQ.**
   - Direct: routes by exact routing key. Fanout: broadcasts to all bound queues. Topic: routes by pattern matching (* and # wildcards). Headers: routes by message headers.

3. **How do acknowledgments work in RabbitMQ?**
   - Consumers send ACK after processing. If no ACK within timeout, the message is redelivered. NACK with requeue=True puts the message back in the queue. This ensures at-least-once delivery.

4. **What is a dead letter exchange?**
   - An exchange that receives messages rejected by queues, expired (TTL), or exceeding max length. Used for debugging, monitoring, or reprocessing failed messages.

5. **What are quorum queues in RabbitMQ?**
   - Raft-based replicated queues that provide high availability and data safety. Messages are replicated to a majority of nodes before being acknowledged. Replaces the older mirroring approach.

## Common Mistakes

- Not using **manual acknowledgments** — messages lost on consumer crash
- Setting **prefetch too high** — consumers overwhelmed, messages timeout
- Not configuring **DLX** — poison messages block the queue
- Using **classic mirroring** instead of quorum queues — less reliable
- Not setting **TTL** — queues grow unbounded
- Treating RabbitMQ like Kafka — it's not designed for event replay

## Summary

RabbitMQ is a mature message broker with flexible routing through exchanges. It excels at task queues, request-reply patterns, and microservice communication. The choice between RabbitMQ and Kafka depends on the use case: RabbitMQ for traditional messaging, Kafka for event streaming and data pipelines.

## Cross-References

- [Messaging Overview](README.md) — Messaging concepts
- [Message Queues](queues.md) — General queue patterns
- [Kafka](kafka.md) — Distributed streaming platform
- [Pub/Sub](pubsub.md) — Publish-subscribe patterns
- [Circuit Breakers](../microservices/circuit-breakers.md) — Handling consumer failures
- [API Gateways](../microservices/api-gateways.md) — Message routing
