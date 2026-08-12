# Chapter 160: Parallel Algorithms

## Prerequisites
- Basic algorithms and complexity theory
- Graph algorithms
- Sorting and searching
- Recurrence relations

## Interview Frequency: ★

Parallel algorithms decompose a problem into subproblems that execute simultaneously across multiple processors. Understanding parallelism is essential for modern multi-core systems, distributed computing, GPU programming, and high-performance computing. While rarely asked in standard interviews, parallel thinking demonstrates mastery of algorithmic efficiency and is critical for systems engineering roles.

---

## 160.1 Motivation and Intuition

### Why Parallelism?

Modern processors are no longer getting significantly faster in single-core performance. Instead, they ship with more cores. A program that uses only one core wastes 87.5% of an 8-core machine.

**Real-world analogy**: Imagine painting a house. One painter (sequential) takes 8 hours. Eight painters (parallel) can finish in roughly 1 hour—but only if they can divide the work without stepping on each other's toes. Some tasks (painting different rooms) parallelize perfectly. Others (mixing a single bucket of paint) cannot be parallelized at all.

### Sequential vs Parallel

| Aspect | Sequential | Parallel |
|---|---|---|
| Processors used | 1 | p |
| Time complexity | T(n) | T(n)/p + overhead |
| Programming model | Simple | Complex (synchronization, race conditions) |
| Hardware trend | Diminishing gains | Main path to performance |

### When Does Parallelism Help?

- **Independent subproblems**: Matrix multiplication, embarrassingly parallel tasks
- **Divide-and-conquer**: Merge sort, quicksort
- **Prefix/scan operations**: Prefix sums, histogram computation
- **Graph traversal**: BFS explores many vertices at the same depth simultaneously
- **Reduction operations**: Sum, max, min across an array

### Amdahl's Law

If a fraction `f` of a program is inherently sequential, then with `p` processors:

```
Speedup = 1 / (f + (1-f)/p)
```

As p → ∞, speedup → 1/f. If 10% is sequential, maximum speedup is 10× regardless of processor count.

**Example**: If f = 0.05 (5% sequential) and p = 100:
```
Speedup = 1 / (0.05 + 0.95/100) = 1 / 0.0595 ≈ 16.8×
```

This shows that even a small sequential fraction severely limits parallelism.

---

## 160.2 PRAM Model (Parallel Random Access Machine)

The PRAM is the foundational theoretical model for parallel algorithms. It assumes:
- Multiple processors with a shared global memory
- Each processor can read/write memory in one step
- Processors execute in lock-step (synchronous)

### PRAM Variants

| Variant | Concurrent Read | Concurrent Write | Realism |
|---|---|---|---|
| **EREW** (Exclusive Read Exclusive Write) | No | No | Most practical |
| **CREW** (Concurrent Read Exclusive Write) | Yes | No | Common pattern |
| **CRCW** (Concurrent Read Concurrent Write) | Yes | Yes | Most powerful |
| **ERCW** (Exclusive Read Concurrent Write) | Yes (write only) | No | Rarely used |

**CRCW Sub-variants** for write conflicts:
- **Common**: All concurrent writes must write the same value
- **Arbitrary**: One arbitrary processor succeeds
- **Priority**: Highest-priority processor wins

**Example — Finding Maximum with CRCW**:
```
Algorithm: Compare all pairs simultaneously
For each pair (i, j) in parallel:
    if A[i] < A[j], set flag[i] = 1
After all comparisons, elements with flag[i] = 0 are maximums

Time: O(1) with O(n²) processors
```

---

## 160.3 Work-Depth Model

A more practical theoretical framework that separates total work from parallel depth.

| Measure | Definition | Significance |
|---|---|---|
| **Work T₁** | Total number of operations | Sequential time equivalent |
| **Depth T∞** | Longest chain of dependent operations | Best possible parallel time |
| **Parallelism T₁/T∞** | Maximum useful processors | Speedup limit |

### Brent's Theorem

With p processors, the execution time satisfies:

```
T_p ≤ T₁/p + T∞
```

