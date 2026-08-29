# OpenACC: Directives-First GPU Porting

OpenACC is a directives-based accelerator programming model first published in November 2011 by Cray, CAPS, NVIDIA, and PGI, and standardized since by the OpenACC organization. You annotate existing C, C++, or Fortran loops with `#pragma acc` / `!$acc` hints and the compiler generates the kernels, the launches, and the data motion. That "port first, optimize later" contract is the whole identity of the model: it competes with hand-written [CUDA](../arch/advanced/cuda-programming.md) on porting cost, not on peak throughput, and with [OpenMP target](./openmp.md) and [SYCL](./sycl-oneapi.md) on how much of the machine the programmer must manage explicitly. The current specification is 3.4 (June 2025), and its strongest user base remains large Fortran science codes. This page covers the three-level execution model, `parallel` vs `kernels`, the data clauses and their structured/unstructured split, async queues, an executed porting-order model, and an honest account of the overheads versus hand-CUDA.

## One directive set, three parallelism levels

OpenACC defines an accelerator as a set of processing elements (PEs) and gives every loop three knob layers:

| Level | Clause | Granularity | NVIDIA GPU analogue |
|---|---|---|---|
| gang | `gang(num)` | coarse, independent | thread block (`blockIdx.x`) |
| worker | `worker(num)` | cooperates within a gang | warp (block y-dimension) |
| vector | `vector(num)` | SIMD lanes within a worker | thread (`threadIdx.x`) |

The specification is deliberately implementation-agnostic -- it never says "gang = block". The concrete mapping is the compiler's choice, and NVIDIA's is documented: the HPC SDK reference defines `NVCOMPILER_ACC_GANGLIMIT` as "the maximum number of gangs (CUDA thread blocks) that will be launched by a kernel", and the compiler's own feedback annotates a generated loop as `gang, vector(128) /* blockIdx.x threadIdx.x */`. Training material from the NVIDIA/OLCF OpenACC course states it directly: "an OpenACC gang is a threadblock, a worker is effectively a warp, and an OpenACC vector is a CUDA thread."

The default launch is worth memorizing because it explains most "why is my kernel slow" questions. Compile a vector add with `nvfortran -acc -Minfo` and a runtime report looks like:

```text
num_gangs=7813  num_workers=1  vector_length=128  grid=7813  block=128
```

One worker per gang: a block of 128 vector lanes -- four hardware warps with no worker-level parallelism inside the block. A default OpenACC kernel uses a fraction of an SM's warp slots, so occupancy tuning means adding `num_workers(...)` / `vector_length(...)` / `num_gangs(...)` clauses until the geometry fits the loop nest -- or fusing nest levels with `collapse(n)`. None of this is optional knowledge just because the code has no `<<<>>>` in it.

## parallel loop vs kernels: who asserts parallelism

Two compute constructs take the same clauses and mean different contracts:

| Dimension | `parallel loop` | `kernels` |
|---|---|---|
| Who finds parallelism | you assert it per loop | compiler analyzes the region |
| If you are wrong | race, silently | loop just runs serial on the device |
| Kernel launches | one per region (loops fused) | possibly several, one per independent loop |
| Data clauses | must be present, or inherited from enclosing `data` | implied present-or-copy per referenced array |
| Execution outside loops | redundant on every gang unless marked | n/a (whole region is compiler-owned) |
| Use when | porting the hot loop, you verified the dependency | broad first sweep over a whole routine |

The trap inside `parallel` without `loop`: the region body is executed redundantly by each gang, so iterations are not distributed at all -- the "I forgot the loop directive" bug that ships in first attempts. The inverse trap in `kernels`: the compiler cannot prove every loop parallel (indirect indexing, loop-carried dependencies), leaves it serial, and the code stays correct but secretly slow; `-Minfo=accel` prints which loops became kernels and which did not, and `independent` asserts what you know. Functions called from device loops need an `acc routine` directive (with a `gang`/`worker`/`vector`/`seq` level) so the compiler generates a device version it can call.

## The data model: present-or-copy, structured vs unstructured

Directive-based porting lives or dies on data motion, and OpenACC's vocabulary is built around one default: **present-or-copy**. A `copy(A[0:N])` on a region copies the array in if it is not already on the device, and uses the existing device copy if it is -- so naive early-porting code is correct even while it re-copies everything per loop, and later stages replace copies with `present`.

| Clause | Meaning |
|---|---|
| `copyin` / `copyout` / `copy` | H2D / D2H / both at region boundaries |
| `create` | allocate device memory, no transfer |
| `present` | assert device copy exists (error if not) |
| `deviceptr` | raw device pointer, unmanaged |
| `attach` / `detach` | wire up pointer members of structs/derived types (deep-copy support) |
| `update host` / `update device` | one-directional sync directive, usable anywhere |
| `host_data use_device(...)` | grab device addresses inside a host block (hand cuBLAS a device pointer) |

