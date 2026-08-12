# Chapter 124: Branch Prediction and CPU Optimization

## Prerequisites
- CPU architecture basics (pipelining, caches)
- C/C++ programming
- Basic algorithm analysis

## Interview Frequency: ★★

Branch prediction awareness matters for writing high-performance code. **Google**, **Meta**, **Jane Street**, **Citadel**, and trading firms test this knowledge. Understanding how CPUs handle branches can make your code 2-10× faster in hot loops.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Branch misprediction cost | ★★ | Medium | ~15-20 cycles per misprediction |
| Branchless programming | ★★ | Medium | Replacing if/else with arithmetic |
| Data layout effects | ★★ | Medium | Sorted vs unsorted data |
| Profile-guided optimization | ★ | Medium | Compiler hints |
| CPU pipeline | ★★ | Medium | Understanding why branches hurt |

---

## 124.1 What Is Branch Prediction?

### Definition

A **branch** is any conditional instruction that changes the flow of execution — `if/else`, `for`, `while`, `switch`, ternary operators, etc.

**Branch prediction** is the CPU's attempt to guess which direction a branch will take *before* it's actually evaluated. Modern CPUs have deep pipelines (15-20 stages), so they need to speculatively execute instructions far ahead.

### Why It Matters

When the CPU predicts correctly, execution flows smoothly. When it **mispredicts**:
1. The speculative work is discarded
2. The pipeline is flushed
3. Execution resumes from the correct path

**Cost of misprediction**: ~15-20 cycles on modern CPUs. In a tight loop processing millions of elements, this adds up dramatically.

### The Pipeline

```
Instruction Pipeline (simplified):
Fetch → Decode → Execute → Memory → Writeback

With branch:
Fetch → Decode → [BRANCH] → ??? → ??? → ???
                    ↓
              Predict taken/not-taken
                    ↓
              Speculatively execute predicted path
                    ↓
              If wrong: flush pipeline, restart (15-20 cycle penalty)
```

### Types of Branch Predictors

| Predictor | How It Works | Accuracy |
|---|---|---|
| Static | Always predict "not taken" or based on direction | ~50-60% |
| 1-bit | Remember last outcome | ~85% |
| 2-bit saturating | Need 2 consecutive flips to change prediction | ~90% |
| Tournament | Multiple predictors, pick the best | ~95%+ |
| TAGE | Tagged geometric history length | ~97%+ |

Modern CPUs (Intel, AMD, ARM) use sophisticated predictors that track patterns in branch history.

---

## 124.2 The Classic Example: Sorted vs Unsorted Data

### Problem

Sum all elements ≥ 128 in an array. Compare performance on sorted vs unsorted data.

### Why Sorted Is Faster

- **Sorted data**: The condition `x >= 128` transitions from false to true exactly once. The branch predictor learns this pattern quickly and almost never mispredicts.
- **Unsorted data**: The condition alternates randomly. The predictor can't find a pattern, so ~50% misprediction rate.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>

