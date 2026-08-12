# Chapter 104: Cartesian Trees and Tournament Trees

## Prerequisites
- Binary search trees (BST)
- Heaps (min-heap, max-heap)
- RMQ (Range Minimum Query)
- Stack-based algorithms
- DFS traversal

## Interview Frequency: ★★

Cartesian trees bridge arrays and trees — they encode an array's structure in a way that makes range minimum queries equivalent to LCA queries. Tournament trees model competition-style elimination and enable efficient k-way merging.

> **Key Insight:** A Cartesian tree built from an array has the heap property on values and an inorder traversal that recovers the original array. The LCA of any two nodes in a Cartesian tree is the minimum element in the corresponding range.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Cartesian tree | ★★★ | Medium | Heap + inorder = array |
| Tournament tree | ★ | Medium | Winner tree for k-way merge |
| Cartesian tree + LCA = RMQ | ★★ | Hard | Foundation of ±1 RMQ |

---

## 104.1 What Problem Does It Solve?

### The RMQ Problem
Given an array `A[0..n-1]`, answer queries: "What is the minimum element in A[l..r]?"

**Approaches and trade-offs:**

| Method | Preprocess | Query | Space |
|---|---|---|---|
| Sparse table | O(n log n) | O(1) | O(n log n) |
| Segment tree | O(n) | O(log n) | O(n) |
| Cartesian tree + LCA | O(n) | O(1) with O(n) LCA | O(n) |

The Cartesian tree approach achieves **O(n) preprocess + O(1) query** when combined with an O(1) LCA data structure (e.g., Euler tour + sparse table).

### The K-Way Merge Problem
Given `k` sorted lists, repeatedly extract the smallest element across all lists. A tournament tree solves this in O(n log k) total.

---

## 104.2 Cartesian Tree — Definition

A **Cartesian tree** of an array `A[0..n-1]` is a binary tree where:

1. **Heap property:** Each node's value is ≤ its children's values (min-heap variant).
2. **Inorder property:** An inorder traversal of the tree visits the elements in their original array order.
3. **Uniqueness:** For distinct elements, the Cartesian tree is unique.

These two properties together mean:
- The **root** is the minimum element of the entire array.
- The **left subtree** is the Cartesian tree of elements to the left of the minimum.
- The **right subtree** is the Cartesian tree of elements to the right of the minimum.

### Visual Example

For `A = [3, 2, 6, 1, 9, 7, 4]`:

```
         1          ← root (minimum of entire array)
        / \
       2   4        ← left subtree: [3,2,6], right subtree: [9,7,4]
      / \   \
     3   6   7
              \
               9
```

Inorder: 3, 2, 6, 1, 9, 7, 4 ✓ (original array order)
Heap property: each parent < children ✓

---

## 104.3 Building a Cartesian Tree — O(n) Stack Algorithm

The key insight: process elements left to right, maintaining a stack of nodes on the rightmost path of the tree being built.

**Algorithm:**
1. For each element `A[i]`, create a new node.
2. Pop elements from the stack while they are greater than `A[i]`.
3. The last popped element becomes the left child of the new node.
4. The new node becomes the right child of the current top of the stack.
5. Push the new node onto the stack.

This works because we're maintaining the rightmost path of the tree, which must be increasing (due to the heap property).

### Dry Run

`A = [3, 2, 6, 1, 9, 7, 4]`

```
i=0, val=3: stack=[], node(3) → stack=[3]
i=1, val=2: pop 3 (>2), node(2).left=3 → stack=[2]
i=2, val=6: no pop, node(6) → 2.right=6 → stack=[2,6]
i=3, val=1: pop 6, pop 2, node(1).left=2 → stack=[1]
i=4, val=9: no pop, node(9) → 1.right=9 → stack=[1,9]
i=5, val=7: pop 9 (>7), node(7).left=9 → 1.right=7 → stack=[1,7]
i=6, val=4: pop 7 (>4), node(4).left=7 → 1.right=4 → stack=[1,4]

Final tree:
        1
       / \
      2   4
     / \   \
    3   6   7
             \
              9
```

---

## 104.4 Cartesian Tree + LCA = RMQ

