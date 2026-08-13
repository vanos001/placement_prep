# Chapter 34: Two Pointers

The two pointers technique is one of the most fundamental and versatile patterns in algorithm design. By maintaining two indices that traverse a data structure (usually an array or string) in a coordinated manner, we can reduce many O(n²) or O(n³) brute-force solutions to O(n) or O(n²). This chapter covers opposite-direction and same-direction pointers, the three-sum pattern, and the classic container/trapping rain water problems. Every example comes with complete, compilable C++17 code.

---

## 34.1 The Two Pointers Technique

### 34.1.1 Why It Works

The core insight: in many problems, when the data is sorted (or has some monotonicity property), moving one pointer gives you information that constrains where the other pointer needs to be. Instead of checking every pair (O(n²)), you can eliminate large portions of the search space with each pointer move.

### 34.1.2 When to Use Two Pointers

- The input is **sorted** (or can be sorted first).
- You need to find **pairs/triplets** satisfying some condition.
- You're working with **subarrays/substrings** and need to optimize a window.
- The problem has a **monotonicity** property: if a pair (i, j) works, then certain pairs with i+1 or j-1 also work (or don't work).

### 34.1.3 General Template

```cpp
// Opposite direction (from both ends)
int left = 0, right = n - 1;
while (left < right) {
    if (conditionMet(arr[left], arr[right])) {
        // process result
        left++;
        right--;
    } else if (needLarger) {
        left++;
    } else {
        right--;
    }
}

// Same direction (fast-slow)
int slow = 0;
for (int fast = 0; fast < n; fast++) {
    if (condition(arr[fast])) {
        // update slow pointer / process
        slow++;
    }
}
```

---

## 34.2 Opposite Direction Pointers

### 34.2.1 Palindrome Check

```cpp
#include <iostream>
#include <string>
using namespace std;

bool isPalindrome(const string& s) {
    int left = 0, right = (int)s.size() - 1;
    while (left < right) {
        if (s[left] != s[right]) return false;
        left++;
        right--;
    }
    return true;
}

int main() {
    cout << boolalpha;
    cout << isPalindrome("racecar") << endl;  // true
    cout << isPalindrome("hello") << endl;    // false
    cout << isPalindrome("a") << endl;        // true
    cout << isPalindrome("") << endl;         // true
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

### 34.2.2 Valid Palindrome II (LeetCode 680)

Allow at most one character deletion.

```cpp
#include <iostream>
#include <string>
using namespace std;

class Solution {
public:
    bool validPalindrome(const string& s) {
        int left = 0, right = (int)s.size() - 1;
        while (left < right) {
            if (s[left] != s[right]) {
                return isPalin(s, left + 1, right) || isPalin(s, left, right - 1);
            }
            left++;
            right--;
        }
        return true;
    }

private:
    bool isPalin(const string& s, int l, int r) {
        while (l < r) {
            if (s[l] != s[r]) return false;
            l++; r--;
        }
        return true;
    }
};

int main() {
    Solution sol;
    cout << boolalpha;
    cout << sol.validPalindrome("aba") << endl;     // true
    cout << sol.validPalindrome("abca") << endl;    // true (remove 'c')
    cout << sol.validPalindrome("abc") << endl;     // false
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

### 34.2.3 Two Sum II — Input Array Is Sorted (LeetCode 167)

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& numbers, int target) {
        int left = 0, right = (int)numbers.size() - 1;
        while (left < right) {
            int sum = numbers[left] + numbers[right];
            if (sum == target) {
                return {left + 1, right + 1};  // 1-indexed
            } else if (sum < target) {
                left++;
            } else {
                right--;
            }
        }
        return {};  // guaranteed to have a solution
    }
};

