# Chapter 109: Bridge Trees and Treewidth

## Prerequisites
- [Chapter 102: Graph Fundamentals](ch22-graph-fundamentals.md)
- Chapter 103: DFS and BFS
- Chapter 104: Strongly Connected Components
- Chapter 26: Shortest Paths
- Chapter 13: Trees
- Tarjan's algorithm, bridge detection, tree decomposition basics

## Interview Frequency: ★★

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Bridge tree | ★★ | Medium | Compress 2-edge-connected components |
| Treewidth | ★ | Hard | Graph width parameter |
| Chordal graphs | ★ | Hard | Perfect elimination ordering |
| Dynamic connectivity | ★★ | Hard | Link-cut trees, ETT |

---

## Motivation

Why do bridge trees and treewidth matter in competitive programming and interviews?

**Bridge trees** appear whenever you need to reason about "critical connections" in a graph. Classic scenarios:

- **Network reliability**: Which links, if severed, disconnect the network? Bridges answer this directly.
- **Query problems**: "Are nodes u and v in the same 2-edge-connected component?" becomes O(1) after building the bridge tree.
- **Path queries on trees**: After compressing components, many graph problems reduce to tree problems — and trees are far easier to handle (LCA, DP, etc.).
- **Interview staple**: "Find all critical connections" (LeetCode 1192) is a direct bridge-finding problem. Many follow-ups ask about 2-edge-connected components.

**Treewidth** matters because it is the single most important graph parameter for turning NP-hard problems into polynomial ones:

- **Bounded treewidth**: If a graph has treewidth k, then problems like Vertex Cover, Dominating Set, Hamiltonian Path, and Graph Coloring can be solved in O(2^k · n) or similar using tree DP.
- **Real-world graphs**: Many practical networks (road maps, VLSI circuits, social network communities) have small treewidth.
- **Interview context**: You won't be asked to compute treewidth directly (it's NP-hard), but understanding the concept helps you recognize when a problem has a tree-like structure that enables efficient DP.

---

## Formal Definitions

**Bridge (cut edge)**: An edge (u, v) in an undirected graph G is a bridge if removing it increases the number of connected components. Equivalently, (u, v) is a bridge if and only if it does not belong to any cycle.

**2-edge-connected component**: A maximal subgraph S of G such that for any two vertices u, v in S, there exist at least two edge-disjoint paths between u and v. Equivalently, S is a maximal subgraph with no bridges. Every vertex belongs to exactly one 2-edge-connected component.

**Bridge tree**: Given a connected undirected graph G, the bridge tree T is constructed by contracting each 2-edge-connected component of G into a single node. Two nodes in T are adjacent if and only if there is a bridge in G connecting the corresponding components. T is always a tree (or forest if G is disconnected).

**Tree decomposition**: A tree decomposition of a graph G = (V, E) is a pair (T, X) where T is a tree and X = {X_t : t ∈ V(T)} is a family of subsets of V (called bags) such that:
1. Every vertex v ∈ V appears in at least one bag.
2. For every edge (u, v) ∈ E, there exists a bag containing both u and v.
3. For every vertex v ∈ V, the set of bags containing v forms a connected subtree of T.

**Treewidth**: The width of a tree decomposition is the size of the largest bag minus 1. The treewidth of a graph G is the minimum width over all possible tree decompositions of G.

**Chordal graph**: A graph is chordal if every cycle of length ≥ 4 has a chord (an edge connecting two non-adjacent vertices of the cycle). Equivalently, a graph is chordal if and only if it has a perfect elimination ordering.

---

## Intuition

### Bridges as "Weak Links"

Think of a graph as a network of roads. A bridge is a road that, if closed, would leave some towns completely unreachable from others. It's the single point of failure — the "weak link."

Visual intuition: if you draw a graph and imagine cutting edges one by one, bridges are the cuts that actually split the graph into separate pieces. Non-bridge edges are part of cycles — there's always an alternative route.

**Mental model**: A 2-edge-connected component is a "cluster" where you can always find a backup route. The bridge tree tells you how these clusters are stitched together via single fragile edges.

### Treewidth as "Tree-likeness"

Treewidth measures how "close" a graph is to being a tree:

