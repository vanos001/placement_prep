# Chapter 140: Algorithm Selection Cheat Sheet

## Prerequisites
- Basic algorithm design paradigms (greedy, DP, divide and conquer)
- Graph algorithms
- Complexity analysis

## Interview Frequency: ★★★★★

Selecting the right algorithm is a critical skill for both competitive programming and technical interviews. This chapter provides a systematic approach to matching problems with optimal algorithms.

---

## 140.1 The Selection Process

When facing a problem, follow this decision tree:

1. **Identify the problem type** (search, optimization, ordering, connectivity, etc.)
2. **Check constraints** (input size determines acceptable complexity)
3. **Look for special structure** (sorted input, small values, tree structure, etc.)
4. **Consider hybrid approaches** (combine algorithms when needed)

---

## 140.2 By Problem Type

### Searching & Selection

| Problem | Algorithm | Time | Notes |
|---|---|---|---|
| Find in sorted array | Binary search | O(log n) | Classic |
| Find k-th element | Quickselect | O(n) avg | O(n²) worst case |
| Find k-th element (guaranteed) | Median of medians | O(n) | Higher constant |
| Find in 2D sorted matrix | Staircase search | O(n+m) | Rows & cols sorted |
| Find peak element | Binary search variant | O(log n) | Local maximum |

### Shortest Path

| Problem | Algorithm | Time | Notes |
|---|---|---|---|
| Unweighted graph | BFS | O(V+E) | Single source |
| Non-negative weights | Dijkstra | O((V+E)log V) | With priority queue |
| Negative edges | Bellman-Ford | O(VE) | Detects negative cycles |
| All pairs | Floyd-Warshall | O(V³) | Dense graphs |
| DAG | Topological sort + relax | O(V+E) | Single source |
| Grid with obstacles | 0-1 BFS | O(V+E) | Weights 0 or 1 |

### Graph Connectivity

| Problem | Algorithm | Time | Notes |
|---|---|---|---|
| Connected components | BFS/DFS | O(V+E) | Undirected |
| Strongly connected | Kosaraju / Tarjan | O(V+E) | Directed |
| Minimum spanning tree | Kruskal / Prim | O(E log E) | Undirected |
| Topological ordering | Kahn's / DFS | O(V+E) | DAG only |
| Bipartite check | BFS coloring | O(V+E) | 2-coloring |
| Bridge / articulation point | Tarjan's | O(V+E) | Low-link values |

### Optimization

| Problem | Algorithm | Time | Notes |
|---|---|---|---|
| Max flow | Dinic | O(V²E) | Or Edmonds-Karp O(VE²) |
| Bipartite matching | Hopcroft-Karp | O(E√V) | Max matching |
| Min cost max flow | SPFA + augment | O(VE·f) | With negative costs |
| Assignment problem | Hungarian | O(n³) | Bipartite weighted |

### String Problems

| Problem | Algorithm | Time | Notes |
|---|---|---|---|
| Single pattern match | KMP | O(n+m) | Preprocess pattern |
| Multiple pattern match | Aho-Corasick | O(n+m+z) | Automaton |
| Longest common subsequence | DP | O(nm) | Classic |
| Edit distance | DP | O(nm) | Levenshtein |
| Longest palindromic substring | Manacher | O(n) | Linear time |
| String rotation | Lyndon factorization | O(n) | See Ch. 121 |

---

## 140.3 By Constraint Size

This is the **most important** table for competitive programming. Match your algorithm's complexity to the constraint:

| n | Acceptable Complexity | Typical Algorithms |
|---|---|---|
| ≤ 10 | O(n!) | Permutation brute force, TSP |
| ≤ 20 | O(2^n) | Bitmask DP, meet-in-the-middle |
| ≤ 100 | O(n⁴) | Interval DP |
| ≤ 500 | O(n³) | Floyd-Warshall, matrix chain |
| ≤ 2,000 | O(n²) | Simple DP, Hungarian |
| ≤ 5,000 | O(n²) | Bellman-Ford, simple graph |
| ≤ 10⁵ | O(n log n) | Sorting, segment tree, Dijkstra |
| ≤ 10⁶ | O(n) | Linear scan, counting sort |
| ≤ 10⁷ | O(n) | Careful linear (watch memory) |
| ≤ 10⁹ | O(√n) | Trial division, sqrt decomposition |
| > 10⁹ | O(log n) | Binary search, math formulas |

### How to Use This Table

1. Read the problem's input size constraint (e.g., "n ≤ 10⁵")
2. Look up the row in the table
3. Choose an algorithm whose complexity fits
4. If multiple algorithms fit, prefer the simpler one

**Example:** n ≤ 10⁵, need range sum queries → O(n log n) is fine → Fenwick tree or segment tree.

