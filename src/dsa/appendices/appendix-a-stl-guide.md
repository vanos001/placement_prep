# Appendix A: Complete STL Guide

The C++ Standard Template Library (STL) is the competitive programmer's and interview candidate's most powerful weapon. This appendix covers every major container, algorithm, and utility you need.

---

## 1. Sequence Containers

### 1.1 `std::vector`

The workhorse of competitive programming. Dynamic array with amortized O(1) push_back.

```cpp
#include <vector>
#include <iostream>
#include <algorithm>
using namespace std;

int main() {
    // Construction
    vector<int> v;                // empty
    vector<int> v2(10);           // 10 elements, value 0
    vector<int> v3(10, 42);       // 10 elements, value 42
    vector<int> v4 = {1, 2, 3};   // initializer list
    vector<int> v5(v4.begin(), v4.end()); // from iterator range

    // Adding elements
    v.push_back(1);        // O(1) amortized
    v.emplace_back(2);     // constructs in-place, slightly faster
    v.insert(v.begin(), 0); // O(n) - shifts elements
    v.insert(v.begin() + 2, 5); // insert at position 2

    // Accessing
    v[0];          // no bounds check
    v.at(0);       // throws std::out_of_range
    v.front();     // first element
    v.back();      // last element
    v.data();      // pointer to underlying array

    // Size and capacity
    v.size();      // number of elements
    v.empty();     // true if size == 0
    v.capacity();  // allocated storage
    v.reserve(100); // pre-allocate (doesn't change size)
    v.resize(20);   // change size (adds/removes elements)
    v.shrink_to_fit(); // request to free unused memory

    // Removing
    v.pop_back();           // O(1) - remove last
    v.erase(v.begin());     // O(n) - remove first
    v.erase(v.begin(), v.begin() + 3); // erase range
    v.clear();              // remove all, doesn't free memory

    // Remove-erase idiom (CRITICAL for interviews)
    v = {1, 2, 3, 2, 5, 2};
    v.erase(remove(v.begin(), v.end(), 2), v.end()); // removes all 2s

    // Iterators
    for (auto it = v.begin(); it != v.end(); ++it) { /* ... */ }
    for (auto it = v.rbegin(); it != v.rend(); ++it) { /* reverse */ }
    for (int x : v) { /* range-based for */ }

    // Comparison (lexicographic)
    vector<int> a = {1, 2, 3}, b = {1, 2, 4};
    bool less = (a < b); // true

    // 2D vectors
    vector<vector<int>> grid(3, vector<int>(4, 0)); // 3x4 grid of zeros
}
```

**Key facts:**
- Memory layout: contiguous (cache-friendly, pointer arithmetic works)
- Iterator invalidation: `push_back` may invalidate all iterators if reallocation occurs
- `emplace_back` vs `push_back`: `emplace_back` constructs in-place, avoids copy/move

### 1.2 `std::deque`

Double-ended queue. O(1) push/pop at both ends.

```cpp
#include <deque>

int main() {
    deque<int> dq;
    dq.push_back(1);    // O(1)
    dq.push_front(0);   // O(1) - vector can't do this!
    dq.pop_back();      // O(1)
    dq.pop_front();     // O(1)
    dq[0];              // O(1) random access
    dq.size();

    // Useful for: sliding window, monotonic deque
}
```

