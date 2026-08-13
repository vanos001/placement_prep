# Chapter 135: De Bruijn Sequences and Morton Codes

## Prerequisites
- Bit manipulation (Chapter 125)
- Binary representation basics
- Spatial data structures (optional, for Morton codes)

## Interview Frequency: ★

These are advanced bit tricks for specialized applications. While rarely asked directly, understanding them demonstrates deep systems knowledge at companies like **Google**, **NVIDIA**, and **game studios**.

---

## 135.1 De Bruijn Sequences

### Definition

A **De Bruijn sequence** B(k, n) is a cyclic string over an alphabet of size *k* that contains every possible length-*n* string over that alphabet exactly once as a contiguous substring.

For binary (k=2), B(2, 3) = "00010111" contains all 3-bit strings: 000, 001, 010, 101, 011, 111, 110, 100.

### Motivation

In competitive programming and systems programming, we often need to find the **index of the least significant set bit** (or most significant set bit) of an integer. The naive approach uses a loop. De Bruijn sequences enable an **O(1) lookup** with a small precomputed table.

### Intuition

A De Bruijn sequence of order *n* over binary has the property that if you take any *n* consecutive bits (wrapping around), you get a unique binary number. This means multiplying by a carefully chosen De Bruijn constant and shifting gives a unique index for each bit position.

### Formal Explanation

For a 32-bit integer, we use B(2, 5) — a sequence where every 5-bit pattern appears exactly once. The magic constant `0x077CB531` is derived from such a sequence.

**Algorithm to find lowest set bit index:**

1. Isolate the lowest set bit: `x & -x` (gives a power of 2)
2. Multiply by the De Bruijn constant: `(x & -x) * 0x077CB531`
3. Right-shift by 27 bits to get a 5-bit index
4. Look up the result in a precomputed 32-entry table

**Why it works:** Each power of 2, when multiplied by the De Bruijn constant, produces a value whose top 5 bits are unique. The table maps these unique 5-bit values back to the original bit position.

### Step-by-Step Walkthrough

Let's trace `x = 40` (binary: `00000000 00000000 00000000 00101000`):

1. `x & -x = 8` (isolates bit 3, which is the lowest set bit)
2. `8 * 0x077CB531 = 0x03BE6988`
3. `0x03BE6988 >> 27 = 0x03BE6988 / 134217728 = 3` (top 5 bits = `00011`)
4. `table[3] = 3` ✓ (bit 3 is indeed the lowest set bit in 40)

### Generating a De Bruijn Sequence

```cpp
#include <iostream>
#include <vector>
#include <string>

// Generate De Bruijn sequence B(k, n)
std::string deBruijn(int k, int n) {
    std::string alphabet = "0123456789";
    std::vector<int> a(k * n, 0);
    std::string seq;
    
    std::function<void(int, int)> db = [&](int t, int p) {
        if (t > n) {
            if (n % p == 0) {
                for (int i = 1; i <= p; i++)
                    seq += alphabet[a[i]];
            }
        } else {
            a[t] = a[t - p];
            db(t + 1, p);
            for (int j = a[t - p] + 1; j < k; j++) {
                a[t] = j;
                db(t + 1, t);
            }
        }
    };
    
    db(1, 1);
    return seq;
}

int main() {
    std::string seq = deBruijn(2, 5);
    std::cout << "De Bruijn B(2,5): " << seq << "\n";
    std::cout << "Length: " << seq.size() << " (expected 32)\n";
    return 0;
}
```

### O(1) Lowest Set Bit Lookup

```cpp
#include <iostream>
#include <cstdint>

// Find index of lowest set bit using De Bruijn sequence
int lowestBitIndex(uint32_t x) {
    if (x == 0) return -1;
    static const int table[32] = {
        0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8,
        31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9
    };
    return table[((uint32_t)(x & -x) * 0x077CB531U) >> 27];
}

int main() {
    for (uint32_t x : {1, 2, 4, 8, 16, 128, 1024})
        std::cout << "Lowest bit of " << x << ": index " << lowestBitIndex(x) << "\n";
    return 0;
}
```

