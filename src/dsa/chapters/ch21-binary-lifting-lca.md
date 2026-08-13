# Chapter 21: Binary Lifting and Lowest Common Ancestor

## 21.1 Binary Lifting

### The Idea

**Binary lifting** is a technique that preprocesses a tree (or any functional graph) so that we can jump `2^k` steps from any node in O(1) time. By representing any number as a sum of powers of 2, we can jump any distance in O(log n) steps.

This is the same principle behind binary search and sparse tables: decompose a quantity into powers of 2.

### Why It Matters

Binary lifting enables:
- **K-th ancestor**: Find the k-th ancestor of any node in O(log n)
- **Lowest Common Ancestor (LCA)**: Find the LCA of any two nodes in O(log n)
- **Distance between nodes**: Compute the distance between any two nodes in O(log n)
- **Path queries**: Answer queries about paths in trees
- **Functional graph problems**: Navigate successor/predecessor chains

### Preprocessing with DP on Trees

Define `up[v][k]` = the 2^k-th ancestor of node `v`.

**Recurrence:**
```
up[v][0] = parent(v)                           (2^0 = 1st ancestor = parent)
up[v][k] = up[up[v][k-1]][k-1]                 (2^k-th ancestor = 2^(k-1)-th ancestor of 2^(k-1)-th ancestor)
```

**Intuition**: To find the 8th ancestor, first find the 4th ancestor, then from there find another 4th ancestor. This is just like binary representation: 8 = 4 + 4, or in binary: 1000.

### Visual Diagram

```
Tree:           Binary lifting table (up[v][k]):
    0                k=0  k=1  k=2
   /|\               0:   -    -    -    (root has no ancestors)
  1 2 3              1:   0    -    -
 /| \                2:   0    -    -
4 5  6               3:   0    -    -
   |                 4:   1    0    -
   7                 5:   1    0    -
                     6:   2    0    -
                     7:   5    1    0

To find the 3rd ancestor of node 7:
  3 = 2 + 1 = 2^1 + 2^0
  Step 1: up[7][1] = 1  (jump 2 from 7 → node 1)
  Step 2: up[1][0] = 0  (jump 1 from 1 → node 0)
  Answer: 0
```

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>

class TreeAncestor {
private:
    int n, maxLog;
    std::vector<int> depth;
    std::vector<std::vector<int>> up;

    // BFS to compute depths and immediate parents
    void bfs(int root, const std::vector<std::vector<int>>& adj) {
        std::vector<bool> visited(n, false);
        std::queue<int> q;

        depth[root] = 0;
        up[root][0] = -1;  // Root has no parent
        visited[root] = true;
        q.push(root);

        while (!q.empty()) {
            int u = q.front();
            q.pop();

            for (int v : adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    depth[v] = depth[u] + 1;
                    up[v][0] = u;  // Parent of v is u
                    q.push(v);
                }
            }
        }
    }

public:
    TreeAncestor(int numNodes, int root, const std::vector<std::vector<int>>& adj)
        : n(numNodes), depth(n) {
        maxLog = static_cast<int>(std::log2(n)) + 1;
        up.assign(n, std::vector<int>(maxLog, -1));

        // Step 1: BFS to get depths and parents
        bfs(root, adj);

        // Step 2: Fill the binary lifting table
        // Process levels from 1 to maxLog-1
        for (int k = 1; k < maxLog; ++k) {
            for (int v = 0; v < n; ++v) {
                if (up[v][k - 1] != -1) {
                    up[v][k] = up[up[v][k - 1]][k - 1];
                }
            }
        }
    }

    // Get the k-th ancestor of node v — O(log n)
    int kthAncestor(int v, int k) const {
        for (int i = 0; i < maxLog; ++i) {
            if (k & (1 << i)) {
                v = up[v][i];
                if (v == -1) return -1;  // No such ancestor
            }
        }
        return v;
    }

    // Find LCA of u and v — O(log n)
    int lca(int u, int v) const {
        // Step 1: Make sure u is deeper
        if (depth[u] < depth[v]) std::swap(u, v);

        // Step 2: Lift u to the same depth as v
        int diff = depth[u] - depth[v];
        u = kthAncestor(u, diff);

        if (u == v) return u;

        // Step 3: Binary search for the LCA
        // Lift both u and v simultaneously, going from large jumps to small
        for (int k = maxLog - 1; k >= 0; --k) {
            if (up[u][k] != up[v][k]) {
                u = up[u][k];
                v = up[v][k];
            }
        }

        // Now u and v are direct children of the LCA
        return up[u][0];
    }

    // Distance between u and v — O(log n)
    int distance(int u, int v) const {
        return depth[u] + depth[v] - 2 * depth[lca(u, v)];
    }

    int getDepth(int v) const { return depth[v]; }
};

