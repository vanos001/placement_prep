# Chapter 58: Expanded Graphs

## Prerequisites

- BFS, DFS, Dijkstra's algorithm
- Basic graph representations (adjacency list, adjacency matrix)
- Disjoint Set Union (Union-Find)
- Dynamic programming fundamentals
- Basic complexity analysis

## Interview Frequency: ★★★★

Graph algorithms beyond the basics appear frequently in hard interview problems. **A\* Search** is popular at **Google** and game companies. **Bipartite matching** shows up at **Meta** and **Amazon**. **Topological sort variants** are common everywhere. **Graph coloring** and **Hamiltonian path** appear in harder rounds at **Google** and **Microsoft**. **DSU optimizations** are essential knowledge for any competitive programming-style interview.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| A* Search | ★★★ | Google, game companies | Medium |
| Bidirectional BFS | ★★★ | Google, Amazon | Medium |
| Dial's Algorithm | ★ | Competitive programming | Medium |
| DSU Optimizations | ★★★★ | All companies | Medium |
| Bipartite Matching | ★★★ | Meta, Amazon, Google | Hard |
| Min-Cut | ★★ | Google, network companies | Hard |
| Hamiltonian Path | ★★ | Google, Microsoft | Hard |
| Graph Coloring | ★★ | Google, scheduling companies | Medium-Hard |
| Topological Sort Variants | ★★★★ | All companies | Medium |

---

## 58.1 A* Search

**A\*** is a heuristic-based pathfinding algorithm that finds the shortest path from start to goal. It extends Dijkstra's by using a **heuristic function** `h(n)` to guide the search toward the goal.

### Key Formula

```
f(n) = g(n) + h(n)
```

- `g(n)` = actual cost from start to node n
- `h(n)` = estimated cost from node n to goal (heuristic)
- `f(n)` = estimated total cost through node n

### Admissible Heuristic

A heuristic is **admissible** if it never overestimates the actual cost. This guarantees A* finds the optimal path.

| Grid Type | Common Heuristic | Formula |
|---|---|---|
| 4-directional grid | Manhattan distance | \|x₁-x₂\| + \|y₁-y₂\| |
| 8-directional grid | Chebyshev distance | max(\|x₁-x₂\|, \|y₁-y₂\|) |
| Any-angle movement | Euclidean distance | √((x₁-x₂)² + (y₁-y₂)²) |

### When to Use

- Shortest path with a good heuristic available
- Game pathfinding, robotics navigation
- When Dijkstra explores too many nodes

### When NOT to Use

- No good heuristic exists (falls back to Dijkstra)
- Negative edge weights (A* assumes non-negative)
- When simplicity matters (Dijkstra is simpler)

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <cmath>
#include <functional>
#include <algorithm>

struct AStarNode {
    int id;
    int f; // f = g + h
    bool operator>(const AStarNode& other) const {
        return f > other.f;
    }
};

class AStar {
    int n;
    struct Edge { int to, weight; };
    std::vector<std::vector<Edge>> adj;
    
public:
    AStar(int n) : n(n), adj(n) {}
    
    void addEdge(int u, int v, int w) {
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }
    
    // h: heuristic function, h(node) estimates cost to goal
    std::vector<int> findPath(int start, int goal, 
                               std::function<int(int)> h) {
        std::vector<int> g(n, INT_MAX);
        std::vector<int> parent(n, -1);
        std::vector<bool> closed(n, false);
        
        std::priority_queue<AStarNode, std::vector<AStarNode>, 
                           std::greater<AStarNode>> open;
        
        g[start] = 0;
        open.push({start, h(start)});
        
        while (!open.empty()) {
            auto [u, f] = open.top();
            open.pop();
            
            if (u == goal) break;
            if (closed[u]) continue;
            closed[u] = true;
            
            for (auto& [v, w] : adj[u]) {
                int newG = g[u] + w;
                if (newG < g[v]) {
                    g[v] = newG;
                    parent[v] = u;
                    open.push({v, newG + h(v)});
                }
            }
        }
        
        // Reconstruct path
        std::vector<int> path;
        if (g[goal] == INT_MAX) return path; // No path
        
        for (int cur = goal; cur != -1; cur = parent[cur]) {
            path.push_back(cur);
        }
        std::reverse(path.begin(), path.end());
        return path;
    }
    
