# TensorRT-LLM

TensorRT-LLM is NVIDIA's open-source library for optimizing LLM inference on NVIDIA GPUs (Hopper, Ampere, Blackwell). It's the highest-performance LLM serving option for NVIDIA hardware, achieving 2-5× the throughput of vLLM on H100 by deeply exploiting the H100's TMA, FP8, and Hopper-specific features. This page covers the architecture, the Hopper-specific optimizations, and the production tuning.

## The Architecture

TensorRT-LLM is built on top of TensorRT (NVIDIA's general inference optimizer), with LLM-specific extensions:

```text
┌────────────────────────────────────────────────────────────────┐
│  Python API (for build + serve)                                │
│  - Build engine from model checkpoint                           │
│  - HTTP API server                                              │
└────────────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│  TensorRT Engine (compiled artifact)                            │
│  - Per-model, per-GPU, per-precision (e.g., Llama-2 70B H100 FP8)│
│  - Pre-compiled, no JIT at runtime                              │
└────────────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│  Plugin Layer (LLM-specific kernels)                            │
│  - GPT Attention plugin (Hopper-optimized)                    │
│  - RMSNorm plugin                                               │
│  - Greedy/sampling/beam search plugin                           │
│  - KV cache manager                                             │
└────────────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│  CUDA + Driver (GPU kernels)                                   │
└────────────────────────────────────────────────────────────────┘
```

The key difference from vLLM/SGLang: TensorRT-LLM compiles the model to a per-GPU engine ahead of time. This enables Hopper-specific kernels that vLLM can't use (vLLM uses generic kernels).

## Building an Engine

```python
# Convert a Hugging Face checkpoint to a TensorRT-LLM engine
import tensorrt_llm
from tensorrt_llm.models import LLaMAForCausalLM

model = LLaMAForCausalLM.from_hugging_face(
    "meta-llama/Llama-2-70b-hf",
    dtype='float16',
    use_fp8=True,  # Hopper FP8
    tp_size=4,     # tensor parallelism
    pp_size=1,    # no pipeline parallelism
)

builder = tensorrt_llm.Builder()
engine = builder.create_engine(model)
engine.save("./llama-2-70b-h100-fp8.engine")
```

The engine is a binary artifact (~30 GB for Llama-2 70B FP8). It's specific to:
- GPU model (H100 engine won't run on A100).
- Precision (FP8 engine is incompatible with FP16 runtime).
- TP size (TP=4 engine can't run on TP=8).

This is more restrictive than vLLM (where the same checkpoint works on any GPU), but enables the Hopper-specific optimizations.

## Hopper-Specific Optimizations

### TMA (Tensor Memory Accelerator)

TMA is a Hopper hardware unit that performs async memory copies between HBM and shared memory. TensorRT-LLM uses TMA to:
- Prefetch the next attention K/V block while computing the current one.
- Overlap memory and compute, hiding HBM latency (~3 TB/s on H100).

For Llama-2 70B with batch=256, TMA gives ~1.5× speedup over non-TMA.

### FP8 Tensor Cores

Hopper's FP8 tensor cores (e4m3 and e5m2) provide 2× the throughput of FP16. TensorRT-LLM's GPT Attention plugin uses FP8 for:
- The Q K^T matrix multiply (attention scores).
- The softmax V multiply (attention output).

The MLP matrices are kept in FP16 (for numerical stability).

Quality impact: ~1-2% degradation vs FP16 on most benchmarks. Throughput: 1.8-2.0× FP16.

### FP8 KV Cache

TensorRT-LLM stores the KV cache in FP8 instead of FP16, halving the memory. This enables:
- Larger batches (more concurrent sequences).
- Longer contexts (more tokens per sequence).

The quality impact is small (~1% on most benchmarks) because the KV cache is already a compressed representation of past tokens.

### Custom CUDA Kernels

TensorRT-LLM ships with highly-tuned CUDA kernels:
- `gptAttentionPlugin`: a single kernel that does the full attention (Q K^T, softmax, V) with TMA + FP8.
- `rmsnormPlugin`: a fused RMSNorm + add residual kernel.
- `gemmSwigluPlugin`: a fused GeMM + SiLU + GEMM kernel (for the MLP).

These kernels are typically 30-50% faster than equivalent cuBLAS + elementwise kernels.

## Continuous Batching

TensorRT-LLM supports continuous batching via the `tensorrt_llm.runtime.GenerationSession` API:

```python
from tensorrt_llm.runtime import GenerationSession

session = GenerationSession(model_config, engine_buffer, runtime_buffer)
session.set_kv_cache_pool(...)

while True:
    requests = queue.get_requests()
    session.generate(requests, max_new_tokens=100)
    for response in session.get_responses():
        send_response(response)
```

The continuous batching is similar to vLLM's: new requests are admitted, finished requests are removed.

## Production Performance

TensorRT-LLM on H100 SXM (80 GB):

| Model | Precision | Throughput (batch=256) | Latency |
|-------|-----------|-------------------------:|--------:|
| Llama-2 7B | FP16 | 6000 tokens/sec | 30 ms |
| Llama-2 7B | FP8 | 11000 tokens/sec | 18 ms |
| Llama-2 70B | FP16 | 1800 tokens/sec | 80 ms |
| Llama-2 70B | FP8 | 3200 tokens/sec | 50 ms |
| Llama-3 70B | FP8 | 3500 tokens/sec | 45 ms |
| Llama-3 70B | INT8 (per-channel) | 3800 tokens/sec | 40 ms |

For comparison, vLLM on the same H100 SXM:
- Llama-2 70B FP16: 1300 tokens/sec (TensorRT-LLM is 1.4× faster).
- Llama-2 70B FP8: 1900 tokens/sec (TensorRT-LLM is 1.7× faster).

The FP8 advantage is more pronounced on TensorRT-LLM because of its optimized FP8 attention kernel.

## The Build-Once Trade-off

TensorRT-LLM engines are per-GPU and per-precision. The build time:
- Llama-2 7B: ~5 minutes.
- Llama-2 70B: ~30 minutes.
- Llama-3 70B with FP8: ~45 minutes.

The engine must be rebuilt when:
- Updating the model checkpoint.
- Changing the GPU type.
- Changing precision (FP8 vs FP16).
- Changing the TP size.

This is a trade-off: longer build time, faster runtime. For production deployments that don't change often, the build time is amortized.

## Comparison to vLLM and SGLang

| Aspect | TensorRT-LLM | vLLM | SGLang |
|--------|--------------|------|--------|
| GPU support | NVIDIA only | NVIDIA + AMD (ROCm) | NVIDIA + AMD |
| Build time | 5-45 min per model | 0 (loads HF checkpoint) | 0 |
| Performance (H100 FP8) | Best (2-5× FP16) | Good | Good |
| Continuous batching | Yes | Yes | Yes |
| Paged attention | Yes | Yes | Yes |
| Prefix caching | Yes (since 0.7) | Yes | Yes (RadixAttention) |
| Quantization | INT4, INT8, FP8, FP16 | AWQ, GPTQ, INT8 | AWQ, GPTQ |
| Multi-LoRA | Yes (since 0.9) | Yes | Yes |
| Ease of deployment | Medium (engine build) | Easy | Easy |

TensorRT-LLM is the choice for:
- NVIDIA-only deployment (no AMD GPU mix).
- Maximum throughput on Hopper hardware.
- Production deployments with stable models (engine builds are infrequent).

vLLM is the choice for:
- Multi-vendor (NVIDIA + AMD).
- Easy deployment without engine building.
- Frequent model updates (HF checkpoint is loaded directly).

## Common Pitfalls

1. **Forgetting that engines are GPU-specific.** A H100 engine won't run on A100. Build per-GPU.

2. **Forgetting that engines are precision-specific.** An FP8 engine can't run with FP16 weights. Build per-precision.

3. **Forgetting that engines are TP-specific.** A TP=4 engine can't run on TP=8. Build per-TP-config.

4. **Forgetting that FP8 quality may differ across models.** Some models (e.g., MoE with extreme outlier weights) lose significant quality under FP8. Test on a held-out benchmark.

5. **Forgetting that engines are large binaries.** A Llama-2 70B FP8 engine is ~30 GB. Plan storage.

6. **Forgetting that the build process downloads model weights.** The first build downloads ~140 GB of weights; subsequent builds can cache them.

## References

- [TensorRT-LLM GitHub repository](https://github.com/NVIDIA/TensorRT-LLM)
- [TensorRT-LLM documentation](https://nvidia.github.io/TensorRT-LLM/)
- NVIDIA, "[H100 Transformer Engine for FP8 inference](https://developer.nvidia.com/blog/hopper-transformer-engine/)" (blog post)
- [NVIDIA TensorRT documentation](https://docs.nvidia.com/deeplearning/tensorrt/)
- [NVIDIA Triton Inference Server](https://docs.nvidia.com/deeplearning/triton-inference-server/)
- [TensorRT-LLM benchmarks](https://github.com/NVIDIA/TensorRT-LLM/blob/main/benchmarks/README.md)
- [LWN: TensorRT-LLM overview (2024)](https://lwn.net/Articles/940012/)
