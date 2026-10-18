# "We load-tested at 2x peak, so production is safe"

## Overview

This page audits the certification claim that ends many performance reviews:
because the team load-tested at twice peak traffic, production is safe. The
claim deserves its confidence more than most — load testing genuinely finds
collapse points, and a service that survived a disciplined 2x test has real
evidence behind it. But the claim overreaches in a specific, listable way: a
load test certifies a *system under synthetic load*, and every gap between
the test rig and production — environment parity, traffic shape, data
distribution, failure injection, measurement method — quietly deletes a
precondition the "safe" conclusion depends on. Synthetic traffic is smooth
where production is bursty, coordinated omission hides the tail, and a load
test by construction exercises capacity, not correctness. The honest
reading of a passed test is therefore a bound with named exclusions, not a
certificate — and a failed test is the most valuable report the team owns.
This page states
the claim fairly, enumerates the parity gaps that void it, and explains what
a load test actually proves: collapse points, not safety.

## The Claim, Stated Fairly

The strongest common form of the claim is: "We replayed 2x projected peak
through the full stack and the p50s were fine, so production is safe for
the holiday." Stated this way, the claim is not recklessness; it reflects a
real and increasingly disciplined practice — environments that stand up
production-like topologies, replay tools that generate serious volume, and
teams that treat a passed test as a genuine release gate.

The claim deserves its fairness because the evidence it cites is real
evidence. The question is what the evidence covers: a load test proves that
*the tested workload, against the tested environment, measured the tested
way* survived 2x. Every one of those italicized qualifiers is where the
certification leaks, and "safe" is a conclusion about production, where the
workload, environment, and failure modes are different.

## Verdict

**False.** The claim inverts in a valid counterexample: production falls
over at a fraction of tested peak because the test environment was missing
the production cache, the synthetic traffic lacked the burst shape and the
tail behaviors, the test data skewed uniform where production is hot-keyed,
or the outage trigger was a failure mode no load test injects. A load test
at 2x peak proves that the collapse points were not at 1x — it does not
prove that the system is *safe*, because safety includes correctness under
load, tail behavior, degraded modes, and failure interaction, none of which
a load test measures.

## Why People Believe It

The kernel of truth is that load testing is among the highest-value
reliability practices, and teams that do it seriously catch real collapse
points every year. The "2x" quantifier gives the claim a scientific flavor —
a number, a margin, a pass/fail — and the review meeting wants exactly that
shape of assurance. Once the test is framed as a *gate*, the pass becomes a
certificate, and certificates get read as conclusions about a broader
domain than they cover.

The belief also survives because the test usually *is* fine and production
usually *is* fine. The common regime — moderate parity, reasonable replay,
no exotic failure — makes the claim indistinguishable from a true one. The
deletion is invisible until the year production fails on Black Friday at
0.6x of the tested peak because the test rig shared the production cache
cluster, or because the bot traffic that dominates real peak behaves
nothing like the replay. Survivorship does the rest: nobody schedules a
review for the load test that quietly saved the peak.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Production is safe" | A load test certifies capacity for the tested workload shape on the tested environment — a collapse-point bound, not a safety certificate |
| "2x peak" | The margin applies to the synthetic offer rate; production stress depends on burst shape, concurrency, hot keys, and retry amplification the test may not model |
| "The p50s were fine" | Means hide the tail; coordinated omission makes the measured distribution optimistic, and users live in the tail |
| "Full stack" | Parity gaps — shared caches, smaller datasets, stubbed third parties, different instance classes — void the certification silently |
| "We tested the system" | Load tests exercise capacity, not correctness: a fast system returning wrong answers, lost writes, or deadlocked flows passes |
| "The test passed" | The honest artifact is a list of found collapse points and their fixes, plus the residual risks the rig could not reach |

The correct sentence: "Our load test found no collapse point at 2x of the
synthetic workload we chose, on an environment with these named parity gaps,
measured with these known blind spots. It bounds some failure modes, not the
system's safety."

## Where It Breaks

