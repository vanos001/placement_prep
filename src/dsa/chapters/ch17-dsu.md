# Chapter 17: Disjoint Set Union (Union-Find)

## 17.1 The Union-Find Problem

The **Disjoint Set Union (DSU)** data structure, also known as **Union-Find**, tracks a partition of a set into disjoint (non-overlapping) subsets. It provides near-constant-time operations to:

1. **Find**: Determine which subset a particular element belongs to
2. **Union**: Merge two subsets into one

This is one of the most elegant data structures in computer science. Despite its simplicity, it achieves an almost O(1) amortized time per operation through clever optimizations.

### The Problem

Imagine you have n elements, initially each in its own group. You need to:
- Repeatedly merge groups together
- Query whether two elements are in the same group
- Count the number of distinct groups

This arises naturally in:
- **Kruskal's minimum spanning tree algorithm**: Check if adding an edge creates a cycle
- **Connected components**: Track which nodes are reachable from each other
- **Equivalence relations**: Group equivalent items (e.g., synonym resolution)
- **Percolation**: Determine if a system percolates from top to bottom

### Equivalence Relations

An equivalence relation satisfies three properties:
- **Reflexive**: a ~ a
- **Symmetric**: if a ~ b then b ~ a
- **Transitive**: if a ~ b and b ~ c then a ~ c

DSU naturally maintains equivalence classes. Each set in the DSU is one equivalence class.

---

## 17.2 Basic Implementation

### Approach 1: Quick-Find

The simplest approach: maintain an array where `id[i]` represents the set that element `i` belongs to.

```cpp
#include <iostream>
#include <vector>

class QuickFind {
private:
    std::vector<int> id_;

public:
    explicit QuickFind(int n) : id_(n) {
        // Initially, each element is in its own set
        for (int i = 0; i < n; ++i) {
            id_[i] = i;
        }
    }

    // Find: O(1) — just return the id
    int find(int p) const {
        return id_[p];
    }

    // Union: O(n) — must update ALL elements in one set
    void unite(int p, int q) {
        int pid = id_[p];
        int qid = id_[q];
        if (pid == qid) return;

        // Replace all instances of pid with qid
        for (int i = 0; i < static_cast<int>(id_.size()); ++i) {
            if (id_[i] == pid) {
                id_[i] = qid;
            }
        }
    }

    bool connected(int p, int q) const {
        return find(p) == find(q);
    }
};

int main() {
    QuickFind uf(10);
    uf.unite(4, 3);
    uf.unite(3, 8);
    uf.unite(6, 5);
    uf.unite(9, 4);
    uf.unite(2, 1);

    std::cout << "0 and 7 connected: " << (uf.connected(0, 7) ? "yes" : "no") << "\n";
    std::cout << "8 and 9 connected: " << (uf.connected(8, 9) ? "yes" : "no") << "\n";

    uf.unite(5, 0);
    uf.unite(7, 2);
    uf.unite(6, 1);
    uf.unite(1, 0);

    std::cout << "0 and 7 connected: " << (uf.connected(0, 7) ? "yes" : "no") << "\n";

    return 0;
}
```

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| Find | O(1) | Direct array lookup |
| Union | O(n) | Must scan entire array |
| Connected | O(1) | Two find operations |

**Problem**: Union is O(n), making m union operations on n elements cost O(mn) — too slow.

### Approach 2: Quick-Union (Forest of Trees)

Represent each set as a tree. Each element points to its parent. The root of the tree is the representative (id) of the set.

```cpp
#include <iostream>
#include <vector>

class QuickUnion {
private:
    std::vector<int> parent_;
    int count_;  // Number of components

public:
    explicit QuickUnion(int n) : parent_(n), count_(n) {
        for (int i = 0; i < n; ++i) {
            parent_[i] = i;  // Each element is its own root
        }
    }

    // Find: follow parent pointers until root — O(tree height)
    int find(int p) const {
        while (p != parent_[p]) {
            p = parent_[p];
        }
        return p;
    }

    // Union: connect roots — O(tree height)
    void unite(int p, int q) {
        int rootP = find(p);
        int rootQ = find(q);
        if (rootP == rootQ) return;

        parent_[rootP] = rootQ;
        --count_;
    }

    bool connected(int p, int q) const {
        return find(p) == find(q);
    }

    int components() const { return count_; }
};

int main() {
    QuickUnion uf(10);
    uf.unite(4, 3);
    uf.unite(3, 8);
    uf.unite(6, 5);
    uf.unite(9, 4);
    uf.unite(2, 1);

    std::cout << "Components: " << uf.components() << "\n";
    std::cout << "8 and 9 connected: " << (uf.connected(8, 9) ? "yes" : "no") << "\n";

    return 0;
}
```

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| Find | O(n) worst case | Tree can degenerate to a linked list |
| Union | O(n) worst case | Dominated by find |