int main() {
    const int N = 1000000;
    std::vector<int> arr(N);
    std::mt19937 rng(42);
    for (int& x : arr) x = rng() % 256;
    
    // Measure: unsorted array
    auto start = std::chrono::high_resolution_clock::now();
    long long sum = 0;
    for (int x : arr) if (x >= 128) sum += x;
    auto end = std::chrono::high_resolution_clock::now();
    auto unsorted_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    // Sort the array
    std::sort(arr.begin(), arr.end());
    
    // Measure: sorted array
    start = std::chrono::high_resolution_clock::now();
    sum = 0;
    for (int x : arr) if (x >= 128) sum += x;
    end = std::chrono::high_resolution_clock::now();
    auto sorted_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << "Unsorted: " << unsorted_us.count() << " μs\n";
    std::cout << "Sorted:   " << sorted_us.count() << " μs\n";
    std::cout << "Speedup:  " << (double)unsorted_us.count() / sorted_us.count() << "x\n";
    
    return 0;
}
```

### Expected Results

| Data | Branch Prediction | Misprediction Rate | Time |
|---|---|---|---|
| Unsorted | ~50% | ~50% | Slow |
| Sorted | ~99% | ~1% | Fast (2-3× faster) |

### Dry Run

Array (unsorted): [200, 50, 150, 80, 130, 20, 170, 90, ...]
Branch pattern:    [T,   F,  T,  F,  T,  F,  T,  F, ...]
Predictor: Can't learn alternating pattern → ~50% miss

Array (sorted): [20, 50, 80, 90, 130, 150, 170, 200, ...]
Branch pattern: [F,  F,  F,  F,  T,   T,   T,   T, ...]
Predictor: Learns pattern after first transition → ~0% miss

---

## 124.3 Branchless Programming

### Core Idea

Replace conditional branches with arithmetic operations that compute the same result without branching.

### Pattern 1: Branchless Conditional Sum

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>

int main() {
    const int N = 1000000;
    std::vector<int> arr(N);
    std::mt19937 rng(42);
    for (int& x : arr) x = rng() % 256;
    
    // Branchy version
    auto start = std::chrono::high_resolution_clock::now();
    long long sum_branchy = 0;
    for (int x : arr) {
        if (x >= 128) sum_branchy += x;
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto branchy_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    // Branchless version: (x >= 128) evaluates to 0 or 1
    start = std::chrono::high_resolution_clock::now();
    long long sum_branchless = 0;
    for (int x : arr) {
        sum_branchless += (x >= 128) * x;
    }
    end = std::chrono::high_resolution_clock::now();
    auto branchless_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << "Branchy:    " << branchy_us.count() << " μs (sum=" << sum_branchy << ")\n";
    std::cout << "Branchless: " << branchless_us.count() << " μs (sum=" << sum_branchless << ")\n";
    std::cout << "Speedup:    " << (double)branchy_us.count() / branchless_us.count() << "x\n";
    
    return 0;
}
```

### Why This Works

`(x >= 128)` compiles to a `cmp` + `setge` instruction (set byte if greater-or-equal), which produces 0 or 1. Then multiply by x. No branch instruction is emitted — the CPU pipeline never stalls.

### Pattern 2: Branchless Min/Max

```cpp
#include <iostream>
#include <algorithm>

// Branchy
int minBranchy(int a, int b) {
    if (a < b) return a;
    return b;
}

// Branchless
int minBranchless(int a, int b) {
    return b ^ ((a ^ b) & -(a < b));
    // If a < b: -(a < b) = -1 = all 1s, result = b ^ (a ^ b) = a
    // If a >= b: -(a < b) = 0, result = b ^ 0 = b
}

// Compiler intrinsic (best)
int minStd(int a, int b) {
    return std::min(a, b);  // Compiler often generates branchless code
}

int main() {
    int a = 42, b = 17;
    std::cout << "minBranchy(" << a << "," << b << ") = " << minBranchy(a, b) << "\n";
    std::cout << "minBranchless(" << a << "," << b << ") = " << minBranchless(a, b) << "\n";
    std::cout << "minStd(" << a << "," << b << ") = " << minStd(a, b) << "\n";
    
    // Performance test
    const int N = 10000000;
    volatile int result = 0;  // volatile to prevent optimization away
    
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; i++)
        result = minBranchy(i, N - i);
    auto end = std::chrono::high_resolution_clock::now();
    std::cout << "Branchy: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
              << " ms\n";
    
    start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; i++)
        result = minBranchless(i, N - i);
    end = std::chrono::high_resolution_clock::now();
    std::cout << "Branchless: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
              << " ms\n";
    
    return 0;
}
```

### Pattern 3: Branchless Absolute Value

```cpp
#include <iostream>

// Branchy
int absBranchy(int x) {
    if (x < 0) return -x;
    return x;
}

// Branchless (two's complement trick)
int absBranchless(int x) {
    int mask = x >> 31;  // arithmetic shift: -1 if negative, 0 if positive
    return (x + mask) ^ mask;
}

// Branchless with conditional move
int absCmov(int x) {
    return x < 0 ? -x : x;  // Compiler may use cmov instruction
}

int main() {
    for (int x : {-5, 3, 0, -100, 42}) {
        std::cout << "abs(" << x << ") = " << absBranchless(x) << "\n";
    }
    return 0;
}
```

---

## 124.4 Branchless Sorting Network

### Idea

Sorting networks use compare-and-swap operations that can be implemented branchlessly.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>

// Branchless compare-and-swap
inline void cmpSwap(int& a, int& b) {
    // Branchless: always compute both, conditionally assign
    int minVal = std::min(a, b);
    int maxVal = std::max(a, b);
    a = minVal;
    b = maxVal;
}

