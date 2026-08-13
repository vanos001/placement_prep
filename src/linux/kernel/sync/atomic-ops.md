# Atomic Operations

## Introduction

Atomic operations are the most fundamental building blocks for lock-free synchronization in the Linux kernel. They guarantee that an operation on a single variable completes indivisibly — no other CPU can observe the variable in an intermediate state. When combined with memory barriers, atomic operations enable the construction of complex lock-free data structures and algorithms.

The Linux kernel provides atomic operations for integers (`atomic_t`, `atomic64_t`), bit operations (`set_bit`, `clear_bit`, `test_and_set_bit`), and the powerful compare-and-swap primitive (`cmpxchg`). Understanding these primitives and their memory ordering guarantees is essential for writing correct concurrent kernel code.

## atomic_t: Atomic Integers

`atomic_t` is a 32-bit atomic integer type. It wraps an `int` in a structure to prevent direct (non-atomic) access:

```c
typedef struct {
    int counter;
} atomic_t;
```

### Initialization

```c
/* Static */
ATOMIC_INIT(0);

/* Dynamic */
atomic_t v;
atomic_set(&v, 0);

/* Read (not atomic on all architectures) */
int val = atomic_read(&v);
```

### Arithmetic Operations

```c
atomic_t v = ATOMIC_INIT(0);

atomic_add(5, &v);           /* v += 5 */
atomic_sub(3, &v);           /* v -= 3 */
atomic_inc(&v);              /* v++ */
atomic_dec(&v);              /* v-- */

/* Return the new value */
int new = atomic_add_return(5, &v);  /* v += 5; return v; */
int new = atomic_sub_return(3, &v);  /* v -= 3; return v; */
int new = atomic_inc_return(&v);     /* v++; return v; */
int new = atomic_dec_return(&v);     /* v--; return v; */

/* Return the old value */
int old = atomic_add_return_relaxed(5, &v);  /* Relaxed ordering */

/* Conditional decrement — decrement only if non-zero */
int was_zero = atomic_dec_and_test(&v);  /* v--; return v==0; */
int was_positive = atomic_sub_and_test(5, &v);  /* v -= 5; return v==0; */

/* Add and test */
int is_zero = atomic_add_negative(-1, &v);  /* v -= 1; return v < 0; */
```

### Compare-and-Swap

```c
/* If *v == old, set *v = new. Returns the old value. */
int old = atomic_cmpxchg(&v, old, new);

/* If *v == old, set *v = new (relaxed ordering) */
int old = atomic_cmpxchg_relaxed(&v, old, new);

/* Atomic exchange — set *v = new, return old */
int old = atomic_xchg(&v, new);
```

### Atomic Bit Operations on Integers

```c
atomic_t flags = ATOMIC_INIT(0);

atomic_or(FLAG_A, &flags);       /* flags |= FLAG_A */
atomic_and(~FLAG_A, &flags);     /* flags &= ~FLAG_A */
atomic_xor(FLAG_A, &flags);      /* flags ^= FLAG_A */

/* Atomic fetch-and-modify */
int old = atomic_fetch_or(FLAG_A, &flags);
int old = atomic_fetch_and(~FLAG_A, &flags);
int old = atomic_fetch_xor(FLAG_A, &flags);
```

## atomic64_t: 64-bit Atomic Integers

For 64-bit atomic operations, use `atomic64_t`:

```c
atomic64_t v;
atomic64_set(&v, 0);
atomic64_add(1, &v);
atomic64_inc(&v);
s64 val = atomic64_read(&v);
s64 old = atomic64_cmpxchg(&v, expected, desired);
s64 old = atomic64_xchg(&v, new);
```

On 64-bit architectures, `atomic64_t` operations are native. On 32-bit architectures, they may use spinlock-based emulation (slower).

### atomic64_t on 32-bit Architectures

On 32-bit systems, 64-bit atomic operations cannot be performed with a single instruction. The kernel provides two strategies:

1. **Spinlock emulation** (`CONFIG_GENERIC_ATOMIC64`): Uses a hash table of spinlocks keyed by the address of the `atomic64_t`. This is correct but slow — each operation requires lock acquisition.

