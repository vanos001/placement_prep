# Chapter 8: Recursion

Recursion is one of the most powerful and elegant concepts in computer science. It is a technique where a function calls itself to solve a problem by breaking it down into smaller, self-similar subproblems. Mastering recursion is essential for coding interviews, as it forms the foundation for trees, graphs, dynamic programming, backtracking, and divide-and-conquer algorithms.

---

## 8.1 What Is Recursion?

### Self-Reference

**Recursion** is a method of solving a problem where the solution depends on solutions to smaller instances of the same problem. A recursive function is one that calls itself during its execution.

Every recursive definition has two essential components:

| Component | Description | Example (Factorial) |
|-----------|-------------|---------------------|
| **Base Case** | The condition under which the function stops calling itself | `n == 0` returns `1` |
| **Recursive Case** | The condition under which the function calls itself with a simpler input | `n * factorial(n-1)` |

Without a base case, the function would call itself forever (infinite recursion). Without a recursive case, there is no self-reference and hence no recursion.

### Real-World Analogies

**Russian Nesting Dolls (Matryoshka):** To find what is inside the smallest doll, you open each doll one by one. Opening a doll is the recursive step; finding the smallest doll (which cannot be opened) is the base case.

**Dictionary Lookup:** You look up a word in a dictionary. The definition contains words you do not know, so you look up those words. You continue until every word in the definition is understood — those are your base cases.

**File System Traversal:** To find all `.cpp` files in a directory, you look in the current directory, then recursively search every subdirectory.

### A Simple Example: Factorial

The factorial of a non-negative integer \\(n\\) is defined as:

\\[n! = \begin{cases} 1 & \text{if } n = 0 \\ n \times (n-1)! & \text{if } n > 0 \end{cases}\\]

```cpp
#include <iostream>
#include <stdexcept>

// Classic recursive factorial
// Time: O(n), Space: O(n) due to call stack
long long factorial(int n) {
    if (n < 0) {
        throw std::invalid_argument("Factorial not defined for negative numbers");
    }
    if (n == 0 || n == 1) {   // Base case
        return 1;
    }
    return n * factorial(n - 1); // Recursive case
}

int main() {
    for (int i = 0; i <= 10; ++i) {
        std::cout << i << "! = " << factorial(i) << "\n";
    }
    return 0;
}
```

**Dry Run for `factorial(4)`:**

```
factorial(4)
  → 4 * factorial(3)
        → 3 * factorial(2)
              → 2 * factorial(1)
                    → 1  (base case)
              → 2 * 1 = 2
        → 3 * 2 = 6
  → 4 * 6 = 24
```

### Key Properties of a Correct Recursive Function

1. **The base case must be reachable.** Every recursive call must progress toward the base case.
2. **The problem must get smaller.** Each recursive call should operate on a strictly smaller input.
3. **The base case must be correct.** An incorrect base case propagates errors to every call.
4. **The recursive calls must be correct.** Trust that the recursive call returns the correct result for the smaller input (this is the **leap of faith**).

---

## 8.2 The Call Stack

### How Function Calls Work

When a program calls a function, the system allocates a **stack frame** on the **call stack**. This stack frame contains:

- The function's **local variables**
- The function's **parameters**
- The **return address** (where to continue after the function returns)
- The **return value** (if any)

When the function finishes, its stack frame is **popped** off the stack, and execution resumes at the return address.

### Visualizing the Call Stack

For `factorial(3)`, the call stack evolves as follows:

```
Step 1: factorial(3) is called
┌─────────────────────┐
│ factorial(3)        │  ← Stack top
│   n = 3             │
│   return address: main│
└─────────────────────┘

Step 2: factorial(3) calls factorial(2)
┌─────────────────────┐
│ factorial(2)        │  ← Stack top
│   n = 2             │
├─────────────────────┤
│ factorial(3)        │
│   n = 3             │
└─────────────────────┘

Step 3: factorial(2) calls factorial(1)
┌─────────────────────┐
│ factorial(1)        │  ← Stack top (base case, returns 1)
├─────────────────────┤
│ factorial(2)        │
│   n = 2             │
├─────────────────────┤
│ factorial(3)        │
│   n = 3             │
└─────────────────────┘

Steps 4-6: Stack unwinds, computing 1→2→6
```

