# Expanded Arrays and Techniques



## Prerequisites

- Arrays and prefix sums
- Basic sorting and binary search
- Familiarity with time complexity analysis

## Interview Frequency

★★★★★ — Array problems are the most common category in interviews. These advanced techniques appear frequently at top-tier companies.

## Companies

Google, Meta, Amazon, Microsoft, Apple, Bloomberg, Goldman Sachs, Citadel, Two Sigma, Uber, Netflix, Stripe, Airbnb — essentially every company that asks algorithmic questions.

---

## Overview

Arrays are the most fundamental data structure, but the techniques built on top of them are remarkably diverse. This chapter covers advanced array techniques that go beyond basic sorting and two pointers.

| Technique | Key Idea | Time Complexity |
|-----------|----------|----------------|
| Difference Array | Range updates in O(1) | O(n + q) |
| Coordinate Compression | Map large ranges to small indices | O(n log n) |
| Prefix XOR | Subarray XOR queries | O(n + q) |
| Circular Arrays | Modular indexing tricks | Varies |
| Offline Queries | Reorder queries for optimal processing | Varies |
| Mo's Algorithm | Sqrt decomposition for range queries | O((n+q)√n) |
| Kadane Variants | Maximum subarray variations | O(n) |
| Subarray Contribution | Count each element's contribution | O(n) |
| Range Updates + Queries | Difference array + prefix sum | O(n + q) |
| Matrix Prefix Sums | 2D inclusion-exclusion | O(nm + q) |

---

## 1. Difference Array

### Problem

Given an array of *n* elements and *q* range update queries of the form "add *val* to all elements in [l, r]," apply all updates and report the final array.

### Naive Approach

Each update takes O(r - l + 1). Total: O(q × n) — too slow.

### Difference Array Technique

Create a difference array `d` where `d[i] = a[i] - a[i-1]`. A range update [l, r] with value *val* becomes two point updates: `d[l] += val` and `d[r+1] -= val`. After all updates, compute prefix sums of `d` to get the final array.

```cpp
#include <vector>
#include <iostream>

class DifferenceArray {
    std::vector<long long> diff;
public:
    explicit DifferenceArray(int n) : diff(n + 2, 0) {}

    // Add val to range [l, r] (0-indexed, inclusive)
    void range_add(int l, int r, long long val) {
        diff[l] += val;
        diff[r + 1] -= val;
    }

    // Build the final array
    std::vector<long long> build() {
        std::vector<long long> result(diff.size() - 1);
        result[0] = diff[0];
        for (int i = 1; i < (int)result.size(); ++i)
            result[i] = result[i - 1] + diff[i];
        return result;
    }
};

int main() {
    int n = 7;
    DifferenceArray da(n);

    // Initial array: all zeros
    // Update [1, 5] by +3
    da.range_add(1, 5, 3);
    // Update [2, 4] by +2
    da.range_add(2, 4, 2);
    // Update [0, 3] by +1
    da.range_add(0, 3, 1);

    auto result = da.build();
    // Expected: [1, 4, 6, 6, 5, 3, 0]
    for (int i = 0; i < n; ++i)
        std::cout << result[i] << " ";
    std::cout << "\n";
}
```

### Dry Run

```
Initial diff: [0, 0, 0, 0, 0, 0, 0, 0, 0]

range_add(1, 5, 3): diff[1] += 3, diff[6] -= 3
diff: [0, 3, 0, 0, 0, 0, -3, 0, 0]

range_add(2, 4, 2): diff[2] += 2, diff[5] -= 2
diff: [0, 3, 2, 0, 0, -2, -3, 0, 0]

range_add(0, 3, 1): diff[0] += 1, diff[4] -= 1
diff: [1, 3, 2, 0, -1, -2, -3, 0, 0]

Prefix sums: [1, 4, 6, 6, 5, 3, 0] ✓
```

### 2D Difference Array

For 2D range updates on a matrix, extend the concept:

