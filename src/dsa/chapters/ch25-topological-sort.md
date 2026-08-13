# Chapter 25: Topological Sort

Topological sort is a fundamental algorithm for ordering the vertices of a directed acyclic graph (DAG) such that for every directed edge \\((u, v)\\), vertex \\(u\\) comes before \\(v\\) in the ordering. It is the backbone of task scheduling, build systems, and dependency resolution.

In this chapter, we explore two approaches to topological sort — Kahn's algorithm (BFS-based) and DFS-based — along with their applications and the critical connection to cycle detection.

---

## 25.1 What Is Topological Sort?

### Definition

Given a DAG \\(G = (V, E)\\), a **topological ordering** is a linear ordering \\(v_1, v_2, \ldots, v_n\\) of all vertices such that for every edge \\((v_i, v_j) \in E\\), we have \\(i < j\\). In other words, every vertex appears before all vertices it has edges to.

### Real-World Applications

| Application | Vertices | Edges | Order |
|------------|----------|-------|-------|
| Course prerequisites | Courses | "A before B" | Valid course sequence |
| Build systems | Source files | Dependencies | Compilation order |
| Task scheduling | Tasks | Prerequisites | Execution order |
| Spreadsheet | Cells | Formula dependencies | Recalculation order |
| Package managers | Packages | Dependencies | Install order |
| Makefile | Targets | Dependencies | Build order |

### Key Properties

- A topological ordering exists **if and only if** the graph is a DAG (no cycles).
- The topological ordering is **not unique** — a DAG can have multiple valid orderings.
- Every DAG has at least one vertex with in-degree 0 (a source) and at least one with out-degree 0 (a sink).

### Example

```
Courses: C1, C2, C3, C4, C5
Prerequisites: C1→C3, C1→C4, C2→C3, C3→C5, C4→C5

Graph:
    C1 → C3 → C5
    C1 → C4 ↗
    C2 → C3

Valid topological orders:
  C1, C2, C3, C4, C5
  C2, C1, C3, C4, C5
  C1, C2, C4, C3, C5
  (and more...)
```

---

## 25.2 Kahn's Algorithm (BFS-Based)

### Idea

Kahn's algorithm repeatedly removes vertices with in-degree 0, since they have no remaining dependencies:

1. Compute the in-degree of every vertex.
2. Enqueue all vertices with in-degree 0.
3. While the queue is not empty:
   a. Dequeue vertex \\(u\\), append it to the result.
   b. For each neighbor \\(v\\) of \\(u\\): decrement \\(v\\)'s in-degree.
   c. If \\(v\\)'s in-degree becomes 0, enqueue \\(v\\).
4. If the result contains all vertices, we have a topological order. Otherwise, the graph has a cycle.

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <queue>

class TopologicalSort {
public:
    // Returns empty vector if cycle exists
    static std::vector<int> kahn(const std::vector<std::vector<int>>& adj, int V) {
        std::vector<int> inDegree(V, 0);
        for (int u = 0; u < V; ++u) {
            for (int v : adj[u]) {
                inDegree[v]++;
            }
        }

        std::queue<int> q;
        for (int i = 0; i < V; ++i) {
            if (inDegree[i] == 0) q.push(i);
        }

        std::vector<int> order;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            order.push_back(u);

            for (int v : adj[u]) {
                if (--inDegree[v] == 0) {
                    q.push(v);
                }
            }
        }

        if ((int)order.size() != V) return {}; // cycle detected
        return order;
    }
};

int main() {
    int V = 6;
    std::vector<std::vector<int>> adj(V);
    auto addEdge = [&](int u, int v) { adj[u].push_back(v); };

    addEdge(5, 0);
    addEdge(5, 2);
    addEdge(4, 0);
    addEdge(4, 1);
    addEdge(2, 3);
    addEdge(3, 1);

    auto order = TopologicalSort::kahn(adj, V);
    if (order.empty()) {
        std::cout << "Cycle detected!\n";
    } else {
        std::cout << "Topological order: ";
        for (int v : order) std::cout << v << " ";
        std::cout << "\n";
    }
    // Possible output: 4 5 0 2 3 1
}
```

**Time Complexity:** \\(O(V + E)\\) — computing in-degrees + processing each vertex and edge once.

**Space Complexity:** \\(O(V)\\) for the in-degree array and queue.

### Dry Run

Graph: `5→0, 5→2, 4→0, 4→1, 2→3, 3→1`

| Step | In-degree | Queue (front→back) | Dequeued | Result |
|------|-----------|-------------------|----------|--------|
| Init | [2,2,1,1,0,0] | [4,5] | — | [] |
| 1 | [1,1,1,1,0,0] | [5] | 4 | [4] |
| 2 | [0,1,0,1,0,0] | [0,2] | 5 | [4,5] |
| 3 | [0,1,0,1,0,0] | [2] | 0 | [4,5,0] |
| 4 | [0,1,0,0,0,0] | [3] | 2 | [4,5,0,2] |
| 5 | [0,0,0,0,0,0] | [1] | 3 | [4,5,0,2,3] |
| 6 | [0,0,0,0,0,0] | [] | 1 | [4,5,0,2,3,1] |

Result: **4 5 0 2 3 1** ✓

### Lexicographically Smallest Topological Order

If we use a **min-heap** (priority queue) instead of a regular queue, we get the lexicographically smallest valid topological ordering.

```cpp
#include <vector>
#include <queue>

