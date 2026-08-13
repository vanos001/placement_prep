# Appendix E: Debugging Checklist

A systematic approach to finding and fixing bugs in your code. When your solution fails, go through this checklist methodically.

---

## 1. Off-By-One Errors

The #1 source of bugs. Check every loop boundary.

### Common Patterns

```cpp
// BUG: Off-by-one in loop
for (int i = 0; i <= n; i++) {  // should be i < n
    // accesses arr[n] which is out of bounds
}

// BUG: Wrong upper bound in binary search
int lo = 0, hi = n;  // should be hi = n - 1 (or hi = n for half-open)
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    // ...
}

// BUG: Fence post error
// n posts, n-1 fences between them
// n+1 segments when cutting a rope at n points

// FIX: Always ask yourself:
// - Is the range [0, n) or [0, n-1]?
// - Should I use < or <=?
// - What happens at the boundary (i=0, i=n-1)?
```

### Checklist
- [ ] Loop bounds: `i < n` vs `i <= n` vs `i < n-1`
- [ ] Array indexing: `arr[0..n-1]` vs `arr[1..n]`
- [ ] Binary search: half-open `[lo, hi)` vs closed `[lo, hi]`
- [ ] String indexing: `s[0..n-1]`, `s.size()` returns `n`
- [ ] Grid boundaries: `0 <= r < rows` and `0 <= c < cols`

---

## 2. Integer Overflow

When calculations exceed the range of the data type.

### Data Type Ranges

| Type | Min | Max |
|------|-----|-----|
| `int` | -2,147,483,648 | 2,147,483,647 (~2×10⁹) |
| `long long` | -9.2×10¹⁸ | 9.2×10¹⁸ |
| `unsigned int` | 0 | 4,294,967,295 (~4×10⁹) |

### Common Overflow Scenarios

```cpp
// BUG: Multiplication overflow
int a = 100000, b = 100000;
int product = a * b;  // OVERFLOW! Result is wrong

// FIX: Use long long
long long product = 1LL * a * b;

// BUG: Sum overflow
int sum = 0;
for (int i = 0; i < 100000; i++) {
    sum += 100000;  // may overflow
}

// FIX: Use long long for accumulators
long long sum = 0;

// BUG: Intermediate calculation overflow
int result = (a * b) % MOD;  // a * b may overflow int
// FIX:
int result = (1LL * a * b) % MOD;

// BUG: Negative modulo
int x = -7 % 3;  // In C++, this is -1, not 2
// FIX:
int x = ((-7 % 3) + 3) % 3;  // Always positive

// BUG: Absolute value of INT_MIN
int x = INT_MIN;
int abs_x = abs(x);  // OVERFLOW! abs(INT_MIN) == INT_MIN
// FIX:
long long abs_x = abs((long long)x);
```

### Checklist
- [ ] Are any multiplications done with `int` that could overflow?
- [ ] Are accumulators (`sum`, `product`) using `long long`?
- [ ] Is `(a * b) % MOD` done safely with `1LL * a * b`?
- [ ] Could `INT_MIN` appear in `abs()` calls?
- [ ] Are modular operations handling negative numbers correctly?

---

## 3. Null Pointer / Segmentation Fault

Accessing memory that doesn't belong to you.

### Common Causes

```cpp
// BUG: Dereferencing null pointer
ListNode* node = nullptr;
node->val;  // SEGFAULT

// FIX: Always check before dereferencing
if (node != nullptr) {
    node->val;
}

// BUG: Accessing empty container
vector<int> v;
v[0];  // UNDEFINED BEHAVIOR
v.front();  // UNDEFINED BEHAVIOR

// FIX: Check size first
if (!v.empty()) { v[0]; }

// BUG: Iterator invalidation
vector<int> v = {1, 2, 3, 4, 5};
for (auto it = v.begin(); it != v.end(); ++it) {
    if (*it == 3) {
        v.erase(it);  // INVALIDATES iterator!
    }
}

// FIX: Use erase-remove idiom or capture return value
for (auto it = v.begin(); it != v.end(); ) {
    if (*it == 3) it = v.erase(it);
    else ++it;
}

// BUG: Accessing after pop
stack<int> st;
st.push(1);
int top = st.top();
st.pop();
// top is still valid (it's a copy), but:
int& ref = st.top();
st.pop();
// ref is now DANGLING REFERENCE
```