    int getCost(int start, int goal, std::function<int(int)> h) {
        std::vector<int> g(n, INT_MAX);
        std::vector<bool> closed(n, false);
        std::priority_queue<AStarNode, std::vector<AStarNode>, 
                           std::greater<AStarNode>> open;
        
        g[start] = 0;
        open.push({start, h(start)});
        
        while (!open.empty()) {
            auto [u, f] = open.top();
            open.pop();
            if (u == goal) return g[goal];
            if (closed[u]) continue;
            closed[u] = true;
            
            for (auto& [v, w] : adj[u]) {
                int newG = g[u] + w;
                if (newG < g[v]) {
                    g[v] = newG;
                    open.push({v, newG + h(v)});
                }
            }
        }
        return INT_MAX;
    }
};

int main() {
    // Grid-like graph: nodes 0-8 arranged as 3x3 grid
    // 0 1 2
    // 3 4 5
    // 6 7 8
    AStar astar(9);
    
    auto idx = [](int r, int c) { return r * 3 + c; };
    
    // Add edges with weights
    for (int r = 0; r < 3; r++) {
        for (int c = 0; c < 3; c++) {
            if (c + 1 < 3) astar.addEdge(idx(r, c), idx(r, c + 1), 1);
            if (r + 1 < 3) astar.addEdge(idx(r, c), idx(r + 1, c), 1);
        }
    }
    
    // Heuristic: Manhattan distance to goal (2, 2) = node 8
    auto h = [&](int node) {
        int r = node / 3, c = node % 3;
        return std::abs(r - 2) + std::abs(c - 2);
    };
    
    auto path = astar.findPath(0, 8, h);
    std::cout << "Path from 0 to 8: ";
    for (int node : path) std::cout << node << " ";
    std::cout << "\nCost: " << astar.getCost(0, 8, h) << "\n";
    
    return 0;
}
```

### A* vs Dijkstra

| Aspect | Dijkstra | A* |
|---|---|---|
| Heuristic | None (h=0) | Uses h(n) |
| Exploration | Explores uniformly | Explores toward goal |
| Optimality | Always optimal | Optimal if h is admissible |
| Speed | Slower (more nodes) | Faster with good heuristic |
| Use case | General shortest path | Known goal position |

---

## 58.2 Bidirectional BFS

**Bidirectional BFS** runs BFS simultaneously from both source and destination, stopping when the two searches meet. This can reduce the search space from O(b^d) to O(b^(d/2)), where b is the branching factor and d is the distance.

### When to Use

- Shortest path in unweighted graphs where both endpoints are known
- The graph has high branching factor
- Regular BFS explores too many nodes

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <unordered_set>
#include <algorithm>

class BidirectionalBFS {
    int n;
    std::vector<std::vector<int>> adj;
    
public:
    BidirectionalBFS(int n) : n(n), adj(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    int shortestPath(int src, int dst) {
        if (src == dst) return 0;
        
        std::vector<int> distF(n, -1), distB(n, -1);
        std::queue<int> qF, qB;
        
        distF[src] = 0;
        distB[dst] = 0;
        qF.push(src);
        qB.push(dst);
        
        int best = INT_MAX;
        
        while (!qF.empty() && !qB.empty()) {
            // Expand from forward frontier
            int result = expandLevel(qF, distF, distB, best);
            if (result != -1) return result;
            
            // Expand from backward frontier
            result = expandLevel(qB, distB, distF, best);
            if (result != -1) return result;
        }
        
        return best == INT_MAX ? -1 : best;
    }
    
private:
    int expandLevel(std::queue<int>& q, std::vector<int>& dist, 
                    std::vector<int>& otherDist, int& best) {
        int sz = q.size();
        for (int i = 0; i < sz; i++) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
                // Check if other BFS has visited this node
                if (otherDist[v] != -1) {
                    best = std::min(best, dist[u] + 1 + otherDist[v]);
                    return best;
                }
            }
        }
        return -1;
    }
};

int main() {
    BidirectionalBFS bfs(10);
    
    // Path: 0-1-2-3-4-5-6-7-8-9
    for (int i = 0; i < 9; i++) {
        bfs.addEdge(i, i + 1);
    }
    // Shortcuts
    bfs.addEdge(0, 5);
    bfs.addEdge(3, 8);
    
    std::cout << "Shortest path 0 to 9: " 
              << bfs.shortestPath(0, 9) << "\n";
    
    return 0;
}
```

