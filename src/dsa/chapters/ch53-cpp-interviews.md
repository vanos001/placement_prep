# C++ for Interviews



## Prerequisites

- Basic C++ (variables, loops, functions, classes, pointers)
- Familiarity with at least one STL container
- Understanding of compilation and linking basics

## Interview Frequency

★★★★★ — Every C++ interview. Even "algorithm" interviews in C++ implicitly test language knowledge through your use of templates, iterators, lambdas, and containers.

## Companies

Google, Meta, Amazon, Microsoft, Apple, Bloomberg, Goldman Sachs, Jane Street, Citadel, Two Sigma, Uber, Lyft, Airbnb, Stripe, Dropbox — any company with a C++ codebase or that accepts C++ in interviews.

---

## Overview

This chapter covers the C++ features and idioms that matter most in interviews. Not everything in the language — just what you'll actually use or be asked about.

| Topic | Interview Relevance |
|-------|-------------------|
| Templates | Code reuse, type genericity |
| References | Efficient parameter passing |
| Move Semantics | Performance optimization |
| constexpr | Compile-time computation |
| Lambda Expressions | Concise callbacks, STL algorithms |
| Functors | Custom comparators, stateful callbacks |
| Iterator Categories | Choosing the right algorithm |
| Allocator Basics | How STL manages memory |
| Exception Safety | Robust code design |
| STL Internals | How vector/map/unordered_map work |
| Container Selection | Choosing the right tool |
| Undefined Behavior | Avoiding traps |
| Common STL Pitfalls | Iterator invalidation, comparator bugs |
| Memory Complexity | Space analysis |
| Thread Safety | Concurrent access rules |

---

## 1. Templates

### Function Templates

```cpp
#include <iostream>
#include <string>

template<typename T>
T max_val(T a, T b) {
    return (a > b) ? a : b;
}

// Explicit specialization for const char*
template<>
const char* max_val<const char*>(const char* a, const char* b) {
    return (std::strcmp(a, b) > 0) ? a : b;
}

int main() {
    std::cout << max_val(3, 7) << "\n";           // 7 — deduced as int
    std::cout << max_val(3.14, 2.71) << "\n";     // 3.14 — deduced as double
    std::cout << max_val<std::string>("a", "b") << "\n"; // explicit
}
```

### Class Templates

```cpp
#include <vector>
#include <stdexcept>

template<typename T, int N>
class FixedStack {
    T data[N];
    int top_ = 0;
public:
    void push(const T& val) {
        if (top_ >= N) throw std::overflow_error("Stack full");
        data[top_++] = val;
    }
    T pop() {
        if (top_ <= 0) throw std::underflow_error("Stack empty");
        return data[--top_];
    }
    const T& top() const {
        if (top_ <= 0) throw std::underflow_error("Stack empty");
        return data[top_ - 1];
    }
    bool empty() const { return top_ == 0; }
    int size() const { return top_; }
};

// Usage: FixedStack<int, 100> s;
```

### SFINAE Basics

**Substitution Failure Is Not An Error:** If template argument substitution fails, the compiler silently removes that overload instead of erroring.

```cpp
#include <type_traits>
#include <iostream>

// Only enabled for integral types
template<typename T>
std::enable_if_t<std::is_integral_v<T>, T>
safe_div(T a, T b) {
    if (b == 0) throw std::domain_error("Division by zero");
    return a / b;
}

// Only enabled for floating-point types
template<typename T>
std::enable_if_t<std::is_floating_point_v<T>, T>
safe_div(T a, T b) {
    return a / b; // floating point division by zero gives inf, not UB
}

int main() {
    std::cout << safe_div(10, 3) << "\n";    // 3 — integral overload
    std::cout << safe_div(10.0, 3.0) << "\n"; // 3.333... — floating-point overload
}
```

### Interview Application

**Q: "What's the difference between `template<typename T>` and `template<class T>`?"**

Nothing — they're interchangeable. Convention: `typename` for templates, `class` when you want to emphasize the type must be a class (though it doesn't enforce it).

**Q: "When does template instantiation happen?"**

At the point of use (implicit instantiation) or when explicitly requested. This is why template definitions are usually in header files — the compiler needs the full definition to instantiate.

---

## 2. References

### Lvalue References

