# Time & Work

Time and work problems test your ability to calculate efficiency, combined work rates, and completion times. The LCM method is the most powerful approach.

## Core Concepts

### Basic Relationship

```
Work = Rate × Time
Rate = Work / Time
Time = Work / Rate
```

If a person completes a job in N days, their one-day work = 1/N.

**Example:** If A can do a job in 10 days, A's one-day work = 1/10.

### LCM Method (Recommended)

The LCM method standardizes the total work to a common value, making calculations easier.

**Steps:**
1. Take LCM of all given times → this becomes total work
2. Find each person's rate = Total work / Their time
3. Add/subtract rates as needed
4. Find time = Total work / Combined rate

**Example:** A can do a job in 10 days, B in 15 days. How long together?

```
LCM(10, 15) = 30 → Total work = 30 units
A's rate = 30/10 = 3 units/day
B's rate = 30/15 = 2 units/day
Together = 5 units/day
Time = 30/5 = 6 days
```

## Two People Working Together

### Formula

If A takes `a` days and B takes `b` days:

```
Together, they take = ab/(a+b) days
```

This is the harmonic mean formula.

**Example:** A = 12 days, B = 18 days:
```
Together = (12×18)/(12+18) = 216/30 = 7.2 days
```

### Verification with LCM

```
LCM(12, 18) = 36
A's rate = 3, B's rate = 2, Combined = 5
Time = 36/5 = 7.2 ✓
```

## Three People Working Together

### Formula

If A takes `a`, B takes `b`, C takes `c` days:

```
Together = abc/(ab + bc + ca) days
```

**Example:** A = 10, B = 15, C = 20:
```
Together = (10×15×20)/(10×15 + 15×20 + 20×10)
= 3000/(150 + 300 + 200)
= 3000/650 = 4.615 days
```

## Work Done in Portions

### "A and B work for x days, then A leaves"

**Problem:** A can do a job in 20 days, B in 30 days. A and B work together for 5 days, then A leaves. How long does B take to finish?

**Solution (LCM method):**
```
Total work = LCM(20,30) = 60 units
A's rate = 3/day, B's rate = 2/day
Together rate = 5/day
Work done in 5 days = 25 units
Remaining = 60 - 25 = 35 units
B alone = 35/2 = 17.5 days
```

### "A works for x days, then B joins"

**Problem:** A starts a job and works alone for 4 days. Then B joins and they finish in 3 more days. A alone takes 10 days, B alone takes 15 days. Verify.

**Solution:**
```
Total work = LCM(10, 15) = 30 units
A's rate = 30/10 = 3 units/day
B's rate = 30/15 = 2 units/day
A works alone for 4 days → 3×4 = 12 units done
Remaining = 30 - 12 = 18 units
A+B together = 5 units/day → 18/5 = 3.6 days
Total time = 4 + 3.6 = 7.6 days
```

If instead A works 3 days alone and then B joins for 3 more days: 3×3 + 5×3 = 9 + 15 = 24 units, leaving 6 units unfinished — so the problem data must be consistent.

## Efficiency Concept

### What is Efficiency?

Efficiency = Work done per day = 1/T × 100% (where T = total days)

If A takes 10 days, efficiency = 100/10 = 10%
If B takes 15 days, efficiency = 100/15 = 6.67%

### Efficiency Ratio

If A is twice as efficient as B:
- A does 2x work per day, B does x work per day
- A will take half the time B takes
- Ratio of times = 1:2 (A:B)
- Ratio of work done in same time = 2:1 (A:B)

**Key insight:** Efficiency is inversely proportional to time.

```
Efficiency_A / Efficiency_B = Time_B / Time_A
```

## Pipes and Cisterns

Pipes and cisterns are time and work problems with a twist: some pipes fill (positive work) and some empty (negative work).

### Basic Pipe Problems

**Inlet pipe** fills a tank in a hours → rate = +1/a per hour
**Outlet pipe** empties a tank in b hours → rate = -1/b per hour

### Two Inlet Pipes

**Problem:** Pipe A fills a tank in 12 hours, Pipe B fills in 15 hours. How long together?

**Solution:**
```
LCM(12, 15) = 60
A's rate = 5/hour, B's rate = 4/hour
Together = 9/hour
Time = 60/9 = 6.67 hours
```

### Inlet + Outlet

**Problem:** Pipe A fills in 10 hours, Pipe B empties in 15 hours. If both are open, how long to fill?

**Solution:**
```
LCM(10, 15) = 30
A fills 3/hour, B empties 2/hour
Net rate = 3 - 2 = 1/hour
Time = 30/1 = 30 hours
```

### Three Pipes (Fill, Fill, Empty)

**Problem:** A fills in 6 hours, B fills in 8 hours, C empties in 12 hours. All open, time to fill?

**Solution:**
```
LCM(6, 8, 12) = 24
A: 4/hr, B: 3/hr, C: -2/hr
Net = 4 + 3 - 2 = 5/hr
Time = 24/5 = 4.8 hours
```

### Pipe Fills in Stages

**Problem:** A fills in 20 hours. Due to a leak, it takes 25 hours. How long does the leak take to empty the full tank?

**Solution:**
```
A's rate = 1/20
A+Leak rate = 1/25
Leak rate = 1/25 - 1/20 = (4-5)/100 = -1/100
Leak empties in 100 hours
```

## Men-Women-Children Problems

These combine efficiency ratios with the work formula.

**Problem:** 2 men or 3 women or 4 children can do a job in 12 days. How long for 1 man + 1 woman + 1 child?

