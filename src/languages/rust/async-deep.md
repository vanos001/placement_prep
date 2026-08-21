# Rust async/await Deep Dive

This page is a from-scratch look at how Rust models asynchronous computation: the
`Future` trait, the desugaring of `async fn` into state machines, the executor /
reactor split, the role of `Pin`, the `Send`/`Sync` bounds that gate where a
future can be polled, and how the design differs from JavaScript promises and
Go goroutines. It is intentionally low on slogans and heavy on the type-level
mechanics that interviewers probe when they ask "how does `async` actually
work?".

## 1. The `Future` trait, in full

Rust's async story is built around a single trait in `std::future`:

```rust
pub trait Future {
    type Output;
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>;
}

pub enum Poll<T> {
    Ready(T),
    Pending,
}
```

Three things are unusual here compared with a Java `CompletionStage` or a JS
`Promise`:

1. **Polling, not callbacks.** A future does not register a callback; it
   exposes a `poll` method. The executor decides when to call `poll`. If the
   future is not ready, it returns `Poll::Pending` and arranges for the
   executor to be poked again later.

2. **`Pin<&mut Self>` as the receiver.** `poll` takes a pinned mutable
   reference, not `&mut Self`. The pinning is what makes self-referential
   state machines safe (section 5).

3. **`Context<'_>` is just a `Waker` carrier.** In `std` today, `Context`
   wraps a `Waker`. The future's job is to register the waker with whatever
   I/O source or timer is blocking it, so that source can wake the executor
   when progress is possible.

A future, then, is just a state machine with a `poll` method. There is no
thread per future, no event loop baked into the language, and no allocation in
the `Future` trait itself.

### The `Waker` contract

```rust
impl Waker {
    pub fn wake(self);
    pub fn wake_by_ref(&self);
    pub fn will_wake(&self, &Waker) -> bool;
}
```

The waker is a callable handle to "the task that owns this future." When a
future returns `Pending`, it must have arranged for the waker to be called
once the underlying resource (socket readable, timer fired, channel has a
message) is ready. If it forgets to register the waker, the executor will
never poll it again — a common bug class called a "lost wakeup."

The contract is: wakers may be called from any thread; they must be
`Send + Sync`; they are cloneable and reference-counted; calling `wake`
multiple times is allowed but only one `poll` is guaranteed to result.
Implementing your own `Waker` is possible (it's a vtable over
`RawWaker`) but rarely done outside of custom executors.

## 2. `async fn` desugars to a state machine

The single most important fact about `async`/`await` in Rust is that the
compiler, not a runtime, transforms the function body into an `enum`
representing the suspended states.

Given this input:

```rust
async fn fetch_and_parse(url: &str) -> u32 {
    let body = fetch(url).await;       // .await point 1
    let parsed = parse(&body).await;  // .await point 2
    parsed.len() as u32
}
```

the compiler generates an anonymous type roughly equivalent to:

```rust
enum FetchAndParse<'a> {
    Start { url: &'a str },
    AwaitingFetch { url: &'a str, fut_fetch: FetchFut<'a> },
    AwaitingParse { url: &'a str, body: Vec<u8>, fut_parse: ParseFut<'a> },
    Done,
}

impl<'a> Future for FetchAndParse<'a> {
    type Output = u32;
    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<u32> {
        loop {
            match &mut *self {
                Self::Start { url } => {
                    let fut = fetch(url);
                    *self = Self::AwaitingFetch { url, fut_fetch: fut };
                }
                Self::AwaitingFetch { url, fut_fetch } => {
                    let body = ready!(Pin::new_unchecked(fut_fetch).poll(cx));
                    let fut = parse(&body);
                    *self = Self::AwaitingParse { url, body, fut_parse: fut };
                }
                Self::AwaitingParse { body, fut_parse, .. } => {
                    let parsed = ready!(Pin::new_unchecked(fut_parse).poll(cx));
                    *self = Self::Done;
                    return Poll::Ready(parsed.len() as u32);
                }
                Self::Done => panic!("poll after Ready"),
            }
        }
    }
}
```

Two consequences fall out of this:

- **No heap allocation is required.** The state machine is a plain enum whose
  size is the maximum of its variants. It can live on the stack, in a `Box`,
  in a `Vec`, anywhere a normal value can.

- **The locals are fields.** Every local that is *live across an `.await`*
  becomes a field of the enum. Locals that are dead before the next `.await`
  don't get stored. This is why `async fn` returning `impl Future` is
  zero-cost: there is no closure object, just a sized struct.

The `ready!` macro is a tiny convenience: it expands to `match e { Poll::Ready(v)
=> v, Poll::Pending => return Poll::Pending }`. Every `.await` is essentially
that macro wrapped around a `poll` call.

### Generators, RFC 2033, and the borrow-check story

`async fn` is sugar over a more general feature called a *generator* (a
resumable function with `yield`). RFC 2033 introduced the trait
`std::ops::Coroutine`, and `async fn` is a coroutine that yields `Pending`
and returns `Output`. The `gen` blocks RFC (RFC 3514) extended this to iterators.
The borrow checker works on the desugared state machine: the captures live in
the enum, so a future that holds `&'a mut State` across an `.await` keeps that
borrow for the entire lifetime of the future — including all the time it
spends parked inside the executor.

## 3. Executors and reactors: a hard split

The `Future` trait says *what* a future is. It says nothing about *who* polls
it, *when*, or *how* the future learns that an I/O resource is ready. That is
the job of two cooperating layers:

```
                 +-----------------+
  user code     |   Future        |  poll()
  (async fn)    |  state machine  |<---------+
                 +-----------------+          |
                        |                    |
                        v                    |
                 +-----------------+         |
  executor      |   Task list     |  wake() |
  (tokio etc)   |   Scheduler     |---------+
                 +-----------------+
                        |
                        v
                 +-----------------+
  reactor       |  epoll/kqueue/  |
                |  IOCP/io_uring  |
                 +-----------------+
                        |
                        v
                 +-----------------+
                 |  kernel sockets |
                 +-----------------+
```

The **executor** owns the task queue and the worker threads. It polls futures
when their wakers fire. The **reactor** is the layer that turns kernel I/O
readiness into waker invocations. In Tokio, reactor and executor live in the
same process and share a `Waker` registration table; the split is logical.

### Tokio's scheduler

Tokio's multi-threaded runtime is a work-stealing scheduler. There is one
global queue plus one per-worker local queue. Tasks are green: they are
 futures boxed into a `BoxFuture` and pinned on the heap. When a worker's
local queue drains, it steals half of another worker's queue, or falls back
to the global queue, or parks on `epoll_wait` (Linux) / `kqueue` (macOS,
BSD) / IOCP (Windows) until a waker fires.

The design choices that matter:

- **Work-stealing**: ensures load balancing across cores without a central
  contention point.
- **LIFO slot optimization**: a single-task "steal from yourself" slot that
  improves cache locality for bursty `tokio::spawn` patterns.
- **No preemption**: a future runs to `Pending` or `Ready` once polled. Long
  CPU-bound futures should periodically `yield` (`tokio::task::yield_now`)
  or be moved to `tokio::task::spawn_blocking` — otherwise the worker is
  starved.

### async-std and smol

`async-std` and `smol` use the `async-executor` crate underneath. Their
scheduler is also work-stealing but more minimal: a single global queue per
executor instance, no LIFO slot, simpler timer implementation. `smol` is the
spiritual home of the "small and composable" philosophy — `smol` proper is a
single crate that wires together `async-io` (the reactor) and
`async-executor` (the scheduler) in roughly 1000 lines.

### Blocking I/O is the cardinal sin

Every runtime above shares one rule: a future that blocks the OS thread
stalls the executor. A `std::thread::sleep` or a `std::fs::read` inside an
async function will hold the worker for as long as the syscall takes. Tokio's
answer is `spawn_blocking`, which moves the closure to a separate
thread-pool for blocking work. async-std has the equivalent `task::spawn_blocking`.

## 4. Pinning: why `Pin` exists

The `poll` signature uses `Pin<&mut Self>`. To understand why, consider what
happens when the compiler builds the state machine for:

```rust
async fn example() {
    let buf = [0u8; 64];
    let slice: &[u8] = &buf;   // borrows buf
    read_into(slice).await;    // future suspended across .await
    println!("{:?}", buf);
}
```

The desugared enum must store both `buf` and `slice` as fields. `slice` is a
reference whose validity depends on `buf` *not moving*. If the enum itself
moves (e.g. pushed into a `Vec<ExampleFut>`, reallocated, copied into a new
`Box`), the `slice` would dangle. The future is **self-referential**.

`Pin<P>` is the type-system tool that prevents this. `Pin` is a wrapper around
a pointer type `P: Deref` (or `DerefMut`) that promises the *pointee will not
be moved* unless its type implements `Unpin`. Almost all "normal" Rust types
(`u32`, `Vec<T>`, `String`, `Box<T>` for any `T: Unpin`) are `Unpin` — pinning
them is harmless because they don't care.

The `async fn` state machine is **not** `Unpin` (the compiler marks it
`!Unpin` by giving it a `PhantomPinned` field). So you can only get a
`Pin<&mut Self>` to a pinned future, never a plain `&mut Self`. Once a future
is pinned with `Pin::new` (only callable when `Self: Unpin`) or boxed with
`Box::pin`, it cannot be moved out again. The executor that owns the task
holds it pinned for the lifetime of the task.

The four important `Pin` methods are:

```rust
impl<P: Deref> Pin<P> {
    pub fn new(pointer: P) -> Pin<P> where P::Target: Unpin;
    pub fn new_unchecked(pointer: P) -> Pin<P>;             // unsafe
    pub fn get_ref(self) -> &P::Target;
    pub fn get_mut(self) -> &mut P::Target where P::Target: Unpin;
    pub unsafe fn get_unchecked_mut(self) -> &mut P::Target;
}
```

`new_unchecked` and `get_unchecked_mut` are the escape hatches. They are
how `Box::pin`, the `pin!` macro, and the inside of `poll` itself manipulate
pinned data without going through `Unpin`. If you write `unsafe` code that
promises pinning, you take on the obligation that "this value will not be
moved or have its memory reused/deallocated until `Drop` runs."

## 5. `Send` and `Sync` on futures

A `Future` itself is `Send` if every value it stores across `.await` points is
`Send`. Concretely: every variant of the desugared enum must contain only
`Send` data. If any one local live across an `.await` is `!Send` (an `Rc`, a
`RefCell`, a raw `*mut`), the future is `!Send`.

This matters because `tokio::spawn` has the bound `F: Future + Send + 'static`.
The spawned future may be polled on any worker thread. A `!Send` future (e.g.
one holding `Rc`) cannot be sent across threads; calling `tokio::spawn` on it
is a compile error:

```rust
async fn holds_rc() {
    let rc = std::rc::Rc::new(42);
    do_io().await;            // future now stores Rc -> !Send
}

tokio::spawn(holds_rc());     // E0277: Rc<i32> cannot be sent between threads
```

For `!Send` futures, use `tokio::task::spawn_local`, which schedules the
future on the current thread only, or `LocalSet`.

`Sync` on a future is rarely required directly; it shows up for wakers
(`Waker: Send + Sync`) and for futures shared via `FuturesUnordered`.

## 6. Zero-cost vs. JavaScript callbacks

The contrast with JavaScript is illustrative. A JS `Promise` is a heap object
holding a list of callback closures. Each `.then` allocates another closure.
An `await` in an `async function` is implemented by the V8 bytecode loop
resuming a generator — every suspension captures the locals into a heap
object. The promise chain has overhead per step.

In Rust, the equivalent `async fn` produces an enum whose `poll` is a single
match expression. With monomorphization and inlining, the hot path of an
`async fn` that awaits five I/O operations compiles to a tight loop with zero
allocations, zero indirect calls, and zero closures. The state machine is
sized exactly to fit its live locals. This is what "zero-cost async" means:
the abstraction compiles away.

