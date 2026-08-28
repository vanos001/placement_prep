# Knative Serving Internals: From Request to Pod and Back

Knative Serving is the de facto Kubernetes layer for scale-to-zero HTTP
services: it wraps a container in a revision object, inserts a queue
between the network and the user pod, and drives the replica count from
observed concurrency - down to zero and back. That last sentence hides
the interesting machinery: an *activator* that buffers requests while
pods boot, an autoscaler with a panic reflex, and a queue-proxy sidecar
that makes per-pod concurrency a measurable, enforceable quantity. This
page walks the data path, the control loops, and the cold-start anatomy,
then simulates the scale-from-zero decision on a request trace.

Platform context: [serverless fundamentals](./serverless.md) for the
model-of-computing overview, [Firecracker](../virtualization/firecracker.md)
for the sandbox layer Knative often runs on, and
[autoscaling](../autoscaling.md) for the HPA comparison.

## The data path, hop by hop

```text
  client -> ingress-gateway -> [activator?] -> queue-proxy (pod) -> user container
                                    |                 |
                                    +-- buffers reqs  +-- enforces concurrency,
                                        while scaling     reports metrics
```

- **Route/Revision**: a Revision pins container image + config + the
  concurrency parameters; Routes point traffic at a Revision (or split).
- **Ingress gateway**: Terminates TLS, routes by host/path.
- **Activator**: The interesting component. When a revision is scaled to
  zero, the gateway targets the activator, which holds requests in a
  queue, requests capacity from the autoscaler, waits for an endpoint,
  then forwards. It is also part of the *steady-state* path when pods
  are saturated (buffering excess concurrency instead of overloading
  pods).
- **Queue-proxy**: A sidecar on every pod. It measures in-flight
  requests (the signal the autoscaler actually consumes), enforces the
  container's concurrency limit (rejecting/queueing above it), and
  handles health/probing - so the user container needs no awareness of
  any of this.

## The autoscaler: KPA, panic, and the stable window

The Knative Pod Autoscaler (KPA) is a concurrency-matching controller:

- **Target**: `containerConcurrency` (hard per-pod limit) or the softer
  `targetConcurrencyUtilization` (usually 70% of the limit).
- **Stable window** (default 60 s): desired pods =
  `ceil(total_concurrent_requests / target_per_pod)` averaged over the
  window - smooth, cheap, and slow to react to bursts.
- **Panic mode** (6 s window): when the 6-second average exceeds the
  panic threshold (200% by default), the autoscaler switches to the
  short window and scales aggressively, then decays back to stable once
  the burst passes. This two-window design is the standard answer to
  "averages hide bursts".
- **Scale-to-zero**: after a grace period with zero traffic, the revision
  scales to 0; the activator absorbs subsequent requests.

The demo below replays a bursty request trace through a simulated KPA
(stable + panic windows, activation latency) and reports end-to-end
latency percentiles per regime - making the cold-start and panic-window
effects concrete.

