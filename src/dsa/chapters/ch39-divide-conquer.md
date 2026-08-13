# Chapter 39: Divide and Conquer

Divide and conquer is one of the most fundamental algorithm design paradigms. It breaks a problem into smaller subproblems, solves them recursively, and combines the results. This chapter revisits classic algorithms through the divide-and-conquer lens and introduces powerful applications like counting inversions and the closest pair of points.

---

## 39.1 The Paradigm

Every divide-and-conquer algorithm follows three steps:

1. **Divide:** Split the problem into smaller subproblems of the same type.
2. **Conquer:** Solve each subproblem recursively. If the subproblem is small enough, solve it directly (base case).
3. **Combine:** Merge the solutions of the subproblems into the solution for the original problem.

### General Structure

```
function solve(problem):
    if problem is small enough:
        return base_case(problem)
    
    subproblems = divide(problem)
    solutions = [solve(sub) for sub in subproblems]
    return combine(solutions)
```

### Why Divide and Conquer?

- **Efficiency:** Many divide-and-conquer algorithms achieve O(n log n) time, beating brute-force O(n²).
- **Parallelism:** Subproblems are independent and can be solved in parallel.
- **Elegant recursion:** The recursive structure often leads to clean, readable code.

### When to Use It

- The problem can be broken into independent subproblems of the same type.
- Subproblem solutions can be combined efficiently.
- The problem has a natural recursive structure (e.g., sorting, searching, geometric problems).

---

## 39.2 Merge Sort Revisited

Merge sort is the quintessential divide-and-conquer algorithm. Let's implement it with careful attention to the details.

### Algorithm

1. **Divide:** Split the array into two halves.
2. **Conquer:** Recursively sort each half.
3. **Combine:** Merge the two sorted halves into one sorted array.

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

void merge(vector<int>& arr, int left, int mid, int right) {
    // Create temporary arrays
    vector<int> L(arr.begin() + left, arr.begin() + mid + 1);
    vector<int> R(arr.begin() + mid + 1, arr.begin() + right + 1);

    int i = 0, j = 0, k = left;

    // Merge back into arr[left..right]
    while (i < (int)L.size() && j < (int)R.size()) {
        if (L[i] <= R[j]) {
            arr[k++] = L[i++];
        } else {
            arr[k++] = R[j++];
        }
    }

    // Copy remaining elements
    while (i < (int)L.size()) arr[k++] = L[i++];
    while (j < (int)R.size()) arr[k++] = R[j++];
}

void mergeSort(vector<int>& arr, int left, int right) {
    if (left >= right) return;

    int mid = left + (right - left) / 2;
    mergeSort(arr, left, mid);
    mergeSort(arr, mid + 1, right);
    merge(arr, left, mid, right);
}

