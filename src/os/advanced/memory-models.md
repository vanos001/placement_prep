# Memory Models and Memory Ordering

Modern CPUs and compilers reorder memory operations for performance. The **memory model** defines which reorderings are allowed and which operations a thread can observe from other threads. Understanding memory models is essential for writing correct lock-free code, understanding why seemingly correct concurrent programs fail, and debugging subtle data races. The [memory barriers basics](../synchronization/memory-barriers.md) cover the Linux API surface; this section explains the underlying models.

## Why Reordering Happens

CPUs reorder memory operations for three reasons:

1. **Store buffers**: A CPU core writes to a store buffer (a small FIFO) before the data reaches cache. Subsequent loads can read stale values from cache while the store is buffered. This is a **store-to-load reordering** — the most common and performance-critical reordering.

2. **Cache coherence latency**: On a MESI-based system, a store to a cache line in another core's Modified state requires an invalidate+acknowledge cycle (~40-100 ns). The CPU can continue executing independent loads/stores while waiting.

3. **Compiler optimization**: The C/C++ compiler may reorder loads and stores across sequence points if it can prove there's no data dependency within the single-threaded semantics. The compiler cannot see other threads.

## Sequential Consistency (SC)

Sequential consistency (Lamport, 1979) is the strongest memory model: the result of any execution is the same as if all operations were executed in some **total order** that is consistent with the program order of each individual thread. In plain terms: operations appear to execute one at a time, in an order that respects each thread's code order.

No modern CPU implements sequential consistency by default. The hardware cost would be enormous: every load would have to wait for all prior stores to reach cache, and all prior loads to complete. x86 comes closest but still allows store-to-load reordering. ARM, RISC-V, and POWER allow even more aggressive reordering.

## x86-TSO — Total Store Order

x86 implements the **Total Store Order** (TSO) model, which is "almost" sequential consistency with one allowed reordering:

**Store-to-load reordering is allowed**: a load can read from memory before a prior store to a *different* address becomes visible to other cores. The store sits in the store buffer while the load proceeds.

```
Core 0:          Core 1:
store A = 1      load B  (sees 0)
store B = 1      load A  (sees 0)

Result under SC: at least one load must see 1
Result under TSO: BOTH loads can see 0! (store buffer reordering)
```

What x86-TSO does NOT allow:
- Load-to-load reordering
- Store-to-store reordering  
- Load-to-store reordering
- A load reading from a store buffer of a *later* store (causality violation)

The x86 `MFENCE` (or `LOCK` prefix) instruction serves as a **full memory barrier**: it drains the store buffer and prevents all reorderings across it. `SFENCE` is store-only, `LFENCE` is load-only.

## Weak Memory Models — ARM, RISC-V, POWER

ARM (pre-v8), RISC-V (default), and POWER allow significantly more reordering than x86-TSO:

- **Store-to-load reordering**: Yes (same as x86)
- **Load-to-load reordering**: Yes (a later load can observe a value before an earlier load)
- **Load-to-store reordering**: Yes (a store can become visible before an earlier load)
- **Store-to-store reordering**: Yes (stores can be reordered)

```
Core 0 (ARM/POWER):   Core 1:
store A = 1            load A  (sees 1)
store B = 1            load B  (sees 0)  ← store B reordered after store A visible

This outcome is IMPOSSIBLE on x86-TSO but LEGAL on ARM/POWER.
```

ARM v8 introduced `LDAR` (Load-Acquire) and `STLR` (Store-Release) instructions to implement acquire/release semantics efficiently. RISC-V has `FENCE RW, RW` for a full barrier and `FENCE R, RW` / `FENCE RW, W` for acquire/release. POWER has `LWSYNC` (lightweight sync, weaker than full sync).

## Acquire and Release Semantics

Acquire and release provide a **portable abstraction** over hardware-specific barriers, used by C11/C++11 `std::atomic`, Java `volatile`, and Linux `smp_load_acquire()` / `smp_store_release()`.

- **Acquire** (on a load): No subsequent memory operations (loads or stores) can be reordered before this load. In hardware: a load-acquire prevents later loads/stores from executing before this load completes.

- **Release** (on a store): No prior memory operations can be reordered after this store. In hardware: a store-release drains the store buffer before this store becomes visible.

- **Acquire-Release pair**: A release on thread A synchronizes-with an acquire on thread B that reads the release's store. All memory operations before the release are visible to all operations after the acquire.

```c
// Producer-consumer with acquire/release (no mutex needed)
// Shared: int data, bool ready

// Producer (Thread A):
data = 42;                        // (1) plain store
smp_store_release(&ready, true);  // (2) release: (1) must be visible before (2)

// Consumer (Thread B):
if (smp_load_acquire(&ready)) {   // (3) acquire: subsequent ops see prior stores
    assert(data == 42);           // (4) guaranteed to see 42 on ALL architectures
}
```

On x86-TSO, `smp_store_release` is a plain store (x86 already prevents store-store reordering), and `smp_load_acquire` is a plain load followed by a compiler barrier (x86 prevents load-load reordering). On ARM, `smp_store_release` compiles to `STLR`, and `smp_load_acquire` compiles to `LDAR`.

## The Linux Kernel Memory Model (LKMM)

The Linux Kernel Memory Model (LKMM, formalized 2018 by Luc Maranget, Alan Stern, Paul McKenney) specifies the memory ordering guarantees that kernel code can rely on, abstracting over x86, ARM, POWER, and RISC-V. It is formalized in **herd7** (a litmus test tool) and documented in `Documentation/memory-barriers.txt`.

