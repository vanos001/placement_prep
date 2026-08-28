# Key-Range and Predicate Locking

Row locks answer one question — "can two transactions change the same *existing* row?" — but the hardest serializability problem involves rows that **do not exist yet**. This page works through the phantom problem, the predicate-lock solution and why System R abandoned it, the multi-granularity compromise, and the design that actually shipped at scale: InnoDB's next-key locking, including the gap-lock/insert-intention interplay behind the most famous deadlock in MySQL operations. It contrasts the pessimistic route (key-range locks under strict two-phase locking) with the optimistic route covered in [serializable-snapshot-isolation.md](serializable-snapshot-isolation.md).

## The Phantom Problem, Formally

A transaction that evaluates a predicate (e.g., `SELECT * FROM employees WHERE age BETWEEN 20 AND 30`) reads a *set* of rows. Row-level locking can only lock rows that are present at read time. If another transaction later inserts a row that also satisfies the predicate, the first transaction re-evaluates the predicate (even something as mundane as repeating the query inside the same transaction) and sees a row that was never locked or read:

```text
employees: ages 10, 20, 30, 40

T1: SELECT * WHERE age BETWEEN 20 AND 30;   reads ages {20, 30}
T2: INSERT INTO employees VALUES (age 25);  no row conflicts -> commits
T1: SELECT * WHERE age BETWEEN 20 AND 30;   now reads {20, 25, 30}
                                             ^^^ row 25 was never locked:
                                                 a phantom
```

Under READ COMMITTED or REPEATABLE READ this is legal; under SERIALIZABLE it must be impossible. The formalization (Eswaran et al., 1976) treats a read of predicate P as reading an implicit set P(DB) — including rows that will exist later. Preventing phantoms therefore requires constraining *inserts*, not just reads and updates of existing records.

## Predicate Locks: The Complete Solution That Wasn't

Eswaran, Gray, Lorie, and Traiger's CACM paper defined the transaction model, established two-phase locking as the serializability mechanism for objects, and proposed the missing piece: **predicate locks**. The rules:

- A read of predicate P acquires a shared lock *on the predicate P*.
- A write of rows matching predicate Q acquires an exclusive lock *on Q*.
- Two predicate locks conflict iff their predicates' extension sets can intersect: P ∩ Q ≠ ∅ (or more generally, there may exist a database state satisfying both).

Under two-phase discipline (all predicate locks held until commit), this is provably serializable — it is the *complete* solution. It was never implemented in System R. Two reasons:

1. **Intersection testing is expensive or undecidable.** Deciding whether `age BETWEEN 20 AND 30` conflicts with `salary > 100 AND dept = 'toys'` requires an SMT-style satisfiability check over arbitrary WHERE clauses, per lock request, at run time. For arithmetic over integers, ranges are easy; add strings, LIKE patterns, subqueries, or OR-trees and the test becomes intractable — for rich enough predicates, undecidable.
2. **Lock count explosion.** Every predicate read is a new lock object; there is no identity to coalesce on and no index to find conflicting predicates quickly.

System R instead shipped the multi-granularity object-locking scheme below, accepting phantom anomalies, and the industry spent 35 years recovering serializability by other means (InnoDB with next-key locks, PostgreSQL with SSI).

## The Hierarchical Compromise: Granularity Ladder

The Gray/Lorie/Putzolu/Traiger multi-granularity protocol lets a transaction lock a database, file (table), page, or row, using **intention locks** to announce activity at finer levels below an already-locked coarse node. A transaction wanting row-level locks on a table first takes IX on the table; a reader wanting the whole table takes S and conflicts with that IX — no per-row scan needed to notice the conflict.

| Mode | Announces | Compatible with |
|------|-----------|-----------------|
| IS   | "I will take S locks on descendants" | IS, IX, S |
| IX   | "I will take X locks on descendants" | IS, IX |
| S    | "I read this node and everything under it" | IS, S |
| SIX  | "I read this node, and will update some descendants" | IS |
| X    | "I own this node and everything under it" | (nothing) |

