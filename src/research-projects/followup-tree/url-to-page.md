# Follow-up Tree: URL to Page

## Overview

"What happens when you type a URL and press Enter?" is the most famous opener in software interviewing, and it earns that status honestly: a complete answer touches DNS, TCP, TLS, HTTP, caching, load balancing, application and database architecture, and browser rendering — then the follow-ups make you *reason* about each layer instead of reciting it. The failure mode this chain trains against is the checklist recitation: naming twelve boxes in order but being unable to say what any layer's caches store, what its failure looks like, or where the milliseconds go. This page walks the ladder with each rung's purpose, reasoning, and answer; TCP handshakes are deliberately not re-explained here — [TCP Lifecycle](./tcp-lifecycle.md) owns that chain and this page links to it.

## The Opening Question

**"What happens when you type a URL and press Enter?"**

The expected core answer is a *pipeline with caches at every stage*: the browser parses the URL (scheme, host, port, path); resolves the hostname through DNS — browser cache, OS resolver cache, then recursive resolvers; opens a TCP connection to the resolved IP; negotiates TLS if the scheme is https; sends an HTTP request (method, path, headers); the request traverses a CDN edge or load balancer to an application server, which may consult its own caches and a database before returning a response; the browser checks response caching headers, then parses HTML into a DOM, builds the CSSOM, computes layout, paints, and composites. The strongest versions of this answer name *where the time goes*: a warm DNS lookup is cached and free, an uncached one costs tens of milliseconds; a TLS handshake costs a round trip or two; the first HTML byte cannot arrive before all of that completes.

Why this answer is correct: it is not the boxes but the *dependencies* that matter — each stage is a cache miss away from the next, and every later interview question ("make it faster", "make it secure", "what if DNS fails?") is a question about exactly one dependency edge. Naming the caches proactively is how you *choose* which rung the interviewer climbs first, which is a real advantage: run the ladder on your own ground.

## Follow-up 1: Walk Me Through DNS — and What If It Fails?

**What it tests:** whether DNS is a hierarchy you can reason about or a magic acronym, and whether you have thought about its failure modes — this is the most common escalation on this rung.

**How to reason:** resolution is a cache-hierarchy walk with TTLs; failures are therefore about staleness, timeout, and who holds the last-known-good answer.

