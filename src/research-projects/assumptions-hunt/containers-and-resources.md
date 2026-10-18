# Container Resource Assumptions: What "The Pod Has 2 CPUs" Silently Promises

## Overview

Declaring resources in a container platform feels like an engineering specification: `limits: {cpu: 2, memory: 4Gi}`. Each line encodes a kernel mechanism with its own contract — and four assumptions hide inside the declarative syntax: that the container gets two cores' worth of throughput; that a memory limit makes the container safe; that garbage collection will absorb memory pressure; and that CPU throttling is an efficiency problem rather than a latency problem. All four are reasonable readings of the YAML, and all four fail in ways that produce characteristic production signatures: p99 spikes with flat average CPU, containers killed with no application error, JVMs that never see their own memory limit, and dashboards showing "50% CPU" on a service that is frozen half the time.

This chapter audits the family with the collection's five-step pattern. The mechanisms cited — cgroup CPU bandwidth control (quota and period), OOM-killer scoring, cgroup memory accounting including page cache, and JVM container ergonomics — are documented kernel and JVM behavior, covered mechanically in the book's container chapters; the focus here is the assumptions: what each declaration silently promises, when it breaks, and what to configure instead. The sibling misconception chapters carry the adjacent false claims (containers are VMs; more threads are faster); this chapter audits the true-but-conditional statements between them.

## Assumption 1: "The Container Has N CPUs, So My App Gets N Cores of Throughput"

### The taught rule

Set the CPU limit to 2 and the application can use two cores of compute; set it to 0.5 and it gets half a core.

### The hidden assumptions

- The limit is a *bandwidth* quota, not a core allocation: cgroup CPU bandwidth control grants `quota` microseconds of runtime per `period` (classically 100 ms). A limit of 2 CPUs means 200 ms of runtime per 100 ms period — usable by any number of threads on any core, not "two dedicated cores."
- The quota is enforced *per period*: a workload that burns its 200 ms in a 20 ms burst (many threads waking simultaneously — GC threads, a fan-out of requests) is hard-throttled for the remaining 80 ms. Average utilization can look low while the container is frozen for most of each period.
- `cpu.weight`/shares are a *relative* claim that only matters under contention; on an idle node the container can use far more than its weight suggests, and on a saturated node it can get less than its quota — the two mechanisms are often conflated in reviews.
- Runtimes size their internal parallelism from what they *believe* the CPU count to be: JVM GC threads, Go's `GOMAXPROCS`, gRPC and fork-join pools all default from visible cores. A container capped at 2 CPUs on a 64-core node historically saw 64 (fixed by `UseContainerSupport` in the JVM and Java 10+, still a live issue for runtimes that read the host's core count), spawning pools sized for 32 times the granted quota.

### Counterexample

A JVM service is limited to 2 CPUs on a 64-core node, before container-aware defaults. The JVM sees 64 processors and sizes 40-something GC threads plus a matching fork-join common pool. Under a request burst, those threads burn the 200 ms quota in a few milliseconds of wall time; the kernel deschedules the entire cgroup until the next period. p99 latency jumps to hundreds of milliseconds while average CPU sits near the limit's half — the classic "low CPU, huge p99" signature. Every mechanism behaved as documented; the only wrong number was the assumption that "2 CPUs" described a *throughput* guarantee rather than a per-period bandwidth cap. The fixes are each one line: align the runtime's view (`UseContainerSupport`, `ActiveProcessorCount`, or `GOMAXPROCS` to the quota), and consider raising the period or dropping the limit in favor of requests-only scheduling.

### What changes when the assumption is removed

Corrected statement: *a CPU limit is a per-period runtime budget that converts bursty parallelism into forced stalls; throughput depends on the runtime's thread count matching the quota.* Read `nr_throttled`/`throttled_time` from the cgroup's `cpu.stat` (the dashboard most teams never added), size thread pools and GC parallelism to the quota rather than the host, and prefer CPU *requests* without hard limits for latency-sensitive services on dedicated capacity — a limit protects neighbors but converts bursts into stalls.

### Consequences

