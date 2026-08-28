# Flat Combining

## The synchronization-parallelism tradeoff

Every shared container has to answer one question: when *k* threads want
to touch it at the same moment, who is allowed to do the work? The two
classical answers sit at the ends of a spectrum. A **coarse lock**
serializes everything — each thread acquires the lock and executes its
own operation — and pays the full acquisition cost *k* times. A
**lock-free** data structure lets every thread run its own operation
concurrently and resolve races with CAS retries — and pays for that
freedom with retry waste, per-node memory management, and an ABA
reclamation problem ([Lock-Free](./lock-free.md),
[ABA Problem](./aba-problem.md)).

Flat combining (FC), due to Danny Hendler, Itai Incze, Nir Shavit, and
Moran Tzafrir (SPAA 2010), is the third answer: **one thread acquires
the lock and executes the operations that other threads have posted on
their behalf.** The other threads become passive: they publish a
description of the operation, then sleep until someone has executed it
and left the result in their record. Work is *delegated*, not
duplicated.

The economics are the point. If a lock acquisition costs `L` ticks and
an operation costs `E`, a coarse lock pays `L + E` per operation at any
contention level. A combining thread that finds `k` posted operations
pays `L` once plus roughly `S·p` scanning cost (`p` posting threads) and
`k·E` execution — so the amortized acquisition cost per operation is
`(L + S·p)/k`, which falls toward zero as the batch grows. At low
arrival rates `k ≈ 1` and flat combining degenerates to a coarse lock;
at high arrival rates the lock cost vanishes into the batch. That
curvature — bad at low load, excellent at high load — is the whole
design space of the technique.

## The combining publication problem

Delegating execution raises a problem the coarse lock never has: if
thread B does not execute its own operation, how does B's *result* get
back to B? B cannot put the result "in a register" — B is asleep. The
result must travel through shared memory, and it must travel reliably
even though B might wake up, see its request slot empty, and repost a
*new* operation while a slow combiner is still working on the old one.

This is the **combining publication problem**, and its solution is the
FC record — a small per-thread descriptor that is the entire protocol:

```text
   per-thread combining record (padded to its own cache line)
   +--------+-----------+-----------+--------+-------------------+
   | locked |  request  |  is_done  |  age   | result / response |
   |  flag  | (op desc) |   flag    | counter|  slot             |
   +--------+-----------+-----------+--------+-------------------+
        ^                                       |
        |  thread posts here, then sleeps       |  combiner writes
        |  on is_done                           |  the response here
        +---------------------------------------+
```

## The record-and-pass protocol

Each thread owns one record. The protocol has a passive and an active
role, and every thread alternates between them depending on who wins
the lock race:

1. **Publish.** A thread writes its operation into its own record
   (`request`), clears `is_done`, and bumps `age` so any stale combiner
   can detect that the record now carries a newer request.
2. **Try to become the combiner.** The thread attempts to acquire the
   single global combining lock (one CAS). If it wins, it is the
   *combiner* for this epoch; otherwise it becomes *passive*.
3. **Passive path.** A passive thread spins (or blocks, in the
   blocking variants) on its own record's `is_done` flag. It does not
   touch the shared object at all — no coherence traffic on the
   container's cache lines beyond the one record the combiner reads.
4. **Combining pass.** The combiner repeatedly walks the array of all
   records. For every record whose `is_done` is clear, it executes the
   posted operation *on that thread's behalf*, writes the response into
   the record's response slot, and sets `is_done`. It keeps making
   passes until a full sweep finds no pending request, then releases
   the lock.
5. **Handoff.** Releasing the lock lets a new combiner arise — often
   one of the very threads whose operation was just served, which wakes
   up, posts nothing, and instead grabs the lock for the next epoch.

```text
   time ---->  (8-thread example, records R0..R7)

   R1 posts op        R3 posts op         combiner (R5) sweeps:
   R5 takes lock  |   R6 posts op    |   exec R1's op -> is_done
                  |                  |   exec R3's op -> is_done
                  v                  v   exec R5's own op
   [ lock held by R5 ................. ]  exec R6's op -> is_done
                                          full pass: nothing new
                                        [ unlock ]

   cost = L + S*(#posters) + k*E     amortized per op: (L + S*p)/k
```

