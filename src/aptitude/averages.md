# Averages

Average problems appear frequently in placement tests. Mastering the shortcut methods can save significant time.

## Core Concepts

### What is an Average?

The average (arithmetic mean) is the sum of all observations divided by the number of observations.

```
Average = Sum of observations / Number of observations
```

**Example:** Average of 10, 20, 30, 40, 50:
```
Average = (10+20+30+40+50)/5 = 150/5 = 30
```

### Rearranged Formulas

```
Sum = Average × Number of observations
Number = Sum / Average
```

## Weighted Average

When different groups have different averages:

```
Weighted Average = (n₁×avg₁ + n₂×avg₂ + ...) / (n₁ + n₂ + ...)
```

**Example:** Section A (30 students) averages 70, Section B (50 students) averages 80.
```
Combined avg = (30×70 + 50×80)/(30+50)
= (2100 + 4000)/80
= 6100/80 = 76.25
```

## Deviation Method (Most Powerful Shortcut)

Instead of adding everything up, choose an assumed average and calculate deviations from it.

### How it Works

1. **Assume** an average (pick a convenient number)
2. **Calculate** deviations (difference from assumed average) for each observation
3. **Sum** the deviations
4. **Actual average** = Assumed average + (Sum of deviations / Number of observations)

### Example

Find the average of 78, 82, 85, 90, 95.

```
Assume average = 85
Deviations: 78-85=-7, 82-85=-3, 85-85=0, 90-85=5, 95-85=10
Sum of deviations = -7-3+0+5+10 = 5
Actual average = 85 + 5/5 = 85 + 1 = 86
```

### Why This Works

It reduces large number additions to small number additions. For numbers in the 80-90 range, you work with deviations of ±10 instead of the full numbers.

## Key Properties of Averages

### Property 1: Average of Consecutive Numbers

```
Average of first n natural numbers = (n+1)/2
Average of first n even numbers = n+1
Average of first n odd numbers = n
```

### Property 2: If Each Number is Multiplied by k

New average = Old average × k

### Property 3: If Each Number is Increased by k

New average = Old average + k

### Property 4: Average of Evenly Spaced Numbers

Average = (First + Last) / 2

**Example:** Average of 5, 10, 15, 20, 25 = (5+25)/2 = 15

### Property 5: Middle Term in Odd-Count Series

For an odd number of terms in an arithmetic progression, the average equals the middle term.

```
Average of 3, 7, 11, 15, 19 = 11 (middle term)
```

## Common Problem Types

### Type 1: Average with New Member

**Problem:** The average age of 30 students is 14 years. When the teacher's age is included, the average increases by 1. Find the teacher's age.

**Solution:**
```
Sum of students' ages = 30 × 14 = 420
New average (with teacher) = 15
New sum = 31 × 15 = 465
Teacher's age = 465 - 420 = 45 years
```

**Shortcut:** Teacher's age = Old average + (Number of students + 1) × Increase
```
= 14 + (30+1) × 1 = 14 + 31 = 45 years
```

### Type 2: Replacing a Member

**Problem:** The average weight of 8 men increases by 1.5 kg when a 65 kg man is replaced. Find the new man's weight.

**Solution:**
```
Increase in total = 8 × 1.5 = 12 kg
New man's weight = 65 + 12 = 77 kg
```

**Shortcut:** New member = Old member + (Number of people × Change in average)

### Type 3: Excluding a Member

**Problem:** Average of 5 numbers is 42. If one number is excluded, the average becomes 38. Find the excluded number.

**Solution:**
```
Sum of 5 = 5 × 42 = 210
Sum of 4 = 4 × 38 = 152
Excluded number = 210 - 152 = 58
```

### Type 4: Average Speed

**Problem:** A person travels from A to B at 60 km/h and returns at 40 km/h. Find average speed.

**Solution:**
```
Average speed = 2×S₁×S₂/(S₁+S₂) = 2×60×40/(60+40) = 4800/100 = 48 km/h
```

**Important:** Average speed is NOT (60+40)/2 = 50. Always use the harmonic mean formula for equal distances.

### Type 5: Average of Groups

**Problem:** In a class of 60, boys average 70 marks, girls average 80 marks. Overall average is 74. Find number of boys and girls.

**Solution:**
```
Using alligation:
Boys 70     Girls 80
      Avg 74
Ratio of Boys:Girls = (80-74):(74-70) = 6:4 = 3:2
Boys = (3/5) × 60 = 36
Girls = (2/5) × 60 = 24
```

## Advanced Concepts

### Average of First n Natural Numbers

