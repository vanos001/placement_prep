# Chapter 159: External Memory Algorithms

## Prerequisites
- Sorting algorithms ([Chapter 108](ch108-dsu-on-tree-rerooting.md))
- B-Trees ([Chapter 104](ch104-cartesian-tournament-trees.md))
- Basic I/O concepts
- Graph algorithms ([Chapter 120](ch120-bwt-fmindex.md))

## Interview Frequency: ★

External memory algorithms optimize for data too large to fit in main memory. Rarely asked in interviews, but critical for systems engineering and database design.

---

## 159.1 Definition and Motivation

### The Problem

Modern computers have a **memory hierarchy**:

```
Registers  →  L1 Cache  →  L2 Cache  →  RAM  →  SSD  →  HDD
~1 ns        ~1 ns        ~4 ns        ~100 ns  ~100 μs  ~10 ms
```

When data fits in RAM, we use standard algorithms. But when data is **larger than RAM** (terabytes of data, database indexes, graph processing), we need algorithms that minimize slow disk I/O.

### The I/O Model

The **External Memory Model** (also called **Disk Access Model** or **DAM**) abstracts this:

- **M** words of fast memory (cache/RAM)
- **Unlimited** slow memory (disk/SSD)
- **B** words transferred per block (disk page)
- **Goal**: minimize block transfers (I/O operations)

| Parameter | Typical Value |
|---|---|
| M (RAM) | 8 GB |
| B (block size) | 4 KB = 1024 words |
| M/B (blocks in RAM) | ~2 million |

### Why I/O Matters

An algorithm with O(n log n) comparisons might perform terribly if it does O(n log n) random disk accesses. Each random disk access is **100,000× slower** than a RAM access.

**Example**: Sorting 1 billion 4-byte integers (4 GB data, 1 GB RAM)
- Standard quicksort: ~30 billion random reads → hours
- External merge sort: ~12 sequential passes → minutes

---

## 159.2 I/O Complexity Basics

### Notation

- **N** = total number of elements
- **Scan(N)** = Θ(N/B) I/Os — read all data sequentially
- **Sort(N)** = Θ((N/B) · log_{M/B}(N/B)) I/Os — external merge sort
- **Search(N)** = Θ(log_B N) I/Os — B-tree lookup

### Lower Bounds

Sorting N elements requires Ω((N/B) · log_{M/B}(N/B)) I/Os. This is the external memory analog of the Ω(n log n) comparison sort lower bound.

---

## 159.3 External Merge Sort

### The Standard Algorithm

**Phase 1: Create sorted runs**
1. Read M elements into memory
2. Sort them using any internal sort (quicksort, etc.)
3. Write the sorted run to disk
4. Repeat until all data is processed

This creates ⌈N/M⌉ sorted runs.

**Phase 2: Merge runs**
1. Load one block from each of M/B runs into memory
2. Perform an (M/B)-way merge
3. Write output in blocks of B elements
4. Repeat until one run remains

### Step-by-Step Example

Sort 24 elements with M = 8, B = 2:

**Data**: [15, 3, 12, 8, 1, 20, 5, 18, 7, 14, 2, 11, 19, 6, 9, 16, 4, 13, 17, 10, 22, 21, 24, 23]

**Phase 1** (3 runs, each 8 elements):
- Run 1: [15, 3, 12, 8, 1, 20, 5, 18] → sort → [1, 3, 5, 8, 12, 15, 18, 20]
- Run 2: [7, 14, 2, 11, 19, 6, 9, 16] → sort → [2, 6, 7, 9, 11, 14, 16, 19]
- Run 3: [4, 13, 17, 10, 22, 21, 24, 23] → sort → [4, 10, 13, 17, 21, 22, 23, 24]

**Phase 2** (merge 3 runs):
- Merge runs 1, 2, 3 → [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]

### Code

**C++**

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <fstream>
#include <queue>
#include <functional>

// Simulate external memory with file I/O
struct Run {
    std::vector<int> data;
    int pos;
    
    bool operator>(const Run& other) const {
        return data[pos] > other.data[pos];
    }
};

