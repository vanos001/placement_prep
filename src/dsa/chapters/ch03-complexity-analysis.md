# Chapter 3: Complexity Analysis

Complexity analysis is the most important theoretical concept for algorithm interviews. It's how we compare solutions, justify our choices, and prove that our approach is efficient. This chapter builds from first principles — no prior knowledge assumed.

---

## 3.1 What Is Complexity?

### Why Do We Measure?

Imagine two programs that sort a list of numbers. On your laptop, Program A takes 0.5 seconds and Program B takes 2 seconds. Is A better?

**Not necessarily!** What if:
- A was tested on 100 numbers, B on 1,000,000?
- A was running on a supercomputer, B on a phone?
- A was written in optimized C++, B in Python?

We need a way to compare algorithms **independent of**:
1. The hardware (CPU speed, RAM)
2. The programming language
3. The specific input data
4. Other running programs

**Complexity analysis** solves this by counting the number of **basic operations** as a function of input size.

### What Counts as a Basic Operation?

We typically count operations that take constant time O(1):
- Arithmetic operations (+, -, ×, ÷)
- Comparisons (<, >, ==)
- Assignments
- Array access (by index)
- Function calls (not counting what's inside)

We do NOT count operations that depend on input size (like copying an array of variable size).

### Input Size

The "size" of input depends on the problem:

| Problem | Input Size |
|---|---|
| Sort an array | n = number of elements |
| Search in a matrix | n = rows, m = columns |
| Graph algorithms | V = vertices, E = edges |
| String problems | n = length of string |
| Number problems | k = number of digits (or log n) |

### Two Types of Complexity

- **Time Complexity:** How many operations the algorithm performs.
- **Space Complexity:** How much extra memory the algorithm uses.

Both are expressed as functions of input size n.

---

## 3.2 Big-O Notation

### Intuition

Big-O notation describes the **upper bound** of an algorithm's growth rate. It answers: "As the input grows, how does the runtime grow?"

**Key idea:** We care about the **growth rate**, not the exact count. An algorithm that does 3n + 5 operations is fundamentally different from one that does n² operations, but 3n + 5 and 7n + 2 are "the same" in terms of growth.

### Formal Definition

\\[O(g(n)) = \{ f(n) : \exists \text{ constants } c > 0, n_0 > 0 \text{ such that } 0 \leq f(n) \leq c \cdot g(n) \text{ for all } n \geq n_0 \}\\]

**In plain English:** f(n) is O(g(n)) if, for sufficiently large n, f(n) is bounded above by some constant multiple of g(n).

**Example:** Is 3n + 5 = O(n)?

We need: 3n + 5 ≤ c·n for all n ≥ n₀

Choose c = 4, n₀ = 5: 3n + 5 ≤ 4n when n ≥ 5. ✓

So 3n + 5 = O(n).

### Visual Explanation

```
Operations
    |        n² (quadratic)
    |       /
    |      /
    |     /     n log n
    |    /      /
    |   /      /   n (linear)
    |  /      /   /
    | /      /   /
    |/      /   /   log n
    +------+------+------→ n
         n₀
```

After n₀, the curves never cross again. The lower-order terms become irrelevant.

### How to Prove Big-O

**Step-by-step method:**

1. Identify f(n) — the operation count of your algorithm.
2. Identify g(n) — the proposed upper bound.
3. Find constants c and n₀ such that f(n) ≤ c·g(n) for all n ≥ n₀.

**Example:** Prove 2n² + 3n + 1 = O(n²)

We need: 2n² + 3n + 1 ≤ c·n²

For n ≥ 1: 3n ≤ 3n² and 1 ≤ n²

So: 2n² + 3n + 1 ≤ 2n² + 3n² + n² = 6n²

Choose c = 6, n₀ = 1. ✓

### Rules for Big-O

| Rule | Example |
|---|---|
| Drop constants | O(3n) = O(n) |
| Drop lower-order terms | O(n² + n) = O(n²) |
| Drop coefficients | O(5n³ + 2n² + 7) = O(n³) |
| Constants are O(1) | O(42) = O(1) |
| Multiply for nested loops | O(n) × O(m) = O(nm) |
| Add for sequential code | O(n) + O(m) = O(n + m) |

### Worst Case, Best Case, Average Case

For any algorithm, we can analyze three scenarios:

**Example: Linear Search** (searching for x in an array of n elements)

| Case | Description | Operations |
|---|---|---|
| Best | x is the first element | O(1) |
| Worst | x is the last element or not present | O(n) |
| Average | x is equally likely to be anywhere | O(n/2) = O(n) |

**In interviews, we almost always discuss the worst case** unless otherwise specified. Big-O by itself means worst-case upper bound.

---

## 3.3 Big-Omega and Big-Theta

### Big-Omega (Ω) — Lower Bound

\\[\Omega(g(n)) = \{ f(n) : \exists \text{ constants } c > 0, n_0 > 0 \text{ such that } 0 \leq c \cdot g(n) \leq f(n) \text{ for all } n \geq n_0 \}\\]

**Plain English:** f(n) grows at LEAST as fast as g(n).

**Example:** 3n + 5 = Ω(n) because 3n + 5 ≥ 1·n for all n ≥ 1.

### Big-Theta (Θ) — Tight Bound

\\[\Theta(g(n)) = O(g(n)) \cap \Omega(g(n))\\]

**Plain English:** f(n) grows at EXACTLY the same rate as g(n) (up to constant factors).

**Example:** 3n + 5 = Θ(n) because it's both O(n) and Ω(n).

### Relationship

```
Ω(g)  ⊇  Θ(g)  ⊆  O(g)
        (tight bound)

Algorithm can be in:
- O(n²) but Ω(n) → not tight either way → O(n²) is correct, Θ(n²) is not
- Θ(n) → O(n) and Ω(n) → tight bound found
```

### Analogy

Think of it like running:
- **O(n):** "I can run at most 10 km/h" (upper bound on speed)
- **Ω(n):** "I can run at least 5 km/h" (lower bound on speed)
- **Θ(n):** "I run at exactly 7-8 km/h" (tight bound)

### Common Confusion

When someone says "Merge Sort is O(n log n)," they typically mean Θ(n log n) — it's always n log n, not just in the worst case. The use of O is by convention, but be precise in proofs.

---

## 3.4 Common Complexity Classes

Understanding these complexity classes is essential for recognizing efficient vs. inefficient solutions:

| Class | Name | n = 10 | n = 100 | n = 1,000 | n = 10⁶ | Example |
|---|---|---|---|---|---|---|
| O(1) | Constant | 1 | 1 | 1 | 1 | Array access |
| O(log n) | Logarithmic | 3 | 7 | 10 | 20 | Binary search |
| O(√n) | Square root | 3 | 10 | 32 | 1000 | Trial division |
| O(n) | Linear | 10 | 100 | 1,000 | 10⁶ | Linear search |
| O(n log n) | Linearithmic | 33 | 664 | 9,966 | 2×10⁷ | Merge sort |
| O(n²) | Quadratic | 100 | 10,000 | 10⁶ | 10¹² | Bubble sort |
| O(n³) | Cubic | 1,000 | 10⁶ | 10⁹ | 10¹⁸ | Naive matrix mult |
| O(2ⁿ) | Exponential | 1,024 | 10³⁰ | 10³⁰¹ | — | Subset enumeration |
| O(n!) | Factorial | 3.6M | 10¹⁵⁷ | — | — | Permutation brute force |

**"—" means the value is so large it's meaningless.**

### What Can We Do in an Interview?

A common question: "Given n ≤ some_limit, what complexity is acceptable?"

| Input Size (n) | Acceptable Complexity |
|---|---|
| n ≤ 10-12 | O(n!), O(2^n) |
| n ≤ 20-25 | O(2^n) |
| n ≤ 100 | O(n³) |
| n ≤ 500 | O(n³) |
| n ≤ 5,000 | O(n²) |
| n ≤ 10⁶ | O(n log n) |
| n ≤ 10⁸ | O(n) |
| n ≤ 10¹² | O(√n) |
| n ≤ 10¹⁸ | O(log n), O(1) |

**Rule of thumb:** Assume ~10⁸ operations per second in C++. If your algorithm does f(n) operations and the time limit is 1 second, you need f(n) ≤ 10⁸.

---

## 3.5 Analyzing Loops

### Single Loop

```cpp
// O(n)
int sum = 0;
for (int i = 0; i < n; i++) {
    sum += arr[i];
}
```

The loop runs n times. Each iteration does O(1) work. Total: O(n).

### Nested Loops — Independent

```cpp
// O(n²)
for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
        matrix[i][j] = 0;
    }
}
```

Outer loop: n iterations. Inner loop: n iterations each. Total: n × n = O(n²).

### Nested Loops — Dependent

```cpp
// O(n²)
for (int i = 0; i < n; i++) {
    for (int j = 0; j < i; j++) {  // j depends on i
        // ...
    }
}
```

Count the total iterations:
\\[\sum_{i=0}^{n-1} i = \frac{n(n-1)}{2} = O(n^2)\\]

### Nested Loops — Logarithmic Inner

```cpp
// O(n log n)
for (int i = 0; i < n; i++) {
    int j = 1;
    while (j < n) {
        // O(1) work
        j *= 2;
    }
}
```

Inner while loop: j doubles each time, so it runs log₂(n) times. Total: n × log(n) = O(n log n).

### Nested Loops — Halving

```cpp
// O(log n)
int i = n;
while (i > 1) {
    // O(1) work
    i /= 2;
}
```

i halved each time: n, n/2, n/4, ..., 1. Number of steps: log₂(n). Total: O(log n).

### Two Sequential Loops

```cpp
// O(n + m) = O(n) if m = O(n)
for (int i = 0; i < n; i++) {
    // O(1) work
}
for (int j = 0; j < m; j++) {
    // O(1) work
}
```

Sequential loops: add the complexities. O(n + m).

### Loop with Early Exit

```cpp
// O(n) worst case, O(1) best case
for (int i = 0; i < n; i++) {
    if (arr[i] == target) return i;
}
```

Worst case: O(n). Best case: O(1). We usually analyze worst case.

### Comprehensive Examples

```cpp
#include <iostream>

// Example 1: What is the complexity?
void example1(int n) {
    int count = 0;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j += i) {
            count++;
        }
    }
    std::cout << "Example 1 count: " << count << std::endl;
}
// Analysis: For each i, the inner loop runs n/i times.
// Total = n/1 + n/2 + n/3 + ... + n/n = n × (1 + 1/2 + 1/3 + ... + 1/n)
// The harmonic series H(n) ≈ ln(n)
// Total = O(n log n)

// Example 2: What is the complexity?
void example2(int n) {
    int count = 0;
    for (int i = 0; i < n; i++) {
        for (int j = i; j < n; j++) {
            for (int k = j; k < n; k++) {
                count++;
            }
        }
    }
    std::cout << "Example 2 count: " << count << std::endl;
}
// Analysis: C(n+2, 3) = (n+2)(n+1)n/6 = O(n³)

int main() {
    example1(1000);
    example2(100);
    return 0;
}
```

---

## 3.6 Analyzing Recursion

### Recurrence Relations

Recursive algorithms are analyzed using recurrence relations. A recurrence expresses the total work T(n) in terms of work on smaller inputs.

### Recursion Tree Method

**Visualize** the recursion as a tree and sum the work at each level.

**Example: Merge Sort** — T(n) = 2T(n/2) + n

```
Level 0:          n                  → work: n
                 / \
Level 1:       n/2  n/2             → work: n
              / \   / \
Level 2:   n/4 n/4 n/4 n/4         → work: n
            ...  ...  ...  ...
Level k:    1  1  1  1  ...  1      → work: n
            (n elements at this level)

Height: log₂(n)
Total: n × log(n) = O(n log n)
```

**Key steps:**
1. Count the work at each level (excluding recursive calls).
2. Count the number of levels.
3. Multiply: total = (work per level) × (number of levels).

### Substitution Method

**Guess the answer, then prove it by induction.**

**Example:** T(n) = 2T(n/2) + n, T(1) = 1

**Guess:** T(n) = O(n log n), i.e., T(n) ≤ cn log n for some constant c.

**Proof by induction:**

Assume T(k) ≤ ck log k for all k < n.

```
T(n) = 2T(n/2) + n
     ≤ 2 · c(n/2) log(n/2) + n
     = cn log(n/2) + n
     = cn(log n - 1) + n
     = cn log n - cn + n
     = cn log n - (c-1)n
     ≤ cn log n    (when c ≥ 1)  ✓
```

### Master Theorem (Expanded)

For recurrences of the form:

\\[T(n) = aT(n/b) + \Theta(n^d \log^k n)\\]

The solution is:

| Case | Condition | Result |
|---|---|---|
| 1 | log_b(a) > d | Θ(n^(log_b(a))) |
| 2 (k=0) | log_b(a) = d | Θ(n^d log n) |
| 2 (k≥0) | log_b(a) = d | Θ(n^d log^(k+1) n) |
| 3 | log_b(a) < d | Θ(n^d) |

**Extended Master Theorem** (for aT(n/b) + f(n) where f(n) doesn't fit the polynomial form):

**Case 1:** If f(n) = O(n^(log_b(a) - ε)) for some ε > 0, then T(n) = Θ(n^(log_b(a)))

**Case 2:** If f(n) = Θ(n^(log_b(a)) × log^k(n)), then T(n) = Θ(n^(log_b(a)) × log^(k+1)(n))

**Case 3:** If f(n) = Ω(n^(log_b(a) + ε)) for some ε > 0, AND af(n/b) ≤ cf(n) for some c < 1, then T(n) = Θ(f(n))

### Worked Examples

```cpp
#include <iostream>
#include <cmath>

void solveRecurrence(const char* rec, double a, double b, double d) {
    double log_b_a = std::log(a) / std::log(b);
    std::cout << rec << std::endl;
    std::cout << "  a=" << a << ", b=" << b << ", d=" << d << std::endl;
    std::cout << "  log_b(a) = " << log_b_a << std::endl;

    if (std::abs(log_b_a - d) < 1e-9) {
        std::cout << "  Case 2: T(n) = Θ(n^" << d << " log n)" << std::endl;
    } else if (log_b_a > d) {
        std::cout << "  Case 1: T(n) = Θ(n^" << log_b_a << ")" << std::endl;
    } else {
        std::cout << "  Case 3: T(n) = Θ(n^" << d << ")" << std::endl;
    }
    std::cout << std::endl;
}

int main() {
    // Binary Search: T(n) = T(n/2) + 1
    solveRecurrence("Binary Search: T(n) = T(n/2) + 1", 1, 2, 0);

    // Merge Sort: T(n) = 2T(n/2) + n
    solveRecurrence("Merge Sort: T(n) = 2T(n/2) + n", 2, 2, 1);

    // Strassen's Matrix Multiplication: T(n) = 7T(n/2) + n²
    solveRecurrence("Strassen: T(n) = 7T(n/2) + n^2", 7, 2, 2);

    // Karatsuba Multiplication: T(n) = 3T(n/2) + n
    solveRecurrence("Karatsuba: T(n) = 3T(n/2) + n", 3, 2, 1);

    // Some algorithm: T(n) = 4T(n/2) + n
    solveRecurrence("T(n) = 4T(n/2) + n", 4, 2, 1);

    return 0;
}
```

**Output:**
```
Binary Search: T(n) = T(n/2) + 1
  a=1, b=2, d=0
  log_b(a) = 0
  Case 2: T(n) = Θ(n^0 log n) = Θ(log n)

Merge Sort: T(n) = 2T(n/2) + n
  a=2, b=2, d=1
  log_b(a) = 1
  Case 2: T(n) = Θ(n^1 log n) = Θ(n log n)

Strassen: T(n) = 7T(n/2) + n^2
  a=7, b=2, d=2
  log_b(a) = 2.807
  Case 1: T(n) = Θ(n^2.807)

Karatsuba: T(n) = 3T(n/2) + n
  a=3, b=2, d=1
  log_b(a) = 1.585
  Case 1: T(n) = Θ(n^1.585)

T(n) = 4T(n/2) + n
  a=4, b=2, d=1
  log_b(a) = 2
  Case 1: T(n) = Θ(n^2)
```

---

## 3.7 Amortized Analysis

### What Is Amortized Analysis?

Amortized analysis finds the **average cost per operation over a worst-case sequence** of operations. It's not average-case analysis — it's a guaranteed bound on the average.

**Key distinction:**
- **Average case:** Assumes a probability distribution over inputs.
- **Amortized:** Guarantees the average over ANY sequence of n operations.

### Motivation: Dynamic Array (vector) Push

When `std::vector::push_back` needs more space, it doubles the capacity:

```
Capacity: 1 → 2 → 4 → 8 → 16 → ...
```

**Worst case for a single push_back:** O(n) — when we need to copy all elements.
**Amortized cost per push_back:** O(1) — because expensive operations are rare.

### Method 1: Aggregate Method

**Idea:** Total cost of n operations ÷ n = amortized cost per operation.

**Example:** n push_back operations on a dynamic array (starting from capacity 1, doubling).

Total copies: 1 + 2 + 4 + 8 + ... + 2^k where 2^k ≈ n

This geometric series sums to 2n - 1 = O(n).

Total cost including the n insertions: n + O(n) = O(n).

Amortized cost per operation: O(n)/n = O(1). ✓

### Method 2: Accounting Method

**Idea:** Assign a "charge" to each operation. Some operations "overpay" to build up credit for future expensive operations.

**Example:** Charge 3 units for each push_back:
- 1 unit: pay for the actual insertion
- 2 units: save as credit for future doubling

When doubling happens (copying k elements), we've had k/2 insertions since the last doubling, accumulating k units of credit. This exactly pays for copying k elements.

**Amortized cost:** 3 per operation = O(1). ✓

### Method 3: Potential Method

**Idea:** Define a potential function Φ that maps the data structure's state to a number.

Amortized cost = Actual cost + ΔΦ (change in potential)

**Example for dynamic array:**

Let Φ = 2 × size - capacity

After a non-doubling push:
- Actual cost: 1
- ΔΦ: 2 (size increased by 1, capacity unchanged)
- Amortized cost: 1 + 2 = 3

After a doubling push (size == capacity before doubling):
- Actual cost: capacity + 1 (copy capacity elements + 1 insert)
- Φ before: 2 × capacity - capacity = capacity
- Φ after: 2 × (capacity + 1) - 2 × capacity = 2
- ΔΦ: 2 - capacity
- Amortized cost: (capacity + 1) + (2 - capacity) = 3 ✓

So every push_back has amortized cost ≤ 3 = O(1). ✓

```cpp
#include <iostream>
#include <vector>

// Simulate dynamic array to demonstrate amortized O(1)
class DynamicArray {
    int* data;
    int sz;
    int cap;
    long long totalCost;  // Track total operations

public:
    DynamicArray() : sz(0), cap(1), totalCost(0) {
        data = new int[cap];
    }

    ~DynamicArray() { delete[] data; }

    void push_back(int val) {
        int cost = 1;  // Cost of insertion

        if (sz == cap) {
            // Need to double — copy all elements
            cost += sz;
            cap *= 2;
            int* newData = new int[cap];
            for (int i = 0; i < sz; i++) {
                newData[i] = data[i];
            }
            delete[] data;
            data = newData;
        }

        data[sz++] = val;
        totalCost += cost;
    }

    int size() const { return sz; }
    long long getTotalCost() const { return totalCost; }
    double getAmortizedCost() const {
        return sz > 0 ? static_cast<double>(totalCost) / sz : 0;
    }
};

int main() {
    DynamicArray arr;
    for (int i = 0; i < 1000; i++) {
        arr.push_back(i);
    }

    std::cout << "Total operations: " << arr.getTotalCost() << std::endl;
    std::cout << "Number of pushes: " << arr.size() << std::endl;
    std::cout << "Amortized cost per push: " << arr.getAmortizedCost() << std::endl;
    // Amortized cost should be close to a small constant (~3)
    return 0;
}
```

---

## 3.8 Space Complexity

### What Is Space Complexity?

Space complexity measures the total memory used by an algorithm as a function of input size.

**Two concepts:**
- **Auxiliary space:** Extra space used by the algorithm (excluding input).
- **Total space:** Input space + auxiliary space.

When interviewers say "space complexity," they usually mean auxiliary space.

### Common Space Complexities

| Complexity | Description | Example |
|---|---|---|
| O(1) | Constant extra space | In-place swap, two pointers |
| O(log n) | Recursion stack for divide-and-conquer | Quick sort (average) |
| O(n) | Linear extra space | Merge sort, hash map copy |
| O(n²) | Quadratic space | 2D DP table |

### Stack Space for Recursion

Each recursive call uses stack space for:
- Return address
- Parameters
- Local variables

**Example: Factorial**

```cpp
// Stack depth: O(n)
long long factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
```

n recursive calls → O(n) stack space.

**Example: Binary Search**

```cpp
// Stack depth: O(log n)
int binarySearch(int arr[], int lo, int hi, int target) {
    if (lo > hi) return -1;
    int mid = lo + (hi - lo) / 2;
    if (arr[mid] == target) return mid;
    if (arr[mid] < target) return binarySearch(arr, mid + 1, hi, target);
    return binarySearch(arr, lo, mid - 1, target);
}
```

Each call halves the range → O(log n) stack depth.

### Tail Recursion

If the recursive call is the last operation, the compiler can optimize it to a loop (eliminating stack growth):

```cpp
// Tail recursive — can be optimized to O(1) space
long long factorialHelper(int n, long long acc) {
    if (n <= 1) return acc;
    return factorialHelper(n - 1, n * acc);  // Tail position
}

long long factorial(int n) {
    return factorialHelper(n, 1);
}
```

**C++ compilers (with optimization)** may convert this to a loop. However, don't rely on this — if space matters, write the iterative version yourself.

### Space Complexity of Common Algorithms

| Algorithm | Auxiliary Space | Why |
|---|---|---|
| Bubble Sort | O(1) | In-place |
| Selection Sort | O(1) | In-place |
| Insertion Sort | O(1) | In-place |
| Merge Sort | O(n) | Temporary arrays for merging |
| Quick Sort | O(log n) average | Recursion stack (balanced) |
| Heap Sort | O(1) | In-place |
| Counting Sort | O(k) | Count array of size k |
| Radix Sort | O(n + k) | Buckets |

```cpp
#include <iostream>
#include <vector>

// Demonstrate space complexity with memory tracking
void mergeSort(std::vector<int>& arr, int lo, int hi) {
    if (lo >= hi) return;

    int mid = lo + (hi - lo) / 2;
    mergeSort(arr, lo, mid);         // O(log n) stack depth
    mergeSort(arr, mid + 1, hi);     // O(log n) stack depth

    // Merge: O(n) auxiliary space
    std::vector<int> temp;
    int i = lo, j = mid + 1;
    while (i <= mid && j <= hi) {
        if (arr[i] <= arr[j]) temp.push_back(arr[i++]);
        else temp.push_back(arr[j++]);
    }
    while (i <= mid) temp.push_back(arr[i++]);
    while (j <= hi) temp.push_back(arr[j++]);

    for (int k = 0; k < (int)temp.size(); k++) {
        arr[lo + k] = temp[k];
    }
}

int main() {
    std::vector<int> arr = {38, 27, 43, 3, 9, 82, 10};
    mergeSort(arr, 0, arr.size() - 1);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 3 9 10 27 38 43 82
    return 0;
}
```

---

## 3.9 Practical Guidelines

### Rules of Thumb for Interviews

1. **Always state the time and space complexity** of your solution. If you don't, the interviewer will ask.

2. **Start with the brute force** — even if it's O(n²) or worse. Then optimize. This shows you can solve the problem and also analyze it.

3. **Know the target complexity.** If n ≤ 10⁵, aim for O(n log n) or better. If n ≤ 10³, O(n²) might be acceptable.

4. **Don't optimize prematurely.** Get the correct solution first, then improve complexity.

5. **Constants matter in practice, but not in interviews.** An O(n) algorithm with a large constant might be slower than O(n log n) for small n. But in an interview, O(n) is always preferred.

### When Constants Don't Matter

Big-O ignores constants, but they matter when:
- The input size is small (n < 100)
- The constant is very large (e.g., an algorithm with 1000n vs n² — for n < 1000, the O(n²) is faster)
- You're optimizing production code

### When Constants DO Matter

In interviews, mention constants when:
- Comparing two O(n log n) algorithms (e.g., Merge Sort vs Quick Sort — Quick Sort has smaller constants)
- The problem has very tight constraints
- Cache efficiency is relevant (e.g., array traversal is faster than linked list traversal due to cache locality)

### Common Interview Patterns and Their Complexities

| Pattern | Typical Time | Typical Space | Example |
|---|---|---|---|
| Two Pointers | O(n) | O(1) | Container With Most Water |
| Sliding Window | O(n) | O(k) | Longest Substring Without Repeats |
| Binary Search | O(log n) | O(1) | Search in Rotated Array |
| BFS/DFS | O(V + E) | O(V) | Number of Islands |
| Dynamic Programming | O(n²) or O(n·m) | O(n) or O(n·m) | Longest Common Subsequence |
| Greedy | O(n log n) | O(1) or O(n) | Activity Selection |
| Divide and Conquer | O(n log n) | O(log n) or O(n) | Merge Sort |

### Analyzing Your Own Solution — Step by Step

When asked "What's the complexity?", follow this process:

1. **Identify the input size** (n, m, etc.)
2. **Count the main operations:**
   - How many iterations does each loop run?
   - How many recursive calls? How deep?
   - What's the cost of each iteration/call?
3. **Multiply nested operations, add sequential ones**
4. **Simplify:** Drop constants, keep highest-order term

**Template for answering:**

> "The time complexity is O(n log n) because we sort the array first (O(n log n)), then do a single pass with binary search at each step (O(n × log n) = O(n log n)). The space complexity is O(n) for the sorted copy."

### Complexity Comparison Cheat Sheet

```
O(1) < O(log n) < O(√n) < O(n) < O(n log n) < O(n²) < O(n³) < O(2ⁿ) < O(n!)
```

When comparing two complexities, ask: "Which grows faster as n → ∞?"

- 1000n vs n²: For n < 1000, n² is smaller. For n > 1000, 1000n is smaller. Big-O says O(n) is better.
- n log n vs n^1.5: n^1.5 grows faster. O(n log n) is better.

---

## Interview Tips

1. **Always analyze before coding.** State your approach and its complexity before writing code. This saves time if the approach is suboptimal.

2. **Know the Master Theorem cold.** Most divide-and-conquer recurrences fit T(n) = aT(n/b) + O(n^d).

3. **Amortized analysis** is rare in interviews but understanding the dynamic array doubling example shows depth of knowledge.

4. **Space complexity matters.** Don't forget to analyze it. An O(n) space solution might need to become O(1) for follow-up.

5. **Be precise about what n means.** In graph problems, distinguish V (vertices) and E (edges). In 2D problems, distinguish n and m.

6. **Practice counting iterations.** Sum(1 to n) = n(n+1)/2. Geometric series: 1 + 2 + 4 + ... + 2^k = 2^(k+1) - 1. Harmonic series: 1 + 1/2 + 1/3 + ... + 1/n ≈ ln(n).

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---|---|---|
| Saying O(n²) is always slower than O(n) | For small n, constants matter | Say "for large enough n" |
| Forgetting stack space in recursion | Recursion uses O(depth) stack | Mention stack space explicitly |
| Confusing O with Θ | O is upper bound, Θ is tight | Use Θ when you mean tight bound |
| Saying "O(2n) = O(n) so they're the same" | True for Big-O, but constants affect real performance | Acknowledge constants exist |
| Analyzing only the best case | Best case is often trivial | Analyze worst case unless told otherwise |
| Not considering input size carefully | Graph: V and E are separate | Use appropriate variables |

## Practice Problems

| # | Problem | Difficulty | Key Concept |
|---|---|---|---|
| 1 | Analyze the complexity of `for(i=0; i<n; i++) for(j=i; j<n; j++)` | Easy | Dependent nested loops |
| 2 | What is the complexity of finding the median of an unsorted array? | Easy | Sorting vs selection |
| 3 | Analyze T(n) = 3T(n/4) + n·log(n) using the Master theorem | Medium | Extended Master theorem |
| 4 | Prove that an algorithm with T(n) = T(n-1) + n has T(n) = O(n²) | Medium | Substitution method |
| 5 | Analyze the amortized cost of a binary counter increment | Medium | Potential method |
| 6 | What is the time and space complexity of printing all subsets of n elements? | Medium | 2^n subsets, each up to size n |
| 7 | Analyze the complexity of building a heap (heapify, not insertion) | Medium | Sum of heights |
| 8 | Prove that any comparison-based sorting algorithm requires Ω(n log n) comparisons | Hard | Decision tree argument |
| 9 | Analyze the complexity of union-find with path compression and union by rank | Hard | Inverse Ackermann |
| 10 | What is the complexity of matrix chain multiplication DP? | Hard | O(n³) time, O(n²) space |

---

*In the next chapter, we'll apply complexity analysis to arrays and strings — the most common data structures in interviews.*
