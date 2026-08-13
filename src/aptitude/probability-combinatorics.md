# Probability & Combinatorics

Probability and combinatorics problems are common in placement tests, especially for product-based companies and GATE. This section covers fundamental counting principles, permutations, combinations, and probability with practical examples.

## Fundamental Counting Principles

### Addition Principle

If task A can be done in m ways and task B in n ways (mutually exclusive), then either A or B can be done in m + n ways.

### Multiplication Principle

If task A can be done in m ways and task B in n ways (independent), then both A and B together can be done in m × n ways.

**Example:** 3 shirts and 4 pants → 3 × 4 = 12 outfits.

## Factorials

```
n! = n × (n-1) × (n-2) × ... × 2 × 1
0! = 1 (by definition)
1! = 1
5! = 120
10! = 3,628,800
```

## Permutations (Order Matters)

### Definition

A permutation is an arrangement of objects in a specific order.

```
P(n, r) = nPr = n! / (n-r)!
```

**Example:** How many 3-letter arrangements from {A, B, C, D, E}?
```
P(5, 3) = 5! / (5-3)! = 120/2 = 60
```

### Permutations with Repetition

If we have n objects with groups of identical objects (n₁ of type 1, n₂ of type 2, ...):

```
P = n! / (n₁! × n₂! × ... × nₖ!)
```

**Example:** Arrangements of "MISSISSIPPI":
```
Total letters = 11
M: 1, I: 4, S: 4, P: 2
P = 11! / (1! × 4! × 4! × 2!) = 39916800 / (1 × 24 × 24 × 2) = 34650
```

### Circular Permutations

Arranging n objects in a circle:
```
P_circular = (n-1)!
```

**Example:** 5 people around a round table:
```
(5-1)! = 4! = 24 ways
```

If the circle can be flipped (like a necklace):
```
P_necklace = (n-1)! / 2
```

## Combinations (Order Doesn't Matter)

### Definition

A combination is a selection where order doesn't matter.

```
C(n, r) = nCr = n! / (r! × (n-r)!)
```

**Example:** Choose 3 people from 10:
```
C(10, 3) = 10! / (3! × 7!) = 720/6 = 120
```

### Key Properties

```
C(n, 0) = 1
C(n, n) = 1
C(n, r) = C(n, n-r)
C(n, 1) = n
C(n, 2) = n(n-1)/2
```

### Pascal's Triangle Relationship

```
C(n, r) = C(n-1, r-1) + C(n-1, r)
```

## Common Combination Formulas

### Selecting from Groups

- Select at least one from n: 2ⁿ - 1
- Select any number from n (including zero): 2ⁿ

**Example:** From 5 books, how many ways to select at least one?
```
2⁵ - 1 = 31 ways
```

### Dividing into Groups

Divide n distinct objects into groups of sizes r₁, r₂, ...:
```
Into k unordered (identical) groups: n! / (r₁! × r₂! × ... × rₖ! × s₁! × s₂! × ... × sₘ!)
  where sᵢ counts how many groups share the same size
  (special case: if all k groups have distinct sizes, this reduces to n! / (r₁! × ... × rₖ!) × 1/k!)

Into k ordered (labeled) groups: n! / (r₁! × r₂! × ... × rₖ!)
```

### Dividing Identical Objects

Divide n identical objects into r groups (each getting at least one):
```
C(n-1, r-1)
```

Divide n identical objects into r groups (groups can be empty):
```
C(n+r-1, r-1)
```

## Probability Basics

### Definition

```
P(Event) = Number of favorable outcomes / Total outcomes
```

**Example:** Probability of getting a 3 on a die:
```
P(3) = 1/6
```

### Properties

```
0 ≤ P(E) ≤ 1
P(certain event) = 1
P(impossible event) = 0
P(E) + P(E') = 1
```

### Complementary Probability

```
P(E') = 1 - P(E)
```

