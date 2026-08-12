# Chapter 76: Advanced Segment Trees

## Prerequisites

- Basic segment tree
- Lazy propagation

## Interview Frequency: ★★★

Advanced segment tree variants handle specialized queries. **Google** and **ByteDance** interviews occasionally test these for hard problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Dynamic segment tree | ★★★ | Medium | Sparse range |
| Segment tree beats | ★★ | Hard | Range min/max operations |
| Merge sort tree | ★★ | Hard | Count in range |
| 2D segment tree | ★★ | Hard | Matrix queries |

---

## 76.1 Dynamic Segment Tree

When the range is large (e.g., [0, 10^18]) but updates are few, use a dynamic segment tree that creates nodes on demand.

```cpp
#include <iostream>
#include <vector>

struct DynNode {
    long long val;
    DynNode *left, *right;
    DynNode(long long v = 0) : val(v), left(nullptr), right(nullptr) {}
};

class DynamicSegTree {
    long long lo, hi;
    DynNode* root;
    
    DynNode* update(DynNode* node, long long l, long long r, long long pos, long long val) {
        if (!node) node = new DynNode(0);
        if (l == r) {
            node->val += val;
            return node;
        }
        long long mid = l + (r - l) / 2;
        if (pos <= mid) node->left = update(node->left, l, mid, pos, val);
        else node->right = update(node->right, mid + 1, r, pos, val);
        
        node->val = 0;
        if (node->left) node->val += node->left->val;
        if (node->right) node->val += node->right->val;
        return node;
    }
    
    long long query(DynNode* node, long long l, long long r, long long ql, long long qr) {
        if (!node || qr < l || r < ql) return 0;
        if (ql <= l && r <= qr) return node->val;
        long long mid = l + (r - l) / 2;
        return query(node->left, l, mid, ql, qr) + 
               query(node->right, mid + 1, r, ql, qr);
    }
    
public:
    DynamicSegTree(long long lo, long long hi) : lo(lo), hi(hi), root(nullptr) {}
    
    void update(long long pos, long long val) {
        root = update(root, lo, hi, pos, val);
    }
    
    long long query(long long ql, long long qr) {
        return query(root, lo, hi, ql, qr);
    }
};

int main() {
    // Range [0, 10^18]
    DynamicSegTree dst(0, 1000000000000000000LL);
    
    dst.update(1000000000000000LL, 5);
    dst.update(2000000000000000LL, 10);
    dst.update(3000000000000000LL, 15);
    
    std::cout << "Sum [0, 2500000000000000]: " 
              << dst.query(0, 2500000000000000LL) << "\n"; // 15
    
    std::cout << "Sum [1500000000000000, 3500000000000000]: " 
              << dst.query(1500000000000000LL, 3500000000000000LL) << "\n"; // 25
    
    return 0;
}
```

---

## 76.2 Segment Tree Beats

Segment Tree Beats handles operations like "range chmin" (set each element to min of itself and x) efficiently.

### Key Insight

For range chmin operations, maintain the maximum value and second maximum. If the chmin value is between max and second max, we can update the max in O(1) per node.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

// Simplified: range chmin + range sum query
class SegTreeBeats {
    int n;
    std::vector<long long> maxVal, secondMax, countMax, sum;
    std::vector<long long> lazy;
    
    void pushDown(int node) {
        if (lazy[node] != LLONG_MAX) {
            applyChmin(2 * node, lazy[node]);
            applyChmin(2 * node + 1, lazy[node]);
            lazy[node] = LLONG_MAX;
        }
    }
    
    void applyChmin(int node, long long val) {
        if (maxVal[node] <= val) return;
        sum[node] -= (maxVal[node] - val) * countMax[node];
        maxVal[node] = val;
        lazy[node] = val;
    }
    
    void pullUp(int node) {
        maxVal[node] = std::max(maxVal[2 * node], maxVal[2 * node + 1]);
        sum[node] = sum[2 * node] + sum[2 * node + 1];
        
        if (maxVal[2 * node] == maxVal[2 * node + 1]) {
            countMax[node] = countMax[2 * node] + countMax[2 * node + 1];
            secondMax[node] = std::max(secondMax[2 * node], secondMax[2 * node + 1]);
        } else if (maxVal[2 * node] > maxVal[2 * node + 1]) {
            countMax[node] = countMax[2 * node];
            secondMax[node] = std::max(secondMax[2 * node], maxVal[2 * node + 1]);
        } else {
            countMax[node] = countMax[2 * node + 1];
            secondMax[node] = std::max(maxVal[2 * node], secondMax[2 * node + 1]);
        }
    }
    
public:
    SegTreeBeats(const std::vector<int>& arr) : n(arr.size()) {
        maxVal.resize(4 * n);
        secondMax.resize(4 * n);
        countMax.resize(4 * n);
        sum.resize(4 * n);
        lazy.assign(4 * n, LLONG_MAX);
        build(arr, 1, 0, n - 1);
    }
    
