# Kokkos: Performance Portability by Execution and Memory Space Mapping

Kokkos is a C++ programming model and ecosystem (Core, Containers, Kernels, Tools) that
originated at Sandia National Laboratories. Its premise: one source tree should run on NVIDIA,
AMD, and Intel GPUs as well as multicore CPUs, by separating *what* a kernel does from *where*
it executes and *where* its data lives. The authors frame this as two orthogonal aspects: an
abstract machine model of execution and memory spaces, and a concrete C++ instantiation of it.

See also: [HPC infrastructure overview](hpc-infra.md), [OpenMP](openmp.md),
[SYCL/oneAPI](sycl-oneapi.md), the [CUDA programming model](../arch/advanced/cuda-programming.md)
page for the NVIDIA concepts Kokkos maps onto, and [MPI parallelism](mpi-parallelism.md).

## 1. The two-axis machine model

```text
     EXECUTION SPACES                        MEMORY SPACES
 (where lambdas run)                    (where Views allocate)
 +--------------------------------+     +-----------------------+
 | device : Cuda | HIP | SYCL     | --> | CudaSpace, HIPSpace,  |
 | host-p : OpenMP | Threads |HPX* | --> | HostSpace, UVM/USM,   |
 | host-s : Serial                |     | pinned host spaces    |
 +--------------------------------+     +-----------------------+
   (* experimental)   spaces declare which other spaces may access them
```

- A kernel is dispatched to an **ExecutionSpace**; data is allocated in a **MemorySpace**;
  accessibility between spaces is a first-class, queryable property, not an assumption.
- At build time you enable at most **one device backend plus one host-parallel backend**; with
  no device backend, Serial is turned on so at least one execution space always exists.
- `Kokkos::DefaultExecutionSpace` resolves to the highest enabled space in the
  `device > host-parallel > host-serial` hierarchy; code that never names a backend is idiomatic.

| ExecutionSpace | Target | Build option | Notes |
|---|---|---|---|
| Cuda | NVIDIA GPUs | `Kokkos_ENABLE_CUDA` | Needs CUDA toolchain |
| HIP | AMD GPUs | `Kokkos_ENABLE_HIP` | Promoted from Experimental in 4.0 |
| SYCL | Intel GPUs | `Kokkos_ENABLE_SYCL` | Promoted in 4.5; Experimental alias deprecated in 5.2 |
| OpenACC | Accelerator offload | `Kokkos_ENABLE_OPENACC` | Experimental |
| OpenMPTarget | OpenMP target offload | removed after 5.0 | Shipped through 4.x and 5.0; gone from the 5.1 build options |
| OpenMP | CPU threads | `Kokkos_ENABLE_OPENMP` | Default host-parallel choice |
| Threads | std::thread pool | `Kokkos_ENABLE_THREADS` | Legacy host-parallel path |
| HPX | HPX runtime | `Kokkos_ENABLE_HPX` | Experimental |
| Serial | One CPU core | `Kokkos_ENABLE_SERIAL` | Reference semantics, debugging |

The OpenMPTarget removal is instructive: directive-offload backends are harder to keep healthy
than backends wrapping a native device runtime.

## 2. Views: data with a space, a layout, and traits

`Kokkos::View` is the reference-counted multidimensional array of the model; it knows its
MemorySpace, its layout, and optional access traits, e.g.
`Kokkos::View<double**, Kokkos::LayoutRight, Kokkos::CudaSpace> B("B", N, M);`.

The default layout depends on the execution space, and the docs say why: `View<int**, Cuda>`
gets `LayoutLeft` so consecutive threads in a warp touch consecutive addresses (coalescing),
while `View<int**, OpenMP>` gets `LayoutRight` so one thread walks contiguous cache lines and
false sharing is avoided. The porting cliff: a 2-D loop nest silently changes memory order when
the default space flips from host to device. Pin the layout explicitly when the data structure
(a BLAS matrix, an I/O buffer) dictates it.

