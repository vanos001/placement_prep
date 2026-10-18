# RPC vs Message Queues: Who Waits for the Answer, and Who Owns the Failure?

## Overview

"RPC or a message queue?" is usually framed as a style question — *synchronous vs asynchronous*, *request/response vs fire-and-forget* — and framing decides the answer before any analysis happens. The sharper question is: **what does the caller get back, and when?** A remote procedure call promises that by the time the function returns, either a result exists or an error can be named; the caller's timeline and the callee's timeline are pinned together for the duration of the exchange. A message queue breaks that pin: the producer hands a record to a broker and moves on, the consumer picks it up seconds or hours later, and no code anywhere is waiting on the specific outcome of that specific message. Everything else — temporal coupling, failure semantics, backpressure, throughput, the shape of observability — falls out of that one decision about who waits.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **RPC couples lifetimes and turns remote failures into immediate, in-line errors; queues decouple lifetimes and turn failures into lag, redelivery, and poison messages that surface far from their cause.** Neither is "more scalable" in the abstract. A queue adds capacity headroom and blast-radius isolation at the price of losing the response, losing the ordering across producers, and losing the caller's ability to know anything at all — what some workloads need, and what an order-placement path cannot afford. The non-obvious middle ground — request-reply over a queue — inherits most of the problems of both, and belongs in this page's edge cases rather than its defaults.

## Step 1: The Problem and Its Constraints

The abstract shape: a caller wants a remote effect — a computation, a state change, a notification. Constraints that decide the answer:

- **Does the caller need the outcome to continue?** If the next line of code depends on the result (a price, an ID, an authorization decision), the caller's timeline is entangled with the callee's no matter what transport is chosen; a queue cannot remove the dependency, only hide it.
- **Must the effect happen at-most-once, at-least-once, or exactly-once?** RPC over a flaky network is genuinely at-most-once unless the caller retries and the callee deduplicates; queues advertise at-least-once by default, which imports idempotency obligations at the consumer.
- **What happens when the callee is slow or down?** Is it acceptable for the caller to fail visibly (checkout returns 502), or must the work survive the outage and complete later (email, indexing, fan-out to analytics)?
- **Caller and callee lifetimes.** Are both always up, deployed together, and owned by the same team? Or is the callee a batch process, a nightly job, a partner service that reboots whenever it pleases?
- **Latency budget vs throughput.** An interactive user is waiting on RPC latency; a background pipeline is waiting on queue throughput. Optimizing the wrong one is the classic mismatch.

## Step 2: The Mechanisms

### Synchronous RPC

The caller invokes what looks like a local function; a stub marshals the arguments, opens (or reuses) a connection, transmits, and blocks until a response or an error arrives. The mechanisms that matter:

- **Failure is a return value.** Timeout, connection refused, TLS failure, HTTP 500 — each surfaces as an exception in the caller's stack, with the stack able to react immediately. This is RPC's defining feature: *the error and the operation that caused it are co-located in time and code*. It is also the failure mode that makes retry storms possible: a caller that retries on timeout, behind a [circuit breaker](../../distributed/microservices/circuit-breakers.md) or without one, multiplies load precisely when the callee can least absorb it (see [timeouts and retries](../assumptions-hunt/timeouts-and-retries.md)).
- **Backpressure is implicit and honest.** A blocked caller consumes a thread, a connection, or a request slot; when callers exhaust those, they slow down. The slowest dependency propagates pressure upstream *through* the call graph, visibly. The cost is that one slow dependency can stall every caller touching it — the thread-pool exhaustion cascade behind the microservices retry mathematics in [monolith vs microservices](./monolith-vs-microservices.md).
- **Deadlines can propagate.** Mature RPC frameworks (gRPC among them, per its [documentation](https://grpc.io/docs/)) carry a deadline header downstream, so a 200 ms budget set at the edge is divided across the subtree of calls. A queue cannot propagate a deadline to work that has not started yet; a delayed message's "deadline" is a consumer-side policy, not a propagated contract.
- **Ordering and consistency are per-call.** One call, one response, one causal chain — and read-your-writes against the callee is trivial, because the write returned before the read began.

### Asynchronous messaging

The producer serializes a record and publishes it to a broker; the broker acks persistence and the producer moves on. Consumers fetch or receive when ready. The mechanisms that matter:

- **Temporal decoupling is the product.** Producer and consumer never share a timeline: the consumer may be down, redeploying, or 10,000 messages behind while producers continue undisturbed. This is why queues absorb bursty producers (flash sales, midnight batch uploads) and why the durable log at the core of [Kafka](../../distributed/messaging/kafka.md) doubles as a buffer *and* a history. The pacing analysis — who owns it, what breaks when it sits on the wrong side — is the same fork dissected in [push vs pull](./push-vs-pull.md).
- **Delivery is a broker contract, not a network outcome.** At-least-once redelivery means the consumer must deduplicate or be idempotent; the mechanics of making that honest (idempotency keys, exactly-once taxes) are the territory of [exactly-once semantics](../../distributed/messaging-internals/exactly-once-semantics.md). The producer, meanwhile, learns nothing about the effect — the ack from the broker certifies storage, not consumption.
- **Backpressure becomes buffering.** A slow consumer does not slow the producer; the difference accumulates as broker lag. That lag is either monitored and acted on (the queue-full and credit-window paths in [backpressure](../connection-atlas/backpressure.md)) or silently grows until retention expires and messages vanish. RPC's "buffer" is the caller's blocked thread — bounded and painful. A queue's buffer is the broker's disk — generous and deceptive.
- **Ordering is scoped, never global.** Kafka gives per-partition order; competing consumers destroy even that unless work is keyed. Cross-producer ordering does not exist. Any workflow that assumes "the update arrives after the create" must encode sequence in the payload or move to request/response.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Synchronous RPC | Queue-based messaging |
|----------|-----------------|------------------------|
| Caller learns the outcome | Yes — in-line, within the call's deadline | No — only the broker's storage ack; consumption is unobservable to the producer |
| Temporal coupling | Full: both endpoints must be up simultaneously | None: broker bridges outages and deploys |
| Failure visibility | Immediate, attributable (this call, this callee) | Deferred, diffuse (rising lag, dead-letter queue hours later) |
| Delivery contract | At-most-once unless caller retries; retry + dedup = caller's job | At-least-once by default; dedup/idempotency = consumer's job |
| Ordering | Per call chain, trivially causal | Per-partition at best; no cross-producer order |
| Backpressure | Implicit, upstream, thread-bounded | Buffering on the broker; needs lag monitoring and credit limits |
| Deadline propagation | Native (deadline headers) | Impossible for queued work; consumer-side policy only |
| Burst absorption | Callers fail or block under burst | Smooths bursts; latency paid as lag, not errors |
| Operational surface | Client libraries, connection pools, load balancing | Broker fleet, retention, consumer groups, rebalancing, DLQs |
| Test/dedup story | Straightforward mocks | Requires fake brokers, redelivery simulation, poison-message drills |

The **deferred-failure** mechanism deserves the arrow drawn. With RPC, the system's worst state — the dependency is down — is announced within seconds, to the code that cares, with context. With a queue, the same outage is announced as a gradually rising consumer-lag graph, noticed by whoever owns that dashboard, correlated by humans. Queues do not remove failures; they *relocate* them from the caller's exception handler to a monitoring pane, and the cost of that relocation is paid in mean-time-to-detection. The queue's second characteristic failure is the **poison message**: one malformed payload that crashes consumers, gets redelivered, crashes them again — the consumer group spends its whole budget re-failing one record until a dead-letter policy or human intervenes. RPC's equivalent bad input merely fails one request.

## Step 4: When Each Wins

**RPC wins** when: the caller needs the answer to proceed (auth checks, pricing, reads of any kind); the operation is user-interactive and latency-bound; the action must not silently duplicate (payment capture — a failed call at least tells you it *might* have failed, and you can reconcile); callee and caller share a team, an SLO, and a deploy train. Simple request/response over HTTP is also the industry's most understood and most instrumented protocol — the [REST vs gRPC](./rest-vs-grpc.md) comparison picks its *shape*, not whether to make it.

**Queues win** when: the producer must not fail because the consumer is down (fan-out to analytics, notifications, cache invalidation); work is bursty and the consumer can catch up later; multiple consumers need the same stream independently; the pipeline's throughput matters more than any single record's latency; retries-with-backoff over minutes or hours are semantically fine (image processing, report generation). The escalation ladder for these systems — delivery guarantees, broker internals, ordering keys — is climbed in [message queues](../followup-tree/message-queues.md).

**The honest hybrid** — where production systems actually live: accept the request synchronously just long enough to validate it and commit it durably (an order row, a job record), return an ID, and do the heavy work through a queue downstream. The user gets an honest "received" and a poll path; the failure mode this prevents is the checkout that blocks on an email provider.

## Step 5: Edge Cases and Counterexamples

- **Request-reply over a queue: the worst of both, sometimes the only option.** Put a command on a queue with a correlation ID and a `reply-to` address, then block (or poll) for the reply message. This is the mandated trap: you keep the caller's waiting, but lose every RPC guarantee. The reply may be at-least-once duplicated; the reply queue is itself a consumer that can fall behind; if the caller times out, the reply may still arrive — orphaned — and *the command may still execute*, so the caller must reconcile by correlation ID, idempotency key, or a status query. Justified when the only channel the callee offers is a queue (mainframes, IoT gateways, JMS-to-HTTP edges); unjustified when the motive is "queues are more scalable" — scalability here is paid for with a hand-rolled correlation layer.
- **The queue that hid a six-hour outage.** A consumer silently dead for six hours, zero errors anywhere: producers healthy, broker healthy, dashboards green except one lag graph nobody paged on. RPC would have failed callers within seconds and paged an SRE; the queue converted a Sev-1 into a backlog. The lesson is not "avoid queues" but "a queue's SLO must include lag," not just broker availability — lag *is* the user-visible degradation for every consumer that promises freshness.
- **RPC that outperforms "async everything."** A team migrated reads (product detail lookups) onto a queue "for resilience." Latency went from 30 ms to 800 ms–2 s (queue round trips plus consumer poll time), and the read path gained at-least-once duplication bugs against a cache. Reads are questions; questions want answers, not acknowledgments. Asynchronous messaging is a posture for *work*, not a universal resilience coat — resilience for reads means caches, replicas, and failover.
- **Retry storms migrate, not vanish.** The synchronous retry storm has a well-known defense (the circuit breaker). The queue version is subtler: a failing consumer with max-redelivery disabled redelivers forever, consuming the partition's entire throughput; the *broker* now looks healthy while delivering nothing new. Poison-pill detection (redelivery-count headers, quarantine queues) is the queue-side circuit breaker.
- **Idempotency debt compounds on the queue side.** At-least-once is the contract, so every consumer pays an idempotency tax on every message type, forever. Teams that "know dedup is needed" still get burned by the second-order case: two different event types (create-user and update-user) whose handlers share a non-idempotent side effect (a welcome email keyed on user ID but not on event). The dedup key is part of the API design, not an implementation detail.

## Step 6: Decision Framework

1. **Does the next line of code need the result?** Yes → RPC (or a DB read). No → the door opens to a queue; continue.
2. **Must the caller know the effect happened, with attribution, within seconds?** Yes (payments, authz, anything user-visible) → RPC, plus reconciliation tooling for the timeout-gray zone.
3. **Must the work survive callee downtime and deploy windows?** Yes → queue; the broker's durability is the feature.
4. **Is the caller's failure to enqueue acceptable when the broker is down?** If losing the record is unacceptable, you need a transactional write (outbox) before the queue — the [app events vs CDC](./app-events-vs-cdc.md) comparison.
5. **Is ordering across records required?** Global or cross-producer ordering → RPC per-entity or a single-partition design with its throughput ceiling; per-key ordering sufficient → keyed queues.
6. **Default in doubt:** validate-and-commit synchronously, process asynchronously — a 200 with a job ID and a durable record beats both a 30-second blocked checkout and a silently dropped fire-and-forget.

## Interview Questions

1. **Why is "queues are more scalable than RPC" an incomplete claim?** Queues move the scaling problem from simultaneous capacity to deferred capacity: per-record latency becomes lag-dependent and unbounded, failure detection degrades from seconds to dashboard-notice, and the consumer must pay an idempotency tax. Scalability is bought with observability and semantics, not for free.
2. **Your team proposes request-reply over a queue to "keep things loosely coupled." What do you insist on before approving?** Correlation IDs end to end, reply timeout semantics that acknowledge the command may still execute after timeout, idempotent command handling keyed by message ID, a bounded reply queue with its own consumer, and a status-query endpoint as the reconciliation path of record.
3. **A consumer is down six hours; producers never noticed. What was missing?** A lag-based SLO with paging, not broker-health paging. For freshness-promising consumers, consumer lag *is* availability. Also missing: dead-letter alerting and an end-to-end synthetic message that would have detected stalled consumption within minutes.
4. **When is fire-and-forget *wrong* even though nobody waits for the result?** When the record's loss or duplication is a correctness event, not a cosmetic one: payment events, ledger entries, security audit trails. Then the producer needs transactional enqueue (outbox/CDC) rather than a best-effort publish, because "nobody waits" is about latency, not about caring whether the thing happened.
5. **How does deadline propagation behave differently across the two models?** RPC frameworks carry deadlines downstream, so a 200 ms edge budget is divided and enforced across the call subtree; a queued task inherits no deadline because it had no start time when the budget was set. The queue equivalent is a per-message TTL plus consumer-side processing budgets.

## Key Takeaways

- The fork is **who waits**: RPC pins caller and callee timelines and returns named errors in-line; queues cut the pin and convert failure into lag, redelivery, and deferred detection.
- RPC's signature strengths: causal consistency per call, deadline propagation, immediate failure attribution. Its signature weakness: temporal coupling — the caller's availability is the callee's availability.
- Queues' signature strengths: burst absorption, outage bridging, independent consumers. Their signature weakness: the producer becomes ignorant of outcomes, and failures surface as rising graphs rather than raised exceptions.
- Request-reply over queues is a legitimate bridge for organizational boundaries and a trap for everything else — it re-adds waiting while subtracting every guarantee that made waiting safe.
- The production default is a hybrid: synchronous validation and durable commit, asynchronous execution, and a status query — each part of the system waits exactly where waiting is required.

## Cross-References

- [REST vs gRPC: Why-Not Handbook](./rest-vs-grpc.md) — choosing the *shape* of the synchronous call this page's first half commits to.
- [Push vs Pull: Why-Not Handbook](./push-vs-pull.md) — the pacing-ownership fork underneath broker push and consumer pull.
- [App Events vs CDC: Why-Not Handbook](./app-events-vs-cdc.md) — how to get a message into a broker without the dual-write problem.
- [Message Queues: Follow-up Tree](../followup-tree/message-queues.md) — the escalation ladder from delivery semantics to broker internals.
- [Timeouts and Retries: Assumptions Hunt](../assumptions-hunt/timeouts-and-retries.md) — the retry-storm mechanics behind RPC failure cascades.
- [Backpressure: Connection Atlas](../connection-atlas/backpressure.md) — queue-full paths and credit windows when buffers fill.
- [Queues](../../distributed/messaging/queues.md) and [Kafka](../../distributed/messaging/kafka.md) — broker mechanics behind the async half.
- [Exactly-Once Semantics](../../distributed/messaging-internals/exactly-once-semantics.md) — the consumer-side dedup obligations at-least-once imports.
- [Circuit Breakers](../../distributed/microservices/circuit-breakers.md) — the synchronous side's defense against retry storms.
- [gRPC](../../networks/http/grpc.md) — deadline propagation and HTTP/2 multiplexing mechanics.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
