# Number Systems

Number system problems test your understanding of divisibility, HCF/LCM, remainders, and number properties. These are foundational for quantitative aptitude.

## Types of Numbers

| Type | Definition | Examples |
|------|-----------|----------|
| Natural Numbers | Counting numbers | 1, 2, 3, ... |
| Whole Numbers | Natural + 0 | 0, 1, 2, 3, ... |
| Integers | Whole + negatives | ..., -2, -1, 0, 1, 2, ... |
| Even Numbers | Divisible by 2 | 2, 4, 6, ... |
| Odd Numbers | Not divisible by 2 | 1, 3, 5, ... |
| Prime Numbers | Only divisible by 1 and itself | 2, 3, 5, 7, 11, ... |
| Composite Numbers | Not prime (>1) | 4, 6, 8, 9, ... |
| Co-prime | HCF = 1 | (8, 15), (3, 7) |
| Rational | Can be expressed as p/q | 1/2, 3, -7 |
| Irrational | Cannot be expressed as p/q | √2, π |

## Prime Numbers

### First 25 Primes

```
2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
53, 59, 61, 67, 71, 73, 79, 83, 89, 97
```

### Checking if a Number is Prime

To check if N is prime:
1. Find √N
2. Check divisibility by all primes ≤ √N
3. If none divide N, it's prime

**Example:** Is 97 prime?
```
√97 ≈ 9.85
Primes ≤ 9: 2, 3, 5, 7
97/2 → not divisible (odd)
97/3 → 9+7=16, not divisible by 3
97/5 → doesn't end in 0 or 5
97/7 → 97/7 = 13.86, not divisible
97 is prime ✓
```

### Prime Factorization

Every number > 1 can be uniquely expressed as a product of primes.

```
360 = 2³ × 3² × 5
120 = 2³ × 3 × 5
```

## Divisibility Rules

| Divisor | Rule | Example |
|---------|------|---------|
| 2 | Last digit even | 346 → 6 is even ✓ |
| 3 | Sum of digits divisible by 3 | 372: 3+7+2=12 ✓ |
| 4 | Last two digits divisible by 4 | 5316: 16÷4=4 ✓ |
| 5 | Last digit 0 or 5 | 245 → 5 ✓ |
| 6 | Divisible by 2 AND 3 | 138: even, 1+3+8=12 ✓ |
| 7 | Double last digit, subtract from rest, repeat | 343: 34-6=28, 28÷7=4 ✓ |
| 8 | Last 3 digits divisible by 8 | 5312: 312÷8=39 ✓ |
| 9 | Sum of digits divisible by 9 | 729: 7+2+9=18 ✓ |
| 10 | Last digit 0 | 450 ✓ |
| 11 | Difference of alternate digit sums | 121: (1+1)-2=0 ✓ |
| 12 | Divisible by 3 AND 4 | 144: sum=9✓, 44÷4✓ |

### Divisibility by 7 (Detailed)

```
Take 2058:
Step 1: 205 - (2×8) = 205 - 16 = 189
Step 2: 18 - (2×9) = 18 - 18 = 0
2058 is divisible by 7 ✓
```

### Divisibility by 11 (Detailed)

```
Take 1331:
(1+3) - (3+1) = 4 - 4 = 0 → divisible by 11 ✓

Take 9152:
(9+5) - (1+2) = 14 - 3 = 11 → divisible by 11 ✓
```

## HCF (Highest Common Factor)

### Method 1: Prime Factorization

```
HCF(36, 48):
36 = 2² × 3²
48 = 2⁴ × 3
HCF = 2² × 3 = 12
```

### Method 2: Euclidean Algorithm

```
HCF(48, 36):
48 = 36 × 1 + 12
36 = 12 × 3 + 0
HCF = 12
```

### Properties of HCF

- HCF divides both numbers
- HCF of co-prime numbers = 1
- HCF(a, b) × LCM(a, b) = a × b

