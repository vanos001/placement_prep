# Persistent Memory: When Storage Became Load/Store

Between 2019 and 2022 it was possible to buy a server DIMM that survived power loss and was addressable with ordinary CPU loads and stores. Intel Optane DC Persistent Memory (PMM) put 128-512 GB of byte-addressable, persistent media on the memory bus, collapsing the classical boundary between "memory" (byte granule, volatile) and "storage" (block granule, durable). The product line is dead -- Intel wound it down in July 2022 -- but the mechanisms it forced engineers to understand (cache flush instructions, persistence domains, torn writes inside a media controller, DAX mappings) remain the reference model for every crash-consistency problem where the persistence boundary is *not* the disk block. This page is about those mechanisms; for a tiering view and the NVM technology landscape see [Tiered & Persistent Storage](../storage/advanced/tiered-persistent.md) and [NVM Technologies](../arch/memory-tech/nvm.md).

## From Battery-Backed DIMMs to 3D XPoint

Persistent DIMMs long predate Optane. The lineage shows the industry solving the same problem -- how to make a DIMM durable -- three different ways:

- **NVDIMM-N** (mid-2010s): DRAM exposed as system memory, with a NAND flash array and a supercapacitor on the module. On power loss the controller drains DRAM into NAND; on reboot software recovers the image. Byte-addressable while powered, but the "persist" event is a bulk copy measured in seconds, and capacity is capped by the DRAM you pay for twice (DRAM + flash + capacitors).
- **NVDIMM-F / -P**: flash-only DIMMs, block-ish, used as fast storage rather than memory. Never mainstream.
- **3D XPoint** (Intel + Micron, announced 2015): a resistive-memory stack (ovonic threshold selector + phase-change storage cells) built in a cross-point array, promising roughly 1000x the endurance and far lower latency than NAND. Intel branded products "Optane"; Micron sold the same media as QuantX and later exited, selling its Lehi fab.
- **Optane DC PMM "Apache Pass"** (April 2019, with 2nd-gen Xeon Scalable "Cascade Lake"): the first mainstream persistent DIMM. 128/256/512 GB modules, up to 3 TB per socket (6 memory channels, 2 PM modules each). The 200-series "Barlow Pass" (2021, Ice Lake-SP) raised module density and added on-module encryption.
- **Wind-down**: Intel announced it was winding down the Optane business in its Q2 2022 earnings (July 28, 2022), taking a $559M impairment.

The important architectural distinction from NVDIMM-N: with Optane there is no bulk-copy persist event. A store that has reached the persistence domain is durable *in place*. The rest of this page is about what "reached the persistence domain" actually means.

## Byte Addressability vs Block Access

| property | DRAM DIMM | Optane DC PMM | NVMe SSD (NAND) |
| -------- | --------- | ------------- | --------------- |
| access instruction | MOV (load/store) | MOV (load/store) | NVMe queue pairs (driver, DMA) |
| access granularity | 64 B cache line | 64 B line, 256 B internal line | 512 B-4 KB logical blocks |
| read latency (app-visible) | ~80-100 ns | ~170-305 ns (measured, idle) | ~50-120 us |
| seq. bandwidth per device | ~100+ GB/s/socket | ~6.6 GiB/s read, ~2.3 GiB/s write per module | 3-14 GB/s |
| endurance | unlimited | ~10^8-10^9 cell writes | ~10^3 program/erase cycles per block |
| survives power loss | no | yes | yes |
| software interface | malloc + pointers | mmap (DAX) or PMDK, or block device | NVMe block I/O, filesystem on top |

The signature trade is latency: Optane sits roughly 2-4x above DRAM on reads (with worse behavior under write mixing and queueing), roughly 1000x below NAND. It is not "slow DRAM" -- its media is asynchronous, row-bufferless, and its bandwidth profile is asymmetric (writes much worse than reads, especially interleaved small writes), which is why the measured characterization matters more than datasheets (Izraelevitz et al. measured ~6.6 GiB/s read and ~2.3 GiB/s write per module, with writes degrading further under contention).

## The Persistence Path

The whole difficulty of PM programming fits in one diagram: the persistence domain ends at the memory controller's write-pending queue (WPQ), not at your store instruction.

