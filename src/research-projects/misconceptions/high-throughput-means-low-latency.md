# "The system does 50,000 requests per second, so responses are fast"

## Overview

Throughput is the most-quoted number in system design and the least
informative about what any individual user experiences. The two quantities
are coupled through concurrency and queueing, not through an implication:
a system can sustain enormous request rates while every request waits
seconds in a backlog, and it can serve a tiny rate with lightning latency
while falling over the moment concurrency rises. This page audits the
inference from "high throughput" to "low latency", works Little's Law and
the saturation curve that actually governs the relationship, shows how
batching buys throughput by spending latency, and delineates the claim
from its bandwidth-flavored sibling in this collection. The verdict is
false: the counterexample — a saturated system proudly reporting 50,000
requests per second while user-visible latency climbs unboundedly — is
the normal shape of an overload, not a corner case.

## The Claim, Stated Fairly

The strongest common form is: "Our benchmark measured 50,000 requests per
second with sub-20-millisecond responses; the production fleet will
therefore be fast." This deserves fairness on two counts. The benchmark
number is usually honestly measured, and at low-to-moderate load the
system really does serve requests quickly — the throughput figure was not
fabricated but obtained with a closed-loop client at some fixed
concurrency, and at that concurrency the queueing was negligible.

The claim fails as an inference because throughput and latency answer
different questions. Throughput is a rate the *system* achieves; latency
is a duration a *request* experiences. The bridge between them is
concurrency and queue occupancy, and the bridge has a cliff: as
utilization approaches capacity, waiting time grows nonlinearly and then
without bound, while the throughput number on the dashboard stays
beautifully flat at capacity. The claim reads the flat number as
"handling the load" — which is precisely what a saturated queue looks
like from the outside.

## Verdict

**False.** High measured throughput implies nothing about response time
at the offered load, because latency is governed by queueing: by
Little's Law, average response time equals concurrency divided by
throughput, and as offered load approaches capacity the queue grows and
waiting time dominates. The valid counterexample needs no exotic setup:
offer 60,000 requests per second to a system whose ceiling is 50,000.
Throughput holds at ~50,000 (the dashboard glows), the backlog grows by
10,000 requests per second, and by Little's Law user-visible latency
reaches ten seconds after a minute of overload. The system "processes
50k req/s" and responses are catastrophically slow — the claim's two
halves hold and its conclusion is inverted.

## Why People Believe It

The kernel of truth is that at load levels comfortably below capacity,
throughput and latency move together: a system that handles more requests
per second on better hardware generally serves each one at least as fast,
because the queue is short and utilization is low. Teams observe this in
load tests (add capacity, both numbers improve) and in scaling wins
(remove a bottleneck, both improve), and the positive correlation
crystallizes into an implication.