The **structured** form is the `acc data copy(...)` region: motion happens at its entry and exit, covering everything inside -- the shape you want around a timestep loop. The **unstructured** form is `acc enter data copyin(...)` and `acc exit data copyout(...)`/`delete`: placement split across functions, which is how you keep device arrays alive across call trees in code where one function initializes and another finalizes (the standard pattern for Fortran module arrays and long-lived simulation state). Between the two ends, `update` moves freshly produced values, and `wait` fences async work.

The biggest silent cost in early ports is uncovered data motion: without a covering data region, every `parallel loop` applies its own present-or-copy per referenced array, so the compiler feedback sprays `Generating copyin(a[:n])` lines and each timestep pays host-device round trips for arrays that never change. The fix is a structured region -- or NVIDIA's **managed memory**: compiling with `-gpu=managed` puts data-clause allocations and dynamic allocation into CUDA managed memory, so copies become no-ops and the runtime migrates pages on demand. That is an NVIDIA-only convenience (the HPC SDK documents Managed/Unified memory modes in its memory-model chapter, and in unified mode the copy clauses "will not result in any device allocation or data transfer"), it trades explicit control for page-fault and migration costs that bite hardest in multi-GPU and bandwidth-bound loops -- the honest position is: managed memory for correctness bring-up, explicit data clauses for the tuned build.

## async queues and wait

Every compute or data region takes `async(n)`, which enqueues it on an integer-labeled asynchronous queue instead of blocking the host. NVIDIA maps these queues onto CUDA streams (`acc_get_cuda_stream` returns the stream backing a queue, and you can substitute your own stream). `wait(n)` blocks for one queue, bare `wait` for all, `acc_wait_all()` from library code; `NVCOMPILER_ACC_SYNCHRONOUS=1` disables the whole machinery for debugging.

What async actually buys: overlapping the halo/staging copies of step k with the kernels of step k+1, keeping the copy engines and the SMs busy simultaneously, and interleaving MPI progress on the host while device work runs. It buys nothing when the step is compute-bound with trivial transfers -- which is exactly what the model below shows.

## The porting ladder, in the order that pays

The standard OpenACC campaign runs in three moves, and the order is the point:

1. **Serial baseline + profile.** Find the loops that own the runtime; compile untouched code with `-acc -Minfo=accel` to see what the compiler would offload.
2. **Parallelize the hot loops.** Add `parallel loop` (or `kernels`) to the top profiled loops. Present-or-copy keeps this correct immediately -- and slow, because data motion is per-region.
3. **Hoist data motion.** Wrap the outer loop (timestep, iteration) in `acc data` / `enter data`, replace copies with `present`, then tune geometry (`collapse`, `num_workers`, `vector_length`) and add `async`.

Porting in the other order -- data clauses first, hot loops later -- produces a program that moves everything and computes almost nothing on the device, and teaches exactly the wrong lesson. The model below puts numbers on each rung; it is a stated-assumptions accounting exercise, not a benchmark.

## MODEL: directive-coverage speedup per porting stage