int main() {
    // Build tree:
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    //      |
    //      6

    int n = 7;
    std::vector<std::vector<int>> adj(n);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };

    addEdge(0, 1);
    addEdge(0, 2);
    addEdge(1, 3);
    addEdge(1, 4);
    addEdge(2, 5);
    addEdge(4, 6);

    TreeAncestor tree(n, 0, adj);

    // LCA queries
    std::cout << "LCA(3, 6): " << tree.lca(3, 6) << "\n";  // 1
    std::cout << "LCA(3, 5): " << tree.lca(3, 5) << "\n";  // 0
    std::cout << "LCA(4, 6): " << tree.lca(4, 6) << "\n";  // 4
    std::cout << "LCA(3, 4): " << tree.lca(3, 4) << "\n";  // 1

    // Distance queries
    std::cout << "Distance(3, 6): " << tree.distance(3, 6) << "\n";  // 3
    std::cout << "Distance(3, 5): " << tree.distance(3, 5) << "\n";  // 4

    // K-th ancestor
    std::cout << "1st ancestor of 6: " << tree.kthAncestor(6, 1) << "\n";  // 4
    std::cout << "2nd ancestor of 6: " << tree.kthAncestor(6, 2) << "\n";  // 1
    std::cout << "3rd ancestor of 6: " << tree.kthAncestor(6, 3) << "\n";  // 0

    return 0;
}
```

---

## 21.2 Lowest Common Ancestor

### What is the LCA?

The **Lowest Common Ancestor (LCA)** of two nodes `u` and `v` in a tree is the deepest node that is an ancestor of both `u` and `v`.

```
        0
       / \
      1   2
     / \   \
    3   4   5
       / \
      6   7

LCA(3, 5) = 0    (common ancestors: 0; deepest: 0)
LCA(3, 4) = 1    (common ancestors: 0, 1; deepest: 1)
LCA(6, 7) = 4    (common ancestors: 0, 1, 4; deepest: 4)
LCA(6, 3) = 1    (common ancestors: 0, 1; deepest: 1)
```

### Why LCA Matters

LCA is a fundamental building block for many tree problems:

1. **Distance between nodes**: `dist(u, v) = depth[u] + depth[v] - 2 * depth[LCA(u, v)]`
2. **Path queries**: The path from u to v goes through LCA(u, v)
3. **Ancestry check**: u is an ancestor of v iff `LCA(u, v) = u`
4. **Tree diameter**: Can be computed using LCA
5. **Path aggregates**: Sum/min/max along a path can be decomposed using LCA

### Naive Approach

Walk up from both nodes until they meet:

```cpp
int lcaNaive(int u, int v, const std::vector<int>& parent, const std::vector<int>& depth) {
    // Bring both nodes to the same depth
    while (depth[u] > depth[v]) u = parent[u];
    while (depth[v] > depth[u]) v = parent[v];

    // Walk up together until they meet
    while (u != v) {
        u = parent[u];
        v = parent[v];
    }
    return u;
}
```

**Time complexity**: O(n) per query in the worst case (linear tree). Too slow for many queries.

---

## 21.3 LCA with Binary Lifting

The binary lifting approach achieves O(log n) per query with O(n log n) preprocessing.

### Algorithm

1. **Preprocess**: Build the `up[v][k]` table using DFS/BFS
2. **Query**:
   - Bring both nodes to the same depth using binary lifting
   - Binary search for the LCA by trying increasingly smaller jumps
   - The LCA is the parent of the final positions

### Step-by-Step Dry Run

```
Tree:
        0
       / \
      1   2
     / \   \
    3   4   5
       / \
      6   7

