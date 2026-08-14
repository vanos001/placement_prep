# Pattern Deep Dive: Frequency Counting / Hash Map

Frequency counting is the most versatile pattern in interviews. It appears as the primary technique in easy problems and as a supporting component in medium and hard problems.

## Core Idea

Use a hash map (Python `dict` or `Counter`) to count occurrences, then query the counts to answer questions about grouping, ranking, or detecting properties.

## Template

```python
from collections import Counter

def frequency_template(nums):
    count = Counter(nums)       # O(n) build
    # Query counts as needed
    for key, freq in count.items():
        # process
```

## Key Problems

### Valid Anagram

Given two strings s and t, check if t is an anagram of s.

```python
def is_anagram(s: str, t: str) -> bool:
    return Counter(s) == Counter(t)
```
Complexity: O(n) time, O(1) space (26 letters for lowercase English).

### Group Anagrams

Given an array of strings, group anagrams together.

```python
from collections import defaultdict

def group_anagrams(strs: list) -> list:
    groups = defaultdict(list)
    for s in strs:
        key = tuple(sorted(s))      # sorted string as key
        groups[key].append(s)
    return list(groups.values())
```
Complexity: O(n * k log k) time where k = avg string length, O(n * k) space.

### Top K Frequent Elements

Given an array, return the k most frequent elements.

```python
import heapq

def top_k_frequent(nums: list, k: int) -> list:
    count = Counter(nums)
    # Min-heap of size k — O(n log k)
    return heapq.nlargest(k, count.keys(), key=count.get)
```
Complexity: O(n log k) time, O(n) space.

### Longest Consecutive Sequence

Given an unsorted array, find the length of the longest consecutive elements sequence.

```python
def longest_consecutive(nums: list) -> int:
    num_set = set(nums)
    longest = 0
    for num in num_set:
        # Only start counting from the beginning of a sequence
        if num - 1 not in num_set:
            current = num
            streak = 1
            while current + 1 in num_set:
                current += 1
                streak += 1
            longest = max(longest, streak)
    return longest
```
Complexity: O(n) time (each element visited at most twice), O(n) space.

## Common Variations

| Variation | Twist | Approach |
-----------|-------|----------|
| Frequency of elements in a range | Subarray query | Prefix sum of frequencies, or Mo's algorithm |
| Most common word (banned list) | Filter before counting | Count, then exclude banned words |
| Find all duplicates | Values in [1, n] | Negate at index (O(1) space) or Counter |
| Sort characters by frequency | Build output from counts | Sort items by count, then repeat |
| Subarray sum equals K | Prefix sum + hash map | Track `prefix_sum - target` in map |

## Interview Tips

- When you see "group by," "anagram," "frequency," "count," or "most common," reach for a hash map immediately
- For character-counting problems with only lowercase English letters, a fixed-size array of length 26 is faster than a hash map
- `Counter` is idiomatic Python — use it in interviews to save time, but understand how it works internally
- If space is constrained (e.g., O(1) extra), consider the negate-at-index trick when values are in [1, n]