```python
# MODEL: Amdahl-style directive-coverage accounting for an OpenACC porting campaign.
# Stated assumptions, not measurements: synthetic per-iteration costs; effective PCIe
# copy bandwidth 7.5 GB/s with a fixed 8.5 us setup per copy; 5 us per kernel launch.
# One timestep is the unit of account. The Amdahl ceiling assumes free offload and
# free motion, i.e. it is set only by the un-clause-able serial fraction.
PCIE, COPY_FIX, LAUNCH = 7.5e9, 8.5e-6, 5e-6
LOOPS = [
    # (name,   kind,       trip_count, cpu_ns/iter, gpu_ns/iter, bytes_moved_per_step)
    ("flux",    "parallel",  2_000_000, 40,  6.0, 48_000_000),  # stencil: resident once covered
    ("tracer",  "reduction", 1_000_000, 30,  9.0,  8_000_000),  # scalar result lands on host
    ("poisson", "parallel",    100_000, 55, 25.0,  2_400_000),
    ("halo",    "parallel",     20_000, 90, 60.0,    600_000),  # staged through host every step
    ("sweep",   "serial",         200, 250_000, 0.0, 0),       # dependent sweep: no clause fixes it
]
HOST_S = 0.030                      # I/O + bookkeeping: un-clause-able host time
COVERED = ("flux", "tracer", "poisson", "halo")

cpu_total = sum(n * c for _, _, n, c, _, _ in LOOPS) * 1e-9 + HOST_S
cover_cpu = sum(n * c for nm, _, n, c, _, _ in LOOPS if nm in COVERED) * 1e-9
ceiling = 1.0 / (1.0 - cover_cpu / cpu_total)

def stage(offload, resident, hide_halo, flux_tune):
    if not offload:
        return 0.0, 0.0, 0.0, cpu_total
    gpu = motion = 0.0
    for nm, _, n, c, g, b in LOOPS:
        if nm in COVERED:
            gpu += n * (4.5 if (nm == "flux" and flux_tune) else g) * 1e-9
            if (not resident) or nm == "halo":
                motion += 2 * b / PCIE + 2 * COPY_FIX     # copyin + copyout each step
    if hide_halo:                                         # async(1): overlap behind flux kernel
        motion -= 2 * 600_000 / PCIE + 2 * COPY_FIX       # valid: copy stream < compute stream
    return gpu, max(motion, 0.0), 4 * LAUNCH, cpu_total - cover_cpu

STAGES = [
    ("S0 serial baseline",          False, False, False, False),
    ("S1 parallel loop, no data",   True,  False, False, False),
    ("S2 + data region (resident)", True,  True,  False, False),
    ("S3 + async + collapse/tune",  True,  True,  True,  True),
]
print("Amdahl ceiling (free offload, free motion): %.2fx" % ceiling)
print("%-28s %8s %8s %7s %8s %8s %7s" % ("stage", "gpu-ms", "motion", "launch", "cpu-ms", "step-ms", "speedup"))
for name, off, res, hide, tune in STAGES:
    g, m, l, c = stage(off, res, hide, tune)
    t = g + m + l + c
    print("%-28s %8.2f %8.2f %7.3f %8.2f %8.2f %6.2fx" % (name, g*1e3, m*1e3, l*1e3, c*1e3, t*1e3, cpu_total/t))
```

Real output of the run above (executed; deterministic; byte-identical on re-run):

```text
Amdahl ceiling (free offload, free motion): 2.47x
stage                          gpu-ms   motion  launch   cpu-ms  step-ms speedup
S0 serial baseline               0.00     0.00   0.000   197.30   197.30   1.00x
S1 parallel loop, no data       24.70    15.80   0.020    80.00   120.52   1.64x
S2 + data region (resident)     24.70     0.18   0.020    80.00   104.90   1.88x
S3 + async + collapse/tune      21.70     0.00   0.020    80.00   101.72   1.94x
```

Read it as a porting-campaign budget: rung one (directives on hot loops) already yields 1.64x despite moving 118 MB per step, because present-or-copy makes the naive version correct rather than broken. Rung two -- the `data` region making flux/tracer/poisson resident -- is the biggest single win per line of code changed, exactly the "data motion dominates" lesson every porting guide repeats. Rung three is polish: in this profile async can only hide a 0.6 MB halo staging copy and tuning buys 3 ms, so the step lands at 1.94x against a 2.47x ceiling set by the dependent sweep and host I/O. If your profile makes async the headline, you have heavy per-step staging (in-situ I/O, MPI halos at scale); if your achieved number is far under the ceiling, the remaining serial fraction -- not the directives -- is the target, and no clause reaches it.

## Performance reality versus hand-CUDA

- **Launch and region overhead.** Each `parallel` region is a kernel launch plus runtime bookkeeping; a port that sprays small regions per loop pays it everywhere. Adjacent independent loops in a `kernels` region can fuse; a `parallel` per loop cannot.
- **Unmanaged data is the default failure mode.** Per-region implicit copies (the `Generating copyin(...)` spam) are the top reason first ports show little speedup; the fix is always the data model, never the compute clauses.
- **Pointer-heavy code pays attach/detach.** C structs or Fortran derived types with pointer members require the pointer target to exist on the device before `enter data`, and each attach is bookkeeping cost -- deep Fortran structures with pointer chains are where OpenACC ports stall in practice.
- **Small or dependent loops stay on the host.** Trip counts below the launch overhead, or sweeps with loop-carried dependencies, belong on CPU cores; NVIDIA's `-acc=multicore` even parallelizes OpenACC regions across host cores instead of offloading.
- **The ceiling is honest Amdahl, not marketing.** The published flagship result makes the point: COSMO's dynamical core was rewritten in a performance-portability DSL, while the physical parameterizations and diagnostics -- the sprinkled, clause-friendly loops -- were ported with compiler directives; that combination ran the full model on 4888 GPUs of Piz Daint. Hand-CUDA keeps the edge where shared-memory staging, warp-level primitives, and kernel fusion matter ([CUDA page](../arch/advanced/cuda-programming.md)); OpenACC's claim is the porting cost curve, and the claim holds.

## Where OpenACC sits among the portability stacks