- **Treewidth 1** = tree (or forest). Every problem solvable by tree DP.
- **Treewidth 2** = series-parallel graphs, outerplanar graphs. Still very tractable.
- **Treewidth k** = can be decomposed into bags of size k+1 arranged in a tree. You solve the problem inside each bag (small!), then combine results along the tree.
- **Treewidth n-1** = complete graph. No helpful structure; you're back to brute force.

**Mental model**: Imagine "unrolling" a graph into a tree where each node of the tree holds a small "bag" of original vertices. The bags overlap in controlled ways. This is exactly what makes tree DP possible — you solve the problem bag by bag, passing partial results along tree edges.

**Key insight**: Many NP-hard problems on general graphs become O(f(k) · n) on graphs with treewidth k, where f is typically exponential in k. This is the foundation of "fixed-parameter tractability" (FPT).

---

## 109.1 Bridge Tree

Compress each 2-edge-connected component into a single node. The resulting structure is a tree (since bridges connect components).

### Algorithm

1. **Find all bridges** using Tarjan's algorithm (DFS with tin/low values).
2. **Remove bridges** from the graph temporarily.
3. **Find connected components** of the remaining graph — these are the 2-edge-connected components.
4. **Build the bridge tree** by adding edges between components that were connected by bridges.

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <set>

class BridgeTree {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> tin, low, comp;
    std::vector<std::pair<int,int>> bridges;
    std::vector<bool> visited;
    
    void findBridges(int u, int p) {
        visited[u] = true;
        tin[u] = low[u] = timer++;
        for (int v : adj[u]) {
            if (v == p) continue;
            if (visited[v]) {
                low[u] = std::min(low[u], tin[v]);
            } else {
                findBridges(v, u);
                low[u] = std::min(low[u], low[v]);
                if (low[v] > tin[u]) bridges.push_back({u, v});
            }
        }
    }
    
    void assignComponent(int u, int c) {
        comp[u] = c;
        for (int v : adj[u])
            if (comp[v] == -1) assignComponent(v, c);
    }
    
public:
    BridgeTree(int n) : n(n), timer(0), adj(n), tin(n), low(n), comp(n, -1), visited(n, false) {}
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }
    
    int build() {
        for (int i = 0; i < n; i++)
            if (!visited[i]) findBridges(i, -1);
        
        // Remove bridges from adjacency
        std::set<std::pair<int,int>> bridgeSet(bridges.begin(), bridges.end());
        std::vector<std::vector<int>> adjNoBridges(n);
        for (int u = 0; u < n; u++)
            for (int v : adj[u])
                if (!bridgeSet.count({u, v}) && !bridgeSet.count({v, u}))
                    adjNoBridges[u].push_back(v);
        
        // Assign components
        int numComponents = 0;
        for (int i = 0; i < n; i++)
            if (comp[i] == -1) assignComponent(i, numComponents++);
        
        return numComponents;
    }
    
    std::vector<int> getComponents() { return comp; }
    std::vector<std::pair<int,int>> getBridges() { return bridges; }
};

int main() {
    BridgeTree bt(7);
    bt.addEdge(0, 1); bt.addEdge(1, 2); bt.addEdge(2, 0);
    bt.addEdge(1, 3); bt.addEdge(3, 4); bt.addEdge(4, 5); bt.addEdge(5, 3);
    bt.addEdge(3, 6);
    
    int components = bt.build();
    std::cout << "Components: " << components << "\n";
    std::cout << "Bridges:\n";
    for (auto& [u, v] : bt.getBridges())
        std::cout << "  " << u << " - " << v << "\n";
    
    return 0;
}
```

---

## Step-by-Step Walkthrough: Building a Bridge Tree

Let's walk through building a bridge tree on a concrete example.

**Input graph** (7 vertices, 8 edges):

```
    0 --- 1 --- 3 --- 4
     \   /      |   / |
      \ /       |  /  |
       2        5 --- 6
```

Edges: (0,1), (0,2), (1,2), (1,3), (3,5), (3,4), (4,5), (5,6)

**Step 1: Find bridges**

Run Tarjan's DFS. We discover:
- Vertices {0, 1, 2} form a cycle → edges (0,1), (0,2), (1,2) are NOT bridges
- Vertices {3, 4, 5} form a cycle → edges (3,4), (3,5), (4,5) are NOT bridges
- Edges (1,3) and (5,6) are bridges (no alternative path exists)

**Step 2: Remove bridges**

After removing (1,3) and (5,6), the remaining graph has three connected components:
- Component A: {0, 1, 2}
- Component B: {3, 4, 5}
- Component C: {6}

**Step 3: Build bridge tree**

The bridge tree has 3 nodes (one per component) and 2 edges:
- A — B (bridge: edge 1-3)
- B — C (bridge: edge 5-6)

```
  [A: {0,1,2}] --- [B: {3,4,5}] --- [C: {6}]
       (1-3)             (5-6)
