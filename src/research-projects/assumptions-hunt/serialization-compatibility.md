# Serialization and Compatibility Assumptions: What "It's Just JSON" Silently Promises

## Overview

Every service boundary is also a format boundary, and the handoffs at that boundary run on assumptions nobody wrote down: that adding a field cannot break an old reader, that a JSON number is a number, that field order in an object is meaningless, and that compatibility is something you check once, on deploy day, between the two current versions. Each assumption fails differently — a reused Protobuf field number corrupts stored rows, a 64-bit id routed through a JavaScript client comes back off by a few units, a signed webhook starts failing after a serialization library upgrade reorders keys, and a rolling deploy runs old readers against new writers in both directions for the entire rollout window.

The deeper pattern is that *compatibility is a property of the format's rules plus the deployment's timeline*, and the formats disagree about which rules they give you. Protobuf hands you field numbers and makes you promise never to reuse them; JSON hands you no schema at all, so convention and validation carry everything; schema registries try to make the rules executable. None of these mechanisms protects a team that believes the assumptions above, which is why the failures are common and quiet — nothing crashes except the consumers, often only for a fraction of traffic. This chapter audits the four with concrete failure mechanics, in the collection's five-step pattern, complementing the sibling [API contracts](api-contracts.md) chapter: that one audits the published promise; this one audits the bytes underneath it.

## Assumption 1: "Adding a Field Is Backward Compatible"

### The taught rule

Adding a field is the safest schema change there is: old readers ignore what they do not know, new readers accept both versions. Ship it.

### The hidden assumptions

- Wire formats differ on what "ignore" means. Protobuf skips unknown fields but *keeps the field number sacred*: adding a field is safe exactly once, with a number that was never used before. Reusing a retired number — after the old field's data still sits in a database, a Kafka topic, or an archive — makes old bytes decode as the new field's type, silently and plausibly wrong.
- "Old readers ignore new fields" is a default, not a law: strict parsers, deny-unknown-field validation (some JSON Schema configurations, many statically typed client SDKs), and hand-written `if key in payload` logic all reject or mishandle the addition. Compatibility is between the field and the *configured* reader, not the reader in the abstract.
- Removal is where the asymmetry bites: deleting a required field (proto2 `required`) makes every stored message permanently unparseable, which is why the Protobuf guidance frames `required` as effectively forever. Renaming a JSON field is a removal-plus-addition to every consumer that never saw a schema registry.
- Enums deserve their own trap: appending an enum value is "additive", but a reader with a closed enum — older bindings switch unknown values to a default or throw — converts the addition into a crash or, worse, into the default value of a *different* meaning.

### Counterexample

A Protobuf message has field 4, `rating`, an int32. The team removes it in v2 and, eight months later, adds `rating_v2` as an int32 and reuses number 4 because the schema file "had a spare slot". Rows written by v1 still store the old field under number 4, so a v3 reader deserializing an old row decodes those bytes as `rating_v2` — same wire type, no error, just a number from the wrong era presented as the new field, feeding a recommender trained on the new scale. The corruption is invisible because wire-type-compatible reuse is precisely the case the format cannot detect. The standard defenses exist for exactly this: mark retired numbers and names `reserved` in the schema (the compiler then rejects reuse), never change a field's type in place, and treat field numbers as a permanent API surface — the rules the official Protobuf [proto3 guide](https://protobuf.dev/programming-guides/proto3/) is built around.

### What changes when the assumption is removed

Corrected statement: *additive evolution is a format-specific contract — Protobuf: fresh field numbers, `reserved` for the dead, append-only enums; JSON: unknown-field tolerance must be verified in every strict reader, because nothing in the format enforces it.* The check is bidirectional: new-reader-meets-old-data and old-reader-meets-new-data are different tests, and only the second is usually run.

### Consequences

In interviews, "why does Protobuf make you reserve field numbers?" is a five-minute question with a production story inside it: the wire format is a position-addressed record, so a number is an address, and reusing an address re-points old bytes at a new meaning.

## Assumption 2: "JSON Numbers Are Precise"

### The taught rule

JSON has a number type; send an integer as an integer and it arrives intact. A decimal is a decimal.

### The hidden assumptions

- JSON specifies numbers as *decimal text*, and [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) explicitly allows implementations to set limits on range and precision — the format guarantees the syntax, not the values. What the number means is decided by whichever parser reads it.
- The dominant parser decision is IEEE 754 double: JavaScript's `JSON.parse`, and many dynamic clients, reduce every number to 53 bits of significand. An int64 larger than 2^53 − 1 (9,007,199,254,740,991) silently rounds to a neighboring representable value — which customer's id breaks is decided by the parity of their id.
- Precision loss is one-directional and quiet: the producer sent exact int64 text; the consumer's parser discarded bits at read time — no error, no truncation marker, just a number off by a small amount in a field that happens to be an identity or foreign key.
- Decimals for money inherit the same path: `19.99` survives as text but any arithmetic performed client-side runs in doubles, and the [floating-point assumptions](floating-point.md) chapter's 0.1 + 0.2 failure arrives through the API boundary even when the backend never used a float.

### Counterexample

