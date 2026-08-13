# Chapter 92: Undefined Behavior in C++

## Prerequisites

- C++ basics

## Interview Frequency: ★★★

Understanding UB is critical for writing correct C++. **Google** and **Meta** test this knowledge.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Integer overflow | ★★★★ | Easy | Signed overflow is UB |
| Null dereference | ★★★ | Easy | Crash or worse |
| Iterator invalidation | ★★★ | Medium | Modifying during iteration |
| Use after free | ★★★ | Medium | Dangling pointers |

---

## Motivation

Why do interviewers care about undefined behavior?

1. **It separates junior from senior.** A junior programmer writes code that "works on my machine." A senior understands *why* it works and when it might not.
2. **It tests compiler awareness.** UB is not just about runtime crashes — it's about what the compiler is *allowed* to assume. Interviewers want to know if you understand the optimizer's perspective.
3. **It reveals debugging skill.** UB bugs are the hardest to diagnose: they may appear to work, then fail with a different optimization level, platform, or even a Tuesday. Candidates who can identify UB are better debuggers.
4. **Production relevance.** Security vulnerabilities (buffer overflows, use-after-free) are UB. Real systems have been compromised because of UB that "seemed fine."

---

## Formal Definition

The C++ standard (ISO/IEC 14882) defines three categories of non-portable behavior:

| Category | Definition | Compiler Obligation |
|---|---|---|
| **Undefined Behavior (UB)** | Behavior for which the standard imposes no requirements | None — anything can happen |
| **Implementation-Defined Behavior** | Behavior that varies between implementations but must be documented | Must document the choice |
| **Unspecified Behavior** | Behavior where the standard provides multiple options but no requirement to document which is chosen | May choose freely but must be consistent within a program |

The standard's exact phrasing (§3.27 in C++20):

> **undefined behavior** — behavior for which this document imposes no requirements

This is deceptively simple. The consequences are profound:

- The compiler may **assume UB never happens** and optimize accordingly.
- The compiler may **generate any code** for a path that leads to UB — including code that does something completely unrelated to what you wrote.
- UB can **propagate backwards in time**: a later UB can cause earlier code to be "retroactively" optimized away because the compiler assumes the UB path is unreachable.

```cpp
// The compiler can assume signed overflow never happens.
// Therefore, if x is signed:
int foo(int x) {
    return x + 1 > x;  // Compiler may optimize this to: return true;
}
// This is "correct" because if x+1 would overflow, the behavior is
// undefined, so the compiler can assume it doesn't happen.
```

---

## Intuition

Think of UB as a **contract between you and the compiler**:

- **You promise** certain things will never happen (no signed overflow, no null deref, no out-of-bounds access).
- **The compiler promises** to generate correct code *as long as you keep your promises*.
- **If you break the promise**, the compiler is released from all obligations. It doesn't have to warn you. It doesn't have to crash. It can do literally anything.

A helpful mental model: **UB is not a runtime error — it's a compile-time permission for the compiler to assume it never happens.**

This is why UB is so dangerous:
- The code *appears* to work (the compiler generated something reasonable by coincidence).
- You add an unrelated change, and now the compiler generates different code that exposes the UB.
- You switch from `-O0` to `-O2`, and the optimizer's assumptions change.
- You switch compilers, and a different optimizer makes different assumptions.

**Rule of thumb:** If your code contains UB, it is *always* wrong — even if it produces the correct output right now.

---

## 92.1 Common Undefined Behaviors

| UB | Example | Consequence |
|---|---|---|
| Signed integer overflow | `int x = INT_MAX + 1` | Unpredictable |
| Null pointer dereference | `*nullptr` | Crash |
| Array out of bounds | `arr[n+1]` | Unpredictable |
| Use after free | `delete p; *p = 1` | Unpredictable |
| Double free | `delete p; delete p` | Crash |
| Shift by negative | `1 << -1` | Unpredictable |
| Signed division by zero | `1 / 0` | Crash |
| Accessing inactive union member | Reading wrong variant | Unpredictable |
| Strict aliasing violation | Casting `int*` to `float*` | Unpredictable |
| Modifying a `const` object | `const_cast` away and write | Unpredictable |

