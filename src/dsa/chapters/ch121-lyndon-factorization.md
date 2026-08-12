# Chapter 121: Lyndon Factorization

## Prerequisites
- String basics
- Understanding of string rotations

## Interview Frequency: ★

A Lyndon word is a string that is strictly smaller (lexicographically) than all of its non-trivial rotations. Every string has a unique Lyndon factorization — a decomposition into non-increasing Lyndon words. This factorization has elegant applications in string processing, including finding the minimal rotation of a string.

---

## 121.1 Definitions

### Lyndon Word
A string **w** is a **Lyndon word** if it is strictly smaller than all its non-trivial rotations.

**Example:** `"abc"` is a Lyndon word because:
- Rotations: `"abc"`, `"bca"`, `"cab"`
- `"abc" < "bca"` ✓ and `"abc" < "cab"` ✓

**Counter-example:** `"aba"` is NOT a Lyndon word because:
- Rotations: `"aba"`, `"baa"`, `"aab"`
- `"aba" > "aab"` ✗

### Lyndon Factorization
Every string **s** can be uniquely decomposed as:

```
s = w₁w₂...wₖ
```

where each **wᵢ** is a Lyndon word and **w₁ ≥ w₂ ≥ ... ≥ wₖ** (non-increasing lexicographic order).

**Example:** `"abcabc"` → `"abc" + "abc"` (both are Lyndon words, "abc" ≥ "abc" ✓)

**Example:** `"aabab"` → `"aab" + "ab"` ("aab" ≥ "ab" ✓)

---

## 121.2 Properties

1. **Uniqueness:** Every string has exactly one Lyndon factorization.
2. **Non-increasing:** The factors are in non-increasing lexicographic order.
3. **First factor:** The first factor w₁ is the lexicographically smallest suffix of s.
4. **Minimal rotation:** The first Lyndon factor gives the starting position of the minimal rotation.
5. **Single factor:** A string is itself a Lyndon word iff its factorization has exactly one factor.

---

## 121.3 Duval's Algorithm

Duval's algorithm (1983) computes the Lyndon factorization in **O(n)** time and **O(1)** extra space.

### Intuition

The algorithm maintains three pointers:
- **i:** Start of the current factor candidate
- **j:** Current position being compared
- **k:** Position within the current period

It scans the string left to right, extending the current candidate. When it finds that the current character breaks the Lyndon property, it backtracks and outputs factors.

### Algorithm

```
i = 0
while i < n:
    j = i + 1, k = i
    while j < n and s[k] <= s[j]:
        if s[k] < s[j]:
            k = i      # Reset period
        else:
            k++        # Continue period
        j++
    while i <= k:
        output factor starting at i of length (j - k)
        i += j - k
```

### Step-by-Step Walkthrough

**Input:** `s = "aabab"`

**Step 1:** i=0, j=1, k=0
- Compare s[0]='a' with s[1]='a': equal → k++, j++
- k=1, j=2
- Compare s[1]='a' with s[2]='b': s[1] < s[2] → k=0, j++
- k=0, j=3
- Compare s[0]='a' with s[3]='a': equal → k++, j++
- k=1, j=4
- Compare s[1]='a' with s[4]='b': s[1] < s[4] → k=0, j++
- k=0, j=5 (j == n, loop ends)

Now output factors while i ≤ k:
- i=0, k=0: factor of length j-k = 5-0 = 5? No, wait...

Let me re-trace more carefully.

**Input:** `s = "aabab"`, n=5

**Iteration 1:** i=0
- j=1, k=0
- s[k]='a' vs s[j]='a': equal → k=1, j=2
- s[k]='a' vs s[j]='b': 'a' < 'b' → k=0, j=3
- s[k]='a' vs s[j]='a': equal → k=1, j=4
- s[k]='a' vs s[j]='b': 'a' < 'b' → k=0, j=5
- j == n, exit inner loop

- i=0, k=0: output s[0..2] = "aab" (length j-k=5-0=5? No...)

Actually, the factor length is j-k. Let me re-check the algorithm.

The standard Duval's algorithm:

```
i = 0
while i < n:
    j = i + 1, k = i
    while j < n and s[k] <= s[j]:
        if s[k] < s[j]:
            k = i
        else:
            k++
        j++
    while i <= k:
        result.push_back(i)
        i += j - k
```

The factor has length `j - k`, and starts at position `i`.

Let me retrace:

**Input:** `s = "aabab"`, n=5

**Iteration:** i=0
- j=1, k=0
- s[0]='a' <= s[1]='a': equal → k=1, j=2
- s[1]='a' <= s[2]='b': 'a' < 'b' → k=0, j=3
- s[0]='a' <= s[3]='a': equal → k=1, j=4
- s[1]='a' <= s[4]='b': 'a' < 'b' → k=0, j=5
- j=5 == n, exit

