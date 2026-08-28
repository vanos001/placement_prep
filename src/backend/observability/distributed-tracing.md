# Distributed Tracing: Propagation, Sampling, and Storage

A user request fans out into dozens of services; when it is slow, the
only tool that shows *where the time went across process boundaries* is a
trace. Distributed tracing is three engineering problems stapled
together: propagating context through every RPC, queue and thread hop;
deciding which 0.01% of requests to keep (sampling); and storing and
indexing billions of spans so a query over them returns in seconds. This
page covers the machinery underneath OpenTelemetry, the sampling
strategies that decide your bill and your debuggability, and the
storage-system design question every tracing backend is really solving.

The user-facing surface: [OpenTelemetry](../observability/opentelemetry.md)
covers the SDK/API semantics; [SLOs and error budgets](../../sre/slo-error-budget.md)
consume the percentiles tracing measures; [load-testing strategies](../../sre/load-testing-strategies.md) generate the traffic that carries
the traces.

## The trace model and propagation

A trace is a tree of spans; each span carries: trace id, span id, parent
span id, timestamps, attributes, and links. Propagation means moving a
*span context* across every boundary:

- **W3C traceparent**: the standard header
  (`00-<32hex traceid>-<16hex spanid>-<2hex flags>`), with `tracestate`
  for vendor-specific key-values. Version-prefix format means unknown
  versions must be passed through untouched - the compat rule every
  instrumentation library implements.
- **Hard boundaries**: thread pools (context must be captured and
  re-installed explicitly - the classic bug: tracing context lost across
  an async boundary), message queues (context serialized into message
  headers; batch consumers must *link*, not parent, when one message
  fan-outs), process handoffs (HTTP redirects carry new spans, not
  continuations).
- **Baggage**: cross-service key-values (tenant id, experiment bucket)
  that ride the context - and the cardinality bomb: baggage values
  propagate into span attributes and then into indexed storage unless
  explicitly filtered.

## Sampling: the economics of keeping 1%

You cannot store every span; sampling is where observability cost and
debuggability meet. The strategies, in decision order:

| strategy        | decides                        | keeps                     | failure mode                |
|-----------------|--------------------------------|---------------------------|------------------------------|
| head, probabilistic | at trace start, before work | p% of all traces         | misses the slow/rare request |
| head, parent-based | inherits upstream decision   | coherent trees            | root's coin flip decides all |
| tail, latency-based | after trace completes       | slowest x% + all errors   | needs full-trace buffering at the collector |
| tail, rule-based | after trace completes          | error + attribute matches | rule maintenance burden      |

Head-based sampling is cheap and coherent (all services honor the root's
decision via propagation) but blind: the interesting trace - the 1-in-
10^6 timeout - is thrown away before it happens. Tail-based sampling
keeps exactly those, at the cost of buffering every trace in the
collector for its full duration plus queueing - the collector becomes a
stateful, memory-hungry service whose sizing (and sharding by trace id)
is the real deployment cost. Production designs blend: head-sample at
10-100x cheaper rates plus tail-catch for errors and SLO-breach traces.

## Storage: the problem every backend is really solving

A tracing backend is a write-heavy, read-rare, range-scan-oriented
store: writes are continuous span streams (potentially millions/sec),
reads are by trace id (get one trace fast) or by service/operation/time
(finding candidate traces). The three generations:

- **Jaeger**: spans fan into Kafka, stored in Cassandra/Elasticsearch;
  trace-by-id lookups via the span's indexed fields. Mature, operationally
  heavy.
- **Tempo**: object-storage-first - spans written to compacted blocks in
  S3, indexed by a small in-memory index (trace-id -> block). Cheap at
  scale, query-by-id fast, ad-hoc search limited to indexed attributes.
- **Query-side alternatives** (ClickHouse-based vendors): store spans as
  rows in a columnar engine; search anything, pay with ingest cost.

The design axis is the usual one: index everything (expensive writes,
fast arbitrary search) vs index trace-id only (cheap writes, search via
service metrics to find candidate ids first). Tail-sampling interacts
directly: tail decisions need *all* spans of a trace co-located, which
pushes architectures toward trace-id-sharded collectors feeding
object storage.

## The demo: tail-sampling decisions and propagation

