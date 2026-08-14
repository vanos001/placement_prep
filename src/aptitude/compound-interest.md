# Compound and Simple Interest

Interest problems appear in nearly every placement test. The key distinction: simple interest is calculated only on the principal, while compound interest is calculated on the principal plus accumulated interest.

## Simple Interest (SI)

```
SI = (P × R × T) / 100
```

Where P = principal, R = rate per annum (%), T = time in years.

**Example:** ₹5,000 at 8% for 3 years.
```
SI = (5000 × 8 × 3) / 100 = ₹1,200
Total amount = 5000 + 1200 = ₹6,200
```

## Compound Interest (CI)

```
A = P × (1 + R/100)^T
CI = A - P = P × [(1 + R/100)^T - 1]
```

**Example:** ₹5,000 at 8% compounded annually for 3 years.
```
A = 5000 × (1.08)^3 = 5000 × 1.259712 = ₹6,298.56
CI = 6298.56 - 5000 = ₹1,298.56
```

## Simple vs Compound Comparison

| Years | SI on ₹10,000 at 10% | CI on ₹10,000 at 10% | Difference |
|-------|----------------------|----------------------|------------|
| 1 | ₹1,000 | ₹1,000 | ₹0 |
| 2 | ₹2,000 | ₹2,100 | ₹100 |
| 3 | ₹3,000 | ₹3,310 | ₹310 |

**Key insight:** The difference grows over time because CI earns interest on interest.

## Key Formulas

### Compounding More Than Once a Year

```
A = P × (1 + R/(n × 100))^(n × T)
```

Where n = number of compounding periods per year.

| Compounding | n |
|-------------|---|
| Annually | 1 |
| Semi-annually | 2 |
| Quarterly | 4 |
| Monthly | 12 |

**Example:** ₹10,000 at 12% compounded quarterly for 1 year.
```
A = 10000 × (1 + 12/(4×100))^4 = 10000 × (1.03)^4 = ₹11,255.09
```

### Effective Annual Rate

```
Effective rate = (1 + R/(n×100))^n - 1
```

For 12% compounded quarterly: (1.03)^4 - 1 = 12.55% effective rate.

## Shortcuts

**Shortcut 1:** If CI and SI on the same principal at the same rate for 2 years are given, the difference equals:
```
CI - SI = P × (R/100)^2
```

**Shortcut 2:** For 3 years, the difference equals:
```
CI - SI = P × (R/100)^2 × (3 + R/100)
```

## Practice Questions

**Q1:** ₹8,000 at 5% CI for 2 years. Find CI.
```
A = 8000 × (1.05)^2 = 8000 × 1.1025 = ₹8,820
CI = 8820 - 8000 = ₹820
```

**Q2:** A sum doubles in 10 years at SI. Find the rate.
```
2P = P + P × R × 10/100
P = P × R × 10/100
R = 10%
```

**Q3:** If CI on ₹5,000 for 2 years is ₹820, find the rate.
```
A = 5820, so (1 + R/100)^2 = 5820/5000 = 1.164
1 + R/100 = √1.164 = 1.079
R = 7.9% ≈ 8%
```

## Summary Table

| Concept | Formula |
|---------|--------|
| Simple Interest | SI = PRT/100 |
| Compound Interest | A = P(1 + R/100)^T |
| CI for n periods/year | A = P(1 + R/(n·100))^(nT) |
| CI - SI (2 years) | P × (R/100)^2 |
| Doubling time (SI) | 100/R years |

## Cross-references

- [Percentages](./percentages.md)
- [Profit and loss](./profit-loss.md)
- [Ratios and proportions](./ratios-proportions.md)
- [Averages](./averages.md)