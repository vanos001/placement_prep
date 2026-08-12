# Chapter 4: Arrays and Strings

Arrays are the most fundamental data structure in computer science. Understanding how they work at the memory level, along with the common techniques used to manipulate them, is essential for interviews. Strings, being arrays of characters, share many of the same properties and patterns.

---

## 4.1 Arrays in Memory

### What Is an Array?

An array is a **contiguous block of memory** that stores elements of the same type, one after another. When you declare `int arr[5]`, the computer allocates 5 × 4 = 20 consecutive bytes (assuming 4-byte integers).

### Memory Layout

```
Memory Address:  1000  1004  1008  1012  1016
                ┌─────┬─────┬─────┬─────┬─────┐
arr:            │  10 │  20 │  30 │  40 │  50 │
                └─────┴─────┴─────┴─────┴─────┘
Index:             0     1     2     3     4
```

### Address Calculation

The address of element `arr[i]` is:

\\[\text{address}(arr[i]) = \text{base\_address} + i \times \text{sizeof(element)}\\]

**Example:** If `arr` starts at address 1000 and each int is 4 bytes:
- `arr[0]` → 1000 + 0×4 = 1000
- `arr[3]` → 1000 + 3×4 = 1012
- `arr[i]` → 1000 + 4i

This is why **array access is O(1)** — we compute the address directly.

### Why Arrays Are Fast: Cache Locality

When the CPU loads data from memory, it doesn't just load a single byte — it loads an entire **cache line** (typically 64 bytes). Since array elements are contiguous, accessing `arr[i]` also loads `arr[i+1]`, `arr[i+2]`, etc. into the cache.

This is called **spatial locality**, and it's why iterating through an array is extremely fast — often faster than following pointers in a linked list, even for the same logical operation.

```cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <list>

int main() {
    const int N = 10000000;

    // Array: contiguous memory
    std::vector<int> vec(N, 1);

    // Linked list: scattered memory
    std::list<int> lst(N, 1);

    // Benchmark: sum all elements
    auto start = std::chrono::high_resolution_clock::now();
    long long sum1 = 0;
    for (int x : vec) sum1 += x;
    auto end = std::chrono::high_resolution_clock::now();
    auto vec_time = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    start = std::chrono::high_resolution_clock::now();
    long long sum2 = 0;
    for (int x : lst) sum2 += x;
    end = std::chrono::high_resolution_clock::now();
    auto lst_time = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    std::cout << "Vector iteration: " << vec_time.count() << " μs\n";
    std::cout << "List iteration:   " << lst_time.count() << " μs\n";
    // Vector is typically 2-10x faster due to cache locality
    return 0;
}
```

### Array Operations — Time Complexities

| Operation | Time | Notes |
|---|---|---|
| Access by index | O(1) | Direct address calculation |
| Search (unsorted) | O(n) | Must check each element |
| Search (sorted) | O(log n) | Binary search |
| Insert at end | O(1) amortized | If space available |
| Insert at position | O(n) | Must shift elements |
| Delete at position | O(n) | Must shift elements |
| Delete at end | O(1) | Just decrease size |

---

## 4.2 Dynamic Arrays (std::vector)

### How std::vector Works

A `std::vector` wraps a dynamically allocated array with:
- `size`: number of elements currently stored
- `capacity`: number of elements the underlying array can hold
- `data`: pointer to the underlying array

```
size = 5, capacity = 8

data → [10, 20, 30, 40, 50, _, _, _]
         0    1    2    3    4    5    6    7
```

### Amortized Doubling

When `push_back` is called and `size == capacity`:

1. Allocate new array with **2× capacity**
2. Copy all existing elements
3. Free old array
4. Insert new element

```
Push 1: capacity=1, size=1  [1]
Push 2: capacity=2, size=2  [1, 2]              ← copied 1 element
Push 3: capacity=4, size=3  [1, 2, 3, _]        ← copied 2 elements
Push 4: capacity=4, size=4  [1, 2, 3, 4]
Push 5: capacity=8, size=5  [1, 2, 3, 4, 5, _, _, _]  ← copied 4 elements
```

**Why double (not add 10 or grow by 50%)?**

Doubling gives **amortized O(1)** per insertion. Growing by a constant amount gives O(n) per insertion on average. Growing by a percentage (like 50%) also gives amortized O(1), but doubling is the simplest.

**Proof sketch:** After n insertions, total copies = 1 + 2 + 4 + ... + 2^k ≈ 2n. Average copies per insertion ≈ 2 = O(1).

### Key Vector Operations

