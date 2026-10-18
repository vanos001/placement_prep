# "We have dashboards, so we are observable"

## Overview

Dashboards are the most visible artifact of an operations practice, which
is why "we have dashboards" is so easily mistaken for "we are
observable". But a dashboard is a set of pre-aggregated, pre-chosen
answers to questions someone anticipated when building it. Observability
is the property of a system that lets you ask *new* questions — ones
about a failure mode nobody predicted — and get answers out of production
telemetry without shipping new code. The two overlap on the happy path
and diverge completely at 3 a.m., when the novel failure is happening and
the panels are all green. This page audits the claim, works the
aggregation and cardinality arithmetic that separates metrics dashboards
from explorability, examines dashboard sprawl as its own failure mode,
and gives curated dashboards their honest due. The verdict is
incomplete: dashboards are the most-used part of an observability
practice and a poor proxy for one.

## The Claim, Stated Fairly

The strongest common form is: "We have Grafana set up with panels for
requests, errors, latency, and saturation; ops can see everything that
matters; therefore we are observable." This is not complacency — it
describes infrastructure most teams genuinely built, and for the
failure modes the panels were designed for, it works: the CPU panel
finds the CPU problem, the error-rate panel finds the error-rate
problem. The claim's fairness comes from daily use: dashboards are the
first thing opened in most incidents and they resolve a large share of
them.

Observability, as the term is used in modern operations, means the
ability to explain any state the system can reach from the telemetry it
emits, including states nobody anticipated. The question this page
audits is whether a fixed set of aggregated panels provides that
ability — and if not, what does.

## Verdict

**Incomplete.** Dashboards answer the questions their authors
anticipated, in the aggregation their authors chose, at the granularity
their storage permitted. The claim is true in exactly that regime: known
failure modes, anticipated questions, coarse answers. It fails to
deliver the promised outcome — understanding — whenever the incident's
shape is novel, correlated across dimensions, or hidden by aggregation:
the classic counterexample is a single tenant failing at 100% inside a
fleet that is 99.95% healthy, invisible on every panel that aggregates
by time and totals. That is an incomplete claim by this collection's
taxonomy: real infrastructure, real benefit, missing preconditions that
carry the actual meaning of the word "observable".

## Why People Believe It

The kernel of truth is that dashboards are indispensable and most
incidents are, in fact, anticipated. CPU saturation, error-rate spikes,
latency creep, queue depth growth — these recur, and a panel per signal
catches them. The engineer whose experience supplies the claim has
genuinely used dashboards to diagnose most problems they have faced.
The belief also draws strength from tooling convergence: since
practically every team has some metrics system (Prometheus plus Grafana
is the default stack of the era), "we have dashboards" is almost
universally true, which makes it feel almost universally sufficient.

The compression happens where the panels come from. A dashboard panel is
a *query someone wrote in advance* over *pre-aggregated time series*.
Both qualifiers are load-bearing. Pre-aggregation means the per-request
detail was discarded at write time — a 5-minute sum or a histogram
bucket cannot be re-derived into per-customer, per-request truth later.
Pre-written queries mean the questions answerable are exactly the ones
frozen on the canvas. The output is a system that is extremely good at
the anticipated and structurally silent about the novel — which is the
precise opposite of the observability property the claim borrows.

The third reason is that dashboards are visible and observability is
not. Nobody can point at "the ability to ask new questions" in a demo;
everyone can point at forty panels. The visible artifact absorbs the
credit for the invisible capability, and budget conversations then fund
more panels rather than the event-level telemetry that would actually
change what is askable.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "We have dashboards" | True — a fixed set of pre-aggregated, pre-chosen queries |
| "So we are observable" | Observability = ability to interrogate production with *new* questions at incident time; dashboards freeze the questions in advance |
| "Metrics cover it" | Pre-aggregated series are lossy and cardinality-capped; they cannot re-derive per-entity truth after the fact |
| "More panels = more coverage" | Panel sprawl dilutes signal; the operational cost of finding the *right* panel grows with panel count |
| "High cardinality is a nice-to-have" | The tenant-segment example below is only findable with per-entity event data or trace-level telemetry |
| "Dashboards are useless then" | False — curated panels are the shared vocabulary of on-call and the fastest path for anticipated failures |

The corrected sentence: "Our dashboards answer the failure modes we have
anticipated; our observability is our ability to ask production
arbitrary new questions about any request, entity, or dimension at
incident time, from high-cardinality events and traces without shipping
code." The first half is the dashboard claim, honestly scoped; the
second half is the capability the word promises.

