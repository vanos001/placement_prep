# Follow-up Tree: URL Shortener

## Overview

"Design a URL shortener" is usually the first system-design interview a candidate sees: the base design fits on one whiteboard, and every interesting question lives in the follow-ups — how codes are minted, what a redirect status commits you to, and what a 100:1 read ratio does to the architecture. The full worked design lives in [URL Shortener (System Design)](../../interview/system-design/url-shortener.md); this page is the escalation companion, as [Rate Limiter Design](./rate-limiter-design.md) is for its own opener.

## The Opening Question

**"Design a URL shortener."**

The expected core answer states *requirements and their numbers before architecture*. Functional: create a short code for a long URL; redirect code → URL; and the optional trio — custom aliases, expiry, analytics — each a follow-up in disguise. Non-functional, quantified: 100M new URLs per day is ~1,200 writes per second; redirects outweigh creations roughly 100:1 — ~120,000 reads per second, several times that at peak; five years at ~500 bytes per record is ~90 TB; the 80/20 skew means a ~10 GB cache covers the hot working set. The read:write ratio is the headline: the design reduces to "a global hash table with a fast read path."

Why this answer is correct: every later rung bends exactly one of these numbers. "Now handle 100× traffic" is unanswerable without a baseline, and the analytics rung exists because redirects are reads that *want* to be writes.

## Follow-up 1: How Do You Generate the Short Code?

**What it tests:** whether you can design an ID space: uniqueness, length, alphabet, and what each guarantee costs.

**How to reason:** the code is a key into a global map — ask how many codes you need, who guarantees uniqueness, and what outsiders can learn from the codes.

**Answer.** Seven characters over base62 spans 62⁷ ≈ 3.5 trillion slots — comfortably above the ~180 billion codes five years of 100M/day produces. Two families mint them. **Counter, base62-encoded:** no collisions by construction, no write-time checking; the price is coordination (a single counter node is a bottleneck and failure domain — the fixes are pre-allocated *ranges*, each app server owning a block, or a key-pool service) and *enumerability*: sequential codes let anyone walk your key space and scrape every link. **Hash, truncate, encode:** no coordination at all, which is its entire appeal. The bill is collisions: randomly minting 100M codes into 3.5 trillion slots expects about n²/2M ≈ **1,400 collisions per 100M codes** — every insert needs a uniqueness check and a salt-retry loop. Hashing also collapses identical long URLs into one code — free deduplication or an analytics/expiry bug, a product decision to state aloud.

| Axis | Counter + base62 | Hash + truncate |
|---|---|---|
| Collisions | None by construction | Uniqueness check + salt-retry per insert |
| Coordination | Range allocation or key pool | None |
| Enumerable? | Yes — sequential | No — pseudorandom |
| Same URL twice | Distinct codes (unless deduped) | Identical code |

Edge cases: **custom aliases** are a third path — user-chosen keys need an atomic availability check and rate limiting, because they are squatting targets; codes are never *reused* after deletion or expiry; and code length is a one-way door.

## Follow-up 2: 301 or 302 — and What Did You Just Promise the Browser?

**What it tests:** whether you see that the redirect status is a *caching policy executed by other people's browsers*.

**How to reason:** a redirect does not just say "go to X" — it says how long the client may remember that. Ask what the product needs from the second click: the click, the control, or the offload.

**Answer.** **301 (Moved Permanently)** lets user agents cache the mapping and never contact the shortener again — [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) defines the semantics, and browsers cache 301s even without explicit cache headers. The consequence chain: bandwidth and latency win, but **analytics die** (you never see the second click), **expiry breaks** (a deleted link keeps redirecting from caches you do not operate), and **corrections cannot propagate** (a mis-mapped 301 lives until users clear their own browsers). **302** is temporary: every click returns to your service, and you keep the click stream, expiry, and edit-ability at the price of one extra hop per redirect, forever. The middle path: **301 with a bounded `Cache-Control: max-age`** — some offload, and a *bound* on how long a mistake lives; the freshness machinery is the same [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) contract walked in [URL to Page](./url-to-page.md). The trap to volunteer: migrating 302 → 301 is safe; the reverse is not, because you cannot un-cache what the world already cached.

## Follow-up 3: Reads Beat Writes 100:1 — Where Does the Cache Sit, and What Does Cache-Aside Race On?

**What it tests:** the read path — whether cache-aside is a flow you can execute *and race* in your head.

**How to reason:** the redirect is `GET code → lookup → 30x`, a key-value read under viral skew. Ask where misses go, what removes entries, and what a concurrent write does to a lazy refill.

