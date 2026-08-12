# Memory Models

## Introduction

A **memory model** defines the ordering guarantees that a processor provides for memory operations (loads and stores). Understanding memory models is critical for writing correct concurrent code in the Linux kernel, because different architectures provide different ordering guarantees, and the kernel must work correctly on all of them.

The two extremes are **Total Store Ordering (TSO)**, where memory operations appear in a mostly programmatic order (x86), and **relaxed ordering**, where the hardware can aggressively reorder memory operations (ARM, RISC-V, PowerPC). The Linux kernel provides **memory barriers** that abstract over these differences.

## Why Memory Models Matter

### The Problem

```c
/* Classic concurrency problem: message passing */
/* CPU 0 writes data, then signals CPU 1 */

/* CPU 0 */                 /* CPU 1 */
data = 42;                  while (!flag) ;
flag = 1;                   print(data);

/* Question: Can CPU 1 print 0 instead of 42?
 * Answer: It depends on the memory model!
 */
```

### Memory Reordering

```
Types of Memory Reordering
──────────────────────────
1. Compiler reordering
   The compiler can reorder instructions during optimization
   Fixed by: compiler barriers, volatile, READ_ONCE/WRITE_ONCE

2. Store buffering (store-store reordering)
   CPU has a store buffer; stores become visible to other CPUs
   before they reach the cache/memory system
   Example: x86 allows store-buffer forwarding

3. Load reordering (load-load reordering)
   Loads can be reordered relative to each other
   Example: ARM/PowerPC allow load-load reordering

4. Store-load reordering
   A store followed by a load can appear reordered
   Example: x86 allows this (store buffer drains asynchronously)

5. Invalidate queue reordering
   On cache-coherent systems, invalidation acknowledgments
   can be delayed, causing stale reads
```

## x86: Total Store Ordering (TSO)

### x86 Memory Ordering Rules

```
x86 TSO Guarantees
───────────────────
✓ Loads are NOT reordered with other loads (load-load ordered)
✓ Stores are NOT reordered with other stores (store-store ordered)
✓ Loads are NOT reordered with older stores to the same address
✗ Stores ARE reordered with subsequent loads (store-load reordering
  CAN occur — the store buffer allows this)
✗ Loads can be reordered with older stores to DIFFERENT addresses

In practice: x86 is "strongly ordered"
  Most code works without explicit memory barriers
  Only store-load ordering requires barriers (MFENCE, LOCK prefix)
```

```c
/* x86 store-load reordering example */

/* Initially: x = 0, y = 0 */

/* CPU 0 */                 /* CPU 1 */
WRITE_ONCE(x, 1);          WRITE_ONCE(y, 1);
r0 = READ_ONCE(y);         r1 = READ_ONCE(x);

/* Can both r0 and r1 be 0?
 * On x86: YES! (store-load reordering)
 * On sequential consistency: NO
 */
```

### x86 Fence Instructions

```nasm
; x86 memory fence instructions

MFENCE          ; Full memory barrier (store-load ordered)
                ; All loads and stores before MFENCE are globally
                ; visible before any load/store after MFENCE

SFENCE          ; Store fence (store-store ordered)
                ; All stores before SFENCE are globally visible
                ; before any store after SFENCE

LFENCE          ; Load fence (load-load ordered on newer CPUs)
                ; Also serializing (waits for all prior instructions)

LOCK prefix     ; On specific instructions (XCHG, LOCK CMPXCHG, etc.)
                ; Acts as a full memory barrier
                ; Also provides atomicity

XCHG reg, mem   ; Implicit LOCK prefix (always)
                ; Full memory barrier
```

## ARM: Relaxed Memory Model

### ARM Memory Ordering Rules

