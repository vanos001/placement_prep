# Chapter 37: Monotonic Stack

A monotonic stack is one of the most powerful and elegant data structure patterns in competitive programming and technical interviews. It transforms what appears to be an O(n²) problem into O(n) by maintaining a stack whose elements are always sorted. This chapter covers the concept, several classic applications, and the intuition behind each.

---

## 37.1 What Is a Monotonic Stack?

A **monotonic stack** is a stack that maintains its elements in either strictly increasing or strictly decreasing order from bottom to top. Every time we push a new element, we pop elements that violate the monotonic property.

**Monotonic Decreasing Stack** (used to find the next greater element):
- Before pushing `arr[i]`, pop all elements smaller than `arr[i]`.
- After processing, the stack contains elements in decreasing order from bottom to top.

**Monotonic Increasing Stack** (used to find the next smaller element):
- Before pushing `arr[i]`, pop all elements greater than `arr[i]`.

### Why It Works

Each element is pushed once and popped at most once. Even though there's a `while` loop inside the `for` loop, the total number of operations across all iterations is O(n). This amortized O(1) per element is what makes monotonic stack efficient.

**Amortized Analysis:**
- Each element enters the stack exactly once → n pushes total.
- Each element leaves the stack at most once → at most n pops total.
- Total operations: O(2n) = O(n).

---

## 37.2 Next Greater Element

### Problem

Given an array, for each element find the **next element to its right** that is greater than it. If no such element exists, use -1.

**Example:** `arr = [2, 1, 2, 4, 3]` → `nge = [4, 2, 4, -1, -1]`

### Approach: Monotonic Decreasing Stack

Traverse from right to left. Maintain a stack of elements in decreasing order. For each element:
1. Pop all elements from the stack that are ≤ current element.
2. The top of the stack (if exists) is the next greater element.
3. Push the current element.

### Template Code

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> nextGreaterElement(const vector<int>& arr) {
    int n = arr.size();
    vector<int> nge(n, -1);
    stack<int> st;  // stores indices (or values)

    for (int i = n - 1; i >= 0; i--) {
        // Pop elements that are not greater than arr[i]
        while (!st.empty() && st.top() <= arr[i]) {
            st.pop();
        }
        // If stack is not empty, top is the next greater element
        if (!st.empty()) {
            nge[i] = st.top();
        }
        st.push(arr[i]);
    }
    return nge;
}

int main() {
    vector<int> arr = {2, 1, 2, 4, 3};
    vector<int> nge = nextGreaterElement(arr);

    cout << "Array:  ";
    for (int x : arr) cout << x << " ";
    cout << "\nNGE:    ";
    for (int x : nge) cout << x << " ";
    cout << "\n";

    // Output:
    // Array:  2 1 2 4 3
    // NGE:    4 2 4 -1 -1

    return 0;
}
```

### Dry Run

Processing from right to left: `arr = [2, 1, 2, 4, 3]`

| i | arr[i] | Stack (before) | Pops           | nge[i] | Stack (after) |
|---|--------|----------------|----------------|--------|---------------|
| 4 | 3      | []             | none           | -1     | [3]           |
| 3 | 4      | [3]            | pop 3 (3≤4)   | -1     | [4]           |
| 2 | 2      | [4]            | none           | 4      | [4,2]         |
| 1 | 1      | [4,2]          | none           | 2      | [4,2,1]       |
| 0 | 2      | [4,2,1]        | pop 1 (1≤2)   | 4      | [4,2]         |

Result: `[4, 2, 4, -1, -1]` ✓

### Alternative: Index-Based NGE (stores indices)

```cpp
vector<int> nextGreaterElementIndex(const vector<int>& arr) {
    int n = arr.size();
    vector<int> nge(n, -1);
    stack<int> st;  // stores indices

    for (int i = n - 1; i >= 0; i--) {
        while (!st.empty() && arr[st.top()] <= arr[i]) {
            st.pop();
        }
        if (!st.empty()) {
            nge[i] = st.top();
        }
        st.push(i);
    }
    return nge;
}
```

### Variant: Next Greater Element I (LeetCode 496)

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> nextGreaterElement(vector<int>& nums1, vector<int>& nums2) {
    unordered_map<int, int> ngeMap;
    stack<int> st;

    // Build NGE map for nums2
    for (int i = nums2.size() - 1; i >= 0; i--) {
        while (!st.empty() && st.top() <= nums2[i]) {
            st.pop();
        }
        ngeMap[nums2[i]] = st.empty() ? -1 : st.top();
        st.push(nums2[i]);
    }

    // Answer queries for nums1
    vector<int> result;
    for (int num : nums1) {
        result.push_back(ngeMap[num]);
    }
    return result;
}

int main() {
    vector<int> nums1 = {4, 1, 2};
    vector<int> nums2 = {1, 3, 4, 2};
    auto res = nextGreaterElement(nums1, nums2);
    for (int x : res) cout << x << " ";  // Output: -1 3 -1
    cout << "\n";
    return 0;
}
```

