# Profit & Loss

Profit and loss problems are among the most common in placement aptitude tests. Understanding the relationships between cost price, selling price, marked price, and discount is essential.

## Core Terms

| Term | Symbol | Meaning |
|------|--------|---------|
| Cost Price | CP | Price at which an article is bought |
| Selling Price | SP | Price at which an article is sold |
| Marked Price | MP | Price printed on the label (before discount) |
| Profit/Gain | P | When SP > CP, profit = SP - CP |
| Loss | L | When CP > SP, loss = CP - SP |
| Discount | D | Reduction on Marked Price |

## Key Formulas

### Basic Profit/Loss

```
Profit = SP - CP (when SP > CP)
Loss = CP - SP (when CP > SP)
```

### Profit/Loss Percentage

```
Profit% = (Profit / CP) × 100
Loss% = (Loss / CP) × 100
```

**Important:** Percentage is ALWAYS calculated on CP unless stated otherwise.

### Finding SP from CP

```
SP = CP × (100 + Profit%) / 100   [when profit]
SP = CP × (100 - Loss%) / 100     [when loss]
```

### Finding CP from SP

```
CP = SP × 100 / (100 + Profit%)   [when profit]
CP = SP × 100 / (100 - Loss%)     [when loss]
```

## Discount Problems

### Discount on Marked Price

```
Discount = MP - SP
Discount% = (Discount / MP) × 100
SP = MP × (100 - Discount%) / 100
```

**Example:** MP = ₹500, Discount = 20%
```
SP = 500 × (100-20)/100 = 500 × 0.8 = ₹400
Discount amount = ₹100
```

### Successive Discounts

Two successive discounts of a% and b% are NOT the same as a single discount of (a+b)%.

**Formula for equivalent single discount:**
```
Single discount = a + b - (ab/100)
```

**Example:** Successive discounts of 20% and 10%:
```
= 20 + 10 - (20×10)/100 = 30 - 2 = 28%
```

**Verify:** On ₹1000:
- After 20%: ₹800
- After 10% on ₹800: ₹720
- Total discount: ₹280 → 28% ✓

### Three Successive Discounts

For discounts a%, b%, c%:
```
SP = MP × (1-a/100)(1-b/100)(1-c/100)
```

**Example:** MP = ₹1000, discounts 10%, 20%, 30%:
```
SP = 1000 × 0.9 × 0.8 × 0.7 = 1000 × 0.504 = ₹504
Effective discount = 49.6%
```

## Profit/Loss with Fractions

### Common Fraction-to-Percentage Mappings

| Fraction | Percentage |
|----------|-----------|
| 1/4 gain | 25% profit |
| 1/5 gain | 20% profit |
| 1/3 gain | 33.33% profit |
| 1/4 loss | 25% loss |
| 1/3 loss | 33.33% loss |

**Problem:** A man sells an article at a profit of 25%. If he had bought it at 20% less and sold it for ₹10.50 less, he would have gained 30%. Find the CP.

**Solution:**
```
Let CP = 100x
SP₁ = 125x (25% profit)
New CP = 80x (20% less)
New SP = 104x (30% profit on 80x)
125x - 104x = 10.50
21x = 10.50
x = 0.5
CP = 100 × 0.5 = ₹50
```

## Dishonest Dealer / False Weight Problems

### Concept

A dealer uses false weights but claims to sell at cost price. His profit% is:

```
Profit% = [(True weight - False weight) / False weight] × 100
```

**Example:** A dealer uses 900g instead of 1kg. Find profit%.
```
Profit% = [(1000 - 900) / 900] × 100 = (100/900) × 100 = 11.11%
```

### Dealer sells at x% loss using y% less weight

```
Actual profit/loss% = [(100+x)/(100-y) - 1] × 100
```

**Wait — correct formula:**

If a dealer sells at a loss of x% but uses y% less weight:
```
Net effect = [(100-x)/(100-y) - 1] × 100
```

If positive → profit, if negative → loss.

**Example:** Sells at 10% loss but uses 20% less weight:
```
= [(100-10)/(100-20) - 1] × 100
= [90/80 - 1] × 100
= [1.125 - 1] × 100 = 12.5% profit
```

## Buy X Get Y Free

**Problem:** A shopkeeper offers "Buy 2 Get 1 Free". What is the discount%?

**Solution:**
```
Customer pays for 2, gets 3
Discount% = (Free / Total) × 100 = (1/3) × 100 = 33.33%
```

**Problem:** "Buy 3 Get 1 Free":
```
Discount% = (1/4) × 100 = 25%
```

**General:** "Buy (n-1) Get 1 Free" → Discount = (1/n) × 100%

## Markup and Profit Relationship

### Finding Markup % for Desired Profit

If a shopkeeper wants x% profit after giving d% discount:

```
MP = CP × (100 + x) / (100 - d)
Markup% = [(100+x)/(100-d) - 1] × 100
```

**Example:** CP = ₹200, wants 20% profit, gives 10% discount:
```
MP = 200 × (100+20)/(100-10) = 200 × 120/90 = ₹266.67
Markup% = (266.67-200)/200 × 100 = 33.33%
```

## Two Items Sold at Same Price

### One at Profit, One at Loss (Same %)

If two items are sold at the same price, one at x% profit and the other at x% loss:

```
Net result = Always a LOSS
Net loss% = x²/100 %
```

**Example:** Two items at ₹1000 each, one at 20% profit, one at 20% loss:
```
Loss% = 20²/100 = 4%
Net loss = 4% of (total CP)
```

**Proof:**
```
SP₁ = SP₂ = S (same selling price)
CP₁ = S × 100/(100+x)
CP₂ = S × 100/(100-x)
Total CP = S[100/(100+x) + 100/(100-x)]
= S × [100(100-x) + 100(100+x)] / [(100+x)(100-x)]
= S × 20000 / (10000-x²)
Total SP = 2S
Loss = Total CP - Total SP = 2S × x²/(10000-x²)
Loss% = x²/100 (approximately, when x is small)
Exact: Loss% = [x²/(10000-x²)] × 100 ≈ x²/100
```

### Different Percentages

If one is sold at x% profit and other at y% loss, and SP is same:
```
Net loss% = (x-y)² / (200+x-y)   [if x < y, it's a loss]
Or use: Net effect = 2xy/(x+y) loss if x=y, general formula is complex.
```

## Tricks & Shortcuts

### Trick 1: CP-SP-MP Relationships

```
CP → (+Profit%) → SP
CP → (+Loss%) → SP (with minus)
MP → (-Discount%) → SP
```

### Trick 2: If Profit% = Loss% on Different CPs

If selling at ₹X gives profit of P%, and selling at ₹Y gives loss of P%:
```
CP = (X + Y) / 2
```

### Trick 3: Finding CP from Profit and Loss Scenarios

If selling at ₹A gives profit of x%, and selling at ₹B gives loss of y%:
```
CP = (A×100)/(100+x) = (B×100)/(100-y)
```

From these two:
```
CP = (100×A)/(100+x) and CP = (100×B)/(100-y)
```

### Trick 4: Equal Profit and Loss Amount

If profit% and loss% are on the same CP and equal in amount:
```
Profit × CP/100 = Loss × CP/100
This only happens when profit% = loss%
```

### Trick 5: Effect of Changing CP and SP

If CP increases by x% and SP remains the same:
- Profit decreases or loss increases

If SP increases by x% and CP remains the same:
- Profit increases or loss decreases

## Practice Questions

### Q1: Basic Profit/Loss
A shopkeeper buys an article for ₹400 and sells it for ₹500. Find profit%.

**Solution:**
```
Profit = 500 - 400 = ₹100
Profit% = (100/400) × 100 = 25%
```

### Q2: Successive Discounts
Find the single equivalent discount for successive discounts of 20%, 15%, and 10%.

**Solution:**
```
Let MP = 100
After 20%: 80
After 15%: 80 × 0.85 = 68
After 10%: 68 × 0.9 = 61.2
Effective discount = 100 - 61.2 = 38.8%
```

### Q3: False Weight
A shopkeeper sells sugar at cost price but uses 800g instead of 1kg. Find profit%.

**Solution:**
```
Profit% = [(1000-800)/800] × 100 = (200/800) × 100 = 25%
```

### Q4: Markup and Discount
A shopkeeper marks an article 40% above CP and allows a 20% discount. Find profit%.

**Solution:**
```
Let CP = 100
MP = 140
SP = 140 × 0.8 = 112
Profit% = 12%
```

### Q5: Two Articles Same SP
Two articles are sold at ₹990 each. One at 10% profit, other at 10% loss. Find net result.

**Solution:**
```
CP₁ = 990 × 100/110 = ₹900
CP₂ = 990 × 100/90 = ₹1100
Total CP = 2000, Total SP = 1980
Loss = ₹20
Loss% = (20/2000) × 100 = 1%
```

### Q6: Buy X Get Y Free
A shopkeeper offers "Buy 4 Get 1 Free". What discount% is this equivalent to?

**Solution:**
```
Pay for 4, get 5
Discount = (1/5) × 100 = 20%
```

### Q7: Complex Problem
A man buys 5 apples for ₹3 and sells 3 apples for ₹5. Find profit% on 15 apples.

**Solution:**
```
CP of 15 apples = 3 × (15/5) = ₹9
SP of 15 apples = 5 × (15/3) = ₹25
Profit = ₹16
Profit% = (16/9) × 100 = 177.78%
```

### Q8: Mixed Problem
A shopkeeper sells an article at 15% profit. If he had bought it at 10% less and sold it for ₹45 less, he would have gained 25%. Find the original CP.

**Solution:**
```
Let CP = 100x
Original SP = 115x
New CP = 90x
New SP = 90x × 1.25 = 112.5x
115x - 112.5x = 45
2.5x = 45
x = 18
CP = ₹1800
```

## Summary Table

| Concept | Formula |
|---------|---------|
| Profit% | (SP-CP)/CP × 100 |
| Loss% | (CP-SP)/CP × 100 |
| SP (profit) | CP × (100+P%)/100 |
| SP (loss) | CP × (100-L%)/100 |
| Discount% | (MP-SP)/MP × 100 |
| Successive disc a,b | a + b - ab/100 |
| False weight profit% | (True-False)/False × 100 |
| Same SP, same % P&L | Loss = x²/100 % |
| Buy n-1 Get 1 Free | Disc = 1/n × 100% |
