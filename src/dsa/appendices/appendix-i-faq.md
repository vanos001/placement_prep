# Appendix I: Frequently Asked Interview Questions

The top 100 most frequently asked DSA interview questions, organized by topic, with brief solution hints.

---

## Arrays & Strings (1-15)

### 1. Two Sum
**Problem:** Find two numbers that add up to a target.
**Hint:** Use a hash map. For each element, check if `target - element` exists in the map.
**Time:** O(n), **Space:** O(n)

### 2. Best Time to Buy and Sell Stock
**Problem:** Find the maximum profit from one buy and one sell.
**Hint:** Track the minimum price seen so far. At each step, calculate profit if selling today.
**Time:** O(n), **Space:** O(1)

### 3. Contains Duplicate
**Problem:** Check if array contains duplicates.
**Hint:** Use a set. If `insert` returns false, duplicate found.
**Time:** O(n), **Space:** O(n)

### 4. Product of Array Except Self
**Problem:** Return array where each element is product of all other elements.
**Hint:** Build prefix products and suffix products. Or use output array as prefix, then multiply by suffix in second pass.
**Time:** O(n), **Space:** O(1) extra

### 5. Maximum Subarray (Kadane's Algorithm)
**Problem:** Find the contiguous subarray with the largest sum.
**Hint:** At each element, decide: extend the previous subarray or start a new one. `dp[i] = max(arr[i], dp[i-1] + arr[i])`
**Time:** O(n), **Space:** O(1)

### 6. Maximum Product Subarray
**Problem:** Find the contiguous subarray with the largest product.
**Hint:** Track both max and min at each position (negative × negative = positive).
**Time:** O(n), **Space:** O(1)

### 7. Find Minimum in Rotated Sorted Array
**Problem:** Find the minimum element in a rotated sorted array.
**Hint:** Binary search. If `arr[mid] > arr[hi]`, minimum is in right half. Otherwise, left half.
**Time:** O(log n), **Space:** O(1)

### 8. Search in Rotated Sorted Array
**Problem:** Search for a target in a rotated sorted array.
**Hint:** Binary search. Determine which half is sorted, then check if target is in that range.
**Time:** O(log n), **Space:** O(1)

### 9. 3Sum
**Problem:** Find all unique triplets that sum to zero.
**Hint:** Sort, then for each element, use two pointers to find pairs that sum to its negative. Skip duplicates.
**Time:** O(n²), **Space:** O(1)

### 10. Container With Most Water
**Problem:** Find two lines that together with the x-axis form a container holding the most water.
**Hint:** Two pointers at both ends. Move the shorter pointer inward.
**Time:** O(n), **Space:** O(1)

### 11. Group Anagrams
**Problem:** Group strings that are anagrams of each other.
**Hint:** Sort each string and use the sorted version as a key in a hash map.
**Time:** O(n × k log k), **Space:** O(n × k)

### 12. Longest Substring Without Repeating Characters
**Problem:** Find the length of the longest substring without repeating characters.
**Hint:** Sliding window with a set. When duplicate found, shrink window from left.
**Time:** O(n), **Space:** O(min(n, m)) where m is charset size

### 13. Minimum Window Substring
**Problem:** Find the smallest window in `s` containing all characters of `t`.
**Hint:** Sliding window. Expand right to include all characters, then shrink left to minimize.
**Time:** O(n), **Space:** O(m)

### 14. Valid Anagram
**Problem:** Check if two strings are anagrams.
**Hint:** Count character frequencies in both strings. They should match.
**Time:** O(n), **Space:** O(1) (26 letters)

### 15. Longest Palindromic Substring
**Problem:** Find the longest palindromic substring.
**Hint:** Expand around each center (odd and even length). Or use Manacher's algorithm for O(n).
**Time:** O(n²) expand, O(n) Manacher, **Space:** O(1)

---

## Linked Lists (16-25)

### 16. Reverse a Linked List
**Problem:** Reverse a singly linked list.
**Hint:** Use three pointers: prev, curr, next. Iterate and reverse links.
**Time:** O(n), **Space:** O(1)

