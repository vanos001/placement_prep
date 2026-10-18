# GraphQL vs REST: Query Flexibility Against Cacheability and Simplicity

## Overview

GraphQL and REST answer the same question — "how does a client fetch structured data over HTTP?" — by relocating different costs. REST fixes the response shape on the server: each URL is a resource, the client assembles screens from multiple resources, and HTTP's uniform interface (methods, status codes, freshness headers) gives intermediaries — browsers, CDNs, proxies — enough shared vocabulary to cache and police traffic without understanding it. GraphQL moves the shape definition to the client: the request document names exactly the fields needed, and a resolver graph on the server stitches them from any backing services. The fork is really a question of **where the contract lives and who pays for shape**: a REST server pays by shipping fixed shapes that are sometimes too big and sometimes too small; a GraphQL server pays by executing arbitrary client-shaped queries against its database.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **GraphQL wins when many heterogeneous clients need differently shaped slices of one evolving data graph; REST wins when cacheability, operational simplicity, and uniform intermediaries dominate.** Neither dominates, and production systems increasingly run both — REST at the CDN edge, GraphQL as the aggregation tier behind it. The mechanisms below explain why that layering keeps re-emerging, and the edge cases (server-side N+1, introspection exposure, cache-hit-ratio collapse) explain why both pure choices fail in characteristic ways.

## Step 1: The Problem and Its Constraints

The abstract shape: a set of clients fetches data from services owned by other teams. Constraints that decide the answer:

