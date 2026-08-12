# Chapter 149: Exact Exponential Algorithms

## Prerequisites
- NP-completeness and computational hardness ([Chapter 143](ch143-knowledge-aids.md))
- Bitmask DP ([Chapter 113](ch113-profile-dp.md))
- Dynamic programming fundamentals ([Chapter 109](ch109-bridge-trees-treewidth.md))
- Graph algorithms ([Chapter 120](ch120-bwt-fmindex.md))

## Interview Frequency: ★

Exact algorithms for NP-hard problems with better-than-brute-force constants. Rarely asked directly in interviews, but understanding these techniques demonstrates deep algorithmic maturity.

---

## 149.1 Definition and Motivation

When a problem is NP-hard, we know that no polynomial-time algorithm is likely to exist. But that doesn't mean we should give up and use brute force. **Exact exponential algorithms** find the optimal solution while being significantly faster than naïve enumeration.

The key question: *Can we solve an NP-hard problem in O(2^n) instead of O(n!)? Can we do O(1.27^n) instead of O(2^n)?*

### Why This Matters

| Approach | n = 20 | n = 30 | n = 40 |
|---|---|---|---|
| O(n!) brute force | 2.4 × 10¹⁸ | 2.7 × 10³² | 8.2 × 10⁴⁷ |
| O(2^n) | 1,048,576 | 1.1 × 10⁹ | 1.1 × 10¹² |
| O(1.27^n) | 103 | 1,378 | 18,526 |

The difference between "completely impossible" and "runs in milliseconds" is often just choosing the right exponential algorithm.

---

## 149.2 Subset DP (Held-Karp for TSP)

### The Problem

**Traveling Salesman Problem (TSP)**: Given n cities and distances between them, find the shortest route that visits every city exactly once and returns to the start.

- Brute force: Try all permutations → O(n!)
- Held-Karp: Use bitmask DP → O(2^n · n²)

### Intuition

Instead of thinking "which city do I visit next?", think "which **subset** of cities have I visited, and where am I now?"

**State**: `dp[mask][v]` = minimum cost to visit exactly the cities in `mask`, ending at city `v`.

**Transition**: To extend the tour, try visiting any unvisited city `u`:
```
dp[mask | (1 << u)][u] = min(dp[mask | (1 << u)][u], dp[mask][v] + dist[v][u])
```

### Step-by-Step Walkthrough

Consider 4 cities with distance matrix:
```
     A    B    C    D
A  [ 0,  10,  15,  20]
B  [10,   0,  35,  25]
C  [15,  35,   0,  30]
D  [20,  25,  30,   0]
```

**Step 1**: Initialize — start at city A.
- `dp[0001][A] = 0` (mask = 0001 means only city A visited)

**Step 2**: Visit one more city from A.
- `dp[0011][B] = dp[0001][A] + dist[A][B] = 0 + 10 = 10`
- `dp[0101][C] = dp[0001][A] + dist[A][C] = 0 + 15 = 15`
- `dp[1001][D] = dp[0001][A] + dist[A][D] = 0 + 20 = 20`

**Step 3**: Visit a third city.
- From B: `dp[0111][C] = 10 + 35 = 45`, `dp[1011][D] = 10 + 25 = 35`
- From C: `dp[0111][B] = 15 + 35 = 50`, `dp[1101][D] = 15 + 30 = 45`
- From D: `dp[1011][B] = 20 + 25 = 45`, `dp[1101][C] = 20 + 30 = 50`

After min updates: `dp[0111][C] = 45`, `dp[1011][D] = 35`, `dp[0111][B] = 50`, `dp[1101][D] = 45`, `dp[1011][B] = 45`, `dp[1101][C] = 50`

**Step 4**: Visit the last city.
- `dp[1111][D] = min(45 + 30, 50 + 25) = min(75, 75) = 75`
- `dp[1111][B] = min(35 + 35, 50 + 10) = min(70, 60) = 60`
- `dp[1111][C] = min(35 + 30, 45 + 15) = min(65, 60) = 60`

**Step 5**: Return to A.
- From D: 75 + 20 = 95
- From B: 60 + 10 = 70
- From C: 60 + 15 = 75

