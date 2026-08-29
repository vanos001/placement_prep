# Prefill/Decode Disaggregation: Splitting the Two Phases of LLM Inference

Every LLM request is really two jobs stapled together. **Prefill** reads the whole prompt in one matrix-matrix pass and produces the initial KV cache. **Decode** then emits output tokens one at a time, re-reading every weight and the entire KV cache on every step. The phases saturate different parts of the GPU, so one co-located fleet must pick a single hardware profile that serves both badly. Prefill/decode (PD) disaggregation runs prefill on one pool of GPUs, decode on another, and ships the KV cache between them over a fast interconnect.

Scope: this page is the PD split itself - phase/resource mismatch, the two latency clocks, KV transfer schemes, P:D fleet sizing, arrival-aware routing, and when NOT to disaggregate. The broader umbrella (remote KV stores, RDMA vs CXL memory pooling) lives in [Disaggregated Inference Architecture](./disaggregated-inference.md).

## Two Phases, Opposite Hardware Profiles

For a dense fp16 model with P parameters, arithmetic intensity is the whole story. A prefill over m prompt tokens does ~2Pm FLOPs but moves ~2P weight bytes once, so its intensity is roughly **m FLOPs/byte**. A decode step at batch c does ~2Pc FLOPs against the same ~2P bytes, so its intensity is roughly **c FLOPs/byte** - the batch size IS the intensity.

An H100-class GPU pairs ~990 dense-bf16 TFLOPS with ~3.35 TB/s of HBM - a ridge point of ~296 FLOPs/byte, or ~118 at a realistic 40% MFU. So prefill is compute-bound for any prompt longer than a few hundred tokens, with wall time `t_p(m) = 2Pm / FLOPS_eff`, while decode is memory-bound until the batch reaches that same ~100-300 threshold, with step time `t_step(c) = ovh + max(2P/BW_mem, 2Pc/FLOPS_eff)`.

| Phase | Bottleneck | Batch scaling | Wall time (8B fp16, H100-class) | Wants |
|-------|-----------|---------------|---------------------------------|-------|
| Prefill (m = 4250 avg) | FLOPs | tokens run in parallel | ~172 ms | compute, no interruptions |
| Decode (step, c = 30) | HBM bandwidth | step time flat, then compute | ~9.8 ms/token | bandwidth, big KV memory, steady cadence |

Co-location fights this profile: one GPU must deliver multi-hundred-millisecond compute bursts AND a fixed ~10 ms heartbeat, and only one phase ever needs the KV cache it competes for. Splitwise (ISCA 2024) pushes the logic further: prefill fits compute-leaning, smaller-memory SKUs; decode wants bandwidth- and memory-heavy ones.

## The Two Clocks: TTFT and TBT

Serving SLOs are stated on two clocks, and each phase owns one. **TTFT** (time to first token) = queue + prefill + transfer if disaggregated + first step: owned by prefill. **TBT/TPOT** (time between streamed tokens / time per output token) = steady-state step time: owned by decode.

On a co-located GPU, one long prefill stalls every decode stream sharing it: a 4K-token prefill is ~150-300 ms of exclusive compute, so other users' inter-token gaps spike by 10x or more. Chunked prefill (prompt slices interleaved with decode steps) bounds that spike - Sarathi-Serve (OSDI 2024) shows stall-free chunked schedules raise serving capacity 2.6x (7B, one A100) to 5.6x (180B with pipeline parallelism) over vLLM under tail-latency constraints - but cannot remove the coupling, because both phases still bid for the same FLOPs and bandwidth.

DistServe (OSDI 2024) made the cost of that coupling quantitative with **goodput**: the request rate at which BOTH the TTFT and TPOT SLOs hold for >90% of requests. Disaggregating the phases and co-optimizing per-phase parallelism serves 7.4x more requests within SLO, or meets a 12.6x tighter SLO, versus state-of-the-art co-located baselines. Co-located chunked prefill trades TTFT against TBT on one GPU; disaggregation decouples the clocks so each fleet is provisioned for its own SLO.

## Moving the KV Cache: The Tax That Buys Independence

The decode GPU needs the exact KV cache the prefill GPU computed. KV size is exact and non-negotiable (no lossy tricks by default): `KV bytes = 2 (K,V) x layers x kv_heads x head_dim x bytes/elem x tokens`.

