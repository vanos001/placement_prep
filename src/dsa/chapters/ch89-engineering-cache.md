# Chapter 89: Cache and Memory Hierarchy

## Prerequisites

- Basic programming (Chapters 1-5)
- Understanding of arrays and pointers (Chapter 53)
- Algorithm complexity (Chapter 15)

## Interview Frequency: ★★

Cache awareness matters for high-performance code. **Google**, **Meta**, **Jane Street**, and trading firms test this knowledge. A cache-friendly O(n²) algorithm can beat a cache-unfriendly O(n log n) algorithm for practical input sizes.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Cache lines | ★★ | Medium | 64-byte blocks |
| Cache associativity | ★ | Hard | Set-associative |
| Cache-friendly code | ★★★ | Medium | Sequential access |
| Memory hierarchy | ★★ | Medium | Registers → L1 → L2 → L3 → RAM |
| Prefetching | ★ | Medium | Hardware/software prefetch |

---

## 89.1 Memory Hierarchy

### Definition

Modern computers have a hierarchy of storage levels, each trading capacity for speed. The CPU accesses registers in 0.3 ns but waits 100 ns for RAM — a 300x difference. Understanding this hierarchy is essential for writing fast code.

### Motivation

CPU speed has outpaced memory speed dramatically (the "memory wall"). A naive matrix multiply that misses cache can be 100x slower than a cache-friendly version, even with the same algorithmic complexity. Cache awareness is the difference between "fast in theory" and "fast in practice."

### Intuition

Think of a library. Your desk (registers) holds the book you're reading — instant access. The shelf nearby (L1 cache) holds related books — a few steps away. The library's main collection (RAM) requires walking across the building. Interlibrary loan (disk) takes days. You want to keep the books you need on your desk.

### The Hierarchy

| Level | Size | Latency | Bandwidth | Managed By |
|---|---|---|---|---|
| Registers | ~1 KB | 0.3 ns | 500+ GB/s | Compiler |
| L1 Cache | 32-64 KB | 1 ns | 200-400 GB/s | Hardware |
| L2 Cache | 256 KB-1 MB | 3-10 ns | 100-200 GB/s | Hardware |
| L3 Cache | 4-64 MB | 10-20 ns | 50-100 GB/s | Hardware |
| RAM | 8-128 GB | 50-100 ns | 10-50 GB/s | OS |
| SSD | 256 GB-4 TB | 25-100 μs | 1-7 GB/s | OS/Driver |
| HDD | 1-16 TB | 5-10 ms | 100-200 MB/s | OS/Driver |

**Key insight**: Each level is roughly 3-10x slower and 10x larger than the previous one.

### Why This Matters for Algorithms

```
Operation              Time (1 GHz CPU)
─────────────────────────────────────────
Register access        ~1 cycle
L1 cache hit           ~1-4 cycles
L2 cache hit           ~10 cycles
L3 cache hit           ~30-50 cycles
RAM access             ~100-300 cycles
Page fault (SSD)       ~100,000 cycles
Page fault (HDD)       ~10,000,000 cycles
```

A single RAM access costs as much as 100-300 instructions. If your algorithm causes frequent cache misses, the CPU stalls waiting for data.

---

## 89.2 Cache Lines

### Definition

Data is transferred between cache and RAM in fixed-size blocks called **cache lines**, typically 64 bytes. When you access a single byte, the entire 64-byte cache line is loaded.

### Motivation

This means accessing adjacent data is essentially free after the first access. A sequential scan of an array is much faster than random access, even though both are O(n) in theory.

### Intuition

Imagine moving houses. You don't carry one book at a time — you fill a box (cache line) and move the whole box. If the books you need happen to be in the same box, you save trips.

### Cache Line Impact

```
Array of 1 million 8-byte integers:
- Total size: 8 MB
- Cache lines: 125,000 (64 bytes each)
- L1 cache: ~512 cache lines (32 KB)

Sequential access: touches all 125,000 lines, but each line is used 8 times
Random access: may touch 125,000 different lines, each used once
```

### Code Example: Sequential vs Random Access

