# Lock-Free Data Structures — Progress, CAS, and Safe Reclamation

A lock-free data structure is one where multiple concurrent operations
cannot get stuck waiting on each other: at least one thread makes
progress in a bounded number of steps. Building these is a strict
discipline. The semantics of the underlying atomic primitive
(compare-and-swap, or CAS), the memory model that wraps it, and the
lifetime policy for reclaimed nodes all have to line up. Get one wrong
and the algorithm is "lock-free" on paper but corrupts memory in
practice.

This chapter ties together material covered in
[Lock-Free Programming](./lock-free.md), [ABA and Reclamation](./aba-problem.md),
and [Atomic Primitives](./atomic-primitives.md). Read those first if
the vocabulary is unfamiliar.

## The progress guarantee hierarchy

Concurrent algorithms are classified by the kind of progress they
guarantee, not by the kind of synchronization they use. Herlihy and
Shavit's *The Art of Multiprocessor Programming* defines three useful
levels:

```
stronger
   |
   v
+-----------------------------+
| wait-free                   |  every thread, bounded steps
+-----------------------------+
| lock-free (non-blocking)    |  at least one thread, bounded steps
+-----------------------------+
| obstruction-free           |  progress only if running alone
+-----------------------------+
| lock-based                  |  no progress guarantee
+-----------------------------+
   |
   v
weaker
```

- **Wait-free**: every thread completes any operation in a finite,
  bounded number of its own steps. No thread starves. The bound is on
  *that thread's work*, not on wall-clock time.
- **Lock-free**: at least one thread makes progress in a bounded number
  of total steps. An individual thread may retry forever under heavy
  contention, but the *system* moves.
- **Obstruction-free**: a thread makes progress only if no other
  thread is currently executing. Useful as a stepping-stone, but not a
  real-world guarantee.
- **Lock-based**: no progress guarantee at all — deadlock, convoy,
  priority inversion, and lock-holder preemption are all possible.

Wait-free algorithms are notoriously hard to design. The classic
Herlihy-Shavit wait-free queue uses an `announce` array plus a helping
protocol where every operation completes every other in-flight operation
before returning. The constant factors are 3-5x worse than a lock-free
version. For most production systems, lock-free is the right stopping
point: it gives deadlock-freedom and system-wide progress without the
bookkeeping cost of wait-freedom.

## The CAS primitive

`CAS(addr, expected, new)` reads `*addr`, and if the value equals
`expected`, writes `new` and returns success. The whole sequence is
atomic with respect to other concurrent accesses to the same address.

```c
#include <stdatomic.h>

int cas(atomic_int *addr, int expected, int new_val) {
    return atomic_compare_exchange_strong(addr, &expected, new_val);
}
```

On x86 this lowers to `LOCK CMPXCHG`, which asserts the `#LOCK` signal
on the cache line for the duration of the operation. On ARM (v8+) it
lowers to an `LDXR`/`STXR` retry loop — the LL/SC pattern, where the
store-conditional fails if the cache line was touched by anyone else in
between. On PowerPC, `lwarx`/`stwcx.` is the same idea. The hardware
difference matters: x86 CAS never spuriously fails; ARM/Power CAS can
spuriously fail because of an interrupt, a context switch, or a
speculative memory access from another core. C++ exposes this through
`compare_exchange_weak`, which is allowed to return false even when the
value matched, and is the form you want inside a CAS loop. Use
`compare_exchange_strong` only outside a loop, e.g., for a one-shot
publication.

The CAS loop idiom — load-compute-CAS-retry — is the universal shape of
non-atomic read-modify-write on shared memory:

```rust
use std::sync::atomic::{AtomicUsize, Ordering};

fn increment(a: &AtomicUsize) {
    loop {
        let cur = a.load(Ordering::Acquire);
        let new = cur + 1;
        match a.compare_exchange_weak(
            cur, new,
            Ordering::AcqRel,   // success ordering
            Ordering::Acquire)  // failure ordering (no write happens)
        {
            Ok(_) => return,
            Err(actual) => cur = actual,  // compiler updates `expected`
        }
    }
}
```

The failure ordering is restricted: it cannot be `release` or
`acq_rel`, because a failed CAS performs no store. The
`acq_rel`/`acquire` pair above is the common pattern — the success side
publishes a write (release) and acquires what it loaded (acquire); the
failure side at least acquires what it saw.

