# Hexadecimal Number System

## Overview

Hexadecimal (base 16) is a compact representation of binary data. Each hex digit represents exactly 4 binary bits, making it the preferred notation for memory addresses, machine code, MAC addresses, and color values.

## Hex Digits

| Hex | Decimal | Binary |
|-----|---------|--------|
| 0 | 0 | 0000 |
| 1 | 1 | 0001 |
| 2 | 2 | 0010 |
| 3 | 3 | 0011 |
| 4 | 4 | 0100 |
| 5 | 5 | 0101 |
| 6 | 6 | 0110 |
| 7 | 7 | 0111 |
| 8 | 8 | 1000 |
| 9 | 9 | 1001 |
| A | 10 | 1010 |
| B | 11 | 1011 |
| C | 12 | 1100 |
| D | 13 | 1101 |
| E | 14 | 1110 |
| F | 15 | 1111 |

## Conversions

### Hex to Binary

Each hex digit → 4 binary bits:

```
0x3A7F = 0011 1010 0111 1111
         3    A    7    F
```

### Binary to Hex

Group binary into 4-bit nibbles (from right):

```
11010110₂ = 1101 0110 = 0xD6
```

### Hex to Decimal

```
0x1A3 = 1×16² + 10×16¹ + 3×16⁰
      = 256 + 160 + 3
      = 419₁₀
```

### Decimal to Hex

```
419 ÷ 16 = 26  remainder 3
 26 ÷ 16 = 1   remainder 10 (A)
  1 ÷ 16 = 0   remainder 1

Result: 0x1A3
```

## Hex in Computing

| Use | Example | Description |
|-----|---------|-------------|
| **Memory addresses** | 0x7FFE0000 | 32-bit address space |
| **MAC address** | 00:1A:2B:3C:4D:5E | 48-bit hardware address |
| **IPv6** | 2001:0db8::1 | 128-bit address |
| **Colors** | #FF5733 | RGB (3 bytes) |
| **Machine code** | 0xE59FF018 | ARM instruction |
| **Unicode** | U+0041 | Character 'A' |
| **Error codes** | 0xDEADBEEF | Debug markers |

## Hex Arithmetic

### Addition

```
  0x1A
+ 0x2F
------
  0x49

A(10) + F(15) = 25 = 0x19 (9 carry 1)
1 + 2 + 1 = 4
```

### Bitwise Operations

```python
# Common hex operations
0xFF & 0x0F  # = 0x0F (mask lower nibble)
0xFF | 0xF0  # = 0xFF (set bits)
0xFF ^ 0x0F  # = 0xF0 (toggle bits)
~0xFF        # = 0x00 (for 8-bit)
0x01 << 4    # = 0x10 (shift left)
0x80 >> 4    # = 0x08 (shift right)
```

## Hex Shorthand

| Notation | Meaning |
|----------|---------|
| 0x prefix | C/C++/Python hex literal |
| # prefix | HTML color codes |
| H suffix | Assembly hex literal |
| $ prefix | Some assembly languages |
| \x prefix | String escape sequences |

## Interview Questions

1. **Q: Convert 0xFF to decimal.**
   A: F=15, F=15. 15×16 + 15 = 240 + 15 = 255. Or simply: 0xFF = 11111111₂ = 255.

2. **Q: Why use hex instead of binary?**
   A: Hex is 4× more compact. 0xFF vs 11111111. Each hex digit = exactly 4 bits, so conversion is trivial. Humans can read hex much faster than long binary strings.

3. **Q: What is a MAC address in hex?**
   A: A 48-bit hardware address written as 6 hex pairs: 00:1A:2B:3C:4D:5E. Each pair = 1 byte. Total = 6 bytes = 48 bits.

4. **Q: How do you convert binary 110101101011 to hex?**
   A: Group into 4-bit nibbles from right: 1101 0110 1011. Convert each: D, 6, B. Result: 0xD6B.

5. **Q: What does 0xDEADBEEF mean?**
   A: A common debug marker used in programming to identify uninitialized memory or as a magic number. It's easily recognizable in hex dumps.

## Common Mistakes

- Forgetting that A-F represent 10-15 (not 1-6)
- Not grouping binary into 4-bit nibbles correctly (start from right)
- Confusing 0x prefix (hex) with 0b prefix (binary) or 0o prefix (octal)
- Forgetting that hex is case-insensitive (0xFF = 0xff)

## Summary

Hexadecimal is a compact binary representation (1 hex digit = 4 bits). Used for memory addresses, MAC addresses, colors, and machine code. Conversions between hex and binary are trivial. Understanding hex is essential for low-level programming.

## Cross-References

- [Number Systems Overview](README.md)
- [Binary](binary.md) — Foundation
- [Two's Complement](twos-complement.md) — Signed hex values
- [IEEE 754](ieee754.md) — Floating point in hex