### Complexity Comparison

| Method | Time | Space | Notes |
|---|---|---|---|
| BFS | O(V + E) | O(V) | Single direction |
| Bidirectional BFS | O(V + E) | O(V) | Meets in middle |
| Speedup factor | ~2x for distance d | — | Reduces explored nodes |

For a graph with branching factor b and shortest path length d:
- BFS explores: O(b^d)
- Bidirectional BFS explores: O(2 × b^(d/2)) = O(b^(d/2))

---

## 58.3 Dial's Algorithm

**Dial's Algorithm** is a variant of Dijkstra for graphs where edge weights are small integers (0 to W). It uses W+1 buckets instead of a priority queue, achieving O(V + E + W·V) time.

### When to Use

- Edge weights are small non-negative integers
- Dijkstra's O((V+E) log V) overhead is too much
- Very sparse graphs with small weights

```cpp
#include <iostream>
#include <vector>
#include <list>
#include <algorithm>

class DialsAlgorithm {
    int n, maxWeight;
    struct Edge { int to, weight; };
    std::vector<std::vector<Edge>> adj;
    
public:
    DialsAlgorithm(int n, int maxWeight) 
        : n(n), maxWeight(maxWeight), adj(n) {}
    
    void addEdge(int u, int v, int w) {
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }
    
    std::vector<int> shortestPaths(int src) {
        std::vector<int> dist(n, INT_MAX);
        // Buckets: bucket[i] contains nodes with distance i
        std::vector<std::list<int>> buckets(maxWeight * n + 1);
        std::vector<int> bucketPos(n, -1); // Position in bucket for quick removal
        
        dist[src] = 0;
        buckets[0].push_back(src);
        
        int currBucket = 0;
        
        while (true) {
            // Find next non-empty bucket
            while (currBucket < (int)buckets.size() && buckets[currBucket].empty()) {
                currBucket++;
            }
            if (currBucket >= (int)buckets.size()) break;
            
            // Get node from bucket
            int u = buckets[currBucket].front();
            buckets[currBucket].pop_front();
            
            // Skip if outdated
            if (dist[u] < currBucket) continue;
            
            for (auto& [v, w] : adj[u]) {
                int newDist = dist[u] + w;
                if (newDist < dist[v]) {
                    dist[v] = newDist;
                    buckets[newDist].push_back(v);
                }
            }
        }
        
        return dist;
    }
};

int main() {
    DialsAlgorithm da(5, 3);
    da.addEdge(0, 1, 1);
    da.addEdge(0, 2, 2);
    da.addEdge(1, 3, 1);
    da.addEdge(2, 3, 1);
    da.addEdge(3, 4, 2);
    
    auto dist = da.shortestPaths(0);
    std::cout << "Distances from 0:\n";
    for (int i = 0; i < 5; i++) {
        std::cout << "  To " << i << ": " << dist[i] << "\n";
    }
    
    return 0;
}
```

---

## 58.4 DSU Optimizations

The basic Disjoint Set Union can be optimized beyond the standard union-by-rank + path compression.

### Optimization Techniques

| Technique | Description | Time per operation |
|---|---|---|
| Union by rank | Attach smaller tree under larger | O(α(n)) amortized |
| Union by size | Same idea, track subtree size | O(α(n)) amortized |
| Path compression | Flatten tree on find | O(α(n)) amortized |
| Path splitting | Parent = grandparent on find | O(α(n)) amortized |
| Path halving | Every other node on path gets new parent | O(α(n)) amortized |

