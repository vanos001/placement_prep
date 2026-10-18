# Database Choices: Normalization vs Denormalization, Index Structures, Optimistic vs Pessimistic Concurrency

## Overview

Database design questions come in trios: how to shape the schema (normalization), how to access it fast (index structure), and how to let writers coexist (concurrency control). Each is routinely answered with a slogan — "always normalize", "always index", "MVCC is modern" — and each slogan is wrong at some scale. This page runs the [handbook framework](./index.md) three times, keeping the quick-reference tables in [Database Trade-offs](../../trade-offs/database-tradeoffs.md) as the summary layer and going mechanism-deep here.

## Comparison A: Normalization vs Denormalization

### Mechanisms

**Normalization** decomposes tables so that every non-key fact is stored exactly once, eliminating redundancy by functional-dependency analysis (3NF and BCNF — see [3NF](../../dbms/normalization/3nf.md) and [BCNF](../../dbms/normalization/bcnf.md)). Each fact lives in one row of one table; consistency is structural, enforced by keys. **Denormalization** reintroduces redundancy deliberately: copying values into parent tables (wide rows), collapsing joins into one table, or restructuring into read-shaped forms (star schemas: a central fact table joined to dimension tables — see [denormalization](../../dbms/normalization/denormalization.md)). The mechanisms are mirror images: normalization spends *read-time joins* to save *write-time fan-out*; denormalization spends *write-time fan-out* to save *read-time joins*.

### The concrete example

Take an orders table that stores `customer_city` directly on each order row (denormalized):

- **Update anomaly**: a customer moves — you must update every order row for that customer. Miss one and the database now disagrees with itself, permanently and silently.
- **Delete anomaly**: delete a customer's last order and their address vanishes from the system.
- **Insert anomaly**: you cannot record a new customer without inventing an order row for them.

The 3NF version — `orders(customer_id, …)` plus `customers(customer_id, city, …)` — fixes all three anomalies: one row to update, history preserved, customers exist independently. The cost is exact and predictable: every "orders joined with city" query now performs a join, and the planner must choose an index or hash join to execute it.

### Join amplification vs read amplification — and when denormalization becomes mandatory

At modest scale, normalization wins: joins on indexed keys are cheap, and single-source-of-truth integrity is worth more than microseconds. The reversal happens through several distinct mechanisms, and knowing which one you are fighting determines the fix:

- **Join latency at read scale.** A dashboard joining six tables to render one row pays six index probes per row and planner risk. A star schema pays one fact scan plus bitmap-filters on dimensions — this is *why OLAP warehouses are denormalized by design*.
- **Replicas cannot fix it.** Read replicas parallelize reads but execute the *same joins*. If the query itself is the bottleneck, scaling out reads multiplies its cost — the point where teams denormalize into a read model (CQRS), a materialized view (PostgreSQL: `MATERIALIZED VIEW` + periodic `REFRESH` — note it is not incremental by default), or a search/document index.
- **Write fan-out is the denormalizer's tax.** Every copy of `customer_city` must be updated on every change. Maintenance mechanisms, in increasing sophistication: application-level updates (dangerous — see below), triggers, or change-data-capture pipelines (Debezium streaming the write to project the read model — see [Debezium](../../data-engineering/debezium.md)).
- **Dual-write is the classic bug.** "Update table A, then update table B" from application code has no atomicity: a crash between the two writes leaves copies diverging silently. Denormalization is only safe when the redundancy is maintained by one transaction, one trigger, or one CDC pipeline — not by two unrelated UPDATE statements.

### Edge cases and counterexamples

- **Denormalize too early** and update logic diverges: the first time city changes, five tables must agree, and the bug reports arrive months later as "stale data" — which no one can trace to the schema decision. The honest rule: normalize until a *measured* read-path problem exists, then denormalize the specific read path.
- **Normalization can also go too far**: BCNF decomposition that splits attributes no longer queried separately turns every trivial screen into a five-way join; the theoretical ideal and the workload can genuinely disagree, and the principled escape is a denormalized projection on top of a normalized core — not abandoning normalization in the core OLTP schema.

## Comparison B: B-tree vs Hash vs LSM vs GiST/GIN

### Mechanisms

