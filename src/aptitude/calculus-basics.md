# Calculus Basics for Placement Tests

Calculus occasionally appears in quantitative aptitude sections, especially for engineering roles. Focus on differentiation rules, basic integration, and rate-of-change applications.

## Limits

A limit describes the value a function approaches as the input approaches a point.

```
lim(x→a) f(x) = L
```

**Key properties:**

| Property | Rule |
|----------|------|
| Constant | lim(x→a) c = c |
| Linear | lim(x→a) x = a |
| Sum | lim(f + g) = lim f + lim g |
| Product | lim(f · g) = lim f · lim g |
| Quotient | lim(f/g) = lim f / lim g (if lim g ≠ 0) |

**Example:** lim(x→2) (x² - 4) / (x - 2)
```
= lim(x→2) (x+2)(x-2) / (x-2)
= lim(x→2) (x + 2) = 4
```

## Derivatives

The derivative measures the rate of change of a function.

### Basic Differentiation Rules

| Function f(x) | Derivative f'(x) |
|---------------|-------------------|
| xⁿ | n xⁿ⁻¹ |
| c (constant) | 0 |
| eˣ | eˣ |
| ln x | 1/x |
| sin x | cos x |
| cos x | -sin x |

### Rules

```
Sum rule:    (f + g)' = f' + g'
Product rule: (fg)' = f'g + fg'
Quotient rule: (f/g)' = (f'g - fg') / g²
Chain rule:  d/dx [f(g(x))] = f'(g(x)) · g'(x)
```

**Example:** Find d/dx of x³ + 2x² - 5x + 3.
```
= 3x² + 4x - 5
```

## Applications of Derivatives

### Finding Maxima and Minima

1. Find f'(x) and set it to zero.
2. Solve for critical points.
3. Use the second derivative test: if f''(x) > 0, it's a minimum; if f''(x) < 0, it's a maximum.

**Example:** Find the minimum of f(x) = x² - 6x + 5.
```
f'(x) = 2x - 6 = 0 → x = 3
f''(x) = 2 > 0 → minimum at x = 3
f(3) = 9 - 18 + 5 = -4
```

## Basic Integration

Integration is the reverse of differentiation.

### Standard Integrals

| Function | Integral |
|----------|----------|
| xⁿ | xⁿ⁺¹ / (n+1) + C (n ≠ -1) |
| 1/x | ln |x| + C |
| eˣ | eˣ + C |
| cos x | sin x + C |
| sin x | -cos x + C |

**Example:** ∫ (3x² + 2x + 1) dx
```
= x³ + x² + x + C
```

## Practice Questions

**Q1:** Find lim(x→0) (sin x) / x.
> **Answer: 1.** This is a standard limit.

**Q2:** Find the derivative of f(x) = x² · eˣ.
```
Using the product rule:
f'(x) = 2x · eˣ + x² · eˣ = eˣ(2x + x²)
```

**Q3:** Find the maximum value of f(x) = -x² + 4x - 3.
```
f'(x) = -2x + 4 = 0 → x = 2
f''(x) = -2 < 0 → maximum
f(2) = -4 + 8 - 3 = 1
```
Answer: **1** at x = 2.

## Cross-references

- [Trigonometry](./trigonometry.md)
- [Number systems](./number-systems.md)
- [Percentages](./percentages.md)
- [Profit and loss](./profit-loss.md)
