# hugetlbfs and Huge Pages: TLB Economics in the Kernel

> hugetlbfs is the kernel's oldest huge-page mechanism (2.5.46, 2002 -- a
> decade before THP) and the only one that sells a *contract*: a pool you
> filled yourself, reserved at `mmap()` time, so later faults can never fail
> for lack of memory. THP asks "can I get a huge page right now?"; hugetlbfs
> asks "how many did you promise me?". That contract is this page.

## Why hugetlbfs Survived Its Own Successor

In theory THP makes hugetlbfs obsolete. In practice LWN describes hugetlbfs
as "a sort of second memory-management subsystem" whose unification with the
rest of MM was still being scoped at the 2024 LSFMM+BPF summit (Peter Xu's
session). Two capabilities keep it alive: **reservation** (a reservation made
today is a fault that cannot fail tomorrow, even after memory fragments) and
**page-table sharing** across processes mapping the same hugetlbfs file,
which anonymous THP cannot offer. The price: an explicitly managed pool,
opt-in APIs, traditionally unswappable mappings, and application cooperation.

## Where the Page Size Lives in the Walk

```text
x86-64, 4-level paging: one table page = 512 entries x 8 B = 4 KiB
  PGD -> PUD -> PMD -> PTE      each level translates 9 VA bits
  4 KiB page: leaf at PTE       walk touches all 5 levels on a TLB miss
  2 MiB page: leaf at PMD       PMD entry points straight at the 2 MiB frame
  1 GiB page: leaf at PUD       no PMD/PTE tables exist below the entry
```

Sizes are architecture policy, not constants: x86-64 offers 2 MiB (PMD) and
1 GiB (PUD); arm64 offers 64 KiB/2 MiB/32 MiB/1 GiB with 4 KiB base pages,
2 MiB/32 MiB/1 GiB with 16 KiB, and 2 MiB/512 MiB/16 GiB with 64 KiB
(`arch/x86/mm/hugetlbpage.c`; header comment of `arch/arm64/mm/hugetlbpage.c`).
The odd arm64 mid-sizes are *contiguous* sizes: 16 or 32 adjacent PTE/PMD entries
flagged as one block, cached in a single TLB entry.

## The Pool Is the Contract: Reservation Accounting

| Knob | What it sets |
|---|---|
| `/proc/sys/vm/nr_hugepages` | persistent pool target (default size) |
| `/proc/sys/vm/nr_overcommit_hugepages` | how far the pool may *grow* past the target with surplus pages |
| `/sys/kernel/mm/hugepages/hugepages-<kB>kB/...` | per-size `nr_hugepages`, `nr_overcommit_hugepages`, `nr_hugepages_mempolicy` (NUMA) |
| `hugepagesz=<size> hugepages=<count>` (boot) | pre-fill at boot; `[kKmMgG]` suffixes; `default_hugepagesz=` picks the default |

`/proc/meminfo` exposes the accounting (semantics from the admin guide):

| Field | Meaning |
|---|---|
| `HugePages_Total` | size of the pool |
| `HugePages_Free` | pool pages not yet allocated (reserved ones count here too) |
| `HugePages_Rsvd` | pages with "a commitment to allocate ... made, but no allocation yet" |
| `HugePages_Surp` | pool pages above `nr_hugepages`; capped by `nr_overcommit_hugepages` |
| `Hugepagesize` / `Hugetlb` | default size / total hugetlb KiB |

The admin guide states the guarantee plainly: reserved pages "guarantee that
an application will be able to allocate a huge page from the pool of huge
pages at fault time." `MAP_NORESERVE` (or surplus/overcommit headroom) lets
a mapping skip that commit -- the failure mode that trips everyone: `mmap()`
succeeds, then the process dies with SIGBUS on the first unsatisfiable fault,
including the CoW write fault of a private mapping. Shrinking `nr_hugepages`
below in-use count converts the difference to surplus pages, freed only as
mappings go away.

## Three Doors Into the Pool

