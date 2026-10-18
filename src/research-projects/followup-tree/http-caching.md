# Follow-up Tree: HTTP Caching

## Overview

"How does HTTP caching work?" opens as a header trivia question and escalates into a systems-design question about consistency, latency, and failure, which is why it appears in backend, platform, and SRE loops alike. The ladder runs from the freshness model (who decides how long a response is good for), through validation (the cheap re-check that turns an expired copy into a 304), into the shared-cache and content-negotiation layer where correctness bugs live, and ends at the design judgment every CDN engineer eventually makes: staleness is not a bug you eliminate but a budget you allocate. The thread tying every rung together is *the cost of a cache miss versus the cost of being wrong* — each follow-up either asks how the copy is proven fresh, what a revalidation costs, or what happens to users when the copy is stale or the origin is down. This chain stays at the HTTP protocol level; the application-cache layer (Redis cache-aside races, stampedes, invalidation) is owned by [Redis Caching](./redis-caching.md), and the distributed-cache design space by [Caching, Distributed](../why-not-handbook/caching-distributed.md). The book-level header reference is [HTTP/1.1](../../networks/http/http1.md); [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) is the caching specification every answer here paraphrases. Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"A browser requests an image it downloaded five minutes ago. What happens?"**

The expected core answer: the browser does not send the request blindly — it first evaluates the stored response against the caching metadata. If the response is *fresh* (within its `Cache-Control: max-age` lifetime, or a heuristic lifetime derived from `Last-Modified` when only that header exists), the browser serves it from cache without touching the network. If it is *stale*, the browser revalidates: a conditional request carrying `If-None-Match` (the stored `ETag`) or `If-Modified-Since` (the stored `Last-Modified` date) goes to the origin, which returns `304 Not Modified` — headers only, no body — or `200 OK` with a new copy if it changed. `no-store` skips caching entirely; `no-cache` means "cache but always revalidate," and the distinction between those two is the most common junior slip in the whole topic.

A weak answer recites "the browser uses Expires and ETags" without being able to say what makes a response fresh, what a 304 saves, or who else between browser and origin holds copies. The strong answer names both halves of the machinery — *freshness* (serve without asking) and *validation* (ask cheaply) — and volunteers that intermediate proxies and CDNs are also participants with their own rules. The follow-up that escalates: **"Who computed that max-age, and what exactly can go wrong between expiry and revalidation?"** — which moves the ladder from mechanics to the freshness model's assumptions.

## Level 2: The Freshness Model and Its Arithmetic

**What it tests:** whether "the cache knows when to expire" is a mechanism you can compute with — Age arithmetic, heuristics, directive precedence — or a hand-wave.

**Weak answer:** "The Expires header says when it expires" — a deprecated-header answer that cannot explain freshness lifetime versus remaining freshness, ignores `Cache-Control` precedence, and has never met the heuristic.

**Strong answer:** distinguishes *freshness lifetime* (how long the response may be reused without checking) from *remaining freshness* (lifetime minus `Age`), states that `s-maxage` > `max-age` > `Expires` in precedence, explains that shared caches (proxies, CDNs) and private caches (browsers) honor different directives, and can derive the heuristic: when no explicit lifetime exists, RFC 9111 lets a cache use 10% of the interval since `Last-Modified`.

**Escalation trigger:** "You served a page with max-age=300. A user reports seeing a version that is 20 minutes old. Walk me through every way that happens."

**Answer.** Every path starts with the same fact: freshness is *asserted by the server and enforced by clocks the server does not control*. The arithmetic suspects first: `Age` is added by every cache hop, and a wrong or missing `Date` on the origin response inflates remaining freshness — a cache that trusts a skewed origin clock extends lifetimes. The config suspects: an intermediate CDN honoring its own `s-maxage` or a default TTL the origin never intended, layered in front of a browser also caching at `max-age` — each layer can serve from its own copy, and the effective staleness is the worst case across layers. The heuristic suspect: a response with only `Last-Modified` and no explicit directive gets the 10% rule, which on a year-old file grants five weeks of freshness — a classic "we changed the logo but users see the old one for days" bug. Then the failure-mode suspects, which earn the rung: a clock-skewed origin emitting responses with a `Date` in the future (caches store them already-stale or already-fresh-forever), and admins "fixing" staleness by maxing out TTLs during an incident. The honest summary is that freshness is a distributed agreement between many clocks, and the repo's general treatment of exactly that failure class is [Caching Assumptions](../assumptions-hunt/caching.md).

The design twist the strong candidate volunteers: `immutable` — a directive promising the resource will *never* change at that URL, letting caches skip even conditional revalidation after expiry, which is the correct pairing for fingerprinted assets (`app.a1b2c3.js`) where "change" is modeled as "new URL." URL-based versioning converts the invalidation problem into a deployment convention, and it is the reason aggressive-TTL static hosting works. The follow-up that escalates: **"If the file did change, how does the server prove it cheaply?"**

