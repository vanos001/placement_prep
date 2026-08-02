# Semaphores

## Overview

A **semaphore** is a synchronization primitive that uses an integer counter and two atomic operations: **wait** (P/dec/down) and **signal** (V/inc/up). Invented by Edsger Dijkstra in 1965, semaphores can solve a wide range of synchronization problems.

## Types of Semaphores

| Type | Counter Range | Use Case |
|------|--------------|----------|
| **Binary** | 0 or 1 | Mutual exclusion (like a mutex) |
| **Counting** | 0 to N | Resource pool (N identical resources) |

## Operations

### wait (P / down / dec)

```c
void wait(semaphore *S) {
    S->value--;
    if (S->value < 0) {
        // Add this thread to S->queue
        block();  // Sleep
    }
}
```

### signal (V / up / inc)

```c
void signal(semaphore *S) {
    S->value++;
    if (S->value <= 0) {
        // Remove a thread from S->queue
        wakeup(thread);  // Wake it up
    }
}
```

### Implementation with Queue

```c
typedef struct {
    int value;
    struct process *queue;  // Waiting processes
} semaphore;
```

**Key**: Both `wait` and `signal` must be **atomic** (implemented with spinlocks or hardware atomics).

## POSIX Semaphores

### Named Semaphores (IPC)

```c
#include <semaphore.h>
#include <fcntl.h>

// Create/open named semaphore
sem_t *sem = sem_open("/mysem", O_CREAT, 0644, 1);  // Initial value = 1

sem_wait(sem);      // P (wait)
// Critical section
sem_post(sem);      // V (signal)

sem_close(sem);
sem_unlink("/mysem");
```

### Unnamed Semaphores (Thread sync)

```c
sem_t sem;
sem_init(&sem, 0, 1);  // pshared=0 (threads), initial value=1

sem_wait(&sem);
// Critical section
sem_post(&sem);

sem_destroy(&sem);
```

## Classic Semaphore Patterns

### 1. Mutual Exclusion (Binary Semaphore)

```c
sem_t mutex;
sem_init(&mutex, 0, 1);  // Initial value = 1

sem_wait(&mutex);    // Lock
// Critical section
sem_post(&mutex);    // Unlock
```

**Note**: This is similar to a mutex but without ownership — any thread can unlock.

### 2. Signaling (Ordering)

```c
sem_t signal_sem;
sem_init(&signal_sem, 0, 0);  // Initial value = 0

// Thread A                     // Thread B
// ... work ...                 sem_wait(&signal_sem);  // Wait for A
sem_post(&signal_sem);         // Continue after A
```

### 3. Resource Pool (Counting Semaphore)

```c
sem_t pool;
sem_init(&pool, 0, 5);  // 5 resources available

// Acquire resource
sem_wait(&pool);  // Decrements counter, blocks if 0

// Use resource

// Release resource
sem_post(&pool);  // Increments counter, wakes a waiter if any
```

## Using Semaphores to Solve Sync Problems

### Producer-Consumer (Bounded Buffer)

```c
#define BUFFER_SIZE 10

sem_t empty;  // Count of empty slots (init = BUFFER_SIZE)
sem_t full;   // Count of full slots (init = 0)
sem_t mutex;  // Binary semaphore for buffer access (init = 1)
int buffer[BUFFER_SIZE];
int in = 0, out = 0;

// Producer                         // Consumer
void produce(int item) {            void consume() {
    sem_wait(&empty);                   sem_wait(&full);
    sem_wait(&mutex);                   sem_wait(&mutex);
    buffer[in] = item;                  int item = buffer[out];
    in = (in + 1) % BUFFER_SIZE;        out = (out + 1) % BUFFER_SIZE;
    sem_post(&mutex);                   sem_post(&mutex);
    sem_post(&full);                    sem_post(&empty);
}                                       return item;
                                    }
```

```mermaid
graph LR
    P[Producer] -->|wait empty| B[Buffer<br>size N]
    P -->|wait mutex| B
    B -->|signal full| C[Consumer]
    B -->|signal mutex| C
```

**Semaphores used:**
- `empty`: Starts at N, decremented by producer, incremented by consumer
- `full`: Starts at 0, decremented by consumer, incremented by producer
- `mutex`: Binary, protects buffer access

### Rendezvous (Both Threads Wait)

```c
sem_t a_arrived, b_arrived;
sem_init(&a_arrived, 0, 0);
sem_init(&b_arrived, 0, 0);

// Thread A                    // Thread B
// ... A's work ...            // ... B's work ...
sem_post(&a_arrived);         sem_post(&b_arrived);
sem_wait(&b_arrived);         sem_wait(&a_arrived);
// Both now past this point
```

## Linux Kernel Semaphores

