# Cache Coherence and Consistency: MESI to CDN Purge

## Overview

A four-core CPU, a fleet of web servers caching database results, and a CDN with 200 edge PoPs holding your stylesheet have the same skeleton: many replicas of one truth, where the truth changes. Each needs a protocol that answers one question — *when a write happens, what happens to every other copy?* Hardware answers with MESI and nanosecond invalidation messages on a shared interconnect. Distributed systems answer with invalidation broadcasts, TTLs, purges, and quorum reads, over links with millisecond latency and partial failure. The principles transfer almost verbatim; the failure modes are separated by five to eight orders of magnitude in timing assumptions.

This page walks the MESI state machine on a concrete two-core example, then shows the same state machine expressed as cache invalidation between app servers and as a CDN purge, and marks exactly where the analogy stops being safe — usually the moment you assume the bus is atomic.

## The Concepts, Independently

**CPU cache coherence.** Each core has private L1/L2 caches; all cores share one physical memory. A cache line (typically 64 bytes) can be replicated across cores, and the hardware maintains a per-line invariant: all cores observe a single agreed value sequence per address (coherence is per-line; the cross-address order story is *memory consistency*, a different contract). MESI gives each line in each cache one of four states — **M**odified (this cache holds the only valid copy, and it is dirty), **E**xclusive (only valid copy, clean), **S**hared (clean copies may exist in many caches), **I**nvalid (no copy). Writes require exclusivity: writing to an S line broadcasts a read-invalidate that demotes every other copy to I. Protocol messages ride the interconnect, either a snooping bus (every cache observes every transaction) or a directory (a point of truth routes messages) — see [../../arch/memory-hierarchy/coherence.md](../../arch/memory-hierarchy/coherence.md), [../../arch/memory-hierarchy/mesi.md](../../arch/memory-hierarchy/mesi.md), and [../../arch/cpu/cache-coherence.md](../../arch/cpu/cache-coherence.md).

**Distributed cache invalidation.** A web tier of N nodes caches query results in front of a database. A write on node A must ensure nodes B..N do not serve the old value beyond the staleness budget. The classic mechanisms map one-to-one onto coherence: *invalidation* (publish "key K is dead" on a bus like Redis pub/sub; holders evict and re-read — the S→I transition), *update/propagation* (push the new value — the bus-write that supplies data), or * TTL (time-based expiry — a probabilistic substitute for an invalidation message). Write-through vs write-back reappears too: whether the database is updated synchronously with the cache write (write-through) or the cache holds dirty state (write-back), with write-back you are maintaining an M state in a fleet.

**CDN purge.** Edge PoPs cache origin responses. On deploy you issue a purge; the provider propagates invalidation across PoPs in seconds-to-minutes. In practice most teams avoid relying on purge latency at all by content-hashing asset filenames (`app.3f9a2c.css` + `Cache-Control: immutable`), which makes invalidation unnecessary — the same trick Git uses (see [./git-cas.md](./git-cas.md)). Purge remains the fallback for HTML and API responses whose URLs cannot change.

**Replicated data consistency.** The database itself, when replicated, faces the same problem one level down: primaries, secondaries, quorum reads and read-repair are directory-like protocols that decide which copy answers and how stale answers may be ([../../distributed/fundamentals/consistency.md](../../distributed/fundamentals/consistency.md)). The consistency model (linearizable, sequential, eventual) plays the role of the coherence contract — but is chosen, not wired into silicon.

## The Shared Principle

**Replicas of one truth plus a write-propagation protocol: writes must either update or invalidate every stale copy, and the protocol is the implementation of a stated consistency contract.** Each system is a state machine per unit (line, cache key, URL, row): read-shared states are cheap and parallel; writes force exclusivity via invalidation. The design space is identical in shape — invalidate vs update, push vs pull, write-through vs write-back, snooping vs directory — and the contract you promise (coherence model, staleness budget, consistency model) determines which point in that space you must implement.

