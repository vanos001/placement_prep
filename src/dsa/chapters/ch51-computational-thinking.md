# Computational Thinking



## Prerequisites

- Basic programming constructs (loops, conditionals, functions)
- Familiarity with at least one programming language
- Basic understanding of algorithms and data structures

## Interview Frequency

★★★★★ — Foundational for **all** interviews. Every algorithmic problem requires computational thinking skills. These meta-skills underpin every solution you write.

## Companies

Google, Meta, Amazon, Microsoft, Apple, Netflix, Stripe, Palantir, Jane Street, Two Sigma — every company that asks algorithmic questions implicitly tests computational thinking.

---

## Overview

Computational thinking is the set of mental frameworks that let you translate real-world and abstract problems into computational solutions. It is not a data structure or an algorithm — it is the *way of thinking* that leads you to choose the right one. This chapter covers eleven pillars of computational thinking, each illustrated with definitions, real-world analogies, DSA examples, and interview applications.

| Concept | Core Question | Key Benefit |
|---------|--------------|-------------|
| Problem Decomposition | Can I break this into smaller pieces? | Manageable subproblems |
| Abstraction | What details can I ignore? | Focus on what matters |
| Modeling | How do I represent this formally? | Translates to known structures |
| Pattern Recognition | Have I seen something like this before? | Reuse known solutions |
| Invariants | What doesn't change? | Reasoning anchors |
| State Representation | How do I encode the situation? | Efficient exploration |
| Reduction | Can I transform this into a known problem? | Leverage existing solutions |
| Decision Trees | What are my choices at each step? | Systematic exploration |
| Greedy Thinking | What's the best local choice? | Simple, fast solutions |
| Recursive Thinking | Does this contain smaller copies of itself? | Natural decomposition |
| DP Mindset | Are there overlapping subproblems? | Avoid redundant work |

---

## 1. Problem Decomposition

### Definition

Problem decomposition is the process of breaking a complex problem into smaller, independent (or semi-independent) subproblems that are easier to solve individually. The final solution is assembled from the sub-solutions.

### Real-World Analogy

Building a house: you don't construct it as one monolithic task. You decompose into foundation, framing, electrical, plumbing, roofing, etc. Each sub-task has its own team, materials, and schedule. The house is the sum of these coordinated sub-tasks.

### DSA Example

**Merge Sort** is the textbook decomposition algorithm:

```
Sort [38, 27, 43, 3, 9, 82, 10]
  → Sort [38, 27, 43] and Sort [3, 9, 82, 10]
    → Sort [38] and Sort [27, 43] ...
    → Merge sorted halves
```

The problem of sorting *n* elements is decomposed into two problems of sorting *n/2* elements, then merging — an O(n log n) solution emerges naturally.

### Interview Application

When you see a problem that seems overwhelming, ask:

1. **Can I solve a simpler version first?** (e.g., solve for a subarray, a subtree, a prefix)
2. **Can I combine sub-solutions?** (e.g., merge, concatenate, aggregate)
3. **Is the problem separable?** (e.g., left half doesn't depend on right half)

**Example:** "Find the maximum subarray sum" → decompose into: max subarray entirely in left half, entirely in right half, or crossing the midpoint. This leads to Kadane's divide-and-conquer variant.

```cpp
#include <algorithm>
#include <vector>
#include <climits>

struct SubarrayInfo {
    int max_sum;
    int max_prefix;
    int max_suffix;
    int total;
};

SubarrayInfo solve(const std::vector<int>& a, int lo, int hi) {
    if (lo == hi) {
        int v = std::max(a[lo], 0);
        return {v, v, v, a[lo]};
    }
    int mid = lo + (hi - lo) / 2;
    auto left = solve(a, lo, mid);
    auto right = solve(a, mid + 1, hi);
    SubarrayInfo res;
    res.total = left.total + right.total;
    res.max_prefix = std::max(left.max_prefix, left.total + right.max_prefix);
    res.max_suffix = std::max(right.max_suffix, right.total + left.max_suffix);
    res.max_sum = std::max({left.max_sum, right.max_sum, left.max_suffix + right.max_prefix});
    return res;
}

int max_subarray_sum(const std::vector<int>& a) {
    if (a.empty()) return 0;
    return solve(a, 0, (int)a.size() - 1).max_sum;
}
```

---

## 2. Abstraction

### Definition

Abstraction is the process of stripping away irrelevant details to focus on the essential structure of a problem. It answers: *what do I actually need to care about?*

### Real-World Analogy

A subway map doesn't show geographic distances — it abstracts away geography and shows only stations and connections. This makes route planning easier, not harder.

### DSA Example

**Graph problems** are often exercises in abstraction. "A social network where people have friends" → abstract to an undirected graph. "A dependency build system" → abstract to a DAG. "A maze" → abstract to a grid graph.

Once abstracted, you can apply BFS, DFS, topological sort, etc., without caring about the original domain.

### Interview Application

When you hear a wordy problem description, immediately ask:

- What are the **entities**? (nodes, edges, values)
- What are the **relationships**? (adjacency, ordering, containment)
- What are the **constraints**? (bounds, uniqueness, monotonicity)
- What is the **goal**? (minimize, maximize, count, find)

**Example:** "There are N cities connected by flights with prices. Find the cheapest route from city A to city B with at most K stops." → Abstract to: weighted directed graph, find shortest path with at most K+1 edges → BFS with state (node, stops_used) or Bellman-Ford with K+1 iterations.

---

## 3. Modeling

### Definition

Modeling is the act of representing a real-world or abstract problem using formal computational structures: graphs, trees, arrays, matrices, state machines, etc.

### Real-World Analogy

An architect creates a blueprint (model) before building. The blueprint captures structural relationships without the physical complexity.

### DSA Example

**Modeling a puzzle as a graph:** The "Word Ladder" problem (transform "hit" to "cog" by changing one letter at a time, each intermediate word must be valid) can be modeled as a graph where nodes are words and edges connect words that differ by one letter. BFS on this graph gives the shortest transformation sequence.

```cpp
#include <string>
#include <vector>
#include <unordered_set>
#include <queue>

int ladder_length(const std::string& begin, const std::string& end,
                  const std::vector<std::string>& word_list) {
    std::unordered_set<std::string> dict(word_list.begin(), word_list.end());
    if (!dict.count(end)) return 0;
    std::queue<std::pair<std::string, int>> q;
    q.push({begin, 1});
    std::unordered_set<std::string> visited;
    visited.insert(begin);
    while (!q.empty()) {
        auto [word, dist] = q.front();
        q.pop();
        for (int i = 0; i < (int)word.size(); ++i) {
            char orig = word[i];
            for (char c = 'a'; c <= 'z'; ++c) {
                if (c == orig) continue;
                word[i] = c;
                if (word == end) return dist + 1;
                if (dict.count(word) && !visited.count(word)) {
                    visited.insert(word);
                    q.push({word, dist + 1});
                }
            }
            word[i] = orig;
        }
    }
    return 0;
}
```

### Interview Application

Common modeling patterns:
- **Scheduling/conflicts** → Interval graphs, greedy by end time
- **Dependencies** → DAG, topological sort
- **State transitions** → BFS/DFS on implicit graph
- **Optimization with constraints** → DP with state encoding
- **Matching** → Bipartite graph, max flow

---

## 4. Pattern Recognition

### Definition

Pattern recognition is the ability to identify structural similarities between a new problem and problems you've solved before. It is the primary accelerator in interviews.

### Real-World Analogy

A doctor recognizes symptoms as a known disease pattern. A chess player recognizes board positions as known tactical motifs. Experience converts novel situations into familiar patterns.

### DSA Example

**Sliding window pattern:** Many problems share the structure "find the longest/shortest subarray satisfying some property where extending the window monotonically affects feasibility." Recognizing this pattern lets you apply the two-pointer sliding window template.

| Pattern Signal | Technique |
|---------------|-----------|
| "Longest subarray with at most K distinct" | Sliding window |
| "Shortest path with exactly K edges" | BFS / DP |
| "Count pairs with sum = target" | Hash map or sort + two pointers |
| "Can I partition into K groups with max sum ≤ X?" | Binary search + greedy check |
| "Minimum cost to connect all" | MST (Kruskal/Prim) |

### Interview Application

Build a mental catalog of patterns. When you see a new problem, scan your catalog:

1. What **data structure** is involved? (array, tree, graph, string)
2. What **operation** is requested? (search, count, optimize, construct)
3. What **constraint** is imposed? (time limit, space limit, ordering)
4. Does this **match a known pattern**?

---

## 5. Invariants

### Definition

An invariant is a property that remains true throughout the execution of an algorithm. Invariants provide reasoning anchors — if you can identify and maintain an invariant, correctness follows.

### Real-World Analogy

In a rotating carousel, "every horse is equally spaced from its neighbors" is an invariant. It holds before, during, and after rotation.

### DSA Example

**Partition in quicksort:** After partitioning around pivot `p`, the invariant is: all elements in `[lo, i)` are `≤ p`, and all elements in `(j, hi]` are `≥ p`. The loop maintains this invariant at every iteration.

**Two-pointer technique:** In "container with most water," the invariant is: we've already checked all pairs where the left pointer was further left or the right pointer was further right. So we can safely move the shorter line inward.

```cpp
#include <vector>
#include <algorithm>

int max_area(const std::vector<int>& height) {
    int lo = 0, hi = (int)height.size() - 1;
    int best = 0;
    while (lo < hi) {
        best = std::max(best, std::min(height[lo], height[hi]) * (hi - lo));
        if (height[lo] < height[hi]) ++lo;
        else --hi;
    }
    return best;
}
```

**Invariant:** At each step, we've computed the maximum area for all pairs involving the current `lo` or `hi`. Moving the shorter side inward is safe because any area involving the shorter side and a more inward position would be smaller.

### Interview Application

When writing a loop, explicitly state your invariant:

- "At the start of iteration `i`, `result` contains the answer for the prefix `[0, i)`"
- "After the while loop, `lo` is the first index where `condition` is true"
- "The deque always stores indices in decreasing order of `a[i]`"

Invariants catch bugs *before* you run the code.

---

## 6. State Representation

### Definition

State representation is how you encode the "current situation" of a problem at any point during computation. A good state representation makes the problem solvable; a bad one makes it intractable.

### Real-World Analogy

A chess position can be described by the full board (complex) or by key features: whose turn it is, piece positions, castling rights, en passant square (compact, sufficient). The compact representation enables efficient computation.

### DSA Example

**DP on subsets:** "Given N ≤ 20 cities, find the shortest Hamiltonian path." The state is `(current_city, visited_mask)` where `visited_mask` is a bitmask of visited cities. This has O(N · 2^N) states — feasible for N ≤ 20.

```cpp
#include <vector>
#include <algorithm>
#include <climits>

// TSP with bitmask DP
int tsp(const std::vector<std::vector<int>>& dist) {
    int n = dist.size();
    int FULL = (1 << n) - 1;
    std::vector<std::vector<int>> dp(1 << n, std::vector<int>(n, INT_MAX));
    dp[1][0] = 0; // start at city 0
    for (int mask = 1; mask <= FULL; ++mask) {
        for (int u = 0; u < n; ++u) {
            if (dp[mask][u] == INT_MAX) continue;
            if (!(mask & (1 << u))) continue;
            for (int v = 0; v < n; ++v) {
                if (mask & (1 << v)) continue;
                int nmask = mask | (1 << v);
                dp[nmask][v] = std::min(dp[nmask][v], dp[mask][u] + dist[u][v]);
            }
        }
    }
    int ans = INT_MAX;
    for (int u = 0; u < n; ++u)
        ans = std::min(ans, dp[FULL][u]);
    return ans;
}
```

### Interview Application

Ask yourself: *what do I need to know to make the next decision?* That's your state. Keep it minimal — every extra dimension multiplies the state space.

| Problem Type | Typical State |
|-------------|---------------|
| Knapsack | `(item_index, remaining_capacity)` |
| Grid DP | `(row, col)` or `(row, col, direction)` |
| String DP | `(i, j)` — positions in two strings |
| Graph DP | `(node, remaining_steps)` |
| Bitmask DP | `(current_node, visited_mask)` |

---

## 7. Reduction

### Definition

Reduction is transforming one problem into another problem whose solution you already know. If you can reduce problem A to problem B, then B is at least as hard as A.

### Real-World Analogy

"Finding the cheapest flight route" reduces to "shortest path in a weighted graph." You transform the flight problem into a graph problem, then use Dijkstra.

### DSA Example

**"Find if there exists a pair with difference K in a sorted array"** reduces to **"for each element x, binary search for x+K."** You've reduced a pair-finding problem to repeated binary search.

**Maximum bipartite matching** reduces to **max flow**. You add a source connected to one partition, a sink connected to the other, all edges with capacity 1, and find max flow.

```cpp
// Reduce "count inversions" to "merge sort with counting"
#include <vector>

long long merge_count(std::vector<int>& a, int lo, int hi) {
    if (lo >= hi) return 0;
    int mid = lo + (hi - lo) / 2;
    long long cnt = merge_count(a, lo, mid) + merge_count(a, mid + 1, hi);
    std::vector<int> tmp;
    int i = lo, j = mid + 1;
    while (i <= mid && j <= hi) {
        if (a[i] <= a[j]) {
            tmp.push_back(a[i++]);
        } else {
            tmp.push_back(a[j++]);
            cnt += mid - i + 1; // all remaining in left are > a[j]
        }
    }
    while (i <= mid) tmp.push_back(a[i++]);
    while (j <= hi) tmp.push_back(a[j++]);
    for (int k = 0; k < (int)tmp.size(); ++k)
        a[lo + k] = tmp[k];
    return cnt;
}

long long count_inversions(std::vector<int> a) {
    return merge_count(a, 0, (int)a.size() - 1);
}
```

### Interview Application

When stuck, ask: "Can I transform this into a problem I know how to solve?"

Common reductions:
- **Array problem** → Sort first, then solve
- **Tree problem** → Flatten to array, solve, map back
- **Constraint satisfaction** → 2-SAT, max flow
- **Counting problem** → Inclusion-exclusion or prefix sums
- **Optimization** → Binary search on answer + greedy check

---

## 8. Decision Trees

### Definition

A decision tree models a problem as a series of choices. Each node represents a state, each edge represents a decision, and leaves represent outcomes. Exploring the tree systematically yields the optimal solution.

### Real-World Analogy

A "20 questions" game: each question splits the remaining possibilities. The sequence of yes/no answers traces a path in a binary decision tree.

### DSA Example

**N-Queens:** Place N queens on an N×N board so no two attack each other. The decision tree: at row *r*, try placing a queen in each column *c* that's not attacked. Recurse to row *r+1*.

```cpp
#include <vector>
#include <string>

class NQueens {
    int n;
    std::vector<std::vector<std::string>> solutions;
    std::vector<int> queens; // queens[row] = col

    bool is_safe(int row, int col) {
        for (int r = 0; r < row; ++r) {
            if (queens[r] == col || std::abs(queens[r] - col) == row - r)
                return false;
        }
        return true;
    }

    void solve(int row) {
        if (row == n) {
            std::vector<std::string> board(n, std::string(n, '.'));
            for (int r = 0; r < n; ++r)
                board[r][queens[r]] = 'Q';
            solutions.push_back(board);
            return;
        }
        for (int col = 0; col < n; ++col) {
            if (is_safe(row, col)) {
                queens[row] = col;
                solve(row + 1);
                // backtrack: implicit undo
            }
        }
    }

public:
    std::vector<std::vector<std::string>> solveNQueens(int N) {
        n = N;
        queens.resize(n);
        solve(0);
        return solutions;
    }
};
```

### Interview Application

Decision trees are the basis of **backtracking**. The key optimizations:

- **Pruning:** Skip branches that can't lead to valid solutions
- **Branch and bound:** Skip branches that can't beat the current best
- **Ordering:** Try the most promising branches first

When you see "generate all," "count all," or "find if any valid," think decision tree + backtracking.

---

## 9. Greedy Thinking

### Definition

Greedy thinking means making the locally optimal choice at each step, hoping it leads to a globally optimal solution. A greedy algorithm never reconsiders its choices.

### Real-World Analogy

Dijkstra's algorithm for shortest paths: always visit the closest unvisited node. This greedy choice is provably optimal because all edge weights are non-negative.

### DSA Example

**Activity Selection:** Given activities with start and end times, select the maximum number of non-overlapping activities. Greedy strategy: always pick the activity that ends earliest.

```cpp
#include <vector>
#include <algorithm>

struct Activity { int start, end; };

int max_activities(std::vector<Activity> acts) {
    std::sort(acts.begin(), acts.end(),
              [](const Activity& a, const Activity& b) { return a.end < b.end; });
    int count = 0, last_end = -1;
    for (auto& a : acts) {
        if (a.start >= last_end) {
            ++count;
            last_end = a.end;
        }
    }
    return count;
}
```

**Why it works:** Choosing the earliest-ending activity leaves the maximum room for future activities. This can be proven by an exchange argument.

### Interview Application

Greedy works when:
1. **Greedy choice property:** A locally optimal choice is part of some globally optimal solution
2. **Optimal substructure:** After making a greedy choice, the remaining problem has the same structure

**When greedy fails:** 0/1 Knapsack (greedy by value/weight ratio doesn't work — need DP). Fractional knapsack does work greedily.

**Test your greedy:** Try to prove it by contradiction or exchange argument. If you can't, it's probably wrong — use DP instead.

---

## 10. Recursive Thinking

### Definition

Recursive thinking is solving a problem by assuming you can solve smaller instances of the same problem. You define the relationship between the problem and its subproblems (recurrence), then solve from the base case up.

### Real-World Analogy

Russian nesting dolls: each doll contains a smaller version of itself. To count all dolls, you open one, count it, and count the dolls inside — which is the same problem at a smaller scale.

### DSA Example

**Tree diameter:** The diameter of a tree is the longest path between any two nodes. For each node, the diameter passes through it (using the two longest paths to leaves in different subtrees) or is entirely within one subtree.

```cpp
#include <vector>
#include <algorithm>

class TreeDiameter {
    int ans = 0;
    std::vector<std::vector<int>> adj;

    int dfs(int u, int parent) {
        int best = 0; // longest path from u to a leaf
        for (int v : adj[u]) {
            if (v == parent) continue;
            int depth = dfs(v, u) + 1;
            ans = std::max(ans, best + depth); // path through u
            best = std::max(best, depth);
        }
        return best;
    }

public:
    int diameter(const std::vector<std::vector<int>>& adj_list) {
        adj = adj_list;
        ans = 0;
        if (!adj.empty()) dfs(0, -1);
        return ans;
    }
};
```

### Interview Application

Recursive thinking is the foundation of:
- **Divide and conquer** (merge sort, quicksort)
- **Tree algorithms** (almost all tree problems are recursive)
- **Backtracking** (explore, recurse, undo)
- **DP** (top-down with memoization)

The key insight: *you don't need to solve the whole problem at once. Trust that the recursive call solves the subproblem correctly, then combine.*

---

## 11. Dynamic Programming Mindset

### Definition

Dynamic programming applies when a problem has **overlapping subproblems** (the same subproblem is solved multiple times) and **optimal substructure** (the optimal solution contains optimal solutions to subproblems). DP caches subproblem solutions to avoid redundant computation.

### Real-World Analogy

Climbing stairs: to reach step *n*, you must have come from step *n-1* or *n-2*. The number of ways to reach step *n* is the sum of ways to reach *n-1* and *n-2*. This is the Fibonacci recurrence — and it has overlapping subproblems.

### DSA Example

**Longest Common Subsequence:**

```cpp
#include <vector>
#include <string>
#include <algorithm>

int lcs(const std::string& a, const std::string& b) {
    int m = a.size(), n = b.size();
    std::vector<std::vector<int>> dp(m + 1, std::vector<int>(n + 1, 0));
    for (int i = 1; i <= m; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (a[i-1] == b[j-1])
                dp[i][j] = dp[i-1][j-1] + 1;
            else
                dp[i][j] = std::max(dp[i-1][j], dp[i][j-1]);
        }
    }
    return dp[m][n];
}
```

### Interview Application

**The DP Framework:**

1. **Define state:** What parameters identify a subproblem?
2. **Define transition:** How does the current state depend on previous states?
3. **Base case:** What are the smallest subproblems?
4. **Answer:** Which state represents the full problem?
5. **Order:** What order do we compute states in (top-down or bottom-up)?

| DP Type | State Example | Transition |
|---------|--------------|------------|
| 0/1 Knapsack | `dp[i][w]` = best value using first *i* items with capacity *w* | `max(dp[i-1][w], dp[i-1][w-wi] + vi)` |
| Edit Distance | `dp[i][j]` = distance between `a[0..i)` and `b[0..j)` | `min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)` |
| Coin Change | `dp[v]` = min coins to make value *v* | `min(dp[v-c] + 1)` for each coin *c* |
| LIS | `dp[i]` = length of LIS ending at *i* | `dp[i] = max(dp[j] + 1)` for `j < i, a[j] < a[i]` |

---

## Putting It All Together

Real interview problems rarely require just one thinking mode. Here's how they combine:

**Example: "Minimum cost to hire K workers"**

1. **Abstraction:** Each worker has a wage and quality. Cost = wage-to-quality ratio × sum of qualities.
2. **Modeling:** Sort by ratio. For each ratio as the "captain," find K-1 workers with smallest quality.
3. **Pattern Recognition:** This is "find K smallest" → max-heap of size K.
4. **Greedy Thinking:** Process workers in increasing ratio order.
5. **Invariant:** The heap always contains the K-1 cheapest-quality workers among those processed so far.

---

## Design Decisions: When to Use Each

| Situation | Recommended Thinking Mode |
|-----------|--------------------------|
| Problem seems too complex | Decomposition |
| Problem description is wordy | Abstraction + Modeling |
| You've seen something similar | Pattern Recognition |
| Writing a loop | Invariants |
| Multiple choices at each step | Decision Tree / Backtracking |
| Local choices seem sufficient | Greedy (verify!) |
| Problem has substructure | Recursive Thinking |
| Overlapping subproblems | DP |
| Problem looks like another | Reduction |
| Need to encode "current situation" | State Representation |

## When NOT to Use Greedy

Greedy is tempting but often wrong. **Don't use greedy when:**
- The problem requires looking ahead (e.g., 0/1 Knapsack)
- Local optimal choices conflict with global optimality
- You can't prove the greedy choice property

**Alternatives:** DP (if optimal substructure + overlapping subproblems), backtracking (if you need all solutions), branch and bound (if you need the optimal solution with pruning).

## Trade-offs

| Approach | Time | Space | Correctness Guarantee | Ease of Implementation |
|----------|------|-------|----------------------|----------------------|
| Greedy | Usually O(n log n) | O(1)–O(n) | Needs proof | Easy |
| DP | O(n²)–O(n³) typical | O(n)–O(n²) | Guaranteed if formulation correct | Medium |
| Backtracking | Exponential | O(depth) | Guaranteed | Medium |
| Divide & Conquer | O(n log n) typical | O(n) or O(log n) | Guaranteed | Medium |
| Reduction | Depends on target | Depends | Depends on reduction | Easy once found |

---

## Summary

Computational thinking is the meta-skill that makes you effective at interviews. Technical knowledge tells you *what* tools exist; computational thinking tells you *when and how* to use them. Practice these eleven modes until they become reflexive — when you see a problem, you should instinctively start decomposing, abstracting, and pattern-matching before writing a single line of code.
