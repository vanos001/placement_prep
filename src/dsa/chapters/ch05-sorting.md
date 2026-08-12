# Chapter 5: Sorting

Sorting is one of the most studied problems in computer science. Nearly every algorithm course starts with sorting, and for good reason: sorting is a building block for countless other algorithms, and the techniques used in sorting (divide and conquer, incremental construction, heap operations) appear everywhere in interviews.

---

## 5.1 Why Sorting Matters

Sorting enables efficient solutions to many problems:

| Problem | Without Sorting | With Sorting |
|---|---|---|
| Find duplicates | O(n²) nested loops | O(n log n) sort + O(n) scan |
| Find pair with sum K | O(n²) or O(n) with hash | O(n log n) sort + O(n) two pointers |
| Find median | O(n) quickselect | O(n log n) sort + O(1) access |
| Interval scheduling | Exponential | O(n log n) sort + O(n) greedy |

Many interview problems have a hidden sorting step that transforms a hard problem into an easy one.

### Quick Reference: Which Sort to Use?

| Situation | Best Choice | Why |
|---|---|---|
| General purpose | `std::sort` | IntroSort hybrid, O(n log n) guaranteed |
| Need stability | `std::stable_sort` or Merge Sort | Preserves relative order of equal elements |
| Nearly sorted data | Insertion Sort | O(n) on nearly sorted input |
| Small array (n < 50) | Insertion Sort | Low overhead, cache-friendly |
| Integers in small range | Counting Sort | O(n + k), beats comparison sorts |
| Large n, bounded digits | Radix Sort | O(d × n), linear for fixed-width ints |
| Guaranteed O(n log n), in-place | Heap Sort | Best worst-case in-place sort |
| Linked list | Merge Sort | O(1) extra space on linked lists |

---

## 5.2 Bubble Sort

### Concept

Repeatedly step through the array, compare adjacent elements, and swap them if they're in the wrong order. After each pass, the largest unsorted element "bubbles up" to its correct position.

### Visualization

```
Initial:  [5, 3, 8, 1, 2]

Pass 1:
  Compare 5,3 → swap → [3, 5, 8, 1, 2]
  Compare 5,8 → ok   → [3, 5, 8, 1, 2]
  Compare 8,1 → swap → [3, 5, 1, 8, 2]
  Compare 8,2 → swap → [3, 5, 1, 2, 8]  ← 8 is in place

Pass 2:
  Compare 3,5 → ok   → [3, 5, 1, 2, 8]
  Compare 5,1 → swap → [3, 1, 5, 2, 8]
  Compare 5,2 → swap → [3, 1, 2, 5, 8]  ← 5 is in place

Pass 3:
  Compare 3,1 → swap → [1, 3, 2, 5, 8]
  Compare 3,2 → swap → [1, 2, 3, 5, 8]  ← 3 is in place

Pass 4:
  Compare 1,2 → ok   → [1, 2, 3, 5, 8]  ← No swaps → DONE
```

### Code

```cpp
#include <iostream>
#include <vector>

// Optimized Bubble Sort with early termination
// Time: Best O(n), Average O(n²), Worst O(n²)
// Space: O(1)
// Stable: Yes
void bubbleSort(std::vector<int>& arr) {
    int n = arr.size();
    for (int i = 0; i < n - 1; i++) {
        bool swapped = false;
        for (int j = 0; j < n - 1 - i; j++) {
            if (arr[j] > arr[j + 1]) {
                std::swap(arr[j], arr[j + 1]);
                swapped = true;
            }
        }
        // If no swaps in this pass, array is sorted
        if (!swapped) break;
    }
}

int main() {
    std::vector<int> arr = {64, 34, 25, 12, 22, 11, 90};
    bubbleSort(arr);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 11 12 22 25 34 64 90
    return 0;
}
```

### Complexity

| Case | Time | When? |
|---|---|---|
| Best | O(n) | Already sorted (with optimization) |
| Average | O(n²) | Random order |
| Worst | O(n²) | Reverse sorted |

**Space:** O(1) — in-place.
**Stable:** Yes — equal elements maintain relative order.

### When to Use

Almost never in practice. It's mainly used for educational purposes. Insertion sort is always preferred for small or nearly sorted arrays.

---

## 5.3 Selection Sort

### Concept

Find the minimum element in the unsorted portion and swap it with the first unsorted element.

### Visualization

```
Initial:  [64, 25, 12, 22, 11]

Pass 1: Find min in [64, 25, 12, 22, 11] → 11, swap with 64
         [11, 25, 12, 22, 64]
          ✓

Pass 2: Find min in [25, 12, 22, 64] → 12, swap with 25
         [11, 12, 25, 22, 64]
          ✓   ✓

Pass 3: Find min in [25, 22, 64] → 22, swap with 25
         [11, 12, 22, 25, 64]
          ✓   ✓   ✓

Pass 4: Find min in [25, 64] → 25, no swap needed
         [11, 12, 22, 25, 64]
          ✓   ✓   ✓   ✓   ✓  DONE
```

### Code

```cpp
#include <iostream>
#include <vector>

// Selection Sort
// Time: O(n²) always (best, average, worst)
// Space: O(1)
// Stable: No (can be made stable with linked lists)
void selectionSort(std::vector<int>& arr) {
    int n = arr.size();
    for (int i = 0; i < n - 1; i++) {
        int minIdx = i;
        for (int j = i + 1; j < n; j++) {
            if (arr[j] < arr[minIdx]) {
                minIdx = j;
            }
        }
        if (minIdx != i) {
            std::swap(arr[i], arr[minIdx]);
        }
    }
}

int main() {
    std::vector<int> arr = {64, 25, 12, 22, 11};
    selectionSort(arr);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 11 12 22 25 64
    return 0;
}
```