### Stack Overflow

Each stack frame consumes memory. If recursion goes too deep (e.g., no base case, or very large input), the call stack exceeds its allocated memory, causing a **stack overflow**.

```cpp
#include <iostream>

// WARNING: This will cause a stack overflow!
// Do NOT run this without a base case that is reachable.
void infinite_recursion(int n) {
    // Missing: no base case that stops the recursion
    std::cout << n << "\n";
    infinite_recursion(n + 1); // Stack grows until it overflows
}

// A safer demonstration: counting stack depth
void count_depth(int n) {
    // Most systems allow ~10,000-50,000 recursive calls
    // before stack overflow occurs
    count_depth(n + 1); // Will eventually crash
}
```

Typical stack sizes:
- Linux default: 8 MB
- Windows default: 1 MB
- Each stack frame: ~16-64 bytes (depending on function)

This means a simple recursive function can safely recurse about 10,000–100,000 times, but deeper recursion requires an iterative approach or explicit stack management.

---

## 8.3 Recursion to Iteration

### Why Convert?

- **Performance:** Iteration avoids the overhead of function calls and stack frames.
- **Stack Safety:** Iteration cannot cause stack overflow.
- **Interview Requirement:** Many interviewers ask you to convert between the two.

### Systematic Conversion Using Explicit Stacks

The key idea: **replace the implicit call stack with an explicit data structure (usually a stack)**.

#### Example: Factorial — Iterative Version

```cpp
#include <iostream>

// Iterative factorial
// Time: O(n), Space: O(1)
long long factorial_iterative(int n) {
    if (n < 0) throw std::invalid_argument("Negative input");
    long long result = 1;
    for (int i = 2; i <= n; ++i) {
        result *= i;
    }
    return result;
}

int main() {
    std::cout << "5! = " << factorial_iterative(5) << "\n"; // 120
    return 0;
}
```

#### Example: Fibonacci — From Naive Recursive to Iterative

The naive recursive Fibonacci has exponential time complexity:

```cpp
#include <iostream>
#include <vector>

// Naive recursive Fibonacci
// Time: O(2^n), Space: O(n) — TERRIBLE!
long long fib_naive(int n) {
    if (n <= 1) return n;
    return fib_naive(n - 1) + fib_naive(n - 2);
}

// Iterative Fibonacci
// Time: O(n), Space: O(1)
long long fib_iterative(int n) {
    if (n <= 1) return n;
    long long prev2 = 0, prev1 = 1;
    for (int i = 2; i <= n; ++i) {
        long long curr = prev1 + prev2;
        prev2 = prev1;
        prev1 = curr;
    }
    return prev1;
}

// Memoized Fibonacci (top-down dynamic programming)
// Time: O(n), Space: O(n)
long long fib_memo(int n, std::vector<long long>& memo) {
    if (n <= 1) return n;
    if (memo[n] != -1) return memo[n];
    memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo);
    return memo[n];
}

int main() {
    int n = 10;
    std::vector<long long> memo(n + 1, -1);
    std::cout << "fib_naive(" << n << ") = " << fib_naive(n) << "\n";
    std::cout << "fib_iterative(" << n << ") = " << fib_iterative(n) << "\n";
    std::cout << "fib_memo(" << n << ") = " << fib_memo(n, memo) << "\n";
    return 0;
}
```

#### Example: Inorder Traversal — Recursive to Iterative with Explicit Stack

