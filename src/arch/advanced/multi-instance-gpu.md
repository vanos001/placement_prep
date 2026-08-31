# NVIDIA Multi-Instance GPU (MIG)

One A100 costs more than a small car, and a serving pod that peaks at 3 GB of HBM and 14 SMs wastes the other 90% of the board — or drags every other tenant through a shared scheduler. MIG is NVIDIA's answer: firmware and hardware partitioning of an Ampere-or-newer GPU (compute capability >= 8.0) into up to **seven GPU Instances**, each of which looks like a small physical GPU with dedicated SMs, a private L2 slice, and its own path through the memory system — no hypervisor, no time-slicing between tenants. This page works from the current [MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/) and builds the profile tables, the GI/CI model, the isolation fine print, and the Kubernetes operational story on top of it.

## The slice model: 8 memory slices x 7 SM slices

The guide's [concepts page](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/concepts.html) defines the currency of MIG partitioning:

- **GPU memory slice** — the smallest fraction of memory *resources*: roughly 1/8 of total capacity **and bandwidth**, including its own memory controllers and cache. This is why a noisy neighbor saturating DRAM cannot touch your instance.
- **GPU SM slice** — roughly 1/7 of the SMs.
- **GPU Instance (GI)** — a set of memory slices + SM slices + engines (copy engines, NVDEC, JPEG, OFA), protected by hardware: the on-chip crossbar ports, L2 cache banks, memory controllers, and DRAM address busses are assigned uniquely to one instance.
- **Compute Instance (CI)** — a further subdivision of a GI's SM slices; CIs *share* the parent GI's memory and engines but own their SMs exclusively.

On the A100-SXM4-40GB that decomposition is concrete: 8 memory slices of 5 GB and 7 SM slices. `nvidia-smi mig -lgip` reports 14 SMs per 1g slice and 39.25 GiB (4.75 GiB per slice) when the whole GPU is handed to one 7g.40gb instance — the seven-slice grid deliberately leaves a few of the die's SMs unassigned. Isolation comes from the fabric, not the scheduler: each instance's traffic physically cannot address another instance's L2 banks or DRAM channels.

```text
A100-SXM4-40GB in MIG mode: 8 memory slices x 7 SM slices
             col0   col1   col2   col3   col4   col5   col6   col7
            +------+------+------+------+------+------+------+------+  col spans from
 4g.20gb    |================ 4 slices = 20 GB, 4 SM slices =====|      |  the driver's
 2g.10gb    |                    |===== 2 = 10 GB, 2 SM =====|      |      |  -lgipp output
 1g.5gb     |                    |                    |== 1 =|      |      |  (4-2-1 layout)
            +------+------+------+------+------+------+------+------+  slice 7:
             5 GB   5 GB   5 GB   5 GB   5 GB   5 GB   5 GB   FREE     5 GB stranded
```

The stranded column is not a drawing artifact: 4g.20gb + 2g.10gb + 1g.5gb is the driver's own documented 4-2-1 placement (`0:4`, `4:2`, `6:1`), and 35 of the 40 GB is all that geometry can reach. Fragmentation is geometric and persistent — as the guide puts it, the physical position of one GI determines which GIs can be instantiated next to it.

## Profile tables (transcribed from the guide)

Profile names encode the geometry: `Ng.Mgb` = N SM slices + M GB of memory. The `+me` suffix adds media engines (one NVDEC/NVJPEG/OFA set; only one 1g profile per GPU may carry it), new `+gfx`/`-me`/`+me.all` variants appear on GB20X RTX PRO boards, and the memory number scales with the SKU: an A100-80GB renames every profile (`1g.10gb`, `2g.20gb`, `3g.40gb`, `4g.40gb`, `7g.80gb`).

**A100-SXM4-40GB** (per the [Supported MIG Profiles](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/supported-mig-profiles.html) table; A100-80GB scales memory x2):