```cpp
#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <numeric>
#include <algorithm>

int main() {
    const int N = 10'000'000;
    const int ACCESS_COUNT = 10'000'000;
    const int TRIALS = 5;

    std::vector<int> arr(N);
    std::iota(arr.begin(), arr.end(), 0);

    // Sequential access
    auto start = std::chrono::high_resolution_clock::now();
    long long sum = 0;
    for (int t = 0; t < TRIALS; t++) {
        for (int i = 0; i < ACCESS_COUNT; i++)
            sum += arr[i % N];
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto seqTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    // Random access
    std::vector<int> indices(ACCESS_COUNT);
    std::mt19937 rng(42);
    for (int& idx : indices) idx = rng() % N;

    start = std::chrono::high_resolution_clock::now();
    sum = 0;
    for (int t = 0; t < TRIALS; t++) {
        for (int i = 0; i < ACCESS_COUNT; i++)
            sum += arr[indices[i]];
    }
    end = std::chrono::high_resolution_clock::now();
    auto randTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    std::cout << "Sequential: " << seqTime.count() << " ms\n";
    std::cout << "Random:     " << randTime.count() << " ms\n";
    std::cout << "Slowdown:   " << (double)randTime.count() / seqTime.count() << "x\n";

    return 0;
}
```

**Typical output**:
```
Sequential: 12 ms
Random:     95 ms
Slowdown:   7.9x
```

---

## 89.3 Cache Associativity

### Definition

A cache is **N-way set-associative** if each "set" (group of cache lines that can hold the same range of addresses) has N "ways" (slots). Common configurations:
- L1: 8-way set-associative
- L2: 8-way set-associative
- L3: 12-16-way set-associative

### Direct-Mapped vs Set-Associative

| Type | Description | Conflict Misses |
|---|---|---|
| Direct-mapped (1-way) | Each address maps to exactly one cache line | Many |
| Set-associative (N-way) | Each address can go in N slots | Fewer |
| Fully associative | Any address can go anywhere | Fewest (but expensive) |

### Cache Conflict Example

```cpp
// Two arrays that map to the same cache sets
// This causes "cache thrashing" with direct-mapped cache
int arr1[1024];  // Size = 4 KB
int arr2[1024];  // Same size, may conflict

// Interleaved access causes conflicts
for (int i = 0; i < 1024; i++) {
    sum += arr1[i] + arr2[i];  // Alternating accesses may evict each other
}
```

### Matrix Transpose and Cache Conflicts

```cpp
#include <iostream>
#include <vector>
#include <chrono>

int main() {
    const int N = 4096;
    std::vector<std::vector<int>> mat(N, std::vector<int>(N));
    std::vector<std::vector<int>> result(N, std::vector<int>(N));

    // Initialize
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            mat[i][j] = i * N + j;

    // Naive transpose (cache-unfriendly)
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            result[j][i] = mat[i][j];
    auto end = std::chrono::high_resolution_clock::now();
    auto naiveTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    // Blocked transpose (cache-friendly)
    const int BLOCK = 64;  // Fit in L1 cache
    start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; i += BLOCK)
        for (int j = 0; j < N; j += BLOCK)
            for (int ii = i; ii < std::min(i + BLOCK, N); ii++)
                for (int jj = j; jj < std::min(j + BLOCK, N); jj++)
                    result[jj][ii] = mat[ii][jj];
    end = std::chrono::high_resolution_clock::now();
    auto blockedTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    std::cout << "Naive transpose:  " << naiveTime.count() << " ms\n";
    std::cout << "Blocked transpose: " << blockedTime.count() << " ms\n";
    std::cout << "Speedup: " << (double)naiveTime.count() / blockedTime.count() << "x\n";

    return 0;
}
```

---

## 89.4 Cache-Friendly Patterns

### The Golden Rules

