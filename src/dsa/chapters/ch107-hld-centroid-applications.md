# Chapter 107: HLD and Centroid Decomposition Applications

## Prerequisites
- Euler tour ([Chapter 106](ch106-euler-tour-tree-flattening.md))
- Segment trees ([Chapter 18](ch18-segment-tree.md))
- LCA (Chapter 15)

## Interview Frequency: ★★★★

HLD enables path queries in O(log²n). Centroid decomposition enables path counting and divide-and-conquer on trees. Both are tested at **Google**, **Meta**, and competitive programming.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| HLD | ★★★★ | Hard | Path queries in O(log²n) |
| Centroid Decomp | ★★★ | Hard | Divide and conquer on trees |
| Path queries | ★★★★ | Medium | Sum, max, min on paths |
| Path counting | ★★★ | Hard | Count paths with property X |

---

## Definition

**Heavy-Light Decomposition (HLD)** decomposes a tree into chains of "heavy" edges (to the largest child) and "light" edges (to smaller children). Any root-to-leaf path crosses O(log n) chains, enabling efficient path queries via segment trees.

**Centroid Decomposition** recursively decomposes a tree by removing its centroid (a node whose removal leaves subtrees of size ≤ n/2). This creates a "centroid tree" of depth O(log n).

## Motivation

Naive path queries (sum on path from u to v) take O(n) per query. HLD reduces this to O(log²n) by mapping tree paths to segment tree ranges.

Centroid decomposition solves problems like "count pairs of nodes at distance exactly k" in O(n log n) instead of O(n²).

## Intuition

- **HLD**: Think of the tree as a collection of chains. Each chain is a contiguous range in the segment tree. A path from u to v jumps between chains, but only O(log n) jumps.
- **Centroid**: The centroid is the "center of mass" of the tree. Removing it splits the tree into roughly equal halves — like binary search on trees.

---

## 107.1 Heavy-Light Decomposition — Deep Dive

### How It Works

1. **DFS 1**: Find the heavy child (largest subtree) of each node
2. **DFS 2**: Assign positions, building chains. Heavy child continues the chain; light children start new chains.
3. **Query path**: Jump up chains, querying segment tree ranges

### Dry Run

Tree:
```
       0
      / \
     1   2
    /|   |
   3  4  5
```

**DFS 1** (subtree sizes, heavy children):
```
sz[3]=1, sz[4]=1, sz[5]=1
sz[1]=3 (children 3,4), heavy[1]=3 (or 4, tie-break by choice)
sz[2]=2, heavy[2]=5
sz[0]=6, heavy[0]=1 (sz=3 > sz=2)
```

**DFS 2** (assign positions, build chains):
```
Chain 1: 0 → 1 → 3 (heavy path)
  pos[0]=0, pos[1]=1, pos[3]=2
Chain 2: 4 (light child of 1, starts new chain)
  pos[4]=3
Chain 3: 2 → 5 (heavy path)
  pos[2]=4, pos[5]=5
```

