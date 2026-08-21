# Event Sourcing Deep Dive

## Overview

Event sourcing is the persistence pattern in which the *events* that have happened to an entity — every state change, in the order it occurred — are the source of truth. The entity's *current* state is derived by replaying the events. Nothing is ever updated; nothing is ever deleted. Every mutation is an `append` to an event log, and "current state" is a function `fold(events) -> state` computed on demand or cached as a snapshot.

The pattern was articulated clearly by Greg Young around 2010 (his talk *A Decade of DDD, CQRS, Event Sourcing* is the canonical retrospective) and by Martin Fowler in his bliki entry *Event Sourcing* (2005, updated 2017). Young's framing: a state-based CRUD system answers the question "what is the current state?" and forgets everything else. An event-sourced system answers "what is the current state?" *and* "how did we get here?" — the latter being a property of the storage model, not a feature added on top.

The cost of event sourcing is substantial: schema evolution becomes a first-class problem (events are immutable but schemas change), aggregates have to be rebuilt, and the mental model is alien to most teams. The benefit is also substantial: full audit by construction, temporal queries ("what was this account's balance at 3pm on Tuesday?"), replay from any point in history, and an event stream that is also a perfect integration feed. Use it when the audit or temporal-query requirement is real — financial systems, regulatory systems, anything that has to answer "what happened, and in what order, and at what time?" — and avoid it when the use case is just "store and update rows".

## The Append-Only Event Log

The event store is an append-only log of typed events. Each event has a small, fixed set of fields:

```
   ┌────────────────────────────────────────────────────────────────────┐
   │ event_id      UUID  (unique, used for idempotency on consumption)   │
   │ stream_id     str  (the aggregate ID; e.g. "order-123")             │
   │ seq           int  (monotonic per-stream sequence number)            │
   │ type          str  (e.g. "OrderPlaced", "ItemAdded")                 │
   │ payload       JSON / Avro / Protobuf — the event's data               │
   │ metadata      JSON — correlation_id, user_id, ip, trace_id, ts        │
   │ timestamp     ISO8601 — when the event occurred (vs. when stored)    │
   └────────────────────────────────────────────────────────────────────┘
```

Events are appended at the end of the stream; they are never rewritten. The store is keyed by `(stream_id, seq)` so that consumers can read any stream in deterministic order. Reads of the log are: "give me all events for stream `order-123` from seq 0" (to rebuild state) or "give me all events for category `order` from the global position P" (for projections).

```
   stream: order-123                              stream: order-456
   ┌───────────────────────────────────────┐       ┌───────────────────────────────────────┐
   │ seq 1: OrderPlaced    {items:[...]}  │       │ seq 1: OrderPlaced    {items:[...]}    │
   │ seq 2: ItemAdded      {sku:A, qty:2} │       │ seq 2: OrderCancelled {reason:"oos"}  │
   │ seq 3: PaymentCharged {amount:99}    │       │ seq 3: RefundIssued   {amount:0}       │
   │ seq 4: OrderShipped    {tracking:..} │       └───────────────────────────────────────┘
   └───────────────────────────────────────┘
                                       ▲
                                       │ append-only: writes go here, never modify above
```

A critical distinction: events are **facts**, not commands. `OrderPlaced` is a fact (it happened); `PlaceOrder` is a command (a request to make it happen). The command may fail validation and produce no event; an event, by definition, has happened and cannot be undone. "Undoing" an event is itself an event — `OrderCancelled` is appended, not by deleting `OrderPlaced`. This is the same property that double-entry bookkeeping has had since the 14th century: corrections are entries, not edits.

## State Reconstruction by Replay

To get the current state of an aggregate, the application loads every event for its stream, in order, and applies each to a stateless fold function. The result is the current state.

```python
class Order:
    """An event-sourced aggregate. State is the result of replaying events."""

    def __init__(self, stream_id: str):
        self.stream_id = stream_id
        self.status = "NEW"
        self.items: list[LineItem] = []
        self.total = Money(0)
        self.version = 0   # the seq of the last applied event

    def apply(self, event: Event) -> None:
        # Pure function of (state, event) -> state. No I/O.
        match event.type:
            case "OrderPlaced":
                self.status = "PLACED"
                self.items = list(event.payload["items"])
                self.total = sum(i.subtotal for i in self.items)
            case "ItemAdded":
                line = LineItem(**event.payload)
                self.items.append(line); self.total = self.total.plus(line.subtotal)
            case "OrderCancelled":
                self.status = "CANCELLED"
        self.version = event.seq

    def handle(self, cmd: AddItemToOrder) -> list[Event]:
        # Validates against current state (loaded by replay); produces events.
        if self.status == "CANCELLED":
            raise OrderClosed(self.stream_id)
        if cmd.quantity <= 0:
            raise ValueError("quantity must be positive")
        return [Event(stream_id=self.stream_id, seq=self.version + 1,
                      type="ItemAdded",
                      payload={"sku": cmd.sku, "quantity": cmd.quantity,
                               "unit_price": cmd.unit_price.amount},
                      timestamp=cmd.occurred_at)]

# Load and rebuild:
order = Order("order-123")
for event in event_store.read_stream("order-123"):
    order.apply(event)
# order.status, order.items, order.total now reflect the current state
```