```cpp
#include <vector>
#include <iostream>

class DiffArray2D {
    int rows, cols;
    std::vector<std::vector<long long>> diff;
public:
    DiffArray2D(int r, int c) : rows(r), cols(c),
        diff(r + 2, std::vector<long long>(c + 2, 0)) {}

    // Add val to submatrix [r1,c1] to [r2,c2] (inclusive, 0-indexed)
    void range_add(int r1, int c1, int r2, int c2, long long val) {
        diff[r1][c1] += val;
        diff[r1][c2 + 1] -= val;
        diff[r2 + 1][c1] -= val;
        diff[r2 + 1][c2 + 1] += val;
    }

    std::vector<std::vector<long long>> build() {
        std::vector<std::vector<long long>> result(rows, std::vector<long long>(cols));
        // Prefix sum along rows
        for (int i = 0; i < rows; ++i)
            for (int j = 0; j < cols; ++j)
                diff[i][j] += (j > 0 ? diff[i][j - 1] : 0);
        // Prefix sum along columns
        for (int j = 0; j < cols; ++j)
            for (int i = 0; i < rows; ++i)
                diff[i][j] += (i > 0 ? diff[i - 1][j] : 0);
        for (int i = 0; i < rows; ++i)
            for (int j = 0; j < cols; ++j)
                result[i][j] = diff[i][j];
        return result;
    }
};

int main() {
    DiffArray2D da(4, 4);
    da.range_add(1, 1, 2, 2, 5); // Add 5 to submatrix [1,1]..[2,2]
    da.range_add(0, 0, 3, 3, 1); // Add 1 to entire matrix
    auto result = da.build();
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j)
            std::cout << result[i][j] << " ";
        std::cout << "\n";
    }
    // 1 1 1 1
    // 1 6 6 1
    // 1 6 6 1
    // 1 1 1 1
}
```

### Interview Application

Difference arrays are the go-to technique when you have many range update queries and need to report the final state. They convert O(q × n) to O(n + q).

---

## 2. Coordinate Compression

### Problem

You have values in a large range (e.g., 1 to 10^9) but only *n* distinct values. Map them to [0, n) while preserving relative order.

### Implementation

```cpp
#include <vector>
#include <algorithm>
#include <iostream>

class CoordinateCompressor {
    std::vector<int> sorted_vals;
public:
    void add(int val) { sorted_vals.push_back(val); }

    void build() {
        std::sort(sorted_vals.begin(), sorted_vals.end());
        sorted_vals.erase(std::unique(sorted_vals.begin(), sorted_vals.end()),
                          sorted_vals.end());
    }

    // Returns compressed index (0-based)
    int compress(int val) const {
        return std::lower_bound(sorted_vals.begin(), sorted_vals.end(), val)
               - sorted_vals.begin();
    }

    // Returns original value from compressed index
    int decompress(int idx) const { return sorted_vals[idx]; }

    int size() const { return sorted_vals.size(); }
};

int main() {
    std::vector<int> values = {1000000000, 5, 1000000000, 1, 5, 3};

    CoordinateCompressor cc;
    for (int v : values) cc.add(v);
    cc.build();

    std::cout << "Compressed values:\n";
    for (int v : values)
        std::cout << v << " -> " << cc.compress(v) << "\n";
    // 1000000000 -> 4
    // 5 -> 3
    // 1000000000 -> 4
    // 1 -> 0
    // 5 -> 3
    // 3 -> 2
}
```

### Interview Application

Coordinate compression is essential when you need to use values as array indices but the range is too large. Common in:
- 2D geometry problems (sweep line algorithms)
- Range queries with large values
- Counting sort on large values
- Mo's algorithm preprocessing

---

## 3. Prefix XOR

### Problem

Given an array, answer queries: "What is the XOR of elements in [l, r]?"

### Technique

Compute prefix XOR: `px[i] = a[0] ^ a[1] ^ ... ^ a[i-1]`. Then XOR of [l, r] = `px[r+1] ^ px[l]`.

