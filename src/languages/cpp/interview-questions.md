# C++ Interview Questions

## Memory Management

### Q1: What is RAII?

Resource Acquisition Is Initialization. Tie resource lifetime to object lifetime. Resources are acquired in constructors and released in destructors.

```cpp
class FileHandle {
    FILE* f;
public:
    FileHandle(const char* name) : f(fopen(name, "r")) {
        if (!f) throw std::runtime_error("open failed");
    }
    ~FileHandle() { if (f) fclose(f); }
    // Delete copy, allow move
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;
    FileHandle(FileHandle&& o) noexcept : f(o.f) { o.f = nullptr; }
};
```

### Q2: unique_ptr vs shared_ptr vs weak_ptr?

| Type | Ownership | Overhead | Use Case |
|------|-----------|----------|----------|
| `unique_ptr` | Single owner | Zero | Default choice |
| `shared_ptr` | Shared (ref count) | Atomic ref count | Multiple owners |
| `weak_ptr` | Non-owning observer | Pointer to control block | Break cycles |

```cpp
auto p = std::make_unique<int>(42);       // Single owner
auto sp = std::make_shared<int>(42);      // Shared ownership
std::weak_ptr<int> wp = sp;               // Observer
if (auto locked = wp.lock()) { /* use locked */ }
```

### Q3: What happens with circular references?

```cpp
struct Node {
    std::shared_ptr<Node> next; // Cycle! Reference count never reaches 0
};
// Fix: use weak_ptr for back-references
struct Node {
    std::weak_ptr<Node> parent; // Weak reference breaks cycle
    std::shared_ptr<Node> child;
};
```

### Q4: How does std::make_shared differ from shared_ptr(new T)?

`make_shared` does a single allocation (object + control block). `shared_ptr(new T)` does two allocations. `make_shared` is more efficient and exception-safe.

## Move Semantics

### Q5: What is std::move?

`std::move` doesn't move anything. It casts its argument to an rvalue reference, enabling move semantics. The actual move happens in the move constructor/assignment.

```cpp
std::string s = "hello";
std::string t = std::move(s); // Move constructor called
// s is now in a valid but unspecified state
```

### Q6: Rule of 5?

If you define any of: destructor, copy constructor, copy assignment, move constructor, move assignment — define all five.

```cpp
class Buffer {
    int* data;
    size_t size;
public:
    ~Buffer() { delete[] data; }                                    // 1
    Buffer(const Buffer& o) : data(new int[o.size]), size(o.size) { // 2
        std::copy(o.data, o.data+size, data);
    }
    Buffer& operator=(const Buffer& o) {                            // 3
        if (this != &o) { delete[] data; size=o.size; data=new int[size]; std::copy(o.data,o.data+size,data); }
        return *this;
    }
    Buffer(Buffer&& o) noexcept : data(o.data), size(o.size) {      // 4
        o.data = nullptr; o.size = 0;
    }
    Buffer& operator=(Buffer&& o) noexcept {                        // 5
        if (this != &o) { delete[] data; data=o.data; size=o.size; o.data=nullptr; o.size=0; }
        return *this;
    }
};
```

### Q7: Copy elision (RVO/NRVO)?

The compiler can eliminate copy/move constructors entirely. Since C++17, copy elision is mandatory in certain cases (prvalue materialization).

```cpp
Widget create() {
    return Widget(); // RVO: no copy/move, constructed directly at caller's site
}
```

## Templates

### Q8: SFINAE?

Substitution Failure Is Not An Error. If template argument substitution fails, the overload is silently removed instead of causing a compile error.

```cpp
template<typename T>
auto serialize(T const& t) -> decltype(t.serialize()) {
    return t.serialize(); // Only for types with serialize()
}

template<typename T>
std::string serialize(T const& t) {
    return std::to_string(t); // Fallback
}
```

### Q9: Concepts (C++20)?

```cpp
template<typename T>
concept Sortable = requires(T a, T b) {
    { a < b } -> std::convertible_to<bool>;
    { a > b } -> std::convertible_to<bool>;
};

template<Sortable T>
void sort(std::vector<T>& v) { std::sort(v.begin(), v.end()); }
```

### Q10: Variadic templates?

```cpp
template<typename... Args>
void print(Args&&... args) {
    (std::cout << ... << args) << "\n"; // C++17 fold expression
}

// Recursive expansion (pre-C++17)
void print() {} // Base case
template<typename T, typename... Rest>
void print(T&& first, Rest&&... rest) {
    std::cout << first;
    print(std::forward<Rest>(rest)...);
}
```

## Concurrency

### Q11: std::atomic and memory ordering?

```cpp
std::atomic<int> x{0}, y{0};

// Sequential consistency (default, safest)
x.store(1, std::memory_order_seq_cst);

// Acquire-Release (faster, still safe for producer-consumer)
// Thread 1
x.store(1, std::memory_order_release);
// Thread 2
if (x.load(std::memory_order_acquire) == 1) { /* sees all prior writes */ }

// Relaxed (fastest, only atomicity guarantee)
x.fetch_add(1, std::memory_order_relaxed);
```

### Q12: How to avoid data races?

```cpp
// Option 1: mutex
std::mutex m;
{
    std::lock_guard<std::mutex> lock(m);
    shared_data++;
}

// Option 2: atomic
std::atomic<int> counter{0};
counter++; // Thread-safe

// Option 3: lock-free (advanced)
// Compare-and-swap loops
```

### Q13: condition_variable usage?

