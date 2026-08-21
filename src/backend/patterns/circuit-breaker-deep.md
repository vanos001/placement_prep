# Circuit Breaker Deep Dive

## Overview

A circuit breaker wraps an outbound call site in a state machine that monitors
recent outcomes and short-circuits calls when the downstream is failing. The
name comes from electrical engineering: a breaker that has *tripped* no longer
carries current, and a human (or a timer) has to reset it before current flows
again. Michael Nygard's *Release It!* (2007) introduced the pattern to the
software mainstream as the antidote to **cascading failures** — the situation
where a slow or failing dependency exhausts threads, connections, and memory
in every upstream service until the whole stack stalls.

The crucial distinction from a retry: a **retry** assumes the failure is
transient and tries again; a **circuit breaker** assumes the failure is
sustained and stops trying. A retry multiplies load on a struggling service;
a breaker sheds load. The two are complementary, never substitutes — the
retry handles the burst, the breaker handles the outage.

## The Three States

Every implementation has the same three states. The names are borrowed from
Hystrix and Resilience4j and are now universal.

```
   ┌─────────────────────────────────────────────────────────────┐
   │                                                             │
   │    ┌──────────┐  failure_rate > threshold   ┌──────────┐    │
   │    │  CLOSED  │ ──────────────────────────▶ │   OPEN   │    │
   │    │ (normal) │                              │ (fail    │    │
   │    │          │ ◀────────────────────────── │  fast)   │    │
   │    └──────────┘     N consecutive probes    └──────────┘    │
   │          ▲                succeed                      │    │
   │          │                                              │    │
   │          │              wait_duration                  │    │
   │          │              elapsed                         ▼    │
   │          │            ┌─────────────┐                   │    │
   │          └────────────│  HALF-OPEN   │ ◀─────────────────┘    │
   │                       │ (probes)     │                        │
   │                       └─────────────┘                        │
   │                              │                               │
   │                              │ probe fails                   │
   │                              └─────▶  OPEN (reset timer)     │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘
```

- **CLOSED** — the steady state. Every call goes through. Outcomes are
  recorded into a sliding window. When the failure rate (or the count of slow
  calls) crosses a threshold, the breaker transitions to OPEN.
- **OPEN** — fail fast. No call reaches the downstream. The caller receives
  a `CircuitBreakerOpenError` (or a fallback, or an HTTP 503) within
  microseconds. The breaker stays in OPEN for `wait_duration_in_open_state`,
  which gives the downstream time to recover without being pummelled.
- **HALF-OPEN** — the probationary state. After the wait elapses, a small
  number of probe calls (the *permitted calls in half-open*) are allowed
  through. If enough of them succeed, the breaker CLOSES. If any fails, it
  re-opens and the wait timer restarts. The half-open state prevents the
  "thundering herd on recovery" problem: when a downstream comes back, every
  upstream breaker doesn't immediately slam it at full traffic.

## The Sliding Window

The decision to open is made on a *sliding window* of recent outcomes — not on
lifetime totals. A breaker that opened on cumulative failures would never
recover.

Two window implementations exist; both compute the same number (a ratio of
failures to total calls) but with different memory and traffic profiles.

### Count-based window

A ring buffer of the last N call outcomes. Once full, the oldest entry is
overwritten. Resilience4j's default `slidingWindowType=COUNT_BASED` with
`slidingWindowSize=100` keeps the last 100 outcomes; the failure rate is
`failures / 100`.

```
   slot:   0   1   2   3   4   5   6   7   8   9   ...  99
   outcome: ✓  ✓  ✗  ✓  ✗  ✗  ✓  ✓  ✗  ✓  ...  ✓
                                ↑
                          failure rate = (count of ✗) / 100
```

Pros: O(1) per update, constant memory. Cons: at low traffic (e.g. 1 call/s,
window=100), the window represents 100 s of history, so a 60 s outage may take
a while to be reflected.

### Time-based window

A bucketed window that holds the last N seconds, split into sub-buckets (e.g.
Resilience4j uses `slidingWindowSize` *seconds*, with one bucket per second).
Each bucket aggregates `(successes, failures, slow_calls)`. On read, buckets
older than the window are dropped; the aggregated ratio is returned.

