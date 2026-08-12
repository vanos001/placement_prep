# Chapter 38: Monotonic Queue

A monotonic queue extends the monotonic stack concept to support efficient retrieval of the minimum or maximum element in a sliding window. It is the go-to data structure for sliding window extremum problems and appears frequently in coding interviews.

---

## 38.1 What Is a Monotonic Queue?

A **monotonic queue** is a double-ended queue (deque) that maintains its elements in either increasing or decreasing order. Unlike a monotonic stack, which only gives access to one end, a deque allows efficient insertion and removal from both ends.

**Monotonic Decreasing Queue:** Front always holds the maximum. Elements are in decreasing order from front to back. Used to get sliding window maximum.

**Monotonic Increasing Queue:** Front always holds the minimum. Elements are in increasing order from front to back. Used to get sliding window minimum.

### Core Operations

For a monotonic decreasing queue processing element `arr[i]`:

1. **Remove expired elements:** If the front index is outside the current window, pop from the front.
2. **Maintain monotonicity:** While the back element ≤ `arr[i]`, pop from the back. This ensures the decreasing property.
3. **Insert:** Push `arr[i]` (with its index) to the back.
4. **Query:** The front of the deque is the maximum in the current window.

### Why a Deque and Not a Stack?

We need to remove elements from the front (expired indices) and from the back (to maintain monotonicity). A stack only allows removal from one end. A deque supports both in O(1).

---

## 38.2 Sliding Window Maximum (LeetCode 239)

### Problem

Given an array `nums` and a window size `k`, return the maximum value in each sliding window of size `k`.

**Example:**
```
nums = [1, 3, -1, -3, 5, 3, 6, 7], k = 3
Output: [3, 3, 5, 5, 6, 7]
```

### Naive Approach: O(nk)

For each window position, scan all k elements. This is too slow for large inputs.

### Optimal Approach: Monotonic Decreasing Queue — O(n)

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> maxSlidingWindow(vector<int>& nums, int k) {
    deque<int> dq;  // stores indices, front = index of max element
    vector<int> result;

    for (int i = 0; i < (int)nums.size(); i++) {
        // Step 1: Remove expired index from front
        if (!dq.empty() && dq.front() <= i - k) {
            dq.pop_front();
        }

        // Step 2: Maintain decreasing order — remove smaller elements from back
        while (!dq.empty() && nums[dq.back()] <= nums[i]) {
            dq.pop_back();
        }

        // Step 3: Insert current index
        dq.push_back(i);

        // Step 4: Record result once window is fully formed
        if (i >= k - 1) {
            result.push_back(nums[dq.front()]);
        }
    }
    return result;
}

