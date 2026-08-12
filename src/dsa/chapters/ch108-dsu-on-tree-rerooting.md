# Chapter 108: DSU on Tree and Rerooting DP

## Prerequisites
- DFS ([Chapter 22](ch22-graph-fundamentals.md))
- DSU / Union-Find (Chapter 20)
- Tree DP ([Chapter 30](ch30-dp-fundamentals.md))

## Interview Frequency: ★★★

These are advanced tree techniques frequently tested at **Google**, **Meta**, and **ByteDance** for hard tree problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| DSU on Tree | ★★★ | Hard | Small-to-large merging |
| Rerooting DP | ★★★ | Medium-Hard | DP from all roots |

---

## Definition

**DSU on Tree** (also called "small-to-large merging" or "Sack") is a technique to answer subtree queries efficiently by always merging smaller child subtrees into the largest one. Each element is moved O(log n) times across all merges.

**Rerooting DP** computes a tree DP for every possible root in O(n) total, by combining "down" results (from children) and "up" results (from parent).

## Motivation

Naively answering "how many distinct values in subtree of u?" for every node takes O(n²) — you traverse each subtree independently. DSU on Tree solves all such queries in O(n log n) by reusing work.

Rerooting solves problems like "for each node, what's the farthest distance to any other node?" without running a separate DFS from each node (which would be O(n²)).

## Intuition

- **DSU on Tree**: When you have multiple child subtrees, don't throw away the work from the biggest one. Keep it, and only add the smaller ones.
- **Rerooting**: First compute what each node "sees" looking down. Then propagate what it "sees" looking up through its parent.

---

## 108.1 DSU on Tree — Deep Dive

### How It Works

1. Find the **heavy child** (largest subtree) of each node
2. DFS all light children first (with `keep=false` — their data is discarded)
3. DFS the heavy child (with `keep=true` — its data is preserved)
4. Add light children's data to the heavy child's data
5. Add current node's data
6. Answer the query for this node
7. If `keep=false`, remove all data from this subtree

### Dry Run

Tree with values [1, 2, 1, 3, 2, 3] at nodes 0-5:
```
       0(1)
      / \
    1(2)  2(1)
    / \
  3(3) 4(2)
       |
      5(3)
```

Processing node 1 (heavy child of 0):
- Process light child 4 (with 5): distinct = {2, 3} → 2
- Process heavy child 3: distinct = {3} → 1
- Keep heavy child 3's data, add light child 4's data
- Add node 1's value: distinct = {2, 3} → 2
- Answer for node 1: 2 distinct values

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <map>

class DSUonTree {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> val, sz, heavy, answer;
    std::map<int,int> cnt;

    int dfsSize(int u, int p) {
        sz[u] = 1; int maxSize = 0;
        for (int v : adj[u]) {
            if (v != p) {
                int subSize = dfsSize(v, u);
                sz[u] += subSize;
                if (subSize > maxSize) { maxSize = subSize; heavy[u] = v; }
            }
        }
        return sz[u];
    }

    void add(int u, int p) {
        cnt[val[u]]++;
        for (int v : adj[u]) if (v != p) add(v, u);
    }

    void remove(int u, int p) {
        cnt[val[u]]--;
        if (cnt[val[u]] == 0) cnt.erase(val[u]);
        for (int v : adj[u]) if (v != p) remove(v, u);
    }

    void dfs(int u, int p, bool keep) {
        // Process light children first (discard their data)
        for (int v : adj[u])
            if (v != p && v != heavy[u]) dfs(v, u, false);

        // Process heavy child (keep its data)
        if (heavy[u] != -1) dfs(heavy[u], u, true);

        // Add light children's data
        for (int v : adj[u])
            if (v != p && v != heavy[u]) add(v, u);

        // Add current node
        cnt[val[u]]++;

        // Answer query: number of distinct values in subtree
        answer[u] = cnt.size();

        // If this is a light child's subtree, clean up
        if (!keep) remove(u, p);
    }

public:
    DSUonTree(int n) : n(n), adj(n), val(n), sz(n), heavy(n, -1), answer(n) {}
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }

    std::vector<int> solve(int root, const std::vector<int>& values) {
        val = values;
        dfsSize(root, -1);
        dfs(root, -1, false);
        return answer;
    }
};