The interview probe "average CPU is 45%, the limit is 2, and p99 is 800 ms — explain" is this assumption compressed into one sentence; the expected answer traces quota → burst → throttle → stall. The more-threads misconception covers the adjacent error (parallelism as free speed); here the platform made the runtime believe in free parallelism by lying about the core count.

## Assumption 2: "A Memory Limit Keeps the Container Safe"

### The taught rule

Set `memory: 4Gi` and the container cannot take down the node; if it exceeds the limit, it gets killed cleanly and restarted.

### The hidden assumptions

- The limit is enforced by the kernel OOM killer *within* the cgroup, which is not "clean": the process gets SIGKILL — no heap dump, no exception, no flush — and the failure looks like a crash, not an allocation failure. Java code that catches `OutOfMemoryError` never runs, because the JVM never learns of the pressure.
- Victim selection is scoring, not fairness: the kernel's `oom_badness` heuristic picks by RSS relative to limits (adjustable via `oom_score_adj`). The killed process is frequently the *largest*, not the *leaking* one — often a healthy sidecar while the actual allocator keeps running.
- Cgroup memory accounting includes **page cache**: file I/O, memory-mapped files, and streaming reads all count toward `memory.max`. Cache is reclaimable, so it usually causes reclaim pressure and latency rather than OOM — but it makes "memory usage" numbers unintuitive.
- The limit protects the node, not the workload: there is no reservation for *your* container against a neighbor's allocation, and `memory.high` throttling (reclaim before kill) trades memory pressure for latency — usually the right trade, but a different contract than the YAML suggests.

### Counterexample

A data-ingestion container streams large files. Its heap is fine — 1 GiB steady — but page cache from streamed files pushes cgroup usage toward the 4 GiB `memory.max`. The kernel reclaims cache first; under a burst of concurrent streams, reclaim cannot keep up, and the cgroup OOMs. The victim chosen by score is not the streaming worker (small RSS) but the main server — the largest-RSS process in the cgroup. It dies with SIGKILL between one syscall and the next; the orchestrator restarts it, and the cycle repeats hours later. Every layer did its documented job, and the postmortem reads "OOM at 4 GiB despite 1 GiB heap" — the missing sentence is that the limit bounds *cgroup memory including cache*, not application allocations.

### What changes when the assumption is removed

Corrected statement: *a memory limit bounds what the kernel accounts to the cgroup; safety comes from matching the limit to (heap + off-heap + thread stacks + cache expectations + variance) and from making OOM observable.* Concretely: budget the non-heap components explicitly, keep `memory.high` headroom so reclaim absorbs bursts before kills, set `oom_score_adj` deliberately rather than accepting RSS-ranked defaults, and alert on cgroup OOM events rather than application exceptions — which, in the cgroup case, never fire.

### Consequences

"Java process killed with exit code 137" is the interview's favorite container war story, and the strong answer names the killer (kernel OOM, cgroup scope), the accounting (cache included), and victim selection — then proposes the budget decomposition above. The gc-means-no-leaks misconception covers the application-side twin; the cgroup side is the same assumption one layer down.

## Assumption 3: "GC Will Save Us Under Memory Pressure"

### The taught rule

When the heap fills, the garbage collector runs, frees unreachable objects, and the application carries on — memory pressure is a GC tuning problem at worst.

### The hidden assumptions

