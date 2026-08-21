# Model Parallelism Overview

Model parallelism (MP) is a family of techniques for training neural networks too large to fit on a single GPU. Unlike data parallelism (which replicates the model on every GPU), model parallelism partitions the model across GPUs. This page covers the three main MP variants — tensor parallelism (TP), pipeline parallelism (PP), and expert parallelism (EP) — and the dimensions along which they differ, with a focus on how they compose in production training.

## The Three Dimensions

```text
                    Data Parallelism (DP)
                            │
                            ▼
                  Replicates the model on every GPU
                  (no model partitioning)

                    Model Parallelism (MP)
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
              TP           PP           EP
       (within a layer)  (across layers) (per-expert)
```

- **Tensor Parallelism (TP)**: splits a single layer's matrix multiply across GPUs. Each GPU computes a slice of the output; communication (all-reduce) happens per layer.
- **Pipeline Parallelism (PP)**: splits the model's layers across GPUs. Each GPU holds a subset of layers; activations flow between stages.
- **Expert Parallelism (EP)**: for MoE models, splits experts across GPUs. Each GPU holds different experts; tokens are routed to their assigned expert.

## Communication Patterns

| Scheme | Per-step communication | Latency | Bandwidth per worker |
|--------|------------------------|---------|----------------------:|
| DP | All-reduce of all gradients | Low (one call) | 2 × model_size |
| TP | All-reduce per layer (×2 for forward+backward) | High (many calls) | 2 × layer_size per layer |
| PP | Send/recv between stages (×2 for forward+backward) | Low (per stage) | layer_size per stage |
| EP | All-to-all per MoE layer | High (per MoE layer) | layer_size × K_per_token |

DP has the lowest latency (one all-reduce per step) but the highest bandwidth per worker (full model size, twice — for grad and for the all-reduce). TP has low bandwidth per call but many calls per step. PP is between.

## Memory Savings

| Scheme | Per-worker memory | Trained model size |
|--------|------------------:|---------------------:|
| DP (no sharding) | 6P | fits in single GPU |
| DP + ZeRO Stage 3 (FSDP) | 5P/N | N GPUs total |
| TP (within a node) | P/N | N GPUs (limited by single node) |
| PP (across nodes) | P × layers_per_stage / total_layers | N stages |
| TP + PP + DP | mixed | any size |

## Composability

The three MP variants can be combined:

```text
Cluster: 4 nodes × 8 GPUs/node = 32 GPUs

TP group: 8 GPUs within a node (NVLink-bound)
PP group: 4 stages across the nodes
DP group: 1 (no DP replicas with this configuration)

Or:
TP group: 4 GPUs within a node
PP group: 4 stages across nodes (cross-node)
DP group: 2 replicas (gradient sync across both TP+PP trees)

Or (for MoE):
TP group: 8 GPUs within a node (within experts)
EP group: 4 nodes across the cluster (1 expert per node)
DP group: 2 replicas
```

The exact combination depends on the cluster topology and the model's needs. Production training scripts typically allow specifying each dimension via command-line flags.

## A Production Example: GPT-3 175B Training

The original GPT-3 (175B) was trained on V100 clusters with the following setup (per the Megatron-LM 2.0 paper):

```text
Cluster: 1024 V100 GPUs in 128 nodes (8 GPUs/node)
TP group size: 8 (within a node, NVLink 300 GB/s)
PP group size: 16 (across nodes, IB 100 Gbps)
DP group size: 8 (gradient sync via all-reduce)
Micro-batches per PP step: 64
Total: 8 × 16 × 8 = 1024 GPUs
Batch size: 1024 × 4 (per-GPU microbatch) × 64 (micro-batches per PP step) / 16 (PP stages) = 16384 tokens
```

Each step's communication breakdown:
- TP all-reduce: ~1 ms per layer × 96 layers = ~100 ms
- PP send/recv: ~50 µs per stage × 16 stages × 2 (forward+backward) = ~1.6 ms (with overlap)
- DP all-reduce: ~50 ms (overlapped with backward)
- Total: ~150 ms communication per step

Compute per step: ~2 seconds (forward + backward for the full batch). Communication is ~7% of compute time — efficient.

## How to Choose

The right combination depends on:

1. **Model size** (parameters): determines if you need MP at all. <20B: DP only. 20B-70B: FSDP. >70B: TP+PP+DP.

2. **Sequence length** (tokens): long sequences mean large activations, requiring PP (which streams activations) or activation checkpointing (which recomputes).

3. **Cluster topology**: NVLink group size limits TP; cross-node bandwidth limits PP and DP.

4. **MoE architecture**: MoE models add EP, which is its own dimension. EP benefits from NVLink (fast all-to-all) and is best deployed within a node.

5. **Training framework support**: PyTorch FSDP for DP-only; Megatron-LM for TP+PP+DP; DeepSpeed for hybrid.

## Hybrid Schemes in Practice

### PyTorch + FSDP

PyTorch's FSDP supports nesting with TP. The outer FSDP shards across DP ranks; the inner TP wraps each transformer layer.

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.tensor.parallel import parallelize_module

# Wrap each transformer block with TP
for block in model.transformer.blocks:
    block = parallelize_module(block, tp_mesh, {
        "attention": ColwiseParallel(),
        "mlp": RowwiseParallel(),
    })

# Wrap the whole model with FSDP across DP ranks
model = FSDP(model, fsdp_mesh)
```

### Megatron-LM + DeepSpeed ZeRO

Megatron-LM provides TP+PP; DeepSpeed's ZeRO provides sharded optimizer state. Together they train models like OPT-175B on 96 GPUs.

### Megatron-DeepSpeed

The most common production framework for >100B models. Combines:
- Megatron-LM's TP and PP
- DeepSpeed's ZeRO Stage 1 for optimizer state sharding
- Optional DeepSpeed MoE for expert routing

## Common Pitfalls

1. **Setting TP > NVLink group size.** TP's all-reduce is fast on NVLink but slow on PCIe. Keep TP within a node.

2. **Setting PP > DP ranks.** PP across nodes with no DP wastes nodes. Use DP replicas to fill the cluster.

3. **Forgetting to overlap DP all-reduce with backward.** Without overlap, DP adds 30-50% to step time. PyTorch DDP auto-overlaps; custom DP code may not.

4. **Using ZeRO Stage 3 with PP.** Stage 3 already shards params across DP ranks; PP across the same ranks redundantly shards. Pick one.

5. **Forgetting that EP's all-to-all is on the critical path.** Unlike DP's all-reduce (which can overlap with backward), EP's all-to-all must happen between the router and the expert forward. It cannot be hidden behind compute.

6. **Trusting framework defaults for huge models.** Defaults are tuned for ~7B models. For 100B+, custom config (TP size, PP size, micro-batch count) is essential.

## Production Frameworks Summary

| Framework | DP | TP | PP | EP | Notes |
|-----------|----|----|----|----|------|
| PyTorch DDP | ✓ | — | — | — | Built-in |
| PyTorch FSDP | ✓ | ✓ | — | — | Built-in |
| Megatron-LM | ✓ | ✓ | ✓ | ✓ | NVIDIA, for transformer LLMs |
| DeepSpeed | ✓ | ✓ | ✓ | ✓ | Microsoft, integrates with HF Transformers |
| Colossal-AI | ✓ | ✓ | ✓ | ✓ | HPC-focused |
| Mesh-TensorFlow | ✓ | ✓ | ✓ | ✓ | Google, older |
| JAX/Flax | ✓ | ✓ | ✓ | — | Google, functional-style |

For LLM training in 2024-2025, the most common choices are PyTorch + FSDP for ≤ 70B and Megatron-DeepSpeed for > 70B.

## References

- Narayanan et al., "[Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM](https://arxiv.org/abs/2104.04473)" (2021)
- Rajbhandari et al., "[ZeRO: Memory Optimizations Toward Trillion Parameter Training](https://arxiv.org/abs/1910.02054)" (2020)
- [PyTorch: FSDP + TP integration](https://pytorch.org/docs/stable/fsdp.html)
- [Megatron-LM source](https://github.com/NVIDIA/Megatron-LM)
- [DeepSpeed documentation](https://www.deepspeed.ai/)
- [PyTorch DDP tutorial](https://pytorch.org/tutorials/intermediate/ddp_tutorial.html)
- [JAX pjit: SPMD model parallelism](https://jax.readthedocs.io/en/latest/jax-101/06-parallelism.html)
