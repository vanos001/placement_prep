# Disaggregated Inference Architecture

## The Case for Disaggregation

Traditional LLM serving co-locates all inference components on the same GPU(s): tokenization, embedding lookup, transformer layers (prefill + decode), and sampling. This monolithic approach works for small models but creates severe inefficiencies at scale because **prefill and decode have fundamentally different compute and memory profiles**.

**Prefill** (processing the prompt) is compute-bound: it processes all input tokens in parallel through the transformer layers. A 4K-token prompt on a 70B model uses ~4K × 70B FLOPs — massive compute, but the operation is parallelized across all input tokens.

**Decode** (generating output tokens) is memory-bandwidth-bound: each new token requires reading the entire KV cache (one row per layer, per attention head) and the model weights. The compute per token is small (one token through all layers), but the memory reads dominate.

This asymmetry means that a GPU optimized for prefill (high compute throughput) is underutilized during decode, and a GPU optimized for decode (high memory bandwidth) is underutilized during prefill. Disaggregating these phases allows independent scaling.

| Phase | Compute Bound? | Memory Bound? | Parallelism | Typical Duration |
|-------|---------------|---------------|-------------|-----------------|
| Prefill | Yes (matrix-matrix) | Moderate | High (token-parallel) | 50–500ms |
| Decode | No (matrix-vector) | Yes (KV cache reads) | Low (sequential) | 10–100ms per token |

> **Interview Angle**: "Why does a single GPU run prefill and decode inefficiently?" Prefill wants high compute (FLOPS) for parallel token processing. Decode wants high memory bandwidth for KV cache reads. A GPU has fixed ratios of compute to bandwidth, so it's optimized for neither phase exclusively.

## Prefill/Decode Disaggregation

Disaggregated prefill-decode splits the inference serving into two separate clusters of GPUs:

```
Traditional (Co-located):        Disaggregated:
┌────────────────────┐         ┌──────────────┐  ┌──────────────┐
│ GPU: Prefill+Decode│         │ Prefill GPU  │  │ Decode GPU   │
│                    │         │ (compute-    │  │ (memory-bw   │
│ [prompt][token1..] │         │  optimized)  │  │  optimized)  │
└────────────────────┘         │              │  │              │
                               │ Process 4K   │  │ Generate     │
  GPU idle during decode?       │ tokens in    │  │ tokens one   │
  GPU underutilized prefill?   │ parallel     │  │ at a time    │
                               └──────┬───────┘  └──────┬───────┘
                                      │    KV cache      │
                                      └──────────────────┘
```

**How it works:**
1. A request arrives at the **prefill cluster**. A prefill GPU processes all prompt tokens in parallel, computing the initial KV cache.
2. The KV cache is **transferred** to a GPU in the decode cluster. This transfer is the critical path — it must be fast (RDMA) and the decode GPU must have sufficient memory to receive it.
3. The **decode cluster** generates tokens one at a time, reading the KV cache from local GPU memory. The decode GPU sends each generated token back to the client.

