# Python Free-Threaded (3.13t) — No-GIL Python

## Overview

For 30 years CPython had a **Global Interpreter Lock (GIL)** — a mutex allowing only one thread to execute Python bytecode at a time. It simplified memory management (refcount protected by GIL) but bottlenecked multi-core. **PEP 703 — Making GIL Optional** introduces a **free-threaded build** (`3.13t`, `3.14t`) where GIL is disabled via `--disable-gil`, with thread-safe refcounts, per-object locking, and deferred reference counting.

This unlocks true multi-threaded parallelism for CPU-bound Python without multiprocessing IPC overhead.

> Related: [Python Overview](./README.md), [CPython Internals](./cpython-internals.md), [GIL](./gil.md), [AsyncIO](./asyncio.md), [Performance](./performance.md)

## PEP 703 & PEP 779 Timeline

| Phase | Version | Status | Single-thread overhead | Multi-thread speedup |
|-------|---------|--------|------------------------|----------------------|
| **Phase 1** | 3.13 (Oct 2024) | Experimental `--disable-gil` | ~40% slower single-thread (specializing adaptive interpreter disabled) | 2-8× for CPU-bound |
| **Phase 2** | 3.14 (Oct 2025) | Officially supported build `3.14t` per PEP 779 | **5-10% slower** (adaptive interpreter re-enabled thread-safe, mimalloc, JIT) | ~3-4× |
| **Phase 3** | 2027-2028 est | GIL off by default, runtime flag to re-enable | Near zero overhead goal | Default |
| **Phase 4** | 2029-2030 est | GIL fully removed | Regular build = free-threaded | — |

Free-threaded build tagged `t` — e.g., `python3.13t`, `python3.14t`.

## What Replaces GIL?

GIL protected refcounts. Without it:

- **Atomic refcounts**: per-object `ob_refcnt` becomes atomic (was plain int). `Py_INCREF`/`Py_DECREF` use atomic ops.
- **Per-object locking / biased locking**: for object header modifications
- **Deferred reference counting**: for some objects (e.g., immortals like `None`, `True`, small ints)
- **Mimalloc allocator**: bundled in 3.13/3.14 for better multi-thread scaling vs pymalloc.
- **JIT**: 3.13 adds JIT (copy-and-patch) — helps offset atomic overhead.

Result: single-threaded overhead in 3.13t ~40% due to atomic refcount on every operation + adaptive interpreter disabled. In 3.14t, optimizations + thread-safe specializing interpreter reduce to 5-10%.

## Performance Reality

### CPU-Bound Multi-Threaded — Big Win

FastAPI endpoint doing numeric work (no I/O):

- 3.13 regular: ~4 req/sec (GIL serialized)
- 3.13t no-GIL: ~32 req/sec — **8× increase** zero code changes, just `threading.Thread` instead of `multiprocessing`

Other examples:

- Image processing `Frame.iter_series().apply(func)`: single-thread 21.3ms (3.13t) vs 17.7ms (3.13), but with `apply_pool(use_threads=True, max_workers=4)` → 7.89ms — **2.7× speedup** despite single-thread overhead
- PageRank multi-threaded: threading fastest on 3.13t no-GIL, while multiprocessing has memory copy overhead
- Pure CPU data transforms: **2.2× with 4 threads on 3.13t**, **3.09× on 3.14t**, rising to **~4×** in 3.14

### I/O-Bound — No Difference

`asyncio` web scraping, DB queries — GIL released during network/database waits already, so free-threaded shows **negligible** change. Stick with asyncio on regular build.

### Single-Threaded — Tax

| Build | Overhead vs 3.12 regular |
|-------|--------------------------|
| 3.13t | ~40% slower (adaptive interpreter disabled) |
| 3.14t | 5-10% slower (specializing re-enabled thread-safe) |

C extension compatibility: if extension doesn't declare `Py_mod_gil_not_used`, interpreter re-enables GIL when loading it, silently defeating purpose. Check compatibility tracker.

## When to Use Free-Threaded

| Workload | Example | Impact | Worth? |
|----------|---------|--------|--------|
| CPU-bound multi-threaded | Image processing, data transforms, numeric loops | 2-8× faster | **Yes** — high value |
| AI/ML pipeline orchestration | Preprocess, postprocess, env logic, feature transforms | Significant Python-land gains | **Yes** |
| High-throughput web APIs | FastAPI + CPU-heavy endpoints | Up to 8× | Yes with profiling |
| I/O-bound async | asyncio scraping, DB | Negligible | Neutral |
| Single-threaded scripts | CLI, notebooks | 5-40% slower | **No** |
| Heavy C extensions unverified | NumPy, Pandas, OpenCV | May re-enable GIL | Verify |

## Code Example — Same Code, Threads Now Parallel

