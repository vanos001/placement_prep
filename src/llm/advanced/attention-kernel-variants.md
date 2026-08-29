# Attention Kernel Variants: MQA, GQA, and MLA

Modern transformer inference is dominated not by attention arithmetic but by moving the key-value (KV) cache between HBM and compute. A family of architecture changes - multi-query attention (MQA), grouped-query attention (GQA), and multi-head latent attention (MLA) - attacks that cost by shrinking which tensors must be cached per generated token, while leaving the attention function itself intact. This page works through the KV-cache arithmetic each variant buys, why decode is a bandwidth problem, and how serving kernels absorb each layout. The Q/K/V fundamentals behind these variants are in [Self-Attention](../../ml/transformers/self-attention.md); kernel-side tiling and online softmax in [Flash Attention](flash-attention.md); block-table management of the cache in [Paged Attention](paged-attention.md); quantizing the cached bytes in [KV Cache Compression](kv-cache-compression.md).

## The Design Space: One Axis, Four Points

Every variant keeps the query heads and shrinks what K and V look like:

```text
                Q heads   K heads   V heads    cached elements per token/layer
MHA  (origin)     n_h       n_h       n_h      2 * n_h * d_h
GQA  (Llama 3)     32         8         8      2 * g * d_h            (g groups, g = 8)
MQA  (PaLM)        n_h        1         1      2 * 1 * d_h            (g = 1)
MLA  (DeepSeek)    128        -         -      d_c + d_R              (low-rank latent + rope)
```

Per generated token, the whole-model cache in bytes - the number that decides batch capacity and decode bandwidth:

```text
MHA/GQA/MQA:  bytes/token = 2 x layers x kv_heads x head_dim x dtype_bytes
MLA:          bytes/token = layers x (kv_lora_rank + rope_dim) x dtype_bytes
```

## KV-Cache Arithmetic on Real Models

Configs below are read from the released model configs (linked in the References):

| Model | Variant | Layers | Q heads | KV heads | head_dim | KiB/token |
|-------|---------|-------:|--------:|---------:|---------:|----------:|
| Llama-2 7B | MHA | 32 | 32 | 32 | 128 | 512.0 |
| Llama-2 70B | GQA-8 | 80 | 64 | 8 | 128 | 320.0 |
| Llama-3 8B | GQA-8 | 32 | 32 | 8 | 128 | 128.0 |
| Mistral 7B | GQA-8 | 32 | 32 | 8 | 128 | 128.0 |
| DeepSeek-V3 | MLA | 61 | 128 | latent 512 + rope 64 | n/a | 68.6 |

Worked example (Llama-2 70B): 2 x 80 layers x 8 KV heads x 128 dim x 2 bytes = 327,680 bytes = 320 KiB per token. MHA at the same shape would cache 2,560 KiB per token; the 64-to-8 KV-head ratio is exactly the 8x saving. DeepSeek-V3 caches 61 x (512 + 64) x 2 = 68.6 KiB per token in bf16, or 34.3 KiB with an fp8 latent. Note Llama-3 8B and Llama-2 7B have identical layer counts and head_dim yet differ 4x in cache: only the KV-head count matters (32 vs 8), not the parameter count.

## Decode Is a Bandwidth Problem

