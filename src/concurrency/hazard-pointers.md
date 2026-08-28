# Hazard Pointers: Lock-Free Reclamation Without a Grace Period

Lock-free data structures have an embarrassing secret: unlinking a node is
the easy part. The hard part is knowing when it is safe to `free()` it,
because some other thread may have *just* loaded a pointer to that node and
not yet dereferenced it. RCU solves this with grace periods and whole-system
quiescence; hazard pointers (Michael, 2004) solve it per-object: each reader
publishes the exact pointer it is about to dereference into a shared slot,
and a reclaimer frees a retired node only after proving no slot names it.
This page builds the two dominant user-space schemes - hazard pointers and
epoch-based reclamation - on one worked trace, so the retention trade-offs
are visible instead of hand-waved.

Sibling treatments: the kernel's take on the same problem is
[RCU](./rcu.md) (and its [kernel-side implementation](../linux/kernel/sync/rcu.md), which add scheduler and memory-barrier
machinery user-space schemes do not need). Hazard pointers appear
everywhere modern lock-free libraries ship - Folly, liburcu, Java's
`VarHandle`-based libraries, .NET's `ConcurrentDictionary` internals.

## Why reclamation is the actual problem

Consider the canonical Treiber stack `pop()`:

```text
  loop:
    head = atomic_load(S)
    if head == NULL: return EMPTY
    next = head->next                     # (1) dereference AFTER the load
    if CAS(S, head, next): return head    # (2) this thread "owns" head
```

Between (1) and (2), any number of competing poppers can win their own CAS,
unlink `head`, and free it. When this thread reaches `head->next` it may be
reading freed memory - and with allocator reuse, reading a *newly allocated
different node* that happens to live at the same address. The second effect
is the **ABA problem**: the CAS at (2) compares only the pointer value, and
a recycled address makes stale state look current. Reclamation strategy and
ABA mitigation are therefore entangled: delayed reclamation (RCU, epochs,
hazards) starves ABA of its raw material - reuse - and tagged pointers or
double-word CAS mop up the rest.

## Hazard pointers: publish, validate, defer

Each thread owns `H` shared slots (one is enough for most structures). The
read side of every dereference becomes:

1. **Publish**: store the candidate pointer into your slot (release store).
2. **Validate**: re-read the structure's head and confirm it still equals
   the published pointer; if not, retry with the new head.
3. **Read**: dereference safely - a concurrent reclaimer will see your slot.
4. **Clear**: remove the publication when done.

The reclamation side: unlink a node, **retire** it onto a per-thread list;
every `R` retirements, scan *all* threads' slots; free only nodes no slot
names; keep the rest. Two properties make this attractive:

- **Retention is exactly per-object.** A stalled reader holds back the one
  node it published - nothing else. The demo below makes this vivid.
- **Bounded waste.** With `N` threads and `H` slots, at most `N*H + (R-1)`
  nodes are ever unreclaimable, independent of how long any reader stalls.
  That worst-case guarantee is the paper's central result.

The cost is the validate step: an extra atomic re-read per traversal hop,
and the retry loop that goes with it. Traversals that race heavily with
mutators re-publish repeatedly. This is why several production libraries
default to epochs and use hazards selectively.

## Epoch-based reclamation: pay O(1), retain by epoch

Fraser's scheme (2004 thesis) inverts the bargain. Readers **pin** the
current global epoch for the duration of their access (one atomic load,
zero per-object work). Updaters retire nodes into per-epoch buckets; a
bucket is freed when the *global minimum* pinned epoch moves past it - in
practice, after three epochs advance with no reader pinned to the old one.

- Publish cost: O(1) per *critical section*, not per object.
- Retention: **per-epoch.** One stalled reader pins its epoch and holds
  back everything retired while it was pinned - potentially unbounded
  memory if the stall is pathological.
- No validate step: no re-reads, no retries on the read path.

The two schemes sit at opposite ends of a retention-vs-cost axis, and the
right choice depends on which failure mode hurts your workload more.

| dimension            | hazard pointers                 | epoch-based reclamation       | kernel RCU                      |
|----------------------|---------------------------------|-------------------------------|----------------------------------|
| publish cost         | store + validate per object     | one pin per critical section  | rcu_read_lock (often free)       |
| reclamation trigger  | scan all slots every R retires  | epoch advance                 | grace period (sched/timers)      |
| stalled reader cost  | holds back its published nodes  | holds back its whole epoch    | holds back the grace period      |
| worst-case waste     | N*H + R-1 (bounded)             | unbounded with a stall        | unbounded with a stall           |
| ABA mitigation       | inherent (no reuse while published) | none inherent             | none inherent                    |

## The demo: one trace, two engines

