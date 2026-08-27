# CXL Memory: Pooling, Tiering, and the End of Stranded DRAM

## The Resource That Strands

CPUs, NICs, and disks are allocated elastically in every serious fleet. Memory is not:
DRAM slots are fixed to server SKUs at purchase time, so every host carries capacity for
*its own* peak, and that capacity idles at every other moment. Fleet memory utilization
commonly lands in the 40-60 percent band (the Azure measurements in
[Pond, ASPLOS 2023](https://doi.org/10.1145/3575693.3578835) are the canonical citation)
because operators provision against per-server tails they cannot share. CXL (Compute
Express Link) attacks this by making device-attached DRAM reachable over a cache-coherent
PCIe-class fabric. The claim is not "cheaper bytes" -- CXL bytes are slower than
socket-local bytes -- but "**fewer total bytes** for the same service level, because
capacity becomes fungible." Protocol layers live in
[Modern Interconnects](./modern-interconnects.md); driver and tooling walkthroughs live in
[the kernel CXL page](../../linux/kernel/memory/cxl.md); this page covers economics and system shapes.

## CXL.mem in Sixty Seconds

CXL reuses the PCIe 5.0+ physical layer and stacks three protocols on it:

| Protocol | Job | Who uses it |
|---|---|---|
| CXL.io | Discovery, config, interrupts (PCIe-compatible) | every CXL device |
| CXL.cache | Device caches and snoops host memory | Type 1 and Type 2 devices |
| CXL.mem | Host reads/writes device-attached memory | Type 2 and Type 3 devices |

| Type | Protocols | Canonical device | Notes |
|---|---|---|---|
| Type 1 | CXL.io + CXL.cache | SmartNIC | caches host memory, exposes none |
| Type 2 | all three | GPU/FPGA accelerator with HBM | coherent with host, bi-directional |
| Type 3 | CXL.io + CXL.mem | memory expander (DIMM or appliance) | pure memory endpoint; the subject here |

A Type 3 access is a plain load/store: on a miss, the CPU's memory controller forwards
the address to the device's home agent, it travels as CXL.mem `MemRd`/`MemWr` packets,
and the device returns data from its local DRAM. Decoders map host physical to device
physical addresses, with interleave across devices for bandwidth. Spec versions matter
here: CXL 2.0 (2020) added switches and multi-logical-device (MLD) addressing -- the
enabler for carving one appliance among hosts -- and CXL 3.0 (2022) added multi-level
switching and dynamic capacity, moving toward fabric memory
([CXL Consortium specifications](https://computeexpresslink.org/cxl-specification/)).

## Three Promises: Pooled, Tiered, Shared

"CXL memory" bundles three different system shapes; keeping them distinct prevents most
architectural arguments:

```text
   POOLED (exclusive, dynamic)     TIERED (per-host, static)     SHARED (multi-host)
   ---------------------------     --------------------------    ----------------------
   host A        host B            host A          host B        host A      host B
     |             |                  |               |             |           |
   [ CXL switch ]--[ CXL switch ]  DRAM | +----------+ | DRAM       [ switch  ]
     |      |        |      |           | | CXL DRAM | |               |         |
     |   +--+--------+--+   |           | | (slow)   | |            +--+----+ +-+----+
   [M1]   [M2]      [M3]  [M4]         +-+----------+-+            |  M    | |  M   |  one device
   M2 owned by A now,                                             +-------+ +------+  mapped into
   may be re-assigned to B           cold pages demoted                              both hosts
                                     down the tier        A and B both READ (coherence!)
   ownership: 1 host at a time     ownership: 1 host, fixed    ownership: many hosts
   allocation: minutes             allocation: boot time       allocation: simultaneous
```

| Property | Expansion (direct-attach) | Pooling (switch) | Sharing (multi-host) |
|---|---|---|---|
| Capacity reuse across hosts | none | yes, exclusive at any instant | yes, concurrent |
| Software surface | NUMA node | NUMA node + fabric manager | distributed-shared-memory semantics |
| Primary win | capacity beyond DIMM slots | recovers stranded capacity | replica/computation colocation |

Most production plans are the middle column (maturity: direct-attach since 2023 server
CPUs, early switches 2023-2025); the right column is where CXL 3.x wants to go and where
RDMA research has lived for a decade (below).

## The Latency Budget

CXL memory is coherent, but it is not DRAM. Budget it as its own tier:

| Path | Added latency (read) | Notes |
|---|---|---|
| Local DDR5 channel | baseline (~80-90 ns end-to-end) | 8 channels: roughly 300 GB/s per socket |
| Type 3, direct-attach | +90-160 ns (about 2-3x local) | [TPP](https://doi.org/10.1145/3582016.3582063) measured ~77 ns local vs ~228 ns on the CXL node |
| One switch hop | add roughly 50-100 ns more | vendor-reported; varies by switch generation -- measure your own |
| Multi-host shared access | switch + coherence traffic | snoop/back-invalidate overhead on top |

Bandwidth asymmetry matters as much as latency: one x16 PCIe 5.0 link carries about
63 GB/s versus roughly 300 GB/s across an 8-channel DDR5 socket -- a ~1/5 tier, so
*what* you place there matters more than *how much*: streaming workloads hide the
latency, pointer-chasing and lock-heavy ones do not. See
[DRAM fundamentals](../memory-tech/dram.md) and
[NUMA scheduling](../../linux/kernel/processes/numa-scheduling.md) for what remote
access already costs between sockets.

## Pooling Math: Why Stranding Disappears

The stranding effect is statistical, not anecdotal. Provisioning each host for its own
95th-percentile peak costs far more than provisioning one pool for the aggregate 95th
percentile: peaks decorrelate across hosts, so aggregate tails flatten while per-host
tails cannot cancel. The runnable model below (Python 3.12, seeded) simulates a 64-server
fleet with lognormal demand bases, daily cycles, and occasional spikes:

```python
"""Memory-stranding math: 64-server fleet, per-server peaks vs a pooled fleet.

Demand model: each server's memory demand oscillates daily around a lognormal
base with multiplicative noise and occasional spikes (batch jobs, cache blooms).
A server-only design must provision each host for ITS OWN 95th-percentile
peak; a pooled design only needs the fleet aggregate's 95th-percentile.
"""
import math
import random
import statistics

random.seed(7)

SERVERS, INSTALLED_GB, HOURS = 64, 512, 30 * 24

def p95(xs):
    return statistics.quantiles(xs, n=100, method="inclusive")[94]

demand = {}                      # server id -> list of hourly demand (GB)
for s in range(SERVERS):
    base = min(510.0, random.lognormvariate(5.25, 0.50))    # wide per-host spread
    phase = random.uniform(0, 6.28)
    series = []
    for t in range(HOURS):
        daily = 1.0 + 0.50 * ((1 + math.sin(6.283 * t / 24 + phase)) / 2)
        noise = random.gauss(1.0, 0.08)
        spike = random.uniform(1.4, 2.5) if random.random() < 0.07 else 1.0
        series.append(min(510.0, base * daily * noise * spike))
    demand[s] = series

installed = SERVERS * INSTALLED_GB
mean_used = sum(sum(v) for v in demand.values()) / HOURS
mean_util = mean_used / installed

local_needed = sum(p95(v) for v in demand.values())          # per-host p95
aggregate = [sum(demand[s][t] for s in range(SERVERS)) for t in range(HOURS)]
pool_needed = p95(aggregate) * 1.10                          # +10% pool headroom

print(f"fleet installed DRAM          : {installed:8.0f} GB ({installed/1024:.1f} TB)")
print(f"mean fleet utilization        : {mean_util:8.1%}")
print(f"provision per-host p95 (sum)  : {local_needed:8.0f} GB "
      f"({local_needed/mean_used:.2f}x mean demand)")
print(f"provision pooled p95 +10%     : {pool_needed:8.0f} GB "
      f"({pool_needed/mean_used:.2f}x mean demand)")
print(f"reclaimable via pooling       : {local_needed - pool_needed:8.0f} GB "
      f"({(local_needed - pool_needed)/installed:.1%} of installed)")
worst = max(statistics.mean(v) / INSTALLED_GB for v in demand.values())
quietest = min(statistics.mean(v) / INSTALLED_GB for v in demand.values())
print(f"busiest host, mean use        : {worst:8.1%} of its 512 GB")
print(f"quietest host, mean use       : {quietest:8.1%} of its 512 GB")
```

Real output:

```text
fleet installed DRAM          :    32768 GB (32.0 TB)
mean fleet utilization        :    50.0%
provision per-host p95 (sum)  :    23344 GB (1.42x mean demand)
provision pooled p95 +10%     :    18878 GB (1.15x mean demand)
reclaimable via pooling       :     4466 GB (13.6% of installed)
busiest host, mean use        :    99.0% of its 512 GB
quietest host, mean use       :    15.4% of its 512 GB
```

Read the two provisioning lines as the whole argument. Server-side-only planning needs
**1.42x** mean demand because every host drags a private tail; a pool sized on the
aggregate -- whose volatility collapses across 64 independent series -- needs **1.15x**,
already padded with 10 percent headroom. One byte in seven of installed DRAM is pure
insurance against per-host variance, and hosts idle anywhere from 1 to 85 percent while
the fleet averages 50 percent utilization. That is the "2:1 overprovisioning" complaint.
Honesty checks: the model ignores the latency tax, and correlated growth (everyone's
cache in the same incident) is what the 10 percent headroom must absorb.

## Software: a Type 3 Device Is Just a NUMA Node

Linux treats CXL memory as a higher-numbered NUMA node: ACPI's CFMWS window describes
the address range, HMAT/SLIT tables describe its (worse) latency and bandwidth, and the
region becomes hot-plugged RAM. Classic remote-memory tooling then applies, and tiering
decides placement:

- **Demotion**: under local-DRAM pressure, cold pages migrate to the slower node
  (reclaim demotion path). **Promotion**: NUMA-balancing fault stats migrate hot pages
  back up.
- **Proactive placement**: [DAMON](../../linux/kernel/memory/damon.md) profiles access
  frequency and can drive migration or reclamation ahead of the OOM/reclaim cliff; with
  CXL tiers it becomes the placement policy engine (usage:
  [kernel DAMON admin guide](https://docs.kernel.org/admin-guide/mm/damon/index.html)).
- **Policy lessons**: Meta's TPP found always-demotion hurt latency-sensitive jobs and
  added hotness-aware placement. Default kernel behavior is conservative for a reason.

Driver-level detail (`drivers/cxl/`, region construction, HMAT plumbing, plus
[NUMA integration](../../linux/kernel/memory/numa.md)) is in [the kernel CXL page](../../linux/kernel/memory/cxl.md).

## Sharing Costs: Coherence Is the Price of Concurrency

Pooled memory changes *who owns* a page; shared memory changes *who can see it*. A
multi-host shared Type 3 device must keep caches coherent (back-invalidate snoop,
formalized in CXL 3.x): that costs a coherence directory, snoop bandwidth, and serialized
ordering -- and semantics: concurrent writers need distributed synchronization, so most
"sharing" deployments are really sharded. Concurrency pays for replicated read-mostly
data (embedding tables), checkpoint/HA memory, and shared KV caches for inference replicas
(see [disaggregated inference](../../llm/advanced/distributed/disaggregated-inference.md),
which does that today with RDMA and NVLink at process granularity).

## Products and Ecosystem

- **CPUs**: Intel's 4th-gen Xeon (Sapphire Rapids, 2023) brought CXL Type 3 support to
  volume x86 servers; later Xeons widened switch/fabric features, and AMD EPYC 9004
  (Genoa) supports CXL 1.1+ memory expansion. Check per-SKU spec revisions.
- **Devices**: Samsung's [CMM](https://semiconductor.samsung.com/dram/cxl-memory-module/),
  the first announced CXL DRAM expander (then the CMM-D DDR5 module), defined the
  category; Micron, SK hynix, and Marvell ship competing expanders and controllers.
- **Switches**: silicon from Broadcom, Marvell, and XConn enables the pooled topology; young fabric managers are the gap between demos and fleets.
- **Security**: link encryption (IDE) and device security (TSP) arrived with CXL 2.0+,
  because a DIMM on a cable outside the chassis changes the threat model -- see the
  [confidential computing stack](../../security/advanced/confidential-computing.md).

## The RDMA Lineage CXL Walks Into

CXL is not the first attempt to break the memory wall between servers. Since ~2016 the
research line has been RDMA-based remote memory: Infiniswap
([NSDI 2017](https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/gu))
turned spare cluster memory into a block device for paging; AIFM and Leap (OSDI 2020)
exposed remote memory through runtimes and smart offloads. The trade against CXL:

| | RDMA disaggregation | CXL pooling |
|---|---|---|
| Software model | explicit API/library, app-visible | load/store, OS-visible NUMA node |
| Cache coherence | none (caller manages) | hardware-enforced |
| Reach | rack-to-datacenter over cluster fabric | in-rack, few switch hops |
| Legacy apps | requires porting | runs unmodified, slower |
| Hardware | reuses existing NICs/network | new switches + CXL silicon |

The honest synthesis: RDMA wins on reach and bypassing the CPU memory controller; CXL wins
on transparency and coherence. [RDMA](../../linux/networking/rdma.md) and
[InfiniBand](../../linux/storage/infiniband.md) predate CXL by a decade, which is why
large systems often end up hybrid: CXL inside the rack, RDMA between racks.

## Failure Modes

- Treating the CXL node as ordinary RAM: tail latencies wreck lock-heavy services; test with real access patterns.
- Demotion thrash: aggressive demotion ping-pongs hot pages; watch promotion counters, gate per workload.
- Switch bandwidth cliffs: pooled devices share upstream links; CXL fabric QoS is immature.
- Re-stranding inside the pool: fragmented regions recreate bin-packing in the fabric manager.
- Uneven firmware support: validate CFMWS/HMAT tables on 2023-era platforms before designing on them.

## Related

- [Modern Interconnects](./modern-interconnects.md) | [Kernel CXL subsystem](../../linux/kernel/memory/cxl.md)
- [NUMA](../../linux/kernel/memory/numa.md) | [NUMA scheduling](../../linux/kernel/processes/numa-scheduling.md) | [DAMON](../../linux/kernel/memory/damon.md)
- [Disaggregated inference](../../llm/advanced/distributed/disaggregated-inference.md) | [RDMA](../../linux/networking/rdma.md) | [InfiniBand](../../linux/storage/infiniband.md)

## References

- CXL Consortium specifications: https://computeexpresslink.org/cxl-specification/
- Linux kernel CXL driver documentation: https://docs.kernel.org/driver-api/cxl/index.html
- Shan et al., "Pond: CXL-Based Memory Pooling Systems for Cloud Platforms," ASPLOS 2023: https://doi.org/10.1145/3575693.3578835
- Agarwal et al., "TPP: Transparent Page Placement for CXL-Enabled Tiered-Memory," ASPLOS 2023: https://doi.org/10.1145/3582016.3582063
- Gu et al., "Infiniswap: Remote Accessible Memory," NSDI 2017: https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/gu
