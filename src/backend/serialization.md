# Serialization — Formats, Schema Evolution & Zero-Copy

## Overview

**Serialization** is the process of converting in-memory data structures into a byte stream (for storage or transmission) and back. It is the invisible backbone of every distributed system: every RPC, every message on a queue, every row written to a log, every value stored in a cache is serialized on the way out and deserialized on the way in. The choice of format determines wire size, parse cost, schema-evolution story, language interoperability, and the boundary between what is and is not a breaking change.

The serialization landscape splits along three axes:

- **Text vs binary** — JSON, XML, YAML are human-readable but expensive to parse and verbose on the wire. Protobuf, Avro, Thrift, Cap'n Proto, FlatBuffers, MessagePack, CBOR are binary: compact, fast, but require a schema or out-of-band type information to interpret.
- **Schema-required vs schemaless** — Protobuf, Avro, Thrift, FlatBuffers, Cap'n Proto require a schema definition (IDL) and generate code. JSON, MessagePack, CBOR are self-describing: the bytes carry their type information. Schemaless formats are easier to adopt but provide no compile-time guarantees.
- **Copy-based vs zero-copy** — Most formats decode into freshly allocated objects. FlatBuffers and Cap'n Proto allow reading fields directly from the serialized buffer with no allocation, trading encoding complexity for read-path performance.

This page focuses on the conceptual core: schema evolution, backward and forward compatibility, and zero-copy techniques. For format-specific deep dives, see the cross-references at the end.

