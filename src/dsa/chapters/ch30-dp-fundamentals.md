# Chapter 30: Dynamic Programming Fundamentals

Dynamic Programming (DP) is one of the most powerful algorithmic paradigms in computer science and one of the most heavily tested topics in technical interviews. At its core, DP is about **solving complex problems by breaking them into simpler subproblems, solving each subproblem once, and storing the results** to avoid redundant computation. This chapter builds DP intuition from the ground up.

---

## 30.1 What Is DP?

### The "Never Solve the Same Problem Twice" Principle

Imagine you're solving a jigsaw puzzle. You wouldn't re-examine pieces you've already placed — you'd remember where they go. DP is exactly this: **solve each subproblem once, write down the answer, and look it up next time you need it.**

Think of it as a **recipe book for problems**:
1. Break a hard problem into smaller pieces.
2. Solve the smallest pieces first.
3. Write each answer in your book.
4. Combine the answers to solve bigger pieces.
5. Never re-solve a piece you've already solved.

This "remember and reuse" strategy turns exponential brute-force into efficient polynomial-time algorithms.

### A Concrete Analogy

Suppose you want to know: "How many ways can I climb 5 stairs if I can take 1 or 2 steps at a time?"

Brute force: enumerate every path — 1,1,1,1,1 … 1,2,2 … 2,1,2 … This grows exponentially.

DP insight: to reach stair 5, I must come from stair 4 or stair 3. So:
- ways(5) = ways(4) + ways(3)
- But to compute ways(4), I need ways(3) and ways(2) — and I already computed ways(3)!

By computing from the bottom up (ways(0), ways(1), ways(2), …) and storing each answer, I solve the whole problem in O(n) time instead of O(2^n).

### The Three Questions That Unlock Any DP Problem

Before writing any code, ask yourself:

1. **What are the subproblems?** What smaller versions of the problem do I need to solve?
   - *Example:* "How many ways to reach stair `i`?" for each `i` from 0 to `n`.

2. **What's the recurrence?** How does the answer to a subproblem relate to answers of smaller subproblems?
   - *Example:* `ways(i) = ways(i-1) + ways(i-2)` — I can arrive at stair `i` from stair `i-1` or stair `i-2`.

3. **What are the base cases?** What are the smallest subproblems I can answer directly?
   - *Example:* `ways(0) = 1` (one way to stay on the ground), `ways(1) = 1` (one way: take one step).

If you can answer these three questions, you have a DP solution. Everything else is implementation details.

---

Dynamic Programming is an optimization technique applied to problems that exhibit two key properties:

1. **Overlapping Subproblems** — The same subproblems are solved multiple times.
2. **Optimal Substructure** — The optimal solution to the problem can be constructed from optimal solutions to its subproblems.

If a problem has both properties, DP can transform an exponential-time brute-force solution into a polynomial-time algorithm.

### The Key Insight

Consider computing the Fibonacci sequence. The naive recursive definition is:

```
F(0) = 0, F(1) = 1
F(n) = F(n-1) + F(n-2)
```

This looks elegant, but it's catastrophically inefficient. Why? Because `F(n-1)` and `F(n-2)` both recompute `F(n-3)`, `F(n-4)`, etc. The same values are calculated exponentially many times.

**DP's insight**: If we've already computed `F(k)`, store it. When we need `F(k)` again, look it up in O(1) instead of recomputing it.

This simple idea — **compute once, reuse many times** — is the foundation of all dynamic programming.

### DP vs Brute Force: A Mental Model

Think of it this way:

| | Brute Force | DP |
|---|---|---|
| **Strategy** | Recompute everything | Compute once, remember |
| **Analogy** | Re-deriving formulas every time | Using a calculator with memory |
| **Fibonacci(40)** | ~1 billion operations | ~40 operations |
| **When it works** | Always (correct but slow) | When subproblems overlap |

The magic of DP is that it trades **space** (storing answers) for **time** (not recomputing them). This is almost always a worthwhile tradeoff.

---

## 30.2 Overlapping Subproblems

A problem has **overlapping subproblems** when a recursive algorithm revisits the same subproblems repeatedly.

### Fibonacci: The Canonical Example

Let's trace the recursion tree for `F(5)`:

```mermaid
graph TD
    F5["F(5)"] --> F4["F(4)"]
    F5 --> F3a["F(3)"]
    F4 --> F3b["F(3)"]
    F4 --> F2a["F(2)"]
    F3a --> F2b["F(2)"]
    F3a --> F1a["F(1)=1"]
    F3b --> F2c["F(2)"]
    F3b --> F1b["F(1)=1"]
    F2a --> F1c["F(1)=1"]
    F2a --> F0a["F(0)=0"]
    F2b --> F1d["F(1)=1"]
    F2b --> F0b["F(0)=0"]
    F2c --> F1e["F(1)=1"]
    F2c --> F0c["F(0)=0"]

    style F3a fill:#f99,stroke:#333,stroke-width:2px
    style F3b fill:#f99,stroke:#333,stroke-width:2px
    style F2a fill:#fc9,stroke:#333,stroke-width:2px
    style F2b fill:#fc9,stroke:#333,stroke-width:2px
    style F2c fill:#fc9,stroke:#333,stroke-width:2px
```

*Red = computed twice, orange = computed three times. With DP memoization, each node is computed only once.*

Notice: `F(3)` is computed **twice**, `F(2)` is computed **three times**, `F(1)` is computed **five times**. For `F(n)`, the time complexity is O(2^n) — exponential!

