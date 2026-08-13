# Chapter 50: Mock Interviews and Final Revision

## 50.1 Mock Interview Framework

Mock interviews are the most effective way to prepare for technical interviews. They simulate the real experience — time pressure, thinking aloud, coding on a whiteboard, and handling follow-up questions.

### How to Conduct Mock Interviews

**With a Partner (Recommended)**

The ideal mock interview has three roles:
1. **Interviewer**: Asks the question, provides hints, evaluates
2. **Candidate**: Solves the problem under time constraints
3. **Observer** (optional): Takes notes on both parties

**Setup**:
- Choose a problem neither person has solved recently
- Set a timer for 45 minutes
- Use a whiteboard or paper (not an IDE)
- The interviewer should act as a real interviewer: ask clarifying questions, give hints if stuck, ask follow-ups

**The Interviewer's Checklist**:
- [ ] Did the candidate understand the problem before coding?
- [ ] Did they consider multiple approaches?
- [ ] Did they analyze time/space complexity?
- [ ] Was their code clean and correct?
- [ ] Did they test their solution?
- [ ] How did they handle hints?
- [ ] How did they handle follow-up questions?

**Alone (When No Partner Available)**

You can simulate mock interviews alone, though it's less effective:

1. **Use a timer**: 45 minutes per problem, no extensions.
2. **Use a whiteboard or paper**: Don't type — write by hand.
3. **Talk out loud**: Narrate your thought process as if someone is listening.
4. **Don't look at solutions**: Once you start, don't peek. If you get stuck, that's valuable information.
5. **Review afterward**: Compare your solution to the optimal one. What did you miss?

**Online Platforms for Mock Interviews**:
- **Pramp**: Free peer-to-peer mock interviews
- **Interviewing.io**: Anonymous mock interviews with engineers from top companies
- **LeetCode Mock Interview**: Timed problem sets that simulate interview conditions

### Mock Interview Problem Selection

