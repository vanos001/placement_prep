# Concurrency and Scheduling Assumptions: What Single-Threaded Intuition Gets Wrong

## Overview

Concurrency bugs are rarely failures of knowledge — everyone knows what a race condition is. They are failures of *assumption*: the belief that a line of code is atomic, that a started thread is running, that a slept thread wakes on time, that a higher-priority thread runs first, and that a timeout is a promise. Each belief is true often enough in development to become invisible, and false often enough in production to become an incident.

This chapter audits those assumptions with the same five-step pattern used throughout this collection. The counterexamples here are chosen so you can reproduce each one mentally from first principles — none relies on exotic hardware, only on the ordinary behavior of schedulers, memory, and signals.

## Assumption 1: "This Operation Is Atomic"

### The taught rule

A statement like `counter++` or `if (map.containsKey(key)) map.put(key, value)` is a single operation and therefore safe from other threads.

### The hidden assumptions

- One source statement is one machine action. In reality `counter++` is load, increment, store — three memory operations that can interleave with another thread's three.
- A read of a wide value reads all of it at once. In Java, a *non-volatile* `long` or `double` write may legally be treated as two separate 32-bit writes (JLS §17.7), so a reader can observe the high half of one value and the low half of another — word tearing, defined behavior, still nonsense values.
- The library call you trust ("check then insert") is a sequence of synchronized sub-operations, not one synchronized operation.

### Counterexample

```java
long value;                    // non-volatile long on a 32-bit JVM
/* Thread A */ value = 0x1122334455667788L;
/* Thread B */ value = 0xAABBCCDDEEFF0011L;
/* Reader may see a mix: 0x11223344DDEEFF00 — no exception, just corruption */
```

And the classic counter: two threads each run `counter++` 10,000 times. Interleavings lose updates; the final count is reliably below 20,000, and by how much varies run to run — the signature of a race.

### What changes when the assumption is removed

Atomicity is a property of the *primitive*, not the syntax: use `AtomicInteger.incrementAndGet` (CAS-based), `std::atomic<int>` in C++, mutex-protected state, or `sync.Map`-style structures that make check-then-act a single operation. The corrected statement: *an operation is atomic only if the language or library guarantees it as one indivisible step — assignment to a `long` is not such a step in Java unless the field is volatile; increment never is.*

### Consequences

"Which operations are atomic in Java?" is a standard senior probe, and the honest answer (references, reads/writes of primitives *except* non-volatile long/double — plus everything under `java.util.concurrent.atomic`) surprises most candidates.

## Assumption 2: "Check-Then-Act Is Safe If Both Parts Are Atomic"

### The taught rule

`if (!cache.containsKey(k)) cache.put(k, compute(k));` — each call is thread-safe, so the composition is fine.

### The hidden assumptions

The check and the act are two atomic operations with a gap between them; another thread can pass the same check inside that gap (time-of-check to time-of-use, TOCTOU). Every part being individually synchronized does not make the *invariant* ("at most one entry per key, computed once") hold.

### Counterexample

Two threads run the line above with a plain `ConcurrentHashMap`. Both see "absent" (both checks are valid), both compute, both put — `compute(k)` ran twice, and if it has side effects (an HTTP call, a charge, an audit entry), you just duplicated them. The file-system version is the security classic: `if (!file.exists()) file.create()` raced by an attacker pre-creating a symlink. The most instructive variant is double-checked locking without `volatile`: the inner `if (instance == null)` passes before the constructor's writes become visible, and another thread receives a half-constructed object — the canonical failure documented in the JSR-133 Cookbook.

### What changes when the assumption is removed

Collapse check-then-act into one atomic step: `map.computeIfAbsent(k, v -> compute(v))`, `putIfAbsent`, compare-and-set loops, or a lock covering the whole region. The corrected statement: *compound invariants need compound atomicity — either a single CAS-style primitive or a critical section spanning check and act.*

### Consequences

This is the most common real-world concurrency review finding, and interviewers escalate it exactly as the [follow-up tree](../followup-tree/index.md) models: from "is HashMap thread-safe?" to "is your check-then-act?" to "is your double-checked locking?".

## Assumption 3: "If the Thread Wrote It, I Will See It" (Single-Core Intuition)

