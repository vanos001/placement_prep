# Configuration Assumptions: What "It's Just Config" Silently Promises

## Overview

Configuration is where code and operations meet, and the meeting is unguarded: config changes do not go through the review, test, and rollout discipline that code changes do, yet config has exactly the same blast radius. This chapter audits four assumptions that flourish in that gap: that defaults are safe (they shipped with the software, so someone must have chosen them for production), that config is static for the process lifetime (the process read it once, so it will live by it), that a flag's existence means the feature is on (the knob is there; someone must have turned it), and that all environments run the same config (staging passed, so production behaves). Each assumption fails with a different mechanism — default drift across versions, half-applied hot reloads, dead flags reactivated, and environment divergence — and all four share one signature: the failure arrives on a machine nobody is looking at, with a value nobody set on purpose.

The chapter applies the collection's five-step pattern to the family. The framing references are the twelve-factor app's config discipline, the book chapters on feature flags and container resources, and the casebook's Knight Capital entry — the canonical incident for dead-flag reactivation, cited there and not retold here. The sibling chapters on testing and on containers supply adjacent halves of the picture: tests pass on whatever config the test environment has, and containers make "the same image" behave differently the moment limits or mounted configs differ. The unifying claim is that configuration is code that executes its decisions invisibly: every default is a decision, every reload boundary is a transaction with no atomicity, and every environment difference is a hypothesis that was never tested.

## Assumption 1: "Defaults Are Safe"

### The taught rule

The software's defaults were chosen by its maintainers; leaving them is the conservative choice, and changing them is the risky one.

### How it fails

Defaults are chosen for *installation success*, not production behavior: they must make the first run work on the smallest machine, so they optimize for the demo, not the fleet. Three mechanisms then erode them. *Default drift across versions:* maintainers change defaults between major versions because the old choice aged badly — MySQL 8.0 switched the default authentication plugin (breaking clients that had compiled against the old one), and every major database and queue has at least one such change in its release notes — so "leaving defaults" silently means "inheriting whatever version's defaults you happen to get," and an image rebuild that bumps a minor version can flip behavior no diff reviewed. *Defaults as invisible config:* unset values do not appear in `config dump`s that show only explicit settings, so the effective configuration is the union of the file, the environment, and the compiled-in defaults — most of it undocumented in any one place. *Defaults tuned for different hardware:* a pool size of 10, a timeout of 30 s, a heap of 1 GB — each reasonable on a laptop, each wrong on a 64-core node with 64 GB, and each discovered only under load.

Defaults are also a compat surface: tools and templates copy them, runbooks assume them, and the hard part is noticing that a version bump changed one implicitly.

### Failure scenario

A team upgrades a message broker's client library inside a routine dependency bump. The new major version changed a default: the client now enables its built-in reconnect-with-retry where the old one failed fast. Nobody read that line of the changelog; the service's own retry layer is unchanged. On the next broker failover, every consumer now issues its own retry storm on top of the platform's — the broker sees triple the reconnection load of the last failover, the failover window stretches from 40 seconds to 11 minutes, and the postmortem finds the behavior difference only by diffing effective client behavior between versions. The fix is a defaults audit: the effective config of every dependency is captured at boot (explicit or inherited), diffed in CI against the previous release's capture, and any change in an inherited default requires the same review as an explicit config change.

### Detection heuristic and what to assume instead

Detection: dump *effective* configuration (not the file — the resolved values) at process start for every service and dependency; diff those dumps version-over-version in CI; review release notes for the word "default" before upgrading anything on the data path. Corrected statement: *defaults are configuration values chosen by someone else, for a different workload, and they change between versions — pin, capture, and review them like any explicit setting, because "unset" is also a choice that drifts.*

## Assumption 2: "Config Is Static for the Process Lifetime"

### The taught rule

The process reads its configuration at startup; from then on, its behavior is determined; changes require a restart, so the running state always matches the boot config.

### How it fails

