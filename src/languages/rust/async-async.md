# Rust async/await — Futures, Pinning, Executors

## Overview

Rust's async story is unusual in two ways:

1. **The compiler emits state machines, not callbacks.** `async fn` becomes a
   `Future`-implementing struct whose `poll` method steps through the body of
   the function. There is no event loop baked into the language.
2. **The executor is a separate library.** Rust ships no runtime. Tokio,
   async-std, smol, and others provide the executor, the reactor, and the
   `spawn` primitive. This is "zero-cost async" in the most literal sense —
   the compiler is allowed to inline the entire future down to a stack
   machine if you let it.

This page covers the `Future` trait, `Pin`, the state-machine transform,
what an executor and reactor actually do, and how Rust's design differs from
JavaScript's callback-rooted async/await.

## 1. The `Future` Trait — Pull, Not Push

```rust
trait Future {
    type Output;
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>;
}

enum Poll<T> {
    Ready(T),
    Pending,
}
```

Two details matter:

- **`poll` takes `Pin<&mut Self>`.** The future cannot be moved while it is
  being polled. This is what makes self-referential futures safe (see §2).
- **`Context<'_>` carries a `Waker`.** When the future returns `Pending`, it
  promises to call `cx.waker().wake()` later, when it should be polled again.
  The executor installs the `Waker` before polling; the future stashes it
  somewhere (typically inside an `Arc` shared with an OS-side completion
  notification).

The Rust model is **pull-based**: the executor *asks* each future "are you
done yet?". This contrasts with JavaScript, where the runtime **pushes**
results into callbacks via the microtask queue — see §6 for the contrast.

Because `poll` takes `&mut Self`, the future owns its own state. There is no
closure capture, no `Box<dyn FnOnce>` indirection — the future *is* the
state. For a deeply-nested `async fn` this can produce types with hundreds of
bytes of captured locals, but it is a single contiguous struct, allocated
once when the future is spawned (or not at all, if you poll it inline).

### A hand-rolled `Future`

```rust
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};
use std::time::{Duration, Instant};

struct Timer { deadline: Instant }

impl Future for Timer {
    type Output = ();
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        if Instant::now() >= self.deadline {
            Poll::Ready(())
        } else {
            // The reactor (tokio) installs a waker that fires at the deadline.
            cx.waker().wake_by_ref();
            Poll::Pending
        }
    }
}
```

The idiomatic way to build this is `std::future::poll_fn`, which hides the
state machine behind a closure.

## 2. `Pin` — Self-Referential Futures, Safely

When you write

```rust
async fn example() -> i32 {
    let s = String::from("hello");
    let r = &s;                       // borrows s
    some_async_op(r).await;           // suspends
    drop(s);
    0
}
```

…the generated state machine stores both `s` (the `String`) and `r` (the
`&String` pointing into `s`) as fields of the future. The future is
**self-referential** — one of its fields holds a pointer to another.

If we were free to *move* this future, the pointer in `r` would still point
at the old address of `s`. That is the classic problem `Pin` solves.

### `Pin<P>`

`Pin<P>` is a wrapper around a pointer type `P: Deref` (or `DerefMut`) that
**forbids moving the pointee**:

```rust
struct Pin<P> { pointer: P }
```

The crucial method is:

```rust
impl<P: DerefMut> Pin<P>
where P::Target: Unpin
{
    pub fn get_mut(self) -> &mut P::Target { ... }
}
```

You can only get a `&mut T` out of a `Pin<&mut T>` (and therefore move `T`)
if `T: Unpin`. Most types — `String`, `Vec`, `i32`, your random struct —
are `Unpin`, because moving them is safe. **`async fn`-generated futures are
*not* `Unpin`** (they may contain borrows of their own fields), so they
cannot be moved out of a `Pin`.

The contract is:

| Operation | Allowed on `Pin<&mut T>` if |
|-----------|------------------------------|
| Read shared `&T`                       | Always |
| `&mut T` to a `T: Unpin`              | Always (because moving is fine) |
| `&mut T` to a `T: !Unpin`             | Only via `unsafe` |
| Drop                                  | Always |

### Why not just ban moves?

Because you sometimes need to put the future *into* a `Box`, a `Vec`, or an
arena — and that move has to be safe before the future is ever polled. The
compromise Rust chose:

