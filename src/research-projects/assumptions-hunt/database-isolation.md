# Database Isolation Assumptions: What "Transactional" Actually Promises

## Overview

"Wrap it in a transaction" is the most trusted sentence in application development, and the most misunderstood. Isolation levels are contracts written in the vocabulary of anomalies — dirty reads, nonrepeatable reads, phantoms — and each level's fine print differs by engine, sometimes in ways that are documented in both vendors' manuals and still surprise engineers who assumed the SQL standard produced identical behavior everywhere. Add an ORM that translates application code into read-modify-write sequences, and the gap between "it's a transaction" and "the invariant survived" becomes a production incident category of its own.

Every quote about MySQL and PostgreSQL behavior in this chapter was verified against the current official manuals: the PostgreSQL transaction isolation documentation and the MySQL InnoDB isolation and consistent-read documentation. Both are linked below.

## Assumption 1: "Transactions Are Isolated"

### The taught rule

A transaction's operations appear to run alone; the database ensures concurrent transactions do not interfere.

### The hidden assumptions

- "Isolated" means *some level* of isolation — and every level below SERIALIZABLE permits, by contract, executions that are not equivalent to any serial order. The SQL standard's own hierarchy (READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE) is a menu of allowed anomalies, not a single guarantee.
- The default level is whichever your engine chose, and the engines disagree: PostgreSQL's manual states "Read Committed is the default isolation level in PostgreSQL", while MySQL's manual documents REPEATABLE READ as the InnoDB default. SQL Server and Oracle default to READ COMMITTED as well. Code ported between engines silently changes isolation semantics.
- At READ COMMITTED, each statement sees a fresh snapshot, so even a single transaction can observe the database change underneath it between statements.

### Counterexample

Two sessions at READ COMMITTED both read `account.balance = 100`. Each computes `balance - 80` in the application and writes it back in its own transaction. Both transactions commit successfully; the account's 100 became 20 twice — one withdrawal vanished. No anomaly from the standard's "forbidden at READ COMMITTED" list (no dirty read, no nonrepeatable read of a *changed* value, no phantom) was violated: a lost update is simply permitted at this level. The guarantee was real; the assumption that the guarantee covered lost updates was not.

### What changes when the assumption is removed

Corrected statement: *a transaction at level L prevents exactly the anomalies excluded at L — and nothing more. Name the level, know its allowed anomalies, and design the write pattern (atomic updates, locking reads, optimistic versions) for the ones it permits.*

### Consequences

"Which anomalies does READ COMMITTED allow?" is the baseline interview question; the follow-up "and is that your engine's default?" is where most candidates — and most codebases — get exposed.

## Assumption 2: "SELECT Never Blocks"

### The taught rule

MVCC databases let readers and writers proceed concurrently: a plain SELECT never waits for a writer.

### The hidden assumptions

- The rule covers *plain* reads of row data under MVCC. `SELECT ... FOR UPDATE/FOR SHARE` takes locks and blocks — as intended.
- Reads can still be *aborted*, not blocked: under PostgreSQL's SERIALIZABLE (implemented as Serializable Snapshot Isolation), a read-only transaction can fail at commit with a serialization error because its reads participated in a dangerous cycle. Waiting was replaced by aborting.
- Reads block on DDL and on tuple/row locks in specific engines and modes (advisory locks, `LOCK TABLE`), and long-running reads hold snapshots that force vacuum/cleanup work to accumulate — "no blocking" is not "no cost".

### Counterexample

Under PostgreSQL SERIALIZABLE, transaction A does `SELECT SUM(amount) FROM orders` and, based on the result, `INSERT` a rebate. It commits fine. Concurrent transaction B inserts an order and commits between A's statements. A is aborted at commit with a serialization failure — its read was *not* silently inconsistent, but it also did not "never block and always succeed": the corrected mental model is that SERIALIZABLE trades blocking for abort-and-retry.

### What changes when the assumption is removed

Corrected statement: *plain MVCC reads neither block writers nor wait on their locks, but locking reads block, serializable reads can abort, and long reads tax cleanup; "SELECT never blocks" is true for exactly the narrow case it describes.*

### Consequences

Retry logic is not optional under SERIALIZABLE — code that assumes every successful parse implies a successful commit is the classic integration bug when teams tighten isolation.

## Assumption 3: "Transaction Order Equals Commit Order (Equals What Others Saw)"

### The taught rule

Transactions are ordered; if T1 finishes before T2 starts in real time, T2 saw T1's effects.

### The hidden assumptions

- At READ COMMITTED there is no single order: each statement takes a new snapshot, so a transaction can see T1's commit in its first statement and not in its second (or vice versa depending on timing).
- Overlapping transactions can commit in either order; commit timestamps order commits, not logical execution, and at weak levels two sessions' "what I saw" histories may not embed into any single serial order.
- The engine's lock acquisition order is not a global transaction order either — two transactions can hold locks that serialize different pairs in different orders (the lock-graph structure behind [deadlock detection](../../concurrency/deadlock-detection.md)).

### Counterexample

