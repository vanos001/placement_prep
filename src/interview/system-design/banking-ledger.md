# Banking Ledger: A Money-Movement System That Cannot Be Wrong

A ledger is the system where "eventually consistent" is not a selling point
but a bug report. Every balance a customer sees is a *derived view*; the
source of truth is an append-only log of **postings**, and the system's
whole discipline — double-entry bookkeeping, exact arithmetic, idempotent
writes, partitioned by account, audited forever — exists to keep that
derived view reconciled with the log under failure. It is also the perfect
interview design: it forces SQL transaction semantics (write skew, gap
locks, isolation levels), idempotency, and partitioning trade-offs into one
coherent story.

Related designs: [Payment System](./payment.md) (the rails around the
ledger), [Event Sourcing deep dive](../../backend/patterns/event-sourcing-deep.md)
(the pattern the ledger embodies), and [Distributed Transactions](../../distributed/advanced/distributed-transactions.md)
(sagas, outbox, idempotency — the toolkit used here).

## The data model: accounts, entries, invariants

Double-entry bookkeeping is one invariant: **every posting debits one
account and credits another for the same amount** — money is never created
or destroyed, so the sum of all entries is identically zero and every
account's balance is a deterministic fold over its entries.

```sql
CREATE TABLE accounts (
  account_id  bigserial PRIMARY KEY,
  owner_id    bigint NOT NULL,
  currency    char(3) NOT NULL,
  opened_at   timestamptz NOT NULL
);

CREATE TABLE entries (
  entry_id     bigserial PRIMARY KEY,
  txn_group    uuid NOT NULL,          -- the business transaction id
  account_id   bigint NOT NULL REFERENCES accounts,
  amount_cents bigint NOT NULL,        -- signed: debit negative, credit positive
  currency     char(3) NOT NULL,
  idempotency_key text,                -- (txn_group, account) uniqueness
  created_at   timestamptz NOT NULL
);
CREATE INDEX ON entries (account_id, entry_id);   -- balance scan + pagination

-- The core invariant, enforced as a CHECK per posting pair is application
-- logic; the sum-zero invariant is verified by reconciliation jobs:
--   SELECT sum(amount_cents) FROM entries;   -- must be 0, always
```

Design decisions with long shadows:

- **Append-only entries, no mutable balance column.** A `balance` field
  invites lost updates (two concurrent debits read-modify-write it) and,
  worse, *reconciliation without a history*. If performance demands a
  cached balance, it is a materialized view with a documented rebuild path —
  not the truth.
- **Signed integer minor units** (cents), never floats: money arithmetic
  must be exact (`DECIMAL`/`BIGINT`); float rounding is a compliance
  incident.
- **`txn_group` ties the paired entries** so a debit without its credit is
  structurally detectable (`entries` grouped by `txn_group` must sum to
  zero *per transaction*, per currency).
- **Single currency per account.** FX is itself a pair of postings through
  an FX position account — the same zero-sum machinery, no special cases.

## Idempotency: the anti-double-spend primitive

Every transfer request arrives at least twice (client retries, gateway
retries, at-least-once queues — see
[Retry and Timeout Patterns](../../backend/patterns/retry-timeout.md)). The
ledger must make replays *harmless*, not rarer:

```sql
-- One statement, one transaction, atomic on (txn_group, account):
INSERT INTO entries (txn_group, account_id, amount_cents, currency, idempotency_key)
VALUES ($1, $2, -10000, 'USD', $1 || ':src')
ON CONFLICT (txn_group, account_id) DO NOTHING
RETURNING entry_id;
-- both legs of the transfer use the same txn_group; a replay inserts nothing
```