```

**Result**: The original 7-vertex graph is now a 3-node tree. Any query that only cares about connectivity can operate on this tree instead.

---

## Dry Run: Tarjan's Bridge Finding

Let's trace Tarjan's algorithm on the example graph above. We'll track `tin[u]` (discovery time) and `low[u]` (lowest tin reachable via back edges).

**DFS order**: Start at vertex 0.

| Step | Visit | tin | low | Action |
|------|-------|-----|-----|--------|
| 1 | 0 | 0 | 0 | DFS(0), explore neighbor 1 |
| 2 | 1 | 1 | 1 | DFS(1), explore neighbor 0 (parent, skip), explore 2 |
| 3 | 2 | 2 | 2 | DFS(2), neighbor 0 is visited back edge → low[2] = min(2, tin[0]) = 0. Neighbor 1 is parent, skip. Return. |
| 4 | — | — | — | Back at 1: low[1] = min(low[1], low[2]) = min(1, 0) = 0. Check: low[2] (0) > tin[1] (1)? **No** → edge (1,2) is NOT a bridge. |
| 5 | — | — | — | Back at 1: explore neighbor 3 |
| 6 | 3 | 3 | 3 | DFS(3), explore neighbor 1 (visited back edge → low[3] = min(3, tin[1]) = 1). Explore 5. |
| 7 | 5 | 4 | 4 | DFS(5), explore 3 (parent, skip). Explore 4. |
| 8 | 4 | 5 | 5 | DFS(4), explore 3 (visited back edge → low[4] = min(5, tin[3]) = 3). Explore 5 (parent, skip). Return. |
| 9 | — | — | — | Back at 5: low[5] = min(low[5], low[4]) = min(4, 3) = 3. Check: low[4] (3) > tin[5] (4)? **No** → edge (5,4) is NOT a bridge. |
| 10 | — | — | — | Back at 5: explore 6 |
| 11 | 6 | 6 | 6 | DFS(6), explore 5 (parent, skip). Return. |
| 12 | — | — | — | Back at 5: low[5] = min(low[5], low[6]) = min(3, 6) = 3. Check: low[6] (6) > tin[5] (4)? **Yes** → edge (5,6) **IS a bridge**. |
| 13 | — | — | — | Back at 3: low[3] = min(low[3], low[5]) = min(1, 3) = 1. Check: low[5] (3) > tin[3] (3)? **No** → edge (3,5) is NOT a bridge. |
| 14 | — | — | — | Back at 1: low[1] = min(low[1], low[3]) = min(0, 1) = 0. Check: low[3] (3) > tin[1] (1)? **Yes** → edge (1,3) **IS a bridge**. |
| 15 | — | — | — | Back at 0: low[0] = min(low[0], low[1]) = min(0, 0) = 0. Check: low[1] (0) > tin[0] (0)? **No** → edge (0,1) is NOT a bridge. |

**Final tin/low values**:

| Vertex | tin | low |
|--------|-----|-----|
| 0 | 0 | 0 |
| 1 | 1 | 0 |
| 2 | 2 | 0 |
| 3 | 3 | 3 |
| 4 | 5 | 3 |
| 5 | 4 | 3 |
| 6 | 6 | 6 |

**Bridges found**: (1,3) and (5,6) ✓

**Why does `low[v] > tin[u]` identify bridges?**
- `low[v]` is the earliest vertex (by discovery time) reachable from v without going through u.
- If `low[v] > tin[u]`, then v cannot reach u or any ancestor of u — meaning the only way from v to u is through the edge (u,v). Therefore (u,v) is a bridge.
- If `low[v] <= tin[u]`, there's a back edge from v's subtree to u or an ancestor of u, so (u,v) is part of a cycle and not a bridge.

---

## Complexity Analysis

| Operation | Time | Space | Notes |
|---|---|---|---|
| Bridge finding (Tarjan) | O(V + E) | O(V) | Single DFS |
| Component assignment | O(V + E) | O(V) | BFS/DFS on non-bridge edges |
| Bridge tree construction | O(V + E) | O(V + E) | Building the tree structure |
| **Total bridge tree** | **O(V + E)** | **O(V + E)** | Linear in input size |
| Tree decomposition (optimal) | NP-hard | O(2^n) naive | No polynomial algorithm exists |
| Treewidth decision (≤ k) | O(f(k) · n) | O(f(k) · n) | FPT for fixed k (Bodlaender's algorithm) |
| Chordal recognition (MCS) | O(V + E) | O(V) | Linear time |

**Practical notes**:
- Bridge tree building is very efficient — O(V+E) and easy to implement.
- Treewidth computation is NP-hard in general, but for fixed k, Bodlaender's algorithm runs in O(k^{O(k³)} · n) — linear in n but with a horrifying constant.
- For k ≤ 3, practical algorithms exist (e.g., for series-parallel graphs, outerplanar graphs).
- In competitive programming, you typically recognize bounded-treewidth by structure (tree, cycle, grid-like) rather than computing it.

---

## Python Implementation

```python
from collections import defaultdict