```
ARM/AArch64 Memory Ordering (Weakly Ordered)
─────────────────────────────────────────────
✗ Loads CAN be reordered with other loads
✗ Stores CAN be reordered with other stores
✗ Loads CAN be reordered with older stores
✗ Independent loads from the same address CAN be reordered
  (in rare cases with dependency-breaking optimizations)

Required: Explicit barriers for ordering
  DMB (Data Memory Barrier) — general ordering
  DSB (Data Synchronization Barrier) — stronger
  ISB (Instruction Synchronization Barrier) — instruction stream
  LDAR/STLR — Load-Acquire / Store-Release
```

```c
/* ARM example: Without barriers, this can fail */

/* CPU 0 */                 /* CPU 1 */
data = 42;                  while (!flag) ;
DMB ISH;                    DMB ISH;
flag = 1;                   print(data);

/* The DMB ISH (Inner Shareable) barrier ensures:
 * CPU 0: The store to 'data' is visible before the store to 'flag'
 * CPU 1: The load of 'flag' completes before the load of 'data'
 */
```

### ARM Barrier Types

```
ARM/AArch64 Memory Barriers
────────────────────────────
DMB (Data Memory Barrier):
  Ensures that all memory accesses before DMB are observed
  before any memory accesses after DMB
  
  Variants:
    DMB ISH  — Inner Shareable (most common in Linux)
    DMB OSH  — Outer Shareable
    DMB SY   — Full system
    DMB ISHST — Store-only, Inner Shareable
    DMB ISHLD — Load-only, Inner Shareable

DSB (Data Synchronization Barrier):
  Like DMB, but also ensures completion of all prior
  memory accesses before any subsequent instructions execute
  
  Used for: TLB maintenance, cache maintenance, interrupt ack

ISB (Instruction Synchronization Barrier):
  Flushes the instruction pipeline
  Ensures context changes (page tables, ASID) take effect
  
  Used after: TTBR changes, SCTLR changes, CP15 changes

LDAR/STLR (Acquire/Release):
  Load-Acquire: subsequent memory accesses cannot be reordered before
  Store-Release: prior memory accesses cannot be reordered after
  Provides one-way ordering (lighter than DMB)
```

```asm
; AArch64 barrier examples

; Full memory barrier
DMB ISH

; Load-Acquire (orders subsequent loads/stores)
LDAR X0, [X1]         ; Load with acquire semantics

; Store-Release (orders prior loads/stores)
STLR X0, [X1]         ; Store with release semantics

; Compare-and-swap with acquire/release
CASAL W0, W1, [X2]   ; Atomic CAS with acquire-release

; Example: Spinlock implementation with acquire/release
; Lock:
1:  LDAXR W0, [X1]    ; Load-exclusive with acquire
    CBNZ  W0, 1b      ; If locked, retry
    STXR  W2, W1, [X1] ; Try to set lock
    CBNZ  W2, 1b       ; If store-exclusive failed, retry
    DMB ISH            ; Barrier after acquiring lock

; Unlock:
    DMB ISH            ; Barrier before releasing lock
    STLR  WZR, [X1]    ; Store zero with release
```

## PowerPC: Weakly Ordered

### PowerPC Memory Ordering

```
PowerPC Memory Ordering (Weakly Ordered)
─────────────────────────────────────────
✗ All four types of reordering can occur
✓ But: Dependencies are respected (address, data, control)

PowerPC provides specific barrier instructions:
  sync       — Full memory barrier (heavyweight)
  lwsync     — Light-weight sync (load-load, store-store, load-store)
               But NOT store-load ordering!
  eieio      — Enforce In-order Execution of I/O
               Orders I/O accesses but not cacheable memory
  isync      — Instruction sync (pipeline flush)
  
PowerPC also provides:
  ldarx/stdcx. — Load-linked/Store-conditional (atomics)
  twi/tw       — Trap instructions (used for speculation barriers)
```

