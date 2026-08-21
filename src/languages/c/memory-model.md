# The C11 / C++11 Memory Model

## Why a Memory Model?

Before C11 and C++11, multithreaded C and C++ programs had **no portable semantics**.
The 1999 C standard (`ISO/IEC 9899:1999`) and the 2003 C++ standard did not mention
threads at all. Programs used POSIX threads, Win32 threads, or `__sync_*` compiler
intrinsics, and what worked on x86 broke on ARM because the hardware memory ordering
rules were different. Compiler writers exploited this freedom: a 2008 study by Hans-J.
Boehm showed that roughly half of the proposed "benign data race" patterns in real
code were in fact **undefined behavior** under any reasonable memory model.

The C11 and C++11 standards fixed this by adopting a single, formal model largely
designed by Boehm and Sarita Adve — the same authors who formulated the
**data-race-free (DRF)** model in their 1990 paper *"Sequential Consistency by
Default"* (PLDI '90). The model rests on four pillars:

1. A library of atomic types and operations with explicit ordering constraints.
2. The **happens-before** relation, a partial order over memory operations across
   threads.
3. The rule that a **data race is undefined behavior**.
4. The **DRF-SC guarantee**: if your program has no data races, then it executes
   as if it were **sequentially consistent** (SC) — the strong, intuitive model
   where all threads see one global interleaving.

The C11 wording lives in §5.1.2.4 ("Multi-threaded executions and data races") and
§7.17 (`<stdatomic.h>`). The C++11 wording lives in §1.10 and §29 (`<atomic>`).
They are essentially the same model; the C++ standard has slightly more
infrastructure (atomic wrappers, default orderings) and C23 caught up further.

## The Happens-Before Relation

`happens-before` (HB) is the heart of the model. It is a transitive, irreflexive
partial order between **evaluations** (reads, writes, synchronization actions)
executed across one or more threads. The key idea: a write `A` is visible to a
read `B` on another thread only if `A` **happens-before** `B`. Otherwise the read
may see either an old value or the new one — and if the two operations form a
"non-synchronizing" race, the program is UB.

HB is composed from three primitives:

| Source of HB                                          | Induced by                                        |
|-------------------------------------------------------|---------------------------------------------------|
| **Sequenced-before** (within one thread)              | Program order: each statement before the next     |
| **Synchronizes-with** (across threads)                | A release store on atomic X synchronizes-with an acquire load on X that reads the value the release wrote |
| **Carries-dependency** (within thread, on data)       | A dependency-ordered carry through relaxed ops    |

HB is the **transitive closure** of the union of those three. Once the compiler
(or you) can prove `A happens-before B`, the value written by `A` must be visible
to `B`. Without such a chain, anything goes.

```
Thread 1                         Thread 2
--------                         --------
data = 42;          // (A)
flag.store(1,       // (B) release
    memory_order_release);
                                 // (C) acquire load: reads 1
                                 while (flag.load(memory_order_acquire) != 1);
                                 print(data);   // (D) guaranteed to see 42
```

The chain here is `(A) sequenced-before (B)` on thread 1, `(B) synchronizes-with (C)`
because (C) reads the value (B) wrote, and `(C) sequenced-before (D)` on thread 2.
Therefore `(A) happens-before (D)` and the read of `data` is well-defined.

## Data Races Are Undefined Behavior

C11 §5.1.2.4 §25 (and C++11 §1.10 §21) defines a **data race** as:

> Two actions are *potentially concurrent* if they are performed by different
> threads, or they are unsequenced, and they are not adjacent to each other. A
> program has a **data race** if, in any consecution, two potentially concurrent
> actions both touch the same memory location and at least one is not atomic
> and neither happens-before the other.

The penalty for a data race is not "you might see a stale value" — it is **full
undefined behavior**, indistinguishable from a null dereference. The compiler may
reorder, register-allocate, or delete the racing access entirely. The DRF-SC
theorem then says: if your program is DRF under the SC model, the implementation
is allowed to assume away all the things UB lets it assume, and you get SC
executions for free.

This is the same trick that makes C fast. C2x and C++17 keep the rule intact.

## The `memory_order_*` Enumerations

C11 and C++11 define a single enumeration, `memory_order` in `<stdatomic.h>` /
`<atomic>`, with six values:

```c
typedef enum {
    memory_order_relaxed,     // no ordering, only atomicity
    memory_order_consume,    // dependency-ordered (rarely implemented as acquire)
    memory_order_acquire,    // no reads/writes reordered before this load
    memory_order_release,    // no reads/writes reordered after this store
    memory_order_acq_rel,    // acquire+release on a read-modify-write
    memory_order_seq_cst     // sequentially consistent (the default)
} memory_order;
```

Each puts different constraints on what the compiler and CPU may reorder:

```
Order          Cost (typical x86)     Effect
-----------    -------------------    -------------------------------------
relaxed        MOV (no fence)        atomic only; no ordering guarantees
acquire        MOV (load-acquire)    later ops cannot move before it
release        MOV (store-release)   earlier ops cannot move after it
acq_rel        LOCK CMPXCHG          both acquire and release on RMW
seq_cst        MOV + MFENCE          total order with all SC ops
```