class BridgeTree:
    """Build a bridge tree from an undirected graph."""
    
    def __init__(self, n):
        self.n = n
        self.adj = defaultdict(list)
        self.timer = 0
        self.tin = [0] * n
        self.low = [0] * n
        self.visited = [False] * n
        self.bridges = []
        self.comp = [-1] * n
    
    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)
    
    def _find_bridges(self, u, parent):
        self.visited[u] = True
        self.tin[u] = self.low[u] = self.timer
        self.timer += 1
        
        for v in self.adj[u]:
            if v == parent:
                continue
            if self.visited[v]:
                # Back edge
                self.low[u] = min(self.low[u], self.tin[v])
            else:
                # Tree edge
                self._find_bridges(v, u)
                self.low[u] = min(self.low[u], self.low[v])
                if self.low[v] > self.tin[u]:
                    self.bridges.append((u, v))
    
    def _assign_component(self, u, c):
        self.comp[u] = c
        for v in self.adj[u]:
            if self.comp[v] == -1:
                # Don't cross bridges
                if (u, v) not in self.bridges and (v, u) not in self.bridges:
                    self._assign_component(v, c)
    
    def build(self):
        # Step 1: Find all bridges
        for i in range(self.n):
            if not self.visited[i]:
                self._find_bridges(i, -1)
        
        # Convert bridges to a set for O(1) lookup
        bridge_set = set()
        for u, v in self.bridges:
            bridge_set.add((min(u, v), max(u, v)))
        
        # Step 2: Assign 2-edge-connected components
        num_components = 0
        for i in range(self.n):
            if self.comp[i] == -1:
                self._assign_component(i, num_components)
                num_components += 1
        
        # Step 3: Build bridge tree
        tree_adj = defaultdict(set)
        for u, v in self.bridges:
            cu, cv = self.comp[u], self.comp[v]
            tree_adj[cu].add(cv)
            tree_adj[cv].add(cu)
        
        return num_components, tree_adj
    
    def get_components(self):
        return self.comp[:]
    
    def get_bridges(self):
        return self.bridges[:]


# Example usage
if __name__ == "__main__":
    bt = BridgeTree(7)
    bt.add_edge(0, 1)
    bt.add_edge(0, 2)
    bt.add_edge(1, 2)
    bt.add_edge(1, 3)
    bt.add_edge(3, 4)
    bt.add_edge(3, 5)
    bt.add_edge(4, 5)
    bt.add_edge(5, 6)
    
    num_comp, tree = bt.build()
    print(f"Components: {num_comp}")
    print(f"Components assignment: {bt.get_components()}")
    print(f"Bridges: {bt.get_bridges()}")
    print(f"Bridge tree adjacency: {dict(tree)}")
```

---

## Java Implementation

```java
import java.util.*;

public class BridgeTree {
    private int n, timer;
    private List<List<Integer>> adj;
    private int[] tin, low, comp;
    private boolean[] visited;
    private List<int[]> bridges;
    
    public BridgeTree(int n) {
        this.n = n;
        this.timer = 0;
        this.adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        this.tin = new int[n];
        this.low = new int[n];
        this.comp = new int[n];
        Arrays.fill(comp, -1);
        this.visited = new boolean[n];
        this.bridges = new ArrayList<>();
    }
    
