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

## Event Time vs Processing Time: Why the Choice Is Load-Bearing

[Streaming basics](../distributed/messaging/messaging-streaming.md) introduce the three clocks; here is why the choice silently decides correctness. Consider a one-minute tumbling window counting user clicks. Traffic is steady at ~100 clicks/minute, and the pipeline runs 2–4 s behind. A burst of 300 clicks fires at 12:00:55 but the queue backs up for 70 s, so 120 of them are consumed between 12:01:00 and 12:02:10. A **processing-time** window splits one logical minute of traffic across two windows (12:00 gets 180, 12:01 gets 120) — no error is raised, no event is dropped, the dashboards simply disagree with reality for that minute. An **event-time** window keyed on the embedded timestamp assigns all 300 to 12:00, provided the watermark has not already closed it. The failure mode of processing time is *silent inaccuracy*, not loss, which is exactly why it survives code review.

Event time is not free. It requires every event to carry a trustworthy timestamp, and it shifts the hard problem from "when do I compute" to "when do I declare the input complete" — which is what watermarks formalize. The canonical treatment of this tradeoff space (correctness vs latency vs cost, over unbounded out-of-order data) is Akidau et al.'s dataflow model paper [1], which introduced the windowing/watermark/trigger vocabulary every modern engine implements.

## Watermarks Are a Business Decision, Not a Config Default

A watermark of "5 minutes" is a claim: *all events with event-time older than now−5m have been seen*. Choosing that number is a three-way tradeoff between result latency, completeness, and state cost, and the arithmetic is unforgiving because **windows are only correct if every event in them is punctual**, not just most events. If per-event lateness beyond the watermark is ε and a window contains n events, window correctness is (1−ε)^n:

| Per-event lateness ε | n = 10 | n = 100 | n = 1,000 |
|---|---|---|---|
| 1% | 90.4% complete windows | 36.6% | ≈0% |
| 5% | 59.9% | 0.6% | ≈0% |

Verified with python3: `(1−0.01)**100 = 0.366`. To get 99% correct windows with n = 100 events per window, per-event punctuality must be 0.9999 — a 0.01% late budget. This is why "we set watermark = 5 min and mostly it works" is not a correctness argument: high-volume windows demand per-event punctuality exponentially close to 1, or an explicit completeness story (retractions, reconcile jobs, or accepted inaccuracy). Two operational corollaries:

- **Idle sources freeze watermarks.** If one input partition goes quiet, a naive watermark computed as min-over-partitions stops advancing, and every downstream window stays open. Production engines have an explicit idleness timeout that excludes idle partitions — at the cost of silently accepting lateness from the excluded partition.
- **Watermark skew ≠ failure.** A watermark that occasionally jumps backward (upstream clock drift) must be tolerated; clamping it forward converts drift into permanent data loss for events older than the clamp.

## Window Mechanics: State Cost, Not Just Semantics

The window table in the [messaging/streaming page](../distributed/messaging/messaging-streaming.md) gives semantics; here is the state math. **Sliding windows amplify writes**: with window length W and slide S, each event contributes to W/S windows (W = 10 min, S = 1 min → 10 accumulator updates per event, and per-key live state proportional to everything seen in the last W). Sliding windows with S ≪ W are the classic cause of "the topology is fine at 1k events/s and falls over at 50k".

**Session windows** are the opposite problem: their count is *data-dependent* (one per user session), and a late event can **merge** two already-emitted sessions. Merging forces the engine to either (a) retract the earlier output and re-emit a merged one, or (b) block emission until the watermark passes the session gap — which couples your output latency to your worst-behaved users. In interviews, state that per-key session state grows with the longest-tail users, and the mitigation is a max session length cap (state bound) plus explicit retraction handling.

## State, Checkpoints, and Recovery Cost

Windowed aggregates are stateful, and state is what makes streaming engines hard to operate. Flink offers a **HashMapStateBackend** (state on JVM heap; fast, limited by memory and GC) and an **EmbeddedRocksDBStateBackend** (state on local disk with serialized access; unbounded-ish size, higher per-access cost), with **incremental checkpoints** for the RocksDB backend so each checkpoint uploads only changed SSTables rather than the full state [2]. The design of those consistent, non-blocking state snapshots traces to Chandy–Lamport-style asynchronous snapshots — see [distributed snapshots](../distributed/advanced/distributed-snapshots.md) for the algorithm.

Checkpointing policy is a latency/recovery tradeoff: a checkpoint every 30 s means a crash replays ≤ 30 s of source data, but every 30 s the pipeline pauses (aligned mode) or absorbs I/O pressure (unaligned mode) to persist state. Large state (hundreds of GB) turns checkpoint duration — not throughput — into the scaling wall, because checkpoint duration grows with state size and the job spends more of its life snapshotting than processing. Mitigations, in the order you should try them: incremental checkpoints, state TTL (expire keys nobody revisits), shrinking window W, and key-space splitting.

## Exactly-Once: The Fine Print

"Exactly-once" in stream processing has a precise, narrower meaning than marketing suggests. From the Flink documentation (verbatim): *"when the ideal situation is described as exactly once this does not mean that every event will be processed exactly once. Instead, it means that every event will affect the state being managed by Flink exactly once."* [3] Side effects (writes to databases, emails, REST calls) are outside that guarantee unless the sink cooperates. End-to-end exactly-once therefore requires two properties, again verbatim: *"your sources must be replayable, and your sinks must be transactional (or idempotent)"* [3].

Concretely: replayable source = Kafka with offsets stored in the checkpoint; transactional sink = Kafka transactions or a DB upsert keyed by (window, key); idempotent sink = writes that can be re-executed without changing the result. This is the same at-least-once + dedup pattern as [exactly-once delivery](../distributed/messaging/messaging-streaming.md) in brokers, and the same reason billing pipelines use [idempotent rollup writes](../interview/system-design/real-world/billing-metering.md). If your sink is an external SaaS API with no idempotency keys, you have at-least-once, whatever the engine config says.

