# Reliability Patterns

> Distributed systems don't fail gracefully by default — you have to design for it.

## 1. Retry with Exponential Backoff

Transient failures (network blips, temporary overload) are common. Retrying naively can amplify the problem. **Exponential backoff** increases the delay between retries, giving the downstream service time to recover.

### Formula

``ndelay = base_delay × 2^attempt + jitter```

### Implementation

```python
import random
import time

def retry_with_backoff(func, max_retries=5, base_delay=0.1):
    for attempt in range(max_retries):
        try:
            return func()
        except TransientError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            jitter = random.uniform(0, delay * 0.5)
            time.sleep(delay + jitter)
```

| Parameter | Purpose | Typical Value |
|-----------|---------|---------------|
| `base_delay` | Initial wait time | 100ms – 1s |
| `max_retries` | Give up after this many attempts | 3 – 5 |
| `jitter` | Random offset to prevent thundering herd | 0 – 50% of delay |
| `max_delay` | Cap to prevent excessive waits | 30s – 60s |

**Why jitter?** Without it, all clients retry at the same moment, causing a **thundering herd** that re-overloads the recovering service.

## 2. Circuit Breaker

Prevent cascading failures by **stop calling a failing service** and give it time to recover.

### Three States

```
         trips threshold        timeout expires
CLOSED ──────────────────→ OPEN ──────────────────→ HALF-OPEN
  ↑                                                    │
  └──────────── success threshold ─────────────────────┘
```

| State | Behavior |
|-------|----------|
| **Closed** | Requests pass through normally. Track failure count. |
| **Open** | All requests fail fast (no network call). Return cached/default response. |
| **Half-Open** | Allow a limited number of test requests. If they succeed → Closed. If they fail → Open. |

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = "CLOSED"
        self.last_failure_time = None

    def call(self, func):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF-OPEN"
            else:
                raise CircuitOpenError("Service unavailable")

        try:
            result = func()
            self.failure_count = 0
            self.state = "CLOSED"
            return result
        except Exception:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

## 3. Bulkhead

Isolate failures by partitioning resources so a failing component can't take down the entire system. Named after ship compartments that prevent water from flooding the entire hull.

### Types

| Pattern | Description |
|---------|-------------|
| **Thread pool isolation** | Each downstream service gets its own thread pool |
| **Process isolation** | Each service runs in a separate process/container |
| **Semaphore isolation** | Limit concurrent requests to a dependency |

```
Service A ──→ Thread Pool A (10 threads) ──→ Payment Service
Service B ──→ Thread Pool B (20 threads) ──→ Notification Service

If Payment Service hangs:
  - Only 10 threads are consumed
  - Notification Service is unaffected
```

Without bulkhead, a slow downstream service exhausts all threads, making the entire application unresponsive.

## 4. Timeout Budgets

Every service call must have a timeout. In a chained call, allocate time budgets **proportionally**.

```
Client → API Gateway (timeout: 5s)
  → User Service (budget: 1s)
  → Order Service (budget: 2s)
    → Inventory Service (budget: 500ms)
    → Database (budget: 300ms)
```

### Rules

| Rule | Explanation |
|------|-------------|
| **Every outgoing call gets a deadline** | No call should block indefinitely |
| **Downstream timeout < upstream timeout** | Leave time for the caller to handle the error |
| **Use deadline propagation** | Pass the remaining deadline to downstream calls |
| **Fail fast** | Return an error rather than hold a thread for a hopeless call |

```go
// Go: context with deadline propagation
ctx, cancel := context.WithTimeout(parentCtx, 2*time.Second)
defer cancel()
resp, err := client.Do(req.WithContext(ctx))
```

## 5. Graceful Degradation

When a non-critical dependency fails, serve a reduced but acceptable experience rather than failing entirely.

```
Normal:  Show product recommendations + reviews + price comparison
Degraded: Show product page without recommendations (cache stale data)
Fallback: Show product page with static content only
```

| Strategy | Example |
|----------|---------|
| **Cached response** | Serve stale data from cache when backend is down |
| **Feature flag** | Disable non-essential features via toggle |
| **Default values** | Return empty results instead of errors |
| **Static fallback** | Serve pre-rendered static pages |

## 6. Health Checks

Expose endpoints that report service health, enabling automated recovery.

### Types

| Type | What It Checks | Use For |
|------|---------------|----------|
| **Liveness** | "Is the process alive?" | Restart the container if it fails |
| **Readiness** | "Can it handle requests?" | Remove from load balancer if not ready |
| **Startup** | "Has it finished initializing?" | Don't route traffic during warmup |

```
GET /healthz          → 200 OK (liveness)
GET /readyz           → 200 OK (readiness) or 503
GET /livez            → detailed liveness with component status
```

A readiness probe might check: database connection pool, Redis connectivity, disk space > 10%. If any check fails, return 503 so the load balancer stops routing traffic.

## 7. Rate Limiting as a Reliability Tool

Rate limiting isn't just for API quotas — it's a **protective mechanism** that prevents any single client (or downstream service) from overwhelming your system.

| Algorithm | Description | Best For |
|-----------|-------------|----------|
| **Token bucket** | Tokens refill at fixed rate; each request consumes one | Bursty traffic with sustained rate limit |
| **Leaky bucket** | Requests processed at fixed rate; queue overflow rejected | Smooth, predictable output rate |
| **Fixed window** | N requests per time window | Simple implementations |
| **Sliding window** | N requests per rolling window | Avoids fixed-window edge burst |

Rate limiting protects against: DDoS, runaway retries (amplification loops), and downstream overload.

## Interview Questions

1. **What is exponential backoff? Why add jitter?**
   Exponential backoff increases retry delay multiplicatively (delay × 2^attempt). Jitter adds randomness to prevent all clients from retrying simultaneously (thundering herd), which would re-overload the recovering service.

2. **Explain the circuit breaker pattern. What problem does it solve?**
   It prevents cascading failures. When a downstream service fails repeatedly, the circuit opens and calls fail fast without making network requests. After a timeout, it transitions to half-open to test recovery. This protects the caller from wasting resources on a failing service.

3. **What is a bulkhead? How does it differ from a circuit breaker?**
   A bulkhead isolates resources (thread pools, connections) per dependency so one failing service can't exhaust resources for others. A circuit breaker stops calling a failing service entirely. They're complementary: bulkhead limits *blast radius*, circuit breaker stops *wasted calls*.

4. **What is a timeout budget and why does it matter?**
   In a chain of service calls (A → B → C → D), each downstream call must have a shorter timeout than its caller. This ensures the caller always has time to handle the error, respond to its client, and avoid holding threads indefinitely.

5. **What's the difference between liveness and readiness probes?**
   Liveness: "restart me if I'm dead" (process crash, infinite loop). Readiness: "don't send me traffic until I'm ready" (warming caches, connecting to DB). A service can be alive but not ready.

6. **Give an example of graceful degradation.**
   An e-commerce page that shows product details but hides recommendations and reviews when the recommendation service is down. Users still get core functionality; the non-essential features degrade silently.

7. **How does rate limiting improve reliability?**
   It prevents any single client or retry storm from overwhelming the system. Without it, a failing service's clients retrying aggressively can create an amplification loop that takes down the entire system.

8. **When would you choose a leaky bucket over a token bucket for rate limiting?**
   Leaky bucket provides a constant, predictable output rate — good for processing pipelines where you need steady throughput. Token bucket allows bursts up to the bucket size — better for API endpoints where some burstiness is acceptable.
