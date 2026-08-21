# Monolith to Microservices Migration Deep Dive

## Overview

Migrating a monolith to microservices is the highest-stakes refactoring most engineering organisations ever undertake. Done well, it lets large product teams move independently, deploy multiple times a day, and scale hot paths separately from cold ones. Done badly — and this is the common outcome — it produces a *distributed monolith*: a system with all of the costs of microservices (network calls, operational complexity, partial failures) and none of the benefits (you still have to deploy everything together because everything calls everything). Sam Newman's *Monolith to Microservices* (O'Reilly, 2019) is the canonical text and is unambiguous on the point: **the migration is not a rewrite, it is a series of small, reversible extractions**, each of which has to leave the system better than it found it.

The decision to migrate is itself worth questioning. Newman and Martin Fowler have both argued for years that a well-structured monolith with clear module boundaries is a perfectly reasonable architecture for the majority of systems. The migration is justified when the *organisation* outgrows the monolith — when teams are stepping on each other's commits, when deploys are gated by a single release manager, when a single misbehaving module keeps taking the whole process down. If those symptoms are absent, the migration is a solution in search of a problem.

This page covers the four techniques that together make up a migration: the **strangler fig** for the cut-over mechanism, **domain-driven decomposition** for deciding *what* to extract, **database decomposition** for the hardest part — splitting the schema — and **change data capture (CDC)** for moving data without breaking the old system. It closes with the anti-patterns that catch teams out.

## The Strangler Fig Approach

The strangler fig pattern, named by Martin Fowler in 2004 after the eponymous tree that grows around and eventually replaces its host, is the only safe cut-over mechanism for an in-production monolith. The idea: put an interception layer in front of the monolith, route *some* requests to a new implementation, leave the rest on the monolith, and gradually move functionality over. At every stage the system works; at no stage is there a "big bang" release where the new system replaces the old one wholesale.

```
                ┌─────────────────────────────────────────┐
                │            API Gateway / Proxy            │
                │   routing rules:                          │
                │     /api/orders/*         → new Orders svc │
                │     /api/billing/*        → new Billing svc│
                │     everything else       → monolith        │
                └───────────┬───────────────────┬───────────┘
                            │                   │
              ┌─────────────▼─────────┐   ┌─────▼──────────────┐
              │  New microservices    │   │   Legacy monolith  │
              │  (extracted over time)│   │   (shrinks over    │
              │                       │   │    time)           │
              └───────────────────────┘   └────────────────────┘
```

The interception layer is almost always an API gateway (Kong, Envoy, NGINX, AWS API Gateway) configured with path-based routing. The first extraction is the hardest because you also have to install the gateway; subsequent extractions are just routing changes.

Three incremental moves characterise a healthy strangler:

1. **Strangle by feature** — pick one functional slice (e.g. "checkout") and move it. The new service owns the user-facing behaviour; the old monolith still handles everything else.
2. **Strangle by read path** — leave writes on the monolith, but serve reads from a new denormalised read model fed by CDC. This is a low-risk first move because reads are idempotent and a fallback to the monolith is trivial.
3. **Strangle by tenant** — route 1% of users (or one customer, or one region) to the new service, compare outcomes, ramp up. This is the *expansion-contraction* pattern from Charity Majors: expand the new path, watch metrics, contract to the old if anything looks wrong.

The signal that the migration is *done* is when the monolith has shrunk to a thin shim — at which point the shim itself can be deleted. Many teams stop earlier and live with a permanently dual-running system; that is usually a sign that the *next* extraction is harder than the last and the team has run out of easy wins.

## Domain-Driven Decomposition

Before you can extract a service, you have to know where the seam is. The naive approach — "let's split it into 12 services, one per top-level directory" — produces a distributed monolith within a year, because the directory structure rarely aligns with the actual *business* boundaries.

