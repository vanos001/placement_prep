# Follow-up Tree: API Gateway

## Overview

"What does an API gateway do?" is the microservices-era opener whose first answer — "it sits in front of the services and routes requests" — is true, shallow, and conceals the entire platform-engineering interview: where authentication happens, where rate limiting lives and *why there*, how versioning survives independent service deploys, and what happens when the component you put in front of everything becomes the thing that can take down everything. Interviewers like this chain because it is a design-judgment amplifier: every rung has a "why there and not elsewhere" answer, and the candidate either reasons about *placement* or recites *features*. This page walks the ladder — what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. Handoffs are deliberate: the identity and session mechanics the edge validates are the connection map in [Auth, Identity, and Session](../connection-atlas/auth-identity-session.md); the rate-limiting algorithm zoo, distributed counters, and fail-open/fail-closed analysis are the design ladder in [Rate Limiter Design](./rate-limiter-design.md) — this chain owns the gateway as a component and the placement questions around it. Book-level depth: [API Gateways](../../distributed/microservices/api-gateways.md), [Reverse Proxies](../../networks/load-balancing/reverse-proxy.md), and [Service Discovery](../../distributed/microservices/discovery.md).

## The Opening Question

**"What is an API gateway, and what problems does it solve that an ordinary load balancer does not?"**

The expected core answer: a gateway is an L7 reverse proxy with *policy*: it terminates client traffic, routes by path/header/host to services, and centralizes the cross-cutting concerns — authentication, rate limiting, request/response transformation, protocol translation, canary routing — so each service does not reimplement them. An ordinary load balancer picks a backend; a gateway makes decisions about *the request*: who is calling, are they allowed, how fast, and which version of the API.

A weak answer lists features ("routing, auth, rate limiting") as a menu without a unifying principle. The strong answer states the principle: the gateway is where *client-facing policy* lives — concerns that are per-client rather than per-service — and names the price it charges: every request gains a hop, and the component in front of everything is now on the critical path of everything. The follow-up that escalates: **"Why is authentication at the gateway — and what does that actually mean for the services behind it?"**

## Level 2: Authentication at the Edge — and the Trust the Services Must Still Have

**What it tests:** whether "auth at the gateway" means "the services can finally stop thinking about security" (wrong) or a *delegation* model with explicit trust boundaries and credentials that flow inward.

**Weak answer:** "The gateway validates the JWT so services don't have to" — full stop. That design makes every internal service trust whoever can reach it directly.

**Strong answer:** describes the edge verifying the caller (JWT signature, expiry, scopes; or session cookie validation) and then *forwarding identity* — either the original token or an exchanged one — so services make per-route authorization decisions themselves; knows the zero-trust alternative (mTLS between services, the gateway as one authenticated participant) and why both models coexist.

**Escalation trigger:** "The gateway validates tokens. A developer reaches a service directly inside the cluster and pulls another user's data. What failed, and what do you change?"

**Answer.** What failed is the *trust boundary*: gateway-side authentication is perimeter security, and once any code path bypasses the perimeter — direct pod-to-pod calls, a misconfigured ingress, an SSRF from another service — the service treated network location as identity and granted the request. The fix is to make the service's question not "where did this come from" but "who is the caller and are they authorized for *this* route," answered from forwarded credentials: the gateway validates the client token and forwards it (or exchanges it for a scoped internal token), and the service enforces route-level authorization itself — the identity/session mechanics and the failure taxonomy are the map in [Auth, Identity, and Session](../connection-atlas/auth-identity-session.md). The strong answer also prices the alternatives: mTLS everywhere (service mesh territory — the comparison rung is below) gives every service cryptographic peer identity but adds certificate-issuance machinery; short-lived internal tokens from the gateway add a token-issuance service to operate. The senior framing: the gateway is the *cheapest* place to reject unauthenticated traffic — it rejects before fanning out — but it is the *only* place to reject nothing else: authorization granularity almost always lives better in services that know their own routes.

## Level 3: Rate Limiting Placement — Edge, Service, or Both

