# Chapter 84: Advanced Tree Algorithms

## Prerequisites
- Tree basics, DFS, LCA (Chapter 15)
- Tree DP ([Chapter 30](ch30-dp-fundamentals.md))

## Interview Frequency: ★★★

Advanced tree techniques appear in **Google**, **Meta**, and **ByteDance** interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Rerooting DP | ★★★ | Medium-Hard | DP from all roots |
| Virtual Trees | ★★ | Hard | Compressed trees |
| Centroid Decomposition | ★★★ | Hard | Divide and conquer |
| Tree Flattening | ★★★★ | Medium | Euler tour |

---

## Definition

**Rerooting DP** computes tree DP values for every node as root in O(n) total.

**Virtual Trees** compress a tree to only include nodes of interest + their LCAs, reducing size from n to k.

**Centroid Decomposition** recursively splits a tree at centroids, creating a centroid tree of depth O(log n).

## Motivation

- **Rerooting**: "For each node, what's the answer if it were the root?" — avoids O(n²) recomputation
- **Virtual Trees**: When queries involve only k nodes out of n, compress the tree to O(k) nodes
- **Centroid Decomposition**: Enables path counting, closest pair, and divide-and-conquer on trees

## Intuition

- **Rerooting**: Compute "down" answers first, then propagate "up" answers through parents
- **Virtual Trees**: Keep only the nodes you care about and their LCAs — like a "summary" tree
- **Centroid**: Find the center of mass, solve there, recurse on halves — like binary search on trees

---

## 84.1 Rerooting DP

### Algorithm

1. **DFS Down**: Compute `down[u]` from children
2. **DFS Up**: For each child v, compute `up[v]` from parent's perspective
3. **Answer**: `ans[u] = combine(down[u], up[u])`

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class RerootingDP {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> down, up, ans;

    int dfsDown(int u, int p) {
        int d = 0;
        for (int v : adj[u])
            if (v != p) d = std::max(d, dfsDown(v, u) + 1);
        down[u] = d;
        return d;
    }

    void dfsUp(int u, int p, int pUp) {
        up[u] = pUp;
        int max1 = 0, max2 = 0;
        for (int v : adj[u]) {
            if (v != p) {
                int val = down[v] + 1;
                if (val > max1) { max2 = max1; max1 = val; }
                else if (val > max2) max2 = val;
            }
        }
        for (int v : adj[u]) {
            if (v != p) {
                int val = down[v] + 1;
                int use = (val == max1) ? max2 : max1;
                dfsUp(v, u, std::max(pUp + 1, use + 1));
            }
        }
        ans[u] = std::max(down[u], up[u]);
    }

public:
    RerootingDP(int n) : n(n), adj(n), down(n), up(n), ans(n) {}
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }

    std::vector<int> solve(int root) {
        dfsDown(root, -1);
        dfsUp(root, -1, 0);
        return ans;
    }
};

int main() {
    RerootingDP tree(6);
    tree.addEdge(0, 1); tree.addEdge(0, 2);
    tree.addEdge(1, 3); tree.addEdge(1, 4); tree.addEdge(2, 5);
    auto ans = tree.solve(0);
    for (int i = 0; i < 6; i++)
        std::cout << "Node " << i << ": max dist = " << ans[i] << "\n";
    return 0;
}
```

### Python Implementation

```python
class RerootingDP:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def solve(self, root):
        n = self.n
        down = [0] * n; up = [0] * n; ans = [0] * n

        def dfs_down(u, p):
            d = 0
            for v in self.adj[u]:
                if v != p: d = max(d, dfs_down(v, u) + 1)
            down[u] = d
            return d

        def dfs_up(u, p, p_up):
            up[u] = p_up
            max1 = max2 = 0
            for v in self.adj[u]:
                if v != p:
                    val = down[v] + 1
                    if val > max1: max2, max1 = max1, val
                    elif val > max2: max2 = val
            for v in self.adj[u]:
                if v != p:
                    val = down[v] + 1
                    use = max2 if val == max1 else max1
                    dfs_up(v, u, max(p_up + 1, use + 1))
            ans[u] = max(down[u], up[u])

        dfs_down(root, -1)
        dfs_up(root, -1, 0)
        return ans

tree = RerootingDP(6)
tree.add_edge(0, 1); tree.add_edge(0, 2)
tree.add_edge(1, 3); tree.add_edge(1, 4); tree.add_edge(2, 5)
for i, a in enumerate(tree.solve(0)):
    print(f"Node {i}: max dist = {a}")
```

### Java Implementation

```java
import java.util.*;

public class RerootingDP {
    int n; List<List<Integer>> adj;
    int[] down, up, ans;

    public RerootingDP(int n) {
        this.n = n; adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        down = new int[n]; up = new int[n]; ans = new int[n];
    }

    void addEdge(int u, int v) { adj.get(u).add(v); adj.get(v).add(u); }

    int dfsDown(int u, int p) {
        int d = 0;
        for (int v : adj.get(u))
            if (v != p) d = Math.max(d, dfsDown(v, u) + 1);
        down[u] = d; return d;
    }

    void dfsUp(int u, int p, int pUp) {
        up[u] = pUp;
        int max1 = 0, max2 = 0;
        for (int v : adj.get(u)) {
            if (v == p) continue;
            int val = down[v] + 1;
            if (val > max1) { max2 = max1; max1 = val; }
            else if (val > max2) max2 = val;
        }
        for (int v : adj.get(u)) {
            if (v == p) continue;
            int val = down[v] + 1;
            int use = (val == max1) ? max2 : max1;
            dfsUp(v, u, Math.max(pUp + 1, use + 1));
        }
        ans[u] = Math.max(down[u], up[u]);
    }

