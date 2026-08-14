# 20 Essential Coding Patterns — Quick Reference

This guide covers the 20 patterns that solve the vast majority of interview and OA problems. For detailed implementations, see the [pattern deep-dives](./README.md) and the [patterns reference](./patterns.md).

## 1. Two Pointers

**Recognize:** Sorted array, pair/triplet finding, palindrome, partition.

```python
def two_pointers_template(arr, target):
    left, right = 0, len(arr) - 1
    while left < right:
        s = arr[left] + arr[right]
        if s == target: return [left, right]
        elif s < target: left += 1
        else: right -= 1
```
Complexity: O(n) time, O(1) space.

---

## 2. Sliding Window

**Recognize:** Contiguous subarray/substring, "longest/shortest subarray with condition."

```python
def sliding_window_template(s, k):
    left = 0
    result = 0
    window = {}
    for right in range(len(s)):
        # add s[right] to window
        while invalid(window):  # shrink
            # remove s[left]
            left += 1
        result = max(result, right - left + 1)
    return result
```
Complexity: O(n) time, O(k) space (k = window size).

---

## 3. Fast & Slow Pointers

**Recognize:** Linked list cycle, middle element, duplicate in array with values in [1, n].

```python
def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast: return True
    return False
```
Complexity: O(n) time, O(1) space.

---

## 4. Merge Intervals

**Recognize:** Overlapping ranges, meeting rooms, scheduling conflicts.

```python
def merge(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged
```
Complexity: O(n log n) time, O(n) space.

---

## 5. Cyclic Sort

**Recognize:** Array with numbers in range [1, n] or [0, n-1], find missing/duplicate.

```python
def cyclic_sort(nums):
    i = 0
    while i < len(nums):
        correct = nums[i] - 1
        if nums[i] != nums[correct]:
            nums[i], nums[correct] = nums[correct], nums[i]
        else:
            i += 1
```
Complexity: O(n) time, O(1) space.

---

## 6. In-place Reversal of Linked List

**Recognize:** Reverse a linked list (full or partial), reverse nodes in k-groups, rotate list.

```python
def reverse(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
```
Complexity: O(n) time, O(1) space.

---

## 7. Tree BFS

**Recognize:** Level-order traversal, shortest path in unweighted graph/ tree, zigzag traversal.

```python
from collections import deque
def bfs(root):
    q = deque([root])
    while q:
        for _ in range(len(q)):
            node = q.popleft()
            # process node
            if node.left: q.append(node.left)
            if node.right: q.append(node.right)
```
Complexity: O(n) time, O(w) space (w = max width).

---

## 8. Tree DFS

**Recognize:** Path-based problems, tree properties (diameter, height), backtracking on trees.

```python
def dfs(root, target):
    if not root: return False
    if root.val == target: return True
    return dfs(root.left, target) or dfs(root.right, target)
```
Complexity: O(n) time, O(h) space (h = height).

---

## 9. Top K Elements (Heap)

**Recognize:** "Find K largest/smallest," "Kth element," median from stream, merge K sorted.

```python
import heapq
def top_k(nums, k):
    return heapq.nlargest(k, nums)  # O(n log k), min-heap of size k
```
For Kth largest: min-heap of size K; for Kth smallest: max-heap of size K.
Complexity: O(n log k) time, O(k) space.

---

## 10. Binary Search

**Recognize:** Sorted input, "find element satisfying condition," monotonic predicate, search on answer.

```python
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target: return mid
        elif arr[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1
```
Complexity: O(log n) time, O(1) space.

---

## 11. Backtracking

**Recognize:** "Find all combinations/permutations/subsets," constraint satisfaction (N-Queens, Sudoku).

```python
def backtrack(path, choices, result):
    if is_solution(path):
        result.append(path[:])
        return
    for c in choices:
        if is_valid(c):
            path.append(c)
            backtrack(path, remaining, result)
            path.pop()  # undo
```
Complexity: O(2^n) or O(n!) time, O(n) space.

---

## 12. Dynamic Programming (1D & 2D)

**Recognize:** Optimal substructure, overlapping subproblems, "max/min/number of ways."

**1D:**
```python
def climb_stairs(n):
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b
```

**2D:**
```python
def lcs(s1, s2):
    dp = [[0]*(len(s2)+1) for _ in range(len(s1)+1)]
    for i in range(1, len(s1)+1):
        for j in range(1, len(s2)+1):
            if s1[i-1] == s2[j-1]: dp[i][j] = dp[i-1][j-1] + 1
            else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[-1][-1]
```
Complexity: 1D O(n) time/space; 2D O(m*n) time/space (often optimizable).

---

## 13. Topological Sort

**Recognize:** Course prerequisites, build order, dependency resolution, directed acyclic graph.