Query: LCA(6, 5)

Binary lifting table (up[v][k]):
v\k    0    1    2
0:    -1   -1   -1
1:     0   -1   -1
2:     0   -1   -1
3:     1    0   -1
4:     1    0   -1
5:     2    0   -1
6:     4    1    0
7:     4    1    0

Depth: [0, 1, 1, 2, 2, 2, 3, 3]

Step 1: Make u deeper. depth[6]=3, depth[5]=2, so u=6, v=5.
        diff = 3 - 2 = 1. Lift u by 1: u = kthAncestor(6, 1) = 4.
        Now depth[u] = depth[v] = 2.

Step 2: u=4, v=5. u ≠ v. Binary search from k=maxLog-1 down to 0.
        k=2: up[4][2] = -1, up[5][2] = -1. Both -1, skip.
        k=1: up[4][1] = 0, up[5][1] = 0. Both 0 (equal), skip.
        k=0: up[4][0] = 1, up[5][0] = 2. Different! Lift both:
             u = up[4][0] = 1, v = up[5][0] = 2.

Step 3: u=1, v=2. They are now direct children of the LCA.
        Return up[1][0] = 0.

LCA(6, 5) = 0 ✓
```

### Why the Binary Search Works

After bringing u and v to the same depth, if they're not the same node, we want to find the **highest** ancestors of u and v that are **different**. The LCA is their parent.

We try jumps from large to small (k = maxLog-1 down to 0):
- If `up[u][k] ≠ up[v][k]`, both nodes can jump up by 2^k (they're still in different subtrees)
- If `up[u][k] = up[v][k]`, jumping would overshoot the LCA, so we don't jump

After all jumps, u and v are direct children of the LCA.

---

## 21.4 LCA with Euler Tour + Sparse Table

This approach achieves O(1) per query with O(n log n) preprocessing, using a sparse table instead of binary lifting.

### The Euler Tour Technique

An **Euler tour** of a tree visits every edge exactly twice (once in each direction), producing a sequence of node visits. The key property:

**The LCA of u and v is the node with the minimum depth among all nodes visited between the first occurrences of u and v in the Euler tour.**

### Algorithm

1. Compute the Euler tour (list of nodes as they are visited during DFS)
2. Record the first occurrence of each node in the Euler tour
3. Build a sparse table on the depths of nodes in the Euler tour
4. To find LCA(u, v): query the minimum-depth node between `first[u]` and `first[v]` in the Euler tour

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <climits>

class LCAEulerSparseTable {
private:
    std::vector<int> euler;      // Euler tour (node indices)
    std::vector<int> depth;      // Depth of each node in the Euler tour
    std::vector<int> first;      // First occurrence of each node in Euler tour
    std::vector<std::vector<int>> st;  // Sparse table on depths
    std::vector<int> logTable;
    int n, maxLog;

    void dfs(int node, int parent, int d, const std::vector<std::vector<int>>& adj) {
        first[node] = static_cast<int>(euler.size());
        euler.push_back(node);
        depth.push_back(d);

        for (int child : adj[node]) {
            if (child != parent) {
                dfs(child, node, d + 1, adj);
                euler.push_back(node);
                depth.push_back(d);
            }
        }
    }

    void buildSparseTable() {
        int m = static_cast<int>(depth.size());
        maxLog = m > 0 ? static_cast<int>(std::log2(m)) + 1 : 0;

        logTable.resize(m + 1);
        logTable[1] = 0;
        for (int i = 2; i <= m; ++i) logTable[i] = logTable[i / 2] + 1;

        st.assign(m, std::vector<int>(maxLog));
        for (int i = 0; i < m; ++i) {
            // Store the INDEX in the Euler tour, not the depth
            st[i][0] = i;
        }

        for (int j = 1; j < maxLog; ++j) {
            for (int i = 0; i + (1 << j) <= m; ++i) {
                int left = st[i][j - 1];
                int right = st[i + (1 << (j - 1))][j - 1];
                // Compare by depth: keep the one with smaller depth
                st[i][j] = (depth[left] <= depth[right]) ? left : right;
            }
        }
    }

public:
    LCAEulerSparseTable(int numNodes, int root, const std::vector<std::vector<int>>& adj)
        : n(numNodes), first(numNodes) {
        // Step 1: DFS to compute Euler tour
        dfs(root, -1, 0, adj);

        // Step 2: Build sparse table on Euler tour depths
        buildSparseTable();
    }

    // LCA of u and v — O(1)
    int lca(int u, int v) const {
        int l = first[u];
        int r = first[v];
        if (l > r) std::swap(l, r);

        // Query minimum depth index in [l, r]
        int len = r - l + 1;
        int k = logTable[len];

        int left = st[l][k];
        int right = st[r - (1 << k) + 1][k];

        return (depth[left] <= depth[right]) ? euler[left] : euler[right];
    }

    // Distance between u and v
    int distance(int u, int v) const {
        int l = first[u];
        int r = first[v];
        if (l > r) std::swap(l, r);

        int len = r - l + 1;
        int k = logTable[len];

        int left = st[l][k];
        int right = st[r - (1 << k) + 1][k];
        int lcaDepth = std::min(depth[left], depth[right]);

        return depth[first[u]] + depth[first[v]] - 2 * lcaDepth;
    }
};

int main() {
    // Tree:
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    //      |
    //      6

    int n = 7;
    std::vector<std::vector<int>> adj(n);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };

    addEdge(0, 1);
    addEdge(0, 2);
    addEdge(1, 3);
    addEdge(1, 4);
    addEdge(2, 5);
    addEdge(4, 6);

    LCAEulerSparseTable lca(n, 0, adj);

    std::cout << "LCA(3, 6): " << lca.lca(3, 6) << "\n";  // 1
    std::cout << "LCA(3, 5): " << lca.lca(3, 5) << "\n";  // 0
    std::cout << "LCA(4, 6): " << lca.lca(4, 6) << "\n";  // 4
    std::cout << "LCA(6, 5): " << lca.lca(6, 5) << "\n";  // 0

    std::cout << "Distance(3, 6): " << lca.distance(3, 6) << "\n";  // 3
    std::cout << "Distance(6, 5): " << lca.distance(6, 5) << "\n";  // 4

    return 0;
}
```

