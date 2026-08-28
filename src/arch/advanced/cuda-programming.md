# CUDA Programming Model

CUDA (Compute Unified Device Architecture) is NVIDIA's parallel computing platform, introduced in 2006. It extends C++ with new syntax for writing code that runs on NVIDIA GPUs, exposing the GPU's parallel hardware (thousands of cores, high-bandwidth memory) to the programmer. This page covers the programming model (grids, blocks, threads), the memory hierarchy, the synchronization primitives, and the modern alternatives (HIP, SYCL, OpenACC).

## The Hierarchy: Grid, Block, Thread

CUDA organizes parallel work as a 3-level hierarchy:

```text
Grid: 1, 2, or 3 dimensions of blocks.
  │
  ├── Block (0,0): 256 threads (a "thread block")
  │     ├── Thread (0,0,0)
  │     ├── Thread (1,0,0)
  │     ├── ...
  │     └── Thread (255,0,0)
  │
  ├── Block (1,0): 256 threads
  │     └── ...
  │
  ├── Block (2,0): 256 threads
  │     └── ...
  │
  └── ... (up to millions of blocks)
```

- **Grid**: the entire parallel region. A grid can have up to 2^31-1 blocks in the x dimension, 65535 in y, 65535 in z.
- **Block (Thread Block)**: a group of threads that can synchronize and share memory. Max 1024 threads per block.
- **Thread**: the smallest unit. Each thread has its own registers and local memory.

A kernel launch specifies the grid and block dimensions:

```cuda
__global__ void vector_add(float* a, float* b, float* c, int N) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < N) {
        c[i] = a[i] + b[i];
    }
}

// Launch: 256 threads per block, (N + 255) / 256 blocks
int threads_per_block = 256;
int blocks_per_grid = (N + threads_per_block - 1) / threads_per_block;
vector_add<<<blocks_per_grid, threads_per_block>>>(a, b, c, N);
```

The `<<<blocks, threads>>>` syntax is a CUDA-specific extension. The compiler translates it to a kernel launch API call.

## The Memory Hierarchy

CUDA threads access memory through several layers:

| Memory | Scope | Latency | Size | Caching |
|---------|-------|---------|------|---------|
| Registers | per-thread | 1 cycle | ~255 per thread | None (in registers) |
| Local memory | per-thread | 100 cycles | Unlimited (in HBM) | L1/L2 cache |
| Shared memory | per-block | 30 cycles | 100 KB (configurable) | None (explicit) |
| Global memory (HBM) | per-grid | 400 cycles | 16-80 GB | L2 cache |
| Constant memory | per-grid | 5 cycles (cached) | 64 KB | Constant cache |
| Texture memory | per-grid | 100 cycles (cached) | Unlimited | Texture cache |

Shared memory is the key optimization: it's fast (30 cycles vs. HBM's 400 cycles), shared by all threads in a block, and explicitly managed by the programmer.

```cuda
__global__ void matrix_multiply(float* A, float* B, float* C, int N) {
    __shared__ float As[16][16];
    __shared__ float Bs[16][16];
    
    int tx = threadIdx.x, ty = threadIdx.y;
    int row = blockIdx.y * 16 + ty;
    int col = blockIdx.x * 16 + tx;
    
    float c = 0.0f;
    for (int t = 0; t < N / 16; t++) {
        // Load A and B tiles into shared memory
        As[ty][tx] = A[row * N + t * 16 + tx];
        Bs[ty][tx] = B[(t * 16 + ty) * N + col];
        __syncthreads();
        
        // Compute the partial result
        for (int k = 0; k < 16; k++) {
            c += As[ty][k] * Bs[k][tx];
        }
        __syncthreads();
    }
    
    C[row * N + col] = c;
}
```

This is the tiled matrix multiplication: tiles of `16x16` are loaded into shared memory once, then reused 16 times by the threads in the block. The HBM bandwidth is amortized.

## Synchronization

- `__syncthreads()`: intra-block barrier. All threads in the block must reach the barrier before any proceed. Used after shared memory writes to ensure visibility.
- `__threadfence()`: memory fence. Ensures writes are visible to other threads (across the grid). Used for inter-block coordination via global memory.
- `__threadfence_block()`: block-level memory fence. Only ensures visibility within the block.

The lack of grid-wide synchronization in CUDA (no `__syncthreads_grid()`) is a fundamental constraint: kernels must complete before launching the next kernel. CUDA 9's "Cooperative Groups" feature adds grid-wide sync, but requires the kernel to fit in a single grid (limit: 79% of SMs occupied).

## Warp Divergence

Threads within a block execute in warps of 32 (NVIDIA) or wavefronts of 64 (AMD). All threads in a warp execute the same instruction at the same time. If a conditional causes warp divergence (e.g., `if (tid < 16) ... else ...`), both branches are executed serially for the appropriate threads.

