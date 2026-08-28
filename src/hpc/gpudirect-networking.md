# GPUDirect Networking: The Economics of Not Touching Host Memory

Every GPU collective, checkpoint write, and dataloader batch pays rent to the PCIe bus. The question that separates a tuned GPU cluster from an expensive one is: how many times does each byte cross that bus, and which CPUs get woken up along the way? GPUDirect is NVIDIA's family of answers -- RDMA, peer-to-peer, and Storage -- all built on one economic principle: a byte that never enters host DRAM costs one PCIe crossing instead of two, skips two driver transitions, and never steals a CPU cycle from the kernel that is trying to run. This page works through the whole family as a cost-accounting exercise, then shows what NCCL, SHARP, and GDRCopy each do with the savings.

## 1. The Staging Tax: Count Crossings Before You Count Nanoseconds

The default path for moving GPU data to the network stages it through host memory. Even with pinned (page-locked) bounce buffers, which remove one copy, the byte still crosses PCIe twice per direction and passes ownership between the CUDA driver and the NIC driver each time:

```text
STAGED (bounce buffer through host DRAM):              GPUDIRECT RDMA (direct):

GPU VRAM                                                GPU VRAM
  | (1) PCIe DMA out                                      | (1) PCIe: NIC DMA in place
  v                                                       |
host DRAM  <-- CPU/driver transition                      |
  | (2) PCIe: NIC DMA out                                 |
  v                                                       v
NIC ==> wire                                            NIC ==> wire

Per direction: 2 PCIe crossings, 2 driver handoffs      1 PCIe crossing, 0 CPU touches
```

Four crossings per send+receive round trip versus two; and each driver handoff contributes a fixed software latency that no amount of bandwidth buys back. On a Gen4 x16 host (about 31.5 GB/s usable per direction) moving 1 GB through the staging path consumes 2 GB of host PCIe bandwidth that the host's own jobs, page mappings, and other devices needed. The table below is the whole argument of this page in one place: PCIe bytes charged per byte delivered, per path.

| Path | PCIe bytes per byte moved | CPU woken? | Where the fixed cost lands |
|---|---|---|---|
| cudaMemcpy staging (D2H + H2D) | 2 | Yes, per chunk | Driver transitions + copy engines |
| GPUDirect RDMA (NIC <-> VRAM) | 1 | No | One-time buffer registration |
| PCIe P2P (GPU <-> GPU, same host) | 1 | No | Peer-enable + mapping setup |
| NVLink peer access (same host) | 0 | No | NVLink fabric, not PCIe |
| GPUDirect Storage (NVMe -> VRAM) | 1 | No | One-time descriptor setup |
| Storage without GDS (NVMe -> host -> GPU) | 2 | Yes | Page cache + memcpy |

## 2. GPUDirect RDMA: Letting the NIC DMA into VRAM

GPUDirect RDMA (docs.nvidia.com/cuda/gpudirect-rdma/) gives a third-party PCIe device -- usually an InfiniBand or RoCE NIC -- read/write access to GPU memory without host DRAM in the middle. The moving parts, in the order a packet actually meets them:

1. **Pinned, registered buffers.** The application allocates with `cudaMalloc`, and the MPI/UCX/NCCL layer registers the region with the NIC (`ibv_reg_mr`). Registration pins the pages and produces the (key, address) pair the NIC later references in its work requests.
2. **The peermem bridge.** A kernel module teaches the RDMA driver about GPU memory. Historically `nv_peer_mem`, replaced by `nvidia-peermem` in CUDA 11.4 -- NVIDIA's docs describe it as providing "Mellanox InfiniBand-based HCAs direct peer-to-peer read and write access to the NVIDIA GPU's video memory." Load it (`modprobe nvidia_peermem`) or registration silently falls back to staging.
3. **Address translation, done once.** GPUDirect RDMA "relies upon all physical addresses being the same from the different PCI devices' point of view": the NIC's DMA engine issues bus addresses that must land in VRAM directly, which is why every buffer's GPU physical address is programmed into the NIC's memory tables at registration time, not per packet.
4. **NIC -> GPU TLPs on PCIe.** A 200 Gb/s NIC sustainably writes an incoming stream straight into VRAM; the GPU's copy engines and SMs never notice.

