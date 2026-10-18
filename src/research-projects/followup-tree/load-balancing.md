# Follow-up Tree: Load Balancing

## Overview

"What is the difference between an L4 and an L7 load balancer?" is the infrastructure interview's most economical opener: the first answer (one balances packets, the other requests) is true, teachable, and the doorway to the entire scaling stack — scheduling algorithms, health checks, session affinity, failover, and global traffic management. Interviewers like this ladder because every rung separates candidates who have operated a load balancer from candidates who have drawn one: the operator knows why least-connections wins only under specific conditions, why a passing health check does not mean traffic works, and why the dangerous scaling talks are the ones that never mention where state lives. This page walks the ladder rung by rung, stating what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. The coupling map for load balancing and partitioning — how spreading *requests* interacts with spreading *data* — lives in the sibling project as [Load Balancing and Partitioning](../connection-atlas/load-balancing-partitioning.md); this page is the interview escalation ladder, that page is the connection map between the two mechanisms. Book-level depth lives in [L4 vs L7](../../networks/load-balancing/l4-vs-l7.md), [Algorithms](../../networks/load-balancing/algorithms.md), and [Reverse Proxies](../../networks/load-balancing/reverse-proxy.md).

## The Opening Question

**"What is the difference between an L4 and an L7 load balancer?"**

The expected core answer: an L4 balancer makes its decisions on connection- and packet-level information — IP addresses and ports, and in some designs the TCP handshake itself — without terminating the connection, so it can be extremely fast but can only see *which* client talks to *which* backend, never *what* the client wants. An L7 balancer terminates the protocol, reads the requests — URL paths, headers, cookies — and can route by content, rewrite responses, and offload TLS.

A weak answer recites the layer numbers and stops, leaving unexplained *why* the difference matters operationally. The strong answer names the consequences: L4 sees no requests, so it cannot route by path, cannot make per-request retry decisions, and can still balance connections on the fly; L7 costs a full protocol termination per request but gains sticky cookies, header-based routing, and the ability to retry a failed request on another backend — a thing L4 can never do once the connection's destination is chosen. The follow-up that escalates: **"Given a fleet, which algorithm decides which instance gets the next request?"** — the scheduling rung.

## Level 2: Scheduling Algorithms — Round-Robin, Least-Connections, Weighted, Hashing

**What it tests:** whether you can choose an algorithm from workload properties instead of a default, and whether you know why the classic algorithms fail when instances differ or requests differ in cost.

**Weak answer:** "Round-robin distributes requests evenly, so that is what we use" — treats even request *count* as the goal, which it is not; the goal is even resource *load*.

**Strong answer:** distinguishes request-count fairness from work fairness, knows the conditions where each algorithm wins and the failure each one is blind to, and can state why least-connections is the safer default behind heterogeneous request costs.

**Escalation trigger:** "Two backends, one twice as powerful — and your requests take anywhere from 1 ms to 5 s. Why is round-robin a disaster here?"

**Answer.** Round-robin assigns request N to backend (N mod k); it is fair in count, stateless, and free — and wrong in almost every interesting case. With heterogeneous request costs (some requests 1 ms, some 5 s), count-fairness means the backend that happened to catch the slow requests stays busy while its "fair share" idles: the queueing signature is uneven latency across identical-capacity instances. Least-connections assigns to the backend with the fewest in-flight requests, which self-corrects for cost heterogeneity — a slow request holds its slot, so the balancer routes around it — and it is the default worth defending for general request streams (see the queueing arithmetic in [Connection Pooling](./connection-pooling.md) and [Scheduling and Queueing](../connection-atlas/scheduling-queueing.md)). Weighted variants encode *capacity* differences (a 2× machine gets weight 2) but not cost skew. Hashing (IP-hash or a header/cookie hash) buys *affinity* — the same client lands on the same backend — at the price of load-blindness: a hot client or a skewed hash can overload one backend, and the fix (consistent hashing) is its own rung below. The senior move is naming the invariant each algorithm trades: round-robin trades workload awareness for simplicity, least-connections buys awareness with per-connection state in the balancer, hashing buys affinity and loses balance.

## Level 3: Health Checks and Failover — Detection Is Not Removal