**Answer**: 70 (A → B → D → C → A or A → C → D → B → A)

### Code

**C++**

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

int tspHeldKarp(const std::vector<std::vector<int>>& dist) {
    int n = dist.size();
    int full = (1 << n) - 1;
    std::vector<std::vector<int>> dp(1 << n, std::vector<int>(n, INT_MAX));
    dp[1][0] = 0;
    
    for (int mask = 1; mask <= full; mask++) {
        for (int u = 0; u < n; u++) {
            if (!(mask & (1 << u)) || dp[mask][u] == INT_MAX) continue;
            for (int v = 0; v < n; v++) {
                if (mask & (1 << v)) continue;
                int next = mask | (1 << v);
                dp[next][v] = std::min(dp[next][v], dp[mask][u] + dist[u][v]);
            }
        }
    }
    
    int result = INT_MAX;
    for (int u = 1; u < n; u++)
        result = std::min(result, dp[full][u] + dist[u][0]);
    return result;
}

int main() {
    std::vector<std::vector<int>> dist = {
        {0, 10, 15, 20},
        {10, 0, 35, 25},
        {15, 35, 0, 30},
        {20, 25, 30, 0}
    };
    std::cout << "TSP (Held-Karp): " << tspHeldKarp(dist) << "\n"; // 80
    return 0;
}
```

**Python**

```python
import sys

def tsp_held_karp(dist):
    n = len(dist)
    full = (1 << n) - 1
    dp = [[float('inf')] * n for _ in range(1 << n)]
    dp[1][0] = 0
    
    for mask in range(1, full + 1):
        for u in range(n):
            if not (mask & (1 << u)) or dp[mask][u] == float('inf'):
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                nxt = mask | (1 << v)
                dp[nxt][v] = min(dp[nxt][v], dp[mask][u] + dist[u][v])
    
    return min(dp[full][u] + dist[u][0] for u in range(1, n))

dist = [[0,10,15,20],[10,0,35,25],[15,35,0,30],[20,25,30,0]]
print(f"TSP (Held-Karp): {tsp_held_karp(dist)}")  # 80
```

**Java**

```java
import java.util.*;

public class TSPHeldKarp {
    public static int tsp(int[][] dist) {
        int n = dist.length;
        int full = (1 << n) - 1;
        int[][] dp = new int[1 << n][n];
        for (int[] row : dp) Arrays.fill(row, Integer.MAX_VALUE);
        dp[1][0] = 0;
        
        for (int mask = 1; mask <= full; mask++) {
            for (int u = 0; u < n; u++) {
                if ((mask & (1 << u)) == 0 || dp[mask][u] == Integer.MAX_VALUE) continue;
                for (int v = 0; v < n; v++) {
                    if ((mask & (1 << v)) != 0) continue;
                    int next = mask | (1 << v);
                    dp[next][v] = Math.min(dp[next][v], dp[mask][u] + dist[u][v]);
                }
            }
        }
        
        int result = Integer.MAX_VALUE;
        for (int u = 1; u < n; u++)
            result = Math.min(result, dp[full][u] + dist[u][0]);
        return result;
    }
    
    public static void main(String[] args) {
        int[][] dist = {{0,10,15,20},{10,0,35,25},{15,35,0,30},{20,25,30,0}};
        System.out.println("TSP (Held-Karp): " + tsp(dist)); // 80
    }
}
```

### Complexity Analysis

| Metric | Value |
|---|---|
| **Time** | O(2^n · n²) |
| **Space** | O(2^n · n) |
| **States** | 2^n subsets × n endpoints |
| **Transitions** | n per state |

---

## 149.3 Inclusion-Exclusion for Counting

### The Problem

Count the number of Hamiltonian paths in a graph. This is #P-hard in general, but inclusion-exclusion gives us an O(2^n · n²) algorithm.

### Intuition

Instead of counting paths that visit **all** vertices, count paths that **avoid** certain vertices, then use inclusion-exclusion.

Let `f(S)` = number of paths in the subgraph induced by vertex set `S`. Then:

```
Hamiltonian paths = Σ (-1)^|V\S| · f(S)    (sum over all subsets S)
```

### Algorithm

1. For each subset `S` of vertices, compute `f(S)` using DP over subsets.
2. Use the Möbius inversion on the subset lattice.

### Code (C++)

```cpp
#include <iostream>
#include <vector>
#include <cstring>

