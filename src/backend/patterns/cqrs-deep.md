# CQRS Deep Dive

## Overview

CQRS — Command Query Responsibility Segregation — is the architectural pattern that splits a system's *write* path (commands that change state) from its *read* path (queries that return state), and gives each path its own model and its own data store. The pattern was introduced by Greg Young in 2010, building on Bertrand Meyer's *Command-Query Separation* principle from *Object-Oriented Software Construction* (1988): a method should either *do* something or *return* something, but not both. CQRS is that principle at the architectural level — a service should either handle a command or answer a query, and the two paths should not share a model.

CQRS is **not** a default. Martin Fowler's 2011 bliki entry is explicit: "the vast majority of systems should not use CQRS". You pay the price — two models, two stores, a synchronisation mechanism — when the read and write sides have genuinely different shapes: heavy queries on a high-write system, multiple views of the same data, or event sourcing forcing a read model by construction.

## Command vs Query Separation

A **command** is an intention to change state: `CreateOrder`, `AddItemToOrder`, `CancelOrder`. It is verb-named, has a target aggregate, and returns either success/failure or an aggregate ID — never domain data. A **query** is a request for state: `GetOrderById`, `ListOrdersByCustomer`, `SearchOrders`. It is noun-named and returns data — never mutates state.

```
                  ┌─────────────────────────────────────────┐
                  │              client / API                 │
                  └──────┬──────────────────────────┬────────┘
                         │ command                   │ query
                         ▼                           ▼
              ┌────────────────────┐         ┌─────────────────────┐
              │  Command handler   │         │  Query handler      │
              │  - validates        │         │  - reads            │
              │  - applies business  │         │  - filters         │
              │    rules            │         │  - paginates       │
              │  - produces events  │         │  - no side effects │
              └────────┬───────────┘         └──────────┬──────────┘
                       │                               │
                       ▼                               ▼
              ┌────────────────────┐         ┌─────────────────────┐
              │   Write store       │         │   Read store        │
              │  (event log or      │         │  (denormalised      │
              │   normalised 3NF)   │         │   views, indexes)  │
              └────────────────────┘         └─────────────────────┘
                       │
                       │ events
                       ▼
              ┌────────────────────┐
              │  Projection        │
              │  (consumer of       │
              │   events; updates   │
              │   read store)       │
              └────────────────────┘
```

The two paths share nothing — not the schema, not the indexes, not the data store technology if it helps. The command side can be a Postgres database normalised to 3NF; the read side can be an Elasticsearch index, a Redis hash, a Materialise view in ClickHouse, a graph in Neo4j, or all of the above for different queries.

## The Write Model: Optimised for Writes

The write model is optimised for *correctness of state transitions*, not for query speed. Its job is to take a command, apply the business rules, and produce a new state. The two questions it has to answer are: *is this command legal right now?* (validation against current state) and *what events describe the resulting change?* (the persistence mechanism).

In a typical CQRS service, the write side is an aggregate: an object that holds the current state and exposes command methods. The aggregate enforces invariants — `Order.add_item` will reject if the order is in `CANCELLED` state. The aggregate never exposes itself to the read side; only the events it produces are visible.

```java
// Write side — aggregate applies the command and produces events.
// It never reads from the query side; its state is the result of
// replaying its own event stream (see Event Sourcing link below).

public final class OrderAggregate {
    private OrderId id;
    private OrderStatus status;
    private Money total = Money.ZERO;

    public List<Event> handle(AddItemToOrder cmd) {
        if (status == OrderStatus.CANCELLED)
            throw new OrderClosedException(id);
        if (cmd.quantity() <= 0)
            throw new IllegalArgumentException("quantity must be positive");
        return List.of(new ItemAdded(id, cmd.sku(), cmd.quantity(),
                                     cmd.unitPrice(),
                                     total.plus(cmd.lineSubtotal())));
    }
}
```

Note what's missing: no `SELECT * FROM orders JOIN order_items` query. The write side does not run read queries; it loads the aggregate (either by replaying events or by fetching a snapshot), applies the command, persists the new events, and returns. The aggregate's storage is shaped by *write* needs — append-only for events, indexed by aggregate ID — not by the shape of any read query.

