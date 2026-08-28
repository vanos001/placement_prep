# Transactional Memory: Atomicity Beyond Locks

The lock-free data structures page shows how far you can push atomic
instructions - and how much complexity it costs (ABA, reclamation,
subtly broken algorithms). Transactional memory proposes the other end
of the trade: write code as if it holds *one big lock* over a critical
section, and let the system detect conflicts and roll back. This page
covers both flavors - software (STM) and hardware (HTM) - their
conflict-detection designs, the fallback paths that made HTM shippable,
and an honest assessment of why TM lost as a mainstream programming
interface while its ideas quietly shipped inside runtimes, locks, and
databases.

Related pages: [lock-free structures](./lock-free-structures.md) (the
complexity TM tries to replace), [hazard pointers](./hazard-pointers.md)
(reclamation, which TM sidesteps by construction), and
[flat combining](./flat-combining.md) (the middle ground).

## What TM promises

A `transaction { ... }` block behaves as if executed atomically and in
isolation against all others: no deadlocks (system rolls back instead of
blocking), no lock ordering to design, composable (two transactions can
concatenate into one - the property locks never had). The costs are
equally fundamental: wasted work on abort, memory overhead for undo/redo
logs, and the need for every memory access inside the transaction to be
instrumented or hardware-tracked.

## STM: versioning and conflict detection in software

Two designs dominate the literature, differing on *when* a writer's
view is consistent:

- **Lazy acquisition / commit-time locking (TL2-style, "mostly
  locking")**: reads record (address, expected version); writes buffer
  into a local write set. At commit: lock all written addresses (by
  CAS on their lock words), increment their version stamps, validate
  the read set still matches, apply. Aborts cost nothing but buffer
  space; conflicts surface only at commit.
- **Eager acquisition / early locking**: acquire write locks as you
  write, with undo logs for rollback. Conflicts detected earlier (less
  wasted work), but a transaction holds locks while running - the
  deadlock-avoidance machinery (the thing TM was supposed to remove)
  sneaks back in as contention on the write locks.

Read validation is the subtle part: a reader must detect that some
address it read was concurrently written (version check per read, or
one global-clock check at commit in TL2's optimization). The demo below
implements a miniature TL2 with read/write sets and shows a conflict
abort and a successful commit on a deterministic schedule.

## HTM: Intel TSX and its cautionary tale

Hardware TM (Intel TSX, 2013) made the transaction a CPU feature:
`XBEGIN` starts a transactional region; the CPU tracks the read/write
sets in the cache coherence protocol itself and commits atomically if
no other core touched them - zero instrumentation on the fast path,
roughly an order of magnitude better than STM.

The deployment history is the lesson. TSX worked, then firmware
disabled it on broad CPU generations after erratum discoveries, was
re-enabled in "TSX-ND" (new data) form on select parts, and was dropped
entirely from later cores. Production code therefore *must* treat HTM
as an opportunistic accelerator over a correct lock path: retry N
times (with exponential backoff), then take the fallback lock. This
"hybrid TM" pattern (and lock elision generally) is what actually
shipped: in glibc's pthread mutexes (lock elision) and inside
lock-free library internals - not in the source language.

| dimension      | STM                          | HTM (TSX-style)             |
|----------------|------------------------------|------------------------------|
| fast-path cost | read/write sets + validation | none (coherence tracking)   |
| capacity       | RAM-sized                    | cache/L1-sized (tiny)       |
| abort cause    | version mismatch             | capacity, interrupts, syscalls |
| fallback       | another STM strategy         | the lock the code replaced  |
| shipped as     | research runtimes, some DBs  | glibc elision, libraries    |

## Why TM didn't win, and where its ideas live

Three structural reasons, each an interview-worthy argument:

1. **I/O and system calls cannot roll back** - transactions are memory-
   shaped, and real programs cross those boundaries constantly; the
   programmer redesigns around them, at which point TM's composability
   pitch weakens.
2. **Semantic visibility gap**: transactions see *some* other
   transactions' effects only at commit - debugging tools, crash
   recovery, and I/O interplay all become subtle.
3. **The hardware bet inverted**: TM needed coherence-level support to
   be fast; when the silicon bet was withdrawn, the STM path was
   10-30x slower than well-written locks.

The surviving descendants: bounded speculation inside lock
implementations (elision), snapshot isolation in databases (read sets
validated at commit - the same structure as STM validation), and
optimistic concurrency control in memory engines (the MVCC machinery
in [mvcc internals](../../dbms/advanced/mvcc-internals.md) is STM's
read-validation problem wearing a data-model hat).

## The demo: a miniature TL2

```python
#!/usr/bin/env python3
"""Miniature TL2-style STM: global version clock, per-address lock
words, read/write sets, commit-time validation. Deterministic schedule
showing (1) a clean commit, (2) a read-validation abort, (3) a write
conflict abort. Pure stdlib."""

GLB = 0                     # global version clock
LOCKS = {}                  # address -> owner (None = free)
STAMPS = {}                 # address -> version stamp

def addr_read(mem, addr, txn):
    # read lock words must be free-or-mine, stamp <= txn.read_version
    owner = LOCKS.get(addr)
    if owner is not None and owner != txn.name:
        txn.abort_reason = "read of write-locked address"
        return None
    if STAMPS.get(addr, 0) > txn.read_version:
        txn.abort_reason = "read validation failed (stamp ahead)"
        return None
    txn.read_set[addr] = mem.get(addr, 0)
    return mem.get(addr, 0)


def addr_write(txn, addr, value):
    txn.write_set[addr] = value


class Txn:
    def __init__(self, name):
        self.name = name
        self.read_version = GLB
        self.read_set, self.write_set = {}, {}
        self.abort_reason = None


def commit(mem, txn):
    global GLB
    # 1. lock write set; on each acquisition also check the stamp:
    #    if the address moved past our read_version, a concurrent writer
    #    committed first -> first-committer-wins abort
    acquired = []
    for addr in txn.write_set:
        if LOCKS.get(addr) is not None:
            for a in acquired:
                LOCKS[a] = None
            txn.abort_reason = f"write conflict on {addr}"
            return False
        if STAMPS.get(addr, 0) > txn.read_version:
            for a in acquired:
                LOCKS[a] = None
            txn.abort_reason = f"write-write conflict on {addr} (stamp ahead)"
            return False
        LOCKS[addr] = txn.name
        acquired.append(addr)
    # 2. validate read set (all stamps <= read_version)
    for addr in txn.read_set:
        if STAMPS.get(addr, 0) > txn.read_version:
            for a in acquired:
                LOCKS[a] = None
            txn.abort_reason = "read-set validation failed at commit"
            return False
    # 3. apply and bump stamps to new global clock
    GLB += 1
    for addr, v in txn.write_set.items():
        mem[addr] = v
        STAMPS[addr] = GLB
    for a in acquired:
        LOCKS[a] = None
    return True


mem = {"x": 0, "y": 0}
print(f"start: mem={mem} global clock={GLB}")

t1 = Txn("t1")
v = addr_read(mem, "x", t1)
addr_write(t1, "y", v + 10)
ok = commit(mem, t1)
print(f"t1 (read x, write y=x+10): commit={ok} mem={mem} clock={GLB}")
assert ok

t2 = Txn("t2")
v = addr_read(mem, "x", t2)
addr_read(mem, "y", t2)                # t2 reads y in its read set
addr_write(t2, "x", v + 1)
# concurrent t3 commits a write to y BEFORE t2 commits -> validation fail
t3 = Txn("t3")
addr_write(t3, "y", 999)
ok3 = commit(mem, t3)
print(f"t3 (write y=999): commit={ok3} mem={mem} clock={GLB}")
ok2 = commit(mem, t2)
print(f"t2 (read x,y; write x): commit={ok2} reason='{t2.abort_reason}'")
assert not ok2 and "validation" in (t2.abort_reason or "")

t4 = Txn("t4")
addr_write(t4, "x", 5)
t5 = Txn("t5")
addr_write(t5, "x", 7)          # t5 started BEFORE t4 commits
ok4 = commit(mem, t4)
ok5 = commit(mem, t5)
print(f"t4 commit={ok4}; t5 (same addr, started earlier) commit={ok5} "
      f"reason='{t5.abort_reason}'")
assert ok4 and not ok5 and "stamp ahead" in t5.abort_reason
print("assertions passed: clean commit, validation abort, write-write conflict")
```

```text
start: mem={'x': 0, 'y': 0} global clock=0
t1 (read x, write y=x+10): commit=True mem={'x': 0, 'y': 10} clock=1
t3 (write y=999): commit=True mem={'x': 0, 'y': 999} clock=2
t2 (read x,y; write x): commit=False reason='read-set validation failed at commit'
t4 commit=True; t5 (same addr, started earlier) commit=False reason='write-write conflict on x (stamp ahead)'
assertions passed: clean commit, validation abort, write-write conflict
```

The three outcomes are the whole STM story: uncontended transactions
commit with two clock bumps; a read validated at commit fails if any
read address's stamp moved (t2's y); and write-write conflicts resolve
at first-committer-wins (t5) - exactly the SI write-conflict rule in
[snapshot isolation](../../dbms/advanced/snapshot-isolation.md).

## Interview probes

- Prove that TL2's commit-time validation plus write locking gives
  serializability (sketch the serialization-point argument at the
  global clock bump).
- Why does HTM capacity abort push implementations toward small
  transactions, and what does that do to the composability pitch?
- Design the fallback ladder for an elided mutex: how many retries,
  what backoff, and which abort code means "never retry"?
- Where does SI's write-conflict rule appear in the STM demo, and what
  would change under serializable validation (SSI-style)?

## References

1. Herlihy & Moss, "Transactional memory: architectural support for
   lock-free data structures", ISCA 1993,
   [doi:10.1145/165123.165164](https://doi.org/10.1145/165123.165164) -
   the original HTM proposal and its cache-coherence design.
2. Dice, Shalev, Shavit, "Transactional locking II" (TL2), DISC 2006 -
   the global-clock versioning scheme the demo implements (author
   pages/tech reports are the canonical source; search-verified).
3. Harris, Marlow, Peyton-Jones, Herlihy, "Composable memory
   transactions", PPoPP 2005,
   [doi:10.1145/1065944.1065952](https://doi.org/10.1145/1065944.1065952)
   - the composability argument and retry/orelse semantics (Haskell STM
   write-up: [Beautiful Concurrency](https://research.microsoft.com/en-us/um/people/simonpj/papers/STM/beautiful.pdf)).
4. [Lock-free structures (this repo)](./lock-free-structures.md) - the
   manual discipline TM automates.