### Dry Run: Euler Tour + Sparse Table

```
Tree:
        0
       / \
      1   2
     / \   \
    3   4   5
       / \
      6   7

DFS from root 0:

Visit 0 (depth 0)
  Visit 1 (depth 1)
    Visit 3 (depth 2) → backtrack to 1
    Visit 4 (depth 2)
      Visit 6 (depth 3) → backtrack to 4
      Visit 7 (depth 3) → backtrack to 4
    → backtrack to 1
  → backtrack to 0
  Visit 2 (depth 1)
    Visit 5 (depth 2) → backtrack to 2
  → backtrack to 0

Euler tour:    [0, 1, 3, 1, 4, 6, 4, 7, 4, 1, 0, 2, 5, 2, 0]
Depth:         [0, 1, 2, 1, 2, 3, 2, 3, 2, 1, 0, 1, 2, 1, 0]
First occur:   {0:0, 1:1, 2:11, 3:2, 4:4, 5:12, 6:5, 7:7}

Query: LCA(6, 5)
  first[6] = 5, first[5] = 12
  l = 5, r = 12

  Euler tour segment [5, 12]:
  Indices:  5  6  7  8  9  10 11 12
  Nodes:    6  4  7  4  1   0  2  5
  Depths:   3  2  3  2  1   0  1  2

  Minimum depth is 0 at index 10, which corresponds to node 0.
  LCA(6, 5) = 0 ✓

Query: LCA(3, 6)
  first[3] = 2, first[6] = 5
  l = 2, r = 5

  Euler tour segment [2, 5]:
  Indices:  2  3  4  5
  Nodes:    3  1  4  6
  Depths:   2  1  2  3

  Minimum depth is 1 at index 3, which corresponds to node 1.
  LCA(3, 6) = 1 ✓
```

### Binary Lifting vs Euler Tour + Sparse Table