**Theorem:** For any two indices `i` and `j`, the RMQ(i, j) = LCA(node_i, node_j) in the Cartesian tree.

**Proof sketch:**
- The minimum of A[i..j] is the first element encountered when walking up from node_i and node_j toward their common ancestor.
- The LCA is the shallowest node that is an ancestor of both, which corresponds to the minimum element in the range.

This gives us:
- Build Cartesian tree: O(n)
- Preprocess LCA (Euler tour + sparse table): O(n log n)
- Answer RMQ in O(1)

For the special case where adjacent RMQ answers differ by at most 1 (the **±1 RMQ** problem), the LCA can be answered in O(1) with O(n) preprocessing, giving truly linear RMQ.

---

## 104.5 Tournament Trees

A **tournament tree** (also called a winner tree) is a complete binary tree where:
- **Leaves** represent the participants (elements).
- **Internal nodes** store the winner (min or max) of their two children.
- The **root** stores the overall winner.

### Building

Fill the leaves, then compute each internal node bottom-up:
```
winner[v] = min(winner[2v], winner[2v+1])   // for min tournament
```

This takes O(n) time for n participants.

### K-Way Merge Application

To merge k sorted lists:
1. Build a tournament tree with the first element of each list as leaves.
2. Extract the root (the global minimum).
3. Replace the leaf from the winning list with its next element.
4. Update the path from that leaf to the root: O(log k).
5. Repeat until all lists are exhausted.

Total: O(n log k) for n total elements across k lists.

### Visual Example

Merging 3 sorted lists: [1,4,7], [2,5,8], [3,6,9]

```
Tournament tree (min):
        1
       / \
      1   3
     / \ / \
    1  2  3  (empty sentinel)

Step 1: Extract 1 from list 0. Replace leaf with 4.
        2
       / \
      2   3
     / \ / \
    4  2  3

Step 2: Extract 2 from list 1. Replace leaf with 5.
        3
       / \
      4   3
     / \ / \
    4  5  3

Step 3: Extract 3 from list 2. Replace leaf with 6.
        4
       / \
      4   6
     / \ / \
    4  5  6
...and so on.
```

---

## 104.6 Complexity Analysis

### Cartesian Tree

| Operation | Time | Space |
|---|---|---|
| Build | O(n) | O(n) |
| LCA (preprocessed) | O(1) | O(n log n) or O(n) |
| RMQ via LCA | O(1) | — |

### Tournament Tree

| Operation | Time | Space |
|---|---|---|
| Build | O(n) | O(n) |
| Extract winner | O(1) | — |
| Replace leaf + update | O(log k) | — |
| Full k-way merge | O(n log k) | O(k) |

---

## 104.7 Implementation

### C++ — Cartesian Tree

```cpp
#include <iostream>
#include <vector>
#include <stack>

struct CartNode {
    int val, idx;
    CartNode *left, *right;
    CartNode(int v, int i) : val(v), idx(i), left(nullptr), right(nullptr) {}
};

CartNode* buildCartesianTree(const std::vector<int>& arr) {
    int n = arr.size();
    if (n == 0) return nullptr;
    std::stack<CartNode*> st;

    for (int i = 0; i < n; i++) {
        CartNode* node = new CartNode(arr[i], i);
        CartNode* last = nullptr;
        while (!st.empty() && st.top()->val > arr[i]) {
            last = st.top();
            st.pop();
        }
        node->left = last;
        if (!st.empty()) st.top()->right = node;
        st.push(node);
    }
    while (st.size() > 1) st.pop();
    return st.top();
}

void printTree(CartNode* node, int depth = 0) {
    if (!node) return;
    printTree(node->right, depth + 1);
    for (int i = 0; i < depth; i++) std::cout << "  ";
    std::cout << node->val << "(i=" << node->idx << ")\n";
    printTree(node->left, depth + 1);
}

int main() {
    std::vector<int> arr = {3, 2, 6, 1, 9, 7, 4};
    CartNode* root = buildCartesianTree(arr);
    std::cout << "Cartesian Tree:\n";
    printTree(root);
    return 0;
}
```

### C++ — Tournament Tree (K-Way Merge)

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <climits>

class TournamentTree {
    int n;
    std::vector<std::pair<int,int>> tree; // {value, list_index}

public:
    TournamentTree(int k) : n(k), tree(2 * k, {INT_MAX, -1}) {}