This is fundamental: it says that with enough processors, depth is the bottleneck; with few processors, work dominates.

**Implication**: To get linear speedup with p processors, we need T₁/p >> T∞, i.e., the parallelism T₁/T∞ must be much larger than p.

### Example: Parallel Prefix Sum

For an array of n elements:
- **Work**: O(n) — same as sequential
- **Depth**: O(log n) — tree height
- **Parallelism**: O(n / log n)

This means we can use up to n/log(n) processors effectively.

---

## 160.4 Parallel Prefix Sum (Scan)

Prefix sum is the most important parallel primitive. Many algorithms reduce to it.

**Problem**: Given array A[0..n-1], compute B[i] = A[0] + A[1] + ... + A[i] for all i.

### Hillis-Steele Algorithm (Blelloch's Work-Efficient Version)

The algorithm has two phases:

**Phase 1 — Up-Sweep (Reduce)**:
```
For d = 0, 1, ..., log₂(n) - 1:
    For all k in parallel where k mod 2^(d+1) == 2^(d+1) - 1:
        A[k] += A[k - 2^d]
```
After up-sweep, A[n-1] contains the total sum.

**Phase 2 — Down-Sweep (Distribute)**:
```
A[n-1] = 0
For d = log₂(n) - 1, ..., 0:
    For all k in parallel where k mod 2^(d+1) == 2^(d+1) - 1:
        temp = A[k]
        A[k] += A[k - 2^d]
        A[k - 2^d] = temp
```

### Dry Run: Prefix Sum on [3, 1, 7, 0, 4, 1, 6, 3]

**Initial**: [3, 1, 7, 0, 4, 1, 6, 3]

**Up-Sweep**:
```
d=0 (stride 1): [3, 4, 7, 7, 4, 5, 6, 9]   (pairs: 1+3, 0+7, 1+4, 6+3)
d=1 (stride 2): [3, 4, 7, 11, 4, 5, 6, 14]  (7+4, 6+9... wait)
d=2 (stride 4): [3, 4, 7, 11, 4, 5, 6, 25]
```
Total sum = 25 at A[7].

**Down-Sweep** (A[7] = 0):
```
d=2: [3, 4, 7, 11, 4, 5, 6, 0] → [3, 4, 7, 11, 7, 9, 13, 11]
d=1: ...
d=0: ...
```

**Result** (exclusive prefix sum): [0, 3, 4, 11, 11, 15, 16, 22]

For inclusive: add A[i] back → [3, 4, 11, 11, 15, 16, 22, 25]

### Step-by-Step Dry Run (Simplified)

Given `[3, 1, 7, 0, 4, 1, 6, 3]`:

```
Level 0 (stride 2):  [3, 1+3, 7, 0+7, 4, 1+4, 6, 3+6]
                    = [3, 4, 7, 7, 4, 5, 6, 9]

Level 1 (stride 4):  [3, 4, 7, 4+7, 4, 5, 6, 5+9]
                    = [3, 4, 7, 11, 4, 5, 6, 14]

Level 2 (stride 8):  [3, 4, 7, 11, 4, 5, 6, 11+14]
                    = [3, 4, 7, 11, 4, 5, 6, 25]
Total sum = 25

Down-sweep sets A[7]=0, then distributes:
Level 2: A[7]=0, A[3]=11
Level 1: A[3]=11+0=11, A[7]=11+14=25... (distribute to children)
Level 0: Final distribution

Inclusive prefix: [3, 4, 11, 11, 15, 16, 22, 25]
```

### Complexity

| Phase | Work | Depth | Processors |
|---|---|---|---|
| Up-Sweep | O(n) | O(log n) | O(n) |
| Down-Sweep | O(n) | O(log n) | O(n) |
| **Total** | **O(n)** | **O(log n)** | **O(n)** |

---

## 160.5 Parallel Sorting

### Parallel Merge Sort

**Idea**: Divide array in half, sort each half in parallel, then merge.

- **Work**: O(n log n) — same as sequential
- **Depth**: O(log² n) — log n levels, each merge is O(log n) depth with parallel merge
- **Processors**: O(n)

