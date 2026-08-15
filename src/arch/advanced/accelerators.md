# Accelerators: DPUs, FPGAs, TPUs, and Beyond

## Overview

The CPU is no longer the only game in town. Data centers are increasingly dominated by **specialized accelerators** for networking (DPUs/smart NICs), ML inference/training (TPUs, GPUs with tensor cores), and reconfigurable computing (FPGAs, CGRAs). This chapter covers the architecture, programming models, and system integration challenges of modern accelerators.

```mermaid
graph TB
    subgraph "The Accelerator Spectrum"
        FPGA["FPGA<br/>(Reconfigurable)"
        CGRA["CGRA<br/>(Coarse-Grained Reconfigurable)"
        GPU["GPU<br/>(SIMT Parallel)"
        TPU["TPU/ASIC<br/>(Fixed-Function)"
        DPU["DPU/Smart NIC<br/>(Infrastructure)"
        CS["Computational Storage<br/>(Near-Data Processing)"
    end
    FPGA --> |"more flexible"| GPU
    GPU --> |"more specialized"| TPU
```

## Smart NICs, DPUs, and IPUs

### What Problem Do They Solve?

CPU cores spend 20-30% of their cycles on **infrastructure tasks** (networking, storage, security) in cloud workloads. DPUs (Data Processing Units) offload these tasks to dedicated hardware:

```
Infrastructure offload targets:
  - Networking: TCP/IP stack, TLS/SSL encryption, flow steering, NAT, load balancing
  - Storage: NVMe-oF, iSCSI, data compression, deduplication, erasure coding
  - Security: TLS termination, IPsec, key management, firewall rules
  - Virtualization: SR-IOV management, virtio backend, OVS (Open vSwitch)
  - Observability: telemetry, packet capture, flow logging
```

### Architecture of a Modern DPU

```
NVIDIA BlueField-3 DPU:
  ┌──────────────────────────────────────────────┐
  │ ARM Cortex-A78 (8 cores, 2.2 GHz)           │  ← General-purpose control plane
  ├──────────────────────────────────────────────┤
  │ Network Accelerators:                       │
  │  - 400 Gbps crypto engine (AES-GCM, etc.)   │
  │  - Regular expression matcher (regex offload)│
  │  - Flow steering engine (millions of flows)  │
  ├──────────────────────────────────────────────┤
  │ Storage Accelerators:                       │
  │  - NVMe controller                          │
  │  - Compression/decompression (LZ4, ZSTD)    │
  │  - Erasure coding engine                    │
  ├──────────────────────────────────────────────┤
  │ Memory: 16-32 GB DDR5 + 8-16 MB SRAM        │
  │ Interfaces: 2× 400GbE, PCIe 5.0 x16, CXL   │
  └──────────────────────────────────────────────┘

Total power: 30-40W (vs. 200W+ for a CPU doing the same work)
```

### DPU Programming Models

| Model | Description | Example |
-------|-------------|----------|
 **Embedded ARM** | Run standard Linux userspace on DPU's ARM cores | DOCA (NVIDIA), P4 + C on ARM |
 **P4** | Programmable packet header parsing + action | Netronome, Tofino |
 **eBPF** | Kernel-level programmable packet processing | Kernel XDP, BlueField DOCA BPF |
 **RDMA** | Direct memory access from NIC to application | libibverbs, GPUDirect |

### Major DPU Products

| Product | Vendor | Cores | NIC Speed | Key Feature |
---------|--------|-------|-----------|-------------|
 BlueField-3 | NVIDIA | 8× ARM A78 | 400 GbE | CXL 3.0, ML acceleration |
 IPU (Infrastructure PU) | Intel | 12× ARM + Xeon-D | 200 GbE | Vault, OVS offload |
 Pensando DPU | AMD (Pensando) | Custom P4 | 400 GbE | Packet flow processor |
 AWS Nitro | Amazon | Custom ARM | 100 GbE | EBS, ENA, VPC offload |

