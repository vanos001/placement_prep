# Chapter 32: Greedy Algorithms

Greedy algorithms make the **locally optimal choice at each step** with the hope of finding a global optimum. Unlike dynamic programming, which considers all possibilities, greedy commits to a choice without looking back. When it works, greedy solutions are elegant, efficient, and simple. The challenge is knowing **when** greedy works — and proving it.

---

## 32.1 What Is Greedy?

A greedy algorithm builds a solution piece by piece, at each step choosing the piece that offers the most immediate benefit. It never reconsiders its choices.

### The Greedy Choice Property

A problem exhibits the **greedy choice property** if a globally optimal solution can be arrived at by making locally optimal choices. In other words, there exists an optimal solution that includes the greedy choice at every step.

### When Greedy Works

Greedy works when:
1. **Greedy choice property**: Making the locally optimal choice leads to a global optimum.
2. **Optimal substructure**: After making a greedy choice, the remaining problem has the same structure.

### When Greedy Doesn't Work

Consider the **0/1 Knapsack** problem. A greedy approach (pick highest value-to-weight ratio first) fails:

```
Capacity: 50
Items: (value=60, weight=10), (value=100, weight=20), (value=120, weight=30)
Ratios: 6, 5, 4
```

Greedy picks items by ratio: item 1 (ratio 6, weight 10) + item 2 (ratio 5, weight 20) = value 160, weight 30. Remaining capacity 20, item 3 doesn't fit.

Optimal: items 2 + 3 = value 220, weight 50. (Or items 1 + 3 = 180, weight 40.)

The greedy solution misses the optimal. This is why 0/1 Knapsack requires DP.

---

## 32.2 Greedy vs DP

Let's solve the same problem both ways to see the difference.

### Problem: Coin Change with Canonical Coin Systems

With US coins (1, 5, 10, 25), greedy works: always pick the largest coin ≤ remaining amount.

With arbitrary denominations, greedy may fail. For coins {1, 3, 4} and amount 6:
- Greedy: 4 + 1 + 1 = 3 coins
- Optimal: 3 + 3 = 2 coins

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

// Greedy coin change (works for canonical systems like US coins)
int coin_change_greedy(std::vector<int> coins, int amount) {
    std::sort(coins.rbegin(), coins.rend());
    int count = 0;
    for (int coin : coins) {
        while (amount >= coin) {
            amount -= coin;
            ++count;
        }
    }
    return (amount == 0) ? count : -1;
}

