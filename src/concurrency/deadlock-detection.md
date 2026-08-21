# Deadlock Detection and Prevention

## Overview

A deadlock is a state in which a set of processes (or threads) is
blocked, each one holding a resource the others need and waiting for
a resource another holds. None can make progress; none can release;
the system is stuck. The phenomenon was first formalised by Edsger
Dijkstra in 1965 in *Cooperating Sequential Processes*, where he
introduced the **Banker's Algorithm** to allocate resources without
ever admitting the system to an unsafe state. Coffman, Elphick, and
Shoshani in 1971 gave the four conditions that must hold
simultaneously for deadlock to occur and that every prevention
strategy targets.

This page covers the four Coffman conditions, the resource-allocation
graph, the Banker's algorithm and the notion of a safe state,
prevention strategies (lock ordering, lock timeouts, `trylock`),
detection via cycle-finding in the wait-for graph, the Java `jstack`
detector, the Linux `lockdep` runtime checker, the Go runtime's
detection of goroutine deadlock, and the comparison to lock-free
optimistic approaches based on CAS.

## The four Coffman conditions

Coffman, Elphick, and Shoshani (1971) showed that deadlock is
possible if and only if four conditions hold simultaneously. Break
any one and deadlock cannot occur.

```
   (1) Mutual exclusion      a resource is held by at most one
                              process at a time

   (2) Hold and wait          a process holds at least one resource
                              while requesting another

   (3) No preemption          only the holding process can release
                              the resource (the OS will not take it
                              away by force)

   (4) Circular wait          the directed graph of "process waits
                              for resource held by process" contains
                              a cycle
```

The four conditions collapse to one practical implication: in any
system that uses mutex-style locks, deadlock is a possibility unless
you actively do something to remove at least one of the conditions.
The four prevention strategies below each target a different
condition.

## The resource-allocation graph

A resource-allocation graph (RAG) is a bipartite directed graph with
two kinds of vertex: processes (P) and resource instances (R). An
edge from P to R means "P is requesting R"; an edge from R to P
means "R is currently held by P".

```
       (P1)                (R1)               (P2)
        |                   ^                   |
        |  request          |  held-by         |  request
        v                   |                   v
       (R2) <-------------- (P2)               (R3)

   Looking at just P-vertices (collapsing R-vertices): the
   wait-for graph. A cycle in the wait-for graph
   is a sufficient condition for deadlock when each resource has a
   single instance.
```

When each resource has a single instance, a cycle in the RAG is both
necessary and sufficient for deadlock. When resources have multiple
instances, a cycle is necessary but not sufficient (the cycle might
be resolvable once one of the instances frees up). The Banker's
algorithm below gives a sufficient condition for deadlock-freedom
even with multi-instance resources.

## The Banker's algorithm

Dijkstra's 1965 Banker's algorithm (named after a banker who lends
money and needs to ensure they never admit themselves to a state in
which they cannot honour all commitments) allocates resources
conservatively: a request is granted only if the resulting state is
**safe**. A state is safe if there exists a sequence (the safe
sequence) in which every process can run to completion with the
resources currently available, releasing its resources at the end,
so that the next process in the sequence can run, and so on.

Inputs to the algorithm:

- `Available[j]` — number of instances of resource `R_j` currently
  free.
- `Max[i][j]` — maximum demand of process `P_i` for `R_j`.
- `Allocation[i][j]` — number of instances of `R_j` currently held
  by `P_i`.
- `Need[i][j] = Max[i][j] - Allocation[i][j]` — remaining demand.

The safety check is a greedy simulation:

```python
def is_safe(available, max_demand, allocation):
    need = [[max_demand[i][j] - allocation[i][j] for j in range(R)]
            for i in range(P)]
    work  = list(available)        # copy
    finish = [False] * P
    progress = True
    while progress:
        progress = False
        for i in range(P):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(R)):
                # P_i can run to completion: take its allocation back
                for j in range(R):
                    work[j] += allocation[i][j]
                finish[i] = True
                progress = True
    return all(finish)             # all processes can finish in some order
```

