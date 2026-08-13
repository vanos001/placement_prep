# Chapter 128: STL Internals and Container Deep Dives

## Prerequisites
- C++ STL basics (vector, map, set, unordered_map)
- Basic data structures (arrays, linked lists, trees, hash tables)

## Interview Frequency: ★★★
## Google, Amazon, Microsoft — core C++ knowledge

---

## 128.1 Why Study STL Internals?

Understanding STL internals helps you:
1. **Choose the right container** for your use case
2. **Avoid performance pitfalls** (e.g., iterator invalidation, cache misses)
3. **Answer interview questions** about data structure trade-offs
4. **Write faster code** by understanding memory layout and allocation

**Interview Reality:** Google, Amazon, and Microsoft frequently ask:
- "How does `std::vector` grow?"
- "What's the difference between `map` and `unordered_map`?"
- "Why is `reserve()` important?"
- "How does `std::sort` work internally?"

---

## 128.2 std::vector Internals

### How std::vector Works

A `vector` is a **dynamic array** that manages three pointers:
- `begin_`: pointer to first element
- `end_`: pointer to one past last element
- `cap_`: pointer to end of allocated storage

```
Memory layout:
[  data  ][  unused capacity  ]
^begin_   ^end_                ^cap_
size = end_ - begin_
capacity = cap_ - begin_
```

### Growth Strategy

When `push_back` is called and `size() == capacity()`:
1. Allocate new storage: typically `capacity * 2` (GCC/Clang) or `capacity * 1.5` (MSVC)
2. Move (or copy) all elements to new storage
3. Destroy old elements and deallocate old storage
4. Update pointers

**Amortized O(1) push_back:** Each element is moved O(1) times on average.

### Simplified Implementation

```cpp
#include <iostream>
#include <memory>

template<typename T>
class SimpleVector {
    T* data_;
    size_t size_, capacity_;
    std::allocator<T> alloc_;

public:
    SimpleVector() : data_(nullptr), size_(0), capacity_(0) {}

    ~SimpleVector() {
        for (size_t i = 0; i < size_; i++)
            std::destroy_at(&data_[i]);
        if (data_) alloc_.deallocate(data_, capacity_);
    }

    void push_back(const T& val) {
        if (size_ == capacity_) {
            size_t newCap = capacity_ == 0 ? 1 : capacity_ * 2;
            reserve(newCap);
        }
        std::construct_at(&data_[size_], val);
        size_++;
    }

    void reserve(size_t newCap) {
        if (newCap <= capacity_) return;
        T* newData = alloc_.allocate(newCap);
        for (size_t i = 0; i < size_; i++) {
            std::construct_at(&newData[i], std::move(data_[i]));
            std::destroy_at(&data_[i]);
        }
        if (data_) alloc_.deallocate(data_, capacity_);
        data_ = newData;
        capacity_ = newCap;
    }

    T& operator[](size_t i) { return data_[i]; }
    const T& operator[](size_t i) const { return data_[i]; }
    size_t size() const { return size_; }
    size_t capacity() const { return capacity_; }
};

int main() {
    SimpleVector<int> v;
    for (int i = 0; i < 20; i++) {
        v.push_back(i);
        std::cout << "i=" << i << " size=" << v.size()
                  << " cap=" << v.capacity() << "\n";
    }
    return 0;
}
```

### Key Properties

| Property | Value |
|---|---|
| Random access | O(1) |
| Push back (amortized) | O(1) |
| Push back (worst case) | O(n) — reallocation |
| Insert at position | O(n) — shift elements |
| Erase at position | O(n) — shift elements |
| Iterator invalidation on push_back | All if reallocation |
| Memory layout | Contiguous |

### Performance Tips

1. **Reserve if you know the size:** `v.reserve(n)` avoids reallocations
2. **Use `emplace_back` instead of `push_back`:** Constructs in-place, avoids copies
3. **Prefer `vector` over `deque`/`list`:** Cache-friendly contiguous memory
4. **Shrink to fit:** `v.shrink_to_fit()` releases unused capacity (may reallocate)

---

## 128.3 std::deque Internals

### How std::deque Works

A `deque` (double-ended queue) uses a **block-based** structure:

```
Map (array of pointers to blocks):
[block0] [block1] [block2] [block3]
   |        |        |        |
   v        v        v        v
 [e0..e7] [e8..e15] [e16..e23] [e24..e31]
```