```text
Address spaces in play:

CPU virtual -> CPU physical (host DRAM)      ordinary page tables
CUDA virtual -> GPU physical (VRAM)          CUDA UVA mapping
NIC address -> GPU physical                  ibv_reg_mr + peermem tables
                  ^
                  | must agree with what PCIe devices see: one flat,
                  | physical address space shared by GPU + NIC + NVMe
```

## 3. When the Direct Path Silently Breaks: IOMMU, ACS, BAR1

The single-physical-address-space assumption is also the failure surface. Three things violate it in the field, and all three fail as "2x slowdown you did not ask for," not as errors:

- **IOMMU translation (VT-d / AMD-Vi).** The NVIDIA docs are explicit: GPUDirect RDMA is "incompatible with IOMMUs performing any form of translation other than 1:1, hence they must be disabled or configured for pass-through translation." An IOMMU remaps the GPU's physical addresses per device, so the address the NIC DMA'd to no longer means VRAM. Platforms often ship with VT-d on by default.
- **ACS (Access Control Services) on PCIe ports.** ACS P2P Redirect and Egress Control exist so that hypervisors can force peer traffic through the root complex for isolation. When enabled on the switches or root ports between GPU and NIC (common on some BIOS defaults and in cloud virtualization), every peer TLP is re-routed upstream: the "direct" path becomes GPU -> root complex -> NIC, with root-complex latency and IOMMU translation attached. Detection is `lspci -vvv | grep -A2 'Access Control'` on every hop between the two endpoints -- enabling ACS on any bridge on the path is enough.
- **BAR1 too small to matter for CPU access.** The GPU's BAR1 aperture (256 MB by default on many datacenter GPUs, with 32 MB reserved; 16 GB+ on large-BAR parts) is the window through which *CPU* accesses reach VRAM. BAR1 size does not limit GPUDirect RDMA itself -- the NIC accesses VRAM through the full device, not the aperture -- but it caps everything in sections 4 and 5 that does go through the aperture, and old BIOSes can hang booting 32-bit-unaware large-BAR parts.

The recurring operational lesson: benchmark the staged and direct paths side by side (`NCCL_DEBUG=INFO` prints the chosen transport) and treat any silent fallback as a platform-configuration bug to bisect, not a number to tune around.

## 4. GDRCopy: BAR1 as a CPU Door

Not every transfer deserves a NIC work request. GDRCopy (github.com/NVIDIA/gdrcopy) is "a fast GPU memory copy library based on NVIDIA GPUDirect RDMA technology": its `gdrdrv` kernel module maps a slice of GPU BAR1 into a process's address space, after which the CPU writes GPU memory with ordinary stores -- no `cudaMemcpy`, no kernel launch, no copy engine. It trades bandwidth (the BAR1 aperture is narrow) for latency (roughly microsecond-scale, versus the multi-microsecond cudaMemcpy path), which is exactly the right trade for the small, control-shaped writes that dominate request latency: flag words, parameter updates, sequence numbers, descriptors. UCX and MPI stacks use it for small-message CPU->GPU injection; `gdrcopy_copylat` and `gdrcopy_pplat` in the repo measure the latency/bandwidth frontier per buffer size so you can pick the crossover empirically.

## 5. Inside the Node: PCIe P2P versus NVLink Peer Access

Peer access between GPUs has two physical realizations, and the economics differ. Over PCIe, `cudaDeviceEnablePeerAccess` sets up direct GPU-to-GPU DMA -- one crossing per byte, subject to the same ACS/IOMMU hazards as section 3. Over NVLink, GPUs have dedicated wires that bypass PCIe entirely: an A100 carries 600 GB/s of aggregate NVLink bandwidth, an H100 900 GB/s, both orders above a x16 slot. CUDA IPC (`cudaIpcMemHandle_t`) is the API layer that lets one process's allocation be mapped into another's address space, layered on whichever fabric exists. NCCL's topology detection walks exactly this decision tree -- NVLink first, then PCIe P2P, then shared-host staging -- per pair of GPUs, which is why its intra-node bandwidth is rarely a single number.

| Dimension | PCIe P2P | NVLink peer |
|---|---|---|
| Bandwidth ceiling (per direction, x16) | ~31.5 GB/s (Gen4), ~63 (Gen5) | 300 GB/s/GPU (A100) to 450+ (H100) |
| CPU involvement after setup | None | None |
| Subject to IOMMU/ACS upstream routing | Yes | No (not a PCIe peer) |
| Topology sensitivity | Root-complex hops matter | Switch-based (NVSwitch) is near-uniform |
| Failure mode | Silent ACS fallback to host path | Falls back to PCIe P2P if not connected |