## Level 3: Validation — ETags, 304s, and Optimistic Concurrency

**What it tests:** whether revalidation is a mechanism you can price — what a 304 actually saves, what an ETag actually is, and where validators leak into other HTTP features.

**Weak answer:** "The server compares the ETag and returns 304" — cannot say what the ETag is derived from, why 304 saves bytes but not round trips, or the difference between strong and weak validators.

**Strong answer:** explains that an ETag is an opaque validator the server computes (hash of content, revision number, mtime+size — anything stable), that strong ETags must change whenever the byte content changes while weak validators (`W/`) admit semantically equivalent representations, that a `304` removes the body from the wire but not the request from the latency path, and that the *same* If-Match/If-None-Match machinery doubles as optimistic concurrency control for writes.

**Escalation trigger:** "Revalidation still costs a round trip. When is a 304-driven architecture worse than just caching harder?"

**Answer.** Price the 304 precisely: it saves bytes and origin work, but the request still pays full RTT, TLS bookkeeping on a cold connection, and a hit on the origin's availability — a revalidating page is a page that must reach the origin every time, which is why "cache harder" (long TTLs, `immutable`, precomputed assets) beats "validate always" for anything where freshness can be traded for latency. Validation wins when payloads are large and changes are rare-but-must-be-seen (APIs returning megabytes, software artifacts), or when the freshness requirement is per-user and TTLs cannot be shared. The granularity bug that earns credit: `Last-Modified` has one-second resolution — two writes within a second produce identical timestamps and a missed change, which is why strong ETags should not be derived from timestamps alone. The subtle cross-feature connection that separates senior candidates: `If-Match` on a `PUT` is the exact optimistic-lock primitive — "apply this write only if the version I read is still current" — so the caching validator and the database compare-and-swap are the same protocol shape at different layers, and an API that supports ETags already has the hard part of conflict detection built.

The design twist: *weak* validators exist because some resources are regenerated bytes (compressed differently, dynamic templating) where byte-equality is too strict — serving a semantically equal representation is correct, and demanding byte equality would destroy hit rates. The follow-up that escalates: **"Everything so far assumed one representation per URL. What breaks that?"**

## Level 4: Shared Caches, Vary, and the Invalidation Problem

**What it tests:** the expert rung — multi-user correctness at shared caches (`Vary`, `private`, `Authorization`), the stale-serving directives that trade correctness for resilience, and why "purge the CDN" is the operations story caching specs mostly refuse to solve.

**Weak answer:** knows `Vary: User-Agent` exists as a bug to avoid but not why; believes invalidation is what TTLs are for; has not met `stale-while-revalidate` or thought about who pays for a purge.

**Strong answer:** explains `Vary` as a second cache key dimension (response varies by request headers, so every distinct header value is a separate entry — `Vary: User-Agent` fragments the cache per browser version), states that shared caches will not cache responses to `Authorization` requests unless explicitly permitted (`public`, `s-maxage`), distinguishes `private` from `no-store` (single-user cacheable vs never cacheable), and knows the stale-serving extensions: `stale-while-revalidate` serves the old copy while refreshing in the background; `stale-if-error` serves it when the origin is down.

**Escalation trigger:** "Your origin is on fire. Configure caching so users notice as little as possible — then tell me what you gave up."

**Answer.** The resilience toolkit, in the order a senior would apply it: `stale-while-revalidate` keeps responses flowing while refresh happens off the request path, converting a thundering-herd refresh into a background trickle; `stale-if-error` keeps serving past expiry exactly when the origin cannot answer, which is the difference between a degraded-but-working site and a hard failure; layered on top, CDNs offer request-coalescing (one origin fetch serves N waiting clients) — the same stampede-protection shape the application-cache ladder [Redis Caching](./redis-caching.md) meets from the other side. What you gave up is the crux: every stale-serving directive is a promise that some users will see old data during failure and churn, and the budget question is *which* users and *how old*. The invalidation half of the rung is where the honest answer matters: HTTP gives origins almost nothing — `Cache-Control` is set at response time, and active purging is a CDN-specific control-plane API, not a protocol feature. The industry's actual answer is architectural: fingerprinted URLs so "invalidation" becomes "deploy new names," short TTLs only where data is genuinely per-user, and error budgets for staleness rather than attempts at cross-layer consistency. The sentence that ends the chain well: caching correctness is a *policy you configure per resource class*, and the worst designs apply one TTL policy globally.

## How to Approach Unfamiliar Variations

The template for caching variations — "why is the API response cached at the CDN but not the browser," "make the dashboard update within a minute," "the cache hit rate is high but users see wrong data":