### Complexity

| Case | Time |
|---|---|
| Best | O(n²) |
| Average | O(n²) |
| Worst | O(n²) |

**Always** O(n²) because we always scan the entire unsorted portion.
**Space:** O(1) — in-place.
**Stable:** No. Example: [5a, 5b, 3] → after first pass: [3, 5b, 5a] — relative order of 5a and 5b changed.

**Minimum swaps:** O(n) — at most n-1 swaps. This is a theoretical advantage when swaps are expensive.

---

## 5.4 Insertion Sort

### Concept

Build the sorted array one element at a time. For each new element, insert it into its correct position in the already-sorted portion.

### Visualization

```
Initial:  [5, 3, 8, 1, 2]

i=1: Insert 3 into [5]       → [3, 5, 8, 1, 2]
i=2: Insert 8 into [3, 5]    → [3, 5, 8, 1, 2]  (8 already in place)
i=3: Insert 1 into [3, 5, 8] → [1, 3, 5, 8, 2]
i=4: Insert 2 into [1, 3, 5, 8] → [1, 2, 3, 5, 8]
```

### Code

```cpp
#include <iostream>
#include <vector>

// Insertion Sort
// Time: Best O(n), Average O(n²), Worst O(n²)
// Space: O(1)
// Stable: Yes
void insertionSort(std::vector<int>& arr) {
    int n = arr.size();
    for (int i = 1; i < n; i++) {
        int key = arr[i];
        int j = i - 1;

        // Shift elements greater than key to the right
        while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            j--;
        }
        arr[j + 1] = key;
    }
}

int main() {
    std::vector<int> arr = {12, 11, 13, 5, 6};
    insertionSort(arr);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 5 6 11 12 13
    return 0;
}
```

### Why Insertion Sort Is Good

1. **Nearly sorted arrays:** O(n) — each element moves only a few positions.
2. **Small arrays:** Low overhead, fast in practice for n < 20-50.
3. **Online algorithm:** Can sort elements as they arrive.
4. **Stable:** Preserves relative order of equal elements.
5. **Adaptive:** Fewer comparisons when data is partially sorted.

**Real-world use:** Many hybrid sorting algorithms (like `std::sort` in C++) switch to insertion sort for small subarrays (typically n ≤ 16-32).

---

## 5.5 Merge Sort

### Concept

**Divide and Conquer:**
1. **Divide** the array into two halves.
2. **Recursively** sort each half.
3. **Merge** the two sorted halves.

### Why It Works — Intuition

Imagine you have two sorted decks of cards. Merging them is easy: compare the top cards, take the smaller one, repeat. This merge step is O(n). Now, how do we get sorted decks? We split the array in half, sort each half (recursively), and merge. The splitting continues until we have single elements (which are trivially sorted). The total work at each level of recursion is O(n), and there are O(log n) levels — giving O(n log n) overall.

### Visualization

```
              [38, 27, 43, 3, 9, 82, 10]
                /                    \
        [38, 27, 43, 3]        [9, 82, 10]
          /          \            /       \
      [38, 27]    [43, 3]    [9, 82]    [10]
       /    \      /    \     /    \       |
     [38]  [27]  [43]  [3]  [9]  [82]   [10]
       \    /      \    /     \    /       |
      [27, 38]    [3, 43]    [9, 82]    [10]
          \          /            \       /
        [3, 27, 38, 43]        [9, 10, 82]
                \                    /
           [3, 9, 10, 27, 38, 43, 82]
```

### Code

```cpp
#include <iostream>
#include <vector>

// Merge two sorted subarrays arr[lo..mid] and arr[mid+1..hi]
void merge(std::vector<int>& arr, int lo, int mid, int hi) {
    std::vector<int> temp;
    int i = lo, j = mid + 1;

    while (i <= mid && j <= hi) {
        if (arr[i] <= arr[j]) {
            temp.push_back(arr[i++]);
        } else {
            temp.push_back(arr[j++]);
        }
    }

    while (i <= mid) temp.push_back(arr[i++]);
    while (j <= hi) temp.push_back(arr[j++]);

    // Copy back
    for (int k = 0; k < (int)temp.size(); k++) {
        arr[lo + k] = temp[k];
    }
}

// Merge Sort
// Time: O(n log n) always
// Space: O(n)
// Stable: Yes
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

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 3 9 10 27 38 43 82
    return 0;
}
```

### Complexity

| Case | Time |
|---|---|
| Best | O(n log n) |
| Average | O(n log n) |
| Worst | O(n log n) |

**Always** O(n log n) — the recurrence is T(n) = 2T(n/2) + O(n).
**Space:** O(n) — temporary arrays for merging.
**Stable:** Yes — during merge, we pick from the left subarray first when elements are equal.

### When to Use

- When stability is required.
- When guaranteed O(n log n) is needed.
- For linked lists (merge sort on linked lists uses O(1) extra space).
- For external sorting (data too large for memory).

---

## 5.6 Quick Sort

### Concept

**Divide and Conquer:**
1. **Pick a pivot** element.
2. **Partition:** Rearrange so elements < pivot are on the left, elements > pivot are on the right.
3. **Recursively** sort left and right partitions.

### Why It Works — Intuition

Think of organizing books on a shelf. Pick one book as a reference (the pivot). Put all thinner books to its left, all thicker books to its right. Now the pivot is in its final position! Recurse on the left and right groups. The key insight: after partitioning, the pivot doesn't need to move again. Each partition step does O(n) work, and if partitions are roughly balanced, we get O(log n) levels → O(n log n) total.

