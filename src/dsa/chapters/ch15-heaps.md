# Chapter 15: Heaps and Priority Queues

## 15.1 Heap Property

A **heap** is a specialized tree-based data structure that satisfies the **heap property**. It is one of the most elegant and widely used data structures in computer science, forming the backbone of priority queues, heap sort, and numerous graph algorithms.

### Max-Heap vs Min-Heap

There are two fundamental variants:

| Property | Max-Heap | Min-Heap |
|----------|----------|----------|
| Root element | Maximum | Minimum |
| Property | `A[parent] ≥ A[child]` | `A[parent] ≤ A[child]` |
| Use case | Extract maximum | Extract minimum |
| STL | `priority_queue<T>` | `priority_queue<T, vector<T>, greater<T>>` |

**Key insight**: A heap is **not** a sorted structure. It is a **partially ordered** structure. The only guarantee is that the root is the extremum (max or min). Siblings have no ordering relationship with each other.

### Why a Complete Binary Tree?

A heap is always a **complete binary tree** — every level is fully filled except possibly the last level, which is filled from left to right. This is critical for two reasons:

1. **Guaranteed O(log n) height**: A complete binary tree with `n` nodes has height `⌊log₂ n⌋`. This means all operations that traverse from root to leaf are O(log n).

2. **Compact array representation**: Because the tree is complete, we can store it in a simple array with no gaps, avoiding the overhead of pointers.

```
Max-Heap as a tree:          Array representation:
        90                   [90, 80, 70, 50, 60, 30, 20]
       /  \                   0   1   2   3   4   5   6
     80    70
    / \   / \
  50  60 30  20
```

The complete binary tree property ensures that the array has no "holes" — every index from 0 to n-1 is occupied, which is extremely cache-friendly.

---

## 15.2 Binary Heap Implementation

### Array Representation and Index Relationships

For a zero-indexed array, the parent-child relationships are:

```
Parent of node i:      (i - 1) / 2      (integer division)
Left child of node i:  2 * i + 1
Right child of node i: 2 * i + 2
```

For a one-indexed array (common in competitive programming):

```
Parent of node i:      i / 2
Left child of node i:  2 * i
Right child of node i: 2 * i + 1
```

**Why does this work?** In a complete binary tree stored in an array, the nodes are laid out level by level, left to right. If node `i` is at some position, its left child is at `2i+1` and right child at `2i+2`. This is a direct consequence of the binary representation of indices in a level-order traversal.

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <stdexcept>
#include <algorithm>
#include <functional>

template <typename T, typename Compare = std::less<T>>
class MaxHeap {
private:
    std::vector<T> data_;
    Compare comp_;

    // Sift up: restore heap property by moving element up
    // Used after insertion — the new element may be larger than its parent
    void siftUp(int index) {
        while (index > 0) {
            int parent = (index - 1) / 2;
            if (comp_(data_[parent], data_[index])) {
                std::swap(data_[parent], data_[index]);
                index = parent;
            } else {
                break;
            }
        }
    }

    // Sift down: restore heap property by moving element down
    // Used after extraction — the replacement element may violate the property
    void siftDown(int index) {
        int n = static_cast<int>(data_.size());
        while (true) {
            int largest = index;
            int left = 2 * index + 1;
            int right = 2 * index + 2;

            if (left < n && comp_(data_[largest], data_[left])) {
                largest = left;
            }
            if (right < n && comp_(data_[largest], data_[right])) {
                largest = right;
            }

            if (largest != index) {
                std::swap(data_[index], data_[largest]);
                index = largest;
            } else {
                break;
            }
        }
    }

public:
    MaxHeap() = default;

    // Build heap from array — O(n) using bottom-up construction
    explicit MaxHeap(const std::vector<T>& arr) : data_(arr) {
        buildHeap();
    }

    void buildHeap() {
        // Start from the last non-leaf node and sift down each
        // Last non-leaf node is at index (n/2 - 1)
        int n = static_cast<int>(data_.size());
        for (int i = n / 2 - 1; i >= 0; --i) {
            siftDown(i);
        }
    }

