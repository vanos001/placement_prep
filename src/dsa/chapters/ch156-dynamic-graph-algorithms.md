# Chapter 156: Dynamic Graph Algorithms

## Prerequisites
- Graph algorithms (BFS, DFS, MST), Union-Find, segment trees, amortized analysis

## Interview Frequency: ★★

Dynamic graph algorithms maintain a graph property (connectivity, MST, shortest paths, bipartiteness) as edges are inserted and deleted. They are critical in network monitoring, real-time routing, social network analysis, and streaming graph processing. Companies like Google, Facebook (Meta), and Cloudflare use dynamic graph techniques for live network topology management.

---

## 156.1 Motivation

In many real-world systems, the graph changes over time:
- **Networks**: Links go up and down (failures, maintenance).
- **Social networks**: Friendships form and dissolve.
- **Road networks**: Roads close, new roads open.
- **Databases**: Edges represent relationships that change.

Recomputing from scratch after each change is too slow. If a graph has n vertices and m edges, running BFS/DFS costs O(n + m) per update. With millions of updates, this is infeasible. Dynamic graph algorithms aim for **sublinear** update time.

---

## 156.2 Problem Taxonomy

| Type | Operations | Typical Goal |
|---|---|---|
| **Incremental** | Insert edges only | Maintain property as graph grows |
| **Decremental** | Delete edges only | Maintain property as graph shrinks |
| **Fully Dynamic** | Insert and delete | Maintain property under any change |

**Key metric**: Amortized time per operation over a sequence of m operations.

---

## 156.3 Dynamic Connectivity

**Problem**: Maintain connected components under edge insertions and deletions. Answer: "Are u and v in the same component?"

### Incremental Connectivity — Union-Find

For insertions only, Union-Find gives O(α(n)) amortized per operation (inverse Ackermann — effectively constant).

### Fully Dynamic Connectivity

This is much harder. The best known bounds:

| Approach | Update Time | Query Time | Notes |
|---|---|---|---|
| Eager (recompute) | O(n + m) | O(1) | Naive |
| Sparsifier + Euler Tour | O(√n · log n) | O(log n / log log n) | Karger's |
| Holm-de Lichtenberg-Thorup (HDT) | O(log² n) amortized | O(log n / log log n) | Best polylog |
| Kapron-King-Mountjoy | O(log n · log³n / log log n) | O(log n / log log n) | Randomized |

### HDT Algorithm — Intuition

The HDT algorithm uses a hierarchy of log n forests. Each edge has a "level" (0 to log n). An edge at level i belongs to the spanning forest if adding it doesn't create a cycle at level i.

**Key ideas**:
1. Maintain a spanning forest using Euler Tour Trees (ETT).
2. Edges not in the forest are "non-tree edges."
3. When a tree edge is deleted, find a replacement edge by searching non-tree edges at the same level.
4. Promote/demote edges between levels to balance work.

**Amortized cost**: O(log² n) per update.

---

## 156.4 Euler Tour Trees (ETT)

An Euler Tour Tree represents a rooted tree as a sequence of vertex visits in an Euler tour, stored in a balanced BST (e.g., treap or splay tree).

**Operations supported in O(log n)**:
- **Link(u, v)**: Add edge between trees containing u and v.
- **Cut(u, v)**: Remove edge (u, v).
- **Connected(u, v)**: Check if u and v are in the same tree.
- **Root(u)**: Re-root the tree at u.
- **Size(u)**: Get size of the tree containing u.

### ETT Representation

For a tree edge (u, v), the Euler tour visits u → v → u. Store these as nodes in a BST keyed by position in the tour.

```
Tree:     0
         / \
        1   2
Euler tour: [0, 1, 1, 2, 2, 0]
BST stores pairs (vertex, direction): (0,+), (1,+), (1,-), (2,+), (2,-), (0,-)
```

---

## 156.5 Full C++ Implementation — Dynamic Connectivity (Simplified)

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <map>
#include <algorithm>
#include <random>

// Simplified dynamic connectivity using level structure
// For educational purposes — not the full HDT algorithm
class DynamicConnectivity {
    int n;
    int levels;
    std::vector<std::set<int>>* adj; // adj[level][u] = neighbors at this level
    std::vector<int> level;          // level of each edge
    std::vector<std::pair<int,int>> edges;
    std::map<std::pair<int,int>, int> edgeId;
    