```
   t-5  t-4  t-3  t-2  t-1  t=now
   ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐
   │2✓│ │0✓│ │3✗│ │1✓│ │2✗│ │0✓│   ← partial buckets aggregated
   │0✗│ │1✗│ │1✓│ │3✗│ │0✓│ │1✗│
   └──┘ └──┘ └──┘ └──┘ └──┘ └──┘
        ↑
   window of last 6 s: 7 success / 10 failures → 58.8% failure rate
```

Pros: decisions are time-barrant — a 30 s window represents 30 s of recent
traffic regardless of rate. Cons: more allocations (buckets are created and
retired), and a bucket is rolled up only after it closes, so the most recent
sub-bucket may underreport.

> **Which to use?** Time-based is the safer default. Count-based is right when
> your traffic is steady enough that "last N calls" really means "last N
> seconds"; otherwise a slow period keeps stale data around for too long.

## Failure Rate Threshold

`failure_rate_threshold` is the ratio of failed calls to total calls above
which the breaker opens. Resilience4j defaults to `50%`. The right value is
sensitive to your traffic:

```
   window = 100 calls, threshold = 50%
   ────────────────────────────────────────
   traffic        time to detect 50 failures     minimum failures to trip
   1 RPS          50 s                            50
   100 RPS        0.5 s                           50
   10 000 RPS     5 ms                            50
```

At very low traffic, 50% of 100 calls = 50 failures, which takes 50 s at
1 RPS — far too long. Resilience4j addresses this with `minimum_number_of_calls`
(default 100) — the breaker won't open until at least that many calls have
been recorded. Tune both: set the threshold to your "real outage" rate
(typically 30–60%) and the minimum to a count you'd consider statistically
meaningful at your lowest realistic traffic.

## Slow Call Duration Threshold

A subtle but critical feature: not every failure is an exception. A call that
returns 200 OK after 30 s is functionally a failure when the caller's budget
is 1 s. Resilience4j (and Polly) track **slow call rate** separately:

- `slow_call_duration_threshold` — a call is "slow" if it takes longer than
  this (e.g. 2 s).
- `slow_call_rate_threshold` — if slow calls exceed this percentage of total
  calls (e.g. 70%), the breaker opens.

Hystrix took a simpler approach: a single timeout, and any call exceeding it
counted as a failure. The split allows finer control — you may want to open
on a *high* slow-call rate (the service is degraded) without opening on a
*moderate* error rate (a few requests are erroring but the bulk are fine).

## Wait Duration in Open State

`wait_duration_in_open_state` is the cooldown before HALF-OPEN is tried. Too
short and the breaker flaps: open → probe → fail → open → probe → …,
hammering the recovering downstream. Too long and you extend the outage
needlessly.

A good rule: set the wait to *your typical recovery time*, plus headroom.
Database failovers take 10–30 s; rolling deploys take 30–120 s; GC pauses
are 1–10 s. A 30 s wait is a reasonable default for most downstreams;
2–5 min for ones that need a deploy to recover.

The trap to avoid: **synchronized probes**. If every upstream instance's
breaker opens at t=0 and they all wait 30 s, they all probe at t=30, creating
a synchronized spike. Add jitter to the wait — Resilience4j doesn't do this by
default, so wire it manually: a per-instance random offset of ±10% on the
wait duration.

## Permitted Calls in Half-Open

`permitted_number_of_calls_in_half_open_state` (Resilience4j) or
`requestVolumeThreshold`'s half-open equivalent (Hystrix) controls how many
probes are allowed before a verdict is reached. Set too high and half-open
becomes a second CLOSED state; set too low (1) and a single transient failure
re-opens the breaker.

Resilience4j's `automatic_transition_from_half_open_to_open` flag matters
here: by default, when a probe fails, the breaker immediately re-opens and
the wait timer starts over. If false, the breaker stays half-open until all
permitted probes have been evaluated — useful when you want to *confirm*
recovery rather than react to one bad call.

The recommended configuration:

```
   permitted calls = 3 to 10
   transition      = automatic (re-open on first failure)
   verdict         = N consecutive successes to close
```

`N consecutive successes` is what Hystrix uses. Resilience4j by default
closes on a single successful probe; setting it higher (`wait_duration` plus
a higher `permitted_number_of_calls` with `automatic_transition=false`) makes
recovery more conservative.

