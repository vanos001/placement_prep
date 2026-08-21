# vLLM Internals

vLLM is an open-source LLM inference engine, developed by LMSYS (Large Model Systems Organization) at UC Berkeley in 2023. It is the most widely-deployed inference engine for production LLM serving, used by Anthropic, Cohere, HuggingFace TGI, and many production deployments. This page covers the architecture (scheduler, block manager, PagedAttention kernel, continuous batching), the production tuning, and the comparison to alternatives (SGLang, TensorRT-LLM, TGI).

## The Architecture

vLLM has four main components:

```text
┌────────────────────────────────────────────────────────────────┐
│  API Server (FastAPI / OpenAI-compatible API)                  │
│  - Receives HTTP requests                                       │
│  - Returns streaming or batched responses                       │
└────────────────────────────────────────────────────────────────┘
            │                                 │
            ▼                                 ▼
┌─────────────────────────┐    ┌───────────────────────────────┐
│  LLMEngine              │    │  AsyncLLMEngine               │
│  - Synchronous          │    │  - Async, integrates with     │
│  - For batched offline  │    │    FastAPI                    │
│    inference             │    │  - For serving                 │
└─────────────────────────┘    └───────────────────────────────┘
            │
            ▼
┌─────────────────────────┐    ┌───────────────────────────────┐
│  Scheduler              │    │  BlockManager                 │
│  - Admits requests      │    │  - Tracks free blocks         │
│  - Pre-empts low-pri    │    │  - Allocates per-request      │
│    requests             │    │    block tables                │
└─────────────────────────┘    └───────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│  Workers (one per GPU; multiple GPUs per replica)               │
│  - Execute the model forward pass                              │
│  - Use PagedAttention CUDA kernels                             │
└────────────────────────────────────────────────────────────────┘
```

## Continuous Batching

The key innovation: continuous batching. Unlike static batching (where a batch is fixed at the start and runs to completion), continuous batching dynamically adds and removes requests from the batch:

```text
Time:    0    1    2    3    4    5    6    7
Batch:   R1   R1   R1   R1   R1   .    .    .   ← R1 finishes at t=5
         R2   R2   R2   .    .    .    .    .   ← R2 finishes at t=3
         R3   R3   R3   R3   R3   R3   R3   .   ← R3 still going
         .    R4   R4   R4   R4   .    .    .   ← R4 starts at t=1, ends at t=5
         .    .    R5   R5   R5   R5   R5   R5  ← R5 starts at t=2
         .    .    .    .    R6   R6   R6   R6  ← R6 starts at t=4
```

At each step (forward pass), the scheduler picks the requests to include in this step. Requests that finish are removed; new requests can be added. This maximizes GPU utilization — no waiting for slow requests to finish.

## The Block Manager

The block manager tracks the KV cache's memory as fixed-size blocks (default 16 tokens per block):

```text
Free blocks: [B0, B1, B2, B3, B4, B5, ...]

Request R1's block table: [B0, B1, B2]   ← 48 tokens generated so far
Request R2's block table: [B3, B4]        ← 32 tokens generated so far
Request R3's block table: [B5, B6, B7, B8]  ← 64 tokens

Next token for R1 needs a new block if position 48-63 will be needed
(but R1 is at token 47, so no new block yet)
```

