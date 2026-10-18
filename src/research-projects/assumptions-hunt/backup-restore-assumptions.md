# Backup and Restore Assumptions: What "We Have Backups" Silently Promises

## Overview

Backup is the rare engineering discipline whose success is invisible and whose failure is total, and the assumptions in this chapter share a signature: they are all beliefs about the *restore* derived from observations of the *backup*. A green backup job proves the archive was written; it proves nothing about whether the archive can be turned back into a working system. The distance between those two claims is where the industry's worst data-loss stories live, and it is measured not in bits but in untested procedures, rotted tooling, drifted schemas, and recovery-point arithmetic that ignores everything except the backup interval.

This chapter audits the backup family with the collection's five-step pattern. The restore-first doctrine — that a backup is not a backup until it has been restored, and that backup policies must require regular restores — comes from the Google SRE book's data-integrity chapter, linked at source. The point-in-time recovery mechanics follow the PostgreSQL continuous-archiving documentation, which defines what WAL archiving does and does not promise, and the GitLab 2017 incident — where a backup existed and the restore did not go — is delegated to the failure casebook rather than retold. The misconception chapter's backups-mean-recovery entry is the complement: it refutes the claim "backups exist so recovery exists" as false; here the conditional version — "backups restore, provided…" — is audited for its unstated preconditions, which is this collection's method.

## Assumption 1: "Restore Is Just Backup in Reverse"

### The taught rule

Backup writes the data somewhere safe; restore reads it back. One is the inverse of the other, so testing one tests the other.

### The hidden assumptions

- The operations are not inverse because they run in different worlds: backup runs against a healthy system with tools, credentials, and schema knowledge at hand; restore runs during an incident, often onto infrastructure that no longer exists, with people who have never done it before.
- Restore has a dependency graph the backup never surfaces: provisioned infrastructure, engine versions compatible with the archive format, application versions compatible with the restored schema, DNS in place, secrets available. The archive is one node of that graph, and backups verify only that node.
- Tooling rots between uses: the restore script that worked eighteen months ago now meets a PostgreSQL major version that changed the archive format, a cloud console API that changed flags, or a runner image that no longer has the client installed. Untested code with a once-a-year execution rate is not code; it is archaeology.
- The people assumption is real: backup is scheduled and automatic; restore is manual and rare. The procedure exists as a runbook at best, and its accuracy decays at the same rate as the tooling.

### Counterexample

