# Schema Registry

Schema Registry is a service for storing and managing message schemas in event streaming systems, originally developed by Confluent for Apache Kafka. It allows producers and consumers to register Avro, Protobuf, or JSON Schema definitions, with compatibility checks for schema evolution. This page covers the architecture, the compatibility levels, the wire format, and the production deployment patterns.

## The Problem

Without a schema registry, Kafka producers and consumers must agree on the message format out-of-band. When a producer changes the format (adds a field, renames a column), consumers break silently — they parse the new format as the old, producing garbage.

The Schema Registry solves this by:
1. Storing all schema versions centrally.
2. Validating new schema versions against existing ones for compatibility.
3. Embedding a schema ID in each Kafka message so consumers know which schema to use.

## The Architecture

```text
┌──────────────────────────────────────────────────────────┐
│  Schema Registry (HA: 3+ instances, in-memory + Kafka log) │
│  - POST /schemas   ← store a new schema                  │
│  - GET /schemas/{id}   ← retrieve by ID                  │
│  - POST /compatibility/subjects/{subject}/versions       │
│      ← check compatibility with latest version             │
└──────────────────────────────────────────────────────────┘
        │                            │
        │ producer/consumer          │ schema updates
        ▼                            ▼
┌──────────────────────────────────────────────────────────┐
│  Producer (Kafka client with serializer)                   │
│  - Serializes messages with schema ID                     │
│  - Pre-registers schema with Schema Registry              │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  Kafka Topic                                              │
│  - Each message has: schema_id (4 bytes) + payload        │
└──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  Consumer (Kafka client with deserializer)                │
│  - Reads schema_id                                         │
│  - Fetches schema from Schema Registry (cached)           │
│  - Deserializes payload with schema                       │
└──────────────────────────────────────────────────────────┘
```

Schema Registry stores its state in a special Kafka topic (`_schemas`); each instance is stateless and reads from the topic. This gives HA without an external database.

## The Wire Format

For Avro/Protobuf/JSON Schema producers using the Confluent serializer:

```text
Kafka message value:
  Byte 0:        0 (magic byte, indicates Confluent format)
  Bytes 1-4:     schema ID (4 bytes, big-endian)
  Bytes 5+:      serialized payload (Avro binary, Protobuf, or JSON)

Total overhead: 5 bytes per message.
```

The consumer reads the schema ID, fetches the schema from the registry (cached after first fetch), and deserializes.

## Schema Evolution and Compatibility

Schemas evolve over time. The Schema Registry enforces compatibility rules to ensure consumers can read messages produced with older (or newer) schemas:

### Backward Compatibility (default)

A new schema is backward-compatible if consumers using the new schema can read messages produced with the previous schema.

- **Adding a field with a default value**: ✓ (consumers using the old schema just don't see the new field; consumers using the new schema get the default for old messages).
- **Removing a field**: ✓ (consumers using the new schema ignore the field in old messages).
- **Adding a required field (no default): ✗ (old messages don't have the field).
- **Changing a field type**: ✗ (usually).

### Forward Compatibility

A new schema is forward-compatible if consumers using the previous schema can read messages produced with the new schema.

- **Adding a field**: ✓ (old consumers ignore it).
- **Removing a field**: depends — if old consumers required the field, they break.
- **Adding a required field: ✓ (the new messages have it).

### Full Compatibility

Both backward and forward. The strictest level; recommended for production.

```bash
# Set compatibility for a subject
curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "FULL"}' \
  http://localhost:8081/config/orders-value
```

## Subjects and Topic Naming

Each schema has a "subject" — a name that groups schema versions. The default subject naming convention:

- `{topic}-key`: schema for the topic's key.
- `{topic}-value`: schema for the topic's value.

For a topic `orders`, the value schema is subject `orders-value`. New versions are `orders-value/1`, `orders-value/2`, etc.

Custom subject naming strategies (e.g., `TopicNameStrategy`, `RecordNameStrategy`) allow more flexibility.

## Production Deployment

```yaml
# Schema Registry config
kafkastore.connection.url: zookeeper:2181   # or bootstrap.servers
kafkastore.topic: _schemas
kafkastore.topic.replication.factor: 3      # HA
schema.registry.group.id: schema-registry
host.name: schema-registry-0
listeners: http://0.0.0.0:8081
```

Run 3+ Schema Registry instances for HA. Each is stateless; they sync via the `_schemas` topic.

## Use with Avro

```java
// Producer (Java)
Properties props = new Properties();
props.put("bootstrap.servers", "kafka:9092");
props.put("key.serializer", "io.confluent.kafka.serializers.KafkaAvroSerializer");
props.put("value.serializer", "io.confluent.kafka.serializers.KafkaAvroSerializer");
props.put("schema.registry.url", "http://schema-registry:8081");

Producer<String, Order> producer = new KafkaProducer<>(props);

Order order = new Order(123, "alice", 99.99);
ProducerRecord<String, Order> record = new ProducerRecord<>("orders", "alice", order);
producer.send(record);
```

The serializer:
1. Looks up the schema for `Order` in the registry.
2. If not present, registers it (subject `orders-value`).
3. Serializes the order with the schema ID prefix.
4. Sends the message to Kafka.

```java
// Consumer (Java)
Properties props = new Properties();
props.put("bootstrap.servers", "kafka:9092");
props.put("key.deserializer", "io.confluent.kafka.serializers.KafkaAvroDeserializer");
props.put("value.deserializer", "io.confluent.kafka.serializers.KafkaAvroDeserializer");
props.put("schema.registry.url", "http://schema-registry:8081");
props.put("group.id", "orders-consumer");

Consumer<String, Order> consumer = new KafkaConsumer<>(props);
consumer.subscribe(Collections.singletonList("orders"));

while (true) {
    ConsumerRecords<String, Order> records = consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, Order> record : records) {
        System.out.println(record.value().getCustomer());
    }
}
```

The deserializer reads the schema ID, fetches the schema (cached), and deserializes the payload.

## Common Pitfalls

1. **Forgetting to set compatibility correctly.** A new schema that breaks compatibility is rejected. Plan the schema evolution carefully.

2. **Forgetting that Schema Registry is a SPOF if you run only one instance.** Always run 3+ for HA.

3. **Forgetting to handle schema-not-found errors.** If a producer references a schema ID that the registry doesn't have (e.g., after a registry wipe), the consumer fails. Backup the `_schemas` topic.

4. **Forgetting that schema registration is one-way.** Schemas can't be deleted (only deprecated). This is intentional — old messages may still reference old schemas.

5. **Forgetting that the Confluent wire format is incompatible with non-Confluent serializers.** If you produce without the Confluent serializer, the message won't have the schema ID prefix.

6. **Forgetting that Avro schemas are JSON.** Avro schemas are JSON documents; not all JSON is valid Avro (e.g., no `null` keys, no nested objects without type declarations).

## References

- [Confluent Schema Registry documentation](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [Schema Registry API reference](https://docs.confluent.io/platform/current/schema-registry/develop/api.html)
- [Avro specification](https://avro.apache.org/docs/current/specification/)
- [Confluent Schema Registry GitHub](https://github.com/confluentinc/schema-registry)
- [Apicurio Registry (open-source alternative)](https://github.com/apicurio/apicurio-registry)
- [LWN: Schema Registry (2020)](https://lwn.net/Articles/820528/)
- [Schema evolution and compatibility (Confluent blog)](https://www.confluent.io/blog/schema-registry-a-vital-component-for-event-streaming-applications/)