**Example:** n ≤ 10⁹, need to count something → O(n) won't work → look for O(log n) or O(√n) solution.

---

## 140.4 Algorithm Design Paradigms

### When to Use Greedy

**Signs a greedy approach works:**
- Problem asks for optimal solution
- You can make a locally optimal choice that leads to globally optimal
- Problem has the **greedy choice property** and **optimal substructure**

**Classic greedy problems:**
- Activity selection / interval scheduling
- Huffman coding
- Fractional knapsack
- Dijkstra's shortest path
- Minimum spanning tree (Kruskal/Prim)

**Counter-example:** 0/1 knapsack is NOT greedy — need DP.

### When to Use Dynamic Programming

**Signs you need DP:**
- Problem has **overlapping subproblems** and **optimal substructure**
- You're counting something (number of ways)
- You're optimizing (min/max cost)
- Brute force has exponential time

**DP Patterns:**
| Pattern | Example |
|---|---|
| Linear DP | Fibonacci, climbing stairs |
| Knapsack | 0/1 knapsack, subset sum |
| Interval | Matrix chain, burst balloons |
| Grid | Unique paths, minimum path sum |
| String | LCS, edit distance |
| Bitmask | TSP, assignment |
| Digit | Count numbers with property |
| Tree | Max independent set on tree |

### When to Use Divide and Conquer

**Signs it fits:**
- Problem splits into independent subproblems
- Subproblems are the same type as the original
- Combining results is efficient

**Classic D&C:**
- Merge sort, quicksort
- Binary search
- Closest pair of points
- Fast Fourier Transform

### When to Use Backtracking

**Signs you need backtracking:**
- Enumerate all solutions (or find one valid solution)
- Problem has constraints that prune the search space
- n is small (≤ 20 for bitmask, ≤ 12 for full permutation)

**Classic backtracking:**
- N-Queens
- Sudoku solver
- Subset/permutation generation
- Graph coloring

---

## 140.5 Special Techniques

### Two Pointers
**When:** Sorted array, need pairs/triplets with some property.
**Examples:** Two sum (sorted), three sum, container with most water.

### Sliding Window
**When:** Contiguous subarray/substring with some property.
**Examples:** Longest substring without repeat, minimum window substring.

### Binary Search on Answer
**When:** Answer is monotonic (if x works, then x+1 also works).
**Examples:** Minimum capacity to ship packages, aggressive cows.

### Prefix Sum
**When:** Frequent range sum queries on static array.
**Examples:** Subarray sum equals k, range sum query.

### Monotonic Stack
**When:** Next greater/smaller element, histogram problems.
**Examples:** Daily temperatures, largest rectangle in histogram.

### Coordinate Compression
**When:** Values are large but only relative order matters.
**Examples:** Range queries with large values, sweep line.

---

## 140.6 Walkthrough: Selecting an Algorithm

**Problem:** Given a weighted directed graph with n ≤ 2000 vertices and m ≤ 5000 edges, find the shortest path from vertex 1 to vertex n. Some edges may have negative weights.

**Step 1: Identify the type** → Shortest path.

**Step 2: Check constraints** → n ≤ 2000, m ≤ 5000.

**Step 3: Consider negative weights** → Rules out Dijkstra.

**Step 4: Check for negative cycles** → Problem doesn't mention, but we should handle it.

**Step 5: Choose algorithm:**
- BFS: No, edges are weighted.
- Dijkstra: No, negative weights.
- Bellman-Ford: O(nm) = O(10⁷) — fits!
- Floyd-Warshall: O(n³) = O(8×10⁹) — too slow.

**Decision:** Bellman-Ford.

**C++ Implementation:**

```cpp
#include <vector>
#include <climits>
using namespace std;

struct Edge { int u, v, w; };

int bellmanFord(int n, vector<Edge>& edges, int src, int dst) {
    vector<int> dist(n + 1, INT_MAX);
    dist[src] = 0;
    
    for (int i = 0; i < n - 1; i++) {
        for (auto& e : edges) {
            if (dist[e.u] != INT_MAX && dist[e.u] + e.w < dist[e.v]) {
                dist[e.v] = dist[e.u] + e.w;
            }
        }
    }
    
    // Check for negative cycle reachable from src
    for (auto& e : edges) {
        if (dist[e.u] != INT_MAX && dist[e.u] + e.w < dist[e.v]) {
            return -1; // Negative cycle detected
        }
    }
    
    return dist[dst];
}
```

**Python Implementation:**