```c
#include <linux/semaphore.h>

DECLARE_MUTEX(sem);              // Binary (init=1)
struct semaphore sem;
sema_init(&sem, 5);             // Counting (init=5)

down(&sem);                      // P (uninterruptible)
down_interruptible(&sem);        // P (interruptible by signals)
down_trylock(&sem);              // P (non-blocking)

up(&sem);                        // V
```

## Semaphore vs Mutex

| Aspect | Semaphore | Mutex |
|--------|-----------|-------|
| Owner | No ownership | Owner must unlock |
| Value | Can be > 1 | Binary (0 or 1) |
| Use | Counting, signaling | Mutual exclusion |
| Any thread can unlock | Yes | No |
| Reentrant | Counting: yes | Recursive: yes |

**Rule of thumb**: Use mutex for critical sections, semaphore for signaling and resource counting.

## Semaphore vs Condition Variable

| Aspect | Semaphore | Condition Variable |
|--------|-----------|-------------------|
| State | Counter persists | Signal lost if no waiter |
| Wait condition | Counter > 0 | Explicit predicate |
| Spurious wakeups | Not possible | Possible |
| Signal | Always wakes one | Wakes one (if any) |
| Use | Counting, ordering | Waiting for conditions |

## Implementation: Semaphore from Mutex + Condvar

```c
typedef struct {
    int value;
    pthread_mutex_t mutex;
    pthread_cond_t cond;
} semaphore_t;

void sem_init(semaphore_t *s, int value) {
    s->value = value;
    pthread_mutex_init(&s->mutex, NULL);
    pthread_cond_init(&s->cond, NULL);
}

void sem_wait(semaphore_t *s) {
    pthread_mutex_lock(&s->mutex);
    while (s->value <= 0)
        pthread_cond_wait(&s->cond, &s->mutex);
    s->value--;
    pthread_mutex_unlock(&s->mutex);
}

void sem_post(semaphore_t *s) {
    pthread_mutex_lock(&s->mutex);
    s->value++;
    pthread_cond_signal(&s->cond);
    pthread_mutex_unlock(&s->mutex);
}
```

## Interview Questions

**Q1: What is a semaphore and what are the two operations?**

A semaphore is an integer counter with two atomic operations: **wait** (P) decrements the counter and blocks if it goes below 0; **signal** (V) increments the counter and wakes a blocked thread if any. Binary semaphores (0/1) provide mutual exclusion. Counting semaphores (0 to N) manage resource pools.

**Q2: What is the difference between a binary semaphore and a mutex?**

A binary semaphore has values 0 and 1 but no ownership — any thread can signal it. A mutex has an owner: only the locking thread can unlock it. This makes mutexes safer (prevents accidental unlocks) but semaphores more flexible (can be used for signaling between threads).

**Q3: How do you implement a bounded buffer using semaphores?**

Use three semaphores: `empty` (init=N, tracks empty slots), `full` (init=0, tracks full slots), `mutex` (init=1, protects buffer). Producer: wait(empty), wait(mutex), produce, signal(mutex), signal(full). Consumer: wait(full), wait(mutex), consume, signal(mutex), signal(empty). The counting semaphores naturally block producers when full and consumers when empty.

**Q4: Why is the order of `wait` operations important in the producer-consumer problem?**

If the producer does `wait(mutex)` before `wait(empty)`, it can deadlock: it holds the mutex but is blocked on empty, while the consumer needs the mutex to consume and signal empty. Always wait on resource semaphores (`empty`, `full`) before the mutex.

**Q5: What is the difference between `down_interruptible` and `down` in the Linux kernel?**

`down()` waits uninterruptibly — the thread cannot be killed or interrupted while waiting. `down_interruptible()` can be interrupted by signals (returns `-EINTR` if interrupted). Most kernel code uses `down_interruptible()` so that processes can be killed (e.g., Ctrl+C) while waiting for a semaphore.

## Common Mistakes

- Waiting in wrong order (mutex before resource semaphore) → deadlock
- Forgetting to signal after critical section → other threads blocked forever
- Using semaphore for mutual exclusion when a mutex is more appropriate (no ownership)
- Not handling `EINTR` from `down_interruptible` in kernel code
- Signal lost if no thread is waiting (unlike condition variables, semaphore state persists)

## Summary

- Semaphores are integer counters with atomic wait/signal operations
- Binary semaphores: mutual exclusion. Counting semaphores: resource pools
- Dijkstra invented them in 1965; they solve many classic synchronization problems
- Producer-consumer, bounded buffer, rendezvous patterns
- No ownership concept — any thread can signal
- Use mutex for critical sections, semaphore for signaling and counting

## Cross-References

- [Mutexes](mutex.md) — ownership-based mutual exclusion
- [Readers-Writers](readers-writers.md) — semaphore-based solution
- [Dining Philosophers](dining-philosophers.md) — resource allocation
- [Monitors](monitors.md) — higher-level synchronization
- [Critical Section](critical-section.md) — the fundamental problem
