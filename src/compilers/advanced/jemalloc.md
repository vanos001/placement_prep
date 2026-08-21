# jemalloc

jemalloc is a general-purpose memory allocator, originally developed by Jason Evans for FreeBSD in 2005, and now used by Facebook, Redis, Meta's HHVM, and many high-performance systems. It's designed for low fragmentation, scalability on multi-core CPUs, and per-thread cache performance. This page covers the arena-based architecture, the size class system, and the production trade-offs vs. glibc's malloc and tcmalloc.

## Why a Custom Allocator?

The default `malloc` in glibc (ptmalloc) is general-purpose but has scaling issues:
- Single global heap lock (with thread-local caches to mitigate).
- Fragmentation can reach 20-30% on long-running workloads.
- Per-thread cache can be too small or too large.

jemalloc's design choices:
- Multiple "arenas" (default: 4× CPU count) — each thread is assigned to one arena, reducing contention.
- Thread-local caches ("tcache") — small allocations never touch the arena lock.
- Size class buckets — exact-size allocations, reducing fragmentation.
- Aggressive coalescing of free chunks.

## The Arena Architecture

```text
Process heap (managed by jemalloc)
   │
   ├── Arena 0 (assigned to threads 0, 4, 8, ...)
   │     ├── Tcache for thread 0
   │     ├── Tcache for thread 4
   │     └── ...
   │
   ├── Arena 1 (assigned to threads 1, 5, 9, ...)
   │     └── ...
   │
   ├── Arena 2 (assigned to threads 2, 6, 10, ...)
   │     └── ...
   │
   └── Arena 3 (assigned to threads 3, 7, 11, ...)
         └── ...
```

Each arena is independent: per-thread allocations within an arena don't contend with allocations in other arenas. The arena assignment is by thread ID hash, distributing threads evenly.

Trade-off: arenas can fragment memory because free chunks in one arena can't be used by another. jemalloc periodically (default every 10 seconds) does "decay" — moving unused pages back to the OS.

## Size Classes

jemalloc categorizes allocations by size:
- **Small**: 8 B to 14 KB. Bucketed into ~40 size classes (8, 16, 32, 48, ..., 14336). Each size class has its own pool.
- **Large**: 14 KB to 32 MB. Allocated from the arena's chunk pool, no per-size pool.
- **Huge**: > 32 MB. Allocated directly via mmap (one chunk per allocation).

```text
Small size classes (subset):
  8, 16, 32, 48, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, ...
  (each class is ~1.25× the previous)
```

A `malloc(15)` returns a 16-byte chunk (next size class up). A `malloc(33)` returns a 48-byte chunk. The "round up to size class" ensures the allocator never has to split chunks, which would fragment.

Trade-off: a 33-byte allocation wastes 15 bytes (the 48-byte chunk has 33 used + 15 unused). The wasted bytes are "internal fragmentation".

## The Tcache (Thread Cache)

Each thread has a tcache with a small pool of recently-freed chunks:

```text
Thread 0's tcache:
  bin_8B:    [free chunk, free chunk, free chunk]
  bin_16B:   [free chunk]
  bin_32B:   []
  bin_48B:   [free chunk, free chunk]
  ...

malloc(33) → look in tcache bin_48B → if free chunk, return it (no lock).
              If no free chunk, fall through to arena.
```

The tcache is lock-free for the thread that owns it. Only on tcache misses does the thread touch the arena's lock.

The tcache is bounded: if a bin has > N (configurable) free chunks, the extras are flushed back to the arena. This prevents tcache from holding too much memory.

## Extents and Pages

jemalloc's heap is organized into "extents" — large contiguous memory regions:
- Each extent is a multiple of the page size (typically 4 KB).
- Extents are tracked in a "radix tree" for fast lookup by address.
- When a chunk is freed, jemalloc checks if the adjacent extents are free and coalesces them.

Coalescing reduces external fragmentation (free chunks scattered across the heap). Without coalescing, two adjacent free 1 KB chunks could not satisfy a 2 KB allocation; with coalescing, they become one 2 KB chunk.

## Production Performance

Typical improvements from glibc to jemalloc:
- 10-30% less RSS (resident set size) on long-running workloads.
- 20-50% faster allocation/deallocation for small objects (tcache).
- Better multi-thread scaling (arenas).

For Redis specifically, jemalloc is the default allocator; using glibc instead increases RSS by ~30% under load.