Movement is explicit: `create_mirror_view` makes a same-shape mirror in another space;
two-argument `deep_copy` synchronously moves bytes, while the three-argument form with an
execution space instance enqueues asynchronously. `CudaUVMSpace` (and HIP managed memory) can be
dereferenced from both sides, but the docs warn that performance depends on the access pattern;
best practice is to touch a View only from dispatches on the space it lives in.

## 3. Atomics and scatter patterns

The docs build atomics from a histogram: `histogram(index)++` is a load-modify-store that races
under parallelism. Portable resolution via free functions on raw element addresses:

- `atomic_add/sub/inc/dec/min/max/and/or` (no return), plus `atomic_load`, `atomic_store`,
  `atomic_exchange`, `atomic_compare_exchange`.
- `atomic_fetch_op` / `atomic_op_fetch` return the old/new value, with
  `op` in `add, and, div, lshift, max, min, mod, mul, or, rshift, sub, xor`.
- A whole-View `MemoryTraits<Atomic>` alias makes every access atomic for one kernel, keeping
  plain `++`/`+=` syntax.
- `ScatterView` switches at compile time between atomics and per-thread replication plus a
  reduce; on low-core CPU builds (one rank per NUMA node next to MPI) replication often wins.

Alternatives the docs weigh: coloring the conflict set (extra memory traffic) and per-thread
output replication (only scales to a few threads); atomics remain the portable default.

## 4. parallel_for, parallel_reduce, parallel_scan

The three patterns cover flat iteration, reduction, and prefix scans; the policy is always the
first argument, which is what makes one functor retargetable:

```cpp
double dot(const View& x, const View& y) {
    double result = 0.0;
    Kokkos::parallel_reduce("dot", Kokkos::RangePolicy<>(0, x.extent(0)),
        KOKKOS_LAMBDA(const int i, double& acc) { acc += x(i) * y(i); },
        result);                    // default reducer: Sum
    return result;                  // copy-back to host scalar is handled
}
```

- The string label on each dispatch is what profilers and Kokkos Tools display.
- Built-in reducers: `Sum`, `Prod`, `Min`/`Max` with location-tracking `MinLoc`/`MaxLoc`, plus
  logical and bitwise variants; custom reducers are supported.
- `parallel_scan` gives exclusive/inclusive prefix sums; `RangePolicy<>(begin, end, chunk_size)`
  controls granularity and `MDRangePolicy` tiles 2-D to 6-D iteration spaces portably.

## 5. Team-level parallelism and scratch memory

`TeamPolicy<Space>(league_size, team_size, vector_length)` maps a 2-D index range: the
**league rank** is the team index, the **team rank** the thread index within the team; the docs
note the CUDA equivalence of a 1-D grid of 1-D blocks. League size is essentially unbounded;
team size must fit hardware constraints.

```text
TeamPolicy<Space>(L, T, V)
+-------------------------------------------------------------------+
| team 0      team 1      team 2   ...                 team L-1    | <- league_rank
|  T threads   T threads   T threads                    T threads   | <- team_rank
|   V lanes     V lanes     V lanes                      V lanes    | <- vector lane
+-------------------------------------------------------------------+
  inside a member: TeamThreadRange(team, n)   splits work over threads
                   ThreadVectorRange(team, n) splits work over lanes
                   Kokkos::single(PerTeam(m)) one elected member runs m
```

Collectives on the member handle: `barrier()`, `team_reduce(Sum<scalar>(val))`,
`team_broadcast`, `team_scan`. Nesting rules are strict: two `TeamThreadRange` loops may not
nest, and writes outside the closure of the current nested layer are illegal.

