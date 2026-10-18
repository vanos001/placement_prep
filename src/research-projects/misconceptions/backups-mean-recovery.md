# "We have backups, so we can recover"

## Overview

"We have backups" is the most reassuring sentence in incident response and
the least informative, because recovery is a capability and a backup is an
artifact. Between the artifact and the capability stand the restore drill
nobody ran, the recovery-time objective nobody priced, the consistency
problem of backing up a database that is mid-write, the restore pipeline
that itself breaks under load, and the cross-region copy that quietly never
happened. This page audits the claim, gives the regime where it holds
(verified, automated, scoped restores), and works the arithmetic of restore
time and recovery point. The verdict is incomplete: backups are necessary
for recovery, but every recorded data-loss disaster in which backups
existed — GitLab 2017 is the canonical case, audited in this collection's
failure casebook — shows the gap between owning the artifact and being able
to use it.

## The Claim, Stated Fairly

The strongest common form is: "Our database is backed up nightly and the
files land in object storage, so if we lose the cluster we restore from
backup and we are back." This is not carelessness. It is the reasonable
summary of a real control that genuinely exists, and in the failure modes
the speaker usually imagines — a dropped table, a corrupted volume on one
node — it works, because a single-table restore from last night's file is
mechanically simple and the data-loss window is small and survivable.

The claim deserves its fairness because backup infrastructure is real and
often good. The question is what "recover" has to mean to be true: return
the *service* to operation within a time the business can absorb (recovery
time objective, RTO), losing no more data than the business can absorb
(recovery point objective, RPO), with a procedure that works on the day,
under load, with the primary mechanism of failure also having taken out
whatever else was nearby. A nightly file dump addresses none of those
dimensions by itself.

## Verdict

**Incomplete.** Backups exist in the common regime and that is genuinely
half the battle. The claim omits the preconditions that convert the
artifact into recovery: a tested restore path (most untested restores fail
on their first real run), an RTO that survives the arithmetic of restore
throughput plus WAL replay plus warm-up, an RPO defined against backup
age, consistency guarantees for databases captured mid-write, and
independence of the backup from the failure (region, account, credential,
and blast-radius independence). When any of these is missing, the promised
outcome — recovery — fails to materialize, which is exactly the
taxonomy's signature of an incomplete claim.

## Why People Believe It

The kernel of truth is that backups do work most of the time they are
needed for small, local failures. A deleted collection, a botched
migration on one environment, a corrupted disk on a single node — for
these, "restore from last night's dump" is a working procedure that
engineers have personally watched succeed. The experience generalizes into
"we can recover", and nothing in daily operation contradicts it, because
nothing in daily operation *tests* it: the full-cluster, cross-region,
mid-incident restore is never exercised in peacetime.

The second reason is vocabulary confusion. "Backup" answers a storage
question (do the bytes exist elsewhere?); "recovery" answers a service
question (how fast is the system serving again, and how much data is
gone?). The two are connected only through a tested procedure. A backup
that has never been restored is a hypothesis; the industry's folk saying —
an untested backup is not a backup — exists because so many teams have
discovered, mid-incident, that the dump is truncated, the schema version
mismatches, the credentials rotated, or the restore tool has been broken
by an upgrade for eight months.

The third reason is that the interesting failure modes are rare and
correlated. Backups fail precisely when the failure is large: the
misconfiguration that destroys the primary also destroys the replica
(instantly, asynchronously replicated), and the region outage that takes
the database also takes the restore tooling that lived beside it.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Backups exist" | Bytes exist in secondary storage — necessary, not sufficient |
| "So we can recover" | Recovery = tested restore path + RTO that fits the arithmetic + RPO that fits backup frequency + independence from the failure |
| "RTO" | Time from declaring disaster to serving traffic; bounded below by restore throughput, WAL replay, DNS and cache warm-up |
| "RPO" | Maximum data loss; bounded below by backup/reclication cadence — a nightly snapshot has a worst-case RPO of ~24 hours |
| "Restore is mechanical" | Restores fail on schema drift, credential rotation, tooling bit-rot, and capacity — each found only by rehearsal |
| "Replicas are backups" | Replication protects against node loss, not against logical corruption, dropped tables, or fat-fingered DDL, which replicate faithfully |
| "Cross-region copies" | Only counts if the copy is verified, access-controlled independently, and outside the failure's blast radius |

