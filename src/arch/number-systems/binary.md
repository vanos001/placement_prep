# Binary Number System

## Overview

Binary (base 2) is the fundamental number system of computing. Every piece of data in a computer — numbers, text, images, instructions — is ultimately represented in binary.

## Binary Basics

Each digit (bit) represents a power of 2:

```
Position:  7    6    5    4    3    2    1    0
Power:     2^7  2^6  2^5  2^4  2^3  2^2  2^1  2^0
Value:     128  64   32   16   8    4    2    1
```

## Binary to Decimal

```
10110101₂ = 1×128 + 0×64 + 1×32 + 1×16 + 0×8 + 1×4 + 0×2 + 1×1
          = 128 + 32 + 16 + 4 + 1
          = 181₁₀
```

## Decimal to Binary

### Method 1: Division by 2

```
181 ÷ 2 = 90  remainder 1
 90 ÷ 2 = 45  remainder 0
 45 ÷ 2 = 22  remainder 1
 22 ÷ 2 = 11  remainder 0
 11 ÷ 2 = 5   remainder 1
  5 ÷ 2 = 2   remainder 1
  2 ÷ 2 = 1   remainder 0
  1 ÷ 2 = 0   remainder 1

Read remainders bottom to top: 10110101₂
```

### Method 2: Subtraction

```
181 - 128 = 53  → bit 7 = 1
 53 - 64  = -11 → bit 6 = 0
 53 - 32  = 21  → bit 5 = 1
 21 - 16  = 5   → bit 4 = 1
  5 - 8   = -3  → bit 3 = 0
  5 - 4   = 1   → bit 2 = 1
  1 - 2   = -1  → bit 1 = 0
  1 - 1   = 0   → bit 0 = 1

Result: 10110101₂
```

## Binary Arithmetic

### Addition

```
  1011  (11)
+ 1101  (13)
------
11000  (24)

Rules:
0 + 0 = 0
0 + 1 = 1
1 + 0 = 1
1 + 1 = 10 (0 carry 1)
1 + 1 + 1 = 11 (1 carry 1)
```

### Subtraction

```
  1101  (13)
- 0101  (5)
------
  1000  (8)

Rules:
0 - 0 = 0
1 - 0 = 1
1 - 1 = 0
0 - 1 = 1 (borrow 1)
```

### Multiplication

```
  101  (5)
× 110  (6)
------
  000  (101 × 0)
 101   (101 × 1, shift left)
101    (101 × 1, shift left)
------
11110  (30)
```

## Binary Representations

### Unsigned Binary

Range for n bits: 0 to 2^n - 1

| Bits | Range |
|------|-------|
| 8 | 0 to 255 |
| 16 | 0 to 65,535 |
| 32 | 0 to 4,294,967,295 |

### Signed Binary (Sign-Magnitude)

MSB is sign bit (0=positive, 1=negative):

```
+5 = 00000101
-5 = 10000101
```

**Problem**: Two representations of zero (+0 and -0).

### Two's Complement

The standard for signed integers. See [Two's Complement](twos-complement.md).

## Binary Coded Decimal (BCD)

Each decimal digit is encoded in 4 bits:

```
92₁₀ = 1001 0010 (BCD)
```

**Use**: Financial calculations (exact decimal representation).

## Binary in Computing

| Data Type | Bits | Range |
|-----------|------|-------|
| **Byte** | 8 | 0-255 (unsigned) |
| **Word** | 16 | 0-65,535 |
| **Double Word** | 32 | 0-4.29 billion |
| **Quad Word** | 64 | 0-18.4 quintillion |

## Interview Questions

1. **Q: Convert 42 to binary.**
   A: 42 ÷ 2 = 21 R0, 21÷2 = 10 R1, 10÷2 = 5 R0, 5÷2 = 2 R1, 2÷2 = 1 R0, 1÷2 = 0 R1. Reading bottom-up: 101010₂. Verification: 32+8+2 = 42.

2. **Q: How many bits are needed to represent 1000?**
   A: 2^9 = 512, 2^10 = 1024. Need 10 bits (range 0-1023). log₂(1000) ≈ 9.97, round up to 10.

3. **Q: What is overflow in binary addition?**
   A: When the result exceeds the representable range. For 8-bit unsigned: 200+100=300 > 255, overflow. For signed: 127+1=128 > 127 (8-bit signed max), overflow.

4. **Q: Why is hexadecimal used in computing?**
   A: Each hex digit maps to exactly 4 binary digits. Hex is more compact (0xFF vs 11111111) and easier to read. Used for memory addresses, MAC addresses, color codes.

## Common Mistakes

- Confusing bit positions (MSB is leftmost, not rightmost)
- Forgetting that 2^n has n+1 bits (100...0)
- Not understanding overflow in fixed-width arithmetic
- Confusing sign-magnitude with two's complement

## Summary

Binary is the foundation of all computer data. Understanding conversions, arithmetic, and representations (unsigned, sign-magnitude, two's complement) is essential. Hex and octal are convenient shorthand for binary.

## Cross-References

- [Number Systems Overview](README.md)
- [Hexadecimal](hex.md) — Compact binary representation
- [Two's Complement](twos-complement.md) — Signed integers
- [Floating Point](floating-point.md) — Real numbers
