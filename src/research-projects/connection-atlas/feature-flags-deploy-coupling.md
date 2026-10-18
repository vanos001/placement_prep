# Feature Flags and Deployment Coupling: Releasing Without Deploying

## Overview

A deployment ships bytes; a release decides who sees behavior. Feature flags are the mechanism that splits those two events, and the split creates an entire subsystem: flag definitions live in a config store, SDKs evaluate them per request, rollout dashboards watch telemetry, kill switches revoke behavior mid-flight, and cleanup processes retire the branches when the experiment ends. The connection this page maps is that flags, deployments, rollouts, kill switches, and config stores are not five tools but one pipeline in which behavior is selected *per request* by evaluating rules against replicated state — while the deployed artifact stays constant. That inversion (code stable, behavior variable) is the source of both the pattern's power and its characteristic failures.

The coupling is bidirectional. Flags decouple release from deploy, but they also couple *runtime* to *configuration infrastructure*: a flag service outage becomes an application availability question, a stale SDK cache becomes a correctness question, and an un-pruned flag list becomes permanent config drift encoded in source control. This page states each system independently, names the shared principle (a runtime branch point over cached, replicated truth), marks where the analogy to ordinary configuration holds and breaks, works the arithmetic of a 1% rollout that still owns your p99, and lists the levers — flag lifecycles, percentage rollouts, targeting rules — that keep the pipeline sane.

## The Systems, Independently

**Feature flags and the flag store.** A flag is a named decision point in code (`if (flags.newCheckout) {...}`) plus a store that maps the flag name, under targeting rules, to a value for a given evaluation context (user ID, region, plan, request attributes). The store is replicated state: a control plane (database, dashboard, API) edits rules; edge servers or SDKs poll or subscribe to updates and cache them locally; evaluation happens in-process at microseconds. Flags come in distinct species with different lifecycles: *release* flags (until a feature ships), *experiment* flags (until an A/B test concludes), *ops/kill-switch* flags (indefinitely — they exist to be flipped during incidents), and *permissioning* flags (long-lived entitlements that are really just configuration). The species distinction matters because each species wants a different expiration policy, and the failures below come mostly from species confusion.

**Deployment, gradual rollout, kill switches, cleanup.** The deployment pipeline builds and ships a version; a gradual rollout (canary or percentage) widens the set of requests that evaluate the flag to `true` — 1%, 10%, 50%, 100% — with automated gates reading error rate and latency between steps. A kill switch is a flag whose `false` path is the last-known-good behavior, kept wired so an incident can turn a feature off in seconds instead of the minutes-to-hours of a rollback. Cleanup is the retirement phase: once a release flag is at 100% (or an experiment concludes), the branch is removed from code, the flag is deleted from the store, and the pair of changes ships together. Nothing about cleanup is optional; it is the phase that prevents the flag system from decaying into a second, undocumented configuration language.

## How the Chain Feeds Itself

The pipeline is a loop with five handoffs. (1) *Code → flag*: a developer wraps new behavior in a flag and deploys it dark — the code runs everywhere but evaluates `false`, so deployment carries zero release risk. (2) *Flag store → SDK*: rules propagate to the fleet, where each process caches them; evaluation is a local lookup, not an RPC. (3) *Rollout controller → store*: percentage and targeting rules step up as telemetry gates pass. (4) *Telemetry → decisions*: metrics segmented by flag value feed both the automated gates and the human dashboard; a rollout that cannot be segmented by flag state is flying blind. (5) *Decision → cleanup or kill*: success promotes to 100% and schedules cleanup; failure either drops the percentage or flips the kill switch.

Shared invariants make the loop trustworthy. *Determinism*: the same context must evaluate the same way on every server, every time, or a user's experience flickers between variants mid-session. *Default safety*: when the store is unreachable, the SDK falls back to a shipped-in-binary default that is always the safe behavior — the flag system must fail toward the old world. *Segmentability*: every metric the rollout gate reads must be attributable to a flag state, which requires logging the evaluated variant alongside the request.

## The Shared Principle

