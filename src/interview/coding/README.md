# Coding Interview Preparation

## Overview

This section is the complete technical-interview track: strategy pages for the online-assessment gauntlet, a framework for live problem solving, and pattern deep-dives that turn 20 recurring techniques into muscle memory. The pages are ordered by the way hiring actually proceeds — most companies run an online assessment first, then an MCQ screen, then a phone screen, then onsite rounds — and each page states which stage it serves. Start with the page index below if you know your stage, or with a study plan at the bottom if you know your deadline but not your plan.

> *"In preparing for battle I have always found that plans are useless, but planning is indispensable."* — Dwight D. Eisenhower

## 🎯 What Coding Interviews Test

Coding interviews evaluate **far more** than your ability to write code. Interviewers assess:

```
┌─────────────────────────────────────────────────────────┐
│              CODING INTERVIEW EVALUATION                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Problem Solving (40%)                               │
│     ├── Understanding the problem                       │
│     ├── Breaking it down                                │
│     ├── Identifying patterns                            │
│     └── Handling edge cases                             │
│                                                         │
│  2. Technical Knowledge (30%)                           │
│     ├── Data structure selection                        │
│     ├── Algorithm design                                │
│     ├── Complexity analysis                             │
│     └── Language proficiency                            │
│                                                         │
│  3. Communication (20%)                                 │
│     ├── Explaining your approach                        │
│     ├── Asking clarifying questions                     │
│     ├── Discussing trade-offs                           │
│     └── Responding to hints                             │
│                                                         │
│  4. Code Quality (10%)                                  │
│     ├── Readable variable names                         │
│     ├── Clean structure                                 │
│     ├── Error handling                                  │
│     └── Testing                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

The weightings explain the section's structure: strategy pages maximize what you control in the first two stages, the framework page trains communication, and the pattern pages build the recognition that problem solving depends on. Note that communication is 20% on its own — more than code quality and nearly as much as technical knowledge — which is why the framework page insists on narrating your approach. Practicing silently at a desk trains exactly the skill interviews do not reward.

## 📚 Complete Page Index

Every file in this section, with what it covers and when to open it:

| Page | Focus | Open it when… |
|------|-------|---------------|
| [README](./README.md) | This index, stage routing, and study plans | Planning your prep or lost about where to start |
| [Online Assessment Strategies](./oa-strategies.md) | Platform quirks (HackerRank/Codility/CodeSignal), time allocation, template library, verify-before-submit loop | You have an OA scheduled — this is the first page to read |
| [MCQ Strategies](./mcq-strategies.md) | Pacing math, elimination techniques, distractor patterns, negative-marking EV arithmetic, OS/DBMS/Networks/OOP playbooks | Your OA includes a 15–30 question fundamentals round |
| [Reading Pseudocode](./pseudocode-reading.md) | Variable-table tracing, call trees, complexity drills, logic-bug spotting | The OA shows pseudocode snippets or "predict the output" questions |
| [Coding Framework](./framework.md) | The UMPIRE method (Understand, Match, Plan, Implement, Review, Evaluate) with scripts for live interviews | Preparing for phone screens and onsite rounds |
| [Problem Patterns](./patterns.md) | The full patterns reference — the largest page in this section | You want the complete catalog with examples per pattern |
| [20 Essential Patterns](./coding-patterns-guide.md) | Quick-reference version of the 20 highest-yield patterns | Last-week review or quick lookup between mocks |
| [Pattern: Two Pointers](./pattern-two-pointers.md) | Sorted-array pair scanning, in-place partitioning | Practicing the most frequent OA pattern |
| [Pattern: Sliding Window](./pattern-sliding-window.md) | Contiguous subarray/substring problems in O(n) | Longest/shortest substring and subarray questions |
| [Pattern: Frequency Counting](./pattern-frequency-counting.md) | Hash-map counting, anagrams, presence checks | Any "count", "duplicate", or "first unique" problem |
| [Pattern: Binary Search](./pattern-binary-search.md) | Classic binary search plus binary-search-on-answer | Monotonic search spaces and "minimize the maximum" problems |
| [Complexity Analysis](./complexity.md) | Big-O hierarchy, amortized analysis, space-time trade-offs | Choosing between approaches or defending complexity in interviews |
| [Data Structures](./data-structures.md) | Complete reference: arrays, trees, graphs, hash maps, heaps | Selecting structures during the Plan step |

The four pattern deep-dives are deliberately narrow — one technique, worked end to end — while `patterns.md` is deliberately broad. Read the deep-dives when learning a pattern for the first time and the big reference when you need a refresher on all of them. The three strategy pages (OA, MCQ, pseudocode) are stage-specific: they pay off immediately before an assessment and age quickly, so schedule them last in any plan.

Two habits make the index pay off regardless of which plan you follow. First, read each strategy page *twice*: once a week before the assessment for the method, and once the day before for the checklists and tables, because the second pass is what survives exam pressure. Second, after every mock, return to exactly one page — the one whose topic cost you the most points — instead of re-reading everything; targeted rereading from a mistakes log beats generic review by a wide margin.

## 🧭 Which Page When: Routing by Interview Stage

```mermaid
flowchart LR
    A["Online Assessment"] --> B["MCQ Round"]
    B --> C["Phone Screen"]
    C --> D["Onsite Coding Rounds"]
    D --> E["System Design and Behavioral"]
    E --> F["Offer"]