The corollary that makes this worth naming: **invalidation traffic is the price of writes, and it scales with the fan-out of readers, not with the write itself.** A write to a line shared by 16 cores costs 15 invalidation messages; a purge to a CDN costs propagation to every PoP holding the object; an invalidation broadcast in a 40-node web tier reaches all 40. The engineering reflex — reduce fan-out, or make copies cheap to re-derive — is the same at every scale.

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS (MESI ↔ distributed caches) | BREAKS |
|---|---|---|
| Per-unit state machine (M/E/S/I ↔ valid/stale/absent) | Same transitions: exclusive-on-write, demote-others, supply-on-miss | Hardware states are per 64-byte line and enforced by silicon; distributed "stale" is a gradient (TTL windows), not a discrete state |
| Invalidation vs update on write | Both worlds choose; invalidate wins when writes are rarer than re-reads | Hardware can afford update protocols on a local bus; WAN update fan-out is usually unaffordable, so invalidation/TTL dominate |
| Snooping bus ↔ pub/sub invalidation | Same mental model: everyone hears every transaction | The bus is **atomic**: all cores see each transaction in the same instant order, guaranteed. Pub/sub is at-most-once-ish, unordered across channels, and lossy — distributed invalidation needs acks/retries or TTL backstops |
| Directory ↔ coordinator/quorum | Both tame fan-out by routing through a point of truth | Hardware directories never fail partially; a "directory" at 50 ms RTT must itself be replicated (consensus), importing the whole distributed-consistency toolchain |
| False sharing ↔ hot keys | Both are performance cliffs invisible in code review | False sharing is diagnosed and fixed by padding/aligning (see [../../os/advanced/false-sharing.md](../../os/advanced/false-sharing.md)); a hot distributed key needs sharding or local mitigation — different fixes for the same shape |
| Timing constants | The structure transfers | The numbers do not: L1 ≈ 1 ns, cross-core line transfer ≈ 40–100 ns, same-DC cache invalidation RTT ≈ 0.5–2 ms (50,000× the L1), CDN purge propagation ≈ seconds-to-minutes. Reasoning about coherence *performance* with distributed numbers — or vice versa — produces confident nonsense |

The deepest break: **hardware treats disagreement as impossibility; distributed systems treat it as the common case.** A core that fails to snoop deadlocks the bus, so the protocol's atomicity is enforced by physics and the interconnect is engineered never to partition. Distributed replicas *do* partition, so coherence is weakened into staleness budgets and eventual consistency, and correctness under partition becomes a modeling decision (CAP) rather than a wiring guarantee. That is why "treat the Redis cache like an L2" fails the moment two nodes write the same key during a network partition — MESI has no equivalent question to even ask.

## A Concrete Worked Example

**MESI walk: two cores, one line.** Line `X` starts in memory; caches A and B are empty.

```text
Step  Action                        A     B     Bus traffic
----  ----------------------------  ----  ----  ---------------------------
1     A reads X                     S     I     BusRead  (memory supplies)
2     B reads X                     S     S     BusRead  (memory or A supplies)
3     A writes X (X=42)             M     I     BusRdX   (read-invalidate)
4     B reads X                     S     S     BusRead  (A supplies, writes back)
5     B writes X (X=7)              I     M     BusRdX   (read-invalidate)
```

Walk the transitions: step 3 requires A to own the line exclusively, so B's copy is invalidated; step 4 is the expensive, telling one — B's read misses, A supplies the data from its Modified state and both end Shared. Step 5 hands ownership back, another broadcast. Six state transitions for three memory operations, all invisible in source code.

**Now make it false sharing.** Suppose instead that A loops writing counter `i` and B loops writing counter `j`, and both variables sit on the same 64-byte line. Every write by either core invalidates the other's copy, so every access is a miss and an inter-core transfer: N writes cost ~2N coherence transactions instead of ~0. The same code with the counters on separate lines (padded) shows 10–100× higher throughput on typical hardware — the cost was pure protocol traffic, not memory bandwidth ([../../os/advanced/false-sharing.md](../../os/advanced/false-sharing.md)).

**The distributed mirror.** A fleet caches the site CSS at the CDN with a 1-hour TTL; a deploy changes the stylesheet. Purge at t=0; propagation completes by t≈30 s. In between, PoPs that missed the purge serve old CSS — an M-state write whose invalidation message has not landed. If a purge request is dropped and nobody retries, the "invalid" copy lives until TTL expiry: the distributed system's fallback is *time*, where MESI's fallback is *physics*. The robust fix is the content-hashed URL: every deploy is a new key, invalidation becomes unnecessary, and the old key simply expires — an append-only, content-addressed asset store, i.e., Git's answer again ([./git-cas.md](./git-cas.md), [../../networks/cdn/how-it-works.md](../../networks/cdn/how-it-works.md)).

## When This Connection Is Useful

