# Computational Storage: Compute Where the Bits Are

A conventional SSD is a ~2 GB/s+ storage device wrapped around a small computer that is already touching every byte: the controller parallelizes, scrambles, ECCs, and wear-levels data across dozens of NAND dies. Computational storage asks the obvious question -- if a full ARM/FPGA computer is already in the data path, why must every scan, filter, and aggregate be shipped over PCIe to host CPUs and back? The SNIA-defined answer (computational storage drives, processors, and a standard NVMe command set) spent 2019-2023 as a promising category, then settled into a niche: powerful where queries are selective and host CPU is the bottleneck, unimpressive where they are not. This page covers the bandwidth math that decides which case you are in, the standardization stack, the flagship product, and the reasons adoption lagged. For placement in a full tiering/ disaggregation architecture see [Tiered & Persistent Storage](../storage/advanced/tiered-persistent.md).

## The Data-Movement Tax

Two budgets decide whether moving compute to data pays:

- **The host link.** PCIe 3.0 x4 moves ~3.9 GB/s, 4.0 x4 ~7.9 GB/s, 5.0 x4 ~15.8 GB/s (raw line rate per lane is 8/16/32 GT/s; ~1.5% encoding overhead). Every byte scanned by the host crosses this link and lands in host DRAM, consuming both directions' bandwidth and memory-controller cycles.
- **The internal array.** A modern NVMe controller talks to 8-16 NAND channels in parallel; internal array bandwidth on current drives is at or above the host link (a Gen4-class drive streams 5-7 GB/s to the host while its NAND array can sustain more). The gap between internal and host-visible bandwidth is the exploitable resource.

Filtering is the canonical exploit. Scanning 1 TB with selectivity `s`:

| selectivity | bytes to host (pushdown) | PCIe 4.0 x4 transfer | host CPU avoided (filter @ ~2 GB/s/core) |
| ----------- | ------------------------ | -------------------- | ---------------------------------------- |
| 0.1% | 1 GB | ~0.2 s | ~500 core-s |
| 1% | 10 GB | ~1.6 s | ~500 core-s |
| 10% | 100 GB | ~16 s | ~500 core-s |
| 50% | 500 GB | ~80 s | ~500 core-s (but bandwidth barely improves) |

Reading the table honestly: the in-drive scan still takes ~1 TB of internal time (~200 s at 5 GB/s), so wall-clock improvement at 1% selectivity is modest -- the win is the ~500 core-seconds of host filtering CPU eliminated and ~99% of PCIe ingress freed for other tenants. Below ~20% selectivity both matter; at 50% you are just moving the same bytes with extra steps, and a weak in-drive core may be slower than a host core with SIMD.

Aggregation pushdown has a stronger profile: a `GROUP BY region SELECT count(*)` computed in-drive ships back only the groups (dozens of rows), independent of input size, so 1 TB scans return in kilobytes -- provided the drive's compute can run the reduction at NAND read speed, which is exactly the programmability gap described below.

## A Wall-Clock Model You Can Run

The bandwidth numbers interact through three serial-resource constraints: the drive reads everything it needs at internal bandwidth, traditional filtering consumes host cores at `cores x per-core rate`, and whatever is not filtered crosses PCIe. Pushdown removes the second constraint and shrinks the third, but keeps the first. The model below computes wall time both ways across selectivity and free-host-core scenarios:

```python
def scan_seconds(data_gb, selectivity, free_cores,
                 internal_gbs=5.0, link_gbs=6.3, host_gbs_per_core=2.0):
    moved = data_gb * selectivity
    t_read = data_gb / internal_gbs                       # both paths: drive reads all data
    t_trad = max(t_read,                                  # internal streaming
                 moved / link_gbs,                        # PCIe (traditional moves everything)
                 data_gb / (host_gbs_per_core * free_cores))  # host cores do the filtering
    t_push = max(t_read, moved / link_gbs)                # drive filters; host gets results
    return t_trad, t_push

print(f"{'selectivity':>11} {'free cores':>10} {'trad (s)':>9} {'pushdown (s)':>13} {'wall gain':>10} {'pcie saved':>11}")
for sel in (0.001, 0.01, 0.1):
    for cores in (1, 4):
        t1, t2 = scan_seconds(1000, sel, cores)
        print(f"{sel:>11} {cores:>10} {t1:>9.1f} {t2:>13.1f} {t1/t2:>9.1f}x {100*(1-sel):>10.1f}%")
```

Real output from this environment:

```text
selectivity free cores  trad (s)  pushdown (s)  wall gain  pcie saved
      0.001          1     500.0         200.0       2.5x       99.9%
      0.001          4     200.0         200.0       1.0x       99.9%
       0.01          1     500.0         200.0       2.5x       99.0%
       0.01          4     200.0         200.0       1.0x       99.0%
        0.1          1     500.0         200.0       2.5x       90.0%
        0.1          4     200.0         200.0       1.0x       90.0%
```

