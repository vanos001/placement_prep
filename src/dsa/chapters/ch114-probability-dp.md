# Chapter 114: Probability and Expected Value DP

## Prerequisites
- DP basics (Chapters 45–48)
- Probability fundamentals
- Markov chains (basic understanding)

## Interview Frequency: ★★★

Expected value problems appear frequently at **Google**, **Two Sigma**, **Jane Street**, **Citadel**, and **Goldman Sachs**. These problems test your ability to model uncertainty with recurrence relations.

---

## 114.1 Core Concepts

### What is Expected Value DP?

**Expected value** is the average outcome over many trials. When a process has random elements, we can use DP to compute:
- **Expected number of steps** to reach a goal
- **Probability of reaching** a particular state
- **Expected reward/cost** of a strategy

The key insight: **expected values satisfy linear recurrences**, just like regular DP.

### The Fundamental Recurrence

If state `s` transitions to states `s₁, s₂, ..., sₖ` with probabilities `p₁, p₂, ..., pₖ`:

```
E[s] = 1 + Σᵢ pᵢ × E[sᵢ]     (if counting steps)
E[s] = reward(s) + Σᵢ pᵢ × E[sᵢ]  (if counting reward)
```

The `1` represents the step taken from state `s` to its successor.

### When to Use Expected Value DP

| Pattern | Example |
|---|---|
| "How many moves on average?" | Dice games, random walks |
| "What's the probability of winning?" | Gambler's ruin, coin games |
| "What's the expected score?" | Stochastic optimization |
| "Optimal strategy under uncertainty?" | Game theory with randomness |

---

## 114.2 Pattern 1: Expected Number of Steps

### Problem: Expected Dice Throws

**Problem:** You start at position 0 and repeatedly roll a fair die (1–6). What's the expected number of throws to reach or exceed position *n*?

**State:** `E[i]` = expected throws from position `i` to reach `n`

**Base case:** `E[n] = 0` (already there)

**Recurrence:**
```
E[i] = 1 + (E[i+1] + E[i+2] + ... + E[i+6]) / 6
```

The `1` counts the current throw. We take `min(i+d, n)` to cap at `n`.

#### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <iomanip>

double expectedDiceThrows(int n) {
    std::vector<double> E(n + 1, 0.0);
    // E[n] = 0 (base case, already initialized)
    for (int i = n - 1; i >= 0; i--) {
        E[i] = 1.0;  // count this throw
        for (int d = 1; d <= 6; d++)
            E[i] += E[std::min(i + d, n)] / 6.0;
    }
    return E[0];
}

int main() {
    for (int n : {10, 20, 30})
        std::cout << "Expected throws to reach " << n << ": " 
                  << std::fixed << std::setprecision(4) << expectedDiceThrows(n) << "\n";
    return 0;
}
```

#### Python Implementation

```python
from typing import List

def expected_dice_throws(n: int) -> float:
    """Expected number of dice throws to reach or exceed position n."""
    E = [0.0] * (n + 1)
    for i in range(n - 1, -1, -1):
        E[i] = 1.0  # count this throw
        for d in range(1, 7):
            E[i] += E[min(i + d, n)] / 6.0
    return E[0]

for n in [10, 20, 30]:
    print(f"Expected throws to reach {n}: {expected_dice_throws(n):.4f}")
```

#### Java Implementation

```java
public class ExpectedDiceThrows {
    public static double solve(int n) {
        double[] E = new double[n + 1];
        for (int i = n - 1; i >= 0; i--) {
            E[i] = 1.0;
            for (int d = 1; d <= 6; d++)
                E[i] += E[Math.min(i + d, n)] / 6.0;
        }
        return E[0];
    }
    
    public static void main(String[] args) {
        for (int n : new int[]{10, 20, 30})
            System.out.printf("Expected throws to reach %d: %.4f%n", n, solve(n));
    }
}
```

#### Dry Run (n=3)

```
E[3] = 0 (base case)
E[2] = 1 + E[3]/6 + E[3]/6 + E[3]/6 + E[3]/6 + E[3]/6 + E[3]/6
     = 1 + 0 = 1.0
E[1] = 1 + E[2]/6 + E[3]/6 + E[3]/6 + E[3]/6 + E[3]/6 + E[3]/6
     = 1 + 1/6 = 1.1667
E[0] = 1 + E[1]/6 + E[2]/6 + E[3]/6 + E[3]/6 + E[3]/6 + E[3]/6
     = 1 + 1.1667/6 + 1/6 = 1 + 0.1944 + 0.1667 = 1.3611
