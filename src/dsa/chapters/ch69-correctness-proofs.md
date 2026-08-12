# Chapter 69: Correctness Proofs and Loop Invariants

## Prerequisites

- Basic algorithms
- Mathematical induction

## Interview Frequency: ★★★

Proving correctness is essential for confident algorithm design. **Google** and **Microsoft** interviewers appreciate candidates who can argue why their solution works. Loop invariants are particularly important for iterative algorithms.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Loop invariants | ★★★★ | Medium | Prove iterative correctness |
| Induction proofs | ★★★★ | Medium | Prove recursive correctness |
| Exchange argument | ★★★ | Medium | Prove greedy correctness |
| Invariant maintenance | ★★★★ | Medium | Maintain during updates |

---

## Definition

**Correctness** means an algorithm produces the expected output for every valid input, as specified by its problem statement.

Formally, for an algorithm A that solves problem P:

- **Partial correctness**: *If* A terminates, then its output is correct. Written as `{precondition} A {postcondition}` (Hoare triple). We prove that whenever the precondition holds and the algorithm halts, the postcondition is satisfied.

- **Total correctness**: A terminates *and* its output is correct. This requires proving both partial correctness and termination. Total correctness is strictly stronger — it guarantees the algorithm doesn't loop forever.

- **Termination**: The algorithm halts on all valid inputs. This is typically shown by identifying a *variant* (a quantity that decreases each iteration and is bounded below, e.g., a natural number ≥ 0).

| Concept | Requires Termination? | Strength |
|---|---|---|
| Partial correctness | No | Weaker — "if it stops, it's right" |
| Total correctness | Yes | Stronger — "it stops and it's right" |

Most interview settings only require informal partial correctness (explaining *why* it works). Production-critical systems (avionics, medical devices) demand total correctness or formal verification.

---

## Motivation

Why bother proving correctness?

1. **Interviews**: Top companies (Google, Meta, Microsoft) expect you to explain *why* your solution works, not just write code. A candidate who can articulate a loop invariant or an exchange argument stands out.

2. **Bugs hide in edge cases**: Testing catches common cases; proofs cover *all* cases. Binary search had a well-known overflow bug that persisted in Java's standard library for 9 years (`(lo + hi) / 2` overflow). A formal proof would have caught it.

3. **Confidence in production**: When an algorithm handles millions of requests per second, you need certainty — not "it passed 100 test cases." Correctness proofs give you that certainty.

4. **Debugging**: If you understand the invariant, you know exactly *where* it breaks when something goes wrong. The invariant becomes a diagnostic tool.

5. **Communication**: Proving correctness is really explaining your algorithm. Engineers who can do this write better documentation, conduct better code reviews, and design better systems.

> **Rule of thumb**: If you can't explain why your algorithm is correct, you don't understand it well enough.

---

## Intuition

Think of correctness proofs as a three-step recipe:

- **Loop invariant** = "what stays true" — like a contract the loop honors every iteration. If you're sorting, the contract might be "everything left of index i is sorted."

- **Induction** = "trust the smaller version" — if you can sort 5 elements, and you can reduce sorting 6 elements to sorting 5 + merging, you're done.

- **Exchange argument** = "my greedy choice doesn't block a better answer" — if swapping a greedy pick for an optimal one never makes things worse, greedy is optimal.

The common thread: break the problem into pieces, prove each piece works, then show the pieces compose correctly.

**Mental model**: Imagine building a wall. Each brick (iteration/recursion) is placed correctly *because* the wall up to that point is correct (invariant). When the wall is complete (termination), the whole structure is sound.

---

## 69.1 Loop Invariants

A **loop invariant** is a condition that:
1. **Initialization**: True before the loop starts
2. **Maintenance**: True at the start of each iteration (if true at start of previous)
3. **Termination**: True when the loop ends → gives us the correct result

### Example: Binary Search

```cpp
#include <iostream>
#include <vector>
#include <cassert>

// Loop invariant: if target exists, it's in arr[lo..hi]
int binarySearch(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    
    // Invariant: target ∈ arr[lo..hi] if it exists in arr
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
        // Invariant maintained: narrowed range correctly
    }
    
    // Termination: lo > hi, range is empty, target not found
    return -1;
}

int main() {
    std::vector<int> arr = {1, 3, 5, 7, 9, 11};
    assert(binarySearch(arr, 7) == 3);
    assert(binarySearch(arr, 4) == -1);
    assert(binarySearch(arr, 1) == 0);
    assert(binarySearch(arr, 11) == 5);
    std::cout << "All binary search tests passed.\n";
    return 0;
}
```