Often easier to calculate P(E') and subtract from 1.

**Example:** Probability of getting at least one head in 3 coin flips:
```
P(at least 1 head) = 1 - P(no heads) = 1 - (1/2)³ = 1 - 1/8 = 7/8
```

## Types of Events

### Independent Events

Events where one doesn't affect the other:
```
P(A and B) = P(A) × P(B)
P(A or B) = P(A) + P(B) - P(A and B)
```

### Mutually Exclusive Events

Events that can't happen simultaneously:
```
P(A and B) = 0
P(A or B) = P(A) + P(B)
```

### Dependent Events

Events where one affects the other:
```
P(A and B) = P(A) × P(B|A)
```

## Conditional Probability

```
P(A|B) = P(A and B) / P(B)
```

**Example:** A bag has 3 red and 5 blue balls. Two balls drawn without replacement. P(second is red | first was red)?
```
After drawing 1 red: 2 red, 5 blue left
P(2nd red | 1st red) = 2/7
```

## Bayes' Theorem

```
P(A|B) = P(B|A) × P(A) / P(B)
```

**Example:** A factory has machines A (60% output), B (40%). A's defect rate = 2%, B's = 3%. A defective item is found. P(it's from A)?

```
P(A|D) = P(D|A) × P(A) / P(D)
P(D) = P(D|A)×P(A) + P(D|B)×P(B)
= 0.02×0.6 + 0.03×0.4 = 0.012 + 0.012 = 0.024
P(A|D) = 0.012/0.024 = 0.5 = 50%
```

## Dice Problems

### Single Die

- Total outcomes: 6
- Even numbers: {2, 4, 6} → P = 3/6 = 1/2
- Odd numbers: {1, 3, 5} → P = 3/6 = 1/2
- Prime: {2, 3, 5} → P = 3/6 = 1/2

### Two Dice

- Total outcomes: 36
- Sum = 7: (1,6)(2,5)(3,4)(4,3)(5,2)(6,1) → 6 outcomes → P = 6/36 = 1/6
- Sum = 2: (1,1) → 1 outcome → P = 1/36
- Sum = 12: (6,6) → 1 outcome → P = 1/36

### Sum Distribution (Two Dice)

| Sum | Outcomes | Count | Probability |
|-----|----------|-------|-------------|
| 2 | (1,1) | 1 | 1/36 |
| 3 | (1,2)(2,1) | 2 | 2/36 |
| 4 | (1,3)(2,2)(3,1) | 3 | 3/36 |
| 5 | (1,4)(2,3)(3,2)(4,1) | 4 | 4/36 |
| 6 | (1,5)(2,4)(3,3)(4,2)(5,1) | 5 | 5/36 |
| 7 | (1,6)(2,5)(3,4)(4,3)(5,2)(6,1) | 6 | 6/36 |
| 8 | (2,6)(3,5)(4,4)(5,3)(6,2) | 5 | 5/36 |
| 9 | (3,6)(4,5)(5,4)(6,3) | 4 | 4/36 |
| 10 | (4,6)(5,5)(6,4) | 3 | 3/36 |
| 11 | (5,6)(6,5) | 2 | 2/36 |
| 12 | (6,6) | 1 | 1/36 |

## Coin Problems

### Single Coin

- P(Head) = 1/2
- P(Tail) = 1/2

### Two Coins

- HH, HT, TH, TT → 4 outcomes
- P(at least 1 head) = 3/4
- P(exactly 1 head) = 2/4 = 1/2

### n Coins

- Total outcomes: 2ⁿ
- P(exactly r heads) = C(n, r) / 2ⁿ

**Example:** 5 coins, P(exactly 3 heads):
```
P = C(5,3)/2⁵ = 10/32 = 5/16
```

## Card Problems

### Standard Deck

| Category | Count |
|----------|-------|
| Total cards | 52 |
| Suits | 4 (♠, ♥, ♦, ♣) |
| Cards per suit | 13 |
| Face cards | 12 (J, Q, K × 4 suits) |
| Aces | 4 |
| Red cards | 26 (♥, ♦) |
| Black cards | 26 (♠, ♣) |

### Common Card Probabilities

```
P(ace) = 4/52 = 1/13
P(face card) = 12/52 = 3/13
P(red) = 26/52 = 1/2
P(heart) = 13/52 = 1/4
P(queen of hearts) = 1/52
```

**Example:** 5 cards drawn. P(all are hearts)?
```
P = C(13,5) / C(52,5) = 1287/2598960 ≈ 0.000495
```

## Odds

### Odds in Favor

```
Odds in favor = P(E) : P(E') = favorable : unfavorable
```

### Odds Against

```
Odds against = P(E') : P(E) = unfavorable : favorable
```

**Example:** Odds of getting a 3 on a die:
```
Favorable = 1, Unfavorable = 5
Odds in favor = 1:5
Odds against = 5:1
```

## Expected Value

```
E(X) = Σ [xᵢ × P(xᵢ)]
```

**Example:** A game: win ₹100 with P=0.3, lose ₹50 with P=0.7.
```
E = 100×0.3 + (-50)×0.7 = 30 - 35 = -₹5
Expected loss of ₹5 per game.
```

## Tricks & Shortcuts

### Trick 1: C(n,2) = Number of Handshakes/Diagonals

```
Handshakes among n people = C(n,2) = n(n-1)/2
Diagonals in n-sided polygon = C(n,2) - n = n(n-3)/2
```

### Trick 2: At Least One → Use Complement

```
P(at least one) = 1 - P(none)
```

### Trick 3: Sum of C(n,r) for all r

```
Σ C(n,r) = 2ⁿ
```

### Trick 4: Odd and Even Selections

```
C(n,0) + C(n,2) + C(n,4) + ... = 2ⁿ⁻¹
C(n,1) + C(n,3) + C(n,5) + ... = 2ⁿ⁻¹
```

### Trick 5: Probability with "at least"

For "at least k" problems, complement is usually easier:
```
P(at least k) = 1 - P(0) - P(1) - ... - P(k-1)
```

## Practice Questions

### Q1: Basic Probability
A bag has 5 red, 3 blue, and 2 green balls. One ball drawn at random. P(red or green)?

**Solution:**
```
Total = 10
Red or Green = 5 + 2 = 7
P = 7/10
```

### Q2: Two Dice
Two dice thrown. P(sum divisible by 3)?

**Solution:**
```
Sums divisible by 3: 3, 6, 9, 12
P(3) = 2/36, P(6) = 5/36, P(9) = 4/36, P(12) = 1/36
Total = (2+5+4+1)/36 = 12/36 = 1/3
```

### Q3: Combination
From 10 people, choose a committee of 4 with a president. How many ways?

**Solution:**
```
Choose 4 from 10: C(10,4) = 210
Choose president from 4: 4
Total = 210 × 4 = 840
```

### Q4: Arrangement
How many ways to arrange the letters of "MATHEMATICS"?

**Solution:**
```
11 letters: M-2, A-2, T-2, H-1, E-1, I-1, C-1, S-1
P = 11! / (2!×2!×2!) = 39916800 / 8 = 4989600
```

### Q5: Conditional Probability
P(A) = 0.6, P(B) = 0.4, P(A∩B) = 0.2. Find P(A|B).

**Solution:**
```
P(A|B) = P(A∩B)/P(B) = 0.2/0.4 = 0.5
```

### Q6: Coin Toss
3 coins tossed. P(at least 2 heads)?

**Solution:**
```
Outcomes: HHH, HHT, HTH, THH, HTT, THT, TTH, TTT
At least 2 heads: HHH, HHT, HTH, THH → 4 outcomes
P = 4/8 = 1/2
Or: C(3,2)/8 + C(3,3)/8 = 3/8 + 1/8 = 4/8 = 1/2
```

### Q7: Card Problem
5 cards drawn from a deck. P(exactly 2 aces)?

**Solution:**
```
P = C(4,2) × C(48,3) / C(52,5)
= 6 × 17296 / 2598960
= 103776 / 2598960 ≈ 0.0399
```

### Q8: Bayes' Theorem
A box has 3 Type A bulbs (10% defective) and 7 Type B bulbs (5% defective). A bulb is defective. P(Type A)?

**Solution:**
```
P(A|D) = P(D|A)×P(A) / P(D)
P(D) = 0.1×0.3 + 0.05×0.7 = 0.03 + 0.035 = 0.065
P(A|D) = 0.03/0.065 = 30/65 = 6/13 ≈ 0.462
```

## Summary Table

| Concept | Formula |
|---------|---------|
| Permutation | P(n,r) = n!/(n-r)! |
| Combination | C(n,r) = n!/(r!(n-r)!) |
| Circular perm | (n-1)! |
| Identical objects | n!/(n₁!×n₂!×...×nₖ!) |
| P(A or B) | P(A)+P(B)-P(A∩B) |
| P(A and B) indep | P(A)×P(B) |
| P(A|B) | P(A∩B)/P(B) |
| Bayes | P(A|B) = P(B|A)P(A)/P(B) |
| Complement | P(E') = 1 - P(E) |
| Expected value | Σ xᵢP(xᵢ) |
