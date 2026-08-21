# Progressive Delivery

## Overview

Progressive delivery is the family of techniques that ship new code **without exposing every user to the new version at once**. The through-line is the same: shift traffic gradually, measure error rates and business metrics, and roll back automatically if the new version regresses. The differences are in **what** gets shifted and **how** the shift is decided.

This page covers the four core patterns — **blue-green**, **canary**, **dark launch**, **shadow deploy** — and how feature flags unify them. We'll look at the tooling (Flagger, Argo Rollouts, LaunchDarkly) and the metrics-based rollback that makes progressive delivery safer than `kubectl apply`.

## The Four Patterns at a Glance

```
┌────────────────┬────────────────────┬─────────────────────────────┐
│ Pattern        │ What shifts?       │ Users exposed to new code   │
├────────────────┼────────────────────┼─────────────────────────────┤
│ Blue-green     │ 100% at once       │ All, but only after verify  │
│ Canary         │ % traffic          │ Gradual: 1% → 5% → 25% → 100%
│ Dark launch    │ Feature flag       │ All users, hidden feature   │
│ Shadow deploy   │ Mirrored traffic   │ None — new code runs in copy│
└────────────────┴────────────────────┴─────────────────────────────┘
```

## Blue-Green Deployment

Two identical environments: **blue** (live) and **green** (idle, or being prepared). Deploy the new version into the idle environment, verify it, then **flip the router** so all traffic moves from blue to green in a single switch. The previous environment stays warm as the rollback target.

```
                ┌──────────────────────────────────┐
                │           Load Balancer           │
                └────────────┬──────────────────────┘
                             │  active = blue (live)
        ┌────────────────────┴───────────────────────┐
        │                                            │
   ┌────▼─────┐                                ┌─────▼─────┐
   │  BLUE    │  ← 100% of traffic             │  GREEN    │
   │ v1.0     │                                │  v1.1     │
   │ (live)   │                                │  (idle)   │
   └──────────┘                                └───────────┘

   After deploy v1.1 into GREEN and verify:

                ┌──────────────────────────────────┐
                │           Load Balancer           │
                └────────────┬──────────────────────┘
                             │  active = green (live)
        ┌────────────────────┴───────────────────────┐
        │                                            │
   ┌────▼─────┐                                ┌─────▼─────┐
   │  BLUE    │                                │  GREEN    │
   │ v1.0     │                                │  v1.1     │
   │ (idle)   │  ← ready for rollback          │  (live)   │
   └──────────┘                                └───────────┘
```

Properties:

- **Atomic switch** — every user moves at once; no version skew within a single request fan-out.
- **Instant rollback** — flip back to the previous environment in seconds, no redeploy.
- **Capacity cost** — two environments must be warm; effectively 2× compute.
- **Schema constraints** — the database is shared; a backward-incompatible migration breaks both environments.

The schema constraint is the main reason blue-green is rarely used in pure form for stateful services. It works best for stateless front-ends and read-only services.

A simplified Kubernetes implementation: two `Deployment` objects behind one `Service`, with the `Service` selector flipping:

```yaml
# Service points at blue by default
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  selector:
    app: frontend
    slot: blue      # flip to green to switch traffic
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-blue
spec:
  replicas: 4
  selector:
    matchLabels:
      app: frontend
      slot: blue
  template:
    metadata:
      labels:
        app: frontend
        slot: blue
    spec:
      containers:
      - name: app
        image: frontend:1.0
```

To promote green: patch the `Service` selector from `slot: blue` to `slot: green`. To roll back: patch it back.

## Canary Deployment

A canary release ships the new version to a small percentage of users, watches metrics, and either proceeds (gradually enlarging the cohort) or rolls back (drops the new version entirely). The name is from coal mines — canaries detect danger before humans.

```
User traffic 100%
   │
   ├──► 90% → v1.0 (stable)
   └──► 10% → v1.1 (canary)   ← measure error rate, latency, conversions
            │
            ├──► metrics OK    → expand: 10% → 25% → 50% → 100%
            └──► metrics bad   → abort: drop canary, all traffic to v1.0
```

