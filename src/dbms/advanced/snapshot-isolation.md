# Snapshot Isolation

Snapshot Isolation (SI) is a database isolation level where a transaction sees a consistent snapshot of the database as of its start time, as if the database were frozen at that moment. SI is the default isolation level in PostgreSQL (called "Repeatable Read" there), Microsoft SQL Server, and Oracle. It is weaker than Serializable but stronger than Read Committed. This page covers the protocol, the write-skew anomaly that SI doesn't prevent, the implementation via MVCC, and the variants (Serializable Snapshot Isolation, Strong SI).

## The Snapshot Isolation Guarantee

A transaction T starting at time `T_start` sees:
- All writes committed before `T_start` (visible).
- No writes that started after `T_start` and committed before T's reads (invisible — even though they're committed).
- T's own writes (visible to itself but not to others until commit).

Additionally, SI guarantees **no read anomalies** (no dirty reads, no non-repeatable reads, no phantom reads) — every read in T returns the same snapshot.

The classic test:
```sql
-- T1 begins at time 0
BEGIN ISOLATION LEVEL REPEATABLE READ;  -- Snapshot Isolation in PostgreSQL
SELECT count(*) FROM accounts WHERE balance > 100;
-- returns 5

-- T2 begins at time 1, updates a row, commits
BEGIN; UPDATE accounts SET balance = 200 WHERE id = 1; COMMIT;

-- T1 continues
SELECT count(*) FROM accounts WHERE balance > 100;
-- still returns 5 (T2's update is invisible)
```

