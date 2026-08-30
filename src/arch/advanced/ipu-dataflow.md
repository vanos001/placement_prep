# Graphcore IPU: Bulk-Synchronous Dataflow Accelerators

A naming collision to clear up first: "IPU" means two unrelated devices. Intel's
Infrastructure Processing Unit -- covered in [the Intel IPU page](intel-ipu.md) --
is a DPU/SmartNIC that offloads networking from server CPUs. This page is about
Graphcore's Intelligence Processing Unit, a completely different machine: an
accelerator that puts every model weight into on-chip SRAM and runs a
bulk-synchronous-parallel (BSP) dataflow model instead of the SIMT model behind
[CUDA programming](cuda-programming.md). Its central lesson survives its commercial
failure: memory placement, not FLOPs, is the binding constraint.

## The argument against GPUs for sparse, graph-like workloads

Graphcore's founding argument (Nigel Toon and Simon Knowles, Bristol, 2016) was
that the GPU design point is wrong for a growing slice of ML workloads:

1. **SIMT lane utilization on irregular compute.** A GPU warp executes 32 lanes in
   lockstep. Dense matmuls keep every lane busy; sparse embeddings, recurrent
   models, beam search, and graph-neighborhood gathers diverge and idle lanes.
   [Tensor cores](tensor-cores.md) sharpen the dense case and leave the irregular
   case no better.
2. **Weight-refresh memory traffic.** GPU weights live in HBM and only ~40 MB of L2
   (A100 class) can hold anything, so every forward step re-streams the full weight
   set across the HBM bus. For small-to-medium models this traffic, not compute,
   sets the pace -- the same bandwidth-bound regime that motivated the
   [TPU](tpu-architecture.md) and its on-die weight staging.
3. **HBM round trips for small tensors.** Each layer's activations and
   intermediates take a round trip to a memory orders of magnitude higher-latency
   than SRAM. A model made of many small ops (LSTM chains, BERT's elementwise
   plumbing) pays this repeatedly.

The IPU bet follows directly: **build the memory hierarchy backwards** -- all the
weights in fast SRAM on-chip, and a slower, explicitly-programmed path for
anything that does not fit.

## IPU architecture: tiles and exchange memory

