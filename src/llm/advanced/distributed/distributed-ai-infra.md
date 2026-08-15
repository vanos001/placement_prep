# Distributed AI Infrastructure

## Distributed Agent Execution

Running hundreds or thousands of LLM-based agents concurrently requires treating agent lifecycles as first-class distributed systems primitives. Each agent is a stateful computation that may span multiple LLM calls, tool invocations, and human interactions over minutes or hours.

**Core challenges** include coordinating agent lifecycles, managing intermediate state, handling partial failures, and preventing resource starvation when many agents compete for limited GPU capacity. Systems like LangGraph, CrewAI, and AutoGen provide programming models for multi-agent coordination, but production deployments require additional infrastructure for durability and scalability.

A typical distributed agent runtime maintains an event-sourced log of agent actions. Each agent step is appended as an event, enabling replay after failures. The runtime orchestrates LLM calls through a shared inference gateway that handles rate limiting, model routing, and token budget management across all active agents.

```
┌─────────────────────────────────────────────┐
│              Agent Orchestrator              │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐          │
│  │Agent│ │Agent│ │Agent│ │Agent│  ...1000s │
│  │  A  │ │  B  │ │  C  │ │  D  │          │
│  └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘          │
│     └───────┴───────┼───────┘              │
│                     ▼                       │
│           Inference Gateway                  │
│          (rate limit, route)                │
│           ┌──────────────┐                  │
│           │ GPU Pool     │                  │
│           │ [H100][A100] │                  │
│           └──────────────┘                  │
└─────────────────────────────────────────────┘
```

### Agent State Replication

Agent state — conversation history, tool results, planning context — must survive process crashes. Three common approaches exist:

1. **Event sourcing to durable storage**: Every action is an immutable event appended to a log (Kafka, database). Recovery replays the log. This provides full auditability but higher read latency.
2. **Checkpoint snapshots**: Periodic snapshots of full agent state written to object storage (S3). Faster recovery but potential data loss between checkpoints.
3. **Stateful streams**: Using systems like Flink or Temporal to maintain agent state as stream state, with exactly-once processing guarantees.

In practice, production systems combine event sourcing for audit trails with periodic snapshots for fast recovery. The choice depends on your RTO (Recovery Time Objective) — how quickly must an agent resume after failure?

> **Interview Angle**: "Design a system that runs 10,000 autonomous research agents simultaneously, each running for hours. How do you handle failures?" The key insight is that agents are long-running, stateful workflows, not stateless requests.

### Checkpointing and Failover

Checkpointing in AI workloads serves two distinct purposes: **training checkpoints** (saving model weights + optimizer state, typically 10s–100s of GB) and **agent/serving checkpoints** (saving inference state, typically KB–MB).

For training, checkpoints are written every N steps to distributed storage. Modern frameworks like DeepSpeed use asynchronous checkpointing where a background thread uploads the checkpoint while training continues, avoiding pipeline stalls. Checkpoint frequency is a trade-off: more frequent checkpoints reduce wasted work on failure but increase I/O overhead.

For agent failover, the system must atomically persist the agent's conversation context, tool execution state, and any in-flight LLM requests. Temporal workflows handle this naturally — each workflow step is durably recorded, and the workflow resumes from the last completed step after a worker crash.

```
Checkpoint Decision Tree:
  Is the workload stateful?
  ├── YES → Long-running (hours)?
  │          ├── YES → Event sourcing + periodic snapshots
  │          └── NO  → In-memory state with request-level retry
  └── NO  → Stateless retry is sufficient
```

## GPU-Aware Scheduling

### AI Workload Scheduling

Traditional cluster schedulers (Kubernetes default scheduler, YARN) treat all resources as homogeneous. AI workloads are fundamentally different: a single training job may need 256 GPUs with specific interconnect topology, while an inference job needs 1 GPU with high memory bandwidth. Schedulers must be GPU-aware.

**Key scheduling dimensions for AI workloads:**

| Dimension | Training | Inference | Fine-tuning |
|-----------|----------|-----------|-------------|
| GPU count | 8–16,384 | 1–8 | 1–64 |
| GPU memory | High (model + grads) | Medium (model + KV) | Medium-High |
| Network | Critical (all-reduce) | Low (request/response) | Moderate |
| Tolerance to preemption | Low (checkpoint cost) | High (stateless) | Medium |
| Job duration | Hours–weeks | Milliseconds–seconds | Minutes–hours |

### GPU Cluster Topology and Network Topology

Modern GPU clusters have a hierarchical network topology that critically affects training performance. Understanding this topology is essential for both scheduling and performance debugging.