    void insert(const T& value) {
        data_.push_back(value);
        siftUp(static_cast<int>(data_.size()) - 1);
    }

    T extractMax() {
        if (data_.empty()) {
            throw std::runtime_error("Heap is empty");
        }
        T maxVal = data_[0];
        data_[0] = data_.back();
        data_.pop_back();
        if (!data_.empty()) {
            siftDown(0);
        }
        return maxVal;
    }

    const T& peek() const {
        if (data_.empty()) {
            throw std::runtime_error("Heap is empty");
        }
        return data_[0];
    }

    // Decrease key: increase the value at index (for max-heap, "decrease" means
    // making it more towards max direction). We sift up.
    void increaseKey(int index, const T& newValue) {
        if (comp_(newValue, data_[index])) {
            throw std::runtime_error("New value is smaller than current");
        }
        data_[index] = newValue;
        siftUp(index);
    }

    // Decrease key: decrease the value at index. We sift down.
    void decreaseKey(int index, const T& newValue) {
        if (comp_(data_[index], newValue)) {
            throw std::runtime_error("New value is larger than current");
        }
        data_[index] = newValue;
        siftDown(index);
    }

    bool empty() const { return data_.empty(); }
    size_t size() const { return data_.size(); }

    void print() const {
        for (const auto& val : data_) {
            std::cout << val << " ";
        }
        std::cout << "\n";
    }
};

int main() {
    // Build heap from array
    std::vector<int> arr = {3, 1, 6, 5, 2, 4};
    MaxHeap<int> heap(arr);

    std::cout << "Built heap: ";
    heap.print();  // Should show max-heap ordering at root

    heap.insert(10);
    std::cout << "After insert(10): ";
    heap.print();

    std::cout << "Extract max: " << heap.extractMax() << "\n";
    std::cout << "Extract max: " << heap.extractMax() << "\n";

    return 0;
}
```

### Build-Heap: O(n) Proof

A common interview question is: **Why is building a heap O(n) and not O(n log n)?**

Naive analysis suggests: we call `siftDown` on n/2 nodes, each costing O(log n), giving O(n log n). But this is a loose bound.

**Tight analysis using potential method:**

A complete binary tree of height h has at most ⌈n/2^(h+1)⌉ nodes at height h. The work done by `siftDown` on a node at height h is O(h) (it can only go down to a leaf).

```
Total work = Σ (h=0 to log n)  [number of nodes at height h] × h
           = Σ (h=0 to log n)  ⌈n/2^(h+1)⌉ × h
           ≤ n × Σ (h=0 to ∞)  h/2^(h+1)
           = n × (1/2 × 0 + 1/4 × 1 + 1/8 × 2 + ...)
           = n × 2
           = O(n)
```

The key insight: most nodes are near the bottom of the tree, where `siftDown` does very little work. Only a few nodes near the top do significant work. The sum converges to 2n.

**Bottom-up vs Top-down building:**
- Bottom-up (our approach): O(n) — start from leaves, sift down
- Top-down (insert one by one): O(n log n) — each insert may sift up the full height

---

## 15.3 Heap Operations — Detailed Analysis

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| Insert | O(log n) | Sift up from leaf to root (worst case) |
| Extract-Min/Max | O(log n) | Move last element to root, sift down |
| Peek (Find-Min/Max) | O(1) | Root is always the extremum |
| Decrease-Key | O(log n) | Sift up after decreasing (min-heap) |
| Increase-Key | O(log n) | Sift down after increasing (min-heap) |
| Build Heap | O(n) | Bottom-up sift down (see proof above) |
| Merge Two Heaps | O(n) | Concatenate arrays + rebuild, or use mergeable heaps |
| Delete Arbitrary | O(n) search + O(log n) sift | Need to find the element first |

### Dry Run: Insert and Extract-Max

Starting max-heap: `[90, 80, 70, 50, 60, 30, 20]`

**Insert 85:**
```
Step 1: Add 85 at the end → [90, 80, 70, 50, 60, 30, 20, 85]
Step 2: Sift up 85 (index 7)
  - Parent at index 3 = 50. 85 > 50, swap → [90, 80, 70, 85, 60, 30, 20, 50]
  - Parent at index 1 = 80. 85 > 80, swap → [90, 85, 70, 80, 60, 30, 20, 50]
  - Parent at index 0 = 90. 85 ≤ 90, stop.
