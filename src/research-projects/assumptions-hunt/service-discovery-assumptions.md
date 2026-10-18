# Service-Discovery Assumptions: What "Just Look Up the Host" Silently Promises

## Overview

Every remote call begins with a question the code barely registers as a question: *which instance do I talk to?* The answer comes from a discovery mechanism — DNS, a registry client, a service mesh — and the calling code assumes the answer is a fact: that the registry reflects who is running right now, that a returned instance is healthy and reachable, that DNS is simply the discovery mechanism with stable names, and that discovery is a neutral lookup rather than a policy decision. Each assumption fails in a specific way — calls routed to an instance that died 70 seconds ago, health checks that pass while the application is wedged, a renamed service reachable by half the fleet and 404-ing for the other half, and a discovery layer that quietly makes availability-versus-consistency choices on the caller's behalf.

The deeper pattern is that *discovery is a cache of membership*, and every property that makes caches useful — latency, availability under failure — is a property that makes them stale; the design question is never "is the registry current?" but "how stale can the routing decision be before it costs more than the freshness would?". A boundary note against the sibling chapter: [DNS assumptions](dns-assumptions.md) audits DNS mechanics — TTL semantics, negative caching, reversibility, round-robin as balancing — and this chapter stays at the discovery layer: registries, health semantics, and the routing decisions built on membership. Both follow the collection's five-step pattern and connect to the same substrate: the [containers-cgroups-namespaces atlas](../connection-atlas/containers-cgroups-namespaces.md) explains the pod-and-namespace machinery whose membership the registry is trying to track.

## Assumption 1: "The Registry Reflects Who Is Running Right Now"

### The taught rule

The service registry is the source of truth for topology: instances register on startup, deregister on shutdown, and a lookup returns the live set.

### The hidden assumptions

- Membership propagates through a pipeline of intervals, not instantly: a new instance waits for a registration call, a health check to pass, and a registry replication round; a dead instance remains listed until its heartbeat deadline plus the registry's eviction interval. Each stage adds its own delay, and the sum is the real staleness bound.
- Clients add their own layer: most discovery clients cache the instance list and refresh on a timer, so the "current" set used for routing is a snapshot from as long ago as the refresh interval. Worst-case routing staleness is heartbeat interval + eviction time + client refresh — with a 10-second heartbeat, 30-second eviction, and 30-second client cache, a killed instance can receive traffic for about 70 seconds.
- "The registry is the source of truth" is true of the registry, not of the fleet: the authoritative fact is which processes hold open sockets, and the registry is an asynchronously updated projection of that fact — the projection is what code queries.
- deregistration on graceful shutdown helps (the [process-shutdown assumptions](process-shutdown-assumptions.md) chapter's sequencing), but ungraceful deaths — SIGKILL, host loss, network partition — leave no deregistration call at all; eviction by timeout is the only mechanism, and its delay is the design's exposure window.

### Counterexample

A deployment kills an instance ungracefully (node failure). The registry's health check runs every 10 seconds with a 30-second mark-dead threshold, and the consumer's instance list refreshes every 30 seconds: for up to 70 seconds, one in `N` requests selects the dead instance and fails. With 12 instances and 1,000 requests per second, roughly 5,800 requests hit the ghost before the projection catches up — each triggering retries that double the load on the surviving instances. The corrected contract: state the staleness bound explicitly (heartbeat + eviction + refresh), shrink the components that matter (passive health checks that fail fast on connection errors, shorter refresh under retry storms), and treat the ghost window as a first-class design number, not an operational surprise.

### What changes when the assumption is removed

Corrected statement: *a registry lookup returns a set that was true at some point in the past; the engineering task is to bound that past — by choosing heartbeat, eviction, and refresh intervals to a stated staleness budget — and to make the failure of routing to a ghost cheap (fast connection failure, retry, circuit breaker) rather than rare.* Freshness and failure cost trade against each other; the design picks a point, whether it says so or not.

### Consequences

In interviews, "an instance dies — how long until clients stop calling it?" is the probe, and the senior answer is the sum-of-intervals arithmetic with each component named and tuned, which is also the cheapest incident-postmortem check for "why did we page on a deploy".

## Assumption 2: "A Returned Instance Is Healthy and Reachable"

### The taught rule

Registries health-check their members and only return passing instances; a returned endpoint is a working endpoint, so the caller can skip its own verification.

### The hidden assumptions

- *Health is check-depth-dependent:* a TCP connect check passes as long as the process accepts sockets — an application deadlocked above the accept loop, or wedged on a slow dependency, stays "healthy" indefinitely; deeper checks (an actual endpoint, a dependency probe) trade cost for specificity, and every registry chooses a depth the caller did not specify.
- *Reachability is a relation, not a property:* an instance can be reachable from the registry's probe and unreachable from the caller — different security groups, a partition between racks or zones, an IP family mismatch (the caller resolving an IPv6 address it cannot route). "Healthy" is measured from one vantage point and consumed from another.
- *Readiness gates warm-up but assumes the gate's predicate:* an instance marked ready after its health endpoint responds can still be functionally cold — empty caches, unparsed state, a JIT that has not compiled the hot paths — so the first minutes of traffic meet latency the readiness check never measured (the deployment-side coupling is the [migrations-deploy-coupling atlas](../connection-atlas/migrations-deploy-coupling.md)'s subject).
- *Health checks consume the same capacity they measure:* aggressive check intervals from many registries and load balancers add their own load to an overloaded instance, deepening the failure they are trying to detect.