| Profile | Mem frac | SM frac | L2 | CEs | NVDEC/JPEG/OFA | Max instances |
|---------|----------|---------|----|-----|----------------|---------------|
| 1g.5gb | 1/8 | 1/7 | 1/8 | 1 | 0 / 0 / 0 | 7 |
| 1g.10gb | 1/8 | 1/7 | 1/8 | 1 | 1 / 0 / 0 | 4 |
| 2g.10gb | 2/8 | 2/7 | 2/8 | 2 | 1 / 0 / 0 | 3 |
| 3g.20gb | 4/8 | 3/7 | 4/8 | 3 | 2 / 0 / 0 | 2 |
| 4g.20gb | 4/8 | 4/7 | 4/8 | 4 | 2 / 0 / 0 | 1 |
| 7g.40gb | Full | 7/7 | Full | 7 | 5 / 1 / 1 | 1 |

**H100 80GB (PCIe and SXM5)** — note what differs from A100: every 1g/2g slice carries a JPEG engine, the wide `1g.20gb` (1 SM slice over 2 memory slices) exists, and the 4-SM profile is `4g.40gb` (H100 has no `4g.20gb`):

| Profile | Mem frac | SM frac | L2 | CEs | NVDEC/JPEG/OFA | Max instances |
|---------|----------|---------|----|-----|----------------|---------------|
| 1g.10gb | 1/8 | 1/7 | 1/8 | 1 | 1 / 1 / 0 | 7 |
| 1g.20gb | 1/4 | 1/7 | 1/8 | 1 | 1 / 1 / 0 | 4 |
| 2g.20gb | 2/8 | 2/7 | 2/8 | 2 | 2 / 2 / 0 | 3 |
| 3g.40gb | 4/8 | 3/7 | 4/8 | 3 | 3 / 3 / 0 | 2 |
| 4g.40gb | 4/8 | 4/7 | 4/8 | 4 | 4 / 4 / 0 | 1 |
| 7g.80gb | Full | 7/7 | Full | 8 | 7 / 7 / 1 | 1 |

**A30-24GB** — only 4 memory slices and 4 SM slices, so the ceiling is 4 instances: `1g.6gb` (x4), `2g.12gb` (x2), `4g.24gb` (x1), plus `+me` variants. Newer additions in the same guide: H200-141GB (`1g.18gb` … `7g.141gb`), B200-180GB (`1g.23gb` … `7g.180gb`, with NVDEC on every 1g slice), and the RTX PRO 6000 Blackwell 96GB, whose `+gfx` profiles are the first MIG instances allowed to run graphics APIs.

Driver floors from the guide: A100/A30 need R525+ (CUDA 11), H100/H200 need R450.80.02+ (CUDA 12), B200 needs R570+, RTX PRO Blackwell needs R575+. Minimums for the surrounding stack: Container Toolkit v2.5.0, k8s-device-plugin v0.7.0, gpu-feature-discovery v0.2.0.

## GI/CI hierarchy and device naming

By default a MIG device is exactly one GI with one CI occupying all of its SM slices — that is what `nvidia-smi -L` prints and what `CUDA_VISIBLE_DEVICES` consumes. The CI layer exists for a second axis of concurrency: carve one `3g.20gb` GI into three `1c.3g.20gb` CIs and each CI gets 14 dedicated SMs while sharing the GI's 20 GB, 3 copy engines, and 2 NVDECs.

```text
GPU 0 (A100-40GB, MIG mode)
|
+-- GI 1: profile 3g.20gb -- 4 mem slices (20 GB) + 3 SM slices + 3 CE + 2 NVDEC
|     |
|     +-- CI 0 (1c.3g.20gb): 14 SMs   -- these three CIs SHARE the 20 GB,
|     +-- CI 1 (1c.3g.20gb): 14 SMs     engines, and L2; SMs are exclusive,
|     +-- CI 2 (1c.3g.20gb): 14 SMs     and one MPS server may run per CI
|
+-- GI 2: profile 1g.10gb -- 2 mem slices (10 GB) + 1 SM slice, single CI
```

