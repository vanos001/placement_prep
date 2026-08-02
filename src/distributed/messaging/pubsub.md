# Pub/Sub Patterns

## Overview

Publish/Subscribe (Pub/Sub) is a messaging pattern where **publishers send messages to topics** and **subscribers receive messages from topics they're interested in**. Unlike point-to-point queues, pub/sub enables one-to-many communication — a single message can be delivered to multiple subscribers. This pattern is fundamental to event-driven architectures.

## Core Concepts

```mermaid
graph TD
    subgraph "Pub/Sub System"
        P1[Publisher 1] --> T[Topic]
        P2[Publisher 2] --> T
        T --> S1[Subscriber 1]
        T --> S2[Subscriber 2]
        T --> S3[Subscriber 3]
    end
```

| Concept | Description |
|---------|-------------|
| **Publisher** | Sends messages to a topic |
| **Subscriber** | Receives messages from a topic |
| **Topic** | Named channel for messages |
| **Subscription** | Link between topic and subscriber |
| **Message** | Data payload with optional metadata |

## Pub/Sub vs. Message Queue

```mermaid
graph TD
    subgraph "Message Queue (Point-to-Point)"
        P1[Producer] --> Q[Queue]
        Q --> C1[Consumer 1]
        Q --> C2[Consumer 2]
        Note1["Each message processed by ONE consumer"]
    end
    
    subgraph "Pub/Sub"
        P2[Publisher] --> T[Topic]
        T --> S1[Subscriber 1]
        T --> S2[Subscriber 2]
        T --> S3[Subscriber 3]
        Note2["Each message delivered to ALL subscribers"]
    end
```

