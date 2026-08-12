# Memory and Hardware Awareness



## Prerequisites

- Basic C++ programming
- Understanding of pointers and references
- Familiarity with arrays and linked lists

## Interview Frequency

★★★★ — Critical for **system design** and **optimization** rounds. Also relevant for senior/Staff-level roles where understanding hardware impact on performance separates candidates.

## Companies

Google (low-latency systems), Meta (News Feed performance), HFT firms (Jane Street, Citadel, Two Sigma), Game studios (Epic, Unity), Database companies (Snowflake, Databricks), Operating systems teams (Microsoft, Apple, Linux kernel).

---

## Overview

Modern CPUs are incredibly fast, but memory is comparatively slow. Understanding *why* — and how to write code that respects the memory hierarchy — is what separates a programmer who writes correct code from one who writes *fast* correct code. This chapter covers the hardware realities that affect algorithm performance.

| Topic | Why It Matters in Interviews |
|-------|------------------------------|
| Stack vs Heap | Choosing the right allocation strategy |
| CPU Cache | Explaining why arrays beat linked lists |
| Memory Hierarchy | Understanding O(1) ≠ fast |
| Virtual Memory | System design, large data problems |
| Alignment & Padding | Struct layout, memory efficiency |
| False Sharing | Multithreading correctness |
| Fragmentation | Long-running systems |
| Pointer Arithmetic | Low-level manipulation |
| Memory Leaks | Code quality |
| RAII | Modern C++ best practice |
| Move Semantics | Performance optimization |
| Smart Pointers | Ownership design |

---

## 1. Stack vs Heap

### Stack Allocation

The stack is a region of memory that grows and shrinks automatically as functions are called and return. Each function call creates a **stack frame** containing local variables, parameters, and the return address.

**Characteristics:**
- **Allocation:** Automatic (compiler-generated instructions adjust the stack pointer)
- **Lifetime:** Scope-bound (destroyed when the function returns)
- **Speed:** Very fast — just a pointer adjustment (typically one instruction)
- **Size:** Limited (typically 1–8 MB per thread)
- **Fragmentation:** None (LIFO order guarantees contiguous allocation)

```cpp
void stack_example() {
    int arr[100];        // Stack: fast, automatic cleanup
    int x = 42;          // Stack
    // arr and x are destroyed when function returns
}
```

### Heap Allocation

The heap is a region of memory managed by the runtime (or the OS). You explicitly request memory with `new`/`malloc` and release it with `delete`/`free`.

**Characteristics:**
- **Allocation:** Manual (or via smart pointers); involves searching for free blocks
- **Lifetime:** Until explicitly freed (or smart pointer goes out of scope)
- **Speed:** Slower — involves bookkeeping, potential system calls
- **Size:** Limited only by available memory (gigabytes)
- **Fragmentation:** Can occur over time

```cpp
void heap_example() {
    int* arr = new int[1000000]; // Heap: slow, manual cleanup
    // Must delete[] arr or use unique_ptr
    delete[] arr;
}
```

### Comparison Table

| Property | Stack | Heap |
|----------|-------|------|
| Allocation speed | ~1 ns (pointer bump) | ~100 ns (search + bookkeeping) |
| Deallocation speed | ~1 ns (pointer restore) | ~100 ns (merge free blocks) |
| Max size | 1–8 MB typical | GBs |
| Thread safety | Per-thread (no sharing) | Shared (needs synchronization) |
| Fragmentation | None | Can occur |
| Cache behavior | Excellent (hot in L1) | Varies |
| Risk | Stack overflow | Memory leaks, dangling pointers |

### When to Use Each

**Use stack when:**
- Size is known at compile time (or small and bounded)
- Object lifetime matches the function scope
- Performance is critical

**Use heap when:**
- Size is large or unknown at compile time
- Object must outlive the function scope
- Size exceeds stack limit

### Interview Application

**Q: "Why is `std::vector` faster than `std::list` for most operations?"**

Part of the answer: `std::vector` stores elements contiguously on the heap, which is cache-friendly. `std::list` allocates each node separately on the heap, causing cache misses. But there's more — see the CPU Cache section.

**Q: "What happens if you allocate a huge array on the stack?"**

Stack overflow. The default stack size is typically 1–8 MB. Allocating `int arr[1000000]` (4 MB) on the stack will crash.

---

## 2. CPU Cache

### Cache Hierarchy

Modern CPUs have multiple levels of cache:

