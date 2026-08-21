# Systolic Arrays

A systolic array is a 2D (or sometimes 1D or 3D) grid of compute units that pass data rhythmically between neighbors in lockstep. The name comes from the analogy to a heart pumping blood: data "pulses" through the array, with each compute unit doing a fixed operation on its inputs and forwarding the result. Systolic arrays are the architectural basis for Google's TPU MXU, NVIDIA's tensor cores, and most domain-specific accelerators for ML inference. This page covers the design pattern, the canonical matrix multiply implementation, and why the pattern is so effective for regular compute.

## The Basic Pattern

Consider a 1D systolic array for a vector dot product `y = a · b`:

```text
   a_0   a_1   a_2   a_3
    │     │     │     │
    ▼     ▼     ▼     ▼
   [M]──→[M]──→[M]──→[M]──→ y (output)
    ▲     ▲     ▲     ▲
    │     │     │     │
   b_0   b_1   b_2   b_3
```

Each `[M]` is a multiply-accumulate (MAC) unit. At cycle t:
- Each `[M]` receives a_i and b_i from above/below.
- Computes `partial += a_i * b_i`.
- Forwards `partial` to the right.
- Forwards `a_i` and `b_i` to the next MAC (if needed elsewhere).

After N cycles, the rightmost MAC outputs `a_0*b_0 + a_1*b_1 + ... + a_{N-1}*b_{N-1}`. The total work is N MACs done in N cycles — not N^2 — because every MAC is busy every cycle. This is the systolic advantage: throughput = 1 MAC/cycle/MAC-unit.

## 2D Systolic for Matrix Multiply

The 2D systolic for `C = A × B` (where A is M×K and B is K×N) uses a K×K array (or M×N, depending on layout):

```text
Matrix A (M×K)               Matrix B (K×N)
   a_00 a_01 a_02 ...         b_00 b_01 b_02 ...
   a_10 a_11 a_12 ...         b_10 b_11 b_12 ...
   ...                        ...

      │  weights pre-loaded into the array
      ▼
   ┌────────────────────────────────────────────┐
   │                                            │
A  │  MAC_00   MAC_01   MAC_02   ...            │  B
s  │   │        │        │                      │  s
t  │   ▼        ▼        ▼                      │  t
r  │  MAC_10   MAC_11   MAC_12   ...            │  r
e  │   │        │        │                      │  e
a  │   ▼        ▼        ▼                      │  a
m  │  MAC_20   MAC_21   MAC_22   ...            │  m
e  │   ...                                     │  e
d  │                                            │  d
   │                                            │
   └────────────────────────────────────────────┘
                            │
                            ▼
                      Matrix C (M×N)
                 Output accumulates downward
```

The TPU's MXU is a 256×256 systolic array (TPU v1) or 128×128 (v2+). Each MAC receives one element of A from the left, one element of B from above, accumulates `C_ij += A_ik * B_kj`, and passes the partial C down to the next row. After K cycles, the bottom row of MACs holds the final C matrix.

## Why It's Efficient

A systolic array achieves near-peak throughput because:

1. **No control overhead.** Each MAC's control logic is a fixed finite state machine: "every cycle, read inputs, compute MAC, forward outputs". No instruction fetch, no branch prediction, no register file pressure. The MAC utilization is ~100%.

2. **Local communication.** Each MAC talks only to its immediate neighbors (left, right, up, down). Wires are short, capacitance is low, and clock rates can be high (TPU v1: 700 MHz; v4: ~1 GHz).

3. **Pipelined memory access.** Each input is loaded once from HBM, then re-used N times as it propagates through the array. A single 256-element row of A is used by 256 MACs in 256 cycles — 1 HBM load amortized across 256 MAC operations.

4. **Deterministic timing.** The array runs in lockstep, so the latency of any computation is exactly K cycles (for a K×K matrix multiply). This is critical for real-time ML inference workloads.

## Wavelength and Wavefront

For a 2D systolic array of size N×N computing C = A × B (both N×N), the array takes ~3N cycles from first weight load to last output:

- Cycles 0 to N: load weights into the array.
- Cycles N to 2N: stream A and B inputs through the array.
- Cycles 2N to 3N: drain the array's partial sums to the output.

This is the **wavefront**: the diagonal front of active MACs that sweeps across the array. For a 256×256 TPU MXU at 700 MHz, the total time is ~1.1 µs for a 256×256 matrix multiply — a peak of 92 TOPS int8.

## Variants: Output-Stationary, Weight-Stationary, Row-Stationary

Three classic dataflow patterns:

1. **Output-stationary**: each MAC holds a partial sum of C stationary in its register; A and B flow through. The TPU MXU is output-stationary (well, the partial sums do flow downward in the v1, but the output is at the bottom of each column — effectively output-stationary with downward flow).

2. **Weight-stationary**: each MAC holds one weight element stationary; A flows through, and B accumulates. Useful when weights are reused across many inferences (CNN convolutions).

