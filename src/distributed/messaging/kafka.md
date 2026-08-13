# Apache Kafka

## Overview

Apache Kafka is a **distributed streaming platform** originally developed at LinkedIn in 2010. It functions as a distributed commit log, providing durable, high-throughput, fault-tolerant messaging. Kafka is used for real-time data pipelines, event sourcing, log aggregation, and stream processing. It's the backbone of many modern data architectures.

## Architecture

```mermaid
graph TD
    subgraph "Kafka Cluster"
        B1[Broker 1] --> Z[ZooKeeper/KRaft]
        B2[Broker 2] --> Z
        B3[Broker 3] --> Z
    end
    
    P[Producers] --> B1
    P --> B2
    P --> B3
    
    B1 --> C[Consumers]
    B2 --> C
    B3 --> C
```

## Core Concepts

### Topics and Partitions

```mermaid
graph TD
    subgraph "Topic: user-events"
        subgraph "Partition 0"
            M0_0["Msg 0 (offset 0)"]
            M0_1["Msg 1 (offset 1)"]
            M0_2["Msg 2 (offset 2)"]
        end
        subgraph "Partition 1"
            M1_0["Msg 0 (offset 0)"]
            M1_1["Msg 1 (offset 1)"]
        end
        subgraph "Partition 2"
            M2_0["Msg 0 (offset 0)"]
            M2_1["Msg 1 (offset 1)"]
            M2_2["Msg 2 (offset 2)"]
            M2_3["Msg 3 (offset 3)"]
        end
    end
```

| Concept | Description |
|---------|-------------|
| **Topic** | Named stream of records (like a table) |
| **Partition** | Ordered, immutable sequence of records |
| **Offset** | Unique ID for each record within a partition |
| **Broker** | Server that stores partitions |
| **Replica** | Copy of a partition for fault tolerance |
| **Leader** | Replica that handles reads/writes |
| **Follower** | Replica that replicates from leader |

### Partition Assignment

```python
# Key-based partitioning (same key → same partition)
partition = hash(key) % num_partitions

# No key → round-robin
partition = next_partition_round_robin()
```

```mermaid
graph LR
    K1["Key: user_123"] --> P0["hash('user_123') % 3 = 0"]
    K2["Key: user_456"] --> P1["hash('user_456') % 3 = 1"]
    K3["Key: user_789"] --> P2["hash('user_789') % 3 = 2"]
    K1 --> P0
    K2 --> P1
    K3 --> P2
```

## Replication

```mermaid
graph TD
    subgraph "Topic Partition 0 (replication-factor=3)"
        L["Leader (Broker 1)"] --> F1["Follower (Broker 2)"]
        L --> F2["Follower (Broker 3)"]
    end
    
    P[Producer] -->|Write| L
    C[Consumer] -->|Read| L
```

### In-Sync Replicas (ISR)

```mermaid
graph TD
    subgraph "ISR = {Broker 1, Broker 2, Broker 3}"
        B1["Broker 1 (Leader)"] --> B2[Broker 2]
        B1 --> B3[Broker 3]
    end
    
    B2 -.->|Falls behind| B4[Out of ISR]
    B2 -->|"Catches up"| B2
```

| Config | Description |
|--------|-------------|
| `replication.factor=3` | 3 copies of each partition |
| `min.insync.replicas=2` | At least 2 replicas must ACK |
| `acks=all` | Producer waits for all ISR to ACK |

## Producers

```mermaid
graph LR
    P[Producer] --> B[Batching]
    B --> S[Serialization]
    S --> PA[Partitioner]
    PA --> Broker[Broker]
    
    Broker -->|ACK| P
```

### Producer Configuration

```python
producer = KafkaProducer(
    bootstrap_servers=['broker1:9092', 'broker2:9092'],
    
    # Durability
    acks='all',                    # Wait for all ISR
    retries=3,                     # Retry on failure
    enable_idempotence=True,       # Exactly-once producer
    
    # Performance
    batch_size=16384,              # Batch size in bytes
    linger_ms=10,                  # Wait time for batching
    compression_type='lz4',        # Compression
    
    # Ordering
    max_in_flight_requests_per_connection=5  # With idempotence, order preserved
)
```

### Delivery Guarantees

```mermaid
graph TD
    subgraph "acks=0"
        A0[Fire and forget]
        A0 --> L0[May lose messages]
    end
    
    subgraph "acks=1"
        A1[Leader ACK only]
        A1 --> L1[May lose if leader fails]
    end
    
    subgraph "acks=all"
        A2[All ISR ACK]
        A2 --> S2[Safest]
    end
```

