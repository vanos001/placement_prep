# FSDP (Fully Sharded Data Parallel)

FSDP is PyTorch's native implementation of ZeRO Stage 3 (memory-efficient DP that shards parameters, gradients, and optimizer state across workers). It was introduced in PyTorch 1.12 (2022) and is the standard way to train 13B-70B models on multi-GPU setups without requiring Megatron-style model code changes. This page covers the sharding scheme, the per-layer all-gather and reduce-scatter, the CPU offload option, and the production tuning.

## The Sharding Scheme

Without FSDP, each DP worker holds:
- Model parameters: P (per layer × num_layers)
- Gradients: P
- Optimizer state (Adam): 4P (fp32 m and v + fp32 master weights)
- Total: 6P per worker

For a 70B model in bf16: 6P = 840 GB per worker — doesn't fit.

FSDP shards all three (params, grads, optimizer) across N workers. Per-worker memory:
- Params shard: P/N
- Gradients shard: P/N (reduce-scattered during backward)
- Optimizer state shard: 4P/N
- Total: 6P/N per worker

For 70B model, N=8: 6 × 140 / 8 = 105 GB. Doesn't fit on 80 GB.

With ZeRO Stage 3 (no fp32 master weights): ~2P/N + 2P/N = 4P/N = 70 GB. Fits on 80 GB H100.

## The Per-Layer Communication

FSDP wraps each layer (or each "FSDP unit", configurable). For each layer's forward:

```text
1. All-gather parameters: each worker gathers the full layer's params from all workers.
   The layer's params now exist on every worker (in transient memory).

2. Compute forward: each worker does the forward for its micro-batch.

3. Discard non-owned params: each worker keeps only its P/N shard, frees the rest.
```

For backward:
```text
1. All-gather parameters: same as forward, gather full params.

2. Compute backward: gradients are computed per layer.

3. Reduce-scatter gradients: each worker ends up with only its G/N shard.

4. Discard non-owned params.
```

The communication pattern is:
- Forward: 1 all-gather per layer
- Backward: 1 all-gather + 1 reduce-scatter per layer
- Total: 2 all-gathers + 1 reduce-scatter per layer per step

For a 70B model with 96 layers, that's 288 collective ops per step. With NVLink at 900 GB/s and ~30 µs fixed overhead per op, the all-gather/reduce-scatter overhead is ~9 ms — manageable.

## The FSDP Unit

FSDP groups layers into "FSDP units" — the granularity at which it shards and gathers. Choosing the right FSDP unit is critical:

- **Wrap every layer individually**: maximum memory savings (smaller all-gathers, lower transient memory), but more communication ops (more overhead).
- **Wrap the whole model as one unit**: minimum communication (one all-gather, one reduce-scatter per step), but maximum transient memory (the full model is gathered).
- **Wrap each transformer block**: middle ground. Each block's all-gather is ~1 GB for a 70B model; the block is the natural "layer" granularity.

```python
# Manually wrap transformer blocks
for i, block in enumerate(model.transformer.blocks):
    model.transformer.blocks[i] = FSDP(block, use_orig_params=True)
# Outer FSDP for the whole model
model = FSDP(model)
```

PyTorch 2.x's `auto_wrap_policies` can do this automatically based on a "transformer block" class name:

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp.wrap import transformer_auto_wrap_policy

auto_wrap_policy = transformer_auto_wrap_policy(
    transformer_layer_cls={TransformerBlock}
)

model = FSDP(model, auto_wrap_policy=auto_wrap_policy)
```

## CPU Offloading

FSDP can offload parameters and optimizer state to CPU RAM, freeing GPU memory:

```python
from torch.distributed.fsdp import CPUOffload

model = FSDP(model, cpu_offload=CPUOffload(offload_params=True))
```

The trade-off:
- Benefit: ~2× more GPU memory available (params + optimizer state live on CPU).
- Cost: CPU↔GPU transfers per layer per step. For a 70B model, that's ~140 GB of transfer per step, at PCIe Gen4 64 GB/s = 2 seconds — a 50-100% training slowdown.

CPU offload is useful for:
- Training > 70B models on 80 GB GPUs when GPU memory is insufficient.
- Fine-tuning with a few CPUs of RAM available.

It's rarely used for production training from scratch — the slowdown is too costly.

## Mixed Precision and FSDP

FSDP supports mixed precision (bf16 forward + fp32 master weights). The sharded parameters are stored in bf16 (smaller); the optimizer state is stored in fp32.

Per-worker memory: P (bf16 params) + 0.5P (fp32 master shard) + 4P (Adam state shard) = ~5.5P/N. For 70B, N=8: 5.5 × 140 / 8 = 96 GB. Doesn't fit on 80 GB.

Without fp32 master (pure bf16): P (bf16 params) + 2P (Adam state, bf16) = 3P/N. For 70B, N=8: 52 GB. Fits.

The choice of fp32 master depends on stability needs; pure bf16 is faster and uses less memory but can have higher gradient noise for sensitive training.

## Activation Checkpointing

FSDP integrates with activation checkpointing (recompute forward in backward to save activation memory):

```python
from torch.distributed.algorithms._checkpoint import checkpoint_wrapper