```cpp
std::mutex m;
std::condition_variable cv;
bool ready = false;

// Producer
{
    std::lock_guard<std::mutex> lk(m);
    ready = true;
}
cv.notify_one();

// Consumer
std::unique_lock<std::mutex> lk(m);
cv.wait(lk, [] { return ready; }); // Avoids spurious wakeups
```

## Modern C++

### Q14: What is constexpr?

```cpp
constexpr int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}
constexpr int x = factorial(5); // Computed at compile time
int arr[x]; // OK: x is compile-time constant
```

### Q15: Structured bindings (C++17)?

```cpp
auto [x, y] = std::make_pair(1, 2);
auto [iter, success] = map.insert({key, value});
for (const auto& [key, value] : map) { /* ... */ }
```

### Q16: std::optional, std::variant, std::any?

```cpp
// Optional: may or may not have a value
// (illustrative pseudocode — `found`/`value` represent your lookup result)
std::optional<int> find(int key) {
    if (db.contains(key)) return db[key];   // value found
    return std::nullopt;                      // not found
}

// Variant: type-safe union (one of specified types)
std::variant<int, std::string> v = "hello";
std::visit(overloaded{
    [](int i) { /* ... */ },
    [](const std::string& s) { /* ... */ }
}, v);

// Any: any type (type-erased)
std::any a = 42;
int i = std::any_cast<int>(a);
```

### Q17: Coroutines (C++20)?

```cpp
#include <coroutine>
#include <generator>  // std::generator is C++23 (P2502)

// C++23 std::generator coroutine (C++20 coroutines require a hand-rolled
// or library-provided generator type; std::generator was added in C++23).
std::generator<int> fibonacci() {
    int a = 0, b = 1;
    while (true) {
        co_yield a;
        auto temp = a;
        a = b;
        b = temp + b;
    }
}
```

## STL

### Q18: vector vs deque vs list?

| Container | Random Access | Insert End | Insert Middle | Memory |
|-----------|:---:|:---:|:---:|----------|
| `vector` | O(1) | Amortized O(1) | O(n) | Contiguous |
| `deque` | O(1) | O(1) | O(n) | Chunked |
| `list` | O(n) | O(1) | O(1) at position | Nodes |

### Q19: unordered_map internals?

Hash table with separate chaining (or open addressing). Buckets store key-value pairs. Load factor triggers rehash. Average O(1) lookup, worst O(n) with bad hash.

### Q20: Iterator invalidation?

| Container | Insert | Erase |
|-----------|--------|-------|
| `vector` | Invalidates all after point | Invalidates all after point |
| `deque` | Invalidates all | Invalidates all |
| `list` | None invalidated | Only erased element |
| `map/set` | None invalidated | Only erased element |

## Advanced

### Q21: Virtual function table (vtable)?

Each class with virtual functions has a vtable (array of function pointers). Each object has a vptr pointing to its class's vtable. Virtual dispatch: follow vptr → index vtable → call function.

### Q22: Diamond problem and virtual inheritance?

```cpp
class A { public: int x; };
class B : virtual public A {}; // Virtual inheritance
class C : virtual public A {};
class D : public B, public C {};
// D has only one A::x
```

### Q23: Perfect forwarding?

```cpp
template<typename T>
void wrapper(T&& arg) {
    // std::forward preserves the value category
    target(std::forward<T>(arg)); // lvalues stay lvalues, rvalues stay rvalues
}
```

### Q24: What is type erasure?

Technique to hide concrete type behind a uniform interface. `std::function`, `std::any`, `std::shared_ptr` use type erasure.

### Q25: CRTP (Curiously Recurring Template Pattern)?

```cpp
template<typename Derived>
class Base {
public:
    void interface() {
        static_cast<Derived*>(this)->implementation();
    }
};

class MyClass : public Base<MyClass> {
public:
    void implementation() { /* ... */ }
};
```

### Q26: Pimpl idiom?

```cpp
// widget.h
class Widget {
    struct Impl;            // Forward declaration
    std::unique_ptr<Impl> pImpl;
public:
    Widget();
    ~Widget();
};

// widget.cpp
struct Widget::Impl { /* private members */ };
Widget::Widget() : pImpl(std::make_unique<Impl>()) {}
Widget::~Widget() = default;
```

### Q27: What are the C++ memory model guarantees?

- Every thread sees its own modifications in order
- Atomic operations are sequentially consistent by default
- Data races cause undefined behavior
- `std::atomic` and `std::mutex` establish happens-before relationships

### Q28: Placement new?

```cpp
// Construct object at pre-allocated memory
char buffer[sizeof(Widget)];
Widget* w = new (buffer) Widget(args...); // Placement new
w->~Widget(); // Must explicitly call destructor
```

### Q29: Compile-time vs runtime polymorphism?

| Compile-time (templates) | Runtime (virtual) |
|--------------------------|-------------------|
| No overhead | vtable overhead |
| Code bloat | Single implementation |
| Duck typing | Explicit interface |
| Detected at compile time | Errors at runtime |

### Q30: What is std::string_view?

Non-owning reference to a string. Zero-copy, no allocation. Use for read-only string parameters.

```cpp
void process(std::string_view sv) { /* ... */ }
process("hello"); // No allocation
process(std::string("hello")); // No allocation
```

## Related Topics

- [C++ Overview](./README.md) — Language overview
- [Move Semantics](./move-semantics.md) — Deep dive
- [Concurrency](./concurrency.md) — Threading
- [Modern C++](./modern-cpp.md) — C++11-23 features
