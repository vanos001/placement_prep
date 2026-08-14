# DSA Edge Cases: The Silent Bug Source

Most interview rejections aren't from failing to know the algorithm — they're from edge cases. This chapter catalogs the most dangerous edge cases by category with concrete examples and fixes.

---

## Empty Input

**Problem:** Empty array, empty string, empty tree (null root), empty graph (no edges).

```cpp
// BUG: returns arr[0] which is undefined behavior
int findMin(vector<int>& arr) { return arr[0]; }

// FIX: handle empty input
int findMin(vector<int>& arr) {
    if (arr.empty()) throw invalid_argument("empty array");
    return *min_element(arr.begin(), arr.end());
}
```

**Rule:** Always check for empty containers as the first line. In interviews, explicitly mention: "I'll handle the empty case first."

---

## Single Element

**Problem:** Arrays of length 1 break median-finding (needs two elements for average), binary search (already found), graph algorithms (no edges to traverse).

Common failure: `median = (nums[left] + nums[right]) / 2` — if left == right, this is correct, but if the problem expects the median of a subarray with one element, make sure the logic doesn't divide by zero elsewhere.

---

## Duplicates

**Problem:** Binary search on answer when multiple elements have the same value, sorting stability, counting vs. finding distinct elements.

```cpp
// BUG: finds ANY position of target, not first/last
int search(vector<int>& a, int t) {
    int lo = 0, hi = a.size() - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] == t) return mid; // might not be first occurrence
        else if (a[mid] < t) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
```

For "first occurrence": when `a[mid] == t`, set `hi = mid - 1` and track the answer. For "last occurrence": set `lo = mid + 1`.

**Graphs:** Dijkstra assumes no negative edges. With duplicates in adjacency lists, ensure no double-counting.

---

## Negative Values and Overflow

**Problem:** Integer overflow in intermediate calculations, negative modulo results, negative indices.

```cpp
// BUG: overflow when computing mid
int mid = (lo + hi) / 2;       // overflow if lo + hi > INT_MAX

// FIX:
int mid = lo + (hi - lo) / 2; // safe

// BUG: negative modulo
int r = (-7) % 3;  // C++: r = -1 (implementation-defined in C++03)

// FIX:
int r = ((-7) % 3 + 3) % 3;  // r = 2
```

**Critical:** `a * b` can overflow even when the final result fits in the range. Always cast to `long long` before multiplication when values approach INT_MAX.

---

## Large Input Handling

**Problem:** Input size exceeds expected, causing TLE or MLE.

- **Stack overflow from recursion:** Convert to iterative or increase stack size. A recursive DFS on a chain of 10^5 nodes uses 10^5 stack frames (~800KB), which may exceed default limits.
- **Memory for DP tables:** `dp[10^5][10^5]` needs 40GB. Use rolling arrays or compress the state.
- **Reading input:** Use fast I/O (see competitive programming techniques chapter).

```python
# Increase Python recursion limit for deep trees
import sys
sys.setrecursionlimit(10**6)
```

---

## Sorted / Reverse Sorted Input

**Problem:** Quicksort degrades to O(n^2) on sorted input. BSTs become linked lists. Some heuristics fail on monotonic sequences.

**Interview test:** "What happens to your algorithm if the input is already sorted?"

- **QuickSort fix:** Randomize pivot selection or use median-of-three.
- **BST fix:** Use balanced trees (AVL, Red-Black) or skip lists.
- **Sliding window:** Already-sorted input means the window never shrinks — verify the shrink condition works.

---

## Cyclic Structures

**Problem:** Linked list cycles, graph cycles, circular arrays.

- **Linked list:** Floyd's cycle detection (slow/fast pointers). Don't forget the cycle may not include the head.
- **Graph cycles:** DFS with coloring (0=unvisited, 1=in-stack, 2=done) for cycle detection. Topological sort fails on cyclic graphs.
- **Circular array:** When implementing a queue with a circular buffer, handle the wrap-around: `(rear + 1) % capacity`.

---

## Disconnected Graphs

**Problem:** BFS/DFS only visits one component. Shortest path algorithms return infinity for unreachable nodes.

```cpp
// BUG: assumes graph is connected
vector<int> bfs(int start, const vector<vector<int>>& adj) {
    vector<int> dist(adj.size(), -1);
    queue<int> q;
    q.push(start); dist[start] = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u])
            if (dist[v] == -1) { dist[v] = dist[u] + 1; q.push(v); }
    }
    // dist[i] == -1 means unreachable — must be handled downstream
    return dist;
}
```

**Always check:** If the problem says "graph" not "connected graph," handle disconnected components explicitly.

---

## Self-Loops and Parallel Edges

**Problem:** Self-loops break Dijkstra (zero-distance cycle), affect degree counting, confuse DFS (infinite loop without visited check).

Parallel edges: minimum spanning tree algorithms handle them correctly (Kruskal just picks the smallest), but shortest path with BFS on unweighted graph may count the same edge twice.

---

## Skewed Trees

**Problem:** A tree that's essentially a linked list breaks balanced-tree assumptions. Tree DP recursion depth equals tree height.

For tree DP: if the tree is a chain, ensure your DP handles the base case correctly (leaf node with no children).

---

## Floating Point Precision

**Problem:** `0.1 + 0.2 != 0.3` in most languages. Never compare floats with `==`.

```cpp
// BUG:
if (a == b) ...           // wrong for floats

// FIX:
if (fabs(a - b) < 1e-9) ...  // epsilon comparison
```

**Geometric algorithms** are particularly vulnerable. Use integer arithmetic (cross products, orientation tests) whenever possible. When unavoidable, use a tolerance of 1e-9 for doubles.

---

## Interview Traps Around Edge Cases

1. **"What if the array has all identical elements?"** — Tests if sorting/binary search/quickselect handles duplicates.
2. **"What if n = 0 or n = 1?"** — Tests base case handling.
3. **"What if all elements are negative?"** — Tests if max-subarray or max-product handles non-positive arrays.
4. **"What if the graph has self-loops?"** — Tests robustness of graph algorithms.
5. **"What if there are multiple valid answers?"** — Tests if you return any valid one or a specific one.
6. **"What if elements are very large (10^18)?"** — Tests overflow awareness.
7. **"What if the tree is just a single node?"** — Tests base case for tree algorithms.
8. **"What if the input string is empty?"** — Tests first thing you should check.

---

## Interview Questions

1. **Your binary search returns -1 for a valid search.** What are the most likely bugs? Walk through all of them.

2. **Implement merge sort.** What happens with an array of size 1? An array of size 0? All duplicates?

3. **Find the median of a data stream.** What edge cases does your solution have? How do you handle a single element?

4. **Implement Dijkstra's algorithm.** What happens with negative edges? Self-loops? Disconnected nodes?

5. **Write a function to check if a binary tree is a BST.** What about an empty tree? A tree with one node? A tree with INT_MIN or INT_MAX values?

6. **Implement an LRU cache.** What happens when capacity is 0? When you access a non-existent key? When all operations are puts?

7. **Design a function to detect a cycle in a linked list.** What if the cycle starts at the head? What if there's no cycle? What if the list has one node?

8. **Implement interval merging.** What about overlapping intervals that share an endpoint? What about a single interval? Empty input? Intervals in reverse order?