When a request finishes, its blocks are returned to the free list. The block manager handles pre-emption (in low-memory conditions, the scheduler can swap a request's blocks to CPU and resume later).

For more on PagedAttention, see the [Paged Attention](./paged-attention.md) page.

## The Scheduler

The scheduler runs every step (every token of every active request). It:

1. Computes the batch size for this step (sum of active sequences).
2. Checks if there's enough KV cache memory for the new tokens.
3. If memory is tight, pre-empts the lowest-priority request (FIFO order, by default).
4. Issues the batch to the GPU workers.

The scheduler's "priority" can be:
- **FCFS** (default): oldest request has highest priority.
- **Throughput**: maximize total tokens/sec.
- **Latency**: minimize per-request latency (shorter sequences have priority).

## Multi-GPU Execution

vLLM supports multi-GPU execution via tensor parallelism:

```bash
# Run on 4 GPUs with TP=4
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-70b-hf \
    --tensor-parallel-size 4
```

The model is partitioned across 4 GPUs (Megatron-style TP). Each GPU holds 1/4 of the model's parameters. The KV cache is also partitioned: each GPU holds the KV cache for 1/4 of the attention heads.

For multi-node deployment, vLLM uses Ray or multiprocessing. Each replica runs on a single node; multiple replicas are load-balanced.

## Production Performance

vLLM's published performance on Llama-2 70B with batch=256, 4×A100 80GB:
- Throughput: 2300 tokens/sec/GPU (9200 total).
- Latency: ~50 ms per token (with continuous batching).

For comparison:
- HuggingFace `transformers` (no PagedAttention, no continuous batching): 25 tokens/sec/GPU.
- TGI (uses paged attention since 1.0): 1500 tokens/sec/GPU.

vLLM's 90× improvement over `transformers` is mostly from continuous batching (running 256 concurrent requests instead of 1) and PagedAttention (efficient KV cache management).

## OpenAI-Compatible API

vLLM exposes an OpenAI-compatible HTTP API:

```bash
# Start the server
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-70b-hf

# Use the API (same as OpenAI's API)
curl -X POST http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "meta-llama/Llama-2-70b-hf",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100
    }'
```

This makes vLLM a drop-in replacement for OpenAI's API — clients using the `openai` Python library can switch to a vLLM server by changing the base URL.

## Production Tuning

Key tuning parameters:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-70b-hf \
    --tensor-parallel-size 4 \          # 4-way TP
    --gpu-memory-utilization 0.9 \      # use 90% of GPU memory for KV cache
    --max-model-len 4096 \              # max sequence length
    --max-num-seqs 256 \                # max concurrent sequences
    --enable-prefix-caching \           # cache common prefixes (RAG)
    --quantization awq                  # use AWQ quantization
```

The most important tunables:
- `--gpu-memory-utilization`: how much GPU memory to use for KV cache. 0.9 leaves 10% for the model and other overhead.
- `--max-num-seqs`: max concurrent requests. Too low wastes GPU; too high increases latency.
- `--enable-prefix-caching`: caches common prefixes (e.g., the system prompt), reducing KV cache memory.

## Common Pitfalls

1. **Forgetting to set `--max-model-len` correctly.** Default is the model's max length (e.g., 4096 for Llama-2). For long-context models (e.g., Llama-3 with 128K context), the KV cache requires more memory — adjust accordingly.

2. **Setting `--gpu-memory-utilization` too high.** Above 0.95 risks OOM during model loading. Stay at 0.85-0.9.

3. **Forgetting that vLLM's continuous batching can cause inconsistent latency.** A new request added to the batch increases per-token latency for existing requests. Set `--max-num-batched-tokens` to limit the batch.

4. **Forgetting to enable prefix caching for RAG workloads.** Without it, every RAG query recomputes the KV cache for the system prompt — wastes compute.

5. **Forgetting that quantization affects quality.** AWQ and GPTQ quantizations reduce quality by 1-3% on most benchmarks. Test before deploying.

6. **Forgetting that vLLM's API is OpenAI-compatible but not identical.** Some OpenAI features (e.g., function calling, vision models) may not be supported for all models.

## Comparison to Alternatives

| Aspect | vLLM | SGLang | TensorRT-LLM | TGI |
|--------|------|--------|---------------|------|
| Open source | Yes (Apache 2.0) | Yes | Yes (Apache 2.0) | Yes |
| Native focus | LLM serving | LLM + structured gen | NVIDIA-optimized | HuggingFace |
| Continuous batching | Yes | Yes | Yes | Yes |
| Paged attention | Yes | Yes | Yes (own impl) | Yes |
| Prefix caching | Yes | Yes (RadixAttention) | Yes | No |
| Multi-LoRA | Yes | Yes | Yes | Yes |
| Quantization | AWQ, GPTQ, INT8 | AWQ, GPTQ | INT8, INT4 | bitsandbytes |
| Production users | Many (Anthropic, Cohere, ...) | Many | NVIDIA partners | HuggingFace |

For greenfield deployments in 2024+: vLLM and SGLang are the leading choices. vLLM has more mature community support; SGLang has more advanced prefix caching via RadixAttention. TensorRT-LLM is the choice if you're already on NVIDIA hardware and need the absolute best performance.

## References

- Kwon et al., "[Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180)" (SOSP 2023)
- [vLLM GitHub repository](https://github.com/vllm-project/vllm)
- [vLLM documentation](https://docs.vllm.ai/)
- [vLLM blog: 22x throughput](https://blog.vllm.ai/2023/06/20/vllm.html)
- [SGLang: RadixAttention for prefix caching](https://github.com/sgl-project/sglang)
- [TensorRT-LLM documentation](https://github.com/NVIDIA/TensorRT-LLM)
- [HuggingFace TGI documentation](https://huggingface.co/docs/text-generation-inference)
- [LWN: vLLM internals (2024)](https://lwn.net/Articles/936632/)
