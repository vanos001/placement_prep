# Lock-Free and Wait-Free Programming

## Overview

Lock-free programming uses atomic operations instead of locks to coordinate between threads. This avoids problems like deadlocks, priority inversion, and lock contention. Lock-free algorithms guarantee system-wide progress — at least one thread makes progress in a finite number of steps. Wait-free algorithms are stronger — every thread makes progress. These techniques are used in high-performance systems, real-time applications, and kernel development.

## Why Go Lock-Free?

```mermaid
graph TD
    PROBLEMS[Problems with Locks] --> P1[Deadlock: circular wait]
    PROBLEMS --> P2[Priority inversion: low-priority holds lock]
    PROBLEMS --> P3[Convoying: lock held while thread sleeps]
    PROBLEMS --> P4[Contention: many threads, one lock]
    PROBLEMS --> P5[No progress guarantee: holder may be suspended]
```

Lock-free algorithms solve these by using atomic hardware instructions that don't block.

## Atomic Operations

### Compare-and-Swap (CAS)

```mermaid
graph TD
    CAS["CAS(address, expected, new)"] --> READ["Read current value at address"]
    READ --> COMPARE{current == expected?}
    COMPARE -->|Yes| SWAP["Write new value atomically"]
    SWAP --> SUCCESS[Return true]
    COMPARE -->|No| FAIL[Return false, don't write]
```

CAS is the fundamental building block. It atomically:
1. Reads the current value.
2. Compares it with expected.
3. If equal, writes the new value.
4. Returns whether it succeeded.

```c
// Pseudocode
bool cas(int* addr, int expected, int new_value) {
    // Hardware atomic instruction
    if (*addr == expected) {
        *addr = new_value;
        return true;
    }
    return false;
}
```

### CAS in Practice

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant T2 as Thread 2
    participant M as Memory: counter = 0

    T1->>M: Read counter = 0
    T2->>M: Read counter = 0
    T1->>M: CAS(0, 1) → Success! counter = 1
    T2->>M: CAS(0, 1) → Fail! (expected 0, got 1)
    T2->>M: Read counter = 1
    T2->>M: CAS(1, 2) → Success! counter = 2
    Note over M: Both threads contributed: final value = 2
```

### Other Atomics

| Operation | Description | Use Case |
|-----------|-------------|----------|
| `atomic_load` | Atomic read | Read shared counter |
| `atomic_store` | Atomic write | Update shared flag |
| `atomic_fetch_add` | Atomic increment | Counter |
| `atomic_fetch_or` | Atomic OR | Bit flags |
| `atomic_exchange` | Atomic swap | Set and get old value |
| `compare_exchange` | CAS | Lock-free algorithms |

### Memory Ordering

```mermaid
graph TD
    ORDER[Memory Ordering] --> RELAXED[Relaxed: no ordering constraints]
    ORDER --> ACQUIRE[Acquire: no reads/writes reordered before]
    ORDER --> RELEASE[Release: no reads/writes reordered after]
    ORDER --> ACQ_REL[Acquire-Release: both]
    ORDER --> SEQ_CST[Sequentially Consistent: strongest]
```

| Ordering | Guarantee | Use Case |
|----------|-----------|----------|
| Relaxed | Atomicity only | Counters, statistics |
| Acquire | Subsequent reads see all prior writes | Load a lock |
| Release | Prior writes are visible | Release a lock |
| Acq_Rel | Both | Read-modify-write |
| Seq_Cst | Total order across all threads | Default, strongest |

### Memory Ordering Visualized

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant T2 as Thread 2
    participant M as Shared Memory

    Note over T1,T2: Release-Acquire pair
    T1->>M: data = 42 (non-atomic)
    T1->>M: flag.store(true, Release)
    Note over T1: Release: data write visible before flag

    M->>T2: flag.load(Acquire) = true
    Note over T2: Acquire: sees data = 42
    T2->>M: data (read) = 42 ✓

    Note over T1,T2: Without Release/Acquire:<br/>T2 might see data = 0 (stale)
```

```cpp
// C++ example: Release-Acquire synchronization
#include <atomic>
#include <thread>

std::atomic<bool> flag{false};
int data = 0;

void producer() {
    data = 42;                                    // Non-atomic write
    flag.store(true, std::memory_order_release);  // Release
}

void consumer() {
    while (!flag.load(std::memory_order_acquire)) {} // Acquire
    assert(data == 42);  // Guaranteed to see 42
}
```

