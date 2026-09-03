# ROCm (Radeon Open Compute)

ROCm (Radeon Open Compute) is AMD's open-source stack for GPU computing, equivalent to NVIDIA's CUDA. It was first released in 2016 and is the foundation for AMD GPU support in PyTorch, TensorFlow, and other ML frameworks. This page covers the software stack (HIP, MIOpen, rocBLAS, RCCL), the GPU architecture (CDNA), and the production differences from CUDA.

## The Stack

```text
┌─────────────────────────────────────────────┐
│  Applications (PyTorch, TensorFlow, JAX)    │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│  HIP (Heterogeneous-Compute Interface)      │
│  - C++ extension for GPU kernels            │
│  - Mostly CUDA-source-compatible            │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│  Math libraries                              │
│  - rocBLAS (BLAS)                            │
│  - MIOpen (deep learning)                    │
│  - rocFFT, rocRAND, rocSPARSE, rocThrust    │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│  Runtime (ROCr)                              │
│  - Driver interface                          │
│  - Memory management                         │
│  - Async queue management                    │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│  Linux kernel driver (amdgpu)               │
└─────────────────────────────────────────────┘
                    │
            AMD GPU hardware (MI250, MI300, ...)
```

## HIP: The CUDA-Compatible Layer

HIP (Heterogeneous-Compute Interface for Portability) is AMD's CUDA-equivalent API. It's source-compatible with CUDA for ~95% of code via the `hipify-perl` tool:

```bash
# Convert CUDA source to HIP source
hipify-perl input.cu > output.cpp
```

The conversion:
- `__global__`, `__device__`, `__shared__` are unchanged.
- `cudaMalloc` → `hipMalloc`, `cudaMemcpy` → `hipMemcpy`, etc.
- `threadIdx` → `threadIdx` (HIP uses the same names).
- `__syncthreads()` → `__syncthreads()` (HIP-compatible).

Most CUDA kernels work in HIP without manual changes. The differences are in launch syntax and some library calls.

```cuda
// CUDA
my_kernel<<<blocks, threads>>>(arg);
// HIP
hipLaunchKernelGGL(my_kernel, dim3(blocks), dim3(threads), 0, 0, arg);
// Or, with the macro:
hipLaunchKernelGGL(my_kernel, blocks, threads, 0, 0, arg);
```

The `<<<>>>` syntax is also supported in HIP via macros, but the standard form is `hipLaunchKernelGGL`.

## GPU Architectures: CDNA vs RDNA

AMD's GPUs come in two flavors:
- **CDNA** (Compute DNA): for data center compute (MI series). Optimized for FP64, FP16, INT8 matrix multiplies. Examples: MI50, MI100, MI200, MI300.
- **RDNA** (Radeon DNA): for gaming and consumer compute (Radeon series). Optimized for FP32 graphics. Examples: RX 7900 XT, etc.

ROCm is targeted at CDNA. RDNA support is partial (newer RDNA3 has improving ROCm support, but not officially).

| Architecture | Year | Process | HBM | Compute (FP16) | Notable GPU |
|--------------|------|---------|-----|----------------|---------------|
| Vega (CDNA 1) | 2017 | 14 nm | 16 GB HBM2 | 7.8 TFLOPS | MI25 |
| MI50/MI60 | 2018 | 7 nm | 16-32 GB HBM2 | 14.7 TFLOPS | MI60 |
| CDNA 2 | 2020 | 7 nm | 64-128 GB HBM2 | 47.9 TFLOPS | MI200 (MI250X) |
| CDNA 3 | 2023 | 5 nm | 128-192 GB HBM3 | 130.7 TFLOPS | MI300 (MI300X) |

