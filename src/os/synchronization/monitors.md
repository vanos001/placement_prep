# Monitors

## Overview

A **monitor** is a high-level synchronization construct that encapsulates shared data, operations, and synchronization into a single unit. It provides mutual exclusion automatically and uses **condition variables** for signaling between threads. Monitors were proposed by C.A.R. Hoare in 1974.

## What Is a Monitor?

A monitor combines:
1. **Shared data** (private to the monitor)
2. **Procedures** that operate on the data
3. **Mutual exclusion** — only one thread can execute in the monitor at a time
4. **Condition variables** — for waiting and signaling

```
┌─────────────────────────────────────────┐
│                Monitor                   │
│                                          │
│  Shared Data:                            │
│    int count;                            │
│    buffer_t buffer[N];                   │
│                                          │
│  Procedures:                             │
│    void produce(item) {                  │
│      // Mutual exclusion guaranteed      │
│      while (full) wait(not_full);        │
│      buffer[in++] = item;                │
│      signal(not_empty);                  │
│    }                                     │
│                                          │
│    item consume() {                      │
│      while (empty) wait(not_empty);      │
│      item = buffer[out++];               │
│      signal(not_full);                   │
│      return item;                        │
│    }                                     │
│                                          │
│  Condition Variables:                    │
│    cond not_full, not_empty;             │
│                                          │
└─────────────────────────────────────────┘
```

**Key property**: At most one thread is active inside the monitor at any time.

## Condition Variables

Condition variables allow threads to **wait** for a condition and **signal** when it changes.

### Operations

| Operation | Behavior |
|-----------|----------|
| `wait(cond)` | Release monitor lock, sleep on `cond`, reacquire on wakeup |
| `signal(cond)` | Wake up one thread waiting on `cond` (if any) |
| `broadcast(cond)` | Wake up ALL threads waiting on `cond` |

### Hoare vs Mesa Semantics

| Aspect | Hoare | Mesa |
|--------|-------|------|
| After `signal` | Signaler yields to waiter | Signaler continues |
| Waiter runs | Immediately after signal | After signaler exits/re-waits |
| Predicate | Guaranteed true on wakeup | Must re-check (use `while`) |
| Implementation | Difficult | Easier (Java, pthreads use Mesa) |

**Most modern systems (Java, pthreads) use Mesa semantics.**

## Java Monitor (synchronized)

Java has built-in monitors via the `synchronized` keyword:

```java
public class BoundedBuffer {
    private final Object[] buffer = new Object[10];
    private int count = 0, in = 0, out = 0;
    
    public synchronized void produce(Object item) throws InterruptedException {
        while (count == buffer.length)
            wait();  // Release lock, wait for not_full
        buffer[in] = item;
        in = (in + 1) % buffer.length;
        count++;
        notify();  // Wake one consumer
    }
    
    public synchronized Object consume() throws InterruptedException {
        while (count == 0)
            wait();  // Release lock, wait for not_empty
        Object item = buffer[out];
        out = (out + 1) % buffer.length;
        count--;
        notify();  // Wake one producer
        return item;
    }
}
```

**`synchronized` methods** are mutually exclusive — only one thread can execute any synchronized method at a time.

### wait/notify vs wait/notifyAll

```java
// notify() - wakes ONE waiting thread
// notifyAll() - wakes ALL waiting threads

// Use notifyAll() when:
// - Multiple conditions on same monitor
// - You can't guarantee the right thread is woken

public synchronized void put(Object item) throws InterruptedException {
    while (count == buffer.length)
        wait();
    // ... add item ...
    notifyAll();  // Safe: wake everyone, they re-check conditions
}
```

## POSIX Threads (pthreads) Monitor Pattern

```c
#include <pthread.h>

typedef struct {
    pthread_mutex_t mutex;
    pthread_cond_t not_full;
    pthread_cond_t not_empty;
    int buffer[10];
    int count, in, out;
} monitor_t;

void produce(monitor_t *m, int item) {
    pthread_mutex_lock(&m->mutex);
    while (m->count == 10)
        pthread_cond_wait(&m->not_full, &m->mutex);
    m->buffer[m->in] = item;
    m->in = (m->in + 1) % 10;
    m->count++;
    pthread_cond_signal(&m->not_empty);
    pthread_mutex_unlock(&m->mutex);
}

int consume(monitor_t *m) {
    pthread_mutex_lock(&m->mutex);
    while (m->count == 0)
        pthread_cond_wait(&m->not_empty, &m->mutex);
    int item = m->buffer[m->out];
    m->out = (m->out + 1) % 10;
    m->count--;
    pthread_cond_signal(&m->not_full);
    pthread_mutex_unlock(&m->mutex);
    return item;
}
```

## Condition Variable: Why `while` Not `if`?

```java
// WRONG (Hoare-style thinking)
if (count == 0)
    wait();
// Another thread might have consumed the item between signal and our wakeup!

// CORRECT (Mesa-style)
while (count == 0)
    wait();
// Re-check after wakeup — item might be gone
```

This is called **spurious wakeup** protection.

## Monitor Implementation with Semaphores

