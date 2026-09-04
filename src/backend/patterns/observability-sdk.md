# Observability SDK Internals: Designing Logging, Metrics, and Tracing Libraries

The book covers observability from the operator's seat — what
[traces](../observability/distributed-tracing.md), metrics, and logs are and how the
OpenTelemetry [pipeline](../observability/opentelemetry.md) moves them. This page takes
the library author's seat: you are designing the SDK that applications embed, which
means your code runs on the request path, inside every thread pool, under the memory
budget of someone else's process. An observability SDK is a forced exercise in the
hardest library-design constraints at once: it must be *optional* (the app runs fine
with telemetry off), *incur negligible cost when on*, *never harm the host under
failure*, and keep a stable API across vendor and backend churn.

## The API / SDK / Exporter Split

The defining layering decision, inherited from OpenTelemetry:

```text
┌──────────────────────────────────────────────────────────────┐
│ API      interfaces + no-op default; stable; embedded in     │
│          shared libraries (web frameworks, DB drivers)       │
├──────────────────────────────────────────────────────────────┤
│ SDK      implements the API; owns processors, samplers,      │
│          registries, aggregation; bound once by the app      │
├──────────────────────────────────────────────────────────────┤
│ Exporter protocol-specific transport (OTLP, stdout, vendor); │
│          swappable without touching instrumentation          │
└──────────────────────────────────────────────────────────────┘
```

- **API layer.** Interfaces plus working no-op implementations. When the app has not
  bound an SDK, the API returns no-ops: the trace spec requires that a non-recording
  span discard data "right away," making the span "effectively a no-op." This is what
  lets a web framework ship with tracing calls compiled in — an app that never
  configures telemetry pays for a flag check, not a pipeline. Design rule: *the API
  must be safe, correct, and cheap with nothing bound.*
- **SDK layer.** Implements the API for real and **owns all configuration** — the spec
  assigns SpanProcessors, sampler, and limits to the `TracerProvider`, with updates
  propagating to already-issued Tracers (they hold a provider reference rather than
  copying config). The provider is the composition root: one object the app builds at
  startup, everything else resolves through it.
- **Exporter layer.** Protocol adapters behind a tiny interface (`Export(batch)`,
  `Shutdown`, `ForceFlush`). Vendors ship exporters; apps switch backends by changing
  one constructor argument, not by re-instrumenting.

The payoff is a dependency-graph property: instrumentation libraries compile against
the API alone, so they neither know nor care whether the app binds an SDK, which SDK,
or which vendor's exporter. That is also the *API evolution* story (below).

```python
# App composition root — the only place that knows about the SDK.
provider = TracerProvider(resource=Resource.create({"service.name": "checkout"}),
                          sampler=ParentBased(root=TraceIdRatioBased(0.01)))
provider.add_span_processor(BatchSpanProcessor(OtlpSpanExporter(endpoint=...)))

# Library code — API only, no SDK imports, no-op unless the app bound one.
tracer = trace.get_tracer("payments.retry")          # instrumentation scope
with tracer.start_as_current_span("charge.retry") as span:
    span.set_attribute("attempt", attempt)
```

## Metrics SDK

### Instrument semantics

| Instrument | Semantics | Hot-path cost |
|---|---|---|
| Counter | Monotonic `add(x)`, x ≥ 0 | one lookup + one add |
| UpDownCounter | Signed add (queue depth, active conns) | one lookup + one add |
| Gauge | Last value wins (temperature, in-flight) | one store |
| Histogram | Distribution per export interval | bucket index + increment |

Synchronous instruments record on the caller's thread; asynchronous (observed via
callback at collection time) invert the pull — right choice for values the runtime
already knows (JVM heap), wrong for request counts. The spec gives instruments
*advisory parameters* — e.g. `ExplicitBucketBoundaries` and an attribute suggestion —
so the instrument author can hint defaults without hard-coding them.

### Where aggregation happens: client-side, by design

The SDK aggregates into *streams* — one stream per metric + attribute-set — and
exports aggregates, not raw events. This is a deliberate architectural choice with
three consequences:

1. **Memory is bounded by cardinality, not traffic.** A counter at 100k RPS costs the
   same as one at 1 RPS: a single integer per stream. Raw-event export (trace-style)
   would move 100k values/sec down the wire; aggregation keeps the export at one
   sample per stream per interval.
2. **Cardinality becomes the load-bearing invariant.** Each distinct attribute set is
   a time series downstream — the [multiplication rule](../../sre/metrics-cardinality.md)
   applies at SDK level first: per-user labels multiply streams *inside the
   application's heap* before they ever reach a collector.
3. **Histograms are quantized at record time.** Which buckets exist is decided when
   the instrument/view is created, not at query time (the
   [HdrHistogram](https://hdrhistogram.github.io/HdrHistogram/) lineage: bucket layout
   is the cost/precision dial). Explicit boundaries are cheap and queryable; base-2
   exponential buckets auto-scale across magnitudes at the cost of readable bucket
   edges. Changing buckets later changes what you can compute — bucket choice is an
   API-evolution decision, not a tuning knob.

### Delta vs cumulative temporality

A cumulative export reports each stream's value since process start; delta reports the
change since the previous export. The spec makes temporality a property of the metric
*reader* (e.g. `PeriodicExportingMetricReader(temporality=...)`), because it is a
wire-format decision, not an instrumentation one: the aggregation is identical, only
the export differs. Cumulative is the Prometheus model — counters that only increase,
rate computed at query time, tolerant of lost scrapes. Delta is friendlier to
push-based backends and stateless collectors (each batch is self-contained, no
restart-aware reset handling) but the backend must sum deltas itself. Get this wrong
and your dashboards are subtly broken after every deploy — cumulative export must
handle the counter *reset* that a restart produces.

### Cardinality governance at the SDK level

The spec's answer is the **View** — a transform applied between instrument and stream:

```python
meter_provider.add_view(
    "http.server.duration",
    attribute_keys=["route", "method", "status_class"],   # allow-list
    aggregation=ExplicitBucketHistogramAggregation(
        boundaries=[5, 10, 25, 50, 100, 250, 500, 1000]),
    aggregation_cardinality_limit=1000,
)
```

- `attribute_keys` is an **allow-list**: the spec says attributes on the allow-list
  are kept and *"all other attributes MUST be ignored"* — the SDK-level analog of
  scrape-time relabeling, applied before memory is spent.
- The **cardinality limit** is "a hard limit on the number of Metric Points that can
  be collected during a collection cycle," enforced *after* attribute filtering, with
  a designated overflow attribute absorbing the excess so the SDK can say "≥ N more
  streams existed" instead of lying.
- `DropAggregation` disables an instrument entirely — the kill switch for a metric
  that turned out to be a cardinality bomb in production, without a redeploy of the
  instrumenting library.

The design lesson: cardinality is a *contract* the SDK enforces, not advice the
backend begs for.

## Logging SDK

### Async appenders and bounded queues

A synchronous logger pays disk/syslog latency inside the application thread; an async
appender reduces the call to "format-lite, enqueue, return," with a background thread
draining to the real sink. Log4j2's async loggers are the reference design: events go
into a pre-allocated ring buffer (default 256×1024 slots in standard mode, 4×1024 in
GC-free mode) that "will never grow or shrink during the life of the system," with
documented trade-offs: higher peak throughput and dampened latency spikes, but *lower
sustainable throughput* — if the app out-logs the drain rate for long enough to fill
the queue, something has to give.

That "something" is the **queue-full policy**, and it is the key design decision:

```text
policy           behavior                              use when
─────────────────────────────────────────────────────────────────────
block            caller waits for queue space          batch jobs; never on request path
drop-newest      ignore the incoming record            keep most recent context
drop-oldest      evict head, append new                keep the freshest tail of context
drop-below-LVL   discard records at/below threshold    log4j2 Discard policy (default INFO)
```

Log4j2 defaults to *blocking* on a full queue and offers `Discard` (drop everything at
or below a threshold level, INFO by default) as the graceful alternative — the
policy hierarchy itself encodes the insight that a DEBUG storm should degrade to
WARN-only output, not to a hung application. Whatever the policy, the SDK must
**export a drop counter as a first-class metric**: drops are a leading indicator that
the application is producing telemetry faster than the pipeline drains, and silent
drops are how "we have logs" quietly becomes "we have the logs that survived."

### Backpressure coupling to app health

Bounded queues make the logger an application-health sensor. Sustained queue
saturation means the process is logging at a rate its own I/O cannot sustain — the
same overload shape as any [bounded queue](./backpressure-pattern.md), but with a
diagnosis twist: the producer is the application, so the fix is either level
filtering, sampling, or fixing whatever is emitting at pathological volume (a retry
loop logging per attempt is the classic). Expose queue depth and drop rate; alert on
them like any saturation signal.

### Level filtering cost and trace-context injection

- **Level filtering must be cheap before formatting.** The guard (`is_enabled(level)`)
  is one integer compare; the expensive part is argument construction — which is why
  lazy messages (suppliers/lambdas) exist: `log.debug(() -> "state=" + dump(state))`
  avoids building the dump when DEBUG is off. An SDK that formats, then filters, has
  the cost model backwards.
- **Structured logs** are key-value records with a schema, not formatted strings.
- **Trace-context injection happens at emit time, in the caller's context.** The spec's
  log record carries `TraceId`, `SpanId`, `TraceFlags`; the processor populates them
  from the current span context when `emit` is called. Injecting at *serialization*
  time — after the record crossed the async boundary into the background thread — is
  the classic bug: the background thread has no request context, so every log line
  either loses its trace ID or, worse, inherits the wrong one. Same rule as every
  context-capture design: capture in the caller's world, use it later.

## Tracing SDK

### Span context propagation

Context is the `SpanContext` (trace-id, span-id, flags, trace state) carried across
boundaries via propagators. The W3C `traceparent` header is
`version-trace-id-parent-id-trace-flags` — lowercase hex, 32 hex chars (16 bytes) for
the trace id, 16 for the span id, 2 for flags. The versioning rules are the
interoperability contract every instrumentation library implements: version `ff` is
forbidden; for an unknown-but-valid version, parse only the fields defined for it,
"MUST NOT parse or assume anything about unknown fields," and rebuild outgoing headers
with "the highest version of the specification known to the implementation." Baggage
rides separately and must be treated as untrusted input — size-limited, allow-listed,
never promoted into indexed attributes by default (the
[cardinality bomb](../observability/distributed-tracing.md) lives here too).

### Context object design: implicit vs explicit

- **Implicit** (thread-locals / `contextvar`s): `start_as_current_span` reads the
  current context, so application code stays clean. The cost model: one lookup per
  span creation, plus the runtime's context-propagation semantics.
- **Explicit**: context passed as an argument — verbose, but immune to the runtime's
  threading quirks.

The async-runtime interaction is where SDKs earn their keep. Python's `contextvars`
copy *into each `Task`* (a `ThreadPoolExecutor` thread does **not** inherit the
submitter's context unless you pass `contextvars.copy_context()`); Java needs wrapped
executors that capture-and-reinstall context around each task. The generic bug shape:
traces work in tests (single-threaded), then lose parents in production at exactly the
thread-pool boundary. An SDK designed for real runtimes ships executor wrappers and
documents the boundary — it does not leave capture discipline to the user.

### Sampling: head vs tail, parent-based

Head sampling decides at the trace root; children inherit via the propagated decision,
which is why the sampler set includes `ParentBased(...)` wrapping — without
parent-inheritance, every service flips its own coin and you get partially-sampled
trees. `TraceIdRatioBased` must be deterministic on the trace id (a hash decision, not
a random draw per service) so the same trace id yields the same decision everywhere.
Tail sampling waits for the full trace and lives in the collector, where the buffering
costs are someone else's sizing problem — see
[sampling economics](../observability/distributed-tracing.md); the SDK's job is only
head decisions plus the `sampled` flag's downstream meaning.

### The span buffer and BatchSpanProcessor

The SDK buffer is a bounded in-memory queue drained by the batch processor. The spec
fixes the semantics — and every parameter is a trade-off you should be able to defend:

| Parameter | Default | Trade-off |
|---|---|---|
| `maxQueueSize` | 2048 | memory vs drop rate; **spans beyond this are dropped** |
| `scheduledDelayMillis` | 5000 | latency-to-backend vs export frequency (network batching) |
| `maxExportBatchSize` | 512 | batch efficiency vs time-to-drain |
| `exportTimeoutMillis` | 30000 | bound on how long a stalled backend can back up the pipeline |

Exports trigger on the delay elapsing, on the queue reaching batch size, or on
`ForceFlush`. `SimpleSpanProcessor` (export inline on `End`) exists for tests and
debugging: it preserves order and latency semantics but puts exporter latency on the
application thread.

**What gets lost on crash, and why that is acceptable:** every span sitting in the
queue when the process dies is gone — no disk spill, no journaling. This is a
deliberate design stance, not an oversight: tracing is a *sampled diagnostic*, not a
durable record. The sample rate already discards 99%+ of traces by design, and
crash-loss is roughly uniform across traffic, so the surviving sample stays
representative. Making span durability real would cost a write path (disk, fsync,
replay) on every request — a tax on everyone to save the last 5 seconds of telemetry
during exactly the crash where the application's own logs and core dumps carry the
evidence. If you need durable per-request evidence, that is an audit log with
different guarantees — and a different library.

## Thread Safety of Shared Registries

Every SDK has hot shared state: the meter/tracer registries (name → instrument), and
per-stream aggregation slots. The design pattern:

- **Registries are read-mostly.** The same instrument name is looked up millions of
  times and created once → `ConcurrentHashMap.computeIfAbsent`-style semantics:
  lock-free reads on the steady-state path, atomic create-once on the cold path, and
  careful double-registration semantics (the spec requires duplicate instrument
  registration to be detected and resolved, not silently duplicated).
- **Recording is contention-shaped, not lookup-shaped.** A counter add is a fetch-add
  on one cache line; 50 threads recording one hot counter serialize on that line. The
  `LongAdder` answer applies: per-thread cells (striped counters) that sum at
  collection time — read side pays, write side scales.
- **Histogram stream creation is the dangerous write.** First record for a new
  attribute set must allocate stream state; stripe the creation lock by name hash so
  concurrent first-records of *different* streams do not serialize behind one lock.
- **Copy-on-write for configuration.** Views/filters change rarely; publish an
  immutable snapshot behind a volatile reference rather than locking recorders against
  reconfiguration.

The performance contract to state out loud: with telemetry configured, the SDK adds
`O(1)` work per record with no locks on the steady-state path; if an SDK shows up in
lock profiles, that is a bug, not an inherent cost.

## API Evolution: How OpenTelemetry Stabilized

The OTel stability model is a case study in evolving a shared API without breaking
embedded libraries:

- **Merged predecessors, one API.** OpenTracing and OpenCensus were subsumed; the
  spec's compatibility sections describe mapping rather than parallel maintenance —
  and the stability document is explicit that even superseded APIs keep support
  ("OpenTelemetry already supports two tracing APIs... we invented a new tracing API,
  but continue to support the old one").
- **Signals stabilize independently.** Each signal moves through a lifecycle
  (development → stable → deprecated → removed) *component by component*, with the
  API required to stabilize before the SDK — so instrumentation could be written
  against a frozen trace API while the metrics and logs APIs were still moving.
  Breaking changes are permitted only in Development status; stable APIs are
  SemVer-governed.
- **The no-op default made adoption safe.** Because unconfigured API calls are
  functional no-ops, libraries adopted the API *before* any backend existed — the
  adoption path did not require the app to change anything.
- **Extension over mutation.** New capabilities (advisory parameters, configurators,
  composite samplers) attach as optional hooks with documented defaults, keeping the
  core interface frozen.

The transferable rule for any SDK you design: *freeze the small API that embedded
libraries see; move all risk (config, exporters, processors) into the layer only apps
touch.*

## Interview Follow-Ups

1. **"Your metrics SDK doubles the application's p99. Debug it."**
   Profile first — assume contention before allocation. Usual suspects, in order:
   (a) a lock around recording (a registry or stream lock hit per record — should be
   lock-free per the contract above); (b) one hot counter with a single fetch-add
   line (fix: per-thread cells); (c) attribute normalization per record — building a
   label map/hash for every call (fix: pre-bound instrument handles, cached
   attribute sets); (d) histogram with thousands of explicit buckets (index search
   linear — fix: fewer boundaries or exponential layout); (e) GC pressure from
   per-record allocations. Verify with a flame graph under production-shaped load,
   not a microbenchmark of `counter.add(1)`.

2. **"Why is dropping spans on crash acceptable, but dropping audit logs isn't?"**
   Traces are sampled diagnostics — the design already accepts 99% loss and stays
   representative; audit logs are durable records with per-event identity, where loss
   is a compliance failure. Different products need different delivery guarantees;
   one buffer design cannot serve both.

3. **"Where do you inject trace context into logs, and why?"**
   At `emit`, in the caller's context — the log record's TraceId/SpanId fields are
   populated from the current span before the record crosses into the async drain
   thread. After that boundary the request context is gone; injecting at serialize
   time yields missing or wrong trace IDs.

4. **"Design zero-overhead telemetry when disabled."**
   No-op implementations behind the API, a recording/sampling flag checked before any
   attribute work, lazy argument evaluation, and an SDK-free classpath so the JIT
   sees a leaf call it can inline and prove cold. Measure: a disabled span create +
   end should be a few nanoseconds.

5. **"Delta or cumulative — decide for a fleet that already has Prometheus."**
   Cumulative at the SDK boundary (matches scrape semantics, tolerates lost scrapes,
   handles restart resets at query time), unless a specific push-based backend or
   stateless-collector architecture needs delta — and then convert centrally, not
   per-app, so dashboard semantics stay uniform.

## Cross-References

- [Distributed Tracing: Propagation, Sampling, and Storage](../observability/distributed-tracing.md) — sampling economics and trace storage
- [OpenTelemetry for Production Observability](../observability/opentelemetry.md) — signals, semantic conventions, the Collector pipeline
- [Metrics Cardinality Explosions](../../sre/metrics-cardinality.md) — the downstream cost this SDK design fights
- [Exemplars](../../sre/exemplars.md) — linking metric buckets back to traces
- [Backpressure Pattern](./backpressure-pattern.md) — the bounded-queue theory behind log/span buffers
- [Messaging and Streaming](../../distributed/messaging/messaging-streaming.md) — propagating context through queue boundaries

## References

1. OpenTelemetry Specification — [overview](https://opentelemetry.io/docs/specs/otel/),
   [Trace API](https://opentelemetry.io/docs/specs/otel/trace/api/),
   [Trace SDK](https://opentelemetry.io/docs/specs/otel/trace/sdk/) (span processors,
   batching parameters, sampler set),
   [Metrics API](https://opentelemetry.io/docs/specs/otel/metrics/api/) (instrument
   semantics, advisory parameters),
   [Metrics SDK](https://opentelemetry.io/docs/specs/otel/metrics/sdk/) (views,
   cardinality limits, aggregations, temporality),
   [Logs SDK](https://opentelemetry.io/docs/specs/otel/logs/sdk/) (log record
   processors, trace fields on records).
2. [Versioning and stability for OpenTelemetry clients](https://opentelemetry.io/docs/specs/otel/versioning-and-stability/)
   — signal lifecycle, API-before-SDK rule, the "no version conflict, ever" guarantee.
3. [W3C Trace Context](https://www.w3.org/TR/trace-context/) — traceparent format,
   version `ff` forbidden, unknown-version parsing rules.
4. [Log4j2 Asynchronous Logging manual](https://logging.apache.org/log4j/2.x/manual/async.html)
   — ring buffer sizing, `AsyncQueueFullPolicy` (block vs discard), throughput trade-offs.
5. [HdrHistogram](https://hdrhistogram.github.io/HdrHistogram/) — client-side bucket
   layout as a precision/cost dial.
6. Sigelman et al., "Dapper, a Large-Scale Distributed Systems Tracing Infrastructure"
   (2010): https://research.google/pubs/pub36356/ — instrumentation layers and
   sampling design this API shape descends from.
