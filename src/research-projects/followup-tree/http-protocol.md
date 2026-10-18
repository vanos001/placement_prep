# Follow-up Tree: HTTP Protocol Evolution

## Overview

"Walk me through what happens in HTTP/1.1 when a page needs 50 resources" is the application-layer ladder that quietly tests protocol design under constraints: every HTTP revision exists because the previous one hit a wall, and the walls are all head-of-line blocking — at the application layer, then at the transport layer, then (spectacularly) it turns out you cannot fully remove it at all. Interviewers on web-infrastructure and API-platform teams use this chain to find out whether a candidate understands *why* protocols evolve: pipelining failed for a reason, multiplexing fixed the application layer but exposed TCP, and QUIC moved the transport into user space to fix what TCP could not. The candidate who can narrate the three-layer HOL story — HTTP/1.1, HTTP/2-over-TCP, HTTP/3-over-QUIC — demonstrates layered-systems thinking that transfers to every protocol question. This page walks the ladder: what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. Depth that this chain deliberately hands off: the TLS negotiation itself (certificates, resumption, the 1-RTT/0-RTT mechanics) is the chain in [TLS Handshake](./tls-handshake.md), and the TCP state machine and congestion control beneath everything are [TCP Lifecycle](./tcp-lifecycle.md). Book-level companions: [HTTP/1.1](../../networks/http/http1.md), [HTTP/2](../../networks/http/http2.md), [HTTP/3](../../networks/http/http3.md), and [HPACK](../../networks/http/hpack.md).

## The Opening Question

**"A page needs 50 resources. Describe what HTTP/1.1 does about that — and where it hurts."**

The expected core answer: each TCP connection carries requests one at a time — request, response, complete, next — so the browser opens up to ~6 parallel connections per origin, queues the rest, and the queue is *head-of-line blocked*: one slow request at the front delays everything queued behind it on that connection. Connection setup per connection costs a TCP handshake (and TLS — [TLS Handshake](./tls-handshake.md)); keep-alive amortizes setup but does nothing for serialization.

