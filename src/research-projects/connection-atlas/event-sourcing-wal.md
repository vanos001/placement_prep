# The Log Is the System: Git History, WAL, Event Sourcing, and CDC

## Overview

Five systems that look unrelated — a Git repository, a database's write-ahead log (WAL), an event-sourced application, a Debezium change-data-capture (CDC) pipeline, and an append-only audit trail — are all instances of one design decision: **keep an immutable, ordered log of what happened, and treat current state as a derived value computed from that log.** Once the log is the source of truth, a family of capabilities falls out almost for free: time travel (replay to a position), audit (the log *is* the record), replication (ship the log), and rebuildable read models (re-fold the log). The costs also fall out for free: replay cost grows with history, so every one of these systems eventually invents snapshots or compaction, and events written under an old schema must still be readable by new code.

This page explains each side independently, names the shared principle precisely, and is honest about the family's deepest structural difference: where the fold runs — snapshots versus deltas.

## The Concepts, Independently

**Git commit history.** A commit is a content-addressed snapshot: it points to a root tree that hashes the entire repository state at that moment, plus parent commit(s) and metadata (see [../../git/internals.md](../../git/internals.md)). The history is a directed acyclic graph of these snapshots; `git checkout <commit>` materializes the state at that point by *reading*, not by replaying, because each commit already caches the folded result. Refs (branches) are mutable pointers into an immutable graph, which is what makes `rebase` possible: rewrite the pointers to new commits while the old objects linger until garbage collection (see [../../git/rebasing.md](../../git/rebasing.md) and the history-rewrite row below).

**The database write-ahead log.** A relational database's durable state is a set of data pages on disk. Writing every touched page in place on every commit would be slow and non-atomic, so the engine instead appends a small record per change to the WAL *before* applying it to pages — the write-ahead rule. Commit = the WAL record is durably on disk (fsync); pages are updated lazily. Recovery after a crash = load the last checkpoint, then redo (and in ARIES-style engines, undo) the log from that point ([../../dbms/internals/wal.md](../../dbms/internals/wal.md), [../../dbms/transactions/aries.md](../../dbms/transactions/aries.md)). The same log does triple duty: it is the recovery mechanism, the input to physical streaming replication, and — exposed through logical decoding — the input to CDC.

**Event sourcing and CQRS.** Move the same idea to the application layer: the system's writes are events ("OrderPlaced", "ItemRemoved") appended to an event store; the current state of any aggregate is a left-fold over its events. Command Query Responsibility Segregation then separates the write side (validate command, append event) from any number of read models (projections) built by subscribing to the log and folding it into query-friendly shapes. Nothing in the write path needs to know how anything is queried; the log is the contract.

**Change data capture (Debezium).** Instead of inventing an application event store, *reuse the database's own log*. Debezium tails the WAL (Postgres logical decoding) or the binlog (MySQL), translates row changes into change events, and publishes them to Kafka, where downstream consumers fold them into caches, search indexes, and analytics stores ([../../data-engineering/debezium.md](../../data-engineering/debezium.md), [../../distributed/messaging-internals/kafka-log-internals.md](../../distributed/messaging-internals/kafka-log-internals.md)). A consumer's offset is exactly a WAL position: "state as of log position N."

**Append-only audit logs.** The compliance version of the same structure: an append-only record of who did what, when — ideally hash-chained so any retroactive edit breaks the chain. The regulatory insight is that the *append* is the primitive: you do not correct an audit log, you append a compensating entry.

## The Shared Principle

**State is a fold over an immutable, ordered event log; present state is a cache of that fold.** In notation: `state(t) = fold(events[1..t])`. Every member of this family picks a position in the log and calls the fold-result up to that position "the truth." This one equation explains the shared capabilities: *time travel* = fold to an earlier t; *audit* = the log itself is the evidence, and its order is the answer to "what exactly happened"; *replication and CDC* = ship positions of the same log to followers, who fold locally; *rebuild* = drop the cache (read model) and re-fold. It also explains the shared costs, which are the interesting part — see the breaks below.

