# Apache Flink

Apache Flink is an open-source stream processing framework, originally developed at the Technical University of Berlin (Stratosphere project, 2010) and donated to Apache in 2014. Flink is designed for true stream processing (event-at-a-time, not micro-batch like Spark Streaming), with strong consistency guarantees (exactly-once semantics), stateful processing, and event-time semantics. This page covers the architecture, the state backends, the checkpoint mechanism, and the comparison to Spark Structured Streaming.

## The Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  JobManager (coordinator)                                │
│  - Scheduler (assigns tasks to TaskManagers)             │
│  - Checkpoint coordinator (triggers periodic checkpoints)│
│  - Job graph holder (the DAG of operators)              │
└─────────────────────────────────────────────────────────┘
        │                              │
        │ deploy tasks                 │ checkpoint barriers
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  TaskManager 1        │    │  TaskManager 2        │
│  - Task slots (4)     │    │  - Task slots (4)     │
│  - State backend       │    │  - State backend       │
│  - Network stack       │    │  - Network stack       │
└──────────────────────┘    └──────────────────────┘
        │                              │
        ▼                              ▼
    Source (Kafka)              Source (Kafka)
```

The JobManager coordinates; TaskManagers execute. State and checkpoints are managed per-task on the TaskManagers.

## Stream Processing Model

Unlike Spark Streaming's micro-batch (which processes batches of N seconds), Flink processes events one at a time:

```python
# PyFlink example
env = StreamExecutionEnvironment.get_execution_environment()
env.enable_checkpointing(60000)  # checkpoint every 60s

# Read from Kafka
kafka_source = KafkaSource.builder() \
    .set_bootstrap_servers("kafka:9092") \
    .set_topics("events") \
    .set_group_id("flink-consumer") \
    .set_value_deserializer(SimpleStringSchema()) \
    .build()

ds = env.from_source(kafka_source, WatermarkStrategy.no_watermarks(), "kafka-source")

# Process events
result = ds.map(lambda x: parse(x)) \
          .filter(lambda x: x.is_valid) \
          .key_by(lambda x: x.user_id) \
          .window(SlidingEventTimeWindows.of(Time.minutes(5), Time.minutes(1))) \
          .reduce(lambda a, b: a + b)

# Sink to Kafka
result.execute()
```

Flink's stream processing:
- **Per-event processing**: each event flows through operators immediately, no batching.
- **Event time semantics**: watermarks track the maximum event time seen; late events are handled.
- **Stateful processing**: each operator maintains state (e.g., per-key windows, per-session state).

## State Backends

Flink stores operator state in a "state backend". Three options:

### MemoryStateBackend (default)

State is in JVM heap. Limited by heap size (~32 GB typical). Fast but doesn't survive TaskManager failure (state is lost; must be re-loaded from checkpoint).

### FsStateBackend

State is in JVM heap during runtime; checkpoints are written to a filesystem (HDFS, S3). Survives TaskManager failure.

### RocksDBStateBackend

State is in RocksDB (on local disk). Survives TaskManager failure (RocksDB is persistent). Slower than in-memory (RocksDB adds ~10 ms per state access) but supports terabytes of state.

```python
env.set_state_backend(RocksDBStateBackend("s3://my-bucket/flink/checkpoints"))
```

For production stateful workloads, RocksDB is the standard. Memory is for testing; Fs is for small states.

## Checkpointing for Exactly-Once

Flink's exactly-once guarantee is via the Chandy-Lamport distributed snapshot algorithm:

```text
1. JobManager triggers a checkpoint at time T.
2. Source operators inject a "checkpoint barrier" into the stream.
3. When an operator sees the barrier:
   a. Stops processing new events (waits for all in-flight events to finish).
   b. Snapshots its state to the state backend.
   c. Forwards the barrier downstream.
4. When all operators have snapshot, the checkpoint is complete.
```

If a TaskManager fails, the JobManager restarts the failed tasks and re-reads state from the last checkpoint. Source operators rewind to the checkpoint's offset in Kafka; downstream operators re-process events.

The "exactly-once" guarantee: each event is processed exactly once across failure recovery. The "at-least-once" guarantee without checkpointing: events may be re-processed on failure.

For "exactly-once" sink semantics, the sink must support transactions (e.g., Kafka transactions, two-phase commit for databases). Flink's `TwoPhaseCommitSinkFunction` provides this abstraction.

## Event Time and Watermarks

Real-world events arrive out of order (network delays, retries, batch processing). Flink processes events by "event time" (the time the event occurred), not "processing time" (when Flink sees it).

A watermark is a timestamp `W` such that Flink assumes no more events with event time < `W` will arrive. The watermark is propagated through the stream; operators use it to close windows.

```python
# Generate watermarks: bounded out-of-orderness of 5 seconds
watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_seconds(5)) \
    .with_timestamp_assigner(lambda event, _: event.timestamp)

ds = env.from_source(kafka_source, watermark_strategy, "kafka-source")
```

For a 5-second bounded out-of-orderness, events with timestamp within 5 seconds of the current max are processed normally; events more than 5 seconds late are dropped (or sent to a side output for late events).

## Windows

Flink groups events into windows for aggregation:

- **Tumbling windows**: fixed-size, non-overlapping. Each event belongs to one window.
- **Sliding windows**: fixed-size, overlapping. Each event belongs to multiple windows.
- **Session windows**: variable-size, based on inactivity gaps.

```python
# 5-minute tumbling window per user
result = ds.key_by(lambda x: x.user_id) \
          .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
          .reduce(lambda a, b: a + b)