1. **hugetlbfs mount** -- `mount -t hugetlbfs -o uid=...,gid=...,mode=...,
   pagesize=...,size=...,min_size=...,nr_inodes=... none /mnt/huge`; "any
   file created on /mnt/huge uses huge pages" (admin guide). Files are
   `ftruncate` + `mmap` + `unlink` only; `read`/`write` unsupported.
2. **`mmap(MAP_HUGETLB)`** -- anonymous; no mount required. Size selection:
   `MAP_HUGE_2MB`/`MAP_HUGE_1GB` (since Linux 3.8) encode `log2(size)` in
   six bits at `MAP_HUGE_SHIFT`; zero selects the default; `MAP_HUGETLB` is
   since 2.6.32; `memfd_create(MFD_HUGETLB)` wraps it for anonymous use.
3. **SysV shared memory** -- `shmget(..., SHM_HUGETLB)`, gated by
   `/proc/sys/vm/hugetlb_shm_group`. PostgreSQL's `huge_pages=on` uses this
   path (its docs' "Linux Huge Pages" section walks pool sizing).

## Shared, Private, and the Price of CoW at 2 MiB

- **`MAP_SHARED`**: all mappers share the same pool page -- and, uniquely,
  hugetlb can share the *page tables* themselves across processes mapping
  the same file. Fewer table pages, fewer TLB fills per context switch.
- **`MAP_PRIVATE`**: first write triggers copy-on-write, and the copy is the
  whole huge page -- a 2 MiB memcpy plus a fresh order-9 allocation *from
  the pool*, not the buddy allocator. Reserved mappings fault in that copy
  at roughly double the demo's per-fault cost; an empty unreserved pool
  turns it into SIGBUS. THP's equivalent quietly falls back to 4 KiB pages;
  hugetlbfs has no fallback -- that is the point.
- **Accounting asymmetry**: a shared pool page is charged once against the
  pool but counted in every mapper's RSS -- the source of "free looks fine
  but my hugepages are gone" tickets. The pool files, not RSS, are truth.

## Filling the Pool: Boot, Runtime, CMA

- **Boot** (`hugepagesz=... hugepages=...`) is the reliable route: it runs
  before memory fragments, so contiguous order-9/order-10 buddy allocations
  succeed. See the [Page Allocator](./page-allocator.md) for order math.
- **Runtime** (`echo N > nr_hugepages`) requests contiguous blocks from a
  possibly-fragmented buddy allocator; on long-lived systems it can fail or
  stall behind compaction. Gigantic pages (1 GiB = order-18) are the worst
  case: `hugetlb_cma=` (`[HW,CMA,EARLY]`; per the kernel parameters doc,
  "The size of a CMA area used for allocation of gigantic hugepages", with a
  `node:nn` per-node format) reserves a CMA region at boot, lent to movable allocations until claimed.
- **Demote**: sysfs `demote`/`demote_size` splits a huge page into smaller
  hugetlb sizes (the admin guide's example: 1 GiB into 2 MiB pages on x86) -- pool flexibility without touching the buddy allocator.

## Tooling and Who Ships on It

`hugeadm` (libhugetlbfs) is the pool's Swiss-army knife: `hugeadm
--pool-list` prints every size's pool state, `hugeadm --pool-pages-min
2MB:10` sets a minimum the tooling keeps topped up. The library itself once
backed the *heap* (`HUGETLB_MORECORE`) and text/data via `LD_PRELOAD` --
mostly historical interest now. Ground truth: `/proc/meminfo`,
`/sys/kernel/mm/hugepages/`, and `HugetlbPages:` in `/proc/<pid>/smaps`.

Adopters: DPDK's Getting Started Guide states "Hugepage
support is required for the large memory pool allocation used for packet
buffers (the HUGETLBFS option must be enabled in the running kernel...)" and
gives the TLB reason directly -- without hugepages, "high TLB miss rates
would occur with the standard 4k page size". DPDK sizes the pool at boot for
the reservation guarantee, then `--huge-dir` maps mempools from hugetlbfs;
the kernel-side sibling is [XDP](../networking/xdp.md). PostgreSQL's
`huge_pages=on` maps postmaster shared memory via `SHM_HUGETLB` -- a size
fixed at startup is the ideal reservation shape. And the THP runbook paradox
-- database guides say "disable THP" (see [Transparent Huge Pages](./thp.md))
while the same deployments enable hugetlbfs -- is not a contradiction:
best-effort off for latency predictability, guaranteed on where it matters.

## The Numbers: Coverage, Page-Table Overhead, Fault Amortization

A calculator under a stated cost model: 1,536 TLB entries; minor fault =
1,000 ns fixed work + zeroing at 10 GiB/s; pool pages (`echo N >
nr_hugepages`) are zeroed at fill time, so pool-backed faults skip zeroing.

```python
#!/usr/bin/env python3
# Model (illustrative): 1,536 TLB entries; fault = 1,000 ns + zeroing at
# 10 GiB/s; pool pages (echo N > nr_hugepages) are zeroed at fill time.
KIB, MIB, GIB = 1 << 10, 1 << 20, 1 << 30
TLB, TENT, TBYTES = 1536, 512, 4096
FAULT_NS, ZERO_BPS = 1_000, 10 * GIB

def human(n):
    for name, div in (("TiB", 1 << 40), ("GiB", 1 << 30),
                      ("MiB", 1 << 20), ("KiB", 1 << 10)):
        if n >= div:
            return f"{f'{n / div:.2f}'.rstrip('0').rstrip('.')} {name}"
    return f"{n} B"

def ptable(mapped, page):
    n, total, span = {4 * KIB: 2, 2 * MIB: 1, 1 * GIB: 0}[page], 0, page
    for _ in range(n):                    # levels dedicated to this mapping
        t = -(-mapped // (span * TENT))   # ceil: tables at this level
        total, span = total + t * TBYTES, span * TENT
    return total

def faults(page, zero):
    n = (1 * GIB) // page
    return n, n * (FAULT_NS + (page / ZERO_BPS * 1e9 if zero else 0))

base = TLB * 4 * KIB
print(f"1) TLB reach with {TLB} entries")
for p in (4 * KIB, 2 * MIB, 1 * GIB):
    print(f"   {human(p):>7} pages: coverage = {human(TLB * p):>7}"
          f"  (x{TLB * p // base:,} the 4 KiB reach)")
print("\n2) dedicated page-table bytes to map 1 GiB")
for p in (4 * KIB, 2 * MIB, 1 * GIB):
    print(f"   {human(p):>7} pages: {ptable(1 * GIB, p):>9,d} B"
          f"  ({human(ptable(1 * GIB, p))})")
print("\n3) first-touch cost of touching 1 GiB")
for p in (4 * KIB, 2 * MIB):
    for label, z in (("zero-at-fault (THP / anonymous)", True),
                     ("pre-zeroed pool  (hugetlbfs)   ", False)):
        n, ns = faults(p, z)
        print(f"   {human(p):>7} {label}: {n:>7,d} faults  {ns / 1e6:>9,.2f} ms")
n4k, t4k = faults(4 * KIB, True); n2m, t2m = faults(2 * MIB, False)
print(f"\n   hugetlbfs 2 MiB vs anonymous 4 KiB: {t4k / t2m:,.0f}x cheaper"
      f" first touch, {n4k // n2m}x fewer faults")
```

Real output of the script above:

```text
1) TLB reach with 1536 entries
     4 KiB pages: coverage =   6 MiB  (x1 the 4 KiB reach)
     2 MiB pages: coverage =   3 GiB  (x512 the 4 KiB reach)
     1 GiB pages: coverage = 1.5 TiB  (x262,144 the 4 KiB reach)

2) dedicated page-table bytes to map 1 GiB
     4 KiB pages: 2,101,248 B  (2 MiB)
     2 MiB pages:     4,096 B  (4 KiB)
     1 GiB pages:         0 B  (0 B)

3) first-touch cost of touching 1 GiB
     4 KiB zero-at-fault (THP / anonymous): 262,144 faults     362.14 ms
     4 KiB pre-zeroed pool  (hugetlbfs)   : 262,144 faults     262.14 ms
     2 MiB zero-at-fault (THP / anonymous):     512 faults     100.51 ms
     2 MiB pre-zeroed pool  (hugetlbfs)   :     512 faults       0.51 ms

   hugetlbfs 2 MiB vs anonymous 4 KiB: 707x cheaper first touch, 512x fewer faults