    void build(const std::vector<int>& firstElements) {
        for (int i = 0; i < (int)firstElements.size(); i++)
            tree[n + i] = {firstElements[i], i};
        for (int i = n - 1; i >= 1; i--)
            tree[i] = std::min(tree[2 * i], tree[2 * i + 1]);
    }

    std::pair<int,int> winner() { return tree[1]; }

    void update(int listIdx, int newValue) {
        int pos = n + listIdx;
        tree[pos] = {newValue, listIdx};
        for (pos /= 2; pos >= 1; pos /= 2)
            tree[pos] = std::min(tree[2 * pos], tree[2 * pos + 1]);
    }
};

std::vector<int> kWayMerge(std::vector<std::vector<int>>& lists) {
    int k = lists.size();
    std::vector<int> ptrs(k, 0);
    std::vector<int> firstElems;
    for (int i = 0; i < k; i++)
        firstElems.push_back(lists[i].empty() ? INT_MAX : lists[i][0]);

    TournamentTree tt(k);
    tt.build(firstElems);

    std::vector<int> result;
    while (true) {
        auto [val, idx] = tt.winner();
        if (val == INT_MAX) break;
        result.push_back(val);
        ptrs[idx]++;
        int next = (ptrs[idx] < (int)lists[idx].size()) ? lists[idx][ptrs[idx]] : INT_MAX;
        tt.update(idx, next);
    }
    return result;
}

int main() {
    std::vector<std::vector<int>> lists = {{1, 4, 7}, {2, 5, 8}, {3, 6, 9}};
    auto merged = kWayMerge(lists);
    std::cout << "Merged: ";
    for (int x : merged) std::cout << x << " ";
    std::cout << "\n";
    return 0;
}
```

### Python — Cartesian Tree

```python
class CartNode:
    def __init__(self, val, idx):
        self.val = val
        self.idx = idx
        self.left = None
        self.right = None


def build_cartesian_tree(arr):
    """Build min-Cartesian tree in O(n) using a stack."""
    n = len(arr)
    if n == 0:
        return None
    stack = []
    for i, val in enumerate(arr):
        node = CartNode(val, i)
        last = None
        while stack and stack[-1].val > val:
            last = stack.pop()
        node.left = last
        if stack:
            stack[-1].right = node
        stack.append(node)
    return stack[0]


def print_tree(node, depth=0):
    if not node:
        return
    print_tree(node.right, depth + 1)
    print("  " * depth + f"{node.val}(i={node.idx})")
    print_tree(node.left, depth + 1)


if __name__ == "__main__":
    arr = [3, 2, 6, 1, 9, 7, 4]
    root = build_cartesian_tree(arr)
    print("Cartesian Tree:")
    print_tree(root)
```

### Java — Cartesian Tree

```java
import java.util.*;

public class CartesianTree {
    static class Node {
        int val, idx;
        Node left, right;
        Node(int v, int i) { val = v; idx = i; }
    }

    public static Node build(int[] arr) {
        if (arr.length == 0) return null;
        Deque<Node> stack = new ArrayDeque<>();
        for (int i = 0; i < arr.length; i++) {
            Node node = new Node(arr[i], i);
            Node last = null;
            while (!stack.isEmpty() && stack.peek().val > arr[i]) {
                last = stack.pop();
            }
            node.left = last;
            if (!stack.isEmpty()) stack.peek().right = node;
            stack.push(node);
        }
        while (stack.size() > 1) stack.pop();
        return stack.peek();
    }

    public static void printTree(Node node, int depth) {
        if (node == null) return;
        printTree(node.right, depth + 1);
        for (int i = 0; i < depth; i++) System.out.print("  ");
        System.out.println(node.val + "(i=" + node.idx + ")");
        printTree(node.left, depth + 1);
    }

    public static void main(String[] args) {
        int[] arr = {3, 2, 6, 1, 9, 7, 4};
        Node root = build(arr);
        System.out.println("Cartesian Tree:");
        printTree(root, 0);
    }
}
```

### Python — Tournament Tree (K-Way Merge)

```python
import heapq