### Lomuto Partition Scheme

```cpp
#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>

// Lomuto partition: pivot is last element
int partition(std::vector<int>& arr, int lo, int hi) {
    int pivot = arr[hi];
    int i = lo;  // Boundary for elements <= pivot

    for (int j = lo; j < hi; j++) {
        if (arr[j] <= pivot) {
            std::swap(arr[i], arr[j]);
            i++;
        }
    }
    std::swap(arr[i], arr[hi]);  // Place pivot in correct position
    return i;
}

// Quick Sort with randomized pivot
// Time: Best O(n log n), Average O(n log n), Worst O(n²)
// Space: O(log n) average (recursion stack)
// Stable: No
void quickSort(std::vector<int>& arr, int lo, int hi) {
    if (lo >= hi) return;

    // Randomize pivot to avoid worst case
    int pivotIdx = lo + rand() % (hi - lo + 1);
    std::swap(arr[pivotIdx], arr[hi]);

    int p = partition(arr, lo, hi);
    quickSort(arr, lo, p - 1);
    quickSort(arr, p + 1, hi);
}

int main() {
    srand(time(nullptr));
    std::vector<int> arr = {10, 7, 8, 9, 1, 5};
    quickSort(arr, 0, arr.size() - 1);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 1 5 7 8 9 10
    return 0;
}
```

### Hoare Partition Scheme

```cpp
#include <iostream>
#include <vector>

// Hoare partition: more efficient, fewer swaps
int hoarePartition(std::vector<int>& arr, int lo, int hi) {
    int pivot = arr[lo + (hi - lo) / 2];
    int i = lo - 1, j = hi + 1;

    while (true) {
        do { i++; } while (arr[i] < pivot);
        do { j--; } while (arr[j] > pivot);
        if (i >= j) return j;
        std::swap(arr[i], arr[j]);
    }
}

void quickSortHoare(std::vector<int>& arr, int lo, int hi) {
    if (lo >= hi) return;
    int p = hoarePartition(arr, lo, hi);
    quickSortHoare(arr, lo, p);
    quickSortHoare(arr, p + 1, hi);
}

int main() {
    std::vector<int> arr = {10, 7, 8, 9, 1, 5};
    quickSortHoare(arr, 0, arr.size() - 1);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    return 0;
}
```

### Pivot Selection Strategies

| Strategy | How | Worst Case |
|---|---|---|
| First element | `arr[lo]` | Sorted array → O(n²) |
| Last element | `arr[hi]` | Sorted array → O(n²) |
| Random element | `arr[random(lo,hi)]` | Extremely unlikely O(n²) |
| Median of three | median of first, middle, last | Very unlikely O(n²) |

### Complexity

| Case | Time | When? |
|---|---|---|
| Best | O(n log n) | Balanced partitions |
| Average | O(n log n) | Random data |
| Worst | O(n²) | Already sorted (with bad pivot) |

**Space:** O(log n) average (recursion stack), O(n) worst case.
**Stable:** No — partitioning can change relative order of equal elements.

### Why Quick Sort Is Often Preferred

Despite O(n²) worst case:
1. **Small constant factors** — fewer comparisons and swaps than merge sort.
2. **Cache-friendly** — operates on contiguous memory.
3. **In-place** — O(log n) auxiliary space vs O(n) for merge sort.
4. **Randomized version** has O(n²) probability that's astronomically low.

---

## 5.7 Heap Sort

### Concept

1. Build a max-heap from the array.
2. Repeatedly extract the maximum (swap root with last unsorted element, reduce heap size, heapify).

### Code

```cpp
#include <iostream>
#include <vector>

// Heapify subtree rooted at index i
void heapify(std::vector<int>& arr, int n, int i) {
    int largest = i;
    int left = 2 * i + 1;
    int right = 2 * i + 2;

    if (left < n && arr[left] > arr[largest]) {
        largest = left;
    }
    if (right < n && arr[right] > arr[largest]) {
        largest = right;
    }

    if (largest != i) {
        std::swap(arr[i], arr[largest]);
        heapify(arr, n, largest);
    }
}

// Heap Sort
// Time: O(n log n) always
// Space: O(1)
// Stable: No
void heapSort(std::vector<int>& arr) {
    int n = arr.size();

    // Build max heap: O(n) — start from last non-leaf node
    for (int i = n / 2 - 1; i >= 0; i--) {
        heapify(arr, n, i);
    }

    // Extract elements one by one
    for (int i = n - 1; i > 0; i--) {
        std::swap(arr[0], arr[i]);  // Move max to end
        heapify(arr, i, 0);          // Heapify reduced heap
    }
}

int main() {
    std::vector<int> arr = {12, 11, 13, 5, 6, 7};
    heapSort(arr);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 5 6 7 11 12 13
    return 0;
}
```

### Dry Run

```
Initial:  [12, 11, 13, 5, 6, 7]

Build max-heap:
  Start from index 2 (value 13): no swap needed
  Index 1 (value 11): children 5, 6. No swap needed.
  Index 0 (value 12): children 11, 13. Swap with 13.
  → [13, 11, 12, 5, 6, 7]

  After heapify at index 2: 12 has child 7. No swap.
  Final heap: [13, 11, 12, 5, 6, 7]

Extract max (13), swap with last:
  [7, 11, 12, 5, 6, | 13]
  Heapify: swap 7 and 12 → [12, 11, 7, 5, 6, | 13]
  Heapify: swap 7 and 6? No, 7 > 6. Done.
  → [12, 11, 7, 5, 6, 13]

Extract max (12), swap with 6:
  [6, 11, 7, 5, | 12, 13]
  Heapify: swap 6 and 11 → [11, 6, 7, 5, | 12, 13]
  Heapify: swap 6 and 5? No, 6 > 5. Done.
  → [11, 6, 7, 5, 12, 13]

... continues until sorted: [5, 6, 7, 11, 12, 13]
```