> **Interview Angle**: "What is a DPU and why are cloud providers adopting them?" A DPU offloads infrastructure workloads (networking, storage, security) from the host CPU to dedicated hardware. This saves 20-30% of CPU cycles that can be used for customer workloads, improving per-server revenue. AWS's Nitro is the most successful example — it abstracts virtualization overhead so the host CPU only runs customer code.

## FPGAs

### Architecture

```
FPGA structure:
  ┌─────────────────────────────────────────┐
  │ CLB  CLB  CLB  CLB  CLB  CLB  CLB  CLB │  ← Configurable Logic Blocks
  │ CLB  BRAM  CLB  CLB  DSP  CLB  CLB  CLB │  ← Block RAM, DSP slices
  │ CLB  CLB  CLB  BRAM  CLB  CLB  DSP  CLB │
  │ I/O                CLB  CLB  CLB  CLB  I/O│  ← I/O blocks (PCIe, DDR, etc.)
  └─────────────────────────────────────────┘

CLB (Configurable Logic Block):
  - 1-2 Look-Up Tables (LUTs): 6-input Boolean function → any 6-input gate
  - 1-2 Flip-flops: state elements
  - Multiplexers: routing between LUTs
  - ~100K–1M CLBs on modern FPGAs

DSP Slice: 25×18 multiply + 48-bit add (MAC operation)
  - Modern FPGAs have 1000-10000 DSP slices
  - Each can do 2-4 MAC operations per cycle at 500+ MHz
```

### FPGA vs. GPU vs. CPU

| Metric | CPU | GPU | FPGA |
--------|-----|-----|------|
 Clock frequency | 3-5 GHz | 1.5-2.5 GHz | 0.3-0.5 GHz |
 Parallelism | 8-64 threads | 10000+ threads | Custom spatial |
 Peak INT8 OPS | ~2 TOPS | ~200 TOPS (A100) | ~50-500 TOPS |
 Latency | ~5-100 ns | ~1-10 μs | ~10-100 ns |
 Power efficiency | ~10 GOPS/W | ~100 GOPS/W | ~50-200 GOPS/W |
 Flexibility | Software | Software | Hardware (bitstream) |
 Development | C/C++/Go | CUDA/OpenCL | Verilog/VHDL/HLS |
 Time to market | Fast | Fast | Slow (6-18 months) |

### HLS (High-Level Synthesis)

HLS allows programming FPGAs with C/C++ instead of Verilog:

```c
// HLS example: vector dot product
#pragma HLS PIPELINE II=1  // Fully pipelined, one result per cycle
void dot_product(int *a, int *b, int *result, int N) {
    int acc = 0;
    for (int i = 0; i < N; i++) {
        #pragma HLS UNROLL factor=4  // Process 4 elements per cycle
        acc += a[i] * b[i];
    }
    *result = acc;
}
```

### Where FPGAs Excel

- **Real-time video processing**: low, deterministic latency
- **Network packet processing**: custom parsers at line rate (400 Gbps)
- **Database acceleration**: compression, filtering, regex
- **Financial trading**: ultra-low-latency decision engines
- **Genomics**: Smith-Waterman alignment (FPGA is 10-100× faster than CPU)

## CGRAs (Coarse-Grained Reconfigurable Arrays)

CGRAs sit between FPGAs and GPUs: reconfigurable spatial computing with word-level (not bit-level) operations:

```
CGRA structure:
  2D grid of Processing Elements (PEs)
  Each PE: 8-16 bit ALU + register file + local memory
  Interconnect: configurable routing between PEs

Example: 8×8 CGRA
  ┌───┬───┬───┬───┬───┬───┬───┬───┐
  │PE │PE │PE │PE │PE │PE │PE │PE │
  ├───┼───┼───┼───┼───┼───┼───┼───┤
  │PE │PE │PE │PE │PE │PE │PE │PE │
  ├───┼───┼───┼───┼───┼───┼───┼───┤
  │PE │PE │PE │PE │PE │PE │PE │PE │
  └───┴───┴───┴───┴───┴───┴───┴───┘

Advantages over FPGA:
  - Higher frequency (500 MHz-1 GHz vs 300-500 MHz)
  - Better power efficiency for data-parallel workloads
  - Easier to compile from C (spatial compiler maps loops to PE array)

Disadvantages:
  - Less flexible than FPGA (word-level, not bit-level)
  - Smaller market (mainly research and a few startups)
```