```

**Answer:** ~1.36 throws on average to reach position 3.

---

## 114.3 Pattern 2: Consecutive Heads

### Problem

**What is the expected number of fair coin flips to get *k* consecutive heads?**

**State:** `dp[i]` = expected flips to get `i` consecutive heads

**Recurrence:**
```
dp[i] = dp[i-1] + 1 + (1/2) × dp[i]
```
Rearranging: `dp[i] = 2 × (dp[i-1] + 1)`

**Intuition:** After getting `i-1` consecutive heads, you flip once. If heads (prob 1/2), you're done. If tails (prob 1/2), you start over from 0. So:
```
dp[i] = dp[i-1] + 1 + (1/2) × 0 + (1/2) × dp[i]
dp[i] - dp[i]/2 = dp[i-1] + 1
dp[i] = 2(dp[i-1] + 1)
```

#### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <iomanip>

double expectedFlipsForKHeads(int k) {
    std::vector<double> dp(k + 1, 0);
    for (int i = 1; i <= k; i++)
        dp[i] = 2.0 * (dp[i - 1] + 1.0);
    return dp[k];
}

int main() {
    for (int k = 1; k <= 5; k++)
        std::cout << "Expected flips for " << k << " consecutive heads: " 
                  << std::fixed << std::setprecision(1) << expectedFlipsForKHeads(k) << "\n";
    return 0;
}
```

#### Python Implementation

```python
def expected_flips_for_k_heads(k: int) -> float:
    """Expected fair coin flips to get k consecutive heads."""
    dp = [0.0] * (k + 1)
    for i in range(1, k + 1):
        dp[i] = 2.0 * (dp[i - 1] + 1.0)
    return dp[k]

for k in range(1, 6):
    print(f"Expected flips for {k} consecutive heads: {expected_flips_for_k_heads(k):.1f}")
```

#### Java Implementation

```java
public class ConsecutiveHeads {
    public static double solve(int k) {
        double[] dp = new double[k + 1];
        for (int i = 1; i <= k; i++)
            dp[i] = 2.0 * (dp[i - 1] + 1.0);
        return dp[k];
    }
    
    public static void main(String[] args) {
        for (int k = 1; k <= 5; k++)
            System.out.printf("Expected flips for %d consecutive heads: %.1f%n", k, solve(k));
    }
}
```

#### Dry Run (k=3)

```
dp[0] = 0
dp[1] = 2 × (0 + 1) = 2
dp[2] = 2 × (2 + 1) = 6
dp[3] = 2 × (6 + 1) = 14
```

**Answer:** 14 expected flips for 3 consecutive heads.

---

## 114.4 Pattern 3: Win/Lose Probability (Gambler's Ruin)

### Problem

**Two gamblers A and B flip a biased coin. A wins each flip with probability p. A starts with `a` dollars, B with `b` dollars. What's the probability that A wins all of B's money?**

**State:** `P[i]` = probability A wins given A currently has `i` dollars

**Base cases:** `P[0] = 0` (A is broke), `P[a+b] = 1` (B is broke)

**Recurrence:** `P[i] = p × P[i+1] + (1-p) × P[i-1]`

**Closed form (fair coin, p=0.5):** `P[a] = a / (a+b)`

**Closed form (biased, p≠0.5):**
```
P[a] = (1 - ((1-p)/p)^a) / (1 - ((1-p)/p)^(a+b))
```

#### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <iomanip>
#include <cmath>

// DP approach for gambler's ruin
double gamblerRuinDP(int a, int b, double p) {
    int total = a + b;
    std::vector<double> P(total + 1, 0.0);
    P[total] = 1.0;  // B is broke, A wins
    
    // Iterative relaxation (Gauss-Seidel style)
    for (int iter = 0; iter < 10000; iter++) {
        for (int i = 1; i < total; i++)
            P[i] = p * P[i + 1] + (1 - p) * P[i - 1];
    }
    return P[a];
}

// Closed form
double gamblerRuinClosed(int a, int b, double p) {
    if (std::abs(p - 0.5) < 1e-9)
        return (double)a / (a + b);
    double r = (1 - p) / p;
    return (1 - std::pow(r, a)) / (1 - std::pow(r, a + b));
}

