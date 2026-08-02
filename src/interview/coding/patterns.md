# Coding Interview Patterns

> *"The ability to recognize patterns is what separates good programmers from great ones."*

## 🎯 Why Learn Patterns?

**90% of coding interview problems** fall into ~15 recurring patterns. Learning these patterns lets you:
- Recognize problem types quickly
- Apply proven solutions instead of reinventing
- Reduce time to solution from 40 minutes to 15-20
- Handle variations and follow-ups confidently

---

## 1. Two Pointers

### When to Use
- Sorted arrays
- Finding pairs with specific properties
- Removing duplicates
- Partitioning arrays

### Template
```python
def two_pointers(arr):
    left, right = 0, len(arr) - 1
    while left < right:
        # Process based on condition
        if condition_met(arr[left], arr[right]):
            # Found answer or move both
            left += 1
            right -= 1
        elif need_larger:
            left += 1
        else:
            right -= 1
```

### Classic Problems
| Problem | Difficulty | Key Insight |
|---------|-----------|-------------|
| Two Sum II (sorted) | Easy | Move pointer based on sum vs target |
| 3Sum | Medium | Fix one, two pointers for rest |
| Container With Most Water | Medium | Move the shorter line inward |
| Trapping Rain Water | Hard | Track max from both ends |
| Remove Duplicates | Easy | Slow/fast pointer |

### Example: Container With Most Water
```python
def maxArea(height):
    left, right = 0, len(height) - 1
    max_area = 0
    while left < right:
        area = min(height[left], height[right]) * (right - left)
        max_area = max(max_area, area)
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_area
```

---

## 2. Sliding Window

### When to Use
- Contiguous subarray/substring problems
- Finding max/min/average of subarray of size K
- Longest/shortest substring with condition

### Template
```python
def sliding_window(s):
    window = {}  # or set, or counter
    left = 0
    result = 0

    for right in range(len(s)):
        # Expand window: add s[right]
        window[s[right]] = window.get(s[right], 0) + 1

        # Shrink window when invalid
        while window_invalid:
            window[s[left]] -= 1
            if window[s[left]] == 0:
                del window[s[left]]
            left += 1

        # Update result
        result = max(result, right - left + 1)

    return result
```

### Classic Problems
| Problem | Difficulty | Window Condition |
|---------|-----------|-----------------|
| Max Subarray of Size K | Easy | Fixed size K |
| Longest Substring Without Repeating | Medium | No duplicates |
| Minimum Window Substring | Hard | Contains all chars of target |
| Longest Repeating Character Replacement | Medium | At most K replacements |
| Permutation in String | Medium | Fixed-size anagram |
| Fruits Into Baskets | Medium | At most 2 distinct |

### Example: Longest Substring Without Repeating Characters
```python
def lengthOfLongestSubstring(s):
    char_set = set()
    left = 0
    max_len = 0

    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)

    return max_len
```

---

## 3. Fast & Slow Pointers

### When to Use
- Cycle detection in linked lists/arrays
- Finding middle of linked list
- Determining if number is happy

### Template
```python
def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False

def find_middle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
```

### Classic Problems
- Linked List Cycle (I & II)
- Happy Number
- Find Middle of Linked List
- Palindrome Linked List
- Reorder List

---

## 4. Merge Intervals

### When to Use
- Overlapping intervals
- Meeting room problems
- Range merging

### Template
```python
def merge_intervals(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        if start <= merged[-1][1]:  # overlap
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    return merged
```

### Classic Problems
| Problem | Difficulty | Variation |
|---------|-----------|-----------|
| Merge Intervals | Medium | Basic merge |
| Insert Interval | Medium | Insert + merge |
| Non-overlapping Intervals | Medium | Greedy removal |
| Meeting Rooms | Easy | Any overlap? |
| Meeting Rooms II | Medium | Min rooms needed |
| Interval List Intersections | Medium | Find all overlaps |

---

## 5. Cyclic Sort

### When to Use
- Array contains numbers in range [1, N]
- Finding missing/duplicate numbers
- Constant space requirement

### Template
```python
def cyclic_sort(nums):
    i = 0
    while i < len(nums):
        correct = nums[i] - 1
        if nums[i] != nums[correct]:
            nums[i], nums[correct] = nums[correct], nums[i]
        else:
            i += 1
    return nums

# Find missing number
def find_missing(nums):
    i = 0
    while i < len(nums):
        correct = nums[i]
        if nums[i] < len(nums) and nums[i] != nums[correct]:
            nums[i], nums[correct] = nums[correct], nums[i]
        else:
            i += 1
    for i in range(len(nums)):
        if nums[i] != i:
            return i
    return len(nums)
```

