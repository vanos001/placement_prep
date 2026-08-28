# rt_mutex Internals: PI Chain Walks and PI Futexes

Every sleeping lock in the kernel that offers priority inheritance boils
down to one file: `kernel/locking/rtmutex.c`. Mutexes on a `PREEMPT_RT`
kernel, `spinlock_t` after the RT conversion, and PI futexes exposed to
user space all delegate their contended slow path to the same waiter tree
and the same chain-walk algorithm. Companion pages cover the contracts
around it: [mutex design](./mutex-design.md) compares mutex vs rt_mutex
policy, [spinlocks](./spinlocks.md) lists which lock types change under
RT, [futexes](./futex.md) gives the syscall surface, and
[real-time scheduling](../processes/realtime-scheduling.md) defines the
priority domains PI must respect.

## The problem the walk solves

A low-priority task L holds lock X, high-priority H blocks on X, and now
any medium-priority task M can preempt L indefinitely. L cannot run to
release X, so H's worst-case wait depends on unrelated M tasks - unbounded:

```text
  time --->
  H:  .....[ acquire X ]........ blocked ...........................
  L:  [ acquire X ][-- preempted by M, holds X the whole time --]
  M:              [run][run][run][run][run][run][run][run][run]
                   ^ H's bound = sum of all M runs: unbounded
```

The 1997 Mars Pathfinder resets made this failure mode famous: a
low-priority meteorological task held a mutex the high-priority bus
manager needed, medium-priority tasks starved the holder, and a watchdog
reset the box. The fix flown to Mars was priority inheritance: while H
blocks on X, L runs at H's priority, so inversion becomes bounded by the
length of L's own critical section.

## The data model

```c
struct rt_mutex_base {
    raw_spinlock_t        wait_lock; /* guards owner + waiters        */
    struct rb_root_cached waiters;   /* prio-ordered blocked tasks    */
    struct task_struct   *owner;     /* low bit = RT_MUTEX_HAS_WAITERS */
};

struct rt_mutex_waiter {
    struct rt_waiter_node  tree;     /* node in lock->waiters          */
    struct rt_waiter_node  pi_tree;  /* node in owner->pi_waiters      */
    struct task_struct    *task;
    struct rt_mutex_base  *lock;
    unsigned int           wake_state; /* TASK_NORMAL or TASK_RTLOCK_WAIT */
    struct ww_acquire_ctx *ww_ctx;
};
```

- **Owner pointer packing.** `owner` is a task pointer whose bit 0 is
  `RT_MUTEX_HAS_WAITERS`; acquire, release, and waiter-enqueue interleave
  through a single `cmpxchg`/`xchg` on this word, so the flag always
  matches the tree contents seen under `wait_lock`.
