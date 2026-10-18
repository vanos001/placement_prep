# "Our microservices are stateless, so scaling is trivial"

## Overview

This page audits the scaling claim attached to almost every microservices
pitch: because the services are "stateless", scaling is trivial — add pods,
add nodes, done. The reality is that state is not eliminated by this
architecture; it is *moved* — into session stores, token caches, Redis
clusters, databases, and queues that the "stateless" tier reads and writes
on every request. The application tier may scale horizontally with pleasant
indifference, but the stateful backing services absorb the load, become the
actual scaling frontier, and bring back every problem the claim was meant to
banish: partitioning, replication lag, failover, and even affinity, which
sneaks home through cache locality and sticky routing to the cache that
warmed a user's data. The phrase is not wrong so much as directional: it
answers a question about the tier with the confidence of an answer about
the system, and the difference between the two is where the capacity plans
of real architectures actually live. This page states the claim fairly,
follows the state
to where it actually lives, and works the scale-out counterexample in which
adding replicas makes the system slower.

## The Claim, Stated Fairly

The strongest common form of the claim is: "Our services hold no state in
memory — sessions are in Redis, data is in Postgres — so any instance can
serve any request, and scaling is just adding instances behind the load
balancer." Stated this way, the claim is largely accurate as far as it goes:
the tier described genuinely can scale elastically, and moving state out of
process memory is a real and valuable architectural decision with real
benefits for deployability, failure handling, and load balancing.

The claim deserves its fairness because "stateless" is not a lie — it is a
true statement about *where state is not*. The question is whether "state is
not here" honestly compresses to "scaling is trivial" — whether the
statement about the tier answers the question about the system.

## Verdict

**Incomplete.** The claim is true in the regime where the backing stateful
services have abundant headroom, and voided exactly when scale is the
question being asked: the moment you scale out the stateless tier, its
backing stores absorb proportionally more load, and the system's scaling
bottleneck is wherever the state actually lives. State under the
architecture is relocated and concentrated, not vanished — and concentration
creates the very scaling problems "stateless" was advertised to remove.

## Why People Believe It

The kernel of truth is strong enough to carry the claim through most
experience. Stateless-in-process design genuinely makes the application tier
elastic, deployable, and restartable without user impact; autoscalers work
on it without ceremony; and the disciplines it removes (session pinning,
in-memory caches that fork per process) are genuinely painful. Teams that
migrated from sticky-session monoliths remember the improvement vividly, and
the architecture diagram — a row of identical boxes over a database cylinder
— visually confirms that "the boxes" are the thing being scaled.

The deletion happens at the word "trivial". The claim silently moves the
noun: "our *tier* scales trivially" is true; "our *system* scales trivially"
is the conclusion being sold. Because the tier is what you operate daily and
the backing store is a managed service in a console, the visibility
asymmetry does the rest — the component that scales in front of your eyes
gets the credit, and the component that saturates gets called "the
database's problem".

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "The services are stateless" | True in-process: request state lives outside the compute tier, in named backing services |
| "State is eliminated" | False: state is relocated — session stores, token caches, databases, queues, caches — and concentrated |
| "Scaling is trivial" | Scaling the tier is trivial; scaling the system means scaling the backing services, which is where the hard problems moved |
| "Any instance serves any request" | True at the LB; affinity returns anyway via cache locality and sticky routes to warmed state |
| "The bottleneck scales with the app" | No: shared stateful services saturate first, and their saturation is worse than a single app node's |
| "Adding replicas is always safe" | Mass scale-out can cause cold-cache stampedes, connection exhaustion, and rebalancing storms |

The correct sentence: "Stateless means the state has a home that is not the
application process — and therefore scaling the application is bounded by
how well that home scales, replicates, partitions, and fails over. We made
the easy part stateless and inherited all of the hard state problems in one
place."

## Where It Breaks

**Follow the state to the bottleneck.** Trace one request through the
"stateless" tier: the auth middleware validates a token — refresh tokens and
revocation lists live in a token store; the handler fetches the session —
session store; the handler reads the user's cart — cache, then database; the
handler enqueues the side effect — queue. Six stateful services underpin
every request, and every replica added to the stateless tier multiplies
connections and queries against them. When the system saturates, it
saturates at the Redis cluster's single hot key, at the primary database's
write path, or at the queue's partition limit — none of which care that the
tier in front of them is infinite. The architecture made the *application*
infinite and left the *system* finite.

