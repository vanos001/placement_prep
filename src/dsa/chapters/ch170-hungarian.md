# Chapter 170: Hungarian Algorithm

## 1. Introduction

The **Hungarian Algorithm** (also known as the Kuhn-Munkres algorithm) solves the **assignment problem**: given *n* workers and *n* tasks, with a cost matrix `cost[i][j]` representing the cost of assigning worker *i* to task *j*, find a one-to-one assignment that minimizes (or maximizes) the total cost.

This is a classic optimization problem with deep connections to graph theory, linear programming, and combinatorial optimization. The algorithm runs in **O(n³)** time, making it practical for problems with thousands of variables.

### Why Should You Care?

- **Competitive Programming**: Assignment problems appear in ICPC, IOI, and online judges.
- **Real-World Applications**: Resource allocation, scheduling, matching markets, image processing.
- **Interview Relevance**: Demonstrates understanding of optimization, bipartite graphs, and algorithm design.
- **Foundation**: Understanding Hungarian algorithm deepens knowledge of min-cost flow, LP duality, and combinatorial optimization.

---

## 2. Problem Definition

### 2.1 The Assignment Problem

Given an *n × n* cost matrix *C*, find a permutation *π* of {1, 2, ..., n} that minimizes:

\\[\sum_{i=1}^{n} C[i][\pi(i)]\\]

Each worker is assigned exactly one task, and each task is assigned exactly one worker.

### 2.2 Bipartite Matching Perspective

The assignment problem is equivalent to finding a **minimum-weight perfect matching** in a complete bipartite graph *K_{n,n}*, where:
- Left vertices = workers
- Right vertices = tasks
- Edge weights = costs

### 2.3 Formal Statement

**Input**: An *n × n* matrix *C* where *C[i][j] ≥ 0*.

**Output**: A set of *n* pairs *(i, π(i))* such that *π* is a permutation and *Σ C[i][π(i)]* is minimized.

---

## 3. Motivation and Intuition

### 3.1 A Simple Example

Consider 3 workers and 3 tasks with the following cost matrix:

```
         Task 1  Task 2  Task 3
Worker 1    4       1       3
Worker 2    2       0       5
Worker 3    3       2       2
```

**Brute force** would check all 3! = 6 permutations. For larger *n*, this is impossible (*n!* grows astronomically).

**Greedy** (assign each worker to their cheapest available task) doesn't work:
- Worker 1 → Task 2 (cost 1)
- Worker 2 → Task 1 (cost 2)  [Task 2 already taken]
- Worker 3 → Task 3 (cost 2)
- Total: 5

But the optimal is:
- Worker 1 → Task 2 (cost 1)
- Worker 2 → Task 1 (cost 2)
- Worker 3 → Task 3 (cost 2)
- Total: 5

In this case greedy works, but consider:

```
         Task 1  Task 2
Worker 1    1       2
Worker 2    3       1
```

Greedy: Worker 1 → Task 1 (1), Worker 2 → Task 2 (1) = 2. Optimal! But:

```
         Task 1  Task 2
Worker 1    1       100
Worker 2    2       1
```

Greedy: Worker 1 → Task 1 (1), Worker 2 → Task 2 (1) = 2. Still optimal. But:

```
         Task 1  Task 2  Task 3
Worker 1    1       100     100
Worker 2    100     1       100
Worker 3    100     100     1
```

Greedy works trivially. The real challenge arises with conflicting "cheap" options:

```
         Task 1  Task 2  Task 3
Worker 1    25      40      35
Worker 2    40      60      35
Worker 3    20      40      25
```

Greedy by row: Worker 1→T1(25), Worker 2→T3(35), Worker 3→T1 CONFLICT! → Worker 3→T3 CONFLICT! → Worker 3→T2(40). Total: 25+35+40 = 100.

Optimal: Worker 1→T2(40), Worker 2→T3(35), Worker 3→T1(20) = 95.

### 3.2 Key Insight: Potential Functions

The Hungarian algorithm is based on the concept of **potentials** (also called **dual variables**). For each worker *i* we have potential *u[i]*, and for each task *j* we have potential *v[j]*.

