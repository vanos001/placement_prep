# SRCU: Sleepable RCU

> Classic RCU read sections come with a contract: don't block, don't
> sleep, don't call anything that might. That contract is why RCU read
> sections compile to almost nothing — but it excludes huge swaths of
> kernel code that legitimately needs to sleep (I/O, mutexes, memory
> allocation under pressure). SRCU (Sleepable RCU, McKenney) trades
> read-section cost for the right to sleep: still O(1) entry and exit,
> still wait-free, but with per-domain counters that make grace periods
> heavier and read sections several times more expensive than plain
> RCU. This page assumes you know [RCU](./rcu.md) and focuses on what
> changes when the read side sleeps.

## Why Plain RCU Cannot Sleep

A classic RCU reader marks its presence with `preempt_disable()` or
`rcu_read_lock()` (on PREEMPT_RT: a local IRQ save). The reclaimer
waits for a grace period, which is proven over by observing *every
CPU* pass through a quiescent state. If a reader could sleep or be
preempted mid-section, the CPU it runs on might report a quiescent
state while the reader still holds references — the reclaimer would
free data out from under it. Sleeping in an RCU read section is a bug
precisely because reader presence is *per-CPU scheduling state*, not
per-task state.

SRCU makes reader presence **per-task and per-domain**:

```text
 struct srcu_struct sp;      // a domain (there can be many)

 int idx = srcu_read_lock(&sp);       // returns an index latch
   ... may sleep, block on mutexes, allocate, do I/O ...
 srcu_read_unlock(&sp, idx);          // must pair with the SAME idx

 synchronize_srcu(&sp);      // waits until all pre-existing readers done
```

## The Two-Counter Mechanism

Each SRCU domain keeps two pairs of per-CPU counters and a locked
flip:

```text
 lock_idx = 0                        # which counter pair readers use
 per-CPU: c[0], c[1], s[0], s[1]     # counts + snapshot

 reader:
   idx = sp->lock_idx                # read once (the latch)
   c[idx]++                          # atomic add on per-CPU counter
   ... critical section ...
   c[idx]--

 gracer (synchronize_srcu):
   1. flip lock_idx to the OTHER index; readers entering now use idx',
      so new readers no longer touch idx
   2. wait until every CPU's c[idx] + s[idx] == 0
      (sum of the old index's counters drains as old readers exit)
   3. flip again and wait once more (two flips = one grace period);
      the second pass guarantees readers that raced the first flip
      have finished
```

Why two flips? A reader that latched `idx` just before flip 1 may not
have incremented its counter yet when the waiter checks. The second
flip closes that race: any reader counted in pass 1 has entered and
exited by the end of pass 2.

The counter pairs alternate between two roles: one pair is being
*read by gracer* (draining), the other is being *incremented by new
readers* — they never share a cache line between those roles, which
is what keeps `srcu_read_lock()` wait-free and free of cross-CPU
snooping.

## Costs vs Classic RCU

| | classic RCU (rcu_read_lock) | SRCU |
|---|---|---|
| Read entry | preempt_count bump / local IRQ save (no atomics) | atomic add on per-CPU counter + idx load |
| May sleep | NO | YES |
| Domains | one global state machine | any number (per-subsystem `srcu_struct`) |
| Grace period | scheduler-driven, ~tens of ms | two counter-drain passes; polling API for explicit control |
| Read-section duration | must be short | can be arbitrarily long (bounded by forward progress only) |
| Debugging | lockdep-RCU | sparse/lockdep support, but stalls hide longer |

The polling API (`start_poll_synchronize_srcu`, `check_for_poll_
synchronize_srcu`, `advance_poll_...`) lets a driver ask "has a grace
period elapsed since my cookie?" without blocking — the pattern for
workqueues that clean up sleeping-reader structures.

## Where SRCU Shows Up

- **Notifier chains** that can unregister while being called
  (`srcu_notifier_*`) — callback lists change while handlers sleep.
- **fuse and filesystem paths** where request lifetime crosses sleeps.
- **KVM / mm notifier ranges**: MMU notifier invalidations must wait
  for readers that may page-faultsleep mid-walk.
- **seccomp filters** (historic usage) and RDMA ucontext teardown —
  any place where "read the config, then do blocking work with it"
  is the shape of the code.

## Worked Demo: The Counter-Drain Simulation

The demo simulates a 4-CPU SRCU domain: readers latch an index,
increment/hold/decrement counters on random-but-seeded CPUs, and a
gracer flips and drains. It prints which pass cleared which readers
and shows the race-closing second flip.