### Complete Implementation with All Optimizations

```cpp
#include <iostream>
#include <vector>
#include <numeric>

class DSU {
    std::vector<int> parent, rank_, size;
    int components;
    
public:
    DSU(int n) : parent(n), rank_(n, 0), size(n, 1), components(n) {
        std::iota(parent.begin(), parent.end(), 0);
    }
    
    // Standard find with full path compression
    int find(int x) {
        if (parent[x] != x) {
            parent[x] = find(parent[x]);
        }
        return parent[x];
    }
    
    // Path splitting: each node on path points to its grandparent
    int findSplit(int x) {
        while (parent[x] != x) {
            int next = parent[x];
            parent[x] = parent[parent[x]];
            x = next;
        }
        return x;
    }
    
    // Path halving: every other node gets new parent
    int findHalf(int x) {
        while (parent[x] != x) {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        return x;
    }
    
    // Union by rank
    bool uniteRank(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        
        if (rank_[x] < rank_[y]) std::swap(x, y);
        parent[y] = x;
        if (rank_[x] == rank_[y]) rank_[x]++;
        components--;
        return true;
    }
    
    // Union by size
    bool uniteSize(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        
        if (size[x] < size[y]) std::swap(x, y);
        parent[y] = x;
        size[x] += size[y];
        components--;
        return true;
    }
    
    bool connected(int x, int y) { return find(x) == find(y); }
    int getSize(int x) { return size[find(x)]; }
    int getComponents() { return components; }
};

int main() {
    DSU dsu(10);
    
    dsu.uniteSize(0, 1);
    dsu.uniteSize(2, 3);
    dsu.uniteSize(0, 2);
    
    std::cout << "0 and 3 connected: " << dsu.connected(0, 3) << "\n";
    std::cout << "Component size of 0: " << dsu.getSize(0) << "\n";
    std::cout << "Total components: " << dsu.getComponents() << "\n";
    
    return 0;
}
```

### Path Splitting vs Path Halving vs Full Compression

| Method | Code Complexity | Practical Speed | Notes |
|---|---|---|---|
| Full compression | Recursive | Good | Stack overhead for deep trees |
| Path splitting | Iterative | Best | No recursion, simple loop |
| Path halving | Iterative | Good | Shorter loop than splitting |

In practice, path splitting and path halving are often preferred because they avoid recursion overhead while achieving the same amortized complexity.

---

## 58.5 Maximum Bipartite Matching

Given a bipartite graph (U, V, E), find the maximum set of edges such that no two share a vertex.

### Hungarian Algorithm (Overview)

The Hungarian algorithm solves the assignment problem in O(n³). For bipartite matching, it finds augmenting paths using BFS/DFS.

### Hopcroft-Karp Algorithm

Hopcroft-Karp finds maximum matching in O(E√V) by finding multiple augmenting paths simultaneously using BFS layers.

### When to Use

- Assignment problems (jobs to workers)
- Matching problems in bipartite graphs
- Network flow reductions

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

class HopcroftKarp {
    int n, m; // n = |U|, m = |V|
    std::vector<std::vector<int>> adj; // adj[u] = neighbors in V
    std::vector<int> pairU, pairV, dist;
    
    bool bfs() {
        std::queue<int> q;
        for (int u = 0; u < n; u++) {
            if (pairU[u] == -1) {
                dist[u] = 0;
                q.push(u);
            } else {
                dist[u] = INT_MAX;
            }
        }
        
        bool found = false;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (pairV[v] == -1) {
                    found = true; // Found free vertex in V
                } else if (dist[pairV[v]] == INT_MAX) {
                    dist[pairV[v]] = dist[u] + 1;
                    q.push(pairV[v]);
                }
            }
        }
        return found;
    }
    
    bool dfs(int u) {
        for (int v : adj[u]) {
            if (pairV[v] == -1 || 
                (dist[pairV[v]] == dist[u] + 1 && dfs(pairV[v]))) {
                pairU[u] = v;
                pairV[v] = u;
                return true;
            }
        }
        dist[u] = INT_MAX;
        return false;
    }
    
