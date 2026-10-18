# Optimistic vs Pessimistic Locking: Does Contention Pay for Coordination Up Front?

## Overview

"Optimistic or pessimistic locking?" is usually answered by vibes — "optimistic is modern" — as if the choice were a fashion cycle rather than an economics problem. The sharper question is: **when two transactions want the same row, when is the cost of coordination paid, and by whom?** The pessimistic contract takes the lock before doing the work: everyone else queues, waits, and pays in latency, but no one does doomed work. The optimistic contract does the work on a snapshot and checks at commit: nobody waits, but every conflict invalidates someone's completed work, and the loser pays in retries — often re-running business logic, not just re-executing a write. This page stays at the database level — rows, version columns, and isolation modes — rather than in-process mutexes and condition variables, which the [in-process sibling](./concurrency-primitives.md) owns.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **pessimistic locking converts contention into waiting for everyone and guarantees work is never wasted; optimistic locking converts contention into retries for the losers and guarantees no one ever waits — the crossover is set by the conflict probability, the cost of the work between read and write, and whether the work between them can even be safely re-run.** A modern wrinkle changes the default: MVCC makes the read side of optimistic concurrency nearly free (readers never block writers), and engine-managed serializable modes (Postgres SSI) detect conflicts the application never wrote checks for — repositioning "optimistic" from a hand-rolled pattern into something the engine can do.

## Step 1: The Problem and Its Constraints

The abstract shape: multiple transactions read a row (or a set of rows), compute, and write. Without coordination, last-writer-wins loses updates; with coordination, either waiting or retrying appears. Constraints that decide which cost profile fits:

- **Contention rate.** What fraction of transactions touch a row another transaction is actively touching? Inventory with 5 units, account balances, seat maps: high contention by construction. Most user-profile rows: near zero.
- **Cost of the work between read and write.** Is the middle of the transaction cheap computation, or minutes of user thinking time, a payment call, an email? Pessimistic locks held across human or network timescales are a different (and worse) system than locks held for microseconds.
- **Re-runnability.** If a conflict invalidates the work, can the transaction simply run again? Re-runnable compute yes; re-runnable payment capture or email sending demands idempotency machinery first.
- **Latency shape required.** Pessimistic queues cost on the contended row and keeps everyone else fast; optimistic keeps everyone fast until commit and concentrates cost on losers. Tail-latency requirements decide which concentration is acceptable.
- **Anomaly class.** Single-row lost updates (both mechanisms solve) or cross-row skew — write skew, phantoms — where neither flavor's row-level mechanics are automatically sufficient (see the isolation [assumptions](../assumptions-hunt/database-isolation.md)).
- **Scope of access.** One row, a range, a table? Granularity is where pessimistic designs grow complicated (gap locks, escalation) and optimistic checks grow subtle (phantoms).

## Step 2: The Mechanisms

### Pessimistic: lock before use

The transaction tells the database its intent up front: `SELECT ... FOR UPDATE` takes an exclusive [row lock](../../dbms/transactions/lock-based.md); the [lock manager](../../dbms/transactions/concurrency-control.md) queues other transactions' requests and blocks them. The mechanisms that matter:

- **Blocking is the coordination.** A second transaction touching the locked row waits — on a lock wait queue, holding a database connection — until the holder commits or rolls back. The waiting is bounded by `innodb_lock_wait_timeout` or its equivalents; unbounded waits are a configuration choice, not a mechanism property.
- **The hold time is the throughput ceiling.** A row locked for the duration of the transaction serializes all writers to it: max throughput on that row ≈ 1/hold-time. Everything that lengthens the transaction (application logic inside the transaction, HTTP calls — see the edge cases) directly divides the ceiling.
- **Deadlocks are possible and detected.** Two transactions taking the same rows in opposite orders wait on each other; the detector picks a victim and aborts it — and, the part teams forget, the victim still needs retry logic. Pessimistic locking reduces retries; it does not remove the path.
- **Locks pin resources across the transaction's length.** The lock is held until commit/rollback regardless of what the transaction does in between — including talking to Stripe, sleeping, or pausing in a debugger.