```cpp
void modify(int& x) { x = 42; }       // Must bind to an lvalue
void read(const int& x) { /* ... */ } // Can bind to rvalues too

int main() {
    int a = 10;
    modify(a);   // OK: a is an lvalue
    // modify(5); // ERROR: 5 is an rvalue, can't bind to non-const lvalue ref
    read(5);     // OK: const lvalue ref extends lifetime of temporary
}
```

### Rvalue References

```cpp
void process(std::string&& s) {
    // s is an rvalue reference — we can steal its resources
    std::string result = std::move(s);
    // ...
}

int main() {
    std::string hello = "hello";
    // process(hello);           // ERROR: hello is an lvalue
    process(std::move(hello));   // OK: cast to rvalue
    process("temporary");        // OK: string literal creates temporary
}
```

### When to Pass What

| Parameter Type | When to Use |
|---------------|-------------|
| `T` (by value) | Small types (int, char, pointer), or when you need a copy anyway |
| `const T&` | Read-only access, don't need to own, don't want copy cost |
| `T&` | Mutable reference, parameter must be modified |
| `T&&` | Taking ownership, perfect forwarding |
| `const T&&` | Rarely used; generally avoid |

---

## 3. Move Semantics and Perfect Forwarding

### Perfect Forwarding

```cpp
#include <utility>
#include <string>
#include <iostream>

class Wrapper {
    std::string data;
public:
    // Perfect forwarding constructor
    template<typename T>
    Wrapper(T&& val) : data(std::forward<T>(val)) {}

    // std::forward preserves the value category:
    // - If called with lvalue, T = std::string&, forward returns lvalue ref
    // - If called with rvalue, T = std::string,  forward returns rvalue ref
};

int main() {
    std::string s = "hello";
    Wrapper w1(s);              // lvalue: copies s into data
    Wrapper w2(std::move(s));   // rvalue: moves s into data
    Wrapper w3("literal");      // rvalue: moves from temporary string
}
```

### `std::move` vs `std::forward`

| Function | What It Does | When to Use |
|----------|-------------|-------------|
| `std::move(x)` | Unconditionally casts to rvalue | When you want to move and don't care about x |
| `std::forward<T>(x)` | Conditionally casts based on T | In forwarding templates, preserving value category |

### Interview Application

**Q: "What's the difference between `std::move` and `std::forward`?"**

`std::move` says "I'm done with this object, take its resources." `std::forward` says "pass this along with the same value category it was given to me." `std::move` is always an rvalue cast; `std::forward` is a conditional cast that depends on the template parameter.

---

## 4. constexpr

### Compile-Time Computation

```cpp
#include <array>
#include <iostream>

constexpr int factorial(int n) {
    int result = 1;
    for (int i = 2; i <= n; ++i)
        result *= i;
    return result;
}

constexpr bool is_prime(int n) {
    if (n < 2) return false;
    for (int i = 2; i * i <= n; ++i)
        if (n % i == 0) return false;
    return true;
}

int main() {
    constexpr int fact10 = factorial(10);  // Computed at compile time
    static_assert(fact10 == 3628800);

    // Can use in array size (requires compile-time constant)
    std::array<int, factorial(5)> arr;  // size = 120

    // Runtime usage also works
    int n;
    // std::cin >> n;
    // int f = factorial(n);  // OK: computed at runtime if n is not constexpr

    // Compile-time prime checking
    static_assert(is_prime(17));
    static_assert(!is_prime(15));

    std::cout << "10! = " << fact10 << "\n";
}
```

### Interview Application

`constexpr` functions can be evaluated at compile time when given constant expressions, or at runtime when given non-constant arguments. They're regular functions with an extra superpower.

**Q: "Can `constexpr` functions have loops?"**

Yes, since C++14. They can also have local variables, conditionals, and multiple return statements. They just can't have `static` variables, `new`/`delete`, or virtual functions (in C++14; C++20 relaxes some restrictions).

---

## 5. Lambda Expressions

### Capture Lists

