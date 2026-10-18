# "Average latency is a good performance metric"

## Overview

The mean is the default statistic of every dashboard, and "our average
latency is 40 ms" is the sentence in which most performance stories get
told to management, written into SLAs, and compared release over release.
For latency specifically, the average is close to the *worst* summary
that still qualifies as a statistic: real latency distributions are
bounded below, long-tailed, and frequently multimodal — cache hits at 2
ms, database reads at 50 ms, retries at 1 s — so the mean describes no
user's experience and moves surprisingly little even when the tail
collapses or explodes. This page audits the claim that averages are a
good latency metric, works the arithmetic that makes tails dominate user
experience, introduces percentiles and their (frequently botched)
aggregation, explains coordinated omission — the measurement bias that
lets a stalled service report fine numbers — and marks the regime where
averages genuinely do suffice.

## The Claim, Stated Fairly

The strongest common form is: "We track average (mean) latency per
endpoint; it is the single number that summarizes how fast the service
is, and regressions show up in it." The claim deserves fairness because
the mean is a genuinely excellent statistic — for the right quantities.
It is additive, stable, and exactly what capacity math needs: total
service time per second, average concurrency, throughput. Many services
that report means are also healthy, because healthy distributions have
short tails where mean and median nearly coincide. The kernel of truth
is that *some* summary is necessary and the mean is the one every tool
computes by default. The audit question is what the mean of a skewed,
multimodal distribution tells you about user experience — and what it
silently fails to tell you.

## Verdict

**Incomplete.** The mean is a valid statistic but an invalid
*representative* for latency: on a long-tailed distribution it is
dominated by the exact requests that define user-perceived quality, it
is insensitive to precisely the regressions that hurt (a small fraction
of very slow requests barely moves it), and it is blind to multimodality
(two services with the same mean can differ by 100× at p99). The
standard fix is to report the distribution's percentiles — p50, p95,
p99, p99.9 — via histograms that can be merged, and to keep the mean for
its honest jobs: throughput, utilization, and cost accounting. The claim
is incomplete rather than false because for tight, unimodal distributions
the mean *is* a decent representative — the failure begins when latency
spreads, which is when measuring it matters.

## Why People Believe It

The kernel of truth is statistical respectability. The arithmetic mean
is the minimum-variance unbiased estimator of a distribution's center
under Gaussian assumptions, and everything engineers learn first —
averages of test scores, averages of utilization — conditions them to
read "average" as "typical". Dashboards default to `avg()`; spreadsheets
make it one function call; SLA templates from the 2000s were written in
means because percentile tooling barely existed at scale. For a service
whose latency is tight (most requests within a small factor of each
other), the mean genuinely does track the typical experience.

