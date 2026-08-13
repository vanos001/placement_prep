# Meta (Facebook) Interview Preparation

## Overview

Meta's interview process is known for its emphasis on coding ability, system design at scale, and the "Move Fast" culture. Meta tends to focus more on practical coding and less on theoretical algorithms compared to Google.

## Interview Process

| Stage | Duration | Focus |
|-------|----------|-------|
| **Phone Screen** | 45 min | 1-2 coding problems |
| **Onsite (4-5 rounds)** | 45 min each | Coding, system design, behavioral |
| **Hiring Decision** | - | Packet review |

## What Meta Looks For

### 1. Coding (2-3 rounds)

Meta coding interviews tend to be more practical and less trick-heavy than Google's.

**Common topics:**
- Arrays and strings (frequent)
- Trees and graphs (very common)
- Hash tables
- Dynamic programming (moderate difficulty)
- BFS/DFS
- Sliding window
- Two pointers
- Stacks and queues

**Meta-specific patterns:**
- Heavy emphasis on graph problems
- Binary tree traversals and modifications
- String parsing and manipulation
- Real-world inspired problems

### 2. System Design (1-2 rounds for E4+, all rounds for E5+)

Meta system design interviews focus on social media scale systems.

**Common topics:**
- Design Facebook News Feed
- Design Instagram
- Design Messenger/WhatsApp
- Design Facebook Live
- Design a notification system
- Design a typeahead/autocomplete system
- Design a social graph

### 3. Behavioral (1 round)

Meta uses the "PEEL" framework:
- **Point**: State your main point
- **Evidence**: Provide specific examples
- **Explain**: Connect evidence to your point
- **Link**: Tie back to the question

**Key values:**
- Move Fast
- Boldness
- Openness
- Building Social Value
- Continuous Improvement

## Meta-Specific Tips

### Coding Approach

```python
# Meta prefers:
# 1. Working code over optimal code (get it working first)
# 2. Clear communication
# 3. Iterative improvement

# Example: Facebook-style problem
def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    """Merge overlapping meeting times."""
    if not intervals:
        return []
    
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    
    return merged
```

### System Design Framework (Meta Style)

1. **Requirements** (5 min)
   - What are we building?
   - Who uses it?
   - What's the scale?

2. **High-level design** (10 min)
   - Core components
   - Data flow
   - API design

3. **Deep dive** (15 min)
   - Database design
   - Scaling the read path
   - Scaling the write path
   - Caching strategy

4. **Bottlenecks and improvements** (10 min)
   - Single points of failure
   - Performance optimization
   - Monitoring and alerting

## Common Meta Interview Questions

### Algorithms (Meta-specific)

1. **Valid Palindrome II** — Two pointers, one deletion allowed
2. **Lowest Common Ancestor** — Binary tree LCA
3. **Binary Tree Right Side View** — BFS/level order
4. **Minimum Remove to Make Valid Parentheses** — Stack
5. **Subarray Sum Equals K** — Prefix sum + hash map
6. **Product of Array Except Self** — Prefix/suffix products
7. **Random Pick with Weight** — Binary search on prefix sums
8. **Merge Intervals** — Sorting + merging
9. **Dot Product of Two Sparse Vectors** — Design question
10. **Building with Ocean View** — Monotonic stack

### System Design

1. **Design Facebook News Feed** — Fanout, ranking, real-time updates
2. **Design Instagram** — Photo upload, feed generation, stories
3. **Design Messenger** — Real-time messaging, presence, delivery receipts
4. **Design Facebook Live** — Video streaming, comments, reactions
5. **Design a Notification System** — Push, email, SMS, preferences
6. **Design a Typeahead** — Trie, ranking, personalization

### Behavioral (Meta-specific)

1. Tell me about a time you moved fast and broke things
2. Describe a situation where you had to be bold
3. How do you handle receiving critical feedback?
4. Tell me about a time you simplified a complex system
5. Describe your approach to technical debt

## Level Expectations

| Level | Title | Coding | System Design | Experience |
|-------|-------|--------|---------------|------------|
| E3 | Software Engineer | Strong | N/A | 0-2 years |
| E4 | Software Engineer | Strong | Basic | 2-5 years |
| E5 | Senior Software Engineer | Expert | Strong | 5+ years |
| E6 | Staff Software Engineer | Expert | Expert | 8+ years |

## Meta vs Google Interviews

| Aspect | Meta | Google |
|--------|------|--------|
| **Coding focus** | Practical, graph-heavy | Algorithmic, DP-heavy |
| **System design** | Social media systems | Infrastructure systems |
| **Behavioral** | Move Fast, Boldness | Googleyness, Leadership |
| **Code quality** | Working first, optimize later | Clean and optimal from start |
| **Difficulty** | Moderate-High | High |

## Resources

- [LeetCode Meta tagged problems](https://leetcode.com/company/facebook/)
- Meta Engineering Blog
- [System Design Primer](https://github.com/donnemartin/system-design-primer)
- [Cracking the Coding Interview](http://www.crackingthecodinginterview.com/)

## Related Topics

- [System Design Framework](../system-design/framework.md) — How to approach system design
- [Coding Patterns](../coding/) — Common algorithm patterns
- [Google Interview](./google.md) — Comparison
- [Behavioral Interview](../behavioral/) — Soft skills