```cpp
#include <iostream>
#include <stack>
#include <vector>

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

// Recursive inorder: Left → Root → Right
void inorder_recursive(TreeNode* root, std::vector<int>& result) {
    if (!root) return;
    inorder_recursive(root->left, result);
    result.push_back(root->val);
    inorder_recursive(root->right, result);
}

// Iterative inorder using explicit stack
// Key insight: simulate the call stack manually
std::vector<int> inorder_iterative(TreeNode* root) {
    std::vector<int> result;
    std::stack<TreeNode*> stk;
    TreeNode* curr = root;

    while (curr || !stk.empty()) {
        // Go as far left as possible (simulates the "left" recursive call)
        while (curr) {
            stk.push(curr);
            curr = curr->left;
        }
        // Process the node (simulates returning from the recursive call)
        curr = stk.top();
        stk.pop();
        result.push_back(curr->val);
        // Move to right subtree (simulates the "right" recursive call)
        curr = curr->right;
    }
    return result;
}

int main() {
    //       4
    //      / \
    //     2   6
    //    / \ / \
    //   1  3 5  7
    TreeNode* root = new TreeNode(4);
    root->left = new TreeNode(2);
    root->right = new TreeNode(6);
    root->left->left = new TreeNode(1);
    root->left->right = new TreeNode(3);
    root->right->left = new TreeNode(5);
    root->right->right = new TreeNode(7);

    std::vector<int> rec_result;
    inorder_recursive(root, rec_result);
    auto iter_result = inorder_iterative(root);

    std::cout << "Recursive inorder: ";
    for (int v : rec_result) std::cout << v << " ";
    std::cout << "\nIterative inorder: ";
    for (int v : iter_result) std::cout << v << " ";
    std::cout << "\n";
    // Both output: 1 2 3 4 5 6 7

    // Cleanup
    delete root->left->left;
    delete root->left->right;
    delete root->right->left;
    delete root->right->right;
    delete root->left;
    delete root->right;
    delete root;
    return 0;
}
```

### General Conversion Recipe

1. **Identify local variables and parameters** in the recursive function — these become fields in a stack frame struct.
2. **Identify the "state"** of execution (e.g., which recursive call has completed).
3. **Push initial state** onto the explicit stack.
4. **Loop:** Pop from the stack, execute the corresponding logic, push new states as needed.
5. **Handle the base case** with a conditional check before pushing.

---

## 8.4 Divide and Conquer

### The Paradigm

**Divide and Conquer** is a strategy that solves a problem by:

1. **Divide:** Split the problem into smaller subproblems of the same type.
2. **Conquer:** Solve each subproblem recursively.
3. **Combine:** Merge the solutions of the subproblems into the solution for the original problem.

This is not just recursion — it is a *structured* form of recursion where the problem is split into *independent* subproblems.

### Merge Sort — The Classic Example

```cpp
#include <iostream>
#include <vector>

// Merge two sorted halves into one sorted array
void merge(std::vector<int>& arr, int left, int mid, int right) {
    std::vector<int> temp(right - left + 1);
    int i = left;       // Pointer for left half
    int j = mid + 1;    // Pointer for right half
    int k = 0;          // Pointer for temp

    while (i <= mid && j <= right) {
        if (arr[i] <= arr[j]) {
            temp[k++] = arr[i++];
        } else {
            temp[k++] = arr[j++];
        }
    }
    while (i <= mid) temp[k++] = arr[i++];
    while (j <= right) temp[k++] = arr[j++];

    // Copy back to original array
    for (int idx = 0; idx < k; ++idx) {
        arr[left + idx] = temp[idx];
    }
}

// Merge Sort
// Time: O(n log n) — every level does O(n) work, and there are O(log n) levels
// Space: O(n) for the temporary array
void mergeSort(std::vector<int>& arr, int left, int right) {
    if (left >= right) return;  // Base case: single element

    int mid = left + (right - left) / 2;
    mergeSort(arr, left, mid);         // Conquer left half
    mergeSort(arr, mid + 1, right);    // Conquer right half
    merge(arr, left, mid, right);      // Combine
}

int main() {
    std::vector<int> arr = {38, 27, 43, 3, 9, 82, 10};
    mergeSort(arr, 0, arr.size() - 1);
    std::cout << "Sorted: ";
    for (int v : arr) std::cout << v << " ";
    std::cout << "\n";
    // Output: 3 9 10 27 38 43 82
    return 0;
}
```

### When Does Divide and Conquer Apply?

| Criterion | Explanation |
|-----------|-------------|
| **Optimal substructure** | The optimal solution can be constructed from optimal solutions of subproblems |
| **Independent subproblems** | Subproblems do not overlap (unlike dynamic programming) |
| **Balanced division** | Splitting the problem roughly in half yields logarithmic depth |

Classic divide-and-conquer algorithms:
- **Merge Sort** — O(n log n)
- **Quick Sort** — O(n log n) average
- **Binary Search** — O(log n)
- **Closest Pair of Points** — O(n log n)
- **Strassen's Matrix Multiplication** — O(n^2.81)

