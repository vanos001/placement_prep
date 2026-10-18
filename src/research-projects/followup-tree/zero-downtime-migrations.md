# Follow-up Tree: Zero-Downtime Migrations

## Overview

"How do you change a table's schema in a system that cannot stop taking traffic?" is the database-engineering ladder that looks like an operations question and lands as a correctness question: every step of an online migration is a distributed-consistency problem between *code versions* and *data versions*, because — the sentence the whole chain hangs on — **during a rolling deploy, multiple versions of your code run against multiple versions of your schema at the same time.** Interviewers on backend and platform teams use this chain to find the candidates who have actually run an expand-contract migration versus those who have read about one: the veterans know why you never rename a column in one step, why backfills cannot be one giant transaction, and why the rollback story is written *before* the cutover, not after it fails. This page walks the ladder — what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. Handoffs are deliberate: the transaction and WAL machinery underneath is the chain in [ACID Transactions](./acid-transactions.md), the log-as-spine view that makes change-data-capture migrations work is [Event Sourcing and WAL](../connection-atlas/event-sourcing-wal.md), and the schema-compatibility audit that governs safe format evolution is [Serialization Compatibility](../assumptions-hunt/serialization-compatibility.md). Book-level depth: [Schema Migrations](../../dbms/advanced/schema-migrations.md) and the release discipline in [Canary Releases](../../sre/canary-releases.md).

## The Opening Question

**"You need to add a column to a 2-billion-row table that serves live traffic. Walk me through it."**

The expected core answer: never do it as one blocking operation. Add the column as nullable (or with a default computed lazily — the per-vendor semantics of `DEFAULT` on `ADD COLUMN` are the first correctness trap), deploy code that writes it while tolerating its absence on read, backfill in batches, then make it non-null / start reading it / drop the old path — in that order, with each step deployable and reversible.

A weak answer says "run ALTER TABLE in a maintenance window" — the answer being replaced, since the premise is *zero* downtime; it also usually cannot say *why* a naive ALTER blocks (metadata locks, table rebuilds, the write amplification of rewriting a table the chain in [Database Indexes](./database-indexes.md) prices). The strong answer states the invariant from the start: every intermediate state must be one that *both* the old code and the new code can operate correctly against, in both directions — that is what "zero downtime" means mechanically. The follow-up that escalates: **"OK — but the code deploys take 20 minutes and the backfill takes 6 hours. What is the full choreography?"**

## Level 2: The Expand–Contract Pattern — Why Three Phases

**What it tests:** whether the candidate can state the pattern's phases and — the part that separates understanding from memorization — why each phase's *deploy ordering* is what makes it safe.

**Weak answer:** "Add the new column, migrate the data, remove the old column" — three steps with no deploy sequencing, which is exactly the procedure that causes an outage.

**Strong answer:** expands the phases into code-and-schema interleavings: expand (schema gains new structure; old code ignores it, new code writes both), migrate (data backfill; both code versions work throughout), contract (old structure removed *after* no running code reads it) — and knows the phase boundaries are gated by *deploys*, not by ALTER statements, because deploys are the slow, risky part.

**Escalation trigger:** "Why can't you just rename a column with a new deploy that also uses the new name?"

