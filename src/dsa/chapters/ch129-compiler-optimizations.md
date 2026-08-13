# Chapter 129: Compiler Optimizations

## Prerequisites
- C/C++ basics
- Basic understanding of assembly (helpful but not required)
- How compilers work (high level)

## Interview Frequency: ★★

Understanding what compilers optimize helps you write better code and reason about performance. This knowledge is valuable at companies building **high-performance systems** (Google, Meta, Apple, NVIDIA, game studios).

---

## 129.1 Why Understand Compiler Optimizations?

### The Gap Between Source Code and Machine Code

What you write and what the CPU executes are very different things. Modern compilers (GCC, Clang, MSVC) perform dozens of optimization passes that can:
- **Eliminate** unnecessary computations
- **Reorder** instructions for better pipeline utilization
- **Vectorize** loops to process multiple elements at once
- **Inline** function calls to remove overhead

### When This Knowledge Matters

| Situation | Benefit |
|---|---|
| Performance-critical code | Know what the compiler can/cannot optimize |
| Debugging | Understand why code behaves unexpectedly |
| Interviews | Explain why O(n) can beat O(n log n) in practice |
| Systems programming | Write cache-friendly, vectorizable code |
| Competitive programming | Understand when "clever" code is actually slower |

---

## 129.2 Common Compiler Optimizations

### 1. Constant Folding

The compiler evaluates constant expressions at compile time.

```cpp
// What you write:
int x = 3 + 4 * 2;
int y = sizeof(int);

// What the compiler generates:
int x = 11;  // computed at compile time
int y = 4;   // known at compile time
```

### 2. Constant Propagation

The compiler tracks known constant values through the code.

```cpp
// What you write:
int foo() {
    const int n = 100;
    int arr[n];
    return arr[n/2];
}

// The compiler knows n=100 everywhere, optimizes accordingly
```

### 3. Dead Code Elimination

Code that can never be reached or whose result is never used is removed.

```cpp
// What you write:
int compute(int x) {
    int unused = x * x;  // result never used
    return x + 1;
}

// Compiler generates:
int compute(int x) {
    return x + 1;  // dead code removed
}
```

### 4. Function Inlining

The compiler replaces a function call with the function body, eliminating call overhead.

```cpp
// What you write:
inline int square(int x) { return x * x; }

int sum_of_squares(int a, int b) {
    return square(a) + square(b);
}

// Compiler may generate:
int sum_of_squares(int a, int b) {
    return a * a + b * b;  // no function call overhead
}
```

**When the compiler inlines:**
- Functions marked `inline`
- Small functions (typically < 100 lines)
- Functions called in hot loops
- With `-O2` or higher

**When it doesn't:**
- Virtual function calls (runtime dispatch)
- Recursive functions (partial inlining possible)
- Functions in shared libraries (unless LTO is enabled)

### 5. Loop Unrolling

The compiler replicates the loop body to reduce branch overhead.

```cpp
// What you write:
int sum = 0;
for (int i = 0; i < n; i++)
    sum += arr[i];

// Compiler may generate (unrolled by 4):
int sum = 0;
int i;
for (i = 0; i + 3 < n; i += 4)
    sum += arr[i] + arr[i+1] + arr[i+2] + arr[i+3];
for (; i < n; i++)
    sum += arr[i];
```

**Benefits:**
- Fewer branch instructions
- Better instruction pipeline utilization
- Enables more register allocation

**Drawbacks:**
- Larger code size (instruction cache pressure)
- Diminishing returns beyond 4-8x unrolling

### 6. Tail Call Optimization (TCO)

When the last action in a function is a recursive call, the compiler can reuse the current stack frame.

```cpp
// Tail-recursive (can be optimized):
int factorial_tail(int n, int acc = 1) {
    if (n <= 1) return acc;
    return factorial_tail(n - 1, n * acc);  // tail position
}

// NOT tail-recursive (cannot be optimized):
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);  // must multiply AFTER recursive call
}
```

