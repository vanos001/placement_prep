# Distributed Training Systems

## AI Networking and Collective Communication

Distributed training of large language models is fundamentally a **communication-bound problem**. While GPUs have doubled in compute every ~2 years (Moore's law for AI), interconnect bandwidth has grown much more slowly. This means that at large scale, GPUs spend more time communicating than computing.

**Collective communication operations** are the building blocks of distributed training:

| Operation | Description | Use Case | Complexity |
|-----------|-------------|----------|------------|
| **Broadcast** | Send data from rank 0 to all | Distribute initial weights, hyperparameters | O(n) |
| **All-Reduce** | Sum data across all ranks, distribute result | Gradient synchronization (data parallelism) | O(n log n) with tree | 
| **All-Gather** | Gather data from all ranks to all | Gathering sharded parameters (tensor parallelism) | O(n) |
| **Reduce-Scatter** | Reduce data, distribute partial results | Reverse of all-gather | O(n) |
| **All-to-All** | Each rank sends different data to each rank | Expert parallelism (MoE routing) | O(n²) |
| **Send/Recv** | Point-to-point | Pipeline stage communication | O(1) |

**All-reduce** is the most critical operation. For data-parallel training, every training step requires an all-reduce of gradient tensors. A 70B model has ~140 GB of gradients (FP32). Even at 400 Gbps InfiniBand, a single all-reduce of 140 GB takes ~3 seconds — and this happens every training step.

**All-reduce algorithms**:
- **Ring all-reduce**: Each GPU sends a chunk to its neighbor in a ring. O(n) bandwidth, O(n/p) latency. Works well when all GPUs are on equal-bandwidth links. Used by default in NCCL for intra-node communication.
- **Tree all-reduce**: Organize GPUs in a tree; reduce up the tree, broadcast down. O(log p) latency but higher bandwidth on root links. Better for cross-node communication where latency matters more.
- **Hierarchical all-reduce**: Combine ring (intra-node, NVLink) with tree (inter-node, InfiniBand). NCCL uses this by default for multi-node training.

```
Ring All-Reduce (4 GPUs, data split into 4 chunks):

Step 1: Reduce-Scatter              Step 2: All-Gather
GPU 0: [A0 B0 C0 D0]              GPU 0: [A+B+C+D, B0, C0, D0]
GPU 1: [A1 B1 C1 D1]              GPU 1: [A0, A+B+C+D, C1, D1]
GPU 2: [A2 B2 C2 D2]              GPU 2: [A0, B0, A+B+C+D, D2]
GPU 3: [A3 B3 C3 D3]              GPU 3: [A0, B0, C0, A+B+C+D]

Each step: p-1 rounds, each round sends 1 chunk to neighbor
```

## Congestion-Aware AI Training

In multi-tenant GPU clusters, multiple training jobs share the same network fabric. This creates **congestion hotspots** where inter-rack links are oversubscribed.

Consider two 64-GPU training jobs running simultaneously. Each job's all-reduce generates traffic between all GPU pairs. If both jobs use the same inter-rack links, their traffic competes, and both jobs slow down. This is the **incast problem** — multiple sources sending to the same destination (or through the same link) simultaneously.

**Solutions:**

1. **Topology-aware job placement**: The scheduler places each training job entirely within a rack (or set of racks) so that intra-job communication stays on NVLink/intra-rack links. Microsoft Singularity does this.

2. **Flow scheduling**: Network switches prioritize training traffic using ECN (Explicit Congestion Notification) and DCTCP (Datacenter TCP). Some systems use priority flow control (PFC) to pause lower-priority traffic during training collective operations.

3. **Adaptive communication**: Training frameworks detect congestion (via NCCL's built-in telemetry) and adapt: reduce batch size, increase gradient accumulation, or pause communication until congestion clears.

> **Interview Angle**: "Your training job runs at 60% GPU utilization on 512 GPUs, and nvidia-smi shows low compute. What's wrong?" This is almost certainly a communication bottleneck. Check NCCL's collective operation timing (`NCCL_DEBUG=INFO`), verify the GPUs are within the same NVLink domain where possible, and check for network congestion from co-located jobs.

## Topology-Aware Training

Given the hierarchical network (NVLink > intra-rack IB > inter-rack IB), training frameworks minimize cross-boundary communication:

**3D parallelism** (data + tensor + pipeline) is the dominant approach for models too large for a single GPU. The key insight is that different parallelism strategies generate different communication patterns:

- **Tensor parallelism**: Communicates every layer via all-reduce. Requires high bandwidth, low latency. Must be within an NVLink domain.
- **Pipeline parallelism**: Communicates once per micro-batch between stages. Can tolerate higher latency (inter-rack OK).
- **Data parallelism**: Communicates once per gradient accumulation step. Can tolerate the highest latency but largest data volume.

```
Optimal Parallelism Placement:

┌─────────────── Rack 1 ───────────────┐
│  Node 0         Node 1              │
│  [TP=8 GPUs]    [TP=8 GPUs]  ◄── TP │  (NVLink, 900 GB/s)
│       \            /                 │
│        PP Stage 0  PP Stage 1 ◄── PP │  (InfiniBand, 50 GB/s)
│                    /                 │
│  Node 2         Node 3              │
│  [TP=8 GPUs]    [TP=8 GPUs]         │
└──────────────────────────────────────┘
          \                    /
           \                  /
            \    DP All-Reduce   ◄── DP (cross-rack)
            /                  \
┌─────────────── Rack 2 ───────────────┐
│  (mirror of Rack 1)                  │
└──────────────────────────────────────┘
```

**Megatron-LM** from NVIDIA provides the canonical implementation of 3D parallelism with automatic topology-aware placement. It places tensor parallel groups within NVLink domains and pipeline stages across nodes within a rack, minimizing the most latency-sensitive communication.

## Fault-Tolerant Training

A 10,000-GPU training run might run for 3–6 weeks. With hardware MTBF (mean time between failures) of ~1 year per GPU, you expect ~200 GPU failures during the run. Without fault tolerance, a single failure kills the entire job.

**Checkpoint-restart** is the simplest approach: save model weights and optimizer state periodically, restart from the last checkpoint on failure. Drawbacks: (1) checkpoint I/O is expensive (minutes for large models), (2) you lose work done since the last checkpoint.

**More advanced approaches:**

- **Asynchronous checkpointing**: Write checkpoint in background while training continues. DeepSpeed supports this. The trade-off is that you need extra memory to hold the checkpoint buffer.

- **Elastic training (DeepSpeed Elastic, TorchElastic)**: The job can survive node failures without restart. When a node fails, the remaining nodes detect it, reshape the data-parallel groups, and continue training with a smaller world size. When replacement nodes come online, the world size grows. This requires that the model can handle variable batch sizes and that the optimizer can adjust to changing world sizes.

- **Selective checkpointing**: Instead of checkpointing the full model, checkpoint only the optimizer state and a small subset of parameters. Combine with gradient accumulation to avoid recomputation.

## Asynchronous and Decentralized Training

### Asynchronous SGD
In synchronous data-parallel training (the standard), all workers compute gradients, then synchronize via all-reduce. The slowest worker determines the step time — this is the **straggler problem**.

Asynchronous SGD removes the synchronization barrier: each worker computes gradients on stale parameters, applies updates immediately, and continues. This eliminates the straggler but introduces **stale gradient** noise, which can slow convergence or cause divergence.

In practice, pure async SGD doesn't work well for LLM training because the staleness tolerance is too low. Variants like **bounded staleness** (wait for at most K stragglers) or **stale synchronous parallelism** (SSP) provide better trade-offs.

### Decentralized (Gossip) Training
Instead of a centralized all-reduce (which requires all-to-all communication), gossip training has each worker communicate with only a few randomly chosen peers each step. Gradients propagate through the network like gossip — eventually reaching all workers.

**Gossip training properties:**
- Communication per step: O(1) instead of O(n) for all-reduce.
- Convergence: Slower by a constant factor, but communication cost is dramatically lower.
- Topology: Works on arbitrary network topologies, including peer-to-peer networks.

Gossip training is attractive for edge/federated scenarios with limited or unreliable connectivity, but the slower convergence makes it impractical for large-scale LLM pretraining where compute cost dominates.

## Federated Learning Systems

Federated learning (FL) enables training on distributed, private datasets without moving data to a central server. Each participant (client) trains locally on its data and sends model updates to a central server, which aggregates updates into a global model.

### Federated Learning Architecture

```
┌─────────────────────────────────────────────┐
│              Aggregation Server              │
│  Global Model θ_t                           │
│         │                                    │
│    Aggregation (FedAvg, FedProx, etc.)       │
│         │                                    │
│    ┌────┼────┐                               │
│    ▼    ▼    ▼                               │
│  θ_1  θ_2  θ_3  (client updates)           │
└────┬────┬────┬─────────────────────────────┘
     │    │    │
     ▼    ▼    ▼
┌────────┐┌────────┐┌────────┐
│Client 1││Client 2││Client 3│
│Hospital││Bank    ││Phone   │
│(GPU)   ││(GPU)   ││(CPU)   │
│D_1     ││D_2     ││D_3     │
└────────┘└────────┘└────────┘
```

### FedAvg and Beyond

**FedAvg** (McMahan et al., 2017) is the foundational FL algorithm: (1) server sends global model to K clients, (2) each client trains for E local epochs, (3) clients send updated weights to server, (4) server averages weights (weighted by dataset size).

**FedAvg limitations:**
- Non-IID data across clients causes convergence issues — client updates may point in conflicting directions.
- Heterogeneous compute (some clients have GPUs, others CPU) creates stragglers.
- Communication cost is high for large models (sending full model updates).

**Modern FL algorithms address these:**

| Algorithm | Key Innovation | Best For |
-----------|---------------|----------|
| **FedProx** | Adds proximal term to local objective to limit divergence from global model | Non-IID data |
| **SCAFFOLD** | Controls client drift with variance reduction | Highly non-IID data |
| **FedNova** | Normalizes local updates by number of local steps | Heterogeneous compute |
| **FedAdam** | Server-side Adam optimizer instead of simple averaging | Faster convergence |
| **FedPer** | Personalize final layers per client | Personalized models |

### Privacy-Preserving Federated Learning

The core promise of FL is privacy — data never leaves the client. However, model updates can leak information about training data through **gradient inversion attacks**. Defenses include:

1. **Differential privacy (DP-SGD)**: Clip individual gradients and add Gaussian noise before sending. Provides mathematical privacy guarantees (ε-delta). Trade-off: privacy budget (ε) vs. model quality. Apple and Google use DP in production FL systems.

2. **Secure aggregation**: The server can compute the sum of client updates without seeing individual updates. This uses cryptographic protocols (secret sharing, homomorphic encryption). Google's production FL system uses secure aggregation.

3. **Trusted execution environments (TEEs)**: Client-side training runs in a hardware-isolated enclave (SGX, TrustZone). The server can verify the training code but cannot inspect the data.

### Byzantine-Robust Aggregation

In adversarial settings (or with faulty clients), some clients may send malicious or corrupted updates. Byzantine-robust aggregation algorithms detect and mitigate these:

- **Krum**: Selects the single update closest to the majority. Robust to up to (n-3)/2 Byzantine clients.
- **Trimmed mean**: Remove the top and bottom K% of updates by each coordinate's value, then average the rest. Simple and effective.
- **Median**: Use coordinate-wise median instead of mean. More robust but slower convergence.
- **Bulyan**: Combines Krum selection with trimmed mean. Among the most robust known aggregators.

### Split Learning and Swarm Learning

**Split learning** partitions the model between client and server: the client computes the first few layers, sends intermediate activations (not gradients) to the server, which computes the remaining layers and backpropagates. The server never sees raw data or the client's full model.

**Swarm learning** (Hewlett Packard Enterprise) removes the central server entirely. Clients communicate peer-to-peer using a blockchain for coordination and model update aggregation. This provides both privacy (no central party) and fault tolerance (no single point of failure).

### Edge and Heterogeneous Federated Learning

Edge FL deploys on resource-constrained devices (phones, IoT sensors, vehicles):

- **Continual FL**: The global model evolves continuously as new data arrives, without forgetting previous knowledge. Combines FL with continual learning techniques (EWC, replay buffers).
- **Heterogeneous FL**: Devices have vastly different compute (phone vs. server), memory (2GB vs. 128GB), and connectivity (4G vs. fiber). Systems like FedDyn and FedSplit adapt the amount of computation per client.
- **Federated analytics**: Sometimes you don't need a trained model — you just need aggregate statistics (mean, median, count) across private datasets. Secure multi-party computation (SMPC) protocols can compute these without revealing individual data points.

> **Interview Angle**: "How would you train a model on data from 100 hospitals without any hospital sharing patient data?" Federated learning with LoRA fine-tuning (to reduce communication cost), secure aggregation (to prevent the server from seeing individual hospital updates), and differential privacy (to prevent gradient inversion). Use FedProx to handle non-IID distributions across hospitals.

## Key Takeaways

1. **Communication, not compute, is the bottleneck** at large scale — understanding all-reduce and its costs is essential.
2. **3D parallelism placement matters** — tensor parallelism must stay within NVLink domains; data parallelism can span racks.
3. **Fault tolerance is non-negotiable** for long training runs — expect ~200 GPU failures in a 10K-GPU, 4-week run.
4. **Federated learning is production-ready** for fine-tuning but impractical for pretraining — communication cost and convergence challenges remain.
5. **Byzantine robustness and differential privacy are table stakes** for production FL deployments handling sensitive data.
6. **Asynchronous and gossip training** reduce communication cost at the expense of convergence — useful in edge settings but not for large-scale pretraining.
