# Chapter 90: C++ Deep Dive for Interviews

## Prerequisites

- C++ basics (variables, loops, functions, classes)
- Basic OOP concepts (encapsulation, inheritance, polymorphism)
- Familiarity with pointers and references

## Interview Frequency: ★★★★

Deep C++ knowledge is tested at **Google**, **Meta**, **Amazon**, and systems companies. Modern C++ (C++11/14/17/20) questions are now standard in senior-level interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Rule of 5 | ★★★★ | Medium | Copy/move semantics |
| Move semantics | ★★★★ | Medium | std::move, rvalue refs |
| Smart pointers | ★★★ | Medium | unique_ptr, shared_ptr |
| Value categories | ★★★ | Medium | lvalue, rvalue, xvalue |
| RAII | ★★★★ | Medium | Resource management |
| Templates | ★★★ | Medium-Hard | Generic programming |
| Const correctness | ★★★ | Medium | const, constexpr, consteval |

---

## Definition

The **Rule of Five** states that if a class manages a resource and defines any one of the five special member functions (destructor, copy constructor, copy assignment operator, move constructor, move assignment operator), it should define all five. This ensures correct resource management and prevents subtle bugs from implicit generation of these functions.

## Motivation

In C++, the compiler can auto-generate special member functions. When a class manages raw resources (heap memory, file handles, sockets), these auto-generated functions perform shallow copies, leading to:
- **Double-free errors** when two objects point to the same memory
- **Memory leaks** when resources aren't properly released
- **Dangling pointers** after moves

Understanding the Rule of Five is essential for writing correct, efficient C++ code — and it's a favorite interview topic.

## Intuition

Think of owning a house (resource). If you copy yourself, should the clone own the same house? No — they need their own house (deep copy). If you move to a new city, you transfer the house deed (move semantics) — the old you no longer owns it.

---

## 90.1 Rule of Five — Deep Dive

If you define any of: destructor, copy constructor, copy assignment, move constructor, move assignment — you should define all five.

### The Five Special Members

| Member | Signature | When Called |
|---|---|---|
| Destructor | `~T()` | Object goes out of scope, `delete` |
| Copy constructor | `T(const T&)` | `T b = a;`, pass by value |
| Copy assignment | `T& operator=(const T&)` | `b = a;` (both already exist) |
| Move constructor | `T(T&&) noexcept` | `T b = std::move(a);` |
| Move assignment | `T& operator=(T&&) noexcept` | `b = std::move(a);` (both exist) |

### Step-by-Step Walkthrough

Consider a class `MyString` that owns a `char*`:

1. **Constructor** allocates heap memory for the string
2. **Destructor** frees that memory
3. **Copy constructor** allocates new memory and copies the content (deep copy)
4. **Copy assignment** frees old memory, then allocates and copies
5. **Move constructor** steals the pointer from the source, nullifies source
6. **Move assignment** frees old memory, steals pointer, nullifies source

### Dry Run

```
MyString s1("Hello");     // Constructor: allocates 6 bytes, copies "Hello"
MyString s2 = s1;          // Copy constructor: s2 gets its own 6 bytes
MyString s3 = std::move(s1); // Move constructor: s3 steals s1's pointer
                           // s1.data is now nullptr
s2 = s3;                   // Copy assignment: s2 frees old, allocates new, copies
s3 = std::move(s2);        // Move assignment: s3 frees old, steals s2's pointer
```

### Complete Implementation

