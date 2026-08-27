# Chiplets & UCIe

For five decades a bigger, better processor meant one bigger die. That road ended twice over. First, reticle optics: a single lithographic exposure covers at most about 26 mm x 33 mm, roughly 858 mm2, and no die larger than that can be printed in one shot - the biggest GPUs ever shipped (NVIDIA's GV100/A100 class at ~815-826 mm2) sit flush against this ceiling. Second, economics: wafer costs per mm2 climb steeply every node while large dies multiply defect exposure, so a monolithic flagship wastes most of its silicon. Chiplets - small dies engineered together in one package over high-bandwidth die-to-die links - are the industry's answer, and UCIe is the attempt to make dies from different vendors interoperate the way PCIe made cards from different vendors interoperate.

## The yield math that motivates everything

The standard yield model treats defects as clustered point events (the negative-binomial / "Bose-Einstein" form):

```text
   Y(A)  =  1 / (1 + D * A)^c

   A  = die area (cm^2)
   D  = defect density (defects per cm^2)
   c  = clustering factor (c = 1 is the simple case; real fabs see c > 1)
```

Defects do not care how big your design ambition is: area is exposure. One reticle field of silicon (858 mm2 = 8.58 cm2) at D = 0.1/cm2 and c = 2:

| Partition | Die area | Yield per die | Dies | Expected good mm2 per reticle field |
| --- | --- | --- | --- | --- |
| Monolithic | 858 mm2 | 29% | 1 | ~249 mm2 |
| 4 chiplets | 214.5 mm2 each | 68% | 4 | ~582 mm2 |
| 8 chiplets | 107 mm2 each | 82% | 8 | ~700 mm2 |

Same silicon area, roughly 2.3-2.8x more of it usable - that multiplier is the business case. It is not free money, though, and a fair accounting subtracts: known-good-die testing at full speed (harder than it sounds for analog and high-speed SerDes), D2D PHY area and bump pads on every chiplet edge, interposer or bridge packaging cost, and assembly yield (one bad chiplet scraps a package). Chiplets win when the yield multiplier exceeds those overheads - which, above a few hundred mm2 of total silicon, it reliably does.

Worth internalizing how the parameters move: defect density D falls slowly per node while wafer cost per mm2 rises quickly, so the *reticle-sized* monolith is the worst possible area to be stuck at - maximum exposure at maximum unit cost. Clustering (c > 1) is what keeps very large dies viable at all; without it, GPU-class monoliths would be economically impossible. And note what the formula does not capture: a 4-chiplet package needs all 4 good to ship, so the relevant quantity is expected good area (yield times area summed over chiplets), not package-level yield - AMD absorbs the 1-of-12 loss rate on Genoa by binning, fusing off defective CCDs, and selling the same silicon from 1 CCD client parts to 12 CCD server parts.

## Case study: where AMD drew the seam

Zen 2 (2019) is the canonical partitioning decision, and the *location* of the seam teaches more than the split itself. AMD cut at the L3 boundary: each CCD is a self-contained 8-core complex with its own caches, talking to a central IOD over Infinity Fabric. Consequences, in order of importance:

- **No coherence structures cross the seam.** The CCD keeps its own L3 snoop filter; the fabric carries cache-line traffic, not probe broadcasts, which keeps IOD complexity and latency manageable.
- **The IOD was a generation behind on purpose.** First-gen Zen 2 IODs shipped on a mature GlobalFoundries node while CCDs used TSMC N7 - the node-mixing saving that monolithic designs can never access.
- **The seam cost was paid in memory latency.** Crossing CCD-to-IOD-to-DRAM adds latency versus an integrated memory controller, and scaling CCD count (Rome 8 -> Genoa 12) kept the I/O die as a congestion point - the reason Genoa doubled DDR5 channels to 12 and widened fabric links.
- **Software saw a socket, not chips.** Despite up to 9 dies, the platform enumerated one socket with NUMA domains - the packaging/UI work that made chiplets commercially invisible.

Later designs refined rather than reversed the seam: 3D V-Cache bonds an SRAM-only chiplet onto the CCD with hybrid bonding (SoIC-class, sub-10 um bonding), adding L3 density exactly where a wire-bonded or 2.5D seam would have been too slow - the seam moved *into* the cache hierarchy without moving out of the yield story.

## Partitioning: deciding what becomes a chiplet

The engineering question is not "should we split?" but "where is the seam cheapest?" Rules that have converged across the industry:

- **Compute stays dense, I/O goes mature.** Logic benefits most from the newest node; SerDes, DDR5/HBM PHYs, and PCIe controllers do not, and they carry analog content that thrives on cheaper nodes. AMD pairs TSMC N5/N4 compute chiplets with an I/O die on N6; Intel's Meteor Lake scatters tiles across Intel 4, Intel 16-class, and TSMC N5/N6.
- **SRAM resists the split.** Caches scale poorly with new nodes and hate deep I/O latency, so big L3 stays on the compute die; cutting a coherent cache domain across dies costs latency and complexity.
- **Frequency islands justify themselves.** Chiplet boundaries let each die ship at its own voltage/frequency sweet spot and let a base tile run slow, low-leak logic for always-on functions (Meteor Lake's low-power SoC tile exists precisely to absorb idle work).
- **Reuse compounds.** One I/O die serves many compute chiplet generations and product tiers: AMD tiles 1-12 compute chiplets around a common IOD from client to 96-core server parts.
- **Memory wants adjacency.** HBM stacks must sit millimeters from their PHY on an interposer; the package floorplan is planned around memory placement first, not last.
- **Keep the boot domain small and mature.** Reset, firmware, and security roots live on the most conservative die in the package (AMD's IOD, Meteor Lake's base tile), because a chiplet that cannot POST cannot be binned.
- **Respect IP and supply boundaries.** A seam is also a legal/procurement line: third-party accelerators, foundry-mixed packages, and multi-sourcing all argue for boundaries exactly where UCIe-class interfaces make them affordable.

## Die-to-die interfaces before and after UCIe

| Interface | Steward | Scope | Medium / reach | Notes |
| --- | --- | --- | --- | --- |
| BoW (Bump-on-Wire) | OCP OSDI workgroup | Open, non-coherent-focused | Organic substrate, ~130 um-class bumps | Lowest cost; energy-lean signaling for short organic-reachable hops |
| AIB (Advanced Interface Bus) | Intel (open-sourced) | Source-synchronous D2D | Organic or bridge packages | Platform-agnostic PHY IP; predecessor mindset to UCIe |
| Infinity Fabric (IFOP/IFIS) | AMD | Coherent + non-coherent, package and socket | Package traces (xGMI between sockets) | Proprietary; carries coherence, security (SMEE encryption), power management across up to a dozen chiplets |
| NVLink-C2C | NVIDIA | Coherent CPU-CPU / CPU-GPU | Silicon interposer / package (Grace) | ~900 GB/s bidirectional; couples Grace CPUs and Grace-Hopper superchips |
| UCIe | UCIe Consortium (2022-) | Open standard, protocol-compatible with PCIe/CXL flits | Standard, advanced, and 3D packages | The interoperability bet; see below |

The proprietary fabrics (Infinity Fabric, NVLink-C2C) remain the performance ceiling today; UCIe's goal is that the *commodity* case - two dies on one package - stops requiring an NDA per pair.

## UCIe: what the spec actually fixes

UCIe 1.0 (2022) standardized the stack in three layers: a die-to-die PHY (bump/pad drivers, training, repair), a D2D adapter (link state, credit-based flow control, optional cache-coherent protocols mapped onto CXL/PCIe-compatible 256B-class flits), and protocol bindings so a die can expose PCIe/CXL semantics without redesign. Package classes and verified bump-pitch regimes:

- **Standard (2D, organic substrate):** bump pitch in the 100-130 um class - cheap assembly, modest bandwidth density.
- **Advanced (silicon interposer / EMIB-class):** 25-55 um pitch - the CoWoS/bridge regime where AMD, NVIDIA, and Google-class packages live.
- **UCIe-3D (added in UCIe 2.0, Aug 2024):** bonding-friendly signaling for pitches from 10-25 um down to 1 um or less, i.e., hybrid-bonding territory with bandwidth densities far beyond 2.5D.

UCIe 2.0 also broadened manageability and 3D system assembly; UCIe 3.0 (2025) doubled bandwidth capability again and pushed manageability/telemetry for multi-die systems. Read the progression as the spec chasing packaging: each time packaging gained a dimension (organic -> interposer -> stacked), UCIe redefined its PHY regime so dies stay interoperable.

A link budget sketch shows what each layer buys:

```text
   die A                          die B
   +-------------+  bump field  +-------------+
   | protocol    |  <--------> | protocol    |   PCIe/CXL-compatible flits,
   | (PCIe/CXL)  |   100-130um | (PCIe/CXL)  |   credit-based flow control
   +-------------+  organic    +-------------+
   | D2D adapter |             | D2D adapter |   retry, ordering, optional
   +-------------+             +-------------+   coherence (CXL.cache-like)
   | PHY         |             | PHY         |   clocking, training, lane
   +-------------+             +-------------+   repair, redundancy
        |_____________________________|  bumps/bridges/interposer/stack
```

The same layering serves all three package classes; what changes is the PHY's signaling regime and bump pitch, which is why the spec names them as separate implementations rather than separate protocols.

## Packaging: 2.5D vs 3D, concretely

```text
2.5D: dies side by side on an interposer          3D: dies bonded in a vertical stack

   +-------+  +-------+  +-------+                  +----------------+
   | CCD 0 |  | CCD 1 |  |  I/O  |   <- top dies    | compute dies   |
   +-------+  +-------+  +-------+                  +----------------+
+------------------------------------------------+        |  hybrid bonding
|   HBM3    HBM3      silicon interposer         |        |  Cu-Cu, <10 um
|   (microbumps -> RDL wiring -> microbumps)     |   +----------------+
+------------------------------------------------+   | base die       |
|        organic package substrate               |   | TSVs (Foveros/ |
|        (BGA balls to the motherboard)          |   | SoIC)          |
+------------------------------------------------+   +----------------+
```

- **CoWoS (TSMC)** - silicon interposer (CoWoS-S), with RDL-interposer (CoWoS-R) and local-silicon-interconnect (CoWoS-L) variants; the workhorse behind NVIDIA's H-class GPUs and AMD's MI300 series. Interposers stitch multiple reticle fields, so the *package* exceeds the reticle even though no single die does.
- **EMIB (Intel)** - small silicon bridges embedded in the organic substrate: interconnect density where dies meet, organic cost everywhere else.
- **Foveros (Intel)** - 3D face-to-face stacking over TSVs; Meteor Lake bonds a compute tile, GPU tile, SoC tile, and I/O tile onto a base die that distributes power and routes low-speed fabric.
- **SoIC (TSMC)** - hybrid (bump-less, Cu-Cu) bonding with interconnect pitches below 10 um; this is the regime that turns chiplets into effectively one dense die and where cache-like traffic becomes conceivable across the stack.

## Products that prove each point

- **AMD EPYC (Zen 2 through Zen 4)** - the volume proof. Split the monolith into 8-core CCDs plus a central IOD (Genoa: up to 12 N5 CCDs + 1 N6 IOD, 96 cores, 12 DDR5 channels), halving engineering cost per SKU and letting the server line scale from 1 to 12 compute chiplets on one fabric. IFOP links carry coherence and a memory-encryption engine between them.
- **Apple M1 Ultra (2022)** - UltraFusion fuses two M1 Max dies with a 2.5 TB/s interconnect and presents them to the OS as one SoC: one kernel, one memory space, software none the wiser. The existence proof that a D2D seam can be made software-invisible when the bandwidth is high enough.
- **Intel Ponte Vecchio (2023)** - 47 tiles from five process technologies stitched with Foveros + EMIB (with Co-EMIB bridges), over 100 billion transistors: the extreme demonstration that packaging itself became a design discipline.
- **Intel Meteor Lake (2023)** - chiplets in a client SoC: four tiles on a Foveros base, mixing Intel 4 compute with TSMC N5 graphics, showing the economics extend beyond servers.
- **NVIDIA Grace** - two Grace CPUs on one package coherent over NVLink-C2C at ~900 GB/s, with LPDDR5X onboard: memory-adjacent CPU chiplets as a data-center building block.

The MI300 series assembles the whole toolbox in one package: compute XCDs hybrid-bonded onto base I/O dies, those spread across a CoWoS-class interposer alongside HBM3 stacks, Infinity Fabric tying it together - 2.5D and 3D simultaneously, proprietary fabric inside, HBM adjacency by design. It is the clearest single artifact for understanding why "chiplet vs monolith" is really a floorplanning discipline: every seam in the package exists because yield, node choice, or bandwidth was better served by a boundary there than by one die.

## Memory implications: HBM, NUMA, and the software bill

Chiplet packages change the memory system in two opposite directions. Bandwidth goes up: attach HBM stacks directly to the package (AMD MI300X pairs 8 compute XCDs and 4 I/O dies with 8 HBM3 stacks, ~192 GB per package), and aggregate per-socket bandwidth reaches terabytes-per-second class. Latency gets uneven: a core on CCD 0 reaching a line homed on another CCD's cache domain, or contending on the IOD's memory channels, pays extra hops, and multi-CCD Threadripper/EPYC parts expose real NUMA domains that schedulers and allocators must honor (pin NIC queues, use `numactl`, size per-CCD working sets). The M1 Ultra result shows the counter-move: spend 2.5 TB/s of seam bandwidth and the NUMA-ness vanishes from software's view. The design trade is thus explicit - pay for bandwidth density to *hide* the partition, or save cost and expose it, then manage it in software. CXL extends the same question off-package: memory pools reachable at CXL latency are yet another NUMA tier (see `linux/kernel/memory/cxl.md`).

For the coherent protocol underneath (MESI-family, directories), see `arch/memory-hierarchy/moesi.md`; for HBM itself, `arch/memory-tech/hbm.md`.

## Interview lens

- *Why not just build one big die?* Reticle limit (~858 mm2) caps it physically, and the yield table above caps it economically; only wafer-scale stitching (Cerebras-class) sidesteps reticle boundaries, at extraordinary packaging cost.
- *Where does chiplet cost actually go?* Known-good-die test, packaging (interposers/bridges), and D2D PHY area. A common interview mistake is quoting raw wafer-yield savings and ignoring assembly yield on a 12-chiplet package.
- *What does UCIe standardize that Infinity Fabric does not?* Interoperability: a layered PHY/adapter/protocol contract and flit formats aligned with PCIe/CXL, so dies from different vendors can share a package - at some bandwidth-density cost versus a bespoke coherent fabric.
- *Why does 3D change the cache conversation?* 2.5D seams carry ~GB/s-per-mm at tens-to-hundreds of ns; hybrid-bonded 3D seams move data at um pitch and low ns, making it plausible to place slices of L3 across stacked dies rather than only streaming traffic across them.

## Pitfalls the white papers skip

- **Thermal coupling in 3D.** Stacked dies share a vertical thermal path: a hot top die throttles the base die beneath it, so power maps must be co-designed, not assembled.
- **Test and debug do not compose.** JTAG/scan across a dozen dies from three vendors, with UCIe links between them, is an open systems problem; a package that passes per-die test can still fail as a system.
- **Profile mismatch is the new ABI break.** UCIe interoperability requires matching protocol profiles and parameters; "UCIe-compliant" dies that implement different profiles still cannot talk - same lesson as "USB-C is not one cable."
- **Coherence across the seam is the expensive part.** Cheap D2D links move raw bytes; snoop filters, ordering, and memory-encryption engines (AMD's SMEE over fabric, CXL memory security) are where designs bog down.
- **Binary dies, binary packages.** Assembly yield on a 12-CCD server package means binning charts that look like silicon lottery but are really packaging economics.
- **Seam bandwidth is not pooled bandwidth.** Each D2D edge has a fixed budget; a topology that funnels four CCDs through two fabric crossings has a bottleneck no aggregate-spec sheet will reveal.

## References

- UCIe Consortium - specifications page (UCIe 1.0/2.0/3.0, packaging classes, bump pitches) - <https://www.uciexpress.org/specifications>
- "An Introduction to the Universal Chiplet Interconnect Express" (ACM survey of the UCIe spec family) - <https://dl.acm.org/doi/10.1145/3819235>
- TSMC 3DFabric - CoWoS family page - <https://3dfabric.tsmc.com/english/dedicatedFoundry/technology/cowos.htm>
- AMD EPYC 9004 series (Zen 4 CCD/IOD chiplet architecture) - <https://www.amd.com/en/products/processors/server/epyc/9004-series.html>
- Apple Newsroom: Apple unveils M1 Ultra (UltraFusion 2.5 TB/s) - <https://www.apple.com/newsroom/2022/03/apple-unveils-m1-ultra-the-worlds-most-powerful-chip-for-a-personal-computer>
