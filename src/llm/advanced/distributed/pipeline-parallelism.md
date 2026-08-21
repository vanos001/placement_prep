# Pipeline Parallelism

Pipeline parallelism (PP) is a model-parallel training scheme that splits a neural network's layers across multiple GPUs along the depth dimension. GPU 0 holds layers 1-N, GPU 1 holds layers N+1-2N, etc. Activations flow from GPU 0 to GPU 1 to GPU 2 during the forward pass; gradients flow back during the backward pass. PP complements data parallelism (which splits the batch) and tensor parallelism (which splits within a layer). This page covers the naive pipeline, the GPipe schedule, the 1F1B schedule, and the interleaved schedule used by Megatron-LM.

## The Naive Pipeline

Naive pipeline: split layers across GPUs, run the full batch through each GPU sequentially:

```text
Time:  0    1    2    3    4    5    6    7
GPU 0: B1 (forward through layers 1-N)
GPU 1: .    B1 (forward through layers N+1-2N)
GPU 2: .    .    B1 (...)
GPU 3: .    .    .    B1 (...)
                              ↑ forward done
GPU 3: .    .    .    .    B1 (backward through layers 3N+1-4N)
GPU 2: .    .    .    .    .    B1 (backward)
GPU 1: .    .    .    .    .    .    B1 (backward)
GPU 0: .    .    .    .    .    .    .    B1 (backward)
                              ↑ done
```

Utilization: at any time, only 1 of 4 GPUs is computing. The pipeline "bubble" (idle time) is `(P-1) / P` of the total — for P=4, 75% of GPU time is wasted.

## GPipe: Micro-Batching

GPipe (Huang et al., 2019) splits the batch into M micro-batches and pipelines them:

```text
Time:   0     1     2     3     4     5     6     7     8     9     10    11
GPU 0:  B1f   B2f   B3f   B4f   .     .     .     .     B1b   B2b   B3b   B4b
GPU 1:  .     B1f   B2f   B3f   B4f   .     .     .     .     B1b   B2b   B3b
GPU 2:  .     .     B1f   B2f   B3f   B4f   .     .     .     .     B1b   B2b
GPU 3:  .     .     .     B1f   B2f   B3f   B4f   .     .     .     .     B1b
                                                       ↑
                                          (forward done on GPU 3, all idle
                                          for 1 step before backward starts)
```

Bubble fraction: `(P-1) / M`. For P=4, M=4: 75% bubble. For P=4, M=64: 4.7% bubble. Large M amortizes the bubble.

GPipe's storage: each GPU must hold activations for M micro-batches (until backward). For M=64 and per-micro-batch activation of 100 MB, that's 6.4 GB per GPU — significant.

## 1F1B Schedule

The 1F1B (one forward, one backward) schedule reduces the storage requirement. Instead of running all forward passes before any backward, alternate:

```text
Time:   0     1     2     3     4     5     6     7     8     9     10
GPU 0:  B1f   B2f   B3f   B4f   B1b   B2f   B3b   B4f   B5b   B6b   ...
GPU 1:  .     B1f   B2f   B3f   B1b   B4f   B2b   B5f   B3b   B6b   ...
GPU 2:  .     .     B1f   B2f   B3f   B1b   B4f   B2b   B5f   B3b   ...
GPU 3:  .     .     .     B1f   B2f   B3f   B1b   B4f   B2b   B5f   ...
```

Each GPU holds at most P activations in flight (vs M for GPipe). The bubble is still `(P-1)/M`, but the storage is `O(P)` instead of `O(M)`.

1F1B is the default in Megatron-LM and PyTorch's pipeline parallelism (`torch.distributed.pipeline.sync`).

## Interleaved Schedule (Megatron-LM 2.0)

The interleaved schedule (also called "virtual pipeline") reduces the bubble further. Instead of assigning contiguous layer ranges to each GPU, assign interleaved chunks:

```text
Layers 1-24 (8 chunks of 3 layers each):
GPU 0: chunks 1, 5, 9, 13, 17, 21   (interleaved with other GPUs)
GPU 1: chunks 2, 6, 10, 14, 18, 22
GPU 2: chunks 3, 7, 11, 15, 19, 23
GPU 3: chunks 4, 8, 12, 16, 20, 24

Each GPU processes chunks in the order:
   chunk1 → chunk2 → ... → chunk8 (but only its subset)
```

This way, each GPU alternates between layers near the start and end of the model. The bubble is reduced by another factor of (chunks per GPU), so the formula becomes:

```text
Bubble = (P-1) / (M × chunks_per_gpu)
```

For P=4, M=4, chunks=4: bubble = 75% / 4 = 18.75%. For P=4, M=64, chunks=4: bubble = 1.2%.

