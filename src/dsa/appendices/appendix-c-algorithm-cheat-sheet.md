# Appendix C: Algorithm Cheat Sheet

Quick reference for every major algorithm: when to use, pseudocode, complexity, and key insight.

---

## 1. Binary Search

**When:** Sorted array, monotonic function, search space reduction.

```
function binary_search(arr, target):
    lo = 0, hi = n - 1
    while lo <= hi:
        mid = lo + (hi - lo) / 2
        if arr[mid] == target: return mid
        if arr[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1
```

**Complexity:** O(log n) time, O(1) space.

**Key insight:** Eliminate half the search space each iteration. Works on any monotonic predicate, not just sorted arrays.

**Variants:**
- Find first occurrence: `if arr[mid] >= target: hi = mid`
- Find last occurrence: `if arr[mid] <= target: lo = mid`
- Find insertion point: standard lower_bound

---

## 2. Two Pointers

**When:** Sorted arrays, pair finding, partition problems, removing duplicates.

```
function two_sum_sorted(arr, target):
    lo = 0, hi = n - 1
    while lo < hi:
        sum = arr[lo] + arr[hi]
        if sum == target: return (lo, hi)
        if sum < target: lo++
        else: hi--
    return (-1, -1)
```

**Complexity:** O(n) time, O(1) space.

**Key insight:** When the array is sorted, moving pointers based on the current sum eliminates the need for nested loops.

---

## 3. Sliding Window

**When:** Subarray/substring problems with contiguous elements.

```
function max_sum_subarray(arr, k):
    window_sum = sum(arr[0..k-1])
    max_sum = window_sum
    for i = k to n-1:
        window_sum += arr[i] - arr[i-k]
        max_sum = max(max_sum, window_sum)
    return max_sum
```

**Complexity:** O(n) time, O(1) space.

**Variable size window:**
```
function min_subarray_len(arr, target):
    lo = 0, sum = 0, min_len = INF
    for hi = 0 to n-1:
        sum += arr[hi]
        while sum >= target:
            min_len = min(min_len, hi - lo + 1)
            sum -= arr[lo++]
    return min_len == INF ? 0 : min_len
```

---

## 4. BFS (Breadth-First Search)

**When:** Shortest path in unweighted graph, level-order traversal, minimum steps.

```
function bfs(graph, start):
    queue = {start}
    visited = {start}
    while queue not empty:
        node = queue.dequeue()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.enqueue(neighbor)
```

**Complexity:** O(V + E) time, O(V) space.

**Key insight:** BFS explores nodes in order of distance from start. First time you reach a node, that's the shortest path.

---

## 5. DFS (Depth-First Search)

**When:** Path finding, cycle detection, topological sort, connected components, backtracking.

```
function dfs(graph, node, visited):
    visited.add(node)
    for neighbor in graph[node]:
        if neighbor not in visited:
            dfs(graph, neighbor, visited)
```

**Complexity:** O(V + E) time, O(V) space (recursion stack).

**Key insight:** DFS goes as deep as possible before backtracking. Use for exhaustive search and when you need to explore all paths.

---

## 6. Dijkstra's Algorithm

**When:** Shortest path with non-negative edge weights.

```
function dijkstra(graph, source):
    dist[source] = 0
    pq = {(0, source)}  // min-heap
    while pq not empty:
        (d, u) = pq.extract_min()
        if d > dist[u]: continue  // stale entry
        for (v, weight) in graph[u]:
            if dist[u] + weight < dist[v]:
                dist[v] = dist[u] + weight
                pq.insert((dist[v], v))
    return dist
```

**Complexity:** O((V + E) log V) with binary heap, O(V log V + E) with Fibonacci heap.

**Key insight:** Greedy approach — always process the closest unvisited node. Does NOT work with negative edges.

---

## 7. Bellman-Ford

**When:** Shortest path with negative edges, detecting negative cycles.

```
function bellman_ford(edges, source, V):
    dist[source] = 0
    for i = 1 to V-1:
        for (u, v, w) in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    // Check for negative cycle
    for (u, v, w) in edges:
        if dist[u] + w < dist[v]:
            return "Negative cycle detected"
    return dist
```

**Complexity:** O(VE) time, O(V) space.

**Key insight:** After V-1 iterations, all shortest paths are found (unless negative cycle exists). The V-th iteration detects negative cycles.

---

## 8. Floyd-Warshall

**When:** All-pairs shortest path, transitive closure.

