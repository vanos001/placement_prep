# MCS Locks and the Linux qspinlock

> Spinning on a contended lock is a war against the cache-coherence system.
> Every failed compare-and-swap or every re-read of a "still locked?" word
> generates coherency traffic that scales with the number of waiters, not
> with the critical section. The MCS algorithm (Mellor-Crummey & Scott,
> 1991) is the classic fix: each waiter spins on its own cache line, so
> contention costs O(1) coherency traffic per handoff. Linux's `qspinlock`
> packs that idea into a single 32-bit word — this page works through both.

## Why Test-and-Test-and-Set Still Hurts

The canonical spinlock progression:

1. **TAS** — atomically set the lock word, spin while it stays set. Under
   contention, every spinner's atomic write invalidates every other
   spinner's cache line: O(N) coherency traffic per lock transfer, and no
   fairness (starvation is routine).
2. **TTAS** — spin with plain loads until the lock *looks* free, then one
   CAS. This removes the constant invalidation storm but still bursts:
   all N waiters see the release simultaneously and stampede the CAS,
   and only the cache line owner wins. Traffic per handoff is still
   O(N); fairness is still unbounded.
3. **Ticket locks** — draw a number, spin until `now_serving` matches.
   FIFO-fair, and only one waiter's line is invalidated per handoff. But
   the `now_serving` counter is still a shared hot line every waiter
   polls, and the lock word must be wide enough for two independent
   counters (Linux spent years at 32-bit ticket locks on x86-64).
4. **MCS** — build an explicit FIFO queue of waiters; each waiter spins
   on a *local* flag embedded in its own queue node.

The key property separating MCS from everything before it: after a waiter
enqueues, *no other CPU ever writes or polls its node's `locked` byte
except its predecessor's handoff*. Cache lines settle between handoffs
instead of churning.

## The MCS Algorithm

Each thread locks via a `mcs_node` that lives on its own stack (or in
per-thread TLS) — no allocation inside the lock path:

```text
 mcs_node fields: { locked : byte, next : *mcs_node }

 lock():
     node.locked = 0; node.next = NULL
     pred = xchg(lock_ptr, &node)        # enqueue; returns old tail
     if pred != NULL:
         pred.next = node                # publish self to predecessor
         spin while node.locked == 0     # spin on MY line only
     # now owner

 unlock():
     if lock.next == NULL:
         if cmpxchg(lock_ptr, &self, NULL) == self:
             return                      # nobody behind us: clean release
         spin until lock.next != NULL    # a waiter is mid-enqueue
     lock.next.locked = 1                # hand off: one write, one line
```

Two subtleties deserve emphasis because they show up in every interview
discussion of the algorithm:

- The `xchg` enqueue is atomic, but publishing `pred.next = node` is a
  plain store. That store must complete *before* the successor starts
  spinning forever on a flag the predecessor will never see — hence the
  release semantics (on the unlock path: acquire on the read side).
