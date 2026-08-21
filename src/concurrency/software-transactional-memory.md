# Software Transactional Memory

## Overview

Software Transactional Memory (STM) is a concurrency primitive that
applies database-style optimistic transactions to in-memory shared
state. Inside an `atomic { ... }` block you can read and write shared
variables without taking locks; the runtime tracks what you read
(the **read-set**) and what you write (the **write-set**), executes
the block speculatively, validates at commit that no one else changed
your read-set, and either commits your writes atomically or restarts
the block from scratch. The result is compositional concurrency:
two `atomic` blocks compose by sequencing, with no global lock order
to discover and no deadlock to worry about.

STM was proposed by Shavit and Touitou in 1995 as a software
reimplementation of Herlihy and Moss's hardware transactional memory
(HTM). Harris's *Composable Memory Transactions* (2005) gave the model
its first-class Haskell implementation and proved that `retry` and
`orElse` could compose transactions as first-class values. Clojure's
`dosync`/`ref` system, the Scala STM standard, and the recent C++ and
Java incubator STM proposals all derive from these sources.

This page covers the `atomic` block, the read-set and write-set, the
optimistic execution and validation loop, the retry on conflict, the
read-lock versus write-lock distinction, the global commit counter,
the Haskell STM API, Clojure's `dosync` and refs, the Scala STM, and
the comparison to locks and to MVCC databases. (For Intel TSX and HTM,
see [Transactional Memory](./transactional-memory.md).)

## The `atomic` block

Conceptually, STM replaces:

```rust
// Hand-rolled locks: every site must discover the right lock order.
fn transfer(from: &Account, to: &Account, amount: u64) {
    // The order matters: lock(from) then lock(to) or vice versa?
    let g1 = from.lock();
    let g2 = to.lock();                 // if someone does to->from, deadlock
    *g1 -= amount;
    *g2 += amount;
}
```

with:

```rust
// STM: no lock order to discover, no deadlock possible.
fn transfer(from: &TVar<u64>, to: &TVar<u64>, amount: u64) {
    atomic(|tx| {
        let bal = from.read(tx)?;
        if bal < amount { return Err(retry()); }
        from.write(tx, bal - amount);
        let to_bal = to.read(tx)?;
        to.write(tx, to_bal + amount);
        Ok(())
    });
}
```

`TVar` is a *transactional variable*: a single memory cell whose reads
and writes inside `atomic` are tracked. Outside `atomic`, `TVar`s are
invisible — you cannot read them without a transaction. That is the
type-system-enforced invariant that lets STM be safe.

## Read-set, write-set, and the optimistic loop

Every transaction tracks two structures:

```
   read-set   = { (addr, value_observed_at_read, version_at_read) }
   write-set  = { (addr, new_value, ) }
```

The execution proceeds in four phases:

```
   1. BEGIN     snapshot the global commit counter; record read_version
   2. EXECUTE   read TVar -> record in read-set (return stale if cached)
                write TVar -> record in write-set (do NOT publish)
   3. VALIDATE  for each (addr, v0) in read-set:
                   if addr.version != v0 -> conflict, abort
   4. COMMIT    acquire global lock (or use CAS on each addr)
                write back write-set values
                bump global commit counter
                release lock
```

The crucial point: writes are not published until commit. A concurrent
reader in another transaction sees either the pre-transaction value
(your writes are still in your write-set) or the post-transaction value
(your commit has completed). It never sees a partial state.

```
   Thread A atomic block              Thread B atomic block
   -----------------------            -----------------------
   BEGIN; rv = global = 10
   x.read() -> reads x@v3
   y.read() -> reads y@v7
   x.write(99)  -- to write-set
                                       BEGIN; rv = global = 10
                                       y.read() -> reads y@v7  (same snapshot)
                                       y.write(11) -- to write-set
                                       VALIDATE: x unchanged, y@v7 matches -> OK
                                       COMMIT: y := 11; global := 11
   VALIDATE: x unchanged but y now v8 != v7 -> conflict
   ABORT, restart block from line 1
```

Validation is the heart of the algorithm. It is also what makes
transactions cheap to retry: the cost of an abort is the cost of
re-running the block, plus the cost of throwing away the write-set.
No I/O, no persistent side effects, no rollback log — because nothing
was published.

## Retry on conflict

When validation detects a conflict, the transaction restarts from the
beginning. The retry has two modes:

- **Spinning** (Harris's original Haskell STM): busy-retry until
  something has changed. Cheap on contention-free paths; under heavy
  contention it becomes a livelock — multiple threads abort and retry
  in lockstep.
- **Blocking** (also Harris, via `retry`): the transaction registers
  the read-set as waiters on each `TVar` it read; when one of those
  `TVar`s is updated by a committing transaction, the runtime wakes
  the waiter and re-runs the block. This avoids spinning and is the
  basis of the `retry` primitive (see below).

The compositional win is that `retry` is not a control-flow primitive
— it is a value. A transaction that calls `retry` is a transaction
that says "I cannot complete now; please wait until at least one of
my reads changes, then re-run me." That is enough to build
synchronization primitives (MVars, semaphores, condition variables)
without locks.

## The read-lock: no write-lock

A subtle but important point: a transaction holds a *read-lock*, not
a write-lock, on the variables it has read. A read-lock is a sentinel
that says "I am depending on this value not to change until I commit."
Multiple transactions can hold read-locks on the same `TVar`
simultaneously — that is, in fact, the common case, because most
transactions on most variables are read-only. A write-lock, by
contrast, is exclusive; STM deliberately does not need it during
execution because the write-set is private to the transaction.

```
   time ---->
   T1:  R(x) -------------------[validate]--------[commit: write x=99]
   T2:  R(x) ---------[commit: write x=2]                 ^T1 aborts
   T3:  R(x) R(y) ----------------------------------[commit: writes none]

   T1 holds a read-lock on x; T2 holds a read-lock on x, then a write-lock
   at commit. T3 holds read-locks on x and y; never writes, so its
   validation just checks that the versions have not bumped.
```

This is why STM scales better than locks on read-heavy workloads: a
thousand transactions can read the same `TVar` simultaneously, all
holding read-locks, and the system makes progress. The same situation
under locks would serialize on the read lock.

## The global commit counter

To avoid scanning the entire read-set at validate time, implementations
maintain a **global commit counter** that is bumped on every successful
commit. At `BEGIN`, the transaction reads the counter into a local
`rv`. At `VALIDATE`, it checks whether the counter has changed since
`rv`. If it has not, no other transaction has committed and the
read-set is trivially valid; the whole validation is one cache-line
read. If it has, the transaction walks the read-set to find which
specific variable invalidated it.

```
   BEGIN:    rv = atomic_load(global_commit_counter)
   READ:     v = TVar.value; TVar.version -> read_set
   VALIDATE: if (atomic_load(global_commit_counter) == rv)
                  read-set is valid, fast path (one cache line)
             else
                  walk read-set, check each TVar.version
   COMMIT:   acquire_lock_all_write_set_vars()
             (re-validate, in case someone committed between VALIDATE
              and lock acquisition)
             publish write-set values
             atomic_fetch_add(global_commit_counter, 1)
             release_locks
```

This is the classic TL2 (Transactional Locking II) algorithm by Dice,
Shalev, and Shavit (2006); it is the basis of most modern STMs,
including the Deuce STM and the Scala STM. The original 1995 Shavit
algorithm used a simpler but slower global version clock; TL2 added
the per-object lock/version pair to make commit cheap.

## Haskell STM

Haskell's STM is the cleanest expression of the model. The
`Control.Concurrent.STM` library exposes:

```haskell
data TVar a                 -- transactional variable
newTVar   :: a -> STM (TVar a)
readTVar  :: TVar a -> STM a
writeTVar :: TVar a -> a -> STM ()
retry     :: STM a           -- give up this attempt, wait for change
orElse    :: STM a -> STM a -> STM a  -- try first, on retry try second
atomically :: STM a -> IO a  -- run a transaction to completion
```

The type system makes STM safe: the `STM` monad cannot do I/O (you
cannot print or send a network packet from inside a transaction, so
retry is always cheap and side effects are always outside the
transaction). The classic example — the bounded concurrent queue:

```haskell
module TQueue (TQueue, newTQueue, readTQueue, writeTQueue) where

import Control.Concurrent.STM

data TQueue a = TQueue (TVar [a]) (TVar [a])

newTQueue :: STM (TQueue a)
newTQueue = do
  read  <- newTVar []
  write <- newTVar []
  return (TQueue read write)

writeTQueue :: TQueue a -> a -> STM ()
writeTQueue (TQueue _ write) a = do
  xs <- readTVar write
  writeTVar write (xs ++ [a])

readTQueue :: TQueue a -> STM a
readTQueue (TQueue read write) = do
  xs <- readTVar read
  case xs of
    (x:xs') -> do writeTVar read xs'
                  return x
    []      -> do
        ys <- readTVar write
        case ys of
          []      -> retry              -- queue empty, block
          _       -> do
              writeTVar write []
              writeTVar read (reverse ys)
              readTQueue (TQueue read write)   -- retry once, head now ready
```

The compositional payoff is `orElse`: if `readTQueue q1` retries
because q1 is empty, the alternative `readTQueue q1 `orElse`
readTQueue q2` blocks on *both* queues, returning whichever has a
value first. Try writing that with condition variables and you will
need two condition variables, a mutex, and the surrounding code will
not compose with anything else.

## Clojure's `dosync` and refs

Clojure's STM is the most widely deployed in production. Its
abstractions are:

```clojure
(def balance (ref 1000))

(dosync
  (alter balance + 100)        ; commute-style update inside transaction
  (ref-set balance 0))         ; direct assignment

;; Commute: read-modify-write with retry
(def counter (ref 0))
(dosync
  (commute counter inc))       ; coalesce concurrent inc operations
```

Clojure has three ref-update primitives: `ref-set` (write), `alter`
(read-modify-write with retry), and `commute` (read-modify-write whose
result is associative; the runtime re-runs at commit using the latest
value, which lets commuting operations like `inc` collapse concurrent
calls). `commute` is a Clojure-specific optimization: when a write
function is purely arithmetic and associative, you do not need to
abort on conflict — just re-apply the function at commit using the
current value.

The Clojure STM uses a multiversion scheme: each `ref` carries a
history of values, and a transaction reads the value that was current
at its `BEGIN`. Write-set entries are buffered to commit time.
Clojure's STM was designed by Rich Hickey to work with persistent
data structures — the language's persistent vectors and maps are
immutable, so a transaction's writes are immutable snapshots stored
in the write-set, and commit is a pointer swap.

## Scala STM and the ScalaSTM standard

The Scala STM standard (ScalaSTM, by the EPFL group) is the closest
thing to a cross-language STM standard. It exposes `Ref` (analogous
to `TVar`), `atomic { ... }`, and `retry`:

```scala
import scala.concurrent.stm._

val balance = Ref(1000)

atomic { implicit txn =>
  balance() = balance() + 100
}

// Retry-based bounded queue
def take[T](q: Ref[List[T]])(implicit txn: InTxn): T = {
  val xs = q()
  if (xs.isEmpty) retry
  q() = xs.tail
  xs.head
}
```

ScalaSTM also supports `single` (an alternative impl that uses a
single global lock, suitable for low-contention workloads) and
`ccstm` (the contention-managed default). The standard's most
interesting feature is the `NestedAtomic` rule: nested `atomic`
blocks flatten into the enclosing transaction rather than starting a
new one, which preserves composability (one `atomic` block calling
another that calls `retry` retries the outer transaction, not just
the inner block).

## STM vs locks

```
   Property                       Locks              STM
   ---------                      -----              ---
   Deadlock                       possible            impossible (no waits)
   Compositional                  NO — lock order leaks  YES
   Progress                       blocking            optimistic, may starve
   Cost uncontended               low (1 atomic)      higher (rv + validate)
   Cost contended                 low (serialize)    low for reads, high for writes
   I/O inside critical section    possible            FORBIDDEN (must be outside atomic)
   Long-held critical section     fine                retried repeatedly -> bad
   Retry semantics                none                built-in (retry / orElse)
```

The composability argument is the load-bearing one: two `atomic`
blocks can be sequenced or nested without the programmer discovering
a lock order. Two locking critical sections composed together have a
deadlock waiting in the wings if the orders differ. For a
read-heavy, low-write system (a config map, a routing table, an
accounting ledger) STM is the right default; for a hot single
counter or a long-held critical section with side effects, locks
remain the right default.

## STM vs MVCC databases

STM and MVCC databases share the optimistic, snapshot-isolation
structure: both maintain a per-transaction snapshot, both validate at
commit, both abort on conflict. The differences:

```
   MVCC database                 STM
   -------------                 ---
   disk-resident, log-structured    in-memory, write-set is a buffer
   two versions per row + vacuum     N versions per TVar (or 2 in TL2)
   serializable via SSI              serializable via read-set validation
   durable (WAL)                      NOT durable (memory only)
   conflict on row-level predicate    conflict on cell version
```

The most important difference is durability: a database transaction's
commit hits a write-ahead log and survives a crash; an STM commit is
gone the moment the process exits. If you need durability, you need
the database. If you need compositional concurrency inside a single
process, you need STM. They are not substitutes for each other; they
solve different parts of the same problem and compose well when the
outer transaction is in a database and the inner work is in memory.

## Interview questions

### What is the read-set and what is the write-set?

The read-set is the set of memory cells the transaction has read,
together with the version observed at read time. The write-set is the
set of cells the transaction will write, with their new values,
buffered until commit. Validation walks the read-set; commit publishes
the write-set.

### Why does STM not deadlock?

Because a transaction never waits for another transaction to release a
lock. It either validates successfully and commits, or detects a
conflict and aborts to retry. There is no hold-and-wait, so the
circular-wait condition of the four Coffman conditions cannot occur.
(See [Deadlock Detection](./deadlock-detection.md) for the
conditions.)

### What is `retry` and why does it compose?

`retry` is a value (not a control-flow primitive) that aborts the
transaction and registers the read-set as waiters on each cell read.
When any cell in the read-set is updated, the runtime wakes the
transaction and re-runs it. It composes because `orElse` (try A, on
retry try B) gives you deterministic choice between alternatives,
and nested `retry` calls bubble up to the outermost transaction.

### When is STM the wrong choice?

When transactions are long, when the write-set is large, when the
workload is write-heavy on the same cells (continuous conflict causes
live lock), or when side effects (I/O, network) must happen inside
the critical section. STM is also wrong when you need priority or
fairness guarantees, because the runtime cannot promise either.

### How does Clojure's `commute` work?

`commute` defers the function application to commit time and re-runs
it against the latest value of the ref. Because the function is
associative (e.g. `inc`, `+`), concurrent commutes can be applied in
any order and the result is the same. This avoids aborts for
conflicting-but-associative updates.

## Cross-references

- [Transactional Memory](./transactional-memory.md) — the HTM (Intel
  TSX) counterpart; this page is the software-only side
- [Actor Model Deep Dive](./actor-model-deep.md) — a different
  composability story, built on asynchronous mailboxes
- [CSP Model](./csp-model.md) — composability built on synchronous
  rendezvous
- [Deadlock Detection](./deadlock-detection.md) — why STM eliminates
  the four Coffman conditions by construction
- [Lock-free Data Structures](./lock-free.md) — when CAS beats STM
- [ABA Problem](./aba-problem.md) — the CAS hazard that STM sidesteps
- [MVCC Internals](../dbms/advanced/mvcc-internals.md) — the
  database analogue of STM
- [Optimistic Concurrency](../dbms/advanced/optimistic-concurrency.md)
  — the same algorithm at the database level

## References

- Nir Shavit and Dan Touitou. *Software Transactional Memory*.
  PODC 1995. <https://groups.csail.mit.edu/tds/ShAvTaou95.pdf>
- Tim Harris, Simon Marlow, Simon Peyton Jones, Maurice Herlihy.
  *Composable Memory Transactions*. ACM PPoPP 2005.
  <https://www.microsoft.com/en-us/research/wp-content/uploads/2005/01/2005-PPoPP-ComposableMemoryTransactions.pdf>
- Tim Harris and Keir Fraser. *Language Support for Lightweight
  Transactions*. OOPSLA 2003.
  <https://www.cl.cam.ac.uk/research/srg/netos/lock-free/Harris-Fraser-2003.pdf>
- Dave Dice, Ori Shalev, Nir Shavit. *Transactional Locking II*.
  DISC 2006. <https://groups.csail.mit.edu/tds/ShAvi-DiSc-ShAle-2006.pdf>
- Haskell STM: Control.Concurrent.STM documentation.
  <https://hackage.haskell.org/package/stm-2.5.0.0/docs/Control-Concurrent-STM.html>
- Haskell documentation: Software Transactional Memory overview.
  <https://wiki.haskell.org/Software_transactional_memory>
- Clojure documentation: Concurrency, refs, and `dosync`.
  <https://clojure.org/reference/refs>
- ScalaSTM project: <https://nbronson.github.io/scala-stm/>
- Anthony Discolo, Patrick Heslin, Tim Harris, Maurice Herlihy, et al.
  *Transactional Locking II* — expanded journal version, and the
  reference implementation used by Deuce STM:
  <http://mcg.cs.tau.ac.il/projects/mtm/>
- Maurice Herlihy and J. Eliot B. Moss. *Transactional Memory:
  Architectural Support for Lock-Free Data Structures*. ISCA 1993.
  <https://www.cs.cmu.edu/afs/cs.cmu.edu/academic/class/15740-f03/www/doc/HerlihyMoss-TM.pdf>
