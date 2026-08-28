# Wait-Free Hierarchy

## Three promises, three costs

Progress guarantees are promises about who finishes. A **blocking**
(lock-based) structure finishes its operation if the threads holding
the locks it needs release them. A **lock-free** structure promises
that *some* thread makes progress in a finite number of system steps —
your operation may starve, but the system moves
([Lock-Free](./lock-free.md)). A **wait-free** structure promises the
strongest thing in shared memory: *every* thread completes every
operation in a bounded number of its own steps, no matter what the
others do ([Obstruction-freedom](./advanced-concurrency.md) sits
between the two: progress once the thread runs alone).

Wait-freedom sounds like a free upgrade. In 1988/1991 Maurice Herlihy
proved it is not: for a given object type, wait-free implementations
have a hard capacity limit called the **consensus number**, and that
limit partitions every shared-memory object ever proposed into a
countably infinite ladder. The ladder explains an enormous amount of
systems practice — why CAS is in every ISA, why wait-free queues are
rare, and why the whole lock-free reclamation apparatus
([Hazard Pointers](./hazard-pointers.md),
[ABA Problem](./aba-problem.md)) exists at all.

## Consensus: the reducer of all synchronization

**Consensus** is the agreement problem: *n* threads each start with a
private proposal; each must eventually (and wait-free) output a value,
every output is *some* thread's proposal (validity), and all outputs
are equal (agreement). Consensus is a reducer: any object that solves
*n*-thread consensus can, via Herlihy's universal construction, build
a wait-free implementation of *any* object at all. So the question
"can object X wait-free-implement object Y?" collapses to "is X's
consensus number at least Y's?"

The **consensus number** of a type X is the largest *n* for which
wait-free *n*-thread consensus is solvable using any number of copies
of X plus read/write registers. Types are grouped by number, and each
level of the ladder is provably unimplementable from lower levels:

| Object type | Consensus number | Notes |
|---|---|---|
| Read/write register | 1 | not even 2-thread consensus |
| Test-and-set, swap, fetch-and-add | 2 | the "read the flag, lose blind" family |
| FIFO queue, stack | 2 | first enqueuer/pusher wins; losers can dequeue the winner's proposal — but only for 2 threads |
| Compare-and-swap, LL/SC | unbounded | the winner's value rides inside the returned old value |
| *n*-register assignment | n | can write n registers atomically |

Two facts give the table its force. First, **level 1 vs level 2**: a
read/write register cannot break symmetry — if two threads read the
same value, their subsequent states are indistinguishable, and no
amount of extra registers helps (the demo below shows the same
indistinguishability argument at level 2 vs level ∞). Second, **level
2 vs level unbounded**: test-and-set, swap, fetch-and-add, queues, and
stacks all return *only* "did I win or lose" (or the element they were
talking to), which suffices for exactly two threads and provably not
for three.

## The impossibility, by execution

The n=2 TAS protocol works because the loser knows *exactly one*
possible winner. Add a third thread and that inference breaks:

```text
   TAS consensus, 3 threads:  A proposes 0, B proposes 1, C proposes ?

   A: read flag (free)     B: read flag (free)     <- identical states
   A: TAS -> free: A wins, decides 0
   B: TAS -> taken: B loses
   C: read flag (taken): someone won...

   ...but the object says nothing about WHO won:
     if A won -> decide A's proposal (0)
     if B won -> decide B's proposal (1)
   C's two views are indistinguishable to any TAS-only protocol,
   yet they demand different outputs -> no 3-thread TAS consensus.
```

The formal proof (Herlihy, PODC 1988) runs this argument inductively
over *bivalent* initial states — states where both outcomes are still
possible — and shows any proposed protocol has an execution in which
the system stays forever poised between two decisions. The demo below
replays the pivotal step and then shows why CAS escapes: a failed CAS
*returns the value it observed*, so the winner's proposal travels
inside the primitive itself and no thread ever has to guess who won.