int main() {
    vector<int> arr = {38, 27, 43, 3, 9, 82, 10};

    cout << "Before: ";
    for (int x : arr) cout << x << " ";
    cout << "\n";

    mergeSort(arr, 0, arr.size() - 1);

    cout << "After:  ";
    for (int x : arr) cout << x << " ";
    cout << "\n";
    // Output: 3 9 10 27 38 43 82

    return 0;
}
```

### Complexity Analysis

**Time:** T(n) = 2T(n/2) + O(n) → O(n log n) by the Master Theorem.

- The array is halved at each level → log n levels.
- At each level, merging takes O(n) total work.
- Total: O(n log n).

**Space:** O(n) for the temporary arrays during merge.

**Stability:** Merge sort is stable because we use `L[i] <= R[j]` (not `<`), preserving the relative order of equal elements.

---

## 39.3 Counting Inversions

### Problem

An **inversion** is a pair `(i, j)` where `i < j` but `arr[i] > arr[j]`. Count the total number of inversions in an array. This measures how "far" the array is from being sorted.

**Example:** `arr = [2, 4, 1, 3, 5]`
- Inversions: (2,1), (4,1), (4,3) → **3 inversions**

### Naive Approach: O(n²)

Check all pairs. Too slow for large inputs.

### Optimal Approach: Modified Merge Sort — O(n log n)

**Key insight:** During the merge step of merge sort, when we pick an element from the right array before all elements in the left array are consumed, we've found inversions.

Specifically, if `L[i] > R[j]`, then `L[i], L[i+1], ..., L[n1-1]` are all greater than `R[j]` (because L is sorted), giving us `n1 - i` inversions.

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

long long mergeAndCount(vector<int>& arr, int left, int mid, int right) {
    vector<int> L(arr.begin() + left, arr.begin() + mid + 1);
    vector<int> R(arr.begin() + mid + 1, arr.begin() + right + 1);

    int i = 0, j = 0, k = left;
    long long inversions = 0;

    while (i < (int)L.size() && j < (int)R.size()) {
        if (L[i] <= R[j]) {
            arr[k++] = L[i++];
        } else {
            // L[i] > R[j] → all remaining elements in L are > R[j]
            inversions += (long long)L.size() - i;
            arr[k++] = R[j++];
        }
    }

    while (i < (int)L.size()) arr[k++] = L[i++];
    while (j < (int)R.size()) arr[k++] = R[j++];

    return inversions;
}

long long countInversions(vector<int>& arr, int left, int right) {
    if (left >= right) return 0;

    int mid = left + (right - left) / 2;
    long long inv = 0;

    inv += countInversions(arr, left, mid);
    inv += countInversions(arr, mid + 1, right);
    inv += mergeAndCount(arr, left, mid, right);

    return inv;
}

int main() {
    vector<int> arr = {2, 4, 1, 3, 5};
    long long inv = countInversions(arr, 0, arr.size() - 1);
    cout << "Inversions: " << inv << "\n";
    // Output: 3

    vector<int> arr2 = {5, 4, 3, 2, 1};
    cout << "Inversions: " << countInversions(arr2, 0, 4) << "\n";
    // Output: 10

    vector<int> arr3 = {1, 2, 3, 4, 5};
    cout << "Inversions: " << countInversions(arr3, 0, 4) << "\n";
    // Output: 0

    return 0;
}
```

### Dry Run

`arr = [2, 4, 1, 3, 5]`

**Level 0:** Split into `[2, 4, 1]` and `[3, 5]`

**Left half `[2, 4, 1]`:** Split into `[2, 4]` and `[1]`

- `[2, 4]`: Split into `[2]` and `[4]`. Merge: `2 ≤ 4`, no inversions. Result: `[2, 4]`
- Merge `[2, 4]` and `[1]`: `2 > 1` → inv += 2 (both 2 and 4 are > 1). Result: `[1, 2, 4]`. Inversions from this merge: 2.

**Right half `[3, 5]`:** Split into `[3]` and `[5]`. Merge: `3 ≤ 5`, no inversions. Result: `[3, 5]`.

**Final merge** `[1, 2, 4]` and `[3, 5]`:
- `1 ≤ 3` → pick 1
- `2 ≤ 3` → pick 2
- `4 > 3` → inv += 1 (only 4 is > 3). Pick 3.
- `4 ≤ 5` → pick 4
- Pick 5.
- Inversions from this merge: 1.

**Total inversions:** 0 + 2 + 0 + 1 = **3** ✓

### Complexity

**Time:** Same as merge sort: O(n log n).
**Space:** O(n) for temporary arrays.

---

## 39.4 Closest Pair of Points

### Problem

Given n points in 2D, find the pair with the smallest Euclidean distance.

### Naive Approach: O(n²)

Check all pairs. Too slow for large n.

### Optimal Approach: Divide and Conquer — O(n log n)

### Algorithm

1. **Sort** points by x-coordinate.
2. **Divide** points into left and right halves by the median x-coordinate.
3. **Conquer** recursively to find the closest pair in each half. Let `d = min(d_left, d_right)`.
4. **Combine:** Find the closest pair that spans both halves (one point from left, one from right).
   - Only consider points within distance `d` of the dividing line.
   - Sort these points by y-coordinate.
   - For each point, check at most 6 points above it (proven geometrically).

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

struct Point {
    double x, y;
};

double dist(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    return sqrt(dx * dx + dy * dy);
}

// Brute force for small arrays
double bruteForce(vector<Point>& points, int left, int right) {
    double minDist = DBL_MAX;
    for (int i = left; i <= right; i++) {
        for (int j = i + 1; j <= right; j++) {
            minDist = min(minDist, dist(points[i], points[j]));
        }
    }
    return minDist;
}

