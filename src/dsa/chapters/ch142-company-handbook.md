# Chapter 142: Company-wise Preparation Guide

## Prerequisites
- All core DSA topics
- System design basics (for senior roles)
- Behavioral interview preparation

## Interview Frequency: ★★★★★

Every company has its own interview culture and focus areas. This chapter provides a **targeted preparation strategy** for each major tech company, based on documented patterns from thousands of interview reports.

---

## 142.1 Google

### Focus Areas
- **Primary:** Hard algorithms, system design, DP, graphs
- **Frequency:** DP, Trees, Graphs, Binary Search, Recursion, Math
- **Style:** Pure algorithmic problem-solving with follow-up challenges

### What Makes Google Different
- Problems often have **multiple follow-ups** that increase difficulty
- Strong emphasis on **code quality** and handling edge cases
- Interviewers expect you to **analyze complexity** proactively
- System design rounds focus on **scalability** and **trade-offs**

### Common Problem Types
| Topic | Frequency | Example |
|---|---|---|
| Dynamic Programming | Very High | Interval DP, knapsack variants |
| Graph Algorithms | High | BFS/DFS, shortest path, topological sort |
| Trees | High | LCA, serialization, BST operations |
| Binary Search | Medium-High | Search space reduction |
| Math/Probability | Medium | Combinatorics, expected value |

### Preparation Tips
1. Practice **explaining your thought process** out loud
2. Always discuss **time and space complexity** before coding
3. Write **clean, production-quality code** — Google reviewers notice
4. Prepare for **"what if" follow-ups** (what if the input is huge? what if we need online processing?)
5. Study system design at scale (GFS, MapReduce, Bigtable concepts)

### Sample Google-Style Problem
```
Given a matrix of 0s and 1s, find the largest rectangle containing only 1s.
Follow-up 1: What if the matrix is streaming (rows arrive one at a time)?
Follow-up 2: What if we need to answer multiple queries on sub-matrices?
```

---

## 142.2 Meta (Facebook)

### Focus Areas
- **Primary:** Practical problems, graphs, trees, arrays
- **Frequency:** BFS/DFS, DP, Arrays, Strings, Trees
- **Style:** Collaborative, iterative refinement

### What Makes Meta Different
- Strong emphasis on **communication** and **collaborative problem-solving**
- Interviewers want to see you **iterate on solutions** (brute force → optimize)
- Problems are often **practical** (related to social graphs, news feed, etc.)
- Cultural fit is important — be **humble, open to feedback**

### Common Problem Types
| Topic | Frequency | Example |
|---|---|---|
| Arrays/Strings | Very High | Two pointers, sliding window |
| BFS/DFS | Very High | Graph traversal, island problems |
| Trees | High | Binary tree operations, BST |
| DP | High | 1D/2D DP, string matching |
| Design | Medium | News feed, friend suggestions |

### Preparation Tips
1. Start with the **brute force** solution, then optimize
2. **Communicate constantly** — explain your reasoning at each step
3. Be open to **hints from the interviewer** — they want to help
4. Practice **iterative refinement**: "I notice this can be improved by..."
5. Prepare behavioral stories using the **STAR method**

### Sample Meta-Style Problem
```
Given a list of user sessions (login/logout times), find the top K users
with the longest total session time.
Follow-up: How would you handle this with billions of users?
```

---

## 142.3 Amazon

### Focus Areas
- **Primary:** Leadership principles + coding
- **Frequency:** Arrays, Strings, Trees, Graphs, DP
- **Style:** LP-driven behavioral + standard coding

### What Makes Amazon Different
- **Leadership Principles (LPs)** are as important as coding
- Every behavioral question maps to specific LPs
- Coding problems are **medium difficulty** but require clean execution
- Bar raiser round focuses on **cultural fit**

### Amazon's 16 Leadership Principles
| Principle | Interview Relevance |
|---|---|
| Customer Obsession | Design decisions, prioritization |
| Ownership | Taking initiative, going beyond scope |
| Invent and Simplify | Creative solutions, reducing complexity |
| Are Right, A Lot | Decision-making, trade-off analysis |
| Learn and Be Curious | Learning new technologies, growth mindset |
| Hire and Develop the Best | Mentoring, team building (senior roles) |
| Insist on the Highest Standards | Code quality, testing |
| Think Big | System design, vision |
| Bias for Action | Speed of execution, calculated risk |
| Frugality | Resource optimization |
| Earn Trust | Communication, transparency |
| Dive Deep | Debugging, root cause analysis |
| Have Backbone; Disagree and Commit | Technical disagreements |
| Deliver Results | Completing projects, meeting deadlines |

### Common Problem Types
| Topic | Frequency | Example |
|---|---|---|
| Arrays/Strings | Very High | Subarray sum, string manipulation |
| Trees | Very High | BST, N-ary trees, serialization |
| Graphs | High | Course schedule, network delay |
| DP | Medium-High | Coin change, longest subsequence |
| System Design | High (senior) | E-commerce, distributed systems |