1. **Locate every cache between client and origin, and its policy.** Browser, CDN edge, regional shield, gateway: each holds a copy under its own directives. A "wrong data" report is a question about the worst staleness across layers, and the fix is named at the layer with the offending TTL.
2. **Split every complaint into freshness and validation halves.** "Too slow" is usually revalidation-everywhere (validation cost) or a cold edge (freshness too short); "wrong data" is usually a freshness or Vary bug. The halves have different fixes and different budgets.
3. **Treat every directive as a trade between origin load and staleness, and name the side being bought.** Longer TTL buys origin load; `stale-if-error` buys availability; `immutable` buys latency by promising forever-fresh URLs. Saying the purchased property out loud is what the top rung scores.
4. **Check who controls the cache key before debugging content.** Query strings, `Vary` headers, and cookie-stripping rules decide whether two users share an entry; most "random" caching bugs are key-definition bugs, not TTL bugs.

## Interview Questions

**Q: Your CDN hit rate is 92% but the origin is saturated. First three hypotheses?**
A: One, request-coalescing is off or broken, so near-simultaneous misses on the same URL all reach the origin — the stampede shape. Two, the cache key includes something that fragments entries (unsorted query parameters, tracking params, a `Vary` on a high-cardinality header), so 92% of *requests* hit but the origin still sees high *unique* fetches. Three, a large fraction of traffic is revalidations (misses-by-design), where 304s still cost origin round trips; check whether those responses could carry longer TTLs instead.

**Q: Why is `Cache-Control: no-cache` not the opposite of `no-store`, and when would you use each?**
A: `no-cache` means "cache it, but revalidate before every use" — it optimizes for bytes saved while keeping freshness tight. `no-store` means "never persist a copy anywhere" — it is the privacy/PII directive for responses that must not even hit disk. Using `no-cache` where `no-store` was meant leaks sensitive responses into shared caches; using `no-store` where `no-cache` was meant destroys hit rates for no correctness gain.

**Q: A team complains their JSON API responses get cached for other users. Diagnosis?**
A: A shared cache is holding a response that was per-user. Check the response: if it lacks `Cache-Control: private, no-store` and the request carries `Authorization`, a misconfigured or non-conformant shared cache is the suspect; if the request authenticates via cookie instead, the cache key may be ignoring the cookie entirely — same bug, different layer. The fix is explicit per-user policy on the response plus a cache key that includes whatever distinguishes users, and the test is fetching as two different accounts through the same edge.

**Q: When would you prefer long TTLs plus URL fingerprinting over short TTLs plus revalidation for a static site?**
A: Almost always for immutable build artifacts: fingerprinted names make content change = URL change, so TTLs can be effectively infinite, revalidation vanishes, and rollbacks are CDN-free. Short-TTL-plus-revalidation is the right model for the handful of genuinely mutable entries (an `index.html` that names the current bundle), where a 60-second TTL bounds staleness and a 304 keeps it cheap. Mixing them — long TTL on mutable names — is the bug that forces manual purges.

## Key Takeaways

- HTTP caching has two mechanisms: freshness (serve without asking, priced in staleness) and validation (ask cheaply, priced in round trips) — every design is a mix.
- Freshness arithmetic is `max-age` minus accumulated `Age` across hops, and the heuristic (10% of age since `Last-Modified`) surprises teams who never set a directive.
- ETags are opaque validators that double as optimistic-concurrency primitives; a 304 saves bytes and origin work, never round trips.
- `Vary` extends the cache key per header value; `private`, `no-store`, and the `Authorization` rules decide what shared caches may hold for multiple users.
- Resilient caching is deliberate staleness — `stale-while-revalidate` and `stale-if-error` are failure-mode features, and invalidation is a control-plane product, not an HTTP guarantee.

## Cross-References

- [Redis Caching](./redis-caching.md) — the application-cache chain: cache-aside races, stampedes, and invalidation below the HTTP layer.
- [Caching Assumptions](../assumptions-hunt/caching.md) — the hidden assumptions ("a cached value is the value") that TTL arithmetic quietly violates.
- [Caching, Distributed](../why-not-handbook/caching-distributed.md) — when a cache should live per-node versus fleet-wide, and the consistency price of each.
- [Cache Always Improves](../misconceptions/cache-always-improves.md) — the misconception this ladder's cost ledger refutes.
- [HTTP Protocol Evolution](./http-protocol.md) — how HTTP/2 multiplexing and HTTP/3 change the connection economics under these headers.
- [URL to Page](./url-to-page.md) — the parent chain where caching appears as one hop in the end-to-end walk.
- [DNS & CDN Routing](../connection-atlas/dns-cdn-routing.md) — the routing layer that decides *which* edge cache, and thus which copy, answers.
- [HTTP/1.1](../../networks/http/http1.md) — the book-level header reference this ladder paraphrases.
- [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) — HTTP Caching: the specification defining freshness, validation, `Vary`, and the stale-serving extensions.
