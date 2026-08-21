# Atomic Primitives — Hardware, Memory Ordering, C11, and C++ `std::atomic`

An atomic operation is one the hardware guarantees is indivisible with
respect to other cores' accesses to the same address: no torn reads, no
torn writes, no interleaving at the cache-line level. The compiler
cannot reorder atomic ops past each other in ways that break the
guarantee, and the cache-coherence protocol delivers the
before-or-after semantics.

This chapter covers what the CPU actually executes when you write
`atomic_fetch_add`, what the C11 and C++ language bindings look like,
the five memory orderings and which one you actually want, and two
famous gotchas — false sharing and the missing 128-bit DCAS — that
cause real bugs even in otherwise-correct code. Read
[Memory Model](./memory-model.md) first for the happens-before
vocabulary, and [Lock-Free Programming](./lock-free.md) for the CAS
patterns.

## CPU atomic instructions

### x86 (Intel SDM vol 2 & 3)

x86 has three relevant atomic primitives:

- `XCHG`: exchange. Implicit lock prefix. Used for spinlocks
  (`__sync_lock_test_and_set`) and to implement `atomic_flag`.
- `LOCK CMPXCHG`: compare-and-swap. The `LOCK` prefix asserts the
  `#LOCK` signal on the cache line, acquiring exclusive ownership. This
  is what a CAS lowers to.
- `LOCK ADD`, `LOCK INC`, `LOCK XADD`: read-modify-write that targets
  memory directly. `fetch_add` lowers to `LOCK XADD` (one instruction,
  one locked cycle).

The `LOCK` prefix is a full hardware fence on x86: it issues an
`MFENCE`-equivalent effect around the locked instruction. This is why
x86 is described as TSO (Total Store Order) with store-buffer
forwarding — most orderings are free or near-free, and only
`memory_order_seq_cst` stores cost an explicit fence (typically a
`MOV` to a separate address followed by `MFENCE`, or a `XCHG` which is
implicitly locked).

### ARM (v7 / v8)

ARM uses the **load-linked / store-conditional** pattern, not a single
CAS instruction. The CPU holds an *exclusive monitor* on a cache line;
a `STREX` to that line succeeds only if the monitor is still held, and
fails (returning a status) if anything invalidated the line.

- ARMv7: `LDREX` / `STREX`
- ARMv8: `LDXR` / `STXR`; acquire/release variants `LDAXR` / `STLXR`

A C11 `atomic_compare_exchange_strong` compiles to roughly:

```asm
1:  ldaxr w1, [x0]          ; load-acquire exclusive
    cmp   w1, w2
    bne   2f                 ; expected mismatch, bail
    stlxr w3, w3, [x0]       ; store-release exclusive
    cbnz  w3, 1b             ; store failed -> retry
2:  ...
```

`STXR` returns nonzero if the monitor was invalidated — which can
happen on *any* interrupt, *any* access to the cache line by another
core, *any* context switch (some kernels clear all monitors on
schedule). This is why ARM CAS loops must be tight and bounded: every
spurious failure is wasted work. It is also why the C++ standard
permits `compare_exchange_weak` to spuriously fail — ARM is the reason
the distinction exists.

### PowerPC

`lwarx` (load-word-and-reserve-indexed) and `stwcx.` (store-word-
conditional-indexed) — the same LL/SC pattern as ARM. Power also has:

- `lwsync` (lightweight sync): orders store-store and load-store, but
  not store-load. Cheaper than a full `sync`.
- `sync` (heavyweight): orders everything. Equivalent to x86 `MFENCE`.
- `isync`: instruction-sync only; pairs with a conditional branch to
  create an acquire fence.

Power's memory model is notoriously hard; the C++ standard committee
spent years arguing about whether `memory_order_consume` could be
efficiently lowered on Power (the answer turned out to be: almost
never, so `consume` was effectively downgraded to `acquire`).

### Other architectures

- **RISC-V**: `lr`/`sc` (atomic extension); also `amoadd.w`, `amoxor.w`
  for direct RMW.
- **MIPS**: `ll`/`sc`.
- **Alpha**: no LL/SC, only `MB` (memory barrier) and ordered loads.
  Alpha required an explicit barrier even on a *data-dependent* load
  — which is why Crossbeam and Linux historically had
  `#ifdef __alpha__` branches for `smp_read_barrier_depends()`.
  Alpha is essentially retired but the scars remain in standard
  wording.