3. **Row-stationary**: (Eyeriss architecture, MIT 2016) — each row of MACs holds one row of weights stationary; activations flow vertically. Optimizes for energy efficiency over throughput.

The choice of dataflow determines:
- Memory bandwidth requirements (weight-stationary minimizes weight loads).
- Register pressure (output-stationary needs more registers per MAC).
- Energy efficiency (row-stationary is most energy-efficient; output-stationary is fastest).

## Beyond Matrix Multiply: Convolutions

CNN convolutions are 4-dimensional (output channels × input channels × kernel_height × kernel_width) but can be reduced to matrix multiply via the **im2col** transform:

```text
Conv: O[c_out, h, w] = sum_{c_in, kh, kw} I[c_in, h+kh, w+kw] * K[c_out, c_in, kh, kw]

im2col: reshape I into a 2D matrix I'[c_in*kh*kw, h*w]
        reshape K into a 2D matrix K'[c_out, c_in*kh*kw]
        Compute O' = K' * I'  (a matrix multiply)
        Reshape O' back to O[c_out, h, w]
```

Once conv is reduced to matrix multiply, a systolic array processes it directly. The cost is memory: im2col inflates the input by ~K²× (the kernel size). For 3×3 conv, this is 9×; for 7×7, 49×.

Modern GPUs avoid im2col by using **direct convolution** kernels in tensor cores (cuDNN's `conv_bwd` and `conv_fwd` paths). The TPU v4 and v5 support direct convolution natively via the XLA compiler, which lowers convs into MXU operations without im2col.

## When Systolic Arrays Don't Help

Systolic arrays are good at:
- Dense matrix multiply (GEMM)
- Dense convolution
- Tensor contractions (einsum with dense operands)

They are bad at:
- **Sparse computation**: if A or B is sparse, most MACs sit idle. Sparse tensor cores (Hopper's `wmma.sp` and Ampere's structured sparsity) help but only support 2:4 sparsity (50% zero in a fixed pattern).
- **Irregular control flow**: no if-else support; the array does the same operation every cycle.
- **Small matrices**: the wavefront takes N cycles to fill; for a 16×16 matrix on a 256×256 array, the array is ~93% idle.
- **Non-multiply-reducible ops** (softmax, layernorm, attention scores). These run on the GPU's CUDA cores or the TPU's vector unit, not the systolic array.

This is why TPUs and GPUs both have a mix of systolic arrays (for matrix ops) and scalar/vector units (for everything else). The hardware split is roughly 80% systolic / 20% vector for ML-focused chips.

## Common Pitfalls

1. **Assuming "systolic" means "matrix-multiply only".** The pattern is general — there are systolic arrays for sorting, for sorting networks, for FFT, for dynamic programming. But ML-focused chips use systolic arrays almost exclusively for matrix multiply because that's the dominant workload.

2. **Treating a 256×256 array as 65,536 cores.** The MACs are not general-purpose; they cannot run independent programs. A 256×256 systolic array does 1 operation (matrix multiply) at 65,536 MACs/cycle, but the "65,536 cores" framing is misleading because the array cannot do anything else.

3. **Forgetting that the wavefront startup cost is paid per matrix multiply.** A workload of many small matrix multiplies (e.g., batched MLP for transformers with batch=1) underutilizes the array. A workload of few large matrix multiplies (e.g., training with batch=1024) saturates it. This is why inference throughput is lower per-FLOP than training throughput on TPUs.

4. **Overestimating tensor-core throughput on sparse workloads.** The H100's "990 TFLOPS with sparsity" assumes 2:4 structured sparsity in the weights. Real-world sparse attention in LLMs often has 80%+ sparsity with irregular patterns; the tensor core cannot exploit this.

5. **Conflating systolic arrays with SIMD.** A SIMD unit (e.g., AVX-512) does the same operation on multiple data lanes from a single instruction stream. A systolic array does the same operation on multiple data flows from multiple neighbors — fundamentally a data-flow model, not an instruction-stream model.

## References

- H.T. Kung, "[Why Systolic Architectures?](https://www.cs.cmu.edu/~fp/courses/15281-s07/lectures/kung-why-systolic-1982.pdf)" (IEEE Computer, 1982) — the original paper
- Jouppi et al., "[In-Datacenter Performance Analysis of a TPU](https://dl.acm.org/doi/10.1145/3079856.3080246)" (ISCA 2017)
- [Eyeriss: A Spatial Architecture for Energy-Efficient Dataflow for CNNs](https://arxiv.org/abs/1612.00707) (ISCA 2016) — row-stationary dataflow
- [Systolic Arrays: The TPU's compute engine](https://cloud.google.com/tpu/docs/system-architecture)
- [CUTLASS: GEMM code generation for tensor cores](https://github.com/NVIDIA/cutlass)
- [LWN: "Systolic arrays and the limits of specialization" (2020)](https://lwn.net/Articles/816221/)
