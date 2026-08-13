# IEEE 754 Floating-Point Standard

## Overview

**IEEE 754** is the most widely used standard for floating-point arithmetic, defining how real numbers are represented in binary, how arithmetic operations are performed, and how special values (infinity, NaN) are handled. Published in 1985 and updated in 2008 and 2019, it's implemented in virtually every modern processor's floating-point unit.

## Detailed Explanation

### Floating-Point Representation

A floating-point number is represented as:

```
Value = (-1)^sign × mantissa × 2^exponent

Where:
  sign: 0 (positive) or 1 (negative)
  mantissa (significand): a binary fraction, typically 1.xxxxx
  exponent: a biased integer representing the power of 2
```

### IEEE 754 Formats

| Format | Total Bits | Sign | Exponent | Mantissa | Precision | Range |
|--------|-----------|------|----------|----------|-----------|-------|
| **Single (float)** | 32 | 1 | 8 | 23 | ~7 decimal digits | ±3.4×10³⁸ |
| **Double (double)** | 64 | 1 | 11 | 52 | ~15 decimal digits | ±1.8×10³⁰⁸ |
| **Half (fp16)** | 16 | 1 | 5 | 10 | ~3 decimal digits | ±65504 |
| **BFloat16** | 16 | 1 | 8 | 7 | ~2 decimal digits | ±3.4×10³⁸ |
| **Quad (long double)** | 128 | 1 | 15 | 112 | ~34 decimal digits | ±1.2×10⁴⁹³² |

### Single-Precision (32-bit) Layout

```
 31  30      23  22                    0
┌───┬─────────┬─────────────────────────┐
│ S │ Exponent│        Mantissa         │
│1b │  8 bits │        23 bits          │
└───┴─────────┴─────────────────────────┘

S = Sign bit (0 = positive, 1 = negative)
Exponent = biased by 127 (stored value = actual exponent + 127)
Mantissa = implicit leading 1 (normalized: 1.xxxxx...)
```

### Biased Exponent

The exponent uses **biased encoding** to allow easy comparison:

```
Actual exponent: -126 to +127 (for single precision)
Stored (biased): 1 to 254
Bias: 127

Example: actual exponent = 5
  Stored = 5 + 127 = 132 = 10000100₂

Example: actual exponent = -3
  Stored = -3 + 127 = 124 = 01111100₂
```

### Normalized Numbers

Most floating-point numbers are **normalized**:

```
The mantissa has an implicit leading 1:
  Actual mantissa = 1.xxxxxxxx... (23 bits for single)

Example: Represent 6.75 in IEEE 754 single precision

Step 1: Convert to binary
  6.75 = 110.11₂

Step 2: Normalize
  110.11₂ = 1.1011₂ × 2²

Step 3: Extract fields
  Sign = 0 (positive)
  Exponent = 2 + 127 = 129 = 10000001₂
  Mantissa = 10110000000000000000000₂

Step 4: Assemble
  0 10000001 10110000000000000000000
  = 0x40D80000
```

### Special Values

IEEE 754 defines special values for exceptional cases:

```
┌─────────────┬──────────────┬──────────────┬──────────────────────┐
│ Value       │ Sign │ Exp   │ Mantissa     │ Meaning              │
├─────────────┼──────┼───────┼──────────────┼──────────────────────┤
│ +0          │  0   │ 00..0 │ 00..0        │ Positive zero        │
│ -0          │  1   │ 00..0 │ 00..0        │ Negative zero        │
│ Denormalized│  ?   │ 00..0 │ non-zero     │ Very small numbers   │
│ +Infinity   │  0   │ 11..1 │ 00..0        │ Positive infinity    │
│ -Infinity   │  1   │ 11..1 │ 00..0        │ Negative infinity    │
│ NaN         │  ?   │ 11..1 │ non-zero     │ Not a Number         │
│ Normalized  │  ?   │ 1..254│ any          │ Normal numbers       │
└─────────────┴──────┴───────┴──────────────┴──────────────────────┘
```

### Denormalized (Subnormal) Numbers