Autoregressive decoding emits one token per step, and each step must read the entire KV cache for every sequence in the batch from HBM. The cache is re-read but never rewritten by attention, so decode attention moves ~2 FLOPs per byte loaded - the definition of memory-bound. (Prefill is the opposite: compute-bound, which is the regime [Flash Attention](flash-attention.md) optimizes.) The demo below turns the table above into capacity and bandwidth floors using H100 SXM5 numbers (3.35 TB/s HBM3, from NVIDIA's H100 page):

```python
# KV-cache arithmetic + decode bandwidth floor for attention variants.
# MHA/GQA/MQA per token per layer: 2 * kv_heads * head_dim elements  (K and V)
# MLA per token per layer:         (kv_lora_rank + rope_dim) elements
ROWS = [
    # name,                  layers, q_heads, kv_heads, head_dim, (lora,rope), dtype_bytes
    ("Llama-2 7B   MHA",        32,      32,       32,      128, None,         2),
    ("Llama-2 70B  GQA-8",      80,      64,        8,      128, None,         2),
    ("Llama-3 8B   GQA-8",      32,      32,        8,      128, None,         2),
    ("Mistral-7B   GQA-8",      32,      32,        8,      128, None,         2),
    ("DeepSeek-V3  MLA bf16",   61,     128,     None,     None, (512, 64),    2),
    ("DeepSeek-V3  MLA fp8",    61,     128,     None,     None, (512, 64),    1),
]
CTX = 32768            # context length (tokens)
BW = 3.35e12           # H100 SXM5 HBM3 bandwidth, bytes/s
BUDGET = 40 * 2**30    # KV cache budget on one 80 GB GPU
B = 4                  # concurrent sequences for the bandwidth floor

hdr = f"{'model':<21}{'KiB/tok':>9}{'vs MHA':>9}{'@32K GB':>9}{'ms/tok B=4':>12}{'maxbatch':>10}"
print(hdr); print("-" * len(hdr))
for name, L, h, kv, dh, mla, bpe in ROWS:
    if mla:
        per_tok = L * (mla[0] + mla[1]) * bpe
        mha_eq = L * 2 * h * 128 * bpe   # same 128 heads, 128-dim K/V, no compression
    else:
        per_tok = 2 * L * kv * dh * bpe
        mha_eq = 2 * L * h * dh * bpe
    cache_gb = per_tok * CTX / 1e9            # full-cache bytes, batch 1
    floor_ms = per_tok * CTX * B / BW * 1e3   # streaming the whole cache, batch B
    maxbatch = int(BUDGET // (per_tok * CTX))
    print(f"{name:<21}{per_tok/1024:>9.1f}{mha_eq/per_tok:>8.1f}x{cache_gb:>9.2f}{floor_ms:>12.2f}{maxbatch:>10}")

w70 = 2 * 70e9  # Llama-2 70B bf16 weight bytes
print(f"\nweight-stream floor, 70B bf16 @ B=1: {w70/BW*1e3:.1f} ms/token")
print("KV floor above is ADDITIVE per sequence: bytes scale with B x C, weights do not.")
```

Output (verified by running the script):

```text
model                  KiB/tok   vs MHA  @32K GB  ms/tok B=4  maxbatch
----------------------------------------------------------------------
Llama-2 7B   MHA         512.0     1.0x    17.18       20.51         2
Llama-2 70B  GQA-8       320.0     8.0x    10.74       12.82         4
Llama-3 8B   GQA-8       128.0     4.0x     4.29        5.13        10
Mistral-7B   GQA-8       128.0     4.0x     4.29        5.13        10
DeepSeek-V3  MLA bf16     68.6    56.9x     2.30        2.75        18
DeepSeek-V3  MLA fp8      34.3    56.9x     1.15        1.37        37

weight-stream floor, 70B bf16 @ B=1: 41.8 ms/token
KV floor above is ADDITIVE per sequence: bytes scale with B x C, weights do not.
```

Reading it: at batch 1 the 70B's weight stream (41.8 ms/token) dwarfs any KV floor, so cache arithmetic is a *capacity* problem first - see the maxbatch column. But the KV read scales linearly with batch and context (B = 4 sequences at 32K context means 43 GB read per generated token on the 70B), while weight traffic stays flat: past a modest batch size, the variant's cache reduction is what converts HBM bandwidth into served throughput. This is exactly the regime MQA was designed for.

## GQA: Grouped KV, the Default at Scale

GQA assigns each of g KV heads to a group of n_h/g query heads that share it. Two results from the GQA paper (Ainslie et al., EMNLP 2023) explain why GQA-8 is the standard choice in Llama 2 70B, Llama 3, Mistral, Mixtral, and Qwen:

- **Cheap conversion.** An MHA checkpoint is uptrained into GQA by mean-pooling each group's K (and V) projection matrices to initialize the shared ones, then resuming training - the paper's recipe uses "5% of original pre-training compute".
- **Quality holds.** The paper reports "uptrained GQA achieves quality close to multi-head attention while being almost as fast as multi-query attention". MQA's quality cliff is real; GQA-8 closes most of it while keeping a 4-8x cache cut.

Kernel interplay: flash-style kernels take "KV with fewer heads" directly (the flash-attention README states MQA/GQA is supported by passing fewer KV heads) and loop the group's query heads over one loaded KV tile, so the shared KV block is read once per tile, not once per query head:

```text
        Q heads in group:   h0   h1   h2   h3
                              \   |   |   /
        Q tile (SRAM):       [q0  q1  q2  q3]
                                     |
        K/V tile (shared):   [k_j | v_j]   loaded ONCE from HBM
                                     |
        S = Q_tile @ K^T -> online softmax -> O += P @ V
```

The wrong shape at inference is materializing the sharing with `repeat_interleave` before calling a kernel: that writes 4-8x more KV bytes into memory and makes the kernel read the duplicated blocks back. Pass fewer KV heads to the kernel and let it share tiles. (The training-side view of GQA, including parameter counting, is in the GQA section of [KV Cache Compression](kv-cache-compression.md).)

## MQA: The One-Head Extreme

MQA (Shazeer, 2019) shares a single K/V head across all query heads: an n_h-fold cache reduction and n_h-fold fewer bytes to stream during decode attention, at a measurable quality cost relative to MHA. PaLM adopted multi-query attention explicitly to speed up decoder inference. In the arithmetic above, MQA is simply GQA with g = 1; production models converged on g = 8 as the quality/throughput knee (per-model details: [Llama](../sota/llama.md), [Mistral](../sota/mistral.md)).

## MLA: Low-Rank Latent KV

MLA (introduced in DeepSeek-V2, deployed through the DeepSeek model line - see [DeepSeek](../sota/deepseek.md)) replaces per-head K/V with a joint low-rank latent:

```text
c_t = W_DKV h_t              (d_c = 512 elements: the ONLY K/V thing cached)
k_t = W_UK c_t               (up-projection to per-head keys; NOT materialized in decode)
v_t = W_UV c_t               (likewise for values)
RoPE branch: k_R = RoPE(W_KR h_t), d_R = 64 elements, cached alongside c_t
```

Why the separate rope branch: RoPE rotates q and k by position-dependent angles before the dot product, so a position-dependent key cannot be folded into a static query projection. The rope key (64 elements) rides along with the latent: 576 cached elements per token per layer. The DeepSeek-V2 paper describes the decode path precisely: "MLA only needs to cache c^KV ... since W^UK can be absorbed into W^Q, and W^UV can be absorbed into W^O, we even do not need to compute keys and values out for attention."

```text
cached:   [ c (512) | k_R (64) ]

unabsorbed (training view)        absorbed (decode kernel)
  k = W_UK c                         q' = q @ W_UK^T        (static per-head matrix)
  s = q.k + q_R.k_R                  s = q'.c + q_R.k_R
  v = W_UV c                         out = W_O applied to (sum_t p_t c_t) with W_UV absorbed
```

Absorption is an associativity identity, so absorbed and unabsorbed scores agree to float rounding; the rank-512 constraint is real but it is a training-time property, not an approximation of some external K. DeepSeek-V2 summarizes the trade: the cache is "equal to GQA with only 2.25 groups, but its performance is stronger than MHA". The demo verifies all three claims at toy scale:

```python
# MLA: absorbed attention is exact; the latent is the model's own definition of K.
def transpose(A):
    return [list(r) for r in zip(*A)]

def matvec(A, x):
    return [sum(a * b for a, b in zip(r, x)) for r in A]

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def lcg(seed):
    """Tiny deterministic LCG -> floats in [-1, 1)."""
    state = seed
    while True:
        state = (state * 6364136223846793005 + 1442695040888963407) % 2**64
        yield state / 2**63 - 1.0

rng = lcg(42)
def randvec(n):
    return [next(rng) for _ in range(n)]

def randmat(r, c):
    return [[next(rng) for _ in range(c)] for _ in range(r)]

# --- check 1: absorption is exact (real arithmetic), float error only ---
d, c = 8, 4                    # model dim, latent dim (one head, RoPE aside)
W_DKV = randmat(c, d)          # h -> latent
W_UK = randmat(d, c)           # latent -> key (one head's slice)
h_t = randvec(d)
c_kv = matvec(W_DKV, h_t)      # the ONLY thing cached (plus the RoPE key)
q = randvec(d)

s_unabs = dot(q, matvec(W_UK, c_kv))          # materialize K, then score
q_abs = matvec(transpose(W_UK), q)            # absorb W_UK into the query side
s_abs = dot(q_abs, c_kv)
print(f"score unabsorbed = {s_unabs:+.12f}")
print(f"score absorbed   = {s_abs:+.12f}")
print(f"abs diff         = {abs(s_unabs - s_abs):.2e}  (float rounding only)")

# --- check 2: latent IS a rank-c compression; vs a hypothetical full-rank K ---
W_K = randmat(d, d)
k_true = matvec(W_K, h_t)
k_hat = matvec(W_UK, c_kv)
norm = lambda v: sum(x * x for x in v) ** 0.5
rel = norm([a - b for a, b in zip(k_true, k_hat)]) / norm(k_true)
print(f"rank-4 latent vs full-rank K, relative error = {rel:.3f}")

# --- check 3: DeepSeek-V2/V3 cache equivalence to GQA groups ---
nh, dh, dc, dr = 128, 128, 512, 64
mha_elems = 2 * nh * dh        # K + V, every head, per token per layer
mla_elems = dc + dr
print(f"MHA {mha_elems} elems vs MLA {mla_elems} elems -> {mha_elems/mla_elems:.2f}x")
print(f"equivalent GQA groups g: 2*g*{dh} = {mla_elems} -> g = {mla_elems/(2*dh):.2f}")
```

Output (verified by running the script):

```text
score unabsorbed = +1.160574173576
score absorbed   = +1.160574173576
abs diff         = 2.22e-16  (float rounding only)
rank-4 latent vs full-rank K, relative error = 1.512
MHA 32768 elems vs MLA 576 elems -> 56.89x
equivalent GQA groups g: 2*g*128 = 576 -> g = 2.25
```

Check 1 confirms absorption is an identity (agreement to 2e-16). Check 2 shows a rank-4 latent differs from a random full-rank K by relative norm 1.5: MLA does not approximate a pre-existing K - the model's attention is *defined* on the up-projected latent, so training adapts to the rank budget. Check 3 reproduces the paper's equivalence: 2 x g x 128 = 576 gives g = 2.25.

## Serving-Stack Integration

- **FlashMLA** (DeepSeek, open source) is the production MLA kernel suite; its README states it powers DeepSeek-V3 and DeepSeek-V3.2-Exp, ships dense prefill/decode kernels plus token-level sparse kernels for DeepSeek Sparse Attention achieving "up to 640 TFlops during prefilling and 410 TFlops during decoding", and a Hopper update delivers "up to 660 TFlops on NVIDIA H800 SXM5 GPUs".
- **vLLM and TensorRT-LLM** implement dedicated MLA backends (paged latent cache plus absorbed kernels) and handle GQA natively in their flash backends - see [vLLM Internals](vllm-internals.md) and [Inference Systems](inference-systems.md).
- **FlashAttention-2/3** support MQA/GQA natively by taking fewer KV heads; FA3 adds Hopper asynchrony and fp8 - see [Flash Attention](flash-attention.md).
- **MLA is not a drop-in** for MHA-shaped kernels: the cached layout (one 576-wide latent per token, no per-head K/V) requires its own kernels; pointing a GQA flash kernel at a latent cache is a category error.

## Pitfalls

1. **Materialized GQA at inference.** `repeat_interleave` before a kernel multiplies KV bytes by the group size and forces duplicate HBM reads; pass fewer KV heads instead.
2. **Counting heads, not head_dim.** Cache bytes scale with kv_heads x head_dim; two 8B models with the same layer count differ 4x in cache purely from the KV-head count.
3. **Assuming projection shapes transfer.** GQA checkpoints have `num_key_value_heads`-shaped K/V projections; loading them into an MHA engine config fails in reshapes, not loudly.
4. **Dropping the rope cache in MLA.** The 64-dim decoupled key is per-token cache too: 576 = 512 + 64, not 512.
5. **Conflating fp8 storage with fp8 compute.** An fp8 KV cache halves bytes; kernels still dequantize tiles for the softmax path.
6. **Reusing GQA throughput rules for MLA.** Absorbed MLA kernels move up-projection FLOPs to the query/output side, so their roofline differs from a GQA kernel at equal cached bytes; benchmark with the real kernel.

## Numbers Worth Remembering

- Cache bytes/token = 2 x layers x kv_heads x head_dim x dtype (MHA/GQA/MQA); layers x (d_c + d_R) x dtype (MLA).
- GQA reduction factor = n_h / g: Llama-2 70B 64/8 = 8x; Llama-3 8B 32/8 = 4x.
- DeepSeek-V2/V3 MLA caches 576 elements/token/layer = GQA with 2.25 groups, with reported quality above MHA.
- Decode attention reads B x C x cache-bytes-per-token from HBM per generated token; weights are read once regardless of B.
- MHA -> GQA uptraining costs ~5% of original pre-training compute (GQA paper).

## References

- N. Shazeer, "[Fast Transformer Decoding: One Write-Head is All You Need](https://arxiv.org/abs/1911.02150)" (2019) - the MQA paper
- J. Ainslie et al., "[GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245)" (EMNLP 2023) - uptraining recipe and quality results
- DeepSeek-AI, "[DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model](https://arxiv.org/abs/2405.04434)" - MLA mechanism, absorption, 2.25-group equivalence
- DeepSeek-AI, "[DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437)" - V3 MLA dims used in the tables above
- [DeepSeek-V3 released config.json](https://huggingface.co/deepseek-ai/DeepSeek-V3/raw/main/config.json) - kv_lora_rank 512, rope 64, 61 layers (verified)
- [Llama-2 70B config](https://huggingface.co/NousResearch/Llama-2-70b-hf/raw/main/config.json) and [Llama-3 8B config](https://huggingface.co/NousResearch/Meta-Llama-3-8B/raw/main/config.json) (open mirrors of the released weights)
- [FlashMLA GitHub repository](https://github.com/deepseek-ai/FlashMLA) - production MLA kernels; performance figures quoted above
- [flash-attention GitHub repository](https://github.com/Dao-AILab/flash-attention) - "Supports multi-query and grouped-query attention (MQA/GQA) by passing in KV with fewer heads"
- A. Chowdhery et al., "[PaLM: Scaling Language Modeling with Pathways](https://arxiv.org/abs/2204.02311)" - multi-query attention at scale
- Mistral AI, "[Mistral 7B](https://arxiv.org/abs/2310.06825)" - GQA-8 and sliding-window config
- [NVIDIA H100 Tensor Core GPU page](https://www.nvidia.com/en-us/data-center/h100/) - 3.35 TB/s HBM3 bandwidth used in the decode-floor math