### Checklist
- [ ] Are all pointers checked before dereferencing?
- [ ] Are containers checked for empty before accessing elements?
- [ ] Are iterators still valid after insert/erase operations?
- [ ] Are references/pointers still valid after container modification?
- [ ] Is the recursive function hitting base case? (Stack overflow from deep recursion)

---

## 4. Infinite Loops

Loops that never terminate.

### Common Causes

```cpp
// BUG: Wrong loop condition
int i = 0;
while (i > 0) {  // never enters, probably meant i < n
    i++;
}

// BUG: Forgetting to update loop variable
while (!q.empty()) {
    int u = q.front();
    // q.pop();  // FORGOT TO POP!
    for (int v : adj[u]) {
        q.push(v);
    }
}

// BUG: Wrong update direction
for (int i = n; i >= 0; i--) {
    // If n is unsigned and we go below 0, wraps to UINT_MAX
}

// FIX for unsigned:
for (int i = n - 1; i >= 0; i--) {  // start from n-1
    // or use size_t carefully
}

// BUG: Floating point comparison in loop
for (double x = 0; x != 1.0; x += 0.1) {
    // May never terminate due to floating point precision
}

// FIX: Use epsilon comparison
for (double x = 0; x < 1.0 + 1e-9; x += 0.1) {
    // ...
}
```

### Checklist
- [ ] Is the loop condition correct? Will it eventually become false?
- [ ] Is the loop variable updated inside the loop?
- [ ] For `while(true)`: is there a `break` statement?
- [ ] For recursive functions: does every path reach the base case?
- [ ] Are you using `==` with floating point numbers?

---

## 5. Wrong Base Case / Recursion Errors

### Common Causes

```cpp
// BUG: Missing base case
int fib(int n) {
    return fib(n-1) + fib(n-2);  // no base case!
}

// FIX:
int fib(int n) {
    if (n <= 1) return n;
    return fib(n-1) + fib(n-2);
}

// BUG: Wrong base case
int factorial(int n) {
    if (n == 1) return 1;  // what about factorial(0)?
    return n * factorial(n-1);
}

// FIX:
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n-1);
}

// BUG: Base case never reached
int f(int n) {
    if (n == 0) return 0;
    return f(n - 2);  // if n is odd, never reaches 0!
}

// FIX:
int f(int n) {
    if (n <= 0) return 0;
    return f(n - 2);
}

// BUG: Off-by-one in base case
// Tree DFS: checking for leaf node
void dfs(TreeNode* node) {
    if (node->left == nullptr && node->right == nullptr) {
        // leaf
    }
    dfs(node->left);   // BUG: node->left could be null!
    dfs(node->right);
}

// FIX:
void dfs(TreeNode* node) {
    if (node == nullptr) return;  // proper null check
    if (node->left == nullptr && node->right == nullptr) {
        // leaf
    }
    dfs(node->left);
    dfs(node->right);
}
```

### Checklist
- [ ] Does every recursive function have a base case?
- [ ] Does every path through the recursion reach the base case?
- [ ] Is the base case correct (not off-by-one)?
- [ ] Are null pointers checked before recursive calls?
- [ ] Is the return value correct for the base case?

---

## 6. Missing Visited Array / Cycle Detection

### Common Causes

```cpp
// BUG: Missing visited array in graph traversal
void dfs(vector<vector<int>>& adj, int u) {
    for (int v : adj[u]) {
        dfs(adj, v);  // INFINITE LOOP if cycle exists!
    }
}

// FIX:
void dfs(vector<vector<int>>& adj, int u, vector<bool>& visited) {
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs(adj, v, visited);
        }
    }
}

// BUG: Not marking visited before recursive call
void dfs(vector<vector<int>>& adj, int u, vector<bool>& visited) {
    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs(adj, v, visited);  // v might be visited by another branch
            visited[v] = true;     // TOO LATE!
        }
    }
}

// FIX: Mark visited when you discover, not when you finish
void dfs(vector<vector<int>>& adj, int u, vector<bool>& visited) {
    visited[u] = true;  // mark when discovered
    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs(adj, v, visited);
        }
    }
}

// BUG: Wrong visited array size
vector<bool> visited(n);  // should be n, not n-1 or n+1

// BUG: Not resetting visited for multiple components
// If you need to run DFS multiple times, reset visited
fill(visited.begin(), visited.end(), false);
```

### Checklist
- [ ] Is there a visited array for graph/tree traversals?
- [ ] Is the visited array the correct size?
- [ ] Is the node marked visited BEFORE the recursive call?
- [ ] For BFS: is the node marked visited when enqueued (not dequeued)?
- [ ] For multiple traversals: is the visited array reset?

