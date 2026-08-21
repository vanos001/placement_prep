# Retry and Timeout Patterns

## Overview

In a distributed system, the network is unreliable, peers are slow, and processes restart. Three primitives — **timeouts**, **retries**, and **circuit breakers** — are the first line of defense against unbounded latency and partial failures. But each is a loaded weapon: a naive retry loop multiplies load during an outage, a missing timeout turns a slow dependency into a thread-pool exhaustion, and a circuit breaker wired to the wrong signal can trap a service in a permanent "open" state.

This page covers the mechanics that make these primitives safe: **deadline propagation**, **exponential backoff with jitter**, **retry budgets**, **the retry-storm / thundering-herd problem**, and **timeout hierarchies**.

## Why Timeouts Are Non-Negotiable

Without a timeout, a call to a slow dependency holds a thread, a connection, and a request-scoped resource forever. The standard story for cascading failure is:

```
1 client call → 1 thread blocked on DB
DB slows to 5s per query
Traffic at 1000 RPS → 5000 blocked threads in 5s
Thread pool exhausted → service stops accepting requests
Upstream service's calls to *us* also time out → recursion
Whole stack falls over
```

A timeout breaks the chain. The single rule that prevents most outages: **every synchronous call crosses a network boundary with a deadline**. No exceptions.

## The Timeout Hierarchy (Deadline Propagation)

A timeout set on the *outermost* operation must be respected at every layer below it; otherwise, an inner call can outlive the outer one and burn resources for a request the client has already given up on. This is **deadline propagation**.

```
Client RPC deadline: 1000ms
  └─ Service A handler budget: 900ms (100ms used for parsing/auth)
       ├─ DB query:        300ms
       ├─ Service B RPC:   400ms
       └─ Cache write:     100ms
```

If Service A calls Service B with a fresh 400ms timeout *ignoring* how much of the 900ms has already elapsed, then a 500ms DB read followed by a 400ms Service B call totals 900ms — exactly at budget — but the inner calls were not coordinated. The fix: derive the inner timeout from the **remaining** deadline.

gRPC exposes this directly via `context.WithTimeout` / `context.WithDeadline`. The deadline travels with the request metadata on the wire (`grpc-timeout` header); a downstream server sees the remaining time and rejects calls that would exceed it.

```python
import time, grpc
from grpc import aio

# Client: stamp a deadline on the call.
async def call_billing(stub, request):
    # Total budget for the entire request is 800ms.
    deadline = time.time() + 0.8
    return await stub.Charge(
        request,
        timeout=0.8,                 # RPC-level timeout
        metadata=(("grpc-timeout", f"{int(0.8 * 1_000_000_000)}n"),),
    )

# Server: derive per-call timeouts from the *remaining* deadline.
async def handle_charge(self, request, context):
    remaining = max(0.0, time.time() - context.time_remaining())
    if remaining < 0.05:
        await context.abort(grpc.StatusCode.DEADLINE_EXCEEDED,
                            "not enough time to serve")
    # Hand the DB a slice of the remaining budget.
    db_timeout = min(0.200, remaining * 0.4)
    row = await db.fetch_one(SQL, timeout=db_timeout)
    ...
```

The principle: **a single deadline lives at the edge; every layer below it consumes a slice, never more**.

## Backoff: Why Linear Retries Are Dangerous

If every client retries on failure after a fixed 100ms, a service that drops to 50% success rate sees:

- **Attempt 1**: 1000 RPS → 500 fail
- **Attempt 2** (100ms later): 500 retries → 250 fail
- **Attempt 3**: 250 retries → 125 fail
- **…**

The upstream service receives a sawtooth load that is synchronized across clients. Worse, if it was *recovering*, the synchronized retry spike knocks it back down — this is the **thundering herd** problem.

**Exponential backoff** removes the sawtooth: wait `base * 2^attempt` between tries. But pure exponential backoff still has clients synchronized at the same exponential marks, and it caps out at some maximum that may be too long for the user.

## Jitter: Decorrelated Jitter Wins