The trade-off: more communication between layers (every chunk transition is a GPU-to-GPU send), so each step has more sends. The interleaved schedule is preferred when computation per chunk is much larger than send time (i.e., large chunks).

## Pipeline Parallelism with Data Parallelism

PP is typically combined with DP: each pipeline stage is replicated across multiple GPUs (data-parallel). With 4 PP stages × 2 DP ranks per stage, you have 8 GPUs total.

```text
PP Stage 1:  GPU 0 (DP rank 0), GPU 1 (DP rank 1)
PP Stage 2:  GPU 2 (DP rank 0), GPU 3 (DP rank 1)
PP Stage 3:  GPU 4 (DP rank 0), GPU 5 (DP rank 1)
PP Stage 4:  GPU 6 (DP rank 0), GPU 7 (DP rank 1)
```

Within a PP stage, the DP ranks gradient-sync via all-reduce (typically the same all-reduce as in pure DP). Across PP stages, gradients are passed stage-to-stage.

## Activation Recomputation

Activation recomputation (a.k.a. activation checkpointing) trades compute for memory: discard intermediate activations after the forward, recompute them in the backward. This is essential for PP because each GPU holds M micro-batches' activations.

For 1F1B with P stages, activation memory is ~P activations. For 70B with 24K context, one activation is ~1 GB. P=4 means 4 GB per GPU just for activations — fine. Without activation recomputation, the actual forward pass would store ~100 activations per micro-batch, requiring 100 GB per GPU — doesn't fit.

Recomputation scheme options:
- **Selective**: recompute only attention (the largest activation); keep MLP activations. ~80% memory savings with ~10% compute overhead.
- **Full**: recompute everything. ~90% memory savings with ~30% compute overhead.

Selective is the default in modern frameworks.

## Communication Cost

PP's per-step communication:
- Per micro-batch forward: P-1 activations sent (between stages).
- Per micro-batch backward: P-1 gradients sent (backwards).

For P=4, M=4: 12 sends per step. Each activation is ~MB to GB (depending on layer width and batch). With NVLink at 900 GB/s, sending a 100 MB activation takes 110 µs — fast. With PCIe (40 GB/s), 2.5 ms — slow.

PP is best suited for intra-node (NVLink) topologies. Cross-node PP requires InfiniBand and is much slower; cross-node, FSDP is typically preferred.

## Pipeline Parallelism Implementations

- **PyTorch Pipeline (RPC-based)**: `torch.distributed.pipeline.sync.Pipe`. Slower, simpler API.
- **PyTorch Pipeline Parallelism (Tensor-aware)**: `torch.distributed.pipeline.sync.Pipe` with `torch.distributed.pipeline.sync.PipeCommitter` for activation checkpointing.
- **Megatron-LM**: own implementation, integrated with TP and DP.
- **DeepSpeed**: own implementation, integrated with ZeRO.
- **Mesh-TensorFlow**: older framework, similar functionality.

For most production training, Megatron-LM or DeepSpeed are the choices.

## Common Pitfalls

1. **Setting the pipeline depth too large.** P > NVLink group size forces cross-node sends, which are much slower. Keep P ≤ GPUs per node.

2. **Using too-small micro-batches.** M < 4 × P gives a large bubble. Aim for M ≥ 8 × P.

3. **Forgetting to handle the embedding layer.** Embeddings are typically on the first GPU; the gradient must flow back to them. Make sure the embedding's parameters are updated.

4. **Mixing PP with naive DP without overlap.** The DP all-reduce should overlap with the next PP step's forward. Frameworks handle this automatically; custom code may not.

5. **Not profiling the bubble.** Production training should monitor GPU utilization; a 50% utilization with PP=4 and M=4 indicates a large bubble. Increase M.

6. **Forgetting the loss calculation timing.** The loss is computed on the last PP stage. The last stage must communicate the loss to all stages (for logging and learning rate scheduling). A naive implementation that prints loss on rank 0 (which is the first stage) won't see it.

## References

- Huang et al., "[GPipe: Efficient Training of Giant Neural Networks using Pipeline Parallelism](https://arxiv.org/abs/1811.06965)" (2019)
- Narayanan et al., "[PipeDream: Generalized Pipeline Parallelism for DNN Training](https://arxiv.org/abs/1806.03377)" (2019)
- Megatron-LM source: [nvidia/megatron-lm](https://github.com/NVIDIA/Megatron-LM)
- [PyTorch Pipeline Parallelism](https://pytorch.org/docs/stable/pipeline.html)
- [DeepSpeed Pipeline Parallelism](https://www.deepspeed.ai/tutorials/pipeline/)
- [Ben-nicolas Lui et al., "Memory-efficient Pipeline-Parallel DNN Training](https://arxiv.org/abs/2110.07399)" (2021)
- LWN: "[Pipeline Parallelism for Large Model Training](https://lwn.net/Articles/862415/)" (2021)