    int[] solve(int root) {
        dfsDown(root, -1); dfsUp(root, -1, 0); return ans;
    }

    public static void main(String[] args) {
        RerootingDP tree = new RerootingDP(6);
        tree.addEdge(0,1); tree.addEdge(0,2);
        tree.addEdge(1,3); tree.addEdge(1,4); tree.addEdge(2,5);
        int[] ans = tree.solve(0);
        for (int i = 0; i < 6; i++)
            System.out.println("Node " + i + ": max dist = " + ans[i]);
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Rerooting DP | O(n) | O(n) |

---

## 84.2 Virtual Trees

### Definition

Given k "important" nodes, build a tree containing only those nodes and their LCAs, preserving ancestor-descendant relationships.

### Algorithm

1. Sort important nodes by Euler tour entry time
2. Insert LCAs of consecutive pairs
3. Build the virtual tree using a stack

### Complexity

| Operation | Time | Space |
|---|---|---|
| Build virtual tree | O(k log k) | O(k) |

---

## 84.3 Centroid Decomposition

### C++ Implementation

```cpp
#include <iostream>
#include <vector>

class CentroidDecomp {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<bool> removed;
    std::vector<int> sz;

    int getSubtreeSize(int u, int p) {
        sz[u] = 1;
        for (int v : adj[u])
            if (v != p && !removed[v]) sz[u] += getSubtreeSize(v, u);
        return sz[u];
    }

    int findCentroid(int u, int p, int treeSize) {
        for (int v : adj[u])
            if (v != p && !removed[v] && sz[v] > treeSize / 2)
                return findCentroid(v, u, treeSize);
        return u;
    }

    void decompose(int u) {
        int treeSize = getSubtreeSize(u, -1);
        int centroid = findCentroid(u, -1, treeSize);
        removed[centroid] = true;
        std::cout << "Centroid: " << centroid << "\n";
        for (int v : adj[centroid])
            if (!removed[v]) decompose(v);
    }

public:
    CentroidDecomp(int n) : n(n), adj(n), removed(n, false), sz(n) {}
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }
    void build() { decompose(0); }
};

int main() {
    CentroidDecomp cd(7);
    cd.addEdge(0, 1); cd.addEdge(0, 2); cd.addEdge(1, 3);
    cd.addEdge(1, 4); cd.addEdge(2, 5); cd.addEdge(2, 6);
    cd.build();
    return 0;
}
```

### Python Implementation

```python
class CentroidDecomp:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.removed = [False] * n
        self.sz = [0] * n

    def add_edge(self, u, v):
        self.adj[u].append(v); self.adj[v].append(u)

    def _get_size(self, u, p):
        self.sz[u] = 1
        for v in self.adj[u]:
            if v != p and not self.removed[v]:
                self.sz[u] += self._get_size(v, u)
        return self.sz[u]

    def _find_centroid(self, u, p, tree_size):
        for v in self.adj[u]:
            if v != p and not self.removed[v] and self.sz[v] > tree_size // 2:
                return self._find_centroid(v, u, tree_size)
        return u

    def _decompose(self, u):
        tree_size = self._get_size(u, -1)
        centroid = self._find_centroid(u, -1, tree_size)
        self.removed[centroid] = True
        print(f"Centroid: {centroid}")
        for v in self.adj[centroid]:
            if not self.removed[v]:
                self._decompose(v)

    def build(self): self._decompose(0)

cd = CentroidDecomp(7)
cd.add_edge(0,1); cd.add_edge(0,2); cd.add_edge(1,3)
cd.add_edge(1,4); cd.add_edge(2,5); cd.add_edge(2,6)
cd.build()
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Centroid decomposition | O(n log n) | O(n) |
| Each node appears in | O(log n) levels | — |

---

## Exercises

1. **Diameter via rerooting**: Use rerooting to compute the diameter of a tree.

2. **Virtual tree queries**: Given k marked nodes, build a virtual tree and answer distance queries between marked nodes.

3. **Count pairs at distance k**: Use centroid decomposition to count pairs of nodes at exactly distance k.

4. **Subtree sum rerooting**: Given node values, compute the sum of all values in each node's subtree when that node is the root.

---

## Interview Questions

1. **Q: How does rerooting avoid O(n²) recomputation?**
   A: By separating "down" and "up" information. The "up" for a child combines the parent's "up" and the best "down" from siblings — all computed in O(1) per edge.

2. **Q: When do you use virtual trees?**
   A: When you have k << n "important" nodes and need to answer queries involving only those nodes. Building a virtual tree reduces the problem from O(n) to O(k) nodes.

3. **Q: Why does centroid decomposition give O(log n) depth?**
   A: Each centroid removal splits the tree into subtrees of size ≤ n/2. After log₂(n) levels, each subtree has size 1.

4. **Q: Compare rerooting with brute-force DFS from each node.**
   A: Brute force is O(n²). Rerooting is O(n) by reusing computation. The key insight is that the answer for a child can be computed from the parent's answer in O(1).

---

## Cross-References
- [Chapter 13: Trees](ch13-trees.md) — Tree fundamentals
- [Chapter 107: HLD and Centroid Applications](ch107-hld-centroid-applications.md) — Detailed HLD and centroid decomposition
- [Chapter 108: DSU on Tree and Rerooting](ch108-dsu-on-tree-rerooting.md) — Detailed rerooting DP
- Chapter 15: LCA — Lowest common ancestor

---

## Summary

| Technique | Time | Key Idea | Best For |
|---|---|---|---|
| Rerooting DP | O(n) | DFS down + up | DP from all roots |
| Virtual Trees | O(k log k) | Compress to k nodes | Subset queries |
| Centroid Decomposition | O(n log n) | Recursive centroids | Path counting |
| Tree Flattening | O(n) | Euler tour | Subtree queries |
