# MPI, OpenMP, OpenACC & GPU Communication Primitives

## MPI (Message Passing Interface)

### Core Model

MPI is the **de facto standard** for distributed-memory parallel programming. Each rank runs as a separate OS process with its own address space. Communication is explicit: ranks send and receive messages through the MPI runtime library. The standard (currently MPI-4.0, 2021) defines point-to-point and collective operations, one-sided communication (RMA), and parallel I/O.

Every MPI program follows the same skeleton:

```c
#include <mpi.h>
int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    // ... parallel work ...
    MPI_Finalize();
}
```

The communicator `MPI_COMM_WORLD` groups all ranks. Custom communicators (via `MPI_Comm_split` or `MPI_Comm_create_group`) enable topology-aware subgroups — a pattern heavily used in deep learning where you split by node, by intra-node GPU group, or by model-parallelism dimension.

### Point-to-Point Communication

MPI provides four send modes that differ in buffering and synchronization semantics:

| Mode | Buffering | Blocking? | When Returns |
|------|-----------|-----------|-------------|
| `MPI_Send` | System chooses | Yes | When buffer is safe to reuse |
| `MPI_Bsend` | User-provided buffer | Yes | Immediately (copies to buffer) |
| `MPI_Ssend` | None (synchronous) | Yes | When matching recv posted |
| `MPI_Rsend` | None (ready) | Yes | Only valid if recv already posted |

The non-blocking variants (`MPI_Isend`, `MPI_Irecv`) return immediately with a request handle; completion is tested with `MPI_Test`/`MPI_Wait` or waited on in bulk with `MPI_Waitall`. This overlap of computation and communication is critical for HPC performance.

> **Interview Angle**: "Why does `MPI_Send` sometimes deadlock?" — The standard allows `MPI_Send` to behave as either buffered or synchronous. If both ranks call `MPI_Send` to each other with insufficient system buffer space, you get a classic deadlock. Use `MPI_Sendrecv` (which internally handles the handoff) or non-blocking sends to avoid this.

### MPI Collectives

Collective operations involve all ranks in a communicator. The MPI standard mandates semantic equivalence (same result), but implementations are free to choose any algorithm:

- **`MPI_Bcast`**: Root sends data to all ranks. Implemented as a binomial tree for small messages, pipelined tree for large.
- **`MPI_Scatter` / `MPI_Gather`**: Root distributes / collects distinct chunks.
- **`MPI_Reduce`**: Combines data from all ranks using an associative operation (sum, max, min, user-defined) at the root. Implemented via reduce-scatter + all-gather or recursive doubling.
- **`MPI_Allreduce`**: Like reduce, but result is available on all ranks — the workhorse of distributed deep learning (gradient averaging).
- **`MPI_Alltoall`**: Every rank sends a distinct message to every other rank. Expensive: O(N²) messages. Used in expert-parallel MoE models.
- **`MPI_Barrier`**: Synchronization point — all ranks wait until everyone arrives.

### MPI Topology

MPI allows you to create virtual topologies that the runtime can map to physical hardware:

```c
int dims[2] = {4, 4};              // 4x4 grid
int periods[2] = {1, 1};           // periodic in both dimensions
MPI_Comm cart_comm;
MPI_Cart_create(MPI_COMM_WORLD, 2, dims, periods, 0, &cart_comm);

int left, right;
MPI_Cart_shift(cart_comm, 0, 1, &left, &right); // neighbors in dimension 0
```

Cartesian (grid) and graph topologies let the MPI library optimize rank placement to minimize network hops. For stencil computations (CFD, weather models), this is essential — you want neighboring ranks on physically adjacent nodes.

### MPI Fault Tolerance (ULFM)

Standard MPI aborts the entire job if any rank fails. The **ULFM** (User Level Failure Mitigation) extension (standardized in MPI-4.0) provides primitives for fault-aware applications:

- `MPI_Comm_shrink`: Create a new communicator excluding failed ranks.
- `MPI_Comm_agree`: Agreement on which ranks are alive.
- `MPI_Comm_revoke`: Forcefully invalidate a communicator.

> **Interview Angle**: "How do you handle node failure in a 10,000-rank MPI job?" — ULFM lets you shrink the communicator and redistribute data. In practice, most HPC sites use application-level checkpoint/restart (see [hpc-infra.md](./hpc-infra.md)) because ULFM adoption is still limited.

## OpenMP: Shared-Memory Parallelism

### Threading Model

OpenMP uses compiler directives (`#pragma omp`) to parallelize loops, sections, and tasks within a single shared-address-space process. It is the standard for intra-node parallelism, complementing MPI's inter-node model (the "MPI+X" hybrid pattern, where X is OpenMP, CUDA, or OpenACC).

```c
#pragma omp parallel for schedule(dynamic, 64) reduction(+:sum)
for (int i = 0; i < N; i++) {
    sum += expensive_compute(data[i]);
}
```

