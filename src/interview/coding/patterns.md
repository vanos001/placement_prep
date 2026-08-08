# Coding Interview Patterns

## Overview

Recognizing patterns is the key to solving coding interview problems efficiently. This guide covers the most common patterns that appear repeatedly in technical interviews at top companies.

## Pattern 1: Sliding Window

**When to use:** Problems involving contiguous subarrays/substrings of variable size.

```python
def max_sum_subarray(nums: list, k: int) -> int:
    """Find maximum sum of subarray of size k."""
    window_sum = sum(nums[:k])
    max_sum = window_sum
    
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    
    return max_sum

def longest_substring_without_repeats(s: str) -> int:
    """Find longest substring without repeating characters."""
    seen = {}
    left = 0
    max_len = 0
    
    for right, char in enumerate(s):
        if char in seen and seen[char] >= left:
            left = seen[char] + 1
        seen[char] = right
        max_len = max(max_len, right - left + 1)
    
    return max_len
```

**Problems:** Longest Substring Without Repeating Characters, Minimum Window Substring, Sliding Window Maximum

## Pattern 2: Two Pointers

**When to use:** Sorted arrays, palindrome checking, pair finding.

```python
def two_sum_sorted(nums: list, target: int) -> list:
    """Find two numbers that add up to target in sorted array."""
    left, right = 0, len(nums) - 1
    
    while left < right:
        current_sum = nums[left] + nums[right]
        if current_sum == target:
            return [left, right]
        elif current_sum < target:
            left += 1
        else:
            right -= 1
    
    return []

def three_sum(nums: list) -> list:
    """Find all unique triplets that sum to zero."""
    nums.sort()
    result = []
    
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i-1]:
            continue
        
        left, right = i + 1, len(nums) - 1
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                result.append([nums[i], nums[left], nums[right]])
                while left < right and nums[left] == nums[left+1]:
                    left += 1
                while left < right and nums[right] == nums[right-1]:
                    right -= 1
                left += 1
                right -= 1
    
    return result
```

**Problems:** Two Sum, Three Sum, Container With Most Water, Trapping Rain Water

## Pattern 3: Fast & Slow Pointers

**When to use:** Linked list cycle detection, finding middle element.

```python
def has_cycle(head: ListNode) -> bool:
    """Detect cycle in linked list."""
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False

def find_middle(head: ListNode) -> ListNode:
    """Find middle of linked list."""
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
```

## Pattern 4: Merge Intervals

**When to use:** Overlapping intervals, meeting rooms, range problems.

```python
def merge_intervals(intervals: list) -> list:
    """Merge all overlapping intervals."""
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    
    return merged

def insert_interval(intervals: list, new_interval: list) -> list:
    """Insert new interval and merge overlaps."""
    result = []
    i = 0
    
    # Add intervals before new_interval
    while i < len(intervals) and intervals[i][1] < new_interval[0]:
        result.append(intervals[i])
        i += 1
    
    # Merge overlapping intervals
    while i < len(intervals) and intervals[i][0] <= new_interval[1]:
        new_interval[0] = min(new_interval[0], intervals[i][0])
        new_interval[1] = max(new_interval[1], intervals[i][1])
        i += 1
    result.append(new_interval)
    
    # Add remaining intervals
    while i < len(intervals):
        result.append(intervals[i])
        i += 1
    
    return result
```

## Pattern 5: Cyclic Sort

**When to use:** Problems involving arrays with numbers in range [1, n].

```python
def find_missing_numbers(nums: list) -> list:
    """Find all missing numbers in range [1, n]."""
    i = 0
    while i < len(nums):
        correct = nums[i] - 1
        if nums[i] != nums[correct]:
            nums[i], nums[correct] = nums[correct], nums[i]
        else:
            i += 1
    
    return [i + 1 for i, num in enumerate(nums) if num != i + 1]
```

## Pattern 6: Tree BFS (Level Order)

**When to use:** Level-by-level traversal, shortest path in unweighted graph.

```python
from collections import deque

def level_order(root: TreeNode) -> list:
    """Level-order traversal of binary tree."""
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
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    
    return result
```

## Pattern 7: Tree DFS

**When to use:** Path finding, tree properties, backtracking.

```python
def has_path_sum(root: TreeNode, target_sum: int) -> bool:
    """Check if tree has root-to-leaf path with given sum."""
    if not root:
        return False
    if not root.left and not root.right:
        return root.val == target_sum
    return (has_path_sum(root.left, target_sum - root.val) or
            has_path_sum(root.right, target_sum - root.val))
```

