# Chapter 65: Searching Expanded

## Prerequisites

- Binary search
- Basic graph theory (for binary lifting)
- Sorting algorithms
- Divide and conquer

## Interview Frequency: ★★★★

Advanced searching techniques appear frequently in interviews. **Binary Lifting** is extremely popular at **Google**, **Meta**, and **Amazon** for LCA and k-th ancestor problems. **Meet in the Middle** is a favorite for subset sum variants. **Exponential Search** and **Interpolation Search** test understanding of binary search variants. **Fractional Cascading** is a theoretical gem that appears in research-oriented interviews.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Exponential Search | ★★★ | Amazon, Google | Easy-Medium |
| Interpolation Search | ★★ | Google, Amazon | Easy-Medium |
| Meet in the Middle | ★★★ | Google, ByteDance | Medium |
| Fractional Cascading | ★ | Research labs | Hard |
| Binary Lifting | ★★★★★ | All companies | Medium |

---

## 65.1 Exponential Search

**Exponential Search** finds the range where the target might exist, then uses binary search within that range. It's ideal when the array size is unknown or unbounded.

### Algorithm

1. Start with range [0, 1]
2. Double the range: [1, 2], [2, 4], [4, 8], ...
3. Until the end of range exceeds the target
4. Binary search within the found range

### When to Use

- Searching in unbounded/infinite sorted arrays
- When the array size is unknown
- When the target is closer to the beginning

### Time Complexity

O(log n) where n is the position of the target (not the array size).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Standard binary search
int binarySearch(const std::vector<int>& arr, int lo, int hi, int target) {
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

// Exponential search
int exponentialSearch(const std::vector<int>& arr, int target) {
    int n = arr.size();
    if (n == 0) return -1;
    if (arr[0] == target) return 0;
    
    // Find range
    int bound = 1;
    while (bound < n && arr[bound] <= target) {
        bound *= 2;
    }
    
    // Binary search in [bound/2, min(bound, n-1)]
    return binarySearch(arr, bound / 2, std::min(bound, n - 1), target);
}

// Unbounded binary search (for unknown size)
// Assumes arr[i] is defined for all i >= 0 and is sorted
// arr[i] = target for some i, arr[i] = INT_MAX for i >= n
int unboundedSearch(int target) {
    // Simulated function
    auto f = [](int i) -> int {
        std::vector<int> arr = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19};
        if (i < (int)arr.size()) return arr[i];
        return INT_MAX;
    };
    
    // Find upper bound
    int bound = 1;
    while (f(bound) < target) {
        bound *= 2;
    }
    
    // Binary search
    int lo = bound / 2, hi = bound;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        int val = f(mid);
        if (val == target) return mid;
        if (val < target) lo = mid + 1;
        else hi = mid - 1;
    }
    
    return -1;
}