int main() {
    Solution sol;
    vector<int> nums = {2, 7, 11, 15};
    auto ans = sol.twoSum(nums, 9);
    cout << ans[0] << ", " << ans[1] << endl;  // 1, 2
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

**Dry run with numbers = [2, 7, 11, 15], target = 9:**

```
left=0 (2), right=3 (15): sum=17 > 9 → right--
left=0 (2), right=2 (11): sum=13 > 9 → right--
left=0 (2), right=1 (7): sum=9 == 9 → found! Return [1, 2]
```

Only 3 steps instead of checking all 6 pairs. The sorted property lets us eliminate elements in bulk.

**Why it works:** If `sum < target`, increasing `left` is the only way to get a larger sum (since the array is sorted). If `sum > target`, decreasing `right` is the only way. Each step eliminates one element, so we finish in at most n steps.

### 34.2.4 Container With Most Water (LeetCode 11)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

class Solution {
public:
    int maxArea(vector<int>& height) {
        int left = 0, right = (int)height.size() - 1;
        int maxWater = 0;
        while (left < right) {
            int w = right - left;
            int h = min(height[left], height[right]);
            maxWater = max(maxWater, w * h);
            if (height[left] < height[right]) {
                left++;
            } else {
                right--;
            }
        }
        return maxWater;
    }
};

int main() {
    Solution sol;
    vector<int> h = {1, 8, 6, 2, 5, 4, 8, 3, 7};
    cout << "Max area: " << sol.maxArea(h) << endl;  // 49
    return 0;
}
```

**Dry run:**
```
height = [1, 8, 6, 2, 5, 4, 8, 3, 7]

left=0 (h=1), right=8 (h=7): area = 8*1 = 8.   height[left] < height[right] → left++
left=1 (h=8), right=8 (h=7): area = 7*7 = 49.  height[left] > height[right] → right--
left=1 (h=8), right=7 (h=3): area = 6*3 = 18.  height[left] > height[right] → right--
left=1 (h=8), right=6 (h=8): area = 5*8 = 40.  height[left] == height[right] → right--
left=1 (h=8), right=5 (h=4): area = 4*4 = 16.  height[left] > height[right] → right--
left=1 (h=8), right=4 (h=5): area = 3*5 = 15.  height[left] > height[right] → right--
left=1 (h=8), right=3 (h=2): area = 2*2 = 4.   height[left] > height[right] → right--
left=1 (h=8), right=2 (h=6): area = 1*6 = 6.   left < right → done

Max = 49
```

**Greedy correctness:** Moving the shorter line is the only potentially beneficial move. If we move the taller line, the width decreases and the height can only stay the same or decrease (bounded by the shorter line), so the area cannot increase.

**Complexity:** O(n) time, O(1) space.

---

## 34.3 Same Direction Pointers

### 34.3.1 Fast-Slow Pointers (Floyd's Cycle Detection)

```cpp
#include <iostream>
using namespace std;

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int v) : val(v), next(nullptr) {}
};

class Solution {
public:
    bool hasCycle(ListNode* head) {
        ListNode* slow = head;
        ListNode* fast = head;
        while (fast && fast->next) {
            slow = slow->next;
            fast = fast->next->next;
            if (slow == fast) return true;
        }
        return false;
    }

    ListNode* detectCycleStart(ListNode* head) {
        ListNode* slow = head;
        ListNode* fast = head;
        while (fast && fast->next) {
            slow = slow->next;
            fast = fast->next->next;
            if (slow == fast) {
                // Find the start of the cycle
                slow = head;
                while (slow != fast) {
                    slow = slow->next;
                    fast = fast->next;
                }
                return slow;
            }
        }
        return nullptr;
    }
};

int main() {
    // Create list: 3 -> 2 -> 0 -> -4 -> (back to 2)
    ListNode* head = new ListNode(3);
    head->next = new ListNode(2);
    head->next->next = new ListNode(0);
    head->next->next->next = new ListNode(-4);
    head->next->next->next->next = head->next;  // cycle at node 2

    Solution sol;
    cout << boolalpha;
    cout << "Has cycle: " << sol.hasCycle(head) << endl;

    ListNode* start = sol.detectCycleStart(head);
    if (start) cout << "Cycle starts at: " << start->val << endl;  // 2

    // Cleanup (break cycle first)
    head->next->next->next->next = nullptr;
    while (head) {
        ListNode* tmp = head;
        head = head->next;
        delete tmp;
    }
    return 0;
}
```

**Why Floyd's algorithm works:** The fast pointer gains 1 step per iteration. If there's a cycle of length C, after at most C steps the fast pointer will "lap" the slow pointer. To find the cycle start: when they meet, move one pointer back to the head. Both move at speed 1. They meet at the cycle entrance because the distance from head to cycle start equals the distance from the meeting point to the cycle start (mod C).

**Complexity:** O(n) time, O(1) space.

### 34.3.2 Remove Duplicates from Sorted Array (LeetCode 26)

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    int removeDuplicates(vector<int>& nums) {
        if (nums.empty()) return 0;
        int slow = 0;  // position to write next unique element
        for (int fast = 1; fast < (int)nums.size(); fast++) {
            if (nums[fast] != nums[slow]) {
                slow++;
                nums[slow] = nums[fast];
            }
        }
        return slow + 1;
    }
};

int main() {
    Solution sol;
    vector<int> nums = {0, 0, 1, 1, 1, 2, 2, 3, 3, 4};
    int k = sol.removeDuplicates(nums);
    cout << "k = " << k << ", nums = [";
    for (int i = 0; i < k; i++) {
        if (i) cout << ", ";
        cout << nums[i];
    }
    cout << "]" << endl;  // k=5, nums=[0, 1, 2, 3, 4]
    return 0;
}
```

