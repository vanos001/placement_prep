# Logical Rewrites: Join Elimination, Partition Pruning, and Constraint Propagation

Before the optimizer picks join orders or access paths, it rewrites the
query against *known facts* — keys, foreign keys, CHECK constraints,
NOT NULL columns, partition bounds. Each rewrite deletes work the user
asked for but provably does not need: joins to tables whose columns never
appear, partitions whose bounds exclude every predicate, predicates that
another constraint already implies. These transformations are why the same
query can be trivial on one schema and pathological on a near-identical one
— and why "add a foreign key" is a performance advice, not only an
integrity one.

The surrounding pipeline is in [Query Optimization](./optimization.md) and
[Query Optimization Deep Dive](../query-optimization-deep.md); the
statistics that drive everything downstream are in
[Cost Estimation](./cost-estimation.md).

## Join elimination: deleting a join the query still mentions

```sql
SELECT o.order_id, o.total
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id;   -- c never used!
```

If `customers.customer_id` is a primary key and `orders.customer_id` has a
declared foreign key to it, the join cannot change the row set: the FK
guarantees every order matches exactly one customer, so the join is
row-preserving and the projection doesn't need `c`. The optimizer drops the
join entirely:

```text
before:  Hash Join  (orders ⋈ customers) → 2 scans + build/probe
after:   Seq Scan on orders                            → 1 scan
```

The exact preconditions matter, and interviews probe each:

- **The FK must be declared in the catalog.** An *implicit* relationship
  the developers know about but never declared gets no elimination —
  the optimizer reasons from constraints, not intentions.
- **The join must be row-preserving.** Inner join to a PK: eliminable.
  Left join to a table whose columns are never referenced: eliminable.
  Inner join to a *unique-but-nullable* column: not eliminable (NULL FK
  semantics can lose rows). An aggregate on the outer side
  (`count(DISTINCT c.region)`) breaks it — the join changed the data.
- **No referenced output columns.** Any `c.*` in the SELECT, ORDER BY, or
  DISTINCT restores the join.

Where it works natively: SQL Server and Oracle have applied FK join
elimination for many releases; PostgreSQL performs the left-join variant
(non-referenced side elimination) but, as of current releases, does not do
FK-based elimination for inner joins — a favorite cross-engine trivia point
and the reason a "useless" FK join sometimes still appears in `EXPLAIN`.
MySQL (8.0) rewrites some `LEFT JOIN`s without WHERE conditions on the
right table into inner joins and can drop unreferenced derived tables — a
different elimination family with the same goal: fewer joins before cost
search begins.

## Constraint propagation: the optimizer's truth maintenance

Constraints are facts; propagation is deriving *new* facts from them:

- **Transitive predicates.** `WHERE a.x = b.y AND b.y = 5` becomes
  `WHERE a.x = 5 AND b.y = 5` — each scan now sees a constant that index
  seeks and partition pruning can use. Without propagation, the predicate
  exists only after the join node, too late for the access method.
- **NOT NULL and outer-join simplification.** If `o.cust_id` is NOT NULL,
  a `LEFT JOIN orders o ... WHERE o.cust_id = 5` can be rewritten to an
  *inner* join — the WHERE clause already rejected the null-extended rows
  (the inverse of the [LEFT JOIN degradation trap](../interview-problems/interview-traps.md),
  used deliberately by the optimizer).
- **CHECK-implied empty results.** `WHERE amount > 0` against a table with
  `CHECK (amount < 0)` is a constant false — the relation is known empty
  before scanning anything. In partitioned engines this generalizes to
  "no partition can contain such rows," which is the bridge to pruning.
- **Equivalence classes.** The join graph's equality classes
  (`a.x = b.y = c.z`) let a predicate on *any* member filter *all* members —
  the mechanism that makes broadcast-join and shuffle-join pushdowns in
  distributed engines (Spark, Trino) correct rather than heuristic.