**A feature flag is a runtime branch point whose decision table is replicated, cached state; percentage rollout is consistent hashing; and every flag evaluation is a read from a cache with a staleness budget.** Each clause is a principle the atlas has met elsewhere. The evaluation is a cache read: SDKs hold a local copy of the rules, refreshed on a poll interval or a push, and serve thousands of evaluations per second from memory exactly like a config cache — the freshness question ("how stale may my view of the rules be?") is identical to CDN or DNS staleness. Percentage rollout is consistent hashing: bucket the user ID space deterministically (hash to 0–9999, compare against the percentage threshold) so that growing 10% → 20% *keeps* the original 10% users in the treatment group — a monotone bucket expansion, the same property that lets consistent hashing add servers without reshuffling every key. The kill switch is statistical failure detection feeding a control action: telemetry detects the regression, the switch sheds load from the bad code path, and the relationship "detect → decide → shed" is the load-shedding loop of any overloaded system.

## Where the Coupling HOLDS and BREAKS

| Aspect | HOLDS | BREAKS |
|---|---|---|
| Config analogy | Flags are config values selected per context; same caching, layering, and staleness questions | Config is *uniform* (all replicas want the same value); experiments are deliberately *non-uniform*, so "eventually consistent everywhere" is not enough — bucket assignment must be deterministic per user across replicas and time |
| Deploy analogy | A 100%-flagged release behaves like a normal deploy | Rollback semantics invert: reverting code redeploys everything, flipping a flag redeploys nothing; teams that stop practicing real rollbacks lose the muscle exactly when the flag system itself is the incident |
| Caching analogy | SDK flag cache ≈ config/CDN cache with a refresh interval | The cost of staleness is asymmetric per species: a stale *experiment* assignment wastes statistical power, but a stale *kill switch* leaves a burning feature on during an incident — same mechanism, wildly different severity |
| `if` in code | A flag is a branch, so review treats it like a branch | A flag is a branch whose decision table lives outside the repo; static analysis, type systems, and tests see only one path unless tests inject flag states explicitly |

## Failure Propagation

**Defaults after expiry and flag-service outage.** If the SDK cannot refresh (control plane down, network partition), it serves the last cached ruleset — fine for minutes, dangerous for hours, because the fleet is now frozen mid-experiment and nobody is sure which rules are live. If the SDK cold-starts with no cache (fresh pod), it must use the compiled-in default; a flag whose default is "on" silently enables unreleased behavior for every new pod during an outage. The propagation rule: *the flag system's availability becomes the application's release-state availability*, which is why defaults must be chosen at flag-creation time, reviewed like code, and biased to the old behavior for release and ops flags.

**Stale flags as config drift and the missing kill switch.** Cleanup debt compounds mechanically: each abandoned flag adds a branch that future readers must interpret, tests must cover, and bundles must ship. At hundreds of live flags, engineers stop knowing which flags are load-bearing, so nobody dares delete any — and the *kill switches rot first*, because they look dead until the day you need them. The worst propagation is silent: a team cleans up a "finished" flag by deleting the store entry but not the branch, the SDK falls back to the default, and the default was never updated to the shipped behavior — a percentage of traffic quietly reverts. Flag debt is config drift with a code comment on it.