**Problem**: Without balancing, repeated unions can create a tall, skinny tree. For example, uniting 0-1, 0-2, 0-3, ..., 0-(n-1) creates a chain of length n.

```
Worst case (degenerate tree):    Ideal (balanced tree):
    0                                3
    |                              / | \
    1                             0  1  2
    |
    2
    |
    3
```

---

## 17.3 Union by Rank

**Union by Rank** keeps trees shallow by always attaching the shorter tree under the taller tree.

**Intuition**: A taller tree has more nodes and more depth. Attaching a short tree under a tall tree doesn't increase the tall tree's height. But attaching a tall tree under a short tree would increase the overall height.

**Rank vs Height**: Rank is an upper bound on the height. We use rank instead of actual height because path compression (next section) changes the actual height but we don't want to recompute it.

```cpp
#include <iostream>
#include <vector>

class UnionByRank {
private:
    std::vector<int> parent_;
    std::vector<int> rank_;
    int count_;

public:
    explicit UnionByRank(int n) : parent_(n), rank_(n, 0), count_(n) {
        for (int i = 0; i < n; ++i) {
            parent_[i] = i;
        }
    }

    int find(int p) const {
        while (p != parent_[p]) {
            p = parent_[p];
        }
        return p;
    }

    void unite(int p, int q) {
        int rootP = find(p);
        int rootQ = find(q);
        if (rootP == rootQ) return;

        // Attach smaller tree under larger tree
        if (rank_[rootP] < rank_[rootQ]) {
            parent_[rootP] = rootQ;
        } else if (rank_[rootP] > rank_[rootQ]) {
            parent_[rootQ] = rootP;
        } else {
            // Same rank — pick one as root, increment its rank
            parent_[rootQ] = rootP;
            rank_[rootP]++;
        }
        --count_;
    }

    bool connected(int p, int q) const {
        return find(p) == find(q);
    }

    int components() const { return count_; }
};
```

**Key insight about rank**: When two trees of equal rank are merged, the resulting tree's rank increases by 1. This is because the path from root to leaf increases by exactly 1 (the new root adds one level).

**Height bound**: With union by rank alone, the height of any tree is at most log₂(n). Proof: A tree of rank r has at least 2^r nodes (by induction — merging two rank r-1 trees gives a rank r tree with at least 2^(r-1) + 2^(r-1) = 2^r nodes). So rank ≤ log₂(n), and find is O(log n).

---

## 17.4 Path Compression

**Path compression** is the key optimization that makes DSU nearly O(1). During a `find` operation, after finding the root, we make every node along the path point directly to the root.

```
Before find(4):          After find(4):
    0                       0
    |                    / | \ \
    1                   1  2  3  4
    |
    2
    |
    3
    |
    4
```

### Implementation with Both Optimizations

