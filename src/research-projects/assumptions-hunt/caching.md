# Caching Assumptions: What "Just Cache It" Silently Promises

## Overview

Caching is the most commonly prescribed performance fix and the least commonly specified one. "Add a cache" is shorthand for a bundle of assumptions: the access pattern has locality, the workload is read-heavy, keeping the cache coherent is cheap, stale answers are acceptable, a TTL will keep staleness bounded, and yesterday's hit rate will persist. Each assumption fails in well-understood, reproducible ways — and the failure modes (stampedes, herds, silent staleness) are worse than the original uncached latency, because they arrive at scale, under load, during the exact events caching was meant to survive.

This chapter audits those assumptions with the collection's five-step pattern. Where an assumption failure has a dedicated page elsewhere in this repo (cache patterns, buffer pools, the "cache always improves" misconception), this chapter links rather than re-explains, and focuses on the *assumption* behind the pattern.

## Assumption 1: "Locality Exists"

### The taught rule

Caches work because accesses are localized in time and space: recently used items are reused, neighbors are likely.

### The hidden assumptions

- The workload is skewed, not uniform. A Zipf-like popularity distribution gives high hit rates; a uniformly random keyspace over a large corpus gives a hit rate near cache-size/keyspace-size — often useless.
- The access pattern is *stable* long enough for the cache to warm. Rotating workloads (time-partitioned data, per-tenant bursts) evict entries just before reuse.
- The data is chunked so that locality is physically realizable: cache lines, buffer-pool pages, Redis values all assume the useful data sits together.

### Counterexample

A metrics service caches the *latest* value per series and is queried round-robin across 50 million series with a cache sized for 5 million entries. Access is uniform over the keyspace, so the hit rate converges to about 10% — the cache adds a network hop and memory pressure while offloading only a tenth of the reads. The identical cache with a top-1000-heavy production distribution would hit 90%+. Same hardware, same code, opposite conclusion: the assumption that was violated is locality, not the cache.

### What changes when the assumption is removed

Measure the actual key-frequency distribution before caching; when it is flat, either partition the problem so each node's working set fits (sharding restores locality) or accept that the "cache" must instead be a store. Corrected statement: *a cache converts skew into speed; without skew it converts memory into overhead.*

### Consequences

The "why didn't the cache help?" incident review starts by plotting the key histogram — the cheapest diagnostic in performance engineering.

## Assumption 2: "The Workload Is Read-Heavy"

### The taught rule

Cache-aside: on read miss, load from the source, populate the cache, serve subsequent reads from it.

### The hidden assumptions

- Reads dominate writes. On a write-heavy dataset, cache-aside multiplies work: every write must invalidate (or update) the cache, and invalidations churn out entries that would have been read.
- The cached computation is more expensive than the cache round trip. Caching a value that costs a microsecond to compute, served over a 1 ms network call to Redis, is a slowdown with extra steps.
- Entries are reused. Per-request-unique data (request IDs, nonces) never hits.

### Counterexample

A rate limiter stores per-user counters in a cache-aside Redis layer. Each request is a write (increment), so the pattern is: read miss, load, increment, write back, invalidate on the next window — the "cache" turns one atomic increment into four round trips, and its hit rate is structurally near zero. Moving the counters into Redis's own atomic `INCR` (no application-side cache) is both simpler and faster. The lesson: the cache improved nothing because the workload assumption was false; the counter-case is documented in the misconceptions project as "cache always improves".

### What changes when the assumption is removed

Match strategy to workload: write-through or write-back for write-heavy data, no cache (or negative-cache only) for high-churn keys, and an explicit cost comparison (compute cost vs. cache round trip) before adding the layer. Corrected statement: *caching pays when reuse times cost; state the reuse assumption and check it with a hit-rate metric that is segmented by key class.*

### Consequences

In system-design interviews, "what's your cache hit rate target and why?" followed by "what's your write ratio?" tests exactly this; candidates who never segment by workload class are reciting, not designing.

## Assumption 3: "Coherence Is Free" (It Isn't — Even On One Machine)

### The taught rule

Multiple cores and multiple cache instances share data; the hardware (or the cache cluster) keeps everything consistent.

### The hidden assumptions

- Hardware cache coherence (MESI-class protocols) maintains consistency by moving or invalidating cache lines — costs paid in coherence traffic, not in instructions.
- Coherence is per-line and per-access: two independent hot variables that share one 64-byte line ping-pong the line between cores ("false sharing"), with no logic bug to blame.
- In distributed caches, coherence means invalidation or version checks — network traffic that scales with write rate and replica count.