### 17. Detect Cycle in Linked List
**Problem:** Determine if a linked list has a cycle.
**Hint:** Floyd's tortoise and hare. Slow pointer moves 1 step, fast moves 2. If they meet, cycle exists.
**Time:** O(n), **Space:** O(1)

### 18. Merge Two Sorted Lists
**Problem:** Merge two sorted linked lists into one sorted list.
**Hint:** Use a dummy head. Compare heads of both lists, append the smaller one.
**Time:** O(n + m), **Space:** O(1)

### 19. Remove Nth Node From End
**Problem:** Remove the nth node from the end of the list.
**Hint:** Two pointers. Move first pointer n steps ahead, then move both until first reaches end.
**Time:** O(n), **Space:** O(1)

### 20. Linked List Cycle II (Find Cycle Start)
**Problem:** Find where the cycle begins.
**Hint:** Floyd's algorithm. After detection, reset one pointer to head. Move both one step at a time. They meet at cycle start.
**Time:** O(n), **Space:** O(1)

### 21. Merge K Sorted Lists
**Problem:** Merge k sorted linked lists.
**Hint:** Use a min-heap. Push the head of each list. Pop the smallest, push its next.
**Time:** O(n log k), **Space:** O(k)

### 22. LRU Cache
**Problem:** Implement an LRU cache with O(1) get and put.
**Hint:** Hash map + doubly linked list. Map stores key→node. List stores access order.
**Time:** O(1) per operation, **Space:** O(capacity)

### 23. Add Two Numbers (Linked List)
**Problem:** Two numbers represented as linked lists, add them.
**Hint:** Iterate both lists simultaneously, maintain carry. Create new nodes for result.
**Time:** O(max(n, m)), **Space:** O(max(n, m))

### 24. Palindrome Linked List
**Problem:** Check if a linked list is a palindrome.
**Hint:** Find middle, reverse second half, compare both halves.
**Time:** O(n), **Space:** O(1)

### 25. Intersection of Two Linked Lists
**Problem:** Find the node where two linked lists intersect.
**Hint:** Use two pointers. When one reaches end, redirect to the other list's head. They'll meet at intersection.
**Time:** O(n + m), **Space:** O(1)

---

## Trees (26-40)

### 26. Maximum Depth of Binary Tree
**Problem:** Find the maximum depth.
**Hint:** `depth = 1 + max(depth(left), depth(right))`
**Time:** O(n), **Space:** O(h)

### 27. Same Tree
**Problem:** Check if two trees are identical.
**Hint:** Recursively check: `same(p, q) = p->val == q->val && same(p->left, q->left) && same(p->right, q->right)`
**Time:** O(n), **Space:** O(h)

### 28. Invert Binary Tree
**Problem:** Mirror a binary tree.
**Hint:** Swap left and right children recursively.
**Time:** O(n), **Space:** O(h)

### 29. Binary Tree Level Order Traversal
**Problem:** Return level-order traversal of a binary tree.
**Hint:** BFS with a queue. Process all nodes at each level before moving to next.
**Time:** O(n), **Space:** O(n)

### 30. Validate Binary Search Tree
**Problem:** Check if a binary tree is a valid BST.
**Hint:** Recursively check with min/max bounds. `isValid(node, min, max)`
**Time:** O(n), **Space:** O(h)

### 31. Lowest Common Ancestor of a Binary Tree
**Problem:** Find the LCA of two nodes.
**Hint:** If `p` and `q` are on different sides of a node, that node is the LCA.
**Time:** O(n), **Space:** O(h)

### 32. Serialize and Deserialize Binary Tree
**Problem:** Convert tree to string and back.
**Hint:** Use pre-order traversal with null markers. Deserialize by reading tokens in same order.
**Time:** O(n), **Space:** O(n)

### 33. Binary Tree Maximum Path Sum
**Problem:** Find the maximum path sum (any node to any node).
**Hint:** At each node, calculate max path through that node. Return max single-branch path to parent.
**Time:** O(n), **Space:** O(h)

