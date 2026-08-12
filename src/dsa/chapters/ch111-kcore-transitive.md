# Chapter 111: K-Core Decomposition and Transitive Closure

## Prerequisites
- Graph basics ([Chapter 22](ch22-graph-fundamentals.md))
- BFS/DFS
- Floyd-Warshall ([Chapter 82](ch82-advanced-shortest-paths.md))

## Interview Frequency: ★★

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| K-Core | ★★ | Medium | Degeneracy ordering |
| Transitive Closure | ★★ | Medium | Reachability matrix |
| Transitive Reduction | ★ | Hard | Minimal equivalent DAG |
| Min Path Cover | ★★ | Medium | Bipartite matching |

---

## Definition

**K-Core** of a graph is the maximal subgraph where every vertex has degree ≥ k within the subgraph. The **core number** of a vertex is the highest k such that the vertex belongs to the k-core.

**Transitive Closure** answers "is there a path from u to v?" for all pairs (u, v) in a directed graph.

## Motivation

- **K-Core**: Community detection in social networks, identifying densely connected groups, degeneracy ordering for graph algorithms
- **Transitive Closure**: Dependency analysis, reachability in networks, compiler optimization (which variables are transitively used)

## Intuition

- **K-Core**: Peel away vertices with degree < k. What's left is the k-core. Like removing the weakest links until only strongly-connected hubs remain.
- **Transitive Closure**: If A→B and B→C, then A can reach C. Build a matrix of all such reachability relationships.

---

## 111.1 K-Core Decomposition

### Algorithm

1. Compute degree of each vertex
2. Repeatedly remove the vertex with minimum degree
3. Assign core number = max k such that vertex survives k rounds

### Step-by-Step Walkthrough

Graph: 0-1, 1-2, 2-0 (triangle), 1-3, 3-4, 4-5, 5-3 (cycle), 4-6, 6-7, 7-8, 8-6 (cycle)

```
Round 0 (degree < 1): Remove vertex 8? No, degree 2.
Actually let's use bucket sort:

Degrees: 0:2, 1:3, 2:2, 3:3, 4:3, 5:2, 6:2, 7:2, 8:2

Process by increasing degree:
- All degree-2 vertices: 0,2,5,6,7,8
- Remove 0: core[0]=2, neighbors 1,2 lose degree
  - 1: degree 3→2, 2: degree 2→1
- Remove 2: core[2]=2, neighbor 1 loses degree
  - 1: degree 2→1
- Process remaining...

Result: core numbers reflect how deeply connected each vertex is.
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

std::vector<int> kCoreDecomposition(int n, const std::vector<std::vector<int>>& adj) {
    std::vector<int> degree(n), core(n, 0);
    for (int i = 0; i < n; i++) degree[i] = adj[i].size();

    int maxDegree = *std::max_element(degree.begin(), degree.end());
    std::vector<std::vector<int>> buckets(maxDegree + 1);
    for (int i = 0; i < n; i++) buckets[degree[i]].push_back(i);

    std::vector<bool> processed(n, false);

    for (int k = 0; k <= maxDegree; k++) {
        for (int u : buckets[k]) {
            if (processed[u]) continue;
            processed[u] = true;
            core[u] = k;
            for (int v : adj[u]) {
                if (processed[v]) continue;
                if (degree[v] > k) {
                    degree[v]--;
                    buckets[degree[v]].push_back(v);
                }
            }
        }
    }

    return core;
}

int main() {
    int n = 9;
    std::vector<std::vector<int>> adj(n);
    auto addEdge = [&](int u, int v) { adj[u].push_back(v); adj[v].push_back(u); };
    addEdge(0, 1); addEdge(1, 2); addEdge(2, 0);
    addEdge(1, 3); addEdge(3, 4); addEdge(4, 5); addEdge(5, 3);
    addEdge(4, 6); addEdge(6, 7); addEdge(7, 8); addEdge(8, 6);

    auto core = kCoreDecomposition(n, adj);
    std::cout << "K-core values:\n";
    for (int i = 0; i < n; i++)
        std::cout << "  Vertex " << i << ": core = " << core[i] << "\n";

    return 0;
}
```