int main() {
    std::vector<int> arr = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25};
    
    for (int target : {7, 15, 25, 100}) {
        int idx = exponentialSearch(arr, target);
        if (idx != -1) {
            std::cout << "Found " << target << " at index " << idx << "\n";
        } else {
            std::cout << target << " not found\n";
        }
    }
    
    // Unbounded search
    std::cout << "\nUnbounded search for 7: index " << unboundedSearch(7) << "\n";
    std::cout << "Unbounded search for 19: index " << unboundedSearch(19) << "\n";
    
    return 0;
}
```

### Exponential Search vs Binary Search

| Aspect | Binary Search | Exponential Search |
|---|---|---|
| Prerequisite | Know array size | Size unknown OK |
| Time | O(log n) | O(log n) |
| Best when | Target uniformly distributed | Target near beginning |
| Unbounded arrays | Not applicable | Works perfectly |

---

## 65.2 Interpolation Search

**Interpolation Search** improves on binary search for uniformly distributed data by estimating the target's position using linear interpolation.

### Key Idea

Instead of always checking the midpoint, estimate where the target would be:

```
pos = lo + ((target - arr[lo]) * (hi - lo)) / (arr[hi] - arr[lo])
```

### When to Use

- Data is uniformly distributed
- Average O(log log n) performance is possible
- Standard binary search is too slow

### When NOT to Use

- Data is not uniformly distributed (worst case O(n))
- Adversarial input

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int interpolationSearch(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    
    while (lo <= hi && target >= arr[lo] && target <= arr[hi]) {
        if (lo == hi) {
            if (arr[lo] == target) return lo;
            return -1;
        }
        
        // Interpolation formula
        int pos = lo + (int)(((double)(hi - lo) / 
                  (arr[hi] - arr[lo])) * (target - arr[lo]));
        
        if (arr[pos] == target) return pos;
        if (arr[pos] < target) lo = pos + 1;
        else hi = pos - 1;
    }
    
    return -1;
}

// Hybrid: interpolation + binary search fallback
int hybridSearch(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    int maxSteps = 2 * (int)(std::log2(arr.size()) + 1);
    
    for (int step = 0; step < maxSteps && lo <= hi; step++) {
        if (arr[lo] == target) return lo;
        if (arr[hi] == target) return hi;
        if (lo == hi) return -1;
        
        // Try interpolation
        if (target < arr[lo] || target > arr[hi]) return -1;
        
        int pos = lo + (int)(((double)(hi - lo) / 
                  (arr[hi] - arr[lo])) * (target - arr[lo]));
        
        pos = std::max(lo, std::min(hi, pos));
        
        if (arr[pos] == target) return pos;
        if (arr[pos] < target) lo = pos + 1;
        else hi = pos - 1;
    }
    
    // Fallback to binary search
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    
    return -1;
}

int main() {
    // Uniformly distributed data
    std::vector<int> uniform(1000);
    for (int i = 0; i < 1000; i++) uniform[i] = i * 3;
    
    for (int target : {0, 150, 999, 2997, 3000}) {
        int idx = interpolationSearch(uniform, target);
        if (idx != -1) {
            std::cout << "Found " << target << " at index " << idx << "\n";
        } else {
            std::cout << target << " not found\n";
        }
    }
    
    // Non-uniform data (exponential distribution)
    std::vector<int> nonUniform;
    for (int i = 0; i < 1000; i++) {
        nonUniform.push_back(i * i);
    }
    
    std::cout << "\nNon-uniform data:\n";
    for (int target : {0, 100, 250000, 998001}) {
        int idx = hybridSearch(nonUniform, target);
        if (idx != -1) {
            std::cout << "Found " << target << " at index " << idx << "\n";
        } else {
            std::cout << target << " not found\n";
        }
    }
    
    return 0;
}
```

### Search Algorithm Comparison

| Algorithm | Average | Worst | Best For |
|---|---|---|---|
| Binary Search | O(log n) | O(log n) | General sorted data |
| Interpolation Search | O(log log n) | O(n) | Uniform distribution |
| Exponential Search | O(log n) | O(log n) | Unknown size |
| Fibonacci Search | O(log n) | O(log n) | No division available |

---

## 65.3 Meet in the Middle

**Meet in the Middle** splits a problem of size n into two halves of size n/2, solves each half independently, then combines results. This reduces exponential complexity from O(2^n) to O(2^(n/2)).

### When to Use

- Subset sum, subset enumeration for n ≤ 40
- Any problem where brute force is O(2^n) but n is moderate
- Can split the problem into two independent halves

### Classic Problem: Subset Sum for n ≤ 40

Given 40 numbers, find if any subset sums to target T.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

class MeetInMiddle {
    // Generate all subset sums of arr[lo..hi]
    std::vector<long long> generateSubsetSums(const std::vector<int>& arr, 
                                                int lo, int hi) {
        int len = hi - lo;
        std::vector<long long> sums;
        
        for (int mask = 0; mask < (1 << len); mask++) {
            long long sum = 0;
            for (int i = 0; i < len; i++) {
                if (mask & (1 << i)) {
                    sum += arr[lo + i];
                }
            }
            sums.push_back(sum);
        }
        
        return sums;
    }
    
public:
    // Check if any subset sums to target
    bool hasSubsetSum(const std::vector<int>& arr, long long target) {
        int n = arr.size();
        int mid = n / 2;
        
        auto leftSums = generateSubsetSums(arr, 0, mid);
        auto rightSums = generateSubsetSums(arr, mid, n);
        
        std::sort(rightSums.begin(), rightSums.end());
        
        for (long long ls : leftSums) {
            long long need = target - ls;
            auto it = std::lower_bound(rightSums.begin(), rightSums.end(), need);
            if (it != rightSums.end() && *it == need) {
                return true;
            }
        }
        
        return false;
    }
    
    // Count subsets that sum to target
    long long countSubsetSums(const std::vector<int>& arr, long long target) {
        int n = arr.size();
        int mid = n / 2;
        
        auto leftSums = generateSubsetSums(arr, 0, mid);
        auto rightSums = generateSubsetSums(arr, mid, n);
        
        std::sort(rightSums.begin(), rightSums.end());
        
        long long count = 0;
        for (long long ls : leftSums) {
            long long need = target - ls;
            auto range = std::equal_range(rightSums.begin(), rightSums.end(), need);
            count += range.second - range.first;
        }
        
        return count;
    }
    
