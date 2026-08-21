# Tensor Cores

Tensor cores are the specialized matrix-multiply units inside NVIDIA GPUs, introduced with the Volta architecture (V100, 2017) and extended in every subsequent generation. They perform small matrix multiplies (typically 4×4×4 or 8×8×4 in bf16/fp16, with fp32 accumulate) in a single cycle, providing the bulk of the GPU's deep-learning throughput. This page covers the matrix-fragment programming model (the WMMA API), the precision variants across generations, and the practical differences between tensor cores and the TPU's MXU.

## The Hardware Primitive

A tensor core is a 4×4×4 (or larger) matrix multiply-accumulate (MMA) unit. Given input matrices A (4×4), B (4×4), and accumulator C (4×4), it computes `C = A * B + C` in one cycle. The Volta tensor core does this in bf16 input/fp32 accumulate; Ampere (A100, 2020) added bf16 inputs natively and tf32 (truncated float32) and INT8/INT4 modes; Hopper (H100, 2022) added fp8.

The GPU's Streaming Multiprocessor (SM) has multiple tensor cores: V100's SM has 8 tensor cores (so 8 MMAs per cycle per SM), and there are 80 SMs on a V100 — totaling 640 tensor cores, providing 125 TFLOPS of bf16 throughput at the V100's 1.5 GHz boost clock.

## The WMMA Programming Model

Programming tensor cores directly is done via the `WMMA` (Warp Matrix Multiply Accumulate) API in CUDA, exposed in PTX as the `wmma` instruction set:

```cuda
#include <mma.h>
using namespace nvcuda;

// 16x16x16 tile
wmma::fragment<wmma::matrix_a, 16, 16, 16, __nv_bfloat16, wmma::row_major> a_frag;
wmma::fragment<wmma::matrix_b, 16, 16, 16, __nv_bfloat16, wmma::col_major> b_frag;
wmma::fragment<wmma::accumulator, 16, 16, 16, float> c_frag;

wmma::fill_fragment(c_frag, 0.0f);
wmma::load_matrix_sync(a_frag, a_ptr, 16);
wmma::load_matrix_sync(b_frag, b_ptr, 16);
wmma::mma_sync(c_frag, a_frag, b_frag, c_frag);  // C = A*B + C
wmma::store_matrix_sync(c_ptr, c_frag, 16, wmma::mem_row_major);
```

Each thread in the warp participates: a warp (32 threads) cooperates to load a tile, do the MMA, and store the result. The hardware distributes the tensor-core lanes across the warp's threads; this is why tensor cores cannot be programmed from a single thread — they're a warp-level primitive.

## CUTLASS and the Higher-Level API

Direct WMMA programming is rarely used in production. Most code uses CUTLASS (CUDA Templates for Linear Algebra), NVIDIA's open-source library that abstracts the tile shapes, data layouts, and pipelining:

```cuda
// CUTLASS GEMM
#include <cutlass/cutlass.h>
#include <cutlass/gemm/device/gemm.h>

using Gemm = cutlass::gemm::device::Gemm<
    cutlass::half_t,       // A
    cutlass::LayoutKMajor,
    cutlass::half_t,       // B
    cutlass::LayoutKMajor,
    float,                 // C
    cutlass::LayoutKMajor,
    float,                 // accumulator
    cutlass::arch::OpClassTensorOp,
    cutlass::arch::Sm80,
    cutlass::gemm::GemmShape<128, 128, 32>,    // threadblock tile
    cutlass::gemm::GemmShape<64, 64, 32>,     // warp tile
    cutlass::gemm::GemmShape<16, 8, 16>       // instruction tile
>;
```

CUTLASS is what cuBLAS, PyTorch, and TensorFlow use internally; it handles the tile scheduling, shared-memory double-buffering, and async-copy pipelining needed to saturate the tensor cores.

## Precision Variants by Generation

| GPU gen | Year | fp32 | tf32 | bf16 | fp16 | fp8 (e4m3/e5m2) | int8 | int4 |
|---------|------|------|------|------|------|-----------------|------|------|
| Volta V100  | 2017 | —   | —    | —    | ✓    | —               | —    | —    |
| Turing T4   | 2018 | —   | —    | —    | ✓    | —               | ✓    | ✓    |
| Ampere A100 | 2020 | ✓   | ✓    | ✓    | ✓    | —               | ✓    | —    |
| Hopper H100 | 2022 | ✓   | ✓    | ✓    | ✓    | ✓               | ✓    | —    |
| Blackwell B200 | 2024 | ✓ | ✓  | ✓    | ✓    | ✓               | ✓    | —    |