**What it tests:** whether you model health checking as a distributed-systems problem — detectors are wrong, information is stale, and removal decisions have their own failure modes — rather than a config toggle.

**Weak answer:** "The balancer checks /healthz and stops sending traffic to dead instances" — no model of check semantics, detection latency, or what happens during the gap.

**Strong answer:** distinguishes passive detection (real-traffic failures, connection resets, timeouts) from active checks (synthetic probes), explains why an instance can pass active checks while failing real traffic, and describes the failover gap: between death and removal, requests are still being routed into the failure.

**Escalation trigger:** "Your health checks pass, deploys are clean — and one in fifty requests still fails. Where do you look?"

**Answer.** Active checks are synthetic: the balancer periodically opens a connection and requests a health endpoint, and the probe tests exactly the path the probe takes — which is why the classic incident is the health check passing while the real path fails: the probe hits a warm code path, a different port, a different dependency, or its own connection pool. Passive detection watches actual traffic — resets, timeouts, 5xx rates — and is slower but tests the truth. Production systems layer both: aggressive intervals catch failures fast but false-positive healthy-but-slow instances into removal, shrinking capacity exactly under load (the same feedback [Backpressure](../connection-atlas/backpressure.md) documents).

The failover gap is the senior content: detection latency × request rate is a *count* of requests sent to a corpse — 5-second detection at 1,000 rps is 5,000 failures unless the client retries, and then retries amplify the load onto survivors (a retry storm — the mitigation ladder is the same one in [Timeouts and Retries](../assumptions-hunt/timeouts-and-retries.md): budgets, jitter, circuit breaking in [Circuit Breakers](../../distributed/microservices/circuit-breakers.md)). The subtlety that earns credit: *removal* is easy, *re-addition* is hard — a recovering instance must be warmed (caches, pools, JIT) before full weight, or it dies again under the sudden flood, which is why slow-start ramps and readiness gates exist in [Kubernetes Pod Lifecycle](./kubernetes-pod-lifecycle.md).

## Level 4: Session Affinity — Why Statelessness Is a Scaling Property

**What it tests:** whether you understand *why* sticky sessions exist, what they cost, and why "make it stateless" is the answer interviewers wait for — plus the mechanics of achieving affinity when you cannot.

**Weak answer:** "Sticky sessions keep the user on the same server" — no why, no cost, no alternatives.

**Strong answer:** explains affinity as a compensation for server-local state, prices the compensation (hot spots, skewed failover, broken draining), and lists the migration path: externalize state (shared store, client-side tokens) until affinity is optional.

**Escalation trigger:** "We added a second instance and now users get logged out randomly. What is happening and what are three fixes?"

**Answer.** Login state stored in server memory (an in-process session map) is invisible to the second instance: round-robin sends half the requests to a server that has never seen the session cookie's identity, and every miss is a logout. Affinity via source-IP hash or an affinity cookie papers over it — the same client sticks to the same instance — and it *works* until it does not: clients behind corporate NAT collapse thousands of users into one source IP (hot spot), a dead instance dumps all its sessions at once (failover cliff — every stuck user re-authenticates simultaneously), and draining deployments must wait out session lifetimes. The three fixes, in order of preference: move the session to a shared store (Redis or the database — every instance reads the same truth; see [Redis Caching](./redis-caching.md) for the cache-aside machinery), move it to the client as a signed/encrypted token (stateless verification, size and revocation caveats — the mechanics are in [Auth, Identity, and Session](../connection-atlas/auth-identity-session.md)), or keep affinity deliberately for the one workload that needs locality (long-lived WebSockets, expensive warm state) while making the rest stateless. The senior framing: affinity is a *performance* optimization once state is externalized, and a *correctness* crutch before it — confusing the two is how scaling projects stall.

## Level 5: Consistent Hashing, Anycast, and the Judgment Rung

**What it tests:** the design-judgment boundary — global load balancing, the algorithms that survive membership change, and whether you can assemble L4/L7, health checks, affinity, and DNS into a defended architecture.

**Weak answer:** knows consistent hashing exists because caches use it, and that anycast is "a network thing" — cannot say what problem each solves or when they are the wrong answer.

