# Concurrency Basics

> Concurrency is about *dealing with* many things at once. Parallelism is about *doing* many things at once. — Rob Pike

## 1. Threads, Processes, and Coroutines

| Concept | Unit | Memory | Overhead | Communication | Examples |
|---------|------|--------|----------|---------------|----------|
| **Process** | OS-scheduled | Isolated (own address space) | High (MBs) | IPC: pipes, sockets, shared mem | Chrome tabs, `fork()` |
| **Thread** | OS-scheduled (typically) | Shared within process | Medium (KBs for stack) | Shared memory (needs sync) | Java threads, pthreads |
| **Coroutine** | Language-runtime scheduled | Shared within process | Low (hundreds of bytes) | Often implicit (channels, `yield`) | Python `async`, Go goroutines, Kotlin coroutines |

### Key Differences

```python
import threading
import multiprocessing
import asyncio

# Thread — shared memory, GIL-bound in CPython
thread = threading.Thread(target=task)

# Process — separate memory, true parallelism in Python
process = multiprocessing.Process(target=task)

# Coroutine — cooperative scheduling, single thread
async def task():
    await asyncio.sleep(1)
```

```go
// Goroutine — lightweight (starts at ~2KB stack, grows as needed)
go func() {
    fmt.Println("concurrent work")
}()
```

## 2. Race Conditions

A **race condition** occurs when the output depends on the non-deterministic ordering of operations by multiple threads.

```python
import threading

counter = 0

def increment():
    global counter
    for _ in range(1_000_000):
        counter += 1  # NOT atomic: read → increment → write

t1 = threading.Thread(target=increment)
t2 = threading.Thread(target=increment)
t1.start(); t2.start()
t1.join(); t2.join()

print(counter)  # Expected: 2_000_000 | Actual: often ~1_200_000
```

The `counter += 1` operation is three steps: read the value, add one, write back. Two threads can interleave:

```
Thread 1: read counter (0) → add 1 (1)
Thread 2:              read counter (0) → add 1 (1)
Thread 1: write counter (1)
Thread 2: write counter (1)  -- lost update!
```

## 3. Deadlocks

A **deadlock** occurs when two or more threads wait indefinitely for each other to release resources.

### Classic Example: Dining Philosophers

```python
import threading

fork_a = threading.Lock()
fork_b = threading.Lock()

def philosopher_1():
    with fork_a:          # grabs fork A
        with fork_b:      # waits for fork B
            eat()

def philosopher_2():
    with fork_b:          # grabs fork B
        with fork_a:      # waits for fork A — DEADLOCK
            eat()
```

### Four Necessary Conditions (Coffman)

All four must hold simultaneously for a deadlock:

| Condition | Description | Mitigation |
|-----------|-------------|------------|
| **Mutual Exclusion** | Only one thread holds a resource | Use lock-free data structures |
| **Hold and Wait** | Thread holds a resource while waiting for another | Acquire all locks atomically |
| **No Preemption** | Resources cannot be forcibly taken | Use `try_lock()` with timeout |
| **Circular Wait** | Circular chain of waiting threads | Acquire locks in a fixed global order |

## 4. Synchronization Primitives

### Mutex (Mutual Exclusion)

Guarantees exclusive access to a shared resource.

```rust
use std::sync::Mutex;
use std::thread;

let counter = Mutex::new(0);
let mut handles = vec![];

for _ in 0..10 {
    let c = counter.lock().unwrap();
    handles.push(thread::spawn(move || {
        let mut num = c.lock().unwrap();
        *num += 1;
    }));
}
```

### Semaphore

Controls access to a resource with a fixed number of permits.

```
Semaphore(n=3) — allows 3 threads concurrently

acquire()  // decrements count; blocks if count == 0
release()  // increments count; wakes a waiting thread
```

Use cases: connection pool limiting (e.g., max 10 DB connections), rate limiting.

### Condition Variable

Allows threads to wait until a condition is met.

