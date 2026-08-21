# TCC (Try-Confirm-Cancel) Transactions

TCC is a compensation-based distributed transaction pattern, an alternative to two-phase commit (2PC) for microservice architectures. It was originally described by Pat Helland in 2007 and refined by the Alibaba Seata team in 2019. TCC replaces the 2PC's resource locks with **business-level compensation**: each service implements a Try, Confirm, and Cancel operation, and a coordinator orchestrates them across services. This page covers the protocol, the failure modes, and when TCC is preferable to Saga or 2PC.

## Why TCC Exists

2PC holds resource locks (e.g., row locks in a database) during the prepare phase. If the coordinator fails between prepare and commit, the locks are held for minutes until the transaction is resolved. In a microservice architecture where one transaction may span 5-10 services, this is unacceptable:

- The probability of a coordinator failure scales with the number of services involved.
- Lock contention cascades: if service A holds a lock on row R for 5 minutes, every other transaction that touches R also waits.

TCC eliminates the long-held locks by moving the "prepare" step into business logic: each service implements a Try operation that reserves the resource without committing it (e.g., "reserve $100 in the wallet's `reserved_balance` column, not the actual `balance`").

## The Protocol

Three operations per service:

- **Try**: Reserve the resource (e.g., deduct from `available_balance`, add to `reserved_balance`).
- **Confirm**: Commit the reservation (e.g., deduct from `reserved_balance`).
- **Cancel**: Roll back the reservation (e.g., add back to `available_balance`, deduct from `reserved_balance`).

```text
Transaction coordinator:
  1. Try(Service A) → reserve $100 in A
  2. Try(Service B) → reserve item X in B
  3. Try(Service C) → reserve shipping slot in C
  4. If all Try succeeded:
       Confirm(A), Confirm(B), Confirm(C)
  5. If any Try failed:
       Cancel(A), Cancel(B), Cancel(C)
```

The key difference from 2PC: the "reserved" state is visible to other transactions, but it's not yet "committed". Other transactions that try to reserve the same resource see the reservation and may either wait, fail, or proceed with a different resource.

## Implementation Patterns

### Pattern 1: Separate "reserved" column

The most common pattern: a database table has both an `available` and a `reserved` column.

```sql
-- Try
UPDATE accounts SET balance = balance - 100, reserved = reserved + 100 WHERE id = 42;
-- Confirm
UPDATE accounts SET reserved = reserved - 100 WHERE id = 42;
-- Cancel
UPDATE accounts SET balance = balance + 100, reserved = reserved - 100 WHERE id = 42;
```

Each operation is a single SQL statement (atomic). The TCC coordinator sends Try to all participants; if all succeed, it sends Confirm; if any fails, it sends Cancel.

### Pattern 2: Pending records

For resources that don't fit a counter (e.g., a seat in a flight), use a pending-records table:

```sql
-- Try
INSERT INTO pending_seats (txn_id, seat_id, flight_id) VALUES (T0, S42, F100);

-- Confirm
INSERT INTO seats (seat_id, flight_id, holder_id) VALUES (S42, F100, user);
DELETE FROM pending_seats WHERE txn_id = T0;

-- Cancel
DELETE FROM pending_seats WHERE txn_id = T0;
```

### Pattern 3: Saga-style compensation

For long-running transactions (e.g., shipping an order that takes hours), the Confirm step may be replaced by an async job that performs the actual work later. The Try step reserves; the Confirm step enqueues a job; the Cancel step releases the reservation.

## Coordinator Failure Modes

The coordinator must record its decisions durably before sending Try/Confirm/Cancel messages. If the coordinator crashes:

- **After Try, before Confirm**: Coordinator must send Cancel to all participants.
- **After Confirm started, before complete**: Coordinator must retry Confirm to participants that didn't ack.
- **After Cancel started, before complete**: Coordinator must retry Cancel.

Each participant must be **idempotent**: Confirm and Cancel can be called multiple times safely. The standard implementation is to track transaction state per participant and skip duplicates:

```python
def confirm(txn_id):
    state = get_txn_state(txn_id)
    if state == "TRIED":
        do_confirm()
        set_txn_state(txn_id, "CONFIRMED")
    elif state == "CONFIRMED":
        return  # idempotent skip
    elif state == "CANCELLED":
        raise InvalidState("Cannot confirm cancelled transaction")
```

## Comparison to Saga and 2PC

| Aspect | TCC | Saga | 2PC |
|--------|-----|------|-----|
| Lock duration | Whole transaction (business lock) | None (compensation runs after failure) | Whole transaction (resource lock) |
| Isolation | Strong (reservations visible) | Weak (no isolation between steps) | Strong (resource locks) |
| Failure recovery | Synchronous Cancel | Async compensation | Coordinator recovery (complex) |
| Best for | Short transactions, strong consistency needed | Long workflows, eventual consistency | Single-database, short transactions |
| Implementation cost | High (each service has Try/Confirm/Cancel) | Medium (compensation logic) | Low (DB-native) |
| Performance | Medium (extra round-trips for Try/Confirm) | High (no extra round-trips) | Low (locks held) |

## When to Use TCC

TCC is best for:
- **Microservices that need strong isolation** between the reservation and commit steps (e.g., inventory management where over-selling is unacceptable).
- **Short transactions** (seconds, not hours) where the cost of Try/Confirm/Cancel is acceptable.
- **High-throughput workloads** where 2PC's lock contention is the bottleneck.

TCC is bad for:
- **Long-running workflows** (e.g., order fulfillment that takes days): the Try reservations would hold business state for days, blocking other operations.
- **Read-mostly workloads**: TCC's overhead is per-transaction; a workload with many reads doesn't benefit.
- **Resources that can't be reserved** (e.g., external APIs that don't expose Try semantics).

## Production Implementations

- **Seata** (Alibaba): the most widely-used open-source TCC framework, especially in Chinese e-commerce (Alibaba, JD, Meituan).
- **DTM** (a Go-based distributed transaction manager): supports TCC, Saga, 2PC, and other patterns.
- **Custom implementations**: many companies build their own TCC coordinators on top of RabbitMQ/Kafka for the Try/Confirm/Cancel messaging.

## Common Pitfalls

1. **Forgetting to make Confirm/Cancel idempotent.** The coordinator may retry these operations. If they're not idempotent, retries will double-charge or double-credit.

2. **Holding Try reservations too long.** A transaction that takes 10 minutes to complete holds all Try reservations for 10 minutes, blocking other transactions. Set a Try reservation timeout (e.g., 30 seconds) and roll back stale reservations.

3. **Mixing TCC with non-TCC transactions.** A TCC transaction that touches a service that doesn't support Try/Confirm/Cancel breaks the model. Either all services in a transaction support TCC, or none should.

4. **Forgetting the "TRIED" state on failure.** If Try succeeds but the coordinator crashes before recording the state, the recovery logic doesn't know whether to Confirm or Cancel. Always persist the state in the same transaction as the Try operation.

5. **Network partitions during Confirm.** If the network partitions between the coordinator and some participants during Confirm, the transaction is left half-confirmed. The coordinator must retry Confirm indefinitely until all participants ack.

6. **Compensation order matters.** If Service A's Confirm depends on Service B's Confirm having completed (e.g., B creates a record that A references), the order must be controlled. TCC's "Confirm all in parallel" model doesn't support ordering; either serialize Confirms or design services to be order-independent.

## References

- Pat Helland, "[Life beyond Distributed Transactions](https://dl.acm.org/doi/10.1145/1229185.1229528)" (2007, CIDR)
- [Seata TCC documentation](https://seata.io/en-us/docs/dev/user/tcc.html)
- [DTM (Go distributed transaction manager)](https://en.dtm.pub/)
- "[Try-Confirm-Cancel: An Investigation into Distributed Transactions](https://martinfowler.com/articles/patterns-of-distributed-systems/tcc.html)" (Martin Fowler)
- [Alibaba Seata TCC source](https://github.com/seata/seata)
- [DTM TCC implementation](https://github.com/dtm-labs/dtm)
- [TCC vs Saga vs 2PC (DTM blog)](https://en.dtm.pub/appanomaly/tcc-vs-saga/)
