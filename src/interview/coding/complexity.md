# Complexity Analysis: Complete Guide

## 📊 Big-O Notation Hierarchy

```
O(1) < O(log n) < O(√n) < O(n) < O(n log n) < O(n²) < O(2ⁿ) < O(n!)

Excellent ───────────────────────────────────────────────► Terrible

O(1)       Constant    Hash lookup, array access
O(log n)   Logarithmic Binary search, balanced BST ops
O(√n)      Sublinear   Prime factorization
O(n)       Linear      Single pass through array
O(n log n) Linearithmic Merge sort, heap sort
O(n²)      Quadratic   Nested loops, bubble sort
O(2ⁿ)      Exponential Subsets, recursive Fibonacci
O(n!)      Factorial   Permutations, brute force TSP
```

## 🔢 Common Data Structure Operations

### Arrays
| Operation | Static Array | Dynamic Array |
|-----------|-------------|---------------|
| Access | O(1) | O(1) |
| Search | O(n) | O(n) |
| Append | N/A | O(1)* |
| Insert | O(n) | O(n) |
| Delete | O(n) | O(n) |

*Amortized

### Linked Lists
| Operation | Singly | Doubly |
|-----------|--------|--------|
| Access by index | O(n) | O(n) |
| Search | O(n) | O(n) |
| Insert at head | O(1) | O(1) |
| Insert at tail | O(n) | O(1) |
| Delete at head | O(1) | O(1) |
| Delete by reference | O(n) | O(1) |

### Hash Maps
| Operation | Average | Worst Case |
|-----------|---------|------------|
| Insert | O(1) | O(n) |
| Delete | O(1) | O(n) |
| Search | O(1) | O(n) |

### Trees
| Operation | BST (avg) | BST (worst) | Balanced BST |
|-----------|-----------|-------------|--------------|
| Search | O(log n) | O(n) | O(log n) |
| Insert | O(log n) | O(n) | O(log n) |
| Delete | O(log n) | O(n) | O(log n) |

### Heaps
| Operation | Binary Heap |
|-----------|------------|
| Insert | O(log n) |
| Extract min/max | O(log n) |
| Peek | O(1) |
| Build from array | O(n) |
| Heapify | O(log n) |

### Graphs (V = vertices, E = edges)
| Operation | Adj. List | Adj. Matrix |
|-----------|-----------|-------------|
| Add vertex | O(1) | O(V²) |
| Add edge | O(1) | O(1) |
| Check edge | O(V) | O(1) |
| Find neighbors | O(V) | O(V) |
| BFS/DFS | O(V + E) | O(V²) |

## 📐 Sorting Algorithms Comparison

| Algorithm | Best | Average | Worst | Space | Stable | In-Place |
|-----------|------|---------|-------|-------|--------|----------|
| Bubble Sort | O(n) | O(n²) | O(n²) | O(1) | Yes | Yes |
| Selection Sort | O(n²) | O(n²) | O(n²) | O(1) | No | Yes |
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) | Yes | Yes |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes | No |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No | Yes |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No | Yes |
| Counting Sort | O(n + k) | O(n + k) | O(n + k) | O(k) | Yes | No |
| Radix Sort | O(nk) | O(nk) | O(nk) | O(n + k) | Yes | No |

**When to use what:**
- **Merge Sort:** When stability matters, linked lists, external sort
- **Quick Sort:** General purpose, best average case, in-place
- **Heap Sort:** Guaranteed O(n log n), in-place, but not stable
- **Insertion Sort:** Nearly sorted data, small arrays (< 50 elements)
- **Counting/Radix:** Integer data with known range

## 🧮 Amortized Analysis

### What is Amortized Analysis?
Average performance of each operation over a **sequence** of operations, not worst-case of single operation.

### Dynamic Array Example
```
Append operations: [1] [2] [3] [4] [5] [6] [7] [8]
Capacity changes:   1   2   2   4   4   4   4   8
Copy operations:    0   1   0   2   0   0   0   4

Total copies for 8 appends: 1 + 2 + 4 = 7
Amortized cost per append: 7/8 ≈ O(1)
```