for i, block in enumerate(model.transformer.blocks):
    block = checkpoint_wrapper(block)
    model.transformer.blocks[i] = FSDP(block)
```

Combined: FSDP shards parameters across workers; activation checkpointing discards intermediate activations and recomputes in backward. Together, they bring a 70B model's per-GPU memory to ~30 GB.

## FSDP + TP

PyTorch 2.x supports combining FSDP with TP. The outer FSDP shards across DP ranks; the inner TP wraps each layer with `parallelize_module`. The two must use different process groups.

```python
from torch.distributed.device_mesh import DeviceMesh
from torch.distributed.tensor.parallel import parallelize_module

mesh = DeviceMesh("cuda", torch.arange(world_size).reshape(dp_size, tp_size))
tp_mesh = mesh["tp"]
dp_mesh = mesh["dp"]

# Inner: TP-parallelize each transformer block
for i, block in enumerate(model.transformer.blocks):
    block = parallelize_module(block, tp_mesh, ...)

# Outer: FSDP across the DP dimension
model = FSDP(model, dp_mesh)
```

This is the modern PyTorch equivalent of Megatron-LM's TP+DP combo.

## FSDP Checkpointing

FSDP saves checkpoints as a set of "shards" — one per DP rank, containing only that rank's shard of the parameters and optimizer state. This is space-efficient (each shard is P/N in size, total = P, not P × N as in naive DDP checkpoints).

```python
# Save
import torch.distributed.checkpoint as dcp
dcp.save_state_dict({"model": model.state_dict()}, checkpoint_id="step-1000")

# Load
dcp.load_state_dict({"model": model.state_dict()}, checkpoint_id="step-1000")
```

The dcp format is optimized for FSDP's sharded layout; loading is also sharded (each rank loads its own shard). This is much faster than the legacy `torch.save(model.state_dict())` which would materialize the full model on rank 0.

## Common Pitfalls

1. **Forgetting `use_orig_params=True`.** Without this flag, FSDP flattens parameters into a single "flat param" per FSDP unit, breaking `state_dict()` and named-parameter access. Always set `use_orig_params=True` (PyTorch 2.x).

2. **Setting the FSDP unit too small.** Each FSDP unit's all-gather has ~30 µs fixed overhead. With 1000 units per model, that's 30 ms of overhead — significant.

3. **Setting the FSDP unit too large.** Large units have large all-gathers; the all-gather uses transient memory equal to the full unit's size. For a 100 MB unit, that's 100 MB transient — fine. For a 5 GB unit, that's 5 GB transient — risky.

4. **Not using activation checkpointing.** Without it, activations of a 70B model with seq 4096 are ~80 GB. With it, ~10 GB.

5. **Using CPU offload for production training.** The PCIe bottleneck can 2-5× slowdown. Use it only for development or when GPU memory is genuinely insufficient.

6. **Forgetting to call `model.reset_init_model()` after loading a sharded checkpoint.** Each rank loads its shard, but the model's flat parameter view must be re-initialized to point to the new shard. The dcp library handles this; custom loading code may not.

7. **Trusting that FSDP works with all PyTorch ops.** FSDP requires that the model is "FSDP-friendly" — uses standard nn.Module patterns, no in-place ops that modify parameters, etc. Custom ops may not work.

## References

- [PyTorch FSDP documentation](https://pytorch.org/docs/stable/fsdp.html)
- [PyTorch FSDP getting started tutorial](https://pytorch.org/tutorials/intermediate/FSDP_tutorial.html)
- Zhao et al., "[PyTorch FSDP: Experiences on Scaling Fully Sharded Data Parallel](https://arxiv.org/abs/2304.11277)" (VLDB 2024)
- [FSDP + TP integration (PyTorch 2.x)](https://pytorch.org/tutorials/intermediate/tp_tutorial.html)
- [DeepSpeed vs FSDP comparison](https://www.deepspeed.ai/tutorials/fsdp-vs-deepspeed/)
- [Hugging Face Transformers + FSDP](https://huggingface.co/docs/transformers/main/en/fsdp)
- Rajbhandari et al., "[ZeRO Stage 3 paper](https://arxiv.org/abs/1910.02054)" (2020)