If `is_safe` returns `True`, the state is safe: there exists an
ordering of the processes such that each, when it finishes, frees
enough to allow the next to finish. The algorithm admits a new
request only if the resulting state is safe.

```
   Example: 3 processes, 1 resource type, 10 instances total.
   Available = 2; Allocation = [5, 2, 1]; Need = [3, 4, 3].
   Work = [2], finish = [F, F, F].

   P1 needs 3 > 2, skip.  P2 needs 4 > 2, skip.  P3 needs 3 > 2, skip.
   Hmm, stuck — that means unsafe, no safe sequence.
   (Wait: P3 needs 3 but Available=2, so cannot run.)

   If instead Available = 3:
   P3 can run (Need 3 <= 3).  After P3, Work = 4.  P1 needs 3 <= 4, runs.
   After P1, Work = 9.  P2 needs 4 <= 9, runs.  SAFE.
   Safe sequence: P3, P1, P2.
```

The Banker's algorithm is rarely used in real operating systems
because (a) `Max` is hard to know in advance — most processes do
not declare their maximum resource usage up front, and (b) the
conservatism is brutal: a process that has *declared* a maximum of
100MB but is currently using 10MB cannot get an additional 1MB
until the banker confirms the resulting state is safe. Real systems
prefer prevention via lock ordering or detection via cycle-finding,
below. The Banker's algorithm survives as an interview topic and as
the conceptual model on which all deadlock-freedom arguments rest.

## Prevention strategies

### Lock ordering

Impose a global ordering on all locks; acquire them only in
increasing order. This breaks the **circular wait** condition. If
every process acquires locks in the order L1, L2, L3, then no cycle
can form: any wait-for edge goes from a higher-ordered lock to a
lower-ordered lock, and a cycle in such a graph would require a
process to wait on a strictly lower-ordered lock than it already
holds, which is impossible.

```c
// WRONG: lock order depends on caller, deadlock waiting to happen
void transfer(account_t* a, account_t* b, int amt) {
    pthread_mutex_lock(&a->lock);
    pthread_mutex_lock(&b->lock);
    // ... do transfer ...
    pthread_mutex_unlock(&b->lock);
    pthread_mutex_unlock(&a->lock);
}

// RIGHT: lock in increasing address order — never deadlock
void transfer(account_t* a, account_t* b, int amt) {
    account_t* first  = (a < b) ? a : b;
    account_t* second = (a < b) ? b : a;
    pthread_mutex_lock(&first->lock);
    pthread_mutex_lock(&second->lock);
    // ... do transfer ...
    pthread_mutex_unlock(&second->lock);
    pthread_mutex_unlock(&first->lock);
}
```

Lock ordering is the most common prevention strategy in the Linux
kernel, in database engines, and in any system where the lock set
is bounded and the order can be documented. It fails when the lock
set is dynamic or when the order is context-dependent (a tree of
locks taken in a hierarchy: leaf first, or root first?).

### Lock timeout

If a lock attempt does not succeed within a fixed interval, release
all held locks and back off. This breaks the **hold and wait**
condition: a process either gets all its locks or it gets none.
Java's `tryLock(timeout)` is the canonical API:

```java
ReentrantLock a = ..., b = ...;
long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);
while (true) {
    if (a.tryLock(deadline - System.nanoTime(), TimeUnit.NANOSECONDS)) {
        try {
            if (b.tryLock(0, TimeUnit.NANOSECONDS)) {
                try {
                    // critical section
                    return;
                } finally { b.unlock(); }
            }
        } finally { a.unlock(); }
    }
    Thread.sleep(randomBackoff());  // break the livelock pattern
}
```

Timeouts break deadlock but introduce **livelock**: two processes
backing off in lockstep can loop forever. The standard remedy is
exponential or randomised backoff; randomised backoff is preferred
because it does not synchronise the two processes' retry clocks.

### `tryLock` without timeout

