# Chapter 35: Sliding Window

Sliding window is a specialized form of the two pointers technique where both pointers move in the same direction and the region between them forms a "window." It is the go-to pattern for problems involving contiguous subarrays or substrings. This chapter covers fixed-size windows, variable-size windows, windows combined with hash maps, monotonic windows, and ends with classic interview problems. All code is complete and compilable in C++17.

---

## 35.1 Fixed-Size Window

### 35.1.1 The Template

A fixed-size window maintains a window of exactly size `k` as it slides from left to right.

```cpp
// Fixed-size window template
int fixedWindow(const vector<int>& arr, int k) {
    int n = arr.size();
    // Step 1: Build the first window
    int windowValue = 0;
    for (int i = 0; i < k; i++) {
        windowValue += arr[i];  // or whatever aggregation
    }
    int result = windowValue;

    // Step 2: Slide the window
    for (int i = k; i < n; i++) {
        windowValue += arr[i];       // add new element (enter window)
        windowValue -= arr[i - k];   // remove old element (leave window)
        result = max(result, windowValue);  // or min, or whatever
    }
    return result;
}
```

**Key insight:** Instead of recomputing from scratch for each window position (O(k) per slide), we update incrementally in O(1) by adding the entering element and removing the leaving element.

### 35.1.2 Maximum Average Subarray I (LeetCode 643)

```cpp
#include <iostream>
#include <vector>
#include <iomanip>
using namespace std;

class Solution {
public:
    double findMaxAverage(vector<int>& nums, int k) {
        double windowSum = 0;
        for (int i = 0; i < k; i++) {
            windowSum += nums[i];
        }
        double maxSum = windowSum;

        for (int i = k; i < (int)nums.size(); i++) {
            windowSum += nums[i] - nums[i - k];
            maxSum = max(maxSum, windowSum);
        }
        return maxSum / k;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {1, 12, -5, -6, 50, 3};
    cout << fixed << setprecision(5);
    cout << sol.findMaxAverage(nums1, 4) << endl;  // 12.75000

    vector<int> nums2 = {5};
    cout << sol.findMaxAverage(nums2, 1) << endl;  // 5.00000
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

### 35.1.3 Maximum/Minimum in a Window of Size K

Finding the maximum in each window of size k requires a **monotonic deque** to achieve O(n).

```cpp
#include <iostream>
#include <vector>
#include <deque>
using namespace std;

class Solution {
public:
    vector<int> maxSlidingWindow(vector<int>& nums, int k) {
        deque<int> dq;  // stores indices, front is always the max
        vector<int> result;

        for (int i = 0; i < (int)nums.size(); i++) {
            // Remove indices that are out of the current window
            while (!dq.empty() && dq.front() <= i - k) {
                dq.pop_front();
            }
            // Remove all elements smaller than current from the back
            while (!dq.empty() && nums[dq.back()] <= nums[i]) {
                dq.pop_back();
            }
            dq.push_back(i);

            if (i >= k - 1) {
                result.push_back(nums[dq.front()]);
            }
        }
        return result;
    }
};

int main() {
    Solution sol;
    vector<int> nums = {1, 3, -1, -3, 5, 3, 6, 7};
    auto ans = sol.maxSlidingWindow(nums, 3);
    for (int x : ans) cout << x << " ";
    cout << endl;  // 3 3 5 5 6 7
    return 0;
}
```

**Dry run with nums = [1, 3, -1, -3, 5, 3, 6, 7], k = 3:**

```
i=0: dq=[0] (val=1)
i=1: remove back(0) since 1<=3 → dq=[1] (val=3)
i=2: dq=[1,2] (val=3,-1). i>=2 → output dq.front()=3
i=3: remove front(1) since 1<=3-3=0 → dq=[2,3] (val=-1,-3). i>=2 → output -1? No, dq.front()=2, nums[2]=-1.
     Wait, let me recheck: i=3, i-k=0. dq.front()=1, 1<=0? No. So dq=[1,2,3].
     nums[3]=-3 <= nums[2]=-1? No, -3 < -1, so we pop back 2? nums[dq.back()]=nums[2]=-1, -1 <= -3? No.
     So dq=[1,2,3]. Output nums[1]=3.
