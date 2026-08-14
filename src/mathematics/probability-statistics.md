# Probability and Statistics for Programmers

Probability and statistics are essential for data science, A/B testing, randomized algorithms, and system design interviews.

---

## Probability Fundamentals

### Basic Rules

- **Addition rule:** P(A or B) = P(A) + P(B) - P(A and B)
- **Multiplication rule:** P(A and B) = P(A) × P(B|A)
- **Complement:** P(not A) = 1 - P(A)
- **Independence:** P(A and B) = P(A) × P(B) (when independent)

### Conditional Probability

P(A|B) = P(A and B) / P(B)

This is the probability of A **given** that B has occurred. It's the foundation of Bayes' theorem.

### Bayes' Theorem

```
P(A|B) = P(B|A) × P(A) / P(B)
```

**Interview application:** Bayes' theorem is used in spam filtering (Naive Bayes), medical testing interpretation, and A/B testing.

**Example:** A disease affects 1% of the population. A test is 99% accurate (both sensitivity and specificity). If you test positive, what's the probability you actually have the disease?

```
P(disease|positive) = P(positive|disease) × P(disease) / P(positive)
P(positive) = 0.99 × 0.01 + 0.01 × 0.99 = 0.0198
P(disease|positive) = 0.99 × 0.01 / 0.0198 = 0.5 (only 50%!)
```

This is the **base rate fallacy** — a common interview trap.

---

## Random Variables and Distributions

### Discrete Distributions

| Distribution | PMF | Mean | Variance | Use Case |
|-------------|-----|------|----------|----------|
| Bernoulli | p^x(1-p)^(1-x) | p | p(1-p) | Coin flip, success/failure |
| Binomial | C(n,x) p^x(1-p)^(n-x) | np | np(1-p) | Number of successes in n trials |
| Poisson | (λ^x e^(-λ))/x! | λ | λ | Event rate (requests/second) |
| Geometric | (1-p)^(x-1)p | 1/p | (1-p)/p² | Trials until first success |

### Continuous Distributions

| Distribution | Use Case | Key Property |
|-------------|----------|-------------|
| Uniform | Random sampling | Equal probability in range |
| Normal (Gaussian) | Natural phenomena, errors | 68-95-99.7 rule |
| Exponential | Time between events | Memoryless property |
| Log-normal | Response times, income | Always positive, right-skewed |

### The Normal Distribution

The most important distribution in statistics. Key facts:

- **68%** of data within 1σ of mean
- **95%** within 2σ
- **99.7%** within 3σ
- Standard normal: Z = (X - μ) / σ

---

## Expected Value and Variance

### Expected Value (Mean)

```
E[X] = Σ x × P(X = x)    (discrete)
E[X] = ∫ x × f(x) dx      (continuous)
```

**Properties:** E[aX + b] = aE[X] + b, E[X + Y] = E[X] + E[Y]

### Variance

```
Var(X) = E[(X - μ)²] = E[X²] - (E[X])²
StdDev(X) = √Var(X)
```

**Properties:** Var(aX + b) = a²Var(X), Var(X + Y) = Var(X) + Var(Y) (if independent)

### Linearity of Expectation

E[X₁ + X₂ + ... + Xₙ] = E[X₁] + E[X₂] + ... + E[Xₙ]

This holds **even if the variables are dependent** — extremely useful in interviews.

**Example:** Expected number of fixed points in a random permutation of n elements = 1 (each position has 1/n probability, n × 1/n = 1).

---

## A/B Testing

### Hypothesis Testing Framework

1. **Null hypothesis (H₀):** No difference between A and B
2. **Alternative hypothesis (H₁):** There is a difference
3. **Test statistic:** Compute from sample data
4. **P-value:** Probability of observing the result if H₀ is true
5. **Significance level (α):** Typically 0.05
6. **Decision:** Reject H₀ if p-value < α

### Common Tests

| Test | When to Use | Interview Context |
|------|-----------|-------------------|
| Z-test | Large samples, known variance | Conversion rate comparison |
| T-test | Small samples, unknown variance | Feature comparison |
| Chi-squared | Categorical data | Click-through rates |
| Mann-Whitney | Non-normal distributions | Latency comparisons |

### Statistical Power

Power = P(reject H₀ | H₁ is true) = 1 - β

**Interview tip:** Low power means you might miss a real effect. To increase power: increase sample size, increase significance level, or reduce variance.

---

## Interview Questions

### Beginner

**Q: What is the difference between probability and statistics?**
Probability starts with a known model and predicts future data. Statistics starts with observed data and infers the underlying model. Probability: model → prediction. Statistics: data → model.

**Q: What is the law of large numbers?**
As sample size increases, the sample mean converges to the expected value. This is why more data gives better estimates, and why Monte Carlo simulations work.

### Intermediate

**Q: A load balancer sends requests to 3 servers randomly. What's the probability server 1 gets exactly 5 out of 12 requests?**
Binomial distribution: C(12,5) × (1/3)^5 × (2/3)^7 ≈ 0.2384. This uses the binomial formula with n=12, k=5, p=1/3.

**Q: Explain p-value in simple terms.**
The p-value is the probability of seeing results at least as extreme as what you observed, assuming the null hypothesis is true. A small p-value (typically < 0.05) suggests the observed effect is unlikely to be due to random chance alone.

### Advanced

**Q: How would you design an A/B test for a new feature?**
1. Define primary metric (conversion rate, latency p99)
2. Calculate required sample size (power analysis: effect size, α=0.05, power=0.8)
3. Randomly split traffic (50/50), ensure no selection bias
4. Run for sufficient duration (account for day-of-week effects)
5. Check for novelty effect and interaction effects
6. Analyze with appropriate statistical test
7. Report confidence intervals, not just p-values
8. Consider multiple testing correction if measuring many metrics

---

## References

- [Khan Academy: Statistics and Probability](https://www.khanacademy.org/math/statistics-probability)
- Jake VanderPlas, *Python Data Science Handbook* (Chapter on Statistics)
- [Seeing Theory](https://seeing-theory.brown.edu/) — Visual introduction to probability and statistics