int main() {
    DSUonTree dsu(6);
    dsu.addEdge(0, 1); dsu.addEdge(0, 2);
    dsu.addEdge(1, 3); dsu.addEdge(1, 4); dsu.addEdge(2, 5);
    std::vector<int> values = {1, 2, 1, 3, 2, 3};
    auto ans = dsu.solve(0, values);
    for (int i = 0; i < 6; i++)
        std::cout << "Subtree " << i << ": " << ans[i] << " distinct\n";
    return 0;
}
```

### Python Implementation

```python
from collections import defaultdict

class DSUonTree:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.val = [0] * n
        self.sz = [0] * n
        self.heavy = [-1] * n
        self.answer = [0] * n
        self.cnt = defaultdict(int)

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def _dfs_size(self, u, p):
        self.sz[u] = 1
        max_size = 0
        for v in self.adj[u]:
            if v != p:
                sub_size = self._dfs_size(v, u)
                self.sz[u] += sub_size
                if sub_size > max_size:
                    max_size = sub_size
                    self.heavy[u] = v
        return self.sz[u]

    def _add(self, u, p):
        self.cnt[self.val[u]] += 1
        for v in self.adj[u]:
            if v != p:
                self._add(v, u)

    def _remove(self, u, p):
        self.cnt[self.val[u]] -= 1
        if self.cnt[self.val[u]] == 0:
            del self.cnt[self.val[u]]
        for v in self.adj[u]:
            if v != p:
                self._remove(v, u)

    def _dfs(self, u, p, keep):
        for v in self.adj[u]:
            if v != p and v != self.heavy[u]:
                self._dfs(v, u, False)

        if self.heavy[u] != -1:
            self._dfs(self.heavy[u], u, True)

        for v in self.adj[u]:
            if v != p and v != self.heavy[u]:
                self._add(v, u)

        self.cnt[self.val[u]] += 1
        self.answer[u] = len(self.cnt)

        if not keep:
            self._remove(u, p)

    def solve(self, root, values):
        self.val = values
        self._dfs_size(root, -1)
        self._dfs(root, -1, False)
        return self.answer

# Example
dsu = DSUonTree(6)
dsu.add_edge(0, 1); dsu.add_edge(0, 2)
dsu.add_edge(1, 3); dsu.add_edge(1, 4); dsu.add_edge(2, 5)
ans = dsu.solve(0, [1, 2, 1, 3, 2, 3])
for i, a in enumerate(ans):
    print(f"Subtree {i}: {a} distinct")
```

### Java Implementation

```java
import java.util.*;

public class DSUonTree {
    int n;
    List<List<Integer>> adj;
    int[] val, sz, heavy, answer;
    Map<Integer, Integer> cnt = new HashMap<>();

    public DSUonTree(int n) {
        this.n = n;
        adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        val = new int[n]; sz = new int[n];
        heavy = new int[n]; Arrays.fill(heavy, -1);
        answer = new int[n];
    }

    void addEdge(int u, int v) { adj.get(u).add(v); adj.get(v).add(u); }

    int dfsSize(int u, int p) {
        sz[u] = 1; int maxSize = 0;
        for (int v : adj.get(u)) {
            if (v != p) {
                int subSize = dfsSize(v, u);
                sz[u] += subSize;
                if (subSize > maxSize) { maxSize = subSize; heavy[u] = v; }
            }
        }
        return sz[u];
    }

    void add(int u, int p) {
        cnt.merge(val[u], 1, Integer::sum);
        for (int v : adj.get(u)) if (v != p) add(v, u);
    }

    void remove(int u, int p) {
        cnt.merge(val[u], -1, Integer::sum);
        if (cnt.get(val[u]) == 0) cnt.remove(val[u]);
        for (int v : adj.get(u)) if (v != p) remove(v, u);
    }