**Complexity:** O(n) time, O(n) space.

---

## 37.3 Next Smaller Element

### Problem

For each element, find the next element to its right that is **strictly smaller**.

**Example:** `arr = [2, 1, 2, 4, 3]` → `nse = [1, -1, -1, 3, -1]`

### Approach: Monotonic Increasing Stack

The only difference from NGE: we pop elements that are **≥** current (instead of ≤), giving us a monotonic increasing stack.

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> nextSmallerElement(const vector<int>& arr) {
    int n = arr.size();
    vector<int> nse(n, -1);
    stack<int> st;

    for (int i = n - 1; i >= 0; i--) {
        while (!st.empty() && st.top() >= arr[i]) {
            st.pop();
        }
        if (!st.empty()) {
            nse[i] = st.top();
        }
        st.push(arr[i]);
    }
    return nse;
}

int main() {
    vector<int> arr = {2, 1, 2, 4, 3};
    vector<int> nse = nextSmallerElement(arr);

    cout << "Array:  ";
    for (int x : arr) cout << x << " ";
    cout << "\nNSE:    ";
    for (int x : nse) cout << x << " ";
    cout << "\n";

    // Output:
    // Array:  2 1 2 4 3
    // NSE:    1 -1 -1 3 -1

    return 0;
}
```

### Dry Run

Processing from right to left:

| i | arr[i] | Stack (before) | Pops           | nse[i] | Stack (after) |
|---|--------|----------------|----------------|--------|---------------|
| 4 | 3      | []             | none           | -1     | [3]           |
| 3 | 4      | [3]            | none           | 3      | [3,4]         |
| 2 | 2      | [3,4]          | pop 4 (4≥2), pop 3 (3≥2) | -1 | [2] |
| 1 | 1      | [2]            | pop 2 (2≥1)   | -1     | [1]           |
| 0 | 2      | [1]            | none           | 1      | [1,2]         |

Result: `[1, -1, -1, 3, -1]` ✓

---

## 37.4 Stock Span Problem

### Problem (LeetCode 901)

Design a class that, for each day's stock price, computes the **span**: the number of consecutive days (including today) where the price was ≤ today's price.

**Example:**
```
Prices: [100, 80, 60, 70, 60, 75, 85]
Spans:  [  1,  1,  1,  2,  1,  4,  6]
```

### Approach

Use a monotonic decreasing stack of pairs `(price, span)`. For each new price:
1. Pop all elements with price ≤ current price, accumulating their spans.
2. Push `(currentPrice, accumulatedSpan)`.

```cpp
#include <bits/stdc++.h>
using namespace std;

class StockSpanner {
    stack<pair<int, int>> st;  // {price, span}
public:
    StockSpanner() {}

    int next(int price) {
        int span = 1;
        while (!st.empty() && st.top().first <= price) {
            span += st.top().second;
            st.pop();
        }
        st.push({price, span});
        return span;
    }
};