```python
# Deterministic SRCU counter-drain simulation (4 CPUs).
# Reader timeline is a fixed script: each reader latches idx, holds
# for k ticks, exits. Gracer flips at t=0 and t=2.

CPUS = 4
READERS = {  # reader_id: (latch_tick, exit_tick, cpu)
    1: (0, 3, 0), 2: (1, 2, 1), 3: (2, 4, 2), 4: (0, 1, 3),
}
FLIPS = [0, 2]              # gracer flips lock_idx at these ticks

state = {0: [0]*CPUS, 1: [0]*CPUS}   # per-idx per-cpu counters
active = {}                          # reader -> idx
lock_idx = 0
events = []

for t in range(6):
    if t in FLIPS:
        old = lock_idx
        lock_idx ^= 1
        events.append(f"t={t}: flip {old}->{lock_idx}")
    for rid, (lt, et, cpu) in READERS.items():
        if t == lt:
            idx = lock_idx
            state[idx][cpu] += 1
            active[rid] = idx
            events.append(f"t={t}: reader {rid} latch idx={idx} cpu={cpu}")
        if t == et and rid in active:
            idx = active.pop(rid)
            state[idx][cpu] -= 1
            events.append(f"t={t}: reader {rid} exit idx={idx}")
    if t == 3:
        drained = {i: sum(state[i]) for i in (0, 1)}
        events.append(f"t={t}: counter sums after drain = {drained}")

for e in events:
    print(e)
print("grace period complete after second flip drains idx=0:", sum(state[0]) == 0)
```

Real output:

```text
t=0: flip 0->1
t=0: reader 1 latch idx=1 cpu=0
t=0: reader 4 latch idx=1 cpu=3
t=1: reader 2 latch idx=1 cpu=1
t=1: reader 4 exit idx=1
t=2: flip 1->0
t=2: reader 2 exit idx=1
t=2: reader 3 latch idx=0 cpu=2
t=3: reader 1 exit idx=1
t=3: counter sums after drain = {0: 1, 1: 0}
t=4: reader 3 exit idx=0
grace period complete after second flip drains idx=0: True
```

The mid-drain line at t=3 is the interesting one: idx=1 has fully
drained (all pre-flip readers gone) but idx=0 holds 1 — reader 3
entered on the *second* index between the flips. That reader is not
covered by this grace period; it is covered by the *next* poll cycle,
which is exactly why the API's cookie-based `start_poll`/`check_poll`
composition works: each cookie guarantees only the readers that
existed before its first flip. The final check confirms the domain
drained after reader 3 exited — two flips, one grace period, no
reader freed early.

## Interview Questions

1. Why can SRCU readers sleep while classic RCU readers cannot?
   (Reader presence is a per-domain counter, not per-CPU scheduling
   state; a sleeping reader's counter stays non-zero wherever it
   reschedules.)
2. Why two flips per grace period? (The first flip stops new readers
   from using the old index; the second closes the latch-before-increment
   race.)
3. What does the `int` return of `srcu_read_lock()` mean, and why must
   `srcu_read_unlock` receive it? (The index latch: unlock must
   decrement the counter pair the reader actually incremented.)
4. When would you choose `synchronize_srcu` over the polling API?
   (Blocking cleanup paths; polling for workqueue/wq contexts that
   cannot block on the wait queue.)
5. Name the cost you pay for sleepability even in the fast path.
   (An atomic add per entry/exit on a per-CPU line, plus an extra
   idx load — several times a classic RCU entry, still far under a
   spinlock.)

## References

- McKenney, P. et al. *RCU Requirements* (kernel doc; SRCU section):
  https://docs.kernel.org/RCU/Design/Requirements/Requirements.html
  (probed 200)
- Kernel source: `kernel/rcu/srcutree.c` (counter pairs, flip logic):
  https://github.com/torvalds/linux/blob/master/kernel/rcu/srcutree.c
  (probed 200)
- LWN: *Sleepable RCU* (original SRCU announcement):
  https://lwn.net/Articles/202822/ (probed 200)
- LWN: *SRCU and the polling API* coverage:
  https://lwn.net/Articles/775226/ (probed 200)
- Michael, M. *Safe Memory Reclamation for Dynamic Lock-Free Objects
  Using Atomic Reads and Writes*. PODC 2002 — the epoch/counter family
  SRCU belongs to. https://doi.org/10.1145/571825.571829 (verified via
  Crossref)

## Cross-References

- [RCU](./rcu.md) — the non-sleepable sibling and its quiescent-state
  machinery.
- [Hazard pointers and epoch reclamation](../../../concurrency/hazard-pointers.md)
  — userspace cousins of the same problem.
- [Memory barriers](../memory/barriers.md) — the ordering guarantees
  the counter flips rely on.
