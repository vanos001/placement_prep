# Mixture of Experts

Mixture of Experts (MoE) is a model architecture where each token's computation passes through only a subset of the model's parameters, chosen dynamically by a router. The full model has many more parameters than a dense transformer of the same FLOPs, but each token only "activates" a small fraction. This page covers the architecture, the routing mechanism, the training challenges (load balancing, capacity), and the production models (Switch Transformer, GLaM, Mixtral, DeepSeek-V3).

## The Architecture

A standard transformer FFN layer computes:

```text
Y = W_2 (GELU (W_1 X))

where:
  X ∈ R^{N × d}   ← input, batch N × hidden d
  W_1 ∈ R^{d × 4d}  ← up-projection
  W_2 ∈ R^{4d × d}  ← down-projection
```

An MoE FFN layer replaces the single W_1, W_2 with N_e experts, each a separate `(d × 4d, 4d × d)` pair:

```text
Router(X) = softmax(X W_R)    ← W_R ∈ R^{d × N_e}, gives per-token expert probabilities
For each token x_i:
  Pick top-K experts (highest probabilities in Router(X))
  Compute: y_i = sum_{j in top-K} (Router(x_i)_j * Expert_j(x_i))
```

Each token's compute is K × (FFN cost) instead of 1 × (FFN cost). For top-1, the cost is the same as a dense FFN. For top-2, 2× the cost. The full model has N_e × FFN parameters (vs dense's 1 × FFN), but only K × FFN are used per token.

## The Router

The router is a small linear layer `W_R ∈ R^{d × N_e}`. Its output (after softmax) is a probability distribution over experts. The router is trained jointly with the experts.

For top-K routing, the top-K probabilities are kept (and re-normalized); the rest are zeroed out. The token is then processed by each selected expert, and the outputs are combined with the (post-softmax) probabilities as weights.

Switch Transformer (top-1) is the simplest: each token goes to exactly one expert. Mixtral 8x7B (top-2) is more common: each token's output is a weighted average of 2 experts' outputs. DeepSeek-V3 (top-8 of 256) uses many experts per token.

## Load Balancing

A naive MoE router collapses: all tokens route to one expert, leaving others idle. The model degenerates to a dense FFN.

The standard fix is an auxiliary loss that penalizes uneven routing:

```text
L_aux = α × sum_i (f_i × P_i)

where:
  f_i = fraction of tokens routed to expert i (over the batch)
  P_i = mean over tokens of router's softmax probability for expert i

The product is minimized when f_i and P_i are equal (i.e., the router sends
1/N_e of tokens to each expert, and the average probability per expert is 1/N_e).
```

`α` is typically 0.01 (small enough not to dominate the main loss). Without this auxiliary loss, MoE training usually fails to balance.

## Capacity and Token Dropping

Each expert has a "capacity" (max tokens per step), typically:

```text
capacity = (N_tokens × K) / N_e × capacity_factor
```

For batch 4096, K=2, N_e=8: capacity = 4096 × 2 / 8 × 1.25 = 1280 tokens per expert per step.

Tokens that arrive after capacity is exceeded are dropped — they don't contribute to the forward pass for that step. The dropped tokens' gradient is zero for that step.

A capacity_factor of 1.0 means each expert's expected load is 1/N_e of tokens × K (perfectly balanced). Factor 1.25 allows 25% slack for imbalance.

## Production MoE Models

### Switch Transformer (Google, 2022)

Top-1 routing, N_e up to 128. The original MoE at scale: 1.6T parameters, ~3× compute reduction vs dense equivalent. Quality matched dense 1T model with 1/3 the FLOPs.

### GLaM (Google, 2021)

Top-2 routing, 1.2T parameters, 64 experts. Showed that MoE with auxiliary loss can train stably at 1T+ scale.

### Mixtral 8x7B (Mistral, 2023)

Top-2 routing, 8 experts × 7B each = 47B total, ~13B per-token activated parameters. Matches dense Llama-2 70B on most benchmarks with ~5× less compute. The first open-weights MoE that production teams could deploy.

### Mixtral 8x22B (Mistral, 2024)

Top-2 of 8 experts × 22B each = 141B total. Matches GPT-3.5 quality; open-weights, runs on a single 8×A100 node.

### DeepSeek-V3 (2024)

Top-8 of 256 experts, plus 1 "shared expert" (always activated). 671B total, ~37B per-token activated. The shared expert handles universal computation; the routed experts handle specialized patterns. The DeepSeek team reports the shared expert makes the router converge much faster and reduces the auxiliary loss's role.

## Routing Variants

### Top-1 (Switch)