### Python Implementation

```python
def lowest_bit_index(x: int) -> int:
    """Find index of lowest set bit using De Bruijn sequence."""
    if x == 0:
        return -1
    table = [
        0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8,
        31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9
    ]
    # Isolate lowest set bit, multiply by De Bruijn constant, shift
    isolated = x & (-x)
    index = (isolated * 0x077CB531) >> 27
    return table[index]

# Demonstration
for x in [1, 2, 4, 8, 16, 128, 1024, 40]:
    print(f"Lowest bit of {x}: index {lowest_bit_index(x)}")
```

### Java Implementation

```java
public class DeBruijnBit {
    private static final int[] TABLE = {
        0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8,
        31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9
    };
    
    public static int lowestBitIndex(int x) {
        if (x == 0) return -1;
        return TABLE[(int)(((long)(x & -x) * 0x077CB531L) >>> 27)];
    }
    
    public static void main(String[] args) {
        int[] tests = {1, 2, 4, 8, 16, 128, 1024};
        for (int x : tests) {
            System.out.printf("Lowest bit of %d: index %d%n", x, lowestBitIndex(x));
        }
    }
}
```

### Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| Lowest bit index | O(1) | O(1) — 32-entry table |
| Generate sequence | O(k^n) | O(k^n) |
| Standard `__builtin_ctz` | O(1) | N/A (hardware) |

> **Note:** Modern compilers provide `__builtin_ctz` (GCC/Clang) or `_BitScanForward` (MSVC) which use hardware instructions. The De Bruijn technique is useful when hardware support is unavailable or when you need a portable solution.

---

## 135.2 Morton Codes (Z-Order Curve)

### Definition

A **Morton code** maps multi-dimensional coordinates to a one-dimensional value by **interleaving the bits** of each coordinate. The resulting ordering creates a **Z-order curve** (also called a Morton curve), a space-filling curve that preserves spatial locality.

### Motivation

When working with 2D spatial data (e.g., game maps, geographic data, image processing), we often need to:
- Store 2D points in a 1D data structure (array, B-tree)
- Perform range queries efficiently
- Cache spatial data with good locality

Morton codes provide a simple, fast way to convert 2D coordinates to 1D while preserving nearby-ness.

### Intuition

Imagine a 2×2 grid. Label each cell by interleaving its row and column bits:

```
Column:  0  1
Row 0:   0  1
Row 1:   2  3
```

For a 4×4 grid:
```
 0  1  4  5
 2  3  6  7
 8  9 12 13
10 11 14 15
```

This "Z" pattern recurs at every scale, creating a fractal-like space-filling curve.

### Formal Explanation

Given coordinates (x, y), the Morton code is computed by interleaving their binary representations:

```
x = x₂ x₁ x₀  (binary)
y = y₂ y₁ y₀  (binary)
z = y₂ x₂ y₁ x₁ y₀ x₀  (interleaved)
```

For example, (3, 5):
```
x = 3  = 011
y = 5  = 101
z = 100111 = 39 (interleave: y₂x₂y₁x₁y₀x₀ = 1·0·0·1·1·1)
```

### Step-by-Step Walkthrough

**Encoding (3, 5):**
1. x = 3 = `011` in binary
2. y = 5 = `101` in binary
3. Interleave bits: take y₂=1, x₂=0, y₁=0, x₁=1, y₀=1, x₁=1
4. Result: `100111` = 39

**Decoding 39 back to (3, 5):**
1. 39 = `100111` in binary
2. Separate even-positioned bits (x): `011` = 3
3. Separate odd-positioned bits (y): `101` = 5

### C++ Implementation