- **Itanium**: `cmpxchg` with an ordering hint field. The C++11 memory
  model was designed with IA-64 in mind — `acquire`/`release` are
  native Itanium concepts. Then Intel killed Itanium and we are left
  with the legacy.

## Memory ordering

C11 §7.17.4 and C++ §31.4 (in C++11/N3291 it was §29) define five
orderings. Six, technically, but `memory_order_consume` has been
"effectively unimplementable" for so long that the committee is
considering removing it.

| Ordering | Guarantees |
|---|---|
| `relaxed` | Atomicity only; no ordering with other memory |
| `consume` | Data-dependent load ordering (treated as `acquire` in practice) |
| `acquire` | This load synchronizes-with a `release` store on the same address |
| `release` | This store releases prior writes (non-atomic) to whoever acquires the same address |
| `acq_rel` (RMW only) | Both — acquire for the load, release for the store |
| `seq_cst` | Single total order of all seq_cst ops, even across unrelated addresses; strongest; the default |

The release-acquire idiom is the workhorse:

```
Thread A:
  data = compute();                       // non-atomic store
  flag.store(1, memory_order_release);    // releases `data`

Thread B:
  while (!flag.load(memory_order_acquire)) {}    // acquires `data`
  assert(data == compute());                    // guaranteed
```

Without the `acquire`/`release` pair, Thread B can see `flag == 1` but
`data` uninitialized — the compiler or CPU may have reordered the two
stores (the store to `flag` ahead of the store to `data`), or reordered
the two loads on B's side.

`seq_cst` is stronger than `acq_rel` because it provides a *total
order* across all seq_cst operations, even on unrelated addresses. On
x86, `seq_cst` stores compile to `XCHG` or `MOV + MFENCE` — extra
cost; on `seq_cst` loads, no extra cost (TSO gives you the ordering
for free). On ARM, `seq_cst` requires a `dmb ish` fence on every store
and every load — substantial overhead, which is why lock-free code on
ARM is so careful about using the weaker orderings.

The practical rule: use `seq_cst` unless you have profiled evidence you
can do better. Use `acquire`/`release` for one-shot publication (a
flag, a one-time init). Use `relaxed` only for counters and statistics
where you don't care about ordering, only atomicity.

## C11 atomics — `<stdatomic.h>`

C11 (ISO/IEC 9899:2011) added `<stdatomic.h>` in §7.17. The core
types and operations:

- `atomic_flag` — the only type *guaranteed* to be lock-free on every
  conforming implementation. Provides `atomic_flag_test_and_set` and
  `atomic_flag_clear`.
- `atomic_bool`, `atomic_int`, `atomic_size_t`, `atomic_uintptr_t`,
  `atomic_ullong`, and friends — typedef aliases of the corresponding
  scalar types.
- Operations: `atomic_init`, `atomic_store`, `atomic_load`,
  `atomic_exchange`, `atomic_compare_exchange_strong` /
  `_weak` (with `_explicit` variants that take a memory order),
  `atomic_fetch_add`, `atomic_fetch_sub`, `atomic_fetch_or`,
  `atomic_fetch_xor`, `atomic_fetch_and`.
- The macros `ATOMIC_INT_LOCK_FREE`, `ATOMIC_POINTER_LOCK_FREE`, etc.
  give compile-time lock-freedom: `2` means "always lock-free",
  `1` means "sometimes," `0` means "never."
- `atomic_is_lock_free(ptr)` is the runtime check.

```c
#include <stdatomic.h>
#include <stdbool.h>

static atomic_int counter = 0;

void inc(void) {
    atomic_fetch_add_explicit(&counter, 1, memory_order_relaxed);
}

int load(void) {
    return atomic_load(&counter);   // seq_cst by default
}

bool cas(int expected, int new_val) {
    return atomic_compare_exchange_strong(
        &counter, &expected, new_val);
}
```

C11 guarantees only `atomic_flag` is lock-free; everything else is
implementation-defined. In practice on x86-64 and ARM64 Linux,
`atomic_int`, `atomic_ptr`, and `atomic_llong` are always lock-free;
`atomic_long_double` (80-bit on x87) is *not* — it requires a lock.

