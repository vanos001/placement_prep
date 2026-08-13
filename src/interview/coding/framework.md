# Coding Interview Framework: Step-by-Step Problem Solving

## 🎯 The UMPIRE Method

A proven framework used by engineers at Google, Meta, and Amazon:

```
U - Understand the problem
M - Match to known patterns
P - Plan the solution
I - Implement the code
R - Review / test
E - Evaluate complexity
```

---

## Step 1: Understand (3-5 minutes)

### Questions to Ask

**Input/Output:**
- What are the inputs? What type? What size?
- What is the expected output format?
- Can the input be empty/null?

**Constraints:**
- What are the time/space constraints?
- Are there memory limits?
- Is the input sorted? Contains duplicates?

**Edge Cases:**
- Empty input
- Single element
- All same elements
- Negative numbers
- Very large input (overflow?)

**Examples:**
- Walk through 1-2 examples from the problem
- Create your own example that tests edge cases

### Template Questions Script
```
"Before I start, let me clarify a few things:
1. Can the input array be empty?
2. Are there negative numbers?
3. Can there be duplicates?
4. What should I return if there's no valid answer?
5. Is the input sorted?"
```

---

## Step 2: Match (2-3 minutes)

### Pattern Recognition Checklist

```
┌─────────────────────────────────────────────────────────┐
│              PATTERN MATCHING FLOWCHART                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Is input sorted?                                       │
│  ├── Yes → Two Pointers / Binary Search                 │
│  └── No → Continue...                                   │
│                                                         │
│  Need contiguous subarray/substring?                    │
│  ├── Yes → Sliding Window                               │
│  └── No → Continue...                                   │
│                                                         │
│  Need to find pairs with condition?                     │
│  ├── Yes → Hash Map / Two Pointers                      │
│  └── No → Continue...                                   │
│                                                         │
│  Tree/graph traversal?                                  │
│  ├── Level-by-level → BFS                               │
│  ├── All paths → DFS + Backtracking                     │
│  └── Shortest path → BFS (unweighted) / Dijkstra        │
│                                                         │
│  Need all combinations/permutations?                    │
│  ├── Yes → Backtracking                                 │
│  └── No → Continue...                                   │
│                                                         │
│  Optimal substructure + overlapping subproblems?        │
│  ├── Yes → Dynamic Programming                          │
│  └── No → Continue...                                   │
│                                                         │
│  Need K largest/smallest?                               │
│  ├── Yes → Heap (Priority Queue)                        │
│  └── No → Continue...                                   │
│                                                         │
│  Dependencies between tasks?                            │
│  ├── Yes → Topological Sort                             │
│  └── No → Continue...                                   │
│                                                         │
│  Connected components?                                  │
│  ├── Yes → Union Find / BFS/DFS                         │
│  └── No → Continue...                                   │
│                                                         │
│  Next greater/smaller element?                          │
│  ├── Yes → Monotonic Stack                              │
│  └── No → Brute force, then optimize                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Step 3: Plan (3-5 minutes)

### Always Start with Brute Force

```
"I'll start with a brute force approach, then optimize."

Brute Force: O(n²) or O(n³)
├── Identify the bottleneck
├── Ask: Can I use a hash map for O(1) lookup?
├── Ask: Can I sort first to use two pointers?
├── Ask: Can I use a heap for top-K?
└── Ask: Can I use DP to avoid recomputation?
```

### Discuss Trade-offs

```
"I see two approaches:
1. [Approach A]: O(n) time, O(n) space - uses extra hash map
2. [Approach B]: O(n log n) time, O(1) space - sort first

I'd go with [Approach A/B] because [reasoning about constraints]."
```

### Write Pseudocode

```python
# Pseudocode (don't write real code yet)
def solve(input):
    # 1. Initialize data structure
    # 2. Process input in loop
    # 3. Update result
    # 4. Return answer
```

---

## Step 4: Implement (15-20 minutes)

### Code Quality Checklist

```python
# ✅ Good
def twoSum(nums, target):
    seen = {}  # value -> index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []  # No solution found

# ❌ Bad
def f(a, t):
    d = {}
    for i in range(len(a)):
        if t-a[i] in d:
            return [d[t-a[i]], i]
        d[a[i]] = i