| Pattern | Cache Behavior | Speedup | Example |
|---|---|---|---|
| Sequential array scan | Excellent | 10-100x | Linear search, sum |
| Row-major 2D access | Good | 3-10x | Matrix multiply |
| Column-major 2D access | Poor | 1x (baseline) | Naive transpose |
| Linked list traversal | Poor | 1x | Pointer chasing |
| Hash table probe | Poor | 1x | Random bucket access |
| Tree BFS (array) | Moderate | 2-5x | Heap operations |
| Blocked/tiled loops | Excellent | 3-10x | Matrix multiply |
| Struct of Arrays (SoA) | Good | 2-5x | Particle simulation |
| Array of Structs (AoS) | Moderate | 1x (baseline) | Object storage |

### Array of Structs vs Struct of Arrays

```cpp
#include <iostream>
#include <vector>
#include <chrono>

struct Particle_AoS {
    float x, y, z;
    float vx, vy, vz;
    float mass;
    int id;
};

struct Particles_SoA {
    std::vector<float> x, y, z;
    std::vector<float> vx, vy, vz;
    std::vector<float> mass;
    std::vector<int> id;
};

int main() {
    const int N = 10'000'000;

    // AoS: Update positions
    std::vector<Particle_AoS> aos(N);
    for (int i = 0; i < N; i++) {
        aos[i] = {1,2,3, 0.1f,0.2f,0.3f, 1.0f, i};
    }

    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; i++) {
        aos[i].x += aos[i].vx * 0.016f;
        aos[i].y += aos[i].vy * 0.016f;
        aos[i].z += aos[i].vz * 0.016f;
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto aosTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    // SoA: Update positions
    Particles_SoA soa;
    soa.x.resize(N); soa.y.resize(N); soa.z.resize(N);
    soa.vx.resize(N); soa.vy.resize(N); soa.vz.resize(N);
    for (int i = 0; i < N; i++) {
        soa.x[i]=1; soa.y[i]=2; soa.z[i]=3;
        soa.vx[i]=0.1f; soa.vy[i]=0.2f; soa.vz[i]=0.3f;
    }

    start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; i++) {
        soa.x[i] += soa.vx[i] * 0.016f;
        soa.y[i] += soa.vy[i] * 0.016f;
        soa.z[i] += soa.vz[i] * 0.016f;
    }
    end = std::chrono::high_resolution_clock::now();
    auto soaTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    std::cout << "AoS update: " << aosTime.count() << " ms\n";
    std::cout << "SoA update: " << soaTime.count() << " ms\n";

    return 0;
}
```

**Why SoA is faster**: In AoS, each `Particle_AoS` is 28 bytes (7 floats + int). When you access `.x`, the cache line also loads `.y`, `.z`, `.vx`, etc. — but you only need x, vx. SoA lets you load only the data you need, improving cache utilization.

---

## 89.5 Cache-Oblivious Algorithms

### Definition

Cache-oblivious algorithms are designed to be cache-efficient *without knowing the cache parameters* (size, line size, associativity). They work well on any memory hierarchy.

### Motivation

Cache-aware algorithms require tuning block sizes to specific hardware. Cache-oblivious algorithms use recursive decomposition that naturally adapts to all cache levels.

### The Van Emde Boas Layout

For a complete binary tree, the Van Emde Boas (VEB) layout recursively partitions the tree and stores each partition contiguously. This achieves O(log_B n) cache misses for tree traversals, where B is the cache line size.

```
Standard BFS layout:    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
VEB layout:             [8, 4, 12, 2, 6, 10, 14, 1, 3, 5, 7, 9, 11, 13, 15]
```

### Cache-Oblivious Matrix Multiply

