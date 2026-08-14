# Memory Profiling

Memory profiling identifies where and how a program allocates memory, finds leaks, and optimizes garbage collection. Memory issues often manifest as gradually increasing RSS, sudden OOM kills, or performance degradation from GC pressure.

## Memory Leak Detection

A memory leak occurs when allocated memory is never freed. In garbage-collected languages, leaks are usually **unintentional object retention** — objects that are still reachable via a reference, even though they're logically unused.

### Common Leak Patterns

| Pattern | Example | Fix |
|--------|---------|-----|
| **Static collections** | Adding to a `static Map` without removal | Use `WeakHashMap`, bound size, or explicit cleanup |
| **Unclosed resources** | Open streams, connections in `finally` block | Use try-with-resources / context managers |
| **Listener registration** | Registering callbacks without deregistering | Track registrations, cleanup on dispose |
| **Thread-local storage** | Per-thread caches that grow unbounded | Size-bound thread-locals or cleanup threads |
| **Cache without eviction** | In-memory LRU cache that's actually infinite | Use Caffeine/Guava with `maximumSize` |
| **Closure capture** | Lambda captures large object, held by long-lived callback | Capture only needed fields |

## Heap Profiling Tools

### Valgrind (C/C++)

Valgrind's **Memcheck** is the gold standard for unmanaged memory error detection:

```bash
$ valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./my_program

# Output excerpt:
# ==12345== 40 bytes in 1 blocks are definitely lost in loss record 1 of 1
# ==12345==    at 0x4C29F73: malloc (vg_replace_malloc.c:309)
# ==12345==    by 0x1086A8: create_node (tree.c:45)
# ==12345==    by 0x1086E2: insert (tree.c:67)
```

**Limitation**: 10-20× slowdown. Not suitable for production or performance-sensitive testing.

### AddressSanitizer (ASAN)

ASAN is a compiler-based sanitizer with **~2× overhead** — much faster than Valgrind:

```bash
# Compile with ASAN
$ gcc -fsanitize=address -g -O1 my_program.c -o my_program
$ ./my_program

# Common issues detected:
# - Heap buffer overflow
# - Use-after-free
# - Stack buffer overflow
# - Memory leaks (with -fsanitize=leak)
```

ASAN is the recommended default for C/C++ development. Google and Meta run ASAN-instrumented binaries in CI.

### Heaptrack (C/C++)

```bash
$ heaptrack ./my_program
$ heaptrack_print heaptrack.my_program.12345.gz

# Shows:
# - Total allocations, temporary allocations
## - Allocation hotspots (functions allocating the most)
# - Growth over time
```

### Java Heap Profiling

```bash
# Heap dump on OOM
$ java -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heap.hprof MyApp

# Trigger heap dump manually
$ jcmd <pid> GC.heap_dump /tmp/heap.hprof

# Analyze with Eclipse MAT or VisualVM
# Key metrics in MAT: 
#   - Dominator tree (which objects retain the most heap)
#   - Leak Suspects report (automatic analysis)
#   - Histogram (class-level allocation summary)
```

## GC Tuning

### Java (G1GC)

```bash
# Modern defaults (Java 17+):
# G1GC is the default, generally needs no tuning

# If you must tune:
$ java -XX:+UseG1GC \
       -XX:MaxGCPauseMillis=200 \
       -Xmx4g \
       -XX:G1HeapRegionSize=8m \
       MyApp

# Key tradeoff: MaxGCPauseMillis vs. throughput
# Smaller target pause → more frequent, smaller collections → lower throughput
```

### Go

Go's concurrent GC aims for sub-millisecond pause times. Key tuning:

```go
// GOGC controls heap growth before GC triggers (default 100 = double heap)
// Lower = more frequent GC, less memory. Higher = less frequent, more memory.
// GOGC=50 triggers GC when heap grows 50%

// For memory-sensitive services:
// GOGC=50  (more aggressive collection)

// For throughput-sensitive services:
// GOGC=200 (less frequent, more headroom)

// Set via environment:
// GOGC=50 ./my_server
```

### Python

CPython uses reference counting + cycle collector. No tuning knobs exist for the GC itself — the strategy is to **reduce allocations**:

```python
# Bad: creates many temporary strings
result = ''.join([str(x) for x in large_list])

# Good: use generator, pre-allocate
result = ','.join(map(str, large_list))

# For numeric work: use numpy (C-level allocations, no Python object overhead)
import numpy as np
arr = np.zeros(10_000_000, dtype=np.float32)  # ~40MB vs ~280MB Python list
```

## Cache Miss Analysis

Cache misses are often the hidden cost behind "mystery" CPU time. Use `perf` to detect:

```bash
$ perf stat -e cache-references,cache-misses,L1-dcache-load-misses,LLC-load-misses ./my_program

# Interpretation:
# L1-dcache-load-misses > 10%  → poor data locality, consider struct reorganization
# LLC-load-misses > 5%         → working set doesn't fit in L3, consider algorithm change
```

**Common fixes for cache misses:**
- **Structure-of-arrays vs. array-of-structures**: Group data by access pattern, not logical type
- **Padding**: Avoid false sharing between threads by padding struct fields to cache line boundaries (64 bytes)
- **Loop tiling**: Process data in cache-line-sized blocks
- **Prefetching**: Use `__builtin_prefetch` (GCC) or let hardware prefetcher work by accessing memory sequentially

## Interview Questions

1. **How do you detect a memory leak in a production Java service?**
2. **What's the difference between Valgrind and AddressSanitizer? When would you use each?**
3. **Explain how Go's garbage collector works and what GOGC controls.**
4. **A Python service's RSS grows by 1GB/day. How do you investigate?**
5. **What is false sharing? How would you detect and fix it?**
6. **How would you size the JVM heap for a container with 2GB memory limit?**
7. **Explain the difference between a memory leak in C and an unintentional retention in Java.**
8. **You see high LLC cache miss rates in `perf stat`. What does that mean and what would you do?**
