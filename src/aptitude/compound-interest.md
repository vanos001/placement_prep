# Compound and Simple Interest

## Overview

Interest problems appear in nearly every placement test, from mass-recruiter aptitude sections to product-company screening tests, and they carry a double payoff: the same compound-growth mechanics reappear later in population-growth, depreciation, and installment questions. The key distinction is that simple interest is calculated only on the original principal, while compound interest is calculated on the principal plus all previously accumulated interest, so the balance grows linearly in one case and geometrically in the other. Mastering the handful of formulas below — plus the conversion rule for compounding frequency and the rule of 72 — covers essentially every variant that appears under exam conditions. Worked examples throughout use rupee amounts and round to two decimals, matching how these questions are asked in real drives.

## Simple Interest (SI)

Simple interest charges a fixed percentage of the original principal every year, regardless of how much has already accumulated. Because the yearly interest never changes, the total interest is directly proportional to time, which is why SI questions reduce to a single multiplication.

```
SI = (P × R × T) / 100
```

Where P = principal, R = rate per annum (%), T = time in years.

**Example:** ₹5,000 at 8% for 3 years.
```
SI = (5000 × 8 × 3) / 100 = ₹1,200
Total amount = 5000 + 1200 = ₹6,200
```

Two derived facts from this formula show up as standalone questions. A sum doubles in \\( 100/R \\) years at simple interest, because doubling requires interest equal to the principal. And SI is always the same fraction of the principal per year, so equal principal-rate-time SI problems can be compared by inspection without computing anything.

## Compound Interest (CI)

Under compounding, each period's interest is added to the balance and earns interest itself, so the amount multiplies by a constant factor every period. This geometric growth is the entire content of the formula.

```
A = P × (1 + R/100)^T
CI = A - P = P × [(1 + R/100)^T - 1]
```

**Example:** ₹5,000 at 8% compounded annually for 3 years.
```
A = 5000 × (1.08)^3 = 5000 × 1.259712 = ₹6,298.56
CI = 6298.56 - 5000 = ₹1,298.56
```

### Formula Derivation

The formula is not arbitrary — it falls out of one repeated multiplication. In year 1 the balance grows from \\( P \\) to \\( P(1 + r/100) \\), where \\( r \\) is the annual rate. In year 2 the *new balance* earns interest, so you multiply by the same factor again, giving \\( P(1 + r/100)^2 \\); after \\( n \\) years the exponent counts the multiplications:

\\( A = P(1 + r/100)^n \\)

The same expansion explains the CI-SI difference formulas in the shortcuts section. Writing \\( x = r/100 \\), the compound amount after 2 years is \\( P(1+x)^2 = P(1 + 2x + x^2) \\) while simple interest gives \\( P(1 + 2x) \\); the difference is exactly \\( P x^2 \\) — the \\( x^2 \\) term is "interest on interest." For 3 years the expansion \\( (1+x)^3 = 1 + 3x + 3x^2 + x^3 \\) produces the \\( P x^2 (3 + x) \\) difference used in practice questions, so the shortcut formulas are just binomial terms, not magic.

## CI vs SI: Worked Contrast

| Years | SI on ₹10,000 at 10% | CI on ₹10,000 at 10% | Difference |
|-------|----------------------|----------------------|------------|
| 1 | ₹1,000 | ₹1,000 | ₹0 |
| 2 | ₹2,000 | ₹2,100 | ₹100 |
| 3 | ₹3,000 | ₹3,310 | ₹310 |

Read the difference column the way the exam wants you to. In year 1 the two agree, because one period of interest cannot compound. In year 2 the extra ₹100 is exactly one year of interest *on the year-1 interest* (10% of ₹1,000). In year 3 the extra ₹310 decomposes as interest-on-interest from year 2 (₹100 growing to ₹110, i.e. ₹210 total) plus ₹100 of interest on the year-2 interest — the gap is itself compounding, which is why the difference column accelerates. This is also why, for 2-year problems, the exam-favorite identity `CI − SI = P × (R/100)²` reproduces the table: 10000 × (0.10)² = ₹100.