The number of unique subproblems is only `n+1` (from `F(0)` to `F(n)`), but without memoization, we compute each one exponentially many times.

### Naive Recursive Implementation

```cpp
#include <iostream>
#include <chrono>

// Naive recursive Fibonacci — O(2^n) time
long long fib_naive(int n) {
    if (n <= 1) return n;
    return fib_naive(n - 1) + fib_naive(n - 2);
}

int main() {
    auto start = std::chrono::high_resolution_clock::now();
    std::cout << "F(40) = " << fib_naive(40) << "\n";
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    std::cout << "Time: " << duration.count() << " ms\n";
    return 0;
}
```

For `n = 40`, this takes several seconds. For `n = 50`, it would take minutes.

### With Memoization

```cpp
#include <iostream>
#include <vector>
#include <chrono>

// Memoized Fibonacci — O(n) time, O(n) space
long long fib_memo(int n, std::vector<long long>& memo) {
    if (n <= 1) return n;
    if (memo[n] != -1) return memo[n];  // Already computed
    memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo);
    return memo[n];
}

int main() {
    int n = 40;
    std::vector<long long> memo(n + 1, -1);
    
    auto start = std::chrono::high_resolution_clock::now();
    std::cout << "F(40) = " << fib_memo(n, memo) << "\n";
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    std::cout << "Time: " << duration.count() << " microseconds\n";
    return 0;
}
```

The memoized version runs in microseconds. The difference is dramatic.

---

## 30.3 Optimal Substructure

A problem has **optimal substructure** if an optimal solution to the problem contains optimal solutions to its subproblems.

### Shortest Path Example

Consider finding the shortest path from A to D in a weighted graph. If the shortest path goes A → B → C → D, then:
- The path from A to C (A → B → C) must be the shortest path from A to C.
- The path from B to D (B → C → D) must be the shortest path from B to D.

If this weren't true — if there were a shorter path from A to C — we could substitute it and get a shorter path from A to D, contradicting our assumption.

### When Optimal Substructure Fails

Not all problems have optimal substructure. For example, the **longest simple path** problem in a general graph does NOT have optimal substructure because the subproblems share vertices and edges, making them non-independent.

**Key distinction**: Problems with optimal substructure allow us to combine subproblem solutions without them interfering with each other.

### How Subproblems Combine

In DP, we express the solution to a problem in terms of solutions to smaller subproblems using a **recurrence relation**. For example:

```
LCS(X[0..m-1], Y[0..n-1]) = 
    if X[m-1] == Y[n-1]:  1 + LCS(X[0..m-2], Y[0..n-2])
    else:                  max(LCS(X[0..m-2], Y[0..n-1]), LCS(X[0..m-1], Y[0..n-2]))
```

This recurrence captures the optimal substructure of the Longest Common Subsequence problem.

---

## 30.4 Memoization vs Tabulation

There are two approaches to implementing DP:

### Top-Down (Memoization)

- Start from the original problem and recurse.
- Cache results of each subproblem.
- Uses recursion + a memo table (usually a hash map or array).

### Bottom-Up (Tabulation)

- Start from the smallest subproblems.
- Build up solutions iteratively.
- Uses a DP table filled in a specific order.

### Code Comparison: Fibonacci

**Top-Down (Memoization)**:

```cpp
#include <iostream>
#include <vector>

class FibonacciTopDown {
    std::vector<long long> memo;
    
public:
    FibonacciTopDown(int n) : memo(n + 1, -1) {}
    
    long long solve(int n) {
        if (n <= 1) return n;
        if (memo[n] != -1) return memo[n];
        memo[n] = solve(n - 1) + solve(n - 2);
        return memo[n];
    }
};

int main() {
    FibonacciTopDown fib(50);
    for (int i = 0; i <= 10; ++i) {
        std::cout << "F(" << i << ") = " << fib.solve(i) << "\n";
    }
    return 0;
}
```

**Bottom-Up (Tabulation)**:

```cpp
#include <iostream>
#include <vector>

long long fib_bottom_up(int n) {
    if (n <= 1) return n;
    std::vector<long long> dp(n + 1);
    dp[0] = 0;
    dp[1] = 1;
    for (int i = 2; i <= n; ++i) {
        dp[i] = dp[i - 1] + dp[i - 2];
    }
    return dp[n];
}

int main() {
    for (int i = 0; i <= 10; ++i) {
        std::cout << "F(" << i << ") = " << fib_bottom_up(i) << "\n";
    }
    return 0;
}
```

### Tradeoffs

| Aspect | Memoization (Top-Down) | Tabulation (Bottom-Up) |
|--------|----------------------|----------------------|
| **Intuition** | Closer to natural recursion | Requires understanding order |
| **Computation** | Only computes needed subproblems | Computes ALL subproblems |
| **Stack usage** | Uses call stack (risk of stack overflow) | No recursion overhead |
| **Space** | Memo table + call stack | DP table only |
| **Debugging** | Harder to trace | Easier (iterative) |
| **Optimization** | Harder to space-optimize | Easy to space-optimize |

**Rule of thumb**: Start with memoization to get the recurrence right, then convert to tabulation for space optimization.

---

## 30.5 The DP Framework

Every DP problem can be solved by following this systematic framework:

```mermaid
flowchart LR
    S1["1. Define<br/>State"] --> S2["2. Write<br/>Recurrence"]
    S2 --> S3["3. Identify<br/>Base Cases"]
    S3 --> S4["4. Determine<br/>Order"]
    S4 --> S5["5. Extract<br/>Answer"]

    style S1 fill:#fdd,stroke:#333
    style S2 fill:#dfd,stroke:#333
    style S3 fill:#ddf,stroke:#333
    style S4 fill:#fdf,stroke:#333
    style S5 fill:#dff,stroke:#333
```

### Step 1: Define the State

What information do we need to represent a subproblem? This is the most critical step.

- **State variables**: What parameters uniquely identify a subproblem?
- **State meaning**: What does `dp[i]` (or `dp[i][j]`, etc.) represent?

**Beginner tip:** Write the state meaning as a complete English sentence before coding. For example: "`dp[i]` = the minimum number of coins needed to make amount `i`." If you can't explain what your DP table stores, you're not ready to write the recurrence.

### Step 2: Write the Recurrence Relation

Express the current state in terms of smaller states.

```
dp[i] = f(dp[i-1], dp[i-2], ...)
```

**Beginner tip:** Think about the *last decision* you make. For climbing stairs: "Did I come from stair i-1 or stair i-2?" This "last choice" framing makes recurrences much easier to write.

### Step 3: Identify Base Cases

What are the smallest subproblems whose answers are known directly?

**Beginner tip:** Base cases are the answers you know *without* any computation. For Fibonacci: F(0)=0, F(1)=1. For climbing stairs: ways(0)=1, ways(1)=1. Always check: does your recurrence handle n=0 and n=1 correctly?

### Step 4: Determine Computation Order

For bottom-up: In what order should we fill the DP table so that dependencies are satisfied?

**Beginner tip:** Draw the DP table as a grid. Mark which cells each cell depends on. Fill in the order that ensures dependencies are computed first (usually left-to-right, top-to-bottom).

### Step 5: Extract the Answer

Where is the final answer in the DP table?

**Beginner tip:** Sometimes it's `dp[n]`, sometimes `dp[n][m]`, sometimes `max(dp[i])` over all `i`. Know where to look before you start coding.

### Example: Climbing Stairs

**Problem**: You can climb 1 or 2 steps at a time. How many distinct ways to reach step `n`?

```mermaid
graph LR
    S0["dp[0]=1"] -->|"+1 step"| S1["dp[1]=1"]
    S0 -->|"+2 steps"| S2["dp[2]=2"]
    S1 -->|"+1 step"| S2
    S1 -->|"+2 steps"| S3["dp[3]=3"]
    S2 -->|"+1 step"| S3
    S2 -->|"+2 steps"| S4["dp[4]=5"]
    S3 -->|"+1 step"| S4
    S3 -->|"+2 steps"| S5["dp[5]=8"]
    S4 -->|"+1 step"| S5

    style S0 fill:#9f9,stroke:#333,stroke-width:2px
    style S5 fill:#f96,stroke:#333,stroke-width:2px
```

*Green = base case. Orange = answer. Each state transitions to the next via +1 or +2 steps. Recurrence: `dp[i] = dp[i-1] + dp[i-2]`.*

1. **State**: `dp[i]` = number of ways to reach step `i`
2. **Recurrence**: `dp[i] = dp[i-1] + dp[i-2]` (reach step `i` from step `i-1` or step `i-2`)
3. **Base case**: `dp[0] = 1` (one way to stay at ground), `dp[1] = 1`
4. **Order**: Compute `dp[0], dp[1], ..., dp[n]`
5. **Answer**: `dp[n]`

```cpp
#include <iostream>
#include <vector>

int climb_stairs(int n) {
    if (n <= 1) return 1;
    
    // Space-optimized: only need last two values
    int prev2 = 1;  // dp[0]
    int prev1 = 1;  // dp[1]
    
    for (int i = 2; i <= n; ++i) {
        int curr = prev1 + prev2;
        prev2 = prev1;
        prev1 = curr;
    }
    return prev1;
}

int main() {
    for (int n = 0; n <= 10; ++n) {
        std::cout << "Ways to climb " << n << " stairs: " << climb_stairs(n) << "\n";
    }
    return 0;
}
```

**Output**:
```
Ways to climb 0 stairs: 1
Ways to climb 1 stairs: 1
Ways to climb 2 stairs: 2
Ways to climb 3 stairs: 3
Ways to climb 4 stairs: 5
Ways to climb 5 stairs: 8
Ways to climb 6 stairs: 13
Ways to climb 7 stairs: 21
Ways to climb 8 stairs: 34
Ways to climb 9 stairs: 55
Ways to climb 10 stairs: 89
```

---

## 30.6 Classic Problems

Let's work through four classic DP problems, showing the progression from brute force to optimized solution.

### 30.6.1 Coin Change

**Problem**: Given coin denominations and a target amount, find the minimum number of coins needed.

```mermaid
graph LR
    A0["dp[0]=0"] -->|"coin 1"| A1["dp[1]=1"]
    A1 -->|"coin 1"| A2["dp[2]=2"]
    A2 -->|"coin 1"| A3["dp[3]=3"]
    A3 -->|"coin 1"| A4["dp[4]=4"]
    A4 -->|"coin 1"| A5a["dp[5]=..."]
    A0 -->|"coin 5"| A5b["dp[5]=1"]
    A0 -->|"coin 6"| A6["dp[6]=1"]
    A5b -->|"coin 6"| A11["dp[11]=2"]
    A6 -->|"coin 5"| A11

    style A0 fill:#9f9,stroke:#333,stroke-width:2px
    style A11 fill:#f96,stroke:#333,stroke-width:2px
    style A5b fill:#fc9,stroke:#333
    style A6 fill:#fc9,stroke:#333
```