**TCO transforms recursion into iteration**, preventing stack overflow for deep recursion.

### 7. Vectorization (SIMD)

The compiler uses SIMD (Single Instruction, Multiple Data) instructions to process multiple data elements simultaneously.

```cpp
// What you write:
void add_arrays(float* a, float* b, float* c, int n) {
    for (int i = 0; i < n; i++)
        c[i] = a[i] + b[i];
}

// Compiler may generate SIMD (SSE/AVX) instructions:
// - SSE: process 4 floats at once (128-bit)
// - AVX: process 8 floats at once (256-bit)
// - AVX-512: process 16 floats at once (512-bit)
```

**Requirements for auto-vectorization:**
- No loop-carried dependencies
- Data aligned in memory (compiler can handle unaligned, but slower)
- Simple loop body
- Use `-O3` or `-ftree-vectorize`

### 8. Common Subexpression Elimination (CSE)

If the same expression is computed multiple times, the compiler computes it once.

```cpp
// What you write:
double x = a * b + c;
double y = a * b - d;

// Compiler generates:
double temp = a * b;
double x = temp + c;
double y = temp - d;
```

### 9. Strength Reduction

Replace expensive operations with cheaper ones.

```cpp
// What you write:
for (int i = 0; i < n; i++)
    arr[i * 4] = i;

// Compiler may generate (replace multiply with add):
int idx = 0;
for (int i = 0; i < n; i++, idx += 4)
    arr[idx] = i;
```

**Common strength reductions:**
- Multiplication by power of 2 → bit shift
- Division by constant → multiply by reciprocal
- Modulo by power of 2 → bitwise AND

### 10. Loop-Invariant Code Motion (LICM)

Move computations that don't change inside a loop to before the loop.

```cpp
// What you write:
for (int i = 0; i < n; i++)
    arr[i] = x * y + i;  // x * y doesn't depend on i

// Compiler generates:
int temp = x * y;
for (int i = 0; i < n; i++)
    arr[i] = temp + i;
```

---

## 129.3 Optimization Levels

### GCC/Clang Flags

| Flag | Description | Compile Time | Code Quality | Binary Size |
|---|---|---|---|---|
| `-O0` | No optimization | Fastest | Poorest | Largest (debug info) |
| `-O1` | Basic optimizations | Medium | Good | Medium |
| `-O2` | Most optimizations | Slow | Better | Smaller |
| `-O3` | Aggressive (incl. vectorization) | Slowest | Best | May be larger |
| `-Os` | Optimize for size | Medium | Good | Smallest |
| `-Ofast` | O3 + fast-math | Slowest | Best* | May be larger |

*`-Ofast` may break IEEE 754 floating-point compliance.

### What Each Level Enables

```
-O0: No optimizations. Good for debugging.
-O1: Constant folding, dead code elimination, basic inlining.
-O2: All of O1 + loop optimizations, CSE, vectorization (basic), inlining heuristics.
-O3: All of O2 + aggressive inlining, loop unrolling, auto-vectorization, interprocedural optimizations.
-Os: Like O2 but prioritizes code size.
-Ofast: O3 + -ffast-math (relaxed FP precision) + -fallow-store-data-races.
```

### MSVC Flags

| Flag | Description |
|---|---|
| `/Od` | No optimization |
| `/O1` | Optimize for size |
| `/O2` | Optimize for speed |
| `/Ox` | Maximum optimization |
| `/fp:fast` | Fast floating-point (like `-ffast-math`) |

---

## 129.4 Practical Examples

### Example 1: Matrix Multiplication