int main() {
    StockSpanner sp;
    vector<int> prices = {100, 80, 60, 70, 60, 75, 85};

    for (int p : prices) {
        cout << "Price " << p << " -> Span " << sp.next(p) << "\n";
    }
    // Price 100 -> Span 1
    // Price 80  -> Span 1
    // Price 60  -> Span 1
    // Price 70  -> Span 2
    // Price 60  -> Span 1
    // Price 75  -> Span 4
    // Price 85  -> Span 6

    return 0;
}
```

### Dry Run for Price = 75

Stack before: `{(70, 2), (60, 1)}` (bottom to top: `(60,1), (70,2)`)

Wait, let me trace more carefully:

After processing [100, 80, 60, 70, 60]:
- 100: push (100, 1). Stack: [(100,1)]
- 80: 80 ≤ 100? No. Push (80, 1). Stack: [(100,1), (80,1)]
- 60: 60 ≤ 80? No. Push (60, 1). Stack: [(100,1), (80,1), (60,1)]
- 70: pop (60,1), span=2. 70 ≤ 80? No. Push (70, 2). Stack: [(100,1), (80,1), (70,2)]
- 60: 60 ≤ 70? No. Push (60, 1). Stack: [(100,1), (80,1), (70,2), (60,1)]

For 75:
- 75 ≤ 60? No → but wait, we check `st.top().first <= price`, so 60 ≤ 75 → yes, pop. span = 1 + 1 = 2.
- 70 ≤ 75 → yes, pop. span = 2 + 2 = 4.
- 80 ≤ 75? No. Push (75, 4). Return 4.

**Complexity:** Each element pushed and popped at most once → O(n) amortized per `next()` call, O(n) total for n calls.

---

## 37.5 Largest Rectangle in Histogram

### Problem (LeetCode 84)

Given an array of bar heights, find the area of the largest rectangle that fits entirely within the bars.

**Example:** `heights = [2, 1, 5, 6, 2, 3]` → Answer: `10`

### Approach

For each bar, the largest rectangle using that bar's height extends from the **next smaller element on the left** to the **next smaller element on the right**. The width is `(right_smaller_index - left_smaller_index - 1)`.

We compute both boundaries using two passes with a monotonic increasing stack.

```cpp
#include <bits/stdc++.h>
using namespace std;

int largestRectangleArea(vector<int>& heights) {
    int n = heights.size();
    vector<int> left(n), right(n);
    stack<int> st;

    // Find Next Smaller Element on the Left
    for (int i = 0; i < n; i++) {
        while (!st.empty() && heights[st.top()] >= heights[i]) {
            st.pop();
        }
        left[i] = st.empty() ? -1 : st.top();
        st.push(i);
    }

    // Clear stack
    while (!st.empty()) st.pop();

    // Find Next Smaller Element on the Right
    for (int i = n - 1; i >= 0; i--) {
        while (!st.empty() && heights[st.top()] >= heights[i]) {
            st.pop();
        }
        right[i] = st.empty() ? n : st.top();
        st.push(i);
    }

    // Compute max area
    int maxArea = 0;
    for (int i = 0; i < n; i++) {
        int width = right[i] - left[i] - 1;
        maxArea = max(maxArea, heights[i] * width);
    }
    return maxArea;
}