| Level | Size | Latency | Scope |
|-------|------|---------|-------|
| L1 | 32–64 KB | ~1 ns (4 cycles) | Per-core |
| L2 | 256 KB–1 MB | ~4 ns (12 cycles) | Per-core |
| L3 | 4–64 MB | ~12 ns (40 cycles) | Shared across cores |
| RAM | 8–256 GB | ~100 ns (300 cycles) | Shared |

A **cache line** is the unit of data transfer between cache levels — typically 64 bytes. When you access one byte, the entire 64-byte cache line is loaded.

### Why Arrays Beat Linked Lists

This is one of the most common interview questions about hardware awareness.

**Linked list traversal:**
```
Node 1 → [data|next] → Node 2 → [data|next] → Node 3 → ...
```
Each node may be anywhere in memory. Following `next` is a **pointer chase** — likely a cache miss for each node.

**Array traversal:**
```
[elem0][elem1][elem2][elem3][elem5][elem6][elem7]...
```
Elements are contiguous. The CPU prefetches the next cache line while you're processing the current one.

### Benchmark: Cache Effects on Algorithm Performance

```cpp
#include <chrono>
#include <iostream>
#include <vector>
#include <list>
#include <random>
#include <numeric>
#include <algorithm>

int main() {
    constexpr int N = 10'000'000;

    // Setup
    std::vector<int> vec(N);
    std::iota(vec.begin(), vec.end(), 0);
    std::list<int> lst(vec.begin(), vec.end());

    // Shuffle for random access benchmark
    std::mt19937 rng(42);
    std::vector<int> indices(N);
    std::iota(indices.begin(), indices.end(), 0);
    std::shuffle(indices.begin(), indices.end(), rng);

    // --- Sequential traversal ---
    auto t1 = std::chrono::high_resolution_clock::now();
    long long sum_vec = 0;
    for (int x : vec) sum_vec += x;
    auto t2 = std::chrono::high_resolution_clock::now();

    long long sum_lst = 0;
    for (int x : lst) sum_lst += x;
    auto t3 = std::chrono::high_resolution_clock::now();

    auto vec_seq = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
    auto lst_seq = std::chrono::duration_cast<std::chrono::microseconds>(t3 - t2).count();

    std::cout << "Sequential traversal:\n";
    std::cout << "  vector: " << vec_seq << " µs\n";
    std::cout << "  list:   " << lst_seq << " µs\n";
    std::cout << "  ratio:  " << (double)lst_seq / vec_seq << "x\n\n";

    // --- Random access (sum every 1000th element via indexing) ---
    t1 = std::chrono::high_resolution_clock::now();
    sum_vec = 0;
    for (int i = 0; i < N; i += 1000) sum_vec += vec[i];
    t2 = std::chrono::high_resolution_clock::now();

    sum_lst = 0;
    auto it = lst.begin();
    for (int i = 0; i < N; i += 1000) {
        auto target = lst.begin();
        std::advance(target, 1000);
        sum_lst += *target;
    }
    t3 = std::chrono::high_resolution_clock::now();

    auto vec_rand = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
    auto lst_rand = std::chrono::duration_cast<std::chrono::microseconds>(t3 - t2).count();

    std::cout << "Random access (stride 1000):\n";
    std::cout << "  vector: " << vec_rand << " µs\n";
    std::cout << "  list:   " << lst_rand << " µs\n";
    std::cout << "  ratio:  " << (double)lst_rand / vec_rand << "x\n";

    return 0;
}
```

**Typical results:**
- Sequential: list is 2–5× slower than vector
- Random access: list is 100–1000× slower than vector

### Cache-Friendly Code Principles

1. **Prefer contiguous data structures** (`vector`, `array`, `deque` segments)
2. **Access memory sequentially** when possible
3. **Use struct-of-arrays (SoA)** instead of array-of-structs (AoS) when iterating over one field
4. **Avoid pointer chasing** (linked lists, trees with heap-allocated nodes)
5. **Process data in cache-line-sized chunks**

```cpp
// AoS: bad for iterating over just x
struct PointAoS { double x, y, z, w; }; // 32 bytes
std::vector<PointAoS> points_aos;

// SoA: good for iterating over just x
struct PointsSoA {
    std::vector<double> x, y, z, w;
};
```

---

## 3. Memory Hierarchy

### Full Hierarchy

