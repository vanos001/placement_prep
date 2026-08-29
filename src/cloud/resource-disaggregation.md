# Resource Disaggregation: Decoupling Compute, Memory, and Storage in the Datacenter

Every server is a compromise: you buy DRAM slots, SSD bays, and PCIe lanes in fixed
ratios no single workload wants, then run the box at a fraction of each spec. Resource
disaggregation is the proposal to stop compromising -- pull memory, storage, and
accelerators out of the chassis, put them behind a network, and allocate on demand.
Storage disaggregation already won (nobody asks which host owns the S3 bucket); memory
is the unfinished war, and CXL is the third attempt to fight it with hardware.

This page is the **datacenter architecture view**: pooling ratios, fault domains,
network taxes, migration, semantics. Protocol internals (CXL.io/cache/mem, device
types) live in [CXL Memory Pooling](../arch/advanced/cxl-memory-pooling.md); the RDMA
lossless-network traps this page leans on are in
[RDMA Congestion Control](../networks/advanced/rdma-congestion-control.md); the
storage-fabric side in
[Tiered Storage and Disaggregated Architectures](../storage/advanced/tiered-persistent.md);
data-path offload economics in
[DPUs and SmartNICs](../arch/advanced/dpu-smartnic-offload.md).

## Three taxes a server pays for being a box

**Stranding.** Operators provision each host's DRAM for that host's peak, and peaks
arrive at different times. Fleet memory utilization plateaus well below capacity --
the Azure measurements in Pond (ASPLOS 2023) land in the 40-60 percent band -- and
the stranded remainder is unpurchasable elasticity: it exists, but the scheduler
cannot move it where it is needed. CPU and storage escape via live migration and
network storage; memory does not, because moving a page costs a page fault and moving
a VM costs a migration window. **Fixed ratios** are the sibling tax: a workload
wanting 2 CPUs + 64 GiB and one wanting 32 CPUs + 8 GiB force two SKUs;
disaggregation collapses the SKU matrix so the memory/accelerator ratio becomes a
placement decision, not a purchase. **Upgrade coupling** is the third: DRAM, SSD, and
CPU generations retire together, forcing fleet-wide forklifts; a pool behind a switch
refreshes once, decoupled from compute cycles.

The arithmetic is risk-pooling: N hosts each carrying headroom `h` against their own
spikes hold `N * (mean + h)`; a shared pool needs only `mean*N + h_pool`, where
`h_pool` grows with the *aggregate* spike -- roughly `z * sigma / sqrt(N)` for
independent demands. That `sqrt(N)` is the business case: 64 hosts each holding 30
percent headroom strand ~19 hosts' worth of memory; a pooled fleet holds ~1/8 of one.

## What can actually travel over a wire

| Resource grain     | Transfer size    | Latency budget     | Network required        | Status in 2026                    |
|--------------------|------------------|--------------------|-------------------------|-----------------------------------|
| Object/blob        | KB - GB          | 10 ms +            | Plain TCP/HTTP          | Won 20 years ago (S3, Haystack)   |
| Block/volume       | 4 - 128 KB       | ~100 us - 1 ms     | NVMe/TCP or NVMe/RDMA   | Won (EBS on Nitro, cloud volumes) |
| Memory, page       | 4 - 64 KB        | ~1 us              | RDMA + software paging  | Research (Infiniswap, LegoOS)     |
| Memory, cache line | 64 B             | ~100 ns (2-4x DDR) | Cache-coherent (CXL)    | Early production (Pond/Azure)     |
| Accelerator state  | GB (weights, KV) | ms +               | Ethernet + RDMA         | Shipping for LLM inference        |

The pattern: **disaggregation succeeds exactly where the network's finest delivered
grain matches the resource's natural access grain.** Objects are megabyte-grained, so
TCP is invisible. Cache lines are 64 bytes, so only a coherent protocol (CXL.mem)
serves them without software in the load path. Pages sit in the awkward middle -- 4 KB
is too fine for Ethernet efficiency and too coarse for coherence -- which is why that
rung stalled for a decade.

## The network tax, and the pre-CXL stall

| Access path                       | Round trip   | Ratio vs local DDR |
|-----------------------------------|--------------|--------------------|
| Local DDR5 load (hit)             | ~100 ns      | 1x                 |
| CXL Type-3, one switch hop        | ~250-400 ns  | ~3-4x              |
| One-sided RDMA read, 4 KB (wire)  | ~1-2 us      | ~10-20x            |
| RDMA page fault incl. kernel path | ~5-15 us     | ~50-150x           |