```cpp
#include <vector>
#include <iostream>

class PrefixXOR {
    std::vector<int> px; // px[0] = 0, px[i] = a[0]^...^a[i-1]
public:
    explicit PrefixXOR(const std::vector<int>& a) : px(a.size() + 1, 0) {
        for (int i = 0; i < (int)a.size(); ++i)
            px[i + 1] = px[i] ^ a[i];
    }

    // XOR of a[l..r] (inclusive, 0-indexed)
    int query(int l, int r) const {
        return px[r + 1] ^ px[l];
    }
};

int main() {
    std::vector<int> a = {3, 7, 2, 5, 1, 8, 4};
    PrefixXOR px(a);

    std::cout << "XOR of [1, 4]: " << px.query(1, 4) << "\n";
    // 7 ^ 2 ^ 5 ^ 1 = 1
    std::cout << "XOR of [0, 6]: " << px.query(0, 6) << "\n";
    // 3^7^2^5^1^8^4 = 0

    // Application: Find subarray with XOR = k
    // Using prefix XOR: px[j] ^ px[i] = k → px[i] = px[j] ^ k
    int k = 5;
    std::unordered_set<int> seen;
    seen.insert(0); // px[0] = 0
    int count = 0;
    for (int j = 1; j <= (int)a.size(); ++j) {
        int target = px.query(0, j - 1) ^ k; // px[j] ^ k
        if (seen.count(target)) ++count;
        seen.insert(px.query(0, j - 1));
    }
    std::cout << "Subarrays with XOR = " << k << ": " << count << "\n";
}
```

### Interview Application

Prefix XOR is the XOR analogue of prefix sums. Key applications:
- Subarray XOR queries
- Finding subarrays with a given XOR
- XOR-based encoding/decoding
- Nim game analysis

---

## 4. Circular Arrays

### Problem

An array is treated as circular — after the last element comes the first. How do we implement this efficiently?

### Implementation Tricks

```cpp
#include <vector>
#include <iostream>

class CircularArray {
    std::vector<int> data;
    int start = 0;
public:
    explicit CircularArray(int n) : data(n, 0) {}

    int& operator[](int idx) {
        return data[(start + idx % (int)data.size() + (int)data.size()) % (int)data.size()];
    }

    void rotate(int k) {
        start = (start - k % (int)data.size() + (int)data.size()) % (int)data.size();
    }
};

// Modular arithmetic helpers
int mod(int a, int m) {
    return (a % m + m) % m;
}

// Circular next/prev
int next_idx(int i, int n) { return (i + 1) % n; }
int prev_idx(int i, int n) { return (i - 1 + n) % n; }

int main() {
    // Circular buffer implementation
    CircularArray ca(5);
    for (int i = 0; i < 5; ++i) ca[i] = i * 10; // [0, 10, 20, 30, 40]

    ca.rotate(2); // Rotate right by 2
    for (int i = 0; i < 5; ++i) std::cout << ca[i] << " ";
    std::cout << "\n"; // 30 40 0 10 20

    // Circular Kadane (see Kadane Variants section)
    std::vector<int> arr = {5, -3, 5};
    int n = arr.size();
    int max_wrap = 0, max_no_wrap = 0;
    // ... see Kadane Variants for the full algorithm
}
```

### Interview Application

Circular arrays appear in:
- Circular buffers (producer-consumer queues)
- Rotated array search
- Circular maximum subarray (Kadane variant)
- Sliding window on circular data

---

## 5. Offline Queries

### Problem

Sometimes processing queries in the order they're given is suboptimal. By reordering (offline processing), you can achieve better complexity.

### Example: Offline Range Minimum Queries

```cpp
#include <vector>
#include <algorithm>
#include <iostream>
#include <climits>

// Answer "min in [l, r]" queries offline using a segment tree
// This is simpler with a segment tree, but the key insight is:
// sorting queries by right endpoint allows incremental processing

struct Query {
    int l, r, idx;
};

int main() {
    std::vector<int> a = {3, 1, 4, 1, 5, 9, 2, 6};
    int n = a.size();

    std::vector<Query> queries = {
        {0, 4, 0}, {2, 7, 1}, {1, 3, 2}, {5, 7, 3}
    };

    // Sort by right endpoint
    std::sort(queries.begin(), queries.end(),
              [](const Query& a, const Query& b) { return a.r < b.r; });

    // Process incrementally (simplified — in practice use segment tree or sparse table)
    std::vector<int> answers(queries.size());
    // For demonstration, just compute directly
    for (auto& q : queries) {
        int mn = INT_MAX;
        for (int i = q.l; i <= q.r; ++i)
            mn = std::min(mn, a[i]);
        answers[q.idx] = mn;
    }

    for (int i = 0; i < (int)queries.size(); ++i)
        std::cout << "Query " << i << ": min = " << answers[i] << "\n";
    // Query 0: min = 1 (range [0,4]: 3,1,4,1,5)
    // Query 1: min = 1 (range [2,7]: 4,1,5,9,2,6)
    // Query 2: min = 1 (range [1,3]: 1,4,1)
    // Query 3: min = 2 (range [5,7]: 9,2,6)
}
```

