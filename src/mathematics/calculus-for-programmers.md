# Calculus for Programmers

Calculus is the mathematical study of continuous change. For programmers, it's most relevant in **machine learning** (gradient descent, backpropagation), **graphics** (curves, surfaces), and **simulation**.

---

## Derivatives

### Intuition

The derivative measures **rate of change** — how much one quantity changes when another changes slightly.

```
f'(x) = lim(h→0) [f(x+h) - f(x)] / h
```

Geometrically, the derivative at a point is the **slope of the tangent line** to the function at that point.

### Common Derivatives

| Function f(x) | Derivative f'(x) |
|--------------|-----------------|
| x^n | n × x^(n-1) |
| e^x | e^x |
| ln(x) | 1/x |
| sin(x) | cos(x) |
| cos(x) | -sin(x) |
| a^x | a^x × ln(a) |

### Chain Rule

For composite functions: `d/dx[f(g(x))] = f'(g(x)) × g'(x)`

**Why it matters:** Neural network backpropagation is essentially repeated application of the chain rule through layers.

### Partial Derivatives

When a function depends on multiple variables, the partial derivative measures change with respect to one variable while holding others constant.

```
f(x, y) = x² + xy + y²
∂f/∂x = 2x + y    (treat y as constant)
∂f/∂y = x + 2y    (treat x as constant)
```

The collection of all partial derivatives forms the **gradient** vector: ∇f = [∂f/∂x, ∂f/∂y, ...]

---

## Gradient Descent

Gradient descent is an **optimization algorithm** that finds the minimum of a function by iteratively moving in the direction of steepest descent (negative gradient).

### Algorithm

```
1. Start with initial parameters θ₀
2. Repeat until convergence:
   θ = θ - α × ∇L(θ)
   where α is the learning rate, ∇L(θ) is the gradient of the loss
```

### Intuition

Imagine standing on a foggy mountain and wanting to reach the valley. You can't see the bottom, but you can feel the slope under your feet. You take steps in the downhill direction. The **learning rate (α)** controls step size — too large and you overshoot; too small and it takes forever.

### Variants

| Variant | Key Idea | Interview Relevance |
|---------|---------|-------------------|
| Batch GD | Use all data per step | Deterministic but slow |
| Stochastic GD (SGD) | Use one sample per step | Noisy but fast |
| Mini-batch GD | Use batch of samples | Best of both |
| Momentum | Accumulate velocity | Faster convergence |
| Adam | Adaptive learning rates | Most popular in practice |

---

## Integration

### Intuition

Integration is the reverse of differentiation. It measures **accumulation** — the area under a curve.

### Definite Integral

```
∫[a,b] f(x)dx = F(b) - F(a)
```

Where F(x) is the antiderivative of f(x).

### Applications in Programming

| Application | Calculus Concept |
|------------|------------------|
| Computing averages of continuous values | Integration |
| Total distance from velocity function | Integral of velocity |
| Probability (area under PDF) | Definite integral |
| Physics simulations | Numerical integration (Euler, RK4) |
| Signal processing | Fourier transforms |

---

## Numerical Methods

In practice, we often compute derivatives and integrals numerically:

### Numerical Derivative

```
f'(x) ≈ [f(x + h) - f(x - h)] / (2h)    # Central difference (O(h²) error)
f'(x) ≈ [f(x + h) - f(x)] / h            # Forward difference (O(h) error)
```

### Numerical Integration

```
∫[a,b] f(x)dx ≈ Σ f(xᵢ) × Δx              # Riemann sum
∫[a,b] f(x)dx ≈ (Δx/2)[f(a) + 2Σf(xᵢ) + f(b)]  # Trapezoidal rule
```

---

## Interview Questions

### Beginner

**Q: What is a derivative, in plain English?**
A derivative tells you how fast something is changing at a specific moment. If position is a function of time, the derivative is velocity. If you're driving and your position changes by 60 miles in 1 hour, your average rate of change (derivative) is 60 mph.

**Q: Why is gradient descent used instead of just setting the derivative to zero?**
Setting the derivative to zero (analytical solution) works for simple functions but is often impossible for complex, high-dimensional loss functions in machine learning. Gradient descent works for any differentiable function, even when no closed-form solution exists.

### Intermediate

**Q: What happens if the learning rate is too high or too low in gradient descent?**
Too high: the algorithm overshoots the minimum and may diverge (loss increases). Too low: convergence is extremely slow, requiring many iterations. In practice, use learning rate scheduling (start high, decay over time) or adaptive methods like Adam.

**Q: Explain the chain rule with a programming analogy.**
If `loss = g(f(x))`, then `d(loss)/dx = g'(f(x)) * f'(x)`. In a neural network, if layer 3 depends on layer 2 which depends on layer 1, the gradient of the loss with respect to layer 1 weights is the product of gradients through each layer — this is backpropagation.

### Advanced

**Q: What is the difference between local and global minima, and how does this affect ML?**
A local minimum is the lowest point in a neighborhood; a global minimum is the lowest point overall. In high-dimensional spaces (neural networks), saddle points are more common than local minima. SGD with momentum helps escape shallow local minima, and the loss landscape of neural networks is generally benign enough that local minima have similar loss to the global one.

---

## References

- 3Blue1Brown, *Essence of Calculus* (YouTube)
- [Khan Academy: Calculus](https://www.khanacademy.org/math/calculus-1)
- [Calculus for Machine Learning](https://explained.ai/matrix-calculus/)