    void dfs(int u, int p, boolean keep) {
        for (int v : adj.get(u))
            if (v != p && v != heavy[u]) dfs(v, u, false);
        if (heavy[u] != -1) dfs(heavy[u], u, true);
        for (int v : adj.get(u))
            if (v != p && v != heavy[u]) add(v, u);
        cnt.merge(val[u], 1, Integer::sum);
        answer[u] = cnt.size();
        if (!keep) remove(u, p);
    }

    int[] solve(int root, int[] values) {
        val = values;
        dfsSize(root, -1);
        dfs(root, -1, false);
        return answer;
    }

    public static void main(String[] args) {
        DSUonTree dsu = new DSUonTree(6);
        dsu.addEdge(0, 1); dsu.addEdge(0, 2);
        dsu.addEdge(1, 3); dsu.addEdge(1, 4); dsu.addEdge(2, 5);
        int[] ans = dsu.solve(0, new int[]{1, 2, 1, 3, 2, 3});
        for (int i = 0; i < 6; i++)
            System.out.println("Subtree " + i + ": " + ans[i] + " distinct");
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Build + all queries | O(n log n) | O(n) |
| Each element moved | O(log n) times | — |

---

## 108.2 Rerooting DP — Deep Dive

### Definition

Rerooting computes a DP value for every node as if it were the root. The key insight: combine "down" information (from children) with "up" information (from parent's perspective).

### Algorithm

1. **DFS Down**: Compute `down[u]` = result when u is root of its subtree
2. **DFS Up**: For each child v, compute `up[v]` = result from the rest of the tree (excluding v's subtree)
3. **Combine**: `answer[u] = f(down[u], up[u])`

### Dry Run

For "max distance from each node" on tree:
```
    0
   / \
  1   2
 /|   |
3  4  5
```

**DFS Down** (compute max depth in subtree):
```
down[3] = 0, down[4] = 0, down[5] = 0
down[1] = max(down[3]+1, down[4]+1) = 1
down[2] = max(down[5]+1) = 1
down[0] = max(down[1]+1, down[2]+1) = 2
```

**DFS Up** (compute max distance going through parent):
```
up[0] = 0
For child 1 of 0: up[1] = max(up[0]+1, down[2]+2) = max(1, 3) = 3
For child 2 of 0: up[2] = max(up[0]+1, down[1]+2) = max(1, 3) = 3
For child 3 of 1: up[3] = max(up[1]+1, down[4]+2) = max(4, 2) = 4
For child 4 of 1: up[4] = max(up[1]+1, down[3]+2) = max(4, 2) = 4
For child 5 of 2: up[5] = max(up[2]+1) = 4
```

**Answer** = max(down[u], up[u]):
```
ans[0] = 2, ans[1] = 3, ans[2] = 3
ans[3] = 4, ans[4] = 4, ans[5] = 4
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class Rerooting {
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
            if (v == p) continue;
            int val = down[v] + 1;
            if (val > max1) { max2 = max1; max1 = val; }
            else if (val > max2) max2 = val;
        }
        for (int v : adj[u]) {
            if (v == p) continue;
            int val = down[v] + 1;
            int use = (val == max1) ? max2 : max1;
            dfsUp(v, u, std::max(pUp + 1, use + 1));
        }
        ans[u] = std::max(down[u], up[u]);
    }

public:
    Rerooting(int n) : n(n), adj(n), down(n), up(n), ans(n) {}
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }

    std::vector<int> solve(int root) {
        dfsDown(root, -1);
        dfsUp(root, -1, 0);
        return ans;
    }
};

int main() {
    Rerooting tree(6);
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
class Rerooting:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def solve(self, root):
        n = self.n
        down = [0] * n
        up = [0] * n
        ans = [0] * n

        def dfs_down(u, p):
            d = 0
            for v in self.adj[u]:
                if v != p:
                    d = max(d, dfs_down(v, u) + 1)
            down[u] = d
            return d

        def dfs_up(u, p, p_up):
            up[u] = p_up
            max1 = max2 = 0
            for v in self.adj[u]:
                if v != p:
                    val = down[v] + 1
                    if val > max1:
                        max2, max1 = max1, val
                    elif val > max2:
                        max2 = val
            for v in self.adj[u]:
                if v != p:
                    val = down[v] + 1
                    use = max2 if val == max1 else max1
                    dfs_up(v, u, max(p_up + 1, use + 1))
            ans[u] = max(down[u], up[u])

        dfs_down(root, -1)
        dfs_up(root, -1, 0)
        return ans

# Example
tree = Rerooting(6)
tree.add_edge(0, 1); tree.add_edge(0, 2)
tree.add_edge(1, 3); tree.add_edge(1, 4); tree.add_edge(2, 5)
ans = tree.solve(0)
for i, a in enumerate(ans):
    print(f"Node {i}: max dist = {a}")
```

### Java Implementation

```java
import java.util.*;

public class Rerooting {
    int n;
    List<List<Integer>> adj;
    int[] down, up, ans;

    public Rerooting(int n) {
        this.n = n;
        adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        down = new int[n]; up = new int[n]; ans = new int[n];
    }

    void addEdge(int u, int v) { adj.get(u).add(v); adj.get(v).add(u); }

    int dfsDown(int u, int p) {
        int d = 0;
        for (int v : adj.get(u))
            if (v != p) d = Math.max(d, dfsDown(v, u) + 1);
        down[u] = d;
        return d;
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
        dfsDown(root, -1);
        dfsUp(root, -1, 0);
        return ans;
    }

    public static void main(String[] args) {
        Rerooting tree = new Rerooting(6);
        tree.addEdge(0, 1); tree.addEdge(0, 2);
        tree.addEdge(1, 3); tree.addEdge(1, 4); tree.addEdge(2, 5);
        int[] ans = tree.solve(0);
        for (int i = 0; i < 6; i++)
            System.out.println("Node " + i + ": max dist = " + ans[i]);
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| DFS Down | O(n) | O(n) |
| DFS Up | O(n) | O(n) |
| Total | O(n) | O(n) |

---

## Exercises

1. **Subtree mode**: Modify DSU on Tree to find the most frequent value in each subtree (mode query).

2. **Subtree sum with rerooting**: Given a tree with node values, compute the sum of all node values in each node's subtree when that node is the root.

3. **Diameter via rerooting**: Use rerooting to compute the diameter of a tree. (Hint: track top-2 depths at each node.)

4. **Count distinct on path**: Combine DSU on Tree with Euler tour to answer "how many distinct values on path from u to v?"

5. **Rerooting for product**: Given a tree, for each node compute the product of distances to all other nodes. Use rerooting with appropriate merge.

---

## Interview Questions

1. **Q: What is the time complexity of DSU on Tree and why?**
   A: O(n log n). Each element is moved to a larger set at most O(log n) times, because each move at least doubles the set size it joins.

2. **Q: How does rerooting avoid recomputing the entire DP for each root?**
   A: It separates "down" information (from children) and "up" information (from parent). The "up" for a child combines the parent's "up" and the best "down" from the parent's other children — all computed in O(1) per edge.

3. **Q: When would you use DSU on Tree vs. Euler tour + Mo's algorithm?**
   A: DSU on Tree is O(n log n) and online (answers queries in DFS order). Mo's on Euler tour is O(n√n) but handles arbitrary query order. Prefer DSU on Tree when queries are naturally subtree-based.

4. **Q: Can rerooting work for problems where the merge isn't commutative?**
   A: Yes, but you need to track prefix and suffix aggregates for children. For each child, combine the parent's "up" with prefix and suffix of sibling "downs" — all in O(degree) per node, still O(n) total.

---

## Cross-References

- Chapter 20: DSU / Union-Find — The "DSU" in DSU on Tree refers to small-to-large merging, not the Union-Find data structure
- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md) — Tree DP is the foundation for rerooting
- [Chapter 107: HLD and Centroid Applications](ch107-hld-centroid-applications.md) — Other advanced tree decomposition techniques
- [Chapter 13: Trees](ch13-trees.md) — Tree fundamentals

---

## Summary

| Technique | Time | Key Idea | Best For |
|---|---|---|---|
| DSU on Tree | O(n log n) | Small-to-large merging | Subtree queries |
| Rerooting DP | O(n) | DFS down + up | DP from all roots |
