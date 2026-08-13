# Stream Processing

## Overview

Stream processing handles **unbounded data streams** in real-time, processing events as they arrive rather than in batches. It's essential for use cases requiring low-latency insights: fraud detection, real-time analytics, monitoring, and event-driven architectures. Major frameworks include Apache Flink, Kafka Streams, and Spark Structured Streaming.

## Batch vs. Stream Processing

```mermaid
graph TD
    subgraph "Batch Processing"
        B1["Bounded Data"] --> B2["Process All at Once"]
        B2 --> B3["Result"]
        Note1["Minutes to hours"]
    end
    
    subgraph "Stream Processing"
        S1["Unbounded Stream"] --> S2["Process Continuously"]
        S2 --> S3["Continuous Results"]
        Note2["Milliseconds to seconds"]
    end
```

| Aspect | Batch | Stream |
|--------|-------|--------|
| **Data** | Bounded (finite) | Unbounded (infinite) |
| **Latency** | High (minutes+) | Low (ms to seconds) |
| **Completeness** | Full dataset available | Partial data |
| **Use case** | Reports, training | Real-time alerts, monitoring |

## Key Concepts

### Event Time vs. Processing Time

```mermaid
graph LR
    subgraph "Event Time"
        E1["Event: user_click\nTime: 10:00:01"]
        E2["Event: user_click\nTime: 10:00:02"]
        E3["Event: user_click\nTime: 10:00:03"]
    end
    
    subgraph "Processing Time"
        P1["Processed: 10:00:05"]
        P2["Processed: 10:00:06"]
        P3["Processed: 10:00:07"]
    end
    
    E1 -.->|"Arrives late"| P2
```

| Time Type | Description | Use Case |
|-----------|-------------|----------|
| **Event time** | When the event actually occurred | Analytics, auditing |
| **Processing time** | When the event is processed | Monitoring, alerts |
| **Ingestion time** | When the event enters the system | Compromise |

### Watermarks

Watermarks track progress in event time, handling late-arriving data:

```mermaid
graph TD
    subgraph "Watermarks"
        W1["Watermark: 10:05:00"]
        Note["Events with time < 10:05:00\nare considered 'on time'"]
        Note2["Events with time >= 10:05:00\nmay still arrive"]
    end
    
    E1["Event: 10:04:59"] -->|On time| P1[Process]
    E2["Event: 10:05:01"] -->|May be late| P2[Buffer]
```

### Windowing

Windows group events for aggregation:

```mermaid
graph TD
    subgraph "Tumbling Window (Non-overlapping)"
        T1["10:00-10:01"] --> T2["10:01-10:02"]
        T2 --> T3["10:02-10:03"]
    end
    
    subgraph "Sliding Window (Overlapping)"
        S1["10:00-10:01"] --> S2["10:00:30-10:01:30"]
        S2 --> S3["10:01-10:02"]
    end
    
    subgraph "Session Window (Gap-based)"
        SE1["Session 1\n10:00-10:02"] --> GAP["Gap: 5 min"]
        GAP --> SE2["Session 2\n10:07-10:10"]
    end
```

| Window Type | Description | Example |
|-------------|-------------|---------|
| **Tumbling** | Fixed-size, non-overlapping | Count per minute |
| **Sliding** | Fixed-size, overlapping | Moving average |
| **Session** | Variable-size, gap-based | User sessions |
| **Global** | All events | Total count |

## Apache Flink

Flink is a true stream processing framework with batch capabilities:

```mermaid
graph LR
    subgraph "Flink Architecture"
        JM[Job Manager] --> TM1[Task Manager 1]
        JM --> TM2[Task Manager 2]
        JM --> TM3[Task Manager 3]
        
        TM1 --> O1[Operator 1]
        TM1 --> O2[Operator 2]
        TM2 --> O3[Operator 3]
        TM3 --> O4[Operator 4]
    end
```

### Flink Example

```java
StreamExecutionEnvironment env = 
    StreamExecutionEnvironment.getExecutionEnvironment();

// Source: Kafka
DataStream<Event> events = env
    .addSource(new FlinkKafkaConsumer<>("events", 
        new EventDeserializer(), properties));

// Processing: Windowed aggregation
DataStream<Result> results = events
    .filter(event -> event.getType().equals("click"))
    .keyBy(event -> event.getUserId())
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new CountAggregate());

// Sink: Database
results.addSink(new JdbcSink(...));

env.execute("Click Counter");
```

### Flink State Management

```mermaid
graph TD
    subgraph "Flink State"
        S[Operator State] --> KS[Keyed State]
        
        KS --> V[Value State]
        KS --> L[List State]
        KS --> M[Map State]
        KS --> R[Reducing State]
    end
```

### Flink Checkpointing

```mermaid
sequenceDiagram
    participant S as Source
    participant O1 as Operator 1
    participant O2 as Operator 2
    participant SN as Sink
    
    Note over S,SN: Checkpoint barrier injected
    S->>O1: Barrier
    O1->>O1: Snapshot state
    O1->>O2: Barrier
    O2->>O2: Snapshot state
    O2->>SN: Barrier
    SN->>SN: Snapshot state
    
    Note over S,SN: Checkpoint complete
    SN->>S: ACK
    
    Note over S,SN: On failure: restore from last checkpoint
```

## Kafka Streams

Kafka Streams is a **client library** for stream processing (no separate cluster needed):