## The Read Model: Optimised for Reads

The read model is denormalised. The shape of the data matches the shape of the query. A "list of orders for a customer, with line items and totals" view becomes a single table:

```sql
-- Read store — one row per order, with embedded line items as JSON.
CREATE TABLE order_summary (
    order_id      UUID PRIMARY KEY,
    customer_id   UUID,
    customer_name TEXT,                -- denormalised from customers
    status        TEXT,
    total         NUMERIC(10, 2),
    line_items    JSONB,               -- denormalised from order_items
    placed_at     TIMESTAMPTZ,
    INDEX customer_idx (customer_id, placed_at DESC),
    INDEX status_idx   (status, placed_at DESC)
);

-- A query that used to be a 4-table join is now a single index seek:
SELECT * FROM order_summary
WHERE customer_id = $1
ORDER BY placed_at DESC
LIMIT 50;
```

The read model can have as many indexes as the queries need; the write side doesn't pay for them, because they live in a separate store. A read model that supports six different query patterns may have six indexes on the same table — fine, because the write side doesn't write to this table; the projection does, asynchronously.

Different query needs get different read models. The same `Order` aggregate might be projected into a Postgres `order_summary` table for the user-facing order list, an Elasticsearch index for full-text search, a Redis sorted set for recently-viewed orders per customer, and a ClickHouse fact table for analytics. Each projection subscribes to the same event stream and shapes the data its own way. Adding a new read model does not touch the write side — you spin up a new consumer, point it at the event stream from the beginning, and it back-fills itself.

## The Event Sourcing Link

CQRS and event sourcing are *often* paired but they are not the same pattern. CQRS is about separating reads from writes; event sourcing is about *what the write store contains*. The two viable write stores for a CQRS system are:

1. **State-based write store** — a normalised 3NF database. The command handler updates the row, emits a domain event (via the outbox pattern) for the projection to consume. The write store holds current state.
2. **Event-sourced write store** — an append-only log of domain events. The command handler appends events; the aggregate's current state is the *result* of replaying the event log. The write store holds history, not current state.

Pairing CQRS with event sourcing is the canonical form because event sourcing *forces* a read model: you cannot query an event log for "current orders" without first projecting the events into a queryable shape. The projection becomes the read store; the event log is the write store. CQRS is the natural description of the resulting architecture.

```
   state-based CQRS                         event-sourced CQRS
   ──────────────────                       ──────────────────
   ┌──────────────┐                         ┌──────────────┐
   │ Command      │                         │ Command      │
   │   handler    │                         │   handler    │
   └──────┬───────┘                         └──────┬───────┘
          │ UPDATE                                  │ append events
          ▼                                         ▼
   ┌──────────────┐  events (outbox)         ┌──────────────┐
   │ orders table │  ─────────────────▶      │ event log    │ ─── events ──▶
   │ (current     │                            │ (history)    │
   │   state)     │                            └──────────────┘
   └──────────────┘
                                                    │
   same projections consume either stream ◀─────────┘
   and produce read models
```

The state-based version is simpler. The event-sourced version gives you temporal queries ("what was this order's state at 3pm on Tuesday?"), full audit, and replay from scratch — but pays with event versioning and aggregate rebuilds. Most teams start with state-based CQRS and only adopt event sourcing when audit or replay is a first-class requirement.

## Eventual Consistency Between Models

The read model lags the write model. A user submits `AddItemToOrder`, the command handler appends `ItemAdded` to the event log, the projection consumes it milliseconds later and updates `order_summary`. For those milliseconds, the read model is stale — a query that runs immediately after the command will return the old state. This is **read-your-writes inconsistency**, the most user-visible cost of CQRS. Three mitigations:

1. **Make the lag invisible.** A few hundred ms of projection lag is hidden behind the network round-trip and the page render. Good enough for most UIs.
2. **Version the read model.** Each read carries a version (the last event sequence it includes). After a write, the client passes the write's version in subsequent reads; the query handler waits (with a timeout) until the read model catches up. Axon's subscription queries support this directly.
3. **Serve the rare strict-consistency read from the write side.** Load the aggregate fresh; skip the read store for that one query. Costs you the read-side optimisation but only for the few queries that need it.