## Late Data, Side Outputs, and Retractions

Three honest options exist for events arriving after the watermark closed their window, and mature designs use all three:

1. **Side output / DLQ**: route too-late events to a dead-letter stream for batch reconciliation. Keeps the streaming aggregate clean and auditable.
2. **Update results** (retractions/upserts): the engine emits a correction row when a late event changes an already-emitted window. Correct, but every downstream consumer must be an upsert store, not a log — a real architectural cost.
3. **Allowed lateness**: keep window state for L past watermark close and update results in place as stragglers arrive, emitting the final result only after the lateness horizon. Trades state retention and result delay for fewer retractions.

The reconcile-with-batch pattern (recompute yesterday's windows from the [batch pipeline](./batch-processing.md) and overwrite) is the pragmatic resolution of the completeness math above: streaming gets you freshness, the nightly recompute gets you a stated accuracy guarantee.

## Reprocessing and the Catch-Up Budget

Replay is the streaming system's version of re-running a batch job — bounded by log retention. The capacity arithmetic interviewers probe: to reprocess 24 h of history in a 2 h maintenance window while also serving live traffic, the job needs (24/2) = 12× steady-state throughput for the reprocessing lanes plus 1× for live, ≈ **13× total** — check partition counts and downstream sink capacity before promising it. Three things that break replays in practice: state schema changed since the snapshot you would restore (plan for compatibility or rebuild state from the log); downstream sees the replay as duplicates (transactional/idempotent sinks again); and retention shorter than the reprocessing horizon silently truncates your history — set retention from the *backfill* requirement, not the steady-state one. Stream-table duality ties this together: a changelog *is* a table under version control, which is why the same replay machinery underlies both stream reprocessing and [materialized view maintenance](../dbms/advanced/incremental-view-maintenance.md).

## Interview Questions

**Q1 (mid): "Our 1-minute windows show ~15% of windows disagree with the database by a few events. Watermark is 2 minutes. Diagnose."**
Strong answers: reframe with the (1−ε)^n math — at ~600 events/min and ε even 0.03%, most windows contain a straggler; the 2-minute watermark is a latency policy, not a completeness guarantee. Checkpoints/restarts replay *within* watermark assumptions but don't fix stragglers. Propose: measure the actual lag distribution, then either raise watermark to cover p999 lag (pay latency), add allowed-lateness with retractions (pay state + upsert sinks), or accept and reconcile against batch. Junior answers jump to "increase the watermark" without the per-event vs per-window distinction; senior answers quantify the tradeoff.

**Q2 (senior): "Design the checkpointing strategy for a 500 GB-state enrichment job with a 10-minute RPO."**
Expected: state can't be heap (500 GB) → RocksDB backend + incremental checkpoints; checkpoint interval interacts with RPO (interval ≤ 10 min; realistically 1–5 min for faster recovery, but watch checkpoint duration < interval or the job never progresses); unaligned checkpoints to avoid backpressure-induced timeout; restore time is the hidden cost (base snapshot + chain of diffs); and if 500 GB is mostly TTL-able session state, argue state shrink first — the cheapest checkpoint is the one with less state.

**Q3 (mid): "Exactly-once is configured end to end, but finance still sees occasional double-counted revenue events. Where does the guarantee leak?"**
Look for: side effects outside the transactional boundary (sink is Kafka-transactional but the downstream *consumer* of that topic reads with autocommit and re-processes), replay of a window after state restore without a transactional sink on the DB path, events that were *deduplicated at the engine but produced twice at the source* (producer retries without idempotence — the leak is upstream of the engine). The general principle: exactly-once claims compose only at transactional boundaries; any hop with at-least-once semantics needs its own dedup key.

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Flink Documentation](https://flink.apache.org/docs/)
- [Streaming Systems — Akidau et al.](https://www.oreilly.com/library/view/streaming-systems/9781491983867/)
1. Akidau, Bradshaw, Chambers, Chernyak, Lax, McNeely, "The Dataflow Model: A Practical Approach to Balancing Correctness, Latency, and Cost in Massive-Scale, Unbounded Out-of-Order Data Processing," *PVLDB* 8(12), 2015. DOI: [10.14778/2824032.2824076](https://doi.org/10.14778/2824032.2824076) — Crossref-verified (title/authors/venue) and DOI resolved via api.crossref.org this session.
2. Apache Flink, "State Backends" (HashMapStateBackend, EmbeddedRocksDBStateBackend, incremental checkpoints) — <https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/state/state_backends/> — fetched in full this session.
3. Apache Flink, "Fault Tolerance / Exactly Once Guarantees" (verbatim quotes above) — <https://nightlies.apache.org/flink/flink-docs-stable/docs/learn-flink/fault_tolerance/> — fetched in full this session.

## Cross-References

- [Messaging & Streaming](../distributed/messaging/messaging-streaming.md) — broker internals, delivery semantics, watermark basics, DLQ patterns
- [Distributed Snapshots](../distributed/advanced/distributed-snapshots.md) — Chandy–Lamport algorithm behind consistent checkpoints
- [Batch Processing](./batch-processing.md) — window/batch reconcile pattern, backfill, DAG scheduling
- [Data-Intensive Systems HLD](../interview/system-design/hld/data-intensive.md) — Lambda vs Kappa architecture tradeoffs
- [Incremental View Maintenance](../dbms/advanced/incremental-view-maintenance.md) — the query-side analog: maintaining aggregates as inputs change
- [Billing & Metering](../interview/system-design/real-world/billing-metering.md) — production at-least-once + idempotent rollup design
