# Chapter 137: Profiling Tools Reference

## Prerequisites
- Command line basics
- C/C++ compilation
- Basic understanding of CPU architecture (cache, branch prediction)

## Interview Frequency: ★★

Performance profiling is essential for competitive programming (time limits), systems programming, and production debugging. Knowing your tools — from simple timers to advanced sanitizers — separates good engineers from great ones.

> **Key Insight:** Don't guess where your code is slow. Measure first, optimize the bottleneck, then measure again. Profiling tools turn performance optimization from guesswork into science.

---

## 137.1 What Problem Does It Solve?

### Common Performance Questions

- "Why is my solution TLE (Time Limit Exceeded)?"
- "Which function is consuming the most CPU time?"
- "Is my code hitting cache misses?"
- "Does my code have memory leaks?"
- "Is there a data race in my multithreaded code?"
- "Am I triggering undefined behavior?"

Each of these has a dedicated tool. Using the right tool for the right question is the key skill.

### The Profiling Workflow

```
1. Measure baseline (chrono, time)
2. Identify bottleneck (perf, gprof, Instruments)
3. Analyze root cause (cache misses? branch misprediction? memory?)
4. Fix the issue
5. Measure again to confirm improvement
6. Repeat if needed
```

---

## 137.2 Time Measurement

### C++ chrono (Cross-Platform)

The simplest and most portable way to measure wall-clock time.

```cpp
#include <iostream>
#include <chrono>

template<typename Func>
double benchmark(Func f, int iterations = 100) {
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < iterations; i++) f();
    auto end = std::chrono::high_resolution_clock::now();
    return std::chrono::duration_cast<std::chrono::microseconds>(end - start).count()
           / 1000.0 / iterations;
}

int main() {
    // Benchmark a simple loop
    double ms = benchmark([]() {
        volatile int sum = 0;
        for (int i = 0; i < 1000000; i++) sum += i;
    }, 10);

    std::cout << "Average time: " << ms << "ms\n";
    return 0;
}
```

**Tips:**
- Use `volatile` to prevent the compiler from optimizing away the work.
- Run multiple iterations and average to reduce noise.
- Warm up the CPU/caches before measuring.
- Use `std::chrono::steady_clock` for reliable timing (not affected by system clock changes).

### Python timeit

```python
import timeit

# Measure a single expression
time_taken = timeit.timeit('sum(range(1000000))', number=100)
print(f"Total: {time_taken:.3f}s, Avg: {time_taken/100*1000:.3f}ms")

# Measure a function
def my_function():
    return sum(i * i for i in range(100000))

elapsed = timeit.timeit(my_function, number=10)
print(f"my_function: {elapsed/10*1000:.3f}ms per call")
```

### Command-Line Timing

```bash
# Unix time command
time ./my_program

# Output:
# real    0m1.234s    (wall clock)
# user    0m1.100s    (CPU time in user mode)
# sys     0m0.050s    (CPU time in kernel mode)
```

---

## 137.3 CPU Profiling

### perf (Linux)

`perf` is the standard Linux profiling tool. It samples CPU events at regular intervals to show where time is spent.

```bash
# Record CPU profile
perf record -g ./my_program

# View report (interactive)
perf report

# Record with call graph
perf record -g --call-graph dwarf ./my_program

# Record specific event (cache misses)
perf record -e cache-misses ./my_program

# Record specific event (branch mispredictions)
perf record -e branch-misses ./my_program

# Stat summary (no detailed recording)
perf stat ./my_program
```

**perf stat output example:**
```
 Performance counter stats for './my_program':

       1234.56 msec  task-clock                #    0.985 CPUs utilized
             12       context-switches          #    9.720 /sec
              3       cpu-migrations            #    2.430 /sec
          45678       page-faults               #   37.003 K/sec
    3456789012       cycles                    #    2.800 GHz
    2345678901       instructions              #    0.68  insn per cycle
     456789012       cache-references          #  370.030 M/sec
      12345678       cache-misses              #    2.704 % of all cache refs
      56789012       branch-instructions       #   46.003 M/sec
       1234567       branch-misses             #    2.175 % of all branches
```