## TPU Architecture

### Google TPU v1–v4

The TPU (Tensor Processing Unit) is a domain-specific ASIC for neural network inference and training.

```
TPU v1 (inference only, 2016):
  ┌─────────────────────────────────────┐
  │ Matrix Multiply Unit (MXU)         │
  │ 256×256 systolic array             │  ← 65,536 MAC units
  │ = 92 TOPS at 700 MHz                │
  ├─────────────────────────────────────┤
  │ Unified Buffer (24 MB)              │  ← Activation storage
  ├─────────────────────────────────────┤
  │ Weight Memory (4 MB, 8-bit)         │
  ├─────────────────────────────────────┤
  │ Activation Unit (ReLU, sigmoid, etc)│
  └─────────────────────────────────────┘
  Interface: PCIe 3.0 (from host CPU)
```

### Systolic Array: The TPU's Core

A systolic array is a 2D grid of multiply-accumulate units where data flows through the array rhythmically:

```
3×3 Systolic Array example:

  Cycle 1:          Cycle 2:          Cycle 3:
  [a0*b0] →  →     [a0*b0][a1*b0]   [a0*b0][a1*b0][a2*b0]
           ↓               ↓     ↓        ↓     ↓     ↓
         [a0*b1]       [a0*b1][a1*b1]  [a0*b1][a1*b1][a2*b1]
                       ↓     ↓        ↓     ↓     ↓
                     [a0*b2]         [a0*b2][a1*b2][a2*b2]

Each PE: receives input from left, weight from top, passes input right, passes weight down
         Computes: partial_sum += input × weight
         Accumulates partial sums as data flows through
```

```
TPU systolic array advantages:
  1. Data reuse: each weight is used O(output_size) times (loaded once)
  2. No register file bottleneck: data flows through PEs, not loaded/stored
  3. Regular communication: nearest-neighbor only (scalable)
  4. High utilization: ~90%+ for matrix-matrix multiply
  
Limitation: only works well for regular data-parallel operations (matrix multiply, convolutions)
  - Poor for element-wise operations, irregular access, sparse matrices
```

### TPU Generations

| TPU | Year | Process | Peak OPS | Memory | Use |
-----|------|---------|----------|--------|-----|
 v1 | 2016 | 28 nm | 92 TOPS (INT8) | 8 GB DDR3 | Inference |
 v2 | 2017 | 16 nm | 180 TOPS | 16 GB HBM2 | Training + Inference |
 v3 (Pod) | 2018 | 16 nm | 420 TOPS | 16 GB HBM2 per chip | Training (2D torus interconnect) |
 v4 | 2021 | 7 nm | 275 TOPS (BF16) | 32 GB HBM2e per chip | Training (4K-chip pods) |
 v5 (Trillium) | 2024 | 4 nm | ~1000 TOPS | HBM3 | Training + LLM inference |

## GPU Architecture Deep Dive

### CUDA Execution Model

```
CUDA hierarchy:
  Grid (1 per kernel launch)
    └─ Block (up to 1024 threads)
         └─ Warp (32 threads, executes in lockstep)
              └─ Thread (scalar execution)

Warp scheduling:
  - SM (Streaming Multiprocessor) can execute 1-4 warps concurrently
  - Scheduler selects ready warps (operands available, no dependencies)
  - Warps execute SIMT: all 32 threads execute the same instruction
  - Divergent branches: both paths are serialized (halves throughput)
```

### NVIDIA H100 SM Architecture

```
NVIDIA H100 Streaming Multiprocessor (SM):
  ┌──────────────────────────────────────────┐
  │ 128 FP32 CUDA cores (4×32 groups)        │
  │ 64 FP64 CUDA cores (2×32 groups)          │
  │ 4 Tensor Cores (per SM, 128 total)       │
  │    - FP16/TF32: 256×16×16 per cycle       │
  │    - INT8: 512×16×16 per cycle            │
  │    - FP8: 1024×16×16 per cycle            │
  │ 4 Warp Schedulers                        │
  │ Shared Memory: 228 KB (configurable)     │
  │ L1 Cache + Shared Memory combined        │
  │ Register File: 256 KB (65536 × 32-bit)   │
  │ Texture/L1 Cache: 128 KB                 │
  └──────────────────────────────────────────┘

H100 specs: 132 SMs, 60 GB HBM3, 3.35 TB/s memory bandwidth
```