### Power(x, n) — Fast Exponentiation

Compute \\(x^n\\) efficiently using divide and conquer:

```cpp
#include <iostream>

// Compute x^n using divide and conquer
// Time: O(log n), Space: O(log n) due to recursion
double power(double x, long long n) {
    if (n == 0) return 1.0;
    if (n < 0) {
        x = 1.0 / x;
        n = -n;
    }
    double half = power(x, n / 2);
    if (n % 2 == 0) {
        return half * half;
    } else {
        return half * half * x;
    }
}

// Iterative version
// Time: O(log n), Space: O(1)
double power_iterative(double x, long long n) {
    if (n < 0) {
        x = 1.0 / x;
        n = -n;
    }
    double result = 1.0;
    while (n > 0) {
        if (n % 2 == 1) {
            result *= x;
        }
        x *= x;
        n /= 2;
    }
    return result;
}

int main() {
    std::cout << "2^10 = " << power(2, 10) << "\n";        // 1024
    std::cout << "2^10 = " << power_iterative(2, 10) << "\n"; // 1024
    std::cout << "2^-3 = " << power(2, -3) << "\n";         // 0.125
    return 0;
}
```

**Dry Run for `power(2, 10)`:**

```
power(2, 10)
  half = power(2, 5)
    half = power(2, 2)
      half = power(2, 1)
        half = power(2, 0) → 1
        1 * 1 * 2 = 2
      2 * 2 = 4
    4 * 4 * 2 = 32
  32 * 32 = 1024
```

---

## 8.5 Tail Recursion

### What Is Tail Recursion?

A function is **tail-recursive** if the recursive call is the **last operation** in the function. There is no computation after the recursive call returns.

**Tail-recursive:**
```cpp
int factorial_tail(int n, int acc = 1) {
    if (n <= 1) return acc;
    return factorial_tail(n - 1, n * acc); // Last operation — tail call
}
```

**NOT tail-recursive:**
```cpp
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1); // Must multiply AFTER the call returns
}
```

### Why Does Tail Recursion Matter?

Some compilers (notably GCC and Clang with optimization enabled, and most functional language compilers) perform **Tail Call Optimization (TCO)**. When a tail-recursive function is detected, the compiler reuses the current stack frame instead of allocating a new one, effectively converting the recursion into a loop.

This means:
- **Space complexity drops from O(n) to O(1)**
- **No risk of stack overflow**
- **Performance comparable to iteration**

### Converting to Tail Recursion

The technique is to use an **accumulator** parameter that carries the result computed so far.

```cpp
#include <iostream>

// Tail-recursive factorial with accumulator
// With TCO: Time O(n), Space O(1)
// Without TCO: Time O(n), Space O(n)
long long factorial_tail(int n, long long acc = 1) {
    if (n <= 1) return acc;
    return factorial_tail(n - 1, n * acc);
}

// Tail-recursive Fibonacci with two accumulators
long long fib_tail(int n, long long a = 0, long long b = 1) {
    if (n == 0) return a;
    if (n == 1) return b;
    return fib_tail(n - 1, b, a + b);
}

// Tail-recursive sum of array
int sum_tail(const std::vector<int>& arr, int index, int acc) {
    if (index == arr.size()) return acc;
    return sum_tail(arr, index + 1, acc + arr[index]);
}

int main() {
    std::cout << "5! = " << factorial_tail(5) << "\n";       // 120
    std::cout << "fib(10) = " << fib_tail(10) << "\n";       // 55

    std::vector<int> arr = {1, 2, 3, 4, 5};
    std::cout << "Sum = " << sum_tail(arr, 0, 0) << "\n";    // 15
    return 0;
}
```

### When Is Tail Recursion Possible?

Tail recursion is possible when the recursive call naturally appears as the last operation, or when you can restructure the computation using accumulators. It is **not always possible** — for example, tree traversals that process both left and right subtrees cannot easily be made tail-recursive.

**C++ does NOT guarantee TCO.** Unlike Scheme or Haskell, the C++ standard does not require tail call optimization. However, modern compilers with `-O2` or `-O3` flags often perform it. In interviews, mention tail recursion as an optimization technique but do not rely on it — use explicit iteration when stack depth is a concern.