```

Reading it: the coverage multiples (512x, 262,144x) are the headline, but
the fault rows carry the interview nuance. Zeroing 2 MiB at fault time costs
real microseconds, so demand-allocated huge pages beat 4 KiB by only ~3.6x
in this model -- while **pool-backed** pages fault in ~700x cheaper because
the zeroing was paid once at `nr_hugepages` time: reservation economics.

## Interview Questions

1. `mmap(MAP_HUGETLB)` succeeded but the process took SIGBUS on first touch.
   What happened? (No reservation was committed -- overcommit headroom or
   `MAP_NORESERVE`; `HugePages_Free` includes unreserved pages.)
2. Is `HugePages_Rsvd` a subset of `HugePages_Free`? (Yes -- reserved pages
   are unallocated pool pages that already carry a commitment.)
3. Why can CoW on a private hugetlb mapping SIGBUS while THP CoW cannot?
   (THP falls back to 4 KiB pages; hugetlbfs must find another pool page --
   there is no smaller fallback inside the contract.)
4. Why do DPDK setup scripts pre-reserve hugepages at boot rather than rely
   on THP? (Guaranteed, pinned, unswappable, 2 MiB-aligned DMA buffers; no
   compaction stalls; THP is best-effort and can split.)
5. What does hugetlb give a shared mapping that THP never can? (Shared page
   tables across processes -- one PMD-level table serving many mappers,
   saving memory and per-context TLB fills.)

## References

- Kernel admin guide, *hugetlbpage* (sysctls, meminfo semantics, mount options, demote): https://docs.kernel.org/admin-guide/mm/hugetlbpage.html (probed 200)
- `mmap(2)` man page (MAP_HUGETLB since 2.6.32; MAP_HUGE_* since 3.8): https://man7.org/linux/man-pages/man2/mmap.2.html (probed 200)
- libhugetlbfs project + HOWTO (hugeadm): https://github.com/libhugetlbfs/libhugetlbfs (probed 200)
- Kernel admin guide, *kernel parameters* (`hugetlb_cma=`, `hugepagesz=`): https://docs.kernel.org/admin-guide/kernel-parameters.html (probed 200)
- Kernel admin guide, *Transparent Hugepages*: https://docs.kernel.org/admin-guide/mm/transhuge.html (probed 200)
- LWN, *Toward the unification of hugetlbfs* (Corbet, May 22 2024 -- 2.5.46 origin, reservation, page-table sharing, LSFMM 2024): https://lwn.net/Articles/974491/ (probed 200)
- DPDK Getting Started Guide, *Use of Hugepages in the Linux Environment*: https://doc.dpdk.org/guides/linux_gsg/sys_reqs.html (probed 200)
- PostgreSQL docs, *Kernel Resources -- Linux Huge Pages*: https://www.postgresql.org/docs/current/kernel-resources.html (probed 200)

## Cross-References

- [Transparent Huge Pages](./thp.md) -- khugepaged, defrag stalls, mTHP, hugetlbfs-vs-THP table.
- [Page Allocator (Buddy System)](./page-allocator.md) -- where order-9/10/18 pool-fill allocations come from.
- [XDP: eXpress Data Path](../networking/xdp.md) -- kernel-side cousin of DPDK's pinned buffers.
- [mmap (Memory-Mapped Files)](../../../os/memory/mmap.md) -- the syscall surface MAP_HUGETLB extends.
