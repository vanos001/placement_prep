# TPU Architecture

The Google Tensor Processing Unit (TPU) is a family of application-specific integrated circuits (ASICs) designed for neural network inference and training. The first generation was deployed in 2015 for internal workloads (RankBrain, AlphaGo); the fifth generation (Trillium, announced 2024) is the latest at time of writing. TPUs are the hardware behind Google's Bard, Gemini, and most internal ML services that need to scale beyond what GPU clusters can deliver. This page covers the systolic array core, the matrix multiply unit, the high-bandwidth memory subsystem, and the interconnect topology that distinguishes TPU v4 and v5 pods from GPU clusters.

## Why TPUs Exist

In 2013, Google projected that inference demand for speech recognition and image classification would double every few months. At the time, the company ran inference on CPUs and GPUs, and a back-of-envelope calculation showed that the projected workload would require doubling datacenter floor space if trends continued. The decision was made to build an ASIC specifically for the matrix-multiply-heavy workloads of neural networks.

The TPU v1 paper (Jouppi et al., ISCA 2017) describes the trade-off: GPUs are general-purpose parallel processors, excellent at irregular parallel workloads but paying overhead for the matrix-multiply hot path. TPUs strip everything else away: a TPU is essentially a giant 2D systolic array for matrix multiply, surrounded by a small scalar control core and high-bandwidth memory.

## The Systolic Array Core

The heart of every TPU is a **Matrix Multiply Unit (MXU)** — a 2D grid of multiply-accumulate (MAC) units that performs a single matrix multiply in O(N) cycles for NxN matrices. The TPU v1 MXU is 256×256, providing 65,536 MACs that fire in parallel on every cycle. At 700 MHz, that's 92 teraflops of 8-bit integer math per TPU.

```text
                Input weights pre-loaded (one column per cycle)
                          ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ...
                ┌────────────────────────────┐
                │  MAC  MAC  MAC  MAC  ...   │
Inputs streamed →│  MAC  MAC  MAC  MAC  ...   │→ partial sums
in rows, one    │  MAC  MAC  MAC  MAC  ...   │  accumulate
per cycle       │  ...                       │  downward
                │  MAC  MAC  MAC  MAC  ...   │
                └────────────────────────────┘
                          ▼
                       Output activations
                  (one row of output per cycle)
```

The "systolic" name comes from the rhythm of data flow: weights are pre-loaded into the array, inputs stream in from the left, partial sums accumulate downward, and outputs emerge from the bottom — all in lockstep. The hardware is **O(1) control complexity per MAC** because each MAC only sees its own input wires and its own neighbor's output.

This is the same computation as a GPU's tensor core, but a GPU tensor core is 4×4×4 = 64 MACs per SM, while a TPU MXU is 256×256 = 65,536 MACs per chip. The TPU has ~1000× more MAC throughput per chip than a GPU tensor core, but the GPU has more flexibility (can do non-matrix ops in the same code path).

## Generations

| Generation | Year | Process | MXU size | Peak (bf16) | HBM | Notable |
|-----------|------|---------|----------|-------------|-----|---------|
| TPU v1    | 2015 | 28 nm   | 256×256 (int8) | 92 TOPS (int8) | —   | Inference only, no HBM |
| TPU v2    | 2017 | 16 nm   | 128×128 ×2 (bf16) | 45 TFLOPS | 8 GB HBM | Training capable, 2 dies |
| TPU v3    | 2018 | 16 nm   | 128×128 ×2 (bf16) | 123 TFLOPS | 16 GB HBM | Liquid cooled, 2× perf |
| TPU v4    | 2020 | 7 nm    | 128×128 ×2 (bf16) | 275 TFLOPS | 32 GB HBM | 3D torus interconnect |
| TPU v5e   | 2022 | —       | —              | 191 TFLOPS (bf16) | 16 GB HBM | Cost-optimized |
| TPU v5p   | 2023 | —       | —              | 459 TFLOPS (bf16) | 95 GB HBM | Largest pod, 8960 chips |
| TPU v6e (Trillium) | 2024 | — | — | 918 TFLOPS (bf16) | 32 GB HBM | 2× perf/watt vs v5e |

A common error (and one found in the audit's review of this repo's previous version) is calling Trillium "TPU v5". Trillium is TPU **v6e**, the sixth generation. Google's [TPU v6e documentation](https://cloud.google.com/tpu/docs/v6e) and [Trillium launch blog](https://cloud.google.com/blog/products/compute/introducing-trillium-6th-gen-tpus) are explicit about the generation number.

## The HBM Subsystem

A single matrix multiply of `M × K × N = 4096 × 4096 × 4096 bf16` requires 64 MB of weights plus 64 MB of activations plus 64 MB of output — far more than any SRAM cache could hold. TPUs from v2 onwards use HBM (High Bandwidth Memory), the same stacked-DRAM technology GPUs use, but at higher capacity:

- TPU v2: 8 GB HBM at 600 GB/s
- TPU v3: 16 GB HBM at 900 GB/s
- TPU v4: 32 GB HBM at 1.2 TB/s
- TPU v5p: 95 GB HBM at 2.8 TB/s
- TPU v6e: 32 GB HBM at 1.6 TB/s

The bandwidth is critical because inference workloads are typically **bandwidth-bound on weights**: a forward pass loads the model weights once per inference, and the MXU's compute throughput can only be sustained if weights arrive at the MXU's input rate.

## The Interconnect: 3D Torus