// Sorting network for 4 elements (optimal: 5 comparators)
void sort4(std::vector<int>& arr) {
    cmpSwap(arr[0], arr[1]);
    cmpSwap(arr[2], arr[3]);
    cmpSwap(arr[0], arr[2]);
    cmpSwap(arr[1], arr[3]);
    cmpSwap(arr[1], arr[2]);
}

// Sorting network for 8 elements
void sort8(std::vector<int>& arr) {
    // Pairwise comparisons
    cmpSwap(arr[0], arr[1]); cmpSwap(arr[2], arr[3]);
    cmpSwap(arr[4], arr[5]); cmpSwap(arr[6], arr[7]);
    // Merge
    cmpSwap(arr[0], arr[2]); cmpSwap(arr[1], arr[3]);
    cmpSwap(arr[4], arr[6]); cmpSwap(arr[5], arr[7]);
    cmpSwap(arr[0], arr[4]); cmpSwap(arr[1], arr[5]);
    cmpSwap(arr[2], arr[6]); cmpSwap(arr[3], arr[7]);
    cmpSwap(arr[1], arr[2]); cmpSwap(arr[3], arr[4]);
    cmpSwap(arr[5], arr[6]);
    cmpSwap(arr[2], arr[4]); cmpSwap(arr[3], arr[5]);
    cmpSwap(arr[1], arr[2]); cmpSwap(arr[3], arr[4]);
    cmpSwap(arr[5], arr[6]);
}

int main() {
    std::vector<int> arr = {42, 17, 8, 99, 23, 4, 55, 71};
    
    std::cout << "Before: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";
    
    sort8(arr);
    
    std::cout << "After:  ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";
    
    // Performance comparison
    const int N = 1000000;
    std::mt19937 rng(42);
    
    // std::sort
    std::vector<std::vector<int>> data(N, std::vector<int>(8));
    for (auto& v : data)
        for (int& x : v) x = rng() % 1000;
    
    auto start = std::chrono::high_resolution_clock::now();
    for (auto& v : data) std::sort(v.begin(), v.end());
    auto end = std::chrono::high_resolution_clock::now();
    auto std_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    // Sorting network
    for (auto& v : data)
        for (int& x : v) x = rng() % 1000;
    
    start = std::chrono::high_resolution_clock::now();
    for (auto& v : data) sort8(v);
    end = std::chrono::high_resolution_clock::now();
    auto net_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << "\nstd::sort:       " << std_us.count() << " μs\n";
    std::cout << "Sorting network: " << net_us.count() << " μs\n";
    
    return 0;
}
```

---

## 124.5 Conditional Move (CMOV) Instructions

### What Is CMOV?

Modern CPUs have **conditional move** instructions that select between two values without branching. The compiler can generate these from ternary operators or simple if/else.

```cpp
#include <iostream>

// This may compile to a branch
int maxBranchy(int a, int b) {
    if (a > b) return a;
    return b;
}

// This often compiles to CMOV
int maxCmov(int a, int b) {
    return a > b ? a : b;
}

int main() {
    // To check: compile with -S and look for 'cmov' instructions
    // g++ -O2 -S branch_cmov.cpp
    
    int a = 42, b = 17;
    std::cout << "max(" << a << "," << b << ") = " << maxCmov(a, b) << "\n";
    
    // Demonstrate with profile-guided optimization hint
    // __builtin_expect tells the compiler which branch is likely
    int x = 100;
    if (__builtin_expect(x > 50, 1)) {
        std::cout << "x is large (likely path)\n";
    } else {
        std::cout << "x is small (unlikely path)\n";
    }
    
    return 0;
}
```

### When CMOV Helps

CMOV is beneficial when:
- Both branches are cheap to compute
- The branch is unpredictable (random data)
- The computation is in a tight loop

CMOV may NOT help when:
- One branch is very expensive (division, memory access)
- The branch is highly predictable (sorted data)
- The compiler can optimize the branch better

---

## 124.6 Profile-Guided Optimization (PGO)

### What Is PGO?

The compiler uses runtime profiling data to make better optimization decisions, including branch prediction hints.

### How to Use PGO

```bash
# Step 1: Compile with profiling
g++ -O2 -fprofile-generate -o program program.cpp

# Step 2: Run with representative input
./program < typical_input.txt