The script below runs one deterministic Treiber-stack schedule (12
operations, 3 threads) through both engines. Thread T2 stalls mid-pop at
operation 7 while holding a reference to node `n5`. Under hazard pointers,
the flushes that follow free everything *except* `n5` (T2's published
slot names it). Under epochs, T2's pin freezes its epoch and the final
reclaim count stays at zero - every retired node waits for T2.

```python
#!/usr/bin/env python3
"""Hazard pointers vs epoch-based reclamation on one Treiber-stack trace.

Same deterministic operation stream, two reclamation engines:

  HP  - hazard pointers (Michael 2004). Each thread has one hazard slot.
        A reader publishes the head pointer into its slot, validates it,
        reads, then clears. A popper retires unlinked nodes into a list;
        every R=2 retirements it scans ALL slots and frees only nodes no
        slot claims. Retention is per-object: exactly what a reader
        dereferences, nothing more.

  EBR - epoch-based reclamation (Fraser 2004). Readers pin the current
        global epoch; updaters retire nodes into bucket[epoch % 3]. A
        bucket can be freed only when the global epoch (= min pinned
        epoch) advances past it. Retention is per-epoch: one stalled
        reader holds back everything retired in its epoch.

Nodes are named by allocation order (n0 pushed first, so n2 is the third
node allocated). T2 is scheduled to stall at op 7 mid-pop while still
dereferencing node n2 - published hazard slot (HP) / still pinned in
epoch 0 (EBR) - which makes the retention difference visible.
"""

STACK = []   # top of stack is STACK[-1] (the head)
OPS = [      # (thread, action) - deterministic schedule
    ("T0", "push"), ("T1", "push"), ("T0", "pop"),
    ("T1", "pop"), ("T0", "pop"), ("T1", "push"),
    ("T2", "pop [stalls]"), ("T0", "push"), ("T1", "pop"),
    ("T0", "pop"), ("T1", "push"), ("T0", "pop"),
]


class HP:
    """Hazard-pointer engine: H=1 slot per thread, retire batch R=2."""

    def __init__(self, threads, R=2):
        self.slots = {t: None for t in threads}
        self.retire, self.R = [], R
        self.reclaimed, self.max_pending, self.slot_reads = 0, 0, 0
        self.log = []

    def pop(self, thread, stalled=False):
        if not STACK:
            return
        node = STACK[-1]
        self.slots[thread] = node        # 1. publish candidate head
        if STACK[-1] == node:            # 2. validate it is still the head
            STACK.pop()                  # 3. safe to unlink now
            if not stalled:              # 4. clear slot (stall: keep it)
                self.slots[thread] = None
            self.retire.append(node)
            self.max_pending = max(self.max_pending, len(self.retire))
            if len(self.retire) >= self.R:
                self.flush(thread)

    def flush(self, thread):
        claimed = set(v for v in self.slots.values() if v is not None)
        self.slot_reads += len(self.retire) * len(self.slots)
        free = [n for n in self.retire if n not in claimed]
        for n in free:
            self.retire.remove(n)
            self.reclaimed += 1
        self.log.append("    HP flush by %s: free %s, keep %s"
                        % (thread, free or "none", self.retire or "none"))


class EBR:
    """Epoch engine: 3 rotating buckets, global epoch = min pinned epoch."""

    def __init__(self, threads):
        self.pinned = {t: None for t in threads}
        self.epoch = 0
        self.buckets = {0: [], 1: [], 2: []}
        self.reclaimed, self.publish_ops = 0, 0
        self.log = []

    def pop(self, thread, stalled=False):
        if not STACK:
            return
        self.publish_ops += 1            # pin: enter epoch-protected region
        self.pinned[thread] = self.epoch
        node = STACK[-1]
        if STACK[-1] == node:
            STACK.pop()
            self.buckets[self.epoch % 3].append(node)
        if not stalled:                  # stall: T2 never unpins
            self.publish_ops += 1
            self.pinned[thread] = None
        self.try_advance()

    def try_advance(self):
        active = [e for e in self.pinned.values() if e is not None]
        floor = min(active) if active else self.epoch
        if floor > self.epoch:           # nobody left in old epochs: free
            for e in range(self.epoch, floor):
                if self.buckets[e % 3]:
                    self.log.append("    EBR advance to %d: free bucket %s"
                                    % (e + 1, self.buckets[e % 3]))
                    self.reclaimed += len(self.buckets[e % 3])
                    self.buckets[e % 3] = []
            self.epoch = floor

    def retained(self):
        return [n for b in self.buckets.values() for n in b]


def run(engine, label):
    print("%s trace:" % label)
    for i, (thread, op) in enumerate(OPS):
        if op == "push":
            STACK.append("n%d" % i)
            node = STACK[-1]
        else:
            node = STACK[-1] if STACK else None
            engine.pop(thread, stalled=(op == "pop [stalls]"))
        print("  op%02d %s %-12s stack=%s" % (i + 1, thread, op, STACK))
        for line in engine.log:
            print(line)
        engine.log = []
    return engine


hp = run(HP(["T0", "T1", "T2"]), "HP ")
ebr = run(EBR(["T0", "T1", "T2"]), "EBR")
print()
print("HP : reclaimed=%d retained=%s max_pending=%d slot_reads=%d"
      % (hp.reclaimed, hp.retire or "none", hp.max_pending, hp.slot_reads))
print("EBR: reclaimed=%d retained=%s bucket0=%s publish_ops=%d"
      % (ebr.reclaimed, ebr.retained() or "none", ebr.buckets[0], ebr.publish_ops))
print("stalled T2: HP holds back exactly the node it dereferences (%s);"
      % hp.retire)
print("EBR holds back every node retired in its epoch (%s)" % ebr.retained())
```