Result: [90, 85, 70, 80, 60, 30, 20, 50]
```

**Extract Max from [90, 85, 70, 80, 60, 30, 20, 50]:**
```
Step 1: Save max = 90. Move last element (50) to root → [50, 85, 70, 80, 60, 30, 20]
Step 2: Sift down 50 (index 0)
  - Children: 85 (idx 1), 70 (idx 2). Max child = 85. 50 < 85, swap → [85, 50, 70, 80, 60, 30, 20]
  - Children of idx 1: 80 (idx 3), 60 (idx 4). Max child = 80. 50 < 80, swap → [85, 80, 70, 50, 60, 30, 20]
  - Children of idx 3: none (idx 7 is out of bounds). Stop.
Result: [85, 80, 70, 50, 60, 30, 20]. Extracted value: 90.
```

---

## 15.4 Heap Sort

Heap sort is an elegant, in-place, comparison-based sorting algorithm with guaranteed O(n log n) time complexity.

### Algorithm

1. **Build a max-heap** from the input array — O(n)
2. **Repeatedly extract the maximum**: swap root with last unsorted element, reduce heap size, sift down — O(n log n)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

void siftDown(std::vector<int>& arr, int n, int i) {
    while (true) {
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
            i = largest;
        } else {
            break;
        }
    }
}

void heapSort(std::vector<int>& arr) {
    int n = static_cast<int>(arr.size());

    // Phase 1: Build max-heap — O(n)
    for (int i = n / 2 - 1; i >= 0; --i) {
        siftDown(arr, n, i);
    }

    // Phase 2: Extract elements one by one — O(n log n)
    for (int i = n - 1; i > 0; --i) {
        // Move current root (maximum) to end
        std::swap(arr[0], arr[i]);
        // Restore heap property on reduced heap
        siftDown(arr, i, 0);
    }
}

int main() {
    std::vector<int> arr = {12, 11, 13, 5, 6, 7, 3, 1, 9, 4};

    std::cout << "Before sort: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";

    heapSort(arr);

    std::cout << "After sort:  ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";

    return 0;
}
```

### Dry Run: Heap Sort on [4, 10, 3, 5, 1]

```
Initial array: [4, 10, 3, 5, 1]

Phase 1: Build max-heap
  Last non-leaf = (5/2 - 1) = 1
  SiftDown(1): node=10, children=5,1. 10 is largest. No swap. → [4, 10, 3, 5, 1]
  SiftDown(0): node=4, children=10,3. Swap with 10 → [10, 4, 3, 5, 1]
    SiftDown(1): node=4, children=5,1. Swap with 5 → [10, 5, 3, 4, 1]
  Max-heap: [10, 5, 3, 4, 1]

Phase 2: Extract elements
  i=4: Swap arr[0] and arr[4] → [1, 5, 3, 4, |10]. SiftDown on [1,5,3,4]
    Swap 1↔5 → [5, 1, 3, 4]. Swap 1↔4 → [5, 4, 3, 1]. Heap: [5,4,3,1,|10]

  i=3: Swap arr[0] and arr[3] → [1, 4, 3, |5, 10]. SiftDown on [1,4,3]
    Swap 1↔4 → [4, 1, 3]. Heap: [4,1,3,|5,10]

  i=2: Swap arr[0] and arr[2] → [3, 1, |4, 5, 10]. SiftDown on [3,1]
    3 > 1. No swap. Heap: [3,1,|4,5,10]

  i=1: Swap arr[0] and arr[1] → [1, |3, 4, 5, 10]. Done.

Sorted: [1, 3, 4, 5, 10] ✓
```

### Properties of Heap Sort

| Property | Value |
|----------|-------|
| Time (all cases) | O(n log n) |
| Space | O(1) — in-place |
| Stable? | No — relative order of equal elements may change |
| Adaptive? | No — always O(n log n) even for nearly sorted input |
| Cache performance | Poor — sift-down jumps around the array |