- **Client heterogeneity.** One web app plus two mobile apps plus partner integrations, each wanting overlapping-but-different slices, multiplies the number of fixed REST shapes the server must design ("the BFF tax"). A homogeneous client population needs one shape, and the flexibility argument evaporates.
- **Cacheability requirement.** What fraction of reads are shared across users? A catalog page served to a million users wants CDN caching keyed on URL; a personalized dashboard wants nothing shared. HTTP caching (see [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)) only works mechanically when the cache key is a URL and the response is user-independent.
- **Network conditions.** High-latency mobile links reward few round trips (GraphQL's single request); lossy links punish large over-fetched payloads (GraphQL again). Desktop on fiber shrinks both advantages.
- **Query-cost exposure.** REST requests cost roughly what their URL says. GraphQL requests cost what their document says, which the server does not control — bounding that cost is a design task, not a default.
- **Evolution cadence.** Who ships new fields, how often, and how painful is coordinating client and server releases? Schema evolution with deprecation is a GraphQL design feature; REST versioning is a social convention with URL or header dialects.

## Step 2: The Mechanisms

### REST: the uniform interface pays intermediaries

- **The vocabulary is URL + method.** `GET /users/42` is fetchable, bookmarkable, and — critically — *cacheable*: freshness headers (`Cache-Control: max-age`), validators (`ETag`, `Last-Modified`) give any intermediary a mechanical rule for reuse without parsing the body (see [MDN: HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)). A CDN in front of a REST API converts (1 − hit ratio) of origin traffic into edge hits; this is the load-bearing reason public read-heavy APIs stay REST.
- **The contract is a document, not a type system.** [OpenAPI](../../backend/api/openapi-spec.md) describes endpoints and shapes, but nothing forces server and client to agree — the "contract" is enforced socially. Consequences: tolerant readers, runtime surprises, and versioning conventions (`/v2/`, date headers) that are negotiation rather than mechanism.
- **Over-fetch and under-fetch are structural.** Over-fetch: `/users/42` returns 40 fields when the screen needs 3. Under-fetch is worse: the client must call `/me`, then `/orders?user=`, then `/orders/{id}/items` — a *waterfall* of round trips where each request's input comes from the previous response. On a 200 ms RTT mobile link, a three-hop waterfall is 600 ms of pure latency no server optimization can remove.

### GraphQL: the document is the query plan

- **One endpoint, client-shaped documents.** The [GraphQL specification](https://spec.graphql.org/) defines a query language and a type system; the server executes the document against a resolver graph. Over-fetch and under-fetch disappear by construction: the client asks for exactly the fields it renders.
- **The server-side N+1 is the signature cost.** Resolvers execute per field: a query for 100 authors' books naïvely issues one database query *per author* — the classic N+1 relocated from the client (REST's waterfall) to the server, where it is more dangerous because it hits the database directly. The standard mitigation is request-scoped batching ([DataLoader](https://graphql.org/learn/)-style): collect all keys requested in one execution pass, fetch them in a single `WHERE id IN (...)`, memoize per request. Batching turns O(n) database round trips into O(1) — but someone must know to build it, and per-request memoization must not cache across requests (an authz leak, below).
- **The query surface is unbounded by default.** Any client may send any syntactically valid document: deeply nested, aliased duplicates, expensive aggregates. Defenses are all server-side design work: depth limits, complexity scoring, timeouts — and *persisted queries*, which replace the free-form document with a hash of a pre-registered query. Persisted queries are the quiet convergence point: once every query is pre-registered and allow-listed, the API is effectively a set of named endpoints — GraphQL with a REST-shaped trust boundary.
- **HTTP caching breaks, application caching replaces it.** GraphQL operations are typically POSTs with the query in the body: no URL key, so no shared/CDN caching. Because the response shape is per-document, two queries touching the same entity don't share cache entries. Gateways rebuild caching at the application layer (entity-keyed caches, automatic persisted queries), which is strictly more work than configuring HTTP semantics.
- **Introspection is the exposed schema.** The [spec](https://spec.graphql.org/) mandates a query (`__schema`, `__type`) that returns the full type graph: every type, field, and deprecation reason. This is superb for tooling and lethal for security posture: anyone can enumerate the schema, including internal-sounding types and forgotten fields, then probe them. See the edge cases.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | REST | GraphQL |
|----------|------|---------|
| Response shape | Fixed by server; over/under-fetch possible | Chosen by client per request |
| Round trips per screen | Often a waterfall (fetch id, then detail) | One, by construction |
| Cache key | URL; HTTP/CDN caching mechanical | None shared; application-level or persisted-query caching |
| Server query-cost bound | Per-resource, designed | Unbounded by default; needs limits or persisted queries |
| N+1 location | Client-side waterfall | Server-side resolver fan-out (batched via loaders) |
| Contract artifact | OpenAPI (descriptive, social) | SDL (introspectable, type-checked) |
| Versioning | URL/header conventions; negotiation | Schema evolution: nullable adds, `@deprecated`, no breaking change |
| Errors | Status codes; intermediaries understand them | 200 + structured partial errors; intermediaries see success |
| Authz granularity | Per-endpoint | Per-field, if explicitly built — otherwise endpoint-level only |
| Streaming/uploads | Native (SSE, multipart) | Extensions and community workarounds |

The **partial-success** mechanism deserves the arrow drawn: GraphQL returns HTTP 200 with a `data` object that may be partially populated and an `errors` array beside it. This is honest — one bad resolver need not sink the whole response — but it breaks the uniform interface's error vocabulary: a CDN, rate limiter, or client retry policy sees status 200 and assumes success. REST's failure modes are the mirror image: status codes are coarse (a 500 hides which of six sub-resources failed), but every intermediary speaks them. Each style locates error-handling intelligence where the other locates caching machinery.

## Step 4: When Each Wins

**GraphQL wins** when: the client population is heterogeneous and shape-hungry (web, iOS, Android, TV, partners pulling overlapping slices); the data graph aggregates several backing services (the gateway/federation pattern replaces a zoo of bespoke BFFs); schema evolution must be smooth without version forks; and the team can afford the server-side defenses — batching, complexity limits, persisted queries, field-level authz. The aggregating-many-clients case is the decisive one: every added client shape costs a REST endpoint revision but zero GraphQL server changes.

**REST wins** when: responses are cacheable and shared (public content, high read ratio — the CDN lever is worth more than shape flexibility); clients are simple or numerous third parties who expect URLs, status codes, and conventional pagination; the API needs uploads, streaming, or webhook-style callbacks; the team cannot staff query-cost defense. A read-heavy public API behind a CDN with 95% hit ratio is the clearest case: GraphQL would multiply origin load by roughly 20× to buy flexibility the clients don't need.

**The honest hybrid menu** — where production systems actually live:
- **REST at the edge, GraphQL behind it.** Public, cacheable, resource-shaped endpoints at the CDN; a GraphQL gateway for the personalized aggregates no one can pre-shape. Each layer does what its mechanism is good at.
- **GraphQL over HTTP GET + persisted queries** recovers some URL-keyed caching for hot, user-independent queries — a deliberate narrowing of the query surface to buy the uniform interface back.
- **REST plus a composition endpoint**: most "we need GraphQL" pain is actually "we need one aggregate endpoint for the dashboard screen"; a purpose-built BFF endpoint solves it without a query language.

## Step 5: Edge Cases and Counterexamples

- **Introspection exposure: the schema is an attack map.** A public GraphQL endpoint with introspection enabled hands attackers the complete type graph — internal types, deprecated fields, admin-ish mutations — before they send a single real query. Combined with the field-level-authz gap (authz written per endpoint, not per resolver), attackers pivot to fields the designers forgot to guard. The counterintuitive part: teams that disable introspection in production also break their own code generation and tooling, which is a useful signal that the *query surface itself*, not the introspection flag, is the trust boundary. Persisted queries plus deny-by-default field authz are the fix; "turn off introspection" alone is security theater.
- **The DataLoader that leaks.** A batching loader keyed on `userId` caches the full row — all columns — per request. An early resolver's restricted field set populates the cache; a later resolver in the same request reads the cached row and serves columns the caller should not see. Batching caches are per-request by design, but *what* they cache must match the *most restricted* reader in that request — an authz subtlety REST never faces because there is no shared request-scoped memo.
- **One round trip can be slower than three.** A dashboard aggregates user, orders, and recommendations. The GraphQL document returns it in one request — but every request is a cache miss (personalized POST), so origin handles full traffic. The REST version splits the screen into three resources, two of which are shared and CDN-cached; the waterfall shrinks under HTTP/2 multiplexing (see [HTTP/2](../../networks/http/http2.md)) and two of three hits come from the edge. "One round trip" is only a win if the round trip is cheap.
- **The under-fetch waterfall REST cannot fix.** A mobile checkout needs the session, then the cart, then shipping options keyed by cart version. Three sequential round trips at 250 ms RTT is 750 ms of latency that no caching or HTTP/2 removes, because each request needs the previous response. This is the workload where GraphQL's single document is not an optimization but a category fix — and why mobile-first products were its earliest adopters.
- **Persisted queries converge back to REST.** Once a team allow-lists every query, versions them, and revokes hashes, they have rebuilt named endpoints with an extra indirection. That is not a failure — it is evidence the trade-off curve has a convergence point: unbounded query flexibility is worth its cost only while the client population is genuinely exploring shapes.

## Step 6: Decision Framework

1. **Is the client population homogeneous, doing CRUD against resources?** Yes → REST; flexibility buys nothing and costs cacheability.
2. **Do shared, cacheable reads dominate traffic?** Yes → REST (or GraphQL-with-persisted-GET at most); a CDN lever compounds daily.
3. **Do multiple client variants need differently shaped slices of one graph?** Yes → GraphQL, with batching and complexity limits as non-negotiable launch requirements, not later hardening.
4. **Can you staff field-level authz and query-cost defense?** No → REST; an unbounded query surface without defenses is an unpatchable DoS vector.
5. **Is the API aggregating many backing services for internal consumers?** Yes → GraphQL gateway/federation is the pattern that replaces N bespoke BFFs.
6. **Default in doubt:** REST for the public, cacheable, partner-facing surface; GraphQL as the internal aggregation tier where client shapes actually vary — and revisit when a persisted-query registry makes the GraphQL side look like REST again.

## Interview Questions

1. **Explain GraphQL's server-side N+1 and the standard mitigation.** Resolvers execute per field, so one query fetching N authors' books issues one database call per author. The fix is request-scoped batching: collect all keys requested during one execution pass and issue a single `IN` query, memoizing per request. Batching must stay per-request — cross-request caching turns a performance optimization into an authz leak.
2. **Why is GraphQL hard to cache with HTTP, and what recovers it?** Operations are POSTs with the query in the body, so there is no URL key and responses are per-document; HTTP/CDN caching becomes inapplicable. Recovery: automatic persisted queries put a stable query identifier in a GET, restoring a cacheable key for hot, user-independent queries — at the cost of pre-registering every query.
3. **Your team ships a public GraphQL API. What does introspection change about your threat model?** The full schema — types, fields, deprecations — is enumerable by anyone, so security can't rely on obscurity of the surface. Authz must be per-field (deny by default), query cost must be bounded (depth/complexity limits or persisted queries), and turning introspection off only helps if you also control the query surface.
4. **When would you deliberately choose REST for a greenfield API despite GraphQL's flexibility?** When reads are shared and cacheable (CDN leverage dominates), clients are simple third parties expecting URLs and status codes, or the team cannot afford server-side query-cost defense. Flexibility is a cost paid on the server; without heterogeneous clients, it is a cost with no offsetting benefit.
5. **What does GraphQL's "200 + partial errors" break, and what does REST's status-code model hide?** GraphQL's model breaks intermediaries: CDNs, retries, and WAFs see success while `errors` carries failures. REST's coarse codes hide which sub-resource failed in a composite response. Each style relocates error-handling intelligence — GraphQL to the client, REST to the operator reading logs.

## Key Takeaways

- The real variable is **who shapes the response**: REST fixes shapes server-side and pays in over/under-fetch and waterfalls; GraphQL lets clients shape queries and pays in unbounded server query cost.
- GraphQL's N+1 is the REST waterfall relocated to the server — more dangerous against the database, and fixable only by deliberate batching infrastructure.
- HTTP cacheability is REST's compounding advantage: URL-keyed caching turns intermediaries into free infrastructure. GraphQL buys it back only by narrowing the query surface (persisted queries) — the convergence point of the two styles.
- Introspection makes the schema public: GraphQL security must be field-level and deny-by-default, because the attack map ships with the API.
- The production answer is usually layered: REST where reads are shared, GraphQL where shapes genuinely vary per client — each mechanism doing the job it was designed for.

## Cross-References

- [REST vs gRPC](./rest-vs-grpc.md) — the sibling comparison: where the API contract lives, compiled artifact vs social convention.
- [GraphQL](../../backend/api/graphql.md) and [GraphQL Federation](../../backend/api/graphql-federation.md) — the query language and gateway mechanics behind this page's aggregation tier.
- [REST](../../networks/http/rest.md) — the resource model, methods, and status-code vocabulary.
- [API Caching](../../backend/api/api-caching.md) — cache strategies for both shapes at the application layer.
- [Caching and Distributed Systems](./caching-distributed.md) — invalidation and stampede mechanics that any API cache inherits.
- [HTTP/2](../../networks/http/http2.md) — multiplexing that shrinks REST waterfalls, weakening GraphQL's round-trip argument.
- [OpenAPI](../../backend/api/openapi-spec.md) — the REST contract artifact and its enforcement gap.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
- [GraphQL learning materials](https://graphql.org/learn/) — the official tutorial behind the resolver and batching discussion.
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — the caching and method vocabulary REST leans on.
- [MDN: HTTP Caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching) — freshness and validator mechanics in depth.