```cpp
#include <iostream>
#include <vector>

int main() {
    // Construction
    std::vector<int> v1;                    // Empty
    std::vector<int> v2(5);                 // 5 zeros
    std::vector<int> v3(5, 42);            // 5 copies of 42
    std::vector<int> v4 = {1, 2, 3, 4, 5}; // Initializer list

    // Size and capacity
    std::cout << "Size: " << v4.size() << std::endl;        // 5
    std::cout << "Capacity: " << v4.capacity() << std::endl; // >= 5

    // Access
    std::cout << "v4[0] = " << v4[0] << std::endl;    // 1 (no bounds check)
    std::cout << "v4.at(0) = " << v4.at(0) << std::endl; // 1 (with bounds check)
    std::cout << "Front: " << v4.front() << std::endl;  // 1
    std::cout << "Back: " << v4.back() << std::endl;    // 5

    // Modifiers
    v4.push_back(6);           // O(1) amortized
    v4.pop_back();             // O(1)
    v4.insert(v4.begin() + 2, 99);  // O(n) — shifts elements
    v4.erase(v4.begin() + 2);       // O(n) — shifts elements

    // Iteration
    for (int x : v4) std::cout << x << " ";
    std::cout << std::endl;

    // Reserve (pre-allocate to avoid reallocations)
    std::vector<int> v5;
    v5.reserve(1000);  // No reallocations until 1000 elements
    for (int i = 0; i < 1000; i++) {
        v5.push_back(i);  // All O(1), no copies
    }

    // Shrink to fit
    v5.shrink_to_fit();  // Reduce capacity to match size

    return 0;
}
```

### Common Pitfalls with Vectors

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3, 4, 5};

    // PITFALL 1: Iterator invalidation
    // BAD: Erasing while iterating forward
    // for (auto it = v.begin(); it != v.end(); ++it) {
    //     if (*it == 3) v.erase(it);  // BUG: invalidates iterator
    // }

    // GOOD: erase returns next valid iterator
    for (auto it = v.begin(); it != v.end(); ) {
        if (*it == 3) it = v.erase(it);
        else ++it;
    }

    // PITFALL 2: Using [] on empty vector
    std::vector<int> empty;
    // empty[0] = 5;  // UNDEFINED BEHAVIOR!
    // Use empty.at(0) for bounds checking, or check size first

    // PITFALL 3: Reallocation invalidates pointers/references
    std::vector<int> v2 = {1, 2, 3};
    int* p = &v2[0];
    v2.push_back(4);  // May reallocate! p is now dangling.
    // *p = 10;  // UNDEFINED BEHAVIOR!

    return 0;
}
```

---

## 4.3 Multidimensional Arrays

### Row-Major vs Column-Major

**Row-major** (C/C++): Elements of each row are stored contiguously.

```
Matrix:          Memory (row-major):
1  2  3          [1, 2, 3, 4, 5, 6]
4  5  6
```

**Column-major** (Fortran, MATLAB, some math libraries): Elements of each column are stored contiguously.

```
Matrix:          Memory (column-major):
1  2  3          [1, 4, 2, 5, 3, 6]
4  5  6
```

### Address Calculation for 2D Arrays

For a matrix with `R` rows and `C` columns (row-major):

\\[\text{address}(arr[i][j]) = \text{base} + (i \times C + j) \times \text{sizeof(element)}\\]

```cpp
#include <iostream>
#include <vector>

int main() {
    const int R = 3, C = 4;

    // Method 1: vector of vectors (common but not cache-friendly for columns)
    std::vector<std::vector<int>> mat(R, std::vector<int>(C, 0));

    // Method 2: Single flat vector (cache-friendly)
    std::vector<int> flat(R * C, 0);
    auto access = [&](int i, int j) -> int& { return flat[i * C + j]; };

    // Fill using flat indexing
    for (int i = 0; i < R; i++) {
        for (int j = 0; j < C; j++) {
            access(i, j) = i * C + j;
        }
    }

    // Print
    for (int i = 0; i < R; i++) {
        for (int j = 0; j < C; j++) {
            std::cout << access(i, j) << "\t";
        }
        std::cout << "\n";
    }

    // Row-major traversal (cache-friendly)
    long long sum = 0;
    for (int i = 0; i < R; i++) {
        for (int j = 0; j < C; j++) {
            sum += access(i, j);  // Sequential memory access
        }
    }

    // Column-major traversal (cache-unfriendly for large matrices)
    sum = 0;
    for (int j = 0; j < C; j++) {
        for (int i = 0; i < R; i++) {
            sum += access(i, j);  // Strided memory access
        }
    }

    return 0;
}
```

### Common 2D Array Patterns

```cpp
#include <iostream>
#include <vector>

