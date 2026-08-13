# Chapter 27: Minimum Spanning Trees

A Minimum Spanning Tree (MST) of a connected, weighted, undirected graph is a subset of edges that connects all vertices with the minimum possible total edge weight, without forming cycles. MSTs are fundamental in network design, clustering, and approximation algorithms.

In this chapter, we explore the theory behind MSTs and the two dominant algorithms: Kruskal's and Prim's.

---

## 27.1 What Is an MST?

### Definition

Given a connected, undirected graph \\(G = (V, E)\\) with edge weights \\(w: E \to \mathbb{R}\\), a **Minimum Spanning Tree** is a spanning subgraph \\(T = (V, E')\\) where:
- \\(T\\) is connected and acyclic (i.e., a tree).
- \\(|E'| = |V| - 1\\).
- The total weight \\(\sum_{e \in E'} w(e)\\) is minimized among all spanning trees.

### Properties

**Property 1: Not necessarily unique.** If multiple edges have the same weight, there may be several MSTs with the same total weight.

**Property 2: Cut Property.** For any cut \\((S, V \setminus S)\\), the minimum-weight edge crossing the cut is in some MST. This is the theoretical foundation for both Kruskal's and Prim's algorithms.

*Proof sketch:* Suppose the minimum crossing edge \\(e = (u, v)\\) with \\(u \in S, v \notin S\\) is not in an MST \\(T\\). Adding \\(e\\) to \\(T\\) creates a cycle. This cycle must cross the cut again via some edge \\(e'\\). Since \\(w(e) \leq w(e')\\), replacing \\(e'\\) with \\(e\\) yields a spanning tree of weight \\(\leq w(T)\\), so \\(e\\) can be in an MST. ∎

**Property 3: Cycle Property.** For any cycle in the graph, the maximum-weight edge in the cycle is not in any MST.

*Proof sketch:* If the heaviest edge \\(e\\) in a cycle were in an MST, removing it splits the tree into two components. The cycle contains another edge \\(e'\\) crossing between these components. Replacing \\(e\\) with \\(e'\\) gives a lighter spanning tree. ∎

**Property 4:** An MST has exactly \\(|V| - 1\\) edges (tree property).

---

## 27.2 Kruskal's Algorithm

### Idea

Kruskal's algorithm is a **greedy** approach that processes edges in order of increasing weight:

1. Sort all edges by weight.
2. For each edge (in sorted order), add it to the MST if it doesn't create a cycle.
3. Stop when we have \\(|V| - 1\\) edges.

**Cycle detection** is done efficiently using a **Disjoint Set Union (DSU)** / **Union-Find** data structure.

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <tuple>

class DSU {
    std::vector<int> parent, rank_;

public:
    DSU(int n) : parent(n), rank_(n, 0) {
        for (int i = 0; i < n; ++i) parent[i] = i;
    }

    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]); // path compression
        return parent[x];
    }

    bool unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false; // already in same set → cycle
        if (rank_[x] < rank_[y]) std::swap(x, y);
        parent[y] = x;
        if (rank_[x] == rank_[y]) rank_[x]++;
        return true;
    }
};

class Kruskal {
public:
    struct Edge {
        int u, v, w;
        bool operator<(const Edge& other) const { return w < other.w; }
    };

    // Returns {totalWeight, mstEdges}, or {-1, {}} if graph is disconnected
    static std::pair<long long, std::vector<Edge>> solve(
        int V, std::vector<Edge> edges) {

        std::sort(edges.begin(), edges.end());

        DSU dsu(V);
        long long totalWeight = 0;
        std::vector<Edge> mst;

        for (auto& e : edges) {
            if (dsu.unite(e.u, e.v)) {
                totalWeight += e.w;
                mst.push_back(e);
                if ((int)mst.size() == V - 1) break;
            }
        }

        if ((int)mst.size() != V - 1) return {-1, {}}; // disconnected
        return {totalWeight, mst};
    }
};

int main() {
    int V = 6;
    std::vector<Kruskal::Edge> edges = {
        {0, 1, 4}, {0, 2, 3}, {1, 2, 1}, {1, 3, 2},
        {2, 3, 4}, {3, 4, 2}, {4, 5, 6}, {2, 4, 5}
    };

    auto [weight, mst] = Kruskal::solve(V, edges);
    if (weight == -1) {
        std::cout << "Graph is disconnected\n";
    } else {
        std::cout << "MST weight: " << weight << "\n";
        std::cout << "MST edges:\n";
        for (auto& e : mst) {
            std::cout << "  " << e.u << " -- " << e.v << " (weight " << e.w << ")\n";
        }
    }
}
```

**Time Complexity:** \\(O(E \log E)\\) for sorting + \\(O(E \cdot \alpha(V))\\) for DSU operations ≈ \\(O(E \log E)\\).

**Space Complexity:** \\(O(V + E)\\).

### Dry Run

Edges sorted by weight: `(1,2,1), (1,3,2), (3,4,2), (0,2,3), (0,1,4), (2,3,4), (2,4,5), (4,5,6)`

| Step | Edge | Weight | Action | DSU Components | MST Weight |
|------|------|--------|--------|---------------|------------|
| 1 | 1-2 | 1 | Add | {0} {1,2} {3} {4} {5} | 1 |
| 2 | 1-3 | 2 | Add | {0} {1,2,3} {4} {5} | 3 |
| 3 | 3-4 | 2 | Add | {0} {1,2,3,4} {5} | 5 |
| 4 | 0-2 | 3 | Add | {0,1,2,3,4} {5} | 8 |
| 5 | 0-1 | 4 | Skip (cycle) | — | 8 |
| 6 | 2-3 | 4 | Skip (cycle) | — | 8 |
| 7 | 2-4 | 5 | Skip (cycle) | — | 8 |
| 8 | 4-5 | 6 | Add | {0,1,2,3,4,5} | 14 |

MST weight: **14**. Edges: `1-2, 1-3, 3-4, 0-2, 4-5`.

---

## 27.3 Prim's Algorithm

### Idea

Prim's algorithm grows the MST from a single starting vertex. At each step, it adds the minimum-weight edge connecting a vertex in the MST to a vertex outside the MST. This is essentially Dijkstra's algorithm but for MST instead of shortest paths.

### Implementation (Priority Queue)

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <utility>
#include <climits>

class Prim {
public:
    // Returns {totalWeight, mstEdges} or {-1, {}} if disconnected
    static std::pair<long long, std::vector<std::pair<int, int>>> solve(
        int V, const std::vector<std::vector<std::pair<int, int>>>& adj) {

        std::vector<bool> inMST(V, false);
        std::vector<long long> key(V, LLONG_MAX);
        std::vector<int> parent(V, -1);
        // Min-heap: (key, vertex)
        std::priority_queue<std::pair<long long, int>,
                            std::vector<std::pair<long long, int>>,
                            std::greater<>> pq;

        key[0] = 0;
        pq.push({0, 0});
        long long totalWeight = 0;
        int edgesUsed = 0;

        while (!pq.empty() && edgesUsed < V) {
            auto [k, u] = pq.top();
            pq.pop();

            if (inMST[u]) continue;
            inMST[u] = true;
            totalWeight += k;
            edgesUsed++;

            for (auto [v, w] : adj[u]) {
                if (!inMST[v] && w < key[v]) {
                    key[v] = w;
                    parent[v] = u;
                    pq.push({w, v});
                }
            }
        }

        if (edgesUsed != V) return {-1, {}}; // disconnected

        std::vector<std::pair<int, int>> mst;
        for (int i = 1; i < V; ++i) {
            mst.push_back({parent[i], i});
        }
        return {totalWeight, mst};
    }
};

int main() {
    int V = 6;
    std::vector<std::vector<std::pair<int, int>>> adj(V);
    auto addEdge = [&](int u, int v, int w) {
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    };

    addEdge(0, 1, 4);
    addEdge(0, 2, 3);
    addEdge(1, 2, 1);
    addEdge(1, 3, 2);
    addEdge(2, 3, 4);
    addEdge(3, 4, 2);
    addEdge(4, 5, 6);
    addEdge(2, 4, 5);

    auto [weight, mst] = Prim::solve(V, adj);
    if (weight == -1) {
        std::cout << "Graph is disconnected\n";
    } else {
        std::cout << "MST weight: " << weight << "\n";
        std::cout << "MST edges:\n";
        for (auto [u, v] : mst) {
            std::cout << "  " << u << " -- " << v << "\n";
        }
    }
}
```

**Time Complexity:** \\(O(E \log V)\\) with a binary heap. Each vertex is extracted once (\\(O(V \log V)\\)), and each edge may cause a push (\\(O(E \log V)\\)).

**Space Complexity:** \\(O(V + E)\\).

### Dry Run

Starting from vertex 0.

| Step | In MST | PQ (key, vertex) | Added | key[] |
|------|--------|-----------------|-------|-------|
| Init | {0} | (3,2), (4,1) | — | [0,4,3,∞,∞,∞] |
| 1 | {0,2} | (1,1), (4,1), (4,3), (5,4) | 2 | [0,1,3,4,5,∞] |
| 2 | {0,2,1} | (2,3), (4,1), (4,3), (5,4) | 1 | [0,1,3,2,5,∞] |
| 3 | {0,2,1,3} | (2,4), (4,1), (4,3), (5,4) | 3 | [0,1,3,2,2,∞] |
| 4 | {0,2,1,3,4} | (6,5), (4,1), (5,4) | 4 | [0,1,3,2,2,6] |
| 5 | {0,2,1,3,4,5} | (6,5) | 5 | [0,1,3,2,2,6] |

MST weight: 0 + 3 + 1 + 2 + 2 + 6 = **14** ✓

### Kruskal's vs Prim's vs Borůvka's

| Aspect | Kruskal's | Prim's | Borůvka's |
|--------|----------|--------|----------|
| Approach | Edge-centric (global greedy) | Vertex-centric (local greedy) | Component-centric (parallel) |
| Data structure | DSU / Union-Find | Priority queue | DSU / Union-Find |
| **Time Complexity** | \\(O(E \log E)\\) | \\(O(E \log V)\\) | \\(O(E \log V)\\) |
| **Space Complexity** | \\(O(V + E)\\) | \\(O(V + E)\\) | \\(O(V + E)\\) |
| **Stable?** | N/A (graph algorithm) | N/A (graph algorithm) | N/A (graph algorithm) |
| **In-place?** | No (needs DSU arrays) | No (needs PQ) | No (needs DSU arrays) |
| Best for | Sparse graphs (\\(E \ll V^2\\)) | Dense graphs (\\(E \approx V^2\\)) | Parallel / distributed settings |
| Works on disconnected | Naturally (produces MSF) | Needs modification | Naturally (produces MSF) |
| Implementation | Requires edge list | Requires adjacency list | Requires adjacency list |
| Parallel-friendly | Yes (sorting can be parallelized) | Less so | Yes (components independent) |
| **Notes** | Easiest to implement; most common in interviews | Faster with Fibonacci heap: \\(O(E + V \log V)\\) | Oldest MST algorithm; halves components each round |

---

## 27.4 Borůvka's Algorithm

### Idea

Borůvka's algorithm is the oldest MST algorithm (1926). It processes all components simultaneously:

1. Initialize each vertex as its own component.
2. For each component, find the minimum-weight edge connecting it to another component.
3. Add all such edges simultaneously.
4. Repeat until there's one component.

### Implementation

```cpp
#include <iostream>
#include <vector>
#include <tuple>
#include <climits>

long long boruvka(int V, const std::vector<std::tuple<int, int, int>>& edges) {
    // Component ID for each vertex
    std::vector<int> comp(V);
    for (int i = 0; i < V; ++i) comp[i] = i;

    long long totalWeight = 0;
    int numComponents = V;

    while (numComponents > 1) {
        // For each component, find cheapest outgoing edge
        std::vector<std::pair<int, int>> cheapest(V, {-1, INT_MAX});
        // cheapest[c] = {edge_index, weight} for component c

        for (int i = 0; i < (int)edges.size(); ++i) {
            auto [u, v, w] = edges[i];
            int cu = comp[u], cv = comp[v];
            if (cu == cv) continue;

            if (w < cheapest[cu].second) cheapest[cu] = {i, w};
            if (w < cheapest[cv].second) cheapest[cv] = {i, w};
        }

        // Add cheapest edges
        bool added = false;
        for (int c = 0; c < V; ++c) {
            if (cheapest[c].first == -1) continue;
            auto [u, v, w] = edges[cheapest[c].first];
            int cu = comp[u], cv = comp[v];
            if (cu != cv) {
                totalWeight += w;
                // Merge components
                int old = cv, replacement = cu;
                for (int i = 0; i < V; ++i) {
                    if (comp[i] == old) comp[i] = replacement;
                }
                numComponents--;
                added = true;
            }
        }
        if (!added) break; // disconnected graph
    }
    return totalWeight;
}
```

**Time Complexity:** \\(O(E \log V)\\) — each iteration halves the number of components.

**Key advantage:** Each iteration is embarrassingly parallel. Borůvka's is the algorithm of choice for parallel MST computation.

---

## 27.5 Applications

### Network Design

MSTs minimize the cost of connecting all nodes in a network (telecommunications, water pipes, road networks).

```cpp
// Given cities and possible connections with costs,
// find minimum cost to connect all cities.
// This is literally the MST problem.
```

### Clustering (Single-Linkage)

By removing the \\(k-1\\) heaviest edges from an MST, we get \\(k\\) clusters. This is **single-linkage clustering**.

```cpp
#include <vector>
#include <algorithm>
#include <tuple>

std::vector<int> clusterByMST(int V, int k,
                               std::vector<std::tuple<int, int, int>> edges) {
    std::sort(edges.begin(), edges.end(),
              [](auto& a, auto& b) { return std::get<2>(a) < std::get<2>(b); });

    std::vector<int> parent(V), rank(V, 0);
    for (int i = 0; i < V; ++i) parent[i] = i;

    std::function<int(int)> find = [&](int x) {
        return parent[x] == x ? x : parent[x] = find(parent[x]);
    };

    auto unite = [&](int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        if (rank[x] < rank[y]) std::swap(x, y);
        parent[y] = x;
        if (rank[x] == rank[y]) rank[x]++;
        return true;
    };

    int edgesAdded = 0;
    for (auto [u, v, w] : edges) {
        if (unite(u, v)) {
            edgesAdded++;
            if (edgesAdded == V - k) break; // stop early: k clusters
        }
    }

    std::vector<int> labels(V);
    for (int i = 0; i < V; ++i) labels[i] = find(i);
    return labels;
}
```

### Approximation Algorithms

MSTs provide a 2-approximation for the **Traveling Salesman Problem (TSP)** on metric graphs: perform a DFS traversal of the MST and visit vertices in the order they're first discovered. The resulting tour is at most twice the optimal TSP tour.

---

## 27.6 Uniqueness and Variations

### Is the MST Unique?

The MST is unique if and only if all edge weights are distinct. When weights are tied, multiple MSTs may exist.

```cpp
// Check if MST is unique
bool isMSTUnique(const std::vector<std::tuple<int, int, int>>& edges) {
    // Sort edges and check for duplicate weights
    std::vector<int> weights;
    for (auto [u, v, w] : edges) weights.push_back(w);
    std::sort(weights.begin(), weights.end());
    for (int i = 1; i < (int)weights.size(); ++i) {
        if (weights[i] == weights[i - 1]) return false;
    }
    return true;
}
```

### Minimum Spanning Forest

For a disconnected graph, the MST becomes a **Minimum Spanning Forest (MSF)** — one MST per connected component. Kruskal's algorithm naturally produces an MSF.

### Second-Best MST

Find the spanning tree with the second-smallest total weight. The second-best MST differs from the MST by exactly one edge swap: remove one MST edge and add one non-MST edge.

```cpp
#include <vector>
#include <algorithm>
#include <tuple>
#include <functional>

long long secondBestMST(int V, std::vector<std::tuple<int, int, int>> edges) {
    // First find MST using Kruskal's
    std::sort(edges.begin(), edges.end(),
              [](auto& a, auto& b) { return std::get<2>(a) < std::get<2>(b); });

    std::vector<int> parent(V), rank(V, 0);
    for (int i = 0; i < V; ++i) parent[i] = i;
    std::function<int(int)> find = [&](int x) {
        return parent[x] == x ? x : parent[x] = find(parent[x]);
    };

    long long mstWeight = 0;
    std::vector<bool> inMST(edges.size(), false);
    std::vector<std::vector<std::pair<int, int>>> mstAdj(V);

    for (int i = 0; i < (int)edges.size(); ++i) {
        auto [u, v, w] = edges[i];
        int ru = find(u), rv = find(v);
        if (ru != rv) {
            if (rank[ru] < rank[rv]) std::swap(ru, rv);
            parent[rv] = ru;
            if (rank[ru] == rank[rv]) rank[ru]++;
            mstWeight += w;
            inMST[i] = true;
            mstAdj[u].push_back({v, w});
            mstAdj[v].push_back({u, w});
        }
    }

    // For each non-MST edge, find the heaviest edge on the path between its endpoints in the MST
    // The second-best MST is obtained by swapping the heaviest MST edge with this non-MST edge
    // This requires LCA preprocessing (beyond this example)
    // Simplified: just try removing each MST edge and adding each non-MST edge
    // O(E * V) approach
    long long secondBest = LLONG_MAX;
    for (int skip = 0; skip < (int)edges.size(); ++skip) {
        if (!inMST[skip]) continue;
        // Try MST without edge 'skip'
        std::fill(parent.begin(), parent.end(), 0);
        for (int i = 0; i < V; ++i) parent[i] = i;
        std::fill(rank.begin(), rank.end(), 0);

        long long weight = 0;
        int edgesUsed = 0;
        for (int i = 0; i < (int)edges.size(); ++i) {
            if (i == skip) continue;
            auto [u, v, w] = edges[i];
            int ru = find(u), rv = find(v);
            if (ru != rv) {
                if (rank[ru] < rank[rv]) std::swap(ru, rv);
                parent[rv] = ru;
                if (rank[ru] == rank[rv]) rank[ru]++;
                weight += w;
                edgesUsed++;
            }
        }
        if (edgesUsed == V - 1) {
            secondBest = std::min(secondBest, weight);
        }
    }
    return secondBest;
}
```

### Bottleneck Spanning Tree

A **bottleneck spanning tree** minimizes the maximum edge weight in the tree. Interestingly, every MST is also a bottleneck spanning tree (but not vice versa). This property is useful in network design where the bottleneck (weakest link) determines overall performance.

---

## Interview Tips

1. **Kruskal's is usually easier to implement** in an interview because it only requires sorting + DSU.
2. **Prim's is better for dense graphs** where \\(E\\) is close to \\(V^2\\).
3. **Always check if the graph is connected** before computing MST. If disconnected, you get a **Minimum Spanning Forest** (MSF).
4. **Edge cases:** Single vertex (\\(V = 1\\), MST weight = 0), no edges (disconnected), all same weights.
5. **For problems asking "minimum cost to connect all points,"** think MST immediately.

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Not checking connectivity | Wrong result for disconnected graphs | Count components or check \\(|MST| = V-1\\) |
| Forgetting to sort edges in Kruskal's | Wrong greedy order | Sort first! |
| Wrong DSU implementation | Infinite loop or wrong merges | Path compression + union by rank |
| Using directed edges | Asymmetric MST | Use undirected edges for both algorithms |
| Off-by-one in edge count | Stopping too early/late | Stop at exactly \\(V-1\\) edges |

## Practice Problems

### Minimum Cost to Connect All Points (LeetCode 1584)

**Problem:** Given `n` points on a 2D plane, find the minimum cost to connect all points where the cost between two points is the Manhattan distance.

```cpp
#include <vector>
#include <algorithm>
#include <cmath>

class Solution {
public:
    int minCostConnectPoints(std::vector<std::vector<int>>& points) {
        int n = points.size();
        std::vector<std::tuple<int, int, int>> edges;

        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int dist = std::abs(points[i][0] - points[j][0]) +
                           std::abs(points[i][1] - points[j][1]);
                edges.push_back({dist, i, j});
            }
        }

        std::sort(edges.begin(), edges.end());

        // DSU
        std::vector<int> parent(n), rank(n, 0);
        for (int i = 0; i < n; ++i) parent[i] = i;
        std::function<int(int)> find = [&](int x) {
            return parent[x] == x ? x : parent[x] = find(parent[x]);
        };

        int total = 0, count = 0;
        for (auto [w, u, v] : edges) {
            int ru = find(u), rv = find(v);
            if (ru != rv) {
                if (rank[ru] < rank[rv]) std::swap(ru, rv);
                parent[rv] = ru;
                if (rank[ru] == rank[rv]) rank[ru]++;
                total += w;
                if (++count == n - 1) break;
            }
        }
        return total;
    }
};
```

### Connecting Cities With Minimum Cost (LeetCode 1135)

**Problem:** Given `n` cities and connections with costs, find the minimum cost to connect all cities. Return -1 if not possible.

```cpp
#include <vector>
#include <algorithm>
#include <functional>

class Solution {
public:
    int minimumCost(int n, std::vector<std::vector<int>>& connections) {
        std::sort(connections.begin(), connections.end(),
                  [](auto& a, auto& b) { return a[2] < b[2]; });

        std::vector<int> parent(n + 1), rank(n + 1, 0);
        for (int i = 0; i <= n; ++i) parent[i] = i;
        std::function<int(int)> find = [&](int x) {
            return parent[x] == x ? x : parent[x] = find(parent[x]);
        };

        int total = 0, edges = 0;
        for (auto& c : connections) {
            int ru = find(c[0]), rv = find(c[1]);
            if (ru != rv) {
                if (rank[ru] < rank[rv]) std::swap(ru, rv);
                parent[rv] = ru;
                if (rank[ru] == rank[rv]) rank[ru]++;
                total += c[2];
                if (++edges == n - 1) return total;
            }
        }
        return -1;
    }
};
```

---

*Next chapter: Advanced Graph Algorithms — strongly connected components, bridges, Euler paths, and more.*