### 34. Construct Binary Tree from Preorder and Inorder
**Problem:** Build tree from traversal arrays.
**Hint:** First element of preorder is root. Find root in inorder to split left/right subtrees.
**Time:** O(n), **Space:** O(n)

### 35. Kth Smallest Element in BST
**Problem:** Find the kth smallest element.
**Hint:** In-order traversal gives sorted order. Stop at the kth element.
**Time:** O(h + k), **Space:** O(h)

### 36. Diameter of Binary Tree
**Problem:** Find the longest path between any two nodes.
**Hint:** At each node, diameter through that node = left_height + right_height. Track the maximum.
**Time:** O(n), **Space:** O(h)

### 37. Symmetric Tree
**Problem:** Check if a tree is a mirror of itself.
**Hint:** Recursively check if left subtree is mirror of right subtree.
**Time:** O(n), **Space:** O(h)

### 38. Path Sum
**Problem:** Check if there's a root-to-leaf path with given sum.
**Hint:** Subtract current node's value from sum. At leaf, check if sum is 0.
**Time:** O(n), **Space:** O(h)

### 39. Flatten Binary Tree to Linked List
**Problem:** Flatten tree to linked list in pre-order.
**Hint:** Process in reverse order (right, left, root). Use a global pointer for the previous node.
**Time:** O(n), **Space:** O(h)

### 40. Count Good Nodes in Binary Tree
**Problem:** Count nodes where all ancestors have smaller values.
**Hint:** DFS passing the maximum value seen so far.
**Time:** O(n), **Space:** O(h)

---

## Graphs (41-50)

### 41. Number of Islands
**Problem:** Count connected components of '1's in a grid.
**Hint:** DFS/BFS from each unvisited '1'. Mark visited cells.
**Time:** O(n × m), **Space:** O(n × m)

### 42. Clone Graph
**Problem:** Deep copy a graph.
**Hint:** BFS/DFS with a hash map from original node to cloned node.
**Time:** O(V + E), **Space:** O(V)

### 43. Course Schedule (Detect Cycle in Directed Graph)
**Problem:** Can you finish all courses given prerequisites?
**Hint:** Topological sort. If cycle exists, return false.
**Time:** O(V + E), **Space:** O(V)

### 44. Pacific Atlantic Water Flow
**Problem:** Find cells that can flow to both oceans.
**Hint:** Run BFS/DFS from each ocean. Cells reachable from both are the answer.
**Time:** O(n × m), **Space:** O(n × m)

### 45. Number of Connected Components in Graph
**Problem:** Count connected components.
**Hint:** DFS/BFS from each unvisited node. Or use DSU.
**Time:** O(V + E), **Space:** O(V)

### 46. Shortest Path in Binary Matrix
**Problem:** Find shortest path from top-left to bottom-right in a binary grid.
**Hint:** BFS from start. 8-directional movement.
**Time:** O(n²), **Space:** O(n²)

### 47. Word Ladder
**Problem:** Find shortest transformation sequence from beginWord to endWord.
**Hint:** BFS. Each word is a node. Words differing by one character are connected.
**Time:** O(M² × N), **Space:** O(M² × N) where M = word length, N = word list size

### 48. Alien Dictionary
**Problem:** Find character order from sorted dictionary.
**Hint:** Build graph from character ordering. Topological sort.
**Time:** O(C), **Space:** O(1) (at most 26 characters)

### 49. Graph Valid Tree
**Problem:** Check if edges form a valid tree.
**Hint:** Tree = connected + n-1 edges + no cycles. Use DSU.
**Time:** O(V + E), **Space:** O(V)

### 50. Rotting Oranges
**Problem:** Find minimum time for all oranges to rot.
**Hint:** Multi-source BFS. Start from all rotten oranges simultaneously.
**Time:** O(n × m), **Space:** O(n × m)

---

## Dynamic Programming (51-65)