```
               ┌─────────────────────┐
               │    InfiniBand Fabric  │
               │    (spine-leaf)       │
               └───┬───────┬───────┬───┘
           ┌───────┘   ┌───┘   └───────┐
           ▼           ▼               ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  Rack 1  │ │  Rack 2  │ │  Rack 3  │
     │ NVLink   │ │ NVLink   │ │ NVLink   │
     │ domain   │ │ domain   │ │ domain   │
     │ 8x GPU   │ │ 8x GPU   │ │ 8x GPU   │
     └──────────┘ └──────────┘ └──────────┘

Bandwidth hierarchy:
  NVLink (900 GB/s) >> NVSwitch (same rack)
  > InfiniBand intra-rack (400 Gbps)
  > InfiniBand inter-rack (400 Gbps, more hops)
```

**NVLink domains** connect 4–8 GPUs within a single node with 300–900 GB/s bidirectional bandwidth. **NVSwitch** extends this to full bisection bandwidth within the domain. **InfiniBand** (or RoCE) connects nodes, but with significantly lower bandwidth and higher latency than NVLink. This hierarchy means that cross-node communication is 10–100x more expensive than intra-node.

### NCCL Topology Optimization

NCCL (NVIDIA Collective Communications Library) is the backbone of distributed training communication. It implements all-reduce, all-gather, reduce-scatter, broadcast, and other collective operations. NCCL automatically discovers the GPU topology and selects an optimal communication pattern, but this auto-tuning isn't always sufficient.

**Topology-aware NCCL configuration** involves:
- Setting `NCCL_P2P_LEVEL=NVL` to prefer NVLink for peer-to-peer transfers
- Configuring `NCCL_SHM_DISABLE=0` for shared memory within a node
- Using `NCCL_SOCKET_IFNAME` to pin traffic to specific NICs
- Setting `NCCL_NET_GDR_LEVEL=5` to enable GPU-direct RDMA

In multi-tenant clusters, NCCL topology awareness must also account for network contention. If two training jobs share inter-rack links, their all-reduce operations compete, degrading both jobs. Production schedulers like Microsoft's Singularity use network topology awareness to pack training jobs within rack boundaries when possible.

> **Interview Angle**: "Your training job is 30% slower than expected on 256 GPUs. How would you diagnose whether it's a communication bottleneck?" Check NCCL statistics (bytes sent per operation, time per collective), use `nccl-tests` to benchmark, inspect GPU utilization with `nvidia-smi`, and check for cross-rack communication patterns.

### ML Cluster Scheduling

Dedicated ML cluster schedulers like **Slurm** (used at most supercomputing labs), **Kubernetes with GPU plugins** (used in cloud), and **internal schedulers** like Microsoft Singularity or Google's Borg address the unique needs of ML workloads:

- **Gang scheduling**: All GPUs for a job must be allocated simultaneously, or none. Partial allocation wastes resources because training cannot proceed with missing ranks.
- **Topology-aware placement**: Prefer placing GPU workers within the same NVLink domain or rack to minimize cross-rack traffic.
- **Preemption with checkpoint-resume**: Training jobs can be preempted (if a recent checkpoint exists) to make room for higher-priority inference workloads.
- **Elastic scaling**: Jobs like DeepSpeed's elastic training can dynamically adjust world size as GPUs come and go.

## Inference-Aware Scheduling and Model Placement

### Model Placement

Model placement decides which physical GPUs host which models. This is a bin-packing problem with GPU memory and compute constraints. A 70B parameter model in FP16 requires ~140 GB — it must be split across at least 2 A100-80GB GPUs using tensor parallelism, or quantized to fit on a single GPU.

**Placement strategies include:**

1. **Static placement**: Models assigned to fixed GPU sets at deployment time. Simple but inflexible. Used by most vLLM/TGI deployments.
2. **Dynamic placement**: Models loaded/unloaded based on demand. Requires fast model loading (mmap from SSD) and warm GPU memory pools.
3. **Multi-tenant placement**: Multiple models share GPUs using MIG (Multi-Instance GPU) or time-slicing. Reduces cost but adds latency variability.

### Parallel Serving

Serving a single model with high throughput requires parallelism across multiple dimensions:

- **Batching**: Grouping multiple requests into a single forward pass. Continuous batching (iteration-level scheduling) allows requests to enter/leave the batch at any token boundary.
- **Tensor parallelism**: Splitting model layers across GPUs for models too large for one GPU. Adds communication overhead per layer.
- **Pipeline parallelism**: Splitting the model into stages across GPUs. Improves throughput but adds bubble overhead.
- **Data parallelism**: Running multiple model replicas, each handling a subset of requests. Best for throughput at the cost of more GPUs.