```

### Best Practices
1. **Descriptive variable names** — `left`, `right`, not `l`, `r`
2. **Consistent naming** — camelCase or snake_case, not mixed
3. **Break into helper functions** — Especially for recursive solutions
4. **Handle edge cases early** — Return immediately for empty/null
5. **Comment tricky parts** — Not every line, just the non-obvious

### Implementation Template
```python
def solution(input):
    # Edge case
    if not input:
        return default_value

    # Initialize
    data_structure = ...
    result = ...

    # Main logic
    for element in input:
        # Process
        ...

    return result
```

---

## Step 5: Review / Test (5 minutes)

### Walk Through Your Code

Pick a test case and trace through **every line**:

```
Input: [2, 7, 11, 15], target = 9

i=0: num=2, complement=7, seen={} → not found, seen={2:0}
i=1: num=7, complement=2, seen={2:0} → found! return [0, 1]

✓ Correct!
```

### Test Cases to Walk Through

1. **Normal case** — Typical input
2. **Edge case** — Empty, single element
3. **Boundary** — Min/max values
4. **Special** — All same, sorted reverse, etc.

### Common Bugs to Check

```
□ Off-by-one errors (<= vs <, length-1)
□ Integer overflow (use long for large numbers)
□ Null/empty handling
□ Modifying collection while iterating
□ Missing return statement
□ Wrong variable in loop (i vs j)
□ Not resetting state between iterations
```

---

## Step 6: Evaluate (2 minutes)

### State Complexity

```
"Let me analyze the complexity:
- Time: O(n) because we iterate through the array once
- Space: O(n) for the hash map in the worst case"
```

### Discuss Optimizations

```
"If we had more time / different constraints:
- We could sort first for O(1) space but O(n log n) time
- We could use bit manipulation if the range was limited
- We could parallelize for very large inputs"
```

---

## 🎯 Framework in Action: Example Problem

### Problem: Longest Substring Without Repeating Characters

**Step 1: Understand**
```
"Let me clarify:
- Input is a string
- I need to find the longest substring with no repeating characters
- Can the string be empty? (Yes → return 0)
- Only lowercase? (Clarify with interviewer)
- Example: 'abcabcbb' → 'abc' → length 3"
```

**Step 2: Match**
```
"This is a contiguous substring problem → Sliding Window pattern.
I'll use a hash set to track characters in the current window."
```

**Step 3: Plan**
```
"Approach: Sliding Window with hash set
- Expand right pointer, add character to set
- If character already in set, shrink from left until removed
- Track max window size

Time: O(n), Space: O(min(n, m)) where m is charset size"
```

**Step 4: Implement**
```python
def lengthOfLongestSubstring(s):
    char_set = set()
    left = 0
    max_length = 0

    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_length = max(max_length, right - left + 1)

    return max_length
```

**Step 5: Review**
```
"Let me trace 'abcabcbb':
right=0: 'a' not in set, add, window='a', max=1
right=1: 'b' not in set, add, window='ab', max=2
right=2: 'c' not in set, add, window='abc', max=3
right=3: 'a' in set, remove 'a' (left=0), left=1, add 'a', window='bca', max=3
... continues correctly

Edge case: '' → returns 0 ✓
Edge case: 'bbbb' → returns 1 ✓"
```

**Step 6: Evaluate**
```
"Time: O(n) — each character is visited at most twice (once by right, once by left)
Space: O(min(n, m)) — the set holds at most min(n, charset_size) characters"
```

---

## ⚠️ Common Interview Mistakes

### Technical Mistakes
1. **Jumping to code** without understanding the problem
2. **Starting with optimal** instead of brute force
3. **Not handling edge cases** (empty input, null, single element)
4. **Off-by-one errors** in loop bounds
5. **Modifying input** when it should be preserved
6. **Integer overflow** with large numbers

### Communication Mistakes
1. **Silent coding** — Always explain your thought process
2. **Not asking questions** — Shows you assume instead of clarify
3. **Ignoring hints** — Interviewers give hints for a reason
4. **Arguing with interviewer** — They're trying to help
5. **Giving up too quickly** — Show you can work through difficulty

### Process Mistakes
1. **No testing** — Always walk through at least one test case
2. **No complexity analysis** — Always state time and space
3. **Spending too long** on one approach — Know when to pivot
4. **Not discussing trade-offs** — Shows depth of understanding

## 🔗 Cross-References

- [Problem Patterns](./patterns.md) — Match problems to patterns in Step 2
- [Data Structures](./data-structures.md) — Choose the right structure in Step 3
- [Complexity Analysis](./complexity.md) — Analyze in Step 6
- [System Design Framework](../system-design/framework.md) — Similar structured approach for design