- GC can only free *unreachable* objects. A cache that grows to the limit, a session map, an unbounded queue, or native memory held by a library is reachable — the collector runs, reclaims almost nothing, and the pressure remains. More GC is the correct response to the wrong problem.
- Under cgroup pressure the feedback loop inverts: the JVM, told its heap is (say) 3 GiB, happily fills it; the container's limit is 4 GiB with other consumers; the kernel OOM-kill is the *only* mechanism that fires, and GC never gets its chance — unless the JVM's `-XX:MaxRAMPercentage` (or explicit `-Xmx`) was sized below the cgroup limit with room for the JVM's own overhead.
- Aggressive GC under pressure converts a memory problem into a latency and CPU problem: full collections burn the CPU quota (Assumption 1's throttling), which lengthens pauses, which widens the window in which the workload allocates, which deepens the pressure.
- "Tune the GC" assumes pressure is uniform: allocation spikes (batch imports, large fan-outs) produce OOM on one request while average heap stays modest — a *variance* problem steady-state tuning cannot fix.

### Counterexample

The JVM container-ergonomics history is the canonical demonstration. Pre-container-aware JVMs read the *host's* RAM: on a 128 GiB node, default heap sizing picked tens of gigabytes for a container limited to 4 GiB. The application ran fine for days — actual heap use stayed small — until one allocation spike pushed usage past the cgroup limit, and the kernel killed the JVM with SIGKILL. No `OutOfMemoryError` was thrown, no heap dump existed, and in-flight work was lost. The fix lineage is documented in the JDK: container support (`UseContainerSupport`, default-on since Java 10, backported to 8u191), `MaxRAMPercentage` defaults, and the rule that heap + JVM overhead must sit measurably below the cgroup limit. The general lesson survives the fix: the GC's safety net has a hole exactly where the kernel's enforcement is, and the two mechanisms were configured by different teams reading different documentation.

### What changes when the assumption is removed

Corrected statement: *GC manages reachability, not resource limits; the container's memory contract is (heap + non-heap + variance) ≤ limit, and the kernel is the enforcer of last resort.* Size the heap below the limit with explicit headroom, make off-heap consumers visible (native tracking, direct-buffer limits), bound the unbounded structures (cache eviction, queue caps) because GC will not, and rehearse the failure: a container OOM should page someone with a runbook, not appear as an unexplained restart.

### Consequences

The interview escalation "your JVM was OOM-killed but the heap was fine — why?" walks this ladder: host-vs-container sizing, cgroup accounting, kernel enforcement, GC's reachability-only contract. The gc-memory-management atlas chapter maps the collector mechanisms; this assumption is where they meet a hard external limit they cannot negotiate with.

## Assumption 4: "CPU Throttling Doesn't Affect Tail Latency"

### The taught rule

Throttling occasionally slows a container down; averages and p95s barely move, and the schedulers and retries smooth it out.

### The hidden assumptions

- Throttling is *cliff-shaped*, not gradual: once the per-period quota is gone, every thread in the cgroup stops — in-flight requests included — until the next period. Latency during the stall is not "slower"; it is a full stop whose length is an artifact of the period.
- The stall hits requests that already started: a 3 ms request that begins 1 ms before the quota runs out experiences a 100 ms-plus completion time. During bursts — when the tail is already worst — a modest fraction of throttled periods can touch a disproportionate share of requests.
- Probes and health checks run in the same cgroup: a throttled container can miss liveness-probe deadlines, get pronounced unhealthy, and be *restarted for being throttled* — an entire incident class whose dashboards show healthy CPU averages throughout.
- Multiple tenants interact through channels the CPU quota does not govern — memory bandwidth, last-level cache — so a neighbor at its limit can still slow your container; the quota bounds runtime, not hardware interference.

### Counterexample

A service with a 1-CPU limit serves 60 requests/second at ~10 ms of CPU each: demand is 60% of the quota, and averages agree. Under a burst to 200 rps, demand doubles the quota; parallel workers burn each 100 ms period in ~50 ms; every request in flight at the boundary stalls up to 50 ms. p50 rises modestly; p99 crosses 500 ms — and the liveness probe (200 ms timeout) times out twice, so the orchestrator restarts the container mid-burst, converting throttling into an availability event. The corrected monitoring is cgroup-native: `nr_throttled` and `throttled_time` per container, plus probe timeouts sized above the worst stall the quota permits. The averages-vs-latency misconception covers the statistical half; the cgroup period is the mechanical half.

### What changes when the assumption is removed

Corrected statement: *throttling converts parallel bursts into synchronized stalls that land on the tail and can trigger restarts; treat the quota as a latency mechanism, not just a fairness one.* Monitor throttle counters (not CPU average), align thread-pool sizes with the quota so bursts queue in the application (where backpressure and shedding apply) instead of in the kernel (where nothing can shed), size probes above the maximum stall, and reserve hard limits for isolation-critical cases.

### Consequences

"CPU is at 50% and users see timeouts" is the canonical hybrid probe, decomposing into this chapter's assumptions 1 and 4 plus the averages misconception. The pattern worth naming in interviews: each configuration was locally sensible (a limit, a probe, a thread pool), and the system behavior emerged from their unexamined interaction — precisely what an assumptions audit is for.

## Interview Questions

1. **A container with a 2-CPU limit shows 45% average CPU and p99 of 800 ms. What is the mechanism?** CFS bandwidth throttling: bursty parallelism burns the per-period quota early, and the cgroup is frozen until the next period while averages stay low. Confirm via `cpu.stat` throttle counters; fix by matching runtime parallelism (GC threads, `GOMAXPROCS`) to the quota and rethinking hard limits.
2. **Your JVM was killed with exit 137 although the heap was 1 GiB inside a 4 GiB limit. Explain.** Exit 137 is the kernel OOM kill. Cgroup memory includes page cache and non-heap; a cache-heavy workload can reach the limit with a small heap, and the kernel SIGKILLs the largest-RSS process — no `OutOfMemoryError`, no heap dump. Budget heap + non-heap + cache below the limit.
3. **Why doesn't GC prevent a container OOM?** GC frees only unreachable objects and runs inside the JVM; the cgroup limit is enforced by the kernel over everything the cgroup accounts, and it fires SIGKILL without informing the runtime. The safety nets do not overlap — heap sizing below the limit is the actual fix.
4. **Why can a liveness probe restart a healthy-but-throttled container?** The probe runs inside the same throttled cgroup; a quota-exhausted period can outlast the probe timeout, the container is declared unhealthy, and the platform restarts it. Size probe timeouts above the maximum stall the quota permits.
5. **What does `cpu: 2` actually promise, in kernel terms?** 200 ms of runtime per 100 ms period across any cores — a bandwidth cap, not two dedicated cores. Relative weight (`cpu.weight`) only applies under contention, and hardware interference (cache, memory bandwidth) is outside the quota entirely.

## Key Takeaways

- A CPU limit is a per-period bandwidth quota (quota/period), not a core count; bursts of parallelism convert it into forced stalls that averages hide and tails record.
- Runtime thread pools size themselves from the visible core count; on overprovisioned nodes that mismatch is the root of "low CPU, huge p99" — align JVM/GC/GOMAXPROCS with the quota.
- A memory limit bounds cgroup accounting (heap + non-heap + page cache) and is enforced by SIGKILL; safety is a budgeting problem, and the OOM victim is chosen by score, not guilt.
- GC manages reachability, not limits: it cannot free reachable caches and cannot see the cgroup ceiling; the heap must sit below the limit with explicit headroom.
- Throttling is a tail-latency and availability mechanism: monitor `nr_throttled`/`throttled_time`, size probes above the maximum stall, and queue in the application where backpressure exists, not in the kernel where nothing does.

## Cross-References

- [Containers are not VMs](../misconceptions/containers-are-vms.md) — the isolation claim this chapter's limits quietly depend on.
- [More threads are not faster](../misconceptions/more-threads-faster.md) — the parallelism assumption colliding with per-period quotas.
- [GC means no leaks](../misconceptions/gc-means-no-leaks.md) — the application-side twin of the "GC will save us" audit.
- [GC and memory management](../connection-atlas/gc-memory-management.md) — collector mechanics and heap dynamics in depth.
- [Concurrency and scheduling assumptions](concurrency-and-scheduling.md) — the single-host scheduling layer beneath the cgroup layer.
- [Cgroups](../../os/containers/cgroups.md), [namespaces](../../os/containers/namespaces.md), and [Linux CFS scheduling](../../os/scheduling/linux-cfs.md) — the kernel mechanisms enforcing everything above.
- [Noisy neighbors](../../cloud/noisy-neighbors.md) — multi-tenant interference beyond the CPU quota's reach.
- [JVM GC](../../languages/java/gc.md) — collector ergonomics and container-aware defaults in the JVM.