*For coins {1,5,6} and amount 11: dp[11] = 2 (coins 5+6). The diagram shows how each state builds on previous states.*

#### Brute Force

Try every combination of coins. For each coin, try using it and recurse on the remaining amount.

```cpp
#include <iostream>
#include <vector>
#include <climits>

// Brute force — exponential time
int coin_change_brute(const std::vector<int>& coins, int amount) {
    if (amount == 0) return 0;
    if (amount < 0) return -1;
    
    int min_coins = INT_MAX;
    for (int coin : coins) {
        int result = coin_change_brute(coins, amount - coin);
        if (result != -1) {
            min_coins = std::min(min_coins, 1 + result);
        }
    }
    return (min_coins == INT_MAX) ? -1 : min_coins;
}
```

#### Memoization

```cpp
#include <iostream>
#include <vector>
#include <climits>

int coin_change_memo_helper(const std::vector<int>& coins, int amount, 
                            std::vector<int>& memo) {
    if (amount == 0) return 0;
    if (amount < 0) return -1;
    if (memo[amount] != -2) return memo[amount];
    
    int min_coins = INT_MAX;
    for (int coin : coins) {
        int result = coin_change_memo_helper(coins, amount - coin, memo);
        if (result != -1) {
            min_coins = std::min(min_coins, 1 + result);
        }
    }
    memo[amount] = (min_coins == INT_MAX) ? -1 : min_coins;
    return memo[amount];
}

int coin_change_memo(const std::vector<int>& coins, int amount) {
    std::vector<int> memo(amount + 1, -2);  // -2 means "not computed"
    return coin_change_memo_helper(coins, amount, memo);
}

int main() {
    std::vector<int> coins = {1, 5, 10, 25};
    int amount = 30;
    std::cout << "Min coins for " << amount << ": " 
              << coin_change_memo(coins, amount) << "\n";
    return 0;
}
```

#### Tabulation

```cpp
#include <iostream>
#include <vector>
#include <climits>

int coin_change_tab(const std::vector<int>& coins, int amount) {
    // dp[i] = minimum coins to make amount i
    std::vector<int> dp(amount + 1, INT_MAX);
    dp[0] = 0;  // base case: 0 coins for amount 0
    
    for (int i = 1; i <= amount; ++i) {
        for (int coin : coins) {
            if (coin <= i && dp[i - coin] != INT_MAX) {
                dp[i] = std::min(dp[i], dp[i - coin] + 1);
            }
        }
    }
    return (dp[amount] == INT_MAX) ? -1 : dp[amount];
}

int main() {
    std::vector<int> coins = {1, 5, 10, 25};
    std::cout << "Min coins for 30: " << coin_change_tab(coins, 30) << "\n";
    std::cout << "Min coins for 11 (coins={1,5,6}): " 
              << coin_change_tab({1, 5, 6}, 11) << "\n";
    return 0;
}
```

**Complexity**: O(amount × |coins|) time, O(amount) space.

### 30.6.2 0/1 Knapsack

**Problem**: Given `n` items with weights and values, and a knapsack of capacity `W`, maximize the total value. Each item can be used at most once.

#### Brute Force

Try all 2^n subsets. For each subset, check if total weight ≤ W and track maximum value.

#### Tabulation (Bottom-Up)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int knapsack_01(const std::vector<int>& weights, const std::vector<int>& values, 
                int capacity) {
    int n = weights.size();
    // dp[i][w] = max value using items 0..i-1 with capacity w
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(capacity + 1, 0));
    
    for (int i = 1; i <= n; ++i) {
        for (int w = 0; w <= capacity; ++w) {
            // Don't take item i-1
            dp[i][w] = dp[i - 1][w];
            // Take item i-1 (if it fits)
            if (weights[i - 1] <= w) {
                dp[i][w] = std::max(dp[i][w], 
                                     dp[i - 1][w - weights[i - 1]] + values[i - 1]);
            }
        }
    }
    return dp[n][capacity];
}

// Space-optimized version using 1D array
int knapsack_01_optimized(const std::vector<int>& weights, 
                          const std::vector<int>& values, int capacity) {
    int n = weights.size();
    std::vector<int> dp(capacity + 1, 0);
    
    for (int i = 0; i < n; ++i) {
        // Traverse backwards to avoid using an item twice
        for (int w = capacity; w >= weights[i]; --w) {
            dp[w] = std::max(dp[w], dp[w - weights[i]] + values[i]);
        }
    }
    return dp[capacity];
}

int main() {
    std::vector<int> weights = {2, 3, 4, 5};
    std::vector<int> values  = {3, 4, 5, 6};
    int capacity = 8;
    
    std::cout << "Max value (2D): " << knapsack_01(weights, values, capacity) << "\n";
    std::cout << "Max value (1D): " << knapsack_01_optimized(weights, values, capacity) << "\n";
    return 0;
}
```

**Output**:
```
Max value (2D): 10
Max value (1D): 10
```

**Dry Run** with weights = [2, 3, 4, 5], values = [3, 4, 5, 6], capacity = 8:

```
DP Table (rows = items considered, columns = capacity 0..8):

         w=0  w=1  w=2  w=3  w=4  w=5  w=6  w=7  w=8
i=0 (  )   0    0    0    0    0    0    0    0    0
i=1 (w=2,v=3)  0    0    3    3    3    3    3    3    3
i=2 (w=3,v=4)  0    0    3    4    4    7    7    7    7
i=3 (w=4,v=5)  0    0    3    4    5    7    8    9    9
i=4 (w=5,v=6)  0    0    3    4    5    7    8    9   10