### Tensor Cores

Tensor cores are matrix-multiply accelerators within each SM that operate on small matrices in a single clock cycle:

```
Tensor Core operation (H100):
  D = A × B + C
  where:
    A: [M×K] matrix (e.g., 16×16 or 8×16)
    B: [K×N] matrix
    C: [M×N] accumulator matrix
    D: [M×N] output matrix

Per tensor core per cycle:
  FP16:  256 FLOPs (16×8×16 matmul)
  TF32:  256 FLOPs 
  INT8:  512 OPS (doubled via int8 packing)
  FP8:   1024 OPS (H100 new format for LLM inference)

Total H100 tensor core throughput:
  FP16:  132 SMs × 4 TCs × 256 FLOPs × 1.83 GHz = ~2,000 TFLOPS (dense)
  FP8:   ~4,000 TOPS
```

### GPU Memory Hierarchy

```
GPU Memory Hierarchy (NVIDIA H100):

  Registers (per SM):  256 KB, 65536 × 32-bit
    ↕ (thread-private, fastest, compiler-managed)
  Shared Memory/L1:   228 KB per SM, ~1.2 μs latency, ~19 TB/s bandwidth
    ↕ (block-shared, programmer-managed or L1 cache)
  L2 Cache:           50 MB shared, ~2.5 μs latency, ~6.5 TB/s bandwidth
    ↕ (global, hardware-managed)
  HBM3:               60 GB, ~80-100 ns latency, ~3.35 TB/s bandwidth
    ↕
  System Memory:      (via PCIe/CXL, ~300-500 ns)
```

### GPU Occupancy

Occupancy measures how many warps can simultaneously be resident on an SM:

```
Occupancy calculation:
  Resources per SM: 256 KB registers, 228 KB shared mem, 64 warps max
  
  Per block (example): 512 threads, 32 KB shared mem, 2048 registers
  
  Registers limit:    256KB / 2048 bytes = 128 blocks (but max 32 blocks)
  Shared mem limit:   228KB / 32KB = 7 blocks
  Threads limit:      2048 / 512 = 4 blocks
  Warps limit:        64 / (512/32) = 4 blocks
  
  Actual max blocks per SM: min(32, 7, 4, 4) = 4
  Active warps per SM: 4 × 16 = 64 (out of 64 max → 100% occupancy)

High occupancy → better latency hiding (more warps to schedule during stalls)
But: doesn't guarantee performance (compute-bound kernels need fewer warps)
```

### CPU-GPU Coherence with CXL

```
Traditional GPU memory model (PCIe):
  CPU and GPU have SEPARATE memory spaces
  Data must be explicitly copied: cudaMemcpy()
  No cache coherence between CPU and GPU

CXL-accelerated model:
  GPU memory is CXL-attached and cache-coherent with CPU
  CPU can directly read/write GPU memory (and vice versa)
  No explicit copy needed (zero-copy)
  GPU caches CPU data via CXL.cache
  
  NVIDIA Grace Hopper (H100 + Grace CPU):
  - 900 GB/s NVLink-C2C between CPU and GPU (coherent)
  - 144 Arm Neoverse V2 cores + 96 GB HBM3 on GPU
  - 480 GB LPDDR5X on CPU (accessible from GPU via CXL/NVLink)
```

## Accelerator Virtualization and Multi-Tenancy

### GPU Sharing and Isolation

