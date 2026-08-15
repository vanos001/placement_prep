# Python Free-Threaded (3.13t, 3.14t) — No-GIL Python

## Overview

For more than three decades CPython has been gated by a **Global Interpreter Lock (GIL)** — a single mutex that allows only one thread to execute Python bytecode at a time. The GIL made CPython's reference-counting memory model thread-safe without per-object locking, and it kept the C API simple, but it serialized CPU-bound Python threads on multi-core machines, forcing developers to reach for `multiprocessing` (with its IPC and pickling cost) or for native extensions like NumPy that release the GIL around heavy compute.

**PEP 703 — Making the GIL Optional in CPython** changes that. It introduces a **free-threaded build** of CPython — `python3.13t`, `python3.14t` — in which the GIL can be disabled at interpreter start. The build replaces the GIL with a set of finer-grained mechanisms: atomic reference counts, a biased-locking scheme for object headers, deferred reference counting for "immortal" objects, the `mimalloc` allocator, and a thread-safe specializing interpreter. **PEP 779** (accepted for 3.14, October 2025) promotes the free-threaded build from "experimental" to "officially supported".

The payoff is real multi-threaded parallelism for CPU-bound Python — without multiprocessing IPC, without rewriting in C, and without releasing the GIL by hand. The cost is a single-threaded overhead (around 40 % in 3.13t, 5–10 % in 3.14t) and a still-maturing C-extension ecosystem.

> Related: [Python Overview](./README.md), [CPython Internals](./cpython-internals.md), [GIL](./gil.md), [AsyncIO](./asyncio.md), [Performance](./performance.md), [Python Concurrency](../../concurrency/python-gil.md)

## PEP 703 & PEP 779 Timeline

| Phase | Version | Status | Single-thread overhead | Multi-thread speedup |
|-------|---------|--------|------------------------|----------------------|
| **Phase 1** | 3.13 (October 2024) | Experimental `--disable-gil` build, must be installed separately from regular 3.13 | ~40 % slower (specializing adaptive interpreter disabled) | 2–8× for CPU-bound |
| **Phase 2** | 3.14 (October 2025) | Officially supported build `3.14t` per PEP 779; free-threading is no longer "experimental" | **5–10 % slower** (specializing interpreter re-enabled thread-safely; JIT; mimalloc) | ~3–4× |
| **Phase 3** | 2027–2028 (estimated) | GIL off by default; runtime flag to re-enable for legacy extensions | Near-zero overhead goal | Default behavior |
| **Phase 4** | 2029–2030 (estimated) | GIL fully removed from the codebase | Regular build = free-threaded | — |

The free-threaded build is tagged with a `t` ABI suffix — `python3.13t`, `python3.14t`. The two builds (regular and `t`) can coexist on the same system, and pip picks the correct wheel based on the ABI tag (e.g., `cp314` vs `cp314t`). Wheels built for the regular interpreter are not ABI-compatible with `3.14t` and vice versa, so extension authors must publish both — most major projects (NumPy 2.1+, Pandas 2.2+, Pillow 11+) now do.

## What Replaces the GIL?

The GIL protected two things: the per-object reference count (`ob_refcnt`) and the global interpreter state (dict of interned strings, exception state, the eval-loop frame). Removing it requires replacing both.

