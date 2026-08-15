# Synchronization Primitives — Advanced

Beyond basic [spinlocks](../synchronization/spinlocks.md) and [mutex](../synchronization/mutex.md), production kernels require synchronization mechanisms that scale to hundreds of cores, minimize reader-writer contention, and handle the complex interactions between preemption, interrupts, and memory ordering. This section covers the advanced primitives that make Linux and similar systems work at scale.

## RCU — Read-Copy-Update

RCU (Read-Copy-Update, Paul McKenney) is a **wait-free read-side synchronization mechanism** used extensively in the Linux kernel (~20,000+ call sites). Readers access shared data without any locks, atomics, or memory barriers. Writers create new copies of data structures and free old copies after a **grace period** — the time after which all pre-existing readers have completed.

### How RCU Works

1. **Reader (critical section)**: `rcu_read_lock()` / `rcu_read_unlock()` simply disable preemption (they're `preempt_disable()` / `preempt_enable()`). No lock is acquired, no memory barrier is issued. The reader can access the data structure freely.

2. **Writer**: Creates a new version of the data structure, atomically swaps the pointer (using `rcu_assign_pointer()`), then waits for a grace period, then frees the old version.

3. **Grace period**: The time during which all CPUs go through at least one context switch (or explicit quiescent state). After this, no pre-existing reader can still hold a reference to the old data.

```c
// Reader (wait-free, no lock!)
rcu_read_lock();
struct my_struct *p = rcu_dereference(global_ptr);
if (p) {
    // Safe: p won't be freed until after grace period
    do_something(p->field);
}
rcu_read_unlock();

// Writer
struct my_struct *new = alloc_my_struct();
*new = *old;
new->field = new_value;

// Atomically publish new version
rcu_assign_pointer(global_ptr, new);

// Wait for all readers to finish, then free old
synchronize_rcu();  // blocks until grace period elapses
kfree(old);
```

### RCU Grace Period Detection

The Linux kernel implements multiple grace period mechanisms:

- **Tree RCU** (default for `CONFIG_PREEMPT_NONE`/`CONFIG_PREEMPT_VOLUNTARY`): Each CPU periodically reports a quiescent state (passing through the idle loop or context switch). A tree of per-CPU nodes propagates completion upward. Grace period completes when all CPUs have reported.

- **Preemptible RCU** (`CONFIG_PREEMPT_RCU`): Required when RCU readers can be preempted (PREEMPT_RT). Uses a more complex state machine tracking whether each CPU is in an RCU read-side critical section. Slower than Tree RCU but necessary for real-time response.

## SRCU — Sleepable RCU

Standard RCU readers cannot sleep (they disable preemption). **SRCU** (Sleepable Read-Copy Update) allows readers to sleep, block, or be preempted freely. Each SRCU domain has its own grace period counter.

```c
// Reader — CAN sleep!
int idx;
idx = srcu_read_lock(&my_srcu);
struct my_struct *p = srcu_dereference(global_ptr, &my_srcu);
if (p) {
    msleep(100);  // totally fine with SRCU
    do_something(p->field);
}
srcu_read_unlock(&my_srcu, idx);
```

SRCU is used in: filesystem VFS lookups (where the lookup might block on I/O), the V4L2 media subsystem, and Btrfs. The cost is higher than RCU: `srcu_read_lock()` involves atomic operations on a per-domain counter.

## QSBR — Quiescent-State-Based Reclamation

QSBR is the most extreme RCU variant: **readers do nothing** — no `rcu_read_lock()`, no `rcu_read_unlock()`. The reader simply ensures it's in a quiescent state (not in an RCU read-side critical section) periodically, and reports this to the QSBR subsystem.

```c
// Reader thread — no lock/unlock overhead at all!
// Just call this periodically (e.g., each event loop iteration)
rcu_quiescent_state();

// Writer — same as RCU
rcu_assign_pointer(global_ptr, new);
// Must wait for ALL reader threads to report a QS
synchronize_rcu();
kfree(old);
```

QSBR has near-zero read-side overhead but requires explicit reader cooperation (every reader thread must call `rcu_quiescent_state()`). Used in DPDK (user-space RCU) and in specialized kernel paths where the reader pattern is known.

## Hazard Pointers

Hazard pointers (Maged Michael, 2004) are an alternative to RCU for memory reclamation in lock-free data structures. Each thread maintains a small array (1-2 pointers) of **hazard pointers** — pointers to objects the thread is currently accessing. An object cannot be freed until no thread has it as a hazard pointer.

```
Thread 0: hazard[0] = &node_A   // "I'm reading node_A"
Thread 1: hazard[0] = &node_B
Thread 2: hazard[0] = &node_A   // "I'm also reading node_A"

Writer wants to retire node_A:
  1. Remove node_A from data structure (CAS on parent's next pointer)
  2. Add node_A to retire list
  3. Scan ALL threads' hazard pointers
  4. If no thread has node_A as a hazard pointer → free it
  5. Otherwise → retry later
```

Compared to RCU: hazard pointers don't require a global grace period, but scanning all threads' hazard pointers is O(H × N) where H is the number of hazard pointers per thread and N is the number of threads. RCU's grace period is O(1) amortized (tree propagation). Hazard pointers are preferred in user-space lock-free libraries where thread sets are small or dynamic.

## Epoch-Based Reclamation (EBR)

Epoch-based reclamation (Hart et al., 2007) divides time into **epochs** (global counter). Each thread periodically announces which epoch it's in. An object from epoch E can be freed when **all threads** have advanced past epoch E.

```
Global epoch = 3
Thread 0: local_epoch = 3   (has seen current epoch)
Thread 1: local_epoch = 2   (hasn't updated yet)
Thread 2: local_epoch = 3

Objects retired in epoch 1: SAFE to free (all threads > 1)
Objects retired in epoch 2: NOT SAFE (Thread 1 is still in epoch 2)
Objects retired in epoch 3: NOT SAFE (threads might still be reading)
```

EBR is simpler than RCU, has comparable read-side overhead (just read a global variable), but requires threads to periodically check in (like QSBR). Facebook's `folly/AtomicUnorderedMap` and Intel TBB use epoch-based reclamation.

## Futex — Fast Userspace Mutex

The futex (fast user-space mutex, 2002, Hubertus Franke) is the building block for `pthread_mutex`, `pthread_cond`, `std::mutex`, and most other userspace synchronization in Linux. A futex combines a **userspace atomic operation** with a **kernel wait queue**:

```c
// Simplified futex-based lock

// Fast path (no contention, no syscall):
int val = atomic_cmpxchg(&lock_word, 0, 1);  // userspace CAS
if (val == 0) {
    // Lock acquired — no syscall!
    return;
}

// Slow path (contention, enter kernel):
// val > 0 means lock is held; wait for it to become 0
futex(&lock_word, FUTEX_WAIT, 1, NULL, NULL, 0);
// Woken up — retry the CAS

// Unlock:
atomic_store(&lock_word, 0);
futex(&lock_word, FUTEX_WAKE, 1, NULL, NULL, 0);  // wake one waiter
```

The key insight: in the uncontended case, the lock is pure userspace — no syscall, no kernel entry. The kernel is only involved when there's contention. Linux's `PI-futex` (priority-inheritance futex) supports priority inheritance for real-time applications, preventing priority inversion.

Futex operations: `FUTEX_WAIT`, `FUTEX_WAKE`, `FUTEX_REQUEUE` (move waiters to another futex), `FUTEX_CMP_REQUEUE` (conditional requeue, used by `pthread_cond_broadcast`), `FUTEX_WAKE_OP` (atomic add-and-wake, used by semaphore implementations).

## Ticket Lock

The ticket lock is a simple, fair spinlock that eliminates the starvation possible with a basic test-and-set lock. It maintains two counters: `next_ticket` (next ticket to serve) and `now_serving` (currently serving).

```c
struct ticket_lock {
    uint16_t next_ticket;
    uint16_t now_serving;
} __attribute__((aligned(64)));

void ticket_lock(struct ticket_lock *lock) {
    uint16_t my_ticket = atomic_fetch_add(&lock->next_ticket, 1);
    while (lock->now_serving != my_ticket) {
        cpu_relax();  // pause instruction on x86
    }
}

void ticket_unlock(struct ticket_lock *lock) {
    lock->now_serving++;  // single writer, no atomic needed
}
```

Ticket locks are **FIFO fair** — threads acquire the lock in the exact order they arrived. However, they suffer from **cache-line bouncing**: every spinning thread reads the same `now_serving` cache line, causing the cache coherence protocol to constantly invalidate it across cores. On 64+ core systems, this becomes a significant scalability bottleneck.

## MCS Lock

The MCS lock (Mellor-Crummey and Scott, 1991) solves cache-line bouncing by building a **distributed queue** in the waiting threads' own cache lines:

```c
struct mcs_node {
    struct mcs_node *next;  // pointer to next waiter
    bool locked;            // "am I waiting for my turn?"
} __attribute__((aligned(64)));

void mcs_lock(struct mcs_node **lock_ptr, struct mcs_node *my_node) {
    my_node->next = NULL;
    struct mcs_node *prev = atomic_xchg(lock_ptr, my_node);
    if (prev != NULL) {
        my_node->locked = true;
        prev->next = my_node;  // link into queue
        while (my_node->locked) cpu_relax();  // spin on MY cache line
    }
    // Lock acquired
}

void mcs_unlock(struct mcs_node **lock_ptr, struct mcs_node *my_node) {
    if (my_node->next == NULL) {
        // Might be last in queue — try to clear lock_ptr
        if (atomic_cmpxchg(lock_ptr, my_node, NULL) == my_node)
            return;  // was last
        // Another thread arrived — wait for it to link
        while (my_node->next == NULL) cpu_relax();
    }
    my_node->next->locked = false;  // wake next waiter
}
```

Each thread spins on its **own** `locked` flag in its own cache line — no shared spinning, no cache-line bouncing. MCS is O(1) per acquisition in cache coherence traffic. The cost: each thread needs a per-lock `mcs_node` (typically on the stack), and the lock word must be passed around.

## qspinlock — Linux's Queue Spinlock

The `qspinlock` (v4.2+, default on x86/arm64) combines the **fast path of a simple spinlock** (single word, no per-CPU data) with the **scalability of MCS** for contended cases. It operates in three modes:

1. **Parked (no contention)**: The lock word is a simple `0` (unlocked) or `1` (locked). First locker does a single `atomic_cmpxchg`. No MCS node allocation.

2. **Queued (2+ waiters)**: The second waiter sets a "queued" bit and creates an MCS node. Subsequent waiters append to the MCS queue. Each waiter spins on its own node.

3. **Optimized (few waiters)**: For 1-3 waiters, the MCS queue is embedded directly in the lock word (using spare bits in the 32-bit lock word), avoiding separate node allocation.

```
Lock word layout (32-bit, x86):
[24 bits: tail CPU# | 1 bit: pending | 1 bit: locked]

State 0: 0x00000000  — unlocked
State 1: 0x00000001  — locked, no waiters (fast path, single cmpxchg)
State 2: 0x00000003  — locked + pending (second waiter arriving)
State 3: 0x00NN0003  — queued (N = tail CPU#, MCS queue active)
```

## Lock Convoying

A **lock convoy** occurs when a highly-contended lock causes threads to repeatedly wake up and immediately block because the lock holder released the lock while another thread was already in the process of acquiring it. This is particularly problematic with sleeping locks (mutexes) where the kernel must perform scheduler operations for each wake/block cycle.

Convoying is worse when: (a) the lock hold time is short but many threads contend, (b) the scheduler doesn't have FIFO handoff (the woken thread doesn't immediately get the CPU), and (c) the lock is associated with a resource that causes bursty access patterns (e.g., a global allocator lock during GC).

