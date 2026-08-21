# Graceful Degradation and Fallback Patterns

## Overview

When a dependency fails, the system can do one of three things: **fail hard** (return an error to the user), **degrade gracefully** (return a worse-but-useful result), or **fail silently** (return nothing and hope nobody notices). The third is a bug; the first is what naive services do; the second is what production-grade services do. **Graceful degradation** is the discipline of choosing, in advance, what each failure mode looks like to the end user — and implementing the fallback paths before you need them.

This page covers the strategies (stale cache, partial result, default value, fail-open vs fail-closed), the circuit breaker as a degradation trigger, the role of feature flags, the "degrade to read-only" pattern, and the contrast with **fail-fast**.

## Why You Need a Degradation Strategy

A typical web request fans out to a half-dozen dependencies: a database, a recommendation service, a billing service, a feature-flag service, a search index. The naive composition is:

```
fetch user          from DB
fetch recommendations from Recs
fetch billing state from Billing
fetch feature flags from Flags
fetch search hits   from Search
→ render page
```

If any one of these fails, the whole page errors. That is the wrong coupling: the user would have happily read the page **without recommendations**; instead they get a 500. Worse, every retry a user does multiplies load on the failing dependency, accelerating its collapse.

**Degradation** asks, for each dependency, the question: *"What is the worst acceptable behavior if this is unavailable?"* The answer is encoded as a fallback — precomputed at design time, not improvised at 3 a.m.

## The Four Core Strategies

### 1. Return stale cache

The most common fallback. If the source of truth is unreachable, return the last-known-good value from a cache. The cache must be **versioned with a TTL and a "stale-while-revalidate" window** so the caller knows what they got.

```python
import time, threading
from typing import Any, Optional, Callable

class StaleCache:
    """A TTL cache that returns stale values after the source is unreachable."""
    def __init__(self, fetcher: Callable[[], Any], ttl: float = 30.0,
                 stale_window: float = 300.0):
        self.fetcher = fetcher
        self.ttl = ttl
        self.stale_window = stale_window
        self._value: Any = None
        self._fetched_at: float = 0.0
        self._lock = threading.Lock()

    def get(self) -> Optional[Any]:
        now = time.time()
        with self._lock:
            age = now - self._fetched_at
            if age < self.ttl:
                return self._value  # fresh
            # Try to refresh, but accept stale if the source is down.
            try:
                v = self.fetcher()
                self._value = v
                self._fetched_at = now
                return v
            except Exception:
                if self._value is not None and age < self.stale_window:
                    return self._value  # stale
            return None
```

The contract: stale is acceptable for a bounded window (say 5 minutes); beyond that, you degrade further (return default or fail).

### 2. Return partial result

Instead of failing the whole page when one piece is missing, return the page without that piece. This is the pattern that powers e-commerce homepages during partial outages: if the recommendations service is down, render the page with an empty recommendations slot. The user can still shop.

```
USER REQUEST
   │
   ├─ user          ✓ 200
   ├─ cart          ✓ 200
   ├─ pricing       ✓ 200
   ├─ recommendations ✗  (circuit open)
   │
   └─ render page WITHOUT recommendations slot
```

Implementation: wrap each dependency call in a `try/except` that, on failure, substitutes `None` for that slot. The renderer treats `None` as "skip this section".

```python
import concurrent.futures as cf
from typing import Optional, Dict, Any

def render_home_page(user_id: str) -> Dict[str, Any]:
    page = {"user": None, "cart": None,
            "recommendations": None, "degraded": []}

    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        f_user = pool.submit(get_user_safe, user_id)
        f_cart = pool.submit(get_cart_safe, user_id)
        f_recs = pool.submit(get_recs_safe, user_id)

        page["user"] = f_user.result(timeout=0.5) or {"id": user_id,
                                                      "name": "Guest"}
        page["cart"] = f_cart.result(timeout=0.5) or {"items": []}
        try:
            page["recommendations"] = f_recs.result(timeout=0.5)
        except Exception:
            page["degraded"].append("recommendations")
    return page
```

