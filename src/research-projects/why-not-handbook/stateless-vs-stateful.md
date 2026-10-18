# Stateless vs Stateful: Where Does the State Live?

## Overview

"Keep services stateless" is repeated until it sounds like physics. It is not physics; it is a *placement decision*: every real system holds state — sessions, carts, rate-limit budgets, game ticks, WebSocket subscriptions — and the design question is **where it lives**. The four live options: sticky sessions (state in one node's memory, pinned by the load balancer), externalized state stores (state in Redis or a database, requested over the network per operation), self-contained tokens (state cryptographically carried with each request — JWT being the default example), and stateful local caches with *ownership* (each node owns a key range and its cache is authoritative for those keys). Each buys something the others cannot and pays a failure mode the others do not have.

This page runs the [handbook framework](./index.md) across the four. The preview: **sticky trades availability for locality; externalization trades locality for elasticity; self-contained tokens trade revocation for zero store hits; ownership trades rigidity for the best latency and consistency of all four.** The anti-isolation mechanics behind "state in one process is not shared" are in [process-full-isolation](../misconceptions/process-full-isolation.md).

## Step 1: The Problem and Its Constraints

A fleet of *N* interchangeable service instances behind a load balancer handles requests that reference user state. Constraints:

- **Latency budget per request.** A network hop to a state store costs ~0.5–2 ms in-datacenter per call, often several sequential calls per request; in-process memory is nanoseconds-to-microseconds. At 10 hops per request, the state store *is* the latency budget.
- **Node churn.** Autoscaling, deploys, and crashes add and remove nodes continuously. Any design where node identity matters must say what happens to the state when the node leaves.
- **Revocation semantics.** "Log out everywhere, now" is a hard requirement for some state (auth) and irrelevant for others (a shopping cart can be stale for seconds).
- **Write rate and cross-request continuity.** A session read once per request and written rarely is a different object from a game tick written 60× per second per player.

## Step 2: The Mechanisms

### Sticky sessions (state pinned to a node)

The load balancer routes a client consistently to one node (cookie insertion or source-IP hash); the node keeps session state in local memory. Mechanism-level consequences: reads and writes are local memory — fastest possible path, no serialization; but **node identity is now part of the session's durability contract**. A node loss kills every session pinned to it (users are logged out mid-flow); a scale-*down* event deliberately destroys sessions; the balancer's hash must be maintained through node membership changes. Sticky also *correlates* load with hash luck: one hot client group can saturate one node while others idle.

### Externalized session store

State lives in a shared store (Redis, a relational table); every request performs store lookups. This is the "stateless service" orthodoxy's actual mechanism — the *service* is stateless because the state moved, not because it vanished. Consequences: any node can serve any request (elastic, deployable, autoscaler-friendly), and the store becomes a **shared dependency whose outage is a total outage** — every request path now includes a network call to a component that can fail independently. The store's consistency model leaks into the application (a session updated concurrently by two tabs is a read-modify-write race on shared state; see [caching & distributed](./caching-distributed.md) for the consistency menu), and the standard cache-aside mitigation quietly reintroduces per-node staleness.

### Self-contained tokens (JWT and friends)

The server *signs* the state (claims: user id, roles, expiry) and gives it to the client; each request presents it; any node verifies the signature with a public key — **no store lookup at all**. Mechanism-level consequences: verification is CPU-only and infinitely cacheable; horizontal scaling is trivial because nothing is shared. The signature buys integrity but not *control*: the token is valid until expiry no matter what happened server-side. The **revocation problem** is structural, not a bug: logout, password change, role downgrade, and "ban this account now" cannot retract an unexpired token — the state of the *user* has changed but the token's claims have not. Mitigations, each a partial re-coupling: short access-token lifetimes + refresh tokens (revocation lands on the refresh flow, bounded staleness = access-token TTL), a denylist of revoked token IDs (a store again — but a *small* one consulted only for revocation checks), or token versioning (user record carries a version; mismatch invalidates — a store lookup per request, which is exactly the mechanism JWT claimed to remove). RFC 7519 ([JWT](https://datatracker.ietf.org/doc/html/rfc7519)) defines the token; the revocation semantics are *your* design.

### Stateful ownership: one key, one owner

A middle design the "stateless" slogan obscured: partition the key space across nodes (consistent hashing), and let each node hold its keys *in memory* as the authoritative copy, with leases to make ownership safe under partitions ([leases](../../distributed/advanced/leases.md); consensus mechanics in [consensus and leases](../connection-atlas/consensus-leases.md)). Consequences: the request for key K must reach owner(K) — a routing layer (shard-aware balancer, service mesh, the classic memcached client libraries) replaces the network hop to a store with *network routing to the data*; consistency is strong by construction (one owner per key at a time); failure of an owner is a *partial* event affecting only its keys, with lease-expiry handover. This is how real-time games shard players to servers, how chat systems pin channels to nodes, and how connection-oriented state must be arranged regardless of fashion.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Sticky sessions | Externalized store | Self-contained tokens | Stateful ownership |
|----------|-----------------|--------------------|------------------------|--------------------|
| Read/write latency | Memory (~ns–µs) | Network hop(s) (~0.5–2 ms each) | Signature verify (µs, cacheable) | Memory + routing hop |
| Elasticity | Poor (membership changes strand sessions) | Best (nodes interchangeable) | Best (nothing shared) | Requires rebalancing on membership change |
| Revocation/logout | Instant (state is mutable) | Instant (state is mutable) | **Not until expiry** — needs denylist/refresh design | Instant |
| Failure mode | Node loss destroys pinned sessions | **Store down = everything down** | Key leak = unrevokable access until expiry | Owner loss strands its keys until lease handover |
| Consistency | Single-node, trivially strong | Store's model (races on concurrent writes) | Stale claims until refresh | Strong via single-owner lease |
| Warm-start behavior | Cold = all sessions gone | Survives node churn | Survives everything (that's the problem) | Keys rebalanced; in-memory state rebuilt from durable backing if designed |

The failure-mode column is the decision driver: **each option relocates the single point of failure** — sticky puts it in one node, externalization in one store, tokens in one key, ownership in the lease/rebalance machinery. Choosing is deciding *which* outage you are willing to have.

## Step 4: When Each Wins

**Sticky sessions win** when: sessions are short-lived and cheap to lose (anonymous browsing state); the fleet is small and stable; or the state is genuinely connection-bound already (an established WebSocket *is* affinity by construction). Its modern niche is narrow but real.

**Externalized stores win** when: nodes must be interchangeable (aggressive autoscaling, zero-downtime deploys); state must survive node loss; state is shared across clients/devices (a cart visible on phone and web); or write volume is modest enough that per-request hops fit the latency budget. This is the right default for most web backends — the orthodoxy is popular because the constraint set above is common.

**Self-contained tokens win** when: verification-per-request is the hot path (API gateways, service-to-service auth at high QPS); issuers and verifiers are separate trust domains (the token is the contract); or short-lived grants make revocation latency tolerable (access token TTL of minutes). They lose outright when "revoke within seconds" is a requirement and no denylist/refresh machinery is acceptable.

**Stateful ownership wins** when: state changes faster than a store round trip allows (game loops at 20–60 ticks/s); state is per-connection (WebSocket subscriptions, cursors — see [WebSocket](../../networks/http/websocket.md)); or one-key-per-node gives strong consistency *and* locality that no shared store can match. The price is a routing/rebalancing layer and lease management — paid once, used forever.

## Step 5: Edge Cases and Counterexamples

- **JWT logout that logs out nothing.** A team ships JWTs with 24-hour expiry; "logout" deletes the token client-side; a stolen token (leaked from logs, an XSS, a proxy cache) remains valid for up to 24 h — including after password reset. The honest fixes are mechanism-level: cut access-token TTL to minutes and gate renewal on a revocable refresh token (revocation lands on a *server-side* object), or run a revocation denylist keyed by `jti` (re-adding a small store to every verification — measure the mechanism you reintroduced). Lesson: **"stateless auth" still holds state — it holds it in the client, where you cannot reach it.**
- **The session store outage that was not "a cache miss".** Because every request reads the store, its failure is a *full-site* failure — yet teams size and monitor it like a cache. Two edge behaviors decide the incident: does the store fail open (requests proceed unauthenticated — usually a security violation) or fail closed (complete outage)? Pre-decide, and give the store the failure isolation of a real dependency (replicas across zones, per-service isolation) rather than sharing one Redis among everything ([caching-distributed](./caching-distributed.md) covers the per-operation consistency choices).
- **Sticky sessions + autoscaler = session massacre.** Scale-*in* under a load dip terminates nodes; every session pinned to them dies at once — the event is periodic, predictable, and invisible in unit tests. Mitigations that keep stickiness where it is genuinely needed: drain connections before termination (connection draining), move session state to the store *only for durable bits* while keeping hot ephemeral bits local, or use connection-level affinity (WebSocket) where the connection object *is* the state and draining is the contract.
- **The rate limiter split-brain.** A per-user rate limit of 100 req/min stored on each node's memory allows N×100 per minute across N nodes — each node sees only its 1/N of the traffic. Local state without ownership *or* a shared counter gives a limit N times weaker than configured. Fixes per state type: shared atomic counter (Redis `INCR` with TTL — one network hop per request), or a token-bucket sync protocol, or accept the approximate limit and *say so* ([rate-limiter design](../followup-tree/rate-limiter-design.md) carries the full algorithm ladder).
- **Game servers: where "stateless" is unimplementable.** A 30 Hz game loop holds authoritative world state and mutates it 30×/s per player; every design that pushes those mutations through a shared store loses (30 Hz × thousands of players × 1 ms = the store is saturated and the loop still needs the value *back*). The only workable shape is ownership: player/world keys owned by one server, durable snapshots to backing storage at intervals, migration of ownership at player handoff ([leases](../../distributed/advanced/leases.md) make the ownership claim safe). This is the counterexample to memorize: **the state's mutation rate, not fashion, chooses the design.**

## Step 6: Decision Framework — Per State Type

1. **Auth/session tokens:** default short-lived JWT + revocable refresh tokens; if instant global revocation is contractual, add a `jti` denylist (a tiny store) or version-gated tokens; keep the access-token TTL the *stated* bound of your revocation latency.
2. **Cart / user documents:** externalized store (survives nodes, works cross-device); cache-aside locally only if latency demands, accepting staleness rules.
3. **Rate-limit counters:** shared atomic counters when exactness matters; local-approximate counters only with an explicitly weaker advertised limit; never per-node memory for an exact global limit.
4. **WebSocket / real-time:** stateful by nature — affinity per connection, connection-local state, ownership for shared world/channel state; drain connections on node retirement.
5. **Ephemeral hot state (games, tick loops, live aggregation):** one-key-per-node ownership with leases; durable snapshots to a backing store; ownership migration at natural boundaries.
6. **Cross-cutting test for any candidate design:** name the component whose death takes the system down, name the revocation latency for "kill this credential now", and name the staleness a user can observe. If any of the three has no answer, the placement decision is not made yet.

## Interview Questions

1. **"We use JWT so our services are stateless." What state did you keep, and where?** In the client, and in the verifier's trust configuration (keys) — the token carries claims you cannot retract. The revocation problem is structural: signature validity is independent of the user's current status. Short TTLs + refresh, denylists, or version checks each reintroduce server-side state *on purpose*; naming which one and its latency bound is the real answer.
2. **Your Redis session store dies. What exactly happens, and what two design decisions made beforehand change the outcome?** Every request path that reads the store fails — full outage, not degraded cache behavior. The two decisions: fail-open vs fail-closed semantics (security vs availability), and isolation/replication posture of the store (shared single instance vs per-service replicated store). Both are placement decisions, not tuning.
3. **Why does a per-node in-memory rate limiter under-count by exactly the fleet size?** Each node observes 1/N of a user's traffic and enforces the full limit against that fraction — aggregate allowance becomes N × limit. Exactness requires a shared counter (per-request hop) or an ownership model (user pinned to one node); approximations must be advertised as weaker.
4. **A real-time game needs 30 Hz authoritative state for 10,000 concurrent players. Why is externalizing state to Redis wrong at the mechanism level?** The mutation rate (300k writes/s plus the read-back latency per tick) exceeds both the store's budget and the loop's latency tolerance; the loop needs the *result* of each mutation immediately. One-key-per-node ownership keeps mutation in the owner's memory with lease-gated ownership and periodic durable snapshots — the store becomes a checkpoint layer, not the hot path.
5. **What does sticky-session affinity break that connection-level affinity does not?** Sticky binds a *session* (abstract, recoverable-in-principle) to a node whose membership changes under autoscaling — scale-in mass-terminates sessions. A WebSocket connection is itself the stateful object: affinity is not simulated by a balancer, it is physical, and retirement is handled by draining, which has well-defined semantics. Cookie-stickiness is a workaround for state that should have been either externalized or made connection-native.

## Key Takeaways

- "Stateless" always means **state placed elsewhere** — a store, a token, or a client. The design question is which placement's failure mode and latency profile the workload can afford.
- Sticky trades availability for locality; externalization trades locality for elasticity and adds a shared dependency; self-contained tokens trade revocation for zero store hits; ownership trades a routing layer for locality *and* strong consistency.
- Each placement relocates the single point of failure: node (sticky), store (externalized), client-held key (JWT), lease machinery (ownership). Name yours explicitly.
- The state's *mutation rate* is the strongest selector: low-rate, durable-ish state externalizes cleanly; high-rate, connection-bound state demands ownership; auth tokens live on a revocation-latency spectrum.
- Decision frameworks must be per state type — one system legitimately uses all four placements at once.

## Cross-References

- [Process Full Isolation: Misconceptions](../misconceptions/process-full-isolation.md) — why in-process state is not shared, the mechanism under every "just put it in memory" plan.
- [Consensus and Leases: Connection Atlas](../connection-atlas/consensus-leases.md) — how ownership claims stay safe under partitions and clock drift.
- [Leases](../../distributed/advanced/leases.md) — the time-bounded ownership primitive behind stateful designs.
- [WebSocket](../../networks/http/websocket.md) — the connection layer that makes stateful affinity physical.
- [Caching & Distributed](./caching-distributed.md) — sibling page: consistency and staleness choices for the externalized-store path.
- [Redis](../../dbms/caching/redis.md) and [Redis Data Structures](../../redis/data-structures.md) — the externalized store's toolkit, including atomic counters.
- [Rate Limiter Design: Follow-up Tree](../followup-tree/rate-limiter-design.md) — the counter-placement problem in algorithmic depth.
- [Consistency Fundamentals](../../distributed/fundamentals/consistency.md) — the guarantee vocabulary for "how stale is a session".
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
