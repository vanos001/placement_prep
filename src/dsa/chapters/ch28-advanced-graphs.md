# Chapter 28: Advanced Graph Algorithms

This chapter covers graph algorithms that go beyond basic traversal and shortest paths. These algorithms — strongly connected components, bridges and articulation points, Euler paths, bipartite checking, and graph coloring — are favorites in technical interviews because they test deep understanding of graph structure.

---

## 28.1 Strongly Connected Components

A **Strongly Connected Component (SCC)** of a directed graph is a maximal set of vertices such that there is a directed path from every vertex to every other vertex in the set.

### Kosaraju's Algorithm

**Idea:** Two-pass DFS.
1. Run DFS on the original graph, recording finish times.
2. Transpose the graph (reverse all edges).
3. Run DFS on the transposed graph in decreasing order of finish times. Each DFS tree in this pass is an SCC.

**Why it works:** In the transposed graph, the SCC with the highest finish time in the first pass has no edges going to other SCCs (in the transposed graph). So DFS from that vertex stays within its SCC.

```cpp
#include <iostream>
#include <vector>
#include <stack>
#include <algorithm>

class Kosaraju {
public:
    static std::vector<std::vector<int>> findSCCs(
        int V, const std::vector<std::vector<int>>& adj) {

        // Step 1: DFS to get finish order
        std::vector<bool> visited(V, false);
        std::stack<int> finishOrder;

        std::function<void(int)> dfs1 = [&](int u) {
            visited[u] = true;
            for (int v : adj[u]) {
                if (!visited[v]) dfs1(v);
            }
            finishOrder.push(u);
        };

        for (int i = 0; i < V; ++i) {
            if (!visited[i]) dfs1(i);
        }

        // Step 2: Build transposed graph
        std::vector<std::vector<int>> adjT(V);
        for (int u = 0; u < V; ++u) {
            for (int v : adj[u]) {
                adjT[v].push_back(u);
            }
        }

        // Step 3: DFS on transposed graph in finish order
        std::fill(visited.begin(), visited.end(), false);
        std::vector<std::vector<int>> sccs;

        std::function<void(int, std::vector<int>&)> dfs2 = [&](int u, std::vector<int>& component) {
            visited[u] = true;
            component.push_back(u);
            for (int v : adjT[u]) {
                if (!visited[v]) dfs2(v, component);
            }
        };

        while (!finishOrder.empty()) {
            int u = finishOrder.top();
            finishOrder.pop();
            if (!visited[u]) {
                std::vector<int> component;
                dfs2(u, component);
                sccs.push_back(component);
            }
        }
        return sccs;
    }
};

int main() {
    int V = 8;
    std::vector<std::vector<int>> adj(V);
    auto addEdge = [&](int u, int v) { adj[u].push_back(v); };

    addEdge(0, 1);
    addEdge(1, 2);
    addEdge(2, 0); // SCC: {0, 1, 2}
    addEdge(2, 3);
    addEdge(3, 4);
    addEdge(4, 5);
    addEdge(5, 3); // SCC: {3, 4, 5}
    addEdge(5, 6);
    addEdge(6, 7); // SCC: {6}, {7}

    auto sccs = Kosaraju::findSCCs(V, adj);
    std::cout << "Number of SCCs: " << sccs.size() << "\n";
    for (int i = 0; i < (int)sccs.size(); ++i) {
        std::cout << "SCC " << i << ": ";
        for (int v : sccs[i]) std::cout << v << " ";
        std::cout << "\n";
    }
}
```

**Time:** \\(O(V + E)\\) — two DFS passes.

### Tarjan's Algorithm

**Idea:** Single-pass DFS using a stack and tracking **discovery times** and **low-link values**.

- `disc[u]`: discovery time of \\(u\\).
- `low[u]`: the smallest discovery time reachable from the subtree rooted at \\(u\\) (including back edges to vertices currently on the stack).
- Vertices are pushed onto a stack when discovered. When `low[u] == disc[u]`, \\(u\\) is the root of an SCC — pop all vertices above \\(u\\) on the stack.