**Key metrics:**
- **insn per cycle (IPC):** Higher is better. < 1.0 suggests memory stalls.
- **cache-misses %:** > 5% is concerning. Consider data layout changes.
- **branch-misses %:** > 5% suggests unpredictable branches. Consider branchless code.

### gprof (Linux)

GNU profiler. Requires compiling with `-pg` flag.

```bash
# Compile with profiling
g++ -pg -O2 my_program.cpp -o my_program

# Run (generates gmon.out)
./my_program

# View profile
gprof my_program gmon.out > profile.txt
```

**gprof output example:**
```
  %   cumulative   self              self     total
 time   seconds   seconds    calls   s/call   s/call  name
 45.2     0.452    0.452  1000000   0.0000   0.0000  sort_partition()
 23.1     0.683    0.231   100000   0.0000   0.0005  process_node()
 15.3     0.836    0.153        1   0.1530   0.8360  main()
  8.2     0.918    0.082  1000000   0.0000   0.0000  compare()
  8.2     1.000    0.082                             __libc_start_main
```

**Limitations:**
- Only profiles functions (not fine-grained lines).
- Doesn't work well with inlined functions.
- Inaccurate for short-running programs.

### Instruments (macOS)

Apple's built-in profiling tool with a GUI.

```bash
# Command-line usage
xctrace record --template 'Time Profiler' --launch -- ./my_program

# Open in Instruments GUI
open my_program.trace
```

Features: Time profiler, memory allocations, leaks, GPU activity, energy usage.

### Visual Studio Profiler (Windows)

Built into Visual Studio. Debug → Performance Profiler (Alt+F2).

Features: CPU usage, memory usage, GPU usage, .NET object allocation.

---

## 137.4 Memory Profiling

### Valgrind — Memcheck

Detects memory leaks, use-after-free, buffer overflows.

```bash
# Check for memory errors
valgrind --tool=memcheck --leak-check=full ./my_program

# With verbose output
valgrind --tool=memcheck --leak-check=full --show-reachable=yes ./my_program
```

**Output example:**
```
==12345== Invalid read of size 4
==12345==    at 0x4005A4: main (my_program.cpp:15)
==12345==  Address 0x5a5a5a4 is 0 bytes after a block of size 100 alloc'd
==12345==    at 0x4C2AB80: malloc (vg_replace_malloc.c:299)
==12345==    at 0x40057E: main (my_program.cpp:12)

==12345== LEAK SUMMARY:
==12345==    definitely lost: 50 bytes in 1 blocks
==12345==    indirectly lost: 0 bytes in 0 blocks
==12345==      possibly lost: 0 bytes in 0 blocks
==12345==    still reachable: 0 bytes in 0 blocks
```

**Limitations:** 10-50x slowdown. Not suitable for benchmarking, only for correctness.

### Valgrind — Callgrind

Call graph profiling with cache simulation.

```bash
# Record call graph
valgrind --tool=callgrind ./my_program

# View with GUI
kcachegrind callgrind.out.12345
```

---

## 137.5 Sanitizers

Sanitizers are compiler-inserted runtime checks. They're faster than Valgrind and catch many of the same issues.

### AddressSanitizer (ASan)

Catches: buffer overflows, use-after-free, use-after-return, memory leaks.

```bash
# Compile with ASan
g++ -fsanitize=address -g my_program.cpp -o my_program

# Run normally
./my_program
```

**What it catches:**
```cpp
int* p = new int[10];
p[10] = 42;  // Heap buffer overflow — ASan catches this!
delete[] p;
p[0] = 1;    // Use-after-free — ASan catches this!
```

**ASan output example:**
```
=================================================================
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x60200000eff8
    #0 0x4008a5 in main my_program.cpp:15
0x60200000eff8 is located 0 bytes to the right of 40-byte region [0x60200000efd0,0x60200000eff8)
allocated by thread T0 here:
    #0 0x7f1234567890 in operator new[](unsigned long)
    #1 0x400876 in main my_program.cpp:12
=================================================================
```

### UndefinedBehaviorSanitizer (UBSan)

Catches: signed integer overflow, null pointer dereference, misaligned access, invalid shift, etc.

```bash
g++ -fsanitize=undefined -g my_program.cpp -o my_program
```