```
function floyd_warshall(dist, V):
    for k = 0 to V-1:
        for i = 0 to V-1:
            for j = 0 to V-1:
                dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
```

**Complexity:** O(V³) time, O(V²) space.

**Key insight:** "DP over intermediate vertices." dist[i][j] after iteration k uses only vertices 0..k as intermediates.

---

## 9. Kruskal's Algorithm (MST)

**When:** Minimum spanning tree, edge list representation.

```
function kruskal(edges, V):
    sort edges by weight
    dsu = new DSU(V)
    mst = []
    for (u, v, w) in edges:
        if dsu.find(u) != dsu.find(v):
            dsu.union(u, v)
            mst.append((u, v, w))
    return mst
```

**Complexity:** O(E log E) time, O(V) space.

**Key insight:** Greedy — always take the cheapest edge that doesn't create a cycle. DSU efficiently checks for cycles.

---

## 10. Prim's Algorithm (MST)

**When:** Minimum spanning tree, adjacency list representation.

```
function prim(graph, start):
    pq = {(0, start)}
    visited = {}
    total_weight = 0
    while pq not empty:
        (w, u) = pq.extract_min()
        if u in visited: continue
        visited.add(u)
        total_weight += w
        for (v, weight) in graph[u]:
            if v not in visited:
                pq.insert((weight, v))
    return total_weight
```

**Complexity:** O((V + E) log V) with binary heap, O(V²) with adjacency matrix.

**Key insight:** Like Dijkstra, but we add edges instead of tracking distances. Greedy — grow the tree by always adding the cheapest crossing edge.

---

## 11. Topological Sort

**When:** DAG ordering, dependency resolution, task scheduling.

**DFS-based:**
```
function topo_sort(graph, V):
    visited = {}
    order = []
    for each node in V:
        if node not in visited:
            dfs(node, visited, order)
    return reverse(order)

function dfs(node, visited, order):
    visited.add(node)
    for neighbor in graph[node]:
        if neighbor not in visited:
            dfs(neighbor, visited, order)
    order.append(node)  // post-order
```