# Step 3: Recompile using profile data
g++ -O2 -fprofile-use -o program program.cpp
```

### What PGO Does

- Identifies hot paths and cold paths
- Reorders code to improve instruction cache usage
- Provides branch prediction hints to the CPU
- Can inline frequently-called functions

```cpp
#include <iostream>
#include <vector>
#include <chrono>

// PGO can optimize this: the common case (index in range) is fast
int lookup(const std::vector<int>& table, int index) {
    if (index >= 0 && index < (int)table.size()) {
        return table[index];  // hot path
    }
    return -1;  // cold path
}

// PGO can also optimize branch ordering
int classify(int x) {
    if (x > 0) return 1;        // most common
    if (x == 0) return 0;       // less common
    return -1;                   // rare
}

int main() {
    std::vector<int> table = {10, 20, 30, 40, 50};
    
    // Simulate typical usage
    const int N = 1000000;
    volatile int result = 0;
    
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < N; i++) {
        result = lookup(table, i % 5);  // always in range
    }
    auto end = std::chrono::high_resolution_clock::now();
    std::cout << "Time: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
              << " ms\n";
    
    return 0;
}
```

---

## 124.7 Real-World Applications

### Application 1: Binary Search Optimization

Binary search has a highly predictable branch pattern (always goes one direction in sorted data). But the *comparison* branch can be optimized.

```cpp
#include <iostream>
#include <vector>
#include <chrono>
#include <random>

// Standard binary search
int binarySearch(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] == target) return mid;
        else if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

// Branchless binary search (using conditional moves)
int binarySearchBranchless(const std::vector<int>& arr, int target) {
    int lo = 0, n = arr.size();
    for (int step = n / 2; step > 0; step /= 2) {
        // Branchless: always update lo, but conditionally
        lo += (arr[lo + step] < target) ? step : 0;
    }
    return (lo < n && arr[lo] == target) ? lo : -1;
}

int main() {
    const int N = 1000000;
    std::vector<int> arr(N);
    for (int i = 0; i < N; i++) arr[i] = i * 2;
    
    std::mt19937 rng(42);
    std::vector<int> queries(100000);
    for (int& q : queries) q = rng() % (2 * N);
    
    // Benchmark standard
    auto start = std::chrono::high_resolution_clock::now();
    volatile int result = 0;
    for (int q : queries) result = binarySearch(arr, q);
    auto end = std::chrono::high_resolution_clock::now();
    auto std_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    // Benchmark branchless
    start = std::chrono::high_resolution_clock::now();
    for (int q : queries) result = binarySearchBranchless(arr, q);
    end = std::chrono::high_resolution_clock::now();
    auto bl_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << "Standard:   " << std_us.count() << " μs\n";
    std::cout << "Branchless: " << bl_us.count() << " μs\n";
    std::cout << "Speedup:    " << (double)std_us.count() / bl_us.count() << "x\n";
    
    return 0;
}
```

### Application 2: SIMD-Friendly Branchless Operations

When using SIMD (Single Instruction, Multiple Data), branches are impossible — everything must be branchless.

```cpp
#include <iostream>
#include <vector>
#include <chrono>
#include <random>

// Process array: clamp values to [0, 255]
void clampBranchy(std::vector<int>& arr) {
    for (int& x : arr) {
        if (x < 0) x = 0;
        if (x > 255) x = 255;
    }
}

void clampBranchless(std::vector<int>& arr) {
    for (int& x : arr) {
        x = x < 0 ? 0 : (x > 255 ? 255 : x);
    }
}

int main() {
    const int N = 1000000;
    std::vector<int> arr(N);
    std::mt19937 rng(42);
    for (int& x : arr) x = (int)(rng() % 600) - 200;  // range [-200, 399]
    
    auto arr_copy = arr;
    
    auto start = std::chrono::high_resolution_clock::now();
    clampBranchy(arr);
    auto end = std::chrono::high_resolution_clock::now();
    auto branchy_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    arr = arr_copy;
    start = std::chrono::high_resolution_clock::now();
    clampBranchless(arr);
    end = std::chrono::high_resolution_clock::now();
    auto branchless_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << "Branchy:    " << branchy_us.count() << " μs\n";
    std::cout << "Branchless: " << branchless_us.count() << " μs\n";
    
    return 0;
}
```

---

## 124.8 Compiler Optimizations

### What the Compiler Does

Modern compilers (GCC, Clang, MSVC) can:
1. **Eliminate branches**: Convert simple if/else to CMOV
2. **Reorder branches**: Put likely path first
3. **Inline functions**: Remove function call overhead
4. **Loop unrolling**: Reduce branch overhead per iteration

### How to Help the Compiler

```cpp
#include <iostream>