i=4: i-k=1. dq.front()=1, 1<=1? Yes, pop front. dq=[2,3].
     nums[4]=5. Pop back: nums[3]=-3 <=5, pop. nums[2]=-1 <=5, pop. dq=[4]. Output 5.
i=5: i-k=2. dq.front()=4, 4<=2? No. nums[5]=3, nums[4]=5, 5<=3? No. dq=[4,5]. Output 5.
i=6: i-k=3. dq.front()=4, 4<=3? No. nums[6]=6, pop 5 (3<=6), pop 4 (5<=6). dq=[6]. Output 6.
i=7: i-k=4. dq.front()=6, 6<=4? No. nums[7]=7, pop 6 (6<=7). dq=[7]. Output 7.

Result: [3, 3, 5, 5, 6, 7] ✓
```

**Complexity:** O(n) time — each element is pushed and popped at most once. O(k) space for the deque.

---

## 35.2 Variable-Size Window

### 35.2.1 Expand-Shrink Template

The variable-size window grows from the right and shrinks from the left until a constraint is satisfied.

```cpp
// Variable-size window template
int variableWindow(const vector<int>& arr, int target) {
    int n = arr.size();
    int left = 0;
    int windowSum = 0;
    int result = 0;  // or INT_MAX, depending on the problem

    for (int right = 0; right < n; right++) {
        // Expand: include arr[right] in the window
        windowSum += arr[right];

        // Shrink: while the window is invalid, move left
        while (windowSum > target) {  // condition depends on problem
            windowSum -= arr[left];
            left++;
        }

        // Update result with current valid window
        result = max(result, right - left + 1);
    }
    return result;
}
```

### 35.2.2 Longest Substring Without Repeating Characters (LeetCode 3)

```cpp
#include <iostream>
#include <string>
#include <unordered_set>
#include <algorithm>
using namespace std;

class Solution {
public:
    // Approach 1: HashSet
    int lengthOfLongestSubstring(string s) {
        unordered_set<char> seen;
        int left = 0, maxLen = 0;

        for (int right = 0; right < (int)s.size(); right++) {
            while (seen.count(s[right])) {
                seen.erase(s[left]);
                left++;
            }
            seen.insert(s[right]);
            maxLen = max(maxLen, right - left + 1);
        }
        return maxLen;
    }

    // Approach 2: HashMap with direct jump (optimized)
    int lengthOfLongestSubstringOpt(string s) {
        unordered_map<char, int> lastSeen;  // char → last index
        int left = 0, maxLen = 0;

        for (int right = 0; right < (int)s.size(); right++) {
            if (lastSeen.count(s[right]) && lastSeen[s[right]] >= left) {
                left = lastSeen[s[right]] + 1;
            }
            lastSeen[s[right]] = right;
            maxLen = max(maxLen, right - left + 1);
        }
        return maxLen;
    }
};

int main() {
    Solution sol;
    cout << sol.lengthOfLongestSubstring("abcabcbb") << endl;  // 3
    cout << sol.lengthOfLongestSubstring("bbbbb") << endl;     // 1
    cout << sol.lengthOfLongestSubstring("pwwkew") << endl;    // 3
    cout << sol.lengthOfLongestSubstring("") << endl;          // 0
    cout << sol.lengthOfLongestSubstring("au") << endl;        // 2
    return 0;
}
```

**Dry run with s = "abcabcbb":**

Using the optimized approach:

```
right=0, s[0]='a': not in lastSeen. lastSeen={a:0}. window=[0,0], len=1
right=1, s[1]='b': not in lastSeen. lastSeen={a:0,b:1}. window=[0,1], len=2
right=2, s[2]='c': not in lastSeen. lastSeen={a:0,b:1,c:2}. window=[0,2], len=3
right=3, s[3]='a': lastSeen[a]=0 >= left=0 → left=1. lastSeen={a:3,b:1,c:2}. window=[1,3], len=3
right=4, s[4]='b': lastSeen[b]=1 >= left=1 → left=2. lastSeen={a:3,b:4,c:2}. window=[2,4], len=3
right=5, s[5]='c': lastSeen[c]=2 >= left=2 → left=3. lastSeen={a:3,b:4,c:5}. window=[3,5], len=3
right=6, s[6]='b': lastSeen[b]=4 >= left=3 → left=5. lastSeen={a:3,b:6,c:5}. window=[5,6], len=2
right=7, s[7]='b': lastSeen[b]=6 >= left=5 → left=7. lastSeen={a:3,b:7,c:5}. window=[7,7], len=1