> Related: [gRPC](./api/grpc.md), [REST](./api/rest.md), [API Versioning](./api/versioning.md), [Kafka](./messaging/kafka.md), [Data Formats](../data-engineering/data-formats.md), [Protobuf vs FlatBuffers vs Cap'n Proto](../linux/sysprog/protobuf-flatbuf.md)

## Why Serialization Matters

Consider a service that emits an event to Kafka whenever a user signs up. The consumer of that event is a different team, deployed independently, possibly weeks behind the producer in release cadence. If the producer adds a new field to the event, every consumer must continue to work without redeployment. If the producer renames a field, every consumer breaks. The serialization format's schema-evolution semantics determine which changes are safe and which require coordinated deploys.

The same concern applies to stored data: a Parquet file written two years ago must still be readable by today's analytics pipeline, even though the schema has evolved. Database schemas evolve too, but databases are centralized — the schema lives in one place and migrations are atomic. Serialized data is decentralized: once bytes are written, the schema at write time is baked in forever.

Three properties capture the practical concerns:

- **Backward compatibility** — new code can read old data. The schema can be evolved without breaking existing readers that have not yet upgraded.
- **Forward compatibility** — old code can read new data. The schema can be evolved without breaking existing readers that have not yet upgraded, by ignoring unknown fields.
- **Zero-copy decoding** — readers can access fields without allocating intermediate objects, important for hot paths in high-throughput systems.

## Format Landscape

| Format | Style | Schema required? | Wire size | Parse speed | Schema evolution | Zero-copy |
|--------|-------|------------------|-----------|-------------|------------------|-----------|
| JSON | Text | No | 1× (baseline) | Slow | Ad hoc, no guarantees | No |
| XML | Text | Optional (XSD) | 1.5–2× JSON | Very slow | XSD, complex | No |
| YAML | Text | No | ~JSON | Slowest | Ad hoc | No |
| MessagePack | Binary | No | ~0.5× JSON | Fast | Like JSON, ad hoc | No |
| CBOR | Binary (RFC 8949) | No | ~0.5× JSON | Fast | Like JSON, ad hoc | No |
| Protobuf | Binary | Yes (.proto) | 0.3–0.5× JSON | Very fast | Strict rules, both directions | No (must decode) |
| Avro | Binary | Yes (.avsc) | 0.2–0.4× JSON | Very fast | Strict rules, both directions | No |
| Thrift | Binary | Yes (.thrift) | ~Protobuf | Very fast | Strict rules, both directions | No |
| FlatBuffers | Binary | Yes (.fbs) | 0.4–0.7× JSON | Fastest decode | Strict rules, both directions | **Yes** |
| Cap'n Proto | Binary | Yes (.capnp) | 0.4–0.7× JSON | Fastest decode | Strict rules, both directions | **Yes** |

Wire-size and parse-speed numbers are approximate, based on benchmarks of representative schemas. Actual numbers depend heavily on the schema (small fields favor Protobuf; large blobs favor raw bytes) and the language (compiled languages benefit more from code generation).

## Text Formats — JSON, XML, YAML

### JSON

JSON (JavaScript Object Notation, RFC 8259) is the lingua franca of the web. It has six types: null, boolean, number (IEEE 754 double), string (UTF-8), array, object. Its strengths are universal support, human readability, and self-description (the bytes carry their types). Its weaknesses are:

- **No schema** — JSON itself has no schema language. JSON Schema (Draft 2020-12) is a separate spec; it is used for validation but is not enforced by parsers.
- **Numbers are doubles** — JSON has a single numeric type. Integers larger than 2^53 lose precision when read by JavaScript's `JSON.parse`. Most other languages provide an integer-vs-float distinction at the parser level, but the wire format does not.
- **No comments** — the spec forbids comments, which makes hand-edited configuration files painful. JSON5 and JSONC are unofficial extensions that allow comments.
- **Verbose** — field names are repeated in every object; no compact field tags.
- **Slow to parse** — string parsing, number parsing, and unicode handling dominate.

For API payloads that humans will inspect and tools will edit, JSON is the right choice. For internal RPC at high QPS, JSON is a measurable overhead.

### XML

XML (Extensible Markup Language, W3C) is more expressive than JSON: it has attributes, namespaces, mixed content, and a schema language (XSD) that can express complex constraints. It is also far more verbose, slower to parse, and harder to use in code. XML is still common in enterprise integrations (SOAP, SAML, older REST APIs), document formats (OOXML, SVG, RSS), and configuration (Maven POMs, Spring configs). For new APIs, prefer JSON unless you need XML's specific capabilities (mixed content, namespace-qualified attributes).

### YAML

YAML (YAML Ain't Markup Language) is a superset of JSON optimized for human authoring. It supports comments, multi-line strings, anchors and aliases (a limited form of references), and a rich type system (dates, booleans, null). It is the dominant format for configuration files (Kubernetes manifests, Docker Compose, GitHub Actions, Ansible playbooks). Its weaknesses are:

- **The spec is enormous** — YAML 1.2 is over 80 pages. Different parsers implement different subsets, leading to subtle incompatibilities.
- **Security** — some YAML parsers support arbitrary object construction via `!!python/object` or `!!java/object` tags, which is a remote code execution vulnerability if untrusted input is parsed. Python's `yaml.safe_load` exists for this reason; `yaml.load` without a Loader argument is unsafe.
- **The Norway problem** — YAML 1.1 interpreted `no`, `yes`, `on`, `off` as booleans. Country codes parsed as booleans broke many a configuration. YAML 1.2 fixed this.

## Binary Self-Describing Formats — MessagePack, CBOR

MessagePack and CBOR (Concise Binary Object Representation, RFC 8949) are binary supersets of JSON: they preserve JSON's data model but encode it compactly. A JSON object `{"name": "Alice", "age": 30}` becomes roughly 18 bytes of MessagePack vs 24 bytes of JSON.

| Format | Spec | Notable users |
|--------|------|---------------|
| MessagePack | msgpack.org | Redis (stored as MessagePack for hash fields), Redisearch, many RPC systems |
| CBOR | RFC 8949 | COSE (CBOR Object Signing and Encryption), WebAuthn, IoT protocols |

Both preserve JSON's lack of schema. They are appropriate when JSON is too slow but you cannot afford the code-generation step of Protobuf or Avro. They do not provide schema-evolution guarantees beyond what JSON provides: an extra field is ignored by readers that do not know about it, and a missing field is reported as absent.

## Schema-Driven Binary Formats — Protobuf, Avro, Thrift

These three formats require an Interface Definition Language (IDL) and generate code for each target language. The schema is the contract; the wire format is an implementation detail.

### Protocol Buffers (Protobuf)

Google's format, originally open-sourced in 2008. Schema is a `.proto` file; the protoc compiler generates language-specific code. Wire format is tag-length-value (TLV): each field is encoded as `(field_number, wire_type, value)`, so unknown fields can be skipped without parsing them.

Example schema (proto3):

```proto
syntax = "proto3";

message User {
  uint64 id = 1;
  string name = 2;
  string email = 3;
  repeated string roles = 4;
  oneof contact {
    string phone = 5;
    string slack = 6;
  }
}
```

Schema evolution rules (proto3):

- **Adding a field** — backward and forward compatible. Old readers ignore the unknown tag; new readers see the default value (zero, empty string, empty list) for missing fields.
- **Removing a field** — backward and forward compatible *if* the tag number is retired and never reused. Reserved tag numbers prevent accidental reuse.
- **Changing a field type** — compatible only between compatible wire types (e.g., `int32` ↔ `int64` are both varint, so compatible; `int32` ↔ `string` is not). When in doubt, do not change types.
- **Renaming a field** — wire-compatible (the wire format uses tag numbers, not names) but breaks JSON-encoded protobuf and any code that references the field by name.
- **Changing field numbers** — always a breaking change. The tag number is the identity on the wire.
- **`required` fields** — in proto2, `required` breaks forward compatibility (old readers reject messages missing the field). proto3 removed `required` entirely. Never use `required` in proto2 unless you control every reader.

### Avro

Avro (Apache) is the standard serialization format for Hadoop-era data engineering. It is schema-required but the schema is carried *with the data* in the file header (for Avro Object Container Files) or in a separate handshake (for RPC). The wire format has no field tags — fields are written in schema order, so the reader's schema must match the writer's schema closely.

Schema evolution rules:

- **Adding a field** — backward compatible if the new field has a default. Forward compatible if the reader's schema has the field as default (i.e., the reader is prepared for the writer to be old).
- **Removing a field** — backward compatible if the reader's schema does not have the field (it ignores the writer's value). Forward compatible if the writer's schema does not have the field (the reader supplies its default).
- **Changing a field type** — allowed only for "promotion" paths: `int` → `long` → `float` → `double` → `string`. The reverse is a breaking change.
- **Renaming a field** — breaking unless aliases are declared in the reader's schema (the reader's `aliases` list maps old names to the new one).