---

## 8.6 Recursion Trees

### Visualizing Recursive Calls

A **recursion tree** is a tree diagram where each node represents the work done at one level of recursion. It is an invaluable tool for:

1. **Understanding** how a recursive algorithm works
2. **Counting** the total amount of work done
3. **Deriving** the time complexity

### Example: Recursion Tree for Merge Sort

For `mergeSort` on an array of size 8:

```
Level 0:               [8 elements]              → O(8) work
                      /               \
Level 1:      [4 elements]       [4 elements]     → O(8) work
                /      \           /      \
Level 2:    [2]      [2]       [2]      [2]       → O(8) work
            / \      / \       / \      / \
Level 3:  [1] [1]  [1] [1]  [1] [1]  [1] [1]     → O(8) work

Total levels: log₂(8) = 3
Total work: 8 × 3 = 24 = O(n log n)
```

### Example: Recursion Tree for Naive Fibonacci

For `fib(5)`:

```
                        fib(5)
                      /        \
                fib(4)          fib(3)
               /      \        /     \
          fib(3)    fib(2)  fib(2)  fib(1)
          /    \    /    \   /   \
      fib(2) fib(1) fib(1) fib(0) fib(1) fib(0)
      /   \
  fib(1) fib(0)
```

Notice the **repeated subproblems**: `fib(3)` is computed twice, `fib(2)` three times. This is why naive Fibonacci is O(2^n) — the recursion tree has exponential nodes.

### Pattern Recognition with Recursion Trees

| Pattern | Example | Nodes per Level | Total Work |
|---------|---------|-----------------|------------|
| Linear decrease | Factorial, Fibonacci | Decreasing by 1 | O(n) |
| Binary split | Merge Sort, Quick Sort | Same at each level | O(n log n) |
| Exponential branching | Naive Fibonacci | Doubling each level | O(2^n) |
| Logarithmic depth | Binary Search | 1 per level | O(log n) |

### Tower of Hanoi — A Classic Recursion Problem

The Tower of Hanoi puzzle: move `n` disks from source peg to target peg using an auxiliary peg, following these rules:
1. Only one disk can be moved at a time.
2. A disk can only be placed on top of a larger disk.
3. Only the top disk of a peg can be moved.

```cpp
#include <iostream>
#include <string>

// Tower of Hanoi
// Time: O(2^n), Space: O(n) — recursion depth
void hanoi(int n, const std::string& source,
           const std::string& target,
           const std::string& auxiliary) {
    if (n == 1) {
        std::cout << "Move disk 1 from " << source << " to " << target << "\n";
        return;
    }
    // Move n-1 disks from source to auxiliary
    hanoi(n - 1, source, auxiliary, target);
    // Move the largest disk from source to target
    std::cout << "Move disk " << n << " from " << source << " to " << target << "\n";
    // Move n-1 disks from auxiliary to target
    hanoi(n - 1, auxiliary, target, source);
}

int main() {
    int n = 3;
    std::cout << "Tower of Hanoi with " << n << " disks:\n";
    hanoi(n, "A", "C", "B");
    return 0;
}
```

**Output for n=3:**
```
Move disk 1 from A to C
Move disk 2 from A to B
Move disk 1 from C to B
Move disk 3 from A to C
Move disk 1 from B to A
Move disk 2 from B to C
Move disk 1 from A to C
```

### Print All Subsets (Power Set)

Given a set of elements, print all possible subsets:

```cpp
#include <iostream>
#include <vector>
#include <string>

// Print all subsets using recursion
// Time: O(2^n), Space: O(n) recursion depth
void printSubsets(const std::vector<int>& nums, int index,
                  std::vector<int>& current) {
    if (index == nums.size()) {
        std::cout << "{ ";
        for (int v : current) std::cout << v << " ";
        std::cout << "}\n";
        return;
    }
    // Choice 1: Include nums[index]
    current.push_back(nums[index]);
    printSubsets(nums, index + 1, current);

    // Choice 2: Exclude nums[index]
    current.pop_back();
    printSubsets(nums, index + 1, current);
}

int main() {
    std::vector<int> nums = {1, 2, 3};
    std::vector<int> current;
    std::cout << "All subsets of {1, 2, 3}:\n";
    printSubsets(nums, 0, current);
    return 0;
}
```