Three props hold the belief up. First, the measurement tooling bias is
self-reinforcing: metrics systems aggregate cheaply by summing and
averaging, so means are what gets recorded, charted, and alerted — and a
team watching only means sees a stable line and concludes latency is
stable. Second, the mean is *needed* for other honest purposes (load,
cost, Little's-law capacity reasoning), so its presence in the toolkit
laundered its use as a user-experience proxy. Third, tail events are
individually rare; a developer testing by hand usually gets a
representative (fast) request, so intuition built on manual use reports
"it's fast" while the distribution's tail tells a different story.

What is lost is the shape. A mean is one moment of the distribution; a
latency SLO is a statement about a quantile. The two are not merely
different numbers — they can move in *opposite directions* during the
same deployment, which is exactly the reconciliation exercise interview
panels love.

## The Correct Formulation

| Statistic | What it answers | Behavior on long-tailed latency | Honest use |
|---|---|---|---|
| Mean (arithmetic average) | Total cost per request; input to capacity math | Moves little when the tail worsens; can improve while users suffer | Throughput, utilization, Little's law, cost per request |
| Median (p50) | The typical request | Stable and honest — but blind to the tail | "How fast is a normal request?" |
| p95 / p99 / p99.9 | The tail the worst-off users hit | Moves early and sharply on regressions | SLOs, alerting, regression gates |
| Max | The single worst sample | Noise-dominated; one outlier ruins it | Triage stories, not metrics |

The precise statement: latency user experience is a *quantile*
question — "what fraction of requests are acceptably fast?" — and the
correct summaries are percentiles computed from histograms. Two
operational rules follow. First, percentiles are not additive: you
cannot average ten hosts' p99s, or twenty minutes' p99s, because the
p99 of a mixture is not the mean of the p99s — you must merge the
underlying histograms and recompute, which is why histogram-based
instrumentation (HDR-style log-linear buckets, or OpenTelemetry
histogram instruments) is the foundation of honest latency reporting.
Second, percentiles need volume: p99.9 of an endpoint that serves
50,000 requests per hour means "the slowest 50 requests", which is a
real statistic; p99.9 of an endpoint serving 40 requests per hour is
noise, and a well-chosen p99 or p99.5 is the honest substitute.

## Where It Breaks

**The mean hides the tail, arithmetically.** Suppose a service serves
99.5% of requests at 10 ms and 0.5% at 1 s (a stuck cache shard, a GC
pause, a retry storm). The mean is 0.995 × 10 + 0.005 × 1000 ≈ 15 ms.
Now a regression triples the slow path to 3 s for 0.5% of requests: the
mean moves 15 → 25 ms — a 67% jump that still looks like noise next to
deployment jitter — while the p99 goes from 10 ms to 3,000 ms, a 300×
degradation in the statistic that matches the user whose request stuck.
Run the same example in reverse: a "mean improved 20%" release can be
entirely a p50 improvement while the tail doubled. The mean did not lie;
it answered a question nobody was asking.

**Tail latency dominates the fan-out case.** A page that fans out to
100 backend calls — the standard microservice shape — is as slow as its
slowest dependency. With each call having just a 1% chance of exceeding
its budget, the probability that *at least one* call does is
1 − 0.99¹⁰⁰ ≈ 63%: the majority of page loads experience the tail that
the mean ignores. This is the argument of Dean and Barroso's "The Tail
at Scale" (2013), and it is why systems that care invest in tail
techniques — request hedging (sending a speculative duplicate for slow
percentiles), fan-out reduction, and per-call deadlines — rather than
in mean improvements.

**Coordinated omission: the ruler that bends.** A load generator that
sends one request every 100 ms measures only the requests it *sent*.
When the system stalls for 5 s, the pending request's response finally
arrives, the generator immediately resumes its 100 ms cadence — and the
system performed the equivalent of 50 requests during the stall, of
which the sample contains one. The worst latencies of the worst episode
are structurally absent from the data, which is why a service can queue
users for seconds during an incident while the load test that "proved"
its p99 was 80 ms never noticed. The fix is rate-independent
measurement: record each request's *intended* start time and count the
unsent ones (Gil Tene's coordinated-omission correction, implemented in
HdrHistogram-based tooling), and validate load tests against production
histograms rather than against their own averages.

**When averages suffice.** The mean remains the right tool where the
quantity is additive and unimodal-ish: CPU utilization (a ratio with a
meaningful total), queue depth, request size, cost per request, and
throughput. It also suffices for latency whose distribution is tight —
a pure cache lookup with 99.9% of hits between 1–3 ms has a mean that
*is* the typical experience. The failure is not "averages are wrong";
it is "averages of skewed distributions are the wrong *representative*"
— and latency, as deployed systems actually behave, is the canonical
skewed distribution. A disciplined team keeps both: histograms for the
experience, means for the accounting.

## Practical Implications

- Instrument histograms, not just means: log-linear latency buckets
  (HDR-style) or OpenTelemetry histogram instruments, merged at
  aggregation time so percentiles survive across hosts and time windows.
- Set SLOs on percentiles matched to user experience (for example,
  99% of page loads under 300 ms), alert on burn rates against those
  SLOs, and gate releases on p95/p99 deltas — not on mean deltas.
- Fix your load tests before trusting them: scheduled-rate generation
  with coordinated-omission correction, and cross-check the test's
  histogram against production's before quoting either.
- Do tail engineering where fan-out concentrates the tail: hedge slow
  requests, bound fan-out, set per-call deadlines and propagate them,
  and treat "which dependency owns our p99?" as a standing question.
- Quote percentiles with their sample size; know the request volume
  that makes a p99.9 meaningful, and refuse to average percentiles
  across any dimension.

## Interview Questions

### Your service's mean latency improved after a release, but support tickets went up. Reconcile.

Percentiles tell the other half of the story: the release likely
sped the common path (p50/p95 down, mean follows) while degrading the
tail — a new code path, a cache that now misses for some tenants, a
retry loop — pushing p99/p99.9 sharply up. The mean weights by total
time and is insensitive to a small fraction of very slow requests;
users who hit the tail write tickets. Pull the histograms for both
releases and compare quantiles to confirm; the reconciliation is the
point, not any specific mechanism.

### Why is "average of p99 across our ten hosts" meaningless, and what do you do instead?

A percentile is a property of a distribution, not a sample statistic
that averages: the mixture's p99 is determined by how the hosts' full
histograms overlap, not by the average of their per-host p99s — ten
hosts at p99 = 20 ms can jointly have p99 = 900 ms if one host's slow
1% lands at the top of the mixture. The correct operation is to merge
the ten hosts' histograms (bucket counts are additive) and recompute
the quantile. This is the operational reason to insist on histogram
instrumentation rather than precomputed percentile gauges.

### A page makes 100 backend calls, each with p99 = 10 ms and 1% of calls over 200 ms. Roughly what fraction of page loads are slow, and what are two mitigations?

The chance that all 100 calls are fast is 0.99¹⁰⁰ ≈ 0.366, so about
63% of page loads include at least one slow call — the tail is now the
*common case* at page level. Mitigations: reduce or batch the fan-out
(one call for the data of ten), and hedge — send a speculative
duplicate for a call that exceeds its expected duration and take the
first response, which trims the tail at modest extra load (with the
caveat that hedging needs idempotent handlers). Deadline propagation
so one slow dependency fails fast is the third standard answer.

### What is coordinated omission, and how do you correct for it in a load test?

It is the bias where a load generator's fixed-rate schedule hides the
system's worst behavior: when responses stall, the generator sends
fewer requests than the schedule promised, so the requests that would
have experienced the worst queuing are never issued and never
measured — the sample omits exactly the episode that matters.
Correction: record each request's *intended* start time independent of
when it was actually sent, and account for the unsent requests (the
HdrHistogram approach), or drive load open-loop from a schedule rather
than closed-loop from responses. Validation: reproduce a stall
deliberately and confirm the corrected histogram reflects it.

## Key Takeaways

- The mean of a skewed, multimodal distribution represents nobody:
  it is dominated by the tail yet insensitive to tail regressions —
  the two properties that make it the wrong latency representative.
- Percentiles answer the user-experience question ("what fraction of
  requests are fast?"); they require histogram instrumentation and
  can never be averaged across hosts or time buckets — merge, then
  recompute.
- Fan-out turns per-call tails into page-level common cases: at 100
  calls of 1% tail each, ~63% of pages hit the tail; tail engineering
  (hedging, batching, deadlines) beats mean optimization.
- Coordinated omission silently deletes the worst episodes from load
  test data; open-loop, intended-start-time measurement is the fix.
- Averages keep their honest jobs — throughput, utilization, cost,
  Little's-law capacity math — and suffice for tight unimodal
  quantities; the mistake is promoting them to latency SLOs.

## Cross-References

- [Misconception: Bandwidth Fixes Latency](./bandwidth-fixes-latency.md)
  — the sibling performance myth: why adding capacity does not move
  the latency statistic that matters
- [Misconception: Good Average-Case Complexity Guarantees Good Performance](./average-case-complexity.md)
  — the algorithmic cousin: averages over input distributions versus
  tails and adversarial cases
- [Misconception: Async/Await Makes My Code Run in Parallel](./async-await-parallelism.md)
  — where event-loop stalls inject the multimodality this page measures
- [Follow-up Tree: Rate Limiter Design](../followup-tree/rate-limiter-design.md)
  — rate-limiting decisions that reshape the latency distribution itself
- [Connection Atlas: Scheduling & Queueing](../connection-atlas/scheduling-queueing.md)
  — queueing behavior as the physical source of long tails
- [Tail Latency](../../distributed/fundamentals/tail-latency.md) — the
  distributed-systems treatment of the quantile question
- [Performance Benchmarking](../../arch/performance/benchmarking.md) —
  measurement methodology this page's load-test rules build on
- [SLO, SLI, SLA](../../sre/slo-sli-sla.md) — turning percentiles
  into objectives, budgets, and alerting
- [System Metrics](../../interview/system-design/metrics.md) — the
  interview-facing menu of metrics and their traps

## References

- J. Dean and L. A. Barroso. *The Tail at Scale*. Communications of
  the ACM, Vol. 56 No. 2, February 2013, cited by title (fan-out tail
  math and hedging techniques).
- Gil Tene. *How NOT to Measure Latency* (Joker/Devoxx talk) and the
  HdrHistogram project — coordinated omission and interval-corrected
  measurement, cited by title; <https://github.com/HdrHistogram/HdrHistogram>
- J. D. C. Little. *A Proof for the Queuing Formula: L = λW*.
  Operations Research, 1961, cited by title (Little's law and the
  honest uses of means).
- Brendan Gregg. *Systems Performance* (2nd ed., 2020) — percentile
  reporting and utilization-vs-latency distinction, cited by title.
- OpenTelemetry. *Metrics API — Histogram instruments*, cited by title
  as the histogram-merge mechanism referenced above.
