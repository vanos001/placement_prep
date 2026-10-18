# Follow-up Tree: ACID Transactions

## Overview

"What does ACID mean?" is the database interview's entry point, and it escalates ruthlessly because the acronym's four letters are *not* four mechanisms of equal depth: Atomicity, Isolation, and Durability are implemented by specific machinery you can be asked to walk through, while Consistency is an *outcome* the other three serve — and candidates who answer all four letters with the same confidence reveal they have never been asked what actually enforces each one. This page walks the ladder: what each follow-up tests, how to reason, and the answer with its edge cases. Isolation gets the deepest treatment here because it is where interviewers live; the sibling deep-dive on lock tables and version storage is [Transactions and Concurrency Control](../connection-atlas/transactions-concurrency-control.md), and the repo's mechanism pages — [Isolation Levels](../../dbms/transactions/isolation-levels.md), [MVCC](../../dbms/transactions/mvcc.md) — own the internals this chain links to.

## The Opening Question

**"What does ACID mean?"**

The expected core answer names each letter *with its mechanism*, not just its slogan. **Atomicity**: a transaction's writes are all-or-nothing — the mechanism is an undo log / rollback segment the recovery manager replays if the transaction aborts. **Consistency**: a transaction moves the database from one valid state to another — constraints hold before and after — and the honest phrasing is that C is the *goal*; A, I, and D are the mechanisms that make it reachable ([Haerder & Reuter, "Principles of Transaction-Oriented Database Recovery", 1983] are the source of the A-I-D framing; [Gray, "The Transaction Concept: Virtues and Limitations", 1981] made the consistency-as-preservation point). **Isolation**: concurrent transactions do not observe each other's intermediate states — with the crucial caveat that isolation is a *spectrum of levels*, not a boolean (rung 2). **Durability**: once committed, the transaction survives crashes — the mechanism is write-ahead logging: the commit record reaches stable storage (fsync) before the commit is acknowledged.

Why this answer is correct: the slogan version ("all-or-nothing, consistent, isolated, durable") is unfalsifiable and therefore ungradeable; the mechanism version predicts every follow-up — "how do you roll back?" (undo log), "what does commit actually mean?" (a durable log record), "can two transactions see each other's work?" (depends on the level). Stating that C is an outcome and AID are machinery is the sentence that reframes the whole interview from vocabulary to architecture.

## Follow-up 1: What Does Each Letter Actually Cost?

**What it tests:** whether the four letters are mechanisms you can price — the difference between reciting the acronym and engineering with it.

**How to reason:** take each letter and name the data structure that implements it and the runtime operation that exercises it.