**What it catches:**
```cpp
int x = INT_MAX;
x += 1;  // Signed integer overflow — UBSan catches this!

int* p = nullptr;
*p = 42;  // Null pointer dereference — UBSan catches this!
```

### ThreadSanitizer (TSan)

Catches: data races, deadlocks.

```bash
g++ -fsanitize=thread -g -pthread my_program.cpp -o my_program
```

**What it catches:**
```cpp
int shared = 0;
// Thread 1:
shared = 1;
// Thread 2:
shared = 2;
// Data race! TSan catches this.
```

### MemorySanitizer (MSan)

Catches: use of uninitialized memory.

```bash
g++ -fsanitize=memory -g my_program.cpp -o my_program
```

**Note:** MSan requires all linked libraries to also be instrumented. Use with `-stdlib=libc++` on Linux.

### Combining Sanitizers

```bash
# Combine ASan + UBSan (most common combo for competitive programming)
g++ -fsanitize=address,undefined -g my_program.cpp -o my_program

# Note: ASan and TSan cannot be combined (they conflict)
```

---

## 137.6 Cache and Branch Analysis

### perf for Cache Misses

```bash
# Count cache misses
perf stat -e cache-references,cache-misses ./my_program

# Detailed cache profiling
perf record -e cache-misses -g ./my_program
perf report

# L1/L2/L3 cache events
perf stat -e L1-dcache-load-misses,L1-dcache-loads ./my_program
perf stat -e LLC-load-misses,LLC-loads ./my_program
```

### perf for Branch Prediction

```bash
# Count branch mispredictions
perf stat -e branch-instructions,branch-misses ./my_program

# Profile branch-heavy code
perf record -e branch-misses -g ./my_program
perf report
```

### Cachegrind (Valgrind)

Detailed cache simulation.

```bash
valgrind --tool=cachegrind ./my_program
cg_annotate cachegrind.out.12345
```

---

## 137.7 Tool Comparison Table

| Tool | Platform | What It Measures | Overhead | Granularity |
|---|---|---|---|---|
| `chrono` | Cross-platform | Wall time | Negligible | Code-level |
| `time` | Unix | Wall + CPU time | Negligible | Program-level |
| `timeit` | Python | Wall time | Low | Expression-level |
| `perf` | Linux | CPU events, cache, branches | ~5% | Function/line |
| `gprof` | Linux | Function call profiling | ~10% | Function-level |
| `valgrind --tool=callgrind` | Linux/Mac | Call graph + cache sim | 10-50x | Instruction-level |
| `valgrind --tool=memcheck` | Linux/Mac | Memory errors | 10-50x | Instruction-level |
| `valgrind --tool=cachegrind` | Linux/Mac | Cache simulation | 5-20x | Function-level |
| AddressSanitizer | GCC/Clang | Memory errors | ~2x | Source-level |
| UBSan | GCC/Clang | Undefined behavior | ~10% | Source-level |
| TSan | GCC/Clang | Data races | 5-15x | Source-level |
| MSan | GCC/Clang | Uninitialized memory | ~2x | Source-level |
| Instruments | macOS | CPU, memory, energy | ~5% | Function/line |
| VS Profiler | Windows | CPU, memory | ~5% | Function/line |

---

## 137.8 Practical Workflow for Competitive Programming

### Step 1: Is it TLE or Wrong Answer?

```bash
# Time your solution
time ./solution < input.txt

# Compare with expected output
diff expected.txt <(./solution < input.txt)
```

### Step 2: If TLE — Profile the Hotspot

```bash
# Quick profile with perf
perf stat ./solution < input.txt

# If cache-misses% > 5%, consider:
# - Better data layout (array of structs → struct of arrays)
# - Smaller data types (int → short if range allows)
# - Sequential access patterns

# If branch-misses% > 5%, consider:
# - Branchless programming (ternary, bitwise tricks)
# - Sorting data before processing
# - Using __builtin_expect() for likely/unlikely branches
```

### Step 3: If Wrong Answer — Check for Bugs

```bash
# ASan + UBSan (catches most bugs)
g++ -fsanitize=address,undefined -g solution.cpp -o solution_debug
./solution_debug < input.txt

# If multithreaded
g++ -fsanitize=thread -g -pthread solution.cpp -o solution_debug
./solution_debug < input.txt
```