### Binary Search Loop Invariant Proof

```
Initialization: lo=0, hi=n-1. If target exists, it's in arr[0..n-1]. ✓

Maintenance: If target exists in arr[lo..hi]:
  - If arr[mid] == target: found, return
  - If arr[mid] < target: target must be in arr[mid+1..hi] (since sorted)
  - If arr[mid] > target: target must be in arr[lo..mid-1] (since sorted)
  Invariant maintained. ✓

Termination: lo > hi → range is empty → target not found. ✓
```

### Python: Binary Search with Invariant

```python
from typing import List

def binary_search(arr: List[int], target: int) -> int:
    """Binary search with explicit loop invariant documentation."""
    lo, hi = 0, len(arr) - 1

    # INVARIANT: If target exists in arr, then target in arr[lo..hi]
    while lo <= hi:
        mid = lo + (hi - lo) // 2

        # Initialization: lo=0, hi=n-1 covers entire array ✓
        # Maintenance: each branch narrows the range correctly ✓
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1  # target must be in arr[mid+1..hi]
        else:
            hi = mid - 1  # target must be in arr[lo..mid-1]

    # Termination: lo > hi → empty range → target absent
    return -1


# Verification
assert binary_search([1, 3, 5, 7, 9, 11], 7) == 3
assert binary_search([1, 3, 5, 7, 9, 11], 4) == -1
assert binary_search([1, 3, 5, 7, 9, 11], 1) == 0
assert binary_search([1, 3, 5, 7, 9, 11], 11) == 5
assert binary_search([], 1) == -1
print("All binary search tests passed.")
```

---

## 69.2 Proof by Induction

For recursive algorithms, use mathematical induction.

### Example: Merge Sort Correctness

**Claim**: Merge sort correctly sorts any array of n elements.

**Base case**: n ≤ 1 is trivially sorted. ✓

**Inductive step**: Assume merge sort correctly sorts arrays of size < n.
- Split array into two halves, each of size < n
- By induction, each half is correctly sorted
- Merge step combines two sorted arrays into one sorted array
- Therefore, the full array is correctly sorted. ✓

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>

void merge(std::vector<int>& arr, int lo, int mid, int hi) {
    std::vector<int> left(arr.begin() + lo, arr.begin() + mid + 1);
    std::vector<int> right(arr.begin() + mid + 1, arr.begin() + hi + 1);
    
    int i = 0, j = 0, k = lo;
    while (i < (int)left.size() && j < (int)right.size()) {
        if (left[i] <= right[j]) arr[k++] = left[i++];
        else arr[k++] = right[j++];
    }
    while (i < (int)left.size()) arr[k++] = left[i++];
    while (j < (int)right.size()) arr[k++] = right[j++];
}

void mergeSort(std::vector<int>& arr, int lo, int hi) {
    if (lo >= hi) return;
    int mid = lo + (hi - lo) / 2;
    mergeSort(arr, lo, mid);
    mergeSort(arr, mid + 1, hi);
    merge(arr, lo, mid, hi);
}

int main() {
    std::vector<int> arr = {38, 27, 43, 3, 9, 82, 10};
    mergeSort(arr, 0, arr.size() - 1);
    
    std::vector<int> expected = {3, 9, 10, 27, 38, 43, 82};
    assert(arr == expected);
    std::cout << "Merge sort correctness verified.\n";
    
    return 0;
}
```

### Python: Merge Sort with Inductive Proof Structure

```python
from typing import List

def merge(arr: List[int], lo: int, mid: int, hi: int) -> None:
    """Merge two sorted halves arr[lo..mid] and arr[mid+1..hi].

    Precondition:  arr[lo..mid] and arr[mid+1..hi] are each sorted.
    Postcondition: arr[lo..hi] is sorted and contains the same elements.
    """
    left = arr[lo:mid + 1]
    right = arr[mid + 1:hi + 1]
    i = j = 0
    k = lo

    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            arr[k] = left[i]; i += 1
        else:
            arr[k] = right[j]; j += 1
        k += 1

    while i < len(left):
        arr[k] = left[i]; i += 1; k += 1
    while j < len(right):
        arr[k] = right[j]; j += 1; k += 1