**Answer.** Because deploys are not atomic across a fleet: rolling updates mean old instances and new instances serve traffic simultaneously, so a rename breaks the old instances the instant the ALTER commits — they query a column that no longer exists and every request touching it fails until the roll finishes (and rollback is impossible without a reverse migration). Expand–contract dissolves the rename: *expand* adds `new_name` and a sync mechanism; code writes both columns (old reads old, new reads new, each version stays correct against either state); *contract* drops `old_name` only after the fleet is fully on the new code — and after you have verified no code path (including cron jobs, scripts, read replicas' consumers) still references it. The same logic governs index changes, splits/merges of tables, and column type widening; the pattern catalog with vendor-specific ALTER semantics (instant vs rebuilding) is the book page [Schema Migrations](../../dbms/advanced/schema-migrations.md). The senior framing: expand–contract is the database echo of rolling-deploy compatibility — the schema is a *protocol* between code versions, and the compatibility rules are the same ones as wire formats, audited in [Serialization Compatibility](../assumptions-hunt/serialization-compatibility.md).

## Level 3: Backfills — Batching, Throttling, and Resumability

**What it tests:** operational maturity: whether the candidate has thought about the mechanics of rewriting a large table under live traffic — locking interactions, replication lag, failure mid-backfill — rather than imagining UPDATE as a single step.

**Weak answer:** "UPDATE the rows where the column is null" — one statement, which is one enormous transaction: row locks held for hours, replicas falling behind, WAL bloat, and one deadlock losing *all* progress.

**Strong answer:** backfills in bounded batches (by primary-key range, not OFFSET), throttled against replication lag and primary load, resumable from a checkpoint (each batch commits independently), idempotent by construction (safe to re-run), and sequenced to respect index and trigger costs.

**Escalation trigger:** "Your batched backfill is running and the read replicas are 90 seconds behind. What do you do?"

**Answer.** Lag is the backfill's throttle signal: each batch's writes replicate asynchronously to replicas (the lag mechanics are the chain in [Replication Lag](./replication-lag.md)), and a backfill that outruns apply throughput turns every replica stale — which, if any readers are replica-routed, is a user-visible consistency regression *you* caused. The fix is closed-loop pacing: measure replica lag (heartbeat age, per Level 3 of that chain) and size or pause batches to keep it under a budget; batch by key range so each statement touches contiguous rows (no OFFSET scans, which re-read from the start), keep each transaction short so row locks release and WAL segments truncate, and checkpoint progress in a migration-state table so a crash resumes instead of restarting. The vendor-specific wrinkle the strong answer names: MySQL's online DDL and pt-online-schema-change / gh-ost *also* backfill — they copy the table under triggers or binlog replay — so "backfill" is sometimes the DDL itself; PostgreSQL 11+ makes `ADD COLUMN ... DEFAULT` an instant metadata change *but* rewriting values on update, so the cost moves rather than vanishes. The judgment sentence: a backfill is a bulk data transfer wearing a database hat — throughput, throttle, resume, and idempotence are its design requirements, exactly as they would be for any ETL.

## Level 4: Dual-Write, CDC, and the Cutover — Writing the Truth Twice

**What it tests:** the hardest correctness rung: when the migration needs *two* sources of truth to stay consistent (old and new store, or old and new shape), the candidate must know why application-level dual-write is subtly broken and how log-based CDC fixes it.

**Weak answer:** "Write to both the old and new schema in the same function" — the dual-write trap: two writes are not one transaction, and partial failure between them silently forks the truth.

**Strong answer:** explains the dual-write failure modes (crash between writes, different failure semantics, no ordering guarantee across targets), and presents change-data-capture as the fix: make the *old* store's log the source, stream its changes into the new structure, verify convergence, then cut reads over — the log becomes the spine, which is exactly the connection the atlas page [Event Sourcing and WAL](../connection-atlas/event-sourcing-wal.md) develops.

**Escalation trigger:** "During dual-write, the new-schema write fails after the old-schema write committed. What is the state of the system, and how does CDC change the answer?"

**Answer.** The state is *inconsistent by design*: the old store has the change, the new one does not, and nothing recorded the gap — the application-level dual-write has no atomicity across targets, and "retry on failure" cannot restore ordering when later writes succeed first (out-of-order application breaks updatable states like counters and balances). Retrying via a background queue converts the bug into a slower bug: queue ordering, duplicate delivery, and the dead-letter path all become correctness components. CDC restructures the problem: the application writes only to the old (primary) store; the *commit log* — the same WAL/binlog machinery [ACID Transactions](./acid-transactions.md) builds durability on — is consumed and applied to the new structure, which inherits the log's ordering and exactly-once-ish semantics (dedup by position), so the new store converges as a *replica* of the old, not as a sibling guess. PostgreSQL's logical replication is the production-grade instance of the idea ([PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html)). The cutover then becomes verifiable: run in shadow (backfill + streaming) until checksums or read-comparison harnesses agree, flip reads (gradually — the canary discipline in [Canary Releases](../../sre/canary-releases.md)), then make the new store primary and the old one the replica being caught up — the same promotion script, with the same fencing concerns, as the failover rung of [Replication Lag](./replication-lag.md).

## Level 5: Rollback and Deploy Ordering — the Judgment Rung

**What it tests:** the boundary rung: whether the candidate designs migrations *backwards* — every step reversible, every deploy order pinned — and can defend the full choreography under the constraint "we must be able to abort at any point."

**Weak answer:** "We keep a down-migration script" — a down-script is not a rollback plan if data has changed shape in the meantime (a dropped column's values are gone; a merged table's provenance is lost).

**Strong answer:** distinguishes schema rollback (cheap, pre-contract) from data rollback (often impossible after contract — which is why contract waits); pins the deploy/migration ordering rule (schema first with old-code compatibility, code second, cleanup last, each phase observed); names the operational gates — feature flags for cutover control, dual-read verification, error-budget-based abort criteria — and treats "migrations as deployable artifacts" with their own review, rehearsal on production-shaped data, and timeout/lock monitoring.

**Escalation trigger:** "Mid-migration, the new code shows a 2 percent error rate on the new path. The backfill is 70 percent done. Abort or continue — and what exactly do you do?"

**Answer.** The decision is cheap *because the choreography made it cheap*: if the error is in new-code-only behavior, roll back the *deploy* (old code still works — the expand phase guaranteed it) while leaving the expanded schema and the in-progress backfill in place; the backfill is idempotent and resumes later. Nothing is lost because contract never ran. That is the payoff of the ordering rule, and the rung's answer is mostly naming the gates: abort criteria defined *before* the migration (error rate, lag, lock-wait thresholds — the SLO-driven discipline in [SLOs and Error Budgets](./slos-and-error-budgets.md)), cutover behind a feature flag so the flip is a config change and the rollback is a config change (the flag mechanics in [Feature Flags](../../sre/feature-flags.md)), and the irreversible step — contract — scheduled only after a full soak with the new shape, because data rollback after contract is archaeology, not engineering. The senior synthesis ties the ladder together: "zero downtime" is not a property of any single tool (gh-ost, logical replication, pg_repack); it is a property of an *ordering* — expand, migrate, cut over behind flags, contract last — in which every state of the world is one some running version of the code was designed for, and every step forward has a step back.

## How to Approach Unfamiliar Variations

The template for migration variations — "merge two tables," "shard a monolithic database," "change primary keys," "move stores entirely":

1. **State the invariant first: old code and new code must both be correct against every intermediate state.** Then derive the phases — everything else (tool choice, CDC versus triggers, backfill scripts) is implementation under that constraint.
2. **Find the two-truths window.** Any migration that copies data has a period with two representations; ask what makes them converge (log-based CDC with ordering beats application dual-write) and what verifies they did (checksums, dual reads, comparison harnesses).
3. **Make every step resumable and idempotent.** Batches by key range, checkpoints, re-run safety — the migration *will* be interrupted; design for the restart you know is coming.
4. **Write the rollback before the cutover, and classify what is reversible.** Schema pre-contract is reversible; data shape changes after contract usually are not. The judgment is scheduling the irreversible step as late and as small as possible.

## Interview Questions

**Q: `ALTER TABLE users ADD COLUMN status VARCHAR DEFAULT 'active'` — instant or blocking? Walk through the considerations.**
A: Vendor-dependent, which is the point: PostgreSQL 11+ stores the default as catalog metadata and evaluates it on read — instant, but rows rewritten on later updates carry the real value; MySQL 8.0 does instant adds for some cases but a default requiring rewrite (or older versions) rebuilds the table under metadata locks that queue behind long transactions. The safe general answer: treat it as potentially blocking, run it with lock-timeout and retry, and remember old code must tolerate the column anyway (expand phase) — the DDL mechanics are in [Schema Migrations](../../dbms/advanced/schema-migrations.md).

**Q: A teammate proposes running the backfill as one big transaction "so it's atomic." What is wrong with that?**
A: Atomicity is the wrong goal at that scale: one transaction holds row locks for its full duration (blocking concurrent updates), generates a WAL blob that balloons replication lag and bloats the log, risks snapshot bloat (vacuum/XIDS issues), and — fatal for operations — *all-or-nothing* means a crash at 90 percent restarts from zero. Batched, checkpointed, idempotent batches give you per-batch atomicity plus resumability; the whole-run "atomicity" is replaced by the idempotence guarantee that re-running any batch converges.

**Q: Why is application-level dual-write considered an anti-pattern, and what replaces it?**
A: Two writes across two targets have no shared atomicity or ordering: a crash between them forks the truth, retries arrive out of order, and neither store can tell which version is current. The replacement is making the *old* store authoritative and deriving the new one from its commit log via CDC — the log provides ordering and a dedup-able position, so the new store converges like a replica. Only after verified convergence do you flip the direction of authority, and the flip is a fencing/promotion problem, not a code change.

**Q: Your migration plan says "drop the old column after two weeks." What must be verified before that runs, and why is two weeks the wrong kind of justification?**
A: Verified: no *deployed* code path reads or writes it (including batch jobs, scripts, replicas' logical consumers, and anything pinned to old versions — mobile clients if it is an API field), no indexes/constraints depend on it, and a dual-read or audit check confirms no references in a monitoring window. The calendar ("two weeks") is the wrong justification because deploys are gated by *facts* (is anything still using it?) not time — a pinned old client or a forgotten cron extends the window indefinitely, which is why usage verification, not patience, gates contract.

## Key Takeaways

- Zero downtime means every intermediate state is correct for both old and new code, in both directions — expand–contract is that invariant turned into a procedure.
- The phase boundaries are gated by deploys, not ALTERs: schema expands first, code rolls through compatibility, contract waits until nothing references the old shape.
- Backfills are bulk transfers: batched by key range, throttled against replication lag, checkpointed, and idempotent — one big transaction is the anti-pattern that fails at exactly the wrong moment.
- Dual-write forks the truth; CDC from the old store's commit log reorders the problem so the new structure converges as a replica, with verification before authority flips.
- Rollback is designed before cutover: deploys roll back cheaply because expand guaranteed compatibility; contract is scheduled last because data rollback after it is archaeology.
- "Zero downtime" is an ordering property, not a tool property — tools (gh-ost, logical replication, repack) implement phases that the ordering makes safe.

## Cross-References

- [ACID Transactions](./acid-transactions.md) — the sibling chain owning the WAL and commit machinery the backfill and CDC rungs ride on.
- [Replication Lag](./replication-lag.md) — the lag measurement and promotion script the backfill throttle and cutover borrow.
- [Database Indexes](./database-indexes.md) — the write-amplification and rebuild costs behind DDL blocking behavior.
- [Event Sourcing and WAL](../connection-atlas/event-sourcing-wal.md) — the coupling map: the log as the spine that makes change-data-capture migrations correct.
- [Serialization Compatibility](../assumptions-hunt/serialization-compatibility.md) — the schema-as-protocol audit: the compatibility rules code versions obey during the transition.
- [Schema Migrations](../../dbms/advanced/schema-migrations.md) — the book chapter on DDL semantics, online schema change tooling, and vendor behavior.
- [Canary Releases](../../sre/canary-releases.md) — the traffic-shift and observation discipline the cutover reuses.
- [Feature Flags](../../sre/feature-flags.md) — the control plane that makes cutover and rollback configuration changes.
- [PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html) — the production CDC instance cited in the cutover rung.