Read it the way an architect would: with 4 free host cores, traditional filtering overlaps streaming completely and wall time is identical -- pushdown buys only the PCIe/DRAM relief. With 1 free core, host filtering is the bottleneck (500 s vs 200 s) and pushdown is 2.5x. The identical pushdown column across selectivities is the honest limitation: the drive still reads all 1 TB internally, so wall time is floored at ~200 s. That floor is also why in-drive *compression-aware* filtering matters -- halving internal read time on compressed columns moves it to ~100 s and makes pushdown win even with idle hosts, and true aggregation (result bytes ~ 0) removes the PCIe term entirely. The headline: computational storage is a host-CPU and bandwidth-recovery technology; it becomes a latency technology only with compression, aggregation, or contended hosts.

## Two Paths Through the Device

```text
 Traditional path (all bytes cross PCIe):

   NAND array --5-7 GB/s--> SSD controller --> PCIe x4 --> host DRAM
   (7 GB/s internal)        (flow control)   (7.9 GB/s)       |
                                                              v
                                              host cores filter/aggregate ~2 GB/s/core
                                              -> results, hot DRAM filled with rejected rows

 In-drive compute path (SNIA/NVMe computational storage):

   NAND array --> SSD controller +--> I/O path --> PCIe (only matching rows)
                                 |
                                 +--> compute engine (FPGA fabric / ARM cores)
                                        filter predicate, aggregate, decompress
                                        runs at internal bandwidth
                                        -> kilobytes of results cross PCIe
```

The second path is what SNIA standardized; the first is what every drive still does by default.

## The SNIA Model: CSD and CSP

SNIA's Computational Storage Technical Work Group defined the terms and a vendor-neutral architecture (the "Computational Storage Architecture and Programming Model" spec line; see snia.org/computational):

- **Computational Storage Drive (CSD):** a storage device with integrated compute -- the SmartSSD pattern. Compute shares the device with flash management; isolation and resource contention are the design problems.
- **Computational Storage Processor (CSP):** a standalone processor attached in front of storage (PCIe card or appliance) that computes over data streams without being the storage endpoint -- more flexible (standard OS environment), but data still moves across a link to reach it, so it recovers some of the data-movement tax rather than all of it.

The spec's contribution is scoping: it names the functions any CSD must expose (discover capabilities, execute a function over a namespace, report status) independently of how a vendor implements them, plus a programming-model track for how hosts describe and invoke those functions. SNIA deliberately does not standardize the execution environment (FPGA bitstream vs ARM binary vs P4-like pipeline), which is both why the spec exists and why the ecosystem fragmented anyway.

## NVMe 2.0 Family: the Computational Programs Command Set

NVMe moved computational storage from vendor commands to a standard command set when the 2.0-era reorganization (base spec + independent command-set specs) landed. The relevant document is the **NVM Express Computational Programs Command Set Specification**, which exists precisely to "allow computational programs to operate on data located in an NVM subsystem" (NVM Express, specification page). As of August 4, 2026 the live family is: NVMe Base Specification revision 2.4, with the Computational Programs Command Set at revision 1.3 -- evidence the work group kept iterating after the initial 2021 restructure rather than shipping once.

What the command-set approach buys: a namespace can carry compute programs alongside standard read/write; discovery and execution are admin/I-O queue operations like any NVMe command, so no new transport; and the same fabric path (NVMe-oF) can reach computational devices remotely. What it does not settle: what a "program" is compiled from. Hosts still meet per-vendor SDKs (FPGA flows, proprietary function IDs) at the last mile -- standardization covers transport and discovery, not portability of the compute payload.

## Samsung SmartSSD: the Reference Product

The concrete embodiment of the CSD definition is Samsung's SmartSSD: a Samsung NVMe SSD controller paired with a Xilinx (now AMD) FPGA in one U.2/U.3 device, so the FPGA sits on the flash channel side of the PCIe host interface and can process data as it streams off NAND.

- First-generation devices were announced as industry-first adaptable computational storage drives by Xilinx and Samsung (November 2020), targeting database filtering, video analytics/transcoding, and AI preprocessing where host CPUs otherwise spend cores on data reduction.
- A second generation was announced by Samsung in February 2022 with upgraded processing capability, developed with AMD (post-acquisition of Xilinx) and positioned at the same workloads with better process node and fabric.
- Samsung's published motivation matches the math above: reduce data moved to the CPU and free host cores; the device is sold as much on host CPU utilization reduction as on bandwidth.

SmartSSD remains the case study because it shipped at scale with an honest interface (FPGA programmable via Vitis, no proprietary black box), which is more than can be said for most of the category.

## What Near-Data Processing Actually Accelerates

The academic record agrees with the arithmetic. Willow (OSDI 2014, Seshadri et al.) built a user-programmable SSD with a simple SDK and showed that in-storage filtering and aggregation for analytical scans can run at the device's internal bandwidth -- and, just as usefully, catalogued how much engineering the "simple SDK" took. The survey by Lukken and Trivedi (arXiv 2112.09691) organizes the design space the same way this page does: which operations are stream-parallel (scan, filter, project, decompress, aggregate), which need cross-record state (joins, sorts), and how the boundary moves with each controller generation.

