# Chapter 67: Algorithmic Thinking

## Prerequisites

- Basic programming
- Problem-solving experience

## Interview Frequency: ★★★★★

Algorithmic thinking is the foundation of every technical interview. Companies like **Google**, **Meta**, **Amazon**, and **Apple** test not just knowledge of algorithms, but the ability to think algorithmically—breaking problems into steps, recognizing patterns, and designing efficient solutions.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Decomposition | ★★★★★ | Easy | Break problem into subproblems |
| Pattern Matching | ★★★★★ | Medium | Recognize known patterns |
| Abstraction | ★★★★ | Medium | Ignore irrelevant details |
| Generalization | ★★★ | Medium | Extend specific to general |
| Refinement | ★★★★ | Medium | Iteratively improve solutions |

---

## 67.1 What Is Algorithmic Thinking?

Algorithmic thinking is a systematic approach to problem-solving that involves:

1. **Understanding** the problem precisely
2. **Decomposing** it into manageable parts
3. **Recognizing** patterns from known problems
4. **Designing** a step-by-step solution
5. **Verifying** correctness
6. **Optimizing** for efficiency

### The Algorithmic Thinking Framework

```
┌─────────────┐
│  UNDERSTAND  │ ← Read carefully, ask questions, identify constraints
└──────┬──────┘
       ▼
┌─────────────┐
│  EXPLORE     │ ← Try examples, draw diagrams, find patterns
└──────┬──────┘
       ▼
┌─────────────┐
│  PLAN       │ ← Choose approach, estimate complexity
└──────┬──────┘
       ▼
┌─────────────┐
│  IMPLEMENT  │ ← Write clean, correct code
└──────┬──────┘
       ▼
┌─────────────┐
│  VERIFY     │ ← Test with examples, edge cases
└──────┬──────┘
       ▼
┌─────────────┐
│  OPTIMIZE   │ ← Improve time/space if needed
└─────────────┘
```

---

## 67.2 Decomposition

**Decomposition** breaks a complex problem into smaller, manageable subproblems.

### Types of Decomposition

| Type | Description | Example |
|---|---|---|
| Sequential | Steps in order | Sort, then search |
| Parallel | Independent subproblems | Process left/right halves |
| Recursive | Same problem, smaller input | Fibonacci, merge sort |
| Hierarchical | Tree of subproblems | Tree DP |

### Example: Finding the K-th Largest Element

**Problem**: Find the k-th largest element in an unsorted array.

**Decomposition**:
1. Can I sort first? → O(n log n), then pick arr[n-k]
2. Can I use a heap? → O(n log k) with min-heap of size k
3. Can I use quickselect? → O(n) average
4. Can I use binary search on value? → O(n log MAX)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <random>

// Approach 1: Sort - O(n log n)
int kthLargestSort(std::vector<int> arr, int k) {
    std::sort(arr.begin(), arr.end(), std::greater<int>());
    return arr[k - 1];
}

// Approach 2: Min-heap of size k - O(n log k)
int kthLargestHeap(const std::vector<int>& arr, int k) {
    std::priority_queue<int, std::vector<int>, std::greater<int>> minHeap;
    for (int x : arr) {
        minHeap.push(x);
        if ((int)minHeap.size() > k) minHeap.pop();
    }
    return minHeap.top();
}

// Approach 3: Quickselect - O(n) average
int quickselect(std::vector<int>& arr, int k) {
    std::mt19937 rng(42);
    int lo = 0, hi = arr.size() - 1;
    
    while (lo <= hi) {
        std::uniform_int_distribution<int> dist(lo, hi);
        int pivotIdx = dist(rng);
        std::swap(arr[pivotIdx], arr[hi]);
        
        int pivot = arr[hi];
        int i = lo;
        for (int j = lo; j < hi; j++) {
            if (arr[j] >= pivot) {
                std::swap(arr[i++], arr[j]);
            }
        }
        std::swap(arr[i], arr[hi]);
        
        if (i == k - 1) return arr[i];
        if (i < k - 1) lo = i + 1;
        else hi = i - 1;
    }
    return -1;
}

