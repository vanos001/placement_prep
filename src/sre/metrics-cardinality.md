# Metrics Cardinality Explosions

A metrics system looks infinitely scalable until one label goes wrong. Unlike logs, where cost grows linearly with traffic, time-series databases cost grows *multiplicatively* with label values, and the explosion is silent: one new label with 50,000 values on an innocent-looking counter can multiply your series count by 50,000 and take down the monitoring stack on the day you need it most - usually during the incident that label was meant to debug.

## The Multiplication Rule

In the Prometheus model (shared by Mimir, Cortex, Thanos, VictoriaMetrics, Datadog with different terminology), a unique time series is identified by the metric name plus every label name-value pair:

```
series = product over labels of (number of distinct values of that label)
```

This is the whole disaster in one line. Consider the most common HTTP metric in the world, `http_requests_total`, labeled on a 10-pod deployment:

```python
# Time-series cardinality: series = product of label cardinalities.
import math

base = {"pod": 10, "route": 5, "method": 3, "code": 4}
n = math.prod(base.values())
print("time-series cardinality: series = product of label cardinalities")
print("  http_requests_total{pod,route,method,code}:", n, "series per replica set")
user_card = 50_000
print("  + user_id label (", user_card, "values):", f"{n * user_card:,}", "series")
# 90-day retention cost at ~1.5 KB per active series per day (chunks + index,
# illustrative order of magnitude; measure on your own TSDB before trusting).
per_series_bytes_day = 1500
total = n * user_card
gib = total * per_series_bytes_day * 90 / 1024**3
print(f"  ~{per_series_bytes_day} B/day/series * 90 d = {gib:,.0f} GiB just for this metric")
# The fix: bucketize low-value labels and drop the high-cardinality one.
reduced = base["pod"] * base["route"] * 3 * 2   # code -> {2xx,5xx}, method -> {GET,OTHER}
print("  after bucketizing code/method and dropping user_id:", reduced, "series",
      f"({n * user_card / reduced:,.0f}x reduction)")
series_budget = 4_000_000
over = (n * user_card) / series_budget
print(f"  a {series_budget:,}-series in-memory budget is exceeded {over:.1f}x by ONE such metric")
```

Output:

```text
time-series cardinality: series = product of label cardinalities
  http_requests_total{pod,route,method,code}: 600 series per replica set
  + user_id label ( 50000 values): 30,000,000 series
  ~1500 B/day/series * 90 d = 3,772 GiB just for this metric
  after bucketizing code/method and dropping user_id: 300 series (100,000x reduction)
  a 4,000,000-series in-memory budget is exceeded 7.5x by ONE such metric
```

Read the failure mode carefully: 600 series is a healthy, queryable metric. Adding `user_id` - the label someone asks for in every postmortem review - produces 30 million series from *one* metric on *one* deployment. Prometheus keeps active series in heap for head-block queries; the practical ceiling for a single Prometheus is a few million series, so this one metric alone exceeds the budget several times over, and it does so gradually - each new user is one more series - until an OOM kill at 3 a.m.

## Why It Hurts So Much Per Series

The cost is not just storage. Four distinct resources degrade with active-series count:

1. **Ingest CPU and heap.** Every sample must be hashed (label set -> fingerprint), matched against the head block, and appended. Prometheus ingestion cost is roughly linear in active series for a fixed scrape rate, and heap pressure grows until either memory or GC pauses bite.
2. **Index memory.** The inverted index from label value -> series grows with distinct label values; `user_id` puts 50,000 postings lists where `code` had 4.
3. **Query latency.** Range queries fan out over matching series; a `sum(rate(...))` over 30 million series cannot be answered interactively no matter how the TSDB is tuned. Cardinality is the primary reason "dashboards got slow" in most organizations.
4. **Compaction and retention pressure.** More series means more chunks per block, larger indexes in object storage, and slower compaction - the degradation continues long after the samples themselves are compressed.

The nasty part is the *interaction with scraping*: series that stop receiving samples eventually age out of the head block, but at any moment the set of active series is what counts, and per-user labels guarantee the active set is as large as your traffic.

## Control Strategies, From Cheapest to Most Drastic

**Bucketize low-value labels.** `code="418"` rarely deserves its own series; map status codes to classes (`2xx/4xx/5xx`) either at instrumentation time or with metric relabeling at scrape time. The simulation above shows a 100,000x reduction from bucketizing two labels and dropping one - with negligible loss of debuggability, because the rare-code detail belongs in logs or traces, where per-event identity is free.

**Drop or bound cardinality at the boundary.** Prometheus `metric_relabel_configs` can drop a label or cap its values *before* ingestion (write-side relabeling in Remote Write; `keep_dropped` limits in scrape configs). Modern long-term stores enforce limits server-side: Mimir and Cortex expose per-tenant `max_series`, `max_label_names`, and per-label-value limits that reject the explosion instead of OOMing the cluster. Datadog's custom-metrics billing does the enforcement with an invoice, which is slower but eventually just as effective.

**Move identity out of metrics entirely.** The 2020s answer to "which users saw 500s?" is exemplars and traces, not labels: store per-request identity in the trace system (high cardinality is its job) and attach exemplar trace IDs to bucket-level metric series. This division of labor - metrics for aggregates, traces for identity - is the single most useful architectural decision a platform team can make on observability.

**Analyze before you ship.** The cardinality of a metric is measurable *before* it ships: `promtool check metrics` lints label design, and tools like Grafana Mimir's `mimirtool analyze` compute the active-series delta of a proposed dashboard/rules package against live traffic. The production-grade practice is a CI check that fails a release when a new metric's projected cardinality exceeds a budget - the same shift-left move performance teams made with load tests.