int main() {
    int R = 3, C = 4;
    std::vector<std::vector<int>> mat = {
        {1, 2, 3, 4},
        {5, 6, 7, 8},
        {9, 10, 11, 12}
    };

    // Transpose (for square matrices, in-place)
    int N = 3;
    std::vector<std::vector<int>> sq = {{1,2,3},{4,5,6},{7,8,9}};
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            std::swap(sq[i][j], sq[j][i]);
        }
    }
    std::cout << "Transposed:\n";
    for (auto& row : sq) {
        for (int x : row) std::cout << x << " ";
        std::cout << "\n";
    }

    // Rotate 90 degrees clockwise (for square matrices)
    // Step 1: Transpose, Step 2: Reverse each row
    sq = {{1,2,3},{4,5,6},{7,8,9}};
    for (int i = 0; i < N; i++)
        for (int j = i + 1; j < N; j++)
            std::swap(sq[i][j], sq[j][i]);
    for (int i = 0; i < N; i++)
        std::reverse(sq[i].begin(), sq[i].end());

    std::cout << "Rotated 90° CW:\n";
    for (auto& row : sq) {
        for (int x : row) std::cout << x << " ";
        std::cout << "\n";
    }
    // 7 4 1
    // 8 5 2
    // 9 6 3

    return 0;
}
```

---

## 4.4 Strings

### C-Style Strings vs std::string

**C-style strings** are null-terminated character arrays:

```cpp
char str[] = "Hello";  // {'H', 'e', 'l', 'l', 'o', '\0'} — 6 bytes
```

**Problems with C-style strings:**
- Easy to forget the null terminator
- No bounds checking
- Manual memory management
- `strlen()` is O(n) — must scan for '\0'

**std::string** is the modern C++ alternative:

```cpp
#include <iostream>
#include <string>

int main() {
    // Construction
    std::string s1 = "Hello";
    std::string s2("World");
    std::string s3(5, 'a');        // "aaaaa"
    std::string s4 = s1 + " " + s2; // Concatenation

    // Size — O(1)!
    std::cout << "Length: " << s1.size() << std::endl;     // 5
    std::cout << "Length: " << s1.length() << std::endl;   // 5 (same as size)
    std::cout << "Empty: " << s1.empty() << std::endl;     // 0 (false)

    // Access
    std::cout << s1[0] << std::endl;    // 'H' (no bounds check)
    std::cout << s1.at(0) << std::endl; // 'H' (with bounds check)
    std::cout << s1.back() << std::endl; // 'o'

    // Search
    size_t pos = s1.find("ll");
    if (pos != std::string::npos) {
        std::cout << "Found at position: " << pos << std::endl; // 2
    }

    // Substring
    std::string sub = s1.substr(1, 3);  // "ell"

    // Modification
    s1 += "!";           // Append
    s1.push_back('?');   // Add character at end
    s1.pop_back();       // Remove last character
    s1.insert(0, "Hi "); // Insert at position
    s1.erase(0, 3);      // Remove 3 characters from position 0

    // Conversion
    std::string num = "42";
    int n = std::stoi(num);         // String to int
    long long ll = std::stoll(num); // String to long long
    std::string back = std::to_string(n); // Int to string

    // Iteration
    for (char c : s1) std::cout << c;
    std::cout << std::endl;

    return 0;
}
```

### String Operations — Time Complexities

| Operation | std::string | Notes |
|---|---|---|
| `s[i]` | O(1) | Direct access |
| `s.size()` | O(1) | Stored as member |
| `s.find(t)` | O(n·m) worst | Can use O(n+m) with KMP |
| `s.substr(pos, len)` | O(len) | Creates new string |
| `s + t` | O(n + m) | Creates new string |
| `s += t` | O(m) amortized | Appends in place |
| `s == t` | O(n) | Character-by-character comparison |

### String Immutability Considerations

In many languages (Java, Python), strings are **immutable** — every modification creates a new string. In C++, `std::string` is mutable, but concatenation in a loop can still be expensive:

```cpp
#include <iostream>
#include <string>
#include <sstream>

// BAD: O(n²) due to repeated string copies
std::string buildBad(const std::vector<int>& nums) {
    std::string result;
    for (int num : nums) {
        result += std::to_string(num) + " ";  // May copy entire string each time
    }
    return result;
}

// GOOD: O(n) — stringstream or reserve
std::string buildGood(const std::vector<int>& nums) {
    std::ostringstream oss;
    for (int num : nums) {
        oss << num << " ";
    }
    return oss.str();
}

// ALSO GOOD: reserve space upfront
std::string buildGood2(const std::vector<int>& nums) {
    std::string result;
    result.reserve(nums.size() * 5);  // Estimate: each number ~5 chars
    for (int num : nums) {
        result += std::to_string(num) + " ";
    }
    return result;
}

