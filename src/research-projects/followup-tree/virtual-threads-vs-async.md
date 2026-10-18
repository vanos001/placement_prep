# Follow-up Tree: Virtual Threads versus Async

## Overview

"How does a server handle 10,000 concurrent connections?" is the concurrency opener that used to have exactly one grown-up answer — event loops and async I/O — and since Java 21 has a second: virtual threads, which promise thread-per-request simplicity at event-loop scale. The interview ladder built on this comparison is one of the sharpest seniority probes in backend interviews because it tests *why* each model exists: blocking threads are simple but each costs a kernel stack and a scheduler slot; async callbacks are efficient but invert control and color every function they touch; virtual threads claim to dissolve the dilemma by making blocking cheap — and the interview is finding out where the claim bends (pinning, carrier scheduling, what does not get cheaper). This page walks the ladder — what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. Handoffs are deliberate: the locking and progress-guarantee machinery underneath is the chain in [Mutex to Lock-Free](./mutex-to-lock-free.md), and the hardware-interrupt analogue of the whole "block versus poll" question is [Interrupts and Asynchrony](../connection-atlas/interrupts-async.md). Book-level depth: [Virtual Threads](../../languages/java/virtual-threads.md), [Thread Pools](../../concurrency/thread-pools.md), [I/O Multiplexing](../../networks/sockets/io-multiplexing.md), and the runtime context in [JVM JIT](../../languages/java/jvm-jit.md).

## The Opening Question

**"How does a server handle 10,000 concurrent connections?"**

The expected core answer: with thread-per-connection, 10,000 platform threads — each a kernel thread with a megabyte-scale stack — mostly blocked on I/O; the OS scheduler holds them all and memory (10 GB of stacks plus kernel overhead) becomes the constraint long before CPU does. The classic alternative is the event loop: one (or a few) threads with non-blocking I/O and readiness notification (`epoll`/`kqueue` — the mechanics in [I/O Multiplexing](../../networks/sockets/io-multiplexing.md)), handling thousands of connections cooperatively — which is why Node, Nginx, and Redis exist.

A weak answer says "use async, threads don't scale" as a slogan — true at the wrong altitude, since it cannot say *what* about threads is expensive (the stack, the kernel object, the context switch; not the blocking itself). The strong answer separates the costs: blocking per se is nearly free — a parked thread costs nothing in CPU — what is expensive is the *per-thread footprint* and scheduler pressure at ten-thousand scale. The follow-up that escalates: **"Java 21 says it fixed this. How do virtual threads make a million threads viable?"**

## Level 2: The Platform-Thread Cost Model — What You Pay per Thread

**What it tests:** whether the candidate can decompose thread cost into stack reservation, kernel bookkeeping, and scheduling pressure — the arithmetic that makes every later rung make sense.

**Weak answer:** "Threads are heavy" — no decomposition, no numbers, and therefore no way to reason about when 10,000 threads are fine (they often are).

**Strong answer:** prices the components: each Java platform thread reserves ~1 MB of stack (lazily committed but address-space and commit-accounting real), maps to a kernel thread with its own scheduler entity, and adds context-switch and cache pollution costs when runnable (the switch-cost analysis is the sibling in [Process Lifecycle](./process-lifecycle.md)); knows the sweet spot — hundreds to a few thousand threads are routinely fine, and the classic remediation before virtual threads was the bounded thread pool with queuing.

**Escalation trigger:** "10,000 connections, thread-per-connection, 512 MB of heap and default stack settings — what fails first?"

**Answer.** Not CPU — blocked threads burn none. The first wall is stack memory: 10,000 × 1 MB reserved (typically committed on demand, but committed under load) is roughly 10 GB against a machine that planned for neither it nor the kernel thread structures; thread creation itself (mapping stacks, registering scheduler entries) makes connection *bursts* expensive, which is why pools exist at all — the sizing arithmetic shared with connection pools is the chain in [Connection Pooling](./connection-pooling.md). The second wall is the scheduler: ten thousand mostly-blocked threads are fine, but ten thousand *occasionally runnable* threads wake in bursts, and wake-ups, migrations, and cache refills cost more than the work. The strong answer's punchline: the traditional mitigations — shrink stacks (`-Xss`), pool and queue, or go async — each trade something real, and the trade-offs are what the next rung is about. The senior framing: platform threads cost memory up front and scheduling under churn; the question "how many threads" is a Little's Law question, not a taste question.