int main() {
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "Fair (p=0.5), a=3, b=7: " << gamblerRuinClosed(3, 7, 0.5) << "\n";
    std::cout << "Biased (p=0.6), a=3, b=7: " << gamblerRuinClosed(3, 7, 0.6) << "\n";
    std::cout << "Biased (p=0.4), a=3, b=7: " << gamblerRuinClosed(3, 7, 0.4) << "\n";
    return 0;
}
```

#### Python Implementation

```python
def gambler_ruin(a: int, b: int, p: float) -> float:
    """Probability that gambler A (with a dollars) beats B (with b dollars).
    p = probability A wins each flip."""
    if abs(p - 0.5) < 1e-9:
        return a / (a + b)
    r = (1 - p) / p
    return (1 - r**a) / (1 - r**(a + b))

print(f"Fair (p=0.5), a=3, b=7: {gambler_ruin(3, 7, 0.5):.4f}")
print(f"Biased (p=0.6), a=3, b=7: {gambler_ruin(3, 7, 0.6):.4f}")
print(f"Biased (p=0.4), a=3, b=7: {gambler_ruin(3, 7, 0.4):.4f}")
```

---

## 114.5 Pattern 4: Expected Value with Decisions

### Problem: Optimal Dice Strategy

**You roll a die. After each roll, you can either keep the value (game ends) or re-roll (lose the previous value). What's the expected value of the optimal strategy?**

**Key insight:** At each roll, keep it if it's above the expected value of future rolls.

**State:** The expected value of the game is the same at every step (memoryless property).

**Recurrence:**
```
E = (1/6) × max(1, E) + (1/6) × max(2, E) + ... + (1/6) × max(6, E)
```

If E ≥ 6, we always stop → E = 3.5 (contradiction since 3.5 < 6).
If E ∈ [k, k+1), we stop for values > k and re-roll for values ≤ k.

**Solving iteratively:**
```
Start with E = 3.5 (unconditional expectation)
E = (1+2+3)/6 + (4+5+6)/6 × 1/1 ... 
Actually: E = (1/6)(max(1,E) + max(2,E) + ... + max(6,E))
With E = 3.5: stops at 4,5,6; re-rolls 1,2,3
E_new = (3.5+3.5+3.5+4+5+6)/6 = 25.5/6 = 4.25
With E = 4.25: stops at 5,6; re-rolls 1,2,3,4
E_new = (4.25×4 + 5 + 6)/6 = 28/6 = 4.667
Converges to: E ≈ 4.667
```

#### C++ Implementation

```cpp
#include <iostream>
#include <iomanip>
#include <cmath>

double optimalDiceStrategy(int sides = 6) {
    double E = (sides + 1.0) / 2.0;  // start with unconditional expectation
    for (int iter = 0; iter < 100; iter++) {
        double newE = 0;
        for (int face = 1; face <= sides; face++)
            newE += std::max((double)face, E) / sides;
        if (std::abs(newE - E) < 1e-12) break;
        E = newE;
    }
    return E;
}

int main() {
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "Optimal strategy for d6: " << optimalDiceStrategy(6) << "\n";
    std::cout << "Optimal strategy for d10: " << optimalDiceStrategy(10) << "\n";
    std::cout << "Optimal strategy for d20: " << optimalDiceStrategy(20) << "\n";
    return 0;
}
```

#### Python Implementation

```python
def optimal_dice_strategy(sides: int = 6) -> float:
    """Expected value with optimal stop-or-reroll strategy."""
    E = (sides + 1) / 2  # unconditional expectation
    for _ in range(100):
        new_E = sum(max(face, E) for face in range(1, sides + 1)) / sides
        if abs(new_E - E) < 1e-12:
            break
        E = new_E
    return E

for sides in [6, 10, 20]:
    print(f"Optimal strategy for d{sides}: {optimal_dice_strategy(sides):.4f}")
```

---

## 114.6 Pattern 5: Markov Chain Absorption

### Problem: Random Walk on a Line

**A particle starts at position `s` on positions 0..n. At each step, it moves left or right with equal probability. Positions 0 and `n` are absorbing (once reached, stay forever). What's the expected number of steps to absorption?**

**State:** `E[i]` = expected steps from position `i` to absorption

**Base cases:** `E[0] = 0`, `E[n] = 0`

**Recurrence:**
```
E[i] = 1 + 0.5 × E[i-1] + 0.5 × E[i+1]
```

This is a system of linear equations solvable in O(n).

#### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <iomanip>

double randomWalkAbsorption(int n, int s) {
    std::vector<double> E(n + 1, 0.0);
    // E[0] = E[n] = 0 (absorbing states)
    
    // Forward-backward sweep (Gauss-Seidel)
    for (int iter = 0; iter < 10000; iter++) {
        for (int i = 1; i < n; i++)
            E[i] = 1.0 + 0.5 * E[i - 1] + 0.5 * E[i + 1];
    }
    return E[s];
}

// Closed form: E[s] = s * (n - s)
double randomWalkClosed(int n, int s) {
    return (double)s * (n - s);
}

int main() {
    std::cout << std::fixed << std::setprecision(2);
    for (int s = 1; s <= 9; s++) {
        int n = 10;
        std::cout << "E[" << s << "] in [0," << n << "]: DP=" 
                  << randomWalkAbsorption(n, s) << " Closed=" 
                  << randomWalkClosed(n, s) << "\n";
    }
    return 0;
}
```