**Dry run with nums = [0, 0, 1, 1, 1, 2, 2, 3, 3, 4]:**

```
slow=0, fast scans from 1 to 9

fast=1: nums[1]=0, nums[slow]=0 → same, skip
fast=2: nums[2]=1, nums[slow]=0 → different!
  slow=1, nums[1] = 1  → array: [0, 1, 1, 1, 1, 2, 2, 3, 3, 4]
fast=3: nums[3]=1, nums[slow]=1 → same, skip
fast=4: nums[4]=1, nums[slow]=1 → same, skip
fast=5: nums[5]=2, nums[slow]=1 → different!
  slow=2, nums[2] = 2  → array: [0, 1, 2, 1, 1, 2, 2, 3, 3, 4]
fast=6: nums[6]=2, nums[slow]=2 → same, skip
fast=7: nums[7]=3, nums[slow]=2 → different!
  slow=3, nums[3] = 3  → array: [0, 1, 2, 3, 1, 2, 2, 3, 3, 4]
fast=8: nums[8]=3, nums[slow]=3 → same, skip
fast=9: nums[9]=4, nums[slow]=3 → different!
  slow=4, nums[4] = 4  → array: [0, 1, 2, 3, 4, 2, 2, 3, 3, 4]

Result: k = slow + 1 = 5, unique elements = [0, 1, 2, 3, 4]
```

The slow pointer tracks where to write the next unique element. The fast pointer scans ahead to find new values. Each element is written at most once → O(n).

**Complexity:** O(n) time, O(1) space.

### 34.3.3 Merge Two Sorted Arrays (in-place, from the end)

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    void merge(vector<int>& nums1, int m, vector<int>& nums2, int n) {
        int i = m - 1;       // last element of nums1's valid part
        int j = n - 1;       // last element of nums2
        int k = m + n - 1;   // last position of nums1

        while (i >= 0 && j >= 0) {
            if (nums1[i] > nums2[j]) {
                nums1[k--] = nums1[i--];
            } else {
                nums1[k--] = nums2[j--];
            }
        }
        while (j >= 0) {
            nums1[k--] = nums2[j--];
        }
        // If i >= 0, elements are already in place
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {1, 2, 3, 0, 0, 0};
    vector<int> nums2 = {2, 5, 6};
    sol.merge(nums1, 3, nums2, 3);
    for (int x : nums1) cout << x << " ";
    cout << endl;  // 1 2 2 3 5 6
    return 0;
}
```

**Dry run with nums1 = [1, 2, 3, 0, 0, 0] (m=3), nums2 = [2, 5, 6] (n=3):**

```
Start: i=2 (nums1[2]=3), j=2 (nums2[2]=6), k=5

Step 1: nums1[2]=3 vs nums2[2]=6 → 6 is larger
  nums1[5] = 6, j=1, k=4  → [1, 2, 3, 0, 0, 6]

Step 2: nums1[2]=3 vs nums2[1]=5 → 5 is larger
  nums1[4] = 5, j=0, k=3  → [1, 2, 3, 0, 5, 6]

Step 3: nums1[2]=3 vs nums2[0]=2 → 3 is larger
  nums1[3] = 3, i=1, k=2  → [1, 2, 3, 3, 5, 6]

Step 4: nums1[1]=2 vs nums2[0]=2 → equal, take nums2 (or nums1, either works)
  nums1[2] = 2, j=-1, k=1  → [1, 2, 2, 3, 5, 6]

Step 5: j < 0, copy remaining nums1 elements (already in place)