```c
/* PowerPC spinlock example (from Linux kernel) */

/* Lock acquisition with lwsync barrier */
static inline void arch_spin_lock(arch_spinlock_t *lock)
{
    unsigned int tmp;
    
    __asm__ __volatile__(
        "1: lwarx   %0, 0, %1\n"     /* Load-linked */
        "   cmpwi   0, %0, 0\n"      /* Is it free? */
        "   bne-    2f\n"             /* No, spin */
        "   stwcx.  %2, 0, %1\n"     /* Try to acquire */
        "   bne-    1b\n"             /* Failed, retry */
        "   isync\n"                  /* Isync after lock acquire */
        "   b       3f\n"            /* Success */
        "2: lwzx    %0, 0, %1\n"     /* Re-read (spin) */
        "   cmpwi   0, %0, 0\n"
        "   bne-    2b\n"
        "   b       1b\n"            /* Try again */
        "3:\n"
        : "=&r"(tmp)
        : "r"(&lock->lock), "r"(1)
        : "cr0", "memory");
}

/* Lock release with lwsync barrier */
static inline void arch_spin_unlock(arch_spinlock_t *lock)
{
    __asm__ __volatile__(
        "lwsync\n"                   /* Release barrier */
        "stw %0, 0(%1)\n"           /* Clear lock */
        :
        : "r"(0), "r"(&lock->lock)
        : "memory");
}
```

## RISC-V: RVWMO (Relaxed Memory Order)

### RISC-V Memory Ordering

```
RISC-V Memory Model: RVWMO
───────────────────────────
RISC-V Weak Memory Ordering (RVWMO) is the base memory model.

Ordering rules (simplified):
  ✓ Address dependency: load ordered with later load/store using its value
  ✓ Data dependency: store ordered with later store using loaded value
  ✓ Control dependency: load ordered with later store (weakly)
  ✗ No other implicit ordering

Fence instructions:
  FENCE        — General fence (predecessor/successor sets)
  FENCE.I      — Instruction fence (I-cache coherence)
  FENCE.TSO    — TSO-compatible fence (strong ordering)
  FENCE.W, FENCE.R, FENCE.RW — Specific access type fences

Acquire/Release (Zaamo extension):
  AMO.OR.aq    — Atomic with acquire semantics
  AMO.OR.rl    — Atomic with release semantics
  AMO.OR.aqrl  — Atomic with acquire+release
```

```c
/* RISC-V fence instruction encoding */
/* FENCE pred, succ */
/* pred/succ bits: bit 0 = device I/O, bit 1 = memory read,
                   bit 2 = memory write, bit 3 = instruction fetch */

/* FENCE RW, RW — Full fence (reads and writes) */
/* Equivalent to: all loads/stores before are ordered before
                  all loads/stores after */

/* RISC-V atomic example with fences */
static inline int atomic_cmpxchg(atomic_t *v, int old, int new)
{
    int prev;
    
    __asm__ __volatile__(
        "1: lr.w    %0, %1\n"        /* Load-reserved */
        "   bne     %0, %2, 2f\n"    /* Compare */
        "   sc.w    %3, %3, %1\n"    /* Store-conditional */
        "   bnez    %3, 1b\n"        /* Retry if failed */
        "   fence   rw, rw\n"        /* Full fence after success */
        "   j       3f\n"
        "2: lr.w    %0, %1\n"        /* Re-read on failure */
        "3:\n"
        : "=&r"(prev), "+A"(v->counter)
        : "r"(old), "r"(new)
        : "memory");
    
    return prev;
}
```

## Linux Kernel Memory Barriers

### Barrier Types

```c
/* Linux provides architecture-independent memory barriers */

/* Compiler barriers (prevent compiler reordering) */
barrier()               /* Compiler barrier (not CPU) */
READ_ONCE(x)           /* Volatile read (prevent compiler optimization) */
WRITE_ONCE(x, v)       /* Volatile write */

/* CPU memory barriers */
mb()                    /* Full memory barrier (read + write) */
rmb()                   /* Read memory barrier */
wmb()                   /* Write memory barrier */

/* SMP barriers (no-op on UP systems) */
smp_mb()                /* Full SMP memory barrier */
smp_rmb()               /* SMP read barrier */
smp_wmb()               /* SMP write barrier */
smp_mb__before_atomic() /* Barrier before atomic operation */
smp_mb__after_atomic()  /* Barrier after atomic operation */

/* Acquire/Release barriers (lighter than full barriers) */
smp_load_acquire(p)     /* Load with acquire semantics */
smp_store_release(p, v) /* Store with release semantics */
smp_acquire__after_ctrl_dep() /* Acquire after control dependency */
```