    public void addEdge(int u, int v) {
        adj.get(u).add(v);
        adj.get(v).add(u);
    }
    
    private void findBridges(int u, int parent) {
        visited[u] = true;
        tin[u] = low[u] = timer++;
        
        for (int v : adj.get(u)) {
            if (v == parent) continue;
            if (visited[v]) {
                low[u] = Math.min(low[u], tin[v]);
            } else {
                findBridges(v, u);
                low[u] = Math.min(low[u], low[v]);
                if (low[v] > tin[u]) {
                    bridges.add(new int[]{u, v});
                }
            }
        }
    }
    
    private void assignComponent(int u, int c) {
        comp[u] = c;
        for (int v : adj.get(u)) {
            if (comp[v] == -1) {
                // Check that (u,v) is not a bridge
                boolean isBridge = false;
                for (int[] b : bridges) {
                    if ((b[0] == u && b[1] == v) || (b[0] == v && b[1] == u)) {
                        isBridge = true;
                        break;
                    }
                }
                if (!isBridge) assignComponent(v, c);
            }
        }
    }
    
    public int build() {
        // Step 1: Find bridges
        for (int i = 0; i < n; i++) {
            if (!visited[i]) findBridges(i, -1);
        }
        
        // Step 2: Assign components (avoiding bridge edges)
        int numComponents = 0;
        for (int i = 0; i < n; i++) {
            if (comp[i] == -1) {
                assignComponent(i, numComponents++);
            }
        }
        
        return numComponents;
    }
    
    public int[] getComponents() { return comp.clone(); }
    public List<int[]> getBridges() { return new ArrayList<>(bridges); }
    
    public static void main(String[] args) {
        BridgeTree bt = new BridgeTree(7);
        bt.addEdge(0, 1); bt.addEdge(0, 2); bt.addEdge(1, 2);
        bt.addEdge(1, 3); bt.addEdge(3, 4); bt.addEdge(3, 5);
        bt.addEdge(4, 5); bt.addEdge(5, 6);
        
        int components = bt.build();
        System.out.println("Components: " + components);
        System.out.println("Component assignment: " + Arrays.toString(bt.getComponents()));
        System.out.println("Bridges:");
        for (int[] b : bt.getBridges()) {
            System.out.println("  " + b[0] + " - " + b[1]);
        }
    }
}
```

---

## 109.2 Treewidth

A graph has treewidth k if it can be decomposed into a tree of bags, each containing at most k+1 vertices, such that for every edge, both endpoints appear in some bag.

**Key insight**: Many NP-hard problems become polynomial on bounded-treewidth graphs using tree DP on the decomposition.

**Examples**: Trees have treewidth 1, cycles have treewidth 2, Kn has treewidth n-1.

```cpp
#include <iostream>
#include <vector>

// Check if graph is a tree (treewidth 1)
bool isTree(int n, const std::vector<std::vector<int>>& adj) {
    std::vector<bool> visited(n, false);
    std::vector<int> parent(n, -1);
    std::vector<int> stack = {0};
    visited[0] = true;
    int edges = 0;
    while (!stack.empty()) {
        int u = stack.back(); stack.pop();
        for (int v : adj[u]) {
            edges++;
            if (!visited[v]) { visited[v] = true; parent[v] = u; stack.push_back(v); }
            else if (v != parent[u]) return false;
        }
    }
    for (bool v : visited) if (!v) return false;
    return edges / 2 == n - 1;
}