// DP coin change (works for any coin system)
int coin_change_dp(const std::vector<int>& coins, int amount) {
    std::vector<int> dp(amount + 1, INT_MAX);
    dp[0] = 0;
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
    // Canonical system: greedy works
    std::vector<int> us_coins = {1, 5, 10, 25};
    std::cout << "Greedy (US, 30): " << coin_change_greedy(us_coins, 30) << "\n";
    std::cout << "DP (US, 30):     " << coin_change_dp(us_coins, 30) << "\n";
    
    // Non-canonical: greedy fails
    std::vector<int> bad_coins = {1, 3, 4};
    std::cout << "Greedy ({1,3,4}, 6): " << coin_change_greedy(bad_coins, 6) << "\n";
    std::cout << "DP ({1,3,4}, 6):     " << coin_change_dp(bad_coins, 6) << "\n";
    
    return 0;
}
```

**Output**:
```
Greedy (US, 30): 2
DP (US, 30):     2
Greedy ({1,3,4}, 6): 3
DP ({1,3,4}, 6):     2
```

### Key Difference

| Aspect | Greedy | DP |
|--------|--------|-----|
| Decision | Commits immediately | Explores all options |
| Subproblems | Solves one subproblem | Solves all subproblems |
| Proof | Needs exchange argument | Optimal substructure suffices |
| Complexity | Usually O(n log n) or O(n) | Usually O(n²) or higher |
| Correctness | Problem-specific | Always correct (if implemented right) |

---

## 32.3 Exchange Argument

The **exchange argument** is the standard technique for proving greedy correctness.

### The Technique

1. **Assume** there exists an optimal solution `O` that differs from the greedy solution `G`.
2. **Show** that we can "exchange" a choice in `O` to match `G` without making the solution worse.
3. **Conclude** that `G` is also optimal (or that we can transform `O` into `G`).

### Example: Activity Selection

**Claim**: Selecting the activity with the earliest finish time is optimal.

**Proof by exchange argument**:

1. Let `G` = greedy solution, `O` = any optimal solution.
2. Let `g₁` = first activity in `G` (earliest finish time), `o₁` = first activity in `O`.
3. Since `g₁` has the earliest finish time: `finish(g₁) ≤ finish(o₁)`.
4. Replace `o₁` with `g₁` in `O`. Since `g₁` finishes no later than `o₁`, all activities in `O` that were compatible with `o₁` are still compatible with `g₁`.
5. The new solution has the same size as `O` and includes `g₁`.
6. By induction, we can transform `O` into `G` without losing optimality.

Therefore, the greedy solution is optimal. ∎

---

## 32.4 Activity Selection

**Problem**: Given `n` activities with start and finish times, select the maximum number of non-overlapping activities.

### Greedy Approach

Sort by finish time. Greedily select the next activity that starts after the last selected activity finishes.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Activity {
    int start, finish, id;
};

int activity_selection(std::vector<Activity>& activities) {
    // Sort by finish time
    std::sort(activities.begin(), activities.end(),
              [](const Activity& a, const Activity& b) {
                  return a.finish < b.finish;
              });
    
    int count = 0;
    int last_finish = -1;
    
    std::cout << "Selected activities: ";
    for (const auto& act : activities) {
        if (act.start >= last_finish) {
            ++count;
            last_finish = act.finish;
            std::cout << act.id << " ";
        }
    }
    std::cout << "\n";
    return count;
}

int main() {
    std::vector<Activity> activities = {
        {1, 4, 1}, {3, 5, 2}, {0, 6, 3}, {5, 7, 4},
        {3, 9, 5}, {5, 9, 6}, {6, 10, 7}, {8, 11, 8},
        {8, 12, 9}, {2, 14, 10}, {12, 16, 11}
    };
    
    std::cout << "Max activities: " << activity_selection(activities) << "\n";
    return 0;
}
```

**Output**:
```
Selected activities: 1 4 7 8 11 
Max activities: 5
```

**Complexity**: O(n log n) for sorting + O(n) for selection = O(n log n).

### Dry Run

```
Sorted by finish: (1,4), (3,5), (0,6), (5,7), (3,9), (5,9), (6,10), (8,11), (8,12), (2,14), (12,16)

Step 1: Select (1,4). last_finish=4
Step 2: (3,5): start=3 < 4. Skip.
Step 3: (0,6): start=0 < 4. Skip.
Step 4: (5,7): start=5 ≥ 4. Select. last_finish=7
Step 5: (3,9): start=3 < 7. Skip.
Step 6: (5,9): start=5 < 7. Skip.
Step 7: (6,10): start=6 < 7. Skip.
Step 8: (8,11): start=8 ≥ 7. Select. last_finish=11
Step 9: (8,12): start=8 < 11. Skip.
Step 10: (2,14): start=2 < 11. Skip.
Step 11: (12,16): start=12 ≥ 11. Select. last_finish=16

Result: 5 activities selected.
```

---

## 32.5 Huffman Coding

Huffman coding is a lossless data compression algorithm that assigns variable-length codes to characters based on their frequency. More frequent characters get shorter codes.

### The Algorithm

1. Create a leaf node for each character with its frequency.
2. While there's more than one node:
   a. Extract the two nodes with lowest frequency.
   b. Create a new internal node with these two as children, frequency = sum.
   c. Insert the new node back.
3. The resulting tree gives the Huffman codes.