```
Challenges:
  1. A rogue process can monopolize GPU resources
  2. GPU memory is shared — one process can exhaust it
  3. GPU compute is shared — no preemptive scheduling
  4. Side-channel risk between VMs sharing a GPU

Solutions:
  | Technology | Mechanism | Vendor |
  |-----------|-----------|--------|
  | MIG (Multi-Instance GPU) | Partition GPU into 1-7 instances, each with dedicated SMs, L2, memory bandwidth | NVIDIA (A100, H100) |
  | NVIDIA MPS | Time-slice GPU between processes at warp granularity | NVIDIA |
  | SR-IOV | Expose virtual functions of GPU to multiple VMs | All GPU vendors |
  | AMD MxGPU | Hardware partitioning of AMD GPUs | AMD |
  | vGPU | VMware/Hyper-V virtual GPU scheduling | Hypervisors |
```

### MIG (Multi-Instance GPU) Details

```
H100 MIG profiles:
  1 instance:  132 SMs, 60 GB, full bandwidth
  2 instances:  66 SMs each, 30 GB each
  4 instances:  33 SMs each, 15 GB each
  7 instances: 18 SMs each, ~8 GB each

Each MIG instance has:
  - Dedicated SMs (no sharing)
  - Dedicated L2 cache slice
  - Guaranteed memory bandwidth slice
  - Independent CUDA context
  - PCIe SR-IOV virtual function

Use case: cloud providers offering fractional GPU instances
  (e.g., 1/7th of an H100 for inference workloads)
```

## Near-Data Processing (NDP) and Computational Storage

### The Idea

Instead of moving data to the CPU for processing, **process data where it lives** (in the storage device or memory):

```
Traditional:  SSD → PCIe → CPU → process → PCIe → SSD
  - Data traverses the full system for every operation
  - PCIe bandwidth is the bottleneck for data-intensive workloads

Computational Storage: SSD → (process inside SSD controller) → result → PCIe → CPU
  - Only results (not raw data) traverse PCIe
  - 10-100× less data transferred for filtering/aggregation workloads
```

### Computational Storage Examples

| Product | Vendor | Compute | Use Case |
---------|--------|---------|----------|
 Samsung SmartSSD | Samsung | ARM cores inside SSD | Video transcoding, database filtering |
 ScaleFlux CSD | ScaleFlux | FPGA + ARM | Compression, encryption |
 NGD Systems | NGD | ARM cores in NVMe | Key-value store, object store |
 AWS S3 Select | AWS | Server-side compute | SQL filtering on objects |

### Processing-in-Memory (PIM)

PIM goes even further: compute inside the memory chip itself:

```
PIM concept:
  ┌─────────────────────────────────┐
  │ DRAM Chip with PIM             │
  │  Bank 0  Bank 1  Bank 2  Bank 3 │
  │  ┌───┐   ┌───┐   ┌───┐   ┌───┐  │
  │  │PIM│   │PIM│   │PIM│   │PIM│  │  ← Compute units in/near banks
  │  │ALU│   │ALU│   │ALU│   │ALU│  │
  │  └───┘   └───┘   └───┘   └───┘  │
  └─────────────────────────────────┘

Advantage: data doesn't leave the DRAM chip
  - Saves: ~10× energy (no I/O drivers), ~10× bandwidth (internal bus)
  - Best for: simple operations on massive data (reduce, filter, scan)

Challenges:
  - Limited compute (simple ALUs, not full processors)
  - Addressing: how to invoke? (ISA extension? memory-mapped?)
  - Programming model: how to express near-data computation?

Samsung HBM-PIM (2021): adds 16 compute units per HBM channel
  - Each unit: 2 FP16 MAC units + 64 KB SRAM
  - Programmable via C++ (Samsung's PIM SDK)
  - Use cases: GEMV, sparse matrix-vector multiply, attention in transformers
```

### Disaggregated Accelerators

```
Disaggregation: separate compute from memory from acceleration

Traditional rack:
  ┌────────────────────────────┐
  │ Server 1: CPU+GPU+NVMe     │
  │ Server 2: CPU+GPU+NVMe     │
  │ Server 3: CPU+GPU+NVMe     │
  └────────────────────────────┘
  Problem: GPU utilization ~30-50%, wasted resources

Disaggregated rack:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ CPU Pool     │  │ GPU Pool     │  │ Memory Pool  │
  │ (compute)    │  │ (training)   │  │ (CXL attached)│
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                   │                  │
         └───────── CXL/InfiniBand Fabric ─────┘
  
  Benefits: resources allocated on demand
  Challenges: latency of fabric access, resource management complexity
```