int main() {
    std::vector<std::vector<int>> adj(4);
    adj[0] = {1, 2}; adj[1] = {0, 3}; adj[2] = {0}; adj[3] = {1};
    std::cout << "Is tree: " << isTree(4, adj) << "\n";
    return 0;
}
```

### Tree Decomposition Example

For a path graph 0-1-2-3, a valid tree decomposition with treewidth 1:

```
Bags: {0,1} — {1,2} — {2,3}
```

Each bag has 2 vertices (width = 2-1 = 1). Every edge appears in some bag, and for each vertex, its bags form a connected subtree.

For a triangle (0,1,2), the treewidth is 2 (one bag {0,1,2}, width = 3-1 = 2).

### Solving Problems on Bounded Treewidth

**Pattern**: Given a tree decomposition of width k:
1. Root the decomposition tree arbitrarily.
2. For each bag, enumerate all 2^k (or k!) possible states of the vertices in that bag.
3. Use DP to combine child bag results into parent bag results.
4. The answer is in the root bag's DP table.

**Example — Vertex Cover on treewidth-k graph**:
- State: For each bag, a bitmask indicating which vertices in the bag are selected.
- Transition: Ensure every edge within the bag is covered; merge consistently with child bags.
- Time: O(2^k · n).

---

## 109.3 Chordal Graphs

A graph is chordal if every cycle of length >= 4 has a chord (edge connecting non-adjacent vertices).

**Properties**:
- Perfect elimination ordering exists
- Can be recognized in O(V + E) using Maximum Cardinality Search
- Many NP-hard problems become polynomial on chordal graphs

```cpp
#include <iostream>
#include <vector>
#include <set>

// Maximum Cardinality Search for chordal graph recognition
std::vector<int> mcs(const std::vector<std::vector<int>>& adj) {
    int n = adj.size();
    std::vector<int> order(n, -1), weight(n, 0);
    std::set<int> remaining;
    for (int i = 0; i < n; i++) remaining.insert(i);
    
    for (int i = n - 1; i >= 0; i--) {
        int best = -1, bestW = -1;
        for (int v : remaining)
            if (weight[v] > bestW) { bestW = weight[v]; best = v; }
        order[i] = best;
        remaining.erase(best);
        for (int v : adj[best]) weight[v]++;
    }
    return order;
}

int main() {
    std::vector<std::vector<int>> adj(4);
    adj[0] = {1, 2}; adj[1] = {0, 2, 3}; adj[2] = {0, 1, 3}; adj[3] = {1, 2};
    auto order = mcs(adj);
    std::cout << "MCS order: ";
    for (int v : order) std::cout << v << " ";
    std::cout << "\n";
    return 0;
}
```

## 109.4 Dynamic Graph Connectivity (Overview)

| Type | Operation | Time |
|---|---|---|
| Incremental | Add edges only | O(α(n)) per op |
| Decremental | Remove edges only | O(α(n)) amortized |
| Fully Dynamic | Add + remove | O(√n) amortized |

**Technique**: ETT (Euler Tour Tree) for forests, link-cut trees for trees.

---

### Treewidth Example

A tree has treewidth 1. A cycle has treewidth 2. A complete graph Kn has treewidth n-1.

```cpp
#include <iostream>
#include <vector>

// Treewidth-related: Check if graph is a tree (treewidth 1)
bool isTree(int n, const std::vector<std::vector<int>>& adj) {
    if (adj.empty()) return true;
    std::vector<bool> visited(n, false);
    std::vector<int> parent(n, -1);
    
    // BFS from node 0
    std::vector<int> stack = {0};
    visited[0] = true;
    int edges = 0;
    
    while (!stack.empty()) {
        int u = stack.back(); stack.pop();
        for (int v : adj[u]) {
            edges++;
            if (!visited[v]) {
                visited[v] = true;
                parent[v] = u;
                stack.push_back(v);
            } else if (v != parent[u]) {
                return false; // Cycle found
            }
        }
    }
    
    // Check connectivity and edge count
    for (bool v : visited) if (!v) return false;
    return edges / 2 == n - 1; // Tree has exactly n-1 edges
}

