# Chapter 6: Searching

Searching is one of the most fundamental operations in computer science. While linear search is straightforward, **binary search** is a technique that appears in countless interview problems — often in disguise. Mastering binary search and its variants is one of the highest-return investments for interview preparation.

---

## 6.1 Linear Search

### Basic Linear Search

The simplest search: check every element until you find the target.

```cpp
#include <iostream>
#include <vector>

// Time: O(n), Space: O(1)
int linearSearch(const std::vector<int>& arr, int target) {
    for (int i = 0; i < (int)arr.size(); i++) {
        if (arr[i] == target) {
            return i;
        }
    }
    return -1;  // Not found
}

int main() {
    std::vector<int> arr = {4, 2, 7, 1, 9, 3};
    int target = 7;

    int idx = linearSearch(arr, target);
    if (idx != -1) {
        std::cout << "Found " << target << " at index " << idx << std::endl;
    } else {
        std::cout << target << " not found" << std::endl;
    }
    // Output: Found 7 at index 2
    return 0;
}
```

### Sentinel Linear Search

Eliminate the bounds check in the inner loop by placing the target at the end:

```cpp
#include <iostream>
#include <vector>

// Sentinel linear search — removes one comparison per iteration
// Time: O(n), Space: O(1)
int sentinelSearch(std::vector<int>& arr, int target) {
    int n = arr.size();
    if (n == 0) return -1;

    int last = arr[n - 1];    // Save last element
    arr[n - 1] = target;      // Place sentinel

    int i = 0;
    while (arr[i] != target) {
        i++;
    }

    arr[n - 1] = last;        // Restore last element

    if (i < n - 1 || arr[n - 1] == target) {
        return i;
    }
    return -1;
}

int main() {
    std::vector<int> arr = {4, 2, 7, 1, 9, 3};
    int idx = sentinelSearch(arr, 7);
    std::cout << "Found at index: " << idx << std::endl;  // 2
    return 0;
}
```

**Why?** In standard linear search, each iteration checks two conditions: `i < n` and `arr[i] == target`. The sentinel removes the first check, saving one comparison per iteration. In practice, this is a micro-optimization, but it demonstrates algorithmic thinking.

---

## 6.2 Binary Search Basics

### The Key Insight

If an array is **sorted**, you can eliminate half the remaining elements with each comparison by checking the middle element.

**Analogy:** Looking up a word in a dictionary. You don't start from page 1 — you open to the middle, see if your word comes before or after, and eliminate half the pages.

### Iterative Binary Search

```cpp
#include <iostream>
#include <vector>

// Time: O(log n), Space: O(1)
int binarySearch(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;

    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;  // Avoid overflow!

        if (arr[mid] == target) {
            return mid;
        } else if (arr[mid] < target) {
            lo = mid + 1;   // Search right half
        } else {
            hi = mid - 1;   // Search left half
        }
    }

    return -1;  // Not found
}

int main() {
    std::vector<int> arr = {2, 3, 4, 10, 40, 50, 60, 70};
    int target = 10;

    int idx = binarySearch(arr, target);
    if (idx != -1) {
        std::cout << "Found at index " << idx << std::endl;  // 3
    } else {
        std::cout << "Not found" << std::endl;
    }
    return 0;
}
```

### Why `lo + (hi - lo) / 2` Instead of `(lo + hi) / 2`?

If `lo` and `hi` are both large (e.g., close to INT_MAX), `lo + hi` can **overflow**. Using `lo + (hi - lo) / 2` avoids this:

```cpp
// BAD: Can overflow for large values
int mid = (lo + hi) / 2;

// GOOD: Safe from overflow
int mid = lo + (hi - lo) / 2;
```

### Recursive Binary Search

```cpp
#include <iostream>
#include <vector>

// Time: O(log n), Space: O(log n) — recursion stack
int binarySearchRecursive(const std::vector<int>& arr, int target, int lo, int hi) {
    if (lo > hi) return -1;

    int mid = lo + (hi - lo) / 2;

    if (arr[mid] == target) return mid;
    if (arr[mid] < target) return binarySearchRecursive(arr, target, mid + 1, hi);
    return binarySearchRecursive(arr, target, lo, mid - 1);
}

int main() {
    std::vector<int> arr = {2, 3, 4, 10, 40, 50, 60, 70};
    int idx = binarySearchRecursive(arr, 10, 0, arr.size() - 1);
    std::cout << "Found at index: " << idx << std::endl;  // 3
    return 0;
}
```

