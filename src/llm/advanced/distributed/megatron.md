# Megatron-LM: Tensor Parallelism

Megatron-LM is a tensor parallelism scheme for transformer training, developed by NVIDIA (Shoeybi et al., 2019). It partitions the matrix multiplications inside a single transformer layer across multiple GPUs, so that a single forward pass uses all GPUs in parallel — as opposed to data parallelism where each GPU computes a separate forward pass. This page covers the column-parallel and row-parallel partitioning, the communication pattern, the integration with data parallelism, and the production performance characteristics.

## Why Tensor Parallelism

Data parallelism (DP) replicates the model on every GPU; each GPU computes a separate forward pass on a different batch, and gradients are all-reduced. DP scales well until the GPU memory can't hold the model + activations + optimizer state. For a 70B model in bf16, the model alone is 140 GB; the optimizer state (Adam, fp32) is 280 GB; gradients are another 140 GB. Total: 560 GB per GPU. An A100 (80 GB) or H100 (80 GB) cannot fit a 70B model.

Tensor parallelism (TP) solves this by splitting the model across GPUs. With TP=8, each GPU holds 1/8 of the model — 70 GB for a 70B model, fitting in H100's 80 GB. The cost is communication: every matrix multiply in the transformer layer requires communication between the TP GPUs.

## The Transformer Layer Partitioning

A standard transformer layer:

```text
Input X (N × d)
   │
   ▼
Multi-Head Attention:
  Q = X W_Q    (N × d × d tensor)
  K = X W_K
  V = X W_V
  S = Q K^T    (N × N attention scores)
  P = softmax(S)
  O = P V     (N × d)
  Output = O W_O    (N × d × d)

   │
   ▼ (residual + layernorm)

MLP:
  H = X W_1   (N × d × 4d)   ← up-projection to 4d
  A = GELU(H)
  Y = A W_2   (N × 4d × d)   ← down-projection back to d
```

Megatron-LM's partitioning:

### Attention Block

- **Column-parallel for Q, K, V projections**: split `W_Q`, `W_K`, `W_V` along the output dimension. Each TP rank `i` holds `W_Q[i]` of shape `(d, d/N)`, computes `Q[i] = X W_Q[i]` of shape `(N, d/N)`. No communication needed for this — each rank computes its own slice of the attention heads.

- **Attention computation**: each rank computes the attention for its head subset, using its `Q[i], K[i], V[i]`. No communication.

- **Row-parallel for output projection**: `W_O` is split along the input dimension. Rank `i` has `W_O[i]` of shape `(d/N, d)`, computes `O[i] W_O[i] = Output_partial[i]` of shape `(N, d)`. The partial outputs are summed across ranks via an all-reduce.

### MLP Block

- **Column-parallel for up-projection**: `W_1` is split along output dimension. Each rank `i` has `W_1[i]` of shape `(d, 4d/N)`, computes `H[i] = X W_1[i]` of shape `(N, 4d/N)`. No communication.

- **GELU**: applied locally.

- **Row-parallel for down-projection**: `W_2` is split along input dimension. Each rank `i` has `W_2[i]` of shape `(4d/N, d)`, computes `Y[i] = A[i] W_2[i]` of shape `(N, d)`. The partial outputs are summed via all-reduce.

## The Communication Pattern

Per transformer layer: 2 all-reduces (one for the attention output, one for the MLP output). For a 96-layer transformer (GPT-3 scale), that's 192 all-reduces per forward pass, plus 192 in the backward.

The all-reduce size is `N × d` (the hidden dimension). For N=2048, d=12288 (GPT-3 scale): 50 MB per all-reduce. With NVLink at 900 GB/s: 50 µs per all-reduce. With 192 all-reduces per forward: 10 ms of communication overhead.

For comparison: the compute per layer (forward) is roughly `2 × N × d × 4d = 8 N d²` = 5 GFLOPS for GPT-3-scale, ~5 µs at H100's 1 PFLOPS effective. So compute is much faster than communication — Megatron-LM is communication-bound.

## Pipeline Parallelism: The Solution

To avoid the communication-bound limit, Megatron-LM is usually combined with Pipeline Parallelism (PP). PP splits the model's layers across GPUs: GPU 0 has layers 1-12, GPU 1 has layers 13-24, etc. Forward activations are sent from GPU 0 to GPU 1 after layer 12.

PP and TP together: with 4 TP ranks per layer and 4 PP stages, a 96-layer model fits in 16 GPUs. Each GPU holds 24 layers × (1/4 of the model per layer) = 6 layer-equivalents.

The combination:

```text
Pipeline stage 1 (GPUs 0,1,2,3): layers 1-24
   TP group: GPU0 || GPU1 || GPU2 || GPU3
Pipeline stage 2 (GPUs 4,5,6,7): layers 25-48
   TP group: GPU4 || GPU5 || GPU6 || GPU7
...
Pipeline stage 4 (GPUs 12,13,14,15): layers 73-96
```