**The parity counterexample, worked end to end.** The October load test runs
in a staging environment that *shares* the production Redis cluster (for
cost), stubs the third-party fraud check, and runs on a dataset one-tenth
the size of production. At 2x peak, p50 latency is 40 ms and the team
certifies. On Black Friday, three things differ: the production-scale key
space defeats the in-process LRU the small dataset accidentally allowed;
the fraud check — stubbed in test — adds a 200 ms synchronous call that
magnifies queue depth exactly when traffic arrives; and the shared cache now
serves two full traffic profiles. The system saturates at 0.6x of projected
peak. Every number the load test reported was true; the certification was
still void, because "safe" was concluded for a system the test did not
test.

**Coordinated omission and the lying distribution.** A load generator that
sends requests at a fixed cadence while the system stalls measures the
system only when it responds: the *missing* measurements are precisely the
worst experiences, because the generator did not send during the stall.
This is coordinated omission — the test's sampling policy hides the exact
events the test exists to find. Synthetic load is also too polite in other
ways: no connection storms, no retry avalanches, no garbage-collector pauses
coinciding with bursts, no slow clients. The tail the test reports is a
modeled tail, and production users live beyond it. Pair the load test with
the latency-measurement discipline of percentiles and open-system
measurement, or the pass is a mean-shaped illusion.

**Data skew and the hot-key economy.** Replay traffic usually spreads keys
uniformly; production traffic follows power laws. A shard or cache cell that
never warmed in test takes the concentrated read load of one celebrity
product or one viral account in production, and a *single* hot key can pin a
partition's CPU while fleet-wide utilization reads 15%. Load tests find
collapse points in aggregate; production collapses pointwise. Testing with
production-shaped data distributions — or replaying production-sampled
traffic — is the difference between a capacity certificate and a capacity
guess.

**Degradation logic never trips in a clean test.** A load test runs the
happy regime: all dependencies up, all caches warm, all timeouts
unused. Production safety is substantially about the *other* regimes —
circuit breakers opening, fallbacks serving, bulkheads isolating — and
those paths receive no load in a pass-shaped test, so their tuning (timeout
ceilings, breaker thresholds, retry budgets) is validated against nothing.
The classic production failure is the retry avalanche: a dependency slows
10x, every caller's untested timeout fires, the retry multiplier lands on
the system at peak, and the load test's "2x" margin is consumed by an
amplifier the test never switched on. A load test that has not been run
*while* injecting dependency failures has certified only the regime that
needs the least certification.

**Capacity is not correctness.** A load test passes a system that returns
wrong answers quickly: the race that loses a duplicate coupon under
concurrency, the overflow that corrupts an id, the deadlock that only forms
under parallel load — all invisible to a throughput assertion. The claim
"safe" spans correctness and capacity; the load test speaks only one
language. This is the same failure as trusting green suites for correctness:
the instrument measures the dimension it was built for, and the conclusion
silently imports the other dimensions. The disciplined claim is "no
capacity collapse found", and it is paired with correctness instruments
under load, plus failure injection (kill nodes, fail the cache, saturate a
dependency) to see how the system degrades — which is what production safety
actually requires.

## Practical Implications

- Publish load-test results as a bound, not a certificate: "no collapse at
  2x of workload X on environment Y with gaps Z" — the gaps list is the
  honest part and the part reviews skip.
- Attack the parity list explicitly: dataset size, cache sharing, stubbed
  dependencies, instance classes, and config drift each void a claim
  silently; close or name them every run.
- Shape the synthetic traffic like production: bursts, diurnal ramps, power
  law keys, slow clients, retries — and measure with an open-system
  generator that captures stalls, not a closed loop that hides them.
- Pair load tests with failure injection and correctness checks under
  concurrency: capacity without correctness is a fast wrong system.
- Use the found collapse points as the deliverable: a load test whose value
  is the pass is a test that found nothing yet.

## Interview Questions

### A service passed a 2x-peak load test but failed in production at 0.6x peak. Name four mechanisms that make this possible.

Environment parity gaps (shared or stubbed dependencies, smaller datasets),
traffic-shape gaps (no bursts, no hot keys, no slow clients, no retry
amplification), measurement blind spots (coordinated omission hiding
stalls, means hiding tails), and failure-mode absence (no dependency
failures, no cache misses at production scale, no rebalancing). The test
bounded the wrong workload on the wrong system.

