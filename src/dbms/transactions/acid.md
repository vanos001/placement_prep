# ACID Properties

## Overview

**ACID** is an acronym for four properties that guarantee reliable processing of database transactions. These properties ensure that the database remains consistent despite errors, crashes, and concurrent access.

## The Four Properties

```mermaid
graph TD
    A["Atomicity<br/>All or Nothing"] --> TXN[Transaction]
    C["Consistency<br/>Valid State Transitions"] --> TXN
    I["Isolation<br/>Concurrent Safety"] --> TXN
    D["Durability<br/>Crash Resilience"] --> TXN

    style A fill:#ffcdd2
    style C fill:#c8e6c9
    style I fill:#bbdefb
    style D fill:#fff9c4
```

## Atomicity

**"All or nothing"** — A transaction's operations either all succeed or all fail. If any operation fails, the entire transaction is rolled back.

### Implementation Mechanism
- **Undo logging**: Before modifying data, the original value is written to a log. On rollback, the log is used to restore original values.
- **Shadow paging**: The database maintains a shadow copy of pages. On commit, the shadow is updated; on abort, the shadow is discarded.

### Example

```sql
BEGIN;
UPDATE Accounts SET balance = balance - 100 WHERE id = 1;  -- Succeeds
UPDATE Accounts SET balance = balance + 100 WHERE id = 2;  -- Fails (constraint violation)
ROLLBACK;  -- Both operations rolled back, no money lost
```

```mermaid
sequenceDiagram
    participant T as Transaction
    participant DB as Database
    participant LOG as Undo Log

    T->>DB: UPDATE Accounts SET balance = balance - 100 WHERE id = 1
    DB->>LOG: Save old balance (500)
    DB->>DB: balance = 400

    T->>DB: UPDATE Accounts SET balance = balance + 100 WHERE id = 2
    DB->>DB: Error: constraint violation

    T->>DB: ROLLBACK
    DB->>LOG: Read old balance
    DB->>DB: Restore balance = 500
```

## Consistency

**"Valid state transitions"** — A transaction brings the database from one consistent state to another. All constraints (PK, FK, CHECK, triggers) must be satisfied before and after the transaction.

### What Consistency Ensures
- Primary key uniqueness
- Foreign key referential integrity
- CHECK constraints
- Trigger-based invariants
- Application-level business rules (partially)

### Example

```sql
-- Consistency rule: total balance across all accounts must be constant
-- Before: Account A = 500, Account B = 300, Total = 800

BEGIN;
UPDATE Accounts SET balance = balance - 100 WHERE id = 'A';  -- A = 400
UPDATE Accounts SET balance = balance + 100 WHERE id = 'B';  -- B = 400
COMMIT;
-- After: Total = 800 ✅ (consistency maintained)
```

**Note**: Consistency is partially the application's responsibility. The DBMS enforces structural constraints; the application must enforce business rules.

## Isolation

**"Concurrent safety"** — Concurrent transactions appear to execute in isolation. The intermediate state of one transaction is not visible to others.

### Concurrency Problems Prevented

| Problem | Description | Isolation Level Required |
|---|---|---|
| Dirty Read | Read uncommitted data | READ COMMITTED |
| Non-Repeatable Read | Same query, different result | REPEATABLE READ |
| Phantom Read | New rows appear between reads | SERIALIZABLE |
| Lost Update | Concurrent writes overwrite | REPEATABLE READ |

### Implementation Mechanisms
- **Locking**: 2PL (Two-Phase Locking)
- **MVCC**: Multi-Version Concurrency Control
- **Timestamp ordering**: Each transaction gets a timestamp

See: [Isolation Levels](isolation-levels.md), [Concurrency Control](concurrency-control.md)

## Durability

**"Crash resilience"** — Once a transaction is committed, its changes persist even if the system crashes immediately after.

### Implementation Mechanism
- **Write-Ahead Logging (WAL)**: All changes are written to a log on stable storage BEFORE being applied to the database. On crash recovery, the log is replayed.
- **Force-at-commit**: All log records for a transaction are forced to stable storage before COMMIT returns.

### Example

```sql
BEGIN;
INSERT INTO Orders VALUES (1001, 'Alice', 500.00);
COMMIT;
-- At this point, even if the server crashes, the order is guaranteed to exist
-- because the WAL was flushed to disk before COMMIT returned
```

```mermaid
sequenceDiagram
    participant T as Transaction
    participant WAL as Write-Ahead Log (disk)
    participant DB as Database (buffer)

    T->>WAL: Write INSERT log record
    WAL->>WAL: Flush to disk
    T->>DB: Apply INSERT to buffer
    T->>WAL: Write COMMIT record
    WAL->>WAL: Flush to disk
    T->>T: COMMIT returns

    Note over DB: If crash here, recovery replays the log
```

## ACID in Practice

### RDBMS (PostgreSQL, MySQL, Oracle)