The corrected sentence: "We can recover within RTO X while losing at most
RPO Y, because we rehearse the full restore path quarterly, our backup
consistency mechanism matches our database engine, and our backups are
independent of the failure modes we defend against." Every clause of that
sentence is checkable, and only the full sentence is true.

The quantitative core is restore-time arithmetic. Streaming 1 TB from
object storage onto volumes at a sustained 200 MB/s takes about 83 minutes
— before the database applies write-ahead logs, before replication to
standbys rebuilds, before caches warm and latency returns to normal, and
before anyone debugs the first failed step. If the promise was "back in an
hour", physics lost the argument before the first hiccup. RPO arithmetic
is equally blunt: a nightly 02:00 snapshot with a failure at 17:30 has a
worst-case data-loss window of 15.5 hours, no matter how pristine the
snapshot is.

## Where It Breaks

**The untested restore (the default failure).** The dump exists and is
complete, and the restore still fails: the `pg_restore` binary version
predates the server's; the object-storage credentials were scoped to an
account that offboarding removed; the restore script's last successful run
was against a schema two years old. None of these are visible in a backup
dashboard, which reports "last backup: 6 hours ago, 210 GB, green". The
claim's failure here is silent in peacetime and total in an incident,
which is why mature organizations schedule game-day restores: the drill
converts the hypothesis into a capability and produces the real RTO
number, which is usually several times worse than estimated.

**Consistency under a running database.** Copying a live database's data
directory — or snapshotting its volume without coordination — captures
pages at different moments. A table page written at time t1 and its index
page written at t2 produce a backup that opens, but contains a torn
transaction: rows whose indexes disagree with the heap, or a partially
applied multi-page update. Databases solve this with engine-aware
mechanisms — PostgreSQL's `pg_basebackup` plus WAL archiving, InnoDB hot
backups plus binlog, storage snapshots taken crash-consistently and
replayed through WAL on restore. A "backup" produced by naive `cp` or an
uncoordinated snapshot may complete, checksum-clean, and still be
unrestorable to a consistent state; the failure announces itself only when
the restored server tries to start, or worse, when it starts and answers
wrong.

**GitLab 2017: five mechanisms, all down at once.** The canonical case
operationalizes every clause of the corrected sentence. After an operator
removed the wrong directory on the primary, the team discovered that five
recovery mechanisms each failed for its own reason: the LVM snapshot and
disk snapshots were not enabled or not taken, the S3 upload procedure was
not configured for the right data, and a synchronizing standby was
similarly useless. One recent manual backup did exist, and restoring even
that took roughly 18 hours of work, losing about six hours of customer
data permanently. The backup story was "we have backups"; the reality was
a restore path that had never been rehearsed end to end. The failure
casebook chapter in this collection walks the mechanics; the lesson for
this page is that five parallel "we can recover" beliefs were each false
independently.

**Blast radius and the restore that needs the thing that died.** Recovery
capacity has its own dependencies. Restoring consumes production-grade
IOPS on the very infrastructure the incident may have degraded; the
DynamoDB event of 2015 in this collection's casebook shows how an
operational error in a control plane cascaded far beyond the intended
scope — a reminder that the systems your recovery depends on are systems
too. Cross-region copies protect against region loss only if they are
verified, and key management is part of the blast radius: an encrypted
backup whose decryption key lived in the destroyed account is ciphertext
with a eulogy. When it accidentally works: quiesced or engine-aware
backups, quarterly full-path drills, independent credentials, cross-region
verification — in that regime the claim is simply true, and every clause
of the corrected sentence is what the drill verifies.

## Practical Implications

- Rehearse the full restore path on a schedule and measure it: the drill
  yields your real RTO, your real runbook gaps, and your real RPO — the
  three numbers the incident will ask for.
- Use engine-aware backup mechanisms (WAL archiving, binlog, coordinated
  snapshots) rather than file copies for any database that is running;
  verify crash-consistency by actually starting the restored copy.
- Define RPO explicitly from backup cadence and write it down: "nightly"
  is an RPO of up to 24 hours, and stakeholders should sign that number,
  not discover it.
- Keep backups independent of the failure: separate account and
  credentials, cross-region, delete-protected (object lock or similar),
  with keys that survive the loss of the primary environment.
- Treat replicas as availability, not recovery: they replicate logical
  damage instantly and faithfully.
- Monitor restores, not just backups: a green "backup completed" panel
  says nothing about "restore would succeed", so track drill outcomes as a
  first-class signal.

## Interview Questions