### Python Implementation

```python
def k_core_decomposition(n, adj):
    degree = [len(adj[i]) for i in range(n)]
    core = [0] * n
    max_deg = max(degree) if degree else 0

    buckets = [[] for _ in range(max_deg + 1)]
    for i in range(n):
        buckets[degree[i]].append(i)

    processed = [False] * n

    for k in range(max_deg + 1):
        for u in buckets[k]:
            if processed[u]:
                continue
            processed[u] = True
            core[u] = k
            for v in adj[u]:
                if processed[v]:
                    continue
                if degree[v] > k:
                    degree[v] -= 1
                    buckets[degree[v]].append(v)

    return core

# Example
n = 9
adj = [[] for _ in range(n)]
def add_edge(u, v):
    adj[u].append(v); adj[v].append(u)

add_edge(0, 1); add_edge(1, 2); add_edge(2, 0)
add_edge(1, 3); add_edge(3, 4); add_edge(4, 5); add_edge(5, 3)
add_edge(4, 6); add_edge(6, 7); add_edge(7, 8); add_edge(8, 6)

core = k_core_decomposition(n, adj)
for i, c in enumerate(core):
    print(f"Vertex {i}: core = {c}")
```

### Java Implementation

```java
import java.util.*;

public class KCoreDecomposition {
    public static int[] decompose(int n, List<List<Integer>> adj) {
        int[] degree = new int[n], core = new int[n];
        int maxDeg = 0;
        for (int i = 0; i < n; i++) {
            degree[i] = adj.get(i).size();
            maxDeg = Math.max(maxDeg, degree[i]);
        }

        List<List<Integer>> buckets = new ArrayList<>();
        for (int i = 0; i <= maxDeg; i++) buckets.add(new ArrayList<>());
        for (int i = 0; i < n; i++) buckets.get(degree[i]).add(i);

        boolean[] processed = new boolean[n];

        for (int k = 0; k <= maxDeg; k++) {
            for (int u : buckets.get(k)) {
                if (processed[u]) continue;
                processed[u] = true;
                core[u] = k;
                for (int v : adj.get(u)) {
                    if (processed[v]) continue;
                    if (degree[v] > k) {
                        degree[v]--;
                        buckets.get(degree[v]).add(v);
                    }
                }
            }
        }
        return core;
    }

    public static void main(String[] args) {
        int n = 9;
        List<List<Integer>> adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        // Add edges...
        int[] core = decompose(n, adj);
        for (int i = 0; i < n; i++)
            System.out.println("Vertex " + i + ": core = " + core[i]);
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| K-Core decomposition | O(V + E) | O(V) |

---

## 111.2 Transitive Closure

### Definition

Given a directed graph, compute `reach[i][j]` = true iff there exists a path from i to j.

### Algorithm — Floyd-Warshall Variant

```cpp
#include <iostream>
#include <vector>

std::vector<std::vector<bool>> transitiveClosure(int n,
    const std::vector<std::vector<int>>& adj) {
    std::vector<std::vector<bool>> reach(n, std::vector<bool>(n, false));
    for (int i = 0; i < n; i++) {
        reach[i][i] = true;
        for (int j : adj[i]) reach[i][j] = true;
    }
    for (int k = 0; k < n; k++)
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                reach[i][j] = reach[i][j] || (reach[i][k] && reach[k][j]);
    return reach;
}

int main() {
    std::vector<std::vector<int>> adj = {{1}, {2}, {0, 3}, {}};
    auto reach = transitiveClosure(4, adj);
    std::cout << "Transitive closure:\n";
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++)
            std::cout << reach[i][j] << " ";
        std::cout << "\n";
    }
    return 0;
}
```

### Python Implementation

```python
def transitive_closure(n, adj):
    reach = [[False] * n for _ in range(n)]
    for i in range(n):
        reach[i][i] = True
        for j in adj[i]:
            reach[i][j] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    return reach

adj = [[1], [2], [0, 3], []]
reach = transitive_closure(4, adj)
for row in reach:
    print([int(x) for x in row])
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Transitive closure | O(V³) | O(V²) |

---

## 111.3 Minimum Path Cover

### Definition

