# KV Cache Compression

KV cache compression is a class of techniques for reducing the memory footprint of the key-value cache during LLM inference. For a 70B model with 32K context and batch=64, the KV cache alone can exceed 100 GB, exceeding GPU memory. Compression extends the supported context length, batch size, or sequence count without upgrading hardware. This page covers the techniques (quantization, eviction, sparse attention, multi-query attention), the trade-offs, and the production implementations.

## The Memory Problem

KV cache size for a transformer with H layers, hidden dimension D, head count N, head dimension D_h = D/N, batch size B, sequence length L, in bytes:

```text
KV per token = 2 (K and V) × H × N × D_h × bytes_per_element
            = 2 × H × D × bytes_per_element  (since N × D_h = D)

For Llama-2 70B (H=80, D=8192, bf16):
  KV per token = 2 × 80 × 8192 × 2 = 2.6 MB

For seq_len=4096, batch=1: 10 GB
For seq_len=4096, batch=64: 640 GB (doesn't fit on a single 80 GB GPU)
```

For longer sequences (32K, 128K) or larger batches, the KV cache is the dominant memory cost, exceeding the model's parameter size.

## Technique 1: Quantization

The simplest compression: store the KV cache in lower precision.

```text
bf16 (default): 2 bytes per element
int8: 1 byte per element (50% reduction)
int4: 0.5 bytes per element (75% reduction)
fp8 (Hopper): 1 byte per element
```

Quantization is lossy: int8 typically reduces quality by ~1% on most benchmarks; int4 by ~3-5%.

Production:
- **vLLM**: supports int8 KV cache via `--quantization fp8` (Hopper) or `--quantization awq` (post-training quantization).
- **TensorRT-LLM**: defaults to FP8 KV cache on Hopper.

## Technique 2: Grouped-Query Attention (GQA)

Standard multi-head attention has separate K and V per head. GQA shares K and V across groups of heads:

```text
Standard MHA: N heads, each with own K, V → total K is N × D_h, V is N × D_h.
MQA: 1 head's K, V shared by all N heads → total K is 1 × D_h, V is 1 × D_h.
GQA: g groups, each group shares K, V → total K is g × D_h, V is g × D_h.
```

For N=32, g=4 (Llama-2 70B uses GQA with 8 KV heads):
- Standard: 32 × D_h per layer.
- MQA: 1 × D_h per layer (32× reduction).
- GQA-8: 8 × D_h per layer (4× reduction).

GQA's quality is between standard and MQA. The KV cache reduction is linear in the number of groups.

```python
class GQA(nn.Module):
    def __init__(self, hidden_dim, num_heads, num_kv_heads):
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = hidden_dim // num_heads
        self.q_proj = nn.Linear(hidden_dim, num_heads * self.head_dim)
        self.k_proj = nn.Linear(hidden_dim, num_kv_heads * self.head_dim)
        self.v_proj = nn.Linear(hidden_dim, num_kv_heads * self.head_dim)
    
    def forward(self, x):
        q = self.q_proj(x).view(B, L, self.num_heads, self.head_dim)
        k = self.k_proj(x).view(B, L, self.num_kv_heads, self.head_dim)
        v = self.v_proj(x).view(B, L, self.num_kv_heads, self.head_dim)
        
        # Repeat k, v for each head in the group
        repeats = self.num_heads // self.num_kv_heads
        k = k.repeat_interleave(repeats, dim=2)
        v = v.repeat_interleave(repeats, dim=2)
        
        return F.scaled_dot_product_attention(q, k, v)
```

## Technique 3: Sliding Window Attention

Limit each token's attention to a window of W recent tokens:

```text
For position i:
  Attend to positions max(0, i-W) to i.
  Earlier positions are not in the attention window.
```

The KV cache only needs to hold the last W tokens. For W=4096 and L=32768, the KV cache is 8× smaller than full attention.

Mistral-7B uses sliding window attention with W=4096. The model handles long contexts by having each layer attend to a local window, and the deep stack of layers aggregates information across windows.

The trade-off: information from far-back tokens must be propagated through layers, not directly attended to. For tasks requiring long-distance attention (e.g., document Q&A), this may not suffice.

## Technique 4: Sparse Attention (Longformer, BigBird)

Sparse attention uses a fixed pattern of which tokens attend to which:

```text
Longformer: each token attends to:
  - The W tokens around it (sliding window).
  - A few "global tokens" (e.g., the [CLS] token) that attend to everything.

BigBird: same, plus a few random connections (for theoretical expressivity).
```

The complexity is O(N × W + G × N) where W is the window size and G is the number of global tokens. For W=512 and N=32K, this is much smaller than the O(N²) of full attention.

