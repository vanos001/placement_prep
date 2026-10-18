# Logging and PII Assumptions: What "Log It All" Silently Promises

## Overview

Logging is the first debugging tool every engineer learns and the last one anyone audits. The result is that log pipelines accumulate four assumptions nobody wrote down: that logs are private (internal systems, so the rules about data do not apply), that redaction can be added later as a post-filter (the data is already there; cleaning it is a search-and-replace away), that structured log schemas are stable (a field rename is cosmetics), and that log levels mean the same thing across services (ERROR is ERROR everywhere). Each assumption fails in a way that combines two of the worst properties an incident can have: the damage is silent and the exposure is retroactive — data that entered the pipeline in 2023 is still readable in 2026 in a vendor's index no one on your team administers.

This chapter audits the family with the collection's five-step pattern. The pipeline-level mechanics — how logs become metrics, traces, and searchable indexes — are the connection atlas's observability chapter; here the subject is what flows into that pipeline and what promises its contents break. The regulatory frame is named rather than lectured: GDPR's data-minimization and erasure principles apply to logs as personal data, and the OWASP Logging Cheat Sheet (verified for this chapter) is the industry's checklist baseline; RFC 5424 defines syslog, whose "structured data" half is the ancestor of every modern structured-log format. The chapter's reference incident for "logs as trusted records" is the UK Post Office Horizon case in the failure casebook — where computer-generated records were presumed correct against human testimony for years, a presumption this chapter's assumption set quietly reproduces inside every organization that treats its logs as both truth and trash at the same time.

## Assumption 1: "Logs Are Private"

### The taught rule

Logs live in internal systems, viewable by engineers with SSH access; they are operational telemetry, not user-facing data, so data-handling rules do not really apply to them.

### How it fails

"Internal" is a routing topology, not an access control. A log line's journey crosses more trust boundaries than the request it describes: it is shipped to an aggregator, indexed by a vendor whose staff have support access, replicated to a hot-search tier, copied into dashboards, pasted into tickets by on-call engineers, attached to customer support threads, and retained by backup systems nobody remembers. Every hop is a disclosure surface with its own access list, and none of them inherit the care the application's database gets. Meanwhile the *content* of logs is systematically more sensitive than engineers assume, because logs capture the moment of failure — and failures serialize everything at hand: full SQL statements with the user's row values in the exception message, URLs carrying session tokens (`?token=`), Authorization headers dumped by verbose HTTP clients, GraphQL operation variables printed whole by error tracers, and stack traces that embed arguments in every frame. A request that would never appear in a database dump can appear, with all its personal data, in an exception log.

The presumption of privacy also shapes behavior: because logs feel internal, they get broader access than production data (every engineer reads them), longer convenient retention, and weaker audit trails — the inverse of what their actual contents deserve.

### Failure scenario