def merge_sort(arr: List[int], lo: int, hi: int) -> None:
    """Sort arr[lo..hi] in place.

    Proof by strong induction on n = hi - lo + 1:
      Base case (n <= 1): trivially sorted.
      Inductive step: assume correctness for all sizes < n.
        Split into two halves, each < n.
        By IH, each half is correctly sorted after recursive calls.
        Merge produces a sorted array from two sorted halves.
        Therefore arr[lo..hi] is sorted. QED
    """
    if lo >= hi:
        return  # Base case: 0 or 1 elements
    mid = lo + (hi - lo) // 2
    merge_sort(arr, lo, mid)
    merge_sort(arr, mid + 1, hi)
    merge(arr, lo, mid, hi)


# Verification
arr = [38, 27, 43, 3, 9, 82, 10]
merge_sort(arr, 0, len(arr) - 1)
assert arr == [3, 9, 10, 27, 38, 43, 82]
print("Merge sort correctness verified.")
```

### Java: Binary Search with Loop Invariant

```java
/**
 * Binary search with formal loop invariant documentation.
 *
 * Loop invariant: If target exists in arr, then target ∈ arr[lo..hi].
 *
 * Initialization: lo=0, hi=n-1 covers the entire sorted array. ✓
 * Maintenance: Each branch eliminates half the search space correctly. ✓
 * Termination: When lo > hi the range is empty; target is absent. ✓
 */
public class BinarySearch {

