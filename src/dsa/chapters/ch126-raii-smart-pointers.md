# Chapter 126: RAII and Smart Pointers

## Prerequisites
- C++ basics, OOP, pointers, memory management

## Interview Frequency: ★★★★

RAII is the foundational C++ idiom for resource management. **Google**, **Meta**, **Amazon**, and **Microsoft** test this extensively—smart pointer questions appear in system design interviews, and RAII understanding is assumed for any senior C++ role.

---

## 126.1 What Is RAII?

**RAII** stands for **Resource Acquisition Is Initialization**. It is a C++ programming idiom where a resource's lifetime is bound to an object's scope:

- **Acquire** the resource in the constructor.
- **Release** the resource in the destructor.
- **Scope exit** (normal return, exception, early return) automatically invokes the destructor, guaranteeing cleanup.

### Motivation

Manual resource management is error-prone:

```cpp
void dangerous() {
    int* p = new int(42);
    if (someCondition()) return;  // LEAK: forgot delete
    // ... more code that might throw ...
    delete p;  // may never reach here
}
```

Every `new` must have a matching `delete`, every `lock()` must have an `unlock()`, every `open()` must have a `close()`. As code grows, humans forget. RAII eliminates this class of bugs entirely.

### Intuition

Think of RAII like a **self-cleaning kitchen**. You acquire ingredients (resources) when you start cooking (construction). When you leave the kitchen (scope exit), everything is automatically cleaned up (destruction). You never have to remember to wash the dishes—they wash themselves.

### Formal Explanation

An RAII class wraps a resource and guarantees:
1. **Invariant**: The resource is valid from construction to destruction.
2. **Exception safety**: Cleanup happens even if an exception is thrown.
3. **No leaking**: Every path out of scope triggers the destructor.

The C++ standard guarantees that local objects are destroyed in reverse order of construction when leaving scope, even during stack unwinding from exceptions.

---

## 126.2 RAII Examples

### File Handler

```cpp
#include <iostream>
#include <fstream>
#include <string>
#include <stdexcept>

class FileHandler {
    std::ofstream file;
    std::string filename;

public:
    // Acquire resource in constructor
    explicit FileHandler(const std::string& name) : file(name), filename(name) {
        if (!file.is_open())
            throw std::runtime_error("Cannot open file: " + name);
    }

    // Release resource in destructor
    ~FileHandler() {
        if (file.is_open()) {
            file.close();
        }
    }

    // Non-copyable (resource is exclusive)
    FileHandler(const FileHandler&) = delete;
    FileHandler& operator=(const FileHandler&) = delete;

    // Movable (transfer ownership)
    FileHandler(FileHandler&& other) noexcept
        : file(std::move(other.file)), filename(std::move(other.filename)) {}

    FileHandler& operator=(FileHandler&& other) noexcept {
        if (this != &other) {
            if (file.is_open()) file.close();
            file = std::move(other.file);
            filename = std::move(other.filename);
        }
        return *this;
    }

    void write(const std::string& data) { file << data; }
    bool isOpen() const { return file.is_open(); }
};
```

### Mutex Lock Guard

```cpp
#include <mutex>

class LockGuard {
    std::mutex& mtx;

public:
    explicit LockGuard(std::mutex& m) : mtx(m) {
        mtx.lock();    // Acquire lock
    }

    ~LockGuard() {
        mtx.unlock();  // Release lock
    }

    LockGuard(const LockGuard&) = delete;
    LockGuard& operator=(const LockGuard&) = delete;
};

// Usage: lock released automatically when guard goes out of scope
void threadSafeFunction() {
    std::mutex mtx;
    {
        LockGuard guard(mtx);
        // Critical section
    } // Mutex unlocked here, even if exception thrown
}
```

### RAII for Dynamic Arrays

```cpp
class DynamicArray {
    int* data;
    size_t size;

public:
    explicit DynamicArray(size_t n) : data(new int[n]()), size(n) {}
    ~DynamicArray() { delete[] data; }

    // Non-copyable, movable
    DynamicArray(const DynamicArray&) = delete;
    DynamicArray& operator=(const DynamicArray&) = delete;

    DynamicArray(DynamicArray&& other) noexcept : data(other.data), size(other.size) {
        other.data = nullptr;
        other.size = 0;
    }

    int& operator[](size_t i) { return data[i]; }
    const int& operator[](size_t i) const { return data[i]; }
    size_t getSize() const { return size; }
};
```

---

## 126.3 Smart Pointers

Smart pointers are RAII wrappers for heap-allocated memory. They are the primary reason most modern C++ code never uses raw `new`/`delete`.

### `std::unique_ptr` — Exclusive Ownership

| Property | Value |
|---|---|
| Ownership | Single owner |
| Overhead | Zero (same as raw pointer) |
| Copyable | No (move only) |
| Use case | Default choice for heap allocation |