The crux of canary is **the metric-driven decision**. Without metrics and an automated rollback, a "canary" is just a slow rollout with no safety benefit — by the time a human notices, the damage is done. Argo Rollouts and Flagger encode this as a `AnalysisTemplate` that runs on a schedule and compares canary vs stable.

A Flagger canary in YAML:

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: frontend
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  service:
    port: 80
    targetPort: 8080
  progressDeadlineSeconds: 60
  analysis:
    interval: 1m              # run analysis every minute
    threshold: 5              # 5 consecutive bad analyses → rollback
    maxWeight: 50             # cap canary at 50% before manual approval
    stepWeight: 10            # add 10% per analysis cycle
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99               # require >= 99% success on canary
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500              # require p99 <= 500ms on canary
      interval: 1m
    webhooks:
    - name: rollout-approval
      type: pre-rollout
      url: https://slack-bot/approve
```

The flow: deploy new `ReplicaSet`, route 10% to it, wait 1 minute, check that success rate ≥ 99% and p99 ≤ 500ms. Pass → step to 20%. Fail five times in a row → rollback to the previous `ReplicaSet`.

### What metrics to gate on

- **Error rate**: 4xx/5xx as a percentage of total requests. Tightly correlated with regressions.
- **Latency p99**: regression in tail latency is invisible in p50. Canary must check the tail.
- **Business metrics**: conversion rate, checkout completion, items per cart. A "successful" deploy with 10% lower conversion is a failed deploy.
- **Resource metrics**: CPU, memory, GC time. A new memory leak shows up here before error rate spikes.

### The "two-sample comparison" pitfall

Comparing canary metrics against stable isn't trivial. The canary serves 10% of traffic; its sample size is smaller, so variance is higher. A 99% success rate on stable with 1000 requests vs 98.5% on canary with 100 requests is **not** statistically significant. Flagger and Argo Rollouts use statistical tests (Mann-Whitney U, KS test) or simple threshold windows to avoid false-positive rollbacks. The naive "any drop rolls back" rule is too sensitive — it will roll back healthy deploys because of normal noise.

## Dark Launch

A dark launch ships the new code path **in production** but **doesn't expose it to users**. The new code runs (often in shadow, see below) and produces real results, but the UI/feature flag hides the output. The team can verify production-scale behavior — load, correctness, downstream integrations — before flipping the user-visible switch.

The classic example is Facebook Messenger's 2010 dark launch: the new chat backend ran for months processing real messages (mirrored from the old backend) before any user saw the new UI. By the time the switch happened, the new backend had handled billions of messages.

Pattern: feature flag wraps the new code path.

```python
def process_checkout(user_id, cart):
    # Old path: always runs
    result = legacy_charge(user_id, cart)

    # Dark launch: new path runs in parallel for flag-enabled users,
    # but its result is logged, not returned.
    if flag_client.eval("new_payment_processor.enabled", user_id,
                        default=False):
        try:
            new_result = new_charge(user_id, cart)
            metrics.incr("new_payment.success")
            log_comparison(result, new_result, user_id)
        except Exception as e:
            metrics.incr("new_payment.error", tags={"type": type(e).__name__})
    return result
```

The flag is configured to enable the new path for **a small cohort** (or just for internal users), and the comparison output is logged to a metrics pipeline. When the new path is healthy and matches the old path on enough samples, flip the flag for everyone.

## Shadow Deployment (Traffic Mirroring)

Shadow deployment routes a copy of production traffic to the new version. The new version's responses are **discarded** — the user only sees the stable version's response. The new version receives real load, real payload variety, real edge cases, without risking any user.

```
User request ──┬──► stable (v1.0) ──► response ──► user
               │
               └──► shadow  (v1.1) ──► response discarded
                    (load-tested in production)
```

Istio's traffic mirroring makes this trivial:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: frontend
spec:
  hosts:
  - frontend.example.com
  http:
  - route:
    - destination:
        host: frontend-stable
        port:
          number: 80
      weight: 100
    mirror:
      host: frontend-canary
      port:
        number: 80
    mirror_percentage:
      value: 100.0   # mirror 100% of traffic to the canary
```