## Lock-Free Counter

```java
// Java AtomicInteger
AtomicInteger counter = new AtomicInteger(0);

// Lock-free increment
public void increment() {
    while (true) {
        int current = counter.get();           // Read
        int next = current + 1;
        if (counter.compareAndSet(current, next)) {  // CAS
            break;  // Success
        }
        // CAS failed, retry (another thread modified it)
    }
}
```

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant T2 as Thread 2
    participant C as Counter = 0

    T1->>C: Read current = 0
    T2->>C: Read current = 0
    T1->>C: CAS(0, 1) → Success, counter = 1
    T2->>C: CAS(0, 1) → Fail (expected 0, actual 1)
    T2->>C: Read current = 1
    T2->>C: CAS(1, 2) → Success, counter = 2
```

## Lock-Free Stack (Treiber Stack)

```mermaid
graph TD
    PUSH[Push(value)] --> READ_HEAD[Read head pointer]
    READ_HEAD --> SET_NEXT[value.next = head]
    SET_NEXT --> CAS_HEAD{"CAS(&head, old_head, &value)"}
    CAS_HEAD -->|Success| DONE[Pushed]
    CAS_HEAD -->|Fail| READ_HEAD[Retry]

    POP[Pop()] --> READ_HEAD2[Read head pointer]
    READ_HEAD2 --> READ_NEXT[new_head = head->next]
    READ_NEXT --> CAS_HEAD2{"CAS(&head, old_head, new_head)"}
    CAS_HEAD2 -->|Success| RETURN[Return old_head value]
    CAS_HEAD2 -->|Fail| READ_HEAD2[Retry]
```

```c
// Lock-free stack push
void push(Node** top, int value) {
    Node* new_node = create_node(value);
    Node* old_top;
    do {
        old_top = *top;
        new_node->next = old_top;
    } while (!CAS(top, old_top, new_node));
}

// Lock-free stack pop
int pop(Node** top) {
    Node* old_top;
    Node* new_top;
    do {
        old_top = *top;
        if (old_top == NULL) return EMPTY;
        new_top = old_top->next;
    } while (!CAS(top, old_top, new_top));
    return old_top->value;
}
```

## Lock-Free Queue (Michael-Scott Queue)

```mermaid
graph TD
    ENQ[Enqueue(value)] --> READ_TAIL[Read tail pointer]
    READ_TAIL --> CAS_NEXT{"CAS(&tail->next, NULL, new_node)"}
    CAS_NEXT -->|Success| CAS_TAIL{"CAS(&tail, old_tail, new_node)"}
    CAS_NEXT -->|Fail| READ_TAIL[Retry: help advance tail]
    CAS_TAIL -->|Done| ENQ_DONE[Enqueued]

    DEQ[Dequeue()] --> READ_HEAD[Read head pointer]
    READ_HEAD --> READ_NEXT[Read head->next]
    READ_NEXT --> CAS_HEAD{"CAS(&head, old_head, next)"}
    CAS_HEAD -->|Success| DEQ_DONE[Return value]
    CAS_HEAD -->|Fail| READ_HEAD[Retry]
```

```java
// Java ConcurrentLinkedQueue (lock-free)
ConcurrentLinkedQueue<String> queue = new ConcurrentLinkedQueue<>();
queue.offer("item");     // Lock-free enqueue
String item = queue.poll(); // Lock-free dequeue

// Internally uses CAS on head/tail pointers
```

```rust
// Rust crossbeam provides lock-free queues
use crossbeam::queue::ArrayQueue;

let queue = ArrayQueue::new(100);
queue.push("item").unwrap();  // Lock-free
let item = queue.pop();       // Lock-free
```

## ABA Problem

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant T2 as Thread 2
    participant Stack as Stack: A → B → C

    T1->>Stack: Read head = A
    T1->>T1: Suspend (preempted)
    T2->>Stack: Pop A
    T2->>Stack: Pop B
    T2->>Stack: Push A (reuses same node!)
    Note over Stack: Stack: A → C
    T1->>T1: Resume
    T1->>Stack: CAS(A, B) → SUCCESS (wrong!)
    Note over Stack: B was already popped! Corrupted!
```

