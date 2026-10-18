# Idempotency Assumptions: What "Retries Are Safe" Silently Promises

## Overview

Retries are the standard response to every failure the network produces, and the safety case for them is stated in one word — idempotent — whose meaning is assumed rather than checked: that the methods marked idempotent by the specification actually are, that a message cannot arrive twice, that an idempotency key turns any operation into a retryable one, and that a deduplication store, once deployed, closes the issue. Each assumption breaks with money attached — a payment executed twice, a webhook double-applied, a replay job re-charging customers whose deduplication records expired — and each leaves the same signature: no error anywhere, just two rows where one should be.

The deeper pattern is that *idempotency is a property of an operation's effect on state, not of the transport, the method name, or the flag set on the request*. The specification defines what "idempotent" means for a method's *intended* effect; achieving it for a specific operation requires the operation itself to be designed — a natural key or a supplied idempotency key, a unique constraint at the storage layer, and a deduplication record whose lifetime covers the retry horizon. The sibling [timeouts and retries](timeouts-and-retries.md) chapter audits when retries happen and how they amplify; this chapter audits whether they were safe. Both chapters follow the collection's five-step pattern, and both trace back to the same root audit: the [network-distributed assumptions](network-distributed.md) chapter's "retries are safe" fallacy, given here the full treatment because it is the assumption with the most direct financial consequences in the collection.

## Assumption 1: "GET, PUT, and DELETE Are Idempotent Because the Spec Says So"

### The taught rule