## Level 3: The Event-Loop Model — Efficiency and Its Inversions

**What it tests:** whether the candidate understands *why* async is efficient (no per-connection thread; work runs only when ready) and can name what it costs in program structure — not as a complaint, as a mechanism.

**Weak answer:** "Async is faster because it doesn't block" — backwards at the mechanism level: async does not avoid blocking work, it avoids *dedicating a thread to waiting*.

**Strong answer:** explains the loop — readiness events from the kernel (epoll), a queue of callbacks/futures, handlers that run to completion and must not block (a blocking call in a handler stalls *every* connection on the loop); names the structural price: inversion of control, stack-trace fragmentation, and function coloring (sync/async split — the language-level analysis in [Coroutines](../../concurrency/coroutines.md) and [Async/Await](../../concurrency/async-await.md)); and can state where the model is unbeatable (extreme connection counts, tiny per-event work — the design point of Nginx and Redis).

**Escalation trigger:** "One handler does a 50 ms blocking JDBC call. What happens to the other 9,999 connections?"

**Answer.** The loop is one thread: while the handler blocks in JDBC, no events are processed, no handlers run — every connection on that loop stalls for 50 ms, and under load those stalls stack into minutes. The event loop's contract is *run-to-completion*: handlers must yield (return to the loop) at every I/O point, which is why blocking APIs are forbidden and why entire async ecosystems (callback-based drivers, reactive libraries) exist to express "do the rest later" — in Java, the reactive stack's complexity is documented in [Reactive Programming](../../languages/java/reactive-programming.md) and the scheduling analogue in [Interrupts and Asynchrony](../connection-atlas/interrupts-async.md): the handler is an interrupt service routine, and "never block in the ISR" is the same rule. The strong answer prices the model honestly: efficiency is real (one thread, no per-connection stacks, work proportional to ready events), but the *programs* pay — control flow inverts, local state must be threaded through closures or state machines, stack traces cross continuations, and one accidental blocking call is a fleet-wide latency bug. That last property — a single blocking call is a platform-wide outage — is the precise weakness virtual threads were designed to remove.

## Level 4: Virtual Threads — Continuations, Carriers, and Pinning

**What it tests:** the mechanism rung: whether the candidate can explain *how* Java makes a million blocking threads cheap — user-mode continuations mounted on a small carrier pool — and can name the escape hatch where the mechanism breaks (pinning).

**Weak answer:** "Virtual threads are lightweight threads from the JVM" — no mechanism, and therefore no ability to predict the failure modes.

**Strong answer:** describes the architecture: virtual threads are JVM-managed continuations whose *stack chunks* live on the heap; blocking operations *unmount* the continuation (freeing the carrier thread to run another virtual thread) and a small pool of carrier (platform) threads does the actual work; the JVM's networking libraries are retrofitted so `socket.read()` parks the virtual thread instead of the carrier ([JEP 444](https://openjdk.org/jeps/444)) — and knows the sharp edge: code inside a `synchronized` block (or a native frame) that blocks *pins* the carrier, because the monitor is tied to the carrier thread, degrading the whole pool.

**Escalation trigger:** "After migrating to virtual threads, p99 degrades under load and thread dumps show carriers stuck in `synchronized`. What is happening?"

