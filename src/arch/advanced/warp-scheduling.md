# GPU Warp Scheduling and Latency Hiding

The [CUDA programming model](./cuda-programming.md) teaches you to think in threads; this page drops below that abstraction to the machinery that makes it work. Each SM runs between one and four **warp schedulers** that, every cycle, pick an eligible warp and issue its next instruction. Because a GPU has no out-of-order machinery and no branch prediction (unlike a CPU core — see [OoO execution](./ooo-execution.md)), *hiding* memory and dependency latency is not the hardware's job. It is the occupancy planner's job: keep enough warps resident so somebody is always ready. The basics of SIMT and divergence live in [GPU Architecture](../parallelism/gpu.md) and [CUDA basics](../parallelism/cuda.md); here we build the scheduling model, the occupancy arithmetic, and the failure modes interviewers probe.

## What an SM Scheduler Does per Cycle

The guide's Hardware Implementation chapter is one paragraph long, and every clause matters:

> The execution context (program counters, registers, and so on) for each warp processed by a multiprocessor is maintained on-chip during the entire lifetime of the warp. Therefore, switching from one execution context to another has no cost, and at every instruction issue time, a warp scheduler selects a warp that has threads ready to execute its next instruction.

Per cycle, on a modern NVIDIA SM (Kepler through Hopper-class):

1. Each warp scheduler scans its resident warps' scoreboard bits for **eligibility**.
2. It picks one eligible warp and issues one instruction to the active lanes. Within a warp, issue is strictly **in-order** — the guide states explicitly that SM instructions "are issued in order and there is no branch prediction or speculative execution."
3. Optionally it *pairs* a second independent instruction (Fermi and Kepler could dual-issue; see the history note below).
4. Long-latency results write back through the scoreboard, clearing pending bits and re-enabling the warps that were waiting.

The scheduler's authority ends at the SM boundary. A global dispatch unit (the **GigaThread engine**, in NVIDIA's whitepaper naming) hands thread blocks to SMs; the SM partitions each block into warps of 32 consecutive thread IDs, and warps never migrate. AMD is the same idea with a different unit count: a CDNA processor groups **64 work-items per wavefront**, not 32 (AMD Instinct MI200 CDNA2 ISA guide), so AMD occupancy numbers are not directly comparable to NVIDIA's.

## The Scoreboard and the Stall Model

A warp is either *ready* (issue something this cycle) or *stalled*. The stall causes are enumerable:

```text
one warp scheduler, one cycle:
                            +---------------------------------+
  resident warps  W0..W63 ->| ready bits (1 per warp)         |
                            +---------------------------------+
                                       | pick ANY ready warp
                                       v
     issue slot -----------------> [dispatch] --> FP32 / INT32 / LDST / SFU pipes

  why a warp's ready bit reads 0 (stall causes):

    W05 ready   W17 ready   W34 ready   W51 NOT ready <--+
    (idle)      (compute)   (compute)                   |
  +-----------------------------------------------------|--+
  | W51: FFMA R4, R8, R9, R4     R8 not written back    |-+
  |      -> register dependency: an earlier instruction  |
  |         (e.g. LDG) still owns R8 in the scoreboard.  |
  +------------------------------------------------------+
  other causes: memory wait (load in flight), barrier wait
  (__syncthreads), memory fence, execution of prior instr.
```

This is a scoreboard in the classic sense (see [data hazards](../pipelining/data-hazards.md)), simplified: dependencies are tracked at **warp granularity**, not per instruction. The Fermi whitepaper describes exactly this hardware — "a multi-port register scoreboard keeps track of any registers that are not yet ready with valid data" — while the Kepler GK110 whitepaper notes that for math instructions, whose latencies are fixed, the *compiler* pre-computes eligibility and encodes it in the instruction, leaving hardware scoreboarding mainly for variable-latency loads and textures. Both whitepapers are linked below.

The best-practices guide reduces the model to one sentence: register dependencies arise "when an instruction uses a result stored in a register written by an instruction before it," and on compute capability 7.0 most arithmetic instructions take ~4 cycles — "this latency can be completely hidden by the execution of threads in other warps." That sentence is the whole latency-hiding thesis.

Each stall cause has a different first lever:

| Stall cause | Scheduler-visible symptom | First lever |
|---|---|---|
| Register dependency | warp ineligible until an ALU result writes back (~4 cycles) | break chains: unroll, independent accumulators |
| Memory wait (L2/DRAM) | warp ineligible for hundreds of cycles | more independent loads per warp, coalescing, tiling, async copies |
| Barrier / fence wait | whole block ineligible together | rebalance work per block; fewer __syncthreads() |
| No eligible warp at all | issue slot idles despite resident warps | raise occupancy (fewer regs/block) or add ILP |