HTTP defines idempotent methods: GET, PUT, and DELETE can be retried freely, because the [specification (RFC 9110)](https://www.rfc-editor.org/rfc/rfc9110.html) says the intended effect of multiple identical requests is the same as a single request — so retry logic can branch on the method name.

### The hidden assumptions

- The spec defines the *intended* effect, not the implemented one: idempotence is a property a method has when the server actually implements it that way, and the specification's own framing ("considered idempotent... in the sense that the intended effect remains the same") describes a convention, not an enforcement mechanism. A PUT to `/counters` or a GET that fires side effects breaks the convention while remaining perfectly valid HTTP.
- Retrying DELETE does not repeat the deletion, but it is not a no-op for the caller: the second request returns 404, and a client that treats 404 as "operation failed" (rather than "already done") converts a successful idempotent retry into a user-visible error.
- Idempotence says nothing about *responses*, only effects: two identical GETs can return different bodies (the resource changed between them), so caching layers and conditional logic that assume response equality are assuming something the spec never promised.
- The spec's scope ends at one request: a retry of a *sequence* (create-then-charge, reserve-then-commit) is not idempotent just because each member is — compound operations need their own key covering the whole sequence.

### Counterexample

A client library retries on 404 for "transient" upstream errors. A user deletes a file; the DELETE succeeds, the UI fires the same DELETE again on a slow response, receives 404, and the retry layer — reading 404 as the upstream's generic failure code — retries twice more and surfaces "deletion failed" for a deletion that succeeded. The operation was idempotent; the *status-code interpretation* was not, and the spec never promised it would be. The corrected contract: distinguish effects from responses, map "already done" (404 after DELETE, duplicate-key on insert) to success in the retry layer, and attach an idempotency key to any compound operation rather than leaning on per-method semantics.

### What changes when the assumption is removed

Corrected statement: *method idempotence is a server-side convention about intended effects — a useful default for retry design, but unverifiable from the method name alone, silent about response equality, and inapplicable to request sequences.* The auditable version of the rule: for each retried request, name the exact server-side effect, name the response the second attempt returns, and confirm the client maps that response to "already done" rather than "failed".

### Consequences

"What makes a method idempotent, and what does the spec actually guarantee?" is the interview opener; the senior answer separates effect semantics from response semantics and volunteers the DELETE-404 trap, which is also the cheapest code-review check in this chapter.

## Assumption 2: "A Message or Request Arrives At Most Once"

### The taught rule

The infrastructure delivers each message once: the broker acknowledges, the network is TCP, and a "sent once" flag at the producer means the consumer processes once.

### The hidden assumptions

- Delivery guarantees are layered and additive: TCP eliminates corruption and reorders, not application-level duplicates; an application retry after a lost *response* (the request succeeded, the ack timed out) creates a second, application-level copy that no transport layer will ever deduplicate.
- The broker's default is exactly the assumption's opposite: Apache Kafka's documented [delivery semantics](https://kafka.apache.org/documentation/) describe at-least-once as the behavior produced by producer retries — duplication is the *designed* outcome when reliability is prioritized, and exactly-once requires the idempotent producer and transactional features to be explicitly enabled and scoped.
- At-most-once is available everywhere and used almost nowhere, because it means "drop on failure": the only way to guarantee a message never arrives twice is to guarantee it sometimes never arrives.
- "Exactly-once delivery" as commonly quoted is really exactly-once *processing* — delivery plus deduplicated effects — which moves the problem from the broker to the application's state layer, where Assumption 4 lives.

### Counterexample

An order service publishes `charge(card, 49.99)` to a queue; the broker acks, but the ack is lost in a network blip, the producer retries, and the broker stores both copies under different offsets. Both copies are delivered during a consumer-group rebalance; the consumer charges the card twice. Every layer did what it promised: TCP delivered both writes, the broker stored both, delivery was at-least-once, and the producer's retry was correct by its own configuration. The defect was the design's assumption that the layering produced a guarantee nobody offers. The corrected contract: treat duplicate arrival as the normal case, give every operation an identity (order id, payment intent id), and enforce uniqueness at the storage layer — the producer's deduplication settings reduce transport-level duplicates but cannot deduplicate application retries.

### What changes when the assumption is removed

Corrected statement: *the only universal delivery guarantee is at-least-once (with retries) or at-most-once (without them); exactly-once is an application construction — operation identity plus atomic dedupe-plus-effect — not a transport property, and "exactly-once delivery" in vendor documentation means "enough machinery for you to build exactly-once processing".* Design reviews should therefore ask "what happens when this message arrives twice?" before asking "how do we prevent it?".

### Consequences

The interview probe "does Kafka give exactly-once delivery?" is answered correctly by separating delivery from processing and naming the enabling machinery — and by noting that the default path, producer retries, is the duplication engine.

## Assumption 3: "An Idempotency Key Makes Retries Safe"

### The taught rule

Attach an idempotency key to the request; the server deduplicates on it; retries are now safe. Most payment APIs document exactly this pattern, and the design is copied everywhere.

### The hidden assumptions

- The key must identify the *logical operation*: generated once per operation by the client and reused across retries of that operation. A key generated per attempt is a unique nonce — it deduplicates nothing — and a key generated once per process lifetime collides across unrelated operations.
- The server must store more than the key: deduplication needs the key, the request's identity (payload fingerprint or operation parameters), and the first response — so a replayed duplicate can be answered with the *original result* instead of re-executing or erroring. The [Stripe idempotent-requests contract](https://docs.stripe.com/api/idempotent_requests) is the reference design: keys retained for 24 hours, reuse of a key with a different payload rejected with an error rather than silently executed.
- Keys need scope and lifetime: scoped per client (or API key) so tenants cannot collide, retained longer than the retry horizon — a 24-hour retention window versus a reconciliation job that retries a failed charge 48 hours later is a double charge with a 24-hour fuse.
- Concurrency is part of the contract: two identical requests racing (timeout client retries while the first still runs) must hit a unique constraint at the storage layer, not a check-then-insert in application code; and the key store itself becomes state with its own availability story.

### Counterexample

A billing worker retries a failed `$49.99` charge with an idempotency key — correctly. But the retry fires 26 hours after the first attempt: the provider's 24-hour retention has expired, the key is unknown, and the charge executes as new. The deduplication layer worked exactly as documented; the *retry horizon* was wider than the *key lifetime*, and nothing in the design compared the two numbers. The corrected contract: key lifetime must strictly exceed the maximum retry horizon (including replay jobs and manual re-runs), keys scoped per client, payload-bound to reject reuse with different parameters, and enforced by a unique constraint so the race between concurrent duplicates lands on the database rather than on luck.

### What changes when the assumption is removed

Corrected statement: *an idempotency key is a lease on uniqueness with a scope, a lifetime, and a stored result — safe only while the retry horizon fits inside the lifetime and the enforcement is atomic.* The audit for any key-based design is four numbers: key retention, maximum retry delay, replay-job age, and manual re-run age — if any number exceeds retention, the design has a fuse.

### Consequences

"What does the idempotency key actually store?" separates real designs from flag-setting: key, fingerprint, result, timestamp, scope. The follow-up "when does it expire, and what retries outlive it?" is the senior probe, and it is answerable only if the design wrote the numbers down.

## Assumption 4: "Duplicate Suppression Equals Correctness"

### The taught rule

The deduplication store is the fix: every processed operation is recorded by key, and processing skips anything already recorded. With the store in place, duplicates are handled.

### The hidden assumptions

- Record-then-process is a sequence, not a transaction: recording *before* processing risks losing the operation on a crash between record and effect (skipped forever); recording *after* risks duplicates on a crash between effect and record (re-executed). Both windows are the process-death scenarios the [process-shutdown assumptions](process-shutdown-assumptions.md) chapter audits — SIGKILL lands between any two instructions.
- The dedupe check and the effect must be atomic — in one database transaction, or via an outbox where the effect is a queued consequence of the recorded intent — otherwise the store is another check-then-act race, the pattern the [concurrency and scheduling](concurrency-and-scheduling.md) chapter audits generally.
- Deduplication state decays: TTLs expire, partitions roll, and the record that would suppress a duplicate is gone when the duplicate finally arrives — which is precisely what happens during the replay scenarios the [queue-dead-letter-replay atlas](../connection-atlas/queue-dead-letter-replay.md) maps: reprocessing a week-old backlog meets a 24-hour dedupe window and re-executes everything.
- Suppression is per-key, not per-fact: two different keys that describe the same real-world operation (retry after client restart with a regenerated key, the same payment submitted through two integrations) bypass the store entirely — uniqueness must eventually rest on a domain constraint (the ledger's uniqueness on order id), not only on the transport key.

### Counterexample

A webhook consumer processes payments: dedupe check on the event id, then apply, then insert the id into a 24-hour-TTL dedupe table. A processor outage causes a replay of two-day-old events; every id has expired, the consumer re-applies all of them, and customers with subscriptions are double-charged — while the dedupe table shows a healthy record of the *recent* events it did suppress, so the monitoring built on it stays green. The structural fix is to move the uniqueness into the domain: a unique constraint on the payment's external id in the ledger, with the apply step as `insert ... on conflict do nothing` in the same transaction as the money movement — atomic, permanent, and independent of any TTL the replay window can outlive.

### What changes when the assumption is removed

Corrected statement: *duplicate suppression is only as strong as its atomicity (check-plus-effect in one transaction), its permanence (keyed to the domain, not to a TTL shorter than the worst replay), and its scope (per real-world operation, not per transport key); a dedupe store that fails any of the three is a cache of recent successes, not a correctness mechanism.* The domain constraint — the unique row in the ledger — is the load-bearing element; everything else is optimization.

### Consequences

The interview question "where exactly do you put the dedupe check?" has one good shape: inside the transaction that performs the effect, on a unique domain constraint. The [webhook-delivery atlas](../connection-atlas/webhook-delivery.md) works the same pattern from the delivery side, and the [message-queues follow-up](../followup-tree/message-queues.md) escalates the consumer-side questions that lead here.

## Interview Questions

1. **DELETE is idempotent — so why did the client report a failed deletion?** The second DELETE correctly returned 404 ("already done"), and the retry layer mapped 404 to failure. Method idempotence governs effects, not responses; retry logic must map "already done" responses to success.
2. **Does Kafka provide exactly-once delivery?** No transport does in the useful sense: the default with retries is at-least-once, at-most-once means dropping on failure, and exactly-once processing is an application construction — operation identity plus atomic dedupe — built on the broker's idempotent-producer and transactional machinery.
3. **A retried charge executed twice despite an idempotency key. What four numbers do you check?** Key retention lifetime, maximum retry delay, replay-job event age, and manual re-run age. The charge ran at 26 hours against a 24-hour retention: the retry horizon outlived the key.
4. **Where does the dedupe check go, and why is a separate dedupe table insufficient?** Inside the same transaction as the effect, on a unique domain constraint. A separate check-then-act store races (crash between check and effect), decays (TTL shorter than replay age), and scopes by transport key rather than by the operation the domain cares about.

## Key Takeaways

- Idempotence is a property of an operation's effect on state; method names, transport guarantees, and request flags are conventions to be verified, not guarantees to be consumed.
- The universal delivery choices are at-least-once (duplicates by design) and at-most-once (loss by design); exactly-once processing is built, with operation identity, payload-bound keys, and atomic enforcement.
- An idempotency key is a lease: scoped per client, bound to the payload, stored with its result, and only as safe as its retention relative to the widest retry horizon that can reach the operation.
- Suppression must be atomic with the effect and permanent at the domain layer — a unique constraint in the ledger outlives every TTL that replay jobs, outages, and manual re-runs can overrun.
- The audit question for every retried operation is the same: what happens on the second arrival, at the storage layer, under concurrency, after the dedupe record has expired — answered with numbers, not intentions.

## Cross-References

- [Timeouts and retries](timeouts-and-retries.md) — the sibling audit of when retries fire and how backoff and budget arithmetic shape them.
- [Network and distributed assumptions](network-distributed.md) — "retries are safe" as a named fallacy, the root this chapter gives the full financial treatment.
- [Process shutdown assumptions](process-shutdown-assumptions.md) — SIGKILL between any two instructions: the crash windows that make record-then-process sequences leak.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — check-then-act races in general; the dedupe store is one instance.
- [Distributed lock assumptions](distributed-lock-assumptions.md) — fencing and claim semantics, the same tools that make re-execution detectable.
- [Follow-up tree: message queues](../followup-tree/message-queues.md) — the consumer-side escalation chain that arrives at delivery semantics and dedupe design.
- [Connection atlas: queue dead-letter replay](../connection-atlas/queue-dead-letter-replay.md) — replay as the workload that meets expired dedupe records.
- [Connection atlas: webhook delivery](../connection-atlas/webhook-delivery.md) — the delivery-side twin: at-least-once webhooks meeting consumer idempotency.
- The [HTTP semantics specification (RFC 9110)](https://www.rfc-editor.org/rfc/rfc9110.html), Stripe's [idempotent requests documentation](https://docs.stripe.com/api/idempotent_requests), and Apache Kafka's [delivery-semantics documentation](https://kafka.apache.org/documentation/) are the primary sources above; all were fetched and verified this session.