The right technique is Eric Evans's **bounded contexts** from *Domain-Driven Design* (2003), applied at the architectural scale. A bounded context is a region of the system where a term means one thing and one thing only. In an e-commerce monolith, the word "Order" might mean a shopping cart (to the catalogue team), a fulfilment job (to the warehouse), an invoice line (to finance), and a customer-support ticket (to the helpdesk). Each of those is a different bounded context. Trying to share one `Order` entity across all four produces a god-class with a thousand fields, which is the disease the migration is supposed to cure.

The decomposition exercise:

```
   workshop output — bounded contexts and their relationships

   ┌──────────────┐  Catalogue ──▶  ┌──────────────┐
   │   Pricing    │  (conformist)  │  Catalogue   │
   └──────────────┘                └──────────────┘
          │  upstream
          ▼  (published language)
   ┌──────────────┐                ┌──────────────┐
   │   Checkout   │  customer ──▶  │   Identity   │
   └──────────────┘                └──────────────┘
          │
          ▼  (ACL: maps to fulfilment domain)
   ┌──────────────┐                ┌──────────────┐
   │  Fulfilment │                │  Payments    │
   └──────────────┘                └──────────────┘
```

Each box becomes a candidate service. The arrows are the context-mapping patterns from DDD: **published language** (one context exposes a stable schema the others consume), **conformist** (one context adopts another's model wholesale, no translation), **anti-corruption layer** (the consuming context translates to protect itself), and **customer/supplier** (the teams have a power relationship that has to be negotiated). Without these explicitly drawn, the new services will end up talking to each other in arbitrary ways — usually by sharing a database table, which is the next problem.

The rule of thumb: a service should be sized to **one bounded context, owned by one team, with a clear business capability**. Smaller than that and you have a "nanoservice" that exists only to add latency; larger and you have a distributed monolith.

## Database Decomposition

The shared database is the single most stubborn obstacle to the migration. Code can be moved by rewriting it; data, if it has foreign keys to other data, cannot be moved without breaking constraints. Eric Brewer's observation that "the database is the bottleneck" applies here with a vengeance: as long as every service reads and writes the same `orders`, `users`, and `inventory` tables, you do not have microservices, you have a distributed monolith with extra hops.

The target is **database-per-service**: each service owns its schema (or its own database entirely), no other service can touch it, and the only way to read another service's data is over its API. This is non-negotiable if you want the benefits of microservices; it is also the source of the worst migration pain.

The decomposition proceeds in three layers of risk, from least to most:

### 1. Reference data first

Static lookups — currency codes, country codes, product categories — are easy to copy. Each service gets its own `currencies` table. Updates are rare and can be synced through a reference-data service or a config push.

### 2. Read-only views

Where service A needs to *read* service B's data but never write it, you can materialise a denormalised view in A's schema. The view is updated by CDC (see below) or by a periodic export. A's schema now contains a `customer_summary` table; A never touches B's `customers` table directly. This is the *consumer-owned projection* pattern.

### 3. Write-shared tables

This is the hard case. If service A and service B both write to the same `orders` table, one of them has to win. The winning service becomes the *owner*; the losing service has to call the owner's API instead of writing the table directly. Until that API exists and the calls are made, the table is effectively shared, and the system is a distributed monolith.

```
   before:                              after:
   ┌─────────────────────┐              ┌────────┐  ┌────────┐
   │  Monolith schema    │              │ orders │  │ users  │
   │  ────────────────   │   ──────▶    │ schema │  │ schema │
   │  users (FK→orders)  │              │  owned │  │  owned │
   │  orders             │              │  by O. │  │  by U. │
   │  order_items        │              │  svc   │  │  svc   │
   │  invoices           │              └────────┘  └────────┘
   │  audit_log          │                  ▲            ▲
   └─────────────────────┘                  │            │
       (all FKs in one DB)                   │  CDC       │
                                            └────────────┘
                                          (no shared FK)
```

The foreign keys disappear across service boundaries because they cannot exist across databases. Referential integrity that used to be enforced by `FOREIGN KEY (user_id) REFERENCES users(id)` now has to be enforced by application code (the `users` service validates that a user exists before `orders` accepts an order). This is a real loss; some teams accept eventual consistency and others add a saga to compensate.

## The Data Migration: Dual-Write + CDC

Once a service is carved out and has its own schema, the existing data has to move into the new schema, and ongoing writes have to keep both schemas in sync until the cut-over. Two techniques handle this.

### Dual-write with the outbox pattern

The naive approach — the monolith writes to its own DB, then makes a synchronous HTTP call to the new service to write the same data — fails on the second failure: if the HTTP call fails, the two systems are out of sync with no recovery. The outbox pattern fixes this: the monolith writes its own table *and* an `outbox` row in the same transaction; a separate process reads the outbox and pushes the event to the new service. Either both happen or neither does, locally.

```
   monolith transaction:
     BEGIN
       INSERT INTO orders (...);              -- normal write
       INSERT INTO outbox (event) VALUES (...);-- same tx, same DB
     COMMIT
                                ▼  separate process, at-least-once
                          ┌─────────────┐
                          │  Debezium   │  reads outbox via CDC
                          │  connector  │  → publishes to Kafka
                          └─────────────┘
                                ▼
                          ┌─────────────┐
                          │  New Orders  │  consumes event,
                          │  Service     │  applies to its DB
                          └─────────────┘
```

### Change Data Capture (CDC)

CDC is the engine that makes the outbox pattern work at scale. Tools like **Debezium** (built on Kafka Connect) read the database's transaction log — Postgres WAL, MySQL binlog, MongoDB oplog — and emit a stream of row-level changes. The new service consumes this stream and updates its own schema. Because CDC reads the log, it sees every committed change, in order, with no impact on the application. Once a service's data is being mirrored by CDC, the cut-over to that service becomes a routing change at the gateway, with the old monolith still in place as a fallback.

When the new service is *the* writer for a slice (say, after cut-over), the direction reverses: the new service writes, publishes events, and the monolith consumes them to keep its (now read-only) copy fresh. Eventually the monolith's copy is dropped.

## Anti-Patterns

### The distributed monolith

A distributed monolith is a system where services are deployed independently but *cannot* be deployed independently, because changing one requires changing others. The symptoms: a deploy of service A breaks service B; a schema change in service A requires a coordinated deploy of services B, C, and D; every service calls every other service synchronously. The cure is to look hard at the dependency graph and break cycles — a cycle of synchronous calls is the smoking gun. Conway's Law applies: a distributed monolith usually reflects an organisation that has not actually split its teams; the architecture is just the org chart in distributed form.

### Premature decomposition

Decomposing a greenfield project into 50 microservices on day one — before the domain boundaries are understood, before the team has felt the pain of the wrong boundary — is premature decomposition. The first version of any non-trivial system is usually a monolith, because monoliths are easier to refactor. The right time to extract a service is the second time you have to change a feature for a reason that has nothing to do with that feature; the wrong time is at project kickoff.

### Shared database as a service

"Database-per-service" is sometimes reinterpreted as "one database server, owned by a database team, that every service writes to". This is the shared database in disguise; it has the same coupling, just with a network hop in the middle. A real database-per-service setup has each service team owning its schema, its migrations, and its operational runbooks.

### Distributed transactions across services

Trying to preserve ACID across services with two-phase commit (XA) is the fastest way to ruin the availability of a microservice system. The right answer is to use sagas — local transactions with compensating actions — and accept eventual consistency. Distributed transactions also betray that the cut has not actually been made: if two services have to be transactionally consistent, they are probably one service.

## Comparison

| Aspect | Big-bang rewrite | Strangler fig migration |
|--------|-------------------|--------------------------|
| Reversibility | None at cutover | Each step reversible |
| Risk | All-or-nothing | Bounded per step |
| Business disruption | Freeze during migration | Continuous delivery maintained |
| Completion time | Theoretically faster | Slower, but real |
| Failure mode | Project cancelled | Last extraction is hardest |

## Interview Questions

### Q: When should you *not* migrate a monolith to microservices?

When the pain you're solving is *not* organisational. If the problem is performance, a hot-path optimisation in the monolith is cheaper. If the problem is reliability, modularising the monolith and adding bulkheads is cheaper. If the problem is team autonomy (multiple teams blocked by one release train, conflicting deploys, ownership disputes), the migration is justified. Newman's framing: "decompose to enable team autonomy, not because 'microservices are modern'."

### Q: How do you split a foreign-key relationship when you separate databases?

You can't — foreign keys don't cross database boundaries. You replace them with application-level validation: the owning service exposes an API (`GET /users/{id}`) and the consuming service calls it (often with a cache) before accepting a write. The cost is eventual consistency: a user deleted in the users service might still be referenced by an order written a moment before. The cure is either soft-delete (mark deleted, don't physically delete) or accepting that referential integrity is now a soft property of the system.

### Q: Why does CDC beat dual-write for keeping two databases in sync?

Dual-write (write to DB1, then write to DB2 in the same application call) fails when DB2 is unreachable: the write to DB1 is committed, the write to DB2 is lost, and there is no automatic recovery. CDC reads DB1's transaction log *after* commit, so DB1 is never blocked by DB2's availability. The CDC pipeline replays missed events on recovery. The trade-off is eventual consistency — DB2 lags DB1 by the CDC pipeline's latency, typically 100ms–1s.

## References

- Sam Newman, *Monolith to Microservices* (O'Reilly, 2019) — the canonical text on the migration; the strangler-fig-by-feature and decomposition-by-bounded-context material is here. https://www.oreilly.com/library/view/monolith-to-microservices/9781492047838/
- Martin Fowler, *StranglerFigApplication* (bliki, 2004, updated 2022) — the original article naming the pattern and explaining the cut-over. https://martinfowler.com/bliki/StranglerFigApplication.html
- Martin Fowler, *Microservices* (article, 2014, co-authored with James Lewis) — the definitional article that named the architectural style and set the conversation. https://martinfowler.com/articles/microservices.html
- Sam Newman, *Building Microservices* 2nd ed. (O'Reilly, 2021) — the companion volume on the *target* architecture, useful when the migration is underway. https://www.oreilly.com/library/view/building-microservices-2nd/9781492034018/
- ThoughtWorks Technology Radar — recurring assessment of migration-related techniques (the outbox pattern, change data capture, the "monolith first" position); search the radar for "strangler", "outbox", and "monolith first". https://www.thoughtworks.com/radar
- Eric Evans, *Domain-Driven Design* (Addison-Wesley, 2003) — bounded contexts, context mapping, and the strategic design that underlies decomposition. https://www.domainlanguage.com/ddd/
- Debezium documentation — the most-used open-source CDC engine; the docs cover the outbox pattern explicitly. https://debezium.io/documentation/reference/stable/transformations/event-flattening.html

## Related Topics

- [Microservices](./microservices.md) — the target architecture; this page is the path to get there.
- [Strangler Fig](./strangler-fig.md) — the cut-over mechanism, treated on its own page.
- [Event-Driven Architecture Deep Dive](./event-driven-architecture-deep.md) — the runtime style most migrated services adopt.
- [CDC and Outbox Pattern](./cdc-outbox.md) — the data-migration engine that makes the cut-over safe.
- [Saga](../../dbms/transactions/saga.md) — the distributed-transaction pattern that replaces XA across service boundaries.
- [Anti-Corruption Layer Deep Dive](./anti-corruption-layer-deep.md) — the translator pattern used when a migrated service has to talk to its old monolith.