Result: [1, 2, 2, 3, 5, 6] ✓
```

**Why merge from the end?** If we merged from the front, we'd overwrite elements in nums1 that haven't been processed yet. Merging from the back fills the empty space at the end of nums1 first, never overwriting unprocessed data.

**Complexity:** O(m + n) time, O(1) space.

---

## 34.4 Three Pointers / Three Sum

### 34.4.1 3Sum (LeetCode 15)

Find all unique triplets that sum to zero.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

class Solution {
public:
    vector<vector<int>> threeSum(vector<int>& nums) {
        vector<vector<int>> result;
        sort(nums.begin(), nums.end());
        int n = nums.size();

        for (int i = 0; i < n - 2; i++) {
            // Skip duplicate for first element
            if (i > 0 && nums[i] == nums[i - 1]) continue;

            // Optimization: if smallest triplet > 0, no solution
            if (nums[i] > 0) break;

            int left = i + 1, right = n - 1;
            int target = -nums[i];

            while (left < right) {
                int sum = nums[left] + nums[right];
                if (sum == target) {
                    result.push_back({nums[i], nums[left], nums[right]});
                    // Skip duplicates for second and third elements
                    while (left < right && nums[left] == nums[left + 1]) left++;
                    while (left < right && nums[right] == nums[right - 1]) right--;
                    left++;
                    right--;
                } else if (sum < target) {
                    left++;
                } else {
                    right--;
                }
            }
        }
        return result;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {-1, 0, 1, 2, -1, -4};
    auto ans = sol.threeSum(nums1);
    for (auto& triplet : ans) {
        cout << "[" << triplet[0] << "," << triplet[1] << "," << triplet[2] << "] ";
    }
    cout << endl;  // [-1,-1,2] [-1,0,1]

    vector<int> nums2 = {0, 0, 0};
    auto ans2 = sol.threeSum(nums2);
    for (auto& triplet : ans2) {
        cout << "[" << triplet[0] << "," << triplet[1] << "," << triplet[2] << "] ";
    }
    cout << endl;  // [0,0,0]
    return 0;
}
```

**Dry run with nums = [-1, 0, 1, 2, -1, -4]:**

After sorting: [-4, -1, -1, 0, 1, 2]

```
i=0, nums[i]=-4, target=4
  left=1, right=5: sum=-1+2=1 < 4 → left++
  left=2, right=5: sum=-1+2=1 < 4 → left++
  left=3, right=5: sum=0+2=2 < 4 → left++
  left=4, right=5: sum=1+2=3 < 4 → left++
  left=5, right=5: done

i=1, nums[i]=-1, target=1
  left=2, right=5: sum=-1+2=1 == 1 → found [-1,-1,2]
    skip duplicates, left=3, right=4
  left=3, right=4: sum=0+1=1 == 1 → found [-1,0,1]
    left=4, right=3: done

i=2, nums[i]=-1, same as nums[1] → skip (duplicate)

i=3, nums[i]=0 > 0? No. But i=3, n-2=4, so we continue.
  left=4, right=5: sum=1+2=3 > 0 → right--
  left=4, right=4: done
```

**Complexity:** O(n²) time (sort O(n log n) + n iterations × O(n) two-pointer), O(1) space (excluding output).

### 34.4.2 Handling Duplicates — The Key Pattern

The duplicate-skipping pattern is critical in many two-pointer problems:

```cpp
// After finding a valid pair/triplet:
while (left < right && nums[left] == nums[left + 1]) left++;
while (left < right && nums[right] == nums[right - 1]) right--;
left++; right--;  // move past the last duplicate
```

This ensures we don't count the same combination twice.

---

## 34.5 Container Problems

### 34.5.1 Trapping Rain Water (LeetCode 42)

Given an elevation map, compute how much water it can trap after rain.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