The `degraded` list travels with the response so the front-end can render a banner ("Recommendations are temporarily unavailable") rather than a blank gap that looks like a bug.

### 3. Return default

For values that have a sensible default, hard-code it. The most common example is the **feature-flag service**: if the flag service is unreachable, return the **last-known defaults** baked into the binary, not an error. LaunchDarkly's SDK documents this exact behavior — it ships with a "config file" of last-known flag values cached on disk.

```python
DEFAULTS = {
    "new_checkout_enabled": False,    # safe default = current behavior
    "experimental_search":  False,
    "max_cart_items":        50,
}

def get_flag(key: str, user_id: str) -> bool:
    try:
        return flag_client.eval(key, user_id, default=DEFAULTS[key])
    except Exception:
        return DEFAULTS[key]
```

Critical defaults must always fall to **the current production behavior**, never to a new behavior — otherwise the fallback path turns into a silent feature rollout.

### 4. Fail open vs fail closed

A coarse but essential decision per dependency: when it fails, do we **allow** the operation (fail open) or **deny** it (fail closed)?

| Dependency | Failure mode | Reasoning |
|---|---|---|
| Authentication | **Fail closed** | If auth is down, deny access — security trumps availability |
| Rate limiter | **Fail open** (with monitoring) | All users blocked = worse than occasional over-quota |
| Fraud check | **Fail closed** (high-value) / open (low-value) | Tiered by transaction value |
| Feature flags | Fail open (to defaults) | Page renders even if flags unreachable |
| Quota check | Depends — for billing, fail closed; for free tier, fail open | Business decision |
| Inventory check | Fail closed | Don't oversell what you can't ship |

The decision is **never** "fail open everywhere" or "fail closed everywhere" — it is per-call, and it must be explicit, written down, and reviewed.

## The Circuit Breaker as a Degradation Trigger

A circuit breaker's `open` state is exactly the signal a degradation strategy needs: **the downstream is sustainedly failing, fall back now**. The flow is:

```
   request → breaker.allow()?
               │ yes       │ no (open)
               │           ▼
               ▼           fallback()
            call()         
```

Wiring it together:

```python
class DegradedCall:
    """Calls fn if the breaker is closed; otherwise runs the fallback."""
    def __init__(self, fn, fallback, breaker):
        self.fn = fn
        self.fallback = fallback
        self.breaker = breaker

    def __call__(self, *args, **kwargs):
        if not self.breaker.allow():
            return self.fallback(*args, **kwargs)
        try:
            result = self.fn(*args, **kwargs)
            self.breaker.record(ok=True)
            return result
        except Exception as e:
            self.breaker.record(ok=False)
            # Only fall back on failures the breaker considers retryable.
            return self.fallback(*args, **kwargs)
```

The crucial property: **once the breaker is open, we don't even attempt the call**. The fallback is the response, instantly, with no latency cost and no additional load on the failing service. This is what makes degradation fast — it short-circuits the entire network path.

## Feature Flags for Degradation

Feature flags aren't just for canary launches; they're a runtime kill switch for degraded subsystems. The pattern: each non-critical subsystem is gated by a flag. When the subsystem's health drops (its own breaker opens, or its error rate spikes), an operator flips the flag to `disabled` and the page renders without it — no deploy, no restart.

```python
def get_recommendations(user_id: str) -> Optional[list]:
    if not flag_client.eval("recs.enabled", user_id, default=True):
        return None  # operator has explicitly disabled recs
    if recs_breaker.state == "open":
        return None  # automatic degradation
    try:
        return recs_client.fetch(user_id, timeout=0.3)
    except Exception:
        return None
```

