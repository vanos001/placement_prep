# Temporal Databases, Streaming & Time-Series

This chapter covers databases that manage time-centric data: temporal databases (tracking history and valid time), time-series databases (sensor/metric data), and stream processing systems (real-time event processing).

## Temporal Databases

### Why Temporal?

Regular databases capture the **current state**. Temporal databases additionally track **when** each fact was true — enabling queries like "what was Alice's salary on January 1st, 2023?" or "show me all changes to this record in the last month."

### Valid Time vs. Transaction Time

| Time Dimension | Meaning | Who Controls | Example |
|---------------|---------|-------------|----------|
| **Valid time** | When the fact was true in the real world | Application/business | Employee salary was $100K from Jan-Jun 2023 |
| **Transaction time** | When the fact was recorded in the database | System | The salary change was entered on June 15, 2023 |

A **bitemporal** database tracks both dimensions simultaneously.

### Bitemporal Data Model

In a bitemporal table, each row has a **valid-time period** `[V_start, V_end)` and a **transaction-time period** `[T_start, T_end)`:  

```sql
-- Bitemporal employee salary history
CREATE TABLE employee_salary (
    emp_id      INT,
    salary      DECIMAL(10,2),
    valid_from  DATE,       -- when this salary became effective
    valid_to    DATE,       -- when this salary stopped being effective
    tx_start    TIMESTAMP,  -- when this record was inserted
    tx_end      TIMESTAMP   -- when this record was superseded/removed
);

-- Query: What was Alice's salary according to the database on March 1, 2023?
SELECT salary, valid_from, valid_to
FROM employee_salary
WHERE emp_id = 1
  AND tx_start <= '2023-03-01' AND (tx_end IS NULL OR tx_end > '2023-03-01')
  AND valid_from <= '2023-03-01' AND valid_to > '2023-03-01';

-- Query: What salary was actually in effect on March 1, 2023 (current state)?
SELECT salary
FROM employee_salary
WHERE emp_id = 1
  AND tx_end IS NULL  -- current transaction-time state
  AND valid_from <= '2023-03-01' AND valid_to > '2023-03-01';
```

### Temporal Query Types

| Query Type | SQL (SQL:2011 standard) | Meaning |
|-----------|------------------------|---------|
| **AS OF** | `SELECT ... FROM table FOR SYSTEM_TIME AS OF t` | State at time t |
| **FROM TO** | `FOR SYSTEM_TIME FROM t1 TO t2` | State during period |
| **BETWEEN** | `FOR SYSTEM_TIME BETWEEN t1 AND t2` | State during inclusive period |
| **ALL** | `FOR SYSTEM_TIME ALL` | Full history |
| **Valid-time** | `FOR VALID_TIME AS OF t` | What was true at real-world time t |

**Systems with temporal support**: PostgreSQL (via extensions like `temporal_tables`), MariaDB (system-versioned tables), MS SQL Server (temporal tables with `SYSTEM_VERSIONING`), Oracle (Flashback Query).

### Temporal Indexing

Temporal queries typically filter on **time ranges**, requiring specialized indexes:
- **Time-partitioned tables**: One partition per day/week/month. `AS OF t` prunes to the relevant partition. Used by most time-series databases.
- **Append-only B-trees with time-sorted keys**: Keys are `(entity_id, timestamp)`, enabling efficient range scans of an entity's history.
- **LSM trees**: Natural fit for append-only temporal data (timestamps are monotonically increasing). Compaction preserves temporal ordering.

> **Interview Angle**: "What is a bitemporal database and why would you use one?" — Explain valid time vs. transaction time, give the example of financial auditing or GDPR compliance, and sketch the bitemporal table schema with two time ranges.

## Streaming Databases

### Stream vs. Batch Processing

| Aspect | Batch | Stream |
|--------|-------|--------|
| Data model | Finite, bounded dataset | Infinite, unbounded sequence |
| Processing | Scheduled jobs (hourly/daily) | Continuous, event-driven |
| Latency | Minutes to hours | Milliseconds to seconds |
| Fault tolerance | Retry entire job | Checkpoint + replay |
| State | External (write to DB) | Internal (in-memory state) |
| Examples | Spark, Hadoop, SQL batch jobs | Flink, Kafka Streams, ksqlDB |

### Event Time vs. Processing Time

``n```
  Event Timeline:   e1(t=10:00)  e2(t=10:05)  e3(t=10:08)  e4(t=10:15)
  Process Timeline:  e1(10:02)    e2(10:06)    e4(10:16)     e3(10:20)    ← out of order!
```

- **Event time**: When the event actually occurred (embedded in the event payload). This is the semantically correct time for business logic.
- **Processing time**: When the event was processed by the system. Easier to use but meaningless for correctness.
- **Watermarks**: A watermark is a timestamp assertion: "no events with event time < W will arrive after this point." Watermarks enable the system to know when it's safe to emit results for a time window.

### Window Types

| Window Type | Definition | Example |
|------------|-----------|----------|
| **Tumbling** | Fixed-size, non-overlapping | Count events per 5-minute bucket |
| **Sliding** | Fixed-size, overlapping | Average over last 10 minutes, updated every 1 minute |
| **Session** | Activity-gap-based | Group events per user session (30s gap = new session) |
| **Global** | All data | Total count since start |

### Stream Processing Architectures