The MI300X is the leading AMD GPU for LLM training/inference in 2024. Its 192 GB HBM3 (vs. NVIDIA H100's 80 GB HBM3) makes it the choice for large-model inference where the model doesn't fit on a single NVIDIA GPU.

## Library Equivalence with CUDA

| CUDA Library | ROCm Equivalent | Purpose |
|-------------|-----------------|---------|
| cuBLAS | rocBLAS | BLAS (matrix multiplication) |
| cuDNN | MIOpen | Deep learning primitives (conv, attention) |
| cuFFT | rocFFT | Fast Fourier Transform |
| cuSPARSE | rocSPARSE | Sparse matrix operations |
| Thrust | rocThrust | C++ parallel algorithms |
| cuRAND | rocRAND | Random number generation |
| NCCL | RCCL | Multi-GPU collective communication |
| Solver (cuSOLVER) | rocSOLVER | LAPACK |
| Profiler (Nsight) | ROCm Profiler | Profiling tools |

Most PyTorch/TF code that uses CUDA libraries automatically uses the ROCm equivalents when built with ROCm support.

## Production Use in ML

PyTorch has supported ROCm since 1.8 (2021). Installation:

```bash
# Install ROCm 6.0
wget https://repo.radeon.com/amdgpu-install/6.0/ubuntu/jammy/amdgpu-install_6.0.60000-1_all.deb
sudo dpkg -i amdgpu-install_6.0.60000-1_all.deb
sudo amdgpu-install --usecase=rocm

# Install PyTorch with ROCm
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0
```

PyTorch with ROCm runs the same Python code as the CUDA version. Most models work without changes.

TensorFlow has had ROCm support since 2.4 (2020). Stable but less mature than PyTorch's ROCm support.

## The Docker Image

AMD provides Docker images with pre-installed ROCm:

```bash
docker pull rocm/pytorch:latest
docker run -it --device=/dev/kfd --device=/dev/dri --group-add=video rocm/pytorch:latest
```

The `--device=/dev/kfd --device=/dev/dri --group-add=video` flags give the container access to the GPU. Without them, the container can't see the GPU.

## Comparison to NVIDIA CUDA

| Aspect | NVIDIA CUDA | AMD ROCm |
|--------|-------------|----------|
| Maturity | 15+ years | 8 years |
| Open source | Partial (driver binary blob) | Yes (entire stack) |
| Library ecosystem | Vast (cuBLAS, cuDNN, cuTensorRT, etc.) | Smaller but covers main use cases |
| Documentation | Excellent | Improving |
| Production users | Most ML projects | Stability AI, some HPC sites, OpenAI (some experiments) |
| Performance (single GPU) | H100: 990 TFLOPS FP16 | MI300X: 130.7 TFLOPS FP16 (smaller compute peak) |
| Memory bandwidth | H100: 3.35 TB/s | MI300X: 5.3 TB/s |
| Memory capacity | H100: 80 GB | MI300X: 192 GB |

ROCm's advantage: memory capacity (MI300X has 2.4× the HBM of H100). This makes MI300X the choice for LLM inference where the model exceeds 80 GB (e.g., GPT-3 175B at ~350 GB in fp16 needs 5 H100s but fits on 2 MI300Xs).

CUDA's advantage: better ecosystem, faster compute, and the fact that most ML researchers have NVIDIA hardware.

## Common Pitfalls

1. **Assuming ROCm supports all CUDA features.** New CUDA features (e.g., TMA on Hopper) may take 6-12 months to appear in ROCm. Check the release notes for the version you target.

2. **Forgetting that ROCm requires a specific kernel version.** The amdgpu driver in the Linux kernel must match the ROCm version. Use AMD's pre-built kernel modules or the kernel shipped with the ROCm package.

3. **Trusting that hipify-perl converts all CUDA code.** ~5% of CUDA code requires manual porting. The most common failures are CUDA-specific APIs without HIP equivalents.

4. **Forgetting that MI300 has two dies (CPU+GPU).** The MI300A is an APU (CPU+GPU in one package). Memory is shared between CPU and GPU; no need for explicit HBM allocation for CPU-visible data. Different from discrete GPUs.

5. **Assuming all PyTorch features work on ROCm.** Some features (e.g., `torch.compile` with specific backends) lag in ROCm support. Check the compatibility matrix.

6. **Forgetting that ROCm's NCCL is called "RCCL"** — and has minor API differences. Code that uses NCCL directly must be ported; frameworks handle this automatically.

## References

- [ROCm documentation](https://rocm.docs.amd.com/)
- [HIP documentation](https://rocm.docs.amd.com/projects/HIP/en/latest/)
- [rocBLAS GitHub](https://github.com/ROCm/rocBLAS)
- [MIOpen GitHub](https://github.com/ROCm/MIOpen)
- [PyTorch ROCm install](https://pytorch.org/get-started/locally/)
- [AMD Instinct MI300X product page](https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html)
- [Stability AI on ROCm (case study)](https://stability.ai/news/stability-ai-and-amd-collaborate-to-brain-generative-ai-workloads)
- [LWN: ROCm overview (2023)](https://lwn.net/Articles/927511/)
