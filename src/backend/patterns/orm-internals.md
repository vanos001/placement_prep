# ORM Internals: Identity Map, Unit of Work, and the N+1 Problem

An object-relational mapper is a local transactional cache with opinions:
it maps tables to classes and rows to objects, buffers your changes until
you commit, and decides — sometimes wrongly — *which* queries to send. The
interview material that survives contact with production is not
annotations; it is the three machines inside every serious ORM (SQLAlchemy,
Hibernate/JPA, Django ORM, Entity Framework): the **identity map** (one row,
one object, per session), the **unit of work** (track dirty objects, write
them in a correct order at flush), and the **fetch strategy** (lazy, eager,
batch — where N+1 lives).

The LLD skills exercised here — ownership, lifecycle, caching, and API
evolution — are the same ones in [Cache LLD](../../interview/system-design/lld/cache-lld.md)
and [Connection Pool](../../backend/patterns/connection-pool-deep.md); the
SQL-side costs show up in [Correlated Subqueries](../../dbms/sql/correlated-subqueries.md)
and [Composite Index](../../dbms/indexing/composite-index.md).

## The session: scope of every guarantee

A session (Hibernate `Session`, JPA `EntityManager`, SQLAlchemy `Session`,
Django's per-request context) owns:

- one **connection** (or borrow window) from the pool;
- one **identity map** — the first-level cache;
- one **unit of work** — the pending insert/update/delete set;
- one **flush boundary** — when buffered changes become SQL.

Everything surprising about ORMs is a consequence of this scope. Two
sessions loading the same row produce two distinct Java/Python objects —
the identity map is per-session, *not* global. A "stale" object read in a
long session is stale *because the session's cache is older than the
transaction snapshot*, and detaching an object (session closed) removes
its dirty-tracking proxies — the "LazyInitializationException" family is a
lifecycle bug, not a mapping bug.

## Identity map: the first-level cache

```text
load("User", 42):
  if 42 in identity_map["users"]:  return cached object   -- no SQL
  row = SELECT ... WHERE id = 42
  object = instantiate + link proxies
  identity_map["users"][42] = object
  return object
```

What it buys:

- **Reference identity**: `a.user is b.user` when both relations point to
  the same row — without this, in-memory object graphs lie (two objects
  for one row, each with its own dirty state).
- **Read-your-writes within the session**: a write followed by a load
  returns the in-memory object, no repeat query.
- **The hygiene burden**: long-lived sessions accumulate every loaded
  object — memory growth *and* staleness. Web-request-scoped sessions are
  the standard policy precisely to bound both; batch jobs that "leak"
  objects per row are the standard incident (detach or clear periodically:
  `session.clear()` / `entityManager.clear()` / `detach()`).

A second-level cache (Hibernate L2, shared across sessions) is a different
beast — a distributed-consistency decision, not a given: it reintroduces
stale reads across nodes and invalidation traffic, i.e. the
[cache-aside problems](../../dbms/caching/advanced-caching.md) wearing ORM
clothing. Treat "turn on L2 caching" as a design review topic, not a flag.

## Unit of work: write buffering and flush order

Writes don't go to the database when you mutate an object; they go to the
unit of work, which decides *what* to write and *in what order* at flush
time:

```text
flush():
  1. insert  new entities   (in dependency order — FKs must resolve)
  2. update  dirty entities (diffed via dirty tracking)
  3. delete  removed entities (children before parents — FKs must not block)
  4. constrain: no insert may violate a FK the ORM is about to satisfy
     by a *later* insert in the same unit → topological sort of pending ops
```

Mechanics worth knowing at interview depth:

- **Dirty tracking** costs a diff. Load-time snapshots (Hibernate's default
  byte-code/proxy approach) or property-set marks (SQLAlchemy attributes
  flag themselves) trade memory or CPU — and a *modified-but-equal* value
  still marks dirty in naive implementations ("updated_at changed even
  though nothing did" is a real ORM ticket genre).
- **Flush ≠ commit.** Flush emits SQL within the transaction; commit ends
  it. Auto-flush-before-query exists so queries see pending changes
  (mode `AUTO`) — and *query-triggered flushes* inside batch loops are a
  classic performance cliff.
- **Write ordering vs deadlock ordering.** The unit of work's topological
  flush order is per-session; two concurrent sessions flushing overlapping
  entity graphs can lock rows in different orders —
  [deadlock](../../dbms/transactions/lock-based.md) between ORMs that
  neither team can see in their own code. Consistent flush order plus
  consistent lock ordering across services is a coordinated design
  decision.
- **Optimistic locking (`@Version`)** is the unit of work's conflict
  detector: flush adds `WHERE version = ?` to the UPDATE; zero rows
  updated → `OptimisticLockException` → merge-and-retry at the
  application. This is [OCC](../../dbms/transactions/optimistic.md) with
  the version column as the fencing token, and it is the right default for
  ORM workloads that cannot hold pessimistic locks across a request.

## Lazy loading and the N+1 problem

Lazy associations proxy themselves; first touch fires a query — per
association instance:

```python
# orders = session.query(Order).all()          -- 1 query for orders
for o in orders:
    print(o.customer.name)                     -- 1 query PER ORDER  → N+1
```

The fix spectrum, and when each applies:

| Strategy | SQL shape | Use when |
|---|---|---|
| Eager join (`JOIN FETCH`, `joinedload`) | one query, join fan-out | child cardinality ≈ 1; note result-set multiplication for 1→many |
| `selectin` / `IN` batch | 1 + k queries, no fan-out | 1→many batches (k = distinct parent sets) — the default modern answer |
| Subquery load | correlated subquery per batch | complex parent filters |
| Entity-graph / fetch-join hints | per-call override of mapped default | API-specific read shapes |

The non-obvious traps:

- **Cartesian explosion**: eager-loading two independent 1→many
  associations with joins multiplies rows (orders × line-items ×
  payments); the ORM "works" but ships M×N rows. `selectin` exists for
  exactly this case.
- **Unbounded collections**: a lazy 1→many that is always fully traversed
  should not be lazy — or mapped; windowed child reads beat object graphs
  at data scale.
- **Detached + lazy** = the runtime error family; the fix is fetch
  strategy at the query boundary (fetch joins in the repository), not
  "open session in view" — the anti-pattern that keeps sessions open for
  the whole HTTP render, coupling DB connection lifetime to view
  rendering (and to [connection pool sizing](../../backend/patterns/connection-pool-deep.md)
  pressure).

The migration-side cousin of this problem — per-row subqueries in batch
pipelines — is documented from the database side in
[Correlated Subqueries](../../dbms/sql/correlated-subqueries.md): same
plan shape, same fix (batch the keys, one query per set).

## Session/cache lifecycle: the LLD checklist

Designing services around an ORM means designing the session lifecycle:

1. **Scope**: one session per request (or per message); never per entity,
   never global. Batch jobs: periodic clear + periodic transaction
   boundaries.
2. **Transactions vs sessions**: session ≠ transaction; long sessions
   across user-think-time hold pool slots and (in non-MVCC DBs) locks —
   the [long-transaction](../../dbms/advanced/mvcc-internals.md) failure.
3. **Bulk operations bypass the unit of work**: `UPDATE ... WHERE ...`
   bulk statements skip dirty tracking and identity-map updates —
   document the invariant "after a bulk op, refresh or clear the session."
4. **Identity-map size** is an operational metric for long-lived sessions
   (Hibernate: `SessionStatistics`); growth without flush/detach is a
   leak with a query-shaped name.
5. **API evolution**: mapping changes (adding a lazy association,
   renaming a table) are *API* changes for every caller of the model —
   version read models, keep write models private. The
   [abstraction trade-offs](../../interview/system-design/lld/abstraction-interfaces.md)
   page covers the general principle; ORMs are its most-felt case.

## Interview questions

1. **Why is the identity map per-session rather than global?** Global
   object identity across sessions needs distributed invalidation and
   reintroduces cross-transaction staleness into in-memory state — the
   first-level cache is deliberately scoped to the transaction boundary.
   Global caching is the opt-in second-level cache with its own
   consistency budget.
2. **What exactly does flush do that commit doesn't?** Flush emits ordered
   SQL inside the open transaction (and may be triggered by queries);
   commit ends the transaction. Auto-flash-on-query is the default that
   hides both from newcomers — and the reason a SELECT inside a loop is
   slow.
3. **How would you eliminate N+1 in a service you inherit?** Measure first
   (query count per request), then choose per relation: `selectin` for
   1→many (avoiding join fan-out), join-fetch for many→1, entity-graph
   hints per endpoint; forbid open-session-in-view; add a query-count
   budget to the test suite so the fix sticks.
4. **`@Version` threw on a hot row — options?** Retry with backoff at the
   use-case boundary (merge-and-retry), or segment the contention
   (sub-entities, queue-per-key serialization). Escalating to pessimistic
   locks is a last resort because it converts conflict rate into hold
   time — the [convoy](../../concurrency/lock-starvation.md) trade.

## Key Takeaways

- ORM = identity map (one row → one object per session) + unit of work
  (ordered write buffering at flush) + fetch strategy — all scoped to the
  session, which is why session lifecycle *is* the design.
- Flush ≠ commit; auto-flush makes SELECTs emit UPDATEs; flush ordering
  interacts with lock ordering across services — coordinate it.
- N+1 is a fetch-strategy bug with a per-relation fix (`selectin` for
  1→many, join-fetch for many→1); open-session-in-view hides the symptom
  and couples DB lifetime to rendering.
- `@Version` = OCC with a fencing column; bulk statements bypass the unit
  of work and demand explicit session refresh policies.

## Cross-References

- [Cache LLD](../../interview/system-design/lld/cache-lld.md) — cache ownership and lifecycle design.
- [Connection Pool](../../backend/patterns/connection-pool-deep.md) — sizing under session-per-request.
- [Optimistic Concurrency Control](../../dbms/transactions/optimistic.md) — the `@Version` primitive in depth.
- [Correlated Subqueries](../../dbms/sql/correlated-subqueries.md) — the database view of N+1.
- [MVCC Internals](../../dbms/advanced/mvcc-internals.md) — long-transaction costs behind wide sessions.
- [Abstraction and Interfaces](../../interview/system-design/lld/abstraction-interfaces.md) — API-evolution principles.

## References

- Martin Fowler, "[Patterns of Enterprise Application Architecture](https://martinfowler.com/eaaCatalog/)" — Identity Map, Unit of Work, Lazy Load; the canonical naming of the three machines.
- Hibernate ORM User Guide, "[Understanding and tuning the Persistence Context](https://hibernate.org/orm/documentation/)" — flush modes, dirty tracking, L2 cache scoping.
- SQLAlchemy Documentation, "[Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)" — identity map and unit-of-work semantics as an explicit API.
- Vlad Mihalcea, *High-Performance Java Persistence*, 2016 — flush ordering, batching, and N+1 remediation patterns at production depth.
