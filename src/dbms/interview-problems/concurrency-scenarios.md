# DBMS Concurrency Scenarios

These scenarios connect transaction theory to the operational behavior an
interviewer expects you to diagnose.

## Lost update

Two transactions read the same value and both write a derived value. The later
write overwrites the earlier update. Prevent it with a row lock, optimistic
version column, serializable retry, or an atomic update:

```sql
UPDATE inventory
SET quantity = quantity - 1
WHERE product_id = 42 AND quantity >= 1;
```

Check the affected-row count; do not read, subtract, and write without a
concurrency policy.

## Deadlock

Transaction A locks row 1 then requests row 2. Transaction B locks row 2 then
requests row 1. The database should detect the wait cycle and abort a victim.
Applications must retry safe transactions with bounded backoff.

Prevent avoidable deadlocks by acquiring locks in a consistent order, keeping
transactions short, indexing predicates, and avoiding user/network calls while
holding locks.

## Isolation anomalies

| Anomaly | Meaning | Typical control |
|---|---|---|
| Dirty read | Read another transaction's uncommitted data | Read committed or stronger |
| Non-repeatable read | Same row changes between reads | Repeatable read or locking |
| Phantom | New matching rows appear | Predicate locks/serializable strategy |
| Write skew | Independent rows violate a cross-row invariant | Serializable or explicit locking |

Isolation names are not identical across databases; explain the actual
implementation and guarantee.

## Optimistic concurrency

Use a version column or compare-and-swap update:

```sql
UPDATE documents
SET body = :new_body, version = version + 1
WHERE document_id = :id AND version = :expected_version;
```

If zero rows are affected, another writer won. Return a conflict or retry after
merging according to the product policy.

## Interview questions

- How would you diagnose a deadlock from database logs and lock tables?
- When is serializable isolation worth its retry cost?
- Why does `SELECT ... FOR UPDATE` not solve a missing predicate index?
- How do MVCC readers avoid blocking writers, and where does version cleanup
  happen?
- How would you make a payment decrement safe under retries and duplicate
  requests?

## Cross-references

- [Transactions](../transactions/README.md)
- [Concurrency control](../transactions/concurrency-control.md)
- [Deadlocks in Operating Systems](../../os/synchronization/deadlocks/README.md)
- [Idempotency](../../backend/patterns/idempotency.md)
- [ABA and memory reclamation](../../concurrency/aba-problem.md)

## References

- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [PostgreSQL deadlock detection](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-DEADLOCKS)