## 6. GPUDirect Storage: The Same Trick for the Dataloader

GPUDirect Storage (docs.nvidia.com/cuda/gpudirect-storage/) applies the section-2 argument to NVMe: with the `cufile` API, storage devices DMA directly into (and out of) VRAM descriptors, skipping the page cache and the host-side memcpy. For a training job reading checkpoints or datasets at tens of GB/s, the staged path costs two PCIe crossings per byte plus CPU copies; GDS costs one and keeps the CPU out of the per-chunk path entirely. The registration story rhymes with RDMA: buffers must be registered with `cuFileBufRegister` so the storage DMA engines get stable, direct bus addresses -- the same address-agreement principle as `ibv_reg_mr`. The win grows with message size (large sequential reads) and shrinks on small random reads, where descriptor overhead dominates -- the same economics as section 9, one fabric over.

## 7. SHARP: Paying the Switch to Do Your Math

SHARP -- the Scalable Hierarchical Aggregation Protocol (Graham et al., COMHPC 2016) -- moves the last staged computation into the network itself: switch ASICs host "aggregation groups" that combine arriving packets in flight. For an allreduce, each rank sends its contribution once up the fabric; switches reduce on arrival; the result fans back down. The data shrinks as it ascends, so upper fabric links carry reduced partial sums, and the sequential hop-count of a ring (2(n-1) software-paced steps) collapses to one up-pass plus one down-pass paced by switch hardware.

```text
RING: reduction on GPUs, 2*(n-1) steps        SHARP: reduction in switch ASICs

G0 -> G1 -> G2 -> ... -> G7 -> G0             G0..G7 --(K up)--> [AG: add in flight]
  ^    each step: recv, reduce, send                              |
  +-- software handoff each hop              partials shrink going up; top
                                             switch emits the final sum
                                             [AG] --(K down)--> every rank
```

NCCL's environment docs list the resulting algorithms: `Collnet`/`CollnetChain`/`CollnetDirect` (SHARP over InfiniBand, since NCCL 2.14), and `NVLS`/`NVLSTree` (since 2.17/2.18), which "enable NVLink SHARP offload" -- the third-generation NVSwitch ASICs run the same in-fabric aggregation over NVLink, with no IB fabric required. The cost side: aggregation-group capacity is bounded (switch memory for the reduction state), so very large node counts form multiple groups and some hierarchy returns; and for bandwidth-bound sizes a ring's 2(n-1)/n wire-bytes can still beat SHARP's 2n/n on fabrics where the network, not PCIe, is the scarce resource. Which is why the next section's benchmark has a "fastest" column rather than a winner.

## 8. What NCCL Builds on Top of All of This

NCCL (github.com/NVIDIA/nccl) is the consumer that turns these primitives into training throughput, and its design is an economics engine:

- **Channels = CTAs.** NCCL launches one streaming-multiprocessor workhorse per *channel*; `NCCL_MIN_CTAS`/`NCCL_MAX_CTAS` bound the count, and each rank sharing a GPU allocates its own channels. Channels buy concurrency: multiple chunks in flight overlap one GPU's PCIe ingress with another's egress, hiding the per-step handoff latency that section 9 charges serially.
- **A menu of data paths, chosen per size and topology.** Ring, Tree, Collnet (SHARP), NVLS, PAT -- selected by heuristics over the discovered topology (NVLink first, then PCIe P2P, then network), overridable via `NCCL_ALGO`.
- **Topology discovery runs at init**, walking PCIe/NVLink/IB trees so the ring's neighbor order follows copper, not rank numbers.

The ring/tree mechanics and bandwidth-optimality math live on the [Ring AllReduce](../llm/advanced/distributed/ring-allreduce.md) page and the allreduce-pattern survey in [Collective Communication](./collective-communication.md); CUDA-aware MPI's use of GPUDirect is sketched in [MPI Parallelism](./mpi-parallelism.md) -- here we hold the focus on the data path itself.

## 9. Worked Numbers: Ring Allreduce Under Three Data Paths