    void build(const std::vector<int>& arr, int node, int lo, int hi) {
        if (lo == hi) {
            maxVal[node] = sum[node] = arr[lo];
            secondMax[node] = LLONG_MIN;
            countMax[node] = 1;
            return;
        }
        int mid = (lo + hi) / 2;
        build(arr, 2 * node, lo, mid);
        build(arr, 2 * node + 1, mid + 1, hi);
        pullUp(node);
    }
    
    // Range chmin: set arr[i] = min(arr[i], val) for i in [ql, qr]
    void rangeChmin(int ql, int qr, long long val, int node = 1, int lo = 0, int hi = -1) {
        if (hi == -1) hi = n - 1;
        if (qr < lo || hi < ql || maxVal[node] <= val) return;
        if (ql <= lo && hi <= qr && secondMax[node] < val) {
            applyChmin(node, val);
            return;
        }
        pushDown(node);
        int mid = (lo + hi) / 2;
        rangeChmin(ql, qr, val, 2 * node, lo, mid);
        rangeChmin(ql, qr, val, 2 * node + 1, mid + 1, hi);
        pullUp(node);
    }
    
    long long rangeSum(int ql, int qr, int node = 1, int lo = 0, int hi = -1) {
        if (hi == -1) hi = n - 1;
        if (qr < lo || hi < ql) return 0;
        if (ql <= lo && hi <= qr) return sum[node];
        pushDown(node);
        int mid = (lo + hi) / 2;
        return rangeSum(ql, qr, 2 * node, lo, mid) + 
               rangeSum(ql, qr, 2 * node + 1, mid + 1, hi);
    }
};

int main() {
    std::vector<int> arr = {5, 3, 8, 1, 7, 2, 9, 4};
    
    SegTreeBeats st(arr);
    
    std::cout << "Initial sum [0, 7]: " << st.rangeSum(0, 7) << "\n"; // 39
    
    // Range chmin: set elements in [1, 5] to min(current, 4)
    st.rangeChmin(1, 5, 4);
    // arr becomes: {5, 3, 4, 1, 4, 2, 9, 4}
    
    std::cout << "After chmin [1,5] with 4, sum [0, 7]: " 
              << st.rangeSum(0, 7) << "\n"; // 32
    
    return 0;
}
```

---

## 76.3 Merge Sort Tree

A merge sort tree stores sorted subarrays at each node, enabling queries like "count elements in [ql,qr] that are ≤ x".

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class MergeSortTree {
    int n;
    std::vector<std::vector<int>> tree;
    
    void build(const std::vector<int>& arr, int node, int lo, int hi) {
        if (lo == hi) {
            tree[node] = {arr[lo]};
            return;
        }
        int mid = (lo + hi) / 2;
        build(arr, 2 * node, lo, mid);
        build(arr, 2 * node + 1, mid + 1, hi);
        
        tree[node].resize(tree[2 * node].size() + tree[2 * node + 1].size());
        std::merge(tree[2 * node].begin(), tree[2 * node].end(),
                   tree[2 * node + 1].begin(), tree[2 * node + 1].end(),
                   tree[node].begin());
    }
    
public:
    MergeSortTree(const std::vector<int>& arr) : n(arr.size()), tree(4 * n) {
        build(arr, 1, 0, n - 1);
    }
    
    // Count elements in [ql, qr] that are <= x
    int countLE(int ql, int qr, int x, int node = 1, int lo = 0, int hi = -1) {
        if (hi == -1) hi = n - 1;
        if (qr < lo || hi < ql) return 0;
        if (ql <= lo && hi <= qr) {
            return std::upper_bound(tree[node].begin(), tree[node].end(), x) 
                   - tree[node].begin();
        }
        int mid = (lo + hi) / 2;
        return countLE(ql, qr, x, 2 * node, lo, mid) + 
               countLE(ql, qr, x, 2 * node + 1, mid + 1, hi);
    }
};

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    
    MergeSortTree mst(arr);
    
    // Count elements <= 4 in range [0, 4]
    // arr[0..4] = {3, 1, 4, 1, 5}, elements <= 4: {3, 1, 4, 1} = 4
    std::cout << "Count <= 4 in [0, 4]: " << mst.countLE(0, 4, 4) << "\n";
    
    // Count elements <= 3 in range [2, 6]
    // arr[2..6] = {4, 1, 5, 9, 2}, elements <= 3: {1, 2} = 2
    std::cout << "Count <= 3 in [2, 6]: " << mst.countLE(2, 6, 3) << "\n";
    
    return 0;
}
```

