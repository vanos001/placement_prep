# Serializable Snapshot Isolation (SSI)

Serializable Snapshot Isolation (SSI) is a database isolation level that provides true Serializability on top of Snapshot Isolation, by tracking the read-write dependencies between transactions and aborting those that would create a serializability violation. It was introduced by Cahill, Roh, Fekete, et al. in 2008 (SIGMOD 2008 paper "Serializable Isolation for Snapshot Databases"). This page covers the protocol, the SIREAD lock mechanism, the implementation in PostgreSQL 9.1+, and the production trade-offs vs. plain SI.

## Why SSI Exists

Snapshot Isolation (SI) prevents most anomalies but allows write-skew: two transactions read the same data, both decide to make different writes based on their reads, and the combined writes violate an application invariant.

```text
T1: reads "On-call doctors: Alice, Bob" → sets Alice to "off".
T2: reads "On-call doctors: Alice, Bob" → sets Bob to "off".
Both commit. Now no doctors on call.
```

Under SI, this is allowed (T1 and T2 wrote different rows, no direct conflict). Under Serializability, the system would detect that T1 and T2 both depend on the "on-call count" and abort one of them.

SSI is the algorithm that detects these predicate-level conflicts and aborts the offending transaction. The cost: more aborts than SI, but no write-skew.

## The SSI Model: rw-Conflicts

The key abstraction is the "rw-conflict" (read-write conflict):