Session A at READ COMMITTED runs `SELECT count(*) FROM orders` and sees 100. Session B inserts order 101 and commits. Session A runs the same count again and sees 101. Session C, which started *after* A but connected before B's commit, might see 101 then 100 — impossible in any serial execution, and entirely permitted at READ COMMITTED. Only REPEATABLE READ and above pin a single snapshot per transaction.

### What changes when the assumption is removed

Corrected statement: *only snapshot-preserving levels (REPEATABLE READ and up) give one consistent view per transaction; at READ COMMITTED the unit of consistency is the statement. If your invariant spans statements, the level must match the invariant — or you must re-read under lock.*

### Consequences

Report-generation and multi-step read-then-decide logic are the usual victims; the interview probe is "when does READ COMMITTED break a multi-step read?"

## Assumption 4: "REPEATABLE READ Means the Same Thing in MySQL and PostgreSQL"

### The taught rule

REPEATABLE READ: reads in a transaction are repeatable — the same query returns the same rows. It is standardized, so it is portable.

### The hidden assumptions

The standard's words leave the *write* path underspecified, and the two engines' documented behaviors diverge on exactly that path:

- **PostgreSQL** implements REPEATABLE READ with a transaction-wide snapshot and protects it on the write side: if your UPDATE targets a row modified by a transaction that committed after your snapshot began, the manual documents the outcome as an error — the transaction "will be rolled back with the message `ERROR: could not serialize access due to concurrent update`". Silent overwrite is impossible; you must retry.
- **MySQL (InnoDB)** documents a different contract: "The snapshot of the database state applies to SELECT statements within a transaction, not necessarily to DML statements," and explains that "a DELETE or UPDATE statement issued from another concurrent REPEATABLE READ transaction could affect those just-committed rows, even though the session could not query them." InnoDB's writes are *current reads* — they act on the latest committed versions, not the snapshot.

Same level name, opposite failure signatures: PostgreSQL fails loudly and preserves your snapshot's integrity; MySQL proceeds and can mutate data your own SELECTs could not see.

### Counterexample

An REPEATABLE READ transaction in each engine, snapshot taken, another session then inserts a row matching your `WHERE status = 'pending'` predicate and commits. In MySQL, your `UPDATE orders SET status = 'done' WHERE status = 'pending'` executes as a current read and *updates that new row* — one your transaction never read and could not SELECT in its snapshot. In PostgreSQL, the same transaction simply does not touch the invisible row (and would error if it tried to modify a *visible* row that changed concurrently). A state machine ported from one engine to the other changes observable behavior with no code change.

### What changes when the assumption is removed

Corrected statement: *isolation levels are engine dialects. Portable code must (a) set the level explicitly rather than inherit the default, (b) re-verify write-path behavior — locking reads, `SELECT ... FOR UPDATE`, gap/next-key locking semantics — per engine, and (c) treat "REPEATABLE READ" as a family of contracts sharing a name.* The repo's isolation-levels chapter and the transactions-concurrency-control atlas page map these dialects in detail.

### Consequences

This is the strongest interview differentiator in database isolation: quoting the divergence from the two manuals demonstrates source-level literacy, and the MySQL current-read anomaly (write affecting rows you cannot read) is a favorite senior-level trap.

## Assumption 5: "Once Phantom Reads Are Gone, We Are Safe"

### The taught rule

REPEATABLE READ prevents nonrepeatable reads and phantoms; the remaining risks are exotic.

### The hidden assumptions

- Phantom prevention at REPEATABLE READ still permits *write skew*: two transactions read overlapping data, each makes a decision based on it, both write to *disjoint* rows, and the invariant linking them breaks. Snapshot isolation's known anomaly, present in both engines' RR.
- PostgreSQL only detects it at SERIALIZABLE (via SSI); InnoDB's REPEATABLE READ has no such detection (its gap/next-key locking protects locking statements from phantoms, but does not perform serialization-cycle detection).
- Constraint enforcement outside unique/FK constraints is application logic — the engine does not know your invariant.

### Counterexample (write skew)

Doctors on-call: the invariant is "at least one doctor is on call". At REPEATABLE READ in either engine, both transactions read: "Alice and Bob are on call". T1 sets Alice off-call; T2 sets Bob off-call; both commit. Each transaction is consistent with its snapshot; the invariant "at least one on call" is now false. PostgreSQL SERIALIZABLE would abort one of them (SSI detects the read-write cycle); the RR levels of both engines will not.

### What changes when the assumption is removed

