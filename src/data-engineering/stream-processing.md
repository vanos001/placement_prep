# Stream Processing

## Apache Kafka

Distributed event streaming platform:

### Core Concepts

```
Producer → Topic (Partitioned) → Consumer Group
              ├── Partition 0 → Consumer 1
              ├── Partition 1 → Consumer 2
              └── Partition 2 → Consumer 3
```

- **Topic**: Named stream of records
- **Partition**: Ordered, immutable sequence of records
- **Offset**: Position of a record within a partition
- **Consumer Group**: Group of consumers that divide partitions
- **Broker**: A Kafka server

### Key Properties

| Property | Description |
|---|---|
| Durability | Replicated across brokers |
| Ordering | Guaranteed within a partition |
| Replay | Consumers can re-read from any offset |
| Scalability | Add partitions and consumers |
| Retention | Configurable time/size-based retention |

### Delivery Semantics

- **At-most-once**: Commit before processing (may lose messages)
- **At-least-once**: Commit after processing (may process duplicates)
- **Exactly-once**: Kafka transactions + idempotent producers (requires coordination)

### Consumer Groups

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'my-topic',
    group_id='my-group',
    auto_offset_reset='earliest',
    enable_auto_commit=False
)

for message in consumer:
    process(message.value)
    consumer.commit()
```

## Apache Flink

Stream processing framework:

```java
StreamExecutionEnvironment env = 
    StreamExecutionEnvironment.getExecutionEnvironment();

DataStream<Event> events = env
    .addSource(new KafkaSource<>())
    .keyBy(Event::getUserId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new CountAggregate());

events.addSink(new KafkaSink<>());
env.execute("Streaming Job");
```

### Flink vs Spark Streaming

| Aspect | Flink | Spark Streaming |
|---|---|---|
| Model | True streaming (event-by-event) | Micro-batch |
| Latency | Milliseconds | Seconds |
| State | Native state management | External state |
| Exactly-once | Native | Via checkpointing |
| Windowing | Rich (event time, session) | Basic (processing time) |

## Stream Processing Patterns

1. **Filtering**: Drop unwanted events
2. **Transformation**: Enrich, map, aggregate
3. **Windowing**: Tumbling, sliding, session windows
4. **Joining**: Stream-stream, stream-table joins
5. **Aggregation**: Count, sum, average per window
6. **Pattern matching**: Complex event processing (CEP)

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Flink Documentation](https://flink.apache.org/docs/)
- [Streaming Systems — Akidau et al.](https://www.oreilly.com/library/view/streaming-systems/9781491983867/)