### Classic Problems
- Missing Number
- Find All Numbers Disappeared in Array
- Find the Duplicate Number
- First Missing Positive
- Find All Duplicates in Array

---

## 6. In-Place Reversal of Linked List

### When to Use
- Reverse entire or portion of linked list
- Palindrome check
- Reorder problems

### Template: Reverse Between Positions
```python
def reverse_between(head, left, right):
    if not head or left == right:
        return head

    dummy = ListNode(0)
    dummy.next = head
    prev = dummy

    for _ in range(left - 1):
        prev = prev.next

    curr = prev.next
    for _ in range(right - left):
        temp = curr.next
        curr.next = temp.next
        temp.next = prev.next
        prev.next = temp

    return dummy.next
```

### Classic Problems
- Reverse Linked List
- Reverse Linked List II (between positions)
- Reverse Nodes in k-Group
- Palindrome Linked List
- Swap Nodes in Pairs

---

## 7. Tree BFS (Level Order)

### When to Use
- Level-by-level processing
- Shortest path in tree
- Zigzag traversal

### Template
```python
from collections import deque

def level_order(root):
    if not root:
        return []
    result = []
    queue = deque([root])

    while queue:
        level_size = len(queue)
        level = []
        for _ in range(level_size):
            node = queue.popleft()
            level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)

    return result
```

### Classic Problems
- Binary Tree Level Order Traversal
- Binary Tree Zigzag Level Order
- Minimum Depth of Binary Tree
- Binary Tree Right Side View
- Average of Levels in Binary Tree
- Populating Next Right Pointers

---

## 8. Tree DFS

### When to Use
- Path finding
- Validation (BST, balanced)
- All paths enumeration

### Template
```python
def dfs(root, path, result):
    if not root:
        return

    # Process current node
    path.append(root.val)

    if is_leaf(root) and meets_condition(path):
        result.append(list(path))
    else:
        dfs(root.left, path, result)
        dfs(root.right, path, result)

    path.pop()  # backtrack
```

### Classic Problems
- Path Sum (I, II, III)
- All Paths for Sum
- Binary Tree Paths
- Sum of Path Numbers
- Validate BST
- Diameter of Binary Tree

---

## 9. Subsets / Combinations / Permutations (Backtracking)

### When to Use
- Generate all subsets, combinations, or permutations
- Constraint satisfaction problems
- Decision tree exploration

### Templates
```python
# Subsets
def subsets(nums):
    result = []
    def backtrack(start, path):
        result.append(list(path))
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result

# Combinations
def combine(n, k):
    result = []
    def backtrack(start, path):
        if len(path) == k:
            result.append(list(path))
            return
        for i in range(start, n + 1):
            path.append(i)
            backtrack(i + 1, path)
            path.pop()
    backtrack(1, [])
    return result

# Permutations
def permute(nums):
    result = []
    def backtrack(path, remaining):
        if not remaining:
            result.append(list(path))
            return
        for i in range(len(remaining)):
            path.append(remaining[i])
            backtrack(path, remaining[:i] + remaining[i+1:])
            path.pop()
    backtrack([], nums)
    return result
```

### Classic Problems
- Subsets (I, II)
- Combinations (I, II)
- Permutations (I, II)
- Combination Sum (I, II, III)
- Palindrome Partitioning
- Letter Combinations of Phone Number
- N-Queens
- Sudoku Solver
- Word Search

---

## 10. Dynamic Programming

### When to Use
- Optimal substructure
- Overlapping subproblems
- Counting problems
- Min/max optimization

### Approaches
```
1. Top-Down (Memoization)
   - Recursive with cache
   - Natural thinking
   - Easier to write initially

2. Bottom-Up (Tabulation)
   - Iterative with table
   - Better space efficiency
   - No stack overflow risk
```

### Common DP Patterns

#### 1D DP
```python
# Fibonacci / Climbing Stairs
def climb_stairs(n):
    if n <= 2: return n
    dp = [0] * (n + 1)
    dp[1], dp[2] = 1, 2
    for i in range(3, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]

# Kadane's Algorithm - Maximum Subarray
def max_subarray(nums):
    max_sum = curr_sum = nums[0]
    for num in nums[1:]:
        curr_sum = max(num, curr_sum + num)
        max_sum = max(max_sum, curr_sum)
    return max_sum
```

#### 2D DP
```python
# Longest Common Subsequence
def lcs(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]
```

