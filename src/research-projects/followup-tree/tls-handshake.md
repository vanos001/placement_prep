# Follow-up Tree: TLS Handshake

## Overview

"What happens during a TLS handshake?" looks like a security question but escalates into a performance and trust question, which is why it appears in infrastructure interviews for backend, platform, and SRE roles alike. The ladder runs from the recited packet sequence (a weak answer) through certificate-chain validation, session resumption and 0-RTT replay, and finally into the privacy and revocation wrinkles — SNI leakage, ECH, OCSP stapling — that separate candidates who have debugged handshakes from candidates who have read about them. The thread that ties every rung together is *trust establishment paid for in round trips*: each follow-up either asks what you are trusting, how you verified it, or how many RTTs the verification cost. This page keeps the TCP three-way handshake out of scope — [TCP Lifecycle](./tcp-lifecycle.md) owns that chain — and focuses on what TLS adds on top; the book-level treatment lives in [TLS Deep Dive](../../networks/security/tls-deep-dive.md) and [HTTPS](../../networks/http/https.md). Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"What happens during a TLS handshake?"**

The expected core answer: after the TCP handshake completes (one RTT — see [TCP: Three-Way Handshake](../../networks/tcp/three-way.md)), the client sends a `ClientHello` with its supported versions, cipher suites, and key-share material; the server replies with `ServerHello`, its certificate chain, and proof it holds the private key; the client validates the chain against its trust anchors, both sides derive session keys from the key exchange, and the finished messages confirm integrity — after which application data flows. The version difference is the senior detail to volunteer up front: **TLS 1.2** needs two full round trips (Hello, then key exchange and Finished), while **TLS 1.3** compresses this to *one* round trip — client and server exchange key shares and finish in a single flight ([RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html) is the spec; [RFC 5246](https://www.rfc-editor.org/rfc/rfc5246.html) covers TLS 1.2).

A weak answer recites "asymmetric then symmetric encryption" without naming messages, versions, or round trips. The strong answer names the flight structure, the RTT arithmetic against TCP's own RTT, and why 1.3 achieved the saving — key shares sent *in the first flight* instead of a separate negotiation. The follow-up that escalates: **"How does the client actually know that certificate is trustworthy?"** — which moves the ladder from mechanics to trust.

## Level 2: Certificate Chains and Trust Anchors

**What it tests:** whether "the browser trusts the certificate" is a mechanism you can decompose — path building, signature verification, hostname matching — or a slogan.

**Weak answer:** "The CA signs the certificate and the browser checks it" — no chain, no intermediates, no hostname verification, no revocation.

**Strong answer:** walks the chain from leaf to a root in the trust store, explains that intermediates exist to keep root keys offline and enable rotation, and distinguishes *identity validation* (does this cert belong to the name I contacted?) from *encryption* (can anyone read the traffic?).

**Escalation trigger:** "Your server presents one certificate — why does the TLS record carry three?"

**Answer.** The server sends its leaf certificate plus the intermediate CA certificates, because the client may know only the root: validation means building a path leaf → intermediate → root, verifying each signature with the issuer's public key, checking validity windows, key usage, and — the rung's most-missed step — that the leaf's SAN (Subject Alternative Name) matches the hostname the client actually contacted. Clients ship a *trust store* of root CAs; those roots are called trust anchors, and everything above them is downstream of their operational security. Two consequences earn credit: first, an intermediate's compromise is containable by revocation and rotation in a way a root's is not, which is why roots sit offline; second, the server is *responsible for sending the chain* — a misconfigured server that omits its intermediate works in the ops team's browser (which cached the intermediate from a previous visit) and fails for everyone else, the classic "works for me" TLS bug.

The design twist the strong candidate volunteers: certificate *pinning* — trusting only a specific key instead of the whole CA ecosystem — trades CA compromise resilience for operational fragility, which is why browser pinning was retired in favor of mechanisms like Certificate Transparency (public, auditable issuance logs) and why mobile apps still pin but must ship an escape hatch. Trust-store questions generalize: who audits the anchors, what happens when a CA mis-issues, and why "the trust anchor set is a policy decision, not a technical constant" is the sentence that ends this rung well. The repo's treatment of these primitives sits in [Security & Crypto Assumptions](../assumptions-hunt/security-crypto.md), and the canonical failure of TLS-library code is [Heartbleed (2014)](../failure-casebook/heartbleed-2014.md) — a bug in the *implementation*, not the protocol, worth citing when asked "is TLS itself safe."

## Level 3: Session Resumption, PSK, and 0-RTT Replay

**What it tests:** whether you know handshakes are cacheable — and can articulate the exact guarantee 0-RTT gives up to buy its latency.

**Weak answer:** "TLS sessions can be reused to make it faster" — no mechanism, no distinction between 1.2 resumption and 1.3 PSK, and no awareness that 0-RTT data can be replayed.

**Strong answer:** explains session tickets or session IDs as cached key material, maps TLS 1.2's 1-RTT resumption and TLS 1.3's PSK resumption onto the flight structure, and states precisely what 0-RTT early data loses: replay protection, because early data is sent before the server contributes any freshness.

**Escalation trigger:** "Why is 0-RTT data safe to send but not safe to accept for payments?"

**Answer.** A full handshake costs the client its key agreement anyway, so TLS lets both sides cache established secrets: in TLS 1.2 via session IDs or session tickets (an encrypted state blob the server hands back), in TLS 1.3 via tickets that seed a *pre-shared key* (PSK) for the next handshake — turning an expensive certificate-authenticated handshake into a cheaper symmetric one. Latency-wise this matters at the margin that counts: TLS 1.3 full handshake is 1-RTT, PSK resumption is also 1-RTT but lighter to compute, and **0-RTT** lets the client send application data *in its first flight*, eliminating the wait entirely for resumed connections. That is why CDNs love it for GETs — and why the rung exists, because the same flight that carries early data carries it *before* the server has contributed fresh key material, so an attacker who captures the flight can replay it and have the server process it twice ([RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html) acknowledges this by design; the fix is application-level).

The senior framing: 0-RTT is safe exactly when the request is **idempotent** — GETs, cache lookups — and unsafe for anything with side effects, unless the application deduplicates (single-use tokens, request IDs) or the server simply disables early data. The vocabulary that earns credit: "replay window," "anti-replay service," and the observation that idempotency is doing double duty here — the same property that makes retries safe makes 0-RTT safe, which is why payment APIs reject early data while static CDNs enable it. This connects outward in two directions: the retry-and-idempotency discipline in [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md), and the transactional machinery in [ACID Transactions](./acid-transactions.md) when "exactly once" is demanded below the application where TLS cannot provide it.

## Level 4: SNI, ECH, Revocation, and the Latency Ledger

**What it tests:** the expert rung — privacy of the handshake itself (SNI leakage and ECH), revocation checking (OCSP stapling), and the ability to do handshake latency math against connection reuse.

**Weak answer:** knows the acronym SNI but not what it leaks, has heard "check revocation" without knowing who pays for the check or what happens when the check itself times out, and cannot quantify handshake cost.

**Strong answer:** states that ClientHello historically carries the hostname in cleartext (SNI), so middleboxes and censors can see and filter which host you contact, and that Encrypted Client Hello (ECH) encrypts it; explains OCSP stapling as the server fetching and stapling a signed revocation statement so *clients* do not make a blocking query to a third party; and can compute cold versus warm connection costs.

**Escalation trigger:** "Count the round trips before the first HTTP request on a cold connection — then make it cheaper."

**Answer.** The ledger, cold and full: DNS (often cached), TCP three-way (1 RTT), TLS 1.3 (1 RTT) or TLS 1.2 (2 RTTs) — so HTTPS over TLS 1.3 costs two sequential RTTs before the request can even ride the wire, and every one of them compounds with the network's RTT (100 ms RTT means ~200 ms before first byte, before the server does any work). The attack list on that number is the design content: session resumption and PSK (Level 3), connection reuse and pooling — keep-alive means the handshake is amortized over many requests, which is why HTTP/1.1 keep-alive and multiplexed HTTP/2 both change the economics (see [HTTP/1.1](../../networks/http/http1.md)) — TLS False Start and TCP Fast Open for the truly latency-starved, and QUIC, which folds transport and cryptographic handshakes into one flight and makes resumption 0-RTT-native (see [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md)). The senior discipline is measuring the waterfall first, because a handshake that is parallel to nothing is the only kind that hurts.

The privacy half: SNI (Server Name Indication, [RFC 6066](https://www.rfc-editor.org/rfc/rfc6066.html)) exists so a server hosting many certificates can pick the right one — but it puts the hostname in the clear in ClientHello, visible to any on-path observer even when everything else is encrypted. ECH (Encrypted Client Hello — see [TLS ECH](../../networks/protocols/tls-ech.md)) encrypts the inner SNI under a public key the client learns from DNS, at the cost of protocol complexity and deployment coordination; when asked, state its status honestly as a deployable but still-maturing extension rather than a universal default. Revocation: a stapled OCSP response ([RFC 6960](https://www.rfc-editor.org/rfc/rfc6960.html) defines OCSP) lets the server prove at handshake time that its certificate was not revoked, removing a client-side query that would otherwise add latency and a privacy leak — and whose failure mode, soft-fail, quietly degrades to "accept anyway," the honest answer to "does revocation checking actually work in practice."

## How to Approach Unfamiliar Variations

The template for TLS variations — "make the handshake faster," "what does mTLS change," "why did this client reject our cert":

1. **Split the handshake into its three contracts: authentication, key agreement, and freshness.** Every variation — client certificates (mTLS adds mutual authentication), PSK-only modes (drop certificates entirely), renegotiation (changed freshness rules) — is a change to exactly one contract. Name the contract, then the consequence.
2. **Answer latency questions in RTTs, not milliseconds.** Recount the sequential flights (TCP, TLS, request) for the specific version and resumption state; a "slow handshake" complaint is usually one added flight or a broken resumption, and the waterfall shows which.
3. **Trust questions resolve to the trust anchor set and the name check.** "Why is this certificate rejected" is path building: expiry, missing intermediate, hostname mismatch, or an anchor that is not anchored — diagnose in that order.
4. **Treat every latency recovery as a trade against a security property, and name the property.** Resumption trades server-side state or ticket key security; 0-RTT trades replay protection; stapling trades the freshness of revocation information. Saying the property out loud is what the top rung scores.

## Interview Questions

**Q: Your p95 TTFB jumped 100 ms after a load balancer change. TLS is suspect. What exactly would you look at?**
A: One added RTT in the handshake, which usually means TLS 1.3 stopped being negotiated (version fallback to 1.2) or resumption broke (session tickets not shared across LB nodes). Check the negotiated version and whether tickets/resumption across the fleet share state; a certificate chain change that grew the chain can also add a validation stall. The 100 ms constant jump across requests smells like exactly one sequential flight, not slower crypto.

**Q: Why do some CDNs enable 0-RTT only for GET requests?**
A: Because 0-RTT early data carries no server freshness, an attacker who captures the first flight can replay it; a replayed GET re-executes a read, which is harmless, while a replayed POST could double a payment. Idempotency is the dividing line — enable early data where replay is a no-op, or add application-level deduplication (request IDs, single-use tokens) where it is not.

**Q: A customer's browser fails certificate validation, but curl on your server succeeds. Diagnosis?**
A: Path building differs: the server likely sends an incomplete chain and curl's store happens to have the intermediate cached, or the two environments have different trust anchors. Inspect the served chain (`openssl s_client`), confirm the leaf's SAN matches the hostname, and fix the server to send leaf plus intermediates — never rely on client-side caching of intermediates.

**Q: What does mTLS change about the handshake, and where is it actually used?**
A: The client presents its own certificate and the server validates it, making authentication mutual — the same chain-validation machinery run in both directions, typically with a private or internal CA as anchor. It is the standard for service-to-service mesh identity (sidecars validating each other) and zero-trust internal networks, where machine identity replaces network location as the trust boundary.

## Key Takeaways

- The handshake is trust establishment paid in round trips: TLS 1.3 does it in one RTT where 1.2 needed two, because key shares ride the first flight.
- Validation is chain building — leaf, intermediates, root anchor — plus the hostname check; servers must send the full chain, and a missing intermediate is the classic works-for-me TLS bug.
- Resumption caches established secrets (session tickets, PSK); 0-RTT removes the last RTT and, by design, gives up replay protection — safe for idempotent requests only.
- SNI leaks the hostname in cleartext; ECH encrypts it; OCSP stapling moves revocation proof to the server so clients avoid a blocking third-party query.
- Cold-connection cost is two sequential RTTs (TCP + TLS 1.3) before first byte; reuse, resumption, and QUIC are all attacks on that count — measure the waterfall before optimizing.

## Cross-References

- [TCP Lifecycle](./tcp-lifecycle.md) — the handshake TLS rides on: three-way setup, TIME_WAIT, and connection economics.
- [URL to Page](./url-to-page.md) — the parent chain; rung 2 counts these same RTTs end to end.
- [TLS Deep Dive](../../networks/security/tls-deep-dive.md) — key schedules, cipher suites, and record-layer internals beyond this ladder.
- [HTTPS](../../networks/http/https.md) — the HTTP-layer view of TLS termination and configuration.
- [TCP: Three-Way Handshake](../../networks/tcp/three-way.md) — the RTT this stack sits on top of.
- [TLS ECH](../../networks/protocols/tls-ech.md) — Encrypted Client Hello mechanics and deployment status.
- [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md) — where the TCP+TLS handshake stack is heading.
- [HTTP/1.1](../../networks/http/http1.md) — keep-alive and the connection-reuse economics this page's ledger assumes.
- [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md) — the idempotency discipline that decides where 0-RTT is safe.
- [Security & Crypto Assumptions](../assumptions-hunt/security-crypto.md) — the hidden assumptions behind "encrypted means trusted."
- [HTTPS Means Secure](../misconceptions/https-means-secure.md) — what TLS does and does not promise, documented as a misconception.
- [Heartbleed (2014)](../failure-casebook/heartbleed-2014.md) — protocol-safe, implementation-broken: the canonical TLS-library failure.
- [ACID Transactions](./acid-transactions.md) — why "exactly once" belongs to transactions, not handshakes.
- [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html), [RFC 5246](https://www.rfc-editor.org/rfc/rfc5246.html), [RFC 6066](https://www.rfc-editor.org/rfc/rfc6066.html), [RFC 6960](https://www.rfc-editor.org/rfc/rfc6960.html) — TLS 1.3, TLS 1.2, SNI, and OCSP.
