# Chapter 91: Profiling and Benchmarking

## Prerequisites

- C++ basics (Chapters 1-10)
- Command line tools
- Basic algorithms and data structures (Chapters 20-50)

## Interview Frequency: ★★

Profiling skills show engineering maturity. **Google**, **Amazon**, and **Meta** value candidates who can measure, analyze, and optimize performance. Knowing how to profile demonstrates that you write production-quality code, not just algorithmically correct solutions.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Time measurement | ★★★ | Easy | chrono, timeit |
| Memory profiling | ★★ | Medium | Valgrind, sanitizers |
| Benchmark methodology | ★★ | Medium | Proper measurement |
| CPU profiling | ★★ | Medium | perf, gprof |
| Cache profiling | ★ | Hard | perf stat, cachegrind |

---

## 91.1 Why Profile?

### Definition

Profiling is the dynamic analysis of a program's resource consumption (time, memory, I/O) during execution. It identifies bottlenecks — the 20% of code causing 80% of slowdowns.

### Motivation

Premature optimization is the root of all evil (Knuth). But so is ignoring performance entirely. Profiling bridges the gap: it tells you *where* to optimize based on evidence, not intuition.

### Intuition

Imagine a relay race where one runner is much slower than the rest. No matter how fast the other runners go, the total time is dominated by the slowest. Profiling finds that slow runner.

### The Profiling Workflow

```
1. Define the performance goal (latency, throughput, memory)
2. Write a benchmark that exercises the target code path
3. Profile to find bottlenecks
4. Optimize the bottleneck
5. Re-profile to verify improvement
6. Repeat until goal is met
```

---

## 91.2 Measuring Time

### Wall Clock vs CPU Time

| Metric | What It Measures | Use When |
|---|---|---|
| Wall clock time | Actual elapsed time | I/O-bound, real-time systems |
| CPU time | Time CPU spent on your process | CPU-bound algorithms |
| User CPU | Time in user-space code | Algorithm analysis |
| System CPU | Time in kernel (syscalls) | I/O optimization |

### C++ Measurement with `<chrono>`

```cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <algorithm>
#include <random>
#include <numeric>

// High-precision timer utility
class Timer {
    using Clock = std::chrono::high_resolution_clock;
    using Microseconds = std::chrono::microseconds;
    Clock::time_point start;
    std::string label;

public:
    Timer(const std::string& label = "") : label(label) {
        start = Clock::now();
    }

    ~Timer() {
        auto end = Clock::now();
        auto us = std::chrono::duration_cast<Microseconds>(end - start).count();
        if (!label.empty())
            std::cout << label << ": " << us / 1000.0 << " ms\n";
    }

    double elapsedMs() {
        auto end = Clock::now();
        return std::chrono::duration_cast<Microseconds>(end - start).count() / 1000.0;
    }
};

// Benchmark function with statistics
template<typename Func>
struct BenchmarkResult {
    double mean, median, stddev, min, max;
    int iterations;
};

template<typename Func>
BenchmarkResult<Func> benchmark(Func f, int iterations = 100, int warmup = 5) {
    // Warmup runs
    for (int i = 0; i < warmup; i++) f();

    std::vector<double> times;
    times.reserve(iterations);

    for (int i = 0; i < iterations; i++) {
        auto start = std::chrono::high_resolution_clock::now();
        f();
        auto end = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count() / 1e6;
        times.push_back(ms);
    }

    std::sort(times.begin(), times.end());
    double sum = std::accumulate(times.begin(), times.end(), 0.0);
    double mean = sum / iterations;
    double median = times[iterations / 2];
    double sqSum = 0;
    for (double t : times) sqSum += (t - mean) * (t - mean);
    double stddev = std::sqrt(sqSum / iterations);

    BenchmarkResult<Func> result;
    result.mean = mean;
    result.median = median;
    result.stddev = stddev;
    result.min = times.front();
    result.max = times.back();
    result.iterations = iterations;
    return result;
}

int main() {
    const int N = 1000000;
    std::vector<int> arr(N);
    std::mt19937 rng(42);
    for (int& x : arr) x = rng() % 1000000;

    // Benchmark std::sort
    auto sortResult = benchmark([&]() {
        std::vector<int> copy = arr;
        std::sort(copy.begin(), copy.end());
    }, 50);

    std::cout << "std::sort (" << N << " elements):\n";
    std::cout << "  Mean: " << sortResult.mean << " ms\n";
    std::cout << "  Median: " << sortResult.median << " ms\n";
    std::cout << "  Stddev: " << sortResult.stddev << " ms\n";
    std::cout << "  Range: [" << sortResult.min << ", " << sortResult.max << "] ms\n";

    // Benchmark linear search
    int target = arr[N / 2];
    auto searchResult = benchmark([&]() {
        volatile auto it = std::find(arr.begin(), arr.end(), target);
        (void)it;
    }, 1000);

    std::cout << "\nLinear search:\n";
    std::cout << "  Mean: " << searchResult.mean << " ms\n";
    std::cout << "  Median: " << searchResult.median << " ms\n";

    return 0;
}
```