    // Find the subset sum closest to target
    long long closestSubsetSum(const std::vector<int>& arr, long long target) {
        int n = arr.size();
        int mid = n / 2;
        
        auto leftSums = generateSubsetSums(arr, 0, mid);
        auto rightSums = generateSubsetSums(arr, mid, n);
        
        std::sort(rightSums.begin(), rightSums.end());
        
        long long best = LLONG_MAX;
        long long bestDiff = LLONG_MAX;
        
        for (long long ls : leftSums) {
            long long need = target - ls;
            auto it = std::lower_bound(rightSums.begin(), rightSums.end(), need);
            
            if (it != rightSums.end()) {
                long long diff = std::abs(ls + *it - target);
                if (diff < bestDiff) {
                    bestDiff = diff;
                    best = ls + *it;
                }
            }
            if (it != rightSums.begin()) {
                --it;
                long long diff = std::abs(ls + *it - target);
                if (diff < bestDiff) {
                    bestDiff = diff;
                    best = ls + *it;
                }
            }
        }
        
        return best;
    }
};

int main() {
    MeetInMiddle mitm;
    
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3};
    int n = arr.size();
    
    std::cout << "Array: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";
    
    // Check subset sum
    for (long long target : {10, 15, 27, 100}) {
        bool exists = mitm.hasSubsetSum(arr, target);
        std::cout << "Subset sum " << target << ": " 
                  << (exists ? "exists" : "doesn't exist") << "\n";
    }
    
    // Count subsets
    std::cout << "\nCount of subsets summing to 15: " 
              << mitm.countSubsetSums(arr, 15) << "\n";
    
    // Closest subset sum
    std::cout << "Closest subset sum to 50: " 
              << mitm.closestSubsetSum(arr, 50) << "\n";
    
    return 0;
}
```

### Complexity

| Method | Time | Space | Max n |
|---|---|---|---|
| Brute force | O(2^n) | O(n) | ~25 |
| Meet in the Middle | O(2^(n/2) × n) | O(2^(n/2)) | ~40 |

---

## 65.4 Fractional Cascading (Overview)

**Fractional Cascading** speeds up binary search across multiple sorted arrays. Instead of doing binary search in each of k arrays (O(k log n)), it achieves O(log n + k) by creating "bridges" between arrays.

### Key Idea

1. Merge arrays pairwise, keeping pointers back to original arrays
2. After binary search in the merged array, follow pointers to find positions in all original arrays

### When to Use

- Same query value searched in multiple sorted arrays
- k binary searches would be O(k log n), fractional cascading gives O(log n + k)
- Example: Range queries in segment tree of sorted arrays

### Complexity

| Method | Preprocessing | Query | Space |
|---|---|---|---|
| k binary searches | O(n) | O(k log n) | O(n) |
| Fractional Cascading | O(n log n) | O(log n + k) | O(n log n) |

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Simplified fractional cascading demonstration
// In practice, this is used within segment tree or interval tree nodes

class FractionalCascading {
    int k; // Number of arrays
    int n; // Size of each array
    std::vector<std::vector<int>> arrays;
    std::vector<std::vector<int>> merged;
    // Pointers: for each merged array, track position in original arrays
    std::vector<std::vector<std::vector<int>>> pointers;
    
public:
    FractionalCascading(const std::vector<std::vector<int>>& input) 
        : k(input.size()), arrays(input) {
        if (k == 0) return;
        n = arrays[0].size();
        
        // Build merged arrays (simplified version)
        merged.resize(k);
        merged[k-1] = arrays[k-1];
        
        for (int i = k - 2; i >= 0; i--) {
            // Merge arrays[i] with merged[i+1]
            merged[i].resize(arrays[i].size() + merged[i+1].size());
            std::merge(arrays[i].begin(), arrays[i].end(),
                      merged[i+1].begin(), merged[i+1].end(),
                      merged[i].begin());
        }
    }
    
    // Find lower_bound of x in all arrays
    // Returns positions in each array
    std::vector<int> search(int x) {
        std::vector<int> positions(k);
        
        // Binary search in first merged array
        int pos = std::lower_bound(merged[0].begin(), merged[0].end(), x) 
                  - merged[0].begin();
        
        // In practice, follow pointers through merged arrays
        // Simplified: just do binary search in each array
        for (int i = 0; i < k; i++) {
            positions[i] = std::lower_bound(arrays[i].begin(), arrays[i].end(), x) 
                          - arrays[i].begin();
        }
        
        return positions;
    }
};

int main() {
    std::vector<std::vector<int>> arrays = {
        {1, 5, 10, 15, 20},
        {2, 7, 12, 17, 22},
        {3, 8, 13, 18, 23},
        {4, 9, 14, 19, 24}
    };
    
    FractionalCascading fc(arrays);
    
    for (int x : {8, 15, 20, 25}) {
        auto positions = fc.search(x);
        std::cout << "Search " << x << ": positions = ";
        for (int p : positions) std::cout << p << " ";
        std::cout << "\n";
    }
    
    std::cout << "\nFractional cascading achieves O(log n + k) per query\n"
              << "instead of O(k log n) for k separate binary searches.\n";
    
    return 0;
}
```

