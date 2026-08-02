# Peterson's Algorithm

## Overview

**Peterson's Algorithm** (1981) is a software-only solution to the critical section problem for **two processes**. It satisfies all three requirements: mutual exclusion, progress, and bounded waiting. It was one of the first correct solutions and remains an important teaching example.

## The Algorithm

```c
bool flag[2] = {false, false};  // Want to enter?
int turn;                        // Whose turn is it?

void process_i(int i) {         // i = 0 or 1
    int j = 1 - i;              // The other process
    
    flag[i] = true;             // I want to enter
    turn = j;                   // But I give priority to the other
    
    while (flag[j] && turn == j);  // Wait if other wants in AND it's their turn
    
    // === CRITICAL SECTION ===
    
    flag[i] = false;            // I'm done
}
```

## How It Works

### Step-by-Step

1. Process `i` sets `flag[i] = true` (announces desire to enter)
2. Process `i` sets `turn = j` (gives priority to the other)
3. If the other process also wants in (`flag[j] == true`) AND it's their turn (`turn == j`), wait
4. Otherwise, enter critical section
5. On exit, set `flag[i] = false`

### Why It Works

**Key insight**: Both processes can't be waiting simultaneously because `turn` can only be one value at a time.

- If both set flags: `turn` is set to `j` by one and `i` by the other — the last write wins
- The process whose turn it is NOT will enter (the other is stuck waiting)
- If only one wants in: `flag[j]` is false, so it enters immediately

## Trace Example

### Scenario 1: Mutual exclusion maintained

```
Time  Process 0              Process 1              flag[0]  flag[1]  turn
─────────────────────────────────────────────────────────────────────────
 1    flag[0] = true                              true     false    ?
 2    turn = 1                                   true     false    1
 3    while(flag[1] && turn==1)                   true     false    1
      → flag[1]=false, exit loop
 4    ENTER CS                                   true     false    1
 5                       flag[1] = true           true     true     1
 6                       turn = 0                 true     true     0
 7                       while(flag[0] && turn==0) true     true     0
                        → flag[0]=true, turn=0, WAIT
 8    (in CS)                                    true     true     0
 9    flag[0] = false                            false    true     0
10                       flag[0]=false, exit loop  false    true     0
11                       ENTER CS                  false    true     0
```

### Scenario 2: Both want to enter simultaneously

```
Time  Process 0              Process 1              flag[0]  flag[1]  turn
─────────────────────────────────────────────────────────────────────────
 1    flag[0] = true                              true     false    ?
 2                       flag[1] = true           true     true     ?
 3    turn = 1                                   true     true     1
 4                       turn = 0                 true     true     0
 5    while(flag[1] && turn==1)                   true     true     0
      → turn=0, NOT 1, exit loop
 6    ENTER CS                                   true     true     0
 7                       while(flag[0] && turn==0) true     true     0
                        → flag[0]=true, turn=0, WAIT
 8    flag[0] = false                            false    true     0
 9                       flag[0]=false, exit loop  false    true     0
10                       ENTER CS                  false    true     0
```

## Proof of Correctness

### Mutual Exclusion

**Claim**: At most one process is in CS at a time.

**Proof**: Suppose both P0 and P1 are in CS. Then:
- P0 passed the while loop: `flag[1]==false` OR `turn==0`
- P1 passed the while loop: `flag[0]==false` OR `turn==1`

Since both are in CS, both have `flag[i]=true` (set before loop, not yet cleared).
So `flag[0]=true` and `flag[1]=true`.
Therefore P0 requires `turn==0` and P1 requires `turn==1`.
But `turn` can't be both 0 and 1. **Contradiction.** ∎

### Progress

**Claim**: If no process is in CS and one wants to enter, it can.

**Proof**: If only P0 wants in (`flag[1]=false`), the while condition `flag[j] && turn==j` is false (first term false). P0 enters immediately. If both want in, `turn` decides — one will enter. ∎

### Bounded Waiting

**Claim**: A process waits at most one CS entry by the other.

**Proof**: If P0 is waiting, then `flag[1]=true` and `turn=1`. P1 can enter CS. When P1 exits, it sets `flag[1]=false`. Now P0's while condition `flag[1] && turn==1` becomes false (first term). P0 enters. P0 waited for at most one CS entry. ∎

## Memory Ordering Issues

On modern CPUs with out-of-order execution, Peterson's algorithm can **fail** without memory barriers:

```c
// Without barriers, CPU may reorder:
flag[i] = true;  // May be reordered AFTER the while check
turn = j;

// Another CPU might not see the updated flag[i] due to store buffering
```

### Correct Version with Memory Barriers

