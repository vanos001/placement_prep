# Python GIL and asyncio Deep Dive

This page is the *implementation* view: what the GIL mutex actually
protects, the `gilstate` state machine in `Python/ceval_gil.c`, the no-GIL
build from PEP 703, the asyncio event loop's selector layer, the
coroutine/Task/Future trampoline, the `await` bytecode state machine, and a
side-by-side with the JavaScript event loop. Existing pages
([GIL](./gil.md), [asyncio](./asyncio.md), [free-threaded](./free-threaded.md),
[CPython internals](./cpython-internals.md)) cover the *what*; this one covers
the *how*.

## 1. The GIL — Why It Exists

### 1.1 Reference counting and C extension safety

The GIL protects two invariants, in priority order:

1. **`ob_refcnt` on every `PyObject` stays consistent.** CPython uses
   reference counting as its primary reclamation mechanism. `Py_INCREF` and
   `Py_DECREF` are *not* atomic in the regular build — they are plain
   integer increments. Without a mutex, two threads simultaneously doing
   `Py_INCREF` would race: load, add, store — a classic lost update that
   either leaks the object (refcnt too high) or frees it twice (refcnt too
   low, use-after-free).

2. **C extensions written before 3.13 are not thread-aware.** The C API
   returns borrowed references (`PyObject*` with no ownership transfer) all
   over the place. If two threads could mutate the same dict/list/object
   simultaneously, every C extension would need fine-grained internal
   locking — which the ecosystem never had. The GIL lets millions of lines
   of existing C extensions keep working unmodified.

The GIL is therefore not an accident of implementation; it is the *price*
CPython pays for using refcounting plus a vast C-API ecosystem. Garbage
collected runtimes without refcounting (JVM, V8, Go) do not need a GIL —
their GCs are designed for concurrent mutation.

### 1.2 The `gilstate` state machine — `Python/ceval_gil.c`

The GIL is not a single `pthread_mutex_t`. It is a struct
(`_gil_runtime_state`) holding:

```
struct _gil_runtime_state {
    _PyAtomicAddress  locked;         // 1 = GIL held, 0 = free
    _Py_TIMING_LOCK   mutex;          // protects the fields below
    struct _cond      cond;           // "GIL is free" cv
    struct _cond      switch_cond;    // waiters wait on this for handoff
    _Py_atomic_int    switch_enabled; // 1 if eval breaker honors switch
    unsigned long     switch_interval; // microseconds, default 5000 (5 ms)
    unsigned long     switch_number;  // how many times the GIL was taken
    PyThreadState    *last_holder;    // the tstate that last held the GIL
    /* ... */
};
```

The lifecycle of one GIL *handoff* (simplified from `take_gil` /
`drop_gil` in [ceval_gil.c][ceval-gil]):

```
   RUNNING goroutine...        eval breaker hit (every ~5 ms)
              │                              │
              ▼                              ▼
     ┌────────────────┐            ┌─────────────────────┐
     │ drop_gil(t)    │            │ take_gil(t')        │
     │  locked := 0   │◀──────────│  while (locked)     │
     │  cond.signal() │           │    cond.wait()      │
     └────────────────┘           │  locked := 1       │
              │                    └─────────────────────┘
              ▼                              │
   schedule next bytecode                    │
   in THIS thread (still)        t' now owns the GIL and resumes
                                its eval loop
```

The two interesting things here:

- **The eval breaker.** Every CPython eval-loop iteration checks a flag in
  the current tstate (`tstate->eval_breaker`). When another thread calls
  `take_gil` and finds the GIL held, it sets
  `gil->drop_request = 1` and signals. The *current* thread notices the
  breaker on the next bytecode and calls `drop_gil`. So preemption is
  cooperative at the bytecode granularity — a single `BINARY_OP` cannot be
  interrupted.
- **The switch interval.** `sys.setswitchinterval(0.005)` (5 ms default)
  sets `switch_interval`. After holding the GIL for that long, the holder
  sets the eval breaker itself and voluntarily drops. This is what makes
  `threading` fair: I/O-bound threads get the GIL back at most 5 ms after
  they wake up.

### 1.3 Per-interpreter GIL (PEP 684, Python 3.12+)