```cpp
#include <algorithm>
#include <vector>
#include <iostream>
#include <string>

int main() {
    std::vector<int> v = {5, 3, 1, 4, 2};

    int threshold = 3;
    // Capture by value
    auto count_above = std::count_if(v.begin(), v.end(),
        [threshold](int x) { return x > threshold; });

    // Capture by reference
    int total = 0;
    std::for_each(v.begin(), v.end(),
        [&total](int x) { total += x; });

    // Capture all by value [=] or all by reference [&]
    int offset = 10;
    auto add_offset = [=](int x) { return x + offset; }; // offset by value

    // Mutable lambda (can modify captured-by-value)
    int counter = 0;
    auto inc = [counter]() mutable { return ++counter; };
    std::cout << inc() << "\n"; // 1
    std::cout << inc() << "\n"; // 2

    std::cout << "count_above: " << count_above << "\n"; // 2 (5 and 4)
    std::cout << "total: " << total << "\n";              // 15
}
```

### Generic Lambdas (C++14)

```cpp
#include <iostream>
#include <string>

auto add = [](auto a, auto b) { return a + b; };

int main() {
    std::cout << add(3, 4) << "\n";           // 7 (int + int)
    std::cout << add(3.14, 2.71) << "\n";     // 5.85 (double + double)
    std::cout << add(std::string("a"), std::string("b")) << "\n"; // "ab"
}
```

### Lambdas in STL

```cpp
#include <algorithm>
#include <vector>
#include <iostream>

int main() {
    std::vector<std::pair<int, std::string>> students = {
        {85, "Alice"}, {92, "Bob"}, {78, "Charlie"}, {92, "David"}
    };

    // Sort by score descending, then by name ascending
    std::sort(students.begin(), students.end(),
        [](const auto& a, const auto& b) {
            if (a.first != b.first) return a.first > b.first;
            return a.second < b.second;
        });

    for (auto& [score, name] : students)
        std::cout << name << ": " << score << "\n";
    // Bob: 92
    // David: 92
    // Alice: 85
    // Charlie: 78
}
```

### Interview Application

Lambdas are essential for concise STL usage. In interviews, prefer lambdas over functors for one-off operations. Use named lambdas for complex logic:

```cpp
auto is_valid = [&](const Node& node) {
    return node.value >= 0 && visited.find(node.id) == visited.end();
};
```

---

## 6. Functors (Function Objects)

```cpp
#include <algorithm>
#include <vector>
#include <iostream>

class MultiplyBy {
    int factor;
public:
    explicit MultiplyBy(int f) : factor(f) {}
    int operator()(int x) const { return x * factor; }
};

int main() {
    std::vector<int> v = {1, 2, 3, 4, 5};
    std::transform(v.begin(), v.end(), v.begin(), MultiplyBy(3));
    for (int x : v) std::cout << x << " "; // 3 6 9 12 15
    std::cout << "\n";
}
```

### Functor vs Lambda

| Aspect | Functor | Lambda |
|--------|---------|--------|
| State | Easy (member variables) | Via capture |
| Reusability | Named class, reusable | Usually one-off |
| Inlining | Compiler can inline | Compiler can inline |
| Readability | Verbose for simple ops | Concise |
| Interview preference | Custom comparators with state | Everything else |

---

## 7. Iterator Categories

```
Input → Forward → Bidirectional → Random Access → Contiguous
```

| Category | Operations | Example Containers |
|----------|-----------|-------------------|
| Input | `++`, `*`, `==` | `istream_iterator` |
| Forward | Input + multi-pass | `forward_list`, `unordered_set` |
| Bidirectional | Forward + `--` | `list`, `set`, `map` |
| Random Access | Bidirectional + `+n`, `-n`, `[]`, `<` | `deque` |
| Contiguous | Random Access + contiguous memory | `vector`, `array`, `string` |

### Why It Matters

```cpp
// std::sort requires Random Access iterators
std::sort(v.begin(), v.end());           // OK: vector has random access
// std::sort(l.begin(), l.end());        // ERROR: list only has bidirectional
l.sort();                                 // OK: list has its own sort

// std::reverse requires Bidirectional
std::reverse(l.begin(), l.end());        // OK: list has bidirectional
```

---

## 8. Allocator Basics

### How STL Allocates Memory

Every STL container takes an allocator as a template parameter (default: `std::allocator<T>`). The allocator handles:

1. `allocate(n)` — request memory for `n` objects of type T
2. `deallocate(p, n)` — return memory
3. `construct(p, args...)` — call constructor at address p
4. `destroy(p)` — call destructor at address p