long long countHamiltonianPaths(const std::vector<std::vector<int>>& adj, int n) {
    // dp[mask][v] = number of paths visiting exactly mask, ending at v
    std::vector<std::vector<long long>> dp(1 << n, std::vector<long long>(n, 0));
    
    for (int i = 0; i < n; i++)
        dp[1 << i][i] = 1;
    
    for (int mask = 1; mask < (1 << n); mask++) {
        for (int v = 0; v < n; v++) {
            if (!(mask & (1 << v)) || dp[mask][v] == 0) continue;
            for (int u : adj[v]) {
                if (mask & (1 << u)) continue;
                dp[mask | (1 << u)][u] += dp[mask][v];
            }
        }
    }
    
    long long total = 0;
    int full = (1 << n) - 1;
    for (int v = 0; v < n; v++)
        total += dp[full][v];
    return total;
}

int main() {
    int n = 4;
    std::vector<std::vector<int>> adj = {{1,2,3}, {0,2,3}, {0,1,3}, {0,1,2}};
    std::cout << "Hamiltonian paths in K4: " << countHamiltonianPaths(adj, n) << "\n";
    // K4 has 4! / 2 = 12 Hamiltonian paths (each path and its reverse are counted)
    return 0;
}
```

### Complexity

- **Time**: O(2^n · n²)
- **Space**: O(2^n · n)

---

## 149.4 Measure and Conquer

### The Idea

Standard analysis counts the input size `n`. **Measure and Conquer** uses a more refined measure that captures the problem's structure, often yielding tighter bounds.

### Example: Maximum Independent Set

**Brute force**: O(2^n) — try all subsets.

**Measure and Conquer analysis**:

Instead of counting vertices, measure the number of vertices with degree ≥ 1 (call it `d`). At each step, we either include a vertex (removing it and its neighbors) or exclude it (removing just it).

The recurrence becomes:
```
T(d) ≤ T(d - 1 - deg(v)) + T(d - 1)
```

Choosing the vertex with maximum degree gives:
```
T(d) ≤ O(1.1996^n)
```

This is a real improvement over O(2^n) for the same problem.

### Key Insight

The measure doesn't have to be the input size. It can be:
- Number of edges
- Number of non-isolated vertices
- A weighted sum of vertex degrees
- Any function that decreases with each recursive call

---

## 149.5 Branch and Bound

### The Idea

Branch and Bound is a general framework for exact algorithms:

1. **Branch**: Divide the problem into subproblems.
2. **Bound**: Compute a lower/upper bound for each subproblem.
3. **Prune**: Skip subproblems whose bound can't beat the best known solution.

### Example: TSP with Branch and Bound

```python
import heapq

def tsp_branch_bound(dist):
    n = len(dist)
    best = float('inf')
    
    # Priority queue: (lower_bound, cost_so_far, visited_set, current_city)
    initial_lb = sum(min(dist[i][j] for j in range(n) if i != j) for i in range(n))
    pq = [(initial_lb, 0, frozenset([0]), 0)]
    
    while pq:
        lb, cost, visited, current = heapq.heappop(pq)
        
        if lb >= best:
            continue
        
        if len(visited) == n:
            best = min(best, cost + dist[current][0])
            continue
        
        for next_city in range(n):
            if next_city in visited:
                continue
            new_cost = cost + dist[current][next_city]
            new_visited = visited | {next_city}
            
            # Compute lower bound for remaining
            remaining = set(range(n)) - new_visited
            new_lb = new_cost
            for v in remaining:
                min_edge = min(dist[v][j] for j in range(n) if j != v)
                new_lb += min_edge
            
            if new_lb < best:
                heapq.heappush(pq, (new_lb, new_cost, new_visited, next_city))
    
    return best