2. **Native LL/SC** (ARM with `LDRD`/`STRD`): Some 32-bit ARM processors support 64-bit load/store-exclusive pairs, enabling native 64-bit atomics.

```c
/* 32-bit x86: cmpxchg8b for 64-bit CAS */
asm volatile("lock cmpxchg8b %0"
             : "=m" (*ptr), "=A" (old)
             : "m" (*ptr), "b" ((u32)new), "c" ((u32)(new >> 32)), "0" (old)
             : "memory");
```

### Performance: atomic_t vs atomic64_t

| Architecture | `atomic_inc` | `atomic64_inc` | Ratio |
|-------------|-------------|----------------|-------|
| x86_64 | ~5ns | ~5ns | 1x (both native) |
| x86_32 | ~5ns | ~50ns | 10x (emulated) |
| ARM64 | ~10ns | ~10ns | 1x (both native) |
| ARM32 (no LDRD) | ~10ns | ~80ns | 8x (emulated) |

On 32-bit systems, prefer `atomic_t` over `atomic64_t` when 32 bits suffice.

## Bit Operations

### Atomic Bit Manipulation

```c
unsigned long flags = 0;

/* Set bit nr */
set_bit(nr, &flags);

/* Clear bit nr */
clear_bit(nr, &flags);

/* Change (toggle) bit nr */
change_bit(nr, &flags);

/* Test bit nr */
int bit = test_bit(nr, &flags);

/* Test and set — returns previous value */
int was_set = test_and_set_bit(nr, &flags);

/* Test and clear */
int was_set = test_and_clear_bit(nr, &flags);

/* Test and change (toggle) */
int was_set = test_and_change_bit(nr, &flags);
```

**Important**: `set_bit()`, `clear_bit()`, etc. are truly atomic — they use locked instructions on x86 (e.g., `LOCK BTS`, `LOCK BTR`). Plain bit assignments (`flags |= (1 << nr)`) are NOT atomic.

### Non-atomic Bit Operations

For per-CPU data or data protected by locks:

```c
__set_bit(nr, &flags);
__clear_bit(nr, &flags);
__change_bit(nr, &flags);
__test_and_set_bit(nr, &flags);
__test_and_clear_bit(nr, &flags);
```

These are faster but not safe for concurrent access from multiple CPUs.

## compare-and-swap (cmpxchg)

The `cmpxchg` family is the most powerful atomic primitive — it enables lock-free algorithms by allowing conditional atomic updates:

```c
/* 32-bit cmpxchg */
typeof(*ptr) old = cmpxchg(ptr, old_val, new_val);
/* Returns: old value
 * If old == old_val, then *ptr = new_val (success)
 * If old != old_val, *ptr is unchanged (failure) */

/* 64-bit cmpxchg */
typeof(*ptr) old = cmpxchg64(ptr, old_val, new_val);

/* 128-bit cmpxchg (where supported) */
typeof(*ptr) old = cmpxchg128(ptr, old_val, new_val);
```

### Architecture Implementation Details

On x86, `cmpxchg` compiles to a single `LOCK CMPXCHG` instruction. On ARM64, it compiles to an `LDXR`/`STXR` loop. The kernel's `cmpxchg()` macro selects the correct implementation based on the pointer type size:

```c
/* x86: size-dependent instruction selection */
case 1: asm volatile("lock cmpxchgb %b1, %0" ...);  /* LOCK CMPXCHGB */
case 2: asm volatile("lock cmpxchw %w1, %0" ...);   /* LOCK CMPXCHGW */
case 4: asm volatile("lock cmpxchgl %k1, %0" ...);  /* LOCK CMPXCHGL */
case 8: asm volatile("lock cmpxchgq %1, %0" ...);   /* LOCK CMPXCHGQ */
```

### CAS Loop Pattern

The standard pattern for using cmpxchg is a retry loop:

```c
/* Atomically increment a shared counter using CAS */
void atomic_cas_increment(atomic_long_t *counter)
{
    long old, new;
    
    do {
        old = atomic_long_read(counter);
        new = old + 1;
    } while (atomic_long_cmpxchg(counter, old, new) != old);
    /* Loop if cmpxchg failed (another CPU changed the value) */
}
```

**CAS loop performance**: Each failed iteration costs a full round-trip to the cache line owner. Under high contention, CAS loops can degrade badly. The kernel mitigates this with:
- **Exponential backoff** (in some algorithms)
- **Per-CPU data** to avoid contention entirely
- **Ticket/queue-based locks** (e.g., qspinlock) instead of CAS-based spinlocks

### Lock-Free Linked List Insertion

```c
/* Lock-free insertion at head using cmpxchg */
void lockfree_push(struct lockfree_stack *stack, struct node *node)
{
    struct node *old_head;
    
    do {
        old_head = READ_ONCE(stack->head);
        node->next = old_head;
    } while (cmpxchg(&stack->head, old_head, node) != old_head);
}
```

## Memory Barriers

Atomic operations have different memory ordering guarantees. The Linux kernel provides several ordering levels:

### Ordering Levels

| Level | Suffix | Guarantee |
|-------|--------|-----------|
| Sequential Consistency | (none) | Full ordering: all prior ops visible before this op, all subsequent ops visible after |
| Acquire | `_acquire` | Subsequent loads/stores see effects of this operation |
| Release | `_release` | Prior loads/stores are visible when this operation is observed |
| Relaxed | `_relaxed` | Only atomicity guaranteed, no ordering |

```c
/* Sequential consistency (strongest, default) */
atomic_set(&v, 1);
int val = atomic_read(&v);
atomic_cmpxchg(&v, old, new);

/* Acquire ordering */
int val = atomic_read_acquire(&v);
int old = atomic_cmpxchg_acquire(&v, old, new);

/* Release ordering */
atomic_set_release(&v, 1);
int old = atomic_cmpxchg_release(&v, old, new);

/* Relaxed ordering (weakest) */
int val = atomic_read_relaxed(&v);
int old = atomic_cmpxchg_relaxed(&v, old, new);
```

### Explicit Memory Barriers

```c
/* Full barrier — all prior loads and stores complete before any subsequent */
smp_mb();

/* Write barrier — all prior stores complete before any subsequent stores */
smp_wmb();

/* Read barrier — all prior loads complete before any subsequent loads */
smp_rmb();

/* Data dependency barrier — ensures dependent loads are ordered */
smp_read_barrier_depends();

/* Compiler barrier — prevents compiler reordering only */
barrier();

/* Before/after I/O */
mb();
wmb();
rmb();
```

### x86 vs ARM Memory Ordering

x86 is **strongly ordered** — loads are not reordered with loads, stores are not reordered with stores, and loads are not reordered with older stores. On x86:
- `smp_mb()` = `lock; addl $0,0(%rsp)` (full barrier, ~20 cycles)
- `smp_wmb()` = `barrier()` (compiler only, ~0 cycles)
- `smp_rmb()` = `barrier()` (compiler only, ~0 cycles)

ARM is **weakly ordered** — all reorderings are possible. On ARM:
- `smp_mb()` = `dmb ish` (data memory barrier, ~50-100 cycles)
- `smp_wmb()` = `dmb ishst` (store barrier, ~30-50 cycles)
- `smp_rmb()` = `dmb ishld` (load barrier, ~30-50 cycles)

RISC-V is also **weakly ordered**:
- `smp_mb()` = `fence rw,rw` (~20-40 cycles)
- `smp_wmb()` = `fence w,w` (~10-20 cycles)
- `smp_rmb()` = `fence r,r` (~10-20 cycles)

**Practical implication**: Code that works correctly on x86 without explicit barriers may fail on ARM/RISC-V. Always use the `_acquire`/`_release` variants or explicit barriers for portable code.

### Barrier Cost Comparison