```cpp
#include <memory>
#include <vector>
#include <iostream>

int main() {
    std::allocator<int> alloc;

    // Allocate space for 5 ints
    int* p = alloc.allocate(5);

    // Construct objects
    for (int i = 0; i < 5; ++i)
        std::allocator_traits<decltype(alloc)>::construct(alloc, p + i, i * 10);

    for (int i = 0; i < 5; ++i)
        std::cout << p[i] << " "; // 0 10 20 30 40
    std::cout << "\n";

    // Destroy and deallocate
    for (int i = 0; i < 5; ++i)
        std::allocator_traits<decltype(alloc)>::destroy(alloc, p + i);
    alloc.deallocate(p, 5);
}
```

### Interview Application

You rarely write custom allocators in interviews, but understanding them explains *why* `vector` is fast (contiguous allocation, amortized O(1) push_back) and *how* `pmr::vector` with a pool allocator can eliminate fragmentation.

---

## 9. Exception Safety

### Three Guarantees

| Guarantee | What It Means | Example |
|-----------|--------------|---------|
| **Nothrow** | Operation never throws | Destructors, `std::move` on primitives |
| **Strong** | If exception thrown, state is unchanged | `vector::push_back` (copies to new buffer, swaps) |
| **Basic** | If exception thrown, no leaks, invariants preserved | Most operations |

### Example: Strong Exception Guarantee

```cpp
#include <vector>
#include <iostream>

class Widget {
    int id;
public:
    Widget(int i) : id(i) {}
    Widget(const Widget& other) : id(other.id) {
        if (id < 0) throw std::runtime_error("Negative ID");
    }
    int get() const { return id; }
};

int main() {
    std::vector<Widget> v;
    v.push_back(Widget(1));
    v.push_back(Widget(2));

    try {
        v.push_back(Widget(-1)); // Throws during copy
    } catch (const std::exception& e) {
        std::cout << "Exception: " << e.what() << "\n";
    }

    // Strong guarantee: v still contains {1, 2}
    std::cout << "Size: " << v.size() << "\n"; // 2
}
```

### Interview Application

**Q: "What exception guarantee does `vector::push_back` provide?"**

Strong guarantee. If the element's copy constructor throws, the vector remains unchanged. This works because `push_back` copies to the new buffer first, and only commits (by swapping) if all copies succeed.

---

## 10. STL Internals

### `std::vector`

- **Storage:** Contiguous array on the heap
- **Growth:** When capacity is exceeded, allocates a new buffer (typically 2×), moves/copies elements, frees old buffer
- **push_back:** Amortized O(1), worst-case O(n) when reallocation needed
- **insert/erase at end:** O(1). At middle: O(n) due to shifting

```cpp
#include <vector>
#include <iostream>

int main() {
    std::vector<int> v;
    std::cout << "capacity doubles:\n";
    for (int i = 0; i < 20; ++i) {
        std::cout << "size=" << v.size() << " cap=" << v.capacity() << "\n";
        v.push_back(i);
    }
}
// Typical output: capacity goes 0, 1, 2, 4, 8, 16, 32...
```

### `std::map` (Red-Black Tree)

- **Structure:** Balanced binary search tree (red-black)
- **Ordering:** Elements sorted by key
- **Operations:** O(log n) search, insert, delete
- **Memory:** Each node has key, value, color, left, right, parent pointers (~48 bytes overhead per node)

### `std::unordered_map` (Hash Table)

- **Structure:** Array of buckets, each bucket is a linked list (or vector)
- **Hashing:** Key → hash → bucket index
- **Operations:** Average O(1), worst O(n) if all keys collide
- **Rehash:** When load factor exceeds threshold (default 1.0), rehashes all elements

### Comparison Table

| Aspect | `vector` | `map` | `unordered_map` |
|--------|----------|-------|-----------------|
| Ordering | Insertion order | Sorted by key | No ordering |
| Search | O(n) | O(log n) | O(1) average |
| Insert end | O(1) amortized | N/A | O(1) average |
| Insert middle | O(n) | O(log n) | O(1) average |
| Memory overhead | Minimal | ~48 bytes/node | ~48 bytes + bucket array |
| Cache behavior | Excellent | Poor (pointer chasing) | Moderate (bucket chains) |
| Iterator invalidation | On reallocation/insert/erase | Only on erase of that element | On rehash/erase |

---

## 11. Container Selection Guide

### Decision Tree