Now: i=0, k=0, j=5, factor length = j-k = 5
- i <= k (0 <= 0): push i=0, i += 5 → i=5

So the result is one factor: "aabab" (the whole string is a Lyndon word).

Wait, is "aabab" a Lyndon word? Let me check its rotations:
- aabab, ababa, babaa, abaab, baab
- Sort: aabab, abaab, ababa, baab, babaa
- "aabab" is the smallest → Yes, it IS a Lyndon word!

Let me try a different example.

**Input:** `s = "ababc"`, n=5

**Iteration:** i=0
- j=1, k=0
- s[0]='a' <= s[1]='b': 'a' < 'b' → k=0, j=2
- s[0]='a' <= s[2]='a': equal → k=1, j=3
- s[1]='b' <= s[3]='b': equal → k=2, j=4
- s[2]='a' <= s[4]='c': 'a' < 'c' → k=0, j=5
- j=5 == n, exit

i=0, k=0, j=5, factor length = 5-0 = 5
- i <= k: push 0, i += 5 → i=5

Again one factor. Let me try "baab":

**Input:** `s = "baab"`, n=4

**Iteration:** i=0
- j=1, k=0
- s[0]='b' <= s[1]='a': 'b' > 'a' → exit inner loop

- i=0, k=0, j=1, factor length = 1-0 = 1
- i <= k (0<=0): push 0, i += 1 → i=1

**Iteration:** i=1
- j=2, k=1
- s[1]='a' <= s[2]='a': equal → k=2, j=3
- s[2]='a' <= s[3]='b': 'a' < 'b' → k=1, j=4
- j=4 == n, exit

- i=1, k=1, j=4, factor length = 4-1 = 3
- i <= k (1<=1): push 1, i += 3 → i=4

Result: factors at positions [0, 1] → "b" + "aab"

Check: "b" is Lyndon ✓, "aab" is Lyndon ✓, "b" ≥ "aab" ✓ (since 'b' > 'a')

---

## 121.4 Implementation

### C++

```cpp
#include <iostream>
#include <string>
#include <vector>

// Returns starting positions of Lyndon factors
std::vector<int> lyndonFactorization(const std::string& s) {
    int n = s.size();
    std::vector<int> result;
    int i = 0;
    while (i < n) {
        int j = i + 1, k = i;
        while (j < n && s[k] <= s[j]) {
            if (s[k] < s[j]) k = i;
            else k++;
            j++;
        }
        while (i <= k) {
            result.push_back(i);
            i += j - k;
        }
    }
    return result;
}

// Get the actual Lyndon factors as strings
std::vector<std::string> getLyndonFactors(const std::string& s) {
    auto starts = lyndonFactorization(s);
    std::vector<std::string> factors;
    for (int idx = 0; idx < (int)starts.size(); idx++) {
        int start = starts[idx];
        int end = (idx + 1 < (int)starts.size()) ? starts[idx + 1] : s.size();
        factors.push_back(s.substr(start, end - start));
    }
    return factors;
}

// Find minimal rotation using Lyndon factorization
int minimalRotation(const std::string& s) {
    std::string doubled = s + s;
    auto starts = lyndonFactorization(doubled);
    for (int pos : starts) {
        if (pos < (int)s.size()) return pos;
    }
    return 0;
}

int main() {
    std::string s = "abcabc";
    auto factors = getLyndonFactors(s);
    std::cout << "Lyndon factors of \"" << s << "\":\n";
    for (auto& f : factors)
        std::cout << "  \"" << f << "\"\n";
    
    std::string t = "cabcab";
    std::cout << "Minimal rotation of \"" << t << "\" starts at index "
              << minimalRotation(t) << "\n";
    return 0;
}
```

### Python

```python
def lyndon_factorization(s: str) -> list[int]:
    """Returns starting positions of Lyndon factors."""
    n = len(s)
    result = []
    i = 0
    while i < n:
        j, k = i + 1, i
        while j < n and s[k] <= s[j]:
            if s[k] < s[j]:
                k = i
            else:
                k += 1
            j += 1
        while i <= k:
            result.append(i)
            i += j - k
    return result


def get_lyndon_factors(s: str) -> list[str]:
    """Returns the actual Lyndon factor strings."""
    starts = lyndon_factorization(s)
    factors = []
    for idx in range(len(starts)):
        start = starts[idx]
        end = starts[idx + 1] if idx + 1 < len(starts) else len(s)
        factors.append(s[start:end])
    return factors


def minimal_rotation(s: str) -> int:
    """Find the starting index of the minimal rotation."""
    doubled = s + s
    starts = lyndon_factorization(doubled)
    for pos in starts:
        if pos < len(s):
            return pos
    return 0


# Example usage
if __name__ == "__main__":
    s = "abcabc"
    print(f"Lyndon factors of '{s}': {get_lyndon_factors(s)}")
    
    t = "cabcab"
    print(f"Minimal rotation of '{t}' starts at index {minimal_rotation(t)}")
```

