# Chapter 130: Coordinate Compression

## Prerequisites
- Sorting (Chapter 14)
- Binary search (Chapter 20)
- Basic data structures (arrays, maps)

## Interview Frequency: ★★★

Coordinate compression maps large or sparse values to a compact range. It's essential for problems involving **segment trees on large ranges**, **sweep line algorithms**, and **grid compression**. Frequently tested at **Google**, **Amazon**, **Meta**, and in competitive programming.

---

## 130.1 What is Coordinate Compression?

### Definition

**Coordinate compression** (also called **value compression** or **discretization**) is a technique that maps a set of values to a contiguous range of integers [0, n-1] while preserving their relative order.

Given values `{1000000000, 5, 3, 7}`, coordinate compression maps them to:
```
3 → 0
5 → 1
7 → 2
1000000000 → 3
```

### Motivation

Many problems involve values in a huge range (e.g., 10⁹) but only a small number of distinct values (e.g., 10⁵). Creating a segment tree or array of size 10⁹ is impractical. Coordinate compression reduces the range to the actual number of distinct values.

**Example:** You have 10⁵ intervals with endpoints up to 10⁹. You need a segment tree over these intervals. Without compression, you'd need 10⁹ nodes. With compression, you need at most 2 × 10⁵ nodes.

### When to Use

| Situation | Why Compression Helps |
|---|---|
| Segment tree on large range | Reduces tree size from O(max_value) to O(n) |
| Sweep line algorithm | Compresses y-coordinates for efficient processing |
| Grid problems with sparse points | Maps to compact grid |
| Counting sort on large values | Makes counting sort feasible |
| 2D range queries | Reduces dimension after compression |

---

## 130.2 The Algorithm

### Step-by-Step

1. **Collect** all values that need compression
2. **Sort** the values
3. **Remove duplicates** (keep unique values)
4. **Map** each value to its index in the sorted unique array

### Time Complexity

| Step | Time | Space |
|---|---|---|
| Collect values | O(n) | O(n) |
| Sort | O(n log n) | O(n) |
| Remove duplicates | O(n) | O(n) |
| Build map | O(n) | O(n) |
| Each query | O(log n) or O(1) | - |

**Total:** O(n log n) preprocessing, O(log n) or O(1) per query.

---

## 130.3 C++ Implementation

### Basic Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

class CoordinateCompression {
    std::vector<int> sorted;
    std::map<int, int> compressed;
    
public:
    void add(int x) { sorted.push_back(x); }
    
    void build() {
        std::sort(sorted.begin(), sorted.end());
        sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
        for (int i = 0; i < (int)sorted.size(); i++)
            compressed[sorted[i]] = i;
    }
    
    int compress(int x) { return compressed[x]; }
    int decompress(int idx) { return sorted[idx]; }
    int size() { return sorted.size(); }
};

int main() {
    std::vector<int> arr = {1000000000, 5, 1000000000, 3, 5, 7, 3};
    
    CoordinateCompression cc;
    for (int x : arr) cc.add(x);
    cc.build();
    
    std::cout << "Compressed values:\n";
    for (int x : arr) std::cout << x << " -> " << cc.compress(x) << "\n";
    std::cout << "Compact range: [0, " << cc.size() - 1 << "]\n";
    
    return 0;
}
```

### Using Binary Search (No Map)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class CoordinateCompressionBS {
    std::vector<int> sorted;
    
public:
    void add(int x) { sorted.push_back(x); }
    
    void build() {
        std::sort(sorted.begin(), sorted.end());
        sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
    }
    
    int compress(int x) {
        return std::lower_bound(sorted.begin(), sorted.end(), x) - sorted.begin();
    }
    
    int decompress(int idx) { return sorted[idx]; }
    int size() { return sorted.size(); }
};
```

### Practical Example: Segment Tree on Compressed Coordinates

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class CompressedSegmentTree {
    std::vector<int> tree;
    int n;
    
public:
    CompressedSegmentTree(int size) : n(size), tree(4 * size, 0) {}
    
    void update(int node, int start, int end, int idx, int val) {
        if (start == end) {
            tree[node] += val;
            return;
        }
        int mid = (start + end) / 2;
        if (idx <= mid)
            update(2 * node, start, mid, idx, val);
        else
            update(2 * node + 1, mid + 1, end, idx, val);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }
    
    int query(int node, int start, int end, int l, int r) {
        if (r < start || end < l) return 0;
        if (l <= start && end <= r) return tree[node];
        int mid = (start + end) / 2;
        return query(2 * node, start, mid, l, r) +
               query(2 * node + 1, mid + 1, end, l, r);
    }
};

