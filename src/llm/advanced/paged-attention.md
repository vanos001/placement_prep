# Paged Attention

Paged Attention is the memory management scheme for the key-value (KV) cache in LLM inference, introduced by Kwon et al. at SOSP 2023 as part of vLLM. It borrows the idea of virtual memory paging from operating systems: the KV cache is divided into fixed-size blocks (pages), each block is allocated on demand, and the logical-to-physical mapping is maintained per request. This eliminates the memory fragmentation and over-allocation problems that limited earlier LLM serving systems to ~50% of theoretical throughput. This page covers the problem, the paging model, the copy-on-write for beam search, and the production impact on throughput.

## The KV Cache Problem

During LLM inference, the model stores the K (keys) and V (values) for every previous token, so that generating the next token can attend to them. For a 70B model with hidden size 8192, 80 layers, 64 attention heads, and bf16 storage:

```text
KV cache per token = 2 (K and V) × 80 layers × 8192 hidden × 2 bytes
                   = 2.6 MB / token

For a sequence of 4096 tokens: 10 GB KV cache.
For a batch of 32 sequences × 4096 tokens: 327 GB.
```

For an A100 (80 GB), 32 sequences don't fit. The traditional solution is to limit the batch size based on the maximum sequence length, but this wastes memory when sequences are shorter than the max.

## The Fragmentation Problem

Traditional KV cache allocation reserves contiguous memory for each request:

```text
Request 1: max_len = 2048 → reserve 5 GB at address 0x100000
Request 2: max_len = 1024 → reserve 2.5 GB at address 0x140000
Request 3: max_len = 4096 → reserve 10 GB at address 0x150000

If request 2 actually generates 100 tokens (uses 250 MB of its 2.5 GB):
  - 2.25 GB is wasted (internal fragmentation)
  - Cannot be reused by another request

If request 2 finishes early, the freed 2.5 GB must be contiguous for the next request — if the next request needs 3 GB, the 2.5 GB hole is useless (external fragmentation).
```

A 2023 study found that ~80% of GPU memory was wasted on internal+external fragmentation in traditional KV cache allocation, limiting the actual concurrency to ~20% of the theoretical max.

## Paged Attention's Approach

Borrowing from OS virtual memory, Paged Attention divides the KV cache into fixed-size blocks (pages):

```text
Block size: 16 tokens × KV_size_per_token = 16 × 2.6 MB = 41 MB per block (for 70B model)

Each request's KV cache is a list of block pointers:
  Request 1: [block_0, block_5, block_7]   ← 3 blocks × 16 tokens = 48 tokens so far
  Request 2: [block_3, block_2]             ← 2 blocks × 16 tokens = 32 tokens
  Request 3: [block_1, block_4, block_6, block_8]
```

Blocks are allocated from a global free list. When a request generates a new token that doesn't fit in its current block, a new block is allocated. When a request finishes, its blocks are returned to the free list.

The mapping from logical (per-request) to physical (per-block) is maintained in a "block table" per request, similar to the page table in OS virtual memory:

```text
Request 1's block table: [0, 5, 7]
Request 2's block table: [3, 2]

When request 1 generates token #49 (block 4):
  It needs attention to tokens 0-48.
  Logical block 0 (tokens 0-15) is physical block 0.
  Logical block 1 (tokens 16-31) is physical block 5.
  Logical block 2 (tokens 32-47) is physical block 7.
  Logical block 3 (token 48 only so far) needs allocation: physical block 9.
```

The attention kernel (PagedAttention kernel) reads the block table and accesses the right blocks:

```cuda
// Pseudocode for paged attention kernel
__global__ void paged_attention(
    float* output,        // [seq_len, hidden]
    float* kv_cache,      // [num_blocks, block_size, hidden]
    int* block_table,     // [num_requests, max_blocks]
    int request_id,
    int seq_len_so_far
) {
    int q_idx = blockIdx.x;
    int head_idx = blockIdx.y;
    
    float acc[hidden] = {0};
    float max_score = -INF;
    float sum_exp = 0;
    
    for (int logical_block = 0; logical_block < (seq_len_so_far + 1) / BLOCK_SIZE; logical_block++) {
        int physical_block = block_table[request_id * MAX_BLOCKS + logical_block];
        for (int in_block = 0; in_block < BLOCK_SIZE; in_block++) {
            int k_idx = logical_block * BLOCK_SIZE + in_block;
            if (k_idx > seq_len_so_far) break;
            
            float score = dot(query[q_idx], kv_cache[physical_block, in_block, head_idx]);
            max_score = max(max_score, score);
            // accumulate softmax...
        }
    }
    
    output[q_idx] = ... // final softmax * V
}
```

The kernel's overhead vs. standard attention is ~5% (one extra indirection per block access). The gain from no fragmentation is 2-4× more concurrent requests, dwarfing the kernel overhead.

## Benefits

