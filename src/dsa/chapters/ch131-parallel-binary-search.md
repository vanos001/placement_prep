# Chapter 131: Parallel Binary Search

## Prerequisites
- Binary search
- Offline algorithms
- Basic data structures (prefix sums, segment trees, DSU)

## Interview Frequency: ★★
## Google, Amazon — advanced algorithmic techniques

---

## 131.1 What Is Parallel Binary Search?

**Parallel Binary Search** (PBS) is an optimization technique that runs binary search
on **multiple queries simultaneously**, batching the feasibility checks to exploit
shared structure.

**Core Idea:** Instead of solving Q independent binary searches (each costing O(N log N)
for feasibility), PBS groups queries by their midpoints and checks feasibility for
all queries in a single pass, achieving O((N + Q) log N × feasibility_check_cost).

### When Does It Apply?

PBS works when:
1. Multiple queries each need binary search
2. The feasibility check has a **shared structure** that can be evaluated in batch
3. The feasibility check is monotonic: if `feasible(mid)` is true, then
   `feasible(mid')` is true for all mid' ≤ mid

**Common applications:**
- Finding minimum spanning tree with edge weight constraint
- Offline minimum/maximum queries with threshold
- Dynamic connectivity queries
- Problems where "is answer ≤ X?" can be checked efficiently in batch

---

## 131.2 Motivation: Why Not Just Binary Search Each Query?

Consider Q queries, each requiring binary search over range [1, N].

**Naive approach:** For each query, binary search independently.
- Time: O(Q × N × feasibility_cost) — if feasibility check is O(N)

**PBS approach:** All queries binary search together.
- Time: O((N + Q) × feasibility_cost × log N)

The key insight: if the feasibility check for all queries at a given "mid" value
can be done in a single sweep of the data, we save a factor of Q.

### Analogy

Imagine you have 100 people each trying to find a specific temperature on a
thermometer. Instead of each person independently checking temperatures (100 × 100
readings = 10,000), you sweep the thermometer once and report to everyone
simultaneously (100 readings for 100 people = 100).

---

## 131.3 The Algorithm

### Setup

- Q queries, each searching for the minimum value v in [lo, hi] such that
  condition(v) is true
- `feasible(v, query)` returns true/false
- Feasibility can be checked in batch: given a set of queries all checking the
  same v, we can evaluate them efficiently

### PBS Steps

```
1. Initialize: for each query i, lo[i] = 0, hi[i] = N
2. While any lo[i] < hi[i]:
   a. For each query with lo[i] < hi[i]:
      mid[i] = (lo[i] + hi[i]) / 2
      Group query i into bucket[mid[i]]
   b. For each value v from 0 to N:
      Process all queries in bucket[v]:
        - Check feasibility for these queries at value v
        - If feasible: hi[i] = mid[i]
        - Else: lo[i] = mid[i] + 1
3. Answer for query i = lo[i] (= hi[i])
```

### Key Insight

The "processing" in step 2b must be incremental. As we sweep from v=0 to v=N,
we build up state incrementally. Each query checks whether the current state
(at value v) satisfies its condition.

This is similar to **offline processing** or **Mo's algorithm** — we move a
"pointer" through the data and answer queries at various positions.

---

## 131.4 Detailed Example: Minimum Weight Edge in Path

**Problem:** Given a weighted tree with N nodes and Q queries of the form
"(u, v, k) — find the minimum weight edge on the path from u to v such that
at least k edges on the path have weight ≤ w."

Simplified version: **For each query, find the minimum w such that the path
from u to v contains at least k edges with weight ≤ w.**

**Approach:**
- Binary search on w for each query
- Feasibility: "does the path from u to v have ≥ k edges with weight ≤ w?"
- PBS: sweep w from small to large, incrementally adding edges with weight ≤ w
- Use LCA to count edges on paths

**Walkthrough:**