**Answer.** The standard flow is **cache-aside**: on read, GET the code from Redis; on hit, redirect; on miss, read the mapping store (sharded by hash of code), SET the entry with a TTL, then redirect. Writes *delete* the cache key rather than update it — deletion is idempotent, cheap, and avoids populating the cache from a transaction that has not fully committed. The race: a reader misses and reads the database's *old* value; a concurrent write commits the new URL and deletes the key; the reader then SETs the stale value back — the cache serves a dead mapping until TTL expiry. Cache-aside lives in application code, so no database isolation level protects the interleaving. Defenses: **TTL as the backstop** (staleness bounded by construction); **versioned keys** (`code:v7`, version bumped on write) so a stale refiller populates a key nobody reads; **delayed double delete** (delete, wait past the refill window, delete again). Two skew consequences: a viral link concentrates traffic on exactly one key — the hot-key problem of [Hot Keys and Sharded Counters](../../distributed/advanced/hot-keys-and-sharded-counters.md) — and expired or deleted codes need **negative caching** (short-TTL tombstones), or the dead-link fraction of traffic hammers the database on every click. The full audit of what "just cache it" promises is [Caching Assumptions](../assumptions-hunt/caching.md); the boundary of the reflex is [Cache Always Improves](../misconceptions/cache-always-improves.md).

## Follow-up 4: Every Redirect Is Also a Write — Analytics Without Hot-Row Updates

**What it tests:** whether you notice the write hiding inside the read path.

**How to reason:** the click count is a read-path write at read volume: ~120K increments per second against the hottest rows in the system. Ask where the increment can live that is *not* a synchronous UPDATE on the redirect path.

**Answer.** `clicks = clicks + 1` on the mapping row serializes every redirect on one row lock — the database becomes the bottleneck of the path the cache just optimized. The standard answer moves counting off the request path: emit a click event (code, timestamp, referrer, geo, user-agent) to an append-only queue, and let consumers aggregate — flush per-code counters in batches, or bucket by (code, hour) so merges are associative adds and out-of-order events are harmless. Variants and prices: **sharded counters** — N counter rows per code, increment a random shard, sum on read; **Redis INCR** with periodic flush to durable storage — fast, but the flush interval is a data-loss window; **HyperLogLog** for unique visitors — ~1% error at ~12 KB per key. Edge cases: a deleted code's pending events must be explicitly landed or dropped — decide, do not leak; and the creator who just shared a link expects *their* dashboard to move — serve their own clicks with read-your-writes semantics.

## Follow-up 5: Abuse, Custom Domains, and the Trust Rung

**What it tests:** threat modeling — a shortener's product is destination opacity; what does that attract?

**How to reason:** everything that hides the destination from the user hides it from the user's defenses too. Walk the abuse surface as a product-existence problem, then custom domains as infrastructure.

**Answer.** Shorteners are a classic malware and phishing vector: the visible URL says nothing, blocklists keyed on final destinations never see the click coming, and one abused link can get your whole domain onto browser and mail blocklists — an existential product risk. Defenses: scan destinations at creation *and re-scan periodically*, because links rot; integrate blocklists (Google Safe Browsing is the canonical feed) with interstitial warnings; expose a preview endpoint that reveals the destination; and rate-limit creation per identity — the rate limiter chain again, protecting the *write* path ([Rate Limiter Design](./rate-limiter-design.md)). **Custom domains** are the enterprise half: per-tenant DNS delegation (the tenant CNAMEs your hostname), TLS issuance per domain, routing by `Host` header. The sharpest edge case is **dangling CNAME takeover**: a tenant points `go.customer.com` at your hostname but never registers the domain in your system; they churn, the CNAME dangles, and anyone can claim the unclaimed hostname and serve content from the customer's subdomain — the fix is domain verification (a TXT challenge) before serving.

## Follow-up 6: The Twists — "Add Expiry," "100× Traffic," "Multi-Region"

**What it tests:** the design-judgment endgame: extend the design without rebuilding it, and say what each twist costs.

**How to reason:** each twist bends one number or invariant from the opening estimate — name which, re-run the estimate at the new number, resolve with the cheapest change.

