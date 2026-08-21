# Data Parallelism

Data parallelism (DP) is the simplest model-parallel training scheme: the model is replicated on every worker, each worker processes a different micro-batch, and gradients are averaged across workers before the optimizer step. DP scales linearly with the number of workers up to the point where the all-reduce becomes a bottleneck. This page covers the protocol, the overlap of compute and communication, the gradient bucketing, and the modern variants (ZeRO Stage 1/2/3, FSDP) that extend DP to models too large for a single GPU.

## The Basic Protocol

```text
Each worker W_i holds:
  - A replica of the model (parameters W)
  - A micro-batch of data X_i
  - Optimizer state (Adam: m_i, v_i for each parameter)

For each training step:
  1. Forward pass: compute loss L_i = loss(W, X_i)
  2. Backward pass: compute gradients G_i = ∇L_i
  3. All-reduce gradients: G_avg = (1/N) sum_i G_i   ← the bottleneck
  4. Optimizer step: W = W - lr * Adam(G_avg, m, v)
```

After the all-reduce, every worker has the same averaged gradient and applies the same optimizer step. The model weights stay in sync across workers.

The all-reduce is the communication cost: every parameter's gradient must be sent to every other worker. For a 7B model in bf16 (14 GB of gradients), 8 workers on NVLink (900 GB/s) take ~30 ms for the all-reduce (14 GB × 2 / 900 GB/s = 31 ms, since all-reduce is 2× bandwidth per worker).

## Gradient Bucketing

Naive DP all-reduces each parameter's gradient as soon as it's computed (in the backward pass). This means many small all-reduce calls, each with ~30 µs of fixed overhead.

PyTorch DDP's optimization: bucket gradients into larger chunks before all-reducing. The bucket size is 25 MB by default, so 14 GB of gradients = 560 buckets. The all-reduce overhead drops from 1000 × 30 µs = 30 ms (per-parameter) to 560 × 30 µs = 17 ms.

```python
# DDP bucketing (default in PyTorch)
model = DDP(model, device_ids=[local_rank], 
            bucket_cap_mb=25)  # default
```

## Gradient-Compute Overlap

DDP overlaps the all-reduce of one layer's gradient with the backward computation of the next layer. The backward pass computes gradients in reverse order (last layer first):

```text
Layer N:    backward computes G_N
Layer N-1:  backward computes G_{N-1}  ← simultaneously, all-reduce of G_N starts
Layer N-2:  backward computes G_{N-2}  ← simultaneously, all-reduce of G_{N-1} starts
...
Layer 1:    backward computes G_1       ← simultaneously, all-reduce of G_2 starts
                                    (after backward finishes, wait for all-reduce of G_1)
```

The overlap hides most of the all-reduce latency behind compute. For a model where compute and all-reduce are balanced, ~80% of the all-reduce is hidden.

## The Memory Problem

Standard DP holds:
- Model parameters: P
- Gradients: P
- Optimizer state (Adam): 4P (fp32 m and v, plus fp32 master weights)
- Activations (with checkpointing): ~P/10
- Total per worker: ~6P

For a 70B model in bf16:
- P = 140 GB
- Per worker: 6P = 840 GB

This doesn't fit on any GPU. Standard DP doesn't work for 70B+ models. ZeRO (see below) extends DP to shard the state.

## ZeRO Stages

ZeRO (Zero Redundancy Optimizer, Rajbhandari et al., 2020) shards the DP state across workers, reducing the per-worker memory:

### ZeRO Stage 1: Shard optimizer state

Instead of each worker holding the full Adam state (4P), shard it so each worker holds 4P/N. The optimizer step is computed on the shard, then an all-gather distributes the updated parameters.

Per-worker memory: P (params) + P (grads) + 4P/N (Adam shard) = 2P + 4P/N.

For 70B, N=8: 2 × 140 + 4 × 140 / 8 = 350 GB. Still too much for a single GPU.

### ZeRO Stage 2: Shard gradients + optimizer state

Each worker holds only its shard of gradients (P/N) and optimizer state (4P/N). The all-reduce is replaced with a reduce-scatter (which gives each worker only its gradient shard).

Per-worker memory: P (params) + P/N (grad shard) + 4P/N (Adam shard) = P + 5P/N.

For 70B, N=8: 140 + 5 × 140 / 8 = 230 GB. Still too much.

### ZeRO Stage 3: Shard everything (params + grads + optimizer)

Each worker holds only its shard of all three. Parameters are gathered on-demand per layer (all-gather before the forward, all-gather before the backward).

Per-worker memory: 5P/N (all three shards).

For 70B, N=8: 5 × 140 / 8 = 87.5 GB. Fits on an 80 GB H100 with activation memory overhead.