When the exponent field is all zeros, the number is **denormalized**:

```
Normalized: (-1)^S × 1.mantissa × 2^(exponent - bias)
Denormalized: (-1)^S × 0.mantissa × 2^(1 - bias)

Denormalized numbers:
  - No implicit leading 1
  - Used to represent numbers closer to zero than the smallest normalized number
  - Enable gradual underflow (no sudden jump to zero)
  - Often slower to compute (some CPUs handle them in microcode)
```

### NaN (Not a Number)

NaN represents undefined or unrepresentable results:

```
Operations that produce NaN:
  0 / 0
  ∞ - ∞
  √(-1)
  NaN + anything
  0 × ∞

Two types:
  Quiet NaN (qNaN): MSB of mantissa = 1 → propagates silently
  Signaling NaN (sNaN): MSB of mantissa = 0 → raises exception

NaN properties:
  NaN ≠ NaN (NaN is not equal to anything, including itself!)
  NaN is not >, <, >=, or <= anything
  Any arithmetic with NaN produces NaN
```

### Rounding Modes

IEEE 754 defines five rounding modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Round to nearest, ties to even** | Default; round to nearest, break ties to even | General purpose |
| **Round toward +∞** | Always round up | Interval arithmetic (upper bound) |
| **Round toward -∞** | Always round down | Interval arithmetic (lower bound) |
| **Round toward 0** | Truncate (chop) | Integer conversion |
| **Round to nearest, ties away from 0** | Break ties away from zero | Less common |

```
"Round to nearest, ties to even" examples:
  1.5 → 2 (tie, round to even)
  2.5 → 2 (tie, round to even)
  3.5 → 4 (tie, round to even)
  1.4 → 1 (round down)
  1.6 → 2 (round up)
```

### Arithmetic Operations

```
Addition/Subtraction:
  1. Align exponents (shift smaller number's mantissa right)
  2. Add/subtract mantissas
  3. Normalize result
  4. Round

Multiplication:
  1. Add exponents
  2. Multiply mantissas
  3. Normalize result
  4. Round

Division:
  1. Subtract exponents
  2. Divide mantissas
  3. Normalize result
  4. Round
```

### Precision Comparison

```
Single precision (float):
  32 bits, ~7 decimal digits
  Example: 1.0 + 1e-8 = 1.0 (1e-8 is lost!)

Double precision (double):
  64 bits, ~15 decimal digits
  Example: 1.0 + 1e-15 = 1.000000000000001

Half precision (fp16):
  16 bits, ~3 decimal digits
  Used in machine learning (training, inference)
```

## Examples

### Example 1: Encode 0.15625 in IEEE 754 Single

```
Step 1: Convert to binary
  0.15625 = 0.00101₂

Step 2: Normalize
  0.00101₂ = 1.01₂ × 2^(-3)

Step 3: Extract fields
  Sign = 0
  Exponent = -3 + 127 = 124 = 01111100₂
  Mantissa = 01000000000000000000000₂

Step 4: Assemble
  0 01111100 01000000000000000000000
  = 0x3E200000
```

### Example 2: Decode IEEE 754 Value

```
Given: 0x41200000

Binary: 0 10000010 01000000000000000000000

Sign = 0 (positive)
Exponent = 10000010₂ = 130, actual = 130 - 127 = 3
Mantissa = 1.01₂ (implicit leading 1)

Value = 1.01₂ × 2³ = 1010₂ = 10.0

Verify: 0x41200000 = 10.0f ✓
```

### Example 3: Floating-Point Precision Loss

```c
float a = 1.0f;
float b = 1e-8f;
float c = a + b;

// c = 1.0f (not 1.00000001!)
// 1e-8 is smaller than single precision can distinguish from 1.0

// In double precision:
double a = 1.0;
double b = 1e-8;
double c = a + b;
// c = 1.00000001 (correct!)
```

### Example 4: Comparison Pitfalls