```cpp
// Cache-oblivious matrix multiply using recursive decomposition
void matrixMultiplyRecursive(
    const std::vector<std::vector<double>>& A,
    const std::vector<std::vector<double>>& B,
    std::vector<std::vector<double>>& C,
    int rowA, int colA, int rowB, int colB, int rowC, int colC,
    int size)
{
    if (size == 1) {
        C[rowC][colC] += A[rowA][colA] * B[rowB][colB];
        return;
    }

    int half = size / 2;

    // C11 = A11*B11 + A12*B21
    matrixMultiplyRecursive(A, B, C, rowA, colA, rowB, colB, rowC, colC, half);
    matrixMultiplyRecursive(A, B, C, rowA, colA + half, rowB + half, colB, rowC, colC, half);

    // C12 = A11*B12 + A12*B22
    matrixMultiplyRecursive(A, B, C, rowA, colA, rowB, colB + half, rowC, colC + half, half);
    matrixMultiplyRecursive(A, B, C, rowA, colA + half, rowB + half, colB + half, rowC, colC + half, half);

    // C21 = A21*B11 + A22*B21
    matrixMultiplyRecursive(A, B, C, rowA + half, colA, rowB, colB, rowC + half, colC, half);
    matrixMultiplyRecursive(A, B, C, rowA + half, colA + half, rowB + half, colB, rowC + half, colC, half);

    // C22 = A21*B12 + A22*B22
    matrixMultiplyRecursive(A, B, C, rowA + half, colA, rowB, colB + half, rowC + half, colC + half, half);
    matrixMultiplyRecursive(A, B, C, rowA + half, colA + half, rowB + half, colB + half, rowC + half, colC + half, half);
}
```

### Complexity Analysis

| Algorithm | Time | Cache Misses | Notes |
|---|---|---|---|
| Naive matrix multiply | O(n³) | O(n³ / B) | Cache-unfriendly |
| Blocked (cache-aware) | O(n³) | O(n³ / (B√M)) | Requires tuning |
| Cache-oblivious | O(n³) | O(n³ / (B√M)) | No tuning needed |

Where M = cache size, B = cache line size.

---

## 89.6 Prefetching

### Definition

Prefetching loads data into cache *before* it's needed, hiding memory latency. Modern CPUs do this automatically for sequential access patterns, but irregular patterns defeat the prefetcher.

### Hardware Prefetching