```text
         Optane DC PMM (App Direct)                     NAND SSD (for contrast)
 -------------------------------          -----------------------------------------
 CPU core                                  CPU core
   L1 / L2 / L3 caches  <-- NOT durable      L1/L2/L3 (volatile, irrelevant to I/O)
        |                                              |
   CLWB / CLFLUSHOPT + SFENCE                          |
        |                                              v
        v                                        NVMe driver, doorbell write
 iMC write-pending queue (WPQ)  <-- durable            |
        |  (ADR: board power holdup                    v
        |   drains WPQ on power fail)            PCIe -> SSD controller
        v                                              |
 media controller: 256 B XPLine buffers               v
        |                                        NAND die array (block/program ops)
        v
 3D XPoint media  <-- bits are persistent here        durability at ~ms of write ordering
 -------------------------------------------------
 ^ durable region: WPQ -> media (ADR)
 eADR (Ice Lake-SP only): durable region extends up into the CPU caches
```

Two persistence-domain tiers existed, and they changed what correctness requires:

- **ADR** (Asynchronous DRAM Refresh): on power failure, platform power (PSU holdup, board capacitors) gives the iMC time to drain the WPQ to media. Everything you explicitly flushed with CLWB is guaranteed durable. CPU caches are NOT included -- data still dirty in L1/L2 is lost. This is the model virtually all Optane servers ran.
- **eADR** (extended ADR, Ice Lake-SP only): the CPU caches themselves are power-fail protected, so a plain store becomes durable once it reaches the cache, no flush needed. Intel removed eADR support in Sapphire Rapids-SP, so the flush-based discipline returned for newer platforms. Code written against eADR assumptions would silently lose the guarantee on migration.

## Why CPU Caches Break Durability

A store instruction completes (retires) long before its data is durable: the line sits dirty in L1/L2 for up to seconds of cache life. A crash in that window loses the write *even though the application observed it succeed*. PM programming therefore treats persistence as an explicit hardware operation:

| instruction | effect | notes |
| ----------- | ------ | ----- |
| `CLFLUSH` (legacy) | invalidate + write back one line, serialized | slow, orders everything; rarely used |
| `CLFLUSHOPT` | same, but without full serialization | flush other lines concurrently |
| `CLWB` | write back, keep line valid in cache | preferred: read-after-flush stays cheap |
| `SFENCE` | orders all prior flushes/stores | pairs with CLWB: flush, fence, then the "commit" store (e.g., a pointer flip) |
| NT stores (`MOVNT`) | bypass cache, write through toward iMC | help write bandwidth, still need fencing |

The idiom for a durable update is always: write payload -> CLWB payload lines -> SFENCE -> atomically flip a metadata field (8-byte store is atomic within the ADR domain) -> CLWB + SFENCE the metadata. Skipping the fence between payload and metadata lets the media controller reorder, which is how you persist a pointer to bytes that were never written. This is the same discipline as WAL commit ordering, just expressed in single instructions and nanoseconds instead of `fsync` and milliseconds.

## Torn Writes on the 256-Byte XPLine

Optane modules do not write arbitrary bytes to media directly. Writes accumulate in 256-byte internal buffers (XPLine) inside the media path, and the line is what gets programmed. Consequences:

- A power loss while an XPLine is being programmed can leave that 256-byte region torn -- part old bytes, part new. The *guaranteed-atomic unit within ADR is 8 bytes*; between 8 and 256 bytes you have no torn-write protection without doing it yourself (undo/redo logs).
- PMDK's copy loops (`pmem_memcpy_persist`) deliberately copy in 256-byte-aligned, cache-line-granular chunks so a torn XPLine damages at most one aligned region the application's logging already covers.
- Data structures that would be trivially fine on disk blocks -- a 40-byte node straddling two lines -- must assume any field pair within one 256 B region can end up inconsistent after a crash. This is the block-storage "torn sector" problem, rediscovered at a granularity where the application, not a filesystem journal, owns the recovery code.

## DAX: mmap Without the Page Cache

A filesystem with DAX (direct access; `ext4 -o dax`, XFS) skips the page cache entirely: file offsets are mapped by the MMU straight onto media physical addresses.

- `mmap()` on a DAX file gives user space direct load/store access to persistent bytes; a store into the mapping is a media write, no `write()` syscall, no page cache copy, no double caching between PM and DRAM.
- `MAP_SYNC` (Linux 4.15+) contracts with the kernel that the mapping stays valid across restart, so the application can persist its *own* metadata (the pointer flips above) without an `fsync` -- the basis of PM-aware stores that recover in microseconds.
- Namespaces are carved with `ndctl` in two flavors: **fsdax** (filesystem, huge-page-capable mappings) and **devdax** (raw character device of PM pages for PMDK to manage itself).
- Memory Mode (the other option) uses PM as bulk capacity behind a DRAM cache -- near-DRAM performance, no persistence, no special code, at the cost of a mandatory DRAM side. Most "large memory, cheap" deployments ran this mode; most crash-consistency research ran App Direct.