### Python Measurement

```python
import time
import statistics
from typing import Callable, List

def benchmark(func: Callable, iterations: int = 100, warmup: int = 5) -> dict:
    """Benchmark a function with warmup and statistics."""
    # Warmup
    for _ in range(warmup):
        func()

    times: List[float] = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        func()
        end = time.perf_counter_ns()
        times.append((end - start) / 1e6)  # Convert to ms

    times.sort()
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': times[0],
        'max': times[-1],
        'iterations': iterations,
    }

# Example: Compare list sort vs manual sort
import random

data = [random.randint(0, 1000000) for _ in range(100000)]

result_builtin = benchmark(lambda: sorted(data))
print(f"sorted() builtin: mean={result_builtin['mean']:.3f}ms, "
      f"median={result_builtin['median']:.3f}ms")

# timeit module (standard library)
import timeit

# Quick one-liner benchmark
elapsed = timeit.timeit(lambda: sorted(data), number=50) / 50
print(f"timeit: {elapsed * 1000:.3f}ms per iteration")
```

### Java Measurement

```java
import java.util.*;

public class Benchmark {
    static <T> Map<String, Double> benchmark(Runnable func, int iterations, int warmup) {
        // Warmup
        for (int i = 0; i < warmup; i++) func.run();

        List<Double> times = new ArrayList<>();
        for (int i = 0; i < iterations; i++) {
            long start = System.nanoTime();
            func.run();
            long end = System.nanoTime();
            times.add((end - start) / 1e6);
        }

        Collections.sort(times);
        double sum = times.stream().mapToDouble(d -> d).sum();
        double mean = sum / iterations;
        double median = times.get(iterations / 2);
        double variance = times.stream().mapToDouble(d -> (d - mean) * (d - mean)).sum() / iterations;

        Map<String, Double> result = new LinkedHashMap<>();
        result.put("mean", mean);
        result.put("median", median);
        result.put("stddev", Math.sqrt(variance));
        result.put("min", times.get(0));
        result.put("max", times.get(iterations - 1));
        return result;
    }

    public static void main(String[] args) {
        int[] arr = new Random(42).ints(1_000_000).toArray();

        var result = benchmark(() -> {
            int[] copy = arr.clone();
            Arrays.sort(copy);
        }, 50, 5);

        System.out.println("Arrays.sort (1M elements): " + result);
    }
}
```

---

## 91.3 Benchmark Best Practices

### The Golden Rules

| Practice | Why | Example |
|---|---|---|
| Warm up the JIT/cache | First runs include compilation, cold cache | Discard first 5 runs |
| Run many iterations | Reduces variance from OS scheduling | 100+ iterations |
| Report median, not mean | Median is robust to outliers | `times[n/2]` after sort |
| Prevent dead-code elimination | Compiler may optimize away "unused" results | Use `volatile` or return value |
| Control input data | Random input varies between runs | Fix random seed |
| Report distribution | Mean ± stddev reveals stability | Show min/median/p95/max |
| Isolate the measurement | Don't include setup/teardown in timing | Time only the hot loop |
| Use consistent environment | Background tasks, CPU throttling affect results | Close other apps, pin CPU |

### Preventing Compiler Optimization (C++)

```cpp
// BAD: Compiler may remove the entire loop
for (int i = 0; i < N; i++) {
    computeSomething();  // Result unused!
}

// GOOD: Use volatile to prevent elimination
volatile int sink;
for (int i = 0; i < N; i++) {
    sink = computeSomething();
}

// BETTER: Use DoNotOptimize (Google Benchmark style)
template<typename T>
void DoNotOptimize(T&& val) {
    asm volatile("" : "+r,m"(val) : : "memory");
}

for (int i = 0; i < N; i++) {
    DoNotOptimize(computeSomething());
}
```

### Statistical Rigor

