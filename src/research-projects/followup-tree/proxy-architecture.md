# Follow-up Tree: Proxy Architecture

## Overview

"What is a reverse proxy and why do we put one in front of our servers?" opens one of the most practical ladders in infrastructure interviews, because proxies sit at the seam where networking, security, and application design meet. Nearly every production request passes through at least one proxy — a CDN edge, a load balancer, an ingress controller, an API gateway — so the topic tests whether you understand the components you deployed or merely configured them. The ladder escalates through four honest follow-ups: the forward/reverse distinction (which is really about trust, not direction), TLS termination (what you give up when encryption ends at the edge), the X-Forwarded-For/X-Forwarded-Proto trust problem (the most common real-world proxy bug), and buffering (where the proxy quietly becomes the bottleneck). The chain overlaps deliberately with others: routing and health checks belong to [Load Balancing](./load-balancing.md), edge policy to [API Gateway](./api-gateway.md), and handshake mechanics to [TLS Handshake](./tls-handshake.md) — this page owns the proxy itself: what it terminates, what it forwards, and what it costs.

## The Opening Question

**"What is a reverse proxy, and why do we put one in front of our servers?"**

The expected core answer: a reverse proxy sits in front of backend servers and accepts requests on their behalf — clients talk to the proxy, it forwards to an internal pool, and responses flow back through it. The *reverse* prefix distinguishes it from a *forward* proxy, which sits in front of clients. Reasons to deploy one: TLS termination and centralized certificate management, load distribution, connection reuse toward origins, caching and compression, path/header routing, and a single enforced point for authentication, rate limiting, and logging. [nginx's proxy module documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) is the artifact most engineers have actually configured, and the [reverse proxy](../../networks/load-balancing/reverse-proxy.md) chapter covers the mechanism in depth.

Why this answer is correct: it never says "a proxy forwards traffic" and stops. Every listed reason is a *policy* that would otherwise be scattered across every backend — and centralizing policy is the real justification for the hop. Interviewers listen for "policy" because it predicts the escalation: once policy lives at the proxy, the follow-ups are what it can see (TLS), what it can trust (headers), and what it can absorb (buffering).

## Level 2: Forward vs Reverse — Why Does the Direction of Trust Matter?

**What it tests:** whether "proxy" is a configured box to you or a trust-architecture concept — who installs it, whose interests it serves, and what that implies for the traffic passing through it.

**Weak answer:** "A forward proxy is for clients and a reverse proxy is for servers" — topology trivia with no security implication drawn from it.

**Strong answer:** a forward proxy is installed by the *client's* organization (egress control, filtering, caching for the client population, anonymity), and servers usually cannot trust or even see who is behind it; a reverse proxy is installed by the *service's* organization (ingress policy, TLS, routing, origin protection), and the client must trust it completely. Same relay mechanics, opposite principals, opposite guarantees.

**Escalation trigger:** "Your application reads X-Forwarded-For to log client IPs. A user sends the header themselves. What happens — and why does forward-vs-reverse explain it?"

**Answer.** A reverse proxy is the first hop of your own infrastructure, so it has the right — and the obligation — to *overwrite* client-supplied forwarding headers with ground truth: it knows the actual peer address of each connection it accepts. An application that trusts X-Forwarded-For without knowing *which proxy wrote it* is trusting whatever the last writer claimed, and any client can claim anything. This is the trust distinction made dangerous: the header mechanism assumes an honest intermediary in the middle of the chain. The same lens explains the rest of the rung: a forward proxy can require *client* authentication (it serves the client's org); a reverse proxy terminates TLS for its origins and is deliberately the public endpoint, entitled to make claims about each request it accepted. The frame interviewers want: topology says where the box sits; the trust question — who installed it, whose policy it enforces, which claims it may make — says what its outputs mean. The header mechanics are the next rung, and the identity half (what an edge claim is worth) is developed in [Auth, Identity, and Session](../connection-atlas/auth-identity-session.md).

## Level 3: TLS Termination — What Ends at the Edge?

**What it tests:** whether you understand that "HTTPS" has a decryption point you can choose, and whether you can defend the choice in both directions.

**Weak answer:** "The proxy handles HTTPS so the backend doesn't have to" — no model of what "handles" means (decrypt? re-encrypt? passthrough?) and no awareness that a plaintext moment exists at all.

**Strong answer:** names the three postures — terminate-and-re-encrypt, terminate-only (backend hop in plaintext), and TLS passthrough (SNI-based routing; decryption at the origin) — and what each costs: termination buys inspection, header-based routing, and centralized certificates but makes the proxy a plaintext vantage point; passthrough preserves end-to-end confidentiality but blinds every header-based policy. Connects termination to protocol features: HTTP/2 and header routing are only available where someone can read headers.

**Escalation trigger:** "Compliance says no plaintext on the internal network. Your gateway routes by header. How do both requirements survive?"

**Answer.** Terminate at the edge and immediately re-encrypt toward the backend — TLS ends *logically* (the edge must see plaintext headers to route) but never travels *physically* in cleartext, which is what the compliance constraint prohibits. Backends verify the proxy with mutual TLS or trust the internal segment, and the client's view of encryption is preserved because the edge presented its own certificate. What the rung really tests is naming what is lost at termination: a plaintext vantage is a security boundary (a compromised proxy sees everything — the concrete reason [HTTPS Means Secure](../misconceptions/https-means-secure.md) is a documented misconception), an audit boundary (logs can contain sensitive headers), and a capability boundary (the only place path-based routing, rewriting, and compression can happen). Passthrough inverts the trade: the proxy degrades to an L4 router seeing only SNI and IP — exactly what protocols that cannot tolerate an inspecting intermediary demand, such as services wanting end-to-end mTLS, or QUIC where the proxy would have to terminate the transport, not just TLS. The certificate-lifecycle work that makes termination survivable is the [TLS Handshake](./tls-handshake.md) chain; the protocol layer it unlocks is [HTTP Protocol Evolution](./http-protocol.md).

## Level 4: X-Forwarded-For and X-Forwarded-Proto — Which Claims Do You Believe?

**What it tests:** the highest-frequency real-world proxy bug: whether you know forwarding headers are *claims written into the request stream*, and can state the rightmost-trusted rule precisely.

**Weak answer:** "X-Forwarded-For contains the client's IP" — treats a client-writable header as an authenticated field, which is exactly the vulnerability.

**Strong answer:** explains append-vs-overwrite semantics: every proxy that understands the convention *appends* the address of the peer it accepted the connection from, so the list reads left-to-right from least to most trustworthy; the correct client IP is derived by walking from the right, skipping entries added by proxies you control, and stopping at the first untrusted hop. Knows X-Forwarded-Proto (the original-scheme claim), the standardized [RFC 7239 Forwarded header](https://www.rfc-editor.org/rfc/rfc7239) that bundles host/proto/for into one field, and that the bug class disappears when the application consumes these headers only after exactly one trusted rewriting hop.

**Escalation trigger:** "A rate limiter keyed on X-Forwarded-For starts failing after you add a second proxy layer — and some users bypass it entirely. Diagnose."

**Answer.** Two live failure modes compound. Bypass: if the first proxy *appends to* rather than sanitizes the client-supplied list, an attacker sends `X-Forwarded-For: 1.2.3.4` and the application sees `1.2.3.4, client, proxy1, proxy2` — walking from the left trusts the attacker's lie, yielding a fresh "IP" per request and defeating the limiter. False block: a second proxy is added but the application's trusted-proxy count still assumes one layer, so derivation walks past the real client into addresses that all look identical, and every user buckets together. The diagnosis procedure is the senior content: enumerate the physical hops; fix a per-hop rewrite policy (the outermost proxy sets the header from its socket peer and *discards* client-supplied values; inner proxies append only their peer); count trusted depth exactly — deriving either in the innermost proxy (writing a clean header the app trusts unconditionally) or in the app with correct trusted-depth configuration. [MDN's X-Forwarded-For reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For) documents the append semantics and the standard warning about them. The durable lesson generalizes past this header: any edge-derived claim — client IP, protocol, host, geolocation — has a trust boundary at the proxy that wrote it, and consuming such claims without knowing that boundary is consuming unauthenticated input. The sibling assumptions project audits exactly this class in [Proxy Header Assumptions](../assumptions-hunt/proxy-header-assumptions.md) — it owns the per-header claim-by-claim breakdown; this rung owns the trust-chain mechanics.

## Level 5: Buffering — When Does the Proxy Become the Bottleneck?

**What it tests:** whether you know what the proxy does with request and response *bodies* — the part everyone forgets — and can reason about the proxy as a finite-memory, finite-CPU component.

**Weak answer:** "The proxy just forwards bytes" — false in the default configuration of nearly every reverse proxy, and it leads directly to production surprises with uploads, streams, and WebSockets.

**Strong answer:** distinguishes buffered mode (the proxy reads the whole body into memory or a disk spool before forwarding — the default for good reasons: slow clients decoupled from fast backends, retryability, inspection, logging) from streaming mode (bytes flow as they arrive; latency-sensitive, but backends now bear slow clients directly), and names the failure signature of each: buffered mode turns large uploads into disk I/O on the proxy; streaming mode couples a slow client to a backend connection for the duration. Identifies proxy-as-bottleneck signatures: CPU saturation from TLS handshakes and header processing, fd or connection exhaustion, disk latency on spooled bodies, and naive buffering's incompatibility with server-push (SSE, WebSockets) where responses are unbounded.

**Escalation trigger:** "After migrating large-file uploads to go through the gateway, gateway disk I/O spikes and uploads fail intermittently. What changed and what are your options?"

**Answer.** The gateway is buffering every upload to local disk (spooling the full body before forwarding), so gateway disk is now the throughput ceiling and a failure point — full disk or slow spool surfaces as client-visible upload failures the backends never saw. Options, in order: disable request buffering for the upload route so bytes stream through (the backend now owns slow-client risk — pair with read timeouts and the connection-lifetime analysis in [Backpressure](../connection-atlas/backpressure.md)); keep buffering but move it to a service designed for it (signed direct-to-object-storage uploads, which remove the body from the request path entirely); or buffer to faster storage and accept the cost. The judgment content is recognizing when the proxy *should* be in the data path at all: buffering is a feature for small bodies (inspection, logging, retryability, decoupling) and a liability for large or unbounded ones (uploads, streams, long-lived connections). The same arithmetic applies to CPU: terminating TLS for thousands of new connections per second is real compute, and the fix is resumption and connection reuse — the economics are the [TLS Handshake](./tls-handshake.md) chain's RTT rung. When the honest answer is "the proxy tier is the bottleneck," the moves are the load-balancing chain's: add proxies, partition by route (streaming routes bypass buffering tiers), or push the feature out of the proxy into dedicated infrastructure.

## How to Approach Unfamiliar Variations

1. **Reduce every proxy question to trust boundaries.** "Can this component sit client-side? What claims does it produce, and which would you believe?" A CDN, an egress filter, a mesh sidecar, and an API gateway are the same relay with different principals — the trust frame answers variants you have never deployed.
2. **Ask what the hop can see, because visibility defines capability.** Terminate TLS and you gain routing, rewriting, logging — and accept a plaintext vantage; passthrough and you keep confidentiality but lose header-based policy. Any variation is answered by what that layer can read.
3. **Price the buffering default before assuming streaming.** When a variation involves bodies — uploads, exports, server-sent events — state the memory/disk consequence of buffered forwarding first; most "mysterious" proxy failures are bodies parked on the wrong tier's disk.
4. **Treat derived headers as unauthenticated input until proven otherwise.** Whatever the variation adds — more hops, a mesh, a new gateway — the procedure is identical: enumerate hops, fix the per-hop rewrite policy, count trusted depth, then consume the claim.

## Interview Questions

**Q: Your backend logs show every request coming from 10.0.1.5. Why, and what is the correct fix?**
A: The backend sees only its TCP peer — the reverse proxy — because connections to the backend originate there. The fix is not logging changes: the proxy must communicate the real client (append its socket peer to X-Forwarded-For, or emit RFC 7239 Forwarded), and the backend must trust exactly that one hop. Any looser trust reintroduces the spoofing hole.

**Q: Why might you deliberately choose TLS passthrough and lose all header visibility at the edge?**
A: When end-to-end confidentiality or client-verifiable identity matters more than edge routing: services needing mTLS to the real client, compliance regimes where a decrypting intermediary is unacceptable, or transports the proxy cannot speak (QUIC). The cost is paid elsewhere — routing moves to SNI/IP only, and header-based policy moves to the origin.

**Q: A user complains your site "remembers" an IP that is not theirs. What happened?**
A: Almost always a forwarding-header derivation bug: some hop trusts client-supplied X-Forwarded-For, the user (or a VPN or injector) set it once, and downstream consumers believed the first value instead of deriving from the rightmost trusted entry. The fix is the rightmost-trusted rule with an explicit trusted-proxy depth, not special-casing the user.

**Q: Your API gateway's CPU doubled after enabling TLS termination for a client population with short-lived connections. What is happening and what are two mitigations?**
A: Full handshakes dominate: each new connection pays asymmetric public-key work at the terminating edge. Mitigations: session resumption (tickets/IDs) so returning clients skip the expensive flight, and longer-lived connections (keepalive tuning, client-side pooling) to amortize handshakes across requests. At genuinely huge scale, scale the termination tier or split termination from L7 policy.

## Key Takeaways

- Forward and reverse describe *whose policy* the proxy serves, not just where it sits — and the trust direction determines which claims in the request stream are believable.
- TLS termination is a visibility decision: someone must read headers to route by them, and that someone is a plaintext vantage point; re-encryption preserves compliance, passthrough preserves end-to-end guarantees.
- X-Forwarded-For is a list of claims ordered least-to-most trustworthy; the correct answer derives from the rightmost trusted proxy, and anything else accepts unauthenticated client input.
- Proxy buffering is a real memory-and-disk contract: it decouples slow clients for small bodies and becomes the bottleneck for large or unbounded ones.
- The proxy is a finite machine — TLS CPU, file descriptors, spool disk — and "just add a hop" is a capacity decision like any other.

## Cross-References

- [Load Balancing](./load-balancing.md) — the sibling chain that owns distribution algorithms, health checks, and the L4/L7 split treated here only as context.
- [API Gateway](./api-gateway.md) — the reverse proxy with opinionated policy: auth, rate limits, versioned routing as the next escalation of the same box.
- [TLS Handshake](./tls-handshake.md) — what termination actually ends: flights, certificates, resumption economics, certificate lifecycle.
- [HTTP Protocol Evolution](./http-protocol.md) — the protocol features termination unlocks and the QUIC cases where proxies must change shape.
- [URL to Page](./url-to-page.md) — where the proxy tiers sit in the end-to-end walk of a request.
- [Redis Caching](./redis-caching.md) — proxy-level response caching and the invalidation machinery it shares with application caches.
- [Connection Pooling](./connection-pooling.md) — the keepalive and upstream-connection arithmetic that determines proxy-to-backend capacity.
- [Load Balancing and Partitioning](../connection-atlas/load-balancing-partitioning.md) — the cross-topic map connecting the proxy tier to sharding and distribution.
- [Auth, Identity, and Session](../connection-atlas/auth-identity-session.md) — what an edge-derived identity claim is worth; sessions versus the proxy tier.
- [Backpressure](../connection-atlas/backpressure.md) — the streaming-mode contract when the body has no end and consumers have limits.
- [HTTPS Means Secure](../misconceptions/https-means-secure.md) — the plaintext vantage point termination creates, as a documented misconception.
- [Reverse Proxy](../../networks/load-balancing/reverse-proxy.md) — the book chapter on forwarding mechanics, header rewriting, and upstream configuration.
- [L4 vs L7](../../networks/load-balancing/l4-vs-l7.md) — the layer split that decides what a proxy tier can see and therefore do.
- [HTTPS](../../networks/http/https.md) — the protocol underpinnings of termination, re-encryption, and header claims.
- [CDN: How It Works](../../networks/cdn/how-it-works.md) — the CDN as a distributed reverse proxy with caching policy at global scale.
- [Forwarded (RFC 7239)](https://www.rfc-editor.org/rfc/rfc7239) — the standardized forwarding header and its trust model (verified this session).
- [MDN: X-Forwarded-For](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For) — the de facto header's exact semantics and misuse warnings (verified this session).
