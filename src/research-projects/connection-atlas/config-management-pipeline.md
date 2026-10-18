# Configuration Management as a Distribution Pipeline

## Overview

Every nontrivial system reads its behavior from somewhere else: files baked into images, environment variables injected at boot, rows in a settings database, entries in a feature-flag store, secrets pulled from a vault at startup and again at rotation time. Each of those is a *replica of intent* — a copy of "how the system should behave" that must be propagated, cached, and eventually invalidated. Configuration management is therefore not a files-and-formats problem but a data distribution problem: you are running a replicated store with layered precedence, per-consumer caching, and rollout semantics, whether or not you bought software with that name.

The failure modes are the ones any replicated store exhibits, translated into ops dialect: half-reloaded processes where one subsystem re-read the new config while another holds the old (a split-brain *inside one process*), stale replicas that lag a rollout wave and silently behave differently from their neighbors, and secrets rotations that outrun the connection pools holding the old credentials. Blast radius is the config system's defining metric — one bad default pushed to a global layer can take down every service that inherits it, which is why the levers that matter are distribution levers: versioned config, atomic swap, canary rolls, and validation gates, rather than prettier file formats. This page maps where config actually lives, how changes propagate through the layers, and where the analogy to caching and replication holds and breaks.

## The Systems, Independently

**Config sources and where config actually lives.** Production behavior is governed by at least five stores with different semantics: (1) *static files* — defaults compiled or shipped with the artifact, versioned in git, immutable per release; (2) *environment variables* — injected at process start by the scheduler or container runtime, read once, invisible to restarts of neighbors; (3) *dynamic config services* — key-value stores (etcd, ZooKeeper, Consul, or a SaaS config service) watched by SDKs and hot-reloaded; (4) *database-backed settings* — rows read per request or cached with a TTL, often per-tenant; (5) *secrets managers* — vaults holding credentials with their own access control, audit, and rotation schedules. Each store answers "when can a change take effect?" differently: never-without-redeploy, at-next-restart, on-watch-event, on-next-read, and on-next-rotation, respectively. A change's true blast radius is the union of the consumers across all five.

**Env layering and precedence.** Config resolution is a lookup through a precedence stack — compiled default ← file ← environment ← dynamic service ← per-request/per-tenant override, with the exact order a per-organization decision that must be written down and enforced. Layering exists so each layer can be owned and reviewed differently, but it creates the classic hazard: a value can be *shadowed* by a layer nobody remembers setting, so the effective value at runtime differs from the value in the file everyone is editing.

**Secrets, hot reload, and blast radius.** Secrets are config with an adversarial audience: they must be distributed with least privilege, rotated on schedule, and never written to logs or images. Hot reload is the propagation mechanism for the dynamic layers: a watcher receives a change and swaps it into a running process. Blast radius engineering is the practice of deciding, per config key, *who may be affected and how fast* — instance-scoped, service-scoped, fleet-scoped, or global — and wiring the rollout mechanism to match.

## How the Changes Propagate

A config change travels: author → review (diff of the effective config, ideally computed against the *resolved* layered view) → versioned store (config is committed like code, immutable entries addressed by version) → control plane → per-consumer propagation (watch event, poll interval, or sidecar push) → in-process application (atomic swap into the live struct) → verification (health check or canary evaluation of the new effective config). The two properties that make this safe are **atomicity** — a process adopts version N of the whole config, never a piecemeal mixture of keys from N and N-1 — and **verifiability** — each process can report "I am running config version N" so the rollout dashboard is a replication-status view, exactly like replica lag in a database.

Shared invariants across all stores: *config is data read far more often than written*, so its architecture is a read-optimized cache with invalidation; *the effective value, not the edited value, is what production executes*, so every tooling and review decision must operate on resolved, layered output; *startup and steady state must agree*, meaning a process that crash-loops and reloads config at boot must land in the same state as one that hot-reloaded it — divergence between the cold path and the warm path is one of the most common and least tested config bugs.

## The Shared Principle