| Property | Binary Lifting | Euler Tour + Sparse Table |
|----------|---------------|--------------------------|
| Preprocessing | O(n log n) | O(n log n) |
| Query time | O(log n) | O(1) |
| Space | O(n log n) | O(n log n) |
| Code complexity | Moderate | Moderate |
| Supports k-th ancestor | Yes (directly) | No (needs modification) |
| Supports path queries | Yes | With additional structure |
| Practical speed | Fast | Faster for many queries |

**Use binary lifting when**: You also need k-th ancestor queries or path queries. It's more versatile.

**Use Euler tour + sparse table when**: You need maximum throughput for LCA queries (O(1) per query).

---

## 21.5 Applications

### Application 1: Distance Between Nodes

The distance between two nodes in a tree is:
```
dist(u, v) = depth[u] + depth[v] - 2 * depth[LCA(u, v)]
```

This works because the path from u to v goes: u → ... → LCA → ... → v. The distance is the sum of distances from u to LCA and from v to LCA.

```cpp
// Already shown in the TreeAncestor class:
int distance(int u, int v) const {
    return depth[u] + depth[v] - 2 * depth[lca(u, v)];
}
```

### Application 2: K-th Ancestor

Find the k-th ancestor of a node (the node that is k levels above it).

```cpp
// Already shown in the TreeAncestor class:
int kthAncestor(int v, int k) const {
    for (int i = 0; i < maxLog; ++i) {
        if (k & (1 << i)) {
            v = up[v][i];
            if (v == -1) return -1;
        }
    }
    return v;
}
```

**How it works**: Express k in binary. For each set bit at position i, jump 2^i levels. For example, k = 13 = 1101₂ = 8 + 4 + 1, so jump 8, then 4, then 1.

### Application 3: K-th Node on Path

Find the k-th node on the path from u to v (0-indexed from u).

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <queue>
#include <algorithm>

class TreePath {
private:
    int n, maxLog;
    std::vector<int> depth;
    std::vector<std::vector<int>> up;

    void bfs(int root, const std::vector<std::vector<int>>& adj) {
        std::vector<bool> visited(n, false);
        std::queue<int> q;
        depth[root] = 0;
        up[root][0] = -1;
        visited[root] = true;
        q.push(root);

        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    depth[v] = depth[u] + 1;
                    up[v][0] = u;
                    q.push(v);
                }
            }
        }
    }

public:
    TreePath(int numNodes, int root, const std::vector<std::vector<int>>& adj)
        : n(numNodes), depth(n) {
        maxLog = static_cast<int>(std::log2(n)) + 1;
        up.assign(n, std::vector<int>(maxLog, -1));
        bfs(root, adj);

        for (int k = 1; k < maxLog; ++k) {
            for (int v = 0; v < n; ++v) {
                if (up[v][k - 1] != -1) {
                    up[v][k] = up[up[v][k - 1]][k - 1];
                }
            }
        }
    }

    int kthAncestor(int v, int k) const {
        for (int i = 0; i < maxLog; ++i) {
            if (k & (1 << i)) {
                v = up[v][i];
                if (v == -1) return -1;
            }
        }
        return v;
    }

    int lca(int u, int v) const {
        if (depth[u] < depth[v]) std::swap(u, v);
        int diff = depth[u] - depth[v];
        u = kthAncestor(u, diff);
        if (u == v) return u;

        for (int k = maxLog - 1; k >= 0; --k) {
            if (up[u][k] != up[v][k]) {
                u = up[u][k];
                v = up[v][k];
            }
        }
        return up[u][0];
    }

    // Find the k-th node on the path from u to v (0-indexed from u)
    int kthNodeOnPath(int u, int v, int k) const {
        int w = lca(u, v);
        int distUW = depth[u] - depth[w];
        int distUV = depth[u] + depth[v] - 2 * depth[w];

        if (k > distUV) return -1;  // k is out of range

        if (k <= distUW) {
            // The k-th node is on the u → LCA segment
            return kthAncestor(u, k);
        } else {
            // The k-th node is on the LCA → v segment
            int distFromV = distUV - k;
            return kthAncestor(v, distFromV);
        }
    }

    int distance(int u, int v) const {
        return depth[u] + depth[v] - 2 * depth[lca(u, v)];
    }
};

