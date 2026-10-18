# Follow-up Tree: Mutex to Lock-Free

## Overview

"What is a mutex?" is the first question in almost every concurrency interview, and its follow-up ladder is the widest in systems interviewing: implementation (futexes), alternatives (spinlocks), semantics (what exactly is being protected), scheduling interaction (priority inversion), global failure (deadlock), and finally the atomic primitives that make locks optional (CAS, ABA, lock-free progress guarantees). This page walks the ladder. The mechanisms are documented in [Mutex](../../os/synchronization/mutex.md) (including its futex flow diagram), [Spinlocks](../../os/synchronization/spinlocks.md), [CAS](../../os/synchronization/cas.md), and [Lock-Free Programming](../../concurrency/lock-free.md); the sibling comparison of primitives is in [Concurrency Primitives](../why-not-handbook/concurrency-primitives.md). Here we cover the escalation reasoning between rungs.

## The Opening Question

**"What is a mutex, and what problem does it solve?"**

The expected core answer: a mutual-exclusion primitive ensuring that at most one thread holds it at a time, so a section of code that manipulates shared state cannot interleave with others doing the same. Two properties distinguish it from mere "locking": *ownership* (only the locker may unlock it) and *blocking* (contenders sleep rather than burn CPU).

Why this answer is correct: the mutex's real product is not exclusion but a **restored invariant**. Code that updates shared state typically breaks it temporarily (a two-field update, a list unlink); the mutex guarantees that no other thread *observes* the intermediate state. If you say "it protects code" the follow-ups will expose the error; say "it protects the invariant over the data, and the critical section is where the invariant may be temporarily broken" and the follow-ups become confirmations. This framing is rung one of the ladder and the thesis of the whole chain.

## Follow-up 1: How Is a Mutex Actually Implemented?

**What it tests:** whether you know the fast/slow-path design — the single most-cited piece of concurrency engineering — and can explain why it is shaped that way.

**How to reason:** a naive mutex needs a syscall per lock/unlock (the kernel must be able to sleep the caller). Ask what that costs when *uncontended* — the overwhelmingly common case — and what mechanism avoids it.

