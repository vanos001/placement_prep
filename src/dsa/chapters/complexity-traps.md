# Complexity Traps: Where O(n) Hides O(n²)

The most dangerous complexity errors aren't in your algorithm design — they're in implementation details that turn a theoretically fast solution into a slow one. This chapter catalogs the most common traps.

---

## Hidden Nested Loops

### String Concatenation in Loops

```python
# TRAP: O(n²) — each concatenation copies the entire string
s = ""
for word in words:
    s += word  # creates a new string of length O(n) each time

# FIX: O(n) — join pre-allocates the result
s = "".join(words)
```

### Substring Search

```cpp
// TRAP: s.find(sub) is O(n*m) in worst case (not O(n))
// If called inside a loop, total complexity balloons
for (int i = 0; i < n; i++)
    if (s.find(queries[i]) != string::npos)  // O(n * m) per call
        count++;

// FIX: Use KMP or Rabin-Karp for all queries, or Aho-Corasick for multiple patterns
```

### List vs. Deque for Queue Operations

```python
# TRAP: list.pop(0) is O(n) — shifts all elements
from collections import deque
q = list()
q.pop(0)  # O(n)

# FIX: deque.popleft() is O(1)
q = deque()
q.popleft()  # O(1)
```

---

## Amortized Operations Hiding Constant Factors

Hash tables are O(1) amortized, but the constant factor and worst case matter:

- **Worst case:** All keys collide → O(n) per operation. With n operations on n elements, worst case is O(n²).
- **Resizing overhead:** A hash map with 10^6 insertions spends significant time on rehashing. The amortized O(1) doesn't tell the full story for a single large batch.
- **String hashing:** Hashing a string of length k costs O(k), not O(1). Using strings as hash keys in a loop over n strings of length k gives O(nk), not O(n).

---

## Recursion Tree Complexity Mistakes

### The Master Theorem Trap

Not all divide-and-conquer follows the Master Theorem. If subproblems **overlap** (like Fibonacci recursion), the recurrence `T(n) = 2T(n-1) + O(1)` gives O(2^n), not the O(n) you might expect from seeing "divide by 2."

### Incorrect Branching Factor

```python
# Thinking: "I explore at most 2 options at each level, so it's O(2^n)"
# Reality: The branching factor might not be constant
# If branching factor grows with n, complexity could be O(n!) or worse
```

Always draw the recursion tree for small n (n=3, 4) and count the nodes before generalizing.

---

## Sorting Hidden Inside API Calls

Many language operations hide a sort:

| Operation | Hidden Cost |
|---|---|
| `collections.Counter(arr).most_common(k)` | O(n log n) if k is large |
| `sorted(set(arr))` | O(n log n) |
| `heapq.nlargest(k, arr)` | O(n log k) — often assumed O(n) |
| `bisect.insort(arr, x)` | O(n) for list insertion |
| Dictionary key iteration order | No guaranteed order in older Python; insertion order in 3.7+ |

**Interview trap:** "My solution is O(n) because I just iterate through the map." But building the map was O(n log n) due to sorted insertion.

---

## Copying Containers Unnecessarily

```cpp
// TRAP: vector passed by value copies O(n) elements
void process(vector<int> arr) {  // O(n) copy!
    sort(arr.begin(), arr.end());
}

// FIX: pass by reference
void process(vector<int>& arr) {
    sort(arr.begin(), arr.end());
}

// TRAP: returning vector by value from a function called in a loop
vector<int> getSlice(const vector<int>& v, int l, int r) {
    return vector<int>(v.begin() + l, v.begin() + r);  // O(r-l) copy
}
// Calling this n times in a loop = O(n²)
```

---

## Iterator Invalidation

```cpp
// TRAP: erasing while iterating over a vector invalidates the iterator
for (auto it = v.begin(); it != v.end(); it++) {
    if (*it == target) v.erase(it);  // UB: it is invalidated
}

// FIX: erase returns the next valid iterator
for (auto it = v.begin(); it != v.end(); ) {
    if (*it == target) it = v.erase(it);
    else it++;
}
```

This doesn't change time complexity but causes crashes. In interviews, it's a correctness trap that wastes debugging time.

---

## Database and Network Complexity Masking

In system design + coding interviews:

- **A single SQL query can be O(n) or O(n log n)** — the database is doing the work
- **Network latency** makes O(1) API calls take 50-200ms each. Calling an API in a loop of 10^5 items = 50+ seconds
- **Batch operations** exist for a reason: one bulk query vs. 10^5 individual queries

---

## The "Looks Linear" Checklist

Before claiming O(n), verify:

1. **Are there any nested function calls?** Even O(1) functions called n times in a loop are O(n), but O(n) functions called n times are O(n²).
2. **Am I creating new objects in a loop?** Each allocation + initialization has a cost.
3. **Am I using a data structure with hidden costs?** (hash map, set, priority queue)
4. **Am I comparing or hashing strings/containers?** These aren't O(1).
5. **Is the input being modified/copyied?** Pass by reference, not by value.

---

## Interview Questions

1. **Is `s += c` O(1) or O(n) in Python?** Explain the difference between CPython's optimization and the general guarantee.

2. **Your solution uses a hash set for O(1) lookups. What is the worst-case complexity? When does it occur?**

3. **You call `sorted(arr)` once and then do O(n) work. Is your overall complexity O(n log n)?** What if `sorted()` is called inside a loop?

4. **Analyze the complexity of this code:**
   ```python
   for i in range(n):
       s = "".join(str(x) for x in arr[:i])
   ```
   **What is it and why?**

5. **You use `bisect.insort()` in a loop of n iterations. What is the total complexity?**

6. **A function processes n items, each requiring a hash of a string of average length k. What is the complexity?**

7. **Explain why `list.pop(0)` is O(n) and `deque.popleft()` is O(1).**

8. **Your recursive function calls itself twice with n-1 and n-2. What is the complexity?** How does memoization change it?

9. **You call an O(n) function inside a loop that runs O(log n) times. Is the total O(n log n)?** What if the loop variable affects the argument size of the function?

10. **An API endpoint returns data for one user in 100ms. You need data for 10,000 users. How do you avoid the O(n) latency trap?**