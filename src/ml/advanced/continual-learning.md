# Continual Learning: Catastrophic Forgetting and Its Mitigations

Train a model on task B and its task-A accuracy collapses - not gradually,
but catastrophically: gradient descent overwrites the weights that encoded
the old skill with no memory of what they were for. Continual learning is
the discipline of sequencing tasks without that destruction, and it is
exactly the gap between "fine-tuned models" and "deployed assistants that
keep learning". This page builds the forgetting mechanics on a toy model
you can run, covers the three mitigation families (regularization, replay,
architecture), and shows where the modern LLM answer - parameter-efficient
adaptation - sits in that taxonomy.

Broader serving context: [RLHF/DPO](../llm-serving/rlhf.md) pipelines face
the same problem (alignment updates eroding base-model capability), and
[model compression](./model-compression.md) interacts with it (quantized
weights have less headroom to absorb drift).

## Why forgetting is structural, not incidental

SGD minimizes the *current* objective; nothing in the update remembers
that some weights matter to other objectives. The failure mode is
visible even in a two-parameter linear model: task B's loss surface has
zero gradient in the directions that only task A cares about, so updates
wander through them freely. Three families fight this:

| family        | mechanism                                        | cost                       | examples            |
|---------------|--------------------------------------------------|-----------------------------|---------------------|
| regularization| penalize moving weights that old tasks depend on | needs old-task Fisher info  | EWC, SI, MAS        |
| replay        | retrain on stored (or generated) old samples     | memory + mixing schedule    | Experience Replay, DER++ |
| architecture  | dedicate/gate capacity per task                  | capacity growth or routing  | Progressive Nets, adapters, LoRA |

The modern LLM stack quietly chose the architectural family: LoRA adapters
freeze the base model and learn small low-rank deltas per task/domain -
forgetting the base becomes *impossible* by construction, at the price of
managing an adapter zoo instead of one evolving model.

## Elastic Weight Consolidation, mechanically

EWC (Kirkpatrick et al., 2017) keeps a per-weight importance F_i (the
Fisher information: how much the old task's loss changes when weight i
wiggles) and adds a quadratic penalty:

```text
  L_total = L_new(theta) + (lambda/2) * sum_i F_i * (theta_i - theta*_i)^2
```

where theta* are the weights after the old task. Weights the old task
found important (high F_i) are tethered in place; unimportant ones move
freely. The demo below implements exactly this on a two-parameter linear
regression pair of tasks - small enough to see the tension numerically.

```python
#!/usr/bin/env python3
"""Toy catastrophic forgetting + EWC demo.

Two linear regression tasks in 2-D:
  task A: fit y = a1*x1 + a2*x2 on data clustered along x1
  task B: fit a different linear map on data clustered along x2
Plain SGD on B (from A's solution) wanders through directions A cares
about -> forgetting. EWC tethers the high-Fisher weights -> retention.

Pure python (no numpy): 2x2 matrices as nested lists, hand-rolled grads.
Deterministic data + fixed iteration counts."""


def mat2(a, b, c, d):
    return [[a, b], [c, d]]


def dot2(M, v):
    return [M[0][0]*v[0] + M[0][1]*v[1], M[1][0]*v[0] + M[1][1]*v[1]]


def taskA_data():
    # y depends mostly on x1 (x2 ~ noise) -> Fisher concentrates on w1
    return [((1.0, 0.1), 2.0), ((1.2, -0.1), 2.4), ((0.8, 0.2), 1.6),
            ((1.1, 0.0), 2.2), ((0.9, 0.1), 1.8)]

def taskB_data():
    # y depends mostly on x2 -> pulls w2 hard, indifferent to w1
    return [((0.1, 1.0), 3.0), ((-0.1, 1.2), 3.6), ((0.2, 0.8), 2.4),
            ((0.0, 1.1), 3.3), ((0.1, 0.9), 2.7)]


def mse(w, data):
    return sum((dot2([[w[0], 0], [0, w[1]]], x)[0]*0 + (w[0]*x[0] + w[1]*x[1]) - y) ** 2
               for x, y in data) / len(data)


def grad(w, data):
    g0 = g1 = 0.0
    for x, y in data:
        e = (w[0]*x[0] + w[1]*x[1]) - y
        g0 += 2 * e * x[0]
        g1 += 2 * e * x[1]
    return [g0 / len(data), g1 / len(data)]


def fisher_diag(w, data):
    """diagonal Fisher via the Laplace approximation at the old optimum.
    For least squares the Gauss-Newton Hessian is 2*E[x_i^2] - evaluating
    squared gradients of the fitted residuals instead would give exactly
    zero here (regression residuals vanish at the optimum), which is the
    degenerate case the classification derivation sidesteps by sampling
    y from the model's predictive distribution."""
    n = len(data)
    f0 = 2 * sum(x[0] * x[0] for x, _y in data) / n
    f1 = 2 * sum(x[1] * x[1] for x, _y in data) / n
    return [f0, f1]


ITERS = 800
LR = 0.02    # keep LR*LAM*F well under 2 or the EWC spring oscillates

# Phase 1: train task A
w = [0.0, 0.0]
A = taskA_data()
for _ in range(ITERS):
    g = grad(w, A)
    w = [w[0] - LR * g[0], w[1] - LR * g[1]]
w_A = list(w)
print(f"after task A:  w = {[round(x, 3) for x in w]}   "
      f"lossA = {mse(w, A):.4f}  lossB = {mse(w, taskB_data()):.4f}")

F = fisher_diag(w_A, A)
print(f"diagonal Fisher under A: F = {[round(f, 3) for f in F]}"
      f"   (w1 important, w2 nearly free)")

# Phase 2: plain SGD on B -> forgetting
w_plain = list(w_A)
B = taskB_data()
for _ in range(ITERS):
    g = grad(w_plain, B)
    w_plain = [w_plain[0] - LR * g[0], w_plain[1] - LR * g[1]]
print(f"plain SGD on B: w = {[round(x, 3) for x in w_plain]}  "
      f"lossB = {mse(w_plain, B):.4f}  lossA = {mse(w_plain, A):.4f}  <-- FORGOTTEN")

# Phase 3: EWC on B -> retention
w_ewc = list(w_A)
LAM = 20.0   # spring stiffness: LR*LAM*F0 ~= 0.8, stable and strong
for _ in range(ITERS):
    g = grad(w_ewc, B)
    # penalty gradient: lambda * F_i * (w_i - w*_i)
    g[0] += LAM * F[0] * (w_ewc[0] - w_A[0])
    g[1] += LAM * F[1] * (w_ewc[1] - w_A[1])
    w_ewc = [w_ewc[0] - LR * g[0], w_ewc[1] - LR * g[1]]
print(f"EWC on B:       w = {[round(x, 3) for x in w_ewc]}  "
      f"lossB = {mse(w_ewc, B):.4f}  lossA = {mse(w_ewc, A):.4f}  <-- retained")

print()
print(f"task-A loss after learning B: plain SGD = {mse(w_plain, A):.4f}, "
      f"EWC = {mse(w_ewc, A):.4f}  (EWC cuts forgetting by "
      f"{mse(w_plain, A) / mse(w_ewc, A):.1f}x)")
print(f"task-B loss achieved: plain = {mse(w_plain, B):.4f}, "
      f"EWC = {mse(w_ewc, B):.4f}  (the plasticity price)")
assert mse(w_plain, A) > 0.05, "plain SGD should forget task A (absolute loss)"
assert mse(w_ewc, A) < 0.5 * mse(w_plain, A), "EWC should halve task-A forgetting"
print("assertions passed: EWC halves forgetting while still fitting B")
```

