# Chapter 136: Gray Code and Advanced Bit Tricks

## Prerequisites
- Bit manipulation basics ([Chapter 112](ch112-hopcroft-karp-blossom.md))
- Number systems and binary representation

## Interview Frequency: ★★

Gray code and bit tricks appear in **Google** and competitive programming. These are the kinds of low-level optimizations that can make solutions elegant and fast.

---

## 136.1 Definition and Motivation

### What is Gray Code?

A **Gray code** (also called **reflected binary code**) is an ordering of binary numbers such that **consecutive values differ in exactly one bit**.

Standard binary: 000, 001, 010, 011, 100, 101, 110, 111
Gray code:      000, 001, 011, 010, 110, 111, 101, 100

Notice: Gray(2)=011 → Gray(3)=010 differ in exactly 1 bit. Standard binary 011 → 100 differ in 3 bits!

### Why Does This Matter?

1. **Hardware**: In digital circuits, changing multiple bits simultaneously can cause glitches. Gray code ensures only one bit changes at a time.
2. **Error detection**: If adjacent values should differ by 1 bit, a multi-bit change indicates an error.
3. **Hamiltonian paths**: Gray code is a Hamiltonian path on the n-dimensional hypercube.
4. **Backtracking**: Enumerate all subsets where consecutive subsets differ by one element.

---

## 136.2 Gray Code Construction

### Formula

The nth Gray code is:
```
G(n) = n XOR (n >> 1)
```

### Why This Works

The XOR with `n >> 1` "reflects" the binary representation. Think of it as:
- The most significant bit stays the same
- Each subsequent bit is XORed with the bit above it

This creates the "reflected" property that ensures only 1 bit changes.

### Step-by-Step

For n = 0 to 7:

| n (binary) | n >> 1 | G(n) = n XOR (n>>1) | G(n) binary |
|---|---|---|---|
| 000 | 000 | 000 | 000 |
| 001 | 000 | 001 | 001 |
| 010 | 001 | 011 | 011 |
| 011 | 001 | 010 | 010 |
| 100 | 010 | 110 | 110 |
| 101 | 010 | 111 | 111 |
| 110 | 011 | 101 | 101 |
| 111 | 011 | 100 | 100 |

### Inverse (Gray → Binary)

To convert Gray code back to binary:
```python
def from_gray(gray):
    result = 0
    while gray:
        result ^= gray
        gray >>= 1
    return result
```

The idea: each bit in the result is the XOR of all bits from the MSB down to that position in the Gray code.

---

## 136.3 Code

**C++**

```cpp
#include <iostream>
#include <vector>

// Convert to Gray code
int toGray(int n) { return n ^ (n >> 1); }

// Convert from Gray code
int fromGray(int gray) {
    int result = 0;
    while (gray) {
        result ^= gray;
        gray >>= 1;
    }
    return result;
}

int main() {
    std::cout << "Gray code sequence (0-7):\n";
    for (int i = 0; i < 8; i++) {
        int gray = toGray(i);
        std::cout << i << " -> " << gray << " (binary: ";
        for (int b = 2; b >= 0; b--) std::cout << ((gray >> b) & 1);
        std::cout << ")\n";
    }
    
    // Verify consecutive differ by 1 bit
    for (int i = 0; i < 7; i++) {
        int diff = toGray(i) ^ toGray(i + 1);
        int bits = __builtin_popcount(diff);
        std::cout << "Gray(" << i << ") ^ Gray(" << i+1 << ") has " << bits << " bit(s)\n";
    }
    
    return 0;
}
```

**Python**

```python
def to_gray(n):
    return n ^ (n >> 1)

def from_gray(gray):
    result = 0
    while gray:
        result ^= gray
        gray >>= 1
    return result

# Generate Gray code sequence
print("Gray code sequence (0-7):")
for i in range(8):
    g = to_gray(i)
    print(f"  {i:03b} -> {g:03b}")

# Verify 1-bit difference
for i in range(7):
    diff = to_gray(i) ^ to_gray(i + 1)
    bits = bin(diff).count('1')
    print(f"Gray({i}) ^ Gray({i+1}) = {diff:03b} ({bits} bit(s))")

# Round-trip verification
for i in range(16):
    assert from_gray(to_gray(i)) == i
print("Round-trip verified for 0-15")
```

**Java**