**Strong answer:** derives consistent hashing from the rehash storm of naive mod-N (every key moves when one node joins); connects anycast to BGP routing as load balancing by infrastructure (nearest point of presence, with failover lag); and can sketch the full stack — DNS/anycast picks a region, L4 picks an instance tier, L7 picks a backend by content — with the failure modes of each layer.

**Escalation trigger:** "Cache cluster of 50 nodes, one dies — with mod-N hashing, what happens? And what does consistent hashing change?"

**Answer.** With mod-N, N changes from 50 to 49 and *almost every key* maps to a new node — a cache-wide miss storm hitting the database exactly when capacity shrank; the escalation is self-amplifying (misses add database load, slower responses, more pressure — the thundering-herd family from [Redis Caching](./redis-caching.md)). Consistent hashing maps both nodes and keys onto a ring so a membership change moves only ~1/N of keys; virtual nodes smooth the variance and even out heterogeneous capacity (the mechanics and the rendezvous alternative are in [Rendezvous Hashing](../../distributed/advanced/rendezvous-hashing.md) and [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md)). Anycast is load balancing at the routing layer: one address announced from many sites, BGP delivers the client to the nearest announcement, and failover is a route withdrawal — global, fast, and blind to per-instance health (the DNS/TTL interaction is the chain in [DNS Resolution](./dns-resolution.md), the routing mechanics in [Anycast and Geo-Routing](../../networks/cdn/anycast-and-geo-routing.md)).