**Every config store is a replicated, layered cache of intent, and every config change is an invalidation problem: the propagation machinery — watch, poll, TTL, push — is interchangeable with the replica-propagation machinery of any caching system, and the staleness semantics you choose *are* the design.** This is the atlas's caching lens applied to behavior: files are the immutable base layer, env vars are boot-time snapshots, dynamic services are write-through stores with watch-based invalidation, DB settings are per-TTL caches, and secrets are leases that must be renewed. Equally, the *layering* is the DNS analogy from [dns-cdn-routing.md](./dns-cdn-routing.md): a hierarchical namespace where a nearer, more specific record overrides a farther, more general one, and where a forgotten override at a mid-layer is the source of "but it works in staging" bugs. And the *rotation* of secrets is the lease-renewal pattern of [auth-identity-session.md](./auth-identity-session.md): credentials are time-bounded grants, and every consumer must be built for the grant expiring — connection pools that never re-read credentials are leases held past expiry.

## Where the Analogy HOLDS and BREAKS

| Aspect | HOLDS | BREAKS |
|---|---|---|
| Replication | Propagation, lag, convergence, and "which version am I on?" all transfer | Consumers are not passive replicas: they *act* on config, so a stale replica is not merely slow — it authorizes the wrong thing, routes to the wrong pool, or speaks to the wrong database |
| Caching/TTL | TTLs bound staleness and are a legitimate tool | Config usually wants *push-based* invalidation, not TTL polling: a TTL of minutes means a rollback takes minutes, which is an eternity during an incident |
| Deployment | Versioned config + atomic swap behaves like an artifact rollout | There is no "restart the config": config changes take effect in long-lived processes mid-flight, so in-flight requests straddle versions unless the process snapshots config per request |
| Precedence/layers | Hierarchical override matches DNS-style delegation | Shadowing is silent: unlike DNS, there is no protocol error when a mid-layer overrides unexpectedly — only resolved-config diffs reveal it |

## Failure Propagation

**Half-reloaded processes.** A hot-reload handler updates the logging subsystem's config but the HTTP client's connection pool was built at startup holding the old timeout — the process now behaves like two machines stitched together. Worse is the *stitched-together fleet*: a rollout wave reaches 80% of replicas; requests hash across both populations; retries hop from an updated replica (new retry budget) to a stale one (old budget) and the effective behavior is neither version's — the compound behavior of a mixed fleet, which no single version's tests ever exercised. Propagation rule: *any consumer that captures config by value at a different moment than its neighbors becomes, temporarily, a different service.*

**Stale replicas and secret rotation.** Secrets turn staleness into outages on a schedule: rotate the database password; every process that cached a connection pool with the old credential keeps serving from live connections, then fails one-by-one as connections cycle — an outage that starts minutes after the "successful" rotation and looks like a traffic problem. The half-reload variant: the app re-read the new secret but the sidecar proxy or the batch job pool did not. And the blast-radius rule cuts here hardest: a bad value in a per-instance layer damages one replica; the same mistake in a global default inherits into every service — config inherits *downward*, so errors at high layers propagate to consumers that never opted in.

## A Concrete Worked Example

**A rollout wave and its arithmetic.** Fleet of 2,000 replicas; config service pushes at 100 replicas/minute; full propagation is 20 minutes. During that window, any cross-replica interaction — retry, fan-out, queue redelivery — can pair version N with version N-1. Suppose version N changes a gRPC deadline from 500 ms to 50 ms: a fan-out of 8 calls served by mixed replicas has a latency profile with a bimodal distribution and a retry pattern tuned for the wrong mode; the tail client sees `DEADLINE_EXCEEDED` from new replicas and 500 ms waits from old ones, so its own timeout (600 ms) now fires *after* the upstream already retried — retry amplification, born entirely from a 20-minute propagation window. The fixes are distributional: pause-based canary (1% of fleet, evaluate, then wave), a "drain" step that verifies 100% adoption before enabling the behavior that *depends* on the new value, or making the consumer handle both versions explicitly (feature-flag the *behavior*, not just the value). Contrast atomic swap: the process receives config version N as one immutable snapshot and switches its pointer in one assignment; requests that started under N-1 finish under N-1 because they captured the old snapshot at admission — per-request config capture is the transactional boundary.

**Secret rotation done right, in numbers.** Two credentials valid in overlap: issue `secret-v2` while `secret-v1` still authenticates; roll writers to v2 within the overlap (say 24 h); then revoke v1. Consumers with hot-reload pick v2 up on their watch interval (≤60 s); consumers with pools re-create connections on next reconnect using a secret *provider* (a function called at connection time), not a secret *value* captured at boot. The overlap window is the lease renewal the whole scheme lives on.

