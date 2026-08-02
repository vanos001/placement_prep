# Concurrency Overview

## Introduction

Concurrency is the ability of a system to handle multiple tasks simultaneously. It's one of the most important topics in systems programming and a favorite in placement interviews. Concurrency enables better resource utilization, higher throughput, and responsive applications — but it also introduces subtle bugs like race conditions, deadlocks, and starvation.

## Concurrency vs Parallelism

```mermaid
graph TD
    subgraph Concurrency[Concurrency - Dealing with many things at once]
        C1[Task A] --> C2[Task B] --> C3[Task A] --> C4[Task C]
    end
    subgraph Parallelism[Parallelism - Doing many things at once]
        P1[Core 1: Task A]
        P2[Core 2: Task B]
        P3[Core 3: Task C]
    end
```

- **Concurrency**: Structuring a program to handle multiple tasks. Tasks may interleave on a single core.
- **Parallelism**: Actually executing multiple tasks simultaneously on multiple cores.

> "Concurrency is about dealing with lots of things at once. Parallelism is about doing lots of things at once." — Rob Pike

## Fundamental Concepts

### Processes vs Threads

```mermaid
graph TD
    subgraph Process[Process - Isolated Memory]
        T1[Thread 1] --> SHARED1[Shared: Code, Heap, Global vars]
        T2[Thread 2] --> SHARED1
        T1 --> PRIV1[Private: Stack, Registers, PC]
        T2 --> PRIV2[Private: Stack, Registers, PC]
    end
```

| Feature | Process | Thread |
|---------|---------|--------|
| Memory | Separate address space | Shared address space |
| Creation | Heavy (fork/exec) | Light (clone) |
| Communication | IPC (pipes, sockets, shared memory) | Shared variables |
| Isolation | Strong (crash isolated) | Weak (crash affects all) |
| Context Switch | Expensive (TLB flush) | Cheap |

### Shared Memory vs Message Passing

```mermaid
graph TD
    subgraph Shared[Shared Memory]
        T1[Thread 1] -->|Read/Write| MEM[Shared Memory]
        T2[Thread 2] -->|Read/Write| MEM
        MEM --> LOCK[Requires synchronization]
    end
    subgraph Message[Message Passing]
        P1[Process 1] -->|Send| CHANNEL[Channel/Queue]
        CHANNEL -->|Receive| P2[Process 2]
        CHANNEL --> SAFE[No shared state]
    end
```

## The Synchronization Problem

### Race Condition

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant MEM as Shared Counter (value = 5)
    participant T2 as Thread 2

    T1->>MEM: Read counter (5)
    T2->>MEM: Read counter (5)
    T1->>MEM: Write counter (6)
    T2->>MEM: Write counter (6)
    Note over MEM: Expected: 7, Actual: 6 (lost update!)
```

A race condition occurs when the result depends on the non-deterministic ordering of operations between threads.

### Critical Section

```mermaid
graph TD
    CODE[Thread Code] --> NC[Non-critical Section]
    CODE --> CS[Critical Section - Access shared resource]
    CS --> NC2[Non-critical Section]

    CS --> LOCK[Must be mutually exclusive]
```

The critical section is the code that accesses shared resources. Only one thread should execute it at a time.

## Synchronization Primitives

```mermaid
graph TD
    SYNC[Synchronization] --> MUTEX[Mutex - Mutual Exclusion]
    SYNC --> SEM[Semaphore - Counting Access]
    SYNC --> COND[Condition Variable - Wait for Signal]
    SYNC --> RWLOCK[Read-Write Lock - Concurrent Reads]
    SYNC --> ATOMIC[Atomic Operations - Lock-free]
    SYNC --> BARRIER[Barrier - Wait for All]
    SYNC --> SPIN[Spinlock - Busy Wait]

    MUTEX --> USE1[Protect critical section]
    SEM --> USE2[Limit concurrent access]
    COND --> USE3[Wait for condition]
    RWLOCK --> USE4[Read-heavy workloads]
    ATOMIC --> USE5[Simple operations, high contention]
    BARRIER --> USE6[Phase-based computation]
    SPIN --> USE7[Short critical sections]