Pros: minimal compute (1 expert per token), simple router.
Cons: lower quality per FLOP (only one expert's contribution).

### Top-2 (Mixtral)

Pros: better quality per FLOP (weighted average of 2 experts).
Cons: 2× compute per token, 2× communication (2 experts to send to in EP).

### Top-K of many (DeepSeek)

Pros: more granular specialization; can model fine-grained patterns.
Cons: K × compute per token, complex routing.

### Expert Choice routing (Zhou et al., 2022)

Instead of routing tokens to experts, route experts to tokens. Each expert picks the top-N tokens it wants to process. This is provably load-balanced (no auxiliary loss needed). Quality is comparable to top-K routing.

### Hash routing (Lewis et al., 2021)

Replace the learned router with a hash function (token ID mod N_e). Eliminates the router parameters and the auxiliary loss, at the cost of fixed token-to-expert assignment. Used in some Retrieval-Augmented MoE models.

## Training Challenges

1. **Load imbalance**: the auxiliary loss must be tuned (α=0.01 typical); too high hurts task loss, too low collapses routing.

2. **Capacity dropping**: ~1-5% of tokens are dropped per step under normal training. The dropped tokens' gradient is zero, slightly slowing convergence.

3. **Communication in EP**: the all-to-all per MoE layer is the main overhead in distributed training. NVLink is essential; cross-node MoE training is much slower.

4. **Memory**: MoE models are large (47B for Mixtral 8x7B). Activation checkpointing is mandatory. EP splits the model across GPUs; FSDP can also shard it.

5. **Initialization**: experts should be initialized differently (otherwise they collapse to identical outputs). Common: random init with different seeds, or split a dense FFN's weights.

## Inference

For inference, MoE models need to load only the activated experts per token. The full model is loaded (all experts in memory), but the active computation uses only K of N_e experts. Memory: full model size. Compute: K / N_e × FFN cost per token.

Serving MoE models requires:
- Loading all experts into GPU memory (or CPU if too large).
- A router that runs per token.
- Per-expert forward passes.
- Combining outputs.

vLLM and SGLang support Mixtral and DeepSeek-V3 inference natively.

## Comparison to Dense Models

| Aspect | Dense 47B | MoE 47B (8×7B, top-2) |
|--------|-----------|----------------------|
| Parameters | 47B | 47B |
| FLOPs per token | 94 GFLOPS | ~28 GFLOPS (2 × 14B equivalent) |
| Memory (params) | 94 GB (bf16) | 94 GB |
| Training cost (vs dense) | 1× | ~0.3× for same quality |
| Inference compute (per token) | 94 GFLOPS | ~28 GFLOPS |
| Inference memory | 94 GB | 94 GB |
| Implementation complexity | Low | High |
| Routing overhead | None | Router + all-to-all (with EP) |

The key MoE trade: 3× less compute for the same quality, at the cost of more memory and more implementation complexity.

## Common Pitfalls

1. **Setting capacity factor too low.** < 1.0 means tokens are routinely dropped, slowing convergence. Use 1.25-1.5.

2. **Forgetting the shared expert.** For DeepSeek-style MoE, the shared expert is mandatory — without it, the routed experts must handle universal patterns and specialization is harder.

3. **Not using the auxiliary loss.** Without it, routing collapses. Start with α=0.01; tune if necessary.

4. **Assuming MoE inference is faster than dense.** Per-token compute is less, but per-token memory access is more (the model is bigger). Memory-bound inference may not be faster; compute-bound (long sequences) is.

5. **Forgetting that EP changes per-token compute.** The all-to-all communication is per-MoE-layer; with many layers, the communication accumulates. Profile to find the right EP/DP/PP/TP mix.

6. **Not testing routing behavior.** Run the trained model on a held-out set and inspect the router's per-expert probabilities. If one expert gets 90% of tokens, the MoE has collapsed to dense.

## References

- Shazeer et al., "[Outrageously Large Neural Networks: The Sparsely-Gated MoE Layer](https://arxiv.org/abs/1701.06538)" (ICLR 2017)
- Lepikhin et al., "[GShard: Scaling Giant Models with Conditional Computation](https://arxiv.org/abs/2006.16668)" (ICLR 2021)
- Fedus et al., "[Switch Transformers: Scaling to Trillion Parameter Models](https://arxiv.org/abs/2101.03961)" (2022)
- Duport et al., "[Mixtral of Experts](https://arxiv.org/abs/2401.04088)" (2023)
- DeepSeek-AI, "[DeepSeek-V3 Technical Report](https://arxiv.org/abs/2401.02966)" (2024)
- Zhou et al., "[Mixture-of-Experts with Expert Choice Routing](https://arxiv.org/abs/2202.09368)" (2022)
- Lewis et al., "[Pre-Trained Summarization with Hash Routing](https://arxiv.org/abs/2104.02786)" (2021)
