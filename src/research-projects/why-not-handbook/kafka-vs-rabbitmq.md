# Kafka vs RabbitMQ: What Does the Broker Promise — a Log or a Queue?

## Overview

"Kafka or RabbitMQ?" is usually argued as throughput versus flexibility, and the framing pre-decides the answer. The sharper question is: **what does the broker do with a record after it acknowledges that record?** Kafka appends it to a durable, partitioned, ordered log; consumption is a pointer movement that reader groups track themselves, so records survive being consumed and can be re-read for as long as retention keeps them. RabbitMQ enqueues it into a queue whose job is work distribution: when the consumer acknowledges, the message is gone, and the broker — not the consumer — was tracking the delivery the whole time. Everything else follows from that divergence: replay versus one-shot delivery, where delivery state lives, what backpressure looks like, and what "the message was processed" can even mean.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **Kafka sells a log — retention, replay, and per-key order as first-class properties; RabbitMQ sells a queue — per-message acknowledgment, rich routing, and delivery state managed by the broker.** Neither is "faster" or "more reliable" in the abstract. Kafka's log makes consumers stateful and the replay window a design parameter; RabbitMQ's queues make the broker stateful and redelivery an acknowledgment contract. Choose wrong and the cost is the operations story: lag graphs where queue depths were expected, or a hand-rolled replay layer where `offset reset` already existed.

## Step 1: The Problem and Its Constraints

The abstract shape: producers emit records, a broker intermediates, consumers act on them. Constraints that decide which broker contract fits:

- **Does the data need to outlive its first consumption?** Event sourcing, audit trails, feeding a new consumer months later, rebuilding a search index from source events — all require the broker to retain records after delivery. A queue that deletes on ack cannot do this at any configuration value.
- **Is each record a unit of work or a fact?** Work items (process this upload, send this email) want assignment, acknowledgment, and removal — the queue contract. Facts (order placed, user signed up) want to be observable by many independent readers — the log contract.
- **Ordering scope.** Is a strict order needed across all producers, per key (per entity), or not at all? None of the systems give global order cheaply; the scope narrows the design.
- **Routing complexity.** Does the same message need to land on different queues based on content (severity, tenant, topic)? RabbitMQ's exchange-binding model is a publish-time feature Kafka deliberately lacks.
- **Latency shape versus aggregate throughput.** Thousands of small messages with low per-message latency is a different target than hundreds of megabytes per second of streaming reads.
- **Consumer fleet shape.** One pool of interchangeable workers, or many independent applications each maintaining its own position in the same stream?

## Step 2: The Mechanisms

### Kafka: the replicated log

