# Transaction Internals

## Overview

Transactions are the mechanism that provide ACID guarantees. While many resources cover isolation levels at the SQL level, this document digs into the *implementation*: how databases track transaction state, how undo and redo logs interact, how MVCC determines visibility, and how deadlocks are detected and resolved.

## Transaction States

Every transaction transitions through a well-defined state machine:

```
                BEGIN
                  │
                  ▼
             [ACTIVE] ─── abort() ───→ [ABORTED]
                  │                         │
          partial commit                   │
                  │                         │
                  ▼                         │
            [PARTIALLY COMMITTED] ────────→ × (after cleanup)
                  │
           last log record
           written to disk
                  │
                  ▼
              [COMMITTED]
```

| State | Description | Can Rollback? |
|-------|-------------|---------------|
| **Active** | Transaction is executing statements | Yes (ROLLBACK) |
| **Partially Committed** | Last statement finished, WAL flushed | Yes (if crash before commit record) |
| **Committed** | Commit record written to WAL | No |
| **Aborted** | Transaction rolled back | No (already undone) |
| **Failed** | Error during execution (e.g., constraint violation) | Auto-aborted |

## Undo Log and Redo Log

Databases maintain two distinct log types to support different recovery needs:

| Aspect | Redo Log | Undo Log |
|--------|----------|----------|
| **Purpose** | Re-apply committed changes after crash | Reverse uncommitted changes (rollback + MVCC) |
| **Content** | After-image (new value) or physiological operation | Before-image (old value) |
| **When written** | Before modifying page in buffer pool | Before modifying page in buffer pool |
| **Structure** | Sequential, per-page logical records | Per-transaction chain (prev_LSN links) |
| **Retention** | Until checkpointed | Until no active snapshot needs it |
| **Used by** | ARIES recovery (redo pass), replication | ARIES recovery (undo pass), MVCC (InnoDB) |
| **InnoDB** | `ib_logfile*` (redo log) | Undo tablespaces (rollback segments) |
| **PostgreSQL** | WAL segments | No separate undo log (uses tuple versioning) |

### InnoDB Undo Log Structure

InnoDB's undo log is organized into **rollback segments**, each containing multiple **undo slots**. Each transaction is assigned an undo slot.

```
Rollback Segment
├── Rseg Header (points to undo slots)
├── Undo Slot 0 → Undo Log Chain (Transaction 1)
│   ├── Undo Record: <page, offset, before_image> (INSERT: row_location)
│   ├── Undo Record: <page, offset, before_image> (UPDATE: old_row)
│   └── ... (linked via undo_no)
├── Undo Slot 1 → Undo Log Chain (Transaction 2)
└── ...
```

For MVCC reads, InnoDB reconstructs old row versions by traversing the undo log chain: the current row has a `roll_ptr` pointing to the undo record containing the previous version, which in turn has a `roll_ptr` to the version before it, and so on.

## ARIES Recovery Algorithm Overview

ARIES (Algorithm for Recovery and Isolation Exploiting Semantics) is the gold standard for crash recovery, used by InnoDB, SQL Server, and IBM DB2. PostgreSQL uses a similar but simplified approach.

### Three-Pass Recovery

```
Pass 1: ANALYSIS (scan WAL forward from last checkpoint)
├── Rebuild the dirty page table (DPT): which pages were dirty at crash?
├── Rebuild the transaction table (TT): which transactions were active?
├── Determine the starting LSN for the redo pass
└── Result: DPT + TT at crash time

Pass 2: REDO (scan WAL forward from earliest dirty page LSN)
├── For each log record:
│   if pageLSN < log_record.LSN:
│       re-apply the operation to the page
├── This re-creates the exact state at crash time
│   (including uncommitted changes = "steal" policy)
└── Result: All pages are in their crash-time state

Pass 3: UNDO (scan WAL backward from end)
├── For each active (uncommitted) transaction in TT:
│   Follow the transaction's LSN chain backward
│   For each record: apply the undo operation
│   Write a Compensation Log Record (CLR) for idempotency
│   Mark transaction as aborted
└── Result: Only committed transactions' effects remain
```
### Key ARIES Properties

| Property | Meaning |
|----------|---------|
| **Steal** | Dirty pages of uncommitted transactions can be written to disk (requires undo) |
| **No-force** | Committed pages need not be written to disk at commit time (requires redo) |
| **Physiological logging** | Redo operates at physical page level; undo operates at logical operation level |
| **CLRs** | Compensation Log Records prevent re-undoing during recovery re-runs |
| **Fuzzy checkpoints** | Checkpoints record the oldest dirty page LSN but don't require all pages to be flushed |

## MVCC Implementation: PostgreSQL Approach

PostgreSQL implements MVCC by storing **multiple versions of each tuple directly in the heap**. Every tuple header contains visibility metadata:

```
+------------------------------------------+
| HeapTupleHeaderData (23 bytes)            |
|  t_xmin: XID of the transaction that      |
|          created this tuple                |
|  t_xmax: XID of the transaction that      |
|          deleted/updated this tuple        |
|          (0 = not deleted)                 |
|  t_cid: command ID within the transaction  |
|          (for statements within one txn)   |
|  t_ctid: CTID of the NEW tuple version    |
|          (if this one was updated)          |
|  t_infomask: hint bits (visibility cache) |
+------------------------------------------+
| User data columns                         |
+------------------------------------------+
```

### Tuple Visibility Rules

A snapshot at time T sees a tuple if:

```
1. t_xmin is committed (exists in CLOG as committed) AND t_xmin ≤ snapshot_xmin
   OR t_xmin == current_transaction_id

2. AND either:
   a) t_xmax == 0 (tuple not deleted) OR
   b) t_xmax is not committed (deleter is still active) OR  
   c) t_xmax > snapshot_xmax (deletion happened after our snapshot)
```

### Hint Bits

Checking the CLOG (commit log, a 2-bit array per XID) for every tuple is expensive. PostgreSQL stores **hint bits** in `t_infomask` after the first visibility check:

| Hint Bit | Meaning |
|----------|---------|
| `HEAP_XMIN_COMMITTED` | Creator is committed (no CLOG lookup needed) |
| `HEAP_XMIN_INVALID` | Creator aborted or rolled back |
| `HEAP_XMAX_COMMITTED` | Deleter is committed (tuple is dead) |
| `HEAP_XMAX_INVALID` | Deleter aborted (tuple is still alive) |

These hints eliminate most CLOG lookups in practice. A query that reads 1M rows typically only hits CLOG for rows created/deleted by very recent transactions.

## Snapshot Isolation vs Serializability

| Aspect | Snapshot Isolation (SI) | Serializable | 
|--------|------------------------|---------------|
| **Guarantee** | Reads are consistent within a snapshot | Full serializability (no anomalies) |
| **Anomalies prevented** | Dirty reads, non-repeatable reads, phantom reads *in theory* | Write skew, all anomalies |
| **Write skew** | **Not prevented** (classic SI bug) | Prevented |
| **Implementation** | Snapshot + first-committer-wins | SSI (Serializable Snapshot Isolation) or 2PL |
| **PostgreSQL default** | `READ COMMITTED` and `REPEATABLE READ` both use SI | `SERIALIZABLE` uses SSI |
| **InnoDB** | `REPEATABLE READ` ≈ SI | `SERIALIZABLE` uses locking |

### Write Skew Example

```
-- Two doctors checking hospital rules:
-- Rule: at least one doctor must be on call
-- Doctor A: SELECT COUNT(*) WHERE on_call=true  → returns 2
-- Doctor B: SELECT COUNT(*) WHERE on_call=true  → returns 2
-- Doctor A: UPDATE doctors SET on_call=false WHERE name='A'  (ok, thinks B is on call)
-- Doctor B: UPDATE doctors SET on_call=false WHERE name='B'  (ok, thinks A is on call)
-- Now ZERO doctors are on call — write skew!
```

Under snapshot isolation, both transactions see a snapshot where 2 doctors are on call, and both commit successfully. Under serializable isolation, SSI detects the conflict and aborts one.

## Predicate Locking vs Key-Range Locking

Phantom reads occur when a new row matching a query's WHERE clause is inserted between two reads. Two approaches prevent this:

| Approach | Mechanism | Granularity | Used By |
|----------|-----------|-------------|---------|
| **Predicate locking** | Lock the *predicate* (e.g., `department=5 AND salary>100000`) | Logical predicate | PostgreSQL SSI (tracks predicates, doesn't actually lock) |
| **Key-range (gap) locking** | Lock the *gap* between index entries | Index range | InnoDB (next-key locks = record lock + gap lock) |

InnoDB's next-key lock: `SELECT * FROM employees WHERE id BETWEEN 10 AND 20 FOR UPDATE` locks rows 10-20 **and the gaps** before 10, between rows, and after 20. This prevents any INSERT in the range.

PostgreSQL's SSI tracks read predicates (via `SIReadLock` pseudo-locks) and checks for dangerous structures (rw-conflicts between transactions) at commit time. It does not block writes — it aborts one transaction if a serializability violation is detected.

## Deadlock Detection in Databases

### Wait-For Graph (WFG)

A deadlock occurs when there is a cycle in the wait-for graph:

```
T1 → (waiting for lock held by) → T2 → (waiting for lock held by) → T1
```

### Detection Algorithms

| Approach | How It Works | Used By |
|----------|-------------|---------|
| **Timeout-based** | Abort transaction if it waits > `lock_timeout` | Simple, can falsely abort non-deadlocked txns |
| **WFG cycle detection** | Maintain a directed graph; run cycle detection periodically | InnoDB (`innodb_deadlock_detect`), PostgreSQL | 
| **Wait-die / wound-wait** | Prevent deadlocks entirely via timestamp ordering | Distributed systems, some academic DBs |

### InnoDB Deadlock Detection

InnoDB maintains a lock table mapping `(transaction, resource) → lock`. When a transaction requests a lock and must wait:

1. A **wait-for** edge is created: `T_waiter → T_holder`
2. InnoDB checks if this edge creates a cycle in the WFG
3. If a cycle is found, InnoDB picks a **victim** (the transaction with the least amount of work done, measured by undo log size)
4. The victim is rolled back with `ER_LOCK_DEADLOCK` (error 1213)
5. The application must retry the transaction

```
Wait-for graph before deadlock detection:
  T1 → lock_A (held by T2)
  T2 → lock_B (held by T3)
  T3 → lock_C (held by T1)  ← CYCLE DETECTED!

Victim: T3 (smallest undo log = least work done)
T3 is rolled back, T1 and T2 proceed
```

### Deadlock Avoidance Tips

1. Always access tables in the **same order** across transactions
2. Keep transactions **short** (reduce lock hold time)
3. Use **consistent indexing** — InnoDB locks rows it scans, not just matching rows
4. Consider `SELECT ... FOR SKIP LOCKED` for job queues (skip locked rows instead of waiting)
5. Set `innodb_deadlock_detect=OFF` and use `lock_wait_timeout` if detection is too expensive at high concurrency

## Interview Questions

**Q: Explain the ARIES recovery algorithm. Why are three passes needed?**
A: (1) **Analysis**: Scan WAL forward from checkpoint to rebuild the dirty page table and active transaction table at crash time. (2) **Redo**: Scan WAL forward from the earliest dirty page's LSN, re-applying all changes (committed and uncommitted) to bring pages to their crash-time state. (3) **Undo**: Scan WAL backward, undoing all changes from uncommitted transactions using CLRs. Three passes are needed because a single forward scan cannot distinguish committed from uncommitted (the commit record may be after the crash), and the undo pass needs to know which transactions were active.

**Q: How does PostgreSQL's MVCC differ from InnoDB's, and what are the tradeoffs?**
A: **PostgreSQL** stores multiple tuple versions in the heap. Each tuple has `xmin`/`xmax` for visibility. Old versions are cleaned up by VACUUM. **InnoDB** stores only the latest version in the data page and reconstructs old versions from the undo log on demand. PostgreSQL's approach is simpler (no undo log management) but causes table bloat. InnoDB's approach avoids bloat but adds complexity (undo log retention, purge thread).

**Q: What is write skew, and which isolation levels prevent it?**
A: Write skew occurs when two transactions read overlapping data, make decisions based on their snapshot, and then update disjoint rows, creating an inconsistent state that no single transaction would have created. Snapshot isolation (PostgreSQL REPEATABLE READ, InnoDB REPEATABLE READ) does NOT prevent write skew. Only serializable isolation prevents it — PostgreSQL uses SSI ( Serializable Snapshot Isolation), InnoDB uses traditional locking.

**Q: How does InnoDB's gap locking work, and why does it prevent phantoms?**
A: InnoDB's next-key lock = record lock on the index entry + gap lock on the gap before it. When `SELECT ... FOR UPDATE` scans a range, it locks all existing rows AND the gaps between them. This prevents any INSERT in the range, which is exactly what a phantom is (a new row appearing in a subsequent read of the same range). Gap locking only works with the REPEATABLE READ isolation level.

**Q: A deadlock is detected and transaction T1 is chosen as the victim. What should the application do?**
A: The application catches the deadlock error (MySQL error 1213, PostgreSQL `SQLSTATE 40P01`) and **retries the entire transaction** from the beginning. It should NOT just retry the failed statement — the transaction state is undefined after rollback. Retry with exponential backoff to avoid thundering herd.

**Q: What are CLRs in ARIES and why are they needed?**
A: A Compensation Log Record (CLR) is written during the undo pass when an operation is rolled back. It records that the undo has been applied. CLRs are needed for **idempotency**: if the system crashes during the undo pass and recovery restarts, the CLR signals that this undo has already been applied, preventing double-undo. CLRs are redo-only (they have no undo of their own).

## References
- PostgreSQL: [MVCC Concurrency Control](https://www.postgresql.org/docs/current/mvcc.html)
- MySQL: [InnoDB Locking](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html)
- *Transaction Processing: Concepts and Techniques*, Gray & Reuter — The ARIES paper and comprehensive theory
- *Designing Data-Intensive Applications*, Martin Kleppmann — Chapter 7 (Transactions)