int main() {
    vector<int> heights = {2, 1, 5, 6, 2, 3};
    cout << "Largest rectangle area: " << largestRectangleArea(heights) << "\n";
    // Output: 10

    vector<int> h2 = {2, 4};
    cout << "Largest rectangle area: " << largestRectangleArea(h2) << "\n";
    // Output: 4

    return 0;
}
```

### Dry Run

`heights = [2, 1, 5, 6, 2, 3]`

**Left boundaries** (NSE to the left):

| i | heights[i] | Stack (before) | Pops            | left[i] | Stack (after) |
|---|-----------|----------------|-----------------|---------|---------------|
| 0 | 2         | []             | none            | -1      | [0]           |
| 1 | 1         | [0]            | pop 0 (2≥1)    | -1      | [1]           |
| 2 | 5         | [1]            | none            | 1       | [1,2]         |
| 3 | 6         | [1,2]          | none            | 2       | [1,2,3]       |
| 4 | 2         | [1,2,3]        | pop 3 (6≥2), pop 2 (5≥2) | 1 | [1,4] |
| 5 | 3         | [1,4]          | none            | 4       | [1,4,5]       |

**Right boundaries** (NSE to the right):

| i | heights[i] | right[i] |
|---|-----------|----------|
| 5 | 3         | 6        |
| 4 | 2         | 6        |
| 3 | 6         | 4        |
| 2 | 5         | 4        |
| 1 | 1         | 6        |
| 0 | 2         | 1        |

**Area calculation:**

| i | height | left | right | width | area |
|---|--------|------|-------|-------|------|
| 0 | 2      | -1   | 1     | 1     | 2    |
| 1 | 1      | -1   | 6     | 6     | 6    |
| 2 | 5      | 1    | 4     | 2     | 10   |
| 3 | 6      | 2    | 4     | 1     | 6    |
| 4 | 2      | 1    | 6     | 4     | 8    |
| 5 | 3      | 4    | 6     | 1     | 3    |

**Max area = 10** ✓

**Complexity:** O(n) time, O(n) space.

---

## 37.6 Trapping Rain Water

### Problem (LeetCode 42)

Given an array of bar heights representing an elevation map, compute how much water can be trapped after rain.

**Example:** `height = [0,1,0,2,1,0,1,3,2,1,2,1]` → Answer: `6`

### Approach 1: Monotonic Stack

Use a monotonic decreasing stack. When we encounter a bar taller than the stack top, we can trap water. The water trapped depends on the minimum of the left boundary (next element in stack) and the current bar, minus the popped bar's height.

```cpp
#include <bits/stdc++.h>
using namespace std;

int trap(vector<int>& height) {
    stack<int> st;  // stores indices
    int water = 0;

    for (int i = 0; i < (int)height.size(); i++) {
        while (!st.empty() && height[i] > height[st.top()]) {
            int top = st.top();
            st.pop();
            if (st.empty()) break;

            int left = st.top();
            int width = i - left - 1;
            int boundedHeight = min(height[left], height[i]) - height[top];
            water += width * boundedHeight;
        }
        st.push(i);
    }
    return water;
}