The ABA problem: a value changes from A to B and back to A. CAS succeeds because it looks unchanged, but the underlying structure has changed.

### Solutions

```mermaid
graph TD
    ABA[ABA Problem] --> SOL1[Versioned pointer: add counter]
    ABA --> SOL2[Hazard pointers: protect nodes]
    ABA --> SOL3[Epoch-based reclamation]
    ABA --> SOL4[Garbage collected language (Java, C#)]

    SOL1 --> DETAIL[Pointer + version: CAS checks both]
    SOL2 --> DETAIL2[Thread announces which nodes it's accessing]
    SOL3 --> DETAIL3[Defer deletion until safe epoch]
```

**Versioned pointer** (tagged pointer):
```c
struct TaggedPointer {
    Node* ptr;
    uint64_t tag;  // Incremented on each modification
};

// CAS compares both ptr AND tag
CAS(&head, {old_ptr, old_tag}, {new_ptr, old_tag + 1});
```

**Hazard pointers**:
```cpp
// Thread announces: "I'm reading this node"
hazard_ptr.store(node, std::memory_order_release);

// Before freeing a node, check if any thread has it as hazard
if (!is_hazard(node)) {
    safe_delete(node);
} else {
    defer_delete(node);  // Retry later
}
```

## Wait-Free vs Lock-Free

```mermaid
graph TD
    GUARANTEES[Progress Guarantees] --> WAIT[Wait-free: ALL threads make progress]
    GUARANTEES --> LOCK[Lock-free: SOME thread makes progress]
    GUARANTEES --> OBSTRUCTION[Obstruction-free: progress if running alone]

    WAIT --> W1[Bounded steps per operation]
    WAIT --> W2[Hardest to implement]
    LOCK --> L1[Unbounded retries possible for individual thread]
    LOCK --> L2[System-wide progress guaranteed]
    OBSTRUCTION --> O1[Progress only without contention]
```

| Guarantee | Individual Thread | System-Wide | Complexity |
|-----------|------------------|-------------|------------|
| Wait-free | Bounded steps | Always | Very high |
| Lock-free | May starve | Always | High |
| Obstruction-free | May starve | If alone | Moderate |
| Lock-based | May deadlock | May deadlock | Low |

## Lock-Free in Practice

### C++ atomics

```cpp
#include <atomic>

std::atomic<int> counter{0};

// Lock-free increment
void increment() {
    counter.fetch_add(1, std::memory_order_relaxed);
}

// Lock-free CAS loop
void compare_and_increment(int expected) {
    while (!counter.compare_exchange_weak(
        expected,
        expected + 1,
        std::memory_order_release,
        std::memory_order_relaxed)) {
        // expected is updated on failure
    }
}

// compare_exchange_weak may spuriously fail (faster on some archs)
// compare_exchange_strong never spurious fails (but slower loop body)
```

### Java Lock-Free Collections

```java
// ConcurrentHashMap uses lock-free reads + CAS for updates
ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();
map.put("key", 1);  // Internally uses CAS

// LongAdder: high-throughput counter (uses cells to reduce contention)
LongAdder counter = new LongAdder();
counter.increment();  // Low contention even with many threads

// StampedLock: optimistic reading
StampedLock lock = new StampedLock();
long stamp = lock.tryOptimisticRead();
// ... read shared data ...
if (!lock.validate(stamp)) {
    // Data changed, fall back to read lock
    stamp = lock.readLock();
    try { /* re-read */ } finally { lock.unlockRead(stamp); }
}
```

### Rust atomics

```rust
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

fn increment() {
    COUNTER.fetch_add(1, Ordering::Relaxed);
}

fn compare_and_swap(expected: usize, new: usize) -> bool {
    COUNTER.compare_exchange(expected, new, Ordering::AcqRel, Ordering::Relaxed).is_ok()
}

// Arc<T> for shared ownership across threads
use std::sync::Arc;
let data = Arc::new(AtomicUsize::new(0));
let data_clone = Arc::clone(&data);
std::thread::spawn(move || {
    data_clone.fetch_add(1, Ordering::Relaxed);
});
```