## Pattern 8: Backtracking

**When to use:** Generating combinations, permutations, subsets.

```python
def subsets(nums: list) -> list:
    """Generate all subsets."""
    result = []
    
    def backtrack(start, current):
        result.append(current[:])
        for i in range(start, len(nums)):
            current.append(nums[i])
            backtrack(i + 1, current)
            current.pop()
    
    backtrack(0, [])
    return result

def permutations(nums: list) -> list:
    """Generate all permutations."""
    result = []
    
    def backtrack(current, remaining):
        if not remaining:
            result.append(current[:])
            return
        for i, num in enumerate(remaining):
            current.append(num)
            backtrack(current, remaining[:i] + remaining[i+1:])
            current.pop()
    
    backtrack([], nums)
    return result
```

## Pattern 9: Dynamic Programming

**When to use:** Optimal solutions, overlapping subproblems, counting problems.

```python
# 1D DP
def climb_stairs(n: int) -> int:
    """Number of ways to climb n stairs (1 or 2 steps)."""
    if n <= 2:
        return n
    prev2, prev1 = 1, 2
    for _ in range(3, n + 1):
        prev2, prev1 = prev1, prev1 + prev2
    return prev1

# 2D DP
def lcs(text1: str, text2: str) -> int:
    """Longest common subsequence."""
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

## Pattern 10: Topological Sort

**When to use:** Dependency resolution, course scheduling, build order.

```python
from collections import deque, defaultdict

def topological_sort(numCourses: int, prerequisites: list) -> list:
    """Course schedule - topological sort using BFS."""
    graph = defaultdict(list)
    in_degree = [0] * numCourses
    
    for course, prereq in prerequisites:
        graph[prereq].append(course)
        in_degree[course] += 1
    
    queue = deque([i for i in range(numCourses) if in_degree[i] == 0])
    order = []
    
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    return order if len(order) == numCourses else []
```

## Pattern 11: Binary Search

**When to use:** Sorted data, search space reduction.

```python
def search_rotated(nums: list, target: int) -> int:
    """Search in rotated sorted array."""
    left, right = 0, len(nums) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        
        if nums[left] <= nums[mid]:  # Left half sorted
            if nums[left] <= target < nums[mid]:
                right = mid - 1
            else:
                left = mid + 1
        else:  # Right half sorted
            if nums[mid] < target <= nums[right]:
                left = mid + 1
            else:
                right = mid - 1
    
    return -1
```

## Pattern 12: Heap / Priority Queue

**When to use:** Top K elements, merge K sorted, scheduling.

```python
import heapq

def top_k_frequent(nums: list, k: int) -> list:
    """Find k most frequent elements."""
    count = {}
    for num in nums:
        count[num] = count.get(num, 0) + 1
    
    return heapq.nlargest(k, count.keys(), key=count.get)

def merge_k_sorted(lists: list) -> list:
    """Merge k sorted lists."""
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))
    
    result = []
    while heap:
        val, list_idx, elem_idx = heapq.heappop(heap)
        result.append(val)
        if elem_idx + 1 < len(lists[list_idx]):
            next_val = lists[list_idx][elem_idx + 1]
            heapq.heappush(heap, (next_val, list_idx, elem_idx + 1))
    
    return result
```

## Summary Table

| Pattern | Key Technique | Time | Space |
|---------|--------------|------|-------|
| Sliding Window | Window expansion/contraction | O(n) | O(1) or O(k) |
| Two Pointers | Converging pointers | O(n) | O(1) |
| Fast & Slow | Different speed traversal | O(n) | O(1) |
| Merge Intervals | Sort + merge | O(n log n) | O(n) |
| Cyclic Sort | In-place swap | O(n) | O(1) |
| Tree BFS | Queue-based level traversal | O(n) | O(w) |
| Tree DFS | Recursive/stack traversal | O(n) | O(h) |
| Backtracking | Explore + undo | O(2^n) | O(n) |
| DP | Memoization/tabulation | O(n²) typical | O(n²) typical |
| Topological Sort | BFS/DFS on DAG | O(V+E) | O(V+E) |
| Binary Search | Halve search space | O(log n) | O(1) |
| Heap | Priority-based extraction | O(n log k) | O(k) |

## Related Topics

- [Coding Overview](./README.md) — Interview coding preparation
- [Data Structures](../../os/) — Underlying data structures
- [System Design](../system-design/) — System design interviews