---

## 7. Incorrect Comparator

### Common Causes

```cpp
// BUG: Comparator doesn't satisfy strict weak ordering
// Requirements:
// 1. Irreflexivity: comp(a, a) == false
// 2. Asymmetry: if comp(a, b) then !comp(b, a)
// 3. Transitivity: if comp(a, b) and comp(b, c) then comp(a, c)
// 4. Transitivity of equivalence: if !comp(a,b) and !comp(b,a) and
//    !comp(b,c) and !comp(c,b) then !comp(a,c) and !comp(c,a)

// BUG: Using <= instead of < in comparator
sort(v.begin(), v.end(), [](int a, int b) {
    return a <= b;  // WRONG! Must use <
});

// FIX:
sort(v.begin(), v.end(), [](int a, int b) {
    return a < b;
});

// BUG: Priority queue comparator is inverted
// For min-heap, you want "greater" comparator
priority_queue<int, vector<int>, less<int>> pq;  // this is MAX-heap!

// FIX for min-heap:
priority_queue<int, vector<int>, greater<int>> minpq;

// BUG: Comparator for pairs doesn't compare correctly
// Want to sort by first descending, then second ascending
sort(v.begin(), v.end(), [](auto& a, auto& b) {
    if (a.first != b.first) return a.first > b.first;
    return a.second < b.second;  // correct
});

// BUG: Using floating point in comparator
sort(v.begin(), v.end(), [](double a, double b) {
    return a < b;  // can cause issues with NaN
});

// BUG: Map/Set comparator doesn't handle equal elements
set<int, decltype([](int a, int b) { return a < b; })> s;
// Lambda as comparator requires C++20 or explicit type
```

### Checklist
- [ ] Does the comparator use `<` not `<=`?
- [ ] Does it satisfy strict weak ordering?
- [ ] For priority_queue: is the comparator direction correct?
- [ ] For custom sorts: are all tie-breaking cases handled?
- [ ] Does the comparator handle equal elements correctly?

---

## 8. Iterator Invalidation

### When Iterators Are Invalidated

| Container | Operation | Invalidated |
|-----------|-----------|-------------|
| `vector` | `push_back` | All if reallocation |
| `vector` | `insert` | All from insertion point |
| `vector` | `erase` | All from erasure point |
| `deque` | `push_front/back` | All |
| `deque` | `insert/erase` | All |
| `list` | `insert` | None |
| `list` | `erase` | Only erased iterator |
| `set/map` | `insert` | None |
| `set/map` | `erase` | Only erased iterator |
| `unordered_*` | `insert` | All if rehash |
| `unordered_*` | `erase` | Only erased iterator |

### Common Bugs

```cpp
// BUG: Erasing during iteration
for (auto it = s.begin(); it != s.end(); ++it) {
    if (*it == target) {
        s.erase(it);  // INVALIDATES it!
    }
}

// FIX for set/map:
for (auto it = s.begin(); it != s.end(); ) {
    if (*it == target) {
        it = s.erase(it);  // erase returns next iterator
    } else {
        ++it;
    }
}

// FIX for vector (remove-erase idiom):
v.erase(remove(v.begin(), v.end(), target), v.end());

// BUG: Using iterator after container modification
auto it = v.begin();
v.push_back(42);  // may reallocate
*it;  // INVALID if reallocation happened

// FIX: Get iterator after modification
v.push_back(42);
auto it = v.begin();
```

### Checklist
- [ ] Are you erasing elements during iteration? Use proper idiom.
- [ ] Are you using iterators after container modification?
- [ ] For `unordered_*`: are you aware of potential rehash on insert?
- [ ] For `vector`: are you aware of potential reallocation on `push_back`?

---

## 9. Stack Overflow from Deep Recursion

### Common Causes

