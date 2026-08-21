# Kotlin Coroutines — Structured Concurrency

## Overview

Kotlin's coroutine system is a **library-level** implementation of lightweight,
cooperative multitasking on top of the JVM (and Kotlin/Native, Kotlin/JS). It is
built around three ideas that distinguish it from every other mainstream
concurrency model:

1. **Continuation-passing-style (CPS) transform at the compiler level** — the
   `suspend` keyword is a language feature, not a runtime feature. The compiler
   rewrites suspend functions into state machines that take an extra
   `Continuation` argument.
2. **Structured concurrency** — every coroutine belongs to a `CoroutineScope`
   that owns a `Job` tree; parents wait for children and cancellation flows
   downwards through the tree.
3. **Pluggable dispatchers** — `Dispatchers.Default`, `Main`, `IO`, `Unconfined`
   decide *where* a coroutine runs (which `Executor` or thread) without changing
   the *what* of the code.

This page covers the CPS transform, the scope/Job/Dispatcher trio, structured
cancellation semantics, `Flow`/`Channel`, the `kotlinx.coroutines` library, and
the contrast with Go goroutines and Project Loom virtual threads.

## 1. The `suspend` Function: a CPS Transform

A `suspend` function looks syntactically like an ordinary function:

```kotlin
suspend fun fetchUser(id: Int): User {
    val raw = api.get("/users/$id")   // api.get is itself suspend
    return User.parse(raw)
}
```

Under the hood, the Kotlin compiler rewrites this function in
**continuation-passing style**. The signature becomes roughly:

```kotlin
fun fetchUser(id: Int, cont: Continuation<User>): User?
```

`Continuation<T>` is the `kotlin.coroutines.Continuation` interface:

```kotlin
public interface Continuation<in T> {
    public val context: CoroutineContext
    public fun resumeWith(result: Result<T>)
}
```

Inside `fetchUser`, the compiler emits a **state machine** that captures all
local variables and the program counter in a field of the continuation object.
Each `suspend` point becomes a label:

```kotlin
// Pseudocode for what the compiler generates
class FetchUserSM(val id: Int, var cont: Continuation<User>) : ContinuationImpl(cont) {
    int label = 0
    User result
    String raw

    override fun resumeWith(result: Result<Any?>) {
        when (label) {
            0 -> {
                label = 1
                api.get("/users/$id", this)   // pass 'this' as continuation
                return
            }
            1 -> {
                raw = result.getOrThrow() as String
                label = 2
                result = User.parse(raw)
                cont.resumeWith(Result.success(result))
            }
        }
    }
}
```

Two consequences follow from this design:

- **No thread is blocked while a coroutine is suspended.** The JVM thread is
  free to run other coroutines; when the awaited future completes, it calls
  `continuation.resumeWith(...)`, which resumes the right state machine.
- **Allocation is paid per suspension, not per call.** A coroutine with three
  suspend points allocates one state-machine object plus the closures it needs
  — typically a few hundred bytes — not the megabytes of a thread stack.

The compiler's choice of CPS over a runtime-level green thread is what makes
Kotlin coroutines usable on stock JVM 8+ with no `--enable-preview` flags and
no native runtime changes.

## 2. `CoroutineScope`, `Job`, and `Dispatcher`

### CoroutineContext

A `CoroutineContext` is an **immutable, persistent set** of elements keyed by
`CoroutineContext.Key`. The most important elements are:

| Key | Element | Purpose |
|-----|---------|---------|
| `Job` | `Job` | Cancellation handle; parent in the structured tree |
| `CoroutineDispatcher` | `CoroutineDispatcher` | Decides which thread runs the coroutine |
| `CoroutineName` | `String` | Debug name |
| `ExceptionHandler` | `CoroutineExceptionHandler` | Uncaught-exception sink |

Contexts are combined with the `+` operator: `Dispatchers.Default + CoroutineName("worker")`.

### Job

A `Job` is the lifecycle handle for a coroutine. Its state machine:

```
       New
        |
        v
   Active --cancel--> Cancelling
     |                    |
   complete                |
     |                    v
     v                 Cancelled
  Completing
     |
     v
  Completed
```

A `Job` is `Active` while its coroutine is running. `join()` suspends until it
reaches a final state. Cancellation is **cooperative**: `cancel()` only sets a
flag; the coroutine must check `isActive` (or hit a suspending point that
checks it for it).

### CoroutineDispatcher

Dispatchers decide where the resumption runs:

```kotlin
runBlocking {                          // blocks the calling thread
    launch(Dispatchers.Default) { /* CPU work */ }
    launch(Dispatchers.IO)     { /* blocking JDBC, file I/O */ }
    launch(Dispatchers.Main)   { /* UI thread, e.g. Android */ }
}
```