The key invariant: for all *i, j*:
\\[u[i] + v[j] \leq C[i][j]\\]

The **reduced cost** of edge *(i, j)* is:
\\[\bar{C}[i][j] = C[i][j] - u[i] - v[j] \geq 0\\]

An assignment is optimal if and only if all assigned edges have **zero reduced cost**. The algorithm maintains potentials and iteratively improves them until a perfect matching exists on zero-cost edges.

---

## 4. The Hungarian Algorithm: Step by Step

### 4.1 High-Level Overview

1. **Initialize** potentials: *u[i] = min_j C[i][j]*, *v[j] = 0*.
2. **Build** a bipartite graph of zero-reduced-cost edges.
3. **Find** a maximum matching in this graph.
4. If matching is perfect → **done**.
5. Otherwise, **update** potentials to create new zero-cost edges.
6. **Repeat** from step 2.

### 4.2 Detailed Algorithm

```
HUNGARIAN(C):
    n = size of C
    u[0..n-1] = 0
    v[0..n-1] = 0
    p[0..n-1] = -1   // p[j] = which worker is matched to task j
    way[0..n-1] = 0

    for i = 0 to n-1:
        // Try to find an augmenting path from worker i
        p[0] = i
        j0 = 0
        minv[0..n-1] = ∞
        used[0..n-1] = false
        
        repeat:
            used[j0] = true
            i0 = p[j0]
            delta = ∞
            j1 = 0
            
            for j = 1 to n-1:
                if not used[j]:
                    cur = C[i0][j] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            
            for j = 0 to n-1:
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            
            j0 = j1
        
        until p[j0] == -1
        
        // Augment along the path
        repeat:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
        until j0 == 0
    
    // Result: p[j] is the worker assigned to task j
    // Answer: -v[0] (for minimization)
    return p, -v[0]
```

### 4.3 Walkthrough Example

Let's trace through a concrete example:

```
Cost matrix:
     T0  T1  T2
W0 [  4   1   3 ]
W1 [  2   0   5 ]
W2 [  3   2   2 ]
```

**Initialization**: u = [0, 0, 0], v = [0, 0, 0]

**Iteration i = 0** (Worker 0):
- Start: p[0] = 0, j0 = 0
- minv = [∞, ∞, ∞], used = [F, F, F]
- Process j0 = 0:
  - used[0] = true, i0 = p[0] = 0
  - For j=1: cur = C[0][1] - u[0] - v[1] = 1 - 0 - 0 = 1. minv[1] = 1, way[1] = 0
  - For j=2: cur = C[0][2] - u[0] - v[2] = 3 - 0 - 0 = 3. minv[2] = 3, way[2] = 0
  - delta = min(1, 3) = 1, j1 = 1
  - Update: u[p[0]] += 1 → u[0] = 1; v[0] -= 1 → v[0] = -1; minv[1] -= 1 = 0; minv[2] -= 1 = 2
  - j0 = 1
- Process j0 = 1:
  - used[1] = true, i0 = p[1] (still -1 at this point)

The standard implementation uses 1-indexed arrays. Cleaner version below.

**Cost matrix (1-indexed)**:
```
     j=1  j=2  j=3
i=1 [  4    1    3 ]
i=2 [  2    0    5 ]
i=3 [  3    2    2 ]
```

**Init**: u = [0,0,0,0], v = [0,0,0,0], p = [0,0,0,0]

**i = 1**:
- p[0] = 1, j0 = 0
- minv = [∞,∞,∞,∞], used = [F,F,F,F]
- j0 = 0: used[0]=T, i0 = p[0] = 1
  - j=1: cur = C[1][1]-u[1]-v[1] = 4. minv[1]=4, way[1]=0
  - j=2: cur = C[1][2]-u[1]-v[2] = 1. minv[2]=1, way[2]=0
  - j=3: cur = C[1][3]-u[1]-v[3] = 3. minv[3]=3, way[3]=0
  - delta = 1, j1 = 2
  - used[0]: u[p[0]] += 1 → u[1] = 1, v[0] -= 1 → v[0] = -1
  - not used: minv[1] = 3, minv[2] = 0, minv[3] = 2
  - j0 = 2
