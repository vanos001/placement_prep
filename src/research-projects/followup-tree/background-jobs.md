# Follow-up Tree: Background Jobs

## Overview

"The API returned 200 — but the work still has to happen. Where does it run, and what happens when it runs twice?" is the follow-up that separates candidates who have operated asynchronous systems from candidates who have only called them. The queue guarantees at-least-once delivery, which means *your* code runs twice, and the interview is about whether you know what that implies. The ladder escalates through the four questions every job system must answer: which trigger shape fits the work (cron, queue, or scheduler — chosen by semantics, not fashion), how processing survives duplication (idempotency as a code property, not a queue feature), what a visibility timeout actually contracts for (worker death mid-job and the double-execution window), and how bulk work coexists with user-facing traffic (backfills, midnight cron storms, noisy neighbors). Each rung connects to a chain here: queue mechanics are the [Message Queues](./message-queues.md) ladder, the backfill case is [Zero-Downtime Migrations](./zero-downtime-migrations.md), and the idempotency incident is the casebook's Knight Capital entry. This page owns what runs after the response and how it is triggered, delivered, retried, and finished.

## The Opening Question

**"Why do we move work out of the request path, and what do we lose when we do?"**

The expected core answer: work moves out of the request path when it is slow (video encoding, report generation), spiky (campaign emails), or not needed in the user's critical path (analytics, cache warming). The request acknowledges and returns; a job system executes the work with its own lifecycle. What you lose is synchronous semantics: no direct error surfaced to the caller, no natural result, and — the heart of this ladder — delivery becomes at-least-once rather than exactly-once, so the job's *effect* must tolerate duplication even if its *invocation* does not.

Why this answer is correct: it names the semantic loss — at-least-once — as the *first-class* consequence rather than an implementation footnote. The interviewer's escalation is predictable — "at-least-once means it runs twice; what does your code do then?" — and a candidate who flagged idempotency in the opening answer has pre-empted three rungs, the strongest possible signal.

## Level 2: Cron, Queues, Schedulers — Which Trigger Shape Fits?

**What it tests:** whether you choose job infrastructure by *trigger semantics* — time-driven, event-driven, or state-driven — instead of by whichever tool you used last.

**Weak answer:** "We run everything on cron" — one mechanism for all three shapes, meaning no delivery guarantees, no backlog visibility, no retry story, each invisible until the first missed run.

**Strong answer:** distinguishes the three shapes by their contracts. Cron is time-triggered fire-and-forget: it starts processes at wall-clock times, and a down machine means the run is skipped — no delivery guarantee, no dedup, no result capture. Queues are event-triggered with durable delivery: producers enqueue, the broker persists, workers process with acknowledged retries — semantics the [Message Queues](./message-queues.md) chain develops. Schedulers are state-driven: work scheduled for a *future* time with a record that survives restarts (delayed jobs, workflow engines, reminders) — the durable "what should have happened by now" state is the point. Selection follows the trigger: maintenance → cron; user-action work → queue; business-timed work → scheduler.

**Escalation trigger:** "Your nightly cron sends one email per active user. A deploy takes the app down at 23:58 for ten minutes. What happened to last night's emails — and would that differ under each shape?"

**Answer.** Under naive cron: if the entry fired while the app was down, the run started and failed; if the cron host was down, crond *skipped* without owing it — cron does not catch up. Nothing retries, nothing is recorded as pending: silent omission. Under a queue: the durable backlog either never enqueued (same hole) or sat in the broker until workers returned — delivery is the broker's guarantee, not the machine's uptime. Under a scheduler: "send daily digest for date D" exists as a row with a status, so the missed window is discoverable and re-runnable — recovery is explicit state, not luck. The senior conclusion: the shapes differ in *who owns the durable record of work owed* — nobody (cron), the broker (queues), or a state machine (schedulers) — and that determines whether an outage causes silent loss or recoverable backlog. Operational details follow: jitter for the midnight herd, overlap protection, and absence monitoring — because cron's failure mode is silence rather than error.

## Level 3: Idempotency and Poison Pills — What Happens When It Runs Twice, or Never Completes?