- **Two trees per waiter.** A blocked task must be findable both as "who
  waits on lock X" (`tree`) and as "what boost task T carries"
  (`pi_tree`, in the owner's `pi_waiters` rbtree guarded by `pi_lock`).
  Each node keeps its own sort-key copy (`prio`, `deadline` - EDF waiters
  win ties) because the trees are locked independently.
- **Waiter structs are stack-allocated** by the blocked task: no shared
  allocation, no reclaim problem - but that is why the futex variant
  needs care: the waiter must vanish when the task is signaled or killed
  (see the CVE case study). `task_struct` carries the other half: a
  `pi_waiters` rbtree, a `pi_top_task` cache, and the `prio` field the
  walk rewrites.

## The chain walk: rt_mutex_adjust_prio_chain()

When H fails the fast path and blocks on X owned by L,
`task_blocks_on_rt_mutex()` enqueues H's waiter and starts the walk at L:

```text
  owner = L;  lock = X
  repeat
    top = max(lock->waiters)         # highest-prio waiter of this lock
    if top is none: break            # lock released meanwhile
    if owner->prio >= top->prio: break  # no change -> stop
    boost owner->prio = top->prio    # requeue owner in pi trees
    lock = owner->blocked_on
    if lock is none: break           # owner runnable -> propagation ends
    owner = owner_of(lock)
  until depth cap or cycle detected
```

- **Monotone stop.** The walk continues only while a boost changes
  something, so work is O(chain length), not O(system state).
- **Deadlock detection rides the walk**: if the initiating task reappears
  as an owner in its own chain, the walk returns `-EDEADLK`. With
  `CONFIG_DEBUG_RT_MUTEXES=y` detection is always on; otherwise callers
  select it via `chwalk` flags.
- **Deboost is the mirror image.** `rt_mutex_slowunlock()` calls
  `mark_wakeup_next_waiter()`: the top waiter becomes the pending owner
  on a wake queue, then the releaser recomputes its effective priority
  from its remaining `pi_waiters`. Hand-off means the new owner never
  re-contends the lock word - a woken high-priority waiter does not lose
  the race it already won.
- **The wake queue knows the lock kind.** `struct rt_wake_q_head` carries
  an extra `rtlock_task` pointer: RT spinlock waiters sleep in
  `TASK_RTLOCK_WAIT` and are woken differently from `TASK_NORMAL`
  sleepers, so one wake queue serves both.

```text
  Boost propagation through a 2-lock chain (H=98, M=50, L=10):

  H --blocks on--> [M1] owned by M --blocks on--> [M2] owned by L

  step 1: H blocks on M1          step 2: M's boost propagates
          M.eff 50 -> 98                  L.eff 10 -> 98
  M1.waiters: {H:98}              M2.waiters: {M:98}
  L runs at 98 -> releases M2 -> hands to M -> releases M1 -> hands to H
```

The cost model is why PREEMPT_RT can sleep inside "spinlocks" and still
meet latency budgets: the slow path does O(chain length) work under
`wait_lock`/`pi_lock`, and chains stay short in practice. The
pathological case is prevented, not optimized: depth cap plus cycle
detection turns an attacker-controlled chain into `-EDEADLK` instead of
an unbounded per-acquisition tax.

## How PREEMPT_RT leans on it

Under `CONFIG_PREEMPT_RT`, `spinlock_t` and `rwlock_t` compile into
rt_mutex wrappers (`rt_spin_lock`) with deadlock detection off, sleeper
state `TASK_RTLOCK_WAIT`, and - the entire point - a preemptible
acquired section: IRQ handlers that would have disabled preemption for
milliseconds run as schedulable threads. See [spinlocks](./spinlocks.md)
for the lock-type matrix and [local locks](./local-lock.md) for the
`local_lock`/`migrate_disable` alternative where sleeping would be wrong
even on RT. Because `mutex` on an RT kernel is also an rt_mutex, PI
becomes effectively kernel-wide: the
[mainline PREEMPT_RT merge](../../embedded/realtime.md) (complete for
x86-64, arm64, and riscv with Linux 6.12) did not add a new lock type;
it made this code the default slow path for everything.

## PI futexes: the user-space protocol

`futex(2)` with `FUTEX_LOCK_PI` / `FUTEX_UNLOCK_PI` exposes the same
machinery to user space, with one twist: user space owns the fast path.
The shared 32-bit futex word is laid out by
`include/uapi/linux/futex.h`:

| Bits | Mask       | Field      | Meaning                            |
|------|------------|------------|------------------------------------|
| 0-29 | 0x3fffffff | TID        | kernel tid of current owner        |
| 30   | 0x40000000 | OWNER_DIED | robust owner exited without unlock |
| 31   | 0x80000000 | WAITERS    | at least one waiter exists         |

```c
/* fast path: grab ownership if the word is unlocked */
if (atomic_cmpxchg(uaddr, 0, gettid()) == 0)
    return 0;                        /* acquired, no kernel entry */
futex(uaddr, FUTEX_LOCK_PI, ...);    /* slow path */
```

The `futex_lock_pi` slow path: the kernel validates the TID against a
live task, sets `WAITERS`, and retries the cmpxchg to close the
lost-wakeup window; the caller attaches a kernel-side waiter and
*proxies* it (a PI futex is not a kernel rt_mutex object, so the futex
code fabricates the owner/waiter relationship the chain walk expects);
the walk boosts the owner; `FUTEX_UNLOCK_PI` requires ownership
(otherwise `-EPERM`) and hands the lock to the top waiter kernel-side.
`FUTEX_CMP_REQUEUE_PI` moves waiters between two PI futexes and hands
the lock to at most one of them - how glibc implements
`PTHREAD_PRIO_INHERIT` condvar broadcast without thundering-herd
re-boosts. Robust futexes add the `OWNER_DIED` bit plus a
user-registered robust list: if the owner exits with the word still set,
the kernel marks it on exit and the next locker recovers instead of
hanging forever.

The simulator below replays a three-task, two-lock scenario: fast path,
contended slow path with a depth-2 chain walk, wrong-owner unlock,
hand-off, and deboost.

```python
#!/usr/bin/env python3
"""PI-futex simulator: FUTEX_LOCK_PI / FUTEX_UNLOCK_PI state machine.

Futex word (include/uapi/linux/futex.h): bits 0-29 owner TID (0x3fffffff),
bit 30 OWNER_DIED (0x40000000), bit 31 WAITERS (0x80000000). Contended
LOCK_PI sets WAITERS, blocks on an rt_mutex waiter, and the chain walk
boosts the owner; UNLOCK_PI hands off to the top waiter and deboosts the
releaser. Priorities are SCHED_FIFO 1..99, higher wins. A task seen twice
in the walk is an ownership cycle, i.e. -EDEADLK (depth capped like the
kernel's max_lock_depth=1024)."""

FUTEX_WAITERS, FUTEX_TID_MASK = 0x80000000, 0x3FFFFFFF


class Task:
    def __init__(self, tid, base):
        self.tid, self.base, self.eff = tid, base, base
        self.blocked_on = None      # futex waited on (or None)
        self.holds = []

    def __repr__(self):
        return "T%d(prio=%d)" % (self.tid, self.base)


class PiFutex:
    def __init__(self, name):
        self.name, self.word, self.waiters = name, 0, []

    def top_waiter(self):
        return max(self.waiters, key=lambda t: t.eff) if self.waiters else None

    def owner(self, tasks):
        return next((t for t in tasks if t.tid == self.word & FUTEX_TID_MASK), None)


def decode(word, tasks):
    if word == 0:
        return "unowned"
    owner = next((t for t in tasks if t.tid == word & FUTEX_TID_MASK), None)
    tag = repr(owner) if owner else "T%d" % (word & FUTEX_TID_MASK)
    return tag + (" WAITERS=True" if word & FUTEX_WAITERS else "")


def chain_walk(tasks, owner, lock, log):
    """rt_mutex_adjust_prio_chain(): boost owner to its top waiter, then
    follow owner.blocked_on; a task seen twice is a cycle (-EDEADLK)."""
    seen = set()
    while owner is not None:
        if owner in seen:
            log.append("  chain walk -> EDEADLK: %r re-enters chain" % owner)
            return False
        seen.add(owner)
        top = lock.top_waiter()
        if top is None or owner.eff >= top.eff:
            log.append("  walk stop: %r eff=%d (depth %d)" % (owner, owner.eff, len(seen)))
            return True
        log.append("  boost   %r %d -> %d (top waiter on %s)"
                   % (owner, owner.eff, top.eff, lock.name))
        owner.eff = top.eff
        lock = owner.blocked_on
        if lock is None:
            log.append("  walk ends: %r unblocked (depth %d)" % (owner, len(seen)))
            return True
        owner = lock.owner(tasks)
    return True


def lock_pi(tasks, f, task, log):
    if f.word & FUTEX_TID_MASK == task.tid:
        log.append("  EDEADLK: %r re-locks %s" % (task, f.name))
        return
    if f.word == 0:                              # fast path: cmpxchg TID in
        f.word, _ = task.tid, task.holds.append(f)
        log.append("  fast path: %r takes %s, word=0x%08x" % (task, f.name, f.word))
        return
    f.word |= FUTEX_WAITERS                      # slow path
    task.blocked_on = f
    f.waiters.append(task)
    log.append("  slow path: %r blocks on %s, word=0x%08x" % (task, f.name, f.word))
    chain_walk(tasks, f.owner(tasks), f, log)


def unlock_pi(tasks, f, task, log):
    if f.word & FUTEX_TID_MASK != task.tid:
        log.append("  %s %r UNLOCK_PI -> EPERM (owner is T%d)"
                   % (f.name, task, f.word & FUTEX_TID_MASK))
        return
    top = f.top_waiter()
    if top is None:                              # plain release
        f.word = 0
        task.holds.remove(f)
        log.append("  %s %r unlocks, word=0 (no waiters)" % (f.name, task))
        return
    f.word = top.tid | (FUTEX_WAITERS if len(f.waiters) > 1 else 0)
    task.holds.remove(f)
    task.eff = task.base                         # deboost to static prio
    f.waiters.remove(top)
    top.blocked_on = None                        # pending owner resumes
    top.holds.append(f)
    log.append("  %s %r unlocks, hand-off to %r, word=0x%08x"
               % (f.name, task, top, f.word))
    if f.waiters:
        chain_walk(tasks, top, f, log)


def main():
    A, B, C = Task(11, 98), Task(22, 50), Task(33, 10)  # SCHED_FIFO prios
    M1, M2 = PiFutex("M1"), PiFutex("M2")
    tasks, log = [A, B, C], []
    ops = [
        ("1. C(10)   LOCK_PI M2",               lambda: lock_pi(tasks, M2, C, log)),
        ("2. B(50)   LOCK_PI M1",               lambda: lock_pi(tasks, M1, B, log)),
        ("3. B(50)   LOCK_PI M2 (contended)",   lambda: lock_pi(tasks, M2, B, log)),
        ("4. A(98)   LOCK_PI M1 (contended)",   lambda: lock_pi(tasks, M1, A, log)),
        ("5. A(98)   UNLOCK_PI M2 (not owner)", lambda: unlock_pi(tasks, M2, A, log)),
        ("6. C(->98) UNLOCK_PI M2",             lambda: unlock_pi(tasks, M2, C, log)),
        ("7. B(->98) UNLOCK_PI M1",             lambda: unlock_pi(tasks, M1, B, log)),
        ("8. B(50)   UNLOCK_PI M2",             lambda: unlock_pi(tasks, M2, B, log)),
        ("9. A(98)   UNLOCK_PI M1",             lambda: unlock_pi(tasks, M1, A, log)),
    ]
    for label, fn in ops:
        print(label)
        fn()
        while log:
            print(log.pop(0))
    print()
    print("word decode: 0x80000021 -> %s" % decode(0x80000021, tasks))
    print("word decode: 0x00000016 -> %s" % decode(0x00000016, tasks))
    print("final effective priorities: A.eff=%d B.eff=%d C.eff=%d"
          % (A.eff, B.eff, C.eff))


if __name__ == "__main__":
    main()
```

```text
1. C(10)   LOCK_PI M2
  fast path: T33(prio=10) takes M2, word=0x00000021
2. B(50)   LOCK_PI M1
  fast path: T22(prio=50) takes M1, word=0x00000016
3. B(50)   LOCK_PI M2 (contended)
  slow path: T22(prio=50) blocks on M2, word=0x80000021
  boost   T33(prio=10) 10 -> 50 (top waiter on M2)
  walk ends: T33(prio=10) unblocked (depth 1)
4. A(98)   LOCK_PI M1 (contended)
  slow path: T11(prio=98) blocks on M1, word=0x80000016
  boost   T22(prio=50) 50 -> 98 (top waiter on M1)
  boost   T33(prio=10) 50 -> 98 (top waiter on M2)
  walk ends: T33(prio=10) unblocked (depth 2)
5. A(98)   UNLOCK_PI M2 (not owner)
  M2 T11(prio=98) UNLOCK_PI -> EPERM (owner is T33)
6. C(->98) UNLOCK_PI M2
  M2 T33(prio=10) unlocks, hand-off to T22(prio=50), word=0x00000016
7. B(->98) UNLOCK_PI M1
  M1 T22(prio=50) unlocks, hand-off to T11(prio=98), word=0x0000000b
8. B(50)   UNLOCK_PI M2
  M2 T22(prio=50) unlocks, word=0 (no waiters)
9. A(98)   UNLOCK_PI M1
  M1 T11(prio=98) unlocks, word=0 (no waiters)

word decode: 0x80000021 -> T33(prio=10) WAITERS=True
word decode: 0x00000016 -> T22(prio=50)
final effective priorities: A.eff=98 B.eff=50 C.eff=10
```

Read the trace against the invariants: op 4 pushes 98 through two owners
in one walk call; op 5 shows the kernel refusing a non-owner unlock;
ops 6-7 show hand-off to the boosted top waiter and deboost-to-static
only at release. The word decodes are real trace states (`0x80000021` =
owner T33 with WAITERS; `0x00000016` = owner T22).

## Case study: CVE-2014-3153

The 2014 futex PI bug (the "Towelroot" primitive on Android) came from
`FUTEX_CMP_REQUEUE_PI` requeuing waiters in a way that corrupted the
rt_mutex waiter/owner wiring while the chain walk still relied on it,
yielding a controlled kernel write primitive. Thomas Gleixner's fix
series restructured the PI code so every requeue path re-validates the
proxy waiter state under the proper locks: the invariant "a waiter's
rt_mutex pointer always describes a real blocked-on relationship" became
enforced by construction. The lesson generalizes: anything reaching into
the waiter trees must re-establish the chain-walk preconditions, or the
walk itself becomes the exploit primitive.

## Pitfalls

- **PI only helps if priorities are comparable.** Boosting a
  `SCHED_OTHER` holder to an RT waiter's priority does nothing across
  scheduling classes; keep contended lock users in comparable domains.
- **A stale TID in the word wedges the protocol.** If an owner misses
  `UNLOCK_PI` on some exit path, the next acquirer's kernel validation
  fails; robust lists cover process death, not logic bugs.
- **`-EDEADLK` is contract, not crash**: re-locking a PI mutex in the
  same thread, or an ownership cycle, returns `-EDEADLK`.
- **The walk runs under `wait_lock`/`pi_lock`** - fine for short chains,
  which is one more reason lock-order design (see
  [lock ordering](./lock-ordering.md)) still matters on RT kernels, and
  why [ww mutexes](./ww-mutex.md) resolve deadlocks through their own
  `ww_acquire_ctx` instead of confusing the PI walk.

## References

- [rt-mutex-design: The rt-mutex design document (kernel.org)](https://docs.kernel.org/locking/rt-mutex-design.html)
- [rt-mutex: RT-mutex subsystem documentation (kernel.org)](https://docs.kernel.org/locking/rt-mutex.html)
- [futex(2) man page (man7.org)](https://man7.org/linux/man-pages/man2/futex.2.html) - FUTEX_LOCK_PI word layout and error semantics
- [Exploit write-up: the Linux futex vulnerability, CVE-2014-3153 (Cloud Foundry Foundation)](https://www.cloudfoundry.org/blog/cve-2014-3153/)
- [include/uapi/linux/futex.h (torvalds/linux on GitHub)](https://github.com/torvalds/linux/blob/master/include/uapi/linux/futex.h) - word masks used by the simulator
