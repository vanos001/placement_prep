# "Single-threaded languages can't use multiple cores"

## Overview

"Node.js is single-threaded" and "the Python GIL means no parallelism" are
among the most repeated sentences in systems interviews, and both are
half-truths that harden, in weaker forms, into "these platforms cannot use
multiple cores, so serious parallel workloads need another language". The
reality is layered: the *language's* execution model is single-threaded
(JavaScript runs your code on one event loop; CPython serializes bytecode
across threads under the GIL), while the *platform* ships multiple
escape hatches — worker threads and process clusters in Node,
multiprocessing and GIL-releasing native code in Python, per-interpreter
GILs and a free-threaded build in recent CPython. This page states the
claim fairly, separates what is actually serialized from what merely
sounds serialized, works the counterexamples with numbers, and handles
the GIL's changing status carefully, including the free-threaded build's
phased rollout.

## The Claim, Stated Fairly

The strongest common form is: "Node.js and Python are single-threaded
runtimes, so a program written in them cannot exploit multiple cores;
CPU-bound work in these languages is a dead end." The claim deserves
fairness because both halves have genuine content. JavaScript *is*
single-threaded per execution context — one event loop runs your code,
and two statements of yours never run simultaneously. CPython *does*
serialize Python bytecode across threads with the Global Interpreter
Lock, so a four-thread pure-Python CPU loop is no faster than a
single-threaded one. Anyone who has tried `threading` for image
manipulation in Python and seen no speedup has direct evidence. The
claim under audit is the jump from "one interpreter/one loop is
single-threaded" to "the platform cannot parallelize" — a jump that
erases workers, processes, native extensions, and the GIL's own
evolution.

## Verdict

**False.** The correct scope of the truth is: *one* JavaScript event loop
and *one* CPython interpreter's bytecode execution are single-threaded —
not the language, the platform, or the deployment. Node.js exposes
`worker_threads`, a cluster of processes, native addons, and libuv's
threadpool; Python exposes `multiprocessing`, `ProcessPoolExecutor`,
subinterpreters with per-interpreter GILs (PEP 684, CPython 3.12),
GIL-releasing C extensions, and — following PEP 703's acceptance — an
experimental free-threaded build shipped in 3.13 with a phased plan
toward broader support. Computed counterexamples abound: a Node cluster
of 8 workers uses all 8 cores of a machine; NumPy's matrix multiply
saturates every core from inside "GIL'd" Python. What the claim gets
right is a real constraint on *one narrow path* — shared-memory threads
executing pure-Python bytecode — and that constraint is exactly what the
escape hatches route around.

## Why People Believe It

The kernel of truth is real and worth stating precisely, because the
slogan would be harmless if it stayed this precise. In CPython, the GIL
is a mutex that a thread must hold to execute Python bytecode, so
threads within one process cannot execute Python code in parallel —
this is by design, to protect reference counting's simplicity and speed.
In Node, the event loop is one thread by design, so callback code
written in JavaScript never races with other JavaScript code. Both
designs trade CPU parallelism *within one execution unit* for
predictability and implementation simplicity, and both produced
spectacular I/O-bound successes — which cemented the identity of the
platform with its most visible limitation.

