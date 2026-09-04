# Lock Starvation and Lock Convoying

A lock can be *correct* and still wreck a system. Two failure modes live in
that gap: **starvation**, where some thread's acquire is postponed
indefinitely because the fairness policy keeps letting others through, and
**convoying**, where a lock becomes a scheduler-quantum transfer point and
throughput collapses even though the critical sections are short. Both are
consequences of the same root cause — lock ownership interacts with the
operating system's scheduling — and both have standard industrial cures:
queue-based (ticket/MCS) locks, phase-fair reader-writer locks, and
handoff batching.

The classic starvations of the readers-writers problem are covered in
[Readers-Writers](./readers-writers.md); this page is the systems level:
why fairness is *not* the default, what convoys look like in production
metrics, and what the synchronization primitives inside
[thread pools](./thread-pools.md) and
[concurrent structures](./concurrent-hashmap.md) actually do about it.

## Starvation: when "eventually" never arrives

An acquire is starved if some other acquire with no priority claim is
always served first. The standard generators:

| Source | Mechanism | Example |
|---|---|---|
| Unfair spinlocks (compare-and-swap) | last arrival at the cache line wins the race; cache-locality bias re-selects recent winners | 2-core-pair ping-pong starves a third NUMA node's thread |
| Readers-preference RW locks | read acquisitions overlap freely; a writer waits while readers stream in | hot config cache, one 30 s rebuild blocked forever |
| Priority scheduling + non-preemptive sections | low-priority holder blocks high-priority acquirer while medium-priority threads preempt the holder (priority inversion) | Mars Pathfinder's 1997 resets — the canonical story |
| Condition-variable thundering herd | broadcast wakes everyone; a scheduler's wake order biases the same subset | one slow waiter never wins `pthread_cond_broadcast` |
| Asymmetric workloads on sharded locks | hash skew keeps re-saturating the same stripe | [hot partitions](../dbms/advanced/database-sharding.md) at the DB layer |

Two subtleties separate senior answers from textbook ones:

- **Starvation is probabilistic, not absolute.** An unfair lock gives the
  underdog *some* chance per round; the question is whether the win
  probability decays to effectively zero under the workload's arrival
  pattern. Fairness analysis is therefore queueing analysis (arrival rate
  vs service distribution — see [Little's Law](../queueing-theory/fundamentals.md)),
  not a code-inspection checkbox.
- **Fairness costs throughput.** FIFO handoff forces a context switch per
  acquire (the holder cannot pass to the next waiter before descheduling),
  so perfectly fair locks are slower than unfair ones precisely in the
  low-contention regime where unfairness is harmless. Production locks are
  *bounded-unfair*: cap how many times a newcomer may cut in line
  (Java's `ReentrantLock(fair=true)` vs default, Go's `sync.Mutex` starve
  mode — described below) rather than being strictly FIFO.

## Lock convoying: the quantum-synchronized stampede

The classic convoy (Anderson, Lazowska, Levy, SIGMETRICS 1989 —
[the paper that named it](https://doi.org/10.1145/75372.75378)):

```text
t0  T1 acquires L, holds it across a slow call (I/O, page fault...)
t0  T1's scheduling quantum expires → T1 blocks (not on L — on the CPU)
t1  T2..Tn block on L and are descheduled
t2  T1 runs again, finishes critical section, releases L
t3  The OS wakes T2..Tn *in the same batch* — all runnable at once
t4  T2 acquires L, immediately burns its quantum *holding the lock* on
    non-critical work; T3..Tn block again...
→ the lock now travels one quantum per thread, at context-switch speed,
  regardless of how short the critical section is.
```

The signature in production: **lock hold times that are microseconds in a
microbenchmark appear as milliseconds per holder in production, and
throughput drops to `1 / quantum`-ish multiples while CPU utilization looks
"busy" (all time is scheduling overhead).** The convoy is a *feedback
loop*: waking a batch synchronizes the waiters, and whoever acquires next
inherits the batch plus the quantum boundary — the lock rides the
scheduler instead of the workload.

Cures, in the order they should be considered:

1. **Shrink the critical section below the noise floor.** No I/O,
   allocation, logging, or callback under a contended lock — convoys need
   *long holds* to start; starving them of hold time starves the loop.
2. **Queue-based locks** (below) convert the wake-batch into an ordered
   handoff: exactly one waiter is made runnable per release, killing the
   herd that sustains the convoy.
3. **Batch handoff / delay release**: a releasing holder may keep the lock
   through a bounded grace window (or hand it to a *designated* successor)
   so that the batch of waiters drains in larger, amortized steps.
   Deliberately "unfair" — measured in convoys' aftermath, not before.
4. **Parked-waiter futex/OS primitives** (Linux `futex`, Windows SRW
   locks) implement variations of (2) and (3) internally; most modern
   mutexes already contain the cure, which is why convoys today appear
   mainly in *hand-rolled* spinlocks and in lock-free code where a CAS
   retry loop meets an overloaded scheduler.

## The industrial fix: queue-based locks

Ticket locks and MCS locks replace "race for the cache line" with an
ordered queue — fairness by construction, starvation impossible:

```text
TAS (test-and-set) lock:          Ticket lock:
  everyone spins on one word        each thread takes a number,
  → winner = whoever's cache        spins on its own ticket
    copy is closest                 → FIFO order, bounded unfairness
                                    (still: all spin on one word
                                     for the "now serving" number)

MCS lock (Mellor-Crummey & Scott, 1991):
  each waiter spins on a *local* flag in its own node; the releasing
  thread flips the successor's flag.
  → FIFO + no shared cache-line traffic + O(1) space per waiter
    (Linux kernel qspinlock, many JVM/JDK internals descend from this)
```

The MCS design is the standard citation for "scalable synchronization"
([ACM TOCS 1991](https://doi.org/10.1145/103727.103729)); the empirical
comparisons (TAS vs TTAS vs ticket vs array/queue locks under increasing
processor counts) are in
[Anderson's TPDS study](https://doi.org/10.1109/71.80120). The
interview-relevant summary: **spin on locally-owned memory, hand off
explicitly, and never let release semantics depend on scheduler timing.**

For reader-writer locks the fair analogue is the **phase-fair RW lock**:
readers and writers alternate in epochs, and within a reader phase all
arrived readers enter — bounding writer wait to one phase while keeping
read concurrency. It fixes the [readers-writers starvation variants](./readers-writers.md)
without serializing reads the way writers-preference does.

## What real runtimes do

- **Go `sync.Mutex`**: starts unfair (barging — best throughput at low
  contention); after a waiter waits >1 ms the mutex flips to *starve
  mode* — handoff directly to the queue head, new arrivals queue instead
  of cutting — and flips back when the queue drains. An explicit,
  documented bounded-unfairness controller; the source comments are the
  best short read on the trade.
- **Java `synchronized` / `ReentrantLock`**: biased/thin/fat lock
  escalation in the JVM; `ReentrantLock(fair=true)` costs roughly its
  unfair sibling in throughput at low contention — the Javadoc says
  exactly why, and interviews like hearing it quoted from first
  principles.
- **Linux `futex`-based mutexes and `qspinlock`**: queue-lock + OS-park
  hybrids — waiters park (no spin burning) while the queue preserves
  order; the kernel's own spinlocks moved to qspinlocks for NUMA scale.
- **Datastore layer**: fairness reappears as *lock queues with admission
  control* (SQL Server lock manager grants, InnoDB's
  `innodb_lock_schedule`-style FIFO-first behavior) and as the
  [distributed version](../dbms/internals/btree-latching.md) — latch
  shunning and latch modes exist precisely because a convoy inside a
  buffer-pool latch path multiplies into every query.

## Interview questions

1. **Your service's p99 spikes 100× but CPU is idle-ish and the mutex is
   held 5 µs. What do you check?** Convoy signatures: long effective hold
   = hold time + quantum interactions, wake-batch synchronization
   (trace wakeup timestamps clustering at release), and whether the
   critical section contains blocking work. Then: shrink the section,
   switch to a queue-based/park-based lock, and check for lock-free CAS
   loops under scheduler overload.
2. **Why not make every lock FIFO?** FIFO handoff forces a context switch
   per acquire, so the uncontended and lightly-contended cases — the vast
   majority of lock acquisitions — pay for the pathological case.
   Bounded-unfair designs (barging with a starvation detector, like Go's
   mutex) get both regimes.
3. **How does a reader-writer lock starve writers even with "fair" locking?**
   A reader phase admits overlapping readers indefinitely (each new
   reader arrives before the last leaves). The fix is epoch/phase-based
   admission (phase-fair locks) or reader-count bounded batching —
   fairness must apply to *phases*, not individual acquisitions.
4. **Where does this show up in databases?** Latch convoys on hot pages
   (last-page insert problem → InnoDB's insert-intention handling and
   range sharding both exist to break the convoy), lock-manager grant
   queues under escalation storms, and hot-row update queues — the
   single-resource queueing math in [Lock-based Protocols](../dbms/transactions/lock-based.md)
   is the shared framework.

## Key Takeaways

- Starvation = fairness policy meets arrival pattern; analyze it as
  queueing, and expect the fix (fairness) to cost throughput in the common
  low-contention case — hence bounded-unfair designs.
- Convoying = wake-batch + quantum synchronization turning a short lock
  into a context-switch-speed relay; the cures are short critical
  sections, ordered handoff, and deliberate batching.
- Ticket/MCS queue locks are the reference fix: FIFO by construction,
  local spinning, O(1) waiter space — and the ancestry of futex/qspinlock
  designs in production kernels.
- The same physics appears in databases as latch convoys and lock-grant
  queues; recognizing the convoy signature (high p99, low CPU,
  "slow" microsecond locks) is the transferable skill.

## Cross-References

- [Readers-Writers](./readers-writers.md) — the classic starvation variants and turnstile fixes.
- [Thread Pools](./thread-pools.md) — scheduling context where convoys form.
- [Lock-based Protocols](../dbms/transactions/lock-based.md) — database lock queues and grant ordering.
- [B-Tree Latching](../dbms/internals/btree-latching.md) — latch modes and the last-page-insert convoy.
- [Deadlock Detection](./deadlock-detection.md) — the other failure mode of contended lock graphs.
- [Queueing Theory Fundamentals](../queueing-theory/fundamentals.md) — arrival/service math behind starvation analysis.

## References

- T. Anderson, B. Lazowska, H. Levy, "[The Performance Implications of Thread Management Alternatives for Shared-Memory Multiprocessors](https://doi.org/10.1145/75372.75378)", *SIGMETRICS 1989 / IEEE TPDS* — origin of the lock-convoy analysis.
- J. Mellor-Crummey, M. Scott, "[Algorithms for Scalable Synchronization on Shared-Memory Multiprocessors](https://doi.org/10.1145/103727.103729)", *ACM TOCS* 9(1), 1991 — ticket/array/MCS queue locks.
- T. Anderson, "[The Performance of Spin Lock Alternatives for Shared-Memory Multiprocessors](https://doi.org/10.1109/71.80120)", *IEEE TPDS* 1(1), 1990 — empirical TAS/TTAS/ticket comparisons.
- Go Documentation, "[sync.Mutex — fairness](https://pkg.go.dev/sync#Mutex)" — the documented barging/starve-mode state machine.
- Linux kernel documentation and source, "[qspinlock](https://docs.kernel.org/locking/locktypes.html)" — production queue-lock design notes.