```
Need ordered data?
├── Yes → Need O(log n) search/insert/delete?
│   ├── Yes → std::map or std::set
│   └── No  → std::vector (sort once, binary search)
├── No → Need O(1) lookup?
│   ├── Yes → std::unordered_map or std::unordered_set
│   └── No → What operations?
│       ├── Push/pop front and back → std::deque
│       ├── Frequent middle insert/delete → std::list (rare in practice)
│       └── Default → std::vector
└── Need both order AND O(1) lookup?
    → Use both: unordered_map + sorted vector (or boost::bimap)
```

### When to Use Each Container

| Container | Best For | Avoid When |
|-----------|----------|------------|
| `vector` | Default choice, random access, cache-friendly | Frequent middle insert/delete |
| `deque` | Push/pop at both ends | Need contiguous memory |
| `list` | Frequent splice operations | Almost everything else (cache-unfriendly) |
| `forward_list` | Memory-critical, singly-linked | Need backward traversal |
| `map`/`set` | Need sorted order, O(log n) operations | Cache matters, O(1) possible |
| `unordered_map`/`unordered_set` | O(1) lookup, no order needed | Need iteration in order |
| `priority_queue` | Max/min extraction | Need arbitrary access |
| `stack`/`queue` | LIFO/FIFO semantics | Need iteration |

---

## 12. Undefined Behavior

### Common UB Traps

```cpp
// 1. Signed integer overflow
int x = INT_MAX;
x += 1;  // UB!

// 2. Null pointer dereference
int* p = nullptr;
*p = 42;  // UB!

// 3. Use after free
int* p = new int(42);
delete p;
*p = 10;  // UB!

// 4. Array out of bounds
int arr[5] = {1, 2, 3, 4, 5};
arr[5] = 10;  // UB! (arr[5] is one past the end — legal to compute, not to write)

// 5. Signed/unsigned comparison bugs
unsigned int a = 0;
int b = -1;
if (a < b) {
    // This is TRUE because b is converted to unsigned!
    // (unsigned)-1 = UINT_MAX
}

// 6. Null dereference through member access
struct S { int x; };
S* p = nullptr;
int y = p->x;  // UB!

// 7. Strict aliasing violation
float f = 3.14f;
int* ip = reinterpret_cast<int*>(&f);
int i = *ip;  // UB! (strict aliasing violation)

// 8. Modifying a const object
const int x = 42;
const_cast<int&>(x) = 10;  // UB if x was originally const!
```

### Interview Application

**Q: "What's undefined behavior? Why does it matter?"**

UB means the compiler can do *anything* — crash, produce wrong results, or appear to work (the worst case). It matters because:
1. Optimizations assume UB doesn't happen
2. Code that "works" may break with a different compiler or optimization level
3. Security vulnerabilities often stem from UB

---

## 13. Common STL Pitfalls

### Iterator Invalidation

```cpp
#include <vector>
#include <iostream>

int main() {
    std::vector<int> v = {1, 2, 3, 4, 5};

    // WRONG: erase invalidates iterators
    // for (auto it = v.begin(); it != v.end(); ++it)
    //     if (*it % 2 == 0) v.erase(it);  // UB!

    // CORRECT: erase returns next valid iterator
    for (auto it = v.begin(); it != v.end(); ) {
        if (*it % 2 == 0)
            it = v.erase(it);
        else
            ++it;
    }

    // Or use erase-remove idiom
    v = {1, 2, 3, 4, 5};
    v.erase(std::remove_if(v.begin(), v.end(),
            [](int x) { return x % 2 == 0; }),
            v.end());

    for (int x : v) std::cout << x << " "; // 1 3 5
    std::cout << "\n";
}
```

### Comparator Requirements

```cpp
#include <set>
#include <iostream>

// WRONG: comparator must define strict weak ordering
struct BadComp {
    bool operator()(int a, int b) const {
        return a <= b; // Not strict weak ordering! (a <= a is true)
    }
};

// CORRECT: strict weak ordering (irreflexive, antisymmetric, transitive)
struct GoodComp {
    bool operator()(int a, int b) const {
        return a < b;
    }
};

int main() {
    // std::set<int, BadComp> bad; // May cause infinite loops or crashes
    std::set<int, GoodComp> good = {3, 1, 4, 1, 5};
    for (int x : good) std::cout << x << " "; // 1 3 4 5
    std::cout << "\n";
}
```