The second reason is measurement design. Benchmarks are run at fixed
concurrency with a closed-loop client, where the system is not saturated:
50,000 requests per second at 20 milliseconds each implies 1,000 requests
in flight (Little's Law: L = λW = 50,000 × 0.020), a comfortable regime.
The number carried forward is the rate, stripped of the concurrency that
made it possible. Production then applies an open loop — arrivals do not
wait for earlier responses — and at 60,000 arrivals per second nothing
about the benchmark's regime survives, but the 50,000 figure on the
dashboard keeps certifying "fast".

The third reason is aggregation. "The system does 50k req/s" averages
over time and over endpoints; a system doing 45,000 easy requests and
5,000 expensive ones reports one number that describes neither. The
sibling audit of averages in this collection covers the statistical form
of this error; here it is enough to note that a single throughput figure
is the same compression in rate form.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "High throughput → fast responses" | Latency = concurrency ÷ throughput (Little's Law); it is a function of queue occupancy, not of the rate record |
| "50k req/s means it handles the load" | At offered load above capacity, throughput pins at capacity and the queue grows — "handling the load" and "saturated" are the same dashboard reading |
| "Latency degrades gracefully" | Waiting time grows roughly as ρ/(1−ρ) as utilization ρ → 1: at 90% utilization waits are ~9× the service time under simple models, and worse with variance |
| "Batching is a pure win" | Batching raises throughput by amortizing overheads while adding the batch window to every item's latency |
| "The benchmark predicts production" | Closed-loop benchmarks hold concurrency fixed; open-loop arrivals are unbounded — measure latency at the offered load, from the client's clock |

Little's Law is the load-bearing relation: L = λW, average number in the
system equals arrival rate times average time in system. Rearranged,
W = L/λ: if the backlog holds 600,000 requests and arrivals are 60,000
per second, each new arrival's expected wait is ten seconds — no
probabilistic model required, just conservation. Queueing theory adds the
shape: with utilization ρ = λ/μ, waiting time behaves like a constant
times ρ/(1−ρ), so the cliff is steep. A service with 20 ms of work per
request and 45,000 rps offered against a 50,000 rps capacity (ρ = 0.9)
pays roughly 9× the service time in queueing under a simple M/M/1-style
model — 180 ms of waiting on 20 ms of work — and the multiplier explodes
as ρ → 1. Variance makes it worse: Kingman's approximation multiplies by
the sum of arrival- and service-time variability, which is why a fleet
with mixed cache hits and misses, GC pauses, and retries cliffs earlier
than the textbook curve.

Batching is the deliberate inversion of the claim: a database writer that
groups 10 ms of writes into one fsync, a Kafka producer that accumulates
a `linger.ms` window, or an inference server that runs batches of 64 all
raise throughput substantially while adding the window (and the queue for
the batch) to every item's latency. That is frequently the right trade —
but it is a trade, and the throughput number alone cannot express it.

## Where It Breaks

**The overload dashboard.** Capacity is 50,000 rps; a marketing campaign
delivers 60,000. Throughput holds at ~50,000, CPU sits at 100%, and the
"requests per second" graph is flat and green. The queue, however, grows
by 10,000 requests per second; after 60 seconds it holds 600,000
requests; Little's Law puts the expected wait for a new arrival at ten
seconds; time-outs start firing at 30 seconds, clients retry, and
effective offered load rises further. Every number the dashboard was
built to show says "operating normally at scale" while the user-visible
service has failed. This is the claim's counterexample in its purest
form: throughput high, latency unbounded, conclusion inverted.

**The utilization cliff, with numbers.** Take the same 50,000 rps
capacity and walk the offered load up. At 25,000 rps (ρ = 0.5) the
simple-model multiplier is 1× — waits are comparable to service time, and
the benchmark's 20 ms experience roughly holds. At 37,500 rps
(ρ = 0.75) the multiplier is 3×. At 45,000 rps (ρ = 0.9) it is 9×. At
49,500 rps (ρ = 0.99) it is 99×, and p99 latency — which scales worse
than the mean under variability — is seconds. The system's *throughput*
rose smoothly 25k → 37.5k → 45k → 49.5k the whole way; its user
experience collapsed. A capacity plan built from the throughput number
alone would call 45,000 rps "90% headroom utilized, healthy", when the
latency at that point already exceeds several services' budgets.

**Coordinated omission hides the cliff.** The load generator that
measures latency while running *at* 60,000 offered rps has its own
problem: a closed-loop client waits for responses before sending, so
during saturation it measures fewer, sampled successes and under-reports
the requests that are waiting in the backlog — the requester never asks
"where is my response from 30 seconds ago?" until it times out. The
benchmark that certified "50k at 20 ms" was measured in a regime the
production load never visits. (Gil Tene's writing on this failure of
latency measurement is the standard reference; see the notes by title.)

**Batching: throughput bought with latency.** An inference service runs
single-request GPU calls at 100 requests per second and 15 ms each.
Enabling batches of 64 with a 10 ms collection window lifts throughput
toward 4,000 requests per second — while every request now pays up to
10 ms waiting for the batch to fill, plus the batch's compute time. That
is a good trade for a video pipeline and a bad one for an auction bid.
The claim's arithmetic cannot even represent the choice, because both
outcomes can report the same "the system is fast at high throughput"
headline. When it accidentally works: for lightly utilized, low-variance
services with short queues, throughput and latency genuinely track each
other — the regime every benchmark lives in, and the reason the
inference feels earned.

## Practical Implications

- Report latency and throughput together, at the same offered load, from
  the client's clock — a throughput figure without a percentile latency
  is marketing, not engineering.
- Size capacity against the utilization cliff, not the ceiling: keep
  steady-state ρ comfortably below ~0.7–0.8, because tails degrade long
  before throughput does (the same lesson the thread-pool audit in this
  collection draws for concurrency).
- Load-test open-loop (constant arrival rate) and watch queue depth and
  time-out rates, not just achieved rate; closed-loop generators
  under-report exactly the failures that matter.
- Treat every batching knob (`linger.ms`, batch size, flush interval) as
  an explicit latency-for-throughput transaction and price both sides.
- Watch the leading indicators of the cliff: queue depth, connection-pool
  saturation, and GC pause frequency — all of which move before user
  latency fully explodes.

## Interview Questions

### A service advertises 50k req/s at 20 ms. What load can it actually take?

Only a load whose steady-state concurrency stays near 1,000 requests in
flight (Little's Law: 50,000 × 0.020). The rate alone is meaningless
without utilization: as offered load approaches 50,000, queueing delay
grows nonlinearly (the ρ/(1−ρ) curve), so the "50k at 20 ms" regime ends
well below 50k offered. A strong answer reframes the advertisement as a
point on a saturation curve, not a property of the system.

### Derive why latency explodes during overload while throughput stays flat.

Above capacity, completed work is pinned at μ, so the excess arrivals
accumulate: queue length grows at (λ − μ) per second. By Little's Law,
wait = L/λ, which grows without bound as L grows, while throughput
remains pinned at μ. The dashboard shows flat throughput because
flatness-at-capacity is what saturation looks like; latency carries the
entire signal of overload.

### Why does batching increase both throughput and latency, and when is it right?

Batching amortizes fixed per-operation costs (fsyncs, network round
trips, GPU launches) across many items, raising throughput; the collection
window plus the larger batch's processing time adds latency to every
item. It is right when the workload tolerates the added window (analytics,
log shipping, offline scoring) and wrong when per-item deadlines are
tight (ad bidding, trading). The point is that it is a trade, not an
optimization.

### Your p99 tripled but throughput is unchanged. What do you check first?

Queueing indicators: queue depth, connection-pool saturation, lock or
thread-pool utilization, GC pause rates — anything that adds waiting
without reducing completion rate. The throughput number cannot see this
failure; the concurrency-side metrics can. Also check for a shifted
service-time distribution (cache hit-rate drop, a slow downstream), since
Kingman's approximation says variability multiplies waiting at the same
utilization.

### How is this misconception different from "more bandwidth makes it faster"?

Different confusion, same family. The bandwidth audit in this collection
conflates *network capacity* (bits per second) with round-trip-bound
latency — an infrastructure-measurement error. This page conflates
*measured service throughput* with per-request response time — a
queueing error. Both fail by reading a capacity-style number as a speed
promise, and both are corrected by measuring the thing the user
experiences at the load actually offered.

## Key Takeaways

- Throughput and latency are coupled only through concurrency and
  queueing; neither implies the other.
- Little's Law (W = L/λ) turns backlog into latency with no model
  assumptions — the overload arithmetic is exact.
- Waiting grows nonlinearly as utilization approaches 1; tails degrade
  long before the throughput number moves.
- Saturation looks like success on a throughput dashboard: flat at
  capacity, green, while latency is unbounded.
- Batching is an explicit throughput-for-latency trade; open-loop load
  tests and concurrency-side metrics are how you see the cliff coming.

## Cross-References

- [Misconceptions: bandwidth-fixes-latency](./bandwidth-fixes-latency.md)
  — the sibling audit, delineated in the text: network capacity versus
  RTT-bound work, a different conflation in the same family
- [Connection Atlas: Scheduling & Queueing](../connection-atlas/scheduling-queueing.md)
  — the queueing mechanics behind the saturation curve
- [Follow-up Tree: Connection Pooling](../followup-tree/connection-pooling.md)
  — the pool as the queue your latency actually waits in
- [Misconceptions: averages-summarize-latency](./averages-summarize-latency.md)
  — the statistical sibling: one number hiding the distribution
- [Misconceptions: more-threads-faster](./more-threads-faster.md) — the
  concurrency sibling: tails degrade before throughput, at the pool level
- [Performance Engineering: Latency Analysis](../../performance-engineering/latency-analysis.md)
  — measuring and attributing latency in real systems
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- J. D. C. Little. *A Proof for the Queuing Formula L = λW*, Operations
  Research, 1961 — cited by title.
- L. Kleinrock. *Queueing Systems, Volume 1: Theory*, Wiley, 1975 — the
  utilization and waiting-time relations summarized above, cited by
  title.
- G. Tene. *How NOT to Measure Latency* — coordinated omission and
  closed-loop measurement hazards, cited by title.