Production: Longformer is used in some document classification tasks. BigBird is in Google's T5 models for long context.

## Technique 5: Eviction (StreamingLLM, H2O)

Eviction policies discard old KV entries that are unlikely to be re-attended:

```text
StreamingLLM (Xiao et al., 2023): keep only the last W tokens + first K tokens (attention sinks).
  - The first K tokens are kept because attention naturally focuses on them (the "sink" phenomenon).
  - The last W tokens are kept for local context.
  - Middle tokens are evicted.

H2O (Heavy-Hitter Oracle, Zhang et al., 2023): keep the tokens with the highest attention scores historically.
  - The "heavy hitters" are the tokens that other tokens attend to most.
```

These methods enable streaming with O(W + K) memory, where W and K are constant (independent of sequence length). Quality degrades gracefully with longer sequences.

Production: StreamingLLM is implemented in vLLM (`--enable-streaming`). H2O is in some commercial LLM serving frameworks.

## Technique 6: Cross-Layer KV Sharing (YOCO, CLA)

YOCO (You Only Cache Once, Sun et al., 2024) shares the KV cache across layers:

```text
Standard: each layer has its own K, V (computed from the input).
YOCO: only the first layer computes K, V; all subsequent layers share.
```

This reduces KV cache size by H× (where H is the layer count). For Llama-2 70B with H=80, the KV cache is 80× smaller.

The trade-off: the model has fewer parameters (the per-layer K, V projections are shared), reducing quality. YOCO papers report ~1% quality loss.

## Production KV Cache Compression

| Technique | Memory reduction | Quality impact | Used in |
|-----------|------------------|----------------|---------|
| FP8 quantization | 2× | -1% | vLLM, TensorRT-LLM |
| INT4 quantization | 4× | -3-5% | TensorRT-LLM |
| GQA (8 groups) | 4× | -0.5% | Llama-2, Llama-3, Mistral |
| MQA | N× | -2% | Mistral-7B (some variants) |
| Sliding window | seq_len / W × | -3% for tasks needing long context | Mistral-7B |
| StreamingLLM | depends | -5% on long sequences | vLLM (experimental) |
| YOCO | H× | -1% | Research only |

For production LLM serving in 2024, the typical combination:
- GQA (built into the model).
- FP8 KV cache (in the serving engine).
- Sliding window for very long contexts (e.g., 128K).

This typically reduces KV cache size by 8-16× vs. naive MHA bf16 KV cache.

## Common Pitfalls

1. **Forgetting that GQA reduces parameters, not just KV cache.** A model with GQA has fewer total parameters than MHA, which may lower quality if the model size is fixed.

2. **Forgetting that sliding window attention changes the model architecture.** A model trained with full attention can't simply be loaded with sliding window; the architecture differs.

3. **Forgetting that eviction policies have quality cliffs.** StreamingLLM works well for context up to 4× training; beyond that, quality degrades sharply.

4. **Forgetting that quantization needs calibration.** INT8 KV cache requires running a calibration set to determine the scale factors; the model's behavior may shift.

5. **Forgetting that FP8 KV cache requires Hopper hardware.** A100 doesn't support FP8; the FP8 KV cache optimization only works on H100+.

6. **Forgetting that KV cache compression doesn't help if the model parameters don't fit.** For a 70B model in FP16 (140 GB), even an empty KV cache requires 2× 80 GB GPUs. The compression helps with the activations + KV cache, not the model itself.

## References

- Ainslie et al., "[GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245)" (EMNLP 2023)
- Shazeer, "[Fast Transformer Decoding with One Write-Head is Better Than Eight](https://arxiv.org/abs/1911.02150)" (2019) — MQA
- Xiao et al., "[Efficient Streaming Language Models with Attention Sinks](https://arxiv.org/abs/2309.17453)" (ICLR 2024) — StreamingLLM
- Zhang et al., "[H2O: Heavy-Hitter Oracle for Efficient Generative Inference of LLMs](https://arxiv.org/abs/2306.14048)" (NeurIPS 2023)
- Sun et al., "[YOCO: You Only Cache Once](https://arxiv.org/abs/2405.05254)" (NeurIPS 2024)
- Beltagy et al., "[Longformer: The Long-Document Transformer](https://arxiv.org/abs/2004.05150)" (2020)
- Zaheer et al., "[Big Bird: Transformers for Longer Sequences](https://arxiv.org/abs/2007.14062)" (NeurIPS 2020)
- [vLLM: Quantized KV cache](https://docs.vllm.ai/en/latest/quantization/)