| Structure | Mechanism | Point lookup | Range/order | Write behavior | Space |
|-----------|-----------|--------------|-------------|----------------|-------|
| **B-tree/B+-tree** (Bayer & McCreight, 1972) | Balanced, high-fan-out pages updated in place; leaves chain for scans ([B-tree index](../../dbms/indexing/b-tree.md)) | O(log n), few page touches | **Native** | In-place page updates + WAL; page splits/merges | Fragmentation slack |
| **Hash index** | Hash key → bucket; chain/probe on collision ([hash index](../../dbms/indexing/hash-index.md)) | O(1)-ish, exact match only | **None** | Cheap tuple insert | Compact |
| **LSM-tree** (O'Neil et al., 1996) | Append to memtable; flush to immutable SSTables; background compaction merges levels ([LSM trees](../../dbms/internals/lsm-trees.md)) | O(levels) with bloom filters, else slow | Range scans read many runs | **Append-only**; compaction amortizes | Good (compression), + tombstones |
| **GiST** (Hellerstein et al., VLDB 1995) | Extensible balanced tree with a per-type `consistent` predicate — a *framework* for ordering anything that supports overlap checks ([GiST](../../dbms/indexing/gist.md)) | Predicate-based | Domain-specific (containment, overlap, kNN) | Page splits on overlap | Moderate |
| **GIN** (inverted index) | Element → posting-list map ([GIN](../../dbms/indexing/gin.md)) | Fast containment ("key ∈ array", full-text match) | No ordering | Expensive updates; pending-list batching | Large posting lists |
| **Bitmap** ([bitmap index](../../dbms/indexing/bitmap-index.md)) | Bit per row per key value; bitwise AND/OR | Low-cardinality analytics predicates | Value-range via bit ranges | Catastrophic for updates (bit per row) | Tiny per value |

### Amplification is the real scoreboard

- **Write amplification.** B-tree: one logical update writes a page image to WAL (and the page again on checkpoint) — bounded and predictable. LSM: the same update is written to WAL, memtable, level-0 flush, then rewritten by every compaction level it descends — RocksDB-style leveled compaction typically multiplies writes by a factor of ~10 or more; that is the *price of append-only*. Hash/GIN: cheap per write but GIN's posting lists can batch into pending-list flush storms under bulk load.
- **Read amplification.** B-tree: ~3–4 page reads even at billions of rows (high fan-out). LSM: check memtable + every level; a *negative* lookup (key absent) without a bloom filter touches every run — bloom filters are not an optimization here, they are the mechanism that makes LSM reads possible. Hash: one probe, best in class. GIN: one posting-list fetch, then intersection.
- **Space amplification.** LSM keeps expired/duplicated versions until compaction; B-trees keep page slack; GIN posting lists grow with cardinality. LSM usually wins on-disk footprint via compression of immutable runs.

### Edge cases and counterexamples

- **PostgreSQL hash indexes cannot enforce UNIQUE** — only B-trees can ([PostgreSQL index types](https://www.postgresql.org/docs/current/indexes-types.html)); and a "hash index" inside InnoDB is not something you create at all: InnoDB's *adaptive* hash index builds hash shortcuts for hot B-tree pages automatically ([MySQL InnoDB](https://dev.mysql.com/doc/refman/8.0/en/innodb-index-types.html)). The lesson: in databases, "hash vs B-tree" is rarely a user choice — B-tree plus adaptive shortcuts dominates because point lookups are rarely the *only* access path a table needs.
- **LSM without bloom filters**: a key-not-exists scan checks every SSTable; a workload with many absent-key lookups (cache-miss-heavy) can make an LSM slower than the B-tree it replaced. Check the bloom-filter false-positive rate before blaming the engine.
- **GIN under high update rate**: each array-valued row update touches many posting lists; the pending list defers this, but flushing it serializes bulk loads. Workload-fit rule: GIN for read-heavy containment, not for churn-heavy array writes.
- **GiST vs GIN confusion**: both index composite/complex data; GiST generalizes lossy predicates (nearest-neighbor, ranges), GIN is exact inverted membership. Choosing by "which is newer" instead of by predicate type produces indexes the planner cannot use for the actual query shape.

## Comparison C: Optimistic vs Pessimistic Concurrency Control

### Mechanisms

**Pessimistic (2PL)**: take locks before touching rows; conflicting transactions *block*; deadlock detection/prevention arbitrates cycles ([lock-based](../../dbms/transactions/lock-based.md)). **Optimistic/MVCC** (Kung & Robinson, 1981): readers see snapshots — writers create new versions (PostgreSQL's xmin/xmax — see [PostgreSQL MVCC deep dive](../../dbms/internals/postgresql-mvcc-deep.md)); conflicts surface at commit as serialization failures to be *retried* ([optimistic](../../dbms/transactions/optimistic.md), [MVCC](../../dbms/transactions/mvcc.md)). MVCC's signature guarantee: readers never block writers and vice versa. Its signature failure mode: under contention, work is *wasted* — a transaction that runs 200 ms and fails validation did 200 ms of CPU for nothing, and retry storms can convert contention into livelock without exponential backoff + jitter.

### The contention decision rule

Optimistic control wins when conflicts are rare: no lock-manager overhead, no deadlocks, and full read throughput from snapshots. Pessimistic wins when conflicts are frequent: blocking *caps* the wasted work (you never run a transaction that cannot commit), while optimistic control's cost scales with conflict rate × transaction length. The rule of thumb: **estimate the probability that two concurrent transactions touch the same rows; above a few percent, or with long transactions over hot rows, pessimistic locking or explicit queueing beats retry-on-commit.**

### Two counterexamples every interviewer knows

- **Hot-row collapse (optimistic loses).** A single counter/stock row updated by hundreds of concurrent transactions: every optimistic transaction reads, computes, and fails validation against the winner. Retry storms burn CPU; throughput *drops* as concurrency rises. Mitigations: `SELECT … FOR UPDATE` (pessimistic) to serialize deliberately, shard the counter into buckets and sum, or move the hot increment out of the transactional path entirely (Redis `INCR` / queue-and-aggregate — see [backpressure](../connection-atlas/backpressure.md)).
- **Write skew (the guarantee gap).** Two on-call doctors each see "at least one doctor on call", and each removes themselves. Under snapshot isolation — the default repeatable-read of PostgreSQL — both commits succeed and *no one is on call*: each transaction's reads stayed true individually, but the pair's interleaving broke the invariant (Berenson et al., "A Critique of ANSI SQL Isolation Levels", 1995). Pessimistic `SELECT … FOR UPDATE` on the doctors table prevents it by blocking the concurrent read-set; optimistic MVCC prevents it only at full serializable (PostgreSQL's SSI detects the read-write cycle and aborts one). "MVCC" alone is not a safety guarantee — the *isolation level* is (see [isolation levels](../../dbms/transactions/isolation-levels.md) and the [database-isolation assumptions](../assumptions-hunt/database-isolation.md) page).

### When each wins

| Condition | Choose |
|-----------|--------|
| Read-dominated, conflicts rare, interactive transactions | Optimistic/MVCC (the OLTP default for good reason) |
| Hot rows, high write contention, short critical sections | Pessimistic row locks (bounded waste) |
| Cross-row invariants ("at least one…") | Serializable (SSI) or explicit locks on the read set |
| Cross-service invariants | Not locks at all — sagas/compensation ([distributed transactions](../../dbms/transactions/distributed.md)) |

## Decision Framework

1. **Schema**: normalize the OLTP core until a *measured* read path hurts; denormalize that path via materialized view, read model, or CDC projection — maintained by one mechanism, never dual writes.
2. **Analytics shape**: star schema over a fact table; do not reuse the OLTP schema for warehouse queries.
3. **Index structure**: order/range needs → B-tree; exact-match-only key-value → hash (mind uniqueness support); ingest-heavy + point/range reads → LSM (verify bloom filters); containment/overlap/NN predicates → GiST or GIN by predicate type; low-cardinality analytics predicates → bitmap.
4. **Concurrency**: measure conflict probability first; rare → MVCC + retries with backoff; hot rows → pessimistic locks or move the increment out of the transactional path; invariants spanning rows → serializable or explicit read-set locking.

## Interview Questions

1. **"Normalize everything" — name the workload where that is actively wrong.** OLAP: a dashboard joining six tables per row pays join amplification on every render, and read replicas only parallelize the same joins. The star schema exists because analytics reads facts-by-dimension, and denormalization there is a design requirement, not laziness.
2. **Why can't a read replica fix a slow join-heavy query?** Replicas execute identical query plans — they scale *concurrency*, not *per-query cost*. If the join is the bottleneck, you need a different data shape (denormalized read model/materialized view), not more copies of the same shape.
3. **A team replaces a B-tree-backed table with an LSM engine "because LSM writes are O(1)". What do they owe the workload in return?** Read amplification: every read checks memtable plus multiple SSTable levels, and absent-key lookups depend on bloom filters; plus space amplification until compaction catches up, and compaction CPU that competes with foreground traffic at the worst times. LSM trades predictable reads for write throughput.
4. **Why is "MVCC" not an answer to write skew?** MVCC is a versioning mechanism; the guarantee comes from the isolation level. Snapshot isolation permits write skew (each transaction's reads stay valid; the interleaving violates the cross-row invariant). You need serializable (SSI detects the read-write cycle) or pessimistic locks covering the read set.
5. **Hundreds of transactions update one counter row and optimistic retries make things worse. Walk the fix.** The row is a serialization point: every retry re-runs a transaction that will conflict again. Options in order: `SELECT FOR UPDATE` to make waiting explicit and bounded; shard the counter (N buckets, sum on read); or remove the increment from the transactional path (atomic INCR in a KV store, or queue-and-aggregate) — trading immediate consistency of the counter for throughput.

## Key Takeaways

- Normalization buys structural consistency for write-time; denormalization buys read-shape for write fan-out. The maintenance mechanism (transaction, trigger, or CDC) is part of the design — dual writes are a bug, not a strategy.
- Index choice is workload-fit, not fashion: B-tree for order + point, hash for exact-match-only (with uniqueness caveats), LSM for write-heavy ingest (with read amplification and bloom-filter dependency), GiST/GIN for predicate-shaped data, bitmap for low-cardinality analytics.
- The amplification trinity — read, write, space — compares structures honestly; every structure shifts cost to a different cell.
- Optimistic control's cost scales with conflict rate × transaction length; pessimistic control caps wasted work at the price of blocking. Measure contention before choosing — hot rows and write skew are the two canonical reversals.
- MVCC is a mechanism, serializability is a guarantee; interviewers probe exactly that distinction.

## Cross-References

- [Indexing Strategy](../../dbms/indexing-strategy.md) — the practical SQL-level guide to choosing indexes.
- [Normalization section](../../dbms/normalization/README.md) — 1NF through 5NF mechanics behind Comparison A.
- [Denormalization](../../dbms/normalization/denormalization.md) — the deliberate-redundancy patterns in detail.
- [B-tree](../../dbms/indexing/b-tree.md) / [B+ Tree](../../dbms/indexing/b-plus-tree.md) — page mechanics and split behavior.
- [LSM Trees](../../dbms/internals/lsm-trees.md) and [Compaction](../../dbms/internals/compaction.md) — write amplification made concrete.
- [GiST](../../dbms/indexing/gist.md) and [GIN](../../dbms/indexing/gin.md) — the extensible-framework and inverted-index designs.
- [MVCC](../../dbms/transactions/mvcc.md), [Optimistic](../../dbms/transactions/optimistic.md), [Lock-Based](../../dbms/transactions/lock-based.md), [Isolation Levels](../../dbms/transactions/isolation-levels.md) — the concurrency-control toolbox.
- [PostgreSQL MVCC Deep Dive](../../dbms/internals/postgresql-mvcc-deep.md) — xmin/xmax mechanics end to end.
- [DB Indexes: Connection Atlas](../connection-atlas/db-indexes-data-structures.md) — the dependency-web view of index structures.
- [Database Isolation: Assumptions Hunt](../assumptions-hunt/database-isolation.md) — the implicit isolation assumptions behind application code.
- [Database Trade-offs](../../trade-offs/database-tradeoffs.md) — quick-reference tables for all three comparisons.
- [Caching & Distributed](./caching-distributed.md) — sibling page: what the database's guarantees cost at the system boundary.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