// Find closest distance in strip (sorted by y)
double stripClosest(vector<Point>& strip, double d) {
    double minDist = d;
    sort(strip.begin(), strip.end(), [](const Point& a, const Point& b) {
        return a.y < b.y;
    });

    // Check at most 7 neighbors ahead
    for (int i = 0; i < (int)strip.size(); i++) {
        for (int j = i + 1; j < (int)strip.size() && (strip[j].y - strip[i].y) < minDist; j++) {
            minDist = min(minDist, dist(strip[i], strip[j]));
        }
    }
    return minDist;
}

double closestPairRec(vector<Point>& points, int left, int right) {
    // Base case: brute force for small arrays
    if (right - left <= 2) {
        return bruteForce(points, left, right);
    }

    int mid = left + (right - left) / 2;
    double midX = points[mid].x;

    double dl = closestPairRec(points, left, mid);
    double dr = closestPairRec(points, mid + 1, right);
    double d = min(dl, dr);

    // Build strip of points within distance d of mid line
    vector<Point> strip;
    for (int i = left; i <= right; i++) {
        if (abs(points[i].x - midX) < d) {
            strip.push_back(points[i]);
        }
    }

    return min(d, stripClosest(strip, d));
}

double closestPair(vector<Point> points) {
    sort(points.begin(), points.end(), [](const Point& a, const Point& b) {
        return a.x < b.x;
    });
    return closestPairRec(points, 0, points.size() - 1);
}

int main() {
    vector<Point> points = {{2, 3}, {12, 30}, {40, 50}, {5, 1}, {12, 10}, {3, 4}};

    double result = closestPair(points);
    cout << fixed << setprecision(4);
    cout << "Closest pair distance: " << result << "\n";
    // Points (2,3) and (3,4) have distance sqrt(2) ≈ 1.4142

    return 0;
}
```

### Why Check Only ~6 Points in the Strip?

**Theorem:** In a strip of width `2d` sorted by y-coordinate, each point needs to be compared with at most 7 subsequent points.

**Proof sketch:** Divide the strip into `d × d` squares. Each square can contain at most 4 points (otherwise two would be closer than `d`, contradicting `d`'s minimality). For any point, the 7 squares directly above it can contain at most 4 × 7 = 28 points, but in practice, the geometry limits it to about 6-7 comparisons.

### Complexity

**Time:** T(n) = 2T(n/2) + O(n log n) → O(n log²n). With careful y-sorted preprocessing, O(n log n).
**Space:** O(n).

---

## 39.5 Master Theorem

The **Master Theorem** provides a direct way to solve recurrences of the form:

```
T(n) = aT(n/b) + O(n^d)
```

where:
- `a` = number of subproblems
- `b` = factor by which the problem size is reduced
- `d` = exponent of the work done outside the recursive calls

### Three Cases

**Case 1:** If `a > b^d`, then `T(n) = O(n^(log_b(a)))`

**Case 2:** If `a = b^d`, then `T(n) = O(n^d · log n)`

**Case 3:** If `a < b^d`, then `T(n) = O(n^d)`

### Intuition

Compare the **growth rate of subproblems** (`a`) with the **growth rate of work per level** (`b^d`):
- If subproblems grow faster (Case 1): the leaves dominate → `O(n^(log_b(a)))`.
- If they're equal (Case 2): each level does the same work → `O(n^d · log n)`.
- If work per level grows faster (Case 3): the root dominates → `O(n^d)`.

### Examples

#### Example 1: Merge Sort

```
T(n) = 2T(n/2) + O(n)
a = 2, b = 2, d = 1
b^d = 2^1 = 2 = a → Case 2
T(n) = O(n^1 · log n) = O(n log n)
```

#### Example 2: Binary Search

```
T(n) = T(n/2) + O(1)
a = 1, b = 2, d = 0
b^d = 2^0 = 1 = a → Case 2
T(n) = O(n^0 · log n) = O(log n)
```

#### Example 3: Strassen's Matrix Multiplication

```
T(n) = 7T(n/2) + O(n^2)
a = 7, b = 2, d = 2
b^d = 2^2 = 4 < 7 = a → Case 1
T(n) = O(n^(log_2(7))) ≈ O(n^2.807)
```

#### Example 4: Karatsuba Multiplication

```
T(n) = 3T(n/2) + O(n)
a = 3, b = 2, d = 1
b^d = 2^1 = 2 < 3 = a → Case 1
T(n) = O(n^(log_2(3))) ≈ O(n^1.585)
```

#### Example 5: A hypothetical algorithm

```
T(n) = 3T(n/4) + O(n · log n)
```

This doesn't fit the standard Master Theorem form directly (the non-recursive work is `O(n log n)`, not `O(n^d)`). For this, use the **generalized Master Theorem**:

If `T(n) = aT(n/b) + O(n^d · (log n)^k)`:
- Case 1: `a < b^d` → `T(n) = O(n^d · (log n)^k)`
- Case 2: `a = b^d` → `T(n) = O(n^d · (log n)^(k+1))`
- Case 3: `a > b^d` → `T(n) = O(n^(log_b(a)))`

### Quick Reference Table

| Algorithm | Recurrence | a | b | d | Case | Result |
|-----------|-----------|---|---|---|------|--------|
| Merge Sort | 2T(n/2) + O(n) | 2 | 2 | 1 | 2 | O(n log n) |
| Binary Search | T(n/2) + O(1) | 1 | 2 | 0 | 2 | O(log n) |
| Strassen | 7T(n/2) + O(n²) | 7 | 2 | 2 | 1 | O(n^2.807) |
| Karatsuba | 3T(n/2) + O(n) | 3 | 2 | 1 | 1 | O(n^1.585) |
| Selection | 2T(n/4) + O(n) | 2 | 4 | 1 | 3 | O(n) |
| Closest Pair | 2T(n/2) + O(n) | 2 | 2 | 1 | 2 | O(n log n) |

### Applying the Master Theorem: Step-by-Step Template

```cpp
// Template for analyzing a divide-and-conquer recurrence:
//
// 1. Identify: T(n) = aT(n/b) + f(n) where f(n) = O(n^d)
// 2. Compute: c = log_b(a) = log(a) / log(b)
// 3. Compare: a vs b^d
//
//    Case 1: a > b^d  → T(n) = O(n^c)
//    Case 2: a = b^d  → T(n) = O(n^d · log n)
//    Case 3: a < b^d  → T(n) = O(n^d)