Without SI (at Read Committed), the second SELECT would see 6 (T2's update is visible). SI prevents this non-repeatable read.

## The Write-Skew Anomaly

SI does NOT prevent write-skew, the canonical anomaly that requires Serializable to fix:

```text
T1 reads "Doctors on call: Alice, Bob" → both can be off?
T2 reads "Doctors on call: Alice, Bob" → both can be off?
T1 updates "Alice is off" (commits)
T2 updates "Bob is off" (commits)
Now: no doctors on call. Constraint violated.
```

Each transaction committed successfully (no conflicting writes), but the combination of the two writes violates the application constraint ("at least one doctor on call").

This is the SI weakness: it prevents conflicting writes (via first-committer-wins), but doesn't detect predicate conflicts (both transactions read the same data and made decisions based on the snapshot).

## The Implementation: Multi-Version Concurrency Control (MVCC)

MVCC is the standard implementation of SI. The database maintains multiple versions of each row:

```text
Row versions for row R:
  V1: written at time 0, contents = "value A", end = NULL (committed)
  V2: written at time 1, contents = "value B", end = NULL (committed)
  (V1's end is updated to time 1 when V2 is created)
```

When a transaction at time `T` reads row R:
- It scans the row versions for the latest version with `start <= T` and `end > T` (or `end = NULL` for uncommitted-to-others versions).
- That version is what the transaction sees.

When a transaction writes row R:
- It creates a new version with `start = T` and `end = NULL`.
- The previous version's `end` is updated to `T` (if the new version is committed).

This is "version chain" MVCC. PostgreSQL and Oracle use it. SQL Server uses a variant called "row-versioning".

## First-Committer-Wins

For two concurrent transactions T1 and T2 both writing to the same row:
- The first to commit wins. The second sees the first's write (when it tries to commit) and aborts with a serialization failure.

```text
T1 begins at time 0, reads row R = "A"
T2 begins at time 0, reads row R = "A"
T1 writes R = "B", commits at time 1.
T2 writes R = "C", tries to commit:
  Check: did any concurrent transaction write R?
  Yes: T1 wrote R at time 1, committed.
  T2 aborts with "could not serialize access due to concurrent update".
```

This is the "first-committer-wins" rule. SI prevents lost updates (where T1's write is overwritten by T2's commit) but allows write-skew (where T1 and T2 write different rows but their combination is invalid).

## Performance of MVCC

MVCC's main cost is storage: each row has multiple versions. The database must garbage-collect old versions when no transaction can see them anymore.

PostgreSQL's VACUUM process identifies "dead tuples" (versions not visible to any active transaction) and removes them, freeing space. Without regular VACUUM, the database bloats — a 1 GB table can grow to 10 GB of version history if updates are frequent.

The autovacuum daemon (since PostgreSQL 8.0) automates this. The key tuning parameters:
- `autovacuum_vacuum_threshold`: minimum updates before vacuuming (default 50).
- `autovacuum_vacuum_scale_factor`: fraction of table updates before vacuuming (default 0.2 = 20%).
- `autovacuum_naptime`: how often to check (default 1 minute).

## SI vs. Read Committed

| Property | Read Committed | Snapshot Isolation |
|----------|----------------|---------------------|
| Dirty reads | Prevented | Prevented |
| Non-repeatable reads | Allowed | Prevented |
| Phantoms | Allowed | Prevented |
| Write-skew | Allowed | Allowed |
| Lost updates | Allowed | Prevented |
| Implementation | Locks + 2 versions | MVCC + version chain |
| Performance | Lock contention | Storage bloat (with VACUUM) |

For most workloads, SI is the recommended default — it's safer than Read Committed without Serializable's overhead.

## SI vs. Serializable

| Property | Snapshot Isolation | Serializable |
|----------|---------------------|---------------|
| Dirty reads | Prevented | Prevented |
| Non-repeatable reads | Prevented | Prevented |
| Phantoms | Prevented | Prevented |
| Write-skew | **Allowed** | Prevented |
| Lost updates | Prevented | Prevented |
| Abort rate | Low | Higher (SSI may restart transactions) |
| Implementation | MVCC | SSI (predicate locks) |

Serializable Snapshot Isolation (SSI, see [SSI page](./serializable-snapshot-isolation.md)) extends SI with predicate tracking to prevent write-skew. The cost is higher abort rates and additional bookkeeping.

## Production Implementations

### PostgreSQL

PostgreSQL's default isolation is "Read Committed", but users can set "REPEATABLE READ" (which is Snapshot Isolation — PostgreSQL's "REPEATABLE READ" is SI per the SQL standard's terminology):

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM accounts WHERE balance > 100;
-- ... other queries ...
COMMIT;
```

If a write conflict occurs, the commit fails with error "could not serialize access due to concurrent update". The application must retry.

PostgreSQL also offers "SERIALIZABLE" isolation, which is SSI (implemented in 9.1).

### Oracle

Oracle's default is "Read Committed", but "Serializable" (the SQL standard's name) is actually Snapshot Isolation (despite the name):

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

Oracle doesn't support true Serializable (SSI); its "Serializable" is SI.

### Microsoft SQL Server

SQL Server's default is "Read Committed". Snapshot Isolation is opt-in:

```sql
-- Enable snapshot isolation on the database (one-time)
ALTER DATABASE mydb SET ALLOW_SNAPSHOT_ISOLATION ON;

-- Use it in a transaction
SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
BEGIN TRANSACTION;
...
COMMIT;
```

SQL Server also has "Read Committed Snapshot Isolation" (RCSI), which is Read Committed but reads see a snapshot (instead of acquiring read locks). RCSI is the default in Azure SQL Database.

### MySQL

MySQL InnoDB's "REPEATABLE READ" is Snapshot Isolation. It's the default.

## Common Pitfalls

1. **Forgetting that SI doesn't prevent write-skew.** A common assumption is that "snapshot isolation = serializable". It's not. Write-skew can happen.

2. **Not handling serialization failures.** SI transactions can abort with "could not serialize". The application must retry — typically 3-5 times with exponential backoff.

3. **Leaving transactions open for too long.** A long-running SI transaction keeps version history alive, bloating the database. Set a transaction timeout.

4. **Treating VACUUM as optional.** Without regular VACUUM, the database grows without bound. Configure autovacuum aggressively on update-heavy tables.

5. **Confusing "REPEATABLE READ" (SQL standard) with SI.** The SQL standard's "REPEATABLE READ" is a weaker level than SI; some implementations (PostgreSQL, MySQL) make it equivalent to SI, but this isn't guaranteed by the standard.

6. **Forgetting that SELECT FOR UPDATE conflicts.** Two `SELECT ... FOR UPDATE` of the same row in SI will cause the second to block or abort, depending on the implementation. SI's "first-committer-wins" applies here.

## References

- Berenson et al., "[A Critique of ANSI SQL Isolation Levels](https://www.cs.umb.edu/~poneil/iso.pdf)" (SIGMOD 1995) — the original SI write-skew discussion
- [PostgreSQL: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [Oracle Database: Data Concurrency and Consistency](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/data-concurrency-and-consistency.html)
- [Microsoft SQL Server: Snapshot Isolation](https://learn.microsoft.com/en-us/sql/relational-databases/databases/snapshots)
- Wu et al., "[Serialization and Snapshot Isolation in Distributed Databases](https://www.cs.umd.edu/~abadi/papers/abadi-sssi-vldb08.pdf)" (VLDB 2008)
- [LWN: Snapshot Isolation and the Lost Update problem](https://lwn.net/Articles/593062/)
- Fekete et al., "[Making Snapshot Isolation Serializable](https://www.eecs.harvard.edu/~margo/papers/fekete-sigmod2005.pdf)" (SIGMOD 2005) — the basis of SSI
