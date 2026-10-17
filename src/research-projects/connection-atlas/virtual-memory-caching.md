# Virtual Memory and Caching: One Hierarchy, Many Owners

## Overview

Demand paging, the Linux page cache, a database buffer pool, and a CDN edge cache look like four different subsystems from four different textbooks. Mechanically they are the *same system* instantiated at four layers of one cost hierarchy: each maintains a bounded amount of fast storage, fills it lazily on first use, evicts by a locality-driven policy when it overflows, and bets everything on the same empirical fact — programs reuse what they recently used. The TLB is just the smallest member of the same family.

The interesting part of this connection is not the sameness but the disagreement in the numbers. Cache-line misses and page faults differ by a factor of ~10⁶, and that single fact reshapes every policy choice: what is a rounding error at one layer is a catastrophe at the next. This page maps the shared machinery, then marks precisely where the "it's all just caching" analogy must stop.

## The Two Sides, Independently

**Demand paging and the page cache (OS).** Virtual memory gives each process a page table mapping virtual pages to physical frames; the valid bit says whether the frame is resident. On first touch of an invalid page the MMU raises a page fault and the kernel fetches the 4 KiB page from the file (or swap) — the page is *demand-filled*, never prefetched speculatively (beyond readahead, which is prefetching by another name). The Linux **page cache** is the kernel-wide cache of file blocks in RAM: two processes reading the same file share one copy, and a `read()` that hits the cache never touches the disk. When RAM fills, the kernel evicts pages — via a clock/second-chance approximation of LRU split into active/inactive lists — writing dirty pages back first. The **working set** (Denning, 1968) is the set of pages a process touches in a window Δt; performance is good as long as the sum of working sets fits in RAM.

**Hardware caches and the TLB (CPU).** L1/L2/L3 caches store 64-byte lines keyed by address, filled on miss, evicted by fixed policies (typically pseudo-LRU) that must run in silicon within a cycle budget. The TLB caches page-table entries (virtual→physical translations), because even *asking* the cache would cost a page-table walk; its miss penalty is a walk of up to several memory references.

**DB buffer pool and CDN (application-managed layers).** A database buffer pool is a user-space cache of 8–16 KiB pages between the executor and the file system, with its own LRU/clock variant, its own dirty-page flusher, and its own pinning (pages of an in-flight scan must not be evicted — an option the OS page cache does not offer). A CDN edge caches whole HTTP objects keyed by URL at the network's rim, with TTLs, revalidation, and eviction under disk pressure. Same loop: check → hit/miss → fetch from origin/next layer → insert → evict.

## The Shared Principle

**Every layer is a demand-filled cache keyed by identity, betting on locality, and evicting with a locality-approximating policy; they form one hierarchy in which each layer's fill source is the next layer's store.** The eviction theory (LRU's stack-distance optimality claims, the clock approximation's rationale, working-set sizing) transfers verbatim between layers; only the constants change. The TLB→L1→L2→L3→RAM→page-cache/SSD→disk→CDN-origin ladder is one object wearing seven uniforms.

A second shared principle: **every layer is an "LRU-shaped" approximation, because exact LRU needs bookkeeping that is too expensive at that layer's time budget** — hardware uses pseudo-LRU bits, the kernel uses clock hands and list placement, buffer pools use clocks or sampled LRU (Redis samples; Postgres uses a clock-sweep). The approximation pressure, not the specific list, is the transferable idea.

## Where the Analogy HOLDS and BREAKS