**What it tests:** whether at-least-once delivery is internalized into code discipline — duplicates must be harmless, and unprocessable work must not stop the pipeline.

**Weak answer:** "The queue gives exactly-once delivery, so we're fine" — wrong on the semantics (brokers give at-least-once or at-most-once; exactly-once effects require end-to-end design), and it skips the poison-pill question entirely.

**Strong answer:** treats idempotency as the job's contract with delivery semantics: an idempotency key (client-supplied or derived from message content), a deduplication window, and effects that are naturally idempotent where possible (state replacement, upserts) versus dangerously non-idempotent (INSERT, increment, charge-a-card). Names the poison pill: a message that always fails (malformed payload, consumer bug, missing record) and, under at-least-once retry, blocks the queue or partition behind it — so consumers need bounded retries distinguishing transient failures (retry with backoff) from permanent ones (dead-letter immediately), plus a DLQ with alerting and replay.

**Escalation trigger:** "A new consumer version deployed at 09:00. At 09:01, one bad message froze the order pipeline; at 09:30 you fixed the bug. Explain both incidents and the design changes."

**Answer.** Incident one is the poison pill: the new consumer crashed on a payload it had never handled, the broker redelivered to the next worker (at-least-once), which also crashed — a crash loop pinning the partition so every *good* message behind the bad one stopped flowing. One unprocessable message became a full outage because unbounded retry meets a permanently-invalid input. Incident two is the double-execution window: in-flight messages were partially processed by the old worker before it died; after the fix, redelivery re-runs work whose side effects may have completed — a charge recorded, a row inserted. The design changes, in order: validate and route unknown payloads to the DLQ *before* crashing; bound retries with transient/permanent classification; and make the effect idempotent so redelivery after any worker death is harmless — a dedup table keyed on message ID checked in the same transaction as the effect, or a state machine that makes re-application a no-op. The cautionary anchor is [Knight Capital (2012)](../failure-casebook/knight-capital-2012.md): work executed twice because *running twice was never made safe*. The rule: delivery semantics live in the broker; correctness lives in the consumer — at-least-once is a contract the job must sign, or the dedup layer must be built explicitly. The same discipline underlies backfills and dual-write windows in [Zero-Downtime Migrations](./zero-downtime-migrations.md).

## Level 4: Visibility Timeouts and Leases — Who Owns an In-Flight Job?

**What it tests:** whether you understand the claim-and-acknowledge protocol beneath every queue — what happens between "worker took the message" and "worker acknowledged it," especially when the worker dies in between.

**Weak answer:** "The queue is durable, so nothing is lost" — conflates broker durability with in-flight ownership, and cannot explain a single duplicate or stuck job.

**Strong answer:** explains the visibility timeout as a *lease*: on delivery the message becomes invisible to other consumers for a bounded window; if the worker acks in time, the message is deleted; if the worker dies (or is too slow), the lease expires and the message redelivers — precisely the mechanism producing at-least-once delivery, since the first worker may still finish. Knows the tuning trap both ways: timeout shorter than worst-case processing duplicates work routinely; longer than failure detection delays recovery. Knows the mitigation for long jobs: lease *renewal* (heartbeat extending the window while work progresses) and in-worker deadlines so jobs fail instead of outliving their lease.

**Escalation trigger:** "A job takes up to 40 minutes. Your visibility timeout is 10 minutes. Every long job runs twice — and one duplicate corrupts state. Walk through the timeline and the fixes."