The arithmetic makes the distinction concrete. A fleet serving 10,000
requests per second emits 10,000 events per second with full per-request
labels — customer, endpoint, region, version, shard. A metrics pipeline
pre-aggregating by (service, endpoint, code) over 5-minute windows
produces a fixed handful of series; the per-customer dimension is gone
before storage. Cardinality math closes the loop: 10 services × 20
endpoints × 5 regions × 3 versions × 500 customers yields 1.5 million
series per metric — far past what a metrics store keeps healthy, which
is why metrics systems force aggregation and why the aggregation is the
loss. Traces and structured events invert the storage model: store the
event, index the dimensions you will want, aggregate only at query time.

## Where It Breaks

**The invisible failing tenant.** An alert fires at a 0.1% error rate;
the fleet-wide error panel reads 0.05% — green. One customer, 0.05% of
traffic, is failing at 100% of requests and has been for forty minutes.
Every time-aggregated panel is green because 0.05% rounds the fleet's
story down to "healthy"; the customer's story is "down". Answering
"error rate *by tenant*" requires the per-tenant dimension to have
survived ingestion — exactly what pre-aggregated metrics discarded. This
is the canonical novel question: not anticipated at panel-writing time,
trivially answerable from event-level data with a filter, unanswerable
from the dashboards by construction.

**The 3 a.m. question with no panel.** An incident shows elevated
latency on one service and a rise in retried requests on another, two
hops away. The panels show each signal separately; the question is
whether requests that hit shard 7 of the cache tier are over-represented
among the slow ones. No panel answers arbitrary joins of dimensions.
The observable team answers it in minutes by querying trace data —
"select requests where cache.shard = 7 and duration > p99" — while the
dashboard-only team ships a temporary metric (deploying code mid-
incident) or gives up and guesses. The gap between those outcomes is
the actual content of the word "observability".

**Dashboard sprawl.** The same dynamic runs in slow motion: each
incident spawns a panel; five years later the org has 300 dashboards
and 6,000 panels; on-call folklore ("check board #14, third row")
substitutes for search; nobody knows which panels are still wired to
reality. Sprawl is not just waste — it *is* the claim failing: the
team that measured its practice in panels built an encyclopedia where
it needed a query language. The Google SRE guidance in the references
pushes the opposite direction: a small curated set, alerting on
symptoms, with the exploration burden moved to the telemetry rather
than the canvas.

**The aggregation that edits history.** Pre-aggregation does not only
lose dimensions; it loses time resolution too. A 5-minute `sum(rate())`
window turns a ten-minute total outage of a low-traffic endpoint into a
slightly lower line on a slightly flatter panel, and histogram buckets
of [10, 50, 100, 500] milliseconds cannot answer whether p99 moved from
90 to 110 ms — both land in the same bucket. The team that later asks
"did the deploy at 14:20 make anything slower?" is asking the recording
rule to remember what it was never told to keep. Every aggregation is a
prediction about future questions, made under pressure at write time;
observability is what happens when that prediction turns out wrong and
the raw events are still there to interrogate.

**When it accidentally works.** For a homogeneous fleet with stable
endpoints, a well-curated golden-signal set — latency, traffic, errors,
saturation — plus alerts on user-facing symptoms genuinely covers daily
operations, and the claim is true in that regime. It stops being true
at the boundaries: multi-tenant products, heterogeneous fleets,
migration periods, and novel failure modes — which is to say, the
incidents that actually wake people up. Curated dashboards remain the
fast path for the anticipated; they are the *floor* of an observability
practice, not the definition of one.

## Practical Implications

- Ask the test question in reviews: "if tenant X reported failures right
  now, how would we see it?" If the honest answer is "grep logs by
  hand", the telemetry model, not the dashboard, is the gap.
- Keep dashboards curated and small; treat panel creation like code
  review, retire stale panels, and record the questions each panel
  exists to answer.
- Invest in high-cardinality event and trace telemetry so aggregation
  happens at query time; accept the storage cost consciously, since
  that cost is what buys arbitrary questions.
- Instrument the dimensions you will need at 3 a.m. — tenant, shard,
  version, region — because dimensions discarded at ingestion cannot be
  recovered at query time.
- Alert on symptoms users feel (error rate, latency against SLOs) and
  let dashboards serve causes; the two-layer split keeps panels useful
  and pages actionable.

## Interview Questions