```python
def bellman_ford(n, edges, src, dst):
    dist = [float('inf')] * (n + 1)
    dist[src] = 0
    
    for _ in range(n - 1):
        for u, v, w in edges:
            if dist[u] != float('inf') and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    
    # Check for negative cycle
    for u, v, w in edges:
        if dist[u] != float('inf') and dist[u] + w < dist[v]:
            return -1  # Negative cycle
    
    return dist[dst]
```

**Java Implementation:**

```java
import java.util.*;

class Edge {
    int u, v, w;
    Edge(int u, int v, int w) { this.u = u; this.v = v; this.w = w; }
}

class Solution {
    int bellmanFord(int n, List<Edge> edges, int src, int dst) {
        int[] dist = new int[n + 1];
        Arrays.fill(dist, Integer.MAX_VALUE);
        dist[src] = 0;
        
        for (int i = 0; i < n - 1; i++) {
            for (Edge e : edges) {
                if (dist[e.u] != Integer.MAX_VALUE && dist[e.u] + e.w < dist[e.v]) {
                    dist[e.v] = dist[e.u] + e.w;
                }
            }
        }
        
        // Check for negative cycle
        for (Edge e : edges) {
            if (dist[e.u] != Integer.MAX_VALUE && dist[e.u] + e.w < dist[e.v]) {
                return -1;
            }
        }
        
        return dist[dst];
    }
}
```

**Dry Run:**
```
Graph: 1→2 (3), 1→3 (5), 2→3 (-2), 2→4 (6), 3→4 (2)
n=4, src=1, dst=4

Initial: dist = [∞, 0, ∞, ∞, ∞]

Iteration 1:
  Edge 1→2: dist[2] = 0+3 = 3
  Edge 1→3: dist[3] = 0+5 = 5
  Edge 2→3: dist[3] = min(5, 3-2) = 1
  Edge 2→4: dist[4] = 3+6 = 9
  Edge 3→4: dist[4] = min(9, 1+2) = 3

Iteration 2:
  No changes (converged)

Result: dist[4] = 3 (path: 1→2→3→4)
```

---

## 140.7 Common Mistakes

1. **Using O(n²) when O(n log n) is needed** — Check constraints first!
2. **Using Dijkstra with negative edges** — Always check for negative weights.
3. **Forgetting to handle edge cases** — Empty graph, disconnected components, self-loops.
4. **Wrong algorithm for the problem type** — E.g., using DFS for shortest path in weighted graph.
5. **Not considering the constant factor** — O(n log n) with high constant may be slower than O(n²) for small n.
6. **Over-complicating** — If a simple solution works, don't add complexity.

---

## 140.8 Exercises

1. **Given n ≤ 15 cities and distances between them**, find the shortest route visiting all cities. → Bitmask DP, O(2^n · n²).

2. **Given a grid with 0s and 1s**, find the number of islands. → BFS/DFS, O(n·m).

3. **Given an array of n ≤ 10⁵ integers**, find the longest increasing subsequence. → DP with binary search, O(n log n).

4. **Given a tree with n nodes**, find the diameter. → Two DFS/BFS, O(n).

5. **Given n intervals**, find the maximum number of overlapping intervals at any point. → Sweep line, O(n log n).

---

## 140.9 Interview Questions

1. **"Find the k-th largest element"** → Quickselect O(n) or heap O(n log k).

2. **"Merge k sorted lists"** → Min-heap of size k, O(n log k).

3. **"Word ladder" (transform one word to another)** → BFS on word graph, O(n·m²).

4. **"Course schedule" (detect cycle in prerequisites)** → Topological sort or DFS cycle detection.

5. **"Longest palindromic substring"** → Manacher O(n) or expand around center O(n²).

6. **"Trapping rain water"** → Two pointers O(n) or monotonic stack O(n).

---

## 140.10 Cross-References

- **Binary Search:** Chapter on Binary Search
- **BFS/DFS:** Chapter on Graph Traversal
- **Dijkstra:** Chapter on Shortest Paths
- **Dynamic Programming:** Chapter on DP
- **Greedy:** Chapter on Greedy Algorithms
- **Segment Trees:** Chapter on Segment Trees
- **String Algorithms:** Chapter on String Matching
- **Complexity Guide:** Chapter 139 (Complexity Handbook)

---

## Summary

| Constraint | Max Complexity | Go-To Algorithms |
|---|---|---|
| n ≤ 10 | O(n!) | Permutation brute force |
| n ≤ 20 | O(2^n) | Bitmask DP |
| n ≤ 500 | O(n³) | Floyd, matrix chain DP |
| n ≤ 5000 | O(n²) | Simple DP, Bellman-Ford |
| n ≤ 10⁵ | O(n log n) | Sort, segment tree, Dijkstra |
| n ≤ 10⁶ | O(n) | Linear scan, BFS, counting |
| n > 10⁶ | O(log n) or O(1) | Binary search, math |
