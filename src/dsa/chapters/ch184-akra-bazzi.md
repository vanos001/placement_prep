# Chapter 184: Akra-Bazzi Master Theorem

The standard Master Theorem handles recurrences of the form T(n) = aT(n/b) + f(n). The **Akra-Bazzi theorem** generalizes this to non-uniform splits, multiple subproblems of different sizes, and additive lower-order terms.

---

## The Theorem

For a recurrence of the form:

```
T(n) = Σ aᵢ · T(n/bᵢ) + f(n)
```

where aᵢ > 0, bᵢ > 1, and f(n) is polynomially bounded, define **p** such that:

```
Σ aᵢ / bᵢᵖ = 1
```

Then:

| Case | Condition | Solution |
|---|---|---|
| 1 | f(n) = O(n^(p-ε)) | T(n) = Θ(n^p) |
| 2 | f(n) = Θ(n^p · log^k n) | T(n) = Θ(n^p · log^(k+1) n) |
| 3 | f(n) = Ω(n^(p+ε)) | T(n) = Θ(f(n)) |

---

## Example 1: Non-Uniform Split

```
T(n) = T(n/3) + T(n/4) + n²
```

Find p: 1/(3^p) + 1/(4^p) = 1. Testing p=1: 1/3 + 1/4 = 7/12 < 1. Testing p ≈ 0.79 satisfies the equation. Since f(n) = n² = Ω(n^(0.79+ε)), this is **Case 3**: T(n) = Θ(n²).

## Example 2: With Log Factor

```
T(n) = 2T(n/2) + n log n
```

Standard master theorem fails (log factor). Here p=1, f(n) = n·log n = Θ(n^1 · log^1 n) → **Case 2**: T(n) = Θ(n · log² n).

---

## Step-by-Step Method

1. Identify all aᵢ and bᵢ from the recurrence.
2. Solve Σ aᵢ/bᵢᵖ = 1 numerically (binary search on p).
3. Classify f(n) relative to n^p.
4. Apply the appropriate case.

```python
def find_p(a_list, b_list, lo=0.0, hi=10.0):
    for _ in range(100):
        mid = (lo + hi) / 2
        val = sum(a / (b ** mid) for a, b in zip(a_list, b_list))
        if val > 1: lo = mid
        else: hi = mid
    return (lo + hi) / 2
```

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Confusing Akra-Bazzi with Master Theorem cases | Akra-Bazzi uses n^p, not n^(log_b a) |
| Not solving for p numerically | Binary search is the standard approach |
| Forgetting the regularity condition in Case 3 | aᵢ·f(n/bᵢ) ≤ c·f(n) must hold |

---

## Practice Problems

| # | Problem | Hint |
|---|---|---|
| 1 | T(n) = T(n/2) + T(n/3) + n | Find p, then classify |
| 2 | T(n) = 3T(n/3) + n/log n | p=1, which case? |
| 3 | T(n) = 2T(n/4) + T(n/2) + n | Non-uniform splits; find p numerically |
| 4 | Median-of-medians recurrence: T(n)=T(n/5)+T(7n/10)+n | Classic Akra-Bazzi application |
| 5 | T(n) = T(√n) + 1 | Substitute m = log n first |
| 6 | Merge sort variant: T(n) = T(⌊n/2⌋) + T(⌈n/2⌉) + n log n | Floors/ceilings don't affect asymptotics |

---

## See Also

- [Chapter 39: Divide and Conquer](ch39-divide-conquer.md)
- [Chapter 139: Complexity Handbook](ch139-complexity-handbook.md)
- [Chapter 03: Complexity Analysis](ch03-complexity-analysis.md)
- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md)