```cpp
#include <iostream>
#include <vector>
#include <stack>
#include <algorithm>

class TarjanSCC {
    int V;
    std::vector<std::vector<int>> adj;
    std::vector<int> disc, low;
    std::vector<bool> onStack;
    std::stack<int> stk;
    int timer;
    std::vector<std::vector<int>> sccs;

public:
    TarjanSCC(int V) : V(V), adj(V), disc(V, -1), low(V, -1),
                        onStack(V, false), timer(0) {}

    void addEdge(int u, int v) { adj[u].push_back(v); }

    void dfs(int u) {
        disc[u] = low[u] = timer++;
        stk.push(u);
        onStack[u] = true;

        for (int v : adj[u]) {
            if (disc[v] == -1) {
                // Tree edge
                dfs(v);
                low[u] = std::min(low[u], low[v]);
            } else if (onStack[v]) {
                // Back edge to vertex on stack (part of current SCC)
                low[u] = std::min(low[u], disc[v]);
            }
        }

        // If u is root of an SCC
        if (low[u] == disc[u]) {
            std::vector<int> component;
            while (true) {
                int v = stk.top();
                stk.pop();
                onStack[v] = false;
                component.push_back(v);
                if (v == u) break;
            }
            sccs.push_back(component);
        }
    }

    std::vector<std::vector<int>> findSCCs() {
        for (int i = 0; i < V; ++i) {
            if (disc[i] == -1) dfs(i);
        }
        return sccs;
    }
};

int main() {
    TarjanSCC g(8);
    g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
    g.addEdge(2, 3); g.addEdge(3, 4); g.addEdge(4, 5);
    g.addEdge(5, 3); g.addEdge(5, 6); g.addEdge(6, 7);

    auto sccs = g.findSCCs();
    std::cout << "Number of SCCs: " << sccs.size() << "\n";
    for (int i = 0; i < (int)sccs.size(); ++i) {
        std::cout << "SCC " << i << ": ";
        for (int v : sccs[i]) std::cout << v << " ";
        std::cout << "\n";
    }
}
```

**Time:** \\(O(V + E)\\) — single DFS pass.

### Dry Run (Tarjan's)

Graph: `0→1, 1→2, 2→0, 2→3, 3→4, 4→5, 5→3, 5→6, 6→7`

| Step | Vertex | disc | low | Stack | Action |
|------|--------|------|-----|-------|--------|
| 1 | 0 | 0 | 0 | [0] | Discover 0 |
| 2 | 1 | 1 | 1 | [0,1] | Discover 1 |
| 3 | 2 | 2 | 0 | [0,1,2] | Discover 2; low[2]=min(2,disc[0])=0 via back edge |
| 4 | 3 | 3 | 3 | [0,1,2,3] | Discover 3 |
| 5 | 4 | 4 | 4 | [0,1,2,3,4] | Discover 4 |
| 6 | 5 | 5 | 3 | [0,1,2,3,4,5] | Discover 5; low[5]=min(5,disc[3])=3 via back edge |
| 7 | — | — | — | [0,1,2] | low[5]==disc[3]? No. Backtrack: low[4]=3, low[3]=3. low[3]==disc[3]=3 → pop SCC {3,4,5} |
| 8 | — | — | — | [0,1,2] | low[2]=min(0,3)=0. low[1]=min(1,0)=0. low[0]=min(0,0)=0. low[0]==disc[0]=0 → pop SCC {0,1,2} |
| 9 | 6 | 6 | 6 | [6] | Discover 6 |
| 10 | 7 | 7 | 7 | [6,7] | Discover 7. low[7]==disc[7]=7 → pop SCC {7} |
| 11 | — | — | — | [6] | low[6]==disc[6]=6 → pop SCC {6} |

SCCs: `{3,4,5}`, `{0,1,2}`, `{7}`, `{6}` ✓

---

## 28.2 Bridges and Articulation Points

### Definitions

- **Bridge** (cut edge): an edge whose removal disconnects the graph (increases the number of connected components).
- **Articulation point** (cut vertex): a vertex whose removal (and its edges) disconnects the graph.