```java
public class GrayCode {
    static int toGray(int n) { return n ^ (n >> 1); }
    
    static int fromGray(int gray) {
        int result = 0;
        while (gray != 0) {
            result ^= gray;
            gray >>= 1;
        }
        return result;
    }
    
    public static void main(String[] args) {
        System.out.println("Gray code sequence (0-7):");
        for (int i = 0; i < 8; i++) {
            int g = toGray(i);
            System.out.printf("  %3s -> %3s%n", 
                Integer.toBinaryString(i), Integer.toBinaryString(g));
        }
        
        // Verify
        for (int i = 0; i < 7; i++) {
            int diff = toGray(i) ^ toGray(i + 1);
            int bits = Integer.bitCount(diff);
            System.out.printf("Gray(%d) ^ Gray(%d) has %d bit(s)%n", i, i+1, bits);
        }
        
        // Round-trip
        for (int i = 0; i < 16; i++) {
            assert fromGray(toGray(i)) == i;
        }
        System.out.println("Round-trip verified");
    }
}
```

---

## 136.4 Gray Code Applications

### 1. Subset Enumeration

Enumerate all subsets of a set, where consecutive subsets differ by exactly one element:

```python
def gray_subsets(items):
    n = len(items)
    result = []
    for i in range(1 << n):
        g = to_gray(i)
        subset = [items[j] for j in range(n) if (g >> j) & 1]
        result.append(subset)
    return result

# Example: subsets of {a, b, c}
for subset in gray_subsets(['a', 'b', 'c']):
    print(subset)
```

### 2. Hamiltonian Path on Hypercube

The n-bit Gray code is a Hamiltonian path on the n-dimensional hypercube graph. This is useful for:
- Generating all binary strings of length n with minimal changes
- Solving the "Tower of Hanoi" variant
- DNA sequencing optimization

### 3. Digital Communication

Gray code is used in:
- **QAM modulation**: Adjacent signal points differ by 1 bit, minimizing bit error rate
- **Rotary encoders**: Position sensors that need to avoid multi-bit transitions
- **Analog-to-digital converters**: Reduce conversion errors

---

## 136.5 Advanced Bit Tricks

### Essential Bit Operations

| Trick | Expression | Purpose | Example |
|---|---|---|---|
| Clear lowest set bit | `x & (x-1)` | Remove rightmost 1 | `1100 & 1011 = 1000` |
| Isolate lowest set bit | `x & (-x)` | Get rightmost 1 | `1100 & 0100 = 0100` |
| Set bit i | `x \| (1 << i)` | Turn on bit i | `1010 \| 0001 = 1011` |
| Clear bit i | `x & ~(1 << i)` | Turn off bit i | `1011 & 1110 = 1010` |
| Toggle bit i | `x ^ (1 << i)` | Flip bit i | `1010 ^ 0001 = 1011` |
| Check bit i | `(x >> i) & 1` | Test bit i | `(1010 >> 1) & 1 = 1` |
| Count set bits | `__builtin_popcount(x)` | Popcount | `1010 → 2` |
| Parity | `__builtin_parity(x)` | Odd/even bits | `1010 → 0` |
| Swap without temp | `a ^= b; b ^= a; a ^= b` | XOR swap | a=3, b=5 → a=5, b=3 |

### Why `x & (x-1)` Clears the Lowest Set Bit

Consider x = 1100 (12 in decimal):
- x - 1 = 1011 (11)
- x & (x-1) = 1100 & 1011 = 1000 (8)

When you subtract 1 from x, all bits below the lowest set bit become 1, and the lowest set bit becomes 0. The AND operation then clears that bit.

### Why `x & (-x)` Isolates the Lowest Set Bit

Two's complement: -x = ~x + 1. This flips all bits and adds 1, which:
- Flips all bits below the lowest set bit to 0
- Keeps the lowest set bit as 1
- Flips all bits above it

AND with x isolates just that bit.

---

## 136.6 Bit Manipulation Patterns

### Pattern 1: Count Set Bits

```python
def count_bits(x):
    count = 0
    while x:
        x &= x - 1  # Clear lowest set bit
        count += 1
    return count
```

This is O(number of set bits), not O(32).

### Pattern 2: Check Power of Two

```python
def is_power_of_two(x):
    return x > 0 and (x & (x - 1)) == 0
```

A power of two has exactly one set bit. Clearing it gives 0.

### Pattern 3: Generate All Subsets of a Set

```python
def all_subsets(mask):
    """Generate all subsets of the set represented by mask."""
    subset = mask
    while subset:
        yield subset
        subset = (subset - 1) & mask
    yield 0  # Empty set
```

### Pattern 4: Iterate Over All Submasks

```python
def submasks(mask):
    """Iterate over all submasks of mask in decreasing order."""
    sub = mask
    while sub:
        yield sub
        sub = (sub - 1) & mask
    yield 0
```

### Pattern 5: Find the Position of the Only Set Bit

```python
def only_bit_position(x):
    """Assumes x is a power of 2. Returns position of the set bit."""
    pos = 0
    while x > 1:
        x >>= 1
        pos += 1
    return pos
```

Or use `x.bit_length() - 1` in Python.

### Pattern 6: Turn Off the Rightmost Set Bit

```python
x = x & (x - 1)
```