## Consumer Groups

```mermaid
graph TD
    subgraph "Consumer Group: analytics"
        C1[Consumer 1] --> P0[Partition 0]
        C2[Consumer 2] --> P1[Partition 1]
        C3[Consumer 3] --> P2[Partition 2]
    end
    
    subgraph "Consumer Group: monitoring"
        C4[Consumer 4] --> P0
        C5[Consumer 5] --> P1
        C6[Consumer 6] --> P2
    end
```

### Consumer Group Rules

1. Each partition is consumed by **exactly one consumer** in a group
2. A consumer can consume **multiple partitions**
3. If consumers > partitions, some consumers are idle
4. Multiple groups can consume the same topic independently

### Consumer Rebalancing

```mermaid
sequenceDiagram
    participant C1 as Consumer 1
    participant C2 as Consumer 2
    participant C3 as Consumer 3 (joins)
    participant B as Broker
    
    Note over C1,C2: Initial: C1→P0, C2→P1
    C3->>B: Join group
    B->>B: Rebalance
    B->>C1: Assign P0
    B->>C2: Assign P1
    B->>C3: Assign P2
    
    Note over C1,C3: After: C1→P0, C2→P1, C3→P2
```

## Offset Management

```mermaid
graph TD
    subgraph "Partition 0"
        O0[offset 0]
        O1[offset 1]
        O2[offset 2]
        O3[offset 3]
        O4[offset 4]
    end
    
    C[Consumer] -->|"committed offset = 2"| O2
    Note["Consumer will read from offset 3 next"]
```

### Offset Commit Strategies

| Strategy | Description | Trade-off |
|----------|-------------|-----------|
| **Auto-commit** | Commit periodically | May lose/duplicate |
| **Manual commit** | Commit after processing | At-least-once |
| **Transactional** | Commit with processing | Exactly-once |

## Exactly-Once Semantics

```mermaid
sequenceDiagram
    participant P as Producer
    participant B as Broker
    participant C as Consumer
    
    Note over P,C: Idempotent Producer
    P->>B: Send (producer_id=PID, seq=0)
    B->>B: Dedup check
    B-->>P: ACK
    P->>B: Send (producer_id=PID, seq=1)
    B->>B: Dedup check
    B-->>P: ACK
    
    Note over P,C: Transactional Consumer
    C->>B: Read offset 0-2
    C->>C: Process
    C->>B: Commit transaction (offset 3 + output)
    B->>B: Atomic commit
```

## Log Compaction

```mermaid
graph TD
    subgraph "Before Compaction"
        K1["Key A: value 1 (offset 0)"]
        K2["Key B: value 1 (offset 1)"]
        K3["Key A: value 2 (offset 2)"]
        K4["Key B: value 2 (offset 3)"]
        K5["Key A: value 3 (offset 4)"]
    end
    
    subgraph "After Compaction"
        K3c["Key A: value 3 (offset 4)"]
        K4c["Key B: value 2 (offset 3)"]
    end
```

Log compaction retains only the **latest value for each key**, useful for changelogs and event sourcing.

## Kafka Architecture Deep Dive

### Broker and Cluster

A Kafka cluster consists of one or more **brokers** (servers). Each broker stores a subset of partitions:

```mermaid
graph TD
    subgraph "Kafka Cluster (3 Brokers)"
        B1[Broker 1<br/>id=1] --> P0_1["Partition 0 (Leader)"]
        B1 --> P1_2["Partition 1 (Follower)"]
        B1 --> P2_3["Partition 2 (Follower)"]

        B2[Broker 2<br/>id=2] --> P0_2["Partition 0 (Follower)"]
        B2 --> P1_1["Partition 1 (Leader)"]
        B2 --> P2_2["Partition 2 (Follower)"]

        B3[Broker 3<br/>id=3] --> P0_3["Partition 0 (Follower)"]
        B3 --> P1_3["Partition 1 (Follower)"]
        B3 --> P2_1["Partition 2 (Leader)"]
    end
```

### KRaft (Replacing ZooKeeper)

Kafka 3.3+ uses **KRaft** (Kafka Raft) to replace ZooKeeper for metadata management:

```mermaid
graph TD
    subgraph "Legacy: ZooKeeper"
        ZK[ZooKeeper Ensemble] --> B1Z[Broker 1]
        ZK --> B2Z[Broker 2]
        ZK --> B3Z[Broker 3]
        NoteZK["Separate cluster to manage"]
    end

    subgraph "Modern: KRaft"
        KR[KRaft Controllers<br/>3 nodes, Raft-based] --> B1K[Broker 1]
        KR --> B2K[Broker 2]
        KR --> B3K[Broker 3]
        NoteKR["Built into Kafka, no external dependency"]
    end
```