def k_way_merge(lists):
    """Merge k sorted lists using a heap (Python's heapq).
    A tournament tree is conceptually equivalent for this purpose."""
    result = []
    heap = []
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))
    while heap:
        val, list_idx, elem_idx = heapq.heappop(heap)
        result.append(val)
        if elem_idx + 1 < len(lists[list_idx]):
            heapq.heappush(heap, (lists[list_idx][elem_idx + 1], list_idx, elem_idx + 1))
    return result


if __name__ == "__main__":
    lists = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
    merged = k_way_merge(lists)
    print(f"Merged: {merged}")  # [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

---

## 104.8 Applications

1. **RMQ via LCA** — Cartesian trees reduce RMQ to LCA, which is the foundation of the Fischer-Heun structure achieving O(n) preprocessing + O(1) query.
2. **K-way merge** — Tournament trees are the standard approach for external sorting (merging sorted runs from disk).
3. **Suffix array construction** — Cartesian trees appear in DC3/skew algorithms for suffix array construction.
4. **Histogram largest rectangle** — The Cartesian tree of a histogram encodes the largest rectangle problem.
5. **Treap** — A Cartesian tree with random priorities gives a randomized BST (treap), which is a balanced BST with high probability.

---

## 104.9 Exercises

1. **Build a max-Cartesian tree** for the array `[5, 3, 8, 1, 2, 7, 4, 6]`. Verify that inorder gives the original array.
2. **RMQ via LCA:** Build a Cartesian tree for `[3, 1, 4, 1, 5, 9, 2, 6]` and verify that LCA(node_2, node_6) gives the minimum of A[2..6].
3. **Tournament tree for external sort:** You have 4 sorted files with 1000 elements each. Describe how a tournament tree merges them, and count the total number of comparisons.
4. **Largest rectangle in histogram:** Given heights `[2, 1, 5, 6, 2, 3]`, build the Cartesian tree and use it to find the largest rectangle. (Hint: the area under each node relates to the rectangle it represents.)
5. **Treap construction:** Assign random priorities to elements `[4, 2, 6, 1, 3, 5, 7]` and build a Cartesian tree on (key, priority) pairs. Verify it's a valid BST on keys and a heap on priorities.

---

## 104.10 Interview Questions

1. **Q: What is the relationship between a Cartesian tree and RMQ?**
   A: The LCA of two nodes in a Cartesian tree corresponds to the minimum element in the range between those two indices. This reduces RMQ to LCA.

2. **Q: How do you build a Cartesian tree in O(n)?**
   A: Use a stack. Process elements left to right. For each element, pop stack elements that are greater, making the last popped the left child. Push the new node. The stack maintains the rightmost path.

3. **Q: What is a tournament tree and when would you use it?**
   A: A complete binary tree where each internal node stores the min/max of its children. Used for k-way merging in external sorting. Extract winner is O(1), replacement is O(log k).

4. **Q: How does a Cartesian tree relate to a treap?**
   A: A treap is a Cartesian tree where keys are array values and priorities are random. The heap property on priorities ensures balanced height with high probability, giving O(log n) expected operations.

5. **Q: Can you build a Cartesian tree from a preorder traversal?**
   A: Yes, if the array elements are distinct. The first element of preorder is the root. Elements less than the root form the left subtree, and elements greater form the right subtree. This is similar to BST construction from preorder.

---

## 104.11 Cross-References

- **Chapter 101 (Segment Trees):** Both solve RMQ; segment trees are more general but slower per query.
- **Chapter 102 (Wavelet Trees):** Another tree structure that partitions arrays recursively.
- **Chapter 105 (Suffix Trees/Arrays):** Cartesian trees appear in suffix array construction algorithms.
- **Chapter 97 (Heaps):** Tournament trees are essentially heap-like structures.
- **Chapter 11 (LCA):** LCA on Cartesian trees gives O(1) RMQ.
- **Chapter 116 (Treaps):** Treaps are Cartesian trees with random priorities.

---

## Summary

| Structure | Build | Key Property |
|---|---|---|
| Cartesian tree | O(n) stack | LCA = RMQ |
| Tournament tree | O(n) | K-way merge winner |
| Cartesian + LCA → RMQ | O(n) + O(n log n) | O(1) RMQ queries |
