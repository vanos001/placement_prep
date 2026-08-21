# Kafka Connect

Kafka Connect is Apache Kafka's framework for moving data in and out of Kafka topics, without writing custom producer/consumer code. It provides a plugin architecture for "connectors" (source connectors that push data into Kafka; sink connectors that consume data from Kafka), with built-in offset management, parallelism, and fault tolerance. This page covers the architecture, the connector lifecycle, the connector ecosystem, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Connect Cluster (one or more workers, HA via group)        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Worker 1                                               │ │
│  │  - Source connector instances (one per partition)        │ │
│  │  - Sink connector instances (one per Kafka partition)   │ │
│  │  - REST API for management                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Worker 2                                               │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Worker 3                                               │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
   Source System                Kafka Cluster
   (PostgreSQL, S3,              (brokers)
   file, ...)                       
```

Workers form a Kafka consumer group (for sink connectors) or use Kafka's internal topics (for source connectors' offset storage).

## Source vs Sink Connectors

- **Source connector**: reads from an external system and produces to Kafka. Examples: JDBC source, Debezium (CDC), FileStream source, S3 source.

- **Sink connector**: consumes from Kafka and writes to an external system. Examples: JDBC sink, Elasticsearch sink, S3 sink, HDFS sink.

```text
Source flow: External → Source Connector → Kafka topic
Sink flow:   Kafka topic → Sink Connector → External
```

Most real-world pipelines have both: source connectors ingest from databases; sink connectors export to warehouses.

## Connector Configuration

A connector is configured via JSON (POST to the REST API) or YAML (in distributed mode):

```bash
# Create a JDBC source connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "postgres-orders-source",
    "config": {
      "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
      "connection.url": "jdbc:postgresql://db/orders",
      "connection.user": "user",
      "connection.password": "pass",
      "table.whitelist": "orders",
      "mode": "incrementing",
      "incrementing.column.name": "id",
      "topic.prefix": "postgres-"
    }
  }'
```

The connector is now running; new rows in `orders` are produced to `postgres-orders`.

## Connector Tasks

Each connector has 1+ tasks (parallelism). The number of tasks is determined by:
- For source connectors: typically one task per source partition (e.g., one per database table).
- For sink connectors: one task per Kafka topic partition (auto-balances with Kafka's consumer group).

```text
Connector: postgres-orders-source
  Tasks:
    Task 0: reads from orders table
    Task 1: reads from users table
    Task 2: reads from products table
```

If a worker fails, the Connect cluster rebalances — the failed worker's tasks are picked up by surviving workers.

## Offset Management

Source connectors must track "where am I in the source" so that on restart, they continue from where they left off. Kafka Connect stores offsets in an internal Kafka topic (`connect-offsets`).

```text
Task 0 reads from orders table, last ID = 12345.
On crash, the task restarts on another worker, reads offset (orders, 12345),
continues from ID 12346.
```

This ensures exactly-once delivery (no duplicates, no gaps) across worker failures.

For sink connectors, Kafka's consumer group offset management handles the same concern.

## Single-File Mode (Development)

For development, Kafka Connect can run in "standalone" mode (single process, no cluster):

```bash
connect-standalone.sh config/standalone.properties jdbc-source-connector.properties
```

All connectors run in this single process. No HA, no rebalancing. Useful for testing.

## Distributed Mode (Production)

For production, distributed mode is required:

```bash
# Worker 1
connect-distributed.sh config/distributed.properties