| Barrier | x86_64 | ARM64 | RISC-V |
|---------|--------|-------|--------|
| `smp_mb()` | ~20 cycles | ~50-100 cycles | ~20-40 cycles |
| `smp_wmb()` | ~0 (compiler) | ~30-50 cycles | ~10-20 cycles |
| `smp_rmb()` | ~0 (compiler) | ~30-50 cycles | ~10-20 cycles |
| `smp_store_release()` | ~0 (compiler) | ~0 (STLR) | ~0 (fence+store) |
| `smp_load_acquire()` | ~0 (compiler) | ~0 (LDAR) | ~0 (fence+load) |

The `_acquire`/`_release` variants are often cheaper than explicit barriers because they can be fused with the load/store instruction on ARM64.

### Control and Data Dependencies

```c
/* Control dependency: if (cond) then store */
if (condition)
    WRITE_ONCE(data, value);  /* CPU guarantees: the store happens after the branch */

/* Data dependency: store depends on prior load */
p = READ_ONCE(pointer);
p->field = value;  /* CPU guarantees: the store to p->field happens after reading p */

/* WRITE_ONCE and READ_ONCE prevent compiler optimizations */
```

## The STORE_ONCE and LOAD_ONCE Pattern

The kernel provides `WRITE_ONCE()` and `READ_ONCE()` to prevent the compiler from doing surprising things:

```c
/* Prevent compiler from optimizing away, merging, or tearing the access */
WRITE_ONCE(shared_var, value);
int val = READ_ONCE(shared_var);
```

Without `WRITE_ONCE()` / `READ_ONCE()`, the compiler might:
- Split a 64-bit store into two 32-bit stores (torn read)
- Cache the value in a register and never re-read from memory
- Merge adjacent writes into a single write
- Reorder the access relative to other operations

## Atomic Operations and Lock-Free Algorithms

### Per-CPU Counter Pattern

```c
DEFINE_PER_CPU(long, my_counter);

void increment_counter(void)
{
    preempt_disable();
    this_cpu_inc(my_counter);
    preempt_enable();
}

long read_counter(void)
{
    long sum = 0;
    int cpu;

    for_each_possible_cpu(cpu)
        sum += per_cpu(my_counter, cpu);

    return sum;
}
```

### Atomic Flags Pattern

```c
#define FLAG_ACTIVE    0
#define FLAG_DIRTY     1
#define FLAG_LOCKED    2

unsigned long flags = 0;

/* Set active flag, return previous value */
if (!test_and_set_bit(FLAG_ACTIVE, &flags)) {
    /* We were the first to set it */
    do_activation();
}

/* Clear dirty flag atomically */
test_and_clear_bit(FLAG_DIRTY, &flags);
```

### Wait-Free Read Pattern

```c
/* Single writer, multiple readers — no locks needed */
static int __read_mostly sysctl_value = 42;

/* Writer (under mutex) */
mutex_lock(&writer_mutex);
WRITE_ONCE(sysctl_value, new_value);
mutex_unlock(&writer_mutex);

/* Reader (any context, no locking) */
int val = READ_ONCE(sysctl_value);
```

## Common Pitfalls

### Non-Atomic RMW on Shared Data

```c
/* BAD: Not atomic! */
shared_var++;

/* GOOD: Atomic */
atomic_inc(&shared_atomic_var);
```

On x86, `shared_var++` compiles to `mov`, `add`, `mov` — three separate instructions. Another CPU can interleave between any of them. Even if the variable is aligned and fits in a cache line, the read-modify-write is not atomic without a `LOCK` prefix.

### Torn Reads/Writes

```c
/* BAD: 64-bit write may be torn on 32-bit arch */
shared_64bit_var = value;

/* GOOD: Use atomic64_t or WRITE_ONCE */
atomic64_set(&shared_64bit_var, value);
WRITE_ONCE(shared_64bit_var, value);  /* 64-bit arch only */
```

A **torn read** occurs when a 64-bit value is read as two separate 32-bit loads. If another CPU writes the value between the two loads, the reader sees a mix of old and new bits. This is particularly dangerous for pointers on 32-bit systems.

### Missing Memory Barriers

