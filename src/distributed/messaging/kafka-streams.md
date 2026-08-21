# Kafka Streams

Kafka Streams is a client library for building stream processing applications on top of Apache Kafka, integrated with the Kafka client since Kafka 0.10 (2016). Unlike Flink or Spark Streaming, Kafka Streams is not a separate cluster — it's a library that runs inside your application. This page covers the architecture, the KStream/KTable abstractions, state stores, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Your Application (with Kafka Streams library)               │
│  - One or more instances (Java/JVM process)                  │
│  - Each instance runs KafkaStream threads                    │
│  - Each thread processes a subset of Kafka partitions        │
└─────────────────────────────────────────────────────────────┘
        │                              │
        │ consumer group              │ producer
        ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Kafka Cluster                                                │
│  - Input topics (consumed by your app)                       │
│  - Output topics (produced by your app)                      │
│  - Internal topics (changelog, repartition)                  │
└─────────────────────────────────────────────────────────────┘
```

Kafka Streams applications look like regular Kafka consumers/producers — there's no separate cluster. The library handles:
- Parallelism (one thread per Kafka partition).
- State management (RocksDB-backed state stores).
- Fault tolerance (state is restored from Kafka changelog topics).
- Local processing (no shuffles; the data is co-located with the processing).

## KStream and KTable

Kafka Streams has two main abstractions:

### KStream

A KStream is an event stream — each record is an independent event:

```java
KStream<String, Order> orders = builder.stream("orders");

// Filter, transform
KStream<String, Order> filtered = orders.filter((key, order) -> order.getAmount() > 100);

// To a topic
filtered.to("large-orders");
```

Records in a KStream have keys (String, Integer, etc.) and values. Records with the same key are not aggregated — each is processed independently.

### KTable

A KTable is a changelog stream — each record updates a key's value:

```java
KTable<String, User> users = builder.table("users");

// Filter
KTable<String, User> activeUsers = users.filter((key, user) -> user.isActive());
```

If a new record with key `alice` arrives, it replaces the previous record with key `alice`. The KTable is the stream-of-updates view of a database table.

KTable operations are stateful — the KTable maintains the current state per key in a state store.

## The DSL

Kafka Streams has a Domain-Specific Language (DSL) for common operations:

```java
StreamsBuilder builder = new StreamsBuilder();

KStream<String, Order> orders = builder.stream("orders");

// Filter
KStream<String, Order> filtered = orders.filter((k, v) -> v.getAmount() > 100);

// Map values
KStream<String, String> customerNames = orders.mapValues(Order::getCustomer);

// Group by key
KGroupedStream<String, Order> grouped = orders.groupByKey();

// Aggregate
KTable<String, Long> orderCounts = grouped.count();

// Join with KTable
KTable<String, User> users = builder.table("users");
KTable<String, UserOrder> joined = users.join(orderCounts, 
    (user, count) -> new UserOrder(user, count));

// Windowed aggregation (5-minute tumbling window)
KTable<Windowed<String>, Long> windowed = orders
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofMinutes(5)))
    .count();

// To topic
joined.toStream().to("user-orders");
```

The DSL is declarative; the library compiles it to a topology of source, processor, and sink nodes.

## State Stores

Stateful operations (KTable, aggregations, joins) maintain state in a "state store":

```text
State store types:
  - In-memory: fast, but limited by RAM (typically <1 GB per store)
  - Persistent (RocksDB): slower, but can hold terabytes on local disk

Each state store has:
  - A backing changelog topic in Kafka (for recovery).
  - Per-partition data (one store instance per Kafka partition).
```

When the application restarts, state stores are restored from the changelog topic. If a partition is reassigned to another instance (e.g., on scaling out), the new instance reads the changelog and rebuilds its state.

## Exactly-Once Processing

Since Kafka 2.5 (2020), Kafka Streams supports exactly-once processing via Kafka's transactional producer:

```properties
# Enable exactly-once
processing.guarantee=exactly_once_v2
```

With this setting, all side effects (output topic writes, state store updates, offset commits) are atomic. If the stream task fails mid-process, the transaction is rolled back; on retry, no duplicates.

## Interactive Queries

Kafka Streams applications can expose their state stores via the "interactive queries" API:

```java
// Get the state store
ReadOnlyKeyValueStore<String, Long> orderCounts = 
    kafkaStreams.store("order-counts", QueryableStoreTypes.keyValueStore());