std::vector<int> kahnLexSmallest(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> inDegree(V, 0);
    for (int u = 0; u < V; ++u)
        for (int v : adj[u]) inDegree[v]++;

    std::priority_queue<int, std::vector<int>, std::greater<int>> pq;
    for (int i = 0; i < V; ++i)
        if (inDegree[i] == 0) pq.push(i);

    std::vector<int> order;
    while (!pq.empty()) {
        int u = pq.top();
        pq.pop();
        order.push_back(u);
        for (int v : adj[u]) {
            if (--inDegree[v] == 0) pq.push(v);
        }
    }
    return order.size() == V ? order : std::vector<int>{};
}
```

### All Topological Sorts

Enumerating all valid topological orders is NP-hard in general (the number can be exponential). However, for small graphs, we can use backtracking:

```cpp
#include <iostream>
#include <vector>
#include <functional>

void allTopoSorts(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> inDegree(V, 0);
    for (int u = 0; u < V; ++u)
        for (int v : adj[u]) inDegree[v]++;

    std::vector<bool> visited(V, false);
    std::vector<int> order;

    std::function<void()> backtrack = [&]() {
        if ((int)order.size() == V) {
            for (int v : order) std::cout << v << " ";
            std::cout << "\n";
            return;
        }
        for (int i = 0; i < V; ++i) {
            if (!visited[i] && inDegree[i] == 0) {
                visited[i] = true;
                order.push_back(i);
                for (int v : adj[i]) inDegree[v]--;

                backtrack();

                visited[i] = false;
                order.pop_back();
                for (int v : adj[i]) inDegree[v]++;
            }
        }
    };
    backtrack();
}
```

---

## 25.3 DFS-Based Topological Sort

### Idea

In a DAG, a vertex that has no outgoing edges (or whose descendants have all been processed) can be placed at the *end* of the ordering. DFS naturally processes vertices in a depth-first manner, and the **reverse of the post-order** gives a valid topological ordering.

**Post-order**: a vertex is "finished" after all its descendants are finished. Reversing the finish order gives a valid topological sort.

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class TopoSortDFS {
    std::vector<std::vector<int>> adj;
    std::vector<int> color; // 0=WHITE, 1=GRAY, 2=BLACK
    std::vector<int> order;
    bool hasCycle;

public:
    TopoSortDFS(int V) : adj(V), color(V, 0), hasCycle(false) {}

    void addEdge(int u, int v) { adj[u].push_back(v); }

    void dfs(int u) {
        color[u] = 1; // GRAY
        for (int v : adj[u]) {
            if (color[v] == 1) { hasCycle = true; return; }
            if (color[v] == 0) dfs(v);
        }
        color[u] = 2; // BLACK
        order.push_back(u); // post-order
    }

    std::vector<int> sort() {
        int V = adj.size();
        for (int i = 0; i < V; ++i) {
            if (color[i] == 0) dfs(i);
        }
        if (hasCycle) return {};
        std::reverse(order.begin(), order.end());
        return order;
    }
};

int main() {
    TopoSortDFS ts(6);
    ts.addEdge(5, 0);
    ts.addEdge(5, 2);
    ts.addEdge(4, 0);
    ts.addEdge(4, 1);
    ts.addEdge(2, 3);
    ts.addEdge(3, 1);

    auto order = ts.sort();
    if (order.empty()) {
        std::cout << "Cycle detected!\n";
    } else {
        std::cout << "DFS Topo order: ";
        for (int v : order) std::cout << v << " ";
        std::cout << "\n";
    }
    // Possible output: 5 4 2 3 1 0
}
```

### Why Does Reversing Post-Order Work?