- `Dispatchers.Default` — backbreaking worker pool sized to `Runtime.getRuntime().availableProcessors()`. Designed for CPU-bound work.
- `Dispatchers.IO` — a separate pool (capped at 64 by default, or `kotlinx.coroutines.io.parallelism`) for blocking calls that should not starve `Default`.
- `Dispatchers.Main` — platform-specific UI thread. On the JVM it uses a
  `MainThreadDispatcher` that schedules onto the AWT/Swing event loop or
  Android's `Handler`.
- `Dispatchers.Unconfined` — runs in whatever thread called `resumeWith`. Mostly a debugging tool; never use for production code.

`withContext(dispatcher) { ... }` is the idiomatic way to switch dispatcher for
a block and come back; it is the moral equivalent of `await`-ing on a different
thread pool.

## 3. Structured Concurrency

Structured concurrency — a phrase popularised by Roman Elizarov in 2017 —
imposes a **tree** on every coroutine:

```
                  App (root Job)
                    |
        +-----------+-----------+
        |                       |
    AuthScope              UiScope
        |                       |
   +----+----+              +---+---+
   |         |              |       |
  login    refresh        render   track
```

Three rules govern the tree:

1. **A coroutine can only be launched inside a `CoroutineScope`.** The scope
   provides a parent `Job`; the launched coroutine becomes a child of that job.
2. **A parent waits for all children.** `parent.join()` does not complete until
   every child has reached a final state.
3. **Cancellation propagates downward.** Cancelling the parent cancels every
   child. A child's failure (an uncaught exception) cancels the parent — and
   therefore all siblings — by default, unless a `SupervisorJob` is in scope.

The classic anti-pattern is the **"fire-and-forget"** coroutine started on
`GlobalScope`:

```kotlin
fun leaky() {
    GlobalScope.launch {           // no parent — leaks past caller's lifetime
        delay(10_000)
        println("done")
    }
}
```

`GlobalScope` exists but is almost never correct: it has no parent, so its
`Job` is unrooted and can outlive the component that started it. The
structured-concurrency alternative is to make the caller provide the scope:

```kotlin
class LoginController(val scope: CoroutineScope) {
    fun login(user: String, pass: String) = scope.launch {
        val token = authApi.login(user, pass).await()  // child of scope
        persistToken(token)
    }
}
```

When the controller is destroyed, its `scope` is cancelled, and the in-flight
`login` coroutine is cancelled with it — no leaked network call, no leaked
memory.

### Cancellation is Cooperative

`coroutineScope { ... }` is the canonical structured primitive — it creates a
new child scope and waits for everything inside it. Cancelling it cancels the
children:

```kotlin
suspend fun loadAll(): List<Item> = coroutineScope {
    val a = async { fetch("a") }
    val b = async { fetch("b") }
    try {
        listOf(a.await(), b.await())
    } catch (e: Throwable) {
        // The scope is cancelling; a and b are cancelled too.
        emptyList()
    }
}
```

A long-running CPU-bound coroutine must check `ensureActive()` or call a
suspending function periodically — otherwise cancellation will not take effect
until the next suspension point.

## 4. `Flow` and `Channel`

### Cold `Flow`

`Flow<T>` is a **cold** asynchronous stream: nothing runs until the consumer
calls `collect`, and each collector gets its own instance.

```kotlin
fun ticker(period: Long): Flow<Int> = flow {
    var i = 0
    while (currentCoroutineContext().isActive) {
        emit(i++)
        delay(period)
    }
}

suspend fun main() = coroutineScope {
    ticker(100).take(3).collect { println(it) }   // prints 0, 1, 2
}
```

`emit` is itself a `suspend` function — it suspends when the downstream is
not ready, which gives `Flow` built-in **back-pressure**. Operators like
`buffer()`, `conflate()`, `combine()`, `zip()`, and `flatMapLatest()` control
how back-pressure is shaped.

### Hot `Channel`

A `Channel<T>` is the **hot** dual — a CSP-style synchronous queue that is
independent of any consumer's lifetime.

```kotlin
val ch = Channel<Int>(capacity = Channel.RENDEZVOUS)  // 0-buffered
launch { for (i in 1..10) ch.send(i); ch.close() }
launch { repeat(10) { println(ch.receive()) } }
```

Internally a `Channel` is implemented as a lock-free MPSC ring buffer for
buffered channels and a `LinkedList` of suspended senders/receivers for the
`RENDEZVOUS` (zero-buffer) case. The implementation lives in
`kotlinx.coroutines.channels`.

## 5. The `kotlinx.coroutines` Library

`kotlinx.coroutines` is the de facto standard coroutine library. The
`kotlin-stdlib` only ships the `Continuation` interface, `suspend lambda` types,
and the `buildSequence`/`buildIterator` intrinsics. Everything you actually
use lives in `kotlinx.coroutines`:

- `kotlinx.coroutines.core` — `Job`, `CoroutineScope`, `Dispatchers`, `Flow`, `Channel`, `select` (multi-plexing).
- `kotlinx.coroutines.jdk8`, `reactor`, `rx2`, `rx3` — bridges to other async
  frameworks.
- `kotlinx-coroutines-debug` — agent-based debugger and the
  `DebugProbes` API.

