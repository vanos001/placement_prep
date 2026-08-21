# Ring AllReduce

Ring AllReduce is a distributed algorithm for computing the sum (or other associative reduction) of tensors across N workers, with O(N × data_size / N) = O(data_size) communication per worker. It is the foundation of synchronous data-parallel training (PyTorch DDP, Horovod, DeepSpeed) and was popularized by Baidu's 2017 paper "Bringing HPC Techniques to Deep Learning". This page covers the algorithm, the bandwidth-optimal property, the variants (recursive halving-doubling, tree allreduce), and the practical integration with NCCL on GPUs.

## The Problem with Parameter Server AllReduce

A naive approach to gradient aggregation across N workers:

```text
Each worker W_i has gradient G_i.
Each worker sends G_i to the parameter server (PS).
PS computes G_sum = sum_i G_i.
PS broadcasts G_sum to all workers.
```

The PS is a bottleneck: it receives N copies of G (total bandwidth N × |G| at the PS), computes the sum, and sends N copies back. For a 1 GB gradient and N=8 workers, the PS sees 8 GB inbound + 8 GB outbound = 16 GB; at 100 Gbps, that's 1.3 seconds per step. The PS's inbound bandwidth is the cluster's training throughput ceiling.

## Ring AllReduce

Ring AllReduce organizes the N workers in a logical ring. Each worker has a left neighbor and a right neighbor; data flows around the ring in two phases.

### Phase 1: Reduce-Scatter

```text
Workers: W0, W1, W2, W3 (in a ring)
Each worker splits its gradient G_i into N chunks (G_i_0, G_i_1, ..., G_i_{N-1}).

Step 0:
  W0 sends G0_0 to W1, W1 sends G1_1 to W2, W2 sends G2_2 to W3, W3 sends G3_3 to W0.

Step 1:
  W1 receives G0_0, computes G0_0 + G1_1 = (G0+G1)_chunk_1, sends to W2.
  W2 receives G1_1, computes G1_1 + G2_2 = (G1+G2)_chunk_2, sends to W3.
  W3 receives G2_2, computes G2_2 + G3_3 = (G2+G3)_chunk_3, sends to W0.
  W0 receives G3_3, computes G3_3 + G0_0 = (G3+G0)_chunk_0, sends to W1.

Step 2 (after N-1 steps total):
  Each worker has the full sum for one chunk.
```

