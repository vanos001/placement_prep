# Data Formats

Data format is an architecture decision, not just a file-extension choice. A
format determines schema evolution, encoding cost, scan performance, type
fidelity, interoperability, and how easily a pipeline can recover from bad
records.

## Row-oriented versus column-oriented

| Layout | Best for | Trade-off |
|---|---|---|
| Row-oriented | Point reads and whole-record updates | Reads unused columns during analytics |
| Column-oriented | Analytics scanning a few columns across many rows | More work for single-record updates |
| Key-value/binary | Low-latency service payloads | Less self-describing and queryable |
| Log/event format | Append-only streams and replay | Consumers must handle evolution and ordering |

A data lake commonly stores columnar Parquet or ORC files, while an API may
use JSON and a high-throughput RPC may use Protobuf.

## Common formats

### CSV

CSV is easy to inspect and widely supported, but it has weak typing, ambiguous
nulls, escaping edge cases, and no reliable schema unless an external contract
exists. Never parse quoted CSV with `cut -d,` when fields may contain commas,
quotes, or newlines.

### JSON

JSON is human-readable and flexible. It is useful at API boundaries and for
small event payloads, but repeated field names and text numbers increase size.
Schema validation and explicit versioning are important when JSON crosses team
or service boundaries.

### Avro

Avro stores a compact binary value and a separate schema. The writer schema and
reader schema can evolve under compatibility rules. It is common in Kafka and
streaming systems where a schema registry governs versions.

### Protobuf

Protocol Buffers define typed messages and field numbers. Adding fields is
usually compatible when old field numbers are never reused and consumers safely
ignore unknown fields. Renaming a field is not the same as changing its field
number; preserve numbers across versions.

### Parquet

Parquet is a columnar file format designed for analytical workloads. It stores
column chunks, pages, encodings, compression, statistics, and optional indexes.
Partitioning and row-group sizing strongly affect scan cost.

### ORC

ORC is another columnar analytical format with type information, stripes,
indexes, and compression. Hive and Hadoop ecosystems use it heavily; the right
choice depends on engine support and existing table layout.

## Schema evolution rules

- Add optional fields with safe defaults.
- Never reuse a removed field number in Protobuf or an incompatible name in a
  registry-governed schema.
- Distinguish missing, null, zero, and empty string.
- Keep readers tolerant before writers begin emitting a new field.
- Version events by meaning, not by every implementation change.
- Test old-reader/new-writer and new-reader/old-writer combinations.
- Record ownership and a deprecation deadline for fields.

## Analytics tuning checklist

- Choose columnar storage when queries scan many rows but few columns.
- Partition on a bounded, frequently filtered dimension; avoid millions of tiny
  partitions.
- Target useful row-group/file sizes rather than one file per event.
- Collect statistics so the engine can skip row groups.
- Compress after choosing encodings; compression ratio is workload-dependent.
- Compact small files and monitor skewed partitions.
- Keep a raw immutable zone so corrected transformations can be replayed.

## Interview questions

**Why is Parquet faster than CSV for a column query?**

Parquet stores columns separately, so the engine can read only the requested
columns and skip row groups using statistics. CSV requires parsing rows and
usually scans the entire file.

**When would JSON be the right choice?**

At a human-facing or loosely coupled API boundary where readability and broad
interoperability matter more than compactness. Use a schema and limits when it
becomes a durable event contract.

**How do you evolve a Protobuf message?**

Add fields with new numbers, retain old numbers as reserved, avoid changing the
type incompatibly, and test mixed-version readers and writers.

## Cross-references

- [Batch Processing](./batch-processing.md)
- [Stream Processing](./stream-processing.md)
- [Data Engineering Fundamentals](./fundamentals.md)
- [Schema and data quality](./data-quality.md)
- [Parquet](https://parquet.apache.org/docs/)
- [Apache Avro specification](https://avro.apache.org/docs/current/specification/)
- [Apache ORC](https://orc.apache.org/specification/)
- [Protocol Buffers language guide](https://protobuf.dev/programming-guides/proto3/)
- [Apache Arrow](https://arrow.apache.org/docs/)