### Barrier Implementations by Architecture

```
Architecture    mb()        rmb()       wmb()       smp_mb()
──────────      ────        ─────       ─────       ────────
x86_64          mfence      lfence      sfence      lock; addl
ARM/AArch64     dmb sy      dmb sy      dmb st      dmb ish
PowerPC         sync        sync        lwsync      lwsync
RISC-V          fence rw,rw fence r,r   fence w,w   fence rw,rw
MIPS            sync        sync        sync        sync
```

### Using Barriers Correctly

```c
/* Example: Correct message passing with barriers */

struct message {
    int data;
    int ready;      /* Flag indicating data is valid */
};

/* Producer (CPU 0) */
void producer(struct message *msg)
{
    msg->data = 42;             /* Store data */
    smp_wmb();                  /* Write barrier: ensure data
                                   is visible before flag */
    WRITE_ONCE(msg->ready, 1);  /* Set flag */
}

/* Consumer (CPU 1) */
void consumer(struct message *msg)
{
    while (!READ_ONCE(msg->ready))  /* Read flag */
        cpu_relax();                /* Spin hint */
    
    smp_rmb();                      /* Read barrier: ensure flag
                                       read completes before data read */
    printf("%d\n", msg->data);       /* Read data — guaranteed 42 */
}
```

### Lock-Based Ordering

```c
/* Spinlocks provide implicit ordering */
spin_lock(&my_lock);
/* All accesses inside the lock are ordered with respect to
 * other CPUs that also take the same lock */
x = shared_data;
shared_data = y;
spin_unlock(&my_lock);
/* spin_unlock implies smp_mb() on most architectures */

/* RCU provides read-side ordering */
rcu_read_lock();
p = rcu_dereference(gp);    /* Ordered read of pointer */
if (p) {
    /* Access p->field — safe because of rcu_dereference */
    do_something(p->field);
}
rcu_read_unlock();
```

## Formal Verification

### Memory Model Formalization

```
Memory Model Formal Verification
────────────────────────────────
The Linux kernel memory model (LKMM) has been formally specified
using the "herd" tool:

LKMM (Linux Kernel Memory Model):
  • Formal specification in tools/memory-model/
  • Defines allowed/forbidden reorderings
  • Used to verify litmus tests (small concurrent programs)
  • Based on the "promising" memory model

Tools:
  herd7    — Memory model simulator
  klitmus7 — Generates kernel modules from litmus tests
```

```c
/* Example litmus test: Message Passing (MP) */
/* C-A-R-B: Can both reads see 0? */

C mp

(*
 * Result: Never (on any architecture)
 * The dependency chain ensures ordering
 *)

{
  x = 0; y = 0;
}

P0(int *x, int *y) {
  WRITE_ONCE(*x, 1);
  smp_wmb();
  WRITE_ONCE(*y, 1);
}

P1(int *x, int *y) {
  int r0 = READ_ONCE(*y);
  smp_rmb();
  int r1 = READ_ONCE(*x);
}

exists (1:r0=1 /\ 1:r1=0)
/* This should NEVER be true (forbidden) */
```

```bash
# Run litmus test with herd7
$ herd7 -conf linux-kernel.cfg testsuites/litmus-tests/MP+fences.litmus

# Result:
# Test MP Allowed
# States 3
# 1:r0=0; 1:r1=0;
# 1:r0=0; 1:r1=1;
# 1:r0=1; 1:r1=1;
# No
# Witnesses
# Positive: 0 Negative: 3
# Condition exists (1:r0=1 /\ 1:r1=0)
# Observation MP Never 0 3
```