```cpp
#include <iostream>
#include <queue>
#include <unordered_map>
#include <string>
#include <vector>

struct HuffmanNode {
    char ch;
    int freq;
    HuffmanNode* left;
    HuffmanNode* right;
    
    HuffmanNode(char c, int f) : ch(c), freq(f), left(nullptr), right(nullptr) {}
    HuffmanNode(int f, HuffmanNode* l, HuffmanNode* r) 
        : ch('\0'), freq(f), left(l), right(r) {}
};

struct Compare {
    bool operator()(HuffmanNode* a, HuffmanNode* b) {
        return a->freq > b->freq;  // Min-heap
    }
};

class HuffmanCoding {
    HuffmanNode* root;
    std::unordered_map<char, std::string> codes;
    
    void build_codes(HuffmanNode* node, const std::string& code) {
        if (!node) return;
        if (!node->left && !node->right) {
            codes[node->ch] = code.empty() ? "0" : code;
            return;
        }
        build_codes(node->left, code + "0");
        build_codes(node->right, code + "1");
    }
    
    void free_tree(HuffmanNode* node) {
        if (!node) return;
        free_tree(node->left);
        free_tree(node->right);
        delete node;
    }
    
public:
    HuffmanCoding() : root(nullptr) {}
    ~HuffmanCoding() { free_tree(root); }
    
    void build(const std::string& text) {
        // Count frequencies
        std::unordered_map<char, int> freq;
        for (char c : text) freq[c]++;
        
        // Build priority queue
        std::priority_queue<HuffmanNode*, std::vector<HuffmanNode*>, Compare> pq;
        for (auto& [ch, f] : freq) {
            pq.push(new HuffmanNode(ch, f));
        }
        
        // Build Huffman tree
        while (pq.size() > 1) {
            HuffmanNode* left = pq.top(); pq.pop();
            HuffmanNode* right = pq.top(); pq.pop();
            pq.push(new HuffmanNode(left->freq + right->freq, left, right));
        }
        
        if (!pq.empty()) {
            root = pq.top();
            build_codes(root, "");
        }
    }
    
    std::string encode(const std::string& text) {
        std::string encoded;
        for (char c : text) encoded += codes[c];
        return encoded;
    }
    
    std::string decode(const std::string& encoded) {
        std::string decoded;
        HuffmanNode* curr = root;
        for (char bit : encoded) {
            curr = (bit == '0') ? curr->left : curr->right;
            if (!curr->left && !curr->right) {
                decoded += curr->ch;
                curr = root;
            }
        }
        return decoded;
    }
    
    void print_codes() {
        for (auto& [ch, code] : codes) {
            std::cout << "'" << ch << "': " << code << "\n";
        }
    }
};

int main() {
    std::string text = "this is an example of huffman encoding";
    
    HuffmanCoding huffman;
    huffman.build(text);
    
    std::cout << "Huffman Codes:\n";
    huffman.print_codes();
    
    std::string encoded = huffman.encode(text);
    std::cout << "\nEncoded: " << encoded << "\n";
    std::cout << "Original size: " << text.size() * 8 << " bits\n";
    std::cout << "Compressed size: " << encoded.size() << " bits\n";
    std::cout << "Compression ratio: " 
              << (1.0 - (double)encoded.size() / (text.size() * 8)) * 100 << "%\n";
    
    std::string decoded = huffman.decode(encoded);
    std::cout << "Decoded: " << decoded << "\n";
    std::cout << "Match: " << (text == decoded ? "Yes" : "No") << "\n";
    
    return 0;
}
```

**Complexity**: O(n log n) where n is the number of distinct characters.

---

## 32.6 Fractional Knapsack

**Problem**: Given items with weights and values, and a knapsack capacity, maximize value. You can take **fractions** of items.

### Greedy Approach

Sort by value-to-weight ratio in decreasing order. Take as much as possible of the highest-ratio item, then the next, etc.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Item {
    double value, weight;
    double ratio;
};