The ladder is a granularity/overhead dial: row locks give concurrency but cost memory and bookkeeping; table locks are cheap but serialize. Every engine therefore **escalates** — SQL Server converts a statement's fine-grained locks to a table lock once roughly 5,000 are held (its documented threshold behavior). Escalation is the practical admission that pure row locking does not scale — the same pressure that motivated key-range locking for predicates.

## InnoDB: Next-Key Locking in Practice

InnoDB implements predicate protection not by locking predicates, but by locking **the index intervals where phantom rows would have to be inserted**. Under REPEATABLE READ and SERIALIZABLE, a locking read on a range acquires, for each index record it touches, a **next-key lock**: a record lock on the entry plus a gap lock on the open interval *before* it.

```text
index on age, entries:  10      20      30      40     [supremum]
                        |-------|-------|-------|------|
gap before 10:   (-inf, 10]
next-key on 20:  record(20) + gap (10, 20]
next-key on 30:  record(30) + gap (20, 30]
next-key on 40:  record(40) + gap (30, 40]
supremum:        gap (40, +inf)  -- the gap above the largest key

A scan of age BETWEEN 20 AND 30 locks:
  next-key(20), next-key(30), and gap (30, 40)
so INSERT age=25 (gap (20,30]) and INSERT age=35 (gap (30,40)) both block.
```

Row-lock kinds in InnoDB's `performance_schema.data_locks` vocabulary, and what each actually guards:

| Lock kind | Guards | Blocks |
|-----------|--------|--------|
| Record lock (REC_NOT_GAP) | one index record | other record locks on that record |
| Gap lock (GAP) | open interval (a, b) between records | inserts of key values in (a, b) |
| Next-key (ORDINARY) | record + gap before it | both of the above |
| Insert intention (INS_INT) | one intended insert position | nothing directly; it *waits* |
| AUTO-INC | table-level counter | concurrent inserts (mode-dependent) |

Three rules make the scheme workable rather than a deadlock factory:

1. **Gap locks are purely inhibitive.** Two transactions may hold gap locks on the *same* gap simultaneously, even "exclusive" ones. A gap lock never conflicts with another gap lock; it only ever blocks an insert. This single rule is what keeps read-heavy serializable scans from deadlocking each other.
2. **Unique-key equality on an existing row takes only a record lock** — no gap. Gap locking applies to range scans and to searches for values that are not there. InnoDB also skips gap locking entirely under READ COMMITTED (except for foreign-key and duplicate-key checks), which is a big part of why RC feels so much snappier under insert-heavy load.
3. **Every transaction touching a gap also holds IX on the table**, but table-level IX is only an intention flag; the real contention is at the interval level. The "supremum" pseudo-record gives every index a well-defined last gap (40, +inf) so the top of the index is lockable too.

## Insert Intention Locks: Waiting Politely

If gap locks simply blocked all inserts, two transactions inserting *different* values into the same gap would serialize pointlessly. InnoDB refines this with the **insert intention lock**: before inserting, a transaction signals intent at its target position and waits only for gap locks that *cover that gap* — never for other insert intentions. Two inserts of 25 and 28 into gap (20, 30) proceed concurrently; an insert waits only for scanners holding gap locks.

| Held ↓ / Wanted → | Gap lock | Insert intention | Record S | Record X |
|-------------------|----------|------------------|----------|----------|
| Gap lock          | Compatible | Conflict       | n/a¹     | n/a¹     |
| Insert intention  | Conflict   | Compatible     | n/a¹     | n/a¹     |
| Record S          | n/a¹       | n/a¹           | Compatible | Conflict |
| Record X          | n/a¹       | n/a¹           | Conflict   | Conflict |
| Next-key X        | Compatible (gap part) | Conflict | Conflict | Conflict |

¹ Record locks address index records; gap locks address open intervals between records. They are different resources and never compete directly; a next-key lock is the one object that spans both.

## The Two-Insert Gap Deadlock

