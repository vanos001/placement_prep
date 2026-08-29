# SYCL and oneAPI: Portable Heterogeneous Computing

[CUDA](../arch/advanced/cuda-programming.md) locks kernels to one vendor, [HIP](../arch/advanced/rocm.md) trades NVIDIA lock-in for AMD lock-in, and OpenMP target spreads the compiler's attention thin. SYCL is the standards-track answer in between: host and device code live in one C++ file, the language is standardized at Khronos rather than owned by a vendor, and no single company owns the only conforming implementation. This page covers the programming model, the buffer/accessor vs USM duality, the backend landscape (DPC++, Codeplay plugins, AdaptiveCpp), the oneAPI toolkit, and the porting economics an interviewer probes.

## What single-source actually changes

CUDA splits host from device code at the toolchain level: `nvcc` compiles `.cu` files, `gcc` compiles the rest, `cudaMemcpy` glues them. SYCL collapses that split into one C++ program one compiler pass understands end to end:

```text
CUDA toolchain                          SYCL toolchain
------------------                      --------------------------------------
host.cpp  --> gcc        -> binary      app.cpp --> DPC++ or AdaptiveCpp
kern.cu   --> nvcc       -> binary                 |  (device code = C++ lambdas)
           cudaMemcpy()                            |--> backends: Level Zero, CUDA,
                                                       HIP, OpenCL, OpenMP (CPU)
```

History in three lines: SYCL 1.2 (2015) still looked like OpenCL with nicer host bindings; SYCL 2020 (ratified February 2021) rebuilt it as modern single-source C++ and made USM a core feature; the spec is still revised in place, with revision 12 published August 6, 2026. (The Khronos registry blocks scripted fetches with HTTP 403, so that revision was confirmed via search indexing rather than a direct probe; every other URL on this page returned 200.)

## Queues, and the buffer/accessor vs USM duality

Everything in SYCL 2020 runs on a `sycl::queue` binding a device, a context, and an async submission model. The default queue is out-of-order - independent command groups may overlap, which CUDA streams make you opt into. The 2020 revision's biggest ergonomic evolution is two ways to express data:

| Dimension | buffer + accessor (SYCL classic) | USM (SYCL 2020 core) |
|---|---|---|
| Allocation | `buffer<float>` owns data, mode-driven | `malloc_device/shared/host`, raw pointers |
| Dependency tracking | runtime reads accessors per command group | you express it via events/`wait()` |
| Data movement | runtime inserts transfers for you | explicit `memcpy`, or shared migrations |
| Mental model | dataflow graph, declarative | pointers, CUDA-like, imperative |
| Best for | task-graph codes, correctness first | porting CUDA code, pointer-heavy code |

```cpp
// Same stencil, both styles (SYCL 2020)
q.submit([&](sycl::handler &h) {
  sycl::accessor in(in_buf, h, sycl::read_only);      // deps derived automatically
  sycl::accessor out(out_buf, h, sycl::write_only);
  h.parallel_for(N, [=](auto i) { out[i] = f(in[i]); });
});
float *in = sycl::malloc_device<float>(N, q);           // USM style
q.parallel_for(N, [=](auto i) { out[i] = f(in[i]); });  // lifetimes are yours
```

Which would you pick? Strong answer: USM for porting CUDA and pointer-chasing workloads; buffer/accessor when you want the runtime to derive the dataflow graph, because it can fuse transfers and expose overlap you would otherwise hand-schedule.

## Kernels: lambdas, parallel_for, and ranges

Kernels are lambdas or functors - no kernel language, no string compilation as in OpenCL. `parallel_for(range)` is a flat index space with a runtime-chosen launch config (simple, but no local-memory control); `parallel_for(nd_range)` is the direct analogue of CUDA's grid/block:

```cpp
// CUDA:  kern<<<blocks, threads>>>(d);  idx = blockIdx.x*blockDim.x+threadIdx.x
q.parallel_for(sycl::nd_range<1>(blocks * threads, threads),
  [=](sycl::nd_item<1> it) {
    auto idx  = it.get_global_id(0);   // == blockIdx.x*blockDim.x+threadIdx.x
    auto lane = it.get_local_id(0);    // == threadIdx.x
  });
```