The honest position: most UIs are already eventually consistent, even in a CRUD system. A page that says "your order is confirmed" 50 ms after a redirect is not lying; it is *describing* a system that has converged. Designing the UI to expect eventual consistency is usually easier than fighting the architecture for strict consistency.

## Projection: Read Model Rebuild

The projection is a stateless consumer of the event stream that, for each event, executes the appropriate insert/update/delete against the read store. Its most important property is **rebuildability**: given the event log, the projection must be able to wipe its read store and reconstruct it from scratch by replaying the events.

```
   event log         projection (idempotent consumer)        read store
   ──────────                                              ─────────────
   seq 1: OrderCreated   ─┐                              INSERT order_summary
   seq 2: ItemAdded        ├─ consume in order ─▶ UPDATE  order_summary.total
   seq 3: ItemAdded       ─┘                              UPDATE  order_summary.total
   seq 4: OrderCancelled                                  UPDATE  order_summary.status
```

Idempotency is essential: the projection may consume the same event twice (a crash mid-apply, a Kafka rebalance), and the read model must end up identical either way. Achieve this either with an `applied_events` table to skip duplicates, or with upserts idempotent by event ID — `INSERT ... ON CONFLICT (order_id) DO UPDATE SET total = EXCLUDED.total WHERE seq < EXCLUDED.seq`.

The rebuild capability is what makes CQRS systems operable: when a projection bug is found, or a new field is added to the read model, the fix is *rebuild* the read store from the event log. No migration, no downtime, no risk to the write side. This is also what makes event-sourced CQRS attractive for systems with complex, evolving read patterns — you can experiment with read models cheaply.

## Production Use

### Axon Framework

Axon Framework (Java) is the most mature CQRS/event-sourcing framework in the JVM world. It provides the command bus, the event bus, the event store, the projection mechanism, and the query gateway as first-class components. An Axon application looks like:

```java
@Aggregate
public class Order {
    @AggregateIdentifier private OrderId id;
    private OrderStatus status;

    @CommandHandler                    // constructor command — emits OrderCreated
    public Order(PlaceOrder cmd) {
        AggregateLifecycle.apply(new OrderCreated(cmd.orderId(), cmd.items()));
    }

    @EventSourcingHandler              // mutates state from the event stream
    public void on(OrderCreated e) { this.id = e.orderId(); this.status = OrderStatus.NEW; }

    @CommandHandler
    public void handle(AddItem cmd) {
        if (status != OrderStatus.NEW) throw new IllegalStateException();
        AggregateLifecycle.apply(new ItemAdded(id, cmd.item()));
    }
}

// Query side — a separate @EventHandler component subscribes to events
// and updates the read store (a JdbcTemplate UPDATE, an Elasticsearch
// index, etc.). Axon routes events to it in order, with retries.
```

Axon handles the plumbing: routing commands to the right aggregate instance, persisting events to the event store (Axon Server, JPA-backed, or a custom `EventStorageEngine`), and dispatching events to projections in order.

### EventStoreDB

