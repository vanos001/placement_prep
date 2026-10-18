# "async/await makes my code run in parallel"

## Overview

`async/await` is the most widely adopted concurrency syntax of the last
decade, and the sentence "now it runs in parallel" is how most developers
first describe what it did for them. What actually happened is almost always
something narrower and, for the workloads involved, more useful: the runtime
kept a single thread busy by interleaving the *waiting* portions of many
tasks, so idle time that used to serialize work no longer did. That is I/O
concurrency on an event loop, not parallelism, and the difference is not
pedantry — it predicts exactly which programs `async/await` will speed up
(I/O-bound ones) and which it will not (CPU-bound ones), and it explains why
an "asyncified" endpoint can still peg one core at 100% while the other
seven sit idle. This page states the claim fairly, gives the correct
vocabulary (concurrency, parallelism, offloading), and works through
counterexamples in JavaScript and Python whose numbers actually come out.

## The Claim, Stated Fairly

The strongest common form of the claim is: "I converted my callbacks to
`async/await` and the work now happens simultaneously — `async/await` makes
my code run in parallel." The claim deserves fairness because the experience
behind it is real and reproducible. A developer who converts four sequential
HTTP calls into four awaited tasks typically watches the wall-clock time drop
from roughly 400 ms to roughly 100 ms, which looks exactly like parallelism
from the outside. The kernel of truth is that multiple operations genuinely
are *in flight* at the same time: sockets are open, requests are unacked,
and the kernel is moving bytes concurrently. What is contested is not the
speedup but the mechanism attributed to it — whether `async/await` itself is
what executes work simultaneously, and on what hardware.

## Verdict

**False.** `async/await` is a syntax for *concurrency* — structuring a
program so many operations can be in flight — not for *parallelism*, which
requires multiple execution units running instructions at the same instant.
In JavaScript every `async` function's code runs on the single main thread;
in Python `asyncio` tasks all share one thread and the GIL besides. The
canonical counterexample: four CPU-bound 50 ms transforms awaited together
finish in ~200 ms, not ~50 ms, on one saturated core. The honest refinement
is that some runtimes (C#'s default scheduler, Rust's Tokio with its
multi-threaded executor) *schedule* continuations onto a thread pool, so
`async/await` there is a gateway to parallelism — but the parallelism comes
from the pool of threads, never from the keywords.

## Why People Believe It

The kernel of truth is the measured speedup on I/O-bound work, and it is
reliable enough to build a career on. Most backend tasks are dominated by
waiting: a request handler spends 95% of its life waiting on the database,
the cache, or an upstream API. Interleaving those waits turns N sequential
round-trips into roughly one round-trip of latency, and the numbers really
do work out — four 100 ms calls awaited together complete in about 100 ms
plus a few scheduling overheads. When the metric improves five-fold the same
week the keywords arrived, attributing the win to "parallelism" is the most
natural available story.

Three further props hold the belief up. First, the syntax *looks* like
threading: `await` reads like "start this and come back later", and
`Promise.all` reads like a thread join, so the mental model imports
threading semantics that were never promised. Second, the ecosystems blur
the vocabulary: Node's documentation advertises that the event loop enables
"non-blocking" operation, C# documents tasks as potentially running
"concurrently", and marketing pages routinely say "parallel" for all of it.
Third, the failure mode is silent: when CPU work fails to parallelize,
nothing crashes — the request is just slow, and slowness has a dozen more
popular explanations than "your concurrency construct has one thread".

What is lost in compression is the distinction between *in flight* and
*executing*. Concurrency is a property of a program's structure — multiple
logical operations whose waits may overlap. Parallelism is a property of the
hardware budget — multiple cores actually executing instructions during the
same interval. `async/await` delivers the first unconditionally and the
second not at all, except by delegating to something else that does.

## The Correct Formulation

| Concept | What it is | `async/await`'s role | JavaScript example |
|---|---|---|---|
| Concurrency | Many operations in flight; waits overlap | The construct's actual job | 4 awaited fetches overlap their network waits |
| Parallelism | Many instructions executing simultaneously | Not provided by the keywords | 4 `JSON.parse` calls still serialize on one thread |
| Offloading | Giving CPU work to another execution unit | Available via separate APIs | `worker_threads`, libuv's threadpool, `run_in_executor` |
| Blocking the loop | One task's CPU work stalls every other task | The characteristic failure | A 50 ms parse delays all timers and I/O callbacks |