Naming follows `Nc.Ng.Mgb` for subdivided devices (`1c.3g.20gb`), collapsing to plain `3g.20gb` when the single CI owns the whole GI. Enumeration details that bite in practice:

- Since R470, every MIG device has a stable `MIG-<UUID>` (from `nvidia-smi -L`); `CUDA_VISIBLE_DEVICES=MIG-<uuid>` pins a process to it. R450/R460 instead used the `MIG-<GPU-UUID>/<gi>/<ci>` path form.
- Drivers >= R570 let one CUDA process enumerate across multiple GIs — but at most **one CI per GI**, at most **64 MIG instances** system-wide, and they coexist with non-MIG GPUs. Pre-R570 a process saw a single MIG device, period.
- Access is mediated by `nvidia-capabilities` device nodes (`mig/config` to create/destroy instances, per-GI/CI `access` nodes to run work), controlled via cgroups — this is what the container runtime injects.

## Isolation guarantees — and the fine print

**Guaranteed per instance:** SM capacity and performance, an L2 slice, memory capacity *and* bandwidth (memory QoS), assigned engines per the profile table, fault isolation (a context crash cannot poison a neighbor), and predictable latency even while other instances thrash their own caches.

**Explicitly not available**, from the [Deployment Considerations](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/deployment-considerations.html) page:

- No peer access across instances: with driver R570 only P2P *between MIG instances on the same GPU* exists — no MIG-to-MIG P2P across GPUs, and none to non-MIG GPUs. CUDA IPC across GIs is unsupported (across CIs it works). This is why distributed training over MIG slices is a non-starter — see [NVLink & NVSwitch](../../hpc/nvlink-nvswitch.md) for the fabric consequences.
- NCCL is not supported with MIG; profiling of shared GPU resources is unsupported, and on Ampere even `nvidia-smi` shows `N/A` utilization — use DCGM for per-instance metrics.
- No graphics APIs (OpenGL/Vulkan) — the RTX PRO 6000 Blackwell `+gfx` profiles are the sole exception.
- GPUDirect RDMA from a GI is supported; cuda-gdb and compute-sanitizer work normally.

**Lifecycle:** on Ampere, flipping `nvidia-smi -i 0 -mig 1` requires a GPU reset (monitoring daemons like DCGM must be stopped first) and the mode bit persists in InfoROM; on Hopper+ no reset is needed but MIG mode does *not* survive a reboot. The created GI/CI geometry is never persistent — tooling like NVIDIA's [mig-parted](https://github.com/NVIDIA/mig-parted) re-applies it at boot via systemd.

## MIG vs MPS vs vGPU vs time-slicing

The guide's concurrency-mechanism comparison, extended with the two sharing options operators actually reach for:

| Property | Streams | MPS | MIG | vGPU (MIG-backed) | k8s time-slicing |
|----------|---------|-----|-----|-------------------|------------------|
| Partition type | logical, 1 process | logical | physical | physical (per GI) | none (time share) |
| Max partitions | unlimited | 48 clients | 7 GIs | 1 VM per MIG dev | replicas (config) |
| SM performance isolation | none | by %, hardware shared | yes | yes (per vGPU) | none |
| Memory bandwidth QoS | no | no | yes | yes | no |
| Error isolation | no | no | yes | yes | no |
| Cross-partition interop | always | IPC | limited IPC | vGPU policy | full (shared GPU) |
| Reconfigure | dynamic | per process launch | when idle | by admin | per pod |

