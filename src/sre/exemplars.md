# Exemplars: Bridging Metrics and Traces

A dashboard tells you the p99 latency is 812 ms. A tracing backend can show you the full life of one request. Neither answers the question an SRE actually asks at 3 a.m.: *which* request was that, and what did it touch? An **exemplar** is the answer - a single observed sample (usually a histogram bucket observation) that carries a reference to the distributed trace it came from, so the jump from "the aggregate is bad" to "this exact request failed here" is one click, not one investigation.

Introduced by OpenMetrics, adopted by Prometheus 2.26+ behind a feature flag, and standardized as Stable in the OpenTelemetry metrics data model, exemplars are a side-channel rather than a fourth signal: metrics stay aggregated, traces keep per-request identity, and exemplars are the controlled leak between the two.

> Related: [Metrics Cardinality Explosions](./metrics-cardinality.md), [OpenTelemetry](../backend/observability/opentelemetry.md), [Observability Engineering](../production-engineering/advanced/observability-advanced.md).

## The One-Hop Navigation Gap

Without exemplars, going from a metric spike to a trace is a manual correlation exercise: note the timestamp, guess the service, construct a trace query, hope. With exemplars the path is mechanical:

```text
histogram bucket series on a dashboard (p99 or a latency bucket)
        |  click the dot the UI draws on the graph
        v
exemplar on that sample: {trace_id="9f2b1c0a4d5e6f708192a3b4"} 812.0 1755000000.0
        |  trace_id is routed to the tracing backend
        v
the exact trace: every span, tags, the downstream call that was slow
```

The aggregate series never learns what a user is. Identity lives one hop away, in the trace backend, reachable only through the exemplar. Prometheus serves exemplar reads through `/api/v1/query_exemplars`; Grafana draws them as dots on panel graphs linked to a tracing data source.

## What an Exemplar Actually Is

The OpenMetrics specification defines exemplars as "references to data outside of the MetricSet. A common use case are IDs of program traces." An exemplar MUST consist of a LabelSet and a value, and MAY carry a timestamp; the label names and values combined MUST NOT exceed 128 UTF-8 code points. In the text exposition format an exemplar trails the sample line it belongs to:

```text
foo_bucket{le="1"} 11 # {trace_id="KOO5S4vxi0o"} 0.67
foo_bucket{le="10"} 17 # {trace_id="oHg5SJYRHA0"} 9.8 1520879607.789
```

