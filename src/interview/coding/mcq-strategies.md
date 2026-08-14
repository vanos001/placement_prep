# MCQ Strategies for Online Assessments

MCQ sections in OAs test breadth over depth. You face 15–30 questions covering CS fundamentals, output prediction, and sometimes quantitative aptitude. Speed and accuracy both matter.

## Common Topics

| Category | High-Yield Topics | Frequency |
|----------|-------------------|-----------|
| **OS** | Process vs thread, deadlock conditions, scheduling (SJF, RR), virtual memory, page replacement | Very High |
| **DBMS** | SQL joins, normalization (1NF–3NF, BCNF), ACID properties, indexing (B-tree vs hash), isolation levels | Very High |
| **Networks** | TCP vs UDP, TCP 3-way handshake, HTTP methods/status codes, DNS, OSI layers | High |
| **OOP** | Polymorphism, encapsulation, inheritance, abstract class vs interface, virtual functions | High |
| **DSA** | Time complexity of operations, BST vs hash map, stack vs queue use cases, graph representations | Medium |
| **Output Prediction** | C/C++ pointer arithmetic, Python pass-by-object-reference, operator precedence, short-circuit evaluation | Very High |
| **Aptitude** | Probability, permutations/combinations, percentages, work-time problems | Medium |

## Time Management

- **Target: 45–60 seconds per question**
- First pass: answer all questions you're confident about (mark uncertain ones)
- Second pass: tackle marked questions — spend up to 2 minutes each
- Third pass: pure guessing on remaining (never leave blanks on platforms that don't penalize)

**Adaptive tests** (AMCAT, some Codility): You cannot skip or return. Read each question carefully the first time.

## Elimination Techniques

### Process of Elimination (POE)

1. **Eliminate absolutes**: Options with "always" or "never" are usually wrong unless the statement is trivially true
2. **Eliminate nonsensical units**: If a complexity question shows O(n log log n) for a simple array traversal, eliminate it
3. **Eliminate contradicted options**: If two options contradict each other, at most one can be correct
4. **Eliminate out-of-scope answers**: An OS question about scheduling won't have a DBMS-related correct answer

### Dimensional Analysis

For quantitative questions, check the units:
- If the answer should be a count, eliminate options with time units
- If asking for complexity, O(n log n) and O(n²) are plausible; O(log n log n) almost never is

## Common Trick Questions

### 1. Pass-by-Value vs Pass-by-Reference Confusion
```
Python: def modify(lst):
    lst.append(4)
a = [1, 2, 3]
modify(a)
# a is now [1, 2, 3, 4] — list is mutable, passed by object reference
```

### 2. Short-Circuit Evaluation Order
```
# Python: "False and side_effect()" — side_effect() is never called
# C/C++: Same behavior with && and ||
```

### 3. Integer Division Traps
```
Python 3: 5 / 2 = 2.5  (true division)
Python 2: 5 / 2 = 2    (floor division)
C/Java:  5 / 2 = 2    (integer division)
```

### 4. Operator Precedence
```
# Bitwise & has lower precedence than ==
if (a & b == 0)   # Parses as (a & (b == 0)), NOT ((a & b) == 0)
```

### 5. Uninitialized Variables
```c
// C: Local variables are garbage. Global/static are zero.
int x;           // garbage
static int y;    // 0
int arr[5];      // garbage (not zeroed)
```

## Handling "Select All That Apply"

These questions are designed to make you second-guess. Strategy:

1. **Evaluate each option independently** — treat it as a true/false for that option alone
2. **Don't overthink correlations** — selecting A doesn't make B more or less likely to be correct
3. **Look for "all of the above"** — if you've confirmed 3 of 4 options, the 4th is almost certainly correct
4. **Watch for partially correct options** — "Thread switching is done by the OS scheduler" is true; adding "and it takes constant time" makes it false
5. **Count your selections** — if you're selecting all 5 options, re-examine; it's rare for all options to be correct

## Interview Tips

- For output prediction questions, **trace the code on paper** with a small concrete input — don't try to run it in your head
- Know the **exact definitions** of ACID, deadlock conditions (mutual exclusion, hold & wait, no preemption, circular wait), and normalization forms
- Memorize **time complexities** for common operations: hash map lookup O(1), BST O(log n), array access O(1), linked list access O(n)
- For SQL MCQs, know the difference between `WHERE` and `HAVING`, `LEFT JOIN` and `INNER JOIN`, `UNION` and `UNION ALL`