int main() {
    // Tree: 0-1, 0-2, 1-3
    std::vector<std::vector<int>> adj(4);
    adj[0] = {1, 2}; adj[1] = {0, 3}; adj[2] = {0}; adj[3] = {1};
    std::cout << "Is tree: " << isTree(4, adj) << "\\n";
    
    // Cycle: 0-1, 1-2, 2-0
    std::vector<std::vector<int>> adj2(3);
    adj2[0] = {1, 2}; adj2[1] = {0, 2}; adj2[2] = {0, 1};
    std::cout << "Is tree: " << isTree(3, adj2) << "\\n";
    
    return 0;
}
```

### Chordal Graph Recognition

A graph is chordal iff it has a perfect elimination ordering. Can be found using Maximum Cardinality Search (MCS).

### Dynamic Connectivity with Link-Cut Trees

Link-Cut Trees maintain connectivity in a dynamic forest with O(log n) per operation:
- `link(u, v)`: Add edge between trees
- `cut(u, v)`: Remove edge
- `connected(u, v)`: Check connectivity
- `findRoot(u)`: Find root of tree containing u

---

## Summary

| Structure | Build Complexity | Key Property |
|---|---|---|
| Bridge tree | O(V+E) | Tree of 2-edge-connected components |
| Tree decomposition | NP-hard to find optimal | Enables DP on graphs |
| Chordal recognition | O(V+E) | Perfect elimination ordering |
| Dynamic connectivity | O(log n) per op (LCT) | Maintains forest connectivity |

---

## Exercises

1. **Critical Connections** (LeetCode 1192): Given a network of n servers, find all critical connections (bridges). Implement Tarjan's algorithm and verify on the sample graph from the walkthrough.

2. **2-Edge-Connected Components**: Given an undirected graph, count the number of 2-edge-connected components and list which vertices belong to each. What is the bridge tree of your graph?

3. **Bridge Tree Diameter**: Given a graph, build its bridge tree and find the diameter of the bridge tree. What does this diameter represent in terms of the original graph's structure?

4. **Biconnected Components vs. 2-Edge-Connected**: What is the difference between 2-vertex-connected (biconnected) components and 2-edge-connected components? Give an example graph where they differ.

5. **Treewidth of Grid Graphs**: What is the treewidth of an m × n grid graph? Prove your answer by constructing a tree decomposition.

6. **Vertex Cover on Treewidth-2**: Given a series-parallel graph (treewidth 2), solve the minimum vertex cover problem in O(n) time using tree DP. Hint: use a tree decomposition with bags of size 3.

7. **Dynamic Bridges**: Design a data structure that supports adding and removing edges from an undirected graph, and can answer "is edge (u,v) a bridge?" in O(log n) time. (Hint: link-cut trees.)

---

## Interview Questions

1. **"Find all critical connections in a network."** — Walk through Tarjan's bridge-finding algorithm. Explain the role of `tin` and `low` arrays. Why is the condition `low[v] > tin[u]` (not `>=`)?

2. **"Given a graph, determine if two vertices are in the same 2-edge-connected component."** — How would you preprocess the graph? What's the query time after preprocessing?

3. **"Explain the difference between bridges and articulation points."** — A bridge is an edge whose removal disconnects the graph. An articulation point is a vertex whose removal disconnects the graph. How do their detection conditions differ in Tarjan's algorithm?

4. **"You're given a graph with n ≤ 10^5 and need to answer connectivity queries after removing each edge one at a time."** — How does the bridge tree help? Which edges actually matter?

5. **"When would you use tree decomposition in practice?"** — Discuss bounded-treewidth graphs, the exponential dependency on treewidth, and real-world examples (road networks, VLSI, social network communities).

6. **"Is the treewidth of a graph always at most its minimum vertex cover size?"** — Yes. Every vertex cover of size k gives a tree decomposition of width k (put all cover vertices in every bag, plus one non-cover vertex per bag). So tw(G) ≤ vc(G).

---

## Cross-References

- **[Chapter 102: Graph Fundamentals](ch22-graph-fundamentals.md)** — Basic graph representations and terminology used throughout this chapter.
- **Chapter 103: DFS and BFS** — DFS is the foundation of Tarjan's bridge-finding algorithm.
- **Chapter 104: Strongly Connected Components** — SCCs are the directed-graph analog of 2-edge-connected components. Tarjan's SCC algorithm uses similar tin/low reasoning.
- **Chapter 105: Shortest Paths** — Bridge trees can be used to optimize shortest path queries in graphs with few bridges.
- **Chapter 108: Trees** — Bridge trees are trees; all tree algorithms (LCA, DP, diameter) apply.
- **[Chapter 110: Euler Tour and Flows](ch106-euler-tour-tree-flattening.md)** — Euler Tour Trees are used for dynamic connectivity on forests.
- **Chapter 112: Advanced Graph Algorithms** — Covers link-cut trees and other advanced dynamic graph data structures.
- **Chapter 106: Minimum Spanning Trees** — Bridges are always in every MST; non-bridge edges may or may not be.
- **[Chapter 107: Network Flow](ch29-network-flow.md)** — Edge connectivity (minimum number of edges whose removal disconnects the graph) relates to bridges (1-edge-connected components).