## Implementations

### Resilience4j (Java, the de facto standard)

Resilience4j is the spiritual successor to Hystrix, written on top of Vavr
and functional interfaces. Configuration is fluent:

```java
CircuitBreakerConfig config = CircuitBreakerConfig.custom()
    .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.TIME_BASED)
    .slidingWindowSize(60)                      // 60 s window
    .minimumNumberOfCalls(20)                   // don't open before 20 calls
    .failureRateThreshold(50f)                  // 50% failure rate
    .slowCallRateThreshold(70f)                 // 70% slow calls open it
    .slowCallDurationThreshold(Duration.ofSeconds(2))
    .waitDurationInOpenState(Duration.ofSeconds(30))
    .permittedNumberOfCallsInHalfOpenState(5)
    .automaticTransitionFromOpenToHalfOpenEnabled(true)
    .recordException(ex -> ex instanceof java.io.IOException
                       || ex instanceof java.util.concurrent.TimeoutException)
    .ignoreException(ex -> ex instanceof IllegalArgumentException)
    .build();

CircuitBreaker breaker = CircuitBreaker.of("payments", config);

// Functional decoration: compose breaker + retry + bulkhead.
Supplier<PaymentResult> decorated = Decorators.ofSupplier(() -> payApi.charge(req))
    .withCircuitBreaker(breaker)
    .withRetry(retry)
    .withBulkhead(bulkhead)
    .decorate();
```

Key features beyond the basics:

- **Ignorable exceptions** — `ignoreException` lets 4xx client errors not
  count as failures (a 400 Bad Request is the caller's fault, not the
  downstream's).
- **Metrics** — auto-publishes to Micrometer: `resilience4j_circuit_breaker_state`,
  `resilience4j_circuit_breaker_calls_total{kind="successful|failed|not_permitted"}`,
  `resilience4j_circuit_breaker_failure_rate`.
- **Reactor/RxJava operators** — `CircuitBreakerOperator` integrates
  reactive streams so the breaker state respects `onNext`/`onError`.

### Netflix Hystrix (deprecated but canonical)

Hystrix is what made the pattern popular. It is in maintenance mode — Netflix
recommends migrating to Resilience4j or `concurrency-limits` — but the design
is worth understanding because the terminology stuck.

The Hystrix model is conceptually different in two ways:

1. **No time-based window, only count-based.** A 10 s bucket of N calls; if
   the failure rate exceeds `circuitBreaker.errorThresholdPercentage` (default
   50%) over the last bucket, open.
2. **Per-command thread pool by default.** Each `HystrixCommand` runs on its
   own thread pool (`HystrixThreadPool`), which doubles as a bulkhead. This
   is why Hystrix is called a "circuit breaker + bulkhead in one library."

```java
public class ChargeCommand extends HystrixCommand<PaymentResult> {
    private final ChargeRequest req;
    public ChargeCommand(ChargeRequest req) {
        super(Setter.withGroupKey(HystrixCommandGroupKey.Factory.asKey("Payments"))
            .andCommandPropertiesDefaults(HystrixCommandProperties.Setter()
                .withCircuitBreakerErrorThresholdPercentage(50)
                .withCircuitBreakerRequestVolumeThreshold(20)
                .withCircuitBreakerSleepWindowInMilliseconds(30000)
                .withExecutionTimeoutInMilliseconds(2000))
            .andThreadPoolPropertiesDefaults(HystrixThreadPoolProperties.Setter()
                .withCoreSize(10)
                .withMaxQueueSize(20)));
        this.req = req;
    }
    @Override protected PaymentResult run() { return payApi.charge(req); }
    @Override protected PaymentResult getFallback() { return PaymentResult.degraded(); }
}
```

Notable defaults:

- `circuitBreaker.requestVolumeThreshold` = 20 — won't open until 20 calls
  have been recorded in the bucket. (Resilience4j's equivalent is
  `minimumNumberOfCalls`.)
- `circuitBreaker.sleepWindowInMilliseconds` = 5000 — 5 s wait. Netflix's
  own services run with this lower because their downstreams are also
  self-recovering.
- The fallback chain is a first-class feature — when open, `getFallback()`
  runs instead of throwing. This makes degraded responses a property of the
  call site, not an error handler far away.

### Polly (.NET)

Polly is to .NET what Resilience4j is to Java: a fluent, composable
resilience library. The latest v8 introduced a "resilience pipeline"
abstraction over the older policy-based API:

```csharp
var circuitBreaker = new CircuitBreakerStrategyOptions<HttpResponseMessage>
{
    FailureRatio = 0.5,
    MinimumThroughput = 20,
    SamplingDuration = TimeSpan.FromSeconds(30),
    BreakDuration = TimeSpan.FromSeconds(30),
    MaximumOpenedCircuits = 2,
    ShouldHandle = new PredicateBuilder<HttpResponseMessage>()
        .Handle<HttpRequestException>()
        .HandleResult(r => r.StatusCode >= System.Net.HttpStatusCode.InternalServerError)
};

var pipeline = new ResiliencePipelineBuilder<HttpResponseMessage>()
    .AddRetry(new RetryStrategyOptions<HttpResponseMessage>
    {
        MaxRetryAttempts = 3,
        BackoffType = DelayBackoffType.Exponential,
        UseJitter = true
    })
    .AddCircuitBreaker(circuitBreaker)
    .AddTimeout(TimeSpan.FromSeconds(5))
    .Build();
```

Polly's `SamplingDuration` is the time-based window; `MinimumThroughput`
mirrors Resilience4j's `minimumNumberOf_calls`. The interesting design choice
is `ShouldHandle` — a predicate that decides which results count as failures,
allowing the breaker to ignore e.g. 404s on a `GET`.

### Comparison of implementations

```
   feature                          Hystrix      Resilience4j   Polly
   ──────────────────────────────────────────────────────────────────
   count-based window              yes          yes            yes
   time-based window               no           yes            yes
   slow-call threshold (separate)  no           yes            yes
   automatic half-open             yes          yes            yes
   integrated bulkhead (threads)   yes          optional       no
   integrated retry                no           no             yes
   metrics                         Hystrix CLI  Micrometer     .NET metrics
   reactive bindings               no           yes (Reactor)  yes (Rx)
   maintenance status              deprecated   active         active
```

## Comparison to Retries

The two patterns are not rivals — they're at different layers of the
defence-in-depth stack.

```
   ┌───────────────────────────────────────────────────────────┐
   │ Caller                                                   │
   │  ┌──────────────────────────────────────────────────┐     │
   │  │ Bulkhead  →  Circuit Breaker  →  Retry  →  RPC   │     │
   │  │  (limit       (fail fast if    (handle         (network
   │  │   concurrency) sustained outage) transient errs) call)│
   │  └──────────────────────────────────────────────────┘     │
   └───────────────────────────────────────────────────────────┘
```

- **Retry** handles **transient** failures (a dropped packet, a 503 during a
  deploy, a GC pause). It assumes the next attempt will probably succeed.
- **Circuit breaker** handles **sustained** failures. It assumes the next
  attempt will fail and short-circuits instead.
- **Bulkhead** handles **capacity** failures. It doesn't care whether the
  downstream is healthy — only that *this caller* is using too much of a
  shared resource.

Wiring them together: the breaker's `allow()` gates the *first* attempt;
`record()` updates state on every outcome. Retries happen *inside* the
breaker-protected scope so the breaker sees both the original attempt and
the retries. If the breaker is open, **do not retry** — that's the whole
point of the open state.

```python
def call_with_resilience(self, req):
    if not self.breaker.allow():
        raise CircuitOpen("fail fast")
    try:
        return self.retry_policy.run(lambda: self.downstream.call(req))
    except Exception as e:
        self.breaker.record(False)
        raise
    else:
        self.breaker.record(True)
```

A common mistake: putting the retry *outside* the breaker. Then a slow
downstream sees 3 retries per request, each adding to the breaker's window —
the retry itself contributes to opening the breaker, and the breaker's open
state doesn't suppress retries, only the first attempt. The order matters:
breaker → retry → call.

## Common Pitfalls

1. **Counting 4xx as failures.** A 400 Bad Request is the caller's mistake;
   treating it as a failure will eventually trip the breaker against a
   perfectly healthy downstream.
2. **Ignoring slow calls.** A 30 s 200-OK is worse than a fast 500 — it holds
   resources. Use `slow_call_duration_threshold` aggressively.
3. **Synchronized half-open probes.** All instances open at the same time,
   all wait 30 s, all probe at the same moment → a synchronized spike on the
   recovering downstream. Add jitter to the wait.
4. **No fallback.** An open breaker without a fallback is just an outage
   with extra steps. Wire a degraded response so the user gets *something*.
5. **Threshold tuned for the wrong traffic.** Defaults from Resilience4j
   (`windowSize=100`, `minCalls=100`) are fine at 1000+ RPS and lethal at
   0.1 RPS. Set `minimumNumberOfCalls` to a number you actually see within
   your expected outage window.

## Interview Questions

### Q: Why does a circuit breaker need a half-open state at all? Why not
just try the call after the wait elapses?

If every breaker that opened at t=0 closes at t=30, every instance probes the
downstream simultaneously at t=30+ε. For a downstream that just recovered,
this is a synchronized traffic spike that may knock it back over. The
half-open state with a small number of permitted probes gates recovery: only
a handful of calls are tried, and a single failure re-opens the breaker
without committing the rest of the caller's traffic. It's a form of admission
control on the path to recovery.

### Q: When would you choose a count-based window over a time-based one?

When your traffic is high and steady enough that "last N calls" is also "last
N seconds" — e.g. a hot path at thousands of RPS. Count-based is cheaper
(O(1) updates, no bucket allocation) and never has stale-bucket issues. At
low or bursty traffic, "last 100 calls" might span minutes; time-based gives
a consistent staleness ceiling regardless of rate.

### Q: How do you stop a circuit breaker from oscillating (flapping) between
OPEN and HALF-OPEN?

Three knobs: (1) increase `wait_duration_in_open_state` so a downstream has
time to actually recover before being probed; (2) require multiple
consecutive successful probes before closing (Resilience4j: set
`permitted_number_of_calls_in_half_open_state` to N and use
`automatic_transition_from_half_open_to_open=false` so a single failure
doesn't immediately re-open); (3) add jitter to the wait so instances don't
probe in lockstep.

## References

- Michael T. Nygard, *Release It!: Design and Deploy Production-Ready
  Software* (Pragmatic Bookshelf, 2nd ed. 2018), Chapter 5 "Stability
  Patterns" — the original and most thorough treatment of the pattern.
  https://pragprog.com/titles/mnee2/release-it-second-edition/
- Martin Fowler, *CircuitBreaker* (bliki entry, 2014) — the canonical
  high-level description.
  https://martinfowler.com/bliki/CircuitBreaker.html
- Resilience4j documentation: *Circuit Breaker* — every knob discussed here
  is documented with defaults.
  https://resilience4j.readme.io/docs/circuitbreaker
- Netflix Hystrix Wiki: *How it Works* — the state machine, request volume
  threshold, and sleep window.
  https://github.com/Netflix/Hystrix/wiki/How-it-Works
- Netflix Hystrix Wiki: *Configuration* — full list of properties and
  defaults, useful for translating Hystrix knowledge to Resilience4j.
  https://github.com/Netflix/Hystrix/wiki/Configuration
- Polly v8 documentation: *Circuit Breaker* — the .NET resilience pipeline
  API and its `ShouldHandle` predicate.
  https://www.pollydocs.org/strategies/circuit-breaker.html
- Google SRE Workbook, Chapter 22: *Addressing Cascading Failures* —
  discusses circuit breakers as one of the failure-shedding mechanisms.
  https://sre.google/sre-book/addressing-cascading-failures/

## Related Topics

- [Retry and Timeout Patterns](./retry-timeout.md) — the smaller sibling; this
  page extends that one's circuit-breaker sketch into a full deep dive.
- [Bulkhead Deep Dive](./bulkhead-deep.md) — the resource-isolation pair to
  the circuit breaker; together they form the standard resilience stack.
- [Graceful Degradation](./graceful-degradation.md) — what to return when the
  breaker is open.
- [Health Check Patterns](./health-check-patterns.md) — the probes a
  downstream exposes that inform the breaker's decisions.
- [Idempotency](./idempotency.md) — required for safe retries *inside* a
  breaker-protected call site.