| Aspect | Message Queue | Pub/Sub |
|--------|--------------|---------|
| **Delivery** | One consumer per message | All subscribers |
| **Coupling** | Tight (producer knows queue) | Loose (producer doesn't know subscribers) |
| **Scaling** | Add consumers to queue | Add subscribers to topic |
| **Use case** | Task distribution | Event notification |

## Pub/Sub Models

### Topic-Based Pub/Sub

```mermaid
graph LR
    subgraph "Topic: orders"
        P[Order Service] --> T[orders]
        T --> S1[Inventory Service]
        T --> S2[Payment Service]
        T --> S3[Notification Service]
    end
    
    subgraph "Topic: payments"
        P2[Payment Service] --> T2[payments]
        T2 --> S4[Accounting Service]
        T2 --> S5[Fraud Detection]
    end
```

### Content-Based Pub/Sub

```mermaid
graph LR
    P[Publisher] --> M["Message: {type: 'order', amount: 100}"]
    M --> R[Router]
    R -->|"type == 'order'"| S1[Order Handler]
    R -->|"amount > 50"| S2[High-Value Handler]
    R -->|"type == 'payment'"| S3[Payment Handler]
```

## Fan-Out Patterns

### Basic Fan-Out

```mermaid
graph TD
    E[Event: user.registered] --> S1[Email Service]
    E --> S2[Analytics Service]
    E --> S3[Recommendation Service]
    E --> S4[Audit Service]
```

### Fan-Out with Filtering

```mermaid
graph TD
    E[Event: order.created] --> F1[Filter: amount > 100]
    E --> F2[Filter: region == 'US']
    E --> F3[Filter: type == 'premium']
    
    F1 --> S1[High-Value Handler]
    F2 --> S2[US Handler]
    F3 --> S3[Premium Handler]
```

## Subscription Types

### Push Subscription

```mermaid
sequenceDiagram
    participant P as Publisher
    participant T as Topic
    participant S as Subscriber
    
    P->>T: Publish message
    T->>S: Push message (HTTP callback)
    S->>S: Process message
    S-->>T: ACK
```

### Pull Subscription

```mermaid
sequenceDiagram
    participant P as Publisher
    participant T as Topic
    participant S as Subscriber
    
    P->>T: Publish message
    Note over S: Periodically polls
    S->>T: Pull messages
    T-->>S: Return messages
    S->>S: Process messages
    S->>T: ACK
```

## Event-Driven Architecture

```mermaid
graph TD
    subgraph "Event Producers"
        US[User Service] -->|"user.created"| EB[Event Bus]
        OS[Order Service] -->|"order.placed"| EB
        PS[Payment Service] -->|"payment.completed"| EB
    end
    
    subgraph "Event Consumers"
        EB -->|"user.created"| NS[Notification Service]
        EB -->|"order.placed"| IS[Inventory Service]
        EB -->|"payment.completed"| AS[Analytics Service]
        EB -->|"order.placed"| RS[Recommendation Service]
    end
```

## Cloud Pub/Sub Services

### Google Cloud Pub/Sub

```python
from google.cloud import pubsub_v1

# Publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, "my-topic")
future = publisher.publish(topic_path, data=b"Hello", attr="value")

# Subscriber
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, "my-sub")

def callback(message):
    print(f"Received: {message.data}")
    message.ack()

subscriber.subscribe(subscription_path, callback=callback)
```

### Amazon SNS + SQS

```mermaid
graph TD
    P[Publisher] --> SNS[SNS Topic]
    SNS --> SQS1[SQS Queue 1]
    SNS --> SQS2[SQS Queue 2]
    SNS --> Lambda[Lambda Function]
    SQS1 --> C1[Consumer 1]
    SQS2 --> C2[Consumer 2]
```

### Azure Service Bus

```python
from azure.servicebus import ServiceBusClient

# Publish
with ServiceBusClient.from_connection_string(conn_str) as client:
    with client.get_topic_sender(topic_name) as sender:
        sender.send_messages(ServiceBusMessage("Hello"))

# Subscribe
with ServiceBusClient.from_connection_string(conn_str) as client:
    with client.get_subscription_receiver(topic_name, sub_name) as receiver:
        for msg in receiver:
            print(str(msg))
            receiver.complete_message(msg)
```

## Pub/Sub with Message Ordering

```mermaid
graph TD
    subgraph "Ordered Pub/Sub"
        P[Publisher] -->|"Key: user_123"| T[Topic]
        T -->|"Partition by key"| S1[Subscriber 1\n(user_123 messages)]
        T -->|"Partition by key"| S2[Subscriber 2\n(user_456 messages)]
    end
```

## Pub/Sub Patterns in Practice

### Event Sourcing

```mermaid
graph LR
    C[Command] --> ES[Event Store]
    ES --> P[Pub/Sub]
    P --> V1[View 1: Current State]
    P --> V2[View 2: Analytics]
    P --> V3[View 3: Search Index]
```

### CQRS (Command Query Responsibility Segregation)

```mermaid
graph TD
    subgraph "Write Side"
        CMD[Command] --> WDB[Write Database]
        WDB --> E[Event]
    end
    
    subgraph "Read Side"
        E --> P[Pub/Sub]
        P --> RDB1[Read DB 1: Users]
        P --> RDB2[Read DB 2: Analytics]
        P --> RDB3[Read DB 3: Search]
    end
    
    Q[Query] --> RDB1
```

### Saga Pattern

```mermaid
sequenceDiagram
    participant O as Order Service
    participant EB as Event Bus
    participant I as Inventory Service
    participant P as Payment Service
    
    O->>EB: OrderCreated
    EB->>I: OrderCreated
    I->>I: Reserve inventory
    I->>EB: InventoryReserved
    
    EB->>P: InventoryReserved
    P->>P: Process payment
    P->>EB: PaymentCompleted
    
    EB->>O: PaymentCompleted
    O->>O: Complete order
```

## Interview Questions

1. **What is the pub/sub pattern?**
   - Publishers send messages to topics without knowing subscribers. Subscribers receive messages from topics they've subscribed to. This enables one-to-many, decoupled communication.

2. **How does pub/sub differ from message queues?**
   - Pub/sub: one message to all subscribers (fan-out). Message queue: one message to one consumer (point-to-point). Pub/sub is for event notification; queues are for task distribution.

3. **What is event-driven architecture?**
   - Components communicate through events rather than direct calls. When something happens (e.g., order created), an event is published. Interested services subscribe and react independently.

4. **What is the difference between push and pull subscriptions?**
   - Push: the broker sends messages to the subscriber's endpoint (real-time, but subscriber must be available). Pull: the subscriber polls for messages (subscriber controls pace, but adds latency).

5. **How do you handle message ordering in pub/sub?**
   - Use message keys to ensure ordering per key. Messages with the same key go to the same partition/subscriber. Global ordering is expensive and limits throughput.

6. **What is the saga pattern and how does it use pub/sub?**
   - A distributed transaction pattern where each service publishes events after completing its step. Other services subscribe and react. Compensating events handle failures.

## Common Mistakes

- Not handling **subscriber failures** — messages may be lost
- Creating **tight coupling** through pub/sub (subscribers depend on message format)
- Not considering **message ordering** — events may arrive out of order
- Ignoring **idempotency** — subscribers may receive duplicate messages
- Not using **dead letter topics** for failed messages
- Over-using pub/sub — not everything needs event-driven architecture

## Summary

Pub/Sub enables loose, scalable communication between distributed components. Publishers send events to topics; subscribers react independently. This pattern is essential for event-driven architectures, microservices, and real-time systems. Cloud providers offer managed pub/sub services (Google Cloud Pub/Sub, Amazon SNS, Azure Service Bus) that handle scaling and reliability.

## Cross-References

- [Messaging Overview](README.md) — Messaging concepts
- [Message Queues](queues.md) — Point-to-point alternative
- [Kafka](kafka.md) — Distributed pub/sub implementation
- [RabbitMQ](rabbitmq.md) — Exchange-based pub/sub
- [Microservices](../microservices/README.md) — Event-driven microservices
- [Stream Processing](../mapreduce/streaming.md) — Processing pub/sub events

## Cross References

- [Kafka](kafka.md)
- [WebSocket](../../networks/http/websocket.md)
- [Microservices](../microservices/README.md)