### Preparation Tips
1. Prepare **2-3 STAR stories for each LP** — you'll need them
2. Use **"I" not "we"** in behavioral answers
3. Include **metrics and numbers** in your stories
4. For coding: focus on **correctness over optimization** first
5. Practice **Amazon-style system design** (scale, availability, cost)

### Sample Amazon-Style Problem
```
Design a system to recommend products to users based on their browsing history.
Coding: Implement a function to find the top K most frequently purchased items
in a given time window.
```

---

## 142.4 Apple

### Focus Areas
- **Primary:** Systems knowledge, clean code
- **Frequency:** Arrays, Strings, Trees, Design, Low-level
- **Style:** Attention to detail, edge cases, systems thinking

### What Makes Apple Different
- Strong focus on **code quality** and **edge case handling**
- Interviewers are very **detail-oriented**
- System design focuses on **user experience** and **performance**
- Apple values **elegance** and **simplicity** in solutions

### Common Problem Types
| Topic | Frequency | Example |
|---|---|---|
| Arrays/Strings | Very High | Manipulation, parsing |
| Trees | High | BST, trie, file systems |
| System Design | High | iOS frameworks, iCloud |
| Bit Manipulation | Medium | Hardware-related problems |
| Concurrency | Medium | Thread safety, async patterns |

### Preparation Tips
1. **Test your code mentally** — trace through edge cases
2. Pay attention to **naming conventions** and **code style**
3. Consider **memory efficiency** — Apple cares about resource usage
4. Prepare for **low-level questions** (memory management, pointers)
5. Think about **user experience** in system design

### Sample Apple-Style Problem
```
Implement a thread-safe LRU cache with O(1) get and put operations.
Follow-up: How would you handle cache invalidation across multiple devices?
```

---

## 142.5 Microsoft

### Focus Areas
- **Primary:** Standard algorithms, clean code
- **Frequency:** Arrays, Strings, Trees, DP, Graphs
- **Style:** Collaborative problem-solving, mentorship-oriented

### What Makes Microsoft Different
- Interviewers are often **helpful and collaborative**
- Problems are **fair and well-defined**
- Strong emphasis on **testing** and **edge cases**
- Cultural fit emphasizes **growth mindset** and **teamwork**

### Common Problem Types
| Topic | Frequency | Example |
|---|---|---|
| Arrays/Strings | Very High | Sorting, searching, manipulation |
| Trees | Very High | Binary tree, BST, serialization |
| DP | High | Knapsack, LCS, edit distance |
| Graphs | Medium-High | BFS/DFS, shortest path |
| Design | Medium | Azure services, Office features |

### Preparation Tips
1. **Communicate your approach** before coding
2. Write **test cases** before implementing
3. Be **open to feedback** — Microsoft interviewers give hints
4. Practice **debugging** — they may ask you to fix broken code
5. Prepare for **"why" questions** — why this approach? why this data structure?

### Sample Microsoft-Style Problem
```
Given a binary tree, find the maximum path sum (path can start and end at any node).
Follow-up: What if the tree is a binary search tree?
```

---

## 142.6 ByteDance

### Focus Areas
- **Primary:** Competitive programming style
- **Frequency:** DP, Graphs, Trees, Advanced algorithms
- **Style:** Speed, optimization, hard problems

### What Makes ByteDance Different
- Problems are often **competitive programming level**
- Strong emphasis on **speed** — you need to code fast
- Interviewers expect **optimal solutions** quickly
- Multiple rounds may be back-to-back (intensity)

### Common Problem Types
| Topic | Frequency | Example |
|---|---|---|
| DP | Very High | Interval DP, digit DP, bitmask DP |
| Graphs | Very High | Shortest path, network flow |
| Trees | High | Heavy-light decomposition, centroid |
| Math | Medium-High | Number theory, combinatorics |
| Data Structures | Medium-High | Segment tree, BIT, trie |

### Preparation Tips
1. Practice **competitive programming** on LeetCode, Codeforces
2. Focus on **speed** — solve medium problems in 15 minutes
3. Know **advanced data structures** (segment tree, BIT, sparse table)
4. Practice **multiple approaches** for each problem
5. Be ready for **hard problems** — ByteDance doesn't hold back

### Sample ByteDance-Style Problem
```
Given an array of n integers, find the number of subarrays whose sum is divisible by k.
Constraints: n ≤ 10^5, k ≤ 10^9
Expected solution: O(n) using prefix sums and modular arithmetic
```

---

## 142.7 Netflix

### Focus Areas
- **Primary:** System design, senior-level thinking
- **Frequency:** Design, Architecture, Coding
- **Style:** Scalability thinking, trade-offs, high-level