**Query path 3→5**:
```
head[3]=0, head[5]=2 → different chains
  depth[head[3]]=0, depth[head[5]]=1
  Move 5 up: query pos[2]..pos[5] = positions 4..5
  u = parent[head[5]] = parent[2] = 0
  Now head[0]=0, head[3]=0 → same chain
  Query pos[0]..pos[3] = positions 0..2
Total: sum(pos[4..5]) + sum(pos[0..2])
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class HLD {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> parent, depth, heavy, head, pos, sz;
    std::vector<int> seg;

    int dfs(int u, int p) {
        parent[u] = p; sz[u] = 1; int maxSize = 0;
        for (int v : adj[u]) {
            if (v == p) continue;
            depth[v] = depth[u] + 1;
            int subSize = dfs(v, u);
            sz[u] += subSize;
            if (subSize > maxSize) { maxSize = subSize; heavy[u] = v; }
        }
        return sz[u];
    }

    void decompose(int u, int h) {
        head[u] = h; pos[u] = timer++;
        if (heavy[u] != -1) decompose(heavy[u], h);
        for (int v : adj[u])
            if (v != parent[u] && v != heavy[u]) decompose(v, v);
    }

    void segUpdate(int idx, int val, int node, int lo, int hi) {
        if (lo == hi) { seg[node] = val; return; }
        int mid = (lo + hi) / 2;
        if (idx <= mid) segUpdate(idx, val, 2*node, lo, mid);
        else segUpdate(idx, val, 2*node+1, mid+1, hi);
        seg[node] = seg[2*node] + seg[2*node+1];
    }

    int segQuery(int ql, int qr, int node, int lo, int hi) {
        if (qr < lo || hi < ql) return 0;
        if (ql <= lo && hi <= qr) return seg[node];
        int mid = (lo + hi) / 2;
        return segQuery(ql, qr, 2*node, lo, mid) + segQuery(ql, qr, 2*node+1, mid+1, hi);
    }

public:
    HLD(int n) : n(n), adj(n), parent(n), depth(n), heavy(n,-1),
                 head(n), pos(n), sz(n), seg(4*n,0), timer(0) {}

    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }

    void build(int root) { dfs(root, -1); decompose(root, root); }

    void update(int u, int val) { segUpdate(pos[u], val, 1, 0, n-1); }

    int queryPath(int u, int v) {
        int result = 0;
        while (head[u] != head[v]) {
            if (depth[head[u]] < depth[head[v]]) std::swap(u, v);
            result += segQuery(pos[head[u]], pos[u], 1, 0, n-1);
            u = parent[head[u]];
        }
        if (depth[u] > depth[v]) std::swap(u, v);
        result += segQuery(pos[u], pos[v], 1, 0, n-1);
        return result;
    }

    int lca(int u, int v) {
        while (head[u] != head[v]) {
            if (depth[head[u]] < depth[head[v]]) std::swap(u, v);
            u = parent[head[u]];
        }
        return depth[u] < depth[v] ? u : v;
    }
};

int main() {
    HLD hld(6);
    hld.addEdge(0, 1); hld.addEdge(0, 2);
    hld.addEdge(1, 3); hld.addEdge(1, 4); hld.addEdge(2, 5);
    hld.build(0);
    for (int i = 0; i < 6; i++) hld.update(i, i + 1);

    std::cout << "Path sum 3 to 5: " << hld.queryPath(3, 5) << "\n";
    std::cout << "LCA(3, 5): " << hld.lca(3, 5) << "\n";

    return 0;
}
```

### Python Implementation

```python
class HLD:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.parent = [-1] * n
        self.depth = [0] * n
        self.heavy = [-1] * n
        self.head = [0] * n
        self.pos = [0] * n
        self.sz = [0] * n
        self.seg = [0] * (4 * n)
        self.timer = 0

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def _dfs(self, u, p):
        self.parent[u] = p
        self.sz[u] = 1
        max_size = 0
        for v in self.adj[u]:
            if v == p:
                continue
            self.depth[v] = self.depth[u] + 1
            sub_size = self._dfs(v, u)
            self.sz[u] += sub_size
            if sub_size > max_size:
                max_size = sub_size
                self.heavy[u] = v
        return self.sz[u]

    def _decompose(self, u, h):
        self.head[u] = h
        self.pos[u] = self.timer
        self.timer += 1
        if self.heavy[u] != -1:
            self._decompose(self.heavy[u], h)
        for v in self.adj[u]:
            if v != self.parent[u] and v != self.heavy[u]:
                self._decompose(v, v)

    def build(self, root):
        self._dfs(root, -1)
        self._decompose(root, root)

    def _seg_update(self, idx, val, node, lo, hi):
        if lo == hi:
            self.seg[node] = val
            return
        mid = (lo + hi) // 2
        if idx <= mid:
            self._seg_update(idx, val, 2*node, lo, mid)
        else:
            self._seg_update(idx, val, 2*node+1, mid+1, hi)
        self.seg[node] = self.seg[2*node] + self.seg[2*node+1]

    def _seg_query(self, ql, qr, node, lo, hi):
        if qr < lo or hi < ql:
            return 0
        if ql <= lo and hi <= qr:
            return self.seg[node]
        mid = (lo + hi) // 2
        return (self._seg_query(ql, qr, 2*node, lo, mid) +
                self._seg_query(ql, qr, 2*node+1, mid+1, hi))

    def update(self, u, val):
        self._seg_update(self.pos[u], val, 1, 0, self.n-1)

    def query_path(self, u, v):
        result = 0
        while self.head[u] != self.head[v]:
            if self.depth[self.head[u]] < self.depth[self.head[v]]:
                u, v = v, u
            result += self._seg_query(self.pos[self.head[u]], self.pos[u], 1, 0, self.n-1)
            u = self.parent[self.head[u]]
        if self.depth[u] > self.depth[v]:
            u, v = v, u
        result += self._seg_query(self.pos[u], self.pos[v], 1, 0, self.n-1)
        return result

# Example
hld = HLD(6)
hld.add_edge(0, 1); hld.add_edge(0, 2)
hld.add_edge(1, 3); hld.add_edge(1, 4); hld.add_edge(2, 5)
hld.build(0)
for i in range(6):
    hld.update(i, i + 1)
print(f"Path sum 3 to 5: {hld.query_path(3, 5)}")
```

