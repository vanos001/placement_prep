# Apache Avro — Schema-First Binary Serialization

Apache Avro is a schema-driven, binary serialization format born at Hadoop's inception (2009, Doug Cutting) to replace the ad-hoc Writable classes Hadoop had been using for inter-node traffic. Unlike Protocol Buffers or Thrift, which embed field tags in every record, Avro stores **the schema once** and writes only the data — the schema is exchanged out-of-band. The result is the densest binary representation in the popular serialization zoo, but at the cost of strict schema coupling between writer and reader.

## The Schema

Avro schemas are JSON documents (`.avsc` files). They declare types in two flavours:

- **Primitive** — `null`, `boolean`, `int`, `long`, `float`, `double`, `bytes`, `string`
- **Complex** — `record`, `enum`, `array`, `map`, `union`, `fixed`

```json
{
  "type": "record",
  "name": "Payment",
  "namespace": "com.acme.payments",
  "doc": "A captured payment authorization.",
  "fields": [
    { "name": "id",         "type": "string", "doc": "UUID" },
    { "name": "amount",     "type": { "type": "bytes", "logicalType": "decimal", "precision": 19, "scale": 2 } },
    { "name": "currency",   "type": { "type": "string", "logicalType": "iso4217" } },
    { "name": "status",     "type": { "type": "enum", "name": "Status", "symbols": ["pending","authorized","captured","voided","refunded"] } },
    { "name": "created_at", "type": { "type": "long", "logicalType": "timestamp-millis" } },
    { "name": "metadata",   "type": { "type": "map", "values": "string" }, "default": {} },
    { "name": "tags",       "type": { "type": "array", "items": "string" }, "default": [] },
    { "name": "refund_reason", "type": ["null", "string"], "default": null }
  ]
}
```

Two design decisions matter:

- **`logicalType`** layers a semantic type on top of a primitive. `timestamp-millis` is `long` underneath; `decimal` is `bytes` underneath; `date` is `int` (days since 1970 epoch). Parsers can ignore logical types and treat the underlying primitive correctly — this is the forward-compatibility guarantee.
- **`union`** is `[<type>, <type>, ...]`. Unions of two record types with the same name are forbidden; instead, use a single record with a `status` field, or wrap each branch in a distinct namespace. This is the source of the most common Avro mistake — designers expect `oneOf`-like behavior and instead get a hard parser error.

Default values are required when a field is added to an existing record without breaking old readers (see schema evolution below).

## Binary Encoding — Compact and Tagless

Avro's wire format is genuinely minimal. Where Protobuf writes `(tag, value)` pairs and Thrift writes `(field-id, type, value)`, Avro writes **only the value**. The schema, exchanged out-of-band, tells the reader what to expect next.

The encoding rules:

| Avro type | Encoding |
|-----------|----------|
| `null`    | Zero bytes |
| `boolean` | 1 byte (`0` or `1`) |
| `int`, `long` | Variable-length zig-zag (signed) + LEB128 varint |
| `float`   | 4 bytes, little-endian IEEE 754 |
| `double`  | 8 bytes, little-endian IEEE 754 |
| `bytes`   | `long` length + raw bytes |
| `string`  | `long` length + UTF-8 bytes |
| `record`  | Concatenation of each field's encoding, in declaration order |
| `enum`    | `int` index of the symbol (zero-indexed, declaration order) |
| `array`   | `long` count, then items, then a `0` long terminator for continuation blocks |
| `map`     | Like array, but each entry is preceded by its key string |
| `union`   | `long` branch index, then the encoded branch |
| `fixed`   | Exactly `size` bytes, no length prefix |

The **zig-zag + varint** encoding for integers is borrowed from Protobuf: positive `n` becomes `2n`, negative `n` becomes `2|n|-1`, then the result is encoded as 7 bits per byte with continuation bits. This means small values fit in one byte regardless of sign, and that `-1` (an extremely common sentinel) is one byte, not ten.

For the `Payment` schema above, a record like:

```json
{ "id": "f1c0-2b3a", "amount": 19.99, "currency": "USD", "status": "authorized",
  "created_at": 1699999999999, "metadata": {}, "tags": ["new","guest"], "refund_reason": null }
```

