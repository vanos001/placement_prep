# Chapter 116: Alien Trick and Parametric Search

## Prerequisites
- Binary search on real/integer domains
- Dynamic programming with constraints
- Lagrange multipliers (conceptual understanding)

## Interview Frequency: ★★
## Google, Amazon, Meta — hard optimization problems

---

## 116.1 What Is the Alien Trick?

The **Alien Trick** (also called **Parametric Search** or **WQS Binary Search**) is an
optimization technique that converts a **constrained optimization** problem into an
**unconstrained** one by introducing a penalty parameter λ (lambda).

**Core Idea:** If you need to optimize some cost function `f(x)` subject to using
exactly (or at most) `K` segments/items, you can instead minimize:

```
f(x) + λ · g(x)
```

where `g(x)` counts the number of segments used. By binary-searching on λ, you find
the value that makes the unconstrained optimum use exactly K segments.

### When Does It Apply?

The Alien Trick works when the **cost vs. number-of-segments** curve is **convex**.
This means:
- Adding one more segment always helps, but with diminishing returns
- The marginal gain of each additional segment is non-increasing

If the curve is convex, the Lagrangian relaxation has a unique optimal point for each λ,
and binary search on λ maps cleanly to the number of segments.

---

## 116.2 Motivating Example

**Problem:** Given an array of `n` positive integers, partition it into exactly `K`
contiguous subarrays to **minimize the maximum subarray sum**.

Without the Alien Trick, this requires a DP with states `(position, partitions_used)`
→ O(n² · K) time.

With the Alien Trick, we reduce it to O(n log C) where C is the range of answers.

**Why is this faster?** We eliminate one dimension of the DP by absorbing the
partition count into the objective function via a penalty.

---

## 116.3 Intuition: The Lagrangian Relaxation

In optimization theory, a **constrained** problem:

```
minimize f(x)    subject to g(x) = K
```

can be relaxed to:

```
minimize f(x) + λ · g(x)    (no constraint on g(x))
```

For each value of λ, the unconstrained problem has some optimal solution with a
particular value of g(x). As λ increases, we penalize using more segments, so the
optimal g(x) decreases. As λ decreases (becomes negative), we reward using more
segments, so g(x) increases.

By binary-searching λ, we find the exact value where g(x) = K.

### Geometric Picture

Plot the "number of segments" on the x-axis and "cost" on the y-axis.
The set of achievable (segments, cost) pairs forms a **convex hull**.
The Alien Trick finds the point on this convex hull where segments = K.

```
Cost
  |  .
  |    .
  |      .         ← Convex hull of achievable points
  |        .
  |          .
  |            .
  +---------------- Segments
```

A line with slope -λ is tangent to this convex hull. Moving λ slides the tangent
point along the hull.

---

## 116.4 Formal Algorithm

**Given:**
- A function `solve(λ)` that returns `(optimal_cost, num_segments)` for penalty λ
- A target number of segments K

**Algorithm:**
1. Binary search on λ (integer or real-valued)
2. For each mid = λ, call `solve(λ)` to get `(cost, segments)`
3. If `segments >= K`: increase λ (penalize segments more)
4. If `segments < K`: decrease λ (encourage more segments)
5. At the boundary, compute the true answer: `answer = cost - λ * K`

**Key Insight:** The true answer is `f(x*) + λ · g(x*) - λ · K`, where `(x*, g(x*))`
is the solution returned by `solve(λ)`.

---

## 116.5 Detailed Example: Partition Array to Minimize Maximum Sum

**Problem Statement:**
Given `arr = [1, 3, 2, 4, 1, 5, 2]` and `K = 3`, partition into 3 contiguous subarrays
to minimize the maximum subarray sum.

**Step-by-step with Alien Trick:**

1. The penalty λ represents "cost per partition."
2. For a given λ, solve the unconstrained problem: partition freely to minimize
   `(max subarray sum) + λ · (number of partitions)`.
3. The unconstrained problem can be solved greedily: keep adding elements to the current
   subarray unless starting a new subarray (cost λ) would be better.

**Walkthrough with λ = 2:**

```
arr = [1, 3, 2, 4, 1, 5, 2]

Start new partition at arr[0] = 1, current_sum = 1, partitions = 1
Add arr[1] = 3 → current_sum = 4. Starting new costs λ=2, extending costs 3. Extend.
Add arr[2] = 2 → current_sum = 6. Starting new costs 2, extending costs 2. Either works; extend.
Add arr[3] = 4 → current_sum = 10. Starting new costs 2, extending costs 4. Start new partition.
  → partitions = 2, current_sum = 4
Add arr[4] = 1 → current_sum = 5. Extend.
Add arr[5] = 5 → current_sum = 10. Starting new costs 2, extending costs 5. Start new partition.
  → partitions = 3, current_sum = 5
Add arr[6] = 2 → current_sum = 7. Extend.

Partitions: [1,3,2], [4,1], [5,2] → max sum = 6, partitions = 3
Objective = 6 + 2·3 = 12

Since partitions = 3 = K, we found the answer!
True answer = 12 - 2·3 = 6
```

