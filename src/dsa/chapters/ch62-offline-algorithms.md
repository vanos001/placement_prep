# Chapter 62: Offline Algorithms

## Prerequisites

- Disjoint Set Union (Union-Find)
- DFS and Euler Tour on trees
- Square root decomposition
- Segment trees
- LCA (Lowest Common Ancestor)

## Interview Frequency: ★★

Offline algorithms appear in competitive programming-style interviews at **ByteDance**, **Yandex**, and **Google**. Mo's Algorithm is a favorite for range query problems. DSU on Tree is powerful for subtree queries. These techniques are less common in standard interviews but are excellent differentiators for hard problems.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Mo's Algorithm | ★★★ | ByteDance, Google | Medium |
| DSU on Tree | ★★ | ByteDance, competitive programming | Hard |
| Offline LCA | ★★ | Google, Amazon | Medium |
| Offline Connectivity | ★ | Research, competitive programming | Hard |
| Offline Query Processing | ★★★ | All companies | Medium |

---

## 62.1 Mo's Algorithm

**Mo's Algorithm** answers offline range queries in O((N + Q)√N) time by processing queries in a specific order that minimizes the number of add/remove operations.

### Key Idea

1. Divide the array into blocks of size √N
2. Sort queries by (block of left endpoint, right endpoint)
3. Maintain a sliding window, adding/removing elements as we move between queries

### When to Use

- Multiple range queries on a static array
- Each query can be answered incrementally (add/remove one element in O(1))
- Online processing is not required

### When NOT to Use