int main() {
    // Problem: Count points in intervals
    // Points: {100, 200, 300, 400, 500}
    // Query: How many points in [150, 350]?
    
    std::vector<int> points = {100, 200, 300, 400, 500};
    std::vector<int> queries = {150, 350};
    
    // Collect all values to compress
    std::vector<int> all_values;
    for (int p : points) all_values.push_back(p);
    for (int q : queries) all_values.push_back(q);
    
    // Compress
    std::sort(all_values.begin(), all_values.end());
    all_values.erase(std::unique(all_values.begin(), all_values.end()), all_values.end());
    
    auto compress = [&](int x) {
        return std::lower_bound(all_values.begin(), all_values.end(), x) - all_values.begin();
    };
    
    // Build segment tree on compressed coordinates
    CompressedSegmentTree st(all_values.size());
    for (int p : points)
        st.update(1, 0, all_values.size() - 1, compress(p), 1);
    
    // Query
    int l = compress(150);
    int r = compress(350);
    std::cout << "Points in [150, 350]: " << st.query(1, 0, all_values.size() - 1, l, r) << "\n";
    
    return 0;
}
```

---

## 130.4 Python Implementation

```python
from typing import List, Dict
from bisect import bisect_left

class CoordinateCompression:
    """Compress large/sparse values to compact range [0, n-1]."""
    
    def __init__(self):
        self.values: List[int] = []
        self.sorted_unique: List[int] = []
        self._built = False
    
    def add(self, x: int):
        """Add a value to be compressed."""
        self.values.append(x)
    
    def build(self):
        """Sort and deduplicate. Must call before compress/decompress."""
        self.sorted_unique = sorted(set(self.values))
        self._built = True
    
    def compress(self, x: int) -> int:
        """Map value to its compressed index."""
        assert self._built, "Call build() first"
        return bisect_left(self.sorted_unique, x)
    
    def decompress(self, idx: int) -> int:
        """Map compressed index back to original value."""
        assert self._built, "Call build() first"
        return self.sorted_unique[idx]
    
    def __len__(self):
        return len(self.sorted_unique)


# Example usage
arr = [1_000_000_000, 5, 1_000_000_000, 3, 5, 7, 3]

cc = CoordinateCompression()
for x in arr:
    cc.add(x)
cc.build()

print("Compressed values:")
for x in arr:
    print(f"  {x} -> {cc.compress(x)}")
print(f"Compact range: [0, {len(cc) - 1}]")
```

### Grid Compression Example

```python
from typing import List, Tuple
from bisect import bisect_left