```python
# Python 3.13 regular vs 3.13t — no code change except using threads
import threading, time

def cpu_heavy(n):
    return sum(i*i for i in range(n))

# Regular 3.13 — threads serialized by GIL → ~4s for 4 threads 10M loops each
# 3.13t — threads truly parallel → ~1.2s with 4 cores
threads = []
start = time.time()
for _ in range(4):
    t = threading.Thread(target=cpu_heavy, args=(10_000_00,))
    t.start()
    threads.append(t)
for t in threads: t.join()
print(time.time() - start)
```

DataFrame example (StaticFrame):

```python
# 3.13t
import static_frame as sf, numpy as np
f = sf.Frame(np.arange(1_000_000).reshape(1000,1000))
func = lambda s: s.loc[s % 2 == 0].sum()
# Single threaded 21.3 ms
# Multi-threaded 7.89 ms with 4 workers — 2.7x
f.iter_series(axis=1).apply_pool(func, use_threads=True, max_workers=4)
```

## C Extension Story

PEP 703 adds slot `Py_mod_gil` — extension declares `Py_mod_gil_not_used` if thread-safe. If not set or absent, GIL re-enabled on import (pause threads + re-enable). Major libraries (NumPy 2.0+, Pandas, etc.) progressively declare.

Check via tracker and `python -c "import module; print(module.__gil__)"` (future).

## Migration Strategy

1. **Profile**: identify CPU-bound Python code currently using `multiprocessing` due to GIL.
2. **Test on 3.14t**: `pyenv install 3.14t` or `python3.14t -m venv venv-t`.
3. **Check extensions**: `pip install` + run with `-X gil=0`? Verify no silent GIL re-enable via `sys._is_gil_enabled()` (3.13t) or `python --disable-gil` build flag.
4. **Replace multiprocessing with threading**: where shared memory beneficial, avoid IPC copy.
5. **Monitor single-thread overhead**: if 5-10% acceptable for multi-thread gains, ship; else wait Phase 3.
6. **Subinterpreters alternative**: Python 3.12 introduced subinterpreters (PEP 684) — per-interpreter GIL, but data sharing not fully solved, slower than threads in most benchmarks.

## Interview Questions

**Q: What is GIL and why does free-threaded matter?**
GIL is mutex preventing parallel Python bytecode execution, simplifying refcount management. Free-threaded build (PEP 703) removes it via atomic refcounts, per-object locks, mimalloc, JIT, enabling true multi-threaded CPU-bound speedups 2-8× without multiprocessing IPC overhead.

**Q: Why 40% single-thread overhead in 3.13t but 5-10% in 3.14t?**
3.13t disabled specializing adaptive interpreter (which gives ~20-30% speedup) because it wasn't thread-safe, plus atomic refcount per operation. 3.14t makes specializing thread-safe and re-enables JIT, reducing overhead to 5-10%.

**Q: When would you NOT use free-threaded?**
Single-threaded scripts (5-10% slower no benefit), I/O-bound asyncio (GIL already released during I/O), heavy C extensions unverified (may re-enable GIL), production where stability > throughput until Phase 3.

**Q: How does reference counting work without GIL?**
Per-object atomic refcount + deferred RC for immortals. `Py_INCREF`/`Py_DECREF` use atomic ops, plus biased locking. mimalloc helps scalability.

## Cross-References

- [Python GIL](./gil.md) — GIL history, why it exists
- [CPython Internals](./cpython-internals.md) — refcount, GC
- [AsyncIO](./asyncio.md) — alternative for I/O-bound
- [Performance](./performance.md) — JIT, mimalloc, specialization

## References

- Liberating Performance with Immutable DataFrames in Free-Threaded Python: 21.3ms single vs 7.89ms 4 workers 2.7×, single-thread slower 21.3ms 3.13t vs 17.7ms 3.13, trade-offs [Towards Data Science]
- Python 3.13 Free-Threaded Mode What No-GIL Means: 4 req/s → 32 req/s 8× FastAPI CPU-bound, 40% single-thread tax 3.13t, 2.2× 4 threads 3.13t → 3.09× 3.14t, table workload type [Java Code Geeks]
- CodSpeed State of Python 3.13 Performance Free-Threading: free-threaded + JIT + mimalloc, PageRank threading fastest 3.13t no-GIL, overhead with GIL enabled due to adaptive interpreter disabled, subinterpreters alternative slower [CodSpeed]
- LWN CPython without GIL: PEP 703 --disable-gil, Py_mod_gil slot, pause threads re-enable GIL if extension not declaring not_used, GC refcount protected by GIL, atomic locking nightmare, 5-8% cost vs 3.12 [LWN]
- PEP 703 Free-Threaded Python When It Lands: Phase 1 3.13 experimental 40% overhead, Phase 2 3.14 officially supported 5-10% overhead ~4× speedup, Phase 3 2027-2028 GIL off by default, Phase 4 2029-2030 GIL removed, 15-20% memory growth [CodeGym]