- Fixed-size blocks (typically 512 bytes or element-size dependent)
- A "map" array holds pointers to blocks
- `push_front` and `push_back` are O(1) amortized

### Comparison with vector

| Aspect | vector | deque |
|---|---|---|
| Random access | O(1), cache-friendly | O(1), may cache-miss |
| Push back | O(1) amortized | O(1) amortized |
| Push front | O(n) | O(1) amortized |
| Insert middle | O(n) | O(n) |
| Memory | Contiguous | Block-based |
| Iterator invalidation | On reallocation | On insert/erase at ends |

---

## 128.4 std::map and std::set: Red-Black Trees

### How std::map Works

`std::map` is implemented as a **red-black tree** — a self-balancing binary search tree.

**Red-Black Tree Properties:**
1. Every node is red or black
2. Root is black
3. Every leaf (NIL) is black
4. If a node is red, both children are black
5. For each node, all paths to descendant leaves have the same number of black nodes

These properties guarantee O(log n) height.

### Node Structure

```cpp
template<typename K, typename V>
struct RBNode {
    K key;
    V value;
    RBNode* left;
    RBNode* right;
    RBNode* parent;
    enum Color { RED, BLACK } color;
};
```

### Operations

| Operation | Time | Notes |
|---|---|---|
| find | O(log n) | BST search |
| insert | O(log n) | BST insert + rebalance |
| erase | O(log n) | BST erase + rebalance |
| lower_bound | O(log n) | BST search |
| begin/end | O(1) | Leftmost/rightmost |

### Iterator Invalidation

- `insert`: Never invalidates existing iterators
- `erase`: Only invalidates iterators to erased element
- This is a key advantage over `unordered_map`

### When to Use map vs unordered_map

| Scenario | Use map | Use unordered_map |
|---|---|---|
| Need ordered traversal | ✓ | ✗ |
| Need range queries | ✓ | ✗ |
| Worst-case O(1) lookup | ✗ | ✓ (with good hash) |
| Iterator stability | ✓ | ✗ (on rehash) |
| Memory overhead | Lower | Higher (buckets) |

---

## 128.5 std::unordered_map: Hash Table Internals

### How std::unordered_map Works

Uses **chaining** (linked lists in buckets) for collision resolution.

```
Bucket array:
[0] -> nullptr
[1] -> [key1,val1] -> [key2,val2] -> nullptr
[2] -> nullptr
[3] -> [key3,val3] -> nullptr
...
[n-1] -> nullptr
```

### Load Factor and Rehashing

- **Load factor** = size / bucket_count
- **Max load factor** (default 1.0): When exceeded, the table rehashes
- **Rehash:** Allocate new bucket array (typically 2x), reinsert all elements

### Hash Function

```cpp
// Default hash for common types
template<typename T>
struct hash {
    size_t operator()(const T& val) const;
};

// Specializations exist for int, long, string, pointer, etc.
// Custom types need custom hash:
struct MyType {
    int x, y;
};

struct MyTypeHash {
    size_t operator()(const MyType& t) const {
        return std::hash<int>()(t.x) ^ (std::hash<int>()(t.y) << 1);
    }
};
```

### Performance Characteristics

| Operation | Average | Worst Case |
|---|---|---|
| find | O(1) | O(n) — all same bucket |
| insert | O(1) | O(n) |
| erase | O(1) | O(n) |

**Worst case happens when:** All keys hash to the same bucket (bad hash function).

### Swiss Table (absl::flat_hash_map)

Google's flat_hash_map uses **Swiss Table** design:
- Open addressing (no chaining)
- SIMD-based probing (checks 16 slots at once)
- Better cache performance than std::unordered_map
- 87.5% max load factor vs 1.0 for std

```cpp
#include <absl/container/flat_hash_map.h>

absl::flat_hash_map<int, int> map;
// Same API as std::unordered_map, but faster
```

### Robin Hood Hashing

Alternative collision resolution that reduces worst-case probe lengths:
- On insertion, if the new element's probe length exceeds the existing element's,
  swap them (rich gives to poor)
- Results in more uniform probe lengths
- Used by `robin_hood::unordered_map`

---

## 128.6 std::sort Internals

### IntroSort (GCC/Clang)

`std::sort` uses **IntroSort** — a hybrid of:
1. **QuickSort** for average case
2. **HeapSort** when recursion depth exceeds 2·log(n) (avoids O(n²) worst case)
3. **InsertionSort** for small subarrays (≤ 16 elements)