std::vector<int> externalMergeSort(const std::vector<int>& data, int M, int B) {
    int n = data.size();
    
    // Phase 1: Create sorted runs
    std::vector<std::vector<int>> runs;
    for (int i = 0; i < n; i += M) {
        int end = std::min(i + M, n);
        std::vector<int> run(data.begin() + i, data.begin() + end);
        std::sort(run.begin(), run.end());
        runs.push_back(run);
    }
    
    // Phase 2: Merge runs (k-way merge where k = M/B)
    int k = M / B;
    while (runs.size() > 1) {
        std::vector<std::vector<int>> newRuns;
        for (int i = 0; i < (int)runs.size(); i += k) {
            int end = std::min(i + k, (int)runs.size());
            
            // k-way merge
            std::priority_queue<Run, std::vector<Run>, std::greater<Run>> pq;
            for (int j = i; j < end; j++) {
                if (!runs[j].empty()) {
                    pq.push({runs[j], 0});
                }
            }
            
            std::vector<int> merged;
            while (!pq.empty()) {
                auto run = pq.top();
                pq.pop();
                merged.push_back(run.data[run.pos]);
                if (run.pos + 1 < (int)run.data.size()) {
                    pq.push({run.data, run.pos + 1});
                }
            }
            newRuns.push_back(merged);
        }
        runs = newRuns;
    }
    
    return runs.empty() ? std::vector<int>() : runs[0];
}

int main() {
    std::vector<int> data = {15, 3, 12, 8, 1, 20, 5, 18, 7, 14, 2, 11, 19, 6, 9, 16};
    int M = 8, B = 2;
    
    std::vector<int> sorted = externalMergeSort(data, M, B);
    std::cout << "Sorted: ";
    for (int x : sorted) std::cout << x << " ";
    std::cout << "\n";
    
    return 0;
}
```

**Python**

```python
import heapq
from typing import List

def external_merge_sort(data: List[int], M: int, B: int) -> List[int]:
    """
    External merge sort simulation.
    M: memory size (number of elements that fit in RAM)
    B: block size (number of elements per disk block)
    """
    n = len(data)
    
    # Phase 1: Create sorted runs
    runs = []
    for i in range(0, n, M):
        chunk = data[i:i + M]
        chunk.sort()
        runs.append(chunk)
    
    # Phase 2: Merge runs (k-way where k = M/B)
    k = M // B
    while len(runs) > 1:
        new_runs = []
        for i in range(0, len(runs), k):
            group = runs[i:i + k]
            # k-way merge using heap
            merged = list(heapq.merge(*group))
            new_runs.append(merged)
        runs = new_runs
    
    return runs[0] if runs else []

# Example
data = [15, 3, 12, 8, 1, 20, 5, 18, 7, 14, 2, 11, 19, 6, 9, 16]
M, B = 8, 2
sorted_data = external_merge_sort(data, M, B)
print(f"Sorted: {sorted_data}")

# I/O analysis
n = len(data)
num_runs = (n + M - 1) // M
merge_passes = 0
r = num_runs
while r > 1:
    r = (r + k - 1) // k  # k = M/B
    merge_passes += 1
total_io = 2 * n / B * (1 + merge_passes)  # Read + write for each pass
print(f"Runs: {num_runs}, Merge passes: {merge_passes}, Estimated I/Os: {total_io:.0f}")
```

**Java**

```java
import java.util.*;