**What it tests:** placement reasoning: the candidate must know *why* rate limiting is usually deployed at the gateway (and at the CDN/edge even before that), what the gateway-only version misses, and where the per-service limiter still belongs.

**Weak answer:** "Rate limiting goes in the gateway config" — no analysis of what the limiter protects, per-caller versus per-service quotas, or the cost of centralized counters.

**Strong answer:** distinguishes the protections: per-client fairness limits (cheap to evaluate at the edge, where the client identity is first seen), per-service *capacity* limits (protect a specific database or dependency, so they belong at or near that service), and abuse protection (WDDoS-scale, so it lives at the CDN — before your origin pays for the bytes); knows the distributed-counter cost and the failure posture choice.

**Escalation trigger:** "You rate-limit 1,000 req/s per client at the gateway. A service's database melts anyway. Why did the gateway limiter not protect it?"

**Answer.** Because a per-*client* limit caps each caller, not the *sum*: 500 clients each within quota is 500× load on whatever one hot endpoint they all hit — the aggregate is only bounded by the client count. The gateway limiter's job is fairness and blunt abuse control at the point where client identity is cheapest to evaluate; the service's job is protecting its own resource, and that needs a limit keyed to the resource — per-endpoint, per-tenant-against-dependency — deployed at the service (or its sidecar). The full algorithm design — token bucket versus sliding window, the distributed counter race, Redis-based or gRPC-based shared state, and the fail-open/fail-closed decision when the counter store dies — is exactly the ladder in [Rate Limiter Design](./rate-limiter-design.md); this rung owns the *placement* conclusion: edge for client fairness, service for resource protection, CDN for volumetric attacks, and if you can afford only one, the one that protects the resource that fails first. The senior detail worth volunteering: response headers (`Retry-After`, remaining quota) turn the limiter from a silent wall into a contract clients can back off against — a policy decision, not a config default.

## Level 4: Routing and Versioning — How Clients and Services Decouple

**What it tests:** whether the candidate can design the gateway's routing layer as an *API lifecycle* tool — version negotiation, canary/traffic splitting, route config as data — rather than a static path table.

**Weak answer:** "Routes map paths to services; v2 gets a new path" — no model of compatibility, no traffic-splitting mechanics, no config rollout story.

**Strong answer:** distinguishes versioning styles (path vs header vs content negotiation) and their client friction; describes weighted routing for canaries and A/B tests with matching on headers/cookies; treats route configuration as a *deployed artifact* with its own change control; and connects the whole thing to rolling-deploy compatibility windows.

**Escalation trigger:** "You deploy a breaking change to a service. Clients on the old API version break. Whose fault is it, and what is the fix?"

**Answer.** Neither side "broke" — the deployment violated the *compatibility window*: with independent service deploys, the contract between client and service must remain valid across the overlap where old clients and new servers (and new clients against old servers, during rollbacks) coexist — the schema and contract analysis is exactly the audit in [Serialization Compatibility](../assumptions-hunt/serialization-compatibility.md). The gateway's role is to make the transition *explicit*: route by version (path prefix or header), run v1 and v2 side by side, shift weight gradually, watch per-version error and latency deltas (the canary discipline in [Canary Releases](../../sre/canary-releases.md)), and deprecate on a published schedule rather than by deploy accident. The strong answer also names where versioning does *not* belong at the gateway: for internal RPC meshes, contract evolution (additive fields, reserved numbers) is usually cheaper than version forks, and the gateway should route *instances*, not versions. The judgment sentence: gateways convert compatibility problems into routing problems, which is a win only when routing configuration is versioned, reviewed, and rolled out with the same discipline as code — otherwise the gateway config becomes the least-tested code in the company.

## Level 5: Bottleneck, SPOF, and Gateway versus Service Mesh — the Judgment Rung

**What it tests:** the design-judgment boundary: what happens when the gateway is saturated or down, how the ecosystem answers (scale-out gateways behind L4 tiers), and when the *mesh* — per-service sidecars — replaces or complements the edge gateway.

**Weak answer:** "If the gateway fails, we add more gateway instances" — no saturation model, no failure-posture analysis, no mesh comparison.