```c
sem_t mutex;     // Binary, init=1 — monitor lock
sem_t next;      // Binary, init=0 — for signaler to wait
int next_count = 0;  // Threads waiting on 'next'

// Enter monitor
wait(mutex);

// wait(cond):
//   cond->count++;
//   if (next_count > 0) signal(next); else signal(mutex);
//   wait(cond->sem);
//   cond->count--;

// signal(cond):
//   if (cond->count > 0) {
//       next_count++;
//       signal(cond->sem);
//       wait(next);       // Signaler waits for waiter to proceed
//       next_count--;
//   }

// Exit monitor
if (next_count > 0) signal(next); else signal(mutex);
```

## Comparison with Other Primitives

| Feature | Monitor | Mutex + Condvar | Semaphore |
|---------|---------|-----------------|-----------|
| Encapsulation | Yes (data + ops) | No | No |
| Mutual exclusion | Automatic | Manual lock/unlock | Manual wait/post |
| Signaling | Built-in condition vars | Separate condvar | signal/wait |
| Language support | Java, C#, Python | C (pthreads) | C, kernel |
| Ease of use | High | Medium | Low-Medium |

## Dining Philosophers with Monitors

```java
public class DiningTable {
    enum State { THINKING, HUNGRY, EATING }
    private State[] state = new State[5];
    private Condition[] self = new Condition[5];
    
    public DiningTable() {
        for (int i = 0; i < 5; i++) {
            state[i] = State.THINKING;
            self[i] = lock.newCondition();
        }
    }
    
    public synchronized void pickup(int i) throws InterruptedException {
        state[i] = State.HUNGRY;
        test(i);
        while (state[i] != State.EATING)
            self[i].await();
    }
    
    public synchronized void putdown(int i) {
        state[i] = State.THINKING;
        test((i + 4) % 5);  // Check left neighbor
        test((i + 1) % 5);  // Check right neighbor
    }
    
    private void test(int i) {
        if (state[(i+4)%5] != State.EATING &&
            state[i] == State.HUNGRY &&
            state[(i+1)%5] != State.EATING) {
            state[i] = State.EATING;
            self[i].signal();
        }
    }
}
```

## Interview Questions

**Q1: What is a monitor and how does it differ from a mutex?**

A monitor is a high-level construct that encapsulates shared data, operations, and synchronization. It provides automatic mutual exclusion (only one thread active inside) and condition variables for waiting/signaling. A mutex is a low-level lock — you must manually lock/unlock. Monitors are easier to use correctly because synchronization is built into the structure.

**Q2: Why must you use `while` instead of `if` when waiting on a condition variable?**

With Mesa semantics (used by Java and pthreads), after `signal`, the signaled thread doesn't run immediately — the signaler continues. By the time the signaled thread runs, the condition might no longer be true (another thread might have changed state). Using `while` re-checks the condition after wakeup, handling spurious wakeups correctly.

**Q3: What is the difference between Hoare and Mesa monitor semantics?**

Hoare: After `signal`, the signaled thread runs immediately, and the condition is guaranteed true. Mesa: After `signal`, the signaled thread runs later, and the condition must be re-checked. Hoare is easier to reason about but harder to implement. Mesa is what Java and pthreads use — it's simpler to implement but requires `while` loops for condition checks.

**Q4: How would you implement a monitor using semaphores?**

Use a binary semaphore for the monitor lock (init=1), a semaphore per condition variable (init=0), and a counter for each condition tracking waiting threads. On `wait`: increment condition count, release monitor lock, wait on condition semaphore, reacquire monitor lock. On `signal`: if any waiters, signal their semaphore and wait on a "next" semaphore to hand off control.

**Q5: What is `notifyAll()` in Java and when should you use it?**

`notifyAll()` wakes all threads waiting on the monitor's condition. Use it when you have multiple conditions or can't guarantee that `notify()` will wake the right thread. For example, if producers and consumers both wait on the same monitor, `notify()` might wake a producer when a consumer is needed. `notifyAll()` ensures everyone re-checks.

## Common Mistakes

- Using `if` instead of `while` for condition checks (spurious wakeups)
- Calling `wait()` without holding the monitor lock (IllegalMonitorStateException in Java)
- Using `notify()` when multiple conditions exist — might wake wrong thread
- Forgetting that `signal()` doesn't give up the monitor lock in Mesa semantics
- Not making shared data private to the monitor (breaks encapsulation)

## Summary

- Monitors encapsulate data + operations + synchronization
- Mutual exclusion is automatic — one thread at a time inside
- Condition variables provide wait/signal for inter-thread communication
- Mesa semantics (re-check conditions with `while`) is standard in modern languages
- Java's `synchronized` + `wait/notify` is a built-in monitor
- pthreads implements monitors via mutex + condition variable pairs

## Cross-References

- [Mutexes](mutex.md) — the lock underlying monitors
- [Semaphores](semaphores.md) — alternative synchronization primitive
- [Readers-Writers](readers-writers.md) — monitor-based solution
- [Dining Philosophers](dining-philosophers.md) — monitor-based solution
- [Critical Section](critical-section.md) — the problem being solved
