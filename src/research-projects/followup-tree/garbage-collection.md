# Follow-up Tree: Garbage Collection

## Overview

"How does garbage collection work?" is the runtime-engineering opener that separates candidates who use a GC'd language from candidates who understand one. The opening answer is genuinely simple — trace reachability, free what is unreachable — and every interesting question hides in the machinery that makes that simple idea cheap: generational layouts, write barriers, concurrent marking, and the collection of misconceptions about what "managed" memory actually promises. This page walks the ladder rung by rung: what each follow-up tests, how to reason, and the answer with its edge cases. The sibling treatment of GC's interaction with the broader memory system is [GC and Memory Management](../connection-atlas/gc-memory-management.md); this chain stays on the interview escalations themselves.

## The Opening Question

**"How does garbage collection work?"**

The expected core answer: the runtime determines **reachability** — periodically it traces the object graph starting from *roots* (thread stacks, global variables, registers, and handles into native code), marks every object it can reach transitively, and treats everything unmarked as garbage, reclaiming it. The canonical first mechanism is **mark-sweep**: a mark phase that walks the graph, then a sweep phase that walks the heap returning unmarked memory to a free list. The reachability model descends from Lisp ([McCarthy, "Recursive Functions of Symbolic Expressions and Their Computation by Machine", 1960] introduced the idea); the durable insight to state is that *reachability approximates liveness from below* — an object the program will never use again but that is still reachable is not collectable, which is why GC'd languages leak (rung 4) and why "garbage" is a conservative, syntactic notion.

Why this answer is correct: it names the roots (the single most-forgotten component — without them, "reachable" is undefined), states the graph-tracing nature, and gives a concrete first algorithm. It also positions the *contrast* the interviewer will reach for: reference counting, which frees objects the moment their count hits zero but cannot collect cycles and pays a counter-update cost on every assignment. Tracing and counting are duals — [Bacon, Cheng, and Rajan, "A Unified Theory of Garbage Collection", 2004] frames precisely which costs each moves where — and offering that framing unprompted is a strong opening.

## Follow-up 1: Mark-Sweep Leaks Fragments — What Are the Alternatives?

**What it tests:** whether you know why mark-sweep is rarely the *whole* answer: fragmentation, and the locality consequences of allocating from a fragmented heap.

**How to reason:** sweep returns memory but does not consolidate it; ask what a fragmented free list does to the next allocation and to the cache.

**Answer.** Three classic strategies, each paying differently. **Mark-sweep**: mark O(live objects), sweep O(heap size), return space to free lists — cheap when much survives, but the heap fragments, and allocation must search free lists, hurting locality. **Mark-compact**: after marking, slide all live objects to one end, updating references — eliminates fragmentation and restores allocation by bumping a pointer, at the cost of a third pass and the need to rewrite every reference (which is why *interior pointers* from native code are a pain for compacting collectors). **Copying collection**: divide the heap into two semispaces; copy live objects from the active space to the other as they are traced — total cost is proportional to *live data only*, which makes it superb when most objects die young, at the price of reserving the other half (space overhead) and of moving objects (which also breaks interior pointers). The workload-driven summary: high mortality favors copying (you pay only for survivors), high survival favors mark-sweep, and fragmentation sensitivity forces compaction eventually — which is exactly the trade the generational design of the next rung exploits. The cost models here are stated per-collection; the amortized story across collections is where the hypothesis of rung 2 does the heavy lifting.

## Follow-up 2: Why Do Nearly All JVM and .NET Collectors Split the Heap into Generations?

**What it tests:** whether you know the *empirical* foundation of GC design — the generational hypothesis — and the machinery (barriers, remembered sets) that a split heap forces.

**How to reason:** the hypothesis is a claim about object mortality distributions; every piece of generational machinery is a consequence of acting on that claim.

**Answer.** The hypothesis, backed by decades of allocation profiling: **most objects die young** — temporaries, parse results, request-scoped allocations. Generational collectors exploit it: a **young generation** collected often and cheaply by copying (only survivors are paid for, and survivors are few), and an **old generation** collected rarely. Two problems the split creates, both standard interview follow-ups: (1) the old generation's pointers *into* the young generation would force scanning the whole old heap on every minor collection, so the collector maintains a **remembered set** via **write barriers** — tiny bookkeeping executed on every reference store that records old→young pointers — which is the tax generational GC puts on *every mutation*; (2) survivors must be **promoted**, and if an object is medium-lived — too old to die young, dead before old age — it lands in the old generation and inflates the next expensive major collection (**premature promotion**; oversized survivor spaces and allocation spikes are the usual causes). The honest statement of the trade: generational GC optimizes *throughput and pause frequency* for the measured mortality profile of typical workloads — and when a workload violates the profile (big long-lived caches allocated in bursts), the design fights the workload instead of helping it.

