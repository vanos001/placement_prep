# Chapter 106: Euler Tour and Tree Flattening

## Prerequisites
- DFS (Depth-First Search)
- Segment trees
- Trees (adjacency lists, rooted trees)
- Recursion

## Interview Frequency: ★★★★

Euler tour flattening transforms tree problems into array problems. By recording entry and exit times during DFS, we can convert subtree queries into range queries on a flat array, which can then be solved with segment trees, BITs, or other array-based data structures. **Google**, **Meta**, **Amazon**, and **Microsoft** all test this pattern.

> **Key Insight:** A subtree rooted at node `u` corresponds to a contiguous range `[tin[u], tout[u]]` in the Euler tour. This means any subtree query becomes a range query on an array.

| Query | Technique | Time |
|---|---|---|
| Subtree sum | Euler Tour + Segment Tree | O(log n) |
| Subtree update | Euler Tour + Lazy Segment Tree | O(log n) |
| Is ancestor? | Check tin/tout ranges | O(1) |
| Path queries | HLD (Heavy-Light Decomposition) | O(log² n) |
| Subtree min/max | Euler Tour + Segment Tree | O(log n) |

---

## 106.1 What Problem Does It Solve?

### The Subtree Query Problem

Given a rooted tree where each node has a value, answer queries like:
- "What is the sum of all values in the subtree of node u?"
- "Add x to all values in the subtree of node u."
- "Is node u an ancestor of node v?"

**Naive approach:** For subtree sum, do a DFS from u and sum all values → O(size of subtree) per query. For many queries on large trees, this is too slow.

**Euler tour approach:** Flatten the tree into an array so that each subtree becomes a contiguous range. Then use a segment tree for O(log n) queries and updates.

---

## 106.2 Intuition — The Flattening Process

Imagine you're exploring a tree with a pen. Every time you visit a node (on entry or exit), you write it down:

```
      0
     / \
    1   2
   /|   |
  3  4  5
```

**DFS traversal with entry/exit recording:**

```
Enter 0 → write 0
  Enter 1 → write 1
    Enter 3 → write 3
    Exit 3
    Enter 4 → write 4
    Exit 4
  Exit 1
  Enter 2 → write 2
    Enter 5 → write 5
    Exit 5
  Exit 2
Exit 0
```

**Euler tour (entry-only):** `[0, 1, 3, 4, 2, 5]`

**Entry/Exit times:**

| Node | tin (entry) | tout (exit) |
|---|---|---|
| 0 | 0 | 5 |
| 1 | 1 | 3 |
| 2 | 4 | 5 |
| 3 | 2 | 2 |
| 4 | 3 | 3 |
| 5 | 5 | 5 |

**Key observation:** The subtree of node 1 consists of nodes {1, 3, 4}, which occupy indices [1, 3] in the Euler tour — a contiguous range!

---

## 106.3 Types of Euler Tours

There are three common variants:

### 1. Entry-Only Tour (Preorder)
Record each node once when first visited.
- Array: `[0, 1, 3, 4, 2, 5]`
- Subtree of u = range `[tin[u], tout[u]]`
- Used for: subtree queries (sum, min, max, update)

### 2. Entry-Exit Tour (Full Euler Tour)
Record each node on entry AND exit.
- Array: `[0, 1, 3, 3, 4, 4, 1, 2, 5, 5, 2, 0]`
- Each edge is traversed exactly twice.
- Used for: LCA (via RMQ on the tour), path queries.

### 3. Edge Tour
Record each edge (parent → child) on traversal.
- Used for: edge-based queries, distance queries.

For most competitive programming and interview problems, the **entry-only tour** is what you need.

---

## 106.4 Formal Definition

For a rooted tree with root `r`:

**Entry time** `tin[u]`: the time (index) when DFS first visits node `u`.
**Exit time** `tout[u]`: the time (index) when DFS finishes processing the subtree of `u`.

**Properties:**
1. `tin[u] ≤ tin[v] ≤ tout[u]` if and only if `u` is an ancestor of `v`.
2. For any node `u`, the subtree of `u` in the Euler tour occupies exactly the range `[tin[u], tout[u]]`.
3. Two nodes `u` and `v` are in different subtrees if and only if their ranges `[tin[u], tout[u]]` and `[tin[v], tout[v]]` don't overlap.