A weak answer says "HTTP/1.1 is slow so we use HTTP/2" without being able to name *what* is slow — the serialization of requests on one connection is the answer, and connection setup is the secondary tax. The strong answer separates the two costs and notes the partial mitigations HTTP/1.1 already had: keep-alive (reuse), pipelining (send without waiting — deprecated because responses still complete in order, so a slow response head-of-line blocks the pipe, and broken proxies made it unsafe in practice), and domain sharding (spread the queue across more connections — a workaround that *raises* connection costs and breaks TCP's own congestion tuning). The follow-up that escalates: **"How does HTTP/2 fix this?"**

## Level 2: HTTP/2 Multiplexing — What It Fixes and What It Adds

**What it tests:** whether the candidate can explain multiplexing at the frame level, and whether they know HTTP/2 introduced *new* problems (header bloat, stream priorities, TCP-level coupling) rather than being a strict upgrade.

**Weak answer:** "HTTP/2 sends many requests over one connection" — mechanism-free, and misses that one connection is exactly what creates the next bottleneck.

**Strong answer:** describes the binary framing layer — streams carrying frames, interleaved on one connection, each with an ID — explains flow control per stream, names HPACK as the header-compression answer to the "50 requests × 800 bytes of repeated headers" tax, and states the residual cost: all streams share one TCP connection, so one packet loss stalls *every* stream.

**Escalation trigger:** "You said one connection. Packet loss rate is 2 percent. What happens to my 50 streams?"

**Answer.** HTTP/2 replaces the text protocol with binary frames ([RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html)): each request is a stream, frames from many streams interleave on one connection, and the server can respond in any order — the application-layer head-of-line blocking is genuinely gone, because a finished response is not queued behind a slow one. HPACK ([RFC 7541](https://www.rfc-editor.org/rfc/rfc7541.html)) attacks the header tax with static/dynamic tables and Huffman coding — repeated headers (`user-agent`, cookies) compress to a few bytes, and the 50 requests no longer carry 50 copies. Per-stream flow control lets a client throttle one stream without stalling others. The costs the strong answer volunteers: HPACK's dynamic table makes header compression *stateful and order-dependent*, which is why it cannot run in parallel across connections and why proxies re-encode; stream priorities turned out to be so complex that implementations diverged (and were dropped in HTTP/3); and — the escalation's target — all 50 streams share one TCP byte-stream. TCP guarantees ordered delivery *per connection*: one lost segment holds back every subsequent byte, including bytes for streams that lost nothing. At 2 percent loss, connection-level throughput collapses while the application multiplexes politely on top of a stalled pipe — HTTP/2 under loss can be *slower* than six parallel HTTP/1.1 connections, which were slow but independent. That measurement, not aesthetics, is what motivated HTTP/3.

## Level 3: The Transport-Layer HOL Problem — and QUIC's Answer

**What it tests:** whether the candidate can locate head-of-line blocking at each layer — HTTP framing, TCP ordering, TLS record decryption — and explain what QUIC restructures rather than merely relocating.

**Weak answer:** "HTTP/3 uses UDP so it's faster" — UDP is not faster; the redesign is what pays, and "faster" needs mechanisms.

**Strong answer:** explains that TCP's in-order byte stream couples all streams (retransmission head-of-line blocking), that TLS-over-TCP adds its own record-layer serialization, and that QUIC solves it by making each stream an independent ordered unit over unreliable UDP packets — loss on stream 7 stalls stream 7, nothing else — plus user-space deployment freedom that TCP's kernel home forbids.

**Escalation trigger:** "Why did they have to build a new transport on UDP? Why not fix TCP?"

**Answer.** The diagnosis is architectural: TCP's reliability model — one ordered byte stream per connection — is the head-of-line blocker, and it cannot be negotiated away because it is the protocol. Fixing it inside TCP would require changing kernel implementations and middleboxes on a decades timescale; QUIC ([RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html)) instead implements a stream-aware transport in *user space* over UDP, where each stream has its own loss recovery: a lost packet retransmits only the streams whose bytes were in it, and out-of-order packets for other streams are delivered immediately. The cryptographic integration matters as much as the multiplexing: QUIC encrypts essentially everything (header metadata too), merges transport and TLS 1.3 handshakes — connection establishment plus crypto in typically one round trip, versus TCP + TLS/1.2's three — and makes the handshake itself authenticated, eliminating the protocol-ossification problem where middleboxes mistook unencrypted TCP header fields for permissions. The honest caveats the strong answer names: UDP can be blocked or throttled by networks (QUIC has a cleartext version-negotiation and falls back), user-space receive costs more CPU than kernel TCP (mitigated by GSO and continuing work), and QUIC inherits UDP's connectionless weakness against spoofing unless the handshake's address validation is honored — the migration and connection-ID story is in [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md) and the internals in [QUIC Internals](../../networks/http/quic-internals.md).

## Level 4: Handshake Economics — 0-RTT, Resumption, and What Each Version Saves

**What it tests:** the latency-arithmetic rung: whether the candidate can count round trips per protocol version for a cold connection, a resumed one, and a resumed one sending early data — and say what 0-RTT *costs*.

**Weak answer:** "HTTP/3 is faster because of 0-RTT" — cannot count the RTTs, and does not know 0-RTT's replay problem.

**Strong answer:** counts: HTTP/1.1-over-TCP+TLS 1.2 is roughly 3 RTTs before first byte (TCP, TLS, request); TLS 1.3 saves one; QUIC merges transport and TLS handshakes into 1 RTT cold; session resumption plus 0-RTT early data approaches zero added RTT for repeat visitors — and names the price: 0-RTT data is replayable, so only idempotent requests qualify, and servers must deduplicate.

**Escalation trigger:** "A shopping-cart POST in 0-RTT data — what can go wrong?"

**Answer.** Counting first: cold HTTP/1.1 with TLS 1.2 costs TCP handshake (1 RTT), TLS handshake (2 RTT for 1.2, 1 for 1.3), then the request — the full taxonomy is the chain in [TLS Handshake](./tls-handshake.md), which owns the certificate and key-schedule depth this rung only counts. QUIC's contribution is merging: transport parameters ride inside the TLS 1.3 handshake, so cold connection is 1 RTT, and with resumption tickets the client can send *0-RTT* application data in its very first flight — no waiting for the handshake to finish. The replay problem is the escalation's answer: 0-RTT data is encrypted under keys derived without fresh server input, and an attacker who captures the first flight can replay it and the server may accept it *again* — an idempotent GET is harmless, but a non-idempotent POST (charge the card, book the order) can execute twice. Hence the rules: servers gate 0-RTT (size limits, single-use tickets, anti-replay windows), applications mark which requests are safe for early data, and frameworks treat it as an optimization for cacheable/GET traffic first. The senior synthesis: 0-RTT buys the *first request's* latency on repeat visits — a real win for API-heavy clients and page loads, a footgun for transactional first-writes — and the [TLS Handshake](./tls-handshake.md) chain's resumption rung carries the token mechanics in depth.

## Level 5: When Each Version Wins — the Judgment Rung

**What it tests:** design judgment: the candidate must stop narrating history and *choose* — per workload, per network, per client population — and defend the choice against the "newer is better" reflex.

**Weak answer:** "Use HTTP/3, it's latest" — version maximalism with no workload analysis.

**Strong answer:** matches versions to conditions: HTTP/1.1 remains correct for simple internal APIs and anything behind lossy middleboxes; HTTP/2 wins for API traffic and dense multiplexing over stable networks; HTTP/3 wins for lossy/mobile networks, high-churn connections, and connection migration — and can articulate the deployment realities (UDP blocked on some networks, proxy/interception appliances that only speak HTTP/1.1, the measurement habit of enabling HTTP/3 as a shadow first).

**Escalation trigger:** "Your API serves mobile clients on flaky networks and enterprise clients behind corporate proxies. What do you enable, and how do you roll it out?"

**Answer.** Serve HTTP/3 (with Alt-Svc advertisement) *alongside* HTTP/2, not instead of it: mobile clients on lossy networks gain per-stream loss isolation and connection migration — a phone moving from Wi-Fi to cellular survives because QUIC's connection ID decouples identity from the 4-tuple (the mechanics in [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md)); the enterprise proxies, meanwhile, may block UDP entirely, and those clients simply continue on HTTP/2 over TCP — the protocol negotiation (HTTPS record / Alt-Svc) makes coexistence the default rather than a cutover. The rollout discipline: enable HTTP/3 on a shadow or per-POP basis, watch handshake success rates, 0-RTT acceptance, and per-network failure classes (the observability habit from [Observability Pipeline](../connection-atlas/observability-pipeline.md)), and treat middlebox interference as an expected finding, not a bug. The judgment also runs backward: for an internal service mesh on a fat, low-loss network, HTTP/2 is entirely sufficient and HTTP/3 adds CPU for little gain; for a handful of low-QPS internal APIs, HTTP/1.1 simplicity with keep-alive costs nothing worth optimizing. The senior sentence the rung wants: "protocol version is a deployment property of your client population and network mix — measure, enable alongside, and let negotiation pick."

## How to Approach Unfamiliar Variations

The template for HTTP variations — "server push," "WebTransport," "why is my HTTP/2 slower," "gRPC over HTTP/3":

1. **Locate the queue.** Every performance complaint in HTTP reduces to: what is serializing, at which layer — request queuing (HTTP/1.1), packet-loss retransmission (TCP), record decryption (TLS), single connection coupling (HTTP/2). Name the layer and the fix space appears.
2. **Count round trips for the claim.** "Faster" claims become checkable: cold connect, resumed connect, early data — count RTTs per version and the comparison is arithmetic, not taste.
3. **Ask who is in the middle.** Middleboxes, proxies, and interception appliances are why pipelining died and why HTTP/3 encrypts metadata; any "why did the protocol do this oddly" question often answers "to survive the middle."
4. **For migration questions, check idempotency and negotiation.** New versions roll out alongside old ones via negotiation, and risky features (0-RTT) are gated by replay-safety. A variation asking "how do you adopt X" is asking "what is X's replay/interoperability hazard."

## Interview Questions

**Q: We enabled HTTP/2 and p99 got worse for some users. What is the likely mechanism?**
A: The single-connection coupling: users on lossy paths now multiplex all streams over one TCP connection, so each loss event stalls every stream — previously six HTTP/1.1 connections isolated the damage. Fix: enable HTTP/3 (per-stream loss recovery) for those clients, or keep connection parallelism for lossy classes; the diagnosis is correlating loss rate with the regression rather than assuming multiplexing is uniformly good.

**Q: Why was HTTP/1.1 pipelining abandoned when HTTP/2 multiplexing succeeded?**
A: Pipelining kept responses strictly ordered — one slow response head-of-line blocked everything behind it, and interleaved responses were impossible in a text protocol whose framing is inferred from delimiters. HTTP/2 succeeded because binary framing makes responses independently schedulable and because it arrived with a negotiation (`h2` via ALPN) that upgraded only between parties that both understood it — solving both the ordering problem and the broken-proxy problem that killed pipelining.

**Q: A team wants to shave startup latency for their API client. Currently: TCP + TLS 1.3 + request. What are the options, in order of effort?**
A: Keep-alive/connection reuse (already assumed), then TLS session resumption (1-RTT handshake on reconnect), then QUIC with its merged 1-RTT cold handshake and 0-RTT resumption for repeat connects — where only idempotent requests may ride the early data. Connection pooling on the client (the [Connection Pooling](./connection-pooling.md) analysis, with HTTP keep-alive as the same mechanism) often dominates all of it for chatty clients.

**Q: HPACK is stateful and order-dependent — why is that a problem for a proxy handling many connections?**
A: Each HPACK context is per-connection and depends on every prior header block being processed in order; a proxy terminating many upstream connections must maintain one state machine per connection, cannot parallelize header decoding within one, and must re-encode when forwarding between differently-versioned hops — real CPU and memory costs, and the reason HTTP/3 redesigned header compression as QPACK with explicit per-stream acknowledgments so it survives QUIC's out-of-order delivery.

## Key Takeaways

- HTTP/1.1's cost is serialized requests per connection plus per-connection setup; pipelining failed because responses stayed ordered and intermediaries broke it.
- HTTP/2 fixes the application layer with binary framing, per-stream scheduling, and HPACK header compression — and exposes the transport: one TCP connection couples all streams under packet loss.
- QUIC fixes the transport by making streams independent loss-recovery units over UDP, in user space, with integrated TLS 1.3 — the head-of-line story is told one layer at a time or not at all.
- Handshake economics count RTTs: 1.2 ≈ 3, 1.3 saves one, QUIC merges to 1, and 0-RTT resumption approaches zero for repeat visits — at the price of replayable early data, so only idempotent requests qualify.
- Version choice is a workload and network decision: enable HTTP/3 alongside HTTP/2, let negotiation choose, and measure per network class — never "latest version" by reflex.
- Every "odd" protocol design decision usually pays for itself against middleboxes, loss, or ossification; find the constraint before judging the design.

## Cross-References

- [TLS Handshake](./tls-handshake.md) — the sibling chain that owns certificates, resumption, and the key schedule this ladder only counts in RTTs.
- [TCP Lifecycle](./tcp-lifecycle.md) — the transport state machine and congestion control whose ordering behavior creates HTTP/2's transport-layer bottleneck.
- [URL to Page](./url-to-page.md) — the end-to-end chain where this protocol ladder sits in the full navigation story.
- [Connection Pooling](./connection-pooling.md) — keep-alive and reuse economics shared by HTTP clients and database pools.
- [HTTP/1.1](../../networks/http/http1.md), [HTTP/2](../../networks/http/http2.md), and [HTTP/3](../../networks/http/http3.md) — the book chapters behind each rung.
- [HPACK](../../networks/http/hpack.md) and [QPACK](../../networks/http/qpack.md) — the header-compression designs and their ordering constraints.
- [QUIC](../../networks/http/quic.md) and [QUIC Internals](../../networks/http/quic-internals.md) — the transport redesign in depth.
- [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md) — connection IDs, mobility, and the NAT-rebinding story.
- [RFC 9113 (HTTP/2)](https://www.rfc-editor.org/rfc/rfc9113.html), [RFC 9114 (HTTP/3)](https://www.rfc-editor.org/rfc/rfc9114.html), [RFC 7541 (HPACK)](https://www.rfc-editor.org/rfc/rfc7541.html), [RFC 9000 (QUIC)](https://www.rfc-editor.org/rfc/rfc9000.html) — the primary specifications for this chain's claims.
- [Observability Pipeline](../connection-atlas/observability-pipeline.md) — the measurement habit the rollout rung depends on.