1. You can move a future freely *before* it's polled.
2. The first call to `poll` takes `Pin<&mut Self>` — from that point on, you
   must keep it pinned.
3. The executor enforces this by `Box::pin(fut)` or by storing futures in a
   pinned arena.

`Box::pin` returns `Pin<Box<T>>`, the standard way to make a future addressable
across suspensions. `tokio::spawn` requires `'static + Send` futures, so it
boxes them internally.

## 3. `async fn` Desugaring to State Machines

The compiler lowers

```rust
async fn fetch_all(urls: Vec<Url>) -> Vec<Data> {
    let mut out = Vec::new();
    for u in urls {
        let d = client.get(u).await?;
        out.push(d);
    }
    out
}
```

…into something like:

```rust
enum FetchAllFut {
    Start(Vec<Url>, Vec<Data>),
    AwaitingGet { urls: Vec<Url>, out: Vec<Data>,
                  get_fut: GetFut },
    Done,
}

impl Future for FetchAllFut {
    type Output = Result<Vec<Data>, Error>;

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>)
        -> Poll<Result<Vec<Data>, Error>>
    {
        // SAFETY: we never move out of `self` field-by-field in ways
        // that would invalidate a self-reference.
        let this = unsafe { self.get_unchecked_mut() };
        loop {
            match this {
                FetchAllFut::Start(urls, out) => {
                    if let Some(u) = urls.first().cloned() {
                        let get_fut = client.get(u);
                        *this = FetchAllFut::AwaitingGet {
                            urls: urls.clone(),
                            out: out.clone(),
                            get_fut,
                        };
                    } else {
                        let out = std::mem::take(out);
                        *this = FetchAllFut::Done;
                        return Poll::Ready(Ok(out));
                    }
                }
                FetchAllFut::AwaitingGet { urls, out, get_fut } => {
                    let pinned_get = unsafe {
                        Pin::new_unchecked(get_fut)
                    };
                    match pinned_get.poll(cx) {
                        Poll::Ready(Ok(d)) => {
                            out.push(d);
                            urls.remove(0);
                            *this = FetchAllFut::Start(
                                std::mem::take(urls),
                                std::mem::take(out),
                            );
                        }
                        Poll::Ready(Err(e)) => {
                            *this = FetchAllFut::Done;
                            return Poll::Ready(Err(e));
                        }
                        Poll::Pending => return Poll::Pending,
                    }
                }
                FetchAllFut::Done => panic!("polled after completion"),
            }
        }
    }
}
```

Three things to notice:

1. **`loop` + state machine = the body of the async fn.** Each `await` point
   is a state transition; the `loop` makes it possible to fall through several
   states in a single `poll` (e.g. when the awaited future returns `Ready`
   immediately).
2. **Each `poll` is *cheap*.** No allocation, no virtual call (modulo the
   `dyn Future` indirection when a boxed future is awaited), no closure
   construction. Just a `match` on the state.
3. **The future size is the sum of every local captured across an `await`.**
   A function with 1 KB of locals and 5 await points does not produce a 5 KB
   future — locals that are dead at the await point are not stored — but the
   size is still the max *live* set. This is why a future can be a few hundred
   bytes when its non-async equivalent would have a 100-byte stack frame.

The `async`/`await` RFC (RFC 2394) calls these *synthetic coroutines* — they
are coroutines in surface syntax but **not** real stackful coroutines under
the hood. They are state machines compiled to plain Rust structs.

## 4. The Executor — Tokio, async-std, smol

An executor is a scheduler for `Future`s. Tokio is the dominant player; the
others share its structure. Tokio's components:

```
                ┌─────────────────────────────────────┐
                │          tokio Runtime             │
                │                                    │
                │   ┌──────────────────────────────┐ │
                │   │  Worker threads (N = cores) │ │
                │   │  ┌────┐ ┌────┐ ┌────┐ ┌────┐│ │
                │   │  │W0 │ │W1 │ │W2 │ │W3 ││ │
                │   │  └─┬──┘ └─┬──┘ └─┬──┘ └─┬──┘│ │
                │   │    │      │      │      │  │ │
                │   │  local  local  local  local │ │
                │   │  queue  queue  queue  queue │ │
                │   │   └──────┴──┬───┴──────┘   │ │
                │   │             │ (steal)      │ │
                │   └─────────────┼──────────────┘ │
                │                 ▼                 │
                │   ┌─────────────────────────────┐ │
                │   │       Reactor (mio)        │ │
                │   │   epoll / kqueue / IOCP     │ │
                │   │   + timer wheel            │ │
                │   └─────────────┬───────────────┘ │
                └─────────────────┼─────────────────┘
                                  │
                                  ▼
                          ┌──────────────────┐
                          │   OS syscalls    │
                          │  epoll_wait /    │
                          │  kqueue / io_uring│
                          └──────────────────┘
```

