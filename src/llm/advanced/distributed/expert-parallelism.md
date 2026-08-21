# Expert Parallelism (MoE)

Expert parallelism (EP) is a model-parallel scheme that places the "experts" of a Mixture-of-Experts (MoE) layer on different GPUs. Each GPU holds a subset of experts; the routing tokens to their assigned expert requires inter-GPU communication. EP was the dominant parallelism strategy for large MoE models like GShard (2020), GLaM (2021), Switch Transformer (2022), Mixtral 8x7B (2023), and DeepSeek-V3 (2024). This page covers the MoE structure, the all-to-all communication pattern, the load balancing problem, and the integration with other parallelism schemes (TP, PP, DP).

## MoE Layer Structure

A standard transformer FFN layer:

```text
X → Linear(d → 4d) → GELU → Linear(4d → d) → Y
```

An MoE FFN layer:

```text
X → Router (Linear d → N_experts) → per-token expert IDs
For each token, the top-K experts (default K=1 or 2) are activated.
The token is sent to the corresponding expert's GPU (if EP).
Each expert applies: Linear(d → 4d) → GELU → Linear(4d → d).
The output is sent back to the token's original GPU.
Y = sum over selected experts of expert_output[token] * routing_weight[token]
```

For Mixtral 8x7B: N_experts=8, top-K=2, d=4096. Each expert is a separate 14B-parameter FFN. The total MoE parameters: 8 × 14B = 112B (8 experts). With top-K=2, the per-token compute is 2 × 14B = 28B parameters worth of FLOPs — roughly equivalent to a 14B dense model.

## The All-to-All Communication

EP's defining characteristic is the all-to-all communication per MoE layer. After routing:

```text
GPU 0 has tokens: T1, T2, T3, T4 (some routed to expert 0, some to expert 1, etc.)
After routing, GPU 0 needs to send:
  T1, T3 → GPU 0 (their expert 0 is on GPU 0)
  T2 → GPU 1 (its expert 1 is on GPU 1)
  T4 → GPU 2 (its expert 3 is on GPU 2)
```

This is an all-to-all: each GPU sends a different subset of tokens to each other GPU. The total data sent across all GPUs is N × d × tokens_per_token (where N is the average number of destinations).

The all-to-all is the bottleneck of EP. For Mixtral 8x7B with N_experts=8 GPUs (1 expert per GPU), the all-to-all is 1 × d × tokens = 4 KB per token. For a batch of 4096 tokens × 8 GPUs, total data is 32 MB per direction. With NVLink at 900 GB/s, that's 35 µs per direction — fast.

For 64K tokens (long context), the all-to-all is 512 MB per direction. Still manageable on NVLink (550 µs), but on InfiniBand (100 Gbps) it's 40 ms — a 100× slowdown. EP is best deployed on NVLink-connected topologies.

## Load Balancing: The Auxiliary Loss

A naive MoE router can collapse: route all tokens to one expert (the "winning" expert), leaving others idle. The model's training dynamics suffer.

The fix is an auxiliary loss:

```text
L_aux = α × sum_i (f_i × P_i)

where:
  f_i = fraction of tokens routed to expert i (probability after softmax)
  P_i = mean over tokens of router probability for expert i (before softmax)
  α = balancing weight (typically 0.01)
```

The `f_i × P_i` product is maximized when both are large (a popular expert) or both are small (an unpopular expert). The product is zero when expert i is chosen by no tokens. To minimize L_aux, the router learns to balance the load.

The auxiliary loss is added to the main task loss and backpropagated. It does not affect inference — only training.

## Top-K Routing and Capacity Factor

For each token, the router picks top-K experts (K=1 or 2). The token is sent to each selected expert's GPU. The expert's "capacity" (max tokens per forward) is:

```text
capacity = (tokens_per_batch / N_experts) × capacity_factor
```

`capacity_factor` is typically 1.0 to 1.5. Tokens that would push an expert over capacity are dropped (and their routing weight is zeroed out). Capacity drops lead to lost information; the auxiliary loss is set up to encourage even distribution so capacity is rarely hit.

## Expert Parallelism vs. Tensor Parallelism for MoE

MoE layers can be parallelized two ways:

- **Expert Parallelism (EP)**: each GPU holds a different expert. All-to-all communication per layer.
- **Tensor Parallelism (TP)**: each GPU holds a slice of every expert. All-reduce per layer (same as dense transformer).