public:
    HopcroftKarp(int n, int m) : n(n), m(m), adj(n), 
                                  pairU(n, -1), pairV(m, -1), dist(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
    }
    
    int maxMatching() {
        int matching = 0;
        while (bfs()) {
            for (int u = 0; u < n; u++) {
                if (pairU[u] == -1 && dfs(u)) {
                    matching++;
                }
            }
        }
        return matching;
    }
    
    std::vector<std::pair<int, int>> getMatching() {
        std::vector<std::pair<int, int>> result;
        for (int u = 0; u < n; u++) {
            if (pairU[u] != -1) {
                result.push_back({u, pairU[u]});
            }
        }
        return result;
    }
};

int main() {
    // Bipartite graph:
    // U = {0, 1, 2, 3}, V = {0, 1, 2, 3}
    // Edges: (0,0), (0,1), (1,0), (1,2), (2,1), (3,2), (3,3)
    
    HopcroftKarp hk(4, 4);
    hk.addEdge(0, 0);
    hk.addEdge(0, 1);
    hk.addEdge(1, 0);
    hk.addEdge(1, 2);
    hk.addEdge(2, 1);
    hk.addEdge(3, 2);
    hk.addEdge(3, 3);
    
    std::cout << "Maximum matching: " << hk.maxMatching() << "\n";
    
    auto matching = hk.getMatching();
    std::cout << "Matching pairs:\n";
    for (auto& [u, v] : matching) {
        std::cout << "  U" << u << " -> V" << v << "\n";
    }
    
    return 0;
}
```

### Complexity Comparison

| Algorithm | Time | Best For |
|---|---|---|
| DFS augmenting paths | O(VE) | Simple implementation |
| Hopcroft-Karp | O(E√V) | Large sparse bipartite graphs |
| Hungarian (assignment) | O(n³) | Weighted assignment |
| Max flow reduction | O(VE²) or better | General framework |

---

## 58.6 Minimum Cut (Max-Flow Min-Cut)

The **Max-Flow Min-Cut Theorem** states that the maximum flow from source to sink equals the minimum capacity of a cut separating source and sink.

### Applications

| Application | How it maps to min-cut |
|---|---|
| Network reliability | Min edges to disconnect |
| Image segmentation | Foreground/background separation |
| Project selection | Maximize profit with dependencies |
| Baseball elimination | Can team still win? |

### Finding Min-Cut from Max-Flow

After computing max-flow, find all nodes reachable from source in the residual graph. The min-cut edges go from reachable to non-reachable nodes.

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <climits>

class MaxFlowMinCut {
    int n;
    struct Edge { int to, cap, flow; };
    std::vector<std::vector<int>> adj;
    std::vector<Edge> edges;
    std::vector<int> level, ptr;
    
    void addEdgeInternal(int u, int v, int cap) {
        adj[u].push_back(edges.size());
        edges.push_back({v, cap, 0});
        adj[v].push_back(edges.size());
        edges.push_back({u, 0, 0}); // Reverse edge
    }
    
    bool bfs(int s, int t) {
        std::fill(level.begin(), level.end(), -1);
        level[s] = 0;
        std::queue<int> q;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int idx : adj[u]) {
                auto& e = edges[idx];
                if (e.cap - e.flow > 0 && level[e.to] == -1) {
                    level[e.to] = level[u] + 1;
                    q.push(e.to);
                }
            }
        }
        return level[t] != -1;
    }
    
    int dfs(int u, int t, int pushed) {
        if (u == t || pushed == 0) return pushed;
        for (int& cid = ptr[u]; cid < (int)adj[u].size(); cid++) {
            int idx = adj[u][cid];
            auto& e = edges[idx];
            if (level[e.to] != level[u] + 1) continue;
            int tr = dfs(e.to, t, std::min(pushed, e.cap - e.flow));
            if (tr == 0) continue;
            e.flow += tr;
            edges[idx ^ 1].flow -= tr;
            return tr;
        }
        return 0;
    }
    
public:
    MaxFlowMinCut(int n) : n(n), adj(n), level(n), ptr(n) {}
    
    void addEdge(int u, int v, int cap) {
        addEdgeInternal(u, v, cap);
    }
    
    int maxFlow(int s, int t) {
        int flow = 0;
        while (bfs(s, t)) {
            std::fill(ptr.begin(), ptr.end(), 0);
            while (int pushed = dfs(s, t, INT_MAX)) {
                flow += pushed;
            }
        }
        return flow;
    }
    
    // Find min-cut edges after max-flow
    std::vector<std::pair<int, int>> findMinCut(int s) {
        // BFS in residual graph from s
        std::vector<bool> reachable(n, false);
        std::queue<int> q;
        q.push(s);
        reachable[s] = true;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int idx : adj[u]) {
                auto& e = edges[idx];
                if (e.cap - e.flow > 0 && !reachable[e.to]) {
                    reachable[e.to] = true;
                    q.push(e.to);
                }
            }
        }
        
        std::vector<std::pair<int, int>> cutEdges;
        for (int u = 0; u < n; u++) {
            if (!reachable[u]) continue;
            for (int idx : adj[u]) {
                auto& e = edges[idx];
                if (!reachable[e.to] && e.cap > 0) {
                    cutEdges.push_back({u, e.to});
                }
            }
        }
        return cutEdges;
    }
};

int main() {
    MaxFlowMinCut mfm(6);
    // s=0, t=5
    mfm.addEdge(0, 1, 16);
    mfm.addEdge(0, 2, 13);
    mfm.addEdge(1, 2, 10);
    mfm.addEdge(1, 3, 12);
    mfm.addEdge(2, 1, 4);
    mfm.addEdge(2, 4, 14);
    mfm.addEdge(3, 2, 9);
    mfm.addEdge(3, 5, 20);
    mfm.addEdge(4, 3, 7);
    mfm.addEdge(4, 5, 4);
    
    int flow = mfm.maxFlow(0, 5);
    std::cout << "Maximum flow: " << flow << "\n";
    
    auto cut = mfm.findMinCut(0);
    std::cout << "Min-cut edges:\n";
    for (auto& [u, v] : cut) {
        std::cout << "  " << u << " -> " << v << "\n";
    }
    
    return 0;
}
```