(the sample above is the specification's own example). The OpenTelemetry metrics data model, where exemplars are marked Stable, defines one as "a recorded value that associates OpenTelemetry context to a metric event within a Metric", consisting of an optional `trace_id`/`span_id`, the observation time, the recorded value, and a set of filtered attributes. Both explicit-bucket histogram data points and sums carry an optional set of exemplars.

Where does the exemplar attach for a histogram? To the **bucket series the value landed in** - including the `+Inf` bucket - not to the histogram as a whole. The Go client keeps one exemplar slot per bucket series, and `ObserveWithExemplar(v, labels)` overwrites it unconditionally on every call: last write wins. The Java client's `ExemplarSampler` is more deliberate: it replaces a resident exemplar only after a minimum hold (default 7 s), discards residents after 70 s, and throttles checks to ~90 ms - all defaults from `ExemplarSamplerConfig`.

## Client-Side Selection Policies

The exemplar you see at scrape time is whichever trace the *client library* decided to advertise. Policies differ, and so does their bias:

| Policy | Where you meet it | Behavior | Visible bias |
|---|---|---|---|
| Last write wins | Go classic histograms (`client_golang`) | one atomic slot per bucket series, overwritten per observe | exemplar is the end of the window, not the worst case |
| Rate-limited replacement | Java client (`client_java`) ExemplarSampler | candidate replaces resident only after ~7 s hold; ~70 s max age | damps churn; slot still ages toward "now" |
| Small pool + TTL | Go native histograms | default max 10 exemplars, 5 min TTL, evicts the older of the two temporally closest exemplars | pool spreads over recent minutes |
| Max-in-bucket | folk model, not a real default | keep the slowest observation seen | over-advertises storms; see the run below |

A fourth constraint hides in the Go source: `ObserveWithExemplar` on a native histogram "should not be called in a high-frequency setting" - the native path is not lock-free, so per-request exemplar attachment has a real hot-path cost, unlike plain `Observe`.

## Model Run: Selection Bias, Measured

**MODEL** - a deterministic simulator, not real telemetry. One 2000-request scrape window with a mid-window retry storm; three selection policies race for the exemplar slots (one per bucket for LAST/SLOWEST, a 5-slot reservoir for UNIFORM):

```python
# MODEL: exemplar-selection simulator, not real telemetry. A deterministic toy
# request stream is scraped once; three client-side selection policies race.
N = 2000                              # requests inside one scrape window
BUCKETS = [50, 100, 200, 400, 800]    # ms bucket upper bounds, plus +Inf
STORM = (900, 1149)                   # retry-storm burst: 12.5% of the window
K = 5                                 # reservoir slots per bucket (UNIFORM)

_seed = 0xC0FFEE
def lcg():
    global _seed
    _seed = (6364136223846793005 * _seed + 1442695040888963407) % (1 << 64)
    return _seed / float(1 << 64)

def trace_id():
    return "%010x" % int(lcg() * (1 << 40))

def bucket_of(v):
    for b in BUCKETS:
        if v <= b:
            return b
    return None                       # the +Inf bucket

reqs = []
for i in range(N):
    ms = 8.0 + 520.0 * lcg() ** 3                 # skewed low, most under 150 ms
    if STORM[0] <= i <= STORM[1]:
        ms += 300.0 + 560.0 * lcg()               # burst: 308..1378 ms
    reqs.append((ms, trace_id()))

def picks_for(strategy):
    out = []
    for b in BUCKETS + [None]:
        obs = [(i, v, t) for i, (v, t) in enumerate(reqs) if bucket_of(v) == b]
        if not obs:
            continue
        if strategy == "LAST":                    # Go classic: slot overwritten every observe
            out.append(obs[-1])
        elif strategy == "SLOWEST":               # max-in-bucket across the window
            out.append(max(obs, key=lambda o: o[1]))
        else:                                     # UNIFORM: V2 reservoir, K slots per bucket
            keep = obs[:K]
            for j, o in enumerate(obs[K:], K):
                r = int(lcg() * (j + 1))
                if r < K:
                    keep[r] = o
            out.append(keep)
    return out

sel = {s: picks_for(s) for s in ("LAST", "SLOWEST", "UNIFORM")}
mean_all = sum(v for v, _ in reqs) / N
print("MODEL - exemplar selection over one %d-request scrape window" % N)
print("buckets(ms): %s +Inf | burst: requests %d-%d (%.1f%% of window)" %
      ("/".join(map(str, BUCKETS)), STORM[0], STORM[1], 100 * (STORM[1] - STORM[0] + 1) / N))
print("population mean latency: %.0f ms" % mean_all)
print()
print("bucket   obs | LAST val tfrac trace | SLOWEST val tfrac trace | UNIFORM val tfrac trace")
for bi, b in enumerate(BUCKETS + [None]):
    name = "<=%d" % b if b else "inf"
    obs = sum(1 for v, _ in reqs if bucket_of(v) == b)
    last, slow, uni = sel["LAST"][bi], sel["SLOWEST"][bi], sel["UNIFORM"][bi]
    u_show = min(uni, key=lambda o: abs(o[0] / (N - 1) - sum(x[0] for x in uni) / (len(uni) * (N - 1))))
    cell = lambda e: "%4.0f %5.2f %s" % (e[1], e[0] / (N - 1), e[2])
    print("%-7s %4d | %18s | %18s | %18s" % (name, obs, cell(last), cell(slow), cell(u_show)))
print("(UNIFORM column shows the median-tfrac member of a 5-slot reservoir)")
print()
print("bias over all retained exemplars vs the full population:")
print("strategy     n  mean_ms  storm_share  mean_tfrac")
print("%-10s %4d %8.0f %12.3f %10.3f" % ("population", N, mean_all,
      (STORM[1] - STORM[0] + 1) / N, 0.5))
for s in ("LAST", "SLOWEST", "UNIFORM"):
    flat = [p for grp in sel[s] for p in (grp if isinstance(grp, list) else [grp])]
    n = len(flat)
    mv = sum(p[1] for p in flat) / n
    ss = sum(1 for p in flat if STORM[0] <= p[0] <= STORM[1]) / n
    mt = sum(p[0] for p in flat) / n / (N - 1)
    print("%-10s %4d %8.0f %12.3f %10.3f" % (s, n, mv, ss, mt))
```

Output (verbatim from a run; `tfrac` = the chosen request's position in the window):

```text
MODEL - exemplar selection over one 2000-request scrape window
buckets(ms): 50/100/200/400/800 +Inf | burst: requests 900-1149 (12.5% of window)
population mean latency: 213 ms

bucket   obs | LAST val tfrac trace | SLOWEST val tfrac trace | UNIFORM val tfrac trace
<=50     740 |    8  1.00 2d4bdd6bd5 |   50  0.70 c1b8e37d36 |   10  0.34 7b0050e1a8
<=100    235 |   90  1.00 b9ee7a455a |  100  0.45 c1e78f4a47 |   66  0.76 c5f3c18518
<=200    293 |  162  1.00 1af3d797cf |  200  0.09 d21c806c9f |  121  0.38 d7bdf35c6a
<=400    335 |  234  1.00 8dfeab52e6 |  400  0.37 f5fe435c75 |  210  0.25 666db7082d
<=800    302 |  493  0.99 acb2feb4ca |  800  0.45 59a98216b7 |  456  0.53 0e88ce819e
inf       95 |  850  0.57 072b753844 | 1352  0.49 96841fde4a |  800  0.52 3cfc428031
(UNIFORM column shows the median-tfrac member of a 5-slot reservoir)

bias over all retained exemplars vs the full population:
strategy     n  mean_ms  storm_share  mean_tfrac
population 2000      213        0.125      0.500
LAST          6      306        0.167      0.925
SLOWEST       6      483        0.333      0.425
UNIFORM      30      312        0.233      0.502
```

- **LAST is temporally biased.** Five of six exemplars sit at `tfrac` 0.99-1.00 (mean 0.925): you see whatever hit the bucket *most recently*. The mid-window storm survives only in the `+Inf` bucket, because nothing slower arrived after it. If the incident ended 30 s before the scrape, the exemplar shows the recovery, not the fire.
- **SLOWEST is value-biased.** Mean 483 ms vs a population mean of 213 ms; the storm is over-represented 2.7x (0.333 vs 0.125). Great for debugging, misleading as a picture of typical traffic - it advertises the storm even when p99 barely moved.
- **Even the unbiased reservoir is not population-representative.** UNIFORM's mean `tfrac` is 0.502, but its mean latency is 312 ms, not 213: every bucket gets 5 slots, so the 95-request `+Inf` bucket contributes 5 of 30 exemplars while carrying 4.75% of traffic. Exemplar sets are bucket-stratified; reading them as population statistics is a mistake.

## Storage Cost and the Cardinality Question

Exemplars create **no new series** - they ride on bucket series that already exist - so the series-count math in [Metrics Cardinality Explosions](./metrics-cardinality.md) is untouched. The costs are elsewhere:

- **Memory, bounded and known.** Prometheus stores exemplars in a fixed-size in-memory circular buffer shared by all series; the documentation budgets roughly 100 bytes per `trace_id`-only exemplar, so the default cap (`storage.exemplars.max_exemplars`, default 100000) is on the order of 10 MB. Exemplars are also appended to the WAL, but only for the WAL's own retention window.
- **Silent eviction.** A full buffer drops its oldest exemplars - no error reaches you. Distributed layers add their own drops: Grafana Mimir's configuration reference exposes a per-request cap on exemplars per series ("the exceeding exemplars are dropped") and a per-tenant limit (`max_global_exemplars_per_user`); flags and defaults shift between releases, so check the live page.
- **Write contract.** Remote Write 2.0 folds exemplars into its write semantics: a receiver MUST NOT return 2xx if exemplars it should have written were not - drops at least surface at the protocol boundary.

## Exemplars vs Span Metrics

The other way to make traces answer aggregate questions is **span metrics**: a pipeline (Grafana Tempo's metrics-generator is the reference example) consumes ingested spans and emits conventional counters/histograms per span name. They solve different problems:

| Dimension | Exemplars | Span metrics |
|---|---|---|
| New series created | none - rides on existing bucket series | one series per span-name x dimension set |
| Cardinality leak risk | none from series; only exemplar-label abuse | real - span names carrying IDs are the classic leak |
| Coverage | a handful of traces per bucket series per scrape | every ingested span, fully aggregated |
| Identity | direct `trace_id`, one click | none - you still query traces by filter afterwards |
| Extra infrastructure | client library only | a second metrics pipeline fed from the trace stream |

They compose rather than compete: span metrics aggregate over traffic your head sampler discarded; exemplars give the dashboard a door into the trace store you already have. If you can afford only one, exemplars are cheaper - and the faster interview answer to "how do you debug a p99 regression for a single tenant?"

## Pitfalls Checklist

1. **"The" exemplar is a client-side choice.** LAST/SLOWEST/reservoir policies see different requests in the same window (run above). Know what your client library does before promising "the exemplar shows the culprit."
2. **Sampling mismatch dead links.** With head sampling, the client may attach a `trace_id` the sampler then discards - the exemplar points at a trace that does not exist. Tail sampling inverts it: only slow/error traces are kept, so fast-request exemplars die. Check whether your SDK gates attachment on the sampling decision.
3. **Retention mismatch.** Exemplar slots live seconds-to-minutes, but long-term stores may serve an old exemplar whose trace was GC'd from the tracing backend days earlier. A dead dot is a normal dot - build the UI for it.
4. **PII and junk in exemplar labels.** The `trace_id` itself is an opaque 16-byte value (32 hex chars per the W3C trace-context spec), but the exemplar LabelSet is arbitrary user data. Putting user IDs or emails there ships identity into the metrics path, which typically has weaker access control than traces and no "delete this user" story. Keep `trace_id` and `span_id`; nothing else without a strong reason.
5. **Silent drops.** Buffer eviction and relay-side per-request caps both discard exemplars without client-visible errors. An empty dashboard dot can mean "no exemplar chosen", not "nothing was slow."
6. **`+Inf` magnetism.** The worst requests all land in the last bucket, whose slot flips constantly during an incident. The dot at p99 tells you *someone* had a bad time; only the count series tells you how many.

## Interview Drill

- **"p99 latency alert fires. Walk me from the dashboard to root cause."** Burn-rate alert confirms budget burn; open the latency histogram; click an exemplar dot on the offending bucket; the `trace_id` opens the full trace; read the waterfall for the slow span. Follow-up: what if the trace 404s? (unsampled, evicted, or expired - pitfalls 2 and 3).
- **"Do exemplars increase cardinality?"** No new series - that is the point. The cost is a bounded exemplar buffer (~100 bytes/slot, default 100000 slots in Prometheus), plus whatever abuse your team commits in exemplar labels. Compare with putting `trace_id` on the sample itself, which destroys aggregation and makes every request a series.

## References

1. OpenMetrics specification, "Exemplars" (MUST/MAY rules, 128-code-point cap, text-format sample): <https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md>
2. Prometheus documentation, "Feature Flags" (`exemplar-storage`: circular buffer, ~100 bytes/exemplar, WAL): <https://prometheus.io/docs/prometheus/latest/feature_flags/>
3. Prometheus configuration reference (`storage.exemplars.max_exemplars`, default 100000): <https://prometheus.io/docs/prometheus/latest/configuration/configuration/>
4. OpenTelemetry specification, Metrics Data Model, "Exemplars" (Stable): <https://opentelemetry.io/docs/specs/otel/metrics/data-model/>
5. Grafana documentation, "Introduction to exemplars" (dashboard navigation model): <https://grafana.com/docs/grafana/latest/fundamentals/exemplars/>
6. Grafana Mimir configuration reference (per-request and per-tenant exemplar limits): <https://grafana.com/docs/mimir/latest/references/configuration-parameters/>
7. Grafana Tempo documentation, "Metrics from traces" (span metrics via metrics-generator): <https://grafana.com/docs/tempo/latest/metrics-from-traces/>
8. `prometheus/client_golang`, `prometheus/histogram.go` (`ObserveWithExemplar`, per-bucket slots, native-histogram pool/TTL): <https://github.com/prometheus/client_golang/blob/main/prometheus/histogram.go>
9. `prometheus/client_java`, `ExemplarSamplerConfig` (7 s / 70 s / 90 ms defaults): <https://github.com/prometheus/client_java/blob/main/prometheus-metrics-core/src/main/java/io/prometheus/metrics/core/exemplars/ExemplarSamplerConfig.java>
10. Prometheus Remote Write 2.0 specification (exemplars in the receiver write contract): <https://prometheus.io/docs/specs/prw/remote_write_spec_2_0/>