    public static int binarySearch(int[] arr, int target) {
        int lo = 0, hi = arr.length - 1;

        // Invariant: target ∈ arr[lo..hi] if it exists in arr
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;  // avoids overflow

            if (arr[mid] == target) return mid;
            else if (arr[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }

        // Termination: lo > hi → empty range → not found
        return -1;
    }

    public static void main(String[] args) {
        int[] arr = {1, 3, 5, 7, 9, 11};
        assert binarySearch(arr, 7) == 3;
        assert binarySearch(arr, 4) == -1;
        assert binarySearch(arr, 1) == 0;
        assert binarySearch(arr, 11) == 5;
        System.out.println("All binary search tests passed.");
    }
}
```

---

## 69.3 The Exchange Argument (Greedy Correctness)

To prove a greedy algorithm is correct:

1. Let OPT be an optimal solution
2. Let GREEDY be our greedy solution
3. Show we can transform OPT into GREEDY without making it worse
4. Conclude GREEDY is also optimal

### Example: Activity Selection

**Greedy**: Always pick the activity that finishes earliest.

**Proof**:
1. Let OPT = {a₁, a₂, ..., aₖ} sorted by finish time
2. Let GREEDY = {g₁, g₂, ..., gₘ} sorted by finish time
3. Claim: m ≥ k (greedy picks at least as many)
4. Proof: g₁ finishes no later than a₁ (greedy picks earliest finish)
5. Therefore g₁ leaves more room for future activities
6. By induction, greedy picks at least as many as optimal

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Activity { int start, end; };

int activitySelection(std::vector<Activity>& activities) {
    std::sort(activities.begin(), activities.end(),
              [](const Activity& a, const Activity& b) {
                  return a.end < b.end;
              });
    
    int count = 0, lastEnd = -1;
    for (auto& act : activities) {
        if (act.start >= lastEnd) {
            count++;
            lastEnd = act.end;
        }
    }
    return count;
}

int main() {
    std::vector<Activity> acts = {{1,4}, {3,5}, {0,6}, {5,7}, {3,9}, {5,9}};
    std::cout << "Max activities: " << activitySelection(acts) << "\n";
    return 0;
}
```

---

## 69.4 Invariant Maintenance in Data Structures

Data structures maintain invariants that ensure correctness.

### BST Invariant

For every node: left subtree values < node value < right subtree values

```cpp
#include <iostream>
#include <climits>

struct TreeNode {
    int val;
    TreeNode *left, *right;
    TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

// Invariant: all values in subtree are in (minVal, maxVal)
bool isValidBST(TreeNode* node, long long minVal = LLONG_MIN, 
                long long maxVal = LLONG_MAX) {
    if (!node) return true;
    if (node->val <= minVal || node->val >= maxVal) return false;
    return isValidBST(node->left, minVal, node->val) &&
           isValidBST(node->right, node->val, maxVal);
}

int main() {
    TreeNode* root = new TreeNode(5);
    root->left = new TreeNode(3);
    root->right = new TreeNode(7);
    root->left->left = new TreeNode(1);
    root->left->right = new TreeNode(4);
    
    std::cout << "Is valid BST: " << isValidBST(root) << "\n";
    
    root->left->right->val = 6; // Violates BST property
    std::cout << "Is valid BST: " << isValidBST(root) << "\n";
    
    return 0;
}
```

---

## 69.5 Proving Correctness of Iterative Algorithms: Quicksort Partition

Beyond simple examples, many iterative algorithms require careful invariant analysis. Quicksort's Lomuto partition is a classic case.

### Lomuto Partition Invariant

```python
from typing import List

def partition(arr: List[int], lo: int, hi: int) -> int:
    """Lomuto partition: pick arr[hi] as pivot.

    Loop invariant after iteration i:
        arr[lo..store-1]  < pivot   (elements less than pivot)
        arr[store..i-1]   >= pivot  (elements >= pivot)
        arr[i..hi-1]      unexamined

    Initialization: store=lo, i=lo → both regions empty. ✓
    Maintenance: swapping arr[i] and arr[store] (when arr[i] < pivot)
                 extends both regions correctly. ✓
    Termination: i=hi → all elements partitioned.
                 Swap arr[store] with arr[hi] (pivot) to place pivot
                 in its final position. ✓
    """
    pivot = arr[hi]
    store = lo

    for i in range(lo, hi):
        if arr[i] < pivot:
            arr[store], arr[i] = arr[i], arr[store]
            store += 1

    arr[store], arr[hi] = arr[hi], arr[store]
    return store


def quicksort(arr: List[int], lo: int, hi: int) -> None:
    """Quicksort proved correct by induction + partition invariant.

    Base case: lo >= hi → 0 or 1 elements, trivially sorted.
    Inductive step:
        Partition places pivot in final position p.
        All elements left of p are < pivot; all right are >= pivot.
        By IH, recursive calls on arr[lo..p-1] and arr[p+1..hi]
        produce sorted subarrays.
        Combined: arr[lo..hi] is sorted. QED
    """
    if lo >= hi:
        return
    p = partition(arr, lo, hi)
    quicksort(arr, lo, p - 1)
    quicksort(arr, p + 1, hi)


# Verification
arr = [10, 7, 8, 9, 1, 5]
quicksort(arr, 0, len(arr) - 1)
assert arr == [1, 5, 7, 8, 9, 10]

arr = [3, 3, 1, 1, 2, 2]
quicksort(arr, 0, len(arr) - 1)
assert arr == [1, 1, 2, 2, 3, 3]
print("Quicksort partition correctness verified.")
```

### Why the Partition Invariant Matters

The partition step is the *foundation* of quicksort's correctness. If the invariant breaks:
- A smaller element stays right of the pivot → it's never sorted into the correct half
- A larger element stays left of the pivot → same problem

The invariant guarantees the pivot is in its **final sorted position**, which is the key insight that makes the divide-and-conquer work.

---

## 69.6 Formal Explanation: Hoare Logic and Weakest Preconditions

### Hoare Logic

Hoare logic provides a formal system for reasoning about program correctness using **Hoare triples**:

```
{P} C {Q}
```

Where:
- **P** = precondition (what's true before C executes)
- **C** = the command/program
- **Q** = postcondition (what's true after C executes)

The triple `{P} C {Q}` is valid if: whenever P holds before C, and C terminates, Q holds after C.

### Assignment Axiom

The simplest rule — for assignment `x := E`:

```
{Q[E/x]}  x := E  {Q}
```

This means: to ensure Q holds after `x := E`, we need `Q` with `E` substituted for `x` to hold before.

**Example**: Want `{x = 5} x := x + 1 {x = 6}`. Substituting: `{5 + 1 = 6} x := x + 1 {x = 6}` → `{6 = 6}` which is trivially true. ✓

### Weakest Precondition (wp)

The **weakest precondition** `wp(C, Q)` is the least restrictive condition on the state before C that guarantees Q after C.

For assignment: `wp(x := E, Q) = Q[E/x]`

For sequencing `C1; C2`: `wp(C1; C2, Q) = wp(C1, wp(C2, Q))`

For conditional `if B then C1 else C2`:
```
wp(if B then C1 else C2, Q) = (B → wp(C1, Q)) ∧ (¬B → wp(C2, Q))
```

### Loop Rule

For a loop with invariant I:

```
{I ∧ B}  C  {I}        (invariant maintained)
{I}  while B do C  {I ∧ ¬B}   (invariant holds and loop exits)
```

This is exactly the loop invariant pattern: I must be initialized, maintained each iteration, and I ∧ ¬B (the invariant plus the loop condition being false) must imply the desired postcondition.

### Applying Hoare Logic to Binary Search

```
P: 0 ≤ lo ∧ hi ≤ n-1 ∧ sorted(arr) ∧ (target ∈ arr → target ∈ arr[lo..hi])
C: while lo ≤ hi do { find mid; narrow range }
Q: (lo > hi ∧ target ∉ arr) ∨ (arr[result] = target)

Invariant I = P  (the precondition itself serves as the invariant)

Maintenance:
  {I ∧ lo ≤ hi}
  mid = lo + (hi - lo) / 2
  {I ∧ lo ≤ mid ≤ hi}

  Case arr[mid] = target: return mid → Q satisfied. ✓
  Case arr[mid] < target:
    lo = mid + 1
    {sorted ∧ target > arr[mid] → target ∈ arr[mid+1..hi] if present} ✓
  Case arr[mid] > target:
    hi = mid - 1
    {sorted ∧ target < arr[mid] → target ∈ arr[lo..mid-1] if present} ✓

Termination:
  Variant: hi - lo + 1 (decreases each iteration, bounded below by 0)
  When lo > hi: I ∧ lo > hi → target ∉ arr. Q satisfied. ✓
```

---

## Step-by-Step Walkthrough: Constructing a Proof from Scratch

Let's walk through *how* to construct a correctness proof from scratch. We'll use the problem of finding the maximum element in an array.

### Step 1: State the Problem Precisely

> Given a non-empty array arr[0..n-1], return an index i such that arr[i] = max(arr).

### Step 2: Write the Algorithm

```python
def find_max(arr):
    max_idx = 0
    for i in range(1, len(arr)):
        if arr[i] > arr[max_idx]:
            max_idx = i
    return max_idx
```

### Step 3: Identify the Candidate Invariant

Ask: *What is true before and after every iteration?*

After examining elements arr[0..i-1], max_idx points to the maximum among them.

**Candidate invariant**: `max_idx ∈ [0, i-1] ∧ arr[max_idx] = max(arr[0..i-1])`

### Step 4: Verify Initialization (Before the Loop)

- i = 1 (loop starts at 1)
- max_idx = 0
- arr[0..0] has one element; max_idx = 0 points to it. ✓

### Step 5: Verify Maintenance (Loop Body Preserves Invariant)

Assume invariant holds at start of iteration i:
- `arr[max_idx] = max(arr[0..i-1])`
- We examine arr[i]:
  - If arr[i] > arr[max_idx]: max_idx = i → arr[max_idx] = arr[i] = max(arr[0..i]). ✓
  - If arr[i] ≤ arr[max_idx]: max_idx unchanged → arr[max_idx] = max(arr[0..i]). ✓
- i increments to i+1, so invariant holds for the next iteration. ✓

### Step 6: Verify Termination

- Loop terminates when i = n
- Invariant gives: arr[max_idx] = max(arr[0..n-1])
- This is exactly the desired postcondition. ✓

### Step 7: Verify Termination (Non-divergence)

- Variant: n - i (decreases by 1 each iteration, bounded below by 0)
- Loop terminates in exactly n - 1 iterations. ✓

### Step 8: Write Up the Proof

```
Invariant I: max_idx ∈ [0, i-1] ∧ arr[max_idx] = max(arr[0..i-1])

Initialization: i=1, max_idx=0. arr[0..0] has one element, max_idx points to it. ✓
Maintenance:    Examining arr[i] and updating max_idx preserves I. ✓
Termination:    i=n → I gives arr[max_idx] = max(arr[0..n-1]). ✓
```

**Key insight**: The hardest part is *finding* the right invariant. Start with "what should be true at the end?" and work backwards to find a condition that's easy to maintain.

---

## Summary

| Proof Technique | When to Use | Key Idea |
|---|---|---|
| Loop Invariant | Iterative algorithms | Init → Maintenance → Termination |
| Induction | Recursive algorithms | Base case + inductive step |
| Exchange Argument | Greedy algorithms | Transform OPT to GREEDY |
| Invariant Maintenance | Data structures | Property holds after every operation |
| Hoare Logic | Formal verification | Weakest precondition + triples |

---

## Interview Questions

### Q1: What is a loop invariant and how do you use one?
**Answer**: A loop invariant is a condition true before and after every iteration. To use one: (1) **Initialization** — prove it's true before the loop, (2) **Maintenance** — prove that if true at the start of an iteration, it's true at the end, (3) **Termination** — prove the loop terminates and the invariant gives the correct result. This mirrors mathematical induction.

### Q2: Prove that insertion sort is correct using a loop invariant.
**Answer**: Invariant: After iteration i, the subarray arr[0..i] is sorted. **Init**: i=0, single element is sorted. **Maintenance**: Inserting arr[i] into the sorted arr[0..i-1] produces a sorted arr[0..i]. **Termination**: i=n, so arr[0..n-1] is fully sorted.

### Q3: How do you prove a greedy algorithm is correct using the exchange argument?
**Answer**: Let OPT be an optimal solution and GREEDY be our solution. Show that for any optimal solution differing from GREEDY, we can swap elements (exchange) to make it more like GREEDY without worsening the solution. Conclude GREEDY is at least as good as OPT.

### Q4: Why is proving correctness important in interviews?
**Answer**: It demonstrates that you understand *why* your solution works, not just *that* it works. Interviewers want to see reasoning ability. A correct proof also catches bugs — if you can't prove it's correct, it probably isn't. At companies like Google and Microsoft, explaining correctness is often worth more than the code itself.

### Q5: What's the difference between proving correctness and testing?
**Answer**: Testing checks specific inputs; correctness proofs cover all inputs. Testing can show the presence of bugs but never their absence. A proof guarantees the algorithm works for every valid input. However, proofs can have errors too — best practice is both proof and testing.

### Q6: What is the difference between partial and total correctness?
**Answer**: Partial correctness says "if the algorithm terminates, the result is correct." Total correctness adds termination: "the algorithm terminates AND the result is correct." An infinite loop can be partially correct (vacuously — it never terminates so the "if" is never tested) but not totally correct. In practice, we usually need total correctness.

### Q7: How would you prove the correctness of a two-pointer technique?
**Answer**: Two-pointer algorithms typically have an invariant relating the pointers to the problem state. For example, in the two-sum problem on a sorted array with pointers at lo and hi: the invariant is "if a solution exists, it involves indices in [lo, hi]." Each step eliminates one index (move lo up if sum too small, move hi down if sum too large) while preserving the invariant. Termination: lo ≥ hi means we've exhausted all pairs.

---

## Exercises

1. **Loop Invariant for Selection Sort**: Write the loop invariant for selection sort and prove it formally (initialization, maintenance, termination).

2. **Prove Merge Correctness**: Prove that the merge step in merge sort correctly produces a sorted array from two sorted halves.

3. **Exchange Argument for Huffman**: Use the exchange argument to prove that Huffman coding produces an optimal prefix-free code.

4. **Invariant for a Stack**: Define a loop invariant for a function that reverses an array using a stack, and prove it's correct.

5. **Find the Bug**: The following binary search has a bug. Identify it, fix it, and prove the fixed version correct using a loop invariant:
   ```cpp
   int search(vector<int>& a, int t) {
       int lo = 0, hi = a.size();
       while (lo < hi) {
           int mid = (lo + hi) / 2;
           if (a[mid] == t) return mid;
           if (a[mid] < t) lo = mid;
           else hi = mid - 1;
       }
       return -1;
   }
   ```

6. **Loop Invariant for Two-Sum**: Given a sorted array and a target sum, write and prove the loop invariant for the two-pointer approach that finds two elements summing to the target.

7. **Prove Quicksort Correctness**: Using the partition invariant from Section 69.5, write a complete correctness proof for quicksort (induction on array size + partition invariant). Include the proof that the pivot ends up in its final sorted position.

---

## See Also

- [Chapter 3: Complexity Analysis](ch03-complexity-analysis.md) — Correctness and complexity are the two pillars of algorithm analysis; prove both.
- [Chapter 5: Sorting](ch05-sorting.md) — Sorting algorithms are classic examples for loop invariant proofs (insertion sort, selection sort).
- [Chapter 8: Recursion](ch08-recursion.md) — Recursive algorithms are proved correct by induction; the recursive call is the inductive step.
- [Chapter 6: Searching](ch06-searching.md) — Binary search is the canonical example of loop invariant analysis.
- [Chapter 9: Backtracking](ch09-backtracking.md) — Backtracking correctness relies on exhaustive search with pruning; the invariant ensures no valid solution is missed.
- Chapter 30: Greedy Algorithms — The exchange argument is the primary tool for proving greedy correctness.