Solutions: MCS/qspinlock (no sleeping, distributed spinning), **handoff** (Linux futex `FUTEX_LOCK_PI` with priority handoff), and eliminating the shared lock entirely (sharding, per-CPU data). Modern Linux mutexes implement optimistic spinning before sleeping, which helps avoid the convoy in many cases.

## Comparison

| Primitive | Read Cost | Write Cost | Memory Reclamation | Use Case |
|-----------|-----------|------------|--------------------|----|
| Spinlock | ~10 ns | ~10 ns + backoff | N/A | Short critical sections |
| Ticket Lock | ~10 ns | ~10 ns | N/A | Fair spinning, few cores |
| MCS Lock | ~10 ns | ~20 ns | N/A | Many-core spinning |
| qspinlock | ~10 ns | ~15 ns | N/A | Linux kernel default |
| RCU | ~1 ns | ~µs (grace period) | Grace period | Read-mostly kernel data |
| SRCU | ~5 ns | ~µs | Per-domain GP | Readers that can sleep |
| QSBR | ~0 ns | ~µs | Quiescent state | Known reader patterns |
| Hazard Pointers | ~2 ns | O(H×N) scan | Per-pointer scan | User-space lock-free |
| EBR | ~1 ns | O(1) amortized | Epoch advance | User-space lock-free |
| Futex | ~10 ns (uncontended) | ~1 µs (contended) | N/A | Userspace mutex base |