public class ExternalMergeSort {
    public static List<Integer> externalMergeSort(int[] data, int M, int B) {
        int n = data.length;
        
        // Phase 1: Create sorted runs
        List<List<Integer>> runs = new ArrayList<>();
        for (int i = 0; i < n; i += M) {
            int end = Math.min(i + M, n);
            int[] chunk = Arrays.copyOfRange(data, i, end);
            Arrays.sort(chunk);
            List<Integer> run = new ArrayList<>();
            for (int x : chunk) run.add(x);
            runs.add(run);
        }
        
        // Phase 2: k-way merge (k = M/B)
        int k = M / B;
        while (runs.size() > 1) {
            List<List<Integer>> newRuns = new ArrayList<>();
            for (int i = 0; i < runs.size(); i += k) {
                int end = Math.min(i + k, runs.size());
                List<List<Integer>> group = runs.subList(i, end);
                
                // k-way merge
                PriorityQueue<int[]> pq = new PriorityQueue<>(Comparator.comparingInt(a -> a[0]));
                for (int j = 0; j < group.size(); j++) {
                    if (!group.get(j).isEmpty()) {
                        pq.offer(new int[]{group.get(j).get(0), j, 0});
                    }
                }
                
                List<Integer> merged = new ArrayList<>();
                while (!pq.isEmpty()) {
                    int[] curr = pq.poll();
                    merged.add(curr[0]);
                    int runIdx = curr[1], pos = curr[2];
                    if (pos + 1 < group.get(runIdx).size()) {
                        pq.offer(new int[]{group.get(runIdx).get(pos + 1), runIdx, pos + 1});
                    }
                }
                newRuns.add(merged);
            }
            runs = newRuns;
        }
        
        return runs.isEmpty() ? new ArrayList<>() : runs.get(0);
    }
    
    public static void main(String[] args) {
        int[] data = {15, 3, 12, 8, 1, 20, 5, 18, 7, 14, 2, 11};
        List<Integer> sorted = externalMergeSort(data, 8, 2);
        System.out.println("Sorted: " + sorted);
    }
}
```

### I/O Complexity

**Phase 1**: Each element is read and written once → O(N/B) I/Os

**Phase 2**: Each merge pass reads and writes all data → O(N/B) per pass
- Number of passes: log_{M/B}(N/M)
- Total: O((N/B) · log_{M/B}(N/B))

---

## 159.4 B-Trees for External Storage

### Why B-Trees?

Binary search trees have O(log₂ N) height, meaning O(log₂ N) disk accesses for a lookup. With N = 1 billion, that's ~30 disk accesses.

B-Trees have O(log_B N) height. With B = 1024, that's ~3 disk accesses for the same data!

### B-Tree Properties

- Each node contains up to **2B - 1** keys (where B = disk page size in keys)
- Each internal node has up to **2B** children
- Height = O(log_B N)
- All leaves at the same depth

### Operations

| Operation | I/O Complexity | Description |
|---|---|---|
| Search | O(log_B N) | Traverse from root to leaf |
| Insert | O(log_B N) | Find position, split if needed |
| Delete | O(log_B N) | Find key, merge if needed |
| Range query | O(log_B N + K/B) | Find start, scan K results |

### B+ Tree Variant

In practice, databases use **B+ Trees**:
- All data in leaves (internal nodes only have keys for routing)
- Leaves linked together for efficient range queries
- Higher fanout → fewer disk accesses

---

## 159.5 Cache-Oblivious Algorithms

### The Idea

Standard external memory algorithms need to know M and B. **Cache-oblivious** algorithms work efficiently **without knowing M and B** — they automatically adapt to any memory hierarchy.

### Key Technique: Recursive Decomposition

Instead of processing data in blocks of size B, recursively split the problem in half. This naturally aligns with cache lines at every level of the memory hierarchy.

### Cache-Oblivious Matrix Transpose

**Standard approach**: Process row by row → O(N²/B) I/Os if N ≤ √M, but poor cache behavior otherwise.

**Cache-oblivious approach**: Recursively divide the matrix into quadrants.

```python
def cache_oblivious_transpose(matrix, row_start, row_end, col_start, col_end):
    """Recursively transpose a submatrix."""
    rows = row_end - row_start
    cols = col_end - col_start
    
    if rows <= 1 and cols <= 1:
        return
    
    if rows >= cols:
        mid = (row_start + row_end) // 2
        cache_oblivious_transpose(matrix, row_start, mid, col_start, col_end)
        cache_oblivious_transpose(matrix, mid, row_end, col_start, col_end)
    else:
        mid = (col_start + col_end) // 2
        cache_oblivious_transpose(matrix, row_start, row_end, col_start, mid)
        cache_oblivious_transpose(matrix, row_start, row_end, mid, col_end)
    
    # Swap the two halves
    # (In practice, this is done during the recursion)
