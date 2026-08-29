# Flash Attention

Flash Attention is an algorithm for computing attention in transformers that reduces the memory bandwidth bottleneck of the standard attention formula. Introduced by Tri Dao, Daniel Y. Fu, Stefano Ermon, Atri Rudra, and Christopher Ré in 2022 (NeurIPS 2022), it produces mathematically identical results to standard attention while reducing the GPU memory needed from O(N²) to O(N) for sequence length N, and avoiding the "memory wall" that limits standard attention to ~2K tokens on a single GPU. Flash Attention 2 (2023) further improves the GPU utilization, and Flash Attention 3 (2024) targets Hopper's TMA hardware.

## The Problem with Standard Attention

Standard scaled dot-product attention for a sequence of length N and head dimension d:

```text
Q, K, V ∈ R^{N × d}
S = Q K^T            ← N × N attention score matrix
P = softmax(S, dim=-1)   ← N × N attention probabilities
O = P V              ← N × d output
```

The bottleneck is the N × N intermediate `S` and `P` matrices. For N=4096 and d=128, this is 16M floats (64 MB) per attention head, per layer, per token-batch. The matrix multiplications themselves are fast on tensor cores (H100: 990 TFLOPS bf16), but writing `S` and `P` to HBM and reading them back dominates:

```text
Compute: Q K^T    2 N² d FLOPs       (16 GFLOPS for N=4096, d=128)
Memory:  S ← HBM  N² × 4 bytes      (64 MB read, ~25 µs at 3 TB/s)
Compute: softmax  ~5 N² FLOPs        (slight)
Memory:  P → HBM  N² × 4 bytes      (64 MB write)
Memory:  P ← HBM  N² × 4 bytes      (64 MB read)
Compute: P V      2 N² d FLOPs        (16 GFLOPS)
Memory:  O ← HBM  N × d × 4 bytes   (small)
```

For N=4096, d=128: compute is ~32 GFLOPS = 32 µs on H100 (at 1 TFLOPS effective); memory is 192 MB × 1/(3 TB/s) = 64 µs. Memory is 2× the compute — attention is **memory-bound**.

For N=16K (long context): memory is 3 GB per attention head, blowing past HBM capacity and forcing the model into activation checkpointing (recomputing attention in the backward pass) which is even slower.

## The Tiling Insight

Flash Attention's key insight: we never need to materialize the full `S` and `P` matrices in HBM. They can be computed in tiles that fit in SRAM, with the softmax computed incrementally:

```text
For each row i of Q (a query vector):
  Initialize: O_i = 0, l_i = 0, m_i = -∞
  
  For each block K_j, V_j of K and V (size B × d):
    # Compute attention scores for this block (in SRAM)
    S_ij = Q_i × K_j^T                    ← B-vector
    
    # Update running max and sum (for numerically stable softmax)
    m_new = max(m_i, max(S_ij))
    P_ij = exp(S_ij - m_new)              ← B-vector
    l_new = exp(m_i - m_new) × l_i + sum(P_ij)
    
    # Update running output (in SRAM)
    O_i = (exp(m_i - m_new) × l_i / l_new) × O_i 
        + (1 / l_new) × P_ij × V_j
    
    # Save state for next block
    m_i = m_new
    l_i = l_new
  
  Output: O_i (the attention output for query i)
```

The full `S` matrix never exists in HBM; only the final `O` is written. The `l` and `m` running statistics (one float per query) are saved for the backward pass, where the recomputation of `S` and `P` is done with the same tiling.

## Memory and Speed Comparison

| N | Standard memory | Flash memory | Standard time (H100) | Flash time (H100) |
|---|----------------:|--------------:|---------------------:|-------------------:|
| 512 | 1 MB | 4 KB | 5 µs | 3 µs |
| 1024 | 4 MB | 8 KB | 15 µs | 8 µs |
| 2048 | 16 MB | 16 KB | 50 µs | 20 µs |
| 4096 | 64 MB | 32 KB | 180 µs | 50 µs |
| 8192 | 256 MB | 64 KB | 700 µs | 130 µs |
| 16384 | 1 GB | 128 KB | 3000 µs | 350 µs |

For N=16K, Flash is 8× faster and uses 8000× less HBM. The crossover where Flash's tiled recomputation in backward becomes faster than storing the full matrix is around N=512; below that, standard attention is fine.

## Flash Attention 2 (2023)

Flash Attention 2 reduced the GPU operation count and improved the parallelism:

1. **Reduced non-matmul FLOPs**: Flash 1 had ~3× the non-matmul FLOPs of standard attention (due to softmax rescaling). Flash 2 reorders the computation to halve the non-matmul work.