**Key insight:** The difference grows over time because CI earns interest on interest, and it grows faster at higher rates — which is why short-term CI and SI questions are distinguishable only through the difference formulas, not through intuition.

### Year-by-Year Balance Contrast

The clearest way to *see* compounding is to track both balances period by period on ₹10,000 at 10%:

| Year | SI balance (grows by ₹1,000) | CI balance (grows by 10% of itself) |
|------|------------------------------|-------------------------------------|
| 0 | ₹10,000 | ₹10,000 |
| 1 | ₹11,000 | ₹11,000 |
| 2 | ₹12,000 | ₹12,100 |
| 3 | ₹13,000 | ₹13,310 |
| 4 | ₹14,000 | ₹14,641 |

The SI column adds the same ₹1,000 every year; the CI column multiplies by 1.1, so its yearly increment grows — ₹1,000, ₹1,100, ₹1,210, ₹1,331. Each CI increment is the previous one times 1.1, which is the geometric sequence hiding inside the formula. When an exam asks "in which year does the gap exceed ₹1,000?" you can answer from this table (between years 3 and 4) without touching the closed-form expressions.

## Compounding Frequency: Yearly vs Half-Yearly vs Quarterly

When compounding happens \\( n \\) times per year, two conversions are applied to the annual formula and nothing else changes: the rate divides by \\( n \\) and the number of periods multiplies by \\( n \\).

```
A = P × (1 + R/(n × 100))^(n × T)
```

| Compounding | n |
|-------------|---|
| Annually | 1 |
| Semi-annually | 2 |
| Quarterly | 4 |
| Monthly | 12 |

The conversion rule is easy to misapply in one specific way: exam problems state the *annual* rate and ask for half-yearly compounding, and the correct move is rate ÷ n with time × n — not rate ÷ n with time unchanged. Both the rate divisor and the exponent multiplier come from the same fact that a "period" is now a fraction of a year. More frequent compounding always yields *more* amount than annual compounding at the same nominal rate, because interest starts earning interest sooner.

**Worked example 1 (half-yearly):** ₹10,000 at 10% per annum for 2 years, compounded half-yearly.
```
Rate per period  = 10/2 = 5%
Number of periods = 2 × 2 = 4
A = 10000 × (1.05)^4 = 10000 × 1.21550625 = ₹12,155.06
CI = ₹2,155.06   (annual compounding would give only ₹2,100)
```

**Worked example 2 (quarterly):** ₹8,000 at 12% per annum for 1 year, compounded quarterly.
```
Rate per period  = 12/4 = 3%
Number of periods = 1 × 4 = 4
A = 8000 × (1.03)^4 = 8000 × 1.12550881 = ₹9,004.07
CI = ₹1,004.07   (annual compounding would give ₹960)
```

### Effective Annual Rate

```
Effective rate = (1 + R/(n×100))^n - 1
```

The effective annual rate restates a multi-period nominal rate as the single annual rate that would produce the same amount, which is the right way to compare products with different compounding frequencies. For 12% compounded quarterly: (1.03)^4 − 1 = 12.55% effective rate, meaning quarterly compounding "secretly" pays 55 basis points more than the nominal figure. Exams test this as a direct formula question and, more deviously, in reverse — giving the effective rate and asking for the nominal one.

### Fractional Years

When time is not a whole number of years, say 2.5 years, do **not** round the exponent. The standard treatment splits the problem: compound for the whole years, then apply simple interest for the leftover fraction, giving \\( A = P(1+r/100)^2 \\times (1 + 0.5 \\times r/100) \\) for 2.5 years. Exam papers at the mass-recruiter level almost always use this split convention, and stating it explicitly earns the method mark even if arithmetic slips later. Some advanced questions instead compound the full fraction \\( (1+r/100)^{2.5} \\), so read the question's wording — "compounded annually, for 2.5 years" signals the split method.