The fold placement splits the family in two. WAL records and domain events store **deltas**: the fold runs at read/recovery time, so its cost is proportional to history unless you snapshot. Git commits store **snapshots**: the fold is computed incrementally at write time (each commit hashes its whole tree, but identical subtrees are shared by content address, so the incremental cost is small), and reading any version is O(1) hashing, not replay. Kafka sits deliberately between: records are deltas, but the broker can *compact* each key down to its latest value, maintaining a materialized fold continuously.

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS across all five | BREAKS (where the systems diverge) |
|---|---|---|
| Append as the only write | Commits, WAL records, events, CDC records, audit entries are all append-only | Git *refs* are mutable pointers over the immutable store; event stores usually allow only append (enforced), while databases keep their WAL format private and versioned with the engine binary |
| Replay = time travel | `checkout`, point-in-time recovery, rebuild an aggregate, re-run a projection, reprocess a topic from offset 0 | Cost grows with history: replay 10 events is trivial, replay 10⁹ is an outage plan — hence snapshotting everywhere (below) |
| The log is the truth | Every system can discard derived state and rebuild it | GitLab 2017: when log replicas (primary vs secondary Postgres) disagree about which log is authoritative and backups are stale, "the log is the truth" means the wrong log is unrecoverably wrong — see [../failure-casebook/gitlab-2017-data-loss.md](../failure-casebook/gitlab-2017-data-loss.md) |
| Compaction / snapshots | All need forgetting to bound replay | Mechanisms differ: WAL checkpoints discard pre-checkpoint redo; Kafka log compaction keeps last value per key; Git packfiles + reflog expiry prune unreachable snapshots; event sourcing adds explicit snapshot records mid-stream |
| Old events stay readable | All replay old records with new code | Schema evolution is the userland-hard problem: WAL formats are engine-private (upgrades gate on them), event-sourced systems must version every event type forever (upcasting), Git only needs to parse objects it still GCs |
| Correcting history | All can represent "it was wrong" | Git *rewrites* history (rebase makes new objects, moves refs); event-sourced and audit systems append compensating events — a fundamental split between snapshot-graph and delta-log worldviews |

The break that bites in practice: **pure delta-logs make reads pay for writes.** A fold over 10⁹ events answers one query about current state. Every member of the family that stores deltas therefore grows a snapshot layer (checkpoints, compaction, projections); the snapshot layer is itself a cache with all the usual invalidation obligations — which is why event-sourcing and caching advice converge (see [../why-not-handbook/caching-distributed.md](../why-not-handbook/caching-distributed.md)).

## A Concrete Worked Example

**A bank account, three ways.** Events: `deposit +100` (t1), `withdraw −30` (t2), `deposit +50` (t3). The fold gives balance 120.

- *Replay cost, small history:* rebuild = read 3 events ≈ microseconds. Correct and cheap.
- *Replay cost, large history:* an account with 10⁶ events × 200 B ≈ 200 MB of log; at a conservative 10⁵ events/s folded, one rebuild ≈ 10 s of CPU per aggregate per query — unacceptable. Fix: snapshot the fold every 1,000 events. Rebuild now = load 1 snapshot + fold ≤ 999 events ≈ milliseconds. The snapshot interval is a textbook tuning knob: more frequent snapshots cost write I/O; less frequent cost recovery time.
- *The same arithmetic in the database:* a Postgres instance takes 10⁶ updates between checkpoints. Crash recovery re-reads (up to) 10⁶ WAL records; doubling checkpoint frequency halves worst-case recovery time but doubles background write load during normal operation. Checkpoint tuning and event-store snapshot intervals are the *same knob* ([../../dbms/transactions/checkpointing.md](../../dbms/transactions/checkpointing.md)).
- *The same arithmetic in CDC:* a Debezium connector that is down for a day does not lose data — on restart it resumes from its retained LSN — but the upstream WAL accumulates every record the slot has not acknowledged. A slot left behind by a decommissioned consumer makes the WAL grow without bound until the disk fills; the log's strength (nothing is lost) is simultaneously its operational failure mode.

**Git as the counterfactual:** the same account as a Git repo — one commit per transaction — would make "balance at t3" a checkout, not a replay, because each commit caches the full state. The price appears on the write path: every tiny change re-hashes the whole tree path (mitigated to near-zero by content-addressed subtree sharing — see [./git-cas.md](./git-cas.md)). Delta-logs amortize cost to reads; snapshot-graphs amortize cost to writes.

## When This Connection Is Useful

- **Event-driven design.** "Should this service be event-sourced?" becomes checkable: does the domain's value lie in the sequence of facts (ledger, order lifecycle, clinical record), or only in current state (user profile)? Do you need the audit trail anyway? If the log is required for compliance, folding state from it may be nearly free.
- **Interview: "add undo / audit / version history to X."** The senior answer is structural: append an event log under the mutations, project current state as a fold, snapshot to bound replay, and expose time travel as fold-to-position. This one template answers undo (fold to t−1), audit (the log), offline sync (ship the log), and debugging (replay production inputs).
- **Engineering decisions.** CDC before dual-writes: two systems that both mutate state drift; one log, many folds, cannot drift. Snapshot intervals and compaction policies are first-class design artifacts — budget them explicitly. When a read model is wrong, the recovery is always the same three steps: fix the projection, delete the cache, re-fold — which is only possible because the log was kept.

