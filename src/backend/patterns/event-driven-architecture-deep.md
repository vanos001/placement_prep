# Event-Driven Architecture Deep Dive

## Overview

Event-driven architecture, EDA, is a style in which services communicate by emitting *events* — immutable, named facts about something that happened — and reacting to them asynchronously. A service that owns a piece of state emits an event when that state changes; other services subscribe to the events they care about and update their own state, or trigger side effects, on receipt. There is no synchronous call from one service to another; the only coupling is the *contract* of the event itself. Martin Fowler's 2017 bliki entry "What do you mean by Event-Driven?" is the canonical short treatment, and Ben Stopford's *Designing Event-Driven Systems* (O'Reilly, 2018) and Jay Kreps's earlier *I Heart Logs* (2014) are the canonical long-form ones.

EDA is the architectural style that makes microservices viable at scale. It loosens the coupling between services — a producer does not need to know who consumes its events, or even if anyone does — at the cost of an unforgiving operational model: failures are silent, latencies are tail-heavy, and "the system is in some state" is now a question with multiple answers depending on which consumer you ask. The trade is worthwhile when the alternative is a synchronous call graph that fails as a unit.

## Producer/Consumer Model

An EDA system has three roles. A **producer** emits an event when its state changes. A **broker** (Kafka, NATS, Pulsar, Kinesis) durably stores the event and delivers it to whoever is interested. A **consumer** subscribes to a stream of events and reacts. The producer and consumer never talk directly.

```
   ┌─────────────┐   emit   ┌──────────────┐   deliver  ┌─────────────┐
   │  Producer    │ ───────▶ │   Broker     │ ─────────▶│  Consumer A │
   │ (Order svc) │  Order   │  (Kafka)      │  OrderPlaced└─────────────┘
   └─────────────┘ Placed   │  topic:      │           ┌─────────────┐
                            │  orders      │ ─────────▶│  Consumer B │
                            │  partitions: │  OrderPlaced└─────────────┘
                            │   12, RF=3   │           ┌─────────────┐
                            └──────────────┘ ─────────▶│  Consumer C │
                                                          └─────────────┘
```

The producer's job is to make a local state change *and* emit the event atomically — which in practice means the outbox pattern: write to your DB and an outbox table in the same transaction, then a CDC pipeline ships the outbox row to the broker. Without this, you get the dual-write problem: write to DB succeeds, emit to broker fails, and your system state contradicts its own events forever.

The consumer's job is to be **idempotent**: it must apply the side effect of an event exactly once, even if the broker delivers the event multiple times (which it will, because at-least-once is the practical delivery guarantee). Idempotency is typically achieved with a `processed_events` table keyed by the event's unique ID — if the consumer has already processed this ID, it skips. Exactly-once *delivery* is an illusion; exactly-once *effect* is achievable, and required.

## The Three Event Types

Fowler's 2017 article distinguishes three flavours of event, and which one you choose has dramatic consequences for your system.

### Event notification

The smallest event. "OrderPlaced(orderId=123)". The consumer, on receipt, calls back to the producer to fetch the full state. This is the most decoupled form: the producer does not commit to a particular event schema, and the consumer decides what data it needs at fetch time. The cost is a synchronous callback on the read path, which reintroduces the runtime coupling that EDA was supposed to remove. Use it when the consumer genuinely only needs to know "something happened" — e.g. an audit logger that records that an order was placed.

### Event-carried state transfer

The event contains the data the consumer needs: "OrderPlaced(orderId=123, customerId=456, total=99.00, items=[...])". The consumer can update its own state without calling back. This is the form used for the *cache invalidation* use case in microservices: service A caches a denormalised view of service B's data; when B emits a state-transfer event, A updates its cache. The cost is schema coupling — B's event is now a contract that has to be versioned.

### Entity events (event sourcing)

The event is the source of truth. State is derived by replaying the event stream. This is the most decoupled and the most demanding: it requires event sourcing (see the dedicated page), and is overkill for most integrations. Use it when audit, replay, and temporal queries are first-class requirements — financial systems, regulatory systems.

The trap is mixing them within one event: an event that contains some state and omits other state, requiring consumers to call back for the omitted part, is the worst of both worlds. Pick one flavour per stream and stick with it.

## Choreography vs Orchestration (Saga)

When a business process spans multiple services — an order placement that has to debit the account, reserve inventory, and charge the card — there are two ways to coordinate the work.

**Choreography**: each service emits an event, the next service reacts. No central coordinator. OrderService emits `OrderPlaced`; InventoryService consumes it, reserves, emits `InventoryReserved`; PaymentService consumes that, charges, emits `PaymentCharged`; OrderService consumes that, marks the order confirmed. The flow is the emergent property of the event subscriptions.

```
   choreography                          orchestration
   ─────────────                         ─────────────
   OrderSvc──OrderPlaced──▶InvSvc        OrderSvc ── placeOrder() ──▶ Orchestrator
                                                       │
   InvSvc──InventoryReserved──▶PaySvc                  ├─ 1. debitAccount  ──▶ AcctSvc
                                                       ├─ 2. reserveInv    ──▶ InvSvc
   PaySvc──PaymentCharged──▶OrderSvc                   ├─ 3. chargeCard    ──▶ PaySvc
                                                       │  (3 fails)
   (no central state;                  (3 fails)        ├─ compensate 2: releaseInv ──▶ InvSvc
    harder to visualise)                               └─ compensate 1: refundAcct ──▶ AcctSvc
```

**Orchestration**: a dedicated *saga orchestrator* (e.g. Temporal, Cadence, AWS Step Functions) issues commands to each service in order, awaits responses, and decides what to compensate on failure. The flow is explicit, debuggable, and visible in one place. The cost is the orchestrator itself, which is a piece of stateful infrastructure with its own failure modes.

The pragmatic rule: choreography for short flows (≤3 steps, ≤3 services), orchestration for everything else. Long choreographed flows are a debugging nightmare — there is no single place to see "where is this order in the pipeline?". Orchestration also makes compensation cleaner: the orchestrator knows the full state machine and can emit the right compensating actions; in choreography, each service has to remember what to compensate, which spreads the saga logic across the system.

## The Event Sourcing Link

EDA and event sourcing are frequently conflated but they are different things. EDA is a *communication* pattern — services emit events. Event sourcing is a *persistence* pattern — the service's own state is the result of replaying its events. A service can do EDA without event sourcing (most do: it emits `OrderPlaced` but stores its own state in a normalised `orders` table). It can do event sourcing without EDA (its event log is internal, no one else consumes it). When combined, the event store and the event bus become the same thing — the producer's events are both the source of truth and the integration stream — which is elegant but constrains the event schema heavily, because changing an event now breaks every consumer.

The rule of thumb: do EDA first, defer event sourcing unless you need audit, replay, or temporal queries. Event sourcing is a strict superset of complexity.

## Kafka, NATS, Pulsar: the Brokers

The three serious open-source brokers have distinct philosophies.

**Apache Kafka** (LinkedIn, 2011) is the de facto standard. It models a topic as an append-only log partitioned by key, with consumers tracking their own offset. Storage is on disk (a partition is a series of segment files); retention is time- or size-based, not consumer-driven. Strengths: throughput in the millions of events/sec, durable storage that lets you replay history, ecosystem (Kafka Connect, Kafka Streams, Schema Registry, ksqlDB). Weaknesses: operationally heavy (Zookeeper historically, KRaft now), no per-message TTL, no native request/reply (you fake it with a topic), consumer rebalances are slow and disruptive on large clusters.

**NATS** (Synadia, 2010) is a lightweight, Go-based broker built around the idea that "a message bus should fit in 30 MB of RAM". NATS core is fire-and-forget at-least-once with no persistence; NATS JetStream adds streams (Kafka-like logs) and work queues. Strengths: latency in the tens of microseconds, trivial to operate (single binary, no external deps), first-class request/reply, wildcards, and subject hierarchies. Weaknesses: smaller ecosystem, fewer connectors, less mature exactly-once semantics.

**Apache Pulsar** (Yahoo, 2016) is the architecturally cleanest of the three. It separates compute (brokers, stateless) from storage (BookKeeper bookies) and supports both queue semantics (ack-per-message) and log semantics (offset-based). Strengths: tiered storage to S3 natively, geo-replication built in, separate scaling of compute and storage, no rebalance pauses when a broker leaves (state is in BookKeeper). Weaknesses: smallest ecosystem, two systems to operate (brokers + bookies), fewer engineers in the market.

```
   feature                       Kafka       NATS/JetStream   Pulsar
   ──────────────────────────────────────────────────────────────────
   storage model                log on disk log + KV          log + BookKeeper
   broker state                 stateful    stateful          stateless
   partition rebalance          slow        fast              none (state in BK)
   throughput (msgs/s, single)  ~1M         ~500K             ~1M
   end-to-end latency           5-20 ms     0.05-2 ms         5-20 ms
   geo-replication              MirrorMaker manual           built-in
   tiered storage to S3         KIP-885     via tier store     native
   request/reply                no          yes                yes
   exactly-once                 yes         yes (newer)       yes
   ops complexity               high        low                medium-high
```

Pick Kafka when you need the ecosystem and you can afford a platform team to run it. Pick NATS when you are small, latency-sensitive, or operating at the edge. Pick Pulsar when geo-replication or tiered storage is a first-class requirement and you have the operational capacity.

## Eventual Consistency Is Fine

The biggest cultural shift in adopting EDA is accepting that the system is *eventually* consistent. After `OrderPlaced` is emitted, the inventory reservation, the payment charge, and the order-confirmation email happen *over the next second*, not in the same database transaction. From the user's perspective, "I placed an order" and the order appearing in their history may be 200 ms apart. If a service is slow, the gap widens.

This is fine *if the system is honest about it*. The user-facing API should reflect uncertainty: a `202 Accepted` instead of a `200 OK` after a state change, with the client polling or subscribing for the eventual outcome. The dashboard should show lag metrics — consumer offset lag in Kafka, queue depth in NATS. The on-call should be paged when lag exceeds a threshold, not when an individual event is slow.

What is *not* fine is silent divergence. If the inventory service is 30 seconds behind the order service, and the order service's `GET /orders/{id}` shows the order as placed but the inventory service's `GET /inventory/{sku}` still shows stock, the user has just seen an inconsistent view of the system. The fix is either: (a) serve the read from the same model that wrote it (no cross-service read after a write — read-your-writes consistency), or (b) accept the inconsistency and design the UI to mask it (show "processing" instead of "in stock").

## The Distributed Monolith Anti-Pattern

EDA's central promise is decoupling. The trap is building a system that *looks* decoupled — events flowing, services subscribing — but where every consumer must be deployed in lockstep with every producer, and a change to any event schema breaks everyone. This is the distributed monolith in event-driven clothing.

The symptoms:

1. **Synchronous request/reply over an event bus.** A producer emits a command event, blocks waiting for a reply event, and times out if the consumer is down. This is just RPC with extra steps and a broker in the middle; you have the latency of EDA with the coupling of RPC.
2. **Tight event schema coupling.** Every consumer parses every field of every event. A producer adding a field breaks consumers that haven't been redeployed. Schema Registry helps but does not solve this — it just makes the breakage predictable.
3. **Single-namespace events.** All events live in one namespace (`company.events.*`) and any team can publish anything. The result is a tangle of events where no one knows who owns what. A per-service namespace (`orders.events.*`, `payments.events.*`) makes ownership clear.
4. **Choreographed sagas with no observability.** A flow that spans six services, with no orchestrator and no trace, is impossible to reason about. Adding distributed tracing (OpenTelemetry, with the trace context propagated in a header on every event) is essential; without it, EDA is a black box.

The cure is discipline: versioned event schemas (Schema Registry + compatibility modes), explicit ownership of every stream, distributed tracing on every event, and a preference for orchestration over choreography once a flow exceeds three steps.

## Interview Questions

### Q: Why at-least-once delivery and not at-most-once or exactly-once?

At-most-once drops events on failure, which is unacceptable for state-changing events. Exactly-once delivery is impossible end-to-end without exotic two-phase commit; the broker cannot know whether the consumer processed the event before crashing. At-least-once plus idempotent consumers gets you exactly-once *effect*, which is what you actually want. Kreps's argument in *Designing Event-Driven Systems* is the canonical explanation.

### Q: How do you handle event schema evolution?

With a schema registry and a compatibility policy. The producer registers a schema (Avro, Protobuf, JSON Schema) with the registry; the registry enforces that new schemas are *backward-compatible* (new consumers can read old events) and *forward-compatible* (old consumers can read new events — usually achieved by treating unknown fields as ignorable). Breaking changes require a new topic or a parallel-publishing period.

### Q: When is EDA the wrong choice?

When the system has a synchronous user expectation that you can't relax. A login flow where the user waits for "you are logged in" cannot tolerate 1 s of consumer lag. A payment authorisation that must succeed before the user leaves the page is the same. In those cases, keep the synchronous path, emit an event afterwards for downstream side-effects. EDA belongs on the *after-the-fact* side of a transaction, not on the critical path of a synchronous user request.

## References

- Martin Fowler, *What do you mean by Event-Driven?* (bliki, 2017) — the three event flavours (notification, state-transfer, entity events) and the trade-offs. https://martinfowler.com/articles/201701-event-driven.html
- Martin Fowler, *EventDrivenCollaboration* (bliki) and the older *Enterprise Integration Patterns* reference — the foundational vocabulary. https://martinfowler.com/eaaDev/EventDrivenCollaboration.html
- Ben Stopford, *Designing Event-Driven Systems* (O'Reilly, 2018, free PDF from Confluent) — the modern canonical book; chapters on contracts, choreography, and event sourcing as the integration pattern. https://www.confluent.io/ebooks/designing-event-driven-systems/
- Jay Kreps, *I Heart Logs* (O'Reilly, 2014) — the short book that argued the log is the central data abstraction of the modern stack. https://www.oreilly.com/library/view/i-heart-logs/9781491912511/
- Apache Kafka documentation — producer/consumer model, log compaction, exactly-once semantics. https://kafka.apache.org/documentation/
- NATS documentation — JetStream streams, work queues, and the at-least-once delivery model. https://docs.nats.io/nats-concepts/jetstream
- Apache Pulsar documentation — broker/bookie separation, tiered storage, geo-replication. https://pulsar.apache.org/docs/concepts-overview/
- Confluent Schema Registry — the practical answer to schema evolution. https://docs.confluent.io/platform/current/schema-registry/index.html

## Related Topics

- [Event-Driven Architecture](./event-driven.md) — the shorter overview page.
- [Event Sourcing Deep Dive](./event-sourcing-deep.md) — the persistence pattern that, combined with EDA, makes the event log the integration stream.
- [CQRS Deep Dive](./cqrs-deep.md) — the read-model pattern most often paired with EDA.
- [CDC and Outbox Pattern](./cdc-outbox.md) — how to make a state change and an event emit atomic.
- [Kafka](../messaging/kafka.md) — broker deep dive.
- [NATS](../messaging/nats.md) — broker deep dive.
- [Saga](../../dbms/transactions/saga.md) — the distributed-transaction pattern, in both its choreography and orchestration flavours.
- [Exactly-Once Delivery](./exactly-once.md) — the semantics of delivery and effect.
