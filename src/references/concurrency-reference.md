# Concurrency & Parallelism Reference Library

This page is a verified index of primary sources for concurrency and parallelism: official language memory models, synchronization and runtime documentation, lock-free libraries, model checkers, observability tooling, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Language memory models and their atomics, runtimes from goroutines to virtual threads to the BEAM, the lock-free algorithm literature, the tools that prove or debug it, and a two-track path from OSTEP's concurrency chapters to reading Vyukov and McKenney directly.

**68 entries** across 8 categories, plus **26 research & open-access sources** and **58 education & reference resources** (24 basic / 34 advanced), plus **9 video resources** and **4 conference sources**.

Every link HTTP-verified on **2026-10-08**.

> cppreference returns 403 to automated clients but loads normally in a browser. `pkg.go.dev` intermittently 429s automated clients. greenteapress.com and the bitbashing.io asset host did not respond to automated checkers at verification time; both load normally in a browser. 1024cores.net is frequently unreachable and is kept name-only.

## Contents

- [1. Go concurrency](#1-go-concurrency) — 7
- [2. JVM concurrency](#2-jvm-concurrency) — 10
- [3. Rust concurrency](#3-rust-concurrency) — 10
- [4. C/C++ concurrency](#4-cc-concurrency) — 10
- [5. Managed & actor runtimes](#5-managed--actor-runtimes) — 11
- [6. Lock-free libraries & classic algorithms](#6-lock-free-libraries--classic-algorithms) — 8
- [7. Models, formal verification & testing](#7-models-formal-verification--testing) — 6
- [8. Observability & debugging](#8-observability--debugging) — 6
- [Research papers & open-access literature](#research-papers--open-access-literature) — 26
- [Education & reference implementations](#education--reference-implementations) — 58 (24 basic / 34 advanced)
- [Video courses, channels & talks](#video-courses-channels--talks) — 9
- [Conference videos, notes & archives](#conference-videos-notes--archives) — 4


## 1. Go concurrency

### The Go Memory Model

- **Docs:** [go.dev/ref/mem](https://go.dev/ref/mem/)
- **Downloadable / offline:** Single HTML page; ships inside the Go source tree
- *Note:* Defines happens-before for Go. Updated in 2022 to make atomics sequentially consistent — pre-2022 summaries of it are wrong. Read before arguing about channels versus mutexes.

### sync

- **Docs:** [pkg.go.dev/sync](https://pkg.go.dev/sync/)
- **Downloadable / offline:** `go doc sync`; full godoc available offline via `pkgsite`
- *Note:* Mutex, RWMutex, WaitGroup, Once, Cond, Pool, Map. Small enough that reading the source is a rite of passage.

### sync/atomic

- **Docs:** [pkg.go.dev/sync/atomic](https://pkg.go.dev/sync/atomic/)
- *Note:* Compare-and-swap plus the typed atomics added in Go 1.19. The package doc's happens-before paragraph is the practical summary of the memory model.

### Data Race Detector

- **Docs:** [go.dev/doc/articles/race_detector](https://go.dev/doc/articles/race_detector/)
- *Note:* `go test -race` — built on ThreadSanitizer. Background in [the race-detector blog post](https://go.dev/blog/race-detector).

### Channels & select (Tour + spec)

- **Docs:** [go.dev/tour/concurrency](https://go.dev/tour/concurrency)
- **Developer / API:** [go.dev/ref/spec](https://go.dev/ref/spec) — channel types and select statements
- *Note:* The spec's channel section is short and precise: a send happens before the corresponding receive completes. Most channel folklore reduces to one sentence.

### context

- **Docs:** [pkg.go.dev/context](https://pkg.go.dev/context/)
- *Note:* Cancellation and deadlines as a first-class value. Misusing it (storing it in long-lived structs) is a reliable interview conversation.

### errgroup

- **Docs:** [pkg.go.dev/golang.org/x/sync/errgroup](https://pkg.go.dev/golang.org/x/sync/errgroup/)
- **Source:** [github.com/golang/sync](https://github.com/golang/sync)
- *Note:* WaitGroup plus error propagation plus context cancellation in about a hundred lines. Read it once WaitGroup makes sense.


## 2. JVM concurrency

### java.util.concurrent

- **Docs:** [docs.oracle.com — java.util.concurrent (Java 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html)
- *Note:* Executors, BlockingQueue, ConcurrentHashMap, Future. The package javadoc reads like a textbook; it is better than almost every blog post written about it.

### java.util.concurrent.atomic

- **Docs:** [docs.oracle.com — java.util.concurrent.atomic (Java 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/atomic/package-summary.html)
- *Note:* CAS-based counters, accumulators and field updaters; the javadoc states the memory effects of every method.

### java.util.concurrent.locks

- **Docs:** [docs.oracle.com — java.util.concurrent.locks (Java 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/package-summary.html)
- *Note:* Lock, ReadWriteLock, Condition and AbstractQueuedSynchronizer. AQS is the framework behind most of j.u.c; its javadoc is the deep end worth reaching.

### CompletableFuture

- **Docs:** [docs.oracle.com — CompletableFuture (Java 21)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html)
- *Note:* Composable futures behind an awkward API. The completion-ordering and default-executor rules in the javadoc are worth reading in full.

### JLS chapter 17 — Threads and Locks

- **Docs:** [docs.oracle.com/javase/specs/jls/se21/html/jls-17.html](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html)
- *Note:* The normative Java Memory Model. Volatile, monitors and final-field semantics stated as rules, not folklore. [All spec versions](https://docs.oracle.com/javase/specs/index.html) live one level up.

### JCStress

- **Source:** [github.com/openjdk/jcstress](https://github.com/openjdk/jcstress)
- *Note:* The JVM litmus-test harness from OpenJDK. If you believe something about the JMM, prove it here.

### JMH

- **Source:** [github.com/openjdk/jmh](https://github.com/openjdk/jmh)
- *Note:* The JVM benchmark harness. Concurrency benchmarks are where naive measurement dies; JMH exists because of that.

### Virtual threads (JEP 444)

- **Docs:** [openjdk.org/jeps/444](https://openjdk.org/jeps/444)
- *Note:* Finalized in JDK 21. Millions of blocked threads on a small pool of carriers — with the pinning caveat around `synchronized` that everyone should be able to explain.

### Structured concurrency (JEP 505)

- **Docs:** [openjdk.org/jeps/505](https://openjdk.org/jeps/505)
- *Note:* Fifth preview (JDK 25). Threads with a lifetime: a failure cancels the siblings. Long lineage — JEP 428, 437, 453, 480, 499, then this.

### Scoped values (JEP 506)

- **Docs:** [openjdk.org/jeps/506](https://openjdk.org/jeps/506)
- *Note:* Finalized in JDK 25. The immutable successor to `ThreadLocal`, designed for virtual threads.


## 3. Rust concurrency

### std::sync

- **Docs:** [doc.rust-lang.org/std/sync](https://doc.rust-lang.org/std/sync/)
- *Note:* Mutex, RwLock, Arc, mpsc, Barrier, Condvar. The `Send` and `Sync` traits (in `std::marker`) are the actual concurrency-safety mechanism; the module docs say so plainly.

### std::sync::atomic

- **Docs:** [doc.rust-lang.org/std/sync/atomic](https://doc.rust-lang.org/std/sync/atomic/)
- *Note:* Atomics with explicit orderings. The module documentation is a miniature memory-model course in itself.

### Tokio

- **Docs:** [docs.rs/tokio](https://docs.rs/tokio)
- **Developer / API:** [tokio.rs](https://tokio.rs/)
- *Note:* The dominant async runtime: scheduler, timers, IO. Know the contract — `std` provides the primitives, Tokio schedules them — and you can answer the "async runtime from scratch" interview question.

### Asynchronous Programming in Rust (the async book)

- **Docs:** [rust-lang.github.io/async-book](https://rust-lang.github.io/async-book/)
- *Note:* Why futures are lazy, what pinning is for, and what the compiler actually builds out of `async`/`await`.

### The Rustonomicon

- **Docs:** [doc.rust-lang.org/nomicon](https://doc.rust-lang.org/nomicon/)
- *Note:* The unsafe-code book. Its chapter on `Send`/`Sync` and data races is the most precise public statement of Rust's concurrency guarantees.

### Loom

- **Source:** [github.com/tokio-rs/loom](https://github.com/tokio-rs/loom)
- *Note:* Exhaustive model checker for concurrent Rust under the C11 memory model. Slow and thorough — use it on primitives, not applications.

### Miri

- **Source:** [github.com/rust-lang/miri](https://github.com/rust-lang/miri)
- *Note:* An interpreter that detects undefined behaviour, including some data races. Complements Loom: UB detection versus interleaving exploration.

### crossbeam

- **Source:** [github.com/crossbeam-rs/crossbeam](https://github.com/crossbeam-rs/crossbeam)
- *Note:* Epoch-based reclamation, scoped threads, channels and deques. The engineering that made non-blocking Rust practical.

### parking_lot

- **Source:** [github.com/Amanieu/parking_lot](https://github.com/Amanieu/parking_lot)
- *Note:* Faster, smaller replacements for `std::sync` primitives. Reading why it exists teaches you what `std`'s portability constraints actually are.

### Rust Atomics and Locks — Mara Bos

- **Docs:** [marabos.nl/atomics](https://marabos.nl/atomics/)
- **Downloadable / offline:** Free and complete online; print editions exist
- *Note:* Written by a Rust library team lead. The clearest treatment of memory ordering in any language, free — do not let "Rust" in the title scare you off if you write C++ or Java.


## 4. C/C++ concurrency

### C++ memory model

- **Docs:** [en.cppreference.com/w/cpp/language/memory_model](https://en.cppreference.com/w/cpp/language/memory_model)
- *Note:* The happens-before formalism that every other language borrowed. cppreference 403s automated clients; fine in a browser.

### std::atomic

- **Docs:** [en.cppreference.com/w/cpp/atomic/atomic](https://en.cppreference.com/w/cpp/atomic/atomic)
- *Note:* Per-operation orderings, the `is_lock_free` honesty check, and `std::atomic_ref` for shared buffers.

### C++ thread support library

- **Docs:** [en.cppreference.com/w/cpp/thread](https://en.cppreference.com/w/cpp/thread)
- *Note:* `std::thread`, `jthread`, mutexes, condition variables, futures, latches and barriers — the standard library sitting on top of the memory model.

### C11 atomics (`stdatomic.h`)

- **Docs:** [en.cppreference.com/w/c/language/atomic](https://en.cppreference.com/w/c/language/atomic)
- *Note:* C11 adopted the same memory model with a much smaller library. Useful reminder that the model, not the API, is the important part.

### P2300 — std::execution

- **Docs:** [wg21.link/P2300](https://wg21.link/P2300)
- *Note:* Senders and receivers — the standard C++ async framework adopted for C++26. Structured, dependency-aware, allocation-conscious.

### libuv

- **Docs:** [libuv.org](https://libuv.org/)
- **Developer / API:** [docs.libuv.org](https://docs.libuv.org/)
- **Source:** [github.com/libuv/libuv](https://github.com/libuv/libuv)
- *Note:* The event loop under Node.js. Handles, requests and the thread pool — the clearest production example of "concurrency is not parallelism" in C.

### Folly

- **Source:** [github.com/facebook/folly](https://github.com/facebook/folly)
- *Note:* Futures, AtomicHashMap, MPMCQueue and friends — battle-tested at Meta scale. Reading it is a graduate course in applied lock-free engineering.

### ThreadSanitizer

- **Docs:** [clang.llvm.org/docs/ThreadSanitizer.html](https://clang.llvm.org/docs/ThreadSanitizer.html)
- *Note:* Happens-before tracking at runtime, in C/C++ and Go. Understand its false negatives before trusting a clean run.

### Valgrind — Helgrind & DRD

- **Docs:** [valgrind.org/docs/manual/manual.html](https://valgrind.org/docs/manual/manual.html)
- *Note:* Two independent race detectors in one manual — Helgrind (happens-before) and DRD (lockset). Slower but sometimes deeper than TSan.

### oneTBB

- **Developer / API:** [oneapi-src.github.io/oneTBB](https://oneapi-src.github.io/oneTBB/)
- **Source:** [github.com/oneapi-src/oneTBB](https://github.com/oneapi-src/oneTBB)
- *Note:* Intel's Threading Building Blocks: work-stealing task arenas, flow graphs, concurrent containers. The reference design for task-based C++ parallelism.


## 5. Managed & actor runtimes

### .NET Task Parallel Library

- **Docs:** [learn.microsoft.com/en-us/dotnet/standard/parallel-programming](https://learn.microsoft.com/en-us/dotnet/standard/parallel-programming/)
- *Note:* Task, Parallel.For, PLINQ — data parallelism documentation that explains its own scheduling instead of hiding it.

### System.Threading.Channels

- **Docs:** [learn.microsoft.com/en-us/dotnet/core/extensions/channels](https://learn.microsoft.com/en-us/dotnet/core/extensions/channels)
- *Note:* The producer/consumer primitive behind modern .NET async pipelines. Bounded and unbounded, with backpressure semantics documented.

### Python — threading

- **Docs:** [docs.python.org/3/library/threading.html](https://docs.python.org/3/library/threading.html)
- *Note:* Shared-memory threads under the GIL: bytecode-level serialization, lock ordering traps. Pair with the GIL chapter of this book.

### Python — asyncio

- **Docs:** [docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
- *Note:* Event loop, coroutines, Tasks, the executor bridge. The docs are unusually candid about what runs where.

### PEP 703 — free-threaded CPython

- **Docs:** [peps.python.org/pep-0703](https://peps.python.org/pep-0703/)
- *Note:* Removing the GIL. Optional build in 3.13, officially supported in 3.14 — watch a language grow a real memory model in public.

### Erlang/OTP

- **Docs:** [erlang.org/doc](https://www.erlang.org/doc)
- *Note:* Processes, message passing, supervision, links and monitors. For the scheduler itself, the canonical references are the OTP efficiency guide and Erik Stenman's *The BEAM Book* — name-only, the scheduler write-ups live in conference talks and evolving drafts. Preemption in small reductions is why no process can starve its neighbours.

### Elixir — Task & GenServer

- **Docs:** [hexdocs.pm/elixir/Task.html](https://hexdocs.pm/elixir/Task.html) and [hexdocs.pm/elixir/GenServer.html](https://hexdocs.pm/elixir/GenServer.html)
- *Note:* Task for one-shot async, GenServer for stateful servers — the actor pattern with supervision trees spelled out.

### Kotlin coroutines

- **Docs:** [kotlinlang.org/docs/coroutines-guide.html](https://kotlinlang.org/docs/coroutines-guide.html)
- *Note:* Structured concurrency as a language feature: Job hierarchies, cancellation as cooperation, dispatchers as schedulers.

### Akka (and Apache Pekko)

- **Docs:** [akka.io](https://akka.io/)
- **SDKs & repos:** Apache Pekko — [pekko.apache.org](https://pekko.apache.org/) — the open-source fork created after Akka's 2022 license change
- *Note:* The industrial-strength actor toolkit: clustering, persistence, streams. Check which of the two your employer can actually use.

### Microsoft Orleans

- **Docs:** [learn.microsoft.com/en-us/dotnet/orleans](https://learn.microsoft.com/en-us/dotnet/orleans/)
- *Note:* Virtual actors — grains are activated on demand and single-threaded per identity. The most honest documentation of actor placement and lifecycle anywhere.

### Clojure — concurrency reference

- **Docs:** [clojure.org/about/concurrent_programming](https://clojure.org/about/concurrent_programming)
- *Note:* atoms, refs (STM), agents, vars — a language that shipped an opinionated concurrency taxonomy instead of one mechanism.


## 6. Lock-free libraries & classic algorithms

### moodycamel::ConcurrentQueue

- **Source:** [github.com/cameron314/concurrentqueue](https://github.com/cameron314/concurrentqueue)
- *Note:* Single-header lock-free MPMC queue, widely adopted in game engines and audio. The README doubles as a design document.

### liburcu

- **Docs:** [liburcu.org](https://liburcu.org/)
- *Note:* Userspace RCU — QSBR flavors, defer-reclaim, call-RCU. Pairs directly with the kernel RCU documentation below.

### JCTools

- **Source:** [github.com/JCTools/JCTools](https://github.com/JCTools/JCTools)
- *Note:* SPSC/MPSC/MPMC Java queues used by Netty and RxJava. The JMH benchmarks inside are the real tutorial.

### Vyukov bounded MPMC queue

- **Developer / API:** [rigtorp.se](https://rigtorp.se/) — Erik Rigtorp's posts rebuild Vyukov's classics with modern benchmarks
- **Source:** [github.com/rigtorp/MPMCQueue](https://github.com/rigtorp/MPMCQueue)
- *Note:* The bounded multi-producer/multi-consumer queue everyone copies — fixed-size cells, sequence numbers, one CAS per operation.

### 1024cores.net

*Note:* Dmitry Vyukov's collection of scalable algorithms — bounded MPMC, rolling queue, lazy stack, the original work-stealing write-ups. The historical reference for this entire field, and frequently unreachable; the content survives in mirrors and the Wayback Machine.

### crossbeam-epoch

- **Docs:** [docs.rs/crossbeam-epoch](https://docs.rs/crossbeam-epoch)
- **Source:** [github.com/crossbeam-rs/crossbeam](https://github.com/crossbeam-rs/crossbeam) — the epoch module
- *Note:* Epoch-based reclamation: how lock-free structures free memory without a garbage collector. Read with hazard pointers for contrast.

### seqlock (kernel docs)

- **Docs:** [docs.kernel.org/locking/seqlock.html](https://docs.kernel.org/locking/seqlock.html)
- *Note:* Sequence counters: writers bump a sequence, readers retry on odd counts. The classic optimistic-read pattern, with its writer-starvation caveats stated.

### RCU (kernel docs)

- **Docs:** [docs.kernel.org/RCU](https://docs.kernel.org/RCU/)
- *Note:* Read-copy-update — the answer to "how does the kernel read shared data without taking a lock". Start with the "What is RCU?" document; it rewards patience.


## 7. Models, formal verification & testing

### TLA+

- **Docs:** [lamport.azurewebsites.net/tla/tla.html](https://lamport.azurewebsites.net/tla/tla.html)
- *Note:* Lamport's specification language: concurrency as mathematics, with TLC exhausting the reachable states. The video course on the same page is the gentlest entry.

### TLA+ tools

- **Source:** [github.com/tlaplus](https://github.com/tlaplus)
- *Note:* The TLC model checker, the Toolbox IDE and the community modules, all open source.

### PlusCal

- **Docs:** [lamport.azurewebsites.net/tla/pluscal.html](https://lamport.azurewebsites.net/tla/pluscal.html)
- *Note:* An algorithm language that compiles to TLA+. Start here; drop to raw TLA+ only when PlusCal cannot say what you mean.

### GenMC

- **Source:** [github.com/MPI-SWS/genmc](https://github.com/MPI-SWS/genmc)
- *Note:* Model checking for C programs under the C11 memory model — the research tool behind a line of PPoPP/PLDI papers. The Rust analogues are Loom and Miri.

### Shuttle

- **Source:** [github.com/awslabs/shuttle](https://github.com/awslabs/shuttle)
- *Note:* AWS's randomized scheduler for Rust tests: bounded, seedable exploration of interleavings that unit tests never see.

### CDSChecker

- **Source:** [github.com/computersforpeace/model-checker](https://github.com/computersforpeace/model-checker)
- *Note:* Memory-model-aware model checking for C11 (SOSP 2013). Where the "C11 is weaker than you think" results came from.


## 8. Observability & debugging

### async-profiler

- **Source:** [github.com/async-profiler/async-profiler](https://github.com/async-profiler/async-profiler)
- *Note:* Low-overhead sampling for the JVM. Wall-clock mode makes lock waits and IO waits visible where a CPU profiler shows nothing.

### jcmd & jstack

- **Docs:** [docs.oracle.com — jcmd (Java 21)](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html) and [jstack](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jstack.html)
- *Note:* Thread dumps remain the fastest path from "the server is stuck" to "which monitor". `jcmd Thread.print` subsumes jstack.

### Go pprof

- **Docs:** [pkg.go.dev/net/http/pprof](https://pkg.go.dev/net/http/pprof)
- *Note:* One import to a profiling endpoint. Goroutine dumps find leaks, and the block and mutex profiles surface contention directly.

### Java Flight Recorder & Mission Control

- **Developer / API:** [jdk.java.net/jmc](https://jdk.java.net/jmc)
- **Source:** [github.com/openjdk/jmc](https://github.com/openjdk/jmc)
- *Note:* Always-on flight recording shipped in the JDK since 11; JMC is the viewer. Production-safe enough to leave enabled.

### Eclipse MAT

- **Docs:** [eclipse.dev/mat](https://eclipse.dev/mat/)
- *Note:* Heap-dump analyzer. Its dominator tree is how you find the object (and the thread holding its monitor) that everything is waiting on.

### perf

- **Docs:** [perf.wiki.kernel.org/index.php/Main_Page](https://perf.wiki.kernel.org/index.php/Main_Page)
- *Note:* `perf sched` and `perf lock` record contention from the kernel's point of view; the CPU profile catches spin-waiting that lock reports miss.


## Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; most systems, ML and PL work appears here before publication
- **Downloadable / offline:** Every paper is a free PDF. Bulk access documented at [info.arxiv.org/help/bulk_data/index.html](https://info.arxiv.org/help/bulk_data/index.html); a full-text API at export.arxiv.org
- *Note:* Not peer-reviewed. Treat an arXiv-only paper as a claim, not a result — but it is where you will read almost everything first.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML instead of PDF
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone and searchable in-page. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* Useful when a paper is contested — the discussion often contains the critique you were looking for.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring and TLDR summaries
- **Downloadable / offline:** Free Graph API ([semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)), bulk datasets available on request
- *Note:* The best free citation graph. 'Highly influential citations' is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions; successor to Microsoft Academic Graph
- **Downloadable / offline:** Entirely free API with no key required; complete database snapshots downloadable
- *Note:* The only large-scale bibliographic database that is open all the way down, including bulk snapshots.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **Developer / API:** [dblp.org/faq/13501473.html](https://dblp.org/faq/13501473.html)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to find everything a given researcher has published, and to see a conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **Source:** [github.com/openreview](https://github.com/openreview)
- **SDKs & repos:** ICLR, NeurIPS, COLM and dozens of other venues — papers plus the full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading the reviews and author rebuttals teaches you how the field evaluates work. Nothing else exposes this.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **Developer / API:** [core.ac.uk/services/api](https://core.ac.uk/services/api)
- **SDKs & repos:** Aggregates 300M+ open-access papers from repositories worldwide
- **Downloadable / offline:** Free API and bulk datasets
- *Note:* Good for finding the green open-access copy when a publisher's version is paywalled.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **Developer / API:** [api.unpaywall.org](https://api.unpaywall.org/)
- **SDKs & repos:** Finds legal free copies of paywalled papers via DOI
- **Downloadable / offline:** Free API; browser extension
- *Note:* Legal, author-deposited copies only. Install the extension and most paywalls simply stop appearing.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** A curated, categorised repository of classic CS papers with local meetup talks
- **Downloadable / offline:** Repo cloneable; many PDFs mirrored in-repo
- *Note:* The best starting point if you do not yet know which papers matter in a subfield.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Adrian Colyer's daily paper summaries, 2014-2021
- **Downloadable / offline:** Free archive, still online
- *Note:* No longer updated, but the back catalogue of ~1000 summarised papers is one of the great free CS resources.

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** OSDI, SOSP (co-published), NSDI, ATC, FAST, Security — the core systems venues
- **Downloadable / offline:** Every paper free, immediately, with no membership. Often with recorded talks
- *Note:* USENIX made everything open access years before the rest of the field. If a systems paper exists, check here first.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **SDKs & repos:** SIGMOD, ASPLOS, PLDI, POPL, SoCC and the ACM journals
- **Downloadable / offline:** Partly open: ACM Open and author-paid OA papers are free; others are paywalled
- *Note:* 403s to automated clients; loads in a browser. For paywalled items, check arXiv, the author's homepage or Unpaywall first — the free copy usually exists.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **SDKs & repos:** ISCA, MICRO, HPCA and the IEEE journals
- **Downloadable / offline:** Mostly paywalled; abstracts free
- *Note:* Almost always worth searching the author's page or arXiv instead. Architecture authors in particular post preprints widely.

### DROPS / LIPIcs (Dagstuhl)

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, CONCUR, ITP, SAT and many theory venues
- **Downloadable / offline:** 100% open access, free PDFs, Creative Commons licensed
- *Note:* A fully open publisher. CONCUR alone makes it worth bookmarking for concurrency theory.

### ACM PPoPP

- **Docs:** [sigplan.org/Conferences/PPoPP](https://www.sigplan.org/Conferences/PPoPP/)
- **SDKs & repos:** Principles and Practice of Parallel Programming — the flagship parallel-programming venue
- **Downloadable / offline:** Partially open via the ACM DL; many papers have arXiv or author copies
- *Note:* Where lock-free algorithms, transactional memory and memory-model work is published. Start with the last decade of test-of-time award winners.

### ACM SPAA

- **Docs:** [spaa.acm.org](https://spaa.acm.org/)
- **SDKs & repos:** ACM Symposium on Parallelism in Algorithms and Architectures — the theory side
- **Downloadable / offline:** Partially open via the ACM DL
- *Note:* Lower-bound and complexity results for shared memory. Read after you can read a pseudocode concurrent queue without wincing.

### ACM PODC

- **Docs:** [podc.org](https://podc.org/)
- **SDKs & repos:** Principles of Distributed Computing — consensus, wait-free hierarchy, impossibility results
- **Downloadable / offline:** Partially open via the ACM DL
- *Note:* The wait-free hierarchy (Herlihy 1991) and the FLP impossibility result live here. The boundary between concurrency and distributed systems is drawn in this venue.

### OOPSLA / PLDI (SIGPLAN)

- **Docs:** [sigplan.org/Conferences/OOPSLA](https://www.sigplan.org/Conferences/OOPSLA/)
- **SDKs & repos:** Programming-language venues — memory models, verification, static race detection
- **Downloadable / offline:** PACMPL (OOPSLA's journal) is fully open access; PLDI papers partly open via the ACM DL
- *Note:* Language-level concurrency work — including the C11 memory model lineage — appears here. Free copies are the norm via PACMPL.

### ASPLOS

- **Docs:** [asplos-conference.org](https://asplos-conference.org/)
- **SDKs & repos:** Architecture, PL and OS in one venue — where hardware memory models meet software
- **Downloadable / offline:** Partly open via the ACM DL
- *Note:* The right venue when the question crosses the hardware/software boundary — TSO, transactional memory, cache coherence exposed to software.

### EuroSys

- **Docs:** [eurosys.org](https://www.eurosys.org/)
- **SDKs & repos:** The leading European systems conference
- **Downloadable / offline:** Proceedings via ACM OA
- *Note:* Often more practical and implementation-focused than OSDI.

### USENIX OSDI

- **Docs:** [usenix.org/conference/osdi26](https://www.usenix.org/conference/osdi26)
- **SDKs & repos:** The flagship OS and systems venue
- **Downloadable / offline:** Every paper free, plus talk recordings
- *Note:* Concurrency at systems scale — schedulers, runtimes, deterministic execution — appears here. Alternates with SOSP.

### ACM SOSP

- **Docs:** [sosp.org](https://sosp.org/)
- **SDKs & repos:** The other flagship OS venue, running since 1967
- **Downloadable / offline:** Recent proceedings open via ACM OA
- *Note:* CDSChecker (SOSP 2013) is a reminder that concurrency verification results land here too.

### Dijkstra — Cooperating Sequential Processes (EWD123)

- **Docs:** [cs.utexas.edu — EWD123 (PDF)](https://www.cs.utexas.edu/~EWD/ewd01xx/EWD123.PDF)
- **Downloadable / offline:** Free PDF; the whole EWD archive is hosted at the same site
- *Note:* The 1965 manuscript where mutual exclusion, semaphores and the critical-section problem were solved on paper. The field's true starting point.

### Leslie Lamport's publications

- **Docs:** [lamport.azurewebsites.net/pubs/pubs.html](https://lamport.azurewebsites.net/pubs/pubs.html)
- **Downloadable / offline:** Nearly everything free from the author's own page
- *Note:* "Time, Clocks, and the Ordering of Events in a Distributed System" (1978) and the bakery algorithm papers are directly downloadable. Lamport's own explanations beat every summary of them.

### Herlihy & Wing — Linearizability (1990)

*Note:* "Linearizability: A Correctness Condition for Concurrent Objects", ACM TOPLAS 1990. Paywalled at the publisher, but the free copy is easy to find via the authors' pages or Unpaywall. The correctness condition every concurrent data structure is still measured against.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*24 resources across 5 topics.*


#### Start here

- **[OSTEP — Operating Systems: Three Easy Pieces](https://pages.cs.wisc.edu/~remzi/OSTEP/)** — Part II is *Concurrency*: threads, locks, condition variables, semaphores, common bugs. Free, complete, better written than the paid alternatives.
- **[The Little Book of Semaphores](https://greenteapress.com/wp/semaphores/)** — Free PDF that teaches synchronization through progressively harder classical problems. greenteapress.com did not answer automated checkers at verification time; it loads in a browser and the PDF is mirrored on many university course pages.
- **[Is Parallel Programming Hard, And, If So, What Can You Do About It?](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html)** — Paul McKenney's free book, continuously updated. The RCU chapters alone justify it.
- **[Rust Atomics and Locks](https://marabos.nl/atomics/)** — Free online. The clearest memory-ordering course in any language.
- **[The Rust Book — Fearless Concurrency](https://doc.rust-lang.org/book/ch16-00-concurrency.html)** — The shortest honest introduction to Send/Sync and message passing versus shared state.


#### Official walkthroughs & pattern write-ups

- **[Go Concurrency Patterns: Pipelines and cancellation](https://go.dev/blog/pipelines)** — The canonical staged-pipeline pattern, with cancellation done right.
- **[Go Concurrency Patterns: Context](https://go.dev/blog/context)** — Why cancellation belongs in a function parameter.
- **[Concurrency Is Not Parallelism (talk)](https://go.dev/blog/waza-talk)** — Rob Pike's talk that fixed the vocabulary. The slide deck has survived every runtime change since.
- **[Effective Go — concurrency sections](https://go.dev/doc/effective_go)** — Share by communicating, goroutines, channels, select.
- **[Go by Example](https://gobyexample.com)** — Goroutines, channels, tickers, worker pools as runnable snippets. Excellent for a first pass.
- **[Oracle Java tutorial — Concurrency](https://docs.oracle.com/javase/tutorial/essential/concurrency/)** — The official trail: threads, synchronization, liveness hazards, executor basics.
- **[.NET — Managed threading](https://learn.microsoft.com/en-us/dotnet/standard/threading/)** — The conceptual overview behind the TPL: threads vs tasks, sync primitives, cancellation.


#### Message passing, gently

- **[Elixir — Getting Started guide](https://elixir-lang.org/getting-started/introduction.html)** — Processes and message passing introduced without ceremony.
- **[Learn You Some Erlang](https://learnyousomeerlang.com/)** — The free Erlang book. The concurrency chapter is the best low-mathematics introduction to the actor model.
- **[Node.js — The event loop, timers, and nextTick](https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick)** — Single-threaded concurrency explained precisely by its most famous implementation.


#### Tutorial classics that outlived every redesign

- **[LLNL — POSIX Threads Programming](https://computing.llnl.gov/tutorials/pthreads/)** — The pthreads tutorial that has survived every platform transition since the 1990s.
- **[LLNL — Introduction to Parallel Computing](https://computing.llnl.gov/tutorials/parallel_comp/)** — Amdahl, granularity, shared vs distributed memory, in tutorial form.
- **[Python — concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)** — Thread and process pools behind one interface. The gentlest real API in this list.


#### The classics — name-only where the PDF floats

- **P. J. Birrell, *An Introduction to Programming with Threads* (1989)** — The DEC-SRC monograph that defined threads-as-an-API. No official stable link; every systems course hosts a copy.
- **Simon Marlow, *Parallel and Concurrent Programming in Haskell*** — Free from the author under O'Reilly's open terms; the URL has moved more than once, so search the title plus the author's site.
- **Brian Goetz, *Java theory and practice* article series** — The pre-JCiP articles ("A brief history of the Java Memory Model" among them) remain the friendliest JMM introduction. Archived across IBM developerWorks mirrors.
- **Herb Sutter, *The Free Lunch Is Over* (2005)** — The essay that predicted the concurrency turn. Short, dated only in its optimism about hardware clock speeds.
- **Julia Evans — concurrency & networking zines** — Sketch-first introductions that make race conditions and queues feel small. Buy or browse at wizardzines.com.
- **Hewitt, Bishop & Steiger, *A Universal Modular ACTOR Formalism* (1973)** — The paper that started the actor model. Paywalled at the publisher; free copies circulate from course pages.


### Advanced

*34 resources across 6 topics.*


#### University courses with full public materials

- **[MIT 6.172 — Performance Engineering of Software Systems](https://ocw.mit.edu/courses/6-172-performance-engineering-of-software-systems-fall-2018/)** — Lectures, labs and readings on multicore performance, all public. The C++ optimization ladder is the useful part.
- **[CMU 15-418 — Parallel Computer Architecture and Programming](https://www.cs.cmu.edu/~418/)** — The best public course on why parallel programs are slow: coherence, consistency, synchronization costs.
- **[Berkeley CS267 — Applications of Parallel Computers](https://www.cs.berkeley.edu/~demmel/cs267)** — Decades of public lecture notes on parallel algorithms. Berkeley blocks some automated clients; it loads in a browser.


#### The books worth owning

- **Herlihy, Shavit, Luchangco & Spear, *The Art of Multiprocessor Programming*** — The textbook for this entire index. Concurrent objects, spin locks, queues, STM — with exercises worth doing.
- **Goetz et al., *Java Concurrency in Practice*** — Twenty years old and still the best applied book on shared-state concurrency in any managed language.
- **Anthony Williams, *C++ Concurrency in Action*** — The standard C++11 concurrency book, kept current through C++20 features.
- **David Butenhof, *Programming with POSIX Threads*** — The 1997 original; the correctness discipline has not been improved on.
- **C. A. R. Hoare, *Communicating Sequential Processes*** — The 1985 book, free PDF at usingcsp.com (site intermittently offline; widely mirrored). The algebra behind CSP, occam, Go channels and Elixir.


#### Memory models & the hardware truth

- **[Matt Kline — What Every Systems Programmer Should Know About Concurrency (PDF)](https://assets.bitbashing.io/papers/concurrency.pdf)** — Free, hardware-first, the best bridge from OSTEP to the memory-model literature. The asset host 403s some automated clients; it loads in a browser.
- **[Ulrich Drepper — What Every Programmer Should Know About Memory (PDF)](https://www.akkadia.org/drepper/cpumemory.pdf)** — Long, but the cache-coherence and NUMA background everything else assumes.
- **Paul McKenney — *Memory Barriers: a Hardware View for Software Hackers*** — No stable link; now folded into the perfbook above, with the original PDF circulating from his site.
- **Sarita Adve & Kourosh Gharachorloo — *Shared Memory Consistency Models: A Tutorial*** — The 1996 tutorial that defined how to talk about consistency. Free copies circulate from the authors' pages.
- **Hans-J. Boehm — *Threads Cannot Be Implemented as a Library* (2005)** — Why C++ needed a memory model, in one paper. Free via SIGPLAN's author-hosted copies.
- **[The JSR-133 Cookbook](https://gee.cs.oswego.edu/dl/jmm/cookbook.html)** — Doug Lea's implementer's-eye view of the JMM: barriers for every compiler transformation.
- **[Bill Pugh — The Java Memory Model (JSR-133 FAQ)](https://www.cs.umd.edu/~pugh/java/memoryModel/)** — The original JMM explainer, still the friendliest correct one.
- **Alexey Shipilev — *Java Memory Model Pragmatics* (talk)** — No official stable link; search the title. The talk that made the JMM's compiler-side consequences legible.


#### Performance culture & the practitioners

- **[Preshing on Programming](https://preshing.com/)** — Jeff Preshing's posts on memory reordering and lock-free patterns are the standard reference-by-example.
- **[Mechanical Sympathy](https://mechanical-sympathy.blogspot.com/)** — Martin Thompson's blog; the origin of the term every low-latency team now uses.
- **[Nitsan Wakart's blog](https://psy-lob-saw.blogspot.com/)** — JMH methodology, false sharing, the Java-level cost model. Dormant, still essential.
- **[The LMAX Disruptor technical paper](https://lmax-exchange.github.io/disruptor/)** — The design write-up behind the [LMAX-Exchange/disruptor](https://github.com/LMAX-Exchange/disruptor) repo. Ring buffers, memory barriers and the business-logic-in-6ms argument.
- **[Agner Fog — Software optimization resources](https://www.agner.org/optimize/)** — Instruction costs and microarchitecture detail; also listed in the computer-architecture index, because the hardware does not care which conference you came from.
- **Bryan Cantrill's conference talks** — No single canonical index; search "Bryan Cantrill concurrency" and "observability". The argumentation about what concurrency bugs cost is unmatched.
- **Martin Thompson — *How WRONG is your queue?* (talk)** — No official stable link; search the title. Every concurrent queue in JVM land, measured.


#### The POSIX floor

- **[futex(2)](https://man7.org/linux/man-pages/man2/futex.2.html)** — What a mutex actually is on Linux. Read once; every managed runtime makes sudden sense.
- **[pthreads(7)](https://man7.org/linux/man-pages/man7/pthreads.7.html)** — The overview page: thread groups, signals, NPTL. The underused companion to every pthreads tutorial.
- **[POSIX / Single UNIX Specification](https://pubs.opengroup.org/onlinepubs/9699919799/)** — pthread_create, pthread_mutex, semaphores, memory visibility — the normative floor under everything above. Also listed in the operating-systems index.


#### Ecosystem deep dives

- **[Doug Lea's concurrency pages](https://gee.cs.oswego.edu/dl/concurrency-interest/)** — The author of j.u.c on why it is shaped the way it is. Sparse pages, dense information.
- **[OpenMP — specifications](https://www.openmp.org/specifications/)** — The pragmatic shared-memory standard: pragmas, tasking, offload. Read the 5.x spec's tasking chapter before dismissing it.
- **[OpenCilk](https://opencilk.org/)** — MIT's Cilk fork: fork-join parallelism with a provable work-stealing scheduler and a real compiler implementation.
- **[HPX](https://github.com/STEllAR-GROUP/hpx)** — A C++ runtime for distributed task-based parallelism; the research continuum made installable.
- **[Coz](https://github.com/plasma-umass/coz)** — The causal profiler: tells you which line of code is worth optimizing for *latency of others*, not CPU share.
- **[rr](https://github.com/rr-debugger/rr)** — Record-and-replay debugging. Concurrency bugs stop being heisenbugs when every run is bit-identical.
- **[Brendan Gregg's site](https://www.brendangregg.com/)** — Also in the operating-systems index; the off-CPU time and flame-graph material is directly about where concurrency hides time.
- **Vyukov — *Scalable Go scheduler design doc* (2012)** — No official stable link; search the title plus "Vyukov". The design note behind Go's work-stealing scheduler and half of every runtime interview question.


---

## Video courses, channels & talks

*9 resources across 2 groups.* Every channel and playlist below was fetched and title-verified on **2026-10-09**. Handles drift and several plausible-looking handles resolve to the wrong channel, so a 200 response is not proof of identity — the links here were each checked against the channel title.

### Channels & conference recordings

- **[CppCon](https://www.youtube.com/@CppCon)** — The C++ conference — where the memory-model and atomics talks live.
- **[NVIDIA Developer](https://www.youtube.com/@NVIDIADeveloper)** — GTC talks on GPU architecture and parallel programming; primary for accelerator design.
- **[Strange Loop Conference](https://www.youtube.com/@StrangeLoopConf)** — The Strange Loop channel: distributed systems, databases and language talks from the conference.
- **[USENIX](https://www.youtube.com/@USENIX)** — Conference recordings for most USENIX papers — free video, the fastest route into a systems paper.
- **[Computerphile](https://www.youtube.com/@Computerphile)** — Short, well-made explainers; the right first stop before a spec.
- **[InfoQ](https://www.youtube.com/@InfoQ)** — Conference keynotes and architecture talks — good for orientation, verify specifics elsewhere.
- **[Google TechTalks](https://www.youtube.com/@GoogleTechTalks)** — Concurrency and runtime talks, including historic ones from the authors of Go and Java libraries.
- **[Linux Plumbers Conference](https://www.youtube.com/@linuxplumbers)** — Kernel scheduler, locking and memory-ordering tracks.

### Lectures & playlists

- **[UC Berkeley CS162 — Operating Systems (Fall 2020)](https://www.youtube.com/playlist?list=PLbGbd5NUA_Nhdy07caUPmCR9v0o95lauT)** — The concurrency third of this course (lectures 6–12) is the clearest free treatment of locks, semaphores and monitors.

*Note:* No channel covers concurrency systematically; CppCon holds the memory-model and lock-free talks, GTC holds the GPU ones.

## Conference videos, notes & archives

*4 resources across 2 groups.* Conference recordings are the primary-source tier of video: the speaker is usually an author of the paper, and where a talk exists the proceedings entry is often open at the same link. Every URL here returned 200 on **2026-10-09** unless the note says otherwise.

Concurrency has no conference of its own; the material appears at CppCon, at the systems venues, and in the kernel tracks.

### Conference channels & video archives

- **[Linux Plumbers Conference](https://lpc.events/)** — Scheduler, locking and memory-ordering microconferences — kernel concurrency discussed by the people maintaining it.
- **[USENIX ATC '26](https://www.usenix.org/conference/atc26)** — The applied venue, open.
- **[FOSDEM video archive](https://video.fosdem.org/)** — Kernel and runtime devrooms.

### Notes, proceedings & paper-adjacent archives

- **No official channel for PPoPP or SPAA** — Checked on 2026-10-09; the parallel-computing conferences do not publish video. Use the ACM DL and author pages.

## If you only do three things

1. **Read OSTEP Part II (Concurrency).** It is free, complete, and gives you the vocabulary every runtime document assumes.
2. **Turn the race detector on in CI.** `go test -race`, `-fsanitize=thread`, JCStress for JVM memory-model claims — the cheapest correctness you will ever buy.
3. **Read Rust Atomics and Locks**, then Matt Kline's concurrency primer. Between the two, memory ordering stops being folklore.

## Honest notes

- **Memory-model documents drift with language versions.** The Go memory model changed materially in 2022; JLS chapter 17 of today is not the JSR-133-era text; C++ keeps extending its model (C++20 atomics wait/fnotify, C++26 execution). Always check *which version* a memory-model page describes, and distrust second-hand summaries — most of them describe the 2013-era state of their language.
- **1024cores.net is unstable.** It is kept name-only above for that reason. Vyukov's algorithms survive in Miri-tested ports, JCTools, crossbeam, and the Wayback Machine.
- **The Tokio/std overlap is deliberate.** The [languages & compilers index](./languages-compilers.md) covers Rust the language — rustc, Cargo, the book. This index scopes the async ecosystem: Tokio, crossbeam, Loom, Miri. Ask "is this a language question or a runtime question?" before choosing which page to open.
- **JCStress is the JVM litmus tool.** A claim about the JMM that comes without a jcstress test is folklore, however well-sourced. The same discipline maps to Loom for Rust and GenMC for C11.
- **Race detectors have false negatives.** TSan, Helgrind and DRD only observe interleavings that actually happened; a clean run is evidence, not proof. Exhaustive tools (Loom, GenMC) and randomized schedulers (Shuttle) exist because of this.
- **Conference access models are mixed.** USENIX is open immediately; PACMPL is open; ACM proceedings are partially open; IEEE is mostly paywalled. Budget Unpaywall/author-page time before budgeting money.
- **cppreference is the arbiter for C/C++ and it 403s bots.** Its memory-model and atomics pages are the practical reference of record; read them in a browser.

---

## Related sections of this book

- [Concurrency](../concurrency/overview.md) — the explanatory chapters this index points into
- [Threads](../os/threads/models.md) — OS-level thread models behind the runtimes above
- [Formal methods — TLA+](../formal-methods/tla-plus.md) — deeper on the verification track
- [Reference Libraries index](./README.md) — the other topic indexes