After N-1 steps, each worker has the fully-reduced sum for one chunk. The total bandwidth per worker is `(N-1) × |G| / N` (each step sends one chunk's worth).

### Phase 2: All-Gather

```text
Step N (start of all-gather):
  W0 has sum_chunk_0, sends it to W1.
  W1 has sum_chunk_1, sends it to W2.
  ... etc.

Step N+1:
  W1 receives sum_chunk_0 from W0, sends to W2.
  W2 receives sum_chunk_1 from W1, sends to W3.
  ... etc.

After another N-1 steps, every worker has the full sum G_sum for every chunk.
```

Total per-worker bandwidth: `2 × (N-1) × |G| / N ≈ 2 |G|`. This is independent of N — the more workers, the less each one sends.

## Bandwidth-Optimal Property

The key property: per-worker bandwidth is `2 |G| (N-1) / N ≈ 2 |G|`. For large N, this approaches `2 |G|`. Compare with the parameter server's `2 |G|` per worker as well — same bandwidth, but no PS bottleneck.

In practice, Ring AllReduce's per-step latency dominates for small |G| (the ring has N-1 sequential steps, so latency scales as N). For large |G| (the common case in ML training), bandwidth dominates and Ring AllReduce is optimal.

## Recursive Halving-Doubling

A variant that reduces the latency from O(N) to O(log N):

```text
Phase 1: Reduce-Scatter by halving
  Pair workers (W0,W4), (W1,W5), (W2,W6), (W3,W7).
  Each pair exchanges half their data; each keeps the reduced half.
  Repeat with re-paired workers, halving data each time.
  After log N steps, each worker has the full sum for 1/N of the data.

Phase 2: All-Gather by doubling
  Reverse the process: pairs exchange the 1/N they have.
  After log N steps, each worker has the full sum.
```

Total steps: `2 × log N` instead of `2 (N-1)`. Each step transfers `|G|/N` of the data, so total bandwidth is still `2 |G|`. But the latency is `2 log N × link_latency` instead of `2 (N-1) × link_latency`.

Recursive halving-doubling is preferred for small messages (latency-bound), and Ring AllReduce for large messages (bandwidth-bound). NCCL auto-selects between the two based on message size.

## Tree AllReduce

A third variant: a tree of workers. Each worker sends to its parent, the root computes the sum, and the root broadcasts back. Tree AllReduce is bandwidth-suboptimal (the root sees O(N) traffic), but has the lowest latency for small N (root-to-leaf communication is one RTT).

NCCL uses Tree AllReduce for very small messages and large N (where the per-step Ring latency becomes a problem).

## NCCL: GPU Implementation

NCCL (NVIDIA Collective Communications Library) implements Ring AllReduce for GPUs, with hardware-specific optimizations:

- **InfiniBand Verbs** for cross-node communication (GPUDirect RDMA).
- **NVLink** for same-node communication (up to 900 GB/s on H100).
- **Topology detection**: NCCL discovers the cluster topology and arranges the ring to minimize cross-node traffic (NVLink > PCIe > IB).
- **Ring vs Tree auto-selection**: NCCL picks the algorithm based on message size and cluster topology.

PyTorch DDP, Horovod, and DeepSpeed all use NCCL under the hood. The user-facing API:

```python
# PyTorch DDP
import torch.distributed as dist

dist.init_process_group("nccl", rank=rank, world_size=N)
model = DDP(model, device_ids=[local_rank])

# Each step, DDP all-reduces the gradients
loss.backward()
# DDP's hooks call dist.all_reduce on each gradient
optimizer.step()
```

The gradient all-reduce happens automatically in `loss.backward()`. DDP overlaps the all-reduce with the backward computation (gradient reduction of one layer happens while the next layer's backward is still computing), hiding most of the all-reduce latency.

## Topology Considerations

Ring AllReduce's efficiency depends on the physical topology. The ideal ring has:
- Same-node workers adjacent in the ring (NVLink between them).
- Cross-node traffic minimized to the ring's "cut" between nodes (one link between nodes).

For a 4-node cluster with 8 GPUs per node (32 GPUs total), the ideal ring:

```text
Node 1: GPU0 → GPU1 → ... → GPU7
                ↓ (cross-node NVLink or IB)
Node 2: GPU0 → GPU1 → ... → GPU7
                ↓
Node 3: GPU0 → GPU1 → ... → GPU7
                ↓
Node 4: GPU0 → GPU1 → ... → GPU7
                ↓ (back to Node 1)
```

Each node has 2 cross-node ring adjacencies (in and out). The cross-node bandwidth is the cluster's training throughput ceiling. With 4 nodes × 100 Gbps IB, the ring's cross-node bandwidth is 100 Gbps × 4 (one per node) = 400 Gbps.

NCCL's topology-aware algorithm picks the ring order automatically based on detected NVLink, IB, and PCIe connections.

## Production Deployment

- **PyTorch DDP**: built-in, no extra setup.
- **Horovod**: framework-agnostic, supports TensorFlow, PyTorch, MXNet.
- **DeepSpeed**: adds ZeRO (memory optimization), pipeline parallelism, and larger batches.
- **Megatron-LM**: tensor parallelism + data parallelism combined.

For typical training (8 GPUs, 1 TB model state, gradient size 32 GB):
- Without overlap: ~3 seconds per step (NCCL all-reduce time).
- With DDP overlap: ~0.5 seconds per step (gradient reduction overlapped with backward).
- With DeepSpeed ZeRO Stage 2: ~0.3 seconds (gradient + optimizer state partitioned).

## Common Pitfalls

1. **Forgetting to use `gradient_as_bucket_view=True` in DDP.** This option (default in recent PyTorch) makes gradient buckets reusable for the all-reduce, halving the memory.

2. **Using multiple small all-reduce calls instead of one large.** Each all-reduce has fixed overhead (~30 µs for NCCL). Reducing 1000 gradients as 1000 small all-reduces is 30 ms of overhead; bucketing them into 1 large is 30 µs. DDP auto-buckets, but custom code may not.

3. **Not using NCCL's tensor core acceleration.** NCCL 2.10+ uses tensor cores for the reduction (FP16/BF16 reductions can be 4× faster). Set `NCCL_TENSOR_OPS=1` (default in recent versions).

4. **Mixing different GPU types in the same ring.** An H100 in the same ring as an A100 will slow down to the A100's speed. Homogeneous clusters are simpler.

5. **Not pinning processes to NUMA nodes.** On multi-socket servers, NCCL on the wrong NUMA node has ~30% lower bandwidth due to cross-socket memory traffic. Use `numactl --cpunodebind` to pin.

6. **Forgetting that PyTorch's "find_unused_parameters" doubles the all-reduce time.** If your model has parameters that don't get gradients in every step (e.g., conditional execution), DDP must do an extra all-reduce to find which parameters were unused.

## References

- Baidu Research, "[Bringing HPC Techniques to Deep Learning](https://research.baidu.com/Blog/index/view?id=119)" (2017) — the original Ring AllReduce paper for ML
- Patarasuk & Yuan, "[Bandwidth Optimal All-reduce Algorithms for Clusters](https://cs.brown.edu/people/jslng/Docs/bandwidthoptimal.pdf)" (2007)
- [NCCL documentation](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/operations.html)
- [PyTorch DDP tutorial](https://pytorch.org/tutorials/intermediate/ddp_tutorial.html)
- [Horovod documentation](https://horovod.readthedocs.io/)
- [DeepSpeed documentation](https://www.deepspeed.ai/)
- [NVIDIA Collective Communication Library (NCCL)](https://github.com/NVIDIA/nccl)
