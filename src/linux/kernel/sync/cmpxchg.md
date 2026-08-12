# cmpxchg (Compare-and-Exchange)

`cmpxchg` is the fundamental atomic compare-and-exchange primitive in the Linux
kernel. It is the building block for lock-free data structures, atomic
read-modify-write operations, and per-CPU variables. The kernel provides
architecture-optimized implementations with explicit memory ordering semantics.

> **Header:** `include/linux/atomic.h`, `include/asm-generic/cmpxchg.h`  
> **Arch headers:** `arch/*/include/asm/cmpxchg.h`  
> **Compiler builtin:** `__sync_val_compare_and_swap()`, `__atomic_compare_exchange()`

---

## Concept

Compare-and-exchange is an atomic operation:

```
cmpxchg(ptr, old, new):
    if *ptr == old:
        *ptr = new
        return old     (success)
    else:
        return *ptr    (failure — *ptr was different)
```

The key property: **the load, comparison, and store happen atomically** with
respect to all other CPUs. No other thread can modify `*ptr` between the
comparison and the store.

---

## Kernel API

### Basic `cmpxchg`

```c
#include <linux/atomic.h>

/* Typed cmpxchg */
typeof(*ptr) cmpxchg(typeof(*ptr) *ptr, typeof(*ptr) old, typeof(*ptr) new);

/* Example */
int expected = 0;
int prev = cmpxchg(&my_var, expected, 1);
if (prev == expected) {
    /* Successfully changed my_var from 0 to 1 */
} else {
    /* my_var was not 0; prev holds the actual value */
}
```

### `cmpxchg_relaxed` / `cmpxchg_acquire` / `cmpxchg_release`

Variants with explicit memory ordering:

| Variant | Ordering | Use Case |
|---------|----------|----------|
| `cmpxchg` | Full barrier (`smp_mb()`) | General purpose; strongest ordering |
| `cmpxchg_relaxed` | No barrier | When ordering is handled separately |
| `cmpxchg_acquire` | Acquire barrier | Lock acquisition pattern |
| `cmpxchg_release` | Release barrier | Lock release pattern |

```c
/* Acquire semantics: subsequent reads/writes see the change */
int old = cmpxchg_acquire(&lock->state, FREE, LOCKED);

/* Release semantics: prior writes visible before this store */
cmpxchg_release(&lock->state, LOCKED, FREE);
```

### `try_cmpxchg`

Modern (Linux 6.1+) variant that returns success/failure via pointer:

```c
bool try_cmpxchg(typeof(*ptr) *ptr, typeof(*ptr) *oldp, typeof(*ptr) new);

/* Usage */
int expected = 0;
if (try_cmpxchg(&my_var, &expected, 1)) {
    /* Success: my_var was 0, now 1 */
} else {
    /* Failure: expected now contains the actual value */
    /* No need for a separate load */
}
```

This is preferred over `cmpxchg` on architectures where the comparison result
is available without an extra load (e.g., x86 sets ZF flag).

### `cmpxchg64` / `cmpxchg_local`

```c
/* 64-bit cmpxchg (needed on 32-bit architectures) */
u64 cmpxchg64(u64 *ptr, u64 old, u64 new);

/* Per-CPU only (no inter-CPU atomicity) — faster for per-CPU variables */
unsigned long cmpxchg_local(unsigned long *ptr, unsigned long old, unsigned long new);
```

### 128-bit cmpxchg (cmpxchg16b)

On x86_64, the kernel can use `CMPXCHG16B` for atomically updating 128-bit values (e.g., a pointer + version counter pair):

```c
/* Requires: -mcx16 compiler flag, CPUID.80000001H:CX16 */
typedef struct {
    u64 low;
    u64 high;
} u128;

u128 cmpxchg128(u128 *ptr, u128 old, u128 new);
```

**Use case**: The kernel uses `cmpxchg16b` for lock-free updates of pointer+sequence pairs in seqcount structures and RCU-protected data structures.

**Performance**: `CMPXCHG16B` is slower than `CMPXCHG` (~20 cycles vs ~10 cycles on Skylake) and requires the cache line to be exclusively held. On AMD Zen 5, `CMPXCHG16B` latency increased to ~30 cycles.

```c
/* Architecture check */
#ifdef CONFIG_X86_64
extern bool cpu_has_cx16;  /* Set by CPUID */

if (cpu_has_cx16) {
    /* Use cmpxchg16b for 128-bit CAS */
} else {
    /* Fall back to spinlock-based emulation */
}
#endif
```

