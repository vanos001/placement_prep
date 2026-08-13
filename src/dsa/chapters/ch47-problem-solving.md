# Chapter 47: Systematic Problem Solving

## 47.1 The UMPIRE Method

The **UMPIRE method** is a structured framework for solving algorithmic problems, particularly useful in interview settings. It ensures you don't rush into coding before understanding the problem, and it helps you communicate your thought process clearly.

UMPIRE stands for:
- **U**nderstand — Clarify the problem
- **M**atch — Identify the pattern/technique
- **P**lan — Design the solution (pseudocode, edge cases)
- **I**mplement — Write clean code
- **R**eview — Trace through examples, check edge cases
- **E**valuate — Analyze complexity, consider optimizations

### Why UMPIRE Works

Most failed interviews share common causes:
1. Solving the wrong problem (didn't understand)
2. Using the wrong approach (didn't match to known patterns)
3. Bugs in code (didn't plan edge cases)
4. Inefficient solutions (didn't evaluate)

UMPIRE systematically addresses each failure mode.

---

## 47.2 Understanding the Problem

The first and most critical step is **truly understanding** what is being asked. Many candidates jump to coding after hearing the first sentence, only to realize halfway through that they misunderstood the problem.

### Clarifying Questions to Ask

**Input questions:**
- What are the input types? (integers, strings, arrays, trees?)
- What are the constraints? (size limits, value ranges?)
- Can the input be empty? (empty array, empty string?)
- Are there duplicate values?
- Is the input sorted?

**Output questions:**
- What exactly should I return? (value, index, boolean, list?)
- If multiple answers exist, which one? (first, all, any?)
- What format should the output be in?

**Edge case questions:**
- What should I return for empty input?
- What about negative numbers, zero?
- Integer overflow concerns?

### Example: Walking Through the Problem

**Problem**: "Find the longest substring without repeating characters."

**Bad approach**: Immediately think "sliding window" and start coding.

**Good approach (UMPIRE Understand)**:
1. "When you say 'substring,' you mean contiguous, correct?" → Yes.
2. "Is the input always lowercase English letters, or any ASCII/Unicode?" → Let's assume all ASCII.
3. "If the string is empty, should I return 0?" → Yes.
4. "What if all characters are the same, like 'aaaa'?" → Return 1.
5. "Should I return the substring itself or just its length?" → Either works; let's return the length.

### Identifying Constraints

Constraints are **hints** about the expected solution:

| Constraint         | Implied Complexity | Likely Technique      |
|-------------------|--------------------|-----------------------|
| n ≤ 20            | O(2^n)            | Bitmask, backtracking |
| n ≤ 1000          | O(n²) or O(n³)    | DP, BFS               |
| n ≤ 10^5          | O(n log n)        | Sorting, divide & conquer |
| n ≤ 10^6          | O(n) or O(n log n)| Linear scan, hash map |
| n ≤ 10^9          | O(log n) or O(1)  | Binary search, math   |

**Rule of thumb**: The time limit is usually ~1 second, which allows ~10^8 operations. Divide the constraint by 10^8 to get the maximum acceptable complexity.

---

## 47.3 Matching to Patterns

Once you understand the problem, the next step is recognizing **which algorithmic pattern** applies. This is where studying data structures and algorithms pays off.

### The Pattern Recognition Guide

**Array/String problems:**
- "Subarray with sum = k" → Prefix sum + hash map
- "Longest substring with condition" → Sliding window
- "Two elements with property" → Two pointers or hash map
- "Sorted array, find element" → Binary search
- "Top k elements" → Heap or quickselect

**Tree problems:**
- "Path from root to leaf" → DFS
- "Level-by-level processing" → BFS
- "Lowest common ancestor" → Binary lifting or Euler tour
- "Serialize/deserialize" → Preorder traversal

**Graph problems:**
- "Shortest path (unweighted)" → BFS
- "Shortest path (weighted, non-negative)" → Dijkstra
- "Shortest path (negative weights)" → Bellman-Ford
- "Connected components" → DFS or Union-Find
- "Topological ordering" → Kahn's algorithm or DFS
- "Minimum spanning tree" → Kruskal or Prim

**Dynamic programming:**
- "Optimal value/maximize/minimize" → DP
- "Count ways" → DP
- "Is it possible" → DP or greedy
- "Overlapping subproblems" → DP (memoization or tabulation)

**String problems:**
- "Pattern matching" → KMP, Rabin-Karp
- "Multiple patterns" → Aho-Corasick
- "All suffixes" → Suffix array or suffix automaton
- "Edit distance" → DP

### Decision Flowchart

```
START: What type of problem?
│
├── Optimization (min/max)?
│   ├── Overlapping subproblems? → Dynamic Programming
│   ├── Greedy choice property? → Greedy Algorithm
│   └── Search space monotonic? → Binary Search on Answer
│
├── Counting (how many ways)?
│   ├── Combinatorial? → Math (nCr, Catalan, etc.)
│   ├── Sequential choices? → DP
│   └── Independent choices? → Multiply counts
│
├── Existence (is it possible)?
│   ├── Graph connectivity? → BFS/DFS/Union-Find
│   ├── Satisfiability? → 2-SAT, backtracking
│   └── Sequence property? → Greedy or DP
│
├── Search (find element/position)?
│   ├── Sorted? → Binary Search
│   ├── Graph? → BFS/DFS/Dijkstra
│   └── Hash-able? → Hash Map
│
├── String problems?
│   ├── Single pattern? → KMP / Rabin-Karp
│   ├── Multiple patterns? → Aho-Corasick
│   ├── Substring queries? → Suffix Array / Suffix Automaton
│   └── Palindromes? → Manacher's / DP
│
└── Range queries?
    ├── Point update, range query? → Fenwick / Segment Tree
    ├── Range update, point query? → Difference Array / Lazy Prop
    └── Offline queries? → Mo's Algorithm / CDQ
```

### Example: Matching a Problem to a Pattern

**Problem**: "Given an array of integers, find the length of the longest increasing subsequence."

**Matching process:**
1. "Optimization? Yes — maximize length."
2. "Overlapping subproblems? Yes — LIS ending at position i depends on LIS ending at earlier positions."
3. "DP applies. But n ≤ 10^5, so O(n²) DP is too slow."
4. "Alternative: patience sorting / binary search approach → O(n log n)."

---

## 47.4 Planning the Solution

Before writing code, **plan** the solution. This saves time and prevents bugs.

### Step 1: Write Pseudocode

Pseudocode captures the algorithm's logic without worrying about syntax:

```
function longestIncreasingSubsequence(arr):
    n = length(arr)
    tails = empty array  // tails[i] = smallest tail element of LIS of length i+1
    
    for each element x in arr:
        pos = binary_search_leftmost(tails, x)
        if pos == length(tails):
            tails.append(x)
        else:
            tails[pos] = x
    
    return length(tails)
```

### Step 2: Identify Edge Cases

Always consider these categories:

**Empty/null input:**
- Empty array: return 0 or empty result?
- Null pointer: should we handle it?

**Single element:**
- Array of size 1: is the answer trivially correct?

**Boundary values:**
- Integer overflow: use `long long`?
- Negative numbers: does the algorithm handle them?
- Maximum/minimum values: INT_MAX, INT_MIN?

**Special structures:**
- Already sorted array
- Reverse sorted array
- All same elements
- Binary tree is a linked list (all left children)

### Step 3: Complexity Budget

Before coding, confirm the complexity fits:

```
Given: n ≤ 10^5
Available: ~10^8 operations
Budget: O(n log n) ≈ 10^5 × 17 ≈ 1.7 × 10^6 ✓
O(n²) ≈ 10^10 ✗ (too slow)
```

### Example: Planning for "Two Sum"

**Problem**: Given a sorted array and a target, find two indices whose values sum to the target.

**Pseudocode**:
```
function twoSum(arr, target):
    left = 0
    right = length(arr) - 1
    
    while left < right:
        currentSum = arr[left] + arr[right]
        if currentSum == target:
            return [left, right]
        else if currentSum < target:
            left++
        else:
            right--
    
    return [-1, -1]  // No solution
```

**Edge cases**:
- Array has fewer than 2 elements → return [-1, -1]
- No valid pair exists → return [-1, -1]
- Duplicate values → algorithm still works (two pointers don't skip)
- Negative numbers → algorithm still works (sorted property preserved)

**Complexity**: O(n) time, O(1) space. Fits budget.

---

## 47.5 Implementing

### Clean Code Principles

**1. Meaningful Names**

```cpp
// Bad
int f(vector<int>& a) {
    int r = 0;
    for (int i = 0; i < a.size(); i++)
        r = max(r, a[i]);
    return r;
}

// Good
int findMaximum(vector<int>& numbers) {
    int maxVal = 0;
    for (int i = 0; i < numbers.size(); i++)
        maxVal = max(maxVal, numbers[i]);
    return maxVal;
}
```

**2. Small Functions**

Break complex logic into helper functions:

```cpp
// Main function
int solve(vector<int>& nums, int target) {
    sort(nums.begin(), nums.end());
    return twoSumSorted(nums, target);
}

// Helper
int twoSumSorted(vector<int>& sorted, int target) {
    int left = 0, right = sorted.size() - 1;
    while (left < right) {
        int sum = sorted[left] + sorted[right];
        if (sum == target) return 1;
        if (sum < target) left++;
        else right--;
    }
    return 0;
}
```

**3. Constants Over Magic Numbers**

```cpp
// Bad
if (n > 1000000) return -1;

// Good
const int MAX_N = 1000000;
if (n > MAX_N) return -1;
```

**4. Consistent Style**

- Choose one naming convention and stick with it.
- Use consistent indentation (4 spaces or tabs, not both).
- Put opening braces on the same line or next line, but be consistent.

### Common Implementation Patterns

**Binary Search**:
```cpp
int binarySearch(vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;  // Avoid overflow
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
```

**Sliding Window**:
```cpp
int slidingWindow(string s) {
    unordered_map<char, int> window;
    int left = 0, result = 0;
    
    for (int right = 0; right < s.size(); right++) {
        window[s[right]]++;
        
        while (/* window invalid */) {
            window[s[left]]--;
            left++;
        }
        
        result = max(result, right - left + 1);
    }
    return result;
}
```

**BFS Template**:
```cpp
int bfs(vector<vector<int>>& graph, int start, int target) {
    queue<int> q;
    unordered_set<int> visited;
    q.push(start);
    visited.insert(start);
    int steps = 0;
    
    while (!q.empty()) {
        int sz = q.size();
        for (int i = 0; i < sz; i++) {
            int node = q.front(); q.pop();
            if (node == target) return steps;
            for (int neighbor : graph[node]) {
                if (!visited.count(neighbor)) {
                    visited.insert(neighbor);
                    q.push(neighbor);
                }
            }
        }
        steps++;
    }
    return -1;
}
```

---

## 47.6 Reviewing

After implementing, **always review** your code before declaring it done.

### Trace Through Examples

Walk through the code line by line with the given example:

**Problem**: Two Sum, `arr = [2, 7, 11, 15]`, `target = 9`

```
Initial: left = 0, right = 3

Iteration 1:
  sum = arr[0] + arr[3] = 2 + 15 = 17
  17 > 9 → right = 2

Iteration 2:
  sum = arr[0] + arr[2] = 2 + 11 = 13
  13 > 9 → right = 1

Iteration 3:
  sum = arr[0] + arr[1] = 2 + 7 = 9
  9 == 9 → return [0, 1] ✓
```

### Check Edge Cases

1. **Empty array**: `arr = []` → `left = 0, right = -1` → loop doesn't execute → return [-1, -1] ✓
2. **No solution**: `arr = [1, 2, 3]`, `target = 100` → loop exhausts → return [-1, -1] ✓
3. **Negative numbers**: `arr = [-3, -1, 0, 2]`, `target = -1` → works correctly ✓
4. **Same elements**: `arr = [3, 3]`, `target = 6` → returns [0, 1] ✓

### Common Review Checklist

- [ ] Does the code handle empty input?
- [ ] Are all variables initialized?
- [ ] Are there off-by-one errors? (Check loop bounds, array indices)
- [ ] Is there integer overflow? (Use `long long` if needed)
- [ ] Does the code handle negative numbers?
- [ ] Are all return paths correct?
- [ ] Is the code consistent with the pseudocode?

---

## 47.7 Evaluating

The final step is to **evaluate** your solution's efficiency and consider alternatives.

### Complexity Analysis

Always state both time and space complexity:

```
Time: O(n log n) — sorting takes O(n log n), two pointers scan takes O(n)
Space: O(1) — only two pointer variables (excluding input)
```

### Comparison with Alternatives

| Approach              | Time      | Space | Notes                        |
|----------------------|-----------|-------|------------------------------|
| Brute force          | O(n²)    | O(1)  | Check all pairs              |
| Hash map             | O(n)     | O(n)  | Extra space for the map      |
| Two pointers (sorted)| O(n log n)| O(1) | Sort first, then linear scan |

### When to Optimize

1. **If your solution meets the constraints**: Don't over-optimize. State that it's sufficient.
2. **If it's borderline**: Mention the optimization possibility but don't implement unless asked.
3. **If it's too slow**: Go back to the matching step and try a different approach.

### What-If Scenarios

Interviewers often ask follow-up questions. Be prepared:

- "What if the array isn't sorted?" → Use hash map approach, O(n) time, O(n) space.
- "What if there are multiple answers?" → Return all pairs, modify the two-pointer loop.
- "What if the array has duplicates?" → The algorithm still works; skip duplicates if unique pairs are needed.
- "What about integer overflow?" → Use `long long` for sums.

---

## Putting It All Together: Complete Example

**Problem**: "Given an array of integers, find the contiguous subarray with the largest sum."

### U - Understand
- "Contiguous subarray" — not subsequence, must be consecutive elements.
- "Largest sum" — maximize the sum.
- "Can the array be all negative?" → Yes, return the least negative.
- "Can the array be empty?" → Assume non-empty.

### M - Match
- "Maximum over contiguous subarrays" → This is Kadane's algorithm (DP / greedy).

### P - Plan
```
function maxSubarraySum(arr):
    maxSoFar = arr[0]
    maxEndingHere = arr[0]
    
    for i = 1 to n-1:
        maxEndingHere = max(arr[i], maxEndingHere + arr[i])
        maxSoFar = max(maxSoFar, maxEndingHere)
    
    return maxSoFar
```

Edge cases: All negative numbers, single element, all positive.
Complexity: O(n) time, O(1) space. ✓

### I - Implement

```cpp
#include <bits/stdc++.h>
using namespace std;

int maxSubarraySum(vector<int>& arr) {
    int maxSoFar = arr[0];
    int maxEndingHere = arr[0];
    
    for (int i = 1; i < (int)arr.size(); i++) {
        maxEndingHere = max(arr[i], maxEndingHere + arr[i]);
        maxSoFar = max(maxSoFar, maxEndingHere);
    }
    
    return maxSoFar;
}

int main() {
    vector<int> arr = {-2, 1, -3, 4, -1, 2, 1, -5, 4};
    cout << "Maximum subarray sum: " << maxSubarraySum(arr) << "\n";
    // Output: 6 (subarray [4, -1, 2, 1])
    return 0;
}
```

### R - Review
- Dry run: `[-2, 1, -3, 4, -1, 2, 1, -5, 4]`
  - i=0: maxSoFar=-2, maxEnd=-2
  - i=1: maxEnd=max(1, -2+1)=1, maxSoFar=1
  - i=2: maxEnd=max(-3, 1-3)=-2, maxSoFar=1
  - i=3: maxEnd=max(4, -2+4)=4, maxSoFar=4
  - i=4: maxEnd=max(-1, 4-1)=3, maxSoFar=4
  - i=5: maxEnd=max(2, 3+2)=5, maxSoFar=5
  - i=6: maxEnd=max(1, 5+1)=6, maxSoFar=6
  - i=7: maxEnd=max(-5, 6-5)=1, maxSoFar=6
  - i=8: maxEnd=max(4, 1+4)=5, maxSoFar=6
  - Result: 6 ✓
- Edge case: All negative `[-3, -1, -2]` → maxSoFar = -1 ✓

### E - Evaluate
- Time: O(n) — single pass through the array.
- Space: O(1) — only two variables.
- Alternative: Divide and conquer approach, O(n log n) — less efficient but good to know.

---

## Interview Tips

1. **Don't start coding immediately.** Spend 2-3 minutes understanding the problem and planning. This saves 10+ minutes of debugging.

2. **Think out loud.** Interviewers want to hear your thought process. Say things like "I'm considering a sliding window approach because..." or "The constraint suggests O(n log n) is acceptable."

3. **Start with brute force.** It's better to have a working O(n²) solution than a broken O(n) solution. Optimize from there.

4. **Test with examples.** Before saying "I'm done," trace through at least one example by hand.

5. **Know your complexity.** Be able to explain why your solution is O(n log n) and not O(n²). The interviewer will ask.

## Common Mistakes

1. **Solving the wrong problem.** Misunderstanding "subarray" vs "subsequence" is the #1 mistake.

2. **Ignoring edge cases.** Empty input, single element, all negative numbers, overflow.

3. **Over-engineering.** Don't use a segment tree when a simple loop suffices.

4. **Not testing before saying "done."** Always trace through at least one example.

5. **Giving up too early.** If stuck, try a brute force approach first, then optimize.

## Practice Problems

1. **LeetCode 1** — Two Sum. (Hint: Hash map for O(n) solution.)

2. **LeetCode 53** — Maximum Subarray. (Hint: Kadane's algorithm.)

3. **LeetCode 15** — 3Sum. (Hint: Sort + two pointers.)

4. **LeetCode 3** — Longest Substring Without Repeating Characters. (Hint: Sliding window with hash set.)

5. **LeetCode 200** — Number of Islands. (Hint: BFS/DFS on grid.)

6. **LeetCode 322** — Coin Change. (Hint: DP, dp[i] = min coins for amount i.)

7. **LeetCode 236** — Lowest Common Ancestor. (Hint: Recursive DFS, check left/right subtrees.)
