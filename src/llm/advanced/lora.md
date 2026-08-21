# LoRA

LoRA (Low-Rank Adaptation) is a parameter-efficient fine-tuning (PEFT) method introduced by Hu et al. in 2021 (ICLR 2022). It freezes the pre-trained model weights and adds trainable low-rank matrices (`A` and `B`) to each layer's weight matrix, so the fine-tuning delta is `W' = W + B A`. LoRA reduces the trainable parameter count by 100-10,000× and the optimizer state by 50-500×, enabling fine-tuning of 70B+ models on a single GPU. This page covers the math, the rank-`r` trade-off, the merging for inference, and the variants (QLoRA, DoRA, rsLoRA).

## The Math

A standard linear layer computes `y = W x`, where `W` is `d_out × d_in`. During fine-tuning, the gradient `dL/dW` updates `W` via:

```text
W_new = W_old - lr * dL/dW
```

For a 70B model in bf16, `W` is 140 GB; `dL/dW` is another 140 GB; Adam's optimizer state is 280 GB (fp32 m and v). Total: 560 GB. Doesn't fit on an 80 GB GPU.

LoRA's idea: instead of updating `W`, update a low-rank decomposition of the update:

```text
W_new = W_old + ΔW
       = W_old + B A

where:
  A ∈ R^{r × d_in}    ← trainable, init N(0, 1/sqrt(r))
  B ∈ R^{d_out × r}   ← trainable, init zero

For r = 8 and d_in = d_out = 4096 (typical 7B layer):
  A and B together: 8 × 4096 × 2 = 65K parameters
  W has 16M parameters
  LoRA trains 0.4% of the parameters
```

The forward pass is `y = W x + B A x = (W + B A) x`. The backward pass computes `dL/dA = dL/dy * B` and `dL/dB = dL/dy * x^T`, both involving `r`-size intermediate products.

The pre-trained `W` is frozen (no gradient, no optimizer state). Only `A` and `B` are trained. Memory savings:

- Model: same as before (W is loaded but not trained).
- Trainable parameters: `2 r d` per layer instead of `d²`. For r=8, d=4096: 65K vs 16M.
- Optimizer state (Adam): 4× trainable params (fp32 m and v). For LoRA: 260K vs 64M.

For a 7B model with `d=4096` and 96 layers (one A, B per layer): LoRA params = 96 × 65K = 6.2M. Adam state: 25 MB. Original (full FT): 7B × 12 = 84 GB. LoRA: 25 MB. **3,400× memory savings.**

## Rank Selection

The rank `r` controls the trade-off between expressiveness and memory:

| r | Params (relative to full) | Quality (relative to full FT) | Memory savings |
|---|----------------------------|-------------------------------|-----------------|
| 1 | 0.05% | -5% to -10% | 2000× |
| 4 | 0.2% | -3% to -5% | 1000× |
| 8 | 0.4% | -1% to -3% | 500× |
| 16 | 0.8% | -0.5% to -2% | 250× |
| 32 | 1.6% | similar | 125× |
| 64 | 3.2% | similar | 60× |

`r=8` is the standard recommendation for general tasks. `r=16-32` for fine-tuning on narrow domains (coding, math). `r=64` for tasks with very high expressiveness needs (e.g., new language).

The "minimum quality loss" depends on the task; for tasks where the pre-trained model is already strong, `r=8` matches full FT. For tasks far from the pre-training distribution (e.g., a new programming language), higher `r` helps.

## Applying LoRA to Which Layers

LoRA was originally applied only to attention Q and V matrices (`W_Q`, `W_V`). Subsequent work found that applying to all attention matrices (`Q, K, V, O`) and the MLP matrices (`W_1`, `W_2`) gives better quality at the same parameter count:

```python
# Apply LoRA to all attention and MLP matrices
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
```

For Hugging Face's `peft` library:

```python
from peft import LoraConfig, get_peft_model

