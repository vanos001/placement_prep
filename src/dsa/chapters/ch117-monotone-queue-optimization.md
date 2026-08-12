# Chapter 117: Monotone Queue Optimization

## Prerequisites
- Dynamic programming basics
- Monotonic deque / sliding window maximum
- Understanding of DP transitions and state spaces

## Interview Frequency: ★★

Monotone queue optimization speeds up certain DP problems from O(n²) to O(n) by exploiting the structure of the transition function. It's a specific case of the more general "convex hull trick" and is essential for competitive programming and optimization-heavy interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Sliding window min/max | ★★★ | Easy | Foundation technique |
| Monotone queue DP | ★★ | Medium | DP with windowed transitions |
| Convex hull trick | ★★ | Hard | Generalization |
| Divide and conquer optimization | ★★ | Hard | Related technique |
| Knuth's optimization | ★ | Hard | Special case |

---

## 117.1 Motivation: From O(n²) to O(n)

Consider this DP problem:

**Problem**: Given an array of n elements and a window size k, compute:
```
dp[i] = min(dp[j] + cost(j, i)) for j in [i-k, i-1]
```

**Naive approach**: For each i, check all j in the window → O(nk) time.

**Key insight**: If the optimal j is **monotone** (doesn't decrease as i increases), we can maintain a deque of candidates and avoid rechecking old values.

**When is this true?** When the cost function satisfies the **quadrangle inequality** or when we're simply finding the minimum dp[j] in a sliding window.

---

## 117.2 Foundation: Sliding Window Minimum

Before tackling DP, let's master the sliding window minimum problem.

### Problem

Given array A of size n and window size k, find the minimum in each window of size k.

### Naive: O(nk)

For each window, scan all k elements.

### Optimal: O(n) with Monotone Deque

Maintain a deque of indices where values are **increasing** (front = minimum).

**Algorithm**:
```
For each index i:
    1. Remove front if it's outside the window (index < i - k + 1)
    2. Remove from back while A[back] >= A[i] (maintain increasing order)
    3. Push i to back
    4. Front of deque = minimum of current window
```

### Why It Works

- **Step 2** removes elements that can never be the minimum (A[i] is smaller and more recent)
- The deque always has elements in increasing order
- Front is always the minimum of the current window

### Walkthrough

Array: [1, 3, -1, -3, 5, 3, 6, 7], k = 3

```
i=0: dq=[0] → window not full
i=1: dq=[0,1] → window not full (1,3)
i=2: remove back (A[1]=3 >= A[2]=-1), dq=[0,2] → min=1 (1,3,-1)
i=3: remove back (A[2]=-1 > A[3]=-3? No, -1 >= -3, so remove), dq=[3] 
     Wait, i-k+1=1, so index 0 is out. Remove front 0.
     Actually: A[2]=-1, A[3]=-3, -1 >= -3 → remove index 2
     Then check: A[0]=1, 1 >= -3 → remove index 0 (but 0 is already out of window)
     dq=[3] → min=-3 (-3,-3,5)
     
Let me redo this more carefully:

i=0: push 0. dq=[0]. Window [0,0] not full yet.
i=1: A[0]=1 < A[1]=3, don't remove. Push 1. dq=[0,1]. Window [0,1] not full.
i=2: Window starts at i-k+1=0. 
     A[1]=3 >= A[2]=-1 → pop back. dq=[0]. A[0]=1 >= -1 → pop back. dq=[].
     Push 2. dq=[2]. Output: A[2]=-1. Window [1,3,-1].
i=3: Window starts at 1. Index 2 is still in window.
     A[2]=-1 >= A[3]=-3 → pop back. dq=[]. Push 3. dq=[3]. Output: A[3]=-3. Window [3,-1,-3].
i=4: Window starts at 2. 
     A[3]=-3 < A[4]=5, don't remove. Push 4. dq=[3,4]. Output: A[3]=-3. Window [-1,-3,5].
i=5: Window starts at 3. Index 3 still in window.
     A[4]=5 >= A[5]=3 → pop back. dq=[3]. A[3]=-3 < 3, keep. Push 5. dq=[3,5].
     Output: A[3]=-3. Window [-3,5,3].
i=6: Window starts at 4. Index 3 is now out! Pop front. dq=[5].
     A[5]=3 < A[6]=6, keep. Push 6. dq=[5,6]. Output: A[5]=3. Window [5,3,6].
i=7: Window starts at 5. 
     A[6]=6 < A[7]=7, keep. Push 7. dq=[5,6,7]. Output: A[5]=3. Window [3,6,7].

Result: [-1, -3, -3, -3, -3, 3, 3]
```

---

## 117.3 Monotone Queue for DP

### Problem Pattern

```
dp[i] = min over j in [L(i), R(i)] of (dp[j] + cost(j, i))
```

where L(i) and R(i) define a sliding window.

### When Monotone Queue Applies

The monotone queue optimization works when:

1. **Window constraint**: The transition considers j in a sliding window [i-k, i-1]
2. **Monotone optimal**: The optimal j doesn't decrease as i increases
3. **Decomposable cost**: cost(j, i) can be split into parts depending on j and i separately

### Classic Example: Minimum Cost with Window

```
dp[i] = min(dp[j]) for j in [i-k, i-1] + arr[i]
```

This is the simplest case: find the minimum dp value in a window, then add arr[i].

### Walkthrough

Array: [1, 3, 2, 4, 1, 5, 2, 3], k = 3

```
dp[0] = arr[0] = 1
dq = [0]  (stores indices with increasing dp values)

i=1: Window [max(0,1-3)=0, 0]
     Front of dq = 0, dp[0] = 1
     dp[1] = dp[0] + arr[1] = 1 + 3 = 4
     While dp[back] >= dp[1]: dp[0]=1 < 4, keep
     Push 1. dq = [0, 1]

i=2: Window [max(0,2-3)=0, 1]
     Front = 0, dp[0] = 1
     dp[2] = dp[0] + arr[2] = 1 + 2 = 3
     While dp[back] >= dp[2]: dp[1]=4 >= 3, pop. dp[0]=1 < 3, keep.
     Push 2. dq = [0, 2]

i=3: Window [max(0,3-3)=0, 2]
     Front = 0, dp[0] = 1
     dp[3] = dp[0] + arr[3] = 1 + 4 = 5
     While dp[back] >= dp[3]: dp[2]=3 < 5, keep
     Push 3. dq = [0, 2, 3]

i=4: Window [1, 3]
     Front = 0, but 0 < 1 → pop front. dq = [2, 3]
     Front = 2, dp[2] = 3
     dp[4] = dp[2] + arr[4] = 3 + 1 = 4
     While dp[back] >= dp[4]: dp[3]=5 >= 4, pop. dp[2]=3 < 4, keep.
     Push 4. dq = [2, 4]

i=5: Window [2, 4]
     Front = 2, dp[2] = 3
     dp[5] = dp[2] + arr[5] = 3 + 5 = 8
     While dp[back] >= dp[5]: dp[4]=4 < 8, keep
     Push 5. dq = [2, 4, 5]

i=6: Window [3, 5]
     Front = 2, but 2 < 3 → pop front. dq = [4, 5]
     Front = 4, dp[4] = 4
     dp[6] = dp[4] + arr[6] = 4 + 2 = 6
     While dp[back] >= dp[6]: dp[5]=8 >= 6, pop. dp[4]=4 < 6, keep.
     Push 6. dq = [4, 6]

i=7: Window [4, 6]
     Front = 4, dp[4] = 4
     dp[7] = dp[4] + arr[7] = 4 + 3 = 7
     While dp[back] >= dp[7]: dp[6]=6 < 7, keep
     Push 7. dq = [4, 6, 7]

Final dp = [1, 4, 3, 5, 4, 8, 6, 7]
Answer: dp[7] = 7
```

---

## 117.4 More Complex: DP with Monotone Cost

When the cost function depends on both j and i, we need the cost to be separable:

```
dp[i] = min over j of (dp[j] + cost(j, i))
```

If cost(j, i) = f(j) + g(i) + cross(j, i), and cross(j, i) has certain monotonicity properties, the monotone queue can still work.

### Example: Minimum Cost with Quadratic Penalty

```
dp[i] = min over j in [0, i-1] of (dp[j] + (sum[i] - sum[j])²)
```

This doesn't have a sliding window, but the optimal j is monotone due to the convexity of the quadratic function. This is better handled by the **convex hull trick** (Chapter 118).

---

## 117.5 Sliding Window Maximum

The dual problem: find the maximum in each window.

### Algorithm

Same as sliding window minimum, but maintain a **decreasing** deque (front = maximum).

```
For each index i:
    1. Remove front if outside window
    2. Remove from back while A[back] <= A[i]
    3. Push i to back
    4. Front = maximum
```

---

## 117.6 Complexity Analysis

| Operation | Naive | Monotone Queue | Improvement |
|---|---|---|---|
| Sliding window min/max | O(nk) | O(n) | k× |
| DP with window | O(nk) | O(n) | k× |
| Sliding window median | O(nk) | O(n log k) | Depends |
| Sliding window sum | O(nk) | O(n) | k× |

**Amortized analysis**: Each element enters and leaves the deque at most once. Total operations: O(n) for n elements.

---

## 117.7 Code: Complete Implementations

### C++: Sliding Window + DP Optimization

```cpp
#include <iostream>
#include <vector>
#include <deque>
#include <climits>
#include <algorithm>

// ============================================================
// Sliding Window Minimum
// ============================================================
std::vector<int> slidingWindowMin(const std::vector<int>& arr, int k) {
    int n = arr.size();
    std::deque<int> dq; // Stores indices, front = minimum
    std::vector<int> result;

    for (int i = 0; i < n; i++) {
        // Remove elements outside window
        while (!dq.empty() && dq.front() < i - k + 1)
            dq.pop_front();

        // Maintain increasing order: remove larger elements from back
        while (!dq.empty() && arr[dq.back()] >= arr[i])
            dq.pop_back();

        dq.push_back(i);

        if (i >= k - 1)
            result.push_back(arr[dq.front()]);
    }
    return result;
}

// ============================================================
// Sliding Window Maximum
// ============================================================
std::vector<int> slidingWindowMax(const std::vector<int>& arr, int k) {
    int n = arr.size();
    std::deque<int> dq; // Stores indices, front = maximum
    std::vector<int> result;

    for (int i = 0; i < n; i++) {
        while (!dq.empty() && dq.front() < i - k + 1)
            dq.pop_front();

        // Maintain decreasing order: remove smaller elements from back
        while (!dq.empty() && arr[dq.back()] <= arr[i])
            dq.pop_back();

        dq.push_back(i);

        if (i >= k - 1)
            result.push_back(arr[dq.front()]);
    }
    return result;
}

// ============================================================
// DP with Monotone Queue: dp[i] = min(dp[j]) for j in [i-k, i-1] + arr[i]
// ============================================================
int minCostWithWindow(const std::vector<int>& arr, int k) {
    int n = arr.size();
    std::vector<int> dp(n, INT_MAX);
    dp[0] = arr[0];

    std::deque<int> dq; // Stores indices with increasing dp values
    dq.push_back(0);

    for (int i = 1; i < n; i++) {
        // Remove elements outside window [i-k, i-1]
        while (!dq.empty() && dq.front() < i - k)
            dq.pop_front();

        // dp[i] = min in window + arr[i]
        dp[i] = dp[dq.front()] + arr[i];

        // Maintain increasing dp order
        while (!dq.empty() && dp[dq.back()] >= dp[i])
            dq.pop_back();
        dq.push_back(i);
    }

    return dp[n - 1];
}

// ============================================================
// DP with Monotone Queue: dp[i] = min(dp[j] + cost) with custom cost
// Problem: Given array, partition into groups of size ≤ k,
//          cost of group [j+1, i] = max(arr[j+1..i])
//          minimize total cost
// ============================================================
int minPartitionCost(const std::vector<int>& arr, int k) {
    int n = arr.size();
    std::vector<int> dp(n + 1, INT_MAX);
    dp[0] = 0;

    std::deque<int> dq;
    dq.push_back(0);

    for (int i = 1; i <= n; i++) {
        // Remove elements outside window
        while (!dq.empty() && dq.front() < i - k)
            dq.pop_front();

        // dp[i] = min(dp[j] + max(arr[j..i-1])) for j in [i-k, i-1]
        // For this simplified version, we use dp[j] + arr[i-1]
        dp[i] = dp[dq.front()] + arr[i - 1];

        while (!dq.empty() && dp[dq.back()] >= dp[i])
            dq.pop_back();
        dq.push_back(i);
    }

    return dp[n];
}

// ============================================================
// Sliding Window Sum (prefix sum technique)
// ============================================================
std::vector<int> slidingWindowSum(const std::vector<int>& arr, int k) {
    int n = arr.size();
    std::vector<int> prefix(n + 1, 0);
    for (int i = 0; i < n; i++)
        prefix[i + 1] = prefix[i] + arr[i];

    std::vector<int> result;
    for (int i = k - 1; i < n; i++)
        result.push_back(prefix[i + 1] - prefix[i - k + 1]);
    return result;
}

// ============================================================
// Longest Subarray with Sum ≤ K (using monotone queue on prefix sums)
// ============================================================
int longestSubarraySumAtMostK(const std::vector<int>& arr, int k) {
    int n = arr.size();
    std::vector<int> prefix(n + 1, 0);
    for (int i = 0; i < n; i++)
        prefix[i + 1] = prefix[i] + arr[i];

    // For each i, find smallest j such that prefix[i] - prefix[j] <= k
    // Equivalently, prefix[j] >= prefix[i] - k
    // Use deque to maintain candidates
    std::deque<int> dq;
    int maxLen = 0;

    for (int i = 0; i <= n; i++) {
        // Remove elements that make sum > k
        while (!dq.empty() && prefix[i] - prefix[dq.front()] > k)
            dq.pop_front();

        if (!dq.empty())
            maxLen = std::max(maxLen, i - dq.front());

        // Maintain increasing prefix sums
        while (!dq.empty() && prefix[dq.back()] >= prefix[i])
            dq.pop_back();
        dq.push_back(i);
    }

    return maxLen;
}

int main() {
    std::vector<int> arr = {1, 3, -1, -3, 5, 3, 6, 7};
    int k = 3;

    // Sliding window min/max
    auto mins = slidingWindowMin(arr, k);
    auto maxs = slidingWindowMax(arr, k);

    std::cout << "Array: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\nSliding window min (k=" << k << "): ";
    for (int x : mins) std::cout << x << " ";
    std::cout << "\nSliding window max (k=" << k << "): ";
    for (int x : maxs) std::cout << x << " ";
    std::cout << "\n";

    // DP with window
    std::vector<int> costs = {1, 3, 2, 4, 1, 5, 2, 3};
    std::cout << "\nDP with window:\n";
    std::cout << "  Costs: ";
    for (int x : costs) std::cout << x << " ";
    std::cout << "\n  Min cost (k=3): " << minCostWithWindow(costs, 3) << "\n";

    // Sliding window sum
    auto sums = slidingWindowSum(arr, k);
    std::cout << "\nSliding window sum (k=" << k << "): ";
    for (int x : sums) std::cout << x << " ";
    std::cout << "\n";

    // Longest subarray with sum <= K
    std::vector<int> data = {1, 2, 3, 4, 5};
    std::cout << "\nLongest subarray with sum <= 9: "
              << longestSubarraySumAtMostK(data, 9) << "\n";

    return 0;
}
```

### Python: Complete Monotone Queue Toolkit

```python
from collections import deque
from typing import List


def sliding_window_min(arr: List[int], k: int) -> List[int]:
    """Find minimum in each window of size k. O(n)"""
    n = len(arr)
    dq = deque()  # Stores indices, front = minimum
    result = []

    for i in range(n):
        # Remove elements outside window
        while dq and dq[0] < i - k + 1:
            dq.popleft()

        # Maintain increasing order
        while dq and arr[dq[-1]] >= arr[i]:
            dq.pop()

        dq.append(i)

        if i >= k - 1:
            result.append(arr[dq[0]])

    return result


def sliding_window_max(arr: List[int], k: int) -> List[int]:
    """Find maximum in each window of size k. O(n)"""
    n = len(arr)
    dq = deque()  # Stores indices, front = maximum
    result = []

    for i in range(n):
        while dq and dq[0] < i - k + 1:
            dq.popleft()

        # Maintain decreasing order
        while dq and arr[dq[-1]] <= arr[i]:
            dq.pop()

        dq.append(i)

        if i >= k - 1:
            result.append(arr[dq[0]])

    return result


def sliding_window_sum(arr: List[int], k: int) -> List[int]:
    """Sum of each window of size k using prefix sums. O(n)"""
    n = len(arr)
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + arr[i]

    return [prefix[i + k] - prefix[i] for i in range(n - k + 1)]


def dp_with_window(arr: List[int], k: int) -> int:
    """DP: dp[i] = min(dp[j]) for j in [i-k, i-1] + arr[i]. O(n)"""
    n = len(arr)
    dp = [float('inf')] * n
    dp[0] = arr[0]

    dq = deque([0])  # Indices with increasing dp values

    for i in range(1, n):
        # Remove elements outside window
        while dq and dq[0] < i - k:
            dq.popleft()

        # dp[i] = min in window + arr[i]
        dp[i] = dp[dq[0]] + arr[i]

        # Maintain increasing dp order
        while dq and dp[dq[-1]] >= dp[i]:
            dq.pop()
        dq.append(i)

    return dp[-1]


def min_cost_partition(arr: List[int], k: int) -> int:
    """Partition array into groups of size ≤ k.
    Cost of each group = max element. Minimize total cost. O(n)"""
    n = len(arr)
    dp = [float('inf')] * (n + 1)
    dp[0] = 0

    # For each group ending at i, we need min(dp[j]) for j in [i-k, i-1]
    # Then dp[i] = min(dp[j]) + max(arr[j..i-1])
    # This requires tracking both min dp and max arr in the window

    dq_min = deque()  # For dp values (increasing)
    dq_max = deque()  # For arr values (decreasing)
    dq_min.append(0)

    for i in range(1, n + 1):
        # Remove elements outside window
        while dq_min and dq_min[0] < i - k:
            dq_min.popleft()
        while dq_max and dq_max[0] < i - k:
            dq_max.popleft()

        # Update max deque for current element
        while dq_max and arr[dq_max[-1]] <= arr[i - 1]:
            dq_max.pop()
        dq_max.append(i - 1)

        # dp[i] = min(dp[j]) + max(arr[j..i-1])
        dp[i] = dp[dq_min[0]] + arr[dq_max[0]]

        # Maintain increasing dp order
        while dq_min and dp[dq_min[-1]] >= dp[i]:
            dq_min.pop()
        dq_min.append(i)

    return dp[n]


def longest_subarray_sum_at_most_k(arr: List[int], k: int) -> int:
    """Find longest subarray with sum ≤ k. O(n)"""
    n = len(arr)
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + arr[i]

    dq = deque()
    max_len = 0

    for i in range(n + 1):
        # Remove elements that make sum > k
        while dq and prefix[i] - prefix[dq[0]] > k:
            dq.popleft()

        if dq:
            max_len = max(max_len, i - dq[0])

        # Maintain increasing prefix sums
        while dq and prefix[dq[-1]] >= prefix[i]:
            dq.pop()
        dq.append(i)

    return max_len


def max_sliding_window_sum_with_negatives(arr: List[int], k: int) -> int:
    """Find maximum sum of any subarray of length ≤ k. O(n)"""
    n = len(arr)
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + arr[i]

    dq = deque()
    max_sum = float('-inf')

    for i in range(n + 1):
        # For each i, find min prefix[j] for j in [i-k, i]
        while dq and dq[0] < i - k:
            dq.popleft()

        if dq:
            max_sum = max(max_sum, prefix[i] - prefix[dq[0]])

        # Maintain increasing prefix sums
        while dq and prefix[dq[-1]] >= prefix[i]:
            dq.pop()
        dq.append(i)

    return max_sum


def demo():
    arr = [1, 3, -1, -3, 5, 3, 6, 7]
    k = 3

    print("Array:", arr)
    print(f"Sliding window min (k={k}):", sliding_window_min(arr, k))
    print(f"Sliding window max (k={k}):", sliding_window_max(arr, k))
    print(f"Sliding window sum (k={k}):", sliding_window_sum(arr, k))

    costs = [1, 3, 2, 4, 1, 5, 2, 3]
    print(f"\nDP with window: costs={costs}, k=3")
    print(f"  Min cost: {dp_with_window(costs, 3)}")

    data = [1, 2, 3, 4, 5]
    print(f"\nLongest subarray with sum <= 9 in {data}: {longest_subarray_sum_at_most_k(data, 9)}")

    arr2 = [2, 1, -3, 4, -1, 2, 1, -5, 4]
    print(f"\nMax subarray sum with length <= 3 in {arr2}: {max_sliding_window_sum_with_negatives(arr2, 3)}")


if __name__ == "__main__":
    demo()
```

### Java: Monotone Queue Implementations

```java
import java.util.*;

public class MonotoneQueueOptimization {

    // Sliding Window Minimum
    public static int[] slidingWindowMin(int[] arr, int k) {
        int n = arr.length;
        Deque<Integer> dq = new ArrayDeque<>();
        int[] result = new int[n - k + 1];
        int idx = 0;

        for (int i = 0; i < n; i++) {
            while (!dq.isEmpty() && dq.peekFirst() < i - k + 1)
                dq.pollFirst();
            while (!dq.isEmpty() && arr[dq.peekLast()] >= arr[i])
                dq.pollLast();
            dq.offerLast(i);
            if (i >= k - 1)
                result[idx++] = arr[dq.peekFirst()];
        }
        return result;
    }

    // Sliding Window Maximum
    public static int[] slidingWindowMax(int[] arr, int k) {
        int n = arr.length;
        Deque<Integer> dq = new ArrayDeque<>();
        int[] result = new int[n - k + 1];
        int idx = 0;

        for (int i = 0; i < n; i++) {
            while (!dq.isEmpty() && dq.peekFirst() < i - k + 1)
                dq.pollFirst();
            while (!dq.isEmpty() && arr[dq.peekLast()] <= arr[i])
                dq.pollLast();
            dq.offerLast(i);
            if (i >= k - 1)
                result[idx++] = arr[dq.peekFirst()];
        }
        return result;
    }

    // DP with Monotone Queue
    public static int dpWithWindow(int[] arr, int k) {
        int n = arr.length;
        int[] dp = new int[n];
        Arrays.fill(dp, Integer.MAX_VALUE);
        dp[0] = arr[0];

        Deque<Integer> dq = new ArrayDeque<>();
        dq.offerLast(0);

        for (int i = 1; i < n; i++) {
            while (!dq.isEmpty() && dq.peekFirst() < i - k)
                dq.pollFirst();

            dp[i] = dp[dq.peekFirst()] + arr[i];

            while (!dq.isEmpty() && dp[dq.peekLast()] >= dp[i])
                dq.pollLast();
            dq.offerLast(i);
        }

        return dp[n - 1];
    }

    // Sliding Window Sum using Prefix Sums
    public static int[] slidingWindowSum(int[] arr, int k) {
        int n = arr.length;
        int[] prefix = new int[n + 1];
        for (int i = 0; i < n; i++)
            prefix[i + 1] = prefix[i] + arr[i];

        int[] result = new int[n - k + 1];
        for (int i = 0; i <= n - k; i++)
            result[i] = prefix[i + k] - prefix[i];
        return result;
    }

    // Longest Subarray with Sum <= K
    public static int longestSubarraySumAtMostK(int[] arr, int k) {
        int n = arr.length;
        int[] prefix = new int[n + 1];
        for (int i = 0; i < n; i++)
            prefix[i + 1] = prefix[i] + arr[i];

        Deque<Integer> dq = new ArrayDeque<>();
        int maxLen = 0;

        for (int i = 0; i <= n; i++) {
            while (!dq.isEmpty() && prefix[i] - prefix[dq.peekFirst()] > k)
                dq.pollFirst();

            if (!dq.isEmpty())
                maxLen = Math.max(maxLen, i - dq.peekFirst());

            while (!dq.isEmpty() && prefix[dq.peekLast()] >= prefix[i])
                dq.pollLast();
            dq.offerLast(i);
        }

        return maxLen;
    }

    public static void main(String[] args) {
        int[] arr = {1, 3, -1, -3, 5, 3, 6, 7};
        int k = 3;

        System.out.println("Array: " + Arrays.toString(arr));
        System.out.println("Sliding window min: " + Arrays.toString(slidingWindowMin(arr, k)));
        System.out.println("Sliding window max: " + Arrays.toString(slidingWindowMax(arr, k)));
        System.out.println("Sliding window sum: " + Arrays.toString(slidingWindowSum(arr, k)));

        int[] costs = {1, 3, 2, 4, 1, 5, 2, 3};
        System.out.println("\nDP with window (k=3): " + dpWithWindow(costs, 3));

        int[] data = {1, 2, 3, 4, 5};
        System.out.println("Longest subarray sum <= 9: " + longestSubarraySumAtMostK(data, 9));
    }
}
```

---

## 117.8 Applications

| Application | Problem | Technique |
|---|---|---|
| Stock trading | Max profit in k-day window | Sliding window max |
| Task scheduling | Min cost with deadline | DP + monotone queue |
| Signal processing | Moving average/filter | Sliding window sum |
| Image processing | Morphological operations | 2D sliding window |
| Text processing | Longest valid substring | Monotone queue on prefix |
| Network analysis | Traffic in time window | Sliding window aggregation |
| Competitive programming | Partition DP | Monotone queue optimization |

---

## 117.9 Related Optimizations

### Convex Hull Trick (CHT)

When cost(j, i) is of the form `m_j * x_i + b_j`:
```
dp[i] = min over j of (m_j * x_i + b_j)
```

Each j defines a line; the minimum at x_i is on the lower convex hull.

### Divide and Conquer Optimization

When the optimal j for dp[i][k] satisfies:
```
opt[i][k] ≤ opt[i+1][k]
```

Use divide and conquer to compute dp in O(n log n) per layer.

### Knuth's Optimization

When cost satisfies the quadrangle inequality:
```
cost(a, c) + cost(b, d) ≤ cost(a, d) + cost(b, c) for a ≤ b ≤ c ≤ d
```

Then opt[i][j-1] ≤ opt[i][j] ≤ opt[i+1][j], enabling O(n²) instead of O(n³).

---

## 117.10 Exercises

### Conceptual Exercises

1. **Prove** that each element enters and leaves the monotone deque at most once, establishing the O(n) amortized bound.

2. **Explain** why the sliding window minimum algorithm maintains a deque with increasing values (not decreasing).

3. **Show** that the monotone queue optimization applies when the transition is `dp[i] = min(dp[j] + c * (i - j))` for j in a window.

4. **Compare** monotone queue optimization with the convex hull trick. When would you use each?

### Coding Exercises

5. **Implement** a sliding window median using two heaps (not monotone queue, but related).

6. **Solve** the "Trapping Rain Water" problem using a monotone stack (related technique).

7. **Implement** a 2D sliding window minimum (min in each k×k submatrix).

8. **Solve** this DP problem: Given n tasks with costs and a window constraint, minimize total cost with at most k tasks per window.

### Challenge Exercises

9. **Prove** that the DP with monotone queue gives correct answers when the cost function satisfies the quadrangle inequality.

10. **Design** a monotone queue that supports both minimum and maximum queries simultaneously.

---

## 117.11 Interview Questions

### Conceptual Questions

1. **Q**: What's the difference between a monotone queue and a regular queue?
   **A**: A monotone queue maintains elements in sorted order (by value, not insertion time). Elements are removed from the back when a better (smaller/larger) element arrives. This ensures the front is always the optimal value.

2. **Q**: When can you use monotone queue optimization for DP?
   **A**: When: (1) the transition considers a sliding window of previous states, (2) the optimal previous state is monotone, (3) the cost function is separable or has monotonicity properties.

3. **Q**: How does monotone queue compare to segment tree for sliding window queries?
   **A**: Monotone queue: O(1) amortized per element, simpler code, works for min/max. Segment tree: O(log k) per query, works for any associative operation (sum, gcd, etc.).

### Implementation Questions

4. **Q**: Implement sliding window maximum in O(n).
   **A**: Use a deque storing indices in decreasing order of values. For each element: remove out-of-window indices from front, remove smaller elements from back, push current index. Front = maximum.

5. **Q**: How would you handle the case where the window size varies (not fixed k)?
   **A**: The same monotone queue works. Just adjust the window boundary check: instead of `i - k + 1`, use the actual left boundary of each window.

### Systems Questions

6. **Q**: How would you use sliding window techniques for real-time monitoring?
   **A**: Maintain a deque for the last N data points. For each new data point: update deque (O(1) amortized), extract min/max/sum. Use for anomaly detection (value > 3σ from window average), rate limiting (count in window), etc.

---

## 117.12 Cross-References

- **Chapter 11 (Stacks and Queues)**: Deque fundamentals
- **Chapter 112 (Heap)**: Alternative for sliding window median
- **Chapter 116 (Dynamic Programming)**: DP fundamentals
- **Chapter 118 (Convex Hull Trick)**: Generalization for linear cost functions
- **Chapter 119 (Divide and Conquer Optimization)**: Related DP optimization
- **Chapter 120 (Knuth's Optimization)**: Quadrangle inequality optimization

---

## Summary

| Pattern | Time | Key Idea | When to Use |
|---|---|---|---|
| Sliding window min/max | O(n) | Decreasing/increasing deque | Fixed window, min/max |
| Sliding window sum | O(n) | Prefix sums | Fixed window, sum |
| Monotone queue DP | O(n) | Deque of DP candidates | Windowed transitions |
| Convex hull trick | O(n log n) or O(n) | Lines on convex hull | Linear cost in i |
| D&C optimization | O(n log n) | Monotone opt point | Quadrangle inequality |

**Key Takeaway**: The monotone queue is a simple but powerful technique that exploits the structure of sliding window problems. By maintaining elements in sorted order with a deque, we achieve O(1) amortized operations. The key insight is that elements that are "dominated" (worse than a newer element) can be safely discarded. This principle extends to DP optimization and is the foundation for more advanced techniques like the convex hull trick.