```cpp
#include <iostream>
#include <cstring>
#include <utility>

class MyString {
    char* data;
    size_t len;

public:
    // Constructor
    MyString(const char* s = "") : len(strlen(s)) {
        data = new char[len + 1];
        memcpy(data, s, len + 1);
    }

    // 1. Destructor
    ~MyString() { delete[] data; }

    // 2. Copy constructor
    MyString(const MyString& other) : len(other.len) {
        data = new char[len + 1];
        memcpy(data, other.data, len + 1);
    }

    // 3. Copy assignment
    MyString& operator=(const MyString& other) {
        if (this != &other) {           // Self-assignment guard
            delete[] data;              // Free old resource
            len = other.len;
            data = new char[len + 1];   // Allocate new
            memcpy(data, other.data, len + 1);  // Deep copy
        }
        return *this;
    }

    // 4. Move constructor
    MyString(MyString&& other) noexcept : data(other.data), len(other.len) {
        other.data = nullptr;   // Leave source in valid state
        other.len = 0;
    }

    // 5. Move assignment
    MyString& operator=(MyString&& other) noexcept {
        if (this != &other) {
            delete[] data;          // Free old resource
            data = other.data;      // Steal resource
            len = other.len;
            other.data = nullptr;   // Nullify source
            other.len = 0;
        }
        return *this;
    }

    void print() const {
        std::cout << (data ? data : "(null)") << "\n";
    }

    size_t size() const { return len; }
};

int main() {
    MyString s1("Hello");
    MyString s2 = s1;               // Copy constructor
    MyString s3 = std::move(s1);    // Move constructor

    s2.print(); // Hello
    s3.print(); // Hello
    s1.print(); // (null) — moved-from state

    MyString s4("World");
    s4 = s2;                        // Copy assignment
    s4 = std::move(s3);            // Move assignment

    s4.print(); // Hello
    s3.print(); // (null) — moved-from

    return 0;
}
```

### Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| Copy constructor | O(n) — must copy data | O(n) — allocates new memory |
| Move constructor | O(1) — pointer swap | O(1) — no allocation |
| Copy assignment | O(n) — copy + delete old | O(n) — allocates new |
| Move assignment | O(1) — pointer swap | O(1) — no allocation |
| Destructor | O(1) — delete array | O(1) |

---

## 90.2 Smart Pointers

Smart pointers manage heap memory automatically using RAII, eliminating manual `delete` calls.

| Type | Ownership | Use Case | Overhead |
|---|---|---|---|
| `unique_ptr` | Single owner | Default choice | Zero overhead |
| `shared_ptr` | Shared ownership | Reference counted | Control block allocation |
| `weak_ptr` | Non-owning ref | Break cycles | Minimal |

### Motivation

Raw pointers have no ownership semantics. Who deletes `p`? When? Smart pointers answer these questions at compile time (`unique_ptr`) or runtime (`shared_ptr`).

### unique_ptr — Exclusive Ownership

```cpp
#include <iostream>
#include <memory>

struct Node {
    int val;
    std::unique_ptr<Node> next;
    Node(int v) : val(v) {}
};

int main() {
    auto head = std::make_unique<Node>(1);
    head->next = std::make_unique<Node>(2);
    head->next->next = std::make_unique<Node>(3);

    // Traverse
    for (auto* curr = head.get(); curr; curr = curr->next.get())
        std::cout << curr->val << " ";
    std::cout << "\n";  // Output: 1 2 3

    // Cannot copy unique_ptr (compile error)
    // auto head2 = head;  // ERROR

    // Can move
    auto head2 = std::move(head);  // head is now nullptr
    // head->val;  // ERROR: nullptr dereference

    return 0;
    // All nodes automatically deleted here
}
```

### shared_ptr — Reference Counting

```cpp
#include <iostream>
#include <memory>

int main() {
    auto sp1 = std::make_shared<int>(42);
    std::cout << "Count: " << sp1.use_count() << "\n";  // 1

    {
        auto sp2 = sp1;  // Copy → count = 2
        std::cout << "Count: " << sp1.use_count() << "\n";  // 2
    }  // sp2 destroyed → count = 1

    std::cout << "Count: " << sp1.use_count() << "\n";  // 1
    std::cout << "Value: " << *sp1 << "\n";  // 42

    return 0;
}
```

### weak_ptr — Breaking Cycles

