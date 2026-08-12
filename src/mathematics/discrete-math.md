# Discrete Mathematics

## Modular Arithmetic

```
a ≡ b (mod n) means n | (a - b)

(a + b) mod n = ((a mod n) + (b mod n)) mod n
(a × b) mod n = ((a mod n) × (b mod n)) mod n
(a - b) mod n = ((a mod n) - (b mod n) + n) mod n
```

### Modular Inverse
```
a × a⁻¹ ≡ 1 (mod n)
Exists iff gcd(a, n) = 1

Extended Euclidean Algorithm:
gcd(3, 11): 11 = 3×3 + 2, 3 = 2×1 + 1
Back-substitute: 1 = 3 - 2×1 = 3 - (11-3×3)×1 = 3×4 - 11×1
So 3⁻¹ ≡ 4 (mod 11)  (verify: 3×4 = 12 ≡ 1 mod 11)
```

## Combinatorics

### Permutations (order matters)
```
P(n, r) = n! / (n-r)!
n objects, choose r, arrange in order

P(5, 3) = 5! / 2! = 60
```

### Combinations (order doesn't matter)
```
C(n, r) = n! / (r! × (n-r)!)
n objects, choose r, no arrangement

C(5, 3) = 5! / (3! × 2!) = 10

Pascal's Triangle:
      1
     1 1
    1 2 1
   1 3 3 1
  1 4 6 4 1
```

### Key Identities
```
C(n, r) = C(n, n-r)
C(n, r) = C(n-1, r-1) + C(n-1, r)  (Pascal's identity)
C(n, 0) + C(n, 1) + ... + C(n, n) = 2^n  (sum of row)
```

## Probability

### Basic Rules
```
P(A ∪ B) = P(A) + P(B) - P(A ∩ B)
P(A | B) = P(A ∩ B) / P(B)           (conditional)
P(A ∩ B) = P(A) × P(B)               (if independent)
```

### Bayes' Theorem
```
P(A | B) = P(B | A) × P(A) / P(B)

Example: Disease test
- P(disease) = 0.01 (prevalence)
- P(positive | disease) = 0.99 (sensitivity)
- P(positive | no disease) = 0.05 (false positive)

P(disease | positive) = (0.99 × 0.01) / (0.99×0.01 + 0.05×0.99)
                      = 0.0099 / 0.0594 ≈ 0.167 (16.7%)
```

### Expected Value
```
E[X] = Σ x × P(x)

Example: Dice roll
E[X] = 1×(1/6) + 2×(1/6) + ... + 6×(1/6) = 3.5

Linearity: E[X + Y] = E[X] + E[Y] (always, even if dependent)
```

## Matrices

### Matrix Multiplication
```
(A × B)[i][j] = Σ_k A[i][k] × B[k][j]

(m×n) × (n×p) = (m×p)
Time: O(m×n×p)
```

### Matrix Exponentiation (for DP)
```
If T(n) = T(n-1) + T(n-2) (Fibonacci):
[T(n)  ]   [1 1]^(n-1)   [T(1)]
[T(n-1)] = [1 0]        × [T(0)]

Compute A^n in O(log n) using repeated squaring.
```

## Interview Questions

**Q: What is the pigeonhole principle?**
A: If n items are placed into m containers and n > m, at least one container has more than one item. Applications: hash collisions are inevitable when keys > buckets, birthday paradox.

**Q: How do you compute C(n, r) efficiently?**
A: Use the recurrence C(n, r) = C(n-1, r-1) + C(n-1, r) with dynamic programming. For modular combinatorics, precompute factorials and use modular inverse. Time: O(n) precomputation, O(1) per query.

## References

- [Discrete Mathematics — Rosen](https://www.mheducation.com/highered/product/discrete-mathematics-applications-rosen/M9780073383095.html)
- [MIT OCW 6.042J](https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/)