**Scratch memory** is the team-private "scratch pad", requested on the policy via
`set_scratch_size(level, PerTeam(bytes), PerThread(bytes))`. Level 0 is the small fast tier
(restricted to a few tens of kilobytes per team; on CUDA it maps to shared memory); level 1 is
the larger, slower tier. Access goes through `member.team_scratch(level)` or as `Unmanaged`
Views typed on `DefaultExecutionSpace::scratch_memory_space`. Pads are recycled by all logical
teams landing on the same physical cores and live exactly as long as the team, which is what
legacy shared-memory tiling wants.

## 6. Fences and the asynchronous model

Device-space dispatch returns immediately; correctness lives at the synchronization points:

- `Kokkos::fence()` blocks until **all** outstanding asynchronous operations complete,
  including parallel dispatches and three-argument asynchronous `deep_copy`; it implies a
  memory fence. Each execution space instance also has its own fence, and `fence(label)`
  feeds labeled events to profiling tools.
- Fences may not be called inside a parallel region, and timing without one measures only
  launch overhead: the docs' timing example wraps `parallel_for` + `fence()` in a `Timer`.
- Two-argument `deep_copy` is itself a synchronization point; the three-argument form overlaps
  transfers with compute, then fences at the phase boundary.

Fences are meant to be rare, coarse-grained phase boundaries, not per-kernel barriers.

## 7. A dispatch-cost model: choosing a space by kernel shape

Choosing between `Cuda`, `OpenMP`, and `Serial` for one kernel is a whiteboard roofline plus
two overhead terms: dispatch cost, and underutilization when the shape is too small to fill the
machine. The MODEL encodes each space as `(overhead_ms, gflops, gbps, n_sat)`, where `n_sat` is
the element count that saturates streaming hardware and utilization ramps linearly below it:

```python
# MODEL: roofline dispatch simulator for Kokkos-style ExecutionSpaces.
# Space = (overhead_ms, gflops, gbps, n_sat): overhead per dispatch, peaks, and
# the element count n_sat that saturates streaming hardware. Below n_sat,
# util = n / n_sat scales both peaks down (underutilization penalty).
# modeled_time_ms = overhead + max(n*flops/(gflops*util), n*bytes/(gbps*util)) * 1e3
SPACES = {  #                 overhead_ms  gflops   gbps    n_sat
    "Serial":  (0.0005, 5.0,    10.0,     1),
    "OpenMP":  (0.0050, 80.0,   100.0,    8000),
    "Cuda":    (0.0100, 9000.0, 1300.0,   500000),
}
KERNELS = [  # (name, n, flops_per_elem, bytes_per_elem)
    ("tiny_fixup",    1000,      1,  16),
    ("moderate_axpy", 20000,     2,  24),
    ("stream_copy",   50000000,  1,  16),
    ("axpy",          50000000,  2,  24),
    ("stencil5_2d",   1000000,  10,  40),
    ("dgemm_block",   1000000, 128,  16),
]

def modeled_time_ms(space, n, flops, bytes_):
    ovh, gflops, gbps, n_sat = space
    util = min(1.0, n / n_sat)
    calc_ms = n * flops / (gflops * 1e9 * util) * 1e3
    mem_ms  = n * bytes_ / (gbps * 1e9 * util) * 1e3
    return ovh + max(calc_ms, mem_ms)

hdr = f"{'kernel':<14}{'n':>10}{'f/B':>5} | {'Serial':>10}{'OpenMP':>10}{'Cuda':>10} | {'best':>7}{'gain_vs_Cuda':>13}"
print(hdr)
print("-" * len(hdr))
for name, n, f, b in KERNELS:
    ts = {s: modeled_time_ms(sp, n, f, b) for s, sp in SPACES.items()}
    best = min(ts, key=ts.get)
    print(f"{name:<14}{n:>10}{f/b:>5.2f} | {ts['Serial']:>10.4f}{ts['OpenMP']:>10.4f}"
          f"{ts['Cuda']:>10.4f} | {best:>7}{ts['Cuda']/ts[best]:>12.2f}x")
print("-" * len(hdr))
print("Times are modeled milliseconds per dispatch; gain_vs_Cuda = 1.0 when Cuda wins.")
```

