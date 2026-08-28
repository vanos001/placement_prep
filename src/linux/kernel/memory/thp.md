# Transparent Huge Pages: Reach, Collapse, and the Cost of Ambition

> A 4 KiB page is a 40-year-old decision that modern workloads outgrew:
> an x86-64 CPU with 1,536 TLB entries covers just 6 MiB of address
> space at 4 KiB granularity — one or two decode-heavy loops are enough
> to start thrashing. Huge pages multiply that coverage by 512 (2 MiB)
> or 4,096 (1 GiB). Transparent Huge Pages (THP) is the kernel's answer
> for getting that coverage *without* application changes, and it is
> the most fought-over sysctl in the kernel's history. This page covers
> the mechanics (allocation, khugepaged, defrag) and the tradeoff that
> made database vendors ship "disable THP" runbooks.

## The TLB Arithmetic That Motivates Everything

```text
 TLB coverage = entries x page size

 4 KiB pages:  1,536 x 4 KiB   =      6 MiB
 2 MiB pages:  1,536 x 2 MiB   =  3,072 MiB
 1 GiB pages:  1,536 x 1 GiB   =   ~1.5 TiB (with 4-level paging)

 page-table walk depth at 4 KiB: 5 levels (PGD..PTE), 5 memory refs
                                 on a TLB miss (worst case)
 at 2 MiB:                       4 levels (PMD entry points at the
                                 physical frame directly)
```

One 2 MiB mapping replaces 512 PTEs with a single PMD entry: fewer TLB
misses (coverage) and shallower walks (miss cost). The demo at the end
puts numbers on a realistic working-set sweep.

## What THP Does

THP makes the kernel allocate huge pages *automatically* for
anonymous memory (and, with filesystem THP, for page-cache pages):

- On a fault in a 2 MiB-aligned range that is fully populated (or
  during `mmap` when the whole range is known), the kernel tries a
  huge-page allocation directly.
- For memory that started as 4 KiB pages, **khugepaged** scans for
  fully-populated 2 MiB ranges ("collapse") — it walks the rmap,
  locks the range, allocates a huge page, copies the data, and
  replaces the PTEs, all under the mmap lock. `collapse_pte_mappings`
  is the expensive part: it takes the rmap locks of every 4 KiB page
  involved.

Tunables (`/sys/kernel/mm/transparent_hugepage/enabled`):

| Mode | Behavior |
|---|---|
| `always` | THP attempted for every eligible anonymous mapping |
| `madvise` | only `MADV_HUGEPAGE`-marked regions |
| `never` | off (but khugepaged may still run for mmap-marked legacy regions — check the file) |

`defrag` controls what an allocation does when the buddy allocator
cannot supply a 2 MiB contiguous block: `direct` (compact synchronously
— the source of the infamous 100ms+ stalls), `defer` (kick kcompactd,
fall back to 4 KiB), `defer+madvise`, `always` — the ordering tradeoff
is allocation success rate vs fault latency.

## The Case Against `always`: The Vendor Runbooks

MongoDB and Redis shipped documentation recommending `never` — the
reasons, in order of impact:

1. **Direct-compaction stalls**: an `always` THP fault that triggers
   synchronous compaction can block for tens of milliseconds — an
   eternity for a p99. `defer` modes fix most of it; `never` fixes it
   absolutely.
2. **Memory bloat**: a 2 MiB page backing a sparse region wastes the
   tail. A heap that grows by 4 KiB deltas under `always` THP can
   double its RSS; under memory pressure, reclaim work grows with the
   wasted share.
3. **Compaction/fragmentation pressure**: THP churn makes long-running
   systems harder to allocate from for *other* subsystems.

The counter-case: workloads with dense, large working sets (HPC, ML
tensor arenas, big hash tables) measure 5-30% throughput wins. Hence
`madvise` as the compromise, and hence **mTHP** (multi-size THP, in
mainline since 6.8) — per-order tunables letting 64 KiB/128 KiB.../1 GiB
folios be enabled independently, with the kernel filling large folios
at page-fault time for regular files too. mTHP reframes the debate:
"THP or not" becomes "which sizes, for which mappings, faulted in how".

## hugetlbfs vs THP

| | hugetlbfs | THP |
|---|---|---|
| Allocation | pre-reserved pool (`/proc/sys/vm/nr_hugepages`) | on-demand from buddy + compaction |
| API | `mmap(MAP_HUGETLB)` / hugetlbfs mount | transparent (or MADV_HUGEPAGE) |
| Guarantees | reserved: no runtime failure | best-effort: can fall back to 4 KiB |
| Swap | traditionally not swappable (varies by flags) | swappable as split 4 KiB pages |
| Used by | DPDK, Oracle, Kafka JVM tuning guides | everyone's anonymous heap |

Pre-reservation is why DPDK's setup scripts allocate hugepages at boot:
a reserved pool cannot fail later and never compacts.