Since 3.12 each `PyInterpreterState` can have its *own* GIL. With
`_interpreters`/`interpreters` (PEP 734 in 3.14), you can spawn a
sub-interpreter whose threads do not contend with the main interpreter's
GIL. This is the halfway house to full free-threading: multiple GILs in
one process, but each interpreter is still internally serialized.

## 2. The Free-Threaded CPython — PEP 703

PEP 703 ([Making the GIL Optional in CPython][pep-703]) shipped as an
experimental build in 3.13 (`python3.13t`) and became officially supported
in 3.14 (`python3.14t`) per PEP 779. The mechanism replaces the single GIL
with five layered mechanisms:

1. **Atomic refcounts.** `ob_refcnt` widens to 64 bits and becomes a
   `_Py_atomic_int`. `Py_INCREF` becomes a relaxed atomic add;
   `Py_DECREF` on the path to zero becomes a CAS (compare-and-swap) so the
   final free happens exactly once.
2. **Biased locking.** Most objects are touched by only one thread — the
   one that allocated them. PEP 703 attaches a "bias" thread id to the
   object header; same-thread access is lock-free, cross-thread access
   triggers an expensive bias revocation.
3. **Deferred (immortal) refcounts.** A small set of "immortal" objects
   (`None`, `True`, `False`, small ints, interned strings, top-level code
   objects) get a sentinel refcount value
   (`_Py_IMMORTAL_REFCNT = UINT32_MAX/2`) and `Py_INCREF`/`Py_DECREF` are
   no-ops on them. This kills the dominant refcount traffic in hot loops.
4. **Per-object critical sections.** New C-API macros
   `Py_BEGIN_CRITICAL_SECTION(op)` / `Py_END_CRITICAL_SECTION(op)` provide
   per-object locking for dict/list/set mutation. Extension authors who
   relied on the GIL as a giant mutex must migrate to these.
5. **`mimalloc` and a thread-safe specializing interpreter.** mimalloc
   gives per-thread arenas, killing the global allocator lock. The
   specializing adaptive interpreter (3.11+) was disabled in 3.13t because
   on-stack bytecode rewrite was not thread-safe; 3.14t moves the
   specialization tables per-thread and re-enables it.

The cost: 3.13t is ~40 % slower single-threaded; 3.14t recovers to
~5–10 % slower. The benefit: 3–4× speedup on CPU-bound workloads with 4–8
threads. See the [free-threaded deep dive](./free-threaded.md) for
benchmark numbers.

## 3. The asyncio Event Loop

### 3.1 The selector layer

`asyncio` does not invent I/O multiplexing — it wraps the
[`selectors`][selectors] module, which is a thin facade over `epoll`
(Linux), `kqueue` (BSD/macOS), or `select` (fallback). The default event
loop on Linux is `_UnixSelectorEventLoop`, which constructs a
`selectors.EpollSelector` and stores it as `self._selector`.

```
                    asyncio.run(main())
                            │
                            ▼
        ┌──────────────────────────────────────────────┐
        │  BaseEventLoop                                │
        │  ┌──────────────┐    ┌──────────────────┐   │
        │  │ _selector    │    │ _ready (deque)   │   │
        │  │ (epoll fd)   │    │ [cb1, cb2, ...]  │   │
        │  └──────┬───────┘    └──────────────────┘   │
        │         │                        ▲          │
        │         │                        │          │
        │  ┌──────▼───────┐    ┌──────────────────┐   │
        │  │ _sched (heap)│    │ _scheduled        │   │
        │  │ timer entries │───▶ timer callbacks  │   │
        │  └──────────────┘    └──────────────────┘   │
        └──────────────────────────────────────────────┘
```

### 3.2 The `_run_once` loop

Each iteration of `loop._run_once()` ([asyncio/base_events.py][base-events])
does exactly four things:

```python
def _run_once(self):
    # 1. Move timers whose time has come from _scheduled (heap) -> _ready
    ntodo = len(self._ready)
    for _ in range(ntodo):
        handle = self._ready.popleft()
        # 2. Run the callback
        handle._run()
    # 3. Compute the next selector timeout from the earliest timer
    timeout = max(0, self._scheduled[0]._when - time.monotonic()) if ... else None
    # 4. Block in epoll_wait; for each ready fd, push its callback into _ready
    event_list = self._selector.select(timeout)
    self._process_event(event_list)
```