Avro's strength is in batch and streaming data: Parquet files use Avro schemas, Kafka topics can be Avro-encoded with the schema registered in a Schema Registry. The Schema Registry enforces compatibility rules on every schema change: a producer cannot register a schema that breaks existing consumers.

### Thrift

Apache Thrift (Facebook, open-sourced 2007) predates both Protobuf and Avro. It includes both a serialization format and an RPC framework. Thrift has multiple wire formats: binary (TLV like Protobuf), compact (smaller, delta-encoded field numbers), and JSON. Schema evolution rules are similar to Protobuf: optional fields with default values can be added or removed; field IDs must not be reused.

Thrift is still in use at Facebook (now Meta), Apache Cassandra (inter-node protocol), and parts of Hadoop, but has lost momentum to Protobuf and Avro for new projects.

## Zero-Copy Formats — FlatBuffers, Cap'n Proto

Both FlatBuffers (Google) and Cap'n Proto (Kenton Varda, the original Protobuf author) take a fundamentally different approach: the serialized bytes are laid out exactly as the in-memory representation would be, so reading a field requires no parsing — just a pointer offset and a type cast. This trades encoding complexity (writing is harder because the layout must be canonical) for read-path performance.

### FlatBuffers

A FlatBuffers message is a tree of offset-based references. Reading the `name` field of a `User` requires: read the root table offset, add the field's vtable offset, dereference to get the field's location, read the field. No allocation, no copy, no parsing of the rest of the message. A 1 MB message can be queried for one field in microseconds.