encodes to roughly:

```
 2  10  f1c0-2b3a                    # string "f1c0-2b3a"  (len 9 as varint)
 8  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  # decimal 19.99 as scaled long in bytes
 6  USD                          # currency string
 1                               # enum index 1 (authorized)
 ce 9c d0 8f d1 14               # timestamp-millis varint
 0                               # empty map (count 0, terminator)
 2                               # array count 2
 3  new                          # "new"
 5  guest                        # "guest"
 0                               # array terminator
 0                               # union branch 0 = null
```

That is ~50 bytes. A JSON encoding of the same record is ~120 bytes; a Protobuf encoding with field tags is ~70 bytes. The savings come from three places: no per-field tags, length-prefixed strings use varints (saving 1 byte per length under 128), and records are concatenated without delimiters.

## The Schema Registry — Where Evolution Lives

The tagless design has an obvious consequence: a reader cannot parse bytes without the writer's schema. To make this practical in a streaming world where producers and consumers are decoupled, **Confluent's Schema Registry** was built. It is a sidecar service that stores schemas keyed by integer IDs; producers register their schema once, then prefix each message with the 5-byte ID `[0 magic byte, 4-byte schema id]`.

```
+--------+----------+----------------+
| 0x00   | schemaId |  payload       |
+--------+----------+----------------+
| magic  | int32 BE | Avro binary    |
+--------+----------+----------------+
```

Consumers fetch the schema by ID from the registry (cached after first fetch), then decode. This is the **Confluent wire format**, the de facto standard for Avro on Kafka; it is not part of the Avro spec itself.

The registry enforces **compatibility rules** for evolving schemas:

| Compatibility mode | New schema can read old data? | Old schema can read new data? | Use case |
|--------------------|-------------------------------|-------------------------------|----------|
| `BACKWARD`         | Yes                            | —                              | Consumers upgrade first |
| `FORWARD`          | —                              | Yes                            | Producers upgrade first |
| `FULL`             | Yes                            | Yes                            | Both directions guaranteed |
| `BACKWARD_TRANSITIVE` | Yes for all prior versions | —                            | Multi-version rolling upgrade |
| `NONE`             | —                              | —                              | Wild west |

Concretely, a `BACKWARD`-compatible change must:

- **Add** a field with a default value (default lets new readers decode old data).
- **Remove** a field (new schema ignores data the old writer still produces).
- **Change** a field type only if the new type can read the old encoding (e.g., `int` → `long` is allowed; `string` → `bytes` is not).
- **Add** an enum symbol — *backward incompatible*, old readers crash on new symbols. Workaround: use `string` instead of `enum`.

A `FORWARD`-compatible change must:

- **Add** a field with a default — old readers ignore the new field's data (default irrelevant for them).
- **Remove** a field that had a default — old readers fall back to the default when the field is missing in new data.

To make an evolution `FULL`, you must respect both rule sets simultaneously, which in practice means "add fields with defaults, never remove fields, never narrow types".

```bash
# Register a schema
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "{\"type\":\"record\",...}"}' \
  http://schema-registry:8081/subjects/payments-value/versions

# Check compatibility of a candidate schema
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "<candidate-escaped-json>"}' \
  http://schema-registry:8081/compatibility/subjects/payments-value/versions/latest?verbose=true
```

## Single-Object Encoding — With a Fingerprint

The Avro spec defines **Single-Object Encoding** for cases where you cannot negotiate a schema out-of-band (e.g., a single record written to a queue with no schema header). The bytes are prefixed by a 2-byte marker followed by an 8-byte CRC-64-AVRO fingerprint of the canonical form of the schema:

```
+--------+--------+----------------+----------------+
| 0xC3   | 0x01   | fingerprint    | Avro payload   |
+--------+--------+----------------+----------------+
| C1 byte | version | 8-byte BE    | encoded record |
+--------+--------+----------------+----------------+
```

The fingerprint is computed by:

1. Computing the parsing canonical form of the schema (rules strip whitespace, sort map keys, normalize numeric literals, drop doc/default aliases that don't affect parsing).
2. Running CRC-64 (polynomial `0x9fb20d4b4ae7e1db`, reflected) over the canonical JSON.
3. Storing the result as 8 bytes big-endian.

A reader that has the same schema in its registry computes the same fingerprint and finds a match. Collisions are astronomically unlikely (2^-64 per pair), but the registry should still verify the schema content matches.

## Container File Format — Avro Data Files

Avro defines a file format for on-disk storage of many records. Each file has:

```
+-------------+--------------------+------------------+
| header      | block 1            | block 2 ...      |
+-------------+--------------------+------------------+
| magic 'Obj' | metadata (Map<str> | sync marker (16B |
|             |  bytes>) incl.     | random)         |
|             | "avro.schema" +    | record count     |
|             | "avro.codec"       | block size       |
|             |                     | encoded records  |
+-------------+--------------------+------------------+
```

The header is itself an Avro-encoded `map<string, bytes>` containing `avro.schema` (the JSON schema), `avro.codec` (`null`, `deflate`, `snappy`, `zstandard`, `bzip2`, `xz`, `lzma`), and arbitrary user metadata. The 16-byte sync marker is a random value written at the end of each block; readers use it to recover from corruption by scanning for the next marker.

Each block stores its record count, its serialized size in bytes, and the records themselves. Splittability comes from the per-block sync marker: a reader can seek to any block boundary and start decoding. This is why Avro is the on-disk format behind many Hadoop ecosystem file formats (ORC, Parquet's evolution was similar but independent) — splittability is non-negotiable for MapReduce.

## Avro vs Protobuf vs Thrift vs JSON

| Property | Avro | Protobuf | Thrift | JSON |
|----------|------|----------|--------|------|
| Schema required? | Yes | Yes | Yes | No |
| Wire contains field tags? | No | Yes | Yes | Yes (names) |
| Self-describing on the wire? | No | No | No | Yes |
| Schema carried with data? | Optional (container) | No | No | Yes |
| Schema evolution strategy | Defaults + compat rules | Field number rules + `reserved` | Field id rules + `optional` | Ad hoc |
| Binary size (representative schema) | Smallest | +30% | +30% | +150% |
| Code generation required? | Yes (or dynamic) | Yes | Yes | No |
| Splittable file format? | Yes (.avro) | No | No | No |
| Dynamic typing? | Yes (GenericRecord) | No | No | Yes |

Avro's sweet spot is large volumes of similarly-structured records where the schema is stable enough to amortize the registry cost: Kafka topics, Parquet files (Parquet reuses Avro's logical types), Hadoop seq files, Iceberg v2 metadata. Protobuf dominates microservice RPC where schemas evolve independently and the wire must be self-describing enough to skip unknown fields. JSON dominates browser-facing APIs where human readability beats wire efficiency.

## Code Examples

### Java — Generic Record

```java
Schema.Parser parser = new Schema.Parser();
Schema schema = parser.parse(new File("Payment.avsc"));

GenericRecord payment = new GenericData.Record(schema);
payment.put("id", "f1c0-2b3a");
payment.put("amount", ByteBuffer.wrap(new BigDecimal("19.99")
    .unscaledValue().toBigInteger().toByteArray()));
payment.put("currency", "USD");
payment.put("status", "authorized");
payment.put("created_at", System.currentTimeMillis());
payment.put("metadata", Map.of());
payment.put("tags", List.of("new", "guest"));
payment.put("refund_reason", null);

ByteArrayOutputStream out = new ByteArrayOutputStream();
DatumWriter<GenericRecord> writer = new GenericDatumWriter<>(schema);
Encoder encoder = EncoderFactory.get().binaryEncoder(out, null);
writer.write(payment, encoder);
encoder.flush();
byte[] bytes = out.toByteArray();
```

### Python — Specific Record (fastavro)

```python
from fastavro import writer, reader, parse_schema

schema = parse_schema({
    "type": "record",
    "name": "Payment",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "amount_cents", "type": "long"},
        {"name": "currency", "type": "string"},
        {"name": "status", "type": {"type": "enum", "name": "Status",
                                    "symbols": ["pending", "authorized", "captured"]}},
    ],
})

with open("payments.avro", "wb") as f:
    writer(f, schema, [
        {"id": "f1c0-2b3a", "amount_cents": 1999, "currency": "USD", "status": "authorized"},
        {"id": "9a21-771d", "amount_cents": 4500, "currency": "EUR", "status": "captured"},
    ])

with open("payments.avro", "rb") as f:
    for record in reader(f):
        print(record["id"], record["status"])
```

### Confluent Kafka Wire Format

```python
from confluent_kafka import SerializingProducer, DeserializingConsumer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer

sr = SchemaRegistryClient({"url": "http://schema-registry:8081"})
serializer = AvroSerializer(sr, schema_str, conf={"use.schema.id": -1})
deserializer = AvroDeserializer(sr)

producer = SerializingProducer({
    "bootstrap.servers": "kafka:9092",
    "value.serializer": serializer,
})

def delivery(err, msg):
    if err:
        raise err

producer.produce(
    topic="payments",
    value={"id": "f1c0", "amount_cents": 1999,
           "currency": "USD", "status": "authorized"},
    on_delivery=delivery,
)
producer.flush()
```

The serializer prefixes the magic byte + schema ID before encoding; the deserializer reads the ID, fetches the schema from the registry (cached), and decodes.

## Common Mistakes

- **Adding an enum symbol** without `BACKWARD` breaking — old consumers crash on the unknown symbol. Use `string` for open sets.
- **Changing a field type** in a non-widening way (`string` → `bytes`) — incompatible at the binary level.
- **Removing a field without a default on the old version** — old readers fail to populate the field on new data.
- **Forgetting the namespace** — schema `name` is the fully-qualified name; collisions silently dedupe.
- **Trusting the JSON form as the wire format** — Avro JSON is for tooling, not for the wire. The wire is always binary.
- **Skipping the registry's `--compatibility` setting** — defaults to `BACKWARD`, which is usually wrong if producers upgrade first.

## Interview Questions

1. **Why is Avro's binary smaller than Protobuf's?**
   Avro does not write per-field tags; the schema is exchanged out-of-band. Protobuf writes a varint field number + wire type for every value.

2. **What does "schema evolution" mean in Avro?**
   A reader's schema need not match the writer's byte-for-byte. They must be *resolvable*: matching fields by name, with defaults for missing fields, and types that are promotable (int → long → float → double). The Schema Registry enforces this with compatibility modes.

3. **How does the Confluent wire format work?**
   A 5-byte prefix (`0` magic + 4-byte BE schema ID) precedes each Avro payload. Consumers fetch the writer's schema by ID from the registry, then perform schema resolution against their own reader schema.

4. **What is a logical type, and why does it matter?**
   A logical type (`timestamp-millis`, `decimal`, `date`, `uuid`) annotates a primitive type with a semantic meaning. Parsers can ignore it and still produce the right bytes; consumers that understand it produce native objects. This is the forward-compatibility hook — adding logical types doesn't break old readers.

5. **How do you handle an enum that needs to grow?**
   Two options: declare the enum `BACKWARD` incompatible and coordinate a deploy, or change the type from `enum` to `string` and validate at the application layer. Many teams opt for the latter.

## References

- Apache Avro 1.12.0 Specification: https://avro.apache.org/docs/1.12.0/specification/
- Confluent Schema Registry documentation: https://docs.confluent.io/platform/current/schema-registry/index.html
- Confluent Schema Registry compatibility rules: https://docs.confluent.io/platform/current/schema-registry/avro.html
- Avro single-object encoding (spec section): https://avro.apache.org/docs/1.12.0/specification/#single-object-encoding
- Avro container file format (spec section): https://avro.apache.org/docs/1.12.0/specification/#object-container-files
- Avro logical types: https://avro.apache.org/docs/1.12.0/specification/#logical+types
- fastavro documentation: https://fastavro.readthedocs.io/
- Confluent wire format (Kafka): https://docs.confluent.io/platform/current/schema-registry/serdes/index.html#wire-format
- Apache Parquet (reuses Avro logical types): https://parquet.apache.org/docs/
- "Schema Registry: A Data Contracting Story", Confluent blog: https://www.confluent.io/blog/schemas-concepts
- Apache Avro Java API: https://avro.apache.org/docs/1.12.0/api/java.html
- Doug Cutting's Avro design notes (Apache Jira AVRO-1): https://issues.apache.org/jira/browse/AVRO-1