### What is coordinated omission and how does it corrupt a load-test result?

A load generator that sends on a fixed schedule measures only requests it
actually sent; when the system stalls, the generator does not add load, so
the worst-case experiences go unmeasured — the sampling policy omits
exactly the regime under test. The reported distribution is therefore
optimistic, particularly in the tail. Open-system measurement and
rate-independent instrumentation are the mitigations.

### Why does "2x peak" not multiply through to a safety margin?

Because the margin applies to the offer rate, while the system's stress
depends on burst shape, concurrency, hot-key concentration, and retry
amplification — factors the rate does not capture. A 2x uniform offer can be
less stressful than 1x bursty traffic with one hot key and a retry storm.
The multiplier is a marketing number unless the shape matches production.

### What should a load-test report contain if it is to be honest?

The workload definition and its divergence from production traffic, the
environment parity gaps, the measurement method and its blind spots, the
collapse points found and their fixes, and the residual risks the rig could
not reach. "Passed at 2x" is one sentence of that report, not the
conclusion.

## Key Takeaways

- A load test certifies a collapse-point bound for a specific synthetic
  workload on a specific environment; "production is safe" imports every
  gap between the rig and reality.
- Parity gaps void the claim silently: shared or stubbed dependencies,
  dataset scale, instance class, and config drift each invalidate a pass.
- Synthetic traffic is too smooth: bursts, power-law keys, slow clients,
  and retry avalanches are the stressors that break systems at fractions of
  tested peak, and coordinated omission hides the tail that proves it.
- Load tests speak capacity, not correctness; pair them with correctness
  checks under concurrency and failure injection to approach "safe".
- The deliverable of a good load test is a list of collapse points found —
  a test valued for its pass has not earned its run.

## Cross-References

- [Misconception: "The system does 50k req/s, so responses are fast"](./high-throughput-means-low-latency.md)
  — the sibling throughput claim: that audit kills the inference from a
  rate record to latency experience, this one kills the inference from a
  test result to production safety; both turn on the missing quantifiers
  behind an impressive number.
- [Misconception: "Average latency is a good performance metric"](./averages-summarize-latency.md)
  — the measurement sibling: means hide the tails where load tests and
  production diverge most, and percentile discipline is the antidote to
  the "p50s were fine" defense.
- [Misconception: "All tests pass, so the code is correct"](./green-tests-mean-correct.md)
  — the correctness sibling: both claims promote a sampling instrument into
  a conclusion, and both fail on the dimensions the instrument does not
  measure.
- [Follow-up Tree: SLOs & Error Budgets](../followup-tree/slos-and-error-budgets.md)
  — what to do with load-test evidence: budgets and burn rates turn
  capacity findings into operational decisions, which is the honest
  successor to the "safe" certificate.
- [Load Testing Strategies](../../sre/load-testing-strategies.md) — the
  practice itself: workload modeling, rig design, and where the discipline
  already accounts for these gaps.
- [Chaos Engineering](../../sre/chaos-engineering.md) — the failure-
  injection complement that tests what load tests cannot: how the system
  degrades while loaded.
- [Capacity Planning](../../sre/capacity-planning.md) — how the headroom
  behind "2x" is actually derived and maintained.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- Google SRE. *Site Reliability Engineering*, the "Testing for Reliability"
  chapter — load testing as one instrument among failure injection and
  configuration testing, and why testing cannot prove reliability.
  <https://sre.google/sre-book/testing-reliability/>
- G. Tene. *How NOT to Measure Latency*. JLove/Latency Hype talk, 2013 —
  the canonical statement of coordinated omission and open-system
  measurement, cited by title.
- B. Gregg. *Systems Performance*, Second Edition, Addison-Wesley, 2020 —
  load versus latency and the methodology of measurement, cited by title.
- N. J. Gunther. *Guerrilla Capacity Planning*. Springer, 2007 — the
  capacity-modeling backdrop for why uniform offer rates mislead, cited by
  title.