---

## 58.7 Hamiltonian Path

A **Hamiltonian Path** visits every vertex exactly once. Finding one is NP-complete in general, but solvable for small n using bitmask DP.

### Bitmask DP for Small n

**State**: `dp[mask][v]` = true if there's a path that visits exactly the vertices in `mask` and ends at vertex `v`.

**Time**: O(2^n × n²)  
**Space**: O(2^n × n)

### When to Use

- n ≤ 20 (bitmask feasible)
- Need to check existence or count Hamiltonian paths
- TSP-like problems (visit all cities)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class HamiltonianPath {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<std::vector<bool>> dp;
    std::vector<std::vector<int>> parent;
    
public:
    HamiltonianPath(int n) : n(n), adj(n), dp(1 << n, std::vector<int>(n, -1)),
                             parent(1 << n, std::vector<int>(n, -1)) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Returns a Hamiltonian path or empty vector
    std::vector<int> findPath() {
        int fullMask = (1 << n) - 1;
        
        // Base: single vertex paths
        for (int v = 0; v < n; v++) {
            dp[1 << v][v] = 1;
        }
        
        // Fill DP
        for (int mask = 1; mask <= fullMask; mask++) {
            for (int v = 0; v < n; v++) {
                if (!(mask & (1 << v))) continue;
                if (dp[mask][v] == -1) continue;
                
                for (int u : adj[v]) {
                    if (mask & (1 << u)) continue;
                    int newMask = mask | (1 << u);
                    dp[newMask][u] = 1;
                    parent[newMask][u] = v;
                }
            }
        }
        
        // Find ending vertex of Hamiltonian path
        int endV = -1;
        for (int v = 0; v < n; v++) {
            if (dp[fullMask][v] == 1) {
                endV = v;
                break;
            }
        }
        
        if (endV == -1) return {}; // No Hamiltonian path
        
        // Reconstruct path
        std::vector<int> path;
        int mask = fullMask;
        int v = endV;
        while (v != -1) {
            path.push_back(v);
            int prev = parent[mask][v];
            mask ^= (1 << v);
            v = prev;
        }
        std::reverse(path.begin(), path.end());
        return path;
    }
};

