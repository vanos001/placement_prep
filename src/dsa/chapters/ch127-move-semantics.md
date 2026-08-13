# Chapter 127: Move Semantics Deep Dive

## Prerequisites
- C++ basics, RAII, smart pointers

## Interview Frequency: ★★★★

Move semantics enable efficient resource transfer. **Google**, **Meta**, **Amazon** test this.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| std::move | ★★★★ | Medium | Cast to rvalue ref |
| Rvalue references | ★★★ | Medium | T&& |
| Perfect forwarding | ★★ | Hard | std::forward |
| Move constructors | ★★★★ | Medium | Rule of 5 |

---

## Definition

Before diving into move semantics, we must understand the C++ value category taxonomy. Every expression in C++ has both a **type** and a **value category**.

### Value Categories (C++11 and later)

```
              expression
             /          \
        glvalue        rvalue
       /      \        /    \
   lvalue    xvalue  xvalue  prvalue
```

| Category | Name | Key Property | Example |
|---|---|---|---|
| **lvalue** | Left value | Has identity (addressable), cannot be moved from implicitly | `int x = 5;` — `x` is an lvalue |
| **prvalue** | Pure rvalue | No identity, temporary, can be moved from | `42`, `std::string("hi")`, `x + y` |
| **xvalue** | Expiring value | Has identity, but is about to be moved from | `std::move(x)`, a function returning `T&&` |
| **glvalue** | Generalized lvalue | Either lvalue or xvalue (has identity) | Any lvalue or xvalue |
| **rvalue** | Right value | Either prvalue or xvalue (can be moved from) | Any prvalue or xvalue |

**Formal definitions:**

- **lvalue**: An expression that refers to a persistent object or function. It has an identifiable memory address. You can take its address with `&`.
- **prvalue**: A temporary value that does not persist beyond the expression that creates it. `42`, `true`, `x + 1`, `std::string("temp")`.
- **xvalue**: An expression that designates an object whose resources can be reused (it is "expiring"). Created by `std::move()` or by calling a function that returns an rvalue reference.
- **glvalue**: The union of lvalue and xvalue — any expression with identity.
- **rvalue**: The union of prvalue and xvalue — any expression that can be moved from.

```cpp
int x = 10;
int& lref = x;           // lref binds to lvalue
int&& rref = 20;          // rref binds to prvalue (rvalue ref)
int&& rref2 = std::move(x); // rref2 binds to xvalue

// lvalue: x, lref, rref (named rvalue refs are lvalues!)
// prvalue: 20, x + 1, std::string("temp")
// xvalue: std::move(x), static_cast<int&&>(x)
```

**Critical insight:** A named rvalue reference (`int&& rref = 20;`) is itself an **lvalue** — it has a name and an address. To move from it, you need `std::move(rref)`.

---

## Motivation

### Why Do Move Semantics Exist?

Before C++11, every time you passed a temporary object to a function or assigned it, the only option was **copying** — allocating new memory and duplicating all the data. This was wasteful when the source was a temporary that was about to be destroyed anyway.

**The problem:**

```cpp
std::vector<int> createLargeVector() {
    std::vector<int> v(1000000, 42);
    return v;  // Without move: deep copy of 1 million ints!
}

std::vector<int> result = createLargeVector(); // Another copy!
```

Without move semantics, the above code would copy 4 million bytes twice — once for the return and once for the assignment — only to immediately destroy the originals.

**Three key motivations:**

1. **Performance**: Move avoids expensive deep copies for large objects (strings, vectors, buffers). A move is typically O(1) pointer transfer vs O(n) data duplication.

2. **Resource management**: Some resources cannot be copied — file handles, sockets, mutexes, unique pointers. Move semantics provide a way to transfer ownership without duplication.

3. **Container efficiency**: `std::vector` reallocation, `std::map` insertion, and `std::swap` all benefit enormously from move semantics. Without them, growing a vector by one element would copy all existing elements.

```cpp
// This is efficient because of move semantics:
std::vector<std::string> vec;
for (int i = 0; i < 100000; i++) {
    vec.push_back(std::string(1000, 'x')); // Move, not copy!
}
```

---

## Intuition

### The Moving Analogy