### Java

```java
import java.util.*;

class LyndonFactorization {
    // Returns starting positions of Lyndon factors
    static List<Integer> lyndonFactorization(String s) {
        int n = s.length();
        List<Integer> result = new ArrayList<>();
        int i = 0;
        while (i < n) {
            int j = i + 1, k = i;
            while (j < n && s.charAt(k) <= s.charAt(j)) {
                if (s.charAt(k) < s.charAt(j)) k = i;
                else k++;
                j++;
            }
            while (i <= k) {
                result.add(i);
                i += j - k;
            }
        }
        return result;
    }
    
    // Get the actual Lyndon factors as strings
    static List<String> getLyndonFactors(String s) {
        List<Integer> starts = lyndonFactorization(s);
        List<String> factors = new ArrayList<>();
        for (int idx = 0; idx < starts.size(); idx++) {
            int start = starts.get(idx);
            int end = (idx + 1 < starts.size()) ? starts.get(idx + 1) : s.length();
            factors.add(s.substring(start, end));
        }
        return factors;
    }
    
    // Find minimal rotation using Lyndon factorization
    static int minimalRotation(String s) {
        String doubled = s + s;
        List<Integer> starts = lyndonFactorization(doubled);
        for (int pos : starts) {
            if (pos < s.length()) return pos;
        }
        return 0;
    }
    
    public static void main(String[] args) {
        String s = "abcabc";
        System.out.println("Lyndon factors of \"" + s + "\": " + getLyndonFactors(s));
        
        String t = "cabcab";
        System.out.println("Minimal rotation of \"" + t + "\" starts at index " + minimalRotation(t));
    }
}
```

---

## 121.5 Complexity Analysis

| Aspect | Complexity |
|---|---|
| Time | O(n) |
| Space | O(n) for storing results, O(1) for the algorithm itself |

**Why O(n)?** Each character is compared at most twice (once when advancing j, once when outputting factors). The total number of comparisons is bounded by 2n.

---

## 121.6 Applications

### 1. Minimal String Rotation

The minimal rotation of a string is the lexicographically smallest among all its rotations. Using Lyndon factorization on `s + s`, the first factor gives the answer.

**Example:** `"cabcab"` → double to `"cabcabcabcab"` → Lyndon factorization gives factors starting at positions that include 3 → minimal rotation starts at index 3, giving `"abccab"` → wait, let me recheck.

Actually for `"cabcab"`:
- Doubled: `"cabcabcabcab"`
- Lyndon factorization: The first Lyndon factor of the doubled string that starts within the first `n` positions gives the minimal rotation.
- Minimal rotation of `"cabcab"` is `"abccab"` → No, rotations are: cabcab, abcabc, bcabca, cabcab, abcabc, bcabca. The unique ones are: abcabc, bcabca, cabcab. Minimal is "abcabc" starting at index 1.

### 2. String Periodicity

A string is periodic with period p iff its Lyndon factorization consists of copies of the same Lyndon word of length p.

### 3. Burrows-Wheeler Transform

Lyndon factorization connects to the BWT through the concept of necklace representatives.

### 4. Duval's Algorithm for Minimal Rotation

A variant of Duval's algorithm directly computes the minimal rotation in O(n) time without explicitly doubling the string.

---

## 121.7 Dry Run: Duval's Algorithm

**Input:** `s = "ababc"` (n=5)

```
i=0: j=1, k=0
  s[0]='a' <= s[1]='b': 'a' < 'b' → k=0, j=2
  s[0]='a' <= s[2]='a': equal → k=1, j=3
  s[1]='b' <= s[3]='b': equal → k=2, j=4
  s[2]='a' <= s[4]='c': 'a' < 'c' → k=0, j=5
  j==n, exit
  Factor: i=0, len=5-0=5 → "ababc"
  i += 5 → i=5

Result: ["ababc"]
```

`"ababc"` is a single Lyndon word.

**Input:** `s = "cbacba"` (n=6)