**Key facts:**
- NOT contiguous memory (no `.data()`, pointer arithmetic doesn't work)
- Random access is O(1) but slower than vector
- Use when you need push_front/pop_front

### 1.3 `std::list`

Doubly-linked list.

```cpp
#include <list>

int main() {
    list<int> lst = {1, 2, 3, 4, 5};

    lst.push_back(6);     // O(1)
    lst.push_front(0);    // O(1)
    lst.pop_back();       // O(1)
    lst.pop_front();      // O(1)

    // Insert/erase without invalidating other iterators
    auto it = lst.begin();
    advance(it, 2);       // O(n) - no random access
    lst.insert(it, 99);   // O(1)
    lst.erase(it);        // O(1)

    // Splice - move elements between lists in O(1)
    list<int> other = {10, 20};
    lst.splice(lst.begin(), other); // move all of 'other' to front

    // Sort (specialized, not std::sort)
    lst.sort();           // O(n log n), stable
    lst.unique();         // remove consecutive duplicates (sort first)
    lst.reverse();        // O(n)
    lst.merge(other);     // merge sorted lists

    // NO random access - lst[0] doesn't compile
}
```

**When to use:** Almost never in competitive programming. Useful when you need stable iterators during insert/erase.

### 1.4 `std::forward_list`

Singly-linked list. More memory-efficient than `list`.

```cpp
#include <forward_list>

int main() {
    forward_list<int> fl = {1, 2, 3};
    fl.push_front(0);     // O(1)
    fl.pop_front();       // O(1)
    // No push_back, no size(), no back()

    auto it = fl.before_begin(); // iterator before first element
    fl.insert_after(it, 99);     // O(1)
    fl.erase_after(it);          // O(1)

    fl.sort();  // O(n log n)
}
```

**When to use:** Memory-constrained scenarios. Rarely needed.

### 1.5 `std::array`

Fixed-size array. Stack-allocated, zero overhead.

```cpp
#include <array>

int main() {
    array<int, 5> arr = {1, 2, 3, 4, 5};

    arr[0];           // O(1)
    arr.at(0);        // bounds-checked
    arr.size();       // always 5
    arr.front();
    arr.back();
    arr.fill(0);      // set all to 0

    // Works with STL algorithms
    sort(arr.begin(), arr.end());

    // Can be returned from functions (unlike C arrays)
}
```

---

## 2. Associative Containers

All associative containers are ordered (by default, using `<`). They use balanced BSTs (typically red-black trees).

### 2.1 `std::set`

Sorted set of unique elements.

```cpp
#include <set>

int main() {
    set<int> s = {3, 1, 4, 1, 5}; // {1, 3, 4, 5}

    // Insertion
    s.insert(2);           // O(log n)
    s.emplace(6);          // O(log n)
    auto [it, inserted] = s.insert(3); // inserted = false (already exists)

    // Lookup
    s.count(3);            // 0 or 1 (O(log n))
    s.find(3);             // iterator or s.end() (O(log n))
    s.contains(3);         // C++20

    // Deletion
    s.erase(3);            // O(log n)
    s.erase(s.begin());    // O(1) amortized
    s.erase(s.begin(), s.find(4)); // range erase

    // Bounds (CRITICAL for interviews)
    s = {1, 3, 5, 7, 9};
    auto lo = s.lower_bound(4);  // iterator to 5 (first >= 4)
    auto hi = s.upper_bound(4);  // iterator to 5 (first > 4)
    auto lo2 = s.lower_bound(5); // iterator to 5 (first >= 5)
    auto hi2 = s.upper_bound(5); // iterator to 7 (first > 5)

    // For range [lo, hi]: use lower_bound(lo) and upper_bound(hi)
    // This gives all elements in [lo, hi]

    // Iteration (sorted order)
    for (int x : s) { /* 1, 3, 5, 7, 9 */ }

    // Custom comparator
    set<int, greater<int>> desc; // descending order
}
```

### 2.2 `std::multiset`

Like `set` but allows duplicates.

```cpp
#include <set>

int main() {
    multiset<int> ms = {1, 1, 2, 2, 3};

    ms.insert(2);           // now has three 2's
    ms.count(2);            // 3

    // Erase ALL occurrences
    ms.erase(2);            // removes all 2's, returns count

    // Erase ONE occurrence
    ms.erase(ms.find(2));   // removes just one

    // Equal range: all elements with value x
    auto [lo, hi] = ms.equal_range(2);
    int count = distance(lo, hi);

    // Lower/upper bound work as expected
    // lower_bound(2) -> first 2
    // upper_bound(2) -> first element after all 2's
}
```

### 2.3 `std::map`

Sorted key-value pairs.

```cpp
#include <map>
#include <string>

int main() {
    map<string, int> mp;

    // Insertion
    mp["alice"] = 95;        // O(log n), creates if not exists
    mp.insert({"bob", 87});  // O(log n)
    mp.emplace("carol", 92); // O(log n)

    // Access (BE CAREFUL: operator[] creates default if missing!)
    int score = mp["alice"];  // 95
    int zero = mp["dave"];    // creates "dave" -> 0 (BAD in read-only context!)

    // Safe access
    auto it = mp.find("dave");
    if (it != mp.end()) { /* it->second */ }

    // C++20
    if (mp.contains("alice")) { /* ... */ }

    // Iteration (sorted by key)
    for (auto& [key, value] : mp) {
        // structured binding (C++17)
    }

    // Bounds
    auto lo = mp.lower_bound("bob");  // first key >= "bob"
    auto hi = mp.upper_bound("carol"); // first key > "carol"

    // Merge with [] for frequency counting
    vector<int> nums = {1, 2, 3, 2, 1};
    map<int, int> freq;
    for (int x : nums) freq[x]++;
    // freq: {1:2, 2:2, 3:1}
}
```

### 2.4 `std::multimap`

Like `map` but allows duplicate keys.

```cpp
#include <map>

int main() {
    multimap<string, int> grades;
    grades.insert({"alice", 95});
    grades.insert({"alice", 87}); // alice has two grades
    grades.insert({"bob", 92});

    // No operator[] for multimap!
    grades.find("alice"); // iterator to first "alice"

    auto [lo, hi] = grades.equal_range("alice");
    for (auto it = lo; it != hi; ++it) {
        // it->second: 95, 87
    }
}
```

---

## 3. Unordered Containers

Hash-based. O(1) average, O(n) worst case.

### 3.1 `std::unordered_set`

```cpp
#include <unordered_set>

int main() {
    unordered_set<int> us;

    us.insert(1);        // O(1) average
    us.count(1);         // 0 or 1, O(1) average
    us.find(1);          // iterator, O(1) average
    us.erase(1);         // O(1) average

    // Custom hash (for pairs, custom types)
    struct PairHash {
        size_t operator()(const pair<int,int>& p) const {
            return hash<long long>()(((long long)p.first << 32) | p.second);
        }
    };
    unordered_set<pair<int,int>, PairHash> ps;

    // Bucket interface
    us.bucket_count();    // number of buckets
    us.load_factor();     // size / bucket_count
    us.max_load_factor(); // default 1.0
}
```

### 3.2 `std::unordered_map`

```cpp
#include <unordered_map>
#include <string>

int main() {
    unordered_map<string, int> um;
    um["key"] = 42;         // O(1) average
    um.find("key");         // O(1) average
    um.count("key");        // O(1) average
    um.erase("key");        // O(1) average

    // Same caution with operator[] as map
}
```

**When to use unordered vs ordered:**
- Unordered: when you only need insert/find/erase, don't need ordering
- Ordered: when you need iteration in sorted order, or need lower_bound/upper_bound
- In practice, unordered containers are faster for large datasets but have higher constant factor for small n

---

## 4. Container Adaptors

### 4.1 `std::stack`

LIFO. Default uses `deque`.

```cpp
#include <stack>

int main() {
    stack<int> st;
    st.push(1);      // O(1)
    st.emplace(2);   // O(1)
    st.top();        // O(1) - peek
    st.pop();        // O(1) - no return value!
    st.empty();      // O(1)
    st.size();       // O(1)

    // Can use vector as underlying container
    stack<int, vector<int>> st2;
}
```

### 4.2 `std::queue`

FIFO. Default uses `deque`.

```cpp
#include <queue>

int main() {
    queue<int> q;
    q.push(1);       // O(1)
    q.emplace(2);    // O(1)
    q.front();       // O(1) - peek front
    q.back();        // O(1) - peek back
    q.pop();         // O(1) - no return value!
    q.empty();
    q.size();
}
```

### 4.3 `std::priority_queue`

Max-heap by default.

```cpp
#include <queue>
#include <vector>
#include <functional>

int main() {
    // Max-heap (default)
    priority_queue<int> maxpq;
    maxpq.push(3);     // O(log n)
    maxpq.push(1);
    maxpq.push(4);
    maxpq.top();       // 4 (O(1))
    maxpq.pop();       // O(log n)

    // Min-heap
    priority_queue<int, vector<int>, greater<int>> minpq;
    minpq.push(3);
    minpq.push(1);
    minpq.top();       // 1

    // Custom comparator (pair-based)
    using P = pair<int, int>;
    priority_queue<P, vector<P>, greater<P>> pq; // min-heap by first

    // Build from existing container: O(n)
    vector<int> v = {3, 1, 4, 1, 5};
    priority_queue<int> pq2(v.begin(), v.end());

    // Custom comparator with lambda (C++17)
    auto cmp = [](int a, int b) { return a > b; }; // min-heap
    priority_queue<int, vector<int>, decltype(cmp)> pq3(cmp);
}
```

---

## 5. Iterators

### 5.1 Iterator Categories

| Category | Capabilities | Containers |
|----------|-------------|------------|
| **Input** | Read once, forward | `istream_iterator` |
| **Output** | Write once, forward | `ostream_iterator` |
| **Forward** | Read/write, forward, multi-pass | `forward_list`, `unordered_*` |
| **Bidirectional** | + backward | `list`, `set`, `map` |
| **Random Access** | + arithmetic (`+n`, `-n`, `[]`) | `vector`, `deque`, `array` |
| **Contiguous** | + contiguous memory | `vector`, `array`, `string` (C++20) |

### 5.2 Iterator Operations

```cpp
#include <iterator>
#include <vector>
#include <iostream>

int main() {
    vector<int> v = {1, 2, 3, 4, 5};

    // Basic operations
    auto it = v.begin();
    *it;              // dereference: 1
    ++it;             // advance: now points to 2
    --it;             // back: now points to 1
    it + 3;           // random access: points to 4
    it[2];            // equivalent to *(it + 2): 3
    distance(v.begin(), v.end()); // 5

    // Advance (modifies iterator)
    auto it2 = v.begin();
    advance(it2, 3);  // it2 now points to 4

    // Next/Prev (returns new iterator)
    auto it3 = next(v.begin());     // points to 2
    auto it4 = prev(v.end());       // points to 5
    auto it5 = next(v.begin(), 3);  // points to 4

    // Insert iterators
    vector<int> dest;
    back_insert_iterator<vector<int>> bii(dest);
    *bii = 10; // same as dest.push_back(10)

    // Or more commonly:
    copy(v.begin(), v.end(), back_inserter(dest));

    // Stream iterators
    copy(v.begin(), v.end(), ostream_iterator<int>(cout, " "));
    // Output: 1 2 3 4 5
}
```

### 5.3 Reverse Iterators

```cpp
vector<int> v = {1, 2, 3, 4, 5};

// Reverse iteration
for (auto it = v.rbegin(); it != v.rend(); ++it) {
    // 5, 4, 3, 2, 1
}

// Convert reverse to forward
auto rit = v.rbegin(); // points to 5
auto fit = rit.base(); // points to v.end()

// CRITICAL: reverse_iterator base() is off by one!
// rit points to element X, rit.base() points to element AFTER X
```

---

## 6. Algorithms

```cpp
#include <algorithm>
#include <numeric>
#include <functional>
```

### 6.1 Sorting

```cpp
vector<int> v = {3, 1, 4, 1, 5, 9};

// Basic sort: O(n log n)
sort(v.begin(), v.end());              // ascending
sort(v.begin(), v.end(), greater<>()); // descending

// Custom comparator
sort(v.begin(), v.end(), [](int a, int b) {
    return a > b; // descending
});

// Sorting pairs/tuples: compares lexicographically
vector<pair<int,int>> vp = {{1,3}, {1,2}, {2,1}};
sort(vp.begin(), vp.end());
// Result: {{1,2}, {1,3}, {2,1}}

// Stable sort: preserves relative order of equal elements
stable_sort(v.begin(), v.end());

// Partial sort: only first k elements sorted
partial_sort(v.begin(), v.begin() + 3, v.end());
// First 3 elements are the 3 smallest, sorted

// nth_element: partition around nth position
nth_element(v.begin(), v.begin() + 3, v.end());
// v[3] is what would be there if fully sorted
// All elements before are <= v[3], all after are >= v[3]
// O(n) average!

// Is sorted?
is_sorted(v.begin(), v.end());
```

### 6.2 Binary Search

```cpp
vector<int> v = {1, 2, 3, 4, 5, 5, 5, 6, 7};

// Binary search: does element exist? O(log n)
binary_search(v.begin(), v.end(), 5); // true

// Lower bound: first element >= value
auto lo = lower_bound(v.begin(), v.end(), 5); // points to first 5
int idx = lo - v.begin(); // index: 4

// Upper bound: first element > value
auto hi = upper_bound(v.begin(), v.end(), 5); // points to 6
int idx2 = hi - v.begin(); // index: 7

// Count of 5s in sorted range:
int count = upper_bound(v.begin(), v.end(), 5) -
            lower_bound(v.begin(), v.end(), 5); // 3

// Equal range: returns pair of (lower_bound, upper_bound)
auto [lo2, hi2] = equal_range(v.begin(), v.end(), 5);

// IMPORTANT: these require SORTED data
// For unsorted data, use find() which is O(n)
```

### 6.3 Permutations

```cpp
vector<int> v = {1, 2, 3};

// Next permutation: O(n)
do {
    // process permutation
} while (next_permutation(v.begin(), v.end()));
// Generates all permutations in lexicographic order
// START with sorted input to get ALL permutations

// Previous permutation
prev_permutation(v.begin(), v.end());

// To check if it's the last permutation:
// next_permutation returns false when it wraps around
```

### 6.4 Unique and Remove

```cpp
vector<int> v = {1, 1, 2, 2, 2, 3, 3};

// Unique: removes CONSECUTIVE duplicates (data must be sorted)
auto new_end = unique(v.begin(), v.end());
// v is now: {1, 2, 3, ?, ?, ?, ?} (new_end points past 3)

// Proper way to get unique elements:
v.erase(unique(v.begin(), v.end()), v.end());
// v is now: {1, 2, 3}

// Remove: moves elements matching value to end
v = {1, 2, 3, 2, 5, 2};
auto new_end2 = remove(v.begin(), v.end(), 2);
v.erase(new_end2, v.end()); // remove-erase idiom
// v is now: {1, 3, 5}

// Remove_if: remove with predicate
v = {1, 2, 3, 4, 5, 6};
v.erase(remove_if(v.begin(), v.end(), [](int x) { return x % 2 == 0; }), v.end());
// v is now: {1, 3, 5}
```

### 6.5 Rotate and Reverse

```cpp
vector<int> v = {1, 2, 3, 4, 5};

// Rotate: makes element at middle the first element
rotate(v.begin(), v.begin() + 2, v.end());
// v is now: {3, 4, 5, 1, 2}

// Reverse
reverse(v.begin(), v.end());
```

### 6.6 Accumulate and Prefix Sums

```cpp
#include <numeric>

vector<int> v = {1, 2, 3, 4, 5};

// Sum
int sum = accumulate(v.begin(), v.end(), 0); // 15

// Product
int prod = accumulate(v.begin(), v.end(), 1, multiplies<int>()); // 120

// String concatenation
vector<string> words = {"hello", " ", "world"};
string s = accumulate(words.begin(), words.end(), string(""));

// Partial sum: prefix sums
vector<int> prefix(v.size());
partial_sum(v.begin(), v.end(), prefix.begin());
// prefix: {1, 3, 6, 10, 15}

// Adjacent difference
vector<int> diff(v.size());
adjacent_difference(v.begin(), v.end(), diff.begin());
// diff: {1, 1, 1, 1, 1}
```

### 6.7 Min/Max and Clamping

```cpp
vector<int> v = {3, 1, 4, 1, 5, 9};

// Min and max element
auto [mn, mx] = minmax_element(v.begin(), v.end());
// *mn = 1, *mx = 9

// Min and max of values
min(3, 5);           // 3
max(3, 5);           // 5
min({1, 2, 3, 4});   // 1 (initializer list)
max({1, 2, 3, 4});   // 4

// Clamp (C++17)
int x = clamp(15, 0, 10); // 10 (clamped to max)
int y = clamp(-5, 0, 10); // 0  (clamped to min)
int z = clamp(5, 0, 10);  // 5  (within range)
```

### 6.8 Count and Find

```cpp
vector<int> v = {1, 2, 3, 2, 5};

// Count
int cnt = count(v.begin(), v.end(), 2);       // 2
int cnt2 = count_if(v.begin(), v.end(),
    [](int x) { return x > 2; });             // 2

// Find
auto it = find(v.begin(), v.end(), 3);        // iterator to 3
auto it2 = find_if(v.begin(), v.end(),
    [](int x) { return x > 3; });             // iterator to 5
auto it3 = find_if_not(v.begin(), v.end(),
    [](int x) { return x < 3; });             // iterator to 3

// All/any/none (C++11)
all_of(v.begin(), v.end(), [](int x) { return x > 0; }); // true
any_of(v.begin(), v.end(), [](int x) { return x > 4; }); // true
none_of(v.begin(), v.end(), [](int x) { return x < 0; }); // true
```

### 6.9 Merge and Set Operations

```cpp
vector<int> a = {1, 3, 5}, b = {2, 4, 6};

// Merge (both must be sorted)
vector<int> merged(a.size() + b.size());
merge(a.begin(), a.end(), b.begin(), b.end(), merged.begin());
// merged: {1, 2, 3, 4, 5, 6}

// Inplace merge
vector<int> c = {1, 3, 5, 2, 4, 6};
inplace_merge(c.begin(), c.begin() + 3, c.end());
// c: {1, 2, 3, 4, 5, 6}

// Set operations (all require sorted ranges)
set_union(a.begin(), a.end(), b.begin(), b.end(), back_inserter(result));
set_intersection(a.begin(), a.end(), b.begin(), b.end(), back_inserter(result));
set_difference(a.begin(), a.end(), b.begin(), b.end(), back_inserter(result));
set_symmetric_difference(a.begin(), a.end(), b.begin(), b.end(), back_inserter(result));

// Includes: is one range a subset of another?
includes(a.begin(), a.end(), a.begin(), a.begin() + 2); // true
```

### 6.10 Heap Operations

```cpp
vector<int> v = {3, 1, 4, 1, 5, 9};

// Make heap: O(n)
make_heap(v.begin(), v.end()); // max-heap: v[0] = 9

// Push: add element then heapify
v.push_back(7);
push_heap(v.begin(), v.end()); // O(log n)

// Pop: move top to end, then heapify
pop_heap(v.begin(), v.end()); // v.back() is now the max
int max_val = v.back();
v.pop_back();

// Sort heap: O(n log n)
sort_heap(v.begin(), v.end());

// Check
is_heap(v.begin(), v.end());
```

### 6.11 Partitioning

```cpp
vector<int> v = {1, 2, 3, 4, 5, 6};

// Partition: elements satisfying predicate come first
auto it = partition(v.begin(), v.end(),
    [](int x) { return x % 2 == 0; });
// Possible result: {6, 2, 4, 3, 5, 1} (relative order may change)

// Stable partition: preserves relative order
auto it2 = stable_partition(v.begin(), v.end(),
    [](int x) { return x % 2 == 0; });
// Result: {2, 4, 6, 1, 3, 5}

// Partition point (C++11)
auto pp = partition_point(v.begin(), v.end(),
    [](int x) { return x % 2 == 0; });
```

### 6.12 Copy and Transform

```cpp
vector<int> src = {1, 2, 3, 4, 5};
vector<int> dst(5);

// Copy
copy(src.begin(), src.end(), dst.begin());
copy_if(src.begin(), src.end(), back_inserter(dst),
    [](int x) { return x > 3; });
copy_n(src.begin(), 3, dst.begin()); // copy first 3
copy_backward(src.begin(), src.end(), dst.end()); // copy in reverse

// Transform
vector<int> result(5);
transform(src.begin(), src.end(), result.begin(),
    [](int x) { return x * 2; });

// Binary transform
vector<int> a = {1, 2, 3}, b = {4, 5, 6}, c(3);
transform(a.begin(), a.end(), b.begin(), c.begin(),
    [](int x, int y) { return x + y; });
// c: {5, 7, 9}

// Fill and generate
fill(v.begin(), v.end(), 0);
fill_n(v.begin(), 5, 42); // fill first 5 with 42
generate(v.begin(), v.end(), [n = 0]() mutable { return n++; });
iota(v.begin(), v.end(), 1); // 1, 2, 3, 4, 5
```

### 6.13 Mismatch and Equal

```cpp
vector<int> a = {1, 2, 3, 4, 5};
vector<int> b = {1, 2, 3, 5, 6};

// Mismatch: find first difference
auto [ia, ib] = mismatch(a.begin(), a.end(), b.begin());
// *ia = 4, *ib = 5

// Equal
equal(a.begin(), a.begin() + 3, b.begin()); // true
equal(a.begin(), a.end(), b.begin(), b.end()); // false

// Lexicographical compare
lexicographical_compare(a.begin(), a.end(), b.begin(), b.end());
```

---

## 7. Functors and Lambda Expressions

### 7.1 Built-in Functors

```cpp
#include <functional>

plus<int>()(3, 4);        // 7
minus<int>()(3, 4);       // -1
multiplies<int>()(3, 4);  // 12
divides<int>()(10, 3);    // 3
modulus<int>()(10, 3);    // 1
negate<int>()(5);         // -5

equal_to<int>()(3, 3);    // true
not_equal_to<int>()(3, 4); // true
greater<int>()(3, 4);     // false
less<int>()(3, 4);        // true
greater_equal<int>()(3, 3); // true
less_equal<int>()(3, 4);  // true

logical_and<int>()(1, 1); // true
logical_or<int>()(0, 1);  // true
logical_not<int>()(0);    // true
```

### 7.2 Lambda Expressions

```cpp
// Basic syntax: [capture](params) -> return_type { body }

// Simple lambda
auto add = [](int a, int b) { return a + b; };
add(3, 4); // 7

// Capture by value
int x = 10;
auto f1 = [x]() { return x; }; // x captured by value

// Capture by reference
auto f2 = [&x]() { x++; }; // x captured by reference

// Capture all
auto f3 = [=]() { return x; };  // all by value
auto f4 = [&]() { x++; };       // all by reference

// Mutable lambda (can modify captured-by-value)
auto f5 = [x]() mutable { x++; return x; };

// Generic lambda (C++14)
auto f6 = [](auto a, auto b) { return a + b; };

// Init capture (C++14)
auto f7 = [y = x + 1]() { return y; };

// Immediately invoked lambda (IIFE)
int result = [](int n) {
    return n * n;
}(5); // result = 25

// Lambda in STL
vector<int> v = {3, 1, 4, 1, 5};
sort(v.begin(), v.end(), [](int a, int b) {
    return a > b; // descending
});

// Lambda with structured binding (C++17)
vector<pair<int,int>> vp = {{1,3}, {2,1}, {3,2}};
sort(vp.begin(), vp.end(), [](const auto& a, const auto& b) {
    return a.second < b.second;
});
```

### 7.3 `std::function`

```cpp
#include <functional>

// Type-erased callable
function<int(int, int)> op;
op = [](int a, int b) { return a + b; };
op(3, 4); // 7

// Can hold function pointers, lambdas, functors
int (*fp)(int, int) = [](int a, int b) { return a * b; };
op = fp;

// Recursive lambda with function
function<int(int)> fib = [&](int n) -> int {
    return n <= 1 ? n : fib(n-1) + fib(n-2);
};
```

---

## 8. `pair` and `tuple`

### 8.1 `std::pair`

```cpp
#include <utility>

pair<int, string> p = {42, "hello"};
p.first;   // 42
p.second;  // "hello"

// Make pair
auto p2 = make_pair(1, "world");

// Comparison (lexicographic: compares first, then second)
pair<int,int> a = {1, 2}, b = {1, 3};
bool less = (a < b); // true

// Structured binding (C++17)
auto [x, y] = p; // x = 42, y = "hello"

// Swap
swap(p, p2);

// Useful for returning two values
pair<int, int> minMax(vector<int>& v) {
    return {*min_element(v.begin(), v.end()),
            *max_element(v.begin(), v.end())};
}
```

### 8.2 `std::tuple`

```cpp
#include <tuple>

tuple<int, string, double> t = {42, "hello", 3.14};

// Access
get<0>(t); // 42
get<1>(t); // "hello"
get<double>(t); // 3.14 (by type, if unique)

// Structured binding (C++17)
auto [a, b, c] = t;

// Make tuple
auto t2 = make_tuple(1, "world", 2.71);

// Tie: create tuple of references
int x; string y; double z;
tie(x, y, z) = t; // assigns values

// Tie with ignore
tie(ignore, y, ignore) = t; // only assign second

// Tuple comparison (lexicographic)
tuple<int,int,int> t1 = {1, 2, 3};
tuple<int,int,int> t2 = {1, 2, 4};
bool less = (t1 < t2); // true

// Apply: call function with tuple as args
auto sum = [](int a, string b, double c) { return a + c; };
double result = apply(sum, t);

// Tuple size
tuple_size<decltype(t)>::value; // 3
```

---

## 9. Common Patterns and Idioms

### 9.1 Frequency Count

```cpp
// With map
map<int, int> freq;
for (int x : arr) freq[x]++;

// With unordered_map (faster)
unordered_map<int, int> freq2;
for (int x : arr) freq2[x]++;

// With vector (when values are small, e.g., 0-255)
vector<int> freq3(256);
for (int x : arr) freq3[x]++;
```

### 9.2 Coordinate Compression

```cpp
void compress(vector<int>& coords) {
    vector<int> sorted = coords;
    sort(sorted.begin(), sorted.end());
    sorted.erase(unique(sorted.begin(), sorted.end()), sorted.end());
    for (int& x : coords) {
        x = lower_bound(sorted.begin(), sorted.end(), x) - sorted.begin();
    }
}
```

### 9.3 Merge Intervals

```cpp
vector<pair<int,int>> mergeIntervals(vector<pair<int,int>>& intervals) {
    sort(intervals.begin(), intervals.end());
    vector<pair<int,int>> merged;
    for (auto& [l, r] : intervals) {
        if (!merged.empty() && l <= merged.back().second) {
            merged.back().second = max(merged.back().second, r);
        } else {
            merged.push_back({l, r});
        }
    }
    return merged;
}
```

### 9.4 Sliding Window with Deque

```cpp
// Max in sliding window of size k
vector<int> maxSlidingWindow(vector<int>& nums, int k) {
    deque<int> dq; // stores indices
    vector<int> result;
    for (int i = 0; i < nums.size(); i++) {
        while (!dq.empty() && dq.front() <= i - k)
            dq.pop_front();
        while (!dq.empty() && nums[dq.back()] <= nums[i])
            dq.pop_back();
        dq.push_back(i);
        if (i >= k - 1)
            result.push_back(nums[dq.front()]);
    }
    return result;
}
```

### 9.5 Custom Hash for Unordered Containers

```cpp
struct custom_hash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9;
        x = (x ^ (x >> 27)) * 0x94d049bb133111eb;
        return x ^ (x >> 31);
    }

    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return splitmix64(x + FIXED_RANDOM);
    }

    size_t operator()(const pair<int,int>& p) const {
        return operator()(((uint64_t)p.first << 32) | p.second);
    }
};

unordered_map<pair<int,int>, int, custom_hash> mp;
```

### 9.6 Multiset for Running Median / Order Statistics

```cpp
#include <set>

multiset<int> lo, hi; // lo: lower half, hi: upper half

void add(int x) {
    lo.insert(x);
    hi.insert(*lo.rbegin());
    lo.erase(prev(lo.end()));
    if (hi.size() > lo.size()) {
        lo.insert(*hi.begin());
        hi.erase(hi.begin());
    }
}

int getMedian() {
    return *lo.rbegin();
}
```

### 9.7 Using `lower_bound` / `upper_bound` Correctly

```cpp
// For set/map: use member functions (O(log n) guaranteed)
set<int> s = {1, 3, 5, 7};
auto it = s.lower_bound(4); // correct: O(log n)

// DON'T use std::lower_bound on set (O(n) for non-random-access!)
auto it2 = lower_bound(s.begin(), s.end(), 4); // BAD: O(n)

// For vector: use std::lower_bound (O(log n), requires sorted)
vector<int> v = {1, 3, 5, 7};
auto it3 = lower_bound(v.begin(), v.end(), 4); // correct: O(log n)
```

### 9.8 Structured Bindings (C++17)

```cpp
// Map iteration
map<string, int> mp = {{"a", 1}, {"b", 2}};
for (auto& [key, value] : mp) {
    cout << key << ": " << value << endl;
}

// Pair/tuple
auto [x, y] = make_pair(1, 2);
auto [a, b, c] = make_tuple(1, 2, 3);

// Array
int arr[] = {1, 2, 3};
auto [p, q, r] = arr;
```

### 9.9 `std::optional` (C++17)

```cpp
#include <optional>

optional<int> findIndex(vector<int>& v, int target) {
    for (int i = 0; i < v.size(); i++)
        if (v[i] == target) return i;
    return nullopt;
}

auto idx = findIndex(v, 42);
if (idx.has_value()) {
    cout << "Found at: " << idx.value() << endl;
}
// Or simply:
if (idx) cout << *idx << endl;
```

### 9.10 `std::variant` (C++17)

```cpp
#include <variant>

variant<int, string> v = 42;
cout << get<int>(v); // 42

v = "hello";
cout << get<string>(v); // "hello"

// Visitor pattern
visit([](auto& arg) {
    cout << arg;
}, v);
```

### 9.11 `std::gcd` and `std::lcm` (C++17)

```cpp
#include <numeric>

gcd(12, 8); // 4
lcm(12, 8); // 24
```

### 9.12 String-Number Conversions

```cpp
#include <string>

// Number to string
string s1 = to_string(42);
string s2 = to_string(3.14);

// String to number
int i = stoi("42");
long l = stol("42");
long long ll = stoll("42");
float f = stof("3.14");
double d = stod("3.14");
```

---

## 10. Performance Tips

1. **Use `reserve()`** when you know the approximate size
2. **Use `emplace_back()`** instead of `push_back()` for complex objects
3. **Pass by reference** to avoid copies: `const vector<int>& v`
4. **Use `ios_base::sync_with_stdio(false)`** and `cin.tie(nullptr)` for fast I/O
5. **Prefer `vector` over `list`** — cache locality matters more than asymptotic complexity for small n
6. **Use `unordered_map`** over `map` when ordering isn't needed
7. **Use `array`** over `vector` when size is fixed
8. **Avoid `endl`** — use `'\n'` instead (endl flushes the buffer)
9. **Use structured bindings** (C++17) for cleaner code
10. **Use `bit` header** (C++20): `popcount`, `countr_zero`, `bit_ceil`

---

*This guide covers the essential STL you need for competitive programming and interviews. Master these, and you'll write solutions faster and with fewer bugs.*