**Comparison with other O(n log n) sorts:**

| Algorithm | Best | Average | Worst | Space | Stable | Adaptive |
|-----------|------|---------|-------|-------|--------|----------|
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No | No |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes | No |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No | Yes |

Heap sort is preferred when guaranteed worst-case O(n log n) and O(1) extra space are both required.

---

## 15.5 STL Priority Queue

The C++ STL provides `std::priority_queue` in `<queue>`, which is a max-heap by default.

### Basic Usage

```cpp
#include <iostream>
#include <queue>
#include <vector>
#include <functional>
#include <string>

int main() {
    // Max-heap (default)
    std::priority_queue<int> maxHeap;
    maxHeap.push(3);
    maxHeap.push(1);
    maxHeap.push(4);
    maxHeap.push(1);
    maxHeap.push(5);

    std::cout << "Max-heap: ";
    while (!maxHeap.empty()) {
        std::cout << maxHeap.top() << " ";  // 5 4 3 1 1
        maxHeap.pop();
    }
    std::cout << "\n";

    // Min-heap
    std::priority_queue<int, std::vector<int>, std::greater<int>> minHeap;
    minHeap.push(3);
    minHeap.push(1);
    minHeap.push(4);
    minHeap.push(1);
    minHeap.push(5);

    std::cout << "Min-heap: ";
    while (!minHeap.empty()) {
        std::cout << minHeap.top() << " ";  // 1 1 3 4 5
        minHeap.pop();
    }
    std::cout << "\n";

    return 0;
}
```

### Custom Comparators

```cpp
#include <iostream>
#include <queue>
#include <vector>
#include <string>
#include <functional>

struct Task {
    std::string name;
    int priority;
    int arrivalTime;

    Task(std::string n, int p, int a) : name(std::move(n)), priority(p), arrivalTime(a) {}
};

// Comparator for priority queue: higher priority first, then earlier arrival
struct TaskComparator {
    bool operator()(const Task& a, const Task& b) const {
        if (a.priority != b.priority) {
            return a.priority < b.priority;  // Higher priority = higher value = dequeued first
        }
        return a.arrivalTime > b.arrivalTime;  // Earlier arrival = dequeued first
    }
};

// Lambda-based comparator (C++17 approach with decltype)
auto cmp = [](const std::pair<int, std::string>& a,
              const std::pair<int, std::string>& b) {
    return a.first > b.first;  // min-heap by first element
};

int main() {
    // Using functor
    std::priority_queue<Task, std::vector<Task>, TaskComparator> taskQueue;
    taskQueue.push({"Email", 2, 100});
    taskQueue.push({"Urgent Bug", 5, 101});
    taskQueue.push({"Code Review", 3, 99});
    taskQueue.push({"Deploy", 5, 102});

    std::cout << "Task execution order:\n";
    while (!taskQueue.empty()) {
        auto t = taskQueue.top();
        std::cout << "  " << t.name << " (priority=" << t.priority << ")\n";
        taskQueue.pop();
    }
    // Output: Urgent Bug, Deploy, Code Review, Email

    // Using lambda with decltype
    std::priority_queue<std::pair<int, std::string>,
                        std::vector<std::pair<int, std::string>>,
                        decltype(cmp)> pq(cmp);

    pq.push({3, "three"});
    pq.push({1, "one"});
    pq.push({2, "two"});

    while (!pq.empty()) {
        std::cout << pq.top().first << ":" << pq.top().second << " ";
        pq.pop();
    }
    // Output: 1:one 2:two 3:three

    return 0;
}
```

### When to Use Min-Heap vs Max-Heap

| Scenario | Heap Type | Reason |
|----------|-----------|--------|
| Find k-th largest | Min-heap of size k | Keep smallest of top-k at top for efficient eviction |
| Find k-th smallest | Max-heap of size k | Keep largest of bottom-k at top |
| Merge k sorted lists | Min-heap | Always pick the smallest among k candidates |
| Dijkstra's algorithm | Min-heap | Extract the unvisited node with minimum distance |
| Task scheduler (high priority first) | Max-heap | Extract the highest priority task |
| Median maintenance | Both! | Max-heap for lower half, min-heap for upper half |