- **Debugging performance surprises.** Unexplained 10× slowdowns in multithreaded code: check for false sharing before blaming the algorithm. Unexplained stale content after deploy: check purge propagation and TTLs before blaming the CDN. Both are "invalidation traffic/staleness" diagnoses, and knowing the state machine tells you what to measure (coherence misses / cache-miss counters; purge status and edge hit ratio).
- **Interview escalation.** "Two threads increment adjacent counters — why slow?" → false sharing → MESI → "how would you fix it?" is a complete seniority ladder. The distributed follow-up — "you have 40 app servers with a local cache; how do writes stay consistent?" — is answered with the same vocabulary (invalidation, update, TTL, directory), which is exactly what makes the answer sound senior rather than memorized.
- **Engineering decisions.** Choose invalidation vs update vs TTL by write ratio and staleness budget, not by fashion. Prefer content-addressed keys where possible (invalidation becomes GC, not correctness). Beware caching with write-back semantics in a fleet (M-state in RAM): it trades correctness risk for speed in a domain with no atomic bus — see the caching deep-dive in [../why-not-handbook/caching-distributed.md](../why-not-handbook/caching-distributed.md) and the caching lens in [./virtual-memory-caching.md](./virtual-memory-caching.md), and the claim "more cache is always better" dismantled in [../misconceptions/cache-always-improves.md](../misconceptions/cache-always-improves.md).

## Interview Questions

1. Walk the MESI transitions for: core A reads X, core B reads X, core A writes X, core B writes X. Which steps generate bus traffic, and what state does the line end in for each cache?
2. What is false sharing at the protocol level (not the "shared cache line" slogan)? Why does padding two counters into separate lines recover 10–100× throughput, and how would you confirm the diagnosis with a performance counter?
3. Your CDN serves stale CSS for up to an hour after a deploy. Explain the failure as a coherence-protocol event, and give two fixes with different trade-offs — one that removes the need for invalidation, one that shortens staleness.
4. Why is "the Redis cache is just an L2 for the database" a broken analogy under partition, in terms of what MESI guarantees that pub/sub invalidation does not?
5. Compare snooping and directory coherence protocols, and match each to a distributed-systems counterpart. Why does every multi-core design above a few dozen cores switch to directories?

## Key Takeaways

- One principle spans silicon and the datacenter: replicas of one truth + a write-propagation protocol that demotes or refreshes stale copies; the protocol implements a promised consistency contract.
- MESI's state machine (M/E/S/I per line) is a useful mental model for cache keys, CDN objects, and replicated rows: reads parallelize, writes demand exclusivity, and invalidation traffic scales with reader fan-out.
- The analogy transfers structure, never constants: 1 ns vs 0.5 ms vs minutes is the whole difference between "enforced by physics" and "enforced by TTLs and retries."
- False sharing is the hardware-side surprise; stale-after-purge is the distributed twin. Both are protocol-traffic or propagation problems invisible at the source level.
- Content addressing (hashed URLs, immutable caching) converts invalidation from a correctness mechanism into garbage collection — the single most transferable trick between Git, CDNs, and cache fleets.

## Cross-References

- [../../arch/memory-hierarchy/mesi.md](../../arch/memory-hierarchy/mesi.md) — MESI Protocol — the full state machine and its variants (MOESI, MESIF).
- [../../arch/memory-hierarchy/coherence.md](../../arch/memory-hierarchy/coherence.md) — Cache Coherence — snooping vs directory protocols in depth.
- [../../arch/cpu/cache-coherence.md](../../arch/cpu/cache-coherence.md) — CPU Cache Coherence — the architecture-course treatment of the same mechanism.
- [../../arch/memory-hierarchy/README.md](../../arch/memory-hierarchy/README.md) — Memory Hierarchy — the levels and latencies behind the numbers above.
- [../../os/advanced/false-sharing.md](../../os/advanced/false-sharing.md) — False Sharing — detection, padding, and measurement.
- [../../distributed/fundamentals/consistency.md](../../distributed/fundamentals/consistency.md) — Consistency Models — where the coherence contract goes when replicas partition.
- [../../networks/cdn/how-it-works.md](../../networks/cdn/how-it-works.md) — How CDNs Work — edge caching, purge, and immutable assets.
- [./virtual-memory-caching.md](./virtual-memory-caching.md) — Virtual Memory and Caching — the demand-filled hierarchy this protocol keeps coherent.
- [./git-cas.md](./git-cas.md) — Git as Content-Addressable Storage — content addressing as the invalidation-elimination strategy.
- [../misconceptions/cache-always-improves.md](../misconceptions/cache-always-improves.md) — Misconception: Cache Always Improves — when replica cost and staleness beat the hit ratio.
- [../why-not-handbook/caching-distributed.md](../why-not-handbook/caching-distributed.md) — Caching vs Distributed Coordination — the decision-level comparison of cache-side and consensus-side answers.
- Sorin, D., Hill, M., & Wood, D., *A Primer on Memory Consistency and Cache Coherence*, 2nd ed. (Morgan & Claypool, 2020) — the standard reference for coherence and consistency definitions.
- Hennessy, J. & Patterson, D., *Computer Architecture: A Quantitative Approach*, 6th ed., ch. 2 (cache coherence and false sharing measurements).