## Interleaving and NUMA Reality

A socket's PM modules are not one flat memory: the iMC interleaves each App Direct region across a channel set (typically 6 channels, 256-byte interleave granularity matching the XPLine) to assemble bandwidth. Three operational consequences:

- **The interleave set is a boot-time contract.** If module population or socket assignment changes, `ndctl` may refuse to assemble the old namespace (label mismatch), and the filesystem simply fails to mount until re-created -- the first "PM disaster" most operators meet is configuration drift, not media failure.
- **Cross-socket PM access costs UPI hops.** A process on socket 0 dereferencing PM mapped from socket 1 pays the same remote-memory penalty as remote DRAM. PM-aware services pin threads and pools to the same NUMA node (`numactl`, PMDK numa-aware allocation) or give up the latency budget.
- **Bandwidth is channel-bound.** The per-module ~6.6 GiB/s read figure multiplies with interleaving (12 modules reach ~50-70 GiB/s aggregate), but a single hot 256-byte-granular structure has no such parallelism -- pointer-chasing workloads see the ugly 300 ns number, not the aggregate.

## Memory Mode in Numbers

Memory Mode paired a small DRAM side (common configurations: 128 GB DRAM with 512 GB PM, i.e., 1:4) with a large PM side. The DRAM acts as a cache for PM lines; PM is invisible to the application except as "a lot of memory":

- Hot sets fitting the DRAM side run at near-DRAM speed; cold or streaming workloads fall through to ~300 ns media with asymmetric write bandwidth.
- No persistence, no CLWB discipline, no PMDK -- an application recompile is not needed, which is exactly why this mode carried most volume.
- The failure mode is capacity planning: a working set that overflows the DRAM cache by 2x can run several times slower than either pure DRAM or a properly architected App Direct deployment, and cache behavior shifts with data churn, making it hard to reason about in SLOs.

## Programming Model: libpmemobj

PMDK's `libpmemobj` is the fullest expression of the model: a transactional persistent heap where pointers are pool-relative offsets, because virtual addresses change between runs.

```c
TOID(struct list_node) head;          /* typed OID: pool offset, stable across restarts */

/* atomic insertion with undo logging: crash mid-transaction -> rolled back */
TX_BEGIN(pop) {
    TOID(struct list_node) n = TX_ALLOC(struct list_node, sizeof(struct list_node));
    D_RW(n)->next = D_RO(head);       /* modify a private copy first */
    TX_SET(n, next, D_RO(head));
    TX_SET(head, next_off, ...);      /* single 8 B commit step, last */
} TX_END
/* pmemobj_tx_commit internally: logged old values -> CLWB -> SFENCE in the right order */
```

What the library owns so you do not have to: allocation metadata persistence, undo/redo logs, flush-and-fence placement, 256-byte torn-write alignment, and type safety across restarts (a struct layout change invalidates old pools loudly). What it costs: an unfamiliar API, per-object overhead, and transactions several times slower than raw flushed stores -- the classic gap between safe and fast persistent code. After the wind-down, PMDK remained usable, with libpmemobj effectively in maintenance mode.

### Crash and Recovery Walk-Through

What actually happens when power dies mid-transaction and the box reboots:

```text
 t0: TX_BEGIN                pool header marks transaction in-flight, undo log allocated
 t1: modify node A           old bytes of A copied to undo log, CLWB + SFENCE
 t2: modify node B           old bytes of B copied to undo log, CLWB + SFENCE
 t3: POWER LOSS              WPQ drains (ADR); anything still in L1/L2 is gone;
                             media holds: header(in-flight) + undo log + partially new A,B
 boot:
   1. pmemobj_open maps the pool, finds "in-flight" transaction marker
   2. replays undo log: restores A and B to their pre-transaction bytes, CLWB + SFENCE
   3. clears the marker; the pool is now at the t0-consistent state
   4. application wakes up inside TX_ONABORT-path semantics, no data lost
```

The recovery cost is proportional to the undo log, not the pool -- a 1 TiB pool with a 4 KiB transaction opens in microseconds. Redo-based designs flip the property (fast commit, lazy apply) the same way WAL and physical-replica logs trade them on block storage.

## PM Failure Modes Checklist

