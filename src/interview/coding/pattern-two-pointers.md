# Pattern Deep Dive: Two Pointers

The two pointers pattern reduces O(n^2) brute-force solutions to O(n) by exploiting sorted order or monotonic properties. It's one of the most frequently tested patterns in OAs.

## Template

```python
def two_pointers(arr):
    left, right = 0, len(arr) - 1
    while left < right:
        # Process arr[left] and arr[right]
        if condition:
            left += 1
        elif condition:
            right -= 1
        else:
            left += 1  # or right -= 1, or both
```

## Key Problems

### Two Sum II — Input Array Is Sorted

Given a sorted array, find two numbers that add up to target. Return 1-based indices.

```python
def two_sum_ii(numbers, target):
    left, right = 0, len(numbers) - 1
    while left < right:
        s = numbers[left] + numbers[right]
        if s == target:
            return [left + 1, right + 1]
        elif s < target:
            left += 1
        else:
            right -= 1
```
Complexity: O(n) time, O(1) space.

### 3Sum

Find all unique triplets that sum to zero.

```python
def three_sum(nums):
    nums.sort()
    result = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            continue
        left, right = i + 1, len(nums) - 1
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                result.append([nums[i], nums[left], nums[right]])
                while left < right and nums[left] == nums[left + 1]: left += 1
                while left < right and nums[right] == nums[right - 1]: right -= 1
                left += 1
                right -= 1
    return result
```
Complexity: O(n^2) time, O(1) space (excluding output).

### Container With Most Water

Find two vertical lines that together with the x-axis form a container holding the most water.

```python
def max_area(height):
    left, right = 0, len(height) - 1
    max_water = 0
    while left < right:
        width = right - left
        h = min(height[left], height[right])
        max_water = max(max_water, width * h)
        # Move the shorter line — moving the taller can only decrease area
        if height[left] < height[right]:
            left += 1
        else:
            right -= 1
    return max_water
```
Complexity: O(n) time, O(1) space.

### Trapping Rain Water

Given elevation map, compute how much water it can trap after raining.

```python
def trap(height):
    left, right = 0, len(height) - 1
    left_max, right_max = 0, 0
    water = 0
    while left < right:
        if height[left] < height[right]:
            left_max = max(left_max, height[left])
            water += left_max - height[left]
            left += 1
        else:
            right_max = max(right_max, height[right])
            water += right_max - height[right]
            right -= 1
    return water
```
Complexity: O(n) time, O(1) space.

## Common Variations

| Variation | Twist | Approach |
-----------|-------|----------|
| Remove duplicates from sorted array | In-place | Slow pointer tracks unique position |
| Move zeros to end | Maintain order | Non-zero pointer + zero pointer |
| Palindrome check | Single array | Two pointers from both ends |
| Sort colors (Dutch flag) | Three values | Three-way partition with left/mid/right pointers |
| Squares of sorted array | Negative numbers | Two pointers from both ends, fill result backwards |

## Interview Tips

- The key insight for two pointers: **which pointer moves, and why?** Always reason about this before coding
- When the problem says "sorted array," two pointers or binary search should be your first thought
- For 3Sum/4Sum, sort first, fix the outer elements, then use two pointers for the inner pair
- For trapping rain water, understand the "min of left_max and right_max" intuition before writing code
- If the array is not sorted, you can sort it (O(n log n)) only if the problem asks about values, not indices