Modern processes are hybrids: some values are read once at boot (env vars in Kubernetes are immutable for the pod's life), some are watched and reloaded (mounted ConfigMap volumes are updated by the kubelet on its sync period — eventually, without the process being told), some come from a feature-flag service with per-second polling, and some sit behind an admin endpoint that reloads a file. Each channel has its own propagation timing and none of them are transactional together. The result is the half-applied state: a reload swaps the database endpoint but the connection pool still holds sockets to the old one; the logging config reloaded but the sampling buffer sized at boot did not; the feature-flag poller picked up the new value while the in-flight requests carry the old one. Restart-required values and reload-safe values are never labeled, so an operator "applies" a change and some of it takes effect, some does not, and the diff between intended and effective state is invisible until an incident maps it.

The failure is compounded by *reload asymmetry* across replicas: a rolling poll means the fleet runs a mixture of config generations, and aggregate behavior reflects neither value of a straddled limit.

### Failure scenario

An operator rotates a credential by updating a secret mounted into pods, expecting the documented "volumes update automatically." The kubelet updates the mounted file within its sync period, but the process caches the credential in memory at boot and never re-reads it: the old credential keeps working from cache until the pod restarts, which the rotation process does not trigger. Days later the old credential is revoked at the source; every pod fails its next outbound call with an auth error, and the incident chain is: live mount, static reader, stale cache, deferred revocation. The fix labels every config key with its propagation contract (boot-static, file-watch, poll, push), pairs secret rotation with an explicit restart or re-read hook, and tests the *effective* reload behavior per key rather than assuming the mount mechanism implies the application follows it.

### Detection heuristic and what to assume instead

Detection: for each config key, record channel (env, file, poller, admin API), propagation latency, and whether re-read is implemented — a three-column table that turns "it should reload" into a testable claim; monitor config-generation version across replicas and alert when the fleet straddles generations for longer than the rollout window. Corrected statement: *a process's configuration is a set of values with different lifetimes and channels; the effective state is the product of all of them, reload is not atomic, and "it takes effect on restart" versus "it reloads" must be declared per key, not discovered per incident.*

## Assumption 3: "The Flag Exists So the Feature Is On"

### The taught rule

If a configuration flag appears in the codebase (or the command line, or the config file), it is a live control for a live feature; setting it changes that feature's behavior, and removing the feature removes the flag.

### How it fails

Flags outlive features and change meanings, and nothing in the config system marks the difference between a live switch and an archaeological artifact. Three mechanisms: *dead flags* whose feature was removed but whose parsing remained (set it and nothing happens — until someone reuses the name); *repurposed flags* whose meaning silently changed between versions (the same string now gates different code); and *default-flipped flags* where a new release turns the feature on unless the flag is explicitly set — the operator who "never touched it" has, in effect, changed the system by upgrading. The Knight Capital incident in the failure casebook is the canonical citation: dead code reactivated through a repurposed flag, missed on one of eight servers, with billions in erroneous orders in under an hour — the casebook has the timeline; the assumption here is what made the setup possible, namely that flag names in a config system carry no contract about what they currently control.

The same assumption has a quieter daily form: a feature-flag service returns "flag exists, default true" for a flag whose targeting rules were edited last week; the flag *exists*, so the caller treats it as on, but the targeting excluded the current user segment. Existence, value, targeting, and kill-switch state are four different questions that one boolean answer conflates.

### Failure scenario

A service's config includes `enable_legacy_cache=true`, set in production since 2019, whose code path was gutted in a refactor — the flag now toggles an empty branch. A new engineer reads the flag as evidence that a legacy cache is *active* and plans a migration around it; meanwhile a separate cleanup PR deletes the empty branch but leaves the flag parsed (deleting the parsing breaks a config linter that checks for unknown keys). Eighteen months later, a performance team needs a cache-bypass switch, finds the flag, repurposes it in a new code path with the same name, and ships it: the production config already contains `enable_legacy_cache=true`, so the "new opt-in feature" is instantly enabled on every host at deploy — including the canary, because the fleet-shared config file outranked the canary's command-line override on the precedence chain. No line of code was wrong; the flag's lifecycle outlived every mechanism meant to track it.

### Detection heuristic and what to assume instead

Detection: audit flags quarterly against their code sites (a flag with no code reference is a finding; a code path with no flag owner is a finding); require that new flags be created *off* by default, carry an expiry or review date, and register their precedence (file, env, CLI, flag service) in one documented order. Corrected statement: *a flag is a promise that some code somewhere reads it, in a direction that may have changed since the config was written — existence proves nothing, defaults flip across versions, and precedence order is part of the feature's semantics.*

## Assumption 4: "All Environments Run the Same Config"

### The taught rule

Staging and production run the same images and the same config templates; the only differences are endpoints and scale, both abstracted; so a staging pass certifies production behavior.

### How it fails

Environment divergence is the norm, and it clusters exactly where it hurts. *Capacity-shaped values:* pool sizes, concurrency limits, batch sizes, and timeouts are tuned per environment for cost — staging's 10-connection pool passes tests that production's 500-connection pool turns into a thundering herd against a shared dependency (the container-resources chapter's quota arithmetic applies here too: the CPU/memory environment differs, so the same values behave differently). *Feature-shaped values:* TLS verification, auth enforcement, and rate limits are relaxed in non-production by convention — so the staging-certified code path includes a disabled check that production enables, and the interaction (a client that caches the insecure behavior) was never exercised. *Secret-shaped values:* the config tree that reached the repository or the CI logs with staging credentials also holds the prod-shaped structure — keys without values are a map of what production uses, and the committed `.env` with real credentials is the classic audit finding. *Drift-shaped values:* environments are edited by hand during incidents ("temporarily raise the timeout in prod"), the temporary value outlives the incident, and the divergence from the template is now undocumented.

The twelve-factor discipline — config strictly per-environment, injected, never baked — addresses the injection mechanics but not the *parity* question: identical images with different limits, flags, and secrets are different systems, and the parity that matters is which differences are deliberate.

### Failure scenario

A service passes staging with a 2-second upstream timeout (staging's dependency is fast, the value was set to keep tests quick). Production runs the same template at 15 seconds — a value raised "temporarily" during an incident two years ago and never reverted. A new dependency degrades slowly; upstream latency creeps from 3 to 14 seconds; staging never sees it (its 2-second ceiling fails fast even in slowness-simulating tests). Production's 15-second ceiling lets every caller wait for near-worst-case latency, so the user-facing p99 climbs while dashboards built from the template's documented "2 s timeout" thresholds stay silent — the monitors encode the template, the fleet runs the drift. The fix makes divergence first-class: environment diffs are generated and reviewed (config-as-code with a per-environment overlay and a mandatory diff in the deploy PR), temporary values carry expiry annotations, and alarms are generated from the *effective* config, not the template.

### Detection heuristic and what to assume instead

Detection: render the effective config of every environment and diff them automatically; require a human-readable rationale comment per differing key; scan config trees and CI logs for credential-shaped strings on a schedule. Corrected statement: *environments never run the same config — the deliverable is not parity but a reviewed diff: every difference between staging and production is deliberate, documented, and visible in the deploy that introduces it.*

## Interview Questions

1. **A dependency upgrade changes behavior with no code or config diff — how?** Inherited defaults: the new version ships different defaults, and "unset" resolves to the new values. Capture effective config at boot and diff it version-over-version in CI; treat default changes in release notes as review-worthy changes.
2. **Why can a "live-mounted" Kubernetes secret still be stale in the process?** The kubelet updates the mounted file eventually, but the process read it once at boot and cached it — propagation is per-channel, and env vars never update without restart. Label each config key with its channel and contract, and pair rotations with explicit restarts or re-reads.
3. **How did Knight Capital's repurposed-flag failure become possible? Name the three structural ingredients.** A dead feature's flag still parsed, a repurposed meaning under the same name, and a deploy that missed one server while the config already held the enabling value. Structure: flag lifecycle audits, default-off creation with expiry, and one documented precedence order.
4. **Staging passed; production failed on a timeout. What class of divergence is this, and what is the fix?** Capacity- or drift-shaped config divergence: values tuned per environment, temporary production edits that outlived their incident. Fix: generated environment diffs reviewed in the deploy PR, expiry on temporary values, alarms generated from effective config.
5. **Where does configuration overlap with secrets management?** Every config tree is a candidate credential store: committed `.env` files, CI logs, and config dumps all leak; the boundary is runtime injection from a secret store, with templates carrying structure but never values.

## Key Takeaways

- Defaults are someone else's configuration, chosen for installability and drift-prone across versions — capture effective config at boot and review inherited-default changes like explicit ones.
- Process config is a set of values with different channels and lifetimes; reload is not atomic and the fleet can straddle generations — declare each key's propagation contract and test it.
- A flag's existence proves nothing: dead and repurposed flags, flipped defaults, and undocumented precedence turn config archaeology into production incidents — audit flags and create them off, with expiry.
- Environments never share config; the deliverable is a reviewed, documented diff, with temporary values expiring and alarms generated from effective rather than template values.
- Config trees are secret-leak surfaces; structure belongs in templates, values in an injected store — and the Knight Capital casebook entry remains the family's exhibit A.

## Cross-References

- [Containers, cgroups, namespaces](../connection-atlas/containers-cgroups-namespaces.md) — the resource-limit half of "same image, different environment."
- [Kubernetes pod lifecycle](../followup-tree/kubernetes-pod-lifecycle.md) — where env vars, mounted volumes, and restart semantics actually propagate.
- [Testing assumptions](testing-assumptions.md) — why a staging pass certifies only the environment it ran in.
- [Knight Capital 2012](../failure-casebook/knight-capital-2012.md) — the casebook entry on repurposed flags and the missed canary.
- [Twelve-factor app](../../backend/twelve-factor-app.md) — the book chapter whose config discipline (and its [config page](https://12factor.net/config), verified) frames injection mechanics.
- [Feature flags](../../sre/feature-flags.md) — the book chapter on flag lifecycle, targeting, and kill switches.