```python
import threading

condition = threading.Condition()
queue = []

def producer():
    with condition:
        queue.append(item)
        condition.notify()  # wake one consumer

def consumer():
    with condition:
        while not queue:        # must use while (spurious wakeup)
            condition.wait()    # releases lock, waits
        item = queue.pop(0)
```

| Primitive | Purpose | Can it block? |
|-----------|---------|---------------|
| Mutex | Exclusive access to one resource | Yes (on lock) |
| Semaphore | Access to N identical resources | Yes (on acquire) |
| Condition Var | Wait for an arbitrary condition | Yes (on wait) |
| Read-Write Lock | Multiple readers OR one writer | Yes |

## 5. Atomic Operations

Atomics are hardware-supported operations that are **indivisible** — no thread can observe a partial update.

```c
// C11 atomics
#include <stdatomic.h>
atomic_int counter = ATOMIC_VAR_INIT(0);
atomic_fetch_add(&counter, 1);  // atomic increment
```

```rust
use std::sync::atomic::{AtomicU64, Ordering};

let counter = AtomicU64::new(0);
counter.fetch_add(1, Ordering::SeqCst);  // atomic increment
```

| Operation | Description |
|-----------|-------------|
| `fetch_add` / `fetch_sub` | Atomic increment/decrement |
| `compare_exchange` | CAS — compare-and-swap (foundation of lock-free algorithms) |
| `load` / `store` | Atomic read/write |

**CAS (Compare-And-Swap)** is the building block for lock-free data structures. It atomically checks if a value equals an expected value and, if so, swaps in a new value.

## 6. Thread Safety

Code is **thread-safe** if it functions correctly when executed by multiple threads simultaneously.

### Strategies for Thread Safety

| Strategy | Description | Trade-off |
|----------|-------------|-----------|
| **Immutable data** | No synchronization needed | Limited to read-heavy workloads |
| **Thread confinement** | Data only accessed by one thread | Simple but inflexible |
| **Mutex locking** | Explicit synchronization | Deadlock risk, contention overhead |
| **Atomic operations** | Lock-free for simple operations | Limited to single-word operations |
| **Message passing** | Threads communicate via channels (Go) | Avoids shared state entirely |

## Interview Questions

1. **What is the difference between concurrency and parallelism?**
   Concurrency is structuring a program so multiple tasks can make progress (interleaved). Parallelism is executing multiple tasks simultaneously on multiple cores. A single-core CPU can be concurrent but not parallel.

2. **What is a race condition? How do you prevent it?**
   A race condition occurs when the outcome depends on thread scheduling order. Prevention: use mutexes, atomics, or avoid shared mutable state entirely (message passing).

3. **What are the four conditions for deadlock?**
   Mutual exclusion, hold-and-wait, no preemption, and circular wait. All four must hold simultaneously. Break any one to prevent deadlock — e.g., always acquire locks in a fixed order to break circular wait.

4. **What is the difference between a mutex and a semaphore?**
   A mutex has ownership (only the locking thread can unlock) and protects a single resource. A semaphore has a counter, allows N concurrent accesses, and any thread can release it.

5. **When would you use a condition variable over a mutex alone?**
   Condition variables are for waiting on a *condition*, not just mutual exclusion. Use them when a thread needs to block until some state changes (e.g., queue is not empty), then get notified.

6. **What is CAS? Why is it important?**
   Compare-And-Swap: atomically compare a memory location to an expected value and swap if equal. It's the foundation of lock-free algorithms and atomic operations, enabling thread-safe updates without locks.

7. **Why must you always use a `while` loop (not `if`) with `condition.wait()`?**
   Because of **spurious wakeups** — the OS may wake a thread without any `notify()`. A `while` loop re-checks the condition, handling this correctly.

8. **What is thread confinement? Give an example.**
   Keeping data accessible by only one thread. Example: thread-local storage, the actor model (each actor processes one message at a time). It eliminates the need for synchronization for that data.