- The unlock race ("I think the queue is empty, CAS it to NULL while an
  enqueuer is handing me a successor") is resolved by making the enqueuer
  and releaser race on the *same* CAS; the loser of the CAS re-reads
  `next` and hands off.

### Cost Model

| Operation | TAS/TTAS | Ticket | MCS |
|---|---|---|---|
| Lock traffic (N waiters) | O(N) per transfer | O(N) polling shared counter | O(1) per transfer |
| Fairness | none | FIFO | FIFO |
| Node storage | 0 | 0 | one pointer per CPU (or per acquirer) |
| Cache lines touched while waiting | owner's line | owner's line + counter line | *own* line only |

The tradeoff is that MCS needs a node — and in its raw form a lock word
wide enough to hold a pointer (64-bit). Linux wanted FIFO fairness and
O(1) handoff in **four bytes**, which is exactly what `qspinlock` does.

## The Linux qspinlock (x86-64)

`arch_spinlock_t` on x86-64 is a 32-bit word with three fields packed
little-endian:

```text
 31          17 16      8 7        1 0
+--------------+----------+----------+-+
|  reserved    | pending  |  tail     |L|     (logical view)
+--------------+----------+----------+-+
  byte layout:  [3][2]      [1]        [0]
                 tail = cpu_idx << 2 | bit    (tail field is 16 bits)
```

- **bit 0 (`L`)** — the actual "locked" bit. Fast path: a single
  `cmpxchg(0 -> 1)` acquires the lock, exactly like a TTAS fast path.
- **byte 1 (`pending`)** — a "one waiter already waiting" flag. The
  *second* contending CPU sets this byte and spins on the whole word
  without queueing — this preserves the cheap uncontended/2-way case
  that MCS handles badly (MCS pays node-publication overhead even for
  two CPUs).
- **bits 16-31 (`tail`)** — an encoded index `(cpu << 2) | bit` into a
  **per-CPU array of MCS nodes**. Because the index needs only 5 bits
  for CPU number and 2 bits for a per-CPU node array index (4 nodes
  handle nesting: spinlock acquired while holding a spinlock in
  interrupt context, etc.), the whole MCS queue fits in 16 bits — the
  innovation that makes an MCS-style lock fit in one word.

### The Handoff Path

```text
 CPU0: cmpxchg(word: 0 -> 1)               owner
 CPU1: set pending byte, spin              2-way fast path
 CPU2: cmpxchg(tail=encode(cpu2,0)),       becomes queue head,
        read tail -> spin on my node        queue forms
 CPU3: ...appends to tail via xchg...
 CPU0 unlock: clear L
        -> pending byte consumed by CPU1    (still no queue touched)
        -> if no pending waiter: clear tail head entry,
           set successor's node.locked = 1  (single cacheline write)
```

The design goal (documented in the kernel's `qspinlock.h` commentary and
LWN's coverage) is a three-tier lock: uncontended = TTAS, lightly
contended (2-3 CPUs) = pending-bit spinning, heavily contended = MCS
queue. Each tier only pays for itself when reached.

### Paravirtualized Spinning

Under a hypervisor, spinning wastes vCPU slices that the lock holder may
never get scheduled onto. `PV qspinlock` reuses the tail field: before
blocking, the waiter writes a *halt hint* into its node; the unlock path
checks the tail and, if the successor is halted, kicks its vCPU via a
hypercall. This turns the MCS node array into a wait/wakeup channel —
the same 4-byte word carries native and PV behavior.

## Worked Simulation

The demo below simulates TTAS, ticket, and MCS locks on the same
interleaved arrival trace and counts coherency-relevant events
(poll-reads that hit a line owned by another CPU, plus invalidating
writes). It is a cost model, not a cache simulator — the assumptions
(a poll costs one snoop if the line is remote-owned; a handoff write
costs one invalidation) are stated in the code.

```python
# Cost-model comparison of TAS/TTAS-style polling vs ticket vs MCS locks.
# Assumptions (explicit):
#   - a waiter spinning on a REMOTE-owned line generates 1 snoop event
#     per simulated "round" while it waits;
#   - acquiring via a remote write (handoff or CAS win) = 1 invalidation;
#   - MCS waiters spin on their OWN node, whose line they own -> 0 snoops.
# Interleaving: 8 CPUs, each requests the lock once, deterministic order.

N = 8
arrival = list(range(N))          # CPU k issues lock() at round k

def simulate(lock_type):
    events = []                   # (round, cpu, 'snoop'|'handoff')
    # crude but deterministic per-policy loop
    if lock_type in ("TAS", "TTAS"):
        # every unacquired waiter polls the owner's line each round
        held = None
        waiting = []
        for r, cpu in enumerate(arrival):
            waiting.append(cpu)
        r = 0
        order = []
        while waiting:
            r += 1
            if held is None:
                nxt = waiting.pop(0)
                order.append(nxt)
                events.append((r, nxt, "handoff"))
                held = nxt
            for w in waiting:
                events.append((r, w, "snoop"))     # all poll owner's line
            if r % 2 == 0:                         # owner leaves every 2 rounds
                held = None
        return events
    if lock_type == "ticket":
        now_serving = 0
        events = []
        # waiters poll the shared counter line until their turn
        for k in range(N):
            turns_waited = 2 * k - k               # deterministic gap
            for _ in range(max(0, 2 * k - k)):
                events.append((k, k, "snoop"))     # polls shared counter
            events.append((k, k, "handoff"))
        return events
    if lock_type == "MCS":
        events = []
        for k in range(N):
            events.append((k, k, "handoff"))       # single handoff write
            # own-line spin: no snoop events
        return events
    raise ValueError(lock_type)

for lt in ("TAS", "ticket", "MCS"):
    ev = simulate(lt)
    snoops = sum(1 for e in ev if e[2] == "snoop")
    hands = sum(1 for e in ev if e[2] == "handoff")
    print(f"{lt:>7}: snoops={snoops:4d} handoffs={hands:3d} total={snoops+hands}")
```

Real output:

```text
    TAS: snoops=  56 handoffs=  8 total=64
 ticket: snoops=  28 handoffs=  8 total=36
    MCS: snoops=   0 handoffs=  8 total=8
```

The absolute numbers come from the simplified cost model — the point the
demo makes real is the structural gap. TTAS-style polling costs every
waiter one snoop per waiting round (8 CPUs arriving one per round gives
0+1+...+7 = 28 snoops for ticket's shared-counter polls, and 7 rounds x
8 waiters = 56 for TAS's owner-line polls), while MCS generates zero
snoop traffic outside the single handoff write per transfer. On real
hardware the effect is superlinear because snoop traffic itself delays
the handoff the waiters are waiting for — that feedback loop is what
"non-scalable locks are dangerous" measured.

## Interview Questions

1. Why does the MCS node live on the caller's stack, and what happens if
   the lock holder returns from the function that declared the node while
   still holding the lock? (Node lifetime must exceed the critical
   section; the kernel's per-CPU node array exists partly to make this
   misuse impossible.)
2. Where does qspinlock's per-CPU node-array index come from, and why
   are there four nodes per CPU? (Nested acquisitions: task -> interrupt
   -> NMI-style contexts each need their own in-flight node.)
3. Why does qspinlock keep a TTAS fast path at all when MCS is fair?
   (Fairness has overhead: publishing a node costs an atomic + store
   even when no one else ever contends. The pending-bit tier covers the
   common 2-way case without queueing.)
4. Under a hypervisor, what breaks with pure spinning, and how does the
   PV qspinlock variant reuse the MCS structure to fix it?
5. Ticket locks were removed from x86-64 in favor of qspinlock — what
   code-size or semantics issue made the conversion non-trivial? (The
   lock word layout changed; code that bit-packed its own assumptions
   about ticket fields broke, and PV/native variants had to coexist.)

## References

- Mellor-Crummey, J., Scott, M. *Algorithms for Scalable Synchronization
  on Shared-Memory Multiprocessors*. ACM TOCS 9(1), 1991.
  https://doi.org/10.1145/103727.103729 (verified via Crossref)
- Boyd-Wickizer, Z., Zeldovich, N. *Non-scalable Locks are Dangerous*.
  USENIX HotPar '10. (official page bot-walls automated checks:
  https://www.usenix.org/conference/hotpar-10/non-scalable-locks-are-dangerous)
- Michael, M., Scott, M. *Simple, Fast, and Practical Non-Blocking and
  Blocking Concurrent Queue Algorithms*. PODC '96.
  https://doi.org/10.1145/248052.248106 (verified via Crossref — the
  canonical wait-free queue paper, background for the node-publication
  discipline MCS borrows)
- Linux kernel source: `include/asm-generic/qspinlock_types.h`,
  `kernel/locking/qspinlock.c` (field layout, per-CPU node array).
  https://github.com/torvalds/linux/blob/master/kernel/locking/qspinlock.c
  (probed 200)
- LWN: Corbet, J. *MCS locks and qspinlocks*. August 2013.
  https://lwn.net/Articles/590243/ (probed 200)

## Cross-References

- [Sync primitives](./sync-primitives.md) — the survey-level tour of
  futexes, mutexes, rwsems, and where each spinning strategy sits.
- [False sharing](./false-sharing.md) — the coherency-traffic mechanics
  (MESI invalidations) that make MCS's local-line spinning matter.
- [Scheduler internals](./scheduler-internals.md) — what happens when a
  spinner burns its timeslice: `MUTEX_SPIN_ON_OWNER` and vcpu throttling.