Consider an edge \\((u, v)\\). When DFS explores \\(u\\):
- If \\(v\\) is unvisited, DFS recurses into \\(v\\). \\(v\\) finishes before \\(u\\) (since \\(v\\) is a descendant), so \\(v\\) appears *after* \\(u\\) in post-order, meaning \\(u\\) comes *before* \\(v\\) after reversal. ✓
- If \\(v\\) is already finished, \\(v\\) was processed earlier, so \\(v\\) appears after \\(u\\) in post-order. After reversal, \\(u\\) comes before \\(v\\). ✓
- If \\(v\\) is GRAY (in progress), that's a back edge, which means a cycle — not a DAG.

---

## 25.4 Applications

### Task Scheduling

Given tasks with dependencies, find a valid execution order.

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <string>

class TaskScheduler {
public:
    static std::vector<std::string> schedule(
        const std::vector<std::string>& tasks,
        const std::vector<std::pair<std::string, std::string>>& deps) {

        int n = tasks.size();
        std::unordered_map<std::string, int> id;
        for (int i = 0; i < n; ++i) id[tasks[i]] = i;

        std::vector<std::vector<int>> adj(n);
        std::vector<int> inDegree(n, 0);
        for (auto& [a, b] : deps) { // b must come before a
            adj[id[b]].push_back(id[a]);
            inDegree[id[a]]++;
        }

        std::queue<int> q;
        for (int i = 0; i < n; ++i)
            if (inDegree[i] == 0) q.push(i);

        std::vector<std::string> order;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            order.push_back(tasks[u]);
            for (int v : adj[u])
                if (--inDegree[v] == 0) q.push(v);
        }
        return order.size() == n ? order : std::vector<std::string>{};
    }
};
```

### Build Systems

In a build system like Make, source files depend on headers and other source files. Topological sort determines the correct compilation order.

```cpp
#include <iostream>
#include <vector>
#include <queue>

std::vector<int> buildOrder(const std::vector<std::vector<int>>& adj, int V) {
    // Kahn's algorithm — same as before
    std::vector<int> inDegree(V, 0);
    for (int u = 0; u < V; ++u)
        for (int v : adj[u]) inDegree[v]++;

    std::queue<int> q;
    for (int i = 0; i < V; ++i)
        if (inDegree[i] == 0) q.push(i);

    std::vector<int> order;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : adj[u])
            if (--inDegree[v] == 0) q.push(v);
    }
    return order.size() == V ? order : std::vector<int>{};
}
```

### Course Prerequisites

```cpp
#include <vector>
#include <queue>

class Solution {
public:
    std::vector<int> findOrder(int numCourses,
                               std::vector<std::vector<int>>& prerequisites) {
        std::vector<std::vector<int>> adj(numCourses);
        std::vector<int> inDegree(numCourses, 0);

        for (auto& p : prerequisites) {
            adj[p[1]].push_back(p[0]); // p[1] is prerequisite for p[0]
            inDegree[p[0]]++;
        }

        std::queue<int> q;
        for (int i = 0; i < numCourses; ++i)
            if (inDegree[i] == 0) q.push(i);

        std::vector<int> order;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            order.push_back(u);
            for (int v : adj[u])
                if (--inDegree[v] == 0) q.push(v);
        }

        return (int)order.size() == numCourses ? order : std::vector<int>{};
    }
};
```

---

## 25.5 Detecting Cycles in DAGs

Both topological sort algorithms naturally detect cycles:

### Kahn's Algorithm

If the resulting order has fewer than \\(V\\) vertices, a cycle exists. The vertices in the cycle never achieve in-degree 0 because they depend on each other.

### DFS-Based

If DFS encounters a GRAY vertex (currently in the recursion stack), a cycle exists. The GRAY vertices on the stack form the cycle.

```cpp
#include <vector>

bool hasCycleDFS(int u, const std::vector<std::vector<int>>& adj,
                 std::vector<int>& color) {
    color[u] = 1; // GRAY
    for (int v : adj[u]) {
        if (color[v] == 1) return true;
        if (color[v] == 0 && hasCycleDFS(v, adj, color)) return true;
    }
    color[u] = 2; // BLACK
    return false;
}

bool hasCycle(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> color(V, 0);
    for (int i = 0; i < V; ++i) {
        if (color[i] == 0 && hasCycleDFS(i, adj, color))
            return true;
    }
    return false;
}
```

### Kahn's Cycle Detection

```cpp
#include <vector>
#include <queue>