The `apply` function is pure: given the same starting state and the same event, it produces the same ending state, with no I/O. This is what makes event sourcing tractable — the rebuild is a deterministic computation over a log. It is also what makes the pattern dangerous: if `apply` is not pure (it reads `datetime.now()`, or fetches a current price from another service), the rebuild is non-deterministic and the system drifts.

The cost of replaying is linear in the number of events. For an aggregate with ten events this is sub-millisecond; for one with ten thousand it starts to be visible. That is where the snapshot optimisation comes in.

## Snapshot Optimisation

A **snapshot** is a checkpoint: a serialised copy of the aggregate's state at a particular sequence number, written alongside the event stream. When the aggregate is next loaded, the application reads the latest snapshot, applies only the events with `seq > snapshot.seq`, and avoids the full replay.

```
   stream: order-123
   seq 1:  OrderPlaced    ──┐
   seq 2:  ItemAdded         │  full replay from seq 0
   ...                       │   until snapshot at seq 50
   seq 50: StatusUpdated   ──┘   (serialised state)
   seq 51: ItemAdded       ──┐
   seq 52: OrderRefunded      │  incremental replay (2 events)
```

Snapshotting is the standard answer to the "aggregate with a long history" problem. It is also the source of a subtle bug: if the snapshot serialisation format ever changes, snapshots written under the old format are unreadable under the new. The solution: store the snapshot's schema version, and on load, migrate the snapshot in memory if needed (or fall back to a full replay if migration is impossible). Axon Framework's `Snapshotter` and EventStoreDB's snapshot projection both take this approach.