```

### Mutex (Mutual Exclusion)

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant Lock as Mutex
    participant T2 as Thread 2

    T1->>Lock: lock()
    Note over T1: In critical section
    T2->>Lock: lock() — BLOCKED
    T1->>Lock: unlock()
    Lock-->>T2: Acquired
    Note over T2: In critical section
    T2->>Lock: unlock()
```

### Semaphore

```mermaid
graph TD
    SEM[Semaphore S = N] --> DOWN[wait/down: S--, block if S < 0]
    SEM --> UP[signal/up: S++, wake blocked thread]

    BIN[Binary Semaphore: S=1] -->|Like mutex| MUTEX[But can be signaled by different thread]
    COUNT[Counting Semaphore: S=N] -->|Limit N concurrent| POOL[Resource pool access]
```

### Condition Variable

```mermaid
sequenceDiagram
    participant T1 as Thread 1 (Producer)
    participant CV as Condition Variable
    participant T2 as Thread 2 (Consumer)

    T2->>CV: wait() — releases lock, sleeps
    T1->>CV: signal() — wakes T2
    T2->>T2: Reacquires lock, checks condition
    Note over T2: Proceeds if condition met
```

## Common Concurrency Problems

### Deadlock

```mermaid
graph TD
    T1[Thread 1] -->|Holds| L1[Lock A]
    T1 -->|Waits for| L2[Lock B]
    T2[Thread 2] -->|Holds| L2
    T2 -->|Waits for| L1
    L1 -.->|Circular wait| L2
    L2 -.->|Circular wait| L1
```

**Four conditions for deadlock** (all must hold):
1. **Mutual Exclusion**: Resources can't be shared.
2. **Hold and Wait**: Thread holds resource while waiting for another.
3. **No Preemption**: Resources can't be forcibly taken.
4. **Circular Wait**: Circular chain of threads waiting for each other.

**Prevention**: Break any one condition (e.g., always acquire locks in the same order to prevent circular wait).

### Starvation

```mermaid
graph TD
    HIGH[High-priority thread] -->|Always gets lock| RES[Resource]
    LOW[Low-priority thread] -->|Never gets lock| STARVE[Starvation]
```

A thread is perpetually denied access to a resource because other threads always get priority.

### Livelock

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant T2 as Thread 2

    T1->>T2: Politely yields lock
    T2->>T1: Politely yields lock
    T1->>T2: Politely yields lock
    T2->>T1: Politely yields lock
    Note over T1,T2: Both active but no progress!
```

Threads keep responding to each other but make no progress. Like two people in a hallway who keep stepping aside in the same direction.

## Memory Models

### What You See Isn't What Happens

```mermaid
graph TD
    CODE[Source Code Order] --> COMPILER[Compiler Reordering]
    COMPILER --> CPU[CPU Reordering]
    CPU --> MEMORY[Memory System]
    MEMORY --> ACTUAL[Actual Execution Order]
```

Compilers and CPUs reorder instructions for performance. Without proper synchronization, threads may see stale or reordered values.

### Memory Barriers / Fences

```mermaid
graph LR
    BEFORE[Operations before fence] --> FENCE[Memory Fence]
    FENCE --> AFTER[Operations after fence]
    FENCE --> GUARANTEE[Guarantees ordering across fence]
```

Memory barriers prevent reordering of memory operations across the barrier. They're the foundation of lock-free programming.

## Concurrency Models

```mermaid
graph TD
    CM[Concurrency Models] --> SHARED[Shared Memory]
    CM --> MESSAGE[Message Passing]
    CM --> ACTOR[Actor Model]
    CM --> CSP[CSP - Go Channels]

    SHARED --> S1[Threads + Locks]
    SHARED --> S2[Lock-free / Atomics]
    MESSAGE --> M1[Processes + Channels]
    ACTOR --> A1[Erlang/Akka actors]
    CSP --> C1[Go goroutines + channels]