# 5-minute window sliding every 1 minute
result = ds.key_by(lambda x: x.user_id) \
          .window(SlidingEventTimeWindows.of(Time.minutes(5), Time.minutes(1))) \
          .reduce(lambda a, b: a + b)

# Session window with 10-minute gap
result = ds.key_by(lambda x: x.user_id) \
          .window(EventTimeSessionWindows.with_gap(Time.minutes(10))) \
          .reduce(lambda a, b: a + b)
```

## Comparison to Spark Structured Streaming

| Aspect | Flink | Spark Structured Streaming |
|--------|--------|------------------------------|
| Model | True streaming (event-at-a-time) | Micro-batch (default) or continuous |
| Latency | <100 ms | ~1 sec (micro-batch) |
| State backends | Memory, FS, RocksDB | Memory (limited) |
| Checkpointing | Chandy-Lamport | Driver-driven |
| Exactly-once | Yes (with transactional sink) | Yes (with sink support) |
| Complex event processing | Native (CEP library) | Limited |
| Production users | Alibaba, Uber, Netflix | Many |

Flink's true streaming is faster (sub-second latency) but more complex to deploy. Spark's micro-batch is simpler (reuses the Spark SQL engine) but slower.

## Production Use Cases

### Real-time Analytics

Count user events per minute, alert on anomalies:

```python
events = env.from_source(kafka_source, watermark_strategy, "kafka-source")

aggregated = events.key_by(lambda e: e.user_id) \
    .window(TumblingEventTimeWindows.of(Time.minutes(1))) \
    .aggregate(SumAggregator())

# Sink to ClickHouse for dashboards
aggregated.add_sink(ClickHouseSink())
```

### Streaming ETL

Read from Kafka, transform, write to a data warehouse:

```python
events = env.from_source(kafka_source, watermark_strategy, "kafka-source")

transformed = events.filter(lambda e: e.is_valid) \
    .map(lambda e: enrich(e)) \
    .key_by(lambda e: e.session_id) \
    .map(StatefulEnrichment())  # joins with state

# Sink to S3 (Parquet)
transformed.add_sink(S3Sink("s3://my-bucket/events/"))
```

### Complex Event Processing (CEP)

Detect patterns in event streams:

```python
from pyflink.cep import CEP
from pyflink.cep.pattern import Pattern

# Detect: failed login followed by successful login within 5 minutes
pattern = Pattern.begin("failed").where(lambda e: e.event_type == "login_failed") \
    .followed_by("success").where(lambda e: e.event_type == "login_success") \
    .within(Time.minutes(5))

alerts = CEP.pattern(events.key_by(lambda e: e.user_id), pattern) \
    .select(lambda pattern: format_alert(pattern))
```

### Fraud Detection

Real-time scoring of transactions against a model:

```python
transactions = env.from_source(kafka_source, watermark_strategy, "kafka-source")

# Join with user state
scored = transactions.key_by(lambda t: t.user_id) \
    .map(UserScoringFunction())  # uses stateful ML model

# Flag high-risk transactions
high_risk = scored.filter(lambda t: t.score > 0.8)
high_risk.add_sink(AlertSink())
```

## Common Pitfalls

1. **Forgetting to enable checkpointing.** Without checkpoints, recovery re-processes all events from the last savepoint. Set `env.enable_checkpointing(60000)` for 60s intervals.

2. **Setting checkpoint interval too low.** Checkpoints pause processing; intervals below 30 seconds waste CPU. Use 1-5 minutes for production.

3. **Using MemoryStateBackend for production.** It's fast but doesn't survive TaskManager failure. Use RocksDB.

4. **Forgetting to set parallelism correctly.** Default parallelism is the cluster's default; per-job parallelism should match the source's partitions (e.g., Kafka topic with 32 partitions → parallelism 32).

5. **Forgetting that watermark determines event time.** A late watermark triggers window closures; if too aggressive, events are dropped. Tune the bounded out-of-orderness to your data's actual delay distribution.

6. **Forgetting that state cleanup is manual.** State grows over time; for time-bounded state, set a TTL. Otherwise state fills disk.

## References

- Carbone et al., "[Apache Flink: Stream and Batch Processing in a Single Engine](https://flink.apache.org/news/2015/03/13/preview-flink-0.9.0.html)" (Data Engineering Bulletin 2015)
- [Flink documentation](https://nightlies.apache.org/flink/flink-docs-stable/)
- [Flink state backends](https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/state_backends/)
- [Flink checkpoints](https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/checkpoints/)
- Carbone et al., "[Lightweight Asynchronous Snapshots for Distributed Dataflows](https://arxiv.org/abs/1506.08603)" (2015) — Flink's checkpoint algorithm
- [Flink vs Spark Streaming (Alibaba blog)](https://www.alibabacloud.com/blog/flink-vs-spark-streaming)
- [LWN: Flink overview (2020)](https://lwn.net/Articles/815528/)