A team restores its production database quarterly — on paper. In year three, the real incident arrives: the archive restores cleanly, but the application has since added two tables the restore tooling's schema filter predates, the restored rows reference a service account whose credentials were rotated into a new secret manager, and the script's cloud-SDK calls fail on a deprecated flag. The database is "restored" for six hours before the application can run, and two of those hours go to rediscovering the compatibility matrix by trial and error. Every failure is restore-side; every green checkmark for three years was backup-side. The fix is procedural, not technical: scheduled restore drills into a clean environment (the SRE book's data-integrity chapter makes the drill a policy requirement, not a suggestion), a compatibility matrix owned as code, and restore timing measured and reported like an SLO.

### What changes when the assumption is removed

Corrected statement: *restore is a separate system that consumes backups, with its own dependencies, versions, credentials, and runbook — and it decays at its own rate, so it needs its own testing cadence.* Operationally: define RTO for each restore class, drill it on a schedule into an isolated environment, and treat drill failures as production incidents with postmortems, because the first un-drilled restore is the real one.

### Consequences

The interview probe "how do you know your backups work?" has a trap built in: the strong answer is "I don't trust backups, I test restores," and the follow-up — "what does a restore drill cost, and how often?" — separates people who have run one from people who have read about them. The storage-durability sibling carries the same doctrine from the durability side.

## Assumption 2: "Restores Are Tested by Backup Jobs Succeeding"

### The taught rule

The nightly backup job has been green for months, and it alerts on failure — so the backups are good.

### The hidden assumptions

- A green backup proves the write path: the source was read, the archive was stored. It says nothing about the archive's internal consistency (a backup taken against a live, actively written database without snapshot or WAL coordination can capture a torn state no tool can reassemble).
- Completeness is a separate axis: a misconfigured flag can exclude the one schema that matters, an encryption key can live in the same system as the archives (available in normal times, gone with them), and WAL archiving can silently stall so the restorable point is weeks old while the backup job stays green.
- Verification depth matters: checksums prove storage integrity, not semantic restorability. The cheapest real test is a restore, the second cheapest an automated smoke test into a scratch instance with row-count and constraint checks — many teams run neither.
- The GitLab 2017 incident is this assumption's canonical failure: backups and replication existed, but the restore path failed under pressure, and the detail that made it famous — the lapsed backup procedure meeting an incident that removed the copies — is documented in the casebook chapter with the primary sources.

### Counterexample

The composite failure, in the order it usually stacks: the nightly `pg_dump` runs against a live primary with a long transaction open, so the dump captures a consistent-but-stale snapshot — green. WAL archiving to the object store silently broke three weeks earlier when a bucket policy change revoked the archiver's credentials; the dump job's separate credentials were fine — green. A logical corruption is noticed on a Tuesday; the most recent restorable point turns out to be the three-week-old WAL gap, and everything between exists only in the green dumps that cannot be reassembled into the missing chain. No monitor ever fired because every monitor watched the backup job, not the restorable point. The detection that closes this: a monitored "latest restorable timestamp" metric computed from the actual archive chain, plus a scheduled automated restore of the newest archive into scratch storage with assertions — the metric catches the WAL gap on day one.

### What changes when the assumption is removed

Corrected statement: *backup job success measures the write path; restorability is a property of the whole chain (coordination with the live workload, WAL continuity, key custody, schema completeness) and must be measured and drilled as such.* Operationally: monitor restorable-point lag, auto-restore the newest archive on a schedule, alert on chain gaps, and keep encryption keys in a custody domain separate from the archives.

### Consequences

The interview probe "your backups are green but restore fails — reconstruct the incident" is a full-systems exercise touching snapshot coordination, archiving, credentials, and monitoring, and the memorable answer is the distinction between backup-path and restore-path telemetry. The casebook's GitLab chapter gives the real timeline; this chapter's composite is the generalized version teams actually meet.

## Assumption 3: "RPO Equals Backup Frequency"

### The taught rule

We back up every hour, so we lose at most an hour of data — the recovery point objective is one hour.

### The hidden assumptions

- RPO is the *worst-case* data loss across the whole chain, and every stage adds loss: the backup interval, the time for the backup to become restorable (upload, verification, index), cross-region copy lag, and the degraded-primary window before detection, because corruption propagates to backups until detected.
- A backup is a point in the past; the workload keeps writing. The real recovery point for a crash-consistent file copy taken at 02:00 against a live database may be "02:00 minus whatever the copy caught mid-write" — crash consistency is not application consistency, and only log-structured recovery (WAL replay, point-in-time recovery) turns an interval into a claim.
- The claim "we lose at most one hour" silently assumes the failure is noticed instantly. Detection lag — hours for silent corruption, days for the WAL gap above — extends RPO past the interval by exactly that time, usually the largest term and the one nobody measures.
- Restore time is a different number (RTO) and is routinely confused with RPO in design docs; a one-hour RPO with a six-hour RTO means six hours of downtime where the design review assumed none.

### Counterexample

A service with hourly backups advertises a one-hour RPO. A storage-layer corruption begins at 09:10 and is detected at 14:40; because replication and backups copied the corruption faithfully, the last clean restorable point is 09:00 — the experienced RPO is five hours forty minutes, not one hour, and the difference is entirely detection lag. The arithmetic that fixes the plan: RPO = backup interval + verification lag + cross-region copy lag + detection lag, with the last term dominating; the mitigations are detection-side (checksum verification on ingest, anomaly alarms, the corruption-would-be-loud misconception's lessons) as much as backup-side (shorter intervals, WAL shipping for a minutes-scale RPO). The PostgreSQL continuous-archiving documentation's replay model is the reference for turning WAL archives into "restore to any second within the archived span," which is what a minutes-scale RPO claim actually requires.

### What changes when the assumption is removed

Corrected statement: *RPO is the worst-case loss across interval, copy lag, and detection lag, and only continuous log shipping plus fast detection makes small RPOs real; RTO is a separate budget measured in drills, not in backup intervals.* Operationally: compute the RPO chain per data class, measure detection lag as a first-class metric, and re-derive the RPO claim whenever any term changes (a region move changes copy lag; a monitoring change changes detection lag).

### Consequences

The interview probe "you back up hourly — what's your RPO?" is designed to catch the interval-equals-RPO shortcut; the strong answer decomposes the chain and names detection lag as the dominant term. The event-sourcing-WAL chapter shows the same log-replay machinery doing double duty as the replication mechanism, which is why WAL-aware backup designs and replication designs rhyme.

## Assumption 4: "Partial Restore Is Possible"

### The taught rule

If the full restore is too heavy, restore just the affected table (or user, or tenant) from the backup — surgical recovery is an option we keep in reserve.

### The hidden assumptions

- Partial restore is a property of the archive format and the backup design, not a right: file-per-table physical formats permit surgical extraction; a single logical dump or a whole-instance snapshot does not, without re-implementing the restore logic under incident pressure.
- Data is not independent: a restored table arrives without the rows other tables reference (foreign keys, ownership records, balance lines), so a surgical restore can produce a database whose constraints are unenforceable or whose application invariants are violated — the restore "works" and the system is inconsistent.
- Schema drift compounds the surgery: if the archive is three weeks old (the WAL-gap case), its schema predates migrations since, and restoring old-shaped rows into new-shaped tables needs a transformation step nobody wrote under calm conditions.
- Point-in-time granularity must be designed in: the PostgreSQL PITR model (base backup plus WAL replay to a target timestamp) is what makes "restore to 09:59:43" possible; a nightly file copy has no such dial, and teams conflate the two until the incident asks for the dial.

### Counterexample

A bad deploy deletes one tenant's rows at 11:00. The team's backup is a nightly whole-database snapshot; the "partial restore" plan is to load last night's snapshot into a scratch instance and copy the tenant's rows back. The scratch load takes four hours on a 2 TB database, and the tenant's rows come back as of 02:00 — so the day's legitimate writes for that tenant are absent, and rows in three related tables the extraction query missed are left dangling, tripping foreign-key violations the moment the application touches the tenant. The recovery that actually works requires: logical archives with per-tenant extractability (or WAL replay to 10:59 — one minute before the delete — which needs PITR designed in), an impact-set query written and *tested* in advance (which tables reference the tenant), and a reconciliation pass that re-imports post-02:00 legitimate writes from the audit log. Every piece is a calm-time artifact; none can be improvised at 11:30.

### What changes when the assumption is removed

Corrected statement: *partial restore must be designed into the backup (archive granularity, PITR support, referential-impact tooling) or it does not exist; the surgical option is built during calm, never during the incident.* Operationally: choose archive formats per restore class, maintain and drill the impact-set queries, and prefer WAL replay to a pre-incident timestamp over row surgery wherever the archive chain supports it.

### Consequences

The interview probe "one tenant was corrupted at 11:00; walk me through recovery" is the design-review test for backup architecture, and the differentiating answer starts with "what can the archive actually express?" rather than "we'll restore what we need." The zero-downtime-migrations chapter's schema-drift discipline is the same problem arriving from the deployment side, and the casebook's GitLab chapter shows what happens when none of the calm-time artifacts exist.

## Interview Questions

1. **How do you know your backups work?** I do not test backups; I test restores — scheduled drills into clean environments with assertions, restore time measured as an SLO, and drill failures treated as incidents (the SRE book's data-integrity posture).
2. **Backups are green but the restore fails. Name three mechanisms.** Torn snapshots against live workloads without WAL coordination; silently stalled archiving (credentials, bucket policy) leaving the restorable point weeks old; tooling rot — archive format versus engine version, deprecated SDK flags, rotated credentials.
3. **Hourly backups — is your RPO one hour?** No: RPO is interval plus verification lag plus copy lag plus detection lag, and detection lag usually dominates; only continuous WAL shipping with fast detection makes a minutes-scale claim real, and RTO is a separate drilled number.
4. **A deploy deleted one tenant's data. Can you restore just that tenant?** Only if the design allows it: archive granularity or PITR to a pre-incident timestamp, tested impact-set queries for referential neighbors, and a reconciliation of post-backup legitimate writes — otherwise the surgical plan fails on foreign keys and lost-day writes.
5. **What does a backup of corrupt data give you?** Corrupt backups, on schedule — which is why detection (checksums, anomaly alarms, verification restores) is part of the RPO chain, not a separate concern; the storage-durability chapter's replication-lag analysis is the same propagation problem.

## Key Takeaways

- Backup and restore are different systems in different worlds: the backup proves the write path, and only drills prove the read-back path, which rots independently.
- Green backup jobs are restore-path-blind; monitor the restorable point itself (chain continuity, latest restorable timestamp) and automate restore smoke tests into scratch environments.
- RPO is a chain arithmetic — interval, verification, copy lag, and dominant detection lag — and RTO is a separate number; only log shipping plus fast detection makes small claims true.
- Partial restore is a designed property of archive granularity, PITR support, and tested impact tooling; improvised surgery during an incident produces referentially inconsistent results.
- The doctrine that survives review is restore-first: define the restore classes, drill them, measure them, and let the backup design follow from what the restore must do.

## Cross-References

- [Storage durability](storage-durability.md) — the sibling audit of durability claims, untested backups, and replication-lag loss.
- [Filesystem durability](filesystem-durability.md) — the fsync and snapshot mechanics underneath crash-consistent backups.
- [Backups mean recovery (misconception)](../misconceptions/backups-mean-recovery.md) — the false-as-stated version of the claim this chapter audits conditionally.
- [GitLab 2017 data loss](../failure-casebook/gitlab-2017-data-loss.md) — the canonical incident where backup met an unworkable restore, with primary sources.
- [Event sourcing and WAL](../connection-atlas/event-sourcing-wal.md) — the log-replay machinery that PITR and replication share.
- [Zero-downtime migrations](../followup-tree/zero-downtime-migrations.md) — the schema-drift discipline restore-from-old-archive collides with.
- [Google SRE book: Data Integrity](https://sre.google/sre-book/data-integrity/) — the restore-first doctrine and backup-policy requirements, from the source.
- [PostgreSQL continuous archiving and PITR](https://www.postgresql.org/docs/current/continuous-archiving.html) — the base-backup-plus-WAL-replay model that makes point-in-time restore real.
- [pg_dump reference](https://www.postgresql.org/docs/current/app-pgdump.html) — logical archive semantics and their consistency caveats against live databases.
- [AWS S3 durability](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DataDurability.html) — object-storage durability as one term in the chain, distinct from availability.