### Java Implementation

```java
import java.util.*;

public class HLD {
    int n, timer;
    List<List<Integer>> adj;
    int[] parent, depth, heavy, head, pos, sz;
    int[] seg;

    public HLD(int n) {
        this.n = n; this.timer = 0;
        adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        parent = new int[n]; depth = new int[n]; heavy = new int[n];
        Arrays.fill(heavy, -1);
        head = new int[n]; pos = new int[n]; sz = new int[n];
        seg = new int[4 * n];
    }

    void addEdge(int u, int v) { adj.get(u).add(v); adj.get(v).add(u); }

    int dfs(int u, int p) {
        parent[u] = p; sz[u] = 1; int maxSize = 0;
        for (int v : adj.get(u)) {
            if (v == p) continue;
            depth[v] = depth[u] + 1;
            int subSize = dfs(v, u);
            sz[u] += subSize;
            if (subSize > maxSize) { maxSize = subSize; heavy[u] = v; }
        }
        return sz[u];
    }

    void decompose(int u, int h) {
        head[u] = h; pos[u] = timer++;
        if (heavy[u] != -1) decompose(heavy[u], h);
        for (int v : adj.get(u))
            if (v != parent[u] && v != heavy[u]) decompose(v, v);
    }

    void build(int root) { dfs(root, -1); decompose(root, root); }

    void update(int u, int val) { /* segment tree update at pos[u] */ }

    int queryPath(int u, int v) {
        int result = 0;
        while (head[u] != head[v]) {
            if (depth[head[u]] < depth[head[v]]) { int t = u; u = v; v = t; }
            result += segQuery(pos[head[u]], pos[u]);
            u = parent[head[u]];
        }
        if (depth[u] > depth[v]) { int t = u; u = v; v = t; }
        result += segQuery(pos[u], pos[v]);
        return result;
    }

    int segQuery(int l, int r) { /* standard segment tree query */ return 0; }

    public static void main(String[] args) {
        HLD hld = new HLD(6);
        hld.addEdge(0, 1); hld.addEdge(0, 2);
        hld.addEdge(1, 3); hld.addEdge(1, 4); hld.addEdge(2, 5);
        hld.build(0);
        System.out.println("Path sum 3 to 5: " + hld.queryPath(3, 5));
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Build | O(n) | O(n) |
| Path query | O(log² n) | O(1) |
| Path update | O(log² n) | O(1) |
| LCA | O(log n) | O(1) |

---

## 107.2 Centroid Decomposition — Deep Dive

### How It Works

1. Find the centroid of the current tree
2. Process all queries involving the centroid
3. Remove the centroid and recursively decompose each remaining subtree

### Finding the Centroid

A centroid is a node whose removal leaves all subtrees with size ≤ n/2. It always exists.

### Dry Run

```
       0
      / \
     1   2
    /|   |
   3  4  5
      |
      6