### Key LKMM Primitives

- `smp_mb()`: Full memory barrier (all directions)
- `smp_rmb()`: Read barrier (subsequent reads can't precede prior reads)
- `smp_wmb()`: Write barrier (subsequent writes can't precede prior writes)
- `smp_load_acquire(p)`: Acquire load
- `smp_store_release(p, v)`: Release store
- `smp_store_mb(p, v)`: Release + full barrier after
- `READ_ONCE()` / `WRITE_ONCE()`: Compiler barrier only, no hardware barrier

### Litmus Tests

LKMM uses litmus tests to formally reason about allowed behaviors:

```
// MP (Message Passing) litmus test
// Can Thread B see data=0 AND ready=1?

Thread A:                Thread B:
WRITE_ONCE(data, 1);      r1 = READ_ONCE(ready);
smp_wmb();               r2 = READ_ONCE(data);
WRITE_ONCE(ready, 1);

exists (1:r1=1 /\ 1:r2=0)  // Is this result allowed?
```

On x86: NO (x86 prevents store-store reordering, so `smp_wmb()` is a no-op). On ARM pre-v8: YES (stores can be reordered, data might not be visible when ready is).

## False Sharing

False sharing occurs when two threads access **different variables that share the same cache line** (typically 64 bytes). The cache coherence protocol treats the entire line as a unit, so Thread A writing to variable X and Thread B writing to variable Y (both in the same 64-byte line) cause the line to bounce between cores at cache-coherence speed.

```
Cache line (64 bytes):
┌──────────┬──────────┬──────────┬──────────┐
│ var_a    │ padding  │ var_b    │ padding  │
│ (Core 0) │          │ (Core 1) │          │
└──────────┴──────────┴──────────┴──────────┘
  ↑ writes by Core 0        ↑ writes by Core 1
  Both invalidate the entire cache line for the other core
```

**Impact**: A contended cache line can reduce throughput by 10-100x. On a simple counter benchmark, 64 threads incrementing separate counters in the same cache line achieve ~50M ops/s; with cache-line alignment, ~2B ops/s.

**Detection**: `perf stat -e cache-misses` shows elevated miss rates. Intel VTune's "false sharing" analysis identifies hot cache lines. Linux `perf c2c` (cache-to-cache) tool shows cache-line-level contention patterns.

**Solutions**: Pad variables to cache-line boundaries (`__attribute__((aligned(64)))`), use per-CPU data (Linux `percpu` allocator), or restructure data to avoid colocating frequently-written variables.

## Cache-Line Bouncing

Cache-line bouncing is the runtime manifestation of false sharing. When two cores write to the same cache line, the MESI protocol forces the line into the **Modified** state on one core and **Invalid** on the other. Each write by Core 0:

1. Issues a RFO (Read-For-Ownership) request on the bus
2. Waits for Core 1 to write back and invalidate its copy
3. Core 1's next access misses, issues its own RFO
4. The line bounces back and forth

Each bounce costs ~40-100 ns (inter-socket via QPI/UPI: ~100-150 ns). At 100M writes/sec per core, this can saturate the interconnect fabric.

## Comparison

| Model | Store→Load | Load→Load | Load→Store | Store→Store | Barrier Cost |
|-------|-----------|-----------|------------|-------------|-------------|
| Sequential Consistency | No | No | No | No | Very high |
| x86-TSO | **Yes** | No | No | No | Low (MFENCE: ~20-40 cycles) |
| ARMv8 (default) | Yes | Yes | Yes | Yes | Medium (DMB: ~10-30 cycles) |
| RISC-V (RVWMO) | Yes | Yes | Yes | Yes | Medium (FENCE: ~10-30 cycles) |
| POWER | Yes | Yes | Yes | Yes | High (sync: ~50-200 cycles) |
| Acquire/Release pair | Synced | Synced | Synced | Synced | 1 barrier per side |

## Interview Questions

1. **"What can go wrong on x86 even though it's relatively strongly ordered?"** Answer hint: Store-to-load reordering (store buffer). A store on Core 0 and a load on Core 1 to different addresses can both see the old values. This requires a `MFENCE` or `LOCK` prefix to prevent. The classic pattern is a flag-setting store: the store to data might not be visible when the flag store becomes visible to other cores.

2. **"When do you need acquire/release vs. a full barrier?"** Answer hint: Acquire/release is sufficient for synchronizing a producer-consumer relationship (single flag variable communicating data readiness). A full barrier (`smp_mb()`) is needed when synchronizing multiple independent flag variables or implementing Dekker's algorithm. If you're publishing multiple data items protected by a single flag, acquire/release on the flag is enough.

3. **"How do you detect false sharing in production?"** Answer hint: `perf c2c record -a -- ./your_program` then `perf c2c report`. This shows which cache lines have the most cross-core invalidations. Look for cache lines with high `Remote HITM` (Hit-Modified) counts — each HITM is a cache-line bounce. VTune's "Memory Access" analysis provides similar data with GUI.

## References
- Lamport, L. "How to Make a Multiprocessor Computer That Correctly Executes Multiprocess Programs." IEEE Trans. Comp. 1979.
- Sewell et al. "x86-TSO: A Rigorous and Usable Programmer's Model for x86 Multiprocessors." CACM 2010.
- Maranget, L. et al. "A Formal Model of the Linux Kernel Memory Model." ESOP 2018.
- Adve & Gharachorloo. "Shared Memory Consistency Models: A Tutorial." IEEE Computer 1996.