The rule of thumb: snapshot every N events (N typically 100–1000, tuned per aggregate's event density and size). Do not snapshot too eagerly — a snapshot on every write is just a state-based store with extra cost.

## Projections: The Read Model

The event log is unqueryable for "current state" — asking "what is the total of order 123?" requires replaying all its events. Projections solve this: a projection is a consumer of the event stream that maintains a queryable, denormalised view in a separate store (Postgres, Elasticsearch, Redis).

```
   event log                          projections             read stores
   ─────────────                      ─────────────           ─────────────
   OrderPlaced ─┐                  Order summary            Postgres table
   ItemAdded  ──┤── projection A →  (current state)         (order_summary)
   OrderShipped─┘
                │
                ├── projection B →  Customer history        Redis sorted set
                │                  (recent orders / cust)  (cust:$id:recent)
                │
                └── projection C →  Search index            Elasticsearch
                                   (full-text on items)     (orders)
```

Each projection subscribes to the event stream, applies events in order, and updates its read store. Adding a new read model is a matter of writing a new projection and pointing it at the log from seq 0 — it back-fills itself. This is the property that makes event-sourced systems operable: a bug in a projection is fixed by fixing the projection, dropping its read store, and replaying. No data migration; no downtime on the write side.

Projections must be **idempotent**. The event store delivers events at-least-once (exactly-once delivery is an illusion across process boundaries); a projection that does `UPDATE balance = balance + 5` will double-count on redelivery. Idempotency comes from either (a) tracking the last-applied event ID per projection and skipping duplicates, or (b) writing upserts that produce the same final state regardless of delivery count — `INSERT ... ON CONFLICT DO UPDATE SET balance = EXCLUDED.balance WHERE last_seq < EXCLUDED.last_seq`.

## The Versioning Problem

Events are immutable but their *schema* evolves. A `PaymentCharged` event that started life with `{amount: 99, currency: "USD"}` eventually needs `{amount: 99, currency: "USD", processor: "stripe", processor_txn_id: "ch_..."}`. The old events are already in the log; you cannot rewrite them. Greg Young's *Versioning in an Event Sourced System* (2014) is the canonical treatment.

Four strategies, in increasing order of sophistication:

### 1. Weak schema (tolerate missing fields)

Use a serialisation format that tolerates missing fields (JSON, Avro with defaults). A consumer reading an old event sees the new field as absent and falls back to a default. Works for *additive* changes — new optional fields, never removed fields. This is what Schema Registry's `BACKWARD` compatibility mode enforces and what most teams start with.

### 2. Upcasters

A pure function `(old_event) -> new_event` applied at read time. When the application loads an event of `schema_version=1`, an upcaster transforms it to `schema_version=2` before handing it to the `apply` function. The log is untouched; the upcaster is part of the read path. Axon, EventStoreDB, and Kafka Streams all support upcasters as a first-class concept:

```java
// Upcaster: transforms a v1 PaymentCharged into a v2 PaymentCharged on read.
public class PaymentChargedUpcasterV1ToV2 implements EventUpcaster {
    public EventData upcast(EventData input) {
        if (!input.type().name().equals("PaymentCharged")
            || input.type().revision() != null)  // null = v1
            return input;
        var p = JsonMutation.on(input.payload())
            .put("processor", "legacy")           // default for old events
            .put("processor_txn_id", "unknown").json();
        return input.withPayload(p).withType(EventType.of("PaymentCharged", "v2"));
    }
}
```

Upcasters chain (`v1 -> v2 -> v3 -> v4`); the application always sees the latest version, regardless of when the event was written. The cost is CPU on the read path — non-trivial for high-volume streams.

### 3. Versioned events (parallel streams)

When the change is breaking and an upcaster is impractical, publish a new event type alongside the old: `PaymentChargedV1` continues for old events; new writes produce `PaymentChargedV2`. Consumers subscribe to both. Works for high-churn schemas but doubles the consumer surface.

### 4. Replay-and-rewrite

The nuclear option: define a new event log with a new schema, replay the old log through a transformation function, and write the new events to the new log. Switch consumers over. Delete the old log. Only justified when the cost of the old shape exceeds the cost of the migration.

The trap to avoid: lazy changes that mutate the event payload in place. Some teams write a script that "patches" old events in the log to the new shape. This violates the immutability contract — the log is no longer a faithful record of what happened — and breaks any consumer that has cached state derived from the old events. Upcasters, parallel streams, and replay-rewrite are the safe alternatives.

## The Event Store

The store itself is a special-purpose database with three properties that distinguish it from a general-purpose database: append-only writes (never updates, never deletes — storage is heavily optimised for sequential appends, no row locks, no MVCC churn); causal ordering per stream (the `(stream_id, seq)` index is the only one that matters for reads; secondary indexes on the payload are the projections' job); and replay from any position (consumers read the log from any offset, either as a one-shot back-fill or as a live subscription).

### EventStoreDB

The canonical purpose-built event store. Streams are first-class — you append to `order-123`, read from `order-123`, and subscribe to category streams (`$ce-order`) for cross-aggregate projections. Persistent subscriptions survive consumer restarts. The on-disk format is optimised for the append-only workload; throughput is high (tens of thousands of appends per second on commodity hardware) and reads scale with the read replicas.

### Apache Kafka as event store

Kafka's partitioned log is a natural fit: one topic per aggregate category, aggregate ID as the partition key, the offset within the partition as the seq number. The wrinkle is **log compaction**: Kafka's standard optimisation retains only the latest event per key and discards older ones — correct for state-transfer events (the latest "current balance" wins) and **wrong** for event sourcing (you need every historical event to rebuild). The workaround is to disable compaction on the event-source topic and use time-based retention sized for the longest projection rebuild window. Many teams instead use a purpose-built store for the event log and publish to Kafka only for inter-service integration.

A related hybrid is **DynamoDB Streams** (or Kinesis) on AWS: every modification to a DynamoDB table produces a stream record, giving an event-log shape over a state-based store. This is CDC-on-a-state-store rather than true event sourcing, but it gives the same operational properties — append-only log, replayable, queryable current state via the table, history via the stream. Many teams call this "pragmatic event sourcing".

## Comparison to State-Based (CRUD)

| Aspect | State-based (CRUD) | Event-sourced |
|--------|--------------------|----------------|
| Source of truth | Current state row | Event log |
| Audit | Add-on (`audit_log` table) | By construction |
| Temporal queries | Impossible without audit log | Native (`state(at=t)`) |
| Update | `UPDATE` row | Append event |
| Delete | `DELETE` row | Append compensating event |
| Schema evolution | Schema migration | Upcasters, versioned events |
| Aggregate load | Single row read | Replay (or snapshot + delta) |
| Cross-service integration | Outbox / CDC | Built-in (the log is the feed) |
| Complexity | Low | High |
| Use case | Most systems | Audit, temporal queries, financial |

## Production Use

### Financial systems

Banking, accounting, and trading systems were the original event-sourcing adopters — predating the pattern's name by centuries, in the form of double-entry bookkeeping. A ledger is an append-only log of transactions; the account balance is the sum of the entries. Regulators require audit ("show me every transaction for this account for the last 7 years"), and *deleting* a transaction is illegal — corrections are reversal entries. Modern banks run the same shape in software: the ledger is an event log, the balance is a projection, and audit queries are reads of the log.

### Audit logs

Any system that has to answer "who did what, when, and from where?" benefits from event sourcing. Configuration systems (AWS Config, Terraform state), access-control systems, and healthcare record systems all naturally fit the pattern — the events are the data, and the current state is the projection. The compliance question "show me the state of this record as of last March" is a temporal query that a state-based system cannot answer without a separate audit log that mimics event sourcing.

## Interview Questions

### Q: Why is "undoing" an event itself an event, not a deletion?

Because the log is the source of truth, and the truth includes the fact that the original event happened. Deleting `OrderPlaced` because the order was cancelled erases the history — the customer placed an order, paid for it, and then cancelled it. A regulator querying "did this customer ever place an order?" needs to see the placement. A `OrderCancelled` event after the `OrderPlaced` event preserves the full history; the projection that computes current state sees both and reports the order as cancelled, while the audit log sees both and reports the full sequence.

### Q: How do you handle an event-sourced aggregate with a million events in its history?

Snapshots. Write a serialised state at every Nth event (N tuned to keep the incremental replay under, say, 100 ms); on load, read the latest snapshot and replay only the events after it. For truly pathological cases (a stream that grows without bound), reconsider the aggregate boundary — a million-event stream is usually a sign that the aggregate is too coarse and should be split into smaller, more focused aggregates.

### Q: How do you change the shape of an event after events of the old shape are already in the log?

Upcasters, in most cases. Write a pure function `(old_event) -> new_event` that the read path applies before handing the event to the aggregate. The log is never rewritten; the upcaster is part of the read code. For breaking changes that an upcaster cannot handle, publish a new event type in parallel and migrate consumers. The nuclear option — replay the log through a transformation and write a new log — is reserved for fundamentally broken event shapes.

## References

- Greg Young, *A Decade of DDD, CQRS, Event Sourcing* (talk at DDD Europe 2016) — the canonical retrospective on the pattern's evolution and the trade-offs teams have learned. https://www.youtube.com/watch?v=Ivd_Dq3jP-w
- Greg Young, *Versioning in an Event Sourced System* (2014) — the canonical treatment of the schema-evolution problem and the upcaster pattern. https://leanpub.com/esversioning
- Martin Fowler, *Event Sourcing* (bliki, 2005, updated 2017) — the high-level introduction, with the explicit framing of events as the source of truth and state as derived. https://martinfowler.com/eaaDev/EventSourcing.html
- EventStoreDB documentation — streams, persistent subscriptions, projections, and the operational model of a purpose-built event store. https://developers.eventstore.com/
- Apache Kafka documentation — the log as the unifying abstraction; the relationship between log compaction and event sourcing is in the docs on log compaction. https://kafka.apache.org/documentation/#compaction
- Axon Framework reference guide — `Snapshotter`, `EventUpcaster`, and the lifecycle of an event-sourcing application. https://docs.axoniq.io/reference-guide/
- Pat Helland, *Accounting for Computer Scientists* — frames double-entry bookkeeping as the original event sourcing and shows how the model maps onto modern systems. https://martinfowler.com/articles/accountingComputer.html

## Related Topics

- [Event Sourcing](./event-sourcing.md) — the shorter overview page.
- [CQRS Deep Dive](./cqrs-deep.md) — the pattern most often paired with event sourcing; the read-model machinery described here is CQRS's read side.
- [Event-Driven Architecture Deep Dive](./event-driven-architecture-deep.md) — the communication pattern that the event log feeds.
- [CDC and Outbox Pattern](./cdc-outbox.md) — for state-based systems that want to emit events atomically; the same problem event sourcing solves by construction.
- [Kafka](../messaging/kafka.md) — the broker often used as the event store, with the compaction caveat.
- [Distributed Transactions](./distributed-transactions.md) — why sagas (not XA) are the right consistency model across event-sourced aggregates.