config = LoraConfig(
    r=8,
    lora_alpha=16,            # scaling factor (see below)
    target_modules=target_modules,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(base_model, config)
```

## The `alpha` Scaling Factor

The LoRA forward pass:

```text
y = W x + (alpha / r) * B A x
```

`alpha` is a scaling factor that controls the magnitude of the LoRA update. Setting `alpha = r` makes the update scale-independent of `r` (doubling `r` doesn't double the update). Setting `alpha = 2r` (the common default) makes the update larger relative to the frozen `W`, which can speed convergence but risks instability.

`alpha = r` (e.g., alpha=8, r=8) is the original paper's recommendation. `alpha = 2 * r` (e.g., alpha=16, r=8) is the popular default in the community.

## Inference: Merging

After training, LoRA's `B A` can be merged into the original `W`:

```text
W_merged = W + (alpha / r) * B A
```

The merged `W_merged` has the same shape as `W`, so inference uses the standard linear layer with no LoRA-specific code. The merged model is bit-for-bit equivalent to the unmerged one (the math is identical).

Merging is useful for:
- **Production deployment**: ship a single merged model, no LoRA-specific runtime.
- **Multiple LoRAs for one base model**: keep the base model in memory, swap LoRA weights per request (no merging). vLLM, TGI, and SGLang support this.

## Multi-LoRA Serving

For services that serve many fine-tuned variants of one base model (e.g., customer-specific chatbots), merging is wasteful — each merged model is the full size of the base. The alternative is **multi-LoRA** serving:

```text
Base model (70B, 140 GB) is loaded once.
LoRA adapters: 100 × 50 MB each = 5 GB total.
Per request: pick the right adapter, do the forward pass.
```

vLLM and TGI support multi-LoRA via:
- Per-request adapter selection.
- Optional adapter merging on-the-fly (if multiple adapters are active for one request).
- Paged attention for the KV cache, with the LoRA's B/A applied per layer.

## LoRA Variants

### QLoRA (2023)

QLoRA combines LoRA with 4-bit NF4 quantization of the base model:

- The base model is quantized to NF4 (4-bit NormalFloat), reducing memory by 4×.
- LoRA matrices `A` and `B` are kept in bf16 (full precision).
- The forward pass: `y = dequantize(W_q) x + B A x` — dequantize on the fly.

Memory: 70B model = 35 GB (NF4) + 100 MB (LoRA r=8) + Adam state (400 MB) = ~36 GB. Fits on a 48 GB GPU (RTX 6000 Ada or A6000).

See the [QLoRA](./qlora.md) page for details.

### DoRA (2024)

DoRA (Decomposed LoRA) decomposes the weight into magnitude and direction:

```text
W = magnitude × direction
LoRA updates the direction only.
Magnitude is a scalar per output channel.
```

DoRA achieves slightly better quality than LoRA at the same parameter count, at the cost of slightly more compute per forward pass.

### rsLoRA (2023)

rsLoRA (rank-stabilized LoRA) uses `alpha = sqrt(r)` instead of `alpha = r`. This makes the update scale-invariant in a different way: the variance of `BA` stays constant as `r` grows. Empirically, rsLoRA gives better results at high `r` (64+).

### GaLore (2024)

GaLore (Gradient Low-Rank Projection) projects the gradient to a low-rank subspace, reducing optimizer memory without changing the model. Different from LoRA (which changes the model), GaLore keeps the model full-rank but optimizes in a low-rank space.

## Common Pitfalls

1. **Setting `r` too low.** `r=1` is rarely enough. Use at least `r=4` for most tasks; `r=8` is the default.

2. **Forgetting to merge for deployment.** A LoRA adapter shipped alone is useless — the base model is also required. Either ship both, or merge into one model.

3. **Forgetting to apply LoRA to MLP matrices.** Applying only to attention is suboptimal; include the MLP's `W_1` (up) and `W_2` (down).

4. **Using `alpha` too high.** `alpha = 4r` makes the LoRA update dominate the base weights, causing instability. Stay at `alpha = r` to `alpha = 2r`.

5. **Not initializing `B` to zero.** LoRA's theory requires `B` to start at zero so the initial forward pass equals the base model's. Some implementations don't enforce this; if `B` is initialized randomly, the first forward pass differs from the base model's, which is fine for fine-tuning but causes issues if you want to "skip" LoRA on the first inference.

6. **Forgetting that LoRA can be applied per-layer (skip some layers).** Not every layer needs LoRA. Sometimes skipping early layers (which are usually representation-learning layers) gives better quality at lower parameter count.

## References

- Hu et al., "[LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)" (ICLR 2022)
- Liu et al., "[DoRA: Weight-Decomposed Low-Rank Adaptation](https://arxiv.org/abs/2402.09353)" (2024)
- Kalajdziev & Narayan, "[rsLoRA: Rank-Stabilized LoRA](https://arxiv.org/abs/2312.03732)" (2023)
- [Hugging Face PEFT library](https://github.com/huggingface/peft)
- [vLLM: Multi-LoRA serving](https://docs.vllm.ai/en/stable/models/lora.html)
- [unsloth: Optimized LoRA training](https://github.com/unslothai/unsloth)
- [PEFT tutorial: fine-tuning Llama-3 with LoRA](https://huggingface.co/blog/peft)