```

| Model | Languages | Shared State | Communication |
|-------|-----------|-------------|---------------|
| Threads + Locks | Java, C++, Python | Yes | Shared variables |
| Lock-free | C++, Rust | Yes (atomics) | Atomic operations |
| Actor | Erlang, Akka | No | Message passing |
| CSP (Channels) | Go | No | Typed channels |
| Async/Await | JS, Python, Rust | Depends | Futures/promises |

## Hardware Support

### Compare-and-Swap (CAS)

```mermaid
graph TD
    CAS["CAS(addr, expected, new)"] --> CHECK{Memory at addr == expected?}
    CHECK -->|Yes| SWAP[Write new, return true]
    CHECK -->|No| FAIL[Return false, don't write]
```

CAS is the fundamental atomic operation for lock-free programming. It atomically checks and updates a memory location.

### Cache Coherence (MESI Protocol)

```mermaid
graph TD
    CORE1[Core 1 Cache] <-->|Snooping| BUS[Memory Bus]
    CORE2[Core 2 Cache] <-->|Snooping| BUS
    BUS <-->|Access| MEM[Main Memory]

    MESI[MESI States] --> M[Modified: only copy, dirty]
    MESI --> E[Exclusive: only copy, clean]
    MESI --> S[Shared: multiple copies, clean]
    MESI --> I[Invalid: stale]
```

Cache coherence protocols ensure all cores see a consistent view of memory. This is why atomic operations are expensive — they require cache line invalidation across cores.

## Interview Questions

1. **Q: What is the difference between concurrency and parallelism?**
   A: Concurrency is about structuring a program to handle multiple tasks (they can interleave on one core). Parallelism is about executing multiple tasks simultaneously (requires multiple cores). You can have concurrency without parallelism (single-core with time-slicing).

2. **Q: What are the four conditions for deadlock?**
   A: Mutual exclusion (resources can't be shared), hold and wait (holding one resource while waiting for another), no preemption (resources can't be forcibly taken), and circular wait (cycle of threads waiting for each other). Break any one to prevent deadlock.

3. **Q: Explain the difference between a mutex and a semaphore.**
   A: A mutex provides mutual exclusion — only one thread can hold it at a time, and only the holder can release it. A semaphore is a counter — multiple threads can hold it simultaneously (counting semaphore), and any thread can signal it. Mutexes are for exclusive access; semaphores are for limiting concurrency.

4. **Q: What is a race condition?**
   A: A race condition occurs when the correctness of a program depends on the relative timing of threads. The outcome changes based on scheduling order. Example: two threads incrementing a shared counter without synchronization can lose updates.

5. **Q: What is the difference between shared memory and message passing concurrency?**
   A: Shared memory uses threads that read/write shared variables, requiring synchronization (locks, atomics). Message passing uses independent processes/goroutines that communicate by sending messages through channels. Message passing avoids shared state issues but requires serialization.

## Common Mistakes

- Using locks everywhere — over-synchronization kills performance. Consider lock-free or message passing.
- Not holding a lock when reading shared data — both reads AND writes need synchronization.
- Forgetting to release a lock on all code paths (including exceptions) — use RAII or `defer`.
- Assuming atomic operations are always correct — they prevent data races but not logical races.
- Ignoring memory models — what the compiler/CPU does may not match your source code order.

## Summary

Concurrency enables systems to handle multiple tasks efficiently but introduces challenges: race conditions, deadlocks, starvation. Synchronization primitives (mutexes, semaphores, condition variables, atomics) protect shared state. Different concurrency models (shared memory, message passing, actors, CSP) offer different trade-offs. For interviews, understand the synchronization problem, deadlock conditions, and the trade-offs between locks and lock-free approaches.

## Cross-References

- [Fork-Join](./fork-join.md) — Parallel task decomposition
- [Thread Pools](./thread-pools.md) — Managed thread reuse
- [Producer-Consumer](./producer-consumer.md) — Classic concurrency pattern
- [Readers-Writers](./readers-writers.md) — Shared access pattern
- [Async/Await](./async-await.md) — Asynchronous programming
- [Lock-Free](./lock-free.md) — Wait-free and lock-free algorithms
- [Go Channels](./go-channels.md) — CSP concurrency model
- [Rust Ownership](./rust-ownership.md) — Compile-time concurrency safety
- [OS Processes](../os/processes/zombie-orphan.md)
- [Interview System Design](../interview/system-design/README.md)
- [Cloud Overview](../cloud/overview.md)