Lim et al. built the quantitative case twice: the ISCA 2009 blade-server design
([Disaggregated memory for expansion and
sharing](https://doi.org/10.1145/1555754.1555789)) showed the capacity savings, and
the HPCA 2012 follow-up ([System-level implications of disaggregated
memory](https://doi.org/10.1109/HPCA.2012.6168955)) showed the tax -- with
then-current interconnects, remote-memory penalties erased most of the utilization
win. After a decade of attempts (swap-over-RDMA, Infiniswap's batched 4-KB
remote-memory blocks ([NSDI 2017](https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/gu)),
LegoOS's split-kernel monitors
([OSDI 2018](https://www.usenix.org/conference/osdi18/presentation/shan))), consensus
hardened into three claims:

- **Page-grain remote memory over RDMA does not pay.** The kernel page-fault path and
  TLB shootdowns cost more than the wire; 4-KB transfers waste most of a jumbo frame;
  tails land an order of magnitude past local DRAM.
- **Object/block grain works and always did.** Facebook's photo stack is the proof:
  [Haystack](https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Beaver.pdf)
  split metadata from blob bytes in 2010, and
  [f4](https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-muralidhar.pdf)
  pushed warm blobs onto erasure-coded, compute-free storage nodes -- storage
  disaggregated across a datacenter at TCP grain.
- **Memory needs cache-line grain at a 2-4x tax, not 50x.** Only a coherent protocol
  delivers that. Pre-CXL no such fabric existed between socket and rack; hence
  "stalled." CXL reuses the PCIe PHY to put one inside the chassis-to-appliance hop.

## Semantics: pick the lie your network tells

- **Block device (swap/I/O stack):** the kernel pays via the fault path; failure mode
  is swap-storm collapse under memory pressure.
- **Pages (mmap, page faults):** kernel and application pay in TLB shootdowns;
  failure mode is latency cliffs at working-set edges.
- **Cache lines (CXL load/store):** hardware pays (home agent, snoop filter); failure
  mode is interleave hot-spots on the switch. The only choice where existing binaries
  run unmodified -- which is why CXL matters.
- **Objects (app-level RPC):** the application pays in a rewrite; chatty protocols,
  but at MB grain the network tax is invisible -- the entire history of cloud storage.
- **Filesystem (NVMe-oF namespace):** the storage stack pays; failure mode is
  queue-depth misallocation.

The block/page rows are why the pre-CXL literature is full of "works for batch, not
for latency-critical paths" verdicts, and the object row is what operators actually
deployed at scale.

## Rack geometry: pools, ratios, fault domains, tails

```text
    integrated (today)                    pooled (CXL, rack scale)

  +-----------+ +-----------+          hosts (8-16)          pool appliance
  | CPU 64G   | | CPU 64G   |        +-----------+         +---------------+
  | 2x NVMe   | | 2x NVMe   |        | CPU + 32G |  x N    | switch (MLD)  |
  +-----------+ +-----------+        +-----+-----+         +-------+-------+
  memory: per-host peak                 CXL x8 |                   | 4 TiB DRAM
  storage: network (already)   ................+...................+
                                         | RDMA/Eth to NVMe-oF / S3 |
```

- **Pooling ratio.** Hosts per appliance: bounded by switch ports (CXL switches ship
  16-32 upstream ports) and by bandwidth -- an x8 PCIe 5.0 link is ~63 GB/s shared
  between a host's local and pooled traffic. Past ~8:1 the uplink, not capacity, is
  the constraint. Vendor "32:1 pooling" claims are port-count math, not traffic math.
- **Fault domain.** An integrated host failure strands one host's memory: bad for one
  tenant. A pool appliance failure evicts every attached host's remote region at
  once -- blast radius scales with the ratio. Hence modest ratios, MLD partitioning
  (each host gets an exclusive logical slice), and dual-homing across two pools.
- **Migration.** Live migration already treats memory as network data; with a pool,
  the scheduler also sees it as a NUMA-like node with a cost. Deployments pin hot
  working sets to local DRAM and let cold regions land in the pool -- tiering by
  temperature. Evacuating a failing appliance is a bulk copy, not a VM migration.
- **Consistency domain.** CXL gives coherence within the appliance hop; across
  appliances you are back to RDMA rules. Pools scale within a switch; federations
  get no coherence for free.
- **Hot-spotting and the tail.** Pooling fixes *capacity* variance and creates
  *bandwidth* variance: one hot 1-GiB region funnels onto one appliance port, and
  static interleave fixes bandwidth at the price of locality -- the NUMA trade, one
  hop out. Burst absorption is incast-shaped (see the pause-storm dynamics in
  [RDMA Congestion Control](../networks/advanced/rdma-congestion-control.md)), and a
  straddling working set sees bimodal p99s, so deployments keep a local overflow
  guard -- the "unplaced" column in the simulator below.

## CXL 3.x fabric claims versus shipping reality

CXL 2.0 (2020) added switches and multi-logical-device (MLD) addressing -- the piece
that makes *pooling* real, each attached host owning an exclusive carve of appliance
DRAM. CXL 3.0 (2022) and 3.1 (2023) added multi-level switching, memory *sharing*
(multiple hosts on the same bytes with hardware back-invalidate coherence), and
dynamic capacity
([CXL Consortium specifications](https://computeexpresslink.org/cxl-specification/)).
Separate what is specified from what is deployed:

- **Shipping:** Type-3 expanders; switch-based MLD pooling; host software treating
  the pool as hot-pluggable NUMA-like memory. Pond (ASPLOS 2023) describes Azure
  evaluating exactly this shape at fleet scale.
- **Specified, silicon-scarce:** multi-head devices, coherent sharing, multi-level
  fabrics. When a vendor deck presents these as available, ask which SKU, which
  switch, which kernel -- sharing needs host-side support most fleets lack.
- **Overclaimed:** "datacenter-wide memory fabric." Coherence does not traverse the
  Ethernet backbone; the CXL domain ends at the rack switch. Anything past it is
  disaggregation the old way -- RDMA and software -- with the old taxes.

## A model you can run (a model, not a measurement)

The simulator sweeps fleet utilization, generates per-host stranded memory in 1-GiB
pages, serves a constant burst increment from the pool, and de-rates pooled capacity
by the hop-tax slowdown:

```python
"""Pooling simulator -- a MODEL, not a measurement.

N=64 hosts x 512 GiB; per-host used ~ triangular around fleet utilization u;
free pages in 1-GiB pages (10% fragmentation loss). The pool absorbs a constant
burst D = 15% of fleet. Hop tax R (CXL 4x, RDMA 60x): slowdown s = 1+f*(R-1),
f = pooled share of touched memory. Pool hardware charged as capacity
equivalent (CXL 2%, RDMA 6% of fleet); unplaced bursts cost 1.5x to cover."""
import random

N, C = 64, 512
FLEET, D = N * C, int(0.15 * N * C)
COST = {"CXL": 0.02, "RDMA": 0.06}
R = {"CXL": 4, "RDMA": 60}


def net(u, name):
    rng = random.Random(1000 + int(u * 100))
    free = sum(int((C - min(1.0, max(0.0, rng.triangular(
        max(0, u - .25), min(1, u + .25), u))) * C) * 0.90) for _ in range(N))
    served = min(free, D)
    f = served / (FLEET * u + served)
    s = 1 + f * (R[name] - 1)
    return served, D - served, f, s, served / s - COST[name] * FLEET - 1.5 * (D - served)


print("fleet = %d hosts x %d GiB = %.1f TiB | burst = %.2f TiB | 1-GiB pages"
      % (N, C, FLEET / 1024, D / 1024))
r50 = {}
for name in ("CXL", "RDMA"):
    print("\n== %s pool (hop/local = %dx, hardware cost %.0f%% of fleet) =="
          % (name, R[name], 100 * COST[name]))
    print("   u    served  unplaced  f_remote  slowdown   net_TiB")
    for u in (0.30, 0.50, 0.70, 0.90):
        sv, un, f, s, v = net(u, name)
        print("  %.2f   %6.2f  %8.2f  %8.3f  %8.2f  %7.2f  %s"
              % (u, sv / 1024, un / 1024, f, s, v / 1024, "POOLS" if v >= 0 else "BUY"))
    be = next((i / 1000 for i in range(300, 990) if net(i / 1000, name)[4] < 0), None)
    print("  break-even utilization (net < 0 above): %s"
          % ("%.2f" % be if be else "none in 0.30-0.99"))
    r50[name] = net(0.50, name)

f = r50["CXL"][2]
print("\nbreak-even hop ratio R* at u=0.50 (f_remote=%.3f):" % f)
for name in ("CXL", "RDMA"):
    sv, un, f, s, v = r50[name]
    print("  %-4s cost %.0f%%: R* = %5.1f  (model uses R=%d)"
          % (name, 100 * COST[name], 1 + (sv / (COST[name] * FLEET) - 1) / f, R[name]))
```

Real output of that program:

```text
fleet = 64 hosts x 512 GiB = 32.0 TiB | burst = 4.80 TiB | 1-GiB pages

== CXL pool (hop/local = 4x, hardware cost 2% of fleet) ==
   u    served  unplaced  f_remote  slowdown   net_TiB
  0.30     4.80      0.00     0.333      2.00     1.76  POOLS
  0.50     4.80      0.00     0.231      1.69     2.20  POOLS
  0.70     4.80      0.00     0.176      1.53     2.50  POOLS
  0.90     4.25      0.55     0.129      1.39     1.61  POOLS
  break-even utilization (net < 0 above): 0.92

== RDMA pool (hop/local = 60x, hardware cost 6% of fleet) ==
   u    served  unplaced  f_remote  slowdown   net_TiB
  0.30     4.80      0.00     0.333     20.67    -1.69  BUY
  0.50     4.80      0.00     0.231     14.61    -1.59  BUY
  0.70     4.80      0.00     0.176     11.41    -1.50  BUY
  0.90     4.25      0.55     0.129      8.59    -2.25  BUY
  break-even utilization (net < 0 above): 0.30

break-even hop ratio R* at u=0.50 (f_remote=0.231):
  CXL  cost 2%: R* =  29.2  (model uses R=4)
  RDMA cost 6%: R* =   7.5  (model uses R=60)
```

Reading it: CXL pooling stays positive across the 30-90 percent band and flips only
when the pool itself empties (u = 0.92, where unplaced bursts must be bought in a
hurry). Page-grain RDMA pooling is negative *everywhere* -- the quantitative form of
the pre-CXL consensus. The punchline is the last block: at 50 percent fleet
utilization the pool breaks even only if the hop costs under ~29x local (2 percent
pool overhead) or ~7.5x (6 percent overhead). Measured CXL lands at 3-4x -- inside.
Measured RDMA with software lands at 50-150x -- out by an order of magnitude. The
stall and the revival are both in those two numbers.

## Interview angle

- **Why did memory lag storage?** Grain mismatch: storage tolerates 100-us
  object/block access over TCP; memory needs cache-line grain at a few-x tax, which
  no network offered until CXL.
- **Where does the pooling win come from?** Variance averaging: per-host headroom
  sums to `N*h`; pooled headroom grows like `sqrt(N)`.
- **What breaks first as the ratio rises?** Bandwidth and blast radius, not capacity:
  uplinks saturate; one appliance failure evicts every attached host's remote region.
- **When would you still not pool?** Latency-critical hot sets, security boundaries
  that cannot share a switch, fleets with uniformly low demand variance.

## References

1. K. Lim, J. Chang, T. Mudge, P. Ranganathan, S. K. Reinhardt, T. F. Wenisch,
   "Disaggregated memory for expansion and sharing in blade servers," ISCA 2009 --
   <https://doi.org/10.1145/1555754.1555789> (doi.org 302 -> ACM; Crossref-verified)
2. K. Lim, Y. Turner, J. R. Santos, A. AuYoung, J. Chang, P. Ranganathan,
   T. F. Wenisch, "System-level implications of disaggregated memory," HPCA 2012 --
   <https://doi.org/10.1109/HPCA.2012.6168955> (doi.org 302 -> IEEE)
3. D. Beaver et al., "Finding a needle in Haystack: Facebook's photo storage," OSDI
   2010 -- <https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Beaver.pdf> (200)
4. S. Muralidhar et al., "f4: Facebook's Warm BLOB Storage System," OSDI 2014 --
   <https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-muralidhar.pdf>
   (200; the landing page 403s to curl, PDF probed directly)
5. J. Gu, Y. Lee, Y. Zhang, M. Chowdhury, K. G. Shin, "Infiniswap: Remote Memory
   Paging for Datacenters," NSDI 2017 --
   <https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/gu> (200)
6. Y. Shan et al., "LegoOS: A Disseminated, Distributed OS for Hardware Resource
   Disaggregation," OSDI 2018 --
   <https://www.usenix.org/conference/osdi18/presentation/shan> (200)
7. H. Li et al., "Pond: CXL-Based Memory Pooling Systems for Cloud Platforms," ASPLOS
   2023 -- <https://doi.org/10.1145/3575693.3578835> (doi.org 302 -> ACM)
8. CXL Consortium, "CXL Specifications" (2.0/3.0/3.1 features) --
   <https://computeexpresslink.org/cxl-specification/> (200)
9. AWS, "The Nitro System" -- production compute-storage disaggregation --
   <https://aws.amazon.com/ec2/nitro/> (200)