```text
after task A:  w = [1.997, 0.062]   lossA = 0.0000  lossB = 8.3192
diagonal Fisher under A: F = [2.04, 0.028]   (w1 important, w2 nearly free)
plain SGD on B: w = [1.453, 2.934]  lossB = 0.0252  lossA = 0.2780  <-- FORGOTTEN
EWC on B:       w = [1.997, 2.297]  lossB = 0.4313  lossA = 0.0733  <-- retained

task-A loss after learning B: plain SGD = 0.2780, EWC = 0.0733  (EWC cuts forgetting by 3.8x)
task-B loss achieved: plain = 0.0252, EWC = 0.4313  (the plasticity price)
assertions passed: EWC halves forgetting while still fitting B
```

Reading the numbers: plain SGD nails task B and wrecks task A (the
forgetting ratio explodes); EWC holds task A's loss near its old value
while still reducing task B's loss substantially - the stability-plasticity
trade visible in a single lambda. Turn lambda up and retention improves
while B's convergence stalls; the production tuning story is exactly that
knob.

## Benchmarks and metrics

Protocol choice changes conclusions, so the vocabulary matters:

- **Task-incremental**: task identity known at test time (easiest;
  head-per-task hides most forgetting).
- **Domain-incremental**: same classes, shifting distribution (the
  realistic deployment shape).
- **Class-incremental**: new classes arrive, no task label at test time
  (hardest; requires the model to disambiguate).

Standard metrics: average accuracy over tasks, **backward transfer**
(performance change on old tasks after new training - the forgetting
measure), forward transfer. ThePermuted-MNIST/Split-CIFAR suites are the
classical arenas; LLM-era evaluations track base-capability retention
across fine-tuning rounds (the same backward-transfer idea in
pretraining-metric clothing).

## Where production systems land

- **LLM fine-tuning**: LoRA/adapters (architectural family) - the base
  is frozen, "forgetting" the base is structurally impossible; the open
  problem moved to *adapter interference* when multiple LoRAs compose.
- **RLHF**: reward-model updates erode alignment - KL penalties to the
  reference policy are EWC's idea in policy clothing (the KL term is the
  Fisher tether).
- **Edge/robotics**: replay is standard (store a small buffer of raw
  episodes); EWC variants where storage is impossible.
- **Fleet models**: staged rollout plus shadow evaluation of old-task
  metrics is the honest operational answer - continual learning research
  has not yet produced a drop-in replacement for "retrain on a
  mixture that includes the old data".

## Interview probes

- Derive the EWC penalty from a Laplace approximation around the old
  task's optimum - where exactly does the Fisher information enter?
- Why does class-incremental learning expose forgetting that
  task-incremental hides? (Answer with the output-head argument.)
- Replay buffers trade memory for plasticity: derive the mixing ratio's
  effect on backward transfer in the two-task toy above.
- Your LoRA-fine-tuned assistant lost its math ability: why is "add
  math data to the next fine-tune" not obviously the fix, and what would
  you measure first?

## References

1. Kirkpatrick, Pascanu, Rabinowitz, et al., "Overcoming catastrophic
   forgetting in neural networks", PNAS 2017,
   [arXiv:1612.00796](https://arxiv.org/abs/1612.00796) - EWC, the
   Fisher-tethering penalty the demo implements.
2. Rolnick et al., "Experience Replay for Continual Learning", NeurIPS
   2019, [arXiv:1811.11682](https://arxiv.org/abs/1811.11682) - the
   replay family's baseline results.
3. Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models",
   [arXiv:2106.09685](https://arxiv.org/abs/2106.09685) - the
   architectural answer now standard in LLM fine-tuning.
4. [RLHF (this repo)](../llm-serving/rlhf.md) - the KL-to-reference
   tether as the same idea in policy optimization.