```mermaid
graph LR
    subgraph "Kafka Streams App"
        S[Source Topic] --> P[Processor]
        P --> SK[Sink Topic]
    end
    
    Note["No separate cluster!\nJust a library in your app"]
```

### Kafka Streams Example

```java
StreamsBuilder builder = new StreamsBuilder();

KStream<String, Event> events = builder.stream("events");

KTable<String, Long> counts = events
    .filter((key, event) -> event.getType().equals("click"))
    .groupBy((key, event) -> event.getUserId())
    .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)))
    .count();

counts.toStream().to("click-counts");

KafkaStreams streams = new KafkaStreams(builder.build(), config);
streams.start();
```

### Kafka Streams Architecture

```mermaid
graph TD
    subgraph "Kafka Streams Application"
        T1["Topic Partition 1"] --> ST1["Stream Thread 1"]
        T2["Topic Partition 2"] --> ST1
        T3["Topic Partition 3"] --> ST2["Stream Thread 2"]
        T4["Topic Partition 4"] --> ST2
    end
    
    ST1 --> S1["State Store 1"]
    ST2 --> S2["State Store 2"]
```

## Comparison: Flink vs. Kafka Streams vs. Spark Streaming

| Aspect | Flink | Kafka Streams | Spark Streaming |
|--------|-------|--------------|-----------------|
| **Type** | Cluster framework | Library | Micro-batch |
| **Latency** | Very low (ms) | Low (ms) | Medium (seconds) |
| **State** | Managed, distributed | Local state stores | DStreams |
| **Fault tolerance** | Checkpoints | Kafka-backed | RDD lineage |
| **Windowing** | Rich (event time) | Basic | Tumbling only |
| **Cluster required** | Yes | No | Yes |
| **Use case** | Complex event processing | Simple Kafka apps | Batch+stream |

## Exactly-Once Semantics

Stream processing must handle failures without duplicating or losing data:

```mermaid
graph TD
    subgraph "Delivery Guarantees"
        ALO["At-Least-Once"] -->|"May duplicate"| Problem1["Idempotent consumers needed"]
        AMO["At-Most-Once"] -->|"May lose"| Problem2["Data loss possible"]
        EO["Exactly-Once"] -->|"Perfect"| Solution["Transactional processing"]
    end
```

### Exactly-Once Implementation

```mermaid
sequenceDiagram
    participant S as Source
    participant P as Processor
    participant SK as Sink
    
    S->>P: Read (checkpoint: offset 100)
    P->>P: Process
    P->>SK: Write (transactional)
    P->>S: Commit offset 100
    
    Note over P: Failure before commit!
    
    P->>S: Restart from offset 100
    P->>SK: Write (same transaction, idempotent)
    P->>S: Commit offset 100
    
    Note over SK: No duplicates!
```

## Interview Questions

1. **What is the difference between event time and processing time?**
   - Event time: when the event actually occurred. Processing time: when it's processed. Event time is important for correctness (handling late data); processing time is simpler but can be misleading.

2. **What are watermarks in stream processing?**
   - Watermarks track progress in event time. A watermark at time T means "no events with time < T are expected." They allow the system to handle late-arriving data.

3. **Explain the different window types.**
   - Tumbling: fixed-size, non-overlapping (1-minute windows). Sliding: fixed-size, overlapping (1-minute window, 30-second slide). Session: variable-size, gap-based (user sessions). Global: all events.

4. **How does Flink achieve exactly-once semantics?**
   - Through checkpointing (distributed snapshots) and transactional sinks. Checkpoints capture the state of all operators. On failure, the system restores from the last checkpoint and reprocesses.

5. **Compare Flink and Kafka Streams.**
   - Flink: cluster framework, rich windowing, managed state, complex event processing. Kafka Streams: client library, simpler, uses Kafka as state store, no separate cluster needed.

6. **What is the difference between narrow and wide transformations in stream processing?**
   - Narrow: each input record produces one output record (map, filter). Wide: input records are grouped/aggregated (groupBy, join) — requires state and potentially repartitioning.

## Common Mistakes

- Ignoring **event time** — processing time can give wrong results with out-of-order events
- Not setting **watermarks** — causes windows to never close
- Choosing **micro-batch** when true streaming is needed
- Not handling **late-arriving data** — use allowed lateness
- Forgetting about **state management** — stateful operations need careful design
- Not considering **exactly-once** requirements — at-least-once can cause duplicates

## Summary

Stream processing handles unbounded data streams in real-time. Key concepts include event time vs. processing time, watermarks, and windowing. Flink provides true streaming with rich features, Kafka Streams offers simplicity as a library, and Spark Structured Streaming bridges batch and stream. Exactly-once semantics requires careful coordination between sources, processors, and sinks.

## Cross-References

- [MapReduce Overview](README.md) — Batch processing context
- [MapReduce Framework](mapreduce.md) — Batch paradigm
- [Apache Spark](spark.md) — Spark Structured Streaming
- [Kafka](../messaging/kafka.md) — Common source/sink
- [Message Queues](../messaging/queues.md) — Delivery guarantees
- [Observability](../microservices/observability.md) — Monitoring stream jobs

## Cross References

- [MapReduce](mapreduce.md)
- [Spark](spark.md)
- [Kafka](../messaging/kafka.md)
- [Pub/Sub](../messaging/pubsub.md)