Forward pass: stage 1 computes layers 1-24, sends activation to stage 2, etc. Within each stage, the 4 TP GPUs run in parallel, communicating via all-reduce.

## Megatron-LM's Micro-Batching

Pipeline parallelism introduces a bubble: when stage 1 is computing layer 1, stage 2 is idle. To minimize the bubble, Megatron-LM uses **micro-batching**: split the global batch into M micro-batches, and pipeline them through the stages.

```text
Time:  0    1    2    3    4    5    6    7    8    9
Stage 1: B1   B2   B3   B4   .    .    .    B1'  B2'  B3'  B4'   ← forward, then backward
Stage 2: .    B1   B2   B3   B4   .    .    .    B1'  B2'  B3'
Stage 3: .    .    B1   B2   B3   B4   .    .    .    B1'  B2'
Stage 4: .    .    .    B1   B2   B3   B4   .    .    .    B1'
                                              ↑
                                      Bubble when stage 1 starts backward
                                      but stage 4 hasn't finished forward
```

The bubble fraction is `(P-1) / M`, where P is the number of pipeline stages and M is the number of micro-batches. For P=4, M=4: bubble = 75%. For P=4, M=64: bubble = 4.7%. Large M is critical for pipeline efficiency.

## Megatron-LM Variants

- **Megatron-LM 1.0 (2019)**: original column/row parallel scheme.
- **Megatron-LM 2.0 (2021)**: adds interleaved pipeline scheduling (1F1B with bubbles further reduced).
- **Megatron-DeepSpeed (2021)**: combines with DeepSpeed's ZeRO optimizer for memory efficiency.
- **Megatron-LM 3.0 (2023)**: adds sequence parallelism (splitting along the sequence dimension), useful for very long contexts.

## Comparison to FSDP

PyTorch's Fully Sharded Data Parallel (FSDP) is an alternative to Megatron-LM for large model training. FSDP shards the model parameters, gradients, and optimizer state across DP ranks, gathering them on-demand per layer.

| Aspect | Megatron-LM (TP+PP) | FSDP |
|--------|---------------------|------|
| Memory savings | ~N×TP × ~P | ~N (DP rank count) |
| Communication per layer | 2 all-reduces (TP) + 1 send/recv (PP) | 2 all-gathers (param gather + reduce-scatter for grad) |
| Communication volume | Low (small all-reduces per layer) | High (full model gathered per layer) |
| Per-GPU memory | 70B model in 8 GPUs | 70B model in 8 GPUs (with ZeRO Stage 3) |
| Implementation complexity | High (model code changes) | Low (wraps any model) |
| Best for | Models too large for one GPU + need very low communication | Models that fit sharded across DP ranks |

Production training setups often combine FSDP (across nodes) and Megatron-LM (within a node), getting the best of both: NVLink-fast tensor parallelism within a node, and FSDP's parameter sharding across nodes.

## Common Pitfalls

1. **Setting TP size > NVLink group size.** Tensor parallelism's all-reduces need NVLink-grade bandwidth. Setting TP=8 on a 2-GPU-per-NVLink-group server means 4 all-reduces go over PCIe, which is 4× slower.

2. **Forgetting that TP breaks naive activation checkpointing.** Activation checkpointing recomputes the forward in the backward. With TP, the recomputation must respect the TP partitioning, or the all-reduce sequence is wrong.

3. **Using too-small micro-batches.** Pipeline bubble is `(P-1)/M`; small M wastes pipeline. Use M ≥ 4 × P.

4. **Trusting that TP works for any model.** TP requires the model to use only Megatron-supported modules. Custom layers may not have TP-aware implementations.

5. **Ignoring the embedding layer.** The embedding lookup (token → vector) is sharded by vocab in Megatron; if your vocab is too small, the per-GPU vocab is tiny and lookups become communication-bound.

6. **Forgetting that TP saves memory but not compute.** A 70B model with TP=8 uses 1/8 the GPU memory but each layer still does the full forward compute. The compute time is the same as on a single GPU; the wall-clock time per step is dominated by communication.

## References

- Shoeybi et al., "[Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism](https://arxiv.org/abs/1909.08053)" (2019)
- Narayanan et al., "[Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM](https://arxiv.org/abs/2104.04473)" (2021)
- Korthikanti et al., "[Reducing Activation Recomputation in Large Transformer Models](https://arxiv.org/abs/2205.05198)" (2022)
- [Megatron-LM GitHub repository](https://github.com/NVIDIA/Megatron-LM)
- [PyTorch Tensor Parallelism (TP) API](https://pytorch.org/docs/stable/distributed.tensor.parallel.html)
- [DeepSpeed-Megatron](https://github.com/microsoft/Megatron-DeepSpeed)
- [NVIDIA's H100 architecture paper](https://images.nvidia.com/cnvml-2/wp-content/uploads/2023/cnvml-2/h100-whitepaper.pdf) (2022)