int main() {
    std::vector<int> nums = {1, 2, 3, 4, 5};
    std::cout << buildGood(nums) << std::endl;
    return 0;
}
```

---

## 4.5 Common Array Techniques

### Two Pointers

Two pointers moving toward each other or in the same direction:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Check if array has a pair that sums to target
bool hasPairWithSum(std::vector<int>& arr, int target) {
    std::sort(arr.begin(), arr.end());
    int left = 0, right = arr.size() - 1;

    while (left < right) {
        int sum = arr[left] + arr[right];
        if (sum == target) return true;
        else if (sum < target) left++;
        else right--;
    }
    return false;
}

int main() {
    std::vector<int> arr = {2, 7, 11, 15};
    std::cout << std::boolalpha;
    std::cout << "Has pair sum 9: " << hasPairWithSum(arr, 9) << std::endl;  // true
    return 0;
}
```

### Reversal

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Reverse a portion of an array
void reverse(std::vector<int>& arr, int start, int end) {
    while (start < end) {
        std::swap(arr[start], arr[end]);
        start++;
        end--;
    }
}

int main() {
    std::vector<int> arr = {1, 2, 3, 4, 5};
    reverse(arr, 0, arr.size() - 1);

    std::cout << "Reversed: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 5 4 3 2 1
    return 0;
}
```

### Array Rotation

**Rotate array right by k positions** using the reversal algorithm:

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Rotate right by k positions using three reversals
// Time: O(n), Space: O(1)
void rotate(std::vector<int>& nums, int k) {
    int n = nums.size();
    k = k % n;  // Handle k > n

    // Step 1: Reverse entire array
    std::reverse(nums.begin(), nums.end());
    // Step 2: Reverse first k elements
    std::reverse(nums.begin(), nums.begin() + k);
    // Step 3: Reverse remaining elements
    std::reverse(nums.begin() + k, nums.end());
}

int main() {
    std::vector<int> nums = {1, 2, 3, 4, 5, 6, 7};
    int k = 3;

    rotate(nums, k);

    std::cout << "Rotated right by " << k << ": ";
    for (int x : nums) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 5 6 7 1 2 3 4

    return 0;
}
```

**Dry run with nums = [1,2,3,4,5,6,7], k = 3:**

```
Original:        [1, 2, 3, 4, 5, 6, 7]
Reverse all:     [7, 6, 5, 4, 3, 2, 1]
Reverse first 3: [5, 6, 7, 4, 3, 2, 1]
Reverse last 4:  [5, 6, 7, 1, 2, 3, 4]  ✓
```

### Partitioning (Dutch National Flag)

The Dutch National Flag problem: sort an array of 0s, 1s, and 2s in a single pass.

```cpp
#include <iostream>
#include <vector>

// Dutch National Flag Algorithm
// Time: O(n), Space: O(1)
void sortColors(std::vector<int>& nums) {
    int low = 0;      // Boundary for 0s
    int mid = 0;      // Current element
    int high = nums.size() - 1;  // Boundary for 2s

    while (mid <= high) {
        if (nums[mid] == 0) {
            std::swap(nums[low], nums[mid]);
            low++;
            mid++;
        } else if (nums[mid] == 1) {
            mid++;
        } else {  // nums[mid] == 2
            std::swap(nums[mid], nums[high]);
            high--;
            // Don't increment mid — need to check swapped element
        }
    }
}

int main() {
    std::vector<int> nums = {2, 0, 2, 1, 1, 0};
    sortColors(nums);

    std::cout << "Sorted colors: ";
    for (int x : nums) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 0 0 1 1 2 2

    return 0;
}
```

**Visual representation:**

```
[0, 0, ..., 0, 1, 1, ..., 1, ?, ?, ..., ?, 2, 2, ..., 2]
 ^           ^  ^           ^  ^          ^  ^           ^
 0        low-1 low      mid-1 mid     high high+1    n-1

0s region: [0, low)
1s region: [low, mid)
Unknown:   [mid, high]
2s region: (high, n-1]
```

### Sliding Window

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Maximum sum subarray of size k
// Time: O(n), Space: O(1)
int maxSumSubarray(const std::vector<int>& arr, int k) {
    int n = arr.size();
    if (n < k) return -1;

    // Compute sum of first window
    int windowSum = 0;
    for (int i = 0; i < k; i++) {
        windowSum += arr[i];
    }

    int maxSum = windowSum;

    // Slide the window
    for (int i = k; i < n; i++) {
        windowSum += arr[i] - arr[i - k];  // Add new, remove old
        maxSum = std::max(maxSum, windowSum);
    }

    return maxSum;
}

int main() {
    std::vector<int> arr = {2, 1, 5, 1, 3, 2};
    int k = 3;
    std::cout << "Max sum subarray of size " << k << ": "
              << maxSumSubarray(arr, k) << std::endl;
    // Output: 9 (subarray [5, 1, 3])
    return 0;
}
```

### Prefix Sums

```cpp
#include <iostream>
#include <vector>

