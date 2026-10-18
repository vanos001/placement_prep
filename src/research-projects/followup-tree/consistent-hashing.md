# Follow-up Tree: Consistent Hashing

## Overview

"What is consistent hashing, and why does adding a cache node cause an outage without it?" is the distributed-systems opener that escalates from a clever ring picture into the load-balancing and partitioning design space, and interviewers use it to test whether a candidate can reason about *reassignment cost* — the price systems pay when membership changes. The ladder here runs from the mod-N problem that motivates the scheme (why `hash(key) % N` throws away most of the cache on any topology change), through ring mechanics and virtual nodes (the fix, and the uneven-distribution problem the naive ring creates), into the production realities of hot keys, hit-ratio cliffs, and bounded-load placement, and ends at the alternatives — rendezvous hashing, jump consistent hash, and range partitioning — that a senior candidate must weigh, not just name. The thread tying every rung together is *what happens to K keys when the cluster changes from N to N+1 nodes*: consistent hashing's claim is that only K/N keys move, and every follow-up either asks how that claim is achieved, when it is not enough, or what structure must be maintained to deliver it. This chain stays at the hashing-and-placement mechanism; the request-routing layer (algorithms, health checks, affinity) is owned by [Load Balancing](./load-balancing.md), and the general partitioning map is the atlas page [Load Balancing & Partitioning](../connection-atlas/load-balancing-partitioning.md). The book-level references are [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md), [Rendezvous Hashing](../../distributed/advanced/rendezvous-hashing.md), and [Jump Consistent Hashing](../../distributed/advanced/jump-consistent-hashing.md); the primary sources are the Karger et al. ring papers (1997, cited by title), the [Jump Hash paper](https://arxiv.org/abs/1406.2294) (Lamping & Veach), and the [Bounded-Load paper](https://arxiv.org/abs/1608.01350) (Fan, Lata & Mitzenmacher). Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"You have 10 cache servers and a fleet of clients hashing keys with `hash(key) % 10`. What happens when you add an 11th server?"**

The expected core answer: modulo hashing scrambles nearly everything. Changing the modulus from 10 to 11 changes the bucket of every key whose `hash(key) % 11 ≠ hash(key) % 10` — in practice roughly 90% of keys — so one added node invalidates nine nodes' worth of cache, and the origin sees a miss storm while all clients refill. Consistent hashing fixes this by hashing *both* keys and nodes onto the same hash space: imagine a circle (0 to 2^128); a key belongs to the first node found clockwise from its hash. When a node joins, only the keys between its position and its clockwise neighbor remap — on expectation K/N of the keys, not all of them. Removal is symmetric: only that node's keys move to its successor.

A weak answer says "consistent hashing spreads keys evenly" — a load-balancing claim, missing the actual property, which is *minimal disruption under membership change*. The strong answer states the reassignment bound as the definition, walks the ring lookup, and volunteers the first problem the picture hides: with few nodes, uniform hashing of *nodes* is not uniform *ownership* — one node's arc can easily be twice another's. The follow-up that escalates: **"Hash functions are random. Why does the ring distribute load badly, and what fixes it?"** — which moves the ladder from scheme to mechanism.

## Level 2: Virtual Nodes and the Distribution Problem

**What it tests:** whether the ring is a mechanism whose failure modes (skew, metadata, heterogeneous machines) you can reason about — or a picture that works in slides.

**Weak answer:** "Place nodes on the ring and route clockwise" — no awareness that a handful of random points gives wildly uneven arcs, no concept of virtual nodes, no answer for nodes with different capacities.

**Strong answer:** explains that with N physical nodes the ownership arcs are N random spacings, and the largest arc dominates: load imbalance scales like log N (for 10 nodes, a node can easily own several times the average share), and the standard fix is *virtual nodes* — each physical machine gets 100–1000 tokens (positions) on the ring, so ownership is the sum of many small arcs and the law of large numbers evens the load; vnode count also becomes the weight knob — a 2x-capacity machine gets 2x tokens.

