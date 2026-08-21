# Bulkhead Pattern Deep Dive

## Overview

A bulkhead isolates resources so that a failure in one part of the system
cannot consume the resources needed by another. The name is from shipbuilding:
a vessel is partitioned into watertight compartments separated by steel walls
(bulkheads); if the hull is breached below the waterline in one compartment,
the others stay dry and the ship floats. Michael Nygard's *Release It!*
borrowed the metaphor for software in 2007, and the term has stuck.

In a service, the "water" is contention — for threads, for connections, for
memory, for CPU. The "bulkheads" are quotas: a thread pool that one
dependency cannot outgrow, a connection pool sized for one caller's budget,
a semaphore that caps in-flight work. The pattern answers one question: *if
this dependency misbehaves, how much of me can it take down?*

A bulkhead is *not* a circuit breaker. A circuit breaker stops calling a
failing service; a bulkhead stops one dependency from taking more than its
share of *your* resources when it is slow or being hammered. The two patterns
are complementary and almost always deployed together.

## The Problem: Resource Exhaustion Cascades

The canonical bulkhead scenario is the slow-dependency cascade. Your service
calls three downstreams: `payments`, `inventory`, and `recommendations`.
Traffic is 1000 RPS. Each downstream normally responds in 50 ms, so the
service's thread pool of 200 threads handles it comfortably.

Now `recommendations` degrades to 5 s per call. Without isolation, every
call to your service that hits `recommendations` holds a thread for 5 s.
Within a second, 200 threads are blocked. The next request arrives, the
pool is empty, the request waits in the accept queue. Within 30 s, the
service has timed out on every request — including requests that never
touched `recommendations`. `payments` calls are failing not because
`payments` is broken, but because there are no threads to serve them.

```
   Without bulkheads                  With bulkheads
   ─────────────────────────────      ──────────────────────────────
   Shared pool (200 threads)          Pool-pay   (50 threads)
                                      Pool-inv    (50 threads)
   recommendations degrades           Pool-rec    (50 threads)
   → 200 threads consumed             → only Pool-rec exhausted
   → all requests time out             → payments, inventory unaffected
```

The fix is to give each downstream a quota: only 50 threads can call
`recommendations` at once. When those 50 are busy, the 51st call fails fast
(returns a fallback, gets a 503) instead of blocking. The rest of the
service — `payments`, `inventory`, even unrelated code paths — keeps
running.

## Three Implementations

### Thread Pool Bulkhead

A dedicated thread pool per dependency. Calls to the dependency are submitted
to the pool; if all threads are busy, the call is queued (up to a bound) or
rejected.

Resilience4j's `ThreadPoolBulkhead`:

```java
ThreadPoolBulkheadConfig config = ThreadPoolBulkheadConfig.custom()
    .maxThreadPoolSize(50)
    .coreThreadPoolSize(10)
    .queueCapacity(20)
    .keepAliveDuration(Duration.ofSeconds(20))
    .build();

ThreadPoolBulkhead recBulkhead = ThreadPoolBulkhead.of("recommendations", config);

// Submit returns a CompletableFuture; the call runs on the bulkhead's pool.
CompletableFuture<Recommendations> f = recBulkhead.submit(() -> recApi.get(req));

CompletableFuture<Recommendations> withFallback = f.exceptionally(e -> {
    // Bulkhead full → BulkheadFullException → fall back to cached recs.
    return cache.get(req.userId);
});
```

The configuration has four knobs that interact:

| Property              | Default | What it bounds                              |
| --------------------- | ------- | ------------------------------------------- |
| `coreThreadPoolSize`  | 10      | Threads kept alive when idle                |
| `maxThreadPoolSize`   | 10      | Hard cap on threads                         |
| `queueCapacity`       | 100     | Tasks waiting for a thread                  |
| `keepAliveDuration`   | 60 s    | Idle excess-core threads live this long     |

The **effective max concurrency** is `maxThreadPoolSize + queueCapacity` —
calls beyond that are rejected with `BulkheadFullException`. Two extreme
mistakes:

- `queueCapacity = Integer.MAX_VALUE` — an *unbounded* queue means the
  bulkhead never rejects, but tasks pile up in memory and call latency
  explodes. A bulkhead that never trips is not a bulkhead.
- `queueCapacity = 0` — no queue at all, so a perfectly healthy dependency
  rejects whenever all threads are momentarily busy. Too aggressive.

