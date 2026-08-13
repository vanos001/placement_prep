# Memory Model

> Understanding how your program uses memory is the difference between code that works and code that works correctly.

## 1. Stack vs Heap (Revisited)

The stack and heap are the two primary memory regions used by programs.

### Stack Memory

```
┌─────────────────────┐
│   Stack Frame: main │
│   local_x = 5       │
│   local_y = 10      │
├─────────────────────┤
│   Stack Frame: foo  │
│   local_a = "hello" │
│   local_b = 3.14    │
├─────────────────────┤
│   Stack Frame: bar  │
│   local_arr[100]    │
└─────────────────────┘
   ↑ Stack Pointer
```

| Property | Stack | Heap |
|----------|-------|------|
| Speed | Very fast (pointer move) | Slower (allocation/deallocation) |
| Size | Limited (1-8 MB typical) | Large (limited by RAM) |
| Management | Automatic | Manual or GC |
| Fragmentation | None | Can fragment |
| Thread safety | Per-thread (no sharing) | Shared (needs synchronization) |
| Use case | Local variables, function frames | Dynamic/large data |

### When to Use Each

```c
// Stack: fixed-size, known at compile time
int arr[100];                    // stack
struct Point p = {1, 2};         // stack

// Heap: dynamic size, must outlive scope, large
int *arr = malloc(n * sizeof(int));  // heap
char *str = strdup("hello");        // heap
```

```java
// Java: primitives on stack, objects on heap
int x = 5;               // stack
String s = "hello";      // reference on stack, object in heap
int[] arr = new int[100]; // reference on stack, array in heap
```

## 2. Pointers

A **pointer** is a variable that stores a memory address.

### C/C++ Pointers

```c
int x = 42;
int *p = &x;    // p stores the address of x
printf("%d", *p); // 42 — dereference to get the value

*p = 100;        // changes x to 100

// Pointer arithmetic
int arr[] = {10, 20, 30};
int *p = arr;     // points to arr[0]
p++;              // now points to arr[1]
*(p + 1)          // arr[2] = 30
```

### Pointer Operations

| Operation | C Syntax | Meaning |
|-----------|----------|---------|
| Address-of | `&x` | Get address of x |
| Dereference | `*p` | Get value at address p |
| Member access | `p->field` | Access field through pointer |
| Array subscript | `p[i]` | Same as `*(p + i)` |

### Null Pointers

```c
int *p = NULL;  // points to nothing
// *p;          // segmentation fault!

// Safe pattern
if (p != NULL) {
    printf("%d", *p);
}
```

```cpp
// C++11: prefer nullptr over NULL
int *p = nullptr;
```

## 3. References

A **reference** is an alias for an existing variable. Unlike pointers, references cannot be null and cannot be reassigned.

### C++ References

```cpp
int x = 42;
int &ref = x;   // ref is an alias for x
ref = 100;      // x is now 100

// References must be initialized
// int &bad;    // compile error!

// References can't be rebound
int y = 200;
ref = y;        // this ASSIGNS y's value to x, doesn't rebind ref
// x is now 200, ref still refers to x
```

### Pointers vs References

| Feature | Pointer | Reference |
|---------|---------|-----------|
| Can be null | Yes | No |
| Can be reassigned | Yes | No |
| Must be initialized | No (dangerous) | Yes |
| Arithmetic | Yes | No |
| Indirection level | Explicit (`*p`) | Implicit |
| Use case | Dynamic data, optional | Aliasing, function params |

## 4. Smart Pointers

Smart pointers automatically manage memory, preventing leaks and dangling pointers.

### C++ Smart Pointers

```cpp
#include <memory>

// unique_ptr: single ownership, can't be copied
std::unique_ptr<int> p1 = std::make_unique<int>(42);
// auto p2 = p1;  // compile error!
auto p2 = std::move(p1);  // transfer ownership
// p1 is now nullptr

// shared_ptr: shared ownership, reference counted
std::shared_ptr<int> sp1 = std::make_shared<int>(42);
auto sp2 = sp1;  // both point to same object, refcount = 2
// Object freed when last shared_ptr is destroyed

// weak_ptr: non-owning reference to shared_ptr's object
std::weak_ptr<int> wp = sp1;
if (auto locked = wp.lock()) {
    // object still alive, use locked
}
```