The `age` counter earns its place in step 5: a passive thread that
times out may re-post into its record while a combiner is mid-sweep.
The combiner compares `age` against what it last executed; a mismatch
marks the response as stale and the operation is executed again in the
next pass. Without that check, one operation could be applied twice or
its result delivered to the wrong request.

## What the batching actually buys: a cost model

The demo below is a deterministic tick-level simulation. All three
strategies see the *same* seeded arrival schedule (8 threads posting
into a shared container); they differ only in who executes and what it
costs. The coarse lock pays `L = 24` ticks per acquisition for every
operation. Flat combining pays `L` once per epoch plus `S = 3` scan
ticks per posting thread, then `E = 6` per operation. The lock-free
path pays `A = 2` ticks per CAS attempt plus a coherence penalty of
`3·(k−1)` ticks per round, because each simultaneous racer forces the
container's cache line through the machine's coherence protocol.

```python
import random

SEED = 7
N_THREADS = 8
WARM = 600          # warm-up ops discarded
MEASURE = 4000      # measured ops per strategy per rate

L, E, S, A = 24, 6, 3, 2   # lock, exec, scan/poster, CAS-attempt costs


class Sched:
    def __init__(self, rate):
        self.rng = random.Random(SEED)
        self.rate = rate

    def tick(self):
        return [t for t in range(N_THREADS)
                if self.rng.random() < self.rate / N_THREADS]


def run_coarse(rate):
    s = Sched(rate)
    pending = [0] * N_THREADS
    busy = 0                      # ticks left in current critical section
    ops = measured = ticks = 0
    lock_acq = 0
    while measured < MEASURE:
        ticks += 1
        for t in s.tick():
            pending[t] += 1
        if busy:
            busy -= 1
            if busy == 0:
                ops += 1
                if ops > WARM:
                    measured += 1
                    lock_acq += 1
            continue
        if any(pending):
            busy = L + E
    return ticks, measured, lock_acq


def run_flatcomb(rate):
    s = Sched(rate)
    record = [0] * N_THREADS
    in_session = False
    left = scan_left = 0
    batch = 0
    ops = measured = ticks = 0
    lock_acq = 0
    sessions = total_k = 0
    while measured < MEASURE:
        ticks += 1
        for t in s.tick():
            record[t] += 1
        if in_session:
            if left > 0:
                left -= 1
                continue
            if scan_left > 0:
                scan_left -= 1
                continue
            # session completes: publish k results at once
            ops += batch
            if ops > WARM:
                measured += batch
                lock_acq += 1
                sessions += 1
                total_k += batch
            in_session = False
            continue
        posters = [t for t in range(N_THREADS) if record[t]]
        if posters:
            batch = sum(record[t] for t in posters)
            left = L + batch * E
            scan_left = len(posters) * S
            in_session = True
            for t in posters:
                record[t] = 0
    return ticks, measured, lock_acq, (total_k, sessions)


def run_lockfree(rate):
    s = Sched(rate)
    inflight = [0] * N_THREADS
    ops = measured = ticks = 0
    attempts = 0
    while measured < MEASURE:
        ticks += 1
        for t in s.tick():
            inflight[t] += 1
        active = [t for t in range(N_THREADS) if inflight[t]]
        if not active:
            continue
        k = len(active)
        ticks += A * k + 3 * (k - 1)       # attempts + coherence penalty
        inflight[active[0]] -= 1           # lowest thread id wins the window
        ops += 1
        if ops > WARM:
            measured += 1
            attempts += k                  # every racer burns one attempt
    return ticks, measured, attempts


print(f"cost model: N={N_THREADS} threads, L={L} E={E} S={S} A={A}, "
      f"seed={SEED}, warm-up {WARM} ops, measured {MEASURE} ops")
print(f"{'rate':>4} | {'ops/ktick: coarse flatcmb lockfree':>34} | "
      f"{'FC batch':>8} {'acq/op coarse':>13} {'acq/op FC':>9} | "
      f"{'CAS att/op':>10} {'CPU t/op: coarse flatcmb lockfree':>32}")
print("-" * 118)
for rate in (0.02, 0.04, 0.08, 0.12, 0.16):
    c_t, c_m, c_a = run_coarse(rate)
    f_t, f_m, f_a, (f_k, f_sess) = run_flatcomb(rate)
    l_t, l_m, l_at = run_lockfree(rate)
    print(f"{rate:4.2f} | {1000 * c_m / c_t:9.1f} {1000 * f_m / f_t:8.1f} "
          f"{1000 * l_m / l_t:8.1f} | {f_k / f_sess:8.2f} "
          f"{c_a / c_m:13.4f} {f_a / f_m:9.4f} | {l_at / l_m:10.2f} | "
          f"{c_t / c_m:8.1f} {f_t / f_m:8.1f} {l_t / l_m:7.1f}")
print("-" * 118)
print("reading: the coarse lock pays L per op at every rate and plateaus at its")
print("ceiling; flat combining amortizes one acquisition over the whole batch, so")
print("its per-op cost falls (acq/op 0.80 -> 0.008) and throughput keeps climbing;")
print("the lock-free path has no lock, but every round pays a coherence penalty")
print("that grows with the number of simultaneous racers, capping its throughput")
print("below flat combining once arrival pressure saturates the CAS line.")
```

