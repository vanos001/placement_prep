# Appendix H: Top 200 Mistakes

The most common mistakes in coding interviews and competitive programming, organized by category. For each mistake, the correct approach is provided.

---

## 1. Off-By-One Errors (1-20)

### 1. Wrong loop upper bound
**Mistake:** `for (int i = 0; i <= n; i++) arr[i]` — accesses `arr[n]`
**Correct:** `for (int i = 0; i < n; i++) arr[i]`

### 2. Wrong loop lower bound
**Mistake:** `for (int i = 1; i < n; i++)` when iterating all elements
**Correct:** `for (int i = 0; i < n; i++)`

### 3. Binary search with wrong bounds
**Mistake:** `int hi = n` with `while (lo <= hi)`
**Correct:** Use `int hi = n` with `while (lo < hi)` (half-open) OR `int hi = n-1` with `while (lo <= hi)` (closed)

### 4. String substring off-by-one
**Mistake:** `s.substr(i, j)` thinking it means `[i, j]`
**Correct:** `s.substr(i, j)` means starting at `i`, length `j`. For range `[i, j)`: `s.substr(i, j-i)`

### 5. Fence post error
**Mistake:** n+1 posts for n fences
**Correct:** n-1 fences for n posts, or n+1 segments for n cuts

### 6. Array size off-by-one
**Mistake:** `int arr[n]` with index `n`
**Correct:** Valid indices are `0` to `n-1`

### 7. Reverse iteration with unsigned
**Mistake:** `for (size_t i = n-1; i >= 0; i--)` — wraps around when `i` goes below 0
**Correct:** `for (int i = n-1; i >= 0; i--)` (use signed type)

### 8. Missing last element
**Mistake:** `for (int i = 0; i < n-1; i++)` when you need all elements
**Correct:** `for (int i = 0; i < n; i++)`

### 9. Double-counting boundary
**Mistake:** Overlapping ranges `[a, b]` and `[b, c]`
**Correct:** Use `[a, b)` and `[b, c)` or `[a, b]` and `[b+1, c]`

### 10. Wrong split point
**Mistake:** `int mid = (lo + hi) / 2` causing infinite loop
**Correct:** For "find max" pattern: `int mid = lo + (hi - lo + 1) / 2`

### 11. Grid boundary not checked
**Mistake:** Accessing `grid[r][c]` without checking `0 <= r < rows` and `0 <= c < cols`
**Correct:** Always check boundaries before access

### 12. Wrong number of iterations
**Mistake:** Running a loop `n` times when you need `n-1` (or vice versa)
**Correct:** Carefully count: n elements need n-1 comparisons for adjacent pairs

### 13. Zero-indexed vs one-indexed confusion
**Mistake:** Using 1-indexed logic on 0-indexed array
**Correct:** Be consistent. If problem uses 1-indexed, convert: `arr[i-1]`

### 14. Wrong prefix sum range
**Mistake:** `prefix[r] - prefix[l]` for range `[l, r]`
**Correct:** `prefix[r] - prefix[l-1]` (1-indexed) or `prefix[r+1] - prefix[l]` (0-indexed prefix)

### 15. Segment tree wrong range
**Mistake:** Building with `[0, n]` instead of `[0, n-1]`
**Correct:** Use `[0, n-1]` for n elements

### 16. Wrong binary search termination
**Mistake:** `while (lo < hi)` with `hi = mid` and `lo = mid` (infinite loop!)
**Correct:** If `hi = mid`, use `lo = mid + 1`. If `lo = mid`, use `hi = mid - 1` (or `mid = lo + (hi-lo+1)/2`)

### 17. Missing +1 in ceiling division
**Mistake:** `int mid = (lo + hi) / 2` when you need ceiling
**Correct:** `int mid = lo + (hi - lo + 1) / 2`

### 18. Wrong count in combinations
**Mistake:** `C(n, k)` when you need `C(n-1, k-1)`
**Correct:** Read the problem carefully — is it "choose k from n" or "choose k-1 from n-1"?