### Invariant-Based Thinking

The most reliable way to write binary search correctly is to maintain **invariants**:

**Invariant for standard binary search:**
- `arr[0..lo-1]` — all elements < target (we've ruled these out)
- `arr[hi+1..n-1]` — all elements > target (we've ruled these out)
- The answer, if it exists, is in `arr[lo..hi]`

When the loop ends (`lo > hi`), the search space is empty and the target is not found.

**Key rules:**
1. Always use `lo + (hi - lo) / 2` for mid.
2. Always update `lo = mid + 1` or `hi = mid - 1` (not `lo = mid` or `hi = mid`) to avoid infinite loops.
3. The loop condition `lo <= hi` ensures we check the last remaining element.

### Dry Run

```
arr = [2, 3, 4, 10, 40, 50, 60, 70], target = 10

Step 1: lo=0, hi=7, mid=3, arr[3]=10 → Found! Return 3.
```

**Example with target not in array:** target = 15

```
Step 1: lo=0, hi=7, mid=3, arr[3]=10 < 15 → lo=4
Step 2: lo=4, hi=7, mid=5, arr[5]=50 > 15 → hi=4
Step 3: lo=4, hi=4, mid=4, arr[4]=40 > 15 → hi=3
Step 4: lo=4 > hi=3 → Loop ends. Return -1.
```

---

## 6.3 Binary Search Variants

### First Occurrence (Lower Bound)

Find the **first** index where `arr[i] >= target`:

```cpp
#include <iostream>
#include <vector>

// Returns the first index where arr[i] >= target
// If all elements < target, returns n
int lowerBound(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size();  // Note: hi = n, not n-1

    while (lo < hi) {  // Note: <, not <=
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] < target) {
            lo = mid + 1;
        } else {
            hi = mid;  // Don't skip mid — it might be the answer
        }
    }

    return lo;
}

int main() {
    std::vector<int> arr = {1, 2, 2, 2, 3, 4, 5};

    std::cout << "lower_bound(2) = " << lowerBound(arr, 2) << std::endl;  // 1
    std::cout << "lower_bound(0) = " << lowerBound(arr, 0) << std::endl;  // 0
    std::cout << "lower_bound(6) = " << lowerBound(arr, 6) << std::endl;  // 7 (n)

    return 0;
}
```

### Last Occurrence (Upper Bound)

Find the **first** index where `arr[i] > target`:

```cpp
#include <iostream>
#include <vector>

// Returns the first index where arr[i] > target
// If all elements <= target, returns n
int upperBound(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size();

    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] <= target) {
            lo = mid + 1;  // Even if arr[mid] == target, keep searching right
        } else {
            hi = mid;
        }
    }

    return lo;
}

int main() {
    std::vector<int> arr = {1, 2, 2, 2, 3, 4, 5};

    std::cout << "upper_bound(2) = " << upperBound(arr, 2) << std::endl;  // 4
    std::cout << "upper_bound(0) = " << upperBound(arr, 0) << std::endl;  // 0
    std::cout << "upper_bound(6) = " << upperBound(arr, 6) << std::endl;  // 7

    return 0;
}
```

### Count of Elements

```cpp
#include <iostream>
#include <vector>

int countOccurrences(const std::vector<int>& arr, int target) {
    // Count = upper_bound - lower_bound
    auto lb = std::lower_bound(arr.begin(), arr.end(), target);
    auto ub = std::upper_bound(arr.begin(), arr.end(), target);
    return ub - lb;
}

int main() {
    std::vector<int> arr = {1, 2, 2, 2, 3, 4, 5};
    std::cout << "Count of 2: " << countOccurrences(arr, 2) << std::endl;  // 3
    std::cout << "Count of 6: " << countOccurrences(arr, 6) << std::endl;  // 0
    return 0;
}
```

### Template for Binary Search Variants

There are two main templates. Understanding both is important:

**Template 1: Standard (lo <= hi)**
```cpp
int lo = 0, hi = n - 1;
while (lo <= hi) {
    int mid = lo + (hi - lo) / 2;
    if (arr[mid] == target) return mid;
    else if (arr[mid] < target) lo = mid + 1;
    else hi = mid - 1;
}
```
Use when: searching for an exact value.

**Template 2: Boundary (lo < hi)**
```cpp
int lo = 0, hi = n;  // or hi = n - 1 depending on problem
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (condition(mid)) hi = mid;    // mid might be the answer
    else lo = mid + 1;               // mid is definitely not the answer
}
// lo == hi is the answer
```
Use when: finding a boundary (first/last occurrence, lower/upper bound).

---

## 6.4 Binary Search on Answer

This is **the most important binary search pattern for interviews**. Instead of searching in an array, we search for the **answer** in a range of possible values.

### The Pattern

```
1. Identify that the answer lies in some range [lo, hi]
2. Define a predicate function: can(x) = "is x a valid answer?"
3. The predicate is monotonic: [F, F, ..., F, T, T, ..., T]
4. Binary search for the first T (or last F)
```

### Example 1: Capacity to Ship Packages

**Problem:** You have `n` packages with weights `weights[i]`. Ship all packages within `days` days. Each day, you can ship a contiguous sequence of packages, and the total weight cannot exceed the ship's capacity. Find the minimum capacity.

```cpp
#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Can we ship all packages within 'days' days with capacity 'cap'?
bool canShip(const std::vector<int>& weights, int days, int cap) {
    int daysNeeded = 1;
    int currentLoad = 0;

    for (int w : weights) {
        if (currentLoad + w > cap) {
            daysNeeded++;
            currentLoad = 0;
        }
        currentLoad += w;
    }

    return daysNeeded <= days;
}

// Binary search on the answer
int shipWithinDays(const std::vector<int>& weights, int days) {
    // Lower bound: max weight (must be able to ship heaviest package)
    int lo = *std::max_element(weights.begin(), weights.end());
    // Upper bound: sum of all weights (ship everything in one day)
    int hi = std::accumulate(weights.begin(), weights.end(), 0);

    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (canShip(weights, days, mid)) {
            hi = mid;     // mid works, try smaller
        } else {
            lo = mid + 1; // mid doesn't work, need more capacity
        }
    }

    return lo;
}

int main() {
    std::vector<int> weights = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    int days = 5;

    std::cout << "Minimum capacity: " << shipWithinDays(weights, days) << std::endl;
    // Output: 15
    // Explanation: Ship [1,2,3,4,5] on day 1 (15), [6,7] on day 2 (13),
    //              [8] on day 3 (8), [9] on day 4 (9), [10] on day 5 (10)

    return 0;
}
```

**Why this works:**
- If capacity C works (can ship in ≤ days), then any capacity > C also works.
- If capacity C doesn't work, then any capacity < C also doesn't work.
- This monotonicity allows binary search!

**Complexity:** O(n × log(sum - max)) where n = number of packages.

### Example 2: Aggressive Cows (Minimize Maximum Distance)

**Problem:** Place `c` cows in `n` stalls (positions given) such that the minimum distance between any two cows is maximized.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Can we place 'c' cows with minimum distance >= 'dist'?
bool canPlace(std::vector<int>& stalls, int c, int dist) {
    int count = 1;  // Place first cow in first stall
    int lastPos = stalls[0];

    for (int i = 1; i < (int)stalls.size(); i++) {
        if (stalls[i] - lastPos >= dist) {
            count++;
            lastPos = stalls[i];
            if (count >= c) return true;
        }
    }

    return false;
}

// Binary search on the answer
int aggressiveCows(std::vector<int>& stalls, int c) {
    std::sort(stalls.begin(), stalls.end());

    int lo = 1;  // Minimum possible distance
    int hi = stalls.back() - stalls[0];  // Maximum possible distance

    while (lo < hi) {
        int mid = lo + (hi - lo + 1) / 2;  // Ceiling division to avoid infinite loop
        if (canPlace(stalls, c, mid)) {
            lo = mid;     // This distance works, try larger
        } else {
            hi = mid - 1; // This distance doesn't work, need smaller
        }
    }

    return lo;
}

int main() {
    std::vector<int> stalls = {1, 2, 8, 4, 9};
    int c = 3;

    std::cout << "Largest minimum distance: " << aggressiveCows(stalls, c) << std::endl;
    // Output: 3
    // Place cows at positions 1, 4, 8 (or 1, 4, 9)

    return 0;
}
```

**Key detail:** When we want to find the **maximum** value that satisfies a condition, use `mid = lo + (hi - lo + 1) / 2` (ceiling) and `lo = mid` / `hi = mid - 1`. When finding the **minimum**, use `mid = lo + (hi - lo) / 2` (floor) and `lo = mid + 1` / `hi = mid`.

### Example 3: Koko Eating Bananas

**Problem:** Koko has `piles[i]` bananas and `h` hours. She eats at rate `k` bananas/hour (from one pile per hour, finishing a pile before starting the next). Find the minimum `k` to finish all bananas in `h` hours.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

// Can Koko finish all bananas in <= h hours at rate k?
bool canFinish(const std::vector<int>& piles, int h, int k) {
    long long hours = 0;
    for (int p : piles) {
        hours += (p + k - 1) / k;  // Ceiling division: ceil(p/k)
    }
    return hours <= h;
}

int minEatingSpeed(std::vector<int>& piles, int h) {
    int lo = 1;
    int hi = *std::max_element(piles.begin(), piles.end());

    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (canFinish(piles, h, mid)) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }

    return lo;
}

int main() {
    std::vector<int> piles = {3, 6, 7, 11};
    int h = 8;

    std::cout << "Minimum eating speed: " << minEatingSpeed(piles, h) << std::endl;
    // Output: 4

    return 0;
}
```

### More Problems Using Binary Search on Answer

| Problem | Search Range | Predicate |
|---|---|---|
| Split Array Largest Sum | [max element, sum] | Can split into ≤ k subarrays with max sum ≤ mid? |
| Minimum Days to Make Bouquets | [1, max day] | Can make m bouquets of k flowers by day mid? |
| Magnetic Force Between Balls | [1, max distance] | Can place m balls with min force ≥ mid? |
| Kth Smallest in Sorted Matrix | [min element, max element] | Count elements ≤ mid; is it ≥ k? |

---

## 6.5 Binary Search on Real Numbers

### When to Use

When the answer is a real number (floating point), and you need precision up to some decimal places.

### Pattern

```cpp
#include <iostream>
#include <cmath>

// Example: Find square root of n
double sqrtBinarySearch(double n, double eps = 1e-9) {
    if (n < 0) return -1;  // Error
    if (n == 0) return 0;

    double lo = 0, hi = (n < 1) ? 1 : n;  // Handle n < 1

    while (hi - lo > eps) {
        double mid = lo + (hi - lo) / 2;
        if (mid * mid <= n) {
            lo = mid;
        } else {
            hi = mid;
        }
    }

    return lo;
}

int main() {
    double n = 10;
    std::cout << "sqrt(" << n << ") ≈ " << sqrtBinarySearch(n) << std::endl;
    std::cout << "sqrt(" << n << ") =  " << std::sqrt(n) << std::endl;
    // Both should be approximately 3.162277660...

    return 0;
}
```

### Precision Handling

**Key insight:** Don't use a fixed number of iterations — use a precision threshold:

```cpp
// BAD: Fixed iterations — might not be precise enough or too slow
for (int i = 0; i < 100; i++) { ... }

// GOOD: Stop when precision is achieved
while (hi - lo > 1e-9) { ... }
```

**For most competitive programming problems:** 1e-7 or 1e-9 precision is sufficient.

**Caution:** Avoid `while (lo != hi)` — floating-point comparison can loop forever!

### Example: Find Median of Two Sorted Arrays

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

// O(log(min(n,m))) solution using binary search
double findMedianSortedArrays(const std::vector<int>& nums1, const std::vector<int>& nums2) {
    // Ensure nums1 is the smaller array
    if (nums1.size() > nums2.size()) {
        return findMedianSortedArrays(nums2, nums1);
    }

    int n = nums1.size(), m = nums2.size();
    int lo = 0, hi = n;

    while (lo <= hi) {
        int cut1 = lo + (hi - lo) / 2;       // Elements from nums1 in left half
        int cut2 = (n + m + 1) / 2 - cut1;   // Elements from nums2 in left half

        int left1 = (cut1 == 0) ? INT_MIN : nums1[cut1 - 1];
        int left2 = (cut2 == 0) ? INT_MIN : nums2[cut2 - 1];
        int right1 = (cut1 == n) ? INT_MAX : nums1[cut1];
        int right2 = (cut2 == m) ? INT_MAX : nums2[cut2];

        if (left1 <= right2 && left2 <= right1) {
            // Found the correct partition
            if ((n + m) % 2 == 0) {
                return (std::max(left1, left2) + std::min(right1, right2)) / 2.0;
            } else {
                return std::max(left1, left2);
            }
        } else if (left1 > right2) {
            hi = cut1 - 1;
        } else {
            lo = cut1 + 1;
        }
    }

    return 0.0;  // Should never reach here
}

int main() {
    std::vector<int> nums1 = {1, 3};
    std::vector<int> nums2 = {2};

    std::cout << "Median: " << findMedianSortedArrays(nums1, nums2) << std::endl;
    // Output: 2.0

    std::vector<int> nums3 = {1, 2};
    std::vector<int> nums4 = {3, 4};

    std::cout << "Median: " << findMedianSortedArrays(nums3, nums4) << std::endl;
    // Output: 2.5

    return 0;
}
```

---

## 6.6 Ternary Search

### Concept

Ternary search finds the maximum or minimum of a **unimodal** function (first increasing then decreasing, or vice versa) in O(log n).

### How It Works

Divide the search range into three parts:
1. If f(m1) < f(m2), the extremum is in [m1, hi].
2. If f(m1) > f(m2), the extremum is in [lo, m2].
3. If f(m1) = f(m2), the extremum is in [m1, m2].

```cpp
#include <iostream>
#include <cmath>
#include <iomanip>

// Example: Find maximum of a unimodal function
// f(x) = -(x - 3)^2 + 10 (parabola with max at x=3)
double f(double x) {
    return -(x - 3.0) * (x - 3.0) + 10.0;
}

// Ternary search for maximum of unimodal function
// Time: O(log((hi-lo)/eps))
double ternarySearch(double lo, double hi, double eps = 1e-9) {
    while (hi - lo > eps) {
        double m1 = lo + (hi - lo) / 3;
        double m2 = hi - (hi - lo) / 3;

        if (f(m1) < f(m2)) {
            lo = m1;
        } else {
            hi = m2;
        }
    }

    return (lo + hi) / 2;
}

int main() {
    double maxX = ternarySearch(0, 10);
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "Maximum at x = " << maxX << std::endl;     // ≈ 3.0
    std::cout << "Maximum value = " << f(maxX) << std::endl;  // ≈ 10.0
    return 0;
}
```

### Ternary Search on Integers

```cpp
#include <iostream>
#include <vector>

// Find the maximum element in a bitonic array (first increasing, then decreasing)
int findPeakBitonic(const std::vector<int>& arr) {
    int lo = 0, hi = arr.size() - 1;

    while (lo < hi) {
        int m1 = lo + (hi - lo) / 3;
        int m2 = hi - (hi - lo) / 3;

        if (arr[m1] < arr[m2]) {
            lo = m1 + 1;
        } else {
            hi = m2 - 1;
        }
    }

    return lo;  // Index of maximum
}

int main() {
    std::vector<int> arr = {1, 3, 5, 7, 8, 6, 4, 2};
    int idx = findPeakBitonic(arr);
    std::cout << "Peak at index " << idx << ", value " << arr[idx] << std::endl;
    // Output: Peak at index 4, value 8
    return 0;
}
```

**When to use ternary search vs binary search:**
- Binary search: finding a specific value or boundary in a monotonic sequence.
- Ternary search: finding the extremum of a unimodal function.

**Note:** Binary search can also find the peak of a bitonic array (see Problem 2 below), and it's often preferred because it's simpler.

---

## 6.7 STL Search Functions

### std::binary_search

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    std::vector<int> arr = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};

    // Returns true/false, NOT the index
    bool found = std::binary_search(arr.begin(), arr.end(), 7);
    std::cout << "Found 7: " << found << std::endl;  // 1 (true)

    found = std::binary_search(arr.begin(), arr.end(), 11);
    std::cout << "Found 11: " << found << std::endl;  // 0 (false)

    return 0;
}
```

### std::lower_bound and std::upper_bound

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    std::vector<int> arr = {1, 2, 2, 2, 3, 4, 5};

    // lower_bound: first position where element >= target
    auto lb = std::lower_bound(arr.begin(), arr.end(), 2);
    std::cout << "lower_bound(2): index " << (lb - arr.begin()) << std::endl;  // 1

    // upper_bound: first position where element > target
    auto ub = std::upper_bound(arr.begin(), arr.end(), 2);
    std::cout << "upper_bound(2): index " << (ub - arr.begin()) << std::endl;  // 4

    // Count of 2s
    std::cout << "Count of 2: " << (ub - lb) << std::endl;  // 3

    // lower_bound for element not in array
    auto lb2 = std::lower_bound(arr.begin(), arr.end(), 0);
    std::cout << "lower_bound(0): index " << (lb2 - arr.begin()) << std::endl;  // 0

    auto lb3 = std::lower_bound(arr.begin(), arr.end(), 6);
    std::cout << "lower_bound(6): index " << (lb3 - arr.begin()) << std::endl;  // 7 (end)

    return 0;
}
```

### std::equal_range

Returns both lower_bound and upper_bound as a pair:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    std::vector<int> arr = {1, 2, 2, 2, 3, 4, 5};

    auto [lb, ub] = std::equal_range(arr.begin(), arr.end(), 2);
    std::cout << "Range: [" << (lb - arr.begin()) << ", " << (ub - arr.begin()) << ")" << std::endl;
    // Output: Range: [1, 4)
    std::cout << "Count: " << (ub - lb) << std::endl;  // 3

    return 0;
}
```

### Using Comparators

All STL search functions accept custom comparators:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <string>

struct Student {
    std::string name;
    int score;
};

int main() {
    std::vector<Student> students = {
        {"Alice", 80}, {"Bob", 85}, {"Charlie", 90}, {"Diana", 95}
    };

    // Find first student with score >= 85
    auto it = std::lower_bound(students.begin(), students.end(), 85,
        [](const Student& s, int score) {
            return s.score < score;
        });

    std::cout << "First with score >= 85: " << it->name << std::endl;  // Bob

    return 0;
}
```

---

## Interview Problems

### Problem 1: Search in Rotated Sorted Array

**Problem:** A sorted array is rotated at some pivot. Search for a target.

```cpp
#include <iostream>
#include <vector>

// Time: O(log n), Space: O(1)
int search(const std::vector<int>& nums, int target) {
    int lo = 0, hi = nums.size() - 1;

    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;

        if (nums[mid] == target) return mid;

        // Check which half is sorted
        if (nums[lo] <= nums[mid]) {
            // Left half is sorted
            if (nums[lo] <= target && target < nums[mid]) {
                hi = mid - 1;  // Target in sorted left half
            } else {
                lo = mid + 1;  // Target in right half
            }
        } else {
            // Right half is sorted
            if (nums[mid] < target && target <= nums[hi]) {
                lo = mid + 1;  // Target in sorted right half
            } else {
                hi = mid - 1;  // Target in left half
            }
        }
    }

    return -1;
}

