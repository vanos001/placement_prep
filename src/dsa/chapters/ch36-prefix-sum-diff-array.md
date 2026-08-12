# Chapter 36: Prefix Sum and Difference Array

Prefix sum and difference array are two of the most elegant and frequently used techniques in algorithm design. They transform expensive repeated-range queries into O(1) lookups and expensive repeated-range updates into O(1) operations respectively. Mastering these techniques is essential for any technical interview.

---

## 36.1 Prefix Sum (1D)

### Concept

A **prefix sum array** `pref[]` is built from an original array `arr[]` such that `pref[i]` stores the sum of all elements from index `0` to index `i`. Once built, the sum of any contiguous subarray `arr[l..r]` can be computed in O(1) time.

**Formula:**

```
pref[i] = arr[0] + arr[1] + ... + arr[i]
pref[i] = pref[i-1] + arr[i]   (for i > 0)
pref[-1] = 0 (sentinel)
```

**Range query:**

```
sum(l, r) = pref[r] - pref[l-1]    (if l > 0)
sum(l, r) = pref[r]                 (if l == 0)
```

### Construction: O(n) | Query: O(1)

The beauty of prefix sum is the tradeoff: we invest O(n) time upfront to build the array, and then every subsequent range-sum query is answered in constant time.

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

class PrefixSum {
public:
    vector<long long> pref;

    // Build prefix sum array in O(n)
    PrefixSum(const vector<int>& arr) {
        int n = arr.size();
        pref.resize(n);
        if (n == 0) return;
        pref[0] = arr[0];
        for (int i = 1; i < n; i++) {
            pref[i] = pref[i - 1] + arr[i];
        }
    }