### What is the difference between monitoring and observability?

Monitoring asks pre-defined questions of pre-aggregated telemetry —
is it up, is the error rate over threshold — and dashboards are its
canvas. Observability is the ability to ask new questions at incident
time and get answers from the telemetry already emitted, without
deploying code. A strong answer notes both are needed: monitoring
catches the anticipated and pages a human; observability explains the
novel.

### A single tenant fails at 100% while fleet-wide error rate stays at 0.05%. Why do dashboards miss it, and what catches it?

Aggregation: the tenant's errors are averaged into a fleet-wide rate
that rounds to healthy, and the per-tenant dimension was discarded when
the metrics were pre-aggregated — the panel cannot answer a question its
input data no longer contains. Per-entity event or trace telemetry
catches it: filter events by tenant, compute the rate at query time.
The design lesson is that cardinality decisions at ingestion determine
what is askable at incident time.

### Your team has 300 dashboards. Diagnose and fix.

The sprawl signals that panel-writing replaced question-answering:
incidents each spawned a panel, nothing was retired, and finding the
right panel now depends on folklore. Fix by treating dashboards as a
curated product: inventory and prune, require a stated question per
panel, move exploratory investigation to queryable event/trace data,
and alert on user-facing symptoms so on-call does not panel-surf during
pages.

### Is high-cardinality labeling just a storage problem?

It is a storage-and-semantics problem. Storing every event with full
dimensions costs more than pre-aggregation, and unbounded label values
(customer IDs, URLs) can blow up a metrics store. But the semantics are
the point: dimensions kept at ingestion determine the questions
answerable later. Mature designs split the streams — bounded-cardinality
metrics for cheap aggregation, event/trace stores for the long tail —
instead of forcing one storage model to serve both.

### When is "we have dashboards" an adequate answer?

For anticipated failure modes on a homogeneous fleet: golden-signal
panels, symptom-based alerts, and a stable query vocabulary resolve
most routine incidents. The answer becomes inadequate the moment the
question is novel, the dimension is per-entity, or the correlation
spans services — which is exactly when observability, not monitoring,
decides the incident's duration.

## Key Takeaways

- A dashboard is a frozen answer; observability is the ability to ask
  unfrozen questions of production telemetry.
- Pre-aggregation is the mechanism of loss: dimensions discarded at
  write time cannot be queried at incident time.
- The canonical blind spot is the fully-failing entity hidden under a
  healthy aggregate — findable only with high-cardinality events or
  traces.
- Sprawl is the slow-motion form of the misconception: panels are not
  a query language, and volume of panels does not convert into
  capability.
- Keep both layers honestly scoped: curated dashboards for the
  anticipated, event-level telemetry for the novel — and fund the
  second, because it is the one the word "observable" promises.

## Cross-References

- [Connection Atlas: Observability Pipeline](../connection-atlas/observability-pipeline.md)
  — how signals flow from emit to storage to query, and where the loss
  happens
- [Misconceptions: averages-summarize-latency](./averages-summarize-latency.md)
  — the statistical sibling: aggregation hiding the distribution, one
  layer down
- [Misconceptions: high-throughput-means-low-latency](./high-throughput-means-low-latency.md)
  — the throughput panel that stays green through a saturation collapse
  is this page's failure in rate form
- [Cloud Observability: Monitoring](../../cloud/observability/monitoring.md)
  — the monitoring layer's own design space
- [Cloud Observability: Tracing](../../cloud/observability/tracing.md)
  — the high-cardinality signal that answers cross-service questions
- [Linux Observability: Metrics](../../linux/observability/metrics.md)
  — the metrics substrate most dashboards sit on
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- OpenTelemetry. *Observability Primer* — the monitoring-versus-
  observability distinction as the industry now uses it.
  <https://opentelemetry.io/docs/concepts/observability-primer/>
- B. Beyer et al. *Site Reliability Engineering*, Chapter 6, *Monitoring
  Distributed Systems* — the case for symptom-based alerting and small
  curated dashboards. <https://sre.google/sre-book/monitoring-distributed-systems/>
- B. Beyer et al. *The SRE Workbook*, Chapter 5, *Alerting on SLOs* —
  symptom alerts and error budgets as the layer above dashboards.
  <https://sre.google/workbook/alerting-on-slos/>
- C. Majors, L. Fong-Jones, G. Miranda. *Observability Engineering*,
  O'Reilly, 2022 — high-cardinality events as the substrate of
  explorability, cited by title.