```

Subtree sizes: sz[3]=1, sz[6]=1, sz[4]=2, sz[1]=4, sz[5]=1, sz[2]=2, sz[0]=7

Centroid of whole tree (size 7): check each node's max subtree after removal:
- Node 0: max child subtree = 4 (too big, 4 > 7/2=3.5)
- Node 1: max child subtree = max(2, 1, 3) = 3 ≤ 3.5 ✓ → centroid!

After removing 1: subtrees {0,2,5}, {3}, {4,6}
Recurse on each.

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

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

        // Process centroid (example: print it)
        std::cout << "Centroid: " << centroid << "\n";

        // Recurse on subtrees
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
    cd.addEdge(1, 4); cd.addEdge(2, 5); cd.addEdge(4, 6);
    cd.build();
    return 0;
}
```

### Application: Count Paths of Length K

```cpp
// For each centroid, count pairs (u,v) where dist(u,v) = k
// and the path passes through the centroid.
// 1. For each subtree of centroid, compute distances
// 2. Use a global counter array to combine subtrees
// 3. O(n log n) total
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
        self.adj[u].append(v)
        self.adj[v].append(u)

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

    def build(self):
        self._decompose(0)

# Example
cd = CentroidDecomp(7)
cd.add_edge(0, 1); cd.add_edge(0, 2); cd.add_edge(1, 3)
cd.add_edge(1, 4); cd.add_edge(2, 5); cd.add_edge(4, 6)
cd.build()
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Build centroid tree | O(n log n) | O(n) |
| Each node processed | O(log n) levels | — |
| Path counting (per centroid) | O(n) | O(n) |

---

## Exercises

1. **Path max query**: Modify HLD to support max queries on paths instead of sum queries.

2. **Path update**: Extend HLD to support range updates on paths (add value to all nodes on path u→v). Use lazy propagation on the segment tree.

3. **Count pairs at distance K**: Use centroid decomposition to count the number of pairs of nodes at exactly distance k in a tree.

4. **HLD vs Euler tour**: For the problem "sum on path from u to v", compare HLD with Euler tour + LCA approach. When is each better?

5. **Centroid for closest pair**: Use centroid decomposition to find the minimum distance between any two marked nodes in a tree.

---

## Interview Questions

1. **Q: Why does HLD decompose into O(log n) chains?**
   A: Each light edge reduces the subtree size by at least half (the heavy child has the largest subtree). So following parent pointers through light edges at most O(log n) times before reaching the root.

2. **Q: What's the difference between HLD and Euler tour for path queries?**
   A: Euler tour + LCA works for subtree queries (O(log n)) but path queries require more complex handling. HLD directly supports path queries in O(log²n). HLD is more versatile for path operations.

3. **Q: Why does a centroid always exist?**
   A: Start at any node. If it's not a centroid, move to the neighbor with the largest subtree (which has size > n/2). This must converge because the "bad" subtree shrinks. A tree always has at most 2 centroids.

4. **Q: How does centroid decomposition help with path counting?**
   A: At each centroid, all paths through it can be counted by combining distance information from different subtrees. Since each node appears in O(log n) centroids' subtrees, total work is O(n log n).

---

## Cross-References

- [Chapter 18: Segment Trees](ch18-segment-tree.md) — HLD uses segment trees for chain queries
- Chapter 15: LCA — HLD provides an LCA implementation
- [Chapter 106: Euler Tour and Tree Flattening](ch106-euler-tour-tree-flattening.md) — Alternative tree decomposition
- [Chapter 108: DSU on Tree and Rerooting](ch108-dsu-on-tree-rerooting.md) — Other advanced tree techniques

---

## Summary

| Technique | Query Time | Build | Best For |
|---|---|---|---|
| HLD | O(log² n) | O(n) | Path queries, updates |
| Centroid Decomp | O(n log n) total | O(n) | Path counting, D&C |
| Euler Tour + ST | O(log n) subtree | O(n) | Subtree queries |