def compress_grid(points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Compress 2D grid coordinates to compact range."""
    xs = sorted(set(x for x, y in points))
    ys = sorted(set(y for x, y in points))
    
    x_map = {x: i for i, x in enumerate(xs)}
    y_map = {y: i for i, y in enumerate(ys)}
    
    return [(x_map[x], y_map[y]) for x, y in points]


# Example: sparse grid
points = [(1000, 2000), (5000, 3000), (1000, 3000), (7000, 1000)]
compressed = compress_grid(points)

print("Original -> Compressed:")
for orig, comp in zip(points, compressed):
    print(f"  {orig} -> {comp}")
```

---

## 130.5 Java Implementation

```java
import java.util.*;

public class CoordinateCompression {
    private int[] sorted;
    private Map<Integer, Integer> compressed;
    
    public CoordinateCompression(int[] values) {
        // Sort and deduplicate
        int[] copy = values.clone();
        Arrays.sort(copy);
        sorted = Arrays.stream(copy).distinct().toArray();
        
        // Build map
        compressed = new HashMap<>();
        for (int i = 0; i < sorted.length; i++)
            compressed.put(sorted[i], i);
    }
    
    public int compress(int x) {
        return compressed.get(x);
    }
    
    public int decompress(int idx) {
        return sorted[idx];
    }
    
    public int size() {
        return sorted.length;
    }
    
    // Binary search version (no map needed)
    public static int compressBS(int[] sorted, int x) {
        int idx = Arrays.binarySearch(sorted, x);
        return idx >= 0 ? idx : -(idx + 1);
    }
    
    public static void main(String[] args) {
        int[] arr = {1_000_000_000, 5, 1_000_000_000, 3, 5, 7, 3};
        
        CoordinateCompression cc = new CoordinateCompression(arr);
        
        System.out.println("Compressed values:");
        for (int x : arr)
            System.out.printf("  %d -> %d%n", x, cc.compress(x));
        System.out.printf("Compact range: [0, %d]%n", cc.size() - 1);
    }
}
```

---

## 130.6 Applications

### 1. Sparse Segment Tree

When the range is [1, 10⁹] but you only have 10⁵ operations, compress coordinates to build a segment tree of size 10⁵ instead of 10⁹.

```cpp
// Problem: Range sum query with values up to 10^9
// Without compression: segment tree of size 4 * 10^9 (impossible)
// With compression: segment tree of size 4 * 2 * 10^5 (feasible)
```

### 2. Sweep Line Algorithms

In sweep line problems (e.g., rectangle area, skyline), compress y-coordinates to process events efficiently.

```cpp
// Problem: Find area covered by rectangles
// Rectangles have coordinates up to 10^9
// Compress y-coordinates, then sweep in x direction
```

### 3. Grid Compression

When a grid has sparse non-zero entries, compress both dimensions.

```cpp
// Problem: 2D prefix sum on sparse grid
// Grid size: 10^9 × 10^9
// Non-zero cells: 10^5
// After compression: 10^5 × 10^5 (or less)
```

### 4. Offline Queries

When queries arrive offline (all known in advance), compress all query parameters together.

```cpp
// Problem: Answer range queries on an array
// Query range [l, r] where l, r can be up to 10^9
// Compress all l and r values, then use compressed indices
```

### 5. Counting Sort Variant

When values are large but few, compression enables counting sort.

```cpp
// Values: {1000000, 2000000, 3000000, 1000000, 2000000}
// After compression: {1, 2, 3, 1, 2}
// Can now use counting sort with array of size 3
```

---

## 130.7 Step-by-Step Walkthrough

### Problem: Count Inversions with Large Values

**Given:** Array of n integers, each up to 10⁹. Count the number of inversions (pairs i < j where a[i] > a[j]).

**Approach:** Use a Binary Indexed Tree (BIT) on compressed coordinates.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class BIT {
    std::vector<int> tree;
    int n;
public:
    BIT(int size) : n(size), tree(size + 1, 0) {}
    void update(int i, int delta) {
        for (; i <= n; i += i & (-i))
            tree[i] += delta;
    }
    int query(int i) {
        int sum = 0;
        for (; i > 0; i -= i & (-i))
            sum += tree[i];
        return sum;
    }
};

long long countInversions(std::vector<int>& arr) {
    int n = arr.size();
    
    // Step 1: Coordinate compression
    std::vector<int> sorted = arr;
    std::sort(sorted.begin(), sorted.end());
    sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
    
    auto compress = [&](int x) {
        return std::lower_bound(sorted.begin(), sorted.end(), x) - sorted.begin() + 1;
    };
    
    // Step 2: Count inversions using BIT
    BIT bit(sorted.size());
    long long inversions = 0;
    
    for (int i = n - 1; i >= 0; i--) {
        inversions += bit.query(compress(arr[i]) - 1);
        bit.update(compress(arr[i]), 1);
    }
    
    return inversions;
}

int main() {
    std::vector<int> arr = {1000000000, 5, 3, 7, 1, 9};
    std::cout << "Inversions: " << countInversions(arr) << "\n";
    return 0;
}
```

**Dry Run:**
```
arr = [1000000000, 5, 3, 7, 1, 9]
sorted_unique = [1, 3, 5, 7, 9, 1000000000]
compress: 1000000000→6, 5→3, 3→2, 7→4, 1→1, 9→5

Process from right to left:
i=5 (9, compressed=5): query(4)=0, update(5,1) → inversions=0
i=4 (1, compressed=1): query(0)=0, update(1,1) → inversions=0
i=3 (7, compressed=4): query(3)=1 (found 1), update(4,1) → inversions=1
i=2 (3, compressed=2): query(1)=1 (found 1), update(2,1) → inversions=2
i=1 (5, compressed=3): query(2)=2 (found 1,3), update(3,1) → inversions=4
i=0 (1000000000, compressed=6): query(5)=5, update(6,1) → inversions=9

Answer: 9 inversions
```

---

## 130.8 Complexity Analysis

| Operation | Time | Notes |
|---|---|---|
| Compression (sort + unique) | O(n log n) | One-time preprocessing |
| Build map | O(n) | Using hash map |
| Compress query (map) | O(1) average | Hash map lookup |
| Compress query (binary search) | O(log n) | Binary search |
| Decompress | O(1) | Array index lookup |
| Space | O(n) | Sorted array + map |

---

## 130.9 Common Pitfalls

1. **Forgetting to include query values:** When compressing for offline queries, include all query parameters (not just array values) in the compression.
2. **Off-by-one errors:** Be consistent with 0-indexed vs 1-indexed compressed values. BIT typically uses 1-indexed.
3. **Not deduplicating:** Use `std::unique` after sorting to remove duplicates.
4. **Using map when binary search suffices:** For competitive programming, binary search is often faster than hash map due to constant factors.
5. **Compressing when not needed:** If values are already in [0, n-1], compression is unnecessary overhead.

---

## 130.10 Advanced: 2D Coordinate Compression

For problems involving 2D grids with sparse points:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

class CoordCompress2D {
    std::vector<int> xs, ys;
    std::map<int, int> x_map, y_map;
    
public:
    void add(int x, int y) {
        xs.push_back(x);
        ys.push_back(y);
    }
    
    void build() {
        // X compression
        std::sort(xs.begin(), xs.end());
        xs.erase(std::unique(xs.begin(), xs.end()), xs.end());
        for (int i = 0; i < (int)xs.size(); i++)
            x_map[xs[i]] = i;
        
        // Y compression
        std::sort(ys.begin(), ys.end());
        ys.erase(std::unique(ys.begin(), ys.end()), ys.end());
        for (int i = 0; i < (int)ys.size(); i++)
            y_map[ys[i]] = i;
    }
    
    std::pair<int, int> compress(int x, int y) {
        return {x_map[x], y_map[y]};
    }
    
    int rows() { return ys.size(); }
    int cols() { return xs.size(); }
};

int main() {
    std::vector<std::pair<int, int>> points = {
        {100, 200}, {500, 300}, {100, 300}, {700, 100}
    };
    
    CoordCompress2D cc;
    for (auto& [x, y] : points)
        cc.add(x, y);
    cc.build();
    
    std::cout << "Grid size: " << cc.rows() << " x " << cc.cols() << "\n";
    for (auto& [x, y] : points) {
        auto [cx, cy] = cc.compress(x, y);
        std::cout << "(" << x << "," << y << ") -> (" << cx << "," << cy << ")\n";
    }
    
    return 0;
}
```

---

## Exercises

1. **Easy:** Compress the array `{50, 10, 30, 10, 50, 20}` and print the mapping.
2. **Medium:** Implement an offline range minimum query using coordinate compression and a segment tree.
3. **Medium:** Given n intervals [l, r] with l, r up to 10⁹, find the maximum number of overlapping intervals using sweep line + coordinate compression.
4. **Hard:** Solve the "rectangle area" problem (LeetCode 850) using 2D coordinate compression and sweep line.
5. **Hard:** Implement a compressed 2D BIT (Binary Indexed Tree) for point update and range sum queries on sparse grids.

## Interview Questions

1. **Q:** When would you use coordinate compression?
   **A:** When the value range is large (10⁹) but the number of distinct values is small (10⁵). Common in segment tree problems, sweep line algorithms, and grid problems with sparse data.

2. **Q:** What's the time complexity of coordinate compression?
   **A:** O(n log n) for sorting and deduplication. Each subsequent query is O(log n) with binary search or O(1) with a hash map.

3. **Q:** How do you handle offline queries with coordinate compression?
   **A:** Collect all values (both data and query parameters) before compression. This ensures query indices map correctly to compressed coordinates.

4. **Q:** Can coordinate compression be done online (streaming)?
   **A:** Not directly, since you need all values to sort and deduplicate. For online processing, use a balanced BST (like `std::map`) to assign indices as values arrive, but this changes the complexity to O(n log n) per operation.

## Cross-References
- Binary Indexed Tree: Chapter 53
- Segment Tree: Chapter 52
- Sweep Line: Chapter 97
- Sorting: Chapter 14
- Binary Search: Chapter 20