**Solution:**
```
2M = 3W = 4C (in terms of work)
LCM(2, 3, 4) = 12
Let total work = 12 units
2M do 12 units in 12 days → 1M does 0.5/day
3W do 12 units in 12 days → 1W does 0.333/day
4C do 12 units in 12 days → 1C does 0.25/day
1M + 1W + 1C = 0.5 + 0.333 + 0.25 = 1.083/day
Time = 12/1.083 = 11.08 days
```

### Shortcut

```
1M = 3W/2 = 4C/2 = 2C
So: 1M + 1W + 1C = 2C + (4/3)C + C = (6+4+3)C/3 = 13C/3
4C take 12 days → 13C/3 take = 12 × 4/(13/3) = 12 × 12/13 = 144/13 ≈ 11.08 days
```

## Negative Work

When someone destroys work (like a leak, or a person breaking instead of building):

```
Net rate = Building rate - Destroying rate
```

**Problem:** A builds a wall in 20 days. B can destroy it in 30 days. If they work alternately (A on day 1, B on day 2, ...), when is the wall complete?

**Solution:**
```
LCM(20, 30) = 60 units
A builds 3/day, B destroys 2/day
In 2 days: net work = 3 - 2 = 1 unit
After 58 cycles (116 days): 58 units done
Day 117: A builds 3 → total = 61 > 60 → Done on day 117
Exact: On day 117, A needs to do 2 more units → 2/3 of day
Total = 116 + 2/3 = 116.67 days
```

## Tricks & Shortcuts

### Trick 1: If A and B Together Take T Days

If A alone takes a days and together they take T days:
```
B alone = aT/(a-T)
```

### Trick 2: Alternating Work

If A and B work on alternate days:
- Work done in 2 days = 1/a + 1/b
- Find full cycles needed, then remaining work

### Trick 3: Efficiency Percentage

If A is x% more efficient than B:
- A's time = B's time × 100/(100+x)
- B's time = A's time × (100+x)/100

### Trick 4: Half the Time, Double the Rate

Rate and time are inversely proportional:
```
If time doubles, rate halves (and vice versa)
```

### Trick 5: Fraction of Work Remaining

If x/a + x/b = 1 (where x is time worked together):
```
x = ab/(a+b) → same as the together formula
```

## Practice Questions

### Q1: Basic Together
A can do a job in 12 days, B in 18 days. They work together for 4 days, then A leaves. How long does B take to finish?

**Solution:**
```
Total work = 36
A: 3/day, B: 2/day
In 4 days together: 5×4 = 20
Remaining: 16
B alone: 16/2 = 8 days
```

### Q2: Pipes
A pipe fills a cistern in 6 hours, another fills in 8 hours, and a third empties in 12 hours. All are opened. When will the cistern be full?

**Solution:**
```
LCM(6,8,12) = 24
Rates: 4/hr + 3/hr - 2/hr = 5/hr
Time = 24/5 = 4 hours 48 minutes
```

### Q3: Efficiency
If A is 50% more efficient than B, and together they finish in 12 days, find individual times.

**Solution:**
```
Let B's rate = 2x, A's rate = 3x
Together = 5x
If together = 12 days, total work = 60x
A alone = 60x/3x = 20 days
B alone = 60x/2x = 30 days
```

### Q4: Men and Days
10 men can do a job in 12 days. 15 women can do the same job in 16 days. How long for 5 men and 8 women?

**Solution:**
```
10M × 12 = 120 man-days → 1M = 1/120 per day
15W × 16 = 240 woman-days → 1W = 1/240 per day
5M + 8W = 5/120 + 8/240 = 1/24 + 1/30 = (5+4)/120 = 9/120 = 3/40
Time = 40/3 = 13.33 days
```

### Q5: Leak Problem
A cistern is filled by a pipe in 4 hours. Due to a leak, it takes 5 hours. How long does the leak take to empty the cistern?

**Solution:**
```
Pipe rate = 1/4
Pipe + Leak = 1/5
Leak = 1/5 - 1/4 = -1/20
Leak empties in 20 hours
```

### Q6: Alternating Days
A does a job in 10 days, B in 15 days. They work on alternate days starting with A. When is the job done?

**Solution:**
```
Total work = 30
A: 3/day, B: 2/day
In 2 days: 5 units
After 6 cycles (12 days): 30 units = Done!
Answer: 12 days
```

### Q7: Partial Work
A and B can do a job in 12 days. B and C in 15 days. C and A in 20 days. How long for A alone?

**Solution:**
```
A+B = 1/12, B+C = 1/15, C+A = 1/20
2(A+B+C) = 1/12 + 1/15 + 1/20 = (5+4+3)/60 = 12/60 = 1/5
A+B+C = 1/10
A = (A+B+C) - (B+C) = 1/10 - 1/15 = (3-2)/30 = 1/30
A alone = 30 days
```

### Q8: Three-Way Efficiency
2 men = 3 women = 4 boys in terms of work capacity. A job needs 12 men working 8 hours/day for 10 days. How many days for 6 women and 4 boys working 6 hours/day?

**Solution:**
```
2M = 3W = 4B → 1M = 1.5W = 2B
Total work = 12 × 8 × 10 = 960 man-hours
6W = 4M, 4B = 2M → Total = 6M
6M working 6 hrs/day: 36 man-hours/day
Days = 960/36 = 26.67 days
```

## Summary Table

| Concept | Formula |
|---------|---------|
| Two people together | ab/(a+b) |
| Three people together | abc/(ab+bc+ca) |
| One-day work | 1/N (if N days total) |
| LCM method | Total work = LCM of times |
| Inlet + Outlet | Net rate = Fill - Empty |
| Efficiency ∝ | 1/Time (inversely proportional) |
| A more efficient by x% than B | A's time = B's time × 100/(100+x) |
| Leak with pipe | Leak = 1/T_with_leak - 1/T_pipe |