### Finding Bridges (Tarjan's Bridge Finding)

Use DFS with discovery times and low-link values. An edge \\((u, v)\\) (tree edge, where \\(u\\) is the parent) is a bridge if and only if `low[v] > disc[u]`. This means no vertex in the subtree of \\(v\\) can reach \\(u\\) or any ancestor of \\(u\\).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class BridgeFinder {
    int V;
    std::vector<std::vector<int>> adj;
    std::vector<int> disc, low;
    std::vector<std::pair<int, int>> bridges;
    int timer;

public:
    BridgeFinder(int V) : V(V), adj(V), disc(V, -1), low(V, -1), timer(0) {}

    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    void dfs(int u, int parent) {
        disc[u] = low[u] = timer++;

        for (int v : adj[u]) {
            if (v == parent) continue; // don't go back through parent
            if (disc[v] == -1) {
                dfs(v, u);
                low[u] = std::min(low[u], low[v]);
                if (low[v] > disc[u]) {
                    bridges.push_back({u, v});
                }
            } else {
                // Back edge
                low[u] = std::min(low[u], disc[v]);
            }
        }
    }

    std::vector<std::pair<int, int>> findBridges() {
        for (int i = 0; i < V; ++i) {
            if (disc[i] == -1) dfs(i, -1);
        }
        return bridges;
    }
};

int main() {
    BridgeFinder g(5);
    g.addEdge(0, 1);
    g.addEdge(1, 2);
    g.addEdge(2, 0); // cycle: no bridge
    g.addEdge(1, 3);
    g.addEdge(3, 4); // bridge!

    auto bridges = g.findBridges();
    std::cout << "Bridges:\n";
    for (auto [u, v] : bridges) {
        std::cout << "  " << u << " -- " << v << "\n";
    }
}
```

**Time:** \\(O(V + E)\\).

### Finding Articulation Points

A vertex \\(u\\) is an articulation point if:
- \\(u\\) is the root of the DFS tree and has \\(\geq 2\\) children, OR
- \\(u\\) is not the root and has a child \\(v\\) with `low[v] >= disc[u]`.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class ArticulationFinder {
    int V;
    std::vector<std::vector<int>> adj;
    std::vector<int> disc, low;
    std::vector<bool> isArticulation;
    int timer;

public:
    ArticulationFinder(int V) : V(V), adj(V), disc(V, -1), low(V, -1),
                                 isArticulation(V, false), timer(0) {}

    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    void dfs(int u, int parent) {
        disc[u] = low[u] = timer++;
        int children = 0;

        for (int v : adj[u]) {
            if (v == parent) continue;
            if (disc[v] == -1) {
                children++;
                dfs(v, u);
                low[u] = std::min(low[u], low[v]);

                // Root with 2+ children
                if (parent == -1 && children >= 2) isArticulation[u] = true;
                // Non-root: child can't reach above u
                if (parent != -1 && low[v] >= disc[u]) isArticulation[u] = true;
            } else {
                low[u] = std::min(low[u], disc[v]);
            }
        }
    }

    std::vector<int> findArticulationPoints() {
        for (int i = 0; i < V; ++i) {
            if (disc[i] == -1) dfs(i, -1);
        }
        std::vector<int> result;
        for (int i = 0; i < V; ++i) {
            if (isArticulation[i]) result.push_back(i);
        }
        return result;
    }
};

int main() {
    ArticulationFinder g(7);
    g.addEdge(0, 1);
    g.addEdge(1, 2);
    g.addEdge(2, 0);
    g.addEdge(1, 3);
    g.addEdge(1, 4);
    g.addEdge(3, 4);
    g.addEdge(1, 5);
    g.addEdge(5, 6);

    auto points = g.findArticulationPoints();
    std::cout << "Articulation points: ";
    for (int v : points) std::cout << v << " ";
    std::cout << "\n";
    // 1 is an articulation point (connecting {0,1,2} to {3,4} and {5,6})
    // 5 is an articulation point (connecting {5} to {6})
}
```