## LCM (Least Common Multiple)

### Method 1: Prime Factorization

```
LCM(12, 18):
12 = 2² × 3
18 = 2 × 3²
LCM = 2² × 3² = 36
```

### Method 2: Using HCF

```
LCM(a, b) = (a × b) / HCF(a, b)
```

### Properties of LCM

- LCM is divisible by both numbers
- LCM ≥ max(a, b)
- LCM of co-prime numbers = a × b

## HCF and LCM of Fractions

```
HCF of fractions = HCF of numerators / LCM of denominators
LCM of fractions = LCM of numerators / HCF of denominators
```

**Example:** HCF(2/3, 4/5):
```
HCF(2, 4) / LCM(3, 5) = 2/15
```

## Remainders

### Basic Remainder

When a is divided by b:
```
a = b × q + r (where 0 ≤ r < b)
```

### Remainder of a Sum

```
Rem[(a + b) / m] = Rem[a/m] + Rem[b/m]
(If this exceeds m, take remainder again)
```

### Remainder of a Product

```
Rem[(a × b) / m] = Rem[a/m] × Rem[b/m]
(Again, take remainder if needed)
```

**Example:** Remainder of 47 × 53 divided by 7:
```
47 mod 7 = 5 (47 = 6×7 + 5)
53 mod 7 = 4 (53 = 7×7 + 4)
5 × 4 = 20
20 mod 7 = 6
```

### Remainder of Powers

**Wilson's Theorem (for prime p):**
```
(p-1)! ≡ -1 (mod p)
(p-1)! mod p = p - 1
```

**Fermat's Little Theorem:**
If p is prime and gcd(a, p) = 1:
```
a^(p-1) ≡ 1 (mod p)
```

**Example:** 2¹⁰⁰ mod 7:
```
By Fermat: 2⁶ ≡ 1 (mod 7)
100 = 16×6 + 4
2¹⁰⁰ = (2⁶)¹⁶ × 2⁴ ≡ 1¹⁶ × 16 ≡ 16 ≡ 2 (mod 7)
```

### Cyclicity of Remainders

Find the pattern of remainders for powers:

```
2¹ mod 7 = 2
2² mod 7 = 4
2³ mod 7 = 1
2⁴ mod 7 = 2
Cycle length = 3
```

So 2¹⁰⁰ mod 7: 100 mod 3 = 1 → 2¹ mod 7 = 2

## Number of Factors

### Formula

If N = p₁^a₁ × p₂^a₂ × ... × pₖ^aₖ:

```
Number of factors = (a₁+1)(a₂+1)...(aₖ+1)
```

**Example:** 360 = 2³ × 3² × 5¹
```
Factors = (3+1)(2+1)(1+1) = 4×3×2 = 24
```

### Sum of Factors

```
Sum = [(p₁^(a₁+1)-1)/(p₁-1)] × [(p₂^(a₂+1)-1)/(p₂-1)] × ...
```

### Number of Odd Factors

Remove the factor of 2 and apply the formula to the remaining part.

**Example:** 360 = 2³ × 45 = 2³ × 3² × 5
```
Odd factors of 360 = factors of 45 = (2+1)(1+1) = 6
```

### Number of Even Factors

```
Even factors = Total factors - Odd factors
```

## Number Properties

### Sum of First N Natural Numbers

```
S = n(n+1)/2
```

### Sum of First N Even Numbers

```
S = n(n+1)
```

### Sum of First N Odd Numbers

```
S = n²
```

### Sum of Squares

```
S = n(n+1)(2n+1)/6
```

### Sum of Cubes

```
S = [n(n+1)/2]²
```

### Arithmetic Progression (AP)

```
nth term: aₙ = a + (n-1)d
Sum: S = n/2 × (2a + (n-1)d) = n/2 × (first + last)
```

### Geometric Progression (GP)