```
Tree edges: (1-2, w=3), (2-3, w=7), (1-4, w=1), (4-5, w=5)
Queries: (2,5,2), (3,4,1)

PBS iteration 1:
  Query 1: mid = 3 (searching [1,5])
  Query 2: mid = 3

  Sweep w from 1 to 3:
    w=1: add edge (1-4, w=1). Count edges ≤1 on path 2→5: 0. Count on 3→4: 0.
    w=2: no edges with weight 2.
    w=3: add edge (1-2, w=3). Count edges ≤3 on path 2→5: 1. Count on 3→4: 1.

  Query 1: need ≥2 edges ≤3 on path 2→5. Found 1. Not feasible → lo = 4.
  Query 2: need ≥1 edge ≤3 on path 3→4. Found 1. Feasible → hi = 3.

PBS iteration 2:
  Query 1: mid = 4 (searching [4,5])
  Query 2: already converged (lo=hi=3)

  Sweep w from 1 to 4:
    w=4: no new edges.
  Count edges ≤4 on path 2→5: still 1. Not feasible → lo = 5.

PBS iteration 3:
  Query 1: mid = 5 (searching [5,5])
  Sweep to w=5: add edge (4-5, w=5). Count on 2→5: 2. Feasible → hi = 5.

Final answers: Query 1 = 5, Query 2 = 3.
```

---

## 131.5 Implementation in C++

### General PBS Framework

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// General parallel binary search framework
// Queries: each query has a condition that depends on a threshold value
// We binary search on the threshold for all queries simultaneously

struct Query {
    int id;
    int lo, hi, mid;
    // Add query-specific fields here
};

class ParallelBinarySearch {
    int n;  // Range of threshold values [0, n)
    int q;  // Number of queries
    std::vector<Query> queries;

public:
    ParallelBinarySearch(int n, int q) : n(n), q(q) {
        queries.resize(q);
        for (int i = 0; i < q; i++) {
            queries[i] = {i, 0, n, -1};
        }
    }

    // Override this: check if query is feasible at threshold value v
    // Called in batch for all queries with the same mid
    virtual bool isFeasible(int queryId, int v) = 0;

    // Override this: called when processing threshold value v
    // Use this to update incremental state
    virtual void process(int v) {}

    std::vector<int> solve() {
        bool changed = true;
        while (changed) {
            changed = false;

            // Group queries by mid
            std::vector<std::vector<int>> buckets(n + 1);
            for (int i = 0; i < q; i++) {
                if (queries[i].lo < queries[i].hi) {
                    queries[i].mid = (queries[i].lo + queries[i].hi) / 2;
                    buckets[queries[i].mid].push_back(i);
                    changed = true;
                }
            }

            if (!changed) break;

            // Sweep through threshold values
            for (int v = 0; v <= n; v++) {
                process(v);  // Update state for threshold v
                for (int idx : buckets[v]) {
                    if (isFeasible(queries[idx].id, v)) {
                        queries[idx].hi = queries[idx].mid;
                    } else {
                        queries[idx].lo = queries[idx].mid + 1;
                    }
                }
            }
        }

        std::vector<int> answers(q);
        for (int i = 0; i < q; i++)
            answers[queries[i].id] = queries[i].lo;
        return answers;
    }
};
```

### Concrete Example: Minimum Prefix Sum Threshold

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// For each query, find minimum k such that prefix_sum[0..k] >= target
std::vector<int> parallelBinarySearch(const std::vector<long long>& prefix,
                                       const std::vector<long long>& targets) {
    int n = prefix.size();
    int q = targets.size();
    std::vector<int> lo(q, 0), hi(q, n - 1), ans(q, -1);

    bool changed = true;
    while (changed) {
        changed = false;
        // Group queries by mid
        std::vector<std::vector<int>> buckets(n);
        for (int i = 0; i < q; i++) {
            if (lo[i] <= hi[i]) {
                int mid = (lo[i] + hi[i]) / 2;
                buckets[mid].push_back(i);
                changed = true;
            }
        }

        // Process in order, checking feasibility
        for (int mid = 0; mid < n; mid++) {
            for (int idx : buckets[mid]) {
                if (prefix[mid] >= targets[idx]) {
                    ans[idx] = mid;
                    hi[idx] = mid - 1;
                } else {
                    lo[idx] = mid + 1;
                }
            }
        }
    }

    return ans;
}

int main() {
    std::vector<long long> prefix = {1, 3, 6, 10, 15, 21, 28, 36};
    std::vector<long long> targets = {5, 10, 20, 30};

    auto ans = parallelBinarySearch(prefix, targets);

    for (int i = 0; i < (int)targets.size(); i++)
        std::cout << "Target " << targets[i] << ": first index with sum >= target = "
                  << ans[i] << "\n";

    return 0;
}
```