## C++ `std::atomic<T>` — `<atomic>`

C++11 added `<atomic>` (placed in §29 of the C++11 working draft
N3291; renumbered to §31 in C++17 and beyond). It mirrors C11 with
templates:

```cpp
#include <atomic>

std::atomic<int> a{0};
a.fetch_add(1, std::memory_order_relaxed);

int expected = a.load(std::memory_order_relaxed);
bool ok = a.compare_exchange_weak(
    expected, expected + 1,
    std::memory_order_acq_rel,    // success ordering
    std::memory_order_acquire);  // failure ordering (no write happens)
```

The two-argument form of `compare_exchange_*` lets the success and
failure orderings differ. The failure ordering *cannot* be `release`
or `acq_rel` (no store happens on failure), and *cannot* be stronger
than the success ordering. The common pattern: `acq_rel` on success,
`acquire` on failure — so even a losing retry sees the most recent
release-store of the location.

Notable additions in later standards:

- `std::atomic_ref<T>` (C++20): atomic access to an existing object.
  Useful for retrofitting atomics into struct fields without changing
  the type.
- `std::atomic<T>::wait` / `notify_one` / `notify_all` (C++20):
  address-based waiting, modeled on Linux `futex` and Windows
  `WaitOnAddress`. Cheaper than a condition variable for one-shot
  signaling.
- `std::atomic_signed` / `std::atomic_unsigned` `lock_free` constexpr
  queries.
- Hazard pointers (P2530) and RCU (P2545), slated for C++26.

## `atomic_flag` and the spinlock

`atomic_flag` is the lowest-level primitive in the standard. It
supports exactly two states and two operations:
`atomic_flag_test_and_set` (returns the previous state, sets to
"set") and `atomic_flag_clear`. It is the *only* type guaranteed to
be lock-free on every platform, which makes it the basis for
implementations of locks and other higher-level primitives.

```cpp
struct Spinlock {
    std::atomic_flag f{};

    void lock() {
        while (f.test_and_set(std::memory_order_acquire)) {
            _mm_pause();              // x86 hint: spin-wait loop
        }
    }
    void unlock() {
        f.clear(std::memory_order_release);
    }
};
```

Why not use `atomic_flag` everywhere? It has only two values. For a
counter you need `atomic<int>`. For a tagged pointer you need
`atomic<uintptr_t>` plus a packed tag, or `std::atomic<TaggedPtr>`
which may or may not be lock-free depending on the platform's
double-word CAS support.

## False sharing

Two atomics on the same cache line cause coherence traffic even when
no *logical* sharing happens. The cache line is the unit of coherence;
any store by any core invalidates the line on every other core, even
if those cores only read the *other* atomic.

```cpp
struct Bad {
    std::atomic<int> a;      // Thread A writes here
    std::atomic<int> b;      // Thread B writes here
};
// 8 bytes apart, same 64-byte cache line.
// Every write to `a` invalidates the line on Thread B's core;
// B reloads the line, sees `a` changed (which it doesn't care about),
// and the next write to `b` does the same thing back to A.
```

The fix is to pad to a cache line. C++11 added `alignas` for this;
the Disruptor and Crossbeam both use `#[repr(align(64))]` or
`alignas(64)`.

```cpp
struct alignas(64) PaddedAtomic {
    std::atomic<int> v;
};

struct Good {
    PaddedAtomic a;          // own cache line
    PaddedAtomic b;          // own cache line
};
// Each write invalidates only that line on the other core. No false sharing.
```

Java has `@jdk.internal.vm.annotation.Contended` (since 8u40), used
inside `CounterCell` and `Cell` (the `LongAdder` cells). The
annotation adds 128 bytes of padding by default, not 64, because some
ARM SoCs have "prefetch" hardware that fetches two cache lines at a
time.

The general rule: if two fields are written by different threads and
they are <64 bytes apart, they false-share. Per-thread state in a
struct indexed by thread ID is the canonical victim.

## The 128-bit DCAS mirage

DCAS = Double-Word Compare-And-Swap. CAS over two adjacent machine
words in one atomic operation. Why you might want it: pointer-tagging
schemes pack `(pointer, version)` into a 128-bit pair and need to CAS
the pair atomically. Hazard-pointer schemes sometimes need 2-word
atomics for safe publication.