### Worker loop

Each worker thread runs roughly:

```rust
loop {
    // 1. Try the local deque (LIFO side for cache locality).
    if let Some(task) = local.pop() {
        poll_task(task); continue;
    }
    // 2. Try the global injector queue.
    if let Some(task) = injector.pop() {
        poll_task(task); continue;
    }
    // 3. Steal from another worker's deque.
    if let Some(task) = steal() {
        poll_task(task); continue;
    }
    // 4. Poll the reactor for I/O readiness.
    reactor.poll(Some(short_timeout));
}
```

Tokio uses a **chase-lev work-stealing deque** per worker, with a global
injector queue for `spawn` from outside the runtime. `spawn` from a worker
pushes onto that worker's deque — the spawned future tends to run on the
same thread that created it, which keeps its captured state hot in cache.

`poll_task` calls `Pin<&mut Task>::poll(&mut Context)`. If the future
returns `Pending`, the executor drops the `Waker` reference, leaves the task
parked, and moves on. When the reactor observes that an FD is ready, it walks
the list of `Waker`s registered for that FD and calls `wake_by_ref` on each.
`wake` marks the task runnable and pushes it back onto a worker deque.

## 5. The Reactor — `epoll`, `kqueue`, `io_uring`

The reactor is the part of the runtime that turns kernel-level I/O
notifications into `Waker::wake` calls. The fundamental primitive is
**readiness notification**: "tell me when this FD can be read or written
without blocking".

### Linux: `epoll`

Tokio on Linux uses `epoll` via the `mio` crate. The pattern:

```c
int epfd = epoll_create1(EPOLL_CLOEXEC);
struct epoll_event ev = { EPOLLIN|EPOLLET, {.fd = sock} };
epoll_ctl(epfd, EPOLL_CTL_ADD, sock, &ev);

// Later, in the reactor thread:
struct epoll_event events[256];
int n = epoll_wait(epfd, events, 256, timeout_ms);
for (i = 0; i < n; i++) {
    int fd = events[i].data.fd;
    reactor.wake(fd);   // call Waker::wake for all futures parked on this fd
}
```

Two subtleties:

- **Edge-triggered (`EPOLLET`) by default.** Rust futures prefer edge
  triggered because they perform *one* read per readiness notification and
  then re-park; level-triggered `epoll` would re-fire forever if data was
  unconsumed.
- **`EPOLLRDHUP`** is monitored so the reactor sees connection close events
  even when the kernel buffer still has readable data.

### macOS: `kqueue`

On macOS, the same `mio` abstraction uses `kqueue`. The semantics are
similar — edge-triggered filters (`EV_CLEAR`) — but the API is inverted:
`kevent` records changes to a watched FD; `kevent(...)` blocks for events.

### Windows: IOCP, the future: `io_uring`

Windows uses I/O Completion Ports (IOCP) — a completion model rather than a
readiness model. The abstraction is the same to Rust code: register a
buffer, get a `Waker` called when the I/O completes.

On Linux 5.1+ `io_uring` (and `tokio-uring`) provides true async syscalls
with submission and completion queues in shared memory. The Rust ecosystem
is moving toward making this a first-class reactor, because `io_uring`
removes the user/kernel boundary crossing on every syscall — submission
rings are written from user space and the kernel polls them.

## 6. Zero-Cost Async — No Allocation Per Poll

The promise of Rust async, repeated throughout the RFCs, is **"zero-cost"**.
Concretely:

- **No heap allocation per `poll`.** A future lives in a struct; the executor
  polls it in place. The only allocations are the one at `spawn` time (to
  put the future behind a heap-stored `Task`) and any the future does itself.
- **No virtual dispatch per `poll` if the future is monomorphized.** When
  you call `client.get(u).await` and the return type is `GetFut`, the
  compiler emits a direct call to `<GetFut as Future>::poll`. There is no
  `dyn` indirection. If you await a `Pin<Box<dyn Future>>` you do pay the
  indirect call — but only because you wrote it.