| Aspect | ZooKeeper | KRaft |
|--------|-----------|-------|
| Metadata storage | External ZK cluster | Internal Raft quorum |
| Scalability | Limited (~200K partitions) | Millions of partitions |
| Startup time | Minutes (ZK sync) | Seconds |
| Operations | Two systems to manage | One system |
| Status | Deprecated (3.5+) | Default since Kafka 3.3+ |

### Kafka Storage Internals

Each partition is a **directory** containing segment files:

```
topic-partition-0/
  00000000000000000000.log    # Segment 1 (messages 0-999)
  00000000000000000000.index  # Offset to file position
  00000000000000000000.timeindex  # Timestamp to offset
  000000000000000001000.log   # Segment 2 (messages 1000-1999)
  000000000000000001000.index
```

**Write path**: Messages are appended to the active segment. Sequential writes are very fast (OS page cache, zero-copy transfer).

**Read path**: Consumers read from a specific offset. Kafka uses the index to jump to the right position in the log file.

## Kafka vs. Traditional Message Queues

| Aspect | Kafka | RabbitMQ/ActiveMQ |
|--------|-------|--------------------|
| **Model** | Distributed log | Message broker |
| **Retention** | Time/key-based | Until consumed |
| **Replay** | Yes (from offset) | No |
| **Ordering** | Per-partition | Per-queue |
| **Throughput** | Very high (millions/sec) | Moderate |
| **Use case** | Event streaming, data pipelines | Task queues, RPC |
| **Protocol** | Kafka binary protocol | AMQP, MQTT, STOMP |
| **Message priority** | No (FIFO per partition) | Yes |
| **Routing** | Topic + partition key | Exchanges, bindings, routing keys |

### When to Use Kafka vs RabbitMQ

- **Kafka**: Event streaming, log aggregation, data pipelines, event sourcing, high throughput
- **RabbitMQ**: Task queues, request/reply RPC, message routing, priority queues, low latency

## Interview Questions

1. **What is Kafka and how does it differ from traditional message queues?**
   - Kafka is a distributed commit log. Unlike traditional queues, messages are retained (not deleted after consumption), consumers can replay messages, and it provides per-partition ordering with very high throughput.

2. **Explain Kafka topics, partitions, and offsets.**
   - Topic: named stream of records. Partition: ordered, immutable sequence within a topic. Offset: unique position of each record within a partition. Partitions enable parallelism and ordering per key.

3. **What is a consumer group?**
   - A group of consumers that cooperatively consume a topic. Each partition is assigned to exactly one consumer in the group. Multiple groups can independently consume the same topic.

4. **How does Kafka achieve durability?**
   - Messages are persisted to disk and replicated across brokers. The replication factor determines how many copies exist. ISR (in-sync replicas) must acknowledge writes for durability.

5. **What is the ISR in Kafka?**
   - In-Sync Replicas: the set of replicas that are fully caught up with the leader. `min.insync.replicas` configures how many must be in sync. If a replica falls behind, it's removed from ISR.

6. **How does Kafka handle consumer rebalancing?**
   - When consumers join/leave a group, the broker triggers a rebalance. Partitions are redistributed among consumers. During rebalance, consumption pauses briefly.

## Common Mistakes

- Setting `acks=1` when durability matters — leader failure can lose messages
- Not configuring `min.insync.replicas` — single broker failure can lose data
- Too few partitions — limits consumer parallelism
- Not handling consumer rebalancing — can cause duplicate processing
- Ignoring consumer lag — consumers fall behind producers
- Using Kafka as a task queue — it's designed for streaming, not work distribution

## Summary

Kafka is a distributed streaming platform that provides durable, high-throughput, fault-tolerant messaging. Topics are divided into partitions for parallelism, and consumer groups enable scalable consumption. Key design choices include replication factor, ISR configuration, and acknowledgment settings. Kafka excels at event streaming, log aggregation, and data pipelines.

## Cross-References

- [Messaging Overview](README.md) — Messaging concepts
- [Message Queues](queues.md) — General queue patterns
- [RabbitMQ](rabbitmq.md) — Traditional message broker
- [Pub/Sub](pubsub.md) — Publish-subscribe patterns
- [Stream Processing](../mapreduce/streaming.md) — Kafka Streams
- [Consistent Hashing](../partitioning/consistent-hashing.md) — Partition assignment