### `std::string::npos` Comparison

```cpp
#include <string>
#include <iostream>

int main() {
    std::string s = "hello";
    auto pos = s.find("world");

    // WRONG: pos is size_t (unsigned), comparing with -1 is dangerous
    // if (pos == -1) { ... }

    // CORRECT:
    if (pos == std::string::npos) {
        std::cout << "Not found\n";
    }
}
```

---

## 14. Memory Complexity of STL

| Container | Memory Overhead | Element Storage |
|-----------|----------------|-----------------|
| `vector<T>` | 3 pointers (begin, end, capacity) = 24 bytes | Contiguous, no per-element overhead |
| `deque<T>` | Array of pointers to fixed-size blocks + metadata (~80 bytes) | Per-block overhead |
| `list<T>` | 3 pointers per node (prev, next, data) = 24 bytes + element | Heap-allocated nodes |
| `forward_list<T>` | 1 pointer per node (next) = 8 bytes + element | Heap-allocated nodes |
| `map<K,V>` | ~48 bytes per node (key, value, left, right, parent, color) | Red-black tree nodes |
| `unordered_map<K,V>` | ~48 bytes per node + bucket array (~1 byte per bucket) | Hash table with chains |
| `set<T>` | ~48 bytes per node | Same as map |
| `priority_queue<T>` | Container overhead (default: vector) | Same as underlying container |

---

## 15. Thread Safety of STL

### The Rule

**The standard guarantees:**
- **Const member functions** can be called concurrently on the same object
- **Non-const member functions** on the same object are NOT thread-safe
- Different objects can be accessed concurrently without synchronization

### Common Pitfalls

```cpp
// UNSAFE: concurrent modification
std::vector<int> v = {1, 2, 3};
// Thread 1: v.push_back(4);  // May trigger reallocation
// Thread 2: int x = v[0];    // May read from freed memory during reallocation

// UNSAFE: concurrent read and modification
std::map<int, int> m = {{1, 10}, {2, 20}};
// Thread 1: m[3] = 30;      // May rehash (for unordered_map)
// Thread 2: auto it = m.find(1); // Iterator may be invalidated
```

### Safe Patterns

```cpp
#include <shared_mutex>
#include <map>

template<typename K, typename V>
class ThreadSafeMap {
    mutable std::shared_mutex mtx_;
    std::map<K, V> data_;
public:
    V get(const K& key) const {
        std::shared_lock lock(mtx_);  // Multiple readers OK
        auto it = data_.find(key);
        return it != data_.end() ? it->second : V{};
    }
    void put(const K& key, const V& val) {
        std::unique_lock lock(mtx_);  // Exclusive access
        data_[key] = val;
    }
};
```

---

## Design Decisions

### When NOT to Use Templates

- When the code is simple and specific to one type → just write it for that type
- When runtime polymorphism is needed → use virtual functions
- When compile times matter → templates increase compilation time
- When debugging → template error messages can be cryptic

**Alternatives:** Virtual functions (runtime polymorphism), `std::variant` + `std::visit` (type-safe union), `std::any` (type-erased container).

### When NOT to Use Lambdas

- When the logic is complex and reusable → use a named class/function
- When you need recursive lambdas → use `std::function` or a named function
- When the capture list gets complicated → extract to a class with members

### Trade-offs

| Feature | Pros | Cons |
|---------|------|------|
| Templates | Zero-cost abstraction, compile-time optimization | Code bloat, long compile times, cryptic errors |
| Virtual functions | Runtime flexibility, clean interfaces | vtable overhead, can't inline |
| Lambdas | Concise, inline-able | Can't be recursive easily, complex captures |
| Exceptions | Clean error propagation | Performance cost, hard to reason about |
| `std::variant` | Type-safe union | Visitor pattern complexity |

---

## Summary

C++ is a large language, but interviews test a focused subset: templates for generic code, references and move semantics for efficiency, lambdas for concise STL usage, and deep knowledge of how STL containers work internally. Know the common pitfalls (iterator invalidation, UB, comparator requirements), understand the performance characteristics of each container, and be able to articulate *why* you'd choose one over another. The best C++ code in interviews is not the cleverest — it's the clearest, most correct, and most appropriate for the problem.