The cost surfaces elsewhere: boxed futures (`Pin<Box<dyn Future>>`) require a
heap allocation and a vtable dispatch per poll. `async fn` returning
`Pin<Box<dyn Future>>` is common at API boundaries (e.g. trait methods) and
does cost a virtual call per `poll`. The `async fn` in trait feature,
stabilized in Rust 1.75, lets you write `async fn` in trait methods directly,
which the compiler then either monomorphizes or boxes behind `dyn` depending
on context.

## 7. The ecosystem

- **`async-trait`**: a pre-1.75 macro that desugared `async fn` in traits
  into `fn -> Pin<Box<dyn Future + Send>>`. Useful historically, but for new
  code prefer native `async fn` in traits plus `#[trait_variant::make]` if you
  need a `Send` variant.

- **`tokio::select!`**: a macro that races several futures concurrently,
  completing when the first is ready and dropping the rest. Implementation:
  wraps each branch in a future, polls them in order, returns on the first
  `Ready`. The dropped branches' cleanup runs on cancellation — this is where
  `Drop` on a future becomes load-bearing (file handles closed, in-flight
  requests aborted, etc.).

- **`tokio::spawn`**: schedules a future on the runtime, returning a
  `JoinHandle<T>` that is itself a future resolving to `Result<T,
  JoinError>`. The error variant is hit when the spawned task panics or is
  cancelled. Cancellation in Rust is drop-based: there is no `cancel()` API
  that fires a flag into the future — the executor simply drops the future
  and its `Drop` runs to completion.

- **`Futures` and `FuturesUnordered`**: from the `futures` crate, let you
  poll a collection of futures concurrently without spawning tasks.

- **`tokio::join!`, `try_join!`**: run futures concurrently and wait for all
  (or all-ok) — macro-level concurrency without spawning.

### What is *not* in `std`

Notably absent from the standard library: an executor, a reactor, a timer, a
`spawn`, an async Mutex, async channels. `std` provides the *vocabulary*
types (`Future`, `Poll`, `Context`, `Waker`, `Pin`); the rest is delegated to
the ecosystem. This is a deliberate choice — it lets different runtimes
target different niches (Tokio for production services, smol for libraries,
embassy for embedded `no_std` targets with a custom cooperative executor) and
is why "Which runtime?" is a real Rust interview question.

## 8. Pitfalls worth knowing

- **`async fn` returning `()` ignores the body's errors silently.** A future
  with `Output = ()` cannot report a panic back to the caller except through
  the `JoinError` from `spawn`.
- **Holding a `std::sync::Mutex` across `.await`** will block the worker
  thread if contention occurs. Use `tokio::sync::Mutex` (async-aware) for
  locks held across await points, with the caveat that it is slower for
  short critical sections.
- **`tokio::spawn` requires `Send + 'static`.** Borrowed futures cannot be
  spawned — they must be `'static`. Use `tokio::scope` (unstable) or
  `LocalSet` for scoped spawning.
- **Cancellation is implicit.** Calling `select!` on a future that holds a
  `&mut` to a buffer will silently drop the future and the buffer state is
  whatever the future's `Drop` left it in. Use `tokio::select!` with a `&mut`
  guard pattern or `tokio::select!`'s `if cancel.is_cancelled()` branch.
- **`FuturesUnordered` does not preserve order.** It yields as futures
  complete. Use `FuturesOrdered` for in-order completion.

## References

- Rust Asynchronous Programming Book — https://rust-lang.github.io/async-book/
- Tokio Documentation — https://docs.rs/tokio/latest/tokio/
- Rust RFC 2592 — `Future` trait — https://rust-lang.github.io/rfcs/2592-futures.html
- Rust RFC 2394 — `async`/`await` syntax — https://rust-lang.github.io/rfcs/2394-async_await.html
- Rust RFC 2033 — Experimental coroutines — https://rust-lang.github.io/rfcs/2033-experimental-coroutines.html
- "Asynchronous Programming in Rust" by Carl Lerche — https://carllerche.com/2019/04/17/an-async-1-0/
- `std::future` API docs — https://doc.rust-lang.org/std/future/
- `std::task::Poll` and `Waker` — https://doc.rust-lang.org/std/task/
- Pinning API and the `Unpin` auto-trait — https://doc.rust-lang.org/std/pin/