### 19. Array initialization off-by-one
**Mistake:** `vector<int> dp(n)` then accessing `dp[n]`
**Correct:** `vector<int> dp(n+1)` if you need index `n`

### 20. Wrong depth in tree
**Mistake:** Root at depth 0 but counting edges as depth
**Correct:** Be consistent: root depth = 0 (edges from root) or root depth = 1 (nodes from root)

---

## 2. Integer Overflow (21-40)

### 21. Multiplication overflow
**Mistake:** `int prod = a * b` where `a, b` can be up to 10⁹
**Correct:** `long long prod = 1LL * a * b`

### 22. Sum overflow
**Mistake:** `int sum = 0; for(...) sum += x;`
**Correct:** `long long sum = 0;`

### 23. Power overflow
**Mistake:** `int p = pow(2, 31)` — overflows `int`
**Correct:** Use `long long` or modular exponentiation

### 24. Modular multiplication overflow
**Mistake:** `(a * b) % MOD` where `a, b` are up to 10⁹
**Correct:** `(1LL * a * b) % MOD`

### 25. Accumulate with wrong type
**Mistake:** `accumulate(v.begin(), v.end(), 0)` — returns `int`
**Correct:** `accumulate(v.begin(), v.end(), 0LL)` — returns `long long`

### 26. INT_MIN absolute value
**Mistake:** `abs(INT_MIN)` — overflows!
**Correct:** `abs((long long)INT_MIN)`

### 27. Negative modulo
**Mistake:** `(-7) % 3` gives `-1` in C++
**Correct:** `((-7) % 3 + 3) % 3` gives `2`

### 28. Unsigned underflow
**Mistake:** `unsigned int x = 0; x - 1` wraps to `UINT_MAX`
**Correct:** Use signed types for subtraction

### 29. Factorial overflow
**Mistake:** `int fact = 1; for(int i=1; i<=20; i++) fact *= i;` — overflows after 12!
**Correct:** Use `long long` (up to 20) or modular arithmetic

### 30. Fibonacci overflow
**Mistake:** `int fib[n]` for large `n`
**Correct:** Use `long long` or modular arithmetic

### 31. Distance squared overflow
**Mistake:** `int d = (x2-x1)*(x2-x1) + (y2-y1)*(y2-y1)`
**Correct:** `long long d = ...`

### 32. Bit shift overflow
**Mistake:** `1 << 31` — undefined behavior for `int`
**Correct:** `1LL << 31` or `(unsigned)1 << 31`

### 33. Size of int confusion
**Mistake:** Assuming `int` is 64-bit
**Correct:** `int` is 32-bit. Use `long long` for 64-bit.

### 34. Intermediate calculation overflow
**Mistake:** `(a + b) / 2` where `a + b` overflows
**Correct:** `a + (b - a) / 2`

### 35. Product of averages
**Mistake:** `avg(a) * avg(b)` ≠ `avg(a * b)`
**Correct:** Compute the actual value, not the product of averages

### 36. Sum of squares overflow
**Mistake:** `int sum = n*(n+1)*(2*n+1)/6` for large `n`
**Correct:** Use `long long` for the computation

### 37. Modular inverse with wrong modulus
**Mistake:** Using `power(a, MOD-2, MOD)` when `MOD` is not prime
**Correct:** Use extended Euclidean algorithm for non-prime modulus

### 38. Double as integer
**Mistake:** `double x = 1e18; int y = x;` — may lose precision
**Correct:** Use `long long` for large integers

### 39. Power of 10 overflow
**Mistake:** `int x = 10^9` (bitwise XOR, not power!)
**Correct:** `int x = 1000000000` or `int x = 1e9`

### 40. Modulo with wrong operator precedence
**Mistake:** `a + b % MOD` (only `b` is modded)
**Correct:** `(a + b) % MOD`

---

## 3. Null Pointer / Segmentation Fault (41-55)

### 41. Dereferencing null
**Mistake:** `node->val` when `node` is `nullptr`
**Correct:** Check `if (node)` before access

### 42. Accessing empty container
**Mistake:** `v.front()` when `v` is empty
**Correct:** Check `if (!v.empty())` first