```cpp
#include <iostream>
#include <vector>
#include <chrono>

// Naive matrix multiply (compiler can vectorize inner loop)
void matmul_naive(const double* A, const double* B, double* C, int n) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            double sum = 0;
            for (int k = 0; k < n; k++)
                sum += A[i * n + k] * B[k * n + j];
            C[i * n + j] = sum;
        }
}

// Cache-friendly version (loop reordering)
void matmul_cache_friendly(const double* A, const double* B, double* C, int n) {
    for (int i = 0; i < n * n; i++) C[i] = 0;
    for (int i = 0; i < n; i++)
        for (int k = 0; k < n; k++)
            for (int j = 0; j < n; j++)
                C[i * n + j] += A[i * n + k] * B[k * n + j];
}

int main() {
    const int n = 512;
    std::vector<double> A(n * n, 1.0), B(n * n, 1.0), C(n * n, 0.0);
    
    auto start = std::chrono::high_resolution_clock::now();
    matmul_naive(A.data(), B.data(), C.data(), n);
    auto end = std::chrono::high_resolution_clock::now();
    
    std::cout << "Naive: " 
              << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() 
              << " ms\n";
    
    return 0;
}
```

### Example 2: Compiler Explorer (Godbolt)

Use [godbolt.org](https://godbolt.org) to see what assembly the compiler generates. This is invaluable for understanding optimizations.

```cpp
// Source code:
int sum_array(int* arr, int n) {
    int sum = 0;
    for (int i = 0; i < n; i++)
        sum += arr[i];
    return sum;
}

// With -O3, GCC generates vectorized assembly using SIMD
// The compiler may use `paddd` (packed add) to process 4 ints at once
```

---

## 129.5 What Compilers Cannot Optimize

### 1. Aliasing

When two pointers might point to the same memory, the compiler must be conservative.

```cpp
// Compiler cannot assume a and b don't overlap
void add(float* a, float* b, int n) {
    for (int i = 0; i < n; i++)
        a[i] += b[i];
}

// Use __restrict__ to tell compiler they don't overlap:
void add_restrict(float* __restrict__ a, float* __restrict__ b, int n) {
    for (int i = 0; i < n; i++)
        a[i] += b[i];
}
```

### 2. Memory Barriers and Volatile

```cpp
// volatile prevents optimization of reads/writes
volatile int* hardware_register = (volatile int*)0x1000;
int value = *hardware_register;  // compiler will NOT optimize this away
```

### 3. Function Pointers and Virtual Calls

```cpp
// Compiler cannot inline through function pointers
void apply(int* arr, int n, int (*func)(int)) {
    for (int i = 0; i < n; i++)
        arr[i] = func(arr[i]);
}

// With templates, the compiler CAN inline:
template<typename F>
void apply_template(int* arr, int n, F func) {
    for (int i = 0; i < n; i++)
        arr[i] = func(arr[i]);
}
```

### 4. Side Effects

```cpp
// Compiler cannot reorder across I/O
printf("before");
x = compute();  // compiler cannot move this before printf
printf("after");
```

---

## 129.6 Writing Optimization-Friendly Code

### DO:
1. **Use `const`** — helps the compiler prove values don't change
2. **Minimize pointer aliasing** — use `__restrict__` or value types
3. **Prefer contiguous memory** — arrays over linked lists
4. **Use standard algorithms** — `std::sort`, `std::copy` are heavily optimized
5. **Profile before optimizing** — measure, don't guess

### DON'T:
1. **Don't use `volatile` for synchronization** — use atomics or mutexes
2. **Don't rely on undefined behavior** — the compiler will exploit it
3. **Don't fight the optimizer** — write clear code, let the compiler optimize
4. **Don't over-inline** — inlining everything increases code size and cache pressure
5. **Don't assume optimization across translation units** — use LTO (Link-Time Optimization)

---

## 129.7 Advanced Topics

### Link-Time Optimization (LTO)

LTO enables optimizations across translation units (`.cpp` files):
- Cross-module inlining
- Whole-program dead code elimination
- Better interprocedural analysis

```bash
# GCC LTO:
g++ -O3 -flto file1.cpp file2.cpp -o program

# Clang LTO:
clang++ -O3 -flto file1.cpp file2.cpp -o program
```

### Profile-Guided Optimization (PGO)

Use runtime profiling data to guide optimization:
- Better branch prediction
- Hot/cold code separation
- Better inlining decisions

```bash
# Step 1: Compile with instrumentation
g++ -O3 -fprofile-generate program.cpp -o program

# Step 2: Run with representative input
./program < typical_input.txt

# Step 3: Compile with profile data
g++ -O3 -fprofile-use program.cpp -o program_optimized
```

### Auto-Vectorization Reporting

See what the compiler vectorized (or why it didn't):

```bash
# GCC:
g++ -O3 -ftree-vectorize -fopt-info-vec-optimized program.cpp
g++ -O3 -ftree-vectorize -fopt-info-vec-missed program.cpp

# Clang:
clang++ -O3 -Rpass=loop-vectorize program.cpp
clang++ -O3 -Rpass-missed=loop-vectorize program.cpp
```

---

## 129.8 Complexity Analysis (of Optimization Impact)

| Optimization | Typical Speedup | When It Helps |
|---|---|---|
| Inlining | 10-30% | Small, frequently called functions |
| Loop unrolling | 5-20% | Tight loops with simple bodies |
| Vectorization | 2-8x | Array operations, data parallelism |
| LICM | 10-50% | Loops with invariant computations |
| Dead code elimination | Variable | Code with unused computations |
| Constant folding | Negligible | Modern CPUs are fast regardless |
| Tail call optimization | Prevents stack overflow | Deep recursion |
| Strength reduction | 5-15% | Heavy arithmetic in loops |

---

## Exercises

1. **Easy:** Write a function that the compiler can fully constant-fold. Verify using Godbolt.
2. **Easy:** Convert a non-tail-recursive factorial to tail-recursive form. Verify the compiler generates a loop.
3. **Medium:** Write a loop that the compiler can auto-vectorize and one that it cannot. Explain why.
4. **Medium:** Use `-fopt-info-vec-optimized` to check if a matrix multiplication inner loop is vectorized.
5. **Hard:** Implement a function that runs 10x faster with `-O3` than `-O0` due to vectorization. Benchmark both.
6. **Hard:** Compare the assembly output of `std::sort` vs a hand-written bubble sort with `-O3`.

## Interview Questions

1. **Q:** What's the difference between `-O2` and `-O3`?
   **A:** `-O3` enables aggressive optimizations including auto-vectorization, loop unrolling, and more aggressive inlining. The code may be faster but also larger. `-O2` is the standard recommendation for production code.

2. **Q:** Why might `-O3` code be slower than `-O2`?
   **A:** Aggressive inlining and unrolling can increase code size, leading to instruction cache misses. In tight loops with simple bodies, this rarely matters, but in large codebases it can hurt.

3. **Q:** What is the `restrict` keyword and when is it useful?
   **A:** `restrict` tells the compiler that a pointer is the only reference to its memory. This enables the compiler to avoid unnecessary reloads, especially in loops. Critical for auto-vectorization.

4. **Q:** How would you determine if a loop is being vectorized?
   **A:** Use compiler flags like `-fopt-info-vec-optimized` (GCC) or `-Rpass=loop-vectorize` (Clang). Alternatively, examine the generated assembly on Godbolt for SIMD instructions.

5. **Q:** What is undefined behavior and how does it relate to optimization?
   **A:** Undefined behavior (UB) gives the compiler freedom to assume it never happens. For example, signed integer overflow is UB, so the compiler can assume it doesn't occur and optimize accordingly. This can lead to surprising results if you rely on UB.

## Cross-References
- Bit manipulation: Chapter 125
- Cache-friendly code: Chapter 128
- SIMD programming: Chapter 131
- Performance profiling: Chapter 127