The merge step can be parallelized using binary search:
```
Parallel Merge(A, B):
    Pick middle element A[mid]
    Binary search for A[mid] in B → position j
    Element A[mid] goes to position mid + j in output
    Recurse on left halves and right halves in parallel
```

### Bitonic Sort

A comparison-based sorting network. Works on arrays of size 2^k.

**Bitonic sequence**: A sequence that first increases then decreases (or can be circularly shifted to be so).

**Key property**: A bitonic sequence of length n can be sorted in O(log n) parallel steps using a bitonic merge network.

**Algorithm**:
```
BitonicSort(A, n):
    if n == 1: return
    Sort first half in ascending order  (in parallel)
    Sort second half in descending order (in parallel)
    BitonicMerge(A, n)

BitonicMerge(A, n):
    if n == 1: return
    For i = 0 to n/2 - 1 in parallel:
        if A[i] > A[i + n/2]: swap(A[i], A[i + n/2])
    BitonicMerge(first half, n/2)  (in parallel)
    BitonicMerge(second half, n/2) (in parallel)
```

**Complexity**:
- Work: O(n log² n)
- Depth: O(log² n)
- Processors: O(n)

### Sample Sort

A practical parallel generalization of quicksort:
1. Each processor sorts its local chunk
2. Select p-1 splitters from sorted chunks
3. Use splitters to partition data into p buckets
4. Each processor handles one bucket

**Complexity**: O(n log n / p + p log p) per processor.

---

## 160.6 Parallel Graph Algorithms

### Parallel BFS

BFS is naturally parallel: all vertices at the same distance can be processed simultaneously.

```
ParallelBFS(graph, source):
    visited = {source}
    frontier = {source}
    while frontier is not empty:
        next_frontier = {}
        for each vertex v in frontier (in parallel):
            for each neighbor u of v:
                if u not in visited:
                    mark u as visited
                    add u to next_frontier
        frontier = next_frontier
```

| Metric | Value |
|---|---|
| Work | O(V + E) |
| Depth | O(diameter) |
| Processors | O(V) |

### Parallel Connected Components

Using pointer jumping (path compression in parallel):
1. Initialize each vertex as its own component representative
2. For each edge (u,v), set the higher-representative to point to the lower
3. Repeat pointer jumping until all paths are compressed

**Complexity**: O(V + E) work, O(log² V) depth.

### Parallel Minimum Spanning Tree

Based on Borůvka's algorithm (naturally parallel):
1. Each vertex selects its minimum-weight outgoing edge
2. Contract the selected edges (merge components)
3. Repeat until one component remains

**Complexity**: O(E log E) work, O(log² V) depth.

### Parallel Shortest Paths

| Algorithm | Work | Depth | Notes |
|---|---|---|---|
| Parallel Dijkstra | O(V² + VE) | O(V) | Dense graphs |
| Parallel Bellman-Ford | O(VE) | O(V) | Negative edges |
| Parallel Floyd-Warshall | O(V³) | O(V) | All-pairs |

---

## 160.7 Parallel Matrix Operations

### Parallel Matrix Multiplication

Given A (m×p) and B (p×n), compute C = A×B:

```
For i = 0 to m-1, j = 0 to n-1 in parallel:
    C[i][j] = Σ_{k=0}^{p-1} A[i][k] * B[k][j]
```

| Metric | Value |
|---|---|
| Work | O(mnp) |
| Depth | O(log p) (parallel reduction for sum) |
| Processors | O(mn) |

### Strassen's Algorithm (Parallel Version)

Reduces work to O(n^2.807) with O(log n) depth using recursive block decomposition.

---

## 160.8 Parallel Algorithm Design Techniques

### 1. Parallel Divide and Conquer

Split problem into subproblems, solve in parallel, combine.

**Template**:
```
ParallelDC(problem):
    if problem is small: solve sequentially
    Split into subproblems P1, P2, ..., Pk
    Solve P1, P2, ..., Pk in parallel
    Combine results
```

