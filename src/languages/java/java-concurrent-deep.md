# Java Concurrency Deep Dive: java.util.concurrent and Beyond

## Overview

The `java.util.concurrent` package arrived in J2SE 5.0 (2004, JSR-166 by Doug Lea and the JSR-166 expert group) and has been the foundation of Java concurrency ever since. The package was the answer to the inadequacy of `Thread`/`synchronized`/`wait`/`notify` for production concurrency: it added thread pools (`ExecutorService`), futures (`Future`, `FutureTask`), synchronizers (`CountDownLatch`, `CyclicBarrier`, `Semaphore`, `Phaser`), concurrent collections (`ConcurrentHashMap`, `CopyOnWriteArrayList`, `ConcurrentLinkedQueue`), and atomic variables (`AtomicInteger`, `AtomicReference`). Subsequent JDKs added `ForkJoinPool` and the work-stealing deque (Java 7), `CompletableFuture` (Java 8), `StampedLock` and `LongAdder` (Java 8), `VarHandle` (Java 9), and virtual threads (Java 21, JEP 444).

The mental model: Java's concurrency primitives are uncolored functions. A blocking call in Java is just a blocking call — the API does not change. This is the platform's central design choice and is what sets it apart from async/await languages like C#, Rust, or Kotlin coroutines where async functions have a different signature.

> Related: [Java Overview](./README.md), [Virtual Threads](./virtual-threads.md), [JVM Memory Model](./jvm-memory-model.md), [Reactive Programming](./reactive-programming.md), [Spring Boot Internals](./spring-boot-internals.md), [Quarkus and Micronaut](./quarkus-micronaut.md)

## ExecutorService, Future, CompletableFuture

`ExecutorService` is the abstraction for "submit a unit of work, get a handle to its result":

```java
ExecutorService pool = Executors.newFixedThreadPool(8);
Future<Integer> f = pool.submit(() -> {
    int result = expensiveComputation();
    return result;
});
// later, possibly from another thread
Integer r = f.get();  // blocks until done
```

`Future` is too thin to be useful for composition — you cannot say "after this finishes, run that". `CompletableFuture<T>` (Java 8) fixed this:

```java
CompletableFuture.supplyAsync(this::fetchUser, pool)
    .thenApply(User::getId)
    .thenComposeAsync(this::fetchPermissions, pool)  // returns CF, flattens
    .thenCombine(fetchDefaultPrefs(), (perms, prefs) -> new Session(perms, prefs))
    .thenAcceptAsync(session -> cache.put(session.id(), session), pool)
    .exceptionally(ex -> { log.error("session build failed", ex); return null; });
```

Key composition operators:

- `thenApply(Function<T,R>)` — synchronous map on the same thread that completed the previous stage.
- `thenApplyAsync(Function<T,R>, Executor)` — map on the supplied executor.
- `thenCompose(Function<T, CompletableFuture<R>>)` — flatMap; the result of the next stage is itself a CF.
- `thenCombine(CompletableFuture<U>, BiFunction<T,U,R>)` — wait for two CFs, combine.
- `allOf(CompletableFuture<?>...)` — wait for all; returns `CompletableFuture<Void>`.
- `anyOf(CompletableFuture<?>...)` — wait for first; result is `Object`.
- `exceptionally(Function<Throwable, T>)` — recover from error.
- `handle(BiFunction<T, Throwable, R>)` — recover or transform on both success and failure.

The trap: `thenApply` runs synchronously on whichever thread completed the previous stage. If you chain 5 stages and the previous one completed on the network IO thread, stage 2 will run on the IO thread. Use the `*Async` variants with an explicit `Executor` to escape.

`CompletableFuture` is push-only — there is no backpressure. For streams of values (not single results), reactive (see [Reactive Programming](./reactive-programming.md)) is the right tool.

## ForkJoinPool and the Work-Stealing Deque

`ForkJoinPool` (Java 7) is a thread pool optimized for divide-and-conquer tasks. The classic example:

```java
class SumTask extends RecursiveTask<Long> {
    private final long[] arr; private final int lo, hi;
    SumTask(long[] a, int l, int h) { arr = a; lo = l; hi = h; }
    protected Long compute() {
        if (hi - lo < THRESHOLD) return seqSum();
        int mid = (lo + hi) >>> 1;
        SumTask left = new SumTask(arr, lo, mid), right = new SumTask(arr, mid, hi);
        left.fork();              // submit left half to the pool
        long r = right.compute(); // run right half inline
        long l = left.join();     // wait for left
        return l + r;
    }
}
```

Each worker thread has a deque of pending subtasks. The worker pushes its own subtasks onto the back, and pops them off the back (LIFO, cache-friendly). When the deque is empty, the worker steals from the **front** of another worker's deque (FIFO, oldest task). The result is that work is distributed while still being cache-friendly for the thread that created it:

```
                Worker 0                Worker 1              Worker 2
            ┌──────────────┐         ┌──────────────┐     ┌──────────────┐
            │  push | pop  │         │  push | pop  │     │  push | pop  │
   back ◄─────────────────┘         └──────────────┘     └──────────────┘  back
   front                  └── steal ◄────── empty ─────── steal ◄────── empty
       (newest)            (oldest task, stolen FIFO)         (oldest)
```

This is the classic Chase-Lev work-stealing deque, implemented in Java as an array of `ForkJoinTask` references with a `volatile` base pointer for stealers and a `volatile` top for the owner. Steals are rare under balanced load — the cost is amortized across many subtasks.

`ForkJoinPool` is also the default executor for `CompletableFuture` when no executor is supplied (it uses the `commonPool`, parallelism = CPU count - 1), and the scheduler for virtual threads.

## Phaser

`Phaser` (Java 7) is a hybrid of `CyclicBarrier` and `CountDownLatch` with the added feature of dynamic parties. Parties can register and deregister on the fly:

```java
Phaser phaser = new Phaser(1);  // main thread is party 1
for (int i = 0; i < N; i++) {
    phaser.register();  // add a party
    new Thread(() -> {
        phaser.arriveAndAwaitAdvance();  // phase 1
        doWorkPhase2();
        phaser.arriveAndAwaitAdvance();  // phase 2
        phaser.arriveAndDeregister();    // leave the phaser
    }).start();
}
phaser.arriveAndAwaitAdvance();  // let phase 1 start
// ...
phaser.arriveAndAwaitAdvance();  // phase 2
```

`Phaser` is used when the number of participants is not known at construction time, or when the barrier must be reused for multiple phases with different party counts. A classic use case is a recursive fork-join where each level registers new parties.

## StampedLock

`StampedLock` (Java 8) is a read-write lock with an additional optimistic read mode. The pattern:

```java
StampedLock lock = new StampedLock();
Point p = new Point();
double dist() {
    long stamp = lock.tryOptimisticRead();     // non-blocking
    double x = p.x, y = p.y;
    if (!lock.validate(stamp)) {                // did a write happen?
        stamp = lock.readLock();                // yes — fall back to blocking
        try { x = p.x; y = p.y; }
        finally { lock.unlockRead(stamp); }
    }
    return Math.hypot(x, y);
}
void move(double dx, double dy) {
    long stamp = lock.writeLock();
    try { p.x += dx; p.y += dy; }
    finally { lock.unlockWrite(stamp); }
}
```

The optimistic read issues no CAS, no memory fence beyond a `volatile` read of the stamp. If no writes happened between the `tryOptimisticRead()` and `validate(stamp)`, the read succeeded at near-zero cost. If a write happened, the reader falls back to a blocking read lock and re-reads.

The catch: optimistic reads work only when writes are rare. Under contention (frequent writes), the fallback path costs more than a plain `ReentrantReadWriteLock`. Also, `StampedLock` is not reentrant — a thread holding the write lock cannot re-acquire it, which is a frequent source of deadlock when wrapping legacy code.

## LongAdder

`LongAdder` (Java 8) is a striped counter. Under high contention, `AtomicLong` becomes a bottleneck — every increment is a CAS on the same word, which under contention becomes a coherence storm on the cache line. `LongAdder` instead maintains a `Cell[]` array; a thread increments a cell selected by `hash(thread)` (striped):

```
              Thread T1        Thread T2       Thread T3
                 │                │               │
                 ▼                ▼               ▼
             ┌─────────┐      ┌─────────┐      ┌─────────┐
             │ Cell 0  │      │ Cell 1  │      │ Cell 2  │
             │  +1     │      │  +1     │      │  +1     │
             │  +1     │      │  +1     │      │  +1     │
             └─────────┘      └─────────┘      └─────────┘
                  └───────────┬────────────────┘
                              │ sum()
                              ▼
                       long total = cells[0] + cells[1] + ... + base
```

The cost is amortized across cells; `sum()` walks the array. The tradeoff: `sum()` is not a snapshot — concurrent writes during the sum will be partially reflected. For counters (request count, message count, throughput metric) this is fine; for exact aggregation under contention, you need a different mechanism.

`LongAccumulator` generalizes `LongAdder` to any associative operation: `new LongAccumulator(Long::sum, 0L)`, `new LongAccumulator(Long::max, Long.MIN_VALUE)`.

## VarHandle and Memory Ordering

`VarHandle` (Java 9, JEP 193) is the standardized replacement for `sun.misc.Unsafe`. It exposes memory-ordered access to fields and array elements:

```java
class Holder {
    private volatile int x;
    private static final VarHandle X;
    static {
        try {
            X = MethodHandles.lookup().findVarHandle(Holder.class, "x", int.class);
        } catch (Exception e) { throw new AssertionError(e); }
    }
    void cas(int old, int new_) {
        X.compareAndSet(this, old, new_);
    }
    void weakCas(int old, int new_) {
        X.weakCompareAndSet(this, old, new_);  // may fail spuriously
    }
    void setRelease(int v) { X.setRelease(this, v); }   // stores release
    int acquireLoad()      { return (int) X.getAcquire(this); }  // loads acquire
    long fetchAndAdd(int n) { return (long) X.getAndAdd(this, n); }
}
```

The memory ordering variants:

- **Plain** — no ordering guarantees (only atomic for the field width).
- **Opaque** — the write is visible, but no ordering with surrounding accesses.
- **Acquire/Release** — acquire (load) prevents subsequent reads from being reordered before; release (store) prevents prior writes from being reordered after. Matches C++ `memory_order_acquire` / `memory_order_release`.
- **Volatile** — full sequentially-consistent, matches `volatile` field semantics.

This is the JDK's port of the C++11 / Linux kernel / `java.util.concurrent` internal memory model. `AtomicReference` and friends now delegate to `VarHandle` under the hood; the performant lock-free algorithms in `ConcurrentHashMap`, `ForkJoinPool`, and the JCTools queues are written against `VarHandle`.

`VarHandle` is to memory ordering what `MethodHandle` is to method dispatch — a low-level, JVM-integrated primitive exposed without `Unsafe`.

## Virtual Threads

Virtual threads (JEP 444, finalized in JDK 21, September 2023) are JVM-managed lightweight threads that yield on blocking I/O and remount on a small pool of carrier platform threads. They are covered in depth in [Virtual Threads](./virtual-threads.md); the summary relevant to this page:

- Many:1 mapping to carrier threads (a `ForkJoinPool` with parallelism = CPU count).
- Stack lives on the heap as a `Continuation`; copied to carrier stack on mount, back to heap on park.
- Blocking I/O (`Thread.sleep`, socket reads, `BlockingQueue.take`) yields the carrier.
- Pinning (carrier cannot be unmounted) on `synchronized` blocks, JNI frames, class init locks — addressed by JEP 491 in JDK 24.

`Executors.newVirtualThreadPerTaskExecutor()` is the drop-in replacement for `Executors.newFixedThreadPool(N)` in I/O-bound services. The whole `java.util.concurrent` API works as-is — `CompletableFuture`, `Semaphore`, `BlockingQueue`, `CountDownLatch` — but the cost model changes: blocking is now cheap, thread count is no longer the bottleneck.

## Comparison to Go Goroutines

Both virtual threads and goroutines are M:N-scheduled lightweight threads with blocking-friendly runtime. Differences:

| Aspect | Java virtual threads | Go goroutines |
|--------|----------------------|----------------|
| Mapping | Many:1 carrier `ForkJoinPool` | Many:1 P/M GOMAXPROCS scheduler |
| Stack | Heap-allocated continuation, grows dynamically | Stack-segmented, starts 2 KB, grows by copying |
| Scheduling | Work-stealing `ForkJoinPool` | Work-stealing P/M model (Dmitry Vyukov) |
| Blocking I/O yields | Yes (JVM runtime hooks) | Yes (runtime netpoller + scheduler) |
| Communication | `BlockingQueue`, `CompletableFuture` | Channels (`chan`) — first-class |
| Selection | `Selector`/`SelectorProvider` | `select` statement (first-class) |
| Memory model | happens-before via `volatile`, `synchronized`, `VarHandle` | happens-before via channel send/receive, mutex |
| Race detector | `Thread sanitizer` via `-XX:+UseThreadSanitizer` (slow) | `-race` flag, near-production |
| Pinning hazard | `synchronized`, JNI, class init | `cgo` calls pin the M |
| Color of functions | No — all functions are uncolored | No — all functions are uncolored |

The deep similarity: both platforms decided that blocking-friendly lightweight threads, not reactive/async colored functions, are the right model for high-throughput I/O. The differences are mostly in the ecosystem — Go has channels first-class, Java has 25 years of blocking library code that just works.

A real semantic difference: Go's channel-based concurrency is built around "share memory by communicating" (Pike); Java's tradition is "communicate by sharing memory" with explicit synchronization. Both can be made to work either way, but idioms differ.

## Interview Questions

**Q: What is the difference between `ExecutorService.submit()` and `CompletableFuture.supplyAsync()`?**
`submit()` returns a `Future<T>` whose only useful methods are `get()`, `cancel()`, `isDone()`. It cannot compose. `supplyAsync(supplier, executor)` returns a `CompletableFuture<T>` which exposes `thenApply`, `thenCompose`, `thenCombine`, `exceptionally`, etc. — full functional composition, including error recovery and parallel coordination via `allOf` / `anyOf`.

