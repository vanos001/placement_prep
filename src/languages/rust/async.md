# Async/Await in Rust

## Overview

Rust's async/await enables efficient asynchronous programming for I/O-bound tasks. Unlike languages with built-in runtimes (Python, JavaScript), Rust's async model is **zero-cost** — the compiler transforms async code into state machines without heap allocation or garbage collection. You choose your own runtime (Tokio, async-std, smol) based on your needs.

## Core Concepts

### The `Future` Trait

```rust
trait Future {
    type Output;
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>;
}

enum Poll<T> {
    Ready(T),    // Future completed with value T
    Pending,     // Future not ready yet, try again later
}
```

### `async` and `await`

The `async` keyword transforms a function into one that returns a `Future`. The `await` keyword suspends execution until the future is ready:

```rust
// async fn returns a Future<Output = String>
async fn fetch_data(url: &str) -> String {
    // Simulated async work
    "data".to_string()
}

// Using async code
async fn process() {
    let data = fetch_data("https://example.com").await;
    println!("{}", data);
}
```

### How `async fn` Works Under the Hood

```rust
// This async function:
async fn example() -> i32 {
    let a = step_one().await;
    let b = step_two(a).await;
    a + b
}

// Is transformed into something like:
enum ExampleFuture {
    Start,
    WaitingForStepOne { a: i32 },
    WaitingForStepTwo { a: i32 },
    Complete,
}

impl Future for ExampleFuture {
    type Output = i32;
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<i32> {
        match self.state {
            Start => {
                match step_one().poll(cx) {
                    Poll::Ready(a) => {
                        self.state = WaitingForStepTwo { a };
                        Poll::Pending
                    }
                    Poll::Pending => Poll::Pending,
                }
            }
            // ... other states
        }
    }
}
```

## Tokio Runtime

Tokio is the most popular async runtime for Rust:

```rust
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() {
    // Spawn concurrent tasks
    let handle1 = tokio::spawn(async {
        sleep(Duration::from_secs(1)).await;
        "task 1 done"
    });

    let handle2 = tokio::spawn(async {
        sleep(Duration::from_secs(2)).await;
        "task 2 done"
    });

    // Wait for both tasks
    let (r1, r2) = tokio::join!(handle1, handle2);
    println!("{}, {}", r1.unwrap(), r2.unwrap());
}
```

### Tokio Components

| Component | Purpose |
|-----------|---------|
| `tokio::spawn` | Spawn a new task |
| `tokio::join!` | Run futures concurrently, wait for all |
| `tokio::select!` | Wait for the first future to complete |
| `tokio::sync::Mutex` | Async-aware mutex |
| `tokio::sync::mpsc` | Async multi-producer, single-consumer channel |
| `tokio::time::sleep` | Async sleep |
| `tokio::fs` | Async file operations |
| `tokio::net` | Async TCP/UDP |

## Concurrency Patterns

### `tokio::join!` — Run Concurrently, Wait for All

```rust
async fn fetch_user(id: u64) -> User { /* ... */ }
async fn fetch_orders(id: u64) -> Vec<Order> { /* ... */ }

async fn load_dashboard(user_id: u64) {
    // Both requests run concurrently
    let (user, orders) = tokio::join!(
        fetch_user(user_id),
        fetch_orders(user_id)
    );
    println!("User: {}, Orders: {}", user.name, orders.len());
}
```

### `tokio::select!` — First to Complete Wins

```rust
use tokio::time::{sleep, Duration};

async fn slow() -> &'static str {
    sleep(Duration::from_secs(5)).await;
    "slow result"
}

async fn fast() -> &'static str {
    sleep(Duration::from_millis(100)).await;
    "fast result"
}

async fn race() {
    tokio::select! {
        result = slow() => println!("Slow won: {}", result),
        result = fast() => println!("Fast won: {}", result),
    }
    // Prints: "Fast won: fast result"
}
```

## Pin and Unpin

`Pin` ensures that a value cannot be moved in memory. This is essential for self-referential types (like async state machines):

```rust
use std::pin::Pin;
use std::future::Future;

// A pinned future
fn pinned_future() -> Pin<Box<dyn Future<Output = i32>>> {
    Box::pin(async { 42 })
}

// Most types are Unpin (can be safely moved)
// async blocks are !Unpin (self-referential)
```

