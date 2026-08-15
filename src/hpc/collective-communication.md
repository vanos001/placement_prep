# Collective Communication & Distributed Training Patterns

## All-Reduce: The Fundamental Collective

All-reduce combines (reduces) a value from every participant and distributes the result to all. In distributed deep learning, this is the **most frequent collective** — every training step requires averaging gradients across all workers. The data volume makes all-reduce the network bottleneck.

### Ring All-Reduce

The ring algorithm is the workhorse for medium-scale all-reduce (used by NCCL, MPI, Horovod, PyTorch DDP):

```
4-GPU Ring All-Reduce (data split into 4 chunks: A B C D)

Reduce-Scatter Phase (N-1 steps):
Step 1: GPU0→GPU1→GPU2→GPU3  (A circulates, partial sums accumulate)
Step 2: GPU0←GPU1←GPU2←GPU3  (B circulates)
Step 3: GPU0→GPU1→GPU2→GPU3  (C circulates)
Result: Each GPU holds one fully-reduced chunk.

All-Gather Phase (N-1 steps):
Step 4: Full chunks broadcast around ring
Result: Every GPU has the complete reduced array.
```

**Cost analysis**: For N GPUs, data size D, bandwidth B per link:
- **Ring**: 2 × (N-1)/N × D/B ≈ 2D/B messages. Bandwidth-bound: each GPU sends/receives 2×(N-1)/N of the data.
- **Naive**: Root collects all (N×D/B) then broadcasts (N×D/B) = 2ND/B — N× worse.

Ring all-reduce is optimal in the bandwidth-bound regime: the lower bound for any all-reduce algorithm is 2(N-1)/N × D/B. The ring algorithm achieves this bound.

### Tree All-Reduce

For large messages or when latency matters more:

```
        Root (GPU0)
       /    \
    GPU1    GPU2
    /  \    /  \
  GPU3 GPU4 GPU5 GPU6

Reduce phase: leaves → root (log N steps, latency-bound)
Broadcast phase: root → leaves (log N steps)
```

Tree all-reduce has latency cost O(log N × α) where α is the network latency, but bandwidth cost depends on the tree degree. A binary tree has the same bandwidth cost as ring for balanced data. NCCL often uses a **tree with higher fanout** (e.g., degree 4) for the large-message path, reducing the number of hops.

### Hierarchical All-Reduce

In multi-node GPU clusters, a **two-level hierarchy** exploits the bandwidth asymmetry between intra-node (NVLink, ~900 GB/s) and inter-node (InfiniBand/RoCE, ~50 GB/s):

```
Node 0:                Node 1:                Node 2:
[GPU0 GPU1 GPU2 GPU3]  [GPU4 GPU5 GPU6 GPU7]  [GPU8 GPU9 GPU10 GPU11]
     \      |      /         \      |      /         \      |      /
   Intra-node ring        Intra-node ring        Intra-node ring
     (NVLink, 900 GB/s)    (NVLink, 900 GB/s)    (NVLink, 900 GB/s)
          \                    |                    /
           \                   |                   /
          Inter-node ring all-reduce (InfiniBand, 50 GB/s)
```

Algorithm: (1) Reduce-scatter within each node via NVLink ring, producing one chunk per node. (2) Cross-node ring all-reduce of the chunks over InfiniBand. (3) All-gather within each node via NVLink. This minimizes inter-node data transfer to just 2D/N_nodes, leveraging the fast intra-node fabric for the bulk of the data movement.

## Communication Compression

### Gradient Compression

At scale (thousands of GPUs), even ring all-reduce is expensive. Gradient compression reduces the data volume:

- **Sparsification (Top-K)**: Only communicate the K largest gradients. The receiver zeros out missing entries. Reduces volume by 10–100× with <1% accuracy loss when K/N ≈ 0.001–0.01 (Deep Gradient Compression, Aji & Heafield 2017).
- **Quantization**: Reduce precision — FP32 → FP16 (2×), FP16 → INT8 (4×), or 1-bit (ternary: {-1, 0, +1}). Error feedback compensates: maintain a residual buffer of the quantization error, add it to the next round's gradient.
- **PowerLaw compression**: Communicate values proportional to |gradient|^p where p > 1, emphasizing large gradients.