The compatibility rules above contain a trap: gap locks coexist, insert intentions conflict with *other transactions'* gaps. Combine them and two sessions can each read-lock a gap (compatible!), then each try to insert into it — each insert-intention lock waits on the other session's gap lock, a textbook cycle. The simulation below implements exactly these compatibility rules and the coverage model, and replays both scenarios deterministically:

```python
#!/usr/bin/env python3
"""Deterministic simulation of InnoDB key-range (next-key/gap) locking.

Part 1: the classic two-session phantom-insert gap deadlock
        (SELECT of a nonexistent row, then INSERT, from both sessions).
Part 2: next-key lock coverage model for a range scan (which INSERTs block).
Pure stdlib, fully deterministic.
"""

REC, GAP, NEXT_KEY, INS_INT = "REC", "GAP", "NEXT_KEY", "INS_INT"

def compatible(held, want, same_txn):
    """InnoDB-style compatibility. Locks are (type, mode); modes S or X.
    Gap locks are purely inhibitive: two gap locks never conflict, even
    two X ones. They only ever conflict with insert intention locks."""
    if same_txn:
        return True
    ht, wm = held[0], want[0]
    if ht == GAP and wm == GAP:
        return True                       # gap vs gap: always compatible
    if ht == INS_INT and wm == INS_INT:
        return True                       # two future inserts don't clash
    if ht == GAP and wm == INS_INT:
        return False                      # insert must wait out the gap
    if ht == INS_INT and wm == GAP:
        return False
    # record / next-key (record part): S+S compatible, else conflict
    return wm == "S" and held[1] == "S"

class LockMgr:
    def __init__(self, keys):
        self.keys = keys                  # sorted key values in the index
        self.locks = {}                   # resource -> {txn: (type, mode)}
        self.gap_cover = {}               # txn -> set of intervals guarded

    def gap_of(self, key):
        """Interval that `key` would be inserted into."""
        prev = max([k for k in self.keys if k < key], default="-inf")
        nxt = min([k for k in self.keys if k > key], default="+inf")
        return (prev, nxt)

    def acquire(self, txn, ltype, mode, res, log):
        for holder, hl in self.locks.get(res, {}).items():
            if not compatible(hl, (ltype, mode), holder == txn):
                log.append(f"    T{txn}: {ltype} on {res} BLOCKED by T{holder}"
                           f" -> waits")
                return False
        self.locks.setdefault(res, {})[txn] = (ltype, mode)
        log.append(f"    T{txn}: {ltype}/{mode} on {res} granted")
        return True

    def cover_gap(self, txn, interval, log):
        """Record gap ownership for insert-intention conflict checks."""
        self.gap_cover.setdefault(txn, set()).add(interval)
        log.append(f"    T{txn}: gap {interval} now guarded")

    def try_insert(self, txn, key, log):
        interval = self.gap_of(key)
        blockers = [t for t in self.gap_cover
                    if t != txn and interval in self.gap_cover[t]]
        if blockers:
            b = sorted(blockers)[0]
            log.append(f"    T{txn}: INSERT {key} blocked: insert-intention "
                       f"lock on {interval} waits for T{b}'s gap lock")
            return b
        log.append(f"    T{txn}: INSERT {key} proceeds")
        return None

def part1():
    print("PART 1: two-session phantom-insert deadlock (the MySQL gap-lock case)")
    print("index keys: 10, 20 | both sessions run SELECT id=15 FOR UPDATE")
    print("(no row 15), then both INSERT id=15.")
    log = []
    mgr = LockMgr([10, 20])
    gap = mgr.gap_of(15)
    # Equality search for a missing row: pure gap lock, no record lock.
    mgr.acquire(1, GAP, "X", ("gap", gap), log)
    mgr.acquire(2, GAP, "X", ("gap", gap), log)   # granted: gap vs gap is OK
    mgr.cover_gap(1, gap, log)
    mgr.cover_gap(2, gap, log)
    for line in log:
        print(line)
    log = []
    print("  -- both sessions now insert --")
    b1 = mgr.try_insert(1, 15, log)
    b2 = mgr.try_insert(2, 15, log)
    for line in log:
        print(line)
    print(f"  wait-for graph: T1 waits for T{b1}, T2 waits for T{b2} -> cycle")
    victim = 2   # InnoDB picks the smaller-undo transaction as victim
    print(f"  InnoDB deadlock detector fires; victim = T{victim}")
    mgr.gap_cover[victim].discard(gap)
    mgr.locks[("gap", gap)].pop(victim)
    log = []
    ok = mgr.try_insert(3 - victim, 15, log)
    for line in log:
        print(line)
    print()

def part2():
    print("PART 2: next-key coverage for SELECT id BETWEEN 20 AND 30 FOR UPDATE")
    keys = [10, 20, 30, 40, 50]
    mgr = LockMgr(keys)
    log = []
    # A serializable range scan takes a next-key lock on every record it
    # touches (record + gap before it), plus one gap lock past the range.
    for k in (20, 30):
        mgr.acquire(1, NEXT_KEY, "X", ("rec", k), log)
        mgr.cover_gap(1, (k - 10, k), log)          # gap before k
    mgr.acquire(1, GAP, "X", ("gap", (30, 40)), log)  # gap after range
    mgr.cover_gap(1, (30, 40), log)
    for line in log:
        print(line)
    print("  -- probe inserts from T2 --")
    log2 = []
    for probe in (15, 25, 35, 45):
        mgr.try_insert(2, probe, log2)
    for line in log2:
        print(line)
    print()
    print("coverage rule: next-key on key k guards the gap (prev(k), k];")
    print("key 20 guards (10,20], key 30 guards (20,30], extra gap guards")
    print("(30,40). Phantom 25 cannot appear: it lands inside (20,30].")

part1()
part2()
```

