# REST vs gRPC: Public HTTP APIs vs Strong-Contract Internal RPC

## Overview

"REST or gRPC?" is usually asked as a style preference, but it is really three questions at once: **where the contract lives**, **who the client is**, and **what the network is allowed to do to the exchange**. REST over HTTP makes the contract a *social* convention — JSON documents, verbs, status codes, [RFC 9110](https://datatracker.ietf.org/doc/html/rfc9110) semantics — that any browser, curl invocation, or third-party engineer can already speak, and that any intermediary is allowed to inspect, cache, or transform. gRPC makes the contract a *compiled artifact* — a `.proto` schema run through code generation — over a multiplexed HTTP/2 session designed for machine-to-machine calls, with streaming, deadline propagation, and a binary message format.

Neither option is the modernized version of the other. gRPC standardizes what internal RPC frameworks always needed (multiplexing, four call shapes, per-call deadlines, generated stubs); REST standardizes what the web needed (reachability, cacheability, a uniform interface that survives decades of client churn). This page runs the [handbook framework](./index.md) over the choice. The preview: **REST pays verbosity and weaker contracts for universality and cacheability; gRPC pays universality for efficiency, streaming, and contract strength** — and the hybrids (gRPC-Web, JSON transcoding, REST-plus-protobuf) exist because each pure model fails in a characteristic way.

## Step 1: The Problem and Its Constraints

The workload: a service exposes operations; callers invoke them; the calls cross networks that include load balancers, proxies, and sometimes browsers. The constraints that actually decide the answer:

- **Caller population.** Browsers and third-party developers cannot be forced to install generated clients; internal services can. A fleet of two hundred polyglot microservices with quarterly API churn has a different contract-governance problem than one public API consumed by ten thousand anonymous integrators.
- **Contract governance.** Can you ship and version SDKs to every caller? If yes, wire-format changes are absorbed by regeneration. If no, the contract must be self-describing and tolerant — the JSON "tolerant reader" path.
- **Caching and intermediaries.** Do responses have cache semantics that a CDN or proxy should exploit, or is every call authenticated and non-idempotent? [HTTP caching](https://datatracker.ietf.org/doc/html/rfc9111) only works if the intermediary understands the protocol.
- **Latency, QPS, and payload profile.** Ten calls per second with 2 KB payloads makes serialization format irrelevant; two million calls per second with 200-byte payloads makes per-call overhead the dominant cost.
- **Streaming.** Is the exchange a unary request/response, or a sequence (client upload, server feed, bidirectional)? The four gRPC call shapes exist because one shape does not fit all.
- **Deadline propagation.** In a call chain ten deep, does a deadline set at the edge travel to every dependency, so the whole path fails fast instead of piling up? That requires the protocol to carry deadlines as data.

## Step 2: The Mechanisms

### Option 1: REST over HTTP — the uniform interface

- **Resources, verbs, and status codes.** [RFC 9110](https://datatracker.ietf.org/doc/html/rfc9110) defines method semantics (GET safe and idempotent, PUT/DELETE idempotent, POST neither) and a status taxonomy. A client that has never seen your API can already retry a `GET`, must not retry a `POST` blindly, and can branch on status classes. That shared behavioral vocabulary is the uniform interface Roy Fielding's dissertation (2000) identified as the web's load-bearing property.
- **Cacheability.** `Cache-Control`, `ETag`, and `If-None-Match` let any intermediary between client and origin serve or revalidate responses ([RFC 9111](https://datatracker.ietf.org/doc/html/rfc9111)). A GET that says `max-age=60` is served by the CDN edge closest to the caller; the origin never sees it. This is a mechanism, not a feature flag: the caching is written into the protocol and understood by every conforming intermediary.
- **Reachability.** Everything that can make an HTTP request can call you — browsers, spreadsheets, command-line tools, and the entire intermediary ecosystem (proxies, gateways, inspection tooling). There is no client library to distribute and no codegen step to gatekeep.
- **Evolvability.** JSON's rule of evolution is "additive fields are safe, unknown fields are ignored by tolerant readers." The contract is enforced socially (schema files, linters, contract tests) rather than by the wire format. See [API contracts](../assumptions-hunt/api-contracts.md) for the assumptions this rests on.
- **The HTTP/1.1 tax.** One in-flight request per connection (pipelining is effectively dead), text parsing on both ends, verbose headers repeated per request. HTTP/2 and HTTP/3 fix the multiplexing part (see [HTTP/2](../../networks/http/http2.md) and [HTTP/3](../../networks/http/http3.md)) — which is exactly the part gRPC takes for granted.

### Option 2: gRPC — the compiled contract

- **HTTP/2 underneath.** gRPC rides [HTTP/2](../../networks/http/http2.md): binary framing splits a connection into independent streams, HPACK compresses repeated headers, and one long-lived TCP connection carries thousands of concurrent calls. The gRPC [documentation](https://grpc.io/docs/) specifies the mapping: request headers, length-prefixed message frames, and **trailers** that carry the final status (`grpc-status`, `grpc-message`) after the body.
- **Protobuf messages.** A field is encoded as a tag — field number plus wire type — followed by a value. Unknown field numbers are skipped on the wire, so a new field does not break an old reader; renumbering or reusing a field number does, which is why the style guides treat field numbers as permanent identifiers. This is a *mechanical* compatibility rule the tooling enforces.
- **Code generation.** The `.proto` file is the single source of truth; stubs are generated for every supported language. The contract drift that plagues hand-written REST clients (stale Postman collections, outdated wiki pages) becomes a build failure instead.
- **Four call shapes.** Unary, server-streaming, client-streaming, and bidirectional streaming are first-class. A server-streaming call keeps the HTTP/2 stream open and pushes frames — no polling, no WebSocket bolt-on.
- **Deadline propagation.** A gRPC call carries a `grpc-timeout` header; libraries propagate it automatically across the whole call chain. A frontend deadline of 200 ms reaches the seventh-hop dependency, which fails fast rather than queueing work the caller will abandon. This is the mechanism behind fail-fast behavior in large microservice fleets — and it interacts with retries and [circuit breakers](../../distributed/microservices/circuit-breakers.md).
- **The connection model tax.** A gRPC channel is typically one (or a few) HTTP/2 connections, kept alive for hours. That is efficient — and it breaks naive load balancing, as Step 5 shows.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | REST over HTTP | gRPC over HTTP/2 |
|----------|----------------|-------------------|
| Contract form | Social: JSON schema files, docs, contract tests | Mechanical: `.proto` + generated stubs; drift is a build error |
| Message format | JSON text; verbose, human-readable, debuggable with curl | Binary protobuf; compact, needs tooling to inspect |
| Transport | HTTP/1.1 (one request per connection) or HTTP/2/3 | HTTP/2 multiplexed streams; one long-lived channel |
| Caching | Protocol-level: any intermediary may cache per [RFC 9111](https://datatracker.ietf.org/doc/html/rfc9111) | None; every call hits the backend (personalized, typically POST-ish semantics) |
| Browser support | Native | None directly — see gRPC-Web edge case |
| Streaming | Emulated (SSE, long polling, WebSocket separately) | Four native call shapes on one mechanism |
| Deadline propagation | Ad hoc (custom headers, each hop must cooperate) | Automatic via `grpc-timeout` header |
| Error model | Status codes + error body; taxonomy varies per API | `grpc-status` codes + details; uniform across the fleet |
| Evolvability | Additive JSON fields; tolerant readers | Field-number rules; unknown fields skipped; renumbering breaks |
| Intermediary compatibility | Any proxy/CDN works | Requires HTTP/2-aware L7 proxying for load balancing |
| Signature failure | Contract drift between client and server; nobody regenerates | Long-lived connections unbalancing L4 load balancers; opaque debugging |

**The load-balancing failure mode deserves unpacking.** HTTP/1.1 load balancing worked almost by accident: a browser opens many short connections, so L4 round-robin distributes them evenly. A gRPC channel opens one connection and multiplexes everything through it, so an L4 balancer routes *every call from a large client to one backend* — that backend saturates while its siblings idle. The fixes are L7-aware balancing, gRPC's client-side balancing and health-checking features, or deliberately sharding traffic across many channels. The mechanism is that connection lifetime grew from milliseconds to days.

## Step 4: When Each Wins

**REST wins** when: callers include browsers, third parties, or anyone you cannot ship an SDK to; responses have cache semantics that CDNs should serve (public docs, product catalogs, status endpoints); the API surface changes in additive ways and you want evolution without regeneration; debuggability by non-specialists matters; call volume is low enough that verbosity is not the bottleneck. Public APIs are REST not by fashion but because the uniform interface plus universal reachability is the only contract that scales to callers you will never meet.

**gRPC wins** when: the fleet is internal, polyglot, and large enough that contract drift is a real cost; QPS is high enough that serialization and connection overhead dominate; streaming is a first-class requirement (log shipping, telemetry, chat); deadline propagation across deep call chains is needed for fail-fast behavior; and you can deploy the tooling (codegen in CI, HTTP/2-aware load balancing) its connection model assumes. gRPC is the industrialized version of the RPC frameworks every large company previously hand-rolled — that is the "why now" behind its adoption.

**The honest hybrid menu:**
- **gRPC-Web**: browser-side gRPC via a translating proxy (see Step 5 for why the proxy is not optional).
- **JSON transcoding**: annotating proto methods with HTTP bindings (Google's `google.api.http` pattern; the [grpc-gateway](https://github.com/grpc-ecosystem/grpc-gateway) project) so one backend serves both gRPC and REST/JSON clients.
- **REST + protobuf**: JSON for the outside, protobuf-encoded bodies inside the perimeter where both ends regenerate from the same schema — keeping HTTP semantics and caching where they matter while shedding JSON parsing where they do not.

## Step 5: Edge Cases and Counterexamples

- **gRPC-Web exists because of trailers, not transport.** The browser `fetch` API cannot read response trailers, and gRPC's final status (`grpc-status`) rides in trailers. So a browser cannot speak plain gRPC *even where HTTP/2 is available*; gRPC-Web works by having a proxy (typically Envoy) move the status into headers or a body frame. The constraint is the browser API surface, which is why the standard workaround is a translating intermediary rather than a protocol change.
- **JSON transcoding is unary-only in practice.** The HTTP-JSON bridge maps naturally to request/response; streaming call shapes have no clean REST equivalent (SSE approximates server-streaming but not client-streaming or bidi). Teams that adopt transcoding expecting full parity discover that their bidirectional endpoints still need a gRPC (or WebSocket) client — the impedance is in the interaction pattern, not the serialization.
- **Deadline propagation can turn one slow dependency into a full outage.** Propagated deadlines make upstreams abandon work that will not finish in time — the correct default. But a shared edge deadline propagates *tightness*: a dependency that normally takes 50 ms inside a 200 ms budget sees perhaps 90 ms remaining after four hops of queuing, and fails rather than retries, converting a transient blip into a cascading failure. Deadline propagation must be paired with retry budgets and [circuit breakers](../../distributed/microservices/circuit-breakers.md), not deployed as an unqualified good.
- **REST cacheability is often theoretical for authenticated APIs.** `Authorization` headers and personalized payloads interact with shared caches through `Vary` and `Cache-Control: private`, and most production auth'd GETs end up uncacheable anyway. The CDN win is real for public, impersonal reads only.
- **Protobuf's compatibility rule cuts both ways.** Unknown fields are skipped — a genuine wire-compat guarantee — but that also means a typo'd field number silently delivers data to the wrong logical field name across versions. The JSON world fails loudly (unknown field in a strict parser) or tolerantly (ignored), but never "parsed as the wrong thing." Field numbers are forever; treat renumbering like changing a primary key.
- **HTTP/3 and gRPC is real but uneven.** The gRPC protocol is specified over HTTP/2; HTTP/3 (QUIC-based, see [QUIC](../../networks/http/quic.md)) support exists in major implementations but intermediary and tooling support lags. Designing a fleet around "gRPC over HTTP/3 everywhere" today means betting on uneven ecosystem maturity.

## Step 6: Decision Framework

1. **Are any callers browsers or third parties you cannot ship SDKs to?** Yes → REST (or gRPC with JSON transcoding in front); gRPC alone is already eliminated by reachability.
2. **Do responses have public, impersonal cache semantics?** Yes → REST; the intermediary caching layer is worth the verbosity.
3. **Is the fleet internal, polyglot, and larger than a handful of services?** Yes → gRPC: generated stubs turn contract drift into build failures, and `grpc-timeout` propagation comes free.
4. **Is streaming a first-class requirement?** Yes → gRPC's four call shapes (or SSE/WebSocket hybrids on the REST side, each with its own operational tax).
5. **Is per-call overhead the dominant cost?** (Small payloads, high QPS.) Yes → binary protobuf + multiplexed HTTP/2 measurably beats JSON/text at the same QPS.
6. **Can you operate the load-balancing consequences?** If only L4 balancing exists between client and server, either add L7-aware balancing or run more, shorter-lived channels — do not discover the single-backend hotspot in production.
7. **Default in doubt:** REST at the perimeter (reachability, caching, debuggability), gRPC inside (contracts, streaming, deadlines) — the pattern most large fleets converge on, because each layer's callers are different populations with different constraints.

## Interview Questions

1. **Why can't a browser speak gRPC directly, given browsers support HTTP/2?** Because gRPC's terminal status travels in HTTP/2 trailers, and the browser `fetch` API exposes no way to read trailers. gRPC-Web inserts a proxy that relocates the status into headers or a body frame — the blocker is the browser API surface, not the transport.
2. **A team deploys gRPC internally and suddenly one backend receives all traffic from their biggest client while three replicas idle. Explain the mechanism.** A gRPC channel is a small number of long-lived HTTP/2 connections multiplexing every call; an L4 balancer assigns connections, not calls, so all of one client's calls land on whichever backend took the connection. Fixes: L7-aware balancing, gRPC client-side balancing and health checking, or multiple channels.
3. **What does "deadline propagation" actually propagate, and what breaks without it?** The `grpc-timeout` header — the remaining time budget — travels hop to hop, so each dependency knows how long the caller will still wait. Without it, deep call chains keep doing work the caller has already abandoned, so load from doomed requests multiplies; with it, the system fails fast. The edge case: propagated budgets shrink hop by hop and can convert transient slowness into cascading aborts without retry budgets.
4. **Is a REST API "evolvable" in the same sense as a protobuf schema? Both skip unknown fields.** Similar spirit, different enforcement. JSON evolution is social and additive (tolerant readers ignore new fields); protobuf evolution is mechanical with hard rules — field numbers are permanent, types must be wire-compatible, renumbering is a breaking change the tooling cannot catch. The protobuf rulebook is stricter and enforced by generators; the JSON rulebook is looser and enforced by discipline and contract tests.
5. **Your public API is REST but internal calls are gRPC. Where do you put the JSON-to-proto boundary and why not transcode everything?** At the API gateway/edge, keeping gRPC's efficiency and contract strength for the internal hop. Transcoding everything means internal services consume the JSON path — losing streaming shapes, deadline propagation headers, and binary efficiency, and coupling internal evolution to the public contract's compatibility window.

## Key Takeaways

- The decision variables are caller population, contract governance, caching semantics, streaming needs, and deadline propagation — not novelty. REST and gRPC optimize different subsets of these.
- REST's uniform interface buys universality and protocol-level caching at the cost of verbose text and socially-enforced contracts; gRPC's compiled contract buys efficiency, streaming, and drift-proofing at the cost of tooling and intermediary compatibility.
- gRPC's long-lived multiplexed connections are simultaneously its biggest performance win and its biggest operational trap (L4 load-balancing hotspots).
- Hybrids are the production norm: gRPC-Web for browsers (a trailer problem, not a transport problem), JSON transcoding for one-backend-two-audiences, REST+protobuf for caching where it matters.
- Deadline propagation is the underappreciated gRPC feature: it changes failure behavior fleet-wide, and it must be paired with retry budgets and circuit breakers to avoid converting blips into cascades.

## Cross-References

- [REST](../../networks/http/rest.md) — the resource-model and HTTP-semantics foundation of the REST side.
- [gRPC](../../networks/http/grpc.md) — the protocol mapping, call shapes, and ecosystem details.
- [HTTP/2](../../networks/http/http2.md) — multiplexing, HPACK, and stream mechanics gRPC rides on.
- [HTTP/3](../../networks/http/http3.md) and [QUIC](../../networks/http/quic.md) — where the transport goes next and what it changes for RPC.
- [API Gateways](../../distributed/microservices/api-gateways.md) — where the REST/gRPC boundary is usually drawn.
- [Circuit Breakers](../../distributed/microservices/circuit-breakers.md) — the pairing required for deadline propagation to be safe.
- [API Contracts: Assumptions Hunt](../assumptions-hunt/api-contracts.md) — the hidden assumptions behind "the contract is the schema."
- [Backpressure: Connection Atlas](../connection-atlas/backpressure.md) — pacing and flow control for the streaming shapes both sides offer.
- [Architecture Trade-offs](../../trade-offs/architecture-tradeoffs.md) — quick-reference tables for API and service style choices.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