**Strong answer:** knows the gateway is a horizontal scaling problem like any proxy (more replicas behind an L4 tier, the load-balancing analysis in [Load Balancing](./load-balancing.md)) but a *config* SPOF like no other (one bad route push can fail every request); compares gateway (edge, coarse, per-client policy) with mesh (every hop, fine, per-service policy: mTLS, retries, timeouts, circuit breaking); and can state the coexistence pattern — edge gateway for the outside world, mesh for inside.

**Escalation trigger:** "Gateway CPU is fine at 40 percent, but p99 through the gateway is 3× direct-to-service latency. What is the gateway doing?"

**Answer.** The saturation model first: proxy CPU and memory are the obvious ceilings, and the answer to *those* is scale-out replicas behind L4 balancing with health-checked pools (the tiering from [Load Balancing](./load-balancing.md) and the reverse-proxy mechanics in [Reverse Proxies](../../networks/load-balancing/reverse-proxy.md)). But 3× p99 at 40 percent CPU is a *latency* signature, not a capacity one — the suspects are per-request work that costs more than it routes: synchronous per-request auth lookups (a token introspection call per request — the fix is local JWT validation or caching with the staleness caveat), connection setup churn (short upstream timeouts forcing reconnect storms — keep-alive pooling, the [Connection Pooling](./connection-pooling.md) analysis with HTTP as the pooled resource), retries and circuit-breaking layered badly (gateway retries amplifying a slow downstream — the amplification analysis in [Circuit Breakers](../../distributed/microservices/circuit-breakers.md)), or logging/body-buffering costs. The SPOF analysis completes the rung: compute SPOF is solved by replicas; *configuration* SPOF is solved by change discipline (staged route pushes, canarying config, automatic rollback) — and the reason gateways fail politically is that they accumulate policy nobody owns. The mesh comparison is the synthesis: a mesh pushes the same policy primitives (mTLS, retries, timeouts) to per-service sidecars, fixing the blast radius and the internal-hop problem but adding a control plane to operate; the standard senior answer is coexistence — mesh inside for service-to-service policy, edge gateway outside for client-facing policy ([API Gateways](../../distributed/microservices/api-gateways.md) and [Service Discovery](../../distributed/microservices/discovery.md) carry the deployment detail; the Kubernetes-native flavor is the ingress pattern in [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) and the pod lifecycle it gates is [Kubernetes Pod Lifecycle](./kubernetes-pod-lifecycle.md)).

## How to Approach Unfamiliar Variations

The template for gateway variations — "BFF pattern," "GraphQL federation at the edge," "multi-tenant gateways," "the gateway team is a bottleneck":

1. **Classify every concern by its natural owner.** Client-facing policy (auth, quota, versioning) wants the edge; resource-protection policy (per-service limits, authorization) wants the service; hop-policy (mTLS, retries, timeouts) wants the hop. A variation question is usually asking you to place one concern correctly.
2. **Ask what the gateway sees.** Its powers come from L7 visibility (paths, headers, identity) and its costs from termination work. Any "should X go in the gateway" question is "does X need request-level visibility?"
3. **Price the hop, then price the config.** Latency and capacity questions are hop-cost questions; blast-radius questions are configuration-change questions. Gateways fail more often from bad config pushes than from traffic.
4. **For gateway-versus-mesh questions, split inside from outside.** The edge faces untrusted clients and owns per-client policy; the mesh faces services and owns per-hop policy. Most confusion dissolves once the traffic direction is named.

## Interview Questions

**Q: Your platform has 40 services and one gateway. A release adds a route that matches too broadly and black-holes a payment path for 6 minutes. What does this incident teach about gateway operations?**
A: Route configuration is production code: the blast radius of a config error is every request, so route changes need the same pipeline as deploys — schema-validated config, automated route-collision tests, staged rollout, canary evaluation of matched-request metrics, and fast rollback. It also teaches ownership: an unowned shared config accumulates errors. The gateway being "just config" is precisely why it needs more discipline, not less.

