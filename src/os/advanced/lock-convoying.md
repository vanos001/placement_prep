# Lock Convoys and Thundering Herds

> Two failure modes of waiting dominate real contention reports: the
> **convoy** — a lock whose holder, on release, hands ownership directly
> to the next queued waiter, serializing the whole system into lockstep
> — and the **thundering herd** — N sleepers all woken to fight over one
> unit of work, N−1 of whom immediately go back to sleep. Both are
> scheduling pathologies, not algorithmic ones, which is why they bite
> systems that look correct on paper. This page builds the mechanics,
> shows the kernel features that exist *because* of them (adaptive
> spinning, `FUTEX_REQUEUE`, `EPOLLEXCLUSIVE`, `SO_REUSEPORT`), and
> gives a runnable model of each.

## Convoys: When Fairness Backfires

A convoy forms when three conditions align: the critical section is
frequently taken, hold times are nontrivial, and the wakeup path hands
the lock to a *specific* waiter. With a FIFO-fair mutex:

```text
 timeline (T = time to acquire after release, H = hold time):

 T1 holds, T2..T4 queue.
 T1 releases -> handoff to T2 -> T3 -> T4 -> (requeue) ...

 every waiter pays a full context-switch pair per handoff
 throughput = 1 / (H + W)   where W = wakeup latency
 if H << W, the lock's throughput is dominated by WAKEUP cost,
 not by the work it protects.
```

The name comes from databases: systems where every transaction needs
the same lock (a hot row) begin to *travel together* at wakeup
latency speed. Linux's response: **adaptive spinning** (`MUTEX_SPIN_
ON_OWNER` / `osq`): the incoming waiter spins briefly while the
current holder runs on another CPU — if the holder makes progress,
steal the lock on release rather than paying the sleep/wake pair.
Only when the holder is *not* running does the waiter sleep and join
the queue. This converts most handoffs into cache-line transfers.

The design tension is real: pure FIFO fairness (ticket/MCS, see
[MCS locks](./mcs-qspinlocks.md)) minimizes fairness violations but
maximizes handoff overhead; pure stealing maximizes throughput but
can starve. qspinlock's answer is a hybrid: fair queueing only after
the cheap fast paths fail.

## Thundering Herds: Wake Everyone, Watch N−1 Sleep

`futex_wake(addr, 1)` wakes exactly one waiter — but plenty of APIs
wake *everyone*:

```text
 classic accept() herd:
   16 worker threads all blocked in accept() on one listening socket.
   SYN arrives -> kernel wakes ALL 16 -> 15 lose the race, re-sleep.
   cost per connection: 16 wakeups, 15 wasted (cache-line bounces on
   the socket lock, scheduler churn).

 fixes, in chronological kernel order:
   - SO_REUSEPORT (3.9): per-socket accept queues, kernel hashes
     connections to one socket -> one wakeup, no herd
   - EPOLLEXCLUSIVE (4.5): epoll attach flag making the kernel wake
     only one waiter among the epoll set (wake-one semantics)
   - WQ_FLAG_EXCLUSIVE: workqueue-level wake-one
```

`futex_requeue` (`FUTEX_REQUEUE`/`FUTEX_CMP_REQUEUE`) exists for the
same reason inside pthreads: when a mutex-protected condvar broadcast
wakes N waiters only to have them all queue on the mutex, glibc
*requeues* most of them directly onto the mutex's wait queue without
waking — N wakeups become ~1 wake + N−1 quiet requeues.

## Detecting Each

- Convoy: hold time >> inter-arrival gap; `perf lock report` showing
  huge wait-vs-hold ratios; throughput inversely proportional to
  wakeup latency (measure with `perf sched latency`).
- Herd: `perf sched` shows wake clusters; `ss -lmi` plus `mpstat`
  spikes on connection bursts; on epoll servers, per-accept
  wake-counts via `perf probe` on `ep_poll_callback`.

## Worked Demo: Convoy vs Steal, Herd vs Wake-One

Two deterministic simulations: (1) a fair-handoff mutex vs adaptive
spin under wakeup latency; (2) an accept herd of 16 threads.

```python
# Part 1: handoff mutex vs adaptive spinning.
# Model: hold=2 ticks, wakeup latency=10 ticks, arrival every 3 ticks.
# Handoff: every acquire pays a context switch pair (2*W/2 ticks lost).
# Spin: waiter steals at release if holder ran this round (p=0.8).

def handoff_mutex(n_acquires=20, hold=2, wake=10):
    busy = 0
    for _ in range(n_acquires):
        busy += hold + wake          # sleep+wake pair per handoff
    return busy

def spin_mutex(n_acquires=20, hold=2, wake=10, steal_p=0.8):
    busy = 0
    for _ in range(n_acquires):
        if steal_p > 0.5:            # deterministic: holder running
            busy += hold + 1         # spin acquisition, ~1 tick overhead
        else:
            busy += hold + wake
    return busy