Output (deterministic; verified identical across reruns):

```text
kernel                 n  f/B |     Serial    OpenMP      Cuda |    best gain_vs_Cuda
-------------------------------------------------------------------------------------
tiny_fixup          1000 0.06 |     0.0021    0.0063    0.0162 |  Serial        7.69x
moderate_axpy      20000 0.08 |     0.0485    0.0098    0.0192 |  OpenMP        1.96x
stream_copy     50000000 0.06 |    80.0005    8.0050    0.6254 |    Cuda        1.00x
axpy            50000000 0.08 |   120.0005   12.0050    0.9331 |    Cuda        1.00x
stencil5_2d      1000000 0.25 |     4.0005    0.4050    0.0408 |    Cuda        1.00x
dgemm_block      1000000 8.00 |    25.6005    1.6050    0.0242 |    Cuda        1.00x
-------------------------------------------------------------------------------------
Times are modeled milliseconds per dispatch; gain_vs_Cuda = 1.0 when Cuda wins.
```

All three spaces win somewhere: sub-5k fixups stay on `Serial` (fork/launch costs dominate);
mid-size bandwidth-bound work favors the host-parallel space (OpenMP beats the GPU 1.96x on
dispatch cost plus underutilization); large or arithmetic-dense kernels go to the device space
by 12.8x over OpenMP for streaming and 66x for the compute-bound block. The model omits
host-to-device movement, occupancy, register pressure, and atomic contention; Kokkos Tools
exist to replace this arithmetic with measurements.

## 8. Kokkos versus RAJA, SYCL, and OpenMP target offload

| Approach | Abstraction | Data model | Backends | Sweet spot |
|---|---|---|---|---|
| Kokkos | Data + execution spaces, teams, scratch | Views with layouts, traits, atomics | Cuda, HIP, SYCL, OpenACC, OpenMP, Threads, HPX, Serial | Whole applications needing CPU and GPU from one tree |
| RAJA | Loop-execution templates over existing loops | App-managed; typically paired with LLNL's Umpire allocator | OpenMP, CUDA, HIP, SYCL | Portable loop execution with minimal disruption to existing code |
| SYCL | Khronos single-source device C++ standard | Buffers/accessors or explicit USM | Any conforming implementation | Vendor-neutral device code, non-NVIDIA accelerators first |
| OpenMP target | Compiler directives in host code | `map` clauses around host data | Whatever the compiler enables | Lowest-effort offload of loop nests |

Nuances worth stating: Kokkos itself can target a SYCL device (the `Kokkos::SYCL` space), so
"Kokkos vs SYCL" is really portable framework vs portable language standard. RAJA's README
frames its goal as portability "with manageable disruption to existing" code, the loop-template
niche Kokkos fills with heavier data machinery. Kokkos dropping its own OpenMPTarget backend
after 5.0 shows the maintenance cost of directive-based device paths. Directives hide data
movement; Kokkos makes it explicit in the type system.

## 9. Verified adopters

| Project | Role of Kokkos | Evidence |
|---|---|---|
| Trilinos | Kokkos grew as a Trilinos/Sandia effort; Tpetra and friends build on it | The TPDS "Kokkos 3" paper frames it as the exascale path for Trilinos-class codes |
| LAMMPS | KOKKOS package; CMake presets named `kokkos` select it | LAMMPS build documentation |
| SPARTA | KOKKOS package; release notes track Kokkos upgrades (one release "updates the Kokkos library to v5.0.2 ... ports many styles to KOKKOS") | SPARTA documentation site |
| Cabana | Particle/cell-list co-design layer: "Cabana is built on Kokkos" | Cabana README |
| Kokkos Kernels | Standalone sparse/dense linear algebra and graph kernels library | kokkos-kernels repository and docs |

## 10. Refactoring legacy code: the repeatable pattern