- **No closure construction per `await`.** Each await point is a state
  machine transition, not a closure allocation. The state machine is part of
  the parent future's struct.

This is what makes Rust async suitable for embedded and kernel contexts:
you can write `async fn` on a microcontroller with no allocator, polling the
future from a `loop { ... }` in `main`. The embedded ecosystem uses this
pattern in `embassy`, `rtic`, and `nrf-softdevice`.

## 7. Comparison with JavaScript async/await

| Aspect | Rust async | JavaScript async |
|--------|-----------|------------------|
| Foundation | `Future::poll` (pull) | `Promise` (push, callback-based) |
| Suspension | Poll returns `Pending`; executor re-polls when `Waker` fires | `Promise.then(cb)` schedules `cb` as a microtask |
| Allocation | One per `spawn` (for the `Task`); future itself is a struct | Every `Promise` is a heap-allocated object |
| Executor | Library (tokio, async-std, etc.) | Built into the language/event loop |
| Threading | Multi-threaded work-stealing pool | Single-threaded (modulo Web Workers / `worker_threads`) |
| `await` cost | State machine transition | Heap allocation + microtask scheduling |
| Cancellation | `drop` the future → state machine destructor runs | Cannot cancel a `Promise` directly; need `AbortController` / `AbortSignal` |
| Stack growth | Fixed-size future struct; size known at compile time | No stack; chains of closures stored on the Promise |

The fundamental contrast is **pull vs push**:

- In Rust, the executor asks the future "are you done?". If the answer is
  no, the future gives back a `Waker` and is silent until the executor polls
  it again. Memory is owned by the future.
- In JavaScript, the `Promise` registers callbacks with whatever async
  source it represents. When the source completes, the `Promise` *pushes*
  the result into the callback, which schedules a microtask. Memory is owned
  by the `Promise`.

Both work; they trade off in different directions. JS is more dynamic (a
`Promise` is a real object you can hold, chain, race). Rust is more
predictable (no hidden heap allocations, no scheduling jitter from the
microtask queue, deterministic destructor on cancel).

## 8. Pitfalls

1. **`async fn` futures are `!Unpin`.** They cannot be moved after `poll`
   begins. If you store one in a struct, the struct field must be `Pin<&mut
   MyFut>` or `Pin<Box<MyFut>>`.
2. **`Box<dyn Future>` is rarely what you want.** It costs a virtual call
   per `poll` and an allocation per spawn. Prefer concrete future types (let
   the compiler infer them with `async fn`) and only box at API boundaries.
3. **Don't block in `async`.** A blocking `std::thread::sleep` or a `Mutex`
   from `std` will hold the worker thread. Use `tokio::time::sleep` and
   `tokio::sync::Mutex` instead.
4. **`spawn` requires `Send + 'static`.** If your future borrows from a
   non-`'static` context, you cannot spawn it; either move the data in or
   use `tokio::task::LocalSet` for `!Send` futures.
5. **Cancellation is `drop`.** Rust has no `cancel()` method on a future.
   Dropping it cancels it. This means a future can be cancelled at any
   `await` point — code that needs cleanup must use RAII guards (`Drop`), not
   `try/finally`.

## References

- Asynchronous Programming in Rust (async book)
  https://rust-lang.github.io/async-book/
- Tokio documentation
  https://docs.rs/tokio/latest/tokio/
- RFC 2394: `async`/`await` (synthetic coroutines)
  https://rust-lang.github.io/rfcs/2394-async_await_synthetic_coroutines.html
- RFC 2592: the `Future` trait
  https://rust-lang.github.io/rfcs/2592-futures.html
- RFC 2349: `Pin` and the "projections" problem
  https://rust-lang.github.io/rfcs/2349-pin.html
- Tokio tutorial
  https://tokio.rs/tokio/tutorial
- `mio` crate — cross-platform I/O event loop
  https://docs.rs/mio/latest/mio/
- `tokio-uring` — `io_uring` integration
  https://github.com/tokio-rs/tokio-uring
- "Pin and suffering" — detailed walkthrough of `Pin` semantics
  https://fasterthanli.me/articles/pin-and-suffering
- std::future::poll_fn — ergonomic manual `Future` construction
  https://doc.rust-lang.org/std/future/fn.poll_fn.html