## Interview Questions

1. **"How does RCU ensure old data isn't freed while a reader is using it?"** Answer hint: RCU defers freeing until a grace period elapses — the time after which all CPUs that were executing before the pointer swap have passed through a quiescent state (context switch, idle loop, or user-mode return). Since readers disable preemption, a reader in an RCU critical section cannot be context-switched, so it will complete before the CPU reports a quiescent state.

2. **"Why does the Linux kernel use qspinlock instead of MCS directly?"** Answer hint: MCS requires each thread to pass a per-lock node pointer, which complicates the API and requires stack allocation. qspinlock encodes the MCS queue in the lock word itself for the common case (1-3 waiters), falling back to per-CPU MCS nodes only for long queues. This gives MCS scalability with the simple API of a single-word spinlock.

3. **"What is lock convoying and how do you avoid it?"** Answer hint: A lock convoy is a pathological pattern where threads repeatedly sleep/wake on a contended mutex without making progress. Avoid by: using spinlocks for very short critical sections (avoid the scheduler entirely), using MCS/qspinlock for many-core spinning, implementing lock handoff (futex PI), or eliminating the contention point (sharding, per-CPU data, RCU for read-mostly data).

## References
- McKenney, P. "Is Parallel Programming Hard, And, If So, What Can You Do About It?" (RCU book, freely available)
- Michael, M. "Hazard Pointers: Safe Memory Reclamation for Lock-Free Objects." IEEE TPDS 2004.
- Hart et al. "Efficient Lock-Free Memory Reclamation Based on Quiescent States." ALENEX 2007.
- Franke, H. et al. "Fuss, Futexes and Furwocks: Fast Userlevel Mutexes." USENIX 2002.
- Corbet, J. "The qspinlock." LWN.net, 2013.