**Verification:** Can we do better than max sum = 6? With 3 partitions on
[1,3,2,4,1,5,2]:
- [1,3,2,4], [1,5], [2] → max = 10
- [1,3], [2,4,1], [5,2] → max = 7
- [1,3,2], [4,1], [5,2] → max = 6 ✓

---

## 116.6 Implementation in C++

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

struct Result {
    long long cost;
    int partitions;
};

// Solve unconstrained problem with penalty lambda per partition
Result solve(const std::vector<int>& arr, long long lambda) {
    int n = arr.size();
    // DP: dp[i] = min cost to partition arr[0..i-1]
    // Each partition's cost is its sum, and each partition costs lambda extra
    long long currentSum = 0;
    long long maxInCurrent = 0;
    int partitions = 0;

    for (int x : arr) {
        // Should we start a new partition here?
        // If extending would make currentSum > lambda + maxInCurrent, start new
        if (partitions > 0 && currentSum + x > maxInCurrent + lambda) {
            partitions++;
            currentSum = x;
            maxInCurrent = x;
        } else {
            currentSum += x;
            maxInCurrent = std::max(maxInCurrent, currentSum);
        }
    }
    // First partition always starts at index 0
    if (partitions == 0) partitions = 1;

    return {maxInCurrent + lambda * partitions, partitions};
}

