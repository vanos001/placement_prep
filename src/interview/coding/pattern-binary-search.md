# Pattern Deep Dive: Binary Search

Binary search reduces search time from O(n) to O(log n) on sorted or monotonic data. The more powerful variant — **binary search on answer** — applies the same logic to search spaces that aren't arrays at all.

## Standard Template

```python
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

## Binary Search on Answer Template

Used when the answer is a value (not an index) and there's a monotonic predicate: "if capacity X works, then any capacity > X also works."

```python
def binary_search_on_answer(lo, hi):
    while lo < hi:
        mid = (lo + hi) // 2
        if is_feasible(mid):
            hi = mid          # try smaller
        else:
            lo = mid + 1      # need larger
    return lo
```

## Key Problems

### Binary Search (standard)

```python
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```
Complexity: O(log n) time, O(1) space.

### Search in Rotated Sorted Array

```python
def search_rotated(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:           # left half is sorted
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                                 # right half is sorted
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
```
Complexity: O(log n) time, O(1) space.

### Find Minimum in Rotated Sorted Array

```python
def find_min(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1
        else:
            hi = mid
    return nums[lo]
```
Complexity: O(log n) time, O(1) space.

### Koko Eating Bananas

Koko can eat at most `k` bananas per hour from any pile. Find the minimum `k` to eat all bananas within `h` hours.

```python
def min_eating_speed(piles, h):
    lo, hi = 1, max(piles)
    while lo < hi:
        mid = (lo + hi) // 2
        hours = sum((p + mid - 1) // mid for p in piles)  # ceil division
        if hours <= h:
            hi = mid
        else:
            lo = mid + 1
    return lo
```
Complexity: O(n log m) time where m = max(pile), O(1) space.

### Capacity to Ship Packages Within D Days

Find the minimum ship capacity to ship all weights within D days (packages must be shipped in order).

```python
def ship_within_days(weights, days):
    lo, hi = max(weights), sum(weights)
    while lo < hi:
        mid = (lo + hi) // 2
        required_days, current_load = 1, 0
        for w in weights:
            if current_load + w > mid:
                required_days += 1
                current_load = 0
            current_load += w
        if required_days <= days:
            hi = mid
        else:
            lo = mid + 1
    return lo
```
Complexity: O(n log S) time where S = sum of weights, O(1) space.

## Common Variations

| Variation | Twist | Approach |
-----------|-------|----------|
| Find first/last occurrence | Duplicates in sorted array | After finding target, keep searching left/right |
| Square root of x | No built-in sqrt | Search [0, x] for largest n where n^2 <= x |
| Kth smallest in sorted matrix | 2D sorted | Binary search on value, count elements <= mid |
| Split array largest sum | Partition into m subarrays | Binary search on max sum, greedily count partitions |
| Aggressive cows | Place cows with max min-distance | Binary search on distance, check feasibility |

## Interview Tips
- When you see "sorted" and "find/minimum/maximum," binary search should be your first thought
- For binary search on answer, **clearly identify the monotonic predicate** — write `is_feasible(mid)` as a separate function
- Use `lo < hi` (not `lo <= hi`) for the "find minimum feasible" variant to avoid infinite loops
- The `mid = (lo + hi) // 2` can overflow in languages with fixed-width integers — use `lo + (hi - lo) // 2` in Java/C++
- Practice the rotated array variants until you can reason about which half is sorted without drawing it out