```cpp
#include <memory>
#include <iostream>

struct Node {
    int val;
    std::unique_ptr<Node> next;
    explicit Node(int v) : val(v), next(nullptr) {}
};

int main() {
    // Create a linked list using unique_ptr
    auto head = std::make_unique<Node>(1);
    head->next = std::make_unique<Node>(2);
    head->next->next = std::make_unique<Node>(3);

    // Traverse
    for (auto* curr = head.get(); curr; curr = curr->next.get())
        std::cout << curr->val << " ";
    std::cout << "\n";  // Output: 1 2 3

    // Automatic cleanup: entire list freed when head goes out of scope
    return 0;
}
```

**Key operations:**

```cpp
auto p = std::make_unique<int>(42);    // Create
int* raw = p.get();                     // Get raw pointer (no ownership transfer)
auto p2 = std::move(p);                // Transfer ownership (p becomes nullptr)
p2.reset();                             // Delete and set to nullptr
int* leaked = p2.release();             // Release ownership (caller must delete!)
```

### `std::shared_ptr` — Shared Ownership

| Property | Value |
|---|---|
| Ownership | Multiple owners |
| Overhead | Reference count (control block) |
| Copyable | Yes (increments ref count) |
| Use case | Shared ownership across components |

```cpp
#include <memory>
#include <iostream>

int main() {
    auto sp1 = std::make_shared<int>(42);
    std::cout << "Count: " << sp1.use_count() << "\n";  // 1

    {
        auto sp2 = sp1;  // Copy: ref count = 2
        std::cout << "Count: " << sp1.use_count() << "\n";  // 2
    } // sp2 destroyed: ref count = 1

    std::cout << "Count: " << sp1.use_count() << "\n";  // 1
    // sp1 destroyed: ref count = 0, memory freed
    return 0;
}
```

### `std::weak_ptr` — Non-Owning Observer

| Property | Value |
|---|---|
| Ownership | None |
| Overhead | Same as shared_ptr |
| Use case | Break reference cycles, cache |
| Key method | `lock()` returns shared_ptr or nullptr |

```cpp
#include <memory>
#include <iostream>

struct Node {
    int val;
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;  // Weak to break cycle
    explicit Node(int v) : val(v) {}
};

int main() {
    auto a = std::make_shared<Node>(1);
    auto b = std::make_shared<Node>(2);
    a->next = b;
    b->prev = a;  // Weak reference: no cycle

    if (auto p = b->prev.lock())
        std::cout << "Prev value: " << p->val << "\n";  // 1

    return 0;
}
```

---

## 126.4 Step-by-Step Walkthrough: Preventing Cycles

Consider a graph with bidirectional edges:

```cpp
// WRONG: creates reference cycle, memory never freed
struct BadNode {
    std::shared_ptr<BadNode> left, right, parent;  // Cycle!
};

// CORRECT: parent is weak
struct GoodNode {
    std::shared_ptr<GoodNode> left, right;
    std::weak_ptr<GoodNode> parent;  // Breaks cycle
};
```

**Dry run of reference counting:**

```
1. Create node A: A.use_count = 1
2. Create node B: B.use_count = 1
3. A->right = B:   B.use_count = 2
4. B->left = A (weak): A.use_count = 1 (not incremented)
5. Destroy A: A.use_count = 0, A freed
   B->left.lock() returns nullptr
6. Destroy B: B.use_count = 0, B freed
```

---

## 126.5 Custom Deleters

Smart pointers can wrap any resource, not just memory:

```cpp
#include <memory>
#include <cstdio>

// File with custom deleter
auto fileDeleter = [](FILE* f) { if (f) fclose(f); };
std::unique_ptr<FILE, decltype(fileDeleter)> fp(fopen("test.txt", "w"), fileDeleter);

// shared_ptr with array
auto arr = std::shared_ptr<int[]>(new int[100]);

// Lambda deleter
auto cleanup = [](int* p) {
    std::cout << "Deleting " << *p << "\n";
    delete p;
};
std::shared_ptr<int> sp(new int(42), cleanup);
```

---

## 126.6 When to Use Which

| Scenario | Smart Pointer |
|---|---|
| Single owner, default | `unique_ptr` |
| Multiple owners needed | `shared_ptr` |
| Observer (no ownership) | `weak_ptr` or raw `T*` |
| Factory function | Return `unique_ptr` |
| Graph with cycles | `shared_ptr` + `weak_ptr` |
| Pimpl idiom | `unique_ptr` |
| Callback ownership | `shared_ptr` |

---

## 126.7 Complexity Analysis

| Operation | unique_ptr | shared_ptr | weak_ptr |
|---|---|---|---|
| Create | O(1) | O(1) | — |
| Copy | — | O(1) | O(1) |
| Move | O(1) | O(1) | O(1) |
| Dereference | O(1) | O(1) | — |
| Destroy | O(1) | O(1) | O(1) |
| Memory overhead | 0 bytes | 16-32 bytes | 16-32 bytes |

