# Chapter 82: Advanced Shortest Paths

## Prerequisites
- Dijkstra's algorithm ([Chapter 26](ch26-shortest-paths.md))
- BFS
- Graph fundamentals ([Chapter 22](ch22-graph-fundamentals.md))

## Interview Frequency: ★★★

Advanced shortest path algorithms handle negative weights, all-pairs queries, and specialized graphs. **Google** and **Amazon** test these for complex graph problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Bellman-Ford | ★★★ | Medium | Negative weights |
| Floyd-Warshall | ★★★★ | Medium | All-pairs shortest |
| 0-1 BFS | ★★★ | Medium | Weights 0 or 1 |
| SPFA | ★★ | Medium | Faster Bellman-Ford |

---

## Definition

**Bellman-Ford** finds shortest paths from a single source, handling negative edge weights. It detects negative cycles in O(VE).

**Floyd-Warshall** finds all-pairs shortest paths in O(V³), handling negative weights (but not negative cycles reachable from a path).

**0-1 BFS** is a specialized BFS for graphs with edge weights 0 or 1, using a deque for O(V+E) time.

## Motivation

Dijkstra fails with negative weights. Bellman-Ford handles them. Floyd-Warshall answers all-pairs queries. 0-1 BFS is optimal for binary-weighted graphs.

## Intuition

- **Bellman-Ford**: Relax all edges V-1 times. If we can still relax after V-1 iterations, there's a negative cycle.
- **Floyd-Warshall**: For each intermediate node k, check if going through k improves any shortest path.
- **0-1 BFS**: Weight-0 edges go to the front of the deque, weight-1 edges go to the back.

---

## 82.1 Bellman-Ford Algorithm

### Step-by-Step

1. Initialize dist[src] = 0, all others = ∞
2. Repeat V-1 times: relax all edges
3. Check for negative cycles: try to relax again

### Dry Run

Graph: 0→1(6), 0→3(7), 1→2(5), 1→3(8), 1→4(-4), 2→1(-2), 3→2(-3), 3→4(9), 4→0(2)

```
Initial: dist = [0, ∞, ∞, ∞, ∞]

Iteration 1:
  0→1: dist[1] = 6
  0→3: dist[3] = 7
  1→2: dist[2] = 11
  1→3: min(7, 14) = 7
  1→4: dist[4] = 2
  2→1: min(6, 9) = 6
  3→2: min(11, 4) = 4
  3→4: min(2, 16) = 2
  4→0: min(0, 4) = 0

Iteration 2:
  3→2: dist[2] = 4 (was 11, now 7+(-3)=4)
  2→1: dist[1] = 2 (was 6, now 4+(-2)=2)
  1→4: dist[4] = -2 (was 2, now 2+(-4)=-2)
  ... (continues)

After V-1=4 iterations: dist = [0, 2, 4, 7, -2]
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <climits>

struct Edge { int u, v, w; };

std::vector<long long> bellmanFord(int n, const std::vector<Edge>& edges, int src) {
    std::vector<long long> dist(n, LLONG_MAX);
    dist[src] = 0;

    for (int i = 0; i < n - 1; i++)
        for (auto& [u, v, w] : edges)
            if (dist[u] != LLONG_MAX && dist[u] + w < dist[v])
                dist[v] = dist[u] + w;

    // Negative cycle check
    for (auto& [u, v, w] : edges)
        if (dist[u] != LLONG_MAX && dist[u] + w < dist[v])
            return {}; // Negative cycle

    return dist;
}

int main() {
    int n = 5;
    std::vector<Edge> edges = {
        {0,1,6},{0,3,7},{1,2,5},{1,3,8},{1,4,-4},
        {2,1,-2},{3,2,-3},{3,4,9},{4,0,2}
    };
    auto dist = bellmanFord(n, edges, 0);
    std::cout << "Distances from 0:\n";
    for (int i = 0; i < n; i++)
        std::cout << "  To " << i << ": " << dist[i] << "\n";
    return 0;
}
```

### Python Implementation

```python
def bellman_ford(n, edges, src):
    dist = [float('inf')] * n
    dist[src] = 0
    for _ in range(n - 1):
        for u, v, w in edges:
            if dist[u] != float('inf') and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    for u, v, w in edges:
        if dist[u] != float('inf') and dist[u] + w < dist[v]:
            return None  # Negative cycle
    return dist

edges = [(0,1,6),(0,3,7),(1,2,5),(1,3,8),(1,4,-4),
         (2,1,-2),(3,2,-3),(3,4,9),(4,0,2)]
dist = bellman_ford(5, edges, 0)
for i, d in enumerate(dist):
    print(f"To {i}: {d}")
```

### Java Implementation