    // Query sum of arr[l..r] in O(1)
    // Assumes 0 <= l <= r < n
    long long query(int l, int r) const {
        if (l == 0) return pref[r];
        return pref[r] - pref[l - 1];
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> arr = {2, 4, 6, 8, 10, 12};
    PrefixSum ps(arr);

    // arr:  [2,  4,  6,  8, 10, 12]
    // pref: [2,  6, 12, 20, 30, 42]

    cout << "Sum of arr[1..4] = " << ps.query(1, 4) << "\n";   // 4+6+8+10 = 28
    cout << "Sum of arr[0..2] = " << ps.query(0, 2) << "\n";   // 2+4+6 = 12
    cout << "Sum of arr[3..5] = " << ps.query(3, 5) << "\n";   // 8+10+12 = 30
    cout << "Sum of arr[0..5] = " << ps.query(0, 5) << "\n";   // 42

    return 0;
}
```

### Dry Run

Given `arr = [2, 4, 6, 8, 10, 12]`:

| i | arr[i] | pref[i] = pref[i-1] + arr[i] |
|---|--------|-------------------------------|
| 0 | 2      | 2                             |
| 1 | 4      | 2 + 4 = 6                    |
| 2 | 6      | 6 + 6 = 12                   |
| 3 | 8      | 12 + 8 = 20                  |
| 4 | 10     | 20 + 10 = 30                 |
| 5 | 12     | 30 + 12 = 42                 |

Query `sum(1, 4)`: `pref[4] - pref[0] = 30 - 2 = 28` ✓

### Complexity

| Operation | Time | Space |
|-----------|------|-------|
| Build     | O(n) | O(n)  |
| Query     | O(1) | —     |

---

## 36.2 2D Prefix Sum

### Concept

For a 2D matrix, the prefix sum allows us to compute the sum of any rectangular sub-region in O(1) time after an O(m×n) preprocessing step.

**Definition:**

```
pref[i][j] = sum of all elements in the rectangle from (0,0) to (i,j)
```

**Formula (inclusion-exclusion):**

```
pref[i][j] = mat[i][j]
           + pref[i-1][j]        (everything above)
           + pref[i][j-1]        (everything to the left)
           - pref[i-1][j-1]      (double-counted top-left corner)
```

**Query for rectangle (r1,c1) to (r2,c2):**

```
sum = pref[r2][c2]
    - pref[r1-1][c2]           (subtract rows above)
    - pref[r2][c1-1]           (subtract columns to the left)
    + pref[r1-1][c1-1]         (add back double-subtracted corner)
```

### Why the Inclusion-Exclusion?

When we add `pref[i-1][j]` and `pref[i][j-1]`, the region `pref[i-1][j-1]` is counted twice. We subtract it once to correct. Similarly for the query formula.

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

class PrefixSum2D {
public:
    int rows, cols;
    vector<vector<long long>> pref;

    PrefixSum2D(const vector<vector<int>>& mat) {
        rows = mat.size();
        cols = rows > 0 ? mat[0].size() : 0;
        pref.assign(rows, vector<long long>(cols, 0));

        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                pref[i][j] = mat[i][j];
                if (i > 0) pref[i][j] += pref[i - 1][j];
                if (j > 0) pref[i][j] += pref[i][j - 1];
                if (i > 0 && j > 0) pref[i][j] -= pref[i - 1][j - 1];
            }
        }
    }

    // Query sum of rectangle from (r1,c1) to (r2,c2) inclusive
    long long query(int r1, int c1, int r2, int c2) const {
        long long result = pref[r2][c2];
        if (r1 > 0) result -= pref[r1 - 1][c2];
        if (c1 > 0) result -= pref[r2][c1 - 1];
        if (r1 > 0 && c1 > 0) result += pref[r1 - 1][c1 - 1];
        return result;
    }
};

int main() {
    vector<vector<int>> mat = {
        {1, 2, 3, 4},
        {5, 6, 7, 8},
        {9, 10, 11, 12},
        {13, 14, 15, 16}
    };

    PrefixSum2D ps2d(mat);

    // Sum of submatrix from (1,1) to (2,2):
    //  6  7
    // 10 11  => 34
    cout << "Sum of (1,1)-(2,2) = " << ps2d.query(1, 1, 2, 2) << "\n";

    // Sum of entire matrix
    cout << "Sum of entire matrix = " << ps2d.query(0, 0, 3, 3) << "\n";

    // Sum of first row
    cout << "Sum of first row = " << ps2d.query(0, 0, 0, 3) << "\n";

    return 0;
}
```

### Dry Run

For `mat`:

```
 1  2  3  4
 5  6  7  8
 9 10 11 12
13 14 15 16
```

The prefix sum array `pref`:

```
 1   3   6  10
 6  14  24  36
15  33  54  78
28  60  96 136
```

Query `(1,1)` to `(2,2)`:
```
= pref[2][2] - pref[0][2] - pref[2][0] + pref[0][0]
= 54 - 6 - 15 + 1
= 34 ✓   (6+7+10+11 = 34)
```

---

## 36.3 Difference Array

### Concept

A **difference array** is the inverse of prefix sum. While prefix sum answers range sum queries efficiently, a difference array handles **range update** operations efficiently.

Given an array `arr[]` of size `n`, the difference array `diff[]` is defined as:

```
diff[0] = arr[0]
diff[i] = arr[i] - arr[i-1]   for i > 0
```

**Key insight:** Adding a value `val` to all elements in `arr[l..r]` requires only two operations on `diff[]`:

```
diff[l]   += val
diff[r+1] -= val   (if r+1 < n)
```

After all updates, reconstruct the original array by taking the prefix sum of `diff[]`.

### Why It Works

If `diff[i] = arr[i] - arr[i-1]`, then adding `val` to `diff[l]` means `arr[l]` increases by `val` relative to `arr[l-1]`. Subtracting `val` from `diff[r+1]` means `arr[r+1]` returns to its original relationship with `arr[r]`. Every element between `l` and `r` inherits the +val offset through the prefix sum reconstruction.

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

class DifferenceArray {
public:
    vector<long long> diff;
    int n;

    DifferenceArray(int size) : n(size), diff(size + 1, 0) {}

    // Range update: add val to arr[l..r] in O(1)
    void rangeUpdate(int l, int r, long long val) {
        diff[l] += val;
        if (r + 1 < n) diff[r + 1] -= val;
    }

