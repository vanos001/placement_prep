# Futures and Promises

## Overview

A Future (or Promise) represents a value that will be available at some point in the future. It's a handle to an asynchronous computation that may not have completed yet. Futures are the foundation of async/await and are used extensively in concurrent programming to represent pending results, compose asynchronous operations, and handle errors across async boundaries.

## Core Concepts

### Future vs Promise

```mermaid
graph TD
    FUTURE[Future: Read-only handle to pending result] --> GET["get() / .await — blocks until done"]
    FUTURE --> DONE["isDone() — check without blocking"]
    FUTURE --> CANCEL["cancel() — attempt to cancel"]

    PROMISE[Promise: Write-end that sets the result] --> SET["set(value) — fulfill the promise"]
    PROMISE --> SET_ERR["set_error(exception) — reject"]
```

- **Future**: The consumer side. You can check if it's done, wait for the result, or cancel it.
- **Promise**: The producer side. You set the result or an error.

In some languages (Java, C++), they're combined. In others (JavaScript), a Promise is the combined object.

```mermaid
graph LR
    PRODUCER[Producer] -->|Sets result| PROMISE[Promise]
    PROMISE -->|Provides handle| FUTURE[Future]
    FUTURE -->|Gets result| CONSUMER[Consumer]
```

## State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending: Created
    Pending --> Fulfilled: set(value)
    Pending --> Rejected: set_error(err)
    Pending --> Cancelled: cancel()
    Fulfilled --> [*]
    Rejected --> [*]
    Cancelled --> [*]
```

A future can be in one of four states:
- **Pending**: Computation not yet complete.
- **Fulfilled**: Computation completed successfully with a value.
- **Rejected**: Computation failed with an error.
- **Cancelled**: Computation was cancelled before completion.

## JavaScript Promises

### Creation and Consumption

```javascript
// Creating a Promise
const future = new Promise((resolve, reject) => {
    // Async operation
    setTimeout(() => {
        if (success) {
            resolve("result");     // Fulfill
        } else {
            reject(new Error("fail"));  // Reject
        }
    }, 1000);
});

// Consuming a Promise
future
    .then(result => console.log(result))    // Handle fulfillment
    .catch(error => console.error(error))   // Handle rejection
    .finally(() => console.log("done"));    // Always runs
```

### Composition

```javascript
// Sequential: chain dependent operations
fetchUser(id)
    .then(user => fetchPosts(user.id))
    .then(posts => renderPosts(posts))
    .catch(handleError);

// Parallel: wait for all
Promise.all([fetchUsers(), fetchPosts(), fetchComments()])
    .then(([users, posts, comments]) => render(users, posts, comments));

// Race: first to complete wins
Promise.race([fetchFromCDN1(), fetchFromCDN2()])
    .then(fastestResult => use(fastestResult));

// AllSettled: wait for all, don't short-circuit on error
Promise.allSettled([p1, p2, p3])
    .then(results => {
        results.forEach(r => {
            if (r.status === 'fulfilled') handleSuccess(r.value);
            else handleError(r.reason);
        });
    });

// Any: first to succeed (ignores rejections)
Promise.any([try1(), try2(), try3()])
    .then(firstSuccess => use(firstSuccess))
    .catch(err => allFailed(err));
```

### Async/Await (Syntactic Sugar)

```javascript
// Equivalent to .then() chains
async function getUserPosts(userId) {
    try {
        const user = await fetchUser(userId);
        const posts = await fetchPosts(user.id);
        return posts;
    } catch (error) {
        handleError(error);
    }
}
```

## Java CompletableFuture

```java
// Async computation
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    return expensiveComputation();
});

// Chaining
CompletableFuture<Integer> result = future
    .thenApply(s -> s.length())           // Transform
    .thenApplyAsync(len -> len * 2)       // Transform async
    .exceptionally(ex -> -1);             // Handle error

// Combining two futures
CompletableFuture<String> combined = future1.thenCombine(future2,
    (r1, r2) -> r1 + r2);

// Wait for all
CompletableFuture<Void> all = CompletableFuture.allOf(f1, f2, f3);
all.join();  // Block until all complete

// Wait for any
CompletableFuture<Object> any = CompletableFuture.anyOf(f1, f2, f3);
```

### Java Future vs CompletableFuture

| Feature | Future | CompletableFuture |
|---------|--------|-------------------|
| Blocking | get() blocks | thenApply() non-blocking |
| Composition | Manual | Built-in (thenCompose, thenCombine) |
| Error handling | try/catch on get() | exceptionally(), handle() |
| Completion callback | No | thenAccept(), thenRun() |
| Manual completion | No | complete(), completeExceptionally() |

## C++ std::future and std::promise

```cpp
#include <future>
#include <iostream>

// Create promise/future pair
std::promise<int> promise;
std::future<int> future = promise.get_future();

// Producer thread
std::thread producer([&promise] {
    // Do work...
    promise.set_value(42);  // Fulfill promise
});

// Consumer
int result = future.get();  // Blocks until promise is fulfilled
producer.join();

// std::async (creates future automatically)
std::future<int> async_result = std::async(std::launch::async, [] {
    return expensive_computation();
});
int value = async_result.get();  // Blocks until done
```

## Rust Futures

```rust
use std::future::Future;
use tokio;