### Counterexample

A service's readiness probe is a TCP connect to its port; a deadlock in the request-processing thread pool leaves the accept loop alive, so the probe passes and the registry keeps returning the instance. Callers route 80 requests per second into a queue that never drains for 40 minutes; the dashboard shows the instance "healthy" the entire time, and the first hour is spent re-checking the registry rather than the process. The corrected contract: match check depth to the failure modes that matter (a real request path, a dependency-light endpoint, a pool-drainability probe), and layer caller-side circuit breaking — the [circuit-breakers follow-up](../followup-tree/circuit-breakers.md) escalation — so the caller's observed failures, not the registry's probe, are the final authority on reachability.

### What changes when the assumption is removed

Corrected statement: *a registry's health verdict is a shallow measurement from one vantage point at one moment; callers must treat discovery output as a candidate list, keep their own failure statistics, and stop routing to instances that fail from where they stand.* Health information flows uphill too: client-side failure feedback (ejecting bad hosts) is the only signal measured at the point of consumption.

### Consequences

"Your registry says the instance is healthy; the instance is not. What went wrong?" decomposes into check depth, vantage point, and warm-up predicate — three named dials instead of one vague complaint, and a ready-made answer for "how would you design health checks?" in system-design rounds.

## Assumption 3: "DNS Is the Discovery Mechanism, and DNS Names Are Stable"

### The taught rule

Services get DNS names; resolving the name is discovery; the name is a stable handle that outlives instances, deploys, and refactors.

### The hidden assumptions