```java
import java.util.*;

public class BellmanFord {
    static class Edge { int u, v, w; Edge(int u, int v, int w) { this.u=u; this.v=v; this.w=w; } }

    static long[] solve(int n, Edge[] edges, int src) {
        long[] dist = new long[n];
        Arrays.fill(dist, Long.MAX_VALUE);
        dist[src] = 0;
        for (int i = 0; i < n-1; i++)
            for (Edge e : edges)
                if (dist[e.u] != Long.MAX_VALUE && dist[e.u] + e.w < dist[e.v])
                    dist[e.v] = dist[e.u] + e.w;
        for (Edge e : edges)
            if (dist[e.u] != Long.MAX_VALUE && dist[e.u] + e.w < dist[e.v])
                return null;
        return dist;
    }

    public static void main(String[] args) {
        Edge[] edges = {new Edge(0,1,6),new Edge(0,3,7),new Edge(1,2,5),
                        new Edge(1,4,-4),new Edge(2,1,-2),new Edge(3,2,-3)};
        long[] dist = solve(4, edges, 0);
        for (int i = 0; i < dist.length; i++)
            System.out.println("To " + i + ": " + dist[i]);
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Bellman-Ford | O(VE) | O(V) |
| Negative cycle check | O(VE) | O(V) |

---

## 82.2 Floyd-Warshall Algorithm

### Algorithm

For each intermediate node k, update all pairs (i,j):
```
dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

std::vector<std::vector<long long>> floydWarshall(int n,
    const std::vector<std::vector<long long>>& adj) {
    auto dist = adj;
    for (int k = 0; k < n; k++)
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                if (dist[i][k] != LLONG_MAX && dist[k][j] != LLONG_MAX)
                    dist[i][j] = std::min(dist[i][j], dist[i][k] + dist[k][j]);
    return dist;
}

int main() {
    int n = 4;
    long long INF = LLONG_MAX;
    std::vector<std::vector<long long>> adj = {
        {0, 5, INF, 10}, {INF, 0, 3, INF},
        {INF, INF, 0, 1}, {INF, INF, INF, 0}
    };
    auto dist = floydWarshall(n, adj);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++)
            std::cout << (dist[i][j] == INF ? -1 : dist[i][j]) << "\t";
        std::cout << "\n";
    }
    return 0;
}
```

### Python Implementation

```python
def floyd_warshall(n, adj):
    dist = [row[:] for row in adj]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] != float('inf') and dist[k][j] != float('inf'):
                    dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
    return dist

INF = float('inf')
adj = [[0,5,INF,10],[INF,0,3,INF],[INF,INF,0,1],[INF,INF,INF,0]]
dist = floyd_warshall(4, adj)
for row in dist:
    print([int(x) if x != INF else -1 for x in row])
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Floyd-Warshall | O(V³) | O(V²) |

---

## 82.3 0-1 BFS

For graphs with edge weights 0 or 1, use a deque.

```cpp
#include <iostream>
#include <vector>
#include <deque>
#include <climits>

struct Edge { int to, weight; };

std::vector<int> bfs01(int n, const std::vector<std::vector<Edge>>& adj, int src) {
    std::vector<int> dist(n, INT_MAX);
    std::deque<int> dq;
    dist[src] = 0;
    dq.push_front(src);

    while (!dq.empty()) {
        int u = dq.front(); dq.pop_front();
        for (auto& [v, w] : adj[u]) {
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                if (w == 0) dq.push_front(v);
                else dq.push_back(v);
            }
        }
    }
    return dist;
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| 0-1 BFS | O(V + E) | O(V) |

---

## Exercises

1. **Negative cycle detection**: Modify Bellman-Ford to find the actual negative cycle, not just detect it.

2. **All-pairs with path reconstruction**: Extend Floyd-Warshall to reconstruct the shortest path between any two nodes.

3. **0-1 BFS application**: Solve the "minimum edges to flip" problem: given a directed graph, find the minimum number of edges to reverse to get from s to t.

4. **SPFA**: Implement the Shortest Path Faster Algorithm (queue-optimized Bellman-Ford). Compare with standard Bellman-Ford.

---

## Interview Questions

1. **Q: When would you use Bellman-Ford over Dijkstra?**
   A: When the graph has negative edge weights. Dijkstra's greedy approach fails with negative weights. Bellman-Ford handles them in O(VE).

2. **Q: How does Floyd-Warshall detect negative cycles?**
   A: After running the algorithm, if any diagonal entry dist[i][i] < 0, there's a negative cycle reachable from node i.

3. **Q: Why does 0-1 BFS work?**
   A: It's essentially Dijkstra with a deque instead of a priority queue. Weight-0 edges don't increase distance (push to front), weight-1 edges do (push to back). This maintains the invariant that the deque is sorted by distance.

4. **Q: Can Floyd-Warshall handle negative edge weights?**
   A: Yes, but not negative cycles that are reachable from a path between two nodes. If dist[i][i] < 0 after the algorithm, node i is part of or reachable from a negative cycle.

---

## Cross-References
- [Chapter 26: Shortest Paths](ch26-shortest-paths.md) — Dijkstra and BFS foundations
- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — Graph representations
- [Chapter 73: Linear Algebra](ch73-linear-algebra.md) — Floyd-Warshall as matrix operation

---

## Summary

| Algorithm | Time | Negative Weights | All-Pairs | Negative Cycle |
|---|---|---|---|---|
| Dijkstra | O((V+E)log V) | No | No | No |
| Bellman-Ford | O(VE) | Yes | No | Yes |
| Floyd-Warshall | O(V³) | Yes | Yes | Yes |
| 0-1 BFS | O(V+E) | No (0/1 only) | No | No |
| SPFA | O(VE) avg | Yes | No | Yes |