---

## 28.3 Euler Paths and Circuits

### Definitions

- **Euler path**: a path that visits every *edge* exactly once.
- **Euler circuit**: an Euler path that starts and ends at the same vertex.

### Conditions

**Undirected graph:**
- Euler circuit exists ↔ every vertex has even degree AND the graph is connected (considering edges).
- Euler path exists ↔ exactly 0 or 2 vertices have odd degree.

**Directed graph:**
- Euler circuit exists ↔ every vertex has equal in-degree and out-degree AND the graph is weakly connected.
- Euler path exists ↔ exactly one vertex has `out-deg = in-deg + 1` (start), one has `in-deg = out-deg + 1` (end), and all others are equal.

### Hierholzer's Algorithm

Finds an Euler circuit/path in \\(O(E)\\) time.

**Idea:** Start from an appropriate vertex. Follow edges, removing them as you go. When stuck (no more outgoing edges), backtrack and insert the current vertex into the circuit.

```cpp
#include <iostream>
#include <vector>
#include <stack>
#include <algorithm>

class EulerPath {
public:
    // For undirected graph
    static std::vector<int> findEulerPathUndirected(
        int V, std::vector<std::pair<int, int>> edges) {

        std::vector<std::vector<std::pair<int, int>>> adj(V);
        for (int i = 0; i < (int)edges.size(); ++i) {
            auto [u, v] = edges[i];
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }

        // Find start vertex (odd degree if exists, else any)
        int start = 0;
        for (int i = 0; i < V; ++i) {
            if (adj[i].size() % 2 == 1) { start = i; break; }
        }

        std::vector<int> path;
        std::vector<bool> usedEdge(edges.size(), false);
        std::stack<int> stk;
        stk.push(start);

        while (!stk.empty()) {
            int u = stk.top();
            bool found = false;
            while (!adj[u].empty()) {
                auto [v, edgeId] = adj[u].back();
                adj[u].pop_back();
                if (!usedEdge[edgeId]) {
                    usedEdge[edgeId] = true;
                    stk.push(v);
                    found = true;
                    break;
                }
            }
            if (!found) {
                path.push_back(u);
                stk.pop();
            }
        }

        std::reverse(path.begin(), path.end());
        return path;
    }

    // For directed graph
    static std::vector<int> findEulerPathDirected(
        int V, std::vector<std::pair<int, int>> edges) {

        std::vector<std::vector<int>> adj(V);
        std::vector<int> inDeg(V, 0), outDeg(V, 0);
        for (auto [u, v] : edges) {
            adj[u].push_back(v);
            outDeg[u]++;
            inDeg[v]++;
        }

        // Find start vertex
        int start = 0;
        for (int i = 0; i < V; ++i) {
            if (outDeg[i] - inDeg[i] == 1) { start = i; break; }
            if (outDeg[i] > 0) start = i;
        }

        std::vector<int> path;
        std::stack<int> stk;
        stk.push(start);

        while (!stk.empty()) {
            int u = stk.top();
            if (!adj[u].empty()) {
                int v = adj[u].back();
                adj[u].pop_back();
                stk.push(v);
            } else {
                path.push_back(u);
                stk.pop();
            }
        }

        std::reverse(path.begin(), path.end());
        return path;
    }
};
```

**Time:** \\(O(E)\\) — each edge is traversed exactly once.

---

## 28.4 Bipartite Graphs

A graph is **bipartite** if its vertices can be 2-colored such that no two adjacent vertices share the same color. Equivalently, a graph is bipartite if and only if it has no odd-length cycle.

### BFS/DFS 2-Coloring Check

```cpp
#include <vector>
#include <queue>

bool isBipartite(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> color(V, -1);

    for (int start = 0; start < V; ++start) {
        if (color[start] != -1) continue;

        std::queue<int> q;
        color[start] = 0;
        q.push(start);

        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (color[v] == -1) {
                    color[v] = 1 - color[u];
                    q.push(v);
                } else if (color[v] == color[u]) {
                    return false; // odd cycle detected
                }
            }
        }
    }
    return true;
}
```