Two-tier degradation: **automatic** (breaker-driven, no human in the loop) and **manual** (operator-driven via flag). Both must exist; the automatic tier handles sub-minute outages, the manual tier handles long outages where you want to take a subsystem offline cleanly (e.g., the recs service is being migrated and you don't want auto-recovery churn).

## The "Degrade to Read-Only" Pattern

A particularly useful degradation shape: when the *write path* is impaired (a database is read-only during a failover, a downstream billing service is down), **accept reads but reject writes with a clear message**. The user can browse, search, and inspect; they cannot place orders.

```
                ┌──────────────────────────┐
                │   Load Balancer           │
                └────────┬─────────────────┘
                         │
        ┌────────────────┴───────────────────┐
        │                                     │
   ┌────▼────┐                          ┌────▼────┐
   │ WRITE   │  ← breaker open          │  READ   │  ← still healthy
   │ path   │  → 503 "Try later"        │  path   │  → 200
   └─────────┘                          └─────────┘
```

Implementation: a single endpoint on the service that exposes the current "writable" state. Every write handler checks this endpoint first; if the write path is degraded, return `503 Service Unavailable` with a `Retry-After` header so clients (and the CDN) treat it as a temporary outage rather than a permanent rejection.

```python
from fastapi import FastAPI, HTTPException, Response
import time

app = FastAPI()
WRITE_STATE = {"writable": True, "since": time.time()}

@app.middleware("http")
async def gate_writes(request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if not WRITE_STATE["writable"]:
            return Response(
                content='{"error":"write_path_degraded"}',
                status_code=503,
                media_type="application/json",
                headers={"Retry-After": "30"},
            )
    return await call_next(request)

@app.post("/admin/write-state")
async def set_write_state(payload: dict):
    # Protected admin endpoint
    WRITE_STATE["writable"] = payload.get("writable", True)
    WRITE_STATE["since"] = time.time()
    return WRITE_STATE
```

The rule: **read paths must not depend on the write path's health**. This is an architectural constraint, not a runtime trick — the read path must hit a read replica or a cache that survives a primary-database failover.

## Comparison to Fail-Fast

Fail-fast is the opposite philosophy: instead of substituting, **return the error immediately**. Both have a place:

| Property | Graceful degradation | Fail-fast |
|---|---|---|
| Latency on failure | High (must run fallback) | Minimal (immediate error) |
| User experience | Continues working, possibly worse | Stops working, explicit error |
| Operator signal | Easy to miss (degraded is silent) | Loud (errors visible) |
| Code complexity | High (multiple code paths) | Low (single error path) |
| Best for | User-facing pages, optional subsystems | Critical-path, write operations |
| Risk | Wrong fallback could mask a real bug | Outage visible to users |

The right answer is usually a hybrid: **fail-fast on the critical path, degrade on optional paths**. A payment cannot be partially charged; an order cannot be partially placed. These must fail fast. A homepage with one fewer recommendation is still a homepage; that should degrade.

The trap is when a team chooses degradation for everything because "we don't want users to see errors" — this hides real outages from operators. The fix: **emit a metric and a log line every time degradation is triggered**. A `degradation_counter{path="recommendations"}` graphed next to the success rate makes a silent fallback loud to on-call.

## Common Pitfalls

1. **No fallback defined for a dependency** — when it fails, the default behavior is a 500. The fix is a design review: every outbound call in the request path must have an explicit "what if this fails" answer.
2. **Silent fallback** — the user gets a worse experience and never knows. Always attach a `degraded` flag to the response and emit a metric.
3. **Fallback that itself depends on the same broken service** — e.g., a stale-cache fallback that calls the same Redis that just went down. Fallbacks must be independent of the failing dependency.
4. **Fail open on security-sensitive paths** — authentication, authorization, fraud checks should fail closed by default; failing open is a security incident waiting to happen.
5. **Default values that change behavior** — a flag's default must be the **currently shipped behavior**, not a future one. Otherwise, the fallback silently rolls out the feature.
6. **Breaker never wired to fallback** — many teams add a circuit breaker but still throw on open. The breaker's whole purpose is to trigger the fallback; wire them together.
7. **Stale cache that's too stale** — a 24-hour stale window for pricing data is a bug, not a fallback. Tune the `stale_window` per data type.

## Interview Questions

### Q: How would you degrade a recommendation service failure on an e-commerce homepage?

The recommendations slot is optional; the rest of the page (user, cart, pricing, inventory) must still render. Wrap the recommendations call in a circuit breaker; on `open` or exception, return `None` for that slot and add `"recommendations"` to a `degraded` list in the response. The renderer skips the slot and emits a banner. An operator can also kill the slot explicitly via a feature flag for longer outages. Throughout, a `degradation_counter` metric tracks how often the fallback is hit so we know about it.

### Q: When should you fail open vs fail closed?

Fail closed when the cost of incorrectly allowing an operation is high (authn, authz, fraud, inventory for physical goods). Fail open when the cost of incorrectly denying is high (rate limiting on a free product, recommendation rendering, non-critical telemetry). The decision is per-call and must be written down; never default one way or the other without analysis.

### Q: How does a circuit breaker enable graceful degradation?

The breaker's `open` state is a fast, local signal that the downstream is sustainedly unhealthy. The caller doesn't need to wait for a timeout or measure error rates — the breaker's `allow()` returns `false` and the caller immediately invokes its fallback. This breaks the failure cascade: the failing service receives no traffic during its outage (giving it room to recover) and the user receives a degraded-but-functional response instead of an error.

### Q: What's the risk of returning a stale cache forever?

Stale data drifts away from reality. A pricing cache that's been stale for 24 hours may show outdated prices, which can cause legal and trust issues. Every stale cache needs a `stale_window` after which the fallback degrades further (return default, fail closed, or surface an error). Operators must also see a metric for `stale_serves` so a long-running stale serve doesn't silently persist.

### Q: How do feature flags interact with degradation?

Flags give operators a manual kill switch on top of the breaker's automatic one. When a subsystem's breaker has been flapping (open, half-open, open again), flipping a flag to `disabled` takes it offline cleanly — no auto-recovery churn, no client timeouts. When the subsystem is fixed, flipping the flag back on lets it warm up before the breaker closes. Flags also let you degrade for non-failure reasons: load-shedding during a traffic spike, or rolling out a fix that needs to be reverted quickly.

## References

- Google SRE Book, Chapter 6: *Dealing with Interrupts* (graceful degradation, fail-fast) — https://sre.google/sre-book/addressing-cascading-failures/
- Google SRE Workbook, Chapter 13: *Handling Overload* — https://sre.google/workbook/handling-overload/
- Netflix Hystrix Wiki: *Fallback* — https://github.com/Netflix/Hystrix/wiki/Fallback
- Resilience4j: *Circuit Breaker and Fallback* — https://resilience4j.readme.io/docs/circuitbreaker
- Peter Deutsch's *Fallacies of Distributed Computing* (1987, still canonical) — https://www.rgoarchitects.com/Software-Anti-Patterns/Distributed-Computing-Fallacies
- AWS Builders' Library: *Graceful Degradation* — https://aws.amazon.com/builders-library/workload-graceful-degradation/
- Microsoft: *Pattern: Health Endpoint Monitoring* — https://learn.microsoft.com/en-us/azure/architecture/patterns/health-endpoint-monitoring
- Martin Fowler: *Circuit Breaker* — https://martinfowler.com/bliki/CircuitBreaker.html
- LaunchDarkly: *Defaults and offline mode* — https://docs.launchdarkly.com/sdk/concepts/flags

## Related Topics

- [Retry and Timeout Patterns](./retry-timeout.md) — what triggers degradation in the first place
- [Health Check Patterns](./health-check-patterns.md) — the probes that inform degradation decisions
- [Progressive Delivery](./progressive-delivery.md) — feature flags as both rollout and degradation tools
- [Idempotency](./idempotency.md) — required when retrying fallback paths
- [Microservices](./microservices.md) — service boundaries across which degradation composes