```python
# 1-bit stochastic quantization with error feedback
residual = 0
for step in training:
    gradient = compute_gradient()
    gradient += residual           # add accumulated error
    sign = sign(gradient)           # 1-bit: +1 or -1
    broadcast(sign)                 # all-reduce the signs
    residual = gradient - sign * scale
```

> **Interview Angle**: "What's the trade-off in gradient sparsification?" — Fewer bytes over the network means less communication time, but the reconstructed gradients are noisy. This noise acts as implicit regularization (sometimes improving generalization) but can slow convergence or cause divergence at very high compression ratios. The error-feedback mechanism is critical for convergence.

## Distributed Training Parallelism Strategies

### Data Parallelism

The simplest strategy: each worker holds a copy of the full model and processes a different data batch. Gradients are all-reduced across workers to keep models in sync.

```
Worker 0: model replica + batch 0 → grad0 ──┐
Worker 1: model replica + batch 1 → grad1 ──┤ All-Reduce
Worker 2: model replica + batch 2 → grad2 ──┤ (average gradients)
Worker 3: model replica + batch 3 → grad3 ──┘
         ↓ update with averaged gradient
```

Memory scaling: O(N × model_size). For a 70B parameter model in FP32, that's 70B × 4 bytes × 4 workers = 1.12 TB. This is why **ZeRO** (Zero Redundancy Optimizer) and model parallelism are needed for large models.

### Tensor (Intra-Layer) Parallelism

Split individual operations (matrix multiplies, layer norms) across GPUs. Introduced by Megatron-LM:

```
Tensor Parallelism for Linear Layer Y = XA:

GPU 0: X_0 → [X_0 @ A_00, X_0 @ A_01] → Y_0
GPU 1: X_1 → [X_1 @ A_10, X_1 @ A_11] → Y_1
                              
A is column-split: [A_0 | A_1]
X is column-split: [X_0; X_1]
Result: each GPU holds a partial Y, followed by all-reduce
```

For a transformer block, Megatron-LM applies: (1) Column-parallel attention (QKV projections split across GPUs), (2) Row-parallel attention output projection, (3) Column-parallel MLP, (4) Row-parallel MLP. The alternating column/row splits avoid all-reduce between consecutive operations — only a communication-avoiding "fused" operation is needed (all-reduce at the end of each sub-layer).

Communication cost: **one all-reduce per transformer sub-layer** (attention + MLP = 2 per block). This requires NVLink bandwidth — over PCIe or network, tensor parallelism is too slow.

### Pipeline Parallelism

Assign different layers to different GPUs in a pipeline:

```
Time →
GPU 0: [F0_b0] [F0_b1] [F0_b2] [F0_b3]
GPU 1:          [F1_b0] [F1_b1] [F1_b2] [F1_b3]
GPU 2:                   [F2_b0] [F2_b1] [F2_b2]
GPU 3:                            [F3_b0] [F3_b1]

F = forward, b = batch. Each GPU passes activations to the next.
Backward pass flows in reverse.
```

**Pipeline bubble**: At the start and end, not all GPUs are utilized. The fraction of time wasted is approximately (P-1)/(M+P-1) where P is the number of pipeline stages and M is the number of micro-batches.

**1F1B schedule** (one forward, one backward): GPipe naively runs all forwards then all backwards (large memory). The 1F1B schedule (PipeDream-Flush) interleaves forward and backward passes to reduce peak memory:

```
GPU 0: F0 F1 F2 F3 B0 B1 B2 B3
GPU 1:    F0 F1 F2 B0 B1 B2 B3
GPU 2:       F0 F1 B0 B1 B2 B3
GPU 3:          F0 B0 B1 B2 B3
```

### Expert Parallelism (Mixture of Experts)

Mixture-of-Experts (MoE) models route tokens to different "expert" feed-forward networks. With E experts and N GPUs:

```
Input tokens → Router (gating function) → Dispatch to experts

GPU 0: Expert 0, Expert 4
GPU 1: Expert 1, Expert 5  
GPU 2: Expert 2, Expert 6
GPU 3: Expert 3, Expert 7

All-to-all: tokens distributed to expert-owning GPUs
Compute: each GPU runs its experts on assigned tokens
All-to-all: results sent back to originating GPUs
```

Communication pattern: **two all-to-all operations** per MoE layer. This is the most communication-intensive parallelism pattern. MoE models like Mixtral 8×7B use EP across nodes, requiring high bisection bandwidth.

### Parallelism Comparison