```cpp
#include <iostream>
#include <vector>

class DisjointSetUnion {
private:
    std::vector<int> parent_;
    std::vector<int> rank_;
    std::vector<int> size_;  // Size of each component (optional)
    int count_;

public:
    explicit DisjointSetUnion(int n) : parent_(n), rank_(n, 0), size_(n, 1), count_(n) {
        for (int i = 0; i < n; ++i) {
            parent_[i] = i;
        }
    }

    // Find with path compression — iterative version
    int find(int p) {
        // First pass: find the root
        int root = p;
        while (root != parent_[root]) {
            root = parent_[root];
        }
        // Second pass: compress path (make all nodes point to root)
        while (p != root) {
            int next = parent_[p];
            parent_[p] = root;
            p = next;
        }
        return root;
    }

    // Alternative: recursive path compression (simpler but uses stack space)
    int findRecursive(int p) {
        if (parent_[p] != p) {
            parent_[p] = findRecursive(parent_[p]);
        }
        return parent_[p];
    }

    // Union by rank with path compression
    void unite(int p, int q) {
        int rootP = find(p);
        int rootQ = find(q);
        if (rootP == rootQ) return;

        // Attach smaller rank tree under larger rank tree
        if (rank_[rootP] < rank_[rootQ]) {
            parent_[rootP] = rootQ;
            size_[rootQ] += size_[rootP];
        } else if (rank_[rootP] > rank_[rootQ]) {
            parent_[rootQ] = rootP;
            size_[rootP] += size_[rootQ];
        } else {
            parent_[rootQ] = rootP;
            rank_[rootP]++;
            size_[rootP] += size_[rootQ];
        }
        --count_;
    }

    bool connected(int p, int q) {
        return find(p) == find(q);
    }

    int components() const { return count_; }

    int componentSize(int p) {
        return size_[find(p)];
    }
};
```

### The Inverse Ackermann Function

With both union by rank and path compression, the amortized time per operation is **O(α(n))**, where α is the **inverse Ackermann function**.

The Ackermann function grows astronomically fast:
- A(1) = 2
- A(2) = 4
- A(3) = 2^65536 - 3 (already unimaginably large)
- A(4) = practically infinity

Its inverse α(n) grows correspondingly slowly:
- α(n) ≤ 4 for any n ≤ 2^65536
- In practice, α(n) ≤ 4 for any conceivable input size

**This means DSU is effectively O(1) per operation in practice.**

| Optimization | Find Time | Union Time | Notes |
|-------------|-----------|------------|-------|
| None (Quick-Union) | O(n) | O(n) | Degenerate trees |
| Union by Rank only | O(log n) | O(log n) | Height bound log n |
| Path Compression only | O(log n) amortized | O(log n) | Similar to union by rank |
| Both | O(α(n)) ≈ O(1) | O(α(n)) ≈ O(1) | Best practical performance |

---

## 17.5 Applications

### Application 1: Kruskal's Minimum Spanning Tree

Kruskal's algorithm uses DSU to efficiently check whether adding an edge would create a cycle.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

struct Edge {
    int u, v, weight;
    bool operator<(const Edge& other) const {
        return weight < other.weight;
    }
};

class DSU {
    std::vector<int> parent_, rank_;
public:
    explicit DSU(int n) : parent_(n), rank_(n, 0) {
        std::iota(parent_.begin(), parent_.end(), 0);
    }

    int find(int p) {
        if (parent_[p] != p) {
            parent_[p] = find(parent_[p]);
        }
        return parent_[p];
    }

    bool unite(int p, int q) {
        int rp = find(p), rq = find(q);
        if (rp == rq) return false;
        if (rank_[rp] < rank_[rq]) std::swap(rp, rq);
        parent_[rq] = rp;
        if (rank_[rp] == rank_[rq]) rank_[rp]++;
        return true;
    }
};

struct MSTResult {
    std::vector<Edge> edges;
    int totalWeight;
};

MSTResult kruskal(int n, std::vector<Edge>& edges) {
    std::sort(edges.begin(), edges.end());

    DSU dsu(n);
    MSTResult result;
    result.totalWeight = 0;

    for (const auto& e : edges) {
        if (dsu.unite(e.u, e.v)) {
            result.edges.push_back(e);
            result.totalWeight += e.weight;
            if (static_cast<int>(result.edges.size()) == n - 1) break;
        }
    }

    return result;
}