int main() {
    vector<int> height = {0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1};
    cout << "Water trapped: " << trap(height) << "\n";
    // Output: 6

    vector<int> h2 = {4, 2, 0, 3, 2, 5};
    cout << "Water trapped: " << trap(h2) << "\n";
    // Output: 9

    return 0;
}
```

### Dry Run

Processing `height = [0, 1, 0, 2, ...]`:

When `i=3` (height=2), stack = [0,1,2] with heights [0,1,0]:
- Pop index 2 (height 0): left boundary = index 1 (height 1), width = 3-1-1 = 1, bounded_height = min(2,1) - 0 = 1, water += 1
- Pop index 1 (height 1): left boundary = index 0 (height 0), width = 3-0-1 = 2, bounded_height = min(2,0) - 1 = -1 → negative, skip
- Actually height[0]=0 < height[1]=1, so bounded_height = min(2,0)-1 = -1. This is negative, meaning no water trapped here (the left boundary is lower).
- Push 3.

**Complexity:** O(n) time, O(n) space.

### Approach 2: Two Pointers (O(1) space)

```cpp
int trapTwoPointers(vector<int>& height) {
    int n = height.size();
    int left = 0, right = n - 1;
    int leftMax = 0, rightMax = 0;
    int water = 0;

    while (left < right) {
        if (height[left] < height[right]) {
            if (height[left] >= leftMax) {
                leftMax = height[left];
            } else {
                water += leftMax - height[left];
            }
            left++;
        } else {
            if (height[right] >= rightMax) {
                rightMax = height[right];
            } else {
                water += rightMax - height[right];
            }
            right--;
        }
    }
    return water;
}
```

**Complexity:** O(n) time, O(1) space.

---

## 37.7 Monotonic Stack Summary Table

| Problem | Stack Type | Direction | Pop Condition |
|---------|-----------|-----------|---------------|
| Next Greater Element | Decreasing | Right→Left | `st.top() <= arr[i]` |
| Next Smaller Element | Increasing | Right→Left | `st.top() >= arr[i]` |
| Previous Greater Element | Decreasing | Left→Right | `st.top() <= arr[i]` |
| Previous Smaller Element | Increasing | Left→Right | `st.top() >= arr[i]` |

**Key insight:** "Decreasing stack" pops smaller elements, leaving greater ones visible — useful for finding greater elements. "Increasing stack" pops greater elements, leaving smaller ones visible.

---

## 37.8 Interview Tips

1. **Recognize the pattern:** Whenever you need "next greater/smaller" or "previous greater/smaller" for each element, think monotonic stack.

2. **Store indices, not values:** Storing indices lets you compute distances, widths, and access the original array.

3. **Amortized O(n):** Don't be fooled by the nested while loop. Each element is pushed and popped at most once.

4. **Left and right boundaries:** Many problems (histogram, rain water) need both left and right boundaries. You can compute them in two separate passes.

5. **Strict vs non-strict:** Decide whether to use `<=` or `<` in your pop condition based on the problem. For "strictly greater", use `<`; for "greater than or equal", use `<=`.

6. **Circular arrays:** For "next greater element in a circular array", iterate through the array twice (indices `0` to `2n-1`, using `i % n`).

---

## 37.9 Common Mistakes

1. **Wrong comparison direction:** Using `>=` when you need `>`, or forgetting the equal sign. This causes wrong answers or infinite loops.

2. **Forgetting to check `st.empty()`:** Always check if the stack is empty before accessing `st.top()`.

3. **Storing values instead of indices:** When you need the distance to the next greater element, you need the index, not just the value.

4. **Off-by-one in width calculation:** For histogram problems, `width = right[i] - left[i] - 1` (not `right[i] - left[i]`).

5. **Not handling edge cases:** Empty arrays, single elements, all equal elements, strictly increasing/decreasing arrays.

6. **Using the wrong traversal direction:** NGE (right) traverses right-to-left; PGE (previous) traverses left-to-right.

---

## 37.10 Practice Problems

| # | Problem | Difficulty | Key Idea |
|---|---------|------------|----------|
| 1 | LeetCode 496 - Next Greater Element I | Easy | Basic monotonic stack |
| 2 | LeetCode 503 - Next Greater Element II | Medium | Circular array + stack |
| 3 | LeetCode 739 - Daily Temperatures | Medium | NGE with distance |
| 4 | LeetCode 901 - Online Stock Span | Medium | Accumulating spans |
| 5 | LeetCode 84 - Largest Rectangle in Histogram | Hard | Left/right NSE boundaries |
| 6 | LeetCode 42 - Trapping Rain Water | Hard | Monotonic stack or two pointers |
| 7 | LeetCode 316 - Remove Duplicate Letters | Medium | Monotonic stack for lexicographic |
| 8 | LeetCode 402 - Remove K Digits | Medium | Monotonic stack for smallest |
| 9 | LeetCode 1019 - Next Greater Node In Linked List | Medium | Stack + linked list |
| 10 | LeetCode 1944 - Number of Visible People in a Queue | Hard | NGE count |

---

## 37.11 Summary

The monotonic stack is a deceptively simple data structure. By maintaining a sorted stack and leveraging amortized analysis, it solves a family of "next greater/smaller" problems in linear time. The key patterns are:

- **Decreasing stack** → next/previous greater element
- **Increasing stack** → next/previous smaller element
- **Store indices** for distance/width calculations
- **Two passes** when you need both left and right boundaries

Master these patterns and you'll recognize monotonic stack opportunities instantly in interviews.