### Classic DP Problems
| Category | Problems |
|----------|----------|
| **1D DP** | Climbing Stairs, House Robber, Decode Ways, Coin Change |
| **2D DP** | LCS, Edit Distance, Unique Paths, Knapsack |
| **String DP** | Palindrome Substrings, Word Break, Interleaving String |
| **Interval DP** | Burst Balloons, Matrix Chain Multiplication |
| **Game DP** | Stone Game, Nim Game |

---

## 11. Top K Elements (Heap)

### When to Use
- Find K largest/smallest elements
- K most frequent elements
- Merge K sorted lists

### Template
```python
import heapq

def top_k_frequent(nums, k):
    count = {}
    for num in nums:
        count[num] = count.get(num, 0) + 1

    return heapq.nlargest(k, count.keys(), key=count.get)

# Using min heap of size K
def find_kth_largest(nums, k):
    heap = []
    for num in nums:
        heapq.heappush(heap, num)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
```

### Classic Problems
- Kth Largest Element
- Top K Frequent Elements
- K Closest Points to Origin
- Find K Pairs with Smallest Sums
- Merge K Sorted Lists
- Task Scheduler

---

## 12. K-Way Merge

### When to Use
- Merge K sorted arrays/lists
- Find smallest range covering elements from K lists

### Template
```python
import heapq

def merge_k_sorted(lists):
    heap = []
    result = []

    # Initialize: push first element of each list
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))

    while heap:
        val, list_idx, elem_idx = heapq.heappop(heap)
        result.append(val)

        if elem_idx + 1 < len(lists[list_idx]):
            next_val = lists[list_idx][elem_idx + 1]
            heapq.heappush(heap, (next_val, list_idx, elem_idx + 1))

    return result
```

---

## 13. Topological Sort

### When to Use
- Dependency resolution
- Task scheduling with prerequisites
- Course schedule problems

### Template (Kahn's Algorithm - BFS)
```python
from collections import deque, defaultdict

def topological_sort(num_nodes, edges):
    graph = defaultdict(list)
    in_degree = [0] * num_nodes

    for src, dst in edges:
        graph[src].append(dst)
        in_degree[dst] += 1

    queue = deque([i for i in range(num_nodes) if in_degree[i] == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != num_nodes:
        return []  # Cycle detected
    return result
```

### Classic Problems
- Course Schedule (I, II)
- Alien Dictionary
- Parallel Tasks
- All Possible Recipes

---

## 14. Union Find (Disjoint Set)

### When to Use
- Connected components
- Detecting cycles in undirected graphs
- Grouping elements

### Template
```python
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True
```

### Classic Problems
- Number of Connected Components
- Redundant Connection
- Accounts Merge
- Surrounded Regions
- Making a Large Island

---

## 15. Monotonic Stack

### When to Use
- Next greater/smaller element
- Daily temperatures
- Histogram problems

### Template
```python
def next_greater_element(nums):
    n = len(nums)
    result = [-1] * n
    stack = []  # indices

    for i in range(n):
        while stack and nums[i] > nums[stack[-1]]:
            idx = stack.pop()
            result[idx] = nums[i]
        stack.append(i)

    return result
```

### Classic Problems
- Next Greater Element (I, II)
- Daily Temperatures
- Largest Rectangle in Histogram
- Trapping Rain Water
- Stock Span Problem

---

## 🎯 Pattern Recognition Guide

```
┌─────────────────────────────────────────────────────────┐
│              HOW TO IDENTIFY THE PATTERN                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  "Sorted array + find pair"          → Two Pointers    │
│  "Contiguous subarray/substring"     → Sliding Window  │
│  "Cycle in linked list"              → Fast/Slow Ptr   │
│  "Overlapping ranges"                → Merge Intervals │
│  "Numbers 1 to N in array"           → Cyclic Sort     │
│  "Reverse linked list portion"       → In-Place Rev    │
│  "Level by level in tree"            → Tree BFS        │
│  "All paths in tree"                 → Tree DFS        │
│  "Generate all combinations"         → Backtracking    │
│  "Min/max/count with choices"        → Dynamic Prog    │
│  "K largest/smallest"                → Top K (Heap)    │
│  "Merge K sorted lists"              → K-Way Merge     │
│  "Dependencies/prerequisites"        → Topo Sort       │
│  "Connected components/grouping"     → Union Find      │
│  "Next greater/smaller element"      → Monotonic Stack │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🔗 Cross-References

- [Data Structures](./data-structures.md) — Complete reference for all structures
- [Complexity Analysis](./complexity.md) — Big-O for all patterns
- [Coding Framework](./framework.md) — Step-by-step problem-solving approach
- [System Design](../system-design/framework.md) — Architecture-level patterns