### A Short History of the Issue Slot

The whitepapers document how much of this machinery was static vs. dynamic:

- **Fermi (2009)**: two warp schedulers per SM, each able to dual-issue — "two integer instructions, two floating instructions, or a mix" per cycle — with hardware doing the hazard work: the multi-port register scoreboard plus a dependency checker analyzing fully decoded instructions.
- **Kepler GK110 (2012)**: four warp schedulers with eight dispatch units, two independent instructions per warp per cycle; because math-pipeline latencies are deterministic, the *compiler* decides eligibility and encodes latency into the instruction, and a simple hardware block masks ineligible warps. Hardware scoreboarding survives only for variable-latency texture and load operations; per-thread registers grew to 255.
- **The lesson**: SIMT's in-order, same-instruction-per-warp contract lets silicon migrate work from dynamic hazard hardware to the compiler — the opposite direction from CPU OoO design.

## Occupancy: Definition and Limits

**Occupancy** is "the ratio of the number of active warps per multiprocessor to the maximum number of possible active warps" (CUDA C++ Best Practices Guide). It is a *capacity* metric: how many of the SM's warp slots are filled with resident warps that the scheduler could pick from.

The limits are a function of compute capability. For an Ampere cc 8.0 SM (A100), from the guide's Compute Capabilities appendix:

| Resource limit (cc 8.0 SM) | Value |
|---|---|
| Resident warps per SM | 64 (2048 threads) |
| Resident blocks per SM | 32 |
| 32-bit registers per SM | 65,536 |
| Max shared memory per SM (carveout) | 164 KB |
| Max registers per thread | 255 |
| Warp size | 32 |

Shared memory is a carveout from the unified 192 KB data cache: cc 8.0 hardware supports 0/8/16/32/64/100/132/164 KB configurations, so raising `cudaFuncAttributePreferredSharedMemoryCarveout` trades L1 capacity for more resident blocks. Registers are allocated to a whole block at once and rounded up at **256 registers per warp** granularity — a kernel using 33 registers/thread pays for 40 per lane (1,280/warp), which can silently cost a whole resident block.

The arithmetic also runs forward: on a cc 7.0 SM (65,536 registers, 2,048-thread capacity), 100% occupancy leaves exactly 65,536 / 2,048 = **32 registers per thread**. Every register above that is bought with resident warps — which is why the register budget, not the code, often sets the latency-hiding ceiling.

## An Occupancy Calculator in 30 Lines

The toolkit ships this as a spreadsheet and as `cudaOccupancyMaxActiveBlocksPerMultiprocessor` (runtime API). The logic is small enough to write from scratch, and writing it is the best way to internalize which resource bites first. Here is the core arithmetic for a cc 8.0 SM — the same computation `--ptxas-options=-v` numbers feed into:

```python
# Occupancy calculator: how many warps can live on one SM?
# Models a cc 8.0-class SM (A100): the four hard limits plus the
# register-allocation granularity (256 registers per warp, rounded up).
WARP = 32
MAX_WARPS = 64        # resident warps per SM
MAX_BLOCKS = 32       # resident blocks per SM
REGS_SM = 65536       # 32-bit registers per SM
SMEM_SM = 164 * 1024  # max shared-memory carveout per SM (bytes)
GRAN = 256            # register allocation granularity (per warp)

def occupancy(regs, smem_kb, threads):
    warps_blk = threads // WARP
    per_warp = -(-regs * WARP // GRAN) * GRAN       # round up to granularity
    regs_lim = REGS_SM // (warps_blk * per_warp)
    smem_lim = SMEM_SM // (smem_kb * 1024) if smem_kb else MAX_BLOCKS
    blocks = min(MAX_BLOCKS, regs_lim, smem_lim)
    warps = blocks * warps_blk
    if warps == MAX_WARPS:
        limiter = "none - all 64 warp slots resident"
    else:
        cands = []
        if blocks == regs_lim: cands.append("registers")
        if blocks == smem_lim: cands.append("shared memory")
        if blocks == MAX_BLOCKS: cands.append("block slot")
        limiter = " + ".join(cands)
    print(f"regs={regs:3d}/thr smem={smem_kb:3d}KB thr={threads:3d}"
          f" -> blocks={blocks:2d} warps={warps:2d}/64"
          f" occ={100 * warps / MAX_WARPS:5.1f}%  limiter: {limiter}")

for cfg in [(32, 0, 256), (64, 0, 256), (96, 0, 256),
            (32, 48, 256), (64, 8, 512), (33, 0, 64)]:
    occupancy(*cfg)
```