| Strategy | What's Split | Memory per GPU | Communication | Best For |
-----------|-------------|---------------|---------------|----------|
 **Data** | Batch | Full model | All-reduce (grad) | Fits in 1 GPU |
 **Tensor** | Individual ops | Model / T | All-reduce per layer | NVLink available |
 **Pipeline** | Layers | Model / P | Point-to-point (activations) | Many GPUs, limited interconnect |
 **Expert** | Experts | Model + experts | All-to-all | MoE models |

In practice, modern training frameworks combine strategies: **3D parallelism** (data + tensor + pipeline) plus ZeRO optimization. Megatron-DeepSpeed and PyTorch FSDP support all combinations.

## Parameter Servers vs. Decentralized All-Reduce

### Parameter Server Architecture

A centralized (or sharded) server stores model parameters. Workers push gradients and pull updated parameters:

```
Worker 0 ──push grad──→ PS 0 (params 0..N/2)
Worker 1 ──push grad──→ PS 1 (params N/2..N)
Worker 2 ──pull param──→ PS 0
Worker 3 ──pull param──→ PS 1
```

**Problem**: The PS becomes a bottleneck. With N workers, the PS must handle N gradient pushes and N parameter pulls per step. Network bandwidth at the PS is the limiting factor.

### Async vs. Synchronous SGD

- **Synchronous (BSP — Bulk Synchronous Parallel)**: All workers compute gradients on their batch, then synchronize (all-reduce). The global step waits for the slowest worker (**straggler problem**). Used by PyTorch DDP, Horovod.

- **Asynchronous (ASP)**: Workers push gradients to PS and immediately pull updated parameters without waiting. Faster but uses **stale gradients** — the model may have been updated K times since this worker's batch was computed. Can diverge if staleness is too high. Used by Downpour SGD (Google 2012).

- **Stale Synchronous Parallelism (SSP)**: Bound the maximum staleness to S steps. Workers can be at most S steps behind the fastest worker. Balances throughput and convergence.

```python
# SSP pseudocode
max_staleness = 3
while not converged:
    params = ps.pull(allow_staleness=max_staleness)
    gradient = compute_gradient(minibatch, params)
    ps.push(gradient)
```

> **Interview Angle**: "Why has all-reduce replaced parameter servers for large-scale training?" — (1) All-reduce has O(1) communication at the PS (no hotspot), with total bandwidth O(N) distributed evenly. (2) Ring all-reduce is bandwidth-optimal. (3) Synchronous SGD converges more reliably than ASP for large models. Parameter servers survive in specific niches (embedding tables in recommendation models, federated learning).

## Federated Optimization

### Federated Learning (FL)

Federated Learning trains a shared model across decentralized data sources (mobile phones, hospitals, edge devices) without moving the raw data:

```
Central Server
    ↑          ↑          ↑
    │ pull     │ pull     │ pull
    │ params   │ params   │ params
    ↓          ↓          ↓
  Client 0   Client 1   Client 2
  (local     (local     (local
   data)      data)      data)
    ↑          ↑          ↑
    │ push     │ push     │ push
    │ grad     │ grad     │ grad
```

Algorithm: **FedAvg** (McMahan et al., 2017):
1. Server broadcasts current model θ_t to K selected clients.
2. Each client k performs E local SGD steps on its data D_k, computing θ_k.
3. Server aggregates: θ_{t+1} = Σ (|D_k|/|D|) × θ_k.

### Challenges in Federated Optimization

- **Non-IID data**: Clients have different data distributions. FedAvg can diverge when data is highly heterogeneous. Solutions: FedProx (proximal regularization), SCAFFOLD (variance reduction with control variates), FedNova (normalized averaging).
- **Communication efficiency**: Each round uploads a full model. Compression (quantization, sparsification) is essential. FedPAQ combines quantization with error accumulation.
- **Stragglers and dropouts**: Clients may be slow or unavailable. The server must handle partial participation gracefully — simply aggregate from whoever responds.
- **Differential privacy**: Add noise to gradients (DP-SGD) to prevent the server from inferring individual client data. The privacy-utility trade-off depends on the number of participating clients.

> **Interview Angle**: "How does federated learning handle a phone that goes offline mid-training?" — The server sets a timeout and proceeds with whichever clients responded. The aggregation weighting adjusts (or drops the missing client). The next round selects a new random subset of clients. The system is inherently robust to partial participation.