### Complexity

| Case | Time |
|---|---|
| Best | O(n log n) |
| Average | O(n log n) |
| Worst | O(n log n) |

**Space:** O(1) — fully in-place.
**Stable:** No.

**Advantage:** Guaranteed O(n log n) with O(1) space — the best of both worlds (guaranteed like merge sort, in-place like quick sort).

**Disadvantage:** Poor cache performance — parent and child nodes can be far apart in memory.

---

## 5.8 Counting Sort

### Concept

A **non-comparison** sort. Count the occurrences of each value, then reconstruct the sorted array.

**Constraint:** Works only for integers in a known range [0, k].

### Code

```cpp
#include <iostream>
#include <vector>

// Counting Sort
// Time: O(n + k) where k is the range of values
// Space: O(n + k)
// Stable: Yes (with prefix sums)
void countingSort(std::vector<int>& arr) {
    if (arr.empty()) return;

    int maxVal = *std::max_element(arr.begin(), arr.end());
    int minVal = *std::min_element(arr.begin(), arr.end());
    int range = maxVal - minVal + 1;

    std::vector<int> count(range, 0);
    std::vector<int> output(arr.size());

    // Count occurrences
    for (int x : arr) {
        count[x - minVal]++;
    }

    // Compute prefix sums (for stable sort)
    for (int i = 1; i < range; i++) {
        count[i] += count[i - 1];
    }

    // Build output array (traverse in reverse for stability)
    for (int i = arr.size() - 1; i >= 0; i--) {
        output[count[arr[i] - minVal] - 1] = arr[i];
        count[arr[i] - minVal]--;
    }

    arr = output;
}

int main() {
    std::vector<int> arr = {4, 2, 2, 8, 3, 3, 1};
    countingSort(arr);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 1 2 2 3 3 4 8
    return 0;
}
```

### Complexity

| Case | Time |
|---|---|
| All | O(n + k) |

**Space:** O(n + k).
**Stable:** Yes (with the prefix sum approach).

**When to use:** When k is not much larger than n. If k = O(n), the sort is O(n) — faster than comparison sorts!

**When NOT to use:** When the range k is very large (e.g., sorting 10 numbers in range [0, 10^9]) — the count array would be huge.

### Dry Run

```
Initial: [4, 2, 2, 8, 3, 3, 1]
minVal=1, maxVal=8, range=8

Step 1 — Count occurrences:
  Value:  1  2  3  4  5  6  7  8
  Count: [1, 2, 2, 1, 0, 0, 0, 1]

Step 2 — Prefix sums (cumulative counts):
  Count: [1, 3, 5, 6, 6, 6, 6, 7]
  Meaning: value 1 ends at position 1, value 2 ends at position 3, etc.

Step 3 — Build output (traverse input in reverse for stability):
  i=6: arr[6]=1 → output[0] = 1, count[1] becomes 0
  i=5: arr[5]=3 → output[4] = 3, count[3] becomes 4
  i=4: arr[4]=3 → output[3] = 3, count[3] becomes 3
  i=3: arr[3]=8 → output[6] = 8, count[8] becomes 6
  i=2: arr[2]=2 → output[2] = 2, count[2] becomes 2
  i=1: arr[1]=2 → output[1] = 2, count[2] becomes 1
  i=0: arr[0]=4 → output[3] = 4, count[4] becomes 3

Output: [1, 2, 2, 3, 3, 4, 8] ✓
```

**Why traverse in reverse?** It ensures stability — when two elements have the same value, the one appearing later in the input is placed later in the output, preserving their relative order.

---

## 5.9 Radix Sort

### Concept

Sort numbers **digit by digit**, from least significant to most significant. Use a stable sort (like counting sort) for each digit.

### Visualization

```
Initial:  [170, 45, 75, 90, 802, 24, 2, 66]

Sort by ones digit:
  [170, 90, 802, 2, 24, 45, 75, 66]

Sort by tens digit:
  [802, 2, 24, 45, 66, 170, 75, 90]

Sort by hundreds digit:
  [2, 24, 45, 66, 75, 90, 170, 802]  ✓
```

### Code

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Counting sort by a specific digit (used as subroutine)
void countingSortByDigit(std::vector<int>& arr, int exp) {
    int n = arr.size();
    std::vector<int> output(n);
    std::vector<int> count(10, 0);

    // Count occurrences of each digit
    for (int i = 0; i < n; i++) {
        int digit = (arr[i] / exp) % 10;
        count[digit]++;
    }

    // Prefix sums
    for (int i = 1; i < 10; i++) {
        count[i] += count[i - 1];
    }

    // Build output (reverse for stability)
    for (int i = n - 1; i >= 0; i--) {
        int digit = (arr[i] / exp) % 10;
        output[count[digit] - 1] = arr[i];
        count[digit]--;
    }

    arr = output;
}

// Radix Sort (LSD — Least Significant Digit first)
// Time: O(d × (n + b)) where d = number of digits, b = base (10)
// Space: O(n + b)
// Stable: Yes
void radixSort(std::vector<int>& arr) {
    if (arr.empty()) return;

    int maxVal = *std::max_element(arr.begin(), arr.end());

    // Sort by each digit, from least significant to most
    for (int exp = 1; maxVal / exp > 0; exp *= 10) {
        countingSortByDigit(arr, exp);
    }
}

