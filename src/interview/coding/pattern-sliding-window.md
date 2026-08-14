# Pattern Deep Dive: Sliding Window

The sliding window pattern solves problems on contiguous subarrays or substrings in O(n) time by maintaining a window that expands and contracts. It replaces O(n^2) brute-force enumeration of all subarrays.

## Templates

### Fixed-Size Window

```python
def fixed_window(arr, k):
    window_sum = sum(arr[:k])
    best = window_sum
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]
        best = max(best, window_sum)
    return best
```

### Variable-Size Window

```python
def variable_window(s):
    left = 0
    result = 0
    window = {}
    for right in range(len(s)):
        # Expand: add s[right] to window
        window[s[right]] = window.get(s[right], 0) + 1
        # Shrink while window is invalid
        while invalid(window):
            window[s[left]] -= 1
            if window[s[left]] == 0:
                del window[s[left]]
            left += 1
        # Update result
        result = max(result, right - left + 1)
    return result
```

## Key Problems

### Best Time to Buy and Sell Stock

Find the maximum profit from one buy and one sell transaction.

```python
def max_profit(prices):
    min_price = float('inf')
    max_profit = 0
    for price in prices:
        min_price = min(min_price, price)
        max_profit = max(max_profit, price - min_price)
    return max_profit
```

This is a degenerate sliding window where the left boundary is the minimum price seen so far.

Complexity: O(n) time, O(1) space.

### Longest Substring Without Repeating Characters

```python
def length_of_longest_substring(s):
    seen = {}
    left = 0
    longest = 0
    for right, ch in enumerate(s):
        if ch in seen and seen[ch] >= left:
            left = seen[ch] + 1
        seen[ch] = right
        longest = max(longest, right - left + 1)
    return longest
```

Complexity: O(n) time, O(min(n, m)) space where m = charset size.

### Minimum Window Substring

Find the smallest substring of s containing all characters of t.

```python
from collections import Counter

def min_window(s, t):
    need = Counter(t)
    missing = len(t)
    left = 0
    start, end = 0, float('inf')
    for right, ch in enumerate(s):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        while missing == 0:
            if right - left < end - start:
                start, end = left, right
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return s[start:end + 1] if end != float('inf') else ""
```

Complexity: O(|s| + |t|) time, O(|t|) space.

### Longest Repeating Character Replacement

You can replace any character at most k times. Find the longest substring of all same characters.

```python
def character_replacement(s, k):
    count = {}
    max_freq = 0
    left = 0
    result = 0
    for right, ch in enumerate(s):
        count[ch] = count.get(ch, 0) + 1
        max_freq = max(max_freq, count[ch])
        # Window size - max_freq = replacements needed
        while (right - left + 1) - max_freq > k:
            count[s[left]] -= 1
            left += 1
        result = max(result, right - left + 1)
    return result
```

Complexity: O(n) time, O(1) space (26 letters).

## Common Variations

| Variation | Twist | Approach |
-----------|-------|----------|
| Subarray sum >= target | Minimum length subarray | Shrink from left when sum >= target |
| Permutation in string | Window equals target exactly | Compare frequency maps |
| Max consecutive ones III | Flip at most k zeros | Window with at most k zeros |
| Fruit into baskets | At most 2 types of fruit | Window with at most 2 distinct values |
| Sliding window maximum | Fixed window, track max | Use monotonic deque (not basic window) |

## Interview Tips

- **Identify the shrink condition** before coding — this is where most bugs occur
- If the problem says "contiguous subarray" or "substring," sliding window should be your first thought
- The fixed-size variant is simpler: just add new element, remove old element, update result
- For the variable-size variant, decide: **do you shrink while invalid, or expand while valid?** Both work, but consistency prevents bugs
- Use `collections.Counter` for frequency-based window validity checks — it handles the bookkeeping cleanly