Two consequences:

- **Timers go through the heap `_scheduled`, never directly to `_ready`.**
  This is why `loop.call_later(0, f)` is not the same as `loop.call_soon(f)`
  — the former schedules a timer, the latter pushes straight to `_ready`
  and runs at the end of the current iteration.
- **`_ready` is drained in full before any new selector wait.** This is
  the asyncio equivalent of the JavaScript "microtask drain": callbacks
  queued during this iteration all run before control returns to the OS.

### 3.3 Coroutines, Tasks, Futures

A `coroutine` is a generator-like object produced by `async def`. It is
*a paused computation* — calling `coro.send(None)` runs it until the next
`await`, which returns whatever the awaitable yielded. A `Future` is a
state machine with three states: `PENDING`, `CANCELLED`, `FINISHED`. A
`Task` is a `Future` subclass that *drives* a coroutine:

```python
class Task(Future):
    def __step(self, exc=None):
        coro = self._coro
        try:
            if exc is None:
                result = coro.send(None)        # advance the coroutine
            else:
                result = coro.throw(type(exc), exc)
        except StopIteration as stop:
            self.set_result(stop.value)         # coroutine finished
        except CancelledError:
            self._fut_waiter = ...
        except Exception as err:
            self.set_exception(err)
        else:
            # The coroutine yielded a Future (or None). When that Future
            # completes, it schedules Task.__step again.
            blocking = getattr(result, "_asyncio_future_blocking", None)
            if blocking is not None:
                result.add_done_callback(self.__step)
                self._fut_waiter = result
```

This is the trampoline: the event loop does not "know" about coroutines —
it only knows about callbacks. The `Task` translates coroutine semantics
into callbacks. When you write `await fut`, the coroutine yields `fut`
back to `__step`; `__step` registers itself as `fut`'s done callback and
the loop returns to `_run_once`. When `fut` resolves (e.g., the socket has
data), the loop calls `fut.set_result(...)`, which fires `__step` again,
which calls `coro.send(...)`, which resumes the coroutine past the `await`.

## 4. The `await` State Machine

### 4.1 Bytecode — `GET_AWAITABLE` + `SEND`

In 3.11+ the bytecode for `await fut` is roughly:

```
LOAD_FAST    fut
GET_AWAITABLE           # ensures fut is awaitable; calls __await__ if needed
LOAD_CONST    None
SEND          resume     # like YIELD_VALUE, but with error propagation
RESUME         0
```

`GET_AWAITABLE` is the dispatch: if the object is a coroutine it is passed
through; if it is a `Future` or has `__await__`, that is called to obtain
an iterator; otherwise `TypeError`. `SEND` (3.11+, replacing the older
`YIELD_FROM`) sends a value or exception into the iterator. If the iterator
raises `StopIteration`, the `await` expression evaluates to its `.value`;
if it yields anything, that bubbles up to the *outer* coroutine's caller
(typically `Task.__step`).

### 4.2 Async generators (PEP 525)

`async def` + `yield` produces an *async generator* — `asynchronous
iterator` whose `__anext__` returns a coroutine. PEP 525 added the `STOPASYNCHRONOUS`
and `GETASYNCHRONOUS` bytecodes (now folded into `SEND`/`RESUME`) and the
`agen` C struct. Each `__anext__` call is a fresh coroutine that runs until
the next `yield` — driven by `async for`, which itself `await`s each
`__anext__()`. The subtle bit is finalization: a coroutine that yields
once and is abandoned leaks its frame. The `shutdown` of `asyncio` calls
`agen.aclose()` on every tracked async generator (via
`sys.set_asyncgen_hooks`), which schedules the final `athrow(GeneratorExit)`
into the generator's loop.

### 4.3 The cost of awaiting nothing

```python
async def busy():
    s = 0
    for i in range(1_000_000):
        s += i
    return s
```

Running this with `asyncio.run(busy())` is *slower* than running the
equivalent synchronous function — the `Task` trampoline, the eval breaker
checks, and the `loop._run_once` overhead are pure cost. asyncio is
strictly an I/O parallelism tool; it is a tax on CPU work, not a speedup.

## 5. Comparison to the JavaScript Event Loop