```python
#!/usr/bin/env python3
"""Two deterministic tracing models.

1. Head vs tail sampling yield: over a synthetic request population
   (seeded latencies, 0.5% errors), compute what each strategy keeps:
   - head 10%: uniform lottery, blind to latency
   - tail: keep 100% of errors + 100% of p99+ + 5% of the rest
   Report: fraction kept, and the fraction of 'interesting' traces
   (errors + slow) captured - the debuggability metric.

2. Propagation model: a service graph fan-out (gateway -> A,B -> C,D)
   with parent/child span ids and a baggage attribute that two services
   wrongly promote into indexed attributes - showing the cardinality
   growth."""

import random

rng = random.Random(9)
N = 20_000
traces = []
for i in range(N):
    slow = rng.random() < 0.004
    err = rng.random() < 0.005
    lat = rng.gauss(3000, 400) if slow else rng.gauss(80, 30)
    traces.append(("slow" if slow else "fast", err, max(10, lat)))

p99 = sorted(t[2] for t in traces)[int(0.99 * N)]

head_kept = [t for t in traces if rng.random() < 0.10]
tail_kept = [t for t in traces if t[1] or t[2] >= p99 or rng.random() < 0.05]

interesting = [t for t in traces if t[1] or t[2] >= p99]
def captured(sample):
    return sum(1 for t in sample if t[1] or t[2] >= p99) / max(1, len(interesting))

print(f"population: {N} traces, {len(interesting)} interesting "
      f"(errors + p99>={p99:.0f}ms)")
print(f"{'strategy':<14} | {'kept':>6} | {'interesting captured':>21}")
print("-" * 50)
print(f"{'head 10%':<14} | {len(head_kept)/N:>5.1%} | {captured(head_kept):>20.1%}")
print(f"{'tail blended':<14} | {len(tail_kept)/N:>5.1%} | {captured(tail_kept):>20.1%}")
head_errs = sum(1 for t in head_kept if t[1])
print(f"  head sampling kept {head_errs} of the {sum(1 for t in traces if t[1])} error traces")
print(f"  tail sampling kept all of them (errors are an always-on rule)")

print()
print("=== propagation: baggage promotion cardinality bomb ===")
SERVICES = {"gateway": ["svcA", "svcB"], "svcA": ["svcC"], "svcB": ["svcC", "svcD"]}
baggage = {"user.id": None, "experiment.bucket": None}
spans = []
def fanout(svc, parent, depth):
    sid = f"{svc}-{depth}-{len(spans)}"
    spans.append((svc, parent, depth))
    for child in SERVICES.get(svc, []):
        fanout(child, sid, depth + 1)
fanout("gateway", None, 0)
promoting = [s for s, _p, _d in spans if s in ("svcA", "svcB")]
print(f"  spans in trace: {len(spans)}")
print(f"  services promoting baggage user.id into attributes: {promoting}")
print(f"  distinct user.id values/day = 2,000,000 -> attribute cardinality")
print(f"  added = {len(promoting)} services x 2,000,000 = "
      f"{len(promoting) * 2_000_000:,} index entries/day")
print("  (the fix: baggage is for propagation, not indexing - drop at the")
print("   collector or promote into logs/metrics with allowlists)")
```

```text
population: 20000 traces, 311 interesting (errors + p99>=154ms)
strategy       |   kept |  interesting captured
--------------------------------------------------
head 10%       | 10.2% |                11.9%
tail blended   |  6.7% |               100.0%
  head sampling kept 13 of the 113 error traces
  tail sampling kept all of them (errors are an always-on rule)

=== propagation: baggage promotion cardinality bomb ===
  spans in trace: 6
  services promoting baggage user.id into attributes: ['svcA', 'svcB']
  distinct user.id values/day = 2,000,000 -> attribute cardinality
  added = 2 services x 2,000,000 = 4,000,000 index entries/day
  (the fix: baggage is for propagation, not indexing - drop at the
   collector or promote into logs/metrics with allowlists)
```

## Interview probes

- Why must head-based sampling be parent-based to stay coherent, and
  what breaks when one service samples independently?
- A collector doing tail-sampling needs to hold a 30s trace: derive
  the memory math for 100k traces/sec at 50 spans each, and the sharding
  key that keeps spans of a trace together.
- What exactly does the W3C traceparent version field require of an
  implementation that sees an unknown version?
- Your trace shows a 200ms gap between a client span and a server span
  of the same RPC: name four causes and the signal that distinguishes
  each.

## References

1. Sigelman et al., "Dapper, a Large-Scale Distributed Systems Tracing
   Infrastructure",
   [research.google.com](https://research.google/pubs/pub36356/) - the
   foundational paper: instrumentation layers, sampling design, and
   the trace-tree model.
2. [W3C Trace Context](https://www.w3.org/TR/trace-context/) - the
   traceparent/tracestate formats and the interoperability rules.
3. [OpenTelemetry specification](https://opentelemetry.io/docs/specs/otel/)
   - the SDK semantics: span model, samplers, collector processors.
4. [OpenTelemetry (this repo)](../observability/opentelemetry.md) - the
   SDK/API usage this page's machinery underlies.