### MST-Based PBS: Minimum Weight Edge to Connect Queries

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Problem: Given a graph with weighted edges and queries (u, v, k),
// find the minimum weight w such that u and v are connected using
// only edges with weight <= w, with at least k edges on the path.

// DSU for incremental connectivity
struct DSU {
    std::vector<int> parent, rank;
    DSU(int n) : parent(n), rank(n, 0) {
        for (int i = 0; i < n; i++) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    void unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return;
        if (rank[x] < rank[y]) std::swap(x, y);
        parent[y] = x;
        if (rank[x] == rank[y]) rank[x]++;
    }
    bool connected(int x, int y) { return find(x) == find(y); }
};

int main() {
    int n = 5;  // nodes
    int m = 6;  // edges
    // Edges: (u, v, weight), 0-indexed
    std::vector<std::tuple<int,int,int>> edges = {
        {0,1,3}, {1,2,7}, {0,3,1}, {3,4,5}, {1,4,4}, {2,4,6}
    };
    std::sort(edges.begin(), edges.end(),
              [](auto& a, auto& b) { return std::get<2>(a) < std::get<2>(b); });

    // Queries: (u, v)
    std::vector<std::pair<int,int>> queries = {{1,4}, {2,3}, {0,4}};
    int q = queries.size();

    // PBS: find minimum edge weight to connect each query pair
    int lo[3] = {0, 0, 0}, hi[3] = {m-1, m-1, m-1};
    int ans[3] = {-1, -1, -1};

    bool changed = true;
    while (changed) {
        changed = false;
        std::vector<std::vector<int>> buckets(m);
        for (int i = 0; i < q; i++) {
            if (lo[i] <= hi[i]) {
                int mid = (lo[i] + hi[i]) / 2;
                buckets[mid].push_back(i);
                changed = true;
            }
        }

        DSU dsu(n);
        for (int e = 0; e < m; e++) {
            auto [u, v, w] = edges[e];
            dsu.unite(u, v);
            for (int idx : buckets[e]) {
                auto [qu, qv] = queries[idx];
                if (dsu.connected(qu, qv)) {
                    ans[idx] = w;
                    hi[idx] = e - 1;
                } else {
                    lo[idx] = e + 1;
                }
            }
        }
    }

    for (int i = 0; i < q; i++)
        std::cout << "Query (" << queries[i].first << "," << queries[i].second
                  << "): min weight = " << ans[i] << "\n";

    return 0;
}
```

---

## 131.6 Implementation in Python

```python
def parallel_binary_search(n, queries, check_batch):
    """
    General PBS framework.

    Args:
        n: Range of threshold values [0, n)
        queries: List of query objects
        check_batch: Function(threshold, query_ids) -> dict {id: is_feasible}

    Returns:
        List of answers, one per query
    """
    q = len(queries)
    lo = [0] * q
    hi = [n - 1] * q
    ans = [-1] * q

    changed = True
    while changed:
        changed = False
        buckets = [[] for _ in range(n)]

        for i in range(q):
            if lo[i] <= hi[i]:
                mid = (lo[i] + hi[i]) // 2
                buckets[mid].append(i)
                changed = True

        if not changed:
            break

        # Sweep through threshold values
        for v in range(n):
            if not buckets[v]:
                continue
            results = check_batch(v, buckets[v])
            for idx in buckets[v]:
                if results[idx]:
                    ans[idx] = v
                    hi[idx] = v - 1
                else:
                    lo[idx] = v + 1

    return [lo[i] for i in range(q)]


# Example: For each query, find minimum index where prefix_sum >= target
def prefix_sum_example():
    prefix = [1, 3, 6, 10, 15, 21, 28, 36]
    targets = [5, 10, 20, 30]
    n = len(prefix)

    def check_batch(threshold, query_ids):
        return {idx: prefix[threshold] >= targets[idx] for idx in query_ids}

    answers = parallel_binary_search(n, list(range(len(targets))), check_batch)

    for i, target in enumerate(targets):
        print(f"Target {target}: first index with sum >= target = {answers[i]}")