Think of **copying** like photocopying a book: you read every page, reproduce it, and now you have two identical books. It takes time proportional to the book's length.

Think of **moving** like handing someone a book: you give them the physical book, and now they have it and you don't. It takes constant time regardless of the book's length — you're just transferring a pointer (the location of the book on the shelf).

```
COPY (expensive):
  Source: [A, B, C, D, E]  ──copy each element──>  Dest: [A, B, C, D, E]
  Source still has: [A, B, C, D, E]

MOVE (cheap):
  Source: [A, B, C, D, E]  ──transfer pointer──>   Dest: [A, B, C, D, E]
  Source now has: [empty] (nullptr)
```

**Key mental model:** After a move, the source object is in a **valid but unspecified** state. It must be safe to destroy and safe to assign to, but you should not rely on its value.

**When to use each:**

| Situation | Operation | Why |
|---|---|---|
| Need to keep original | Copy | Move would leave original in unspecified state |
| Temporary / no longer needed | Move | Avoid expensive deep copy |
| Transferring ownership | Move | Copy is not possible or semantically wrong |
| `std::unique_ptr` | Must move | Cannot copy unique ownership |

---

## 127.1 Rvalue References

An rvalue reference `T&&` binds to temporary objects (rvalues). This enables "stealing" resources from temporaries.

```cpp
#include <iostream>
#include <cstring>
#include <utility>
#include <vector>

class MyString {
    char* data;
    size_t len;
    
public:
    // Constructor
    MyString(const char* s = "") : len(strlen(s)) {
        data = new char[len + 1];
        memcpy(data, s, len + 1);
        std::cout << "Constructed: \"" << data << "\"\n";
    }
    
    // Destructor
    ~MyString() {
        std::cout << "Destroyed: \"" << (data ? data : "null") << "\"\n";
        delete[] data;
    }
    
    // Copy constructor (deep copy)
    MyString(const MyString& other) : len(other.len) {
        data = new char[len + 1];
        memcpy(data, other.data, len + 1);
        std::cout << "Copied: \"" << data << "\"\n";
    }
    
    // Move constructor (steal resources)
    MyString(MyString&& other) noexcept : data(other.data), len(other.len) {
        other.data = nullptr;
        other.len = 0;
        std::cout << "Moved: \"" << data << "\"\n";
    }
    
    // Copy assignment
    MyString& operator=(const MyString& other) {
        if (this != &other) {
            delete[] data;
            len = other.len;
            data = new char[len + 1];
            memcpy(data, other.data, len + 1);
        }
        return *this;
    }
    
    // Move assignment
    MyString& operator=(MyString&& other) noexcept {
        if (this != &other) {
            delete[] data;
            data = other.data;
            len = other.len;
            other.data = nullptr;
            other.len = 0;
        }
        return *this;
    }
    
    void print() const {
        std::cout << "\"" << (data ? data : "") << "\" (len=" << len << ")\n";
    }
};

int main() {
    MyString s1("Hello");
    MyString s2 = s1;              // Copy
    MyString s3 = std::move(s1);   // Move
    MyString s4 = MyString("World"); // Move (temporary)
    
    s1.print(); // Empty (moved from)
    s2.print(); // Hello
    s3.print(); // Hello
    s4.print(); // World
    
    // Move in vector operations
    std::vector<MyString> vec;
    vec.push_back(MyString("A")); // Move
    vec.push_back(MyString("B")); // Move (if no reallocation)
    
    return 0;
}
```

---

## Step-by-Step Walkthrough

Let's trace through a move operation line by line using the `MyString` class.

```cpp
MyString s1("Hello");       // Step 1
MyString s3 = std::move(s1); // Step 2
s1.print();                  // Step 3
s3.print();                  // Step 4
```

### Step 1: `MyString s1("Hello")`

```
Memory layout after construction:
  s1.data ──→ ['H','e','l','l','o','\0']  (heap, 6 bytes)
  s1.len = 5
```

The constructor allocates 6 bytes on the heap, copies "Hello" into it, and stores the pointer and length in `s1`.

### Step 2: `MyString s3 = std::move(s1)`

`std::move(s1)` does **not** move anything — it simply casts `s1` to `MyString&&` (an rvalue reference). This tells the compiler: "treat `s1` as a temporary; it's safe to steal from."