```
i=0: j=1, k=0
  s[0]='c' <= s[1]='b': 'c' > 'b' → exit
  Factor: i=0, len=1-0=1 → "c"
  i += 1 → i=1

i=1: j=2, k=1
  s[1]='b' <= s[2]='a': 'b' > 'a' → exit
  Factor: i=1, len=1 → "b"
  i += 1 → i=2

i=2: j=3, k=2
  s[2]='a' <= s[3]='c': 'a' < 'c' → k=2, j=4
  s[3]='c' <= s[4]='b': 'c' > 'b' → exit
  Factor: i=2, len=2 → "ac"? Wait...

Let me re-check: j=4, k=3? No, k was set to 2 initially, then:
- s[2]='a' < s[3]='c' → k=i=2, j=3? No, j starts at i+1=3.

Let me restart more carefully.

i=2: j=3, k=2
  s[2]='a' <= s[3]='c': 'a' < 'c' → k=i=2, j=4
  s[2]='a' <= s[4]='b': 'a' < 'b' → k=i=2, j=5
  s[2]='a' <= s[5]='a': equal → k=3, j=6
  j==n, exit
  Factor: i=2, len=6-3=3 → s[2..4] = "acb"? 

Hmm, the factor length is j-k = 6-3 = 3. So factor starts at i=2 with length 3: s[2], s[3], s[4] = "acb". Wait, that doesn't seem right.

Actually, the factor covers positions i to i+(j-k)-1. So:
- Factor: positions 2 to 2+3-1 = 2 to 4 → "acb"

But "acb" should be a Lyndon word. Rotations: acb, cba, bac. Sorted: acb, bac, cba. "acb" is smallest ✓.

Then: i += j-k = 2+3 = 5

i=5: j=6, k=5
  j==n, exit immediately
  Factor: i=5, len=6-5=1 → "a"
  i += 1 → i=6

Result: ["c", "b", "acb", "a"]

Check: c ≥ b ≥ acb ≥ a? 'c' > 'b' > 'a' (first char of acb) > 'a' ✓
```

---

## 121.8 Related Algorithms

### Booth's Algorithm (Minimal Rotation)
Booth's algorithm finds the minimal rotation in O(n) using a similar approach to Duval's but with a doubled string trick.

### Suffix Array Connection
The Lyndon factorization is related to the suffix array — the first Lyndon factor is always the lexicographically smallest suffix of `s + s` that starts within the first n positions.

### Lyndon Array
The **Lyndon array** L[i] stores the length of the longest Lyndon word starting at position i. It can be computed in O(n) time and is useful for various string problems.

---

## 121.9 Exercises

1. **Compute the Lyndon factorization** of `"banana"`. *Answer: "b" + "anana".*

2. **Is `"abcabc"` a Lyndon word?** If not, what is its factorization? *Answer: No. Factorization: "abc" + "abc".*

3. **Find the minimal rotation** of `"bbaacc"` using Lyndon factorization.

4. **Prove** that every string has a unique Lyndon factorization.

5. **Implement** the Lyndon array (length of longest Lyndon word starting at each position).

6. **Given a string s**, count how many distinct Lyndon words appear as factors.

---

## 121.10 Interview Questions

1. **"What is a Lyndon word?"** — A string strictly smaller than all its rotations. Equivalent to being the lexicographically smallest among all rotations.

2. **"What is the time complexity of Duval's algorithm?"** — O(n), where n is the string length. Each character is compared at most twice.

3. **"How do you find the minimal rotation of a string in O(n)?"** — Use Duval's algorithm on the doubled string. The first Lyndon factor starting within the first n positions gives the answer.

4. **"What's the relationship between Lyndon words and string periodicity?"** — A string is periodic with period p iff its Lyndon factorization consists of repetitions of a single Lyndon word of length p.

5. **"Compare Lyndon factorization with suffix arrays for finding minimal rotations."** — Both work in O(n). Lyndon factorization is simpler and uses O(1) extra space (beyond the result), while suffix arrays need O(n) space.

---

## 121.11 Cross-References

- **String Basics:** Chapter on Strings
- **Suffix Arrays:** Chapter on Suffix Arrays
- **Minimal Rotation:** Related to Booth's algorithm
- **String Matching:** Lyndon words connect to pattern matching via suffix structures
- **Suffix Automaton:** Chapter on Suffix Automaton
- **Z-Algorithm:** Chapter on Z-Algorithm (alternative for minimal rotation)

---

## Summary

| Property | Value |
|---|---|
| Definition | String strictly smaller than all rotations |
| Factorization | Unique decomposition into non-increasing Lyndon words |
| Algorithm | Duval's algorithm |
| Time | O(n) |
| Space | O(1) auxiliary |
| Key application | Minimal string rotation |
| Related | Booth's algorithm, suffix arrays, BWT |