EventStoreDB (a purpose-built event store written in C#) makes streams first-class: you append events to `order-123`, and consumers subscribe via `$ce-order` (a category projection that gives you all events for orders in order). The streams model is lighter than Kafka's topic model — no partitions, no consumer groups, just per-stream subscribers — which makes it easier to reason about for the typical aggregate-as-stream pattern.

### Kafka as event store

Kafka can serve as the event store, with one topic per aggregate type and the aggregate ID as the message key. One wrinkle: log compaction (which retains the latest event per key and discards older ones) is incompatible with event sourcing, because the *older* events are exactly what you need to rebuild state. The workaround is a non-compacted topic with retention-by-time, or a dedicated event store that publishes to Kafka only for inter-service integration.

## Comparison to CRUD

| Aspect | CRUD (one model) | CQRS (split models) |
|--------|------------------|----------------------|
| Read & write share schema | Yes | No |
| Read latency | Constrained by write schema | Optimised independently |
| Write latency | Constrained by read indexes | No read indexes on write store |
| Scaling | Whole store scales together | Read store scales independently |
| Consistency | Strong (single store) | Eventual (projection lag) |
| Complexity | Low | High (two stores, projection) |
| Schema evolution | One migration | Migration on write; rebuild on read |
| Best for | Simple CRUD, balanced R/W | Skewed R/W, complex queries, ES |

## Common Pitfalls

1. **Adopting CQRS for a CRUD system.** If your read and write patterns are similar, CQRS buys you nothing but complexity. The test: are you querying your data in shapes that differ significantly from how you write it? If not, do not adopt CQRS.
2. **Sharing a database between read and write.** A slow query on the read side can starve the write side. The whole point is independent scaling; if you share the store, you have not actually separated them.
3. **Projections that aren't idempotent.** A projection that does `UPDATE total = total + 5` on an `ItemAdded` event will produce wrong totals on a replay. Projections must be full-replaceable: `UPDATE total = ?` driven by the event's `newTotal` field.
4. **Blocking the command side on the read side.** If the user-facing API calls the command handler and then waits for the projection to catch up before returning, you have built the slowest possible synchronous system.
5. **Multiple read models with conflicting schemas.** Six projections that each model `Order` slightly differently become a maintenance nightmare when the business rules change. Treat the read models as ephemeral and rebuildable.

## Interview Questions

### Q: When is CQRS the wrong choice?

When the read and write sides have the same shape. A blog platform with `posts` and `comments` tables, queried in roughly the form they are written, gains nothing from CQRS. A ticketing system with high-volume writes (every check-in, every status change) and wildly different read shapes (per-venue dashboards, per-customer histories, real-time analytics) is a natural fit. Fowler's test: "for the vast majority of systems, CRUD is enough."

### Q: How do you handle the read-your-writes problem in CQRS?

Three options, increasing in complexity: (1) accept the lag if it's small enough that the UI hides it; (2) version the read model and have the query handler block until the projection catches up to the write's version (Axon's subscription queries); (3) route the rare strict-consistency read to the write side. For most systems (1) is the right answer — design the UI to expect a brief convergence window.

### Q: Why is the projection's idempotency so important?

Because the projection will be replayed. Crashes, schema migrations, new read models, projection bugs — all are resolved by wiping the read store and replaying from the event log. A non-idempotent projection produces wrong state on the second consumption of an event, and on every replay. The rule: every projection must produce identical state given identical input events, regardless of how many times each event is consumed.

## References

- Greg Young, *CQRS Documents* (2010, published online) — the original paper that defined the pattern; the unambiguous source on what CQRS is and is not. https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf
- Greg Young, *CQRS with Event Sourcing* (talk at QCon 2010 / DDD Europe) — the canonical talk that introduced the pattern to the wider community. https://www.infoq.com/presentations/cqrs-introduction/
- Martin Fowler, *CQRS* (bliki, 2011) — the high-level treatment, with the explicit warning that the pattern is over-applied. https://martinfowler.com/bliki/CQRS.html
- Martin Fowler, *CQRS & Event Sourcing* (bliki) — Fowler's analysis of the CQRS+ES combination and the risks of conflating the two. https://martinfowler.com/bliki/CQRSAndEventSourcing.html
- Axon Framework reference guide — the canonical JVM implementation; the docs walk through command bus, event bus, projection, and query gateway end-to-end. https://docs.axoniq.io/reference-guide/
- EventStoreDB documentation — streams, projections, and persistent subscriptions; the operational model of a purpose-built event store. https://developers.eventstore.com/
- DDD Community, *CQRS* — community-curated resources, talks, and papers on the pattern. https://www.dddcommunity.com/library/young_2010/

## Related Topics

- [Event Sourcing Deep Dive](./event-sourcing-deep.md) — the persistence pattern most often paired with CQRS.
- [Event-Driven Architecture Deep Dive](./event-driven-architecture-deep.md) — the communication style that projections sit on.
- [CQRS](./cqrs.md) — the shorter overview page.
- [CDC and Outbox Pattern](./cdc-outbox.md) — how to emit events atomically with state changes in state-based CQRS.
- [Kafka](../messaging/kafka.md) — the broker that most CQRS projections consume from.
- [Anti-Corruption Layer Deep Dive](./anti-corruption-layer-deep.md) — when a read model has to translate from another bounded context.