```
Throughput vs. Latency Trade-off:

  Throughput ▲
              │        Data Parallelism
              │       ╱
              │      ╱  Pipeline Parallelism
              │     ╱   ╱
              │    ╱   ╱  Tensor Parallelism
              │   ╱   ╱  ╱
              │  ╱   ╱  ╱
              │ ╱   ╱  ╱  Single GPU
              └─────────────────────► Latency
```

> **Interview Angle**: "How would you serve a 70B model to 10,000 concurrent users with P99 latency < 2 seconds?" The answer combines continuous batching, tensor parallelism (2–4 GPUs per replica), data parallelism (multiple replicas behind a load balancer), KV cache management, and request queuing with priority queues.

## Federated LLM Training and Fine-Tuning

### Federated LLM Training

Federated training for LLMs adapts the classic federated learning paradigm to foundation models. Instead of training from scratch (which is impractical federated), the dominant approach is **federated fine-tuning**: each client (data owner) fine-tunes a pre-trained model on local data, then server-side aggregation merges the updates.

The key challenge is communication efficiency. LLM fine-tuning via LoRA produces small adapter weights (~10–100 MB) rather than full model updates (~140 GB for a 70B model). This makes federated fine-tuning practically feasible — clients upload only adapter deltas, not full gradients.

### Edge LLM Inference and On-Device Inference

Running LLMs on edge devices (phones, IoT, vehicles) requires extreme optimization:

- **Quantization**: 4-bit (GPTQ, AWQ) or 3-bit quantization is mandatory. A 7B model at 4-bit needs ~4 GB.
- **Knowledge distillation**: A smaller student model (1–3B parameters) is trained to mimic a larger teacher model's outputs on domain-specific data.
- **Speculative decoding**: A tiny draft model generates candidate tokens, verified in parallel by the main model. Effective on devices where compute is limited but memory is available.
- **KV cache compression**: Techniques like Heavy Hitter Oracle (H2O) evict less important KV cache entries, reducing memory pressure.

Real systems: Apple's on-device LLM (3B parameters) runs on iPhone 15 Pro using optimized Metal kernels. Qualcomm runs 7B models on Snapdragon X Elite laptops. llama.cpp provides a portable C++ inference engine supporting CPU, CUDA, Metal, and Vulkan backends.

### Accelerator-Aware Orchestration

Beyond GPUs, modern AI infrastructure must orchestrate diverse accelerators: TPUs (Google), HPUs (Intel Gaudi), NPUs (mobile), and custom ASICs. Each accelerator has different memory hierarchies, compute capabilities, and interconnects. Orchestrators like Kubernetes with device plugins or Ray provide abstraction layers, but optimal performance requires accelerator-specific tuning.

### AI Data Pipelines and Distributed Embedding Generation

Training and RAG systems require processing billions of documents into embeddings. Distributed embedding pipelines use map-reduce patterns: documents are partitioned across workers, each worker generates embeddings using a local model, and results are written to a vector database. The bottleneck is typically the embedding model inference throughput, not the vector DB write speed. Systems like ColBERT generate token-level embeddings (rather than single vector per document), increasing quality but also computational cost by 10–100x.

## Comparison Table: AI Infrastructure Systems

| System | Primary Use | GPU Awareness | Scaling Model | Topology Awareness |
|--------|-------------|---------------|---------------|-------------------|
| Kubernetes + Karpenter | General + AI | Basic (node-level) | Horizontal pod autoscaling | Label-based |
| Ray | AI/ML workloads | Per-task GPU | Autoscaling actor pool | Limited |
| Slurm | HPC training | Full (MIG, affinity) | Job arrays | Full (InfiniBand topology) |
| Microsoft Singularity | Internal AI | Full | Elastic scaling | Network + topology aware |
| Volcano (K8s) | Batch/AI on K8s | Queue-level GPU | Queue scheduling | Co-scheduling support |

## Key Takeaways

1. **AI scheduling is fundamentally different from web scheduling** — GPUs are expensive, communication-heavy, and topology-sensitive.
2. **Agent systems need durable state** — treat agents as long-running workflows, not stateless requests.
3. **Model placement is a constrained optimization** — bin-packing with memory, compute, and network constraints.
4. **Edge inference is about compression** — quantization, distillation, and KV cache management are non-negotiable.
5. **Federated fine-tuning is practical with LoRA** — adapter-based updates reduce communication by 1000x compared to full model updates.