Corrected statement: *invariants that span rows and decisions need either SERIALIZABLE with retry, explicit locking (`SELECT ... FOR UPDATE` over the invariant's rows), or database-enforced constraints (unique, exclusion, check-with-trigger) — REPEATABLE READ's phantom prevention does not cover multi-row decision logic.*

### Consequences

The on-call doctors example is the standard interview scenario for snapshot isolation anomalies; the strong answer names write skew *and* the engine-specific detection difference.

## Assumption 6: "My ORM Handles Races"

### The taught rule

The ORM wraps operations in transactions; concurrency is handled.

### The hidden assumptions

- An ORM transaction at the default level wraps statements in *time*; it does not make a read-modify-write *sequence* atomic. `account = repo.find(id); account.balance -= 80; repo.save(account)` is still two sessions reading the same 100.
- Generated `UPDATE`s often write *all* columns (the full entity), so the lost update can clobber fields the user never edited — a wider blast radius than the naive code suggests.
- The ORM's identity map hides the read from you; the race window is between its SELECT and its UPDATE, invisible in application code.

### Counterexample and fixes

The Assumption 1 lost update, now with an ORM: two requests load the same entity, both save, last write wins. The standard defenses, in increasing invasiveness: atomic in-database update (`UPDATE account SET balance = balance - 80 WHERE id = :id AND balance >= 80` and check affected rows — the *database* does the arithmetic); pessimistic `SELECT ... FOR UPDATE` around the read-modify-write; optimistic concurrency with a version column (`UPDATE ... SET ..., version = version + 1 WHERE id = :id AND version = :seenVersion` — zero affected rows means someone raced you). All three are ORM-agnostic; none can be inferred from "we use transactions".

### What changes when the assumption is removed

Corrected statement: *an ORM is a statement generator, not a concurrency controller; concurrency correctness comes from the isolation level plus the shape of the generated statements — atomic updates, locking reads, or version checks chosen deliberately per invariant.*

### Consequences

"Your service lost an update under load — walk through the generated SQL" is the interview question; the candidates who can produce the two generated statements and the interleaving are the ones who have actually debugged this.

## Interview Questions

1. **Is a lost update possible at READ COMMITTED? At REPEATABLE READ?** Yes at READ COMMITTED in both PostgreSQL and MySQL — the level permits it. At REPEATABLE READ: PostgreSQL errors on the conflicting update ("could not serialize access due to concurrent update"); MySQL's DML performs current reads, so an application read-modify-write can still lose updates unless the write is atomic or the row is locked.
2. **Give one documented behavioral difference between MySQL and PostgreSQL at REPEATABLE READ.** PostgreSQL rolls back an UPDATE that touches a row modified after the snapshot began; MySQL's snapshot covers SELECTs but "not necessarily" DML — an UPDATE/DELETE from a concurrent RR transaction can affect rows your transaction could not query (MySQL manual, consistent-read section).
3. **Both doctors set themselves off-call and the invariant breaks — which level fixes it and why?** Snapshot isolation's write skew; both engines' REPEATABLE READ permit it. PostgreSQL SERIALIZABLE (SSI) detects the read-write cycle and aborts one transaction; otherwise use `SELECT ... FOR UPDATE` on the on-call set or an enforceable constraint.
4. **Why does "SELECT never blocks" not mean "reads are free"?** Plain MVCC reads skip row-lock waiting, but locking reads block, serializable reads can be aborted at commit, and long-running reads hold snapshots that delay cleanup (bloat/vacuum pressure). Different cost, same engine.
5. **List three ORM-level fixes for lost updates and when each fits.** Atomic in-database arithmetic (single-counter/value invariants — simplest and lock-free), `SELECT ... FOR UPDATE` (multi-field invariants needing consistent reads plus writes), and optimistic version checks (low-contention entities where retries are cheaper than locking).

## Key Takeaways

- Isolation levels are menus of permitted anomalies; the default differs by engine (PostgreSQL READ COMMITTED, MySQL InnoDB REPEATABLE READ), so portable code sets levels explicitly.
- At READ COMMITTED the unit of consistency is the statement; multi-step read-then-decide logic needs a snapshot-preserving level or locking.
- REPEATABLE READ is an engine dialect: PostgreSQL protects the snapshot on the write path with serialization errors; MySQL's DML reads current data and can affect rows the transaction never saw — both behaviors are quoted from the vendors' own manuals.
- Write skew survives phantom prevention; only SERIALIZABLE-class detection, explicit locks, or real constraints cover multi-row invariants.
- ORMs generate statements, not guarantees; lost updates are fixed by atomic updates, locking reads, or version columns — chosen per invariant, verified in the generated SQL.

## Cross-References

- [Isolation levels](../../dbms/transactions/isolation-levels.md) — the repo's systematic treatment of the SQL levels.
- [MVCC](../../dbms/transactions/mvcc.md) and [concurrency control](../../dbms/transactions/concurrency-control.md) — the mechanisms that implement the contracts above.
- [PostgreSQL manual: transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) — primary source for default level and RR error behavior (verified).
- [MySQL manual: InnoDB isolation levels](https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html) — primary source for InnoDB defaults and locking (verified).
- [MySQL manual: consistent nonlocking reads](https://dev.mysql.com/doc/refman/8.0/en/innodb-consistent-read.html) — primary source for the SELECT-vs-DML snapshot quote (verified).
- [Transactions and concurrency-control atlas](../connection-atlas/transactions-concurrency-control.md) — how these contracts connect to two-phase locking and MVCC internals.
- [Jepsen testing](../../distributed/testing/jepsen.md) — empirical verification of vendor claims about isolation.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — sibling chapter: the check-then-act pattern, which the ORM section is a database instance of.
- [Caching](caching.md) — sibling chapter: stale data and versioned writes, the cache-layer twin of read-repair.