### Optimistic: check at commit

The transaction reads data with a version marker (a version column, an updated-at, or the engine's snapshot), does its work, and commits with a conditional write: `UPDATE ... WHERE id = ? AND version = ?`. Zero rows affected means someone changed the row in between — conflict detected, work discarded, transaction retried. The mechanisms that matter:

- **[MVCC](../../dbms/transactions/mvcc.md) makes the read side free.** Readers see a snapshot; writers create new versions; nobody blocks. The "lock" is virtual: the conflict check is a predicate on the write. This is why optimistic locking scales read-heavy workloads without tuning — there is nothing to tune.
- **The retry loop is the coordination.** Conflict cost = all work since the read. A retry re-executes the transaction; a retry storm (N writers, one row, all retrying on the same tick) is the optimistic twin of the pessimistic wait queue, and it needs backoff and jitter to avoid synchronizing.
- **Engine-managed optimistic mode exists.** Serializable snapshot isolation in Postgres tracks read-write dependencies and aborts transactions whose serialization assumption broke — the [engine detects](../../dbms/advanced/serializable-snapshot-isolation.md) what the hand-rolled version check cannot (cross-row skew). The application's job becomes "retry on serialization failure," not "write correct checks everywhere."
- **Phantoms and predicate drift are the subtle failures.** Version-checking the rows you read does not notice a *new* matching row appearing — the classic reason hand-rolled optimistic checks under-report conflicts versus what serializable semantics require.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Pessimistic (row locks) | Optimistic (version columns / SSI) |
|----------|--------------------------|-------------------------------------|
| Coordination moment | Before the work (lock acquired) | At commit (conflict detected) |
| Cost under low contention | Lock overhead on every access; negligible | Nearly zero — reads are snapshot reads |
| Cost under high contention | Everyone queues on the row; throughput = 1/hold-time | Losers repeat work; retry storms without backoff |
| Wasted work | None — lock holders complete | All work since the read, per conflict |
| Deadlocks | Possible; detector aborts a victim | Impossible by construction (no waits) |
| Blocking other transactions | Yes, including readers in some engines' modes | Readers never blocked (MVCC); writers never blocked |
| Fairness | FIFO-ish at the lock queue | Winner by commit race; starvation possible without backoff policy |
| Interaction with long transactions | Catastrophic — locks held for the duration | Fine — snapshot is stable across the transaction |
| External side effects mid-transaction | Dangerous — side effect done, then rollback; lock held meanwhile | Dangerous differently — side effect done, then retry repeats it |
| Anomaly coverage | Depends on isolation level + lock scope (gaps for phantoms) | Depends on check completeness; SSI covers what hand checks miss |
| Retry discipline needed | Still yes (deadlock victims, timeouts) | Yes, on every conflicting write |
| Hot-row ceiling | Hard serial ceiling | Bounded by commit throughput, not hold time |

The **cost-location flip** deserves the arrow drawn. Both mechanisms enforce the same contract — no two transactions both "win" the row — and differ in when the bill arrives. Pessimistic bills *everyone who touches the contended resource*, including the transactions that would never have conflicted at commit, and bills them in wait time; it buys certainty that no work is wasted. Optimistic bills *only the losers*, in discarded work and retries; it buys zero waiting at the price of re-runnable work and idempotent side effects. The crossover arithmetic: at conflict probability p, work cost c, and lock wait w, pessimistic pays ~w per transaction and optimistic pays ~p·c — read-mostly workloads (p → 0) are optimistic territory; hot rows (w grows with queue depth) are pessimistic territory.

## Step 4: When Each Wins

| Condition | Choice | Why |
|-----------|--------|-----|
| Known hot row with real contention (inventory, balances, seat maps) | Pessimistic | Waiting is cheaper than repeated wasted work; ceiling is predictable |
| Work between read and write is long or human-paced | Optimistic (or restructure) | Holding locks that long stalls the row and the connection pool |
| Mostly-read data, rare conflicts | Optimistic | Conflict cost ~p·c ≈ 0; no lock overhead at all |
| Work includes non-re-runnable side effects (payment capture) | Pessimistic (with care) | Retry must not re-run the side effect; serialize that segment explicitly |
| Engine-managed serializability available and wanted | Optimistic (SSI) | The engine detects cross-row anomalies hand checks miss |
| Deadlock-free requirement without retry paths | Neither honestly | Pessimistic needs deadlock-victim retries; optimistic needs conflict retries |

**Pessimistic wins** where contention is structural and work is short: the last units of stock, an account balance — anywhere the row queue stays short and certainty that work is not wasted is worth the wait. **Optimistic wins** wherever conflict probability is low or the lock would be held too long: user profiles, document edits with version columns, anything crossing an HTTP or human boundary, and default paths where MVCC makes snapshots free. **The honest hybrid** is how real systems ship: version columns as the default, targeted `FOR UPDATE` on the few known hot rows, and engine-level serializable mode where write skew matters more than throughput — selected per access path, not per application.

## Step 5: Edge Cases and Counterexamples

- **The lock held across an HTTP call.** `SELECT FOR UPDATE` on the order row, then call the payment provider (300 ms p50, 8 s p99), then commit. Every other transaction touching that order queues — each holding a connection. At modest concurrency the pool exhausts and *unrelated* requests stall: the pessimistic failure is not "the row felt slow," it is "the whole service stopped." Locks are for microseconds; anything network-shaped belongs outside the transaction — which usually means optimistic for everything around it.
- **The 100-writer commit stampede.** A promotion drives 100 concurrent writers at one hot row. All read version 7, all attempt the write, 1 wins, 99 retry — on the same tick, without backoff, re-running logic that may already have sent a notification. Optimistic locking does not fail by being wrong here; it fails by being *racy* at commit. Exponential backoff with jitter, retry budgets, and idempotent side effects are not optional companions — they are the mechanism's second half.
- **The deadlock victim that had no retry path.** Transaction A locks row 1 then wants row 2; transaction B locks row 2 then wants row 1. The detector kills B; the batch job treats the error as fatal and dies. Pessimistic locking still requires retry code — deadlock victims, lock-wait timeouts — so "we chose pessimistic to avoid retries" was never true; it only reduced their frequency.
- **Write skew: the anomaly both row-level flavors miss by default.** Two on-call doctors each check "at least one doctor is on call," each stays, and both go off-call — each transaction's checks passed; the *pair* violated the invariant. Row locks on touched rows do not help: neither transaction read the other's guard. Serializable snapshot isolation detects it; hand-rolled version checks do not. The optimistic/pessimistic choice on *rows* is downstream of the isolation question, not a substitute for it.
- **The hot-row counter that sharding could not fix — but batching could.** A global statistics row serializes at one lock-holder at a time; neither mechanism changes the 1/hold-time ceiling. The unlock is the *mechanism contract*: batch updates applied every 100 ms, shard the counter into N rows summed on read, or move it off the transactional path. Some contention problems are locking problems; others are "you are transactionally serializing something that does not need to be."

## Step 6: Decision Framework

1. **What is the realistic conflict probability on this access path?** Near zero → optimistic (version column or snapshot); cost ≈ p·c. Structural and hot → pessimistic on that row.
2. **How long is the work between read and write?** Microseconds in-database → either works; choose by contention. Anything crossing a network or human boundary → optimistic, and shrink the transaction.
3. **Can the work be safely re-run?** No (non-idempotent side effects) → pessimistic around exactly that segment, or make the side effect idempotent first. Optimistic without re-runnability is a duplicate-effect generator.
4. **Is the anomaly class single-row lost updates, or cross-row invariants?** Single row → row-level either flavor. Cross-row (write skew) → serializable mode or explicit predicate locking; row-level choices alone are insufficient.
5. **Does the engine offer managed serializable optimistic mode, and can the workload afford its abort rate?** Yes and yes → let the database detect conflicts instead of hand-writing checks per path.
6. **Default in doubt:** version columns as the baseline, targeted `FOR UPDATE` on measured hot rows, backoff-plus-jitter on every retry path, and periodic lock-wait checks — queue length on a row is the measurement that should drive a flip in either direction.

## Interview Questions

1. **Frame the choice as an economics claim, not a preference.** Pessimistic pays ~w (wait) per transaction on the contended resource and never wastes work; optimistic pays ~p·c (conflict probability × work cost) and never waits. Read-mostly and long-work-between-read-write push toward optimistic; hot rows with short transactions push toward pessimistic. State the arithmetic and the answer stops being a fashion debate.
2. **A team reports "optimistic locking causes duplicate emails under load." Diagnose.** The retry path re-ran the whole transaction including a non-idempotent side effect. Both fixes are needed: make the side effect idempotent (idempotency key derived from the entity version), and run side effects after commit so retries do not repeat them. The version column did not fail; the transaction boundary was drawn wrong.
3. **Why does pessimistic locking not eliminate the need for retry code?** Deadlock detection aborts victims, lock-wait timeouts fire, and serialization failures can still occur at the isolation level in use. Pessimistic reduces retry frequency; it does not remove the path. A batch job without retry-on-deadlock is a latent outage regardless of the locking strategy.
4. **What does MVCC change about this comparison, specifically?** It removes reader/writer blocking — historically pessimism's biggest tax — and makes snapshot reads free, so the read side of optimistic concurrency costs nothing. What remains is the write-write collision decision: queue it (locks) or abort-and-retry it (version columns / SSI). MVCC also enables engine-managed serializable modes that detect conflicts hand-written checks miss.
5. **Design the coordination for "last 5 units of a flash-sale item."** Pessimistic on the inventory row: `SELECT FOR UPDATE`, verify count, decrement, commit — microseconds, no payment call inside. Add a lock-wait queue-depth alert; if the sale saturates the row, batch or shard the counter rather than tuning timeouts — the ceiling is 1/hold-time, and the fix is hold-time.

## Key Takeaways

- The fork is **when contention's cost is paid**: up front as waiting for everyone (locks) or at commit as wasted work for losers (version checks) — crossover ≈ where p·c meets w.
- Pessimistic's signature failure is the lock held too long: row queues exhaust connection pools and stall unrelated traffic; its ceiling on a hot row is 1/hold-time.
- Optimistic's signature failure is the unmanaged retry: synchronized retry storms and repeated non-idempotent side effects; backoff, jitter, and idempotency are the mechanism's second half.
- Neither flavor fixes cross-row anomalies (write skew) by itself — isolation level and locking granularity are a separate axis from the optimistic/pessimistic choice.
- MVCC restructured the default: snapshot reads are free, engines can manage optimistic detection (SSI), and the hybrid — version columns broadly, targeted locks on hot rows — is how production systems ship.

## Cross-References

- [Database Choices: Why-Not Handbook](./database-choices.md) — the workload-level view of the same fork this page derives from mechanisms.
- [Concurrency Primitives: Why-Not Handbook](./concurrency-primitives.md) — the in-process sibling: mutexes and signaling, below the database row.
- [Database Isolation: Assumptions Hunt](../assumptions-hunt/database-isolation.md) — the isolation-level assumptions underneath both mechanisms.
- [ACID Transactions: Follow-up Tree](../followup-tree/acid-transactions.md) — the transaction ladder these locking choices climb.
- [Transactions and Concurrency Control: Connection Atlas](../connection-atlas/transactions-concurrency-control.md) — the dependency web linking isolation, MVCC, and locks.
- [Lock-Based Concurrency](../../dbms/transactions/lock-based.md) and [Optimistic Concurrency](../../dbms/transactions/optimistic.md) — the book's mechanism chapters for each half.
- [Snapshot Isolation](../../dbms/advanced/snapshot-isolation.md) — the write-skew anomaly that row-level choices do not cover.
- [PostgreSQL MVCC Internals](../../dbms/internals/postgresql-mvcc-deep.md) — the version-storage mechanics behind snapshot reads.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