int main() {
    vector<int> nums = {1, 3, -1, -3, 5, 3, 6, 7};
    int k = 3;

    vector<int> result = maxSlidingWindow(nums, k);
    cout << "Sliding window maximums: ";
    for (int x : result) cout << x << " ";
    cout << "\n";
    // Output: 3 3 5 5 6 7

    return 0;
}
```

### Dry Run

`nums = [1, 3, -1, -3, 5, 3, 6, 7]`, `k = 3`

Deque stores indices. Let's trace each step:

| i | nums[i] | Action | Deque (front→back) | Max | Result |
|---|---------|--------|---------------------|-----|--------|
| 0 | 1       | push 0 | [0]                 | —   | —      |
| 1 | 3       | pop 0 (1≤3), push 1 | [1]       | —   | —      |
| 2 | -1      | push 2 | [1,2]              | 3   | [3]    |
| 3 | -3      | remove expired? dq.front()=1, 1≤3-3=0? No. Push 3 | [1,2,3] | 3 | [3,3] |
| 4 | 5       | remove expired? 1≤4-3=1? Yes, pop 1. Pop 2(-1≤5), Pop 3(-3≤5). Push 4. | [4] | 5 | [3,3,5] |
| 5 | 3       | push 5 | [4,5]              | 5   | [3,3,5,5] |
| 6 | 6       | remove expired? 4≤6-3=3? No. Pop 5(3≤6). Push 6. | [4,6] | 6 | [3,3,5,5,6] |
| 7 | 7       | remove expired? 4≤7-3=4? Yes, pop 4. Pop 6(6≤7). Push 7. | [7] | 7 | [3,3,5,5,6,7] |

**Result: [3, 3, 5, 5, 6, 7]** ✓

### Why Each Element Is Processed O(1) Amortized

Each index enters the deque exactly once and is removed at most once. Even though there's a `while` loop, the total number of dequeue operations across all iterations is at most n. Therefore, the amortized cost per element is O(1), and the total time is O(n).

---

## 38.3 Sliding Window Minimum

The same approach works for minimum — just flip the comparison:

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> minSlidingWindow(vector<int>& nums, int k) {
    deque<int> dq;  // monotonic increasing: front = min
    vector<int> result;

    for (int i = 0; i < (int)nums.size(); i++) {
        // Remove expired
        if (!dq.empty() && dq.front() <= i - k) {
            dq.pop_front();
        }

        // Maintain increasing order — remove larger elements from back
        while (!dq.empty() && nums[dq.back()] >= nums[i]) {
            dq.pop_back();
        }

        dq.push_back(i);

        if (i >= k - 1) {
            result.push_back(nums[dq.front()]);
        }
    }
    return result;
}

int main() {
    vector<int> nums = {1, 3, -1, -3, 5, 3, 6, 7};
    int k = 3;

    vector<int> result = minSlidingWindow(nums, k);
    cout << "Sliding window minimums: ";
    for (int x : result) cout << x << " ";
    cout << "\n";
    // Output: -1 -3 -3 -3 3 3

    return 0;
}
```

---

## 38.4 Applications

### Application 1: Shortest Subarray with Sum at Least K (LeetCode 862)

This is a harder problem that combines prefix sums with a monotonic deque.

**Problem:** Find the shortest subarray with sum ≥ k. Return -1 if none exists.

**Approach:** Use prefix sums. We need `pref[j] - pref[i] >= k` where `j - i` is minimized. Maintain a deque of prefix sums in increasing order.

```cpp
#include <bits/stdc++.h>
using namespace std;

int shortestSubarray(vector<int>& nums, int k) {
    int n = nums.size();
    vector<long long> pref(n + 1, 0);
    for (int i = 0; i < n; i++) {
        pref[i + 1] = pref[i] + nums[i];
    }

    deque<int> dq;
    int result = n + 1;

    for (int i = 0; i <= n; i++) {
        // Try to find valid subarrays
        while (!dq.empty() && pref[i] - pref[dq.front()] >= k) {
            result = min(result, i - dq.front());
            dq.pop_front();
        }

        // Maintain increasing order of prefix sums
        while (!dq.empty() && pref[dq.back()] >= pref[i]) {
            dq.pop_back();
        }

        dq.push_back(i);
    }

    return result <= n ? result : -1;
}

int main() {
    vector<int> nums1 = {1};
    cout << shortestSubarray(nums1, 1) << "\n";  // Output: 1

    vector<int> nums2 = {1, 2};
    cout << shortestSubarray(nums2, 4) << "\n";  // Output: -1

    vector<int> nums3 = {2, -1, 2};
    cout << shortestSubarray(nums3, 3) << "\n";  // Output: 3

    return 0;
}
```

**Complexity:** O(n) time, O(n) space.

**Why monotonic deque works here:** By maintaining prefix sums in increasing order, when we find that `pref[i] - pref[dq.front()] >= k`, we know `dq.front()` is the earliest index with a small enough prefix sum, giving us the shortest subarray ending at `i`.

### Application 2: Constrained Subsequence Sum (LeetCode 1425)

**Problem:** Find the maximum sum of a subsequence where adjacent chosen elements are at most `k` indices apart.

**Approach:** Dynamic programming with monotonic queue. `dp[i] = nums[i] + max(0, max(dp[j]))` for `j` in `[i-k, i-1]`. Use a monotonic decreasing deque to maintain the window maximum of `dp` values.

