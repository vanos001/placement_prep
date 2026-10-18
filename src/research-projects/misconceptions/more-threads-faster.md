# "Adding more threads always improves performance"

## Overview

The claim appears whenever a service is slow and someone proposes the cheapest
visible fix: raise the thread pool size. This page argues the claim is false
as stated, explains the two regimes (more threads help, more threads hurt),
gives Amdahl's law its due, and works the arithmetic of both a blocking-I/O
workload (where the claim is true up to a point) and a contended workload
(where it inverts). The correct formulation: throughput is bounded by the
parallelizable fraction of the work and by the throughput of contention
points, and latency tails degrade before throughput does.

## The Claim, Stated Fairly

The strongest honest form is: "On multicore hardware, throughput scales with
thread count; if 8 threads process 8,000 requests per second, 16 threads
process more, and 64 process much more. Threads are cheap; idle cores are
expensive." This is not ignorance — it is a rule that is genuinely true in the
regime the speaker usually inhabits: services with few threads, low
contention, and lots of waiting on the network or disk.

## Verdict

**False.** Beyond the point where cores are saturated and contention appears,
extra threads add context switches, cache pollution, and lock queueing that
reduce throughput and inflate tail latency; useful parallelism is capped by
the parallelizable fraction of the work.

## Why People Believe It

The kernel of truth has two parts. First, blocking I/O overlap: a thread
waiting on a database holds no CPU, so a second thread genuinely raises
throughput — this is the oldest and most legitimate reason for concurrency.
Second, Amdahl's law does promise speedup as cores grow, as long as the
parallel fraction is large. A program that is 95% parallel shows real gains
from 1 to 2 to 4 threads, and the developer watching those gains extrapolates
a straight line that Amdahl's law itself says must bend.

What the belief misses is that threads are not free and cores are not the only
serialized resource. Every additional thread costs scheduler bookkeeping and
stack memory, evicts useful working set from shared caches, and — when threads
share locks, connections, or queues — spends its time not computing but
waiting in line, where it consumes context switches while producing nothing.

## The Correct Formulation

Amdahl's law: with serial fraction s and c cores, speedup is at most
1 / (s + (1 − s)/c). For s = 0.05 (95% parallel):

| Cores | Speedup |
|---|---|
| 2 | 1.90 |
| 8 | 5.93 |
| 32 | 12.55 |
| 64 | 15.42 |
| ∞ | 20.00 |

Three corrections complete the statement. First, the cap: no amount of
threading pushes that workload past 20×, because 5% of the work is serial.
Second, the contention term Amdahl does not model: if the "parallel" section
shares one mutex or one database connection pool, the effective serial
fraction grows with thread count, and throughput can *fall* as threads are
added. Third, the overhead term: context switches (microseconds of direct
scheduler cost each, plus indirect cost as each switch cools the CPU caches
of the outgoing thread) grow with thread count while useful work does not.

The useful sizing heuristic for a thread pool executing tasks that spend w
time computing and b time blocked is roughly cores × (1 + b/w) — from Brian
Goetz's *Java Concurrency in Practice* — which says: size for waiting, but
cap near the point where the CPU is saturated.

## Where It Breaks

**Blocking-I/O overlap (the claim holds, up to a point).** Each request needs
25 ms of CPU and 100 ms waiting on the database. One thread: a 125 ms cycle,
so 8 requests/second, with the CPU idle 80% of the time. Four threads: 32
requests/second (80% CPU). Five threads: 40 requests/second — the CPU is
100% busy and the database wait is fully overlapped. A sixth thread adds
nothing but scheduler work: the bottleneck moved from waiting to CPU. The
claim was true exactly until the CPU saturated.

**Contention collapse (the claim inverts).** Sixteen threads all need one
mutex held for 1 ms per acquisition. Only one thread holds work at a time; the
other fifteen are parked in the lock queue, being woken and parked again.
Throughput is governed by the lock — about 1,000 acquisitions/second — no
matter whether 16 or 160 threads are queued. Add cache-line ping-ponging on
the lock word and each acquisition gets slower than it was with fewer
competitors. This is the regime the claim cannot survive: more threads made
it slower, not faster.