class Solution {
public:
    // Approach 1: Two pointers (optimal)
    int trap(vector<int>& height) {
        int n = height.size();
        if (n <= 2) return 0;

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

    // Approach 2: Precompute leftMax and rightMax arrays
    int trapDP(vector<int>& height) {
        int n = height.size();
        if (n <= 2) return 0;

        vector<int> leftMax(n), rightMax(n);
        leftMax[0] = height[0];
        for (int i = 1; i < n; i++)
            leftMax[i] = max(leftMax[i - 1], height[i]);

        rightMax[n - 1] = height[n - 1];
        for (int i = n - 2; i >= 0; i--)
            rightMax[i] = max(rightMax[i + 1], height[i]);

        int water = 0;
        for (int i = 0; i < n; i++) {
            water += min(leftMax[i], rightMax[i]) - height[i];
        }
        return water;
    }
};

int main() {
    Solution sol;
    vector<int> h1 = {0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1};
    cout << "Water trapped: " << sol.trap(h1) << endl;     // 6
    cout << "Water (DP):    " << sol.trapDP(h1) << endl;   // 6

    vector<int> h2 = {4, 2, 0, 3, 2, 5};
    cout << "Water trapped: " << sol.trap(h2) << endl;     // 9
    return 0;
}
```

**Dry run with height = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]:**

Using the two-pointer approach:

```
Initial: left=0, right=11, leftMax=0, rightMax=0, water=0

left=0 (h=0): h[left] < h[right] (0<1)
  0 >= leftMax(0)? yes → leftMax=0
  left=1

left=1 (h=1): h[left] < h[right] (1<1)? no, equal → go right
  Actually h[left] >= h[right], so process right:
  right=11 (h=1): 1 >= rightMax(0)? yes → rightMax=1
  right=10

left=1 (h=1): h[left] < h[right] (1<2)? yes
  1 >= leftMax(0)? yes → leftMax=1
  left=2

left=2 (h=0): h[left] < h[right] (0<2)? yes
  0 >= leftMax(1)? no → water += 1-0 = 1, water=1
  left=3

left=3 (h=2): h[left] < h[right] (2<2)? no, equal → right
  right=10 (h=2): 2 >= rightMax(1)? yes → rightMax=2
  right=9

left=3 (h=2): h[left] < h[right] (2<1)? no → right
  right=9 (h=1): 1 >= rightMax(2)? no → water += 2-1 = 1, water=2
  right=8

... continuing this process yields water = 6
```

**Why the two-pointer approach works:** At each step, we process the side with the smaller height. The key insight is that the water at any position is bounded by `min(leftMaxFromLeft, rightMaxFromRight)`. When `height[left] < height[right]`, we know `rightMax` is at least `height[right]`, so the water level at `left` is determined by `leftMax`. This lets us correctly compute water without precomputing both arrays.

**Complexity:**
- Two-pointer: O(n) time, O(1) space.
- DP approach: O(n) time, O(n) space.

---

## Interview Tips

1. **Sort first if possible.** Many two-pointer problems require sorted input. If the original order doesn't matter, sort first (O(n log n)) and then apply two pointers (O(n)).
2. **Know the three main patterns:** opposite-direction, same-direction (fast-slow), and three-pointer (fix one + two-pointer on the rest).
3. **Duplicate handling is critical.** In problems like 3Sum, always think about how to skip duplicates to avoid duplicate results.
4. **Two pointers ≠ sliding window.** Two pointers is the broader technique. Sliding window is a specific sub-pattern where both pointers move in the same direction and the "window" between them is the focus.
5. **Greedy moves in opposite-direction.** Be prepared to prove why moving the pointer with the smaller/larger value is correct (e.g., Container With Most Water).

## Common Mistakes

- **Off-by-one errors.** Be careful with `left < right` vs `left <= right` — the choice depends on whether you want to allow the same element twice.
- **Forgetting to skip duplicates.** In 3Sum, if you don't skip duplicates at the right places, you'll get duplicate triplets.
- **Integer overflow.** In Container With Most Water, `width * height` can overflow `int`. Use `long long` if needed.
- **Not handling empty input.** Always check for empty arrays before accessing `nums[0]` or `nums.back()`.
- **Confusing indices and values.** In Two Sum II, the problem asks for 1-indexed positions. Don't forget to add 1.

## Practice Problems

1. **3Sum Closest** (LeetCode 16) — Find the triplet with sum closest to target. *Hint: Sort, fix one element, use two pointers. Track the closest sum.*
2. **4Sum** (LeetCode 18) — Find all unique quadruplets summing to target. *Hint: Sort, fix two elements, then two-pointer on the rest. O(n³).*
3. **Sort Colors** (LeetCode 75) — Dutch National Flag problem. *Hint: Three pointers — low, mid, high. Swap 0s to front, 2s to back.*
4. **Move Zeroes** (LeetCode 283) — Move all zeros to end while maintaining order. *Hint: Slow pointer tracks write position, fast pointer scans.*
5. **Remove Element** (LeetCode 27) — Remove all instances of a value in-place. *Hint: Same pattern as Remove Duplicates — slow tracks write position.*

---

## See Also

- [Chapter 5: Sorting](ch05-sorting.md) — Two pointers often require sorted input; sorting is the natural first step.
- [Chapter 6: Searching](ch06-searching.md) — Binary search and two pointers are complementary techniques for sorted data.
- [Chapter 35: Sliding Window](ch35-sliding-window.md) — A related technique for subarray problems; sliding window handles fixed-size windows, two pointers handles variable-size.
- [Chapter 36: Prefix Sum and Difference Array](ch36-prefix-sum-diff-array.md) — Prefix sums combined with two pointers enable subarray sum queries.
- [Chapter 37: Monotonic Stack](ch37-monotonic-stack.md) — Another linear-time technique for array problems; often used alongside two pointers.
- [Chapter 131: Parallel Binary Search](ch131-parallel-binary-search.md) — When binary search on answer is needed for multiple queries, parallel binary search combines with two-pointer-like techniques.