---

## 15.6 Applications

### Application 1: K-th Largest Element in a Stream

**Problem**: Design a class that finds the k-th largest element in a stream. Note that it is the k-th largest element in sorted order, not the k-th distinct element.

**Approach**: Maintain a min-heap of size k. The root of this min-heap is the k-th largest element.

```cpp
#include <iostream>
#include <queue>
#include <vector>

class KthLargest {
private:
    int k_;
    std::priority_queue<int, std::vector<int>, std::greater<int>> minHeap_;

public:
    KthLargest(int k, const std::vector<int>& nums) : k_(k) {
        for (int num : nums) {
            add(num);
        }
    }

    int add(int val) {
        if (static_cast<int>(minHeap_.size()) < k_) {
            minHeap_.push(val);
        } else if (val > minHeap_.top()) {
            minHeap_.pop();
            minHeap_.push(val);
        }
        return minHeap_.top();
    }
};

int main() {
    std::vector<int> nums = {4, 5, 8, 2};
    KthLargest kthLargest(3, nums);

    std::cout << kthLargest.add(3) << "\n";   // returns 4
    std::cout << kthLargest.add(5) << "\n";   // returns 5
    std::cout << kthLargest.add(10) << "\n";  // returns 5
    std::cout << kthLargest.add(9) << "\n";   // returns 8
    std::cout << kthLargest.add(4) << "\n";   // returns 8

    return 0;
}
```

**Complexity**: Each `add` is O(log k). Space: O(k).

**Why min-heap of size k?** We want the k largest elements. A min-heap of size k keeps the smallest of those k elements at the top. When a new element arrives, if it's larger than the current k-th largest (heap top), we replace the top. This ensures the heap always contains exactly the k largest elements seen so far.

### Application 2: Merge K Sorted Lists

```cpp
#include <iostream>
#include <vector>
#include <queue>

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

struct Compare {
    bool operator()(ListNode* a, ListNode* b) const {
        return a->val > b->val;  // min-heap
    }
};

ListNode* mergeKLists(std::vector<ListNode*>& lists) {
    std::priority_queue<ListNode*, std::vector<ListNode*>, Compare> pq;

    // Push the head of each non-empty list
    for (ListNode* head : lists) {
        if (head) {
            pq.push(head);
        }
    }

    ListNode dummy(0);
    ListNode* tail = &dummy;

    while (!pq.empty()) {
        ListNode* smallest = pq.top();
        pq.pop();

        tail->next = smallest;
        tail = tail->next;

        if (smallest->next) {
            pq.push(smallest->next);
        }
    }

    return dummy.next;
}

// Helper to create linked list from vector
ListNode* createList(const std::vector<int>& vals) {
    ListNode dummy(0);
    ListNode* tail = &dummy;
    for (int v : vals) {
        tail->next = new ListNode(v);
        tail = tail->next;
    }
    return dummy.next;
}

void printList(ListNode* head) {
    while (head) {
        std::cout << head->val;
        if (head->next) std::cout << " -> ";
        head = head->next;
    }
    std::cout << "\n";
}

int main() {
    std::vector<ListNode*> lists = {
        createList({1, 4, 5}),
        createList({1, 3, 4}),
        createList({2, 6})
    };

    ListNode* merged = mergeKLists(lists);
    printList(merged);  // 1 -> 1 -> 2 -> 3 -> 4 -> 4 -> 5 -> 6

    return 0;
}
```

**Complexity**: O(N log k) where N is total number of elements across all lists, and k is the number of lists. Each element is pushed and popped once, each operation O(log k).

### Application 3: Top K Frequent Elements