- j0 = 2: used[2]=T, i0 = p[2]... p[2] = 0 (unset)

The bookkeeping gets fiddly to trace by hand; the implementation below shows the canonical version with comments at each step.

---

## 5. Implementation

### 5.1 C++ Implementation

```cpp
#include <vector>
#include <algorithm>
#include <climits>
using namespace std;

/**
 * Hungarian Algorithm for minimum cost assignment.
 * 
 * Input: cost[i][j] = cost of assigning worker i to task j
 * Output: minimum total cost
 * 
 * Time: O(n^3), Space: O(n^2)
 * 
 * Uses 1-indexed internally. Converts from 0-indexed input.
 */
long long hungarian(vector<vector<long long>>& cost) {
    int n = cost.size() - 1;  // 1-indexed: rows 1..n, cols 1..n
    
    vector<long long> u(n + 1, 0), v(n + 1, 0);
    vector<int> p(n + 1, 0), way(n + 1, 0);
    
    for (int i = 1; i <= n; i++) {
        // Find augmenting path from row i
        p[0] = i;
        int j0 = 0;
        vector<long long> minv(n + 1, LLONG_MAX);
        vector<bool> used(n + 1, false);
        
        do {
            used[j0] = true;
            int i0 = p[j0];
            long long delta = LLONG_MAX;
            int j1 = 0;
            
            for (int j = 1; j <= n; j++) {
                if (!used[j]) {
                    long long cur = cost[i0][j] - u[i0] - v[j];
                    if (cur < minv[j]) {
                        minv[j] = cur;
                        way[j] = j0;
                    }
                    if (minv[j] < delta) {
                        delta = minv[j];
                        j1 = j;
                    }
                }
            }
            
            for (int j = 0; j <= n; j++) {
                if (used[j]) {
                    u[p[j]] += delta;
                    v[j] -= delta;
                } else {
                    minv[j] -= delta;
                }
            }
            
            j0 = j1;
        } while (p[j0] != 0);
        
        // Augment along the path
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0 != 0);
    }
    
    // p[j] = worker assigned to task j
    // Minimum cost = -v[0]
    return -v[0];
}

// Helper: convert 0-indexed matrix to 1-indexed
long long hungarian0(vector<vector<long long>>& cost0) {
    int n = cost0.size();
    vector<vector<long long>> cost(n + 1, vector<long long>(n + 1));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            cost[i + 1][j + 1] = cost0[i][j];
    return hungarian(cost);
}

// Also retrieve the assignment
pair<long long, vector<int>> hungarianWithAssignment(
    vector<vector<long long>>& cost) {
    int n = cost.size() - 1;
    vector<long long> u(n + 1, 0), v(n + 1, 0);
    vector<int> p(n + 1, 0), way(n + 1, 0);
    
    for (int i = 1; i <= n; i++) {
        p[0] = i;
        int j0 = 0;
        vector<long long> minv(n + 1, LLONG_MAX);
        vector<bool> used(n + 1, false);
        
        do {
            used[j0] = true;
            int i0 = p[j0];
            long long delta = LLONG_MAX;
            int j1 = 0;
            
            for (int j = 1; j <= n; j++) {
                if (!used[j]) {
                    long long cur = cost[i0][j] - u[i0] - v[j];
                    if (cur < minv[j]) {
                        minv[j] = cur;
                        way[j] = j0;
                    }
                    if (minv[j] < delta) {
                        delta = minv[j];
                        j1 = j;
                    }
                }
            }
            
            for (int j = 0; j <= n; j++) {
                if (used[j]) {
                    u[p[j]] += delta;
                    v[j] -= delta;
                } else {
                    minv[j] -= delta;
                }
            }
            j0 = j1;
        } while (p[j0] != 0);
        
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0 != 0);
    }
    
    // assignment[j] = worker assigned to task j (1-indexed)
    vector<int> assignment(n + 1);
    for (int j = 1; j <= n; j++)
        assignment[j] = p[j];
    
    return {-v[0], assignment};
}
```

