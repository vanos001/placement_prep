# futex Internals

`futex` (Fast Userspace Mutex) is the Linux system call that powers every modern userspace synchronization primitive — `pthread_mutex_t`, `std::sync::Mutex` in Rust, `sync.Mutex` in Go, all of them. The design, introduced in kernel 2.5.7 by Ingo Molnar and Rusty Russell, is that the uncontended case is handled entirely in userspace with a single atomic operation, and the kernel is only entered when a thread must actually block. This page covers the system call interface, the kernel-side data structures, the wake-up protocol, and the subtle correctness issues that have produced multiple CVEs.

## The Core Idea

A `futex` is a 32-bit aligned word in userspace memory, plus a kernel-side wait queue indexed by the physical address of that word. The kernel does not own the word; userspace writes to it directly with atomic instructions. The kernel only gets involved when:

- A waiter wants to block: `futex(addr, FUTEX_WAIT, expected_val, timeout, NULL, 0)`. The kernel atomically verifies `*addr == expected_val`; if not, returns `EAGAIN`; if so, blocks the calling thread on the address.
- A waker wants to wake: `futex(addr, FUTEX_WAKE, max_count, NULL, NULL, 0)`. The kernel wakes up to `max_count` waiters blocked on the address.

The atomic verify-then-block is the heart of the design: it closes the race where a waker increments the futex word after the waiter reads it but before the waiter calls `FUTEX_WAIT`. Without this atomicity, the waiter could block forever waiting for a wake-up that already happened.

## The Classic Mutex Pattern