### 43. Missing null check in tree DFS
**Mistake:** `dfs(node->left)` without checking if `node` is null
**Correct:** `if (node == nullptr) return;` at start of function

### 44. Iterator after erase
**Mistake:** `v.erase(it); it++;` — `it` is invalidated
**Correct:** `it = v.erase(it);` (erase returns next iterator)

### 45. Using invalidated pointer
**Mistake:** `int* p = &v[0]; v.push_back(1); *p;` — may be invalidated
**Correct:** Don't hold pointers/references to vector elements across modifications

### 46. Stack overflow from deep recursion
**Mistake:** DFS on a graph with 10⁵ nodes recursively
**Correct:** Use iterative DFS or increase stack size

### 47. Null string operations
**Mistake:** `string s; s[0]` — undefined for empty string
**Correct:** Check `if (!s.empty())` first

### 48. Map default insertion
**Mistake:** `mp[key]` in read-only context creates default entry
**Correct:** Use `mp.find(key)` or `mp.count(key)`

### 49. Accessing end iterator
**Mistake:** `*m.end()` — `end()` points past the last element
**Correct:** `*prev(m.end())` for last element

### 50. Priority queue top after pop
**Mistake:** `int x = pq.top(); pq.pop(); // x is valid, but ref would be dangling`
**Correct:** Copy the value before popping

### 51. Returning reference to local
**Mistake:** `int& f() { int x = 5; return x; }` — dangling reference
**Correct:** Return by value

### 52. Array delete mismatch
**Mistake:** `int* p = new int[10]; delete p;` (should be `delete[]`)
**Correct:** `delete[] p;` for arrays

### 53. Double free
**Mistake:** `delete p; delete p;`
**Correct:** Set `p = nullptr` after delete

### 54. Accessing after end of string
**Mistake:** `s[s.size()]` — out of bounds
**Correct:** Valid indices are `0` to `s.size()-1`

### 55. Uninitialized pointer
**Mistake:** `int* p; *p = 5;` — undefined behavior
**Correct:** `int* p = nullptr;` or `int* p = new int;`

---

## 4. Logic Errors (56-80)

### 56. Greedy when DP needed
**Mistake:** Using greedy for coin change: coins = [1,3,4], amount = 6 → greedy gives 4+1+1=3, optimal is 3+3=2
**Correct:** Use DP when greedy property doesn't hold

### 57. BFS when DFS needed
**Mistake:** Using BFS to find all paths
**Correct:** Use DFS for exhaustive search, BFS for shortest path

### 58. Wrong graph representation
**Mistake:** Using adjacency matrix for sparse graph (n=10⁵)
**Correct:** Use adjacency list for sparse graphs

### 59. Not considering disconnected graph
**Mistake:** Running DFS from node 0 only
**Correct:** Run DFS from all unvisited nodes

### 60. Wrong direction in directed graph
**Mistake:** Treating directed edges as undirected
**Correct:** Only traverse in the edge direction

### 61. Missing cycle detection
**Mistake:** Not checking for cycles in dependency graph
**Correct:** Use topological sort or DFS with coloring

### 62. Wrong base case in DP
**Mistake:** `dp[0] = 0` when it should be `dp[0] = 1`
**Correct:** Verify base case with small examples

### 63. Wrong transition in DP
**Mistake:** `dp[i] = dp[i-1] + dp[i-2]` when the recurrence is different
**Correct:** Derive the recurrence carefully from the problem

### 64. Not initializing DP array
**Mistake:** `vector<int> dp(n);` — values are 0, may be wrong
**Correct:** Initialize to `INT_MAX`, `-1`, or appropriate base values

### 65. Wrong order in bottom-up DP
**Mistake:** Computing `dp[i]` before `dp[i-1]` is computed
**Correct:** Ensure dependencies are computed first

### 66. Not considering all possibilities
**Mistake:** Only checking one path in backtracking
**Correct:** Explore all choices and backtrack

### 67. Wrong comparison in sorting
**Mistake:** `sort(v.begin(), v.end(), [](int a, int b) { return a <= b; })`
**Correct:** Use `<` not `<=` for strict weak ordering

