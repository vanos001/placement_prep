# CUDA Graphs: Killing Kernel-Launch Overhead

A modern GPU executes a micro-kernel in 2-3 microseconds, but *submitting* that kernel from the CPU costs a comparable amount of time: argument packing, driver validation, command-buffer writes, doorbell rings. A workload of many small kernels (simulation timesteps, LLM decode steps, pre/post-processing chains) can spend more time sequencing work than executing it. CUDA Graphs (introduced in CUDA 10.1) fix this with two moves: build the whole DAG of operations once, then replay it with a single launch.

This page covers the launch-overhead problem, stream capture, the node/edge model, the instantiate/replay/update lifecycle, and production use in vLLM. For the underlying programming model (grids, blocks, streams), see [CUDA Programming Model](./cuda-programming.md); for kernel-fusion context, see [GPU/HPC Programming](../parallelism/gpu-hpc.md).

## The Launch-Overhead Problem

Every `kernel<<<...>>>` call is CPU work. The driver validates pointers, packs launch descriptors, and enqueues commands — microseconds per launch, even before the GPU does anything. If kernels are short and the CPU cannot run ahead (per-step syncs, data-dependent next launches), the GPU idles between kernels. NVIDIA's walkthrough measures this on a Tesla V100 (CUDA 10.1): a kernel that runs 2.9 us costs 9.6 us per launch when synchronized per kernel [2].

```text
One-by-one, sync per step (CPU cannot run ahead)          time -->
CPU   [8us submit][8us submit][8us submit][8us submit] ...
GPU        [ 20us kernel  ][ 20us kernel  ][ 20us kernel ] ...
      ^^^^
      GPU idle: waits for each new launch
Per-kernel wall cost = 8 us CPU + 20 us GPU = 28 us
100 kernels: 2800 us wall, GPU busy only 2000/2800 = 71%

One cudaGraphLaunch (whole DAG submitted once)            time -->
CPU   [8us submit]                          then the CPU is free
GPU        [20us][20us][20us] ... [20us]    100 nodes, back-to-back
Wall = 8 + 100 x 20 = 2008 us, GPU busy 2000/2008 = 99.6%
```

Two costs combine here: the CPU-side submit gap (driver work per launch) and GPU-side front-end setup (the GPU command processor also prepares each launch). Moving the sync out of the inner loop lets launches overlap execution (3.8 us per kernel in the same experiment) but still pays per-launch costs; only the graph removes the per-kernel CPU work entirely (3.4 us per kernel) [2].

The programming guide states the principle directly: graph definition is separated from execution, so "CPU launch costs are reduced compared to streams, because much of the setup is done in advance" [1].

## Stream Capture Mechanics

The ergonomic way to build a graph is **stream capture**: bracket existing stream code with `cudaStreamBeginCapture` / `cudaStreamEndCapture`. Inside the bracket, work launched into the stream is *not* enqueued for execution — it is appended to an internal graph being built. Dependencies follow stream order; library calls that use the stream are captured too [1].

```text
capture ON                                   capture OFF
|<----------- recorded, NOT executed -------->|
cudaStreamBeginCapture(stream)
  A<<<stream>>>        (node A)
  B<<<stream>>>        (node B, after A: stream order -> edge A->B)
  memsetAsync(stream)  (node M, after B)
cudaStreamEndCapture(stream, &graph)   -->   cudaGraph_t
                                              |
                                  cudaGraphInstantiate(&exec, graph)
                                              |
                                  cudaGraphLaunch(exec, stream)  x N replays
```

Cross-stream capture expresses real DAG edges with events: record an event on the capturing stream, make other streams `cudaStreamWaitEvent` on it (fork), and reverse the pattern to join [1]. `cudaStreamBeginCapture` also takes a restriction mode such as `cudaStreamCaptureModeGlobal`. The guide's hard gotchas [1]:

- Capture works on any stream **except** the legacy NULL stream; `cudaStreamPerThread` is fine.
- If a capturing stream was not created with `cudaStreamNonBlocking`, any use of the legacy stream — or any synchronous API — invalidates the capture, because the legacy handle implicitly spans every stream in the context.
- A few async APIs (`cudaStreamAttachMemAsync`) are simply not graph-capturable and error on a capturing stream.
- Once an invalid operation poisons the capture, every subsequent use of the associated streams errors until `cudaStreamEndCapture` returns an error and a NULL graph.

The explicit alternative builds the graph by hand: `cudaGraphCreate` plus `cudaGraphAddKernelNode` / `cudaGraphAddMemcpyNode`, passing each node's dependency list directly — verbose, but it gives exact control over edges.

## The Graph as a DAG of Nodes

A graph is a set of **nodes** (operations) connected by **edges** (dependencies). An operation runs as soon as every node it depends on completes; the CUDA system decides scheduling. Node types include kernels, memory copies, memsets, empty nodes, event record/wait, child graphs, and conditional nodes [1].