**Escalation trigger:** "Where does the ring live? Every client needs to compute it — what is the metadata cost, and what happens when it is stale?"

**Answer.** The ring is *distributed state*, and its management is the hidden cost of the scheme. Every client (or a metadata service clients poll) needs the full token map: nodes' positions, vnode counts, and health. The costs: memory for the map (thousands of tokens), a propagation path for membership changes (gossip, a coordination service, or a control plane), and a consistency window during which clients disagree about ownership — a key sent to the old owner after a rebalance costs one miss per moved key until clients converge. The senior observations: first, consistent hashing does not eliminate rebalancing work, it *bounds the blast radius* — K/N keys still move (new node pulls, or old pushes; caches just miss and refill; storage runs anti-entropy then flips the range). Second, stale maps degrade *gracefully but measurably*: a client on an old map is just a client with slightly wrong `hash % N` — bounded wrongness, unlike modulo's unbounded wrongness. Third, this is why Dynamo and Cassandra made token management explicit (fixed tokens, then vnodes, then weight-aware schemes) — the ring's shape is an operational surface, not an implementation detail.

The design twist: *the same ring serves affinity and partitioning* — load balancers use it for session affinity with minimal reassignment, storage systems for partition ownership with minimal data movement; the property is identical, and a moved key costs either a cache miss or a data copy. The follow-up that escalates: **"The map is perfect and the arcs are even. Why is one node still burning hot?"**

## Level 3: Hot Keys, Bounded Loads, and Rebalance Storms

**What it tests:** the operational rung — why uniform keyspace does not mean uniform request load, what bounded-load hashing adds, and how topology changes interact with caches (the hit-ratio cliff).

**Weak answer:** "Consistent hashing handles hot keys" — it does not; a single key hashes to exactly one node no matter how clever the ring, and a celebrity key's QPS arrives there undivided.

**Strong answer:** separates *keyspace balance* (vnodes solve) from *request-load balance* (unsolved by hashing — a skewed key distribution concentrates traffic), then names the countermeasures: split hot keys across replicas with per-request replica selection, add a small client-side cache for the hottest keys, or use *bounded-load consistent hashing* — each node accepts at most (1+ε) times its fair share, overflowing the rest clockwise, which smooths skew at the price of more reassignment.

**Escalation trigger:** "A flash-crowd key (one celebrity object) gets 200k requests per second to one cache node. Design the fix without moving all keys."

**Answer.** Hashing cannot split a key; only the *key's replicas* can share its load. The layered answer: replicate the hot key on R nodes (a ring with replication factor R already provides them — the next R distinct nodes clockwise) and have clients pick among the R replicas randomly or by least-load, turning one hot node into R warm ones. If the key set is unpredictable, bounded-load placement ([Fan, Lata & Mitzenmacher](https://arxiv.org/abs/1608.01350)) generalizes the trick at key level: each node refuses work beyond (1+ε) of its share, spilling to neighbors — Google's Maglev-style tables implement the same idea for load balancers (Maglev, cited by title), and the cost is bounded: keys beyond the cap move on topology change, so ε trades evenness for disruption. The second half of the rung is the rebalance storm: when the ring changes, moved keys miss — and if 5% of keys remap, a cache with a 95% hit rate sees *all* of its traffic's misses concentrated in a burst, because every client refills simultaneously; the mitigations are staggering the switch (clients adopt the new map in random waves), warming the new node before it takes traffic (a join/leaving state machine, not a binary membership flip), and keeping ring identity *stable* — vnodes over ephemeral shard ids — because identity that survives restarts means fewer moves.

The design twist: *hit ratio is a function of topology stability* — the mathematical guarantee "only K/N keys move" translates directly into "the miss storm is K/N of keyspace," so sizing N (more, smaller nodes) makes each change proportionally cheaper but the map proportionally bigger: metadata cost and disruption cost pull in opposite directions. The follow-up that escalates: **"Rendezvous hashing and jump hash also promise minimal reassignment. When are they better than a ring?"**