```
Registers    (~0.3 ns, ~1 cycle)      32–64 × 64-bit
    ↓
L1 Cache     (~1 ns, ~4 cycles)       32–64 KB
    ↓
L2 Cache     (~4 ns, ~12 cycles)      256 KB–1 MB
    ↓
L3 Cache     (~12 ns, ~40 cycles)     4–64 MB
    ↓
RAM          (~100 ns, ~300 cycles)    8–256 GB
    ↓
SSD          (~100 µs)                256 GB–4 TB
    ↓
HDD          (~10 ms)                 1–16 TB
```

### Implications for Algorithm Design

**O(1) is not always fast.** Hash table lookup is O(1) but involves pointer chasing and cache misses. Binary search is O(log n) but accesses a contiguous array — potentially faster for moderate *n*.

**Example:** Searching a sorted `std::vector<int>` of 1 million elements:
- Binary search: ~20 comparisons, all in contiguous memory, ~20 cache misses worst case
- `std::unordered_set` lookup: 1 hash + 1–3 pointer chases, ~1–3 cache misses

For sequential lookups on sorted data, binary search on a vector often beats hash tables.

### Interview Application

**Q: "When would you use a sorted array instead of a hash map?"**

Answer: When the data fits in cache and you're doing many lookups. A sorted `std::vector` has excellent spatial locality. For read-heavy workloads with moderate size, the cache advantage can outweigh the O(log n) vs O(1) theoretical difference.

---

## 4. Virtual Memory

### How It Works

Each process has its own **virtual address space** (e.g., 48-bit = 256 TB on x64). The OS maps virtual pages to physical frames using a **page table**. The **TLB (Translation Lookaside Buffer)** caches recent translations.

| Component | Size | Latency |
|-----------|------|---------|
| TLB | 64–1536 entries | ~1 ns |
| Page table walk | 4-level on x64 | ~100 ns |
| Page size | 4 KB (or 2 MB / 1 GB huge pages) | — |
| Page fault (soft) | OS handles from RAM | ~1–10 µs |
| Page fault (hard) | OS reads from disk | ~10 ms |

### Interview Application

**Q: "Why might a program be slow even though its algorithm is O(n)?"**

Possible answer: The working set exceeds physical memory, causing **page faults**. Each page fault to disk costs ~10 ms — millions of times slower than a cache miss. This is why external memory algorithms exist for datasets larger than RAM.

**Q: "What are huge pages and when would you use them?"**

Huge pages (2 MB or 1 GB) reduce TLB misses for large data structures. Databases and HFT systems use them to avoid TLB thrashing.

---

## 5. Alignment and Padding

### What Is Alignment?

Data types have **alignment requirements** — they must be stored at addresses that are multiples of their size (on most architectures). The compiler inserts **padding bytes** to satisfy alignment.

```cpp
struct Bad {
    char a;     // 1 byte + 3 bytes padding
    int b;      // 4 bytes
    char c;     // 1 byte + 3 bytes padding
    int d;      // 4 bytes
}; // Total: 16 bytes

struct Good {
    int b;      // 4 bytes
    int d;      // 4 bytes
    char a;     // 1 byte
    char c;     // 1 byte + 2 bytes padding
}; // Total: 12 bytes
```

### Why It Matters

- **Memory efficiency:** Reordering struct members can save 25%+ memory
- **Cache efficiency:** Smaller structs mean more fit in a cache line
- **Performance:** Unaligned access can be slower or even crash on some architectures

### Verification

```cpp
#include <iostream>
#include <cstddef>

struct Bad  { char a; int b; char c; int d; };
struct Good { int b; int d; char a; char c; };

int main() {
    std::cout << "sizeof(Bad):  " << sizeof(Bad)  << "\n"; // 16
    std::cout << "sizeof(Good): " << sizeof(Good) << "\n"; // 12
    std::cout << "offsetof(Bad, a):  " << offsetof(Bad, a)  << "\n"; // 0
    std::cout << "offsetof(Bad, b):  " << offsetof(Bad, b)  << "\n"; // 4
    std::cout << "offsetof(Bad, c):  " << offsetof(Bad, c)  << "\n"; // 8
    std::cout << "offsetof(Bad, d):  " << offsetof(Bad, d)  << "\n"; // 12
}
```

---

## 6. False Sharing

### What Is It?

When two threads modify different variables that reside on the **same cache line**, the cache coherence protocol invalidates the line for the other core — even though they're not actually sharing data. This is **false sharing**.