int main() {
    std::vector<int> arr = {170, 45, 75, 90, 802, 24, 2, 66};
    radixSort(arr);

    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 2 24 45 66 75 90 170 802
    return 0;
}
```

### Complexity

| Case | Time |
|---|---|
| All | O(d × (n + b)) |

Where d = number of digits, b = base (10 for decimal), n = number of elements.

If numbers have a fixed number of digits (e.g., 32-bit integers), d is constant and Radix Sort is **O(n)**.

**Space:** O(n + b).
**Stable:** Yes.

### Dry Run

```
Initial: [170, 45, 75, 90, 802, 24, 2, 66]
maxVal=802, need 3 digit passes

Sort by ones digit (exp=1):
  Digits: 170→0, 45→5, 75→5, 90→0, 802→2, 24→4, 2→2, 66→6
  Stable sort by digit → [170, 90, 802, 2, 24, 45, 75, 66]

Sort by tens digit (exp=10):
  Digits: 170→7, 45→4, 75→7, 90→9, 802→0, 24→2, 2→0, 66→6
  Stable sort by digit → [802, 2, 24, 45, 66, 170, 75, 90]

Sort by hundreds digit (exp=100):
  Digits: 802→8, 2→0, 24→0, 45→0, 66→0, 170→1, 75→0, 90→0
  Stable sort by digit → [2, 24, 45, 66, 75, 90, 170, 802] ✓
```

**Key insight:** Each pass uses a *stable* sort. Stability ensures that elements sorted by less significant digits maintain their relative order when sorted by more significant digits. This is why LSD Radix Sort produces a correct final result.

### When to Use

- When numbers have a bounded number of digits.
- When n is large but the range is manageable.
- As a subroutine for other algorithms.

---

## 5.10 Bucket Sort

### Concept

Distribute elements into buckets, sort each bucket individually, then concatenate. Works well when input is **uniformly distributed**.

### Code

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Bucket Sort for floating-point numbers in [0, 1)
// Time: O(n + k) average, O(n²) worst case
// Space: O(n + k)
// Stable: Depends on the sort used for buckets
void bucketSort(std::vector<float>& arr) {
    int n = arr.size();
    if (n <= 1) return;

    // Create n buckets
    std::vector<std::vector<float>> buckets(n);

    // Distribute elements into buckets
    for (float x : arr) {
        int idx = static_cast<int>(x * n);  // Map [0,1) to [0,n)
        if (idx >= n) idx = n - 1;
        buckets[idx].push_back(x);
    }

    // Sort each bucket
    for (auto& bucket : buckets) {
        std::sort(bucket.begin(), bucket.end());
    }

    // Concatenate buckets
    int idx = 0;
    for (auto& bucket : buckets) {
        for (float x : bucket) {
            arr[idx++] = x;
        }
    }
}

int main() {
    std::vector<float> arr = {0.897, 0.565, 0.656, 0.1234, 0.665, 0.3434};
    bucketSort(arr);

    std::cout << "Sorted: ";
    for (float x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 0.1234 0.3434 0.565 0.656 0.665 0.897
    return 0;
}
```

### Complexity

| Case | Time | When? |
|---|---|---|
| Best | O(n + k) | Uniformly distributed |
| Average | O(n + k) | Uniformly distributed |
| Worst | O(n²) | All elements in one bucket |

**Space:** O(n + k) where k = number of buckets.

### Dry Run

```
Initial: [0.897, 0.565, 0.656, 0.1234, 0.665, 0.3434]
n=6, so 6 buckets covering ranges [0, 0.167), [0.167, 0.333), ...

Step 1 — Distribute into buckets:
  Bucket 0 [0.000-0.167): [0.1234]
  Bucket 1 [0.167-0.333): []
  Bucket 2 [0.333-0.500): [0.3434]
  Bucket 3 [0.500-0.667): [0.565, 0.656]
  Bucket 4 [0.667-0.833): [0.665]
  Bucket 5 [0.833-1.000): [0.897]

Step 2 — Sort each bucket:
  Bucket 3: [0.565, 0.656] — already in order
  All others: single elements, trivially sorted

Step 3 — Concatenate all buckets:
  [0.1234, 0.3434, 0.565, 0.656, 0.665, 0.897] ✓
```

**Why uniform distribution matters:** If all elements land in one bucket, we degrade to O(n²) since that bucket holds all n elements. Uniform distribution keeps buckets small and gives O(n) average time.

---

## 5.11 STL Sorting

### std::sort

The C++ standard library's `std::sort` is typically **IntroSort** — a hybrid of Quick Sort, Heap Sort, and Insertion Sort.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <string>