### Step 4: If Memory Issues

```bash
# ASan for memory errors
g++ -fsanitize=address -g solution.cpp -o solution_debug
./solution_debug < input.txt

# Valgrind for detailed leak analysis
valgrind --tool=memcheck --leak-check=full ./solution < input.txt
```

---

## 137.9 Implementation — Benchmarking Harness

### C++ — Complete Benchmarking Utility

```cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <functional>

class Benchmark {
    std::string name;
    int iterations;
    std::vector<double> times;

public:
    Benchmark(std::string name, int iterations = 100)
        : name(name), iterations(iterations) {}

    template<typename Func>
    void run(Func f) {
        times.clear();
        times.reserve(iterations);

        // Warmup
        for (int i = 0; i < 3; i++) f();

        for (int i = 0; i < iterations; i++) {
            auto start = std::chrono::high_resolution_clock::now();
            f();
            auto end = std::chrono::high_resolution_clock::now();
            times.push_back(
                std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count()
            );
        }
    }

    void report() const {
        if (times.empty()) return;
        auto sorted = times;
        std::sort(sorted.begin(), sorted.end());

        double sum = std::accumulate(sorted.begin(), sorted.end(), 0.0);
        double mean = sum / sorted.size();
        double median = sorted[sorted.size() / 2];
        double p95 = sorted[(int)(sorted.size() * 0.95)];
        double p99 = sorted[(int)(sorted.size() * 0.99)];

        double sq_sum = 0;
        for (double t : sorted) sq_sum += (t - mean) * (t - mean);
        double stddev = std::sqrt(sq_sum / sorted.size());

        std::cout << "=== " << name << " ===" << std::endl;
        std::cout << "  Iterations: " << iterations << std::endl;
        std::cout << "  Mean:       " << mean / 1000.0 << " μs" << std::endl;
        std::cout << "  Median:     " << median / 1000.0 << " μs" << std::endl;
        std::cout << "  Stddev:     " << stddev / 1000.0 << " μs" << std::endl;
        std::cout << "  Min:        " << sorted.front() / 1000.0 << " μs" << std::endl;
        std::cout << "  Max:        " << sorted.back() / 1000.0 << " μs" << std::endl;
        std::cout << "  P95:        " << p95 / 1000.0 << " μs" << std::endl;
        std::cout << "  P99:        " << p99 / 1000.0 << " μs" << std::endl;
    }
};

int main() {
    Benchmark bm_sort("std::sort (1M ints)", 50);
    std::vector<int> data(1000000);
    std::iota(data.begin(), data.end(), 0);
    std::reverse(data.begin(), data.end());

    bm_sort.run([&]() {
        auto v = data;  // Copy (so sort has work to do)
        std::sort(v.begin(), v.end());
    });
    bm_sort.report();

    Benchmark bm_search("Binary search (1M)", 1000);
    bm_search.run([&]() {
        volatile int result = std::binary_search(data.begin(), data.end(), 500000);
    });
    bm_search.report();

    return 0;
}
```

### Python — Benchmarking Utility

```python
import time
import statistics

def benchmark(name, func, iterations=100, warmup=3):
    """Run a benchmark and report statistics."""
    # Warmup
    for _ in range(warmup):
        func()

    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        func()
        end = time.perf_counter_ns()
        times.append(end - start)

    times.sort()
    mean = statistics.mean(times)
    median = statistics.median(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0

    print(f"=== {name} ===")
    print(f"  Iterations: {iterations}")
    print(f"  Mean:       {mean/1000:.1f} μs")
    print(f"  Median:     {median/1000:.1f} μs")
    print(f"  Stddev:     {stdev/1000:.1f} μs")
    print(f"  Min:        {times[0]/1000:.1f} μs")
    print(f"  Max:        {times[-1]/1000:.1f} μs")
    print(f"  P95:        {times[int(len(times)*0.95)]/1000:.1f} μs")


if __name__ == "__main__":
    import random

    data = list(range(1000000))
    random.shuffle(data)

    benchmark("sort (1M ints)", lambda: sorted(data), iterations=20)
    benchmark("list comprehension (100K)",
              lambda: [x * 2 for x in range(100000)], iterations=50)
```

---

## 137.10 Common Performance Pitfalls and Their Diagnoses