- T1 reads predicate P (e.g., "doctors on call").
- T2 writes a row matching P (e.g., updates Bob's status).
- T2's commit makes T1's read "stale" — if T1 had seen T2's write, it might have made a different decision.

SSI tracks these rw-conflicts. A serializability violation occurs when there's a "dangerous structure" of three transactions forming a cycle:

```text
T1 → T2 → T3
   rw    rw

T1 reads predicate P.
T2 writes a row matching P (creating rw-conflict T1 → T2).
T2 reads predicate Q.
T3 writes a row matching Q (creating rw-conflict T2 → T3).
If T3 also writes a row matching P (creating rw-conflict T3 → T1),
we have a cycle and must abort one of T1, T2, T3.
```

The SSI algorithm detects these cycles and aborts the "middle" transaction (T2 in this example). The middle transaction is the one most likely to be the cause of the conflict; aborting it breaks the cycle.

## The Implementation: SIREAD Locks

SSI tracks predicate reads via "SIREAD locks" (predicate read locks):

- When a transaction reads a predicate (via SELECT WHERE), the database notes the predicate and the table/index it scanned.
- When a transaction writes a row, the database checks: are there any active SIREAD locks whose predicate matches this row?
- If yes, an rw-conflict is recorded between the writer and the reader.
- The SSI algorithm uses the rw-conflict graph to detect cycles.

For efficiency, SIREAD locks are tracked at the index level. If a query uses an index range scan, the SIREAD lock is on the index range (not on individual rows). For sequential scans, the SIREAD lock is on the whole table (less precise, more false positives).

## The Implementation in PostgreSQL

PostgreSQL 9.1 (2011) implemented SSI as the SERIALIZABLE isolation level. The implementation:

1. **Per-tuple SIRead locks**: every row read by a SERIALIZABLE transaction is tracked.
2. **Predicate lock entries**: stored in a hash table, keyed by (relation OID, index OID, page number, tuple ID).
3. **Conflict detection**: on every write, check if any predicate lock matches. If yes, record the rw-conflict.
4. **Cycle detection**: when a transaction prepares to commit, check if its rw-conflicts form a dangerous structure.
5. **Abort**: if a dangerous structure is detected, abort the middle transaction.

The implementation is in `src/backend/storage/lmgr/predicate.c` (~4000 lines).

```sql
-- Use SSI in PostgreSQL
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM doctors WHERE on_call = true;
-- ... possibly update a doctor's on_call status ...
COMMIT;  -- may fail with "could not serialize access due to read/write dependencies"
```

If the commit fails, the application must retry the transaction.

## Performance

SSI's overhead vs. plain SI:
- **CPU**: 5-15% for the predicate lock tracking.
- **Memory**: 100-500 bytes per predicate lock, depending on granularity.
- **Abort rate**: 0.5-5% for typical workloads (higher for conflict-heavy workloads).

For low-conflict workloads, SSI is essentially free. For high-conflict workloads (e.g., a counter incremented by many concurrent transactions), SSI's abort rate becomes the bottleneck.

The rule of thumb: use SSI when you need correctness (financial transactions, ordering systems); use SI when you can tolerate write-skew (analytics, dashboards).

## Production Use

- **PostgreSQL**: SERIALIZABLE since 9.1. Default isolation is Read Committed.
- **CockroachDB**: SERIALIZABLE is the default (their implementation is SSI-based, but the protocol is integrated with their HLC and 2PC).
- **FoundationDB**: SERIALIZABLE is the only isolation (strict serializability, in fact).
- **SQL Server**: has SERIALIZABLE but it's lock-based, not SSI.
- **Oracle**: doesn't support SSI; "Serializable" is actually SI in Oracle.

## The SSI Test Cases

SSI's behavior on common anomalies:

| Anomaly | SI | SSI |
|---------|----|-----|
| Dirty read | Prevented | Prevented |
| Non-repeatable read | Prevented | Prevented |
| Phantom read | Prevented | Prevented |
| Lost update | Prevented | Prevented |
| **Write skew** | **Allowed** | **Prevented** |
| Read-only transaction anomaly | Allowed (rare) | Prevented |

The read-only transaction anomaly is a subtle case where a read-only transaction sees inconsistent data even though the writers were serializable. SSI prevents this; SI doesn't.

## Common Pitfalls

1. **Forgetting that SSI can abort transactions.** An SSI transaction can fail with "could not serialize". The application must retry — typically 3-5 times.

2. **Using SERIALIZABLE for high-conflict workloads.** A counter incremented by many transactions will see high abort rates. Use SI or 2PL for these.

3. **Treating SSI aborts as errors.** They're not errors — they're a sign that the system detected a potential serializability violation and prevented it. Log them as informational, not warnings.

4. **Forgetting that SSI requires careful index design.** Sequential scans create whole-table SIREAD locks, which over-abort. Use indexes to narrow the predicate locks.

5. **Mixing SERIALIZABLE and lower-isolation transactions.** A SERIALIZABLE transaction that conflicts with a Read Committed transaction may abort unnecessarily (the RC transaction doesn't track conflicts). Best practice: use SERIALIZABLE for all transactions in a database that needs serializability.

6. **Long-running SSI transactions.** An SSI transaction that holds a SIREAD lock for hours blocks any writer matching the predicate. Set a transaction timeout.

## Comparison to Two-Phase Locking (2PL)

| Aspect | SSI | Strict 2PL |
|--------|-----|------------|
| Isolation | Serializable | Serializable |
| Read locks | Predicate locks (released at commit) | Row locks (held until commit) |
| Write locks | Row locks (held until commit) | Row locks (held until commit) |
| Deadlocks | No (no waiting) | Yes (waits cause cycles) |
| Abort rate | Higher (for conflict-heavy) | Lower (waits instead of aborts) |
| Throughput | Lower for low-conflict (overhead) | Lower for high-conflict (lock waits) |

SSI is better for low-conflict workloads with many short transactions (web apps). 2PL is better for high-conflict workloads (OLTP with many updates to the same row).

## When to Use SSI

- You need Serializability for correctness (financial transactions, ordering).
- Your workload has low write-conflict (most transactions write different rows).
- You can tolerate some aborts and retries.

When NOT to use SSI:
- High-conflict workloads (counters, leaderboards).
- Long-running transactions (would hold SIREAD locks too long).
- Workloads where SI is "good enough" (analytics, reporting).

## References

- Cahill, Roh, Fekete, et al., "[Serializable Isolation for Snapshot Databases](https://www.eecs.harvard.edu/~margo/papers/fekete-sigmod2008.pdf)" (SIGMOD 2008)
- [PostgreSQL 9.1 Release Notes (SSI)](https://www.postgresql.org/docs/9.1/release-9-1.html)
- [PostgreSQL SSI implementation (source)](https://github.com/postgres/postgres/blob/master/src/backend/storage/lmgr/predicate.c)
- [PostgreSQL: Transaction Isolation (SSI)](https://www.postgresql.org/docs/current/transaction-iso.html)
- Fekete et al., "[Making Snapshot Isolation Serializable](https://www.eecs.harvard.edu/~margo/papers/fekete-sigmod2005.pdf)" (SIGMOD 2005)
- [CockroachDB docs: transaction layer (SSI + hybrid-logical clocks)](https://www.cockroachlabs.com/docs/stable/architecture/transaction-layer)
- [LWN: SSI in PostgreSQL (2011)](https://lwn.net/Articles/460358/)