**For a 45-minute mock interview, choose problems that are**:
- Medium difficulty (Hard problems often require 45+ minutes)
- From a variety of topics (don't do 5 DP problems in a row)
- Realistic for the company you're targeting

**Sample Mock Interview Schedule** (8 weeks):

| Week | Focus Area              | Problems                              |
|------|-------------------------|---------------------------------------|
| 1    | Arrays & Strings        | Two Sum, Longest Substring, 3Sum      |
| 2    | Linked Lists & Stacks   | Reverse List, Valid Parentheses       |
| 3    | Trees & Graphs          | BFS/DFS, LCA, Number of Islands       |
| 4    | Binary Search & Sorting | Search Rotated Array, Merge Intervals |
| 5    | Dynamic Programming     | Coin Change, LIS, Edit Distance       |
| 6    | Advanced Topics         | Trie, Union-Find, Segment Tree        |
| 7    | Mixed Problems          | Random selection from all categories   |
| 8    | Company-Specific        | Problems from target company           |

---

## 50.2 Debugging Strategies

### Systematic Debugging

When your code doesn't work, don't randomly change things. Follow a systematic process:

**Step 1: Reproduce the bug**
- Find a small input that triggers the bug.
- If the input is large, try to reduce it while keeping the bug.

**Step 2: Understand the expected vs actual behavior**
- What should the output be?
- What is the actual output?
- Where do they diverge?

**Step 3: Binary search the code**
- Add print statements at the midpoint of your algorithm.
- Check: is the state correct at this point?
- If correct, the bug is in the second half. If wrong, it's in the first half.
- Repeat until you find the exact line.

**Step 4: Fix and verify**
- Fix the bug.
- Test with the original failing input.
- Test with edge cases.

### Print Debugging

Print debugging is the most practical debugging technique in interviews. Here's how to do it effectively:

```cpp
// Debug macro (remove before submission)
#define DEBUG 1
#if DEBUG
#define dbg(x) cerr << #x << " = " << (x) << endl;
#define dbg2(x, y) cerr << #x << " = " << (x) << ", " << #y << " = " << (y) << endl;
#define dbgVec(v) cerr << #v << ": "; for (auto& x : v) cerr << x << " "; cerr << endl;
#else
#define dbg(x)
#define dbg2(x, y)
#define dbgVec(v)
#endif

// Usage in code:
vector<int> twoSum(vector<int>& arr, int target) {
    int left = 0, right = arr.size() - 1;
    while (left < right) {
        int sum = arr[left] + arr[right];
        dbg2(left, right);
        dbg(sum);
        if (sum == target) return {left, right};
        if (sum < target) left++;
        else right--;
    }
    return {-1, -1};
}
```

### What to Print

**For loops**: Print loop variables and key state at each iteration.
```cpp
for (int i = 0; i < n; i++) {
    // ... computation ...
    cerr << "i=" << i << " dp[i]=" << dp[i] << endl;
}
```

**For recursion**: Print entry/exit and parameters.
```cpp
int dfs(int node, int parent) {
    cerr << "dfs(" << node << ", " << parent << ")" << endl;
    // ... recursion ...
    cerr << "dfs(" << node << ") = " << result << endl;
    return result;
}
```

**For data structures**: Print the contents of arrays, maps, etc.
```cpp
// Print vector
for (int i = 0; i < n; i++) cerr << arr[i] << " \n"[i == n-1];

// Print map
for (auto& [k, v] : mp) cerr << k << ":" << v << " ";
cerr << endl;
```

### Boundary Testing

Test your code with these boundary inputs:

**Numerical boundaries**:
- 0, 1, -1
- INT_MAX, INT_MIN
- n = 0 (empty input)
- n = 1 (single element)

**Array boundaries**:
- Empty array
- Single element
- Two elements
- All same elements
- Already sorted
- Reverse sorted
- All negative
- All positive
- Mixed positive and negative

**String boundaries**:
- Empty string
- Single character
- All same character
- Longest possible input

**Tree boundaries**:
- Empty tree (null root)
- Single node
- Linear tree (all left children or all right children)
- Perfect binary tree

**Graph boundaries**:
- Single node, no edges
- Disconnected components
- Self-loops (if allowed)
- Cycles

---

## 50.3 Time Management

### How to Allocate Time in a 45-Minute Interview

A typical 45-minute technical interview breaks down as:

| Phase              | Time      | What to Do                                    |
|-------------------|-----------|-----------------------------------------------|
| Understand         | 3-5 min   | Clarify problem, ask questions                |
| Plan               | 5-7 min   | Discuss approaches, analyze complexity        |
| Implement          | 15-20 min | Write code on whiteboard                      |
| Test               | 5-10 min  | Trace through examples, check edge cases      |
| Follow-up          | 5-10 min  | Discuss optimizations, answer questions       |

### Time Management Tips

**1. Set checkpoints**
- At 10 minutes: Should have a clear plan.
- At 25 minutes: Should have working code.
- At 35 minutes: Should have tested the code.
- At 40 minutes: Should be discussing optimizations or follow-ups.

**2. Don't get stuck on one part**
If you've spent 5 minutes on a single line of code, you're probably overthinking it. Move on and come back.

**3. Start with brute force**
If you can't think of an optimal solution, implement brute force first. It's better to have a working O(n²) solution than a broken O(n) solution.

**4. Optimize after implementing**
Get the brute force working, then optimize. Don't try to write the optimal solution directly — it's riskier.

**5. Know when to stop optimizing**
If your solution meets the constraints and the interviewer seems satisfied, don't keep optimizing. Move on to testing or follow-ups.

### What to Do When Running Out of Time

**If you haven't finished coding (5 minutes left)**:
- Don't rush — messy code is worse than incomplete but clean code.
- Explain what the remaining parts would do.
- "I would add error handling here, and the base case for the recursion would return..."

**If you haven't tested (3 minutes left)**:
- Trace through ONE example quickly.
- "Let me verify with the example: input [1,2,3], target 5. We start with left=0, right=2..."

**If you haven't discussed complexity (1 minute left)**:
- State it quickly: "Time complexity is O(n log n) due to the sort, space is O(1)."

---

## 50.4 How Interviewers Evaluate

### What Interviewers Look For

Most tech companies evaluate candidates on 4 dimensions:

**1. Problem Solving (30-35%)**
- Do you understand the problem?
- Can you identify the right approach?
- Do you consider multiple solutions?
- Can you analyze complexity?
- How do you handle getting stuck?

**2. Coding (30-35%)**
- Is your code correct?
- Is it clean and readable?
- Do you use meaningful variable names?
- Is it free of bugs?
- Does it handle edge cases?

**3. Communication (15-20%)**
- Do you explain your thought process?
- Do you ask clarifying questions?
- Can you articulate trade-offs?
- Do you respond well to hints?
- Are you easy to work with?

**4. Testing (10-15%)**
- Do you test your code?
- Do you consider edge cases?
- Can you identify bugs in your own code?
- Do you verify with examples?

### The Evaluation Rubric

Most interviewers use a rubric like this:

| Rating        | Problem Solving                           | Coding                              |
|--------------|-------------------------------------------|-------------------------------------|
| Strong Hire  | Optimal solution with clear reasoning     | Clean, bug-free code                |
| Hire         | Optimal solution with some guidance       | Minor bugs, fixable quickly         |
| Lean Hire    | Suboptimal solution, but good process     | Several bugs, but correct structure |
| Lean No Hire | Struggled significantly, needed heavy help| Many bugs, hard to fix              |
| No Hire      | Couldn't solve the problem                | Code is fundamentally broken        |

### What Separates "Hire" from "Strong Hire"

**Hire**: Gets the right answer with some hints.
**Strong Hire**: Gets the right answer independently, explains the reasoning clearly, considers alternatives, tests thoroughly, and handles follow-ups with ease.

The difference is often **polish** — the strong hire has practiced enough that the entire process feels natural and confident.

---

## 50.5 Recovering from Mistakes

### What to Do When Stuck

**1. Don't panic**
Being stuck is normal. Interviewers expect it. Take a breath and think systematically.

**2. Go back to examples**
If you're stuck on the algorithm, trace through the example by hand. Often, the pattern becomes apparent when you see the steps.

**3. Try a different approach**
If your current approach isn't working, try something different. "I've been trying a greedy approach, but I'm not sure it works for all cases. Let me consider dynamic programming instead."

**4. Ask for a hint**
It's better to ask for a hint than to sit in silence for 10 minutes. "I'm stuck on how to handle the case where the tree is unbalanced. Can you give me a hint?"

**5. Simplify the problem**
Can you solve a simpler version first? "Let me start with the case where all numbers are positive. Then I'll extend to handle negatives."

### What to Do When Your Solution Is Wrong

**1. Don't argue with the interviewer**
If they say your solution is wrong, it probably is. Don't defend it — investigate it.

**2. Find the bug**
"Let me trace through the example again... Ah, I see — when the array has duplicates, my two-pointer approach skips the correct answer."

**3. Fix it**
"I need to add a check for duplicates. After finding a valid pair, I'll skip all subsequent elements that are the same."

**4. Learn from it**
"This is a good reminder to always test with duplicate values. I'll add that to my edge case checklist."

### What to Do When You Realize Your Approach Is Wrong Midway

**1. Acknowledge it**
"I just realized my greedy approach doesn't work for this case. The greedy choice of always picking the largest element doesn't lead to the optimal solution."

**2. Pivot gracefully**
"Let me switch to dynamic programming. I'll define dp[i] as the maximum sum ending at index i."

**3. Don't start from scratch**
Reuse as much of your existing work as possible. The variable names, the loop structure, the edge case handling — much of it carries over.

**4. Manage time**
If you're running low on time, explain the new approach without fully implementing it. "I would implement this as a bottom-up DP with a 1D array. The recurrence is dp[i] = max(dp[i-1] + arr[i], arr[i])."

### What to Do When You Make a Syntax Error

**1. Don't apologize profusely**
A quick "sorry, let me fix that" is enough.

**2. Fix it calmly**
Cross out the error, write the correction. Don't try to erase — it wastes time and makes a mess.

**3. Move on**
Don't dwell on syntax errors. Interviewers care about logic, not semicolons.

---

## 50.6 Final Revision Checklist

### Key Algorithms to Review

**Sorting**:
- [ ] Merge Sort — O(n log n), stable, divide & conquer
- [ ] Quick Sort — O(n log n) average, O(n²) worst, in-place
- [ ] Heap Sort — O(n log n), in-place, not stable
- [ ] Counting Sort — O(n + k), non-comparison, for integers in range

**Searching**:
- [ ] Binary Search — O(log n), works on sorted arrays
- [ ] BFS — O(V + E), shortest path in unweighted graphs
- [ ] DFS — O(V + E), cycle detection, topological sort
- [ ] Dijkstra — O((V + E) log V), shortest path with non-negative weights

**Dynamic Programming**:
- [ ] 1D DP — Fibonacci, climbing stairs, house robber
- [ ] 2D DP — Edit distance, LCS, knapsack
- [ ] Interval DP — Matrix chain multiplication, burst balloons
- [ ] Bitmask DP — TSP, assignment problem
- [ ] DP on trees — Diameter, tree knapsack

**Graph**:
- [ ] Union-Find — O(α(n)) per operation, connected components
- [ ] Topological Sort — Kahn's algorithm (BFS) or DFS
- [ ] Kruskal's/Prim's — Minimum spanning tree
- [ ] Bellman-Ford — Shortest path with negative weights
- [ ] Floyd-Warshall — All-pairs shortest path

**String**:
- [ ] KMP — O(n + m) pattern matching
- [ ] Rabin-Karp — O(n + m) average, rolling hash
- [ ] Trie — O(m) insert/search, prefix matching
- [ ] Suffix Array — O(n log²n) construction, LCP array
- [ ] Aho-Corasick — O(n + m + z) multi-pattern matching

### Key Data Structures to Review

- [ ] Hash Map — O(1) average insert/delete/lookup
- [ ] Stack — LIFO, monotonic stack for next greater/smaller element
- [ ] Queue — FIFO, deque for sliding window
- [ ] Heap (Priority Queue) — O(log n) insert/extract, top-k problems
- [ ] Binary Search Tree — O(log n) average operations
- [ ] Segment Tree — O(log n) range queries and updates
- [ ] Fenwick Tree (BIT) — O(log n) prefix sum queries
- [ ] Trie — O(m) prefix operations

### Key Patterns to Review

- [ ] Two Pointers — Sorted array problems, palindromes
- [ ] Sliding Window — Subarray problems with constraints
- [ ] Fast & Slow Pointers — Cycle detection, middle of list
- [ ] Merge Intervals — Overlapping intervals
- [ ] Cyclic Sort — Find missing/duplicate in 1..n
- [ ] Top K Elements — Heap-based selection
- [ ] K-way Merge — Merge k sorted lists
- [ ] Subset/Permutation — Backtracking templates
- [ ] Binary Search on Answer — Optimization with monotonic property
- [ ] Monotonic Stack — Next greater element, histogram problems

### Common Mistakes to Avoid in Interviews

1. **Off-by-one errors**: Check `<` vs `<=`, `n-1` vs `n`.
2. **Integer overflow**: Use `long long` for sums and products.
3. **Uninitialized variables**: Always initialize before use.
4. **Null pointer dereference**: Check for null before accessing.
5. **Infinite loops**: Ensure loop termination conditions are correct.
6. **Not handling empty input**: Check for empty arrays, strings, trees.
7. **Modifying input when you shouldn't**: Make a copy if needed.
8. **Forgetting to update state**: In DP, make sure to update the DP table.
9. **Wrong base case**: In recursion/DP, verify base cases with examples.
10. **Not testing before saying "done"**: Always trace through at least one example.

### Day-of-Interview Checklist

**Before the interview**:
- [ ] Get a good night's sleep
- [ ] Eat a light meal
- [ ] Review your story bank (for behavioral questions)
- [ ] Glance at your algorithm cheat sheet (don't cram)
- [ ] Test your equipment (if remote interview)
- [ ] Have paper and pen ready

**During the interview**:
- [ ] Listen carefully to the problem
- [ ] Ask clarifying questions
- [ ] Think before coding
- [ ] Explain your approach
- [ ] Code cleanly
- [ ] Test your solution
- [ ] Discuss complexity
- [ ] Ask thoughtful questions at the end

**After the interview**:
- [ ] Write down what went well and what didn't
- [ ] Note any problems you struggled with for later review
- [ ] Send a thank-you email (if appropriate)
- [ ] Take a break before the next round

### The Night Before: What to Review

Don't try to learn new material the night before. Instead:
1. **Review your solved problems** — skim through your notes on problems you've solved.
2. **Review templates** — BFS, DFS, binary search, DP, etc.
3. **Review your stories** — Make sure your behavioral answers are fresh.
4. **Relax** — Confidence comes from preparation, not last-minute cramming.

---

## Putting It All Together: A Complete Mock Interview

**Problem**: "Given a binary tree, return the level order traversal of its nodes' values."

**Time**: 45 minutes

**Minute 0-3: Understand**
"Level order traversal means visiting nodes level by level, left to right. So for this tree:
```
    3
   / \
  9  20
    /  \
   15   7
```
The output would be [[3], [9, 20], [15, 7]]."

**Minute 3-7: Plan**
"I'll use BFS with a queue. Process nodes level by level: for each level, record the queue size, process that many nodes, and collect their values. This is O(n) time and O(n) space."

**Minute 7-25: Implement**

```cpp
#include <bits/stdc++.h>
using namespace std;

struct TreeNode {
    int val;
    TreeNode *left, *right;
    TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

vector<vector<int>> levelOrder(TreeNode* root) {
    vector<vector<int>> result;
    if (!root) return result;

    queue<TreeNode*> q;
    q.push(root);

    while (!q.empty()) {
        int levelSize = q.size();
        vector<int> currentLevel;

        for (int i = 0; i < levelSize; i++) {
            TreeNode* node = q.front(); q.pop();
            currentLevel.push_back(node->val);
            if (node->left) q.push(node->left);
            if (node->right) q.push(node->right);
        }

        result.push_back(currentLevel);
    }

    return result;
}
```

**Minute 25-35: Test**
"Let me trace through the example:
- Start: q = [3]
- Level 0: levelSize=1, process 3, add 9 and 20. result = [[3]]
- Level 1: levelSize=2, process 9 (no children), process 20 (add 15, 7). result = [[3], [9, 20]]
- Level 2: levelSize=2, process 15 (no children), process 7 (no children). result = [[3], [9, 20], [15, 7]]
- Queue empty, done. ✓

Edge cases:
- Empty tree: returns empty vector ✓
- Single node: returns [[root->val]] ✓"

**Minute 35-40: Complexity**
"Time: O(n) — each node is visited once.
Space: O(n) — the queue holds at most one level, which is at most n/2 nodes."

**Minute 40-45: Follow-up**
"If asked for reverse level order: same approach, but reverse the result at the end.
If asked for zigzag level order: alternate the direction of insertion for each level."

---

## Interview Tips

1. **Practice under realistic conditions**. Use a timer, write by hand, talk out loud.

2. **Review your mistakes**. After every practice session, note what went wrong and how to improve.

3. **Don't memorize solutions**. Understand the patterns and apply them to new problems.

4. **Stay calm**. If you're stuck, take a breath and think systematically. The interviewer is rooting for you.

5. **Be yourself**. Authenticity beats perfection. Interviewers want to see how you think, not how well you memorized.

## Common Mistakes

1. **Not practicing enough**. Reading about algorithms is not the same as solving problems.

2. **Only practicing easy problems**. You need to be comfortable with medium-difficulty problems.

3. **Not practicing under time pressure**. A 2-hour solution is useless in a 45-minute interview.

4. **Ignoring behavioral questions**. Many candidates focus entirely on technical and bomb the behavioral.

5. **Not getting feedback**. Practice with others and ask for honest feedback.

## Practice Problems for Final Review

1. **LeetCode 146** — LRU Cache. (Hint: Hash map + doubly linked list.)

2. **LeetCode 23** — Merge k Sorted Lists. (Hint: Min-heap of size k.)

3. **LeetCode 42** — Trapping Rain Water. (Hint: Two pointers or precompute max heights.)

4. **LeetCode 124** — Binary Tree Maximum Path Sum. (Hint: Post-order DFS, track max gain.)

5. **LeetCode 297** — Serialize and Deserialize Binary Tree. (Hint: Preorder traversal with null markers.)

6. **LeetCode 329** — Longest Increasing Path in a Matrix. (Hint: DFS with memoization.)

7. **LeetCode 295** — Find Median from Data Stream. (Hint: Two heaps — max-heap for lower half, min-heap for upper half.)

8. **LeetCode 76** — Minimum Window Substring. (Hint: Sliding window with character count map.)

9. **LeetCode 312** — Burst Balloons. (Hint: Interval DP, dp[i][j] = max coins for bursting balloons between i and j.)

10. **LeetCode 269** — Alien Dictionary. (Hint: Topological sort on character graph.)
