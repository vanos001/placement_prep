# Chapter 183: DAG Shortest & Longest Paths

For **directed acyclic graphs (DAGs)**, shortest paths can be found in **O(V + E)** — faster than Dijkstra. The key insight: process vertices in **topological order**, guaranteeing that when we relax an edge, all incoming paths have already been finalized.

---

## Algorithm

1. Compute a topological ordering of the DAG.
2. Initialize `dist[s] = 0`, all others = ∞.
3. For each vertex `u` in topological order, relax every outgoing edge `(u, v, w)`.

```cpp
// O(V + E) shortest paths from source s in a DAG
void dag_shortest(int n, vector<tuple<int,int,int>>& edges, int s, vector<int>& dist) {
    vector<vector<pair<int,int>>> adj(n);
    for (auto& [u, v, w] : edges) adj[u].push_back({v, w});

    // Topological sort (Kahn's algorithm)
    vector<int> indeg(n, 0), order;
    for (auto& [u, v, w] : edges) indeg[v]++;
    queue<int> q;
    for (int i = 0; i < n; i++) if (!indeg[i]) q.push(i);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (auto& [v, w] : adj[u]) if (--indeg[v] == 0) q.push(v);
    }

    // Relax in topological order
    dist.assign(n, INT_MAX);
    dist[s] = 0;
    for (int u : order) {
        if (dist[u] == INT_MAX) continue;
        for (auto& [v, w] : adj[u])
            if (dist[u] + w < dist[v]) dist[v] = dist[u] + w;
    }
}
```

For **longest paths**, simply negate all weights and run shortest paths, or flip the relaxation comparison.

---

## Walkthrough

DAG with edges: 0→1 (3), 0→2 (6), 1→2 (2), 1→3 (4), 2→3 (1). Source = 0.

| Step | Vertex | dist[] before | Edges relaxed | dist[] after |
|---|---|---|---|---|
| 1 | 0 | [0,∞,∞,∞] | 0→1:3, 0→2:6 | [0,3,6,∞] |
| 2 | 1 | [0,3,6,∞] | 1→2:2, 1→3:4 | [0,3,5,7] |
| 3 | 2 | [0,3,5,7] | 2→3:1 → 5+1=6 < 7 | [0,3,5,6] |
| 4 | 3 | [0,3,5,6] | No outgoing edges | [0,3,5,6] |

Shortest path 0→3: **6** (0→1→2→3).

---

## Critical Path: Job Scheduling

Model tasks as a DAG (edges = dependencies, weights = durations). The **longest path** from start to end gives the **critical path** — the minimum project duration.

---

## Complexity

| Phase | Time |
|---|---|
| Topological sort | O(V + E) |
| Relaxation pass | O(V + E) |
| **Total** | **O(V + E)** |
| Space | O(V + E) |

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Running on a graph with cycles | Verify DAG property first; otherwise use Bellman-Ford or Dijkstra |
| Forgetting longest-path negation trick | Negate weights and run shortest, or use `max` instead of `min` |
| Using Dijkstra unnecessarily on a DAG | Dijkstra is O(E log V); topological sort is O(V + E) |

---

## Practice Problems

| # | Problem | Hint |
|---|---|---|
| 1 | Course Schedule II (LeetCode 210) | Topological sort; longest chain = semesters needed |
| 2 | Parallel Courses (LeetCode 1136) | DAG longest path in terms of levels |
| 3 | Alien Dictionary (LeetCode 269) | Build DAG from ordering constraints, topological sort |
| 4 | Critical Connections (LeetCode 1192) | Related: find bridges, but topological order helps DAG problems |
| 5 | Longest Increasing Path in Matrix (LeetCode 329) | Build DAG where edge u→v exists if a[u]<a[v], find longest path |
| 6 | Cheapest Flights Within K Stops — DAG variant | If stops form a DAG layer structure, use this approach |

---

## See Also

- [Chapter 25: Topological Sort](ch25-topological-sort.md)
- [Chapter 26: Shortest Paths](ch26-shortest-paths.md)
- [Chapter 82: Advanced Shortest Paths](ch82-advanced-shortest-paths.md)
- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md)