#include <bits/stdc++.h>
using namespace std;

void analyzeRecurrence(int a, int b, int d) {
    double c = log(a) / log(b);
    double bd = pow(b, d);

    cout << "T(n) = " << a << "T(n/" << b << ") + O(n^" << d << ")\n";
    cout << "  a = " << a << ", b = " << b << ", d = " << d << "\n";
    cout << "  log_b(a) = " << fixed << setprecision(4) << c << "\n";
    cout << "  b^d = " << bd << "\n";

    if (a > bd) {
        cout << "  Case 1: a > b^d → T(n) = O(n^" << c << ")\n";
    } else if (abs(a - bd) < 1e-9) {
        cout << "  Case 2: a = b^d → T(n) = O(n^" << d << " · log n)\n";
    } else {
        cout << "  Case 3: a < b^d → T(n) = O(n^" << d << ")\n";
    }
    cout << "\n";
}

int main() {
    analyzeRecurrence(2, 2, 1);  // Merge Sort
    analyzeRecurrence(1, 2, 0);  // Binary Search
    analyzeRecurrence(7, 2, 2);  // Strassen
    analyzeRecurrence(3, 2, 1);  // Karatsuba

    return 0;
}
```

---

## 39.6 More Divide and Conquer Applications

### Maximum Subarray (Kadane vs D&C)

The maximum subarray problem can be solved with divide and conquer in O(n log n), though Kadane's algorithm does it in O(n).

```cpp
#include <bits/stdc++.h>
using namespace std;

int maxCrossingSum(vector<int>& arr, int left, int mid, int right) {
    // Left side: max sum ending at mid
    int leftSum = INT_MIN, sum = 0;
    for (int i = mid; i >= left; i--) {
        sum += arr[i];
        leftSum = max(leftSum, sum);
    }

    // Right side: max sum starting at mid+1
    int rightSum = INT_MIN;
    sum = 0;
    for (int i = mid + 1; i <= right; i++) {
        sum += arr[i];
        rightSum = max(rightSum, sum);
    }

    return leftSum + rightSum;
}