prefix_sum_example()
```

---

## 131.7 Implementation in Java

```java
import java.util.*;

public class ParallelBinarySearch {

    static int[] parallelBinarySearch(int n, long[] prefix, long[] targets) {
        int q = targets.length;
        int[] lo = new int[q];
        int[] hi = new int[q];
        int[] ans = new int[q];
        Arrays.fill(hi, n - 1);
        Arrays.fill(ans, -1);

        boolean changed = true;
        while (changed) {
            changed = false;
            List<List<Integer>> buckets = new ArrayList<>();
            for (int i = 0; i < n; i++) buckets.add(new ArrayList<>());

            for (int i = 0; i < q; i++) {
                if (lo[i] <= hi[i]) {
                    int mid = (lo[i] + hi[i]) / 2;
                    buckets.get(mid).add(i);
                    changed = true;
                }
            }

            if (!changed) break;

            for (int mid = 0; mid < n; mid++) {
                for (int idx : buckets.get(mid)) {
                    if (prefix[mid] >= targets[idx]) {
                        ans[idx] = mid;
                        hi[idx] = mid - 1;
                    } else {
                        lo[idx] = mid + 1;
                    }
                }
            }
        }

        return lo;
    }

    public static void main(String[] args) {
        long[] prefix = {1, 3, 6, 10, 15, 21, 28, 36};
        long[] targets = {5, 10, 20, 30};

        int[] ans = parallelBinarySearch(prefix.length, prefix, targets);

        for (int i = 0; i < targets.length; i++)
            System.out.println("Target " + targets[i] +
                ": first index with sum >= target = " + ans[i]);
    }
}
```

---

## 131.8 Complexity Analysis

| Approach | Time | Space |
|---|---|---|
| Naive (Q independent binary searches) | O(Q × N × feasibility_cost) | O(Q) |
| Parallel Binary Search | **O((N + Q) × feasibility_cost × log N)** | O(N + Q) |

**Breakdown:**
- log N iterations of the outer loop
- Each iteration: O(N) to sweep + O(Q) to check queries
- Feasibility check cost × (N + Q) per iteration

### When PBS Wins

PBS is most beneficial when:
1. **Q is large** (many queries)
2. **Feasibility check is expensive** but can be done incrementally
3. **The sweep builds shared state** (e.g., DSU, segment tree)

If feasibility check is O(1), PBS doesn't save much over naive.
If feasibility check is O(log N) with incremental updates, PBS saves a lot.

---

## 131.9 Comparison with Other Techniques

| Technique | Time | When to Use |
|---|---|---|
| Independent binary search | O(Q × N × feasibility) | Simple, few queries |
| Parallel binary search | O((N+Q) × feasibility × log N) | Many queries, batch feasibility |
| Mo's algorithm | O((N+Q) × √N × feasibility) | Offline queries on array |
| Offline dynamic connectivity | O(N log²N) | Graph connectivity queries |

### PBS vs. Mo's Algorithm

- **Mo's:** Orders queries to minimize pointer movement. Good for array queries.
- **PBS:** Groups queries by binary search midpoint. Good for threshold-based queries.
- Both are **offline** techniques (require knowing all queries upfront).

---

## 131.10 Advanced Example: PBS with DSU Rollback

**Problem:** Given a graph that gains edges over time, and queries asking
"are u and v connected at time t?", find the earliest time each query pair
becomes connected.

**PBS approach:**
- Binary search on time t for each query
- Feasibility: "are u and v connected after adding edges 1..t?"
- Sweep t from 0 to T, incrementally adding edges
- Use **DSU with rollback** to reset state between PBS iterations

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct DSUWithRollback {
    std::vector<int> parent, rank;
    std::vector<std::tuple<int,int,int>> history;  // (node, old_parent, old_rank)

    DSUWithRollback(int n) : parent(n), rank(n, 0) {
        for (int i = 0; i < n; i++) parent[i] = i;
    }

    int find(int x) {
        while (parent[x] != x) x = parent[x];
        return x;
    }

    void unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) {
            history.push_back({-1, -1, -1});  // No change
            return;
        }
        if (rank[x] < rank[y]) std::swap(x, y);
        history.push_back({y, parent[y], rank[x]});
        parent[y] = x;
        if (rank[x] == rank[y]) rank[x]++;
    }

    void rollback() {
        if (history.empty()) return;
        auto [node, oldParent, oldRank] = history.back();
        history.pop_back();
        if (node == -1) return;
        parent[node] = oldParent;
        // Note: rank rollback requires tracking which node's rank changed
    }

    bool connected(int x, int y) { return find(x) == find(y); }
};

int main() {
    int n = 4;
    // Edges added at times 1, 2, 3
    std::vector<std::pair<int,int>> edges = {
        {0,1}, {1,2}, {2,3}, {0,3}
    };
    int t = edges.size();

    // Queries: when do these pairs become connected?
    std::vector<std::pair<int,int>> queries = {{0,2}, {1,3}, {0,3}};
    int q = queries.size();

    int lo[3] = {0,0,0}, hi[3] = {t,t,t};
    int ans[3] = {-1,-1,-1};

    bool changed = true;
    while (changed) {
        changed = false;
        std::vector<std::vector<int>> buckets(t + 1);
        for (int i = 0; i < q; i++) {
            if (lo[i] <= hi[i]) {
                int mid = (lo[i] + hi[i]) / 2;
                buckets[mid].push_back(i);
                changed = true;
            }
        }

        DSUWithRollback dsu(n);
        for (int time = 0; time <= t; time++) {
            if (time > 0) {
                auto [u, v] = edges[time - 1];
                dsu.unite(u, v);
            }
            for (int idx : buckets[time]) {
                auto [u, v] = queries[idx];
                if (dsu.connected(u, v)) {
                    ans[idx] = time;
                    hi[idx] = time - 1;
                } else {
                    lo[idx] = time + 1;
                }
            }
        }
    }

    for (int i = 0; i < q; i++)
        std::cout << "Query (" << queries[i].first << "," << queries[i].second
                  << "): connected at time " << ans[i] << "\n";

    return 0;
}
```