### 68. Modifying container while iterating
**Mistake:** `for (auto x : v) if (x == 2) v.erase(...);`
**Correct:** Use erase-remove idiom or iterate carefully

### 69. Not handling duplicates
**Mistake:** Using `set` when duplicates matter
**Correct:** Use `multiset` or handle duplicates explicitly

### 70. Wrong merge condition
**Mistake:** `if (intervals[i].start <= intervals[i-1].end)` (should check both start and end)
**Correct:** `if (intervals[i].start <= merged.back().end)`

### 71. Not sorting before binary search
**Mistake:** `binary_search` on unsorted array
**Correct:** Sort first, or use `find` for unsorted

### 72. Wrong palindrome check
**Mistake:** Only checking first half
**Correct:** Compare `s[i]` with `s[n-1-i]` for all `i < n/2`

### 73. Not considering negative numbers
**Mistake:** Algorithm assumes positive numbers
**Correct:** Handle negative numbers explicitly

### 74. Wrong tree traversal order
**Mistake:** Using pre-order when post-order is needed
**Correct:** Pre: root→left→right. In: left→root→right. Post: left→right→root

### 75. Not handling single element
**Mistake:** Algorithm fails for n=1
**Correct:** Check edge case explicitly

### 76. Wrong priority queue comparator
**Mistake:** `priority_queue<int, vector<int>, less<int>>` for min-heap
**Correct:** `priority_queue<int, vector<int>, greater<int>>` for min-heap

### 77. Not considering all edge cases
**Mistake:** Only testing with "normal" inputs
**Correct:** Test with empty, single, all-same, sorted, reverse-sorted

### 78. Wrong condition for valid parentheses
**Mistake:** Only checking count of '(' and ')'
**Correct:** Track balance: increment on '(', decrement on ')', never negative

### 79. Not handling wrap-around
**Mistake:** Circular array index `i+1` without `% n`
**Correct:** `(i + 1) % n`

### 80. Wrong condition for BST
**Mistake:** Only checking `node->left->val < node->val`
**Correct:** Check with valid range: `min_val < node->val < max_val`

---

## 5. Data Structure Mistakes (81-100)

### 81. Wrong container choice
**Mistake:** Using `vector` for frequent insert/delete at front
**Correct:** Use `deque` for O(1) front operations

### 82. Using `list` unnecessarily
**Mistake:** Using `list` for random access
**Correct:** Use `vector` — cache locality matters

### 83. Wrong hash function
**Mistake:** Using default hash for pairs
**Correct:** Provide custom hash for pairs/tuples

### 84. Not reserving vector space
**Mistake:** `vector<int> v; for(int i=0; i<100000; i++) v.push_back(i);`
**Correct:** `v.reserve(100000);` to avoid reallocations

### 85. Using `endl` instead of `'\n'`
**Mistake:** `cout << x << endl;` — flushes buffer every time
**Correct:** `cout << x << '\n';` — much faster

### 86. Wrong stack/queue usage
**Mistake:** Using `queue` when you need LIFO
**Correct:** `stack` for LIFO, `queue` for FIFO

### 87. Not using `emplace_back`
**Mistake:** `v.push_back(pair<int,int>(a, b));`
**Correct:** `v.emplace_back(a, b);` — constructs in-place

### 88. Wrong map access
**Mistake:** `mp[key]` to check existence (creates entry!)
**Correct:** `mp.count(key)` or `mp.find(key)`

### 89. Using `set` for frequency
**Mistake:** `set<int>` to count occurrences
**Correct:** `map<int, int>` or `unordered_map<int, int>`

### 90. Wrong DSU implementation
**Mistake:** Not using path compression
**Correct:** Always use path compression + union by rank/size

### 91. Wrong segment tree size
**Mistake:** `tree.resize(n)` for segment tree
**Correct:** `tree.resize(4 * n)`

### 92. Wrong Fenwick tree indexing
**Mistake:** Using 0-indexed Fenwick tree
**Correct:** Fenwick tree is 1-indexed

### 93. Not checking empty before top/pop
**Mistake:** `st.top()` when stack is empty
**Correct:** `if (!st.empty()) st.top();`

