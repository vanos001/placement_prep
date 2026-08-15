# HPC Infrastructure: Scheduling, Portability, and Exascale Systems

## HPC Job Scheduling

### The Role of a Resource Manager

HPC systems serve multiple users and projects competing for shared resources (compute nodes, GPUs, storage allocation). A **workload manager** allocates resources to jobs, enforces policies (fair-share, priorities, time limits), and optimizes system utilization. Unlike cloud orchestrators (Kubernetes) that manage many short-lived, loosely-coupled services, HPC schedulers handle **long-running, tightly-coupled jobs** that require specific node counts and interconnect topologies.

### Slurm

Slurm (Simple Linux Utility for Resource Management) is the dominant HPC scheduler, used at ~60% of Top500 systems including Frontier, LUMI, and most university clusters.

Key components:

- **`slurmctld` (controller daemon)**: Central scheduler. Maintains job queue, makes allocation decisions, monitors node state.
- **`slurmd` (node daemon)**: Runs on every compute node. Launches tasks, enforces resource limits, reports health.
- **`slurmdbd` (database daemon)**: Tracks historical job data for accounting and fair-share calculations.

A job submission script:

```bash
#!/bin/bash
#SBATCH --job-name=weather_sim
#SBATCH --partition=gpu
#SBATCH --nodes=64              # 64 nodes
#SBATCH --ntasks-per-node=8     # 8 MPI ranks per node
#SBATCH --gpus-per-node=4       # 4 GPUs per node
#SBATCH --time=48:00:00         # 48 hour wall time
#SBATCH --output=logs/%j.out

srun python train.py --config config.yaml
```

`#SBATCH` directives are parsed by `sbatch`. At runtime, `srun` (or `mpirun` with Slurm integration) launches the MPI ranks across the allocated nodes, setting environment variables (`SLURM_PROCID`, `SLURM_NTASKS`, etc.) that MPI uses for rank placement.

### Gang Scheduling

Many MPI jobs require **all ranks to run simultaneously** — if even one rank is descheduled, the others spin-wait or block on communication, wasting resources. Gang scheduling ensures that all tasks of a job are scheduled together (or none at all):

``nTime Slots →
Slot 1: [===== Job A (all 64 nodes) =====]
Slot 2: [=== Job B (32 nodes) ===][Job C (32 nodes)]
Slot 3: [=== Job B (32 nodes) ===][Job D (32 nodes)]

Job B is "gang-scheduled": all 32 nodes run simultaneously in each slot.
```

Slurm implements gang scheduling via the `schedule/gang` plugin. It coordinates time-slicing across nodes so that all components of a coscheduled job are active during the same time slot.

> **Interview Angle**: "Why don't HPC systems use container orchestration like Kubernetes?" — HPC jobs need gang scheduling (all ranks simultaneously), specialized interconnects (InfiniBand, NVLink), bare-metal performance (no container network overhead), and batch-oriented scheduling with priority/fair-share policies. Kubernetes optimizes for service availability and elasticity; HPC optimizes for throughput and time-to-solution.

### Backfilling

Consider a job queue: Job A needs 64 nodes for 8 hours (scheduled next), followed by Job B (4 nodes, 1 hour), Job C (8 nodes, 2 hours). Job B and C could start now on idle nodes — but only if they finish before Job A's start time. **Backfilling** identifies such opportunities:

``nAlgorithm: Conservative Backfilling
1. Find the highest-priority job that cannot start now → Job A (needs 64 nodes)
2. Estimate Job A's start time T_A (when 64 nodes free up)
3. For each lower-priority job J:
   - If J can start now AND J.wall_time + now < T_A → START J
   - If J's estimated completion would delay Job A → SKIP J

```

Slurm's default backfill scheduler uses conservative estimates (each job runs for its full requested wall time). More aggressive variants use **easy backfilling** (assume jobs may finish early) or **deadline-aware backfilling** (speculative scheduling with checkpoints).

## Checkpoint/Restart

### Why Checkpoint?

HPC jobs run for hours to weeks. Mean Time Between Failures (MTBF) for a 10,000-node system can be as low as a few hours. Without fault tolerance, a single node failure loses the entire job's progress. **Checkpoint/restart** periodically saves application state so the job can resume from the last checkpoint after a failure.