## Installment Problems

Installment questions ask: a loan is repaid in equal annual installments; find the installment. The governing principle is **present value**: each future installment, discounted back at the loan's interest rate, must sum to the principal borrowed. Equivalently, if the loan were invested at that rate, it would grow to exactly cover the installments as they fall due. Set up the equation first and let algebra, not intuition, produce the answer — guessing "principal ÷ number of installments" ignores the interest entirely.

**Worked example 1 (2 installments):** A loan of ₹4,200 is repaid in two equal annual installments at 10% per annum. Find each installment.

Let each installment be ₹\\( X \\). The installment paid after 1 year discounts back one year, and the one after 2 years discounts back two years:

\\( X/1.1 + X/1.21 = 4200 \\)

Writing \\( 1/1.1 = 10/11 \\) and \\( 1/1.21 = 100/121 \\):

\\( X \\times (110 + 100)/121 = 4200 \\Rightarrow X \\times 210/121 = 4200 \\Rightarrow X = 4200 \\times 121/210 = 2420 \\)

Each installment is **₹2,420**. Verify in the forward direction, which is the habit that catches sign errors: ₹4,200 grows to ₹4,620 in one year, minus ₹2,420 leaves ₹2,200; that grows to ₹2,420 in the second year, which the second installment clears exactly.

**Worked example 2 (3 installments):** A loan of ₹3,310 is repaid in three equal annual installments at 10% per annum. Find each installment.

\\( X(10/11 + 100/121 + 1000/1331) = 3310 \\)

The bracket sums to \\( (1210 + 1100 + 1000)/1331 = 3310/1331 \\), so \\( X = 3310 \\times 1331/3310 = 1331 \\).

Each installment is **₹1,331**. The forward check makes the structure visible, year by year: ₹3,310 grows to ₹3,641, minus ₹1,331 leaves ₹2,310; that grows to ₹2,541, minus ₹1,331 leaves ₹1,210; that grows to ₹1,331, which the last installment clears exactly to zero. Forward verification takes thirty seconds and turns an answer you hope is right into one you know is right.

## Population Growth and Depreciation

The compound formula transfers unchanged to any quantity that grows or shrinks by a fixed percentage per period — population, machine value, property price, bacterial count. Growth uses a plus sign; depreciation uses a minus:

```
Growth:        A = P × (1 + R/100)^n
Depreciation:  A = P × (1 - R/100)^n
```

**Population example:** A town of 2,00,000 grows at 5% per year for 2 years.
```
A = 200000 × (1.05)^2 = 200000 × 1.1025 = 2,20,500
```

**Depreciation example:** A machine worth ₹4,00,000 depreciates at 10% per year for 3 years.
```
A = 400000 × (0.9)^3 = 400000 × 0.729 = ₹2,91,600
```

Two variants extend these and appear in harder papers. If growth is \\( R_1\\% \\) for some years and \\( R_2\\% \\) afterwards, multiply the factors in sequence rather than averaging the rates. And if a population *declines* to a given fraction of itself ("declines to 0.64 of its value in 2 years"), equate \\( (1-R/100)^n \\) to the fraction and take roots — here \\( 1 - R/100 = 0.8 \\), so R = 20%.

## Mental Shortcuts

**Shortcut 1:** If CI and SI on the same principal at the same rate for 2 years are given, the difference equals:
```
CI - SI = P × (R/100)^2
```

**Shortcut 2:** For 3 years, the difference equals:
```
CI - SI = P × (R/100)^2 × (3 + R/100)
```

Both follow from the binomial expansion in the derivation section, and both let you answer "find the difference" questions without computing CI and SI separately — a 30-second save that matters in 60-second-per-question sections.