```
IntroSort(arr, depth_limit):
    if size ≤ 16:
        InsertionSort(arr)
    else if depth_limit == 0:
        HeapSort(arr)
    else:
        pivot = MedianOfThree(arr)
        partition around pivot
        IntroSort(left, depth_limit - 1)
        IntroSort(right, depth_limit - 1)
```

### Complexity

| Case | Time | Notes |
|---|---|---|
| Average | O(n log n) | QuickSort |
| Worst case | O(n log n) | HeapSort fallback |
| Best case | O(n) | Already sorted (InsertionSort) |

### std::stable_sort

Uses **MergeSort** to preserve relative order of equal elements.
- O(n log n) time
- O(n) extra space

### Why IntroSort Over Pure QuickSort?

Pure QuickSort has O(n²) worst case (sorted input, duplicate elements).
IntroSort's HeapSort fallback guarantees O(n log n).

---

## 128.7 std::priority_queue Internals

### How std::priority_queue Works

Uses a **binary heap** (typically `std::vector` as underlying container).

```
Array: [90, 80, 70, 30, 60, 50, 40]

Tree view:
        90
       /  \
      80    70
     / \   / \
    30  60 50  40
```

**Parent-child relationship:**
- Parent of i: (i-1)/2
- Left child of i: 2i+1
- Right child of i: 2i+2

### Operations

| Operation | Time | Notes |
|---|---|---|
| push | O(log n) | Sift up |
| pop | O(log n) | Sift down |
| top | O(1) | Root element |
| size | O(1) | |

### Push: Sift Up

```
push(65):
Initial:   [90, 80, 70, 30, 60, 50, 40]
Add 65:    [90, 80, 70, 30, 60, 50, 40, 65]
Sift up:   65 > 30? Yes → swap → [90, 80, 70, 65, 60, 50, 40, 30]
           65 > 80? No → done
```

### Pop: Sift Down

```
pop():
Take root 90, replace with last element 30:
[30, 80, 70, 65, 60, 50, 40]
Sift down: 30 < max(80,70)? Yes → swap with 80
[80, 30, 70, 65, 60, 50, 40]
Sift down: 30 < max(65,60)? Yes → swap with 65
[80, 65, 70, 30, 60, 50, 40]
Sift down: 30 has no children → done
```

---

## 128.8 std::string: Small String Optimization (SSO)

### What is SSO?

For short strings (typically ≤ 15 chars on 64-bit), `std::string` stores the
characters **inline** in the string object itself, avoiding heap allocation.

```
Long string (> 15 chars):
struct string {
    char* data;      // pointer to heap
    size_t size;
    size_t capacity;
};
// Total: 24 bytes + heap allocation

Short string (≤ 15 chars, SSO):
struct string {
    char data[16];   // inline storage
    size_t size;
};
// Total: 24 bytes, no heap allocation
```

### Why SSO Matters

- **No heap allocation** for short strings → faster
- **Cache-friendly** → data is inline
- **No memory fragmentation** from many small allocations

### Proof of SSO

```cpp
#include <iostream>
#include <string>

int main() {
    // Short string: stored inline
    std::string short_str = "Hello";
    std::cout << "Short: size=" << short_str.size()
              << " cap=" << short_str.capacity() << "\n";

    // Long string: heap allocated
    std::string long_str = "This is a very long string that exceeds SSO";
    std::cout << "Long: size=" << long_str.size()
              << " cap=" << long_str.capacity() << "\n";

    // Demonstrate SSO threshold
    for (int len = 0; len <= 25; len++) {
        std::string s(len, 'x');
        std::cout << "len=" << len << " cap=" << s.capacity() << "\n";
    }
    return 0;
}
```

Typical output shows capacity jumps from 15 (inline) to 22+ (heap) around len=16.

---

## 128.9 Iterator Invalidation Rules

### vector

| Operation | Invalidates |
|---|---|
| push_back | All if reallocation; none otherwise |
| pop_back | Only to last element |
| insert | All at/after insertion point |
| erase | All at/after erase point |
| clear | All |
| reserve | All if reallocation |

### deque

| Operation | Invalidates |
|---|---|
| push_front/back | All iterators; references valid |
| pop_front/back | Iterators to front/back |
| insert middle | All |
| erase middle | All |

### map/set (red-black tree)