int main() {
    // 6 nodes, 9 edges
    std::vector<Edge> edges = {
        {0, 1, 4}, {0, 2, 4}, {1, 2, 2},
        {1, 3, 5}, {2, 3, 8}, {2, 4, 10},
        {3, 4, 2}, {3, 5, 6}, {4, 5, 3}
    };

    auto mst = kruskal(6, edges);

    std::cout << "MST edges:\n";
    for (const auto& e : mst.edges) {
        std::cout << "  " << e.u << " - " << e.v << " (weight " << e.weight << ")\n";
    }
    std::cout << "Total weight: " << mst.totalWeight << "\n";

    return 0;
}
```

**Complexity**: O(E log E) for sorting edges, plus O(E · α(V)) for DSU operations. Total: O(E log E).

### Application 2: Connected Components in Dynamic Graphs

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <numeric>

class DynamicConnectivity {
private:
    std::vector<int> parent_, rank_;
    int components_;

public:
    explicit DynamicConnectivity(int n) : parent_(n), rank_(n, 0), components_(n) {
        std::iota(parent_.begin(), parent_.end(), 0);
    }

    int find(int p) {
        if (parent_[p] != p) parent_[p] = find(parent_[p]);
        return parent_[p];
    }

    void addEdge(int u, int v) {
        if (find(u) != find(v)) {
            // Union by rank
            int ru = find(u), rv = find(v);
            if (rank_[ru] < rank_[rv]) std::swap(ru, rv);
            parent_[rv] = ru;
            if (rank_[ru] == rank_[rv]) rank_[ru]++;
            components_--;
        }
    }

    bool connected(int u, int v) {
        return find(u) == find(v);
    }

    int countComponents() const { return components_; }
};

int main() {
    int n = 7;
    DynamicConnectivity dc(n);

    dc.addEdge(0, 1);
    dc.addEdge(1, 2);
    dc.addEdge(3, 4);

    std::cout << "Components after 3 edges: " << dc.countComponents() << "\n";  // 5
    std::cout << "0 and 2 connected: " << (dc.connected(0, 2) ? "yes" : "no") << "\n";
    std::cout << "0 and 4 connected: " << (dc.connected(0, 4) ? "yes" : "no") << "\n";

    dc.addEdge(2, 4);
    std::cout << "Components after 4 edges: " << dc.countComponents() << "\n";  // 4
    std::cout << "0 and 4 connected: " << (dc.connected(0, 4) ? "yes" : "no") << "\n";

    return 0;
}
```

### Application 3: Cycle Detection in Undirected Graphs

```cpp
#include <iostream>
#include <vector>
#include <numeric>

class CycleDetector {
    std::vector<int> parent_, rank_;
public:
    explicit CycleDetector(int n) : parent_(n), rank_(n, 0) {
        std::iota(parent_.begin(), parent_.end(), 0);
    }

    int find(int p) {
        if (parent_[p] != p) parent_[p] = find(parent_[p]);
        return parent_[p];
    }

    // Returns true if adding edge (u, v) creates a cycle
    bool addEdge(int u, int v) {
        int ru = find(u), rv = find(v);
        if (ru == rv) return true;  // Same component → cycle!

        if (rank_[ru] < rank_[rv]) std::swap(ru, rv);
        parent_[rv] = ru;
        if (rank_[ru] == rank_[rv]) rank_[ru]++;
        return false;
    }
};

int main() {
    CycleDetector cd(5);

    std::vector<std::pair<int, int>> edges = {
        {0, 1}, {1, 2}, {2, 3}, {3, 4}, {4, 1}  // Last edge creates cycle
    };

    for (auto& [u, v] : edges) {
        if (cd.addEdge(u, v)) {
            std::cout << "Cycle detected when adding edge " << u << " - " << v << "\n";
        } else {
            std::cout << "Edge " << u << " - " << v << " added successfully\n";
        }
    }

    return 0;
}
```

### Application 4: Counting Connected Components

```cpp
#include <iostream>
#include <vector>
#include <numeric>

int countComponents(int n, const std::vector<std::pair<int, int>>& edges) {
    std::vector<int> parent(n), rank(n, 0);
    std::iota(parent.begin(), parent.end(), 0);

    std::function<int(int)> find = [&](int p) -> int {
        if (parent[p] != p) parent[p] = find(parent[p]);
        return parent[p];
    };

    int components = n;
    for (auto& [u, v] : edges) {
        int ru = find(u), rv = find(v);
        if (ru != rv) {
            if (rank[ru] < rank[rv]) std::swap(ru, rv);
            parent[rv] = ru;
            if (rank[ru] == rank[rv]) rank[ru]++;
            components--;
        }
    }

    return components;
}

int main() {
    int n = 5;
    std::vector<std::pair<int, int>> edges = {{0, 1}, {1, 2}, {3, 4}};
    std::cout << "Connected components: " << countComponents(n, edges) << "\n";  // 2
    return 0;
}
```

### Application 5: Accounts Merge (LeetCode 721)

