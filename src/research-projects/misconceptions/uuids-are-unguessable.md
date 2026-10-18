# "UUIDs are unguessable, so exposing them in URLs is safe"

## Overview

This page audits the access-control claim that hides inside an identifier
format: because resources are addressed by UUIDs, nobody can reach a record
without authorization, so the identifier can be pasted into URLs, emails,
and support tickets freely — and can even serve as the only gate. The claim
is true for exactly one member of the UUID family and false for the rest,
because "UUID" names a 128-bit *format* with eight defined versions, and
the unguessability property lives not in the format but in the entropy
source behind a specific version. UUIDv4, generated from a
cryptographically secure random source, carries 122 random bits and is
unguessable in the strongest practical sense. UUIDv1 carries a wall-clock
timestamp, a 14-bit clock sequence, and a node field that on typical hosts
is the interface MAC address — a counter wrapped around two known
quantities. UUIDv3 and v5 are deterministic hashes of a name: anyone who
can guess the name can *compute* the identifier. UUIDv7 is time-ordered
with 74 random bits. This page states the claim fairly, walks the version
arithmetic, and runs a live disproof that recovers the creation timestamp
from a v1 UUID in one line of Python.

## The Claim, Stated Fairly

The strongest common form is: "Our record URLs use GUIDs instead of
sequential integers, so the resources are unguessable — an attacker cannot
enumerate them, and sharing the link is safe." Stated this way, the claim is
not a strawman. It appears in security questionnaires that ask "are object
references enumerable?", in the design of unlisted share links, and in
thousands of APIs where the UUID in the path replaced an autoincrement ID
during a security push. The practice it encodes — unguessable reference
tokens as one factor against enumeration — is a real and recommended
technique.

The kernel is also historically grounded: UUIDv4 with a proper random
source really is unguessable, with a 122-bit space that no attacker can
search. The failure is that "UUID" is said while "v4 from a CSPRNG" is
meant, and the systems that get breached are the ones running v1 for
database-locality reasons, or v5 for reproducibility reasons, or v4 from a
seed that is not cryptographically secure, while the URL-sharing claim was
written against the v4 case.

## Verdict

**Incomplete.** The claim is true in the regime where the identifier is
UUIDv4 generated from a cryptographically secure random number generator,
and it collapses for every other common configuration. UUIDv1 identifiers
advance as a wall-clock counter with a fixed clock sequence and node for
the life of a boot, leak their creation time, and — where the node field
holds the interface MAC as the RFC default provides — reduce the
unguessable residue to 14 bits plus elapsed time. UUIDv3 and v5 are
computed from a namespace and a name, so their unguessability is exactly
the guessability of the name. UUIDv7 exposes its 48-bit timestamp in the
clear, leaving 74 random bits — still strong, but a different number than
the one the claim assumes. Above all, "unguessable" is an entropy property,
not an authorization system: an unguessable URL with no authentication,
logging, or revocation is a capability token that can be forwarded,
scraped from a referrer header, and never retired.

## Why People Believe It

Three forces keep the claim alive. First, the format is uniform: a v1 and a
v4 UUID look identical — the same 8-4-4-4-12 hex — and the version nibble
that distinguishes them (the first hex digit of the third group) is read by
no one. A team that migrated from v4 to v1 for index locality, or from
random to name-based for reproducibility, inherits URLs that still *look*
unguessable long after the property is gone.

Second, the winning case dominates experience. Most teams do run v4, most
v4 generators do use their platform's CSPRNG (Java's `UUID.randomUUID`,
Python's `uuid4`, and Go's `uuid.New` all route to cryptographic sources),
and most URLs are never attacked. A property that holds in the common case
is indistinguishable from a property of the format itself — until a code
audit finds `uuid1()`, or a pentester gets one identifier from a referrer
header and starts walking neighbors.

Third, the claim is usually made about *access*, which makes it feel
conservative. Saying "the ID is unguessable" sounds like saying "the door
is locked", and questioning it sounds like arguing for more security
spending. In fact the claim hides a category error: an unguessable
identifier is a capability, and capabilities need the surrounding machinery
— issuer, scope, expiry, revocation, audit — that the word "UUID" carries
nowhere in its 128 bits.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "UUIDs are unguessable" | UUIDv4 from a CSPRNG carries 122 random bits and is unguessable; the property belongs to the entropy source, not the format |
| "GUID in the URL is enough" | An unguessable reference is one factor; authorization, logging, expiry, and revocation are separate controls that the identifier does not provide |
| "v1 is fine, it looks random" | v1 is a 60-bit wall-clock counter plus 14 bits of clock sequence plus a node; within one boot the node is fixed and the time field increments |
| "v5 is random, it's hashed" | v3/v5 are deterministic hashes of a name; anyone who can guess the name computes the identifier — unguessability equals name guessability |
| "v7 is like v4" | v7 exposes a 48-bit Unix-millisecond timestamp, leaving 74 random bits — time-ordered by design, strong but not v4-grade |
| "Enumeration is the only threat" | Identifiers leak through referrer headers, logs, browser history, and screenshots; leaked v1 IDs reveal creation time and, with a MAC node, the host's interface |