**Affinity sneaks back through caches.** The promise was "any instance can
serve any request", and at the load balancer that is literally true. But
locality re-forms immediately one layer down: the first request for a user
warms a cache entry, so the second request is fast wherever the entry lives,
and operations teams install sticky routing (to processes, to cache shards,
to reader replicas tuned for freshness) to raise hit rates. Each stickiness
is state-affinity in the old sense, and each reintroduces the costs
"stateless" was supposed to banish: uneven load, painful drain and rebalance,
and user-visible regressions when the warm path breaks. The claim said
affinity was eliminated; the performance budget re-bought it.

**Scale-out has its own failure modes.** Autoscaling from 10 to 100 replicas
in a demand spike opens thousands of new connections to stores sized for the
old pool, exhausting connection limits that require PgBouncer-style pooling
or store-side tuning to survive. A mass of cold instances with empty caches
produces a thundering herd against the origin — the cache-warmer stampede
that turns a scale-out event into an outage. Sharded stores rebalance under
the new topology, and rebalancing consumes exactly the headroom the spike
needs. "Trivial" scaling assumes the backing services scale in lockstep for
free; each has its own capacity model, its own scaling lag, and its own
failure boundary.

**The queue is state too.** The asynchronous half of a "stateless" design
hides its state in the most operationally demanding place of all: a capped,
partitioned queue with consumers that rebalance. A stateless producer can
enqueue far faster than the consumer drains, and the backlog — offset
positions, in-flight messages, redelivery timers — is system state that
no instance restart clears. When the stateless tier scales out during a
spike, it multiplies *production* into a queue whose drain rate is fixed by
its partitions and consumer count; the backlog becomes latency for every
downstream effect, and the eventual consumer catch-up competes with fresh
traffic for the same store. Scaling the front tier without scaling the
queue's drain path is how architectures that "hold no state" accumulate
hours of stateful lag anyway.

**The stateful core is where consistency lives.** Once the state is
concentrated, every distributed-systems problem the tier avoided reappears
at the core: replication lag makes reads stale after writes, failover
requires quorum decisions, partitioning decisions made early bind the
scaling ceiling, and consistency-versus-availability tradeoffs can no longer
be dodged per service. The claim's emotional payload — "we don't have to
think about state" — is precisely the work the stateless architecture
concentrates instead of dissolving.

## Practical Implications

- In design reviews, treat "stateless" as a claim about the tier and demand
  the follow-up: enumerate the backing services, and for each, name the
  scaling limit (hot keys, write primary, connection ceiling, partition
  count) and the failover plan.
- Load-test the *system* at target scale, not the tier: the number that
  matters is when the session store or the primary saturates, and it will
  arrive well before the stateless tier's 200th replica.
- Design affinity deliberately where it buys performance — cache keys
  partitioned by user, reader replicas with freshness bounds — rather than
  letting sticky routing accrete invisibly until a drain becomes an
  incident.
- Bound the scale-out rate: connection pools, cache warmup, and store
  autoscaling must be coordinated with instance autoscaling, or the recovery
  action causes the outage.
- Say "state-externalized" rather than "stateless" in architecture docs; the
  honest word keeps the backing services in the scaling conversation.

## Interview Questions

### "Our microservices are stateless, so scaling is trivial." Where does this claim break?

At the word "trivial", applied to the system rather than the tier. State
moved into session stores, caches, databases, and queues; scaling the
stateless tier multiplies load on those, and the bottleneck is wherever the
state lives. A strong answer follows one request through its backing
services and names where the system saturates — the hot key, the write
primary, the connection ceiling.

### If any instance can serve any request, why do sticky sessions and cache affinity reappear anyway?

Because locality is economically irresistible: a warmed cache makes the
second request for a user faster, so teams route users to warm state to
raise hit rates. That routing is affinity by another name, with all the old
costs — uneven load, rebalance pain, drain problems. The load balancer lost
the stickiness; the performance budget re-bought it one layer down.