double fractional_knapsack(std::vector<Item> items, double capacity) {
    // Calculate ratios and sort
    for (auto& item : items) {
        item.ratio = item.value / item.weight;
    }
    std::sort(items.begin(), items.end(),
              [](const Item& a, const Item& b) {
                  return a.ratio > b.ratio;
              });
    
    double total_value = 0.0;
    double remaining = capacity;
    
    for (const auto& item : items) {
        if (remaining >= item.weight) {
            // Take the whole item
            total_value += item.value;
            remaining -= item.weight;
            std::cout << "Take full: value=" << item.value 
                      << " weight=" << item.weight << "\n";
        } else {
            // Take fraction
            double fraction = remaining / item.weight;
            total_value += item.value * fraction;
            std::cout << "Take " << fraction * 100 << "%: value=" << item.value 
                      << " weight=" << item.weight << "\n";
            remaining = 0;
            break;
        }
    }
    return total_value;
}

int main() {
    std::vector<Item> items = {
        {60, 10}, {100, 20}, {120, 30}
    };
    double capacity = 50;
    
    std::cout << "Max value: " << fractional_knapsack(items, capacity) << "\n";
    return 0;
}
```

**Output**:
```
Take full: value=60 weight=10
Take full: value=100 weight=20
Take 66.6667%: value=120 weight=30
Max value: 240
```

**Complexity**: O(n log n).

---

## 32.7 Job Scheduling

### Unweighted Job Scheduling

Maximize the number of jobs completed. This is exactly the activity selection problem.

### Weighted Job Scheduling

Maximize total weight of non-overlapping jobs. This **requires DP**, not greedy.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Job {
    int start, finish, weight;
};

int weighted_job_scheduling(std::vector<Job>& jobs) {
    // Sort by finish time
    std::sort(jobs.begin(), jobs.end(),
              [](const Job& a, const Job& b) {
                  return a.finish < b.finish;
              });
    
    int n = jobs.size();
    std::vector<int> dp(n);
    dp[0] = jobs[0].weight;
    
    for (int i = 1; i < n; ++i) {
        // Find latest non-conflicting job
        int include = jobs[i].weight;
        for (int j = i - 1; j >= 0; --j) {
            if (jobs[j].finish <= jobs[i].start) {
                include += dp[j];
                break;
            }
        }
        dp[i] = std::max(dp[i - 1], include);
    }
    return dp[n - 1];
}

// Optimized with binary search: O(n log n)
int weighted_job_scheduling_opt(std::vector<Job>& jobs) {
    std::sort(jobs.begin(), jobs.end(),
              [](const Job& a, const Job& b) {
                  return a.finish < b.finish;
              });
    
    int n = jobs.size();
    std::vector<int> dp(n);
    dp[0] = jobs[0].weight;
    
    for (int i = 1; i < n; ++i) {
        // Binary search for latest non-conflicting job
        int lo = 0, hi = i - 1, best = -1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (jobs[mid].finish <= jobs[i].start) {
                best = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        
        int include = jobs[i].weight;
        if (best != -1) include += dp[best];
        
        dp[i] = std::max(dp[i - 1], include);
    }
    return dp[n - 1];
}

int main() {
    std::vector<Job> jobs = {
        {1, 3, 50}, {2, 5, 20}, {4, 6, 70}, {6, 7, 60}, {5, 8, 30}
    };
    std::cout << "Max weighted jobs: " << weighted_job_scheduling_opt(jobs) << "\n";
    return 0;
}
```

**Key insight**: Weighted job scheduling needs DP because the greedy choice (earliest finish) doesn't account for weights.

---

## 32.8 Interval Scheduling

### Merge Overlapping Intervals

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Interval {
    int start, end;
};

std::vector<Interval> merge_intervals(std::vector<Interval>& intervals) {
    if (intervals.empty()) return {};
    
    std::sort(intervals.begin(), intervals.end(),
              [](const Interval& a, const Interval& b) {
                  return a.start < b.start;
              });
    
    std::vector<Interval> merged = {intervals[0]};
    for (int i = 1; i < (int)intervals.size(); ++i) {
        if (intervals[i].start <= merged.back().end) {
            merged.back().end = std::max(merged.back().end, intervals[i].end);
        } else {
            merged.push_back(intervals[i]);
        }
    }
    return merged;
}

