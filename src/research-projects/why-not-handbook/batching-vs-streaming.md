# Batching vs Streaming: Window Economics Against Continuous Liveness

## Overview

Batch and streaming are answers to one question: **when does processing start?** A batch system waits for a fixed accumulation — a file landing at midnight, an hourly partition, a 24-hour window — then processes everything at once with the full dataset visible. A streaming system starts on arrival: each event is processed the moment it enters, with state accumulated incrementally across events. Every downstream property follows from that single fork. Latency (bounded by the window vs bounded by the network), cost (elastic clusters spun per job vs always-on infrastructure), correctness machinery (re-run the window vs checkpointed exactly-once), late data (invisible in batch vs a first-class watermark problem), and backfill (rerun the job vs replay the log) all inherit their shape from the pacing decision.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **batch buys simplicity, global optimization, and cheap reprocessing by paying a window-shaped latency floor; streaming buys liveness by paying for permanent state management and exactly-once machinery.** Neither dominates. Mini-batch hybrids (Spark's structured streaming, commit-interval consumers) exist precisely because each pure model fails in a characteristic way: batch fails on alerting SLAs, streaming fails on cost discipline and operational maturity. The edge cases — the lambda architecture's dual-codebase drift, the backfill a pure streaming system cannot perform, the watermark trap — are where the real decision lives.

## Step 1: The Problem and Its Constraints

The abstract shape: events arrive from many sources at rate *r* with burstiness; results feed reports, dashboards, alerts, or serving systems; both the pipeline and its consumers fail independently. Constraints that decide the answer:

- **Liveness SLA.** "How old may a result be when a decision reads it?" A nightly finance report tolerates 24 hours; a fraud alert at checkout tolerates nothing above seconds. This single number eliminates one branch of the fork outright — and its absence (no SLA at all) is the strongest argument for batch.
- **Correctness target.** Does the output need exactly-once semantics, or is at-least-once with dedup acceptable? Exactly-once is *free* in batch (rerun the window deterministically) and *expensive* in streaming (checkpointing plus transactional sinks) — a cost asymmetry that shapes everything downstream.
- **Event-time vs processing-time.** Do results depend on when events *happened* (sessionization, billing windows) or only on when they arrive? Event-time logic needs watermarks and late-data policy — machinery only streaming has to build.
- **Cost structure.** Variable, spiky workloads fit elastic batch clusters that bill only while running. Always-on streaming clusters burn the same bill at 3 a.m. when traffic is near zero.
- **Backfill expectation.** Schema changes and bug fixes will require recomputing history. How much history, how often, and how fast?
- **Team maturity.** Stateful, exactly-once streaming is operationally harder — checkpoints, state migration across versions, watermark tuning. An honest skills inventory is a constraint like any other.

## Step 2: The Mechanisms

### Batch: accumulate, then process with global knowledge

- **The window is the unit of work, failure, and correctness.** A job processes partition `ds=2024-06-01`; if it crashes, rerun the same partition — idempotent by construction if the job is deterministic. Exactly-once needs no transaction machinery because "try again" is the recovery story, and the output overwrites atomically.
- **Global visibility buys global optimization.** Because the whole dataset is present, the engine sorts, shuffles once, joins with full statistics, and pushes predicates across the entire input. The [Spark](https://spark.apache.org/) engine's sort-merge joins and plan-level optimizations assume bounded inputs — an assumption streaming cannot make.
- **Statelessness is the simplicity dividend.** No checkpoints, no state migration, no watermark tuning. The job's state lives in the data it reads; a new version of the code is just a rerun. This is why batch pipelines survive team turnover in ways stateful streaming systems often do not.
- **Cost is elastic and visible.** Clusters spin up per job on spot/preemptible capacity and vanish after. Zero traffic costs zero money — the economic inverse of streaming.

### Streaming: process on arrival, with state inside operators

- **State is a permanent liability.** Windows, session aggregations, and stream-stream joins hold state inside the operators; that state must survive failures and version upgrades. [Flink](https://flink.apache.org/)-class systems checkpoint operator state asynchronously (aligned barriers) and restore it on failure — the machinery is mature but mandatory, and restoring a 500 GB keyed state is an operational event, not a rerun.
- **Exactly-once is the stream tax.** End-to-end exactly-once requires atomically committing processed state *and* sink writes — Kafka transactions, or a two-phase-commit sink where the job prepares writes and commits on checkpoint. Batch gets the same guarantee by rerunning windows; streaming must build it because there is no "rerun the window" escape. See [exactly-once semantics](../../distributed/messaging-internals/exactly-once-semantics.md).
- **Event time needs watermarks.** The system cannot know an hourly window is complete until it decides to stop waiting. Watermarks are that decision — a heuristic clock that trades window completeness against latency, with an explicit late-data policy (allowed lateness, side outputs) for events that arrive after the window closed.
- **Backpressure is continuous and shared.** A slow sink applies credit-based backpressure upstream through the [pipeline](../../distributed/messaging-internals/backpressure-and-flow-control.md); the [Kafka broker](https://kafka.apache.org/documentation/) holds the excess as log retention — pacing ownership sits with the consumer, as in the pull model discussed in [push vs pull](./push-vs-pull.md). The stream never "finishes", so neither does backpressure management.
- **Cost is steady-state.** The cluster runs always, and per-event marginal cost is low at high volume — but the fixed floor dominates at low volume. A pipeline handling 5 events/minute still pays for a running cluster every hour.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Batch (windowed) | Streaming (continuous) |
|----------|------------------|------------------------|
| Result latency | ≥ window duration; floor is the design | Milliseconds to seconds after arrival |
| Exactly-once | Free: rerun the deterministic window | Costly: checkpoints + transactional/2PC sinks |
| Late data | Not a category — window sees everything | Watermarks, allowed lateness, side outputs |
| Backfill/reprocessing | Native: rerun history partitions | Replay from a durable log, or a batch side-road |
| Cost model | Elastic, per-job, zero when idle | Fixed floor, always burning |
| State complexity | Stateless jobs | Operator state, checkpoints, state migration |
| Optimization scope | Global (full dataset visible) | Local (per-event/per-micro-batch) |
| Failure recovery | Rerun the job | Restore checkpoint; sink dedup on replay |
| Schema evolution | Re-run affected windows | In-flight decode compatibility; state schemas |
| Debugging | Deterministic re-run of a window | Live state inspection; harder reproducibility |

The **backfill asymmetry** deserves the arrow drawn: batch's unit of work is a window, so "recompute last quarter" is a scheduling task. A pure streaming system's unit of work is *an event*, so history correction means replaying the source log through the pipeline — which works only if the log retains long enough, the processing is deterministic, and the sinks tolerate a full re-write. Systems that never planned for replay discover the gap during their first serious bug, when the data is wrong and the only recovery is re-deriving six months. This is the strongest argument for log-first architectures ([kappa-style](../../data-engineering/stream-processing.md)): the durable log converts streaming's weakness into batch's strength by making *replay* the backfill.

## Step 4: When Each Wins

**Batch wins** when: the consumer is a report, an ML training run, a billing statement, or any analysis whose value does not decay in minutes; correctness matters more than liveness (re-runnable windows beat exactly-once machinery on both cost and trust); workloads are spiky or seasonal (elastic clusters idle at zero cost); teams lack stateful-streaming operational depth; and the pipeline must reprocess history routinely. The simplicity dividend compounds: a stateless daily job that a single engineer understands will still work in five years.

**Streaming wins** when: the SLA is contractual — fraud blocking, alerting, monitoring, live personalization — and a window floor is a business failure; the output maintains serving-side state (search indexes, feature stores, caches) that must track reality continuously; event-time windows must close in minutes; and the org can fund the operational sophistication (checkpoint tuning, state migration, watermark policy). The decisive test: would acting on stale data cause a loss larger than the streaming premium?

**The honest hybrid menu** — where production systems actually live:
- **Micro-batch.** Spark structured streaming runs batches every 100 ms–1 s: streaming-shaped liveness on batch-shaped machinery, with the interval as an explicit latency/overhead dial. The trade-off: a slow micro-batch backpressures the source, so the window becomes both a latency floor and a buffering surface (see edge cases).
- **Stream with batch replay (kappa over lambda).** Persist everything to a durable log; serve liveness from the stream; perform backfills by replaying the log through the same code. The [lambda architecture](../../data-engineering/batch-processing.md)'s dual speed-layer/batch-layer codebases are now widely considered an anti-pattern — two implementations of one computation drift, and reconciling them is the hidden cost (edge case below).
- **Commit-interval consumers.** Plain Kafka consumers polling every 500 ms are "streaming" for latency purposes with batch-shaped simplicity — often enough for alerting SLAs of seconds.

## Step 5: Edge Cases and Counterexamples

- **The lambda drift bug.** A team runs a streaming job for the live dashboard and a batch job for the audited report. Six months later a customer escalates: dashboard says 1,204 orders, report says 1,197. The streaming job deduplicates on a field the batch job doesn't (or vice versa). Both were "correct" against different specs; nobody owns the reconciliation. The cost of lambda architecture is not running two systems — it is maintaining two *definitions of truth* that will eventually disagree in front of executives. Kappa (one code path, replay for history) exists to delete this failure.
- **The micro-batch interval that is two dials in one.** Lowering Spark's trigger interval to 200 ms improves liveness but increases per-batch overhead (job scheduling, commit churn) until the pipeline spends more time starting batches than processing them — and a batch that runs longer than its trigger stacks up, silently becoming the new backpressure point into Kafka. The interval is simultaneously a latency knob, an overhead knob, and a buffering knob; teams that tuned only the first discover the third during the first traffic spike.
- **The streaming cluster that costs more than the data is worth.** An alerting pipeline for a low-traffic internal service runs a dedicated Flink cluster at 4% utilization around the clock. The batch alternative — a five-minute cron polling the database — meets the actual SLA (five minutes to alert) at a tenth of the cost. "Streaming" is a requirement when the SLA says so; when the SLA says minutes, batch is the cheaper correct answer, and no amount of architectural fashion changes the bill.
- **The backfill that broke the stream.** A schema bug corrupts eight months of sessionized events. The pipeline is pure streaming with a seven-day log retention. The fix requires re-deriving history that no longer exists in the log — the raw source archives exist, but the stream code path cannot process bounded inputs efficiently (unbounded-state assumptions), so the team writes a one-off Spark job anyway, discovering that their "pure streaming" system always had a batch dependency, unplanned. Replay-ability is a designed property, not an emergent one.
- **The watermark that ate the afternoon.** A burst of mobile events arrives three hours late (offline phones syncing). The hourly windows already emitted; totals are wrong. Allowed-lateness plus side-output streams catch the stragglers, but now downstream consumers must merge window emissions with late corrections — complexity batch never faces because it waits for all data by construction. The lesson: streaming's "real-time" guarantee is really "real-time *plus a correction channel*", and the correction channel is part of the design.

## Step 6: Decision Framework

1. **Is there a liveness SLA below ~5 minutes?** No → batch; the simplicity, cost, and correctness dividends all apply. Yes → streaming family.
2. **Is the computation stateful across events** (sessions, stream joins, running aggregates)? Yes → streaming needs checkpointed state machinery; batch gets it by seeing all data at once.
3. **Is exactly-once required end-to-end?** Batch: rerun windows. Streaming: budget for transactions/2PC sinks and verify sink idempotency.
4. **Will history be recomputed routinely** (schema changes, bug fixes)? Design replay in: durable log with sufficient retention, deterministic processing — regardless of the streaming/batch choice.
5. **Is utilization spiky and cost-sensitive?** Batch's elastic clusters win; an always-on cluster idling at 4% is the tell.
6. **Default in doubt:** batch first, add streaming only where an SLA demands it, keep one code path (replay, not dual pipelines), and treat micro-batch intervals as the latency/overhead/buffering dial they really are.

## Interview Questions

1. **Why is exactly-once effectively free in batch and expensive in streaming?** Batch's unit of work is a deterministic windowed job whose output can be recomputed and atomically overwritten — recovery *is* rerun. Streaming has no such unit; results are emitted continuously, so exactly-once requires checkpointed state plus atomic sink commits (Kafka transactions or a two-phase-commit sink), with deduplication at consumers as the fallback.
2. **A dashboard and an audited report disagree. Diagnose as an architecture problem, not a data problem.** Two code paths computing "the same" metric (lambda architecture) embed two definitions of truth; any difference in dedup keys, window boundaries, or filter timing diverges silently. The fix is a single processing path — stream with log replay for history — or an explicit reconciliation contract with an owner.
3. **When is a five-minute batch cron better than a streaming pipeline?** When the alerting SLA is minutes, traffic is sparse, and the streaming cluster's fixed cost dominates. Latency requirements decide the family; the event rate and cost model decide within it. Sparse events with minute-level SLAs make batch the cheaper *and* simpler correct answer.
4. **What must a pure streaming system design for that batch never faces?** Late data and replay. Watermarks, allowed lateness, and correction channels exist because windows close before all events arrive; replay capacity (log retention, deterministic processing, idempotent sinks) exists because there is no windowed rerun. Batch gets both properties implicitly from bounded inputs.
5. **Explain micro-batch as a hybrid and the failure mode tuning it introduces.** Micro-batch runs windowed jobs at sub-second triggers: batch machinery, streaming-shaped liveness. The trigger interval is simultaneously a latency, overhead, and buffering knob — too low and per-batch scheduling dominates; too slow a batch and source backpressure builds. Tuning it means sizing all three at once.

## Key Takeaways

- The single fork is **when processing starts**: after a window (batch) or on arrival (stream). Latency, cost, correctness machinery, late data, and backfill all derive from it.
- Batch's unit of work — a rerunnable window — makes exactly-once free and backfill native; streaming's unit is an event, so it must *build* both properties with checkpoints, transactions, and replayable logs.
- Streaming's guarantee is "real-time plus a correction channel": watermarks and late-data policy are part of the contract, not optional hardening.
- Hybrids are the production norm: micro-batch dials latency against overhead and buffering; kappa (replay the log) replaces the lambda architecture's dual-truth drift.
- Cost is a first-class constraint: always-on clusters burn money at 3 a.m., elastic batch clusters do not. An SLA is the only thing that justifies the difference.

## Cross-References

- [Backpressure: Connection Atlas](../connection-atlas/backpressure.md) — the queue-full path when a streaming consumer stalls and pacing ownership decides who buffers.
- [Message Queues: Follow-up Tree](../followup-tree/message-queues.md) — the queueing substrate both styles consume.
- [ETL vs ELT](./etl-vs-elt.md) — the sibling comparison: where transformation runs, independent of when it runs.
- [Batch Processing](../../data-engineering/batch-processing.md) and [Stream Processing](../../data-engineering/stream-processing.md) — the book chapters behind each mechanism.
- [Kafka](../../distributed/messaging/kafka.md) — the durable log that makes replay-based backfill possible.
- [Exactly-Once Semantics](../../distributed/messaging-internals/exactly-once-semantics.md) — the transaction and dedup machinery behind the stream tax.
- [Spark Internals](../../data-engineering/spark-internals.md) and [Flink](../../data-engineering/flink.md) — the engines on each side of the fork.
- [Push vs Pull](./push-vs-pull.md) — pacing ownership at the broker layer, the same fork one level down.
- [Backpressure and Flow Control](../../distributed/messaging-internals/backpressure-and-flow-control.md) — credit systems that keep continuous pipelines stable.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
- [Spark](https://spark.apache.org/) and [Flink](https://flink.apache.org/) — the engine documentation for micro-batch and true-streaming execution.
- [Kafka documentation](https://kafka.apache.org/documentation/) — the log-retention and consumer mechanics behind replay.