**Oversubscription.** 10,000 threads each with a 1 MB stack reserve ~10 GB of
address space, and the scheduler burns measurable time just switching between
them. A service tuned from 200 threads to 10,000 typically shows flat
throughput, worse p99 (a ready thread can wait through hundreds of others'
time slices), and a bigger memory bill.

**Tail latency.** Queueing delay grows nonlinearly as utilization approaches
1. Adding threads raises offered concurrency, pushes internal queues toward
saturation, and the 99th percentile response degrades long before mean
throughput moves — the number users actually notice.

## Practical Implications

- For CPU-bound work, size pools near core count; for I/O-bound work, use the
  cores × (1 + b/w) heuristic and find the saturation point by measurement.
- When concurrency demand far exceeds useful thread count, prefer async I/O
  or event loops over thread-per-request.
- Find the actual serialization points (locks, pools, single connections)
  before adding threads; removing a contention point buys more than any pool
  resize.
- Measure p50 and p99 separately when changing concurrency: throughput gains
  can hide tail regressions.
- Go's runtime schedules many goroutines over GOMAXPROCS OS threads for the
  same reason: cheap multiplexed tasks, bounded OS-level parallelism.

## Interview Questions

### Your service uses 8 threads and gets 8,000 requests/second. Why won't 64 threads necessarily give 8× that?

Two caps: Amdahl's serial fraction (for 95% parallel work, the ceiling is
20× regardless of cores) and contention points — shared locks or pools make
the effective serial fraction grow with thread count. Extra threads also add
context-switch and cache pollution overhead, so throughput can actually drop.

### When does adding threads genuinely help, and how do you find the optimal count?

When threads spend time blocked on I/O that overlaps with computation. The
optimum is near cores × (1 + b/w) for tasks with b blocking time and w
computing time, found empirically by sweeping pool size while watching
throughput and p99 — stop when the CPU saturates or the tail degrades.

### A team increased its worker pool from 50 to 500 threads and p99 tripled with no throughput gain. What happened?

The extra threads increased queueing and context switching without adding
CPU capacity or removing the bottleneck. Utilization rose toward saturation
so waiting time exploded (queueing delay is nonlinear near 1), and cache
pollution made each context switch costlier. Fix: revert the pool size and
find the real serialization point.

## Key Takeaways

- Amdahl's law caps speedup at 1/s for serial fraction s: 5% serial means a
  hard ceiling of 20×, forever.
- Contention converts "parallel" threads into a queue; throughput follows the
  lock, not the thread count.
- Threads pay rent: stacks, scheduler time, cache pollution. Rent is paid
  even when no useful work happens.
- The claim is true in exactly one regime — waiting-dominated, uncontended
  work — and the engineering task is to find that regime's edge, not to
  assume it is everywhere.
- Tail latency degrades before mean throughput: concurrency changes must be
  measured at the percentiles users feel.

## Cross-References

- [Follow-up Tree: Mutex to Lock-Free](../followup-tree/mutex-to-lock-free.md)
  — what to do when the mutex is the throughput ceiling
- [Assumptions Hunt: Concurrency and Scheduling](../assumptions-hunt/concurrency-and-scheduling.md)
  — the assumptions behind "threads are cheap"
- [Why-Not Handbook: Concurrency Primitives](../why-not-handbook/concurrency-primitives.md)
  — choosing between threads, pools, and event loops
- [Thread Pools](../../concurrency/thread-pools.md) — sizing and the
  machinery behind the heuristics above
- [Python GIL](../../languages/python/gil.md) — the case where extra OS
  threads add no CPU parallelism at all
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- G. M. Amdahl. *Validity of the Single Processor Approach to Achieving Large
  Scale Computing Capabilities*. AFIPS Spring Joint Computer Conference, 1967.
  <https://dl.acm.org/doi/10.1145/1465482.1465560>
- B. Goetz, T. Peierls, J. Bloch, J. Bowbeer, D. Holmes, D. Lea. *Java
  Concurrency in Practice*. Addison-Wesley, 2006. (Source of the
  cores × (1 + wait/compute) sizing heuristic.)
- The Go Authors. *Package runtime — GOMAXPROCS and scheduler documentation*.
  <https://pkg.go.dev/runtime>