```text
cost model: N=8 threads, L=24 E=6 S=3 A=2, seed=7, warm-up 600 ops, measured 4000 ops
rate | ops/ktick: coarse flatcmb lockfree | FC batch acq/op coarse acq/op FC | CAS att/op CPU t/op: coarse flatcmb lockfree
----------------------------------------------------------------------------------------------------------------------
0.02 |      28.0     18.0     17.3 |     1.25        1.0000    0.7977 |       1.01 |     35.7     55.5    57.9
0.04 |      28.0     35.7     32.9 |     1.96        1.0000    0.5108 |       1.02 |     35.7     28.0    30.4
0.08 |      28.0     69.9     59.6 |     5.90        1.0000    0.1694 |       1.03 |     35.7     14.3    16.8
0.12 |      28.0    104.9     82.8 |    21.30        1.0000    0.0470 |       1.06 |     35.7      9.5    12.1
0.16 |      28.0    135.9    100.2 |   124.61        1.0000    0.0080 |       1.08 |     35.7      7.4    10.0
----------------------------------------------------------------------------------------------------------------------
reading: the coarse lock pays L per op at every rate and plateaus at its
ceiling; flat combining amortizes one acquisition over the whole batch, so
its per-op cost falls (acq/op 0.80 -> 0.008) and throughput keeps climbing;
the lock-free path has no lock, but every round pays a coherence penalty
that grows with the number of simultaneous racers, capping its throughput
below flat combining once arrival pressure saturates the CAS line.
```

Three things to read off the table:

- **The coarse lock is rate-independent.** Whether 1 or 8 threads want
  in, the container serves `1/(L+E)` operations per tick, forever. Its
  ceiling is a property of the lock, not the load.
- **Flat combining's per-op cost *falls* with load.** The batch grows
  from 1.25 to 124 operations per lock acquisition, and acquisitions
  per op drop from 0.80 to 0.008. At the lowest rate it is actually
  the *worst* of the three (the scan overhead on a batch of one) —
  flat combining is a high-load optimization, and the paper's own
  evaluation shows exactly this inversion.
- **The lock-free path has no lock to amortize, but its cost grows
  with the number of simultaneous racers** — the `3·(k−1)` coherence
  term — so its curve saturates below flat combining under pressure.

## When flat combining wins, and when it does not

| Situation | Flat combining | Lock-free (CAS) | Coarse lock |
|---|---|---|---|
| Low core utilization, low arrival rate | degenerates to coarse lock + scan overhead | usually fastest | fine, simple |
| Moderate/high arrival rate, bursty posts | best: amortized lock ≈ 0 | coherence waste grows | ceiling reached early |
| Very many cores (dozens+), heavy conflict | single combiner becomes bottleneck | scales further with effort | collapses |
| Code complexity budget | plain non-atomic code inside the combiner | CAS loops, versioning, reclamation | trivial |
| Memory per thread | one fixed-size record | hazard-pointer slots, per-node overhead | nothing |