Caveats:

- **Idempotency required.** Mirrored requests are real requests; if they have side effects (POST /charge), the new version will double the side effects. Either make mirrored calls read-only, strip authentication, or run a special "shadow" client that doesn't write.
- **Capacity cost.** Mirroring 100% of traffic means the canary needs the same capacity as stable; this is rarely economical. Usually mirror 10–50%.
- **Comparison tooling.** A shadow deploy without comparison is just a load test. You need a tool that diffs the responses and reports mismatches.

## Feature Flags Unify Progressive Delivery

Feature flags are the runtime switch behind all four patterns:

- **Blue-green**: the flag selects environment.
- **Canary**: the flag selects the cohort percentage.
- **Dark launch**: the flag is `enabled=false` for users but `enabled=true` for the new code path.
- **Shadow**: the flag enables the mirroring pipeline.

The advantage of unifying on flags is that **rollout and rollback are runtime operations**, not deploys. A bad deploy with `kubectl apply` requires another `kubectl apply` to roll back, plus the CI/CD pipeline time. A flag flip is a single API call (or config change) and takes effect within seconds. LaunchDarkly, Unleash, and OpenFeature all expose this as a feature of the platform.

```python
from ldclient import LDClient

client = LDClient(sdk_key="...")
# Rollout percentage is a server-side flag; flipping it changes
# the cohort for all running instances immediately.
def get_version_for_user(user_id):
    return client.variation("checkout.v2.enabled",
                            {"key": user_id}, default=False)
```

A flag's rollout strategy in LaunchDarkly:

- **Boolean flag** with a **percentage rollout** rule: 5% on first, ratcheted up to 100% over days.
- **Targeted rules**: enable for `internal-users` segment first, then `beta-users`, then everyone.
- **Prerequisites**: a flag can require another flag, so "new-checkout" requires "auth-v2" first.

The critical pattern: **never set a flag's default to `true`** until you've validated in production. The default is what every new instance sees at startup when the flag service is unreachable (see [graceful degradation](./graceful-degradation.md)). A `true` default silently rolls out the feature.

## Tooling

| Tool | Pattern | Notes |
|---|---|---|
| **Argo Rollouts** | Canary, blue-green | Kubernetes controller; replaces `Deployment` with `Rollout`; built-in analysis templates |
| **Flagger** | Canary | Kubernetes operator; works with Istio/Linkerd/NGINX/Contour; integrates with Prometheus |
| **LaunchDarkly** | Feature flags | SaaS; flag-driven canaries, dark launches, kill switches |
| **Istio** | Shadow (mirroring) | Service mesh; `mirror` directive on `VirtualService` |
| **Envoy** | Shadow, canary | L7 proxy with traffic mirroring and weighted routing |
| **Keptn** | Canary with quality gates | Open-source; sequence-based delivery with SLO evaluation |

The Kubernetes-native tooling (Argo Rollouts, Flagger) integrates with Prometheus so the canary decision can use any metric you can query in PromQL. The flag-tooling (LaunchDarkly) is more flexible but operates at the application layer — your code has to call `variation()`.

## Common Pitfalls

1. **Canary without metrics** — a slow rollout with no automated rollback is just a slow outage.
2. **Rolling out 100% on first green** — defeats the point of canary. Always start at 1–5%.
3. **Mismatched cohort** — canary routes by header or user ID hash; ensure the same user always lands on the same version, or you'll see "intermittent" bugs that are actually version-skew bugs.
4. **Long canary windows with hotfix pressure** — a canary that runs for a week blocks emergency hotfixes (which would be a third version live at once). Keep canary windows short, or have a process for aborting cleanly.
5. **Shadow with side effects** — mirroring `POST /charge` will charge the user twice. Mirror only idempotent or read-only calls, or strip the side effect from the mirrored copy.
6. **Schema-mismatched versions** — canary and stable share a database; a migration that breaks stable breaks canary too. Use backward-compatible migrations (expand-then-contract).
7. **Feature flag defaults to `true`** — silent rollout when the flag service is down. Defaults must be the pre-flag behavior.
8. **No kill switch** — a flag that lets you turn the feature on should also let you turn it off instantly. Plan the off path, not just the on path.