### When to Use Offline Processing

| Scenario | Technique |
|----------|-----------|
| Many range queries, can reorder | Sort by endpoint, incremental processing |
| Queries depend on "current state" | Process in optimal order |
| Queries have a parameter to sort on | Sweep line |

---

## 6. Mo's Algorithm

### Problem

Given an array and *q* range queries (e.g., "count distinct elements in [l, r]"), answer all queries efficiently.

### Key Idea

Sort queries in a specific order so that the left and right pointers move at most O(n√q) total. Partition the array into √n blocks. Sort queries by block of left endpoint, then by right endpoint within each block.

### Implementation

```cpp
#include <vector>
#include <algorithm>
#include <cmath>
#include <iostream>

struct Query {
    int l, r, idx, block;
};

int main() {
    std::vector<int> a = {1, 2, 1, 3, 2, 1, 4, 3};
    int n = a.size();
    int block_size = std::sqrt(n);

    std::vector<Query> queries = {
        {0, 4, 0, 0}, {1, 5, 1, 0}, {2, 7, 2, 0}, {0, 7, 3, 0}
    };

    for (auto& q : queries) q.block = q.l / block_size;

    std::sort(queries.begin(), queries.end(), [&](const Query& a, const Query& b) {
        if (a.block != b.block) return a.block < b.block;
        // Within same block, alternate order for even/odd blocks (optimization)
        return (a.block % 2 == 0) ? a.r < b.r : a.r > b.r;
    });

    // Current range and answer
    int cur_l = 0, cur_r = -1;
    int distinct = 0;
    std::vector<int> freq(5, 0); // freq of each value

    auto add = [&](int idx) {
        if (freq[a[idx]] == 0) ++distinct;
        ++freq[a[idx]];
    };
    auto remove = [&](int idx) {
        --freq[a[idx]];
        if (freq[a[idx]] == 0) --distinct;
    };

    std::vector<int> answers(queries.size());

    for (auto& q : queries) {
        while (cur_l > q.l) add(--cur_l);
        while (cur_r < q.r) add(++cur_r);
        while (cur_l < q.l) remove(cur_l++);
        while (cur_r > q.r) remove(cur_r--);
        answers[q.idx] = distinct;
    }

    for (int i = 0; i < (int)queries.size(); ++i)
        std::cout << "Query " << i << ": distinct = " << answers[i] << "\n";
    // Query 0 [0,4]: {1,2,1,3,2} → distinct = 3
    // Query 1 [1,5]: {2,1,3,2,1} → distinct = 3
    // Query 2 [2,7]: {1,3,2,1,4,3} → distinct = 4
    // Query 3 [0,7]: {1,2,1,3,2,1,4,3} → distinct = 4
}
```

### Complexity Analysis

- Sorting queries: O(q log q)
- Processing: Each query moves pointers by O(√n) amortized, total O(q√n)
- **Overall: O((n + q)√n)**

### Interview Application

Mo's algorithm is useful when:
- Queries are offline (can be reordered)
- You can add/remove elements from the current range efficiently
- The answer can be maintained incrementally

Common Mo's applications: count distinct, mode, frequency of most frequent, sum of unique elements.

---

## 7. Kadane Variants

### Standard Kadane (Maximum Subarray Sum)