dist = [[0,10,15,20],[10,0,35,25],[15,35,0,30],[20,25,30,0]]
print(f"TSP (Branch & Bound): {tsp_branch_bound(dist)}")  # 80
```

### Complexity

Worst case is still exponential, but pruning can be very effective in practice.

---

## 149.6 Dynamic Programming over Subsets — General Pattern

Many NP-hard problems on small graphs can be solved with subset DP:

| Problem | State | Complexity |
|---|---|---|
| TSP | `dp[mask][v]` | O(2^n · n²) |
| Hamiltonian Path | `dp[mask][v]` | O(2^n · n²) |
| Steiner Tree | `dp[mask][v]` | O(3^n · n + 2^n · n²) |
| Graph Coloring | `dp[mask]` | O(2^n · n) |
| Feedback Vertex Set | `dp[mask]` | O(2^n · n) |

### The Pattern

```
for each subset mask of {0, 1, ..., n-1}:
    for each "endpoint" v in mask:
        for each "extension" u not in mask:
            dp[mask ∪ {u}][u] = optimize(dp[mask][v] + cost(v, u))
```

---

## 149.7 Summary

| Problem | Brute Force | Exact Algorithm | Technique |
|---|---|---|---|
| TSP | O(n!) | O(2^n · n²) | Subset DP (Held-Karp) |
| Hamiltonian Path Count | O(n! · n) | O(2^n · n²) | Subset DP |
| Vertex Cover | O(2^n) | O(1.2738^k · n) | Branching |
| Max Independent Set | O(2^n) | O(1.1996^n) | Measure & Conquer |
| Graph Coloring | O(k^n) | O(2^n · n) | Subset DP |
| Subset Sum | O(2^n) | O(2^{n/2}) | Meet in the Middle |

---

## 149.8 Exercises

### Conceptual

1. **Why is Held-Karp faster than brute force?** What structure does it exploit?
2. **Explain the difference between O(2^n) and O(1.27^n).** For n = 50, what's the ratio?
3. **What is "Measure and Conquer"?** Give an example where a non-standard measure improves the analysis.

### Implementation

4. **Implement Held-Karp** and verify it on the 4-city example. Print the optimal tour, not just the cost.
5. **Implement inclusion-exclusion counting** for Hamiltonian paths in a complete graph K_n. Verify that the result equals n!/2 for n ≥ 3.
6. **Implement Branch and Bound for TSP** and compare its performance with Held-Karp on random instances.

### Challenge

7. **Steiner Tree DP**: Design an O(3^k · n + 2^k · n²) algorithm for Steiner Tree, where k is the number of terminal vertices.
8. **Meet in the Middle for Subset Sum**: Implement an O(2^{n/2}) algorithm that splits the set in half.

---

## 149.9 Interview Questions

1. **Q**: Can TSP be solved in polynomial time?
   **A**: No, TSP is NP-hard. But the Held-Karp algorithm solves it in O(2^n · n²), much better than O(n!) brute force.

2. **Q**: What's the key idea behind Held-Karp?
   **A**: Use bitmask DP where the state is (subset of visited cities, current city). This avoids recomputing overlapping subproblems.

3. **Q**: When would you use an exact exponential algorithm instead of an approximation?
   **A**: When the input is small (n ≤ 20-25) and you need the exact optimum. Examples: VLSI design, scheduling with small job counts.

4. **Q**: What's the difference between Branch and Bound and Dynamic Programming for TSP?
   **A**: Both are exact. DP has predictable time complexity. B&B can be much faster with good bounds but has worse worst-case.

---

## 149.10 Cross-References

- **Bitmask DP**: [Chapter 113](ch113-profile-dp.md) — the foundation for subset DP techniques
- **NP-Completeness**: [Chapter 143](ch143-knowledge-aids.md) — why these problems are hard
- **Approximation Algorithms**: [Chapter 150](ch150-advanced-randomized.md) — when exact is too slow
- **Branch and Bound**: [Chapter 148](ch148-parameterized-algorithms.md) — systematic search with pruning
- **Meet in the Middle**: [Chapter 114](ch114-probability-dp.md) — O(2^{n/2}) technique
- **Dynamic Programming**: [Chapter 109](ch109-bridge-trees-treewidth.md) — general DP principles