```cpp
#include <thread>
#include <atomic>
#include <chrono>
#include <iostream>

// BAD: counters are adjacent, likely on the same cache line
struct Bad {
    std::atomic<long long> counter_a{0};
    std::atomic<long long> counter_b{0};
};

// GOOD: pad to separate cache lines
struct alignas(64) PaddedCounter {
    std::atomic<long long> value{0};
    char padding[64 - sizeof(std::atomic<long long>)];
};

struct Good {
    PaddedCounter counter_a;
    PaddedCounter counter_b;
};

template<typename T>
long long benchmark(T& counters, int iterations) {
    auto start = std::chrono::high_resolution_clock::now();
    std::thread t1([&] {
        for (int i = 0; i < iterations; ++i)
            counters.counter_a.value.fetch_add(1, std::memory_order_relaxed);
    });
    std::thread t2([&] {
        for (int i = 0; i < iterations; ++i)
            counters.counter_b.value.fetch_add(1, std::memory_order_relaxed);
    });
    t1.join();
    t2.join();
    auto end = std::chrono::high_resolution_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
}

int main() {
    constexpr int ITERS = 100'000'000;
    Bad bad;
    Good good;
    auto t_bad  = benchmark(bad, ITERS);
    auto t_good = benchmark(good, ITERS);
    std::cout << "False sharing:  " << t_bad  << " ms\n";
    std::cout << "Padded:         " << t_good << " ms\n";
    // Typically: false sharing is 2-10x slower
}
```

### Interview Application

**Q: "Your multithreaded code doesn't scale beyond 2 cores. What could be wrong?"**

Check for false sharing. Profile cache line invalidations. Use `alignas(64)` or `__attribute__((aligned(64)))` to separate hot variables onto different cache lines.

---

## 7. Memory Fragmentation

### Internal Fragmentation

Memory allocated is larger than needed. Example: `malloc(17)` might return a 32-byte block. The 15 wasted bytes are internal fragmentation.

### External Fragmentation

Free memory is scattered in small blocks. Total free memory might be sufficient, but no single contiguous block is large enough.

```
[USED][free 16][USED][free 24][USED][free 16][USED]
Total free: 56 bytes, but can't allocate 40 contiguous bytes
```

### Interview Application

**Q: "Why do long-running servers have increasing memory usage even without leaks?"**

External fragmentation: small allocations and deallocations create gaps. The allocator can't coalesce them. Solutions: custom allocators (pool, slab), periodic restart, or using containers that minimize fragmentation (e.g., `std::deque` over many small `new`s).

---

## 8. Pointer Arithmetic

### How It Works

Pointer arithmetic respects the type size. `p + 1` advances by `sizeof(*p)` bytes.

```cpp
int arr[5] = {10, 20, 30, 40, 50};
int* p = arr;       // points to arr[0]
p += 2;             // points to arr[2], advances by 2 * sizeof(int) = 8 bytes
*p = 99;            // arr[2] = 99

// Equivalent to arr[2] = 99
// Which is *(arr + 2) = 99
```

### Undefined Behavior Risks

```cpp
int arr[5] = {1, 2, 3, 4, 5};
int* p = arr + 5;  // One past the end — legal to compute, but NOT to dereference
// *p = 10;        // UNDEFINED BEHAVIOR

int* q = arr + 6;  // UB: more than one past the end
int* r = arr - 1;  // UB: before the beginning
```

**Key rules:**
- `arr + N` (where N is the array size) is legal — it's the "one past the end" pointer
- Dereferencing it is UB
- Any pointer outside `[arr, arr + N]` is UB to compute

---

## 9. Memory Leaks

### Detection

```cpp
// Simple RAII wrapper to detect leaks
#include <iostream>
#include <set>

class LeakDetector {
    static inline std::set<void*> allocations;
public:
    static void* allocate(size_t size) {
        void* p = ::operator new(size);
        allocations.insert(p);
        return p;
    }
    static void deallocate(void* p) {
        allocations.erase(p);
        ::operator delete(p);
    }
    static void report() {
        if (!allocations.empty())
            std::cerr << "LEAK: " << allocations.size() << " allocations not freed\n";
        else
            std::cerr << "No leaks detected\n";
    }
};
```

### Prevention

1. **Use RAII** (see next section)
2. **Use smart pointers** instead of raw `new`/`delete`
3. **Use containers** (`vector`, `string`) instead of manual arrays
4. **Tools:** Valgrind, AddressSanitizer (`-fsanitize=address`), LeakSanitizer

---

## 10. RAII (Resource Acquisition Is Initialization)