The trade-off: ZeRO Stage 3 adds 2× all-gather per layer (forward + backward), increasing communication by ~3× vs. standard DP. The benefit: 70B+ models can be trained on commodity hardware.

## FSDP: PyTorch's Implementation

FSDP (Fully Sharded Data Parallel) is PyTorch's native ZeRO Stage 3 implementation, introduced in PyTorch 1.12 (2022). The API:

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP

model = MyModel()
model = FSDP(model, 
             shard_init_state=True,
             use_orig_params=True,
             cpu_offload=cpu_offload_config)  # optional: offload params to CPU
```

FSDP wraps the model and handles:
- Sharding the parameters across workers at init.
- All-gathering the parameters per layer in the forward.
- Reduce-scattering the gradients per layer in the backward.
- Optional CPU offloading of params or optimizer state.

For 70B+ training, FSDP is the most common approach in production. It's simpler than Megatron-LM (no model code changes) and works with any PyTorch model.

## FSDP vs. DDP: When to Use Each

| Aspect | DDP | FSDP |
|--------|-----|------|
| Memory per worker | ~6P | ~P/N |
| Communication | All-reduce of all gradients | All-gather + reduce-scatter per layer |
| Communication volume | 2P | ~4P (slightly more) |
| Implementation | No code changes | No code changes (wrap with FSDP) |
| Best for | Models that fit on a single GPU | Models too large for a single GPU |

For models ≤ 7B, DDP is the standard. For 13B-70B, FSDP or a hybrid (DP across nodes + TP within a node). For > 70B, FSDP or Megatron-style TP+PP+DP.

## Asynchronous DP

A variant where workers do not synchronize after every step. Each worker continues training on its own gradient without waiting for the all-reduce. The model weights drift apart, but the worker periodically pulls the average from a parameter server.

Asynchronous DP was popularized by TensorFlow's `AsynchronousParameterServer` in 2016. It's faster (no waiting for slow workers) but produces lower-quality models (the staleness of gradients causes the optimizer to take noisy steps).

For most production training (which uses synchronous SGD), asynchronous DP is rare. The only exception is huge clusters where the slowest worker slows the whole cluster — asynchronous DP tolerates stragglers.

## Production DP Implementations

- **PyTorch DDP**: the standard, built-in.
- **PyTorch FSDP**: built-in since 1.12.
- **Horovod**: framework-agnostic, supports TensorFlow/PyTorch/MXNet.
- **DeepSpeed**: Microsoft's framework, includes ZeRO and many other optimizations.
- **Megatron-LM**: NVIDIA's framework, integrates DP with TP and PP.

## Common Pitfalls

1. **Setting too-small micro-batch size.** With DP=N and per-GPU micro-batch=B, the global batch is N×B. If B is too small, the global batch is too small for stable training. Use gradient accumulation to maintain a large global batch even with small B.

2. **Forgetting `find_unused_parameters`.** If your model has parameters that don't get gradients every step (e.g., conditional execution), DDP's gradient sync fails. Set `find_unused_parameters=True` (at a 2× cost).

3. **Not using `gradient_as_bucket_view=True`.** Without this, DDP copies gradients to the bucket, doubling memory. Set this flag to make the bucket reuse the gradient's memory.

4. **Mixing DP and FSDP incorrectly.** FSDP itself can be combined with DP (each FSDP group has DP replicas). The outer DP and inner FSDP must use different process groups; naive wrapping produces incorrect gradients.

5. **Forgetting that FSDP reshards after every layer.** FSDP gathers params per layer, frees them after the layer. If your model's forward computes a layer's output multiple times (e.g., for residual connections), FSDP re-gathers each time, slowing training.

6. **Not monitoring the all-reduce time.** A healthy training run has <30% of step time in all-reduce. If >50%, the cluster is communication-bound: increase batch size, use ZeRO Stage 2 (lower comm) or upgrade to NVLink.

## References

- Rajbhandari et al., "[ZeRO: Memory Optimizations Toward Trillion Parameter Training](https://arxiv.org/abs/1910.02054)" (2020)
- [PyTorch Distributed Data Parallel (DDP) documentation](https://pytorch.org/docs/stable/generated/torch.nn.parallel.DistributedDataParallel.html)
- [PyTorch FSDP documentation](https://pytorch.org/docs/stable/fsdp.html)
- [DeepSpeed: ZeRO documentation](https://www.deepspeed.ai/tutorials/zero/)
- [Horovod documentation](https://horovod.readthedocs.io/)
- Goyal et al., "[Accurate, Large Minibatch SGD: Training ImageNet in 1 Hour](https://arxiv.org/abs/1706.02677)" (2017)