---

## 106.5 Step-by-Step Walkthrough

### Problem: Subtree Sum with Updates

Given a tree with node values, support:
- `UPDATE(u, x)`: add `x` to all nodes in subtree of `u`
- `QUERY(u)`: return sum of all values in subtree of `u`

**Solution using Euler Tour + Lazy Segment Tree:**

1. **Flatten the tree:** Run DFS, record `tin[u]` and `tout[u]` for each node.
2. **Create flat array:** `flat[tin[u]] = value[u]`
3. **Build segment tree** on the flat array.
4. **UPDATE(u, x):** Range update on `[tin[u], tout[u]]` → O(log n)
5. **QUERY(u):** Range sum on `[tin[u], tout[u]]` → O(log n)

### Dry Run

Tree:
```
      0 (val=5)
     / \
    1   2 (val=3, val=7)
   /|   |
  3  4  5 (val=1, val=4, val=2)
```

**Step 1: DFS to get tin/tout**

```
DFS(0, -1): tin[0]=0
  DFS(1, 0): tin[1]=1
    DFS(3, 1): tin[3]=2, tout[3]=2
    DFS(4, 1): tin[4]=3, tout[4]=3
  tout[1]=3
  DFS(2, 0): tin[2]=4
    DFS(5, 2): tin[5]=5, tout[5]=5
  tout[2]=5
tout[0]=5
```

**Step 2: Flat array**
```
Index:  0  1  2  3  4  5
Value:  5  3  1  4  7  2
Node:   0  1  3  4  2  5
```

**Step 3: QUERY(1)**
- Range: [tin[1], tout[1]] = [1, 3]
- Sum of flat[1..3] = 3 + 1 + 4 = **8** ✓

**Step 4: UPDATE(1, 10)**
- Range update on [1, 3]: add 10 to flat[1], flat[2], flat[3]
- New flat: [5, 13, 11, 14, 7, 2]

**Step 5: QUERY(0) after update**
- Range: [0, 5]
- Sum = 5 + 13 + 11 + 14 + 7 + 2 = **52** ✓

---

## 106.6 Ancestor Check in O(1)

To check if `u` is an ancestor of `v`:
```
isAncestor(u, v) = (tin[u] <= tin[v]) && (tout[v] <= tout[u])
```

This works because:
- If u is an ancestor of v, DFS enters u before v and exits u after v.
- Conversely, if tin[u] ≤ tin[v] ≤ tout[u], then v was discovered while exploring u's subtree.

---

## 106.7 Complexity Analysis

| Operation | Time | Notes |
|---|---|---|
| DFS (build tour) | O(n) | Single DFS pass |
| Build segment tree | O(n) | On flat array |
| Subtree query | O(log n) | Range query on segment tree |
| Subtree update | O(log n) | Lazy range update |
| Ancestor check | O(1) | tin/tout comparison |
| Path query | O(log² n) | Requires HLD |
| Space | O(n) | tin, tout, flat, segment tree |

---

## 106.8 Implementation

### C++ — Euler Tour with Segment Tree

