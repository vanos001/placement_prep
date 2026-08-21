# Health Check Patterns

## Overview

A health check is a service's answer to the question *"can you serve traffic right now?"* It is not a single yes/no — there are several different questions hiding under that label, and conflating them causes outages. Kubernetes formalized the split into three probes — **liveness**, **readiness**, and **startup** — each with a different purpose, a different failure handling, and a different consequence when wrong. On top of these, **deep health checks** answer *"what is broken internally?"* and exist for humans, not for orchestrators.

This page covers the four kinds, the endpoint design (what `/health`, `/ready`, `/live` should and shouldn't return), the comparison to Kubernetes probes, and the failure modes that get teams paged at 3 a.m.

## The Four Questions

```
┌──────────────────────────────────────────────────────────────────┐
│ Is the process running?                     →  liveness probe    │
│ Is the process still booting?              →  startup probe      │
│ Can the process serve traffic right now?    →  readiness probe    │
│ What is broken inside?                     →  deep health check │
└──────────────────────────────────────────────────────────────────┘
```

Mixing these up is the source of almost every health-check-related incident:

- Treating **readiness** as **liveness** → orchestrator kills the pod when a downstream is down, restarting healthy containers that just couldn't reach a database.
- Treating **liveness** as **readiness** → orchestrator keeps the pod in the service mesh even though it crashed, sending traffic to a dead process.
- Treating **deep** checks as **readiness** → a flaky downstream takes the pod out of rotation, propagating the failure to every caller.

## Liveness: Is the Process Alive?

Liveness answers: *"If I send this process a request, will it respond at all — or is it hung in a deadlock, stuck in a GC pause, or panicked?"* The orchestrator uses liveness to decide **whether to restart the container**.

Properties of a good liveness probe:

- **Cheap**: must return in well under a second. It runs frequently (every 10s by default).
- **Local**: must not depend on any other service. Liveness that checks DB connectivity will kill the pod when the DB is down.
- **Coarse**: a 200 means "the process can answer HTTP at all"; a 500 means "the event loop is stuck, restart me".

```python
import time
from fastapi import FastAPI

app = FastAPI()
STARTED_AT = time.time()
LAST_READY = time.time()  # updated by readiness logic

@app.get("/live")
def liveness():
    # Only "is the process here". A 200 here means: the event loop is
    # running and HTTP handlers can fire. Nothing else.
    if time.time() - LAST_READY > 60:
        # Watchdog: if readiness hasn't run in 60s, the event loop
        # is stuck. Force a restart by failing liveness.
        return {"status": "dead"}, 503
    return {"status": "alive"}
```

A common watchdog pattern: a background thread updates `LAST_READY` every 5s; liveness checks that the timestamp is fresh. If the timestamp is stale, the event loop is blocked and the container should be killed.

## Readiness: Can the Process Serve Traffic?

Readiness answers: *"Is this pod able to handle a request usefully right now?"* The orchestrator uses readiness to decide **whether to route traffic to the pod** — but **not** to restart it.

A pod can be not-ready for many reasons without being broken:

- It's still warming up its caches after startup.
- A downstream dependency (DB, Redis) is temporarily unreachable.
- It's draining in preparation for shutdown.

```python
import redis, psycopg2

@app.get("/ready")
def readiness():
    # Readiness DOES depend on dependencies — that's the point.
    # If we can't reach the DB, we can't serve a request usefully.
    try:
        db.ping(timeout=0.2)
    except Exception:
        return {"status": "not-ready", "reason": "db-down"}, 503
    return {"status": "ready"}
```

Key rule: **not-ready ≠ broken**. If a downstream blip drops a pod's readiness, the load balancer stops sending traffic — but the orchestrator must not kill the pod. This is why Kubernetes uses different probes: `livenessProbe` failure → restart; `readinessProbe` failure → stop routing.

## Startup: Is the Process Still Booting?

Startup is a relatively recent addition (Kubernetes 1.16+) that solves a specific problem: **slow-booting services with aggressive liveness probes**. A Java service that takes 90 seconds to start will fail a liveness probe set to `initialDelaySeconds=30, periodSeconds=10, failureThreshold=3` — it dies before it finishes booting.

The startup probe runs only during initialization; while it's failing, the liveness and readiness probes are suspended. Once it succeeds once, it never runs again and the other two take over.

```yaml
# Kubernetes pod spec
startupProbe:
  httpGet:
    path: /startup
    port: 8080
  failureThreshold: 30      # 30 × 10s = 5 min allowed for boot
  periodSeconds: 10
livenessProbe:
  httpGet:
    path: /live
    port: 8080
  periodSeconds: 10
  failureThreshold: 3
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  periodSeconds: 5
  failureThreshold: 1
```

The endpoint:

```python
@app.get("/startup")
def startup():
    # Returns 200 only once initialization is fully complete
    # (warm caches, ready to serve). Then Kubernetes switches over.
    if not APP_INITIALIZED:
        return {"status": "starting"}, 503
    return {"status": "started"}
```

The right pattern: use startup with a long `failureThreshold` so slow boots survive; use liveness with a tight threshold so post-boot hangs are caught.

## Deep Health Checks: What's Broken Inside?

A liveness/readiness probe is binary — it tells the orchestrator yes/no. **Deep health checks** tell a human what is wrong: which downstream is unreachable, which cache is stale, which queue is backing up. They run on a different endpoint, return a structured payload, and are consumed by dashboards and alerting — not by Kubernetes.

```python
@app.get("/health")
def health():
    """Deep check: enumerate each subsystem and its state."""
    checks = {
        "database":   check_db(),
        "redis":      check_redis(),
        "downstream": check_billing(),
        "queue_depth": queue_depth(),
    }
    overall = all(c["ok"] for c in checks.values())
    return {
        "status": "ok" if overall else "degraded",
        "checks": checks,
    }, 200 if overall else 503

def check_db():
    try:
        with db.connection(timeout=0.3) as conn:
            conn.execute("SELECT 1")
        return {"ok": True, "latency_ms": 12}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def check_redis():
    try:
        r.ping()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def queue_depth():
    n = queue.length()
    return {"ok": n < 10000, "depth": n}
```

Design rules for deep checks:

1. **Each check has a per-check timeout.** A 30s deep check that hangs defeats its purpose. Cap each sub-check at 200–500ms.
2. **Aggregate state, not just sub-state.** A single check failure can mark the whole service `degraded` (503) or just report it as a degraded sub-check with the overall status still `ok`. Pick a convention and stick to it.
3. **Don't wire `/health` to the orchestrator.** Use `/live`, `/ready`, `/startup` for Kubernetes; use `/health` (or `/healthz`, `/status`) for humans and dashboards. Mixing them is what gets pods killed when a non-critical subsystem blips.
4. **Distinguish critical from non-critical sub-checks.** A recommendations-service blip should not mark the service `degraded`; a database blip should. Tag each check with a severity.

## Endpoint Design: What Goes Where

```
/live        ← liveness    (cheap, local, orchestrator-driven)
/ready       ← readiness   (depends on traffic-serving deps)
/startup     ← startup     (initialization only)
/health      ← deep        (subsystem enumeration, human-driven)
/metrics     ← Prometheus  (numerical, for alerting)
```

Anti-patterns to avoid:

- **`/health` that returns 500 when a downstream is down** → Kubernetes (if pointed here) restarts the pod. Use `/ready` instead.
- **`/ready` that returns 500 when a non-critical downstream is down** → pod leaves rotation; the service loses capacity. Readiness should only fail for **traffic-critical** dependencies.
- **`/live` that connects to the DB** → DB blip kills every pod; the entire service is restarted because a downstream was unhealthy. Catastrophic.
- **Deep checks with no per-check timeout** → one hung downstream makes the whole `/health` endpoint hang, hiding the real state.
- **No `/startup` and an aggressive `/live`** → slow-booting services die before they finish starting.

## Comparison to Kubernetes Probes

| Probe | Failure consequence | Run frequency | Depends on | Use case |
|---|---|---|---|---|
| **liveness** | Restart the container | ~every 10s | Nothing external | Catch deadlocks, GC stalls, panics |
| **readiness** | Remove pod from service endpoints | ~every 5s | Traffic-critical deps | Skip the pod during blips, drains |
| **startup** | Restart container (after long threshold) | ~every 10s, only during boot | Internal init state | Allow slow boots to finish |
| **deep health** | None (humans read it) | On demand | All subsystems | Diagnose what is broken |

The probes map onto different orchestrator actions. Crucially, **readiness is not "is the pod broken"** — it's "should the load balancer route to this pod". A pod can be `live=true, ready=false` for minutes during a downstream blip, and the orchestrator should leave it alone.

## Failure Modes

### 1. Liveness kills pods during downstream outage

A pod's liveness probe checks the database. The database fails. Every pod's liveness starts failing. Kubernetes restarts every pod. The restarts don't fix the DB and instead lose warm caches, making recovery slower. Fix: liveness must be local-only.

### 2. Readiness flapping causes cascading load shedding

A pod's readiness probe has `failureThreshold=1, periodSeconds=5`. A downstream blips for 6 seconds. The pod leaves rotation, traffic shifts to the others, they overload, their readiness fails, traffic shifts again, oscillation. Fix: tune `failureThreshold` and `periodSeconds` so transient blips don't trigger removal; the standard advice is `failureThreshold=3` minimum.

### 3. Startup probe missing, slow boots die

A JVM service takes 2 minutes to start. Liveness kills it at 90s. Fix: add a startup probe with `failureThreshold: 30, periodSeconds: 10` (5 minutes of allowed boot time).

### 4. Deep checks used as readiness

The team wires `/health` (which checks five downstreams) as the readiness probe. Any downstream blip takes the pod out of rotation. The service haemorrhages capacity on every minor downstream issue. Fix: separate `/ready` (only traffic-critical deps) from `/health` (full subsystem picture for humans).

### 5. Health check itself has no timeout

`/health` calls each downstream with the default 30s timeout. A single hung downstream makes the whole probe hang for 30s, during which the orchestrator has already declared the pod unhealthy. Fix: per-check timeouts, total probe time bounded.

## Common Pitfalls

1. **Using one endpoint for everything** — `/health` that does it all inevitably serves some caller badly. Split into `/live`, `/ready`, `/startup`, `/health`.
2. **Liveness that depends on the network** — the cardinal sin. Liveness is "is the process here"; checking the network asks "is the network here".
3. **No startup probe for slow boots** — Java, .NET, or any JIT-heavy runtime needs startup; without it, the orchestrator kills the pod mid-boot.
4. **Readiness with `failureThreshold=1`** — guarantees flapping on any blip. Use 3+.
5. **Returning 500 on partial deep-check failure** — Kubernetes (if misconfigured to use `/health`) restarts pods. Reserve 500 for "I cannot serve traffic"; use 200 with a `degraded` payload for "something is wrong but I'm up".
6. **No auth on deep checks** — `/health` exposes internal topology (downstream hostnames, queue depths). Put it behind auth or a private port.
7. **Health check blocking the request path** — some teams put health logic in middleware that runs on every request; this adds latency to user traffic. Health endpoints should be distinct handlers.

## Interview Questions

### Q: What's the difference between liveness and readiness probes?

Liveness answers "should Kubernetes restart this container?" — it tests whether the process itself is alive (event loop running, can answer HTTP). It must not depend on the network. Readiness answers "should the load balancer route traffic to this container?" — it tests whether the pod can usefully serve a request right now, which may include checking downstream connectivity. A pod can be live but not ready (a downstream blip); a pod cannot be ready without being live.

### Q: Why does Kubernetes have a startup probe in addition to liveness?

Slow-booting services (Java, large .NET apps, anything that JIT-compiles or warms caches) take minutes to start. An aggressive liveness probe will kill the container before it finishes booting — a "crash loop" where the pod never becomes ready. The startup probe runs only during initialization, with a long failure threshold, and suspends liveness and readiness until it succeeds once. After boot, liveness and readiness take over.

### Q: How do you design a deep health check endpoint?

Separate it from the orchestrator-driven probes (use `/health`, not `/live` or `/ready`). It enumerates each subsystem — database, cache, downstream services, queue depths — with per-check timeouts of 200–500ms. It returns a structured payload (`{"status": "degraded", "checks": {...}}`) and an HTTP status that distinguishes "I can serve traffic but something is wrong" (200 with degraded payload) from "I cannot serve traffic" (503). It's consumed by dashboards and alerting, not by Kubernetes.

### Q: How would you prevent a downstream outage from cascading via the health check?

Two rules: (1) liveness is local-only — it must not check the network, so a downstream outage cannot kill pods; (2) readiness checks only traffic-critical dependencies with a tuned `failureThreshold` so transient blips don't remove pods from rotation. For non-critical downstreams, use circuit breakers and graceful degradation in the request path rather than removing the pod from rotation. Deep health checks report downstream state for humans but never affect pod lifecycle.

### Q: Should `/health` return 200 or 503 when a non-critical subsystem is down?

Depends on the audience. For Kubernetes-driven probes, never use `/health` — use the specific probe. For human-driven dashboards, returning 200 with a `degraded` payload (and a per-subsystem breakdown) is more useful than a blanket 503, because the dashboard can show which subsystem failed. Returning 503 only when the service cannot serve traffic keeps the signal-to-noise ratio high.

## References

- Kubernetes documentation: *Configure Liveness, Readiness and Startup Probes* — https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Kubernetes documentation: *Pod Lifecycle* (probe semantics) — https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
- Google SRE Book, Chapter 6: *Monitoring* (asymmetric monitoring, alerting) — https://sre.google/sre-book/practical-alerting/
- Google SRE Book, Chapter 14: *Addressing Cascading Failures* (health check failure modes) — https://sre.google/sre-book/addressing-cascading-failures/
- Spring Boot Actuator: *Health Indicators* — https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/#actuator
- Kubernetes enhancement KEP-0057: *Startup probes* — https://github.com/kubernetes/enhancements/tree/master/keps/sig-network/0057-distributed-ldu
- AWS Builders' Library: *Implementing Health Checks* — https://aws.amazon.com/builders-library/implementing-health-checks/
- Microsoft Azure: *Health Endpoint Monitoring pattern* — https://learn.microsoft.com/en-us/azure/architecture/patterns/health-endpoint-monitoring
- Cloud Native Computing Foundation: *Liveness and Readiness Probes — Best Practices* — https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/

## Related Topics

- [Retry and Timeout Patterns](./retry-timeout.md) — health-check timeouts on the probe path
- [Graceful Degradation](./graceful-degradation.md) — what to do when deep checks show degradation
- [Progressive Delivery](./progressive-delivery.md) — probes gate canary promotion and rollback
- [Microservices](./microservices.md) — service meshes and probe integration
