# Chapter 97: Pattern Recognition Handbook

## Prerequisites

- All previous chapters

## Interview Frequency: ★★★★★

Pattern recognition is the most important meta-skill for interviews. This chapter provides a systematic guide to identifying which technique to use.

---

## 97.1 Master Decision Flowchart

```
START: Read problem carefully
│
├─ Is input SORTED?
│   ├─ YES → Binary Search, Two Pointers, Merge
│   └─ NO → Can you sort? → Usually yes → Sort first
│
├─ Need SUBARRAY/SUBSTRING (contiguous)?
│   ├─ Fixed size k → Sliding Window
│   ├─ Variable size → Sliding Window or Two Pointers
│   ├─ Maximum/minimum → Kadane's, DP
│   └─ Count with property → Prefix Sum, Sliding Window
│
├─ Need SUBSEQUENCE (not contiguous)?
│   ├─ Longest increasing → Binary Search or DP
│   ├─ Common to two strings → DP (LCS)
│   └─ Count → DP
│
├─ Is it a GRAPH problem?
│   ├─ Shortest path → BFS (unweighted), Dijkstra (weighted)
│   ├─ Connectivity → DFS, Union-Find
│   ├─ Cycle detection → DFS with colors
│   ├─ Ordering → Topological Sort
│   ├─ All paths → Backtracking/DFS
│   └─ Min cut/flow → Max Flow
│
├─ Is it a TREE problem?
│   ├─ Path queries → HLD, LCA
│   ├─ Subtree queries → Euler Tour + Segment Tree
│   ├─ Optimal in subtree → Tree DP
│   └─ Rerooting → Rerooting DP
│
├─ Is it about COUNTING?
│   ├─ With constraints → DP
│   ├─ Combinatorial → nCr, inclusion-exclusion
│   └─ Probability → Expected value DP
│
├─ Is it OPTIMIZATION (min/max)?
│   ├─ Overlapping subproblems → DP
│   ├─ Greedy works → Greedy
│   ├─ Choices at each step → DP
│   └─ Search space monotone → Binary Search on Answer
│
├─ Is n ≤ 20?
│   └─ Bitmask, Backtracking, Meet in the Middle
│
├─ Is n ≤ 500?
│   └─ O(n³) OK: Floyd-Warshall, Matrix Chain
│
├─ Is n ≤ 10^5?
│   └─ O(n log n): Sorting, Segment Tree, Divide & Conquer
│
└─ Is n ≤ 10^7?
    └─ O(n): Linear scan, Hash Map, Two Pointers
```

---

## 97.2 Pattern Quick Reference

### Sliding Window
**Keywords**: "subarray", "substring", "contiguous", "window", "consecutive"
**Recognition**: Need to find/optimize something in a contiguous range

### Two Pointers
**Keywords**: "sorted array", "pair", "triplet", "sum to target"
**Recognition**: Sorted input, looking for pairs/triplets

### Binary Search
**Keywords**: "sorted", "minimum such that", "maximum such that", "first/last"
**Recognition**: Monotonic property, can verify answer

### Dynamic Programming
**Keywords**: "minimum cost", "maximum profit", "number of ways", "count"
**Recognition**: Choices at each step, overlapping subproblems

### Greedy
**Keywords**: "minimum number of", "maximum number of", "interval scheduling"
**Recognition**: Local optimal → global optimal (exchange argument)

### Graph BFS/DFS
**Keywords**: "connected", "shortest path (unweighted)", "reachability"
**Recognition**: Nodes and edges, traversal needed

### Union-Find
**Keywords**: "connected components", "merge", "same group"
**Recognition**: Dynamic connectivity, grouping

### Segment Tree
**Keywords**: "range query", "range update", "interval"
**Recognition**: Queries on ranges of array

### Hash Map
**Keywords**: "frequency", "count", "two sum", "anagram"
**Recognition**: Need O(1) lookup, counting

### Heap
**Keywords**: "top k", "k-th largest/minimum", "median"
**Recognition**: Need extreme values, priority queue

### Monotonic Stack
**Keywords**: "next greater", "next smaller", "histogram"
**Recognition**: Need nearest greater/smaller element

### Backtracking
**Keywords**: "all combinations", "all permutations", "generate all"
**Recognition**: Need all solutions, n ≤ 20

---

## 97.3 Common Disguises

| Looks Like | Actually Is | Technique |
|---|---|---|
| "Minimize max difference" | Binary search on answer | Binary search |
| "Can we split into k groups?" | Binary search on answer | Binary search + greedy check |
| "Number of islands" | Graph connectivity | DFS/BFS/Union-Find |
| "Edit distance" | Two string DP | LCS-like DP |
| "Word break" | String DP | DP + Trie |
| "Meeting rooms" | Interval scheduling | Sort + greedy/sliding window |
| "Top k frequent" | Heap | Min-heap of size k |
| "Serialize tree" | BFS/DFS traversal | Queue/recursion |

---

## 97.4 Constraint → Complexity Guide

| Constraint | Max Complexity | Typical Approach |
|---|---|---|
| n ≤ 10 | O(n!) | Permutation |
| n ≤ 20 | O(2^n) | Bitmask |
| n ≤ 50 | O(n⁴) | 4D DP |
| n ≤ 200 | O(n³) | Floyd, Matrix Chain |
| n ≤ 5000 | O(n²) | Simple DP |
| n ≤ 10^5 | O(n log n) | Sort, Seg Tree |
| n ≤ 10^6 | O(n) | Linear |
| n ≤ 10^7 | O(n) | Careful linear |
| n > 10^7 | O(log n) | Binary search, math |