```
nth term: aₙ = ar^(n-1)
Sum: S = a(rⁿ-1)/(r-1) for r ≠ 1
Infinite sum: S = a/(1-r) for |r| < 1
```

## Tricks & Shortcuts

### Trick 1: Quick Sum of Consecutive Numbers

```
Sum from a to b = (a+b) × (b-a+1) / 2
```

**Example:** Sum from 51 to 100:
```
= (51+100) × 50 / 2 = 151 × 25 = 3775
```

### Trick 2: Number of Digits

Number of digits in N = floor(log₁₀N) + 1

### Trick 3: Perfect Squares

A perfect square's last digit can only be: 0, 1, 4, 5, 6, 9
A perfect square ends with even number of zeros.
Digital root of a perfect square is 1, 4, 7, or 9.

### Trick 4: Quick HCF by Observation

If one number divides the other, the HCF is the smaller number.
HCF(a, 0) = a.

### Trick 5: Product and HCF/LCM

```
a × b = HCF(a,b) × LCM(a,b)
```

## Practice Questions

### Q1: Divisibility
Is 345678 divisible by 9?

**Solution:**
```
Sum of digits: 3+4+5+6+7+8 = 33
33/9 = 3.67 → Not divisible by 9
```

### Q2: HCF and LCM
Find HCF and LCM of 84 and 120.

**Solution:**
```
84 = 2² × 3 × 7
120 = 2³ × 3 × 5
HCF = 2² × 3 = 12
LCM = 2³ × 3 × 5 × 7 = 840
Check: 84 × 120 = 10080 = 12 × 840 ✓
```

### Q3: Number of Factors
Find the number of factors of 720.

**Solution:**
```
720 = 2⁴ × 3² × 5
Factors = (4+1)(2+1)(1+1) = 5×3×2 = 30
```

### Q4: Remainder
Find the remainder when 2²⁰⁰ is divided by 7.

**Solution:**
```
2³ = 8 ≡ 1 (mod 7)
200 = 66×3 + 2
2²⁰⁰ = (2³)⁶⁶ × 2² ≡ 1⁶⁶ × 4 ≡ 4 (mod 7)
Remainder = 4
```

### Q5: HCF and LCM Relationship
If HCF of two numbers is 12 and their LCM is 720, and one number is 72, find the other.

**Solution:**
```
a × b = HCF × LCM
72 × b = 12 × 720
b = 8640/72 = 120
```

### Q6: Sum Problem
Find the sum of all 3-digit numbers divisible by 7.

**Solution:**
```
First: 105 (7×15), Last: 994 (7×142)
Count: 142 - 15 + 1 = 128
Sum = 128 × (105+994)/2 = 128 × 549.5 = 70,336
```

### Q7: Co-prime Check
Are 17 and 23 co-prime?

**Solution:**
```
Both are prime numbers ≠ each other
HCF(17, 23) = 1
Yes, they are co-prime
```

### Q8: Power Remainder
Find the last digit of 7²⁰²³.

**Solution:**
```
Cyclicity of 7: 7, 9, 3, 1 (cycle length 4)
2023 mod 4 = 3
3rd in cycle: 3
Last digit = 3
```

## Summary Table

| Concept | Formula |
|---------|---------|
| HCF (prime factor) | Product of lowest powers of common primes |
| LCM (prime factor) | Product of highest powers of all primes |
| HCF × LCM | = a × b |
| Number of factors | (a₁+1)(a₂+1)...(aₖ+1) |
| Div by 3/9 | Sum of digits ÷ 3/9 |
| Div by 11 | (Odd pos sum - Even pos sum) ÷ 11 |
| Sum of first N | N(N+1)/2 |
| Sum of first N squares | N(N+1)(2N+1)/6 |
| Sum of first N cubes | [N(N+1)/2]² |
| AP sum | N/2 × (2a + (N-1)d) |
| GP sum | a(r^N-1)/(r-1) |
| Fermat's Little Theorem | a^(p-1) ≡ 1 (mod p) |