Real output of the script above:

```text
PART 1: two-session phantom-insert deadlock (the MySQL gap-lock case)
index keys: 10, 20 | both sessions run SELECT id=15 FOR UPDATE
(no row 15), then both INSERT id=15.
    T1: GAP/X on ('gap', (10, 20)) granted
    T2: GAP/X on ('gap', (10, 20)) granted
    T1: gap (10, 20) now guarded
    T2: gap (10, 20) now guarded
  -- both sessions now insert --
    T1: INSERT 15 blocked: insert-intention lock on (10, 20) waits for T2's gap lock
    T2: INSERT 15 blocked: insert-intention lock on (10, 20) waits for T1's gap lock
  wait-for graph: T1 waits for T2, T2 waits for T1 -> cycle
  InnoDB deadlock detector fires; victim = T2
    T1: INSERT 15 proceeds

PART 2: next-key coverage for SELECT id BETWEEN 20 AND 30 FOR UPDATE
    T1: NEXT_KEY/X on ('rec', 20) granted
    T1: gap (10, 20) now guarded
    T1: NEXT_KEY/X on ('rec', 30) granted
    T1: gap (20, 30) now guarded
    T1: GAP/X on ('gap', (30, 40)) granted
    T1: gap (30, 40) now guarded
  -- probe inserts from T2 --
    T2: INSERT 15 blocked: insert-intention lock on (10, 20) waits for T1's gap lock
    T2: INSERT 25 blocked: insert-intention lock on (20, 30) waits for T1's gap lock
    T2: INSERT 35 blocked: insert-intention lock on (30, 40) waits for T1's gap lock
    T2: INSERT 45 proceeds

coverage rule: next-key on key k guards the gap (prev(k), k];
key 20 guards (10,20], key 30 guards (20,30], extra gap guards
(30,40). Phantom 25 cannot appear: it lands inside (20,30].
```

Note in Part 2 that INSERT 45 is allowed even though the scan's next-key locks cover much of the index — coverage is exact, not whole-table. Note in Part 1 that the deadlock is *not* a bug: it is the price of the "gap locks coexist" rule, and every MySQL operator eventually meets it (typically via batch upserts from workers scanning overlapping missing keys).

