# API Contract Assumptions: What "The API Returns What the Docs Say" Silently Promises

## Overview

"The API returns what the docs say" sounds like a claim about the server. It is actually a claim about a conversation between two independently deployed programs, and it silently assumes the conversation is stable while both sides change: that pages of results are cut from a fixed table, that `null` and "absent" mean the same thing, that rows arrive in an order that means something, and that every server-side change that looks additive is safe for clients that were compiled years ago. Each assumption fails in a way that is easy to demonstrate with a small table and hard to debug across an organizational boundary, because the failure appears on the client, after the server has "behaved correctly".

This chapter audits the family with the collection's five-step pattern. The pagination-shift counterexamples below were verified by direct simulation over a 20-row table (page size 5), so the shifted row lists are exact, not schematic. The design responses — cursor pagination, explicit schemas, consumer-driven contract tests — follow Google's AIP-158 pagination guidance, the GraphQL pagination model, and the Pact contract-testing documentation, all linked from the ledger.

## Assumption 1: "Pagination Is Stable Under Concurrent Writes"

### The taught rule

Fetch pages with `?offset=0&limit=5`, then `?offset=5&limit=5`, and so on, and you will walk the whole result set exactly once.

### The hidden assumptions

- Offset pagination defines page N as "rows N×limit through (N+1)×limit of the *current* table state". Between two fetches, the table can change, so "row 5" names a different item each time.
- Inserts before the cursor (or any ordering where new rows rank earlier) shift every subsequent row down, producing duplicates on later pages and pushing tail rows out of reach; deletes shift rows up, producing gaps — rows that are silently skipped, never returned to any page.
- The instability exists even without concurrent *writes* in the classic sense: any new data the ordering ranks ahead of the read position (newer timestamps, larger IDs in a descending feed) causes it. "The docs say offset works" is true and useless — the docs are describing a static table.

### Counterexample

Verified by simulation. A table holds rows with IDs 1–20, ordered by ID descending, page size 5. Page 1 (`offset=0`) returns 20, 19, 18, 17, 16. Three new rows (IDs 23, 22, 21) are inserted. Page 2 (`offset=5`) returns 18, 17, 16, 15, 14 — rows 16, 17, and 18 are delivered a *second* time. In the ascending direction, page 1 returns IDs 1–5; row 2 is deleted; page 2 (`offset=5`) returns 7, 8, 9, 10, 11 — so ID 6 is skipped entirely and never appears on any page the client fetches. Both failure shapes are purely positional: no data was corrupt, no query was wrong, and re-running the same export tomorrow yields a different set.

### What changes when the assumption is removed

Corrected statement: *offset pagination enumerates positions in a moving list; cursor (keyset) pagination enumerates items after a fixed marker, and only the latter composes with concurrent writes.* The fix, as standardized in Google's API Design Guide AIP-158 ("Pagination") and GraphQL's cursor-based connections: the server returns an opaque cursor encoding the last item's sort key, and the next query fetches items strictly after it — inserts elsewhere in the list become irrelevant, and deletes cost at most one "not found" rather than a shifted window. Cursor pagination requires a *total, stable* order (see Assumption 3) and does not support random access to "page 37", which is exactly the property that makes it stable; exports that need a snapshot as well as stability combine cursors with a transaction boundary, as covered in the isolation chapter.

### Consequences

"Sync everything into the data warehouse via offset pagination" is the canonical production bug of this family: nightly syncs silently drop rows deleted-rank items and duplicate others, and the corruption is discovered weeks later during reconciliation. The API-design interview follow-up "why do modern APIs use cursors?" expects exactly the two-row-shift demo above, not the word "stability" alone.

## Assumption 2: "Absent vs Null Is a Detail"

### The taught rule

`{"name": null}` and `{}` both mean "no name"; the client treats them the same and everything works.

### The hidden assumptions

- JSON distinguishes three states a field can be in — present-with-null, present-with-value, absent — and most type systems clients use distinguish at least two: JavaScript maps them to `null` vs `undefined`, Rust `Option<T>` vs missing field with a default, Go pointer vs zero value. Collapsing them in the server is a decision the client silently inherits.
- Patch semantics make the distinction load-bearing: JSON Merge Patch (RFC 7386) defines absent as "leave unchanged" and explicit null as "clear the field" — a client that treats absent as null will erase data it never intended to touch.
- Deserializers disagree by default: some reject unknown fields, some drop them; some fill defaults for absent fields, some surface "missing". The same JSON document parses to different objects depending on the client's library flags.

### Counterexample