This is a real-world application where DSU groups accounts by shared emails.

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <set>
#include <numeric>
#include <algorithm>

class DSU {
    std::vector<int> parent_;
public:
    explicit DSU(int n) : parent_(n) {
        std::iota(parent_.begin(), parent_.end(), 0);
    }

    int find(int p) {
        if (parent_[p] != p) parent_[p] = find(parent_[p]);
        return parent_[p];
    }

    void unite(int p, int q) {
        parent_[find(p)] = find(q);
    }
};

std::vector<std::vector<std::string>>
accountsMerge(const std::vector<std::vector<std::string>>& accounts) {
    DSU dsu(accounts.size());
    std::map<std::string, int> emailToOwner;

    // Map each email to its owner account, and unite accounts with shared emails
    for (int i = 0; i < static_cast<int>(accounts.size()); ++i) {
        for (int j = 1; j < static_cast<int>(accounts[i].size()); ++j) {
            const std::string& email = accounts[i][j];
            if (emailToOwner.count(email)) {
                dsu.unite(i, emailToOwner[email]);
            } else {
                emailToOwner[email] = i;
            }
        }
    }

    // Group emails by their root owner
    std::map<int, std::set<std::string>> merged;
    for (auto& [email, owner] : emailToOwner) {
        merged[dsu.find(owner)].insert(email);
    }

    // Build result
    std::vector<std::vector<std::string>> result;
    for (auto& [owner, emails] : merged) {
        std::vector<std::string> entry;
        entry.push_back(accounts[owner][0]);  // Name
        entry.insert(entry.end(), emails.begin(), emails.end());
        result.push_back(entry);
    }

    return result;
}

int main() {
    std::vector<std::vector<std::string>> accounts = {
        {"John", "johnsmith@mail.com", "john00@mail.com"},
        {"John", "johnnybravo@mail.com"},
        {"John", "johnsmith@mail.com", "john_newyork@mail.com"},
        {"Mary", "mary@mail.com"}
    };

    auto result = accountsMerge(accounts);
    for (const auto& account : result) {
        std::cout << account[0] << ": ";
        for (int i = 1; i < static_cast<int>(account.size()); ++i) {
            std::cout << account[i] << " ";
        }
        std::cout << "\n";
    }

    return 0;
}
```

---

## Complete Working Example: Full DSU with All Features

```cpp
#include <iostream>
#include <vector>
#include <numeric>
#include <cassert>

class DisjointSetUnion {
private:
    std::vector<int> parent_;
    std::vector<int> rank_;
    std::vector<int> size_;
    int count_;

public:
    explicit DisjointSetUnion(int n)
        : parent_(n), rank_(n, 0), size_(n, 1), count_(n) {
        std::iota(parent_.begin(), parent_.end(), 0);
    }

    int find(int p) {
        int root = p;
        while (root != parent_[root]) {
            root = parent_[root];
        }
        while (p != root) {
            int next = parent_[p];
            parent_[p] = root;
            p = next;
        }
        return root;
    }

    bool unite(int p, int q) {
        int rootP = find(p);
        int rootQ = find(q);
        if (rootP == rootQ) return false;

        if (rank_[rootP] < rank_[rootQ]) {
            parent_[rootP] = rootQ;
            size_[rootQ] += size_[rootP];
        } else if (rank_[rootP] > rank_[rootQ]) {
            parent_[rootQ] = rootP;
            size_[rootP] += size_[rootQ];
        } else {
            parent_[rootQ] = rootP;
            rank_[rootP]++;
            size_[rootP] += size_[rootQ];
        }
        --count_;
        return true;
    }

    bool connected(int p, int q) {
        return find(p) == find(q);
    }

    int components() const { return count_; }

    int componentSize(int p) {
        return size_[find(p)];
    }
};