```cpp
#include <iostream>
#include <climits>

int main() {
    // Signed overflow is UB (don't rely on wraparound)
    int x = INT_MAX;
    // x + 1 is undefined! Use unsigned or check first.
    
    // Safe approach:
    if (x < INT_MAX) {
        x = x + 1; // Safe
    }
    
    std::cout << "x = " << x << "\n";
    
    // Unsigned overflow is well-defined (wraps around)
    unsigned int y = UINT_MAX;
    y++; // Well-defined: wraps to 0
    std::cout << "y = " << y << "\n";
    
    return 0;
}
```

---

## 92.2 Step-by-Step Walkthrough: Signed Overflow Surprise

Let's trace through a real UB bug where the optimizer generates surprising code.

### The Code

```cpp
#include <iostream>
#include <climits>

bool isPositive(int x) {
    return x + 1 > x;
}

int main() {
    std::cout << std::boolalpha;
    std::cout << isPositive(0) << "\n";        // true
    std::cout << isPositive(INT_MAX) << "\n";   // ???
    return 0;
}
```

### What You Expect

`INT_MAX + 1` would wrap to `INT_MIN` (on most platforms), so `isPositive(INT_MAX)` should return `false` (since `INT_MIN < INT_MAX`).

### What Actually Happens (with -O2)

The compiler outputs `true` for both calls.

### Step-by-Step

1. **Compiler analyzes** `x + 1 > x`.
2. **For signed `int`**, the standard says overflow is undefined.
3. **The compiler assumes** `x + 1` never overflows (because if it did, the behavior is undefined, and the compiler can assume UB doesn't happen).
4. **Therefore** `x + 1` is always greater than `x` (no overflow → value increases).
5. **The compiler optimizes** the function to `return true;` — always.
6. **No warning is emitted.** The code compiles cleanly.

### The Fix

```cpp
// Option 1: Use unsigned arithmetic (well-defined wraparound)
bool isPositive(unsigned int x) {
    return x + 1 > x;  // Always true for all x except UINT_MAX
}

// Option 2: Check before adding
bool isPositive(int x) {
    if (x == INT_MAX) return true; // INT_MAX is positive
    return x + 1 > x;
}

// Option 3: Use compiler builtins
#include <limits>
bool isPositive(int x) {
    int result;
    return !__builtin_add_overflow(x, 1, &result) && result > x;
}
```

---

## 92.3 Dry Run: Iterator Invalidation

Let's trace through iterator invalidation step by step.

```cpp
std::vector<int> v = {1, 2, 3, 4, 5};
for (auto it = v.begin(); it != v.end(); ++it) {
    if (*it % 2 == 0) {
        v.erase(it);  // BUG: invalidates 'it'
    }
}
```

### Trace

| Step | `it` points to | Value | Action | State of `v` |
|---|---|---|---|---|
| 1 | `v[0]` | 1 | Skip (odd) | `{1, 2, 3, 4, 5}` |
| 2 | `v[1]` | 2 | **Erase** — `it` is now invalid! | `{1, 3, 4, 5}` |
| 3 | `it` (invalid) | ??? | **UB**: incrementing invalidated iterator | Undefined |

After `erase`, `it` points to freed/relocated memory. The `++it` in the loop header is UB — it might crash, skip elements, or appear to work by accident.

### Correct Approach

```cpp
// Option 1: Erase-remove idiom
v.erase(std::remove_if(v.begin(), v.end(),
        [](int x) { return x % 2 == 0; }), v.end());

// Option 2: Use erase's return value
for (auto it = v.begin(); it != v.end(); ) {
    if (*it % 2 == 0) {
        it = v.erase(it);  // erase returns iterator to next element
    } else {
        ++it;
    }
}
```

---

## 92.4 Iterator Invalidation

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3, 4, 5};
    
    // WRONG: Erasing during range-based for
    // for (int x : v) if (x % 2 == 0) v.erase(...); // UB!
    
    // CORRECT: Erase-remove idiom
    v.erase(std::remove_if(v.begin(), v.end(), 
            [](int x) { return x % 2 == 0; }), v.end());
    
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";
    
    return 0;
}
```

---

## Complexity Analysis

UB itself has no algorithmic complexity — it's a language-level property, not an algorithm. However, **detecting and preventing UB has real costs**:

| Detection Method | Runtime Overhead | When to Use |
|---|---|---|
| `-fsanitize=undefined` (UBSan) | 2–5× slowdown | Development, CI testing |
| `-fsanitize=address` (ASan) | 2–3× slowdown | Memory-related UB |
| `-fsanitize=memory` (MSan) | 3× slowdown | Uninitialized reads |
| `-fsanitize=thread` (TSan) | 5–15× slowdown | Data races |
| Valgrind | 10–50× slowdown | Memory errors |
| Static analysis (clang-tidy) | 0 runtime cost | Compile-time checks |
| Manual code review | 0 runtime cost | Always |

**Key insight:** The cost of UB *detection* is paid during development. The cost of UB *exploitation* (by the compiler or attackers) is paid in production. Always run sanitizers in CI.

```cpp
// Compile with sanitizers for testing:
// g++ -fsanitize=undefined,address -g -O0 test.cpp