## Level 4: Alternatives — Rendezvous, Jump Hash, and the Judgment Call

**What it tests:** the expert rung — the design space beyond the ring, each scheme's structural cost (per-key computation, metadata, weights), and the ability to *choose* with a workload in hand rather than recite a favorite.

**Weak answer:** names the alternatives as trivia ("there's also rendezvous and jump hash") with no cost model — cannot say which needs metadata, which supports weights, which scales to hundreds of nodes.

**Strong answer:** prices each scheme. *Rendezvous (highest-random-weight) hashing:* for a key, compute `hash(key, node)` for *every* node and pick the maximum — zero shared metadata (each client needs only the node list), perfect minimal disruption, but O(N) work per lookup, so it shines for small N (tens) and dies at thousands; weights fold in naturally. *Jump consistent hash:* a ~10-line algorithm computing `hash(key, num_buckets)` with O(ln N) time and *no per-node state at all* — but only for uniform-weight integer buckets 0..N-1, and bucket numbering is not stable for arbitrary identity ([Lamping & Veach](https://arxiv.org/abs/1406.2294) built it for Google's storage backends). *Ring with vnodes:* O(log T) lookup over a token map that must be maintained, but supports weights, replication (walk clockwise for R distinct owners), and data identity that survives node restarts.

**Escalation trigger:** "Choose a placement scheme for: (a) 8 cache proxies behind a load balancer, (b) a 500-node Cassandra-style store with heterogeneous hardware, (c) a client-side library sharding keys over a dynamic worker pool with thousands of slots. Justify each."

**Answer.** (a) *Rendezvous:* N=8 makes the O(N) per-key cost trivial, there is no metadata service to run, weights are one line, and disruption is minimal — the ring's machinery buys nothing at this scale. (b) *Ring with vnodes:* replication needs the clockwise walk anyway; heterogeneous hardware needs the weight knob; token identity must survive node restarts, which jump hash's positional buckets do not provide; the token map is worth operating at 500 nodes. (c) *Jump hash:* the worker pool is a numbered set of identical slots with no per-slot identity or weight, membership changes constantly, and a client-side library cannot afford a metadata service — O(ln N) compute with zero state is the design point; the sacrifice (no weights, no stable slot identity) matches the workload. The judgment frame that earns the top rung: ask three questions — *how many nodes* (sets the per-lookup compute budget), *do owners need identity or just positions* (storage wants identity; ephemeral workers want positions), and *who can own the metadata* (a control plane buys the ring's flexibility; none means rendezvous or jump). The sentence that ends the chain well: every scheme here solves the same problem — *minimal disruption* — and differs only in where it spends structure: compute per key (rendezvous), metadata (ring), or flexibility (jump hash); pick the currency you can afford.

## How to Approach Unfamiliar Variations

The template for hashing variations — "weighted consistent hashing," "hot shards in a sharded store," "why did hit rate drop after we added a node":

1. **Reduce every scheme to its reassignment and cost profile.** Mod-N moves ~all keys; the ring moves K/N but needs a token map; rendezvous moves K/N with O(N) compute and no map; jump hash moves K/N with O(ln N) and no identity. Any proposed variant is a point in this space — place it before judging it.
2. **Separate keyspace balance from request-load balance.** Uniform ownership is not uniform traffic; hot keys need replication, bounded loads, or client-side caching — hashing alone never fixes a skewed key popularity distribution.
3. **Ask what a membership change costs *at the application*.** For caches: a miss storm sized by the remapped fraction, staggerable in time. For storage: data movement sized the same, plus range-flip sequencing. The scheme sets the size; the rollout protocol sets the pain.
4. **Check who computes and who stores the map.** Client-side hashing needs either a cheap function (jump) or a gossipable map (ring); metadata is often the deciding constraint, and the first question to ask of any proposal.

## Interview Questions

**Q: Your cache fleet's hit rate drops sharply every time an autoscaler adds a node, even with consistent hashing. Why, and what do you tune?**
A: The remapped fraction (K/N of keyspace) all misses at once: every client refills those keys in the same burst, so the origin sees a synchronized miss storm, not the steady-state miss rate. Tune three things: vnode count and node identity so fewer tokens move (stable identities, not ephemeral pod IPs), the rollout (staggered map adoption, warming the new node before full traffic), and optionally bounded-load placement so the new node absorbs share gradually.

**Q: Why do 100 virtual nodes per machine even out load, and what breaks if you use 10,000?**
A: Ownership becomes the sum of 100 random arc samples instead of 1, so relative variance drops with the square root of the count — imbalance shrinks toward the mean, and vnode count becomes a capacity weight. At 10,000 per node the token map balloons (N × 10,000 entries to gossip, store, and search), rebalance churn grows, and lookup cost rises — smoothing past diminishing returns, now paid in metadata and convergence time.

**Q: A key belonging to one celebrity account receives 40% of total traffic. The consistent-hashing ring is perfectly balanced. What do you do?**
A: Nothing about the ring — hashing cannot split one key. Replicate that key's data on the next R distinct owners clockwise and have clients choose among replicas (random or least-loaded), or add a bounded-load tier that spills overflow requests to neighbors, or short-circuit the hottest keys in a small client-side cache. The ring balance fixes *which* node owns the key; the hot key needs *load* mechanisms one layer up.

**Q: When would you deliberately choose rendezvous hashing over a consistent-hash ring?**
A: Small, stable node sets with no metadata infrastructure: per-key O(N) cost is irrelevant at tens of nodes, clients need only the node list, weights fold in naturally, and disruption is minimal without a token service. The moment N grows into the hundreds (per-lookup compute), or owners need persistent identity and replication walks (token map pays off), or the fleet is thousands of weightless slots (jump hash wins), rendezvous gives way.

## Key Takeaways

- Consistent hashing is defined by *minimal disruption*: hashing keys and nodes into one space means only K/N keys remap on membership change — mod-N moves nearly all of them.
- Naive rings are lopsided at small N; virtual nodes average many small arcs, even the load, and double as a capacity-weight knob.
- The ring is distributed state: its map, propagation, and staleness windows are the hidden operational cost, and identity that survives restarts is what keeps rebalancing cheap.
- Hashing balances keyspace, not request load — hot keys need replication, bounded-load placement, or client-side caching; a hit-ratio cliff after topology change is a remap storm to be staggered.
- Rendezvous (O(N), no metadata), jump hash (O(ln N), no identity), and vnodes (metadata, weights, replication) spend the same guarantee in different currencies — choose by node count, identity needs, and who can run the map.

## Cross-References

- [Load Balancing](./load-balancing.md) — the sibling chain: where consistent hashing sits among scheduling algorithms, health checks, and affinity.
- [Hash Tables](./hash-tables.md) — the foundation ladder whose final rung (distributed lookup) this chain deepens.
- [Load Balancing & Partitioning](../connection-atlas/load-balancing-partitioning.md) — the atlas map joining request routing and data placement.
- [Message Queues](./message-queues.md) — partition assignment in log-based systems, the consumer-side cousin of node ownership.
- [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) — the book-level treatment of rings, vnodes, and partition assignment.
- [Rendezvous Hashing](../../distributed/advanced/rendezvous-hashing.md) and [Jump Consistent Hashing](../../distributed/advanced/jump-consistent-hashing.md) — the alternative schemes priced in Level 4.
- [Jump Consistent Hash paper](https://arxiv.org/abs/1406.2294) (Lamping & Veach, 2014) — the stateless O(ln N) algorithm.
- [Bounded-Load Consistent Hashing paper](https://arxiv.org/abs/1608.01350) (Fan, Lata & Mitzenmacher) — the cap-and-overflow scheme that smooths hot keys.
- Karger et al. (1997) and the Amazon Dynamo paper (DeCandia et al., 2007) — the original ring and its production form; cited by title, no verified public link this session.