A good mental picture of the lattice of orderings (SC at the top, relaxed at the
bottom):

```
         seq_cst            <-- strongest, slowest
           |
        acq_rel             (only valid on RMWs)
        /     \
   acquire   release
       \      /
        consume             (in practice treated as acquire)
           |
        relaxed             <-- weakest, fastest
```

Choosing the weakest order that preserves correctness is the standard idiom for
high-performance atomics. Sequence-locked readers (Linux kernel's `seqlock_t`,
`std::atomic<bool>` flags, RCU read-side indicators) almost always use
`acquire/release` rather than `seq_cst`.

## A Concrete Example: Spinlock

```c
#include <stdatomic.h>
#include <stdbool.h>

typedef struct { atomic_flag locked; } spinlock_t;

void spin_lock(spinlock_t *s) {
    while (atomic_flag_test_and_set_explicit(
               &s->locked, memory_order_acquire)) {
        /* spin */
    }
}

void spin_unlock(spinlock_t *s) {
    atomic_flag_clear_explicit(&s->locked, memory_order_release);
}
```

The unlock is a **release store**: every load and store inside the critical section
is sequenced-before it, so it cannot move past the unlock. The lock's
`test_and_set` is an **acquire load**: no memory operation in the critical section
can be hoisted before the lock is acquired. Together they create the HB edge the
critical section needs. Note we deliberately avoid `seq_cst`; on x86 the only
overhead of `seq_cst` versus `acq_rel` is the trailing `MFENCE` on stores, but on
ARM/POWER it is a `DMB ISH` heavyweight fence — measurable on contended locks.

## Compare-Exchange and Per-Operation Orderings

`atomic_compare_exchange_strong` / `_weak` are the cornerstone of lock-free
algorithms. They take **two** memory orders: one for the success case, one for the
failure case:

```c
int expected = 5;
bool ok = atomic_compare_exchange_strong_explicit(
    &v, &expected, 7,
    memory_order_acq_rel,   // success: RMW that both acquires and releases
    memory_order_acquire);  // failure: just a load — no writes happened
```

This asymmetry is a real optimization. On a CAS loop retrying many times before
succeeding, the failure path only needs to *load* the current value — there is
nothing to release. Treating failure as `acq_rel` would emit an unnecessary fence
per failed iteration.

A common idiom for the failure case is "we saw the value, but someone else moved
first." On failure, the implementation **loads** the current value into `expected`,
and that load must respect the failure ordering. If the failure order is
`relaxed`, the load is allowed to see a value that is "older" than the latest
write — which is fine for retry loops that just want a fresh value to retry
against. If the failure order is `acquire`, the load acts as an acquire load
and synchronizes with any prior release store whose value the CAS sees.

## Fences: `atomic_thread_fence`

Fences are standalone operations that impose ordering without performing a memory
access. Their semantics are subtle: a release fence combined with an atomic load
can pair with an acquire load elsewhere:

```c
// Thread 1
data = 42;
atomic_thread_fence(memory_order_release);
flag.store(1, memory_order_relaxed);   // relaxed store, but paired with fence

// Thread 2
while (flag.load(memory_order_relaxed) != 1)
    ;
atomic_thread_fence(memory_order_acquire);
print(data);  // sees 42
```

The release fence ensures `data = 42` is not reordered after the relaxed store of
`flag`; the acquire fence ensures the read of `data` is not hoisted before the
relaxed load. Fences give finer control than per-operation orderings —
particularly useful when many relaxed stores happen and you want a single fence to
"flush" them.

There is also `atomic_signal_fence`, which is only a **compiler barrier**: it emits
no machine fence, but prevents the compiler from reordering across it within a
signal handler context. Using `atomic_thread_fence` in signal-handler-safe code is
wrong — the hardware fence is heavier than necessary and may not even be safe
inside a signal handler.

## The DRF-SC Theorem, Concretely

Boehm and Adve's PLDI 1990 paper proved that if every pair of conflicting memory
operations in a program is ordered by HB (i.e., no data races), then there exists
an SC execution that produces the same observable behavior. The C11/C++11 model
operationalizes this by saying: implementations may use any execution consistent
with the rules, but a program that is DRF has its SC executions preserved.

What this means in practice:

- If you use only `seq_cst` atomics and you have no data races, you get the
  intuitive interleaving semantics.
- If you use weaker orderings, you must add explicit synchronization (release/
  acquire pairs, fences, or dependency ordering) to create HB edges where data
  needs to flow.
- If you have a race on non-atomic memory, your program is broken, period — no
  ordering will save it.

## Comparison to the Java Memory Model

Java has had a memory model since 1995, but the original was so broken that
double-checked locking was famously wrong (a 2001 paper by David Bacon and
others catalogued the failure modes). JSR-133, finalized in 2004, defined a
**different** model from C11/C++11. The key contrasts:

| Aspect                        | C11/C++11                              | Java JMM (JSR-133)                          |
|-------------------------------|----------------------------------------|---------------------------------------------|
| Atomic types                  | `atomic_int`, `std::atomic<T>`         | `int`, `long` + `volatile` (post-JSR-133)   |
| Default ordering              | `seq_cst`                              | `volatile` is roughly acquire/release       |
| Data race on shared variable  | **Undefined behavior**                 | Defined: out-of-thin-air reads "prohibited" |
| Out-of-thin-air reads         | Allowed by the formal model (a known wart; prevented in practice by implementations) | Explicitly forbidden                          |
| Final fields                  | N/A                                    | Special: safe publication guarantee         |
| Memory model in spec?         | Yes, since C11/C++11                   | Yes, since Java 5 (JSR-133)                 |

The deepest difference is the **consequence of a race**. In C/C++, racing on
non-atomic memory is UB. In Java, a race is defined (you might see stale or
partially-constructed values, but the JVM is constrained in what it can do — it
cannot, for example, fabricate arbitrary values out of thin air). This makes
C/C++ harder to write but easier to optimize aggressively, and Java safer but
harder to optimize.

A notorious consequence: C/C++'s relaxed memory order formally permits an
"out-of-thin-air" value to appear. For example:

```c
atomic_int x = 0, y = 0;
// Thread 1: r1 = x.load(relaxed); y.store(r1, relaxed);
// Thread 2: r2 = y.load(relaxed); x.store(r2, relaxed);
```

Under a literal reading of the C11 model, both `r1` and `r2` could be `42` if both
threads "speculatively" chose 42 and then justified each other. Real CPUs do not
do this, and the C++ standards committee has spent years trying to patch the
formalism without breaking existing code (see N2382 and follow-on proposals). The
JSR-133 group just prohibited the outcome by fiat.

## When to Use What

| Pattern                                       | Recommended order            |
|-----------------------------------------------|------------------------------|
| Atomic counter (statistics, reference count) | `relaxed`                    |
| Single producer / single consumer flag        | `release` store + `acquire` load |
| Mutex implementation                          | `acquire` lock + `release` unlock |
| Lock-free queue (Michael-Scott)               | `acq_rel` on CAS, `release` enq, `acquire` deq |
| Once-init (`pthread_once`-style)              | `seq_cst` for the gate load  |
| Volatile flag termination check                | `relaxed` load (often)       |

## Interview Questions

1. **Why is `memory_order_relaxed` not enough for a spinlock?** Because without
   acquire/release pairing, the compiler and CPU may move the protected loads and
   stores outside the critical section. Relaxed only buys you atomicity of the
   single op.
2. **What is the difference between `seq_cst` and `acq_rel` on a CAS?** `seq_cst`
   additionally participates in a single global total order with all other SC
   operations. `acq_rel` only synchronizes with one matching acquire or release
   at a time, which is enough for most lock-free code but cannot express some
   algorithms (e.g., Dekker's mutual exclusion requires SC or explicit fences).
3. **Explain why a data race on `int` is UB even on x86, where hardware atomicity
   would make it "appear to work".** Because the compiler is free to assume no race
   exists and to optimize accordingly — register-allocation across threads,
   dead-store elimination, instruction reordering. The hardware isn't the only
   thing that can break you.
4. **When would you use `atomic_thread_fence` instead of an atomic operation with
   a strong memory order?** When you have many relaxed operations that should all
   be flushed with one fence; the per-op overhead of `seq_cst` would be
   multiplied across them.

## References

- ISO/IEC 9899:2011 (C11), §5.1.2.4 "Multi-threaded executions and data races" and §7.17 `<stdatomic.h>` — https://www.iso.org/standard/57853.html
- cppreference: `std::atomic` and C atomics reference — https://en.cppreference.com/w/c/atomic
- Hans-J. Boehm, Sarita V. Adve, *"Foundations of the C++ Concurrency Memory Model"*, PLDI 2008 — https://www.hpl.hp.com/techreports/2008/HPL-2008-56.html
- Hans-J. Boehm, Sarita V. Adve, *"Sequential Consistency by Default"*, original DRF paper, 1990 — https://dl.acm.org/doi/10.1145/93542.93545
- Herb Sutter, *"Atomic Weapons"* talks (Cppcon 2013/2014) — https://herbsutter.com/2013/09/30/atomic-weapons-the-c-memory-model-and-modern-hardware/
- Mark Batty et al., *"Mathematizing C++ Concurrency"*, POPL 2011 (the formal semantics) — https://www.cl.cam.ac.uk/~mjb220/papers/popl081.pdf
- JSR-133: Java Memory Model and Thread Specification — https://docs.oracle.com/javase/specs/jls/se8/html/jls-17.html
- Paul McKenney, *"Memory Barriers: a Hardware View for Software Hackers"* — https://www.paulmck.us/Talks/memory-barriers/
- N2382 (C++ "out-of-thin-air" problem) — http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p2382r0.html

## Related Topics

- [Undefined Behavior](./undefined-behavior.md) — data races are a special case of UB
- [Performance](./performance.md) — memory ordering cost on real CPUs
- [POSIX](./posix.md) — `pthread_once`, mutexes, condition variables
- [C++ Memory Model](../cpp/memory-model.md) — the C++11 side of the same model