### Key Insight
Individual operations may be O(n), but over n operations the total is O(n), so amortized is O(1).

## 🔍 Analyzing Code Complexity

### Nested Loops
```python
# O(n²) - Both loops depend on n
for i in range(n):
    for j in range(n):
        print(i, j)

# O(n * m) - Different sizes
for i in range(n):
    for j in range(m):
        print(i, j)

# O(n) - Inner loop doesn't start from 0
for i in range(n):
    for j in range(i, n):  # Sum = n + (n-1) + ... + 1 = n(n+1)/2
        print(i, j)        # Actually O(n²)
```

### Recursion
```python
# O(2ⁿ) - Each call branches into 2
def fib(n):
    if n <= 1: return n
    return fib(n-1) + fib(n-2)

# O(n) - Single branch, linear recursion
def factorial(n):
    if n <= 1: return 1
    return n * factorial(n-1)

# O(log n) - Halving each time
def binary_search(arr, target):
    mid = len(arr) // 2
    if arr[mid] == target: return mid
    elif arr[mid] < target: return binary_search(arr[mid+1:], target)
    else: return binary_search(arr[:mid], target)

# O(n log n) - Divide and conquer (merge sort pattern)
def merge_sort(arr):
    if len(arr) <= 1: return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)
```

### Master Theorem
For recurrences of the form: T(n) = aT(n/b) + O(nᵈ)

```
If a < bᵈ:  T(n) = O(nᵈ)
If a = bᵈ:  T(n) = O(nᵈ log n)
If a > bᵈ:  T(n) = O(n^(log_b a))

Examples:
- Binary Search: T(n) = T(n/2) + O(1) → a=1, b=2, d=0 → O(log n)
- Merge Sort: T(n) = 2T(n/2) + O(n) → a=2, b=2, d=1 → O(n log n)
- Strassen: T(n) = 7T(n/2) + O(n²) → a=7, b=2, d=2 → O(n^2.81)
```

## ⚖️ Space Complexity

### Common Space Patterns
```
O(1)       - In-place algorithms, constant variables
O(log n)   - Recursive call stack (binary search)
O(n)       - New array, hash map, recursive stack (linear)
O(n²)      - 2D matrix, adjacency matrix
O(n + m)   - Graph adjacency list
```

### Space-Time Trade-offs
| Trade-off | Example |
|-----------|---------|
| Hash map for O(1) lookup | Two Sum (space for speed) |
| Memoization | Fibonacci (cache for recomputation) |
| Sorting first | Two Sum II (sort for two-pointer) |
| Bit manipulation | Finding duplicates (space-efficient) |

## 📋 Quick Reference: Common Operations

```
Operation              Time        Space
─────────────────────────────────────────
Array access           O(1)        -
Array search           O(n)        -
Binary search          O(log n)    O(1) iterative / O(log n) recursive
Hash lookup            O(1) avg    O(n)
BST insert/search      O(log n)    O(1)
Heap insert            O(log n)    O(1)
Heap extract           O(log n)    O(1)
BFS/DFS                O(V+E)     O(V)
Dijkstra               O((V+E)logV) O(V)
Topological sort       O(V+E)     O(V)
Union Find (amortized) O(α(n))    O(n)
```

## 🎯 Interview Tips for Complexity

1. **Always state complexity** after writing your solution
2. **Analyze both time and space**
3. **Consider best, average, and worst cases** when relevant
4. **Use amortized analysis** for dynamic arrays and union-find
5. **Mention the trade-off** if you're using extra space for speed

## 🔗 Cross-References

- [Data Structures](./data-structures.md) — Operations and their complexities
- [Problem Patterns](./patterns.md) — Complexity of each pattern
- [Coding Framework](./framework.md) — When to optimize
- [OS Questions](../os-questions.md) — Scheduling algorithm complexities
