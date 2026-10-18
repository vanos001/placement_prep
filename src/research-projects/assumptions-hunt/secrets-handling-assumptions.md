# Secrets-Handling Assumptions: What "It's in the Vault" Silently Promises

## Overview

Every system has a set of strings that must never be readable except by the components that need them — database passwords, API keys, signing keys, tokens — and the handling story for those strings is built on assumptions stated as nouns: "the vault", "the config", "the pipeline", "the scrubber". Each noun hides a claim that fails specifically and quietly: configuration is private (it leaks through process environments, orchestration metadata, and image layers), rotation is routine (it assumes every consumer re-reads on the operator's schedule), logs and error reports scrub secrets (a post-filter cannot redact a format it does not recognize), and version control plus CI are trusted places (history is permanent and logs are echoed to anyone who can read the build).

The deeper pattern is that *a secret's exposure surface is determined by every system that has ever held it in memory, on disk, or in a log line* — not by the vault at the center of the architecture diagram. Hardening the vault while ignoring the replication of secrets through environments, exception payloads, and CI transcripts is securing the bank vault while mailing copies of the key to every branch office. This chapter audits the four assumptions in the collection's five-step pattern. It sits beside the sibling [security and crypto](security-crypto.md) audit (cryptographic primitives and password storage), the [randomness and ids](randomness-and-ids.md) audit (entropy — where secret *values* come from), and the [logging and PII](logging-and-pii.md) audit (personal data in logs — this chapter handles the credential-shaped subset of the same failure class).

## Assumption 1: "A Secret in Configuration Is Private"

### The taught rule

Secrets live in configuration, injected by the deployment system and never committed to source control; the [12-factor config principle](https://12factor.net/config) — configuration in the environment, code and config strictly separated — is the pattern, and following it means the secret is safe.

### The hidden assumptions

- *The environment is readable by more than the process.* On Linux, `/proc/<pid>/environ` is readable by anything running as the same user; child processes inherit the full environment; and crash reporters, profilers, and debug endpoints that dump process state dump the secrets with it. One `env` command in a shared debugging session is an exfiltration path.
- *Orchestration metadata is a secret store nobody indexed.* Environment variables appear in pod specs, task definitions, and job configs — visible in `kubectl describe`, `docker inspect`, and the control-plane UI to everyone with read access, which is a different, much larger audience than the runtime's service account. The [config-management-pipeline atlas](../connection-atlas/config-management-pipeline.md) maps how config propagates; secrets ride the same edges.
- *Image layers are additive.* A secret written to a file in an early build layer and deleted in a later one remains recoverable from the earlier layer — deletion in a later layer hides the file from the container's view but not from the image history. Credentials passed as build args are baked the same way.
- *Secrets in memory outlive their usefulness:* core dumps, heap dumps, and swap can carry them to storage; the assumption "in memory" equals "transient" holds only if dumps are disabled and destinations are bounded.

### Counterexample

A team follows 12-factor correctly: the database password arrives as an environment variable and never appears in the repo. Six months later, a memory dump from a leaking pod — collected for a heap analysis and uploaded to the incident bucket — contains the environment block, password included. The bucket is readable by the whole engineering org, so the credential's audience is now "every engineer" until the next quarterly rotation, and nothing in the vault's audit log shows any of it. The corrected contract: inject secrets as files with restricted permissions where the runtime supports it (or via a secrets CSI/direct integration), keep them out of process environments entirely where feasible, treat orchestration metadata as public-to-readers, and rotate after any dump, debug session, or image export that may have captured them.

### What changes when the assumption is removed

Corrected statement: *a secret is as private as the most readable place it has been copied to — environment, pod spec, image layer, dump, or bucket — and each copy site must be enumerated and audited, because the vault protects the origin only.* The review question is not "is it in the vault?" but "list every system that has held this value since the vault".

### Consequences

In interviews, "where do secrets leak even with a vault?" expects the enumeration above, and the strongest answers volunteer the pod-spec and image-layer cases, which are invisible in application code and therefore invisible in code review.

## Assumption 2: "Rotation Is a Routine Operation"

### The taught rule

Rotate credentials on a schedule — 90 days, say — and the exposure window of any leaked secret is bounded by design; the runbook is "issue new secret, deploy, revoke old one".

### The hidden assumptions

- *Every consumer must re-read on the operator's schedule, not its own.* Services cache secrets at startup; connection pools authenticate when connections are created, not when the credential rotates; long-lived sessions and issued tokens (JWTs with hour-scale expiries, OAuth refresh flows) carry the old credential until they expire on their own clock.
- *Revocation and rotation have a validity gap:* between "new secret live" and "old secret revoked", both work (that is the point); if revocation is delayed or partial — per-region caches, per-component propagation — the old secret works much longer than the runbook says, and no dashboard shows the true dual-validity window.
- *Rotation is a load event:* when the shared database password rotates, every pod's pool must re-authenticate; 200 pods opening 10 fresh connections each is a 2,000-connection storm against the database at one instant — an availability incident scheduled by the security team.
- *Rotation without leakage response misses the point:* a leaked credential's risk window starts at the leak, not at the next scheduled rotation; the 90-day cadence bounds nothing about a key copied to an engineer's laptop in week 12.

### Counterexample

A platform rotates its PostgreSQL password on a Sunday. The rollout updates the secret store and restarts half the fleet; the other half — a batch tier whose jobs run for hours — keeps old connections until its next job boundary on Tuesday. Revocation happens immediately per the runbook, locking the batch tier out for 36 hours; the emergency fix re-enables the old credential, and now the "rotated" system has two live passwords indefinitely, neither tracked in the inventory. The corrected contract: rotation is a migration with phases — dual-validity window first, consumers re-read and prove it (connection age metrics), then revocation — and the window's length is whatever the slowest consumer's re-read interval is, measured, not assumed.

### What changes when the assumption is removed

Corrected statement: *rotation is complete when the slowest consumer has demonstrably re-read — everything else is a dual-validity window with an unmeasured length; the rotation plan must schedule consumer verification and tolerate reconnection load, and incident-driven rotation must beat the leak's clock, not the calendar's.* The certificate-shaped cousin of this whole section — renewal, propagation, revocation checking — is the [certificate rotation](certificate-rotation.md) audit, and the mechanics carry over directly.

### Consequences

"Walk me through rotating a database credential with zero downtime" is the interview probe: the senior answer is the phased plan above with connection-age verification and the reconnection storm called out by number.

## Assumption 3: "Logs and Error Reports Scrub Secrets"

### The taught rule

A redaction middleware strips Authorization headers and password fields before logs ship, so the logging pipeline is a safe place: what reaches the aggregator has been scrubbed.

### The hidden assumptions

- *A post-filter redacts shapes it knows.* Authorization headers and `password` fields are known shapes; credentials embedded in *values* are not: a JDBC connection string in an exception message (`jdbc:postgresql://user:secretpw@host/db`) puts the password in the middle of a log line, and stack traces, request dumps, and third-party client errors copy it verbatim.
- *Formats defeat matching:* the same secret base64-encoded, URL-encoded, or split across a structured object defeats literal-pattern scrubbing, which is why scrubbers pass known secrets and leak rotated ones — the filter's rule list always lags the secret inventory.
- *The debug path bypasses the scrubber entirely:* verbose flags, `console.log` leftovers, debug endpoints that echo request bodies, and error reporters configured with "attach local variables" send unscrubbed material to a different destination than the logging pipeline the scrubber protects — the [logging and PII](logging-and-pii.md) chapter's "redaction is a retrofittable post-filter" assumption, applied to the credential subset.
- *Logs are replicated:* aggregated, indexed, and retained for months, a single leaked line has a readership and a lifetime no rotation schedule can recall — the exposure surface argument from Assumption 1, one hop downstream.

### Counterexample

A payment integration fails during an outage, and its SDK's exception message embeds the full request URL — including the API key as a query parameter. The exception is logged with a stack trace by the default handler, shipped to the aggregator, and indexed; the scrubber matches `password` and `authorization` fields and never sees a key inside a URL string. The key is now readable to everyone with log access until the next rotation, and — because the on-call pasted the log line into a ticket — to whoever reads tickets. The corrected contract: pass secrets in headers or bodies the SDK cannot stringify, wrap third-party clients with error sanitizers that redact *by inventory* (every known secret value, matched as a literal) rather than by field name, and rotate the key on the same ticket that quotes the log line.

### What changes when the assumption is removed

Corrected statement: *scrubbing is probabilistic over unknown shapes and exact only over inventoried values; the durable defenses are structural — secrets never in URLs or stringified requests, error reporting configured to exclude locals, and literal-value redaction fed from the secret inventory.* "The logs are scrubbed" is a claim about a filter list, and the filter list is always one format behind.

### Consequences

The interview probe "your API key leaked through logs — what do you fix first?" has a two-layer answer: rotate now (Assumption 2's incident clock), then fix structurally, and the structural fix is inventory-driven redaction, not another regex.

## Assumption 4: "CI and Version Control Are Trusted Places for Secrets"

### The taught rule

CI systems mask secrets, repositories are private, and the deployment pipeline is operator-controlled — so build and deploy configurations may hold credentials, and the occasional committed `.env` is harmless once removed.

### The hidden assumptions

- *Masking matches literals.* CI masks the exact secret value in logs; transform it — base64, substring concatenation, `echo $SECRET | base64` — and the mask misses, so debugging scripts that encode or split secrets print them in clear text to everyone who can read build logs.
- *Fork builds change the trust boundary:* workflows triggered by pull requests run repository code with, depending on trigger configuration, access to secrets; a malicious or careless contributor's workflow change can exfiltrate them — the pipeline's trust model must be checked per trigger type, not assumed uniform. The [OWASP secrets-management cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) enumerates this and the other pipeline exposures audited here.
- *Removal is not deletion:* a committed `.env` removed in the next commit remains in history — reachable by anyone who clones the repo, forever, across forks — the "history is immutable" reality the [git workflow assumptions](git-workflow-assumptions.md) chapter audits. Push protection (GitHub's [secret-scanning push protection](https://docs.github.com/en/code-security/secret-scanning/push-protection-for-repositories-and-organizations)) blocks new pushes containing detected secrets, but only going forward and only for recognized formats.
- *One token, every privilege:* pipelines routinely hold a single credential that can read source, write packages, and deploy to production, so one leaked build secret is a full compromise; scoping and short-lived credentials shrink the blast radius of the leaks this section assumes will happen.

### Counterexample

A developer commits a `.env` with a staging database password during a prototype, deletes it two commits later, and the review approves "nothing sensitive in the final tree". Eight months later, a contractor clones the repository, runs a credential scanner over the full history, and recovers the password — which, per Assumption 2's calendar logic, was never rotated because "it was only staging" — and the staging database holds a production-shaped copy of customer data. The exposure came from version control's one-way memory, not from any live file. The corrected contract: treat every push as permanent (scanner-gated and push-protection-enabled), grant CI credentials per job with minimum scope and short lifetime, and assume build logs are readable org-wide when deciding what may be printed.

### What changes when the assumption is removed

Corrected statement: *version control is a permanent publication system and CI logs are an org-readable transcript; the working assumptions are "committed equals retained" and "printed equals disclosed", with push protection and masking treated as helpful damping on a channel that is never confidential.* The remediation for any secret that entered either channel is rotation first — deletion is cosmetic.

### Consequences

"A secret was committed and then removed. Is it exposed?" is a pass/fail interview question: the correct answer is yes, permanently, with rotation as the only remediation — and it doubles as the cheapest security-training slide in the building.

## Interview Questions

1. **A vault holds every secret and nothing is committed to source control. Name four leak paths that remain.** Process environments and `/proc` dumps, orchestration metadata visible to anyone with read access, additive image layers retaining deleted files, and logs/error reports carrying secrets in values the scrubber does not match.
2. **Why can "rotate the database password" be an availability incident?** Connection pools re-authenticate on rotation; hundreds of pods re-opening pools simultaneously is a connection storm, and consumers that re-read late (batch tiers, long sessions) either break at revocation or force a dual-validity window nobody measured.
3. **A scrubber matches `password` and `authorization` fields. What leaks anyway?** Secrets embedded in values — connection strings and URLs inside exception messages, base64- or URL-encoded variants, debug-path dumps with locals — plus any destination (tickets, error reporters) the scrubber never sees.
4. **A `.env` was committed and removed a commit later. What is the correct response?** The credential is permanently exposed via history; rotation is the remediation, deletion is cosmetic. Going forward: push protection, history scanning, and CI credentials scoped per job with short lifetimes.

## Key Takeaways

- A secret's privacy is bounded by the least-protected system that has ever held it — environment, pod spec, image layer, dump, log line, build transcript — so the audit is an enumeration of copy sites, not a check of the vault.
- Rotation is a phased migration with a dual-validity window whose length is the slowest consumer's re-read interval, and a load event (reconnection storms) that must be scheduled like any other migration.
- Log scrubbing is exact only over inventoried values and structural only over known shapes; the durable defenses are keeping secrets out of stringified contexts and feeding literal-value redaction from the inventory.
- Version control is permanent and CI logs are org-readable: committed equals retained, printed equals disclosed, and the remediation for either is rotation, not deletion.
- The cross-cutting discipline is blast-radius control: scoped, short-lived credentials and per-destination exposure reviews turn the leaks this chapter assumes into recoverable events.

## Cross-References

- [Security and crypto assumptions](security-crypto.md) — the primitives side: password hashing, randomness-adjacent crypto choices, and "HTTPS as endorsement".
- [Randomness and IDs](randomness-and-ids.md) — where secret values come from: entropy, PRNG unpredictability, and UUID uniqueness as secrecy.
- [Logging and PII](logging-and-pii.md) — the personal-data twin of Assumption 3: post-filter redaction over unknown shapes.
- [Configuration assumptions](configuration-assumptions.md) — the config surface (defaults, drift, per-environment parity) that secrets ride into every system.
- [Git workflow assumptions](git-workflow-assumptions.md) — history immutability and "clean tree as pushed work", the mechanics behind Assumption 4.
- [Connection atlas: auth, identity, session](../connection-atlas/auth-identity-session.md) — how credentials become sessions and tokens, the consumption side of rotation.
- [Connection atlas: config management pipeline](../connection-atlas/config-management-pipeline.md) — the propagation graph that duplicates config — and secrets — across systems.
- [Failure casebook: Target, 2013](../failure-casebook/target-2013-breach.md) — the vendor-credential entry path that started the breach: credentials as the softest perimeter.
- The [12-factor config principle](https://12factor.net/config), the [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html), and GitHub's [push protection documentation](https://docs.github.com/en/code-security/secret-scanning/push-protection-for-repositories-and-organizations) are the primary sources above; all were fetched and verified this session.