### 94. Wrong iterator type
**Mistake:** `vector<int>::iterator it = 0;`
**Correct:** `auto it = v.begin();`

### 95. Using `size_t` in subtraction
**Mistake:** `size_t x = v.size() - 1;` when `v` might be empty
**Correct:** `int x = (int)v.size() - 1;`

### 96. Wrong priority queue for Dijkstra
**Mistake:** Using max-heap for Dijkstra
**Correct:** `priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>> pq;`

### 97. Not popping stale entries
**Mistake:** Processing all entries from priority queue without checking
**Correct:** `if (d > dist[u]) continue;`

### 98. Wrong comparator for sort
**Mistake:** `sort(v.begin(), v.end(), greater<int>())` for ascending
**Correct:** `sort(v.begin(), v.end())` for ascending, `greater<int>()` for descending

### 99. Using `multimap` with `[]`
**Mistake:** `multimap<int,int> mp; mp[key] = val;` — doesn't compile!
**Correct:** `mp.insert({key, val});`

### 100. Wrong container for fast lookup
**Mistake:** Using `vector` + `find` for O(n) lookup
**Correct:** Use `unordered_set` for O(1) average lookup

---

## 6. String Mistakes (101-120)

### 101. Not handling empty string
**Mistake:** `s[0]` without checking `s.empty()`
**Correct:** Always check for empty string

### 102. Wrong string comparison
**Mistake:** `s1 == s2` for C-style strings (compares pointers)
**Correct:** Use `string` class or `strcmp`

### 103. Not handling spaces in input
**Mistake:** `cin >> s` only reads until whitespace
**Correct:** `getline(cin, s)` for full line

### 104. Wrong substring extraction
**Mistake:** `s.substr(i, j)` thinking it's `[i, j]`
**Correct:** `s.substr(i, j-i)` for range `[i, j)`

### 105. Not converting to lowercase/uppercase
**Mistake:** Comparing without case normalization
**Correct:** `transform(s.begin(), s.end(), s.begin(), ::tolower);`

### 106. Wrong character comparison
**Mistake:** `'A' == 'a'`
**Correct:** Convert to same case first

### 107. Not handling special characters
**Mistake:** Assuming alphanumeric only
**Correct:** Check `isalnum()`, `isalpha()`, `isdigit()`

### 108. Wrong string concatenation in loop
**Mistake:** `s += c;` in loop — O(n²) due to repeated copying
**Correct:** Use `stringstream` or `reserve()` first

### 109. Not handling trailing newline
**Mistake:** `getline` after `cin >> n` reads empty line
**Correct:** `cin.ignore()` before `getline`

### 110. Wrong KMP failure function
**Mistake:** Off-by-one in LPS computation
**Correct:** Carefully implement: `lps[i]` = length of longest proper prefix which is also suffix

### 111. Wrong anagram check
**Mistake:** Sorting both strings: O(n log n)
**Correct:** Count frequencies: O(n)

### 112. Not handling Unicode
**Mistake:** Assuming 1 byte per character
**Correct:** For ASCII problems, `char` is fine. For Unicode, use `wstring` or specialized libraries

### 113. Wrong string to number conversion
**Mistake:** `int x = s - '0';` for multi-digit
**Correct:** `int x = stoi(s);` or iterate digit by digit

### 114. Not handling leading zeros
**Mistake:** Treating "007" as 7
**Correct:** The problem usually specifies whether leading zeros are allowed

### 115. Wrong character to digit
**Mistake:** `int d = s[i];` (gets ASCII value)
**Correct:** `int d = s[i] - '0';`

### 116. Off-by-one in string iteration
**Mistake:** `for (int i = 0; i <= s.size(); i++)`
**Correct:** `for (int i = 0; i < s.size(); i++)`

### 117. Not using string::npos correctly
**Mistake:** `if (s.find("abc") == -1)`
**Correct:** `if (s.find("abc") == string::npos)`

### 118. Wrong string reversal
**Mistake:** Manual loop with off-by-one
**Correct:** `reverse(s.begin(), s.end());`