The library is versioned with `-eap` suffixes for early access and follows a
strict **binary-compatibility** policy: code written against `1.0.0` in 2018
still compiles against `1.8.x` in 2024.

The default dispatcher uses a `SchedulerCoroutineDispatcher` backed by a
`ThreadPoolExecutor` with a work-stealing queue per worker — not unlike Go's
`P`-local run queue, see the comparison below.

## 6. Comparison to Go Goroutines

| Aspect | Kotlin Coroutines | Go Goroutines |
|--------|-------------------|---------------|
| Where is it implemented? | **Library** (`kotlinx.coroutines`) over JVM threads | **Runtime** (the Go scheduler built into every Go binary) |
| Compiler support | `suspend` keyword → CPS transform | `go` keyword → runtime call |
| Stack model | Continuation object holds locals; stack is just the JVM stack | Growable stack, starts at 2 KB, grows by copying |
| Preemption | Cooperative (must reach a suspension point) | Cooperative *and* asynchronous (signals at function prologue / loop backedge) |
| Cancellation | Cooperative flag; must check `isActive` | `context.Done()` channel; code must poll it |
| Scheduler | `Dispatchers.Default` = JVM `ForkJoinPool`-like work-stealing pool | GMP with work-stealing and a network poller |
| Channels | `kotlinx.coroutines.channels.Channel` (library) | Built-in `chan` type |
| Error propagation | Exceptions — but only inside a structured tree | `panic`/`recover`, no per-goroutine propagation |

The key contrast is **library vs runtime**. Go's `go` keyword calls into the
Go runtime, which manages a private M:N scheduler entirely invisible to the
OS. Kotlin's `launch` calls into a Kotlin library, which sits *on top* of JVM
threads — there is no separate scheduler runtime; the JVM's `ForkJoinPool`
and `ThreadPoolExecutor` do the actual scheduling.

This means: Kotlin coroutines inherit whatever thread model the JVM gives
them (and Project Loom changes that — see below), whereas Go's runtime owns
the entire concurrency stack from the syscall layer up.

## 7. JVM Integration and Project Loom

JEP 444 (delivered in JDK 21, September 2023) introduced **virtual threads** to
the JVM. A virtual thread is a `Thread` whose stack is stored on the heap and
whose execution is multiplexed onto a small number of "carrier" OS threads by
the JVM itself — at the runtime level, not the library level.

From Kotlin's perspective this is significant:

- A blocking JDBC call inside a coroutine on `Dispatchers.IO` consumes a
  pool thread for the whole duration of the blocking call.
- The same call on `Dispatchers.Default` is even worse — it starves the
  CPU-bound pool.
- Under Loom, `Thread.ofVirtual().start(runnable)` lets a coroutine run a
  blocking call *without* consuming a carrier thread, because the JVM
  unmounts the virtual thread at the blocking syscall.

The Kotlin team added `Dispatchers.Virtual` experimentally. The migration
story is that Loom and `kotlinx.coroutines` coexist: suspend functions remain
preferable for new code (zero allocation, cancellable), but legacy blocking
code can be wrapped in `runBlocking { Thread.startVirtualThread { ... }.join() }`
and treated like a coroutine.

## 8. Pitfalls and Best Practices

1. **Never use `runBlocking` in production code on the JVM.** It blocks the
   carrier thread — exactly the thing coroutines are supposed to avoid.
   `runBlocking` is for `main` functions and tests.
2. **Don't make a coroutine that "lives forever" without a parent.** If you
   need a long-lived service, give it its own `CoroutineScope(SupervisorJob() + Dispatchers.Default)` and cancel it explicitly on shutdown.
3. **Don't swallow `CancellationException`.** It is the protocol by which
   structured concurrency signals cancellation; rethrow it.
4. **Don't switch to `Dispatchers.IO` for every line.** `IO` exists for
   blocking calls; non-blocking code should stay on `Default`.
5. **Test with `runTest`.** It uses a virtual time source (`TestScope`) so
   `delay(60_000)` returns immediately.

## References

- Kotlin coroutines overview — official docs
  https://kotlinlang.org/docs/coroutines-overview.html
- kotlinx.coroutines GitHub repository
  https://github.com/Kotlin/kotlinx.coroutines
- Roman Elizarov, "Structured concurrency" (2017)
  https://medium.com/@elizarov/structured-concurrency-722d358327f4
- Kotlin KEEP proposal for coroutines (KEEP-69)
  https://github.com/Kotlin/KEEP/blob/master/proposals/coroutines.md
- JEP 444: Virtual Threads (Project Loom)
  https://openjdk.org/jeps/444
- Roman Elizarov, "Asynchronous Programming with Kotlin" (KotlinConf 2017)
  https://www.youtube.com/watch?v=_P1y3lRqIpw
- The `Continuation` interface source code
  https://github.com/JetBrains/kotlin/blob/master/libraries/stdlib/src/kotlin/coroutines/Continuation.kt