```cpp
#include <iostream>
#include <cstdint>
#include <vector>
#include <algorithm>

// Spread bits of a 16-bit integer into even bit positions
uint32_t spreadBits(uint32_t x) {
    x = (x | (x << 8)) & 0x00FF00FF;
    x = (x | (x << 4)) & 0x0F0F0F0F;
    x = (x | (x << 2)) & 0x33333333;
    x = (x | (x << 1)) & 0x55555555;
    return x;
}

// Compact bits from even positions back to contiguous
uint32_t compactBits(uint32_t x) {
    x = x & 0x55555555;
    x = (x | (x >> 1)) & 0x33333333;
    x = (x | (x >> 2)) & 0x0F0F0F0F;
    x = (x | (x >> 4)) & 0x00FF00FF;
    x = (x | (x >> 8)) & 0x0000FFFF;
    return x;
}

uint32_t mortonEncode(uint32_t x, uint32_t y) {
    return spreadBits(x) | (spreadBits(y) << 1);
}

void mortonDecode(uint32_t code, uint32_t &x, uint32_t &y) {
    x = compactBits(code);
    y = compactBits(code >> 1);
}

// Naive bit-by-bit encoding (easier to understand)
uint32_t mortonEncodeNaive(uint32_t x, uint32_t y) {
    uint32_t z = 0;
    for (int i = 0; i < 16; i++) {
        z |= ((x & (1 << i)) << i) | ((y & (1 << i)) << (i + 1));
    }
    return z;
}

int main() {
    uint32_t x = 3, y = 5;
    uint32_t code = mortonEncode(x, y);
    std::cout << "Morton(" << x << ", " << y << ") = " << code << "\n";
    
    uint32_t dx, dy;
    mortonDecode(code, dx, dy);
    std::cout << "Decoded: (" << dx << ", " << dy << ")\n";
    
    // Show Z-order for a 4x4 grid
    std::cout << "\n4x4 Z-order:\n";
    for (int r = 0; r < 4; r++) {
        for (int c = 0; c < 4; c++)
            std::cout << mortonEncode(c, r) << "\t";
        std::cout << "\n";
    }
    
    return 0;
}
```

### Python Implementation

```python
def spread_bits(x: int) -> int:
    """Spread bits of x into even bit positions."""
    x = (x | (x << 8)) & 0x00FF00FF
    x = (x | (x << 4)) & 0x0F0F0F0F
    x = (x | (x << 2)) & 0x33333333
    x = (x | (x << 1)) & 0x55555555
    return x

def compact_bits(x: int) -> int:
    """Compact bits from even positions back to contiguous."""
    x = x & 0x55555555
    x = (x | (x >> 1)) & 0x33333333
    x = (x | (x >> 2)) & 0x0F0F0F0F
    x = (x | (x >> 4)) & 0x00FF00FF
    x = (x | (x >> 8)) & 0x0000FFFF
    return x

def morton_encode(x: int, y: int) -> int:
    """Encode (x, y) to Morton code (Z-order)."""
    return spread_bits(x) | (spread_bits(y) << 1)

def morton_decode(code: int) -> tuple:
    """Decode Morton code back to (x, y)."""
    return compact_bits(code), compact_bits(code >> 1)

# Demonstration
x, y = 3, 5
code = morton_encode(x, y)
print(f"Morton({x}, {y}) = {code}")
print(f"Decoded: {morton_decode(code)}")

# 4x4 Z-order grid
print("\n4x4 Z-order:")
for r in range(4):
    row = [morton_encode(c, r) for c in range(4)]
    print("\t".join(map(str, row)))
```

### Java Implementation

```java
public class MortonCode {
    
    public static int spreadBits(int x) {
        x = (x | (x << 8)) & 0x00FF00FF;
        x = (x | (x << 4)) & 0x0F0F0F0F;
        x = (x | (x << 2)) & 0x33333333;
        x = (x | (x << 1)) & 0x55555555;
        return x;
    }
    
    public static int compactBits(int x) {
        x = x & 0x55555555;
        x = (x | (x >>> 1)) & 0x33333333;
        x = (x | (x >>> 2)) & 0x0F0F0F0F;
        x = (x | (x >>> 4)) & 0x00FF00FF;
        x = (x | (x >>> 8)) & 0x0000FFFF;
        return x;
    }
    
    public static int encode(int x, int y) {
        return spreadBits(x) | (spreadBits(y) << 1);
    }
    
    public static int[] decode(int code) {
        return new int[]{ compactBits(code), compactBits(code >>> 1) };
    }
    
    public static void main(String[] args) {
        int code = encode(3, 5);
        System.out.println("Morton(3, 5) = " + code);
        int[] xy = decode(code);
        System.out.printf("Decoded: (%d, %d)%n", xy[0], xy[1]);
    }
}
```