int main() {
    // Complete graph K4 has Hamiltonian paths
    HamiltonianPath hp(4);
    for (int i = 0; i < 4; i++) {
        for (int j = i + 1; j < 4; j++) {
            hp.addEdge(i, j);
        }
    }
    
    auto path = hp.findPath();
    if (!path.empty()) {
        std::cout << "Hamiltonian path: ";
        for (int v : path) std::cout << v << " ";
        std::cout << "\n";
    } else {
        std::cout << "No Hamiltonian path found.\n";
    }
    
    // Path graph: 0-1-2-3
    HamiltonianPath hp2(4);
    hp2.addEdge(0, 1);
    hp2.addEdge(1, 2);
    hp2.addEdge(2, 3);
    
    auto path2 = hp2.findPath();
    std::cout << "Path graph: ";
    for (int v : path2) std::cout << v << " ";
    std::cout << "\n";
    
    return 0;
}
```

---

## 58.8 Graph Coloring

**Graph Coloring** assigns colors to vertices such that no two adjacent vertices share the same color. The minimum number of colors needed is the **chromatic number** χ(G).

### Greedy Coloring

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

class GraphColoring {
    int n;
    std::vector<std::vector<int>> adj;
    
public:
    GraphColoring(int n) : n(n), adj(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Greedy coloring - returns color for each vertex
    // Colors are 0-indexed
    std::vector<int> greedyColor() {
        std::vector<int> color(n, -1);
        color[0] = 0;
        
        for (int u = 1; u < n; u++) {
            // Find colors used by neighbors
            std::set<int> usedColors;
            for (int v : adj[u]) {
                if (color[v] != -1) {
                    usedColors.insert(color[v]);
                }
            }
            
            // Assign smallest available color
            int c = 0;
            while (usedColors.count(c)) c++;
            color[u] = c;
        }
        
        return color;
    }
    
    // Backtracking for exact chromatic number (small graphs)
    bool isSafe(int v, int c, const std::vector<int>& color) {
        for (int u : adj[v]) {
            if (color[u] == c) return false;
        }
        return true;
    }
    
    bool colorBacktrack(int v, int maxColors, std::vector<int>& color) {
        if (v == n) return true;
        
        for (int c = 0; c < maxColors; c++) {
            if (isSafe(v, c, color)) {
                color[v] = c;
                if (colorBacktrack(v + 1, maxColors, color)) return true;
                color[v] = -1;
            }
        }
        return false;
    }
    
    int chromaticNumber() {
        // Binary search on number of colors
        int lo = 1, hi = n;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            std::vector<int> color(n, -1);
            if (colorBacktrack(0, mid, color)) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        return lo;
    }
};

int main() {
    // Cycle of 5 nodes (needs 3 colors)
    GraphColoring gc(5);
    gc.addEdge(0, 1); gc.addEdge(1, 2); gc.addEdge(2, 3);
    gc.addEdge(3, 4); gc.addEdge(4, 0);
    
    auto colors = gc.greedyColor();
    int maxColor = *std::max_element(colors.begin(), colors.end());
    
    std::cout << "Greedy coloring (5-cycle):\n";
    for (int i = 0; i < 5; i++) {
        std::cout << "  Vertex " << i << " -> Color " << colors[i] << "\n";
    }
    std::cout << "Colors used: " << maxColor + 1 << "\n";
    
    return 0;
}
```

### Graph Coloring Properties

| Graph Type | Chromatic Number | Notes |
|---|---|---|
| Bipartite | 2 | All edges go between two sets |
| Tree | 2 | Always bipartite |
| Cycle (even length) | 2 | Bipartite |
| Cycle (odd length) | 3 | Not bipartite |
| Complete graph K_n | n | Every pair adjacent |
| Planar graph | ≤ 4 | Four Color Theorem |

---

## 58.9 Topological Sort Variants

### All Topological Orders