The precise statement: `async/await` lets one thread interleave the *idle*
segments of many tasks; it executes the *busy* segments of those tasks
exactly as serially as plain code. A useful accounting rule is that total
CPU work is unchanged by `await` — only the overlap of waits changes. If a
handler spends 5 ms of CPU and 95 ms waiting, awaiting ten of them costs
about 50 ms of CPU spread across ~95–105 ms of wall clock. If each handler
spends 95 ms of CPU and 5 ms waiting, ten of them cost about 950 ms of wall
clock no matter how the `await`s are arranged, because there is only one
thread to do the executing.

## Where It Breaks

**The CPU-bound batch job.** Take the realistic Node.js case: four image
transforms of 50 ms each. Sequential `await t1(); await t2(); await t3();
await t4();` finishes in ~200 ms. The "obvious fix" `await
Promise.all([t1(), t2(), t3(), t4()])` also finishes in ~200 ms, because
each function's synchronous body runs to completion on the main thread
before any other task can start — `Promise.all` overlaps only the waits,
and there are no waits to overlap. Worse, during each 50 ms burst every
other connection on the server stalls: timers fire late, socket reads sit
unprocessed, and p99 latency climbs even though average latency looks fine.
The claim "runs in parallel" fails in the exact scenario a developer would
use to test it.

**Python adds the GIL on top.** The same experiment in `asyncio` gives the
same result, and one more: replacing `asyncio` with threads does not rescue
CPU-bound work either, because CPython's Global Interpreter Lock serializes
bytecode execution across threads. One hundred awaited HTTP fetches drop
from ~100 s sequential to ~1–2 s concurrent, while hashing one hundred files
with threads finishes in essentially the same total CPU time as a loop.
The remedies are specific and off-loop: `loop.run_in_executor` (a thread
pool helps only for GIL-releasing work such as most I/O and many C
extensions), `ProcessPoolExecutor` or `multiprocessing` for real parallel
CPU work, or native libraries that release the GIL internally.

**Node's threadpool footnote.** Node is not literally single-threaded:
libuv maintains a small threadpool (four threads by default, tunable via
`UV_THREADPOOL_SIZE`) used by `fs` APIs, `dns.lookup`, and crypto's
asynchronous variants. Some "async" file and crypto work therefore does run
on other threads — but four of them, shared process-wide, and invisible in
the language's model. Two facts follow: heavy `fs` or `crypto.pbkdf2` load
saturates at four-way parallelism no matter how many cores exist, and a
developer crediting `async/await` for that parallelism has misattributed a
threadpool they never configured.

**Where the claim is actually true — and why that is a trap.** In C#, the
default scheduler may run continuations on thread-pool threads, so
CPU-composed tasks genuinely execute in parallel; Rust's Tokio does the same
with a multi-threaded runtime; Go's goroutines are multiplexed onto all
cores outright. These are real, but the parallelism is a property of the
*scheduler and its thread pool*, not of the `async` keyword — set Tokio to a
single-threaded runtime and the keywords behave exactly like the JavaScript
story. The correct sentence to carry out of this page: "`async/await`
provides concurrency; runtimes with thread pools can add parallelism; the
keywords themselves execute nothing."

## Practical Implications

- Classify before you await: if the awaited body is mostly waiting (network,
  disk, timers), `async/await` wins big; if it is mostly computing, it wins
  nothing and can add scheduling overhead.
- Keep per-event-loop work small: any CPU burst longer than a few
  milliseconds delays every other task on the loop; chunk long computations
  with `await` yield points or move them off the loop entirely.
- Know your offload paths cold: Node `worker_threads` and libuv's threadpool
  (and its default size of 4), Python `run_in_executor`,
  `ProcessPoolExecutor`, and GIL-releasing native libraries. These, not
  `await`, are the parallelism tools.
- Measure loop lag, not just request latency: event-loop delay histograms
  expose a saturated single thread that mean latency hides.
- In interviews, say "concurrency" when you mean overlapping waits and
  "parallelism" only when multiple cores execute at once — the distinction
  is a standard probe question precisely because so many candidates
  conflate them.

## Interview Questions

### Your Node.js service awaits four CPU-heavy transforms with `Promise.all` and sees no speedup. Why, and what are your options?

Because JavaScript's `Promise.all` overlaps only waits, and the transform
bodies are synchronous CPU work that runs to completion on the single main
thread, so total time is still the sum. The options are to move the work to
`worker_threads` (one per core for real parallelism), to child processes, or
to a native module that offloads internally. A strong answer also notes the
side effect: while each transform runs, the whole event loop stalls.

### Explain the difference between concurrency and parallelism using only `async/await` vocabulary.

Concurrency is having many tasks in flight, interleaving their waiting
periods on one thread — `async`, `await`, and `Promise.all` provide that.
Parallelism is multiple cores executing instructions simultaneously, which
the keywords never provide; it comes from the runtime's thread pool
(Tokio multi-threaded, .NET thread pool) or from explicit workers and
processes. In single-threaded runtimes the two are fully decoupled: you can
have unbounded concurrency and zero parallelism.