int main() {
    // Basic sort — ascending
    std::vector<int> nums = {5, 2, 8, 1, 9, 3};
    std::sort(nums.begin(), nums.end());
    // nums: {1, 2, 3, 5, 8, 9}

    // Descending sort
    std::sort(nums.begin(), nums.end(), std::greater<int>());
    // nums: {9, 8, 5, 3, 2, 1}

    // Sort with custom comparator
    std::vector<std::string> words = {"banana", "apple", "cherry", "date"};
    std::sort(words.begin(), words.end(),
        [](const std::string& a, const std::string& b) {
            return a.size() < b.size();  // Sort by length
        });
    // words: {"date", "apple", "banana", "cherry"}

    // Sort subarray
    std::vector<int> arr = {5, 2, 8, 1, 9, 3};
    std::sort(arr.begin() + 1, arr.begin() + 4);  // Sort indices [1, 4)
    // arr: {5, 1, 2, 8, 9, 3}

    // Partial sort — get the k smallest elements
    std::vector<int> ps = {5, 2, 8, 1, 9, 3};
    std::partial_sort(ps.begin(), ps.begin() + 3, ps.end());
    // First 3 elements are the 3 smallest, sorted: {1, 2, 3, ...}

    // nth_element — partition around the nth element
    std::vector<int> ne = {5, 2, 8, 1, 9, 3};
    std::nth_element(ne.begin(), ne.begin() + 2, ne.end());
    // ne[2] is the 3rd smallest element. Elements before are <= ne[2], after are >= ne[2]

    return 0;
}
```

### std::stable_sort

Preserves the relative order of equal elements:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <string>

struct Student {
    std::string name;
    int grade;
};

int main() {
    std::vector<Student> students = {
        {"Alice", 85}, {"Bob", 90}, {"Charlie", 85}, {"Diana", 90}
    };

    // Sort by grade — stable sort preserves original order for equal grades
    std::stable_sort(students.begin(), students.end(),
        [](const Student& a, const Student& b) {
            return a.grade < b.grade;
        });

    for (const auto& s : students) {
        std::cout << s.name << ": " << s.grade << "\n";
    }
    // Alice: 85, Charlie: 85, Bob: 90, Diana: 90
    // Alice and Charlie maintain their original relative order
    // Bob and Diana maintain their original relative order

    return 0;
}
```

### Custom Comparators

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <tuple>

int main() {
    // Sort tuples by multiple criteria
    std::vector<std::tuple<int, int, std::string>> items = {
        {1, 3, "apple"},
        {2, 1, "banana"},
        {1, 2, "cherry"},
        {2, 1, "date"}
    };

    // Sort by first element ascending, then second element descending
    std::sort(items.begin(), items.end(),
        [](const auto& a, const auto& b) {
            if (std::get<0>(a) != std::get<0>(b))
                return std::get<0>(a) < std::get<0>(b);
            return std::get<1>(a) > std::get<1>(b);
        });

    for (const auto& [x, y, name] : items) {
        std::cout << "(" << x << ", " << y << ", " << name << ")\n";
    }
    // (1, 3, apple), (1, 2, cherry), (2, 1, banana), (2, 1, date)

    return 0;
}
```

---

## 5.12 Comparison of All Algorithms

| Algorithm | Best | Average | Worst | Space | Stable | In-Place |
|---|---|---|---|---|---|---|
| Bubble Sort | O(n) | O(n²) | O(n²) | O(1) | ✅ | ✅ |
| Selection Sort | O(n²) | O(n²) | O(n²) | O(1) | ❌ | ✅ |
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) | ✅ | ✅ |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | ✅ | ❌ |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | ❌ | ✅ |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | ❌ | ✅ |
| Counting Sort | O(n+k) | O(n+k) | O(n+k) | O(n+k) | ✅ | ❌ |
| Radix Sort | O(d(n+b)) | O(d(n+b)) | O(d(n+b)) | O(n+b) | ✅ | ❌ |
| Bucket Sort | O(n+k) | O(n+k) | O(n²) | O(n+k) | ✅ | ❌ |

### Decision Guide

```
Need stable sort?
├── Yes → Merge Sort (general) or Counting/Radix (integers)
└── No
    ├── Need guaranteed O(n log n)? → Heap Sort or Merge Sort
    ├── Need in-place? → Quick Sort (average) or Heap Sort
    ├── Small array (n < 50)? → Insertion Sort
    ├── Nearly sorted? → Insertion Sort or Timsort
    └── General purpose? → Quick Sort or std::sort