```
Sum = n(n+1)/2
Average = (n+1)/2
```

### Average of Squares

```
Average of squares of first n natural numbers = (n+1)(2n+1)/6
```

### Average of Cubes

```
Average of cubes of first n natural numbers = [n(n+1)/2]²/n = n(n+1)²/4
```

### Running Average

When a new number is added:
```
New average = (Old sum + New number) / (Old count + 1)
= (Old avg × n + New number) / (n + 1)
```

## Tricks & Shortcuts

### Trick 1: Average Doesn't Change with Equal Addition/Subtraction

If you add the same value to all observations, the average increases by that value. If you multiply all by k, the average multiplies by k.

### Trick 2: Average of Consecutive Numbers

For consecutive integers from a to b:
```
Average = (a + b) / 2
```

### Trick 3: Weighted Average Position

If Group A has average a and Group B has average b (a < b), and combined average is m:
```
A:B = (b-m):(m-a)
```

This is essentially alligation applied to averages!

### Trick 4: Deviation Method for Equal Deviations

If deviations from assumed average cancel out (sum to zero), then assumed average = actual average.

### Trick 5: Average Speed for Multiple Distances

If distances d₁, d₂, ... are covered at speeds s₁, s₂, ...:
```
Average speed = Total distance / Total time
= (d₁+d₂+...) / (d₁/s₁ + d₂/s₂ + ...)
```

For equal distances at two speeds:
```
Average speed = 2s₁s₂/(s₁+s₂) (harmonic mean)
```

## Practice Questions

### Q1: Basic Average
Find the average of first 40 natural numbers.

**Solution:**
```
Average = (40+1)/2 = 20.5
```

### Q2: Replacement Problem
The average of 11 results is 60. The first 6 average 58 and the last 6 average 62. Find the 6th result.

**Solution:**
```
Sum of 11 = 11 × 60 = 660
Sum of first 6 = 6 × 58 = 348
Sum of last 6 = 6 × 62 = 372
6th result = 348 + 372 - 660 = 60
```

### Q3: Age Problem
The average age of a family of 4 members is 25 years. A baby is born, and the average becomes 20 years. Find the baby's age.

**Solution:**
```
Sum of 4 = 4 × 25 = 100
Sum of 5 = 5 × 20 = 100
Baby's age = 100 - 100 = 0 (newborn)
```

### Q4: Speed Problem
A car travels 200 km at 50 km/h, then 300 km at 75 km/h. Find average speed.

**Solution:**
```
Time₁ = 200/50 = 4 hours
Time₂ = 300/75 = 4 hours
Average speed = 500/8 = 62.5 km/h
```

### Q5: Group Average
The average marks of 3 sections are 70, 75, and 80 with 40, 30, and 30 students respectively. Find the overall average.

**Solution:**
```
Total marks = (40×70) + (30×75) + (30×80)
= 2800 + 2250 + 2400 = 7450
Total students = 100
Average = 7450/100 = 74.5
```

### Q6: Deviation Method
Find the average of 451, 453, 455, 457, 459, 461, 463.

**Solution:**
```
Assume average = 457 (middle term)
Deviations: -6, -4, -2, 0, 2, 4, 6
Sum = 0
Average = 457 + 0/7 = 457
```

### Q7: Temperature Problem
Average temperature for Monday-Wednesday was 30°C. Tuesday-Thursday was 33°C. Thursday's temperature was 36°C. Find Monday's temperature.

**Solution:**
```
Mon+Tue+Wed = 3 × 30 = 90
Tue+Wed+Thu = 3 × 33 = 99
Thu - Mon = 99 - 90 = 9
Monday = 36 - 9 = 27°C
```

### Q8: Weighted Average
A batsman's average in 15 innings is 40. His highest score exceeds his lowest by 100 runs. If these two innings are excluded, the average of the remaining 13 innings is 38. Find the highest score.

**Solution:**
```
Total of 15 = 15 × 40 = 600
Total of 13 = 13 × 38 = 494
Highest + Lowest = 600 - 494 = 106
Highest - Lowest = 100
Solving: 2 × Highest = 206 → Highest = 103
```

## Summary Table

| Concept | Formula |
|---------|---------|
| Average | Sum / Count |
| Weighted Average | Σ(nᵢ × avgᵢ) / Σnᵢ |
| Average speed (2 equal dist) | 2s₁s₂/(s₁+s₂) |
| New avg after adding member | (Old avg × n + new)/(n+1) |
| Consecutive numbers avg | (First + Last)/2 |
| First n natural numbers avg | (n+1)/2 |
| Deviation method | Assumed avg + Σdeviations/n |