### 2. Parallel Pointer Jumping

Repeatedly update pointers until convergence. Used in list ranking, connected components.

### 3. Randomized Parallel Algorithms

Random choices can break dependencies and enable parallelism where deterministic approaches cannot.

**Example**: Randomized work-stealing for load balancing.

### 4. Parallel Reduction

Combine elements using an associative operator (sum, max, min, etc.) in a tree pattern.

```
Reduction(A, op):
    while |A| > 1:
        for i = 0 to |A|/2 in parallel:
            A[i] = A[2i] op A[2i+1]
        A = first |A|/2 elements
    return A[0]
```

---

## 160.9 Implementations

### C++: Parallel Prefix Sum

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>

// Parallel prefix sum using Blelloch's work-efficient scan
// Sequential simulation of the parallel algorithm
std::vector<int> parallelPrefixSum(std::vector<int> arr) {
    int n = arr.size();
    if (n == 0) return arr;
    
    // Ensure n is a power of 2 for simplicity
    while ((n & (n - 1)) != 0) {
        arr.push_back(0);
        n++;
    }
    
    // Up-sweep: build partial sums
    for (int d = 0; (1 << d) < n; d++) {
        int stride = 1 << (d + 1);
        for (int i = 0; i < n; i += stride) {
            int right = i + stride - 1;
            int left = right - (1 << d);
            arr[right] += arr[left];
        }
    }
    
    // Store total sum and set last element to 0 (exclusive scan)
    int totalSum = arr[n - 1];
    arr[n - 1] = 0;
    
    // Down-sweep: distribute values
    for (int d = (int)(std::log2(n)) - 1; d >= 0; d--) {
        int stride = 1 << (d + 1);
        for (int i = 0; i < n; i += stride) {
            int right = i + stride - 1;
            int left = right - (1 << d);
            int temp = arr[left];
            arr[left] = arr[right];
            arr[right] += temp;
        }
    }
    
    // Convert exclusive to inclusive prefix sum
    std::vector<int> result(n);
    result[0] = arr[0];
    for (int i = 1; i < n; i++)
        result[i] = result[i - 1] + arr[i];
    
    return result;
}

int main() {
    std::vector<int> arr = {3, 1, 7, 0, 4, 1, 6, 3};
    auto prefix = parallelPrefixSum(arr);
    
    std::cout << "Input:        ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\nPrefix sums:  ";
    for (int x : prefix) std::cout << x << " ";
    std::cout << "\n";
    // Expected: 3 4 11 11 15 16 22 25
    
    return 0;
}
```

### Python: Parallel Merge Sort

```python
from concurrent.futures import ThreadPoolExecutor
import math

def sequential_merge(left, right):
    """Merge two sorted arrays."""
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def parallel_merge_sort(arr, depth=0, max_depth=3):
    """
    Parallel merge sort using thread pool.
    Limits parallelism depth to avoid thread explosion.
    """
    if len(arr) <= 1:
        return arr
    
    mid = len(arr) // 2
    
    if depth < max_depth:
        with ThreadPoolExecutor(max_workers=2) as executor:
            left_future = executor.submit(
                parallel_merge_sort, arr[:mid], depth + 1, max_depth
            )
            right_future = executor.submit(
                parallel_merge_sort, arr[mid:], depth + 1, max_depth
            )
            left = left_future.result()
            right = right_future.result()
    else:
        # Fall back to sequential for small subproblems
        left = parallel_merge_sort(arr[:mid], depth + 1, max_depth)
        right = parallel_merge_sort(arr[mid:], depth + 1, max_depth)
    
    return sequential_merge(left, right)

def binary_search(arr, target, lo, hi):
    """Binary search for insertion point."""
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo

def parallel_merge_optimized(left, right):
    """
    Merge using parallel binary search.
    Each element finds its position in the other array independently.
    """
    n, m = len(left), len(right)
    result = [0] * (n + m)
    
    # For each element in left, find how many from right come before it
    # This is inherently parallelizable
    positions = []
    for i in range(n):
        pos = binary_search(right, left[i], 0, m)
        positions.append(pos)
    
    for i in range(n):
        result[i + positions[i]] = left[i]
    for j in range(m):
        # Count how many left elements are <= right[j]
        count = sum(1 for p in positions if p <= j)
        result[j + count] = right[j]
    
    return result

