# Canary vs Blue-Green: Gradual Exposure Against Instant Cutover

## Overview

Both canary and blue-green deployment aim at the same target — ship a new version with zero downtime and a fast way back — and they differ in one design variable: **how traffic reaches the new version over time.** Blue-green provisions two complete production stacks. The old one (blue) serves everything; the new one (green) runs in parallel, passes its checks, and then receives 100% of traffic in a single router flip. Rollback is another flip — seconds, deterministic, independent of the new version's behavior. Canary instead shifts traffic progressively: 1%, then 10%, then 50%, then 100%, with automated analysis gates between steps comparing the new version's metrics against the old. Blast radius is proportional to the ramp; rollback is a weight change plus whatever the gate caught.

The fork is really a question about **risk exposure and detection**. Blue-green front-loads risk: the moment of cutover exposes every user at once, and its celebrated instant rollback is only instant if a human or alert *knows* to trigger it. Canary spreads risk over time and automates detection, but requires per-version telemetry of statistical quality and a ramp long enough to catch slow-burn regressions. This page runs the [handbook framework](./index.md) across the pair — mechanisms, the cost and database-migration interactions, stateful-service complications, and the dual-write edge case that turns both strategies into state-synchronization problems. The one-sentence preview: **blue-green buys deterministic rollback and pays double infrastructure plus all-at-once exposure; canary buys bounded blast radius and pays for metric infrastructure, ramp time, and a subtler failure mode — gates that pass on insufficient evidence.**

## Step 1: The Problem and Its Constraints

The abstract shape: a service with production traffic deploys a new version that passed its test suite; the residual risk is behavioral (performance under real load, integrations, data shapes). Constraints that decide the answer:

- **Blast-radius tolerance.** How many users may experience a regression, and for how long, before an abort? A payments API and an internal admin tool answer very differently.
- **Detection quality.** Do per-version error rates, latencies, and business KPIs exist, labeled correctly, with enough traffic for significance? Canary gates are only as good as this telemetry; without it, canary is a slower way to ship blind.
- **Rollback-latency requirement.** Is "seconds, deterministically" a hard requirement (incident-driven flips), or is "minutes, automated" acceptable and cheaper?
- **Infrastructure cost appetite.** Blue-green holds a full duplicate environment warm; canary holds roughly one extra replica-set-sized increment during the ramp.
- **State and session affinity.** Sticky users, long-lived connections, and in-flight work complicate both strategies differently; stateful services reshape the whole decision (see Step 5).
- **Database migration coupling.** Both versions must coexist against one schema; the migration discipline (expand–contract) is shared, but the *timeline* each strategy forces on it differs.

## Step 2: The Mechanisms

### Blue-green: two worlds, one switch

- **The flip is the whole trick.** A load balancer target group, an ingress weight, or a DNS change routes 100% of traffic from blue to green in one atomic step (see [blue-green deployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)). Because green ran warm and served smoke tests before the flip, "deployment" reduces to routing — cold-start and warm-up failures are caught pre-cutover.
- **Rollback is deterministic and version-independent.** Flipping back is the same atomic step in reverse; it works even when the new version is *so* broken it cannot serve its own health endpoint. This is the property incident commanders love: the rollback does not depend on diagnosing the failure first.
- **Cost is 2× during the transition window** — two full environments, both running, one idle-serving. For a large fleet this is real money; for a small service it is noise. The window's length is a process choice, and shortening it (cut, watch, decommission blue) trades away the cheap rollback.
- **Exposure is all-or-nothing.** Every user crosses to green simultaneously. A subtle regression — one that smoke tests miss and alerts need minutes to notice — hits everyone at once. Blue-green bounds the *rollback* time, not the *exposure*.
- **Config drift between stacks is the quiet failure.** Two environments invite divergence: a scaling setting tuned on blue during a holiday, a feature flag flipped on green only. The flip then changes *more* than the deploy, and the diff of what actually changed is unknown — the classic post-flip mystery regression.