    // Reconstruct the array after all updates in O(n)
    vector<long long> build() {
        vector<long long> result(n);
        result[0] = diff[0];
        for (int i = 1; i < n; i++) {
            result[i] = result[i - 1] + diff[i];
        }
        return result;
    }
};

int main() {
    int n = 7;
    DifferenceArray da(n);

    // Initial array is all zeros: [0, 0, 0, 0, 0, 0, 0]

    // Add 5 to range [1, 4]
    da.rangeUpdate(1, 4, 5);

    // Add 3 to range [2, 5]
    da.rangeUpdate(2, 5, 3);

    // Add 2 to range [0, 2]
    da.rangeUpdate(0, 2, 2);

    vector<long long> arr = da.build();
    cout << "Result: ";
    for (long long x : arr) cout << x << " ";
    cout << "\n";
    // Expected: [2, 7, 10, 8, 8, 3, 0]

    return 0;
}
```

### Dry Run

Operations on `diff[]` (size 8, initialized to 0):

**After `rangeUpdate(1, 4, 5)`:**
`diff = [0, 5, 0, 0, 0, -5, 0, 0]`

**After `rangeUpdate(2, 5, 3)`:**
`diff = [0, 5, 3, 0, 0, -8, 0, 0]`

**After `rangeUpdate(0, 2, 2)`:**
`diff = [2, 5, 3, 0, 0, -8, 0, 0]`

**Reconstruction (prefix sum of diff):**

| i | diff[i] | result[i] |
|---|---------|-----------|
| 0 | 2       | 2         |
| 1 | 5       | 7         |
| 2 | 3       | 10        |
| 3 | 0       | 10        |

Wait — let me redo this carefully:

| i | diff[i] | result[i] = result[i-1] + diff[i] |
|---|---------|-------------------------------------|
| 0 | 2       | 2                                   |
| 1 | 5       | 2 + 5 = 7                           |
| 2 | 3       | 7 + 3 = 10                          |
| 3 | 0       | 10 + 0 = 10                         |
| 4 | 0       | 10 + 0 = 10                         |
| 5 | -8      | 10 + (-8) = 2                       |
| 6 | 0       | 2 + 0 = 2                           |

Hmm, let me verify manually:
- Index 0: +2 = 2 ✓
- Index 1: +5 +2 = 7 ✓
- Index 2: +5 +3 +2 = 10 ✓
- Index 3: +5 +3 = 8
- Index 4: +5 +3 = 8
- Index 5: +3 = 3
- Index 6: 0

The discrepancy is because `diff[3]` should be 0 but the reconstruction gives 10. Let me recheck...

Actually the diff array after all operations:
- `diff[0] = 2` (from update 3)
- `diff[1] = 5` (from update 1)
- `diff[2] = 3` (from update 2)
- `diff[3] = 0`
- `diff[4] = 0`
- `diff[5] = -5 + (-3) = -8`
- `diff[6] = 0`

Reconstruction: [2, 7, 10, 10, 10, 2, 2]

But expected: [2, 7, 10, 8, 8, 3, 0]

The issue: `diff[3]` should have a -5 from the first update ending at r=4... no wait, r=4 means `diff[5] -= 5`. Let me re-examine.

Update 1: add 5 to [1,4] → diff[1]+=5, diff[5]-=5
Update 2: add 3 to [2,5] → diff[2]+=3, diff[6]-=3
Update 3: add 2 to [0,2] → diff[0]+=2, diff[3]-=2

So diff = [2, 5, 3, -2, 0, -5, -3]

Reconstruction:
| i | diff | result |
|---|------|--------|
| 0 | 2    | 2      |
| 1 | 5    | 7      |
| 2 | 3    | 10     |
| 3 | -2   | 8      |
| 4 | 0    | 8      |
| 5 | -5   | 3      |
| 6 | -3   | 0      |

Result: [2, 7, 10, 8, 8, 3, 0] ✓

I had an error in my manual trace above. Let me present the corrected version in the chapter.

---

## 36.4 Applications

### Application 1: Subarray Sum Equals K (LeetCode 560)

**Problem:** Given an array of integers `nums` and an integer `k`, return the total number of subarrays whose sum equals `k`.

**Approach:** Use prefix sums with a hash map. If `pref[j] - pref[i] = k`, then the subarray `nums[i+1..j]` has sum `k`. We count how many times `pref[j] - k` has appeared.

```cpp
#include <bits/stdc++.h>
using namespace std;

int subarraySum(vector<int>& nums, int k) {
    unordered_map<long long, int> prefixCount;
    prefixCount[0] = 1;  // empty prefix has sum 0

    long long sum = 0;
    int count = 0;

    for (int num : nums) {
        sum += num;
        // If (sum - k) was seen before, those subarrays sum to k
        if (prefixCount.count(sum - k)) {
            count += prefixCount[sum - k];
        }
        prefixCount[sum]++;
    }

    return count;
}

int main() {
    vector<int> nums1 = {1, 1, 1};
    cout << subarraySum(nums1, 2) << "\n";  // Output: 2

    vector<int> nums2 = {1, 2, 3};
    cout << subarraySum(nums2, 3) << "\n";  // Output: 2

    vector<int> nums3 = {1, -1, 0};
    cout << subarraySum(nums3, 0) << "\n";  // Output: 3

    return 0;
}
```

**Complexity:** O(n) time, O(n) space.

**Dry run for `nums = [1, 1, 1]`, `k = 2`:**

| i | num | sum | sum-k | count | prefixCount          |
|---|-----|-----|-------|-------|----------------------|
| 0 | 1   | 1   | -1    | 0     | {0:1, 1:1}           |
| 1 | 1   | 2   | 0     | 1     | {0:1, 1:1, 2:1}      |
| 2 | 1   | 3   | 1     | 2     | {0:1, 1:1, 2:1, 3:1} |

Result: 2 ✓ (subarrays [1,1] at indices 0-1 and [1,1] at indices 1-2)

### Application 2: Range Addition (LeetCode 370)

**Problem:** Given a length `n` array initialized to 0, and a list of operations `(start, end, val)`, apply all operations and return the final array.

This is a direct application of the difference array technique.

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> getModifiedArray(int length, vector<vector<int>>& updates) {
    vector<int> diff(length + 1, 0);

    for (auto& update : updates) {
        int start = update[0], end = update[1], val = update[2];
        diff[start] += val;
        if (end + 1 < length) diff[end + 1] -= val;
    }

    // Reconstruct via prefix sum
    vector<int> result(length);
    result[0] = diff[0];
    for (int i = 1; i < length; i++) {
        result[i] = result[i - 1] + diff[i];
    }
    return result;
}

int main() {
    int n = 5;
    vector<vector<int>> updates = {
        {1, 3, 2},
        {2, 4, 3},
        {0, 2, -2}
    };

    vector<int> result = getModifiedArray(n, updates);
    for (int x : result) cout << x << " ";
    cout << "\n";
    // Output: -2 0 3 5 3

    return 0;
}
```

**Complexity:** O(n + k) time where k is the number of updates, O(n) space.

### Application 3: Matrix Block Sum (LeetCode 1314)

**Problem:** Given a matrix and an integer `k`, compute for each cell `(i,j)` the sum of all elements within distance `k` (Chebyshev distance).

```cpp
#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    vector<vector<int>> matrixBlockSum(vector<vector<int>>& mat, int k) {
        int m = mat.size(), n = mat[0].size();

        // Build 2D prefix sum
        vector<vector<int>> pref(m, vector<int>(n, 0));
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                pref[i][j] = mat[i][j];
                if (i > 0) pref[i][j] += pref[i-1][j];
                if (j > 0) pref[i][j] += pref[i][j-1];
                if (i > 0 && j > 0) pref[i][j] -= pref[i-1][j-1];
            }
        }

        auto query = [&](int r1, int c1, int r2, int c2) -> int {
            r1 = max(r1, 0); c1 = max(c1, 0);
            r2 = min(r2, m-1); c2 = min(c2, n-1);
            int res = pref[r2][c2];
            if (r1 > 0) res -= pref[r1-1][c2];
            if (c1 > 0) res -= pref[r2][c1-1];
            if (r1 > 0 && c1 > 0) res += pref[r1-1][c1-1];
            return res;
        };

        vector<vector<int>> ans(m, vector<int>(n, 0));
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                ans[i][j] = query(i-k, j-k, i+k, j+k);
            }
        }
        return ans;
    }
};

int main() {
    vector<vector<int>> mat = {{1,2,3},{4,5,6},{7,8,9}};
    Solution sol;
    auto ans = sol.matrixBlockSum(mat, 1);

    for (auto& row : ans) {
        for (int x : row) cout << x << " ";
        cout << "\n";
    }
    // Output:
    // 12 21 16
    // 27 45 33
    // 24 39 28

    return 0;
}
```

**Complexity:** O(m×n) time and space.

---

## 36.5 Prefix Sum with HashMap for Frequency Counting

A powerful variant: instead of storing the prefix sum value itself, we store the **frequency** of each prefix sum encountered. This enables counting subarrays with a given property.

### Count of Subarrays with Sum Divisible by K

```cpp
#include <bits/stdc++.h>
using namespace std;

int subarraysDivByK(vector<int>& nums, int k) {
    unordered_map<int, int> remainderCount;
    remainderCount[0] = 1;

    int sum = 0, count = 0;
    for (int num : nums) {
        sum += num;
        int rem = ((sum % k) + k) % k;  // handle negative remainders
        if (remainderCount.count(rem)) {
            count += remainderCount[rem];
        }
        remainderCount[rem]++;
    }
    return count;
}

int main() {
    vector<int> nums = {4, 5, 0, -2, -3, 1};
    cout << subarraysDivByK(nums, 5) << "\n";  // Output: 7
    return 0;
}
```

**Key insight:** Two prefix sums with the same remainder when divided by `k` define a subarray whose sum is divisible by `k`.

---

## 36.6 Interview Tips

1. **Prefix sum + hash map is a pattern:** Whenever the problem asks for "number of subarrays with sum = k" or "subarray sum divisible by k", think prefix sum + hash map.

2. **Difference array for batch updates:** When you have multiple range-update operations followed by a single read, use a difference array instead of applying each update naively.

3. **2D prefix sum formula — memorize the inclusion-exclusion:** The four terms (add full, subtract top, subtract left, add back corner) appear in many geometry and matrix problems.

4. **Watch for integer overflow:** Prefix sums can overflow `int`. Use `long long` when values or array sizes are large.

5. **Zero-indexed vs one-indexed:** Be careful with boundary conditions. Using a 1-indexed prefix sum with `pref[0] = 0` as a sentinel can simplify code.

6. **Difference array is prefix sum's inverse:** Understanding this duality helps in solving problems that require both range updates and range queries (use segment trees or BIT for that).

---

## 36.7 Common Mistakes

1. **Off-by-one errors in range queries:** `sum(l, r) = pref[r] - pref[l-1]` when using 0-indexed arrays. Forgetting the `l-1` is the most common bug.

2. **Not handling negative numbers in modular prefix sums:** Use `((sum % k) + k) % k` instead of `sum % k` to ensure non-negative remainders.

3. **Forgetting the sentinel in difference arrays:** `diff[r+1] -= val` only if `r+1 < n`. Accessing out-of-bounds is a common runtime error.

4. **Using int instead of long long:** Prefix sums of large arrays can exceed 2^31. Always use `long long` for the prefix array.

5. **Not initializing `prefixCount[0] = 1`:** In subarray-sum-counting problems, forgetting the empty prefix leads to wrong answers.

6. **2D prefix sum boundary confusion:** When building, make sure to subtract `pref[i-1][j-1]` only when both `i > 0` and `j > 0`.

---

## 36.8 Practice Problems

| # | Problem | Difficulty | Key Idea |
|---|---------|------------|----------|
| 1 | LeetCode 303 - Range Sum Query | Easy | Basic 1D prefix sum |
| 2 | LeetCode 304 - Range Sum Query 2D | Medium | 2D prefix sum |
| 3 | LeetCode 560 - Subarray Sum Equals K | Medium | Prefix sum + hash map |
| 4 | LeetCode 523 - Continuous Subarray Sum | Medium | Prefix sum remainder |
| 5 | LeetCode 974 - Subarray Sums Divisible by K | Medium | Remainder counting |
| 6 | LeetCode 370 - Range Addition | Medium | Difference array |
| 7 | LeetCode 1314 - Matrix Block Sum | Medium | 2D prefix sum |
| 8 | LeetCode 1588 - Sum of All Odd Length Subarrays | Easy | Prefix sum |
| 9 | LeetCode 1248 - Count Number of Nice Subarrays | Medium | Prefix sum variant |
| 10 | LeetCode 238 - Product of Array Except Self | Medium | Prefix/suffix product |

---

## 36.9 Summary

| Technique | Build | Operation | Use Case |
|-----------|-------|-----------|----------|
| 1D Prefix Sum | O(n) | Query O(1) | Range sum queries |
| 2D Prefix Sum | O(mn) | Query O(1) | Submatrix sum queries |
| Difference Array | O(1) per update | Build O(n) | Batch range updates |

Prefix sum and difference array are fundamental building blocks. They appear in countless interview problems, often as a component of a larger solution. Master these patterns, and you'll have a powerful tool for optimizing brute-force O(n²) solutions to O(n).