int maxSubArrayDC(vector<int>& arr, int left, int right) {
    if (left == right) return arr[left];

    int mid = left + (right - left) / 2;
    int leftMax = maxSubArrayDC(arr, left, mid);
    int rightMax = maxSubArrayDC(arr, mid + 1, right);
    int crossMax = maxCrossingSum(arr, left, mid, right);

    return max({leftMax, rightMax, crossMax});
}

int main() {
    vector<int> arr = {-2, 1, -3, 4, -1, 2, 1, -5, 4};
    cout << "Maximum subarray sum: " << maxSubArrayDC(arr, 0, arr.size() - 1) << "\n";
    // Output: 6 (subarray [4, -1, 2, 1])

    return 0;
}
```

---

## 39.7 Interview Tips

1. **Identify the pattern:** If a problem can be split into independent subproblems with a combinable solution, it's divide and conquer.

2. **Base case matters:** Always define a clear base case. For sorting, it's a single element. For geometric problems, it's 2-3 points.

3. **Master Theorem for complexity:** Learn to recognize the three cases. It's the fastest way to analyze D&C recurrences in interviews.

4. **D&C vs other approaches:** Sometimes D&C isn't the optimal approach (e.g., maximum subarray with Kadane's O(n) vs D&C's O(n log n)). Know when to use it.

5. **Count inversions is a classic:** It appears in many disguised forms (e.g., "minimum swaps to sort", "number of visible pairs").

6. **Closest pair:** The geometric argument for why we only check ~6 points in the strip is a favorite interview question.

---

## 39.8 Common Mistakes

1. **Forgetting the base case:** Infinite recursion leads to stack overflow. Always handle `left >= right` or array size ≤ 1.

2. **Integer overflow in mid calculation:** Use `left + (right - left) / 2` instead of `(left + right) / 2`.

3. **Not handling duplicates in merge sort:** Use `<=` (not `<`) when merging to maintain stability.

4. **Off-by-one in inversion counting:** When `L[i] > R[j]`, add `L.size() - i` (not `L.size() - i - 1`).

5. **Closest pair: not sorting by x first:** The algorithm requires points sorted by x-coordinate as a precondition.

6. **Master Theorem misapplication:** The recurrence must be in the form `T(n) = aT(n/b) + O(n^d)`. If the non-recursive work is `O(n log n)`, use the generalized form.

7. **Stack overflow for deep recursion:** For very large inputs, the recursion depth of O(log n) is usually fine, but be aware of stack limits in some environments.

---

## 39.9 Practice Problems

| # | Problem | Difficulty | Key Idea |
|---|---------|------------|----------|
| 1 | LeetCode 912 - Sort an Array | Medium | Merge sort implementation |
| 2 | Count Inversions | Medium | Modified merge sort |
| 3 | LeetCode 53 - Maximum Subarray | Medium | D&C or Kadane's |
| 4 | LeetCode 215 - Kth Largest Element | Medium | Quickselect (D&C) |
| 5 | Closest Pair of Points | Hard | Geometric D&C |
| 6 | LeetCode 240 - Search a 2D Matrix II | Medium | D&C on matrix |
| 7 | LeetCode 23 - Merge K Sorted Lists | Hard | D&C merge |
| 8 | LeetCode 493 - Reverse Pairs | Hard | Modified merge sort |
| 9 | LeetCode 327 - Count of Range Sum | Hard | Merge sort + range counting |
| 10 | LeetCode 315 - Count of Smaller Numbers After Self | Hard | Merge sort / BIT |

---

## 39.10 Summary

Divide and conquer is more than a technique — it's a way of thinking. The key takeaways:

- **Three steps:** Divide, Conquer, Combine.
- **Merge sort** is the foundation: understand it deeply.
- **Counting inversions** is merge sort's most important variant for interviews.
- **Closest pair of points** demonstrates D&C on geometric problems.
- **Master Theorem** gives instant complexity analysis for standard recurrences.
- **Not always optimal:** Compare with other approaches (greedy, DP, two pointers) before committing to D&C.

The ability to recognize when a problem can be decomposed, and to combine subproblem solutions efficiently, is what separates good engineers from great ones.