    // Simple BFS for connectivity check (for demonstration)
    bool bfs(int u, int v, int maxLevel) {
        if (u == v) return true;
        std::vector<bool> visited(n, false);
        std::vector<int> queue = {u};
        visited[u] = true;
        for (int qi = 0; qi < (int)queue.size(); qi++) {
            int curr = queue[qi];
            for (int l = 0; l <= maxLevel; l++) {
                for (int neighbor : adj[l][curr]) {
                    if (neighbor == v) return true;
                    if (!visited[neighbor]) {
                        visited[neighbor] = true;
                        queue.push_back(neighbor);
                    }
                }
            }
        }
        return false;
    }
    
public:
    DynamicConnectivity(int n) : n(n), levels(20) {
        adj = new std::vector<std::set<int>>[levels];
        for (int l = 0; l < levels; l++)
            adj[l].resize(n);
        level.resize(0);
    }
    
    ~DynamicConnectivity() { delete[] adj; }
    
    void insertEdge(int u, int v) {
        if (u > v) std::swap(u, v);
        int id = edges.size();
        edges.push_back({u, v});
        edgeId[{u, v}] = id;
        level.push_back(0);
        adj[0][u].insert(v);
        adj[0][v].insert(u);
    }
    
    void deleteEdge(int u, int v) {
        if (u > v) std::swap(u, v);
        auto it = edgeId.find({u, v});
        if (it == edgeId.end()) return;
        
        int id = it->second;
        int l = level[id];
        adj[l][u].erase(v);
        adj[l][v].erase(u);
        edgeId.erase(it);
        
        // Try to find replacement at level l
        // (Simplified: in full HDT, search non-tree edges at level l)
    }
    
    bool connected(int u, int v) {
        return bfs(u, v, levels - 1);
    }
};

int main() {
    DynamicConnectivity dc(6);
    dc.insertEdge(0, 1);
    dc.insertEdge(1, 2);
    dc.insertEdge(3, 4);
    
    std::cout << "0-2: " << dc.connected(0, 2) << "\n"; // 1
    std::cout << "0-3: " << dc.connected(0, 3) << "\n"; // 0
    
    dc.insertEdge(2, 3);
    std::cout << "0-3: " << dc.connected(0, 3) << "\n"; // 1
    
    dc.deleteEdge(2, 3);
    std::cout << "0-3: " << dc.connected(0, 3) << "\n"; // 0
    
    return 0;
}
```

---

## 156.6 Python Implementation — Incremental Connectivity

```python
class UnionFind:
    """Union-Find with path compression and union by rank."""
    
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n
    
    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x: int, y: int) -> bool:
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        self.components -= 1
        return True
    
    def connected(self, x: int, y: int) -> bool:
        return self.find(x) == self.find(y)


class DynamicConnectivitySimple:
    """Fully dynamic connectivity with O(n + m) per delete, O(α(n)) per insert."""
    
    def __init__(self, n: int):
        self.n = n
        self.edges = set()
        self.uf = UnionFind(n)
    
    def insert(self, u: int, v: int):
        if u > v:
            u, v = v, u
        self.edges.add((u, v))
        self.uf.union(u, v)
    
    def delete(self, u: int, v: int):
        if u > v:
            u, v = v, u
        self.edges.discard((u, v))
        # Rebuild — naive approach
        self.uf = UnionFind(self.n)
        for eu, ev in self.edges:
            self.uf.union(eu, ev)
    
    def connected(self, u: int, v: int) -> bool:
        return self.uf.connected(u, v)


def demo():
    dc = DynamicConnectivitySimple(6)
    dc.insert(0, 1)
    dc.insert(1, 2)
    dc.insert(3, 4)
    
    print(f"0-2 connected: {dc.connected(0, 2)}")  # True
    print(f"0-3 connected: {dc.connected(0, 3)}")  # False
    
    dc.insert(2, 3)
    print(f"0-3 connected: {dc.connected(0, 3)}")  # True
    
    dc.delete(2, 3)
    print(f"0-3 connected: {dc.connected(0, 3)}")  # False

