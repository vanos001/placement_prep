# Data Structures: Complete Interview Reference

## 📊 Data Structure Comparison

| Structure | Access | Search | Insert | Delete | Space | Best For |
|-----------|--------|--------|--------|--------|-------|----------|
| Array | O(1) | O(n) | O(n) | O(n) | O(n) | Random access, known size |
| Dynamic Array | O(1) | O(n) | O(1)* | O(n) | O(n) | Appending, random access |
| Linked List | O(n) | O(n) | O(1) | O(1) | O(n) | Frequent insert/delete at head |
| Stack | O(n) | O(n) | O(1) | O(1) | O(n) | LIFO, undo, DFS |
| Queue | O(n) | O(n) | O(1) | O(1) | O(n) | FIFO, BFS, scheduling |
| Hash Map | - | O(1)* | O(1)* | O(1)* | O(n) | Fast lookup, counting |
| Binary Search Tree | O(log n)* | O(log n)* | O(log n)* | O(log n)* | O(n) | Sorted data, range queries |
| Heap | O(n) | O(n) | O(log n) | O(log n) | O(n) | Priority queue, top-K |
| Trie | O(m) | O(m) | O(m) | O(m) | O(n*m) | Prefix search, autocomplete |
| Graph (Adj. List) | - | O(V+E) | O(1) | O(V) | O(V+E) | Sparse graphs, social networks |
| Graph (Adj. Matrix) | O(1) | O(V²) | O(1) | O(1) | O(V²) | Dense graphs, quick edge lookup |

*Amortized / average case

---

## 📦 Arrays

### Key Properties
- **Contiguous memory** — cache-friendly, O(1) random access
- **Fixed size** (static) or **dynamic** (resizable with amortized O(1) append)
- **Zero-indexed** in most languages

### Common Operations
```python
# Python (list = dynamic array)
arr = [1, 2, 3, 4, 5]

arr.append(6)          # O(1) amortized - add to end
arr.insert(0, 0)       # O(n) - add to beginning (shifts elements)
arr.pop()              # O(1) - remove from end
arr.pop(0)             # O(n) - remove from beginning (shifts)
arr[3]                 # O(1) - random access
3 in arr               # O(n) - linear search
sorted_arr = sorted(arr)  # O(n log n)
```

### Interview Patterns with Arrays
1. **Two Pointers** — Pair with target sum, remove duplicates
2. **Sliding Window** — Max subarray, longest substring
3. **Prefix Sum** — Range sum queries
4. **Sorting + Greedy** — Interval problems

### Common Mistakes
- Off-by-one errors in loop bounds
- Modifying array while iterating
- Not considering empty array edge case
- Forgetting that `insert(0, x)` and `pop(0)` are O(n)

---

## 🔗 Linked Lists

### Types
```
Singly Linked:  1 → 2 → 3 → 4 → None
Doubly Linked:  None ← 1 ⇄ 2 ⇄ 3 ⇄ 4 → None
Circular:       1 → 2 → 3 → 4 → 1 (back to head)
```

### Key Operations
```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

# Insert at head - O(1)
def insert_head(head, val):
    new_node = ListNode(val)
    new_node.next = head
    return new_node

# Delete node (given reference) - O(1)
def delete_node(node):
    node.val = node.next.val
    node.next = node.next.next

# Reverse linked list - O(n)
def reverse(head):
    prev = None
    curr = head
    while curr:
        next_temp = curr.next
        curr.next = prev
        prev = curr
        curr = next_temp
    return prev
```

### Interview Patterns with Linked Lists
1. **Fast & Slow Pointers** — Detect cycle, find middle
2. **Dummy Head** — Simplify edge cases in deletion/insertion
3. **Recursion** — Reverse, merge, palindrome check
4. **Two Pointers** — Nth from end, intersection

