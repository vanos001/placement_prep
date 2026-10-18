# Push vs Pull: Webhooks vs Polling, Broker Push vs Consumer Pull, Origin-Pull vs Origin-Push

## Overview

"Push or pull?" is asked at every layer of the stack, and the same answer keeps being rediscovered: the question is really **who owns the pacing**. A pull system lets the receiver decide when work arrives — the consumer fetches when it is ready. A push system lets the sender decide — the producer transmits when data exists. Everything else (latency, liveness, backpressure, firewall behavior) follows from that ownership decision, which is why the same trade-off reappears for webhooks vs polling, for Kafka's consumer-pull model vs Pulsar's broker-push model, for a CDN fetching from origin vs origin uploading to the CDN, and for an IMAP client sitting in [IMAP IDLE](https://datatracker.ietf.org/doc/html/rfc2177) waiting for the server to say "you have new mail".

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **pull is paced by the consumer and pays in detection latency; push is paced by the producer and pays in backpressure and receiver-side buffering.** Neither dominates; hybrids (long polling, webhooks-plus-verification) exist precisely because each pure model fails in a characteristic way.

## Step 1: The Problem and Its Constraints

The abstract shape: a producer generates events at rate *r*; a receiver consumes them; both are distributed, independently failing, and connected by a network that may be one-way at times. Constraints that decide the answer:

- **Liveness bound.** "How long may pass between an event existing and the consumer acting on it?" A 60 s polling interval means an average 30 s / worst-case 60 s detection delay — a *contractual* bound, not a performance accident.
- **Consumer capacity.** Can the receiver always absorb work when it arrives? If the consumer's throughput is variable (GC pauses, deploys, a downstream database having a bad day), the pacing owner matters enormously.
- **Connectivity direction.** Consumers behind NAT, corporate firewalls, or browsers cannot *listen*; producers behind firewalls cannot *be reached*. Physical reachability constrains the pacing owner before any performance argument does.
- **Event rate and waste budget.** At one event per hour, a 1 s poll makes 3,600 fruitless requests per event. At 10,000 events per second, polling overhead is noise; the question becomes who absorbs bursts.

## Step 2: The Mechanisms

### Polling (consumer-paced pull)

The consumer asks "anything new?" every *T* seconds. The mechanisms that matter:

- **Detection latency is a property of *T*, not of the network.** Expected delay *T*/2, worst case *T* — an explicit, schedulable bound. Gmail-style [IMAP IDLE](https://datatracker.ietf.org/doc/html/rfc2177) exists because full-polling mailboxes was wasteful: IDLE is a long-lived connection on which the *server* pushes an untagged `EXISTS` response. But even IDLE mandates re-issue every 29 minutes — long-lived connections die silently — so the hybrid keeps a pull-shaped fallback clock underneath a push-shaped fast path.
- **Waste scales as 1/*T* per source**: each empty poll costs a full request/response cycle (CPU, connection overhead, a cursor or max-id query). At high *T* the waste is small; at the low *T* needed for near-real-time latency, poll volume approaches event volume — the classic reason polling does not scale to low latency.
- **Natural backpressure.** If the consumer is slow, it simply polls less often or processes a backlog on its next poll. The consumer's loop is the governor; nothing upstream needs to know it slowed down.

### Webhooks / broker push (producer-paced push)

The producer (or broker) transmits to a receiver-registered endpoint the moment data exists. Mechanisms:

- **Delivery is immediate but *reliability* becomes the sender's retry policy.** A webhook POST that times out — did the receiver get it? The producer retries per its policy, and the receiver must deduplicate, because at-least-once delivery is the only honest contract under timeouts and retries (see [timeouts and retries](../assumptions-hunt/timeouts-and-retries.md)). GitHub and Stripe both document retried, unordered webhook delivery — order is *not* a push guarantee the receiver may assume.
- **Backpressure ownership is the crux.** Under push, the sender keeps sending unless the receiver can refuse. TCP provides per-connection flow control, but a webhook receiver that returns 200 and then works through the item has accepted work it cannot refuse later; a receiver that returns 5xx triggers the producer's retry policy — now the *retry storm* mechanism: the receiver is down, every producer retries on timeout, and when it recovers it faces the accumulated retry wave of every producer simultaneously. Exponential backoff with jitter mitigates, but the pacing authority sits on the wrong side of the failure.
- **Reachability tax.** Webhooks require a publicly reachable HTTPS endpoint, TLS, signature verification (HMAC of the payload with a shared secret), and a firewall hole per producer. Polling requires only outbound connectivity. Behind restrictive NAT — or for browsers — push toward the client is impossible without an intermediary, which is why browsers live on long polling and WebSockets rather than raw webhooks.

### The broker middle ground: Kafka pull vs Pulsar push

- **Kafka consumers pull.** The consumer asks the broker for batches when it is ready; flow control is the consumer's fetch loop. The rationale in the [Kafka documentation](https://kafka.apache.org/documentation/#design) is exactly the reasoning above: consumer-paced design lets each consumer control its own pace and keeps broker-side state minimal. The cost shows at the latency tail: waiting on `fetch.min.bytes` adds latency, eager fetching wastes requests (the poll trade-off relocated inside the protocol), and consumer-group rebalances (see [kafka consumer rebalancing](../../distributed/messaging-internals/kafka-consumer-rebalancing.md)) pause consumption because a pull model has no broker-side channel to say "stop partition 3".
- **Pulsar pushes.** Brokers deliver to connected consumers up to a receiver queue size; consumers grant permits via a shared [flow control window](https://pulsar.apache.org/docs/concepts-messaging/#flow-control), so the broker paces itself against an explicit credit. The pushed model gives the broker enough state for features pull makes awkward — per-message acknowledgment timeouts, redelivery tracking, negative acknowledgments — but broker and consumer now share a live, stateful session, and a stuck consumer turns broker memory into the buffering surface.

### CDN origin-pull vs origin-push

Same fork, third costume. Origin-pull (the default): a cache miss fetches from origin on demand; stale content serves until TTL expiry, so origin sees (1 − hit ratio) × traffic in bursts synchronized with expiry — the thundering herd that stale-while-revalidate exists to damp (see [cache patterns](../../sre/cache-patterns.md)). Origin-push (uploading assets, or an invalidation API): origin pays immediately and controls when content changes, but must know every edge's state. The reconciliation rule: **push immutable hashed artifacts with long TTLs; pull (cache) everything whose freshness the origin cannot predict.**

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Pull (polling) | Push (webhooks/broker-push) |
|----------|----------------|------------------------------|
| Detection latency | Expected *T*/2, bound *T* — explicit | Near-zero in the good case; retry-policy-dependent in the bad case |
| Throughput overhead | Empty polls ∝ 1/*T* per source | Per-event connection/channel overhead |
| Backpressure owner | Consumer (implicit, robust) | Producer, unless a credit/permit protocol exists (then shared) |
| Failure under slow consumer | Consumer falls behind privately | Buffer bloat: broker memory or sender retry queue grows; receiver OOM or retry storm |
| Failure under receiver outage | No event emitted; next poll catches up | Retry storms; duplicate delivery after recovery; possible producer memory exhaustion |
| Reachability requirement | Outbound only | Public endpoint, TLS, signature verification; impossible toward NAT'd clients |
| Ordering/duplication contract | Whatever the cursor query gives | At-least-once, unordered, dedup required |
| State location | Cursor at consumer | Session/permit state at broker; subscription config at receiver |

The **slow-consumer buffer-bloat** mechanism deserves the arrow drawn: push moves the buffering *location* to the sender. A push system with a stuck consumer must stop delivering (backpressure — needs credit-based flow control), buffer unboundedly (broker memory exhaustion — the broker becomes the failure), or drop (data loss). Pull never faces this trilemma because the consumer's fetch request *is* the backpressure signal. This is the mechanism-level content of [backpressure](../connection-atlas/backpressure.md): **the component that paces must be the component that knows it is overloaded — and only the receiver knows that.**

## Step 4: When Each Wins

**Pull wins** when: consumers are heterogeneous and unpredictable in capacity (each paces itself); sources vastly outnumber consumers or events are sparse (poll waste is small at low frequency); receivers cannot be reached (NAT, browsers); simplicity of the failure story matters (worst case: stale data, not a retry storm). Kafka's consumer-pull choice is the existence proof that at extreme scale, consumer-paced fetching plus a durable log is the robust core.

**Push wins** when: liveness latency is contractual (payments webhooks, chat, new-mail notifications); event rates are high enough that polling waste dominates; receivers are stable services with capacity signals to expose (credit windows); the sender legitimately owns delivery policy (retries, dead-lettering). Pulsar's push model exists to make broker-side per-message bookkeeping (ack timeouts, selective redelivery) tractable; webhooks exist because SaaS providers cannot poll ten million tenants.

**The honest hybrid menu** — where production systems actually live:
- **Long polling**: the client's request hangs until data or timeout — poll-shaped reachability, push-shaped latency ([RFC 6202](https://datatracker.ietf.org/doc/html/rfc6202) catalogs the known issues: proxy timeouts, reload storms, resource pinning).
- **Webhooks + verification fetch**: the webhook says "something changed" (or carries a signed reference); the receiver pulls the actual state from a GET endpoint. Push latency, pull authority — at-least-once push duplication becomes idempotent pull. This is the standard hardening of naive webhook designs.
- **IMAP IDLE pattern**: a pushed notification over a long-lived connection *plus* a mandated slow re-poll, because push channels die silently; liveness is anchored by the pull clock.

## Step 5: Edge Cases and Counterexamples

- **Push with no credit system: the broker becomes the OOM.** A Pulsar consumer that stops reading does not slow the broker politely; unacked messages accumulate against its receiver queue, then in broker memory. The counterintuitive result: the *broker* — the component assumed stable — is the first to die, taking all tenants on that broker with it. Pull-based Kafka with the same stuck consumer shows a growing lag number and a healthy broker; the failure is visible, bounded, and isolated to the consumer's own partition assignment.
- **Polling that outperforms push: the sparse-event case.** One status change per hour across 10,000 devices. Push requires 10,000 always-on inbound endpoints (each a TLS surface and a NAT traversal); polling every 60 s requires 10,000 outbound requests per minute against a trivial cursor query. The "inefficient" design has lower latency, lower cost, and no inbound attack surface. Efficiency claims about push assume event density the workload may not have.
- **The webhook retry storm after a deploy.** A receiver's 30 s deploy returns 503 for every in-flight webhook; every producer's retry timer fires in the same window; on recovery the receiver faces a synchronized retry wave plus normal rate — a self-inflicted DDoS. Mitigations are all pacing-authority moves: producer-side backoff *with jitter*, receiver-side accept-then-process (202 + internal queue — moving the buffer onto the receiver deliberately), or push-notification-plus-pull reconciliation so retries are harmless.
- **NAT/firewalls make the choice for you.** Mobile clients, browsers, and anything behind symmetric NAT cannot receive pushes. The industry answer (push services, WebSocket gateways) is not really push — it is *a pull-shaped long-lived connection to a proxy that fans out*. "Push to clients" is always "push to an intermediary the client holds open"; the reachability constraint never disappears, it is paid somewhere.
- **IMAP IDLE's 29-minute rule is a liveness lesson.** Even with a push channel, IDLE clients must re-issue IDLE because middleboxes drop idle flows without error. Push systems need a pull-shaped dead-man clock or they silently stop being live — "the socket was open" is not a liveness guarantee (see [timeouts and retries](../assumptions-hunt/timeouts-and-retries.md) for the general form).

## Step 6: Decision Framework

1. **Can the receiver be reached inbound?** No → pull or long-poll/WebSocket-gateway; the question of push shape is already settled.
2. **Is detection latency contractual (< seconds)?** Yes → push-shaped notification (webhook, IDLE-style); then immediately add dedup + verification fetch.
3. **Is consumer capacity variable or unpredictable?** Yes → consumer-paced pull (or explicit credit-based flow control); do not build producer-paced delivery without a permit system.
4. **Are events sparse relative to the desired latency?** (Events per hour ÷ desired latency ≫ 1) → polling is cheaper and simpler; do not apologize for it.
5. **Who must own delivery policy (retries, DLQ, per-message acks)?** Receiver-side state needed → broker-push with permits; consumer-side cursor enough → pull from a durable log.
6. **Default in doubt:** pull from a durable log, add a push notification channel for liveness, reconcile via verification fetch — the hybrid is not a compromise; it is how the failure modes of both pure models are individually disarmed.

## Interview Questions

1. **Why does Kafka have consumers pull instead of the broker pushing?** Consumer-paced fetching makes backpressure implicit (the fetch *is* the flow-control signal), keeps broker state minimal, and lets heterogeneous consumers each control their own pace. Push would force the broker to track live per-consumer capacity — the slow-consumer problem — and buffer on the broker when consumers stall.
2. **Your service consumes webhooks; a partner claims "guaranteed delivery, in order." What do you build anyway?** Deduplication on event IDs (at-least-once is the honest contract under timeout-then-retry), ordering-insensitive handling or sequence-based reconciliation, signature verification, and a verification fetch against their API as the source of truth — push notifications are hints; state is pulled and reconciled.
3. **A polling system needs 10× better detection latency. Why is "just lower the interval 10×" often wrong, and what do you do instead?** Poll volume scales as 1/*T*: 10× the requests, often drowning the very database being polled (each poll is a query). Better: long polling (hang the request until change — latency without poll volume), a pushed notification channel with a pull fallback, or cursor-based cheap polls (HEAD/ETag, max-id) so waste per poll shrinks.
4. **Explain buffer bloat in a push messaging system as a failure located in a specific component.** With producer-paced push and no credit protocol, a stalled consumer's undelivered messages accumulate in the broker's memory (or its disk page cache pressure). The broker — shared, presumed stable — exhausts first and fails other consumers too. The fix is moving pacing authority to the consumer: credit/permit windows (Pulsar's flow control), or pull.
5. **Why do CDNs default to origin-pull instead of having origins push content to edges?** Origin-pull requires the origin to know nothing about edge topology; each cache decides what to store and absorbs miss bursts with staleness and revalidation tools. Push would make origin responsible for predicting edge demand and every edge's state — coupling it to cache topology. Push is reserved for what origin *does* know: immutable assets and explicit invalidations.

## Key Takeaways

- The real variable is **pacing ownership**: pull = consumer-paced, push = producer-paced. Latency, backpressure, failure blast radius, and reachability requirements all derive from it.
- Pull's weakness is bounded and explicit (detection latency ≤ interval, wasted polls); push's weakness is unbounded and shared (buffer bloat on the sender, retry storms on recovery) unless a credit protocol moves pacing back to the receiver.
- Reachability is a physical constraint that decides before performance does: NAT'd clients pull or long-poll through an intermediary — that is not an optimization choice.
- Hybrids are the production norm: long polling, webhooks + verification fetch, IDLE-style push with a mandated re-poll clock. Each hybrid attaches a pull-shaped liveness anchor or dedup path to a push-shaped fast path.
- "Push is faster" and "pull is inefficient" are workload claims, not laws: sparse events make polling the cheaper, lower-latency, smaller-attack-surface design.

## Cross-References

- [Backpressure: Connection Atlas](../connection-atlas/backpressure.md) — the queue-full path and who owns the pacing when buffers fill.
- [Timeouts and Retries: Assumptions Hunt](../assumptions-hunt/timeouts-and-retries.md) — the retry-storm and duplicate-delivery mechanics behind push failure modes.
- [Kafka](../../distributed/messaging/kafka.md) and [Kafka log internals](../../distributed/messaging-internals/kafka-log-internals.md) — the durable-log pull model in depth.
- [Pulsar](../../distributed/messaging/pulsar.md) and [Pulsar internals](../../distributed/messaging-internals/pulsar-internals.md) — the broker-push model with credit-based flow control.
- [Kafka Consumer Rebalancing](../../distributed/messaging-internals/kafka-consumer-rebalancing.md) — how a pull model handles membership changes.
- [Backpressure and Flow Control](../../distributed/messaging-internals/backpressure-and-flow-control.md) — credit systems and slow-consumer handling across brokers.
- [Pub/Sub](../../distributed/messaging/pubsub.md) — the general push family tree.
- [Circuit Breakers](../../distributed/microservices/circuit-breakers.md) — the receiver-side defense against retry storms.
- [Advanced I/O](../../network-programming/advanced-io.md) — polling vs event-driven I/O: the same fork at the syscall layer.
- [Cache Patterns](../../sre/cache-patterns.md) — origin-pull herds and their operational mitigations.
- [WebSocket](../../networks/http/websocket.md) — the persistent-connection channel that makes client-push feasible.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