```c
/* BAD: On weakly-ordered archs, writer may reorder */
data = 42;
ready = 1;

/* GOOD: Explicit barrier */
data = 42;
smp_wmb();       /* Or use smp_store_release */
ready = 1;

/* Reader */
while (!READ_ONCE(ready))
    cpu_relax();
smp_rmb();       /* Or use smp_load_acquire */
printk("%d\n", data);  /* Now guaranteed to see 42 */
```

The `smp_wmb()` ensures the store to `data` is visible to other CPUs before the store to `ready`. Without it, the CPU or compiler may reorder the stores, and the reader may see `ready == 1` but `data == 0`.

### Using Plain Variables with Concurrent Access

```c
/* BAD: Compiler may optimize, tear, or cache */
if (shared_flag) {
    do_something();
}

/* GOOD: Use READ_ONCE to ensure a fresh read */
if (READ_ONCE(shared_flag)) {
    do_something();
}
```

Without `READ_ONCE()`, the compiler may:
- Cache the value in a register and never re-read from memory
- Elide the read entirely if it determines the value hasn't changed
- Split a 64-bit read into two 32-bit reads (torn read)

### Atomic Operations on Volatile

```c
/* BAD: volatile does NOT make operations atomic */
volatile int counter;
counter++;  /* Still not atomic! volatile only prevents compiler caching */

/* GOOD: Use atomic_t */
atomic_t counter = ATOMIC_INIT(0);
atomic_inc(&counter);  /* Truly atomic */
```

`volatile` only prevents the compiler from caching or eliding accesses. It does NOT prevent:
- CPU reordering of memory operations
- Torn reads/writes on multi-word values
- Hardware-level race conditions between CPUs

### Double-Fetch in User-Space Copy

```c
/* BAD: TOCTOU with user-space pointer */
if (get_user(addr, &user_ptr) == 0) {
    /* Another thread might change user_ptr here! */
    if (get_user(val, (int __user *)addr) == 0) {  /* Double fetch */
        process(val);
    }
}

/* GOOD: Fetch once, use local copy */
if (get_user(addr, &user_ptr) == 0) {
    int val;
    if (get_user(val, (int __user *)addr) == 0) {
        process(val);
    }
}
```

## Debugging Atomic Operations

### KCSAN (Kernel Concurrency Sanitizer)

```
CONFIG_KCSAN=y
```

KCSAN detects data races by monitoring concurrent accesses to the same memory location:

```
BUG: KCSAN: data-race in my_reader / my_writer

read to 0xffff888012345678 of size 4 by task 1234 on CPU 0:
 my_reader+0x23/0x45

write to 0xffff888012345678 of size 4 by task 5678 on CPU 1:
 my_writer+0x45/0x67
```

KCSAN works by:
1. Randomly selecting accesses to watch
2. Setting up a watchpoint on the accessed memory location
3. Checking if another CPU accesses the same location concurrently
4. Reporting a data race if both accesses are non-atomic and at least one is a write

### CONFIG_DEBUG_ATOMIC_SLEEP

Warns when sleeping in atomic context (e.g., while holding a spinlock or inside `rcu_read_lock()`):

```
BUG: sleeping function called from invalid context at mm/slab.h:421
in_atomic(): 1, irqs_disabled(): 0, non_block: 0, pid: 1234, name: my_thread
CPU: 2 PID: 1234 Comm: my_thread Not tainted 6.x.x
Call Trace:
 dump_stack+0x.../0x...
 ___might_sleep+0x.../0x...
 __kmalloc+0x.../0x...
 my_function+0x.../0x...  /* Called while holding spinlock */
```

### Lockdep for Atomic Context

Lockdep tracks which locks are held and warns about invalid operations:

```
===============================================
WARNING: possible irq lock inversion dependency detected
6.x.x #1 Not tainted
----------------------------------------
fio/1234 just changed the state of lock:
 &rq->lock {+.+.}-{2:2}, at: scheduler_tick+0x.../0x...
but this lock was taken by another, HARDIRQ-safe lock in the past:
 &rq->lock {+.+.}-{2:2}
```

