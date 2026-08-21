# Load Testing Strategies

> "A load test that doesn't change your architecture is a load test that didn't find the limit." — paraphrase of the Google SRE Workbook's discussion of load testing as a *discovery* activity, not a *validation* one.

Load testing is the systematic injection of synthetic demand into a system to discover its performance envelope. The output of a load test is not "we passed" — it is a set of numbers: the throughput at which latency crosses your SLO, the throughput at which errors begin, the throughput at which a resource saturates, the shape of degradation under sustained load. The numbers are then fed into capacity planning, autoscaling policy, SLO targets, and procurement decisions. This chapter covers the test types, ramp-up models, environment considerations, the metrics that matter, the tools, and a concrete test plan template.

## Test Types

The taxonomy below is the industry-standard set, codified in k6 and Gatling documentation and consistent with the Google SRE Book's discussion of testing for reliability (Chapter 12). The five types answer five different questions.

```
┌─────────────┬──────────────────────────────┬──────────────────────────────────────┐
│ Type        │ Question answered            │ Typical duration                    │
├─────────────┼──────────────────────────────┼──────────────────────────────────────┤
│ Load test   │ Does the system handle       │ 30–60 min at expected peak         │
│             │ expected production load?    │                                     │
│ Stress test │ What is the breaking point?  │ Ramp until failure, ~30 min         │
│ Spike test  │ How does it react to sudden  │ Short, very high load (1–5 min)    │
│             │ surges?                      │                                     │
│ Soak test   │ Does it degrade over time    │ 4–24 hours at moderate load        │
│             │ (leaks, exhaustion)?         │                                     │
│ Breakpoint  │ Where exactly does the      │ Slow ramp, run to breakpoint       │
│ test        │ first SLO violation occur?   │                                     │
└─────────────┴──────────────────────────────┴──────────────────────────────────────┘
```

### Load test (baseline / smoke)

The simplest and most-ran type: hold a target throughput at the *expected production peak* and verify that latency stays inside the SLO for the duration. The expected peak is not "what we see now" — it is the modeled peak from capacity planning: `current_peak × growth × seasonal × safety_buffer`. If your service is currently peaking at 1,000 RPS, growing 50% over the year, with a 3× seasonal factor and a 1.3 safety buffer, the load-test target is ~5,850 RPS.

### Stress test

Run beyond the modeled peak until something breaks — the system errors out, latency crosses an SLO, or a resource saturates. The point is to characterize the *cliff*: what is the failure mode at the edge of the envelope? Is it a clean degradation (graceful, errors rise linearly) or a cliff (sudden total outage)? The SRE-relevant question is *the cliff*, not "did we pass" — every system fails eventually, and how it fails determines your runbook.

### Spike test

A spike test models a sudden surge in traffic — a Black Friday flash sale, a viral product launch, a cache-miss storm after a deploy. The shape is a near-vertical ramp from baseline to 5–10× baseline in a few seconds, held for a short duration (1–5 minutes), then dropped back. The spike tests three things: (1) does autoscaling react fast enough to keep latency inside SLO during the ramp? (2) do circuit breakers / rate limits / graceful-degradation paths trigger? (3) is there a thundering-herd risk (e.g., every request triggers a cache refresh at once)?

### Soak test (endurance)

Run a moderate load (60–80% of peak) for 4–24 hours. The point is *not* to find a sudden failure; it is to find slow-onset degradation:

- **Memory leaks** — a slow drift in `container_memory_working_set_bytes` over hours, often invisible in shorter tests.
- **Connection-pool exhaustion** — a slow growth in connections in `TIME_WAIT` or in the application's pool gauge.
- **File-descriptor leaks** — slow growth in `lsof` count.
- **Log volume growth** — disk fills; rotates at unexpected times.
- **Database connection caches** — the planner's cache evicts the wrong queries over time, latency creeps.

Soak tests catch bugs that take hours to manifest. They are typically run before major version releases and as part of a quarterly cadence, not on every commit.

### Breakpoint test