- Queries need to be answered online
- Updates are interleaved with queries (use Mo's with updates or segment tree)
- The add/remove operation is not O(1)

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <map>

struct Query {
    int l, r, idx;
};

class MoAlgorithm {
    int n, blockSize;
    std::vector<int> arr;
    std::vector<Query> queries;
    std::vector<long long> answers;
    
    // State for current window
    long long currentAnswer;
    std::map<int, int> freq; // frequency of each value
    
    void add(int pos) {
        int val = arr[pos];
        // For "count distinct": if freq[val] == 0, answer increases
        if (freq[val] == 0) currentAnswer++;
        freq[val]++;
    }
    
    void remove(int pos) {
        int val = arr[pos];
        freq[val]--;
        if (freq[val] == 0) currentAnswer--;
    }
    
public:
    MoAlgorithm(const std::vector<int>& arr) 
        : n(arr.size()), blockSize(std::sqrt(n)), arr(arr), currentAnswer(0) {}
    
    void addQuery(int l, int r) {
        queries.push_back({l, r, (int)queries.size()});
    }
    
    std::vector<long long> solve() {
        answers.resize(queries.size());
        
        // Sort queries by Mo's order
        std::sort(queries.begin(), queries.end(), [this](const Query& a, const Query& b) {
            int blockA = a.l / blockSize;
            int blockB = b.l / blockSize;
            if (blockA != blockB) return blockA < blockB;
            // Within same block, sort by right endpoint
            // Alternate direction for even/odd blocks (optimization)
            if (blockA % 2 == 0) return a.r < b.r;
            return a.r > b.r;
        });
        
        int curL = 0, curR = -1;
        
        for (auto& q : queries) {
            // Extend/shrink window to match query
            while (curL > q.l) add(--curL);
            while (curR < q.r) add(++curR);
            while (curL < q.l) remove(curL++);
            while (curR > q.r) remove(curR--);
            
            answers[q.idx] = currentAnswer;
        }
        
        return answers;
    }
};

// Example 2: Range sum query (trivial with Mo's, better with prefix sum)
// But demonstrates the pattern
class MoSum {
    int n, blockSize;
    std::vector<int> arr;
    long long currentSum;
    
    void add(int pos) { currentSum += arr[pos]; }
    void remove(int pos) { currentSum -= arr[pos]; }
    
public:
    MoSum(const std::vector<int>& arr) 
        : n(arr.size()), blockSize(std::sqrt(n)), arr(arr), currentSum(0) {}
    
    std::vector<long long> solve(std::vector<std::pair<int,int>>& queries) {
        int q = queries.size();
        std::vector<std::tuple<int,int,int>> qs; // l, r, idx
        for (int i = 0; i < q; i++) {
            qs.push_back({queries[i].first, queries[i].second, i});
        }
        
        std::sort(qs.begin(), qs.end(), [this](auto& a, auto& b) {
            int ba = std::get<0>(a) / blockSize;
            int bb = std::get<0>(b) / blockSize;
            if (ba != bb) return ba < bb;
            return std::get<1>(a) < std::get<1>(b);
        });
        
        std::vector<long long> answers(q);
        int curL = 0, curR = -1;
        
        for (auto& [l, r, idx] : qs) {
            while (curL > l) add(--curL);
            while (curR < r) add(++curR);
            while (curL < l) remove(curL++);
            while (curR > r) remove(curR--);
            answers[idx] = currentSum;
        }
        
        return answers;
    }
};

int main() {
    // Problem: Count distinct elements in each range
    std::vector<int> arr = {1, 2, 1, 3, 2, 1, 4, 3};
    
    MoAlgorithm mo(arr);
    mo.addQuery(0, 4); // [1,2,1,3,2] → 3 distinct
    mo.addQuery(2, 5); // [1,3,2,1] → 3 distinct
    mo.addQuery(0, 7); // All → 4 distinct
    
    auto answers = mo.solve();
    
    std::cout << "Distinct count queries:\n";
    for (int i = 0; i < (int)answers.size(); i++) {
        std::cout << "Query " << i << ": " << answers[i] << "\n";
    }
    
    return 0;
}
```

### Block Size Optimization

The standard block size is √N, but this can be tuned:

| Block Size | Time Complexity | Notes |
|---|---|---|
| √N | O((N+Q)√N) | Standard |
| N/√Q | O(N√Q) | Better when Q << N |
| N^(2/3) | O(N^(2/3) × Q^(1/2)) | For Mo's with updates |

```cpp
// Optimized block size
int blockSize = std::max(1, (int)(n / std::sqrt(queries.size())));
```

### Mo's Algorithm Variants

| Variant | Modification | Use Case |
|---|---|---|
| Standard | Static array | Range queries |
| With updates | 3D Mo's (l, r, time) | Array updates + queries |
| On trees | Euler Tour flattening | Subtree/path queries |
| Hilbert order | Hilbert curve sorting | Better cache performance |

### Mo's on Trees

Convert tree queries to array queries using Euler Tour:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

// Answer queries: "count distinct values on path from u to v"
// Use Euler Tour + Mo's algorithm

struct EulerTourMo {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> val;
    std::vector<int> tin, tout, euler;
    std::vector<int> depth;
    
    void dfs(int u, int p) {
        tin[u] = timer;
        euler[timer] = u;
        timer++;
        for (int v : adj[u]) {
            if (v != p) {
                depth[v] = depth[u] + 1;
                dfs(v, u);
            }
        }
        tout[u] = timer;
        euler[timer] = u;
        timer++;
    }
    
    EulerTourMo(int n) : n(n), timer(0), adj(n), val(n), 
                          tin(n), tout(n), euler(2 * n), depth(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void build(int root) {
        depth[root] = 0;
        dfs(root, -1);
    }
};

int main() {
    std::cout << "Mo's on trees: flatten tree with Euler Tour,\n"
              << "then apply standard Mo's on the flat array.\n"
              << "Path queries require special handling with tin/tout.\n";
    
    return 0;
}
```

---

## 62.2 DSU on Tree (Small-to-Large Merging)

**DSU on Tree** (also called Sack or Small-to-Large merging) answers subtree queries efficiently by always merging the smaller set into the larger one.

### Key Idea

For each node, maintain a multiset of values in its subtree. When merging children, always merge the smaller set into the larger one. This ensures each element is moved at most O(log n) times.

### When to Use

- Subtree queries (e.g., "how many distinct values in subtree of u?")
- Problems where we need to aggregate information from subtrees
- When a direct DFS with sets would be O(n²)

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <map>
#include <algorithm>

class DSUonTree {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> val;
    std::vector<int> sz;
    std::vector<int> heavy; // Heavy child
    std::map<int, int> cnt; // Count of each value in current subtree
    std::vector<int> answer;
    
    int dfsSize(int u, int p) {
        sz[u] = 1;
        int maxSize = 0;
        for (int v : adj[u]) {
            if (v != p) {
                int subSize = dfsSize(v, u);
                sz[u] += subSize;
                if (subSize > maxSize) {
                    maxSize = subSize;
                    heavy[u] = v;
                }
            }
        }
        return sz[u];
    }
    
    void add(int u, int p) {
        cnt[val[u]]++;
        for (int v : adj[u]) {
            if (v != p) add(v, u);
        }
    }
    
    void remove(int u, int p) {
        cnt[val[u]]--;
        if (cnt[val[u]] == 0) cnt.erase(val[u]);
        for (int v : adj[u]) {
            if (v != p) remove(v, u);
        }
    }
    
    void dfs(int u, int p, bool keep) {
        // Process light children first (and clear their data)
        for (int v : adj[u]) {
            if (v != p && v != heavy[u]) {
                dfs(v, u, false);
            }
        }
        
        // Process heavy child (keep its data)
        if (heavy[u] != -1) {
            dfs(heavy[u], u, true);
        }
        
        // Add light children's data
        for (int v : adj[u]) {
            if (v != p && v != heavy[u]) {
                add(v, u);
            }
        }
        
        // Add current node
        cnt[val[u]]++;
        
        // Answer query for subtree of u
        // Example: count distinct values
        answer[u] = cnt.size();
        
        // If not keeping, clear all data
        if (!keep) {
            remove(u, p);
        }
    }
    
public:
    DSUonTree(int n) : n(n), adj(n), val(n), sz(n), heavy(n, -1), answer(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    std::vector<int> solve(int root, const std::vector<int>& values) {
        val = values;
        dfsSize(root, -1);
        dfs(root, -1, false);
        return answer;
    }
};

int main() {
    //       0(1)
    //      / \
    //    1(2) 2(1)
    //    /|   |
    //  3(3) 4(2) 5(3)
    
    DSUonTree dsu(6);
    dsu.addEdge(0, 1);
    dsu.addEdge(0, 2);
    dsu.addEdge(1, 3);
    dsu.addEdge(1, 4);
    dsu.addEdge(2, 5);
    
    std::vector<int> values = {1, 2, 1, 3, 2, 3};
    
    auto answer = dsu.solve(0, values);
    
    std::cout << "Distinct values in each subtree:\n";
    for (int i = 0; i < 6; i++) {
        std::cout << "Subtree " << i << ": " << answer[i] << " distinct\n";
    }
    
    return 0;
}
```

### Complexity Analysis

| Step | Time | Notes |
|---|---|---|
| dfsSize | O(n) | Standard tree DFS |
| Each `add` call | O(size of subtree) | But each node added O(log n) times |
| Total | O(n log n) | Small-to-large guarantee |

---

## 62.3 Offline LCA (Tarjan's Algorithm)

**Tarjan's Offline LCA** uses DSU to answer all LCA queries in O(n α(n)) total time.

### Algorithm

1. DFS the tree
2. When returning from a subtree, union all nodes in that subtree
3. For each query (u, v): after both u and v are visited, LCA(u, v) = find(u) (or find(v))

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class OfflineLCA {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<std::vector<std::pair<int, int>>> queries; // queries[u] = {(v, queryIdx)}
    std::vector<int> parent, rank_;
    std::vector<bool> visited;
    std::vector<int> ancestor;
    std::vector<int> answer;
    
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    
    void unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return;
        if (rank_[x] < rank_[y]) std::swap(x, y);
        parent[y] = x;
        if (rank_[x] == rank_[y]) rank_[x]++;
    }
    
    void dfs(int u, int p) {
        parent[u] = u;
        ancestor[u] = u;
        visited[u] = true;
        
        for (int v : adj[u]) {
            if (v != p) {
                dfs(v, u);
                unite(u, v);
                ancestor[find(u)] = u;
            }
        }
        
        // Answer all queries involving u
        for (auto& [v, idx] : queries[u]) {
            if (visited[v]) {
                answer[idx] = ancestor[find(v)];
            }
        }
    }
    
public:
    OfflineLCA(int n) : n(n), adj(n), queries(n), parent(n), 
                         rank_(n, 0), visited(n, false), ancestor(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void addQuery(int u, int v, int idx) {
        queries[u].push_back({v, idx});
        queries[v].push_back({u, idx});
    }
    
    std::vector<int> solve(int root, int numQueries) {
        answer.resize(numQueries);
        dfs(root, -1);
        return answer;
    }
};

int main() {
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    
    OfflineLCA lca(6);
    lca.addEdge(0, 1);
    lca.addEdge(0, 2);
    lca.addEdge(1, 3);
    lca.addEdge(1, 4);
    lca.addEdge(2, 5);
    
    lca.addQuery(3, 4, 0); // LCA(3, 4) = 1
    lca.addQuery(3, 5, 1); // LCA(3, 5) = 0
    lca.addQuery(4, 5, 2); // LCA(4, 5) = 0
    lca.addQuery(3, 2, 3); // LCA(3, 2) = 0
    
    auto answers = lca.solve(0, 4);
    
    std::cout << "LCA queries:\n";
    for (int i = 0; i < 4; i++) {
        std::cout << "Query " << i << ": LCA = " << answers[i] << "\n";
    }
    
    return 0;
}
```

### Complexity

| Aspect | Value |
|---|---|
| Time | O((N + Q) α(N)) ≈ O(N + Q) |
| Space | O(N + Q) |
| Constraint | All queries known in advance |

---

## 62.4 Offline Connectivity

Process a sequence of edge additions and deletions, answering connectivity queries. This is challenging online but can be solved offline using **divide and conquer on time**.

### Approach

1. Build a segment tree over time
2. Each edge exists during a time interval → add it to O(log T) segment tree nodes
3. DFS the segment tree, maintaining a DSU with rollback
4. At leaves (query times), answer the connectivity query

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class DSUWithRollback {
    std::vector<int> parent, rank_;
    std::vector<std::tuple<int, int, int, int>> history; // x, y, rankX, rankY
    
public:
    DSUWithRollback(int n) : parent(n), rank_(n, 0) {
        for (int i = 0; i < n; i++) parent[i] = i;
    }
    
    int find(int x) {
        while (parent[x] != x) x = parent[x];
        return x;
    }
    
    bool unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        
        if (rank_[x] < rank_[y]) std::swap(x, y);
        history.push_back({x, y, rank_[x], rank_[y]});
        parent[y] = x;
        if (rank_[x] == rank_[y]) rank_[x]++;
        return true;
    }
    
    int snapshot() { return history.size(); }
    
    void rollback(int snap) {
        while ((int)history.size() > snap) {
            auto [x, y, rx, ry] = history.back();
            history.pop_back();
            parent[x] = x;
            parent[y] = y;
            rank_[x] = rx;
            rank_[y] = ry;
        }
    }
};

int main() {
    std::cout << "Offline connectivity with DSU rollback:\n"
              << "- Build segment tree over time intervals\n"
              << "- DFS segment tree with DSU rollback\n"
              << "- Answer queries at leaves\n\n";
    
    // Example: 4 nodes, edges added/removed over time
    // Time 0: add edge (0,1)
    // Time 1: add edge (1,2)
    // Time 2: query: is 0 connected to 2?
    // Time 3: remove edge (0,1)
    // Time 4: query: is 0 connected to 2?
    
    DSUWithRollback dsu(4);
    dsu.unite(0, 1);
    dsu.unite(1, 2);
    
    std::cout << "After adding (0,1) and (1,2):\n";
    std::cout << "0 connected to 2: " << (dsu.find(0) == dsu.find(2)) << "\n";
    
    int snap = dsu.snapshot();
    dsu.rollback(snap);
    
    std::cout << "\nAfter rollback:\n";
    std::cout << "0 connected to 2: " << (dsu.find(0) == dsu.find(2)) << "\n";
    
    return 0;
}
```

---

## 62.5 Offline Query Processing

### General Strategy

Many problems become easier when queries are processed in a specific order rather than the given order.

### Techniques

| Technique | Idea | Example |
|---|---|---|
| Sort by endpoint | Process queries by right endpoint | Range mode, range distinct |
| Sort by value | Process elements by value | K-th smallest in range |
| Mo's order | Block-based sorting | Any incremental range query |
| Reverse order | Process backwards | Deletion → addition |
| Time-based | Divide and conquer on time | Dynamic connectivity |

### Example: K-th Smallest in Range (Offline)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

// Using persistent segment tree approach (offline with coordinate compression)
// For pure offline: sort queries by value and use BIT

struct Query {
    int l, r, k, idx;
};

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    int n = arr.size();
    
    // Coordinate compression
    std::vector<int> sorted = arr;
    std::sort(sorted.begin(), sorted.end());
    sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
    
    auto compress = [&](int x) {
        return std::lower_bound(sorted.begin(), sorted.end(), x) - sorted.begin();
    };
    
    std::cout << "Coordinate compression:\n";
    for (int i = 0; i < n; i++) {
        std::cout << arr[i] << " -> " << compress(arr[i]) << "\n";
    }
    
    // Offline approach: binary search + BIT for each query
    // Or: sort queries by answer value and use BIT
    
    std::cout << "\nOffline k-th smallest uses persistent segment tree\n"
              << "or parallel binary search with BIT.\n";
    
    return 0;
}
```

---

## 62.6 Offline vs Online Algorithms

### Comparison

| Aspect | Offline | Online |
|---|---|---|
| Query knowledge | All queries known upfront | Queries arrive one by one |
| Flexibility | Can reorder for efficiency | Must answer immediately |
| Data structures | Can preprocess globally | Must maintain incrementally |
| Typical advantage | Better asymptotic or practical | More general/applicable |

### When to Choose Offline

1. **All queries available at start**: No streaming requirement
2. **Reordering improves complexity**: Mo's algorithm, sorting by endpoint
3. **Global preprocessing helps**: Building segment tree over time
4. **DSU with rollback needed**: Dynamic connectivity

### When to Choose Online

1. **Interactive/streaming**: Queries arrive over time
2. **Updates interleaved with queries**: Data changes between queries
3. **Real-time requirements**: Must answer immediately
4. **No preprocessing possible**: Unknown future queries

### Hybrid Approaches

Many problems benefit from a hybrid approach:
- **Online with lazy updates**: Maintain data structure, update lazily
- **Batch processing**: Buffer queries, process in batches
- **Incremental preprocessing**: Build structure as queries arrive

## 62.7 Offline Algorithm Design Patterns

### Pattern 1: Sort and Sweep

When queries have a natural ordering that allows incremental processing:

```
1. Sort queries by one dimension
2. Maintain a data structure (BIT, segment tree, etc.)
3. Process queries in order, updating structure incrementally
4. Answer each query using current structure state
```

**Example**: "Count inversions in each query range" → sort queries by right endpoint, use BIT to count inversions incrementally.

### Pattern 2: Divide and Conquer on Time

When elements have "active intervals" (added at time t1, removed at time t2):

```
1. Build segment tree over time [0, T)
2. Each element active during [t1, t2) is added to O(log T) nodes
3. DFS the segment tree:
   - At each node, add all elements stored there
   - Recurse to children
   - After children, rollback (undo additions)
4. At leaves (query times), answer using current state
```

**Example**: Dynamic connectivity, offline range updates.

### Pattern 3: Parallel Binary Search

When the answer can be binary searched, and feasibility can be checked offline:

```
1. For each query, maintain search range [lo, hi]
2. While any query has lo < hi:
   a. Set mid = (lo + hi) / 2 for each query
   b. Group queries by their mid value
   c. Check feasibility for all queries at once
   d. Update lo/hi based on feasibility
```

**Example**: "What is the minimum k such that..." for multiple queries.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Parallel binary search example:
// For each query [l, r], find the minimum value k such that
// the subarray arr[l..r] has at least k distinct elements
// (This is a simplified demonstration)

int main() {
    std::cout << "Parallel Binary Search Pattern:\n";
    std::cout << "1. Maintain [lo, hi] for each query\n";
    std::cout << "2. Binary search all queries simultaneously\n";
    std::cout << "3. Group by mid, check feasibility in batch\n";
    std::cout << "4. Update ranges, repeat until converged\n\n";
    
    std::cout << "Time: O((N + Q) log N log(max_answer))\n";
    std::cout << "Often faster than individual binary searches.\n";
    
    return 0;
}
```

## Summary

| Technique | Time | Key Idea | Best For |
|---|---|---|---|
| Mo's Algorithm | O((N+Q)√N) | Sort queries, sliding window | Static range queries |
| DSU on Tree | O(N log N) | Small-to-large merging | Subtree queries |
| Offline LCA | O((N+Q)α(N)) | Tarjan's DSU-based | Multiple LCA queries |
| Offline Connectivity | O(N log²N) | Segment tree + DSU rollback | Dynamic connectivity |
| Query reordering | Problem-dependent | Process in optimal order | Various |
| Sort and Sweep | Problem-dependent | Sort + incremental DS | Range queries |
| D&C on Time | O(N log²N) | Segment tree over time | Active intervals |
| Parallel BS | O(N log²N) | Batch binary search | Multiple feasibility checks |
