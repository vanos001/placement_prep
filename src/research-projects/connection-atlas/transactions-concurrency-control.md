# Transactions and Concurrency Control: Ordering Contracts Across Two Worlds

## Overview

A database lock manager and a thread holding a mutex are doing the same job: denying some interleavings of reads and writes so that the surviving executions have comprehensible semantics. Two-phase locking (2PL) and read-write locks are the same pessimistic scheme at different scales; a DB monitor waiting on a row lock and a Java thread waiting on an object monitor differ mainly in how long they wait; MVCC is "give readers immutable snapshots" implemented with version chains, the same idea thread libraries implement with copy-on-write and RCU. The mapping is so strong that vocabulary transfers cleanly — shared/exclusive, waiters, deadlock — and so incomplete that applying DB guarantees vocabulary to threaded code (or vice versa) produces real design errors: transactions span *many* objects and *commit*, mutexes guard *one* invariant region and release; that difference is where 2PC and distributed deadlocks enter.

## The Concepts, Independently

**Database concurrency control.** 2PL splits every transaction's life into a growing phase (acquire S/X locks, never release early) and a shrinking phase (release, never acquire again); strict 2PL — holding all locks until commit — guarantees conflict-serializability plus no cascading aborts. The lock manager keeps a lock table: per-object queues of granted and waiting holders. MVCC takes the other road: writers append new versions (Postgres marks rows with `xmin`/`xmax`; readers filter by their snapshot), so **readers never block writers and writers never block readers**; snapshot isolation (SI) gives each transaction a consistent snapshot and uses first-committer-wins to stop write-write conflicts (write skew remains possible — two transactions each read the other's untouched row and write disjoint rows, breaking a joint invariant). Isolation levels (read committed, repeatable read, serializable) are the menu of contracts; serializability is the strictest: the result equals *some* serial order of the transactions.

**Thread-level concurrency control.** A mutex provides mutual exclusion; a monitor couples it with condition variables for waiting. A read-write lock (see [../../concurrency/readers-writers.md](../../concurrency/readers-writers.md)) generalizes it: shared mode for concurrent readers, exclusive for writers — semantically the DB's S/X pair. Deadlock prevention at thread level is usually **lock ordering** (acquire locks in a global total order) because cycles in the wait-for graph are the failure; detection via resource-allocation graphs exists in OS courses but is rarely shipped in user threads. Memory consistency models are the hardware's cousin: sequential consistency (Lamport) says all threads see *some* interleaving respecting program order; real CPUs (TSO/x86, weaker ARM) and language memory models (C++/Java) relax those guarantees and require fences/volatiles to restore them.

## The Shared Principle

**Concurrency control is a chosen ordering contract plus a mechanism that enforces it: block pessimistically (2PL, RW locks, mutexes), validate optimistically (OCC, optimistic DB concurrency, seqlocks), or multiversion (MVCC, RCU, copy-on-write).** Both worlds interleave read/write *sets* over shared state, both define correctness by "some equivalent non-interleaved execution," and both fail the same way when the mechanism is blocking: cycles in the wait-for graph. The mapping in one line: **serializability is to transactions what (strict) linearizability is to operations** — both say "equivalent to a legal sequential history," and the differences below are about scope and real time, not spirit.

## Where the Analogy HOLDS and BREAKS