| Aspect | Python asyncio | JavaScript (V8) |
|--------|----------------|-----------------|
| Threading model | Single thread *per event loop*; multiple loops in multiple threads possible | Single thread *per isolate*; no in-process multi-loop |
| Multiplexing | `selectors` → `epoll`/`kqueue` | libuv → `epoll`/`kqueue`/IOCP |
| "Microtask" queue | `_ready` deque, drained every `_run_once` iteration | Microtask queue, drained after every macrotask |
| "Macrotask" queue | `_scheduled` heap + selector events | SetImmediate / timer phase / poll phase |
| Awaitable primitive | `Future` (callback-based state machine) | `Promise` (then-handlers chain) |
| Scheduling primitive | `loop.call_soon(cb)` | `queueMicrotask(cb)` / `Promise.resolve().then(cb)` |
| `await` lowering | `GET_AWAITABLE` + `SEND` (3.11+) | `Generator` + `async/await` syntax transform, runtime suspend via generators |
| Cancellation | `task.cancel()` sets a flag; `CancelledError` thrown at next `await` | `AbortController` — manual propagation, no throw |
| Traceback on rejection | Full Python traceback, attached to `task._exception` | Stack at the throw site, often lost if unhandled |

Two structural differences worth flagging:

- **Python lets you run several event loops in one process** (one per
  thread). V8 cannot — the JS event loop is per-isolate and the isolate is
  the unit of concurrency. This is why Python can `asyncio.run_in_executor`
  into a `ThreadPoolExecutor` while JS must reach for Worker threads (a
  separate isolate) for the same effect.
- **Cancellation is a thrown exception in Python.** `Task.cancel()` arranges
  for the next `await` to raise `CancelledError`. In JS, cancellation is a
  signal the awaited code must poll on — there is no exception injection
  into a suspended `await`. The Python model is more powerful (cancellation
  propagates through `try/finally` and context managers) and more dangerous
  (a poorly written `finally` can swallow cancellation).

## 6. Performance Characteristics

- **CPU-bound threading under the GIL.** With the regular build, 4
  CPU-bound threads on 4 cores run at ~1× wall-clock, not 4×. The 5 ms
  switch interval means each thread gets ~200 context switches/second.
- **I/O-bound threading under the GIL.** Threads release the GIL on
  blocking syscalls (`read`, `recv`, `time.sleep`, `select`), so an I/O
  workload with 100 threads can saturate a 100-Mbit/s link. This is the
  reason `threading` is fine for I/O and useless for compute.
- **asyncio throughput.** A single-threaded asyncio server typically tops
  out around 100k RPS for tiny payloads — limited by the eval breaker
  checks and the trampoline overhead, not by I/O. Uvicorn on a 16-core
  machine usually runs one worker per core and pins an asyncio loop to
  each, dodging the GIL the same way Node.js cluster does.
- **Free-threaded on CPU work.** On a synthetic SHA-256 hashing loop,
  3.14t with 8 threads hits ~4× the throughput of single-threaded 3.14 —
  sublinear due to atomic refcount contention but a real speedup. The same
  workload on regular 3.14 with 8 `threading.Thread`s is ~0.95× (slower
  than single-threaded, because of GIL contention overhead).

## References

- [PEP 703 — Making the GIL Optional in CPython][pep-703]
- [PEP 525 — Asynchronous Generators](https://peps.python.org/pep-0525/)
- [PEP 684 — A Per-Interpreter GIL](https://peps.python.org/pep-0684/)
- [CPython source — `Python/ceval_gil.c`][ceval-gil]
- [CPython source — `Modules/_asynciomodule.c` (Task driving)](https://github.com/python/cpython/blob/main/Modules/_asynciomodule.c)
- [Python asyncio documentation][asyncio-docs]
- [Brett Cannon — "How the heck does async/await work in Python 3.5?"](https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/)
- [Selectors module documentation][selectors]

[pep-703]: https://peps.python.org/pep-0703/
[ceval-gil]: https://github.com/python/cpython/blob/main/Python/ceval_gil.c
[base-events]: https://github.com/python/cpython/blob/main/Lib/asyncio/base_events.py
[asyncio-docs]: https://docs.python.org/3/library/asyncio.html
[selectors]: https://docs.python.org/3/library/selectors.html
