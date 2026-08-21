# mimalloc

mimalloc is a general-purpose memory allocator developed by Daan Leijen at Microsoft Research, first released in 2019. It's designed for performance, predictability, and simplicity. Compared to jemalloc (older, more mature) and tcmalloc (Google's), mimalloc emphasizes per-thread "heap" structures with deferred freeing, and uses fewer configuration knobs. This page covers the per-thread heap design, the deferred free mechanism, and the production trade-offs.

## Why mimalloc Exists

Modern allocators (jemalloc, tcmalloc) achieve good performance but have:
- **Complex configuration**: many tunables, hard to set correctly.
- **Idle thread issues**: a thread that allocates then exits leaves its tcache memory orphaned.
- **Long-running fragmentation**: under sustained allocation patterns, fragmentation grows.

mimalloc's design goals:
- Drop-in replacement for `malloc`/`free` (single shared library).
- Good performance out of the box (no tuning).
- Per-thread "heaps" that can be reclaimed when the thread exits.
- Predictable behavior (no random delays for compaction).

## The Per-Thread Heap

mimalloc's central abstraction is the "thread-local heap" (mi_heap_t):

```text
Process heap
   │
   ├── mi_heap_t for thread 0
   │     ├── pages of various size classes
   │     ├── free lists per size class
   │     └── ... (no lock for thread 0's allocations)
   │
   ├── mi_heap_t for thread 1
   │     └── ...
   │
   └── mi_heap_t for thread N
         └── ...
```

Each thread has its own heap. Allocations within a thread's heap are lock-free (the thread owns its heap). Only when a thread's heap is full (or for very large allocations) does it consult the global heap, which has a lock.

The difference from jemalloc: jemalloc uses arenas (a thread is assigned to one arena, but multiple threads share an arena). mimalloc gives each thread its own heap, eliminating arena contention entirely.

## Deferred Freeing

A subtle issue: thread T0 allocates an object, passes it to thread T1, T1 frees it. T1's heap doesn't own the object; freeing it in T1's heap would put it in the wrong place.

mimalloc's solution: **deferred free**. When T1 frees an object owned by T0's heap, the object is put on T1's "deferred free list". Later (when T1 does its own allocation or after a quiescent period), T1's deferred list is moved to T0's heap.

```text
T1.free(obj_owned_by_T0):
  T1's deferred_free_list.append(obj_owned_by_T0)

T1's next alloc:
  if T1's deferred_free_list is non-empty:
    move list to T0's free list (must acquire T0's lock briefly)
  return alloc from T1's own heap
```

The brief lock acquisition is amortized: each deferred list transfer handles many objects, so the per-object overhead is small.

## Size Classes

mimalloc uses ~60 size classes for small allocations:

```text
8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, ..., 16384
```

Each size class has its own page (a 64 KB chunk divided into chunks of that size). The page has a "free list" of available chunks.

Allocation flow:
1. Round up to next size class.
2. Look in current thread's heap for a page of that size.
3. If a page has free chunks, take one (lock-free).
4. If no page, allocate a new page from the OS (or reuse a freed page).

## Production Performance

mimalloc's claims vs. alternatives:

| Allocator | Throughput (small allocs) | RSS overhead | Fragmentation |
|-----------|--------------------------|---------------|----------------|
| glibc | 1× (baseline) | 1× (baseline) | High |
| tcmalloc | 1.3× | 0.9× | Low |
| jemalloc | 1.5× | 0.85× | Very low |
| mimalloc | 1.4× | 0.95× | Low |

mimalloc's throughput is competitive with jemalloc (slightly behind), and its RSS is competitive (slightly higher than jemalloc). The main advantage: no tuning required, and very predictable performance.

## Production Users

- **Rust (some distributions)**: mimalloc is an alternative global allocator for Rust programs.
- **Koka**: a Haskell-like functional language; mimalloc is the default allocator.
- **Microsoft products**: some internal Microsoft products (e.g., SQL Server) use mimalloc.
- **JavaScriptCore (Apple)**: has used mimalloc-inspired ideas.

mimalloc is less widely deployed than jemalloc but growing.

## Usage

Linking mimalloc:

```bash
# C/C++
gcc myapp.c -lmimalloc

# Or LD_PRELOAD
LD_PRELOAD=/usr/lib/libmimalloc.so myapp

# Rust
# Cargo.toml:
[dependencies]
mimalloc = { version = "0.1", default-features = false }

# main.rs:
use mimalloc::MiMalloc;
#[global_allocator]
static GLOBAL: MiMalloc = MiMalloc;
```

## Tuning

mimalloc has fewer tunables than jemalloc:

```bash
# Show stats on exit
MIMALLOC_SHOW_STATS=1 myapp

# Set purge policy (default: 5 sec delay)
MIMALLOC_PURGE_DELAY=10000 myapp

# Limit number of threads (default: unlimited)
MIMALLOC_NTHREADS=8 myapp
```

The simplicity is intentional: most workloads need no tuning.

## Comparison to jemalloc

| Aspect | jemalloc | mimalloc |
|--------|----------|----------|
| First release | 2005 | 2019 |
| Default in | FreeBSD, Redis | (none yet) |
| Configuration knobs | Many | Few |
| Per-thread isolation | Arenas (shared) | Heap (private) |
| Throughput | Higher | Slightly lower |
| RSS | Lower | Slightly higher |
| Predictability | Varies | High |
| Best for | Tuned production | Drop-in simplicity |

jemalloc is the better choice if you've tuned it for your workload. mimalloc is the better choice for new projects that want a fast allocator without tuning.

## Common Pitfalls

1. **Forgetting that LD_PRELOAD doesn't affect static binaries.** Statically-linked Rust or Go binaries need to be recompiled with mimalloc linked in.

2. **Expecting dramatic improvements over glibc.** The improvement is 10-30% on most workloads. Don't expect 2× speedups.

3. **Forgetting that mimalloc doesn't help with large allocations.** Allocations > 32 MB go through mmap directly; the allocator doesn't help.

4. **Forgetting that deferred free has latency.** Object freed in another thread isn't immediately available; it's available after the deferred transfer. For high-churn workloads, the deferred free list can grow.

5. **Forgetting that mimalloc uses more RSS than jemalloc.** The per-thread heaps hold onto pages longer than jemalloc's arenas. Plan memory accordingly.

6. **Forgetting that the deferred free list must be drained.** A thread that allocates a lot but doesn't free much (in its own heap) accumulates a large deferred free list. The thread should periodically drain it.

## References

- Daan Leijen, "[mimalloc: a free list allocator](https://www.microsoft.com/en-us/research/publication/mimalloc-free-list-allocator/)" (ISMM 2019)
- [mimalloc GitHub](https://github.com/microsoft/mimalloc)
- [mimalloc documentation](https://microsoft.github.io/mimalloc/)
- [Rust mimalloc crate](https://github.com/purpleprotocol/mimalloc_rust)
- [Comparison: mimalloc vs jemalloc vs tcmalloc](https://www.zivelife.com/alloc-comparison/)
- [LWN: mimalloc design (2020)](https://lwn.net/Articles/820133/)