demo()
```

---

## 156.7 Java Implementation — Dynamic MST

```java
import java.util.*;

public class DynamicMST {
    private int n;
    private List<int[]> edges; // [u, v, weight]
    
    public DynamicMST(int n) {
        this.n = n;
        this.edges = new ArrayList<>();
    }
    
    public void addEdge(int u, int v, int w) {
        edges.add(new int[]{u, v, w});
        System.out.println("Added edge (" + u + "," + v + ") w=" + w);
    }
    
    public void removeEdge(int u, int v) {
        edges.removeIf(e -> (e[0] == u && e[1] == v) || (e[0] == v && e[1] == u));
        System.out.println("Removed edge (" + u + "," + v + ")");
    }
    
    // Kruskal's MST — recomputed on demand
    public int computeMST() {
        Collections.sort(edges, Comparator.comparingInt(e -> e[2]));
        int[] parent = new int[n];
        int[] rank = new int[n];
        for (int i = 0; i < n; i++) parent[i] = i;
        
        int mstWeight = 0;
        int edgesUsed = 0;
        
        for (int[] e : edges) {
            int pu = find(parent, e[0]);
            int pv = find(parent, e[1]);
            if (pu != pv) {
                mstWeight += e[2];
                edgesUsed++;
                if (rank[pu] < rank[pv]) { int t = pu; pu = pv; pv = t; }
                parent[pv] = pu;
                if (rank[pu] == rank[pv]) rank[pu]++;
                if (edgesUsed == n - 1) break;
            }
        }
        
        return (edgesUsed == n - 1) ? mstWeight : -1;
    }
    
    private int find(int[] parent, int x) {
        if (parent[x] != x) parent[x] = find(parent, parent[x]);
        return parent[x];
    }
    