**Shortcut 3: The rule of 72.** Money doubles in roughly \\( 72/R \\) years when compounded at \\( R\\% \\) per year: at 8% about 9 years, at 12% about 6 years, at 6% about 12 years. The constant comes from the natural logarithm of 2 (≈ 0.693, i.e. about 69.3) adjusted upward to 72 because 72 has more divisors and compensates for annual rather than continuous compounding. The rule is most accurate between roughly 6% and 10%; outside that band, adjust mentally (at 4-5% use ~70-72, at higher rates use slightly less than 72/R). The exact-doubling frame also reverses into rate questions: "in how many years does this double?" becomes one division instead of a logarithm.

**Shortcut 4: Memorize the 10% ladder.** Powers of 1.1 recur constantly because exam-setters love 10%:
```
(1.1)^1 = 1.1    (1.1)^2 = 1.21    (1.1)^3 = 1.331    (1.1)^4 = 1.4641
```
Amounts of ₹10,000 at 10% for 2 and 3 years (₹12,100 and ₹13,310) then read off directly, and any problem whose amount ratio equals 1.331 is a disguised 10%-for-3-years problem — as in practice question 9 below. The 5% ladder ((1.05)^2 = 1.1025, (1.05)^4 = 1.21550625) covers most half-yearly problems the same way.

## Practice Questions

| # | Question | Answer (worked) |
|---|----------|-----------------|
| 1 | CI on ₹8,000 at 5% for 2 years | \\( 8000 \\times 1.05^2 = 8820 \\); CI = **₹820** |
| 2 | A sum doubles in 10 years at SI. Find the rate. | Doubling needs SI = P: \\( P = P \\times R \\times 10/100 \\Rightarrow \\) **10%** |
| 3 | CI on ₹5,000 for 2 years is ₹820. Find the rate. | \\( (1+r)^2 = 5820/5000 = 1.164 \\Rightarrow r \\approx \\) **8%** (7.9% exactly) |
| 4 | ₹10,000 at 10% p.a. for 2 years, compounded half-yearly | \\( 10000 \\times 1.05^4 = \\) ₹12,155.06; CI = **₹2,155.06** |
| 5 | CI − SI on ₹12,000 at 12.5% for 2 years | \\( 12000 \\times (0.125)^2 = \\) **₹187.50** |
| 6 | A sum triples in 2 years at CI. Find the rate. | \\( (1+r)^2 = 3 \\Rightarrow r = \\sqrt{3} - 1 \\approx \\) **73.2%** |
| 7 | Population of 50,000 grows 2% per year for 2 years | \\( 50000 \\times 1.0404 = \\) **52,020** |
| 8 | Machine worth ₹1,00,000 depreciates 20% per year for 2 years | \\( 100000 \\times 0.64 = \\) **₹64,000** |
| 9 | ₹5,000 amounts to ₹6,655 in 2 years at CI. Find the rate. | \\( 6655/5000 = 1.331 = 1.1^2 \\Rightarrow \\) **10%** |
| 10 | Loan of ₹2,100 repaid in 2 equal annual installments at 10% | \\( X(10/11 + 100/121) = 2100 \\Rightarrow X = \\) **₹1,210** |

Question 6 is the one worth re-reading: "triples" means the *amount* ratio is 3, not the interest, so the equation is \\( (1+r)^2 = 3 \\) — candidates who write CI = 3P consistently overshoot. Question 9 rewards the 10% ladder from the shortcuts section, since recognizing 1.331 converts a root-taking exercise into a lookup.

## Interview Questions

1. **Why is compound interest always at least as large as simple interest on the same principal and rate?** Each period of CI applies the rate to a balance that includes previously credited interest, so the growth factor compounds multiplicatively, while SI applies the rate to the frozen original principal and grows linearly. The two are equal for exactly one period (or a zero rate), because one period of compounding cannot compound. From period 2 onward the gap equals the interest earned on interest, which the 2-year identity \\( P(R/100)^2 \\) quantifies exactly. In interviews, demonstrating this with the year-by-year table rather than asserting the formula is what scores.