**BFS-based (Kahn's):**
```
function kahn(graph, V):
    in_degree = compute_in_degrees(graph)
    queue = {nodes with in_degree 0}
    order = []
    while queue not empty:
        node = queue.dequeue()
        order.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor]--
            if in_degree[neighbor] == 0:
                queue.enqueue(neighbor)
    if len(order) != V: return "Cycle detected"
    return order
```

**Complexity:** O(V + E) time, O(V) space.

---

## 12. Union-Find (DSU)

**When:** Disjoint set operations, connected components, cycle detection.

```
class DSU:
    parent = []
    rank = []

    function find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])  // path compression
        return parent[x]

    function union(x, y):
        rx = find(x), ry = find(y)
        if rx == ry: return false
        if rank[rx] < rank[ry]: swap(rx, ry)
        parent[ry] = rx
        if rank[rx] == rank[ry]: rank[rx]++
        return true
```

**Complexity:** O(α(n)) ≈ O(1) per operation with path compression + union by rank.

---

## 13. Segment Tree

**When:** Range queries (sum, min, max) with point/range updates.

```
function build(node, lo, hi):
    if lo == hi:
        tree[node] = arr[lo]
        return
    mid = (lo + hi) / 2
    build(2*node, lo, mid)
    build(2*node+1, mid+1, hi)
    tree[node] = tree[2*node] + tree[2*node+1]

function query(node, lo, hi, ql, qh):
    if ql > hi or qh < lo: return 0
    if ql <= lo and hi <= qh: return tree[node]
    mid = (lo + hi) / 2
    return query(2*node, lo, mid, ql, qh) +
           query(2*node+1, mid+1, hi, ql, qh)

function update(node, lo, hi, idx, val):
    if lo == hi:
        tree[node] = val
        return
    mid = (lo + hi) / 2
    if idx <= mid: update(2*node, lo, mid, idx, val)
    else: update(2*node+1, mid+1, hi, idx, val)
    tree[node] = tree[2*node] + tree[2*node+1]
```

**Complexity:** O(n) build, O(log n) query and update, O(n) space.

---

## 14. Fenwick Tree (BIT)

**When:** Prefix sums, point updates. Simpler than segment tree for these operations.

```
function update(i, delta):
    while i <= n:
        tree[i] += delta
        i += i & (-i)  // add LSB

function query(i):  // prefix sum [1..i]
    sum = 0
    while i > 0:
        sum += tree[i]
        i -= i & (-i)  // remove LSB
    return sum

function range_query(l, r):
    return query(r) - query(l-1)
```

**Complexity:** O(log n) per operation, O(n) space.

**Key insight:** `i & (-i)` gives the lowest set bit. This determines which ranges each index is responsible for.

---

## 15. KMP (Knuth-Morris-Pratt)

**When:** Pattern matching in strings.

```
function compute_lps(pattern):
    lps = [0] * len(pattern)
    len = 0, i = 1
    while i < len(pattern):
        if pattern[i] == pattern[len]:
            len++
            lps[i] = len
            i++
        else:
            if len != 0: len = lps[len-1]
            else: lps[i] = 0, i++
    return lps

function kmp_search(text, pattern):
    lps = compute_lps(pattern)
    i = 0, j = 0
    while i < len(text):
        if text[i] == pattern[j]: i++, j++
        if j == len(pattern):
            found at i - j
            j = lps[j-1]
        elif i < len(text) and text[i] != pattern[j]:
            if j != 0: j = lps[j-1]
            else: i++
```

**Complexity:** O(n + m) time, O(m) space.

**Key insight:** The LPS array tells us how far to backtrack in the pattern when a mismatch occurs, avoiding redundant comparisons.

---

## 16. Z Algorithm

**When:** Pattern matching, finding all occurrences.

```
function compute_z(s):
    n = len(s)
    z = [0] * n
    l = r = 0
    for i = 1 to n-1:
        if i <= r:
            z[i] = min(r - i + 1, z[i - l])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i]++
        if i + z[i] - 1 > r:
            l = i, r = i + z[i] - 1
    return z

function search(text, pattern):
    s = pattern + "$" + text
    z = compute_z(s)
    for i = len(pattern)+1 to len(s)-1:
        if z[i] == len(pattern):
            found at i - len(pattern) - 1
```

**Complexity:** O(n + m) time, O(n + m) space.

---

## 17. Trie

**When:** Prefix queries, autocomplete, XOR problems.

```
class TrieNode:
    children = {}
    is_end = false

class Trie:
    root = new TrieNode()

    function insert(word):
        node = root
        for char in word:
            if char not in node.children:
                node.children[char] = new TrieNode()
            node = node.children[char]
        node.is_end = true

    function search(word):
        node = root
        for char in word:
            if char not in node.children: return false
            node = node.children[char]
        return node.is_end

    function starts_with(prefix):
        node = root
        for char in prefix:
            if char not in node.children: return false
            node = node.children[char]
        return true
```

**Complexity:** O(L) per operation, L = word length.

---

## 18. Backtracking

**When:** Generate all solutions, constraint satisfaction, permutations/combinations/subsets.

```
function backtrack(state, choices, result):
    if is_solution(state):
        result.add(copy(state))
        return
    for choice in choices:
        if is_valid(choice, state):
            make_choice(choice, state)
            backtrack(state, choices, result)
            undo_choice(choice, state)  // backtrack
```

**Key insight:** Explore all possibilities by making choices, recursing, and undoing choices. Prune early when a partial solution can't lead to a valid complete solution.

---

## 19. Dynamic Programming

### 19.1 Top-Down (Memoization)

```
function dp(state):
    if state in memo: return memo[state]
    if is_base_case(state): return base_value
    result = 0
    for transition in transitions(state):
        result = combine(result, dp(next_state))
    memo[state] = result
    return result
```

### 19.2 Bottom-Up (Tabulation)

```
function dp(states):
    initialize dp_table
    set base cases
    for state in order:
        for transition in transitions(state):
            dp_table[state] = combine(dp_table[state], dp_table[prev_state])
    return dp_table[target]
```

### 19.3 Common DP Patterns

| Pattern | Transition | Example |
|---------|-----------|---------|
| Linear | dp[i] = f(dp[i-1], dp[i-2], ...) | Fibonacci, climbing stairs |
| Grid | dp[i][j] = f(dp[i-1][j], dp[i][j-1]) | Unique paths, minimum path sum |
| Knapsack | dp[i][w] = max(dp[i-1][w], dp[i-1][w-wi]+vi) | 0/1 knapsack |
| Interval | dp[i][j] = min/max(dp[i][k] + dp[k+1][j] + cost) | Matrix chain |
| Subsequence | dp[i] = max(dp[j] + 1) for j < i | LIS |
| String | dp[i][j] = f(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) | LCS, edit distance |
| Bitmask | dp[mask] = f(dp[mask ^ (1<<i)]) | TSP, assignment |
| Digit | dp[pos][tight][state] | Count numbers |

---

## 20. Monotonic Stack

**When:** Next greater/smaller element, histogram problems, stock span.

```
function next_greater_element(arr):
    n = len(arr)
    result = [-1] * n
    stack = []
    for i = 0 to n-1:
        while stack not empty and arr[stack.top()] < arr[i]:
            result[stack.pop()] = arr[i]
        stack.push(i)
    return result
```

**Complexity:** O(n) time, O(n) space.

**Key insight:** Each element is pushed and popped at most once, so total operations are O(n).

---

## 21. Monotonic Queue (Deque)

**When:** Sliding window minimum/maximum.

```
function sliding_window_max(arr, k):
    dq = deque()  // stores indices
    result = []
    for i = 0 to n-1:
        while dq not empty and dq.front() <= i - k:
            dq.pop_front()
        while dq not empty and arr[dq.back()] <= arr[i]:
            dq.pop_back()
        dq.push_back(i)
        if i >= k - 1:
            result.append(arr[dq.front()])
    return result
```

**Complexity:** O(n) time, O(k) space.

---

## 22. Lowest Common Ancestor (LCA)

**When:** Tree queries involving ancestors. Binary lifting approach.

```
Preprocessing: O(n log n)
    for each node: up[node][0] = parent[node]
    for j = 1 to LOG:
        for each node:
            up[node][j] = up[up[node][j-1]][j-1]

function lca(u, v):
    if depth[u] < depth[v]: swap(u, v)
    // Lift u to same depth as v
    diff = depth[u] - depth[v]
    for j = 0 to LOG:
        if diff & (1 << j): u = up[u][j]
    if u == v: return u
    // Binary lift both
    for j = LOG downto 0:
        if up[u][j] != up[v][j]:
            u = up[u][j]
            v = up[v][j]
    return up[u][0]
```

**Complexity:** O(n log n) preprocessing, O(log n) per query.

---

## 23. Tarjan's SCC Algorithm

**When:** Finding strongly connected components in directed graphs.

```
function tarjan_scc(graph):
    index = 0
    stack = []
    on_stack = {}
    indices = {}
    lowlink = {}
    sccs = []

    function strongconnect(v):
        indices[v] = lowlink[v] = index++
        stack.push(v)
        on_stack.add(v)
        for w in graph[v]:
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            scc = []
            do:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
            while w != v
            sccs.append(scc)

    for v in graph:
        if v not in indices: strongconnect(v)
    return sccs
```

**Complexity:** O(V + E) time, O(V) space.

---

## 24. Convex Hull (Andrew's Monotone Chain)

**When:** Finding the convex hull of a set of points.

```
function convex_hull(points):
    sort points by (x, y)
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]
```

**Complexity:** O(n log n) time, O(n) space.

---

## 25. Manacher's Algorithm

**When:** Finding all palindromic substrings in O(n).

```
function manacher(s):
    t = "^#" + "#".join(s) + "#$"
    n = len(t)
    p = [0] * n
    center = right = 0
    for i = 1 to n-2:
        mirror = 2 * center - i
        if i < right:
            p[i] = min(right - i, p[mirror])
        while t[i + p[i] + 1] == t[i - p[i] - 1]:
            p[i]++
        if i + p[i] > right:
            center = i, right = i + p[i]
    return p
```

**Complexity:** O(n) time, O(n) space.

**Key insight:** Use previously computed palindrome information to avoid redundant comparisons. The right boundary acts as a "mirror."

---

## 26. Edmonds-Karp (Max Flow)

**When:** Maximum flow in a network.

```
function edmonds_karp(graph, source, sink):
    max_flow = 0
    while bfs finds augmenting path:
        path_flow = min residual capacity along path
        max_flow += path_flow
        update residual graph
    return max_flow
```

**Complexity:** O(VE²) time, O(V + E) space.

---

## 27. Dinic's Algorithm (Max Flow)

**When:** Maximum flow, faster than Edmonds-Karp for many cases.

```
function dinic(graph, source, sink):
    max_flow = 0
    while bfs builds level graph:
        while dfs finds blocking flow:
            max_flow += flow
    return max_flow
```

**Complexity:** O(V²E) time, O(V + E) space. O(E√V) for unit capacity graphs.

---

## 28. Euler's Totient Function

**When:** Count numbers coprime to n, modular arithmetic.

```
function phi(n):
    result = n
    for p = 2 to sqrt(n):
        if n % p == 0:
            while n % p == 0: n /= p
            result -= result / p
    if n > 1: result -= result / n
    return result
```

**Complexity:** O(√n) time.

---

## 29. Sieve of Eratosthenes

**When:** Finding all primes up to n.

```
function sieve(n):
    is_prime = [true] * (n + 1)
    is_prime[0] = is_prime[1] = false
    for i = 2 to sqrt(n):
        if is_prime[i]:
            for j = i*i to n step i:
                is_prime[j] = false
    return is_prime
```

**Complexity:** O(n log log n) time, O(n) space.

**Linear sieve:**
```
function linear_sieve(n):
    is_prime = [true] * (n + 1)
    primes = []
    for i = 2 to n:
        if is_prime[i]: primes.append(i)
        for p in primes:
            if i * p > n: break
            is_prime[i * p] = false
            if i % p == 0: break
    return primes
```

**Complexity:** O(n) time, O(n) space.

---

## 30. Modular Exponentiation

**When:** Computing a^b mod m efficiently.

```
function power(a, b, m):
    result = 1
    a = a % m
    while b > 0:
        if b is odd: result = (result * a) % m
        b = b >> 1
        a = (a * a) % m
    return result
```

**Complexity:** O(log b) time, O(1) space.

---

## 31. LIS (Longest Increasing Subsequence)

**When:** Find longest increasing subsequence.

```
function lis(arr):
    tails = []  // smallest tail of LIS of length i
    for x in arr:
        pos = lower_bound(tails, x)
        if pos == len(tails): tails.append(x)
        else: tails[pos] = x
    return len(tails)
```

**Complexity:** O(n log n) time, O(n) space.

**Key insight:** `tails[i]` stores the smallest possible last element of an increasing subsequence of length `i+1`.

---

## 32. Edmonds' Blossom Algorithm

**When:** Maximum matching in general (non-bipartite) graphs.

**Complexity:** O(V³) time, O(V + E) space.

**Key insight:** Shrinks odd-length cycles (blossoms) into single vertices and recurses.

---

## 33. Hungarian Algorithm

**When:** Minimum cost bipartite matching, assignment problem.

**Complexity:** O(V³) time, O(V²) space.

---

## 34. Aho-Corasick

**When:** Multiple pattern matching in text.

**Complexity:** O(m) preprocessing (m = total pattern length), O(n + k) search (n = text length, k = matches).

**Key insight:** Combines a trie with failure links (like KMP's LPS generalized to a trie).

---

## 35. Suffix Array

**When:** String problems requiring sorted suffixes, LCP queries.

```
// SA-IS algorithm (linear time)
function build_suffix_array(s):
    // ... SA-IS construction
    return suffix_array

// Kasai's algorithm for LCP
function build_lcp(s, sa):
    n = len(s)
    rank = inverse(sa)
    lcp = [0] * (n - 1)
    k = 0
    for i = 0 to n-1:
        if rank[i] == 0: continue
        j = sa[rank[i] - 1]
        while s[i + k] == s[j + k]: k++
        lcp[rank[i] - 1] = k
        if k > 0: k--
    return lcp
```

**Complexity:** O(n log n) with doubling, O(n) with SA-IS.

---

## Quick Decision Matrix

| Problem | Algorithm | Time |
|---------|-----------|------|
| Find element in sorted array | Binary Search | O(log n) |
| Shortest path (unweighted) | BFS | O(V+E) |
| Shortest path (non-negative weights) | Dijkstra | O((V+E)logV) |
| Shortest path (negative weights) | Bellman-Ford | O(VE) |
| All-pairs shortest path | Floyd-Warshall | O(V³) |
| MST | Kruskal / Prim | O(E logV) |
| Topological order | DFS / Kahn's | O(V+E) |
| Connected components | DFS / DSU | O(V+E) |
| Strongly connected components | Tarjan / Kosaraju | O(V+E) |
| Maximum flow | Dinic | O(V²E) |
| Range sum query | Fenwick / Segment Tree | O(log n) |
| Range min query | Segment Tree / Sparse Table | O(log n) / O(1) |
| Pattern matching | KMP / Z Algorithm | O(n+m) |
| Longest increasing subsequence | DP + Binary Search | O(n log n) |
| All permutations | Backtracking / next_permutation | O(n!) |
| Shortest palindromic substring | Manacher | O(n) |

---

*This cheat sheet covers the essential algorithms you need. For each algorithm, understand when to use it, the key insight, and the complexity.*