---

## 131.11 Practice Problems

1. **SPOJ NKLEAVES:** Minimum cost to collect leaves (PBS + DP)
2. **Codeforces — Offline queries with DSU:** Find connectivity time
3. **Minimum spanning tree queries:** For each query, find MST weight with edge constraint
4. **K-th smallest in range:** PBS on value with BIT/segment tree feasibility
5. **Dynamic connectivity:** PBS with DSU rollback

---

## 131.12 Interview Questions

1. **Q:** What is parallel binary search?
   **A:** An optimization that runs binary search on multiple queries simultaneously,
   grouping queries by midpoint and batching feasibility checks to exploit shared
   structure. Reduces time from O(Q × N) to O((N + Q) × log N).

2. **Q:** When is PBS better than independent binary search?
   **A:** When you have many queries (large Q), feasibility checks can be done
   incrementally (e.g., sweeping through values), and the feasibility check
   benefits from batch processing.

3. **Q:** What's the difference between PBS and Mo's algorithm?
   **A:** PBS groups queries by binary search midpoint; Mo's orders queries to
   minimize array pointer movement. PBS is for threshold-based queries; Mo's
   is for range queries on arrays.

4. **Q:** Can PBS be used online?
   **A:** No. PBS requires knowing all queries upfront to group them by midpoint.
   It's an offline technique.

---

## 131.13 Related Topics

| Topic | Chapter | Connection |
|---|---|---|
| Binary Search | Ch. 04 | Core technique being parallelized |
| Offline Algorithms | Ch. 145 | PBS is an offline technique |
| DSU | Ch. 35 | Common feasibility structure |
| Mo's Algorithm | Ch. 130 | Alternative offline technique |
| Alien Trick | Ch. 116 | Another binary search optimization |

---

## Summary

| Aspect | Value |
|---|---|
| Time | O((N + Q) log N × feasibility_check) |
| Benefit | Batch feasibility checks across queries |
| Best for | Multiple binary searches with shared structure |
| Requirement | Monotone feasibility, offline queries |
| Common structures | DSU, segment tree, BIT |

**Key Takeaway:** Parallel Binary Search transforms Q independent binary searches
into a single coordinated search, batching feasibility checks for massive speedups.
It's the go-to technique when you have many threshold-based queries with shared
incremental structure.