An IPU is a 2D mesh of identical **tiles**. Each tile is self-sufficient: one
multithreaded core (6 hardware threads) with its own local SRAM holding
instructions, weights, and that tile's working data. There is no cache and no
shared global memory -- tile SRAM is a scratchpad the programmer manages, closer in
spirit to a [systolic array's](systolic-arrays.md) tightly-coupled registers than
to a GPU SM with L1/L2.

```text
  ONE IPU, Mk2/Bow generation (~1,472 tiles)

  +----------------------------------------------------+
  | tile  tile  tile  tile  tile  tile  tile           |
  | [core][core][core][core][core][core][core]         |
  | [SRAM 624 KB each]                                 |
  |    \       \       \      /      /       /         |
  |     +-----+-----+- EXCHANGE -+-----+               |
  |     |  tile-to-tile data movement  |               |
  +-----|-------------------------------|-------------+
         off-chip: IPU-Links / PCIe Gen4 host link / IPU-Gateway -> Ethernet
```

Generations and the numbers worth quoting (per-IPU memory and compute figures are
from Graphcore's Bow-2000 datasheet on docs.graphcore.ai):

| Generation | Silicon | Tiles | SRAM per tile | Per-IPU on-chip memory | Note |
|---|---|---|---|---|---|
| Mk1 | GC2 IPU | 1,214 | 256 KB | ~304 MB | 2017-2019 era, PCIe host link |
| Mk2 | GC200 IPU | 1,472 | 624 KB | ~900 MB | IPU-M2000 machines, direct IPU-Links |
| Bow | Bow IPU | 1,474 | 624 KB | ~900 MB | 2022; stacked second die adds FPUs |

The Bow-2000 datasheet puts 4 Bow IPUs at 3.6 GB of In-Processor Memory (~900 MB
each) and 1.394 petaFLOPS of AI compute (~350 TFLOPS per IPU in FP16.16 with SR),
plus up to 256 GB of "Streaming Memory" on DDR4 -- an option that exists precisely
because on-chip capacity is finite. This shared SRAM is **exchange memory**: no
caching, all tile-to-tile movement explicit -- a program states what each tile
computes, then what to swap with neighbors between phases. On-chip exchange
bandwidth (261 TB/s per Bow-2000 machine) dwarfs the off-chip links.

The machine hierarchy has three link tiers: **IPU-Links** are direct serial links
chaining IPUs within a card or machine into one exchange fabric (the Mk1 C2 card
paired two GC2 IPUs; Mk2/Bow machines wire four IPUs together directly); **PCIe**
is the host link, where the CPU is a peer that feeds streams rather than a
supervisor in the hot loop; and scale-out runs the **IPUoF protocol** over standard
Ethernet switches through IPU-Gateway chips, so a pod is switch-topology, not a
bespoke interconnect.

## The BSP programming model

Poplar programs execute as **bulk synchronous parallel** supersteps -- Leslie
Valiant's bridging model (CACM 1990) implemented in silicon-friendly form:

```text
  time -->

  | compute | exchange | sync | compute | exchange | sync | ...
  | (local) | (move    | bar- | (local) | (move)   | bar-
  |         |  data    | rier |         |  data    | rier

  No tile touches another tile's data during compute. Cross-tile movement
  happens in the exchange phase; sync is a global barrier.
```

Three properties make BSP a good fit for ML training. All-reduce and parameter
exchange map directly to exchange phases -- gradient averaging is exactly bulk data
movement followed by a barrier, the pattern GPUs emulate with kernel-boundary
implicit barriers and NCCL collectives. With no caches there are no coherence
surprises: deterministic placement makes runs reproducible and performance analysis
tractable. And because phases are separated, the compiler can cost the whole
program from compute, exchange, and sync terms.

Contrast with [CUDA](cuda-programming.md): warp-synchronous execution hides memory
latency behind occupancy and independent instruction streams, barriers inside
kernels are best avoided, and data movement is buried under caches and async
copies. BSP makes data movement a first-class, scheduled phase instead. The cost is
architectural: every consumer of remote data waits for the next exchange.

## Poplar: software stack for a dataflow machine

The IPU is unusable without its software. **Poplar**, the graph compiler and
runtime, represents a program as a dataflow graph whose leaf operations are
**vertices** -- small C++ code fragments bound to a tile -- moving host and IPU
data through **streams**, executed as sequences of compute, exchange, and sync
stages. **PopART** is the framework-integration runtime and IR (ONNX, TensorFlow);
**PopTorch** wraps PyTorch; **PopRT** targets inference deployment. The Poplar SDK
is versioned as a unit, since compiled vertices bind to specific silicon.

## Explicit placement and the exchange cost model

Because there is no cache, the Poplar graph compiler performs **explicit code and
data placement**: it decides which tile holds every tensor and which tile runs
every vertex. Placement is an optimization problem with a visible cost model:

```text
  T_step  ~  T_compute(tiles) + T_exchange(bytes on/off each tile) + T_sync

  - T_compute:  bounded by tile FLOPs; good when tile SRAM holds the operands
  - T_exchange: bounded by IPU-Link/exchange bandwidth; grows with tensor fan-out
  - T_sync:     fixed barrier latency, paid once per superstep
```

The compiler partitions the graph to balance those terms: replicating compute
where exchange would dominate (trading SRAM for bandwidth), laying out tensors to
minimize mesh hops, inserting exchange/sync stages only where dataflow forces
them. Poplar's profiling view reports per-stage compute, exchange, and sync time.

## Where IPUs win and lose, honestly

| Workload shape | Verdict | Why |
|---|---|---|
| BERT/LSTM-era models (10M-1B params, many small ops) | Strong fit | Weights and activations fit in ~900 MB SRAM; no weight refresh; Graphcore shipped dedicated BERT fine-tuning docs |
| GNNs, temporal graph networks, sparse embeddings | Good fit | Irregular compute stays on-tile; no SIMT divergence penalty; scratchpad suits sharded embeddings |
| Classic CV (ResNet-class CNNs) | Competitive, rarely dominant | Dense convs are exactly what tensor-core GPUs do well |
| LLM training/inference (multi-GB weights) | Poor fit | Weights exceed SRAM; must stream from DDR4 Streaming Memory, eroding the founding bet |

The last row is where the bet broke. Weights that fit in on-chip SRAM arrive for
free at SRAM bandwidth and latency; weights that do not must stream over links
provisioned for activations, and the GPU's HBM advantage returns. Graphcore's own
answer, the Bow-2000's DDR4 Streaming Memory, is an admission that SRAM residency
had a size ceiling below where the industry's workloads went.

## Market reality

Graphcore raised hundreds of millions of dollars, shipped Mk1 through Bow, deployed
in academic and enterprise clusters, and still failed to out-compete NVIDIA on the
workloads that scaled hardest. In July 2024 SoftBank Group acquired the company --
Graphcore's own announcement post ("Graphcore joins SoftBank Group...") is dated
July 11, 2024, and the deal closed the same year. The lesson is not "SRAM residency
is wrong"; it is that a design point must match the *trajectory* of workloads, and
model sizes outran a fixed ~900 MB on-chip capacity. Cerebras pushed the same SRAM
bet roughly 50x further with an entire wafer as the chip (tens of GB of on-wafer
SRAM), buying capacity at the cost of yield and flexibility. The HBM-equipped
mainstream won the middle.

## Demo: a BSP cost model vs. the HBM streaming model

The model prices one layer step two ways. IPU-style supersteps cost
`compute + exchange + sync`, with weights resident while they fit in tile SRAM and
streamed from DDR4 (2x DDR4-2400, per the Bow-2000 datasheet) when they do not;
GPU-style steps re-stream weights from HBM every step, because weights never fit
in a ~40 MB L2. FLOP, capacity, and bandwidth anchors are real specs; the exchange
fraction and sync latency are labeled illustrative.

```python
# BSP superstep cost vs GPU weight-refresh cost, one layer step.
# Anchors: Bow IPU ~350 TFLOPS bf16-with-SR, ~900 MB in-processor memory,
#          2x DDR4-2400 Streaming Memory [Bow-2000 datasheet, docs.graphcore.ai]
#          A100-40GB: 40 MB L2, 1,555 GB/s HBM, 312 TFLOPS bf16 [NVIDIA datasheet]
KB, MB, GB = 1024, 1024 ** 2, 1024 ** 3

IPU_SRAM_TOTAL = 1474 * 624 * KB   # ~0.88 GiB in-processor memory per Bow IPU
IPU_PEAK = 350e12                  # bf16-with-SR FLOP/s (Bow, from 1.394 PF / 4)
IPU_STREAM_BW = 38.4e9             # 2x DDR4-2400 Streaming Memory (datasheet)
IPU_SYNC = 50e-6                   # barrier latency per superstep (illustrative)
EXCH_FRAC = 0.10                   # exchange phase = 10% of compute (illustrative)

GPU_PEAK, GPU_HBM, GPU_L2 = 312e12, 1.555e12, 40 * MB

def ipu_superstep(w_bytes):
    """T = compute + exchange + sync; weights stream only past SRAM capacity."""
    t_compute = 2.0 * w_bytes / IPU_PEAK     # one use of every weight per step
    t_exchange = EXCH_FRAC * t_compute
    if w_bytes > IPU_SRAM_TOTAL:             # SRAM overflow: stream the excess
        t_exchange += (w_bytes - IPU_SRAM_TOTAL) / IPU_STREAM_BW
    return t_compute + t_exchange + IPU_SYNC

def gpu_step(w_bytes):
    """T = max(compute, weight refresh from HBM each step)."""
    t_compute = 2.0 * w_bytes / GPU_PEAK
    t_refresh = 0.0 if w_bytes <= GPU_L2 else w_bytes / GPU_HBM
    return max(t_compute, t_refresh)

lo, hi = MB, IPU_SRAM_TOTAL               # bisect the lower (sync-floor) crossover
while hi - lo > 0.05 * MB:
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if gpu_step(mid) / ipu_superstep(mid) < 1.0 else (lo, mid)

print("GPU wins below ~%d MB (sync floor); IPU wins above, until SRAM fills." % (hi / MB))
print("\nweight set    SRAM fit   IPU step    GPU step   speedup")
for name, w in [("50 MB", 50 * MB), ("200 MB", 200 * MB), ("800 MB", 800 * MB),
                ("0.88 GiB", IPU_SRAM_TOTAL), ("2 GB", 2 * GB), ("8 GB", 8 * GB),
                ("40 GB", 40 * GB), ("175 GB", 175 * GB)]:
    ti, tg = ipu_superstep(w), gpu_step(w)
    fit = "yes" if w <= IPU_SRAM_TOTAL else "NO"
    print("%-10s   %-4s     %8.3f ms  %8.3f ms  %7.3fx" %
          (name, fit, ti * 1e3, tg * 1e3, tg / ti))
```

```text
GPU wins below ~74 MB (sync floor); IPU wins above, until SRAM fills.

weight set    SRAM fit   IPU step    GPU step   speedup
50 MB        yes         0.050 ms     0.034 ms    0.670x
200 MB       yes         0.051 ms     0.135 ms    2.628x
800 MB       yes         0.055 ms     0.539 ms    9.760x
0.88 GiB     yes         0.056 ms     0.606 ms   10.831x
2 GB         NO         31.460 ms     1.381 ms    0.044x
8 GB         NO        199.273 ms     5.524 ms    0.028x
40 GB        NO       1094.274 ms    27.620 ms    0.025x
175 GB       NO       4870.058 ms   120.839 ms    0.025x
```

Read the table against reality. Between the sync floor (~50 us, which is why tiny
weight sets and tiny batches lose) and the SRAM ceiling (~900 MB), SRAM residency
beats HBM weight-refresh by up to an order of magnitude, matching Graphcore's
published BERT and GNN results. Past the ceiling, DDR4 streaming at tens of GB/s
puts a 2 GB model ~20x behind an A100 re-streaming from HBM at 1.5 TB/s. The bet
was real but narrow, and model sizes kept growing.

## References

- [Graphcore documentation portal](https://docs.graphcore.ai/) -- Poplar, PopART, hardware docs; live under SoftBank
- [Bow-2000 IPU-Machine datasheet](https://docs.graphcore.ai/projects/bow-2000-datasheet/en/latest/) -- In-Processor Memory, AI compute, Streaming Memory figures
- [Poplar and PopLibs User Guide](https://docs.graphcore.ai/projects/poplar-user-guide/en/latest/) -- vertices, streams, programs, BSP execution
- [Graphcore BERT fine-tuning docs](https://docs.graphcore.ai/projects/bert-training/en/latest/) -- the workload class the architecture fit best
- [Graphcore joins SoftBank Group](https://www.graphcore.ai/posts/graphcore-joins-softbank-group-to-build-next-generation-of-ai-compute) -- July 11, 2024 acquisition announcement
- [Graphcore white papers index](https://www.graphcore.ai/resources/white-papers) -- hosts the IPU architecture white paper
- Xu et al., "[Dissecting the Graphcore IPU Architecture via Microbenchmarking](https://arxiv.org/abs/1912.03413)" -- tile, exchange, and SRAM behavior measured directly
- [Graphcore C2 Card performance for image-based deep learning](https://arxiv.org/abs/2002.11670) -- independent Mk1 benchmarks
- [Comparison of Graphcore IPUs and Nvidia GPUs for cosmology](https://arxiv.org/abs/2106.02465) -- honest head-to-head on scientific workloads
- Valiant, "A bridging model for parallel computation", Communications of the ACM 33(8), 1990 (BSP model; no stable public URL)
- See also: [TPU architecture](tpu-architecture.md) (HBM-based counter-bet), [systolic arrays](systolic-arrays.md) (lockstep primitives), [Intel IPU](intel-ipu.md) (the other "IPU"), [CUDA programming](cuda-programming.md) (SIMT contrast)