```python
import statistics

def robust_benchmark(func, iterations=200):
    """Benchmark with outlier detection and confidence intervals."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        func()
        end = time.perf_counter_ns()
        times.append((end - start) / 1e6)

    # Remove outliers (beyond 2 standard deviations)
    mean = statistics.mean(times)
    stdev = statistics.stdev(times)
    filtered = [t for t in times if abs(t - mean) < 2 * stdev]

    n = len(filtered)
    mean = statistics.mean(filtered)
    stderr = statistics.stdev(filtered) / (n ** 0.5)

    return {
        'mean': mean,
        'ci_95': (mean - 1.96 * stderr, mean + 1.96 * stderr),
        'removed_outliers': len(times) - len(filtered),
        'samples': n,
    }
```

---

## 91.4 CPU Profiling Tools

### Tool Comparison

| Tool | Type | Overhead | Granularity | Platform |
|---|---|---|---|---|
| `gprof` | Sampling + instrumentation | Medium | Function-level | Linux |
| `perf` | Hardware counters | Low | Instruction-level | Linux |
| `valgrind --tool=callgrind` | Instrumentation | Very high | Instruction-level | Linux/Mac |
| `Instruments` | Sampling | Low | Function + source | macOS |
| `Visual Studio Profiler` | Sampling | Low | Function + source | Windows |
| `gperftools (CPU profiler)` | Sampling | Low | Function-level | Linux |
| `VTune` | Hardware counters | Low | Instruction-level | Cross-platform |
| `FlameGraphs` | Visualization | N/A | Stack-level | Cross-platform |

### Using `perf` (Linux)

```bash
# Record CPU profile
perf record -g ./my_program

# View report (interactive)
perf report

# Generate flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Count hardware events
perf stat -e cache-misses,cache-references,branch-misses,instructions ./my_program

# Profile specific event
perf record -e cpu-cycles -g ./my_program
```

### Using `gprof`

```bash
# Compile with profiling flags
g++ -pg -O2 -o my_program my_program.cpp

# Run (generates gmon.out)
./my_program

# View profile
gprof my_program gmon.out > profile.txt
```

### Using `valgrind/callgrind`

```bash
# Run with callgrind
valgrind --tool=callgrind ./my_program

# View with KCachegrind
kcachegrind callgrind.out.12345
```

### Flame Graphs

Flame graphs visualize stack traces as a heatmap. The x-axis shows the stack profile population (not time), and the y-axis shows stack depth. Wide bars = frequently sampled functions.

```
Generating a flame graph:
1. Record stack samples: perf record -g ./program
2. Collapse stacks: perf script | stackcollapse-perf.pl
3. Generate SVG: flamegraph.pl > out.svg

Reading a flame graph:
- Wide bars = hot functions (high CPU%)
- Plateaus = functions that do significant work
- Narrow spikes = functions called briefly
- Look for wide bars near the top = leaf functions to optimize
```

---

## 91.5 Memory Profiling

### Memory Issues to Detect

| Issue | Description | Tool |
|---|---|---|
| Memory leaks | Allocated but never freed | Valgrind, ASan |
| Buffer overflow | Write past allocation boundary | ASan, MSan |
| Use after free | Access freed memory | ASan |
| Double free | Free same memory twice | ASan |
| Uninitialized read | Read before write | MSan, Valgrind |
| Excessive allocation | Too many mallocs | Heaptrack, massif |

### Address Sanitizer (ASan)

```bash
# Compile with ASan
g++ -fsanitize=address -g -o my_program my_program.cpp

# Run (will catch memory errors at runtime)
./my_program

# Example output for buffer overflow:
# ==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x...
```

### Valgrind Memcheck

```bash
# Full memory check
valgrind --leak-check=full --show-leak-kinds=all ./my_program

# Example output:
# ==12345== 40 bytes in 1 blocks are definitely lost in loss record 1 of 1
# ==12345==    at 0x...: malloc (vg_replace_malloc.c:...)
# ==12345==    by 0x...: main (my_program.cpp:10)
```

### Heap Profiling with `massif`

```bash
# Profile heap usage over time
valgrind --tool=massif ./my_program

# View results
ms_print massif.out.12345
```

### Memory Profiling in Python

```python
import tracemalloc
import linecache

def profile_memory():
    """Profile memory usage with tracemalloc."""
    tracemalloc.start()

    # Code to profile
    data = [list(range(1000)) for _ in range(10000)]

    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    print("[ Top 10 memory allocations ]")
    for stat in top_stats[:10]:
        print(stat)

    current, peak = tracemalloc.get_traced_memory()
    print(f"\nCurrent: {current / 1024 / 1024:.1f} MB")
    print(f"Peak: {peak / 1024 / 1024:.1f} MB")
    tracemalloc.stop()

profile_memory()
```