| Aspect | HOLDS | BREAKS |
|---|---|---|
| The loop (check/fill/evict) | Identical at all seven layers, with the same hit/miss vocabulary | Hardware policies are frozen at design time; kernel, DB, and CDN policies are adaptive and tunable |
| Eviction theory | Working set, LRU approximations, scan-resistance all transfer (DB "pin" ≈ OS "mlocked" page ≈ CDN "pinned object") | A DB *chooses* to bypass the OS page cache (double caching) precisely because generic eviction lacks application intent |
| Cost model | Monotone: higher layers are faster but smaller | Not a smooth gradient: L1→RAM is ~100×, RAM→SSD is ~10³–10⁴×, SSD→spindle ~10²×. Treat "one level down" uniformly and you misprice everything |
| Failure mode under overload | All layers degrade when the working set exceeds capacity | *Which* failure: hardware = gradual miss-rate rise; VM = **thrashing** (self-sustaining, system-wide); CDN = **stampede** on a single key (thundering herd). Different animals, different cures |
| Granularity | All are block-oriented | Line 64 B vs page 4 KiB vs CDN object 1 KiB–1 GiB; false sharing exists at line granularity and is meaningless at page granularity |

The "disk is not just slow RAM" break deserves its own paragraph, because it is the most consequential mis-analogy in systems teaching. RAM has uniform random access (~100 ns for any address); a spindle has ~10 ms *seeks* that depend on the previous request's location; even an SSD has asymmetric read/write and finite program-erase cycles. Consequences: swapping to disk turns a compute workload into a seek-dominated I/O workload (effective bandwidth of 4 KiB pages at 100 IOPS is 0.4 MB/s vs ~500 MB/s sequential — a 1000× collapse); `mmap` on a file you access randomly can page-fault-storm precisely because the hardware underneath is not RAM-shaped. The layered-cache *diagram* is right; the *latency continuum* it suggests is wrong — there is a cliff between RAM and persistent storage, not a slope.

## A Concrete Worked Example

**Thrashing vs stampede, with numbers.** Server: 4 GiB RAM, six services each with a 1 GiB working set — total 6 GiB > 4 GiB. Every service constantly touches pages that were just evicted: page-fault rate ~4,000 faults/s, each costing ~10 ms of SSD I/O (page 4 KiB). Effective useful bandwidth: 4,000 × 4 KiB ≈ 16 MB/s, while the SSD can do ~500 MB/s — the machine runs at 3% of its storage capability and CPU sits idle waiting. That is thrashing: self-sustaining, global, and cured only by reducing the summed working set (smaller services, more RAM, fewer co-tenants) or admitting the overload explicitly. Contrast the stampede: one hot cache key expires in a CDN/app cache; 5,000 concurrent requests miss simultaneously and all hit the origin (which costs 50 ms each) — the origin sees a 5,000-request burst, possibly dying. Cures are *local*, not global: request coalescing (single-flight), stale-while-revalidate, probabilistic early expiry. Same locality theory, different disease, different medicine — which is exactly why the analogy must be used carefully.

**Buffer pool sizing, with numbers.** Postgres on a 64 GiB box, hot data set 40 GiB. Setting `shared_buffers = 56 GiB` leaves 8 GiB for the OS page cache and doubles every read path (file must be copied into the DB pool from the page cache). Common production guidance keeps `shared_buffers` at ~25% of RAM and lets the kernel's page cache hold the cold-but-sometimes-read tail — you are deliberately splitting one logical cache across two managers with different eviction intents. The atlas-relevant point: the *decision* is an eviction-policy decision made across a boundary the analogy pretends does not exist.

## When This Connection Is Useful

- **Problem-solving heuristics.** (1) Any "why is it slow" question starts with locating the workload on the cost ladder and computing the miss rate × miss cost at each layer — one number per layer, take the max. (2) Capacity planning reduces to working-set arithmetic: sum of concurrent working sets must fit in the layer you are willing to pay for; if it cannot, choose *which* failure mode (thrash vs shed) explicitly. (3) Scan-resistant and pinning behaviors explain why full-table scans "poison" naive LRU caches at every layer.
- **Interview answers.** "Is a DB buffer pool just a cache?" is a seniority test: the strong answer is yes-and — same loop, same eviction theory, but application intent (pinning, write batching, O_DIRECT to avoid double caching) is why DBMSes re-implement what the OS already provides. "Why is mmap sometimes slower than read()?" is answered entirely by the fault-cost cliff and random-access patterns.
- **Engineering decisions.** Choose page size / block size / object size with the next layer's transfer unit in mind; choose eviction policy by the time budget of the layer (silicon: bits, kernel: clock hands, app: full LRU); treat swap as a *capacity* tool, not a performance tool, on latency-sensitive systems (or disable it and use explicit admission control).