For training at scale (LLM-scale models), a single TPU is not enough. TPUs are connected in a **3D torus** topology, where each TPU has six direct neighbors (±x, ±y, ±z) via custom optical links. A TPU v4 pod is up to 4096 chips in a 8×8×64 arrangement; a TPU v5p pod is up to 8960 chips.

```text
TPU v4 pod (8×8×8 sub-cube shown):

       ┌─────┐         ┌─────┐         ┌─────┐
       │ TPU │─────────│ TPU │─────────│ TPU │   ← x-axis
       │ 0,0 │         │ 0,1 │         │ 0,2 │
       └──┬──┘         └──┬──┘         └──┬──┘
          │                │                │       ← y-axis
       ┌──┴──┐         ┌──┴──┐         ┌──┴──┐
       │ TPU │─────────│ TPU │─────────│ TPU │
       │ 1,0 │         │ 1,1 │         │ 1,2 │
       └─────┘         └─────┘         └─────┘

(z-axis wraps around — each chip connects to ±z neighbor)
```

The 3D torus minimizes the worst-case path length between any two chips to O(N^(1/3)) for an N-chip pod. Each link is 50 Gbps per direction on v4 and 100 Gbps per direction on v5p. The total pod bisection bandwidth is the perimeter of the largest cut, scaling as O(N^(2/3)).

Compare with a GPU cluster: NVIDIA's NVLink gives 4-8 direct neighbors per GPU, but the topology is essentially a clique of 8 GPUs per "node" with InfiniBand between nodes. TPU pods are designed for hundreds-thousands of chips with no InfiniBand in the path.

## The Software Stack: XLA and JAX

TPUs run programs compiled by **XLA** (Accelerated Linear Algebra), Google's ML graph compiler. XLA takes an HLO (High-Level Optimizer) IR program, fuses elementwise + reduction ops, and emits TPU-specific machine code that schedules weights, activations, and partial sums across the MXU and HBM.

The user-facing API is **JAX** (for Python) and **TensorFlow with `tpu_strategy`**. JAX's functional programming model (no implicit state, no side effects) is the natural fit for TPU's deterministic hardware: JAX programs can be auto-sharded across a TPU pod by writing only single-chip code and letting the compiler infer the cross-chip communications needed for a multi-chip version.

## Comparison to GPUs

| Aspect | TPU v5p | H100 (SXM) |
|--------|---------|------------|
| Peak (bf16) | 459 TFLOPS | 990 TFLOPS (with sparsity) |
| Memory bandwidth | 2.8 TB/s | 3.35 TB/s |
| HBM capacity | 95 GB | 80 GB |
| Interconnect | 6×100 Gbps ICI | 18×200 Gbps NVLink |
| Pod size | 8960 chips | 256 chips (DGX SuperPOD) |
| Per-chip TDP | ~350 W | ~700 W |
| Workloads | JAX/TF | CUDA, all parallel |

The TPU's advantage is **scale**: a single pod has 35× more chips than a SuperPOD, and the per-chip power is half. For workloads that fit JAX's programming model and don't need GPU's flexibility, TPU pods win on cost-per-FLOP at scale.

The GPU's advantage is **flexibility and ecosystem**: CUDA code can run on a single GPU; TPU code requires the XLA stack. For research and for workloads that mix ML with non-ML code, GPUs win.

## Common Pitfalls

1. **Assuming TPU is faster than GPU for all ML workloads.** TPUs excel at dense matrix multiplies (transformers, convnets). They are slow on sparse or irregular computations (graph neural networks, sparse attention, Mixture of Experts with top-k > 8). The MXU's 256×256 array is idle for most of a sparse-MoE forward pass.

2. **Forgetting that TPU v1 has no HBM.** TPU v1's weights are streamed from host memory over PCIe; it's an inference-only chip with 8 GB of on-chip DRAM, not HBM. Many tutorials reference "TPU HBM" without specifying the generation, leading to confusion.

3. **Confusing TPU v4/v5 pod sizes with v5e/v5p pod sizes.** v5e is a single-host chip (no 3D torus, just host-attached); v5p is the multi-chip version. The "pod" terminology only applies to v4, v5p, and v6e+.

4. **Calling Trillium TPU v5.** Trillium is TPU **v6e** — Google's sixth generation. The "v5" name was used for v5e (cost-optimized) and v5p (performance), and Trillium is the next generation after both.

5. **Assuming the 3D torus is the same as InfiniBand.** The torus is a custom Optical Circuit Switch (OCS) topology that reconfigures at boot; InfiniBand is a packet-switched network that reconfigures per packet. The torus has lower latency but is less flexible.

## References

- Jouppi et al., "[In-Datacenter Performance Analysis of a Tensor Processing Unit](https://dl.acm.org/doi/10.1145/3079856.3080246)" (ISCA 2017) — TPU v1 paper
- Jouppi et al., "[TPU v4: The Hardware-Software Co-Design](https://arxiv.org/abs/2104.09452)" (2021)
- [Google Cloud TPU documentation](https://cloud.google.com/tpu/docs)
- [Google Trillium announcement (TPU v6e)](https://cloud.google.com/blog/products/compute/introducing-trillium-6th-gen-tpus)
- [TPU v5p pod scale: 6144 TFLOPS at 8960 chips](https://cloud.google.com/blog/products/compute-cloud/tpu-v5p)
- [JAX: High-Performance Array Computing](https://github.com/google/jax)
- [XLA: Accelerated Linear Algebra compiler](https://www.tensorflow.org/xla)