int main() {
    std::vector<int> nums = {4, 5, 6, 7, 0, 1, 2};

    std::cout << "Search 0: " << search(nums, 0) << std::endl;  // 4
    std::cout << "Search 3: " << search(nums, 3) << std::endl;  // -1
    std::cout << "Search 6: " << search(nums, 6) << std::endl;  // 2

    return 0;
}
```

**Key insight:** In a rotated sorted array, at least one half is always sorted. Determine which half is sorted, then check if the target lies in that half.

### Problem 2: Find Peak Element

**Problem:** Find any peak element (greater than its neighbors) in O(log n).

```cpp
#include <iostream>
#include <vector>

// Time: O(log n), Space: O(1)
int findPeakElement(const std::vector<int>& nums) {
    int lo = 0, hi = nums.size() - 1;

    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;

        if (nums[mid] < nums[mid + 1]) {
            lo = mid + 1;  // Peak is to the right
        } else {
            hi = mid;       // Peak is at mid or to the left
        }
    }

    return lo;
}

int main() {
    std::vector<int> nums = {1, 2, 3, 1};
    std::cout << "Peak at index: " << findPeakElement(nums) << std::endl;  // 2

    std::vector<int> nums2 = {1, 2, 1, 3, 5, 6, 4};
    std::cout << "Peak at index: " << findPeakElement(nums2) << std::endl;  // 1 or 5

    return 0;
}
```

**Why it works:** If `nums[mid] < nums[mid+1]`, a peak must exist to the right (the array is going up). If `nums[mid] > nums[mid+1]`, a peak exists at mid or to the left.

### Problem 3: Capacity to Ship Packages (See Section 6.4)

### Problem 4: Aggressive Cows (See Section 6.4)

### Additional Problem: Find Minimum in Rotated Sorted Array

```cpp
#include <iostream>
#include <vector>