// Prefix sum for range sum queries
class PrefixSum {
    std::vector<long long> prefix;

public:
    PrefixSum(const std::vector<int>& arr) {
        int n = arr.size();
        prefix.resize(n + 1, 0);
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + arr[i];
        }
    }

    // Sum of elements from index l to r (inclusive)
    long long rangeSum(int l, int r) {
        return prefix[r + 1] - prefix[l];
    }
};

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    PrefixSum ps(arr);

    std::cout << "Sum [0..2]: " << ps.rangeSum(0, 2) << std::endl;  // 8
    std::cout << "Sum [3..5]: " << ps.rangeSum(3, 5) << std::endl;  // 15
    std::cout << "Sum [0..7]: " << ps.rangeSum(0, 7) << std::endl;  // 31

    return 0;
}
```

---

## 4.6 STL Containers

### Choosing the Right Container

| Container | When to Use | Random Access | Insert/Erase Middle | Insert/Erase End |
|---|---|---|---|---|
| `std::array<T,N>` | Fixed-size array known at compile time | O(1) | O(n) | N/A |
| `std::vector<T>` | Dynamic array, most common choice | O(1) | O(n) | O(1) amortized |
| `std::deque<T>` | Insert/remove at both ends | O(1) | O(n) | O(1) |
| `std::string` | Text manipulation | O(1) | O(n) | O(1) amortized |

### std::array vs C-style Array

```cpp
#include <iostream>
#include <array>

int main() {
    // C-style array — no size info, decays to pointer
    int c_arr[5] = {1, 2, 3, 4, 5};

    // std::array — knows its size, supports STL algorithms
    std::array<int, 5> arr = {1, 2, 3, 4, 5};

    std::cout << "Size: " << arr.size() << std::endl;
    std::cout << "Empty: " << arr.empty() << std::endl;

    // Iteration
    for (int x : arr) std::cout << x << " ";
    std::cout << std::endl;

    // Fill
    arr.fill(0);

    // At with bounds checking
    try {
        arr.at(10) = 5;  // Throws std::out_of_range
    } catch (const std::out_of_range& e) {
        std::cout << "Out of range: " << e.what() << std::endl;
    }

    return 0;
}
```

### std::deque

```cpp
#include <iostream>
#include <deque>

int main() {
    std::deque<int> dq;

    // Push/pop at both ends — O(1)
    dq.push_back(3);    // [3]
    dq.push_back(4);    // [3, 4]
    dq.push_front(2);   // [2, 3, 4]
    dq.push_front(1);   // [1, 2, 3, 4]

    dq.pop_front();     // [2, 3, 4]
    dq.pop_back();      // [2, 3]

    // Random access — O(1)
    std::cout << "dq[0] = " << dq[0] << std::endl;  // 2

    for (int x : dq) std::cout << x << " ";
    std::cout << std::endl;

    return 0;
}
```

---

## Interview Problems

### Problem 1: Two Sum

**Problem:** Given an array of integers and a target, return indices of two numbers that add up to the target.

**Approach:** Use a hash map to store seen values. For each element, check if `target - element` exists in the map.

```cpp
#include <iostream>
#include <vector>
#include <unordered_map>

// Time: O(n), Space: O(n)
std::vector<int> twoSum(const std::vector<int>& nums, int target) {
    std::unordered_map<int, int> seen;  // value -> index

    for (int i = 0; i < (int)nums.size(); i++) {
        int complement = target - nums[i];
        if (seen.count(complement)) {
            return {seen[complement], i};
        }
        seen[nums[i]] = i;
    }

    return {};  // No solution
}

int main() {
    std::vector<int> nums = {2, 7, 11, 15};
    int target = 9;

    auto result = twoSum(nums, target);
    std::cout << "Indices: [" << result[0] << ", " << result[1] << "]" << std::endl;
    // Output: [0, 1] because nums[0] + nums[1] = 2 + 7 = 9

    return 0;
}
```

**Dry run with nums = [2, 7, 11, 15], target = 9:**

| i | nums[i] | complement | seen | Found? |
|---|---|---|---|---|
| 0 | 2 | 7 | {2:0} | No |
| 1 | 7 | 2 | {2:0, 7:1} | Yes! seen[2]=0 |

Return [0, 1].

### Problem 2: Best Time to Buy and Sell Stock

**Problem:** Given prices on each day, find the maximum profit from one buy and one sell.

**Approach:** Track the minimum price seen so far. At each day, calculate potential profit.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Time: O(n), Space: O(1)
int maxProfit(const std::vector<int>& prices) {
    if (prices.empty()) return 0;

    int minPrice = prices[0];
    int maxProfit = 0;

    for (int i = 1; i < (int)prices.size(); i++) {
        // Update max profit if selling today is better
        maxProfit = std::max(maxProfit, prices[i] - minPrice);
        // Update minimum price
        minPrice = std::min(minPrice, prices[i]);
    }

    return maxProfit;
}

int main() {
    std::vector<int> prices = {7, 1, 5, 3, 6, 4};
    std::cout << "Max profit: " << maxProfit(prices) << std::endl;
    // Output: 5 (buy at 1, sell at 6)

    std::vector<int> prices2 = {7, 6, 4, 3, 1};
    std::cout << "Max profit: " << maxProfit(prices2) << std::endl;
    // Output: 0 (prices only decrease)

    return 0;
}
```