### The taught rule

A thread sets `stop = true`; the worker loop `while (!stop) { ... }` exits shortly after.

### The hidden assumptions

- The reading thread re-fetches the variable each iteration. Optimizing compilers and JITs may hoist the load out of the loop (it never changes "within the thread"), producing an infinite loop — without any exotic CPU model, purely from legal optimization.
- Even if re-fetched, the write is visible promptly: without a happens-before edge there is no bound on staleness (see [memory model](memory-model.md) for the semantics).

### Counterexample

The hoisted-load infinite loop above is observable in practice for non-volatile fields on modern JITs. It is also historically the difference between the buggy and fixed publications of the same code: adding `volatile` to `stop` both prevents the hoist and creates the ordering edge. Hardware alone would eventually let the loop see the update on most x86 code paths — it is the *compiler assumption* ("this variable is effectively constant in this loop") that bites first.

### What changes when the assumption is removed

Cross-thread visibility and ordering must be established explicitly: `volatile`/atomics for flags, better yet a signal that blocks (`queue.take()`, `condition_variable`), which also avoids busy-waiting. Corrected statement: *a loop condition that reads a variable written by another thread needs a synchronization edge; "it works on my machine" measured nothing about the compiler's optimization budget.*

### Consequences

Interviewers phrase it as "why does the busy-loop sometimes never terminate?" and the strong answers mention both the JIT hoist and the visibility guarantee.

## Assumption 4: "volatile Makes Increment Atomic"

### The taught rule

Make the shared counter `volatile` and races disappear.

### The hidden assumptions

`volatile` (Java) provides visibility and ordering, not atomicity of read-modify-write. `volatile int c; c++` is still load, add, store — three steps with races between them.

### Counterexample

Two threads incrementing a `volatile int` 10,000 times each still lose updates; making the field volatile only guarantees each thread *sees* the others' stores, not that the three-step sequence is indivisible. The fix is `AtomicInteger` (whose `incrementAndGet` is a single CAS-locked hardware operation) or a mutex.

### What changes when the assumption is removed

Match the tool to the needed guarantee: visibility → `volatile`; atomic read-modify-write → atomics or locks; compound invariants → locks or concurrent data structures. The corrected statement mirrors the [memory model](memory-model.md) chapter: in C/C++ `volatile` does not even provide visibility, so the Java intuition fails there doubly.

### Consequences

This is the trap inside the trap: candidates who correctly said "use volatile" for Assumption 3 over-apply it here. Distinguishing visibility from atomicity is the actual skill being tested.

## Assumption 5: "sleep(1) Waits 1 Second" (and Sleep-Based Coordination Works)

### The taught rule

`sleep(n)` pauses the thread for n units, so sleeps sequence events: write, `sleep(1)`, read.

### The hidden assumptions

- Sleeps are "at least" bounds, not exact durations: the OS timer granularity, scheduler delay, and load all add time.
- POSIX `sleep`/`nanosleep` can return *early* when interrupted by a signal — POSIX specifies that `sleep` returns the unslept remainder when this happens. Code that ignores the return value can proceed "one second later" after ten milliseconds.
- The other machine finished its work. A sleep is a guess about someone else's latency distribution.

### Counterexample

A test does `send(); Thread.sleep(1000); assert resultReady();`. Under CI load the producer takes 1.4 seconds, the assert fails intermittently, and the team adds retries to the test instead of a real readiness signal. In the reverse direction, a C program calling `sleep(10)` inside a process that receives SIGUSR1 every second never sleeps more than milliseconds — and the bug only appears after the signal handler was introduced.

### What changes when the assumption is removed

Coordinate with synchronization primitives, not time: completion callbacks, condition variables, latches, polling readiness with backoff for genuinely asynchronous systems — and treat every sleep-based workaround as a defect ticket. Corrected statement: *sleep gives a lower bound on delay (modulo signal interruption, which returns early) and gives no guarantee about other components' progress; deadlines belong to explicit timeouts, readiness to explicit signals.*

### Consequences

"Flaky test that passes on retry" is one of the most common interview war stories, and sleep-based synchronization is its most common root cause.

## Assumption 6: "Higher Priority Runs First"