Jitter randomizes backoff so clients desynchronize. The AWS Architecture Blog identifies several jitter strategies; **decorrelated jitter** is the recommended one because it has provably bounded expected load and a desirable "sleep" distribution under contention.

```python
import random

# Equal jitter: half the exponential value + half random.
def equal_jitter_sleep(attempt: int, base: float, cap: float) -> float:
    expo = min(cap, base * (2 ** attempt))
    return expo / 2 + random.uniform(0, expo / 2)

# Decorrelated jitter (AWS recommended): sleep is uniform in
# [base, last_sleep * 3], capped. Gives a light-tailed distribution
# whose expectation converges rather than compounds.
def decorrelated_jitter(attempt: int, base: float, cap: float,
                        prev: float) -> float:
    nxt = min(cap, random.uniform(base, prev * 3))
    return nxt  # caller must remember `nxt` for next iteration
```

The decorrelated variant uses the *previous* sleep as the seed for the next one — that's the "decorrelated" part — which breaks the geometric coupling between attempt index and delay that equal jitter still has.

### Full retry loop with deadline

```python
import time, random
from typing import Callable, Optional

class DeadlineExceeded(Exception):
    pass

def retry_with_jitter(
    fn: Callable[[], bool],          # returns True on success
    *,
    base: float = 0.025,            # 25ms initial backoff
    cap: float = 1.0,               # never wait more than 1s
    max_attempts: int = 5,
    deadline: float = 2.0,          # absolute budget in seconds
    retryable: Callable[[Exception], bool] = lambda e: True,
) -> None:
    start = time.monotonic()
    sleep_prev = base
    for attempt in range(max_attempts):
        try:
            if fn():
                return
        except Exception as e:
            if not retryable(e):
                raise
            if time.monotonic() - start > deadline:
                raise DeadlineExceeded() from e
        # decorrelated jitter
        sleep_prev = min(cap, random.uniform(base, sleep_prev * 3))
        if time.monotonic() + sleep_prev - start > deadline:
            raise DeadlineExceeded()
        time.sleep(sleep_prev)
    raise DeadlineExceeded()
```

## Retry Budgets

Even with jitter, retries multiply load. If a service normally handles 1000 RPS and 5% of calls fail with a 5-attempt retry policy, the steady-state load on a downstream is `1000 * (1 - 0.95^5) / 0.05 ≈ 1051 RPS` — a ~5% overhead. During a partial outage, however, 50% failure drives retries to ~1690 RPS, a **69% overhead** that pushes the failing service deeper into failure.

A **retry budget** caps this multiplier. The Google SRE formulation: keep a token bucket where successful calls add 1 token (up to a cap, often 10% of the request rate) and each retry consumes 1 token. When the bucket is empty, **do not retry** — fail fast.

```python
import threading, time

class RetryBudget:
    """Token bucket: refills at ~10% of the observed success rate."""
    def __init__(self, refill_ratio: float = 0.1, max_tokens: int = 100):
        self.refill_ratio = refill_ratio
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.success_window = []   # rolling window of (ts, ok)
        self.lock = threading.Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - 60.0
        self.success_window = [e for e in self.success_window if e[0] >= cutoff]

    def record(self, ok: bool) -> None:
        now = time.time()
        with self.lock:
            self.success_window.append((now, ok))
            self._prune(now)
            if ok:
                self.tokens = min(self.max_tokens, self.tokens + 1)

    def can_retry(self) -> bool:
        now = time.time()
        with self.lock:
            self._prune(now)
            if self.tokens > 0:
                self.tokens -= 1
                return True
            return False
```

The bucket ties retries to the recent *success* rate — when the service is healthy, the bucket is full and retries are cheap; when it's failing, the bucket drains and retries are throttled to the configured percentage.

## The Retry Storm (a.k.a. Thundering Herd)

When Service A retries Service B, and Service B also retries Service C, a single end-user request can fan out into dozens of internal calls. The classic paper-cut:

```
User → A (retry 3x) → B (retry 3x) → C (retry 3x)
1 user call = up to 3 × 3 × 3 = 27 internal calls to C
```