| System | Model | State | Exactly-Once | SQL? |
|--------|-------|-------|-------------|------|
| **Apache Flink** | Dataflow (operator DAG) | RocksDB-backed keyed state | Yes (2PC + aligned barriers) | Flink SQL |
| **Kafka Streams** | Processor topology (DAG) | Local state stores (RocksDB) | Yes (transactional Kafka) | ksqlDB |
| **Spark Structured Streaming** | Micro-batch + continuous | Checkpointed state | Yes (write-ahead log) | Spark SQL |
| **Materialize** | Differential dataflow | In-memory, persistent | Yes (deterministic) | Full SQL |
| **RisingWave** | Streaming SQL engine | Hummock (LSM on object store) | Yes | Full PostgreSQL SQL |
| **Arroyo** | Dataflow with temporal join | In-memory + SSD | Yes | SQL |

### State Management in Streams

Stateful stream processing requires fault-tolerant state:

```
Keyed State: per-key state (e.g., per-user session, per-sensor count)
  ┌─────────┐
  │ key: user_1 → count: 42, last_seen: 10:05 │
  │ key: user_2 → count: 7, last_seen: 10:08  │
  └─────────┘
  Backed by RocksDB or an in-memory hashmap.
  Checkpointed periodically to durable storage.

Operator State: non-keyed state (e.g., window buffer)
  ┌──────────────┐
  │ window [10:00, 10:05): [e1, e2, e3]  │
  │ window [10:05, 10:10): [e4, e5]     │
  └──────────────┘
```

**Chandy-Lamport-style barriers** (Flink): A special "barrier" marker is injected into the stream. When all input partitions have received the barrier at an operator, the operator snapshots its state and sends the barrier downstream. This provides **exactly-once** semantics with low overhead.

## Time-Series Databases

### What is Time-Series Data?

Time-series data consists of **timestamped numerical values** from sensors, metrics, or financial instruments:

```
temperature,host=server-1 value=72.5 1704067200

cpu_usage,host=server-1,region=us-east value=85.2 1704067201
```

### Time-Series Database Design

| Design Aspect | Approach | Rationale |
|--------------|----------|-----------|
| **Partitioning** | By time range (day/week) + series ID | Time-range queries scan sequential partitions; series ID enables multi-series queries |
| **Compression** | Delta-of-delta encoding for timestamps, XOR for floats (Gorilla paper) | 12x compression for metrics data |
| **Storage** | Columnar per metric, append-only | Write-optimized, enables efficient range scans |
| **Indexing** | Inverted index (series ID → series metadata) + time-partitioned data | "Find all series with tag host=server-1" uses inverted index |
| **Downsampling** | Pre-aggregated rollups (1m → 1h → 1d) | Reduces long-range query cost |

### Gorilla Compression (Facebook, 2015)

Facebook's Gorilla system introduced **XOR-based floating-point compression** that achieves ~12x compression on time-series data:

1. **XOR current value with previous value**: Most changes are small, so XOR produces leading zeros.
2. **Encode leading zeros + significant bits**: A variable-length encoding stores only the changed bits.
3. **Delta-of-delta for timestamps**: Store the difference between consecutive timestamp differences. Most timestamps are evenly spaced, so this is often 0.

### TSDB Comparison

| System | Storage | Query Language | Distributed | Compression | Use Case |
|--------|---------|--------------|-------------|-------------|----------|
| **InfluxDB** (TSM engine) | TSM (columnar LSM) | InfluxQL / Flux | Enterprise | Gorilla-like | General metrics |
| **TimescaleDB** | PostgreSQL (hypertables) | Full SQL | Yes (multinode) | Columnar compression | SQL-compatible TSDB |
| **Prometheus** | Local TSDB | PromQL | Federation only | Gorilla-like | Monitoring/alerting |
| **VictoriaMetrics** | Custom LSM | MetricsQL (PromQL+) | Yes (cluster) | Gorilla-like | High-cardinality metrics |
| **ClickHouse** | MergeTree (columnar) | SQL | Yes | LZ4/ZSTD + columnar | General analytics + TS |

### Hypertables (TimescaleDB)

TimescaleDB extends PostgreSQL with **hypertables**: transparently partitioned tables where data is automatically sharded by time. The user creates a regular table and converts it:

```sql
CREATE TABLE metrics (
    time        TIMESTAMPTZ    NOT NULL,
    sensor_id  INT,
    value      DOUBLE PRECISION
);

SELECT create_hypertable('metrics', 'time', chunk_time_interval => INTERVAL '1 day');

-- This automatically creates daily chunks:
-- _hyper_1_1_chunk (time: 2024-01-01 to 2024-01-02)
-- _hyper_1_2_chunk (time: 2024-01-02 to 2024-01-03)
-- ...

-- Queries are automatically pruned to relevant chunks
SELECT AVG(value) FROM metrics
WHERE time > NOW() - INTERVAL '7 days' AND sensor_id = 42;
-- Only scans 7 chunks instead of the full table
```

> **Interview Angle": "How does TimescaleDB differ from InfluxDB?" — TimescaleDB is built on PostgreSQL with full SQL, ACID transactions, and JOINs. InfluxDB is purpose-built with InfluxQL/Flux, better write throughput for pure time-series, but limited SQL. For mixed workloads (relational + time-series), TimescaleDB wins. For high-ingest monitoring, InfluxDB or VictoriaMetrics may be better.

## References

- Snodgrass, R.T. "Developing Time-Oriented Database Applications in SQL." Morgan Kaufmann, 1999.
- Johnson, T. et al. "Gorilla: A Fast, Scalable, In-Memory Time Series Database." VLDB, 2015.
- Akidau, T. et al. "The Dataflow Model: A Practical Approach to Balancing Correctness, Latency, and Cost in Stream Processing." PVLDB, 2015. (Flink)
- Armbrust, M. et al. "Structured Streaming: A Declarative API for Real-Time Applications in Apache Spark." SIGMOD, 2018.