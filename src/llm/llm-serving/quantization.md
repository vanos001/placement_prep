# Quantization

## Overview

Quantization reduces the precision of model weights (and optionally activations) from floating-point to lower-bit representations. This reduces memory usage, improves inference speed, and lowers cost — with minimal quality loss. For LLMs, quantization is essential for serving models on consumer hardware and reducing GPU requirements in production.

## Precision Levels

```mermaid
graph LR
    FP32[FP32 - 32 bits] --> FP16[FP16 - 16 bits]
    FP16 --> INT8[INT8 - 8 bits]
    INT8 --> INT4[INT4 - 4 bits]
    INT4 --> INT2[INT2 - 2 bits]

    FP32 -.-> |"4 bytes/param"| M32["7B = 28 GB"]
    FP16 -.-> |"2 bytes/param"| M16["7B = 14 GB"]
    INT8 -.-> |"1 byte/param"| M8["7B = 7 GB"]
    INT4 -.-> |"0.5 bytes/param"| M4["7B = 3.5 GB"]
    INT2 -.-> |"0.25 bytes/param"| M2["7B = 1.75 GB"]
```

## Quantization Methods

### Post-Training Quantization (PTQ)

Quantize after training without retraining:

```mermaid
graph LR
    MODEL[Trained FP16 Model] --> CALIBRATE[Calibration]
    CALIBRATE --> QUANT[Quantize Weights]
    QUANT --> QUANT_MODEL[Quantized Model]
```

### Quantization-Aware Training (QAT)

Simulate quantization during training:

```mermaid
graph LR
    MODEL[Model] --> FAKE[Fake Quantize in Forward Pass]
    FAKE --> TRAIN[Train with Quantization Simulation]
    TRAIN --> QAT_MODEL[QAT Model]
```

QAT is more accurate but rarely used for LLMs due to training cost.

## Key Quantization Methods

### GPTQ (GPT Quantization)

Post-training quantization to INT4/INT3 using layer-wise optimization:

```mermaid
graph TD
    LAYER[Weight Matrix W] --> HESSIAN["Compute Hessian (importance)"]
    HESSIAN --> GROUP["Group columns (128 typical)"]
    GROUP --> QUANTIZE[Quantize each group]
    QUANTIZE --> COMPENSATE[Compensate error using Hessian]
    COMPENSATE --> NEXT[Move to next layer]
```

**How GPTQ works:**
1. Process one layer at a time
2. Compute the Hessian (second-order information) to determine weight importance
3. Quantize weights in groups (e.g., 128 columns)
4. Use the Hessian to redistribute quantization error to unquantized weights
5. Move to next layer

**GPTQ Configuration:**
```python
from transformers import AutoModelForCausalLM, GPTQConfig

quantization_config = GPTQConfig(
    bits=4,                    # 4-bit quantization
    dataset="c4",             # Calibration dataset
    group_size=128,           # Quantization group size
    desc_act=True,            # Descending activation order
)

model = AutoModelForCausalLM.from_pretrained(
    "model-name",
    quantization_config=quantization_config,
    device_map="auto"
)
```

### AWQ (Activation-Aware Weight Quantization)

Protects important weights based on activation patterns:

```mermaid
graph TD
    ACT[Run calibration data] --> IMPORTANCE[Measure activation magnitude per channel]
    IMPORTANCE --> SCALE[Scale important channels before quantization]
    SCALE --> QUANT[Quantize to INT4]
    QUANT --> FUSE[Fuse scaling into weights]
```

**Key insight:** Not all weights are equally important. Weights that receive large activations should be quantized more carefully (or left at higher precision). AWQ identifies these channels and scales them to protect precision.

**AWQ vs GPTQ:**

| Aspect | GPTQ | AWQ |
|---|---|---|
| **Method** | Hessian-based error compensation | Activation-aware scaling |
| **Speed** | Slower quantization | Faster quantization |
| **Quality** | Good | Slightly better |
| **Hardware** | General | Optimized kernels |
| **Group size** | 128 typical | 128 typical |

### GGUF (llama.cpp format)

GGUF is the quantization format used by llama.cpp and Ollama:

| Type | Bits/Weight | Quality | Speed |
|---|---|---|---|
| **Q2_K** | 2.6 | Low | Fastest |
| **Q3_K_M** | 3.9 | Fair | Fast |
| **Q4_0** | 4.5 | Good | Good |
| **Q4_K_M** | 4.8 | Good | Good |
| **Q5_K_M** | 5.7 | Very good | Moderate |
| **Q6_K** | 6.6 | Excellent | Slower |
| **Q8_0** | 8.5 | Near-lossless | Slowest |

```python
# Convert model to GGUF
python convert_hf_to_gguf.py model-name --outfile model.gguf

# Quantize
./llama-quantize model.gguf model-q4_k_m.gguf Q4_K_M
```

### bitsandbytes (BNB)

Dynamic quantization integrated with Hugging Face:

```python
import torch
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# 8-bit quantization
bnb_config_8bit = BitsAndBytesConfig(load_in_8bit=True)

# 4-bit NF4 quantization (used by QLoRA)
bnb_config_4bit = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",           # NormalFloat4
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,       # Double quantization
)

model = AutoModelForCausalLM.from_pretrained(
    "model-name",
    quantization_config=bnb_config_4bit,
    device_map="auto"
)
```

## NF4 (4-bit NormalFloat)

NF4 (Dettmers et al., 2023) is an information-theoretically optimal quantization for normally distributed weights:

```mermaid
graph TD
    NORM["LLM weights ~ Normal distribution"] --> NF4["NF4: Quantiles of normal distribution"]
    NF4 --> BITS["4 bits → 16 levels"]
    BITS --> OPTIMAL["Optimal for normal distributions"]
```