**Q: Why do most designs put rate limiting at the gateway but authorization in the services?**
A: Rate limiting needs client identity and is cheapest at the first hop — rejecting there saves fan-out cost and the limiter's decisions are per-client, which the edge sees first. Authorization needs route semantics — which resource, which action — that only the service knows, so pushing it to the edge means either duplicating route knowledge in the gateway (drift) or authorizing too coarsely. The edge rejects the definitely-unauthorized; the service decides the definitely-specific.

**Q: A service mesh is proposed to replace your gateway. What does that get you, and what breaks?**
A: A mesh gives per-hop policy (mTLS, retries, timeouts, telemetry) at every service pair, removing the edge's internal-traffic role and shrinking blast radius from "one config" to "per-service config." What breaks: the mesh does not face the internet — you still need an edge for client auth, quota, and API versioning; and you now operate a control plane, certificate rotation, and sidecar lifecycle (the pod-side cost is the [Kubernetes Pod Lifecycle](./kubernetes-pod-lifecycle.md) chain). The correct conclusion is almost always "mesh inside, gateway at the edge," not replacement.

**Q: The gateway must translate REST to gRPC for internal services. What are the risks beyond the mapping itself?**
A: Protocol translation hides failures: timeouts, deadlines, and cancellation semantics differ between the front protocol and the back protocol, and a translated call can keep retrying after the client gave up (orphaned work); streaming and metadata (trace context, idempotency keys) must be mapped explicitly or they are silently dropped; and error models differ — an HTTP 4xx/5xx taxonomy flattened into gRPC status codes loses information clients rely on. Every translated field is a compatibility surface, so version the mapping like any contract.

## Key Takeaways

- A gateway is L7 reverse proxying plus client-facing policy: routing, auth, quota, transformation — its defining property is *placement* in front of everything, which is both its power and its failure mode.
- Authentication at the edge is rejection economics, not a trust boundary: forward identity inward and keep per-route authorization in services, or direct access bypasses everything.
- Rate limiting placement follows the protection target: edge for per-client fairness, service for resource capacity, CDN for volumetric abuse — a per-client edge limit never bounds the sum.
- Gateways turn compatibility problems into routing problems: versioned routes, weighted canary shifts, and published deprecation only work when route config is deployed with code-level discipline.
- Gateway SPOFs come in two kinds — compute (solved by scale-out behind L4) and configuration (solved by staged, reviewed, reversible pushes); latency problems at low CPU are per-request work, not capacity.
- The mature pattern is coexistence: edge gateway for outside, service mesh for inside — each owns the policy its position can actually see.

## Cross-References

- [Rate Limiter Design](./rate-limiter-design.md) — the sibling ladder owning the algorithm zoo, distributed counters, and fail-open/fail-closed this chain's placement rung assumes.
- [Load Balancing](./load-balancing.md) — the tier beneath the gateway: L4/L7 division of labor, health checks, and scale-out.
- [URL to Page](./url-to-page.md) — the end-to-end chain that shows where the gateway sits in the request's full journey.
- [Kubernetes Pod Lifecycle](./kubernetes-pod-lifecycle.md) — readiness gates and termination that the gateway's health checks and draining interact with.
- [Auth, Identity, and Session](../connection-atlas/auth-identity-session.md) — the identity mechanics behind the edge-auth rung.
- [API Gateways](../../distributed/microservices/api-gateways.md) — the book chapter on gateway patterns, BFFs, and translation.
- [Reverse Proxies](../../networks/load-balancing/reverse-proxy.md) — the proxy mechanics the gateway is built from.
- [Service Discovery](../../distributed/microservices/discovery.md) — how the gateway's routes resolve to instances.
- [Circuit Breakers](../../distributed/microservices/circuit-breakers.md) — the retry/breaker interactions that turn gateway policy into amplification.
- [Serialization Compatibility](../assumptions-hunt/serialization-compatibility.md) — the contract-evolution audit behind the versioning rung.
- [Canary Releases](../../sre/canary-releases.md) — the traffic-shift discipline the versioning rung borrows.
- [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) — the Kubernetes-native gateway pattern, verified official docs.