```python
FREE, TAKEN = 0, 1


class TASObj:
    """Test-and-set: returns the flag value it observed."""

    def __init__(self):
        self.flag = FREE

    def tas(self):
        prev = self.flag
        self.flag = TAKEN
        return prev


class CASObj:
    """Compare-and-swap: CAS(expected, new) returns the value seen."""

    def __init__(self):
        self.val = None

    def cas(self, expected, new):
        seen = self.val
        if seen == expected:
            self.val = new
        return seen


def tas_read_flag(obj):
    return obj.flag


print("consensus-number ladder (Herlihy 1988/1991)")
print("  object                                consensus number")
print("  read/write register                   1")
print("  test-and-set / swap / fetch-and-add   2")
print("  FIFO queue / stack                    2")
print("  compare-and-swap / LL-SC              unbounded")
print()

# ---------------------------------------------------------------- n=2 TAS
print("TAS consensus, n=2 (the borderline case)")
a_prop, b_prop = 0, 1
obj = TASObj()
a_reg, b_reg = {}, {}
a_reg["proposal"] = a_prop
b_reg["proposal"] = b_prop
print(f"  A: propose {a_prop};  B: propose {b_prop}")
ra = tas_read_flag(obj)
rb = tas_read_flag(obj)
print(f"  A reads flag=free; B reads flag=free    <- both optimistic")
pa = obj.tas()
pb = obj.tas()
assert pa == FREE and pb == TAKEN
a_decides = a_prop
b_decides = a_reg["proposal"]          # B's only possible rival is A
print(f"  A TAS -> free  : A WINS,  decides {a_decides}")
print(f"  B TAS -> taken : B LOSES; only rival is A -> reads A's register = "
      f"{b_decides}")
print(f"  decision: A={a_decides} B={b_decides}  AGREE  (n=2 is solvable)")
print()

# ---------------------------------------------------------------- n=3 TAS
print("TAS consensus, n=3 (Herlihy's impossibility, played out)")


def tas_run3(order):
    """order: which register C inspects first. Returns decisions."""
    obj = TASObj()
    regs = {"A": {"proposal": 0}, "B": {"proposal": 1},
            "C": {"proposal": 0}}
    tas_reads = {}
    for t in ("A", "B"):                    # both read the flag optimistically
        tas_reads[t] = tas_read_flag(obj)
    tas_ret = {}
    tas_ret["A"] = obj.tas()                # A linearizes first -> wins
    tas_ret["B"] = obj.tas()                # B arrives late -> loses
    assert tas_ret["A"] == FREE and tas_ret["B"] == TAKEN
    a_dec = regs["A"]["proposal"]           # winner decides its own proposal
    c_flag = tas_read_flag(obj)
    # C sees the flag taken but cannot tell WHICH thread won: both A and B
    # have posted proposals, and the object carries no identity.
    c_dec = regs[order]["proposal"]         # C must just pick a register
    return {"A": a_dec, "B": None, "C": c_dec}, c_flag


print("  A: propose 0;  B: propose 1;  C: propose 0")
print("  -- prefix, identical in both completions --")
print("  A reads flag=free; B reads flag=free")
print("  A TAS -> free  : A decides 0")
print("  B TAS -> taken : B LOSES (cannot learn the winner)")
print("  C reads flag=taken: someone won, but who?")
run1, _ = tas_run3("A")
run2, _ = tas_run3("B")
print("  -- completion 1: C inspects A's register first --")
print(f"  proposal(A)=0 -> C decides {run1['C']}")
print("  -- completion 2: C inspects B's register first --")
print(f"  proposal(B)=1 -> C decides {run2['C']}")
print(f"  same prefix, two legal outcomes (C=0 vs C=1) -> "
      f"TAS consensus impossible for n=3")
print()

# ------------------------------------------------------------- CAS, any n
print("CAS consensus: the winner's proposal rides inside the object")


def cas_run(n):
    obj = CASObj()
    decisions = []
    # adversarial order: everyone reads (CASes) optimistically in id order;
    # the first CAS sees None and wins, every later one sees the winner.
    for i in range(n):
        proposal = i % 2                    # A,B,C,... propose 0,1,0,1,...
        seen = obj.cas(None, proposal)
        decisions.append(proposal if seen is None else seen)
    return decisions


for n in (2, 3, 5, 8):
    dec = cas_run(n)
    agree = len(set(dec)) == 1
    print(f"  n={n}: decisions {dec}  "
          f"{'AGREE' if agree else 'DISAGREE'}")
print()
print("every failed CAS returned the winning proposal, so each loser")
print("learned the decision value directly from the object -> consensus")
print("for ANY n. That is why CAS is the universal primitive.")
```