### 51. Climbing Stairs
**Problem:** How many ways to climb n stairs (1 or 2 steps)?
**Hint:** Same as Fibonacci: `dp[n] = dp[n-1] + dp[n-2]`
**Time:** O(n), **Space:** O(1)

### 52. Coin Change
**Problem:** Minimum coins to make amount.
**Hint:** `dp[i] = min(dp[i], dp[i - coin] + 1)` for each coin.
**Time:** O(n × amount), **Space:** O(amount)

### 53. Longest Increasing Subsequence
**Problem:** Find length of LIS.
**Hint:** Binary search approach: maintain `tails` array. For each element, find position with `lower_bound`.
**Time:** O(n log n), **Space:** O(n)

### 54. Longest Common Subsequence
**Problem:** Find length of LCS of two strings.
**Hint:** `dp[i][j] = dp[i-1][j-1] + 1` if `s1[i]==s2[j]`, else `max(dp[i-1][j], dp[i][j-1])`
**Time:** O(n × m), **Space:** O(min(n, m))

### 55. Word Break
**Problem:** Can string be segmented into dictionary words?
**Hint:** `dp[i] = true` if `dp[j]` is true and `s[j..i]` is in dictionary.
**Time:** O(n² × m), **Space:** O(n)

### 56. House Robber
**Problem:** Max money from non-adjacent houses.
**Hint:** `dp[i] = max(dp[i-1], dp[i-2] + nums[i])`
**Time:** O(n), **Space:** O(1)

### 57. Unique Paths
Problem:** Count paths from top-left to bottom-right (only right/down).
**Hint:** `dp[i][j] = dp[i-1][j] + dp[i][j-1]`
**Time:** O(n × m), **Space:** O(m)

### 58. Jump Game
**Problem:** Can you reach the last index?
**Hint:** Track the farthest reachable index. If at any point current index > farthest, return false.
**Time:** O(n), **Space:** O(1)

### 59. Decode Ways
**Problem:** Number of ways to decode a string of digits.
**Hint:** `dp[i] = dp[i-1]` (if valid single digit) + `dp[i-2]` (if valid two-digit)
**Time:** O(n), **Space:** O(1)

### 60. Partition Equal Subset Sum
**Problem:** Can array be partitioned into two equal-sum subsets?
**Hint:** Subset sum DP with target = total_sum / 2.
**Time:** O(n × target), **Space:** O(target)

### 61. Edit Distance
**Problem:** Min operations (insert, delete, replace) to convert one string to another.
**Hint:** `dp[i][j] = dp[i-1][j-1]` if equal, else `1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])`
**Time:** O(n × m), **Space:** O(min(n, m))

### 62. Maximum Length of Repeated Subarray
**Problem:** Find longest common subarray (contiguous).
**Hint:** `dp[i][j] = dp[i-1][j-1] + 1` if `a[i]==b[j]`, else 0.
**Time:** O(n × m), **Space:** O(m)

### 63. Palindrome Partitioning
**Problem:** Min cuts to partition string into palindromes.
**Hint:** `dp[i] = min(dp[j] + 1)` for all `j < i` where `s[j..i]` is palindrome.
**Time:** O(n²), **Space:** O(n²)

### 64. Regular Expression Matching
**Problem:** Match string with pattern containing '.' and '*'.
**Hint:** 2D DP. Handle '*' by matching zero or more of the preceding character.
**Time:** O(n × m), **Space:** O(n × m)

### 65. Burst Balloons
**Problem:** Maximize coins from bursting balloons.
**Hint:** Interval DP. Think about which balloon to burst last in each range.
**Time:** O(n³), **Space:** O(n²)

---

## Binary Search (66-70)

### 66. Binary Search
**Problem:** Find target in sorted array.
**Hint:** Standard binary search with `lo <= hi`.
**Time:** O(log n), **Space:** O(1)

### 67. Search a 2D Matrix
**Problem:** Search in a matrix where each row and column is sorted.
**Hint:** Start from top-right (or bottom-left). Move left if too big, down if too small.
**Time:** O(n + m), **Space:** O(1)