The CPU detects:
- **Sequential access**: Stride-1 prefetch (loads next cache line)
- **Stride access**: Constant-stride patterns (e.g., every 4th element)
- **Pointer chasing**: Limited support (Intel's L2 streamer)

### Software Prefetching

```cpp
#include <immintrin.h>  // For _mm_prefetch

// Prefetch data that will be needed soon
for (int i = 0; i < n; i++) {
    // Prefetch data for iteration i + lookahead
    if (i + 8 < n)
        _mm_prefetch((const char*)&data[i + 8], _MM_HINT_T0);

    process(data[i]);
}
```

### When Prefetching Helps

| Access Pattern | Hardware Prefetch | Software Prefetch |
|---|---|---|
| Sequential | Automatic | Not needed |
| Stride (small) | Automatic | Not needed |
| Stride (large) | May not detect | Helpful |
| Random/pointer chase | Poor | Helpful if predictable |
| Linked list traverse | Poor | Helpful with lookahead |

---

## 89.7 Practical Cache Optimization Techniques

### Technique 1: Loop Tiling/Blocking

```cpp
// Blocked matrix multiply
const int BLOCK = 64;
for (int i = 0; i < N; i += BLOCK)
    for (int j = 0; j < N; j += BLOCK)
        for (int k = 0; k < N; k += BLOCK)
            for (int ii = i; ii < min(i+BLOCK, N); ii++)
                for (int jj = j; jj < min(j+BLOCK, N); jj++)
                    for (int kk = k; kk < min(k+BLOCK, N); kk++)
                        C[ii][jj] += A[ii][kk] * B[kk][jj];
```

### Technique 2: Loop Fusion

```cpp
// BAD: Two passes over the data
for (int i = 0; i < N; i++) result[i] = a[i] + b[i];
for (int i = 0; i < N; i++) result[i] *= c[i];

// GOOD: One pass
for (int i = 0; i < N; i++) result[i] = (a[i] + b[i]) * c[i];
```

### Technique 3: Data Layout Transformation

```cpp
// BAD: Linked list (poor locality)
struct Node { int data; Node* next; };

// GOOD: Array-based (excellent locality)
struct DynamicArray { int* data; int size; };
```

### Technique 4: Padding to Avoid Conflicts

```cpp
// Pad to avoid cache line conflicts
struct PaddedElement {
    int value;
    char padding[60];  // Pad to 64 bytes (one cache line)
};
```

---

## 89.8 Code Example (Python)

```python
import time
import numpy as np

def naive_matrix_multiply(A, B, N):
    """Naive O(N^3) matrix multiply."""
    C = [[0] * N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            for k in range(N):
                C[i][j] += A[i][k] * B[k][j]
    return C

def blocked_matrix_multiply(A, B, N, block=64):
    """Cache-friendly blocked matrix multiply."""
    C = [[0] * N for _ in range(N)]
    for i in range(0, N, block):
        for j in range(0, N, block):
            for k in range(0, N, block):
                for ii in range(i, min(i + block, N)):
                    for jj in range(j, min(j + block, N)):
                        for kk in range(k, min(k + block, N)):
                            C[ii][jj] += A[ii][kk] * B[kk][jj]
    return C


def sequential_vs_random_access():
    """Demonstrate cache effects on access patterns."""
    N = 10_000_000
    arr = list(range(N))

    # Sequential access
    start = time.perf_counter()
    total = 0
    for i in range(N):
        total += arr[i]
    seq_time = time.perf_counter() - start

    # Random access
    import random
    random.seed(42)
    indices = [random.randint(0, N - 1) for _ in range(N)]

    start = time.perf_counter()
    total = 0
    for i in range(N):
        total += arr[indices[i]]
    rand_time = time.perf_counter() - start

    print(f"Sequential: {seq_time:.3f}s")
    print(f"Random:     {rand_time:.3f}s")
    print(f"Slowdown:   {rand_time / seq_time:.1f}x")


if __name__ == "__main__":
    sequential_vs_random_access()

    # NumPy is cache-friendly by default
    N = 512
    A = np.random.rand(N, N)
    B = np.random.rand(N, N)

    start = time.perf_counter()
    C = A @ B  # Uses optimized BLAS (cache-friendly)
    numpy_time = time.perf_counter() - start

    print(f"\nNumPy {N}x{N} multiply: {numpy_time:.4f}s")
```

---

## 89.9 Code Example (Java)

```java
public class CacheDemo {
    public static void main(String[] args) {
        int N = 10_000_000;
        int[] arr = new int[N];
        for (int i = 0; i < N; i++) arr[i] = i;

        // Sequential access
        long start = System.nanoTime();
        long sum = 0;
        for (int i = 0; i < N; i++) sum += arr[i];
        long seqTime = (System.nanoTime() - start) / 1_000_000;

        // Random access
        java.util.Random rng = new java.util.Random(42);
        int[] indices = new int[N];
        for (int i = 0; i < N; i++) indices[i] = rng.nextInt(N);

        start = System.nanoTime();
        sum = 0;
        for (int i = 0; i < N; i++) sum += arr[indices[i]];
        long randTime = (System.nanoTime() - start) / 1_000_000;

        System.out.println("Sequential: " + seqTime + "ms");
        System.out.println("Random:     " + randTime + "ms");
        System.out.println("Slowdown:   " + (double) randTime / seqTime + "x");

        // Blocked vs naive matrix transpose
        int M = 4096;
        int[][] mat = new int[M][M];
        int[][] result = new int[M][M];
        for (int i = 0; i < M; i++)
            for (int j = 0; j < M; j++)
                mat[i][j] = i * M + j;

        // Naive transpose
        start = System.nanoTime();
        for (int i = 0; i < M; i++)
            for (int j = 0; j < M; j++)
                result[j][i] = mat[i][j];
        long naiveTime = (System.nanoTime() - start) / 1_000_000;

        // Blocked transpose
        int BLOCK = 64;
        start = System.nanoTime();
        for (int i = 0; i < M; i += BLOCK)
            for (int j = 0; j < M; j += BLOCK)
                for (int ii = i; ii < Math.min(i + BLOCK, M); ii++)
                    for (int jj = j; jj < Math.min(j + BLOCK, M); jj++)
                        result[jj][ii] = mat[ii][jj];
        long blockedTime = (System.nanoTime() - start) / 1_000_000;

        System.out.println("\nNaive transpose:  " + naiveTime + "ms");
        System.out.println("Blocked transpose: " + blockedTime + "ms");
        System.out.println("Speedup: " + (double) naiveTime / blockedTime + "x");
    }
}
```

---

## Exercises

### Exercise 1: Cache Miss Analysis
Write a program that accesses a 2D array in row-major vs column-major order. Use `perf stat` to measure L1 cache misses for each. Explain the difference.

### Exercise 2: Blocked Matrix Multiply
Implement blocked matrix multiply with block sizes of 32, 64, 128, and 256. Benchmark each and determine which block size is optimal on your machine. Why?

### Exercise 3: Linked List vs Array
Compare linked list traversal vs array traversal for N = 10⁶ elements. Measure the time difference and explain it using cache line concepts.

### Exercise 4: AoS vs SoA
Implement a particle simulation with 10 million particles. Compare Array of Structs vs Struct of Array layouts. Measure the performance difference for position updates.

### Exercise 5: Cache-Oblivious Sort
Implement cache-oblivious merge sort using recursive decomposition. Compare its performance with standard merge sort on large arrays (N = 10⁷).

---

## Interview Questions

### Question 1: Why is sequential access faster than random access?
**Answer**: Modern CPUs load data in cache lines (typically 64 bytes). Sequential access benefits from spatial locality — after the first access, adjacent elements are already in cache. Random access causes cache misses for each element, and each miss costs 50-100ns to fetch from RAM vs ~1ns for a cache hit.

### Question 2: What is a cache line and why does it matter?
**Answer**: A cache line is the smallest unit of data transfer between cache and RAM, typically 64 bytes. It matters because accessing one byte loads the entire line. This means iterating over adjacent array elements is fast (each access uses the cached line), while accessing widely separated addresses causes repeated cache misses.

### Question 3: Explain loop tiling and when it helps.
**Answer**: Loop tiling (blocking) partitions iteration space into smaller blocks that fit in cache. It helps when the working set of a loop nest exceeds cache size. For example, naive matrix multiply reuses each element of B N times, but if B doesn't fit in cache, each reuse causes a miss. Tiling ensures each block of B fits in cache during its reuse window.

### Question 4: What's the difference between AoS and SoA? When would you use each?
**Answer**: AoS (Array of Structs) stores all fields of an object together. SoA (Struct of Arrays) stores each field in a separate array. SoA is better when you process one field across many objects (e.g., updating all x-coordinates), because the relevant data is contiguous in memory. AoS is better when you process all fields of a few objects (e.g., serializing one object).

### Question 5: How would you optimize a hash table for cache performance?
**Answer**: (1) Use open addressing instead of chaining to avoid pointer chasing. (2) Use Robin Hood hashing or hopscotch hashing to keep probes short. (3) Store keys and values inline (not via pointers). (4) Use a Swiss Table design (Google's `absl::flat_hash_map`) with metadata bytes packed into cache lines. (5) Consider cache-line-sized buckets with SIMD probing.

---

## Cross-References

- **Arrays** (Chapter 3): Contiguous memory, cache-friendly by default
- **Linked Lists** (Chapter 12): Cache-unfriendly pointer chasing
- **Hash Tables** (Chapter 55): Cache behavior depends on implementation
- **Sorting** (Chapters 30-36): Merge sort is cache-friendly, quicksort has good locality
- **Matrix Operations** (Chapter 75): Blocking for cache efficiency
- **Profiling** (Chapter 91): Tools to measure cache behavior
- **Parallel Algorithms** (Chapter 145): False sharing and cache coherence

---

## Summary

| Principle | Impact | How to Apply |
|---|---|---|
| Sequential access | 10-100x faster than random | Use arrays, iterate in order |
| Data locality | Keep related data together | SoA for batch processing |
| Cache line awareness | Align data to 64 bytes | Padding, struct layout |
| Prefetching | Hide memory latency | Sequential patterns, software prefetch |
| Loop tiling | Fit working set in cache | Block iteration for large data |
| Avoid pointer chasing | Reduce cache misses | Arrays over linked structures |