    public static void main(String[] args) {
        DynamicMST dmst = new DynamicMST(5);
        dmst.addEdge(0, 1, 2);
        dmst.addEdge(1, 2, 3);
        dmst.addEdge(2, 3, 1);
        dmst.addEdge(3, 4, 4);
        dmst.addEdge(0, 4, 5);
        
        System.out.println("MST weight: " + dmst.computeMST()); // 10
        
        dmst.removeEdge(2, 3);
        dmst.addEdge(1, 3, 1);
        System.out.println("MST weight: " + dmst.computeMST()); // 8
    }
}
```

---

## 156.8 Dynamic Shortest Paths

### Decremental Single-Source Shortest Paths

**Even-Shiloach Algorithm**: For unweighted graphs, maintain BFS layers. When an edge is deleted, recompute affected layers.

| Operation | Algorithm | Time |
|---|---|---|
| Decremental SSSP (unweighted) | Even-Shiloach | O(n · m) total |
| Decremental SSSP (weighted, positive) | Ramalingam-Reps | O(m · Δ) total |
| Fully Dynamic APSP | Thorup | O(n^{2+ε}) per update |

**Ramalingam-Reps**: When edge (u, v) is deleted, only vertices whose shortest path went through (u, v) need updating. Propagate changes using a priority queue.

---

## 156.9 Dynamic Minimum Spanning Forest

**Problem**: Maintain MST under edge insertions and deletions.

**Approach**: Use Euler Tour Trees + a heap of non-tree edges.

1. Maintain the MST as a forest using ETT.
2. When a non-tree edge is inserted: if it's lighter than the heaviest edge on the cycle it creates, swap.
3. When a tree edge is deleted: find the lightest non-tree edge that reconnects the two components.

**Time**: O(log² n) amortized per update.

---

## 156.10 Dynamic Bipartiteness

**Problem**: Is the graph still bipartite after edge updates?

**Challenge**: Unlike connectivity, bipartiteness is a global property. A single edge insertion can make a non-bipartite graph bipartite (if it connects two components) or vice versa.

**Approach**: Maintain a 2-coloring. When an edge (u, v) connects same-color vertices, find an odd cycle and repair.

**Time**: O(√n) amortized per update (best known for fully dynamic).

---

## 156.11 Complexity Summary

| Problem | Incremental | Decremental | Fully Dynamic |
|---|---|---|---|
| Connectivity | O(α(n)) | O(α(n)) amortized | O(log² n) amortized |
| MST | O(log² n) | O(log² n) amortized | O(√n · polylog) |
| SSSP (unweighted) | O(1) amortized | O(n) total | O(√m) per update |
| Bipartiteness | O(α(n)) | O(√n) amortized | O(√n) amortized |
| Spanning Forest | O(α(n)) | O(α(n)) amortized | O(log⁴ n) amortized |

---

## 156.12 Real-World Applications

1. **Network monitoring**: ISPs track connectivity as links fail. Dynamic connectivity algorithms detect partitions in real time.
2. **Social networks**: Friend/follow relationships change constantly. Dynamic algorithms maintain connected components and shortest paths.
3. **Compilers**: Control flow graphs change during optimization passes. Dynamic dominance and reachability queries.
4. **Databases**: Graph databases (Neo4j) need efficient updates to materialized views.
5. **Traffic routing**: Road closures require recomputing shortest paths efficiently.

---

## 156.13 Exercises

1. **Easy**: Implement incremental connectivity using Union-Find. Test on a sequence of 10^5 edge insertions.

2. **Medium**: Implement Euler Tour Trees for a static tree. Support link, cut, and connectivity queries.

3. **Medium**: Design a dynamic algorithm for maintaining the number of connected components. What is your update time?

4. **Hard**: Implement the Even-Shiloach algorithm for decremental BFS. Analyze total work over a sequence of m edge deletions.

5. **Hard**: Prove that maintaining dynamic minimum spanning forest requires Ω(log n) amortized time per operation in the cell-probe model.

---

## 156.14 Interview Questions

1. **Q**: How would you maintain connectivity in a graph with only edge insertions?
   **A**: Use Union-Find (DSU). Each insertion is a union operation in O(α(n)) amortized time. Queries are find operations in O(α(n)). This is optimal for incremental connectivity.

2. **Q**: What makes fully dynamic connectivity harder than incremental?
   **A**: With insertions only, Union-Find works perfectly. With deletions, we can't simply "undo" a union — the edge we're deleting might not be the one that caused the merge. We need more sophisticated data structures (ETT + sparsifiers) to handle this efficiently.

3. **Q**: Explain Euler Tour Trees. What operations do they support?
   **A**: ETT represents a tree as an Euler tour stored in a balanced BST. Supports link (merge two trees), cut (split a tree), and connectivity in O(log n). The BST stores (vertex, direction) pairs from the Euler tour, allowing efficient split/merge of tour segments.

4. **Q**: How does the HDT algorithm maintain connectivity in O(log² n) per update?
   **A**: HDT uses log n levels of spanning forests. Each edge is assigned a level. When a tree edge is deleted at level i, we search for a replacement among non-tree edges at level i. Edges are promoted to higher levels when they become "important." Each edge is promoted O(log n) times, and each promotion does O(log n) work.

5. **Q**: You're building a real-time network monitoring system. Which dynamic graph algorithm would you choose and why?
   **A**: For connectivity monitoring with both failures (deletions) and restorations (insertions), use the HDT algorithm or a practical variant. For simplicity, a level-based approach with Union-Find at each level works well. If the network is sparse, even the O(√n) approach is practical. Trade off between implementation complexity and update frequency.

---

## 156.15 Cross-References

- **Chapter 69 (Graph Algorithms)**: Static graph foundations
- **Chapter 36 (Union-Find)**: Core data structure for incremental connectivity
- **Chapter 88 (Dynamic Programming on Graphs)**: Related optimization techniques
- **Chapter 148 (Parameterized Algorithms)**: Treewidth-based approaches
- **Chapter 134 (Consistent Hashing)**: Distributed dynamic systems

---

## Summary

| Problem | Best Fully Dynamic | Key Technique |
|---|---|---|
| Connectivity | O(log² n) | HDT (ETT + levels) |
| MST | O(√n · polylog) | ETT + non-tree edge heaps |
| SSSP | O(n^{2/3}) per update | Even-Shiloach / Ramalingam-Reps |
| Bipartiteness | O(√n) | Level structure + ETT |
| Reachability | O(n²) per update | Transitive closure maintenance |