int main() {
    std::vector<Interval> intervals = {{1,3}, {2,6}, {8,10}, {15,18}};
    auto merged = merge_intervals(intervals);
    std::cout << "Merged intervals: ";
    for (auto& iv : merged) {
        std::cout << "[" << iv.start << "," << iv.end << "] ";
    }
    std::cout << "\n";
    return 0;
}
```

### Minimum Number of Arrows to Burst Balloons

**Problem**: Given balloons as horizontal intervals, find the minimum number of arrows (shot vertically) to burst all balloons. An arrow at position `x` bursts all balloons that span `x`.

**Greedy**: Sort by end point. Shoot an arrow at the end of the first unburst balloon.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int find_min_arrows(std::vector<std::vector<int>>& points) {
    if (points.empty()) return 0;
    
    // Sort by end point
    std::sort(points.begin(), points.end(),
              [](const std::vector<int>& a, const std::vector<int>& b) {
                  return a[1] < b[1];
              });
    
    int arrows = 1;
    int arrow_pos = points[0][1];
    
    for (int i = 1; i < (int)points.size(); ++i) {
        if (points[i][0] > arrow_pos) {
            // Need a new arrow
            ++arrows;
            arrow_pos = points[i][1];
        }
    }
    return arrows;
}

int main() {
    std::vector<std::vector<int>> points = {{10,16}, {2,8}, {1,6}, {7,12}};
    std::cout << "Min arrows: " << find_min_arrows(points) << "\n";  // 2
    return 0;
}
```

---

## Interview Problem: Jump Game

**Problem**: Given an array where each element represents the maximum jump length, determine if you can reach the last index.

### Greedy Approach

Track the furthest reachable index. If at any point the current index exceeds the furthest reachable, return false.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

bool can_jump(const std::vector<int>& nums) {
    int max_reach = 0;
    for (int i = 0; i < (int)nums.size(); ++i) {
        if (i > max_reach) return false;
        max_reach = std::max(max_reach, i + nums[i]);
        if (max_reach >= (int)nums.size() - 1) return true;
    }
    return true;
}

int main() {
    std::vector<int> nums1 = {2, 3, 1, 1, 4};
    std::vector<int> nums2 = {3, 2, 1, 0, 4};
    
    std::cout << "Can jump [2,3,1,1,4]: " << (can_jump(nums1) ? "Yes" : "No") << "\n";
    std::cout << "Can jump [3,2,1,0,4]: " << (can_jump(nums2) ? "Yes" : "No") << "\n";
    return 0;
}
```

**Output**:
```
Can jump [2,3,1,1,4]: Yes
Can jump [3,2,1,0,4]: No
```

### Jump Game II (Minimum Jumps)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int min_jumps(const std::vector<int>& nums) {
    int n = nums.size();
    if (n <= 1) return 0;
    
    int jumps = 0;
    int current_end = 0;    // End of current jump range
    int farthest = 0;       // Furthest reachable in current range
    
    for (int i = 0; i < n - 1; ++i) {
        farthest = std::max(farthest, i + nums[i]);
        if (i == current_end) {
            ++jumps;
            current_end = farthest;
            if (current_end >= n - 1) break;
        }
    }
    return jumps;
}

int main() {
    std::vector<int> nums = {2, 3, 1, 1, 4};
    std::cout << "Min jumps: " << min_jumps(nums) << "\n";  // 2
    return 0;
}
```

## Interview Problem: Task Scheduler

**Problem**: Given tasks and a cooldown period `n`, find the minimum time to complete all tasks (same task must be separated by at least `n` intervals).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_map>