---

## Atomic Operations Built on cmpxchg

The kernel implements compound atomic operations using `cmpxchg`:

```c
/* These are all built on cmpxchg internally: */
atomic_add_return(i, v);      /* atomic add, return result */
atomic_sub_return(i, v);      /* atomic subtract */
atomic_inc_return(v);         /* atomic increment */
atomic_dec_return(v);         /* atomic decrement */
atomic_fetch_add(i, v);       /* add, return old value */
atomic_fetch_or(i, v);        /* bitwise OR */
atomic_fetch_and(i, v);       /* bitwise AND */
atomic_fetch_xor(i, v);       /* bitwise XOR */

/* 64-bit variants */
atomic64_cmpxchg(v, old, new);
atomic64_try_cmpxchg(v, &old, new);
```

### How `atomic_add_return` Uses cmpxchg

```c
/* Simplified — actual implementation varies by arch */
static inline int atomic_add_return(int i, atomic_t *v)
{
    int old, new;
    do {
        old = atomic_read(v);
        new = old + i;
    } while (cmpxchg(&v->counter, old, new) != old);
    return new;
}
```

On architectures with native atomic add (x86 `lock xadd`), this is a single
instruction instead of a cmpxchg loop.

---

## Architecture Implementations

### x86 / x86_64

```c
/* arch/x86/include/asm/cmpxchg.h */

/* 32-bit cmpxchg */
#define cmpxchg(ptr, old, new)                         \
    __cmpxchg(ptr, old, new, sizeof(*(ptr)))

/* Inline assembly — x86 has native CMPXCHG instruction */
static inline unsigned long __cmpxchg(volatile void *ptr,
                                       unsigned long old,
                                       unsigned long new, int size)
{
    switch (size) {
    case 1:
        asm volatile("lock cmpxchgb %b1, %0"
                     : "+m" (*(u8 *)ptr), "=a" (old)
                     : "r" ((u8)new), "1" ((u8)old)
                     : "memory");
        break;
    case 2:
        asm volatile("lock cmpxchw %w1, %0"
                     : "+m" (*(u16 *)ptr), "=a" (old)
                     : "r" ((u16)new), "1" ((u16)old)
                     : "memory");
        break;
    case 4:
        asm volatile("lock cmpxchgl %k1, %0"
                     : "+m" (*(u32 *)ptr), "=a" (old)
                     : "r" ((u32)new), "1" ((u32)old)
                     : "memory");
        break;
#ifdef CONFIG_X86_64
    case 8:
        asm volatile("lock cmpxchgq %1, %0"
                     : "+m" (*(u64 *)ptr), "=a" (old)
                     : "r" ((u64)new), "1" ((u64)old)
                     : "memory");
        break;
#endif
    }
    return old;
}
```

**Key instruction:** `LOCK CMPXCHG` — atomic on SMP via cache-line locking.

On x86, `cmpxchg` includes a full memory barrier (`lock` prefix implies `mfence`
on modern CPUs).

### ARM64

```c
/* arch/arm64/include/asm/cmpxchg.h */

/* Uses LL/SC (Load-Linked / Store-Conditional) */
#define __CMPXCHG_CASE(w, sz, name, mb, cl)                         \
static inline unsigned long __cmpxchg_case_##name(                    \
        volatile void *ptr, unsigned long old, unsigned long new)    \
{                                                                     \
    unsigned long tmp, ret;                                           \
    asm volatile(                                                     \
        "   prfm    pstl1strm, %2\n"                                 \
        "1: ld" #mb "xr" #sz "\t%" #w "0, %2\n"                     \
        "   eor     %" #w "1, %" #w "0, %" #w "3\n"                 \
        "   cbnz    %" #w "1, 2f\n"                                  \
        "   st" #cl "xr" #sz "\t%w1, %" #w "4, %2\n"                \
        "   cbnz    %w1, 1b\n"                                       \
        "2:"                                                          \
        : "=&r" (ret), "=&r" (tmp), "+Q" (*(unsigned long *)ptr)     \
        : "r" (old), "r" (new)                                       \
        : cl);                                                        \
    return ret;                                                       \
}
```

**ARM64 instructions:** `LDXR` (load-exclusive) / `STXR` (store-conditional)
loop, with optional `LDAXR` / `STLR` for acquire/release semantics.