A `pthread_mutex_t` (Linux glibc's NPTL) using futex looks approximately like:

```c
// Lock path (uncontended fast path)
int expected = 0;  // unlocked
if (__atomic_compare_exchange_n(&mutex->state, &expected, 1,
                                /*weak=*/false,
                                __ATOMIC_ACQUIRE,
                                __ATOMIC_RELAXED))
    return;  // got the lock, no syscall

// Contended slow path
lock_slow(mutex);

void lock_slow(pthread_mutex_t *mutex) {
    int expected = 0;
    while (1) {
        if (__atomic_compare_exchange_n(&mutex->state, &expected, 1,
                                        false, ACQUIRE, RELAXED))
            return;
        // state is now 1 or 2 — try to mark contended
        if (expected == 1) {
            if (__atomic_compare_exchange_n(&mutex->state,
                                            &(int){1}, 2,
                                            false, ACQUIRE, RELAXED)) {
                // state is now 2 — block in the kernel
                futex(&mutex->state, FUTEX_WAIT, 2, NULL, NULL, 0);
                // woken up; loop and retry
                expected = 0;
                continue;
            }
        }
        // Try again
        expected = 0;
    }
}

// Unlock path
int prev = __atomic_fetch_sub(&mutex->state, 1, __ATOMIC_RELEASE);
if (prev != 1) {
    // There were waiters; wake one
    mutex->state = 0;
    futex(&mutex->state, FUTEX_WAKE, 1, NULL, NULL, 0);
}
```

The three-state protocol (0=free, 1=locked-no-waiters, 2=locked-with-waiters) is what makes this efficient: in the uncontended case (1→0), no futex syscall is needed. Only when the previous value was 2 (with waiters) does the kernel get a `FUTEX_WAKE` call.

## The Kernel-Side Data Structures

The kernel maintains a hash table of wait queues, `futex_queues` in `kernel/futex/core.c`:

```c
// Simplified
struct futex_hash_bucket {
    struct futex_q *head;  // doubly-linked list of waiters
    raw_spinlock_t lock;
};

static struct futex_hash_bucket *futex_queues;
#define futex_buckets_log 11  /* hash table size 2^11 = 2048 */
```

Each `futex_q` represents one blocked thread:

```c
struct futex_q {
    struct plist_node list;        // node in the bucket's priority list
    struct task_struct *task;       // the blocked thread
    spinlock_t *lock_ptr;          // pointer to bucket's lock
    union futex_key key;            // what the user passed
    u32 bitset;                     // for FUTEX_WAIT_BITSET
    struct rt_mutex *rt_waiter;     // for PI futex
    union {
        struct hlist_node task_list;
        struct rcu_head rcu;
    };
};
```

The hash key (`union futex_key`) is what disambiguates waiters on the same logical address across address spaces. It can be:

- `FUTEX_KEY_INODE` — the address is backed by a file; the key is `(inode, offset_within_page, ...)` and is shared across all processes mapping that file.
- `FUTEX_KEY_MM` — the address is anonymous (private) memory; the key is `(mm_struct, address, ...)` and is per-process.

The hash function combines the key parts to land in a bucket. Bucket contention is the principal scaling limit for futex workloads: a hash collision rate of 1% on a 2048-bucket table means 1% of waiters contend the same `raw_spinlock_t`, which serializes all wait/wake operations on those addresses.

## The Wake Protocol

`FUTEX_WAKE` walks the bucket's priority-sorted list of waiters and wakes up to `nr_wake` of them. The wake sequence:

1. Take `bucket->lock`.
2. Walk the list, collect the top `nr_wake` entries (priority order if `FUTEX_WAKE_OP_PRIVATE`, FIFO otherwise).
3. For each, set `task->__state = TASK_RUNNING`, remove from the bucket, and call `wake_up_q()` (deferred to avoid taking the runqueue lock N times).
4. Release `bucket->lock`.
5. Call `wake_up_q()` which then schedules each thread.

The deferred `wake_up_q` is a significant optimization: in a thundering-herd wake-up of 1000 threads on the same address, the runqueue lock would be taken 1000 times if each `try_to_wake_up` immediately entered the runqueue update. The `wake_up_q` batches them into one.

## Private vs Shared Futexes

`FUTEX_PRIVATE_FLAG` (kernel 2.6.31) tells the kernel the futex is process-local and can never be shared. This skips the inode lookup, taking a faster path through `get_user_pages_fast` and using a smaller per-mm hash table. Glibc sets this on `pthread_mutex_t` initialized with `PTHREAD_PROCESS_PRIVATE`.

For shared futexes (across `fork()`, `mmap(MAP_SHARED)`, or `shm_open()`), the kernel must locate the underlying `struct address_space` (file) or `struct anon_vma` (anonymous) and use that as the key, so the same logical address in two processes hash to the same bucket.

## `FUTEX_WAIT_BITSET` and the Bitset

`FUTEX_WAIT_BITSET`/`FUTEX_WAKE_BITSET` add a 32-bit mask to the wait/wake protocol. A waiter specifies the bits it's interested in; a waker specifies which bits to wake. Waiters with `(waiter_mask & wake_mask) == 0` are skipped.

This is the foundation of `pthread_barrier_t`, where each "phase" of waiters has a different bit, and the broadcaster wakes only the current phase.

## `FUTEX_REQUEUE` and the Thundering Herd

The classic thundering-herd problem in `pthread_cond_t`: a single `pthread_cond_signal` may wake many waiters, only one of which can make progress; the rest re-block. `FUTEX_REQUEUE` solves this by transferring waiters from one futex (the condvar's `seq` field) to another (the associated mutex's `state` field) without waking them. The waiters re-block on the mutex, no spurious wake.

```c
// Wake nr_wake waiters from addr1, then requeue nr_requeue of them on addr2
futex(addr1, FUTEX_REQUEUE, nr_wake, (struct timespec *)(long)nr_requeue,
      addr2, 0);
```

`FUTEX_CMP_REQUEUE` adds a `val3` argument that the kernel verifies matches `*addr1`. Without this, the kernel cannot distinguish "wake happened between read and requeue" from "wake will happen after requeue". The cmp variant is the only one safe to use in production.

## PI Futexes (`FUTEX_LOCK_PI`)

Priority-inheritance futexes solve the priority-inversion problem on real-time kernels. A high-priority thread blocking on a mutex held by a low-priority thread temporarily boosts the holder's priority so it can run and release the lock quickly. The mechanism:

- `FUTEX_LOCK_PI` blocks and looks up the current holder via the `TID` field in the futex word (userspace must keep this current).
- The kernel boosts the holder via `rt_mutex_setprio`.
- On unlock, `FUTEX_UNLOCK_PI` re-checks the TID, clears it, and wakes one waiter.

This requires the kernel and userspace to agree on the TID field's offset within the futex word. The layout is documented in `Documentation/locking/rt-mutex.rst`. PREEMPT_RT kernels require all kernel mutexes to be PI; non-RT kernels treat PI futexes as a niche feature.

## `FUTEX_WAIT_MULTIPLE` (kernel 5.16+)

`FUTEX_WAIT_MULTIPLE` allows waiting on up to 10 futex words atomically — any one wake returns the call. This is the Linux equivalent of Win32's `WaitForMultipleObjects`. Use cases include thread pools waiting on N condvars.

## The Modern Replacement: `futex2`

Kernel 5.16 introduced `futex2` (`sys_futex_wait`, `sys_futex_wake`, `sys_futex_requeue`) with a cleaner API:

- Multiple futex words of varying sizes (8/16/32/64-bit) in one call.
- A separate per-futex `futex_waitv()` syscall that takes an array.
- No `union futex_key` — uses the underlying `struct file` directly.

As of kernel 6.x, `futex2` is being progressively adopted by glibc and musl, but the original `futex` syscall remains the production path.

## Pitfalls

1. **Sharing futexes via `fork()` requires the child to `mmap(MAP_SHARED)` the same memory.** A `MAP_PRIVATE` copy has a different physical address; `fork()`-inherited waiters will see different keys.
2. **`FUTEX_WAIT` wakes spuriously.** The kernel may return `EINTR` for any reason (signal, timeout, false wake-up). Always re-check the condition in userspace and loop.
3. **`FUTEX_WAKE` returns the number of threads actually woken, which may be less than requested.** A waker that assumes all `nr_wake` were woken will leak state — for example, a condvar that thinks all waiters are gone when really some weren't.
4. **A futex word must be 4-byte aligned on every architecture.** The kernel uses `get_user` with a 32-bit op, which faults on misaligned addresses. ARM64 generates a `SIGBUS` for unaligned atomic operations in some configurations.
5. **The TID field in a PI futex word is a contract.** If userspace forgets to clear the TID before the holder exits, the next acquirer will see a stale TID and the kernel will refuse to boost a dead thread.
6. **`futex` syscall is not interruptible by `SA_RESTART`.** A signal during `FUTEX_WAIT` always returns `EINTR`; userspace must explicitly retry. This is a deliberate design choice (the kernel cannot re-verify the expected value without races).

## References

- [futex(2) manpage](https://man7.org/linux/man-pages/man2/futex.2.html)
- Hubertus Franke, Rusty Russell, "Fuss, Futexes and Furwocks: Fast Userlevel Locking in Linux" (OLS 2002) — the original paper
- [kernel.org: futex documentation](https://docs.kernel.org/locking/futex.html)
- Darren Hart, "A futex API overview" (LPC 2009)
- [LWN: "A futex overview and update" (2009)](https://lwn.net/Articles/360699/)
- André Almeida, "[futex2 design notes](https://www.collabora.com/news-and-blog/blog/2020/11/17/futex2-a-future-of-fast-user-level-locking-on-linux/)"
- Thomas Gleixner, "[futex: Cure inconsistencies and subtle races](https://lwn.net/Articles/767893/)" — CVE-2014-3153 writeup