`tryLock()` returns immediately with `true` if the lock was acquired
and `false` if not. Combine with release-and-retry: you acquire
locks one at a time with `tryLock`; if any `tryLock` fails, you
release all held locks and retry from the beginning. This is the
strategy used in many database engines and in `std::lock` in C++17
(which does the algorithm internally for you).

```cpp
// C++17 std::lock algorithm: avoid deadlock by attempting all
// locks with try_lock; if any fails, release and retry with backoff
std::unique_lock<std::mutex> lock_a(a, std::defer_lock);
std::unique_lock<std::mutex> lock_b(b, std::defer_lock);
std::lock(lock_a, lock_b);   // handles the try/retry/backoff loop
// critical section
```

This breaks **hold and wait**: you never hold one lock waiting for
another; you hold only after acquiring all of them.

### Preemption (designing out mutual exclusion)

The fourth condition, **mutual exclusion**, can be broken by
design: if you do not need exclusive access to the resource at all,
deadlock cannot occur. This is the lock-free / wait-free approach,
which uses CAS and atomic operations instead of locks. It is the
approach taken by [Lock-free Data Structures](./lock-free.md) and by
[Transactional Memory](./transactional-memory.md).

## Detection: the wait-for graph and cycle finding

When you cannot prevent deadlock (because the lock set is dynamic,
unknown, or context-dependent), you fall back to **detection**: let
the deadlock occur, periodically build the wait-for graph, find
cycles, and abort one process in each cycle to recover.

The wait-for graph (WFG) is a directed graph on processes only:
edge `P_i -> P_j` exists if `P_i` is blocked waiting for a resource
held by `P_j`. A cycle in the WFG, when each resource has a single
instance, is necessary and sufficient for deadlock.

```
   P1 waits on R1 held by P2  -->  P1 -> P2
   P2 waits on R2 held by P3  -->  P2 -> P3
   P3 waits on R3 held by P1  -->  P3 -> P1   (cycle: P1 P2 P3 P1)

   => Deadlock. Pick a victim, abort it, release its resources,
      recompute the WFG, repeat until no cycle.
```

Cycle detection in a directed graph is O(V + E) per process and
O(V^2 + V·E) for the whole graph (the standard DFS-based three-colour
algorithm). Real systems run detection periodically rather than on
every wait: a database engine typically runs the WFG sweep every
few hundred milliseconds or whenever a wait exceeds a threshold.

Victim selection matters: aborting a process that has done little
work is cheap; aborting one that has done a transaction's worth of
writes is expensive. Common heuristics: lowest priority, least work
done, youngest (most recently started) process. The database world
solves this with the **wound-wait** and **wait-die** schemes,
which order aborts by transaction timestamp; see the
[Optimistic Concurrency](../dbms/advanced/optimistic-concurrency.md)
page.

## Java: `jstack` and the deadlock detector

The JVM ships a built-in deadlock detector. `jstack <pid>` walks the
Java-level monitor state of every thread, builds the wait-for graph
in memory, finds cycles, and prints them.

```text
$ jstack 12345
...
"Thread-1" #18 prio=5 ... waiting to lock <0x000000076b5c2b38>
  - locked <0x000000076b5c2a20> (a java.lang.Object)
"Thread-2" #19 prio=5 ... waiting to lock <0x000000076b5c2a20>
  - locked <0x000000076b5c2b38> (a java.lang.Object)

Found 1 deadlock.
"Thread-1":
  waiting to lock monitor 0x00007f9b88004f88 (object 0x000000076b5c2b38,
                                             a java.lang.Object)
  locked ownable synchronizers: - none
"Thread-2":
  waiting to lock monitor 0x00007f9b88004f88 (object 0x000000076b5c2a20,
                                             a java.lang.Object)
  ...
```

The detector works on `synchronized` blocks and on `java.util.concurrent`
locks (`ReentrantLock`, `ReentrantReadWriteLock`); it uses the JVM's
internal `ObjectMonitor` linked list (the `_entry_list`, `_wait_set`
fields on the parker) to construct edges in the wait-for graph. The
algorithm runs whenever you call `jstack`, or `ThreadMXBean.findDeadlockedThreads()`
from inside the JVM. Note that AQS-based synchronisers (e.g. semaphore,
`CountDownLatch`) are *not* visible to the deadlock detector unless they
use the `AbstractOwnableSynchronizer` machinery; the user must
register ownership explicitly.

