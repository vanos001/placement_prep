# Banker's Algorithm

## Overview

The **Banker's Algorithm** (Dijkstra, 1965) is a deadlock avoidance algorithm. Before granting a resource request, it checks whether the resulting state is **safe** (i.e., whether all processes can eventually complete). Named after the analogy of a bank manager who only grants loans if they can satisfy all customers.

## Data Structures

For **n** processes and **m** resource types:

| Structure | Size | Description |
|-----------|------|-------------|
| `Available[m]` | m | Number of available resources per type |
| `Max[n][m]` | n×m | Maximum demand of each process |
| `Allocation[n][m]` | n×m | Currently allocated resources |
| `Need[n][m]` | n×m | Remaining need = Max - Allocation |

## Complete Example

### Initial State

```
5 processes (P0-P4), 3 resource types (A, B, C)
Total resources: A=10, B=5, C=7

         Allocation  Max      Need     Available
         A  B  C     A  B  C  A  B  C   A  B  C
P0       0  1  0     7  5  3  7  4  3
P1       2  0  0     3  2  2  1  2  2   3  3  2
P2       3  0  2     9  0  2  6  0  0
P3       2  1  1     2  2  2  0  1  1
P4       0  0  2     4  3  3  4  3  1
```

### Safety Check

```python
def is_safe(available, max_res, allocation, need, n, m):
    work = available.copy()
    finish = [False] * n
    
    # Find a process that can finish
    while True:
        found = False
        for i in range(n):
            if not finish[i] and need[i] <= work:
                # Process i can finish
                work = work + allocation[i]
                finish[i] = True
                found = True
                break
        
        if not found:
            break
    
    return all(finish)
```

### Step-by-Step Trace

```
Work = (3, 3, 2)

Iteration 1:
  P0: Need(7,4,3) <= (3,3,2)? No (A: 7>3)
  P1: Need(1,2,2) <= (3,3,2)? Yes ✓
  → Work = (3,3,2) + (2,0,0) = (5,3,2)
  → Finish: [F, T, F, F, F]

Iteration 2:
  P0: Need(7,4,3) <= (5,3,2)? No
  P2: Need(6,0,0) <= (5,3,2)? No
  P3: Need(0,1,1) <= (5,3,2)? Yes ✓
  → Work = (5,3,2) + (2,1,1) = (7,4,3)
  → Finish: [F, T, F, T, F]

Iteration 3:
  P0: Need(7,4,3) <= (7,4,3)? Yes ✓
  → Work = (7,4,3) + (0,1,0) = (7,5,3)
  → Finish: [T, T, F, T, F]

Iteration 4:
  P2: Need(6,0,0) <= (7,5,3)? Yes ✓
  → Work = (7,5,3) + (3,0,2) = (10,5,5)
  → Finish: [T, T, T, T, F]

Iteration 5:
  P4: Need(4,3,1) <= (10,5,5)? Yes ✓
  → Work = (10,5,5) + (0,0,2) = (10,5,7)
  → Finish: [T, T, T, T, T]

All finish → SAFE
Safe sequence: <P1, P3, P0, P2, P4>
```

## Resource Request Algorithm

When P_i makes a request Request_i:

```python
def request_resources(i, request, available, allocation, need, max_res):
    # Step 1: Check request <= need
    if not (request <= need[i]):
        raise Error("Exceeded maximum claim")
    
    # Step 2: Check request <= available
    if not (request <= available):
        return False  # Must wait
    
    # Step 3: Pretend to allocate
    available -= request
    allocation[i] += request
    need[i] -= request
    
    # Step 4: Check if safe
    if is_safe(available, max_res, allocation, need):
        return True  # Grant request
    else:
        # Unsafe — undo pretend
        available += request
        allocation[i] -= request
        need[i] += request
        return False  # Must wait
```

### Example Request

P1 requests (1, 0, 2):