### Memory Ordering Verification with LKMM

The **Linux Kernel Memory Model** (LKMM) is a formal model that can verify memory ordering in kernel code using the `herd7` tool:

```bash
# Install herd7 (from github.com/herd/herdtools7)
# Then verify a litmus test:
cat > mp-wmb-rmb.litmus << 'EOF'
C mp-wmb-rmb

{
}

P0(int *x, int *y)
{
    WRITE_ONCE(*x, 1);
    smp_wmb();
    WRITE_ONCE(*y, 1);
}

P1(int *x, int *y)
{
    int r0;
    int r1;
    r0 = READ_ONCE(*y);
    smp_rmb();
    r1 = READ_ONCE(*x);
}

exists (1:r0=1 /\ 1:r1=0)
EOF

herd7 -conf linux-kernel.cfg mp-wmb-rmb.litmus
# Expected: No (the exists condition is never satisfied)
```

The LKMM can prove that specific patterns are correct or find counterexamples where reordering could cause bugs.

## Atomic Instruction Latency

The following table shows measured latency for common atomic instructions on modern hardware:

| Instruction | x86_64 (Skylake) | x86_64 (Zen 4) | ARM64 (Neoverse N1) |
|------------|-----------------|-----------------|---------------------|
| `LOCK XADD` (uncontended) | ~8 cycles | ~7 cycles | ~12 cycles (LDXR/STXR) |
| `LOCK CMPXCHG` (uncontended) | ~10 cycles | ~8 cycles | ~12 cycles (LDXR/STXR) |
| `LOCK CMPXCHG` (contended) | ~40-200 cycles | ~35-180 cycles | ~50-300 cycles |
| `LOCK BTS` (test-and-set bit) | ~8 cycles | ~7 cycles | ~12 cycles |
| `MFENCE` | ~20 cycles | ~15 cycles | ~50 cycles (DMB ISH) |

Contended latency depends heavily on the number of CPUs competing for the same cache line. With 64 CPUs, a contended `LOCK CMPXCHG` can take over 1000 cycles due to cache-line bouncing.

## Summary Table

| Operation | Type | Atomic? | Returns |
|-----------|------|---------|---------|
| `atomic_add()` | RMW | Yes | void |
| `atomic_add_return()` | RMW | Yes | new value |
| `atomic_cmpxchg()` | CAS | Yes | old value |
| `atomic_xchg()` | Exchange | Yes | old value |
| `set_bit()` | RMW | Yes | void |
| `test_and_set_bit()` | RMW | Yes | old bit |
| `cmpxchg()` | CAS | Yes | old value |
| `smp_mb()` | Barrier | N/A | N/A |
| `smp_wmb()` | Barrier | N/A | N/A |
| `smp_rmb()` | Barrier | N/A | N/A |
| `READ_ONCE()` | Load | N/A | value |
| `WRITE_ONCE()` | Store | N/A | N/A |

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Linux Kernel Documentation: Atomic Types](https://www.kernel.org/doc/html/latest/core-api/atomic_ops.html)
- [Linux Kernel Documentation: Memory Barriers](https://www.kernel.org/doc/html/latest/core-api/wrappers/memory-barriers.html)
- [Linux Kernel Source: Documentation/memory-barriers.txt](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/memory-barriers.txt)
- [Paul E. McKenney: "Memory Barriers: a Hardware View for Software Hackers"](https://www2.rdrop.com/users/paulmck/scalability/paper/whymb.2010.07.23a.pdf)
- [LWN: "A formal kernel memory-ordering model"](https://lwn.net/Articles/718628/)
- [LWN: "Who's afraid of a big bad optimizing compiler?"](https://lwn.net/Articles/793253/)

## Related Topics

- [Synchronization Overview](overview.md) — When and why synchronization is needed
- [Spinlocks](spinlocks.md) — Lock-based synchronization
- [RCU](rcu.md) — Uses atomic operations and memory barriers
- [Seqlocks](seqlocks.md) — Uses atomic sequence counters
- [Lockdep](lockdep.md) — Debugging synchronization issues