**Answer.** The lookup walks the hierarchy: the stub resolver asks a recursive resolver (ISP or public), which asks a root server (which answers with the TLD nameservers), then the TLD server (which answers with the domain's authoritative nameservers), then the authoritative server (which answers with the record) — [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html) defines the model. Every hop caches: the browser, the OS stub, the recursive resolver, each for the record's TTL; a hot domain resolves from a nearby recursive cache in under a millisecond, a cold lookup costs tens of milliseconds across several RTTs. The mechanics live in [DNS Resolution](../../networks/dns/resolution.md) and [DNS Caching](../../networks/dns/caching.md).

The escalation — **"what if DNS fails?"** — has layered answers: a resolver timeout (your retry and fallback-resolver policy decides whether the user sees an error or a delay); a stale *negative* cache (a cached NXDOMAIN keeps returning "no such domain" even after the record exists — negative TTLs are real and bite during migrations); and a record that *is* served but points somewhere unhealthy (DNS does no health checking; failing over means lowering TTLs *in advance* or using health-aware DNS, and a long TTL you set yesterday is now your recovery time — this coupling between cache TTL and failover speed is the senior observation). Retry behavior in general is its own discipline: see [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md). Note also what DNS does *not* promise: the resolver is a third party (encrypted DNS exists to close that gap), and resolution succeeding tells you nothing about the host being up.

## Follow-up 2: How Many Round Trips Before the First Byte?

**What it tests:** whether you model latency as round trips, which is the currency every handshake is paid in.

**How to reason:** count the sequential network exchanges that must complete before the HTTP request can be sent — DNS, TCP, TLS — and know which can overlap or be skipped.

**Answer.** On a cold connection with HTTPS over TCP: TCP's three-way handshake is one RTT (the request can ride the third segment), and TLS 1.3's handshake adds one RTT before the request — [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html) — so two RTTs plus DNS stand between Enter and the request. TLS 1.2 would cost two RTTs for the handshake; session resumption (1-RTT for TLS 1.2, 0-RTT data for TLS 1.3) removes RTTs on warm connections at the price of replay considerations for 0-RTT early data. The TCP side — why the third handshake segment exists, what TIME_WAIT costs a client opening many connections — is exactly the chain in [TCP Lifecycle](./tcp-lifecycle.md); the connection-management details (keep-alive reuse, connection pooling, opening 6+ connections in parallel to work around head-of-line blocking) are the browser's contributions to this arithmetic. The senior observation: "first byte" latency is dominated by *sequential* RTTs, so every optimization in this chain — cached DNS, resumption, edge servers — is an attack on the number of sequential round trips, not on bandwidth. If the interviewer pushes on QUIC, the answer is that QUIC folds transport and cryptographic handshakes together so a resumed connection can send application data in its first flight — a pointer, not a rerun, of [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md).

## Follow-up 3: What Does the HTTP Exchange Look Like, and What Makes the Response Cacheable?

**What it tests:** whether HTTP is a protocol you can read — methods, headers, status codes — and whether you understand caching as a *contract* between client, intermediaries, and origin.

**How to reason:** the request names a resource and states its capabilities; the response carries the representation plus metadata that tells every cache downstream what it may do. Caching rules are declarative — read them off the headers.

**Answer.** The request is a method, path, and headers (`Host`, `Accept`, `Cookie`, conditional headers if a cached copy exists); the response is a status line, headers, and body. HTTP/1.1's wire format and its head-of-line blocking are covered in [HTTP/1.1](../../networks/http/http1.md); what matters for the ladder is the caching contract of [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html): `Cache-Control: max-age` says how long a fresh copy may be reused; `ETag`/`Last-Modified` enable *conditional* revalidation — the client resends `If-None-Match` and a 304 response carries the new metadata with no body, saving the transfer but not the round trip; `no-cache` means "store but revalidate," while `no-store` means "never persist"; and `Vary` names request headers that are part of the cache key. The rung's classic trap: caching is keyed and layered, so "we set max-age=0" does not invalidate copies already held by browsers or shared caches — invalidating what others already cached is fundamentally hard, which is why versioned URLs (`app.v42.js`) exist. Whether HTTPS *itself* makes a site "secure" is a claim with real limits — [HTTPS Means Secure](../misconceptions/https-means-secure.md) documents the misconception; the headers that carry actual security posture (HSTS, cookie flags, CSP) belong to the "make it secure" twist below.

## Follow-up 4: Where Does the CDN Fit, and What Does It Change?

**What it tests:** whether you see the CDN as an architectural layer with its own cache hierarchy and failure modes — not a marketing box on the diagram.

**How to reason:** a CDN is a globally distributed cache with a routing scheme (anycast) that steers users to a nearby edge; every property it has follows from being a cache that is *in front of* your origin.

**Answer.** The user's request terminates at the nearest edge (anycast routes the same IP to different sites by location — see [Anycast and Geo-Routing](../../networks/cdn/anycast-and-geo-routing.md)); a cache hit at the edge serves the response without touching your infrastructure at all; a miss goes through an optional *shield* tier to the origin, and the response populates the edge under the same RFC 9111 rules (plus CDN-specific purging and stale-while-revalidate serving). The consequence rung: what *can* be edge-cached is static and shared; personalized responses cannot be cached at the edge, which drives the modern pattern of splitting a page into a cached shell plus personalized API calls. The failure rung is the interesting one: when a CDN is in the path, its misconfiguration is *everyone's* outage at once — the June 2021 Fastly incident took down large fractions of the web with a single bad configuration deployment, and [The Fastly Outage of June 2021](../failure-casebook/fastly-june-2021.md) walks the timeline; the general lesson, that a global layer adds global blast radius, also appears in [Network & Distributed Assumptions](../assumptions-hunt/network-distributed.md). Edge mechanics and economics continue in [CDN Edge](../../networks/cdn/edge.md) and [How CDNs Work](../../networks/cdn/how-it-works.md).

## Follow-up 5: The Request Reaches Your Infrastructure — Then What?

**What it tests:** the server-side half of the ladder: load balancing, application servers, and the database — and whether you can follow the request the last mile.

**How to reason:** each hop is a queue in front of a resource; the ladder question is where requests wait, what state each hop holds, and what the database does with the query.

**Answer.** A load balancer (L4 forwarding by connection, L7 by HTTP content — the split is [L4 vs L7](../../networks/load-balancing/l4-vs-l7.md), with design-level scaling logic in [Load Balancing Design](../../interview/system-design/hld/load-balancing-design.md)) picks an application server from its healthy pool; the app server runs the handler, which typically reads or writes state through caches and a database. The database rung has its own escalations: an uncached read that was 2 ms at the app tier becomes a query whose cost depends on whether the planner can use an index — the chain in [Database Indexes](./database-indexes.md) — and under load, requests *queue*: the tail latency of the whole page is dominated by the slowest queue, not the average server. The boundary worth stating: app servers are stateless only because the state was pushed down into caches and databases — an assumption worth making explicit, since it is exactly where capacity plans break.

## Follow-up 6: The Browser Has the HTML — Then What?

**What it tests:** whether "the browser renders it" is a real model of the rendering pipeline or a shrug — many strong backend candidates lose the ladder at exactly this rung.

**How to reason:** rendering is itself a pipeline of transforms — parse, style, layout, paint, composite — with dependencies you can name, and every dependency is a place to block.

**Answer.** The parser turns bytes into a DOM (the HTML spec's error-recovery is why malformed HTML still renders), the stylesheet into a CSSOM; they combine into a render tree, layout computes geometry, paint rasterizes, and compositing assembles layers on the GPU. The escalations are about *what blocks what*: CSS in the head blocks rendering (the browser cannot compute style until it has all rules), synchronous scripts block parsing (hence `defer`/`async`), and a web font may swap late. The full pipeline and its performance model belong to [Browser Rendering](../../web-development/browser-rendering.md) and [Browser Architecture](../../web-development/browser-architecture.md); the ladder-level point is symmetry — the browser is a cache-and-pipeline system exactly like the server side, and the same reasoning ("what is cached, what blocks, what fails") applies on both sides of the wire.

## Follow-up 7: Now Make It Faster — Then Make It Secure

**What it tests:** design judgment on the whole pipeline: can you *spend* the mental model you just built, per stage, with measurement reasoning instead of a laundry list?

**How to reason:** make it faster = attack sequential dependencies and cache more, then *measure which stage the waterfall blames*. Make it secure = for each layer, ask what that layer trusts and who can lie to it.

**Answer.** *Faster*, by stage: DNS — cache more, lower cold-lookup cost (the rung 1 arithmetic); connection — resumption, 0-RTT, or QUIC (rung 2); transfer — cacheable representations, compression, conditional requests (rung 3); path — serve from nearer edges (rung 4); server — cache reads, index the queries, cut queueing (rung 5); client — unblock the critical path, lazy-load the tail (rung 6). The discipline that earns credit: "first I would measure the waterfall and find the *longest sequential* edge, because parallel work hides while sequential work compounds." *Secure*, by layer: DNS — the resolver is trusted, so hijacking or poisoning it redirects everything (encrypted DNS narrows who can lie); TLS — authenticates the server and encrypts the path, but does not authenticate *content* or make the app safe (the limits live in [HTTPS Means Secure](../misconceptions/https-means-secure.md)); HTTP — cookies need `Secure`/`HttpOnly`/`SameSite`, and HSTS stops the downgrade dance where an attacker forces the first request onto http; application and origin — the CDN and LB see and can modify everything, so the security model must say what each hop may read. The pattern for both twists is identical: name the layer, name what it trusts, name the fix in its own currency — and never answer "make it secure" with only "use HTTPS," any more than you would answer "make it faster" with only "add a cache" (the reason that instinct misleads is documented in [Cache Always Improves](../misconceptions/cache-always-improves.md)).

## How to Approach Unfamiliar Variations

The transferable template for this chain and its cousins ("what happens when you send an email", "what happens when you scan a QR code"):

1. **Produce the dependency chain first, boxes second.** Name the sequential hand-offs — resolve → connect → secure → request → compute → render — and you have also named the latency budget and the failure surface. Every variation of this question is a re-instantiation of that chain.
2. **At each layer, state the cache and the trust.** "What is cached here, for how long, keyed by what?" and "what does this layer assume about the previous one?" — those two questions generate most follow-ups before the interviewer asks them.
3. **Convert failure questions into TTL and timeout questions.** "What if X fails?" almost always means: what does the previous stage remember (cache/TTL), how long does it wait (timeout), and what is the fallback (retry, secondary resolver, stale serving)?
4. **When asked to improve, attack the longest sequential edge, not the biggest box.** The waterfall, not the architecture diagram, decides where milliseconds go; a 50 ms edge win that is parallel to everything wins nothing.

## Interview Questions

**Q: Your page's p75 time-to-first-byte jumped 200 ms in production. Where do you look first?**
A: The waterfall's front: DNS and TLS are the sequential edges before any bytes flow. Check whether DNS TTLs expired at scale (cold resolver lookups), whether TLS resumption broke (a session-ticket change or new certificate chain adding an RTT), and whether the CDN began missing to a farther origin. The diagnosis pattern is to diff the *edges* of the waterfall, because a 200 ms constant jump smells like one added sequential RTT, not slower code.

**Q: Why does a 304 response help if it still costs a round trip?**
A: It saves the *transfer*, not the latency: no body crosses the network, so the win is bytes and server work, which matters on slow links and large payloads — and matters not at all if the bottleneck is the RTT itself. Knowing which currency a fix pays in is the actual answer.

**Q: You need to take an origin down for maintenance with zero user impact, and your DNS TTL is 24 hours. What went wrong and what do you do?**
A: The TTL was set for resolver-load reasons without modeling failover: every resolver that cached the record keeps sending users to the dead origin for up to 24 hours. Now: lower TTLs and serve a degraded path, or shift traffic at a layer that obeys you today (the LB/CDN), and afterward, set TTLs to match your actual failover requirements. The coupling — cache lifetime is recovery speed — is the lesson.

**Q: An interviewer asks what the browser does with a `Set-Cookie` response on an image request from a third party. Does the ladder change?**
A: The early rungs do not (DNS, TCP, TLS are identical for the subresource), but the trust model does: a third-party response can set cookies that ride along on later requests — the mechanism behind cross-site tracking and the reason `SameSite` and cookie partitioning exist. The ladder is the same; the security analysis of rung 7 is where the difference lives.

## Key Takeaways

- The URL-to-page answer is a dependency chain with caches at every stage; the caches (DNS, browser, CDN, app, DB, HTTP) are where both performance and failure actually live.
- Latency is paid in sequential round trips: DNS + TCP + TLS stand before the first byte, and every optimization is an attack on that count — resumption, 0-RTT, edges, and cached DNS all shorten the same critical path.
- HTTP caching is a declarative contract (RFC 9111): freshness, revalidation, and `Vary` keys — and it cannot retroactively invalidate what other caches already hold, hence versioned URLs.
- CDNs add a global cache layer with global blast radius; server-side, requests queue, and the database rung reappears as an index-and-latency question.
- "Make it faster" means attack the longest sequential edge after measuring; "make it secure" means naming what each layer trusts — neither is answered by a single technology.

## Cross-References

- [TCP Lifecycle](./tcp-lifecycle.md) — the connection-opening chain this page links to instead of repeating: handshakes, TIME_WAIT, congestion control.
- [Database Indexes](./database-indexes.md) — the database rung's own escalation chain: from query to index to write amplification.
- [Rate Limiter Design](./rate-limiter-design.md) — what sits in front of the app tier and how it fails open or closed.
- [DNS Resolution](../../networks/dns/resolution.md) — the full recursive walk, record types, and delegation mechanics.
- [DNS Caching](../../networks/dns/caching.md) — TTL semantics, negative caching, and resolver behavior.
- [TLS Deep Dive](../../networks/security/tls-deep-dive.md) — handshake internals beyond this page's RTT accounting.
- [HTTP/1.1](../../networks/http/http1.md) — wire format, keep-alive, and head-of-line blocking.
- [How CDNs Work](../../networks/cdn/how-it-works.md) and [CDN Edge](../../networks/cdn/edge.md) — the edge-cache hierarchy and its economics.
- [L4 vs L7 Load Balancing](../../networks/load-balancing/l4-vs-l7.md) — the two kinds of balancer and where each sees what.
- [Browser Rendering](../../web-development/browser-rendering.md) — the render pipeline this chain only sketches.
- [Load Balancing Design](../../interview/system-design/hld/load-balancing-design.md) — the server-tier design decisions this rung compresses.
- [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md) — the discipline behind every "what if it fails?" answer in this chain.
- [Network & Distributed Assumptions](../assumptions-hunt/network-distributed.md) — the sibling treatment of hidden network assumptions.
- [HTTPS Means Secure](../misconceptions/https-means-secure.md) — what TLS does and does not promise, documented as a misconception.
- [Cache Always Improves](../misconceptions/cache-always-improves.md) — why "add a cache" is not automatically the faster answer.
- [The Fastly Outage of June 2021](../failure-casebook/fastly-june-2021.md) — a single config deployment breaking half the web via the CDN layer.
- [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md) — where the TCP+TLS handshake stack is heading.