int main() {
    // Example: Social network friend groups
    DisjointSetUnion dsu(10);

    // Friend connections
    dsu.unite(0, 1);
    dsu.unite(1, 2);
    dsu.unite(3, 4);
    dsu.unite(5, 6);
    dsu.unite(6, 7);
    dsu.unite(7, 8);

    std::cout << "Friend groups: " << dsu.components() << "\n";
    std::cout << "Group size of person 0: " << dsu.componentSize(0) << "\n";
    std::cout << "Group size of person 5: " << dsu.componentSize(5) << "\n";
    std::cout << "0 and 2 are friends: " << (dsu.connected(0, 2) ? "yes" : "no") << "\n";
    std::cout << "0 and 5 are friends: " << (dsu.connected(0, 5) ? "yes" : "no") << "\n";

    // Connect the two groups
    dsu.unite(2, 5);
    std::cout << "\nAfter connecting groups:\n";
    std::cout << "Friend groups: " << dsu.components() << "\n";
    std::cout << "Group size of person 0: " << dsu.componentSize(0) << "\n";
    std::cout << "0 and 5 are friends: " << (dsu.connected(0, 5) ? "yes" : "no") << "\n";

    return 0;
}
```

---

## Interview Tips

1. **Recognize DSU problems by keywords**: "connected components", "groups", "equivalence", "merge", "union", "friends", "provinces", "redundant connection".

2. **Always use both optimizations**: Union by rank (or size) AND path compression. Together they give O(α(n)) amortized time.

3. **DSU vs BFS/DFS for connectivity**: DSU is better when edges are added dynamically and you need to query connectivity repeatedly. BFS/DFS is better for a single static graph traversal.

4. **Path compression — recursive vs iterative**: The recursive version `parent[p] = find(parent[p])` is simpler and works great. The iterative version avoids stack overflow for very deep trees.

5. **Counting components**: Initialize count to n. Decrement each time you successfully unite two different components.

6. **Edge cases**: Single node (always 1 component), self-loops (ignore or detect), duplicate edges (idempotent unite handles them).

7. **Union by size vs union by rank**: Both give the same asymptotic complexity. Union by size is useful when you also need to track component sizes.

## Common Mistakes

1. **Forgetting path compression**: Without it, find can be O(n) in the worst case, making the whole algorithm slow.

2. **Wrong parent update in union**: Make sure you update the root's parent, not the original node's parent. `parent[find(p)] = find(q)`, not `parent[p] = find(q)`.

3. **Off-by-one in initialization**: Element indices should match. If nodes are 1-indexed, make the parent array size n+1.

4. **Not checking if already connected before union**: Uniting two elements in the same component should be a no-op. Don't decrement the component count.

5. **Using rank when you mean height**: Rank is an upper bound on height. After path compression, actual height decreases but rank doesn't change. This is intentional — rank is only updated during union.

6. **Stack overflow with recursive find on very large inputs**: For inputs with millions of elements, the iterative path compression is safer.

---

## Practice Problems

### Problem 1: Number of Provinces (LeetCode 547)
**Difficulty**: Medium
**Hint**: Each row of the adjacency matrix represents connections. Use DSU to unite connected cities, then count components.

### Problem 2: Redundant Connection (LeetCode 684)
**Difficulty**: Medium
**Hint**: Process edges one by one. If both endpoints are already in the same component, this edge is redundant (creates a cycle).

### Problem 3: Accounts Merge (LeetCode 721)
**Difficulty**: Medium
**Hint**: Map each email to its account index. When two accounts share an email, unite them. Group emails by their root account.

### Problem 4: Minimum Size Subarray Sum — using DSU variant
**Difficulty**: Medium
**Hint**: Think about how DSU can help with range connectivity problems.

### Problem 5: Surrounded Regions (LeetCode 130)
**Difficulty**: Medium
**Hint**: Use DSU to connect 'O' cells. Connect border 'O' cells to a special "border" node. After processing, flip all 'O' cells not connected to the border.

### Problem 6: Making A Large Island (LeetCode 827)
**Difficulty**: Hard
**Hint**: Use DSU to find all island components and their sizes. For each '0' cell, try flipping it and compute the sum of unique neighboring component sizes.

### Problem 7: Evaluate Division (LeetCode 399)
**Difficulty**: Medium
**Hint**: Use DSU with weighted edges. Each union stores the ratio between two variables. On find, compute the cumulative ratio along the path.

### Problem 8: Lexicographically Smallest Equivalent String (LeetCode 1061)
**Difficulty**: Medium
**Hint**: Use DSU where union always makes the lexicographically smaller character the root.

---

*Next chapter: [Chapter 18: Segment Tree](ch18-segment-tree.md)*