**Why Pin exists:** When an `async` block is compiled to a state machine, it may hold references to its own fields. Moving the state machine would invalidate those references. `Pin` prevents this.

## Streams

Streams are the async equivalent of iterators:

```rust
use tokio_stream::StreamExt;
use tokio::time::{interval, Duration};

async fn count_stream() {
    let mut stream = tokio_stream::iter(vec![1, 2, 3, 4, 5]);

    while let Some(value) = stream.next().await {
        println!("Got: {}", value);
    }
}

// Interval stream
async fn tick() {
    let mut interval = interval(Duration::from_secs(1));
    let mut count = 0;

    loop {
        interval.tick().await;
        count += 1;
        println!("Tick {}", count);
        if count >= 5 { break; }
    }
}
```

## Cancellation

In Rust, dropping a future cancels it. This is different from languages where cancellation requires explicit mechanisms:

```rust
async fn long_running() {
    for i in 0..1000 {
        tokio::time::sleep(Duration::from_millis(100)).await;
        println!("Step {}", i);
    }
}

async fn example() {
    let handle = tokio::spawn(long_running());

    // Cancel after 1 second
    tokio::time::sleep(Duration::from_secs(1)).await;
    handle.abort(); // Explicit cancellation

    // Or just drop the future
    let _future = long_running(); // Not awaited, dropped immediately
}
```

**Important:** Cancellation can happen at any `.await` point. Resources must be cleaned up properly:

```rust
async fn process() {
    let _guard = CleanupGuard; // RAII - cleanup on drop
    some_async_work().await;   // If cancelled here, _guard still runs
    // ...
}

struct CleanupGuard;
impl Drop for CleanupGuard {
    fn drop(&mut self) {
        println!("Cleaning up!");
    }
}
```

## Async vs Sync Comparison

| Feature | Async | Sync/Threads |
|---------|-------|-------------|
| Best for | I/O-bound | CPU-bound |
| Memory per task | ~hundreds of bytes | ~8MB stack |
| Context switch | User-space (cheap) | Kernel (expensive) |
| Max concurrent tasks | Millions | Thousands |
| Complexity | Higher (Pin, lifetimes) | Lower |
| Runtime needed | Yes (Tokio, async-std) | No (OS threads) |

## Common Mistakes

1. **Blocking in async code** — Use `tokio::task::spawn_blocking` for CPU-heavy work
2. **Not understanding that `async fn` doesn't execute until awaited** — Futures are lazy
3. **Forgetting that `tokio::spawn` requires `'static`** — Move owned data into spawned tasks
4. **Using `std::sync::Mutex` in async code** — Use `tokio::sync::Mutex` to avoid blocking
5. **Ignoring cancellation safety** — Ensure resources are cleaned up when futures are dropped

## Interview Questions

1. **How does Rust's async differ from Python's or JavaScript's?**
   Rust's async is zero-cost (compiled to state machines, no heap allocation), has no built-in runtime (you choose one), and futures are lazy (don't execute until polled). Python/JS have built-in runtimes and eagerly scheduled tasks.

2. **What is the `Future` trait?**
   `Future` has an associated `Output` type and a `poll` method. `poll` returns `Poll::Ready(value)` when complete or `Poll::Pending` when not ready. The runtime calls `poll` repeatedly.

3. **What is `Pin` and why is it needed?**
   `Pin` prevents values from being moved in memory. It's needed for self-referential types (like async state machines) where moving would invalidate internal references.

4. **How do you handle cancellation in Rust async?**
   Dropping a future cancels it. Use RAII guards for cleanup. Be aware that cancellation can happen at any `.await` point.

5. **When should you use async vs threads?**
   Use async for I/O-bound tasks with many concurrent operations. Use threads for CPU-bound tasks. You can combine them with `spawn_blocking`.

## See Also

- [Ownership](./ownership.md) — Ownership rules apply in async contexts
- [Borrow Checker](./borrow-checker.md) — Borrowing across `.await` points
- [Lifetimes](./lifetimes.md) — Async lifetimes and `'static` bounds
- [Error Handling](./error-handling.md) — Error handling in async functions