1. **No internal fragmentation.** A request that generates 100 tokens uses 7 blocks (112 tokens' worth); only 12 tokens are wasted. With block size 16, internal fragmentation is at most 15 tokens per request.

2. **No external fragmentation.** Blocks are interchangeable; any free block serves any request.

3. **Sharing via copy-on-write.** Beam search, parallel sampling, and other multi-branch generation can share KV cache for the common prefix. Only divergent tokens get new blocks; shared prefixes point to the same physical blocks.

```text
Beam search with 4 beams:
  Prefix "The capital of France is" → 5 tokens → 1 block, shared by all 4 beams.
  Beam 1 continues: " Paris" → new block.
  Beam 2 continues: " Lyon" → new block.
  Beam 3 continues: " Marseille" → new block.
  Beam 4 continues: " a country" → new block.

Without sharing: 4 beams × 6 tokens = 24 tokens = 2 blocks of KV cache.
With shared prefix: 1 block (prefix) + 4 small blocks = 5 blocks. But each "small block" is partial, so 1 + 4 = 5 blocks (vs 8 blocks without sharing).
```

The shared block is marked read-only; if any beam wants to write to it (rare, but happens for some decoding algorithms), copy-on-write allocates a new block and copies the contents.

## Memory Savings

For a 70B model serving a mix of requests (some 100-token generations, some 4000-token generations), traditional allocation reserves max_len × KV_size_per_token per request. Paged attention reserves actual_len × KV_size_per_token + O(block_size).

| Workload | Traditional | Paged | Savings |
|----------|-------------:|------:|--------:|
| 32 reqs × 100 tokens | 32 × 100 × 2.6 MB = 8 GB allocated; 8 GB used | Same | 0% |
| 32 reqs × 100 tokens (max_len=4096) | 32 × 4096 × 2.6 MB = 327 GB allocated; 8 GB used | 8 GB | 40× |
| 8 reqs × 4096 tokens (max_len=4096) | 8 × 4096 × 2.6 MB = 82 GB (doesn't fit) | 82 GB (fits if A100 80GB+oversubscribe) | n/a |

The big win is the second case: requests with short actual lengths but high max_len (the common case for chatbots, where users may type 4000 tokens but typically get 200 back).

## vLLM: The Reference Implementation

vLLM is the open-source implementation of paged attention, written in Python + CUDA. Key components:

- **Scheduler**: chooses which requests to admit based on KV cache availability.
- **Block manager**: maintains the free list and per-request block tables.
- **PagedAttention CUDA kernel**: the optimized attention kernel.
- **Continuous batching**: dynamically adds new requests to the batch when others complete, keeping the GPU at full utilization.

vLLM's published throughput numbers on Llama-2 70B with batch 256:
- Traditional (Hugging Face `transformers`): 25 tokens/sec/GPU
- vLLM with paged attention: 2300 tokens/sec/GPU (90× improvement)

The 90× improvement comes mostly from continuous batching (running 256 concurrent requests instead of 1) but paged attention enables the high concurrency by managing memory efficiently.

## Production Impact

Paged Attention has become the standard for LLM inference. The major serving frameworks all implement it:

- **vLLM**: the original, optimized for throughput.
- **SGLang**: vLLM fork with additional features (RadixAttention for prefix caching).
- **TensorRT-LLM**: NVIDIA's implementation, optimized for H100's TMA.
- **Text-Generation-Inference (TGI)**: Hugging Face's serving framework, uses paged attention since 1.0.
- **LMDeploy**: Chinese open-source serving framework.
- **DeepSpeed-FastGen**: Microsoft's serving framework.

For training, paged attention is less common — training workloads have known sequence lengths (so fragmentation is less of an issue), and the kernel overhead is less justified. PyTorch 2.x has experimental support for paged attention in training.

## Common Pitfalls

1. **Setting the block size too small.** Small blocks (e.g., 4 tokens) cause many block-table lookups per attention computation, slowing the kernel. Use 16 (the vLLM default) or 32.

2. **Setting the block size too large.** Large blocks (e.g., 256 tokens) waste memory on internal fragmentation for short requests. Use 16-32.

3. **Forgetting that block size affects kernel throughput.** The PagedAttention kernel's performance depends on the block size matching the warp size (32 for NVIDIA). Block size = 16 = half-warp, OK; block size = 32 = full warp, optimal.

4. **Not pre-allocating enough blocks.** If the block pool is too small, the scheduler rejects requests that could have fit. Pre-allocate based on `total_GPU_memory - model_size - activations`.

5. **Forgetting to enable continuous batching.** Paged attention alone gives ~2× throughput; combined with continuous batching, it gives 50-100×. Both must be enabled.

6. **Forgetting that paged attention breaks some attention optimizations.** Flash Attention expects a contiguous KV cache. Paged Attention's blocks are non-contiguous (in general), so Flash cannot be directly applied. vLLM has a custom PagedAttention kernel that does what Flash would do, but block-aware.

## References

- Kwon et al., "[Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180)" (SOSP 2023)
- [vLLM: source code](https://github.com/vllm-project/vllm)
- [vLLM blog: PagedAttention](https://blog.vllm.ai/2023/06/20/vllm.html)
- [SGLang: RadixAttention for prefix caching](https://github.com/sgl-project/sglang)
- [TensorRT-LLM: paged attention for H100](https://github.com/NVIDIA/TensorRT-LLM)
- [Hugging Face TGI: paged attention integration](https://github.com/huggingface/text-generation-inference)
- [LWN: How vLLM's paged attention works (2023)](https://lwn.net/Articles/936632/)