**Answer sketch.** *"Add expiry"*: store `expires_at` with the mapping; on read, compare before redirecting and serve **410 Gone** — not 404, because the code did exist and clients and crawlers treat "gone on purpose" differently; reclaim space with a background sweeper; and **never reuse expired codes** — a QR code printed in 2021 does not expire when the row does, and a browser-cached 301 may hold the mapping indefinitely; a recycled code turns every memorized copy into a hijack you shipped on purpose. *"100× traffic"*: the baseline becomes ~12M reads per second — the redirector tier scales horizontally, the cache hit ratio becomes the survival variable (add an in-process L1 in front of Redis, sized to each node's hot set), and the store shards by hash of code — with consistent hashing if resharding mid-life is on the table ([Consistent Hashing](../../distributed/partitioning/consistent-hashing.md)); the write side barely notices. *"Multi-region"*: steer users to the nearest region (anycast or geo-DNS — see [Anycast and Geo-Routing](../../networks/cdn/anycast-and-geo-routing.md)) and replicate mappings asynchronously from the writing region to read replicas. The honest cost: a code created in region A is briefly invisible in region B — a creator clicking their own fresh link can hit a replica that lacks it; route the creator's own lookups home, or hold them until the version arrives. What multi-region does *not* need — the key space is disjoint by construction — is conflict resolution: codes never merge, they only replicate.

## How to Approach Unfamiliar Variations

The transferable template for "design X" chains where X is read-heavy and key-value-shaped (shortener, pastebin, typeahead):

1. **Estimate first and keep the numbers alive.** Writes/sec, reads/sec, storage, and the read:write ratio are load-bearing; every twist is phrased against them, and "now make it 100×" is unanswerable without a baseline.
2. **Count the writes hiding inside reads.** Analytics, counters, sessions — read-heavy systems carry a write-shaped feature bolted onto the read path, and it is where the naive design collapses into hot rows. Move those writes off the request path and state their loss windows.
3. **Treat protocol-level choices as product decisions.** A status code, a header, an alphabet — each commits behavior at the scale of everyone's browsers, not your fleet. Ask what it promises and whether you can take it back.
4. **A twist is one violated assumption.** Locate the changed number, re-derive only what it affects, and price the fix in the currencies already on the table: staleness, latency, control.

## Interview Questions

**Q: Why not just hash the long URL and skip the counter entirely?**
A: You can — no coordination, deterministic codes. But truncating a hash into 3.5 trillion slots collides (~1,400 expected per 100M codes), so every insert needs a uniqueness check and salt-retry, and identical URLs collapse to one code — free dedup or an analytics bug. The counter buys uniqueness by construction at the price of coordination and enumerability; the choice is *who you pay*.

**Q: Your click counts are consistently lower than what partners measure on their side. Hypothesis?**
A: 301s. Browsers and intermediaries cached the permanent redirect, so later clicks never reach your servers — partners count events you never see. Audit which links return 301 and whether their `Cache-Control` is unbounded; ship 302 (or bounded-max-age 301) going forward — already-cached 301s cannot be recalled, which is why the status code is a one-way door.

**Q: A pasted link goes viral and one Redis shard saturates while the rest idle. Options, cheapest first?**
A: The key is hot and Redis serializes per-key work, so cluster headroom does not help. Cheapest first: serve the redirect from an in-process L1 on each redirector — the mapping is immutable in practice, so a 60-second local TTL is safe; then replicate the hot key to N shards and pick one at random per read; and if the key also takes *writes*, those become sharded counters. A bigger Redis is the wrong answer — the ceiling is contention on one key.

## Key Takeaways

- The read:write ratio and the scale estimate *are* the design; every rung bends one number from the opening estimate.
- Code generation chooses who pays for uniqueness: a coordinated counter (no collisions, enumerable) or hashing (no coordination, collision checks and retries).
- The redirect status is a caching policy executed by the world's browsers: 301 offloads and blinds simultaneously; no expiry or correction survives an unbounded 301.
- Cache-aside is application logic with a built-in race — stale refill over a delete — so TTL is the backstop, versioned keys the cure, negative caching the forgotten half.
- Analytics is the write inside the read path; each twist breaks exactly one earlier assumption, and the senior answer names which one.

## Cross-References

- [URL Shortener (System Design)](../../interview/system-design/url-shortener.md) — the full worked design: capacity tables, component diagram, API sketch.
- [Rate Limiter Design](./rate-limiter-design.md) — the sibling design chain; the abuse rung reuses its fail-open/fail-closed logic.
- [URL to Page](./url-to-page.md) — the client-side ladder; where the redirect hop sits inside a page load.
- [Hash Tables](./hash-tables.md) — the key-value shape of the whole design, and the origin of consistent hashing.
- [Caching Assumptions](../assumptions-hunt/caching.md) — what "just cache it" silently promises, audited assumption by assumption.
- [Cache Always Improves](../misconceptions/cache-always-improves.md) — the boundary of the caching reflex the read rung builds on.
- [Hot Keys and Sharded Counters](../../distributed/advanced/hot-keys-and-sharded-counters.md) — the mechanism behind the viral-link twist and the analytics rung.
- [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) — resharding the mapping store without a full migration.
- [Anycast and Geo-Routing](../../networks/cdn/anycast-and-geo-routing.md) — steering users to the nearest region in the multi-region twist.