// A future in Rust is a trait
// trait Future {
//     type Output;
//     fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>;
// }

// Creating futures with async/await
async fn fetch_data() -> String {
    // .await suspends until the inner future completes
    let response = reqwest::get("https://api.example.com").await.unwrap();
    response.text().await.unwrap()
}

// Combining futures
async fn process() {
    // Sequential
    let data = fetch_data().await;
    let processed = transform(data).await;

    // Concurrent
    let (a, b, c) = tokio::join!(
        fetch_a(),
        fetch_b(),
        fetch_c()
    );
}
```

## Future Composition Patterns

### Then/Map (Transform)

```mermaid
graph LR
    F1[Future A] -->|then/thenApply| F2[Future B]
    F1 -.->|transform value| F2
```

```javascript
// JavaScript
fetchUser(id).then(user => user.name);

// Java
future.thenApply(s -> s.length());

// Rust
async { fetch_user(id).await.name }
```

### FlatMap/Chain (Dependent)

```mermaid
graph LR
    F1[Future User] -->|thenCompose| F2[Future Posts]
    F1 -.->|flatmap: result feeds next| F2
```

```javascript
// JavaScript
fetchUser(id).then(user => fetchPosts(user.id));

// Java
future.thenCompose(user -> fetchPosts(user.getId()));
```

### Zip/Combine (Independent)

```mermaid
graph LR
    F1[Future A] -->|combine| F3[Future C]
    F2[Future B] -->|combine| F3
    F1 -.->|combine results| F3
    F2 -.->|combine results| F3
```

```javascript
// JavaScript
Promise.all([fetchA(), fetchB()]);

// Java
f1.thenCombine(f2, (a, b) -> a + b);
```

### Race (First Success)

```mermaid
graph LR
    F1[Future 1] -->|race| WINNER[First to complete]
    F2[Future 2] -->|race| WINNER
    F3[Future 3] -->|race| WINNER
```

## Error Handling

### Monadic Error Handling

```mermaid
graph TD
    F[Future] -->|Success| THEN[Continue chain]
    F -->|Error| CATCH[Error handler]

    THEN --> F2[Next Future]
    F2 -->|Success| THEN2[Continue]
    F2 -->|Error| CATCH2[Error handler]
```

Futures propagate errors through the chain, similar to Result/Option types:

```javascript
fetchUser(id)                        // May fail
    .then(user => fetchPosts(user.id)) // Skipped if fetchUser fails
    .then(posts => render(posts))      // Skipped if fetchPosts fails
    .catch(err => showError(err));     // Catches any error in chain
```

## Interview Questions

1. **Q: What is a Future/Promise?**
   A: A Future is a placeholder for a value that will be available later. It represents an ongoing computation. A Promise is the write-end that sets the result. Together, they decouple the producer (who sets the value) from the consumer (who waits for it).

2. **Q: What's the difference between Future, CompletableFuture, and Promise?**
   A: A basic Future is read-only and requires blocking to get the result. CompletableFuture (Java) adds non-blocking composition (thenApply, thenCombine). Promise (JavaScript) is both producer and consumer, with .then() for chaining. They all represent pending async results with different APIs.

3. **Q: How does error propagation work in futures?**
   A: Errors propagate through the chain like exceptions. In JS, a rejected promise skips .then() handlers until a .catch() is found. In Java, exceptionally() handles errors. In Rust, the ? operator propagates errors. This is monadic error handling.

4. **Q: What is the difference between Promise.all, Promise.race, and Promise.allSettled?**
   A: all() waits for all to fulfill, rejects if any rejects. race() returns the first to settle (fulfill or reject). allSettled() waits for all to settle and returns all results (both fulfilled and rejected). any() returns the first to fulfill, rejects only if all reject.

5. **Q: How do Rust futures differ from JavaScript promises?**
   A: Rust futures are lazy — they only execute when polled by a runtime (tokio). JavaScript promises are eager — they start executing immediately. Rust gives more control but requires explicit runtime. JS is simpler but less flexible.

## Common Mistakes

- Forgetting to handle errors — unhandled promise rejections cause crashes (JS) or silent failures.
- Creating the "callback hell" with nested .then() — use async/await instead.
- Blocking on a future inside an async context — defeats the purpose.
- Not cancelling long-running futures — resource leaks.
- Assuming futures are always concurrent — sequential awaits run sequentially.

## Summary

Futures/Promises represent pending asynchronous computations. They enable non-blocking composition of async operations through chaining (then/thenApply), combining (all/race/combine), and error handling (catch/exceptionally). They're the foundation of async/await in all modern languages. For interviews, understand the state machine, composition patterns, and the difference between eager (JS promises) and lazy (Rust futures) evaluation.

## Cross-References

- [Async/Await](./async-await.md) — Syntactic sugar over futures
- [Coroutines](./coroutines.md) — Implementation mechanism
- [Go Channels](./go-channels.md) — Alternative communication model
- [Concurrency Overview](./overview.md) — Fundamental concepts
- [Java Concurrency](./java.md)
- [LLM Batching](../llm/llm-serving/batching.md)