**Answer.** **Atomicity** costs an undo log: before modifying a page, the old value is recorded so an abort can restore it — every write pays logging overhead even if no transaction ever aborts. **Isolation** costs either *blocking* (locks acquired and held until commit — the 2PL of rung 3) or *versioning* (extra versions stored and garbage-collected — MVCC), plus the conflict-detection logic itself. **Durability** costs the WAL write and an `fsync` on the commit path — the single most expensive synchronous I/O in most databases, which is why group commit (batching several transactions' fsyncs into one) exists: durability is paid per *batch*, not per transaction. **Consistency** costs constraint checking — foreign keys, uniqueness, triggers — executed inside the engine where isolation protects them. The senior observation to volunteer: every one of these costs is *optional in some system*, and the products differ exactly there — NoSQL stores that drop real isolation (rung 6), databases with `synchronous_commit = off` (durability relaxed to "durable within a small window"), engines without undo logs (atomicity via whole-page snapshots). The acronym describes a *bundle*, and bundles are negotiable — which is precisely what the follow-ups negotiate.

## Follow-up 2: "Isolated" Isn't a Boolean — Walk the Isolation Levels

**What it tests:** the most commonly escalated rung: whether you know the SQL isolation levels as *anomaly catalogs*, not as labels — and can spot which anomalies each level permits.

**How to reason:** each level is defined by the anomaly it forbids; the levels form a ladder where each rung kills one more way concurrent transactions can observe each other.

**Answer.** The catalog ([Berenson et al., "A Critique of ANSI SQL Isolation Levels", 1995] is the canonical analysis, including the ambiguities in the standard itself): **Read Uncommitted** permits dirty reads (seeing another transaction's uncommitted writes); **Read Committed** forbids dirty reads but permits non-repeatable reads (your own re-read of a row changes because another transaction committed in between) and phantoms (new rows matching your earlier query appear); **Repeatable Read** additionally forbids non-repeatable reads but — in its snapshot implementation — still permits **write skew**: two transactions each read a disjoint predicate, each writes based on it, and the *pair* violates a constraint neither transaction broke alone — the classic example is two doctors checking that at least one doctor is on call, each seeing the other on call and going off duty, leaving zero. **Serializable** forbids everything: the result is equivalent to some serial order. Two implementation notes that show depth: PostgreSQL's REPEATABLE READ is snapshot isolation (not the SQL standard's locking semantics — see [PostgreSQL's MVCC chapter](https://www.postgresql.org/docs/current/mvcc-intro.html)), and its SERIALIZABLE is SSI — serializable snapshot isolation — which detects the dangerous structures (rw-antidependency cycles) write skew creates and aborts one transaction. The full anomaly table and per-engine defaults live in [Isolation Levels](../../dbms/transactions/isolation-levels.md), and the sibling interrogation of what "isolated" assumes is [Database Isolation](../assumptions-hunt/database-isolation.md).

## Follow-up 3: Two Ways to Get It — 2PL or MVCC?

**What it tests:** whether you can compare the two canonical concurrency-control families on mechanism, not marketing — readers-writers locking versus versioned snapshots.

**How to reason:** both must prevent the anomalies of the chosen level; ask what each *blocks*, what each *stores*, and what each does on conflict.

**Answer.** **Two-phase locking** (the growing/shrinking phases; the mechanism in [Lock-Based Concurrency Control](../../dbms/transactions/lock-based.md)) has transactions acquire read/write locks and hold them to commit: conflicts *block*, aborts resolve deadlocks (detection via wait-for graphs, or prevention via ordered acquisition), and readers serialize behind writers — throughput falls under read-write contention, but the enforcement is simple and per-row. **MVCC** ([MVCC](../../dbms/transactions/mvcc.md) for the internals) gives each transaction a snapshot: writers create *new versions* and never block readers; readers see the consistent snapshot chosen at their start; no read ever waits. The costs move rather than vanish: version storage grows (PostgreSQL's dead-tuple vacuum is the garbage collector for old versions — [PostgreSQL MVCC internals](../../dbms/internals/postgresql-mvcc-deep.md) walks it), update-in-place engines maintain undo chains, and — the rung's key subtlety — **snapshot isolation is not serializable** by default: two blind writes to the same row conflict, but the write-skew pattern (read a predicate, write elsewhere) does not, so serializable MVCC needs the extra conflict machinery (first-updater-wins on predicates, SSI's cycle detection). The decision framing: 2PL wins on read-mostly-less, write-hot, short transactions where lock waits are bounded; MVCC wins overwhelmingly where reads dominate and blocking readers is unacceptable — which is most OLTP — at the price of version GC and the anomalies-above-snapshot ceiling. The engine-level comparison table is [Transactions and Concurrency Control](../connection-atlas/transactions-concurrency-control.md).

## Follow-up 4: Commit Is a Log Write — What Does WAL Actually Buy, and When Does It Lie?

**What it tests:** durability's mechanism end to end: log-before-data, checkpointing, and the storage stack's habit of caching writes when you told it not to.

**How to reason:** durability is a promise about *crashes*, so walk the write path to stable storage and ask where the promise can break.

**Answer.** **Write-ahead logging** enforces one rule: the log record describing a change reaches stable storage *before* the changed data page does ([PostgreSQL's WAL intro](https://www.postgresql.org/docs/current/wal-intro.html)). Three wins: an undo/redo log makes atomicity and durability share one mechanism (redo for committed transactions whose data pages were lost, undo for uncommitted ones — the recovery procedure is the subject of the sibling page [Crash Recovery](../why-not-handbook/crash-recovery.md)); sequential log appends turn random page writes into a sequential log write that can be batched (group commit); and checkpoints bound recovery time by forcing dirty pages to disk and marking a log position to replay from. The "when it lies" half is the senior content: `fsync` is a promise from the kernel, and the device below may break it — disks with volatile write caches that acknowledge writes before the platters/flash have them (fixed by `barrier`/FUA settings or write-through cache modes), and network-attached storage that acknowledges before replication completes. Durability is therefore a *chain* (process → kernel page cache → device cache → media), and "we have WAL" only means as much as the weakest link — the same lesson the journaling-filesystem story tells in [Filesystem Journaling](../../os/filesystems/journaling.md). The cost arithmetic to volunteer: one fsync ≈ a disk-seek timescale on spinning rust, ~hundreds of microseconds to milliseconds on NVMe — which is why the durability knob is the first thing throughput-tuning touches, and why relaxing it is a *business decision* (how many committed transactions may vanish in a crash?) dressed as a config flag. The event-sourcing cousin of the same log — where the log *is* the database — is [Event Sourcing and WAL](../connection-atlas/event-sourcing-wal.md).

## Follow-up 5: A Transaction Updates Rows on Two Databases — What Is Distributed ACID?

**What it tests:** two-phase commit: the protocol, its blocking window, and why it is both necessary and hated.

**How to reason:** atomicity across participants needs a vote; a vote needs a coordinator; a coordinator that can crash creates an in-doubt state that no local protocol can resolve.

**Answer.** **Two-phase commit**: phase 1, the coordinator asks every participant to *prepare* (apply everything, write the prepare record durably, but do not commit); phase 2, if all vote yes, the coordinator writes its commit decision durably and informs everyone. The mechanics and their failure windows live in [Distributed Transactions](../../dbms/transactions/distributed.md); the rung's depth is the *blocking* property: if the coordinator crashes after some participants voted yes, those participants hold locks and cannot unilaterally abort (the decision might have been "commit") or commit (it might have been "abort") — they are **in doubt** until the coordinator recovers. The costs to price: two extra synchronous round trips plus a forced log write per participant *before* the user's commit can return — 2PC is latency on every transaction, not just failed ones. The modern counter-proposal to volunteer: replace the coordinator's single point with **consensus** — each shard replicates its decision via Raft ([Raft](../../distributed/consensus/raft.md)), and the commit becomes a sequence of consensus agreements; that buys fault-tolerant coordination while keeping the round trips. The senior framing: 2PC's problem is not that it is wrong — it is the only way to get distributed atomicity without additional assumptions — but that it converts a crash into a stall and adds latency to the happy path; both costs are why "do you actually need cross-database atomicity?" is the first question to ask, and sharding so a transaction touches one shard is the cheapest 2PC elimination there is.

## Follow-up 6: "What If You Only Need CA?" — Unpacking the Last Escalation

**What it tests:** whether you can disentangle ACID's C from CAP's C, and whether "drop the ACID bundle" gets reasoned rather than recited.

**How to reason:** the question conflates two different C's and two different failure models. Separate them, then reason about which letters the workload genuinely needs.

**Answer.** First, the disentangling: ACID's **C** is *constraint preservation* (foreign keys hold, invariants pass), a property of the transaction processing model; CAP's **C** is *linearizability of reads and writes* in a replicated, partition-prone distributed system — different property, different setting, and the confusion between them is documented in [Consistency and Availability vs Partition Tolerance](../misconceptions/consistency-availability-partition.md) and [CAP](../../distributed/fundamentals/cap.md). A single-node database does not face network partitions among its components, so "choosing CA" there is a category error — the real question is *which isolation level and which durability knob* the workload needs (rungs 2 and 4). Second, the reasoning about relaxing letters, which *is* a real design space: drop **I** to read-committed or below and you gain concurrency at the price of anomalies your application must tolerate or re-check; relax **D** to `synchronous_commit = off`-style bounded durability and you gain group-commit throughput at the price of losing a small window of committed transactions on crash; drop **A** across services (no distributed transaction, compensate instead — sagas) and you gain availability at the price of writing compensation logic for every failure path. The interview-winning shape: "ACID is a bundle priced per letter; tell me the workload's anomaly tolerance and crash-window tolerance, and I will tell you which letters you can cheapen — and C-as-constraints I would keep wherever the data has invariants, because the engine enforces it cheaper than code can."

## How to Approach Unfamiliar Variations

The transferable template for transaction follow-ups:

1. **Translate every claim into a mechanism and its cost.** "Isolated" → which level, enforced by locks or versions, paid in blocking or version GC; "durable" → which fsync, on which device chain; "atomic" → undo log or snapshot. The acronym is a map of mechanisms; answers that name mechanisms survive every follow-up.
2. **When anomalies appear, name the read/write interleaving precisely.** Write skew is not a lost update; a phantom is not a non-repeatable read. Replaying the exact interleaving ("T1 reads predicate P, T2 writes outside P and commits, T1 writes based on P") is how you prove which level permits it — and how you sound like someone who has debugged isolation, not read about it.
3. **Locate the log before believing a durability claim.** Recovery time, group-commit batching, and device cache behavior all follow from the WAL's position in the write path; "it's durable" without "which write reached which medium" is incomplete.
4. **For distributed questions, find the blocking window.** Any protocol with a coordinator (2PC, sagas' orchestration) has a state where progress waits on one node's recovery; any protocol built on consensus moves that window into quorum logic. Naming the window is the analysis; comparing protocols is choosing where it lives.

## Interview Questions

**Q: Your team sets isolation to SERIALIZABLE everywhere "to be safe." What breaks?**
A: Throughput first: SSI detects rw-antidependency cycles and *aborts* transactions that might have produced write skew, so contended workloads see retry storms, and every caller needs retry logic. More subtly, serializability changes what "safe" means for read-only analytics on the same engine. The better default is the weakest level that makes the app's invariants hold — usually READ COMMITTED with explicit checks for the few genuinely skew-sensitive invariants.

**Q: A credit-limit check reads the customer's balance, then debits. Under snapshot isolation, what can go wrong?**
A: Write skew: two concurrent debits each read the same balance, each sees sufficient funds, both commit — the pair's effect violates the constraint neither violated alone, because each transaction's writes were outside the rows it read. Fixes: SELECT FOR UPDATE on the read (materialize the conflict), serializable isolation (SSI catches it), or an invariant-level redesign (a single atomic UPDATE with the check in the WHERE clause).

**Q: Why does `synchronous_commit = off` not mean "uncommitted data is lost"?**
A: It means the commit acknowledgment races the durable fsync: the WAL write is issued but the server may acknowledge before it reaches stable media. On clean operation nothing is lost; on a *crash* within the window (typically bounded to the fsync interval, since group commit flushes continuously) recently acknowledged commits may vanish — while the database itself remains consistent. It converts "no acknowledged commit is ever lost" into "at most N milliseconds of acknowledged commits may be lost," which is a different contract and must be sold as one.

**Q: Why is 2PC still the answer in Spanner-style systems despite its blocking reputation?**
A: The blocking window is removed by replicating *both* the participants and the coordination decision via consensus: a crashed coordinator no longer strands in-doubt participants because the decision is recoverable from the quorum. What remains of 2PC's cost is the latency — the extra round trips are intrinsic to getting a *unanimous, durable* vote — and that cost is paid for genuine multi-shard atomicity, which the workload (or the query planner) chooses to incur.

## Key Takeaways

- ACID is four mechanisms plus one outcome: undo log (A), locks or versions (I), WAL and fsync (D) — and C is the constraint-preservation goal those mechanisms serve, not a mechanism itself.
- Isolation is a ladder of forbidden anomalies; the levels are defined by dirty reads, non-repeatable reads, phantoms, and — above snapshot isolation — write skew, which is the anomaly that separates "repeatable read" from "serializable" in practice.
- 2PL blocks (deadlocks, aborts, no reader starvation) and MVCC versions (readers never wait, version GC, snapshot-isolation ceiling); serializable MVCC needs SSI's extra detection.
- WAL turns durability into a sequential log write plus a recovery protocol — and its guarantee is only as strong as the weakest storage layer between the kernel and the media.
- Distributed atomicity is 2PC's vote plus its blocking window; consensus-based designs remove the single-coordinator cliff while keeping the round-trip cost — and the cheapest transaction is the one that touches one shard.
- ACID's C and CAP's C are different properties in different settings; "which letters do you need" is answerable only per workload, per letter.

## Cross-References

- [Transactions and Concurrency Control](../connection-atlas/transactions-concurrency-control.md) — the sibling deep-dive: lock tables, version storage, and engine comparisons.
- [Crash Recovery](../why-not-handbook/crash-recovery.md) — the sibling page that walks WAL replay, checkpoints, and the ARIES lineage end to end.
- [Event Sourcing and WAL](../connection-atlas/event-sourcing-wal.md) — when the log is not just recovery machinery but the system of record.
- [Database Isolation](../assumptions-hunt/database-isolation.md) — the hidden assumptions inside "isolated," interrogated.
- [Consistency and Availability vs Partition Tolerance](../misconceptions/consistency-availability-partition.md) — CAP's C versus ACID's C, as a documented misconception.
- [Isolation Levels](../../dbms/transactions/isolation-levels.md) — the full anomaly table and per-engine defaults.
- [Lock-Based Concurrency Control](../../dbms/transactions/lock-based.md) — 2PL's phases, deadlocks, and lock managers.
- [MVCC](../../dbms/transactions/mvcc.md) — snapshots, version chains, and conflict rules.
- [PostgreSQL MVCC Internals](../../dbms/internals/postgresql-mvcc-deep.md) — vacuum, dead tuples, and the price of version storage.
- [Distributed Transactions](../../dbms/transactions/distributed.md) — 2PC variants and their failure windows.
- [Filesystem Journaling](../../os/filesystems/journaling.md) — the same log-before-data discipline below the database.
- [Raft](../../distributed/consensus/raft.md) — the consensus primitive modern coordination layers build on.
- [CAP](../../distributed/fundamentals/cap.md) — the theorem behind the "CA" confusion.
- [PostgreSQL MVCC Intro](https://www.postgresql.org/docs/current/mvcc-intro.html) — the engine's own statement of its isolation model.
- [PostgreSQL WAL Intro](https://www.postgresql.org/docs/current/wal-intro.html) — write-ahead logging from the documentation.