```text
consensus-number ladder (Herlihy 1988/1991)
  object                                consensus number
  read/write register                   1
  test-and-set / swap / fetch-and-add   2
  FIFO queue / stack                    2
  compare-and-swap / LL-SC              unbounded

TAS consensus, n=2 (the borderline case)
  A: propose 0;  B: propose 1
  A reads flag=free; B reads flag=free    <- both optimistic
  A TAS -> free  : A WINS,  decides 0
  B TAS -> taken : B LOSES; only rival is A -> reads A's register = 0
  decision: A=0 B=0  AGREE  (n=2 is solvable)

TAS consensus, n=3 (Herlihy's impossibility, played out)
  A: propose 0;  B: propose 1;  C: propose 0
  -- prefix, identical in both completions --
  A reads flag=free; B reads flag=free
  A TAS -> free  : A decides 0
  B TAS -> taken : B LOSES (cannot learn the winner)
  C reads flag=taken: someone won, but who?
  -- completion 1: C inspects A's register first --
  proposal(A)=0 -> C decides 0
  -- completion 2: C inspects B's register first --
  proposal(B)=1 -> C decides 1
  same prefix, two legal outcomes (C=0 vs C=1) -> TAS consensus impossible for n=3

CAS consensus: the winner's proposal rides inside the object
  n=2: decisions [0, 0]  AGREE
  n=3: decisions [0, 0, 0]  AGREE
  n=5: decisions [0, 0, 0, 0, 0]  AGREE
  n=8: decisions [0, 0, 0, 0, 0, 0, 0, 0]  AGREE

every failed CAS returned the winning proposal, so each loser
learned the decision value directly from the object -> consensus
for ANY n. That is why CAS is the universal primitive.
```

## Why queues and stacks stop at 2

Queues and stacks are level-2 objects for a structural reason worth
knowing in interviews. A queue solves 2-thread consensus: both threads
enqueue their proposal, then dequeue; whoever dequeues first gets a
proposal and decides it (that thread "won"), and the loser dequeues
the winner's proposal and decides that. With three threads the same
ambiguity as TAS reappears: a thread that finds the queue's element
already taken cannot tell whether the first or second enqueuer won.
The dequeue returns *an element*, not *the decision* — and one element
of context is provably not enough to disambiguate three or more
competing winners. Fetch-and-add fails the same way: FAA returns the
old counter value, which collapses all racing threads into
indistinguishable "I incremented after someone" states.

## CAS as the universal primitive

Because CAS/LL-SC have unbounded consensus number, they can wait-free
implement *every* object — Herlihy's **universal construction**. The
shape is simple enough to sketch from memory:

```text
   universal construction (one CAS cell "head" + per-thread announce slot)

   thread i:  announce(op_i) in its slot
   loop:
     p = head                          # the current serial log tail
     build next = append(p, op_i)      # private new log cell
     if CAS(head, p, next):            # my op appended after the log
         pass
     # either way, someone's op is now in the log
     walk the log from the last state I applied,
       apply each op to my local copy of the object,
       if my op appears: return its response
```

The log serializes operations; consensus on the CAS cell decides the
order; every thread terminates after a bounded number of its own
steps. This is why every ISA that takes lock-free programming
seriously grew a CAS/LL-SC instruction ([Atomic
Primitives](./atomic-primitives.md)), and why higher-level
constructions — Michael-Scott queues, Treiber stacks, epoch
reclamation — are all, underneath, log-serializing protocols over CAS.

Two consequences for practice:

- **Fetch-and-add cannot substitute for CAS.** FAA is consensus
  number 2: it can build wait-free counters, but not wait-free
  arbitrary objects. A wait-free design that avoids CAS and ABA by
  using only FAA is impossible in general — a favorite trick question.
  (Fatourou and Kallimanis's 2011 universal construction gets as close
  as theory allows: wait-freedom from CAS *plus* FAA with far fewer
  CAS operations per op than the naive construction.)
- **The delegation escape hatch exists.** [Flat
  Combining](./flat-combining.md) and the delegated structures around
  it give up wait-freedom at the object level (passive threads block on
  their combining record) and buy back simplicity and throughput — an
  engineering decision the hierarchy makes precise.

## Why wait-freedom is rare in shipped code, and what it costs

If wait-free structures are strictly better by the progress metric,
why is production code full of CAS *loops* (lock-free, not
wait-free)? Three compounding costs:

1. **The reclamation tax.** A wait-free or lock-free operation hands
   pointers to other threads that may read them after the handoff. Freeing
   memory then risks use-after-free through an in-flight pointer — the ABA
   family of bugs. The fixes (hazard pointers, epochs, RCU) are per-thread
   infrastructure with their own memory costs
   ([Hazard Pointers](./hazard-pointers.md),
   [RCU](./rcu.md)). Under a lock, the lock's mutual exclusion is the
   grace period and no apparatus is needed.