Max = 3
```

**Complexity:** Both approaches are O(n) time. The optimized approach is O(min(n, m)) space where m is the character set size.

### 35.2.3 Minimum Size Subarray Sum (LeetCode 209)

Find the minimal length of a contiguous subarray with sum ≥ target.

```cpp
#include <iostream>
#include <vector>
#include <climits>
using namespace std;

class Solution {
public:
    int minSubArrayLen(int target, vector<int>& nums) {
        int left = 0;
        int windowSum = 0;
        int minLen = INT_MAX;

        for (int right = 0; right < (int)nums.size(); right++) {
            windowSum += nums[right];

            while (windowSum >= target) {
                minLen = min(minLen, right - left + 1);
                windowSum -= nums[left];
                left++;
            }
        }
        return minLen == INT_MAX ? 0 : minLen;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {2, 3, 1, 2, 4, 3};
    cout << sol.minSubArrayLen(7, nums1) << endl;  // 2 (subarray [4,3])

    vector<int> nums2 = {1, 4, 4};
    cout << sol.minSubArrayLen(4, nums2) << endl;  // 1

    vector<int> nums3 = {1, 1, 1, 1, 1, 1, 1, 1};
    cout << sol.minSubArrayLen(11, nums3) << endl; // 0
    return 0;
}
```

**Complexity:** O(n) time, O(1) space. Each element is added and removed from the window at most once.

---

## 35.3 Window with HashMap

### 35.3.1 Character Frequency in a Window

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
using namespace std;

void printWindowFrequencies(const string& s, int k) {
    unordered_map<char, int> freq;
    // Build first window
    for (int i = 0; i < k; i++) freq[s[i]]++;
    cout << "Window [0," << k-1 << "]: ";
    for (auto& [ch, cnt] : freq) cout << ch << ":" << cnt << " ";
    cout << endl;

    // Slide
    for (int i = k; i < (int)s.size(); i++) {
        freq[s[i]]++;
        freq[s[i - k]]--;
        if (freq[s[i - k]] == 0) freq.erase(s[i - k]);
        cout << "Window [" << i-k+1 << "," << i << "]: ";
        for (auto& [ch, cnt] : freq) cout << ch << ":" << cnt << " ";
        cout << endl;
    }
}

int main() {
    printWindowFrequencies("abcabc", 3);
    return 0;
}
```

### 35.3.2 Find All Anagrams in a String (LeetCode 438)

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <array>
using namespace std;

class Solution {
public:
    vector<int> findAnagrams(string s, string p) {
        vector<int> result;
        if (s.size() < p.size()) return result;

        array<int, 26> pCount{}, sCount{};
        for (char c : p) pCount[c - 'a']++;

        int k = p.size();
        for (int i = 0; i < (int)s.size(); i++) {
            sCount[s[i] - 'a']++;

            if (i >= k) {
                sCount[s[i - k] - 'a']--;
            }

            if (i >= k - 1 && sCount == pCount) {
                result.push_back(i - k + 1);
            }
        }
        return result;
    }
};

int main() {
    Solution sol;
    auto ans = sol.findAnagrams("cbaebabacd", "abc");
    for (int x : ans) cout << x << " ";
    cout << endl;  // 0 6

    auto ans2 = sol.findAnagrams("abab", "ab");
    for (int x : ans2) cout << x << " ";
    cout << endl;  // 0 1 2
    return 0;
}
```

**Complexity:** O(n) time — each character is processed once, and array comparison is O(26) = O(1). O(1) space (fixed-size arrays).

### 35.3.3 Minimum Window Substring (LeetCode 76)

Given strings `s` and `t`, find the minimum window in `s` that contains all characters of `t`.

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <climits>
using namespace std;

class Solution {
public:
    string minWindow(string s, string t) {
        if (s.size() < t.size()) return "";

        unordered_map<char, int> need, have;
        for (char c : t) need[c]++;

        int required = need.size();  // number of distinct chars needed
        int formed = 0;              // number of distinct chars satisfied
        int left = 0;
        int minLen = INT_MAX, minStart = 0;

        for (int right = 0; right < (int)s.size(); right++) {
            char c = s[right];
            have[c]++;

            if (need.count(c) && have[c] == need[c]) {
                formed++;
            }

            // Shrink while window is valid
            while (formed == required) {
                if (right - left + 1 < minLen) {
                    minLen = right - left + 1;
                    minStart = left;
                }
                char lc = s[left];
                have[lc]--;
                if (need.count(lc) && have[lc] < need[lc]) {
                    formed--;
                }
                left++;
            }
        }

        return minLen == INT_MAX ? "" : s.substr(minStart, minLen);
    }
};

int main() {
    Solution sol;
    cout << sol.minWindow("ADOBECODEBANC", "ABC") << endl;  // "BANC"
    cout << sol.minWindow("a", "a") << endl;                // "a"
    cout << sol.minWindow("a", "aa") << endl;               // ""
    return 0;
}
```

**Dry run with s = "ADOBECODEBANC", t = "ABC":**

```
need = {A:1, B:1, C:1}, required = 3

right=0 'A': have={A:1}. formed=1 (A satisfied). Not all formed.
right=1 'D': have={A:1,D:1}. Not in need.
right=2 'O': have={A:1,D:1,O:1}. Not in need.
right=3 'B': have={A:1,D:1,O:1,B:1}. formed=2 (B satisfied).
right=4 'E': have={A:1,D:1,O:1,B:1,E:1}.
right=5 'C': have={A:1,B:1,C:1,D:1,E:1,O:1}. formed=3 (C satisfied).
  All formed! Window [0,5] = "ADOBEC", len=6. minLen=6, minStart=0.
  Shrink: remove 'A' (left=0). have[A]=0 < need[A]=1 → formed=2. left=1.
  Not all formed. Continue.

right=6 'O': have update. Not all formed.
right=7 'D': Not all formed.
right=8 'E': Not all formed.
right=9 'B': have[B]=2. Already formed.
right=10 'A': have[A]=1 == need[A]. formed=3.
  All formed! Window [1,10] = "DOBECODEBA", len=10. 10 >= 6, no update.
  Shrink: remove 'D' (left=1). Not in need. left=2.
  Still formed. Window [2,10] len=9. No update.
  Shrink: remove 'O' (left=2). Not in need. left=3.
  Still formed. Window [3,10] len=8. No update.
  Shrink: remove 'B' (left=3). have[B]=1 == need[B]=1. Still formed. left=4.
  Window [4,10] len=7. No update.
  Shrink: remove 'E' (left=4). Not in need. left=5.
  Still formed. Window [5,10] len=6. No update.
  Shrink: remove 'C' (left=5). have[C]=0 < need[C]=1 → formed=2. left=6.
  Not all formed. Continue.

right=11 'N': Not all formed.
right=12 'C': have[C]=1 == need[C]=1. formed=3.
  All formed! Window [6,12] = "ODEBANC", len=7. No update.
  Shrink: remove 'O' (left=6). Not in need. left=7.
  Still formed. Window [7,12] len=6. No update.
  Shrink: remove 'D' (left=7). Not in need. left=8.
  Still formed. Window [8,12] = "EBANC", len=5. Update! minLen=5, minStart=8.
  Shrink: remove 'E' (left=8). Not in need. left=9.
  Still formed. Window [9,12] = "BANC", len=4. Update! minLen=4, minStart=9.
  Shrink: remove 'B' (left=9). have[B]=0 < need[B]=1 → formed=2. left=10.
  Not all formed. Done.

Result: s.substr(9, 4) = "BANC"
```

**Complexity:** O(|s| + |t|) time, O(|s| + |t|) space.

---

## 35.4 Monotonic Window

A monotonic window uses a deque to maintain a monotonic property (increasing or decreasing) within the window. We already saw this in the maximum sliding window problem (Section 35.1.3).

### 35.4.1 Sliding Window Maximum — Alternative Implementation

```cpp
#include <iostream>
#include <vector>
#include <deque>
using namespace std;

vector<int> maxSlidingWindow(const vector<int>& nums, int k) {
    deque<int> dq;  // monotonic decreasing deque (stores indices)
    vector<int> result;

    for (int i = 0; i < (int)nums.size(); i++) {
        // 1. Remove elements outside the window
        while (!dq.empty() && dq.front() < i - k + 1) {
            dq.pop_front();
        }
        // 2. Maintain monotonicity (decreasing)
        while (!dq.empty() && nums[dq.back()] < nums[i]) {
            dq.pop_back();
        }
        // 3. Add current element
        dq.push_back(i);

        // 4. Record result once window is fully formed
        if (i >= k - 1) {
            result.push_back(nums[dq.front()]);
        }
    }
    return result;
}

int main() {
    vector<int> nums = {1, 3, -1, -3, 5, 3, 6, 7};
    auto ans = maxSlidingWindow(nums, 3);
    for (int x : ans) cout << x << " ";
    cout << endl;  // 3 3 5 5 6 7

    vector<int> nums2 = {9, 11};
    auto ans2 = maxSlidingWindow(nums2, 2);
    for (int x : ans2) cout << x << " ";
    cout << endl;  // 11
    return 0;
}
```

### 35.4.2 Longest Continuous Subarray With Absolute Diff ≤ Limit (LeetCode 1438)

```cpp
#include <iostream>
#include <vector>
#include <deque>
#include <algorithm>
using namespace std;

class Solution {
public:
    int longestSubarray(vector<int>& nums, int limit) {
        deque<int> maxDQ, minDQ;  // monotonic decreasing and increasing
        int left = 0, maxLen = 0;

        for (int right = 0; right < (int)nums.size(); right++) {
            // Maintain decreasing deque for max
            while (!maxDQ.empty() && nums[maxDQ.back()] <= nums[right])
                maxDQ.pop_back();
            maxDQ.push_back(right);

            // Maintain increasing deque for min
            while (!minDQ.empty() && nums[minDQ.back()] >= nums[right])
                minDQ.pop_back();
            minDQ.push_back(right);

            // Shrink if diff exceeds limit
            while (nums[maxDQ.front()] - nums[minDQ.front()] > limit) {
                if (maxDQ.front() == left) maxDQ.pop_front();
                if (minDQ.front() == left) minDQ.pop_front();
                left++;
            }

            maxLen = max(maxLen, right - left + 1);
        }
        return maxLen;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {8, 2, 4, 7};
    cout << sol.longestSubarray(nums1, 4) << endl;  // 2

    vector<int> nums2 = {10, 1, 2, 4, 7, 2};
    cout << sol.longestSubarray(nums2, 5) << endl;  // 4

    vector<int> nums3 = {4, 2, 2, 2, 4, 4, 2, 2};
    cout << sol.longestSubarray(nums3, 0) << endl;  // 3
    return 0;
}
```

**Complexity:** O(n) time — each element enters and exits each deque at most once. O(k) space.

---

## 35.5 Applications

### 35.5.1 Grumpy Bookstore Owner (LeetCode 1052)

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    int maxSatisfied(vector<int>& customers, vector<int>& grumpy, int minutes) {
        int n = customers.size();
        // Base satisfaction (when owner is not grumpy)
        int baseSat = 0;
        for (int i = 0; i < n; i++) {
            if (!grumpy[i]) baseSat += customers[i];
        }

        // Find max additional satisfaction from the technique window
        int additional = 0, maxAdditional = 0;
        for (int i = 0; i < n; i++) {
            if (grumpy[i]) additional += customers[i];
            if (i >= minutes) {
                if (grumpy[i - minutes]) additional -= customers[i - minutes];
            }
            maxAdditional = max(maxAdditional, additional);
        }
        return baseSat + maxAdditional;
    }
};