---

## 97.5 Practice Problems by Pattern

### Sliding Window
1. Maximum average subarray of size k
2. Longest substring without repeating characters
3. Minimum window substring
4. Sliding window maximum

### Two Pointers
1. Two sum (sorted)
2. Three sum
3. Container with most water
4. Trapping rain water

### Binary Search
1. Search in rotated sorted array
2. Find minimum in rotated sorted array
3. Koko eating bananas
4. Capacity to ship packages

### DP
1. Coin change
2. Longest increasing subsequence
3. Edit distance
4. Word break

### Graph
1. Number of islands
2. Course schedule
3. Clone graph
4. Word ladder

---

## 97.6 Implementation Templates

### Sliding Window Template
```cpp
int slidingWindow(vector<int>& nums, int k) {
    int n = nums.size();
    int left = 0, result = 0;
    int windowState = 0; // track window property
    
    for (int right = 0; right < n; right++) {
        // Expand: add nums[right] to window
        windowState += nums[right];
        
        // Shrink: maintain window constraint
        while (/* window invalid */) {
            windowState -= nums[left];
            left++;
        }
        
        // Update answer
        result = max(result, right - left + 1);
    }
    return result;
}
```

### Two Pointers Template
```cpp
int twoPointers(vector<int>& nums, int target) {
    sort(nums.begin(), nums.end());
    int left = 0, right = nums.size() - 1;
    int result = 0;
    
    while (left < right) {
        int sum = nums[left] + nums[right];
        if (sum == target) {
            result++;
            left++; right--;
        } else if (sum < target) {
            left++;
        } else {
            right--;
        }
    }
    return result;
}
```

### Binary Search Template
```cpp
int binarySearch(vector<int>& nums, int target) {
    int lo = 0, hi = nums.size() - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (nums[mid] == target) return mid;
        else if (nums[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

// Binary search on answer
int binarySearchOnAnswer(int lo, int hi) {
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (isFeasible(mid)) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}
```

### DFS/BFS Template
```cpp
void dfs(vector<vector<int>>& graph, int node, vector<bool>& visited) {
    visited[node] = true;
    for (int neighbor : graph[node]) {
        if (!visited[neighbor])
            dfs(graph, neighbor, visited);
    }
}

void bfs(vector<vector<int>>& graph, int start) {
    queue<int> q;
    vector<bool> visited(graph.size(), false);
    q.push(start);
    visited[start] = true;
    while (!q.empty()) {
        int node = q.front(); q.pop();
        for (int neighbor : graph[node]) {
            if (!visited[neighbor]) {
                visited[neighbor] = true;
                q.push(neighbor);
            }
        }
    }
}
```

### DP Template
```cpp
int dp(vector<int>& nums) {
    int n = nums.size();
    vector<int> memo(n, -1);
    
    function<int(int)> solve = [&](int i) -> int {
        if (i >= n) return 0;
        if (memo[i] != -1) return memo[i];
        
        // Choice 1: take nums[i]
        int take = nums[i] + solve(i + 2);
        // Choice 2: skip nums[i]
        int skip = solve(i + 1);
        
        return memo[i] = max(take, skip);
    };
    return solve(0);
}
```

---

## 97.7 Edge Case Checklist

Before submitting, always test these edge cases:

| Category | Edge Cases |
|---|---|
| **Empty input** | n=0, empty string, empty array |
| **Single element** | n=1, array of one element |
| **All same** | All elements identical |
| **Already sorted** | Input is sorted (for sort-based) |
| **Reverse sorted** | Worst case for many algorithms |
| **Negative numbers** | If problem allows negatives |
| **Overflow** | Sum/product exceeds int range → use long |
| **Duplicates** | Array has duplicates (affects two-pointer) |
| **Large input** | Test with n at upper bound |
| **Boundary values** | k=0, k=n, target=0, target=MAX |

---

## 97.8 Anti-Patterns: Common Mistakes

| Mistake | Problem | Fix |
|---|---|---|
| Using DP when greedy works | Unnecessary complexity | Prove greedy choice property first |
| Sorting when order matters | Destroys required ordering | Use a different approach (hash map, etc.) |
| Off-by-one in binary search | Wrong answer on boundaries | Use `lo < hi` with `hi = mid` / `lo = mid + 1` |
| Forgetting to handle duplicates | Wrong count in two-pointer | Skip duplicates after finding a valid pair |
| Using O(n²) when O(n log n) exists | TLE on large inputs | Check if sorting enables a better approach |
| Not considering empty subarray | Wrong answer for all-negative arrays | Clarify: can answer be empty? |
| Integer overflow | Wrong answer on large sums | Use `long long` / `int64_t` |

---

## Summary

| Step | Action |
|---|---|
| 1. Read carefully | Identify input type, constraints, output |
| 2. Check constraints | n → complexity budget |
| 3. Match pattern | Use flowchart above |
| 4. Verify approach | Walk through example |
| 5. Implement | Clean code, handle edge cases |
| 6. Test | Edge cases first |
| 7. Optimize | Space, constant factors |