### Finding the Bipartition

```cpp
#include <vector>
#include <queue>
#include <utility>

std::pair<std::vector<int>, std::vector<int>> findBipartition(
    const std::vector<std::vector<int>>& adj, int V) {

    std::vector<int> color(V, -1);
    std::vector<int> left, right;

    for (int start = 0; start < V; ++start) {
        if (color[start] != -1) continue;
        std::queue<int> q;
        color[start] = 0;
        q.push(start);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (color[v] == -1) {
                    color[v] = 1 - color[u];
                    q.push(v);
                }
            }
        }
    }

    for (int i = 0; i < V; ++i) {
        if (color[i] == 0) left.push_back(i);
        else right.push_back(i);
    }
    return {left, right};
}
```

---

## 28.5 Graph Coloring

### Greedy Coloring

Given a graph, assign colors to vertices such that no two adjacent vertices share the same color, using as few colors as possible. Finding the **chromatic number** (minimum colors needed) is NP-hard, but greedy coloring gives a reasonable approximation.

```cpp
#include <iostream>
#include <vector>
#include <set>

std::vector<int> greedyColor(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> color(V, -1);
    color[0] = 0; // first vertex gets color 0

    for (int u = 1; u < V; ++u) {
        // Find colors used by neighbors
        std::set<int> usedColors;
        for (int v : adj[u]) {
            if (color[v] != -1) usedColors.insert(color[v]);
        }
        // Assign smallest available color
        int c = 0;
        while (usedColors.count(c)) c++;
        color[u] = c;
    }
    return color;
}

int main() {
    int V = 5;
    std::vector<std::vector<int>> adj(V);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };
    addEdge(0, 1); addEdge(0, 2); addEdge(1, 2);
    addEdge(1, 3); addEdge(2, 3); addEdge(3, 4);

    auto color = greedyColor(adj, V);
    int maxColor = *std::max_element(color.begin(), color.end());
    std::cout << "Colors used: " << maxColor + 1 << "\n";
    for (int i = 0; i < V; ++i) {
        std::cout << "  Vertex " << i << ": color " << color[i] << "\n";
    }
}
```

**Greedy coloring guarantees** using at most \\(\Delta + 1\\) colors, where \\(\Delta\\) is the maximum degree. The actual chromatic number could be much smaller.

### Chromatic Number Overview

- **Bipartite graph:** chromatic number = 2.
- **Complete graph \\(K_n\\):** chromatic number = \\(n\\).
- **Cycle \\(C_n\\):** chromatic number = 2 (even \\(n\\)) or 3 (odd \\(n\\)).
- **Planar graph:** chromatic number ≤ 4 (Four Color Theorem).
- **General graph:** NP-hard to compute exactly.

---

## Interview Tips

1. **SCCs:** If the problem involves a directed graph and asks about "groups of mutually reachable vertices," think SCCs. After finding SCCs, you can compress them into a DAG (the **condensation graph**).
2. **Bridges/articulation points:** If the problem asks about "critical connections" or "network reliability," use Tarjan's algorithm.
3. **Euler path:** If the problem asks to traverse every *edge* exactly once, it's an Euler path problem (not Hamiltonian — that's NP-hard).
4. **Bipartite:** If the problem involves 2-grouping or matching, check bipartiteness first.
5. **Condensation graph:** After finding SCCs, compress each SCC into a single node. The resulting graph is a DAG, enabling topological sort and DP.

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Confusing Euler path with Hamiltonian path | Mixing \\(O(E)\\) with NP-hard | Euler = every edge, Hamiltonian = every vertex |
| Not handling multiple components in bridge/SCC | Missing results | Outer loop over all vertices |
| Using `disc[v]` vs `low[v]` incorrectly in Tarjan's | Wrong low-link computation | `low[u] = min(low[u], disc[v])` for back edges |
| Forgetting to handle self-loops in coloring | Wrong color assignment | Skip self-edges or handle explicitly |

## Practice Problems