---

## Summary

| Variant | Key Feature | Time | Space |
|---|---|---|---|
| Dynamic | Sparse range | O(log R) per op | O(Q log R) |
| Beats | Range chmin/chmax | Amortized O(log n) | O(n) |
| Merge Sort Tree | Count in range | O(log² n) | O(n log n) |
| 2D | Matrix queries | O(log² n) | O(n log n) |

---

## 76.4 Disjoint Sparse Table

Preprocess array for range queries in O(n log n) time and space, with O(1) queries. Works for any idempotent operation (min, max, gcd).

**Key idea**: For each level k, precompute answers for ranges that span the midpoint of each block of size 2^k.

---

## 76.5 Fischer-Heun RMQ

Achieves O(n) preprocessing and O(1) RMQ queries by combining:
1. **Cartesian tree reduction**: RMQ on array = LCA on Cartesian tree
2. **Block decomposition**: Split into blocks of size (log n)/2
3. **Sparse table**: On block minima for inter-block queries
4. **Type encoding**: Only O(√n) distinct block types exist, precompute all

This is the theoretical optimal for static RMQ.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

// Simplified: Sparse Table for O(1) RMQ (slightly less optimal but practical)
class SparseTable {
    int n, LOG;
    std::vector<std::vector<int>> table;
    
public:
    SparseTable(const std::vector<int>& arr) : n(arr.size()) {
        LOG = std::log2(n) + 1;
        table.assign(n, std::vector<int>(LOG));
        for (int i = 0; i < n; i++) table[i][0] = arr[i];
        for (int k = 1; k < LOG; k++)
            for (int i = 0; i + (1 << k) <= n; i++)
                table[i][k] = std::min(table[i][k-1], table[i + (1 << (k-1))][k-1]);
    }
    
    int query(int l, int r) {
        int k = std::log2(r - l + 1);
        return std::min(table[l][k], table[r - (1 << k) + 1][k]);
    }
};

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    SparseTable st(arr);
    std::cout << "RMQ [0,3]: " << st.query(0, 3) << "\n"; // 1
    std::cout << "RMQ [4,7]: " << st.query(4, 7) << "\n"; // 2
    return 0;
}
```
## 76.6 Sliding Window Aggregation

Maintain a running aggregate (sum, min, max) over a sliding window in O(1) amortized per operation using two stacks.

```cpp
#include <iostream>
#include <stack>

// Sliding window min using two stacks
class SlidingWindowMin {
    std::stack<std::pair<int,int>> in, out;
    
    void refill() {
        if (out.empty()) {
            while (!in.empty()) {
                int val = in.top().first;
                int newMin = in.top().second;
                in.pop();
                int minVal = out.empty() ? val : std::min(val, out.top().second);
                out.push({val, minVal});
            }
        }
    }
    
public:
    void push(int val) {
        int newMin = in.empty() ? val : std::min(val, in.top().second);
        in.push({val, newMin});
    }
    
    void pop() {
        refill();
        out.pop();
    }
    
    int getMin() {
        refill();
        int inMin = in.empty() ? INT_MAX : in.top().second;
        int outMin = out.empty() ? INT_MAX : out.top().second;
        return std::min(inMin, outMin);
    }
};

---

### Fischer-Heun RMQ Details

The Fischer-Heun structure achieves O(1) RMQ with O(n) preprocessing by:

1. **Block decomposition**: Split array into blocks of size (log n)/2
2. **Block RMQ**: Use sparse table on block minima → O(1) per query between blocks
3. **Intra-block RMQ**: Each block is represented by its ±1 differences relative to first element. There are only O(√n) distinct block types, so precompute all answers.

**Total**: O(n) preprocessing, O(1) query, O(n) space.

This is the theoretical optimal for static RMQ and demonstrates the connection between RMQ and LCA via Cartesian trees.

## See Also

- [Chapter 18: Segment Tree](ch18-segment-tree.md) — The foundation; master lazy propagation and basic range queries before tackling advanced variants.
- [Chapter 19: Fenwick Tree (Binary Indexed Tree)](ch19-fenwick-tree.md) — When you only need prefix sums/counts, BIT is simpler and faster in practice.
- [Chapter 20: Sparse Table](ch20-sparse-table.md) — O(1) static RMQ; the theoretical building block for many advanced techniques here.
- [Chapter 75: Persistent Data Structures](ch75-persistent-ds.md) — Persistent segment trees are one of the most important applications of persistence.
- [Chapter 102: Wavelet Trees](ch102-wavelet-trees.md) — Another powerful structure for range queries on arrays.
- [Chapter 106: Euler Tour and Tree Flattening](ch106-euler-tour-tree-flattening.md) — Converting tree problems to array problems for segment tree processing.