**Answer.** The mechanism first: a virtual thread blocks by *unmounting* — the JVM captures its stack as a heap object and the carrier moves on; the kernel-visible thread count stays at the carrier-pool size (default ≈ CPU count) while the application sees millions of virtual threads ([JEP 444](https://openjdk.org/jeps/444)). The degradation is *pinning*: a virtual thread that blocks while holding a monitor (inside `synchronized`) or executing a native frame cannot be unmounted — the carrier it rides is stuck for the duration of the block, and enough pinned carriers starve the pool: virtual threads queue waiting for carriers, latencies spike, and the symptom is a healthy-looking application inside a starved runtime. The fixes, in order: replace hot `synchronized` blocks around blocking calls with `ReentrantLock` (j.u.c locks park without pinning), narrow the synchronized scope so no I/O happens inside it, or (JDK 24+) the JEP that removes monitor pinning — the lock implementation comparison is the chain in [Mutex to Lock-Free](./mutex-to-lock-free.md). The senior details that earn the rung: thread-locals are *per virtual thread*, so a million virtual threads means a million copies of anything cached in one; and virtual threads are *not faster* at CPU-bound work — the carrier pool is CPU-sized, and compute throughput is unchanged; the win is entirely in blocked-on-I/O scale.

## Level 5: Migration Traps and the Judgment Rung — Which Model When

**What it tests:** design judgment: the candidate must migrate a real codebase (or choose a model for a new one) and defend it — knowing that virtual threads change *scheduling*, not semantics, and that every pooling instinct is suddenly wrong.

**Weak answer:** "Wrap the executor with virtual threads and it's faster" — the throughput math says otherwise: the win is memory/scale, not per-request speed, and pool sizing instincts actively break the design.

**Strong answer:** knows the trap list — semaphores not thread pools for limiting concurrency (pools now *artificially cap* what virtual threads were meant to make free); pinning from synchronized and natives; thread-local caches multiplied a million-fold; CPU-bound tasks still CPU-bound; and can state the decision rule: thread-per-request with virtual threads for I/O-bound services that value simple blocking code; event loops for extreme-fanout proxies with tiny handlers; platform-thread pools for CPU-bound work.

**Escalation trigger:** "Your service limits concurrency with a 200-thread pool. You switch to virtual threads and the database falls over. What happened, conceptually?"

**Answer.** The pool was never (only) a scheduling device — it was an *admission controller*: 200 concurrent requests capped the load aimed at the database, sized by the pool arithmetic in [Connection Pooling](./connection-pooling.md). Virtual threads removed the cap as a side effect: 10,000 requests now run concurrently, each opening its borrow-checkout against the pool, and the database — whose useful concurrency is CPU-and-lock-bounded, not connection-bounded — melts. The fix is to make the limit explicit and intentional: a `Semaphore` (the JDK's own recommendation in [JEP 444](https://openjdk.org/jeps/444)) around the database-touching region, or per-dependency bulkheads — the concurrency-limiting discipline is identical to the rate-limiter ladder's admission control in [Rate Limiter Design](./rate-limiter-design.md). The judgment synthesis the rung wants: virtual threads make *blocking* free and therefore make *unlimited concurrency* the default — a gift for I/O-bound handling and a hazard for downstream systems that assumed the old cap; the migration is not a runtime upgrade, it is a concurrency-budget renegotiation ([More Threads ≠ Faster](../misconceptions/more-threads-faster.md) is the documented claim). The decision rule to say aloud: "If my problem is thousands of blocked tasks and I want simple code, virtual threads; if my handlers are tiny and my fanout is extreme, an event loop; if my work is CPU-bound, the thread count is cores regardless — and no model changes that."

## How to Approach Unfamiliar Variations

The template for concurrency-model variations — "structured concurrency," "Go's goroutines," "Loom versus Node," "should the JDBC driver go async":

1. **Ask where the stack lives.** Platform threads: kernel stacks. Event loops: one stack, state in closures. Virtual threads/coroutines: heap-resident stacks swapped by the runtime. Every performance and debugging property (memory, pinning, stack traces) follows from that answer.
2. **Ask what blocking costs in this model.** "Cheap blocking" is the design goal of virtual threads and goroutines; "forbidden blocking" is the contract of event loops. A variation question is usually a hidden version of "what happens when this code blocks?"
3. **Separate concurrency from throughput.** None of these models make CPU work faster; they change how many *waiting* tasks are affordable. When a variation claims speed, check whether it means latency (fewer threads contending), memory (smaller stacks), or scale (more concurrent connections).
4. **For migration questions, hunt the implicit caps.** Every pool, semaphore, and thread-local was load-bearing under the old model. List them before flipping the runtime, or the limits reappear as downstream outages.

## Interview Questions

**Q: A virtual thread does CPU-heavy work for 2 seconds. What is the effect on other virtual threads?**
A: It occupies a carrier thread for the duration (no unmounting — there is no blocking point), and the default carrier pool is roughly CPU-sized, so one core's worth of throughput is consumed, as with any thread. Worse: long CPU runs trigger forced preemption checks only at Safepoint-poll boundaries (or explicit `yield()`), so the scheduler cannot rebalance mid-computation. Virtual threads change the cost of *waiting*, not of *working* — CPU-bound load needs an executor sized to cores, which is the same answer as before.

**Q: Why does the JDK recommend semaphores instead of thread pools with virtual threads?**
A: Because a pool's size was doing double duty — worker scheduling *and* load limiting — and virtual threads make the scheduling half free, so keeping a pool silently reintroduces an arbitrary concurrency cap. A semaphore expresses the part you actually meant: at most N concurrent operations against a resource that can only take N. The distinction (scheduling versus admission) is the entire conceptual migration.

**Q: Your async (reactive) service works but juniors keep introducing blocking calls that stall the loop. Virtual threads are proposed as the fix. What changes and what stays?**
A: The blocking-call hazard disappears at the platform level — a blocked virtual thread unmounts, so accidental JDBC calls degrade gracefully instead of stalling a shared loop — and code can return to sequential style (stack traces, debugging, try-with-resources all behave). What stays: the *admission* discipline (unbounded virtual concurrency still needs semaphores), CPU-bound work still needs core-sized executors, and `synchronized`-around-I/O patterns become pinning hazards until the migration checklist handles them. The operational win is turning a class of outage into a class of slowdown.

**Q: Nginx and Redis use event loops at extreme connection counts. Why didn't they adopt thread-per-connection even before virtual threads?**
A: Their per-event work is tiny and their connection counts are extreme (100K+), where even cheap blocking threads (megabyte stacks, scheduler pressure) waste memory proportional to connections rather than to *active* work; an event loop's memory is proportional to connection *state*, which is orders smaller, and run-to-completion handlers are simple when they are small. Virtual threads shrink the per-thread footprint but still cost more per idle connection than an epoll registration — the event loop remains the right point of the curve at proxy scale; the models are points on one trade-off, not a rivalry.

## Key Takeaways

- Platform threads cost stack memory and scheduler pressure, not "blocking"; the classic 10K-connection problem is a per-thread footprint problem, which is why pools and queues were the pre-Loom answer.
- Event loops avoid dedicating threads to waiting, and pay in structure: run-to-completion handlers, function coloring, and a single blocking call becomes a fleet-wide stall.
- Virtual threads are heap-resident continuations unmounted on blocking, riding a CPU-sized carrier pool — a million cheap blocking threads with kernel-visible thread count unchanged.
- Pinning is the mechanism's sharp edge: blocking inside `synchronized` or native frames strands carriers; ReentrantLock and scope discipline are the mitigation.
- Virtual threads remove implicit concurrency caps; migration is a renegotiation of admission control (semaphores, bulkheads), not a runtime swap.
- The decision rule: I/O-bound and want simple code — virtual threads; extreme fanout with tiny handlers — event loop; CPU-bound — core-sized pools in every model.

## Cross-References

- [Mutex to Lock-Free](./mutex-to-lock-free.md) — the sibling chain owning locks, parking, and progress guarantees beneath the pinning rung.
- [Process Lifecycle](./process-lifecycle.md) — the context-switch and scheduler mechanics platform threads pay for.
- [Connection Pooling](./connection-pooling.md) — the Little's Law sizing and admission-control arithmetic this ladder's migration rung re-derives.
- [Interrupts and Asynchrony](../connection-atlas/interrupts-async.md) — the hardware analogue: handlers that must not block, at process and kernel scale.
- [Virtual Threads](../../languages/java/virtual-threads.md) — the book chapter on scheduler, continuations, and JDK APIs.
- [Reactive Programming](../../languages/java/reactive-programming.md) — the Java-side async ecosystem the event-loop rung summarizes.
- [Thread Pools](../../concurrency/thread-pools.md) — the pre-virtual-threads answer, and why its sizing instincts break after migration.
- [Coroutines](../../concurrency/coroutines.md) and [Async/Await](../../concurrency/async-await.md) — the language-level treatment of coloring and continuations across ecosystems.
- [I/O Multiplexing](../../networks/sockets/io-multiplexing.md) — epoll/kqueue readiness mechanics the event loop is built on.
- [More Threads ≠ Faster](../misconceptions/more-threads-faster.md) — the documented misconception the throughput math dismantles.
- [JVM JIT](../../languages/java/jvm-jit.md) — the runtime execution context (compilation, safepoints) carrier scheduling interacts with.
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444) — the primary specification for this chain's Java claims.