Against [OpenMP target](./openmp.md): same directive philosophy, different instincts. OpenACC grew up GPU-first -- present-or-copy defaults, unstructured data lifetimes, `host_data`, and explicit async queues arrived earlier and stay more ergonomic than the OpenMP equivalents -- while OpenMP target rides the bigger standard's institutional momentum and one compiler flag. Both sit behind hand-CUDA for irregular, pointer-chasing kernels; OpenACC's practical advantage today is Fortran, where its data semantics map cleanly onto whole-array code and where its implementations are deepest.

Support state, verified per implementation: NVIDIA HPC SDK (`nvfortran`, `nvc`, `nvc++` with `-acc`) is the reference implementation, documented against the 2.7-era semantics plus extensions such as `collapse(force:n)`; GCC accepts `-fopenacc` and "strives to be compatible with OpenACC v2.6"; HPE Cray Compiling Environment supports OpenACC "for offloading to NVIDIA GPUs, AMD GPUs, or the current CPU target"; Clang/Flang OpenACC remains a work in progress. That spread -- spec at 3.4, compilers implementing 2.x-plus-patches -- is the correct interview answer to "is OpenACC portable?": the source is, the performance is compiler-by-compiler.

Ecosystem reality: OpenACC survives where 300K-line Fortran codes, national weather services, and leadership-facility porting campaigns (the OLCF OpenACC hackathons paired six teams with GPU mentors) need incremental acceleration without rewrites, and where [MPI+X](./mpi-parallelism.md) hybrids want X to be cheap. New greenfield C++ projects default to CUDA, HIP, or [SYCL/oneAPI](./sycl-oneapi.md); OpenACC is the migration path, not the destination. [HPC infrastructure](./hpc-infra.md) tooling (batch systems, profilers) treats all of them identically.

## Pitfalls interviewers probe

1. A `parallel` region whose loops lack `loop` directives: redundant execution, not distribution -- the race or the no-speedup puzzle.
2. Trusting `kernels` to parallelize everything; unverifiable loops go serial silently until `-Minfo=accel` says otherwise.
3. Implicit per-loop copies during early porting; motion hoisting is the performance step, and `present` clauses are where the runtime errors then point.
4. `enter data` on a pointer member before the target is allocated -- attach fails or attaches garbage; order matters.
5. Async queues reusing buffers across steps without `wait`: the race hides until the staging volume changes.
6. Assuming spec parity across compilers: your 3.x clause may be 2.6-vintage on GCC or absent from the C++ front end.

## References

- OpenACC specification page (current: Version 3.4, June 2025): https://www.openacc.org/specification (probed 200; version verified on page)
- OpenACC 3.4 announcement, "the first revision since November 2022" (ISC 2025): https://www.openacc.org/blog/announcing-openacc-34 (probed 200)
- NVIDIA HPC Compilers User Guide -- `-acc`, Managed/Unified memory modes (sec. 5.4.2), `NVCOMPILER_ACC_GANGLIMIT`: https://docs.nvidia.com/hpc-sdk/compilers/hpc-compilers-user-guide/index.html (probed 200)
- NVIDIA OpenACC Getting Started Guide (26.5 docs; grid/block launch reports, async/wait, stream mapping): https://docs.nvidia.com/hpc-sdk/compilers/openacc-gs/index.html (probed 200)
- GCC manual, OpenACC (v2.6 compatibility, `-fopenacc`): https://gcc.gnu.org/onlinedocs/gcc/OpenACC.html (probed 200)
- HPE Cray Compiling Environment `intro_openacc(7)`: https://cpe.ext.hpe.com/docs/24.03/cce/man7/intro_openacc.7.html (probed 200)
- COSMO success story (300K-line Fortran 90 model, HP2C goals): https://www.openacc.org/success-stories/cosmo (probed 200)
- Fuhrer et al., "Near-global climate simulation at 1 km resolution ... 4888 GPUs with COSMO 5.0", Geosci. Model Dev. 11, 2018, doi:10.5194/gmd-11-1665-2018: https://gmd.copernicus.org/articles/11/1665/2018 (probed 200; abstract distinguishes DSL core from directive-based parameterizations)
- OLCF training archive (Introduction to OpenACC slides/recording; OLCF/NVIDIA OpenACC course): https://docs.olcf.ornl.gov/training/training_archive.html (probed 200); gang=threadblock/worker=warp/vector=thread mapping quoted from the course deck mirrored at https://www.psc.edu/wp-content/uploads/2025/11/Advanced-OpenACC.pdf (probed 200)
- OLCF OpenACC Hackathon, six teams porting with OpenACC (NVIDIA Technical Blog mirror): https://forums.developer.nvidia.com/t/porting-scientific-applications-to-gpus-at-the-olcf-openacc-hackathon/148597 (probed 200); the OLCF 3-part OpenACC training-series page https://www.olcf.ornl.gov/openacc-training-series returns 403 to scripted fetches, verified via search indexing