---

## 126.8 Python Equivalent: Context Managers

Python uses `with` statements for RAII-like behavior:

```python
class FileManager:
    """RAII-style file handler in Python."""
    def __init__(self, filename, mode='r'):
        self.filename = filename
        self.mode = mode
        self.file = None

    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        return False  # Don't suppress exceptions

# Usage
with FileManager('/tmp/test.txt', 'w') as f:
    f.write("Hello, RAII!\n")
# File automatically closed

# Python's built-in support:
with open('/tmp/test.txt', 'r') as f:
    data = f.read()
```

---

## 126.9 Java Equivalent: Try-with-Resources

```java
import java.io.*;

public class RAIIExample {
    // AutoCloseable interface is Java's RAII
    static class DatabaseConnection implements AutoCloseable {
        private String name;

        public DatabaseConnection(String name) throws Exception {
            this.name = name;
            System.out.println("Opening " + name);
        }

        public void query(String sql) {
            System.out.println("Executing: " + sql);
        }

        @Override
        public void close() {
            System.out.println("Closing " + name);
        }
    }

    public static void main(String[] args) throws Exception {
        // Try-with-resources: auto-closes at end of block
        try (DatabaseConnection db = new DatabaseConnection("mydb")) {
            db.query("SELECT * FROM users");
        } // close() called automatically, even on exception
    }
}
```

---

## 126.10 Common Pitfalls

### Pitfall 1: Raw `new`/`delete` alongside smart pointers

```cpp
// BAD
std::shared_ptr<int> sp(new int(42));  // Two allocations

// GOOD
auto sp = std::make_shared<int>(42);   // One allocation (more efficient)
```

### Pitfall 2: Returning `unique_ptr` from function, then sharing

```cpp
// OK: transfer to shared if needed
auto up = std::make_unique<int>(42);
std::shared_ptr<int> sp = std::move(up);  // Convert unique to shared

// BAD: can't go from shared to unique
```

### Pitfall 3: `shared_ptr` cycle

```cpp
// Use weak_ptr for back-references (see 126.4)
```

### Pitfall 4: Dangling raw pointer from smart pointer

```cpp
auto sp = std::make_shared<int>(42);
int* raw = sp.get();  // Don't use raw after sp is destroyed!
sp.reset();
// *raw = 10;  // UNDEFINED BEHAVIOR
```

---

## 126.11 Exercises

1. **Implement `unique_ptr`**: Write a simplified version with template, move semantics, and destructor.
2. **Reference counter**: Implement a `shared_ptr` with an explicit reference count.
3. **Thread-safe shared_ptr**: Identify which operations on `shared_ptr` are thread-safe.
4. **File lock RAII**: Create an RAII class that acquires a file lock (flock) in the constructor and releases it in the destructor.
5. **Circular linked list**: Create a doubly-linked list using `shared_ptr` for `next` and `weak_ptr` for `prev`. Verify no memory leaks.

---

## 126.12 Interview Questions

1. **What is RAII and why is it important?**
   *Answer*: RAII binds resource lifetime to object scope. Constructor acquires, destructor releases. Guarantees cleanup even with exceptions, eliminating resource leaks.

2. **Difference between `unique_ptr` and `shared_ptr`?**
   *Answer*: `unique_ptr` has exclusive ownership with zero overhead; `shared_ptr` has shared ownership via reference counting with ~16-32 byte overhead. Default to `unique_ptr`.

3. **When would you use `weak_ptr`?**
   *Answer*: To break reference cycles in `shared_ptr` graphs, for caching (check if object still exists), and as an observer that doesn't extend lifetime.

4. **Is `shared_ptr` thread-safe?**
   *Answer*: The reference count is thread-safe (atomic). The managed object is NOT thread-safe—concurrent reads/writes need separate synchronization.

5. **How do you implement RAII in languages without destructors?**
   *Answer*: Use `with`/`using` statements (Python/C#), `try-with-resources` (Java), or `defer` (Go). These are scoped but require explicit annotation.

---

## 126.13 Cross-References

- **Chapter 2**: Memory management fundamentals
- **Chapter 5**: Linked lists using smart pointers
- **Chapter 32**: Thread safety and mutexes
- **Chapter 45**: Move semantics and rvalue references
- **Chapter 78**: Design patterns (Factory with `unique_ptr`)
- **Chapter 145**: Lock-free data structures

---

## Summary

| Idiom | Purpose | Overhead |
|---|---|---|
| RAII | Automatic resource management | Zero |
| `unique_ptr` | Exclusive ownership | Zero |
| `shared_ptr` | Shared ownership, ref counted | ~16-32 bytes |
| `weak_ptr` | Non-owning observer, breaks cycles | ~16-32 bytes |
| Custom deleters | Any resource cleanup | Varies |