If C is the database, 27x load on a struggling DB is a kill shot. Three defenses:

1. **Retry only at the boundary closest to the failure.** If A calls B and B is failing, B should retry its own downstream; A should *not* retry B unless A has reason to believe the failure was transient. The Google SRE book calls this the "**retry only once or at the highest layer**" rule.
2. **Use retry budgets everywhere.** Each layer throttles its own retries to a fixed percentage of successes.
3. **Combine retries with a circuit breaker.** If B has been failing for 30 seconds, stop retrying entirely; let the breaker trip and short-circuit.

## Circuit Breaker Integration

A circuit breaker watches a sliding window of call outcomes and trips into the **open** state when failures exceed a threshold. While open, calls fail immediately without consuming a downstream resource. After a *cooldown*, it transitions to **half-open**: a small number of probe calls are allowed through; if they succeed, the breaker **closes** again.

```
       ┌──────────────┐   failure rate > threshold   ┌──────────────┐
       │   CLOSED     │ ───────────────────────────▶ │    OPEN       │
       │ (normal call) │                                │ (fail fast)  │
       └──────────────┘ ◀─────────────────────────── └──────────────┘
                                probes succeed
                                       │  cooldown elapsed
                                       ▼
                                ┌──────────────┐
                                │  HALF-OPEN   │
                                │ (probe calls)│
                                └──────────────┘
```

This is the bridge between retries and degradation:

- Retries handle **transient** failures (a packet dropped, a GC pause).
- The circuit breaker handles **sustained** failures (a downstream is down).
- Together they make the **same call site** adaptive: burst errors get retried, sustained outages fail fast and degrade.

A minimal implementation:

```python
import time, threading
from collections import deque

class CircuitBreaker:
    def __init__(self, failure_threshold=10, cooldown=30.0,
                 window=60.0, half_open_max=3):
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self.window = window
        self.half_open_max = half_open_max
        self.events = deque()       # (ts, ok)
        self.state = "closed"
        self.opened_at = 0.0
        self.half_open_count = 0
        self.lock = threading.Lock()

    def _prune(self, now):
        cutoff = now - self.window
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def allow(self):
        now = time.time()
        with self.lock:
            self._prune(now)
            if self.state == "open":
                if now - self.opened_at >= self.cooldown:
                    self.state = "half-open"
                    self.half_open_count = 0
                else:
                    return False
            if self.state == "half-open":
                if self.half_open_count >= self.half_open_max:
                    return False
                self.half_open_count += 1
            return True

    def record(self, ok):
        now = time.time()
        with self.lock:
            self.events.append((now, ok))
            self._prune(now)
            failures = sum(1 for _, k in self.events if not k)
            if self.state == "half-open":
                if ok:
                    self.state = "closed"
                else:
                    self.state = "open"
                    self.opened_at = now
            elif self.state == "closed" and failures >= self.failure_threshold:
                self.state = "open"
                self.opened_at = now
```

Wiring it into the retry loop: the breaker's `allow()` gates the *first* attempt, and `record()` updates state on every outcome (success or failure). A retry inside an open breaker is a contradiction — fail fast instead.

## Choosing Timeouts

A common mistake is to pick timeouts by feel. The SRE discipline:

1. **Measure** the latency distribution (p50, p95, p99) of the call under normal load.
2. **Set the timeout at p99 × N** (N often 2–5) — high enough to ride out normal tails but low enough to abort pathological cases.
3. **Propagate**: the outer deadline must be the sum of the inner budgets plus some slack.
4. **Re-measure after incidents**: a 1s timeout set when p99 was 50ms is wrong when p99 drifts to 800ms.

## Common Pitfalls