- **Atomic reference counts.** `ob_refcnt` becomes a 64-bit atomic integer. `Py_INCREF` / `Py_DECREF` use relaxed atomic operations for the common case and an atomic compare-and-swap when the count drops toward zero. This is the single biggest source of single-thread overhead — every Python operation involves multiple refcount mutations, and atomics are 5–20× more expensive than plain loads on contended paths.
- **Biased locking.** Most objects are only ever touched by one thread (the one that created them). PEP 703 implements a biased-locking scheme: an object's first access from a thread "biases" the object to that thread; subsequent accesses by the same thread are lock-free. Contention from a second thread triggers a slow-path bias revocation. This brings the common case close to GIL-era performance.
- **Deferred reference counting.** Some objects are so common that even atomic refcount ops dominate. PEP 703 marks a small set of "immortal" objects (`None`, `True`, `False`, small integers, interned strings, top-level code objects) whose refcount is set to a sentinel "immortal" value and never touched — `Py_INCREF` and `Py_DECREF` are no-ops on them. This eliminates the dominant refcount traffic in tight loops.
- **Thread-safe specializing interpreter.** CPython 3.11+ has a specializing adaptive interpreter that observes runtime types and rewrites bytecode in place to specialized fast paths (e.g., `LOAD_ATTR` for attribute access becomes a cached slot lookup). The 3.13t build had to disable this because the on-stack replacement was not thread-safe; 3.14t makes the specialization tables per-thread and re-enables it, recovering most of the lost performance.
- **`mimalloc` allocator.** Bundled in 3.13/3.14, mimalloc replaces `pymalloc` for non-object allocations and provides per-thread arenas, avoiding the global allocator lock that the GIL used to hide.
- **Per-object critical sections.** New C-API macros `Py_BEGIN_CRITICAL_SECTION(op)` and `Py_END_CRITICAL_SECTION(op)` provide per-object locking for mutable operations (dict insertion, list append, set mutation) that previously relied on the GIL. This is the replacement pattern that extension authors must adopt.
- **JIT (3.13+).** The copy-and-patch JIT, also from PEP 744, helps offset atomic overhead by generating native code for hot loops. The JIT is independent of free-threading but the two features compound.

The net effect: single-thread overhead in 3.13t is ~40 % (atomics + disabled specialization), but 3.14t recovers to 5–10 % by re-enabling specialization thread-safely and tuning the atomic operations.

## Performance Reality

### CPU-Bound Multi-Threaded — The Big Win

A FastAPI endpoint doing numeric work (no I/O):

- CPython 3.13 regular: ~4 req/s — the GIL serializes the four worker threads, so adding threads does not add throughput.
- CPython 3.13t free-threaded: ~32 req/s — an 8× increase with **zero code changes** beyond using `threading.Thread` instead of `multiprocessing.Process`.

Other representative measurements from public benchmarks:

- **StaticFrame image processing** (`Frame.iter_series().apply(func)` over a 1 000 × 1 000 array): single-thread 21.3 ms on 3.13t vs 17.7 ms on 3.13 (a ~20 % single-thread tax), but `apply_pool(use_threads=True, max_workers=4)` drops to 7.89 ms — a 2.7× speedup that beats the single-threaded baseline.
- **PageRank multi-threaded**: threading is fastest on 3.13t no-GIL, while multiprocessing pays a one-time memory copy cost per worker that dominates at smaller graph sizes.
- **Pure CPU data transforms**: 2.2× with 4 threads on 3.13t, 3.09× on 3.14t, rising toward ~4× in 3.14 as the specialization paths mature.

### I/O-Bound — No Difference

`asyncio` web scraping, database queries, HTTP client fanout — the GIL is already released around `socket.read`, `socket.write`, and most `select`-based waits, so free-threaded shows **negligible** change. If your workload is 99 % I/O wait, the GIL was never your bottleneck; keep using `asyncio` on the regular build and save the free-threaded build for the CPU-bound parts of your pipeline.

### Single-Threaded — The Tax

| Build | Overhead vs 3.12 regular | Reason |
|-------|--------------------------|--------|
| 3.13t | ~40 % slower | Adaptive specializing interpreter disabled; atomic refcounts on every operation |
| 3.14t | 5–10 % slower | Specializing re-enabled thread-safely; JIT; mimalloc; immortal-object fast path |