## Interview Questions

### Q: What's the difference between blue-green and canary?

Blue-green switches 100% of traffic at once between two environments, after verifying the new environment. Canary routes a small percentage to the new version, measures, and gradually enlarges. Blue-green is atomic and instant-rollback but has 2× capacity cost and risks full exposure on the switch; canary has gradual exposure and metrics-driven rollback but requires traffic splitting (mesh or load balancer) and statistical comparison. Canary is preferred when you can't verify the new version offline and need real-traffic signal to decide.

### Q: How does a shadow deploy differ from a dark launch?

In shadow deploy, real traffic is **mirrored** to the new version; the new version processes it and its responses are discarded. The user only sees the stable version. In a dark launch, the new code path runs in the **same** process as the stable one (not mirrored) but the result isn't shown to users — the feature is hidden behind a flag. Shadow tests the new version as a whole system; dark launch tests a specific new code path inside the existing system. Shadow is heavy (needs duplicate capacity); dark launch is light (in-process).

### Q: How do you prevent canary false-positive rollbacks?

Canary metrics have higher variance at small traffic shares. Use statistical tests (e.g., Mann-Whitney U for distributions, or simple confidence intervals) instead of "any drop rolls back". Tune the threshold window (`threshold: 5` consecutive failures) so a single noisy minute doesn't trigger a rollback. And gate on multiple metrics — a transient p99 spike on canary but stable error rate is likely noise; both spiking is a real regression.

### Q: How would you dark launch a new payment processor?

Ship the new code path alongside the old one, gated by a feature flag that's `enabled=false` for all users by default. For a small cohort (internal users first, then beta users), set the flag to `enabled=true` — both old and new processors run, but only the old result is returned to the user. The new result is logged with a correlation ID so we can compare old-vs-new for every charge. After enough matches (and zero mismatches), flip the flag for all users. Throughout, the new processor's error rate is on a dashboard with an alert — if it exceeds the old processor's, we stop the rollout.

### Q: Why are feature flags the unifying abstraction for progressive delivery?

Every pattern — blue-green (flag selects environment), canary (flag selects cohort %), dark launch (flag is `false` for users, `true` for code path), shadow (flag enables mirroring) — is a runtime routing decision. Flags make routing a runtime operation rather than a deploy operation, so rollouts and rollbacks take seconds instead of pipeline minutes. They also decouple release from deploy — you can deploy a new version and leave the flag off for weeks before turning it on, separating "code is in production" from "users see the new behavior".

## References

- Argo Rollouts documentation — https://argo-rollouts.readthedocs.io/
- Flagger documentation — https://docs.flagger.app/
- LaunchDarkly documentation: *Feature flag concepts* — https://docs.launchdarkly.com/sdk/concepts/flags
- Martin Fowler: *CanaryRelease* — https://martinfowler.com/bliki/CanaryRelease.html
- Martin Fowler: *FeatureToggles* (a.k.a. Feature Flags) — https://martinfowler.com/articles/feature-toggles.html
- Istio documentation: *Traffic Mirroring* — https://istio.io/latest/docs/tasks/traffic-management/mirroring/
- Kubernetes documentation: *Deployments* and rolling update strategy — https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- OpenFeature: *Feature flagging specification* — https://openfeature.io/
- Charity Majors: *Canary vs Blue-Green vs Rolling* — https://honeycomb.io/blog/canary-vs-blue-green-vs-rolling-deployments
- Google SRE Book, Chapter 27: *Reliable Product Launches at Scale* (staged rollouts, canary) — https://sre.google/sre-book/reliable-product-launches/

## Related Topics

- [Health Check Patterns](./health-check-patterns.md) — probes that gate canary promotion and rollback
- [Graceful Degradation](./graceful-degradation.md) — flags double as degradation switches
- [Retry and Timeout Patterns](./retry-timeout.md) — required when canaries expose new latency profiles
- [Microservices](./microservices.md) — service mesh primitives for traffic shifting and mirroring
- [Idempotency](./idempotency.md) — required for safe shadow and dark-launch side-effecting calls