## Interview Questions

### Q1: What is a DPU and how does it differ from a regular NIC?
**A**: A DPU (Data Processing Unit) has programmable ARM cores, dedicated accelerators (crypto, compression, regex), and runs its own OS. A regular NIC only handles packet reception/transmission at the hardware level. A DPU can run the entire networking stack (TCP/IP, TLS, OVS), storage stack (NVMe-oF), and security functions, offloading 20-30% of CPU cycles from the host. NVIDIA BlueField-3 and AWS Nitro are examples.

### Q2: How does a systolic array work and why is it efficient for matrix multiply?
**A**: A systolic array is a 2D grid of MAC units where data flows rhythmically through the array. Weights flow top-to-bottom, activations flow left-to-right, and partial sums accumulate. Each input is loaded once and reused across multiple PEs as it flows through. This maximizes data reuse (minimizing memory bandwidth) and uses only nearest-neighbor communication (efficient routing). A 256×256 array like TPU v1 achieves ~90% utilization for matrix multiply.

### Q3: What is GPU occupancy and why does it matter?
**A**: Occupancy is the ratio of active warps on an SM to the maximum warps it can support. High occupancy means more warps are available to hide memory latency (when one warp stalls on a memory access, another can execute). It's limited by register file size, shared memory, and thread count per SM. However, high occupancy doesn't guarantee performance — compute-bound kernels may achieve peak throughput with lower occupancy.

### Q4: Explain computational storage and its benefits.
**A**: Computational storage integrates compute (ARM cores, FPGAs) into the storage device (SSD) so that data is processed where it resides, not moved to the CPU. Benefits: (1) only filtered/aggregated results traverse PCIe, saving 10-100× bandwidth, (2) lower latency for data-intensive workloads (databases, analytics), (3) reduced CPU utilization. Example: a database filter that rejects 99% of rows — only 1% of data needs to cross PCIe.

### Q5: What is MIG and why do cloud providers need it?
**A**: Multi-Instance GPU (MIG) partitions a physical GPU into multiple isolated instances, each with dedicated SMs, L2 cache, and memory bandwidth. Cloud providers need MIG to offer fractional GPU instances (e.g., 1/4 or 1/7 of an A100) for inference workloads that don't need a full GPU. Without MIG, the only options are time-slicing (no isolation) or 1:1 passthrough (wasteful for small workloads). MIG provides hardware-level isolation between tenants.

## Summary

| Topic | Key Idea |
-------|----------|
 DPUs/Smart NICs | Offload infrastructure tasks from CPU; run TCP/IP, TLS, OVS on dedicated hardware |
 FPGAs | Reconfigurable logic; best for low-latency, deterministic, packet/video processing |
 CGRAs | Spatial computing between FPGA and GPU; word-level reconfigurable arrays |
 TPU | Systolic array for matrix multiply; 92-4000 TOPS across generations |
 GPU Deep Dive | Warp scheduling, tensor cores, occupancy, memory hierarchy |
 GPU Sharing | MIG partitions GPU hardware; SR-IOV for virtual functions |
 PIM | Compute inside DRAM; 10× bandwidth and energy for simple operations |
 Computational Storage | Process data in the SSD; reduce PCIe traffic 10-100× |
 Disaggregation | Separate CPU/GPU/memory pools connected by CXL fabric |

## Cross-References

- [GPU Basics](../parallelism/gpu.md) — GPU fundamentals
- [CUDA](../parallelism/cuda.md) — CUDA programming model
- [SIMD](../parallelism/simd.md) — Vector instruction basics
- [PCIe](../io/pcie.md) — GPU interconnect
- [NVMe](../io/nvme.md) — Computational storage interface
- [Modern Interconnects](./modern-interconnects.md) — CXL for coherent GPU access
- [Memory System Advanced](./memory-system-advanced.md) — DRAM and HBM fundamentals
- [HBM](../memory-tech/hbm.md) — HBM technology details