### Morton Code Applications

| Application | Description |
|---|---|
| **Sparse segment trees** | Map 2D points to 1D for efficient storage |
| **Range queries** | Find all points in a rectangular region |
| **GPU texture tiling** | Improve cache locality for 2D textures |
| **Database indexing** | Spatial indexing in databases (e.g., PostGIS) |
| **Image processing** | Quadtree decomposition |
| **Game engines** | Spatial hashing for collision detection |

### Z-Order Curve Properties

| Property | Value |
|---|---|
| Dimension | Maps ℝ² → ℝ¹ |
| Locality | Preserves proximity (not perfect, but good) |
| Self-similar | Fractal structure at every scale |
| Bit complexity | O(B) for B-bit coordinates |
| Cache-friendly | Sequential Morton order ≈ cache lines |

### Complexity Analysis

| Operation | Naive | Bit-manipulation |
|---|---|---|
| Encode | O(B) per coordinate | O(log B) with magic numbers |
| Decode | O(B) per coordinate | O(log B) with magic numbers |
| Compare two codes | O(1) | O(1) |
| Space | O(1) per point | O(1) per point |

Where B is the number of bits per coordinate (typically 16 or 32).

---

## 135.3 Related Concepts

### Hilbert Curve

Unlike Morton/Z-order, the **Hilbert curve** is a continuous space-filling curve with better locality preservation. It's more complex to compute but avoids the "jumping" behavior of Z-order.

### Bit Interleaving in Practice

Bit interleaving appears in:
- **GPUDirect**: NVIDIA's memory layout optimization
- **Z-index in databases**: PostgreSQL's GiST indexes
- **Hash functions**: Some hash functions use bit interleaving

---

## Exercises

1. **Easy:** What is the Morton code for (7, 3)? Verify by decoding.
2. **Medium:** Implement a function that finds the **most significant set bit** index using a De Bruijn-like approach.
3. **Medium:** Given a list of 2D points, sort them by Morton code and verify that nearby points tend to cluster.
4. **Hard:** Implement a Morton-code-based range query: given a bounding box [x1,x2] × [y1,y2], find all points in the box using Z-order curve properties.
5. **Hard:** Extend Morton encoding to 3D (interleaving x, y, z bits). What changes in the bit manipulation?

---

## Interview Questions

1. **Q:** How would you efficiently find all points within a rectangle in a 2D grid stored in a 1D array?
   **A:** Use Morton codes to map 2D→1D while preserving spatial locality. Points in a rectangle will cluster in Morton order, allowing efficient range queries.

2. **Q:** What is the advantage of a De Bruijn sequence over a simple loop for finding the lowest set bit?
   **A:** O(1) with a fixed-size lookup table vs O(B) loop. The De Bruijn property guarantees uniqueness of the hash, making the table lookup correct.

3. **Q:** When would you choose a Hilbert curve over a Z-order (Morton) curve?
   **A:** When locality preservation is critical (e.g., database range queries). Hilbert avoids Z-order's "jumping" but is more expensive to compute.

---

## Summary

| Technique | What it does | Complexity | Key Use |
|---|---|---|---|
| De Bruijn sequence | Unique substring property | O(1) bit index lookup | Fast bit scanning |
| Morton code | Interleave bits of coordinates | O(1) encode/decode | Spatial indexing |
| Z-order curve | Space-filling curve via Morton | O(n log n) sort by space | Range queries |

## Cross-References
- Bit manipulation fundamentals: Chapter 125
- Segment trees: Chapter 52
- Spatial data structures: Chapter 56
- Hashing: Chapter 33