```cpp
#include <iostream>
#include <vector>

class EulerTour {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> tin, tout, flat, val;

    void dfs(int u, int p) {
        tin[u] = timer;
        flat[timer] = val[u];
        timer++;
        for (int v : adj[u])
            if (v != p) dfs(v, u);
        tout[u] = timer - 1;
    }

public:
    EulerTour(int n) : n(n), timer(0), adj(n), tin(n), tout(n), flat(n), val(n) {}

    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }
    void setVal(int u, int v) { val[u] = v; }
    void build(int root) { dfs(root, -1); }

    std::pair<int,int> subtreeRange(int u) { return {tin[u], tout[u]}; }
    int getFlat(int i) { return flat[i]; }

    bool isAncestor(int u, int v) {
        return tin[u] <= tin[v] && tout[v] <= tout[u];
    }
};

// Segment Tree for range sum + range update
class SegTree {
    int n;
    std::vector<long long> tree, lazy;

    void push(int node, int start, int end) {
        if (lazy[node]) {
            tree[node] += lazy[node] * (end - start + 1);
            if (start != end) {
                lazy[2*node] += lazy[node];
                lazy[2*node+1] += lazy[node];
            }
            lazy[node] = 0;
        }
    }

    void update(int node, int start, int end, int l, int r, int val) {
        push(node, start, end);
        if (start > r || end < l) return;
        if (l <= start && end <= r) {
            lazy[node] += val;
            push(node, start, end);
            return;
        }
        int mid = (start + end) / 2;
        update(2*node, start, mid, l, r, val);
        update(2*node+1, mid+1, end, l, r, val);
        tree[node] = tree[2*node] + tree[2*node+1];
    }

    long long query(int node, int start, int end, int l, int r) {
        push(node, start, end);
        if (start > r || end < l) return 0;
        if (l <= start && end <= r) return tree[node];
        int mid = (start + end) / 2;
        return query(2*node, start, mid, l, r) +
               query(2*node+1, mid+1, end, l, r);
    }

public:
    SegTree(int n) : n(n), tree(4*n, 0), lazy(4*n, 0) {}
    void build(const std::vector<int>& arr, int node, int start, int end) {
        if (start == end) { tree[node] = arr[start]; return; }
        int mid = (start + end) / 2;
        build(arr, 2*node, start, mid);
        build(arr, 2*node+1, mid+1, end);
        tree[node] = tree[2*node] + tree[2*node+1];
    }
    void update(int l, int r, int val) { update(1, 0, n-1, l, r, val); }
    long long query(int l, int r) { return query(1, 0, n-1, l, r); }
};

int main() {
    //       0 (val=5)
    //      / \
    //     1   2 (val=3, val=7)
    //    /|   |
    //   3  4  5 (val=1, val=4, val=2)

    EulerTour et(6);
    et.addEdge(0, 1); et.addEdge(0, 2);
    et.addEdge(1, 3); et.addEdge(1, 4); et.addEdge(2, 5);
    et.setVal(0, 5); et.setVal(1, 3); et.setVal(2, 7);
    et.setVal(3, 1); et.setVal(4, 4); et.setVal(5, 2);
    et.build(0);

    // Build segment tree on flat array
    std::vector<int> flatArr(6);
    for (int i = 0; i < 6; i++) flatArr[i] = et.getFlat(i);
    SegTree st(6);
    st.build(flatArr, 1, 0, 5);

    // Subtree sum of node 1
    auto [l, r] = et.subtreeRange(1);
    std::cout << "Subtree sum of 1: " << st.query(l, r) << "\n"; // 3+1+4 = 8

    // Update subtree of 1: add 10
    st.update(l, r, 10);

    // Subtree sum of 1 after update
    std::cout << "Subtree sum of 1 after +10: " << st.query(l, r) << "\n"; // 13+11+14 = 38

    // Subtree sum of root
    auto [l0, r0] = et.subtreeRange(0);
    std::cout << "Subtree sum of 0: " << st.query(l0, r0) << "\n"; // 5+13+11+14+7+2 = 52

    // Ancestor check
    std::cout << "0 ancestor of 5? " << et.isAncestor(0, 5) << "\n"; // 1
    std::cout << "1 ancestor of 5? " << et.isAncestor(1, 5) << "\n"; // 0

    return 0;
}
```

### Python — Euler Tour with Segment Tree