### Scheduling Strategies

The `schedule` clause controls loop iteration assignment to threads:

| Schedule | Chunk Assignment | Best For |
|----------|-----------------|----------|
| `static` | Block partition at compile time | Uniform iteration cost |
| `static, k` | Round-robin blocks of size k | Mild load imbalance |
| `dynamic` | First-idle-gets-next-chunk | High load imbalance |
| `guided` | Decreasing chunk sizes | Balancing overhead and load |
| `auto` | Runtime decides | Portable code |

The OpenMP runtime maintains a worksharing internal control variable (ICV) that tracks each thread's loop bounds. For `dynamic`, this is a shared counter protected by an atomic or lock — which becomes a contention point with many threads. `guided` scheduling reduces contention by exponentially shrinking chunks.

### OpenMP Tasking

OpenMP 3.0+ introduced the **task** model for irregular parallelism (recursive decomposition, graph traversal):

```c
#pragma omp parallel
#pragma omp single
{
    #pragma omp task
    process_subtree(root->left);
    #pragma omp task
    process_subtree(root->right);
}
```

Tasks are placed in a per-thread deque. Threads that exhaust their own tasks attempt to **steal** from other threads' deques (work-stealing, similar to Go's scheduler). The `depend` clause enables task dependencies:

```c
#pragma omp task depend(in: A[0:N]) depend(out: B[0:N])
compute(A, B, N);
```

This creates a DAG of tasks that the runtime executes respecting dependencies — similar in spirit to CUDA Graphs.

## OpenACC: Directive-Based GPU Programming

OpenACC provides compiler directives to offload compute regions to GPUs without writing explicit CUDA code:

```c
#pragma acc data copyin(A[0:N], B[0:N]) copyout(C[0:N])
{
    #pragma acc parallel loop
    for (int i = 0; i < N; i++) {
        C[i] = A[i] + B[i];
    }
}
```

Key clauses: `parallel` (launch kernel), `loop` (parallelize loop), `kernels` (compiler decides parallelism), `data` (manage transfers), `async` (overlap with host). The `collapse` clause fuses nested loops for better parallelism. OpenACC is popular in legacy Fortran/C++ scientific codebases because it requires minimal restructuring — you add directives incrementally.

> **Interview Angle**: "OpenACC vs. CUDA for a new project?" — CUDA gives fine-grained control (shared memory, warp-level primitives, cooperative groups) essential for high-performance kernels. OpenACC trades control for portability across NVIDIA/AMD/Intel GPUs. For new projects targeting a single vendor, CUDA (or HIP for AMD) is preferred.

## CUDA Advanced: Memory, Streams, Graphs, Cooperative Groups

### CUDA Memory Hierarchy and Optimization

Beyond basic `cudaMalloc`/`cudaMemcpy`, HPC kernels exploit the full memory hierarchy:

- **Pinned (page-locked) host memory** (`cudaMallocHost`): Enables DMA transfers via GPUDirect, avoiding double-copy through pinned bounce buffers. Required for async memcpy overlap.
- **Unified Memory** (`cudaMallocManaged`): Page-migration between CPU and GPU. On systems with NVLink, this is efficient; on PCIe, page faults cause significant stalls. Use with `cudaMemPrefetchAsync` to hint migration.
- **Managed memory with `cudaMemAdvise`**: Allows advising the driver about access patterns — preferred location, set accessed-by, or prefetch. Critical for NUMA-aware data placement.
- **Shared memory**: On-chip memory (~48–228 KB depending on GPU generation), banked for parallel access. Bank conflicts cause serialization. Use `__shared__` variables and `__syncthreads()` for barrier synchronization.

### CUDA Streams and Overlap

Streams enable concurrent kernel execution and async memory transfers:

```c
cudaStream_t stream1, stream2;
cudaStreamCreate(&stream1);
cudaStreamCreate(&stream2);

// Overlap: kernel on stream1 while H2D copy for stream2
cudaMemcpyAsync(d_A, h_A, size, cudaMemcpyHostToDevice, stream1);
kernel1<<<grid, block, 0, stream1>>>(d_A); // depends on copy
cudaMemcpyAsync(d_B, h_B, size, cudaMemcpyHostToDevice, stream2);
kernel2<<<grid, block, 0, stream2>>>(d_B);
```

The GPU command processor serializes within a stream but can interleave operations across streams, subject to resource availability (SMs, copy engines). Default stream (0) is special: it is a blocking stream that synchronizes with all other streams unless `cudaStreamCreateWithFlags(&s, cudaStreamNonBlocking)` is used.

### CUDA Graphs

CUDA Graphs capture a sequence of kernel launches and memory operations into a single **graph** that can be launched repeatedly with minimal CPU overhead:

```c
cudaGraph_t graph;
cudaGraphExec_t graphExec;
cudaStreamBeginCapture(stream, cudaStreamCaptureModeRelaxed);
// ... sequence of kernel launches and memcpy ...
cudaStreamEndCapture(stream, &graph);
cudaGraphInstantiate(&graphExec, graph, NULL, NULL, 0);
// Later: launch entire graph with one call
cudaGraphLaunch(graphExec, stream);
```

Without graphs, each kernel launch requires a CPU-side call into the driver (~5–20μs). For short kernels, this dominates runtime. Graphs reduce launch overhead to ~1μs. They are heavily used in inference serving (TensorRT) and training loops where the same operations repeat each iteration.

> **Interview Angle**: "When do CUDA Graphs break?" — Dynamic control flow (data-dependent kernel launches), varying grid sizes, or tensor shapes that change per iteration. In these cases, you need to re-capture the graph, losing the benefit.

### Cooperative Groups

Cooperative Groups (CUDA 9+) generalize thread synchronization beyond block boundaries:

- **Thread Group**: Subset of threads within a block.
- **Block Group**: All threads in a block (`this_thread_block()`). Supports `sync()`, `shuffle` (warp-level exchange).
- **Multi-Block Group**: Threads across blocks on the same GPU, launched via `<<<grid, block, 0, stream>>>(..., cooperative_groups::this_multi_block)` with `cudaDeviceSynchronize()`.
- **Device Group**: All threads across all GPUs (requires Launch Coherence — rare).

This enables grid-wide reductions, peer-to-peer sharing, and collective operations that were previously impossible without separate kernel launches.

## NCCL: NVIDIA Collective Communications Library

NCCL implements highly optimized collective operations (all-reduce, all-gather, broadcast, reduce-scatter) for GPUs within and across nodes. It is the backbone of every major distributed training framework (PyTorch `DistributedDataParallel`, TensorFlow, JAX).

```
NCCL All-Reduce Internals (single node, 8 GPUs):

GPU0 ←→ GPU1 ←→ GPU2 ←→ GPU3
  ↑          ↑          ↑          ↑
  └──── NVLink/NVSwitch interconnect ────┘
```

NCCL automatically selects the best algorithm based on message size, number of GPUs, and topology:
- **Ring** for medium messages (1KB–10MB)
- **Tree** for large messages (10MB+)
- **Direct peer-to-peer** for small messages between directly connected GPUs

It uses **NCCL_P2P_LEVEL** to determine connectivity: NVLink > P2P over PCIe > same NUMA node > different NUMA > different nodes. The `ncclTopoGetSystem` call queries the hardware topology at initialization to build an optimal communication pattern.

## GPUDirect

GPUDirect comprises three technologies that enable direct GPU-to-device communication:

| Technology | What It Does | Latency Benefit |
|-----------|-------------|----------------|
| **GPUDirect RDMA** | GPU and NIC exchange data directly via DMA, bypassing CPU and host memory | ~40μs → ~5μs per transfer |
| **GPUDirect for CUDA IPC** | GPUs within a node share memory via NVLink/PCIe P2P | Zero-copy, ~1μs |
| **GPUDirect Async** | GPU can signal NIC directly (signaling without CPU) | Removes CPU from critical path |

For GPUDirect RDMA, the GPU memory must be registered with the NIC (via `ibv_reg_mr` for InfiniBand). The NIC performs DMA reads/writes directly to GPU VRAM. This requires IOMMU support and BAR1 mapping. On NVIDIA, this works transparently through NCCL when supported hardware is detected.

## RDMA (Remote Direct Memory Access)

RDMA enables a machine to read from or write to the memory of a remote machine **without involving the remote CPU**. The NIC handles the entire data transfer via DMA:

```
Traditional Send/Recv:                  RDMA Write:

App → [kernel] → NIC ──→ NIC → [kernel] → App    App → [kernel] → NIC ──→ NIC → Remote Memory
     CPU copies           CPU copies                  CPU copies            No remote CPU!
```

RDMA verbs (the InfiniBand programming interface):

- **Post Send/Recv**: The receiver must post a receive buffer before the sender transmits (connection-oriented).
- **RDMA Write/Read**: The initiator specifies a remote address and remote key (rkey). No remote CPU involvement. Requires prior memory registration.
- **Atomic operations**: Fetch-and-add, compare-and-swap on remote memory.

Memory registration (`ibv_reg_mr`) pins the pages and provides a local key (lkey) for local DMA and a remote key (rkey) for remote access. This is expensive (~10–100μs per registration), so HPC applications register large memory pools at startup.

## InfiniBand

InfiniBand (IB) is the dominant HPC interconnect, designed from the ground up for RDMA and low latency:

```
InfiniBand Protocol Stack:
┌─────────────────────┐
│     Application      │
├─────────────────────┤
│    Verbs API (libibverbs)  │
├─────────────────────┤
│    Transport:       │  RDMA CM, RC/UC/UD QPs
├─────────────────────┤
│    Network: IB (InfiniBand) or RoCE (Ethernet) │
├─────────────────────┤
│    Link:            │  64b/66b encoding, NRZ/PAM4
├─────────────────────┤
│    Physical:        │  Copper (NDR), Optical (EDR/HDR/NDR)
└─────────────────────┘
```

Key InfiniBand concepts:

- **Queue Pairs (QP)**: A send queue and receive queue. Reliable Connected (RC) QPs guarantee in-order delivery with hardware retransmission — analogous to TCP but in hardware at ~1μs latency. Unreliable Datagram (UD) is connectionless but provides no guarantees.
- **Completion Queue (CQ)**: Work requests generate completion queue entries (CQEs) when done. Polled by the application (or via interrupt for less performance-critical paths).
- **Channel Adapter (HCA)**: The InfiniBand NIC. Modern HCAs (Mellanox ConnectX-6/7, NVIDIA BlueField DPU) support 200–400 Gbps.

### InfiniBand Generations

| Generation | Speed | HDR (200Gb/s) | NDR (400Gb/s) | XDR (800Gb/s, upcoming) |
|-----------|-------|---------------|---------------|------------------------|
| Throughput | Per port | 200 Gb/s | 400 Gb/s | 800 Gb/s |
| Latency | Typical | ~0.6μs | ~0.5μs | Target <0.5μs |

## RoCE (RDMA over Converged Ethernet)

RoCE v2 runs RDMA over standard Ethernet with UDP encapsulation (IP + UDP + IB transport header). This allows RDMA on commodity Ethernet switches rather than specialized InfiniBand switches.

```
RoCE v2 Packet:  [Ethernet] [IP] [UDP dst=4791] [BTH] [Payload]
InfiniBand:      [LRH] [BTH] [Payload]
```

The challenge: Ethernet provides **no in-order delivery guarantee or PFC (Priority Flow Control)** by default. RoCE requires:
- **PFC (IEEE 802.1Qbb)**: Link-level pause frames to prevent buffer overflow (lossless Ethernet).
- **ECN (Explicit Congestion Notification)**: For congestion control.
- **DCQCN**: Datacenter Quantized Congestion Notification — the de facto congestion control protocol for RoCE.

RoCE v2 has largely won the datacenter AI cluster market because it runs over existing Ethernet infrastructure. InfiniBand still dominates traditional HPC (Top500) for its lower latency and simpler congestion management.

## NVLink and NVSwitch

NVLink is NVIDIA's high-speed GPU-to-GPU interconnect:

| Generation | Bandwidth per link | Links per GPU | Total GPU-GPU BW |
|-----------|-------------------|---------------|-----------------|
| NVLink 2 (V100) | 25 GB/s | 6 | 300 GB/s |
| NVLink 3 (A100) | 50 GB/s | 12 | 600 GB/s |
| NVLink 4 (H100) | 50 GB/s | 18 | 900 GB/s |
| NVLink 5 (B200) | 56.25 GB/s | 18 | 1.8 TB/s (bidirectional 3.6 TB/s) |

NVLink provides cache-coherent interconnect: GPUs can atomically access each other's memory. NVSwitch (used in DGX/HGX systems) provides a full crossbar — any GPU can communicate with any other GPU at full NVLink bandwidth simultaneously. Without NVSwitch, NVLink connections are limited to a ring or mesh topology per node.

> **Interview Angle**: "Why is NVLink important for model parallelism?" — Tensor parallelism (splitting a single matrix multiply across GPUs) requires all-reduce of partial results every layer. Over PCIe, this takes ~100μs for a large tensor; over NVLink 4, it takes ~1–2μs. For a 100-layer model, that's the difference between 10ms and 200ms of communication overhead per training step.

## Comparison: Interconnect Technologies

| Feature | NVLink 4 | PCIe 5.0 | InfiniBand NDR | RoCE v2 (400G) |
|---------|----------|----------|---------------|-----------------|
| **Bandwidth** | 900 GB/s (GPU-GPU) | 64 GB/s (bidir) | 400 Gb/s (~50 GB/s) | 400 Gb/s (~50 GB/s) |
| **Latency** | ~1μs | ~1–2μs (P2P) | ~0.5μs | ~1–2μs |
| **Scope** | Intra-node | Intra-node | Inter-node | Inter-node |
| **CPU involvement** | None (GPU-initiated) | Requires CPU | None (RDMA) | None (RDMA) |
| **Topology** | NVSwitch crossbar | Tree/Ring | Fat-tree/Clos | Clos (Ethernet) |
| **Use case** | Tensor parallelism | GPU↔CPU data | HPC MPI | AI training clusters |