A common heuristic: `queueCapacity ≈ maxThreadPoolSize`, so a downstream
spike has one round of buffering before rejections kick in.

### Semaphore Bulkhead

A `java.util.concurrent.Semaphore` (or equivalent) that caps concurrent
in-flight calls without spinning up dedicated threads. The caller's own
thread is the one that enters the semaphore, calls the downstream, and
releases on return.

```java
BulkheadConfig config = BulkheadConfig.custom()
    .maxConcurrentCalls(50)
    .maxWaitDuration(Duration.ofMillis(0))   // fail fast, no waiting
    .build();

Bulkhead recBulkhead = Bulkhead.of("recommendations", config);

Supplier<Recommendations> decorated = Bulkhead.decorateSupplier(
    recBulkhead, () -> recApi.get(req));
Recommendations result = decorated.get();
```

In Python (asyncio variant):

```python
import asyncio

class SemaphoreBulkhead:
    def __init__(self, name: str, max_concurrent: int, max_wait: float = 0.0):
        self.name = name
        self.sem = asyncio.Semaphore(max_concurrent)
        self.max_wait = max_wait

    async def __aenter__(self):
        try:
            await asyncio.wait_for(self.sem.acquire(), timeout=self.max_wait)
        except asyncio.TimeoutError:
            raise BulkheadFull(self.name)
        return self

    async def __aexit__(self, *exc):
        self.sem.release()

# usage
rec_bulkhead = SemaphoreBulkhead("recommendations", max_concurrent=50)

async def get_recommendations(user_id):
    async with rec_bulkhead:
        return await rec_client.fetch(user_id)
```

The semaphore version is **cheaper** than the thread pool version (no extra
threads, no context switches, no separate queue) and **fits the reactive
model** because it doesn't impose a threading model on the caller. The
trade-off: it cannot bound *blocking* calls cleanly — a caller that blocks
on a JDBC call while holding a semaphore slot is still a blocked OS thread,
just one that's now also gated by a permit.