### 68. Find Peak Element
**Problem:** Find any peak element (greater than neighbors).
**Hint:** Binary search. If `arr[mid] < arr[mid+1]`, peak is on right. Else left.
**Time:** O(log n), **Space:** O(1)

### 69. Median of Two Sorted Arrays
**Problem:** Find median of two sorted arrays.
**Hint:** Binary search on the partition point of the shorter array.
**Time:** O(log(min(n, m))), **Space:** O(1)

### 70. Capacity To Ship Packages Within D Days
**Problem:** Find minimum capacity to ship all packages within D days.
**Hint:** Binary search on capacity. Check if given capacity allows shipping within D days.
**Time:** O(n × log(sum)), **Space:** O(1)

---

## Stacks & Queues (71-78)

### 71. Valid Parentheses
**Problem:** Check if parentheses are valid.
**Hint:** Use a stack. Push opening brackets. On closing bracket, check if top matches.
**Time:** O(n), **Space:** O(n)

### 72. Min Stack
**Problem:** Stack that supports getMin in O(1).
**Hint:** Use two stacks: one for values, one for minimums. Or store pairs (value, current_min).
**Time:** O(1) per operation, **Space:** O(n)

### 73. Daily Temperatures
**Problem:** For each day, find how many days until a warmer temperature.
**Hint:** Monotonic stack. Store indices. When you find a warmer day, pop and calculate.
**Time:** O(n), **Space:** O(n)

### 74. Largest Rectangle in Histogram
**Problem:** Find the largest rectangular area in a histogram.
**Hint:** Monotonic stack. For each bar, find the first shorter bar on left and right.
**Time:** O(n), **Space:** O(n)

### 75. Implement Queue using Stacks
**Problem:** Implement FIFO queue using two stacks.
**Hint:** Push to input stack. Pop from output stack. When output is empty, transfer all from input.
**Time:** Amortized O(1), **Space:** O(n)

### 76. Next Greater Element
**Problem:** For each element, find the next greater element.
**Hint:** Monotonic stack. Traverse right to left.
**Time:** O(n), **Space:** O(n)

### 77. Sliding Window Maximum
**Problem:** Find max in each sliding window of size k.
**Hint:** Monotonic deque. Store indices. Remove from front if out of window, from back if smaller.
**Time:** O(n), **Space:** O(k)

### 78. Trapping Rain Water
**Problem:** Calculate water trapped after rain.
**Hint:** Two pointers or monotonic stack. Water at position = min(max_left, max_right) - height.
**Time:** O(n), **Space:** O(1) two pointers, O(n) stack

---

## Heaps / Priority Queues (79-83)

### 79. Kth Largest Element in Array
**Problem:** Find the kth largest element.
**Hint:** Min-heap of size k. Or quickselect (partition-based).
**Time:** O(n log k) heap, O(n) quickselect, **Space:** O(k) or O(1)

### 80. Top K Frequent Elements
**Problem:** Find the k most frequent elements.
**Hint:** Count frequencies, then use min-heap of size k. Or bucket sort.
**Time:** O(n log k) heap, O(n) bucket, **Space:** O(n)

### 81. Find Median from Data Stream
**Problem:** Find median of a stream of numbers.
**Hint:** Two heaps: max-heap for lower half, min-heap for upper half. Balance sizes.
**Time:** O(log n) per insert, O(1) for median, **Space:** O(n)

### 82. Merge K Sorted Lists
**Problem:** Merge k sorted linked lists.
**Hint:** Min-heap. Push head of each list. Pop smallest, push its next.
**Time:** O(n log k), **Space:** O(k)

### 83. Task Scheduler
**Problem:** Minimum time to complete tasks with cooldown.
**Hint:** Greedy with heap. Execute most frequent task first. Or use formula: `(max_freq - 1) × (n + 1) + count_of_max_freq`
**Time:** O(n), **Space:** O(1)

---

## Backtracking (84-88)