// In production, compile with optimizations:
// g++ -O2 -DNDEBUG release.cpp
```

---

## 92.5 Defensive Programming

Write code that fails fast and clearly when assumptions are violated.

```cpp
#include <iostream>
#include <cassert>
#include <stdexcept>

// Use assertions for internal invariants
int binarySearch(const int* arr, int n, int target) {
    assert(arr != nullptr && "Array must not be null");
    assert(n >= 0 && "Size must be non-negative");
    
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

// Use exceptions for external errors
int parseInt(const std::string& s) {
    try {
        return std::stoi(s);
    } catch (...) {
        throw std::invalid_argument("Invalid integer: " + s);
    }
}

int main() {
    int arr[] = {1, 3, 5, 7, 9};
    std::cout << "Found 5 at: " << binarySearch(arr, 5, 5) << "\n";
    std::cout << "Parsed: " << parseInt("42") << "\n";
    return 0;
}
```

---

## 92.6 Delta Debugging (Overview)

Systematically isolate the minimal input that causes a bug:
1. Split input into two halves
2. Test each half
3. If one half fails, recurse on that half
4. If both fail, try smaller splits
5. Continue until minimal reproducing case found

---

### Delta Debugging Implementation

```cpp
#include <iostream>
#include <vector>
#include <functional>
#include <string>

// Delta Debugging: Find minimal input that triggers a bug
// 'test' returns true if the bug occurs
std::vector<int> deltaDebug(std::vector<int> input, 
                             std::function<bool(const std::vector<int>&)> test) {
    int n = input.size();
    
    // Try removing each element
    for (int i = 0; i < n; i++) {
        std::vector<int> reduced;
        for (int j = 0; j < n; j++)
            if (j != i) reduced.push_back(input[j]);
        if (test(reduced)) {
            return deltaDebug(reduced, test); // Recurse on smaller input
        }
    }
    
    // Try splitting in half
    if (n > 2) {
        int mid = n / 2;
        std::vector<int> left(input.begin(), input.begin() + mid);
        std::vector<int> right(input.begin() + mid, input.end());
        
        if (test(left)) return deltaDebug(left, test);
        if (test(right)) return deltaDebug(right, test);
    }
    
    return input; // Can't reduce further
}

int main() {
    // Example: Find minimal input that causes a crash
    std::vector<int> input = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    
    // Simulated bug: crashes when input contains both 3 and 7
    auto testBug = [](const std::vector<int>& v) -> bool {
        bool has3 = false, has7 = false;
        for (int x : v) {
            if (x == 3) has3 = true;
            if (x == 7) has7 = true;
        }
        return has3 && has7;
    };
    
    auto minimal = deltaDebug(input, testBug);
    std::cout << "Minimal reproducing input: ";
    for (int x : minimal) std::cout << x << " ";
    std::cout << "\\n"; // Should be {3, 7} or similar
    
    return 0;
}
```

---

## Python Perspective

Python doesn't have undefined behavior in the C++ sense — the language defines the semantics of every operation. However, Python has its own class of "surprising" pitfalls that trip up programmers:

### Pitfall 1: Mutable Default Arguments

```python
# DANGER: Default mutable object is shared across calls
def append_to(element, target=[]):
    target.append(element)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [1, 2] — surprise! Same list reused.

# Fix:
def append_to(element, target=None):
    if target is None:
        target = []
    target.append(element)
    return target
```

### Pitfall 2: Late Binding Closures

```python
# DANGER: Closures capture the variable, not its value
functions = []
for i in range(5):
    functions.append(lambda: i)

print([f() for f in functions])  # [4, 4, 4, 4, 4] — not [0, 1, 2, 3, 4]

# Fix: Capture the value immediately
functions = []
for i in range(5):
    functions.append(lambda i=i: i)  # Default arg captures current value
```

### Pitfall 3: Integer Overflow Doesn't Exist (But Float Does)

```python
# Python integers have arbitrary precision — no overflow!
x = 2 ** 1000  # Works fine, produces a 302-digit number

# But float overflow DOES happen:
import math
x = math.exp(1000)  # OverflowError or inf

# And numpy arrays have fixed-size integers:
import numpy as np
x = np.int32(2147483647)
print(x + 1)  # -2147483648 — wraps around (not UB, but surprising!)
```

### Pitfall 4: Modifying a List While Iterating

```python
# DANGER: Skipping elements silently
lst = [1, 2, 3, 4, 5, 6]
for item in lst:
    if item % 2 == 0:
        lst.remove(item)  # Skips elements!

print(lst)  # [1, 3, 5] — happens to be correct, but fragile

# Fix: Iterate over a copy or use list comprehension
lst = [x for x in lst if x % 2 != 0]
```

**Key takeaway:** Python's pitfalls are **deterministic** (same input → same behavior) while C++ UB is **non-deterministic**. Python will always do the same surprising thing; C++ UB can do different surprising things on different compilers, platforms, or optimization levels.

---

## Java Perspective

Java was designed to eliminate the most dangerous forms of UB found in C/C++. Here's how Java handles the same concerns:

### Defined Overflow Behavior

```java
// Java: signed integer overflow is DEFINED (wraps around)
int x = Integer.MAX_VALUE;
System.out.println(x + 1);  // -2147483648 — always, on every platform

// No optimizer can assume "x + 1 > x" for signed int
// This is a deliberate design choice for safety
```

### Array Bounds Checking

```java
// Java: ArrayIndexOutOfBoundsException at runtime
int[] arr = {1, 2, 3};
try {
    System.out.println(arr[10]);  // Throws exception
} catch (ArrayIndexOutOfBoundsException e) {
    System.out.println("Caught: " + e.getMessage());
}
// C++ equivalent: arr[10] is UB — may read garbage, crash, or worse
```

### Null Safety

```java
// Java: NullPointerException at runtime
String s = null;
try {
    System.out.println(s.length());  // Throws NPE
} catch (NullPointerException e) {
    System.out.println("Caught null dereference");
}
// C++ equivalent: dereferencing nullptr is UB
```

### No Manual Memory Management

```java
// Java: Garbage collection eliminates use-after-free and double-free
Object obj = new Object();
obj = null;  // GC will eventually reclaim the memory
// No "delete" — no use-after-free, no double-free, no memory leaks (in theory)
```

### What Java Still Gets Wrong

| Issue | Java Behavior | Still Surprising? |
|---|---|---|
| `Integer.MAX_VALUE + 1` wraps | Defined, but may be unintended | Yes |
| Comparing `Integer` objects with `==` | Reference equality, not value | Yes |
| `ConcurrentModificationException` | Runtime exception, not compile-time | Somewhat |
| Silent precision loss (`long` → `int`) | Narrowing cast, no warning | Yes |

**Key takeaway:** Java trades performance for safety. The JVM adds runtime checks (bounds, null, overflow) that prevent silent corruption, but these checks have a cost. C++ trusts the programmer and the optimizer, which is faster but more dangerous.

---

## Interview Questions

### Q1: What is undefined behavior? Give three examples.
**Answer**: Undefined behavior (UB) is code whose behavior is not defined by the C++ standard — the compiler can do anything. Examples: signed integer overflow (`INT_MAX + 1`), null pointer dereference (`*nullptr`), use-after-free (`delete p; *p = 1`), and out-of-bounds array access.

### Q2: Why is signed integer overflow UB but unsigned overflow is well-defined?
**Answer**: The C++ standard defines unsigned arithmetic as modular (wraps at 2^n). Signed overflow was left undefined to allow compilers to optimize without worrying about wraparound — for example, assuming `x + 1 > x` is always true for signed `x`.

### Q3: How do you safely erase elements from a vector while iterating?
**Answer**: Use the erase-remove idiom: `v.erase(std::remove_if(v.begin(), v.end(), pred), v.end())`. Erasing during a range-based for loop invalidates iterators and is UB. Alternatively, use the iterator-returning erase in a while loop, capturing the returned iterator.

### Q4: What's the difference between UB and implementation-defined behavior?
**Answer**: UB has no guarantees — anything can happen. Implementation-defined behavior is unspecified by the standard but must be documented by the compiler (e.g., `sizeof(int)` is typically 4 but the compiler defines it). Both vary across compilers, but only UB can cause the optimizer to generate surprising code.

### Q5: How can sanitizers help detect UB?
**Answer**: Compilers offer sanitizers like `-fsanitize=undefined` (UBSan) and `-fsanitize=address` (ASan) that insert runtime checks. UBSan catches signed overflow, null derefs, misaligned access, etc. ASan catches use-after-free, buffer overflows, and memory leaks. They turn silent UB into loud crashes with stack traces.

### Q6: Can UB in dead code affect the rest of the program?
**Answer**: Yes. Because the compiler assumes UB never happens, it may treat a code path containing UB as "unreachable" and optimize surrounding code accordingly. For example, if `if (cond) { UB_code; }` appears, the compiler may assume `cond` is always false and remove the entire conditional — even the check itself.

### Q7: What is strict aliasing and why does violating it cause UB?
**Answer**: The strict aliasing rule says you may only access an object through its actual type, `char*`/`unsigned char*`, or a compatible type. Violating it (e.g., casting `int*` to `float*` and reading) is UB because the compiler may reorder loads/stores across the aliased access, assuming they don't interfere. Use `memcpy` for type punning instead.

### Q8: How does UB differ between C++ and Java/Python?
**Answer**: Java defines the behavior of integer overflow (wraps), null dereference (throws `NullPointerException`), and array bounds (throws `ArrayIndexOutOfBoundsException`). Python has arbitrary-precision integers (no overflow) and always-defined semantics. Neither has "real" UB — their pitfalls are deterministic. C++ UB is non-deterministic and can vary across compilers, platforms, and optimization levels.

---

## Exercises

1. **Signed vs. Unsigned**: Write a function `safeAdd(int a, int b, int& result)` that returns `false` if the addition would overflow. Test it with edge cases like `INT_MAX + 1` and `-1 + INT_MIN`.

2. **Iterator Invalidation Bug**: The following code has a bug. Find and fix it:
   ```cpp
   std::vector<int> v = {1, 2, 3, 4, 5, 6};
   for (auto it = v.begin(); it != v.end(); ++it)
       if (*it % 2 == 0) v.erase(it);
   ```

3. **Sanitizer Practice**: Compile the following with `-fsanitize=undefined` and explain what the sanitizer reports:
   ```cpp
   int x = 2147483647;
   int y = x + 1;
   ```

4. **Defensive Coding**: Add assertions to this function to catch UB at runtime:
   ```cpp
   int& get(std::vector<int>& v, int i) {
       return v[i];
   }
   ```

5. **Type Punning**: Explain why `reinterpret_cast` between unrelated types is UB, and describe the safe alternative using `memcpy`.

6. **Optimizer Surprise**: Write a function that uses signed overflow to compute something, compile it with `-O2`, and demonstrate that the compiler's output differs from what you'd expect with wraparound semantics. Use `objdump` or Compiler Explorer to inspect the generated assembly.

7. **Python Pitfall**: Translate this C++ code to Python, noting which pitfalls have direct equivalents and which ones Python avoids:
   ```cpp
   int x = INT_MAX;
   int y = x + 1;  // UB in C++, defined in Python
   ```

---

## Summary

| Category | Examples | Prevention |
|---|---|---|
| Arithmetic | Overflow, div by zero | Check bounds, use unsigned |
| Memory | Use-after-free, null deref | Smart pointers, RAII |
| Iterators | Invalidation | Erase-remove idiom |
| Type punning | Reinterpret cast | Use memcpy |

---

## See Also

- [Chapter 127: Move Semantics](ch127-move-semantics.md) — Move semantics interact with object lifetimes; moving from an object and then using it is a form of use-after-move (not UB per se, but the object is in a valid-but-unspecified state).
- [Chapter 94: Hashing Deep Dive](ch94-hashing-deep-dive.md) — Hash function implementations must avoid UB (signed overflow, type punning).
- [Chapter 126: RAII and Smart Pointers](ch126-raii-smart-pointers.md) — RAII prevents use-after-free and double-free, two common sources of UB.
- Chapter 91: Debugging Techniques — Sanitizers (UBSan, ASan) and tools like Valgrind detect UB at runtime.
- [Chapter 129: Compiler Optimizations](ch129-compiler-optimizations.md) — Compilers exploit UB to optimize aggressively; understanding this helps predict surprising behavior.
- [Chapter 124: Branch Prediction](ch124-branch-prediction.md) — UB can affect branch prediction behavior due to compiler assumptions about undefined cases.