```c
#include <stdatomic.h>

atomic_bool flag[2] = {false, false};
atomic_int turn;

void process_i(int i) {
    int j = 1 - i;
    
    atomic_store_explicit(&flag[i], true, memory_order_relaxed);
    atomic_store_explicit(&turn, j, memory_order_release);  // ← release barrier
    
    while (atomic_load_explicit(&flag[j], memory_order_acquire) &&  // ← acquire
           atomic_load_explicit(&turn, memory_order_relaxed) == j) {
        // busy wait
    }
    atomic_thread_fence(memory_order_acquire);  // ← acquire fence
    
    // Critical section
    
    atomic_store_explicit(&flag[i], false, memory_order_release);
}
```

## Limitations

| Limitation | Description |
|------------|-------------|
| Only 2 processes | Cannot generalize easily to N processes |
| Busy waiting | Spins CPU while waiting |
| Memory ordering | Needs barriers on modern hardware |
| Not practical | Real code uses mutexes or atomic ops |

### Generalization: Filter Algorithm (N processes)

Peterson's can be extended to N processes using N-1 "rooms" with increasing priority:

```c
int level[N] = {0};    // Level each process is at
int waiting[N] = {0};  // Who is waiting at each level

void lock(int i) {
    for (int L = 1; L < N; L++) {
        level[i] = L;
        waiting[L] = i;
        while (waiting[L] == i && 
               exists_j(level[j] >= L && j != i)) {
            // wait
        }
    }
}

void unlock(int i) {
    level[i] = 0;
}
```

## Comparison with Hardware Solutions

| Aspect | Peterson's | test_and_set | CAS |
|--------|-----------|-------------|-----|
| Busy wait | Yes | Yes | Yes |
| Bounded waiting | Yes (1 CS) | No (by default) | No (by default) |
| Processes | 2 only | N | N |
| Hardware support | None needed | Atomic instruction | Atomic instruction |
| Memory barriers | Required | Built into instruction | Built into instruction |

## Interview Questions

**Q1: Explain Peterson's algorithm and why it satisfies mutual exclusion.**

Peterson's uses two shared variables: `flag[2]` (intent) and `turn` (priority). A process sets its flag and gives priority to the other. It enters CS only if the other doesn't want in OR it's not the other's turn. Mutual exclusion holds because if both want in, `turn` can only be one value — the process with priority waits, the other enters.

**Q2: Why does Peterson's algorithm need memory barriers on modern CPUs?**

Modern CPUs can reorder memory operations. Without barriers, `flag[i]=true` might be reordered after the while check, or the store might not be visible to the other CPU due to store buffering. Release-acquire barriers ensure that the flag write is visible before the while check on the other CPU.

**Q3: What are the limitations of Peterson's algorithm?**

1. Only works for 2 processes (generalization to N is complex)
2. Busy waiting wastes CPU
3. Requires memory barriers on modern hardware
4. Not used in practice — mutexes and CAS are preferred
5. On some weakly-ordered architectures, even with barriers, correctness is tricky

**Q4: How would you extend Peterson's to N processes?**

Use the Filter Algorithm: N-1 levels, each level acts like Peterson's turn variable. A process must pass through all levels. At each level, at least one competing process is eliminated. The highest-level process enters CS. This satisfies mutual exclusion and progress but is O(N) in space and time.

**Q5: Why is `turn = j` done after `flag[i] = true` in Peterson's?**

Setting `turn = j` after `flag[i] = true` ensures that if both processes execute simultaneously, the one that writes `turn` last gives priority to the other. This prevents deadlock: if both are waiting, the last writer to `turn` will be the one that has to wait, allowing the other to enter.

## Common Mistakes

- Forgetting memory barriers on modern hardware — algorithm can fail
- Setting `turn = i` instead of `turn = j` — causes deadlock
- Assuming it generalizes to N processes without modification
- Thinking it's practical — real code uses OS-provided primitives
- Not considering weak memory ordering (ARM, RISC-V)

## Summary

- Peterson's algorithm solves the critical section problem for 2 processes using software only
- Uses `flag[2]` (intent) and `turn` (priority) to ensure mutual exclusion, progress, and bounded waiting
- Proof: mutual exclusion by contradiction on `turn`, bounded waiting by counting
- Needs memory barriers on modern CPUs due to instruction reordering
- Limitation: 2 processes only, busy waiting, not practical for real code
- Foundation for understanding more complex synchronization primitives

## Cross-References

- [Critical Section](critical-section.md) — the problem definition
- [Mutexes](mutex.md) — practical alternative
- [CAS](cas.md) — hardware primitive
- [Memory Barriers](memory-barriers.md) — preventing reordering
- [Lock-Free](lock-free.md) — non-blocking alternatives


## Cross References

- [Critical Section](../os/synchronization/critical-section.md)
- [Mutex](../os/synchronization/mutex.md)
- [Memory Barriers](../os/synchronization/memory-barriers.md)
- [CPU Architecture](../arch/cpu/README.md)