```cpp
#include <iostream>
#include <memory>

struct Child;

struct Parent {
    std::shared_ptr<Child> child;
    ~Parent() { std::cout << "Parent destroyed\n"; }
};

struct Child {
    std::weak_ptr<Parent> parent;  // weak_ptr breaks the cycle!
    ~Child() { std::cout << "Child destroyed\n"; }
};

int main() {
    auto parent = std::make_shared<Parent>();
    auto child = std::make_shared<Child>();
    parent->child = child;
    child->parent = parent;

    // Access weak_ptr
    if (auto p = child->parent.lock()) {
        std::cout << "Parent accessible\n";
    }

    return 0;
    // Both destroyed correctly — no leak
}
```

---

## 90.3 Value Categories

Understanding value categories is crucial for understanding when copies vs moves happen.

| Category | Example | Can bind to `T&&`? | Can bind to `const T&`? |
|---|---|---|---|
| **lvalue** | `x`, `*p`, `arr[i]` | No | Yes |
| **prvalue** | `42`, `x + y`, `T()` | Yes | Yes |
| **xvalue** | `std::move(x)`, `static_cast<T&&>(x)` | Yes | Yes |

### Explanation

- **lvalue** (locator value): Has an address. You can take its address with `&`.
- **prvalue** (pure rvalue): A temporary, no persistent address. Created by literals or expressions.
- **xvalue** (expiring value): An lvalue that has been cast to an rvalue reference. About to be moved from.

```cpp
#include <iostream>
#include <utility>

void process(const std::string& s) {
    std::cout << "lvalue ref: " << s << "\n";
}

void process(std::string&& s) {
    std::cout << "rvalue ref: " << s << "\n";
}

int main() {
    std::string a = "hello";
    process(a);                    // lvalue ref (a is lvalue)
    process(std::move(a));         // rvalue ref (std::move casts to xvalue)
    process("world");              // rvalue ref (string literal creates prvalue)
    process(std::string("test"));  // rvalue ref (temporary prvalue)
}
```

---

## 90.4 RAII (Resource Acquisition Is Initialization)

RAII ties resource lifetime to object lifetime. Resources are acquired in the constructor and released in the destructor.

### Why RAII Matters

```cpp
// BAD: Exception-unsafe
void bad() {
    int* p = new int[1000];
    risky_function();  // If this throws, p leaks!
    delete[] p;
}

// GOOD: RAII
void good() {
    std::vector<int> v(1000);
    risky_function();  // If this throws, v's destructor runs automatically
}  // v cleaned up here regardless
```

### Custom RAII Example: File Handle

```cpp
#include <iostream>
#include <cstdio>
#include <stdexcept>

class FileHandle {
    FILE* file;

public:
    explicit FileHandle(const char* filename, const char* mode)
        : file(fopen(filename, mode)) {
        if (!file) throw std::runtime_error("Cannot open file");
    }

    ~FileHandle() {
        if (file) fclose(file);
    }

    // Prevent copying
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;

    // Allow moving
    FileHandle(FileHandle&& other) noexcept : file(other.file) {
        other.file = nullptr;
    }

    FileHandle& operator=(FileHandle&& other) noexcept {
        if (this != &other) {
            if (file) fclose(file);
            file = other.file;
            other.file = nullptr;
        }
        return *this;
    }

    FILE* get() const { return file; }
};

int main() {
    try {
        FileHandle f("test.txt", "w");
        fprintf(f.get(), "Hello RAII!\n");
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
    }
    // File automatically closed here, even if exception thrown
    return 0;
}
```

---

## 90.5 Const Correctness

| Keyword | Meaning | Example |
|---|---|---|
| `const` | Runtime immutable | `const int x = 5;` |
| `constexpr` | Compile-time evaluable | `constexpr int sq(int n) { return n*n; }` |
| `consteval` | Must be compile-time (C++20) | `consteval int sq(int n) { return n*n; }` |

```cpp
#include <iostream>

constexpr int factorial(int n) {
    return (n <= 1) ? 1 : n * factorial(n - 1);
}

int main() {
    constexpr int f5 = factorial(5);  // Computed at compile time
    std::cout << "5! = " << f5 << "\n";  // 120

    // const: runtime value that cannot change
    int x = 10;
    const int& ref = x;  // Cannot modify x through ref
    // ref = 20;  // ERROR

    const int* p = &x;   // Pointer to const int
    // *p = 20;  // ERROR

    int* const q = &x;   // Const pointer to int
    *q = 20;   // OK: can modify through q
    // q = nullptr;  // ERROR: cannot reseat q

    return 0;
}
```