// Time: O(log n), Space: O(1)
int findMin(const std::vector<int>& nums) {
    int lo = 0, hi = nums.size() - 1;

    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;

        if (nums[mid] > nums[hi]) {
            lo = mid + 1;  // Minimum is in right half
        } else {
            hi = mid;       // Minimum is at mid or left
        }
    }

    return nums[lo];
}

int main() {
    std::vector<int> nums = {4, 5, 6, 7, 0, 1, 2};
    std::cout << "Minimum: " << findMin(nums) << std::endl;  // 0

    std::vector<int> nums2 = {2, 1};
    std::cout << "Minimum: " << findMin(nums2) << std::endl;  // 1

    return 0;
}
```

---

## Interview Tips

1. **Binary search is not just for arrays.** It applies to any monotonic predicate. Think "binary search on the answer" for optimization problems.

2. **Always clarify:** Is the array sorted? Are there duplicates? What should I return if the element is not found?

3. **The predicate must be monotonic.** If it's [F,F,F,T,T,T], binary search finds the first T. If it's [T,T,T,F,F,F], find the last T.

4. **Watch for integer overflow:** Use `lo + (hi - lo) / 2`, not `(lo + hi) / 2`.

5. **Off-by-one errors** are the #1 source of bugs. Test with:
   - Empty array
   - Single element
   - Target at boundaries
   - Target not in array

6. **For "binary search on answer" problems,** identify:
   - The search range (what are the possible answers?)
   - The predicate (what makes an answer valid?)
   - Whether you want the first T or last F

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---|---|---|
| `(lo + hi) / 2` overflow | Can exceed INT_MAX | Use `lo + (hi - lo) / 2` |
| `lo = mid` or `hi = mid` with `lo <= hi` | Infinite loop | Use `lo = mid + 1` or `hi = mid - 1` |
| Wrong loop condition | `lo < hi` vs `lo <= hi` depends on template | Match the template to the problem |
| Not handling duplicates | First/last occurrence logic differs | Use lower_bound/upper_bound patterns |
| Forgetting array must be sorted | Binary search requires sorted input | Sort first, or use different approach |
| Wrong precision for floating-point | `while (lo != hi)` can loop forever | Use `while (hi - lo > eps)` |

## Practice Problems

| # | Problem | Difficulty | Key Technique |
|---|---|---|---|
| 1 | Binary Search (basic) | Easy | Standard template |
| 2 | Search Insert Position | Easy | Lower bound |
| 3 | First Bad Version | Easy | Binary search on predicate |
| 4 | Search in Rotated Sorted Array | Medium | Modified binary search |
| 5 | Find Peak Element | Medium | Binary search on unsorted |
| 6 | Search a 2D Matrix | Medium | Treat as 1D array |
| 7 | Capacity to Ship Packages | Medium | Binary search on answer |
| 8 | Aggressive Cows | Medium | Binary search on answer |
| 9 | Median of Two Sorted Arrays | Hard | Binary search on partition |
| 10 | Split Array Largest Sum | Hard | Binary search on answer |

---

## See Also

- [Chapter 5: Sorting](ch05-sorting.md) — Sorting is often a prerequisite for binary search; many search problems assume sorted input.
- [Chapter 34: Two Pointers](ch34-two-pointers.md) — Two pointers on sorted arrays is a natural extension of binary search thinking.
- [Chapter 35: Sliding Window](ch35-sliding-window.md) — Another technique for searching through arrays; complements binary search for subarray problems.
- [Chapter 65: Searching Expanded](ch65-searching-expanded.md) — Advanced search techniques: ternary search, exponential search, and more.
- [Chapter 131: Parallel Binary Search](ch131-parallel-binary-search.md) — Solving multiple binary searches simultaneously; useful in offline algorithms.
- [Chapter 18: Segment Tree](ch18-segment-tree.md) — Binary search on segment trees enables order-statistic queries.

*In the next chapter, we'll study hashing — a technique that enables O(1) average-case lookups and is essential for many interview problems.*