## Linux `lockdep`

`lockdep` is the runtime deadlock detector in the Linux kernel,
merged by Ingo Molnar in 2006. It maintains a per-CPU map of every
held lock and the order in which locks have been acquired across the
whole system; on every `mutex_lock` call it checks whether the new
lock class has ever been taken after a class that, somewhere in the
system, has been taken after the new class — that is, it looks for
a cycle in the **lock-class graph**.

```
   lockdep: tracking the order in which classes were taken.
   class graph:
        A -> B   (seen: lock A then lock B)
        B -> C
        C -> A   (CYCLE in the class graph -> report potential deadlock)
```

`lockdep` reports potential deadlocks even when no actual deadlock
has occurred, because it tracks *classes of locks*, not individual
instances. The runtime overhead is significant — on the order of
10% of the kernel's lock-taking cost — and `lockdep` is therefore
not enabled in production kernels; it is a debug-build feature. The
same idea is used in the Rust `parking_lot` deadlock-detector crate,
which the user opt-in enables in test builds.

## Go: goroutine deadlock detection

The Go runtime ships a deadlock detector for goroutines. It tracks
every goroutine that is parked on a channel send/receive or a
`sync.Mutex`/`sync.WaitGroup`. When all goroutines are parked, the
runtime aborts with:

```text
fatal error: all goroutines are asleep - deadlock!

goroutine 1 [chan receive]:
main.main()
        /tmp/foo.go:8 +0x6b
```

The algorithm is: count the number of runnable goroutines (i.e.
goroutines in the runqueue or in a syscall that is expected to
return); if it is zero and no timer is pending and no goroutine is
waiting on a network poll, declare deadlock. This is detection
applied at the language runtime level rather than at the OS level.
It does not catch deadlocks involving goroutines blocked on
external resources (file I/O, C calls), only Go-level
synchronization primitives.

## Comparison to optimistic approaches (CAS)

The CAS-based (compare-and-swap) approach sidesteps the four Coffman
conditions by design: there is no mutual exclusion (any thread can
attempt the CAS), no hold-and-wait (the CAS does not hold any
resource — it reads, computes, and writes atomically), no
preemption issue (the CAS is one instruction), and therefore no
circular wait. The cost is **retry under contention**: when two
threads race on the same atomic, one wins and one's CAS fails; the
loser re-reads, re-computes, and retries. Under heavy contention,
the retry storm can be worse than the lock.

```
   Lock-based critical section       CAS-based critical section
   ----------------------------      ----------------------------
   lock(m);                           loop {
   modify state;                          expected = atomic_load(x);
   unlock(m);                             new_val    = compute(expected);
                                          if (atomic_cas(x, expected, new_val))
   no retry on contention,                break;
   throughput serialised              }
   on the lock.
                                       On contention: many retries.
                                       Under no contention: one atomic.
   Deadlock: possible                  Deadlock: impossible
   Livelock: impossible                Livelock: possible (retry storms)
```

The pragmatic answer, validated across decades of systems code:
**use locks when the critical section is non-trivial or when the
contention is real; use CAS when the critical section is a single
update, when contention is rare, and when the workload is
read-heavy.** Lock-free data structures (see
[Lock-free Data Structures](./lock-free.md)) are not universally
better; they are better in specific situations, and they trade
deadlock for livelock and starvation.

## Interview questions

### What are the four Coffman conditions?

Mutual exclusion, hold-and-wait, no preemption, and circular wait.
All four must hold for deadlock to be possible. Break any one and
deadlock cannot occur.

### What is a safe state in the Banker's algorithm?

A state is safe if there exists an ordering of the processes such
that each process can run to completion using currently available
resources (its remaining need is less than or equal to the
available plus the resources held by earlier processes in the
sequence). The Banker's algorithm admits a request only if the
resulting state is safe.