### Problem 3: Remove Duplicates from Sorted Array

**Problem:** Remove duplicates in-place from a sorted array. Return the new length.

**Approach:** Two pointers — one for the write position, one for scanning.

```cpp
#include <iostream>
#include <vector>

// Time: O(n), Space: O(1)
int removeDuplicates(std::vector<int>& nums) {
    if (nums.empty()) return 0;

    int writePos = 0;  // Position to write next unique element

    for (int i = 1; i < (int)nums.size(); i++) {
        if (nums[i] != nums[writePos]) {
            writePos++;
            nums[writePos] = nums[i];
        }
    }

    return writePos + 1;
}

int main() {
    std::vector<int> nums = {1, 1, 2, 2, 3, 4, 4, 5};
    int newLen = removeDuplicates(nums);

    std::cout << "New length: " << newLen << std::endl;
    std::cout << "Array: ";
    for (int i = 0; i < newLen; i++) std::cout << nums[i] << " ";
    std::cout << std::endl;
    // Output: New length: 5, Array: 1 2 3 4 5

    return 0;
}
```

### Problem 4: Rotate Array

**Problem:** Rotate array to the right by k steps.

**Approach:** Three reversals (shown in Section 4.5).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Time: O(n), Space: O(1)
void rotate(std::vector<int>& nums, int k) {
    int n = nums.size();
    k = k % n;

    std::reverse(nums.begin(), nums.end());
    std::reverse(nums.begin(), nums.begin() + k);
    std::reverse(nums.begin() + k, nums.end());
}

