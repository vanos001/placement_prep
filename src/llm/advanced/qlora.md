# QLoRA

QLoRA (Quantized LoRA) is a fine-tuning method introduced by Tim Dettmers et al. in 2023 (NeurIPS 2023) that combines 4-bit NormalFloat (NF4) quantization of the base model with LoRA training. The result: a 70B model can be fine-tuned on a single 48 GB GPU (vs. ~80 GB for plain LoRA or ~560 GB for full fine-tuning). This page covers the NF4 quantization format, the double-quantization optimization, the paged-attention integration, and the production trade-offs vs. plain LoRA.

## The Memory Problem

For a 70B model in bf16:
- Model: 140 GB
- LoRA matrices (r=8): ~100 MB
- Adam optimizer state: ~400 MB (for the LoRA params only)
- Activations (with gradient checkpointing): ~10-20 GB
- KV cache (for inference): ~5-10 GB
- Total: ~150-180 GB

Plain LoRA on a 70B model needs a 192 GB GPU (or 2× 80 GB). QLoRA reduces the model footprint by 4× via 4-bit quantization, bringing the total to ~50 GB — fits on one 48 GB GPU.

## NF4: NormalFloat 4-Bit

The key insight: pre-trained neural network weights are approximately normally distributed (with mean 0 and a known variance). Quantizing them to 4 bits with a uniform grid (like int4) wastes bits on tail values that are rare. NF4 uses a non-uniform grid optimized for normal distributions:

```text
Standard int4 grid (uniform):
  {-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7}

NF4 grid (s-optimal for normal):
  {-1.0, -0.6962, -0.5251, -0.3949, -0.2844, -0.1848, -0.0911, 0,
    0.0796, 0.1609, 0.2461, 0.3379, 0.4407, 0.5626, 0.7230, 1.0}
```

NF4's 16 levels are computed by `2^(k/8)` for k=1..15, normalized to fit in [-1, 1]. The densest grid points are near 0 (where normal-distributed weights are most common), the sparsest at the tails.

NF4's mean-squared-error on normally-distributed weights is ~30% lower than int4's, with no computational overhead (the dequantization is a single lookup).

## Double Quantization

QLoRA also quantizes the per-tensor scaling factors. Each tensor block (typically 64 elements) has its own scale (a 32-bit float). For a 70B model with 1 billion blocks, that's 4 GB of scaling factors — non-trivial.

Double quantization quantizes the scaling factors themselves to 8 bits (FP8), reducing them to 1 GB. The 8-bit quantization of 32-bit floats is lossless for scales in the typical range (the scales are themselves normally distributed).

Combined: NF4 (4 bits per weight) + 8-bit scales (1 bit per weight on average) = ~5 bits per weight effective. For a 70B model: ~44 GB.

## Paged Attention

QLoRA integrates with paged attention (the same paged-attention used in vLLM) to avoid OOM during long sequences. When the KV cache grows beyond GPU memory, pages are evicted to CPU memory and re-fetched on demand.

For fine-tuning with sequence length 4096 on a 48 GB GPU, the KV cache alone is ~10 GB. Without paging, an OOM is likely. With paging, the cache can spill to CPU memory (slower but no OOM).

## Forward and Backward Passes

QLoRA's forward pass:

```python
def qdora_forward(W_q, x, A, B, alpha, r):
    # Dequantize W on-the-fly
    W = dequantize_nf4(W_q, scale)   # W is bf16, in SRAM
    # Compute base output
    y_base = W @ x
    # Compute LoRA update
    y_lora = (alpha / r) * (B @ (A @ x))
    return y_base + y_lora
```

The dequantization is on-the-fly (per layer, per forward), so the model never materializes the full bf16 weights. The bf16 `W` exists only for the duration of the matrix multiply.

The backward pass:

```python
def qdora_backward(W_q, x, dy, A, B, alpha, r):
    W = dequantize_nf4(W_q, scale)  # same dequantize
    dA = B.T @ dy @ x.T   # dL/dA
    dB = dy @ A @ x       # dL/dB
    # Note: W's gradient is NOT computed (frozen)
    return dA, dB
```