```python
class EulerTour:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.tin = [0] * n
        self.tout = [0] * n
        self.flat = [0] * n
        self.val = [0] * n
        self.timer = 0

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def build(self, root=0):
        self.timer = 0
        self._dfs(root, -1)

    def _dfs(self, u, p):
        self.tin[u] = self.timer
        self.flat[self.timer] = self.val[u]
        self.timer += 1
        for v in self.adj[u]:
            if v != p:
                self._dfs(v, u)
        self.tout[u] = self.timer - 1

    def subtree_range(self, u):
        return self.tin[u], self.tout[u]

    def is_ancestor(self, u, v):
        return self.tin[u] <= self.tin[v] and self.tout[v] <= self.tout[u]


class SegTree:
    """Segment tree for range sum with lazy range updates."""
    def __init__(self, data):
        self.n = len(data)
        self.tree = [0] * (4 * self.n)
        self.lazy = [0] * (4 * self.n)
        self._build(data, 1, 0, self.n - 1)

    def _build(self, data, node, start, end):
        if start == end:
            self.tree[node] = data[start]
            return
        mid = (start + end) // 2
        self._build(data, 2 * node, start, mid)
        self._build(data, 2 * node + 1, mid + 1, end)
        self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]

    def _push(self, node, start, end):
        if self.lazy[node]:
            self.tree[node] += self.lazy[node] * (end - start + 1)
            if start != end:
                self.lazy[2 * node] += self.lazy[node]
                self.lazy[2 * node + 1] += self.lazy[node]
            self.lazy[node] = 0

    def update(self, l, r, val, node=1, start=0, end=None):
        if end is None:
            end = self.n - 1
        self._push(node, start, end)
        if start > r or end < l:
            return
        if l <= start and end <= r:
            self.lazy[node] += val
            self._push(node, start, end)
            return
        mid = (start + end) // 2
        self.update(l, r, val, 2 * node, start, mid)
        self.update(l, r, val, 2 * node + 1, mid + 1, end)
        self.tree[node] = self.tree[2 * node] + self.tree[2 * node + 1]

    def query(self, l, r, node=1, start=0, end=None):
        if end is None:
            end = self.n - 1
        self._push(node, start, end)
        if start > r or end < l:
            return 0
        if l <= start and end <= r:
            return self.tree[node]
        mid = (start + end) // 2
        return (self.query(l, r, 2 * node, start, mid) +
                self.query(l, r, 2 * node + 1, mid + 1, end))


if __name__ == "__main__":
    et = EulerTour(6)
    et.add_edge(0, 1); et.add_edge(0, 2)
    et.add_edge(1, 3); et.add_edge(1, 4); et.add_edge(2, 5)
    vals = [5, 3, 7, 1, 4, 2]
    for i, v in enumerate(vals):
        et.val[i] = v
    et.build(0)

    st = SegTree(et.flat)

    l, r = et.subtree_range(1)
    print(f"Subtree sum of 1: {st.query(l, r)}")  # 8

    st.update(l, r, 10)
    print(f"Subtree sum of 1 after +10: {st.query(l, r)}")  # 38

    l0, r0 = et.subtree_range(0)
    print(f"Subtree sum of 0: {st.query(l0, r0)}")  # 52

    print(f"0 ancestor of 5? {et.is_ancestor(0, 5)}")  # True
    print(f"1 ancestor of 5? {et.is_ancestor(1, 5)}")  # False
```

### Java — Euler Tour

```java
import java.util.*;

public class EulerTourExample {
    static int n, timer;
    static List<List<Integer>> adj;
    static int[] tin, tout, flat, val;

    static void dfs(int u, int p) {
        tin[u] = timer;
        flat[timer] = val[u];
        timer++;
        for (int v : adj.get(u))
            if (v != p) dfs(v, u);
        tout[u] = timer - 1;
    }

    static boolean isAncestor(int u, int v) {
        return tin[u] <= tin[v] && tout[v] <= tout[u];
    }

    public static void main(String[] args) {
        n = 6;
        adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        tin = new int[n]; tout = new int[n]; flat = new int[n];
        val = new int[]{5, 3, 7, 1, 4, 2};

        //       0
        //      / \
        //     1   2
        //    /|   |
        //   3  4  5
        int[][] edges = {{0,1},{0,2},{1,3},{1,4},{2,5}};
        for (int[] e : edges) {
            adj.get(e[0]).add(e[1]);
            adj.get(e[1]).add(e[0]);
        }

        timer = 0;
        dfs(0, -1);

        System.out.println("Subtree range of 1: [" + tin[1] + ", " + tout[1] + "]");
        System.out.println("0 ancestor of 5? " + isAncestor(0, 5));
        System.out.println("1 ancestor of 5? " + isAncestor(1, 5));

        // Subtree sum of 1 (using flat array directly for demo)
        int sum = 0;
        for (int i = tin[1]; i <= tout[1]; i++) sum += flat[i];
        System.out.println("Subtree sum of 1: " + sum);
    }
}
```

---

## 106.9 Applications