### Critical Connections in a Network (LeetCode 1192)

**Problem:** Given `n` servers and connections, find all critical connections (bridges).

```cpp
#include <vector>
#include <algorithm>

class Solution {
public:
    int timer = 0;
    std::vector<int> disc, low;
    std::vector<std::vector<int>> adj;
    std::vector<std::vector<int>> bridges;

    void dfs(int u, int parent) {
        disc[u] = low[u] = timer++;
        for (int v : adj[u]) {
            if (v == parent) continue;
            if (disc[v] == -1) {
                dfs(v, u);
                low[u] = std::min(low[u], low[v]);
                if (low[v] > disc[u]) {
                    bridges.push_back({u, v});
                }
            } else {
                low[u] = std::min(low[u], disc[v]);
            }
        }
    }

    std::vector<std::vector<int>> criticalConnections(
        int n, std::vector<std::vector<int>>& connections) {

        adj.assign(n, {});
        disc.assign(n, -1);
        low.assign(n, -1);
        timer = 0;

        for (auto& c : connections) {
            adj[c[0]].push_back(c[1]);
            adj[c[1]].push_back(c[0]);
        }

        for (int i = 0; i < n; ++i) {
            if (disc[i] == -1) dfs(i, -1);
        }
        return bridges;
    }
};
```

### Redundant Connection II (LeetCode 685)

**Problem:** In a directed graph that was originally a rooted tree, one extra edge was added. Find it. The answer could be a back edge creating a cycle, or an edge giving a node two parents.

**Approach:** Handle three cases: (1) node has two parents but no cycle, (2) node has two parents and there's a cycle, (3) no node has two parents but there's a cycle.

```cpp
#include <vector>
#include <functional>

class Solution {
public:
    std::vector<int> findRedundantDirectedConnection(
        std::vector<std::vector<int>>& edges) {

        int n = edges.size();
        std::vector<int> parent(n + 1, 0);
        std::vector<int> cand1, cand2;

        // Step 1: Check for node with two parents
        for (auto& e : edges) {
            int u = e[0], v = e[1];
            if (parent[v] == 0) {
                parent[v] = u;
            } else {
                cand1 = {parent[v], v};
                cand2 = e;
                e[1] = 0; // "remove" this edge temporarily
            }
        }

        // Step 2: Union-Find to check for cycle
        std::vector<int> uf(n + 1);
        for (int i = 0; i <= n; ++i) uf[i] = i;
        std::function<int(int)> find = [&](int x) {
            return uf[x] == x ? x : uf[x] = find(uf[x]);
        };

        for (auto& e : edges) {
            int u = e[0], v = e[1];
            if (v == 0) continue; // removed edge
            int ru = find(u), rv = find(v);
            if (ru == rv) {
                // Cycle found
                if (cand1.empty()) return e; // Case 3: no two-parent issue
                return cand1; // Case 2: cycle + two parents → remove first candidate
            }
            uf[rv] = ru;
        }
        return cand2; // Case 1: two parents, no cycle → remove second candidate
    }
};
```

### Is Graph Bipartite? (LeetCode 785)

*Solution: See the BFS 2-coloring code in Section 28.4 above.*

---

## See Also

- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — Prerequisite: graph representations, adjacency lists, and basic terminology.
- [Chapter 23: Depth-First Search](ch23-dfs.md) — DFS is the backbone of many advanced graph algorithms covered here.
- [Chapter 29: Network Flow](ch29-network-flow.md) — Flow algorithms are the natural next step after mastering advanced graph techniques.
- [Chapter 81: SCC, Bridges, and Articulation Points](ch81-scc-bridges.md) — Strongly connected components and connectivity analysis.
- [Chapter 82: Advanced Shortest Paths](ch82-advanced-shortest-paths.md) — Johnson's algorithm, A*, and other advanced shortest path techniques.
- [Chapter 27: Minimum Spanning Tree](ch27-mst.md) — Kruskal's and Prim's algorithms; a foundational graph algorithm.

*Next chapter: Network Flow — the theory of flows, cuts, and their powerful applications.*