A specific instance of a stress test where the goal is to find the *exact* throughput at which the first SLO violation occurs. The shape is a slow, continuous ramp; the breakpoint is the throughput at the moment the SLI crosses the SLO target. Useful for setting your autoscaling maximum — the `maxReplicas` should sit comfortably below the breakpoint, leaving headroom.

## Ramp-Up Models

A load test's *shape* — how throughput rises from zero to target — is the ramp-up. Three common models:

```
Step (staircase)         Linear                Exponential
                                                          
    │  ╱──╱──╱──╱            │      ╱──                    │       ╱
    │ /                       │    ╱                        │      ╱
    │/                        │  ╱                          │     ╱
    │                         │╱                            │  ╱─
    └─────────► t             └─────────► t                 └────► t (log scale)
    Hold-then-jump             Smooth climb                 Saturates quickly
    Each step is a mini-test   Easy on autoscalers          Stress-like from start
```

| Model | When to use | When to avoid |
|---|---|---|
| **Step (staircase)** | Find the breakpoint cleanly; each step is a stable mini-test; verify SLO at each level | When testing autoscaling behavior — it learns to predict the jumps |
| **Linear ramp** | Most general purpose; mimics organic growth; lets autoscaling react | When you want to find the exact cliff quickly |
| **Exponential** | Stress-like from start; spike-test precursor; simulates viral adoption | When autoscaling needs time to react; saturates too fast for HPA |
| **Square (instant)** | Pure spike test; off → 10× peak instantly | Anything not specifically about spikes |

The shape is part of the test design — it determines what you can conclude. A step test with a 5-minute hold at each step gives you stable latency measurements per step; an exponential ramp gives you only the moment of crossing.

## Test Environment: Prod-Like vs Staging

The single biggest source of misleading load-test results is testing against an environment that doesn't resemble production. Three issues, in rough order of severity:

1. **Capacity is 1/N of prod.** A staging cluster with 3 nodes does not produce 3 nodes' worth of useful data — it produces a number that, scaled up, is wrong because of non-linear effects (connection pool sizes, contention on shared caches, GC pauses change with heap).
2. **Dataset is not prod-shaped.** A test database with 1,000 rows does not behave like a prod database with 10 billion. Index strategies, query plans, and buffer pool hit rates all change.
3. **Network topology is wrong.** Staging often has everything in one AZ, no VPC peering, no cross-region traffic — hiding latency that dominates the prod user journey.

Three approaches, in increasing order of fidelity and risk:

| Approach | Fidelity | Risk | When to use |
|---|---|---|---|
| **Synthetic against staging** | low | none | CI, smoke tests, regression on every PR |
| **Synthetic against a prod-shadow** | medium | low | Pre-release verification; copy of prod infra, isolated dataset |
| **Replay prod traffic against prod** (shadow load) | high | medium | Quarterly capacity validation; production traffic mirrored to a test path |
| **Direct load against prod** | highest | high | Game day; intentionally run synthetic load on live traffic (off-peak) |

The Google SRE Book's load-testing chapter recommends **shadow traffic against production** as the gold standard for capacity validation: real prod traffic replayed against a duplicate of the prod stack. The risk is bounded by isolating the shadow from the real write path (intercept writes, drop them, log only). This is expensive — it duplicates prod — and that's the point: it is the only environment that actually behaves like prod.

## Metrics to Watch

A load test produces a lot of numbers. The four that matter, and what each tells you:

```
┌──────────────────────────┬───────────────────────────────────────────────────┐
│ Metric                   │ What it tells you                                │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Latency (p50/p95/p99)    │ User-visible experience                          │
│                          │ Watch for p99 >> p95 (cliff, not tail)           │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Throughput (RPS, ops/s)  │ How much work the system does                    │
│                          │ At saturation, throughput stops growing          │
│                          │   while latency keeps rising → you hit a limit   │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Error rate               │ Where the system starts to fail                  │
│                          │ Watch for non-2xx climbing before latency does   │
│                          │   → backpressure / rate-limit / circuit breaker   │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Resource saturation      │ Which subsystem is the bottleneck                │
│   - CPU %                │ CPU-bound, network-bound, disk-bound, or         │
│   - Memory %             │   pool/connection-bound?                          │
│   - Network throughput   │                                                  │
│   - Disk IOPS / MB/s     │                                                  │
│   - DB connection pool   │                                                  │
│   - Goroutine / thread   │                                                  │
│     count                │                                                  │
└──────────────────────────┴───────────────────────────────────────────────────┘
```