| Operation | Invalidates |
|---|---|
| insert | None |
| erase | Only to erased element |
| find | None |

### unordered_map/unordered_set

| Operation | Invalidates |
|---|---|
| insert | All if rehash; none otherwise |
| erase | Only to erased element |
| find | None |
| rehash | All |

---

## 128.10 Custom Allocator Example

```cpp
#include <iostream>
#include <vector>
#include <memory>

// Arena allocator: bump pointer, very fast, no individual deallocation
template<typename T>
class ArenaAllocator {
    T* arena_;
    size_t capacity_;
    size_t offset_;

public:
    using value_type = T;

    ArenaAllocator(T* arena, size_t cap)
        : arena_(arena), capacity_(cap), offset_(0) {}

    T* allocate(size_t n) {
        if (offset_ + n > capacity_) throw std::bad_alloc();
        T* ptr = arena_ + offset_;
        offset_ += n;
        return ptr;
    }

    void deallocate(T*, size_t) {
        // Arena allocator: no-op (bulk free at end)
    }

    void reset() { offset_ = 0; }
};

int main() {
    // Pre-allocate arena
    constexpr size_t ARENA_SIZE = 1024;
    int arena[ARENA_SIZE];

    ArenaAllocator<int> alloc(arena, ARENA_SIZE);
    std::vector<int, ArenaAllocator<int>> vec(alloc);

    for (int i = 0; i < 100; i++)
        vec.push_back(i);

    std::cout << "Size: " << vec.size() << "\n";
    return 0;
}
```

---

## 128.11 Common Interview Questions

1. **Q:** What's the time complexity of `std::vector::push_back`?
   **A:** Amortized O(1). Worst case O(n) when reallocation is needed. Reallocation
   typically doubles capacity, so the amortized cost per insertion is constant.

2. **Q:** When does `std::vector` invalidate iterators?
   **A:** On `push_back` if reallocation occurs (capacity doubles). After reallocation,
   ALL iterators, pointers, and references are invalidated.

3. **Q:** What's the difference between `std::map` and `std::unordered_map`?
   **A:** `map` uses a red-black tree (O(log n), ordered, stable iterators).
   `unordered_map` uses a hash table (O(1) average, unordered, iterators may
   invalidate on rehash).

4. **Q:** How does `std::sort` work?
   **A:** IntroSort — starts with QuickSort, switches to HeapSort if recursion
   depth exceeds 2·log(n), uses InsertionSort for small subarrays (≤16 elements).

5. **Q:** What is Small String Optimization (SSO)?
   **A:** For short strings (≤15 chars), the string data is stored inline in the
   string object, avoiding heap allocation. This improves performance for many
   small string operations.

6. **Q:** Why is `std::deque` slower than `std::vector` for random access?
   **A:** `deque` uses block-based storage, so accessing element i requires computing
   which block it's in and then accessing that block. `vector` uses contiguous
   memory, which is cache-friendly for sequential and random access.

---

## 128.12 Practice Problems

1. **Implement a simple vector** with push_back, reserve, and operator[]
2. **Implement an LRU cache** using `unordered_map` + `list`
3. **Benchmark** `vector` vs `deque` vs `list` for various operations
4. **Implement a min-heap** from scratch using an array
5. **Write a custom hash function** for a struct with multiple fields

---

## 128.13 Related Topics

| Topic | Chapter | Connection |
|---|---|---|
| Hash Tables | Ch. 25 | Foundation for unordered containers |
| Red-Black Trees | Ch. 30 | Foundation for map/set |
| Sorting Algorithms | Ch. 05 | std::sort implementation |
| Memory Management | Ch. 129 | Allocators and memory layout |
| Cache-Oblivious Algorithms | Ch. 132 | Why contiguous memory matters |

---

## Summary

| Container | Underlying Structure | Key Operation | Time |
|---|---|---|---|
| vector | Dynamic array | Random access | O(1) |
| deque | Block array | Push front/back | O(1) amortized |
| list | Doubly linked list | Insert/erase anywhere | O(1) |
| set/map | Red-black tree | Find/insert/erase | O(log n) |
| unordered_* | Hash table | Find/insert/erase | O(1) avg |
| priority_queue | Binary heap | Push/pop | O(log n) |

**Key Takeaway:** STL containers make specific trade-offs between cache performance,
iterator stability, worst-case guarantees, and memory overhead. Understanding these
trade-offs is essential for writing high-performance C++ code.