if __name__ == "__main__":
    import random
    arr = [random.randint(1, 100) for _ in range(16)]
    print(f"Input:  {arr}")
    sorted_arr = parallel_merge_sort(arr)
    print(f"Sorted: {sorted_arr}")
    
    # Verify correctness
    assert sorted_arr == sorted(arr), "Sort failed!"
    print("✓ Sort verified correct")
```

### Java: Bitonic Sort

```java
import java.util.Arrays;

public class BitonicSort {
    
    /**
     * Bitonic sort: a comparison-based sorting network.
     * Works only on arrays of size 2^k.
     * 
     * Time: O(n log^2 n) comparisons
     * Depth: O(log^2 n) parallel steps
     */
    
    private static void bitonicSort(int[] arr, int low, int cnt, boolean ascending) {
        if (cnt > 1) {
            int k = cnt / 2;
            
            // Sort first half ascending
            bitonicSort(arr, low, k, true);
            // Sort second half descending
            bitonicSort(arr, low + k, k, false);
            // Merge the bitonic sequence
            bitonicMerge(arr, low, cnt, ascending);
        }
    }
    
    private static void bitonicMerge(int[] arr, int low, int cnt, boolean ascending) {
        if (cnt > 1) {
            int k = cnt / 2;
            for (int i = low; i < low + k; i++) {
                if (ascending == (arr[i] > arr[i + k])) {
                    // Swap
                    int temp = arr[i];
                    arr[i] = arr[i + k];
                    arr[i + k] = temp;
                }
            }
            bitonicMerge(arr, low, k, ascending);
            bitonicMerge(arr, low + k, k, ascending);
        }
    }
    
    /**
     * Pad array to next power of 2, sort, then trim.
     */
    public static void sort(int[] arr) {
        int n = arr.length;
        int paddedSize = Integer.highestOneBit(n - 1) << 1; // next power of 2
        if (paddedSize < n) paddedSize = n;
        
        int[] padded = new int[paddedSize];
        Arrays.fill(padded, Integer.MAX_VALUE);
        System.arraycopy(arr, 0, padded, 0, n);
        
        bitonicSort(padded, 0, paddedSize, true);
        
        System.arraycopy(padded, 0, arr, 0, n);
    }
    