```
1. (1,0,2) <= Need[1]=(1,2,2)? Yes
2. (1,0,2) <= Available=(3,3,2)? Yes
3. Pretend:
   Available = (3,3,2) - (1,0,2) = (2,3,0)
   Allocation[1] = (2,0,0) + (1,0,2) = (3,0,2)
   Need[1] = (1,2,2) - (1,0,2) = (0,2,0)

4. Safety check:
   Work = (2,3,0)
   
   P1: Need(0,2,0) <= (2,3,0)? Yes
     Work = (2,3,0) + (3,0,2) = (5,3,2)
   
   P3: Need(0,1,1) <= (5,3,2)? Yes
     Work = (5,3,2) + (2,1,1) = (7,4,3)
   
   P0: Need(7,4,3) <= (7,4,3)? Yes
     Work = (7,4,3) + (0,1,0) = (7,5,3)
   
   P2: Need(6,0,0) <= (7,5,3)? Yes
     Work = (7,5,3) + (3,0,2) = (10,5,5)
   
   P4: Need(4,3,1) <= (10,5,5)? Yes
     Work = (10,5,5) + (0,0,2) = (10,5,7)
   
   All finish → SAFE → GRANT REQUEST
```

## Implementation in C

```c
#include <stdbool.h>
#include <string.h>

#define N 5  // processes
#define M 3  // resource types

bool is_safe(int available[], int max_res[][M], 
             int allocation[][M], int need[][M]) {
    int work[M];
    bool finish[N] = {false};
    memcpy(work, available, sizeof(int) * M);
    
    int count = 0;
    while (count < N) {
        bool found = false;
        for (int i = 0; i < N; i++) {
            if (!finish[i]) {
                bool can_finish = true;
                for (int j = 0; j < M; j++) {
                    if (need[i][j] > work[j]) {
                        can_finish = false;
                        break;
                    }
                }
                if (can_finish) {
                    for (int j = 0; j < M; j++)
                        work[j] += allocation[i][j];
                    finish[i] = true;
                    count++;
                    found = true;
                }
            }
        }
        if (!found) break;
    }
    
    for (int i = 0; i < N; i++)
        if (!finish[i]) return false;
    return true;
}
```

## Complexity

| Operation | Time Complexity |
|-----------|----------------|
| Safety check | O(m × n²) |
| Request check | O(m × n²) |
| Space | O(n × m) |

Where n = number of processes, m = number of resource types.

## Limitations

1. **Must know Max in advance** — processes must declare maximum needs
2. **Static process set** — doesn't handle dynamic creation well
3. **Conservative** — may deny requests that wouldn't cause deadlock
4. **Overhead** — O(m×n²) per request is expensive
5. **Not used in practice** — real systems prefer resource ordering

## Interview Questions

**Q1: Walk through Banker's algorithm with an example.**

Given 5 processes, 3 resources. Maintain Available, Max, Allocation, Need. On request: check Request ≤ Need and Request ≤ Available. Pretend to allocate, run safety check (find sequence where all can finish), grant if safe.

**Q2: Why is it called the "Banker's algorithm"?**

Like a banker who only grants loans if they can satisfy all depositors. The banker (OS) ensures that after granting a request, all customers (processes) can eventually complete. If not, the request is denied (customer must wait).

**Q3: What makes a state "safe" vs "unsafe"?**

Safe: there exists a sequence where each process can obtain its maximum resources and complete. Unsafe: no such guarantee exists. Deadlock can only occur in unsafe states, but unsafe states don't always lead to deadlock.

**Q4: Why isn't Banker's algorithm used in real operating systems?**

1. Processes rarely know their maximum resource needs
2. O(m×n²) overhead per request is too high
3. The number of processes and resources changes dynamically
4. Resource ordering (prevention) is simpler and more effective

**Q5: How does Banker's algorithm relate to deadlock detection?**

The detection algorithm is similar but uses Request (current request) instead of Need (maximum remaining). Detection checks if processes can finish with current resources; avoidance checks if granting a request keeps the system safe.

## Common Mistakes

- Confusing Need with Request — Need = Max - Allocation (remaining), Request = current ask
- Forgetting to undo the "pretend" allocation when request is denied
- Not updating Need when Allocation changes
- Using Banker's for single-instance resources (simpler graph-based approach)
- Not checking both Request ≤ Need and Request ≤ Available

## Summary

- Banker's algorithm avoids deadlock by checking if a request leads to a safe state
- Safe state: all processes can complete in some sequence
- Safety check: O(m×n²) — find a completion sequence
- Must know Max resources in advance
- Not used in practice due to overhead and assumptions
- Resource ordering (prevention) is preferred

## Cross-References

- [Deadlock Avoidance](avoidance.md) — the strategy context
- [Deadlock Detection](detection.md) — similar algorithm for detection
- [Deadlock Prevention](prevention.md) — practical alternative
- [Deadlock Recovery](recovery.md) — what to do if avoidance fails