A transparent, deliberately serial model (upper bound; no cross-chunk pipelining): 8 single-GPU nodes, PCIe Gen4 x16 at 31.5 GB/s, InfiniBand HDR at 25 GB/s, 6 us software handoff per ring step, 2 us switch reduction. "Staged" pays 4 PCIe crossings per chunk (NIC->DRAM->GPU in, GPU->DRAM->NIC out); GPUDirect pays 2; SHARP pays 2 but sends only one up-pass and one down-pass over the network instead of 2(n-1) ring steps.

```python
# Ring allreduce of S bytes over n=8 single-GPU nodes, three data paths.
# Serial per-step accounting (upper bound: no cross-chunk pipelining).
# One software handoff (t_sw) per ring step; SHARP offloads the reduce into
# the switch ASIC (t_red) and needs only one up + one down network pass.
N_GPUS   = 8                  # one rank per node
PCIE_GB  = 31.5               # PCIe Gen4 x16, one direction, GB/s
NET_GB   = 25.0               # InfiniBand HDR (200 Gb/s) line rate, GB/s
T_SW     = 6e-6               # proxy-thread / driver handoff, seconds
T_RED    = 2e-6               # switch-ASIC reduction per chunk, seconds
SIZES_MB = [1, 8, 64, 256, 1024]

def step(mb, pcie_crossings):
    """One ring chunk step: network TX + PCIe crossings + one handoff."""
    c    = mb / 1000.0                 # chunk size, GB
    net  = c / NET_GB                  # NIC -> wire (opposite direction overlaps)
    pcie = pcie_crossings * c / PCIE_GB
    return net + pcie + T_SW

def times(smb):
    n      = N_GPUS
    chunk  = smb / n                   # ring: S/n per step
    staged = 2 * (n - 1) * step(chunk, 4)   # NIC->DRAM->GPU in, GPU->DRAM->NIC out
    direct = 2 * (n - 1) * step(chunk, 2)   # GPUDirect RDMA: one crossing each way
    sharp  = (2 * (smb / 1000.0 / NET_GB)    # K up + reduced K down
             + 2 * (smb / 1000.0 / PCIE_GB)  # NIC DMA into VRAM, both ways
             + 2 * T_RED + T_SW)
    return staged, direct, sharp

print(f"{'S (MB)':>7} | {'staged ms':>10} | {'gdr ms':>9} | {'sharp ms':>9} | fastest")
print("-" * 55)
for smb in SIZES_MB:
    st, dr, sh = times(smb)
    best = min((st, "staged"), (dr, "gdr"), (sh, "sharp"))[1]
    print(f"{smb:>7} | {st*1e3:>10.3f} | {dr*1e3:>9.3f} | {sh*1e3:>9.3f} | {best}")

busbw = 2 * (N_GPUS - 1) / N_GPUS      # ring bytes-on-wire factor
st, dr, sh = times(1024)
print()
print(f"Ring-equivalent busbw at 1024 MB: staged {busbw*1.0/st:.1f} GB/s, "
      f"GDR {busbw*1.0/dr:.1f} GB/s, SHARP {busbw*1.0/sh:.1f} GB/s")
print(f"PCIe bytes moved per byte all-reduced: staged 4, GPUDirect 2, SHARP 2")
print(f"Network bytes per byte all-reduced:   staged {2*(N_GPUS-1)/N_GPUS:.2f}, "
      f"GPUDirect {2*(N_GPUS-1)/N_GPUS:.2f}, SHARP 2.00")
```

Real output of the script above:

```text
 S (MB) |  staged ms |    gdr ms |  sharp ms | fastest
-------------------------------------------------------
      1 |      0.376 |     0.265 |     0.153 | sharp
      8 |      2.422 |     1.533 |     1.158 | sharp
     64 |     18.786 |    11.675 |     9.193 | sharp
    256 |     74.893 |    46.448 |    36.744 | sharp
   1024 |    299.320 |   185.542 |   146.946 | sharp

Ring-equivalent busbw at 1024 MB: staged 5.8 GB/s, GDR 9.4 GB/s, SHARP 11.9 GB/s
PCIe bytes moved per byte all-reduced: staged 4, GPUDirect 2, SHARP 2
Network bytes per byte all-reduced:   staged 1.75, GPUDirect 1.75, SHARP 2.00
```

