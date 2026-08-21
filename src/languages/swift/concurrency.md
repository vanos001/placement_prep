# Swift Concurrency — async/await, Actors, and Structured Concurrency

## Overview

Swift's concurrency model shipped in Swift 5.5 (September 2021) and is the
single biggest language-level change since Swift 1. Unlike the
grand-central-dispatch (GCD) world it replaces, Swift's model is **compiler-enforced**:
the type system, not the programmer, decides which values can cross concurrency
boundaries safely. Three pillars hold it up:

1. **`async`/`await`** (SE-0296) — a continuation-based syntax that lets
   functions suspend without blocking a thread, much like the C# / ES2017 form
   it borrows from.
2. **Actors** (SE-0306) — reference types whose state is isolated to a
   serial executor, making data races **impossible to express** in safe Swift.
3. **Structured concurrency** (SE-0317, SE-0338) — `Task`, `TaskGroup`, and
   `async let` build a tree whose lifetimes are statically nested, with
   cancellation propagated through the tree.

This page covers the cooperative thread pool (the *cooperative executor*),
the actor isolation model, the `Sendable` checking that makes it all sound,
and the differences from Kotlin and Go.

## 1. `async`/`await`

### The syntax

```swift
func fetch(_ url: URL) async throws -> Data {
    let (data, _) = try await URLSession.shared.data(from: url)
    return data
}

await fetch(URL(string: "https://example.com")!)
```

The `async` keyword on the declaration says "this function can suspend". The
`await` keyword at the call site says "this is a suspension point". Both are
inherited: a function that calls an `async` function must itself be `async`.

The compiler lowers `async` functions in a style very similar to Kotlin's:
each `await` point becomes a `Continuation` parameter, and locals are hoisted
into a generated state-machine struct. The Swift runtime exposes this through
`UnsafeContinuation<T>` and the `withUnsafeContinuation` primitive:

```swift
func wait<T>(_ body: (UnsafeContinuation<T, Never>) -> Void) async -> T {
    await withUnsafeContinuation { body($0) }
}
```

A continuation is just a callback with one method — `resume(returning:)`. The
runtime guarantees that a continuation is resumed exactly once; resuming
twice traps.

### Suspension is not blocking

```swift
Task {
    let a = await compute()    // suspends; thread free to do other work
    print(a)
}
```

While a `Task` is suspended at an `await`, the thread it was running on is
free to execute another `Task`. **No OS thread is held.** This is what makes
"async all the way down" scalable: a single 16-thread pool can host tens of
thousands of concurrent `Task`s waiting on I/O.

## 2. Actors

An actor is a reference type whose mutable state is **isolated** behind a
serial executor:

```swift
actor Counter {
    private var count = 0
    func increment() { count += 1 }       // implicitly `async` from outside
    func value() -> Int { count }
}
```

From outside the actor, calls are asynchronous:

```swift
let counter = Counter()
await counter.increment()                  // awaits the actor's executor
let n = await counter.value()
```

Inside the actor, calls are synchronous — `increment` and `value` execute
back-to-back without suspending because the actor *is* the serial executor
owning the state.

### Why data races are impossible

In a normal `class`, two threads can mutate `count` concurrently. With an
actor, the compiler inserts a hop onto the actor's executor for every external
access. Mutating a `let` property of an actor from outside still requires
`await`, even though the property is constant, because the executor hop is
the *only* path in.

The compiler also enforces **actor isolation** at the source level. The
following does not compile:

```swift
actor Bank {
    var balance = 0
}

let bank = Bank()
Task { bank.balance = 100 }    // error: actor-isolated property 'balance'
                               // can not be referenced from a non-isolated
                               // async context
```

You must call an `async` method on the actor — the method *is* the entry
point.

### `nonisolated` and the global actor

Sometimes a property is logically immutable. `nonisolated` says "this is
reachable from anywhere without the executor hop":

```swift
actor Account {
    let id: UUID              // `let` properties are safe to read
    nonisolated let id: UUID  // explicit, also callable from sync code
    var balance: Decimal      // isolated, requires await
}
```

A **global actor** (`@MainActor`, `@MyCustomActor`) is an actor that is the
*type* of a singleton executor. Annotating a class, a method, or a property
with `@MainActor` makes it run on that actor's executor — the Swift equivalent
of the Android `Dispatchers.Main` rule, but enforced statically:

```swift
@MainActor
class View {                   // all methods run on the main actor
    func render() { ... }     // callable only from main-actor context
}
```

## 3. Structured Concurrency

### `Task`

```swift
let handle = Task { computePi() }   // unstructured; detached from any scope
let pi = try await handle.value     // wait for it
handle.cancel()                     // cancel it
```

A `Task` is the Swift analog of Kotlin's `Job`. Unlike Kotlin, however,
`Task { ... }` **detaches** from the surrounding task: it does not become a
child of the caller's task. To get a *child* task you have to use the
structured primitives below.

### `async let`

The simplest form of structured concurrency is `async let`:

```swift
func loadDashboard() async throws -> Dashboard {
    async let user = api.fetchUser()
    async let feed = api.fetchFeed()
    async let notifs = api.fetchNotifs()
    // The three requests run concurrently; 'await' below joins them.
    return try await Dashboard(user: user, feed: feed, notifs: notifs)
}
```

`async let` creates a *child task* that is **cancelled** if the surrounding
function throws or returns early. The scope of the child is the lexical scope
of the `async let` binding. If any one of the three requests throws, the
others are cancelled before `loadDashboard` propagates the error — exactly
like a `coroutineScope { ... }` block in Kotlin.

### `TaskGroup`

For dynamic fan-out, use `TaskGroup`:

```swift
func crawl(urls: [URL]) async -> [Data] {
    await withTaskGroup(of: Data.self) { group in
        for url in urls {
            group.addTask { await fetch(url) }
        }
        var results: [Data] = []
        for await chunk in group {
            results.append(chunk)
        }
        return results
    }
}
```

Properties of the group:

- All child tasks share the **parent's cancellation state**. Calling
  `cancelAll()` on the group — or the parent task being cancelled — cascades
  to every child.
- The group does **not** return until every child has finished. This is the
  parent-waits-for-children rule of structured concurrency.
- Throwing inside a child cancels siblings, just like `async let`.

There is also `withThrowingTaskGroup`, which propagates the first thrown
error and cancels the rest.

### Cancellation is cooperative

Cancellation in Swift is **not** preemption. A child task's `Task.isCancelled`
flag is set; the child has to check it (or call a cancellation-aware primitive
like `Task.checkCancellation()`):

```swift
func longCompute() async throws -> Int {
    for i in 0..<Int.max {
        try Task.checkCancellation()
        computeStep(i)
    }
    return 0
}
```

This is identical in spirit to Kotlin's cooperative `isActive` flag and to Go's
`context.Done()` pattern.

## 4. The Cooperative Thread Pool

Before Swift 5.5, async work was done with GCD — a system-managed thread pool
with `dispatch_async`, `dispatch_queue`, and `dispatch_semaphore`. The new
concurrency model deliberately does **not** run on GCD.

Instead, Swift ships a dedicated **cooperative thread pool** in the standard
library's `Concurrency` module. Two properties distinguish it from GCD:

1. **Work-stealing, like Go's `P`-local queue.** Each worker has a local
   deque; idle workers steal from the back of busy workers' deques. This
   keeps cache-hot tasks local and avoids global lock contention.
2. **Cooperative scheduling, not preemptive.** A worker thread will keep
   running tasks from its deque until the runtime signals it to yield — for
   example, when a higher-priority task becomes runnable. (Until Swift 5.9
   shipped the *priority-based preemption* machinery, switching was strictly
   cooperative at suspension points.)

Schematically the system looks like:

```
              ┌──────────────────────────────────────┐
              │     Swift Cooperative Executor       │
              │                                     │
              │   ┌───┐   ┌───┐   ┌───┐   ┌───┐    │
              │   │W0 │   │W1 │   │W2 │   │W3 │    │
              │   └─┬─┘   └─┬─┘   └─┬─┘   └─┬─┘    │
              │     │       │       │       │      │
              │   local    local   local  local   │
              │   deque   deque   deque  deque    │
              │     └───────┴──────┴──────┘       │
              │      work stealing (back)          │
              └──────────────────────────────────────┘
                              │
                              │ thread hops to actor
                              ▼
                ┌─────────────────────────┐
                │  Actor serial executor  │
                │   (one per actor)       │
                └─────────────────────────┘
```

Why not GCD? Two reasons. First, GCD's per-queue serial execution model
cannot express "this task is running on the same thread it was scheduled on"
because GCD hides the thread. Actors rely on knowing which executor is the
*current* one — that's how a synchronous internal call skips the hop. Second,
GCD is not work-stealing; long queues on one core with idle cores elsewhere
is the classic GCD pathology that Swift's pool eliminates.

## 5. `Sendable` — Compile-Time Concurrency Safety

`Sendable` (SE-0302, refined in SE-0414) is the protocol that marks types safe
to share across actor boundaries:

```swift
protocol Sendable {}
```

The compiler synthesizes `Sendable` conformance automatically for:

- Value types (`struct`, `enum`) whose stored properties are themselves `Sendable`.
- Actors (they enforce isolation themselves).
- `final class`es whose stored properties are `Sendable` and immutable.

Conformance is **checked**, not just declared. The compiler rejects:

```swift
class Mutable {
    var x = 0          // mutable
}
extension Mutable: Sendable {}   // error: stored property 'x' is not
                                // 'Sendable' (or is mutable)
```

The check fires when a value crosses a concurrency domain: passing an
argument to a `Task` initializer, capturing in an `@Sendable` closure,
returning from a function whose context differs from the caller's actor.

### `@unchecked Sendable`

When the programmer *knows* a class is safe (e.g., it has internal locking)
but cannot prove it to the compiler, `@unchecked Sendable` opts out of the
check:

```swift
final class Locked: @unchecked Sendable {
    private let lock = NSLock()
    private var x = 0
    func incr() { lock.lock(); x += 1; lock.unlock() }
}
```

This is a sharp tool. The Swift team's recommendation is to use it only when
wrapping thread-safe C/Objective-C APIs.

### Sendable checking is "strict" only with `-strict-concurrency`

Through Swift 5.7, `Sendable` violations were warnings. From 5.8 onward the
`-strict-concurrency=complete` flag makes them errors; in Swift 6 it is the
default. **Swift 6 is the milestone where the language becomes data-race-safe
by default** — code that does not type-check cannot be compiled in Swift 6
language mode.

## 6. Comparison with Kotlin and Go

| Feature | Swift | Kotlin | Go |
|---------|-------|--------|-----|
| Async primitive | `async`/`await` (SE-0296) | `suspend`/`await` | `go` keyword + channels |
| Concurrency unit | `Task` | `Job`/coroutine | goroutine |
| Data isolation | `actor` (compiler-enforced) | `Mutex`/`Channel` (manual) | channel + "share by communicating" idiom |
| Cancellation | `Task.cancel()` → flag, cooperative | `Job.cancel()` → flag, cooperative | `context.Done()` channel |
| Scheduler | Swift cooperative pool (work-stealing) | `Dispatchers.*` over JVM pools | Go runtime GMP scheduler |
| Static data-race safety | `Sendable` (compiler-checked) | None | `go vet -race` (runtime) |
| Library vs runtime | Compiler + stdlib | Library (`kotlinx.coroutines`) over JVM | Runtime |
| Structured concurrency | `async let`, `TaskGroup` | `coroutineScope` | `errgroup.WithContext` (idiom) |
| Preemption | Cooperative + priority hints | Cooperative | Cooperative + async preemption (Go 1.14+) |

Two contrasts are worth dwelling on:

- **Kotlin vs Swift on data races.** Kotlin lets you share a mutable
  `HashMap` across `launch` blocks; if it races, you find out at runtime
  with a `ConcurrentModificationException` or silent corruption. Swift
  forbids the shared mutable `HashMap` at compile time — the only path
  through the type system is to put it in an actor or wrap it in a `Mutex`
  with `@unchecked Sendable`.
- **Go vs Swift on data isolation.** Go's slogan is "share memory by
  communicating" — but the language does not enforce it. You can write a
  shared `*sync.Map` in Go and have a race. Swift makes the equivalent
  forbidden by default: there is no way to mutate an actor's `var` from
  outside its executor.

## 7. Pitfalls

1. **A `Task { ... }` is detached.** It will outlive the function that
   started it. If you need it bound to the surrounding scope, use `async let`
   or `TaskGroup`.
2. **`@MainActor` is viral.** A function annotated `@MainActor` must be
   `await`ed from a non-main context, and it forces every function calling
   it to be either `@MainActor` or `async`. Choose carefully.
3. **`Sendable` errors with Objective-C interop.** Many `NSError`-bridged
   types are not yet `Sendable` and produce noise. Use `@unchecked Sendable`
   only as a temporary fix.
4. **Don't fight priority escalation.** If a high-priority task awaits a
   low-priority child, the runtime temporarily *raises* the child's priority
   to match (SE-0307). This is by design; do not work around it.
5. **Avoid unstructured concurrency in library code.** Public APIs that
   return detached `Task`s are hostile to cancellation; prefer `withTaskGroup`
   or `withCheckedThrowingContinuation`.

## References

- SE-0296: Async/await
  https://github.com/apple/swift-evolution/blob/main/proposals/0296-async-await.md
- SE-0306: Actors
  https://github.com/apple/swift-evolution/blob/main/proposals/0306-actors.md
- SE-0302: Sendable and @Sendable closures
  https://github.com/apple/swift-evolution/blob/main/proposals/0302-concurrency-safety/static-sendable.md
- SE-0317: async let — implicitly awaiting sub-tasks
  https://github.com/apple/swift-evolution/blob/main/proposals/0317-async-let.md
- SE-0338: Concurrency Interoperability with Objective-C (back-deployment)
  https://github.com/apple/swift-evolution/blob/main/proposals/0338-swift-concurrency-backdeployment.md
- SE-0307: Cooperative task cancellation and priority escalation
  https://github.com/apple/swift-evolution/blob/main/proposals/0307-actor-execution.md
- Swift Concurrency guide (official docs)
  https://docs.swift.org/swift-book/LanguageGuide/Concurrency.html
- WWDC 2021 — "Meet async/await" (session 10132)
  https://developer.apple.com/videos/play/wwdc2021/10132/
- WWDC 2021 — "Protect mutable state with actors" (session 10333)
  https://developer.apple.com/videos/play/wwdc2021/10333/
- Swift standard-library `Concurrency` module source
  https://github.com/apple/swift/tree/main/stdlib/public/Concurrency