| Model (fp16, GQA-8, head_dim 128) | Layers | KV bytes/token | 4K context | 8K context |
|-----------------------------------|--------|----------------|------------|------------|
| 8B dense                          | 32     | 128 KB         | 512 MB     | 1.05 GB    |
| 70B dense                         | 80     | 320 KB         | 1.31 GB    | 2.62 GB    |

Transfer time for the 8K-context 70B cache (2.62 GB):

| Link                 | Payload bandwidth | Transfer time | Reach        |
|----------------------|-------------------|---------------|--------------|
| PCIe 5.0 x16         | 64 GB/s           | 41 ms         | host-to-host |
| 400G RDMA (IB/RoCE)  | 50 GB/s           | 52 ms         | cluster-wide |
| NVLink 4 (H100 node) | 900 GB/s          | 2.9 ms        | within node  |

Naive transfer adds the full link time to TTFT, so production systems overlap it with compute:

```
MONOLITHIC (post-prefill)    LAYER-WISE STREAMING       PROMPT-CHUNK PIPELINE
prefill [############]       prefill [############]     prefill [###][###][###]
xfer                    |    xfer L1..Ln overlapped    xfer ck |  ck  |  ck
TTFT = t_p + t_xfer          TTFT = t_p + small tail    TTFT = t_p + small tail
```

- **Layer-wise streaming**: each layer's KV is RDMA-written while the next layer computes; the transfer hides under prefill and only a small tail remains. TensorRT-LLM's prototype disaggregated service defaults to exactly this (`TRTLLM_DISABLE_KV_CACHE_TRANSFER_OVERLAP` defaults to off, i.e. overlap on).
- **Prompt-chunk pipelining**: chunked prefill across two pools; chunk k's KV ships while chunk k+1 prefills. The same primitive that bounds TBT co-located also pipelines the handoff disaggregated.
- **Monolithic**: simplest; correct for short prompts or intra-node NVLink where the tax is single-digit ms.

Consistency matters: KV must arrive bit-exact and in layer order, and the decode GPU must reserve memory before admission. If the decode pool cannot admit, the transfer is wasted work - which is why routing and sizing decide whether disaggregation pays.

## Sizing the P:D Split

Steady state demands `P x (1/E[t_p]) >= lambda` for prefill and `D x c/t_step(c) >= lambda x E[N_out]` for decode, which gives the split:

`D/P = (E[N_out] x t_step(c)) / (c x E[t_p])` - with the demo parameters below: `(280 x 9.8 ms / 30) / 172 ms = 0.53`, so an 8-GPU fleet wants roughly 5-6 prefill : 2-3 decode GPUs.