2. **Better parallelism**: Flash 1 parallelized across the batch dimension and head dimension. Flash 2 adds parallelism across the sequence dimension (for the K/V loop), scheduling 4× more work per SM.

3. **Better warp-level partitioning**: Flash 1 used thread blocks; Flash 2 uses warps (32 threads) as the work unit, reducing shared memory traffic.

Net speedup: 2× over Flash 1, putting Flash 2 within 70-80% of the H100's theoretical matmul peak for N > 2048.

## Flash Attention 3 (2024)

Flash Attention 3 targets Hopper (H100) hardware features:

1. **Asynchronous data movement via TMA (Tensor Memory Accelerator)**: TMA copies data between HBM and shared memory asynchronously with the SM's compute. Flash 3 issues the next tile's load while computing the current tile, hiding memory latency.

2. **FP8 support**: H100's FP8 tensor cores can do 2× the throughput of FP16. Flash 3 uses FP8 for the score matrix (Q K^T) and FP16 for the softmax and V multiplication, with a small accuracy loss for most workloads.

3. **Warp-specialized kernels**: one warp handles data movement, another handles compute. The producer-consumer pattern maximizes overlap.

Flash 3 achieves 1.5-2× the speed of Flash 2 on H100 for N > 4096 (numbers from the paper's headline benchmarks). Unlike FlashAttention-2, FA3 is not what PyTorch's `scaled_dot_product_attention` ships by default -- it is distributed as a separate Hopper-targeted module in the `flash-attn` project (`flash_attn_interface`), so adopting it means an explicit code change, not a version bump.

## Production Use

```python
import torch
import torch.nn.functional as F
from flash_attn import flash_attn_func

# Standard attention (slow for long sequences)
def standard_attention(Q, K, V):
    S = Q @ K.transpose(-1, -2) / math.sqrt(d)
    P = F.softmax(S, dim=-1)
    return P @ V

# Flash Attention (fast for any sequence length)
def flash_attention(Q, K, V):
    return flash_attn_func(Q, K, V, causal=True)
```

PyTorch 2.0+ has Flash Attention built into `F.scaled_dot_product_attention` (SDPA):

```python
out = F.scaled_dot_product_attention(Q, K, V, is_causal=True)
# PyTorch auto-selects Flash Attention 2 if available, with fallbacks
```

For H100 users, Flash 3 is available via `flash-attn` package 3.0+:

```python
from flash_attn import flash_attn_func as flash_v3
out = flash_v3(Q, K, V, causal=True)
```

## Common Pitfalls

1. **Expecting identical outputs across implementations.** Standard and Flash Attention are mathematically equivalent but numerically different (Flash uses online softmax, which has slightly different floating-point rounding). Floating-point tolerance: max abs diff is ~1e-5 in bf16.

2. **Using Flash with very small sequences.** For N < 512, the kernel launch overhead and tile underutilization make Flash slower than standard. PyTorch's SDPA dispatches to standard for small N.

3. **Forgetting that backward recomputation happens.** Flash stores only `l` and `m` statistics for the backward pass. The Q K^T and softmax are recomputed in backward — this is faster than storing the full matrix, but uses more compute than ideal.

4. **Using non-causal masks incorrectly.** Flash accepts a `causal=True` flag that masks the lower triangle of the attention matrix. Using a custom attention mask (e.g., sliding window) requires Flash 2.2+.

5. **Assuming Flash supports all attention variants.** Multi-query attention (MQA) and grouped-query attention (GQA) need Flash 2.2+; sparse attention patterns (BigBird, Longformer) are not supported by Flash — use the original sparse attention implementation for those.

6. **Forgetting to use `torch.compile`.** PyTorch 2.0+'s `torch.compile` can fuse Flash with the surrounding elementwise ops (residual, layernorm), giving additional 10-30% speedup.

## References

- Tri Dao et al., "[FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135)" (NeurIPS 2022)
- Tri Dao, "[FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning](https://arxiv.org/abs/2307.08691)" (2023)
- Jay Shah et al., "[FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-Precision](https://arxiv.org/abs/2407.08608)" (2024)
- [flash-attn GitHub repository](https://github.com/Dao-AILab/flash-attention)
- [PyTorch SDPA documentation](https://pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html)
- [Tri Dao: FlashAttention-2 paper (PDF)](https://tridao.me/publications/flash2/flash2.pdf)
- [Hugging Face: How to use Flash Attention with transformers](https://huggingface.co/docs/transformers/perf_infer_gpu_one#flashattention)