Use cases: game engines (Google's ARCore, many Unity games), mobile apps where allocation pressure matters, and read-heavy workloads where the same message is read by many consumers but only some fields are used by each.

### Cap'n Proto

Cap'n Proto takes the same idea further: the wire format *is* the in-memory format. Pointers are relative (not absolute), so a serialized message can be loaded into memory at any address without relocation. Reads are direct pointer dereferences. Cap'n Proto also supports capability-based RPC (each interface method is a "capability" that can be passed around).

Cap'n Proto's encoding is so fast that there is no separate "encode" step — you build the message in place in a pre-allocated buffer, and the buffer is already serialized. The same is true for decoding: there is no decode step, you just read the fields.

Use cases: Sandstorm.io (the cloud platform Cap'n Proto was originally built for), high-throughput RPC systems, real-time systems where allocation must be avoided.

The trade-off: zero-copy formats have larger wire sizes than Protobuf (typically 1.5–2×) because the layout must be canonical and includes vtables / pointer offsets. They also cannot compress as well at the field level (each field's bytes are at a fixed offset, not packed).

## Schema Evolution — Compatibility Levels

When you change a schema, the question is: which readers can still read data written with the old schema? Confluent's Schema Registry formalizes this with three compatibility levels:

| Level | What it guarantees | Typical use |
|-------|-------------------|-------------|
| **BACKWARD** | New schema can read data written with the *previous* schema | Consumer upgrade first |
| **FORWARD** | Previous schema can read data written with the new schema | Producer upgrade first |
| **FULL** | Both backward and forward | Either side can upgrade first, fully decoupled |

For each level, you also choose `TRANSITIVE` (compatible with all previous versions) or non-transitive (compatible only with the immediately previous version). A typical production setup uses `BACKWARD_TRANSITIVE` for Kafka topics: consumers can always read old messages, producers can be upgraded independently.

Concrete rules per format (summary):

| Change | Protobuf (proto3) | Avro | JSON |
|--------|-------------------|------|------|
| Add optional field | ✅ Backward + Forward | ✅ Backward + Forward (if default) | ✅ (old readers ignore) |
| Remove optional field | ✅ Backward + Forward | ✅ Backward + Forward | ✅ |
| Add required field | ❌ Breaking | ❌ Breaking | n/a |
| Remove required field | ❌ Breaking | ❌ Breaking | n/a |
| Change field type | ⚠️ Wire-compatible types only | ⚠️ Promotion only | n/a |
| Change field number / name (identity) | ❌ Breaking | ⚠️ Aliases work | ⚠️ Renames break JSON paths |
| Reorder fields | ✅ (tag-based) | ✅ (name-based) | ❌ (positional in arrays) |

## Zero-Copy Techniques

Zero-copy serialization aims to eliminate the allocations and memcpy calls that conventional formats impose on the read path. Three patterns are common:

- **Pointer-relative layout** (Cap'n Proto, FlatBuffers): the wire format *is* the in-memory format. Fields are accessed via offsets, not by parsing into separate objects.
- **Memory-mapped files**: open the serialized data with `mmap` and read fields directly from the mapped region. The OS handles paging; no explicit read or copy is needed. Used by SQLite, RocksDB (SSTables), and many columnar formats.
- **`sendfile` / `splice`**: the kernel copies data directly from one file descriptor to another, bypassing user space. Used by static-file web servers (nginx, Apache) and by Kafka's zero-copy send path (file → socket without a user-space copy).

A common pattern in high-throughput systems: the producer serializes into a direct `ByteBuffer` (off-heap), the network stack sends it via `sendfile` or `writev`, and the consumer memory-maps the file and reads fields without ever copying them into the JVM heap. The Java NIO `FileChannel.transferTo` method and the Linux `splice(2)` syscall are the primitives.

## Serialization Costs

What you actually pay for, in approximate descending cost:

1. **Allocation** — every decode allocates a new object graph. GC pressure dominates CPU at high throughput. Zero-copy formats eliminate this.
2. **Reflection** — generic serializers (Java's `ObjectOutputStream`, Python's `pickle`) use reflection to walk the object graph, which is 10–100× slower than code-generated serializers.
3. **String parsing** — JSON's per-character loop, UTF-8 validation, and number parsing dominate. SIMD JSON parsers (simdjson) achieve 1–3 GB/s by parallelizing this work; conventional parsers do 100–300 MB/s.
4. **Field name lookup** — self-describing formats (JSON, MessagePack) carry field names on the wire; the parser must hash and look up each name. Schema-driven formats replace names with tag numbers, eliminating this cost.
5. **Memory bandwidth** — at high throughput, the bytes themselves become the bottleneck. Smaller wire formats win, which is why binary formats dominate at scale.

For a microservice doing 100k RPCs/sec with 1 KB payloads, switching from JSON to Protobuf typically halves CPU usage and reduces latency by 30–50%. For a data pipeline moving terabytes per day, switching from JSON to Parquet (columnar + dictionary encoding) reduces storage by 5–10× and query time by 10–100×.

## Security Considerations

- **Deserialization vulnerabilities** — language-native serializers (Java `ObjectInputStream`, Python `pickle`, Ruby `Marshal`, .NET `BinaryFormatter`) can construct arbitrary objects from the byte stream. Untrusted input deserialized with these is a remote code execution vulnerability. The rule: never deserialize untrusted input with a language-native serializer. Use a schema-driven format (Protobuf, Avro, JSON) where the parser constructs only the declared types.
- **Schema validation** — for JSON, validate incoming payloads against a JSON Schema before processing. Without validation, a missing field becomes a `null`-pointer exception deep in your business logic; with validation, it is rejected at the boundary.
- **Version negotiation** — for RPC protocols, the client and server must agree on a schema version. gRPC uses HTTP/2 headers (`Content-Type: application/grpc+proto`); REST APIs use versioning in the URL or a vendor MIME type (`application/vnd.example.v2+json`).
- **Billion laughs / entity expansion** — XML parsers can be DOSed with small payloads that expand exponentially (`<!ENTITY lol "lol">...<!ENTITY lol9 "&lol8;&lol8;...">`). All modern XML parsers have defenses (Xerces' `FEATURE_SECURE_PROCESSING`, libxml2's `XML_PARSE_HUGE` defaults to off); verify they are enabled.

## Choosing a Format

| Scenario | Recommended format | Why |
|----------|--------------------|-----|
| Public web API | JSON | Universal, debuggable, self-describing |
| Internal RPC at high QPS | Protobuf + gRPC | Schema enforcement, small wire, fast parse |
| Streaming data pipeline | Avro + Schema Registry | Schema evolution with compatibility guarantees |
| Columnar analytics storage | Parquet or ORC | Column-major layout, predicate pushdown, compression |
| Game / mobile messages | FlatBuffers | Zero-copy read, no allocation pressure |
| Real-time / capability RPC | Cap'n Proto | No encode/decode step, capability-based security |
| Configuration files | YAML or TOML | Human authoring, comments, type system |
| Untrusted data interchange | JSON with JSON Schema | No object construction, schema validation |
| Internal Kafka events | Avro or Protobuf | Schema Registry enforces compatibility |

## Interview Questions

**Q: What is the difference between backward and forward compatibility?**
Backward compatibility means new code can read old data — the new schema is a superset of the old. Forward compatibility means old code can read new data — the old schema ignores or defaults the new fields. A schema change that is both backward and forward compatible is "fully compatible": either side can upgrade independently.

**Q: How do Protobuf and Avro differ in schema evolution?**
Protobuf uses tag-number-based encoding (TLV); unknown fields are skipped, so adding or removing an optional field is both backward and forward compatible. Avro uses name-based encoding with the schema carried with the data; adding a field requires a default for backward compatibility, removing a field requires a default for forward compatibility, and type changes are limited to promotion paths (int → long → float → double → string). Both can achieve full compatibility, but Avro's rules are stricter.

**Q: What is zero-copy serialization and when does it matter?**
Zero-copy serialization means the serialized bytes can be read in place — no allocation, no parsing, no copy. FlatBuffers and Cap'n Proto achieve this by laying out the wire format exactly as the in-memory representation, using relative offsets instead of pointers. It matters when the read path is hot (high QPS, low latency) and when allocation pressure would otherwise dominate GC. For most business APIs, the added complexity is not worth it; for game engines, mobile apps, and high-throughput RPC, it is decisive.

**Q: Why is Java's `ObjectInputStream` dangerous?**
`ObjectInputStream.readObject` can construct arbitrary Java objects from the byte stream, including classes whose constructors or setters have side effects (opening files, making network connections, executing commands). A small malicious payload can trigger a chain of "gadget" classes (already on the classpath) that executes arbitrary code. The fix: never deserialize untrusted input with `ObjectInputStream`. Use a schema-driven format like Protobuf or JSON, where the parser only constructs the declared types.

**Q: How does a Schema Registry work?**
A Schema Registry is a service that stores schemas keyed by subject (typically a topic name for Kafka) and version. Producers register a schema before sending; the registry checks the new schema against the configured compatibility level (BACKWARD, FORWARD, FULL) versus the latest version. If the check fails, the producer's send fails. Consumers fetch schemas by ID embedded in each message payload. This makes schema evolution a first-class, enforced concern rather than a convention.

**Q: Why is JSON's number type a problem?**
JSON has a single numeric type, parsed as an IEEE 754 double. Integers larger than 2^53 lose precision when round-tripped through JavaScript's `JSON.parse` (which uses doubles exclusively). A 64-bit user ID like `9223372036854775807` arrives as `9223372036854776000`. The workaround is to send large integers as strings and parse them in the consumer; many APIs (Stripe, Twitter, GitHub) do this for IDs.

**Q: When would you use Avro vs Protobuf?**
Avro when you have a data-engineering flavor — Kafka topics with multiple consumers, schema stored alongside data, batch analytics. Protobuf when you have an RPC flavor — gRPC services, strongly typed APIs, generated stubs across many languages. Both can do either job; the ecosystems differ. Avro's Schema Registry is more mature for streaming; Protobuf's tooling is more mature for RPC.

**Q: What is the "Norway problem" in YAML?**
YAML 1.1 interpreted the unquoted strings `no`, `yes`, `on`, `off` as booleans. A configuration listing country codes (`- NO` for Norway) was parsed as a list with a single boolean `false`. YAML 1.2 fixed this, but many parsers (Ruby's psych, older Python yaml) implement 1.1 semantics, so the bug persists. The fix is to always quote strings that could be interpreted as booleans.

## Cross-References

- [gRPC](./api/grpc.md) — Protobuf over HTTP/2
- [REST](./api/rest.md) — JSON APIs
- [API Versioning](./api/versioning.md) — schema evolution at the API level
- [Kafka](./messaging/kafka.md) — Avro + Schema Registry
- [Data Formats](../data-engineering/data-formats.md) — at-rest formats (Parquet, ORC, Avro)
- [Protobuf vs FlatBuffers vs Cap'n Proto](../linux/sysprog/protobuf-flatbuf.md) — format-specific deep dive
- [I/O and Serialization](../programming-fundamentals/io-and-serialization.md) — beginner introduction

## References

- JSON RFC 8259 — https://www.rfc-editor.org/rfc/rfc8259
- CBOR RFC 8949 — https://www.rfc-editor.org/rfc/rfc8949
- Protocol Buffers Language Guide (proto3) — https://protobuf.dev/programming-guides/proto3/
- Apache Avro Specification — https://avro.apache.org/docs/current/specification/
- Apache Thrift — https://thrift.apache.org/docs/
- FlatBuffers documentation — https://google.github.io/flatbuffers/
- Cap'n Proto documentation — https://capnproto.org/
- Confluent Schema Registry compatibility configs — https://docs.confluent.io/platform/current/schema-registry/avro.html#compatibility
- simdjson — parsing gigabytes of JSON per second — https://github.com/simdjson/simdjson
- OWASP Deserialization Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- Martin Fowler — "Schema Evolution" (evolutionary database design) — https://martinfowler.com/articles/evodb.html