Real output:

```text
regs= 32/thr smem=  0KB thr=256 -> blocks= 8 warps=64/64 occ=100.0%  limiter: none - all 64 warp slots resident
regs= 64/thr smem=  0KB thr=256 -> blocks= 4 warps=32/64 occ= 50.0%  limiter: registers
regs= 96/thr smem=  0KB thr=256 -> blocks= 2 warps=16/64 occ= 25.0%  limiter: registers
regs= 32/thr smem= 48KB thr=256 -> blocks= 3 warps=24/64 occ= 37.5%  limiter: shared memory
regs= 64/thr smem=  8KB thr=512 -> blocks= 2 warps=32/64 occ= 50.0%  limiter: registers
regs= 33/thr smem=  0KB thr= 64 -> blocks=25 warps=50/64 occ= 78.1%  limiter: registers
```

Read the last line twice: 33 registers per thread sounds lean, but the 256-register warp granularity (1,056 -> 1,280) pushes the block footprint up so far that the kernel lands at 78% instead of 100%. The guide's own worked example makes the cliff vivid: with 512-thread blocks at 64 registers/thread on a cc 6.x SM, exactly two blocks fit (2 x 512 x 64 = 65,536 registers, 32 warps); *one more register* and only one block (16 warps) fits — a 50% occupancy drop from a single register.

## Latency-Hiding Math

The guide quantifies hiding directly: "the number of instructions required to hide a latency of L clock cycles" is **4L** for cc 5.x, 6.1, 6.2, 7.x and 8.x (four warps issued per cycle, one instruction each). Volkov's GTC 2010 talk states the same relation as Little's law: **needed parallelism = latency x throughput**. His measurements: on G80, ~24 cycles x 8 lanes ≈ 192 operations per SM — six warps with zero ILP; on GTX 480, ~18 cycles x 32 lanes = 576 threads — 18 warps. The guide's version: cc 7.x arithmetic latency is ~4 cycles, so **16 active warps** (4 cycles x 4 schedulers) hide it.

| Latency source | ~L (cycles) | Instructions in flight needed (4L) | Who supplies them |
|---|---|---|---|
| Register dependency (ALU) | 4 | 16 | 16 warps x 1 instruction |
| Shared memory / L1 hit | ~30 | ~120 | 15 warps x 8 ILP, or 30 x 4 |
| L2 hit | ~200 | ~800 | tiling + cache-friendly access, not raw warps |
| Global memory (DRAM) | ~400 | ~1600 | async copies, prefetch, more warps + MLP |

So why can **8-16 warps hide hundreds of cycles** of memory latency? Because the hiding budget is *bytes in flight*, not warps alone. In Little's law's bandwidth form: to sustain B bytes/s with latency L, you need B x L bytes outstanding. A modern HBM-class SM shares ~1-2 TB/s across ~100 SMs, call it 10 GB/s each; at 400 cycles ≈ 300 ns that is ~3 KB in flight — about **24 coalesced 128 B warp-loads**. Sixteen warps each keeping ~2 independent loads outstanding clear that bar; sixteen warps with one dependent load each hold only ~2 KB in flight — roughly two-thirds of the target — and a dependent load-use chain cannot do better. Occupancy sets the ceiling; per-warp memory-level parallelism determines whether you touch it. (The same logic in reverse: 16 warps *cannot* hide a 400-cycle latency for dependent computation — arithmetic needs the 4-cycle treatment above.)

## Warp Divergence, Briefly

Divergence is a scheduling-adjacent cost, covered fully in [CUDA basics](../parallelism/cuda.md) and the [programming model page](./cuda-programming.md) — here is only the ledger entry: a divergent branch serializes the warp's paths (both paths execute, each with masked lanes), so the scheduler sees one warp issuing twice as many instructions. Since Volta, each thread has its own program counter ("independent thread scheduling"), which enables intra-warp exchange but does *not* make divergent branches cheap — the paths still serialize. Divergence burns issue slots; occupancy cannot buy them back.

## ILP vs TLP: Two Ways to Fill the Slots

The guide frames the scheduler's choice precisely: at each issue time it selects "another independent instruction of the same warp, exploiting instruction-level parallelism, or more commonly an instruction of another warp, exploiting thread-level parallelism." The two are substitutes for hiding latency — but they cost different resources:

- **TLP** (more warps) costs registers and shared memory *per warp* and pays off for any workload. Limited by occupancy.
- **ILP** (unrolling, independent accumulators) costs registers *per thread* — which can *reduce* occupancy and buy back the wrong thing. It also needs the dependency chains broken; reusing one accumulator serializes.

Volkov's experiment is the canonical evidence: without ILP, a GTX 480 SM needs 576 threads for full utilization; with ILP, far fewer threads saturate the same units. His matrix-multiply kernels hit *2x speedup at 33% occupancy* by doing more work per thread. The trade is not free — unrolling inflates register pressure, and the compiler may spill to local memory (see register pressure notes in the [programming model page](./cuda-programming.md)).

## Occupancy Is Not Throughput

The most common interview trap. The best practices guide says it outright: "Higher occupancy does not always equate to higher performance — there is a point above which additional occupancy does not improve performance." Pitfalls worth memorizing:

1. **Above saturation, extra warps idle.** Once latency is hidden, more warps change nothing except cache pressure.
2. **Forcing occupancy can backfire.** `__launch_bounds__`/`-maxrregcount` that cap registers may force spills to local memory, adding instructions and stalls that defeat the occupancy gain.
3. **Barriers stall everyone.** A `__syncthreads()`-heavy kernel serializes regardless of warp count; occupancy hides *independent* latency, not lockstep waiting.
4. **Occupancy counts warps, not issue slots.** A 100%-occupancy kernel of divergent or dependency-chained code still leaves the scheduler with nothing eligible to issue.

Diagnose with Nsight Compute: achieved occupancy, stall reasons (long scoreboard vs. short scoreboard vs. barrier), and issued-vs-eligible warp slots tell you which resource is actually binding.

## Interview Questions

### Q: Why is switching between warps on an SM free, while an OS context switch costs microseconds?

The guide's answer: each warp's context (program counters, registers) lives in the SM register file on-chip for the warp's entire lifetime — switching means picking a different warp's ready instruction, with nothing saved or restored. No privilege change, no TLB work, no cache-cold start. A CPU context switch moves register state to memory and back through kernel code; a warp "switch" is a mux select. The cost is *capacity*: the register file is partitioned among resident warps, which is exactly why occupancy exists as a concept.

### Q: A kernel uses 96 registers/thread, no shared memory, 256-thread blocks on a cc 8.0 SM. What occupancy do you get, and what is the limiter?

Per warp: 96 x 32 = 3,072 registers (already a multiple of 256). Per block: 8 warps x 3,072 = 24,576. Two blocks fit (49,152 of 65,536 registers); a third would need 73,728. So 16 warps of 64 — **25% occupancy, register-limited** (config C in the calculator above). To recover occupancy: reduce registers via `__launch_bounds__` (accepting possible spills), restructure to lower live-value pressure, or get more ILP out of the fewer resident warps.

### Q: Your kernel runs at 60% occupancy and is bandwidth-bound. A teammate says "push occupancy to 100%." What do you tell them?

Occupancy is a means, not an end. Apply Little's law: what matters is bytes in flight = bandwidth x latency. Check achieved bandwidth against peak; if every warp already keeps multiple independent loads outstanding, the last 40% of warps add nothing (the guide: above a point, "additional occupancy does not improve performance"). Raising occupancy may also shrink the L1/shared carveout or force spills. If bandwidth *is* short, the levers are per-warp memory-level parallelism (unrolled independent loads), wider loads (`float4`), async copies, and tiling to shorten effective latency.

### Q: Fermi's scheduler had a hardware dependency-checking stage; Kepler GK110 mostly removed it. Why, and what remained?

The GK110 whitepaper: Fermi's dual-issue needed "a multi-port register scoreboard" plus "a dependency checker block" analyzing decoded instructions dynamically. But math-pipeline latencies are deterministic, so GK110 had the *compiler* decide up front when instructions become eligible and encode that latency in the instruction; a simple hardware block masks ineligible warps at the scheduler. What stayed in hardware: scoreboarding for genuinely variable-latency operations (texture and loads) and the inter-warp scheduling logic that picks the next warp among eligible candidates. A power optimization enabled by the SIMT contract that warps execute in order.

## References