A profile service exposes `PATCH /user` accepting merge-patch semantics. A mobile client builds its update payload by copying the fields it manages and *omitting* the rest — but its serialization library converts uninitialized optional strings to explicit `null` rather than omitting the key. The user's birthday, managed by a different team's screen, arrives as `"birthday": null` in every profile update, and per RFC 7386 the server clears it. No error is logged anywhere: the request was well-formed and the server did exactly what the standard says. The inverse shape fails too — a strict desktop client compiled against schema version 1 crashes on a version-2 response that adds a new enum value, because "additive on the server" is "unparsable" to a parser that validates exhaustively.

### What changes when the assumption is removed

Corrected statement: *field presence, null, and default are three separate channel signals; an API contract must say which the server sends, which the client must tolerate, and which Patch method maps to which semantics.* Practical discipline: define serialization rules centrally (always omit absent optionals, or always emit explicit nulls — pick one and enforce it), document patch semantics per endpoint (merge-patch's null-clears-vs-absent-keeps distinction is the point of RFC 7386), and configure deserializers deliberately (tolerate unknown fields; reject silently-dropped required ones). The deep-dive contract question "what does your client do with a field it has never seen?" is unanswerable without this discipline.

### Consequences

Most "the API broke our client" incidents in this family are not version changes at all — they are the three-state distinction leaking through a serializer nobody reviewed. The frontend track's JavaScript deep dive covers the null/undefined split on the client side; the interview API-design page treats error and field semantics as part of the contract, not implementation details.

## Assumption 3: "Ordering Is Guaranteed"

### The taught rule

The response list is in the order the database returns, or in "natural order" — the client paginates, diffs, and renders against it.

### The hidden assumptions

- An SQL query without `ORDER BY` has no defined order at all — not insertion order, not ID order; parallel plans and buffer-pool state make it vary run to run and replica to replica.
- Even with `ORDER BY`, ties in the sort key have no defined relative order: two rows with the same `updated_at` may swap positions across pages, across replicas, or across requests. A sort key without a unique tiebreaker is not a total order.
- Many serialization layers (unordered maps, sets, language-level nondeterministic map iteration such as Go's) scramble field or item order after the data layer did the right thing — the guarantee exists in the database and evaporates in the JSON.

### Counterexample

A feed endpoint orders by `updated_at DESC` with no tiebreaker, page size 50. Two posts share an `updated_at` (a common bulk import artifact). Page 1's last row is one of them; between fetches, a replica serves the next page and the twin sorts first on it — the same post appears on both pages, while a third post slips off both. The pagination instability of Assumption 1 and the ordering instability here compound: offset pagination over a non-total order is unstable twice over. The fix is mechanical: every ordered read gets a unique final tiebreaker (`ORDER BY updated_at DESC, id DESC`), which makes the order total and cursor pagination (which encodes that order) exact.

### What changes when the assumption is removed

Corrected statement: *unordered results and tie-broken sorts are different contracts; only a total order supports pagination, deduplication, and deterministic diffs.* Specify the order in the API contract itself (including the tiebreaker and the collation), and treat "the order is unspecified" as a legitimate but explicitly-marked contract — clients then know not to paginate against it.

### Consequences

The interview probe "your API paginates by timestamp and users report missing items — first debugging step?" should end at "check for ties and add a tiebreaker" rather than starting at the database. The database indexes chapter shows the index design that makes tie-broken sorts cheap.

## Assumption 4: "Additive Changes Are Backwards Compatible"

### The taught rule

Adding a field, adding an enum value, or adding a new error code is an additive, non-breaking change; per semantic versioning the minor version bumps and no client is harmed.

### The hidden assumptions

- Compatibility is a property of *every client program that previously worked*, including strict ones: a parser that validates enum values exhaustively, or a JSON Schema consumer with `additionalProperties: false`, breaks on additions. "Additive" means "additive under a tolerance policy the client may not share".
- Error codes are enumerated too: a client `switch` with a `default` branch that treats unknown codes as retryable-infra will misbehave the first time the server adds a new 4xx code that must not be retried (the retry-budget coupling from the timeout chapter).
- Numeric fields cross language boundaries as doubles in many stacks: a new 64-bit identifier field added "additively" arrives corrupted in JavaScript clients above 2^53 (verified bit-for-bit in the floating-point chapter — 9007199254740993 reads as 9007199254740992).
- Removing or renaming fields is never additive, and deprecation policies exist precisely because the period of overlap must be *scheduled*: Kubernetes documents a deprecation policy with minimum windows per stability level (API elements must keep working for a stated number of releases) — an explicit, public version of the promise most teams make implicitly.

### Counterexample

A payments API adds a new failure enum value `CARD_VELOCITY_EXCEEDED` alongside `INSUFFICIENT_FUNDS`. Version-1 SDKs generated from the old schema deserialize unknown enum values into an "invalid" state or throw; one client's error handler treats the throw as a network error and retries — a decision that must never happen for a declined-card class of error (the double-charge mechanics are in the retry chapter). Nothing about the change was non-additive on the server; the breakage happened entirely inside clients whose tolerance policy was "exhaustive and strict". The corrected rollout: define the tolerance rule in the contract ("clients must treat unknown enum values as a generic failure of the same HTTP class"), ship the new value only after SDKs default to that policy, and version the SDKs so strict parsers are an explicit, deprecated mode.

### What changes when the assumption is removed

Corrected statement: *a change is backwards compatible only relative to a stated client tolerance policy — the contract must define how unknown fields, unknown enum values, and unknown error codes are handled, and versioning (semver plus a deprecation window) schedules the exceptions.* The enforcement mechanisms are explicit schemas (OpenAPI for HTTP APIs; protobuf's unknown-field tolerance rules for RPC), and consumer-driven contract tests — Pact's model, where each consumer's expectations are verified against the provider before deploy — which turn "the docs say" into "every known client's expectations hold". The software-engineering testing page situates contract tests in the broader test pyramid.

### Consequences

In system-design interviews, "you need to add a field — what could break?" is the compatibility probe, and the strong answer names strict parsers, exhaustive switches, retry-misclassification of new error codes, and the 2^53 identifier trap. In production, the cheapest defense is cultural: write the tolerance policy into the style guide once, and let code review reject contracts that rely on undocumented client behavior.

## Interview Questions

1. **Why does offset pagination duplicate and skip rows under concurrent writes?** Pages are positional cuts of a moving list: inserts ahead of the read position shift rows down (duplicates on later pages, verified demo: 16/17/17/18 re-delivered), deletes shift rows up (ID 6 skipped forever). Cursor/keyset pagination anchors to the last item's sort key and is immune to both.
2. **What are the three states a JSON field can be in, and where does the distinction matter most?** Present-with-value, present-with-null, absent. It matters most in PATCH semantics: JSON Merge Patch (RFC 7386) defines absent as "unchanged" and null as "clear" — a serializer that emits explicit nulls for unset optionals silently erases data.
3. **Your paginated feed ordered by `updated_at` loses and duplicates posts with no writes in between. Cause?** Ties in the sort key: `updated_at` is not a total order, so equal-key rows can swap across pages and replicas. Add a unique tiebreaker (`id DESC`) and paginate by the composite key.
4. **Why is "additive change" not automatically backwards compatible?** Compatibility is defined by existing clients' tolerance policies: strict enum parsing, `additionalProperties: false`, exhaustive error-code switches, and doubles-everywhere JSON stacks (2^53) all break on additions. The contract must state the tolerance rule; versioning schedules exceptions.
5. **How do you make "the API returns what the docs say" checkable rather than aspirational?** Explicit schema (OpenAPI/protobuf) plus consumer-driven contract tests (Pact): each consumer's expectations run against the provider in CI, so a breaking change fails the *provider's* build before clients ever see it.

## Key Takeaways

- Offset pagination cuts positions from a moving list; cursor pagination anchors to items — concurrent writes make the difference between a corrupted export and a correct one.
- Field presence, null, and default are three signals; patch semantics (RFC 7386) make confusing them destructive, and serializer defaults choose for you if you do not choose.
- A sort key without a unique tiebreaker is not a total order; pagination, dedup, and diffs all silently fail without one.
- Backwards compatibility is relative to a stated tolerance policy for unknown fields, enum values, and error codes — write the policy down, enforce it with schemas and contract tests.
- 64-bit identifiers shipped as JSON numbers are corrupted above 2^53 in doubles-everywhere clients — a contract decision, not a client bug.
- Semver plus a scheduled deprecation window (Kubernetes' published policy is the reference model) is how the exceptions get handled without ambushes.

## Cross-References

- [Floating point](floating-point.md) — the 2^53 identifier problem, verified bit-for-bit.
- [Timeouts and retries](timeouts-and-retries.md) — why new error codes must not be misclassified as retryable.
- [API design (HLD)](../../interview/system-design/hld/api-design.md) — where contract decisions land in a designed system.
- [Testing (software engineering)](../../software-engineering/testing.md) — where contract tests sit in the test pyramid.
- [Database isolation](database-isolation.md) — snapshot boundaries for exports that need stability as well as pagination.
- [AIP-158: Pagination](https://aip.dev/158) — Google's API Design Guide pagination standard, from the source.
- [GraphQL pagination](https://graphql.org/learn/pagination/) — the connections/cursor model, from the source.
- [Semantic Versioning](https://semver.org/) — the versioning discipline assumed by compatibility arguments.
- [Kubernetes API deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/) — a public, scheduled deprecation contract.
- [Pact](https://docs.pact.io/) — consumer-driven contract testing, from the source.