```cuda
__global__ void divergent_kernel(int* a, int N) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid < N / 2) {
        a[tid] = 1;     // executed by first 16 threads in the warp
    } else {
        a[tid] = 2;     // executed by last 16 threads in the warp
    }
    // The warp executes BOTH branches, masking off threads not in the active branch.
}
```

Performance impact: divergence halves the warp throughput. To avoid, structure code so warps don't diverge, or use predication.

## Streams and Asynchronous Execution

CUDA operations are asynchronous by default. A kernel launch returns immediately; the CPU can do other work while the kernel runs. Synchronization happens via:

- `cudaDeviceSynchronize()`: wait for all outstanding work.
- `cudaStreamSynchronize(stream)`: wait for work in a specific stream.
- `cudaEventSynchronize(event)`: wait for a specific event.

```cuda
cudaStream_t stream1, stream2;
cudaStreamCreate(&stream1);
cudaStreamCreate(&stream2);

// Launch on stream1
my_kernel<<<blocks, threads, 0, stream1>>>(...);

// Launch on stream2 (runs concurrently with stream1)
my_kernel<<<blocks, threads, 0, stream2>>>(...);

cudaDeviceSynchronize();
```

Multiple streams enable concurrent kernel execution. The GPU schedules warps from different streams to fill idle SMs.

## Modern CUDA: Cooperative Groups

CUDA 9 (2017) introduced "Cooperative Groups", a more flexible synchronization API:

```cuda
#include <cooperative_groups.h>
using namespace cooperative_groups;

__global__ void kernel(int* a, int N) {
    thread_block block = this_thread_block();
    
    // Synchronize within the block
    sync(block);
    
    // Synchronize across the grid (cooperative launch)
    grid_group grid = this_grid();
    sync(grid);
}
```

Cooperative groups let you synchronize at any granularity (warp, block, cluster of blocks, or grid). They require the kernel to be launched with `cudaLaunchCooperativeKernel`, which limits the grid to fit in the GPU's SMs.

## Alternatives to CUDA

- **HIP** (AMD): CUDA-like API for AMD GPUs. Drop-in for most CUDA code via `hipify-perl`. Used in PyTorch's ROCm backend.
- **SYCL** (Intel): a C++ abstraction over multiple accelerators (NVIDIA, AMD, Intel). Code is portable across vendors.
- **OpenACC**: directive-based (like OpenMP but for GPUs). Higher-level than CUDA but slower.
- **OpenMP target**: see [OpenMP page](../../hpc/openmp.md).
- **Triton** (OpenAI): a Python-based DSL for writing GPU kernels. Used in modern ML frameworks.

For ML libraries (PyTorch, TensorFlow), the back-end is usually CUDA-specific code (cuBLAS, cuDNN), with HIP, SYCL, and OpenMP as alternatives for portability.

## Common Pitfalls

1. **Forgetting `cudaDeviceSynchronize()` before reading results.** Kernel launches are async; reading the result immediately returns stale data.

2. **Choosing the wrong block size.** 256 threads per block is a sweet spot for many kernels. Too small (32) underutilizes the SM; too large (1024) reduces parallelism.

3. **Ignoring memory coalescing.** Adjacent threads should access adjacent memory addresses (e.g., `a[tid]` not `a[tid * stride]`). Otherwise, the GPU issues separate memory transactions per thread, wasting bandwidth.

4. **Forgetting to free GPU memory.** `cudaFree(ptr)` is required; otherwise, the GPU leaks. RAII wrappers (like `std::unique_ptr` with custom deleters) help.

5. **Using `__syncthreads()` in conditional branches.** If only some threads take the branch, the others wait forever. All threads in the block must reach `__syncthreads()`.

6. **Confusing shared memory and global memory.** Shared memory (`__shared__`) is fast and per-block; global memory (`__device__` without `__shared__`) is slow and per-grid. Mixing them up leads to wrong or slow code.

## References

- [NVIDIA CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [NVIDIA CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- Kirk & Hwu, "[Programming Massively Parallel Processors](https://www.elsevier.com/books/programming-massively-parallel-processors/kirk/978-0-12-415992-1)" (4th edition, 2022) — textbook
- [Mark Harris's CUDA tutorials](https://developer.nvidia.com/blog/tag/cuda/)
- [Cooperative Groups documentation](https://docs.nvidia.com/cuda/cooperative-groups/index.html)
- [HIP: AMD's CUDA-equivalent](https://github.com/ROCm/HIP)
- [Triton: OpenAI's GPU DSL](https://github.com/openai/triton)
- [LWN: Modern CUDA (2023)](https://lwn.net/Articles/927507/)