### You autoscale from 10 to 200 instances during a traffic spike and the system collapses. Give three mechanisms.

One: new instances exhaust store connection limits the old pool was sized
for. Two: cold caches stampede the origin database as empty instances
re-request the same entries. Three: sharded stores rebalance under the new
load, consuming headroom precisely when the spike needs it. Each is a
backing-service scaling limit that "stateless" claims did not remove.

### What is the difference between "stateless" and "state-externalized", and why does the distinction matter for capacity planning?

Stateless strictly means no durable state anywhere; practically it means
state lives in backing services outside the process. The distinction matters
because capacity planning for the stateless tier is trivial (CPU per
request), while capacity for the externalized state is the real system
limit — replication, partitioning, and failover of the stores. Using the
second word keeps the stores inside every scaling discussion.

## Key Takeaways

- Stateless means state relocated, not state eliminated: sessions, tokens,
  caches, and queues hold it, and they concentrate rather than distribute
  the difficulty — the word describes the process, not the system.
- The stateless tier scales elastically; the system scales exactly as well
  as its stateful backing services, which saturate first and fail hardest.
- Affinity returns through cache locality and sticky routing; the property
  the architecture claims is re-purchased by the performance budget.
- Scale-out has its own failure modes — connection exhaustion, cold-cache
  stampedes, rebalancing storms — so elasticity must be coordinated with
  the stores, not just the instances.
- The honest architecture sentence is "state-externalized", and it obliges
  you to answer for the stores: their limits, their failover, their lag.
- Scale the state where the state is: when the plan says "add replicas",
  check whether the replicas are for the tier that saturates or merely for
  the tier that is easy to saturate more without ever being the limit.

## Cross-References

- [Why-Not Handbook: Stateless vs Stateful](../why-not-handbook/stateless-vs-stateful.md)
  — the decision analysis this audit presupposes: the handbook weighs when
  to keep state in process versus externalize it, while this page audits
  the scaling claim made *after* choosing externalization.
- [Connection Atlas: Auth, Identity & Session](../connection-atlas/auth-identity-session.md)
  — where the first hidden state lives: session and token stores are the
  backing services most often forgotten when "stateless" is claimed, and
  that page maps their mechanics.
- [Misconception: "More replicas = more reliable and more consistent"](./more-replicas-more-consistency.md)
  — the replication sibling: adding copies of the *state* trades consistency
  for reliability, just as adding copies of the *tier* exposes the state's
  limits; both claims confuse count with capability.
- [Misconception: "A cache always improves performance"](./cache-always-improves.md)
  — the locality sibling: the cache that re-buys affinity only pays under
  reuse and hit-rate conditions, which is what makes sticky routes
  tempting and draining them painful.
- [Follow-up Tree: Redis Caching](../followup-tree/redis-caching.md) — the
  escalation chain for the stateful store that inherits the load.
- [Follow-up Tree: Message Queues](../followup-tree/message-queues.md) —
  the queue-shaped state whose partitions cap the throughput the stateless
  tier can drive.
- [Follow-up Tree: Load Balancing](../followup-tree/load-balancing.md) —
  how routing, connection counts, and affinity interact at the layer in
  front of the "any instance" pool.
- [Autoscaling](../../cloud/autoscaling.md) — the mechanics of scale-out,
  including the coordination with backing stores this page argues is
  mandatory.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- M. Kleppmann. *Designing Data-Intensive Applications*. O'Reilly, 2017 —
  the partitioning and replication chapters that govern how concentrated
  state scales, cited by title.
- M. T. Nygard. *Release It!* Second Edition, Pragmatic Bookshelf, 2018 —
  stability patterns (connection pools, bulkheads, thundering herd) for the
  failure modes of scale-out, cited by title.
- Google SRE. *Site Reliability Engineering*, Chapter on handling overload
  — saturation behavior of tiers and their dependencies, cited by title.
- Redis Ltd. *Redis documentation: replication and cluster sharding* — the
  scaling mechanics and limits of the canonical "stateless backing" store,
  cited by title.