### 119. Not reserving string capacity
**Mistake:** Building string character by character without reserve
**Correct:** `s.reserve(expected_size);`

### 120. Wrong split implementation
**Mistake:** Not handling consecutive delimiters
**Correct:** Use `getline` with `stringstream` or handle explicitly

---

## 7. Graph Mistakes (121-145)

### 121. Not checking for disconnected components
**Mistake:** Running BFS/DFS from single source
**Correct:** Loop through all nodes, run BFS/DFS from each unvisited

### 122. Wrong adjacency list initialization
**Mistake:** `vector<int> adj[n];` (VLA, not standard C++)
**Correct:** `vector<vector<int>> adj(n);`

### 123. Not handling self-loops
**Mistake:** Ignoring edges from node to itself
**Correct:** Handle explicitly based on problem

### 124. Not handling multiple edges
**Mistake:** Assuming simple graph
**Correct:** Use appropriate data structure (set for unique edges)

### 125. Wrong Dijkstra with negative edges
**Mistake:** Using Dijkstra with negative edge weights
**Correct:** Use Bellman-Ford for negative edges

### 126. Not checking negative cycle
**Mistake:** Running Bellman-Ford without checking for negative cycle
**Correct:** Run one more iteration and check for relaxation

### 127. Wrong topological sort for cyclic graph
**Mistake:** Running topo sort on graph with cycles
**Correct:** Check for cycles: if `order.size() < n`, there's a cycle

### 128. Not using visited in BFS
**Mistake:** Enqueuing same node multiple times
**Correct:** Mark visited when enqueuing (not when dequeuing)

### 129. Wrong edge weight type
**Mistake:** Using `int` for weights when they can be large
**Correct:** Use `long long` for distances

### 130. Not initializing distance array
**Mistake:** `vector<int> dist(n);` — values are 0, not infinity
**Correct:** `vector<long long> dist(n, INF);`

### 131. Wrong DFS for cycle detection
**Mistake:** Not tracking "in recursion stack" for directed graphs
**Correct:** Use three states: unvisited, in-stack, done

### 132. Using BFS for weighted shortest path
**Mistake:** BFS gives shortest path only for unweighted graphs
**Correct:** Use Dijkstra for weighted graphs

### 133. Wrong Floyd-Warshall initialization
**Mistake:** Not setting `dist[i][i] = 0`
**Correct:** Initialize diagonal to 0, others to INF

### 134. Not considering both directions in undirected graph
**Mistake:** Only adding `adj[u].push_back(v)`
**Correct:** Also add `adj[v].push_back(u)` for undirected

### 135. Wrong Kruskal edge sorting
**Mistake:** Sorting by node instead of weight
**Correct:** Sort edges by weight

### 136. Not using path compression in DSU
**Mistake:** `find` without path compression
**Correct:** `parent[x] = find(parent[x])` (path compression)

### 137. Wrong SCC algorithm
**Mistake:** Using undirected graph algorithm for SCC
**Correct:** Use Tarjan's or Kosaraju's for directed graphs

### 138. Not handling unreachable nodes
**Mistake:** Accessing `dist[v]` when `v` is unreachable
**Correct:** Initialize to INF, check before use

### 139. Wrong bipartite check
**Mistake:** Only checking one component
**Correct:** Check all components

### 140. Not handling zero-weight edges
**Mistake:** Algorithm assumes positive weights
**Correct:** Dijkstra handles zero-weight edges correctly

### 141. Wrong LCA implementation
**Mistake:** Not lifting to same depth first
**Correct:** Lift deeper node, then lift both together

### 142. Not considering edge cases in tree
**Mistake:** Algorithm fails for single node or two nodes
**Correct:** Test with small trees

### 143. Wrong Euler path condition
**Mistake:** Not checking degree conditions
**Correct:** Euler path exists iff 0 or 2 vertices have odd degree

### 144. Wrong max flow algorithm
**Mistake:** Using BFS for max flow without residual graph
**Correct:** Maintain residual graph, find augmenting paths

### 145. Not handling disconnected graph in MST
**Mistake:** Assuming graph is connected
**Correct:** Check if MST has n-1 edges