int least_interval(std::vector<char>& tasks, int n) {
    std::unordered_map<char, int> freq;
    for (char t : tasks) freq[t]++;
    
    int max_freq = 0;
    for (auto& [_, f] : freq) max_freq = std::max(max_freq, f);
    
    int max_count = 0;
    for (auto& [_, f] : freq) {
        if (f == max_freq) ++max_count;
    }
    
    // Formula: (max_freq - 1) * (n + 1) + max_count
    // But can't be less than tasks.size()
    int result = (max_freq - 1) * (n + 1) + max_count;
    return std::max(result, (int)tasks.size());
}

int main() {
    std::vector<char> tasks = {'A', 'A', 'A', 'B', 'B', 'B'};
    std::cout << "Least interval (n=2): " << least_interval(tasks, 2) << "\n";  // 8
    // A -> B -> idle -> A -> B -> idle -> A -> B
    
    std::vector<char> tasks2 = {'A', 'A', 'A', 'B', 'B', 'B'};
    std::cout << "Least interval (n=0): " << least_interval(tasks2, 0) << "\n";  // 6
    
    return 0;
}
```

## Interview Problem: Gas Station

**Problem**: Given gas amounts and costs at `n` stations arranged in a circle, find the starting station to complete the circuit, or -1 if impossible.

```cpp
#include <iostream>
#include <vector>

int can_complete_circuit(const std::vector<int>& gas, const std::vector<int>& cost) {
    int total_tank = 0;
    int current_tank = 0;
    int start = 0;
    
    for (int i = 0; i < (int)gas.size(); ++i) {
        int diff = gas[i] - cost[i];
        total_tank += diff;
        current_tank += diff;
        
        if (current_tank < 0) {
            start = i + 1;
            current_tank = 0;
        }
    }
    
    return (total_tank >= 0) ? start : -1;
}

int main() {
    std::vector<int> gas  = {1, 2, 3, 4, 5};
    std::vector<int> cost = {3, 4, 5, 1, 2};
    std::cout << "Start station: " << can_complete_circuit(gas, cost) << "\n";  // 3
    return 0;
}
```

**Why greedy works here**: If starting from station `i` you can't reach station `j+1`, then no station between `i` and `j` can be a valid start either (they'd have even less fuel when reaching `j`).

---

## Interview Tips

1. **Always prove greedy correctness** before coding. Use the exchange argument.

2. **Greedy fails on weighted problems** (weighted job scheduling, 0/1 knapsack). When you see "maximize total weight/value with constraints," think DP first.

3. **Sorting is the key**: Most greedy algorithms start with sorting by some criterion (finish time, ratio, end point).

4. **If greedy seems right but you can't prove it**, try DP. You can always fall back to DP.

5. **Greedy + Priority Queue** is a common pattern (Huffman, task scheduling, meeting rooms).

6. **Two conditions for greedy**: (1) Greedy choice property, (2) Optimal substructure.

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Applying greedy to 0/1 Knapsack | Wrong answer | Use DP instead |
| Wrong sorting criterion | Sort by start instead of finish in activity selection | Identify the right criterion |
| Not proving correctness | Greedy gives WA on edge cases | Use exchange argument |
| Greedy on weighted problems | Weighted job scheduling | Use DP |
| Assuming canonical coin system | Non-canonical denominations | Use DP for general case |

## Practice Problems

1. **Jump Game** (LeetCode 55) — Greedy reachability
2. **Jump Game II** (LeetCode 45) — Minimum jumps greedy
3. **Task Scheduler** (LeetCode 621) — Greedy with formula
4. **Gas Station** (LeetCode 134) — Circular greedy
5. **Minimum Number of Arrows** (LeetCode 452) — Interval greedy
6. **Non-overlapping Intervals** (LeetCode 435) — Activity selection variant
7. **Queue Reconstruction by Height** (LeetCode 406) — Greedy reconstruction
8. **Partition Labels** (LeetCode 763) — Greedy partitioning
9. **Course Schedule III** (LeetCode 630) — Greedy with priority queue
10. **Meeting Rooms II** (LeetCode 253) — Greedy with heap