Read the table as a sensitivity analysis, not a scoreboard. With Gen4 PCIe and HDR the *crossing count* dominates: staged pays double PCIe per byte and loses 1.6x to GPUDirect at every size; SHARP keeps GPUDirect's PCIe cost but deletes 12 of 14 sequential handoffs, so it wins everywhere in this regime. The balance flips when the fabric, not PCIe, is the constraint: on multi-rail NDR (50 GB/s per rail) or under an oversubscribed aggregation group, the ring's 1.75 wire-bytes-per-byte versus SHARP's 2.00 reclaims the lead at large sizes -- which is precisely why NCCL ships all of ring, tree, Collnet, and NVLS and picks per message size rather than compiling in a winner. At 1 MB the staged model spends a quarter of its time in pure software handoff: that fixed cost is what NVLS exists to delete on NVSwitch boxes.

## 10. Failure-Mode Field Guide

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| NCCL logs "via CPU" / P2P disabled | peermem module not loaded | `lsmod`, look for peermem | `modprobe nvidia_peermem`; verify driver versions match |
| GPUDirect works, throughput halves | ACS enabled on a bridge between GPU and NIC | `lspci -vvv` on each hop | Disable ACS (or re-seat cards on the same switch/complex) |
| Works bare-metal, fails in VM | IOMMU translating (non-1:1), no VFIO passthrough | `dmesg`, check DMAR/IOMMU lines | Pass-through mode or disable VT-d |
| `cudaMemcpy` fine, `gdr_map` fails | BAR1 exhausted by mappings or tiny BAR | `nvidia-smi -q`, BAR1 Memory section | Free mappings; enable large-BAR firmware |
| `ibv_reg_mr` on device memory EINVAL | Buffer not allocated via CUDA, or driver mismatch | CUDA runtime version vs nvidia.ko | Reallocate with `cudaMalloc`; align driver stack |
| Registration succeeds but slow first iter | Fallback path during warmup, then cache hit | `NCCL_DEBUG=INFO` transport lines | Ensure persistent buffers; avoid per-step `cudaFree` |

## 11. Interview Angles

- **"Why is my 8-GPU allreduce slower than 8x single-GPU training?"** Start from the crossing table: staged paths double-charge PCIe, and if ACS or IOMMU is on, the "direct" path degrades to root-complex routed with zero errors raised. Walk the section-10 checklist out loud.
- **"NCCL chose Tree over Ring -- why?"** Ring is bandwidth-optimal (2(n-1)/n wire bytes) but latency-serial (2(n-1) steps); small messages pay the alpha term, so trees and NVLS/SHARP offload win there. Tie to the section-9 table.
- **"Design dataloading for a 64-GPU training job."** GDS for large sequential batches, registration like RDMA, host page cache demoted from critical path; quantify with the section-1 table.

## 12. Cross-References and Sources

Related pages: [MPI Parallelism](./mpi-parallelism.md) (CUDA-aware MPI and the GPUDirect summary table), [Collective Communication](./collective-communication.md) (allreduce patterns and parallelism strategies), [Ring AllReduce](../llm/advanced/distributed/ring-allreduce.md) (ring math, NCCL survey, DDP usage), [GPU for HPC](../arch/parallelism/gpu-hpc.md) (CUDA-aware MPI in context), [InfiniBand](../linux/storage/infiniband.md) (RDMA verbs underneath this page). There is no standalone NCCL page in this repo; the primary sources below are the authoritative entry points.

References:

1. NVIDIA, "GPUDirect RDMA" -- CUDA Toolkit Documentation. https://docs.nvidia.com/cuda/gpudirect-rdma/ (IOMMU 1:1 requirement, BAR sizes, nvidia-peermem).
2. NVIDIA, "GPUDirect Storage" -- CUDA Toolkit Documentation. https://docs.nvidia.com/cuda/gpudirect-storage/index.html
3. R. L. Graham et al., "Scalable Hierarchical Aggregation Protocol (SHArP): A Hardware Architecture for Efficient Data Reduction," COMHPC @ SC16, Nov 2016. DOI: 10.1109/COMHPC.2016.006
4. NVIDIA Collective Communications Library (NCCL). https://github.com/NVIDIA/nccl -- and NCCL User Guide, environment variables (`NCCL_ALGO`, `NCCL_MIN_CTAS`, NVLS): https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html
5. NVIDIA GDRCopy. https://github.com/NVIDIA/gdrcopy