## Interview Questions

1. List the seven layers of the demand-filled hierarchy from TLB to CDN origin. For each, name the key, the unit, the eviction policy, and the rough miss penalty. What does the pattern of penalties tell you about where optimization effort pays?
2. Why do nearly all real LRU implementations approximate LRU? Give the hardware and kernel reasons separately — they have different constraints.
3. A service's memory usage is stable but performance collapsed after a deployment that added 20% memory per request. Diagnose using working-set arithmetic, and state the two least-disruptive mitigations.
4. Thrashing, cache stampede, and retry storm are three overload deaths. Match each to its layer and to a one-line mechanism, and explain why the cures do not transfer between them.
5. Why does Postgres keep its own buffer pool instead of trusting the OS page cache, and when would you argue the opposite (trust the OS)?

## Key Takeaways

- Demand paging, page cache, TLB, CPU caches, buffer pools, and CDNs are one hierarchy of demand-filled, locality-betting, LRU-approximating caches; the eviction *theory* transfers fully.
- The cost gradient is a cliff ladder, not a slope: ~10², ~10³–10⁴×, ~10²× between adjacent storage layers; policy choices are driven by these constants.
- Working set is the universal sizing tool: sum of concurrent working sets vs capacity predicts health at every layer.
- Thrashing (global, self-sustaining) and stampede (local, burst) are distinct overload diseases of the same theory; cure one and you may cause the other.
- "The disk is slow RAM" is exactly wrong in the way that matters: seek asymmetry and fault costs turn random access patterns into order-of-magnitude collapses, which is why application intent (pinning, O_DIRECT, readahead) keeps leaking back into layers the theory says should be generic.

## Cross-References

- [../../os/virtual-memory/demand-paging.md](../../os/virtual-memory/demand-paging.md) — Demand Paging — fault handling mechanics behind the OS side.
- [../../os/virtual-memory/working-set.md](../../os/virtual-memory/working-set.md) — Working Set — Denning's model in its canonical OS treatment.
- [../../os/virtual-memory/clock.md](../../os/virtual-memory/clock.md) — Clock Page Replacement — the second-chance approximation reused across layers.
- [../../os/memory/tlb.md](../../os/memory/tlb.md) — TLB — the smallest cache in the hierarchy.
- [../../arch/memory-hierarchy/levels.md](../../arch/memory-hierarchy/levels.md) — Memory Hierarchy Levels — L1/L2/L3 numbers and policies.
- [../../dbms/caching/buffer-pool.md](../../dbms/caching/buffer-pool.md) — Buffer Pool — the DBMS's user-space re-implementation of the page cache.
- [../../dbms/storage/buffer-management.md](../../dbms/storage/buffer-management.md) — Buffer Management — pinning, flushing, and eviction inside the engine.
- [../../networks/cdn/how-it-works.md](../../networks/cdn/how-it-works.md) — How CDNs Work — the network-rim member of the family.
- [../followup-tree/virtual-memory.md](../followup-tree/virtual-memory.md) — Virtual Memory Follow-up Tree — question-escalation chains for this material.
- [../why-not-handbook/caching-distributed.md](../why-not-handbook/caching-distributed.md) — Caching vs Distributed Coordination — when to stop caching and start coordinating.
- [../../interview/system-design/latency-numbers.md](../../interview/system-design/latency-numbers.md) — Latency Numbers Every Programmer Should Know — the constant table this page leans on.
