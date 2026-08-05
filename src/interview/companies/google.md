# Google Interview Preparation

## Overview

Google is known for its rigorous technical interview process that emphasizes algorithms, system design, and Googleyness (culture fit). The process typically involves 4-6 interviews with a strong focus on problem-solving ability and code quality.

## Interview Process

| Stage | Duration | Focus |
|-------|----------|-------|
| **Phone Screen** | 45 min | 1-2 coding problems |
| **Onsite (4-5 rounds)** | 45 min each | Coding, system design, Googleyness |
| **Hiring Committee** | - | Reviews all feedback |
| **Team Match** | - | Finding the right team |

## What Google Looks For

### 1. Coding (2-3 rounds)

- **Algorithms**: Sorting, searching, graph traversal, dynamic programming
- **Data structures**: Arrays, linked lists, trees, graphs, hash maps, heaps
- **Code quality**: Clean, readable, well-structured code
- **Testing**: Think about edge cases, write test cases
- **Communication**: Explain your thought process clearly

**Common topics:**
- Graph algorithms (BFS, DFS, Dijkstra, topological sort)
- Dynamic programming (memoization, tabulation)
- Tree traversals and manipulations
- String manipulation and pattern matching
- Binary search variations
- Sliding window and two pointers

### 2. System Design (1-2 rounds for L4+, all rounds for L5+)

- **Scale**: Design for billions of users
- **Trade-offs**: Discuss pros and cons of decisions
- **Depth**: Go deep on components you're familiar with
- **Breadth**: Cover all major components

**Common topics:**
- Design a URL shortener
- Design a chat system
- Design YouTube/Netflix
- Design Google Search
- Design Google Maps
- Design a distributed file system (GFS)
- Design MapReduce

### 3. Googleyness (1 round)

- **Leadership**: How you handle ambiguity and lead projects
- **Collaboration**: Working with others, handling disagreements
- **Impact**: Your contributions and their significance
- **Learning**: How you grow from failures

## Google-Specific Tips

### Coding Style

```python
# Google prefers:
# 1. Clear variable names
# 2. Modular code (separate functions)
# 3. Defensive programming (check inputs)

def find_median_sorted_arrays(nums1: List[int], nums2: List[int]) -> float:
    """Find median of two sorted arrays in O(log(min(m,n)))."""
    if len(nums1) > len(nums2):
        nums1, nums2 = nums2, nums1
    
    m, n = len(nums1), len(nums2)
    left, right = 0, m
    
    while left <= right:
        partition1 = (left + right) // 2
        partition2 = (m + n + 1) // 2 - partition1
        
        max_left1 = float('-inf') if partition1 == 0 else nums1[partition1 - 1]
        min_right1 = float('inf') if partition1 == m else nums1[partition1]
        max_left2 = float('-inf') if partition2 == 0 else nums2[partition2 - 1]
        min_right2 = float('inf') if partition2 == n else nums2[partition2]
        
        if max_left1 <= min_right2 and max_left2 <= min_right1:
            if (m + n) % 2 == 0:
                return (max(max_left1, max_left2) + min(min_right1, min_right2)) / 2
            else:
                return max(max_left1, max_left2)
        elif max_left1 > min_right2:
            right = partition1 - 1
        else:
            left = partition1 + 1
```

### System Design Framework

1. **Clarify requirements** (5 min)
   - Functional requirements
   - Non-functional requirements (scale, latency, availability)
   - Constraints

2. **Estimate scale** (5 min)
   - Users, QPS, storage, bandwidth

3. **Design high-level** (10 min)
   - Major components
   - Data flow
   - API design

4. **Deep dive** (15 min)
   - Database schema
   - Key algorithms
   - Scalability bottlenecks

5. **Discuss trade-offs** (5 min)
   - CAP theorem choices
   - Consistency vs availability
   - Cost vs performance

## Common Google Interview Questions

### Algorithms

1. **Two Sum** — Hash map approach, O(n)
2. **Longest Substring Without Repeating Characters** — Sliding window
3. **Merge k Sorted Lists** — Heap/priority queue
4. **Word Ladder** — BFS
5. **Trapping Rain Water** — Two pointers or stack
6. **Regular Expression Matching** — DP
7. **Median of Two Sorted Arrays** — Binary search
8. **Longest Palindromic Substring** — Expand around center or Manacher's
9. **Serialize and Deserialize Binary Tree** — DFS/BFS
10. **Alien Dictionary** — Topological sort

### System Design

1. **Design Google Search** — Crawling, indexing, ranking, serving
2. **Design YouTube** — Upload, transcode, serve, recommend
3. **Design Google Maps** — Tiles, routing, geocoding
4. **Design Gmail** — Storage, search, spam filtering
5. **Design Google Drive** — File sync, deduplication, sharing
6. **Design a CDN** — Edge servers, cache invalidation
7. **Design a Distributed Lock Manager** — Paxos, Chubby

### Behavioral

1. Tell me about a time you had to make a difficult technical decision
2. Describe a project where you had to work with ambiguous requirements
3. How do you handle disagreements with teammates?
4. Tell me about a time you failed and what you learned
5. Describe your most impactful project

## Level Expectations

| Level | Title | Coding | System Design | Experience |
|-------|-------|--------|---------------|------------|
| L3 | SWE II | Strong | N/A | 0-2 years |
| L4 | SWE III | Strong | Basic | 2-5 years |
| L5 | Senior SWE | Expert | Strong | 5+ years |
| L6 | Staff SWE | Expert | Expert | 8+ years |

## Resources

- [LeetCode Google tagged problems](https://leetcode.com/company/google/)
- [Cracking the Coding Interview](http://www.crackingthecodinginterview.com/)
- [Designing Data-Intensive Applications](https://dataintensive.net/)
- [System Design Interview](https://www.amazon.com/System-Design-Interview-insiders-Second/dp/B08CMF2CQF)
- Google Engineering Blog
- MIT 6.824 Distributed Systems

## Related Topics

- [System Design Framework](../system-design/framework.md) — How to approach system design
- [Coding Patterns](../coding/) — Common algorithm patterns
- [Behavioral Interview](../behavioral/) — Soft skills preparation
- [Meta Interview](./meta.md) — Similar but different focus