### USE method for saturation

Brendan Gregg's **USE method** (Utilization, Saturation, Errors) is the framework for *resource* metrics:

- **Utilization** — how busy the resource is (CPU%).
- **Saturation** — how much work is queued (run-queue length, connection-pool wait time).
- **Errors** — counts of resource-level errors (disk I/O errors, dropped packets, OOM kills).

A resource is saturated at 100% utilization *or* at nonzero saturation, whichever comes first. The bottleneck is the resource whose saturation crosses its threshold first.

### The throughput-latency curve

The single most useful plot from any load test is **throughput vs latency**:

```
 latency
    ms
    │                                        .
    │                                  .  ◄── breakpoint (latency > SLO)
    │                            .
    │                      .            ◄── knee (latency starts rising sharply)
    │                .
    │          .
    │    .
    │.________________________________
    └─────────────────────────────────►
    0         throughput (RPS)        target
```

The curve has a **knee** — the point at which latency stops growing linearly and starts growing rapidly — and a **breakpoint** — the point at which latency crosses your SLO. The system's *safe* throughput is below the knee. The system's *maximum* throughput is around the breakpoint, with degraded quality. Autoscaling should aim to keep the system on the linear part of the curve, well below the knee.

## Tools

| Tool | Language | Strength | Weakness | When to pick |
|---|---|---|---|---|
| **k6** | JavaScript (ES6) | Modern, scriptable, CI-friendly, JS API is clean | Distributed load generation needs k6 Cloud or a cluster | Modern CI-driven load testing; HTTP APIs; engineer-friendly |
| **Locust** | Python | Distributed, web UI, easy to write complex user journeys in Python | Single-process worker limited (~1000 RPS) before needing distributed | Python-shop; complex user-journey scripting |
| **JMeter** | Java | Mature, huge plugin ecosystem, GUI + non-GUI modes | Heavy (JVM), XML config is verbose, GUI is slow | Enterprises with existing JMeter libraries; non-HTTP protocols (JDBC, JMS) |
| **Gatling** | Scala (DSL) | High performance per node (Netty-based), excellent HTML reports | Scala DSL is a learning curve; CI integration harder than k6 | High-throughput single-node tests; teams with Scala expertise |
| **wrk2** | C | Constant-throughput (not closed-loop), tiny footprint, very accurate latency | Configuration is minimal; you'll write Lua for any non-trivial flow | Microbenchmark of an endpoint; p99 correctness matters (closed vs open loop) |
| **Artillery** | JavaScript | YAML/JS mix, easy ramp-up config, AWS Lambda runner | Smaller community than k6 | Quick YAML-defined tests |

### Closed-loop vs open-loop — why wrk2 is special

Most load tools are **closed-loop**: the test fires N concurrent virtual users; each fires a request, waits, fires the next. The throughput is a function of latency — if latency doubles, throughput halves because the virtual users are blocked waiting.

Production is **open-loop**: requests arrive at a rate independent of the system's response. A spike of 1,000 RPS hits your system whether it responds in 100 ms or 1,000 ms. The implication, codified by John D. Mitchell in his analysis of "Little's Law gone wrong" and the basis for the [wrk2 paper](https://github.com/gilt/wrk2): **closed-loop load tests systematically overestimate the system's capacity.** A closed-loop test of "1,000 virtual users" will report lower latency than an open-loop test at "1,000 RPS" because, when the system gets slow, the closed-loop virtual users naturally back off and reduce the offered load.