## The ABA problem

A CAS checks that a *value* is unchanged. It does not check that the
*state of the world* is unchanged. If a value changes from A to B and
back to A, a CAS loop reading A will succeed even though two real
operations happened in between.

Concretely, consider a Treiber stack pop. Thread 1 reads `head = A` and
`A->next = B`. Before Thread 1's CAS, Thread 2 pops A, pops B (freeing
it), and pushes A back at the head. Thread 1's CAS succeeds because the
head still equals A — but `B` has been freed. Thread 1 returns `A`'s
value and also publishes `B` as the new head, dangling into freed
memory.

```
T1: load head=A, load A.next=B  (preempted)
T2: pop A   pop B   push A (reuses A's address)
T1: CAS(head, A, B) -> SUCCESS  (but B is freed)
```

See [ABA and Reclamation](./aba-problem.md) for the longer worked
example. There are two separable questions:

1. **Logical ABA:** did the shared state change and return to an equal
   value? Solve with a version tag.
2. **Lifetime safety:** can a thread still dereference an object that
   another thread has reclaimed? Solve with hazard pointers, epochs,
   RCU, or a managed runtime.

A tag addresses only the first; it does not keep a freed object alive
while a reader dereferences it.

## Tagged / pointer-packing fix

Pair the pointer with a monotonically increasing version. Every
successful update increments the version, so `A@v7` differs from
`A@v9` even though the pointer is the same address. The CAS now
compares the (pointer, version) pair atomically.

On 64-bit platforms where only 48 bits of the address are used (x86-64
and ARM64 canonical addresses), the remaining 16 bits can hold a tag in
place — no double-word CAS required. The cost: a finite tag wraps. The
wrap interval must exceed the maximum time a stale observation can
remain relevant, or you need a different scheme.

```cpp
struct TaggedHead {
    Node* ptr;
    uint64_t tag;          // increments on every successful update
};
// CAS over the (ptr, tag) pair as one atomic state
```

For platforms without a 2-word CAS, the tagged pointer trick can fall
back to a global lock, a packed tag, or an indirection through a
descriptor. Crossbeam's `Atomic<T>` uses a 2-word `AtomicU128` on
x86-64 when `cmpxchg16b` is available, and falls back to a smaller tag
otherwise.

## Hazard pointers — deferred reclamation

Maged Michael's hazard pointers solve the lifetime question. Each
reader publishes a per-thread slot announcing which node it is
currently dereferencing. A remover places removed nodes on a retire
list and periodically scans every hazard slot; only nodes that no
slot protects can be freed.

```cpp
// Reader (sketch — real impls are careful about publication ordering)
for (;;) {
    Node* p = head.load(std::memory_order_acquire);
    haz.store(p, std::memory_order_seq_cst);   // publish intent
    if (p == head.load(std::memory_order_acquire)) break;
    // p may have been freed; loop
}
use(p);
haz.store(nullptr, std::memory_order_release);

// Remover
retire(old);           // put on retire list
if (epoch_passed() && no_hazard_matches(old)) {
    delete old;
}
```

The reader pays a publication and a revalidation per protected pointer,
often with a sequentially consistent store. That is not free. The
remover pays O(N*H) per scan, where N is thread count and H is the
number of hazard slots per thread. Hazard pointers are a good fit for
structures where most reads are short and the retire list is small.

## Epoch-based reclamation — Crossbeam

Epoch-based reclamation (EBR) batches the cost. A reader pins itself in
a global epoch, does its work, unpins. A removed node is retired in the
current epoch. When every participant has advanced past that epoch, the
node can be freed.

```rust
use crossbeam_epoch::{self as epoch, Atomic, Owned};
use std::sync::atomic::Ordering;

let guard = epoch::pin();
let h = head.load(Ordering::Acquire, &guard);
if let Some(n) = unsafe { h.as_ref() } {
    inspect(n);               // safe while `guard` is pinned
}
unsafe { guard.defer_destroy(removed); }   // retired, freed later
```