int main() {
    // Tree:
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    //      |
    //      6

    int n = 7;
    std::vector<std::vector<int>> adj(n);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };
    addEdge(0, 1);
    addEdge(0, 2);
    addEdge(1, 3);
    addEdge(1, 4);
    addEdge(2, 5);
    addEdge(4, 6);

    TreePath tree(n, 0, adj);

    // Path from 3 to 5: 3 → 1 → 0 → 2 → 5
    std::cout << "Path 3 to 5: ";
    int dist = tree.distance(3, 5);
    for (int i = 0; i <= dist; ++i) {
        std::cout << tree.kthNodeOnPath(3, 5, i) << " ";
    }
    std::cout << "\n";  // 3 1 0 2 5

    // K-th node on path
    std::cout << "2nd node on path 3→5: " << tree.kthNodeOnPath(3, 5, 2) << "\n";  // 0

    return 0;
}
```

### Application 4: Path Queries with Binary Lifting

We can augment the binary lifting table to store aggregate information along the path.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <queue>
#include <algorithm>
#include <climits>

class PathMinQuery {
private:
    int n, maxLog;
    std::vector<int> depth;
    std::vector<std::vector<int>> up;
    std::vector<std::vector<int>> pathMin;  // pathMin[v][k] = min on path from v to 2^k-th ancestor

    void bfs(int root, const std::vector<std::vector<int>>& adj,
             const std::vector<int>& nodeWeight) {
        std::vector<bool> visited(n, false);
        std::queue<int> q;
        depth[root] = 0;
        up[root][0] = -1;
        pathMin[root][0] = INT_MAX;
        visited[root] = true;
        q.push(root);

        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    depth[v] = depth[u] + 1;
                    up[v][0] = u;
                    pathMin[v][0] = nodeWeight[u];
                    q.push(v);
                }
            }
        }
    }

public:
    PathMinQuery(int numNodes, int root, const std::vector<std::vector<int>>& adj,
                 const std::vector<int>& nodeWeight)
        : n(numNodes), depth(n) {
        maxLog = static_cast<int>(std::log2(n)) + 1;
        up.assign(n, std::vector<int>(maxLog, -1));
        pathMin.assign(n, std::vector<int>(maxLog, INT_MAX));

        bfs(root, adj, nodeWeight);

        for (int k = 1; k < maxLog; ++k) {
            for (int v = 0; v < n; ++v) {
                if (up[v][k - 1] != -1) {
                    up[v][k] = up[up[v][k - 1]][k - 1];
                    pathMin[v][k] = std::min(pathMin[v][k - 1],
                                             pathMin[up[v][k - 1]][k - 1]);
                }
            }
        }
    }

    int kthAncestor(int v, int k) const {
        for (int i = 0; i < maxLog; ++i) {
            if (k & (1 << i)) {
                v = up[v][i];
                if (v == -1) return -1;
            }
        }
        return v;
    }

    int lca(int u, int v) const {
        if (depth[u] < depth[v]) std::swap(u, v);
        int diff = depth[u] - depth[v];
        u = kthAncestor(u, diff);
        if (u == v) return u;

        for (int k = maxLog - 1; k >= 0; --k) {
            if (up[u][k] != up[v][k]) {
                u = up[u][k];
                v = up[v][k];
            }
        }
        return up[u][0];
    }

    // Minimum weight on the path from u up to (but not including) its k-th ancestor
    int minOnPathUp(int u, int k) const {
        int result = INT_MAX;
        for (int i = 0; i < maxLog; ++i) {
            if (k & (1 << i)) {
                result = std::min(result, pathMin[u][i]);
                u = up[u][i];
            }
        }
        return result;
    }

    // Minimum weight on the path from u to v (including both endpoints)
    int minOnPath(int u, int v, const std::vector<int>& nodeWeight) const {
        int w = lca(u, v);
        int result = nodeWeight[w];  // Include LCA

        // Min on path from u to LCA (not including LCA)
        int distU = depth[u] - depth[w];
        if (distU > 0) {
            result = std::min(result, minOnPathUp(u, distU));
        }

        // Min on path from v to LCA (not including LCA)
        int distV = depth[v] - depth[w];
        if (distV > 0) {
            result = std::min(result, minOnPathUp(v, distV));
        }

        return result;
    }
};

int main() {
    // Tree with weights:
    //       0 (weight 5)
    //      / \
    //     1   2 (weights 3, 8)
    //    / \   \
    //   3   4   5 (weights 1, 7, 2)

    int n = 6;
    std::vector<std::vector<int>> adj(n);
    std::vector<int> weight = {5, 3, 8, 1, 7, 2};

    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };
    addEdge(0, 1);
    addEdge(0, 2);
    addEdge(1, 3);
    addEdge(1, 4);
    addEdge(2, 5);

    PathMinQuery tree(n, 0, adj, weight);

    std::cout << "Min on path 3→5: " << tree.minOnPath(3, 5, weight) << "\n";  // 1
    std::cout << "Min on path 4→5: " << tree.minOnPath(4, 5, weight) << "\n";  // 3
    std::cout << "Min on path 3→4: " << tree.minOnPath(3, 4, weight) << "\n";  // 1

    return 0;
}
```