## Worked Demo: TLB Miss Cost vs Page Size

The demo sweeps a working set over simulated TLB capacities and page
sizes using a deterministic locality trace and a stated cost model
(TLB hit = 1 cycle; miss + walk = 60 cycles at 4 KiB, 50 at 2 MiB —
one level shallower).

```python
# TLB-coverage cost model across page sizes (stated assumptions,
# deterministic sweep of a sequential + hot-region workload).

TLB_ENTRIES = 1536
MISS_4K, MISS_2M = 60, 50
HIT = 1

def sweep(ws_bytes, page_size, miss):
    pages = max(1, ws_bytes // page_size)
    tlbed = min(pages, TLB_ENTRIES)
    # sequential pass: each page touched once -> 1 miss + (page_size/64) hits
    lines_per_page = page_size // 64
    miss_cycles = pages * miss
    hit_cycles = (pages * lines_per_page - pages) * HIT
    return (miss_cycles + hit_cycles) / 1e6   # Mcycles

print(f"{'working set':>14} {'4 KiB':>10} {'2 MiB':>10}")
for ws in (64 << 20, 256 << 20, 1 << 30):      # 64 MiB, 256 MiB, 1 GiB
    a = sweep(ws, 4096, MISS_4K)
    b = sweep(ws, 2 << 20, MISS_2M)
    print(f"{ws >> 20:>10} MiB {a:>10.2f} {b:>10.2f}  (Mcycles)")

# coverage cliff: where does 4 KiB TLB coverage end?
cov = TLB_ENTRIES * 4096 / (1 << 20)
print(f"\n4 KiB TLB coverage = {cov:.0f} MiB; 2 MiB coverage = "
      f"{TLB_ENTRIES * (2 << 20) / (1 << 30):.0f} GiB")
```

Real output:

```text
   working set      4 KiB      2 MiB
        64 MiB       2.02       1.05  (Mcycles)
       256 MiB       8.06       4.20  (Mcycles)
      1024 MiB      32.24      16.80  (Mcycles)

4 KiB TLB coverage = 6 MiB; 2 MiB coverage = 3 GiB
```

In this model the 2 MiB row wins by ~2x across the sweep — even a
*sequential* pass pays one TLB miss per page, and the 4 KiB row has
512x more pages to miss on while its per-page hit savings cannot
compensate. The coverage-cliff effect is far more dramatic still for
random access (the sweep above doesn't model it): once the working set
exceeds the 6 MiB 4-KiB coverage, every random touch misses, while the
2 MiB row stays covered out to 3 GiB. That asymmetry — modest wins for
streaming, order-of-magnitude wins for pointer-chasing workloads — is
why benchmarking on your own access pattern is the only defensible
position.

## Interview Questions

1. Why can khugepaged collapse only *fully populated* 2 MiB ranges?
   (A huge PTE has no per-4KiB present bits; partial residency would
   need split pages back — collapse of sparse ranges is the swap-in
   path's job.)
2. What is the direct-compaction stall, and which defrag mode
   eliminates it? (Synchronous memory compaction inside the fault;
   `defer`/`defer+madvise`.)
3. How does mTHP change the THP debate? (Per-size granularity: enable
   64 KiB folios for the heap without 2 MiB bloat — smaller granularity
   captures most TLB wins at far less waste.)
4. Why does DPDK pre-reserve hugetlbfs pages instead of using THP?
   (Guaranteed, unswappable, non-fragmenting memory for DMA pools; THP
   is best-effort and can split under pressure.)
5. A database's runbook says set THP to never. What two measurements
   would you run before blindly following it? (Latency histogram under
   `always` vs `defer+madvise` — looking for compaction stalls; and
   RSS bloat delta under your actual working set.)

## References

- Kernel admin guide, *Transparent Hugepages*:
  https://docs.kernel.org/admin-guide/mm/transhuge.html (probed 200)
- Kernel admin guide, *hugetlbpage*:
  https://docs.kernel.org/admin-guide/mm/hugetlbpage.html (probed 200)
- LWN: Corbet, J. *Multi-size THP* (mTHP coverage):
  https://lwn.net/Articles/937959/ (probed 200)
- Corbet, J. *Huge pages, part 1..5* (background series):
  https://lwn.net/Articles/374424/ (probed 200)
- MongoDB production notes on THP:
  https://www.mongodb.com/docs/manual/tutorial/transparent-huge-pages/
  (probed 200)

## Cross-References

- [NUMA-aware scheduling](../processes/numa-scheduling.md) — huge pages
  also halve NUMA-hint-fault granularity; interplay matters.
- [Memory internals](../../../os/advanced/memory-internals.md) — the
  buddy allocator and compaction engine behind THP allocations.
- [DAX](./dax.md) — the direct-access alternative that skips page
  cache and struct page entirely.