### RISC-V

```c
/* arch/riscv/include/asm/cmpxchg.h */

/* Uses LR/SC (Load-Reserved / Store-Conditional) */
#define __cmpxchg(ptr, old, new, size)                                  \
({                                                                       \
    __typeof__(*(ptr)) __ret;                                            \
    switch (size) {                                                      \
    case 4:                                                              \
        __ret = cmpxchg_val_32(ptr, old, new);                          \
        break;                                                           \
    }                                                                    \
    __ret;                                                               \
})

/* cmpxchg_val_32 uses lr.w / sc.w loop */
```

**RISC-V instructions:** `LR.W` / `SC.W` (32-bit), `LR.D` / `SC.D` (64-bit).

### PowerPC

```c
/* arch/powerpc/include/asm/cmpxchg.h */

/* Uses lwarx / stwcx. (LL/SC variant) */
#define __cmpxchg_u32(ptr, old, new)                                    \
({                                                                       \
    unsigned int *__ptr = (unsigned int *)(ptr);                         \
    unsigned int __old = (old);                                          \
    unsigned int __new = (new);                                          \
    unsigned int __prev;                                                 \
    __asm__ __volatile__(                                                \
        "1: lwarx   %0,0,%2\n"                                          \
        "   cmpw    0,%0,%3\n"                                           \
        "   bne-    2f\n"                                                \
        "   stwcx.  %4,0,%2\n"                                           \
        "   bne-    1b\n"                                                \
        "   isync\n"                                                     \
        "2:"                                                             \
        : "=&r" (__prev), "=m" (*__ptr)                                  \
        : "r" (__ptr), "r" (__old), "r" (__new), "m" (*__ptr)           \
        : "cc", "xer", "memory");                                        \
    __prev;                                                              \
})
```

---

## Memory Barriers and Ordering

cmpxchg interacts with the CPU memory model. The barriers ensure that:

1. **No reordering of cmpxchg with surrounding accesses** (full barrier variant).
2. **Acquire/release semantics** for lock-free algorithms.

### Full Barrier (default `cmpxchg`)

```
Store A ──┤                    ├── Load X
          ├── cmpxchg(old,new) ├──
Load B  ──┤                    ├── Store Y
```

Nothing moves across the cmpxchg in either direction.

### Acquire (`cmpxchg_acquire`)

```
                ├── cmpxchg_acquire(old,new) ├──
Load B  ──┤                    ├── Load X
Store A ──┤                    ├── Store Y
```

Loads and stores *after* the acquire cannot move *before* it.

### Release (`cmpxchg_release`)

```
Store A ──┤                    ├── Load X
Load B  ──┤                    ├── Store Y
          ├── cmpxchg_release(old,new) ├──
```

Loads and stores *before* the release cannot move *after* it.

### x86 vs ARM64 Barrier Cost

| Architecture | Full barrier cost | Acquire/Release cost |
|-------------|-------------------|---------------------|
| x86_64 | `lock` prefix (~20 cycles) | Same (x86 is strongly ordered) |
| ARM64 | `DMB ISH` (~50-100 cycles) | `LDAXR`/`STLR` (free or near-free) |

On ARM64, using `cmpxchg_acquire`/`cmpxchg_release` instead of `cmpxchg` can
be significantly faster.

---

## Common Usage Patterns

### Lock-Free Stack (Treiber Stack)

```c
struct node {
    struct node *next;
    int data;
};

struct stack {
    struct node *head;
};

void push(struct stack *s, struct node *n)
{
    struct node *old;
    do {
        old = READ_ONCE(s->head);
        n->next = old;
    } while (cmpxchg(&s->head, old, n) != old);
}

struct node *pop(struct stack *s)
{
    struct node *old, *next;
    do {
        old = READ_ONCE(s->head);
        if (!old)
            return NULL;
        next = old->next;
    } while (cmpxchg(&s->head, old, next) != old);
    return old;
}
```

**Performance characteristics**:
- **Uncontended**: Each push/pop is a single `cmpxchg` — ~10 cycles on x86
- **Contended**: CAS failures cause retries. With N threads, expect O(N) retries per operation
- **ABA vulnerability**: The pop operation is vulnerable to the ABA problem (see below)

### Lock-Free Queue (Michael-Scott Queue)