### Reference Counting

```
shared_ptr sp1 ──→ ┌──────────┐
                   │ value: 42 │
shared_ptr sp2 ──→ │ refcount: 2│
                   └──────────┘

sp1 destroyed → refcount: 1
sp2 destroyed → refcount: 0 → object freed
```

### Smart Pointer Comparison

| Type | Ownership | Copyable | Use Case |
|------|-----------|----------|----------|
| `unique_ptr` | Single | No (move only) | Exclusive ownership |
| `shared_ptr` | Shared | Yes | Multiple owners |
| `weak_ptr` | Non-owning | Yes | Break cycles, observe |

### Rust Ownership (No Pointers Needed)

```rust
// Rust's ownership system replaces smart pointers
let s1 = String::from("hello");
let s2 = s1;  // s1 is moved, s2 owns the string
// println!("{}", s1);  // compile error!

let s3 = s2.clone();  // explicit deep copy
// Both s2 and s3 are valid

// Borrowing (non-owning reference)
fn print_str(s: &String) {
    println!("{}", s);  // borrows, doesn't take ownership
}
```

## 5. Garbage Collection

**Garbage collection (GC)** automatically reclaims memory that is no longer referenced.

### How GC Works

#### Reference Counting

```python
# Python uses reference counting (plus cycle detection)
import sys

a = []
print(sys.getrefcount(a))  # 2 (a + getrefcount's parameter)

b = a  # refcount: 3
del b  # refcount: 2

# When refcount reaches 0, memory is freed immediately
```

**Problem**: Circular references aren't collected.

```python
# Circular reference
a = []
b = [a]
a.append(b)
# refcount of both a and b is 2, but nothing else references them
# Python's cycle detector handles this
```

#### Mark and Sweep

```
1. Start from "roots" (stack variables, globals)
2. Mark all reachable objects
3. Sweep (free) all unmarked objects

Before GC:
┌───┐   ┌───┐   ┌───┐   ┌───┐
│ A │──→│ B │──→│ C │   │ D │  ← unreachable
└───┘   └───┘   └───┘   └───┘
  ↑
roots

After GC:
┌───┐   ┌───┐   ┌───┐
│ A │──→│ B │──→│ C │
└───┘   └───┘   └───┘
D is freed
```

#### Generational GC

Most modern GCs are **generational**:

```
┌─────────────────────────────────────────┐
│               Old Generation            │  Long-lived objects
│  (collected infrequently)               │
├─────────────────────────────────────────┤
│           Young Generation              │  Short-lived objects
│  ┌─────────┬───────────┬─────────────┐  │
│  │  Eden   │  Survivor │  Survivor   │  │
│  │  (new)  │    (S0)   │    (S1)     │  │
│  └─────────┴───────────┴─────────────┘  │
│  (collected frequently)                 │
└─────────────────────────────────────────┘
```

Based on the **generational hypothesis**: most objects die young.

### GC Languages

| Language | GC Type | Notes |
|----------|---------|-------|
| Java | Generational (G1, ZGC, Shenandoah) | Low-latency options available |
| Python | Reference counting + cycle detector | `gc` module for manual control |
| Go | Concurrent, tri-color mark-sweep | Very low latency |
| JavaScript/V8 | Generational (Orinoco) | Incremental, concurrent |
| C# | Generational | Similar to Java |
| Rust | None (ownership system) | Compile-time memory management |
| C/C++ | None (manual) | `malloc`/`free`, `new`/`delete` |

## 6. Manual Memory Management

### C: malloc/free

```c
// Allocate
int *arr = malloc(10 * sizeof(int));
if (arr == NULL) {
    // handle allocation failure
}

// Use
for (int i = 0; i < 10; i++) {
    arr[i] = i * i;
}

// Free
free(arr);
arr = NULL;  // good practice: prevent dangling pointer

// Common mistakes:
// 1. Memory leak: forget to free
// 2. Double free: free twice
// 3. Use after free: use pointer after freeing
// 4. Wrong free: free with wrong function
```

### C++: new/delete