Full ACID support with configurable isolation levels. Uses WAL for durability, MVCC for isolation, and strict constraint enforcement for consistency.

### NoSQL (MongoDB, Cassandra, DynamoDB)

- **MongoDB**: ACID for single-document operations. Multi-document transactions available since v4.0 (with performance overhead).
- **Cassandra**: Tunable consistency (eventual, quorum, all). No cross-partition transactions.
- **DynamoDB**: ACID for single-item operations. Transactions for up to 100 items.

### NewSQL (CockroachDB, TiDB, Spanner)

Full ACID across distributed nodes using distributed consensus (Raft, Paxos).

## BASE Model (NoSQL Alternative)

| ACID | BASE |
|---|---|
| **A**tomicity | **B**asically **A**vailable |
| **C**onsistency | **S**oft state |
| **I**solation | **E**ventual consistency |
| **D**urability | — |

BASE sacrifices strong consistency for availability and partition tolerance (CAP theorem trade-off).

## Interview Questions

### Beginner

**Q1: What are ACID properties?**
A: Atomicity (all-or-nothing), Consistency (valid state transitions), Isolation (concurrent safety), Durability (crash resilience). They ensure database transactions are reliable.

**Q2: What is the difference between atomicity and durability?**
A: **Atomicity** ensures a transaction's operations all succeed or all fail — partial updates are rolled back. **Durability** ensures committed changes survive crashes — once committed, data is permanent.

**Q3: How does the database ensure durability?**
A: Through Write-Ahead Logging (WAL). Before any change is applied to the database, it's written to a log on stable storage. On crash recovery, the log is replayed to restore committed transactions.

### Intermediate

**Q4: Can a database be consistent but not durable?**
A: Yes. Consistency ensures valid state transitions during normal operation. Durability ensures those states persist after crashes. An in-memory database without persistence is consistent but not durable.

**Q5: How does PostgreSQL implement ACID?**
A: **Atomicity**: Uses MVCC — uncommitted changes are invisible; ROLLBACK discards the transaction's changes. **Consistency**: Constraint enforcement (PK, FK, CHECK, triggers). **Isolation**: MVCC with snapshot isolation. **Durability**: WAL with fsync before COMMIT.

**Q6: What's the relationship between ACID and CAP theorem?**
A: ACID focuses on single-node transaction guarantees. CAP theorem applies to distributed systems — you can have at most 2 of: Consistency, Availability, Partition tolerance. Traditional RDBMS prioritizes C and A; distributed NoSQL often sacrifices C for A and P.

### Advanced

**Q7: How do distributed databases achieve ACID across nodes?**
A: Distributed ACID requires:
- **Atomicity**: Two-phase commit (2PC) or consensus protocols (Paxos/Raft)
- **Consistency**: Distributed constraint checking, consensus on state
- **Isolation**: Distributed lock management or distributed MVCC
- **Durability**: Replication (synchronous for strong durability, asynchronous for performance)

Examples: Google Spanner uses TrueTime + Paxos; CockroachDB uses Raft + serializable isolation.

**Q8: Design a system that guarantees exactly-once processing for a message queue with database writes.**
A:
```sql
-- Idempotency table
CREATE TABLE ProcessedMessages (
    message_id VARCHAR(255) PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Transaction with idempotency check
BEGIN;
INSERT INTO ProcessedMessages (message_id) VALUES ('msg-123')
ON CONFLICT (message_id) DO NOTHING;

-- Only process if this is a new message
INSERT INTO Orders (customer_id, amount)
SELECT 'cust-1', 500.00
WHERE EXISTS (SELECT 1 FROM ProcessedMessages WHERE message_id = 'msg-123'
              AND processed_at > NOW() - INTERVAL '5 minutes');
COMMIT;
```

## Common Mistakes

- Assuming consistency is fully handled by the DBMS (application must enforce business rules)
- Not understanding that isolation levels trade correctness for performance
- Confusing atomicity with durability
- Not using transactions for multi-statement operations
- Committing too frequently (transaction overhead) or too infrequently (holding locks too long)

## Summary

| Property | Guarantee | Mechanism |
|---|---|---|
| Atomicity | All or nothing | Undo log, shadow paging |
| Consistency | Valid state transitions | Constraints, triggers |
| Isolation | Concurrent safety | Locking, MVCC, timestamps |
| Durability | Crash resilience | WAL, force-at-commit |

## Cross-References

- [Transaction States](states.md) — Transaction lifecycle
- [Isolation Levels](isolation-levels.md) — Isolation trade-offs
- [Concurrency Control](concurrency-control.md) — Implementing isolation
- [Recovery](recovery.md) — Implementing durability
- [Serializability](serializability.md) — Strongest isolation guarantee


## Cross References

- [Isolation Levels](isolation-levels.md)
- [Concurrency Control](concurrency-control.md)
- [WAL](../internals/wal.md)
- [Serializability](serializability.md)
- [Consensus](../../distributed/consensus/raft.md)