`wrk2` (and `k6`'s `constant_arrival_rate` executor) are open-loop: they generate requests at a fixed rate independent of the system's response. For capacity planning, prefer open-loop.

### k6 example

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const checkoutLatency = new Trend('checkout_duration_ms');
const checkoutErrors  = new Rate('checkout_errors');

export const options = {
  scenarios: {
    checkout_journey: {
      executor: 'ramping-vus',           // or 'constant-arrival-rate' for open-loop
      startVUs: 0,
      stages: [
        { duration: '2m',  target: 100 },   // ramp
        { duration: '10m', target: 100 },   // hold
        { duration: '2m',  target: 500 },   // stress ramp
        { duration: '5m',  target: 500 },   // stress hold
        { duration: '2m',  target: 0   },   // ramp down
      ],
    },
  },
  thresholds: {
    'http_req_duration{journey:checkout}': ['p(99)<800'],   // SLO: p99 < 800ms
    'checkout_errors': ['rate<0.001'],                       // SLO: <0.1% errors
  },
};

export default function () {
  const checkout = http.post('https://api.example.com/checkout',
    JSON.stringify({ cart_id: 'loadtest-cart', amount: 100 }),
    { headers: { 'Content-Type': 'application/json' },
      tags: { journey: 'checkout' } });

  checkoutLatency.add(checkout.timings.duration);
  checkoutErrors.add(checkout.status !== 200);

  check(checkout, {
    'status 200': (r) => r.status === 200,
  });
  sleep(1);
}
```

Run: `k6 run --vus 100 --duration 10m checkout.js`. The `thresholds` block fails the test (non-zero exit) if SLOs are violated, which makes k6 ideal for gating CI.

## Test Plan Template

A test plan is a short (one-page) document every load test should have. Without it, the test produces numbers nobody can interpret a week later.

```markdown
# Load Test Plan: Checkout API, Q3 2024 capacity validation

## 1. Goal
Validate that the checkout service handles 5,850 RPS sustained for 30 min,
with p99 < 800ms and error rate < 0.1%, per the Q3 capacity plan.

## 2. Hypotheses
- H1: p99 stays < 800ms up to 5,850 RPS.
- H2: Throughput caps at ~7,500 RPS due to DB connection pool size 100.
- H3: Autoscaling (HPA) brings new pods online in < 90s after spike.

## 3. Environment
- Target: staging-blue cluster (1:1 replica of prod, same instance types)
- Dataset: prod-clone of last 90 days of orders (anonymized)
- Load generators: 5 × c5.2xlarge in same VPC, k6 OSS distributed
- Time: Sat 04:00 UTC (off-peak window, no prod deploys scheduled)

## 4. Test phases
1. Baseline 1,000 RPS for 5 min (warmup, validate plumbing)
2. Ramp to 5,850 RPS over 5 min (step test)
3. Hold 5,850 RPS for 30 min (soak under peak)
4. Spike to 12,000 RPS for 60s (spike test)
5. Ramp down over 2 min

## 5. Metrics & SLOs
- p99 latency < 800ms (fail test if violated during phase 3)
- Error rate < 0.1% (fail test if violated during phase 3)
- HPA reaction time < 90s on spike (phase 4)
- DB connection pool gauge stays < 80%

## 6. Rollback
- Stop load with `k6 halt` (graceful)
- Roll back any autoscaler changes
- Notify #eng-loadtest channel before start and after end

## 7. Post-test
- Export Grafana snapshot to S3
- Write test report: throughput vs latency curve, breakpoint, observed
  autoscaler behavior, action items
```

## Common Anti-Patterns

- **Test passes / no action.** A load test that says "we passed" without finding a breakpoint has wasted its run. Every load test should characterize the *cliff*, not just the safe region.
- **Single load generator.** Running 10,000 virtual users from a single k6 process on a single host — the load generator saturates before the system under test does. Distribute.
- **Closed-loop only.** "1,000 virtual users" with closed-loop execution is not the same as "1,000 RPS open-loop." For capacity planning, use the open-loop executor.
- **Test against dev dataset.** A 1,000-row test database will not reveal the query plan that scans 10 billion rows at peak.
- **No ramp-down.** Hard-stopping a load test produces a spike on the *down* side. Always ramp down.
- **Running during prod peak.** Even on staging, shared backend dependencies (a shared QA database, a shared SaaS dependency) can be impacted. Schedule off-peak.

## Interview Questions

**Q1: What are the different types of load tests and when would you use each?**
A: Five standard types: (1) **load test** — hold expected peak throughput and verify SLOs; used for capacity validation before release. (2) **stress test** — ramp beyond peak until something breaks; used to characterize the failure mode at the edge of the envelope. (3) **spike test** — near-instant surge to 5–10× peak for 1–5 minutes; tests autoscaling and circuit breakers. (4) **soak test** — moderate load for 4–24 hours; catches memory leaks, connection exhaustion, slow-onset degradation. (5) **breakpoint test** — slow continuous ramp to find the exact throughput at which the first SLO violation occurs; used to set autoscaling maximums.

**Q2: Why is open-loop testing important, and how does it differ from closed-loop?**
A: In closed-loop testing, virtual users fire a request, wait, fire the next — throughput is a function of latency, so when the system gets slow the offered load naturally drops. Production is open-loop: requests arrive at a rate independent of system response. Closed-loop tests systematically *overestimate capacity* because they back off exactly when the system needs the most stress. `wrk2` and k6's `constant-arrival-rate` executor are open-loop: they hold a fixed offered rate regardless of response time, matching production behavior. For capacity planning, always use open-loop.

**Q3: How do you choose between k6, Locust, JMeter, Gatling, and wrk2?**
A: For modern HTTP-API testing with CI integration, **k6** — JavaScript, clean scriptable API, thresholds gate CI. For Python shops with complex user-journey scripting, **Locust**. For enterprises with legacy JMeter libraries or non-HTTP protocols (JDBC, JMS), **JMeter**. For very high single-node throughput and excellent HTML reports with Scala expertise, **Gatling**. For microbenchmarking a single endpoint where p99 accuracy is critical, **wrk2** — it's open-loop and tiny. The practical modern default is k6 for new projects.

**Q4: How would you set up a load test against a production-like environment?**
A: Three levels of fidelity, increasing in cost: (1) Synthetic against a 1:1 staging cluster with a prod-clone dataset (90-day anonymized copy) — minimum bar for any capacity validation. (2) Shadow traffic against a duplicate of prod: real prod traffic replayed against a duplicate stack with writes intercepted and dropped — gold standard for capacity, expensive. (3) Direct load against prod during off-peak game days — highest fidelity, requires careful coordination, used sparingly. The anti-pattern is testing against a dev-scale cluster with a 1,000-row test database — the numbers from such a test are worse than useless because they're confidently wrong.

**Q5: What metrics do you watch during a load test, and why?**
A: Four classes. (1) **Latency** (p50, p95, p99 — never averages): user-visible experience; watch for p99 >> p95 indicating a cliff rather than a tail. (2) **Throughput** (RPS): how much work the system does; at saturation, throughput stops growing while latency keeps rising — you've hit a limit. (3) **Error rate**: where the system starts to fail; if errors climb before latency does, you've hit backpressure (rate limit, circuit breaker, pool exhaustion). (4) **Resource saturation (USE method)**: CPU%, memory%, network, disk IOPS, DB connection pool, goroutine/thread count — to identify *which subsystem* is the bottleneck, which feeds the capacity-planning fix.

## References

- [k6 — Documentation](https://k6.io/docs/)
- [Locust — Documentation](https://docs.locust.io/en/stable/)
- [Apache JMeter — User Manual](https://jmeter.apache.org/usermanual/index.html)
- [Gatling — Documentation](https://docs.gatling.io/)
- [wrk2 — GitHub (constant-throughput load test tool)](https://github.com/gilt/wrk2)
- [Google SRE Book — Chapter 12: Reliable Cascading (testing)](https://sre.google/sre-book/)
- [Google SRE Workbook — Load testing chapter](https://sre.google/workbook/)
- [Brendan Gregg — The USE Method](https://www.brendangregg.com/usemethod.html)
- [Little's Law on Wikipedia](https://en.wikipedia.org/wiki/Little%27s_law)