The idempotency key is the *intent identifier* (client-supplied request id
propagated through the API — the
[Stripe idempotency request model](https://stripe.com/docs/api/idempotent_requests)),
and the uniqueness constraint is enforced by the database, not by a
pre-check: `SELECT-then-INSERT` races two concurrent retries into two
inserts. Note what this buys against the
[exactly-once delivery illusion](../../distributed/messaging/README.md):
delivery stays at-least-once; *processing* becomes effectively-once.

## The concurrency core: holding the invariant under parallelism

Two concurrent debits must not both pass a "balance sufficient?" check —
that is a lost update. The naive check-then-debit sequence has a race, and
the fixes are exactly the isolation-level material interviews probe (see
[Isolation Levels](../../dbms/transactions/isolation-levels.md) and
[Snapshot Isolation](../../dbms/advanced/snapshot-isolation.md)):

```sql
-- Option A: lock the source account row first (pessimistic, Serializable-safe)
BEGIN;
SELECT balance_cents FROM account_balances
  WHERE account_id = $1 FOR UPDATE;      -- serializes writers per account
INSERT INTO entries ...;                  -- the debit leg
UPDATE account_balances SET balance_cents = balance_cents - 10000
  WHERE account_id = $1;
COMMIT;
```

- **Row locks serialize per account**, so hot accounts become lock
  convoys — throughput is bounded by one account's row (see
  [Lock-based Protocols](../../dbms/transactions/lock-based.md)). Queue
  hot accounts deliberately (partitioned worker, ordered queue) instead of
  pretending contention away.
- **Serializable Snapshot Isolation fixes the check-then-act race without
  explicit locks** — but the classic *write skew* example is literally two
  accounts' guards: "each transaction checks `balance >= 0` across
  *different* rows and both commit." SSI detects the rw-antidependency and
  aborts one; under plain Snapshot Isolation the ledger goes negative. This
  is *the* reason banks use serializable or explicit locking for balances —
  and the crispest interview story for "when does SI break?"
  ([Write skew coverage](../../dbms/advanced/snapshot-isolation.md)).
- **Deferred constraint checking** (available balance vs booked balance):
  production ledgers keep *two* balances — booked immediately, available
  after holds — so pending authorizations never double-spend through the
  gap between them.

## Partitioning the ledger

The entries table grows without bound; shard it by `account_id` so one
account's entries (and its balance fold) live on one shard:

- **Local (shard-keyed) transactions** — a transfer between two accounts on
  the same shard is a local ACID transaction. Fast, boring, correct.
- **Cross-shard transfers** need atomicity across shards: 2PC-backed
  distributed transactions (Spanner/CockroachDB-style — see
  [Distributed Databases](../../dbms/advanced/distributed-databases.md)),
  or an outbox + saga with compensations and a *posted-then-reconciled*
  interim state visible as "pending" (see
  [2PC](../../dbms/transactions/two-phase-commit.md) and
  [Sagas](../../dbms/transactions/saga.md)). Money systems usually
  prefer the saga: the interim state is a feature (pending payment), not a
  hack.
- **Co-locating counter-accounts** (payments vs receipts) by
  `txn_group`-hashing would make transfers local — but then *account*
  histories scatter, and the read pattern (statement per account) pays
  forever to optimize the write. The standard resolution: partition by
  account, accept occasional distributed transactions, and route
  high-frequency pairs (payroll runs) through batching.
- **Time-based tiering within a shard**: hot window (90 days) in the OLTP
  store, older entries compacted to the warehouse — balances are folds, so
  a "balance as of archive boundary" checkpoint keeps old data queryable
  without scanning history ([columnar formats](../../dbms/advanced/columnar-formats.md)
  for the archive side).

## Reading balances, statements, and audit

- **Balance reads** come from the maintained view (lock-free,
  eventually-tick-consistent with the entries), with read-your-writes
  guaranteed by reading the primary after the customer's own write or by
  sticky routing (see [Consistency Models](../../distributed/fundamentals/consistency.md)).
- **Statements** are paginated entry scans (`(account_id, entry_id)` index)
  plus a per-period opening-balance checkpoint so "last 90 days" never
  scans years.
- **Audit and reconciliation**: the append-only log + zero-sum invariant
  makes reconciliation *mechanical*: sums per `txn_group`, sums per
  currency, sum of everything = 0. Discrepancies localize to a transaction
  group, not to "somewhere in the money." Regulatory "immutable audit"
  requirements fall out of the storage discipline (append-only, no
  destructive updates, WORM archive) rather than from a bolted-on feature.

## Reliability posture

| Concern | Mechanism |
|---|---|
| No lost commits | WAL durability, synchronous replication to a quorum before commit (see [WAL Internals](../../dbms/advanced/wal-internals.md)) |
| No double-spend on retry | Idempotency key uniqueness at the database |
| No negative balances under concurrency | Serializable isolation or per-account row locks (write-skew-aware) |
| Region loss | RPO 0 across regions (sync replication), RTO minutes via leader failover — see [Multi-Region](../../sre/multi-region.md) |
| Quiet corruption | Continuous reconciliation (sum-to-zero) + checksum sweeps |
| Backpressure | Per-account serialization gives natural isolation; [bulkheads](../../sre/bulkheads.md) per tenant class |

## Interview questions

1. **Why double-entry instead of a per-account balance?** The zero-sum
   invariant makes loss/corruption *detectable* (reconciliation is a SUM),
   makes every state change attributable (audit), and gives one uniform
   model for FX, fees, and reversals. A mutable balance column has no
   invariant to check and no history to rebuild from.
2. **Two accounts, one on each shard — walk the transfer.** Saga with
   outbox: reserve (hold) on source, post on destination, then finalize or
   compensate the reserve; interim "pending" is customer-visible; the
   outbox pattern guarantees the events exist despite local-commit
   boundaries; idempotency keys make retries safe at every hop.
3. **Where does snapshot isolation break a ledger?** Write skew: two
   concurrent overdraft-guarded debits on *different* accounts each read
   "fine," both commit, the invariant (never negative) is violated — SI
   only prevents write-write conflicts on the same rows. Fix: serializable
   (SSI) or explicit per-account locks, which is why balance paths are
   kept serialization-critical and small.
4. **How do you support "show my balance in real time" at read scale?**
   Replica reads break read-your-writes after the customer's own payment.
   Options: read the leader for self-writes (session-aware routing),
   or serve lagged balances with a consistent "as-of" timestamp. What is
   *not* acceptable is silently mixing both — stale-read semantics must be
   a product decision ([stale reads](../../dbms/interview-problems/interview-traps.md)).

## Key Takeaways

- Append-only double-entry postings are the truth; balances are derived
  views with documented rebuilds — the sum-to-zero invariant is the
  system's self-audit.
- Idempotency keys enforced by database uniqueness (not pre-checks) turn
  at-least-once delivery into effectively-once money movement.
- The overdraft race is write skew under snapshot isolation; the answer is
  serializable execution or per-account locking on a deliberately narrow
  critical path.
- Partition by account, accept cross-shard transfers as explicit sagas
  with visible pending states, and keep reconciliation mechanical.

## Cross-References

- [Payment System](./payment.md) — gateway, authorization, and settlement around the ledger.
- [Snapshot Isolation](../../dbms/advanced/snapshot-isolation.md) — write skew and SSI in depth.
- [Two-Phase Commit](../../dbms/transactions/two-phase-commit.md) and [Saga Pattern](../../dbms/transactions/saga.md) — cross-shard transfer strategies.
- [Event Sourcing Deep Dive](../../backend/patterns/event-sourcing-deep.md) — append-only state-machine modeling.
- [Distributed Transactions](../../distributed/advanced/distributed-transactions.md) — outbox, idempotency, exactly-once semantics.
- [WAL Internals](../../dbms/advanced/wal-internals.md) — the durability substrate.

## References

- Stripe API Documentation, "[Idempotent Requests](https://stripe.com/docs/api/idempotent_requests)" — the canonical public design for client-supplied idempotency keys and replay semantics.
- Martin Fowler, "[Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)" — append-only event state as the system of record.
- Microsoft Azure Architecture Center, "[Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)" — guarantees and trade-offs of append-only stores.
- M. Kleppmann, *Designing Data-Intensive Applications*, O'Reilly, 2017, Chapters 7 and 9 — write-skew mechanics, exactly-once processing limits, and audit-friendly log designs.