## Memory Model Comparison

```
Architecture Memory Model Comparison
────────────────────────────────────
Feature              x86 (TSO)    ARM         PowerPC     RISC-V
──────────           ─────────    ───         ───────     ──────
Load-Load order      ✓ Yes        ✗ No        ✗ No        ✗ No
Store-Store order    ✓ Yes        ✗ No        ✗ No        ✗ No
Load-Store order     ✓ Yes*       ✗ No        ✗ No        ✗ No
Store-Load order     ✗ No         ✗ No        ✗ No        ✗ No
Dependency order     ✓ Yes        ✓ Yes       ✓ Yes       ✓ Yes

Full barrier         mfence       dmb sy      sync        fence rw,rw
Light barrier        lfence/sfence dmb ish    lwsync      fence r/w
Acquire/Release      lock prefix  ldar/stlr   —           aq/rl bits

Model strength:      Strongest ──────────────────────→ Weakest
                     x86 > ARM > PowerPC ≈ RISC-V

* x86: load-store ordering only to same address
```

## Practical Guidelines

### When to Use Barriers

```c
/* Rule 1: Use READ_ONCE/WRITE_ONCE for all shared variables */
data = shared_var;           /* BAD: compiler may optimize */
data = READ_ONCE(shared_var); /* GOOD: volatile read */

/* Rule 2: Use smp_mb() for full ordering when needed */
/* Rule 3: Use smp_wmb()/smp_rmb() for producer/consumer patterns */
/* Rule 4: Use smp_load_acquire/smp_store_release for lock-free code */
/* Rule 5: Prefer locks (spin_lock/spin_unlock) — they handle ordering */
/* Rule 6: Prefer RCU for read-mostly data structures */
```

### Common Mistakes

```
Common Memory Ordering Mistakes
───────────────────────────────
1. Missing barriers in producer/consumer
   BAD:  data = 42; flag = 1;  /* ARM/PowerPC may reorder */
   GOOD: data = 42; smp_wmb(); flag = 1;

2. Using barrier() instead of smp_mb()
   barrier() only prevents compiler reordering, not CPU reordering

3. Forgetting READ_ONCE/WRITE_ONCE
   Without them, compiler can merge/split/reorder accesses

4. Assuming x86 ordering on all architectures
   Code tested only on x86 may break on ARM

5. Over-using barriers (performance impact)
   smp_mb() on ARM generates expensive DMB instructions
   Use the weakest barrier that's sufficient
```

## References and Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- Linux kernel memory barriers documentation: https://www.kernel.org/doc/html/latest/process/volatile-considered-harmful.html
- Linux kernel memory-barriers.txt: https://www.kernel.org/doc/html/latest/memory-barriers.html
- LKMM (Linux Kernel Memory Model): https://github.com/torvalds/linux/tree/master/tools/memory-model
- x86 memory ordering: Intel SDM Volume 3, Chapter 8
- ARM memory ordering: ARM Architecture Reference Manual, Chapter B2
- PowerPC memory ordering: Power ISA, Book II
- RISC-V memory model: RISC-V ISA Manual, Chapter 14
- Paul McKenney's "Is Parallel Programming Hard?": https://mirrors.edge.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html
- "Memory Barriers: A Hardware View for Software Hackers" — Paul McKenney
- herd7 tool: https://github.com/herd/herdtools7
- "A Tutorial Introduction to the ARM and POWER Relaxed Memory Models" — Pulte et al.

## Related Topics

- [x86 Architecture](./x86.md) — TSO memory model
- [ARM Architecture](./arm.md) — relaxed memory ordering
- [RISC-V Architecture](./riscv.md) — RVWMO model
- [PowerPC Architecture](./powerpc.md) — weakly ordered model
- [Key Kernel Subsystems](../history/subsystems.md) — subsystems using barriers
- [Calling Conventions](./calling-conventions.md) — ABI implications