Three props hold the belief up. First, the tutorials that taught the
runners also taught the slogan: "Node is single-threaded, therefore
fast for I/O" was the original marketing, and the second clause never
got the same billing. Second, the escape hatches are heterogeneous and
have rough edges — `multiprocessing` serializes arguments over pipes,
`worker_threads` need explicit `SharedArrayBuffer` sharing, C
extensions must opt in to releasing the GIL — so the easy experiment
(threads, the wrong tool) fails and the right tool requires reading.
Third, the GIL was genuinely immutable for decades; a belief formed in
2010 was accurate for fifteen years, and updates (PEP 684 in 3.12,
PEP 703's acceptance and the 3.13 experimental build) have outrun
memory.

What is lost is the layer distinction. "The language" (a specification),
"the implementation" (CPython), "the runtime's execution unit" (an
interpreter instance, an event loop), and "the process" are four
different things, and the cores are attached to the process. A claim
about cores is a claim about processes and threads, not about language
syntax — and it is refuted by anything that gets more cores doing the
same work.

## The Correct Formulation

| Platform | What is single-threaded | Escape hatches to multiple cores | Cost of the escape hatch |
|---|---|---|---|
| Node.js | The event loop; all your JS on one thread | `worker_threads` (shared `SharedArrayBuffer`), `child_process`/cluster (one process per core), native addons, libuv threadpool (4 threads by default) | Message-passing serialization or shared-memory discipline; pool saturation at 4 for `fs`/crypto |
| CPython (GIL build) | One interpreter's bytecode under the GIL | `multiprocessing`/`ProcessPoolExecutor`, subinterpreters (PEP 684, 3.12+), C/C++/Rust extensions releasing the GIL (NumPy/BLAS, hashlib, zlib) | Pickling overhead per call; native code must be written to release the lock |
| CPython (free-threaded) | Nothing — GIL removed in that build | Shared-memory threads across cores directly | Single-threaded overhead and extension compatibility during the phased rollout (PEP 703 plan) |
| JVM | Nothing — threads are OS threads | Plain threads, fork/join pools, parallel GC | Memory footprint per thread; synchronization is your job |
| Go | Nothing — M:N scheduler | Goroutines multiplexed onto `GOMAXPROCS` OS threads | Data races possible; you pay with discipline (and `-race`) |

The precise statement: parallelism is a property of how many execution
units run your work, and every mainstream "single-threaded" platform
provides a sanctioned way to add execution units. The interesting
engineering question is not "can it parallelize?" but "at what
granularity and cost?" — process granularity pays in serialization,
thread granularity pays in synchronization, native granularity pays in
boundary design, and the free-threaded build eventually moves the bill
from your architecture to the runtime.

## Where It Breaks

**Node using all the cores, computed.** Take an image-service that
resizes uploads, 100 ms of native decode/encode per image. Naive
in-handler processing caps throughput at ~10 requests/second on one
core no matter how many await you sprinkle. Two lines of remediation
change the ceiling: spawn `os.cpus()` workers via the `cluster` module
(≈ 8× throughput on an 8-core host, each worker an independent event
loop), or offload resize work to `worker_threads`/native addons. The
libuv threadpool explains a subtlety that trips even believers: `fs`
and crypto operations are already "parallel" up to 4, so heavy `pbkdf2`
load saturates a 4-thread pool while 8 cores idle — proof that the
runtime was never single-threaded, just selectively so.

**Python's cores are already there.** A pure-Python nested loop gains
nothing from threads — the GIL arithmetic holds. Now run the same
computation as `numpy` matrix multiply: BLAS dispatches to all cores
because the C/Fortran layer releases the GIL around its work, and a
single `matmul` call can occupy an entire 16-core machine. The
generalized rule: *the GIL serializes Python bytecode, not the
machine* — any extension that drops the lock around long C calls
unlocks parallelism without leaving Python. For code that must stay
pure-Python, `multiprocessing` with a `Pool` maps a 10-minute job onto
8 processes at ~8× speedup minus pickling costs — measurable, not
mythical.

**The GIL is moving, carefully.** The claim would have been true for
the one-narrow-path sense until recently, and the update is phased, not
instant. PEP 684 (CPython 3.12, 2023) gave *subinterpreters* their own
GILs; PEP 703 — accepted by the Steering Council — produced an
experimental free-threaded build in 3.13 (`python3.13t`, 2024), with
the release series continuing the plan toward official support and,
eventually, a default flip, while retaining the GIL build for
compatibility. The honest status sentence for an interview: "shared-memory
threads in the default CPython build remain GIL-serialized; a
free-threaded build exists and is on a multi-release path; extensions
and tooling are the adoption bottleneck." Check the current release
notes before quoting specifics — this is exactly the fact that decays.

**When it accidentally works.** The claim's regime is real because most
services are I/O-bound: a typical API spends its life waiting on
networks and databases, one core saturates around tens of thousands of
requests per second of *orchestration*, and the single-threaded model
is a feature — no data races on ordinary state, deterministic per-request
reasoning, and trivial horizontal scaling (`cluster`, per-core process
managers, or just more pods). Teams that scale by adding processes and
hosts never meet the ceiling, so "can't use multiple cores" stays
unfalsified in their experience. The claim fails precisely when the
workload is CPU-shaped (image/video, parsing, crypto, ML preprocessing)
and someone quotes the slogan instead of measuring — usually while the
fix is already shipped in the standard library.

## Practical Implications

- Diagnose the bottleneck before the language: profile first, because
  "Python can't parallelize" and "the database is the bottleneck" are
  checked with different tools and fixed with different code.
- Match the escape hatch to the sharing pattern: independent tasks →
  processes (`multiprocessing`, `cluster`); shared-memory-heavy tasks →
  worker threads with `SharedArrayBuffer`, or GIL-releasing native
  libraries; mostly-waiting tasks → event-loop concurrency (see the
  sibling page on async/await).
- Budget the boundary: process-based parallelism pays pickling costs
  per call; move *coarse* units of work across, not per-item calls.
- For native-heavy Python work, check whether the hot extension
  releases the GIL (NumPy, hashlib, zlib do) — it changes the design
  from multiprocessing to plain threads.
- In interviews, scope every sentence: "one event loop", "one
  interpreter instance", "the default build", "the process" — the
  precision is the answer.

## Interview Questions

### "Node is single-threaded." Make that sentence precise, then name the ways Node uses multiple cores.

Precise version: each Node.js process runs one event loop, and all
application JavaScript in that process executes on that single thread.
Node uses additional threads without your code racing: libuv's
threadpool (default 4) runs `fs`, DNS lookups, and some crypto; native
addons may spawn their own pools; and the platform offers
`worker_threads` (parallel JS with shared memory) and
`child_process`/`cluster` (one process per core). The slogan describes
the execution unit, not the runtime's resource use.

### What exactly does the GIL serialize, and what does it not?

It serializes execution of Python *bytecode* within one interpreter
process: only the lock holder runs Python code at any instant. It does
not serialize blocking I/O (the lock is released during waits), native
extensions that explicitly release it around long C work (which is why
NumPy and hashing scale across cores), or anything across processes.
That asymmetry is why threads help I/O-bound Python but not
pure-Python CPU loops.

### You have a pure-Python CPU-bound batch job taking 40 minutes. Give three designs with expected speedups and costs.

One: `ProcessPoolExecutor` with workers-per-core — roughly 8× on 8
cores, minus pickling overhead; coarse task units keep the tax small.
Two: rewrite the hot loop in NumPy/Cython/Rust-extension — speedups of
10–100× from both GIL release and vectorization, at rewrite cost.
Three: on a free-threaded CPython build, plain threads over the same
code — no rewrite, bounded by build maturity and extension support.
Mentioning that `threading` alone gains ~nothing (GIL) is the
discriminator that earns the point.

### How does Go's scheduler make "single-threaded-looking" code use all cores, and why doesn't CPython just do the same?

Go compiles to native code with an M:N scheduler: goroutines are
multiplexed onto `GOMAXPROCS` OS threads, with preemption at function
calls and cheap stacks, so blocking calls yield the thread. CPython
interpreter frames carry reference-counting state protected by one
global lock; removing that lock breaks the C-API contract thousands of
extensions rely on, which is why the fix is a parallel build and
per-interpreter GILs (PEP 684) rather than a flag. The contrast is
about runtime contracts and extension ecosystems, not ambition.

## Key Takeaways

- The truthful scope: one event loop and one GIL'd interpreter's
  bytecode are single-threaded; the platform, the process, and the
  machine are not.
- Node: `worker_threads`, `cluster`, native addons, and libuv's
  4-thread pool already touch multiple cores — the slogan survives
  because JS code itself never runs in parallel within one loop.
- Python: `multiprocessing`, GIL-releasing native extensions,
  subinterpreters (PEP 684), and the free-threaded build (PEP 703's
  phased rollout, experimental in 3.13) each unlock cores at a
  different price.
- The GIL serializes Python bytecode, not the machine — most real
  "Python parallelism" is native code dropping the lock.
- The claim accidentally works because I/O-bound services fill one
  core and scale out instead; it fails on CPU-shaped workloads, where
  the escape hatch is usually already in the standard library.

## Cross-References

- [Misconception: Async/Await Makes My Code Run in Parallel](./async-await-parallelism.md)
  — the concurrency-versus-parallelism vocabulary this page leans on
- [Misconception: Adding More Threads Always Improves Performance](./more-threads-faster.md)
  — what happens *after* you get your parallel execution units
- [Follow-up Tree: Process Lifecycle](../followup-tree/process-lifecycle.md)
  — the process-vs-thread escalation chain behind the escape hatches
- [Follow-up Tree: Mutex to Lock-Free](../followup-tree/mutex-to-lock-free.md)
  — what shared-memory parallelism costs once you have it
- [Concurrency: Python GIL](../../concurrency/python-gil.md) — the
  lock's mechanics, history, and release points in depth
- [Python Free-Threaded](../../languages/python/free-threaded.md) —
  the PEP 703 build and its trade-offs in detail
- [Node.js](../../languages/javascript/nodejs.md) — event loop,
  worker threads, and cluster scaling
- [Go Concurrency Deep](../../languages/go/concurrency-deep.md) and
  [Go Scheduler](../../languages/go/scheduler.md) — the M:N model
  that "just uses all cores"
- [Thread Models](../../os/threads/models.md) — the OS-level
  user/kernel thread taxonomy beneath all of the above

## References

- Python Software Foundation. *multiprocessing* and
  *concurrent.futures* documentation. Python 3.
  <https://docs.python.org/3/library/multiprocessing.html>
- PEP 684 — *A Per-Interpreter GIL* (CPython 3.12).
  <https://peps.python.org/pep-0684/>
- PEP 703 — *Making the Global Interpreter Lock Optional in CPython*
  (accepted; free-threaded build phases). <https://peps.python.org/pep-0703/>
- OpenJS Foundation. *Node.js API: worker_threads*, *cluster*, and the
  libuv threadpool documentation.
  <https://nodejs.org/api/worker_threads.html>
- Go Project. *Effective Go — Concurrency* and the runtime scheduler
  source documentation ("Scalable Go Scheduler Design Doc", 2012,
  cited by title). <https://go.dev/doc/effective_go>
