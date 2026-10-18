# Application Events vs Change Data Capture: Who Declares What Happened?

## Overview

Two pipelines can both deliver a stream of "facts" to downstream consumers: application-emitted events, where the code explicitly publishes "OrderPlaced" after committing its transaction, and log-based change data capture (CDC), where a connector tails the database's write-ahead or replication log and publishes every committed row change as a fact. The payloads can be made to look identical, which is why teams treat the choice as a transport detail. It is not. The choice is really **who owns the definition of truth**: the application, which knows intent but must be trusted to publish honestly and exactly once per fact; or the database's commit log, which cannot lie about what committed but knows nothing about meaning.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **application events carry intent and schema but sit outside the transaction, inviting the dual-write problem; CDC inherits transactional atomicity, ordering, and completeness from the log, but emits noise-level physical details that downstream systems must interpret.** The production answer is frequently the bridge pattern — the transactional outbox — where the application writes an event *in the same transaction as the state change*, and CDC carries it out. That hybrid, why it works, and the backfill question both pure models answer badly, are where the real engineering lives.

## Step 1: The Problem and Its Constraints

The abstract shape: a state change occurs in a database; other systems — caches, search indexes, analytics, other services — need to react. Constraints that decide the answer:

- **Atomicity between state and stream.** Must "the row changed" and "the event went out" succeed or fail together? Any yes-corner here eliminates the naive "publish after commit" design immediately.
- **Who may define the fact.** Is the event a business concept with a deliberate schema owned by a team (OrderPlaced v2)? Or is it acceptable — even preferable — for downstream to observe raw table deltas it filters and interprets?
- **Ordering and completeness requirements.** Does a consumer need every change, in commit order, including the ones from a manual SQL fix run by an SRE at 3 a.m.? Or is best-effort notification with occasional gaps tolerable?
- **Schema evolution surface.** Who coordinates the contract when a field changes — application teams across a registry, or a single pipeline owner who reshapes physical changes into stable projections?
- **Backfill and replay.** Will new consumers need history (all existing rows, not just today's changes)? Will existing consumers need to rebuild after a bug? The log supports this natively; application events rarely do.

## Step 2: The Mechanisms

### Application-emitted events

After (or before, or "around") the database write, application code publishes a record to a broker. The mechanisms that matter:

- **The dual-write problem is the defining hazard.** Commit the DB transaction, then publish: the process dies between the two, and the fact exists in the database but never in the stream — permanently, because the commit has no reminder attached. Publish first, then commit: the stream carries facts about transactions that roll back — lies. Neither ordering is safe; this is not a bug to fix but a structural hole, and the fixes (outbox, CDC-of-the-outbox) are attempts to *move the publish into the transaction's scope*.
- **Intent and schema ownership are the defining strength.** `OrderPlaced { order_id, customer_id, total, items }` says what happened *in the business's language*, is versioned deliberately (compatibility rules, registries — the mechanics in [schema registry](../../distributed/messaging/schema-registry.md) and the assumptions in [serialization compatibility](../assumptions-hunt/serialization-compatibility.md)), and can hide internal refactors. Downstream consumers subscribe to meaning, not storage.
- **Delivery semantics are the application's problem.** The broker ack certifies storage, not the transaction; at-least-once publishing plus crash-retry means duplicates that downstream must dedup. The delivery-contract analysis parallels [RPC vs message queues](./rpc-vs-message-queue.md).
- **Nothing enforces coverage.** Every code path that mutates state must remember to publish. A new service, a migration script, a bulk update — all silently unannounced. Completeness is a convention, enforced by review, forgotten under deadline.

### Log-based change data capture

A connector reads the database's replication/WAL stream (PostgreSQL logical decoding, MySQL binlog; the PostgreSQL mechanism is documented in its [logical decoding](https://www.postgresql.org/docs/current/logicaldecoding.html) chapter) and publishes each committed change as an event, typically through a platform like [Debezium](https://debezium.io/documentation/). The mechanisms that matter:

- **The log is the source of truth, so the stream inherits its guarantees.** Only committed transactions appear, in commit order, complete — including changes made by anything that touches the database: ORMs, scripts, other services, DBAs. The dual-write problem cannot occur for changes *of the database* because the publication *is* the commit's echo. The WAL's role as the atomicity engine itself is developed in [WAL internals](../../dbms/advanced/wal-internals.md) and [crash recovery](../../dbms/transactions/log-recovery.md), and the event-log/database-log kinship in the atlas page [event sourcing and WAL](../connection-atlas/event-sourcing-wal.md).
- **Ordering is real but scoped.** Per-table (and with careful configuration, per-key) order matches commit order — the guarantee application events cannot make at all, since independent producers interleave arbitrarily.
- **The events are physical by default.** Row deltas — column values, before/after images, table names, LSNs. Meaning is implicit: downstream must know that `status` going 2→3 means "shipped." Every refactor of the schema is, whether anyone wants it or not, a change to the public contract — schema evolution becomes a pipeline concern rather than a domain concern.
- **Snapshots and backfill are native.** A connector starts by snapshotting existing rows, then streams from the log position — new consumers get history automatically. Replay is rewinding the log (within retention). Application events would need a bespoke backfill job for each new consumer — the backfill-versus-livelock analysis in [zero-downtime migrations](../followup-tree/zero-downtime-migrations.md) applies directly.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Application events | Log-based CDC |
|----------|--------------------|---------------|
| Atomicity with state change | None by default — dual-write hole | Inherited from the commit log — publication follows commit |
| Coverage/completeness | Whatever code paths remember to publish | Everything that commits, including scripts and manual fixes |
| Payload semantics | Intent, in business language, deliberately versioned | Physical row deltas; meaning implicit in consumers |
| Schema ownership | Producer team, via registry and compatibility rules | Pipeline owner; every DDL is a de facto contract change |
| Ordering | None across producers; per-topic at best | Commit order per table/key; real causal order |
| Duplicates | At-least-once publish + crash retry → dedup needed | Connector restarts → re-emission from offsets → dedup still needed |
| Backfill/new consumers | Bespoke backfill jobs per consumer | Snapshot + log position, native |
| Database coupling | None — broker is the boundary | Strong: log format, replication slots, connector health |
| Write-path cost | One extra broker round trip per fact | Near zero for app; replication slot and log retention pressure |
| Characteristic failure | Silent gaps: the fact that never got published | Slot bloat: an unclaimed WAL slot pins log files until the disk fills |

The **silent gap vs slot bloat** pairing deserves the arrow drawn: each model's worst failure is the other's strength. Application events fail *quietly* — a missing publish is invisible forever unless a reconciliation audit exists, because nothing downstream knows a fact was owed. CDC fails *loudly and physically* — the unclaimed replication slot holds back WAL recycling, and PostgreSQL will fill the disk rather than break the slot's promise; but disk-full alerts page someone, whereas a missing event pages no one. CDC's failure to publish is a monitorable pipeline outage; application events' failure to publish is a semantic void.

## Step 4: When Each Wins

**Application events win** when: the fact is genuinely a business concept whose meaning lives in a team's head (OrderCancelled with reason codes); multiple storage engines are involved, so no single log holds the truth; consumers want stable, versioned contracts more than completeness; the write path already commits through an outbox, making atomicity moot. Event design is API design — the same contract-location reasoning as [normalize vs denormalize](./normalize-vs-denormalize.md), applied to streams: who pays for the mapping from storage to meaning.

**CDC wins** when: completeness and ordering are the requirement (caches, search indexes, analytics replicas, cache invalidation — where one missed update is a stale-word bug); changes come from heterogeneous writers (legacy code, scripts, third-party tools writing straight to the DB); new consumers need history without bespoke backfill; the database is, de facto, the system of record. This is the mechanics behind the data-pipeline placements in [Debezium](../../data-engineering/debezium.md) and the stream-processing systems in [stream processing](../../data-engineering/stream-processing.md); how such streams relate to batch windows is the sibling comparison [batching vs streaming](./batching-vs-streaming.md).

**The honest hybrid** — the production norm at scale: application events for intent-bearing facts *written to an outbox table inside the same transaction*, CDC carrying outbox rows (and, where wanted, raw table changes) to the broker. Atomicity from the log, meaning from the application.

## Step 5: Edge Cases and Counterexamples

- **The outbox pattern: the bridge, and its own sharp edges.** Write the event row and the state change in one local transaction; a relay (CDC connector or poller) publishes outbox rows and marks them. This dissolves the dual-write hole because the broker-facing publication is derived from a committed record — but it imports new problems: the outbox table grows until purged (a retention job is mandatory, and a mis-sized purge loop can throttle the very transactions it serves); ordering of outbox publication must respect commit order or consumers see cancels before creates (keyed by aggregate ID solves it); and delivery remains at-least-once — the outbox row is only *cleaned up* after confirmed publish, so duplicates are the design's normal output, not a bug. The canonical reference is the [transactional outbox pattern](https://microservices.io/patterns/data/transactional-outbox.html).
- **The 3 a.m. SQL fix that CDC caught and events missed.** An SRE corrected a mispriced order directly in SQL during an incident. Downstream caches, fed by CDC, updated; downstream analytics, fed by application events, never learned — the two stores now disagree, and every future reconciliation blames "the cache." The lesson: choose per *table*, not per system — if any writer other than your service can touch the data, application events alone cannot promise coverage.
- **CDC that was the wrong choice: analytics drowning in physical truth.** A team wired CDC straight into a consumer that had to reconstruct "OrderPlaced" from three table change-streams (orders, order_items, order_status_history), maintaining an in-consumer join with commit-order assumptions across tables. Every schema migration broke the reconstruction; the "simple connector" grew a distributed state machine. When the *meaning* requires a join across tables, that projection belongs in the pipeline (stream-table or KTable-style materialization, per [Kafka](../../distributed/messaging/kafka.md) semantics) or in an outbox event — not re-derived in every consumer.
- **Replication slot orphans.** A staging environment's CDC connector was decommissioned; the slot remained. With no consumer reading it, WAL accumulated for weeks until the disk filled and the *primary* refused writes. The dual-write problem's mirror image: the pipeline's health is coupled to the primary's storage even when no one consumes the stream. Slots need ownership, monitoring (lag in bytes), and an expiry policy — the durability assumptions documented in [storage durability](../assumptions-hunt/storage-durability.md).
- **Schema evolution flips the coupling.** With application events, adding a field is a producer-side compatibility exercise governed by the registry. With CDC, adding a column is invisible until a consumer's hard-coded column list misses it, and *renaming* one is a breaking change across every downstream projection. Teams that treat CDC as "schema-free plumbing" discover the schema lives on, undocumented, in consumers — the worst of both worlds.

## Step 6: Decision Framework

1. **Can anything other than your application write the tables in question?** Yes (scripts, legacy services, DBA fixes) → CDC must be in the pipeline; application events alone cannot promise coverage.
2. **Must event and state change be atomic?** Yes → outbox in a local transaction (then optionally CDC to publish it); naive publish-after-commit is disqualified.
3. **Do consumers need business meaning or physical completeness?** Meaning, versioned contracts → application events (via outbox); completeness, caching, indexing → CDC projections.
4. **Is per-key commit ordering required?** Yes → CDC (or keyed outbox publication); application events cannot deliver causal order across producers.
5. **Do new consumers need historical backfill regularly?** Yes → the log's snapshot-and-stream model wins; budget connector infrastructure accordingly.
6. **Default in doubt:** outbox inside the transaction, CDC as the transport, business-meaning events as the outbox's content — atomicity from the log, semantics from the application, and neither model's characteristic failure mode left armed.

## Interview Questions

1. **Explain the dual-write problem and why "publish after commit" doesn't fix it.** The commit and the publish are two systems' effects with no shared transaction. Die (or crash, or lose the network) between them and the fact lives in the DB but never reaches the stream — with no reminder, because the transaction is done. Publish-first imports the opposite lie (facts about rolled-back work). The fix moves publication inside the transaction's scope: an outbox row committed atomically, relayed afterwards.
2. **Why does CDC inherit completeness and ordering "for free," and what does it pay with?** The connector reads the same log the database itself uses for durability and replication, so only committed changes appear, in commit order, whatever wrote them. It pays with physical payloads (meaning implicit in consumers), schema coupling (DDL changes are contract changes), and pipeline infrastructure (slots, connector health, disk pressure from lagging slots).
3. **Design an event flow for "order shipped" that cannot silently vanish.** Order-state update and an outbox row in one transaction (same key for ordering); CDC or a polled relay publishes outbox rows at-least-once; consumer dedups by event ID; outbox purged only after confirmed publication; a reconciliation audit compares outbox age/max IDs against published offsets to catch pipeline stalls — the monitorable failure replacing the semantic void.
4. **When is raw CDC into consumers the wrong architecture even though atomicity is perfect?** When meaning requires joining several tables' streams or mapping storage encodings to domain states: every consumer re-derives the projection and inherits every schema migration. Put the projection in one pipeline layer or emit intent-bearing outbox events instead.
5. **A lagging replication slot filled the primary's disk. What was the root cause and the standing policy you now add?** A slot pins WAL until its consumer reads it; a decommissioned/failed consumer turns the pipeline's backlog into primary storage exhaustion — the database protects the slot's promise, not its disk. Policies: slot ownership and monitoring (retained-WAL bytes), expiration/removal automation, and alerting on slot lag as a primary-capacity risk.

## Key Takeaways

- The fork is **ownership of truth**: application events own intent but sit outside the transaction; CDC owns atomicity, completeness, and ordering but speaks in physical deltas.
- The dual-write problem is structural, not a bug class: any design that publishes outside the transaction's scope will eventually emit nothing-or-lies. The outbox pattern is the standard repair — the event becomes a row the transaction commits.
- CDC's failures are loud and physical (slot lag, disk pressure); application events' failures are silent and semantic (the fact never published). Choose based on which failure your monitoring and processes can actually see.
- Choose per table, not per system: if any writer besides your service touches the data, coverage demands CDC somewhere in the pipeline.
- The mature architecture layers them: application-defined events in an outbox, CDC as the transport, dedup and schema compatibility owned explicitly — atomicity from the log, meaning from the application.

## Cross-References

- [Event Sourcing and WAL: Connection Atlas](../connection-atlas/event-sourcing-wal.md) — the kinship between the database's log and the event log as system-of-record designs.
- [ACID Transactions: Follow-up Tree](../followup-tree/acid-transactions.md) — the transactional guarantees the outbox pattern leans on.
- [RPC vs Message Queues: Why-Not Handbook](./rpc-vs-message-queue.md) — the delivery-semantics fork for whatever carries these events.
- [Batching vs Streaming: Why-Not Handbook](./batching-vs-streaming.md) — when the resulting stream is processed incrementally vs in windows.
- [ETL vs ELT: Why-Not Handbook](./etl-vs-elt.md) — where CDC sits in data-pipeline architectures.
- [Normalize vs Denormalize: Why-Not Handbook](./normalize-vs-denormalize.md) — the storage-to-meaning mapping cost, applied to streams.
- [WAL Internals](../../dbms/advanced/wal-internals.md) and [Log Recovery](../../dbms/transactions/log-recovery.md) — the log mechanics CDC readers subscribe to.
- [Debezium](../../data-engineering/debezium.md) and [Stream Processing](../../data-engineering/stream-processing.md) — connector and consumer mechanics in depth.
- [Schema Registry](../../distributed/messaging/schema-registry.md) and [Serialization Compatibility: Assumptions Hunt](../assumptions-hunt/serialization-compatibility.md) — the contract side of event design.
- [Storage Durability: Assumptions Hunt](../assumptions-hunt/storage-durability.md) — the device-level assumptions behind WAL retention and slots.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