### 5.2 Python Implementation

```python
from typing import List, Tuple

def hungarian(cost: List[List[int]]) -> int:
    """
    Hungarian algorithm for minimum cost perfect matching.
    
    Args:
        cost: n x n matrix (0-indexed), cost[i][j] = cost of assigning
              worker i to task j
    
    Returns:
        Minimum total assignment cost
    
    Time: O(n^3)
    """
    n = len(cost)
    # Convert to 1-indexed
    C = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(n):
            C[i + 1][j + 1] = cost[i][j]
    
    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)   # p[j] = worker matched to task j
    way = [0] * (n + 1)
    
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float('inf')] * (n + 1)
        used = [False] * (n + 1)
        
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float('inf')
            j1 = 0
            
            for j in range(1, n + 1):
                if not used[j]:
                    cur = C[i0][j] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            
            j0 = j1
            if p[j0] == 0:
                break
        
        # Augment
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    
    return -v[0]


def hungarian_with_assignment(cost: List[List[int]]) -> Tuple[int, List[int]]:
    """
    Returns (min_cost, assignment) where assignment[j] = worker for task j.
    """
    n = len(cost)
    C = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(n):
            C[i + 1][j + 1] = cost[i][j]
    
    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)
    
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float('inf')] * (n + 1)
        used = [False] * (n + 1)
        
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float('inf')
            j1 = 0
            
            for j in range(1, n + 1):
                if not used[j]:
                    cur = C[i0][j] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            
            j0 = j1
            if p[j0] == 0:
                break
        
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    
    assignment = [0] * n  # 0-indexed: assignment[task] = worker
    for j in range(1, n + 1):
        assignment[j - 1] = p[j] - 1
    
    return -v[0], assignment
```

### 5.3 Java Implementation

```java
import java.util.*;

public class HungarianAlgorithm {
    
    /**
     * Finds minimum cost perfect matching using Hungarian algorithm.
     * cost[i][j] = cost of assigning worker i to task j.
     * Time: O(n^3)
     */
    public static long hungarian(long[][] cost0) {
        int n0 = cost0.length;
        // Convert to 1-indexed
        int n = n0;
        long[][] cost = new long[n + 1][n + 1];
        for (int i = 0; i < n0; i++)
            for (int j = 0; j < n0; j++)
                cost[i + 1][j + 1] = cost0[i][j];
        
        long[] u = new long[n + 1];
        long[] v = new long[n + 1];
        int[] p = new int[n + 1];
        int[] way = new int[n + 1];
        
        for (int i = 1; i <= n; i++) {
            p[0] = i;
            int j0 = 0;
            long[] minv = new long[n + 1];
            Arrays.fill(minv, Long.MAX_VALUE);
            boolean[] used = new boolean[n + 1];
            
            do {
                used[j0] = true;
                int i0 = p[j0];
                long delta = Long.MAX_VALUE;
                int j1 = 0;
                
                for (int j = 1; j <= n; j++) {
                    if (!used[j]) {
                        long cur = cost[i0][j] - u[i0] - v[j];
                        if (cur < minv[j]) {
                            minv[j] = cur;
                            way[j] = j0;
                        }
                        if (minv[j] < delta) {
                            delta = minv[j];
                            j1 = j;
                        }
                    }
                }
                
                for (int j = 0; j <= n; j++) {
                    if (used[j]) {
                        u[p[j]] += delta;
                        v[j] -= delta;
                    } else {
                        minv[j] -= delta;
                    }
                }
                
                j0 = j1;
            } while (p[j0] != 0);
            
            do {
                int j1 = way[j0];
                p[j0] = p[j1];
                j0 = j1;
            } while (j0 != 0);
        }
        
        return -v[0];
    }
    
    /**
     * Returns both the minimum cost and the assignment.
     * assignment[j-1] = worker assigned to task j (0-indexed).
     */
    public static Result hungarianWithAssignment(long[][] cost0) {
        int n0 = cost0.length;
        int n = n0;
        long[][] cost = new long[n + 1][n + 1];
        for (int i = 0; i < n0; i++)
            for (int j = 0; j < n0; j++)
                cost[i + 1][j + 1] = cost0[i][j];
        
        long[] u = new long[n + 1];
        long[] v = new long[n + 1];
        int[] p = new int[n + 1];
        int[] way = new int[n + 1];
        
        for (int i = 1; i <= n; i++) {
            p[0] = i;
            int j0 = 0;
            long[] minv = new long[n + 1];
            Arrays.fill(minv, Long.MAX_VALUE);
            boolean[] used = new boolean[n + 1];
            
            do {
                used[j0] = true;
                int i0 = p[j0];
                long delta = Long.MAX_VALUE;
                int j1 = 0;
                
                for (int j = 1; j <= n; j++) {
                    if (!used[j]) {
                        long cur = cost[i0][j] - u[i0] - v[j];
                        if (cur < minv[j]) {
                            minv[j] = cur;
                            way[j] = j0;
                        }
                        if (minv[j] < delta) {
                            delta = minv[j];
                            j1 = j;
                        }
                    }
                }
                
                for (int j = 0; j <= n; j++) {
                    if (used[j]) {
                        u[p[j]] += delta;
                        v[j] -= delta;
                    } else {
                        minv[j] -= delta;
                    }
                }
                j0 = j1;
            } while (p[j0] != 0);
            
            do {
                int j1 = way[j0];
                p[j0] = p[j1];
                j0 = j1;
            } while (j0 != 0);
        }
        
        int[] assignment = new int[n];
        for (int j = 1; j <= n; j++)
            assignment[j - 1] = p[j] - 1;
        
        return new Result(-v[0], assignment);
    }
    
    static class Result {
        long cost;
        int[] assignment;
        Result(long cost, int[] assignment) {
            this.cost = cost;
            this.assignment = assignment;
        }
    }
}
```