### In Python, which CPU-bound workloads actually benefit from replacing `asyncio` with a thread pool, and why?

Only work that releases the GIL: blocking I/O, and native extensions such as
hashing, compression, and much of NumPy that drop the lock around long C
calls. Pure-Python CPU loops serialize under the GIL regardless of thread
count, so they need `ProcessPoolExecutor`/`multiprocessing` (separate
interpreters) or the free-threaded build instead. The discriminating test is
whether the hot path executes Python bytecode or C code without the lock.

### A service's p50 latency is fine but p99 spikes whenever a big payload is processed, even though everything is `async`. Diagnose.

Big-payload processing is CPU work on the event loop: while it runs, all
other tasks' callbacks, timers, and socket reads queue behind it, so a
minority of requests that overlap the burst absorb a full loop stall. Check
event-loop lag (e.g., monitored timer drift) against the spike timing; the
fix is to chunk the processing across event-loop turns or offload it to a
worker thread or process. Averages look unaffected because the stall hits a
small fraction of requests — which is exactly the tail.

### A colleague says "we made it async, so it's parallel now." How would you falsify or confirm that in five minutes?

Check the workload mix first: if the awaited calls are network or disk
waits, the throughput gain is real but is concurrency, not parallelism.
Then run the discriminating experiment — fire N CPU-only tasks through
`Promise.all` and compare wall clock to the sequential sum; equality falsifies
the parallel claim immediately. Confirm parallelism positively by watching
CPU: one core saturated at 100% is the event loop, while all cores busy
indicates a worker pool. Finally, read the runtime configuration, because a
single-threaded Tokio runtime or a `run_in_executor`-free Python loop settles
the question from the deployment side.

## Key Takeaways

- `async/await` is a concurrency construct: it overlaps waiting, not
  execution. Total CPU time is unchanged; only idle-time overlap improves.
- JavaScript executes all task code on one thread; Python `asyncio` adds the
  GIL on top. CPU-bound work gains nothing from either, and long CPU bursts
  block every other task.
- Real parallelism requires real execution units: worker threads, child
  processes, a multi-threaded runtime's pool, or GIL-releasing native code.
  Node's libuv threadpool (default 4) already provides some, invisibly.
- The claim "survives" in production because I/O-bound services do see
  large throughput gains — but the credit belongs to overlapping waits,
  not to simultaneous execution.
- The vocabulary matters in interviews and design docs alike: say
  "concurrency" for in-flight work, "parallelism" for simultaneous
  execution, and name the offload mechanism when you promise the second.

## Cross-References

- [Misconception: Adding More Threads Always Improves Performance](./more-threads-faster.md)
  — the sibling claim on the threads-and-speed conflation, with Amdahl-style
  arithmetic for the parallel case
- [Misconception: Single-Threaded Languages Can't Parallelize](./single-threaded-languages-cant-parallelize.md)
  — the mirror-image myth: what worker threads, multiprocessing, and
  free-threaded CPython actually deliver
- [Follow-up Tree: Process Lifecycle](../followup-tree/process-lifecycle.md)
  — the process-versus-thread escalation chain behind the offload options
- [Concurrency: Async/Await](../../concurrency/async-await.md) — the
  book's full treatment of the syntax this page audits
- [Concurrency: Python GIL](../../concurrency/python-gil.md) — why Python
  threads serialize CPU work even when you add them
- [Node.js](../../languages/javascript/nodejs.md) — event-loop mechanics,
  worker threads, and the libuv threadpool in depth
- [Python Asyncio](../../languages/python/asyncio.md) — the event-loop
  implementation and its executor integration
- [Socket I/O Multiplexing](../../networks/sockets/io-multiplexing.md) —
  the kernel-side epoll/kqueue machinery the event loop is built on

## References

- Python Software Foundation. *asyncio — Asynchronous I/O*, and
  *concurrent.futures — ProcessPoolExecutor*. Python 3 documentation.
  <https://docs.python.org/3/library/asyncio.html>
- OpenJS Foundation. *Node.js API: worker_threads* and guide *Event loop,
  timers, and process.nextTick()*. <https://nodejs.org/api/worker_threads.html>
- libuv. *libuv API documentation — Thread pool operations*
  (`UV_THREADPOOL_SIZE` default of 4).
  <https://docs.libuv.org/en/v1.x/threadpool.html>
- PEP 703 — *Making the Global Interpreter Lock Optional in CPython*
  (status of the free-threaded build referenced in the Python section).
  <https://peps.python.org/pep-0703/>