### Approaches

| Approach | Description | Overhead | Transparency |
----------|-------------|----------|-------------|
 **Application-level** | App writes its own checkpoint (e.g., model weights + optimizer state) | Minimal (selective) | Requires code changes |
 **Library-level (C/R)** | BLCR, DMTCP intercept system calls, freeze process, dump memory to file | Moderate | Mostly transparent |
 **System-level** | Kernel CR (CRIU), save full process tree + VMAs | High | Fully transparent |
 **Message-logging** | Log messages, replay after recovery | Low during run | Complex protocol changes |

For MPI applications, checkpoint must be **coordinated**: all ranks save consistent state simultaneously. The BLCR (Berkeley Lab Checkpoint/Restart) kernel module freezes all processes in the job and writes their memory to a parallel filesystem. Restart reloads all processes and re-establishes MPI connections.

### Checkpoint Interval Optimization

Checkpointing too often wastes time and I/O bandwidth. Too rarely risks losing hours of work. The **Young/Daly formula** gives the optimal interval:

```
T_optimal ≈ sqrt(2 × T_checkpoint × MTBF)
```

For MTBF = 10 hours and T_checkpoint = 5 minutes: T_optimal ≈ sqrt(2 × 0.083 × 10) ≈ 1.29 hours.

> **Interview Angle**: "How does PyTorch handle training interruption?" — PyTorch's `torch.save(model.state_dict(), ...)` saves weights. Combined with a learning rate scheduler state and optimizer state, you can resume exactly. Frameworks like DeepSpeed add asynchronous checkpointing (save to local SSD in background thread, then stage to distributed storage).

## Exascale Computing

### What is Exascale?

Exascale = 10^18 floating-point operations per second (1 EFLOPS). The first exascale systems (Frontier at ORNL, Aurora at Argonne, LUMI in Finland) achieved this milestone in 2022–2023. These systems consume 20–40 MW of power and require specialized cooling.

### Energy-Aware Computing

Power is the dominant constraint. At $0.10/kWh, a 30 MW system costs $26M/year in electricity alone. Strategies:

- **Dynamic voltage and frequency scaling (DVFS)**: Reduce CPU/GPU clock speed during memory-bound phases. NVML's `nvmlDeviceSetPowerManagementLimit` caps GPU power.
- **Power capping**: Set a power budget per node; the OS/GPU driver adjusts frequencies. Slurm's `power/gpu` plugin enforces per-job power limits.
- **Right-sizing**: Use performance models to allocate only the resources needed. Running on 50% of GPUs at full speed may be more energy-efficient than 100% of GPUs at reduced speed (due to non-linear power-performance curves).
- **Hardware**: ARM-based processors (Fugaku, Grace-Hopper) offer better performance-per-watt than x86 for many HPC workloads. Liquid cooling (direct-to-chip) handles 1–2 kW per node.

## Performance Portability

### The Problem

HPC applications must run efficiently across diverse architectures: x86 CPUs, ARM CPUs, NVIDIA GPUs, AMD GPUs, Intel GPUs. Writing separate optimized code for each is unsustainable. **Performance portability** aims to write code once and achieve near-native performance everywhere.

### Kokkos

Kokkos (Sandia National Labs) is a C++ programming model that provides a hardware-agnostic abstraction layer:

```cpp
#include <Kokkos_Core.hpp>

Kokkos::View<double**> A("A", N, N);
Kokkos::View<double**> B("B", N, N);
Kokkos::parallel_for("compute", N*N, KOKKOS_LAMBDA(const int i) {
    int row = i / N, col = i % N;
    A(row, col) = B(col, row);  // transpose
});
```

Kokkos maps the execution space (`Kokkos::Cuda`, `Kokkos::HIP`, `Kokkos::OpenMP`, `Kokkos::Serial`) at compile or runtime. The `View` abstraction handles memory allocation on the appropriate device (GPU global memory, pinned host memory) and manages data transfers. Memory spaces (`HostSpace`, `CudaSpace`, `CudaUVMSpace`) are first-class concepts.

### SYCL

SYCL (originated by Khronos, now driven by Intel oneAPI) provides single-source C++ for accelerators:

```cpp
#include <sycl/sycl.hpp>

sycl::queue q(sycl::gpu_selector_v);
sycl::buffer<float> bufA(dataA, N);
sycl::buffer<float> bufB(dataB, N);
sycl::buffer<float> bufC(dataC, N);

q.submit([&](sycl::handler& h) {
    sycl::accessor aA(bufA, h, sycl::read_only);
    sycl::accessor aB(bufB, h, sycl::read_only);
    sycl::accessor aC(bufC, h, sycl::write_only);
    h.parallel_for(N, [=](sycl::id<1> i) {
        aC[i] = aA[i] + aB[i];
    });
});
```

SYCL code compiles for NVIDIA, AMD, and Intel GPUs via respective compilers (DPC++, hipSYCL/AdaptiveCpp, triSYCL). The buffer/accessor model manages data dependencies automatically.

### Intel oneAPI

oneAPI is Intel's unified programming platform built on SYCL. It includes:

- **DPC++ compiler**: Intel's SYCL compiler (based on LLVM), targeting Intel CPUs, Intel GPUs (Arc/Ponte Vecchio), and NVIDIA/AMD GPUs via plugins.
- **oneMKL**: Math kernels (BLAS, FFT, random number generators) with SYCL interfaces.
- **oneDAL**: Data analytics library (preprocessing, algorithms).
- **oneDNN (formerly MKL-DNN/DNNL)**: Deep learning primitives (convolutions, attention) optimized for Intel hardware.

### OpenMP Offloading

OpenMP 4.0+ added target directives for GPU offloading:

```c
#pragma omp target teams distribute parallel for map(to: A[0:N]) map(from: C[0:N])
for (int i = 0; i < N; i++) {
    C[i] = A[i] * 2.0f;
}
```

The `target` directive offloads the region to a device (GPU). `map` clauses specify data transfer direction. This is the simplest path for porting CPU OpenMP code to GPUs, but performance is often lower than CUDA/HIP/SYCL due to limited control over memory hierarchy and thread mapping.

### Comparison

| Framework | Languages | Backends | Control Level | Adoption |
-----------|-----------|----------|--------------|----------|
 **CUDA** | C/C++, Python (CuPy) | NVIDIA only | Maximum | Dominant in ML/AI |
 **HIP** | C/C++ | AMD, NVIDIA (via translation) | High | AMD ecosystem |
 **SYCL/oneAPI** | C++ | Intel, NVIDIA, AMD | Medium-High | Growing (Intel push) |
 **Kokkos** | C++ | CUDA, HIP, OpenMP, Serial | Medium | HPC (DOE labs) |
 **OpenMP target** | C/C++/Fortran | All (compiler-dependent) | Low | Legacy HPC porting |
 **OpenACC** | C/C++/Fortran | NVIDIA, AMD, Intel | Low | Legacy Fortran codes |

> **Interview Angle**: "How would you port a CUDA codebase to support AMD GPUs?" — HIP provides a near-drop-in replacement: `hipify-perl` or `hipconvertinplace` automatically translates CUDA syntax to HIP. For architecture-specific optimizations (shared memory, warp intrinsics), you may need `#ifdef __HIP_PLATFORM_AMD__` guards. For true portability, consider SYCL or Kokkos for new code.

## Heterogeneous HPC

Modern HPC nodes are **heterogeneous**: CPUs + GPUs (or other accelerators). Programming models must manage:

- **Data placement**: Which memory (host vs. device) holds each data structure?
- **Task placement**: Which device executes which computation?
- **Overlap**: While GPU computes, CPU prepares next data.
- **Load balancing**: If the GPU finishes before the CPU (or vice versa), work is wasted.

The **StarPU** runtime (INRIA) automatically schedules tasks across heterogeneous resources using a task graph and performance models. Each task type has empirically-measured execution time on each architecture, and the scheduler greedily assigns tasks to the fastest available worker.

In AI training, the pattern is simpler: the GPU runs the forward/backward pass while the CPU handles data loading, augmentation, and communication scheduling. PyTorch's `DataLoader` with `num_workers > 0` and `pin_memory=True` implements this pipeline overlap.