### What Makes Netflix Different
- Interview focuses heavily on **system design** and **architecture**
- Coding problems are **medium difficulty** but require elegant solutions
- Strong emphasis on **scalability** and **reliability**
- Netflix values **freedom and responsibility** culture

### Common Problem Types
| Topic | Frequency | Example |
|---|---|---|
| System Design | Very High | Video streaming, recommendation engine |
| Coding | Medium | Arrays, strings, basic algorithms |
| Architecture | High | Microservices, event-driven systems |
| Reliability | High | Failure handling, redundancy |
| Data | Medium | ETL, real-time processing |

### Preparation Tips
1. Study **Netflix's tech blog** — they publish a lot
2. Focus on **distributed systems** concepts
3. Prepare for **trade-off discussions** — there are no perfect answers
4. Think about **cost optimization** — Netflix cares about efficiency
5. Practice **high-level design** before diving into details

### Sample Netflix-Style Problem
```
Design a system to deliver personalized video recommendations to 200M+ users.
Consider: data pipeline, model serving, A/B testing, real-time updates.
```

---

## 142.8 Other Major Companies

### Apple vs Google vs Meta (Comparison)

| Dimension | Google | Meta | Apple |
|---|---|---|---|
| Difficulty | Hard | Medium-Hard | Medium |
| Focus | Algorithms | Communication | Detail |
| Follow-ups | Yes, progressive | Yes, iterative | Yes, edge cases |
| Cultural | Innovation | Move fast | Excellence |

### Startups (General)

| Aspect | Expectation |
|---|---|
| Coding | Medium difficulty, practical problems |
| System Design | Basic to intermediate |
| Culture | Scrappy, resourceful, adaptable |
| Speed | Faster process, fewer rounds |

### Quant Firms (Two Sigma, Jane Street, Citadel)

| Aspect | Expectation |
|---|---|
| Coding | Hard, math-heavy |
| Math | Probability, statistics, combinatorics |
| Puzzles | Brain teasers, estimation |
| Speed | Very fast problem-solving |

---

## 142.9 Universal Preparation Framework

### Week-by-Week Plan (8 weeks)

| Week | Focus | Hours/Day |
|---|---|---|
| 1-2 | Arrays, Strings, Two Pointers | 3-4 |
| 3-4 | Trees, Graphs, BFS/DFS | 3-4 |
| 5-6 | DP, Greedy, Backtracking | 3-4 |
| 7 | System Design, Behavioral | 4-5 |
| 8 | Mock Interviews, Review | 4-5 |

### Daily Routine

```
Morning (1 hour):   Review 2-3 previously solved problems
Afternoon (2 hours): Solve 2-3 new problems (company-specific)
Evening (1 hour):   Read system design / behavioral prep
```

### Problem-Solving Template

```
1. UNDERSTAND: Restate the problem in your own words
2. EXAMPLES: Walk through 2-3 examples manually
3. APPROACH: Discuss brute force, then optimize
4. CODE: Write clean, well-structured code
5. TEST: Trace through your code with examples
6. ANALYZE: State time and space complexity
```

---

## 142.10 Summary

| Company | Focus | Key Differentiator | Difficulty |
|---|---|---|---|
| Google | Algorithmic depth | Hard problems + follow-ups | ★★★★★ |
| Meta | Communication | Iterative improvement | ★★★★ |
| Amazon | Leadership principles | LP + code combination | ★★★★ |
| Apple | Systems thinking | Clean implementation | ★★★★ |
| Microsoft | Collaboration | Problem-solving approach | ★★★ |
| ByteDance | Speed | Competitive programming | ★★★★★ |
| Netflix | Scalability | System design depth | ★★★★ |

## Exercises

1. **Research:** Find 5 recent interview questions from your target company on LeetCode/Glassdoor. Solve each one.
2. **Mock:** Conduct a mock interview with a friend, focusing on your weakest company-specific area.
3. **Behavioral:** Write out STAR stories for 5 leadership principles (Amazon) or 5 company values.
4. **System Design:** Design a URL shortener. Practice explaining it in 30 minutes.
5. **Speed:** Solve 3 medium LeetCode problems in 45 minutes. Time yourself.

## Interview Questions

1. **Q:** How should I prepare differently for Google vs Amazon?
   **A:** For Google, focus on hard algorithms and follow-up questions. For Amazon, balance coding with leadership principle stories — they're equally important.

2. **Q:** What if I get a problem I've never seen before?
   **A:** Start with brute force, identify patterns, break it into subproblems, and communicate your thought process. Interviewers value problem-solving approach over memorized solutions.

3. **Q:** How important is system design for a new grad?
   **A:** Less important than coding, but still tested at some companies (especially Meta and Amazon). Focus on basic concepts: scalability, caching, databases, and load balancing.

## Cross-References
- All algorithm chapters in this book
- System design: Chapter 140
- Behavioral interviews: Chapter 141
- Mock interview strategies: Chapter 143
