# Python Cheat Sheet for Interviews

## Data Structures

```python
# List - ordered, mutable, duplicates
lst = [1, 2, 3]
lst.append(4)        # O(1)
lst.pop()            # O(1) from end
lst.insert(0, x)     # O(n)
lst.sort()           # O(n log n)

# Dictionary - ordered (3.7+), mutable, unique keys
d = {"key": "value"}
d.get("key", default)  # O(1) average
d.pop("key")           # O(1) average
for k, v in d.items(): pass

# Set - unordered, mutable, unique
s = {1, 2, 3}
s.add(4)             # O(1)
s.remove(4)          # O(1)
s | t                # union
s & t                # intersection
s - t                # difference

# Tuple - ordered, immutable
t = (1, 2, 3)
t[0]                 # O(1)
```

## Collections Module

```python
from collections import defaultdict, Counter, deque, OrderedDict

# defaultdict - auto-create missing keys
dd = defaultdict(list)
dd["key"].append(1)  # No KeyError

# Counter - counting elements
c = Counter([1,1,2,3,3,3])  # {3:3, 1:2, 2:1}
c.most_common(2)             # [(3,3), (1,2)]

# deque - double-ended queue
dq = deque()
dq.append(x)         # O(1) right
dq.appendleft(x)     # O(1) left
dq.pop()             # O(1) right
dq.popleft()         # O(1) left
```

## Heap (Priority Queue)

```python
import heapq

# Min heap
heap = []
heapq.heappush(heap, 3)
heapq.heappush(heap, 1)
min_val = heapq.heappop(heap)  # 1

# Max heap (negate values)
heap = []
heapq.heappush(heap, -3)
max_val = -heapq.heappop(heap)  # 3

# Top K elements
top_k = heapq.nlargest(k, iterable)
bottom_k = heapq.nsmallest(k, iterable)
```

## Sorting

```python
# Custom sort
lst.sort(key=lambda x: x[1])           # In-place
sorted(lst, key=lambda x: (-x[0], x[1]))  # New list

# Multiple criteria
students.sort(key=lambda s: (-s.grade, s.name))
```

## Binary Search

```python
import bisect

# Sorted array
arr = [1, 3, 5, 7, 9]
idx = bisect.bisect_left(arr, 5)   # 2 (first >= 5)
idx = bisect.bisect_right(arr, 5)  # 3 (first > 5)

# Manual binary search
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target: return mid
        elif arr[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1
```

## Graph Representations

```python
# Adjacency List
graph = defaultdict(list)
graph[u].append(v)

# BFS
from collections import deque
def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

# DFS (recursive)
def dfs(graph, node, visited=None):
    if visited is None: visited = set()
    visited.add(node)
    for neighbor in graph[node]:
        if neighbor not in visited:
            dfs(graph, neighbor, visited)
```

## Common Patterns

```python
# Sliding Window
def sliding_window(arr, k):
    window_sum = sum(arr[:k])
    max_sum = window_sum
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i-k]
        max_sum = max(max_sum, window_sum)
    return max_sum

# Two Pointers
def two_sum_sorted(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo < hi:
        s = arr[lo] + arr[hi]
        if s == target: return [lo, hi]
        elif s < target: lo += 1
        else: hi -= 1

# Trie
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False
```

## Interview Tips

```python
# Use defaultdict instead of checking keys
# Use Counter for frequency counting
# Use heapq for top-k / priority problems
# Use bisect for sorted array problems
# Use deque for BFS / sliding window
# Use set for O(1) lookup
# Use zip() for parallel iteration
# Use enumerate() for index+value
# Use sorted() with key for custom sorting
# List comprehension > map/filter for readability
```

## Time Complexity Quick Reference

| Operation | List | Dict | Set | Deque |
|-----------|------|------|-----|-------|
| Access | O(1) | O(1) | - | O(n) |
| Search | O(n) | O(1) | O(1) | O(n) |
| Insert | O(n) | O(1) | O(1) | O(1) |
| Delete | O(n) | O(1) | O(1) | O(1) |
| Append | O(1) | - | O(1) | O(1) |
