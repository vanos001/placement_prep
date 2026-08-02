# Deadlock Prevention

## Overview

**Deadlock prevention** eliminates one of the four Coffman conditions, making deadlock structurally impossible. It's a proactive approach — design the system so deadlock can't occur.

## Breaking Each Condition

### 1. Breaking Mutual Exclusion

**Approach**: Make resources shareable (read-only access).

```
Problem: Printers are inherently exclusive
Solution: Spooling — all print jobs go to a spool area
         Multiple processes can write to spool concurrently
         Printer daemon processes jobs one at a time
```

**Limitations**: Not all resources can be made shareable (mutexes, write access).

### 2. Breaking Hold and Wait

**Approach**: Require processes to request ALL resources at once before execution.

```c
// WRONG: Hold and wait
lock(mutex1);
// ... work ...
lock(mutex2);  // May block while holding mutex1

// CORRECT: Request all at once
acquire_all(mutex1, mutex2);  // Atomic acquire of both
// ... work ...
release_all(mutex1, mutex2);
```

**Implementation**: Use a wrapper that atomically acquires multiple locks.

```c
bool acquire_all(int n, sem_t *sems[]) {
    // Try to acquire all atomically
    for (int i = 0; i < n; i++) {
        if (try_wait(sems[i]) == FAIL) {
            // Release all acquired so far
            for (int j = 0; j < i; j++)
                signal(sems[j]);
            return false;
        }
    }
    return true;
}
```

**Drawbacks**: 
- Low resource utilization (hold all or nothing)
- Starvation possible (process may never get all resources simultaneously)

### 3. Breaking No Preemption

**Approach**: Allow resources to be forcibly taken from a process.

```c
// If a process can't get resource B:
// 1. Release resource A
// 2. Wait a bit
// 3. Try again

lock(mutex1);
if (trylock(mutex2) == FAIL) {
    unlock(mutex1);        // Preempt our own resource
    sleep(random_time);    // Back off
    retry();
}
```

**Limitations**: 
- Only works for resources whose state can be saved/restored
- Not applicable to mutexes (you can't save "lock state")

### 4. Breaking Circular Wait (Resource Ordering) ✅ Best

**Approach**: Assign a total order to resources. All processes must acquire resources in increasing order.

```c
// Define ordering: mutex1 < mutex2 < mutex3

// CORRECT: Always lock in order
lock(mutex1);
lock(mutex2);
lock(mutex3);
// ... work ...
unlock(mutex3);
unlock(mutex2);
unlock(mutex1);

// WRONG: Different order in different threads
// Thread A: lock(mutex1), lock(mutex2)  ✓
// Thread B: lock(mutex2), lock(mutex1)  ✗ → potential deadlock
```

```mermaid
graph TD
    subgraph "Without Ordering"
        T1A[Thread 1] -->|holds| M1A[Mutex 1]
        T1A -->|wants| M2A[Mutex 2]
        T2A[Thread 2] -->|holds| M2A
        T2A -->|wants| M1A
        M1A -.->|cycle| M2A
    end
    
    subgraph "With Ordering (1 < 2)"
        T1B[Thread 1] -->|holds| M1B[Mutex 1]
        T1B -->|wants| M2B[Mutex 2]
        T2B[Thread 2] -->|wants| M1B
        Note: T2B must wait for M1B first
    end
```

**This is the most practical and widely used prevention technique.**

## Lock Ordering in Practice

### Linux Kernel

The kernel defines lock ordering with lockdep:

```c
// Lock classes are assigned ordering levels
// lockdep validates that locks are always acquired in order

static DEFINE_MUTEX(mutex_a);  // Lock class 0
static DEFINE_MUTEX(mutex_b);  // Lock class 1

// Thread 1
mutex_lock(&mutex_a);   // Level 0
mutex_lock(&mutex_b);   // Level 1 ✓

// Thread 2
mutex_lock(&mutex_a);   // Level 0
mutex_lock(&mutex_b);   // Level 1 ✓

// This would trigger a lockdep warning:
// mutex_lock(&mutex_b);   // Level 1
// mutex_lock(&mutex_a);   // Level 0 ✗
```

### Address Ordering

When resources don't have natural ordering, use their memory addresses:

```c
void lock_both(pthread_mutex_t *a, pthread_mutex_t *b) {
    if (a < b) {
        pthread_mutex_lock(a);
        pthread_mutex_lock(b);
    } else {
        pthread_mutex_lock(b);
        pthread_mutex_lock(a);
    }
}
```

## Prevention vs Avoidance

| Aspect | Prevention | Avoidance |
|--------|-----------|-----------|
| When | Design time | Runtime |
| Approach | Restrict resource requests | Check before granting |
| Overhead | None (design constraint) | Runtime computation |
| Flexibility | Less flexible | More flexible |
| Example | Resource ordering | Banker's algorithm |

## Interview Questions

**Q1: What are the four conditions for deadlock and how can each be broken?**

1. **Mutual exclusion**: Make resources shareable (spooling)
2. **Hold and wait**: Request all resources at once (atomic acquire)
3. **No preemption**: Allow forced release (rollback and retry)
4. **Circular wait**: Impose resource ordering (always acquire in order)

**Q2: Why is resource ordering the most practical prevention technique?**

It has no runtime overhead (just a design rule), works with any resource type, is easy to enforce (code review, lockdep), and doesn't reduce resource utilization. Other techniques either can't be applied to all resources (mutual exclusion), waste resources (hold-and-wait), or are complex (preemption).

**Q3: How does lockdep in the Linux kernel work?**

Lockdep builds a graph of lock ordering at runtime. Each lock is assigned a "class" based on its instantiation site. It tracks which locks are held when acquiring each lock. If it detects an ordering violation (potential cycle), it prints a warning. This catches deadlock-prone patterns before they actually deadlock.

**Q4: What is the difference between deadlock prevention and avoidance?**

Prevention makes deadlock impossible by design (e.g., resource ordering). Avoidance checks at runtime whether granting a request would lead to a potentially unsafe state (e.g., Banker's algorithm). Prevention is more restrictive; avoidance is more flexible but has overhead.

**Q5: How do you prevent deadlock when acquiring locks based on runtime values?**

Use address ordering: always acquire the lock with the lower memory address first. This creates a consistent ordering even when lock identities aren't known at compile time. `if (a < b) { lock(a); lock(b); } else { lock(b); lock(a); }`

## Common Mistakes

- Not ordering ALL lock acquisitions consistently
- Using different ordering in different code paths
- Forgetting that ordering must be transitive (if A < B and B < C, then A < C)
- Not documenting the ordering (other developers may violate it)
- Assuming try-lock + retry is prevention — it's actually a form of avoidance

## Summary

- Prevention eliminates one of the four Coffman conditions
- Resource ordering (breaking circular wait) is the most practical approach
- Other techniques: spooling (mutual exclusion), atomic acquire (hold-and-wait), forced release (no preemption)
- Lockdep validates ordering at runtime in the Linux kernel
- Prevention is a design-time decision with no runtime overhead

## Cross-References

- [Deadlock Avoidance](avoidance.md) — Banker's algorithm
- [Deadlock Detection](detection.md) — finding deadlocks
- [Deadlock Recovery](recovery.md) — fixing deadlocks
- [Mutexes](../mutex.md) — common source of deadlocks
- [Banker's Algorithm](bankers.md) — avoidance algorithm