This family of rewrites descends from System R's rule-based layer and its
successor architecture of *query rewrites before optimization* — the
survey reference for the whole area is
[Graefe's *Query Evaluation Techniques*](https://doi.org/10.1145/152610.152611),
whose "rewrites" chapter remains the standard catalogue (predicate
propagation, join elimination, distinct-elimination, and friends with
precise correctness conditions).

## Partition pruning: deleting partitions instead of rows

Partitioning divides a table into pieces with *declared bounds*; pruning
uses predicate-vs-bound reasoning to open only the pieces a query can
touch:

```sql
CREATE TABLE events (ts timestamptz, payload text)
PARTITION BY RANGE (ts);          -- monthly partitions

-- query touches 3 of 120 partitions:
SELECT count(*) FROM events
WHERE ts >= '2026-07-01' AND ts < '2026-08-01';
```

```text
PostgreSQL EXPLAIN:
  ->  Append
        ->  Seq Scan on events_2026_07      ← opened
        ->  Seq Scan on events_2026_08      ← opened
        (111 sibling partitions pruned away before execution)
```

Three pruning regimes, by *when* the pruning happens — the taxonomy worth
reciting in interviews:

| Regime | When | What it needs |
|---|---|---|
| Static (plan-time) | during planning | literal or parameter-bound predicates comparable to bounds |
| Initial execution-time | at executor start | parameters unknown at plan time but bound before execution (prepared statements) |
| Dynamic (per-row) | during execution | join keys driving partition choice (partition-wise join pruning) |

The classic failure: **non-comparable predicates prune nothing.**
`WHERE date_trunc('month', ts) = '2026-07-01'` or a wrapper-function
predicate cannot be matched against declared range bounds — the same
non-SARGability that kills [index usage](../interview-problems/interview-traps.md)
kills pruning, but with a bigger multiplication factor (the engine now
scans 120 partitions instead of missing one index). Cross-shard pruning in
distributed systems ([Database Sharding](../advanced/database-sharding.md))
is the same computation one level up: route by shard bounds instead of
scatter-gather — and its failure mode (functions on the shard key) is
likewise identical.

## Reading the evidence in EXPLAIN

Each rewrite leaves fingerprints:

- **Eliminated join** → the plan node disappears (a 2-table query plans as
  1-scan). If it didn't, check for the FK, for hidden references
  (`SELECT *`), and for aggregates.
- **Propagation** → index conditions appear on tables that had no literal
  predicate (`Index Cond: a.x = 5` on a table whose WHERE clause only
  mentioned `b.y`).
- **Pruning** → the plan lists only surviving partitions (PostgreSQL's
  `Append` with siblings absent); SQL Server's execution plan shows
  per-partition access counts; Oracle's `PARTITION RANGE ITERATOR` with
  pruned bounds.

When a rewrite you expected *didn't* happen, the debugging order is: catalog
facts (FK/CHECK present?), predicate comparability (function-wrapped
column?), and plan-time vs execution-time knowledge (prepared statements
with [generic plans](./plan-caching.md) can move pruning to a later regime —
a subtle interaction between this page and plan caching).

## Interview questions

1. **Why does declaring a FK you never query still help?** It is the
   provenance of join elimination: the optimizer can prove the join is
   row-preserving and delete it. No FK → no proof → the "useless" join
   executes — one of the few places where a constraint changes the *plan*,
   not just the integrity.
2. **Where exactly can pruning happen in a prepared statement?** Three
   regimes: plan-time (literals), initial-execution (bound parameters),
   and dynamic per-row (join keys). With generic plans the pruning regime
   shifts later — which is also why a prepared statement sometimes reads
   more partitions than the identical ad-hoc text.
3. **`WHERE date_trunc('month', ts) = '2026-07-01'` on a monthly-partitioned
   table — what does the plan do?** No pruning: the function-wrapped
   column is not comparable to declared bounds, so every partition is
   opened and scanned. Rewrite as a half-open range on the raw column —
   the [SARGability](../interview-problems/interview-traps.md) rule in its
   most expensive failure mode.
4. **Propagating `b.y = 5` into `a.x = 5` — what could go wrong?** Nothing
   semantically (equality classes are exact), but estimates can: the added
   predicate changes selectivity estimates on `a`, possibly switching join
   algorithms — rewrites are *plan-visible* even though they are invisible
   in the answer.

## Key Takeaways

- Rewrites delete provably-dead work before cost-based search: joins via
  FK/PK proof, partitions via bound comparison, predicates via transitive
  equality and NOT NULL/CHECK facts.
- Join elimination requires *declared* constraints and a non-referenced,
  row-preserving side; PostgreSQL (inner-join FK variant) vs SQL
  Server/Oracle is the standard engine-difference answer.
- Pruning regimes are plan-time / initial-execution / per-row; function-
  wrapped partition keys disable all three.
- Every rewrite is visible in EXPLAIN — diagnosis starts by asking "was
  the fact available to the optimizer, and was the predicate comparable?"

## Cross-References

- [Query Optimization](./optimization.md) — the full logical/physical pipeline these rewrites feed.
- [Cost Estimation](./cost-estimation.md) — statistics and selectivity under propagated predicates.
- [Plan Caching](./plan-caching.md) — generic plans and the pruning-regime shift.
- [Database Sharding](../advanced/database-sharding.md) — the distributed analogue: routing by shard bounds.
- [Composite Index](../indexing/composite-index.md) — the access-path side of the same predicates.

## References

- G. Graefe, "[Query Evaluation Techniques for Large Databases](https://doi.org/10.1145/152610.152611)", *ACM Computing Surveys* 25(2), 1993 — the canonical catalogue of logical rewrites with correctness conditions.
- PostgreSQL Documentation, "[Partition Pruning](https://www.postgresql.org/docs/current/ddl-partitioning.html#PARTITION-PRUNING)" — the three pruning regimes and executor behavior.
- Oracle Database 19c VLDB and Partitioning Guide, "[Partition Pruning](https://docs.oracle.com/en/database/oracle/oracle-database/19/vldbg/loe.html)" — pruning against declared bounds, including join pruning.
- Microsoft Learn, "[Partitioned Tables and Indexes](https://learn.microsoft.com/en-us/sql/relational-databases/partitions/partitioned-tables-and-indexes)" — partition elimination in SQL Server plans.
- MySQL 8.0 Reference Manual, "[Outer Join Simplification](https://dev.mysql.com/doc/refman/8.0/en/outer-join-simplification.html)" — the MySQL join-removal family.