---

## 8. Dynamic Programming Mistakes (146-165)

### 146. Not identifying the DP state
**Mistake:** Trying to solve with greedy
**Correct:** Identify overlapping subproblems and optimal substructure

### 147. Wrong DP state definition
**Mistake:** State doesn't capture enough information
**Correct:** Include all relevant information in the state

### 148. Wrong recurrence relation
**Mistake:** Incorrect transition between states
**Correct:** Derive recurrence from the problem statement

### 149. Not initializing DP table
**Mistake:** `vector<int> dp(n);` — all zeros
**Correct:** Initialize base cases explicitly

### 150. Wrong iteration order
**Mistake:** Computing `dp[i]` before dependencies
**Correct:** Ensure dependencies are computed first

### 151. Not using memoization
**Mistake:** Recursive solution without memoization — exponential
**Correct:** Add memoization table

### 152. Wrong memoization key
**Mistake:** Missing a dimension in the memo key
**Correct:** Include all state variables

### 153. Not considering all transitions
**Mistake:** Missing a case in the recurrence
**Correct:** Enumerate all possible choices

### 154. Wrong base case
**Mistake:** `dp[0] = 0` when it should be `dp[0] = 1`
**Correct:** Verify with small examples

### 155. Off-by-one in DP
**Mistake:** `dp[i]` represents wrong thing
**Correct:** Clearly define what `dp[i]` represents

### 156. Not space-optimizing
**Mistake:** Using 2D array when only previous row is needed
**Correct:** Use 1D array with rolling update

### 157. Wrong knapsack implementation
**mistake:** Forward iteration for 0/1 knapsack
**Correct:** Backward iteration: `for (int w = W; w >= weights[i]; w--)`

### 158. Not handling impossible states
**Mistake:** Not checking if a state is reachable
**Correct:** Initialize to INF/-1 and check before use

### 159. Wrong LIS implementation
**Mistake:** `O(n²)` DP when `O(n log n)` is possible
**Correct:** Use binary search with `tails` array

### 160. Not considering empty subsequence
**Mistake:** Missing the case of taking no elements
**Correct:** Initialize `dp[0] = 0` or handle explicitly

### 161. Wrong bitmask DP
**Mistake:** Wrong bit manipulation in state
**Correct:** `mask | (1 << i)` to set, `mask & (1 << i)` to check

### 162. Not handling overlapping subproblems
**Mistake:** Computing same state multiple times
**Correct:** Use memoization or bottom-up DP

### 163. Wrong interval DP
**Mistake:** Wrong split point
**Correct:** Try all possible split points

### 164. Not considering all ending positions
**Mistake:** Only considering `dp[n-1]` as answer
**Correct:** Answer might be `max(dp[i])` for all `i`

### 165. Wrong digit DP
**Mistake:** Not handling tight constraint
**Correct:** Include `tight` flag in state

---

## 9. Binary Search Mistakes (166-180)

### 166. Infinite loop
**Mistake:** `lo = mid` with `mid = (lo+hi)/2`
**Correct:** `lo = mid + 1` or use `mid = lo + (hi-lo+1)/2`

### 167. Wrong termination condition
**Mistake:** `while (lo < hi)` with `hi = n` (half-open) but returning `lo`
**Correct:** Be consistent: half-open `[lo, hi)` or closed `[lo, hi]`

### 168. Not handling duplicate elements
**Mistake:** Binary search stops at any occurrence
**Correct:** Use `lower_bound` for first, `upper_bound` for last

### 169. Wrong predicate for binary search on answer
**Mistake:** Predicate is not monotonic
**Correct:** Ensure the predicate is monotonic (all true then all false, or vice versa)

### 170. Not considering the answer is outside range
**Mistake:** Binary search range doesn't include the answer
**Correct:** Verify bounds include the answer

### 171. Wrong floating point binary search
**Mistake:** Using `==` for floating point comparison
**Correct:** Use `while (hi - lo > eps)` with appropriate epsilon

### 172. Integer overflow in mid calculation
**Mistake:** `int mid = (lo + hi) / 2`
**Correct:** `int mid = lo + (hi - lo) / 2`