### Canary: proportional exposure, automated evidence

- **Traffic weights do the shifting.** Weighted target groups, service-mesh routing, or ingress controllers split traffic by percentage; the canary cohort is random at the connection level. With [Kubernetes](../../cloud/kubernetes/deployments.md) the mechanism is typically two deployments (stable + canary) behind one weighted service.
- **Gates convert telemetry into promotion decisions.** Between ramp steps, automated analysis compares the canary's metrics — error rate, p99 latency, saturation, and ideally a business KPI — against the stable baseline over a fixed window; pass promotes the weight, fail aborts. This is canary's essential added machinery: metric pipelines, per-version labels, and an analysis definition someone maintains (see [canary releases](https://martinfowler.com/bliki/CanaryRelease.html) and [SLO-based gating](../../sre/slo-error-budget.md)).
- **Rollback is a weight drop — fast, but gated on detection.** Dropping the canary weight takes seconds. The catch: rollback latency is *detection latency + weight-drop*, and detection is only as fast as the metric window. A gate evaluating a 5-minute window can let a bad version serve at 10% for those five minutes — bounded, but not zero.
- **Statistical sufficiency is a real constraint.** At 1% of a low-traffic service, the canary sees too few requests to distinguish a 2× error rate from noise within any useful window. Low-traffic services cannot run meaningful canaries on error-rate gates — the strategy silently degrades to a slow blue-green.
- **Session affinity poisons the proportions.** Sticky routing pins a user to a backend; a 5% weight does not mean 5% of *users* — some users are 100% canary, others 0%. Gate metrics become sample-biased, and the edge cases below follow.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Blue-green | Canary |
|----------|------------|--------|
| Exposure shape | 100% at one instant | Proportional, over the ramp |
| Rollback | Deterministic flip, seconds; diagnosis-independent | Weight drop, seconds *after* detection |
| Detection | Manual/alert-driven, post-cutover | Automated gates during the ramp |
| Infrastructure cost | 2× full environment during window | ~+5–10% during ramp |
| Blast radius on regression | Everyone, until flip-back | Fraction served, bounded by ramp |
| Telemetry requirement | Basic fleet health | Per-version metrics, labels, significance |
| Traffic-volume requirement | None | Enough for statistical gates |
| Session affinity | Users pinned to a dying blue at drain | Proportions biased; sample skew |
| DB migration window | Compat must hold at the flip instant | Compat must hold across the whole ramp |
| Config drift risk | Two stacks diverge during window | Minimal — same stack, new replica set |

The **detection-location** mechanism deserves the arrow drawn: both strategies promise fast rollback, but they place *detection* differently. Blue-green's detection happens after cutover, in production, through the normal alerting path — its rollback is fast but its detection is human-speed. Canary's detection happens before full exposure, through purpose-built gates — slower per decision, but the decision is automated and the exposure is bounded. The strategies do not differ in whether you can go back; they differ in **who notices the regression, when, and how many users are holding the evidence**. That is why the decision hinges on telemetry quality more than on any routing feature.

## Step 4: When Each Wins

**Blue-green wins** when: traffic is too thin for statistical gates (low-traffic internal services, regional deployments); rollback must be deterministic and diagnosis-independent (the failure mode is catastrophic and detection is incident-driven); the environment is stateless and config can be template-locked; and the 2× cost during a short window is affordable. It is also the natural shape for infrastructure-level changes — runtime, kernel, node-pool migrations — where "a fraction of traffic" is the wrong axis and "old world vs new world" is the real fork.

**Canary wins** when: traffic volume gives gates significance; subtle, percentage-level regressions are the realistic risk (performance, ML model updates, dependency upgrades); blast radius must be bounded by construction; and the org maintains the telemetry and gate definitions. High-traffic stateless tiers with mature SLOs are the canonical case — the canary cohort is large even at 1%, and a 30-minute ramp catches most regressions before they reach half the fleet.

**The honest hybrid menu** — where production systems actually live:
- **Canary with a warm green.** Pre-provision the next environment (blue-green's cost) but promote it progressively (canary's exposure curve). You pay 2× for determinism *and* buy gradual exposure — the standard shape for high-stakes, high-traffic tiers.
- **Feature flags as the software-layer canary.** Deploy the new code to everyone, gate behavior per cohort with [flags](../../sre/feature-flags.md); the deployment is atomic (blue-green-like), the exposure is progressive (canary-like), and rollback is a config change. The coupling between feature rollout and deploy is then a choice, not an accident (see the atlas page on that coupling).
- **Dark launch before blue-green.** Green receives mirrored production traffic (read-only shadow) before the flip: canary-style evidence, blue-green-style cutover. Used heavily for capacity validation on the flip path.

## Step 5: Edge Cases and Counterexamples

- **Dual-write during transition.** Both stacks are live in either strategy's overlap window; if both write to shared systems (queues, databases, external APIs), side effects double: emails send twice, charges post twice, counters double-count. The classic fixes are all *write-gating*: only one stack writes while the other serves reads, or every write carries an idempotency key the sink deduplicates. The moment a service holds writable state, "deployment strategy" quietly becomes "distributed state-migration problem" — and the flip, not the code, is the moment the second writer appears.
- **Sticky sessions poison the canary's math.** With session affinity, 5% weight yields a canary cohort of maybe 12% of *users* (the newly-assigned) while long-lived sticky users never see it; gate metrics sample the biased cohort. Worse: draining blue resets every pinned session mid-checkout. Production answer: affinity only where the app demands it, ramp metrics computed per-user not per-request, and drain policies that treat session loss as user-visible impact.
- **The migration that broke blue.** The deploy includes a schema change; green migrates the database; the flip happens; blue — still running, still the rollback target — crashes on the new schema the moment it receives a request. Instant rollback flips to a version that can no longer read its own database. The discipline is expand–contract with [online schema changes](../../dbms/advanced/online-schema-change.md): expand (additive, backward-compatible), migrate data, deploy code that works on both shapes, and contract only after every old-version instance is decommissioned. Blue-green's binary timeline makes the contract step easy to schedule at the wrong moment; canary's long ramp stretches the compat window but also lengthens the time two code shapes hit one schema.
- **The gate that passed on morning traffic.** A canary ramps at 09:00 on weekend-level traffic; the gate window closes on clean metrics; promotion reaches 100% before the Monday peak — where the new version's cache-warming behavior sends p99 latency over SLO fleet-wide. Gates must cover the traffic cycles their metrics depend on; a ramp that never saw peak traffic has tested nothing about peak. The general lesson: canary evidence is only as representative as the traffic that generated it.
- **Stateful services: the flip that did not move the connections.** A WebSocket gateway on blue holds 80,000 live connections; the blue-green flip routes *new* connections to green, but existing ones stay pinned to blue for their lifetime. "Instant cutover" is now a connection-drain schedule, the two stacks run concurrently for hours (dual-write risk above), and rollback would bifurcate live state. Long-lived-connection services need explicit drain-and-migrate choreography — for them, neither strategy is the zero-downtime story its diagram promises.

## Step 6: Decision Framework

1. **Is traffic volume sufficient for per-version statistical gates?** No → blue-green (or flags); a canary without significance is a slow all-at-once deploy.
2. **Is rollback required to be diagnosis-independent?** Yes (catastrophic failure modes, incident-driven flips) → blue-green's deterministic flip.
3. **Is blast-radius bounding the dominant risk?** Yes (subtle regressions, high traffic) → canary with automated gates.
4. **Does the service hold writable state or long-lived connections?** Yes → neither diagram applies as-is: plan write-gating, drain, and dual-run choreography first.
5. **Is the database migration backward-compatible during the whole overlap?** Enforce expand–contract regardless of strategy; schedule the contract step after full decommission of the old version.
6. **Default in doubt:** canary on high-traffic stateless tiers with trusted SLO gates; blue-green for low-traffic, infrastructure-level, or instant-revert-critical paths; both behind the same migration discipline — and measure config drift between stacks as seriously as code diff.

## Interview Questions

1. **Blue-green promises instant rollback. What is the hidden assumption, and when does it fail?** That you *know* you must roll back. Detection runs through the normal alerting path after cutover; the flip is fast, the noticing is not. It also fails when rollback is impossible by construction — e.g., an incompatible schema migration broke the old stack, or dual-writes have already mutated shared state.
2. **Why can a low-traffic service not run a meaningful canary?** Gates decide on metric windows; at 1% of thin traffic the canary cohort is too small to distinguish a real regression from noise in any useful window. The strategy silently degrades to blue-green with extra steps — the correct choices are blue-green, feature flags, or a longer explicit bake.
3. **A canary's gates pass at 09:00 and the fleet regresses at Monday peak. What went wrong?** The evidence was unrepresentative: gates evaluated on non-peak traffic missed a peak-shaped behavior (cache warming, connection pool sizing, downstream saturation). Ramps must span the traffic cycles that drive the metrics — or promotion must be gated on reaching representative volume, not just on clean windows.
4. **Explain the dual-write problem in the overlap window and two fixes.** Both versions live and both write to shared systems, doubling side effects (duplicate charges, messages, notifications). Fixes: write-gating (one stack writable, the other read-only), or idempotency keys so sinks deduplicate. Stateful services turn deployment strategy into state-migration design.
5. **How does the database migration plan differ between the two strategies?** Both need expand–contract (additive schema first, contract after old code is gone). Blue-green concentrates the compatibility requirement at the flip instant — old code must work on the new schema or rollback dies. Canary stretches the requirement across the whole ramp: two code shapes coexist against one schema longer, so the compat window is longer but each instant is lower-risk.

## Key Takeaways

- The single variable is **exposure over time**: blue-green is all-at-once with deterministic rollback; canary is proportional with automated detection. Everything else — cost, telemetry, migration timelines — derives from it.
- Rollback speed is two numbers: detection latency plus the mechanical flip/weight-drop. Blue-green minimizes the second; canary minimizes the first.
- Statistical sufficiency is a hard prerequisite for canary: thin traffic cannot produce gate-grade evidence, and the strategy collapses into slow blue-green.
- Both strategies require the same database discipline — expand–contract with the contract step gated on full decommission of the old version — and both become state-migration problems under dual-writes and long-lived connections.
- Hybrids are the production norm: canary with a warm green, feature flags over atomic deploys, dark launches before flips — combinations that buy each strategy's strength while paying for it explicitly.

## Cross-References

- [Kubernetes Pod Lifecycle: Follow-up Tree](../followup-tree/kubernetes-pod-lifecycle.md) — the per-pod mechanics (readiness, termination, draining) both strategies ride on.
- [Feature Flags and Deployment Coupling: Connection Atlas](../connection-atlas/feature-flags-deploy-coupling.md) — how flag-driven rollout decouples from — and re-couples to — the deploy mechanics here.
- [Canary Releases](../../sre/canary-releases.md) — the operational playbook, including automated analysis patterns.
- [Feature Flags](../../sre/feature-flags.md) — the software-layer exposure control that decouples rollout from deploy.
- [SLOs and Error Budgets](../../sre/slo-error-budget.md) — the metric discipline canary gates consume.
- [Kubernetes Deployments](../../cloud/kubernetes/deployments.md) — weighted routing and replica-set mechanics in practice.
- [Online Schema Change](../../dbms/advanced/online-schema-change.md) — expand–contract mechanics behind the migration edge case.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
- [Martin Fowler: BlueGreenDeployment](https://martinfowler.com/bliki/BlueGreenDeployment.html) and [CanaryRelease](https://martinfowler.com/bliki/CanaryRelease.html) — the canonical definitions this page mechanizes.