A Kafka [topic](https://kafka.apache.org/documentation/) is split into partitions; each partition is an append-only, replicated log with monotonically increasing offsets. Producers append; the broker acks at the configured durability level (`acks=all` waits for the in-sync replica set). Consumers do not remove anything — a consumer group reads a partition by moving an offset pointer, and the group coordinator tracks which member owns which partitions. The mechanisms that matter:

- **Delivery state lives on the consumer.** Offsets are committed (by the consumer, to a broker-kept log) whenever the consumer chooses. Commit-after-processing gives at-least-once; commit-before-processing gives at-most-once; the broker never knows whether a record was actually handled. Replay is therefore free: reset the offset, re-read anything within retention. The price is that every consumer must be idempotent, because the crash window between "processed" and "committed" always exists.
- **Retention is independent of consumption.** Records expire by time or size, not because someone read them. This makes the log simultaneously a buffer, a history, and a source of truth for rebuilding derived state — the property [event-driven pipelines](./app-events-vs-cdc.md) lean on.
- **Ordering is per partition.** Producers route by key, so all records for one entity land on one partition and are strictly ordered there; cross-partition order does not exist. Parallelism equals partition count — a ceiling set at topic-creation time.
- **Throughput is the design center.** Sequential disk appends, message batching, compressed micro-batches, and consumer-side fetch loops make the common case a large-block copy. Per-message latency is intentionally traded for batch efficiency, and [consumer rebalancing](../../distributed/messaging-internals/kafka-consumer-rebalancing.md) reassigns partitions when membership changes.

### RabbitMQ: queues and acknowledgments

RabbitMQ is a queue system built around the AMQP model: publishers send to an **exchange**, and **bindings** copy messages onto one or more **queues** according to routing keys (direct, topic, fanout, and header matching). Consumers subscribe to queues; the broker delivers, and tracks each unacknowledged delivery itself. The mechanisms that matter:

- **Delivery state lives in the broker.** Until a consumer sends an ack, the message is "unacked" and bookkept per channel. Crash the consumer and the broker requeues everything outstanding — at-least-once by default — while acknowledging before processing silently produces at-most-once. The [delivery contract](https://www.rabbitmq.com/docs/confirms) spans both sides: publisher confirms cover broker persistence, consumer acks cover processing.
- **The prefetch window is broker-enforced backpressure.** A consumer's [prefetch count](https://www.rabbitmq.com/docs/consumers) is a credit limit: the broker will not deliver more unacked messages than the window allows. This is flow control as a first-class knob — the queue-full and credit-window analysis in [backpressure](../connection-atlas/backpressure.md) — and it keeps slow consumers from unbounded buffering.
- **Routing is publish-time.** Topic exchanges, binding keys, and dead-letter exchanges (with per-message TTLs and priorities) let the broker do content-based fan-out that Kafka would implement as multiple topics plus a routing consumer.
- **Ordering is FIFO per queue, weakened by features.** Priorities reorder; competing consumers process concurrently so cross-consumer completion order is unspecified; requeued messages jump back near the head. Strict ordering and flexible delivery semantics pull against each other.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Kafka (log) | RabbitMQ (queue) |
|----------|-------------|------------------|
| Storage model | Append-only partitioned log; records expire by retention | Queue holding undelivered/unacked messages; removed on ack |
| Records outlive consumption | Yes — replay by offset reset within retention | No — ack is deletion |
| Delivery state | Consumer side (committed offsets) | Broker side (unacked deliveries) |
| Delivery contract | At-least-once if consumers commit after processing | At-least-once with manual acks; requeue on channel loss |
| Ordering | Strict per partition (per key) | FIFO per queue, weakened by priorities and requeues |
| Routing | Producer-side (key to partition, topic choice) | Broker-side (exchanges, bindings, headers) |
| Backpressure | Consumer paces itself by fetching; lag is visible state | Prefetch credit window enforced by broker |
| Latency profile | Batched; optimized for aggregate throughput | Lower per-message latency for small messages |
| Operational surface | Partition planning, rebalancing, retention, lag monitoring | Queue/exchange topology, prefetch tuning, DLX policies |
| Characteristic failure | Silent data expiry under retention; lag invisibility | Unacked message pileups; requeue storms from crashing consumers |
| Fan-out to many independent readers | Consumer groups, each with own offset | Multiple queues bound to the same exchange |

The **delivery-state location** deserves the arrow drawn. Kafka moves the "was it handled?" bookkeeping into every consumer; the broker stays simple and scalable, but correctness is now distributed — a mismanaged offset commit is a data-duplication or data-loss bug, and consumer tooling (lag metrics, commit discipline) becomes part of every application. RabbitMQ concentrates that bookkeeping in the broker; applications stay simple, but the broker's memory and per-connection bookkeeping become the scaling ceiling, and the queue-depth graph — not a lag graph — is the health signal. The second characteristic failure follows from each choice: Kafka's silent mode of failure is **retention expiry** — a dead consumer for six hours plus a two-hour retention policy deletes data without any error, only a shrinking oldest-offset; RabbitMQ's silent mode is the **requeue loop** — a consumer that crashes mid-message requeues it, crashes again, and the queue livelocks on one poison delivery until a dead-letter policy intervenes.

## Step 4: When Each Wins

| Condition | Choice | Why |
|-----------|--------|-----|
| Same stream feeds many independent consumers, each at its own pace | Kafka | Consumer groups give each reader an independent offset |
| Records must be replayable (rebuild state, audit, backfill) | Kafka | Retention plus offset reset is native; a queue would need a replay layer built by hand |
| Per-entity strict ordering with high write throughput | Kafka | Keyed partitions order per key while parallelizing across partitions |
| Each message is a work item to be assigned, acked, and removed | RabbitMQ | Ack-and-delete is the native contract; consumer-side offset plumbing adds nothing |
| Content-based routing at publish time (severity, tenant) | RabbitMQ | Exchange-binding model routes without a custom dispatcher |
| Low per-message latency for small messages at moderate volume | RabbitMQ | Fewer batching round trips; broker tracks delivery without consumer polling |
| Per-message TTL, priority, or dead-letter policy | RabbitMQ | First-class per-message properties |
| One platform for both event backbone and job queue | Neither alone | Run the log for facts and a queue for work — the honest hybrid |

**Kafka wins** when the stream is a product: multiple downstream systems (search indexing, analytics, caches, ML features) consuming the same facts independently, retention doubling as an audit and recovery mechanism, and per-key order carrying the business invariants. **RabbitMQ wins** when the workload is task distribution: jobs with per-item deadlines, routing that depends on message content, worker pools that must not be handed more than they can chew, and an operations team that wants the broker to own delivery tracking. **The honest hybrid** is the production default at scale — the event backbone on a log, job distribution on a queue, with the [outbox pattern](./app-events-vs-cdc.md) guaranteeing neither loses records the database already committed. Declaring one "the message broker" for every use is how teams end up writing a queue implementation inside Kafka or a replay implementation inside RabbitMQ.

## Step 5: Edge Cases and Counterexamples

- **The prefetch window that flips the delivery guarantee.** A consumer with prefetch 100, auto-ack enabled, and a crash after 50 processed-but-unpersisted messages loses them silently — at-most-once, despite "reliable broker" configuration. Set manual acks and the same crash requeues 50 in-flight messages that may have already sent their side effects — duplicates fan out precisely on failure. The prefetch knob is not a performance setting; it is the at-least-once window size, and sizing it without counting the side effects is how duplicate emails ship in batches.
- **Rebalance duplicate-drain in Kafka.** A consumer dies mid-batch during a deploy; partitions are reassigned; the new owner reprocesses the entire uncommitted range. Duplicates concentrate at exactly the highest-throughput moments, because rebalances happen during deploys, deploys happen during load spikes, and the idempotency machinery built for "rare crashes" fires during every rollout.
- **Retention expiry: the queue's authors would call it a bug, the log's authors call it configuration.** A six-hour consumer outage with a two-hour retention silently deletes the records the consumers were owed. No error fires; the oldest offset simply marches forward. The fix is an SLO on consumer lag plus an alert when the oldest unconsumed offset approaches retention — the log converts "broker down" into "data gone quietly," which a queue cannot do because it never retains past ack.
- **The poison-message livelock.** One malformed payload crashes a RabbitMQ consumer; the broker requeues; the consumer crashes again. With prefetch 1, the queue spends its entire budget re-failing one message — the queue-side equivalent of the synchronous retry storm, and the reason dead-letter exchanges with delivery-count headers exist. Kafka's version is subtler: the poison record blocks its partition's offset until the consumer skips it explicitly, a stalled partition behind an invisible head-of-line block. Using Kafka as a job queue reverses the trap: visibility timeouts, delayed retries, and per-message dead-lettering all become consumer code — a hand-rolled copy of the contract a queue provides as configuration.

## Step 6: Decision Framework

1. **Must the data survive consumption?** Yes (replay, audit, multiple future consumers) → the log; retention is the feature. No → a queue; ack-and-delete is the feature.
2. **Is each record a fact or a task?** Fact (something happened) → Kafka topics. Task (something must be done exactly once per item) → RabbitMQ queues with manual acks.
3. **What ordering scope does correctness need?** Per-entity order under high throughput → keyed Kafka partitions. Per-queue FIFO at moderate throughput → queue. Cross-entity global order → neither solves it cheaply; plan a single-partition design or an external sequencer.
4. **Who should own delivery bookkeeping?** Willing to make every consumer idempotent and lag-monitored → log. Want the broker to own it and keep apps thin → queue with prefetch-sized at-least-once windows.
5. **Is routing content-based at publish time?** Yes → exchanges and bindings; re-implementing that on a log means writing a routing consumer.
6. **Default in doubt:** put facts on the log and tasks on the queue, bridge them with the outbox, and monitor lag on one side and queue depth plus unacked counts on the other — each system's health graph is the one its mechanism makes native.

## Interview Questions

1. **Why is "Kafka is faster" an incomplete comparison claim?** Throughput is a consequence of the log design: sequential appends, batching, and consumer-managed offsets remove per-message bookkeeping from the broker. The same design removes ack-and-delete, per-message TTLs, and broker-side routing — the comparison is about which contract the workload needs, with speed as one consequence of the mechanism.
2. **A team's Kafka consumer was down six hours and no data was lost — but downstream state is wrong. What happened?** Retention outlived the outage, so records were still there, but the consumer redelivered the whole uncommitted window on restart. The missing controls: lag-based alerting during the outage, and consumers idempotent on record identity rather than arrival.
3. **Where does at-least-once come from in each system, and who pays for it?** Kafka: consumers committing offsets after processing; consumers pay with idempotency and commit discipline. RabbitMQ: broker-side unacked tracking plus requeue-on-failure; operators pay with prefetch sizing, ack placement, and dead-letter policy. Neither can promise exactly-once end to end without consumer-side deduplication.
4. **You need "process each order event exactly once, in order per order." Design the delivery path.** Kafka topic keyed by order ID for strict per-order partition ordering; consumers commit offsets after processing; order processing handlers idempotent on event ID; a dead-letter path for poison records; and any step needing cross-event order stays on one partition, accepting its throughput ceiling.
5. **When is RabbitMQ's broker-side delivery state a liability rather than a simplification?** When throughput per queue scales past the broker's bookkeeping (memory for unacked deliveries, per-connection state), or when consumers need replay — the broker deleted the records on ack, so any rebuild needs a source other than the queue.

## Key Takeaways

- The fork is **what the broker sells**: a log (retention, replay, per-key order, consumer-owned delivery state) or a queue (ack-and-delete, broker-owned delivery state, routing, credit-based flow control).
- Delivery-state location decides the failure story: Kafka's silent failure is retention expiry and uncommitted-offset duplication; RabbitMQ's is unacked pileups and poison-message requeue loops.
- At-least-once has a different payer in each system — consumer idempotency on the log, ack and prefetch discipline on the queue — and neither offers exactly-once without it.
- Ordering, routing, and backpressure are all mechanism consequences: partitions versus queues decide where order, fan-out, and backpressure knobs physically live.
- The production answer is frequently both: a log as the event backbone, queues for task distribution, and the outbox pattern at the boundary where the database commits.

## Cross-References

- [RPC vs Message Queues: Why-Not Handbook](./rpc-vs-message-queue.md) — the upstream fork: whether to use a broker at all versus in-line calls.
- [Push vs Pull: Why-Not Handbook](./push-vs-pull.md) — the pacing-ownership fork both brokers implement differently.
- [App Events vs CDC: Why-Not Handbook](./app-events-vs-cdc.md) — getting records into the broker without the dual-write hole.
- [Message Queues: Follow-up Tree](../followup-tree/message-queues.md) — the escalation ladder from delivery semantics to broker internals.
- [Backpressure: Connection Atlas](../connection-atlas/backpressure.md) — the queue-full and credit-window paths this comparison's prefetch knob belongs to.
- [Queue Dead Letter and Replay: Connection Atlas](../connection-atlas/queue-dead-letter-replay.md) — DLQ and replay mechanics behind the poison-message edge cases.
- [Kafka](../../distributed/messaging/kafka.md) and [RabbitMQ](../../distributed/messaging/rabbitmq.md) — the book's broker-mechanics chapters for each side.
- [Kafka Log Internals](../../distributed/messaging-internals/kafka-log-internals.md) — the partition-log storage design the log half rests on.
- [Kafka Consumer Rebalancing](../../distributed/messaging-internals/kafka-consumer-rebalancing.md) — the membership-change mechanism behind the duplicate-drain edge case.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
