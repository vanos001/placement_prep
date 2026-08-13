# Compare-and-Swap (CAS)

## Overview

**Compare-and-Swap (CAS)** is the most important atomic hardware instruction for building lock-free data structures. It atomically compares a memory location to an expected value and, if equal, writes a new value. If not equal, it fails and the caller can retry.

## The Instruction

```c
// Pseudocode
bool CAS(int *addr, int expected, int new_value) {
    // This entire operation is ATOMIC
    if (*addr == expected) {
        *addr = new_value;
        return true;   // Success
    } else {
        return false;  // Failed — *addr was not expected
    }
}

// Actual return: the OLD value
int CAS(int *addr, int expected, int new_value) {
    int old = *addr;
    if (old == expected)
        *addr = new_value;
    return old;  // Caller checks if old == expected
}
```

### x86 Implementation

```asm
; CMPXCHG instruction
; EAX = expected value
; Destination = memory location
; Source = new value
; If [destination] == EAX: [destination] = source, ZF=1
; Else: EAX = [destination], ZF=0

lock cmpxchg [dest], src
```

The `lock` prefix ensures atomicity across CPUs.

### C11 / GCC Built-ins

```c
#include <stdatomic.h>

int old = atomic_load(&value);
do {
    // Prepare new value based on old
    new_value = old + 1;
} while (!atomic_compare_exchange_weak(&value, &old, new_value));

// GCC built-in (older)
int old = __sync_val_compare_and_swap(&value, expected, new_value);

// __sync_bool_compare_and_swap returns true/false
```

## CAS vs test_and_set

| Aspect | CAS | test_and_set |
|--------|-----|-------------|
| Operation | Compare and conditionally swap | Unconditionally set to true |
| Return | Old value | Old value |
| Flexibility | Can update to any value | Only set to true |
| ABA problem | Yes | No (binary state) |
| Use case | Lock-free algorithms | Simple spinlocks |

## CAS-Based Spinlock

```c
#include <stdatomic.h>

atomic_int lock = 0;

void acquire() {
    int expected = 0;
    while (!atomic_compare_exchange_weak(&lock, &expected, 1)) {
        expected = 0;  // Reset expected (CAS may have updated it)
    }
}

void release() {
    atomic_store(&lock, 0);
}
```

## CAS-Based Counter (Lock-Free)

```c
atomic_int counter = 0;

void increment() {
    int old_val, new_val;
    do {
        old_val = atomic_load(&counter);
        new_val = old_val + 1;
    } while (!atomic_compare_exchange_weak(&counter, &old_val, new_val));
}
```

**Thread 1**: old=5, new=6 → CAS(5→6) → Success
**Thread 2**: old=5, new=6 → CAS(5→6) → Fail (counter is now 6) → Retry with old=6

## strong vs weak CAS

```c
// weak: may fail spuriously (faster on some architectures)
atomic_compare_exchange_weak(&val, &expected, new_val);

// strong: never fails spuriously
atomic_compare_exchange_strong(&val, &expected, new_val);
```

**When to use weak**: In a retry loop (spurious failure just causes another iteration). This is the recommended choice for CAS loops — it can be faster on LL/SC architectures (ARM, RISC-V).

**When to use strong**: When you need a single CAS attempt without a loop.

## Memory Ordering

```c
// Relaxed — no ordering guarantees
atomic_compare_exchange_weak(&val, &expected, new_val,
                             memory_order_relaxed, memory_order_relaxed);

// Acquire-release — standard for locks
atomic_compare_exchange_weak(&val, &expected, new_val,
                             memory_order_acquire, memory_order_acquire);

// Sequential consistency — strongest
atomic_compare_exchange_weak(&val, &expected, new_val,
                             memory_order_seq_cst, memory_order_seq_cst);
```

| Ordering | Use Case |
|----------|----------|
| `relaxed` | Counters, statistics (no ordering needed) |
| `acquire` | Lock acquire (subsequent reads see prior writes) |
| `release` | Lock release (prior writes visible to acquirer) |
| `seq_cst` | Default, strongest (total order) |

## ABA Problem with CAS

