# Chapter 72: Probability and Expected Value

## Prerequisites

- Basic combinatorics
- Modular arithmetic

## Interview Frequency: ★★★

Probability problems appear in interviews at **Google**, **Two Sigma**, **Jane Street**, and **Meta**. Expected value calculations are particularly common in DP and game theory problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Expected value | ★★★★ | Medium | DP with probabilities |
| Linearity of expectation | ★★★★ | Medium | Powerful technique |
| Birthday paradox | ★★★ | Medium | Hash collision analysis |
| Coupon collector | ★★ | Medium | Expected time analysis |

---

## 72.1 Conditional Probability and Bayes' Theorem

```
P(A|B) = P(A ∩ B) / P(B)
P(A|B) = P(B|A) × P(A) / P(B)   [Bayes' theorem]
```

```cpp
#include <iostream>
#include <iomanip>

// Bayes' theorem example: Medical test
// P(Disease) = 0.01 (prevalence)
// P(Positive|Disease) = 0.99 (sensitivity)
// P(Positive|No Disease) = 0.05 (false positive rate)
// Question: P(Disease|Positive) = ?

double bayesTheorem(double pA, double pBgA, double pBgNotA) {
    // P(A|B) = P(B|A)*P(A) / (P(B|A)*P(A) + P(B|~A)*P(~A))
    return pBgA * pA / (pBgA * pA + pBgNotA * (1 - pA));
}

int main() {
    double pDisease = 0.01;
    double pPosGivenDisease = 0.99;
    double pPosGivenNoDisease = 0.05;
    
    double pDiseaseGivenPos = bayesTheorem(pDisease, pPosGivenDisease, pPosGivenNoDisease);
    
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "P(Disease|Positive) = " << pDiseaseGivenPos << "\n";
    // ~0.1667 — surprisingly low due to low prevalence!
    
    return 0;
}
```

---

## 72.2 Expected Value and Linearity of Expectation

**Expected value**: E[X] = Σ x × P(X = x)

**Linearity of expectation**: E[X + Y] = E[X] + E[Y] (always, even if X and Y are dependent!)

### Example: Expected Number of Dice Rolls to Get a 6

```cpp
#include <iostream>
#include <iomanip>

// E[rolls until first 6] = 1/P(6) = 6
// This follows from geometric distribution

// More complex: Expected number of distinct values when rolling a die n times
double expectedDistinctValues(int sides, int rolls) {
    // For each value, P(it appears at least once) = 1 - (1 - 1/sides)^rolls
    // By linearity: E[distinct] = sides × (1 - (1 - 1/sides)^rolls)
    double pNotAppear = std::pow(1.0 - 1.0 / sides, rolls);
    return sides * (1.0 - pNotAppear);
}

int main() {
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "Expected distinct values (6-sided die, 10 rolls): " 
              << expectedDistinctValues(6, 10) << "\n";
    std::cout << "Expected distinct values (6-sided die, 100 rolls): " 
              << expectedDistinctValues(6, 100) << "\n";
    
    return 0;
}
```

---

## 72.3 Birthday Paradox

With n people and 365 days, the probability that at least two share a birthday:

```
P(collision) ≈ 1 - e^(-n²/(2×365))
```

For n = 23: P ≈ 0.507 (50%!)

### Application to Hashing

This explains why hash collisions happen more often than intuition suggests.

```cpp
#include <iostream>
#include <cmath>
#include <iomanip>

double birthdayParadox(int n, int days = 365) {
    double probNoCollision = 1.0;
    for (int i = 0; i < n; i++) {
        probNoCollision *= (double)(days - i) / days;
    }
    return 1.0 - probNoCollision;
}

int main() {
    std::cout << std::fixed << std::setprecision(4);
    for (int n : {10, 20, 23, 30, 50, 70, 100}) {
        std::cout << "n=" << n << ": P(collision) = " 
                  << birthdayParadox(n) << "\n";
    }
    return 0;
}
```

---

## 72.4 Coupon Collector Problem

Expected number of trials to collect all n coupons:

```
E[T] = n × (1 + 1/2 + 1/3 + ... + 1/n) = n × H(n)
```

where H(n) is the n-th harmonic number ≈ n × ln(n).