    public static void main(String[] args) {
        int[] arr = {3, 7, 4, 8, 6, 2, 1, 5};
        System.out.println("Before: " + Arrays.toString(arr));
        
        sort(arr);
        
        System.out.println("After:  " + Arrays.toString(arr));
        // Output: [1, 2, 3, 4, 5, 6, 7, 8]
    }
}
```

---

## 160.10 Exercises

### Conceptual Exercises

1. **Amdahl's Law**: A program is 20% sequential. What is the maximum speedup with 1000 processors?

2. **Work-Depth**: An algorithm has work O(n²) and depth O(n). How many processors give linear speedup?

3. **PRAM Variants**: Explain why EREW is the most practical PRAM model. Give an example where CRCW provides a provable advantage.

4. **Prefix Sum**: Show that any problem solvable in O(log n) depth with O(n) work can also be solved sequentially in O(n) time.

5. **Bitonic Sort**: Why must the array size be a power of 2? How would you handle arbitrary sizes?

### Programming Exercises

1. **Parallel Reduction**: Implement a parallel sum reduction. What is its work and depth?

2. **Parallel BFS**: Implement BFS that processes all vertices at the same level simultaneously.

3. **Parallel Matrix Multiply**: Implement matrix multiplication where each output element is computed independently.

4. **Parallel Merge**: Implement the binary-search-based parallel merge described in Section 160.5.

5. **Parallel Histogram**: Given an array of values in [0, k), compute the frequency histogram in O(n) work and O(log n) depth using prefix sums.

---

## 160.11 Interview Questions

### Conceptual Questions

1. **Q**: What is the difference between work and depth? Why do we need both?
   **A**: Work measures total operations (relates to sequential time). Depth measures the longest dependency chain (relates to parallel time). We need both because work tells us if the algorithm is efficient overall, and depth tells us the best possible parallel time. An algorithm with O(n²) work and O(log n) depth uses many processors but cannot be made faster than O(n²/p + log n).

2. **Q**: Explain Amdahl's Law. How does it limit parallelism?
   **A**: Amdahl's Law states that if a fraction f of code is sequential, maximum speedup is 1/f regardless of processor count. If 5% is sequential, you can never get more than 20× speedup. This motivates designing algorithms with minimal sequential portions.

3. **Q**: How does parallel prefix sum help in parallel algorithms?
   **A**: Prefix sum is a fundamental building block. It enables: (1) compact — removing unwanted elements, (2) allocation — computing output indices for each element, (3) segmented operations, (4) radix sort, (5) polynomial evaluation. Many algorithms reduce to prefix sums.

4. **Q**: What makes BFS naturally parallel?
   **A**: All vertices at the same distance from the source are independent — processing one doesn't affect others. The frontier at each level can be explored in parallel. The depth is bounded by the graph diameter, not V.

### Coding Questions

1. **Q**: Implement a parallel algorithm to find the maximum element in an array. What are its work and depth?
   **A**: Use a parallel reduction (tournament tree). Work: O(n). Depth: O(log n). Each round pairs elements and keeps the larger.

2. **Q**: Given n points in 2D, find the closest pair. Can this be parallelized?
   **A**: Yes. The divide-and-conquer closest pair algorithm can be parallelized. Divide by x-coordinate (O(log n) depth with parallel partition). Solve halves in parallel. The combine step examines a strip of width 2d around the dividing line — this can be done in O(log n) depth with sorting.

3. **Q**: How would you parallelize counting sort?
   **A**: (1) In parallel, count occurrences of each value (requires CRCW or local counts + reduction). (2) Compute prefix sums of counts (O(log k) depth). (3) In parallel, place each element at its correct position. Total: O(n + k) work, O(log k) depth.

---

## 160.12 Cross-References

- **Chapter 10: Sorting** — Sequential sorting algorithms that parallel algorithms build upon
- **Chapter 23: Graph Traversal** — BFS and DFS foundations for parallel graph algorithms
- **Chapter 15: Divide and Conquer** — The design paradigm most amenable to parallelism
- **Chapter 157: Concurrent Data Structures** — Thread-safe data structures for parallel algorithms
- **Chapter 158: Succinct Data Structures** — Bit-parallel operations on compact representations
- **Chapter 161: External Memory Algorithms** — I/O-efficient algorithms that complement parallelism
- **Chapter 163: Advanced Mathematics** — Probability theory for randomized parallel algorithms
- **Chapter 100: Van Emde Boas Trees** — Recursive structure with parallel decomposition ideas

---

## Summary

| Problem | Sequential | Parallel Depth | Processors | Key Technique |
|---|---|---|---|---|
| Prefix Sum | O(n) | O(log n) | O(n) | Tree reduction |
| Sorting (Merge) | O(n log n) | O(log² n) | O(n) | Parallel merge |
| Sorting (Bitonic) | O(n log² n) | O(log² n) | O(n) | Sorting network |
| BFS | O(V+E) | O(diameter) | O(V) | Frontier parallelism |
| Connected Components | O(V+E) | O(log² n) | O(V+E) | Pointer jumping |
| MST | O(E log E) | O(log² V) | O(E) | Borůvka's |
| Matrix Multiply | O(n³) | O(log n) | O(n²) | Independent computation |
| Reduction | O(n) | O(log n) | O(n) | Tree reduction |

**Key Takeaway**: Parallel algorithms trade processors for time. The work-depth model captures this tradeoff. Prefix sum is the most versatile parallel primitive. Amdahl's Law reminds us that sequential bottlenecks limit speedup regardless of processor count. Design for minimum depth while keeping work efficient.