bool hasCycleKahn(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> inDegree(V, 0);
    for (int u = 0; u < V; ++u)
        for (int v : adj[u]) inDegree[v]++;

    std::queue<int> q;
    for (int i = 0; i < V; ++i)
        if (inDegree[i] == 0) q.push(i);

    int count = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        count++;
        for (int v : adj[u])
            if (--inDegree[v] == 0) q.push(v);
    }
    return count != V; // true if cycle exists
}
```

---

## 25.6 DAG Dynamic Programming

Topological order enables efficient DP on DAGs. Since every edge goes forward in topological order, we can process vertices in that order and be sure that all dependencies are resolved.

### Longest Path in DAG

Finding the longest path in a general graph is NP-hard, but in a DAG it's \\(O(V + E)\\) using topological sort + DP.

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <climits>

long long longestPathDAG(int source, int V,
                         const std::vector<std::vector<std::pair<int, int>>>& adj) {
    // Topological sort (Kahn's)
    std::vector<int> inDegree(V, 0);
    for (int u = 0; u < V; ++u)
        for (auto [v, w] : adj[u]) inDegree[v]++;

    std::queue<int> q;
    for (int i = 0; i < V; ++i)
        if (inDegree[i] == 0) q.push(i);

    std::vector<int> topo;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        topo.push_back(u);
        for (auto [v, w] : adj[u])
            if (--inDegree[v] == 0) q.push(v);
    }

    // DP: dist[v] = longest path from source to v
    std::vector<long long> dist(V, LLONG_MIN);
    dist[source] = 0;

    for (int u : topo) {
        if (dist[u] == LLONG_MIN) continue;
        for (auto [v, w] : adj[u]) {
            dist[v] = std::max(dist[v], dist[u] + w);
        }
    }

    return *std::max_element(dist.begin(), dist.end());
}
```

### Counting Paths in DAG

How many paths exist from vertex \\(s\\) to vertex \\(t\\)?

```cpp
#include <vector>
#include <queue>

long long countPaths(int s, int t, int V,
                     const std::vector<std::vector<int>>& adj) {
    // Topological sort
    std::vector<int> inDegree(V, 0);
    for (int u = 0; u < V; ++u)
        for (int v : adj[u]) inDegree[v]++;

    std::queue<int> q;
    for (int i = 0; i < V; ++i)
        if (inDegree[i] == 0) q.push(i);

    std::vector<int> topo;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        topo.push_back(u);
        for (int v : adj[u])
            if (--inDegree[v] == 0) q.push(v);
    }

    // DP: paths[v] = number of paths from s to v
    std::vector<long long> paths(V, 0);
    paths[s] = 1;

    for (int u : topo) {
        for (int v : adj[u]) {
            paths[v] += paths[u];
        }
    }
    return paths[t];
}
```

### Key Insight

Whenever you see a DAG and need to compute some aggregate along paths (longest, shortest, count, etc.), think: **topological sort + DP**. The topological order ensures that when you process a vertex, all its predecessors have already been processed.

---

## 25.7 Condensation Graph

After finding SCCs in a directed graph, we can compress each SCC into a single node. The resulting graph is called the **condensation graph** and it's always a DAG.

```cpp
#include <vector>
#include <set>

std::vector<std::vector<int>> buildCondensation(
    int V, const std::vector<std::vector<int>>& adj,
    const std::vector<int>& component) {

    int numComponents = *std::max_element(component.begin(), component.end()) + 1;
    std::vector<std::set<int>> condensed(numComponents);

    for (int u = 0; u < V; ++u) {
        for (int v : adj[u]) {
            int cu = component[u], cv = component[v];
            if (cu != cv) {
                condensed[cu].insert(cv);
            }
        }
    }

    // Convert set to vector
    std::vector<std::vector<int>> result(numComponents);
    for (int i = 0; i < numComponents; ++i) {
        result[i].assign(condensed[i].begin(), condensed[i].end());
    }
    return result;
}
```

**Applications of condensation:**
- Compute the "strength" of connectivity between groups.
- Find the minimum edges to make the graph strongly connected.
- Solve problems that are easy on DAGs but hard on general directed graphs.

---

## Interview Tips

