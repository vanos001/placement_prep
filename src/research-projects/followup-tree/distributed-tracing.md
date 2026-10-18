# Follow-up Tree: Distributed Tracing

## Overview

"An endpoint takes 900 ms and calls twelve services — how do you find where the time went?" is the observable-systems opener, and it escalates into one of the most senior rungs in reliability interviews because tracing is where instrumentation, cost, and privacy collide. The ladder runs from the span model (what a trace actually records), through context propagation — the mechanism that makes twelve services one story, including the async and queue hops where propagation dies — into sampling, the economics that decide what you can afford to record, and ends at the expert rung: cardinality, storage, and the observability contract that joins traces to logs and metrics. The thread tying every rung together is *causality you can afford*: a trace is a causal hypothesis rendered in timestamps, and every design decision — propagation format, sampling rate, attribute policy — trades how much causality you keep against what it costs to carry, store, and query. This chain stays at the tracing mechanism; the surrounding pipeline (what a metric is, how logs and traces become one signal, where alerting reads from) is the atlas map [Observability Pipeline](../connection-atlas/observability-pipeline.md), and what NOT to put into recorded telemetry is the assumption audit [Logging and PII](../assumptions-hunt/logging-and-pii.md). The book-level survey is [Observability](../../distributed/microservices/observability.md); the primary sources are the [Dapper paper](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/) (Google, 2010), the [W3C Trace Context](https://www.w3.org/TR/trace-context/) propagation standard, and the [OpenTelemetry trace model](https://opentelemetry.io/docs/concepts/signals/traces/). Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"A user reports a slow request. It touched twelve services. How do you find where the time went?"**

The expected core answer: reconstruct the request's causal tree from spans. A *span* is one timed operation — an RPC, a query, a function of interest — carrying a trace id, its own span id, its parent span id, start time, duration, and attributes; spans whose parent ids chain back to the ingress span form a *trace*, and reading each span's duration minus its children's durations exposes the unaccounted time — the standard way to discover that 400 ms is a database query nobody wrote an index for, or 300 ms is a serialization gap between services. The instrumentation exists because the first service on the path *started* the trace and every downstream hop *continued* it: the trace id and current span context ride request headers, each service creates a child span before calling out, and the spans are exported to a backend that stitches and indexes them.

A weak answer says "we use Jaeger/Zipkin" or "we add a request ID to logs" — a tool name without the span/parent model, or an ID without causality (a request id correlates; it does not decompose latency into a tree). The strong answer names the three fields that make a tree (trace id, span id, parent id), states that durations nest causally, and volunteers that the hard part is *propagation*, not recording. The follow-up that escalates: **"The trace stops at your message queue and restarts at the consumer. What exactly is missing?"** — which moves the ladder from model to propagation.

## Level 2: Spans and Context Propagation

**What it tests:** whether you can state the mechanism that carries causality across process boundaries — including the boundaries where it breaks.

**Weak answer:** "The trace id is in a header" — one field, no span/parent distinction, no answer for queues, thread pools, or async continuations, and no idea whose headers they are.

**Strong answer:** describes propagation as a wire format for the *current span context* — trace id, span id, sampling flags — that the caller injects (W3C `traceparent` is the standard: `version-traceid-parentid-flags` in one header) and the callee extracts to become the parent of its own spans; the callee creates a *child* span, so the parent id chain encodes the causal tree; and for fire-and-forget boundaries the context must be *carried inside the message payload or its properties*, because a queue decouples the processes in time.

**Escalation trigger:** "Trace context survives HTTP hops but your trace has a gap at the Kafka consumer. Why, and where do you fix it?"

**Answer.** Because HTTP instrumentation injects and extracts context at client and server boundaries automatically, while a queue splits one logical operation into two: the producer's send, the broker's transit, and the consumer's processing are three spans whose parent links must be carried *through the message* — either as message headers (Kafka record headers carrying `traceparent`) or explicitly via OpenTelemetry's propagator helpers. Where it is missing, the consumer starts a fresh trace with no parent and the backend cannot stitch; the fix is a producer-side extractor and a consumer-side injector around the queue client, and the senior observation is that the queue hop is not an edge case — it is the case where tracing earns its keep, because the *latency inside the broker* (offset lag, retry loops) is exactly the time a naive request-id log cannot attribute. The same discipline applies to thread hops inside one process: context is thread-local by default, so a work item handed to a pool must carry the span context explicitly, and losing it produces traces that end at the executor. Async boundaries are where instrumentation silently dies, and "check the queue consumer first" is the senior reflex.

The design twist: *baggage* — a small key-value set that propagates alongside span context — lets request-wide facts (tenant id, feature-flag state, user segment) ride every span without each service re-adding them; the cost is that baggage is a contract with every service on the path, and unbounded or privacy-sensitive baggage is how tracing systems turn into accidental data pipelines. The follow-up that escalates: **"You can't record everything. What do you drop, and when?"**

## Level 3: Sampling — the Economics of Recording

**What it tests:** whether "turn sampling down" is a principled decision you can reason about — head versus tail, what each preserves, and what each destroys.

**Weak answer:** "Sample 1% so the bill is low" — no distinction of *when* the decision is made, no awareness that naive head sampling can drop precisely the slow request you installed tracing to find.

**Strong answer:** distinguishes *head sampling* (decide at the root span, propagate the decision — deterministic cost, but blind: a uniformly-sampled system records boring traces and misses the tail) from *tail sampling* (buffer whole traces, decide at the end by policy — keep all errors, keep p99-latency traces, keep every trace for canary deploys), and explains the cost shift: tail sampling buys relevance by paying for buffering, memory, and a stateful component in the telemetry path.

**Escalation trigger:** "Your team proposes 100% sampling 'for a week, to be safe' before a big launch. Price it for them."

**Answer.** Price in three currencies. *Volume arithmetic:* a busy service emitting one span per downstream call means traces of tens of spans; at thousands of requests per second, 100% is tens of millions of spans per hour, which prices the collector fleet, the buffer memory for tail decisions, and the backend's write path — the reason Dapper reported single-digit-percent baseline sampling as sustainable at Google scale. *Query economics:* storage is not the constraint people fear; the constraint is *findability* — a backend indexed on service/operation/latency answers "show me slow checkout traces" only if span attributes stay bounded (next rung). *Signal economics:* 100% of a steady state is 100% redundancy — the marginal information of the ten-thousandth identical healthy trace is zero, which is why the sane baseline is probabilistic head sampling for volume plus targeted tail policies (all errors, latency outliers, new-code rollouts) for signal. The senior framing: sampling policy is a *retention policy for causality* — define what question you will ask during an incident (all failed requests, the slowest 1%, everything from the canary), and configure policies that guarantee those traces exist. The OpenTelemetry tail-sampling processor exists precisely because this policy composition is the common case, not the exception.

The design twist the strong candidate volunteers: *the sampling decision must propagate.* With head sampling, the root's decision rides the context so all services in one trace agree — otherwise a trace is 40% recorded and unreadable; with tail sampling, the decision is deferred but the *possibility* must be preserved by buffering everywhere. This is why "sampling flags" is a field in the propagation header, not an implementation detail. The follow-up that escalates: **"Storage keeps growing and queries keep slowing. What is actually in those spans?"**

## Level 4: Cardinality, Cost, and the Observability Contract

**What it tests:** the expert rung — span attributes as unbounded data, traces as the join key across signals, and PII as the compliance edge of instrumentation.

**Weak answer:** "Traces are just big logs" — no attribute-cardinality model, no trace-to-log join, and no reaction to "the support engineer pastes a customer's email into a span tag."

**Strong answer:** separates span *identity* (bounded: trace/span/parent ids) from span *attributes* (unbounded by construction: every engineer adding a tag adds a label the backend must index), states the cardinality discipline (attributes should be low-cardinality dimensions: service, endpoint, error type — not user ids, order ids, or free text), explains that trace id is the *join key* that links a metric spike to the exact failed spans to the exact log lines, and knows the privacy boundary: telemetry systems are downstream of GDPR because payloads, URLs, and baggage carry personal data unless redacted at emission.

**Escalation trigger:** "Design the tracing strategy for a new microservice platform. What is recorded, sampled, bounded, and who enforces it?"

**Answer.** The strategy is a platform contract, not per-team taste. *Recorded:* spans at every network and queue boundary plus one manual span per business operation the on-call needs to see — auto-instrumentation for the boundary work, explicit spans only where causality is non-obvious. *Sampled:* head-sampling baseline for volume with tail policies for errors, latency outliers, and deploys; the policy is configuration reviewed like code because it decides what incidents are reconstructable. *Bounded:* an attribute allowlist enforced at the collector — services may attach service-name, endpoint-template, and error-class; they may not attach raw SQL, full URLs with query strings, or identifiers that belong to the PII class (the emission-side discipline of [Logging and PII](../assumptions-hunt/logging-and-pii.md)); URL templating happens at instrumentation so `/users/418/orders` becomes `/users/:id/orders` *before* it becomes an indexed dimension. *Joined:* the trace id is propagated into log lines and attached to exemplar metrics, so the three signals are one story told at three granularities — the integration the atlas map [Observability Pipeline](../connection-atlas/observability-pipeline.md) draws end to end, and the reason a platform that adopted tracing but not log correlation still has slow incidents. *Enforced:* at the collector, not by convention — because an unenforced allowlist is a suggestion, and cardinality explosions are discovered during the incident when the query times out. The sentence that ends the chain well: tracing's deliverable is not the flame graph; it is the *guarantee that the causal record for any bad request exists and is findable in under a minute* — everything above is how that guarantee is paid for.

## How to Approach Unfamiliar Variations

The template for tracing variations — "traces or logs first," "eBPF-based tracing without code changes," "the trace volume tripled after a deploy":

1. **Ask what causality the variation preserves.** Every mechanism — header propagation, message-embedded context, eBPF-synthesized spans — is a way to keep the trace/parent tree intact across a boundary. If the tree breaks, the tool is decoration regardless of vendor.
2. **Answer cost questions in spans-per-second, not gigabytes.** Span count drives collectors, buffers, and indexing; converting any proposal to spans/sec makes head-vs-tail trade-offs computable.
3. **Treat attributes as a schema, not a log.** Each attribute is a future index key; high-cardinality values are the tracing equivalent of an unindexed column — expensive forever.
4. **Name the incident you are buying.** "All errors retained" buys post-incident reconstruction; "p99 retained" buys latency forensics; "100% for canaries" buys deploy safety. If no incident class is named, the sampling policy is guesswork.

## Interview Questions

**Q: Your traces show a 300 ms gap between a service's span and its downstream call. What is on your hypothesis list?**
A: The gap is unaccounted time in the caller: queueing on a saturated connection pool (rung: pool sizing), serialization/deserialization of a large payload, CPU starvation on the caller (throttling from limits), or lock contention before the call. The trace proves the time is *inside the caller's span window* but outside its child spans; the fix direction is profiling that window, not adding more downstream spans.

**Q: Why does head sampling at 1% risk missing exactly the requests you care about?**
A: The decision is made at the root before the request's outcome exists, uniformly — so slow, failed, or anomalous requests are dropped at the same 1% rate as healthy ones, and over a day the tail you installed tracing to study is 99% absent. The remedy is tail sampling with error and latency policies, or a hybrid: low head-sampling baseline plus always-sample flags on canary traffic and error paths.

**Q: A queue consumer starts a brand-new trace id on every message. What is broken and what is the fix?**
A: Propagation across the queue boundary is missing — the producer's context was not written into message headers or the consumer did not extract it, so the consumer's spans are parentless and the backend shows two disconnected traces. Fix both sides: producer injects `traceparent` into record headers (OpenTelemetry propagator around the queue client), consumer extracts it as parent before creating its first span. The same check applies to thread-pool handoffs inside a service.

**Q: What makes `user_id=4821` a bad span attribute while `error_type=payment_declined` is a good one?**
A: Cardinality and intent. Attributes become indexed dimensions; an attribute whose value is near-unique per request multiplies index entries without answering any query you actually ask — "show declined payments across the fleet" filters on error_type, never on user_id, which is what the trace-to-log join via trace id is for. The rule: attributes are dimensions for questions, and per-entity identifiers belong in logs retrievable by the trace id, not in span tags.

## Key Takeaways

- A trace is a causal tree of spans — trace id, span id, parent id — and durations minus children expose unaccounted time; a request ID without parents is correlation, not tracing.
- Propagation is the mechanism that makes many services one trace, and async boundaries (queues, thread pools) are where it dies unless the context is carried explicitly.
- Head sampling decides blind and cheap; tail sampling decides informed and expensive — the sane design is a volume baseline plus policies that guarantee error and outlier traces exist.
- Span attributes are future index keys: low-cardinality dimensions only, URL templating and PII redaction at emission, enforcement at the collector.
- The deliverable is a guarantee — the causal record for any bad request exists and is findable quickly — and the trace id join across metrics, traces, and logs is what makes it usable.

## Cross-References

- [Observability Pipeline](../connection-atlas/observability-pipeline.md) — the map joining metrics, logs, and traces into one system, with traces as the join key.
- [Logging and PII](../assumptions-hunt/logging-and-pii.md) — the privacy boundary for span attributes, baggage, and payload capture.
- [Dashboards Mean Observability](../misconceptions/dashboards-mean-observability.md) — the misconception this ladder's causality model refutes.
- [Message Queues](./message-queues.md) — the queue mechanics that make the consumer-side propagation gap the common case.
- [SLOs and Error Budgets](./slos-and-error-budgets.md) — the reliability contract that decides which traces (burning SLOs) must be retained.
- [API Gateway](./api-gateway.md) — the usual root span: where traces start and where sampling decisions propagate outward.
- [Observability](../../distributed/microservices/observability.md) — the book-level survey of tracing backends and instrumentation patterns.
- [Exemplars](../../sre/exemplars.md) — metric-to-trace links that turn a latency spike into a specific trace id.
- [Dapper paper](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/) — the original tracing infrastructure design and its sampling economics.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) and [OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/) — the propagation standard and the vendor-neutral model behind modern instrumentation.