```

### Funnel Sort

A cache-oblivious sorting algorithm that achieves the optimal O((N/B) · log_{M/B}(N/B)) I/O complexity without knowing M or B.

**Key idea**: Use a k-way merge with a "funnel" — a binary tree of buffers that recursively merges sorted sequences.

---

## 159.6 External Graph Algorithms

### The Challenge

Graphs in external memory are tricky because:
- Adjacency lists may span many disk pages
- BFS/DFS visit neighbors in unpredictable order
- Random access patterns destroy I/O efficiency

### External BFS

**Standard BFS**: Visit neighbors in random order → O(V + E) random accesses → terrible I/O performance.

**External BFS**: Use the **level-synchronous** approach:
1. Process all vertices at the current level
2. Write discovered vertices to disk
3. Read and deduplicate for the next level

```python
def external_bfs(adj_file, source, M, B):
    """
    External BFS using level-synchronous approach.
    adj_file: adjacency list stored on disk
    M: memory capacity
    B: block size
    """
    visited = set()
    current_level = [source]
    visited.add(source)
    
    while current_level:
        next_level = []
        
        # Process current level in chunks that fit in memory
        for chunk_start in range(0, len(current_level), M // B):
            chunk = current_level[chunk_start:chunk_start + M // B]
            
            # Read adjacency lists for vertices in chunk
            for v in chunk:
                neighbors = read_adjacency(adj_file, v)  # Disk read
                for u in neighbors:
                    if u not in visited:
                        visited.add(u)
                        next_level.append(u)
        
        # Write next level to disk
        write_level_to_disk(next_level)
        current_level = next_level
    
    return visited
```

### I/O Complexity for Graph Algorithms

| Algorithm | I/O Complexity |
|---|---|
| BFS | O((V + E)/B · log_{M/B}(V/B)) |
| DFS | O((V + E)/B · log_{M/B}(V/B)) |
| Connected Components | O((V + E)/B · log_{M/B}(V/B)) |
| Single-source Shortest Paths | O((V + E)/B · log_{M/B}(V/B)) |
| Minimum Spanning Tree | O((V + E)/B · log_{M/B}(V/B)) |

---

## 159.7 Practical Considerations

### SSD vs HDD

| Property | HDD | SSD |
|---|---|---|
| Random read | ~10 ms | ~100 μs |
| Sequential read | ~200 MB/s | ~3 GB/s |
| Random/Sequential ratio | 1000:1 | 30:1 |

SSDs are more forgiving for random access, but sequential access is still 30× faster. External memory algorithms are still important for SSDs.

### Parallel I/O

Modern SSDs can handle multiple concurrent reads. Algorithms should:
- Issue multiple I/O requests in parallel
- Use prefetching to hide latency
- Process data while waiting for I/O

### Memory-Mapped Files

OS provides virtual memory abstractions over files. The OS handles paging, but you can improve performance by:
- Accessing data sequentially
- Using `madvise()` to hint access patterns
- Keeping working set smaller than RAM

---

## 159.8 Dry Run: External Merge Sort

Sort 16 elements: [15, 3, 12, 8, 1, 20, 5, 18, 7, 14, 2, 11, 19, 6, 9, 16]
M = 4, B = 1

**Phase 1: Create runs**

| Run | Elements | Sorted |
|---|---|---|
| 1 | [15, 3, 12, 8] | [3, 8, 12, 15] |
| 2 | [1, 20, 5, 18] | [1, 5, 18, 20] |
| 3 | [7, 14, 2, 11] | [2, 7, 11, 14] |
| 4 | [19, 6, 9, 16] | [6, 9, 16, 19] |

**Phase 2: Merge passes** (k = M/B = 4)

**Pass 1**: Merge all 4 runs at once (since k = 4)
- 4-way merge of [3,8,12,15], [1,5,18,20], [2,7,11,14], [6,9,16,19]
- Result: [1, 2, 3, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 18, 19, 20]

**I/O count**:
- Phase 1: 16 reads + 16 writes = 32 I/Os
- Phase 2: 16 reads + 16 writes = 32 I/Os
- Total: 64 I/Os

---

## 159.9 Complexity Analysis

| Algorithm | I/O Complexity | Notes |
|---|---|---|
| External Merge Sort | O((N/B) · log_{M/B}(N/B)) | Standard |
| B-Tree Search | O(log_B N) | Point query |
| B-Tree Insert | O(log_B N) | May split nodes |
| B-Tree Range Query | O(log_B N + K/B) | Scan K results |
| External BFS | O((V+E)/B · log_{M/B}(V/B)) | Level-synchronous |
| Cache-oblivious Sort | O((N/B) · log_{M/B}(N/B)) | No M/B knowledge needed |

### Comparison with Internal Algorithms

| Problem | Internal (RAM) | External (Disk) |
|---|---|---|
| Sorting | O(N log N) comparisons | O((N/B) log_{M/B}(N/B)) I/Os |
| Search | O(log N) comparisons | O(log_B N) I/Os |
| BFS | O(V + E) | O((V+E)/B · log_{M/B}(V/B)) |

---

## 159.10 Exercises

### Conceptual

1. **Why is random access so much slower than sequential access on HDDs?** What about SSDs?
2. **What's the difference between the I/O model and the comparison model?** How does it change the lower bounds?
3. **Why are cache-oblivious algorithms useful?** What advantages do they have over cache-aware algorithms?

### Implementation

4. **Implement external merge sort** with a simulation of disk I/O. Count the number of block transfers.
5. **Implement a B-Tree** with disk page simulation. Test insert, delete, and range query operations.
6. **Implement external BFS** on a graph stored in a file. Measure I/O operations.

### Challenge

7. **Design a cache-oblivious matrix multiplication** algorithm and analyze its I/O complexity.
8. **Implement a B+ Tree** with linked leaves and measure range query performance vs. a standard B-Tree.

---

## 159.11 Interview Questions

1. **Q**: What is the external memory model and why is it important?
   **A**: It models algorithms that process data too large for RAM, with fast memory of size M, blocks of size B, and a goal of minimizing I/O operations. Important for databases, file systems, and big data processing.

2. **Q**: How does external merge sort work?
   **A**: Phase 1: Read M elements, sort in memory, write sorted run. Phase 2: Merge M/B runs at a time using a priority queue. Total I/O: O((N/B) · log_{M/B}(N/B)).

3. **Q**: Why are B-Trees preferred over binary search trees for disk storage?
   **A**: B-Trees have height O(log_B N) vs O(log₂ N) for BSTs. With B = 1024, a B-Tree with 1 billion keys has height ~3, vs ~30 for a BST. Each level is one disk access.

4. **Q**: What's the difference between cache-aware and cache-oblivious algorithms?
   **A**: Cache-aware algorithms know M and B and optimize for them. Cache-oblivious algorithms don't know M/B but use recursive decomposition to automatically achieve optimal I/O complexity.

5. **Q**: How would you sort 100 GB of data on a machine with 8 GB of RAM?
   **A**: Use external merge sort. Phase 1: Create sorted runs of 8 GB each (13 runs). Phase 2: Merge runs in groups of ~2 million (M/B). The I/O complexity is O((N/B) · log_{M/B}(N/B)).

---

## 159.12 Cross-References

- **Sorting**: [Chapter 108](ch108-dsu-on-tree-rerooting.md) — internal sorting algorithms used within runs
- **B-Trees**: [Chapter 104](ch104-cartesian-tournament-trees.md) — disk-friendly search trees
- **Graph Algorithms**: [Chapter 120](ch120-bwt-fmindex.md) — BFS, DFS, shortest paths
- **Hash Tables**: [Chapter 101](ch101-rope-gap-buffer.md) — external hashing techniques
- **Parallel Algorithms**: [Chapter 158](ch158-succinct-ds.md) — parallel I/O and concurrent access
- **Database Indexing**: [Chapter 160](ch160-parallel-algorithms.md) — practical applications of B-Trees