EP scales better with the number of experts (more experts = more GPUs without communication increase per GPU). TP scales better with the per-expert size (larger experts fit on more GPUs without EP's all-to-all).

Modern MoE training uses EP+TP: EP across experts, TP within each expert. With 8 experts × 4 TP per expert, you need 32 GPUs.

## Combined with PP and DP

A typical 70B+ MoE training setup combines EP, TP, PP, and DP:

```text
8 GPUs per node (TP group within the node, NVLink-bound)
N nodes × M GPU nodes (EP group across nodes)
K pipeline stages (PP group, often across the cluster)
D data-parallel replicas (DP group, gradient sync via all-reduce)
```

For Mixtral 8x7B (47B parameters total):
- EP=8 (1 expert per GPU): each GPU holds 14B expert params.
- TP=2 within each expert: 7B per GPU.
- DP=8: 16 total GPUs, batch=128, micro-batch=8 per DP rank.
- PP=4: 64 GPUs total.

This is roughly the configuration Meta used for Mixtral training.

## Common Pitfalls

1. **Setting capacity factor too low.** Capacity factor <1.0 means tokens are routinely dropped. Use 1.25-1.5 for stable training.

2. **Forgetting to remove the auxiliary loss for inference.** The auxiliary loss should be set to 0 for inference (it's only for training). Some frameworks don't do this automatically.

3. **Using top-K > 2 for very large N_experts.** Mixtral's top-2 of 8 experts uses 25% of parameters per token; top-4 of 8 uses 50%. For larger N_experts (e.g., 64), top-K=4 is fine; for small N_experts (e.g., 8), top-K=2 is the sweet spot.

4. **Naive EP without NVLink.** Cross-node all-to-all is much slower than within-node. Make EP fit within a node (or use a hybrid scheme where experts within a node use TP, between nodes use EP).

5. **Ignoring token routing skew.** Some tokens are routed to the same expert every step (e.g., punctuation tokens route to one specific expert). This causes load imbalance even with the auxiliary loss. Solutions: token shuffling before routing, or shared experts (DeepSeek's approach).

6. **Forgetting that EP changes the FLOPs per token.** A 47B-MoE model with top-2 of 8 has ~14B effective parameters per token, not 47B. FLOPs estimates must reflect this.

## Comparison to Dense Models

| Aspect | Dense 47B | MoE 47B (8×7B, top-2) |
|--------|-----------|------------------------|
| Parameters | 47B | 47B (sum of all experts) |
| FLOPs per token | ~94 GFLOPS | ~28 GFLOPS (1.5×14B params) |
| Memory (params) | 94 GB | 94 GB |
| Training throughput | 1× (baseline) | ~3× (less compute per token) |
| Inference throughput | 1× (baseline) | ~3× (less compute per token) |
| Routing overhead | None | All-to-all per MoE layer |
| Implementation complexity | Simple | High |

MoE trades implementation complexity for FLOPs. The same memory budget supports a model with 3× more parameters, improving quality at the cost of more code and more communication.

## Production MoE Models

- **GShard (Google, 2020)**: 600B MoE, the original.
- **Switch Transformer (Google, 2022)**: top-1 routing, even more parameters.
- **GLaM (Google, 2021)**: 1T MoE.
- **Mixtral 8x7B (Mistral, 2023)**: open-weights, 47B.
- **Mixtral 8x22B (Mistral, 2024)**: 141B.
- **DeepSeek-V3 (2024)**: 671B, top-8 of 256, with shared experts for non-routed computation.

## References

- Lepikhin et al., "[GShard: Scaling Giant Models with Conditional Computation](https://arxiv.org/abs/2006.16668)" (ICLR 2021)
- Fedus et al., "[Switch Transformers: Scaling to Trillion Parameter Models](https://arxiv.org/abs/2101.03961)" (2022)
- Duport et al., "[Mixtral of Experts](https://arxiv.org/abs/2401.04088)" (Mistral AI, 2023)
- DeepSeek-AI, "[DeepSeek-V3 Technical Report](https://arxiv.org/abs/2401.02966)" (2024)
- Shazeer et al., "[Outrageously Large Neural Networks: The Sparsely-Gated MoE Layer](https://arxiv.org/abs/1701.06538)" (ICLR 2017)
- [DeepSpeed-MoE](https://github.com/microsoft/Megatron-DeepSpeed)