Enumerate all valid orderings of a DAG. Used in scheduling problems where multiple valid orderings exist.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class AllTopSorts {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> inDegree;
    std::vector<bool> visited;
    std::vector<int> current;
    std::vector<std::vector<int>> allOrders;
    
    void backtrack() {
        if ((int)current.size() == n) {
            allOrders.push_back(current);
            return;
        }
        
        for (int u = 0; u < n; u++) {
            if (!visited[u] && inDegree[u] == 0) {
                visited[u] = true;
                current.push_back(u);
                
                for (int v : adj[u]) inDegree[v]--;
                
                backtrack();
                
                for (int v : adj[u]) inDegree[v]++;
                current.pop_back();
                visited[u] = false;
            }
        }
    }
    
public:
    AllTopSorts(int n) : n(n), adj(n), inDegree(n, 0), visited(n, false) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        inDegree[v]++;
    }
    
    std::vector<std::vector<int>> findAll() {
        allOrders.clear();
        backtrack();
        return allOrders;
    }
};

// Lexicographically smallest topological sort
std::vector<int> lexSmallestTopSort(int n, 
                                      const std::vector<std::vector<int>>& adj) {
    std::vector<int> inDegree(n, 0);
    for (int u = 0; u < n; u++) {
        for (int v : adj[u]) inDegree[v]++;
    }
    
    // Use min-heap instead of regular queue
    std::priority_queue<int, std::vector<int>, std::greater<int>> pq;
    for (int i = 0; i < n; i++) {
        if (inDegree[i] == 0) pq.push(i);
    }
    
    std::vector<int> result;
    while (!pq.empty()) {
        int u = pq.top(); pq.pop();
        result.push_back(u);
        for (int v : adj[u]) {
            if (--inDegree[v] == 0) {
                pq.push(v);
            }
        }
    }
    
    return result;
}

int main() {
    // DAG: 0->1, 0->2, 1->3, 2->3
    AllTopSorts ats(4);
    ats.addEdge(0, 1);
    ats.addEdge(0, 2);
    ats.addEdge(1, 3);
    ats.addEdge(2, 3);
    
    auto all = ats.findAll();
    std::cout << "All topological orders:\n";
    for (auto& order : all) {
        std::cout << "  ";
        for (int v : order) std::cout << v << " ";
        std::cout << "\n";
    }
    
    // Lexicographically smallest
    std::vector<std::vector<int>> adj(4);
    adj[0] = {1, 2}; adj[1] = {3}; adj[2] = {3};
    
    auto lex = lexSmallestTopSort(4, adj);
    std::cout << "Lex smallest: ";
    for (int v : lex) std::cout << v << " ";
    std::cout << "\n";
    
    return 0;
}
```

### Topological Sort Applications

| Problem | Technique |
|---|---|
| Task scheduling | Standard topological sort |
| Parallel scheduling | Level-based BFS |
| Lex smallest ordering | Min-heap topological sort |
| Detect cycle | If result has < n nodes, cycle exists |
| Longest path in DAG | Topo sort + DP |
| Course prerequisites | Topo sort (if possible, no cycle) |

---

## Summary

| Algorithm | Key Insight | Time | Best For |
|---|---|---|---|
| A* Search | Heuristic-guided Dijkstra | O(E log V) with good h | Pathfinding with known goal |
| Bidirectional BFS | Meet in the middle | O(V + E) | Unweighted shortest path |
| Dial's Algorithm | Bucket-based Dijkstra | O(V + E + WV) | Small integer weights |
| DSU Optimizations | Path splitting/halving | O(α(n)) | Dynamic connectivity |
| Hopcroft-Karp | Layered augmenting paths | O(E√V) | Bipartite matching |
| Min-Cut | Max-flow = min-cut | O(VE²) Dinic | Network separation |
| Hamiltonian Path | Bitmask DP | O(2^n × n²) | Small n, visit all |
| Graph Coloring | Greedy / backtracking | O(n + E) greedy | Scheduling, coloring |
| Topo Sort Variants | Priority queue / enumerate | O(V + E) | DAG ordering |