> **Rule of thumb.** Use a thread-pool bulkhead when the downstream is a
> blocking API (synchronous I/O, JDBC, a third-party SDK you can't change).
> Use a semaphore bulkhead when the downstream is already async (HTTP/2,
> reactive, NIO) — the goal is admission control, not thread isolation.

### Connection Pool Bulkhead

The lowest layer: a database or HTTP client connection pool sized per
*consumer*, not per service. A single Postgres pool of 100 connections
shared between `payments` and `analytics` means a bad `analytics` query
can starve `payments`. The fix:

```
   Total DB pool: 100 connections
   ├── payments service:  40 connections  ← critical, gets the headroom
   ├── orders service:   30 connections
   ├── users service:     20 connections
   └── analytics service: 10 connections  ← non-critical, smallest pool
```

If `analytics` runs a pathological 60 s join, only 10 connections are tied
up — `payments` still has its 40. The pool itself (`HikariCP`, `pgxpool`,
`asyncpg`) provides the bulkhead; the application just has to size each
caller's slice and never share across consumer boundaries.

A common mistake: using one HTTP client instance with one connection pool
across the whole service. Each downstream should have its own client with
its own pool, sized to that downstream's expected traffic.

## Max Concurrent Calls vs Queue Length

The two parameters of a semaphore/thread-pool bulkhead are easy to confuse:

- **`maxConcurrentCalls`** (in-flight work) — how many calls to the downstream
  are *actively being made* at one time. This bounds the resources you
  consume on the downstream.
- **Queue length** (waiting work) — how many *additional* calls can sit
  buffered waiting for a slot. This bounds the latency your *callers* see
  before being rejected.

```
   maxConcurrentCalls = 50, queueCapacity = 20

   ┌─────────────────────┐
   │  in-flight (≤50)    │ ← actual concurrent work on the downstream
   ├─────────────────────┤
   │  queued (≤20)       │ ← callers waiting, will run when a slot frees
   ├─────────────────────┤
   │  rejected (rest)    │ ← callers beyond capacity: get BulkheadFull
   └─────────────────────┘
```

The math: total admitted work = `maxConcurrentCalls + queueCapacity`. Total
*rejected* work = everything else. A call that enters the queue waits up to
`maxWaitDuration`; if no slot opens up in that window, it's rejected.

The deeper insight: **queue length is a latency trade-off against failure
rate**. A long queue means callers wait longer before failing — useful when
downstream recovery is fast and you'd rather delay than reject. A short
queue means callers fail fast — correct when the downstream is unrecoverable
and waiting only adds latency cost to a failure.

## Fallback When Full

A bulkhead rejection is *not* a fatal error. It is a signal that you've
chosen to degrade *this* caller rather than cascade. The fallback strategy
matters:

| Fallback                 | When to use                                          |
| ------------------------ | --------------------------------------------------- |
| Cached/stale response    | Read paths where stale data is acceptable           |
| Default value            | Optional fields (recommendations, thumbnails)       |
| Asynchronous retry-queue | Mutating operations that can be retried later        |
| HTTP 503 + Retry-After   | Public API; let the client decide                   |
| HTTP 202 + job id        | Async accept; the work happens later                |

The pattern is the same as the circuit breaker's fallback — and the two are
usually composed. A `BulkheadFullException` from the bulkhead can be caught
at the same boundary as a `CircuitBreakerOpenError`; both trigger the same
degraded response.

```python
async def get_recommendations(user_id):
    try:
        async with rec_bulkhead:
            return await rec_client.fetch(user_id)
    except BulkheadFull:
        # Bulkhead full — return cached recs and let the caller continue.
        metrics.incr("rec.bulkhead_rejected")
        return await cache.get_recommendations(user_id)
```

The fallback must be **cheaper than the original call** — if your fallback
also calls a downstream that's slow, you've moved the problem, not solved it.

## Comparison to Circuit Breaker

The two patterns are paired, but they answer different questions:

```
   ┌───────────────────────┬──────────────────────────────────────────┐
   │ Pattern               │ Question it answers                     │
   ├───────────────────────┼──────────────────────────────────────────┤
   │ Bulkhead              │ "How much of MY resources can this      │
   │                       │  downstream consume before I cut it off?"│
   ├───────────────────────┼──────────────────────────────────────────┤
   │ Circuit breaker       │ "Should I call this downstream at all,   │
   │                       │  given its recent failure rate?"        │
   └───────────────────────┴──────────────────────────────────────────┘
```

| Aspect                | Bulkhead                            | Circuit breaker                   |
| --------------------- | ----------------------------------- | --------------------------------- |
| Limits                | Concurrency                         | Failure propagation               |
| Mechanism             | Resource partitioning               | State machine (closed/open/half)  |
| Active when           | Always                              | Only when failures are sustained  |
| Recovery              | Instant (slot frees on return)      | Gradual (half-open probes)        |
| Protects against      | Resource exhaustion                 | Cascading failure                 |
| Failure signal        | Capacity exceeded                   | Error rate exceeded               |

They compose:

```
   request ──▶ Bulkhead (admission) ──▶ Circuit breaker ──▶ Downstream
                  │                       │
                  ▼ full                  ▼ open
               fallback               fallback
```

The bulkhead gates the call: only N concurrent calls enter. The circuit
breaker decides whether to forward each admitted call or fail fast. If the
breaker is open, the bulkhead slot is released immediately (no downstream
call) — which means an open breaker doesn't consume bulkhead capacity.

> **Subtlety.** Without a bulkhead, an open breaker still protects you
> against the downstream, but not against your *callers* — your service may
> still be overrun with requests that all hit the open breaker and return a
> fallback. The bulkhead caps how much work your service will accept on
> behalf of *this* dependency.

## The Netflix (Hystrix) Bulkhead

Hystrix is the historical reference point because it bundled bulkheading
into the breaker itself. Each `HystrixCommand` is bound to a
`HystrixCommandGroupKey` and (optionally) a `HystrixThreadPoolKey`. The
thread pool key partitions commands onto separate `HystrixThreadPool`
instances; each pool has its own queue and rejection logic.

```java
public class ChargeCommand extends HystrixCommand<PaymentResult> {
    public ChargeCommand(ChargeRequest req) {
        super(Setter.withGroupKey(HystrixCommandGroupKey.Factory.asKey("Payments"))
            .andThreadPoolKey(HystrixThreadPoolKey.Factory.asKey("Payments-Pool"))
            .andThreadPoolPropertiesDefaults(HystrixThreadPoolProperties.Setter()
                .withCoreSize(20)
                .withMaxQueueSize(20)
                .withQueueSizeRejectionThreshold(15)));
        // ...
    }
    @Override protected PaymentResult run() { return payApi.charge(req); }
    @Override protected PaymentResult getFallback() { return PaymentResult.degraded(); }
}
```

A few Hystrix-specific quirks worth knowing:

- `withMaxQueueSize` vs `withQueueSizeRejectionThreshold` — the queue is
  a `LinkedBlockingQueue` with a hard cap (`maxQueueSize`), but the rejection
  threshold is a *soft* cap you can change at runtime. Netflix used this to
  tune pool sizes without redeploying.
- The default pool size was 10 threads, which was almost always wrong —
  Netflix's own wiki recommends sizing from `peak_qps × p99_latency_seconds`.
- Because the command runs on a separate thread, the caller thread is
  protected from the downstream's latency. But this also means request-scoped
  context (`ThreadLocal`, MDC, security context) doesn't propagate by
  default — you have to install a `HystrixConcurrencyStrategy` to copy it.

The thread-isolation model is what made Hystrix famous and what got it
deprecated: thread pools per command are expensive (each is a long-lived
`ExecutorService` with its own monitoring) and the context-propagation
plumbing was fiddly. Resilience4j dropped the integrated bulkhead in favour
of separate, optional `Bulkhead` and `ThreadPoolBulkhead` modules.

## The Reactive Bulkhead (Project Reactor)

Reactor is a non-blocking runtime — there's no thread-per-request model.
Bulkheading here is about *reactive concurrency*, not threads. Two operators
matter:

- `.transformDeferred(BulkheadOperator.of(bulkhead))` — gates each
  `subscribe()` against a `Bulkhead` instance; rejected calls become
  `onError(BulkheadFullException)`.
- `.publishOn(scheduler)` with a bounded `Schedulers.newBoundedElastic(...)`
  — bounds both threads and queued tasks.

```java
Bulkhead bulkhead = Bulkhead.of("recommendations",
    BulkheadConfig.custom().maxConcurrentCalls(50).build());

Mono<Recommendations> recs = Mono.fromCallable(() -> recApi.get(req))
    .transformDeferred(BulkheadOperator.of(bulkhead))
    .timeout(Duration.ofSeconds(2))
    .onErrorResume(e -> Mono.fromCallable(() -> cache.get(req.userId)));
```

A subtler reactive pattern: **`.flatMap` with concurrency**.

```java
Flux<UserId> ids = ...;
Flux<Recommendations> recs = ids.flatMap(
    id -> getRecommendations(id),
    256   // concurrency = 256, equivalent to a per-subscriber bulkhead
);
```

The second argument to `flatMap` is the concurrency limit — the maximum
number of in-flight inner `Mono`s. This is the *reactive* form of a
semaphore: 256 concurrent downstream calls; the 257th waits until one
completes. Tuning this number is tuning a bulkhead.

> **Caution.** `Schedulers.newBoundedElastic` has a default queue cap of
> **unbounded** — it will happily queue millions of tasks and OOM your
> process. Always pass a cap: `Schedulers.newBoundedElastic(20, 1000, "x")`.

## Sizing

The starting point is Little's Law, `L = λ · W`: the average in-flight
requests equal the arrival rate × the average latency. A downstream at
1000 RPS with 100 ms latency has steady-state concurrency `L = 100`. Size
the bulkhead to `L × safety_factor` (1.5–3×), and substitute p99 latency
for p50 when sizing against tail load — the p99 of a log-normal distribution
can be 5–10× the p50, so be generous.

```
   peak_qps              = 1000
   p99_latency           = 0.5 s
   safety_factor         = 2.0
   ─────────────────────────────────
   bulkhead_size         = 1000 × 0.5 × 2.0 = 1000 concurrent calls
```

Cross-check against available resources: 1000 concurrent calls × 50 KB
per in-flight context = 50 MB of memory; 1000 × 1 DB connection is almost
certainly a misconfiguration.

## Common Pitfalls

1. **Shared bulkhead across tenants.** One noisy tenant fills the bulkhead;
   every other tenant gets `BulkheadFull`. The fix is per-tenant bulkheads
   with per-tier quotas.
2. **Unbounded queues.** A `LinkedBlockingQueue` with no cap can hide the
   rejection signal until OOM. Always pass a capacity to the constructor.
3. **The fallback is more expensive than the call.** A bulkhead rejection
   that triggers a downstream call to a *different* service just moves the
   contention.
4. **Forgetting to release permits on exception paths.** A semaphore that
   isn't released in a `finally` block leaks permits until the bulkhead is
   permanently full. Always pair `acquire()` with `try/finally release()`.
5. **Sharing one connection pool across downstreams.** Even with a circuit
   breaker per downstream, a shared pool means a slow `recommendations`
   exhausts the connections `payments` needs.

## Interview Questions

### Q: When would you use a thread-pool bulkhead versus a semaphore bulkhead?

Thread pool: when the downstream call is blocking (JDBC, synchronous HTTP,
a third-party SDK you can't rewrite). The thread pool isolates the
caller's threads from the downstream's latency — a slow call blocks a
bulkhead thread, not a caller thread. Semaphore: when the downstream is
already non-blocking (reactive HTTP, NIO, gRPC async stubs). The goal is
admission control rather than thread isolation; a semaphore is cheaper
and composes naturally with reactive code.

### Q: How would you implement a per-tenant bulkhead in a multi-tenant API?

Maintain a registry of bulkheads keyed by tenant ID, with a fallback for
unknown or oversized registries (e.g., an LRU eviction policy). Configure
each tenant's bulkhead from their tier's quota: `free: 5`, `pro: 50`,
`enterprise: 200`. On a cache miss, lazily create a bulkhead from the
tenant's tier. The trap: an unbounded registry is a memory leak — pair it
with an eviction policy that closes bulkheads idle for more than N minutes.

### Q: What metrics should you monitor for a bulkhead?

- `bulkhead_active_calls` (gauge) — how many permits are currently held.
- `bulkhead_available_calls` (gauge) — `max_concurrent - active`; alert when
  this drops below 20% of `max_concurrent`.
- `bulkhead_rejected_total` (counter) — increment on each
  `BulkheadFullException`. Alert on any sustained rejection rate.
- `bulkhead_queue_wait_seconds` (histogram) — time spent in the queue before
  acquiring a permit. p99 above 100 ms suggests the bulkhead is undersized
  for steady-state traffic.
- `bulkhead_state` (gauge, 0/1) — whether the bulkhead is currently full.
  Plot alongside circuit-breaker state; if both are pegged, the downstream
  is both failing *and* saturated.

## References

- Michael T. Nygard, *Release It!: Design and Deploy Production-Ready
  Software* (Pragmatic Bookshelf, 2nd ed. 2018), Chapter 5 "Stability
  Patterns" — the *Bulkheads* section introduces the metaphor and the
  resource-isolation argument.
  https://pragprog.com/titles/mnee2/release-it-second-edition/
- Netflix Hystrix Wiki: *How it Works* — the section on "Dependency
  Isolation" describes the per-command thread pool, the queue, and the
  fallback semantics.
  https://github.com/Netflix/Hystrix/wiki/How-it-Works
- Netflix Hystrix Wiki: *Configuration* — the full list of
  `hystrix.threadpool.*` properties with defaults.
  https://github.com/Netflix/Hystrix/wiki/Configuration
- Resilience4j documentation: *Bulkhead* — both `Bulkhead` (semaphore)
  and `ThreadPoolBulkhead` APIs, including the configuration knobs
  (`maxThreadPoolSize`, `coreThreadPoolSize`, `queueCapacity`) and the
  Reactor integration via `BulkheadOperator`.
  https://resilience4j.readme.io/docs/bulkhead
- Resilience4j source: `resilience4j-bulkhead` module on GitHub — the
  reference implementation of both the semaphore and thread-pool variants,
  useful for reading the exact rejection semantics.
  https://github.com/resilience4j/resilience4j/tree/master/resilience4j-bulkhead
- Project Reactor reference: *Choosing an Operator — flatMap* — describes
  the concurrency parameter and its relationship to parallelism and
  backpressure.
  https://projectreactor.io/docs/core/release/reference/
- Project Reactor documentation: *Schedulers* — the bounded-elastic
  scheduler, its default queue, and the queue-cap parameter that turns it
  into a de-facto bulkhead.
  https://projectreactor.io/docs/core/release/reference/#schedulers

## Related Topics

- [Circuit Breaker Deep Dive](./circuit-breaker-deep.md) — the failure-side
  counterpart; this page covers the capacity side.
- [Retry and Timeout Patterns](./retry-timeout.md) — the smaller sibling
  in the resilience stack.
- [Graceful Degradation](./graceful-degradation.md) — what the fallback
  branch of a bulkhead actually returns.
- [Backpressure Pattern](./backpressure-pattern.md) — the reactive equivalent
  of bulkheading, where the producer rather than the consumer is throttled.
- [Connection Pools](../api/connection-pools.md) — the lowest-layer
  bulkhead; sizing a database pool is sizing a bulkhead.