- NVIDIA, CUDA C++ Programming Guide (current, CUDA 13 rewrite): <https://docs.nvidia.com/cuda/cuda-programming-guide/>
- NVIDIA, CUDA C++ Programming Guide — Hardware Implementation / Multiprocessor Level (legacy edition, still live; source of the context-switch and 4L quotes): <https://docs.nvidia.com/cuda/cuda-c-programming-guide/>
- NVIDIA, Compute Capabilities appendix (cc 8.0 limits, shared-memory carveouts): <https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html>
- NVIDIA, CUDA C++ Best Practices Guide — Occupancy, Hiding Register Dependencies, Effects of Shared Memory: <https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/>
- NVIDIA, CUDA Runtime API — Occupancy: <https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__OCCUPANCY.html>
- V. Volkov, *Better Performance at Lower Occupancy*, GTC 2010 (Little's law, ILP vs TLP measurements): <https://www.nvidia.com/content/gtc-2010/pdfs/2238_gtc2010.pdf>
- NVIDIA, Fermi Compute Architecture Whitepaper (dual-issue, two warp schedulers, GigaThread): <https://www.nvidia.com/content/PDF/fermi_white_papers/NVIDIA_Fermi_Compute_Architecture_Whitepaper.pdf>
- NVIDIA, Kepler GK110/210 Architecture Whitepaper (register scoreboarding, compiler-side dependency checking): <https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/tesla-product-literature/NVIDIA-Kepler-GK110-GK210-Architecture-Whitepaper.pdf>
- AMD, Instinct MI200 (CDNA2) Instruction Set Architecture — wavefront = 64 work-items: <https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/instruction-set-architectures/instinct-mi200-cdna2-instruction-set-architecture.pdf> (ISA guides indexed at <https://gpuopen.com/amd-gpu-architecture-programming-documentation/>)
- E. Lindholm, J. Nickolls, S. Oberman, J. Montrym, "NVIDIA Tesla: A Unified Graphics and Computing Architecture," IEEE Micro, 2008. doi:10.1109/MM.2008.31

---
Task ID: 64-2
Probed URLs (all returned 200 unless noted):
- https://docs.nvidia.com/cuda/cuda-c-programming-guide/ (200; now carries a legacy banner pointing to the CUDA 13 rewrite)
- https://docs.nvidia.com/cuda/cuda-programming-guide/ (200) and /05-appendices/compute-capabilities.html (200), /02-basics/writing-cuda-kernels.html (200), /05-appendices/cuda-cpp-execution-model.html (200)
- https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/ (200; Occupancy / Hiding Register Dependencies / Effects of Shared Memory verified verbatim)
- https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__OCCUPANCY.html (200)
- https://www.nvidia.com/content/gtc-2010/pdfs/2238_gtc2010.pdf (200, PDF; Little's law slide "Needed parallelism = Latency x Throughput", G80 ≈192 ops, GTX480 576-thread result)
- https://www.nvidia.com/content/PDF/fermi_white_papers/NVIDIA_Fermi_Compute_Architecture_Whitepaper.pdf (200, PDF; warp=32, dual-issue, scoreboard quotes)
- https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/tesla-product-literature/NVIDIA-Kepler-GK110-GK210-Architecture-Whitepaper.pdf (200, PDF; multi-port register scoreboard, compiler-provided latency encoding)
- https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/instruction-set-architectures/instinct-mi200-cdna2-instruction-set-architecture.pdf (200, PDF; "Wavefront: A collection of 64 work-items"); legacy developer.amd.com/wordpress media paths redirect (301) to amd.com hub
- https://gpuopen.com/amd-gpu-architecture-programming-documentation/ (200; current AMD ISA index)
- https://doi.org/10.1109/MM.2008.31 verified via https://api.crossref.org/works/10.1109/MM.2008.31 (Lindholm/Nickolls/Oberman/Montrym, IEEE Micro, 2008)
- https://developer.nvidia.com/blog/cuda-refresher-cuda-programming-model/ (200; checked for Little's law content — no warp-level material, not cited)
Stage summary: wrote src/arch/advanced/warp-scheduling.md (220 lines): per-cycle scheduler model with verified guide quotes; ASCII scoreboard/stall diagram (text fence, no mermaid) plus stall-cause-to-lever table; occupancy definition + cc 8.0 limits table + 32-reg/100%-occupancy rule; dependency-free deterministic python occupancy calculator (6 fixed configs, granularity-aware, prints limiting resource) with verbatim stdout; Little's-law latency-hiding math (4L rule, in-flight-bytes estimate) in a table; divergence recap cross-linked (no re-teaching); ILP vs TLP; occupancy-is-not-throughput pitfalls; 4 interview Q&A; 10 references. Cross-links: cuda-programming.md, ../parallelism/cuda.md, ../parallelism/gpu.md, ooo-execution.md, ../pipelining/data-hazards.md. QA: python3 scripts/qa_page.py — CLEAN (220 lines, 1 py fence, demo output verbatim MATCH, no issues).