A payments service hits an intermittent serialization bug. The error path logs the full request body "to reproduce it" — including cardholder name, email, and the masked PAN the gateway sends (masked in the gateway's view, unmasked in the field the service re-serialized before masking). Three months of exceptions accumulate 1.4 million request bodies in the log vendor's index. A data-protection review discovers it: the logs are personal data at scale, the vendor's retention policy (13 months, chosen for troubleshooting convenience) is now a compliance problem, the "who has accessed" answer is "everyone with the team's shared login," and the ticket system holds forty pasted stack traces containing the same fields. The remediation cost — vendor-side purge requests, access-model rework, retraining — is orders of magnitude beyond the cost of the field-level redaction that was skipped in an afternoon of "we'll log it fully for now."

### Detection heuristic and what to assume instead

Detection: sample production logs and run a PII scan (email, phone, PAN patterns, token shapes) over the sample quarterly; classify every log consumer (vendor, dashboard, ticket) as a disclosure surface in the data map. Corrected statement: *logs are a replication of production data into the system with the broadest access and the weakest controls — classify them as personal-data surfaces, inventory their consumers, and design their contents for the broadest reader they will ever have.*

## Assumption 2: "Redaction Can Be Added Later as a Post-Filter"

### The taught rule

Log the rich data now for debuggability; when compliance asks, run a redaction pass over the pipeline — a regex for emails, a masker for tokens — and the history is clean.

### How it fails

Post-filters arrive after the data has already replicated, which is the whole problem in one sentence. Between "we log it fully" and "the filter deploys," the raw data flows to every consumer in Assumption 1's inventory: vendor indexes (retained per *their* policy, not yours), backups, tickets, laptop-local log files, and any analytics job that copied the topic. A retroactive filter cleans the forward flow only; it cannot reach the copies, and "delete it from the vendor" is a support negotiation with an outcome measured in weeks — GDPR's erasure right does not wait politely for the search cluster's next compaction. The filter itself is also weaker than the assumption: regex redaction catches the formats it was written for, while real PII arrives in encodings (base64, URL-encoded, JSON-escaped), in composite fields (`"name": "Ann Example"` inside a payload string), and in novel shapes (a national ID formatted differently per country) that no fixed rule set anticipates. And the filter sits on the hot path of the *highest-volume* stream in most companies, so every subsequent schema change that shifts field positions silently degrades it — the filter keeps "working" while matching less.

There is also an ordering trap: systems that sample or drop logs *before* redaction keep the full-fidelity copy in the sample path; systems that redact *after* the trace-correlation enrichment have already embedded user IDs in trace metadata that the redactor's field list does not cover.

### Failure scenario

An engineering team adds a "debug mode" that logs full authorization tokens to diagnose a flaky OAuth flow — with a comment: "temporary, we'll strip it in the pipeline later." The month-long debug window ends; the field is removed from the emitter. Eight months later, a security review traces a credential-stuffing campaign to valid tokens *found in logs* — the post-filter that was eventually deployed masked a field named `token`, but the debug emitter named it `access_token.value`, a nested path the filter's schema never knew. The tokens' validity window (hours) had long passed, but the leak taught the responders where every future token would be findable, and the incident report's line — "the pipeline redaction was schema-coupled and the emitter changed shape" — becomes the team's argument for redacting at emission, where the emitter and the masker are the same code and cannot disagree.

### Detection heuristic and what to assume instead

Detection: test the redaction pipeline with an adversarial corpus (PII in encodings, nested paths, renamed fields) on a schedule, and alert when the *unrecognized-field* rate in log schemas rises — new field shapes are where filters go blind. Corrected statement: *redaction is an emission-time property, not a pipeline stage — the only filter that cannot be bypassed by a schema change is the one in the same function that formats the line; treat anything downstream as best-effort cleanup of an already-complete disclosure.*

## Assumption 3: "Structured Log Schemas Are Stable"

### The taught rule

We log JSON with named fields; adding a field is additive and safe, renaming one is a trivial diff; downstream parsers and dashboards handle it.

### How it fails

Structured logs are a distributed schema with no registry and no compatibility contract — every consumer (parsers, dashboards, alert rules, SIEM detections, the vendor's query language, other services' ingestion configs) is a hand-written dependency on field names, types, and nesting that no deploy pipeline checks. The failure modes mirror the serialization-compatibility chapter's but arrive *faster*, because logs change with every refactor: a renamed field (`user_id` → `userId`) silently empties the dashboards and alert rules that queried it; a type change (`user_id` as string to an integer, to satisfy the new ORM) breaks parsers that assumed string comparisons; a field promoted from scalar to object (`error: "timeout"` → `error: {kind, message}`) turns every `"error": "timeout"` alert rule into dead text; and a percentage of lines from the older app version interleave with new-format lines during rolling deploys, so even a careful migration window sees mixed shapes. The worst variant is *type ambiguity at the collector*: JSON numbers that some parsers coerce to floats lose precision on 64-bit IDs — the exact class of bug in the sibling serialization chapter, appearing here as a silently misgrouped audit trail.

Alert rules are the highest-stakes consumers: a detection written against `auth.failure.count` stops firing on the renamed field, and nobody notices because alerts that do not fire produce no signal — the absence is the incident.

### Failure scenario

A platform team "modernizes" logging: fields camelCased, `error` restructured, `duration_ms` renamed `latency`. Deployment is clean; the aggregation pipeline accepts everything. Three weeks later: an on-call rotation misses a credential-stuffing pattern because the SIEM rule queried `user_id` (snake) and received `userId`; the latency SLO dashboard reports zeros while the error budget burns; and a post-incident timeline is written from logs that a forensic query now returns as empty. Total: one unnoticed attack window, one missed SLO breach, one audit finding — from a change whose diff looked like cosmetics. The fix institutionalizes the missing contract: a versioned log schema with documented additive-compatibility rules, a schema-registry-style check in CI for the emitter, and consumer-side tests (the api-contracts chapter's discipline) asserting that every alert rule and dashboard still matches a fixture of the current schema.

### Detection heuristic and what to assume instead

Detection: run schema-diff on log fixtures in CI and enumerate *consumers per field* — any field with a consumer (alert, dashboard, parser) requires a deprecation window before rename or type change; sample live logs weekly against the documented schema and alert on unrecognized fields. Corrected statement: *a log field's name and type are an interface consumed by machines that fail silently — evolve them like an API (additive, versioned, with consumer tests), not like code refactors.*

## Assumption 4: "Log Levels Mean the Same Thing Across Services"

### The taught rule

DEBUG, INFO, WARN, ERROR (and FATAL) are a shared vocabulary: ERROR means "something failed and needs attention," WARN means "degraded but operating," so a dashboard or pager policy built on levels works fleet-wide.

### How it fails

Levels are assigned per-service by authors with no cross-service convention, and they drift in two opposite directions. *Inflation:* a service that logs every failed validation, 404, and upstream 429 as ERROR teaches its operators that ERROR is noise; the paging rule on `ERROR` rate then either pages constantly (and is silenced, dropping the real signals with it) or is tuned so high that genuine failures hide inside the baseline. *Deflation:* another service logs exhausted connection pools and failed writes as WARN "because we retry" — and the retry loop that eventually gives up logs at WARN too. Aggregate dashboards that compare services by level (`team A has 10× the ERROR rate of team B`) compare vocabulary choices, not health. Levels also carry *implicit routing*: many pipelines ship WARN+ to the searchable tier and DEBUG to the local disk only — so the service whose authors debug-log the critical path loses exactly those lines when the incident requires them, and the team that logged a data-corruption path at INFO (it "recovered") finds the evidence outside the retained tier. Sampling compounds it: high-volume INFO streams get tail-sampled to cut costs, and the sampler — optimized to keep representative successful traces — systematically drops the rare error-shaped lines that were the reason anyone would read the stream.

### Failure scenario

An incident review needs to reconstruct a 20-minute window across four services. Service A logged the failure chain at ERROR with full context. Service B, whose authors were told to "reduce ERROR noise" in a previous quarter, logged its part at WARN — which its pipeline ships to a 7-day-retention tier that has aged out (the incident is 9 days old). Service C's relevant path ran at DEBUG, never shipped. Service D's sampler dropped the failing requests' traces because they arrived during a spike (exactly when volume triggers sampling). The reconstruction, which should take minutes, takes a week of inference from database timing and one lucky client-side log — and the postmortem's first action is a level taxonomy per service, documented next to the pipeline's routing rules, with "evidence-grade" paths pinned at ERROR and exempt from sampling.

### Detection heuristic and what to assume instead

Detection: per service, plot the ratio of ERROR to total and read it as a vocabulary metric — a steady ERROR rate of 40% means the level carries no signal; audit the pipeline's level-based routing and sampling policy against "which levels hold incident evidence." Corrected statement: *log levels are per-service dialects, not a protocol — document each service's level semantics next to its code, pin evidence-critical paths to levels that are retained and unsampled, and build aggregate views on structured outcomes (error kinds), not on level counts.*

## Interview Questions

1. **Why is "logs are internal" not a data-protection answer?** Because logs replicate across more trust boundaries than the data they describe — vendors, backups, tickets, dashboards — with broader access and weaker controls, and they capture full failure context (SQL, tokens, GraphQL variables) precisely at the moments users are involved.
2. **Why can't redaction be a retroactive pipeline stage?** Disclosure is a fan-out: the vendor index, backups, and tickets hold copies the filter never reaches; the filter is schema-coupled and degrades silently on renames; and compliance erasure does not wait for log compaction. Redact at emission, where emitter and masker cannot disagree.
3. **A field rename broke your alerting and nobody noticed for weeks. What discipline was missing?** Log schemas are machine-consumed interfaces: CI schema-diff, per-field consumer inventories, deprecation windows, and consumer-side fixture tests (the api-contracts discipline) — plus alert-rule tests that fail when their fields stop matching.
4. **What does a 40% steady ERROR rate tell you, and what breaks because of it?** That the level's vocabulary has inflated and carries no signal; paging rules built on it are either silenced (losing real signals) or tuned into uselessness. Aggregate health comparisons must use structured outcomes, not level counts.
5. **Why do sampling policies drop exactly the logs incidents need?** Samplers optimize for representative high-volume success traces; errors are rare and cluster during spikes — the sampler's busiest moments. Evidence-grade paths need an exemption from sampling and from short retention tiers.

## Key Takeaways

- Logs are production data replicated into the least-controlled system in the company; inventory consumers and design contents for the broadest future reader.
- Post-filter redaction is best-effort cleanup of an already-complete disclosure; emission-time redaction is the only variant a schema change cannot bypass.
- Structured log schemas are unregistered distributed interfaces; renames and type changes fail silently in dashboards, parsers, and alert rules — evolve them like APIs.
- Log levels are per-service dialects: inflation makes ERROR meaningless, deflation hides failures, and level-based routing decides what evidence survives an incident.
- Sampling and retention policies choose which truths remain reconstructable; exempt evidence-grade paths, and test the pipeline the way you test code.
- The Horizon casebook entry shows the other side of the same coin: log-derived records can be trusted too completely — log integrity and log humility are both requirements.

## Cross-References

- [Observability pipeline](../connection-atlas/observability-pipeline.md) — how logs become metrics, traces, and indexes downstream of the assumptions audited here.
- [UK Post Office Horizon](../failure-casebook/uk-post-office-horizon.md) — logs as trusted evidence: the casebook entry on records presumed correct against human testimony.
- [API contracts](api-contracts.md) — the contract-evolution discipline log schemas are missing.
- [Serialization compatibility](serialization-compatibility.md) — the field-evolution and numeric-precision machinery that log schemas inherit from.
- [Logging](../../cloud/observability/logging.md) — the book chapter on pipeline architecture this audit assumes as background.
- [RFC 5424](https://www.rfc-editor.org/rfc/rfc5424.html) — syslog's structured-data model (verified); [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) — the baseline checklist (verified). GDPR's minimization and erasure principles cited by name.