```text
HP  trace:
  op01 T0 push         stack=['n0']
  op02 T1 push         stack=['n0', 'n1']
  op03 T0 pop          stack=['n0']
  op04 T1 pop          stack=[]
    HP flush by T1: free ['n1', 'n0'], keep none
  op05 T0 pop          stack=[]
  op06 T1 push         stack=['n5']
  op07 T2 pop [stalls] stack=[]
  op08 T0 push         stack=['n7']
  op09 T1 pop          stack=[]
    HP flush by T1: free ['n7'], keep ['n5']
  op10 T0 pop          stack=[]
  op11 T1 push         stack=['n10']
  op12 T0 pop          stack=[]
    HP flush by T0: free ['n10'], keep ['n5']
EBR trace:
  op01 T0 push         stack=['n0']
  op02 T1 push         stack=['n0', 'n1']
  op03 T0 pop          stack=['n0']
  op04 T1 pop          stack=[]
  op05 T0 pop          stack=[]
  op06 T1 push         stack=['n5']
  op07 T2 pop [stalls] stack=[]
  op08 T0 push         stack=['n7']
  op09 T1 pop          stack=[]
  op10 T0 pop          stack=[]
  op11 T1 push         stack=['n10']
  op12 T0 pop          stack=[]

HP : reclaimed=4 retained=['n5'] max_pending=2 slot_reads=18
EBR: reclaimed=0 retained=['n1', 'n0', 'n5', 'n7', 'n10'] bucket0=['n1', 'n0', 'n5', 'n7', 'n10'] publish_ops=9
stalled T2: HP holds back exactly the node it dereferences (['n5']);
EBR holds back every node retired in its epoch (['n1', 'n0', 'n5', 'n7', 'n10'])
```

Read the last two lines as the whole design space: the HP engine reclaimed
4 nodes and retained exactly one (the node the stalled reader named), while
the EBR engine reclaimed nothing because its epoch floor never moved. Flip
the workload - millions of short readers racing a few updaters - and EBR's
zero-per-object cost wins despite retention risk, which is precisely the
kernel RCU trade documented in [RCU](./rcu.md).

## Interview probes

- Why must publish be followed by a *validation* re-read, and what exactly
  goes wrong if the validation is omitted? (Answer with the two-step race
  between unlink and free, not "cache coherence".)
- Derive the `N*H + (R-1)` waste bound for hazard pointers and explain why
  the same bound does not exist for EBR.
- Where does the ABA problem show up in this trace, and how do hazard
  pointers accidentally mitigate it? What do tagged pointers add?
- EBR uses *three* buckets - why three, not two?

## References

1. Michael, "Hazard pointers: safe memory reclamation for lock-free
   objects", IEEE TPDS 15(6):491-504, 2004,
   [doi:10.1109/TPDS.2004.8](https://doi.org/10.1109/TPDS.2004.8) - the
   publish/validate protocol and the bounded-waste proof.
2. Michael, "Safe memory reclamation for dynamic lock-free objects using
   atomic reads and writes", PODC 2002,
   [doi:10.1145/571826.571829](https://doi.org/10.1145/571826.571829) - the
   conference precursor.
3. Fraser, *Practical Lock-Freedom*, UCAM-CL-TR-579, 2004,
   [the technical report](https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-579.pdf)
   - epoch-based reclamation, SMR engineering data, the ROP-style ABA
   analyses.
4. McKenney, "What is RCU, Fundamentally?",
   [LWN.net](https://lwn.net/Articles/262464/) - the grace-period mental
   model this page's kernel-RCU column assumes.