```cpp
// BUG: Deep recursion without optimization
// Default stack size is ~8MB
// Each stack frame uses ~100-500 bytes
// So max depth is ~16,000 - 80,000 calls

// For a tree with 10^5 nodes, DFS may overflow

// FIX 1: Increase stack size (platform-specific)
// On Linux, before running:
// ulimit -s unlimited
// Or compile with: g++ -Wl,-stack_size,0x10000000

// FIX 2: Convert to iterative
void dfs_iterative(vector<vector<int>>& adj, int start) {
    stack<int> st;
    st.push(start);
    vector<bool> visited(adj.size(), false);
    while (!st.empty()) {
        int u = st.top(); st.pop();
        if (visited[u]) continue;
        visited[u] = true;
        for (int v : adj[u]) {
            if (!visited[v]) st.push(v);
        }
    }
}

// FIX 3: Use tail recursion where possible
// Bad:
int sum(int n) {
    if (n == 0) return 0;
    return n + sum(n - 1);  // not tail recursive
}
// Good:
int sum(int n, int acc = 0) {
    if (n == 0) return acc;
    return sum(n - 1, acc + n);  // tail recursive
}

// FIX 4: Use explicit stack for DFS on large graphs
```

### Checklist
- [ ] What's the maximum recursion depth? Is it safe?
- [ ] For n > 10^4: convert to iterative
- [ ] For trees: consider iterative DFS or BFS
- [ ] For DP: use bottom-up instead of top-down

---

## 10. Wrong Data Type

### Common Mistakes

```cpp
// BUG: Using int for large numbers
int n = 1000000000;
int sq = n * n;  // OVERFLOW

// FIX: Use long long
long long n = 1000000000LL;
long long sq = n * n;

// BUG: Signed/unsigned comparison
vector<int> v = {1, 2, 3};
for (int i = 0; i < v.size() - 1; i++) {  // v.size()-1 is unsigned!
    // If v is empty, v.size()-1 wraps to UINT_MAX
}

// FIX:
for (int i = 0; i + 1 < v.size(); i++) {  // safer
// or
for (size_t i = 0; i + 1 < v.size(); i++) {

// BUG: Integer division
int a = 5, b = 2;
double result = a / b;  // result is 2.0, not 2.5!

// FIX:
double result = (double)a / b;  // or 1.0 * a / b

// BUG: char arithmetic
char c = '9';
int digit = c - '0';  // correct: 9
int digit2 = c - 0;   // WRONG: ASCII value of '9' (57)
```

### Checklist
- [ ] Are all large numbers using `long long`?
- [ ] Are there any signed/unsigned comparisons?
- [ ] Is integer division intended? If not, cast to `double`.
- [ ] Are character conversions done correctly?

---

## 11. Wrong Algorithm / Logic Error

### Common Mistakes

```cpp
// BUG: Not considering all edge cases
// - Empty input
// - Single element
// - All same elements
// - Negative numbers
// - Very large input

// BUG: Greedy when DP is needed
// Example: Coin change with greedy doesn't always work
// coins = [1, 3, 4], amount = 6
// Greedy: 4 + 1 + 1 = 3 coins
// Optimal: 3 + 3 = 2 coins

// BUG: BFS when DFS is needed (or vice versa)
// BFS: shortest path in unweighted graph
// DFS: finding all paths, cycle detection, topological sort

// BUG: Not considering negative edges in shortest path
// Dijkstra doesn't work with negative edges
// Use Bellman-Ford instead

// BUG: Using floating point for exact comparisons
if (a == b) { }  // WRONG for doubles
// FIX:
if (abs(a - b) < 1e-9) { }

// BUG: Not handling duplicate elements
set<int> s = {1, 1, 2};  // s = {1, 2}, size is 2
multiset<int> ms = {1, 1, 2};  // ms = {1, 1, 2}, size is 3
```

### Checklist
- [ ] Have you tested with edge cases (empty, single, all same)?
- [ ] Is greedy correct for this problem? (Prove it or use DP)
- [ ] Are negative numbers handled correctly?
- [ ] Is floating point comparison done with epsilon?
- [ ] Are duplicate elements handled correctly?

---

## 12. Memory Issues

### Common Causes

```cpp
// BUG: Accessing out of bounds
vector<int> v(10);
v[10] = 42;  // OUT OF BOUNDS (valid indices: 0-9)

// FIX: Use .at() for bounds checking, or be careful with indices

// BUG: Memory leak (in raw pointer code)
int* arr = new int[100];
// ... forgot delete[] arr;

// FIX: Use smart pointers or containers
vector<int> arr(100);

// BUG: Stack overflow from large local array
int main() {
    int arr[10000000];  // ~40MB, stack overflow!
}

// FIX: Use vector (heap allocated)
vector<int> arr(10000000);

// BUG: Use after free
int* p = new int(42);
delete p;
*p = 10;  // UNDEFINED BEHAVIOR

// FIX: Set pointer to null after delete
delete p;
p = nullptr;
```