2. **Bounded-step proofs are hard.** A lock-free loop terminates only if
   the system as a whole progresses; proving a *bound on an individual
   thread's* steps means bounding retry counts, which real schedules
   (preemption, NUMA skew) make delicate.
3. **The hierarchy blocks shortcuts.** There is no clever register
   trick that beats consensus number 2 objects into wait-free
   generality — thirty-plus years of attempts all reduce to Herlihy's
   impossibility. The only exits are consensus-unbounded primitives
   (CAS/LL-SC) or delegation.

The shared-memory ladder also has a message-passing shadow: in
distributed systems, the same style of bivalence argument yields the
FLP impossibility for asynchronous consensus
([FLP](../distributed/fundamentals/flp.md),
[Impossibility Models](../distributed/advanced/impossibility-models.md))
— Herlihy's hierarchy is what the problem looks like when shared
memory replaces messages and steps are instead of rounds.

## Interview questions

1. **Q: State Herlihy's wait-free hierarchy in one sentence.**
   A: Shared-memory object types form an infinite ladder by consensus
   number — the largest n for which they wait-free solve n-thread
   consensus; an object at level n cannot be wait-free implemented from
   objects at lower levels, and CAS/LL-SC sit at the top with unbounded
   consensus number.

2. **Q: Why do queues have consensus number 2, not unbounded?**
   A: Two threads: enqueue both proposals, dequeue — first dequeuer wins,
   the loser dequeues the winner's proposal. Three threads: a thread
   arriving late cannot determine which of the earlier enqueuers won, so
   two executions indistinguishable to it require different outputs.

3. **Q: What makes CAS universal where test-and-set is not?**
   A: A failed CAS returns the value it observed, so the winner's
   identity/proposal is carried inside the primitive to every loser;
   TAS returns only a bit, so losers cannot learn who won, and a third
   thread cannot disambiguate.

4. **Q: How does the hierarchy relate to ABA and memory reclamation?**
   A: Since only CAS is universal, lock-free structures are built on CAS
   pointer swaps; CAS compares raw addresses, so free-then-reuse trips
   ABA. All the standard reclamation schemes (hazard pointers, epochs,
   RCU) exist to keep pointers stable long enough for CAS loops to be
   safe.

5. **Q: A colleague proposes a wait-free universal construction built
   from fetch-and-add alone. What do you tell them?**
   A: Impossible by the hierarchy: FAA has consensus number 2, and a
   universal construction needs unbounded consensus. Their design either
   solves only 2-thread problems, blocks some thread indefinitely (not
   wait-free), or is secretly using a CAS/LL-SC underneath.

## Cross-references

- [Lock-Free Data Structures](./lock-free.md) — the lock-free vs
  wait-free distinction in code; Treiber stack and Michael-Scott queue
- [Atomic Primitives](./atomic-primitives.md) — the CAS/LL-SC/FAA
  instruction set the ladder ranks
- [ABA Problem](./aba-problem.md) and
  [Hazard Pointers](./hazard-pointers.md) — the reclamation tax that
  follows from building everything on CAS
- [RCU](./rcu.md) — grace periods as an alternative reclamation contract
- [Flat Combining](./flat-combining.md) — delegation as the pragmatic
  middle ground the hierarchy permits
- [Advanced Concurrency](./advanced-concurrency.md) — progress
  guarantee definitions and the synchronization primitives they rank
- [FLP Impossibility](../distributed/fundamentals/flp.md) and
  [Impossibility Models](../distributed/advanced/impossibility-models.md)
  — the message-passing cousins of the bivalence argument

## References

- Maurice P. Herlihy. *Impossibility and Universality Results for
  Wait-Free Synchronization*. ACM PODC 1988.
  <https://doi.org/10.1145/62546.62593>
- Maurice Herlihy. *Wait-Free Synchronization*. ACM Transactions on
  Programming Languages and Systems 13(1), 1991.
  <https://doi.org/10.1145/114005.102808>
- Maurice Herlihy. *A Methodology for Implementing Highly Concurrent
  Data Objects*. ACM TOPLAS 15(5), 1993.
  <https://doi.org/10.1145/161468.161469>
- Hagit Attiya, Jennifer L. Welch. *Sequential Consistency versus
  Linearizability*. ACM TOCS 12(2), 1994.
  <https://doi.org/10.1145/176575.176576>
- Panagiota Fatourou, Nikolaos D. Kallimanis. *A Highly-Efficient
  Wait-Free Universal Construction*. ACM SPAA 2011.
  <https://doi.org/10.1145/1989493.1989549>