Reading dp[4][8] = 10.

How to get 10? Items 2 (w=3, v=4) + Item 4 (w=5, v=6) = weight 8, value 10.

Trace back: dp[4][8] ≠ dp[3][8] (9 vs 10) → item 4 taken.
  Remaining capacity: 8 - 5 = 3. dp[3][3] = 4.
  dp[3][3] ≠ dp[2][3] (4 vs 4) → item 3 NOT taken (same value).
  dp[2][3] ≠ dp[1][3] (4 vs 3) → item 2 taken.
  Remaining capacity: 3 - 3 = 0. dp[1][0] = 0 → done.
  Items taken: 2 and 4. ✓
```

**Complexity**: O(n × W) time. 2D version: O(n × W) space. 1D version: O(W) space.

### 30.6.3 Longest Common Subsequence (LCS)

**Problem**: Given two strings, find the length of their longest common subsequence.

#### Tabulation

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

int lcs(const std::string& s1, const std::string& s2) {
    int m = s1.size(), n = s2.size();
    // dp[i][j] = LCS of s1[0..i-1] and s2[0..j-1]
    std::vector<std::vector<int>> dp(m + 1, std::vector<int>(n + 1, 0));
    
    for (int i = 1; i <= m; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (s1[i - 1] == s2[j - 1]) {
                dp[i][j] = 1 + dp[i - 1][j - 1];
            } else {
                dp[i][j] = std::max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }
    return dp[m][n];
}

// Space-optimized: O(min(m,n)) space
int lcs_optimized(const std::string& s1, const std::string& s2) {
    // Make s1 the shorter string
    if (s1.size() > s2.size()) return lcs_optimized(s2, s1);
    
    int m = s1.size(), n = s2.size();
    std::vector<int> prev(m + 1, 0), curr(m + 1, 0);
    
    for (int j = 1; j <= n; ++j) {
        for (int i = 1; i <= m; ++i) {
            if (s1[i - 1] == s2[j - 1]) {
                curr[i] = 1 + prev[i - 1];
            } else {
                curr[i] = std::max(prev[i], curr[i - 1]);
            }
        }
        std::swap(prev, curr);
        std::fill(curr.begin(), curr.end(), 0);
    }
    return prev[m];
}

int main() {
    std::string s1 = "ABCBDAB";
    std::string s2 = "BDCABA";
    std::cout << "LCS length (2D): " << lcs(s1, s2) << "\n";
    std::cout << "LCS length (1D): " << lcs_optimized(s1, s2) << "\n";
    return 0;
}
```

**Output**:
```
LCS length (2D): 4
LCS length (1D): 4
```

The LCS is "BCBA" (length 4).

**Dry Run** with s1 = "ABCBDAB", s2 = "BDCABA":

```
DP Table (rows = s1 prefixes, columns = s2 prefixes):

       ""  B  D  C  A  B  A
""      0  0  0  0  0  0  0
A       0  0  0  0  1  1  1
B       0  1  1  1  1  2  2
C       0  1  1  2  2  2  2
B       0  1  1  2  2  3  3
D       0  1  2  2  2  3  3
A       0  1  2  2  3  3  4
B       0  1  2  2  3  4  4

Reading dp[7][6] = 4.

Trace back to find the LCS "BCBA":
  dp[7][6]=4, s1[6]='B' == s2[5]='A'? No → max(dp[6][6], dp[7][5]) = max(4,4)
  Go up: dp[6][6]=4, s1[5]='A' == s2[5]='A'? Yes → 'A' is in LCS.
  Move to dp[5][5]=3, s1[4]='D' == s2[4]='B'? No → max(dp[4][5], dp[5][4])
  dp[4][5]=3, s1[3]='B' == s2[4]='B'? Yes → 'B' is in LCS.
  Move to dp[3][4]=2, s1[2]='C' == s2[3]='A'? No → max(dp[2][4], dp[3][3])
  dp[3][3]=2, s1[2]='C' == s2[2]='C'? Yes → 'C' is in LCS.
  Move to dp[2][2]=1, s1[1]='B' == s2[1]='D'? No → max(dp[1][2], dp[2][1])
  dp[2][1]=1, s1[1]='B' == s2[0]='B'? Yes → 'B' is in LCS.
  Move to dp[1][0]=0 → done.
  LCS (reversed): A, B, C, B → "BCBA" ✓
```

**Complexity**: O(m × n) time, O(m × n) or O(min(m, n)) space.

---

## 30.7 State Space Design

The hardest part of DP is choosing the right state definition. Here are principles to guide you:

### Single Variable State

When the problem involves one sequence or one dimension of choice:

```
dp[i] = answer for the prefix [0..i]
```

**Examples**: Climbing stairs, house robber, maximum subarray.

### Multiple Variable State

When the problem involves two sequences or two dimensions:

```
dp[i][j] = answer for prefixes s1[0..i-1] and s2[0..j-1]
```

**Examples**: LCS, edit distance, knapsack.

### State Design Principles

1. **State should capture all information needed** to solve the subproblem independently.
2. **State should be minimal** — include only what's necessary.
3. **State should lead to a recurrence** that expresses the current state in terms of smaller states.

### Example: Why State Matters

Consider a problem: "Find the maximum profit from buying and selling a stock at most `k` times."