---

## 91.6 Cache Profiling

### Using `perf stat` for Cache Statistics

```bash
# Count cache events
perf stat -e cache-misses,cache-references,L1-dcache-load-misses,LLC-load-misses ./my_program

# Example output:
#     1,234,567      cache-misses
#    12,345,678      cache-references
#     9.99%          cache miss rate
```

### Using `cachegrind` (Valgrind)

```bash
# Profile cache behavior
valgrind --tool=cachegrind ./my_program

# View with KCachegrind
cg_annotate cachegrind.out.12345
```

### Cache-Friendly Benchmark

```cpp
#include <iostream>
#include <chrono>
#include <vector>

int main() {
    const int N = 10000;
    const int TRIALS = 100;
    std::vector<std::vector<int>> matrix(N, std::vector<int>(N, 1));

    // Row-major (cache-friendly)
    auto start = std::chrono::high_resolution_clock::now();
    long long sum = 0;
    for (int t = 0; t < TRIALS; t++)
        for (int i = 0; i < N; i++)
            for (int j = 0; j < N; j++)
                sum += matrix[i][j];
    auto end = std::chrono::high_resolution_clock::now();
    auto rowTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    // Column-major (cache-unfriendly)
    start = std::chrono::high_resolution_clock::now();
    sum = 0;
    for (int t = 0; t < TRIALS; t++)
        for (int j = 0; j < N; j++)
            for (int i = 0; i < N; i++)
                sum += matrix[i][j];
    end = std::chrono::high_resolution_clock::now();
    auto colTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    std::cout << "Row-major: " << rowTime.count() << "ms\n";
    std::cout << "Col-major: " << colTime.count() << "ms\n";
    std::cout << "Speedup: " << (double)colTime.count() / rowTime.count() << "x\n";

    return 0;
}
```

---

## 91.7 Microbenchmark Anti-Patterns

### Common Mistakes

| Mistake | Problem | Fix |
|---|---|---|
| No warmup | First run includes JIT, cold cache | Add warmup iterations |
| Too few iterations | High variance, unreliable results | Run 100+ times |
| Measuring setup code | Inflates time with irrelevant work | Time only the hot path |
| Forgetting `volatile` | Compiler eliminates "unused" code | Use `volatile` or `DoNotOptimize` |
| Comparing debug builds | Debug mode adds checks, no optimization | Always benchmark `-O2`/`-O3` |
| Ignoring GC (Java/Python) | GC pauses inflate some iterations | Track GC time separately |
| Different input sizes | Not an apples-to-apples comparison | Fix all variables except the one being tested |

### Google Benchmark Style (C++)

```cpp
// Using Google Benchmark library
#include <benchmark/benchmark.h>
#include <vector>
#include <algorithm>

static void BM_Sort(benchmark::State& state) {
    std::vector<int> data(state.range(0));
    std::mt19937 rng(42);
    for (auto& x : data) x = rng();

    for (auto _ : state) {
        std::vector<int> copy = data;
        benchmark::DoNotOptimize(copy);
        std::sort(copy.begin(), copy.end());
        benchmark::DoNotOptimize(copy);
    }
    state.SetItemsProcessed(state.iterations() * state.range(0));
}

BENCHMARK(BM_Sort)->Arg(1000)->Arg(10000)->Arg(100000)->Unit(benchmark::kMillisecond);

BENCHMARK_MAIN();
```

---

## 91.8 Profiling Methodology

### The ICE Framework

1. **I**dentify the performance goal and constraints
2. **C**reate a representative benchmark
3. **E**xecute the profiling workflow

### Top-Down Profiling

```
1. Start with wall-clock time of the full program
2. Profile to find the top 3 hot functions
3. For each hot function:
   a. Analyze the algorithm complexity
   b. Check for cache misses (perf stat)
   c. Check for branch mispredictions
   d. Look for unnecessary allocations
4. Optimize the biggest bottleneck
5. Re-profile to verify improvement
6. Repeat until goal is met
```

### Bottom-Up Profiling

```
1. Start with a suspicious inner loop
2. Micro-benchmark it in isolation
3. Compare with known complexity bounds
4. If it's slower than expected:
   a. Check data structure choices
   b. Check memory access patterns
   c. Check for unnecessary copies
5. Optimize and re-benchmark
6. Integrate and verify end-to-end improvement
```