Find the minimum number of vertex-disjoint paths that cover all vertices of a DAG.

### Reduction to Bipartite Matching

- Create bipartite graph: left copy and right copy of vertices
- Add edge (u_left, v_right) for each edge (u, v) in DAG
- Min path cover = n − max matching

### C++ Implementation

```cpp
#include <iostream>
#include <vector>

int minPathCover(int n, const std::vector<std::pair<int,int>>& edges) {
    std::vector<std::vector<int>> adj(n);
    for (auto& [u, v] : edges) adj[u].push_back(v);

    std::vector<int> match(n, -1);
    std::vector<bool> visited;

    std::function<bool(int)> bpm = [&](int u) -> bool {
        for (int v : adj[u]) {
            if (visited[v]) continue;
            visited[v] = true;
            if (match[v] == -1 || bpm(match[v])) {
                match[v] = u;
                return true;
            }
        }
        return false;
    };

    int matching = 0;
    for (int u = 0; u < n; u++) {
        visited.assign(n, false);
        if (bpm(u)) matching++;
    }
    return n - matching;
}

int main() {
    int n = 4;
    std::vector<std::pair<int,int>> edges = {{0,1}, {0,2}, {1,3}, {2,3}};
    std::cout << "Min path cover: " << minPathCover(n, edges) << "\n"; // 2
    return 0;
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Min path cover | O(V × E) | O(V + E) |

---

## 111.4 Transitive Reduction

### Definition

The **transitive reduction** of a directed graph is the smallest graph with the same reachability. For DAGs, it's unique and equals the graph with edges (u,v) removed if there's a longer path u→...→v.

### Algorithm for DAGs

1. Compute transitive closure
2. For each edge (u,v), check if there's an intermediate w with reach[u][w] and reach[w][v]
3. If yes, remove edge (u,v) — it's redundant

---

## Exercises

1. **K-Core visualization**: Given a social network graph, compute core numbers and identify the innermost core (highest k). Plot the core decomposition.

2. **Reachability queries**: Given a DAG with n ≤ 500 nodes, preprocess transitive closure, then answer m reachability queries in O(1) each.

3. **Path cover reconstruction**: Extend the min path cover algorithm to actually output the paths, not just the count.

4. **K-Core for community detection**: Given a graph, find all connected components in the k-core for k = 1, 2, 3, .... How do communities emerge?

5. **Dynamic transitive closure**: Given a DAG with edge insertions, maintain transitive closure incrementally. What's the amortized cost per insertion?

---

## Interview Questions

1. **Q: What is the degeneracy of a graph?**
   A: The maximum core number across all vertices. A graph with degeneracy d can be colored with d+1 colors. It's a measure of how "sparse" a graph is.

2. **Q: How does K-Core relate to community detection?**
   A: The k-core decomposition reveals nested communities. The innermost core (highest k) is the most tightly connected group. Social networks often have a small, high-core "clique" surrounded by lower-core periphery.

3. **Q: Can transitive closure be computed faster than O(V³)?**
   A: For general graphs, not really (it's equivalent to Boolean matrix multiplication). For sparse graphs, BFS from each node is O(V(V+E)) which can be better. For DAGs, topological order + bitsets can be faster in practice.

4. **Q: What's the relationship between min path cover and maximum matching?**
   A: By König's theorem, min path cover in a DAG = n − max bipartite matching. Each matched edge "joins" two path segments, reducing the cover count by 1.

---

## Cross-References

- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — BFS/DFS foundation
- [Chapter 82: Advanced Shortest Paths](ch82-advanced-shortest-paths.md) — Floyd-Warshall for transitive closure
- [Chapter 29: Network Flow](ch29-network-flow.md) — Bipartite matching for path cover
- [Chapter 107: HLD and Centroid Applications](ch107-hld-centroid-applications.md) — Other graph decomposition techniques

---

## Summary

| Algorithm | Time | Application |
|---|---|---|
| K-Core | O(V + E) | Community detection, degeneracy |
| Transitive Closure | O(V³) | Reachability queries |
| Min Path Cover | O(V × E) | DAG path optimization |
| Transitive Reduction | O(V³) | Minimal DAG representation |