1. **Subtree queries** — The most common use. Any associative operation (sum, min, max, XOR, GCD) on subtrees can be answered with a segment tree on the flattened array.

2. **Ancestor checks** — O(1) ancestor determination using tin/tout ranges. Used in LCA algorithms and tree-based DP.

3. **Flattening for Mo's algorithm on trees** — Convert tree path queries to array range queries for Mo's algorithm.

4. **Dynamic connectivity on trees** — Euler tour + segment tree supports subtree updates and path queries.

5. **Tree decomposition** — Euler tours are a building block for Heavy-Light Decomposition (HLD).

6. **Bracket sequences** — The entry-exit tour can be encoded as a balanced bracket sequence, enabling additional techniques.

---

## 106.10 Exercises

1. **Subtree XOR:** Given a tree with node values, answer queries: "What is the XOR of all values in the subtree of node u?" Implement using Euler tour + segment tree.

2. **Subtree minimum:** Modify the solution to support range minimum queries on subtrees.

3. **Count nodes in subtree:** Given a tree, answer "how many nodes are in the subtree of u?" for many queries. (Hint: you don't even need values — just count indices.)

4. **Path sum query (HLD):** Extend the Euler tour approach to handle path queries from node u to node v using Heavy-Light Decomposition.

5. **Flatten a DAG:** Can you flatten a DAG (directed acyclic graph) similarly? What complications arise compared to a tree?

6. **Euler tour + Mo's:** Implement Mo's algorithm on a tree by converting subtree queries to array queries using Euler tour. What's the time complexity?

---

## 106.11 Interview Questions

1. **Q: What is an Euler tour of a tree and how do you compute it?**
   A: An Euler tour records nodes in the order they're visited during DFS. We record `tin[u]` (entry time) and `tout[u]` (exit time) for each node. The subtree of u maps to range `[tin[u], tout[u]]` in the flat array.

2. **Q: How do you check if u is an ancestor of v in O(1)?**
   A: Check if `tin[u] <= tin[v]` and `tout[v] <= tout[u]`. This works because DFS enters u before any of its descendants and exits u after all of them.

3. **Q: Can Euler tour handle path queries?**
   A: Not directly. For path queries, use Heavy-Light Decomposition which decomposes paths into O(log n) contiguous segments, each queryable via segment tree.

4. **Q: What's the difference between entry-only and entry-exit Euler tours?**
   A: Entry-only records each node once (preorder). Entry-exit records each node twice (on entry and exit). Entry-only is simpler for subtree queries. Entry-exit is needed for LCA via RMQ and some path-based techniques.

5. **Q: How would you handle subtree queries if the tree is unrooted?**
   A: Choose an arbitrary root (e.g., node 0). The Euler tour from that root works for subtree queries. Note that "subtree" is defined relative to the chosen root.

6. **Q: What if you need to support both subtree and path queries?**
   A: Use Euler tour for subtree queries and Heavy-Light Decomposition for path queries. HLD decomposes the tree into chains, each represented as a contiguous range in an array.

---

## 106.12 Cross-References

- **Chapter 101 (Segment Trees):** Euler tour + segment tree is the standard pattern for subtree queries.
- **Chapter 99 (BIT/Fenwick Tree):** BIT can replace segment tree for subtree sum (no lazy updates).
- **Chapter 11 (LCA):** Euler tour (entry-exit variant) is the foundation of the Euler tour + sparse table LCA method.
- **Chapter 110 (Heavy-Light Decomposition):** HLD extends Euler tour to handle path queries.
- **Chapter 102 (Wavelet Trees):** Can be used on the flattened array for more advanced queries.
- **Chapter 150 (Mo's Algorithm):** Euler tour + Mo's algorithm handles subtree queries offline.

---

## Summary

| Operation | Time | Notes |
|---|---|---|
| Build Euler Tour | O(n) | Single DFS pass |
| Subtree query | O(log n) | With segment tree on flat array |
| Subtree update | O(log n) | With lazy segment tree |
| Ancestor check | O(1) | tin[u] ≤ tin[v] ≤ tout[u] |
| Path query | O(log² n) | Requires HLD extension |
| Space | O(n) | tin, tout, flat arrays + segment tree |