---

## Exercises

1. **Rule of 5 practice**: Implement a `DynamicArray` class that manages a `int*` and `size_t`. Include all five special members. Test with copies and moves.

2. **Smart pointer linked list**: Build a doubly-linked list using `unique_ptr` for `next` and raw pointers (or `weak_ptr`) for `prev`. Implement `push_back`, `pop_front`, and iteration.

3. **RAII wrapper**: Write an RAII wrapper for a mutex lock (use `std::mutex` as the underlying type). Ensure the lock is released in the destructor.

4. **Value category quiz**: For each expression below, determine if it's an lvalue, prvalue, or xvalue:
   - `std::string("hello")`
   - `std::move(a)` where `a` is `std::string`
   - `a + b` where both are `int`
   - `*ptr` where `ptr` is `int*`
   - `a[0]` where `a` is `int[10]`

5. **constexpr challenge**: Write a `constexpr` function that computes the nth Fibonacci number. Verify it works at compile time.

---

## Interview Questions

1. **Q: What happens if you define a destructor but not a copy constructor?**
   A: The compiler generates a copy constructor that does shallow copy. If your destructor frees a resource, the shallow copy leads to double-free. This is the "Rule of Three" problem.

2. **Q: Why is `noexcept` important on move operations?**
   A: Standard library containers (e.g., `std::vector` reallocation) use move operations only if they're `noexcept`. If move can throw, containers fall back to copy for safety, losing performance benefits.

3. **Q: What's the difference between `std::move` and `std::forward`?**
   A: `std::move` unconditionally casts to an rvalue reference. `std::forward` conditionally casts — it preserves the value category of the original argument in template code (perfect forwarding).

4. **Q: Explain the difference between `unique_ptr` and `shared_ptr`. When would you use each?**
   A: `unique_ptr` has zero overhead — it's a compile-time ownership transfer. `shared_ptr` uses a control block with reference count for shared ownership. Use `unique_ptr` as default; use `shared_ptr` only when multiple owners are genuinely needed.

5. **Q: Can a `shared_ptr` be constructed from a `unique_ptr`?**
   A: Yes, via `std::move`: `auto sp = std::make_unique<int>(5); auto sp2 = std::shared_ptr<int>(std::move(sp));`. The `unique_ptr` is invalidated. The reverse is not possible.

6. **Q: What is the "Rule of Zero"?**
   A: If your class doesn't manage any resources, don't define any special member functions. Let the compiler generate them. Compose with RAII types (`std::string`, `std::vector`, smart pointers) instead.

---

## Cross-References

- [Chapter 14: Binary Search Trees](ch14-bst.md) — BST node classes benefit from smart pointers for automatic cleanup
- [Chapter 75: Persistent Data Structures](ch75-persistent-ds.md) — Shared pointers enable structural sharing in persistent trees
- [Chapter 157: Link-Cut Trees](ch157-link-cut-trees.md) — Advanced tree structures that benefit from move semantics
- Chapter 91: STL Deep Dive — STL containers use RAII and move semantics extensively
- Chapter 93: Template Metaprogramming — Templates and constexpr are core to generic C++

---

## Summary

| Concept | Key Point |
|---|---|
| Rule of 5 | Define all or none of special members when managing resources |
| Rule of Zero | Prefer composing RAII types over manual resource management |
| RAII | Acquire in constructor, release in destructor — guarantees cleanup |
| unique_ptr | Default smart pointer, zero overhead, single owner |
| shared_ptr | Reference-counted shared ownership, use sparingly |
| move semantics | Transfer ownership cheaply via `std::move` |
| Value categories | lvalue (has address), prvalue (temporary), xvalue (expiring) |
| const correctness | Use `const` everywhere possible; prefer `constexpr` for compile-time |