The judgment synthesis the rung expects: layer the decisions and say which failure each layer catches. Anycast/DNS chooses *where in the world* (minutes of staleness, coarse weights); L4 chooses *which instance tier* (fast, blind to content, can't retry requests); L7 chooses *which backend and which path* (full visibility, per-request retries, affinity cookies) — with the L4-terminating/L7-backend handoff, connection draining, and health-check semantics at each seam (the packet-splicing internals are in [L4 Load Balancing Internals](../../networks/advanced/l4-load-balancing-internals.md)). The coupling to *data* placement — balancing requests means nothing if the data those requests need lives elsewhere — is the map in [Load Balancing and Partitioning](../connection-atlas/load-balancing-partitioning.md); and when the balancer itself becomes the bottleneck or single point of failure, the answer is the same design the ecosystem converged on: ECMP/anycast L4 tiers in front of horizontally scalable L7 proxies — never one hero box.

## How to Approach Unfamiliar Variations

The template for load-balancing variations — "balance gRPC," "balance WebSocket connections," "the balancer is saturating," "balance across regions":

1. **Ask what a "request" is at the layer you are balancing.** L4 balances connections (long-lived ones pin their backend for the connection's life — WebSockets and gRPC streams make even count-fairness meaningless); L7 balances requests (but HTTP/2 multiplexes many requests over one connection, changing L7 behavior). Name the unit and the algorithm question re-derives itself.
2. **Follow the state.** Every affinity question is a state-location question: find what the backend remembers (sessions, caches, streams), and the cost of the stickiness is the cost of that memory.
3. **Price the detection gap.** Any failover claim is incomplete without detection latency, check semantics, and the retry policy during the gap. "Failover takes RTO seconds and loses RTO × rate requests, mitigated by idempotent retries" is a senior sentence.
4. **When the balancer is the bottleneck, change what it terminates.** TLS handshakes, header rewrites, and connection bookkeeping are CPU work; the escalation path is L4 packet-splicing, more L7 proxies, or pushing decisions (with hashing) into the clients — say which resource saturates first and why.

## Interview Questions

**Q: Your L7 balancer reports 30 percent CPU and latency through it is fine; the backends report 80 percent. Someone proposes "remove the balancer to save a hop." Evaluate.**
A: Reject the framing: at 30 percent the balancer is not the bottleneck, and the "hop" is doing protocol work (TLS, routing, retries) that the backends would otherwise absorb worse. Removing it loses health-aware routing and per-request retries. The real question is why backends are at 80 percent — capacity or request cost — and the balancer's CPU budget matters only at saturation, where the answer is more balancer replicas.

**Q: Why can an L4 balancer not retry a failed request on another backend?**
A: Because L4 forwards a *connection*: the client's TCP (and often TLS) termination is at one chosen backend, and the balancer only sees encrypted or stream bytes. A retry requires re-issuing an application-level request — which requires reading it — which requires L7 termination. L4 can only fail the connection and hope the client reconnects; this is precisely why L7 exists despite its cost.

**Q: Least-connections balances well, yet a team reports one backend pegged while others idle, with no weight config. Diagnose.**
A: Affinity leakage: a hash-based or cookie-based stickiness rule is overriding the algorithm for that traffic class, or long-lived connections (WebSockets, pooled gRPC) opened before a deploy are pinning load. Least-connections only sees *new* dispatches; connections that never close are invisible to it. Fix: drain/rotate long-lived connections, or move stickiness decisions explicitly rather than by accident.

**Q: A failover test kills an instance; 8 seconds of errors follow, then full recovery. The health check interval is 2 s. Explain the gap and shrink it safely.**
A: The gap is detection latency plus removal propagation plus client behavior: the check interval is a *lower* bound, not the whole story — failure thresholds, check timeouts, balancer propagation, and in-flight requests all add up, and clients may retry into the same gap. Shrink safely with passive failure detection on real traffic (instant reset/timeout signals), a failure threshold tuned against probe variance so slow-but-alive instances are not evicted, and idempotency-aware client retries with jitter so the retry burst does not stampede the survivors.

## Key Takeaways

- L4 balances connections without understanding them; L7 terminates the protocol and buys content routing, retries, and affinity at the price of termination cost — the layer you pick decides which failures you can even see.
- Round-robin balances request counts, least-connections balances in-flight work; with heterogeneous request costs, only the second tracks the goal.
- Health checks are fallible distributed detectors: active probes test the probe's path, passive detection tests the truth, and detection latency × request rate is the failure count you accept during failover.
- Sticky sessions are a crutch for server-local state; externalize the state and affinity becomes a tunable performance tool instead of a correctness dependency.
- Consistent hashing exists because mod-N rehashing moves nearly all keys on membership change; anycast moves the problem to BGP and gains global reach with coarse control.
- The architecture that scales is layered: anycast/DNS chooses the region, L4 chooses the tier, L7 chooses the backend — each layer catches a different class of failure.

## Cross-References

- [TCP Lifecycle](./tcp-lifecycle.md) — the connection state machine the L4 tier forwards.
- [DNS Resolution](./dns-resolution.md) — the TTL-as-blast-radius chain that governs how fast DNS-level balancing can react.
- [Rate Limiter Design](./rate-limiter-design.md) — the design-ladder sibling: load balancing spreads load, rate limiting rejects it, and both are admission control.
- [Kubernetes Pod Lifecycle](./kubernetes-pod-lifecycle.md) — readiness gates, graceful termination, and slow-start as the orchestrator's half of health checking.
- [Hash Tables](./hash-tables.md) — where hashing-as-distribution entered your toolkit.
- [Load Balancing and Partitioning](../connection-atlas/load-balancing-partitioning.md) — the coupling map between spreading requests and spreading data; this page is the ladder, that page is the connection.
- [L4 vs L7](../../networks/load-balancing/l4-vs-l7.md) — the book chapter on the trade this ladder's opening rung introduces.
- [Algorithms](../../networks/load-balancing/algorithms.md) — scheduling algorithm catalog with the failure modes of each.
- [Reverse Proxies](../../networks/load-balancing/reverse-proxy.md) — the L7 proxy as the workhorse implementation of the L7 rung.
- [L4 Load Balancing Internals](../../networks/advanced/l4-load-balancing-internals.md) — packet splicing, ECMP, and the Maglev-style designs behind the L4 tier.
- [Anycast and Geo-Routing](../../networks/cdn/anycast-and-geo-routing.md) — BGP-layer load balancing and the global traffic tier.
- [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) and [Rendezvous Hashing](../../distributed/advanced/rendezvous-hashing.md) — the membership-change-safe distribution algorithms from Level 5.
- [Circuit Breakers](../../distributed/microservices/circuit-breakers.md) — the client-side complement to balancer-side failover.
- [Auth, Identity, and Session](../connection-atlas/auth-identity-session.md) — where session state lives and what affinity costs.