```

### The Comparison Sort Lower Bound

**Theorem:** Any comparison-based sorting algorithm requires Ω(n log n) comparisons in the worst case.

**Proof sketch:** There are n! possible permutations of n elements. Each comparison eliminates at most half the possibilities. After k comparisons, at most 2^k outcomes. We need 2^k ≥ n!, so k ≥ log₂(n!) = Ω(n log n).

This means Merge Sort, Quick Sort, and Heap Sort are **asymptotically optimal** among comparison sorts. Counting Sort and Radix Sort beat this bound by not using comparisons.

---

## Interview Tips

1. **Know Merge Sort and Quick Sort cold.** They're the most commonly asked about.

2. **Quick Sort's partition** is a standalone technique. It's used in Quick Select (finding kth element) and other problems.

3. **Stability matters.** When asked to sort by multiple criteria, stability is essential.

4. **std::sort is IntroSort:** Quick Sort for most of the work, switches to Heap Sort if recursion gets too deep, switches to Insertion Sort for small subarrays.

5. **Non-comparison sorts** (Counting, Radix, Bucket) are O(n) but have constraints on input type/range.

6. **Practice the partition step** — it's the core of Quick Sort and appears in many interview problems (e.g., Dutch National Flag).

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---|---|---|
| Using `std::sort` on linked list | O(n²) — no random access | Use `list.sort()` |
| Wrong comparator (not strict weak ordering) | Undefined behavior | Ensure `comp(a,a)` is false, transitivity holds |
| Forgetting stability requirement | Wrong answer for multi-key sort | Use `std::stable_sort` |
| Quick Sort pivot = first element on sorted data | O(n²) worst case | Randomize pivot |
| Off-by-one in partition bounds | Infinite loop or wrong result | Test with small examples |
| Not handling equal elements in partition | Infinite loop | Include equality in one side |

## Practice Problems

| # | Problem | Difficulty | Key Concept |
|---|---|---|---|
| 1 | Sort an array of 0s, 1s, and 2s | Easy | Dutch National Flag |
| 2 | Merge two sorted arrays | Easy | Merge step of merge sort |
| 3 | Kth largest element | Medium | Quick Select / Heap |
| 4 | Sort colors (3-way partition) | Medium | Partition variation |
| 5 | Merge intervals | Medium | Sort + linear scan |
| 6 | Largest number (custom sort) | Medium | Custom comparator |
| 7 | Count inversions | Medium | Modified merge sort |
| 8 | Find k closest points to origin | Medium | Partial sort / nth_element |
| 9 | Maximum gap | Hard | Bucket sort / pigeonhole |
| 10 | Count of smaller numbers after self | Hard | Merge sort with indices |

---

## Additional Exercises

### Exercise 1: Sort Array by Parity
**Difficulty**: Easy
**Problem**: Given an array of integers, rearrange it so that all even numbers come before all odd numbers. The relative order within even/odd groups does not matter.
**Hint**: Use two pointers: one at the start (for evens) and one at the end (for odds). Swap when the left pointer finds an odd and the right pointer finds an even.
**Expected Time Complexity**: O(n), Space: O(1).

### Exercise 2: Find Kth Largest Element
**Difficulty**: Medium
**Problem**: Given an unsorted array, find the kth largest element without fully sorting the array.
**Hint**: Use Quick Select: partition around a pivot like Quick Sort, but only recurse into the side that contains the kth element. Average case is O(n). Alternatively, use a min-heap of size k.
**Expected Time Complexity**: O(n) average with Quick Select, O(n log k) with heap.

### Exercise 3: Merge K Sorted Arrays
**Difficulty**: Hard
**Problem**: Given k sorted arrays, merge them into one sorted array.
**Hint**: Use a min-heap containing the smallest unprocessed element from each array. Extract the minimum, then insert the next element from the same array. Alternatively, merge pairs of arrays iteratively (like merge sort's merge step applied k-1 times).
**Expected Time Complexity**: O(N log k) where N is total elements, using a heap.

### Exercise 4: Sort Characters By Frequency
**Difficulty**: Medium
**Problem**: Given a string, sort characters by frequency in descending order. Characters with higher frequency appear first.
**Hint**: Count frequencies with a hash map. Use a bucket sort approach (buckets indexed by frequency) or sort the (char, freq) pairs by frequency. For bucket sort, iterate from highest bucket to lowest.
**Expected Time Complexity**: O(n) with bucket sort, O(n log n) with comparison sort.

### Exercise 5: Wiggle Sort
**Difficulty**: Medium
**Problem**: Given an unsorted array, reorder it such that `nums[0] <= nums[1] >= nums[2] <= nums[3]...`
**Hint**: Single pass: for each index i, if i is even and nums[i] > nums[i+1], swap. If i is odd and nums[i] < nums[i+1], swap. This works because each swap fixes the current position without breaking previous ones.
**Expected Time Complexity**: O(n), Space: O(1).

### Exercise 6: Maximum Gap Between Consecutive Sorted Elements
**Difficulty**: Hard
**Problem**: Given an unsorted array, find the maximum difference between successive elements in the sorted version. Must run in O(n) time and O(n) space.
**Hint**: Use bucket sort / pigeonhole principle. With n elements and range [min, max], the max gap must be at least `(max-min)/(n-1)`. Create n-1 buckets of that width. The max gap is between consecutive buckets (not within a bucket).
**Expected Time Complexity**: O(n), Space: O(n).

### Exercise 7: Sort an Array of 0s, 1s, and 2s (Dutch National Flag)
**Difficulty**: Easy
**Problem**: Given an array containing only 0s, 1s, and 2s, sort it in-place in a single pass.
**Hint**: Use three-way partitioning with pointers low, mid, high. All elements before low are 0, all between low and mid are 1, all after high are 2. Process mid: if 0, swap with low; if 2, swap with high; if 1, advance mid.
**Expected Time Complexity**: O(n), Space: O(1).

### Exercise 8: Count Inversions in an Array
**Difficulty**: Medium
**Problem**: An inversion is a pair (i, j) where i < j but arr[i] > arr[i]. Count the total number of inversions.
**Hint**: Modify merge sort. During the merge step, when an element from the right half is placed before elements from the left half, it forms inversions with all remaining elements in the left half. Count these and add to the total.
**Expected Time Complexity**: O(n log n).

### Exercise 9: Find All Duplicate Elements in O(n) Time and O(1) Space
**Difficulty**: Medium
**Problem**: Given an array of n integers where each integer is in [1, n] and some appear twice, find all duplicates in O(n) time and O(1) extra space.
**Hint**: Use the array itself as a hash set. For each element, negate the value at index `abs(arr[i]) - 1`. If it's already negative, `abs(arr[i])` is a duplicate.
**Expected Time Complexity**: O(n), Space: O(1) excluding output.

### Exercise 10: Minimum Number of Moves to Sort Array (Adjacent Swaps)
**Difficulty**: Medium
**Problem**: Given an array, find the minimum number of adjacent swaps needed to sort it.
**Hint**: This equals the number of inversions. Each adjacent swap reduces the inversion count by exactly 1. Use modified merge sort to count inversions.
**Expected Time Complexity**: O(n log n).

---

## Additional Interview Questions

### Q1: Why is Quick Sort preferred over Merge Sort in practice despite having O(n²) worst case?
**Key Insight**: Quick Sort has smaller constant factors (fewer comparisons and swaps per element), better cache locality (operates on contiguous memory in-place), and uses O(log n) auxiliary space vs O(n) for Merge Sort. The randomized version has an astronomically low probability of hitting O(n²). C++'s `std::sort` uses IntroSort (Quick Sort + Heap Sort fallback), which guarantees O(n log n) worst case while keeping Quick Sort's practical speed.
**Optimal Complexity**: O(n log n) average, O(n²) worst case (but extremely unlikely with randomization).

### Q2: When would you use a non-comparison sort (Counting/Radix/Bucket) over a comparison sort?
**Key Insight**: Non-comparison sorts beat the Ω(n log n) lower bound by exploiting properties of the data (integers, fixed-width keys). Use Counting Sort when the range k is O(n) — it's O(n+k). Use Radix Sort when elements have a fixed number of digits — it's O(d×n). Use Bucket Sort when input is uniformly distributed over a known range. The constraint: these sorts work on integers or discrete values, not arbitrary comparable objects.
**Optimal Complexity**: Counting: O(n+k). Radix: O(d(n+b)). Bucket: O(n+k) average.

### Q3: What is stability in sorting and why does it matter?
**Key Insight**: A stable sort preserves the relative order of equal elements. This is crucial when sorting by multiple criteria: first sort by secondary key, then by primary key with a stable sort. Example: sort students by name (stable), then by grade (stable) — students with the same grade remain alphabetically sorted. Unstable sorts (Quick Sort, Heap Sort) can scramble the previous ordering.
**Optimal Complexity**: Stability doesn't affect time complexity. Stable sorts include Merge Sort, Counting Sort, Radix Sort, and Insertion Sort.

### Q4: How does the Dutch National Flag algorithm work and where is it used?
**Key Insight**: It's a three-way partition that divides an array into three sections in a single pass using three pointers (low, mid, high). Elements before low are in group 0, between low and mid in group 1, after high in group 2. Used in: sorting arrays with 3 distinct values, Quick Sort's 3-way partition (handles duplicates efficiently — O(n) when all elements are equal vs O(n²) for standard partition).
**Optimal Complexity**: O(n) single pass, O(1) space.

### Q5: Explain how to use merge sort to count inversions.
**Key Insight**: During the merge step, when an element from the right subarray is placed before remaining elements in the left subarray, it forms inversions with all those remaining left elements. Count these and add to the total. The merge sort structure naturally examines all pairs (i, j) where i is in the left half and j is in the right half, covering all inversions exactly once.
**Optimal Complexity**: O(n log n) — same as merge sort, but with an O(1) counter added per merge step.

### Q6: What is IntroSort and why is it used in `std::sort`?
**Key Insight**: IntroSort starts with Quick Sort but monitors recursion depth. If depth exceeds 2×log(n), it switches to Heap Sort to avoid O(n²) worst case. For small subarrays (n ≤ 16), it switches to Insertion Sort for its low overhead. This hybrid guarantees O(n log n) worst case while maintaining Quick Sort's practical speed and cache efficiency.
**Optimal Complexity**: O(n log n) guaranteed worst case.

### Q7: How would you sort a linked list efficiently?
**Key Insight**: Merge Sort is the best choice for linked lists. Unlike arrays, linked lists can be merged in O(1) extra space (just relink pointers). Quick Sort is problematic because random access is O(n) and partitioning creates overhead. Split the list using the slow/fast pointer technique (find middle in O(n)), recursively sort both halves, then merge.
**Optimal Complexity**: O(n log n) time, O(1) auxiliary space (excluding recursion stack).

### Q8: How do you sort data that doesn't fit in memory (external sorting)?
**Key Insight**: External Merge Sort. Divide data into chunks that fit in memory, sort each chunk (in-memory sort), write sorted chunks to disk. Then merge chunks using a k-way merge with a min-heap, reading one block at a time from each chunk. Minimize disk I/O by using large block sizes. This is the same algorithm databases use for sorting large tables.
**Optimal Complexity**: O(n log n) comparisons, but dominated by I/O: O(n log(n/M) / B) block transfers, where M = memory size, B = block size.

### Q9: When is insertion sort actually the best choice?
**Key Insight**: Insertion sort excels for: (1) small arrays (n < 50) — low overhead beats asymptotic advantage of O(n log n) sorts, (2) nearly sorted data — O(n) adaptive performance, (3) online sorting — elements arrive one at a time, (4) as a subroutine in hybrid sorts (IntroSort, Timsort use it for small chunks). It's also stable and in-place.
**Optimal Complexity**: O(n) for nearly sorted, O(n²) worst case. Best for small or nearly sorted data.

### Q10: How would you sort an array of objects by multiple criteria?
**Key Insight**: Use a custom comparator that checks criteria in priority order. For example, sort students by grade (descending), then by name (ascending): `if (a.grade != b.grade) return a.grade > b.grade; return a.name < b.name;`. For a stable multi-key sort, sort by least important key first using a stable sort, then by more important keys. `std::stable_sort` is ideal for this.
**Optimal Complexity**: O(n log n) per sort pass. With stable sorting and k criteria, you can do k passes of O(n log n) each, or one pass with a compound comparator.

## See Also

- [Chapter 6: Searching](ch06-searching.md) — Binary search and its variants; searching is the natural complement to sorting.
- [Chapter 34: Two Pointers](ch34-two-pointers.md) — A technique that often follows sorting; two pointers exploit sorted order for O(n) solutions.
- [Chapter 39: Divide and Conquer](ch39-divide-conquer.md) — Merge sort and quicksort are divide-and-conquer algorithms; understanding the paradigm deepens sorting knowledge.
- [Chapter 15: Heaps](ch15-heaps.md) — Heapsort and priority queues; heaps are the foundation for selection-based algorithms.
- [Chapter 130: Coordinate Compression](ch130-coordinate-compression.md) — A technique that uses sorting to map large value ranges to compact indices.

*In the next chapter, we'll study searching algorithms — particularly binary search, one of the most powerful and versatile techniques in interviews.*