int main() {
    Solution sol;
    vector<int> cust = {1, 0, 1, 2, 1, 1, 7, 5};
    vector<int> grumpy = {0, 1, 0, 1, 0, 1, 0, 1};
    cout << sol.maxSatisfied(cust, grumpy, 3) << endl;  // 16
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

### 35.5.2 Subarray Product Less Than K (LeetCode 713)

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    int numSubarrayProductLessThanK(vector<int>& nums, int k) {
        if (k <= 1) return 0;

        int left = 0;
        long long product = 1;
        int count = 0;

        for (int right = 0; right < (int)nums.size(); right++) {
            product *= nums[right];

            while (product >= k) {
                product /= nums[left];
                left++;
            }

            // All subarrays ending at 'right' and starting from left..right are valid
            count += right - left + 1;
        }
        return count;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {10, 5, 2, 6};
    cout << sol.numSubarrayProductLessThanK(nums1, 100) << endl;  // 8

    vector<int> nums2 = {1, 2, 3};
    cout << sol.numSubarrayProductLessThanK(nums2, 0) << endl;   // 0
    return 0;
}
```

**Why `count += right - left + 1`:** When the window `[left, right]` is valid, every subarray ending at `right` and starting at any index from `left` to `right` is also valid (since removing elements from the left can only decrease the product). That's `right - left + 1` subarrays.

**Complexity:** O(n) time, O(1) space.

---

## Interview Tips

1. **Identify the pattern.** If the problem asks for "longest/shortest subarray/substring with some property," it's almost certainly a sliding window problem.
2. **Fixed vs variable:** If the window size is given (e.g., "of size k"), use a fixed-size template. If you need to find the optimal size, use the variable-size expand-shrink template.
3. **HashMap + window** is a powerful combination for character/string problems. Think about what state you need to maintain (character counts, distinct count, etc.).
4. **Monotonic deque** when you need max/min in a sliding window.
5. **Count subarrays ending at each position.** When counting valid subarrays, `right - left + 1` counts all valid subarrays ending at `right`.

## Common Mistakes

- **Off-by-one in window boundaries.** The window is `[left, right]` inclusive. When `right` enters, update state. When removing, remove `left` before incrementing.
- **Forgetting to handle empty/minimal inputs.** Check `s.size() < t.size()` before processing.
- **Not shrinking enough.** In variable-size windows, use `while` (not `if`) to shrink — you may need to remove multiple elements.
- **Integer overflow in product.** Use `long long` for product-based windows.
- **HashMap comparison overhead.** In anagram problems, prefer `array<int, 26>` over `unordered_map<char, int>` for O(1) comparison.

## Practice Problems

1. **Longest Repeating Character Replacement** (LeetCode 424) — Find the longest substring with at most k replacements to make all characters the same. *Hint: Window is valid when `windowSize - maxFreq <= k`.*
2. **Max Consecutive Ones III** (LeetCode 1004) — Longest subarray of 1s after flipping at most k 0s. *Hint: Sliding window, count zeros in window.*
3. **Fruit Into Baskets** (LeetCode 904) — Longest subarray with at most 2 distinct elements. *Hint: Exactly the "longest substring with at most k distinct characters" pattern.*
4. **Minimum Window Subsequence** (LeetCode 727) — Hard variation. *Hint: When a match is found, shrink from left while still matching.*
5. **Substring with Concatenation of All Words** (LeetCode 30) — Find all starting indices of concatenated substrings. *Hint: Fixed-size window of `wordLen * numWords`, use HashMap to match word counts.*