### A team says "we have nightly backups, so RPO is 24 hours." What is wrong with that sentence?

Nothing about the sentence guarantees recovery at all, and RPO is a worst-
case property: a nightly 02:00 snapshot with a failure at 17:30 loses up
to 15.5 hours, so 24 hours is only an upper bound if backups always
succeed. RPO also presumes the backup is consistent and restorable.
A strong answer separates backup existence (an artifact) from RPO/RTO
(properties of a tested capability).

### Why can copying a running database's files produce a backup that "completes" but is useless?

Because pages are captured at different times, so multi-page structures
(heap and index, or a transaction's page set) are torn. The file may be
byte-complete and pass file-level checks, yet the restored server fails to
start or serves inconsistent data. The fixes are engine-aware: WAL
archiving with `pg_basebackup`, InnoDB hot backup with binlog replay, or
crash-consistent snapshots replayed through recovery.

### What did GitLab's 2017 incident teach about "five recovery mechanisms"?

That parallel mechanisms are not redundancy if none is verified: each of
the five failed for a distinct, mundane reason (not enabled, not
configured, mid-sync), and the single usable restore took about 18 hours
with roughly six hours of data lost. Redundancy of *beliefs* is not
redundancy of *capability*; only drills convert the former into the
latter.

### Design a backup strategy for a 1 TB database with an RTO of 4 hours and RPO of 5 minutes. What does the arithmetic force?

RPO 5 minutes rules out nightly snapshots as the only mechanism — you need
continuous WAL/binlog shipping to a secondary location. RTO 4 hours is
feasible on paper (1 TB at 200 MB/s is ~83 minutes of streaming) but the
budget must also cover WAL replay, standby rebuild, DNS and cache warm-up,
and first-attempt failures — which is why the strategy must include
scheduled full restores, since an unmeasured 4-hour RTO is a wish.

### Why are replicas not backups?

Replication is synchronous with respect to logical operations: a dropped
table, a bad migration, or corrupted application data is written to every
replica as fast as the primary. Replicas protect against node and disk
loss, not against damage the application itself caused. Backups with
history (point-in-time recovery) protect against logical damage because
they let you rewind to before the mistake — that temporal dimension is the
difference.

## Key Takeaways

- A backup is an artifact; recovery is a capability. Only a tested restore
  path connects them, and untested restores fail on mundane first contact.
- RTO is bounded by restore throughput, WAL replay, and warm-up — do the
  arithmetic in peacetime, not mid-incident.
- RPO is set by backup cadence and shipping; "nightly" means losing up to
  a day, and stakeholders should approve that explicitly.
- Databases need engine-aware, consistent capture; naive file copies of
  live engines produce plausible, unrestorable artifacts.
- Independence is part of the guarantee: separate credentials, cross-
  region, delete protection, and keys outside the blast radius.
- GitLab 2017 remains the definitive counterexample: five mechanisms, zero
  rehearsals, ~18 hours of restore, ~6 hours of data gone.

## Cross-References

- [Failure Casebook: GitLab 2017 Data Loss](../failure-casebook/gitlab-2017-data-loss.md)
  — the five failed recovery mechanisms, step by step
- [Failure Casebook: AWS DynamoDB 2015](../failure-casebook/aws-dynamodb-2015.md)
  — recovery-adjacent control planes fail under operational error too
- [Misconceptions: more-replicas-more-consistency](./more-replicas-more-consistency.md)
  — why replica count is not backup coverage: replication propagates
  logical damage instantly
- [Misconceptions: corruption-would-be-loud](./corruption-would-be-loud.md)
  — backups faithfully preserve silent corruption; verification at
  write time matters as much as the copy
- [Assumptions Hunt: Storage Durability](../assumptions-hunt/storage-durability.md)
  — the assumptions behind "the data is safe on disk"
- [Cloud: Disaster Recovery](../../cloud/disaster-recovery.md) — RTO/RPO
  tiers and the patterns that meet them
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- PostgreSQL documentation, *Continuous Archiving and Point-in-Time
  Recovery (PITR)* — the engine-aware backup mechanism referenced above.
  <https://www.postgresql.org/docs/current/continuous-archiving.html>
- GitLab. *Postmortem of the 17 January 2017 database outage* — cited by
  title; mechanics summarized via this collection's failure casebook
  chapter.
- Amazon Web Services. *AWS Well-Architected Framework, Reliability
  Pillar: backup and recovery guidance* — RTO/RPO strategy definitions,
  cited by title.