```text
                 fork (2 edges out)         join (2 edges in)
              +----> [memset out] ----+
[copy in] ----+                       +----> [reduce] ----> [copy result]
              +----> [memset res] ----+

edges = "cannot start until all upstream nodes finish"
independent branches run concurrently on the GPU, no CPU involvement
```

This is the difference from streams: a stream is a *total order* enforced one op at a time as the CPU submits them; a graph is a *partial order* the device can walk alone. A single `cudaGraphLaunch` submits the entire DAG, and the GPU front-end interleaves independent branches without waiting for the CPU to catch up. Task-graph runtimes express the same idea (DAG of dependent tasks, runtime schedules them) — see [MPI Parallelism](../../hpc/mpi-parallelism.md).

## Lifecycle: Capture, Instantiate, Launch, Update

| Stage | API | When it runs | Cost / notes |
|---|---|---|---|
| Capture or build | `cudaStreamBeginCapture`/`EndCapture`, or `cudaGraphCreate` + `cudaGraphAddKernelNode` | once per graph version | ops recorded, not executed; topology fixed here |
| Instantiate | `cudaGraphInstantiate` | once per graph | creates a pre-initialized `cudaGraphExec_t`; ~400 us for a 20-kernel graph in NVIDIA's measurement [2] |
| Launch (replay) | `cudaGraphLaunch` | every step/iteration | one CPU call submits the whole DAG; first launch ~33% slower, then steady [2] |
| Param update | `cudaGraphExecKernelNodeSetParams`, `cudaGraphExecUpdate` | when inputs change | in-place patch of pointers/params; skips topology checks, cheaper than re-instantiating [1] |
| Re-instantiate | `cudaGraphInstantiate` | topology changed | node adds/removes or type changes force a full rebuild [1] |

The update path matters because graphs bake in fixed pointers and shapes at capture time. Same topology, new input buffer? Patch node params and replay.

Different batch size or a data-dependent kernel choice? That is a topology change — re-capture and re-instantiate, which is why runtimes capture one graph per shape bucket instead of re-capturing per step.

## When Graphs Win (and When They Do Not)

Win:

- **Many small kernels, repeated**: decode steps, timestep loops, per-layer pre/post-processing. The submit gap dominates; replay amortizes it to ~zero.
- **Fixed structure per shape**: the graph is captured once per (shape, config) bucket and replayed thousands of times — instantiation cost amortizes away [2]. Breakeven arithmetic from NVIDIA's own numbers: instantiate costs ~400 us once; the graph saves ~6.2 us per kernel (9.6 vs 3.4) x 20 kernels ≈ 124 us per replay, so it pays for itself after roughly 4 replays.
- **Multi-stream fan-out/fan-in**: capture expresses fork/join once; replay gets the concurrency without re-submitting events.

Lose or need care:

- **Few large kernels**: launch overhead is already hidden behind execution; nothing to reclaim.
- **Fully async independent streams with long kernels**: pipelining already hides the CPU gap (see the sweep's crossover below).
- **Shape-hopping workloads**: every new topology forces re-capture + re-instantiate; churn can cost more than the launches saved.
- **The graph still has residual GPU-side dispatch per node** — graphs cut CPU submission, they do not make kernels faster. Fusion (fewer, bigger kernels) and graphs (cheap sequencing) are complementary, not substitutes.

## Production Use: vLLM Decode Steps

LLM inference is the canonical graph workload: every decode step runs the same layer sequence with small, latency-critical kernels. vLLM's v1 engine captures CUDA graphs by default and dispatches per batch composition: modes `NONE`, `PIECEWISE` (attention stays eager, everything else is graphed), `FULL` (whole step captured), and the default `FULL_AND_PIECEWISE` (full graphs for uniform decode batches, piecewise elsewhere) [3]. Capture is per batch-size bucket — shapes must match a captured graph to replay.

`--enforce-eager` disables the graphs entirely and runs plain eager PyTorch, useful for debugging [4]. The design note reports the graphed modes are the most performant setting for low latency, especially for small models and MoEs [3]. Walk through the serving-side view in [vLLM](../../llm/llm-serving/vllm.md).

## Worked Simulation: Makespan of 100 Small Kernels

The model below is pure arithmetic, calibrated to the problem above: each naive launch costs 8 us of CPU-side time and is serialized with its kernel (the per-step-sync pattern); the graph pays submit once. Then the kernel GPU time is swept to find where graphs stop mattering.

```python
"""Launch overhead vs one graph launch: deterministic makespan model.

Fixed assumptions (pure arithmetic, no measurement):
- Each naive launch costs SUBMIT_US of CPU-side time (argument packing,
  driver validation, submission ioctl) and is serialized with the kernel
  it submits (per-step sync: CPU waits, then prepares the next launch).
- The graph path pays the CPU submit cost once; the GPU then runs all
  nodes back-to-back from the pre-built DAG, no CPU in the loop.
"""
N_KERNELS = 100
SUBMIT_US = 8.0
K_US = 20.0

def naive_makespan(n, gap, k):
    return n * (gap + k)

def graph_makespan(n, gap, k):
    return gap + n * k

naive = naive_makespan(N_KERNELS, SUBMIT_US, K_US)
graph = graph_makespan(N_KERNELS, SUBMIT_US, K_US)
print(f"Workload: {N_KERNELS} kernels x {K_US:.0f} us GPU each")
print(f"naive one-by-one : {N_KERNELS} x ({SUBMIT_US:.0f} submit + {K_US:.0f} run) = {naive:.0f} us")
print(f"one graph launch : {SUBMIT_US:.0f} submit + {N_KERNELS} x {K_US:.0f} run    = {graph:.0f} us")
print(f"speedup          : {naive:.0f} / {graph:.0f} = {naive / graph:.2f}x")
print()
print("Sweep kernel GPU time 5..100 us, step 5: overhead-dominated -> execution-dominated")
print(f"{'k_us':>5} | {'naive_us':>8} | {'graph_us':>8} | {'speedup':>7} | {'cpu_overhead':>12}")
crossover = None
for k in range(5, 101, 5):
    nv = naive_makespan(N_KERNELS, SUBMIT_US, k)
    gr = graph_makespan(N_KERNELS, SUBMIT_US, k)
    oh = 100.0 * (nv - gr) / nv
    if oh < 10.0 and crossover is None:
        crossover = (k, oh)
    print(f"{k:>5} | {nv:>8.0f} | {gr:>8.0f} | {nv / gr:>6.2f}x | {oh:>11.1f}%")
print()
print(f"crossover: CPU overhead first drops below 10% of the naive makespan at k = {crossover[0]} us")
print(f"kernel time ~{crossover[0] / SUBMIT_US:.0f}x the {SUBMIT_US:.0f} us submit gap; beyond this graphs stop mattering")
```

Real output:

```text
Workload: 100 kernels x 20 us GPU each
naive one-by-one : 100 x (8 submit + 20 run) = 2800 us
one graph launch : 8 submit + 100 x 20 run    = 2008 us
speedup          : 2800 / 2008 = 1.39x

Sweep kernel GPU time 5..100 us, step 5: overhead-dominated -> execution-dominated
 k_us | naive_us | graph_us | speedup | cpu_overhead
    5 |     1300 |      508 |   2.56x |        60.9%
   10 |     1800 |     1008 |   1.79x |        44.0%
   15 |     2300 |     1508 |   1.53x |        34.4%
   20 |     2800 |     2008 |   1.39x |        28.3%
   25 |     3300 |     2508 |   1.32x |        24.0%
   30 |     3800 |     3008 |   1.26x |        20.8%
   35 |     4300 |     3508 |   1.23x |        18.4%
   40 |     4800 |     4008 |   1.20x |        16.5%
   45 |     5300 |     4508 |   1.18x |        14.9%
   50 |     5800 |     5008 |   1.16x |        13.7%
   55 |     6300 |     5508 |   1.14x |        12.6%
   60 |     6800 |     6008 |   1.13x |        11.6%
   65 |     7300 |     6508 |   1.12x |        10.8%
   70 |     7800 |     7008 |   1.11x |        10.2%
   75 |     8300 |     7508 |   1.11x |         9.5%
   80 |     8800 |     8008 |   1.10x |         9.0%
   85 |     9300 |     8508 |   1.09x |         8.5%
   90 |     9800 |     9008 |   1.09x |         8.1%
   95 |    10300 |     9508 |   1.08x |         7.7%
  100 |    10800 |    10008 |   1.08x |         7.3%

crossover: CPU overhead first drops below 10% of the naive makespan at k = 75 us
kernel time ~9x the 8 us submit gap; beyond this graphs stop mattering
```

Read the sweep as the overhead/execution boundary: at 5 us kernels the CPU gap is most of the wall time (graphs win 2.56x); by 75 us kernels the same 8 us gap is under 10% of the makespan and graphs approach irrelevance. The crossover sits at roughly kernel-time ≈ 10x the submit gap.

One honest caveat: if launches are fully asynchronous and independent, the CPU can run ahead and hide the gap once kernels outlast it — the serialized model above reflects the common per-step-dependency pattern, which is also where NVIDIA measured 9.6 us vs 3.4 us per kernel [2].

## Interview Questions

**Q1. Your GPU profiler shows kernels taking 3 us each, but the end-to-end step takes 3x that. What is happening, and what are two fixes?**

The difference is launch overhead: CPU-side driver work plus GPU front-end setup per launch, exposed because kernels are shorter than the per-launch cost. Fix one: fuse kernels (fewer, larger launches). Fix two: CUDA Graphs — capture the step once, replay with a single `cudaGraphLaunch`, so per-step CPU work drops from N launches to one. They compose: fuse first, graph what remains.

**Q2. Explain stream capture end to end. What does the GPU do with a kernel launched between `cudaStreamBeginCapture` and `cudaStreamEndCapture`, and how do cross-stream dependencies become graph edges?**

Nothing executes. Capture mode diverts stream work into an internal graph — stream order becomes dependency edges. For multi-stream capture, an event recorded on the capturing stream plus `cudaStreamWaitEvent` on a second stream creates a fork edge; reversing the pattern joins the branches. After `EndCapture`, `cudaGraphInstantiate` builds the executable form and any number of `cudaGraphLaunch` calls replay it.

**Q3. A graph was captured for a fixed input tensor. The next iteration uses a different buffer and batch size. What are your options, and what does each cost?**

Same topology, new pointers: individual node updates (`cudaGraphExecKernelNodeSetParams`) or whole-graph `cudaGraphExecUpdate` against a re-captured `cudaGraph_t` — in-place and cheap, but the topology must be identical. Different shapes or node counts mean topology changed: re-capture and re-instantiate, paying the full setup cost (~hundreds of microseconds). Production runtimes avoid the churn by capturing one graph per shape bucket and padding odd shapes into the nearest bucket.

**Q4. Why does vLLM capture CUDA graphs for decode but keep prefill (piecewise) eager, and what knob turns the whole thing off?**

Decode steps repeat a fixed layer sequence with small kernels and strict latency targets — ideal for full-graph replay, and batches are padded to captured size buckets. Prefill shapes vary token-by-token and mix in graph-incompatible attention work, so vLLM runs it piecewise (graphs around attention, attention eager) or eager. The dispatcher picks per batch composition (`FULL_AND_PIECEWISE` is the default); `--enforce-eager` disables capture for debugging [3][4].

## References

- [1] NVIDIA, *CUDA C++ Programming Guide*, §4.2 "CUDA Graphs" (graph structure, node types, stream capture, updates) — https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html
- [2] A. Gray, "Getting Started with CUDA Graphs," NVIDIA Technical Blog (V100 measurements: 2.9 us kernel, 9.6/3.8/3.4 us per kernel across submission styles, ~400 us instantiate) — https://developer.nvidia.com/blog/cuda-graphs/
- [3] vLLM docs, "CUDA Graphs" (v1 design: CUDAGraphMode, dispatcher, decode vs piecewise capture) — https://docs.vllm.ai/en/latest/design/cuda_graphs/
- [4] vLLM docs, "Engine Arguments" (`--enforce-eager` disables CUDA graph capture) — https://docs.vllm.ai/en/latest/configuration/engine_args/

---

## Worklog

Task ID: 64-3

Probed URLs (all fetched live during research):
- https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#graph — HTTP 200 but redirects to the new guide site; the Graph chapter now lives at https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html (cited as [1]; verified title "4.2. CUDA Graphs", CUDA 13.3; confirmed in-page: cudaStreamBeginCapture/EndCapture semantics, node-type list, fork/join event capture, cudaGraphInstantiate, cudaGraphLaunch, cudaGraphExecUpdate, cudaGraphExecKernelNodeSetParams, capture modes)
- https://developer.nvidia.com/blog/cuda-graphs/ — HTTP 200, "Getting Started with CUDA Graphs," Alan Gray, Sep 5, 2019 (cited as [2]; all numbers quoted from fetched body text)
- https://docs.vllm.ai/en/latest/design/cuda_graphs/ — HTTP 200 (cited as [3]; verified CUDAGraphMode enum, FULL_AND_PIECEWISE default, uniform-decode capture)
- https://docs.vllm.ai/en/latest/configuration/engine_args/ — HTTP 200 (cited as [4]; verified `--enforce-eager` text)
- Dead ends not cited: docs.vllm.ai performance_optimization (404), vLLM piecewise_cuda_graphs.html (redirects to /contributing/), CUDA archive sitemap (404). No DOIs used; no paper claims made.

Stage summary: wrote `src/arch/advanced/cuda-graphs.md` (~230 lines): launch-overhead problem with ASCII timelines, stream-capture ASCII, DAG node/edge model, lifecycle table (capture/instantiate/launch/update), win/lose list, vLLM production section cross-linking llm/llm-serving/vllm.md and the cuda-programming exemplar, deterministic python makespan demo + real stdout, 4 interview Q&As, 4 verified references. Cross-links: ./cuda-programming.md, ../parallelism/gpu-hpc.md, ../../llm/llm-serving/vllm.md. No git commands run (integrator commits). QA: `python3 /home/z/my-project/scripts/qa_page.py` passed clean.