---

## 65.5 Binary Lifting

**Binary Lifting** preprocesses a tree (or DAG) to answer ancestor queries in O(log n) time. Each node stores its 2^k-th ancestor for all valid k.

### Applications

| Application | Query | Time |
|---|---|---|
| K-th ancestor | Find k-th parent of node | O(log n) |
| LCA | Lowest common ancestor | O(log n) |
| Distance on tree | dist(u, v) | O(log n) |
| Path queries | Aggregate on path | O(log n) |
| K-th ancestor on path | Combined with HLD | O(log² n) |

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class BinaryLifting {
    int n, LOG;
    std::vector<std::vector<int>> adj;
    std::vector<std::vector<int>> up; // up[v][k] = 2^k-th ancestor of v
    std::vector<int> depth;
    
public:
    BinaryLifting(int n) : n(n), adj(n), depth(n) {
        LOG = 0;
        int temp = n;
        while (temp > 0) { LOG++; temp /= 2; }
        LOG++; // Safety margin
        up.assign(n, std::vector<int>(LOG, -1));
    }
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void build(int root) {
        // DFS to set depth and parent (2^0-th ancestor)
        dfs(root, -1);
        
        // Fill up table
        for (int k = 1; k < LOG; k++) {
            for (int v = 0; v < n; v++) {
                if (up[v][k-1] != -1) {
                    up[v][k] = up[up[v][k-1]][k-1];
                }
            }
        }
    }
    
    void dfs(int u, int p) {
        up[u][0] = p;
        for (int v : adj[u]) {
            if (v != p) {
                depth[v] = depth[u] + 1;
                dfs(v, u);
            }
        }
    }
    
    // Find k-th ancestor of v
    int kthAncestor(int v, int k) {
        for (int i = 0; i < LOG; i++) {
            if ((k >> i) & 1) {
                v = up[v][i];
                if (v == -1) return -1;
            }
        }
        return v;
    }
    
    // LCA using binary lifting
    int lca(int u, int v) {
        if (depth[u] < depth[v]) std::swap(u, v);
        
        // Lift u to same depth as v
        int diff = depth[u] - depth[v];
        u = kthAncestor(u, diff);
        
        if (u == v) return u;
        
        // Binary lift both until LCA
        for (int k = LOG - 1; k >= 0; k--) {
            if (up[u][k] != up[v][k]) {
                u = up[u][k];
                v = up[v][k];
            }
        }
        
        return up[u][0];
    }
    
    // Distance between u and v
    int dist(int u, int v) {
        int l = lca(u, v);
        return depth[u] + depth[v] - 2 * depth[l];
    }
    
    // Check if u is ancestor of v
    bool isAncestor(int u, int v) {
        return lca(u, v) == u;
    }
    
    // K-th node on path from u to v
    int kthOnPath(int u, int v, int k) {
        int l = lca(u, v);
        int du = depth[u] - depth[l];
        int dv = depth[v] - depth[l];
        
        if (k <= du) {
            return kthAncestor(u, k);
        } else {
            return kthAncestor(v, du + dv - k);
        }
    }
};