```cpp
#include <iostream>
#include <cmath>
#include <iomanip>

double couponCollector(int n) {
    return n * std::log(n) + 0.5772 * n + 0.5; // Euler-Mascheroni approximation
}

int main() {
    std::cout << std::fixed << std::setprecision(2);
    for (int n : {10, 52, 100, 1000}) {
        std::cout << "Expected trials for " << n << " coupons: " 
                  << couponCollector(n) << "\n";
    }
    // For a deck of 52 cards: ~236 draws to see all cards
    return 0;
}
```

---

## 72.5 Indicator Variables

Define indicator random variables to simplify expected value calculations.

### Example: Expected Number of Fixed Points in a Random Permutation

Let Xi = 1 if element i is in position i, 0 otherwise.

E[Xi] = 1/n for each i.

E[total fixed points] = Σ E[Xi] = n × (1/n) = 1.

**Surprising result**: Expected number of fixed points is always 1, regardless of n!

```cpp
#include <iostream>
#include <random>
#include <vector>
#include <algorithm>
#include <iomanip>

double simulateFixedPoints(int n, int trials) {
    std::mt19937 rng(42);
    int totalFixed = 0;
    
    for (int t = 0; t < trials; t++) {
        std::vector<int> perm(n);
        std::iota(perm.begin(), perm.end(), 0);
        std::shuffle(perm.begin(), perm.end(), rng);
        
        for (int i = 0; i < n; i++) {
            if (perm[i] == i) totalFixed++;
        }
    }
    
    return (double)totalFixed / trials;
}

int main() {
    std::cout << std::fixed << std::setprecision(3);
    for (int n : {5, 10, 50, 100, 1000}) {
        double avg = simulateFixedPoints(n, 100000);
        std::cout << "n=" << n << ": avg fixed points = " << avg << "\n";
    }
    // All close to 1.0!
    
    return 0;
}
```

---

## Summary

| Concept | Formula/Insight | Application |
|---|---|---|
| Bayes' Theorem | P(A\|B) = P(B\|A)P(A)/P(B) | Medical tests, spam filters |
| Linearity | E[X+Y] = E[X]+E[Y] | Counting problems |
| Birthday Paradox | P ≈ 1 - e^(-n²/2d) | Hash collision analysis |
| Coupon Collector | E = n × H(n) ≈ n ln n | Coverage problems |
| Indicator Variables | E[Xi] = P(Xi=1) | Simplify calculations |

---

## Exercises

1. **Dice expectation**: Roll two dice. What's the expected value of their sum? What about their product?

2. **Card matching**: A deck of n cards is shuffled. What's the expected number of cards that remain in their original position?

3. **Random walk**: A drunk person takes steps +1 or -1 with equal probability. After n steps, what's E[position²]?

4. **Loaded coin**: A coin lands heads with probability p. What's the expected number of flips to get k consecutive heads?

5. **Birthday paradox**: How many people are needed for a >50% chance that two share a birthday? Verify with simulation.

---

## Interview Questions

1. **Q: What is linearity of expectation and why is it powerful?**
   A: E[X + Y] = E[X] + E[Y] always, even if X and Y are dependent. This lets us decompose complex expectations into sums of simple indicator variables.

2. **Q: Explain the birthday paradox.**
   A: With 23 people, there's a >50% chance two share a birthday. The key insight: we're checking all pairs (~253 pairs for 23 people), not comparing each person to a specific date.

3. **Q: What's the expected number of rolls to see all 6 faces of a die?**
   A: By the coupon collector problem: 6(1 + 1/2 + 1/3 + 1/4 + 1/5 + 1/6) = 14.7 rolls.

4. **Q: How do you use indicator variables for expected value?**
   A: Define I_j = 1 if event j occurs, 0 otherwise. Then E[total] = Σ E[I_j] = Σ P(event j). This simplifies many problems.

5. **Q: A random permutation of n elements — what's the expected number of cycles?**
   A: H(n) = 1 + 1/2 + 1/3 + ... + 1/n ≈ ln(n). Each element has probability 1/k of starting a new cycle among the first k elements.

---

## Cross-References

- [Chapter 61: Game Theory](ch61-game-theory.md) — Expected value in game contexts
- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md) — Probability DP
- [Chapter 114: Probability DP](ch114-probability-dp.md) — DP with probabilistic transitions
- [Chapter 71: Combinatorics](ch71-combinatorics.md) — Counting techniques for probability