- **fp32**: standard single-precision math. Used for legacy code and scientific computing. ~19.5 TFLOPS on A100 (no tensor core).
- **tf32**: "TensorFloat-32" — fp32 range (8 exponent bits) but only 10 mantissa bits (like fp16). Same dynamic range as fp32, but ~10× less precision. The default for Ampere/Hopper training. 156 TFLOPS on A100.
- **bf16**: "Brain Float 16" — 8 exponent bits, 7 mantissa bits. Same dynamic range as fp32, 1-bit less mantissa than fp16. The recommended choice for transformer training. 312 TFLOPS on A100.
- **fp8 (e4m3 / e5m2)**: 4 exponent + 3 mantissa, or 5 exponent + 2 mantissa. Used for Hopper-era inference and training where the model has been calibrated. 1980 TFLOPS on H100 (e4m3).
- **int8/int4**: integer only, for inference of quantized models. 624 TOPS int8 on A100.

The general rule: use the lowest precision that the model tolerates. Most transformer training is bf16; CNN inference is int8; LLM inference (post-calibration) is fp8 on Hopper.

## The WMMA Pipeline

To saturate a tensor core, the GPU must keep it fed. Each MMA cycle consumes one A tile and one B tile, and these tiles must be loaded from shared memory (which is loaded from HBM). The pipeline:

```text
HBM (3 TB/s)  ──┐
                 │
                 ├─→ Global memory load (LDG) ──┐
                 │                               │
                 │                               ▼
                 │                          Shared memory (LDGSTS)
                 │                               │
                 │                               ▼
                 │                          L2 cache (fallback)
                 │                               │
                 │                               ▼
                 ▼                          Shared memory
            Async copy                            │
            (cp.async)                            │
                                                 ▼
                                       WMMA load (LDSM)
                                                 │
                                                 ▼
                                       Tensor core (MMA)
                                                 │
                                                 ▼
                                       WMMA store (STSM)
                                                 │
                                                 ▼
                                       Shared memory → HBM
```

The "async copy" (`cp.async`) introduced in Ampere lets the GPU pipeline HBM→shared-memory copies without going through registers. Without it, the GPU spent ~30% of cycles on data movement; with it, tensor cores can run at >80% utilization on large matrices.

## Tensor Cores vs. TPU MXU

| Aspect | Tensor core (H100) | TPU MXU (v5p) |
|--------|-------------------|----------------|
| MMA size | 16×16×16 bf16 (per warp) | 128×128 bf16 (per chip) |
| Peak (bf16) | 990 TFLOPS per GPU | 459 TFLOPS per TPU |
| Compute precision | bf16/fp16/fp8/int8 | bf16/int8 |
| Programming model | CUDA + WMMA + warp | JAX/TF + XLA |
| Data layout | Row/col-major tiles | 2D systolic, hardware-managed |
| Memory | 80 GB HBM3 | 95 GB HBM |
| Memory bandwidth | 3.35 TB/s | 2.8 TB/s |

The TPU MXU is ~1000× larger than a tensor core (65,536 vs 64 MACs per unit), but the GPU has 132 SMs each with multiple tensor cores, and the GPU's clock is higher (1.8 GHz vs ~1 GHz). Net: per-chip peak is similar, with the TPU at lower power.

The big difference is the programming model: tensor cores require explicit tile management in CUDA, while the TPU's MXU is abstracted by XLA. CUTLASS is the equivalent abstraction layer for tensor cores.

## Pitfalls

1. **Forgetting that tensor cores need warp-coherent loads.** A single thread cannot load a tensor-core tile; the warp must cooperate. Code that uses non-uniform control flow (if-else per thread) breaks the WMMA API silently.

2. **Mixing precision variants in a single program.** A `mma_sync` with bf16 inputs but fp32 accumulator works; mixing bf16 inputs with fp16 inputs fails to compile or silently produces wrong results.

3. **Not using async copies on Ampere+.** The default `LDG.SHARED` path stalls the SM on every load. Use `cp.async` (and `cp.async.bulk` on Hopper) for any HBM→shared-memory transfer that's on the tensor-core critical path.

4. **Assuming fp16 = bf16.** fp16 has 5 exponent bits (range ±65k), bf16 has 8 (range ±3.4×10^38). A model trained in fp16 may overflow when converted to bf16; a model trained in bf16 may lose precision when converted to fp16. Always know which you're using.

5. **Ignoring TMA (Tensor Memory Accelerator) on Hopper.** TMA is the hardware unit that automates the async-copy pipeline. Using it (via the `cp.async.bulk.tensor` PTX instruction) provides 2-4× throughput over manual `cp.async` for large tiles.

## References

- [NVIDIA Volta architecture whitepaper](https://images.nvidia.com/content/volta-architecture-whitepaper.pdf) (2017)
- [NVIDIA Hopper architecture whitepaper](https://resources.nvidia.com/en-us-hopper-architecture-1) (2022)
- [PTX ISA: WMMA instructions](https://docs.nvidia.com/cuda/parallel-thread-execution/#warp-level-matrix-instructions)
- [CUTLASS: CUDA Templates for Linear Algebra](https://github.com/NVIDIA/cutlass)
- [NVIDIA cuBLAS documentation](https://docs.nvidia.com/cuda/cublas/)
- [How to use tensor cores in PyTorch](https://pytorch.org/docs/stable/notes/cuda.html#tensor-cores)
- [LWN: "Tensor cores and the limits of GPU specialization" (2018)](https://lwn.net/Articles/751124/)