**Bad state**: `dp[i]` = max profit up to day `i`. (Doesn't track how many transactions used.)

**Good state**: `dp[i][j][0/1]` = max profit up to day `i`, with at most `j` transactions, where 0 = not holding, 1 = holding.

The state must capture everything that affects future decisions.

### Dry Run: Coin Change

Let's trace `coin_change_tab({1, 5, 6}, 11)`:

```
dp[0]  = 0  (base case)
dp[1]  = dp[0] + 1 = 1  (use coin 1)
dp[2]  = dp[1] + 1 = 2
dp[3]  = dp[2] + 1 = 3
dp[4]  = dp[3] + 1 = 4
dp[5]  = min(dp[4]+1, dp[0]+1) = min(5, 1) = 1  (use coin 5)
dp[6]  = min(dp[5]+1, dp[1]+1, dp[0]+1) = min(2, 2, 1) = 1  (use coin 6)
dp[7]  = min(dp[6]+1, dp[2]+1, dp[1]+1) = min(2, 3, 2) = 2
dp[8]  = min(dp[7]+1, dp[3]+1, dp[2]+1) = min(3, 4, 3) = 3
dp[9]  = min(dp[8]+1, dp[4]+1, dp[3]+1) = min(4, 5, 4) = 4
dp[10] = min(dp[9]+1, dp[5]+1, dp[4]+1) = min(5, 2, 5) = 2
dp[11] = min(dp[10]+1, dp[6]+1, dp[5]+1) = min(3, 2, 2) = 2
```

Answer: 2 (coins 5 + 6).

---

## Interview Tips

1. **Always start with the recurrence relation**. Don't worry about optimization until you have a correct recurrence.

2. **Draw the recursion tree** for small inputs. This reveals overlapping subproblems and guides your state definition.

3. **State definition is 80% of the work**. If you get the state right, the recurrence almost writes itself.

4. **Start with memoization**, then convert to tabulation. It's easier to think recursively.

5. **Space optimization**: If `dp[i]` only depends on `dp[i-1]`, you only need two rows (or one row with backward iteration).

6. **Verify base cases carefully**. Off-by-one errors in base cases are the #1 source of bugs.

7. **Trace through a small example** by hand before coding. Fill in a DP table on paper.

### The "DP Table as Spreadsheet" Technique

If you're stuck, literally draw a spreadsheet:

1. Label rows and columns with your state variables.
2. Fill in the base cases.
3. For each cell, write the formula (recurrence) that computes it.
4. Fill cells in order until you reach the answer.

This physical act of filling cells makes the DP structure concrete and often reveals the pattern you need. Many experienced engineers still do this for unfamiliar DP problems.

### From Brute Force to DP: A Step-by-Step Process

1. **Write the brute-force recursive solution first.** Don't optimize — just make it correct.
2. **Identify the repeated subproblems.** Add print statements or draw the recursion tree.
3. **Add a memo table.** Cache results of each unique subproblem call.
4. **Convert to bottom-up.** Replace recursion with iteration and a DP table.
5. **Optimize space.** If you only need the previous row, use a 1D array.

This process works for 90% of DP problems. Don't try to jump to step 4 — get step 1 right first.

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---------|---------------|-----|
| Forgetting base cases | Leads to wrong answers or infinite recursion | Always define base cases first |
| Wrong iteration order | Bottom-up needs dependencies computed first | Draw dependency graph |
| Not initializing DP table | Garbage values lead to wrong comparisons | Initialize to appropriate sentinel |
| Using INT_MAX without overflow checks | `INT_MAX + 1` overflows | Check before adding |
| Off-by-one in indices | `dp[i]` vs `dp[i-1]` confusion | Be explicit about what `i` represents |
| Space optimization breaks order | 1D knapsack must iterate backwards | Understand why direction matters |

## Practice Problems

1. **Min Cost Climbing Stairs** (LeetCode 746) — `dp[i] = min(dp[i-1]+cost[i-1], dp[i-2]+cost[i-2])`
2. **House Robber** (LeetCode 198) — `dp[i] = max(dp[i-1], dp[i-2]+nums[i])`
3. **Decode Ways** (LeetCode 91) — Count ways to decode a digit string
4. **Unique Paths** (LeetCode 62) — 2D DP on a grid
5. **Minimum Path Sum** (LeetCode 64) — 2D DP with cost accumulation
6. **Partition Equal Subset Sum** (LeetCode 416) — 0/1 Knapsack variant
7. **Coin Change 2** (LeetCode 518) — Count number of combinations
8. **Longest Palindromic Subsequence** (LeetCode 516) — LCS variant
9. **Edit Distance** (LeetCode 72) — Classic 2D DP
10. **Word Break** (LeetCode 139) — DP + dictionary lookup

---

## Additional Exercises

### Exercise 1: Minimum Cost to Reach End with Variable Steps
**Difficulty**: Medium
**Problem**: Given an array `cost` of size n, you start at index 0 and can jump 1, 2, or 3 steps at a time. Each step to index i costs `cost[i]`. Find the minimum cost to reach index n-1 (or beyond). You may start from index 0 or index 1.
**Hint**: Define `dp[i]` as the minimum cost to reach index i. Recurrence: `dp[i] = cost[i] + min(dp[i-1], dp[i-2], dp[i-3])`. Base cases: `dp[0] = cost[0]`, `dp[1] = cost[1]`.
**Expected Time Complexity**: O(n), Space: O(1) with rolling variables.

### Exercise 2: Longest Increasing Subsequence (LIS)
**Difficulty**: Medium
**Problem**: Given an array of integers, find the length of the longest strictly increasing subsequence.
**Hint**: Define `dp[i]` = length of LIS ending at index i. Recurrence: `dp[i] = max(dp[j] + 1)` for all `j < i` where `arr[j] < arr[i]`. For O(n log n), maintain a sorted array of the smallest tail element for each LIS length.
**Expected Time Complexity**: O(n²) with DP, O(n log n) with binary search optimization.

### Exercise 3: Palindrome Partitioning (Minimum Cuts)
**Difficulty**: Hard
**Problem**: Given a string, find the minimum number of cuts needed to partition it such that every substring in the partition is a palindrome.
**Hint**: Precompute `isPalin[i][j]` (whether s[i..j] is a palindrome) in O(n²). Then define `dp[i]` = minimum cuts for s[0..i]. Recurrence: `dp[i] = min(dp[j-1] + 1)` for all `j <= i` where s[j..i] is a palindrome. Base case: `dp[i] = 0` if s[0..i] is already a palindrome.
**Expected Time Complexity**: O(n²).

### Exercise 4: Decode Ways
**Difficulty**: Medium
**Problem**: A message containing letters A-Z is encoded as numbers: 'A'→1, 'B'→2, ... 'Z'→26. Given a string of digits, count the number of ways to decode it.
**Hint**: Define `dp[i]` = number of ways to decode s[0..i-1]. If s[i-1] != '0', `dp[i] += dp[i-1]`. If s[i-2..i-1] forms a number between 10 and 26, `dp[i] += dp[i-2]`. Watch for leading zeros.
**Expected Time Complexity**: O(n), Space: O(1).

### Exercise 5: Maximum Profit from Stock Trading (At Most K Transactions)
**Difficulty**: Hard
**Problem**: Given stock prices for n days and an integer k, find the maximum profit from at most k buy-sell transactions. You cannot hold more than one share at a time.
**Hint**: Define `dp[t][d]` = max profit using at most t transactions up to day d. Recurrence: `dp[t][d] = max(dp[t][d-1], max(price[d] - price[j] + dp[t-1][j])` for all `j < d`. Optimize the inner max with a running variable.
**Expected Time Complexity**: O(nk) with optimization (O(n²k) naive).

### Exercise 6: Minimum Edit Distance
**Difficulty**: Medium
**Problem**: Given two strings, find the minimum number of operations (insert, delete, replace) to transform one into the other.
**Hint**: Define `dp[i][j]` = edit distance between s1[0..i-1] and s2[0..j-1]. If `s1[i-1] == s2[j-1]`, `dp[i][j] = dp[i-1][j-1]`. Otherwise, `dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])`.
**Expected Time Complexity**: O(m × n).

### Exercise 7: Partition Equal Subset Sum
**Difficulty**: Medium
**Problem**: Given a non-empty array of positive integers, determine if it can be partitioned into two subsets with equal sum.
**Hint**: If total sum is odd, return false. Otherwise, this is a 0/1 knapsack problem: can we select elements that sum to `total/2`? Define `dp[j]` = true if sum j is achievable. Iterate items, then iterate j backwards from target.
**Expected Time Complexity**: O(n × sum/2).

### Exercise 8: Maximum Length of Repeated Subarray
**Difficulty**: Medium
**Problem**: Given two integer arrays, find the maximum length of a subarray that appears in both arrays.
**Hint**: Define `dp[i][j]` = length of the longest common subarray ending at nums1[i-1] and nums2[j-1]. If `nums1[i-1] == nums2[j-1]`, `dp[i][j] = dp[i-1][j-1] + 1`. Track the global maximum.
**Expected Time Complexity**: O(m × n).

### Exercise 9: Unique Paths with Obstacles
**Difficulty**: Medium
**Problem**: Given an m×n grid where some cells are blocked (marked 1), count the number of unique paths from top-left to bottom-right, moving only right or down.
**Hint**: `dp[i][j] = 0` if `grid[i][j] == 1`, else `dp[i][j] = dp[i-1][j] + dp[i][j-1]`. Handle the first row and first column carefully — once you hit an obstacle, all cells after it are 0.
**Expected Time Complexity**: O(m × n).

### Exercise 10: Burst Balloons
**Difficulty**: Hard
**Problem**: Given n balloons with numbers on them, bursting balloon i yields `nums[i-1] × nums[i] × nums[i+1]` coins (with virtual balloons of value 1 at boundaries). Find the maximum coins by bursting all balloons.
**Hint**: Instead of thinking "which balloon to burst first," think "which balloon to burst last in range [l, r]." Define `dp[l][r]` = max coins from bursting all balloons in (l, r). Recurrence: `dp[l][r] = max(dp[l][k] + dp[k][r] + nums[l] × nums[k] × nums[r])` for all `k` in (l, r). Process by increasing interval length.
**Expected Time Complexity**: O(n³).

---

## Additional Interview Questions

### Q1: When should you use memoization vs tabulation in an interview?
**Key Insight**: Start with memoization to get the recurrence right — it's more intuitive because it mirrors the natural recursive thought process. Once you have a correct recurrence, convert to tabulation if you need space optimization (e.g., reducing from O(n²) to O(n) by keeping only the previous row). In interviews, memoization is often faster to code and less error-prone for complex state spaces.
**Optimal Complexity**: Both have the same time complexity. Tabulation often allows easier space optimization.

### Q2: How do you identify the state space for a DP problem?
**Key Insight**: Ask yourself: "What information do I need to know to solve the remaining subproblem?" The state variables are exactly those pieces of information. For example, in knapsack: (item index, remaining capacity). In LCS: (position in string 1, position in string 2). The state should be **minimal** — every variable must affect the answer. If removing a variable doesn't change correctness, remove it.
**Optimal Complexity**: The number of states determines the time complexity. Minimize state variables to minimize complexity.

### Q3: How do you detect if a problem is solvable by DP vs greedy?
**Key Insight**: DP is needed when you face a **choice** where the locally optimal choice isn't guaranteed to be globally optimal (greedy-choice property fails). Test: can you construct a counterexample where picking the greedy option leads to a worse overall result? If yes, use DP. Also, if the problem asks for a count or a specific combination (not just the optimal value), DP is almost always the answer.
**Optimal Complexity**: If greedy works, it's typically O(n log n) or O(n). DP solutions are typically O(n²) or O(nk).

### Q4: What is the significance of computing DP values in the correct order?
**Key Insight**: In bottom-up tabulation, you must fill the DP table such that when you compute `dp[i]`, all values it depends on are already computed. Drawing the dependency graph (which states depend on which) reveals the correct order. For example, in 2D DP on strings, you fill row by row (or column by column). For interval DP, you fill by increasing interval length. Wrong order = using uninitialized values = wrong answer.
**Optimal Complexity**: The order doesn't change time complexity, but getting it wrong causes incorrect results.

### Q5: How do you optimize space in 2D DP problems?
**Key Insight**: If `dp[i][j]` only depends on `dp[i-1][...]` (the previous row), you only need two rows — `prev` and `curr`. After computing `curr`, swap them. For 1D recurrence (like Fibonacci), you only need the last 1-2 values. The backward iteration trick in 0/1 knapsack (`for w = W down to weight[i]`) reduces 2D to 1D because it prevents using an item twice.
**Optimal Complexity**: Space reduces from O(n × m) to O(m), time remains unchanged.

### Q6: How do you handle DP problems with very large state spaces (e.g., n up to 10^9)?
**Key Insight**: When n is too large for a DP table, look for **patterns** in the recurrence. Linear recurrences (like Fibonacci) can be computed in O(log n) using matrix exponentiation. Alternatively, look for **cycle detection** in the state transitions. Some problems have **mathematical closed-form** solutions that bypass DP entirely.
**Optimal Complexity**: Matrix exponentiation gives O(k³ log n) for k×k matrices, where k is the recurrence order.

### Q7: What is the difference between counting problems and optimization problems in DP?
**Key Insight**: In optimization (min/max), the recurrence uses `min()` or `max()`. In counting problems, the recurrence uses `+`. The key difference is in handling overlapping choices: optimization picks the best, counting sums all possibilities. A common mistake is using `max` in a counting problem or `+` in an optimization problem. Also, counting problems often require careful handling of double-counting.
**Optimal Complexity**: Counting and optimization DP have the same time complexity structure; the difference is in the combine operation.

### Q8: How do you approach a DP problem you've never seen before?
**Key Insight**: Follow the 5-step framework: (1) Define the state — what uniquely identifies a subproblem? (2) Write the recurrence — how does the current state relate to smaller states? (3) Identify base cases — what are the smallest subproblems? (4) Determine computation order — bottom-up order. (5) Extract the answer. Always start with a small example and fill in a DP table by hand before coding.
**Optimal Complexity**: The framework itself doesn't determine complexity, but it systematically leads you to the correct recurrence, which then determines complexity.

### Q9: Can DP problems have multiple valid state definitions? How do you choose?
**Key Insight**: Yes, often multiple state definitions work, but they lead to different complexities. For example, the stock trading problem can be defined as `dp[i][k][holding]` (day, transactions remaining, holding or not) or `dp[i][k]` (day, transactions used). The key criterion: the state must capture **all** information needed to make future decisions, and the recurrence must express the current state in terms of **smaller** states (no cycles). Prefer the state definition that leads to the simplest recurrence.
**Optimal Complexity**: Different state definitions can yield O(n), O(n²), or O(nk) for the same problem. Choose wisely.

### Q10: Explain the "interval DP" pattern and when it applies.
**Key Insight**: Interval DP applies when you need to solve a problem on a contiguous subarray and the solution depends on splitting that subarray at some point. Define `dp[l][r]` = answer for the subarray [l, r]. Recurrence: try all split points k, `dp[l][r] = optimize(dp[l][k] + dp[k+1][r] + cost(l, r, k))`. Process by increasing interval length. Classic examples: matrix chain multiplication, burst balloons, optimal BST.
**Optimal Complexity**: Typically O(n³) due to three nested loops (left, right, split point).

---

## See Also

- [Chapter 31: DP Patterns](ch31-dp-patterns.md) — A catalog of common DP patterns (knapsack, LIS, interval DP, bitmask DP) that build on the fundamentals here.
- [Chapter 85: Digit DP](ch85-digit-dp.md) — A specialized DP technique for counting problems with digit constraints; processes numbers digit by digit.
- [Chapter 86: DP Optimization](ch86-dp-optimization.md) — Knuth's optimization, divide-and-conquer DP, and convex hull trick for speeding up naive DP transitions.
- [Chapter 32: Greedy](ch32-greedy.md) — When greedy works, it's simpler than DP; understanding the greedy-choice property helps identify when DP is necessary.
- [Chapter 59: DP Expanded](ch59-dp-expanded.md) — Additional DP topics and advanced patterns for deeper study.