## Design Levers

- **Versioned config with atomic swap.** Config entries are immutable and content-versioned; processes load whole snapshots and switch atomically; every process exports its running version for dashboards — rollout status becomes replica lag.
- **Schema evolution discipline.** Config has its own compatibility problem: a consumer updated for key shape N meets a store still serving N-1 (and vice versa during rollout waves), so additive changes with defaults, reserved fields, and a stated compatibility mode for every config schema are the migration-gate discipline of this pipeline in miniature.
- **Validation gates before propagation.** Schema-check every key, diff the *resolved* config per service per layer in review, and run smoke evaluation in a canary before the wave — bad config should be a build failure, not an incident.
- **Layering with enforced precedence.** Document the stack, reject ambiguous shadowing in CI (warn when a value is overridden by a non-obvious layer), and expose a "why is this value X?" resolver command for operators.
- **Secrets as leases.** Short-TTL credentials, providers called at use-time, rotation with overlap windows, audit on every read — never bake secrets into images or env files that outlive the rotation schedule.
- **Blast-radius routing.** Match the propagation mechanism to the key's scope: global defaults get canary + wave + drain; instance-scoped tuning gets fast push; per-tenant values get TTL caches. The speed of a config change should be proportional to how narrowly you can undo it.

## Interview Questions

1. "Config is a replicated cache of intent" — unpack the sentence: what is the key, the value, the replica, and the invalidation protocol in a system you have operated?
2. A hot reload left your process running with half new, half old configuration. Describe the code shapes that cause this (boot-time capture, partial handlers) and the snapshot discipline that prevents it.
3. Design secret rotation so that rotating a database password cannot cause an outage. Where do connection pools, overlap windows, and boot-time reads each fit?
4. Your service's config has five layers. A value is wrong in production but right in the file everyone edits. How do you build tooling so this is answerable in one command?
5. A global default change must roll out to 2,000 replicas. Compare canary-wave, TTL, and flag-gating strategies for bounding the blast radius, and say when each is the wrong tool.

## Key Takeaways

- Configuration is distributed state: five stores with different propagation semantics (redeploy, restart, watch, read, rotation), all caching one intent — design them as a coherent replication system, not as scattered files.
- The effective, *resolved* layered value is what production executes; every review, diff, and debugging tool must operate on resolved output or it will lie to you.
- Atomic snapshot swap plus per-request capture is the transactional boundary that prevents half-reloaded processes and mixed-version fleets; versioned config makes rollout status observable as replica lag.
- Secrets are leases: rotation with overlap windows and use-time providers turns credential changes into non-events; captured-at-boot secrets are leases held past expiry.
- Blast radius is a design parameter: match propagation speed and rollout discipline to the scope a key can damage, and remember config errors inherit downward into consumers who never opted in.

## Cross-References

- [./cache-coherence-consistency.md](./cache-coherence-consistency.md) — Cache Coherence and Consistency — hot reload is an invalidation protocol over many replicas; MESI is the same problem in silicon.
- [./dns-cdn-routing.md](./dns-cdn-routing.md) — DNS and CDN Routing — hierarchical override and TTL-bounded staleness, the two mechanisms config layering reinvents.
- [./auth-identity-session.md](./auth-identity-session.md) — Auth, Identity, and Session — credentials as time-bounded leases; rotation is lease renewal with an overlap window.
- [./feature-flags-deploy-coupling.md](./feature-flags-deploy-coupling.md) — Feature Flags and Deployment Coupling — flags are behavior-targeted config with the same staleness, default, and cleanup-debt mechanics.
- [./containers-cgroups-namespaces.md](./containers-cgroups-namespaces.md) — Containers, cgroups, and Namespaces — where env vars, mounted config volumes, and immutable images fit in the propagation chain.
- [../assumptions-hunt/caching.md](../assumptions-hunt/caching.md) — Caching Assumptions Audit — the stale-read assumptions config SDKs inherit from their cache implementations.
- [../../os/overview.md](../../os/overview.md) — Operating Systems Overview — the process-startup path (env, argv, files) that boot-time config capture rides on.