## The Debugging Playbook When It Already Blew Up

When Prometheus is OOMing or a tenant is rejected for `max_series`, find the top series contributors first: the TSDB status page (`/api/v1/status/tsdb`) lists the label-value pairs contributing the most series, and `count(count by (job)({__name__=~".+"}))` per job ranks offenders. The emergency remediation ladder, in order of blast radius: drop the offending label via scrape-time relabeling (instant, no app change), reduce scrape frequency for the noisy job (halves sample rate, does *not* reduce series count - a common misconception), shorten retention (frees storage, not heap), and finally shard the tenant across Prometheus replicas with functional partitioning (`--enable-feature=extra-scrape-metrics` style split by job).

The one-line summary for interviews: time-series cardinality multiplies across labels, so every label is a bet that its value set stays small; enforce that bet with bucketing and limits at the boundary, and route per-entity identity to systems designed for it.

## Hidden Multipliers People Miss

Two sources of cardinality hide inside "normal" instrumentation and deserve their own warnings.

**Histogram buckets multiply silently.** A Prometheus histogram is not one series - it is a family: one cumulative counter per bucket plus `_sum` and `_count`. A request-latency histogram with 14 `le` buckets and 2 extra labels (route, method) produces 14 x 5 x 3 = 210 series *per pod*, x10 pods = 2,100 series, before any status-code label. Native-histogram formats (Prometheus 2.40+, OTel exponential histograms) change the economics: one series holds a whole configurable bucket layout, at the cost of query-tool compatibility - which is why teams with severe histogram cardinality adopt them selectively.

**Error strings and IDs leak into labels.** The classic incident sequence: someone adds `error="..."` for debugging; the first deploys produce 8 error classes; then a bug produces a unique message containing a URL or a user ID per request, and the series count follows the distinct-message count. The rule that survives audits: any label whose value set is "whatever the code prints" is unbounded, and unbounded label values must be rejected at the instrumentation boundary (SDKs like OTel let you register view processors to drop or hash them; Prometheus client libraries let you pre-validate in wrappers).

**A concrete blown-up production sequence**, reconstructed from the shape every ops team eventually meets:

```
day 1  error label added for debugging          +12 series
day 9  a client sends malformed URLs; message
       includes the URL                         +40,000 series/day
day 10 Prometheus heap climbs; GC pauses grow;
       scrapes start timing out (target down)
day 11 dashboards break - during the incident the
       error label was added to debug
```

The scrapes timing out is the vicious part: a metrics system failing *because of* a debugging label makes every other team's dashboards collateral damage. This is the operational argument for server-side per-tenant limits - the blast radius of one team's label must be one team's rejected metric, not a shared OOM.

## Enforcing the Budget Like an SLO

Treat cardinality as a budget with three enforcement layers, mirroring how you treat latency or quota:

1. **Admission control at the collector.** OTel Collector processors (`filter`, `transform`) and Prometheus relabeling drop or rewrite offending labels before storage. This is where bucketization (`code="503"` -> `code_class="5xx"`) belongs.
2. **Hard limits at storage.** Mimir/Cortex per-tenant `max_global_series_per_user`, `max_label_value_length`, and Cardinality Management API (since Mimir 2.x) that reports top contributors per tenant. Enforcement must be *reject with a signal to the offender* (Remote Write 429 + which limit), never silent drop.
3. **Cost allocation in commercial stacks.** Datadog bills custom metrics per distinct series; that converts cardinality directly into dollars and moves the enforcement conversation to finance. Works, but slowly - by the time the invoice arrives, the multipler has shipped to production.

The cultural fix that makes the technical ones stick: a CI gate. `mimirtool analyze prometheus` diffs a proposed dashboard/rules bundle against a running system's active series; wiring that into the release pipeline means the person adding the label sees "this change adds 1.2M series" in their pull request - not the on-call at midnight.

## Metrics vs Logs vs Traces: Who Owns Identity

The cardinality explosion is ultimately a misrouting problem: per-entity facts (which user, which request) were pushed into a system designed for aggregates. The mature observability architecture assigns each signal the cardinality it can afford:

| Signal | Cardinality budget | Right home for per-user detail |
|---|---|---|
| Metrics | thousands of series per metric | no - aggregates only, exemplars as bridge |
| Traces | one span set per request (unbounded) | yes - identity is the point |
| Logs | one line per event (unbounded) | yes, at linear cost |

The exemplar mechanism deserves special mention because it is the *controlled leak* between the layers: a metric series stays bucketed, but select high-latency or error samples carry a `trace_id` reference, so a dashboard spike can be clicked through to individual culprits without the metric ever knowing what a user ID is. That design - aggregate in the metric, identity one hop away in the trace - is the answer to give in system-design interviews when asked "how would you debug a p99 regression for a single tenant?".

## References

- Prometheus documentation, "Exemplars" and storage overview (head block / active series model): <https://prometheus.io/docs/prometheus/latest/storage/>
- Grafana Mimir documentation, "Limitations" (per-tenant series and label limits): <https://grafana.com/docs/mimir/latest/configure/configure-about/limits/>
- Robust Perception (Brian Brazil's blog), canonical posts on cardinality, e.g. "Cardinality is key": <https://www.robustperception.io/cardinality-is-key/>
- Grafana Mimir `mimirtool` (analyze dashboards/rules for cardinality impact): <https://grafana.com/docs/mimir/latest/operators-guide/tools/mimirtool/>
- Prometheus `metric_relabel_configs` reference (drop/bucket at scrape boundary): <https://prometheus.io/docs/prometheus/latest/configuration/configuration/#metric_relabel_configs>