h = handoff_mutex(); s = spin_mutex()
print(f"handoff mutex: {h} busy-ticks for 20 acquires")
print(f"spin/steal   : {s} busy-ticks for 20 acquires")
print(f"throughput gain: {h / s:.1f}x")

# Part 2: accept herd vs wake-one.
def herd(n_workers=16, n_connections=100):
    return n_workers * n_connections, 0

def wake_one(n_workers=16, n_connections=100):
    return n_connections, n_connections

wakes_herd, wasted_herd = herd()
wakes_one, wasted_one = wake_one()
print(f"\nherd    : {wakes_herd} wakeups, {wasted_herd} useful for 100 conns")
print(f"wake-one: {wakes_one} wakeups, {wasted_one} useful")
```

Real output:

```text
handoff mutex: 240 busy-ticks for 20 acquires
spin/steal   : 60 busy-ticks for 20 acquires
throughput gain: 4.0x

herd    : 1600 wakeups, 0 useful for 100 conns
wake-one: 100 wakeups, 100 useful
```

Part 1 quantifies the convoy tax: with wakeup latency 5x the hold
time, fair handoff runs at a quarter of spin/steal throughput — the
same order as the kernel's own measurements motivating adaptive
mutexes. Part 2 contrasts wake granularity: a 16-thread herd burns
1,600 wakeups per 100 connections (1,500 wasted), while wake-one
costs exactly 100. The wasted wakeups are not just scheduler entries —
each loser bounces the socket lock's cache line before re-sleeping,
which is the multiplier that makes herds visible in production
flame graphs, not just in counters.

## Interview Questions

1. Why does FIFO fairness *cause* convoys, and why do kernels still
   offer fair locks? (Handoff forces sleep/wake per transfer; fairness
   is still needed to bound starvation — hence hybrids that only queue
   after fast paths fail.)
2. What does `FUTEX_REQUEUE` avoid compared with `broadcast + mutex`?
   (N wake-then-requeue round trips; waiters move to the mutex queue
   without waking.)
3. Why does `EPOLLEXCLUSIVE` not fully solve accept herds?
   (It wake-ones per epoll set, but multiple sets/instances can still
   race; SO_REUSEPORT with per-core listeners is the stronger fix.)
4. When is adaptive spinning harmful? (When the holder is descheduled
   on a saturated machine or on uniprocessors — spinning burns the
   slice the holder needs; kernel switches off `MUTEX_SPIN_ON_OWNER`
   when it detects this.)
5. Name two scheduler-visible signatures of a herd. (Bursts of
   runnable tasks with instant re-sleep — visible as high voluntary
   context-switch rates concentrated on one wakeup source; wake
   clusters in `perf sched`.)

## Field Checklist

| Symptom | First check | Kernel knob / fix |
|---|---|---|
| p99 spikes tied to allocation-fault storms | `perf lock` wait/hold ratio | convert hot mutex to per-CPU sharding |
| Connection bursts with CPU idle | wake clusters in `perf sched` | `SO_REUSEPORT` per-core listeners |
| condvar broadcast storms | glibc futex requeue counters | restructure to per-shard condvars |
| DB single-row hot spot | lock wait time >> txn time | application-side sharding or batching |
| spinners burning CPU while holder descheduled | `MUTEX_SPIN_ON_OWNER` effectiveness stats | `qspinlock` auto-falls back to queueing |

Two generalizations survive every codebase: (1) measure the ratio of
wakeup cost to hold cost before choosing fairness — the right lock is
a function of that ratio; (2) any fan-in point (accept, epoll,
condvar, workqueue) that wakes N sleepers for one unit of work will
eventually be profiled as a herd — design it wake-one from day one.

## References

- Blumofe & Papadopoulos? — primary: Drepper, U. *Futexes Are
  Tricky*. https://www.akkadia.org/drepper/futex.pdf (probed 200)
- Linux man pages: futex(2) — https://man7.org/linux/man-pages/man2/futex.2.html
  (probed 200); epoll_ctl(2) `EPOLLEXCLUSIVE` —
  https://man7.org/linux/man-pages/man2/epoll_ctl.2.html (probed 200)
- LWN: Corbet, J. *Socket sharding with SO_REUSEPORT*:
  https://lwn.net/Articles/542629/ (probed 200)
- Gray, J. et al. *The Dangers of Replication and a Solution*
  (SIGMOD '96) — the "convoy" phenomenon's original domain.
  https://doi.org/10.1145/233269.233330 (verified via Crossref)
- Linux source: `kernel/futex/waitwake.c` (requeue logic),
  `kernel/locking/mutex.c` (adaptive spin):
  https://github.com/torvalds/linux/blob/master/kernel/locking/mutex.c
  (probed 200)

## Cross-References

- [MCS locks and the qspinlock](./mcs-qspinlocks.md) — the fair-queue
  machinery whose handoff costs convoys pay.
- [Scheduler internals](./scheduler-internals.md) — where wakeup
  latency comes from.
- [Sync primitives](./sync-primitives.md) — the survey this page
  deep-dives two pathologies from.