## Performance: Lock-Free vs Locks

```mermaid
graph TD
    CONTENTION{Contention Level?} -->|Low| LOCKS[Locks may be faster]
    CONTENTION -->|High| LOCKFREE[Lock-free often faster]

    LOCKS --> L1[Simple, fast when uncontended]
    LOCKS --> L2[OS blocking for long waits]

    LOCKFREE --> LF1[CAS retry loop burns CPU]
    LOCKFREE --> LF2[No blocking, no OS overhead]
    LOCKFREE --> LF3[Linearizable, composable]
```

Lock-free isn't always faster. Under low contention, a simple mutex can outperform CAS retry loops. Lock-free shines under high contention or when you need progress guarantees.

## Interview Questions

1. **Q: What is the difference between lock-free and wait-free?**
   A: Lock-free guarantees that at least one thread makes progress in a finite number of steps (system-wide progress). Wait-free guarantees every thread makes progress (individual progress). Wait-free is stronger but much harder to implement.

2. **Q: What is the ABA problem?**
   A: A value changes from A to B back to A. CAS succeeds because the value looks unchanged, but the underlying structure may have changed. Solutions: versioned pointers (tag + pointer), hazard pointers, or garbage-collected languages.

3. **Q: How does Compare-and-Swap (CAS) work?**
   A: CAS atomically reads a memory location, compares it with an expected value, and if equal, writes a new value. It returns whether the swap succeeded. If another thread modified the value between read and CAS, the CAS fails and the algorithm retries.

4. **Q: When should you use lock-free data structures vs locks?**
   A: Use lock-free when you need progress guarantees (real-time systems), when lock contention is very high, or when you need to avoid deadlocks. Use locks when the code is simpler, contention is low, and you don't need progress guarantees.

5. **Q: What is memory ordering in atomics?**
   A: Memory ordering controls how atomic operations interact with non-atomic memory accesses. Relaxed: no ordering. Acquire: subsequent reads see prior writes. Release: prior writes are visible. Seq_Cst: total order. Wrong ordering can cause subtle bugs.

6. **Q: Why might lock-free be slower than locks under low contention?**
   A: CAS retry loops consume CPU even when there's no contention. A simple mutex has almost zero overhead when uncontended (just an atomic flag set). Lock-free benefits appear under high contention where locks cause OS-level blocking.

7. **Q: What are hazard pointers?**
   A: A safe memory reclamation technique. Each thread publishes which nodes it's currently reading. Before freeing a node, a thread checks all hazard pointers. If any thread is reading the node, deletion is deferred. This solves ABA without garbage collection.

## Common Mistakes

- Using CAS for complex data structures without handling ABA.
- Wrong memory ordering — Relaxed when you need Acquire/Release.
- Assuming lock-free is always faster — under low contention, locks can be faster.
- Not handling CAS retry loops efficiently — exponential backoff helps.
- Mixing atomics and non-atomics on the same data — causes data races.

## Summary

Lock-free programming uses atomic operations (especially CAS) instead of locks. It guarantees system-wide progress, avoids deadlocks, and can handle high contention. The ABA problem is a key challenge, solved by versioned pointers or safe memory reclamation. Wait-free algorithms are stronger but harder to implement. For interviews, understand CAS, the ABA problem, memory ordering, and when lock-free outperforms locks.

## References

- [C++ Memory Model](https://en.cppreference.com/w/cpp/atomic/memory_order)
- [Java Concurrent Package](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/package-summary.html)
- [Rust Atomics and Locks (Mara Bos)](https://marabos.nl/atomics/)
- [Lock-Free Data Structures (Dmitry Vyukov)](https://www.1024cores.net/home/lock-free-algorithms)
- [Hazard Pointers (Maged Michael)](https://www.cs.otago.ac.nz/cosc440/readings/hazard-pointers.pdf)
- [crossbeam (Rust lock-free utilities)](https://github.com/crossbeam-rs/crossbeam)

## Cross-References

- [Concurrency Overview](./overview.md) — Synchronization primitives
- [Java Concurrency](./java.md) — AtomicInteger, ConcurrentHashMap
- [Rust Ownership](./rust-ownership.md) — Safe concurrent access
- [Thread Pools](./thread-pools.md) — Higher-level concurrency