---

## 114.7 Complexity Analysis

| Problem Type | State Space | Time | Space |
|---|---|---|---|
| Expected steps | O(n) states | O(n) | O(n) |
| Win probability | O(n) states | O(n) | O(n) |
| With decisions | O(n) states | O(n × iterations) | O(n) |
| Multi-dimensional | O(n^d) states | O(n^d) | O(n^d) |
| Markov chain | O(n) states | O(n × iterations) | O(n) |

**Key insight:** The number of iterations for convergence depends on the problem. For finite Markov chains, convergence is guaranteed. For systems with closed forms, solve analytically when possible.

---

## 114.8 Common Pitfalls

1. **Forgetting the +1:** When counting steps, remember to add 1 for the current transition.
2. **Wrong base cases:** Absorbing states have E = 0 (already done) or P = 1 (already won).
3. **Infinite loops in recurrence:** If the recurrence is circular (E depends on E), solve as a system of equations.
4. **Conditional vs unconditional:** Be clear about what the expectation is conditioned on.
5. **Precision issues:** Use `double` not `float`; for competitive programming, check if modular arithmetic is needed.

---

## 114.9 Summary Table

| Pattern | State | Transition | Example |
|---|---|---|---|
| Expected steps | E[s] | E[s] = 1 + Σ p × E[s'] | Dice throws |
| Win probability | P[s] | P[s] = Σ p × P[s'] | Gambler's ruin |
| Expected reward | R[s] | R[s] = reward + Σ p × R[s'] | Coin game |
| Optimal strategy | V[s] | V[s] = max(action) of E[reward + V[s']] | Dice strategy |
| Absorption time | E[s] | E[s] = 1 + Σ p × E[s'] | Random walk |

## Exercises

1. **Easy:** What's the expected number of fair coin flips to get at least one head?
2. **Easy:** In the dice-throw game, verify that the expected throws for n=6 is exactly 7/3.6 ≈ 1.9444.
3. **Medium:** You flip a coin with probability p of heads. What's the expected number of flips to see the pattern HTH?
4. **Medium:** Two players alternately flip a fair coin. The first to flip heads wins. What's the probability the first player wins?
5. **Hard:** You have a biased coin (p heads). You flip until you see k consecutive heads. Derive the expected number of flips as a function of p and k.
6. **Hard:** A random walk starts at position 0 on integers. At each step, move +1 with probability p and -1 with probability 1-p. What's the probability of ever reaching position n > 0?
7. **Hard:** Implement a solver for the "optimal dice strategy" problem with an n-sided die and k allowed re-rolls.

## Interview Questions

1. **Q:** You roll a fair die repeatedly. What's the expected number of rolls until the sum exceeds 100?
   **A:** Use DP where E[s] = expected rolls from sum s. E[s] = 1 + Σ E[min(s+d, 101)]/6 for s ≤ 100.

2. **Q:** In a game, you flip a fair coin. Heads = +1, Tails = -1. You start at 0 and stop when you reach -10 or +10. What's the expected number of flips?
   **A:** This is the random walk absorption problem. E[s] = 1 + 0.5×E[s-1] + 0.5×E[s+1], with E[-10] = E[10] = 0. Closed form: E[0] = 100 (since E[s] = s×(n-s) for symmetric walk).

3. **Q:** You have a bag with 3 red and 7 blue balls. You draw without replacement. What's the expected number of draws until you get a red ball?
   **A:** E = Σ k × P(first red at draw k). Alternatively, by linearity: E = (3/10)×1 + (7/10)×(1 + E_with_2_red_6_blue). Solve recursively.

## Cross-References
- DP fundamentals: Chapter 45
- Game theory DP: Chapter 115
- Probability basics: Chapter 100
- Markov chains: Chapter 101