## Usage

Linking jemalloc into a C/C++ program:

```bash
# Compile with jemalloc
gcc myapp.c -ljemalloc

# Or via LD_PRELOAD for unmodified binaries
LD_PRELOAD=/usr/lib/libjemalloc.so myapp
```

For Java applications, jemalloc can be used via JNI for native allocations (but Java's heap is managed by the JVM's GC, not jemalloc).

## Tuning

Environment variables (with `MALLOC_CONF=`):

```bash
# Set arena count to 8 (default is 4*ncpu)
MALLOC_CONF=narenas:8 myapp

# Disable tcache (small allocations go directly to arena)
MALLOC_CONF=tcache:false myapp

# Set decay time for unused pages (default 10s)
MALLOC_CONF=dirty_decay_ms:30000,muzzy_decay_ms:30000 myapp

# Print stats on exit
MALLOC_CONF=stats_print:true myapp
```

The `dirty_decay_ms` controls how long dirty pages (recently freed but not returned to OS) stay in the cache. Higher = better re-use, more RSS. Lower = less RSS, more mmap/munmap calls.

## Statistics

jemalloc's stats output (via `MALLOC_CONF=stats_print:true` or `mallctl` API):

```text
___ Begin jemalloc statistics ___
Version: "5.3.0-0-g54eaed44b0e7f...\""
Arenas: 32
Atoms: N0
Useful: true
Run quantum: 8
NBINS: 39
Run quantums: 1
"Last" size class: 14336
Muzzy decay_ms: 10000
Dirty decay_ms: 10000

___ Begin arena 0 stats ___
small: 1000000 allocs, 1000000 frees, 1000 rem
large: 1000 allocs, 1000 frees, 0 rem
huge: 0 allocs, 0 frees, 0 rem
```

This is invaluable for diagnosing fragmentation and tuning.

## Comparison to Alternatives

| Allocator | Default in | Strengths | Weaknesses |
|-----------|------------|-----------|------------|
| glibc (ptmalloc2) | Linux | Simple, well-tested | Fragmentation, contention |
| tcmalloc | Google's apps | Thread cache, low overhead | Larger RSS than jemalloc |
| jemalloc | FreeBSD, Facebook, Redis | Low fragmentation, arenas | More complex config |
| mimalloc | Microsoft | Fast, simple | Newer, less adoption |
| scudo | Android, Chrome | Security (quarantine) | Higher overhead |

For most Linux workloads, jemalloc is the recommended upgrade from glibc. For embedded/security-sensitive, scudo or mimalloc are options.

## Common Pitfalls

1. **Forgetting to set `MALLOC_CONF=stats_print:true` for debugging.** Without stats, you can't tell if fragmentation is the problem.

2. **Setting `narenas` too high.** More arenas = more fragmentation (each arena's free chunks can't be shared). Default (4*ncpu) is good.

3. **Forgetting that LD_PRELOAD doesn't affect statically-linked binaries.** Statically-linked Go binaries use their own allocator, not jemalloc.

4. **Confusing the "decay" with "free".** Dirty pages in tcache are not free; they're cached for fast re-use. Decay returns them to the OS only after the decay_ms timeout.

5. **Forgetting that huge allocations don't go through arenas.** A 1 GB malloc goes directly to mmap; the arena's stats don't include it.

6. **Using jemalloc with Java apps.** Java's heap is JVM-managed; jemalloc only affects native (JNI) allocations. Don't expect Java GC improvements from jemalloc.

## References

- Jason Evans, "[A Scalable Concurrent malloc Implementation for FreeBSD](https://people.freebsd.org/~jasone/jemalloc/bsdcan2006/jemalloc.pdf)" (BSDCan 2006)
- [jemalloc GitHub](https://github.com/jemalloc/jemalloc)
- [jemalloc documentation](https://jemalloc.net/jemalloc.html)
- [Redis with jemalloc](https://redis.io/docs/reference/internals/memory-allocator/) (Redis default)
- [jemalloc vs tcmalloc vs glibc benchmark](https://github.com/jemalloc/jemalloc/wiki/Testing)
- [mimalloc: Microsoft's competitor](https://github.com/microsoft/mimalloc)
- [tcmalloc: Google's allocator](https://github.com/gperftools/gperftools)
- [LWN: jemalloc internals (2015)](https://lwn.net/Articles/639024/)