**Flag interactions as combinatorial debt.** Flags do not compose: with 30 live flags the behavioral space is 2³⁰ potential configurations, and tests, by default, exercise exactly one of them — the all-defaults state. Two flags that each pass testing can still interact (flag A changes the request shape that flag B's code path parses), and the interaction fires only in the corner of the matrix some rollout happens to create. The propagation rule is that the state space grows multiplicatively while testing effort grows linearly, so mature shops restrict it structurally: dependency declarations between flags ("B requires A off"), mutually exclusive groups enforced by the store, and a hard ceiling on simultaneously live flags per service — not because any single flag is dangerous, but because the *product* of them is untestable.

## A Concrete Worked Example

**A 1% rollout still owns your p99.** Ship a checkout change whose p99 is 800 ms where the old path is 200 ms, and ramp it to 1% of traffic. The fleet's response-time distribution is now a mixture: 99% of requests in the fast population, 1% in the slow one. The 99th percentile of the mixture sits exactly at the boundary — the top 1% of requests are all from the slow bucket — so fleet p99 ≈ 800 ms even though 99% of users see no change. Any SLO or gate keyed on *unsegmented* p99 now reads the experiment as a fourfold regression and blocks the rollout; the fix is segmentation by flag state, not smaller percentages. The same arithmetic explains why canary error budgets are computed per-bucket: 1% traffic at 5% error rate contributes only 0.05 percentage points of fleet-wide error rate, so fleet error-rate gates are nearly blind to canary regressions — percentile gates over-detect, average gates under-detect, and only per-variant metrics see the truth.

**Deterministic bucketing, with numbers.** With 10 million users and a hash of the user ID mapped to 0–9999, 1% rollout = buckets 0–99 ≈ 100,000 users; ramping to 10% = buckets 0–999 keeps those 100,000 users in treatment and adds ≈ 900,000. Random per-request assignment would instead put each request in treatment with probability 1%, splitting a single user's session across variants — corrupting both the experiment's statistics and any server-side session state the two variants treat differently.

## Design Levers

- **Flag lifecycles as first-class metadata.** Every flag carries a species (release/experiment/ops/permission), an owner, an expiry or review date, and a documented safe default. Expiry alerts fire before the flag becomes archaeology; creation without metadata is rejected by the store.
- **Percentage rollout with deterministic, monotone bucketing.** Consistent-hash the stable identifier, keep buckets monotone across ramps, and pin experiment assignment per user (sticky) so sessions do not straddle variants.
- **Targeting rules instead of code branches.** Region-, plan-, and account-level conditions live in the rule table, not in more `if` statements, so one flag serves many audiences and the cleanup surface stays one row wide.
- **Kill switches budgeted like capacity.** Ops flags are reviewed quarterly under the same discipline as on-call runbooks: flip it in a game day or delete it.
- **Defaults fail toward the old world.** Compiled-in fallbacks default to last-known-good for release and ops flags; "flag service unavailable" must never mean "new behavior everywhere."

## Interview Questions

1. "Deploy is not release" — explain the sentence with a flag lifecycle, then name two new failure modes the decoupling introduces that a plain deploy does not have.
2. Design a percentage rollout that keeps a user's variant stable across a ramp and across server restarts. Why is per-request randomization unacceptable, and what does consistent hashing buy you?
3. Your flag service goes down for an hour. Walk through what each flag species does in that hour with correct defaults, and what goes wrong with wrong defaults.
4. The codebase has 400 live flags, 120 attached to shipped features. Propose a cleanup program: how do you decide what is safe to delete, and how do you keep kill switches from being deleted with the rest?
5. A 1% canary shows 10× error rate in its own segment but fleet error rate barely moves. Why do fleet-wide averages hide canary regressions, and what gate design sees them?

## Key Takeaways

- Flags split deploy from release by making behavior a per-request evaluation over replicated rules — a cached-lookup decision table, with all the staleness and default semantics caches always carry.
- Percentage rollout is consistent hashing over user identifiers: deterministic, monotone bucket expansion; determinism is what makes ramps safe and experiments statistically valid.
- The flag system's failure modes propagate inward: control-plane outages freeze rollouts, cold starts consult compiled-in defaults, and wrong defaults turn an infra outage into a release accident.
- Cleanup debt is config drift in source control; kill switches are the part of the debt that costs the most exactly when it has rotted the most.
- Segment every gate by flag state: unsegmented p99 over-reacts to small rollouts and fleet averages under-react — only per-variant telemetry sees the rollout.

## Cross-References

- [./dns-cdn-routing.md](./dns-cdn-routing.md) — DNS and CDN Routing — every addressing layer is cached truth with a TTL; flag rulesets propagate under the same staleness budget.
- [./load-balancing-partitioning.md](./load-balancing-partitioning.md) — Load Balancing and Partitioning — consistent hashing and rendezvous hashing are the bucketing machinery behind stable percentage rollouts.
- [./observability-pipeline.md](./observability-pipeline.md) — The Observability Pipeline — rollout gates are consumers of the telemetry fan-in; segmentation by flag state is a join across that pipeline.
- [./tcp-distributed-failure.md](./tcp-distributed-failure.md) — TCP and Distributed Failure — the kill switch loop (detect statistically, decide, shed) is the same detect-and-respond discipline as timeouts and load shedding.
- [../assumptions-hunt/caching.md](../assumptions-hunt/caching.md) — Caching Assumptions Audit — the "it is cached so it is eventually right" assumptions that flag SDKs silently inherit.
- [../../networks/cdn/how-it-works.md](../../networks/cdn/how-it-works.md) — How CDNs Work — TTL, revalidation, and stale-while-revalidate mechanics that flag-cache refresh is a special case of.