// Use __builtin_expect for branch hints (GCC/Clang)
#define LIKELY(x)   __builtin_expect(!!(x), 1)
#define UNLIKELY(x) __builtin_expect(!!(x), 0)

void process(int x) {
    if (LIKELY(x >= 0)) {
        // Normal case: process positive value
        std::cout << "Processing: " << x << "\n";
    } else {
        // Error case: negative value
        std::cout << "Error: negative value " << x << "\n";
    }
}

// Use [[likely]] and [[unlikely]] in C++20
void process20(int x) {
    if (x >= 0) [[likely]] {
        std::cout << "Processing: " << x << "\n";
    } else [[unlikely]] {
        std::cout << "Error: negative value " << x << "\n";
    }
}

int main() {
    process(42);
    process(-1);
    process20(42);
    process20(-1);
    return 0;
}
```

### Compiler Flags for Branch Optimization

```bash
# Profile-guided optimization
g++ -O2 -fprofile-generate -o prog prog.cpp
./prog
g++ -O2 -fprofile-use -o prog prog.cpp

# Branch hints
g++ -O2 -fprofile-arcs -o prog prog.cpp

# Auto-vectorization (forces branchless)
g++ -O3 -march=native -o prog prog.cpp
```

---

## Summary

| Scenario | Branch Behavior | Impact | Solution |
|---|---|---|---|
| Sorted data | Predictable | Fast | Natural |
| Random data | Unpredictable | Slow (15-20 cycles/mispredict) | Branchless |
| Hot loop | Many branches | Amplified | Branchless or CMOVs |
| Cold code | Doesn't matter | Negligible | Don't optimize |
| SIMD | No branches allowed | — | Must be branchless |

---

## Exercises

1. **Branchless Absolute Value**: Implement `abs(x)` without branches using the two's complement trick. Verify it works for INT_MIN.

2. **Branchless Clamping**: Write a branchless function that clamps an integer to the range [lo, hi].

3. **Sorting Network**: Implement a sorting network for 5 elements. How many comparators do you need?

4. **Benchmark Branch Prediction**: Write a benchmark that measures the branch misprediction penalty. Use `perf stat` to count branch misses.

5. **Branchless Binary Search**: Implement branchless binary search for 32-bit integers. Compare performance with standard binary search on random queries.

6. **Profile-Guided Optimization**: Compile a program with PGO and measure the improvement over standard compilation.

---

## Interview Questions

1. **Q**: Why does sorting an array before processing it with conditional branches make it faster?
   **A**: The branch predictor learns the pattern: all false values come before all true values (or vice versa). With only one transition point, the predictor achieves near-100% accuracy, eliminating misprediction penalties.

2. **Q**: When should you use branchless code vs regular branches?
   **A**: Use branchless when: (1) the branch is unpredictable (random data), (2) it's in a hot loop, (3) both branches are cheap to compute. Use regular branches when: (1) the branch is predictable, (2) one branch is much more expensive, (3) code clarity matters more than performance.

3. **Q**: What is a CMOV instruction and when does the compiler generate it?
   **A**: CMOV (conditional move) selects between two values based on a condition without branching. The compiler generates it for simple ternary expressions and if/else with cheap branches, especially with -O2 or higher.

4. **Q**: How does branch prediction interact with speculative execution?
   **A**: The CPU speculatively executes instructions along the predicted path. If the prediction is correct, these instructions are committed. If wrong, the speculative results are discarded and the pipeline is flushed, wasting 15-20 cycles.

5. **Q**: Can branch misprediction cause security vulnerabilities?
   **A**: Yes — Spectre and Meltdown exploits use speculative execution to leak information through cache side channels. The CPU speculatively accesses memory based on mispredicted branches, leaving traces in the cache that an attacker can detect.

---

## Cross-References

- **Chapter 123**: Cache Optimization — memory access patterns affect performance
- **Chapter 125**: SIMD and Vectorization — branchless code enables SIMD
- **Chapter 126**: Memory Hierarchy — understanding CPU caches
- **Chapter 10**: Sorting Algorithms — sorting networks
- **Chapter 30**: Binary Search — branchless binary search
- **Chapter 117**: Bit Manipulation — bit tricks for branchless code