EBR is much cheaper per read (one pin, one unpin, no per-pointer
publication) but has a stall sensitivity: a participant that stays
pinned prevents reclamation of every older epoch. Crossbeam uses three
buckets rotating through, so at most one stale epoch's worth of garbage
is retained — bounded memory growth in normal operation. See the
[Crossbeam documentation](https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/)
for the precise pin/unpin and guard contract.

For read-mostly workloads (kernel routing tables, dentry cache), Linux
RCU goes further: readers pay almost nothing on the fast path, and the
updater pays the full grace-period cost. See [RCU](./rcu.md).

## Treiber stack

The Treiber stack is the simplest lock-free stack. Push and pop are
each a single CAS on the head pointer.

```c
#include <stdatomic.h>
#include <stdlib.h>

typedef struct Node {
    int val;
    struct Node *next;
} Node;

static _Atomic(Node*) head = NULL;

void push(int v) {
    Node *n = malloc(sizeof *n);
    n->val = v;
    Node *old;
    do {
        old = atomic_load_explicit(&head, memory_order_acquire);
        n->next = old;
    } while (!atomic_compare_exchange_weak_explicit(
        &head, &old, n,
        memory_order_acq_rel,
        memory_order_acquire));
}

int pop(void) {
    Node *old;
    Node *new_head;
    do {
        old = atomic_load_explicit(&head, memory_order_acquire);
        if (!old) return -1;            // empty
        new_head = old->next;           // stale-safe only under EBR
    } while (!atomic_compare_exchange_weak_explicit(
        &head, &old, new_head,
        memory_order_acq_rel,
        memory_order_acquire));
    int v = old->val;
    /* reclaim `old` via hazard pointer / epoch; never `free` directly */
    return v;
}
```

The `acq_rel`/`acquire` orderings matter. The acquire on the load
pairs with the release side of the winning CAS: when a thread reads
`old`, it must see every write the publishing thread made to `old->val`
and `old->next` before its CAS. A relaxed load here is unsound — the
CPU is allowed to reorder the field reads after the CAS, exposing
uninitialized memory. (Linux's `READ_ONCE`/`smp_store_release` and
C11's `memory_order_consume` were attempts to make the
data-dependent-load case cheaper, but `consume` was effectively
downgraded to `acquire` everywhere.)

## Michael-Scott queue (1996)

The Michael-Scott queue is the canonical lock-free FIFO. It uses a
singly linked list with a sentinel (dummy) head node, and two atomic
pointers: `head` (dequeue end) and `tail` (enqueue end). The structure
has two CAS sites per enqueue and one per dequeue, plus a "help"
protocol where an in-progress enqueue is finished by the next arriving
enqueuer.

```
       head                           tail
        |                              |
        v                              v
   +--------+    +--------+    +--------+
   | dummy  | -> |   A    | -> |   B    | -> NULL
   +--------+    +--------+    +--------+
```

Enqueue (paraphrased from Michael & Scott, PODC 1996):

```c
void enqueue(Node *n) {
    n->next = NULL;
    Node *t, *next;
    for (;;) {
        t = atomic_load(&tail);                  // (1) read tail
        next = atomic_load(&t->next);            // (2) read tail.next
        if (next != NULL) {
            // tail is lagging; help advance it
            atomic_compare_exchange_weak(&tail, &t, next);
            continue;
        }
        // try to link n at tail.next
        if (atomic_compare_exchange_weak(&t->next, &next, n)) {
            // success; try to swing tail forward (may be done by a helper)
            atomic_compare_exchange_weak(&tail, &t, n);
            return;
        }
    }
}
```

Two important details:

1. The first CAS (`tail->next, NULL -> n`) is the *linearization point*
   of enqueue — once it succeeds, the node is reachable.
2. The second CAS (`tail, t -> n`) is just bookkeeping. If it fails
   (because a helper already advanced the tail, or because a
   simultaneous enqueuer won the race), the queue is still correct; the
   next enqueuer observes `tail->next != NULL` and helps it forward.

This "helping" pattern is what gives the queue its lock-freedom: a
stalled enqueuer cannot block the system because another enqueuer will
finish the stalled CAS for it.

Dequeue is a single CAS on the head, swinging it to the next node and
copying the value out of the (former) first real node. The sentinel
trick means we never dequeue into an empty queue — we copy from the
node *after* the sentinel, then free the sentinel and keep the new
sentinel.