| Symptom | Likely Cause | Tool | Fix |
|---|---|---|---|
| High cache-misses % | Poor data locality | perf, Cachegrind | Restructure data layout |
| High branch-misses % | Unpredictable branches | perf | Branchless code, sort first |
| Low IPC (< 1.0) | Memory stalls | perf stat | Reduce memory access |
| Increasing memory | Memory leak | ASan, Valgrind | Fix allocation/deallocation |
| Crash after free | Use-after-free | ASan | Fix lifetime management |
| Intermittent crash | Data race | TSan | Add synchronization |
| Wrong output | UB (overflow, etc.) | UBSan | Fix the UB |
| Slow allocation | Heap fragmentation | Massif, Instruments | Pool allocator, stack alloc |

---

## 137.11 Exercises

1. **Profile a sorting algorithm:** Write implementations of bubble sort, insertion sort, and std::sort. Use `perf stat` to compare their cache-miss rates and branch-miss rates on random data.

2. **Find a memory leak:** Write a program with an intentional memory leak. Use ASan and Valgrind to find it. Compare the output formats.

3. **Cache-friendly vs cache-unfriendly:** Write two versions of matrix multiplication — one row-major, one column-major. Use `perf stat` or Cachegrind to show the cache-miss difference.

4. **Branch prediction experiment:** Write code that processes sorted vs unsorted arrays with a conditional branch. Use `perf stat` to measure branch-miss rates and show the performance difference.

5. **Data race detection:** Write a multithreaded counter with a deliberate data race. Use TSan to detect it. Fix the race and verify TSan is clean.

---

## 137.12 Interview Questions

1. **Q: How do you find the bottleneck in a slow program?**
   A: Use `perf record` + `perf report` on Linux, or Instruments on macOS. Look at the "self" column to find which function consumes the most time. Then drill into that function.

2. **Q: What's the difference between ASan and Valgrind?**
   A: ASan is a compiler-inserted runtime check (~2x slowdown), while Valgrind is a binary instrumentation tool (~10-50x slowdown). ASan catches similar bugs but is much faster. Valgrind doesn't require recompilation and has more tools (cachegrind, callgrind).

3. **Q: How do you detect a data race?**
   A: Use ThreadSanitizer (TSan) with `-fsanitize=thread`. It instruments memory accesses to detect unsynchronized reads/writes from different threads. Much faster than manual code review for complex concurrent code.

4. **Q: What is undefined behavior and why does it matter for performance?**
   A: UB is code behavior the standard doesn't define (signed overflow, null deref, etc.). The compiler can assume UB never happens and optimize accordingly, leading to surprising results. UBSan catches UB at runtime.

5. **Q: How would you optimize a program that has high cache-miss rates?**
   A: Improve data locality: use arrays instead of linked lists, access data sequentially, use smaller data types, apply struct-of-arrays layout, and prefetch data when possible.

6. **Q: What does it mean when `perf stat` shows "0.68 insn per cycle"?**
   A: The CPU is executing less than one instruction per cycle, meaning it's stalling — likely on memory accesses. A healthy program should achieve 1.0-3.0 IPC depending on the workload.

---

## 137.13 Cross-References

- **Chapter 136 (Complexity Analysis):** Profiling validates theoretical complexity with real measurements.
- **Chapter 138 (Optimization Techniques):** Once you find the bottleneck, optimization techniques tell you how to fix it.
- **Chapter 139 (Memory Management):** Memory profiling tools relate to understanding allocation patterns.
- **Chapter 140 (Cache Optimization):** Cache profiling tools directly inform cache optimization strategies.
- **Chapter 141 (Parallelism):** TSan and thread profiling are essential for parallel code.

---

## Summary

| Need | Tool |
|---|---|
| Measure time | chrono, time, timeit |
| Profile CPU hotspots | perf, gprof, Instruments |
| Find memory bugs | ASan, Valgrind Memcheck |
| Find UB | UBSan |
| Find race conditions | TSan |
| Find uninitialized reads | MSan |
| Cache analysis | perf stat, Cachegrind |
| Branch analysis | perf stat |
| Memory leak detection | ASan (leak sanitizer), Valgrind |
| Call graph profiling | gprof, Callgrind, perf |