```c
float a = 0.1f + 0.2f;
float b = 0.3f;

if (a == b) {
    printf("Equal\n");  // NOT printed!
} else {
    printf("Not equal\n");  // This prints!
}

// 0.1 + 0.2 = 0.300000011920928955078125 (in single precision)
// 0.3 = 0.2999999932944774627685546875
// They differ!

// Correct comparison:
if (fabs(a - b) < 1e-6f) {
    printf("Equal within tolerance\n");
}
```

### Example 5: NaN Propagation

```c
float x = sqrt(-1.0f);  // x = NaN
float y = x + 5.0f;     // y = NaN
float z = x * 0.0f;     // z = NaN

// Checking for NaN:
if (x != x) {           // NaN != NaN is true!
    printf("x is NaN\n");
}

// Better: use isnan()
if (isnan(x)) {
    printf("x is NaN\n");
}
```

## Interview Questions

### Q1: What is IEEE 754?
**Answer**: IEEE 754 is the standard for floating-point arithmetic that defines how real numbers are encoded in binary (sign, biased exponent, mantissa), special values (±0, ±∞, NaN), rounding modes, and arithmetic operations. It ensures consistent floating-point behavior across different hardware and software platforms.

### Q2: Why does 0.1 + 0.2 ≠ 0.3 in floating point?
**Answer**: Because 0.1, 0.2, and 0.3 cannot be represented exactly in binary (they have infinite repeating binary fractions, like 1/3 in decimal). The closest representable values are approximations, and the rounding errors accumulate. The result is approximately 0.30000000000000004.

### Q3: What is a denormalized number?
**Answer**: A denormalized (subnormal) number has a zero exponent field and a non-zero mantissa. It represents numbers closer to zero than the smallest normalized number by using an implicit leading 0 instead of 1. This enables gradual underflow rather than a sudden jump to zero, preventing certain numerical instabilities.

### Q4: What is NaN and how do you check for it?
**Answer**: NaN (Not a Number) represents undefined results like 0/0 or √(-1). Key property: NaN ≠ NaN (it's not equal to anything, including itself). Check using `isnan(x)` or `x != x`. NaN propagates through arithmetic: any operation with NaN produces NaN.

### Q5: Why use biased exponents?
**Answer**: Biased encoding (stored = actual + bias) allows the exponent to be treated as an unsigned integer for comparison purposes. Positive exponents are larger than negative exponents in the biased representation, so a simple unsigned integer comparison of the bit pattern correctly compares floating-point magnitudes (useful for sorting and min/max operations).

## Common Mistakes

1. **Using `==` to compare floats** — Floating-point rounding errors mean `0.1 + 0.2 != 0.3`. Always use an epsilon-based comparison: `abs(a - b) < epsilon`.
2. **Ignoring denormalized numbers** — Denormals can cause severe performance penalties on some CPUs (handled in microcode). Some applications flush denormals to zero (FTZ/DAZ flags).
3. **Confusing precision with range** — Double precision has more precision (15 vs 7 digits) and more range, but the key difference for most applications is precision.
4. **Forgetting about associativity** — Floating-point addition is NOT associative: `(a + b) + c ≠ a + (b + c)` due to rounding. Compiler optimizations that reorder floating-point operations can change results.
5. **Assuming all platforms give the same result** — While IEEE 754 defines the standard, different rounding implementations and extended precision (80-bit x86) can cause cross-platform differences.

## Summary

| Aspect | Detail |
|--------|--------|
| **Standard** | IEEE 754 (1985, revised 2008/2019) |
| **Single (float)** | 32 bits: 1 sign + 8 exponent + 23 mantissa |
| **Double (double)** | 64 bits: 1 sign + 11 exponent + 52 mantissa |
| **Special Values** | ±0, ±∞, NaN, denormalized numbers |
| **Rounding** | Default: round to nearest, ties to even |
| **Key Pitfall** | 0.1 + 0.2 ≠ 0.3; always use epsilon for comparison |

## Cross-References

- [Floating Point](./floating-point.md) — General floating-point concepts
- [Binary](./binary.md) — Binary number system fundamentals
- [ALU](../cpu/alu.md) — Where floating-point operations execute (FPU)
- [SIMD](../parallelism/simd.md) — Parallel floating-point operations