## Interview Questions

1. Given the event list `+100, −30, +50`, explain why the account balance is "a fold over the log" and what exactly the snapshot layer caches. At what history size does snapshotting pay for itself, and what does the trade-off curve look like?
2. Git commits are snapshots; WAL records are deltas. Give one capability each design buys that the other must simulate, with the mechanism of the simulation.
3. A Debezium consumer is decommissioned but its replication slot is left behind. Explain, in terms of log positions and folding, why the database's disk fills — and two operational guards against it.
4. Your event-sourced aggregate needs a schema change: the field `amount` becomes `amountMinor` (integer cents). What are your options for replaying events written under the old schema, and what does each cost?
5. Why does event sourcing make "correcting a wrong event" structurally different from `git rebase`, and why is a compensating event the standard answer on the log side?

## Key Takeaways

- State as a fold over an immutable, ordered log is one idea that instantiates as Git history, database WAL, event sourcing, CDC, and audit logs — with the same capabilities (time travel, audit, rebuild) and the same costs (replay growth, schema evolution).
- Where the fold runs is the key design choice: delta-logs fold at read/recovery time and grow snapshots; snapshot-graphs (Git) fold at write time and pay on the write path.
- Every member of the family grows a forgetting mechanism — WAL checkpoints, Kafka compaction, Git GC, event-store snapshots — and the forgetting policy is where the real engineering lives.
- "The log is the truth" is only as good as the log's own redundancy; when log replicas disagree, you are in backup territory, not replay territory.
- Correcting history splits the family: rebase-and-forget (Git) versus append-a-compensation (events, audit). Choose per domain, not by habit.

## Cross-References

- [./git-cas.md](./git-cas.md) — Git as Content-Addressable Storage — why each commit is a snapshot and how content addressing makes snapshotting cheap.
- [./transactions-concurrency-control.md](./transactions-concurrency-control.md) — Transactions and Concurrency Control — the ordering contract that decides which events may enter the log.
- [./incremental-computation.md](./incremental-computation.md) — Incremental Computation — read models as memoized folds and the invalidation rules that keep them sound.
- [../../dbms/internals/wal.md](../../dbms/internals/wal.md) — Write-Ahead Log Internals — the canonical delta-log: redo/undo, LSNs, and full-page writes.
- [../../dbms/transactions/aries.md](../../dbms/transactions/aries.md) — ARIES Recovery — the reference algorithm for folding a WAL back into consistent state.
- [../../dbms/transactions/checkpointing.md](../../dbms/transactions/checkpointing.md) — Checkpointing — the snapshot knob and its recovery-time/write-load trade.
- [../../git/internals.md](../../git/internals.md) — Git Internals — object model and refs, the snapshot-graph side of the family.
- [../../os/filesystems/journaling.md](../../os/filesystems/journaling.md) — Filesystem Journaling — the same append-before-mutate rule one layer down.
- [../../data-engineering/debezium.md](../../data-engineering/debezium.md) — Debezium and CDC — turning the database's own log into an integration bus.
- [../../distributed/messaging-internals/kafka-log-internals.md](../../distributed/messaging-internals/kafka-log-internals.md) — Kafka Log Internals — offsets, retention, and log compaction as fold maintenance.
- [../assumptions-hunt/filesystem-durability.md](../assumptions-hunt/filesystem-durability.md) — Filesystem Durability Assumptions — what fsync actually promises to the append.
- [../failure-casebook/gitlab-2017-data-loss.md](../failure-casebook/gitlab-2017-data-loss.md) — GitLab 2017 Data Loss — when "the log is the truth" picks the wrong truth.
- PostgreSQL documentation: Reliability and the Write-Ahead Log, <https://www.postgresql.org/docs/current/wal-internals.html>.
- Debezium documentation, <https://debezium.io/documentation/>.
- Fowler, M., "Event Sourcing," <https://martinfowler.com/eaaDev/EventSourcing.html>; Kleppmann, M., *Designing Data-Intensive Applications*, chs. 3, 11 (O'Reilly, 2017).
- Chacon, S. & Straub, B., *Pro Git*, 2nd ed. — Git internals book, <https://git-scm.com/book/en/v2/Git-Internals-Git-Objects>.