### Definition

RAII ties resource lifetime to object lifetime. Resources are acquired in the constructor and released in the destructor. When the object goes out of scope, the destructor runs automatically — no leaks.

### Example

```cpp
#include <cstdio>
#include <stdexcept>

class FileHandle {
    FILE* fp;
public:
    explicit FileHandle(const char* filename, const char* mode)
        : fp(std::fopen(filename, mode)) {
        if (!fp) throw std::runtime_error("Failed to open file");
    }
    ~FileHandle() {
        if (fp) std::fclose(fp);
    }
    // Non-copyable
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;
    // Movable
    FileHandle(FileHandle&& other) noexcept : fp(other.fp) { other.fp = nullptr; }
    FileHandle& operator=(FileHandle&& other) noexcept {
        if (this != &other) { if (fp) std::fclose(fp); fp = other.fp; other.fp = nullptr; }
        return *this;
    }
    FILE* get() const { return fp; }
};

void write_log(const char* msg) {
    FileHandle f("log.txt", "a");  // Acquired
    std::fputs(msg, f.get());
    // Automatically closed when f goes out of scope
    // Even if fputs throws (it doesn't, but conceptually)
}
```

### Interview Application

RAII is the foundation of modern C++ resource management. Every `std::vector`, `std::string`, `std::unique_ptr`, `std::lock_guard` uses RAII. If you write code with raw `new`/`delete` in an interview, be prepared to explain why you didn't use RAII.

---

## 11. Move Semantics

### Why Move Exists

Copying a large object (e.g., a vector of 1 million elements) is expensive. If the source is about to be destroyed, we can **move** its internal data (just swap pointers) instead of copying — O(1) instead of O(n).

### `std::move` and Rvalue References

```cpp
#include <vector>
#include <utility>
#include <iostream>

int main() {
    std::vector<int> v1 = {1, 2, 3, 4, 5};
    // v1 has data at address P

    std::vector<int> v2 = std::move(v1);
    // v2 now has data at address P
    // v1 is in a "valid but unspecified" state (empty here)

    std::cout << "v1.size() = " << v1.size() << "\n"; // 0
    std::cout << "v2.size() = " << v2.size() << "\n"; // 5
}
```

### When to Move vs Copy

| Situation | Use |
|-----------|-----|
| Source is a temporary (rvalue) | Move (automatic) |
| Source is named but no longer needed | `std::move(source)` |
| Source must remain valid | Copy |
| Returning local variable | Copy elision (RVO) — no move needed |

### Interview Application

**Q: "When does `std::move` actually move?"**

`std::move` by itself does nothing — it just casts to an rvalue reference. The actual move happens when the rvalue reference is used by a move constructor or move assignment operator. `std::move` is a promise: "I don't need this object's value anymore."

---

## 12. Copy Semantics

### Deep vs Shallow Copy

```cpp
class Shallow {
    int* data;
public:
    Shallow(int val) : data(new int(val)) {}
    // Default copy: shallow — both objects point to same data!
    // DANGER: double-free on destruction
};

class Deep {
    int* data;
public:
    Deep(int val) : data(new int(val)) {}
    Deep(const Deep& other) : data(new int(*other.data)) {} // Deep copy
    Deep& operator=(const Deep& other) {
        if (this != &other) { *data = *other.data; } // Copy the value
        return *this;
    }
    ~Deep() { delete data; }
};
```

### Rule of Five

If you define any of destructor, copy constructor, copy assignment, move constructor, or move assignment, you should define all five:

```cpp
class Resource {
    int* data;
public:
    Resource(int val) : data(new int(val)) {}
    ~Resource() { delete data; }                                          // 1. Destructor
    Resource(const Resource& o) : data(new int(*o.data)) {}               // 2. Copy ctor
    Resource& operator=(const Resource& o) {                              // 3. Copy assign
        if (this != &o) *data = *o.data;
        return *this;
    }
    Resource(Resource&& o) noexcept : data(o.data) { o.data = nullptr; }  // 4. Move ctor
    Resource& operator=(Resource&& o) noexcept {                          // 5. Move assign
        if (this != &o) { delete data; data = o.data; o.data = nullptr; }
        return *this;
    }
};
```

---

## 13. Smart Pointers

### `std::unique_ptr`

Exclusive ownership. Cannot be copied, only moved. Zero overhead over raw pointer.