### Application 5: Finding the Diameter of a Tree

The diameter of a tree is the longest path between any two nodes. It can be computed efficiently using LCA.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <queue>
#include <algorithm>

class TreeDiameter {
private:
    int n, maxLog;
    std::vector<int> depth;
    std::vector<std::vector<int>> up;

    void bfs(int root, const std::vector<std::vector<int>>& adj) {
        std::vector<bool> visited(n, false);
        std::queue<int> q;
        depth[root] = 0;
        up[root][0] = -1;
        visited[root] = true;
        q.push(root);

        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    depth[v] = depth[u] + 1;
                    up[v][0] = u;
                    q.push(v);
                }
            }
        }
    }

public:
    TreeDiameter(int numNodes, int root, const std::vector<std::vector<int>>& adj)
        : n(numNodes), depth(n) {
        maxLog = static_cast<int>(std::log2(n)) + 1;
        up.assign(n, std::vector<int>(maxLog, -1));
        bfs(root, adj);

        for (int k = 1; k < maxLog; ++k) {
            for (int v = 0; v < n; ++v) {
                if (up[v][k - 1] != -1) {
                    up[v][k] = up[up[v][k - 1]][k - 1];
                }
            }
        }
    }

    int kthAncestor(int v, int k) const {
        for (int i = 0; i < maxLog; ++i) {
            if (k & (1 << i)) {
                v = up[v][i];
                if (v == -1) return -1;
            }
        }
        return v;
    }

    int lca(int u, int v) const {
        if (depth[u] < depth[v]) std::swap(u, v);
        int diff = depth[u] - depth[v];
        u = kthAncestor(u, diff);
        if (u == v) return u;

        for (int k = maxLog - 1; k >= 0; --k) {
            if (up[u][k] != up[v][k]) {
                u = up[u][k];
                v = up[v][k];
            }
        }
        return up[u][0];
    }

    int distance(int u, int v) const {
        return depth[u] + depth[v] - 2 * depth[lca(u, v)];
    }

    // Find the diameter using BFS + LCA
    // More efficient: two BFS passes (but LCA approach generalizes better)
    std::pair<int, std::pair<int, int>> diameter() const {
        // Find the farthest node from root (node a)
        int a = 0;
        for (int i = 1; i < n; ++i) {
            if (depth[i] > depth[a]) a = i;
        }

        // For each node, compute distance to a
        // The farthest from a is one end of the diameter
        int b = 0;
        int maxDist = 0;
        for (int i = 0; i < n; ++i) {
            int d = distance(a, i);
            if (d > maxDist) {
                maxDist = d;
                b = i;
            }
        }

        return {maxDist, {a, b}};
    }
};