### Checklist
- [ ] Are all array accesses within bounds?
- [ ] Are large arrays allocated on the heap (vector)?
- [ ] For raw pointers: is every `new` matched with `delete`?
- [ ] Are smart pointers used where possible?

---

## 13. Input/Output Issues

### Common Causes

```cpp
// BUG: Not clearing input buffer
int n;
cin >> n;
string s;
getline(cin, s);  // reads empty line (leftover newline)

// FIX:
cin >> n;
cin.ignore();  // or use cin >> for strings too

// BUG: Not handling whitespace in input
// Input: "hello world"
string s;
cin >> s;  // reads only "hello"

// FIX:
getline(cin, s);  // reads entire line

// BUG: Wrong output format
// Expected: "Case #1: 42"
// Output: "42"

// BUG: Not flushing output
cout << "Enter value: ";
// No flush, prompt may not appear
// FIX:
cout << "Enter value: " << flush;
// or
cout << "Enter value: " << endl;  // endl flushes

// BUG: Mixed cin/cout and scanf/printf
cin >> n;
printf("%d\n", n);  // can cause issues
// FIX: stick to one I/O method
```

### Checklist
- [ ] Is the input format correct?
- [ ] Are there leftover newlines in the buffer?
- [ ] Is the output format exactly as expected?
- [ ] Are you using consistent I/O methods?

---

## 14. Modular Arithmetic Errors

### Common Causes

```cpp
const int MOD = 1e9 + 7;

// BUG: Addition overflow before modulo
int a = 1e9, b = 1e9;
int sum = (a + b) % MOD;  // a + b overflows int!

// FIX:
int sum = ((long long)a + b) % MOD;

// BUG: Multiplication overflow before modulo
int a = 1e9, b = 1e9;
int prod = (a * b) % MOD;  // a * b overflows!

// FIX:
int prod = (1LL * a * b) % MOD;

// BUG: Subtraction can go negative
int diff = (a - b) % MOD;  // if a < b, result is negative

// FIX:
int diff = ((a - b) % MOD + MOD) % MOD;

// BUG: Division modulo
int div = (a / b) % MOD;  // WRONG! Division doesn't work with modulo

// FIX: Use modular inverse
// div = (a * mod_inverse(b, MOD)) % MOD;

// BUG: Power modulo
int power = pow(a, b) % MOD;  // pow returns double, loses precision

// FIX: Use modular exponentiation
long long power_mod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}
```

### Checklist
- [ ] Are all additions done with `long long` before modulo?
- [ ] Are all multiplications done with `1LL *` before modulo?
- [ ] Is subtraction handled with `+ MOD` to avoid negatives?
- [ ] Is division done using modular inverse?
- [ ] Is exponentiation done with fast power?

---

## 15. Debugging Strategy

When your solution fails, follow this systematic approach:

### Step 1: Understand the Failure
- [ ] Read the error message carefully
- [ ] Is it WA (Wrong Answer), TLE (Time Limit Exceeded), RE (Runtime Error), or CE (Compilation Error)?
- [ ] What's the input that causes the failure?

### Step 2: Generate Test Cases
- [ ] Small inputs (n=1, 2, 3)
- [ ] Edge cases (empty, single element, all same)
- [ ] Maximum constraints
- [ ] Random test cases

### Step 3: Add Debug Output
```cpp
#ifdef DEBUG
    #define dbg(x) cerr << #x << " = " << x << endl
#else
    #define dbg(x)
#endif
```

### Step 4: Check Each Component
- [ ] Is the input read correctly?
- [ ] Is the algorithm correct?
- [ ] Are all variables initialized?
- [ ] Is the output formatted correctly?

### Step 5: Binary Search for the Bug
- [ ] Comment out parts of the code
- [ ] Add assertions at key points
- [ ] Compare expected vs actual at each step

---

## 16. Quick Reference: Common Bug Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Wrong answer on large input | Integer overflow | Use `long long` |
| Segfault on large input | Stack overflow | Convert to iterative |
| Wrong answer on small input | Off-by-one | Check loop bounds |
| Infinite loop | Missing update | Check loop variable |
| Wrong answer on specific case | Edge case not handled | Test with edge cases |
| TLE | Wrong complexity | Use better algorithm |
| WA on sorted input | Wrong comparator | Check strict weak ordering |
| Runtime error | Null pointer | Check for null before access |
| Wrong answer after sorting | Iterator invalidation | Check iterator validity |

---

*When in doubt, print everything. Add debug output for every variable, every step. It's faster to add prints than to stare at code.*