---

## Exercises

### Exercise 1: Benchmark Sorting Algorithms
Write a benchmark that compares `std::sort`, `std::stable_sort`, and a hand-written merge sort on arrays of size 10³, 10⁴, 10⁵, and 10⁶. Report median times and plot the results.

### Exercise 2: Memory Leak Detection
Write a C++ program with an intentional memory leak. Use Valgrind to detect it, and fix the leak. Show the Valgrind output before and after.

### Exercise 3: Cache Miss Analysis
Write two versions of matrix multiplication: naive (O(n³)) and blocked/tiled. Use `perf stat` to compare cache miss rates. Explain the difference.

### Exercise 4: Profiling a Real Program
Profile a program that reads a large file, processes each line, and writes results. Identify whether it's CPU-bound or I/O-bound, and optimize accordingly.

### Exercise 5: Python Profiling
Use `cProfile` and `line_profiler` to profile a Python function that computes Fibonacci numbers recursively vs iteratively. Compare the results.

```python
import cProfile

def fib_recursive(n):
    if n <= 1: return n
    return fib_recursive(n-1) + fib_recursive(n-2)

def fib_iterative(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

cProfile.run('fib_recursive(30)')
cProfile.run('fib_iterative(30)')
```

---

## Interview Questions

### Question 1: How would you find the bottleneck in a slow program?
**Answer**: I'd start by profiling with `perf` or a sampling profiler to identify hot functions. For each hot function, I'd check: (1) algorithm complexity — is it O(n²) when O(n log n) is possible? (2) cache behavior — are there cache misses from random access? (3) memory allocation — is it allocating/deallocating frequently? (4) I/O — is it blocked on disk or network? Then I'd optimize the biggest bottleneck first.

### Question 2: What's the difference between sampling and instrumentation profiling?
**Answer**: Sampling profilers periodically interrupt the program (e.g., every 1ms) and record the current stack. Low overhead but may miss short functions. Instrumentation profilers insert probes at function entry/exit, recording every call. Higher overhead but complete coverage. Sampling is preferred for production profiling; instrumentation is better for detailed analysis.

### Question 3: How do you benchmark code in the presence of garbage collection?
**Answer**: In GC languages (Java, Python, Go), I'd: (1) warm up the GC with several iterations before timing, (2) trigger a full GC before each measurement, (3) report percentiles (p50, p95, p99) rather than mean, since GC pauses create bimodal distributions, (4) use GC-aware profilers (JFR for Java) to separate GC time from application time.

### Question 4: Explain the difference between wall clock time and CPU time.
**Answer**: Wall clock time measures actual elapsed time, including I/O waits, context switches, and sleep. CPU time measures only the time the CPU spent executing your process. For CPU-bound tasks, they're similar. For I/O-bound tasks, wall clock time is much higher. Use wall clock for user-facing latency, CPU time for algorithm analysis.

### Question 5: How would you profile a program running in production?
**Answer**: Use low-overhead sampling profilers that can run continuously: e.g., `async-profiler` for Java, `py-spy` for Python, or eBPF-based tools for Linux. These add <1% overhead and can be attached to running processes without restart. For C++, use `perf` with `-p PID`. Always set up flame graph generation in your monitoring pipeline.

---

## Cross-References

- **Cache and Memory Hierarchy** (Chapter 89): Understanding cache behavior for profiling
- **Algorithm Complexity** (Chapter 15): Big-O analysis guides optimization priorities
- **Sorting Algorithms** (Chapters 30-36): Common benchmark targets
- **Hash Tables** (Chapter 55): Cache behavior differences vs arrays
- **Dynamic Memory** (Chapter 53): Allocation profiling and leak detection
- **Parallel Algorithms** (Chapter 145): Profiling concurrent code
- **System Design** (Chapter 160): Performance at scale

---

## Summary

| Metric | Tool | What to Look For |
|---|---|---|
| CPU time | chrono, perf | Hot functions, algorithmic bottlenecks |
| Memory | Valgrind, ASan | Leaks, overflows, excessive allocation |
| Cache misses | perf stat, cachegrind | Cache-unfriendly access patterns |
| Branch misprediction | perf stat | Branchless optimization opportunities |
| Wall clock | time, chrono | I/O bottlenecks, lock contention |
| Allocation rate | massif, tracemalloc | GC pressure, memory churn |