```python
from collections import deque, defaultdict
def topo_sort(n, edges):
    graph = defaultdict(list)
    indeg = [0] * n
    for u, v in edges:
        graph[u].append(v)
        indeg[v] += 1
    q = deque([i for i in range(n) if indeg[i] == 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for nb in graph[node]:
            indeg[nb] -= 1
            if indeg[nb] == 0:
                q.append(nb)
    return order if len(order) == n else []
```
Complexity: O(V + E) time, O(V + E) space.

---

## 14. Union-Find

**Recognize:** Connected components, dynamic connectivity, "are A and B in the same group?"

```python
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py: return False
        if self.rank[px] < self.rank[py]: px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]: self.rank[px] += 1
        return True
```
Complexity: O(α(n)) amortized time, O(n) space.

---

## 15. Trie

**Recognize:** Word search, autocomplete, prefix matching, word games.

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()
    def insert(self, word):
        node = self.root
        for c in word:
            if c not in node.children:
                node.children[c] = TrieNode()
            node = node.children[c]
        node.is_end = True
    def search(self, word):
        node = self.root
        for c in word:
            if c not in node.children: return False
            node = node.children[c]
        return node.is_end
```
Complexity: Insert/search O(L) where L = word length; space O(26^L) worst case.

---

## 16. Monotonic Stack

**Recognize:** Next greater/smaller element, daily temperatures, largest rectangle in histogram, remove K digits.

```python
def next_greater(nums):
    result = [-1] * len(nums)
    stack = []  # indices with decreasing values
    for i, val in enumerate(nums):
        while stack and nums[stack[-1]] < val:
            result[stack.pop()] = val
        stack.append(i)
    return result
```
Complexity: O(n) time (each element pushed/popped once), O(n) space.

---

## 17. Monotonic Queue (Deque)

**Recognize:** Sliding window maximum/minimum, constrained window optimization.

```python
from collections import deque
def sliding_window_max(nums, k):
    dq = deque()  # indices, values decreasing
    result = []
    for i, val in enumerate(nums):
        while dq and nums[dq[-1]] < val:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            result.append(nums[dq[0]])
    return result
```
Complexity: O(n) time, O(k) space.

---

## 18. Frequency Counting / Hash Map

**Recognize:** Anagrams, top K frequent, character counting, "group items by property."

```python
from collections import Counter
def top_k_frequent(nums, k):
    count = Counter(nums)
    return [x for x, _ in count.most_common(k)]
```
Complexity: O(n) time, O(n) space.

---

## 19. Prefix Sum

**Recognize:** Range sum queries, subarray sum equals K, equilibrium index, 2D range sum.

```python
def subarray_sum(nums, k):
    prefix = {0: 1}
    curr = 0
    count = 0
    for num in nums:
        curr += num
        count += prefix.get(curr - k, 0)
        prefix[curr] = prefix.get(curr, 0) + 1
    return count
```
Complexity: O(n) time, O(n) space.

---

## 20. Greedy

**Recognize:** "Maximum/minimum number of X," interval scheduling, coin change (canonical), activity selection.

```python
def activity_selection(activities):  # (start, end) pairs
    activities.sort(key=lambda x: x[1])  # sort by end time
    count, last_end = 0, float('-inf')
    for s, e in activities:
        if s >= last_end:
            count += 1
            last_end = e
    return count
```
Complexity: O(n log n) time (due to sort), O(1) space.

---

## Pattern Selection Quick Reference

| Problem Cue | Pattern |
|-------------|---------|
| Sorted array, find pair/triplet | Two Pointers, Binary Search |
| Contiguous subarray/substring | Sliding Window |
| Linked list cycle/middle | Fast & Slow Pointers |
| Linked list reverse/rotate | In-place Reversal |
| Overlapping ranges | Merge Intervals |
| Numbers in [1, n] | Cyclic Sort |
| Level-by-level traversal | Tree BFS |
| Path, property, all solutions | Tree DFS / Backtracking |
| K largest/smallest | Heap |
| Sorted input, monotonic predicate | Binary Search |
| All combos/perms/constraints | Backtracking |
| Optimal + overlapping subproblems | DP |
| Prerequisites, dependencies | Topological Sort |
| Connected components, grouping | Union-Find |
| Words, prefixes, autocomplete | Trie |
| Next greater/smaller element | Monotonic Stack |
| Window maximum/minimum | Monotonic Queue |
| Counting, grouping by property | Hash Map / Counter |
| Range sum, subarray sum | Prefix Sum |
| Maximum/minimum count of X | Greedy |

## Interview Tips

- Spend the first 30 seconds of every problem identifying the pattern — this saves more time than jumping straight into code
- If a problem doesn't fit any single pattern cleanly, it's likely a **combination** of two (e.g., sliding window + hash map, or BFS + topological sort)
- Practice each pattern until you can write the template from memory without looking
- For a deeper dive into individual patterns, see [patterns.md](./patterns.md) and the [pattern-specific guides](./pattern-frequency-counting.md)
