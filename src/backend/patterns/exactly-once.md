# Exactly-Once Processing

"Exactly-once" is a property of message-processing systems where every input message is processed exactly once — no duplicates, no skips. The phrase is misleading: any non-trivial system has at-least-once delivery at the network level (because messages can be retransmitted), so exactly-once is achieved by **making the processing idempotent** at the application level. This page covers why the network can't deliver exactly-once, the idempotency patterns that achieve it, and the trade-offs with at-least-once and at-most-once semantics.

## Why At-Least-Once Is the Network Reality

TCP delivers bytes in order without loss, but it can deliver duplicates if the receiver ack is lost and the sender retransmits. The TCP protocol has no way to know whether the receiver has processed the retransmitted data or not — only that it received it.

For higher-level message systems (Kafka, RabbitMQ, SQS), the problem is worse:

```text
Producer ──→ Message Broker ──→ Consumer
1. Producer sends message M
2. Broker receives M, sends ACK to Producer
3. ACK is lost in the network
4. Producer retransmits M
5. Broker now has two copies of M (or has deduplicated)
```

The broker can deduplicate, but only if the producer attaches a unique ID to each message (Kafka's `idempotent producer` does this with a producer ID and sequence numbers). Without this, the broker cannot distinguish a duplicate from a retransmission.

On the consumer side, the same problem:

```text
Consumer ──→ Broker
1. Consumer receives message M
2. Consumer processes M (e.g., deducts $100 from account)
3. Consumer sends ACK to Broker
4. ACK is lost
5. Broker re-delivers M
6. Consumer processes M again — DOUBLE DEDUCTION
```

Without an idempotency mechanism, the consumer will deduct $100 twice. With at-least-once delivery, the consumer's processing must be idempotent: processing the same message twice must have the same effect as processing it once.

## The Three Semantics

- **At-most-once**: messages may be lost but never duplicated. Implementation: send and forget. Use case: telemetry, logs (a missed metric is fine).
- **At-least-once**: messages are never lost but may be duplicated. Implementation: retry on failure. Use case: most real-world systems.
- **Exactly-once**: messages are processed exactly once. Implementation: idempotent processing + transactional state. Use case: financial transactions.

"Exactly-once" is really "at-least-once + idempotent processing". The label is misleading but has stuck in industry literature.

## Idempotency Patterns

### Pattern 1: Unique Message ID + Dedup Table

The consumer maintains a table of processed message IDs:

```sql
CREATE TABLE processed_messages (
    message_id VARCHAR(64) PRIMARY KEY,
    processed_at TIMESTAMP NOT NULL,
    result TEXT
);

-- Consumer flow:
BEGIN;
INSERT INTO processed_messages (message_id, processed_at, result)
VALUES (?, NOW(), NULL)
ON CONFLICT (message_id) DO NOTHING
RETURNING message_id;

-- If RETURNING is empty, the message was already processed; skip.
-- Otherwise, process the message and update the result.

UPDATE processed_messages SET result = ? WHERE message_id = ?;
COMMIT;
```

This requires the consumer's database to be in the same transaction as the dedup table. PostgreSQL and MySQL support this; Redis can do it with a SETNX-based atomic check.

### Pattern 2: Idempotency Key + Conditional Update

For HTTP APIs, the client provides an idempotency key (typically a UUID). The server stores the key with the response, and on a duplicate request returns the stored response:

```http
POST /api/charge
Idempotency-Key: 9c2f3a7e-1b5d-4f8e-9c0a-2b3c4d5e6f7a

{ "amount": 100, "currency": "USD" }
```

```http
HTTP/1.1 200 OK
Idempotency-Key: 9c2f3a7e-1b5d-4f8e-9c0a-2b3c4d5e6f7a

{ "charge_id": "ch_123", "amount": 100, "currency": "USD" }
```

If the client retries with the same key, the server returns the same response (no duplicate charge). Stripe's [idempotency key documentation](https://docs.stripe.com/api/idempotent_requests) describes this in detail.

### Pattern 3: Kafka Transactions

Kafka 0.11+ supports **transactional producers**: a producer can send multiple messages to multiple topics atomically:

```java
producer.initTransactions();
try {
    producer.beginTransaction();
    producer.send(new ProducerRecord<>("topic1", "key1", "value1"));
    producer.send(new ProducerRecord<>("topic2", "key2", "value2"));
    // Also: producer.sendOffsetsToTransaction() to commit consumer offsets atomically
    producer.commitTransaction();
} catch (Exception e) {
    producer.abortTransaction();
}
```

Consumers reading from these topics see either all of the transaction's messages or none. The Kafka consumer's `isolation.level=read_committed` ensures only committed transactions are visible.

For end-to-end exactly-once from one Kafka topic to another, the **consume-process-produce loop** must be atomic:

```java
consumer.subscribe(Collections.singleton("input-topic"));
producer.initTransactions();

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
    
    producer.beginTransaction();
    
    for (ConsumerRecord<String, String> record : records) {
        // Process the record and produce to output topic
        producer.send(new ProducerRecord<>("output-topic", 
                                            record.key(), 
                                            processValue(record.value())));
    }
    
    // Atomically commit the producer's messages AND the consumer's offsets
    producer.sendOffsetsToTransaction(
        Collections.singletonMap(
            new TopicPartition("input-topic", 0),
            new OffsetAndMetadata(consumer.position(new TopicPartition("input-topic", 0)))
        ),
        consumer.groupMetadata()
    );
    producer.commitTransaction();
}
```

This pattern gives end-to-end exactly-once: the input topic's offset is committed in the same Kafka transaction as the output topic's writes. If the transaction is aborted (e.g., consumer crashes mid-process), the offset is not committed, and the consumer will re-read the messages on restart.

### Pattern 4: Outbox Pattern with Change Data Capture

For non-Kafka systems (e.g., a service that writes to a database and sends a message), the **transactional outbox** pattern:

1. In a single database transaction, write the business state AND a row to the `outbox` table.
2. A separate "CDC" (Change Data Capture) process reads from `outbox` and publishes to the message broker.
3. The CDC process tracks its position (e.g., last published `outbox.id`) so it can resume after a crash.

```sql
-- Service's transaction
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 42;
INSERT INTO outbox (event_type, payload) VALUES ('payment_charged', '{"account":42,"amount":100}');
COMMIT;
```

The CDC process (Debezium, Maxwell, or a custom poller) reads `outbox` and publishes to Kafka. If the CDC process crashes after publishing but before recording the position, it will re-publish — but the consumer must dedup based on a unique event ID in the outbox row.

## Comparison of Patterns

| Pattern | Latency overhead | Throughput | Implementation cost | Use case |
|---------|------------------|-----------|----------------------|----------|
| Dedup table (per-message) | Low (single DB lookup) | High | Low | Most microservices |
| Idempotency key (HTTP) | Low | High | Low | HTTP APIs |
| Kafka transactions | Medium (transaction commit) | Medium | Low (Kafka built-in) | Kafka-to-Kafka pipelines |
| Outbox + CDC | High (async CDC) | Medium | High (CDC infra) | Cross-system (DB → broker) |

## Why "exactly-once" Has So Many Caveats

The phrase "exactly-once" is often used loosely. Strictly speaking:

- **Within a single Kafka cluster, end-to-end exactly-once is real** (since 0.11).
- **Across Kafka and an external system (e.g., a database)**, exactly-once requires the consumer to be idempotent — there's no way to atomically commit to both Kafka's offsets and the external system without a 2PC.
- **HTTP APIs are exactly-once only if the client provides an idempotency key** — the server cannot prevent duplicate side effects otherwise.
- **Real-world financial systems use at-least-once + idempotency, not "true" exactly-once**.

The phrase "exactly-once delivery" is meaningless without specifying the boundaries. "Exactly-once processing within Kafka" means one thing; "exactly-once side effects on a remote API" means another.

## Common Pitfalls

1. **Confusing "exactly-once" with "at-most-once".** A naive implementation that doesn't retry on failure gives at-most-once (messages are lost on crash). To get exactly-once, you need at-least-once delivery + idempotent processing.

2. **Using `auto_offset_reset=latest` for production consumers.** This skips any messages produced before the consumer joined the group, resulting in lost data. Use `earliest` for new consumers.

3. **Forgetting to commit offsets only after processing.** If you commit before processing and then crash, the message is lost (at-most-once). The default auto-commit in many Kafka clients is unsafe.

4. **Mixing transactional and non-transactional producers.** A consumer using `isolation.level=read_committed` will not see non-transactional messages. If your pipeline mixes both, data is lost from the consumer's perspective.

5. **Treating HTTP idempotency keys as deduplication only.** The server should return the same response on retry, not just skip the duplicate. If the original request returned an error, the retry should return the same error (not a "duplicate" success).

6. **Not handling the "zombie" case.** A consumer that's alive but whose heartbeat isn't reaching the broker gets evicted from the group; another consumer takes over and processes the same messages. The original consumer must finish or abort cleanly.

## References

- Kafka KIP-98: "Exactly Once Delivery and Transactional Messaging" — [KIP-98](https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging)
- Kafka KIP-447: "Producer scalability for exactly-once" — [KIP-447](https://cwiki.apache.org/confluence/display/KAFKA/KIP-447)
- [Apache Kafka documentation: Exactly-once semantics](https://kafka.apache.org/documentation/#semantics)
- [Debezium: CDC for transactional outbox](https://debezium.io/blog/2023/02/02/transactional-outbox/)
- [Stripe idempotency key docs](https://docs.stripe.com/api/idempotent_requests)
- [Confluent: Exactly-once semantics](https://www.confluent.io/blog/exactly-once-semantics-are-possible-heres-how-apache-kafka-does-it/)
- "[Exactly-once is impossible](https://brooker.cc/blog/2024/02/22/exactly.html)" — Marc Brooker (AWS) on why the phrase is misleading