1. **Sandbox first.** Wrap `main` in `Kokkos::initialize/finalize`; build with Serial so the
   first port is correctness-only.
2. **Alias the spaces.** `using exec_space = Kokkos::DefaultExecutionSpace;` plus
   `using mem_space = exec_space::memory_space;` in one header; backend swaps touch one line.
3. **Wrap the data.** Replace `malloc`/`new[]` members with Views in `mem_space`; expose host
   copies via `create_mirror_view` + `deep_copy`; pass Views, never raw pointers, across APIs.
4. **Convert the hot loops.** Inner loops become `parallel_for` with `KOKKOS_LAMBDA`; helpers
   become `KOKKOS_FUNCTION`. No allocation, I/O, or virtual dispatch inside lambdas.
5. **Replace reductions and scatter-adds.** OpenMP reduction clauses become `parallel_reduce`
   with reducers; scatter-adds become `atomic_add`, `ScatterView`, or colored dispatches.
6. **Promote nested loops to teams.** Shared-memory-tiled loops become `TeamPolicy` +
   `TeamThreadRange`/`ThreadVectorRange` with `set_scratch_size` scratch pads.
7. **Only then optimize placement.** Measure with Kokkos Tools, move Views to explicit spaces,
   retire UVM reliance, and thin fences down to phase boundaries.

| Gotcha | Symptom | Fix |
|---|---|---|
| Default-layout flip on port | 2-D kernel fast on CPU, collapsed bandwidth on GPU | Pin `LayoutLeft`/`LayoutRight` explicitly where access order matters |
| Raw host pointer captured in lambda | Invalid device access on GPU | Capture only Views; wrap legacy buffers as Unmanaged Views in the right space |
| Reading results without synchronization | Stale values after dispatch | Fence, or rely on `parallel_reduce` scalar copy-back, before host reads |
| Atomic contention on hot bins | GPU kernel far below roofline | Color the conflict set, or use ScatterView replication |
| Scratch over-request | Runtime error at dispatch | Keep level 0 within the few-tens-of-KB budget; overflow to level 1 |
| UVM page thrashing | Cross-space reads mysteriously slow | Move to explicit spaces plus `deep_copy`/mirror pairs |

## References

1. Kokkos Core repository: <https://github.com/kokkos/kokkos>
2. Kokkos Core Wiki, Machine Model chapter: <https://kokkos.org/kokkos-core-wiki/ProgrammingGuide/Machine-Model.html>
3. Kokkos configuration guide (backend switches, one-device-plus-one-host rule): <https://kokkos.org/kokkos-core-wiki/get-started/configuration-guide.html>
4. Kokkos fence API reference: <https://kokkos.org/kokkos-core-wiki/API/core/parallel-dispatch/fence.html>
5. Kokkos deprecations table (Experimental HIP/SYCL promotions, 5.x removals): <https://kokkos.org/kokkos-core-wiki/deprecations.html>
6. H. C. Edwards, C. R. Trott, D. Sunderland, "Kokkos: Enabling manycore performance portability through polymorphic memory access patterns", J. Parallel Distrib. Comput. 74(12), 2014, <https://doi.org/10.1016/j.jpdc.2014.07.003>
7. C. R. Trott et al., "Kokkos 3: Programming Model Extensions for the Exascale Era", IEEE Trans. Parallel Distrib. Syst. 33(11), 2022, <https://doi.org/10.1109/TPDS.2021.3097283>
8. RAJA (LLNL): <https://github.com/LLNL/raja> ; Umpire allocator (LLNL): <https://github.com/LLNL/Umpire>
9. Khronos SYCL: <https://www.khronos.org/sycl/> ; OpenMP specifications: <https://www.openmp.org/specifications/>
10. LAMMPS build docs (KOKKOS presets): <https://docs.lammps.org/Build_package.html> ; SPARTA docs: <https://sparta.github.io/> ; Cabana: <https://github.com/ECP-copa/Cabana>