1. **No timeout at all** on outbound HTTP/DB calls — the default `requests.get()` and many DB drivers will block forever on a hung peer. Always set `timeout=`.
2. **Retrying non-idempotent operations.** A retried `POST /charge` can double-charge; combine with idempotency keys or restrict retries to `GET`/`PUT`/`DELETE`.
3. **Retrying on the wrong exceptions.** Retry on `ConnectionError`, `Timeout`, `503`, `429`. Do **not** retry on `400`, `401`, `403`, `404`, `409` — the request is wrong, not transient.
4. **Setting inner timeouts larger than outer ones.** A 5s DB call inside a 2s RPC budget means the 2s caller times out but the DB call keeps running, holding its connection pool slot.
5. **Forgetting jitter.** Synchronized retries create synchronized spikes; under load these spikes prevent recovery.
6. **Tripping the breaker on transient spikes.** A 30s window with `failure_threshold=5` is too sensitive; tune for your traffic volume so a single bad second doesn't trigger a multi-minute outage.
7. **Retrying through a circuit breaker** — an open breaker is a signal to stop retrying, not to try harder.

## Interview Questions

### Q: Why is exponential backoff with jitter better than plain exponential backoff?

Plain exponential backoff still synchronizes clients: every client that failed at t=0 retries at t=base, t=2·base, t=4·base, … producing synchronized spikes that match the failure mode of the upstream. Jitter spreads the retries across a window, decorrelating clients. Decorrelated jitter (AWS) goes further: by basing the next sleep on the previous one rather than on the attempt index, the distribution of sleeps is light-tailed, which prevents the rare but catastrophic long-sleep cascades that equal jitter can produce.

### Q: How would you prevent a retry storm in a service mesh?

Three layers: (1) per-service retry budgets that cap retries to ~10% of successful calls; (2) the rule "retry once at the layer closest to the failure" — let the failing service retry its own downstreams, not its caller; (3) a circuit breaker that short-circuits calls when the downstream is sustainedly failing, so retries stop entirely during outages. Combined with idempotency keys at the application layer (so retries are safe even when they do occur).

### Q: What is deadline propagation and why does it matter?

A single deadline is set at the edge (the user request). It travels with the RPC on the wire (gRPC `grpc-timeout` header, deadline in `context.WithTimeout`). Every downstream computes its timeouts from the *remaining* budget, never from a fresh clock. This guarantees that the sum of inner calls cannot exceed the outer deadline, which prevents orphaned work (a DB call still running after the caller gave up) and gives the end user a predictable latency ceiling.

### Q: When should you NOT retry?

- The operation is non-idempotent and you can't add an idempotency key.
- The error is a 4xx (client error) — the request is wrong, retrying it makes the same wrong request again.
- The circuit breaker is open — retrying is just multiplying load on a broken dependency.
- You're already at the deadline — there's no time left for the retry to succeed.
- The user is waiting synchronously and the latency cost of a retry exceeds the value of recovery.

## References

- AWS Architecture Blog: *Exponential Backoff and Jitter* (classic) — https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- AWS Builders' Library: *Timeouts, Retries, and Backoff with Jitter* — https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- Google SRE Book, Chapter 22: *Addressing Cascading Failures* — https://sre.google/sre-book/addressing-cascading-failures/
- Google SRE Workbook, Chapter 22: *Handling Overload* — https://sre.google/workbook/handling-overload/
- gRPC deadlines documentation — https://grpc.io/docs/guides/deadlines/
- gRPC proposal A6: deadline propagation — https://github.com/grpc/proposal/blob/master/A6-client-stats.md
- Netflix Hystrix Wiki: *How it Works* (circuit breaker state machine) — https://github.com/Netflix/Hystrix/wiki/How-it-Works
- Resilience4j documentation (modern successor to Hystrix) — https://resilience4j.readme.io/docs/circuitbreaker
- Microsoft Azure: *Retry guidance for Azure services* — https://learn.microsoft.com/en-us/azure/architecture/best-practices/retry-service-specific

## Related Topics

- [Idempotency](./idempotency.md) — required for safe retries of non-GET operations
- [Graceful Degradation](./graceful-degradation.md) — what to do when retries and breakers give up
- [Health Check Patterns](./health-check-patterns.md) — probes and the data behind rollback decisions
- [Microservices Communication](./microservices.md) — RPCs and the boundaries across which timeouts propagate
- [Distributed Transactions](./distributed-transactions.md) — how retries interact with two-phase commit