```
Thread 1: reads *ptr = A
Thread 1: wants to CAS(A → C)
Thread 1: preempted

Thread 2: changes *ptr = B
Thread 2: changes *ptr = A  (back to A!)

Thread 1: resumes, CAS(A → C) succeeds
But the state may have changed (A's linked list may be different)
```

### Solutions

1. **Double-word CAS (DWCAS)**: CAS on (value, version) pair
2. **Hazard pointers**: Protect reads
3. **Epoch-based reclamation**: Deferred freeing

## Hardware CAS Support

| Architecture | Instruction | Width |
|-------------|-------------|-------|
| x86/x64 | `CMPXCHG`, `CMPXCHG8B`, `CMPXCHG16B` | 32/64/128-bit |
| ARM | `LDREX`/`STREX` (load-linked/store-conditional) | 32/64-bit |
| RISC-V | `LR`/`SC` (load-reserved/store-conditional) | 32/64-bit |
| MIPS | `LL`/`SC` | 32/64-bit |

### LL/SC vs CAS

**CAS**: Single atomic instruction. May have ABA problem.

**LL/SC** (Load-Linked / Store-Conditional):
```c
// Pseudocode for LL/SC
do {
    old = LL(addr);        // Load-linked: marks the cache line
    new_val = old + 1;
} while (SC(addr, new_val) == FAIL);  // Store-conditional: fails if cache line modified
```

**Advantage**: No ABA problem (any modification to the cache line causes SC to fail). **Disadvantage**: SC can fail spuriously (e.g., context switch clears the link).

## Interview Questions

**Q1: What is compare-and-swap and why is it important?**

CAS atomically compares a memory location to an expected value and, if equal, writes a new value. It's the foundation of lock-free programming — it allows threads to agree on state changes without locks. If the CAS fails (another thread changed the value), the caller retries with the updated value.

**Q2: What is the ABA problem in CAS?**

The ABA problem: a value changes A→B→A between a read and CAS. The CAS succeeds but the state may have changed (e.g., the linked list starting at A has been reorganized). Solutions: tagged pointers (version counter), hazard pointers, or LL/SC (which avoids ABA naturally).

**Q3: What is the difference between `compare_exchange_weak` and `compare_exchange_strong`?**

Weak may fail spuriously (on LL/SC architectures, context switches can cause failure). Strong never fails spuriously. Use weak in CAS retry loops (one more iteration is fine). Use strong when you need a single attempt.

**Q4: How does CAS work on x86 vs ARM?**

x86: `CMPXCHG` is a single instruction with `lock` prefix for atomicity. ARM: uses `LDREX`/`STREX` (load-linked/store-conditional) — the exclusive monitor on the cache line tracks whether any other CPU modified it. If yes, `STREX` fails. This is why `weak` CAS is preferred on ARM.

**Q5: What memory ordering should you use with CAS?**

For lock acquire: `memory_order_acquire` (ensures subsequent reads see writes before the lock was released). For lock release: `memory_order_release` (ensures writes are visible to the next acquirer). For counters/stats: `memory_order_relaxed` (no ordering needed, just atomicity). Default is `seq_cst` which is safe but may be slower.

## Common Mistakes

- Not resetting `expected` after a failed CAS (the value may have changed to something else)
- Using `seq_cst` ordering when `acquire/release` suffices (performance cost)
- Forgetting that CAS loops can livelock under heavy contention (exponential backoff helps)
- Assuming CAS is always faster than locks — under low contention, locks may be faster
- Not handling the ABA problem in linked data structures

## Summary

- CAS atomically compares and conditionally updates a memory location
- Foundation of lock-free data structures and algorithms
- x86: `CMPXCHG` instruction. ARM/RISC-V: LL/SC pairs
- ABA problem: value changes A→B→A, CAS succeeds incorrectly
- Memory ordering matters: acquire/release for locks, relaxed for counters
- weak vs strong: use weak in loops, strong for single attempts

## Cross-References

- [Lock-Free](lock-free.md) — data structures built with CAS
- [Memory Barriers](memory-barriers.md) — ordering guarantees
- [Spinlocks](spinlocks.md) — CAS-based spinlock implementation
- [Critical Section](critical-section.md) — the problem CAS solves