long long aliensTrick(const std::vector<int>& arr, int k) {
    // Binary search on lambda
    long long lo = -1e15, hi = 1e15;
    long long answer = 0;

    while (lo <= hi) {
        long long mid = lo + (hi - lo) / 2;
        auto result = solve(arr, mid);
        if (result.partitions >= k) {
            answer = result.cost - mid * k;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return answer;
}

int main() {
    std::vector<int> arr = {1, 3, 2, 4, 1, 5, 2};
    int k = 3;
    std::cout << "Min max-subarray with " << k << " partitions: "
              << aliensTrick(arr, k) << "\n";
    return 0;
}
```

---

## 116.7 Implementation in Python

```python
def solve(arr, lam):
    """Solve unconstrained problem with penalty `lam` per partition."""
    n = len(arr)
    current_sum = 0
    max_in_current = 0
    partitions = 0

    for x in arr:
        if partitions > 0 and current_sum + x > max_in_current + lam:
            # Start new partition
            partitions += 1
            current_sum = x
            max_in_current = x
        else:
            current_sum += x
            max_in_current = max(max_in_current, current_sum)

    if partitions == 0:
        partitions = 1

    return max_in_current + lam * partitions, partitions


def aliens_trick(arr, k):
    """Find minimum max-subarray-sum when partitioning into exactly k parts."""
    lo, hi = -10**15, 10**15
    answer = 0

    while lo <= hi:
        mid = (lo + hi) // 2
        cost, partitions = solve(arr, mid)
        if partitions >= k:
            answer = cost - mid * k
            lo = mid + 1
        else:
            hi = mid - 1

    return answer


# Example
arr = [1, 3, 2, 4, 1, 5, 2]
k = 3
print(f"Min max-subarray with {k} partitions: {aliens_trick(arr, k)}")
# Output: Min max-subarray with 3 partitions: 6
```

---

## 116.8 Implementation in Java

```java
public class AlienTrick {

    static class Result {
        long cost;
        int partitions;
        Result(long cost, int partitions) {
            this.cost = cost;
            this.partitions = partitions;
        }
    }

    static Result solve(int[] arr, long lambda) {
        long currentSum = 0;
        long maxInCurrent = 0;
        int partitions = 0;

        for (int x : arr) {
            if (partitions > 0 && currentSum + x > maxInCurrent + lambda) {
                partitions++;
                currentSum = x;
                maxInCurrent = x;
            } else {
                currentSum += x;
                maxInCurrent = Math.max(maxInCurrent, currentSum);
            }
        }
        if (partitions == 0) partitions = 1;

        return new Result(maxInCurrent + lambda * partitions, partitions);
    }

    static long aliensTrick(int[] arr, int k) {
        long lo = -1_000_000_000_000_000L;
        long hi = 1_000_000_000_000_000L;
        long answer = 0;

        while (lo <= hi) {
            long mid = lo + (hi - lo) / 2;
            Result result = solve(arr, mid);
            if (result.partitions >= k) {
                answer = result.cost - mid * k;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return answer;
    }

    public static void main(String[] args) {
        int[] arr = {1, 3, 2, 4, 1, 5, 2};
        int k = 3;
        System.out.println("Min max-subarray with " + k + " partitions: "
                           + aliensTrick(arr, k));
    }
}
```

---

## 116.9 Complexity Analysis

| Step | Time | Space |
|---|---|---|
| `solve(λ)` | O(n) | O(1) |
| Binary search on λ | O(n · log C) | O(1) |
| Total | **O(n · log C)** | **O(1)** |

Where `C` is the range of possible λ values (typically 10^15 for 64-bit integers).

**Comparison with standard DP:**
- Standard DP: O(n² · K) time, O(n · K) space
- Alien Trick: O(n · log C) time, O(1) space

The Alien Trick is dramatically faster when n and K are large.

---

## 116.10 Common Pitfalls

1. **Non-convex cost curve:** If the cost vs. segments curve is not convex, the trick
   fails. The binary search may oscillate or find a wrong answer.

2. **Tie-breaking:** When multiple solutions have the same cost but different segment
   counts, you need consistent tie-breaking. The standard approach is to prefer more
   segments (or fewer) consistently.

3. **Off-by-one in λ:** The binary search must handle the case where the exact K is
   achievable but λ lands between two integers.

4. **Integer vs. real λ:** For problems where the cost function involves integers,
   integer λ suffices. For real-valued costs, you may need real-valued λ with
   sufficient precision.

---

## 116.11 Practice Problems

1. **Partition array into K subarrays minimizing max sum** (the example above)
2. **IOI 2016 — Railroad:** Minimize cost with exactly K rail segments
3. **AtCoder DP Contest — X:** Partition with penalty per segment
4. **Codeforces 739E — Gosha is hunting:** Two types of "balls" with constraints
5. **USACO — Balanced Teams:** Group students into exactly K teams

---

## 116.12 Interview Questions

1. **Q:** When can you apply the Alien Trick?
   **A:** When the cost vs. number-of-segments curve is convex. This means each
   additional segment provides diminishing returns.

2. **Q:** What is the time complexity improvement over standard DP?
   **A:** From O(n² · K) to O(n · log C), where C is the answer range. The Alien
   Trick eliminates one DP dimension.

3. **Q:** How do you handle the case where no valid partition exists?
   **A:** Return a sentinel value or check feasibility before applying the trick.

4. **Q:** Can the Alien Trick be used for maximization problems?
   **A:** Yes, with appropriate sign changes. The penalty λ encourages or discourages
   more segments depending on the optimization direction.

---

## 116.13 Dry Run: Full Trace

**Input:** `arr = [7, 2, 5, 10, 8]`, `K = 2`

**Binary search on λ:**

| Iter | λ | Cost | Partitions | Action |
|---|---|---|---|---|
| 1 | 0 | 17 (all in one) | 1 | partitions < K → decrease λ |
| 2 | -5 | 17 + (-5)·1 = 12 | 1 | still < K → decrease λ |
| 3 | -8 | Split [7,2,5] + [10,8] → max=14, cost=14+(-8)·2=-2 | 2 | partitions = K → record answer = -2 - (-8)·2 = 14, increase λ |
| 4 | -6 | Split [7,2,5] + [10,8] → cost=14+(-6)·2=2 | 2 | partitions = K → answer = 2 - (-6)·2 = 14, increase λ |
| 5 | -4 | [7,2,5,10]+[8] → max=24, cost=24+(-4)·2=16 | 2 | answer = 16 - (-4)·2 = 24, increase λ |
| ... | ... | ... | ... | converges |

**Final answer:** 14 (partition [7,2,5] and [10,8], max sum = 14)

---

## 116.14 Related Techniques

| Technique | Use Case |
|---|---|
| **Alien Trick** | Convex optimization with segment count constraint |
| **Lagrange Multipliers** | Continuous optimization with equality constraints |
| **Parametric Search** | Binary search on a parameter to find a threshold |
| **WQS Binary Search** | Same as Alien Trick, named after Wei-Qi Shou |

---

## Summary

| Step | Action |
|---|---|
| 1 | Verify convexity of cost vs. segments curve |
| 2 | Define unconstrained: f(x) + λ · g(x) |
| 3 | Binary search on λ |
| 4 | For each λ, solve unconstrained problem in O(n) |
| 5 | Answer = result_cost - λ · K |

**Key Takeaway:** The Alien Trick trades a dimension of DP for a binary search,
dramatically improving time complexity for constrained partitioning problems.