```cpp
#include <memory>

void unique_ptr_demo() {
    auto p = std::make_unique<int>(42);
    // auto q = p;                    // ERROR: can't copy
    auto q = std::move(p);           // OK: transfer ownership
    // p is now nullptr
    // q is destroyed when it goes out of scope — memory freed automatically
}
```

### `std::shared_ptr`

Shared ownership via reference counting. Thread-safe reference count manipulation.

```cpp
#include <memory>
#include <iostream>

void shared_ptr_demo() {
    auto p = std::make_shared<int>(42);  // refcount = 1
    {
        auto q = p;                       // refcount = 2
        std::cout << *q << "\n";          // 42
    } // q destroyed, refcount = 1
    std::cout << *p << "\n";              // 42
} // p destroyed, refcount = 0, memory freed
```

### `std::weak_ptr`

Non-owning reference to a `shared_ptr`-managed object. Used to break cycles.

```cpp
#include <memory>

struct Node {
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;  // weak to break cycle
};
```

### Decision Table

| Scenario | Use |
|----------|-----|
| Single owner, clear lifetime | `unique_ptr` |
| Multiple owners, last one cleans up | `shared_ptr` |
| Need reference without ownership (break cycle) | `weak_ptr` |
| Performance-critical, ownership is obvious | Raw pointer (non-owning) |
| Array ownership | `unique_ptr<T[]>` or `vector` |

### `shared_ptr` Overhead

| Aspect | Cost |
|--------|------|
| Memory | 2 pointers (object + control block) + refcount |
| Control block | ~48 bytes (refcount, weak count, deleter, allocator) |
| Increment/decrement | Atomic operations (~10–20 ns) |
| Thread safety | Reference count is thread-safe; the object itself is NOT |

---

## Comprehensive Comparison: Allocation Strategies

| Strategy | Speed | Fragmentation | Thread Safety | Use Case |
|----------|-------|---------------|---------------|----------|
| Stack | Fastest | None | Per-thread | Local variables, small objects |
| `unique_ptr` | Fast (single heap alloc) | Minimal | Single owner | Exclusive ownership |
| `shared_ptr` | Moderate (heap + control block) | Moderate | Refcount is atomic | Shared ownership |
| Pool allocator | Fast (fixed-size blocks) | None | Can be per-pool | Many same-sized objects |
| Stack allocator | Fast (bump pointer) | None | Per-thread | Temp allocations in a scope |
| Arena/Bump | Very fast | Resets entirely | Varies | Batch processing |

---

## Practical Interview Tips

1. **"Why is my code slow?"** → Check cache misses, not just Big-O.
2. **"How do you avoid memory leaks?"** → RAII and smart pointers.
3. **"When would you use `std::move`?"** → When transferring ownership and the source is no longer needed.
4. **"What's the cost of `shared_ptr`?"** → ~48 bytes extra, atomic refcount operations, potential cache line contention.
5. **"How do you make a struct smaller?"** → Reorder members by alignment, use bitfields, avoid padding.
6. **"Why is multithreaded code slow?"** → Check for false sharing with `perf` or VTune.
7. **"Arrays or linked lists?"** → Almost always arrays, unless you need O(1) insertion/deletion in the middle and don't care about cache.

---

## Design Decisions

### When NOT to Use `shared_ptr`

- When ownership is clear and exclusive → use `unique_ptr`
- When the object is stack-allocated and lifetime is obvious → use references
- When you need performance and can manage lifetime manually → use raw non-owning pointers

**Alternatives:** `unique_ptr` (lighter), raw references (no ownership semantics), `weak_ptr` (break cycles).

### When NOT to Use Move Semantics

- When the source must remain valid (use copy)
- When the object is trivially copyable (copy is already fast)
- When returning a local variable (RVO handles it)

### Trade-offs

| Decision | Pros | Cons |
|----------|------|------|
| Stack allocation | Fast, no leaks | Limited size |
| Heap + smart pointers | Flexible size, safe | Overhead, slower |
| Custom allocator | Optimal for specific patterns | Complexity |
| Cache-aware design | Orders of magnitude faster | Code may be less readable |
| RAII | Automatic cleanup | Must design classes carefully |

---

## Summary

Hardware awareness turns you from a programmer who writes correct code into one who writes correct *and fast* code. The key insight: **Big-O is necessary but not sufficient.** A cache-friendly O(n log n) algorithm can beat a cache-hostile O(n) algorithm for practical input sizes. Know your cache lines, respect the memory hierarchy, and use RAII and smart pointers to avoid resource management bugs.