MPS and MIG compose: run one MPS server per MIG instance (the guide walks through `CUDA_MPS_PIPE_DIRECTORY` per-instance setup), and note the 48-client cap shrinks proportionally with CI size. Time-slicing, by contrast, gives every client of an oversubscribed resource an *equal CUDA time slice* with no isolation guarantees. The [MIG-backed vGPU](https://docs.nvidia.com/ai-enterprise/latest/user-guide/index.html#configuring-a-gpu-for-mig-backed-vgpus) path puts a hypervisor on top so each partition becomes a VM's vGPU — the standard shape for CSPs selling fractional GPUs.

## Kubernetes and scheduler implications

The [k8s-device-plugin](https://github.com/NVIDIA/k8s-device-plugin) exposes MIG through `MIG_STRATEGY`:

- `none` (default) — a MIG-enabled GPU advertises nothing; `single` — every GPU on the node must have an identical geometry, and each instance advertises as plain `nvidia.com/gpu` with node labels distinguishing the profile; `mixed` — full GPUs and MIG devices coexist, instances advertised as `nvidia.com/mig-1g.5gb`-style resources (the README's A100-40GB list: `mig-1g.5gb`, `mig-2g.10gb`, `mig-3g.20gb`, `mig-7g.40gb`).
- The plugin's own MPS *sharing* feature is not supported on MIG-enabled devices, and time-slicing is supported for both `nvidia.com/gpu` and the mixed-strategy MIG resources — equal time slices, no QoS.
- Scheduling consequences: each `mig-Ng.Mgb` type is an independent resource, so the kube-scheduler bin-packs per type while the per-GPU geometry (chosen by an admin or mig-parted, not the scheduler) fixes the feasible combinations. Cluster-level schedulers layer on top — see [GPU cluster scheduling](../../llm/advanced/distributed/gpu-cluster-scheduling.md) — and [inference systems](../../llm/advanced/inference-systems.md) lean on 1g slices to pack small models.
- Dynamic Resource Allocation reached stable in Kubernetes v1.35 and gives vendors an expressive ResourceClaim/DeviceClass model; NVIDIA ships a `k8s-dra-driver-gpu` that can allocate MIG-shaped devices at pod admission time instead of pre-carved static geometry.
- HPC lands the same way: Slurm has managed MIG devices as GRES since 21.08.

## Demo: exact profile-pack search over the driver's placements

The solver below hardcodes the two tables above (A100 and H100) plus the exact `-lgipp` placement sets from the guide's A100 capture, then does an exhaustive, deterministic search: given a workload spec, which non-overlapping GI layouts fit? It reproduces the driver's documented 4-2-1 and 3-2-1-1 geometries and shows the slice arithmetic that kills `7x1g.5gb + 3g.20gb`.

```python
# MIG profile-pack solver for A100-40GB and H100-80GB (exact, deterministic).
# Profile data transcribed from the NVIDIA MIG User Guide:
#   - "Supported MIG Profiles" (GPU Instance Profiles on A100 / on H100 tables)
#   - "Getting Started with MIG" nvidia-smi mig -lgip / -lgipp captures
# Layout model: 8 memory slices x 7 SM slices. Profile <n>g.<m>gb claims n SM
# slices and m GB of memory spanning contiguous memory-slice slots; legal
# start slots are the driver's own -lgipp placement sets (A100-SXM4-40GB).
A100 = {"1g.5gb": (1, 5, 7), "1g.10gb": (1, 10, 4), "2g.10gb": (2, 10, 3),
        "3g.20gb": (3, 20, 2), "4g.20gb": (4, 20, 1), "7g.40gb": (7, 40, 1)}
H100 = {"1g.10gb": (1, 10, 7), "1g.20gb": (1, 20, 4), "2g.20gb": (2, 20, 3),
        "3g.40gb": (3, 40, 2), "4g.40gb": (4, 40, 1), "7g.80gb": (7, 80, 1)}
# -lgipp placements: profile -> (allowed start slots, size in memory slices)
PLACE = {"1g.5gb": ({0, 1, 2, 3, 4, 5, 6}, 1), "1g.10gb": ({0, 2, 4, 6}, 2),
         "2g.10gb": ({0, 2, 4}, 2), "3g.20gb": ({0, 4}, 4),
         "4g.20gb": ({0}, 4), "7g.40gb": ({0}, 8)}
SLOTS = 8
def search(workload):
    """All valid non-overlapping layouts; profiles processed in fixed order."""
    counts = {}
    for p in workload:
        counts[p] = counts.get(p, 0) + 1
    items = sorted(counts.items())
    out = []
    def rec(i, used, chosen):
        if i == len(items):
            out.append(tuple(sorted(chosen)))
            return
        prof, need = items[i]
        starts, size = PLACE[prof]
        cand = sorted(starts)
        def pick(k, pos, us, ch):
            if k == need:
                rec(i + 1, us, ch)
                return
            for j in range(pos, len(cand)):
                s = cand[j]
                span = frozenset(range(s, s + size))
                if span & us:
                    continue
                pick(k + 1, j + 1, us | span, ch + [(prof, s)])
        pick(0, 0, used, chosen)
    rec(0, frozenset(), [])
    return sorted(set(out))
def sm_used(workload, table):
    return sum(table[p][0] for p in workload)
print("== A100-SXM4-40GB: exact placement search over 8 memory slices ==")
w = ["4g.20gb", "2g.10gb", "1g.5gb"]
doc = tuple(sorted([("4g.20gb", 0), ("2g.10gb", 4), ("1g.5gb", 6)]))
print("W1  4g.20gb + 2g.10gb + 1g.5gb   ->", len(search(w)), "valid layout(s):", search(w))
print("    driver's documented layout is in the set:", doc in search(w),
      "(memory slice 7 stays free = 5GB stranded)")
w = ["3g.20gb", "2g.10gb", "1g.5gb", "1g.5gb"]
print("W2  3g.20gb + 2g.10gb + 2x1g.5gb ->", len(search(w)), "valid layout(s)")
print("    lexicographically first:", search(w)[0])
w = ["1g.10gb"] * 4
print("W3  4x1g.10gb                    ->", len(search(w)), "layout(s):", search(w)[0])
print("    SM rows stranded: %d of 7 (4x1g eats 2+2+2+2 = 8 of 8 memory slices)"
      % (7 - sm_used(w, A100)))
w = ["1g.5gb"] * 7 + ["3g.20gb"]
print("W4  7x1g.5gb + 3g.20gb           -> INFEASIBLE: 7x1 + 4 = %d > %d memory slices,"
      % (7 * 1 + 4, SLOTS))
print("    and 7x1g.5gb is already the profile cap (max 7)")
print("== H100-80GB: capacity check (memory slices of 10GB, 7 SM slices) ==")
w = ["3g.40gb"] * 2
print("W5  2x3g.40gb                    -> fits:", sum(H100[p][1] for p in w) <= 80,
      "| memory %dGB of 80, SM slices %d of 7"
      % (sum(H100[p][1] for p in w), sm_used(w, H100)))
w = ["3g.40gb"] * 3
print("W6  3x3g.40gb                    -> fits:", sum(H100[p][1] for p in w) <= 80,
      "| would need %d > %d memory slices; profile cap is %d"
      % (3 * 40 // 10, SLOTS, H100["3g.40gb"][2]))
```

```text
== A100-SXM4-40GB: exact placement search over 8 memory slices ==
W1  4g.20gb + 2g.10gb + 1g.5gb   -> 1 valid layout(s): [(('1g.5gb', 6), ('2g.10gb', 4), ('4g.20gb', 0))]
    driver's documented layout is in the set: True (memory slice 7 stays free = 5GB stranded)
W2  3g.20gb + 2g.10gb + 2x1g.5gb -> 2 valid layout(s)
    lexicographically first: (('1g.5gb', 0), ('1g.5gb', 1), ('2g.10gb', 2), ('3g.20gb', 4))
W3  4x1g.10gb                    -> 1 layout(s): (('1g.10gb', 0), ('1g.10gb', 2), ('1g.10gb', 4), ('1g.10gb', 6))
    SM rows stranded: 3 of 7 (4x1g eats 2+2+2+2 = 8 of 8 memory slices)
W4  7x1g.5gb + 3g.20gb           -> INFEASIBLE: 7x1 + 4 = 11 > 8 memory slices,
    and 7x1g.5gb is already the profile cap (max 7)
== H100-80GB: capacity check (memory slices of 10GB, 7 SM slices) ==
W5  2x3g.40gb                    -> fits: True | memory 80GB of 80, SM slices 6 of 7
W6  3x3g.40gb                    -> fits: False | would need 12 > 8 memory slices; profile cap is 2
```

Read W2 against the guide: the driver's own 3-2-1-1 example places `1g.5gb` at `0:1` and `1:1`, `2g.10gb` at `2:2`, `3g.20gb` at `4:4` — exactly the lexicographically first layout, and the search proves no third layout exists because `1g.5gb` may never start at slice 7. W3 is the scheduler's trap: four `1g.10gb` pods fill all 8 memory slices while stranding 3 of the 7 SM slices, capacity no later pod can claim.

## Interview questions

1. **Why does MIG offer 7 instances when the memory divides by 8?** SM slices are the scarce axis (7 per GPU); seven 1g.5gb instances strand the 8th memory slice, and the 7-slice cap also bounds every mixed geometry.
2. **A CI shares its GI's memory — what isolation survives?** SM capacity is exclusive; memory capacity/bandwidth, engines, and L2 are shared with sibling CIs, so one CI can exhaust the GI's 20 GB. Fault isolation holds per CI context.
3. **Why is distributed training across MIG slices unsupported?** No P2P between instances on different GPUs and no CUDA IPC across GIs; NCCL rejects MIG devices — collectives need fabric-level peer access (see [NVLink & NVSwitch](../../hpc/nvlink-nvswitch.md)).
4. **MIG or MPS for 40 tenants of a 200 MB model?** Neither alone: MIG caps at 7 physically isolated instances, MPS shares one GPU with up to 48 clients but no error/bandwidth isolation — combine MPS *inside* MIG instances for tenant density with QoS.
5. **What changed at Hopper for MIG ops?** No GPU reset to enable mode, but the mode bit no longer persists across reboots; geometry still needs re-creation (mig-parted) and R570 relaxed CUDA enumeration to multiple GIs per process.

## Related pages

The accelerator landscape around MIG — where it sits against TPU, SR-IOV and AMD MxGPU — is surveyed in [Accelerators & Domain-Specific Architectures](./accelerators.md); CUDA's other concurrency mechanisms (streams, graphs) in [CUDA Graphs](./cuda-graphs.md); the CPU-side analog of shared-cache partitioning in [Intel RDT & resctrl](./rdt-resctrl.md).

## References

1. NVIDIA Multi-Instance GPU User Guide (entry page). https://docs.nvidia.com/datacenter/tesla/mig-user-guide/
2. NVIDIA, "Supported MIG Profiles" (A100/H100/H200/B200/A30 profile tables). https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/supported-mig-profiles.html
3. NVIDIA, "Concepts" (terminology, GI/CI model, CUDA concurrency-mechanism table). https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/concepts.html
4. NVIDIA, "Getting Started with MIG" (driver prerequisites, -lgip/-lgipp/-cgi captures, MPS-on-MIG workflow). https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/getting-started-with-mig.html
5. NVIDIA, "Deployment Considerations" (P2P/IPC/NCCL/graphics limits, reset semantics). https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/deployment-considerations.html
6. NVIDIA, "MIG Device Names" (naming scheme, CUDA enumeration across driver releases, 64-instance limit). https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/mig-device-names.html
7. NVIDIA, "Supported GPUs" (compute capability >= 8.0 requirement, per-product max instances). https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/supported-gpus.html
8. NVIDIA, "CUDA Multi-Process Service" documentation. https://docs.nvidia.com/deploy/mps/index.html
9. NVIDIA, k8s-device-plugin README (MIG_STRATEGY, time-slicing, MPS-sharing limits). https://github.com/NVIDIA/k8s-device-plugin
10. NVIDIA, mig-parted (MIG Partition Editor; boot-time geometry re-creation). https://github.com/NVIDIA/mig-parted
11. SchedMD, "Slurm GRES Guides — MIG Management" (MIG as GRES since 21.08). https://slurm.schedmd.com/gres.html
12. Kubernetes, "Dynamic Resource Allocation" (Stable since v1.35). https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/