A platform generates int64 event ids (snowflake-style, comparable to the [Snowflake scheme](../why-not-handbook/snowflake-vs-uuid.md)) and ships them in JSON as bare numbers. A JavaScript dashboard reads `{"event_id": 9007199254740993}` and parses it as the double `9007199254740992`; a "view this event" deep link built from the parsed value returns the wrong event or none. The failure is user-dependent — ids below 2^53 work, later ones do not — so it surfaces as "the dashboard breaks for new events only", misdirecting debugging toward data instead of toward the parse. The corrected contract: transmit 64-bit integers as strings at the wire boundary (Protobuf's int64 survives JSON only if the producer quotes it), convert at the edges, and never let an id participate in client-side arithmetic.

### What changes when the assumption is removed

Corrected statement: *a JSON number is a decimal literal whose meaning is fixed by each reader's parser; the safe wire contract for values beyond double precision or below decimal-representability is explicit typing — strings for int64 ids, decimal-safe encodings for money, integers kept as integers end-to-end where every consumer guarantees it.* Verify the chain, not the hop: the producer's type system is irrelevant to what the consumer's parser does with the bytes.

### Consequences

"Why does your API send ids as strings?" is the interview probe, and the senior answer quotes the 2^53 boundary, names the RFC's precision caveat, and notes the failure is data-dependent — the property that makes it survive testing.

## Assumption 3: "Field Order Doesn't Matter"

### The taught rule

JSON objects are unordered maps; `{a, b}` equals `{b, a}` semantically, so serialization order is an implementation detail.

### The hidden assumptions

- Semantically true for data models — and false for every mechanism that hashes, signs, or deduplicates *serialized bytes*. A signature computed over "the JSON" is over one particular byte string; any re-serialization (different key order, different whitespace, different number formatting) breaks verification.
- The standard fix — canonicalization — is itself subtle: [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) (JSON Canonicalization Scheme) fixes key ordering, number formatting, and string escaping precisely so that two conforming serializations of the same data are byte-identical. Teams that skip it and "just sort the keys" inherit number-formatting and escape divergences they cannot see.
- Duplicate keys are the adversarial edge: JSON does not define which duplicate wins, and parsers disagree (last-one-wins is common, first-one-wins exists). A signature validated by one parser over `{"amount":1, "amount":100}` while a second parser reads the other value is a real request-smuggling shape at format boundaries.

### Counterexample

A payment provider signs webhooks: the payload is JSON, the signature is HMAC over the raw body, and the consumer's verify step parses the JSON, re-serializes it "for normalization", and compares HMACs. The provider upgrades its serializer and starts emitting keys in a different (still valid) order; every consumer doing the parse-and-reserialize dance fails verification — or, to stop the false alarms, switches to comparing against a *re-serialized* canonical form they control, at which point an attacker exploits the duplicate-key divergence above to make the verifier sign one document and the handler execute another. The corrected pattern is strict: HMAC the exact received bytes (or parse once, canonicalize per RFC 8785, and sign the canonical form on *both* sides), and reject duplicate keys at the door.

### What changes when the assumption is removed

Corrected statement: *any bytes-level mechanism (hashing, signing, deduplication, caching by body) requires a canonical serialization agreed by every producer and consumer; without one, "field order doesn't matter" is true only for readers that never compare bytes.* Choose per use: sign raw bytes as transmitted; canonicalize per RFC 8785 where a logical comparison is needed; treat duplicate keys as malformed input, not a puzzle.

### Consequences

The interview probe "what do you sign when you sign a JSON payload?" unfolds this assumption completely: raw bytes versus canonical form, the re-serialization trap, and the duplicate-key differential. It is also a durable code-review check: code that hashes a value it just parsed-and-rebuilt is carrying this assumption into production.

## Assumption 4: "Schema Evolution Is a Deploy-Day Concern"

### The taught rule

When you ship a schema change, you run the migration, check the two versions against each other, and you are done — compatibility was verified at deploy time.

### The hidden assumptions

- A rolling deploy is a version-skew window in *both* directions: old readers meet new writers (unknown fields, Assumption 1) and new readers meet old writers (fields the new reader expects are absent or null). Both mixes run in production for the entire rollout, and the "current versus current" test matches neither.
- The skew window does not close at deploy end: persisted data — event logs, Kafka topics, database rows, object storage — is read by consumers deployed *months later*. For a topic with a year of retention, the "deploy" of a schema change is distributed across a year of consumers that have not been written yet.
- Clients you do not control pin old schemas indefinitely: mobile apps installed and never updated, third-party integrations cached against your exported schema, internal consumers whose upgrade cycle is quarterly. The oldest deployed reader, not the newest, defines the compatibility floor.
- "We tested it" usually means one pair (v_n, v_n+1). Compatibility is a property of the whole *history*: a change compatible with yesterday's schema can still be incompatible with the schema a two-year-old archived message was written under.

### Counterexample

A producer adds a required-in-practice field (`status_v2`) to events on a Kafka topic with 30-day retention. Rolling deploy succeeds — the integration test ran v_new producer against v_new consumer. Two weeks later, a replay job re-processes the backlog from before the deploy: the replay's consumer (v_new) meets pre-deploy messages where `status_v2` is absent, and the handler's assumption that the field is always present NPEs the pipeline at 3 a.m. The failure had nothing to do with deploy-day; it lived in the *retention window*. This is the exact problem Confluent's schema registry compatibility modes (BACKWARD, FORWARD, FULL) exist to gate: each new version is checked against the registered history before it can be used — deploy-day hope becomes a registration-time rule. The [message-queues follow-up tree](../followup-tree/message-queues.md) reaches the same design point from the consumer side.

### What changes when the assumption is removed

Corrected statement: *compatibility is enforced against the oldest reader that can ever meet the newest writer — the deployment fleet during rollout, the retention window of every store, and the pinned clients you do not operate — and it must be checked at schema-registration time against the version history, not tested at deploy time against one pair.* Practically: write new readers tolerant of everything the registered history can produce; write new writers to emit nothing the oldest registered reader mishandles; and let a registry (or an equivalent CI gate over the schema repo) be the enforcement point.

### Consequences

In system-design interviews, "what happens the day after the deploy?" separates deployment thinking from data-lifecycle thinking: the expected answer names the retention window, the replay job, and the unpinned mobile client. The distributed-systems framing — the deploy is a range, not a moment — is the same insight the [network-distributed assumptions](network-distributed.md) chapter develops for code version skew generally.

## Interview Questions

1. **Why must Protobuf field numbers be reserved after removal, and what exactly corrupts if you reuse one?** Wire bytes are position-addressed by field number and wire type; reusing a compatible number makes stored old bytes decode as the new field — plausible, undetectable garbage. `reserved` makes the compiler enforce the promise.
2. **An int64 id breaks in a JavaScript client but not in the backend. Where did precision go, and what is the wire fix?** JSON numbers are decimal text; JS parses to IEEE 754 doubles with 53-bit significands, rounding values above 2^53 − 1. Fix: transmit int64 as strings (or a typed format), convert at the edge, and never arithmetic on ids client-side.
3. **Your signed webhooks started failing after a library upgrade that only reordered JSON keys. Diagnose and give two correct fixes.** The signature covered one serialization; the verifier re-serialized and compared, so order broke it. Fixes: HMAC the exact received bytes, or canonicalize both sides per RFC 8785; reject duplicate keys to close the parser-differential hole.
4. **A rolling deploy tested clean, yet a replay job crashed two weeks later. Classify the failure.** Forward compatibility against the retention window: new reader met old-writer data missing the assumed field. Fix: registration-time compatibility gating against schema history (registry modes) plus readers tolerant of the entire registered history.
5. **What does "additive" mean per format — JSON versus Protobuf?** JSON: nothing in the format enforces unknown-field tolerance, so "additive" holds only against verified-lenient readers; Protobuf: additive means fresh field numbers, append-only enums, and never re-typing a field in place.

## Key Takeaways

- Wire compatibility is format-specific: Protobuf gives you field numbers and forbids their reuse; JSON gives you nothing and delegates to reader tolerance you must verify. "Additive" is not a property of the change but of the change plus every reader's configuration.
- A JSON number is decimal text interpreted by each reader; values beyond 2^53 or decimal-exact money need explicit wire typing (strings, decimal encodings), because the RFC's precision caveat is where silent rounding lives.
- Bytes-level mechanisms (signatures, hashes, dedup) need canonical serialization — RFC 8785 or raw-bytes signing — and duplicate keys must be treated as malformed, or the format's undefined behavior becomes an attacker's tool.
- Schema evolution spans the deployment range, the retention window, and every pinned client; compatibility is a property of schema *history*, enforced at registration time against the oldest reader that can ever meet the newest writer.
- The recurring failure signature is quietness: every mechanism above produces wrong data or wrong control flow without an error at the layer that made the change.
- Version skew is bidirectional during rolling deploys; test both directions (new-reader-meets-old-data, old-reader-meets-new-writer) as first-class cases.

## Cross-References

- [API contracts](api-contracts.md) — the contract-level twin of this chapter: additive changes, pagination, and error codes as published promises.
- [Floating-point assumptions](floating-point.md) — the numerics underneath "JSON numbers are precise".
- [Network and distributed assumptions](network-distributed.md) — version skew between machines as the general case this chapter's rolling-deploy failure instantiates.
- [Follow-up tree: message queues](../followup-tree/message-queues.md) — the consumer-side escalation path that arrives at schema-registry compatibility modes.
- [Event sourcing and WAL atlas](../connection-atlas/event-sourcing-wal.md) — persisted event logs as the reader-from-months-later compatibility floor.
- [gRPC](../../networks/http/grpc.md) — Protobuf as gRPC's default serialization, where field-number discipline is a service contract.
- [Storage durability](storage-durability.md) — stored bytes outliving the systems that wrote them, the persistence half of the evolution timeline.
- RFC 8259 (JSON, including the precision caveat), RFC 8785 (JSON Canonicalization Scheme), and the Protobuf [proto3 programming guide](https://protobuf.dev/programming-guides/proto3/) (field-number, reserved, and enum rules) are the primary sources for the format claims above.