**Q: How does work-stealing in `ForkJoinPool` work?**
Each worker has its own deque. It pushes subtasks onto the back and pops them from the back (LIFO, cache-friendly for the producing thread). When its own deque is empty, the worker steals from the front of another worker's deque (FIFO, oldest task, less likely to be in the victim's cache). The deque is a Chase-Lev work-stealing deque: a `volatile` base pointer for stealers, a `volatile` top for the owner. Steals are rare under balanced load.

**Q: When would you use `Phaser` instead of `CyclicBarrier`?**
When the number of parties is not known at construction time, when parties need to join and leave dynamically, or when you need multiple phases with different party counts. `CyclicBarrier` is for a fixed, fully-known party set reused across a single repeated barrier; `Phaser` is more flexible.

**Q: How does `StampedLock.tryOptimisticRead()` actually work?**
It returns a long stamp (a generation counter). The reader then reads the fields it cares about (without volatile reads or fences), and calls `validate(stamp)` which reads the same stamp again and checks equality. If a write occurred, the stamp changed, and `validate` returns false — the reader falls back to a blocking read lock. Under no write contention, the optimistic path is essentially free (two plain reads, no CAS).

**Q: What does `LongAdder.sum()` return — exact, or approximate?**
Approximate. It walks the cells; concurrent writes during the walk are partially reflected. For monotonic counters (request count, throughput) this is fine. For exact aggregation under contention, you need a different mechanism (e.g., `synchronized`, or lock up all writers).

**Q: What memory orderings does `VarHandle` expose?**
Plain (no ordering, just atomic width), Opaque (visibility only, no ordering with surrounding accesses), Acquire/Release (matches C++ acquire/release), Volatile (sequentially consistent). These mirror C++11 `memory_order_*`.

**Q: Why do virtual threads unmount on blocking I/O but not on `synchronized`?**
The JVM has runtime hooks in `Thread.sleep`, NIO socket reads, `BlockingQueue.take`, etc., that yield the virtual thread's continuation to the heap and free the carrier. `synchronized` (monitor enter/exit) is implemented at the bytecode level via JVM monitors that pin the thread to its carrier for the duration of the block — the runtime can't transparently unmount. JEP 491 (JDK 24) lifts most of this by reimplementing monitors without pinning.

**Q: What is the difference between `ForkJoinPool` and `Executors.newWorkStealingPool()`?**
`newWorkStealingPool()` is a convenience factory that creates a `ForkJoinPool` with parallelism = CPU count and async-mode = true (FIFO, not LIFO). `newFixedThreadPool` / `newCachedThreadPool` create `ThreadPoolExecutor`s with a shared queue, not per-worker deques. The work-stealing pool is appropriate for fork-join tasks; the classic pools for request/response.

**Q: How does `CompletableFuture.thenApply` differ from `thenApplyAsync`?**
`thenApply(fn)` runs `fn` on whichever thread completed the previous stage (could be the supplier's thread, could be the caller's thread if already complete). `thenApplyAsync(fn, executor)` schedules `fn` on the supplied executor. The former is faster in the no-async path; the latter protects you from running application code on a thread you don't own (e.g., the Netty event loop thread).

## Cross-References

- [Java Overview](./README.md)
- [Virtual Threads](./virtual-threads.md) — JEP 444 in depth
- [JVM Memory Model](./jvm-memory-model.md) — happens-before, volatile semantics
- [JVM Internals](./jvm.md) — `Monitor` and `synchronized` bytecode
- [Reactive Programming](./reactive-programming.md) — backpressure vs uncolored functions
- [Spring Boot Internals](./spring-boot-internals.md) — `@Async` thread pools
- [Quarkus and Micronaut](./quarkus-micronaut.md) — Vert.x event loops vs ForkJoinPool

## References

- "Java Concurrency in Practice" by Brian Goetz, Tim Peierls, Joshua Bloch, Joseph Bowbeer, David Holmes, Doug Lea (Addison-Wesley, 2006) — the canonical reference, still accurate on the principles
- JEP 444: Virtual Threads — https://openjdk.org/jeps/444
- JEP 193: Variable Handles — https://openjdk.org/jeps/193
- JDK API — `java.util.concurrent` package summary — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html
- JDK API — `java.util.concurrent.atomic` — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/atomic/package-summary.html
- JDK API — `java.util.concurrent.locks` — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/package-summary.html
- Doug Lea — JSR-166 — https://gee.cs.oswego.edu/dl/jsr166/
- The Go Memory Model — https://go.dev/ref/mem
- Dmitry Vyukov — Go scheduler design — https://www.ardanlabs.com/blog/2018/08/scheduling-in-go-part2.html