---

## 6. Complexity Analysis

| Aspect | Complexity |
|--------|-----------|
| **Time** | O(n³) |
| **Space** | O(n²) for cost matrix, O(n) for auxiliary arrays |

### Why O(n³)?

- Outer loop runs *n* times (one per worker).
- Each iteration finds an augmenting path, which scans all *n* columns.
- The inner path-finding may visit up to *n* vertices.
- Total: *n × n × n = n³*.

### Comparison with Alternatives

| Method | Time | Notes |
|--------|------|-------|
| Brute force | O(n! × n) | Try all permutations |
| Min-cost max-flow | O(n³ × log n) or O(n⁴) | Using successive shortest paths |
| **Hungarian** | **O(n³)** | **Optimal for dense matrices** |
| Auction algorithm | O(n² × log n) amortized | Better for sparse, parallelizable |

---

## 7. Handling Maximization

To maximize instead of minimize, negate all costs or subtract from the maximum value:

```cpp
// Method 1: Negate costs
// The answer will be -hungarian(negated_cost)

// Method 2: Subtract from max
long long maxVal = *max_element(cost.begin(), cost.end(), ...);
// new_cost[i][j] = maxVal - cost[i][j]
// answer = n * maxVal - hungarian(new_cost)
```

---

## 8. Non-Square Matrices (Rectangular Assignment)

When the number of workers ≠ number of tasks (*m* workers, *n* tasks, *m < n*), pad the cost matrix with dummy rows/columns having zero cost, then run the standard algorithm.

```cpp
// Pad to make square
int sz = max(m, n);
vector<vector<long long>> padded(sz, vector<long long>(sz, 0));
for (int i = 0; i < m; i++)
    for (int j = 0; j < n; j++)
        padded[i][j] = cost[i][j];
// Run Hungarian on padded matrix
```

---

## 9. Applications

### 9.1 Image Processing
Template matching: aligning two images by finding the best pixel-to-pixel correspondence.

### 9.2 Natural Language Processing
Word alignment in machine translation: matching words between source and target sentences.

### 9.3 Economics
Matching markets: kidney exchange, school choice, resident-hospital matching.

### 9.4 Computer Vision
Multi-object tracking: matching detected objects across consecutive frames.

