# Speculative Decoding: Draft, Verify, Accept

Autoregressive LLM decoding is memory-bandwidth-bound: each generated
token requires reading every weight once, so a single token's latency is
the cost of streaming the model - regardless of batch size one. Speculative
decoding breaks that 1-token-per-weight-scan contract: a cheap *draft*
model (or the target model itself, restructured) proposes a block of
tokens, and the target model verifies the whole block in ONE forward pass
- a parallel scoring pass that costs one weight-scan but can emit several
tokens. The magic is the correctness argument: with the right acceptance
rule, the output distribution is *identical* to sampling from the target
model alone. This page builds that argument, the throughput math, and the
self-speculative successors (Medusa, EAGLE).

Serving context lives in [vLLM internals](./vllm-internals.md) (the
serving engine where this ships), [PagedAttention](./paged-attention.md)
(the KV-memory machinery speculative decoding composes with), and
[KV cache management](../llm-serving/kv-cache.md).

## The draft-then-verify loop

```text
  for each step:
    draft model (small, fast) autoregressively proposes k tokens:
        t1, t2, ... tk        (k forward passes of a TINY model)
    target model scores all k+1 prefixes in ONE pass (parallel):
        p(x | prefix), p(x | prefix,t1), ..., p(x | prefix,t1..tk)
    accept/reject each token left-to-right; on first rejection,
    resample from the corrected distribution and stop the block
```

The target pass is the same size as one ordinary decode step (one weight
scan) - that is the entire trick. Whether the step wins depends on the
*acceptance rate* of the draft: if the draft's tokens are usually what the
target would have sampled, each weight-scan of the target yields several
tokens.

## The rejection-sampling correctness argument

Let the draft's distribution at a position be `q(x)` and the target's
`p(x)`. Proposed token `x ~ q`. Accept with probability
`min(1, p(x)/q(x))`. On rejection, sample from the residual
distribution:

```text
  p'(x) = normalize( max(0, p(x) - q(x)) )
```

Then the accepted token's distribution is exactly `p`:

- acceptance chooses x with probability `q(x) * min(1, p/q) = min(q, p)`,
- rejection adds `max(0, p - q)` (total rejection mass = 1 - sum(min(q,p))
  = sum(max(0, p - q)), so the residual is exactly what's needed),
- `min(q,p) + max(0, p-q) = p` pointwise. QED.

No approximation, no temperature-dependent drift: speculative decoding is
a *sampling-equivalent* accelerator, which is why it composes with
temperature, top-p and beam tricks (they change `p`; the argument applies
to whatever `p` is).

## Throughput math: when does it pay?

Per target-model forward pass, the expected number of emitted tokens is

```text
  E[accepts] = (1 - alpha^(k+1)) / (1 - alpha)      (accept prob alpha, iid approx)
```

alpha is the per-token acceptance probability - essentially the agreement
between draft and target on the argmax/conditional. The cost model: one
target pass costs `C_T` (dominated by weight streaming), each draft token
costs `C_D`. Net win condition:

```text
  E[tokens/step] / (C_T + k * C_D)   >   1 / C_T
  <=>  E[accepts] > 1 + k * C_D / C_T
```

For C_D/C_T ~ 1/30 (a 1B draft under a 30B target, bandwidth-bound) and
k=4, you need E[accepts] > 1.13 - an alpha of about 0.65 under the iid
model. Draft selection is therefore the whole game: too weak a draft
lowers alpha; too strong a draft raises C_D. The demo below runs the
exact arithmetic on a parameter grid and then *verifies* the residual
distribution identity numerically.

```python
#!/usr/bin/env python3
"""Speculative decoding: two deterministic models.

1. Expected tokens per target forward pass, over a (alpha, k, cost-ratio)
   grid - with the break-even line printed.

2. Rejection-sampling correctness check: with arbitrary p, q over a toy
   alphabet, simulate accept/residual sampling for 200k trials and
   compare the empirical distribution to p (total-variation distance)."""

def expected_tokens(alpha, k):
    if abs(1 - alpha) < 1e-12:
        return k + 1
    return (1 - alpha ** (k + 1)) / (1 - alpha)


print("=== A. E[tokens per target pass] and break-even ===")
print(f"{'alpha':>6} | {'k=2':>6} | {'k=4':>6} | {'k=8':>6}")
for alpha in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
    print(f"{alpha:>6.2f} | {expected_tokens(alpha,2):>6.3f} | "
          f"{expected_tokens(alpha,4):>6.3f} | {expected_tokens(alpha,8):>6.3f}")
print()
C_T, C_D = 1.0, 1 / 30
print(f"cost model: C_T=1 target pass, C_D=1/30 draft pass (30x smaller draft)")
for k in (2, 4, 8):
    be = 1 + k * C_D / C_T
    print(f"  k={k}: need E[accepts] > {be:.3f} -> "
          f"alpha > ~{[a for a in (0.4,0.5,0.6,0.7,0.8,0.9) if expected_tokens(a,k) > be][0]:.2f}")

print()
print("=== B. rejection sampling reproduces the target distribution ===")
import random
rng = random.Random(42)
ALPHA_V = [0.20, 0.30, 0.35, 0.15]      # toy target p
Q_V     = [0.35, 0.25, 0.25, 0.15]      # toy draft q

def normalize(v):
    s = sum(v)
    return [x / s for x in v]

def residual(p, q):
    r = [max(0.0, pi - qi) for pi, qi in zip(p, q)]
    s = sum(r)
    return [x / s for x in r] if s > 0 else p

def sample(cdf_v, u):
    acc = 0.0
    for x, v in enumerate(cdf_v):
        acc += v
        if u <= acc:
            return x
    return len(cdf_v) - 1

p, q = normalize(ALPHA_V), normalize(Q_V)
res = residual(p, q)
trials = 200_000
counts = [0] * len(p)
for _ in range(trials):
    x = sample(q, rng.random())                      # draft proposes
    u = rng.random()
    if u < min(1.0, p[x] / q[x]):                    # accept
        counts[x] += 1
    else:                                            # residual resample
        counts[sample(res, rng.random())] += 1

emp = [c / trials for c in counts]
tv = 0.5 * sum(abs(e - pi) for e, pi in zip(emp, p))
print(f"target p = {p}")
print(f"draft  q = {q}")
print(f"residual = {normalize([max(0.0, pi - qi) for pi, qi in zip(p, q)])}")
print(f"empirical (200k accept/residual trials) = {[round(e,4) for e in emp]}")
print(f"total-variation distance to p = {tv:.4f}  (0 = identical)")
assert tv < 0.01
print("assertion passed: accepted tokens are distributed exactly as p")
```

```text
=== A. E[tokens per target pass] and break-even ===
 alpha |    k=2 |    k=4 |    k=8
  0.40 |  1.560 |  1.650 |  1.666
  0.50 |  1.750 |  1.938 |  1.996
  0.60 |  1.960 |  2.306 |  2.475
  0.70 |  2.190 |  2.773 |  3.199
  0.80 |  2.440 |  3.362 |  4.329
  0.90 |  2.710 |  4.095 |  6.126

cost model: C_T=1 target pass, C_D=1/30 draft pass (30x smaller draft)
  k=2: need E[accepts] > 1.067 -> alpha > ~0.40
  k=4: need E[accepts] > 1.133 -> alpha > ~0.40
  k=8: need E[accepts] > 1.267 -> alpha > ~0.40

=== B. rejection sampling reproduces the target distribution ===
target p = [0.2, 0.3, 0.35, 0.15]
draft  q = [0.35, 0.25, 0.25, 0.15]
residual = [0.0, 0.3333333333333333, 0.6666666666666666, 0.0]
empirical (200k accept/residual trials) = [0.1987, 0.2986, 0.3523, 0.1504]
total-variation distance to p = 0.0027  (0 = identical)
assertion passed: accepted tokens are distributed exactly as p
```

## Self-speculative: Medusa and EAGLE

Training a separate draft model is operational overhead; the successors
extract drafts from the target model itself:

- **Medusa** (2024): extra decoding heads on the target's top layer
  propose continuations in parallel (one per head), verified by the same
  target pass; a tree-attention variant proposes trees of continuations.
- **EAGLE** (2024): a small autoregressive head operates on the target's
  *feature layer* (pre-logits) rather than tokens - feature-level
  uncertainty is more predictable, pushing acceptance rates up
  substantially; its "rethinking" thesis is that token-level sampling is
  the wrong abstraction for the draft.

Both keep the exact-distribution guarantee because verification is still
the target's own probabilities. The engineering frontier is batching:
speculative decoding's serial draft phase interacts badly with high
batch sizes (the KV working set grows while acceptance variance rises),
which is why production deployments (vLLM, TensorRT-LLM) expose it as a
per-request or per-batch-size toggle rather than a default.

## Interview probes

- Prove the residual construction yields exactly p, including the
  corner case q(x) > p(x) everywhere... (show it cannot happen and why
  the total mass works out).
- Your draft has alpha=0.55: find the k that maximizes tokens per
  *second*, and explain why the optimum k is finite even as alpha rises.
- Why does speculative decoding help memory-bound serving more than
  compute-bound training-style workloads? (Answer in bytes of weight
  traffic per token.)
- What breaks if the draft is sampled greedily while the target is
  sampled at temperature 1? Where does the correctness argument bite?

## References

1. Leviathan, Kalman, Matias, "Fast Inference from Transformers via
   Speculative Decoding", [arXiv:2211.17192](https://arxiv.org/abs/2211.17192)
   - the acceptance rule and the E[accepts] analysis this page uses.
2. Chen, Borgeaud, Irving, Lespiau, Sifre, Jumper, "Accelerating Large
   Language Model Decoding with Speculative Sampling",
   [arXiv:2302.01318](https://arxiv.org/abs/2302.01318) - the independent
   formulation and the sampling-equivalence proof.
3. Cai et al., "Medusa: Simple LLM Inference Acceleration Framework with
   Multiple Decoding Heads", [arXiv:2401.10774](https://arxiv.org/abs/2401.10774)
   - the self-speculative multi-head variant.
4. Li et al., "EAGLE: Speculative Sampling Requires Rethinking Feature
   Uncertainty", [arXiv:2401.15077](https://arxiv.org/abs/2401.15077)
   - feature-level drafting and the acceptance-rate gains.