2. **How does compounding frequency change the effective cost of a loan?** The nominal annual rate stays fixed, but dividing it over \\( n \\) periods multiplies the number of growth steps, so the effective annual rate is \\( (1 + R/(n \\times 100))^n - 1 \\) — 12% nominal quarterly is 12.55% effective. As \\( n \\) grows the effective rate approaches the continuously compounded limit \\( e^{R/100} - 1 \\), which for 12% is about 12.75%. The practical interview point is comparison: offers or products with different compounding frequencies must be compared on effective, not nominal, rates.

3. **Where does the rule of 72 come from, and when does it break down?** Solving \\( (1+r)^n = 2 \\) exactly gives \\( n = \\ln 2 / \\ln(1 + r) \\approx 0.693/r \\) for small \\( r \\), and the constant is rounded up to 72 (from 69.3) because 72 divides evenly by 4, 6, 8, 9, and 12 and the rounding compensates for annual-compounding effects. The approximation is excellent between roughly 6% and 10% — at 8% it predicts 9 years against a true 9.006. It degrades at extreme rates (true doubling at 24% takes about 3.2 years, not 3), so state the working range when you invoke it.

4. **A loan is repaid in equal annual installments. What single idea solves every such problem?** Present value: each installment discounted at the loan rate must sum to the principal, \\( X/(1+r) + X/(1+r)^2 + \\dots = P \\), because money repaid later is worth less today at the loan's own interest rate. This one equation handles 2, 3, or \\( n \\) installments, unequal installments, and even "part repayment plus balloon payment" variants by simply adding terms. The complementary verification is to grow the balance forward year by year and check it hits zero exactly — a 30-second audit that catches most algebra slips.

5. **How do you adapt these formulas to population decline or machine depreciation?** Replace the growth factor \\( (1 + R/100) \\) with \\( (1 - R/100) \\) and everything else — the exponent, the frequency conversion, the rule of 72 analog for half-life questions — carries over unchanged. Decline problems sometimes state the result as a fraction ("falls to 0.64 of its value in 2 years"), which you solve by equating \\( (1-R/100)^n \\) to the fraction and taking roots: \\( 0.64 = 0.8^2 \\) gives 20% per year. The trap is mixing directions across periods, e.g. 5% growth for 2 years then 10% decline for 1 year — multiply the three factors in order rather than netting the rates.

## Key Takeaways

- SI is linear in time and charged on the original principal; CI is geometric and charged on the running balance — equal only for one period.
- \\( A = P(1 + r/100)^n \\) is just repeated multiplication by one growth factor; the CI−SI difference formulas are binomial terms of that expansion.
- For \\( n \\) compounding periods per year: rate ÷ n and time × n — both conversions, always together.
- More frequent compounding strictly increases the amount; compare products by effective annual rate \\( (1 + R/(n \\times 100))^n - 1 \\), never by nominal rate.
- Installment problems are present-value equations: discounted installments sum to the principal; verify by growing the balance forward to exactly zero.
- Population growth and depreciation reuse the same formula with a sign flip; multi-rate periods multiply their factors in sequence.
- The rule of 72 gives doubling time \\( 72/R \\) years (best 6-10%), and the 1.1/1.05 power ladders convert most exam numbers into lookups.

## References

- [Compound interest — Wikipedia](https://en.wikipedia.org/wiki/Compound_interest) — history, continuous-compounding limit, and effective-rate formalism
- [Rule of 72 — Wikipedia](https://en.wikipedia.org/wiki/Rule_of_72) — derivation of the doubling-time approximation and its accuracy bands

## Cross-references

- [Percentages](./percentages.md) — percentage change is the substrate every interest formula multiplies
- [Profit and loss](./profit-loss.md) — the same rate-on-base thinking applied to commerce questions
- [Averages](./averages.md) — mean-rate comparisons that appear alongside interest questions in DI sets
- [Ratios and proportions](./ratios-proportions.md) — ratio manipulation used in amount-ratio and installment setups
