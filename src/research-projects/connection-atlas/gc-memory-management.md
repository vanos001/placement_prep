# Garbage Collection and Memory Management: Defining Death

## Overview

Every memory-managed system must answer one question: when is an object dead? The surprising part is that the major answers — tracing, reference counting, generations, leases — are all *approximations computed from incomplete information*, and the differences between them are differences in which error they prefer: retaining garbage (leak) or freeing something live (correctness catastrophe). The same question reappears, almost verbatim, in distributed systems: when is a session, a lock, or a temporary file dead? There the answer is a lease — a time-based approximation — and its failure mode (expiring a live holder) is the distributed twin of a GC bug.

This page connects the worlds by their shared graph-theoretic core (reachability from roots), their shared locality bet (generations ↔ working sets), their shared SLO pressure (stop-the-world pauses ↔ tail latency), and then maps exactly where the analogy collapses: a collector can stop the world; a distributed system cannot.

## The Concepts, Independently

**Tracing GC.** The collector maintains a root set — stacks, registers, globals, JNI/handles — and computes *reachability*: mark phase is literally a BFS/DFS over the pointer graph from the roots (the same traversal as [../../dsa/README.md](../../dsa/README.md)'s graph unit); sweep or compact then reclaims the unmarked. Reachability is a **conservative** definition of death: an object the program will never use again but that is still reachable (a static cache, a stale listener) is retained — tracing GC can leak by loitering, but it never frees live data. Cycles are collected correctly, because reachability doesn't care how objects reference each other if no root reaches them.

**Reference counting.** Each object stores a count; aliasing increments, drops decrement; zero means free — immediately and incrementally. It is an **aggressive** definition: zero references ⇒ dead. Costs: counter traffic on every pointer assignment (and atomic traffic in concurrent settings), plus the classic flaw — a cycle never reaches zero (two objects pointing at each other are each "referenced" forever). Python ships a tracing GC alongside its refcounting precisely to collect cycles: a real-world admission that the two definitions are complements.

**Generations and working sets.** The generational hypothesis is an empirical claim: *most objects die young* (commonly measured well above 90% in allocation-heavy workloads — an empirical rule, not a law). So the heap is split young/old; minor collections scan only the young generation plus a *remembered set* of old→young pointers. Denning's working-set model ([../../os/virtual-memory/working-set.md](../../os/virtual-memory/working-set.md)) makes the same locality bet for paging: a process runs well iff its Δt-window touch set fits in RAM. Both are locality claims converted into *bounded work*: scan the hot set, not the world.

**Pauses, SLOs, and the distributed answer.** A stop-the-world (STW) pause stops all mutators; for a service with a 100 ms p99 SLO, a 1 s full-GC pause *is* an SLO violation with a fingerprint (periodic latency spikes at heap-pressure intervals). Modern collectors attack it by making most work concurrent: G1 (pause target via `-XX:MaxGCPauseMillis`, default 200 ms), ZGC and Shenandoah (sub-ms pauses via concurrent marking/relocation with load barriers and colored pointers — see [../../compilers/advanced/zgc.md](../../compilers/advanced/zgc.md), [../../compilers/advanced/shenandoah-gc.md](../../compilers/advanced/shenandoah-gc.md)). Distributed systems, facing the same "when is it dead" question without a root set, answer with **leases**: a time-limited grant (session, lock, DHCP address, S3 pre-signed URL) renewed by heartbeat; expiry is the definition of death. Because expiry can outlive a live holder, leases are paired with **fencing tokens** — monotonic identifiers the resource checks, so a stale holder's writes are rejected (see [../../distributed/fundamentals/fencing-tokens.md](../../distributed/fundamentals/fencing-tokens.md)).

## The Shared Principle

**Reclamation requires a definition of dead, and every definition is an approximation from incomplete information: unreachable-from-roots (tracing), zero-references (refcounting), expired-lease (distributed).** Each chooses its error direction deliberately — tracing may retain (safe, leaks space), refcounting may leak cycles (safe, leaks space) but frees promptly, leases may kill live holders (unsafe without fencing, frees promptly *by wall clock*). A second shared principle: all of them exploit **locality to bound reclamation work** — generations scan the young set, working sets scan the hot set, lease systems renew only live grants so the "dead" set identifies itself silently.

## Where the Analogy HOLDS and BREAKS

| Aspect | HOLDS | BREAKS |
|---|---|---|
| The liveness question | "When can I reclaim?" is identical for heap objects, sessions, locks, temp files | The oracle differs: GC computes reachability on demand; distributed systems *cannot* compute it globally and settle for time |
| Cycle handling | Refcounting fails cycles; tracing collects them | Distributed "cycles" (A waits on B while B waits on A) are *deadlocks*, a liveness problem, not a reclamation one — same graph shape, different pathology (see [./transactions-concurrency-control.md](./transactions-concurrency-control.md)) |
| Locality bet | Generational hypothesis ↔ working set: both bound work to the hot set | Memory working sets are measured in Δt windows by the kernel; "generations" of *sessions* have no equivalent cheap measurement — TTLs are policy, not measurement |
| Pauses | STW pause = SLO-shaped tail latency, in-process | A distributed lease has a worse failure: the *world stops for the holder* (GC pause, VM migration, network blip) while the clock keeps running — expiry strikes live holders, producing split brain; GC has no analogue because the collector and the mutators share a clock |
| Safety direction | Tracing errs toward retention; that is *safe* in-process | Premature reclamation distributed (fencing absent) is *unsafe* (two writers); hence distributed designs must add fencing, where GC needs no equivalent |

The deepest break: **a tracing collector has an atomic global view — it can stop the world and then compute truth.** No distributed system can. A lease is a promise to approximate that global view with local clocks, and every lease design inherits clock skew, renewal failures, and the "paused holder wakes up" scenario. This is why distributed reclamation is a *protocol* problem (renewal, fencing, quorum-checked grants) while GC is a *runtime* problem.

## A Concrete Worked Example

**Generational arithmetic.** Heap: 8 GiB, young gen 256 MiB, allocation rate 1 GiB/s, 90% of objects die before promotion. Mark throughput ~1 GiB/s per core, 8 cores. Full-heap mark-and-compact: 8 GiB / (8 × 1 GiB/s) ≈ **1 s STW**. Minor collection: scan 256 MiB young + ~10 MiB remembered set ≈ 266 MiB / (8 × 1 GiB/s) ≈ **33 ms**. Bounding work by locality bought a 30× pause reduction; sizing the young gen so it fills between SLO-critical windows (or using G1/ZGC to interleave) is the SLO engineering on top. The counterfactual is the lesson: without the generational bet, *every* collection pays full-heap cost and the p99 SLO dies at heap size, not at code speed.

**The paused lease holder (distributed twin of a GC bug).** ZooKeeper-style lock: client A acquires lock with session lease T = 10 s, fencing token 33. A's process hits a 12 s full-GC pause (exactly the 1 s pause from above, on a bigger heap). Lease expires at t+10; session closes; client B acquires the lock with token 34 and starts writing to storage. A wakes at t+12 with a valid-looking lock in memory and writes too — **split brain**. Fencing closes it: storage rejects token 33 < 34. The map to GC is exact: A's "reachable in memory" state was not the system's definition of liveness; the wall clock was. Any design that lets a process's internal state (lock held, session valid) substitute for a renewed lease will eventually meet this pause.

**Refcount cycle arithmetic.** A doubly linked list of 1,000 nodes (64 B each) is dropped in a pure-refcount runtime: every node holds two internal references; counts never hit zero; 64 KiB leaks per occurrence. At 100 occurrences/hour that is 6.4 MB/hour — invisible in a load test, fatal over a month. Python's hybrid (refcount + cyclic GC) is the production answer; Rust's `Rc`/`Weak` split is the compile-time answer.

## When This Connection Is Useful

- **Problem-solving heuristics.** Any "resource cleanup" design — heap, file handles, sessions, locks, cache entries — should begin by choosing the definition of dead and its error direction: prefer retention-with-GC when correctness beats space; prefer expiry-with-fencing when space/staleness beats the cost of a false kill. Then ask who measures liveness (roots, counters, clocks) and what the work bound is (full heap, young gen, live grants).
- **Interview answers.** "Implement a garbage collector" reduces to: define roots, BFS, sweep — the graph traversal is the whole idea, and saying so plus the trade (retention-safe, pause-costly) is the senior signal. "Why did our lock fail over while the holder was alive?" — the lease/pause/fencing story above; candidates who reach for fencing tokens unprompted stand out. "Why do generational GCs exist?" — connect the generational hypothesis to the working-set model: one locality principle, two domains.
- **Engineering decisions.** Size young gen and pause targets against the SLO, not the heap (pause ≈ scanned-bytes / mark-throughput). Choose collectors by pause budget: throughput collector for batch, ZGC/Shenandoah/G1 for p99-sensitive services. In distributed designs, never trust an unrenewed lease; ship fencing tokens with the lock from day one, and keep lease TTL comfortably above worst-case pause (which, per the arithmetic above, you must first measure).

## Interview Questions

1. Define the GC root set and trace why mark phase is a graph reachability computation. Which DSA traversal(s) does it use, and what makes the "unreachable ⇒ dead" definition conservative?
2. Explain why reference counting cannot collect cycles, quantify the leak for a 1,000-node doubly linked list, and name two production systems that hybridize refcounting with tracing.
3. State the generational hypothesis and connect it to Denning's working-set model. Both bound collection work by locality — what is measured in each case, and who measures it?
4. Walk through the paused-lease-holder scenario with concrete times and show precisely how a fencing token prevents the split brain. Why does the in-process GC analogy have no equivalent failure?
5. Your service has a 100 ms p99 SLO and a 32 GiB heap with ~2 s full-GC pauses. Give three distinct mitigation strategies with their trade-offs, ordered by implementation cost.

## Key Takeaways

- Reclamation always needs a definition of dead: unreachable (tracing), zero-referenced (refcounting), lease-expired (distributed) — each an approximation with a chosen error direction.
- Tracing GC is graph reachability from roots; refcounting is per-object counting; their known failure modes (loitering vs cycles) are duals, and production systems hybridize them.
- The generational hypothesis and the working-set model are the same locality principle; both turn "scan everything" into "scan the hot set," with ~30× pause effects in the arithmetic.
- STW pauses are SLO events: pause ≈ scanned bytes / mark throughput; modern collectors (G1, ZGC, Shenandoah) exist to move that work off the critical path.
- Distributed reclamation replaces the global reachability oracle with time (leases) — and therefore must add fencing, because a paused or partitioned holder can otherwise outlive its own death.

## Cross-References

- [../../compilers/advanced/garbage-collection.md](../../compilers/advanced/garbage-collection.md) — Garbage Collection — collector taxonomy in depth.
- [../../compilers/advanced/g1gc.md](../../compilers/advanced/g1gc.md) — G1 GC — region-based, pause-targeted collection.
- [../../compilers/advanced/zgc.md](../../compilers/advanced/zgc.md) — ZGC — sub-ms pauses via colored pointers and load barriers.
- [../../compilers/advanced/shenandoah-gc.md](../../compilers/advanced/shenandoah-gc.md) — Shenandoah — concurrent compaction, the other pauseless design.
- [../../compilers/advanced/jemalloc.md](../../compilers/advanced/jemalloc.md) — jemalloc — the manual-allocation counterpoint.
- [../../os/memory/slab-allocator.md](../../os/memory/slab-allocator.md) — Slab Allocator — kernel object caching and lifetimes.
- [../../os/virtual-memory/working-set.md](../../os/virtual-memory/working-set.md) — Working Set — Denning's model, the OS-side locality measurement.
- [../../distributed/fundamentals/fencing-tokens.md](../../distributed/fundamentals/fencing-tokens.md) — Fencing Tokens — the safety net for lease-based liveness.
- [../../distributed/fundamentals/distributed-locks.md](../../distributed/fundamentals/distributed-locks.md) — Distributed Locks — lease acquisition and renewal protocols.
- [./transactions-concurrency-control.md](./transactions-concurrency-control.md) — Transactions and Concurrency Control — who collects MVCC's dead versions; cycles-as-deadlock.