```python
#!/usr/bin/env python3
"""Knative-style autoscaler simulation on a bursty trace.

Model per second (discrete): request arrivals; active pods handle
`target_conc` each; excess queues at the activator. Scale decisions use
two windows: stable (60s mean concurrency) and panic (6s mean, when
panic > 2x target). Scale-to-zero after 90s idle. Activation: from 0
pods, first request waits act_latency then pods serve.

Deterministic trace: 10 min = 600s, 3 phases (idle, spike, steady)."""
import math

SECS = 600
TARGET_CONC = 10          # per pod
STABLE_W, PANIC_W = 60, 6
PANIC_THRESHOLD_PCT = 200
ACTIVATION_LATENCY = 3.0  # seconds from 0 -> first pod ready
POD_START_RATE = 5.0      # pods added per second once scaling

def arrivals(t):
    """requests per second: quiet, then a 50x spike, then steady 2x"""
    if t < 200: return 5
    if t < 220: return 250       # spike
    if t < 400: return 10
    return 12

conc_hist, pods, queued = [], 0, 0.0
lat_samples = []
panic_until = -1
zero_since = 0
for t in range(SECS):
    a = arrivals(t)
    conc_hist.append(a)
    stable = sum(conc_hist[-STABLE_W:]) / min(len(conc_hist), STABLE_W)
    panic_mean = sum(conc_hist[-PANIC_W:]) / min(len(conc_hist), PANIC_W)
    if panic_mean > (PANIC_THRESHOLD_PCT / 100) * TARGET_CONC:
        panic_until = t + 30
    in_panic = t <= panic_until
    window = PANIC_W if in_panic else STABLE_W
    mean = panic_mean if in_panic else stable
    want = math.ceil(mean / TARGET_CONC) if mean > 0 else 0
    if want == 0 and a == 0:
        zero_since += 1
        if zero_since > 90:
            pods = 0
    else:
        zero_since = 0
    if pods == 0 and a > 0:
        lat_samples.append(ACTIVATION_LATENCY + a / (POD_START_RATE * TARGET_CONC))
        pods = min(want, max(1, int(POD_START_RATE)))
        queued = max(0.0, a - pods * TARGET_CONC)
    else:
        deficit = want - pods
        if deficit > 0:
            pods += min(deficit, max(1, int(POD_START_RATE)))
        elif deficit < 0 and a == 0:
            pods = max(0, want)
    served = pods * TARGET_CONC
    backlog = queued + a
    if pods > 0:
        drain = min(backlog, served)
        lat_samples.append(drain / served * 1.0 + 0.05)
        queued = backlog - drain
    if t in (10, 205, 215, 230, 300, 450, 590):
        print(f"  t={t:>3}s arrivals={a:>4} pods={pods:>3} "
              f"{'PANIC' if in_panic else 'stable':>6} queued={queued:>7.1f}")

lat_samples.sort()
n = len(lat_samples)
def pct(p): return lat_samples[int(p * n)]
print()
print(f"simulated latency (per-second service-time model, seconds):")
print(f"  p50 = {pct(0.50):.2f}  p95 = {pct(0.95):.2f}  p99 = {pct(0.99):.2f}  "
      f"max = {lat_samples[-1]:.2f}")
print(f"  (activation adds {ACTIVATION_LATENCY}s to first requests after idle;")
print(f"   panic-window scaling is what keeps the spike phase from queuing")
print(f"   behind a 60s average that barely moves)")
```

```text
t= 10s arrivals=   5 pods=  1 stable queued=    0.0
  t=205s arrivals= 250 pods= 25  PANIC queued=  600.0
  t=215s arrivals= 250 pods= 25  PANIC queued=  600.0
  t=230s arrivals=  10 pods= 25  PANIC queued=    0.0
  t=300s arrivals=  10 pods= 25 stable queued=    0.0
  t=450s arrivals=  12 pods= 25 stable queued=    0.0
  t=590s arrivals=  12 pods= 25 stable queued=    0.0

simulated latency (per-second service-time model, seconds):
  p50 = 0.10  p95 = 0.55  p99 = 1.05  max = 3.10
  (activation adds 3.0s to first requests after idle;
   panic-window scaling is what keeps the spike phase from queuing
   behind a 60s average that barely moves)
```

## Cold-start anatomy and the mitigation menu

A scale-from-zero request pays: ingress routing (~ms) -> activator
accept -> autoscaler decides -> Kubernetes schedules a pod -> image
pull -> container init -> queue-proxy ready -> endpoint propagation ->
first byte. Measured cold starts land in the hundreds-of-ms to
multi-second range, dominated by image pull and app init. The mitigation
menu, in order of leverage: keep images small and pre-pulled (node
image caching), init-container warming, `minScale=1` for hot paths
(paying always-on cost), and - the research frontier - snapshot/restore
via CRIU-style images or Firecracker microVM snapshots, which move the
boundary from "boot" to "restore memory" (tens of ms).

Stateful serverless (Cloudburst, arXiv:2001.04592) adds the other half:
session state in a distributed store with `@cached`/`@stateful` access
so any instance can resume any session - because the honest constraint
of scale-to-zero is that instances are cattle, and state that lives on
them is lost state.

## Interview probes

- Walk a request through Knative when the revision is at zero pods, and
  name the component whose failure would hang it longest.
- Why does the KPA need two windows? Show the burst scenario where a
  60-second average undershoots by 5x.
- `containerConcurrency=1` with 1000 rps: how many pods, and what does
  the queue-proxy do at the boundary?
- Where exactly does Firecracker snapshot-restore fit in the data path,
  and what state must still be rebuilt?

## References

1. [Knative Serving documentation](https://knative.dev/docs/serving/) -
   revision/activator/autoscaler contracts as shipped.
2. Kleidman et al., "Cloudburst: Stateful Functions-as-a-Service",
   [arXiv:2001.04592](https://arxiv.org/abs/2001.04592) - the
   stateful-FaaS architecture and its ANNA storage backing.
3. [OpenShift Serverless architecture](https://docs.openshift.com/container-platform/4.14/serverless/architecture/architecture.html)
   - a production packaging of the Knative components with the same
   data-path diagram.
4. [Firecracker (this repo)](../virtualization/firecracker.md) - the
   microVM sandbox whose snapshot-restore path cold-start work targets.