The move constructor `MyString(MyString&& other)` is then invoked:

```
Move constructor body:
  s3.data = other.data;   // s3.data ← s1.data (pointer copy, O(1))
  s3.len  = other.len;    // s3.len  ← s1.len  (size_t copy, O(1))
  other.data = nullptr;   // s1.data ← nullptr  (steal ownership)
  other.len  = 0;         // s1.len  ← 0

Memory layout after move:
  s1.data ──→ nullptr
  s1.len = 0
  s3.data ──→ ['H','e','l','l','o','\0']  (same heap block!)
  s3.len = 5
```

**No new allocation. No data copy. Just pointer reassignment.**

### Step 3: `s1.print()`

Outputs `"" (len=0)` — the moved-from object is empty but valid. It can be destroyed safely.

### Step 4: `s3.print()`

Outputs `"Hello" (len=5)` — `s3` now owns the original data.

### Destruction (end of scope)

```
~s3: deletes ['H','e','l','l','o','\0']  — frees the heap memory
~s1: delete[] nullptr is a no-op          — safe, no crash
```

---

## Dry Run: Memory Layout Before and After Move

### Before Move

```
Stack                          Heap
┌──────────────┐
│     s1       │
│  data: ●──────────────→ ['H','e','l','l','o','\0']
│  len:  5     │              addr: 0x7f3a001000
└──────────────┘

┌──────────────┐
│     s3       │  (not yet constructed)
│  data: ???   │
│  len:  ???   │
└──────────────┘
```

### After `std::move(s1)` — During Move Constructor

```
Stack                          Heap
┌──────────────┐
│     s1       │
│  data: ●─┐   │           ┌──→ ['H','e','l','l','o','\0']
│  len:  5 │   │           │     addr: 0x7f3a001000
└──────────│───┘           │
           │               │
┌──────────│───┐           │
│     s3   │   │           │
│  data: ●─┘   │───────────┘
│  len:  5     │
└──────────────┘
```

### After Move Completes — Source Nulled

```
Stack                          Heap
┌──────────────┐
│     s1       │
│  data: nullptr│   (no heap allocation)
│  len:  0     │
└──────────────┘

┌──────────────┐
│     s3       │
│  data: ●──────────────→ ['H','e','l','l','o','\0']
│  len:  5     │              addr: 0x7f3a001000
└──────────────┘
```

**Key observation:** Only one heap allocation exists. Ownership transferred from `s1` to `s3`. The heap block was never copied — only the pointer was reassigned.

---

## 127.2 When Move Happens

| Expression | Type | Move? |
|---|---|---|
| `MyString s("hi")` | Named variable | No |
| `MyString s = MyString("hi")` | Temporary | Yes |
| `MyString s = std::move(other)` | Explicit move | Yes |
| `vec.push_back(s)` | Named variable | Copy |
| `vec.push_back(std::move(s))` | Explicit move | Yes |

---

## 127.3 Perfect Forwarding

`std::forward<T>(arg)` preserves the value category (lvalue/rvalue) of the argument.

```cpp
#include <iostream>
#include <utility>

template<typename T>
void wrapper(T&& arg) {
    // Forward preserves lvalue/rvalue nature
    std::cout << "Forwarded: ";
    // In real code: target(std::forward<T>(arg));
    std::cout << arg << "\n";
}

int main() {
    int x = 42;
    wrapper(x);           // T = int&, arg is lvalue
    wrapper(42);          // T = int, arg is rvalue
    wrapper(std::move(x)); // T = int, arg is rvalue
    return 0;
}
```

---

## 127.4 Move and Containers

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <chrono>