### Counterexample

A worker pool where each thread increments its own counter — declared adjacently in the same struct, hence the same cache line. Throughput collapses versus one shared atomic counter times n, because every increment invalidates the other cores' copies. Padding each counter to its own line (alignas(64), `@Contended`, cache-line-aligned allocation) restores linear scaling. This is coherence's price made visible in a 10-line benchmark.

### What changes when the assumption is removed

Treat coherence traffic as a resource: pad hot per-thread data, batch cross-core (and cross-node) communication, and prefer shared-nothing designs whose "coherence" is the message queue. Corrected statement: *consistency between cache instances is purchased with traffic proportional to sharing frequency; design so that sharing frequency is low on purpose.*

### Consequences

"False sharing" is a standard senior performance interview; the buffer-pool chapter shows the same cost structure at the database layer, where the *page* is the coherence unit.

## Assumption 4: "Stale Data Is Tolerated" and "TTL Solves Consistency"

### The taught rule

Use TTLs; after expiry the cache refreshes, so staleness is bounded by the TTL.

### The hidden assumptions

- TTL bounds staleness in *time*, not in *versions*: a stale value written after the authoritative update can persist for a full TTL.
- Race conditions in the cache-aside pattern itself: the sequence "read miss → read DB → (writer updates DB and invalidates) → write stale value to cache" leaves the cache stale *immediately*, with the TTL guaranteeing only that it will not outlive the TTL.
- "Bounded staleness" is a per-key statement; consistency *between* keys (e.g., a user row and their permissions) is not addressed by per-key TTLs at all.

### Counterexample (the cache-aside write race)

| Time | Reader | Writer |
|------|--------|--------|
| t1 | cache miss on key k | |
| t2 | reads DB: value v1 | |
| t3 | | updates DB to v2, invalidates k |
| t4 | writes v1 to cache k | |
| t5 onward | every reader gets v1 until TTL | |

The invalidation at t3 was defeated by the reader's slow write at t4. The fix is to make cache writes version-aware (store a version/monotonic timestamp and refuse to overwrite newer values), to use short TTLs as a *repair* mechanism rather than the primary consistency tool, or to write through the cache so the cache write happens inside the authoritative update.

### What changes when the assumption is removed

Corrected statement: *a TTL is a staleness upper bound only in the absence of races; the full guarantee is "staleness ≤ TTL + worst-case race window" — so reason about the read-repair path, not just the timer.* For cross-key invariants, per-key TTLs are irrelevant by construction; you need versioned writes, transactions, or explicit invalidation coordination.

### Consequences

The interview escalation "cache invalidation is hard — why, concretely?" is exactly this table; candidates who answer with "TTLs" have restated the assumption rather than examined it.

## Assumption 5: "Hit Rates Transfer"

### The taught rule

The cache shows a 95% hit rate in staging; it will behave the same in production and for the new feature.

### The hidden assumptions

- Key popularity is stable across workloads, tenants, and time. Hit rate is a function of the *distribution*, not the cache.
- New features change distributions: a bulk-export endpoint or a new tenant with uniform access patterns can drop a shared cache's hit rate for everyone.
- A single aggregate hit-rate number hides class-level pathology: 95% overall can hide 99.9% on the catalog and 20% on per-user feeds.

### Counterexample

A shared Redis holds both product data (heavily reused) and per-session data (accessed twice ever). The aggregate hit rate looks healthy until session volume doubles; the sessions crowd out product entries, the product hit rate halves, and the database — which had been sized against the old load — falls over during the traffic shift. Nothing "broke"; one distribution changed and a single undifferentiated cache transmitted the change to an unrelated workload.

### What changes when the assumption is removed

Segment caches by key class (separate pools or namespaces with separate eviction budgets), alarm on per-class hit rates rather than aggregates, and re-measure after every workload-changing release. Corrected statement: *hit rate is a property of (workload, cache size, eviction policy); quote all three or the number is meaningless.*

### Consequences

The [cache patterns](../../sre/cache-patterns.md) page and the HLD caching-strategy chapter both drill capacity planning from distributions; this assumption is why "capacity plan from the aggregate" fails.

## Assumption 6: "The Cache Has No Downsides" (Stampedes, Herds, and Hidden Costs)

### The taught rule

A cache can only help — it stores computed answers and serves them faster.

### The hidden assumptions