1. **Always check for cycles.** If the graph might have a cycle, your topological sort should detect it and return an empty result (or an error).
2. **Kahn's is usually preferred** in interviews because it's intuitive, uses BFS, and naturally detects cycles by counting.
3. **DFS-based** is elegant but watch for the cycle detection (GRAY/BLACK coloring).
4. **Not unique:** Don't assume a single valid order. If the problem asks for a specific one (e.g., lexicographically smallest), use a priority queue.
5. **Model the problem as a DAG.** Many problems that don't look like graph problems can be modeled as dependency graphs.

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Applying topo sort to undirected graph | Doesn't make sense | Only for DAGs |
| Forgetting cycle detection | Infinite loop or wrong answer | Check `order.size() == V` |
| Wrong edge direction in prerequisite | Reversed order | \\(b \to a\\) means "b before a" |
| Using DFS without reversing post-order | Wrong ordering | Reverse at the end |
| Not handling disconnected DAG | Missing vertices | Outer loop over all vertices |

## Practice Problems

### Course Schedule II (LeetCode 210)

**Problem:** There are `numCourses` courses with prerequisites. Return the ordering of courses to take all of them. If impossible (cycle), return empty.

*Solution: See the Course Prerequisites code in Section 25.4 above.*

### Alien Dictionary (LeetCode 269)

**Problem:** Given a sorted list of words from an alien language, derive the character order.

```cpp
#include <string>
#include <vector>
#include <queue>
#include <functional>

class Solution {
public:
    std::string alienOrder(std::vector<std::string>& words) {
        std::vector<std::vector<int>> adj(26);
        std::vector<int> inDegree(26, -1); // -1 = not used

        // Mark all used characters
        for (auto& w : words) {
            for (char c : w) inDegree[c - 'a'] = 0;
        }

        // Build graph from adjacent word comparisons
        for (int i = 0; i + 1 < (int)words.size(); ++i) {
            auto& a = words[i], &b = words[i + 1];
            int len = std::min(a.size(), b.size());
            bool found = false;
            for (int j = 0; j < len; ++j) {
                if (a[j] != b[j]) {
                    adj[a[j] - 'a'].push_back(b[j] - 'a');
                    inDegree[b[j] - 'a']++;
                    found = true;
                    break;
                }
            }
            // Edge case: "abc" before "ab" is invalid
            if (!found && a.size() > b.size()) return "";
        }

        // Kahn's algorithm
        std::queue<int> q;
        int charCount = 0;
        for (int i = 0; i < 26; ++i) {
            if (inDegree[i] == 0) q.push(i);
            if (inDegree[i] >= 0) charCount++;
        }

        std::string order;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            order += (char)('a' + u);
            for (int v : adj[u]) {
                if (--inDegree[v] == 0) q.push(v);
            }
        }

        return (int)order.size() == charCount ? order : "";
    }
};
```

### Parallel Courses (LeetCode 1136)

**Problem:** There are `n` courses with prerequisites. You can take any number of courses in parallel as long as prerequisites are met. Find the minimum number of semesters to complete all courses.

**Approach:** BFS level by level — each level is one semester. Vertices with in-degree 0 at each level can be taken in parallel.

```cpp
#include <vector>
#include <queue>

class Solution {
public:
    int minimumSemesters(int n, std::vector<std::vector<int>>& relations) {
        std::vector<std::vector<int>> adj(n + 1); // 1-indexed
        std::vector<int> inDegree(n + 1, 0);

        for (auto& r : relations) {
            adj[r[0]].push_back(r[1]);
            inDegree[r[1]]++;
        }

        std::queue<int> q;
        for (int i = 1; i <= n; ++i) {
            if (inDegree[i] == 0) q.push(i);
        }

        int semesters = 0, taken = 0;
        while (!q.empty()) {
            int size = q.size();
            semesters++;
            for (int i = 0; i < size; ++i) {
                int u = q.front(); q.pop();
                taken++;
                for (int v : adj[u]) {
                    if (--inDegree[v] == 0) q.push(v);
                }
            }
        }

        return taken == n ? semesters : -1;
    }
};
```

---

## See Also

- [Chapter 23: Depth-First Search](ch23-dfs.md) — DFS-based topological sort (post-order reversal) is the classic approach; Kahn's BFS-based algorithm is the alternative.
- [Chapter 24: Breadth-First Search](ch24-bfs.md) — Kahn's algorithm uses BFS (indegree-based) for topological ordering; also detects cycles.
- [Chapter 81: SCC, Bridges, and Articulation Points](ch81-scc-bridges.md) — Kosaraju's algorithm uses two-pass DFS; SCC condensation produces a DAG suitable for topological sort.
- [Chapter 26: Shortest Paths](ch26-shortest-paths.md) — On DAGs, shortest paths can be found in O(V+E) by processing vertices in topological order.
- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — Prerequisite: DAGs, indegree, and graph representations.

*Next chapter: Shortest Paths — from Dijkstra to Bellman-Ford to Floyd-Warshall.*