A more complex lock-free data structure: a FIFO queue with separate head and tail pointers:

```c
struct ms_queue {
    _Atomic(struct node *) head;
    _Atomic(struct node *) tail;
};

void enqueue(struct ms_queue *q, int value)
{
    struct node *new_node = alloc_node(value);
    struct node *old_tail, *next;

    new_node->next = NULL;
    while (true) {
        old_tail = atomic_load(&q->tail);
        next = atomic_load(&old_tail->next);
        if (old_tail == atomic_load(&q->tail)) {
            if (next == NULL) {
                /* Tail points to last node — try to append */
                if (atomic_compare_exchange_weak(&old_tail->next,
                                                  next, new_node))
                    break;  /* Success */
            } else {
                /* Tail is lagging — help advance it */
                atomic_compare_exchange_weak(&q->tail,
                                              old_tail, next);
            }
        }
    }
    /* Try to advance tail to new node */
    atomic_compare_exchange_weak(&q->tail, old_tail, new_node);
}
```

The key insight: **helping** — if a thread sees the tail is lagging, it helps advance it before retrying its own operation. This ensures progress even if a thread is preempted mid-operation.

### Version Counter / Sequence Lock Pattern

```c
struct seqcount {
    unsigned int sequence;
};

void write_begin(struct seqcount *sc)
{
    /* Odd = write in progress */
    sc->sequence++;
    smp_wmb();
}

void write_end(struct seqcount *sc)
{
    smp_wmb();
    sc->sequence++;  /* Even = stable */
}

unsigned int read_begin(struct seqcount *sc)
{
    unsigned int seq;
    seq = READ_ONCE(sc->sequence);
    smp_rmb();
    return seq;
}

bool read_retry(struct seqcount *sc, unsigned int start)
{
    smp_rmb();
    return READ_ONCE(sc->sequence) != start;
}
```

### Test-and-Set Bit

```c
/* Atomically test and set bit, return old value */
bool test_and_set_bit(long nr, volatile unsigned long *addr)
{
    /* Implemented via cmpxchg on most architectures */
    unsigned long mask = 1UL << (nr % BITS_PER_LONG);
    unsigned long old;
    do {
        old = *addr;
        if (old & mask)
            return true;  /* already set */
    } while (cmpxchg(addr, old, old | mask) != old);
    return false;
}
```

---

## cmpxchg vs Other Primitives

| Primitive | Use Case | Atomicity |
|-----------|----------|-----------|
| `cmpxchg` | Conditional update, CAS loops | Single atomic RMW |
| `atomic_add` | Simple increment/decrement | May use native instruction |
| `xchg` | Unconditional exchange | Single atomic RMW |
| `test_and_set_bit` | Bit manipulation | Via cmpxchg or native |
| `spin_lock` | Mutual exclusion | cmpxchg-based on ticket/spin locks |
| `rcu_assign_pointer` | RCU publish | Store + barrier |

---

## Common Pitfalls

### ABA Problem

The ABA problem is the most subtle bug in lock-free programming:

```
Thread 1: reads ptr → A, reads A.next → B
Thread 1: gets preempted
Thread 2: pops A, pops B, pushes C, pushes A (A.next now points to C)
Thread 1: resumes, cmpxchg(ptr, A, B) succeeds!
Thread 1: now has a stale view — A.next was B but is now C
```

**Solutions:**

1. **Tagged pointers** (most common in kernel): Add a version counter to the pointer
```c
/* Use the upper 16 bits of a 64-bit pointer as a version tag */
uint64_t tagged = ((uint64_t)version << 48) | (uint64_t)ptr;
cmpxchg((uint64_t *)&head, old_tagged, new_tagged);
```

2. **RCU**: The grace period ensures old nodes aren't reused while readers exist

3. **Hazard pointers**: Explicitly protect nodes before accessing them

### Spurious Failures

cmpxchg can fail spuriously on LL/SC architectures (ARM64, RISC-V) if the
cache line is evicted between the load-exclusive and store-conditional. This is
*correct behavior* — CAS loops always retry. Never assume cmpxchg succeeds
based on the value being correct:

```c
/* BAD: assuming success */
if (expected_value == old)
    *ptr = new;  /* NOT atomic! */

/* GOOD: always use cmpxchg */
old = cmpxchg(ptr, expected_value, new);
```

### Size Mismatch