For purely single-threaded scripts (CLI tools, notebooks, batch jobs that don't parallelize), the free-threaded build is strictly slower — use the regular build. The two coexist on the same machine; `python3.14` and `python3.14t` are separate executables with separate site-packages.

## C Extension Compatibility

A C extension must explicitly declare that it is thread-safe. PEP 703 adds the `Py_mod_gil` module slot — an extension that has been audited and found thread-safe sets it to `Py_mod_gil_not_used`. If a loaded module does **not** set this slot (or sets it to `Py_mod_gil`), the interpreter pauses all running threads, re-enables the GIL, and emits a warning. This silent fallback is the most common migration pitfall: you install `3.14t`, run your code, and see only a 5 % improvement because one of your dependencies forced the GIL back on.

Check the current state at runtime:

```python
import sys
print(sys._is_gil_enabled())   # False on 3.14t with all extensions thread-safe
```

Major libraries with verified free-threaded wheels (as of late 2025):

| Library | Free-threaded support | Notes |
|---------|----------------------|-------|
| NumPy | ✅ 2.1+ | Wheels for cp313t, cp314t |
| Pandas | ✅ 2.2+ | NumPy-backed paths thread-safe |
| Pillow | ✅ 11.0+ | Image operations release per-pixel locks |
| PyTorch | ✅ 2.4+ (experimental) | Torch dispatch is GIL-free; some custom ops still pin |
| Pillow / scikit-image | ⚠️ Partial | C-extensions still being audited |
| Cython modules | ⚠️ Per-module | Must add `# cython: freethreading=True` and recompile |
| cffi | ✅ | Foreign function calls already release the GIL |

For Cython extensions, add the directive `# cython: freethreading=True` at the top of each `.pyx` file and rebuild against `3.14t` headers. The Cython compiler will emit the `Py_mod_gil_not_used` slot if the module declares no shared mutable state.

## When to Use Free-Threaded

| Workload | Example | Impact | Worth it? |
|----------|---------|--------|-----------|
| CPU-bound multi-threaded | Image processing, data transforms, numeric loops | 2–8× faster | **Yes** — high value |
| AI/ML pipeline orchestration | Preprocess, postprocess, env logic, feature transforms | Significant Python-land gains | **Yes** |
| High-throughput web APIs with CPU-heavy endpoints | FastAPI + numeric compute | Up to 8× | Yes, with profiling |
| I/O-bound async | asyncio scraping, DB | Negligible | Neutral |
| Single-threaded scripts | CLI, notebooks | 5–40 % slower | **No** |
| Heavy unverified C extensions | Some legacy OpenCV builds, old Fortran wrappers | May silently re-enable GIL | Verify first |

## Code Examples — Same Code, Threads Now Parallel

```python
# Python 3.13 regular vs 3.13t — no code change except using threads
import threading, time

def cpu_heavy(n):
    return sum(i * i for i in range(n))

# Regular 3.13 — threads serialized by GIL → ~4 s for 4 threads × 1M loops each
# 3.13t — threads truly parallel → ~1.2 s with 4 cores
threads = []
start = time.perf_counter()
for _ in range(4):
    t = threading.Thread(target=cpu_heavy, args=(1_000_000,))
    t.start()
    threads.append(t)
for t in threads:
    t.join()
print(time.perf_counter() - start)
```

DataFrame example using StaticFrame:

```python
import static_frame as sf
import numpy as np

f = sf.Frame(np.arange(1_000_000).reshape(1000, 1000))
func = lambda s: s.loc[s % 2 == 0].sum()

# Single-threaded: 21.3 ms on 3.13t
# Multi-threaded: 7.89 ms with 4 workers — 2.7× speedup
f.iter_series(axis=1).apply_pool(func, use_threads=True, max_workers=4)
```

Checking that the GIL is actually off:

```python
import sys
if not hasattr(sys, "_is_gil_enabled"):
    print("Not a free-threaded build")
elif sys._is_gil_enabled():
    print("WARNING: GIL is enabled — an extension likely forced it back on")
    # On 3.14t you can list loaded modules to find the offender
    import importlib.metadata as md
    for dist in md.distributions():
        print(dist.metadata["Name"])
else:
    print("Free-threaded — true parallelism is active")
```

Forcing the GIL off explicitly (3.14t only):

```bash
# Default in 3.14t: GIL off unless an extension forces it on
python3.14t -X gil=0 script.py

# Force GIL on (e.g., for debugging a thread-unsafe extension)
python3.14t -X gil=1 script.py
```

## Migration Strategy

1. **Profile.** Identify CPU-bound Python code currently using `multiprocessing` because of the GIL. `py-spy record -o profile.svg --pid <pid>` or `cProfile` will show hot Python loops.
2. **Install 3.14t.** `pyenv install 3.14t` or your distro's `python3.14t` package. Create a separate venv: `python3.14t -m venv venv-t`.
3. **Audit extensions.** Install your dependencies and run `python -c "import sys; print(sys._is_gil_enabled())"` after each import. Any module that flips the flag back to `True` is the offender — check the free-threading compatibility wheel tracker on pyfreeframethreading.github.io.
4. **Replace `multiprocessing` with `threading`.** Where shared memory is beneficial (large NumPy arrays, model weights) and the workload is CPU-bound, `ThreadPoolExecutor` now wins over `ProcessPoolExecutor` because it avoids pickling and IPC.
5. **Watch single-thread overhead.** If the 5–10 % tax on serial code is acceptable for the multi-thread gain, ship. If not, keep two deployments: a `3.14` service for single-threaded endpoints and a `3.14t` service for parallel workers.
6. **Consider subinterpreters as a fallback.** Python 3.12 introduced per-interpreter GILs via PEP 684. Subinterpreters give some parallelism with stronger isolation (no shared mutable state), but data sharing between interpreters is still limited, and in most benchmarks they are slower than free-threaded. They are useful for embedding Python inside a larger application (e.g., a multi-tenant plugin host), not for replacing `multiprocessing`.
7. **Update C extensions you own.** Add `Py_mod_gil_not_used` to the module definition, replace raw `ob_refcnt` accesses with `Py_INCREF` / `Py_DECREF` (now atomic), and replace GIL-protected critical sections with `Py_BEGIN_CRITICAL_SECTION(op)` / `Py_END_CRITICAL_SECTION(op)`.

## Internal Implementation Notes

- **`ob_refcnt` layout**: 64-bit atomic on 64-bit builds (was 32-bit `Py_ssize_t`). Atomic operations use relaxed memory ordering for the common inc/dec paths; only the compare-and-swap on drop-to-zero needs acquire/release semantics. This keeps the fast path cheap.
- **Biased lock word**: a single 64-bit word in the object header encodes either "unlocked", "biased to thread T", or "thin-locked by thread T". Bias revocation is a stop-the-world event that walks thread stacks to find biased objects and unbiases them — rare in practice.
- **Immortal refcount**: the magic value `UINT32_MAX` (or `_Py_IMMORTAL_REFCNT` on 64-bit) marks an object as immortal. `Py_INCREF` checks for this value and skips the atomic op. The set of immortal objects is fixed at startup: `None`, `True`, `False`, `Ellipsis`, `NotImplemented`, small ints `[-5, 256]`, interned strings in the startup set, and code objects for the standard library.
- **Dict thread safety**: a dict's `ma_keys` and `ma_values` arrays are immutable once published; mutation builds a new array and swaps it in atomically. Readers see either the old or new version, never a torn state. This is the same pattern as `java.util.concurrent.ConcurrentHashMap`'s bucket array swap.
- **Thread state**: `PyThreadState` is per-thread (it always was), but the global `interpreter` struct now has per-thread `tstate_head` chains instead of a single global list, and the eval frame is thread-local.

## Comparison With Other Languages

| Aspect | CPython free-threaded | Java (Loom) | Go (goroutines) | Ruby (3.x Ractor + M:N) |
|--------|----------------------|-------------|-----------------|-------------------------|
| Parallelism | True multi-threaded (no GIL) | Always true multi-threaded | Always true multi-threaded | True multi-threaded via Ractors |
| Concurrency primitive | `threading.Thread` | Virtual threads | Goroutines | `Ractor.new` |
| Memory model | Sequentially consistent for atomics; C-API critical sections for mutables | JMM (happens-before) | Go memory model (happens-before) | Per-Ractor heap, no shared mutable |
| C-API impact | Atomic refcounts, `Py_BEGIN_CRITICAL_SECTION` | None — JMM unchanged | n/a (no shared C API) | n/a |
| Migration cost | High (extension audit) | Low (drop-in `ExecutorService`) | n/a (greenfield) | Medium (must isolate) |

Free-threading's distinctive cost is the C-extension ecosystem — Java and Go never had a GIL to remove, so they did not have to convince every native library to declare thread-safety. Python's free-threading adoption rate is therefore bounded by the rate at which extension authors publish `Py_mod_gil_not_used`.

## Interview Questions

**Q: What is the GIL and why does free-threaded matter?**
The GIL is a single mutex preventing parallel Python bytecode execution across threads; it simplified CPython's reference-counting memory model by serializing all refcount mutations. Free-threaded (PEP 703) replaces it with atomic reference counts, a biased-locking scheme for object headers, deferred reference counting for immortal objects, the mimalloc allocator, and per-object critical sections in the C API. The payoff is true multi-threaded CPU-bound speedups of 2–8× without multiprocessing IPC overhead; the cost is a single-threaded tax (40 % in 3.13t, 5–10 % in 3.14t) and a C-extension ecosystem that must declare thread-safety.

**Q: Why is 3.13t ~40 % slower single-threaded but 3.14t only 5–10 %?**
3.13t disabled the specializing adaptive interpreter (which gives ~20–30 % speedup) because its on-stack bytecode rewriting was not thread-safe, on top of paying the atomic-refcount cost on every operation. 3.14t makes the specialization tables per-thread and re-enables the specializing interpreter, recovers the JIT, and uses `mimalloc` for per-thread allocation arenas. The remaining 5–10 % is the irreducible cost of atomics on the refcount hot path.

**Q: When would you NOT use free-threaded?**
Purely single-threaded scripts (5–10 % slower for no benefit), I/O-bound `asyncio` services (the GIL is already released during I/O waits, so the change is negligible), production deployments that depend on a C extension that has not yet declared `Py_mod_gil_not_used` (the GIL silently re-enables on import), and stability-critical services where the 3.14t maturity level is insufficient. Subinterpreters are an alternative for embedding use cases but are slower for general-purpose parallelism.

**Q: How does reference counting work without the GIL?**
Per-object `ob_refcnt` becomes a 64-bit atomic. `Py_INCREF` / `Py_DECREF` use relaxed atomic operations for the common case and an atomic compare-and-swap when the count approaches zero. Immortal objects (those marked with the sentinel `_Py_IMMORTAL_REFCNT` value) skip the atomic operations entirely. Biased locking handles object-header mutations: the first thread to access an object "biases" it; subsequent accesses by the same thread are lock-free; contention from a second thread triggers a stop-the-world bias revocation.

**Q: What is `Py_mod_gil` and why does it matter?**
It is a module-definition slot added by PEP 703. An extension sets it to `Py_mod_gil_not_used` to declare that it is thread-safe and does not need the GIL. If a loaded module does not set this slot, the interpreter pauses all running threads, re-enables the GIL, and emits a warning. This is the mechanism that lets the runtime dynamically fall back to GIL-on behavior when an unported extension is loaded — but it is also the silent failure mode where you install `3.14t` and see no speedup because one dependency forced the GIL back on.

**Q: How do you check whether the GIL is actually off at runtime?**
`sys._is_gil_enabled()` returns `False` on a free-threaded build with no extensions forcing the GIL on, and `True` otherwise. Run it after every import during migration to identify offenders. The `python -X gil=0` flag (3.14t) forces the GIL off; if an extension then tries to force it on, the interpreter raises a `RuntimeError` instead of silently enabling it — useful for catching undocumented dependencies.

**Q: Why are immortal objects needed?**
Without immortal objects, every `LOAD_CONST None` or `LOAD_SMALL_INT` would pay an atomic refcount inc/dec — and `None` is touched on virtually every Python function call. Marking `None`, `True`, `False`, `Ellipsis`, `NotImplemented`, small integers, and key interned strings as immortal makes their refcounts untouchable, so the inc/dec ops become no-ops. This eliminates the dominant refcount traffic in real workloads and is a large part of why 3.14t's overhead is 5–10 % rather than 30 %.

## Cross-References

- [Python GIL](./gil.md) — full GIL history and rationale
- [CPython Internals](./cpython-internals.md) — refcounting, GC, frame execution
- [AsyncIO](./asyncio.md) — alternative for I/O-bound workloads
- [Performance](./performance.md) — JIT, mimalloc, specializing interpreter
- [Python Concurrency](../../concurrency/python-gil.md)
- [Memory Model](../../concurrency/memory-model.md) — happens-before applies once the GIL is gone

## References

- PEP 703 — Making the GIL Optional in CPython (Sam Gross et al.) — https://peps.python.org/pep-0703/
- PEP 779 — The Python 3.14 Free-Threading Support Status (2025) — https://peps.python.org/pep-0779/
- PEP 683 — Immortal Objects with a Static Reference Count — https://peps.python.org/pep-0683/
- PEP 684 — A Per-Interpreter GIL — https://peps.python.org/pep-0684/
- PEP 744 — JIT Compilation (Copy-and-Patch) — https://peps.python.org/pep-0744/
- Python Free-Threading Compatibility Tracker — https://py-free-threading.github.io/tracking/
- Python Software Foundation blog — Free-Threading in Python 3.14 — https://blog.python.org/2025/10/python-3140-released.html
- Sam Gross — "Facebook: A no-GIL Python" (PyCon 2023 keynote) — design rationale for atomic refcounts, biased locking, deferred RC