**Output:**
```
All subsets of {1, 2, 3}:
{ 1 2 3 }
{ 1 2 }
{ 1 3 }
{ 1 }
{ 2 3 }
{ 2 }
{ 3 }
{ }
```

**Recursion tree for subsets:**

```
                        []
                   /          \
              [1]              []
            /     \          /    \
        [1,2]    [1]      [2]     []
        /   \    /  \     / \    / \
    [1,2,3][1,2][1,3][1][2,3][2][3][]
```

Each leaf represents one subset. There are \\(2^n\\) leaves for \\(n\\) elements.

---

## Interview Tips

1. **Always identify the base case first.** This is the most common source of bugs.
2. **Use the "leap of faith":** Trust that your recursive call works correctly for the smaller input, then focus on combining the result.
3. **Draw the recursion tree** for small inputs to understand the flow and count complexity.
4. **Memoize overlapping subproblems** — if the same subproblem appears multiple times, use a cache (this leads to dynamic programming).
5. **Know the tradeoffs:** Recursive solutions are elegant but may have stack overflow issues. Be ready to convert to iteration.
6. **Tail recursion is a bonus:** Mention it, but do not rely on TCO in C++.

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Missing base case | `int f(int n) { return n * f(n-1); }` | Add `if (n <= 1) return 1;` |
| Base case never reached | `f(n)` calls `f(n)` instead of `f(n-1)` | Ensure input moves toward base case |
| Off-by-one in base case | `factorial(0)` should return 1, not 0 | Verify base case with small inputs |
| Not handling negative input | `factorial(-1)` recurses forever | Add input validation |
| Excessive recomputation | Naive Fibonacci recalculates same values | Use memoization |
| Stack overflow on large input | Deep recursion with n > 10000 | Convert to iteration |

---

## Practice Problems

### Easy

1. **Sum of Digits** — Write a recursive function to compute the sum of digits of a positive integer.
   - *Hint:* `sumDigits(123) = 3 + sumDigits(12)`

2. **Reverse a String** — Reverse a string recursively.
   - *Hint:* `reverse(s) = reverse(s[1:]) + s[0]`

3. **Check Palindrome** — Determine if a string is a palindrome using recursion.
   - *Hint:* Compare first and last characters, recurse on the middle.

### Medium

4. **Power Set** — Return all subsets of a given set (already shown above, extend to handle duplicates).
   - *Hint:* Sort the input, skip duplicate elements at the same recursion level.

5. **Tower of Hanoi** — Implement Tower of Hanoi and count the number of moves for `n` disks.
   - *Hint:* The answer is \\(2^n - 1\\) moves.

6. **Generate Parentheses** — Generate all valid combinations of `n` pairs of parentheses.
   - *Hint:* Track the count of open and close parentheses. Add `(` if open < n, add `)` if close < open.

### Hard

7. **Regular Expression Matching** — Implement regex matching with `.` and `*`.
   - *Hint:* Handle `*` by considering zero or more occurrences of the preceding character.

8. **Word Break II** — Given a string and a dictionary, return all possible sentences.
   - *Hint:* At each position, try every word in the dictionary that matches the prefix.

9. **Sudoku Solver** — Solve a 9×9 Sudoku puzzle using backtracking (covered in detail in Chapter 9).

---

## Complexity Summary

| Algorithm | Time | Space | Notes |
|-----------|------|-------|-------|
| Factorial | O(n) | O(n) stack | Easily made iterative |
| Fibonacci (naive) | O(2^n) | O(n) stack | Use memoization → O(n) |
| Fibonacci (memoized) | O(n) | O(n) | Top-down DP |
| Fibonacci (iterative) | O(n) | O(1) | Bottom-up DP |
| Tower of Hanoi | O(2^n) | O(n) stack | Optimal — cannot be better |
| Power(x, n) | O(log n) | O(log n) stack | Divide and conquer |
| Merge Sort | O(n log n) | O(n) | Divide and conquer |
| Print all subsets | O(2^n) | O(n) stack | Must enumerate all subsets |