- A miss is cheap and rare. When a hot key expires, *every* concurrent request misses simultaneously, and all of them hit the database at once: the cache stampede (a.k.a. dogpile).
- Recovery is gradual. After a restart or failover, an empty cache converts the entire read load into database load at once — the thundering-herd cousin.
- Storage and CPU are free: cached values must be serialized and deserialized, held in memory (or off-heap), and garbage-collected; large cached objects move the cost into the allocator and GC.
- Absences are cached too: without negative caching, repeated lookups of nonexistent keys bypass the cache entirely and hammer the source.

### Counterexample

A product page is read 10,000 times per second; its cached representation costs 50 ms to build and has a 60-second TTL. At expiry, requests arriving during the ~50 ms rebuild window (roughly 500 of them) all miss and all start rebuilding — a 500x read amplification on the database for one key, recurring every minute. Known defenses: request coalescing (a single-flight guard so one request rebuilds while others wait), probabilistic early expiration (Vattani, Chierichetti, and Lowenstein's VLDB 2015 analysis, deployed at Twitter — refresh a fraction of entries before expiry so the herd never forms), and soft TTLs with stale-while-revalidate serving.

### What changes when the assumption is removed

Corrected statement: *a cache is a load-amplification risk concentrated at miss and expiry events; engineer those events (coalescing, early probabilistic refresh, warmup, negative caching) or the cache's worst moment will be your database's worst moment.* The cache-patterns page in the SRE track catalogs the mitigations; the anti-pattern framing lives in the misconceptions project's "cache always improves" page.

### Consequences

"Design a cache that survives expiry of its hottest key" is a complete system-design interview in miniature: it touches locks, deduplication, probabilistic reasoning, and graceful degradation — all from one assumption.

## Interview Questions

1. **Your cache hit rate is 95%. Name three questions before you trust that number.** Segmented by key class? Under which distribution and cache size (the hit rate is a property of the workload, not the cache)? And how recently was it measured — did a feature change the key popularity since?
2. **Walk through the cache-aside race that a TTL does not fix.** Reader misses, reads old value; writer updates the database and invalidates; reader then writes the old value into the cache. Stale until TTL. Fix with versioned cache writes, write-through, or treating the TTL as repair rather than the primary mechanism.
3. **What is a cache stampede and give two defenses.** Concurrent misses on one hot (or expiring) key amplify load onto the source. Defenses: single-flight/request coalescing so only one request rebuilds, and probabilistic early expiration so expirations do not align; plus stale-while-revalidate serving during rebuilds.
4. **Two counters in one struct, one per thread, and the code scales worse than a single shared atomic. Why?** False sharing: both counters share a cache line, so coherence traffic serializes them. Pad to separate lines. It demonstrates that hardware coherence is a service you pay for per access, not a free guarantee.
5. **When is caching a rate-limit counter wrong, and what is right?** The workload is write-heavy per request, so cache-aside multiplies round trips and never hits. Use an atomic increment in the system of record (e.g., Redis `INCR`) — or accept that this data wants a store, not a cache.

## Key Takeaways

- A cache converts skew into speed: no locality, no win — measure the key distribution before believing a hit rate.
- Read-heavy is a load-bearing assumption; write-heavy cache-aside is a pessimization with extra network hops.
- Coherence costs traffic per share, on-chip (false sharing) and across nodes (invalidation); design sharing to be rare.
- TTLs bound staleness only in the absence of races; the cache-aside write race defeats invalidation, so version your cache writes or write through.
- Expiry and miss events concentrate load — coalesce, refresh probabilistically, warm up, and negative-cache; otherwise the cache's failure mode is the database's outage.
- Segment caches and their metrics by key class; aggregate hit rates transmit one workload's changes into another workload's incident.

## Cross-References

- [Cache patterns](../../sre/cache-patterns.md) — the mitigation catalog (coalescing, early expiration, negative caching).
- [Buffer pool](../../dbms/caching/buffer-pool.md) — the same assumptions at the database page level.
- [Redis](../../dbms/caching/redis.md) — the store-versus-cache boundary in practice.
- [Cache always improves](../misconceptions/cache-always-improves.md) — the misconception form of Assumption 6.
- [Caching strategy (HLD)](../../interview/system-design/hld/caching-strategy.md) — system-design application of these assumptions.
- [Complexity claims](complexity-claims.md) — sibling chapter: the memory-hierarchy assumptions behind locality.
- [Virtual memory and caching atlas](../connection-atlas/virtual-memory-caching.md) — how OS paging and caching connect.
- [Hash lookup is O(1)](../misconceptions/hash-lookup-o1.md) — adjacent assumption about constant-time structures.