### 173. Wrong search space
**Mistake:** Binary searching on array when answer is in value space
**Correct:** Binary search on the answer range

### 174. Not verifying the answer
**Mistake:** Trusting binary search result without checking
**Correct:** Verify the answer satisfies the condition

### 175. Off-by-one in lower_bound
**Mistake:** `lower_bound` returns iterator to first `>=`, not first `>`
**Correct:** `lower_bound` for `>=`, `upper_bound` for `>`

### 176. Wrong binary search for rotated array
**Mistake:** Not determining which half is sorted
**Correct:** Check if left half or right half is sorted, then decide

### 177. Not handling single element
**Mistake:** Binary search fails for n=1
**Correct:** Test with single element

### 178. Wrong binary search for peak
**Mistake:** Moving in wrong direction
**Correct:** If `arr[mid] < arr[mid+1]`, peak is on right; else on left

### 179. Using binary search on unsorted data
**Mistake:** Binary search requires sorted data
**Correct:** Sort first, or use linear search

### 180. Wrong binary search for insertion position
**Mistake:** Not handling equal elements correctly
**Correct:** `lower_bound` for leftmost, `upper_bound` for rightmost

---

## 10. Miscellaneous Mistakes (181-200)

### 181. Not reading the problem carefully
**Mistake:** Missing a constraint or requirement
**Correct:** Read the problem 2-3 times before coding

### 182. Not asking clarifying questions
**Mistake:** Assuming something not stated in the problem
**Correct:** Ask the interviewer about unclear requirements

### 183. Jumping into code too fast
**Mistake:** Coding without planning
**Correct:** Discuss approach first, then code

### 184. Not testing with examples
**Mistake:** Submitting without tracing through examples
**Correct:** Walk through your code with the given examples

### 185. Not handling edge cases
**Mistake:** Only testing with "normal" inputs
**Correct:** Test with empty, single, all-same, sorted, reverse-sorted

### 186. Not considering time complexity
**Mistake:** O(n²) when O(n log n) is required
**Correct:** Estimate complexity before coding

### 187. Not considering space complexity
**Mistake:** Using O(n²) space when O(n) is possible
**Correct:** Consider space-optimized solutions

### 188. Using wrong data type
**Mistake:** `int` when `long long` is needed
**Correct:** Use `long long` for large numbers

### 189. Not using fast I/O
**Mistake:** Slow input/output for large datasets
**Correct:** `ios_base::sync_with_stdio(false); cin.tie(nullptr);`

### 190. Copy-paste errors
**Mistake:** Variable name mismatch after copying code
**Correct:** Review all copied code carefully

### 191. Not handling negative numbers
**Mistake:** Algorithm assumes positive numbers
**Correct:** Handle negative numbers explicitly

### 192. Wrong output format
**Mistake:** Missing newline, wrong spacing
**Correct:** Match the expected output format exactly

### 193. Not considering all test cases
**Mistake:** Only testing with provided examples
**Correct:** Create your own test cases

### 194. Debugging with print statements in production
**Mistake:** Leaving debug prints in final code
**Correct:** Remove all debug output

### 195. Not understanding the algorithm
**Mistake:** Memorizing code without understanding
**Correct:** Understand why the algorithm works

### 196. Overcomplicating the solution
**Mistake:** Using complex data structures when simple ones work
**Correct:** Start with the simplest approach

### 197. Not considering integer division
**Mistake:** `int result = 5 / 2` gives 2, not 2.5
**Correct:** `double result = 5.0 / 2;`

### 198. Not handling the "no solution" case
**Mistake:** Algorithm assumes solution exists
**Correct:** Check if no solution is possible

### 199. Wrong modulo operation
**Mistake:** `result = result % MOD` after subtraction can be negative
**Correct:** `result = ((result % MOD) + MOD) % MOD`

### 200. Not practicing enough
**Mistake:** Only reading solutions without implementing
**Correct:** Implement every solution yourself

---

*Review this list periodically. Most bugs fall into these categories. Awareness is the first step to prevention.*