Reductions are built in (`sycl::reduction` as a `parallel_for` argument), so the hand-rolled warp-shuffle reduction that dominates CUDA porting effort often disappears - the cost model below makes this concrete. Sub-groups (SYCL's explicit warp/wavefront handle) are where the remaining SIMT-intrinsic effort lives.

## One standard, many compilers

The spec says nothing about implementation. As of August 2026, three compilers matter in HPC:

```text
                 your SYCL application
                         |
      +------------------+----------------------+
      v                  v                      v
 Intel DPC++       Codeplay plugins        AdaptiveCpp
 (intel/llvm,      bolt onto DPC++         (independent; formerly
 sycl branch)      for NVIDIA + AMD         hipSYCL / Open SYCL)
      |                  |                      |
      v                  v                      v
 Level Zero,        CUDA (NVIDIA),         generic SSCP single-pass
 OpenCL, plugins    HIP (AMD)              JIT; OpenMP/HIP/CUDA/L0
```

- **DPC++** is the open-source LLVM-based compiler (github.com/intel/llvm, `sycl` branch) behind Intel's productized oneAPI DPC++/C++ compiler. Native backends are Level Zero and OpenCL; NVIDIA and AMD GPUs work through Codeplay's plugins (announced December 2022). Honesty note: the AMD plugin tracked 2025.2 releases while community threads in late 2025 flagged the NVIDIA plugin listing as stalled at 2025.1 - plugin cadence is a real risk off the vendor's own compiler.
- **AdaptiveCpp** (github.com/AdaptiveCpp/AdaptiveCpp; the old illuhad/hipSYCL URL 301-redirects there, via the intermediate name Open SYCL) is the independent Heidelberg-born project, not an Intel effort. Its generic SSCP flow is a single-pass compiler emitting one binary that runs on NVIDIA, AMD ROCm, and Intel GPUs without per-target compilation; the project's IWOCL 2023 paper reports roughly 20% additional compile time versus single-target builds, and its README claims it is the only SYCL implementation shipping a binary with no compile-time target list. Attribute those claims to the project and benchmark on your workload - but the one-binary/many-vendors positioning is verified in their material.
- **SYCLomatic** (open-sourced by Intel, May 2022) migrates CUDA to SYCL; Intel's guidance says 90-95% of CUDA code is migrated automatically, and the repository tracks CUDA 8.0 through 12.9. The remaining 5-10% is where the work is (see the model below).

## The oneAPI toolkit in one table

| Component | Role | Replaces (in CUDA-land) |
|---|---|---|
| DPC++ compiler | SYCL 2020 + CUDA interop, productized | nvcc |
| oneMKL | BLAS, FFT, RNG, sparse with SYCL interfaces | cuBLAS, cuFFT, cuRAND, cuSPARSE |
| oneDNN | Deep-learning primitives | cuDNN |
| oneCCL | Collectives for distributed DL/HPC | NCCL (see collective-communication page) |
| SYCLomatic | CUDA -> SYCL source migration | (no CUDA analogue needed) |

## Porting economics: a cost model

Migration questions are cost questions: what does the 90-95% automatic figure leave on the table? Toy model (labeled MODEL; rules and rates are stated assumptions, not measured data). Five kernels from a CUDA mini-app, three port paths: hipify to HIP, SYCLomatic to DPC++, full rewrite under AdaptiveCpp. Vendor-library remaps are costed separately because they - not the kernels - dominate real ports:

```python
# MODEL: kernel-port effort matrix + speedup-vs-portability frontier.
# Toy rules, stated assumptions, person-day units, deterministic. Not measured data.
K = [  # (name, hand-written device LOC, vendor-lib dep, warp-intrinsic fix factor)
    ("K1 stencil",      40, "none",   0.0),
    ("K2 reduction",    60, "none",   1.0),
    ("K3 GEMM chain",   20, "cuBLAS", 0.0),
    ("K4 FFT pipeline", 25, "cuFFT",  0.0),
    ("K5 conv stack",   30, "cuDNN",  0.0),
]
LIB = {  # vendor-lib remap cost, person-days
    "HIP":                 {"cuBLAS": 1, "cuFFT": 1, "cuDNN": 3},
    "DPC++/SYCLomatic":    {"cuBLAS": 2, "cuFFT": 2, "cuDNN": 5},
    "AdaptiveCpp rewrite": {"cuBLAS": 6, "cuFFT": 8, "cuDNN": 10},  # libs -> portable kernels
}
VERIFY  = {"HIP": 0.5, "DPC++/SYCLomatic": 1.0, "AdaptiveCpp rewrite": 1.5}
AUTO    = {"HIP": 0.02, "DPC++/SYCLomatic": 0.05, "AdaptiveCpp rewrite": 0.15}  # d per LOC
RETAIN  = {"HIP": 0.95, "DPC++/SYCLomatic": 0.75, "AdaptiveCpp rewrite": 0.85}  # vs tuned CUDA
VENDORS = {"HIP": 1, "DPC++/SYCLomatic": 3, "AdaptiveCpp rewrite": 3}

def cost(loc, lib, fix, path):
    kern = loc * AUTO[path] + loc * fix * (0.30 if path == "HIP" else 0.10) + VERIFY[path]
    return kern, LIB[path].get(lib, 0)

rows = {p: ({k[0]: cost(*k[1:], p) for k in K},
            sum(sum(cost(*k[1:], p)) for k in K)) for p in AUTO}

print("Per-kernel port cost (kernel-days + lib-remap-days), person-days:")
hdr = "%-22s" % "path" + "".join("%-16s" % k[0] for k in K) + "total"
print(hdr); print("-" * len(hdr))
for path, (per, total) in rows.items():
    print("%-22s" % path + "".join("%-16s" % ("%d+%d" % (round(per[k[0]][0]), per[k[0]][1])) for k in K) + "%d" % round(total))

print("\nSpeedup-vs-portability frontier (throughput = RETAIN, portability = #vendors):")
print("%-22s %10s %12s %9s %s" % ("path", "port-days", "throughput", "vendors", "pareto"))
for path, (_, total) in sorted(rows.items(), key=lambda kv: (-VENDORS[kv[0]], -RETAIN[kv[0]])):
    dom = any(VENDORS[o] >= VENDORS[path] and RETAIN[o] > RETAIN[path] and o != path for o in rows)
    print("%-22s %10d %12.2f %9d %s" % (path, round(total), RETAIN[path], VENDORS[path], "no" if dom else "YES"))
```

Real output of the run above (executed; deterministic; byte-identical on a second run):

```text
Per-kernel port cost (kernel-days + lib-remap-days), person-days:
path                  K1 stencil      K2 reduction    K3 GEMM chain   K4 FFT pipeline K5 conv stack   total
-----------------------------------------------------------------------------------------------------------
HIP                   1+0             20+0            1+1             1+1             1+3             29
DPC++/SYCLomatic      3+0             10+0            2+2             2+2             2+5             29
AdaptiveCpp rewrite   8+0             16+0            4+6             5+8             6+10            64

Speedup-vs-portability frontier (throughput = RETAIN, portability = #vendors):
path                    port-days   throughput   vendors pareto
AdaptiveCpp rewrite            64         0.85         3 YES
DPC++/SYCLomatic               29         0.75         3 no
HIP                            29         0.95         1 YES
```

HIP and SYCLomatic tie at 29 days for opposite reasons: HIP converts device code nearly free and stumbles only on warp-level code (K2's 20 days), while SYCLomatic spends more per kernel reviewing machine-translated code but kills the hand-rolled reduction via `sycl::reduction` (K2 drops to 10). The rewrite path costs more than double because dropping cuBLAS/cuFFT/cuDNN means replacing vendor libraries with portable kernels - the hidden line item in every "just use an open stack" pitch. On the frontier, the DPC++ route is dominated in this model (same vendor count as AdaptiveCpp, lower retained throughput), which mirrors the complaint that you pick DPC++ for first-party Intel support, not as the fastest non-NVIDIA path. Change the RETAIN assumptions and the frontier moves; state assumptions, then defend them.

## Portability reality: exit code 0 is not the finish line

- **Vendor-library depth.** cuDNN's Tensor Core dispatch heuristics took years of NVIDIA-only tuning. oneDNN is excellent on Intel GPUs and good elsewhere, but library parity is per-backend and per-release.
- **Feature lag on non-native backends.** New PTX features (TMA, cluster launch, latest tensor-core instructions) land in CUDA first; SYCL access on NVIDIA arrives via backend extensions or waits for plugin work.
- **Tuning asymmetry.** Compiler heuristics (work-group sizing, unrolling, register allocation) are best on their own vendor's hardware; the same source can show a 1.5-2x spread across backends with no correctness bug. AdaptiveCpp's claim is portable performance, not parity with the vendor stack everywhere.
- **Verification cost multiplies.** Every backend is another floating-point profile, another memory-model implementation, another CI leg - budget it (the VERIFY constants above) or discover the debt in production.

The surrounding infrastructure (queues, batch systems, cluster tooling) has its own page: [HPC Infrastructure](./hpc-infra.md).

## SYCL vs OpenMP target-offload: picking a positioning

OpenMP target and SYCL solve the same problem with opposite philosophies. OpenMP target wins when you have a large existing CPU OpenMP codebase (especially Fortran) and want directives as the portable layer - add `target teams distribute`, map your data, accept the performance ceiling; the mechanics are in [OpenMP](./openmp.md). SYCL wins when the GPU is the product: explicit queues give you the dataflow graph, `nd_range` gives you the memory hierarchy, and the kernel is real C++ you can template and profile. The pragmatic split in HPC centers: OpenMP target for a thousand sprinkled CPU loops that occasionally deserve a GPU, SYCL (or HIP, or CUDA) for the 5% of the code consuming 80% of the runtime. Saying exactly that, with a workload example, is a strong answer.

## The four-portability-paths comparison

| Dimension | CUDA | OpenMP target | ROCm / HIP | SYCL (DPC++) | AdaptiveCpp |
|---|---|---|---|---|---|
| Owner / spec body | NVIDIA (proprietary) | OpenMP ARB | AMD (open source) | Khronos spec, Intel impl | independent project |
| Language surface | CUDA C++ extensions | pragmas + snippets | CUDA-like C/C++ | standard C++ lambdas | standard C++ lambdas |
| Vendors reachable | NVIDIA only | NVIDIA, AMD, Intel (varies) | AMD (NVIDIA via HIP SDK) | Intel, NVIDIA, AMD via plugins | NVIDIA, AMD, Intel, CPUs |
| CUDA migration tool | n/a | n/a | hipify (high fidelity) | SYCLomatic (90-95% claim) | manual rewrite |
| Vendor-lib story | cuBLAS/cuDNN native | none built in | hipBLAS/MIOpen near-parity on AMD | oneMKL/oneDNN, maturity varies | bring-your-own or oneAPI libs |
| Perf ceiling | reference | lowest of the four | near-CUDA on AMD | backend-dependent | project claims near-vendor via SSCP |
| Killer risk | vendor lock-in | perf ceiling, data-motion bugs | Linux-first, Windows gaps | plugin cadence on non-Intel | smaller ecosystem, fewer admins know it |

## SYCL-specific pitfalls

1. Writing to a read-write accessor whose buffer was built from uninitialized host data - the runtime faithfully copies your garbage back.
2. Flat `parallel_for(range)` where you meant `nd_range` - no local memory, no barriers, a runtime-chosen launch config; the "same" kernel runs slower for a reason invisible in the source.
3. Default out-of-order queue plus USM raw pointers with no event chaining: the race exists in CUDA too, but async command groups hide it better.
4. Assuming `malloc_shared` migrations are free - coherent shared allocations across PCIe are convenience, not performance.
5. Backend `#ifdef` creep: once your "portable" kernel contains NVIDIA-only backend extensions, you have CUDA with extra steps.
6. Benchmarking the port against default nvcc builds instead of tuned CUDA; the honest baseline is vendor-tuned, not first-attempt.

## Interview questions

1. Explain the buffer/accessor vs USM trade-off and when the runtime-derived dataflow graph beats explicit event management.
2. What does SYCLomatic's "90-95% automatic migration" claim not cover, and which uncovered part dominates cost? (Library remapping; vendor-lib parity; verification.)
3. A binary built with AdaptiveCpp's single-pass flow runs on three GPU vendors. What is guaranteed, and what is not? (Execution, not performance.)
4. A grant requires the same code on an AMD-labeled and an Intel-labeled supercomputer. Walk through your stack decision and its risks, including toolchain cadence on non-native backends.

## References

- Khronos SYCL overview: https://www.khronos.org/sycl/
- SYCL 2020 Specification, revision 12, Aug 6, 2026 (registry 403s scripted fetches - revision verified via search): https://registry.khronos.org/SYCL/specs/sycl-2020/html/sycl-2020.html
- KhronosGroup SYCL-Docs: https://github.com/KhronosGroup/SYCL-docs
- intel/llvm `sycl` branch (DPC++): https://github.com/intel/llvm/tree/sycl
- oneAPI Base Toolkit: https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit.html
- oneAPI Programming Guide: https://www.intel.com/content/www/us/en/develop/documentation/oneapi-programming-guide/top.html
- Codeplay oneAPI for NVIDIA GPUs: https://developer.codeplay.com/products/oneapi/nvidia/
- Codeplay oneAPI for AMD GPUs: https://developer.codeplay.com/products/oneapi/amd/
- AdaptiveCpp (formerly hipSYCL / Open SYCL): https://github.com/AdaptiveCpp/AdaptiveCpp
- SYCLomatic: https://oneapi-src.github.io/SYCLomatic/get_started/index.html and https://github.com/oneapi-src/SYCLomatic
- Intel DPC++/C++ Compiler: https://www.intel.com/content/www/us/en/developer/tools/oneapi/dpc-compiler.html