### 9.5 Resource Allocation
Assigning tasks to machines, jobs to workers, or frequencies to transmitters.

---

## 10. Related Problems

### 10.1 Minimum Cost Perfect Matching in Bipartite Graphs
The Hungarian algorithm is a special case of min-cost flow with unit capacities.

### 10.2 Maximum Weight Matching in General Graphs
Requires Edmonds' Blossom algorithm (see Chapter 112).

### 10.3 Minimum Cost Maximum Flow
The assignment problem can be solved via MCMF with O(n) augmentations on a bipartite graph.

---

## 11. Exercises

### Easy

1. **Basic Assignment**: Given the cost matrix below, find the minimum cost assignment:
   ```
   [2, 3, 1]
   [3, 2, 4]
   [1, 4, 3]
   ```

2. **Maximization**: Convert the following maximization problem to minimization and solve:
   ```
   [10, 5, 8]
   [7,  9, 4]
   [3,  6, 12]
   ```

3. **Non-Square**: Given 2 workers and 3 tasks, find the minimum cost assignment:
   ```
   [4, 1, 3]
   [2, 5, 1]
   ```

### Medium

4. **UVa 10888 - Warehouse**: Model the problem as an assignment and solve.

5. **Codeforces 1430G**: Implement Hungarian algorithm for a competitive programming problem.

6. **Bottleneck Assignment**: Find an assignment that minimizes the *maximum* cost among all assigned pairs (hint: binary search + Hungarian).

### Hard

7. **Dense Assignment with Updates**: Design a data structure that supports updating one row of the cost matrix and re-querying the optimal assignment efficiently.

8. **k-Assignment**: Find the *k* best distinct assignments (hint: use successive shortest path with deviation).

---

## 12. Interview Questions

1. **Q**: What is the time complexity of the Hungarian algorithm?
   **A**: O(n³), where n is the number of workers (= number of tasks).

2. **Q**: Can the Hungarian algorithm handle rectangular matrices?
   **A**: Yes, by padding with dummy rows or columns of zero cost.

3. **Q**: How does the Hungarian algorithm relate to linear programming?
   **A**: The assignment problem is an LP with integrality property. The Hungarian algorithm implicitly solves the dual LP using complementary slackness.

4. **Q**: What is the key insight behind the Hungarian algorithm?
   **A**: Maintaining feasible potentials (u, v) such that reduced costs are non-negative, and iteratively improving them to find zero-cost augmenting paths.

5. **Q**: When would you use min-cost flow instead of Hungarian?
   **A**: When the bipartite graph is sparse (not all edges exist), or when capacities are not unit, or when you need to solve a more general transportation problem.

---

## 13. Common Mistakes

1. **Off-by-one errors**: The standard implementation uses 1-indexed arrays. Be careful when converting from 0-indexed input.

2. **Integer overflow**: Costs can be large. Use `long long` in C++ and be careful with `LLONG_MAX` arithmetic.

3. **Negation for maximization**: Simply negating costs works correctly with the algorithm.

4. **Non-square matrices**: Forgetting to pad will cause incorrect results.

5. **Negative costs**: The algorithm works with negative costs as long as the cost matrix is well-defined (no -∞).

---

## 14. Cross-References

- **Chapter 29: Network Flow** — Assignment problem as a special case of min-cost flow
- **Chapter 112: Hopcroft-Karp and Blossom Algorithm** — Maximum matching in general graphs
- **Chapter 151: Linear Programming** — LP relaxation and duality
- **Chapter 162: Algorithmic Game Theory** — Matching markets and mechanism design
- **Chapter 73: Linear Algebra for Programming** — Matrix operations underlying the algorithm

---

## 15. Further Reading

- Kuhn, H. W. (1955). "The Hungarian Method for the Assignment Problem." *Naval Research Logistics Quarterly*.
- Munkres, J. (1957). "Algorithms for the Assignment and Transportation Problems." *Journal of the Society for Industrial and Applied Mathematics*.
- Burkard, R., Dell'Amico, M., & Martello, S. (2009). *Assignment Problems*. SIAM.