The dequantization happens twice per layer per step (forward + backward). This is QLoRA's main overhead: the dequantization is ~10-20% of the matrix multiply time, so training is ~20% slower than plain bf16 LoRA.

## Memory Budget

For a 70B model with QLoRA, sequence length 4096, batch 4 on a 48 GB GPU (RTX 6000 Ada):

- Model (NF4 + double-quant scales): ~36 GB
- LoRA matrices (r=16, all attention + MLP): ~200 MB
- Adam optimizer state (fp32 m, v for LoRA): ~800 MB
- Activations (with gradient checkpointing): ~5 GB
- KV cache (paged): ~2-5 GB (spills to CPU if needed)
- Total: ~44 GB → fits in 48 GB

## Quality Comparison to Plain LoRA

QLoRA's quality matches plain bf16 LoRA within 1-2% on most benchmarks:

| Method | Llama-2 70B MMLU | Llama-2 70B GSM8k | Memory (48 GB GPU) |
|--------|------------------|-------------------|---------------------|
| bf16 LoRA (r=16) | 65.3 | 56.1 | Doesn't fit |
| QLoRA (r=16) | 64.8 | 55.6 | Fits |

For most production use cases, the 1% quality drop is acceptable for the 4× memory reduction.

## Common Pitfalls

1. **Using NF4 with non-normal weights.** NF4 assumes normal distribution; if your weights are heavy-tailed (e.g., from a sparse model), int4 with per-channel scales is better.

2. **Forgetting to set `compute_dtype=torch.bfloat16` in the `BitsAndBytesConfig`.** The default is fp32, which gives correct results but is 4× slower.

3. **Forgetting that QLoRA's gradient is for the LoRA matrices only.** The base model's gradients are not computed (the weights are frozen). Calling `model.parameters()` returns all parameters, but only LoRA ones require_grad=True.

4. **Loading the model in bf16 first, then quantizing.** This needs the bf16 model (140 GB) in memory transiently. Load directly from the quantized checkpoint instead:

```python
from transformers import BitsAndBytesConfig, AutoModelForCausalLM

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b",
    quantization_config=quant_config,
    device_map="auto",
)
```

5. **Inference with QLoRA is slower than with a merged bf16 model.** The on-the-fly dequantization adds 10-20% latency. For production serving, merge LoRA into the model and re-quantize the merged model for inference (or use vLLM with the unmerged QLoRA adapter).

6. **Forgetting that gradient checkpointing is mandatory.** Without it, the activations of a 70B model with sequence 4096 are ~80 GB. With it, ~5 GB. Always enable `model.gradient_checkpointing_enable()`.

## Production Deployment

QLoRA is the recommended approach for fine-tuning 70B+ models on a single GPU. The standard pipeline:

```python
# 1. Load model in NF4 quantization
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b-hf",
    quantization_config=quant_config,
    device_map="auto",
)

# 2. Add LoRA adapters
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

model = prepare_model_for_kbit_training(model)
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)

# 3. Train
trainer = Trainer(
    model=model,
    train_dataset=dataset,
    args=TrainingArguments(
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        max_steps=1000,
        fp16=False,
        bf16=True,
        gradient_checkpointing=True,
    ),
)
trainer.train()

# 4. Save the LoRA adapter (not the base model)
model.save_pretrained("./lora_adapter")  # ~50 MB
# Or merge and save the merged model
model.merge_and_unload().save_pretrained("./merged_model")  # ~140 GB bf16 or ~35 GB NF4
```

## References

- Dettmers et al., "[QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)" (NeurIPS 2023)
- [bitsandbytes library](https://github.com/bitsandbytes-foundation/bitsandbytes)
- [Hugging Face Transformers: 4-bit quantization](https://huggingface.co/blog/4bit-transformers-with-bitsandbytes)
- [PEFT: Parameter-Efficient Fine-Tuning](https://github.com/huggingface/peft)
- [unsloth: Faster QLoRA training](https://github.com/unslothai/unsloth)
- [Tim Dettmers' blog: QLoRA + 4-bit Queens](https://timdettmers.com/2023/05/19/qlora-4-bit-queens/)