## Follow-up 3: Stop-the-World or Concurrent — What Does G1/ZGC/Shenandoah Actually Buy?

**What it tests:** whether you understand *why* concurrent collection is hard (mutators running while you trace) and what the modern collectors pay for their pause guarantees.

**How to reason:** a concurrent collector must preserve the marking invariant while the application mutates the graph; every design answer to that is a specific barrier and a specific cost.

**Answer.** Naive tracing must stop all mutators — **stop-the-world** — or the graph changes mid-walk and live objects get missed. The standard model for reasoning aloud is **tri-color marking**: white (unvisited), gray (reachable, children not yet traced), black (fully traced). The invariant: a black object must never gain a pointer to a white one without the collector noticing. Two families of enforcement: **incremental update** (re-gray objects when the barrier sees black→white stores) and **snapshot-at-the-beginning/SATB** (record every *overwrite* of a pointer so the initial snapshot stays complete) — both via write barriers, both spending mutator time to buy concurrency. Modern JVM collectors: **G1** (default since [JEP 248](https://openjdk.org/jeps/248)) splits the heap into regions, runs most marking concurrently, and *evacuates* (copies) regions within a *pause target* you set — pauses are bounded by choosing how much evacuation fits in each pause; **ZGC** ([JEP 333](https://openjdk.org/jeps/333), production in [JEP 377](https://openjdk.org/jeps/377)) and **Shenandoah** ([JEP 189](https://openjdk.org/jeps/189), production in [JEP 379](https://openjdk.org/jeps/379)) push almost all work — including relocation — concurrent, using load barriers and colored pointers (ZGC) or forwarding pointers (Shenandoah) so application threads can read moved objects, achieving sub-millisecond-to-low-millisecond pauses even at multi-GB heaps. The cost to state explicitly: barriers execute on *every* reference load/store, so peak throughput drops and memory footprint grows (headroom for concurrent work and relocation) — tail latency is bought with throughput and RAM, the trade the "which GC would you pick" rung asks you to price. Go's collector makes the opposite bet — concurrent mark-sweep, *non*-generational, betting that small object lifetimes are absorbed by cheap allocation rather than by generational machinery; the design notes in [Go's GC guide](https://go.dev/doc/gc-guide) are a good contrast to cite.

## Follow-up 4: If GC Frees Unreachable Memory, Why Do GC'd Programs Still Leak?

**What it tests:** the misconception rung — whether "garbage collected" is understood as *unreachable memory freed*, not *memory managed*.

**How to reason:** reachability is syntactic. Ask where memory can be reachable-but-dead, and where memory lives that the tracer cannot even see.

**Answer.** Leaks in GC'd languages take two forms. **Reachable-but-dead**: objects the program will never use but that chains of references keep alive — unbounded static caches (a map keyed by request IDs that only ever grows), listeners and callbacks registered but never unregistered (each registration pins its target), `ThreadLocal` values in pooled threads (the thread outlives every request it served), and memoization without eviction. The fix is always the same shape: give long-lived registries bounded lifetime — eviction policies, weak references, or explicit teardown — and the sibling page [GC Means No Leaks](../misconceptions/gc-means-no-leaks.md) catalogs the belief directly. **Off-heap**: memory the tracer never walks — native allocations via JNI, `mmap`ed files, pooled direct buffers whose *Java wrapper* is small while the native region is large. The heap can look healthy while process RSS climbs until the kernel's OOM killer ends the party — the mechanism is [The OOM Killer](../../os/modern/oom-killer.md), and the diagnostic signature (RSS grows, GC logs clean, container killed at its cgroup limit) is worth volunteering as the rung's edge case. A third form, classloader leaks in application servers — a redeployed webapp whose stale references pin its entire classloader — is the same reachable-but-dead pattern at system scale. The chain-level lesson: GC moved the *bookkeeping* from the programmer to the runtime, not the *lifetime design*.

## Follow-up 5: Finalizers and Weak References — What Are They Actually For?

**What it tests:** whether you know the cleanup toolbox beyond the collector proper, including why finalization is being removed.

**How to reason:** these features exist because reachability is the wrong lifetime for some resources — files, sockets, native memory — that need *timely, deterministic* release. Ask what each tool promises and what it cannot.

**Answer.** **Finalizers** promised "run this when the object becomes unreachable" and failed on every axis that matters: execution is delayed arbitrarily (an object needing cleanup can live a long time on a quiet heap), are not guaranteed to run at all on exit, can *resurrect* the object by storing `this` somewhere reachable, and impose ordering chaos — [JEP 421](https://openjdk.org/jeps/421) deprecates finalization for removal, replaced by `Cleaner`/phantom-reference mechanisms that at least avoid resurrection and run user code off the object. **References** come in strengths: **soft** (cleared only when memory is tight — for memory-sensitive caches, with the caveat that "how tight" is policy and unpredictable across heaps), **weak** (cleared at the next collection — for canonical mappings like `WeakHashMap` and for listener registries that should not pin their targets), and **phantom** (enqueued after the object is finalizable-and-gone — the correct hook for native-resource cleanup paired with explicit `close()`). The senior framing: all of these are *hints layered on a syntactic definition of death*; the only deterministic cleanup for resources is explicit lifecycle management (`try`-with-resources, RAII-by-structure), and the reference types exist for the cases where ownership is genuinely shared or ambient.

## Follow-up 6: "Which GC Would You Pick?" — How Do You Answer Without Guessing?

**What it tests:** design judgment: can you turn a workload description into collector requirements and a measurement plan, instead of naming a flag?

**How to reason:** the choice is priced in three currencies — pause magnitude, throughput cost, and footprint — and the workload fixes the exchange rate. Then insist on measuring before and after.

**Answer.** Extract the four inputs that matter: **heap size** (GB-scale heaps make concurrent evacuation attractive), **allocation rate** (high rates mean frequent young collections — the frequency, not the pause, can be the SLO killer), **live-data set** (a large live set makes copying expensive and favors mark-sweep phases), and the **latency contract** (p99.9 for a trading path is a different collector conversation than a batch job's throughput). The decision skeleton: default to the platform default (G1) and *measure*; if pauses exceed the SLO at a large heap, ZGC/Shenandoah trade some throughput and footprint for near-constant pauses; if the job is batch and throughput-bound, parallel stop-the-world collecting is *cheaper* and correct. The metric discipline that earns the rung's credit: know your **allocation rate** (GB/s), collection frequency, and pause *percentiles* — not averages — before changing anything, and re-measure the same three numbers after; collector swaps that are not preceded by a pause-percentile measurement are superstition. The final senior sentence: the best GC tuning is often no collector work at all but *less garbage* — smaller allocation churn (object reuse, buffer pools, tighter request scopes) moves every collector's numbers, and moving the workload is cheaper than re-tuning the machine it runs on. The memory-hardware context beneath all of it — what a page fault during evacuation costs, why heap sizing interacts with NUMA — is [Virtual Memory](./virtual-memory.md) and [Memory and the Hardware](../../os/memory/README.md)'s territory.

## How to Approach Unfamiliar Variations

The transferable template for GC follow-ups:

1. **Reduce every question to the reachability model plus one cost.** New collector? New barrier? New flag? Ask: what does it change about (a) what is considered garbage, or (b) which pass pays for it — mark, sweep, move, barrier, or footprint. Answers that name the changed cost are never wrong by more than a constant.
2. **Separate correctness from latency from throughput.** A collector that misses live objects is a bug; one with 10 ms pauses is a design point; one with 20% throughput loss is a design point of a different workload. Keep the three claims in three sentences and complexity-style ambiguity disappears.
3. **When a leak appears, classify it before fixing.** Reachable-but-dead (fix lifetimes, weak references, eviction) vs off-heap (fix native accounting, pool sizing) vs classloader pinning (fix ownership across redeploys). The symptoms differ: GC-log pressure, RSS growth with quiet logs, or perm-space behavior across redeploys.
4. **Translate "which GC" into the four workload inputs** — heap size, allocation rate, live set, latency contract — and into a before/after measurement plan. A decision framework that produces a measurement beats a memorized default.

## Interview Questions

**Q: Why can a reference-counting collector with cycle detection still lose to a tracing collector on throughput?**
A: Counting pays on *every* pointer assignment (increment/decrement, plus cache traffic on the counter), while tracing amortizes its cost into periodic collections paid only at collection time — for assignment-heavy workloads the steady-state tax of counting exceeds the batched cost of tracing. Cycle detection adds its own pass. Counting wins where deterministic, incremental reclamation matters (refcounted shared pointers, Python's object model with a cycle collector on top).

**Q: Your JVM service has clean GC logs but the container is OOM-killed at 4 GiB. Walk the diagnosis.**
A: RSS ≠ heap: the tracer sees only the Java heap, so the leak is off-heap — direct buffers, JNI allocations, mmap, or metaspace. Check native memory tracking and RSS-over-time, correlate with allocation sites (buffer pool sizing is the usual suspect), and bound the native user the same way you would bound a cache. The cgroup limit is doing its job; the missing piece was native accounting in the capacity model.

**Q: A teammate proposes soft references for the session cache. Objections?**
A: Soft references are cleared under memory pressure the *collector* defines, so cache size is unpredictable and eviction order is not LRU — hit rates swing with heap state, and a soft-reference cache can degrade exactly when load is highest (more live data → tighter memory → aggressive clearing). A bounded cache with explicit eviction is deterministic and testable; soft refs fit "best effort, correctness-neutral" data only.

**Q: Why does increasing the young generation sometimes *worsen* p99 latency even though minor GCs become less frequent?**
A: Each minor pause scales with survivors and copy work; a bigger young gen means more objects accumulate per collection, so pauses lengthen even as their count drops. If the SLO bounds the *pause* rather than the frequency, the trade goes the wrong way — which is why tuning starts from "is the contract on frequency or magnitude?"

## Key Takeaways

- GC is reachability from roots; mark-sweep is the canonical mechanism, and its costs (mark ∝ live, sweep ∝ heap) define the alternatives: copying pays for survivors, compaction pays a pass to kill fragmentation.
- The generational hypothesis — most objects die young — justifies the young/old split, whose price is write barriers and remembered sets, and whose failure mode is premature promotion.
- Concurrent collectors enforce the tri-color invariant with barriers: G1 bounds pauses by region evacuation, ZGC/Shenandoah move nearly everything off the pause path, and the price is throughput and footprint.
- GC'd languages leak in two ways — reachable-but-dead structures and memory the tracer cannot see (off-heap) — because GC automates bookkeeping, not lifetime design.
- Finalization is deprecated because deferred, unreliable, resurrectable cleanup is a trap; the reference types are lifetime hints, and deterministic cleanup remains explicit.
- "Which GC" is a pricing question: pause magnitude × throughput × footprint against heap size, allocation rate, live set, and the latency contract — measured in percentiles, before and after.

## Cross-References

- [GC and Memory Management](../connection-atlas/gc-memory-management.md) — the sibling deep-dive on GC's interaction with allocators and the OS memory system.
- [GC Means No Leaks](../misconceptions/gc-means-no-leaks.md) — the misconception behind rung 4, documented claim by claim.
- [Virtual Memory](./virtual-memory.md) — the address-translation and paging machinery beneath every heap.
- [The OOM Killer](../../os/modern/oom-killer.md) — what the kernel does when RSS exceeds the cgroup limit.
- [Memory and the Hardware](../../os/memory/README.md) — caches, NUMA, and the physical layer heap sizing must respect.
- [Process Lifecycle](./process-lifecycle.md) — where a runtime's heap comes from: fork, exec, mmap, and the memory layout rung.
- [ZGC JEP 333](https://openjdk.org/jeps/333) / [ZGC production JEP 377](https://openjdk.org/jeps/377) — ZGC's design and productionization.
- [Shenandoah JEP 189](https://openjdk.org/jeps/189) / [production JEP 379](https://openjdk.org/jeps/379) — Shenandoah's design and productionization.
- [G1 default JEP 248](https://openjdk.org/jeps/248) — G1 as the JVM default collector.
- [Finalization deprecation JEP 421](https://openjdk.org/jeps/421) — why finalizers are being removed, from the source.
- [Go GC guide](https://go.dev/doc/gc-guide) — the non-generational concurrent design contrast.
- [Java reference package](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/ref/package-summary.html) — soft/weak/phantom semantics from the API documentation.