```cpp
#include <iostream>
#include <vector>
#include <unordered_map>
#include <queue>

std::vector<int> topKFrequent(const std::vector<int>& nums, int k) {
    // Count frequencies
    std::unordered_map<int, int> freq;
    for (int num : nums) {
        freq[num]++;
    }

    // Min-heap of size k, ordered by frequency
    // pair<frequency, element>
    using P = std::pair<int, int>;
    std::priority_queue<P, std::vector<P>, std::greater<P>> pq;

    for (auto& [num, count] : freq) {
        if (static_cast<int>(pq.size()) < k) {
            pq.push({count, num});
        } else if (count > pq.top().first) {
            pq.pop();
            pq.push({count, num});
        }
    }

    std::vector<int> result;
    while (!pq.empty()) {
        result.push_back(pq.top().second);
        pq.pop();
    }
    return result;
}

int main() {
    std::vector<int> nums = {1, 1, 1, 2, 2, 3};
    auto result = topKFrequent(nums, 2);
    for (int x : result) {
        std::cout << x << " ";
    }
    std::cout << "\n";  // Output: 1 2 (order may vary)
    return 0;
}
```

### Application 4: Find Median from Data Stream

This is a classic problem that uses **two heaps** — a max-heap for the lower half and a min-heap for the upper half.

```cpp
#include <iostream>
#include <queue>
#include <vector>

class MedianFinder {
private:
    // Max-heap for the lower half
    std::priority_queue<int> maxHeap_;
    // Min-heap for the upper half
    std::priority_queue<int, std::vector<int>, std::greater<int>> minHeap_;

public:
    void addNum(int num) {
        // Always add to max-heap first (lower half)
        maxHeap_.push(num);

        // Ensure max-heap's top ≤ min-heap's top
        // Move the largest from lower half to upper half
        minHeap_.push(maxHeap_.top());
        maxHeap_.pop();

        // Balance sizes: max-heap can have at most 1 more element
        if (minHeap_.size() > maxHeap_.size()) {
            maxHeap_.push(minHeap_.top());
            minHeap_.pop();
        }
    }

    double findMedian() {
        if (maxHeap_.size() > minHeap_.size()) {
            return maxHeap_.top();
        }
        return (maxHeap_.top() + minHeap_.top()) / 2.0;
    }
};

int main() {
    MedianFinder mf;
    std::vector<int> stream = {5, 15, 1, 3, 8, 7, 9};

    for (int num : stream) {
        mf.addNum(num);
        std::cout << "Added " << num << ", median = " << mf.findMedian() << "\n";
    }
    return 0;
}
```

**How it works**:
- The lower half (max-heap) contains the smaller elements; the top is the largest of the small ones.
- The upper half (min-heap) contains the larger elements; the top is the smallest of the large ones.
- We maintain the invariant: `maxHeap.size() - minHeap.size()` is 0 or 1.
- Median is either `maxHeap.top()` (odd count) or the average of both tops (even count).

**Complexity**: `addNum` is O(log n), `findMedian` is O(1).

---

## 15.7 Variants

### D-ary Heap

A **d-ary heap** is a generalization of a binary heap where each node has d children instead of 2.

```
Parent of node i:      (i - 1) / d
Children of node i:    d*i + 1, d*i + 2, ..., d*i + d
```

| Property | Binary Heap | D-ary Heap |
|----------|------------|------------|
| Height | log₂ n | log_d n |
| Insert (sift up) | O(log₂ n) | O(log_d n) — faster! |
| Extract-min (sift down) | O(log₂ n) | O(d · log_d n) — slower! |
| Decrease-key | O(log₂ n) | O(log_d n) — faster! |