The pattern that holds across all of them:

- **Wins are selectivity- and compute-bound, not bandwidth-bound.** In-storage filtering, predicate pushdown, decompression-then-filter, and pre-aggregation all reduce host-side bytes or CPU per byte. Full-table random reads and joins do not compress over the link and gain little.
- **Compression is a multiplier.** Filtering on compressed data inside the drive (common: 2-4x columnar compression) multiplies the effective internal bandwidth advantage and cuts host bytes further.
- **The host CPU savings often exceed the latency savings.** For cloud operators, 500 core-seconds per TB scanned freed from `WHERE` clauses is a capacity story, not just a speed story.

## Deployment Realities

| reality | consequence |
| ------- | ----------- |
| fragmented programming models | per-vendor SDKs (FPGA flows, proprietary function IDs); code is not portable between CSDs; NVMe standardizes transport, not the compute payload |
| weak general-purpose compute in-device | SSD controller ARM cores are far below host cores; realistic in-drive compute means FPGA skills (HDL/HLS), a talent bottleneck |
| resource contention | compute shares controller SRAM, PCIe credits, and NAND channels with I/O; a heavy program degrades plain reads on the same device |
| operational gaps | per-device firmware updates, telemetry, and multi-tenant isolation lag the enterprise SSD tooling hosts already run |
| economics | premium device price needs a workload that is selective, read-mostly, and CPU-bound simultaneously; most fleets are not |

This is why the category is real but narrow: archives and scan-heavy analytics (where selectivity is low and host CPU is contended), edge/appliance boxes where one box's worth of host CPU cannot afford to filter sensor blobs, and security-sensitive flows where data should not leave the device. General-purpose OLTP gained nothing, and zoned/direct-I/O approaches on ordinary NVMe drives captured much of the host-CPU-bypass benefit at zero premium.

## Vendor Landscape at a Glance

| vendor / product | form | compute model | status and lesson |
| ---------------- | ---- | ------------- | ----------------- |
| Samsung SmartSSD (1st gen 2020, 2nd gen 2022) | CSD: NVMe SSD + Xilinx/AMD FPGA | programmable FPGA fabric (Vitis flow) | the category's only at-scale shipping product |
| ScaleFlux computational SSDs | CSD with on-controller compute cores | fixed-function + programmable engines, exposed as transparent compression | showed compression-offload alone can carry a product |
| NGD Systems in-situ processing | CSD computing inside NAND dies | ARM cores per die | advanced concept; company wound down -- ambition outran the software stack |
| Nebulon SPU (acquired by NVIDIA, 2021) | CSP-style processing unit in server | embedded ARM/FPGA offload for storage services | absorbed into DPU line -- the CSP idea migrated toward SmartNICs |
| Generic "FPGA in front of NVMe" appliances | CSP | vendor FPGA shell + customer kernels | real deployments exist, all bespoke |

The pattern across rows: hardware shipped, programmability did not standardize, and the surviving strategies are either fixed-function (compression) or folded into the DPU ecosystem. Interview answer for "why did computational storage underdeliver?": every vendor solved silicon; none solved the software distribution problem -- there is still no equivalent of "an app store for storage programs", and the NVMe command set standardizes invocation, not portability of the compute payload.

## Relationship to DPUs and SmartNICs

Computational storage and DPUs solve adjacent data-movement problems at different points in the path. A DPU (e.g., BlueField-class SmartNIC) sits between the network and the storage stack, offloading NVMe-oF targets, encryption, and virtualization -- moving compute toward the *network* end of the data path. A CSD moves compute toward the *media* end, past the PCIe boundary. They compose: a rack can run remote NVMe into a DPU, which fronts ordinary drives, or front CSDs and filter before data ever crosses the fabric. The conceptual takeaway is identical -- every byte that must be examined should be examined at the earliest point that has the capability -- and the adoption constraint is identical too: programmability standardization lags the silicon.

## References

- SNIA, Computational Storage (architecture spec, CSD/CSP definitions, technical work group) - <https://www.snia.org/computational>
- NVM Express, Computational Programs Command Set Specification (part of the NVMe 2.x family; rev 1.3 with Base rev 2.4 as of Aug 2026) - <https://nvmexpress.org/specification/computational-programs-command-set/>
- Samsung Newsroom, "Samsung Electronics Develops Second-Generation SmartSSD Computational Storage Drive with Upgraded Processing Functionality" (Feb 2022) - <https://news.samsung.com/global/samsung-electronics-develops-second-generation-smartssd-computational-storage-drive-with-upgraded-processing-functionality>
- Seshadri et al., "Willow: A User-Programmable SSD", OSDI 2014 - <https://www.usenix.org/conference/osdi14/technical-sessions/presentation/seshadri>
- Lukken & Trivedi, "Past, Present and Future of Computational Storage: A Survey", arXiv 2112.09691 - <https://arxiv.org/abs/2112.09691>