int main() {
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    //       |
    //       6
    
    BinaryLifting bl(7);
    bl.addEdge(0, 1);
    bl.addEdge(0, 2);
    bl.addEdge(1, 3);
    bl.addEdge(1, 4);
    bl.addEdge(2, 5);
    bl.addEdge(4, 6);
    
    bl.build(0);
    
    // K-th ancestor
    std::cout << "2nd ancestor of 6: " << bl.kthAncestor(6, 2) << "\n"; // 1
    std::cout << "3rd ancestor of 6: " << bl.kthAncestor(6, 3) << "\n"; // 0
    
    // LCA
    std::cout << "\nLCA(3, 4) = " << bl.lca(3, 4) << "\n"; // 1
    std::cout << "LCA(3, 6) = " << bl.lca(3, 6) << "\n"; // 1
    std::cout << "LCA(3, 5) = " << bl.lca(3, 5) << "\n"; // 0
    std::cout << "LCA(6, 5) = " << bl.lca(6, 5) << "\n"; // 0
    
    // Distance
    std::cout << "\nDistance(3, 6) = " << bl.dist(3, 6) << "\n"; // 3
    std::cout << "Distance(3, 5) = " << bl.dist(3, 5) << "\n"; // 4
    
    // Ancestor check
    std::cout << "\n1 is ancestor of 6: " << bl.isAncestor(1, 6) << "\n"; // 1
    std::cout << "3 is ancestor of 6: " << bl.isAncestor(3, 6) << "\n"; // 0
    
    // K-th node on path
    std::cout << "\nPath from 3 to 5: ";
    int pathLen = bl.dist(3, 5);
    for (int k = 0; k <= pathLen; k++) {
        std::cout << bl.kthOnPath(3, 5, k) << " ";
    }
    std::cout << "\n";
    
    return 0;
}
```

### Binary Lifting on Arrays (Sparse Table)

Binary lifting can also be applied to arrays for Range Minimum Query:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

class SparseTable {
    int n, LOG;
    std::vector<std::vector<int>> table;
    
public:
    SparseTable(const std::vector<int>& arr) : n(arr.size()) {
        LOG = std::log2(n) + 1;
        table.assign(n, std::vector<int>(LOG));
        
        // Base case: intervals of length 1
        for (int i = 0; i < n; i++) table[i][0] = arr[i];
        
        // Fill table
        for (int k = 1; k < LOG; k++) {
            for (int i = 0; i + (1 << k) <= n; i++) {
                table[i][k] = std::min(table[i][k-1], 
                                       table[i + (1 << (k-1))][k-1]);
            }
        }
    }
    
    // Range minimum query in O(1)
    int query(int l, int r) {
        int len = r - l + 1;
        int k = std::log2(len);
        return std::min(table[l][k], table[r - (1 << k) + 1][k]);
    }
};

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3};
    
    SparseTable st(arr);
    
    std::cout << "Array: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";
    
    // RMQ queries
    std::cout << "Min in [0, 3]: " << st.query(0, 3) << "\n"; // 1
    std::cout << "Min in [4, 7]: " << st.query(4, 7) << "\n"; // 2
    std::cout << "Min in [0, 15]: " << st.query(0, 15) << "\n"; // 1
    
    return 0;
}
```

### Binary Lifting Complexity

| Operation | Time | Space |
|---|---|---|
| Preprocessing | O(n log n) | O(n log n) |
| K-th ancestor | O(log n) | O(1) |
| LCA | O(log n) | O(1) |
| Distance | O(log n) | O(1) |
| RMQ (sparse table) | O(n log n) preprocess | O(1) query |

---

## Summary

| Technique | Key Insight | Time | Best For |
|---|---|---|---|
| Exponential Search | Double range until found | O(log n) | Unknown size arrays |
| Interpolation Search | Estimate position by value | O(log log n) avg | Uniform distribution |
| Meet in the Middle | Split 2^n into 2×2^(n/2) | O(2^(n/2)) | Subset problems, n≤40 |
| Fractional Cascading | Bridge between sorted arrays | O(log n + k) | Multi-array search |
| Binary Lifting | Jump pointers (powers of 2) | O(log n) query | LCA, k-th ancestor |
| Sparse Table | Binary lifting on arrays | O(1) query | Static RMQ |

---

## 65.6 Uniform Cost Search

Dijkstra's algorithm without a goal test. Expands the node with lowest path cost.

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <climits>

struct State { int node; int cost; };
bool operator>(const State& a, const State& b) { return a.cost > b.cost; }

int uniformCostSearch(int n, const std::vector<std::vector<std::pair<int,int>>>& adj,
                      int start, int goal) {
    std::vector<int> dist(n, INT_MAX);
    std::priority_queue<State, std::vector<State>, std::greater<State>> pq;
    
    dist[start] = 0;
    pq.push({start, 0});
    
    while (!pq.empty()) {
        auto [u, cost] = pq.top(); pq.pop();
        if (u == goal) return cost;
        if (cost > dist[u]) continue;
        for (auto& [v, w] : adj[u]) {
            if (cost + w < dist[v]) {
                dist[v] = cost + w;
                pq.push({v, dist[v]});
            }
        }
    }
    return -1;
}

int main() {
    int n = 5;
    std::vector<std::vector<std::pair<int,int>>> adj(n);
    adj[0] = {{1, 2}, {2, 5}};
    adj[1] = {{3, 1}};
    adj[2] = {{3, 3}, {4, 1}};
    adj[3] = {{4, 2}};
    
    std::cout << "UCS cost 0 to 4: " << uniformCostSearch(n, adj, 0, 4) << "\n"; // 5
    return 0;
}
```