int main() {
    // Tree:
    //     0
    //    / \
    //   1   2
    //  /|   |\
    // 3 4   5 6
    //        |
    //        7

    int n = 8;
    std::vector<std::vector<int>> adj(n);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };
    addEdge(0, 1);
    addEdge(0, 2);
    addEdge(1, 3);
    addEdge(1, 4);
    addEdge(2, 5);
    addEdge(2, 6);
    addEdge(5, 7);

    TreeDiameter tree(n, 0, adj);

    auto [diam, endpoints] = tree.diameter();
    std::cout << "Diameter: " << diam << "\n";
    std::cout << "Endpoints: " << endpoints.first << " and " << endpoints.second << "\n";
    // Diameter: 5 (path: 3 → 1 → 0 → 2 → 5 → 7 or 4 → 1 → 0 → 2 → 5 → 7)

    return 0;
}
```

---

## Interview Tips

1. **Recognize LCA problems by keywords**: "common ancestor", "distance in tree", "path between nodes", "tree queries", "k-th ancestor".

2. **Binary lifting is the standard approach**: It's versatile (supports LCA, k-th ancestor, path queries) and easy to implement. Start with this in interviews.

3. **The LCA algorithm has 3 steps**:
   - Bring both nodes to the same depth
   - If they're the same, return it
   - Binary search for the highest different ancestors, return their parent

4. **Distance formula**: `dist(u, v) = depth[u] + depth[v] - 2 * depth[LCA(u, v)]`. Memorize this.

5. **Path decomposition**: Any path in a tree can be decomposed as `u → LCA(u,v) → v`. Use this to answer path queries.

6. **Euler tour + sparse table for O(1) LCA**: Use this when you have many LCA queries and the tree doesn't change. But binary lifting is usually sufficient and more flexible.

7. **Root choice doesn't matter**: LCA is well-defined regardless of which node is the root. The answer may differ if you change the root, but the algorithm works for any root.

## Common Mistakes

1. **Forgetting to handle the root**: The root has no parent (up[root][0] = -1). Make sure your code handles this.

2. **Off-by-one in depth lifting**: When lifting u to the same depth as v, use `depth[u] - depth[v]`, not `depth[v] - depth[u]`.

3. **Not checking `up[u][k] != -1`**: When the ancestor doesn't exist (above the root), `up[u][k]` is -1. Accessing -1 as an index causes undefined behavior.

4. **Wrong LCA when u = v**: If u and v are the same node, the LCA is that node. Handle this case before the binary search.

5. **Using the wrong root**: The LCA depends on the root. Make sure you're consistent about which node is the root.

6. **Not considering the node's own value in path queries**: When computing min/max on a path, remember to include the LCA node itself.

---

## Practice Problems

### Problem 1: Lowest Common Ancestor (LeetCode 236)
**Difficulty**: Medium
**Hint**: Classic LCA problem. Use binary lifting for the general case, or the recursive approach for a simpler solution.

### Problem 2: K-th Ancestor of a Tree Node (LeetCode 1483)
**Difficulty**: Hard
**Hint**: Precompute the binary lifting table. For `getKthAncestor(node, k)`, decompose k into powers of 2 and jump.

### Problem 3: Distance in Tree (Codeforces 208E)
**Difficulty**: Medium
**Hint**: Use LCA to compute distances. For each query (v, p), find the p-th ancestor and count nodes at depth `depth[v] + p`.

### Problem 4: Minimize the Maximum Edge Weight (LeetCode 2876 variant)
**Difficulty**: Hard
**Hint**: Use binary lifting to answer queries about paths in trees.

### Problem 5: Count Nodes in Subtree with Specific Property
**Difficulty**: Medium
**Hint**: Use Euler tour to convert subtree queries to range queries, then use a Fenwick tree or segment tree.

### Problem 6: Tree Distances II (CSES)
**Difficulty**: Medium
**Hint**: For each node, compute the sum of distances to all other nodes. Use the relation: `sum[v] = sum[parent[v]] + n - 2 * size[v]`.

### Problem 7: Company Queries II (CSES)
**Difficulty**: Medium
**Hint**: Direct LCA application. Implement binary lifting and answer multiple LCA queries.

### Problem 8: Path Queries with Updates (Advanced)
**Difficulty**: Hard
**Hint**: Decompose paths using LCA, then use heavy-light decomposition (HLD) with a segment tree for efficient path updates and queries.

---

*This concludes the advanced data structures section. These chapters cover the most important data structures for competitive programming and technical interviews. Master them, and you'll be well-equipped to tackle a wide range of algorithmic challenges.*