The memory-ordering profile is the same as the Treiber stack: acquire
on reads, `acq_rel` on the success side of the CAS. Lifetime safety
requires hazard pointers, epochs, or a GC; the queue's correctness does
not give you the right to `free` nodes immediately on dequeue.

## Memory model requirements on CAS

The single most subtle point: a successful CAS only proves that the
compared atomic state matched. It does *not* prove that a pointer you
loaded earlier is still alive, and it does *not* prove that a
non-atomic field of the pointed-to object is initialized. For both of
those you need:

- **Publication ordering** — the writer must `release`-store the pointer
  *after* writing the fields, so the reader's `acquire`-load pairs
  correctly and sees the writes.
- **Lifetime protection** — hazard pointer, epoch, RCU, or GC must keep
  the object alive between the reader's load and its use of the
  pointer.

A CAS by itself with `memory_order_relaxed` is atomic on its address but
establishes no happens-before relationship for ordinary memory. A CAS
with `memory_order_acquire` on the failure path is *necessary* when a
retrying CAS needs to observe the most recent release-store of the
location. The C++ standard wording is that compare-exchange has two
memory-order arguments precisely because the failure path can have a
weaker ordering than the success path.

The most useful interview sentence in this area is from
[ABA and Reclamation](./aba-problem.md): CAS solves atomic state
transition; reclamation solves object lifetime. They are related, but
they are not the same problem.

## Choosing a scheme

For Rust: `crossbeam-epoch` is the production choice for general
lock-free structures. Hazard pointers (P2530, slated for C++26) give
per-pointer granularity at a higher per-read cost. For bounded pools, a
tagged index into a fixed array removes the lifetime question entirely
— there is no pointer to free, only a slot to mark reusable.

For Linux kernel code: use the kernel's RCU, refcount, and locking
APIs; do not roll your own reclamation.

For managed runtimes (JVM, CLR, Go): the GC handles lifetime, so a
lock-free algorithm only needs to be careful about publication ordering
(`volatile` in Java, `final` field semantics, `atomic.Value` in Go).

## Cross-references

- [Lock-Free Programming](./lock-free.md) — CAS loops in practice, language bindings
- [ABA and Reclamation](./aba-problem.md) — lifetime proofs and techniques
- [Atomic Primitives](./atomic-primitives.md) — hardware instructions and orderings
- [Memory Model](./memory-model.md) — happens-before across languages
- [RCU](./rcu.md) — kernel-grade deferred reclamation
- [Concurrent Queues](./concurrent-queues.md) — Treiber/Michael-Scott in production
- [Work-Stealing Scheduler](./work-stealing.md) — Chase-Lev deque uses CAS on both ends

## References

- Maurice Herlihy and Nir Shavit, *The Art of Multiprocessor Programming*, 2nd ed. (Morgan Kaufmann) — formal progress guarantees and wait-free queue construction. Author site: [cs.tau.ac.il/~shahar/](https://www.cs.tau.ac.il/~shahar/)
- Maged M. Michael and Michael L. Scott, ["Simple, Fast, and Practical Non-Blocking and Blocking Concurrent Queue Algorithms,"](https://www.cs.rochester.edu/research/concurrency/papers/popl-96.pdf) PODC 1996 — the Michael-Scott queue paper
- Maged M. Michael, ["Hazard Pointers: Safe Memory Reclamation for Lock-Free Objects,"](https://www.cs.otago.ac.nz/cosc440/readings/hazard-pointers.pdf) IEEE TPDS 15(6), June 2004 — original hazard pointers scheme
- Paul E. McKenney, [*Is Parallel Programming Hard, And, If So, What Can You Do About It?*](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html) — atomics and progress guarantees across architectures, with Linux RCU context
- Crossbeam documentation: [crossbeam-epoch](https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/) and [crossbeam-queue](https://docs.rs/crossbeam-queue/latest/crossbeam_queue/) — Rust epoch-based reclamation and lock-free queue implementations
- Herb Sutter, ["atomic<> Weapons" (CppCon 2012)](https://www.youtube.com/watch?v=Ke7dPhV9lys) — talk series covering ordering, fences, and hardware
- WG21 [P2530 — Hazard Pointers for C++26](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2023/p2530r3.pdf) standardization proposal
