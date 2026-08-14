# Algorithm Correctness Proofs: Interview Guide

Being able to **prove** your algorithm is correct separates good candidates from great ones. You don't need formal rigor, but you need to articulate *why* your solution works. This chapter covers the proof techniques most useful in interviews.

---

## Loop Invariants

A loop invariant is a property that is:
1. **True before the first iteration** (initialization)
2. **Maintained by each iteration** (maintenance)
3. **True after the loop terminates, yielding the answer** (termination)

### Example: Binary Search Correctness

**Invariant:** At the start of each iteration, the target (if it exists) is in `arr[lo..hi]`.

```
function binarySearch(arr, target):
    lo, hi = 0, len(arr) - 1
    # INITIALIZATION: target in arr[0..n-1] = arr[lo..hi] ✓
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if arr[mid] == target: return mid
        elif arr[mid] < target:
            lo = mid + 1
            # MAINTENANCE: arr[mid] < target, so target in arr[mid+1..hi] = arr[lo..hi] ✓
        else:
            hi = mid - 1
            # MAINTENANCE: arr[mid] > target, so target in arr[lo..mid-1] = arr[lo..hi] ✓
    return -1
    # TERMINATION: lo > hi, so arr[lo..hi] is empty. Target not found. ✓
```

**Interview tip:** When asked "prove your binary search is correct," walk through these three steps. It takes 30 seconds and demonstrates rigor.

---

## Mathematical Induction for Algorithm Correctness

### Structure
1. **Base case:** Prove the algorithm is correct for the smallest input
2. **Inductive step:** Assume it's correct for all inputs of size < n, prove it for size n

### Example: Merge Sort Correctness

**Base case:** Arrays of size 0 or 1 are already sorted. Correct.

**Inductive step:** Assume merge sort correctly sorts all arrays of size < n. For an array of size n:
- Split into left (size n/2) and right (size n - n/2), both < n
- By inductive hypothesis, both halves are correctly sorted
- The merge step combines two sorted arrays into one sorted array (provable separately by loop invariant)
- Therefore the result is sorted. QED.

---

## Exchange Arguments (Greedy Proofs)

Prove a greedy algorithm is optimal by showing that any optimal solution can be transformed into the greedy solution without worsening it.

### Example: Activity Selection

**Claim:** Always picking the activity that finishes earliest is optimal.

**Proof:** Let G be the greedy solution and O be any optimal solution. If G[1] != O[1], then since G[1] finishes no later than O[1], we can replace O[1] with G[1] in O. The remaining activities in O are still compatible (they started after O[1] which finishes no earlier than G[1]). The new solution is still optimal and now agrees with G on the first choice. Repeat by induction. QED.

---

## Proof by Contradiction

Assume the opposite of what you want to prove, derive a contradiction.

### Example: No Two Elements in a BST Violate the Property

**Claim:** In a valid BST, there is no pair (a, b) where a is in b's left subtree and a > b.

**Proof by contradiction:** Assume such a pair exists. Since a is in b's left subtree, the BST property requires a <= b. But we assumed a > b. Contradiction. QED.

---

## Cut Property (MST Proofs)

**Cut property:** For any cut of the graph (partition of vertices into two sets), the minimum-weight edge crossing the cut belongs to *some* MST.

**Proof:** Suppose edge e is the minimum crossing edge but no MST includes it. Take any MST T. Adding e to T creates a cycle. This cycle must contain another edge f crossing the same cut. Since e has minimum weight, w(e) <= w(f). Replace f with e: the result is still a spanning tree with weight <= T. Since T was an MST, the new tree is also an MST, and it contains e. Contradiction. QED.

---

## Greedy Stays Ahead Lemma

Show that at every step, the greedy algorithm's solution is at least as good as any other solution's prefix.

### Template
1. Define a measure of "goodness" at each step
2. Show the greedy choice is at least as good as the optimal choice at that step
3. By induction, greedy is optimal overall

---

## Amortized Analysis

Amortized analysis proves that a sequence of n operations costs O(n) total, even though individual operations may be O(n).

### Aggregate Method
Compute the total cost of all n operations and divide by n.

**Example:** Dynamic array appending. Resizing happens at sizes 1, 2, 4, 8, ..., n. Total copy cost: 1 + 2 + 4 + ... + n = 2n - 1 = O(n). So n append operations cost O(n) total → O(1) amortized per append.

### Potential Method (Accounting)
Assign a "potential" to the data structure. The amortized cost = actual cost + change in potential. If total potential never goes negative, total amortized cost >= total actual cost.

**Example:** For a dynamic array of size m with n elements, define potential Φ = 2n - m (always >= 0).
- **Normal append (no resize):** actual cost = 1, Φ changes by 2. Amortized cost = 3.
- **Resize append:** actual cost = n, m doubles, Φ changes from 2n - n = n to 2n - 2n = 0, so ΔΦ = -n. Amortized cost = n + (-n) = 1.
- **Total for n appends:** 3n - O(n) resize = O(n). Amortized O(1) per operation.

---

## Interview Questions

1. **Prove that your binary search implementation is correct.** Use the loop invariant method.

2. **Prove that the greedy activity selection algorithm is optimal.** Use the exchange argument.

3. **Prove that Kruskal's algorithm produces an MST.** Use the cut property.

4. **Prove that Dijkstra's algorithm finds shortest paths when all edge weights are non-negative.** What goes wrong with negative edges?

5. **Prove that quicksort has expected O(n log n) comparisons.** What is the worst case?

6. **Prove that the amortized cost of push_back in a vector is O(1).** Use both the aggregate method and the potential method.

7. **Prove by induction that your DP solution for the knapsack problem is correct.**

8. **A interviewer says your greedy solution for a scheduling problem is wrong.** How do you construct a counterexample? Describe the process.

9. **Prove that BFS finds the shortest path in an unweighted graph.** Use the property that BFS explores nodes in order of distance.

10. **Prove that the LRU eviction policy minimizes cache misses under the assumption of no knowledge of future accesses (competitive analysis).** Show it is k-competitive where k is the cache size.