Standard INT4 uses uniform spacing. NF4 uses non-uniform spacing that matches the normal distribution — more levels near zero where most weights are.

## Quantization Trade-offs

| Precision | Memory (7B) | Speed | Quality Loss | Use Case |
|---|---|---|---|---|
| FP16 | 14 GB | Baseline | None | Production baseline |
| INT8 | 7 GB | 1.5-2× | <0.5% perplexity | Production standard |
| INT4 (GPTQ/AWQ) | 3.5 GB | 2-3× | 1-3% perplexity | Consumer GPUs |
| INT4 (NF4/QLoRA) | 3.5 GB | 2-3× | 1-2% perplexity | Fine-tuning |
| INT3 | 2.6 GB | 2-4× | 3-5% perplexity | Very tight memory |
| INT2 | 1.75 GB | 3-5× | 5-10% perplexity | Extreme compression |

## Activation Quantization

Weight quantization is common; activation quantization is harder:

| Approach | Weights | Activations | Complexity |
|---|---|---|---|
| **W-only** | INT4/INT8 | FP16 | Simple |
| **W+A** | INT8 | INT8 | Moderate |
| **W4A8** | INT4 | INT8 | Advanced |
| **FP8** | FP8 | FP8 | NVIDIA H100+ |

### FP8 (Float8)

FP8 is emerging as the standard for H100/H200 GPUs:

```
FP8 E4M3: 4-bit exponent, 3-bit mantissa (for weights)
FP8 E5M2: 5-bit exponent, 2-bit mantissa (for gradients)
```

- 2× memory reduction vs FP16
- Near-lossless quality
- Hardware support on H100+
- Used in TensorRT-LLM, vLLM

## SmoothQuant

SmoothQuant (Xiao et al., 2023) makes activation quantization easier by migrating quantization difficulty from activations to weights:

```
Y = (X · diag(s)^{-1}) · (diag(s) · W) = X̂ · Ŵ
```

**Key insight:** Activations have outliers (some channels have very large values), making them hard to quantize. By dividing activations by a scaling factor s and multiplying weights by s, we smooth out the outliers. Both X̂ and Ŵ are easier to quantize.

## Interview Questions

### Q1: Explain the difference between GPTQ and AWQ.
**Answer:**
- **GPTQ**: Uses second-order (Hessian) information to determine weight importance. Quantizes layer-by-layer, using the Hessian to redistribute quantization error to unquantized weights. Good general-purpose method.
- **AWQ**: Uses activation magnitudes to identify important weight channels. Scales important channels before quantization to protect their precision. Often slightly better quality and faster inference with optimized kernels.
- Both are post-training methods that quantize to INT4 with group-wise quantization (group_size=128 typical).

### Q2: What is NF4 and why is it better than INT4 for LLMs?
**Answer:** NF4 (NormalFloat4) is a quantization format where the 16 quantization levels are placed at the quantiles of a standard normal distribution. Since LLM weights are approximately normally distributed, NF4 is information-theoretically optimal — it minimizes quantization error for normally distributed data. Standard INT4 uses uniform spacing, which wastes levels on regions where few weights exist. NF4 is used in QLoRA for 4-bit fine-tuning.

### Q3: How does group_size affect quantization quality?
**Answer:** Group size determines how many weights share the same quantization parameters (scale and zero-point). Smaller group size (e.g., 32) = more accurate but more overhead (more scales to store). Larger group size (e.g., 128) = less accurate but less overhead. Common choice is 128, which provides a good balance. The overhead per parameter is: log2(group_size) / group_size bits.

### Q4: Can you quantize a model to 2 bits?
**Answer:** Technically yes (Q2_K in GGUF), but quality degrades significantly. At 2 bits, you only have 4 possible values per weight. Large models (70B+) can sometimes tolerate 2-bit quantization better than small models because the redundancy is higher. However, for production use, INT4 is typically the minimum for acceptable quality. INT2 is mainly used for extreme edge deployment or research.

### Q5: What is the difference between weight-only and weight+activation quantization?
**Answer:**
- **Weight-only**: Only model weights are quantized (INT4/INT8). Activations remain FP16. Simpler, widely supported, good quality.
- **Weight+activation (W+A)**: Both weights and activations are quantized (e.g., W8A8). Better throughput (integer GEMM is faster) but harder to maintain quality due to activation outliers. Requires techniques like SmoothQuant.
- **W4A8**: Weights in INT4, activations in INT8. Emerging standard balancing quality and speed.

## Common Mistakes

- ❌ Assuming INT4 is always "good enough" (quality depends on model, task, and method)
- ❌ Not testing quantized models on your specific use case before deploying
- ❌ Forgetting that quantization affects different layers differently (some are more sensitive)
- ❌ Confusing weight quantization with activation quantization
- ❌ Ignoring that KV cache can also be quantized (separate from weight quantization)

## Summary

Quantization reduces LLM memory and compute by using lower-precision representations. GPTQ and AWQ are the main INT4 methods for production. NF4 is optimal for normally distributed weights (used in QLoRA). GGUF is the standard for CPU/edge deployment. FP8 is emerging for H100+ GPUs. The trade-off between size and quality must be evaluated per use case.

## Cross-References

- [Architecture →](architecture.md) Weight matrices being quantized
- [KV Cache →](kv-cache.md) KV cache quantization
- [SFT →](sft.md) QLoRA fine-tuning with NF4
- [Inference →](inference.md) Speed improvements from quantization
- [vLLM →](vllm.md) Quantized model serving
- [Ollama →](ollama.md) GGUF model deployment
- [ML Quantization](../../ml/advanced/quantization.md)
- [TensorRT](./tensorrt.md)
- [Model Compression](../../ml/advanced/compression.md)