**When to use d-ary heap**: When you perform many more `decrease-key` operations than `extract-min` (e.g., Dijkstra's algorithm on dense graphs). A 4-ary heap is often a good practical choice.

### Fibonacci Heap

The **Fibonacci heap** is a theoretically superior heap that achieves amortized O(1) for `insert`, `decrease-key`, and `merge`, and O(log n) for `extract-min`.

| Operation | Binary Heap | Fibonacci Heap |
|-----------|------------|----------------|
| Insert | O(log n) | O(1) amortized |
| Extract-min | O(log n) | O(log n) amortized |
| Decrease-key | O(log n) | O(1) amortized |
| Merge | O(n) | O(1) |

**Why it matters**: Dijkstra's algorithm runs in O(V log V + E) with a binary heap but O(V log V + E) with a Fibonacci heap. For dense graphs where E ≈ V², this becomes O(V²) vs O(V² log V).

**Why it's rarely used in practice**: Large constant factors, complex implementation, poor cache locality. The binary heap or 4-ary heap often outperforms it for practical input sizes.

### Binomial Heap

A **binomial heap** is a collection of binomial trees that supports efficient merge operations.

- Merge two binomial heaps: O(log n)
- Insert: O(1) amortized, O(log n) worst case
- Extract-min: O(log n)

It's simpler to implement than a Fibonacci heap and is useful when merging heaps is a frequent operation.

---

## Interview Tips

1. **Recognize heap problems by keywords**: "k-th largest/smallest", "top k", "median of stream", "merge k sorted", "priority", "sliding window maximum".

2. **Two-heap pattern**: When you need to maintain a median or split data into two halves, use a max-heap and min-heap together.

3. **Size-k heap pattern**: For "top k" or "k-th largest" problems, use a heap of size k. Min-heap for k-th largest, max-heap for k-th smallest.

4. **Know your STL**: `priority_queue` doesn't support `decrease-key` directly. If you need it, use a workaround (add duplicate entries and skip stale ones when popping) or implement your own.

5. **Build-heap is O(n)**: This is a favorite interview question. Know the proof.

6. **Heap sort is in-place but unstable**: Mention this tradeoff when comparing sorting algorithms.

7. **Time complexity of heap operations**: Be prepared to explain why insert and extract are O(log n) while peek is O(1).

## Common Mistakes

1. **Wrong comparator direction**: `std::greater<T>` for min-heap, default `std::less<T>` for max-heap. Mixing these up is extremely common.

2. **Off-by-one in parent/child formulas**: Remember: zero-indexed parent = `(i-1)/2`, left child = `2i+1`, right child = `2i+2`.

3. **Forgetting to check empty heap**: Always check before calling `top()` or `pop()`.

4. **Using heap for sorted traversal**: A heap is not a sorted structure. If you need sorted output, use a different data structure or accept O(n log n) extraction.

5. **Assuming heap sort is stable**: It is not. Equal elements may be reordered.

6. **Not knowing that `priority_queue` doesn't support decrease-key**: In Dijkstra's, use the "lazy deletion" approach: push new (better) distances and skip stale entries when popping.

---

## Practice Problems

### Problem 1: Kth Largest Element in an Array (LeetCode 215)
**Difficulty**: Medium
**Hint**: Use a min-heap of size k. Iterate through the array, maintaining only the k largest elements.

### Problem 2: Merge K Sorted Lists (LeetCode 23)
**Difficulty**: Hard
**Hint**: Push the head of each list into a min-heap. Pop the smallest, push its next node. Repeat until the heap is empty.

### Problem 3: Top K Frequent Elements (LeetCode 347)
**Difficulty**: Medium
**Hint**: Count frequencies with a hash map, then use a min-heap of size k to find the k most frequent.

### Problem 4: Find Median from Data Stream (LeetCode 295)
**Difficulty**: Hard
**Hint**: Use two heaps: a max-heap for the lower half and a min-heap for the upper half. Balance their sizes.

### Problem 5: Sliding Window Maximum (LeetCode 239)
**Difficulty**: Hard
**Hint**: Use a max-heap with (value, index) pairs. Pop elements whose index is outside the current window.

### Problem 6: Task Scheduler (LeetCode 621)
**Difficulty**: Medium
**Hint**: Count task frequencies. The most frequent task determines the minimum time. Use a max-heap to greedily schedule the most frequent tasks first.

### Problem 7: Reorganize String (LeetCode 767)
**Difficulty**: Medium
**Hint**: Use a max-heap of (count, char). Greedily pick the most frequent character that isn't the previous one.

### Problem 8: IPO (LeetCode 502)
**Difficulty**: Hard
**Hint**: Sort projects by capital. Use a max-heap for profits of affordable projects. Greedily pick the most profitable project at each step.

---

*Next chapter: [Chapter 16: Trie](ch16-trie.md)*