int main() {
    std::vector<int> arr = {3, 2, 1, 5, 6, 4};
    int k = 2;
    
    std::cout << "Array: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";
    
    std::cout << k << "-th largest (sort): " << kthLargestSort(arr, k) << "\n";
    std::cout << k << "-th largest (heap): " << kthLargestHeap(arr, k) << "\n";
    
    std::vector<int> arr2 = arr;
    std::cout << k << "-th largest (quickselect): " << quickselect(arr2, k) << "\n";
    
    return 0;
}
```

---

## 67.3 Pattern Matching

**Pattern matching** recognizes that a new problem is structurally similar to a known problem.

### Common Patterns

| Pattern | Signal | Technique |
|---|---|---|
| Sorted array | "Given a sorted array..." | Binary search |
| Optimization | "Minimum/Maximum cost" | DP or Greedy |
| Connectivity | "Connected components" | Union-Find, DFS |
| Ordering | "Order of tasks" | Topological sort |
| Frequency | "Count occurrences" | Hash map |
| Subarray | "Contiguous elements" | Sliding window, prefix sum |
| Subsequence | "Not necessarily contiguous" | DP |
| Tree path | "Path between nodes" | LCA, HLD |
| Game | "Two players, optimal" | Game theory, Grundy numbers |

### How to Build Pattern Recognition

1. **Solve many problems**: Exposure builds intuition
2. **Categorize solutions**: Group problems by technique
3. **Abstract the pattern**: What makes this problem amenable to this technique?
4. **Practice recognition**: Given a problem, identify the technique before solving

---

## 67.4 Abstraction

**Abstraction** ignores irrelevant details and focuses on the essential structure.

### Example: Word Ladder

**Problem**: Transform "hit" to "cog" by changing one letter at a time, using only valid words.

**Abstraction**: This is a shortest path problem on an implicit graph where:
- Nodes = words
- Edges = words differing by one letter
- Algorithm = BFS (unweighted graph)

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <string>
#include <unordered_set>
#include <algorithm>

int ladderLength(std::string beginWord, std::string endWord,
                 std::vector<std::string>& wordList) {
    std::unordered_set<std::string> wordSet(wordList.begin(), wordList.end());
    if (!wordSet.count(endWord)) return 0;
    
    std::queue<std::pair<std::string, int>> q;
    q.push({beginWord, 1});
    std::unordered_set<std::string> visited;
    visited.insert(beginWord);
    
    while (!q.empty()) {
        auto [word, dist] = q.front();
        q.pop();
        
        if (word == endWord) return dist;
        
        for (int i = 0; i < (int)word.size(); i++) {
            char original = word[i];
            for (char c = 'a'; c <= 'z'; c++) {
                word[i] = c;
                if (wordSet.count(word) && !visited.count(word)) {
                    visited.insert(word);
                    q.push({word, dist + 1});
                }
            }
            word[i] = original;
        }
    }
    
    return 0;
}

int main() {
    std::vector<std::string> wordList = {"hot", "dot", "dog", "lot", "log", "cog"};
    std::cout << "Ladder length: " << ladderLength("hit", "cog", wordList) << "\n";
    return 0;
}
```

---

## 67.5 The Exploration Phase

Before designing an algorithm, explore the problem space:

### Exploration Checklist

```
□ Work through 2-3 examples by hand
□ Draw diagrams (trees, graphs, matrices)
□ Identify constraints (input size → complexity budget)
□ Look for patterns in the examples
□ Consider edge cases (empty, single element, all same)
□ Check if the problem has special structure (sorted, tree, etc.)
```

### Constraint Analysis

Input size tells you what complexity is acceptable:

| Input Size | Acceptable Complexity | Typical Approach |
|---|---|---|
| n ≤ 10 | O(n!) | Permutation/brute force |
| n ≤ 20 | O(2^n) | Bitmask DP, backtracking |
| n ≤ 500 | O(n³) | Floyd-Warshall, matrix chain |
| n ≤ 5000 | O(n²) | Simple DP, nested loops |
| n ≤ 10^6 | O(n log n) | Sorting, divide and conquer |
| n ≤ 10^7 | O(n) | Linear scan, hash map |
| n > 10^7 | O(log n) or O(1) | Binary search, math |

---

## 67.6 From Brute Force to Optimal

### The Optimization Ladder

```
Step 1: Brute Force (correct but slow)
  ↓ Identify bottleneck
Step 2: Eliminate redundant work (memoization, hash map)
  ↓ Identify structure
Step 3: Use appropriate data structure (heap, BST, segment tree)
  ↓ Identify mathematical property
Step 4: Apply algorithmic technique (DP, greedy, divide & conquer)
  ↓ Fine-tune
Step 5: Micro-optimizations (constant factors, cache)
```

### Example: Two Sum → Three Sum → Four Sum

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_map>

// Two Sum: O(n) with hash map
std::vector<int> twoSum(const std::vector<int>& arr, int target) {
    std::unordered_map<int, int> seen;
    for (int i = 0; i < (int)arr.size(); i++) {
        int complement = target - arr[i];
        if (seen.count(complement)) {
            return {seen[complement], i};
        }
        seen[arr[i]] = i;
    }
    return {};
}

// Three Sum: O(n²) with two pointers after sorting
std::vector<std::vector<int>> threeSum(std::vector<int> arr, int target) {
    std::sort(arr.begin(), arr.end());
    int n = arr.size();
    std::vector<std::vector<int>> result;
    
    for (int i = 0; i < n - 2; i++) {
        if (i > 0 && arr[i] == arr[i-1]) continue;
        
        int lo = i + 1, hi = n - 1;
        while (lo < hi) {
            int sum = arr[i] + arr[lo] + arr[hi];
            if (sum == target) {
                result.push_back({arr[i], arr[lo], arr[hi]});
                while (lo < hi && arr[lo] == arr[lo+1]) lo++;
                while (lo < hi && arr[hi] == arr[hi-1]) hi--;
                lo++; hi--;
            } else if (sum < target) lo++;
            else hi--;
        }
    }
    
    return result;
}

int main() {
    // Two Sum
    auto result2 = twoSum({2, 7, 11, 15}, 9);
    std::cout << "Two Sum indices: " << result2[0] << ", " << result2[1] << "\n";
    
    // Three Sum
    auto result3 = threeSum({-1, 0, 1, 2, -1, -4}, 0);
    std::cout << "Three Sum triplets:\n";
    for (auto& triplet : result3) {
        std::cout << "  [" << triplet[0] << "," << triplet[1] 
                  << "," << triplet[2] << "]\n";
    }
    
    return 0;
}
```

---

## 67.7 Common Algorithmic Paradigms

| Paradigm | Core Idea | When to Use | Example |
|---|---|---|---|
| Brute Force | Try everything | Small input, correctness check | All permutations |
| Divide & Conquer | Split, solve, merge | Independent subproblems | Merge sort |
| Greedy | Local optimal = global optimal | Exchange argument holds | Activity selection |
| Dynamic Programming | Optimal substructure + overlapping | Min/max with choices | Knapsack |
| Backtracking | Explore + prune | All solutions needed | N-Queens |
| Binary Search | Eliminate half each step | Monotonic property | Search in sorted |
| Two Pointers | Converge from ends | Sorted array, pairs | Container with most water |
| Sliding Window | Maintain window invariant | Contiguous subarray | Max sum subarray of size k |

---

## Summary

| Skill | Key Insight | Practice Method |
|---|---|---|
| Decomposition | Break into subproblems | Solve 100+ problems |
| Pattern Matching | Recognize known structures | Categorize solutions |
| Abstraction | Ignore irrelevant details | Model problems as graphs |
| Exploration | Work examples by hand | Always do this first |
| Constraint Analysis | Input size → complexity | Check before coding |
| Optimization | Brute force → optimal | Practice the ladder |