```cpp
#include <vector>
#include <algorithm>
#include <iostream>

int kadane(const std::vector<int>& a) {
    int max_ending_here = a[0];
    int max_so_far = a[0];
    for (int i = 1; i < (int)a.size(); ++i) {
        max_ending_here = std::max(a[i], max_ending_here + a[i]);
        max_so_far = std::max(max_so_far, max_ending_here);
    }
    return max_so_far;
}
```

### Variant 1: Maximum Product Subarray

```cpp
int max_product_subarray(const std::vector<int>& a) {
    int max_prod = a[0];
    int cur_max = a[0], cur_min = a[0];
    for (int i = 1; i < (int)a.size(); ++i) {
        if (a[i] < 0) std::swap(cur_max, cur_min);
        cur_max = std::max(a[i], cur_max * a[i]);
        cur_min = std::min(a[i], cur_min * a[i]);
        max_prod = std::max(max_prod, cur_max);
    }
    return max_prod;
}
```

**Key insight:** Track both maximum and minimum. A negative number × minimum = new maximum.

### Variant 2: Circular Maximum Subarray

The maximum subarray in a circular array is either:
1. A standard maximum subarray (doesn't wrap around), OR
2. The total sum minus the minimum subarray (wraps around)

```cpp
int circular_max_subarray(const std::vector<int>& a) {
    int max_sum = a[0], cur_max = a[0];
    int min_sum = a[0], cur_min = a[0];
    int total = a[0];

    for (int i = 1; i < (int)a.size(); ++i) {
        // Standard Kadane for max
        cur_max = std::max(a[i], cur_max + a[i]);
        max_sum = std::max(max_sum, cur_max);

        // Kadane for min
        cur_min = std::min(a[i], cur_min + a[i]);
        min_sum = std::min(min_sum, cur_min);

        total += a[i];
    }

    // Edge case: if all elements are negative, max_sum is the answer
    // (min_sum == total, so total - min_sum == 0, which is wrong)
    if (min_sum == total) return max_sum;

    return std::max(max_sum, total - min_sum);
}

int main() {
    std::vector<int> a1 = {5, -3, 5};
    std::cout << "Circular max: " << circular_max_subarray(a1) << "\n"; // 10 (5 + -3 + 5 wraps)

    std::vector<int> a2 = {8, -1, 3, 4};
    std::cout << "Circular max: " << circular_max_subarray(a2) << "\n"; // 15 (8 + -1 + 3 + 4)

    std::vector<int> a3 = {-3, -2, -1};
    std::cout << "Circular max: " << circular_max_subarray(a3) << "\n"; // -1 (single element)
}
```

### Variant 3: Maximum Subarray Sum with Length Constraint

```cpp
#include <deque>
#include <climits>

// Maximum subarray sum of length exactly k
int max_subarray_sum_k(const std::vector<int>& a, int k) {
    int n = a.size();
    if (n < k) return INT_MIN;
    std::vector<long long> prefix(n + 1, 0);
    for (int i = 0; i < n; ++i) prefix[i + 1] = prefix[i] + a[i];

    // For each ending position j, we want max(prefix[j] - prefix[i]) where j - i >= k
    // → min(prefix[i]) for i <= j - k
    long long best = LLONG_MIN;
    long long min_prefix = 0; // prefix[0]
    for (int j = k; j <= n; ++j) {
        if (j >= k) {
            best = std::max(best, prefix[j] - min_prefix);
        }
        min_prefix = std::min(min_prefix, prefix[j - k + 1]);
    }
    return (int)best;
}
```

---

## 8. Subarray Contribution Techniques

### Problem

Count something over all subarrays by computing each element's contribution.

### Example: Sum of All Subarray Sums

Element `a[i]` appears in `(i + 1) * (n - i)` subarrays (choose left endpoint in [0, i], right endpoint in [i, n-1]).

```cpp
#include <vector>
#include <iostream>

long long sum_of_all_subarray_sums(const std::vector<int>& a) {
    long long total = 0;
    int n = a.size();
    for (int i = 0; i < n; ++i) {
        // a[i] appears in (i+1) * (n-i) subarrays
        total += (long long)a[i] * (i + 1) * (n - i);
    }
    return total;
}

int main() {
    std::vector<int> a = {1, 2, 3};
    // Subarrays: [1], [2], [3], [1,2], [2,3], [1,2,3]
    // Sums: 1 + 2 + 3 + 3 + 5 + 6 = 20
    std::cout << "Sum of all subarray sums: " << sum_of_all_subarray_sums(a) << "\n"; // 20
}
```

### Example: Count Subarrays Where Element is Maximum

```cpp
#include <vector>
#include <stack>
#include <iostream>

long long count_subarrays_where_max(const std::vector<int>& a) {
    int n = a.size();
    std::vector<int> left(n), right(n);
    std::stack<int> st;

    // For each element, find how far left/right it's the strict maximum
    // left[i] = distance to previous greater element
    for (int i = 0; i < n; ++i) {
        while (!st.empty() && a[st.top()] < a[i]) st.pop();
        left[i] = st.empty() ? i + 1 : i - st.top();
        st.push(i);
    }
    while (!st.empty()) st.pop();

    // right[i] = distance to next greater or equal element
    for (int i = n - 1; i >= 0; --i) {
        while (!st.empty() && a[st.top()] <= a[i]) st.pop();
        right[i] = st.empty() ? n - i : st.top() - i;
        st.push(i);
    }

    long long total = 0;
    for (int i = 0; i < n; ++i)
        total += (long long)a[i] * left[i] * right[i];
    return total;
}

int main() {
    std::vector<int> a = {1, 3, 2};
    std::cout << "Contribution sum: " << count_subarrays_where_max(a) << "\n";
    // a[0]=1: 1 subarray where it's max ([1]) → 1*1*1 = 1
    // a[1]=3: 3 subarrays ([3], [1,3], [3,2], [1,3,2]) → 3*2*2 = 12
    //   Actually: left=2 (positions 0,1), right=2 (positions 1,2)
    //   Contribution: 3 * 2 * 2 = 12
    // a[2]=2: 1 subarray ([2]) → 2*1*1 = 2
    // Total: 1 + 12 + 2 = 15
    // Wait, let me recheck: subarray sums of maxes:
    // [1]→1, [3]→3, [2]→2, [1,3]→3, [3,2]→3, [1,3,2]→3 → 1+3+2+3+3+3=15 ✓
}
```

### Interview Application

Contribution techniques convert "for each subarray, compute X" (O(n²)) into "for each element, compute its contribution to X" (O(n) or O(n log n)). The key is finding the number of subarrays where a given element is the max/min/median/etc.

---

## 9. Range Updates + Range Queries

### Combine Difference Array with Prefix Sum

To support both range updates and range queries efficiently, use a **Binary Indexed Tree (Fenwick Tree)** or **Segment Tree**.

```cpp
#include <vector>
#include <iostream>

class BIT {
    std::vector<long long> tree;
    int n;
public:
    BIT(int size) : n(size), tree(size + 1, 0) {}

    void update(int i, long long val) {
        for (++i; i <= n; i += i & (-i))
            tree[i] += val;
    }

    long long query(int i) const {
        long long sum = 0;
        for (++i; i > 0; i -= i & (-i))
            sum += tree[i];
        return sum;
    }

    long long range_query(int l, int r) const {
        return query(r) - (l > 0 ? query(l - 1) : 0);
    }
};

// Range update + range query using two BITs
class RangeBIT {
    BIT b1, b2;
    int n;
public:
    RangeBIT(int size) : n(size), b1(size), b2(size) {}

    // Add val to range [l, r]
    void range_update(int l, int r, long long val) {
        b1.update(l, val);
        b1.update(r + 1, -val);
        b2.update(l, val * (l - 1));
        b2.update(r + 1, -val * r);
    }

    // Prefix sum of [0, i]
    long long prefix_query(int i) const {
        return b1.query(i) * i - b2.query(i);
    }

    // Range sum of [l, r]
    long long range_query(int l, int r) const {
        return prefix_query(r) - (l > 0 ? prefix_query(l - 1) : 0);
    }
};

int main() {
    RangeBIT rbit(10);
    rbit.range_update(1, 5, 3); // Add 3 to [1, 5]
    rbit.range_update(3, 7, 2); // Add 2 to [3, 7]

    std::cout << "Sum [0, 9]: " << rbit.range_query(0, 9) << "\n";
    // 0 + 3 + 3 + 5 + 5 + 5 + 2 + 2 + 0 + 0 = 25
    std::cout << "Sum [2, 4]: " << rbit.range_query(2, 4) << "\n";
    // 3 + 5 + 5 = 13
}
```

---

## 10. Matrix Prefix Sums

### 2D Prefix Sum

Compute prefix sums for a 2D matrix so that any submatrix sum can be answered in O(1).

```cpp
#include <vector>
#include <iostream>

class MatrixPrefixSum {
    std::vector<std::vector<long long>> ps;
    int rows, cols;
public:
    MatrixPrefixSum(const std::vector<std::vector<int>>& mat)
        : rows(mat.size()), cols(mat[0].size()),
          ps(rows + 1, std::vector<long long>(cols + 1, 0)) {
        for (int i = 0; i < rows; ++i)
            for (int j = 0; j < cols; ++j)
                ps[i + 1][j + 1] = mat[i][j] + ps[i][j + 1]
                                 + ps[i + 1][j] - ps[i][j];
    }

    // Sum of submatrix [r1, c1] to [r2, c2] (inclusive, 0-indexed)
    long long query(int r1, int c1, int r2, int c2) const {
        return ps[r2 + 1][c2 + 1] - ps[r1][c2 + 1]
             - ps[r2 + 1][c1] + ps[r1][c1];
    }
};

int main() {
    std::vector<std::vector<int>> mat = {
        {1, 2, 3, 4},
        {5, 6, 7, 8},
        {9, 10, 11, 12},
        {13, 14, 15, 16}
    };

    MatrixPrefixSum mps(mat);
    std::cout << "Sum [0,0]-[1,1]: " << mps.query(0, 0, 1, 1) << "\n"; // 1+2+5+6=14
    std::cout << "Sum [1,1]-[3,3]: " << mps.query(1, 1, 3, 3) << "\n"; // 6+7+8+10+11+12+14+15+16=99
    std::cout << "Sum [0,0]-[3,3]: " << mps.query(0, 0, 3, 3) << "\n"; // 136
}
```

### Inclusion-Exclusion Formula

```
Sum(r1, c1, r2, c2) = P[r2+1][c2+1] - P[r1][c2+1] - P[r2+1][c1] + P[r1][c1]
```

Where P is the 2D prefix sum array.

---

## Comparison Table

| Technique | Update | Query | Space | Use Case |
|-----------|--------|-------|-------|----------|
| Difference Array | O(1) range | O(n) to build | O(n) | Many range updates, report final state |
| Prefix XOR | None | O(1) | O(n) | Subarray XOR queries |
| BIT | O(log n) point | O(log n) prefix | O(n) | Point updates + range queries |
| Segment Tree | O(log n) range | O(log n) range | O(n) | Range updates + range queries |
| Mo's Algorithm | O(1) add/remove | O(√n) amortized | O(n) | Offline range queries |
| Matrix Prefix Sum | None | O(1) submatrix | O(nm) | Static 2D range sum queries |

---

## Design Decisions

### When NOT to Use Difference Array

- When you need to query intermediate states (use BIT or segment tree)
- When updates are point updates (use BIT directly)
- When the array is dynamic (elements added/removed)

### When NOT to Use Mo's Algorithm

- When queries must be answered online (in order)
- When add/remove is expensive (not O(1))
- When n or q is very large and O((n+q)√n) is too slow

### When NOT to Use Coordinate Compression

- When values fit in a reasonable range already
- When you need to preserve actual values (though you can decompress)
- When the overhead of sorting + binary search isn't justified

---

## Summary

These array techniques are the building blocks for solving complex interview problems efficiently. The key patterns:

1. **Transform the representation** (difference array, coordinate compression, prefix sums)
2. **Reorder the work** (offline queries, Mo's algorithm)
3. **Count contributions** (each element's contribution to the answer)
4. **Decompose the problem** (circular → linear, 2D → 1D)

Master these and you'll find that many "hard" array problems reduce to known patterns.