The correct sentence: "An identifier is unguessable if and only if it
carries enough entropy from a cryptographically secure source — for UUIDs,
that means v4 (122 bits), or v7/v4-class randomness where ordering is
needed (74 bits after the timestamp). The version byte in the third group
tells you which world you are in, and 'unguessable' is a property of the
randomness, never of the format."

## Where It Breaks

**The v1 disproof, run live.** Generate three consecutive time-based UUIDs
in Python and read them:

```python
import uuid, datetime
a = uuid.uuid1(); b = uuid.uuid1(); c = uuid.uuid1()
print(a, b, c)
# 7c1320f4-cad9-11f1-8ae5-bdd403de972e
# 7c13214e-cad9-11f1-8ae5-bdd403de972e
# 7c132176-cad9-11f1-8ae5-bdd403de972e
epoch = datetime.datetime(1582, 10, 15)
print(epoch + datetime.timedelta(microseconds=a.time // 10))
# 2026-10-18 09:51:26.353842
```

Three observations, each fatal to the claim. The clock sequence and node
(`8ae5-bdd403de972e`) are identical across all three: within one boot,
62 of the 128 bits are constants. The leading time field advances in
lockstep with generation (`7c1320f4` to `7c13214e` to `7c132176` — 346 and
40 ticks of 100 nanoseconds between calls): the identifier is a counter.
And the timestamp decodes from the ID alone, with no system access, to the
wall-clock creation time to the microsecond. On hosts where the node field
carries the interface MAC as the RFC default provides, an attacker who
obtains one identifier of a host also learns its hardware address; where
the generator substitutes a random node (as this container did, flagging it
with the RFC's multicast bit), the IDs remain sortable proxies for creation
time. Either way, "unguessable" overstates a 14-bit clock sequence.

**The enumeration counterexample.** An invoice service addresses documents
as `/invoices/<uuid1>`. The identifiers never appear in any list endpoint
— the claim is satisfied as written. But the product emails invoice links,
and email clients leak the URL in the `Referrer` header when the invoice
page loads a third-party font. An attacker with one leaked identifier now
knows the generator: v1. Identifiers created in the same millisecond share
the timestamp; the unknown residue is the 14-bit clock sequence (often
constant per boot) — 16,384 candidates against an endpoint that returns
404 versus 200 as its only signal. At a modest 200 requests per second,
the neighborhood of one leaked invoice is enumerated in about a minute.
With v4, the same leak would give the attacker a 122-bit space; the
breach-relevant difference was never "UUID versus integer", it was "which
version".

**The computed identifier.** A tenant's API keys are v5 UUIDs derived as
SHA-1 of `"<namespace>|<customer-slug>"`. The identifiers are documented
as unguessable. But a v5 UUID is a deterministic function of its inputs:
an attacker who can guess slugs — company names, domain stems, `default`,
`test` — *computes* valid identifiers without touching the randomness at
all. Reproducibility, the reason v5 was chosen (stable IDs across
environments for fixtures and imports), is precisely the property that
destroys unguessability; the two goals are mutually exclusive by
construction.

**The capability inversion.** The sharpest failure is not in any version
but in the inference "unguessable, therefore access-controlled". A record
whose only gate is a v4 URL has: no authentication (any holder of the
string is authorized), no revocation (the link works forever), no audit
(who fetched it?), and no rotation (a leaked link cannot be invalidated
without changing the identifier everywhere). The sibling audit of
encryption-versus-access-control makes the same cut: a mechanism with one
property was sold as a different, larger property. Unguessability
contributes exactly one factor — resisting guessing — and the
authorization decision, the expiry, and the paper trail live outside it.

**What survives the audit.** The kernel remains valuable and worth keeping:
v4 identifiers from a CSPRNG are excellent unenumerable references, and
unguessable tokens are a legitimate layer against enumeration scanning.
RFC 9562's own security considerations point security-sensitive uses at
v4 for precisely this reason. The discipline the claim needs is small:
check the version byte of the identifiers you expose, confirm the random
source is the platform CSPRNG, and treat the unguessable identifier as one
factor beside authentication and authorization — never as the
authorization itself.

## Practical Implications

- Audit exposed identifiers by version byte, not by shape: the first hex
  digit of the third group names the version, and the security claim must
  match it (v4 or v7-class randomness; not v1, not v3/v5).
- Never let an unguessable URL be the only gate for sensitive resources;
  pair it with authentication, scope checks, and rate limits on the
  reference space.
- Design for identifier leakage as a normal event — referrer headers,
  logs, tickets — and keep a revocation story for any capability-style
  link (short-lived signed URLs, rotatable tokens).
- Prefer key-based v4 or v7 identifiers for exposed references and reserve
  v1 for cases that genuinely need its clock (and note that v1's ordering
  and MAC payload are themselves privacy decisions, documented in the
  RFC's privacy section).

## Interview Questions

### Why is UUIDv4 considered unguessable, and what exactly carries the property?

The 122 random bits (128 minus 6 for version and variant) drawn from a
cryptographically secure source. At 10^12 guesses per second, a search of
the 2^122 space (about 5.3 x 10^36 candidates) takes on the order of
10^17 years. The
property lives in the entropy source — the format is inert, which is why a
v1 UUID shaped identically does not share it.

### You see the identifier `3f2a1c9e-7b11-11ee-8c4f-0242ac110002` in a URL. What can you say about it without any other information?

The version nibble (first digit of the third group, `1`) says it is a
time-based v1 UUID: a 60-bit Gregorian timestamp, a 14-bit clock sequence,
and a node field (here ending in the MAC-shaped `0242ac110002`, the
multicast-adjusted form of a container interface address). It encodes its
creation time, its node is fixed per boot, and neighboring identifiers are
enumerable around any known one — so the "unguessable" claim is false for
it regardless of how random it looks.

### A team wants stable, reproducible identifiers across environments and unguessable public URLs. Can one UUID version serve both?

No. v3/v5 achieve reproducibility by hashing a namespace and name
deterministically, which makes the identifier computable by anyone who can
guess the name — the exact opposite of unguessable. v4 achieves
unguessability with fresh randomness, which is by definition
non-reproducible. The designs split the requirement: internal reproducible
v5 keys, external references that are fresh v4s mapped to them, accepting
that the mapping itself must be protected.

### What is the difference between using an unguessable identifier as a control and using authentication and authorization?

An unguessable identifier is a capability: whoever holds the string can
act, with no identity, no expiry, no audit, and no revocation.
Authentication establishes who is asking; authorization decides what that
identity may do on this resource; both produce logs and can be revoked.
Unguessable references are a useful anti-enumeration layer *underneath*
those controls, and a dangerous substitute for them.

## Key Takeaways

- "UUID" names a format with eight versions; unguessability is a property
  of the entropy behind v4 (122 bits) and partially of v7 (74 bits after a
  visible timestamp), and is absent in v1, v3, and v5.
- A v1 UUID is a wall-clock counter plus a fixed node: its creation time
  decodes from the identifier alone, and neighbors are enumerable around
  any leak.
- v3/v5 determinism is reproducibility, which is the enemy of
  unguessability — anyone who can guess the name can compute the ID.
- The version nibble is one hex digit away in every identifier you expose;
  audits and pentests start there.
- An unguessable reference is one factor against enumeration, never a
  substitute for authentication, authorization, expiry, and revocation.

## Cross-References

- [Why-Not Handbook: Snowflake vs UUID](../why-not-handbook/snowflake-vs-uuid.md)
  — the design decision this claim ignores: what time-ordered identifiers
  buy and cost relative to random ones.
- [Assumptions Hunt: Randomness & IDs](../assumptions-hunt/randomness-and-ids.md)
  — the hidden assumptions behind "the ID is random", including entropy
  sources and seeding, which decide whether this page's verdict applies.
- [System Design: ID Generation](../../interview/system-design/hld/id-generation.md)
  — the generation schemes (snowflake, ULID, UUID versions) as design
  options with their security and locality trade-offs.
- [Misconception: "The data is encrypted at rest, so access is controlled"](./encryption-at-rest-means-access-control.md)
  — the sibling category error: both claims sell one mechanism's property
  (cipher strength, identifier entropy) as a different, larger property
  (access control).
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- J. Davis, K. Peabody, P. Leach. *Universally Unique IDentifiers (UUIDs)*.
  RFC 9562, May 2024 — defines the versions (including v6, v7, v8), the
  version and variant bits, and the security and privacy considerations
  this page audits.
  <https://www.rfc-editor.org/rfc/rfc9562.html>
- P. Leach, M. Mealling, R. Salz. *A Universally Unique IDentifier (UUID)
  URN Namespace*. RFC 4122, July 2005 — the legacy specification whose v1
  timestamp/clock-sequence/node layout the live disproof decodes.
  <https://www.rfc-editor.org/rfc/rfc4122.html>