## Serializable: Range Locks vs SSI

There are exactly two families of full serializability in production engines, and they take opposite bets about where the cost goes:

| Property | Key-range S2PL (InnoDB SERIALIZABLE, SQL Server range locks) | SSI (PostgreSQL) |
|----------|---------------------------------------------------------------|------------------|
| Mechanism | Acquire next-key/range locks at read time, hold to commit | Optimistic: track rw-antidependencies, abort "dangerous structures" at commit |
| Phantom prevention | Insert physically blocked until scanners commit | Phantom inserts proceed; conflicting committer aborts |
| Cost profile | Readers block writers for the transaction duration | Locks are cheap, but commit-time aborts under contention |
| Failure mode | Throughput collapse, gap deadlocks | Serialization failures (`40001` retries) |
| Best when | Conflicts are rare and short | Conflicts are rare *and* transactions are long |

The pessimistic family never aborts a committed transaction but pays with blocked inserts and gap deadlocks (as above). SSI never blocks but pays with aborts — the dangerous-structure detection is exactly a *deferred* predicate-conflict test. Neither dominates; see the deeper protocol analysis in [serializable-snapshot-isolation.md](serializable-snapshot-isolation.md) and the isolation-level mechanics in [../transactions/isolation-levels.md](../transactions/isolation-levels.md).

SQL Server packages the same idea differently: under SERIALIZABLE it takes **range locks** (types `RangeS-S`, `RangeS-U`, `RangeX-X`) that lock the interval between consecutive keys in a single lock resource — conceptually identical to InnoDB's record-plus-gap pairing, but expressed as one lock object per range rather than a record lock plus a gap lock. The same "two readers then two writers" phantom scenario deadlocks there for the same reason.

## Operational Notes

- **Supremum hot-spots.** Monotonic inserts (auto-increment PKs, append-only event tables) all target the top gap. Under REPEATABLE READ, any serializable scan that reaches the supremum pseudo-record serializes inserts behind it — append-heavy tables should stay on READ COMMITTED.
- **Gap deadlocks are retry-legal.** Error 1213 rolls the victim back atomically; retry logic is mandatory for any workload mixing range scans with inserts. `SHOW ENGINE INNODB STATUS` prints the two statements, each side's locks (`lock_mode X locks gap before rec`), and the victim; `performance_schema.data_locks` shows live GAP vs INSERT_INTENTION holders at lock-resolution time.
- **Escalation is the exit ramp.** When range locking costs too much (thousands of gap locks per scan), the pragmatic answers are: coarser granularity (escalate to page/table), weaker isolation (READ COMMITTED drops gap locks), or optimistic concurrency ([optimistic-concurrency.md](optimistic-concurrency.md)) — the same ladder Gray et al. proposed in the 1970s.

## References

1. K. P. Eswaran, J. N. Gray, R. A. Lorie, I. L. Traiger, "The notions of consistency and predicate locks in a database system," *Communications of the ACM* 19(11), 1976. doi:10.1145/360363.360369 (verified via Crossref).
2. J. N. Gray, R. A. Lorie, G. R. Putzolu, I. L. Traiger, "Granularity of locks in a shared data base" — the multi-granularity intention-lock protocol. doi:10.1145/1282480.1282513 (verified via Crossref).
3. MySQL 8.0 Reference Manual, §17.7.1 "InnoDB Locking" — record, gap, next-key, insert-intention, and AUTO-INC lock definitions. https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html (probed: HTTP 200).
4. MySQL 8.4 Reference Manual, §17.7.4 "Phantom Rows" — next-key locking algorithm and the two-session gap deadlock example. https://dev.mysql.com/doc/refman/8.4/en/innodb-next-key-locking.html (probed: HTTP 200).
5. Microsoft Learn, "SQL Server transaction locking and row versioning guide" — key-range locks under SERIALIZABLE and lock-escalation thresholds. https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide (probed: HTTP 200).