```cpp
#include <bits/stdc++.h>
using namespace std;

int constrainedSubsetSum(vector<int>& nums, int k) {
    int n = nums.size();
    vector<int> dp(n);
    deque<int> dq;  // stores indices, front = index with max dp value

    int result = INT_MIN;

    for (int i = 0; i < n; i++) {
        // Remove expired indices
        while (!dq.empty() && dq.front() < i - k) {
            dq.pop_front();
        }

        // dp[i] = nums[i] + max(0, dp[dq.front()])
        dp[i] = nums[i];
        if (!dq.empty()) {
            dp[i] = max(dp[i], nums[i] + dp[dq.front()]);
        }

        // Maintain decreasing order of dp values
        while (!dq.empty() && dp[dq.back()] <= dp[i]) {
            dq.pop_back();
        }

        dq.push_back(i);
        result = max(result, dp[i]);
    }

    return result;
}

int main() {
    vector<int> nums = {10, 2, -10, 5, 20};
    cout << constrainedSubsetSum(nums, 2) << "\n";  // Output: 37
    // Subsequence: 10, 2, 5, 20 (indices 0,1,3,4)

    vector<int> nums2 = {-1, -2, -3};
    cout << constrainedSubsetSum(nums2, 1) << "\n";  // Output: -1

    return 0;
}
```

**Complexity:** O(n) time, O(n) space.

### Application 3: Jump Game VI (same as above)

This is the same problem as Constrained Subsequence Sum, confirming the pattern.

### Application 4: Longest Continuous Subarray with Absolute Diff ≤ Limit (LeetCode 1438)

**Problem:** Find the longest subarray where `max - min <= limit`.

**Approach:** Two monotonic deques — one for max (decreasing), one for min (increasing). Use a sliding window.

```cpp
#include <bits/stdc++.h>
using namespace std;

int longestSubarray(vector<int>& nums, int limit) {
    deque<int> maxDq, minDq;  // store indices
    int left = 0, result = 0;

    for (int right = 0; right < (int)nums.size(); right++) {
        // Maintain max deque (decreasing)
        while (!maxDq.empty() && nums[maxDq.back()] <= nums[right]) {
            maxDq.pop_back();
        }
        maxDq.push_back(right);

        // Maintain min deque (increasing)
        while (!minDq.empty() && nums[minDq.back()] >= nums[right]) {
            minDq.pop_back();
        }
        minDq.push_back(right);

        // Shrink window if diff exceeds limit
        while (nums[maxDq.front()] - nums[minDq.front()] > limit) {
            left++;
            if (maxDq.front() < left) maxDq.pop_front();
            if (minDq.front() < left) minDq.pop_front();
        }

        result = max(result, right - left + 1);
    }
    return result;
}

int main() {
    vector<int> nums = {8, 2, 4, 7};
    cout << longestSubarray(nums, 4) << "\n";  // Output: 2

    vector<int> nums2 = {10, 1, 2, 4, 7, 2};
    cout << longestSubarray(nums2, 5) << "\n";  // Output: 4

    return 0;
}
```

**Complexity:** O(n) time, O(n) space.

---

## 38.5 Monotonic Queue vs Monotonic Stack

| Feature | Monotonic Stack | Monotonic Queue |
|---------|----------------|-----------------|
| Underlying structure | `std::stack` | `std::deque` |
| Remove from front | ✗ | ✓ |
| Remove from back | ✓ | ✓ |
| Use case | Next/prev greater/smaller | Sliding window max/min |
| Typical problem | NGE, histogram, rain water | Sliding window maximum |

Both share the same amortized O(n) analysis because each element enters and leaves at most once.

---

## 38.6 Building a Monotonic Queue from Scratch

For educational purposes, here's a complete implementation:

```cpp
#include <bits/stdc++.h>
using namespace std;

template<typename T>
class MonotonicDecreasingQueue {
    deque<pair<T, int>> dq;  // {value, index}
    int currentIndex = 0;
public:
    void push(const T& value) {
        while (!dq.empty() && dq.back().first <= value) {
            dq.pop_back();
        }
        dq.push_back({value, currentIndex++});
    }

    T max() const {
        return dq.front().first;
    }

    void popExpired(int windowStart) {
        if (!dq.empty() && dq.front().second < windowStart) {
            dq.pop_front();
        }
    }

    bool empty() const {
        return dq.empty();
    }
};

int main() {
    MonotonicDecreasingQueue<int> mq;
    vector<int> nums = {1, 3, -1, -3, 5, 3, 6, 7};
    int k = 3;

    for (int i = 0; i < (int)nums.size(); i++) {
        mq.push(nums[i]);
        if (i >= k) {
            mq.popExpired(i - k + 1);
        }
        if (i >= k - 1) {
            cout << "Window [" << i-k+1 << "," << i << "] max = " << mq.max() << "\n";
        }
    }

    return 0;
}
```

---

## 38.7 Interview Tips

1. **Pattern recognition:** "Sliding window + maximum/minimum" → monotonic queue. This is the most common application.

2. **Store indices:** Always store indices in the deque, not values. You need indices to determine when elements expire (leave the window).

3. **Two deques for range queries:** When you need both max and min in a window (e.g., absolute difference problems), use two deques.

4. **Combine with DP:** Many DP problems where `dp[i] = nums[i] + max(dp[j])` for `j` in a sliding window can be optimized with a monotonic queue.

5. **Boundary condition:** The window is fully formed when `i >= k - 1`. Don't try to record results before that.

6. **Amortized analysis:** Be prepared to explain why the nested while loop doesn't make it O(n²). Each element is pushed and popped at most once.

---

## 38.8 Common Mistakes

1. **Storing values instead of indices:** Without indices, you can't determine when an element leaves the window.

2. **Wrong comparison for increasing vs decreasing:** Using `<=` when you need `>=` (or vice versa) breaks the monotonic property.

3. **Forgetting to remove expired elements:** Always check if the front element's index is still within the window before querying.

4. **Off-by-one in window boundaries:** `i - k + 1` is the start of the window ending at `i`. Be precise.

5. **Not handling empty deques:** If all elements in the window are the same, the deque might have only one element. Always check `empty()` before `front()` or `back()`.

6. **Using stack instead of deque:** A `std::stack` doesn't support `pop_front()`. You need `std::deque`.

---

## 38.9 Practice Problems

| # | Problem | Difficulty | Key Idea |
|---|---------|------------|----------|
| 1 | LeetCode 239 - Sliding Window Maximum | Hard | Classic monotonic queue |
| 2 | LeetCode 862 - Shortest Subarray with Sum ≥ K | Hard | Prefix sum + deque |
| 3 | LeetCode 1425 - Constrained Subsequence Sum | Hard | DP + monotonic queue |
| 4 | LeetCode 1438 - Longest Subarray With Abs Diff ≤ Limit | Medium | Two deques |
| 5 | LeetCode 1696 - Jump Game VI | Medium | DP + deque |
| 6 | LeetCode 2071 - Maximum Number of Tasks You Can Assign | Hard | Binary search + monotonic queue |
| 7 | LeetCode 1862 - Sum of Floored Pairs | Hard | Prefix sum + sliding window |
| 8 | LeetCode 2398 - Maximum Number of Robots Within Budget | Hard | Sliding window + deque |
| 9 | LeetCode 1562 - Find Latest Group of Size M | Medium | Sliding window |
| 10 | LeetCode 918 - Maximum Subarray Sum Circular | Medium | Sliding window min |

---

## 38.10 Summary

The monotonic queue is the natural extension of the monotonic stack to sliding window problems. The key ideas are:

- **Deque** allows removal from both ends (front for expiration, back for monotonicity).
- **Store indices** to track window boundaries.
- **Amortized O(n)**: each element pushed and popped at most once.
- **Combines with DP**: sliding window optimization for DP transitions.
- **Two deques** when you need both max and min simultaneously.

When you see "sliding window" and "maximum/minimum" in the same problem, reach for a monotonic queue. It's the difference between O(nk) and O(n).