- *What a DNS name resolves to is a configuration decision.* In Kubernetes, a normal ClusterIP service returns one virtual IP while a headless service returns the A records of the individual pods — the [pod DNS documentation](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/) specifies both — so two services that "use DNS" receive a single load-balanced address or a raw member list depending on a YAML flag the calling code never sees.
- *The records that make discovery richer exist and go unused:* SRV records ([RFC 2782](https://www.rfc-editor.org/rfc/rfc2782)) carry port, priority, and weight — enough for full discovery — but most clients resolve only A records and hard-code ports, so "DNS discovery" in practice means "DNS addressing".
- *Names are stable, resolutions are not:* a service rename leaves the old name cached (negative caching on the old name is the [DNS assumptions](dns-assumptions.md) chapter's subject), split-horizon setups resolve the same name differently inside and outside the cluster, and migration tooling that flips DNS makes the name a deployment instrument with the TTL as its blade.
- *DNS membership updates are pull-based:* resolvers honor record TTLs, so membership changes propagate at TTL speed — minutes of ghost routing are designed into any DNS-based discovery, as the load-balancing follow-up's [DNS-vs-registry comparison](../followup-tree/load-balancing.md) develops.

### Counterexample

A team replaces `orders.internal` with `orders-v2.internal` and keeps the old name as a CNAME during migration. Clients in the cluster resolve fine; the batch tier outside the cluster resolves through a corporate resolver whose cached answer for the old name was negative — cached from a lookup during a window when the record was misconfigured. For the negative TTL (30 minutes here), the batch tier's discovery fails while the in-cluster fleet is unaffected: same name, same service, two truths, differing only in which resolver answered. The corrected contract: treat DNS-based discovery as TTL-bound and resolver-dependent — verify from *every* vantage point that will resolve the name, pre-warm critical names before cutover, and use SRV or registry-based discovery when ports or per-instance membership are actually needed.

### What changes when the assumption is removed

Corrected statement: *a DNS name is a stable handle for a resolution that is cached, vantage-point-dependent, and usually port-blind; DNS-based discovery is appropriate when membership changes at TTL speed and a single load-balanced address suffices, and inappropriate exactly when the design needs per-instance membership or fast eviction.* The mechanism choice — DNS versus registry versus mesh — is the discovery decision, made from staleness and granularity requirements rather than familiarity.

### Consequences

The interview probe "why do service meshes exist if we have DNS?" is answered by this assumption: meshes push membership changes and carry per-instance health, which DNS's TTL-bound, address-shaped model cannot — the [DNS and CDN routing atlas](../connection-atlas/dns-cdn-routing.md) maps the same boundary at global scale.

## Assumption 4: "Discovery Is a Neutral Lookup, Not a Policy Decision"

### The taught rule

Discovery just answers "where is service X?"; routing policy — load balancing, locality, retries — is a separate layer the caller controls, and the registry does not make choices on anyone's behalf.

### The hidden assumptions

- *The discovery topology chooses the consistency model.* Registries are distributed systems with their own CAP position: systems in the Consul-and-Eureka lineage deliberately serve possibly-stale membership during partitions — Consul's DNS interface documented in its [discovery documentation](https://developer.hashicorp.com/consul/docs/discover/dns) continues answering from local state — which is a policy (availability over freshness) made for every caller.
- *Push versus pull is a liveness policy:* an Envoy-style control plane can push endpoint updates within milliseconds (the [service-discovery architecture documentation](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery) contrasts eventual-consistent and strongly-consistent delivery), while polling clients batch changes at refresh granularity, so the caller's failure window is set by a choice made in the discovery layer.
- *Cache expiry is a synchronization event:* 2,000 clients refreshing a 30-second instance list produce about 67 queries per second steady-state, but if the list carries an expiry timestamp aligned across clients — or a registry restart aligns everyone — the refresh rate spikes by an order of magnitude against the registry, and discovery becomes the outage. The [caching assumptions](caching.md) chapter's stampede mechanics apply verbatim to instance lists.
- *Locality and filtering are policy too:* same-zone preference, canary filtering, and subset routing are usually implemented inside discovery clients — so "just a lookup" already contains the traffic-shaping decisions that outages and hot spots trace back to.

### Counterexample

A registry holds 5,000 instances, and all 2,000 consumer processes refresh their full instance list with a 30-second TTL. A registry failover briefly resets list expiries; consumers that had staggered refreshes now align, and the registry faces a burst near 2,000 queries in one second — twenty-plus times steady-state — precisely when it can least serve it. Refreshes time out, clients keep expiring lists, and the retry loop turns a transient registry blip into a fleet-wide discovery outage: every service in the platform loses routing simultaneously. The corrected contract: jitter refresh timers (±20% of interval), serve a last-known list on refresh failure (stale-but-usable, the AP choice made explicitly), rate-limit client refresh retries with backoff, and size the registry for the aligned worst case, not the average.

### What changes when the assumption is removed

Corrected statement: *every discovery mechanism embeds policy — staleness versus availability (its CAP position), push versus pull latency, cache expiry behavior, and locality filtering — and the caller inherits all of it; the design task is to choose the mechanism whose embedded policy matches the service's failure budget, and to damp its synchronization points (jitter, stale-on-error) explicitly.* The CAP framing behind this is the [consistency-availability-partition misconception](../misconceptions/consistency-availability-partition.md) audit, read from the registry's chair.

### Consequences

"Where does discovery live in your outage tree?" is the senior interview question: a discovery layer is a dependency of every other dependency, and its failure is total — which is why the corrected statement above makes stale-on-error a deliberate, documented choice rather than an accident of implementation.

## Interview Questions

1. **An instance dies — how long until no client routes to it? Give the formula.** Heartbeat interval + registry eviction threshold + client refresh interval (plus any load-balancer propagation). With 10 s + 30 s + 30 s, up to 70 seconds of ghost routing; the design should state this budget and make ghost calls fail fast and retry cheaply.
2. **Why can an instance be "healthy" in the registry and still fail every request?** Check depth (TCP connect passes above a wedged application), vantage point (reachable from the probe, not from the caller), and readiness predicates that do not measure functional warmth. Callers need their own failure statistics and circuit breaking.
3. **Kubernetes has both ClusterIP and headless services — what discovery difference does that flag make?** ClusterIP resolves to one virtual IP (per-connection balancing, membership hidden); headless returns each pod's A record (raw membership to the client). Same name, two discovery models — ports, eviction speed, and client-side policy all differ.
4. **A registry blip took down discovery for the whole fleet. What design numbers were missing?** Refresh jitter (aligned expiries turned 67 QPS into a ~20× burst), stale-on-error behavior, and refresh retry backoff. The registry's capacity was sized for the average, and discovery is the one dependency every other one has.

## Key Takeaways

- A registry lookup returns the past: staleness is heartbeat + eviction + client refresh, and the budget should be stated and tuned like any other latency number.
- Health is depth- and vantage-dependent; a returned instance is a candidate, and the caller's own failure statistics must be the final authority.
- DNS is TTL-bound, vantage-dependent, and usually port-blind; it fits discovery whose membership changes slowly and whose consumers need one address, not a member list.
- Discovery embeds policy — CAP position, push versus pull, cache expiry, locality — so the mechanism choice is a routing-policy choice, and its synchronization points need jitter and stale-on-error dampers.
- Discovery is every service's dependency; its failure modes (stampedes, ghost routing, aligned expiries) are fleet-wide by construction, which is why the numbers in this chapter belong in design documents.

## Cross-References

- [DNS assumptions](dns-assumptions.md) — the mechanics twin: TTL semantics, negative caching, and round-robin, the ground under Assumption 3.
- [Network and distributed assumptions](network-distributed.md) — accurate failure detection and zero-latency calls, the general fallacies this chapter's registry arithmetic instantiates.
- [Caching](caching.md) — stampede and expiry-alignment mechanics, applied verbatim to instance-list refreshes in Assumption 4.
- [Follow-up tree: load balancing](../followup-tree/load-balancing.md) — the consumer-side escalation from "a list of hosts" to real balancing policy.
- [Misconception: consistency-availability-partition](../misconceptions/consistency-availability-partition.md) — the CAP claims behind registry behavior, corrected as a misconception.
- [Connection atlas: DNS, CDN, and routing](../connection-atlas/dns-cdn-routing.md) — the global-scale version of the same resolution-and-staleness trade.
- [Connection atlas: containers, cgroups, namespaces](../connection-atlas/containers-cgroups-namespaces.md) — the pod and namespace machinery whose membership registries track.
- The [Kubernetes pod DNS documentation](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [RFC 2782](https://www.rfc-editor.org/rfc/rfc2782) (SRV records), the [Envoy service-discovery architecture overview](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery), and [Consul's DNS discovery documentation](https://developer.hashicorp.com/consul/docs/discover/dns) are the primary sources above; all were fetched and verified this session.