### Classic Problems
- Reverse a linked list (iterative + recursive)
- Detect cycle (Floyd's algorithm)
- Merge two sorted lists
- Remove nth node from end
- Flatten a multilevel linked list
- LRU Cache (doubly linked list + hash map)

---

## 🗺️ Hash Maps

### How They Work
```
Key → Hash Function → Index → Bucket → Value

Collision Resolution:
├── Chaining (linked list at each bucket)
└── Open Addressing (linear/quadratic probing)
```

### Key Properties
- **Average O(1)** for insert, delete, lookup
- **Worst case O(n)** with many collisions
- **Load factor** = n/m (elements/buckets), resize when > 0.75
- **Not ordered** (use TreeMap/OrderedDict if order matters)

### Interview Patterns with Hash Maps
1. **Frequency Counting** — Count occurrences, anagram check
2. **Two Sum** — Store complements as you iterate
3. **Grouping** — Group anagrams, categorize items
4. **Caching** — Memoization, LRU cache
5. **Set Operations** — Union, intersection, difference

```python
# Two Sum - O(n) with hash map
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Group Anagrams - O(n * k log k)
def group_anagrams(strs):
    groups = {}
    for s in strs:
        key = ''.join(sorted(s))
        groups.setdefault(key, []).append(s)
    return list(groups.values())
```

---

## 🌳 Trees

### Binary Tree Traversals
```python
# Inorder (Left, Root, Right) — gives sorted order for BST
def inorder(root):
    if root:
        inorder(root.left)
        print(root.val)
        inorder(root.right)

# Preorder (Root, Left, Right) — used for copying/serialization
def preorder(root):
    if root:
        print(root.val)
        preorder(root.left)
        preorder(root.right)

# Postorder (Left, Right, Root) — used for deletion, calculating size
def postorder(root):
    if root:
        postorder(root.left)
        postorder(root.right)
        print(root.val)

# Level Order (BFS) — level by level
from collections import deque
def level_order(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)
    return result
```

### Binary Search Tree (BST)
```
Properties:
- Left subtree values < root < Right subtree values
- Inorder traversal gives sorted sequence
- Average O(log n) for search/insert/delete
- Worst case O(n) if unbalanced (degenerates to linked list)

Balanced BSTs:
- AVL Tree: strict balance (height diff ≤ 1)
- Red-Black Tree: relaxed balance, fewer rotations
- Used in: TreeMap (Java), std::map (C++)
```

### Tree Interview Patterns
1. **Recursion** — Most tree problems are naturally recursive
2. **BFS (Level Order)** — Level-by-level processing
3. **DFS (Pre/In/Post)** — Path finding, validation
4. **Divide & Conquer** — Split into left/right subtrees

### Classic Tree Problems
- Maximum depth / height
- Validate BST
- Lowest common ancestor
- Serialize/deserialize binary tree
- Diameter of binary tree
- Path sum (all paths, any path)
- Binary tree to doubly linked list
- Construct tree from inorder + preorder

---

## 📊 Heaps (Priority Queues)

### Properties
```
Min Heap: Parent ≤ Children (smallest at top)
Max Heap: Parent ≥ Children (largest at top)

Operations:
├── insert: O(log n)
├── extract_min/max: O(log n)
├── peek: O(1)
└── build_heap: O(n)
```

### Python Implementation
```python
import heapq

# Min heap (default in Python)
heap = []
heapq.heappush(heap, 3)
heapq.heappush(heap, 1)
heapq.heappush(heap, 2)
min_val = heapq.heappop(heap)  # 1

# Max heap (negate values)
max_heap = []
heapq.heappush(max_heap, -3)
heapq.heappush(max_heap, -1)
max_val = -heapq.heappop(max_heap)  # 3

# Build heap from list - O(n)
nums = [3, 1, 4, 1, 5, 9]
heapq.heapify(nums)

# Top K elements
top_k = heapq.nlargest(k, nums)
```

### Interview Patterns with Heaps
1. **Top-K Elements** — K largest/smallest, K most frequent
2. **Merge K Sorted** — Use min heap to track smallest across K lists
3. **Median Finding** — Two heaps (max heap for lower half, min heap for upper)
4. **Task Scheduler** — Priority-based scheduling
5. **Sliding Window Maximum** — Monotonic deque or heap

---

## 📈 Graphs

### Representations
```python
# Adjacency List (most common in interviews)
graph = {
    'A': ['B', 'C'],
    'B': ['A', 'D'],
    'C': ['A', 'D'],
    'D': ['B', 'C']
}

# Adjacency Matrix
#     A  B  C  D
# A [[0, 1, 1, 0],
# B  [1, 0, 0, 1],
# C  [1, 0, 0, 1],
# D  [0, 1, 1, 0]]

# Edge List
edges = [('A', 'B'), ('A', 'C'), ('B', 'D'), ('C', 'D')]
```

### BFS vs DFS
```
BFS (Breadth-First Search):
├── Uses Queue (FIFO)
├── Explores level by level
├── Shortest path in unweighted graph
├── Space: O(V) for queue
└── Use: Shortest path, level order, connected components

DFS (Depth-First Search):
├── Uses Stack (or recursion)
├── Explores as deep as possible
├── Better for path finding, cycle detection
├── Space: O(V) for stack/recursion
└── Use: Topological sort, cycle detection, maze solving
```

### Graph Interview Patterns
1. **BFS** — Shortest path, word ladder, rotting oranges
2. **DFS** — Number of islands, course schedule, clone graph
3. **Topological Sort** — Task scheduling, dependency resolution
4. **Union Find** — Connected components, redundant connection
5. **Dijkstra** — Weighted shortest path
6. **Backtracking** — All paths, permutations

### Classic Graph Problems
- Number of islands (DFS/BFS)
- Course schedule (topological sort)
- Clone graph (DFS + hash map)
- Word ladder (BFS)
- Network delay time (Dijkstra)
- Accounts merge (Union Find)
- Alien dictionary (topological sort)

---

## 🔤 Tries

### Structure
```
Trie for ["cat", "car", "card", "dog", "dot"]:

        root
       /    \
      c      d
      |      |
      a      o
     / \     / \
    t   r   g   t
        |
        d
```

### Implementation
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
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True

    def search(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                return False
            node = node.children[char]
        return node.is_end

    def starts_with(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return False
            node = node.children[char]
        return True
```

### When to Use Tries
- Autocomplete / word suggestions
- Spell checking
- IP routing (longest prefix match)
- Word search in 2D grid

---

## 🔗 Cross-References

- [Problem Patterns](./patterns.md) — See which data structures pair with which patterns
- [Complexity Analysis](./complexity.md) — Big-O for all operations
- [Coding Framework](./framework.md) — How to select the right data structure
- [Cheatsheets](../../cheatsheets/os.md) — Quick reference for CS fundamentals