```cpp
// Single object
int *p = new int(42);
delete p;

// Array
int *arr = new int[100];
delete[] arr;  // note: delete[] for arrays!

// Better: use smart pointers
auto p = std::make_unique<int>(42);
auto arr = std::make_unique<int[]>(100);
// No manual delete needed
```

## 7. Common Memory Bugs

### Memory Leak

```c
void leak() {
    int *p = malloc(100);
    // forgot to free(p)
}  // p goes out of scope, memory is leaked

void conditional_leak(int condition) {
    int *p = malloc(100);
    if (condition) {
        return;  // leaked!
    }
    free(p);
}
```

### Dangling Pointer

```c
int *dangling() {
    int x = 42;
    return &x;  // x dies when function returns!
}

int *p = dangling();
printf("%d", *p);  // undefined behavior!
```

### Buffer Overflow

```c
char buf[10];
strcpy(buf, "This string is way too long!");  // overflow!
// Writes past the end of buf, corrupting stack
```

### Double Free

```c
int *p = malloc(100);
free(p);
free(p);  // double free — undefined behavior!
```

### Use After Free

```c
int *p = malloc(100);
free(p);
*p = 42;  // use after free — undefined behavior!
```

### How Languages Prevent These

| Bug | C/C++ | Java/Python/JS | Rust |
|-----|-------|----------------|------|
| Memory leak | Manual prevention | GC prevents | Ownership prevents |
| Dangling pointer | Manual prevention | GC prevents | Borrow checker prevents |
| Buffer overflow | Manual prevention | Bounds checking | Bounds checking |
| Double free | Manual prevention | GC prevents | Ownership prevents |
| Use after free | Manual prevention | GC prevents | Borrow checker prevents |

## 8. Memory Alignment and Layout

### Struct Memory Layout

```c
// Unoptimized: wastes memory due to alignment
struct Bad {
    char a;    // 1 byte + 3 padding
    int b;     // 4 bytes
    char c;    // 1 byte + 7 padding
    double d;  // 8 bytes
};
// sizeof(Bad) = 24 bytes

// Optimized: order fields by size
struct Good {
    double d;  // 8 bytes
    int b;     // 4 bytes
    char a;    // 1 byte
    char c;    // 1 byte + 2 padding
};
// sizeof(Good) = 16 bytes
```

### Alignment Rules

- Data must be aligned to addresses that are multiples of its size
- `int` (4 bytes) must be at addresses divisible by 4
- `double` (8 bytes) must be at addresses divisible by 8
- Padding is added to satisfy alignment

## Interview Questions

1. **What's the difference between stack and heap memory?**
   Stack: fast, automatic, limited size, per-thread. Heap: slower, manually managed (or GC'd), large, shared. Local variables go on stack; dynamic data goes on heap.

2. **What is a dangling pointer? How do you prevent it?**
   A pointer to memory that has been freed or deallocated. Prevention: set pointers to NULL after freeing, use smart pointers (C++), use Rust's ownership system, or use GC.

3. **Explain smart pointers in C++.**
   `unique_ptr`: exclusive ownership, can't be copied. `shared_ptr`: shared ownership with reference counting. `weak_ptr`: non-owning reference to break cycles.

4. **How does garbage collection work?**
   Most use mark-and-sweep: start from roots, mark reachable objects, free unmarked ones. Generational GC adds the insight that most objects die young, so collect young generation more frequently.

5. **What is memory fragmentation?**
   When free memory is split into many small non-contiguous blocks. External fragmentation: total free space is enough but not contiguous. Internal fragmentation: allocated block is larger than needed.

6. **Why does Rust not need a garbage collector?**
   Rust's ownership system tracks who owns each piece of memory at compile time. When the owner goes out of scope, memory is freed. The borrow checker ensures no dangling references exist.

7. **What is RAII?**
   Resource Acquisition Is Initialization. Tie resource lifetime to object lifetime. Resources are acquired in constructors and released in destructors, ensuring cleanup even during exceptions.

8. **Explain the difference between `delete` and `delete[]` in C++.**
   `delete` frees a single object. `delete[]` frees an array. Using the wrong one is undefined behavior. Better yet: use smart pointers to avoid this entirely.