int main() {
    const int N = 1000000;
    
    // Copy vs Move benchmark
    auto start = std::chrono::high_resolution_clock::now();
    std::vector<std::string> vec1;
    for (int i = 0; i < N; i++) {
        std::string s = "hello world this is a test string";
        vec1.push_back(s); // Copy
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto copyTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    start = std::chrono::high_resolution_clock::now();
    std::vector<std::string> vec2;
    for (int i = 0; i < N; i++) {
        std::string s = "hello world this is a test string";
        vec2.push_back(std::move(s)); // Move
    }
    end = std::chrono::high_resolution_clock::now();
    auto moveTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    std::cout << "Copy: " << copyTime.count() << "ms\n";
    std::cout << "Move: " << moveTime.count() << "ms\n";
    
    return 0;
}
```

---

## Complexity Analysis: Move vs Copy

Understanding the performance difference between move and copy is critical for writing efficient C++.

### Time Complexity

| Operation | Copy | Move | Notes |
|---|---|---|---|
| `std::string` construction | O(n) | O(1) | n = string length |
| `std::vector` construction | O(n) | O(1) | n = number of elements |
| `std::vector` push_back (no realloc) | O(n) | O(1) | n = element size |
| `std::vector` reallocation | O(n) | O(1) per element | n = total elements |
| `std::map` node extraction | O(log n) | O(1) per node | node handle |
| `std::swap(a, b)` | O(n) | O(1) | n = object size |
| `std::unique_ptr` | N/A (non-copyable) | O(1) | Must move |

### Space Complexity

| Operation | Copy | Move |
|---|---|---|
| Temporary allocation | O(n) new allocation | O(0) — reuses source |
| Peak memory | 2× original | 1× original |

### Why `noexcept` Matters

Standard containers (like `std::vector`) check whether the move constructor is `noexcept`. If it is, the container uses move during reallocation. If not, it falls back to copy for **exception safety** — a move that throws mid-way could lose data.

```cpp
// GOOD: noexcept tells vector it's safe to move during reallocation
MyString(MyString&& other) noexcept : data(other.data), len(other.len) {
    other.data = nullptr;
    other.len = 0;
}

// BAD: Without noexcept, vector will COPY during reallocation
MyString(MyString&& other) : data(other.data), len(other.len) {
    // vector won't use this move — too risky
}
```

**Rule:** Always mark move constructors and move assignment operators `noexcept`.

---

## 127.5 Rule of Zero

If your class doesn't manage resources directly, don't define any special member functions. Let the compiler generate them.

```cpp
#include <iostream>
#include <string>
#include <vector>

// BAD: Unnecessary destructor
class Bad {
    std::string name;
    std::vector<int> data;
public:
    ~Bad() {} // Unnecessary! Compiler would do the same
};

// GOOD: Rule of Zero
class Good {
    std::string name;
    std::vector<int> data;
    // No destructor, copy/move constructors needed!
    // Compiler generates correct ones.
};

int main() {
    Good g1;
    Good g2 = g1; // Compiler-generated copy works fine
    Good g3 = std::move(g1); // Compiler-generated move works fine
    std::cout << "Rule of Zero: let the compiler handle it!\n";
    return 0;
}
```

---

## 127.6 Memory Alignment

Data should be aligned to its size for optimal access. Misaligned access can cause crashes or performance penalties.

```cpp
#include <iostream>
#include <cstddef>

struct BadLayout {
    char a;     // 1 byte + 7 padding
    double b;   // 8 bytes
    char c;     // 1 byte + 7 padding
}; // sizeof = 24 bytes

struct GoodLayout {
    double b;   // 8 bytes
    char a;     // 1 byte
    char c;     // 1 byte + 6 padding
}; // sizeof = 16 bytes

int main() {
    std::cout << "BadLayout size: " << sizeof(BadLayout) << "\n";  // 24
    std::cout << "GoodLayout size: " << sizeof(GoodLayout) << "\n"; // 16
    
    // alignof
    std::cout << "alignof(double): " << alignof(double) << "\n"; // 8
    std::cout << "alignof(int): " << alignof(int) << "\n";       // 4
    
    return 0;
}
```

---

## 127.7 Placement New

Construct an object at a pre-allocated memory location. Used in custom allocators and container implementations.

```cpp
#include <iostream>
#include <new> // for placement new
#include <memory>

int main() {
    // Pre-allocate memory
    alignas(int) char buffer[sizeof(int) * 5];
    
    // Construct ints in the buffer
    int* arr = reinterpret_cast<int*>(buffer);
    for (int i = 0; i < 5; i++) {
        new (&arr[i]) int(i * 10); // Placement new
    }
    
    for (int i = 0; i < 5; i++)
        std::cout << arr[i] << " ";
    std::cout << "\n";
    
    // Destruct (for non-trivial types, call destructor manually)
    // For int, nothing needed
    
    return 0;
}
```

---

## Python Equivalents

Python does **not** have move semantics. Every assignment in Python is a reference binding (like a shared pointer), and the garbage collector handles deallocation. However, Python has its own mechanisms for controlling copy behavior.

### `__copy__` and `__deepcopy__`

```python
import copy

class MyBuffer:
    def __init__(self, data: list[int]):
        self._data = data

    def __copy__(self):
        """Shallow copy: new MyBuffer, same underlying list reference."""
        print("Shallow copy called")
        return MyBuffer(self._data)

    def __deepcopy__(self, memo):
        """Deep copy: new MyBuffer with a new list."""
        print("Deep copy called")
        return MyBuffer(copy.deepcopy(self._data, memo))

    def __repr__(self):
        return f"MyBuffer({self._data})"

a = MyBuffer([1, 2, 3])
b = copy.copy(a)        # Calls __copy__ — shallow
c = copy.deepcopy(a)    # Calls __deepcopy__ — deep
print(a, b, c)
```

### Why Python Doesn't Need Move Semantics

| Aspect | C++ | Python |
|---|---|---|
| Assignment | Copies value (or invokes copy ctor) | Binds reference (like `shared_ptr`) |
| Ownership | Manual (or RAII) | Garbage collected |
| Temporary destruction | Deterministic (end of scope) | Reference-counted (GC) |
| Resource transfer | `std::move` | Not needed — references are cheap |
| Large data copy | Expensive without move | Reference binding is O(1) always |

In Python, `a = b` never copies data — it just makes `a` point to the same object. The expensive copy only happens when you explicitly call `copy()` or `deepcopy()`. This means Python avoids the accidental-copy problem that motivated move semantics in C++.

**However**, Python's approach has trade-offs:
- Mutation through shared references can cause subtle bugs
- You must explicitly copy when you need independence
- No compile-time ownership tracking (unlike `std::unique_ptr`)

---

## Java Comparison

Java, like Python, has **no move semantics**. Java uses references for all objects and relies on garbage collection.

### How Java Handles Similar Concerns

```java
// Java: All object variables are references
String s1 = new String("Hello");
String s2 = s1;  // s2 and s1 point to the SAME object (no copy)
String s3 = s1;  // s3 also points to the same object

// To "copy" in Java, you must be explicit:
// - Cloneable interface (clone())
// - Copy constructor
// - Factory method
```

| Concern | C++ Approach | Java Approach |
|---|---|---|
| Avoid accidental copies | Move semantics | References are already O(1) |
| Transfer ownership | `std::move` + `unique_ptr` | GC handles lifecycle |
| Deep vs shallow copy | Copy ctor / move ctor | `clone()` / copy constructor |
| Temporary optimization | Rvalue references | JIT compiler optimizations |
| Resource management | RAII + move | try-with-resources (no transfer) |
| Non-copyable types | Delete copy ctor | No language support |

**Key difference:** Java's `String` is immutable, so sharing references is always safe. In C++, `std::string` is mutable, so sharing without copying leads to aliasing bugs — this is why C++ copies by default and needs move to avoid the cost.

### When Java's Approach Falls Short

Java cannot express ownership transfer at the type level. There's no way to say "this method consumes the parameter" in the type system. This is why Java APIs often have confusing semantics around who owns a passed-in `InputStream` or `ByteBuffer`.

```cpp
// C++: Ownership transfer is explicit in the type
void process(std::unique_ptr<Widget> w);  // Caller gives up ownership

// Java: No way to express this — documentation only
void process(Widget w);  // Does this method own w? Who knows?
```

---

## Summary

| Concept | Purpose | When to Use |
|---|---|---|
| `T&&` (rvalue ref) | Bind to temporaries | Move constructor/assignment |
| `std::move` | Cast to rvalue | When you won't use variable again |
| `std::forward` | Preserve value category | Perfect forwarding in templates |
| Move constructor | Steal resources | Rule of 5 |
| `noexcept` | Enable container optimization | All move operations |

---

## Exercises

### Exercise 1: Identify Value Categories

Classify each expression as lvalue, prvalue, or xvalue:

```cpp
int x = 10;
int& ref = x;
```

1. `x`
2. `ref`
3. `10`
4. `x + 1`
5. `std::move(x)`
6. `std::move(ref)`
7. `int&& rref = 42;` — what is `rref`?

<details>
<summary>Solution</summary>

1. `x` — **lvalue** (named variable with address)
2. `ref` — **lvalue** (reference to lvalue)
3. `10` — **prvalue** (literal, temporary)
4. `x + 1` — **prvalue** (temporary result)
5. `std::move(x)` — **xvalue** (cast to rvalue reference, has identity)
6. `std::move(ref)` — **xvalue** (same as above)
7. `rref` — **lvalue**! Named rvalue references are lvalues. You need `std::move(rref)` to get an xvalue.
</details>

### Exercise 2: Move Constructor Behavior

Given this class, what is the output?

```cpp
class Box {
    int* data;
public:
    Box(int v) : data(new int(v)) { cout << "Ctor " << *data; }
    Box(const Box& o) : data(new int(*o.data)) { cout << "Copy " << *data; }
    Box(Box&& o) noexcept : data(o.data) { o.data = nullptr; cout << "Move "; }
    ~Box() { if(data) { cout << "Dtor " << *data; delete data; } else cout << "Dtor null"; }
};

Box a(1);
Box b = a;
Box c = std::move(a);
```

<details>
<summary>Solution</summary>

```
Ctor 1        → Box a(1)
Copy 1        → Box b = a (copy constructor, a still owns its data)
Move          → Box c = std::move(a) (move constructor, a.data becomes nullptr)
Dtor null     → ~a (data is nullptr, nothing to delete)
Dtor 1        → ~c (owns the original data)
Dtor 1        → ~b (owns its own copy)
```

Note: destruction order is reverse of construction (c, then b, then a — but a's data was moved to c, so a prints "Dtor null").
</details>

### Exercise 3: Fix the Bug

This move constructor has a bug. Find and fix it.

```cpp
class Buffer {
    char* data;
    size_t size;
public:
    Buffer(Buffer&& other) : data(other.data), size(other.size) {
        // BUG: forgot to null out other!
    }
};
```

<details>
<summary>Solution</summary>

The source object `other` still points to the same memory. When `other` is destroyed, it will `delete[]` the data, leaving `this` with a dangling pointer.

```cpp
Buffer(Buffer&& other) noexcept : data(other.data), size(other.size) {
    other.data = nullptr;  // Transfer ownership
    other.size = 0;
}
```

Don't forget `noexcept`!
</details>

### Exercise 4: Move vs Copy in Vector

Predict the output and explain why:

```cpp
std::vector<std::string> vec;
std::string s = "hello";
vec.push_back(s);           // (A)
vec.push_back(std::move(s)); // (B)
std::cout << s;              // (C)
```

<details>
<summary>Solution</summary>

- **(A)**: `s` is an lvalue → copy constructor called. `s` still holds "hello".
- **(B)**: `std::move(s)` is an xvalue → move constructor called. `s` is now in a valid but unspecified state (likely empty string).
- **(C)**: Prints whatever `s` contains after the move. In most implementations, this prints an empty string. **Do not rely on the value of moved-from objects.**
</details>

### Exercise 5: Implement Swap Using Move

Implement a generic `swap` function using move semantics.

```cpp
template<typename T>
void my_swap(T& a, T& b) {
    // Your code here
}
```

<details>
<summary>Solution</summary>

```cpp
template<typename T>
void my_swap(T& a, T& b) {
    T temp = std::move(a);    // a → temp (move)
    a = std::move(b);         // b → a (move)
    b = std::move(temp);      // temp → b (move)
}
```

Three moves, zero copies. This is exactly how `std::swap` works in the standard library. For types with efficient move (like `std::vector`), this is O(1) per move instead of O(n) per copy.
</details>

### Exercise 6: Perfect Forwarding Constructor

Write a `Wrapper` class template that perfectly forwards arguments to the wrapped type's constructor.

```cpp
template<typename T>
class Wrapper {
    T value;
public:
    // Constructor that forwards args to T's constructor
    // Your code here
};
```

<details>
<summary>Solution</summary>

```cpp
template<typename T>
class Wrapper {
    T value;
public:
    template<typename... Args>
    Wrapper(Args&&... args) : value(std::forward<Args>(args)...) {}
};
```

This uses a **variadic template** with **universal references** (`Args&&...`) and `std::forward` to preserve value categories. It works with any constructor of `T` — copy, move, or any other.
</details>

---

## Interview Questions

### Q1: What is the difference between `std::move` and actually moving?

**Answer:** `std::move` does **not** move anything. It is simply a cast — `static_cast<std::remove_reference_t<T>&&>(arg)`. It casts its argument to an rvalue reference, which *enables* a move constructor or move assignment operator to be called. The actual moving happens inside those operators (transferring pointers, nulling out the source).

### Q2: Why must move constructors be `noexcept`?

**Answer:** Standard containers like `std::vector` use the strong exception guarantee during reallocation. If the move constructor is `noexcept`, the container will use it to transfer elements to the new buffer. If it might throw, the container falls back to copy constructors to ensure that if an exception occurs, the original data is still intact. This means a throwing move constructor can cause `std::vector` to silently use expensive copies instead.

### Q3: Can you move from a `const` object?

**Answer:** No — not in a useful way. `std::move(const_obj)` produces a `const T&&`, which cannot bind to a `T&&` parameter (non-const rvalue reference). It will fall back to the copy constructor. Moving from a `const` object would violate the contract of `const`, since move modifies the source (nulling pointers, etc.).

### Q4: What happens if you use a moved-from object?

**Answer:** A moved-from object is in a **valid but unspecified** state. You can:
- Destroy it (destructor runs safely)
- Assign to it (give it a new value)
- Call methods with no preconditions (like `size()` on a vector)

You **cannot** assume any specific value. For example, a moved-from `std::string` might be empty, or it might still contain the old data — it depends on the implementation.

### Q5: Explain the Rule of Five.

**Answer:** If you define **any one** of these five special member functions, you should define **all five**:
1. Destructor
2. Copy constructor
3. Copy assignment operator
4. Move constructor
5. Move assignment operator

The reason: if you need custom logic for one (e.g., a destructor to free memory), the compiler-generated defaults for the others are likely wrong (e.g., it would generate a copy constructor that does shallow copy, leading to double-free).

### Q6: What is the difference between `T&&` in a function template vs a regular function?

**Answer:** In a **function template**, `T&&` is a **forwarding reference** (universal reference) — it can bind to both lvalues and rvalues. `T` is deduced as `U&` for lvalues and `U` for rvalues. In a **regular function** (non-template), `T&&` is simply an rvalue reference that can only bind to rvalues.

```cpp
template<typename T>
void f(T&& x);        // Forwarding reference

void g(std::string&& x); // Rvalue reference only
```

### Q7: How does `std::vector` use move semantics during reallocation?

**Answer:** When `std::vector` needs to grow beyond its capacity, it allocates a new buffer and transfers elements from the old buffer to the new one. If the element type's move constructor is `noexcept`, the vector uses move to transfer elements (O(1) per element). If the move constructor might throw, the vector uses copy instead (O(n) per element) to maintain the strong exception guarantee. This is why `noexcept` on move constructors is critical for performance.

---

## See Also

- **Chapter on RAII**: Move semantics are built on top of RAII (Resource Acquisition Is Initialization).
- **Chapter on Smart Pointers**: `std::unique_ptr` is the quintessential move-only type. `std::shared_ptr` uses reference counting instead.
- **Chapter on Templates**: Perfect forwarding (`std::forward`) is a template metaprogramming technique.
- **Chapter on STL Containers**: Container operations like `push_back`, `emplace_back`, and `swap` are heavily influenced by move semantics.
- **Chapter on Copy Elision / RVO**: C++17 mandates copy elision in many cases (guaranteed NRVO), which sometimes makes `std::move` counterproductive.
- **`std::exchange`**: Useful utility for implementing move operations — returns old value and assigns new one.
- **`std::move_if_noexcept`**: Conditionally casts to rvalue only if the move constructor is `noexcept`, used internally by containers.