### The taught rule

Priority schedulers run the highest-priority runnable task; priorities express importance.

### The hidden assumptions

- A higher-priority task is *runnable*. If it blocks on a lock held by a low-priority task, the scheduler runs everyone else in between — priority inversion, unbounded waiting, starvation of the important task by the unimportant ones.
- Priorities are static and meaningful; in fair-share schedulers (CFS on Linux) "priority" is a weight on CPU share, and a thread that sleeps a lot accumulates entitlement — the intuition "high nice wins immediately" does not match the mechanism.
- Starvation is a scheduler bug. It is the direct consequence of strict priority ordering with a continuous stream of high-priority work: low-priority tasks can wait indefinitely (lock-level starvation is catalogued in this repo's [lock starvation](../../concurrency/lock-starvation.md) page).

### Counterexample

The Mars Pathfinder mission (1997) is the textbook incident: a low-priority meteorological thread held a mutex; medium-priority threads consumed the CPU; the high-priority thread that needed the mutex stalled; the watchdog reset the system — repeatedly, on Mars. The diagnosis and fix (enabling priority inheritance so the mutex holder briefly inherits the blocked reader's priority) are documented in the JPL software team's own account. The mechanism generalizes to any system with priorities plus shared locks, from RTOS code to database priority queues.

### What changes when the assumption is removed

Corrected statement: *strict priority ordering is only safe combined with inversion protection — priority inheritance/ceiling on locks, aging, or reservation-based fairness; otherwise importance must be expressed as share (fair schedulers) or deadlines (EDF), not as strict ordering.* In interviews, "design a scheduler where important work always wins" should immediately raise "and how do you prevent inversion and starvation?" — that question is the point.

### Consequences

Priority inversion connects this chapter to real-time scheduling, to [deadlock and blocking analysis](../../concurrency/deadlock-detection.md), and to the design-review habit of asking who holds locks across which waits.

## Assumption 7: "Threads Start Instantly and Are Cheap"

### The taught rule

Need parallelism? Create a thread (or ten thousand). Startup cost is negligible.

### The hidden assumptions

- Thread creation allocates a stack and registers the thread with the OS: microseconds of CPU plus megabytes of address space, under a scheduler that may not run the new thread promptly under load.
- Unbounded creation amplifies overload: each new request spawns a thread, more threads contend, throughput collapses — the retry storm's sibling.
- "Started" means "scheduled": between `t.start()` and the first instruction executing, an unbounded real-time gap can pass (this is the sibling of the [network](network-distributed.md) assumption "a sent request is being processed").

### Counterexample

A server under burst load creates one thread per request. At 5,000 concurrent requests it holds thousands of stacks (memory pressure) and spends measurable time purely in scheduler context switching; latency grows superlinearly precisely when it matters. The same server with a bounded pool of 200 workers degrades by queueing, which is observable and controllable.

### What changes when the assumption is removed

Bounded executors with explicit queueing, backpressure on the admission side, and asynchronous/structured concurrency where the runtime multiplexes tasks onto few threads. Corrected statement: *thread (or goroutine, or request) creation is a resource decision with a cost curve; treat concurrency level as a tuned parameter, not an emergent one.*

### Consequences

The "thread pool sizing" interview question exists to test exactly this; the follow-up ("what happens if the queue is unbounded?") tests whether the candidate has replaced the assumption or just moved it.

## Assumption 8: "A Timeout Is a Guarantee"

### The taught rule

Set a timeout and the operation cannot hang the system: `connectTimeout=5s`, `readTimeout=10s`, done.

### The hidden assumptions

- A timeout bounds *waiting*, not *effect*. If the server processed the request and the response was lost, the client times out and retries — the work happens twice (see [network-distributed](network-distributed.md) for idempotency).
- Each hop's timeout must fit inside the caller's deadline; a 10-second read timeout under a 5-second user-facing budget is a bug that only appears under load.
- The operation respects the timeout at all: a blocking call into a library (DNS resolution, a driver without socket timeouts, a stuck mutex) may ignore your setting entirely.

### Counterexample

A payment client times out at 10 seconds and retries on the same idempotency-less API. The first request *did* reach the card network after 9.8 seconds; the retry charges the customer twice. The bug was not the timeout — it was the assumption that a timeout means the operation did not happen. Fencing tokens and idempotency keys are the standard defenses; the failure-detector framing (timeouts as *suspicion*, not fact) is in this repo's [failure detectors](../../distributed/fundamentals/failure-detectors.md) page.

### What changes when the assumption is removed

Corrected statement: *a timeout converts "unknown duration" into "bounded waiting with unknown outcome"; pair every timeout with an idempotency strategy and a deadline that propagates across hops.* That is also the honest framing for the interview question "how do you prevent double charges on retry?"

### Consequences

Every distributed-systems interview that involves retries reaches this assumption within minutes; the candidates who state "timeout means I don't know, not that it failed" are the ones who design idempotency correctly.

## Interview Questions

1. **Is `counter++` atomic in Java if `counter` is volatile?** No. Volatile gives visibility and ordering; the increment is still a three-step read-modify-write. Use `AtomicInteger` or a lock. Bonus depth: non-volatile `long`/`double` can even tear (JLS §17.7).
2. **Both threads call check-then-put on a ConcurrentHashMap and `compute` runs twice. Each individual call was thread-safe — what failed?** The compound invariant. Thread-safety of components does not compose into atomicity of sequences; collapse the sequence with `computeIfAbsent`/`putIfAbsent` or hold a lock across the whole check-then-act.
3. **Why can `while (!stop) {}` loop forever even after another thread sets `stop = true`?** The JIT may hoist the never-modified-locally load out of the loop, and there is no happens-before edge forcing visibility. Declare `stop` volatile (or use a blocking signal) so the write is both seen and ordered.
4. **What actually went wrong on Mars Pathfinder, and what is the general fix?** Priority inversion: a low-priority mutex holder was preempted by medium-priority work while a high-priority task blocked on the mutex, tripping watchdog resets. The fix was priority inheritance. Generally: strict priority scheduling needs inversion protection (inheritance/ceiling), aging, or share-based fairness.
5. **A client times out and retries. Under what conditions is that safe, and what does the timeout actually tell you?** The timeout bounds waiting, not the server's effect: the work may have completed. Retrying is safe only if the operation is idempotent (idempotency keys, fencing tokens, exactly-once infrastructure). "Unknown outcome" is the correct reading of a timeout.

## Key Takeaways

- Atomicity belongs to primitives and critical sections, never to source statements or per-call thread safety.
- Check-then-act is the most common concurrency defect shape; the fix is always "make the sequence atomic", never "make the parts atomic".
- Visibility and atomicity are different guarantees; `volatile` in Java is the former, atomics and locks are both, C's `volatile` is neither for threads.
- Sleeps are lower bounds and guesses; priorities need inversion protection; threads are resources with cost curves; timeouts convert uncertainty into bounded waiting, not into knowledge.
- Every corrected statement here is a design-review question in disguise — which is why these assumptions dominate senior interviews.

## Cross-References

- [Memory model assumptions](memory-model.md) — the semantics (happens-before, races, volatile) that this chapter builds on.
- [Concurrency overview](../../concurrency/overview.md) — the repo's main concurrency track.
- [Atomic primitives](../../concurrency/atomic-primitives.md) — CAS, fences, and the tools that replace these assumptions.
- [Lock starvation](../../concurrency/lock-starvation.md) — starvation mechanics at the lock level.
- [Thread pools](../../concurrency/thread-pools.md) and [OS thread pools](../../os/threads/pools.md) — the resource-management answer to Assumption 7.
- [Priority scheduling](../../os/scheduling/priority.md) and [Linux CFS](../../os/scheduling/linux-cfs.md) — scheduler mechanisms behind Assumption 6.
- [Deadlock detection](../../concurrency/deadlock-detection.md) — blocking analysis for inversion-prone designs.
- [Failure detectors](../../distributed/fundamentals/failure-detectors.md) — timeouts as imperfect failure detection.
- [Network-distributed assumptions](network-distributed.md) — sibling chapter: retries, idempotency, and the fallacies behind Assumption 8.
- [Therac-25](../failure-casebook/therac-25.md) — the canonical incident where check-then-act races had safety-critical consequences.