int main() {
    std::vector<int> nums = {1, 2, 3, 4, 5, 6, 7};
    rotate(nums, 3);

    std::cout << "Rotated: ";
    for (int x : nums) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 5 6 7 1 2 3 4

    return 0;
}
```

---

## Interview Tips

1. **Always clarify constraints.** Is the array sorted? Are there duplicates? What's the range of values? Can negative numbers appear?

2. **Two pointers and hash maps are your best friends** for array problems. When you see "pair" or "sum," think two pointers (if sorted) or hash map (if unsorted).

3. **In-place manipulation** is often required. Use the two-pointer technique to avoid extra space.

4. **Prefix sums** are powerful for range query problems. Build once O(n), query O(1) each.

5. **Edge cases to always check:**
   - Empty array
   - Single element
   - All elements the same
   - Already sorted
   - Reverse sorted

6. **Know your STL.** `std::sort` is O(n log n). `std::reverse` is O(n). `std::find` is O(n). `std::lower_bound` is O(log n) on sorted ranges.

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---|---|---|
| Off-by-one in loop bounds | `i <= n` vs `i < n` | Be explicit about boundaries |
| Modifying array while iterating | Can skip elements or go out of bounds | Use separate pass or two-pointer |
| Forgetting to handle empty input | Crashes or wrong answer | Always check `if (arr.empty())` |
| Using `vector<bool>` | Specialization, weird reference type | Use `vector<char>` or `vector<int>` |
| Integer overflow in sum | Sum of 10^5 ints can overflow int | Use `long long` |
| Not accounting for negative numbers | Two-pointer on sorted may miss pairs | Clarify constraints upfront |

## Practice Problems

| # | Problem | Difficulty | Key Technique |
|---|---|---|---|
| 1 | Maximum Subarray (Kadane's algorithm) | Easy | Dynamic programming / greedy |
| 2 | Contains Duplicate | Easy | Hash set |
| 3 | Product of Array Except Self | Medium | Prefix/suffix products |
| 4 | Maximum Product Subarray | Medium | Track min and max |
| 5 | 3Sum | Medium | Sort + two pointers |
| 6 | Container With Most Water | Medium | Two pointers from ends |
| 7 | Merge Intervals | Medium | Sort + linear scan |
| 8 | Spiral Matrix | Medium | Layer-by-layer traversal |
| 9 | Set Matrix Zeroes | Medium | Use first row/column as markers |
| 10 | Longest Consecutive Sequence | Medium | Hash set |

---

*In the next chapter, we'll study sorting algorithms — a rich source of interview questions and algorithmic techniques.*

---

## Additional Exercises

### Exercise 1: Find the Majority Element
**Difficulty**: Easy
**Problem**: Given an array of size n, find the element that appears more than ⌊n/2⌋ times. The element is guaranteed to exist.
**Hint**: Boyer-Moore Voting Algorithm: maintain a candidate and a counter. If counter is 0, set current element as candidate. If element matches candidate, increment counter; otherwise decrement. The candidate at the end is the majority element.
**Expected Time Complexity**: O(n), Space: O(1).

### Exercise 2: Trapping Rain Water
**Difficulty**: Hard
**Problem**: Given n non-negative integers representing elevation heights, compute how much water can be trapped after rain.
**Hint**: For each position, water trapped = min(max_left, max_right) - height[i]. Precompute max_left and max_right arrays, or use two pointers from both ends to compute in O(1) space.
**Expected Time Complexity**: O(n), Space: O(1) with two pointers.

### Exercise 3: Find All Anagrams in a String
**Difficulty**: Medium
**Problem**: Given strings s and p, find all starting indices of p's anagrams in s.
**Hint**: Use a sliding window of size |p|. Maintain a frequency count of characters in the window. Compare with p's frequency count. Slide the window by adding the new character and removing the old one.
**Expected Time Complexity**: O(n) where n = |s|.

### Exercise 4: Longest Substring Without Repeating Characters
**Difficulty**: Medium
**Problem**: Given a string, find the length of the longest substring without repeating characters.
**Hint**: Sliding window with a hash map tracking the last index of each character. When you see a repeat, move the left pointer to one past the previous occurrence. Track the maximum window size.
**Expected Time Complexity**: O(n).

### Exercise 5: Product of Array Except Self Without Division
**Difficulty**: Medium
**Problem**: Given an integer array, return an array where each element is the product of all other elements. Cannot use division.
**Hint**: Build prefix products (product of all elements before i) and suffix products (product of all elements after i) in two passes. Result[i] = prefix[i] × suffix[i]. Can be done in O(1) extra space by using the output array for prefix, then multiplying by suffix in a reverse pass.
**Expected Time Complexity**: O(n), Space: O(1) excluding output.

### Exercise 6: Minimum Window Substring
**Difficulty**: Hard
**Problem**: Given strings s and t, find the minimum window in s that contains all characters of t.
**Hint**: Sliding window: expand right to include all required characters, then shrink left to minimize the window. Track how many characters are still needed. When all are satisfied, update the minimum. Use a frequency map for t.
**Expected Time Complexity**: O(|s| + |t|).

### Exercise 7: Spiral Matrix Traversal
**Difficulty**: Medium
**Problem**: Given an m×n matrix, return all elements in spiral order.
**Hint**: Use four boundaries: top, bottom, left, right. Traverse right along top row, then down along right column, then left along bottom row, then up along left column. After each traversal, shrink the corresponding boundary. Stop when boundaries cross.
**Expected Time Complexity**: O(m × n).

### Exercise 8: Find First Missing Positive Integer
**Difficulty**: Hard
**Problem**: Given an unsorted integer array (may contain negatives and zeros), find the smallest missing positive integer. Must run in O(n) time and O(1) space.
**Hint**: Use the array as a hash set. For each value v in [1, n], place it at index v-1 by swapping. Then scan: the first index i where arr[i] != i+1 gives the answer i+1.
**Expected Time Complexity**: O(n), Space: O(1).

### Exercise 9: Group Anagrams Together
**Difficulty**: Medium
**Problem**: Given an array of strings, group anagrams together.
**Hint**: Sort each string to get its "anagram key." Use a hash map from sorted string to list of original strings. All anagrams share the same sorted form.
**Expected Time Complexity**: O(n × k log k) where k is the max string length.

### Exercise 10: Container With Most Water
**Difficulty**: Medium
**Problem**: Given n non-negative integers representing vertical lines, find two lines that together with the x-axis form a container holding the most water.
**Hint**: Two pointers at both ends. Area = min(height[left], height[right]) × (right - left). Move the pointer with the shorter height inward, because moving the taller one can never increase the area.
**Expected Time Complexity**: O(n), Space: O(1).

---

## Additional Interview Questions

### Q1: Why are arrays the most cache-friendly data structure?
**Key Insight**: Arrays store elements in contiguous memory. When the CPU accesses `arr[i]`, it loads an entire cache line (typically 64 bytes) containing `arr[i]` through `arr[i+15]` (for 4-byte ints). Subsequent accesses to nearby elements hit the cache. This "spatial locality" makes array iteration 2-10x faster than linked list traversal, even for the same number of elements. This is why `std::vector` is preferred over `std::list` for most use cases.
**Optimal Complexity**: Array access is O(1) with near-zero latency on cache hits.

### Q2: Explain the two-pointer technique. When does it apply?
**Key Insight**: Two pointers work when the array has some **monotonic property** (sorted, or partitioned). Common patterns: (1) Converging pointers from both ends — find pair with target sum in sorted array. (2) Fast/slow pointers — detect cycles or find middle. (3) Same-direction pointers — remove duplicates, partition arrays. The key insight: moving a pointer in a predictable direction eliminates the need to check all pairs, reducing O(n²) to O(n).
**Optimal Complexity**: Typically O(n) time, O(1) space.

### Q3: How do prefix sums help with range query problems?
**Key Insight**: A prefix sum array `prefix[i]` stores the sum of elements from index 0 to i-1. Range sum from l to r is `prefix[r+1] - prefix[l]` in O(1). Build the prefix array in O(n). This transforms any number of range sum queries from O(n) each to O(1) each. Extended to 2D for submatrix sums. Also useful for counting subarrays with target sum: for each index, count how many previous prefix sums equal `current_prefix - target`.
**Optimal Complexity**: O(n) build, O(1) per query.

### Q4: What is the sliding window technique and when should you use it?
**Key Insight**: Sliding window maintains a "window" [left, right] over the array that satisfies some invariant. As right expands, update the window state. When the invariant is violated, shrink from the left. Use when: (1) looking for a contiguous subarray/substring, (2) the window state can be updated incrementally in O(1) when adding/removing elements. Common problems: longest substring without repeats, minimum window substring, maximum sum subarray of size k.
**Optimal Complexity**: O(n) — each element enters and leaves the window at most once.

### Q5: How would you handle integer overflow when computing sums over large arrays?
**Key Insight**: An array of 10^5 integers each up to 10^9 can sum to 10^14, which overflows a 32-bit int (max ~2×10^9). Use `long long` (64-bit) for accumulations. In Java, use `long`. Watch for overflow in intermediate computations too — e.g., `mid = (lo + hi) / 2` can overflow; use `mid = lo + (hi - lo) / 2` instead. Always consider the maximum possible value of your accumulator.
**Optimal Complexity**: No performance impact — just use wider types.

### Q6: How do you efficiently rotate a matrix 90 degrees clockwise in-place?
**Key Insight**: Two-step process: (1) Transpose the matrix (swap `mat[i][j]` with `mat[j][i]` for all i < j). (2) Reverse each row. This rotates 90° clockwise. For 90° counterclockwise: transpose then reverse each column. For 180°: reverse each row then reverse each column. All are O(n²) with O(1) space.
**Optimal Complexity**: O(n²) time, O(1) space.

### Q7: What is Kadane's algorithm and what's the key insight behind it?
**Key Insight**: Kadane's algorithm finds the maximum subarray sum in O(n). At each position, decide: extend the current subarray (`current_sum + arr[i]`) or start a new one (`arr[i]`). Take the max. The key insight: if the running sum becomes negative, it can never contribute to a maximum subarray starting at a later position, so reset it. Track the global maximum separately.
**Optimal Complexity**: O(n) time, O(1) space.

### Q8: How do you solve the "two sum" problem optimally?
**Key Insight**: For unsorted arrays: use a hash map. For each element, check if `target - element` exists in the map. O(n) time, O(n) space. For sorted arrays: use two pointers from both ends. If sum < target, move left pointer right; if sum > target, move left pointer left. O(n) time, O(1) space. The hash map approach works for unsorted data; the two-pointer approach works only for sorted data but uses no extra space.
**Optimal Complexity**: O(n) time with hash map or O(n log n) if sorting is needed first.

### Q9: When should you use a hash set vs a boolean array for tracking seen elements?
**Key Insight**: Use a boolean array when the value range is small and known (e.g., values in [0, 10^6]) — O(1) access with no hashing overhead. Use a hash set when values can be large, sparse, or non-integer (strings, objects). Hash sets have O(1) amortized but higher constant factors and potential collisions. Boolean arrays have O(1) guaranteed with minimal overhead.
**Optimal Complexity**: Both O(1) per operation. Boolean arrays are faster in practice for bounded ranges.

### Q10: How do you handle problems that ask for "all subarrays" — isn't that O(n²)?
**Key Insight**: Enumerating all subarrays is indeed O(n²). But many problems have O(n) or O(n log n) solutions using clever techniques: (1) Kadane's for max sum subarray, (2) prefix sums + hash map for count of subarrays with target sum, (3) sliding window for subarrays satisfying a monotonic property, (4) divide and conquer for counting special subarrays. The key is to avoid explicitly enumerating every subarray — instead, compute the answer incrementally.
**Optimal Complexity**: Depends on the specific problem, but often O(n) with the right technique.

---

## See Also

- [Chapter 5: Sorting](ch05-sorting.md) — Sorting is a building block for many array problems.
- [Chapter 34: Two Pointers](ch34-two-pointers.md) — A deep dive into the two-pointer technique.
- [Chapter 35: Sliding Window](ch35-sliding-window.md) — The sliding window technique in depth.