```

| Stage | Format | Primary pages | Supporting pages |
|-------|--------|---------------|------------------|
| **OA — coding** | 2–3 problems, 60–90 min, proctored, hidden tests | [OA Strategies](./oa-strategies.md), [Two Pointers](./pattern-two-pointers.md) | [Framework](./framework.md), [Complexity](./complexity.md) |
| **OA — MCQ** | 15–30 fundamentals questions, sometimes negative marking | [MCQ Strategies](./mcq-strategies.md) | [Complexity](./complexity.md), [Pseudocode](./pseudocode-reading.md) |
| **Phone screen** | 1 medium problem, 45–60 min, live coder with an engineer | [Framework](./framework.md), [Patterns](./patterns.md) | [Data Structures](./data-structures.md) |
| **Onsite coding** | 2–4 problems across rounds, communication graded | [Patterns](./patterns.md), pattern deep-dives | [Complexity](./complexity.md), [Framework](./framework.md) |
| **Take-home / machine coding** | Larger exercise, hours to days | [Framework](./framework.md) | [Data Structures](./data-structures.md) |

Read the stage you are entering *and* the one before it: OA skills decay fastest, while pattern recognition built for onsites carries the phone screen for free. If your pipeline starts with an OA, resist studying for onsites first — the strategies differ enough that they partially conflict, especially around narration and time discipline. The routing table is also a triage tool for short deadlines: one primary page per stage is the minimum viable prep.

## 📊 Problem Difficulty Distribution

Based on analysis of recent FAANG interviews (2024-2026):

```
Easy    ████████░░░░░░░░░░░░  20%  (Warm-up, usually < 10 min)
Medium  ████████████████░░░░  55%  (Core of most interviews)
Hard    █████░░░░░░░░░░░░░░░  25%  (Differentiator for senior roles)
```

**Key insight:** You don't need to solve Hard problems to get hired. **Consistently solving Medium problems with clean code and good communication** is enough for most offers. The distribution also explains the study plans below: they front-load Medium-level pattern drilling and treat Hards as pattern combinations rather than a separate category. OAs skew slightly easier than onsites but add time pressure, which is why the strategy pages emphasize pacing over depth.

## 🗓️ Study Plans

### 1-Week Intensive (interview within 7 days)

| Day | Focus | Pages + work |
|-----|-------|--------------|
| 1 | Diagnosis + framework | [Framework](./framework.md); 3 Easy + 2 Medium problems, narrating aloud |
| 2 | Two pointers + sliding window | [Two Pointers](./pattern-two-pointers.md), [Sliding Window](./pattern-sliding-window.md); 4 Mediums |
| 3 | Frequency counting + binary search | [Frequency Counting](./pattern-frequency-counting.md), [Binary Search](./pattern-binary-search.md); 4 Mediums |
| 4 | Data structure selection | [Data Structures](./data-structures.md), [Complexity](./complexity.md); 3 Mediums choosing structures deliberately |
| 5 | Mock OA under real conditions | [OA Strategies](./oa-strategies.md): 2 problems, 60 min, template library only |
| 6 | Patterns sweep + mock MCQ | [20 Essential Patterns](./coding-patterns-guide.md), [MCQ Strategies](./mcq-strategies.md): 30-question timed set |
| 7 | Light review + rest | [Pseudocode](./pseudocode-reading.md) drills; skim mistakes log; no new material after noon |

The intensive plan sacrifices breadth for reliability: every day ends with timed, realistic practice because pattern knowledge without clock pressure does not transfer. Days 2–3 cover the two highest-frequency OA patterns, which is the right bet when time is short. Do not skip Day 7 — fatigued mocks train slow habits.

### 2-Week Standard (interview within 14 days)

| Days | Focus | Pages + work |
|------|-------|--------------|
| 1–2 | Framework + diagnosis | [Framework](./framework.md), [Complexity](./complexity.md); 6 mixed problems |
| 3–5 | Core patterns I | [Two Pointers](./pattern-two-pointers.md), [Sliding Window](./pattern-sliding-window.md), [Frequency Counting](./pattern-frequency-counting.md); 2 Mediums each day |
| 6–8 | Core patterns II | [Binary Search](./pattern-binary-search.md) + [Patterns](./patterns.md) (DP, trees, graphs sections); 2–3 problems daily |
| 9 | Full patterns review | [20 Essential Patterns](./coding-patterns-guide.md) end to end; tag every unsolved problem by pattern |
| 10 | Data structures drill | [Data Structures](./data-structures.md); re-solve 3 old problems with better structures |
| 11 | Mock OA + MCQ | [OA Strategies](./oa-strategies.md) + [MCQ Strategies](./mcq-strategies.md), fully timed |
| 12 | Pseudocode + output prediction | [Pseudocode](./pseudocode-reading.md): all drills and step tables |
| 13 | Full mock day | One 90-min OA, one 45-min mock phone screen, mistake-log review |
| 14 | Taper | Skim cheat sheets, retype the template library once, sleep |

The two-week plan adds what the intensive one cannot fit: a second pass through the patterns catalog and a dedicated data-structure selection day. The mid-point review on Day 9 is the plan's checkpoint — if pattern-tagging still feels unreliable, repeat Days 3–5 material instead of pushing into new topics. Both plans assume roughly two focused hours per day; scale the problem counts, not the page reading, if you have less.

## 🎓 Recommended Problem Sets

### By Platform
- **LeetCode:** Top 150 (Blind 75 + NeetCode 150)
- **HackerRank:** Interview Preparation Kit
- **CodeForces:** Div 2 A-C problems for speed

### By Topic Priority
1. **Arrays & Strings** — Most common, master these first
2. **Trees & Graphs** — Second most common, essential for Google
3. **Dynamic Programming** — Hard but predictable patterns
4. **Linked Lists** — Common for fundamentals testing
5. **Stacks & Queues** — Often combined with other structures
6. **Hash Maps** — Used in almost every problem as a component

Match the problem sets to the plans above rather than grinding either linearly: the topic priority list tells you *what* to drill, while the study-plan tables tell you *when*. Keep a mistakes log with one line per failed problem — pattern missed, edge case forgotten, or time lost — because your log is a better curriculum than any list. Re-solving logged problems after a week is worth more than solving a fresh problem of the same type.

## ⏱️ Time Management in Interviews

For a 45-minute coding interview:

```
┌─────────────────────────────────────────────┐
│         TIME ALLOCATION (45 min)            │
├─────────────────────────────────────────────┤
│  Understanding & Questions    5 min (11%)   │
│  Approach & Discussion        8 min (18%)   │
│  Coding                      20 min (44%)   │
│  Testing & Edge Cases         7 min (16%)   │
│  Follow-up / Optimization     5 min (11%)   │
└─────────────────────────────────────────────┘
```

The same proportions scale to phone screens (use 50–60 min formats) and to the per-problem budgets in [OA Strategies](./oa-strategies.md). The two blocks candidates routinely steal from are Understanding and Testing, and both thefts are expensive: an extra 3 minutes of clarification routinely saves 10 minutes of wrong-direction coding. Announce your checkpoints aloud ("I'm at 20 minutes, so I'm starting to code now") — interviewers read time discipline as seniority.

## 🔗 Cross-References

- [Cheat Sheets](../../cheatsheets/os.md) — Quick reference for all CS fundamentals
- [Revision Notes](../../revision/os.md) — Quick review before interviews
- [System Design](../system-design/README.md) — For senior roles, coding + system design are both critical
- [Interview Overview](../overview.md) — How the coding section fits into the full interview process
- [Python Cheat Sheet](../../cheatsheets/python.md) — Syntax reference for the template library
- [OS Questions](../os-questions.md) — Practice bank backing the OS rows of the MCQ topics table
- [DBMS Cheat Sheet](../../cheatsheets/dbms.md) — Joins, normalization, and ACID for the MCQ round
- [Networks Cheat Sheet](../../cheatsheets/networking.md) — TCP handshake, DNS, and OSI layers at a glance