Where it exists:

- **32-bit x86**: `CMPXCHG8B` — CAS an 8-byte pair (two 32-bit words).
  Available since the original Pentium.
- **64-bit x86**: `CMPXCHG16B` — CAS a 16-byte pair (two 64-bit
  words). Requires the `CPUID.001H:ECX.CX16[bit13]` feature flag,
  which is set on every CPU shipped since about 2013. Early Athlon 64s
  lacked it.

Where it doesn't:

- **ARM** — there is no native DCAS. ARMv8.3 added `LDP` / `STP` with
  acquire/release semantics, but only single-copy-atomic on the
  individual words, not the pair as a whole. Real 128-bit atomics on
  ARM are typically emulated with a global lock (Linux kernel falls
  back to `__cmpxchg_...` helpers) or avoided by restructuring the
  algorithm.
- **PowerPC**, **MIPS**, **RISC-V**: same story — no DCAS.

The consequence: pointer-tagging tricks that need a 2-word CAS work
natively on x86-64 (with `cmpxchg16b`) but have to fall back to a
global lock, a smaller tag, or a different algorithm on ARM. Crossbeam's
`Atomic<T>` uses `AtomicU128` on x86-64 when available; on other
platforms it falls back to a packed tag (16-bit version packed into the
high bits of a 48-bit pointer) or a spinlock.

There is no widely-available 128-bit DCAS that is also wait-free across
architectures. If you absolutely need 128-bit atomics, the practical
options are:

1. Use a `std::mutex` (the lock-based fallback). Correct, slightly
   slower.
2. Restructure so you don't need a 2-word CAS — use hazard pointers
   or epochs for the lifetime question (so the CAS only needs to
   cover the pointer, not a version tag), and use a separate atomic
   for the version counter.
3. On x86-64 only, use `__sync_bool_compare_and_swap` on a
   `__int128`; mark it as non-portable.

The most useful interview framing: lock-free code that needs DCAS is
often actually asking the wrong question. The lifetime of the
pointed-to object should be managed by a reclamation scheme, and the
version counter can frequently live in a separate atomic that's
checked after the CAS — see [ABA and Reclamation](./aba-problem.md)
for the pattern.

## Cross-references

- [Memory Model](./memory-model.md) — happens-before across languages
- [Lock-Free Programming](./lock-free.md) — CAS loops and orderings in practice
- [Lock-Free Structures](./lock-free-structures.md) — Treiber stack, Michael-Scott queue
- [ABA and Reclamation](./aba-problem.md) — where DCAS would have helped, and what we use instead
- [Readers-Writers](./readers-writers.md) — when atomics are not enough
- [Work-Stealing Scheduler](./work-stealing.md) — Chase-Lev deque: two atomics with careful ordering

## References

- ISO/IEC 9899:2011 (C11) §7.17 "Atomics" — `<stdatomic.h>`, atomic types, atomic operations. cppreference mirror: [c/atomic](https://en.cppreference.com/w/c/atomic)
- ISO/IEC 14882:2011 (C++11) §29 "Atomic operations library"; renumbered to §31 in C++17+. cppreference mirror: [cpp/atomic](https://en.cppreference.com/w/cpp/atomic)
- Herb Sutter, ["atomic<> Weapons" (CppCon 2012, parts 1 & 2)](https://www.youtube.com/watch?v=Ke7dPhV9lys) — covers ordering, fences, hardware implications, the cost of `seq_cst` across arches
- Paul E. McKenney, [*Is Parallel Programming Hard, And, If So, What Can You Do About It?*](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html) — atomics across architectures, memory-barrier semantics, RCU
- Intel 64 and IA-32 Architectures Software Developer's Manual, vol 2 (instruction set) and vol 3 ch 8 "Multiple-Processor Management" and ch 9 "Memory Ordering"
- ARM Architecture Reference Manual (ARM ARM), v8, vol B — `LDXR`/`STXR` and the exclusive monitor semantics
- LLVM atomic operations and concurrency docs: [llvm.org/Atomics](https://llvm.org/docs/Atomics.html) — how the compiler lowers atomic operations to per-arch instructions
- Linux kernel, [Documentation/atomic_t.txt](https://www.kernel.org/doc/Documentation/atomic_t.txt) — the kernel's atomic semantics and ordering rules