- **CLWB without SFENCE**: flushes are ordered only by the fence; a commit record can reach media before the payload it commits, surfacing months later as "corruption after every crash, never in testing".
- **eADR assumptions on ADR platforms**: code assuming dirty cache lines survive power loss silently loses writes on any Sapphire Rapids or earlier non-Ice host.
- **Mode switch after service**: a DIMM reconfigured from App Direct to Memory Mode (BIOS/`ipmctl`) comes back as a plain volatile device; the old filesystem contents are unreachable until reconfigured back -- and are gone if someone reformats.
- **Interleave-set drift**: swapping one module or moving it to a different socket breaks namespace assembly on next boot; mount failures with label errors, not media errors.
- **Small-granularity churn on one structure**: a hot 64-byte counter hammered by CLWB traffic wears its cells and serializes on the XPLine; PM likes writes spread across the interleave set, not concentrated.
- **Skipping PMEM_ERR checksums on maps**: DAX mappings expose media errors as SIGBUS on access; applications that never handle SIGBUS on their PM mapping crash on the first bad cell, where a block-device stack would have returned EIO and remapped.

## Why Intel Killed Optane

The July 28, 2022 announcement ended the category. The contributing causes were economic and architectural, not a single flaw:

- **Cost per bit never approached DRAM.** The pitch was "cheaper than DRAM capacity"; in practice module prices landed a multiple above DRAM per GB while offering a fraction of its bandwidth, and well above NAND per GB while offering far less density per DIMM slot than big DDR modules.
- **Demand concentration.** Volume hinged on a handful of large customers (SAP HANA being the flagship); the general-purpose market kept buying DRAM + NVMe.
- **The benefit shrank as platforms evolved.** CXL made "more memory capacity per socket" available without a new media type; NAND latency and zoned interfaces (ZNS, FDP) ate the low end of the persistence argument; dropping eADR support signaled where platform investment was going.
- **It required real software work.** Few applications wanted to own crash consistency; the fsync block model, for all its cost, was good enough for most, which kept the addressable market small.

The $559M impairment charge in Q2 2022 is the accounting echo of that gap between technical novelty and replaceable-workload economics.

## What Survived

- **SAP HANA on PMem** is the reference legacy deployment: HANA 2.0 SPS04+ supported Optane PMem in scale-up configurations, cutting restart times (column-store data persisted in PM survives process restart without a DRAM reload) and extending memory capacity per socket. Systems still running it have a real dependency on a discontinued part.
- **The software carries forward.** The Linux DAX stack, MAP_SYNC, ndctl, and PMDK remain; the persistence-instruction discipline (CLWB/SFENCE ordering) is now part of every crash-consistency discussion, including for SSD FTL power-loss design.
- **CXL.memory is the partial successor**: CXL.mem devices give per-socket capacity expansion over a cache-coherent link with latencies below NVMe, and the CXL ecosystem explicitly discusses persistent CXL devices as a future category. What CXL expansion does *not* give you today is the persistence story -- most shipping devices are DRAM-like and volatile, and the ADR/eADR plumbing that made byte persistence platform-defined does not automatically extend across the CXL link.

## Lessons for Storage Design

1. **The persistence boundary is a platform contract, not a library call.** `fsync` hides this; PM made it visible. Any system built on "write then commit marker" logic depends on where the domain ends -- caches, WPQ, or media -- and teams should be able to name that boundary for their stack.
2. **Torn writes exist wherever a buffer sits between the durability contract and the media.** 512 B sectors, 4 KB emulated sectors, 256 B XPLines: the fix is always the same trio -- fixed-size aligned regions, logging, and an 8-byte (or single-sector) atomic commit.
3. **Crash consistency without block semantics is expensive to get right** -- undo logs, fences, and type-safe recovery for every structure. The block+journal model survives because it concentrates that cost in one layer. Any "just make it persistent memory" rewrite inherits the cost in application code.
4. **Latency and bandwidth asymmetry beats averages.** PM's write path was disproportionately worse than its read path; workloads designed around the average (not the ratio) disappointed. The same trap exists on QLC flash and SMR.

## References

- Izraelevitz et al., "Basic Performance Measurements of the Intel Optane DC Persistent Memory Module", 2019 - <https://arxiv.org/abs/1903.05714>
- pmem.io - PMDK (libpmem, libpmemobj) documentation - <https://pmem.io/pmdk/>
- SNIA NVM Programming Model (persistence domains, PM/block programming models) - <https://www.snia.org/tech_activities/standards/curr_standards/npm>
- Intel, "Intel Optane Business Update" (official end-of-sales/warranty position) - <https://www.intel.com/content/www/us/en/support/articles/000091826/memory-and-storage.html>
- Forbes, "Intel Winding Down Its Optane Memory Business", July 28, 2022 - <https://www.forbes.com/sites/tomcoughlin/2022/07/28/intel-winding-down-its-optane-memory-business>