### What is the wait-for graph and when is a cycle in it a deadlock?

The wait-for graph is a directed graph on processes: edge `P_i -> P_j`
exists if `P_i` is blocked waiting for a resource held by `P_j`. A
cycle is a deadlock when every resource has a single instance
(sufficient and necessary); for multi-instance resources, a cycle is
necessary but not sufficient.

### How does lock ordering prevent deadlock?

If every process acquires locks in increasing global order, the
wait-for graph is a subgraph of a strict partial order; cycles are
impossible. The cost is that lock ordering is a global discipline —
any code that does not follow the order is a bug, and the order is
brittle when the lock set is dynamic.

### What does Java `jstack` actually do?

It walks the JVM's `ObjectMonitor` linked lists to build the
wait-for graph in memory, runs cycle detection, and prints any cycle
it finds, labelling the threads and the monitor addresses involved.
It works for both `synchronized` and `java.util.concurrent.locks`
locks that participate in `AbstractOwnableSynchronizer`.

### Why is `lockdep` not enabled in production?

Because the runtime overhead is roughly 10% of kernel lock-taking
cost — unacceptable for production workloads. `lockdep` is a debug
build feature, run on developer machines and in continuous
integration.

## Cross-references

- [Lock-free Data Structures](./lock-free.md) — the CAS-based
  alternative that avoids deadlock by avoiding mutual exclusion
- [ABA Problem](./aba-problem.md) — the CAS hazard that lock-free
  structures must additionally address
- [Transactional Memory](./transactional-memory.md) — the
  optimistic-concurrency alternative that breaks hold-and-wait
- [Software Transactional Memory](./software-transactional-memory.md)
  — why STM eliminates the Coffman conditions by construction
- [Readers-Writers](./readers-writers.md) — the canonical lock-based
  pattern that needs careful ordering
- [Producer-Consumer](./producer-consumer.md) — the
  condition-variable pattern that is prone to missed wakeups
- [Lock-based Transactions](../dbms/transactions/lock-based.md) —
  two-phase locking and wound-wait/wait-die at the database level
- [Distributed Lock](../interview/system-design/real-world/distributed-lock.md)
  — the same problem across nodes, with the additional failure of
  network partitions

## References

- E. W. Dijkstra. *Cooperating Sequential Processes*. 1965.
  Reprinted in *Programming Languages*, F. Genuys (ed.), Academic
  Press 1968. <https://www.cs.utexas.edu/users/EWD/transcriptions/EWD00xx/EWD123.html>
- E. G. Coffman, M. J. Elphick, A. Shoshani. *System Deadlocks*.
  ACM Computing Surveys 1971.
  <https://dl.acm.org/doi/10.1145/356586.356587>
- Oracle. *jstack — Stack Trace*.
  <https://docs.oracle.com/en/java/javase/21/docs/specs/man/jstack.html>
- Oracle. *ThreadMXBean.findDeadlockedThreads API*.
  <https://docs.oracle.com/en/java/javase/21/docs/api/java.lang.management/javax/management/ThreadMXBean.html#findDeadlockedThreads()>
- Linux kernel: lockdep documentation.
  <https://docs.kernel.org/locking/lockdep-design.html>
- Linux kernel: lockdep troubleshooting and usage.
  <https://www.kernel.org/doc/html/latest/dev-tools/lockdep.html>
- Go runtime source: `runtime/proc.go` deadlock detection
  (`checkdead`).
  <https://github.com/golang/go/blob/master/src/runtime/proc.go>
- Andrew S. Tanenbaum and Herbert Bos. *Modern Operating Systems*,
  5th ed., chapter on Deadlocks. Prentice Hall 2014.
  <https://www.pearson.com/en-us/subject-catalog/p/modern-operating-systems>
- Andrew Birrell. *An Introduction to Programming with Threads*.
  DEC SRC Research Report 35, 1989. (The canonical reference for
  the hold-and-wait removal via try-lock, on which `std::lock` is
  based.) <https://birrell.org/andrew/papers/035-Threads.pdf>