**Answer.** The timeline: consumer A claims the message at t=0 with a 10-minute lease; at t=10 the lease expires and the broker redelivers to B while A is still running; at t=20 A acks a message the broker no longer considers outstanding, while B completes independently — two executions of one job. The corruption is idempotency failure made systematic: not a rare crash but a *guaranteed* duplicate for every job longer than the lease, so "make it not crash" is the wrong fix family. Fixes, in order: renew the lease from the worker (heartbeat at timeout/3, so a stalled worker stops renewing and recovery stays fast — the standard long-job pattern in SQS-style APIs and [Celery](https://docs.celeryq.dev/en/stable/userguide/tasks.html) late-ack configurations); enforce a processing deadline inside the job so it fails before the lease lapses; and — non-negotiably — make the effect idempotent anyway, because renewal shrinks the duplicate window without removing it. The conceptual frame: the lease is the queue's answer to *failure detection* — you cannot distinguish "dead" from "slow," so you bound the wait and accept redelivery. It is the same lease concept as leader-election terms in [Consensus: Raft](./consensus-raft.md), and the same reason fencing tokens exist: a worker past its lease is a zombie whose writes need fencing.

## Level 5: Backfills and Shared Clusters — Bulk Work Beside User Traffic

**What it tests:** production coexistence judgment: how bulk jobs (backfills, re-processing, exports) share infrastructure with user traffic without starving either, and how to run a week-long backfill you might have to stop.

**Weak answer:** "We run the backfill at night when traffic is low" — a heuristic that fails the moment the backfill outlives one night, saying nothing about read amplification, throttling, or resumability.

**Strong answer:** treats bulk work as a capacity-planning problem with an explicit admission policy: rate-limit the backfill (a client-side token bucket, not hope), isolate its reads (replicas or a separate pool — the pool arithmetic is [Connection Pooling](./connection-pooling.md)), watch the user-facing SLI while it runs (the [SLOs and Error Budgets](./slos-and-error-budgets.md) chain makes "stop the backfill" a budget rule, not an argument), and build resumability in from the start: watermark checkpoints, idempotent units, chunking that allows pause or kill without loss. Knows the amplification signatures: a rewriting backfill doubles write load and bloats replication lag, and a 10M-row re-read can evict the cache the app depends on.

**Escalation trigger:** "You must backfill 900 million rows on the live database. Design the job — then the on-call engineer pages you at hour three: user latency is degrading. What happens?"

**Answer.** The design first, because the page response depends on it: chunk by primary-key range with a persisted watermark; per-chunk idempotent updates; a client-side rate limiter with a configurable budget; reads against a replica with its own lag guard (pause when lag exceeds a threshold, resume when it drains); a kill switch that stops scheduling new chunks without losing progress. When the page comes, the answer is *turn the knob you built*: halve the rate and watch the user-facing percentile and replica lag; if degradation continues, stop at the next chunk boundary — resumability makes "stop" a cheap decision instead of a confrontation with 300 million half-done rows. The judgment content is the explicit trade: the backfill is *also* a workload with an SLO (its completion date), and the shared cluster arbitrates between two SLOs — so the design says "user traffic gets the first X percent, backfill the rest," making the conflict a parameter instead of a nightly negotiation. Sizing workers and forecasting completion from measured throughput is [Capacity Planning](../../sre/capacity-planning.md); the queueing intuition for why unthrottled bulk load destroys everyone's latency is [Queueing Fundamentals](../../queueing-theory/fundamentals.md).

## How to Approach Unfamiliar Variations

1. **Ask what owns the durable record of work owed.** Cron, queue, and scheduler differ exactly there. Any unfamiliar tool — scheduled lambdas, delayed-job libraries, workflow engines — is classified by where the "this work has not happened yet" state lives and whether it survives restarts.
2. **When duplication is mentioned, move immediately to the effect.** "Runs twice" is a property of delivery; "is safe to run twice" is a property of code. Design the idempotency key, the dedup window, the transactional check — and name what remains non-idempotent and how it is fenced.
3. **Bound every retry and classify every failure.** Transient (retry with backoff), permanent (dead-letter immediately), unknown (dead-letter with full payload capture for replay). If the variation adds a failure mode, add it to the classification, not to the retry loop.
4. **Separate the trigger time from the processing deadline.** Most scheduling surprises are clock arithmetic: lease shorter than work, cron jitter, dedup windows shorter than backoff. Write the four clocks (trigger, claim, lease expiry, dedup expiry) and check their ordering.

## Interview Questions

**Q: A scheduled task must run exactly once per day. Your team claims the workflow engine "guarantees exactly-once." What is your response?**
A: Exactly-once *effects* are a property of the whole path, not the engine's marketing: the engine can guarantee at-most-once scheduling or at-least-once execution with dedup, but the task's effect must still be idempotent — a dedup key on the task's date, checked in the same transaction as the effect.

**Q: Your consumer runs 8 parallel workers. Latency is fine, but a downstream API rate-limits you at 100 requests per second and you get throttled. What changed semantically?**
A: The downstream, not the queue, is now the admission controller: worker parallelism converts queue depth into an uncontrolled request rate that ignores the downstream's budget. Fixes: a client-side rate limiter shared across workers (token bucket sized to the quota), prefetch limits to bound in-flight messages, or bulk endpoints.

**Q: A cron job's runtime has grown from 5 minutes to 2 hours over two years. What risks does that create and how do you address each?**
A: Overlap risk (the next run starts mid-previous — add a lock or convert to a queue job with explicit concurrency control), silent-failure risk (a run dying at minute 110 has no partial-progress story — checkpoint), and schedule-drift risk (the interval no longer fits the work; the job is effectively continuous). The fix each time: promote the job from a crontab line to an owned component with state, limits, and absence alerts.

**Q: An engineer proposes moving validation out of the request path into a background job to cut p99 latency. What do you check before agreeing?**
A: Whether validation failures currently produce user-visible errors (if yes, async means users learn of bad input minutes later — a product decision), whether validation gates something irreversible, and what the error-handling UX becomes. Moving work async changes *when errors surface and who pays for them* — that must be designed, not defaulted.

## Key Takeaways

- Cron, queues, and schedulers differ in who owns the durable record of work owed — nobody, the broker, or an explicit state machine — and that determines whether outages cause silent loss or recoverable backlog.
- At-least-once is the broker's guarantee; idempotency is the consumer's obligation. Exactly-once effects require a dedup key checked in the same transaction as the effect.
- Poison pills are bounded-retry problems: classify transient versus permanent failures, dead-letter the latter immediately, and alert on DLQ depth.
- A visibility timeout is a lease — the queue's answer to "dead versus slow" — and any job longer than its lease duplicates by construction; renew leases and make effects idempotent regardless.
- Backfills are workloads with SLOs competing on shared infrastructure: rate-limit, isolate reads, checkpoint, and make "stop" a cheap decision.

## Cross-References

- [Message Queues](./message-queues.md) — the sibling chain that owns broker mechanics: partitions, offsets, consumer groups, delivery semantics.
- [Zero-Downtime Migrations](./zero-downtime-migrations.md) — the canonical backfill scenario: expand–contract deploys, batched resumable backfills, dual-write traps.
- [Connection Pooling](./connection-pooling.md) — the sizing arithmetic that determines how much of a shared database a job pool may consume.
- [SLOs and Error Budgets](./slos-and-error-budgets.md) — the decision framework that arbitrates between job completion and user-facing burn.
- [Consensus: Raft](./consensus-raft.md) — leases and failure detection in their strongest form: terms, expiry, fencing.
- [Webhook Delivery](../connection-atlas/webhook-delivery.md) — the outbound sibling: retry schedules, signatures, DLQs for HTTP callbacks.
- [Event Sourcing and WAL](../connection-atlas/event-sourcing-wal.md) — where the job-as-event-log connection (replay, reprocessing) is developed.
- [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md) — the assumption audit for every retry the job system performs on your behalf.
- [Knight Capital (2012)](../failure-casebook/knight-capital-2012.md) — the production case where work ran twice and double execution was not safe.
- [Kafka](../../distributed/messaging/kafka.md) — the log-based broker whose offset model changes the lease-and-ack story.
- [RabbitMQ](../../distributed/messaging/rabbitmq.md) — the classic AMQP broker: acks, prefetch, and dead-letter exchanges as concrete mechanisms.
- [Queueing Fundamentals](../../queueing-theory/fundamentals.md) — why unthrottled bulk load destroys latency for every other workload on shared capacity.
- [Capacity Planning](../../sre/capacity-planning.md) — sizing workers and forecasting backlog completion from measured throughput.
- [Kubernetes CronJob docs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) — a concrete scheduler with explicit concurrency-policy knobs (verified this session).