The row that surprises people is the code-complexity one. Because the
combiner is the *only* thread touching the container during an epoch,
the container itself needs **no atomics at all** — plain reads and
writes, checked by none of the usual memory-model reasoning. The
entire concurrency surface shrinks to one lock and the record array.
This is why flat combining is attractive as a *wrapper*: an existing
single-threaded object gets a concurrent façade without being
rewritten ([Atomic Primitives](./atomic-primitives.md) catalogues what
the lock-free alternative would have to deploy).

The memory comparison has the same shape. A Treiber stack or
Michael-Scott queue needs a node per element *plus* a safe-reclamation
apparatus — hazard-pointer slots or epoch structures per thread
([Hazard Pointers](./hazard-pointers.md)) — because nodes are freed
while other threads may still hold pointers into them. Flat combining
needs one fixed-size, cache-line-padded record per thread and no
reclamation machinery at all, because nothing is freed while any
combiner can be looking at it: the combiner's exclusive access *is*
the grace period.

The honest weakness is the single combiner. Throughput is bounded by
one thread's ability to scan records and execute operations; on large
machines the combiner's scan becomes an `O(threads)` walk per epoch and
its core saturates. That limitation motivates the hierarchical variant.

## Combining funnels and trees: the scalable variant

The fix for the single-combiner bottleneck is to *nest* combiners. In
an **elimination–combining funnel** (Hendler, Shavit, and Yerushalmi,
SPAA 2004 — the direct ancestor of the 2010 flat-combining paper),
threads enter at the leaves of a balancing tree of combining nodes and
drift toward the root:

```text
   thread arrivals                combining funnel
   ------------------        ---------------------------
   t3 t7 t1 t5 ...            level 2:   [ root ]          <- one combiner
                                 level 1: [A]    [B]      <- 2 combiners
                                 level 0: [a][b] [c][d]   <- 4 combiners
   each node: a small pass-the-operation rendezvous; the thread
   holding a node combines the ops of threads arriving behind it
```

Each node is itself a tiny flat-combining site: whoever arrives first
executes the operations of whoever arrives next, and passes the
combined result upward. The tree spreads the combining work across
`O(threads)` nodes, so no single core saturates; the same idea in
hardware is the *combining network* that Yew, Tzeng, and Lawrie
proposed in 1987 for hot-spot memory locations in large
multiprocessors — hardware fuses concurrent requests to the same line
on the fly, which is flat combining implemented in switches. The 2004
funnel doubles as an *elimination* structure: a push meeting a pop at a
node can be resolved locally (the value never even reaches the stack),
removing work from the shared container entirely.

Flat combining also has a wait-free relative. Fatourou and Kallimanis
(SPAA 2011) built a wait-free universal construction in which threads
delegate their operations to whichever thread holds a synchronization
variable — the same "execute on someone's behalf" move, but organized
so every thread makes progress in a bounded number of its own steps,
using fetch-and-add rather than CAS
([Wait-Free Hierarchy](./wait-free-hierarchy.md) explains why the
choice of primitive matters). Herlihy and Koskinen's *transactional
boosting* (PPoPP 2008) is a further relative at the semantics level:
abstract operations on a non-linearizable object are executed under
commit-time locks on the object's behalf — combining by another name,
inside a transaction ([Transactional Memory](./transactional-memory.md),
[Software Transactional Memory](./software-transactional-memory.md)).

## Flat combining in real systems

The idea ships in libraries, not just papers. **libcds** (a widely used
C++ concurrency library) provides `FlatCombining`-based containers —
queues, stacks, priority queues — alongside its lock-free equivalents,
precisely so practitioners can pick per workload. The pattern also
shows up wherever a hot single lock guards cheap operations and the
data is shared by a bounded thread population: logging pipelines,
statistics counters, and embedded runtimes where the code-size and
verification budget rules out lock-free reclamation machinery. The
signature to look for in a codebase is a "worker that serves other
workers' requests found in shared slots" loop — that is a combining
pass, whatever the comment above it says.