# Worker 2, 3, ...
connect-distributed.sh config/distributed.properties
```

Workers form a cluster, share connector state via the `connect-configs` and `connect-offsets` internal topics. Connectors can be added/removed via REST API.

## Connector Ecosystem

Hundreds of Kafka Connect connectors are available:

### Source connectors

- **JDBC Source**: reads from any JDBC-compatible database.
- **Debezium**: reads CDC events from MySQL, PostgreSQL, MongoDB, SQL Server, Oracle.
- **FileStream Source**: reads from a file (line by line).
- **MQTT Source**: reads from MQTT brokers.
- **Azure Blob Storage Source**: reads from Azure Blob.
- **S3 Source**: reads from S3.
- **Twitter Source**: reads from Twitter's API.

### Sink connectors

- **JDBC Sink**: writes to any JDBC database.
- **Elasticsearch Sink**: writes to Elasticsearch.
- **S3 Sink**: writes to S3 as Parquet/JSON.
- **HDFS Sink**: writes to HDFS.
- **Cassandra Sink**: writes to Cassandra.
- **MongoDB Sink**: writes to MongoDB.
- **BigQuery Sink**: writes to BigQuery.
- **Snowflake Sink**: writes to Snowflake.

Most connectors are open-source (Confluent Hub) but some are commercial.

## Debezium: The Canonical CDC Connector

Debezium is a popular Kafka Connect connector that reads Change Data Capture (CDC) events from databases:

```text
PostgreSQL logical replication → Debezium connector → Kafka topic
  Each row change becomes a Kafka message:
    {"before": {...}, "after": {...}, "op": "u" (update), "ts_ms": 1692616800000}
```

Debezium supports:
- **PostgreSQL**: via logical replication (pgoutput plugin).
- **MySQL**: via binlog.
- **MongoDB**: via change streams.
- **SQL Server**: via Change Tracking.
- **Oracle**: via LogMiner (commercial feature).

The CDC pattern enables real-time data pipelines: any change in the source DB is immediately available in Kafka, and downstream sinks (e.g., Elasticsearch, ClickHouse) consume it.

## Schema Registry

For connectors that produce structured data (Avro, Protobuf, JSON Schema), the Confluent Schema Registry stores and validates schemas:

```text
Source connector → Schema Registry → Kafka topic (Avro with schema ID)

Schema evolution:
  Producer registers new schema version.
  Schema Registry validates compatibility (backward, forward, full).
  Consumers can handle multiple schema versions.
```

This avoids the "schema drift" problem where producers and consumers disagree on the message format.

## Single Message Transforms (SMT)

Kafka Connect supports per-message transformations:

```json
{
  "transforms": "extractId,filterStatus",
  "transforms.extractId.type": "org.apache.kafka.connect.transforms.ExtractField$Key",
  "transforms.extractId.field": "id",
  "transforms.filterStatus.type": "org.apache.kafka.connect.transforms.Filter",
  "transforms.filterStatus.predicate": "isShipped",
  "predicates.isShipped.type": "org.apache.kafka.connect.predicate.RecordIs$Value",
  "predicates.isShipped.field": "status",
  "predicates.isShipped.value": "shipped"
}
```

SMTs run in the worker, before the message is produced (source) or after it's consumed (sink). Useful for:
- Field extraction (e.g., extract a key from the value).
- Field renaming.
- Filtering (e.g., only "shipped" orders).
- Timestamp extraction.

## Common Pitfalls

1. **Forgetting to set `value.converter` correctly.** The default is JSON; if your sink expects Avro, you must set `value.converter=io.confluent.connect.avro.AvroConverter`.

2. **Forgetting that source connector restarts may produce duplicates.** Without "exactly-once" mode (added in Kafka 3.3), a worker failure may produce a duplicate message. Sink connectors must be idempotent.

3. **Forgetting that connector tasks share JVM memory.** A connector with a memory leak affects all connectors on the same worker. Monitor JVM heap.

4. **Forgetting to set `offset.storage.topic` replication factor.** The default is 1 (single replica); for HA, set to 3.

5. **Forgetting that SMTs add per-message latency.** A complex SMT chain can add ms to every message. Profile.

6. **Forgetting that Debezium requires database configuration.** PostgreSQL must enable logical replication; MySQL must use row-based binlog. These are not enabled by default.

## References

- [Kafka Connect documentation](https://kafka.apache.org/documentation/#connect)
- [Confluent Connector Hub](https://www.confluent.io/hub/)
- [Debezium documentation](https://debezium.io/documentation/)
- [Confluent Schema Registry](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [Kafka Connect REST API](https://docs.confluent.io/platform/current/connect/management.html)
- [Single Message Transforms](https://www.confluent.io/blog/kafka-connect-single-message-transformums-smt-vsmt-with-examples/)
- [Debezium + Kafka Connect tutorial](https://debezium.io/documentation/reference/tutorial/)