// Query a key
Long count = orderCounts.get("alice");
```

This turns the Kafka Streams app into a key-value store that other services can query (e.g., via a REST API). Useful for low-latency reads of pre-computed aggregations.

## Production Use Cases

### Real-time Aggregations

```java
// Count orders per customer per 5-minute window
KStream<String, Order> orders = builder.stream("orders");
KTable<Windowed<String>, Long> counts = orders
    .groupByKey()
    .windowedBy(TimeWindows.of(Duration.ofMinutes(5)))
    .count();
counts.toStream().to("order-counts-5min");
```

### Stream-Table Joins

```java
// Enrich orders with customer info
KStream<String, Order> orders = builder.stream("orders");
KTable<String, Customer> customers = builder.table("customers");

KStream<String, EnrichedOrder> enriched = orders.join(
    customers,
    (order, customer) -> new EnrichedOrder(order, customer.getName())
);
enriched.to("enriched-orders");
```

### Sessionization

```java
// Group user events into sessions (10-minute gap)
KTable<Windowed<String>, List<Event>> sessions = events
    .groupByKey()
    .windowedBy(SessionWindows.with(Duration.ofMinutes(10)))
    .aggregate(
        ArrayList::new,
        (key, event, events) -> { events.add(event); return events; },
        (key, events1, events2) -> { events1.addAll(events2); return events1; }
    );
```

## Comparison to Flink and Spark Streaming

| Aspect | Kafka Streams | Flink | Spark Streaming |
|--------|---------------|--------|------------------|
| Deployment model | Library (in your app) | Separate cluster | Separate cluster |
| State backends | RocksDB | Memory, FS, RocksDB | Memory (limited) |
| Exactly-once | Yes (Kafka transactions) | Yes (Chandy-Lamport) | Yes (with sink support) |
| Latency | <100 ms | <100 ms | ~1 sec |
| Complex event processing | Limited (no CEP library) | Native | Limited |
| Window types | Tumbling, hopping, session, unbounded | Same | Tumbling, sliding, session |
| Best for | Kafka-native apps, simple pipelines | Complex streaming | Streaming + Spark SQL integration |

Kafka Streams is the choice when your data is in Kafka and you don't want a separate cluster. Flink is the choice for complex streaming with rich semantics. Spark Streaming is the choice when you already use Spark for batch and want unified code.

## Common Pitfalls

1. **Forgetting that Kafka Streams instances must have the same application ID.** The application ID is the consumer group; instances with different IDs are different applications.

2. **Forgetting that state stores are per-partition.** A 32-partition topic has 32 state store instances (one per partition). The aggregate across all instances requires querying all of them via interactive queries.

3. **Forgetting that exactly-once requires Kafka 2.5+.** On older Kafka versions, exactly-once-v2 isn't supported.

4. **Forgetting that state stores need disk space.** A stateful app with RocksDB on a 32-partition topic uses ~32 × state_size of disk. Plan capacity.

5. **Forgetting that scale-out requires rebalancing.** Adding instances triggers a rebalance; state stores are rebuilt from the changelog (slow for large state).

6. **Forgetting that the changelog topic has retention = infinite.** State stores' changelog topics don't expire; they grow indefinitely. Compact them.

## References

- [Kafka Streams documentation](https://kafka.apache.org/documentation/streams/)
- [Kafka Streams Developer Guide](https://kafka.apache.org/documentation/streams/developer-guide/)
- [Confluent Streams: Examples and tutorials](https://docs.confluent.io/platform/current/streams/index.html)
- [Kafka Streams vs Flink comparison](https://www.confluent.io/blog/kafka-streams-vs-flink-comparison/)
- [Kafka Interactive Queries](https://kafka.apache.org/33/documentation/streams/developer-guide/interactive-queries.html)
- [Exactly-once processing in Kafka Streams (Confluent blog)](https://www.confluent.io/blog/enabling-exactly-once-kafka-streams/)
