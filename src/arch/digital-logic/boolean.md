# Boolean Algebra

## Overview

Boolean algebra is the mathematical foundation of digital logic. It deals with variables that have two values (TRUE/FALSE or 1/0) and operations on them. Every digital circuit can be described and analyzed using Boolean algebra.

## Fundamental Laws

### Basic Operations

| Operation | Symbol | Expression | Result |
|-----------|--------|------------|--------|
| **AND** | · or ∧ | A · B | 1 only if both A and B are 1 |
| **OR** | + or ∨ | A + B | 1 if either A or B (or both) is 1 |
| **NOT** | ' or ¬ | A' | Inverts A (1→0, 0→1) |

### Truth Tables

**AND Gate:**
```
A | B | A·B
0 | 0 |  0
0 | 1 |  0
1 | 0 |  0
1 | 1 |  1
```

**OR Gate:**
```
A | B | A+B
0 | 0 |  0
0 | 1 |  1
1 | 0 |  1
1 | 1 |  1
```

**NOT Gate:**
```
A | A'
0 |  1
1 |  0
```

## Boolean Laws

### Identity Laws
```
A + 0 = A
A · 1 = A
```

### Null Laws
```
A + 1 = 1
A · 0 = 0
```

### Complement Laws
```
A + A' = 1
A · A' = 0
```

### Idempotent Laws
```
A + A = A
A · A = A
```

### Commutative Laws
```
A + B = B + A
A · B = B · A
```

### Associative Laws
```
(A + B) + C = A + (B + C)
(A · B) · C = A · (B · C)
```

### Distributive Laws
```
A · (B + C) = A·B + A·C
A + (B · C) = (A + B) · (A + C)
```

### De Morgan's Theorems

**Critical for interviews:**
```
(A · B)' = A' + B'
(A + B)' = A' · B'
```

**In words**: The complement of a product equals the sum of complements. The complement of a sum equals the product of complements.

**Application**: NAND gate = OR gate with inverted inputs. NOR gate = AND gate with inverted inputs.

## Simplification Examples

### Example 1: Simplify F = A·B + A·B'

```
F = A·B + A·B'
F = A·(B + B')        [Distributive]
F = A·1                [Complement: B+B'=1]
F = A                  [Identity: A·1=A]
```

### Example 2: Simplify F = A·B + A'·C + B·C

```
F = A·B + A'·C + B·C
F = A·B + A'·C + B·C·(A + A')   [Complement: A+A'=1]
F = A·B + A'·C + A·B·C + A'·B·C [Distributive]
F = A·B·(1 + C) + A'·C·(1 + B)  [Factor]
F = A·B + A'·C                   [Null: 1+C=1, 1+B=1]
```

### Example 3: Using De Morgan's

Simplify F = (A·B)' + A

```
F = (A·B)' + A
F = A' + B' + A        [De Morgan: (A·B)'=A'+B']
F = (A' + A) + B'      [Associative]
F = 1 + B'             [Complement: A'+A=1]
F = 1                  [Null: 1+anything=1]
```

## Canonical Forms

### Sum of Products (SOP)

Each term is a product (AND) of literals, terms are summed (OR):

```
F = A·B·C' + A·B'·C + A'·B·C'
```

### Product of Sums (POS)

Each term is a sum (OR) of literals, terms are multiplied (AND):

```
F = (A+B+C') · (A+B'+C) · (A'+B+C')
```

### Minterms and Maxterms

| Notation | Form | Value |
|----------|------|-------|
| **Minterm (m)** | Product term where F=1 | A·B·C' (when A=1,B=1,C=0) |
| **Maxterm (M)** | Sum term where F=0 | A+B'+C (when A=0,B=1,C=0) |

## Karnaugh Maps (K-Maps)

K-Maps provide a visual method for simplifying Boolean expressions:

### 3-Variable K-Map

```
        BC
AB    00  01  11  10
 0  |  0 | 1 | 1 | 0 |
 1  |  1 | 1 | 1 | 1 |
```

Groups of 1, 2, 4, or 8 adjacent cells simplify the expression.

## Interview Questions

1. **Q: State De Morgan's theorems.**
   A: (A·B)' = A' + B' and (A + B)' = A' · B'. The complement of a product is the sum of complements; the complement of a sum is the product of complements.

2. **Q: How do you implement XOR using basic gates?**
   A: XOR = A·B' + A'·B = (A+B)·(A·B)'. Requires AND, OR, and NOT gates.

3. **Q: What is the difference between SOP and POS?**
   A: SOP (Sum of Products): OR of AND terms (each term selects rows where F=1). POS (Product of Sums): AND of OR terms (each term selects rows where F=0). SOP is more intuitive; POS can be more efficient for certain functions.

4. **Q: What is a K-Map used for?**
   A: Karnaugh Maps visually simplify Boolean expressions by grouping adjacent 1s (or 0s). Adjacent cells differ by one variable, allowing elimination. Groups must be powers of 2 (1, 2, 4, 8).

## Common Mistakes

- Confusing AND (·) with OR (+) in expressions
- Forgetting that A + A = A (idempotent, not 2A)
- Not applying De Morgan's correctly (negate each variable AND change operator)
- Making K-Map groups that aren't powers of 2
- Confusing minterms (where F=1) with maxterms (where F=0)

## Summary

Boolean algebra is the mathematical language of digital circuits. Key operations: AND, OR, NOT. Key laws: De Morgan's, distributive, complement. Simplification reduces circuit complexity. K-Maps provide visual simplification.

## Cross-References

- [Digital Logic Overview](README.md)
- [Logic Gates](gates.md) — Physical implementation
- [Combinational Circuits](combinational.md) — Applying Boolean algebra