**Benefits:**
- Prefill GPUs can use lower-memory, higher-compute chips (e.g., H100 with 80GB is fine — prefill doesn't need huge KV cache storage).
- Decode GPUs can be provisioned purely for memory bandwidth (e.g., H200 with 141GB HBM3e).
- Independent autoscaling: scale prefill capacity based on prompt length distribution, decode capacity based on output length distribution.

**Challenges:**
- KV cache transfer latency adds to time-to-first-token (TTFT). With RDMA, a 4K-context KV cache for a 70B model is ~2–4 GB, transferable in ~1–2ms over 400Gbps InfiniBand.
- Load balancing between prefill and decode clusters is non-trivial — the optimal ratio depends on workload characteristics.

**Real systems**: Splitwise (SOSP '24), DistServe (MLSys '24), and Microsoft's production systems implement variants of this architecture. vLLM is adding experimental support.

## KV Cache Disaggregation and Remote KV Cache

As context windows grow (100K, 1M, even 10M tokens), the KV cache becomes the dominant memory consumer. A 1M-token context for a 70B model at FP16 requires approximately 2 TB of KV cache storage — far exceeding any single GPU's memory.

**KV cache disaggregation** separates KV cache storage from the compute GPUs:

```
Compute GPU                    Memory GPU (KV Cache Store)
┌──────────────┐    RDMA/CXL   ┌──────────────────────┐
│ Model Weights │◄────────────►│  KV Cache Layer 0    │
│ (frozen)      │              │  KV Cache Layer 1    │
│               │              │  ...                  │
│ Attention     │  Read KV     │  KV Cache Layer N    │
│ Compute       │  rows via    │                      │
│               │  RDMA        │  (SSD-backed if      │
└──────────────┘              │   exceeds GPU mem)   │
                              └──────────────────────┘
```

**Two sub-approaches exist:**

1. **GPU-backed remote KV cache**: KV cache stored in GPU memory on separate "memory nodes." Accessed via GPU-direct RDMA (GPUDirect RDMA), bypassing CPU memory. Latency: ~1–5μs per access. Used by systems like Splitwise and Mooncake (ByteDance).

2. **SSD/CPU-backed KV cache**: KV cache overflows from GPU memory to CPU RAM, then to SSD. Accessed via PCIe. Latency: ~10–100μs (CPU RAM) or ~100μs–1ms (SSD). Used by systems like vLLM's prefix caching overflow and CacheGen.

**The attention computation with remote KV cache** becomes an I/O-bound operation. Instead of loading the full KV cache into GPU memory, the system loads only the KV rows needed for the current attention computation (a sliding window or paged attention approach). This is analogous to virtual memory paging — the GPU's HBM acts as a cache for the remote KV store.

> **Interview Angle**: "How would you serve a 1M-token context window on GPUs with only 80GB memory?" Use KV cache disaggregation: store KV cache on remote memory nodes, stream required KV pages via RDMA on demand. Use paged attention to manage cache pages. Prefetch upcoming pages based on attention patterns. This is essentially GPU virtual memory for the KV cache.

## GPU Memory Disaggregation

Beyond KV caches, GPU memory disaggregation generalizes the concept: allow GPUs to access memory that is physically located on other GPUs or on CPU memory nodes. This is enabled by:

- **NVLink/NVSwitch**: GPUs within a node can access each other's memory with ~900 GB/s bandwidth. This is fast enough for direct model weight access but still 2–3x slower than local HBM.
- **RDMA (GPUDirect RDMA)**: GPUs can DMA to/from remote memory (CPU or GPU) over InfiniBand or RoCE, bypassing the CPU. Bandwidth: 200–400 Gbps (~25–50 GB/s). Suitable for streaming KV cache pages.
- **CXL (Compute Express Link)**: A new interconnect standard allowing cache-coherent shared memory between CPUs, GPUs, and other accelerators. Bandwidth: 32–64 GB/s (CXL 3.0). Lower bandwidth than RDMA but provides cache coherence, simplifying programming.

## Inference over RDMA

RDMA (Remote Direct Memory Access) enables a GPU on one machine to read/write memory on another machine without involving the remote CPU. This is critical for disaggregated inference because it eliminates CPU overhead from the critical path.

**GPUDirect RDMA** (NVIDIA) extends RDMA to allow the GPU NIC to directly read/write GPU HBM:

```
Without GPUDirect RDMA:           With GPUDirect RDMA:
GPU A → CPU A → NIC A            GPU A → NIC A ───────────→ NIC B → GPU B
         (copy 1)                                                (copy 1)
         NIC A → ... → NIC B                                       
         (network)                                                
         NIC B → CPU B                                            
         (copy 2)                                                
         CPU B → GPU B                                            
         (copy 3)                                                

Latency: ~10–50μs                Latency: ~1–5μs
CPU utilization: high             CPU utilization: ~0%
```

**RDMA verbs used in inference:**
- **RDMA Write**: Push KV cache from prefill GPU to decode GPU's memory. Used for KV cache transfer after prefill.
- **RDMA Read**: Decode GPU pulls KV cache pages from remote memory store. Used during attention computation with remote KV cache.
- **RDMA Send/Recv**: Used for control messages (request dispatch, completion notification) between components.

**Production considerations:**
- RDMA requires InfiniBand or RoCE (RDMA over Converged Ethernet) networking, which adds ~$5–15K per server.
- Network congestion on RDMA networks is particularly damaging because RDMA has no software-level backpressure — the NIC hardware handles flow control. Congestion-aware routing and ECN (Explicit Congestion Notification) are essential.
- RDMA connection management is complex. Libraries like libfabric and UCX (Unified Communication X) provide abstractions, but production deployments still require careful tuning.

## Inference over CXL

CXL (Compute Express Link) is a PCIe-based interconnect that provides cache-coherent memory sharing between devices. For inference, CXL enables:

1. **Memory expansion**: GPUs can access CPU RAM as if it were local memory, with cache coherence handled by the CXL fabric. A GPU with 80GB HBM could transparently use 256GB of CPU RAM for KV cache overflow.

2. **Memory pooling**: Multiple GPUs share a pool of CXL-attached memory. This avoids over-provisioning each GPU's local memory.

3. **Accelerator disaggregation**: A CXL-attached accelerator (e.g., a dedicated attention computation chip) can directly access the GPU's memory without data copies.

**CXL vs. RDMA for inference:**

| Property | RDMA | CXL |
|----------|------|-----|
| Bandwidth | 25–50 GB/s (per NIC) | 32–64 GB/s (CXL 3.0) |
| Latency | 1–5 μs | 0.5–2 μs |
| Cache coherence | No (manual invalidation) | Yes (hardware-managed) |
| Programming model | Explicit send/recv | Load/store (transparent) |
| Availability | Production (IB/RoCE) | Early (CXL 2.0), limited |
| Distance | Rack-scale (100m) | Server/node-scale (1–2m) |

CXL's key advantage is **transparency** — the GPU can access remote memory using normal load/store instructions, as if it were local. This dramatically simplifies software. However, CXL's distance limitation (currently ~2m with retimers) means it's suitable for within-node or adjacent-node disaggregation, not cross-rack.

> **Interview Angle**: "When would you use RDMA vs. CXL for disaggregated inference?" Use RDMA for cross-rack disaggregation (different servers, 100m range) where bandwidth and distance matter more than coherence. Use CXL for within-node or adjacent-node memory expansion where cache coherence and programming simplicity are more valuable.

## Designing a Disaggregated Serving System

Putting it all together, a production disaggregated serving system looks like:

```
                    ┌─────────────────────────────────────┐
                    │           Load Balancer              │
                    └──────────┬──────────────────────────┘
                               │
                    ┌──────────▼──────────────────────────┐
                    │        Request Router                │
                    │  (cache check, model selection,      │
                    │   routing to prefill cluster)        │
                    └──────────┬──────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │ Prefill GPU │     │ Prefill GPU │     │ Prefill GPU │
   │ (H100, 80GB)│     │ (H100, 80GB)│     │ (H100, 80GB)│
   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
          │                   │                   │
          └───────────┬───────┴───────────┬───────┘
                      │  KV Cache Transfer│
                      │  (RDMA, ~1–2ms)   │
                      ▼                   ▼
   ┌─────────────────────────────────────────────────────┐
   │              Decode Cluster (H200, 141GB)            │
   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
   │  │ Decode  │ │ Decode  │ │ Decode  │ │ Decode  │   │
   │  │ GPU 1   │ │ GPU 2   │ │ GPU 3   │ │ GPU 4   │   │
   │  │ + KV    │ │ + KV    │ │ + KV    │ │ + KV    │   │
   │  │ Cache   │ │ Cache   │ │ Cache   │ │ Cache   │   │
   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
   └─────────────────────────────────────────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────────────────────┐
   │         Remote KV Cache Store (Memory Nodes)         │
   │  (for contexts > decode GPU memory capacity)         │
   └─────────────────────────────────────────────────────┘
```

## Key Takeaways

1. **Prefill is compute-bound, decode is memory-bound** — this fundamental asymmetry drives disaggregation.
2. **KV cache is the bottleneck** — it grows linearly with context length and quadratically with model size. Disaggregating it enables arbitrarily long contexts.
3. **RDMA is production-ready for disaggregation** — GPUDirect RDMA provides ~1–5μs latency with zero CPU overhead.
4. **CXL is the future for memory expansion** — cache-coherent, transparent access, but limited to within-node/adjacent-node today.
5. **Disaggregation adds network latency** — the KV cache transfer must be fast enough that TTFT (time-to-first-token) remains acceptable. RDMA at 400Gbps keeps this under 5ms for typical workloads.
6. **Autoscaling becomes more nuanced** — you independently scale prefill and decode capacity based on their respective utilization patterns.