| Mechanism pair | HOLDS (mechanism is shared) | BREAKS (mechanism genuinely differs) |
|---|---|---|
| 2PL ↔ read-write locks | Identical S/X semantics, identical deadlock cycles in the wait-for graph | DB locks are held **until commit** (ms–s) and are inherently many-object; thread locks are held for ns–µs inside one critical section — so DB waits block on queues with deadlock *detection*, threads avoid via *ordering* and spin briefly |
| Mutex/monitor ↔ table/row lock with waiter queue | Same shape: one exclusive holder, FIFO-ish waiters, wake-on-release | Monitors have condition variables (wait/notify on a predicate); SQL lock waits have timeouts, deadlock victims, and priority by isolation level — the "wait policy" surface differs completely |
| MVCC ↔ RCU/COW snapshots | Readers never block writers in both; both pay with version garbage collection | MVCC guarantees a *transaction-wide consistent snapshot across objects*; RCU gives per-object pointer stability and no cross-object snapshot — pretending otherwise causes read-skew bugs in "RCU-as-MVCC" designs |
| Serializability ↔ linearizability | Both are "equivalent to a sequential execution" contracts | Linearizability is per-operation with real-time respect; serializability is per-transaction with **no** real-time requirement — serializable transactions can be reordered across real time (that stricter compound is *strict serializability*, e.g., Spanner's external consistency) |
| Isolation levels ↔ memory consistency models | Both are ladders from "anything goes" to "looks sequential" | The mapping is *interpretive, not formal*: read-uncommitted ≈ hardware reordering visible, serializable ≈ sequentially consistent — but memory models govern single-access ordering, while isolation levels govern **multi-object atomic composition**, which hardware models cannot even express |

The last row is the subtlest and most interview-valuable: a CPU that is sequentially consistent still lets your non-transactional code update one account and not the other (crash between writes); a serializable database makes the pair atomic. Consistency models answer "in what order may operations appear"; transactions answer "which groups of operations count as one." Neither subsumes the other.

## A Concrete Worked Example

**The same deadlock in both worlds.** Transfer $100 from A to B. Thread version: T1 does `lock(A); lock(B); A -= 100; B += 100; unlock…` while T2 does `lock(B); lock(A); …`. T1 holds A, wants B; T2 holds B, wants A — a two-cycle in the wait-for graph; with no order discipline they hang. Database version: T1 `UPDATE accounts SET bal = bal - 100 WHERE id='A';` then `… id='B'`; T2 updates B then A — the lock manager's wait-for graph has the identical cycle. The enforcement differs by duration economics: Postgres's deadlock detector wakes on `deadlock_timeout` (default 1 s) — cheap because DB locks are held for seconds, so 1 s of detection latency is noise — picks a victim, aborts it with a serialization error, and the app retries. The thread version instead imposes **lock ordering** (always acquire A before B) because user-space locks are held for microseconds: a 1 s detection cycle would dwarf the critical section. Same graph theory, opposite engineering answer — chosen by how long locks are held.

**Write skew under snapshot isolation, with numbers.** Doctors rule: at least 1 of {Alice, Bob} must be on call. Both transactions read `on_call = {Alice, Bob}` (2 people), each removes only themselves, both commit under SI: each saw a snapshot where the invariant held and they wrote disjoint rows (Alice's row, Bob's row), so first-committer-wins never fires. Result: `on_call = {}` — invariant broken although each transaction was internally consistent. Serializable (2PL or serializable-SI, e.g., Postgres's SSI) detects the rw-antidependency and aborts one. The lesson for application design: under SI, any invariant spanning *multiple* rows needs either serializable isolation or explicit conflict materialization (force both transactions to write a common row).

## When This Connection Is Useful

- **Problem-solving heuristics.** Concurrency bugs in threaded code and transaction anomalies have the same taxonomy: lost update (two read-modify-writes interleave), dirty read (seeing uncommitted/unreleased state), write skew (each preserves its own read set, joint invariant dies), deadlock (cycle). Name the anomaly first, then pick the enforcement family — pessimistic when contention is high and critical sections short, optimistic (validate/retry) when contention is low, multiversion when readers dominate and snapshot semantics suffice.
- **Interview answers.** "Serializability vs linearizability" is a standing senior-level question: answer with scope (transactions vs operations) and real-time (only linearizability respects it), then note strict serializability = both, citing Spanner. "Why doesn't MVCC need read locks?" — versions give readers a stable snapshot; old versions are GC'd once no snapshot needs them. "Is a DB row lock just a mutex?" — semantics yes, but commit-duration, many-object scope, and deadlock-by-detection change every design constant.
- **Engineering decisions.** Choose the isolation level per use case, not by fear: read committed for most web workloads, SI (+ retry on 40001) for consistent multi-row reads, serializable only where cross-row invariants are money-shaped. In threaded code, replace "add a lock" thinking with "name the invariant, choose the enforcement family." In distributed transactions, expect 2PC on top of local strictness (see [../../dbms/transactions/two-phase-commit.md](../../dbms/transactions/two-phase-commit.md)) and expect deadlock detection to become approximate (phantom deadlocks from stale wait-for edges across nodes).

## Interview Questions

1. Show that strict 2PL's lock-until-commit rule prevents both cascading aborts and non-serializable schedules, and explain what the growing/shrinking phases have to do with cycles in the serialization graph.
2. Two threads deadlock on two mutexes; two transactions deadlock on two row locks. Why does the standard fix differ (lock ordering vs detection-and-abort), and what property of DB transactions makes 1-second deadlock detection acceptable?
3. Define write skew, construct it with a two-row invariant and concrete numbers, and give two application-level fixes that do not require raising the isolation level.
4. A colleague claims "MVCC is just RCU." Refute precisely: what guarantee does MVCC give that RCU does not, and where does each collect its version garbage?
5. Map each isolation level to its nearest memory-consistency-model analogue, then give one concrete scenario where sequential consistency at the hardware level still permits a database-style lost update.

## Key Takeaways

- Pessimistic (locks), optimistic (validation), and multiversion (snapshots) are the three enforcement families; DBs and thread libraries both offer all three, tuned for their lock-holding durations.
- 2PL ↔ RW locks and mutex ↔ table lock are genuine mechanism matches; the engineering divergence (ordering vs detection) comes from hold time, not theory.
- MVCC = snapshot isolation via versioning: readers never block writers, paid for with version GC; it prevents dirty/non-repeatable reads but allows write skew.
- Serializability is per-transaction without real-time; linearizability is per-operation with real-time; strict serializability unifies them — do not say they are "the same thing."
- Isolation levels and memory consistency models are ladders with different rungs: memory models order accesses; transactions compose objects atomically. Transactions spanning many nodes add 2PC and *approximate* deadlock detection — the point where the thread analogy finally runs out.

## Cross-References

- [../../dbms/transactions/lock-based.md](../../dbms/transactions/lock-based.md) — Lock-Based Concurrency Control — 2PL variants and the lock manager in depth.
- [../../dbms/transactions/mvcc.md](../../dbms/transactions/mvcc.md) — MVCC — version chains, xmin/xmax, vacuum.
- [../../dbms/transactions/serializability.md](../../dbms/transactions/serializability.md) — Serializability — conflict graphs and SSI.
- [../../dbms/transactions/isolation-levels.md](../../dbms/transactions/isolation-levels.md) — Isolation Levels — the full ladder and its anomalies.
- [../../dbms/transactions/two-phase-commit.md](../../dbms/transactions/two-phase-commit.md) — Two-Phase Commit — atomic commit when the transaction spans nodes.
- [../../concurrency/readers-writers.md](../../concurrency/readers-writers.md) — Readers-Writers Problem — the thread-side S/X mechanism.
- [../../concurrency/memory-model.md](../../concurrency/memory-model.md) — Memory Models — the hardware/language ordering ladder.
- [../../concurrency/deadlock-detection.md](../../concurrency/deadlock-detection.md) — Deadlock Detection — wait-for-graph cycles on both sides of the analogy.
- [../../distributed/fundamentals/consistency.md](../../distributed/fundamentals/consistency.md) — Consistency Models — linearizability and friends in the distributed setting.
- [./gc-memory-management.md](./gc-memory-management.md) — GC and Memory Management — who collects MVCC's dead versions, and the lease connection.