**Answer.** Linux-style futex mutexes (Drepper, ["Futexes Are Tricky"](https://akkadia.org/drepper/futex.pdf); the syscall is [futex(2)](https://man7.org/linux/man-pages/man2/futex.2.html)): the mutex is a word in userspace; lock uncontended is a single atomic CAS from "unlocked" to "locked" — **no syscall, no kernel entry**. Only when the CAS fails (someone holds it) does the thread call `futex(FUTEX_WAIT)` to sleep in the kernel; unlock does a CAS back and calls `futex(FUTEX_WAKE)` to wake a waiter *only if waiters exist*. The design principle is worth stating explicitly: *optimize the uncontended path even at the cost of the contended path*, because contention frequency falls off a cliff while its cost is bounded. Deeper machinery exists — glibc uses a three-state word (unlocked / locked-no-waiters / locked-with-waiters) to skip the wake syscall when nobody waits, and [qspinlock/MCS designs](../../os/advanced/mcs-qspinlocks.md) give each waiter its own cache line to avoid thundering herds — but at this rung, fast path + slow path + "why" is the answer. The full mechanics live in [Futex Deep Dive](../../os/modern/futex-deep-dive.md).

## Follow-up 2: Spinlock vs Mutex — When Would You Ever Busy-Wait?

**What it tests:** whether you can reason about the interaction between waiting strategy, critical-section length, and the scheduler — not just recite "spin = waste."

**How to reason:** sleeping costs a context switch (microseconds, plus cold caches — see [Context Switching](../../os/processes/context-switching.md)); spinning costs CPU cycles *held by a thread that cannot make progress*. Each is cheaper in a different regime. Name the regime boundary: the expected wait time versus the cost of a context switch.

**Answer.** If the holder will release in a few hundred nanoseconds (short critical sections, both threads on cores), spinning wins: the contender acquires on the first try after release, having avoided a two-context-switch round trip that costs more than the wait. If the wait could exceed a context switch's cost, sleeping wins: spinning steals the CPU from the very thread that could release the lock — and on a single CPU, a spinning contender *guarantees* the holder never runs. Hence: mutexes (sleep) for user-space critical sections of unknown length; spinlocks (busy-wait, with `preempt_disable` discipline) for kernel contexts where sleeping is illegal (interrupt handlers) or sections are provably tiny; **adaptive mutexes** spin briefly then sleep, betting that a lock that was recently held is still hot ([Spinlocks](../../os/synchronization/spinlocks.md), [Sync Primitives](../../os/advanced/sync-primitives.md)). Edge cases to volunteer: spinning under oversubscription (more runnable threads than cores) is self-defeating; and long critical sections make *any* wait strategy bad — the fix is shrinking the section or splitting the lock, not choosing a fancier wait. Under real contention, queue-based locks (MCS/qspinlock) avoid the cache-line thundering herd that naive test-and-set spinlocks cause — a good senior flourish because it ties this rung to the cache-coherence cost model.

## Follow-up 3: What Exactly Does a Mutex Protect?

**What it tests:** the invariant discipline — the most common conceptual failure in concurrency interviews and in code review.

**How to reason:** take a candidate answer ("the array," "the function") and stress it: is the array safe the instant the mutex is released? What about the *other* mutable state the function touched?

**Answer.** A mutex protects an **invariant over a set of data**, and the critical section is the interval in which that invariant is allowed to be broken. Consequences that sound advanced but follow directly: (1) *multiple locks can guard one invariant* — a hash map with per-bucket locks has one invariant ("every key findable, values consistent") spanning all buckets, so operations touching two buckets need both; (2) *one lock cannot guard two unrelated invariants cheaply* — sharing it serializes unrelated operations (a lock-convoy and contention tax; see [Lock Convoying](../../os/advanced/lock-convoying.md)); (3) *invariants crossing mutexes* (two maps kept consistent) cannot be restored atomically by either mutex alone — you need lock ordering (Follow-up 5), a combined lock, or a lock-free protocol. This rung is also where granularity questions live: coarse locking is simple and slow, fine-grained is fast and deadlock-prone, and the choice is driven by how often operations touch multiple pieces of state — a trade to articulate, not a rule to cite.

## Follow-up 4: What Is Priority Inversion? (Mars Pathfinder)

**What it tests:** whether you understand that a mutex's correctness depends on the *scheduler* — the interaction that textbook lists usually leave as a named phenomenon.

**How to reason:** three priority levels, one lock. Walk the timeline: low-priority thread holds the lock; high-priority blocks on it; medium-priority threads — which don't need the lock — can now preempt the low-priority holder. Ask how long that can last.

**Answer.** Unboundedly — the high-priority thread waits on a lock whose holder cannot run because unrelated medium-priority threads keep the CPU: **priority inversion**. The canonical incident is Mars Pathfinder (1997): the lander's VxWorks system used a mutex (without priority inheritance enabled) around an information-bus structure; a low-priority meteorological thread holding it could be preempted by medium-priority communications work, starving the high-priority bus manager until a watchdog reset the entire spacecraft — resets recurring for days until JPL diagnosed it remotely and uploaded the fix (enabling priority inheritance on that mutex). The account is documented in Mike Jones's widely circulated essay "What really happened on Mars?" (1997) and in Glenn Reeves's JPL team-lead retrospective on the Pathfinder software; together they are the standard primary references. Fixes: **priority inheritance** (the holder temporarily inherits the highest blocked thread's priority — what Pathfinder enabled) or **priority ceiling** (lock acquirers are raised to a precomputed ceiling so they can't be preempted mid-section). The general lesson to state: *blocking primitives couple threads that never touched each other's data* — the medium-priority threads needed no access to the mutex yet participated in the inversion — which is why real-time kernels and lock-free code (no blocking, no inversion) care about this rung. Related pathologies: [Lock Starvation](../../concurrency/lock-starvation.md) and [Lock Convoying](../../os/advanced/lock-convoying.md).

## Follow-up 5: When Does a System Deadlock, and How Do You Prevent It?

**What it tests:** the four-condition analysis — whether you can turn "two locks in wrong order" into a system property and defend the standard prevention.

**How to reason:** deadlock needs *all four* Coffman conditions simultaneously (Coffman, Elphick, Shoshani, "System Deadlocks," 1971): mutual exclusion, hold-and-wait, no preemption, circular wait. Each prevention strategy deletes exactly one. Ask which deletion is cheapest at runtime.

**Answer.** Deleting *circular wait* via **global lock ordering** is the practical winner: acquire locks in a fixed total order and a cycle is impossible by construction — zero runtime cost, enforceable in review and by tooling (lockdep), and it composes (deadlock prevention details in [Deadlock Prevention](../../os/synchronization/deadlocks/prevention.md) and the [deadlocks](../../os/synchronization/deadlocks/README.md) hub). The other deletions are costlier: break mutual exclusion (impossible for real resources), break hold-and-wait (acquire-all-upfront — wastes locks and hurts concurrency), allow preemption (rollback semantics — fine for transactions with [optimistic concurrency](../../dbms/transactions/optimistic.md), not for mutexes). Detection at runtime is a wait-graph cycle search ([Deadlock Detection](../../concurrency/deadlock-detection.md)) — what databases and the kernel do when prevention wasn't enforced. The senior connection back to rung 3: deadlocks are what invariants *across multiple locks* cost you; the ordering discipline is the fee for composing invariants. And the twist to expect — "can a single mutex deadlock?" — yes, with self-deadlock (non-recursive relock) or with a condition variable whose predicate is signaled after an unlock gap; a reminder that deadlock is about *wait-for cycles*, not lock counts.

## Follow-up 6: What Is CAS, and What Does Lock-Free Mean?

**What it tests:** whether the ladder's top rung — bypassing locks — comes with an honest account of what it costs.

**How to reason:** CAS is "atomically: if word == expected, write new, report success." Ask what protocols you can build from it (optimistic retry loops), what "progress" means without blocking, and what new failure modes appear.

**Answer.** A lock-free structure replaces "block until the lock frees" with "retry until the world matches my expectation": read state, compute the new state, CAS it, retry on failure — no thread ever holds a lock, so blocking-based pathologies (inversion, convoys, deadlock) cannot occur. Progress terminology matters at this rung ([Wait-Free Hierarchy](../../concurrency/wait-free-hierarchy.md)): **lock-free** = *some* thread makes progress system-wide; **wait-free** = *every* operation completes in bounded steps (much harder, rarer); the CAS-retry loop is lock-free but not wait-free, because a thread can starve losing races forever. New failure modes replace the old ones: **ABA** — thread reads A, is preempted; others change A to B and back to A; the CAS succeeds although the world it reasoned about is gone (classic in stacks: a node was popped and re-pushed); fixes are versioned pointers/tags stamped into the CAS, or safe memory reclamation like hazard pointers ([ABA Problem](../../concurrency/aba-problem.md), [Hazard Pointers](../../concurrency/hazard-pointers.md)); **memory ordering** — on weakly ordered CPUs, a CAS publishes data that may be seen stale without acquire/release fences ([Memory Barriers](../../os/synchronization/memory-barriers.md), [Memory Model](../../concurrency/memory-model.md)); and **complexity** — every operation's edge cases need proof, which is why lock-free code is written by specialists with formal models ([Atomic Primitives](../../concurrency/atomic-primitives.md), [Lock-Free Structures](../../concurrency/lock-free-structures.md)). The judgment sentence that closes the ladder: choose locks by default; reach for lock-free when a *measured* contention bottleneck demands it — priority inversion disappears, but verification and reclamation costs arrive.

## How to Approach Unfamiliar Variations

1. **Ask "what invariant, over what data, restored where?"** Any primitive a interviewer names — RWLock, semaphore, monitor, transaction — is an invariant-restoration mechanism with a particular wait policy. Naming the invariant and the wait policy classifies it instantly.
2. **Ask "who can be delayed, and for how long?"** Every waiting mechanism has a worst-case delay composed of: critical-section length, scheduler behavior, and requeue storms. Priority inversion, convoys, starvation, and deadlock are all answers to this one question under different conditions.
3. **For lock-free variants, ask "what did the retry loop assume, and can the world violate it?"** ABA, lost updates, and stale publishes are all assumption violations of read-then-CAS. The fixes (versioning, fences, reclamation schemes) map one-to-one to the assumptions.
4. **When offered a choice, price it in the two currencies: progress guarantees and verification cost.** Locks: blocking progress, trivial reasoning. Lock-free: system-wide progress, hard reasoning. Wait-free: per-op progress, hardest reasoning. The interviewer's "when would you not use X?" is checking that you see the second currency.

## Interview Questions

**Q: Why does an uncontended lock cost ~20 ns while a contended one can cost microseconds?**
A: Uncontended is one CAS in userspace — no syscall (the futex fast path). Contended adds: syscall entry, sleeping and waking (two context switches), scheduler latency, and cold caches for the woken thread; at high contention add queueing and cache-line ping-ponging. This asymmetry is why lock granularity and section length dominate performance long before primitive choice does.

**Q: A real-time task sometimes misses deadlines for no visible reason; a logging thread runs constantly. Hypothesis?**
A: Priority inversion: the RT task blocks on a mutex held by a low-priority thread that the logging thread (medium priority) keeps preempting. Fix: priority-inheritance mutexes, shorten the shared section, or eliminate the shared lock. This is Pathfinder's exact shape, in miniature.

**Q: Two threads deadlock with locks A and B; the lock code is correct. What was missing?**
A: A global acquisition order (or enforcement of one). All four Coffman conditions held: mutual exclusion, hold-and-wait, no preemption, and — the one that only *convention* can break — circular wait. Fix in code review with an ordering rule, or at runtime with try-lock-backoff, or structurally by merging the locks if the critical sections are short.

**Q: A lock-free stack under load occasionally loses an element. Race?**
A: Almost certainly ABA: a consumer read the head, stalled, and on resume CAS succeeded because the head pointer was restored to the same value by pop-push cycles — the node it captured was meanwhile freed and reused. Fix: stamped (versioned) head pointer in a double-width CAS, or hazard-pointer/epoch reclamation so nodes outlive the read.

## Key Takeaways

- A mutex is an invariant-restoration mechanism with ownership and blocking; "protect the data, not the code" is the sentence that upgrades every later answer.
- The futex fast/slow-path design — CAS in userspace, kernel sleep only on contention — is the pattern to know, and its principle (optimize the uncontended case) generalizes far beyond mutexes.
- Spin vs sleep is a bet on wait duration versus context-switch cost; the losing bet in either direction is worse than the primitive choice itself.
- Priority inversion shows that blocking couples threads through the scheduler, not just through data — Mars Pathfinder is the standard citation and the reason priority inheritance exists.
- Deadlock is four Coffman conditions; lock ordering deletes circular wait for free. CAS and lock-free code trade blocking pathologies for ABA, memory-ordering, and verification costs — a trade to make on measurement, not fashion.

## Cross-References

- [Mutex](../../os/synchronization/mutex.md) — mechanics, futex flow diagram, POSIX details.
- [Futex Deep Dive](../../os/modern/futex-deep-dive.md) — the kernel side of the fast/slow path, state encodings, requeue.
- [Spinlocks](../../os/synchronization/spinlocks.md) and [MCS/qspinlock](../../os/advanced/mcs-qspinlocks.md) — spinning designs from naive to queue-based.
- [Critical Sections](../../os/synchronization/critical-section.md) — the invariant-interval framing at rung 3.
- [Deadlock Prevention](../../os/synchronization/deadlocks/prevention.md) and [Deadlocks hub](../../os/synchronization/deadlocks/README.md) — the four conditions and their removal.
- [Deadlock Detection](../../concurrency/deadlock-detection.md) — runtime wait-graph analysis.
- [Lock Starvation](../../concurrency/lock-starvation.md) and [Lock Convoying](../../os/advanced/lock-convoying.md) — contention pathologies adjacent to inversion.
- [CAS](../../os/synchronization/cas.md), [Atomic Primitives](../../concurrency/atomic-primitives.md), [Memory Barriers](../../os/synchronization/memory-barriers.md) — the lock-free toolkit.
- [ABA Problem](../../concurrency/aba-problem.md), [Hazard Pointers](../../concurrency/hazard-pointers.md), [Wait-Free Hierarchy](../../concurrency/wait-free-hierarchy.md) — the top rung's failure modes and guarantees.
- [Memory Model](../../concurrency/memory-model.md) — why reordering makes the rung-6 fences necessary.
- [Concurrency Primitives](../why-not-handbook/concurrency-primitives.md) — sibling structured comparison of the primitives named across this ladder.
- [Transactions and Concurrency Control](../connection-atlas/transactions-concurrency-control.md) — sibling atlas page linking rung 5's ideas to database transaction mechanisms.
- [Concurrency Overview](../../concurrency/overview.md) and [OS Overview](../../os/overview.md) — parent hubs.