### Pattern 7: Turn On the Rightmost Unset Bit

```python
x = x | (x + 1)
```

### Pattern 8: Isolate the Rightmost Unset Bit

```python
x = ~x & (x + 1)
```

---

## 136.7 Bit Tricks in Competitive Programming

### Fast Modulo for Powers of Two

```python
# x % 2^n is the same as x & (2^n - 1)
remainder = x & ((1 << n) - 1)
```

### Check if Two Numbers Have Opposite Signs

```python
def opposite_signs(a, b):
    return (a ^ b) < 0
```

The sign bit is 1 if they differ.

### Compute Absolute Value Without Branching

```python
def abs_no_branch(x):
    mask = x >> 31  # All 1s if negative, all 0s if positive
    return (x + mask) ^ mask
```

### Round Up to Next Power of Two

```python
def next_power_of_two(x):
    x -= 1
    x |= x >> 1
    x |= x >> 2
    x |= x >> 4
    x |= x >> 8
    x |= x >> 16
    return x + 1
```

---

## 136.8 Dry Run: Gray Code for Subset Enumeration

Given items = ['a', 'b', 'c'] (n=3):

| i | Gray(i) | Binary | Subset |
|---|---|---|---|
| 0 | 0 | 000 | {} |
| 1 | 1 | 001 | {a} |
| 2 | 3 | 011 | {a, b} |
| 3 | 2 | 010 | {b} |
| 4 | 6 | 110 | {b, c} |
| 5 | 7 | 111 | {a, b, c} |
| 6 | 5 | 101 | {a, c} |
| 7 | 4 | 100 | {c} |

Notice: consecutive subsets differ by exactly one element. This is the Gray code property applied to subset enumeration.

---

## 136.9 Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| Convert to Gray | O(1) | O(1) |
| Convert from Gray | O(log n) | O(1) |
| Generate all Gray codes | O(2^n) | O(2^n) |
| Count set bits (Brian Kernighan) | O(k) where k = set bits | O(1) |
| Check power of two | O(1) | O(1) |

---

## 136.10 Exercises

### Conceptual

1. **Why does Gray code use XOR with `n >> 1`?** Prove that consecutive Gray codes differ by exactly one bit.
2. **What's the relationship between Gray code and the hypercube?** How does the Gray code traverse the hypercube?
3. **Why is `x & (x-1)` useful for counting set bits?** What's the time complexity?

### Implementation

4. **Implement Gray code conversion** (both directions) and verify the round-trip property for 0-15.
5. **Generate all subsets** using Gray code ordering and verify that consecutive subsets differ by one element.
6. **Implement Brian Kernighan's bit counting** and compare its performance with `__builtin_popcount`.

### Challenge

7. **Construct a Gray code that is also a cyclic code** (first and last values also differ by one bit).
8. **Use Gray code to solve the "Revolving Door" problem**: Generate all n-choose-k subsets such that consecutive subsets differ by two elements (one added, one removed).

---

## 136.11 Interview Questions

1. **Q**: What is Gray code and why is it useful?
   **A**: An ordering of binary numbers where consecutive values differ by exactly one bit. Used in hardware to prevent glitches, in error correction, and for efficient subset enumeration.

2. **Q**: How do you convert a number to Gray code?
   **A**: `G(n) = n XOR (n >> 1)`. The XOR with the right-shifted value creates the single-bit-change property.

3. **Q**: How do you convert Gray code back to binary?
   **A**: Accumulate XOR from MSB to LSB: `result = 0; while gray: result ^= gray; gray >>= 1`.

4. **Q**: How would you check if a number is a power of two?
   **A**: `x > 0 && (x & (x-1)) == 0`. A power of two has exactly one set bit; clearing it gives zero.

5. **Q**: What does `x & (-x)` compute?
   **A**: It isolates the lowest set bit of x. This is because -x in two's complement flips all bits and adds 1, which isolates the rightmost 1.

6. **Q**: How would you generate all subsets of a set using bit manipulation?
   **A**: For an n-element set, iterate i from 0 to 2^n - 1. Each bit in i represents whether an element is in the subset. For Gray code ordering, use `to_gray(i)` instead of `i`.

---

## 136.12 Cross-References

- **Bit Manipulation Basics**: [Chapter 112](ch112-hopcroft-karp-blossom.md) — fundamental bit operations
- **Bitmask DP**: [Chapter 113](ch113-profile-dp.md) — using bits for state representation
- **Subset Enumeration**: [Chapter 114](ch114-probability-dp.md) — systematic subset generation
- **Graph Theory**: [Chapter 120](ch120-bwt-fmindex.md) — hypercube and Hamiltonian paths
- **Error Correcting Codes**: [Chapter 155](ch155-advanced-graph-theory.md) — Gray code in coding theory