```c
/* WRONG: cmpxchg on a u8 using u32 pointer */
u8 val = 0;
cmpxchg((u32 *)&val, 0, 1);  /* undefined behavior — may corrupt adjacent memory */

/* RIGHT: use properly typed pointer */
cmpxchg(&val, (u8)0, (u8)1);
```

### Missing Retry Loop

```c
/* BAD: single cmpxchg attempt — fails silently if contended */
old = cmpxchg(&shared, expected, new);
if (old != expected) {
    /* Give up — data may be inconsistent */
}

/* GOOD: retry loop */
do {
    old = READ_ONCE(shared);
    new = compute_new(old);
} while (cmpxchg(&shared, old, new) != old);
```

### cmpxchg on Floating-Point

```c
/* WRONG: cmpxchg does not work on floating-point types */
float val = 1.0f;
cmpxchg(&val, 1.0f, 2.0f);  /* Compile error or undefined behavior */

/* RIGHT: use integer representation */
int32_t ival;
memcpy(&ival, &val, sizeof(ival));
/* Use cmpxchg on ival */
```

## Performance Analysis

### cmpxchg Latency by Architecture

| Architecture | Uncontended | 2-thread contention | 8-thread contention |
|-------------|-------------|--------------------|--------------------|
| x86_64 (Skylake) | ~10 cycles | ~40 cycles | ~200 cycles |
| x86_64 (Zen 3) | ~8 cycles | ~35 cycles | ~180 cycles |
| ARM64 (Neoverse N1) | ~12 cycles | ~50 cycles | ~300 cycles |
| RISC-V (SiFive U74) | ~20 cycles | ~80 cycles | ~400 cycles |

**Key insight**: Contention cost grows super-linearly because each failed cmpxchg causes a cache-line transfer between CPUs (~40-80ns each).

### When to Use cmpxchg vs Alternatives

```mermaid
graph TD
    A[Need atomic RMW?] --> B{Simple increment/decrement?}
    B -->|Yes| C[Use atomic_add/atomic_inc
(native instruction on x86)]
    B -->|No| D{Conditional update?}
    D -->|Yes| E{Single variable?}
    E -->|Yes| F[Use cmpxchg]
    E -->|No| G{Need 128-bit CAS?}
    G -->|Yes| H[Use cmpxchg16b if available]
    G -->|No| I[Use spinlock or RCU]
    D -->|No| J[Use xchg for unconditional swap]
```

### cmpxchg vs atomic_add_return

On x86, `atomic_add_return()` uses `LOCK XADD` (a single instruction) rather than a cmpxchg loop. On ARM64, it uses an `LDXR`/`STXR` loop:

| Operation | x86 implementation | ARM64 implementation |
|-----------|-------------------|---------------------|
| `atomic_add_return()` | `LOCK XADD` | `LDXR`/`ADD`/`STXR` loop |
| `atomic_cmpxchg()` | `LOCK CMPXCHG` | `LDXR`/`CMP`/`STXR` loop |
| `atomic_xchg()` | `LOCK XCHG` | `LDXR`/`MOV`/`STXR` loop |

---

## Relation to Other Kernel Subsystems

- **cmpxchg** is the foundation for `atomic_*` operations.
- **spinlock** (ticket/MCS/qspinlock) uses cmpxchg for lock acquisition.
- **RCU** uses cmpxchg for lock-free pointer updates.
- **Per-CPU variables** use `cmpxchg_local` for fast per-CPU operations.
- **Lock-free lists** (e.g., `llist`) are built on cmpxchg.

---

## Further Reading

- [Kernel docs: Atomic Operations](https://www.kernel.org/doc/html/latest/core-api/atomic_ops.html)
- [Kernel docs: Memory Barriers](https://www.kernel.org/doc/html/latest/core-api/wrappers/memory-barriers.html)
- [LWN: Lock-free algorithms](https://lwn.net/Articles/262464/)
- [Intel SDM Vol. 2: CMPXCHG instruction](https://www.intel.com/sdm)
- [ARM Architecture Reference Manual: LDXR/STXR]
- [Hans Boehm: Can Seqlocks Get Along With Programming Language Memory Models?](https://www.hpl.hp.com/techreports/2012/HPL-2012-68.html)
- See also: [Spinlocks](/kernel/sync/spinlock), [Memory Barriers](/kernel/sync/barriers), [RCU](/kernel/sync/rcu), [Atomic Operations](/kernel/sync/atomic)