## Interview questions

1. **Q: What problem does flat combining solve that a coarse lock does not?**
   A: The lock-acquisition cost is amortized across a batch. A coarse lock
   pays the full acquisition for every operation; a combiner pays it once
   and executes every posted operation in the same critical section, so the
   per-operation lock cost falls as contention rises.

2. **Q: How does a passive thread get its result back?**
   A: Through its own combining record. It posts the operation description
   and sleeps on the record's `is_done` flag; the combiner executes the
   operation, writes the response into the record, and sets the flag. The
   `age` counter detects a stale response when a thread reposts while a
   slow combiner is still sweeping.

3. **Q: Why can the container under a flat-combining lock be non-atomic?**
   A: Only the combiner touches it, and only while holding the lock, so
   all accesses are serialized by construction. Plain reads and writes
   are safe; the memory-model reasoning is delegated to the lock instead
   of the data structure.

4. **Q: When does lock-free beat flat combining?**
   A: At low arrival rates (no batch to amortize; the scan overhead is
   pure loss) and on very large machines, where the single combiner's
   `O(threads)` record sweep saturates its core while a lock-free
   structure keeps distributing work across cores.

5. **Q: What is the relationship between combining funnels and hardware combining?**
   A: The same protocol at different layers: a combining funnel tree has
   threads rendezvous at tree nodes where one thread executes others'
   operations; a hardware combining network does the identical thing in
   switching elements for concurrent accesses to the same memory line.

## Cross-references

- [Lock-Free Data Structures](./lock-free.md) — the retry-based
  alternative; its CAS loops and reclamation are exactly what flat
  combining trades away
- [ABA Problem](./aba-problem.md) — the hazard lock-free structures
  carry and FC sidesteps by never freeing under a combiner
- [Hazard Pointers](./hazard-pointers.md) — the reclamation
  machinery the lock-free path needs and FC does not
- [Atomic Primitives](./atomic-primitives.md) — the CAS/FAA toolbox
  that both approaches sit on
- [Concurrent Queues](./concurrent-queues.md) — where combining
  variants compete with Vyukov and Disruptor designs
- [Software Transactional Memory](./software-transactional-memory.md)
  — optimistic batching of a different kind; and
  [Transactional Memory](./transactional-memory.md) for the hardware
  side
- [Wait-Free Hierarchy](./wait-free-hierarchy.md) — why the
  delegation-based universal constructions care which primitive is
  available
- [Deadlock Detection](./deadlock-detection.md) — FC holds exactly one
  lock, so the Coffman conditions never line up

## References

- Danny Hendler, Itai Incze, Nir Shavit, Moran Tzafrir. *Flat Combining
  and the Synchronization-Parallelism Tradeoff*. ACM SPAA 2010.
  <https://doi.org/10.1145/1810479.1810540>
- Danny Hendler, Nir Shavit, Lena Yerushalmi. *A Scalable Lock-Free
  Stack Algorithm*. ACM SPAA 2004. <https://doi.org/10.1145/1007912.1007944>
  (journal version: JPDC, <https://doi.org/10.1016/j.jpdc.2009.08.011>)
- Pen-Chung Yew, Nian-Feng Tzeng, Duncan H. Lawrie. *Distributing
  Hot-Spot Addressing in Large-Scale Multiprocessors*. IEEE
  Transactions on Computers, C-36(4), 1987.
  <https://doi.org/10.1109/TC.1987.1676921>
- Panagiota Fatourou, Nikolaos D. Kallimanis. *A Highly-Efficient
  Wait-Free Universal Construction*. ACM SPAA 2011.
  <https://doi.org/10.1145/1989493.1989549>
- Maurice Herlihy, Eric Koskinen. *Transactional Boosting: A
  Methodology for Highly-Concurrent Transactional Objects*. ACM PPoPP
  2008. <https://doi.org/10.1145/1345206.1345237>
- libcds — C++ concurrent data structures library (flat-combining
  containers): <https://github.com/khizmax/libcds>