The right answer moves with the traffic. Chat (short prompts, long outputs) drives D up; RAG and long-context (huge prompts, short answers) drive P up. Two production anchors: Splitwise sizes the split per objective (throughput, cost, power) and gets 1.4x throughput at 20% lower cost, or 2.35x throughput at equal cost/power. Mooncake (FAST 2025, Kimi's platform) treats the whole cluster as a KVCache-centric system whose scheduler jointly routes requests and rebalances prefill/decode resources, with prediction-based early rejection when overloaded - reporting up to a 525% throughput lift in long-context scenarios and 75% more requests on real workloads. Sizing is not set-and-forget: recompute P:D as arrival rate and length distributions drift, or the wrong pool starves (the demo below makes a 1P:7D fleet unusable).

## Routing: Arrival-Aware, Not Round-Robin

The router makes three coupled decisions per request:

1. **Prefill placement** by predicted cost (prompt length is known at admission) and queue depth - scheduling known-size jobs, which is easy to do well.
2. **KV affinity** - on a prefix-cache hit (system prompt, shared RAG context), route to where that KV already lives instead of re-prefilling; Mooncake's KVCache-centric scheduler exists largely for this.
3. **Decode placement** - pick a decode GPU with KV memory reserved for the incoming cache; backpressure to prefill when decode saturates beats accepting work you cannot stream.

DistServe adds a bandwidth-aware twist: place the two pools so inter-pool link capacity matches the KV traffic the arrival rate implies - a 52 ms RDMA handoff is fine at low rates and a bottleneck at high ones.

## When NOT to Disaggregate

| Signal                               | Stay co-located because...                     | Disaggregate because...                |
|--------------------------------------|------------------------------------------------|----------------------------------------|
| Low utilization, SLOs met            | transfer + ops cost buys nothing               | (don't)                                |
| Prompt << output (chat)              | prefill rarely blocks decode                   | only when decode SLO is tight at scale |
| Prompt >> output (RAG, long-context) |                                                | prefill interference dominates         |
| No RDMA/NVLink between pools         | PCIe-class transfer adds ~40+ ms to every TTFT | only with a fast interconnect          |
| Single node, small fleet             | NVLink makes pools pointless (2.9 ms handoff)  | multi-node, multi-tenant fleets        |
| Prefix-heavy traffic                 | cache hits skip prefill anyway                 | cache-miss-heavy mixed traffic         |

The honest summary: disaggregation converts a scheduling problem (protect decode from prefill) into a capacity-planning problem (size and connect two pools). Take that trade when you are capacity-constrained against SLOs at real load, not as a default architecture.

## A Model You Can Run: Sizing Sweep With a Crossover

The simulation below (pure stdlib, event-driven, roofline-calibrated for an 8B-class fp16 model on H100-class GPUs) compares a co-located fleet (strict chunk/step alternation as an idealized chunked prefill) against 1P:7D, 4P:4D and 6P:2D splits of the same 8 GPUs, at two arrival rates. The numbers are a MODEL, not a measurement: link contention, prefix caching and scheduler variance are simplified.

```python
import heapq, random
from collections import deque

PARAMS, HBM_BW = 8e9, 3.35e12        # 8B-class fp16 model; H100-class HBM bytes/s
WEIGHT_B = 2 * PARAMS                # weight bytes re-read every decode step
TFLOPS   = 0.40 * 990e12             # dense bf16 peak x achieved MFU
KV_B_TOK = 2 * 32 * 8 * 128 * 2      # 128 KB/token: 2 x 32L x 8 kv-heads x 128 x 2B
LINK_BW, LINK_OVH, STEP_OVH = 50e9, 2e-3, 5e-3   # RDMA payload, setup, per-step ovh
CHUNKS, N_GPUS, TTFT_SLO, TBT_SLO = 4, 8, 0.600, 0.100  # chunked prefill; SLOs, s

def prefill_time(n): return 2 * PARAMS * n / TFLOPS
def step_time(c):    return STEP_OVH + max(WEIGHT_B / HBM_BW, 2 * PARAMS * c / TFLOPS)
def xfer_time(n):    return LINK_OVH + KV_B_TOK * n / LINK_BW

def simulate(mode, lam, n_arr, p_pref, seed=7):
    rng = random.Random(seed)
    ev, seq = [], 0
    def push(t, kind, *pl):
        nonlocal seq
        heapq.heappush(ev, (t, seq, kind) + pl); seq += 1
    t = 0.0
    for i in range(n_arr):
        push(t, "ARR", i); t += rng.expovariate(lam)
    R = [dict(prompt=rng.randint(500, 8000), out=rng.randint(80, 480),
              arr=0.0, ft=None, lt=None, gap=0.0, chunks=0) for _ in range(n_arr)]
    ttft, gaps, done = [], [], 0
    P = p_pref if mode == "disagg" else 0
    G = N_GPUS - P
    pg = [dict(q=deque()) for _ in range(P)]             # dedicated prefill pool
    dg = [dict(q=deque(), batch={}, alt=False) for _ in range(G)]
    pbusy, dbusy = [False] * P, [False] * G

    def pump_pre(t, gi):                   # dedicated prefill: full unsplit job
        s = pg[gi]
        if s["q"] and not pbusy[gi]:
            pbusy[gi] = True
            push(t + prefill_time(R[s["q"][0]]["prompt"]), "PRE", gi)

    def pump_dec(t, gi):                   # decode-only pool: batched steps
        s = dg[gi]
        if s["batch"] and not dbusy[gi]:
            dbusy[gi] = True
            push(t + step_time(len(s["batch"])), "STEP", gi)

    def pump_colo(t, gi):                  # co-located: strict chunk/step alternation
        s = dg[gi]
        if dbusy[gi]: return
        if s["batch"] and (not s["q"] or not s["alt"]):
            dbusy[gi] = True; s["alt"] = True
            push(t + step_time(len(s["batch"])), "STEP", gi)
        elif s["q"] and (not s["batch"] or s["alt"]):
            dbusy[gi] = True; s["alt"] = False
            push(t + prefill_time(R[s["q"][0]]["prompt"]) / CHUNKS, "CHNK", gi, s["q"][0])
        elif s["batch"]:
            dbusy[gi] = True
            push(t + step_time(len(s["batch"])), "STEP", gi)
        elif s["q"]:
            dbusy[gi] = True
            push(t + prefill_time(R[s["q"][0]]["prompt"]) / CHUNKS, "CHNK", gi, s["q"][0])

    while done < n_arr:
        t, _, kind, *pl = heapq.heappop(ev)
        a = pl[0] if pl else None
        b = pl[1] if len(pl) > 1 else None
        if kind == "ARR":
            i = a; R[i]["arr"] = t
            if mode == "disagg":
                gi = min(range(P), key=lambda k: len(pg[k]["q"]) + pbusy[k])
                pg[gi]["q"].append(i); pump_pre(t, gi)
            else:
                gi = min(range(G), key=lambda k: len(dg[k]["q"]) + len(dg[k]["batch"]))
                dg[gi]["q"].append(i); pump_colo(t, gi)
        elif kind == "PRE":                # dedicated prefill done -> ship KV cache
            gi = a; pbusy[gi] = False
            i = pg[gi]["q"].popleft(); R[i]["pre"] = t
            push(t + xfer_time(R[i]["prompt"]), "XFER", i)
            pump_pre(t, gi)
        elif kind == "CHNK":               # one co-located prefill chunk done
            gi, i = a, b; dbusy[gi] = False
            s = dg[gi]; R[i]["chunks"] += 1
            if R[i]["chunks"] == CHUNKS:
                s["q"].popleft(); s["batch"][i] = R[i]["out"]
            pump_colo(t, gi)
        elif kind == "XFER":               # KV arrived: admit to least-loaded decode GPU
            i = a
            gi = min(range(G), key=lambda k: len(dg[k]["batch"]))
            dg[gi]["batch"][i] = R[i]["out"]; pump_dec(t, gi)
        elif kind == "STEP":
            gi = a; dbusy[gi] = False; s = dg[gi]
            for j in list(s["batch"]):
                s["batch"][j] -= 1
                if R[j]["ft"] is None:
                    R[j]["ft"] = t; ttft.append(t - R[j]["arr"])
                else:
                    gap = t - R[j]["lt"]; gaps.append(gap)
                    R[j]["gap"] = max(R[j]["gap"], gap)
                R[j]["lt"] = t
                if s["batch"][j] == 0:
                    del s["batch"][j]; done += 1
            (pump_dec if mode == "disagg" else pump_colo)(t, gi)
    return R, ttft, gaps, t

def pct(xs, q):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(q * len(xs)))]

hdr = "mode        split   lam  TTFTp50  TTFTp99  TBTp99  goodput  out tok/s per GPU"
print("model: 8B-class fp16 on H100-class GPUs | fleet: 8 GPUs | 400G RDMA handoff")
print("SLOs: TTFT <= 600 ms and max token gap <= 100 ms | 6000 arrivals/run (seed 7)")
print(hdr); print("-" * len(hdr))
for lam in (8.0, 28.0):
    for mode, split in (("colocated", "8G"), ("disagg", "1P:7D"),
                        ("disagg", "4P:4D"), ("disagg", "6P:2D")):
        p = 0 if mode == "colocated" else int(split[0])
        R, ttft, gaps, t_end = simulate(mode, lam, 6000, p)
        good = sum(1 for r in R if r["ft"] is not None and
                   r["ft"] - r["arr"] <= TTFT_SLO and r["gap"] <= TBT_SLO) / len(R)
        thr = 6000 / t_end * sum(r["out"] for r in R) / len(R) / 8
        print(f"{mode:11} {split:6} {lam:4.1f} {pct(ttft,.5)*1e3:7.1f}"
              f" {pct(ttft,.99)*1e3:8.1f} {pct(gaps,.99)*1e3:7.1f}"
              f" {good*100:7.1f}% {thr:14.0f}")
    print()
```

Output (real run of the code above):

```text
model: 8B-class fp16 on H100-class GPUs | fleet: 8 GPUs | 400G RDMA handoff
SLOs: TTFT <= 600 ms and max token gap <= 100 ms | 6000 arrivals/run (seed 7)

mode        split   lam  TTFTp50  TTFTp99  TBTp99  goodput  out tok/s per GPU
-----------------------------------------------------------------------------
colocated   8G      8.0   223.5    510.5    70.3    99.7%            284
disagg      1P:7D   8.0 145914.7 283242.8     9.8     0.0%            206
disagg      4P:4D   8.0   191.5    400.2     9.8   100.0%            284
disagg      6P:2D   8.0   187.6    348.5     9.8   100.0%            284

colocated   8G     28.0   313.4   1020.9    88.5    89.2%            980
disagg      1P:7D  28.0 406660.2 805519.7     9.8     0.0%            206
disagg      4P:4D  28.0 23337.6  45382.6     9.8     0.6%            810
disagg      6P:2D  28.0   251.6    695.2     9.8    97.2%            980
```

How to read it:

- **At lambda = 8 both designs are fine** (99.7% vs 100% goodput, same per-GPU throughput). Below the SLO knee, co-location is the right answer - the "when NOT to disaggregate" row made numeric.
- **The crossover is the arrival rate, not a fixed winner.** At lambda = 28 the co-located TTFT p99 nearly triples to 1021 ms and goodput drops to 89.2%, while the right split (6P:2D, matching the analytic D/P ~ 0.5) holds 97.2% with a flat 9.8 ms TBT p99 - decode never sees prefill.
- **The wrong split is worse than no split.** 1P:7D starves prefill (TTFT p50 in the *minutes*); 4P:4D is fine at low load and collapses at high load (0.6% goodput) because prefill demand (lambda x E[t_p] ~ 4.8 GPU-seconds/s) exceeds 4 GPUs. Sizing must track load and length distributions.
- Co-located TBT p99 of 70-89 ms is the chunk/step alternation tax; dedicated decode pools hold the ~10 ms step floor regardless of prefill load.

## Interview Angles

- "Why place prefill and decode on different hardware?" - intensity argument: prefill ~m FLOPs/byte, decode ~c; one compute:bandwidth ratio cannot serve both.
- "Chunked prefill already fixes interference - why disaggregate?" - chunking bounds TBT but the TTFT/TBT clocks stay coupled to one GPU's FLOPs; disaggregation removes the coupling and lets each pool scale to its own SLO.
- "What does the KV handoff cost, and when does it hurt?" - size it (320 KB/token for a 70B), overlap it layer-wise, and remember it is pure overhead if the decode pool cannot admit the request.
- "How would you size P:D?" - the D/P formula, then the twist: it is a function of arrival rate and length distribution, so it is monitored and re-balanced, not computed once.
- "Name a failure mode unique to PD systems." - split-brain overload: prefill keeps accepting work the decode pool cannot admit, stranding half-transferred KV on both sides (Mooncake's early-rejection exists for this).

## Cross-References

- [Disaggregated Inference Architecture](./disaggregated-inference.md) - KV-cache/memory pooling and RDMA vs CXL mechanics underneath the PD handoff.
- [GPU Cluster Scheduling](./gpu-cluster-scheduling.md) - gang scheduling and fairness; PD pools inherit these problems plus a phase coupling.
- [Inference Systems](../inference-systems.md) - serving stacks, autoscaling signals, SLO-based routing in the co-located world.
- [Batching & Scheduling](../../llm-serving/batching.md) - continuous batching and chunked prefill mechanics on a single pool.

## References

1. Y. Zhong, S. Liu, J. Chen, J. Hu, Y. Zhu, X. Liu, X. Jin, H. Zhang. DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving. OSDI 2024. https://arxiv.org/abs/2401.09670
2. P. Patel, E. Choukse, C. Zhang, A. Shah, I. Goiri, S. Maleki, R. Bianchini (Microsoft). Splitwise: Efficient Generative LLM Inference Using Phase Splitting. ISCA 2024. https://arxiv.org/abs/2311.18677
3. R. Qin, Z. Li, W. He, M. Zhang, Y. Wu, W. Zheng, X. Xu. Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving. FAST 2025. https://arxiv.org/abs/2407.00079
4. A. Agrawal, N. Kedia, A. Panwar, J. Mohan, N. Kwatra, B. S. Gulavani, A. Tumanov, R. Ramjee. Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve. OSDI 2024. https://arxiv.org/abs/2403.02310
5. vLLM documentation. Disaggregated Prefilling (experimental), with pluggable KV-transfer connectors (Mooncake, LMCache). https://docs.vllm.ai/en/latest/features/disagg_prefill.html
6. NVIDIA TensorRT-LLM documentation. Disaggregated Service (Prototype) - context/generation phase split with overlappable KV-cache transfer. https://nvidia.github.io/TensorRT-LLM/advanced/disaggregated-service.html