### 84. Subsets
**Problem:** Generate all subsets of a set.
**Hint:** For each element, choose to include or exclude. Recurse.
**Time:** O(2ⁿ), **Space:** O(n)

### 85. Permutations
**Problem:** Generate all permutations of an array.
**Hint:** Swap each element with the current position, recurse, swap back.
**Time:** O(n! × n), **Space:** O(n)

### 86. Combination Sum
**Problem:** Find all combinations that sum to target (elements reusable).
**Hint:** Backtrack. At each step, try adding each element (allow same element again).
**Time:** O(n^(target/min)), **Space:** O(target/min)

### 87. N-Queens
**Problem:** Place N queens on N×N board with no conflicts.
**Hint:** Place queens row by row. Track columns, diagonals, and anti-diagonals.
**Time:** O(N!), **Space:** O(N²)

### 88. Word Search
**Problem:** Find if a word exists in a grid (adjacent cells).
**Hint:** DFS from each cell. Mark visited cells. Backtrack.
**Time:** O(n × m × 4^L), **Space:** O(L)

---

## Math & Bit Manipulation (89-93)

### 89. Power of Two
**Problem:** Check if a number is a power of two.
**Hint:** `n > 0 && (n & (n-1)) == 0`
**Time:** O(1), **Space:** O(1)

### 90. Counting Bits
**Problem:** Count 1-bits for every number from 0 to n.
**Hint:** `dp[i] = dp[i >> 1] + (i & 1)`
**Time:** O(n), **Space:** O(n)

### 91. Reverse Integer
**Problem:** Reverse digits of an integer.
**Hint:** Pop digits from end, push to result. Check for overflow.
**Time:** O(log n), **Space:** O(1)

### 92. Excel Sheet Column Number
**Problem:** Convert column title to number (A=1, B=2, ..., Z=26, AA=27).
**Hint:** Base-26 conversion. `result = result * 26 + (c - 'A' + 1)`
**Time:** O(n), **Space:** O(1)

### 93. Happy Number
**Problem:** Check if a number eventually reaches 1 by summing squares of digits.
**Hint:** Use Floyd's cycle detection. Or use a set to detect loops.
**Time:** O(log n), **Space:** O(1)

---

## Trie & String Matching (94-97)

### 94. Implement Trie
**Problem:** Implement a trie with insert, search, and startsWith.
**Hint:** Tree of characters. Each node has 26 children and an is_end flag.
**Time:** O(L) per operation, **Space:** O(ALPHABET × N × L)

### 95. Word Search II
**Problem:** Find all words from a dictionary in a grid.
**Hint:** Build a trie from the dictionary. DFS on the grid, following the trie.
**Time:** O(n × m × 4^L), **Space:** O(W × L)

### 96. Longest Common Prefix
**Problem:** Find the longest common prefix of all strings.
**Hint:** Vertical scanning: compare character at each position across all strings.
**Time:** O(S), **Space:** O(1)

### 97. Palindrome Pairs
**Problem:** Find all pairs of indices that form a palindrome when concatenated.
**Hint:** Use a trie. For each word, check if its reverse or any prefix/suffix forms a palindrome.
**Time:** O(n × L²), **Space:** O(n × L)

---

## Greedy (98-100)

### 98. Jump Game II
**Problem:** Minimum jumps to reach the end.
**Hint:** BFS-like greedy. Track current range and next range.
**Time:** O(n), **Space:** O(1)

### 99. Merge Intervals
**Problem:** Merge all overlapping intervals.
**Hint:** Sort by start. If current start ≤ previous end, merge. Otherwise, add new interval.
**Time:** O(n log n), **Space:** O(n)

### 100. Non-overlapping Intervals
**Problem:** Min intervals to remove to make rest non-overlapping.
**Hint:** Sort by end time. Greedily select intervals that end earliest.
**Time:** O(n log n), **Space:** O(1)

---

*These 100 questions cover the vast majority of what you'll encounter in interviews. Master these, and you'll be well-prepared for any DSA interview.*
