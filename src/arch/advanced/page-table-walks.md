# Page-Table Walks: What the MMU Does When the TLB Misses

When the TLB cannot answer a translation, the MMU executes a *page walk* — a
fixed sequence of dependent memory reads through a radix tree in RAM. This page
treats the walk as a cost object: how many memory references it issues, how
those references multiply under nested virtualization, how long the resulting
TLB entries live, and what invalidating them costs. Data-structure fundamentals
live in [multi-level page tables](../../os/memory/multi-level-page-tables.md),
[page tables](../../os/memory/page-tables.md), and
[the TLB page](../../os/memory/tlb.md); here we count references.

## The walk loop, level by level

On x86-64 the walker is driven by CR3 (page-table base) plus index fields sliced
out of the linear address. Each level reads one 8-byte table entry; the low bit
(P) says whether the next read even happens. With 4 KiB pages the 4-level split is:

```text
        4-level (LA48, 4 KiB page)                5-level (LA57, 4 KiB page)
63         47 46      39 38  30 29  21 20  12 11       0
+-----------+----------+-----+-----+-----+-----+----------+
| sign (16b)| PML4 idx |PDPT | PD  | PT  |  offset (12b)  |
+-----------+----------+-----+-----+-----+-----+----------+
      |            |        |     |     |          |
      v            v        v     v     v          v
     CR3-->PML4-->PML4E-->PDPTE-->PDE-->PTE--> physical page

63         56 55      48 47  39 38  30 29  21 20  12 11      0
+-----------+----------+-----+-----+-----+-----+-----+---------+
| sign (8b) | PML5 idx |PML4 |PDPT | PD  | PT  |  offset (12b) |
+-----------+----------+-----+-----+-----+-----+-----+---------+
                   |        |     |     |     |         |
                   v        v     v     v     v         v
             CR3-->PML5-->PML4E-->PDPTE-->PDE-->PTE--> page
```

A canonical 48-bit address wastes bits 63:47 as sign copies; LA57 opens bits
47:56, giving 128 PiB of linear space, at the price of one more dependent read
per walk. Linux enables 5-level paging only when the CPU and firmware report
support and falls back to LA48 otherwise; the [kernel's x86_64 memory-layout
documentation](https://docs.kernel.org/arch/x86/x86_64/mm.html) shows the
resulting VA split and the `CONFIG_X86_5LEVEL` build-time switch.

The per-level register chain and its exit conditions:

| Level | Table read | Entry holds | Walk ends here when |
|-------|-----------|-------------|---------------------|
| 1 | PML4E (or PML5E first on LA57) | base of next table + perms | never (no PS bit at this level) |
| 2 | PDPTE | base of PD, or 1 GiB frame if PS=1 | PS=1 -> 1 GiB page |
| 3 | PDE | base of PT, or 2 MiB frame if PS=1 | PS=1 -> 2 MiB page |
| 4 | PTE | 4 KiB frame + perms | always (leaf) |

Two details of the loop matter for performance engineering more than the
bit-split does:

1. **The reads are dependent**, not parallel — level *n+1* needs the physical
   address from level *n*. A walk cannot be pipelined; each read pays full
   memory latency (or L2/L3, depending on where the page tables landed).
2. **Walks can write memory.** Setting accessed/dirty bits on the PTE is a
   read-modify-write by the walker itself; a store miss to a clean page
   dirties the PTE, and on multi-socket systems that write crosses the
   coherence fabric.

## Huge pages as walk-depth compression

A PS (page size) bit at level *n* makes that entry a leaf and deletes all
deeper reads from the walk. This is the second, less-advertised benefit of
huge pages: beyond TLB-reach, they shorten every miss.

| Mapping | Leaf entry | Walk reads (TLB miss) | Reach per entry |
|---------|-----------|----------------------|-----------------|
| 4 KiB | PTE | 4 | 4 KiB |
| 2 MiB | PDE (PS=1) | 3 | 2 MiB |
| 1 GiB | PDPTE (PS=1) | 2 | 1 GiB |
| 5-level 4 KiB | PTE | 5 | 4 KiB |

Huge-page *support* (backing memory with 2 MiB / 1 GiB frames, THP vs explicit
hugetlbfs) is covered in [Linux huge pages](../../linux/kernel/memory/huge-pages.md)
and the [hugetlbpage admin guide](https://docs.kernel.org/admin-guide/mm/hugetlbpage.html).
The walker's view is simpler: a miss costs `levels_to_leaf + 1` references —
the model below makes that trade explicit.

## Counting references: the miss-cost model

Let `v` be the TLB miss rate per data access and `L` the walk depth. A TLB hit
costs 1 reference (the data itself); a miss costs `L` walk reads + 1 data read.
Expected references per access: `(1-v)·1 + v·(L+1)`.

```python
"""Walk-depth miss-cost model: expected memory references per data access.

Counts raw memory-system references, not cycles: a TLB hit costs 1 read (the
data access itself); a TLB miss first performs an L-level walk (L reads, one
per page-table level), then the data read. Under EPT/NPT every guest-visible
read (each page-table read and the data read) is itself translated by a host
walk, so a cold host TLB turns 1 guest read into L_host + 1 host reads.

Pure-stdlib, deterministic model; numbers are reference counts, not timings.
"""
from collections import namedtuple

Scenario = namedtuple("Scenario", "name depth")

# depth = levels walked for a 4 KiB leaf unless the page size collapses levels
SCENARIOS = [
    Scenario("bare 4-level, 4 KiB pages", 4),
    Scenario("bare 4-level, 2 MiB page", 3),   # PS=1 in PDE: PT read skipped
    Scenario("bare 4-level, 1 GiB page", 2),   # PS=1 in PDPTE: PD+PT skipped
    Scenario("bare 5-level, 4 KiB pages", 5),
]


def expected_refs_bare(depth, v):
    """E[refs] = hit branch + miss branch (v = TLB miss probability)."""
    return (1 - v) * 1 + v * (depth + 1)


def expected_refs_nested(guest_depth, host_depth, v, ept_miss):
    """Every guest read costs c host references; c depends on EPT TLB hit."""
    c = (1 - ept_miss) * 1 + ept_miss * (host_depth + 1)  # host cost per read
    return (1 - v) * c + v * (guest_depth + 1) * c


def main():
    base = expected_refs_bare(4, 0.01)
    print("Expected memory references per data access (TLB miss rate v)")
    print(f"{'scenario':<28} {'walk':>4} {'v=1%':>7} {'v=5%':>7} {'cold':>5}")
    for s in SCENARIOS:
        e1 = expected_refs_bare(s.depth, 0.01)
        e5 = expected_refs_bare(s.depth, 0.05)
        print(f"{s.name:<28} {s.depth:>4} {e1:>7.3f} {e5:>7.3f} {s.depth + 1:>5}")
    print()
    # Nested: guest TLB miss rate v=1%, EPT TLB miss rate 0.5% per host read
    n1 = expected_refs_nested(4, 4, 0.01, 0.005)
    n5 = expected_refs_nested(4, 4, 0.05, 0.005)
    print(f"EPT/NPT guest 4-level, host 4-level")
    print(f"  per-guest-read host cost c = 0.995*1 + 0.005*(4+1) = {0.995 + 0.005*5:.3f}")
    print(f"  v=1%: {n1:.4f}   v=5%: {n5:.4f}")
    print(f"  amplification vs bare 4-level @1%: {n1 / base:.3f}x")
    print()
    print("Worst case, everything cold:")
    print(f"  bare 4-level: 4 walk + 1 data = 5 refs")
    print(f"  EPT-nested:   4*5 guest-walk + 5 data = {4*5 + 5} refs total")
    print(f"                (24 translation refs + 1 data read)")


if __name__ == "__main__":
    main()
```

```text
Expected memory references per data access (TLB miss rate v)
scenario                     walk    v=1%    v=5%  cold
bare 4-level, 4 KiB pages       4   1.040   1.200     5
bare 4-level, 2 MiB page        3   1.030   1.150     4
bare 4-level, 1 GiB page        2   1.020   1.100     3
bare 5-level, 4 KiB pages       5   1.050   1.250     6

EPT/NPT guest 4-level, host 4-level
  per-guest-read host cost c = 0.995*1 + 0.005*(4+1) = 1.020
  v=1%: 1.0608   v=5%: 1.2240
  amplification vs bare 4-level @1%: 1.020x

Worst case, everything cold:
  bare 4-level: 4 walk + 1 data = 5 refs
  EPT-nested:   4*5 guest-walk + 5 data = 25 refs total
                (24 translation refs + 1 data read)
```

Two readings of this table. In the *steady state* (warm TLBs) the depth
differences are noise — which is why 5-level paging costs almost nothing when
adopted. The *cold* column is where depth hurts: start-up, context switches
without PCID, page-fault storms, and every EPT miss in a nested walk.

## Two-dimensional walks: EPT and NPT

With hardware virtualization the guest owns CR3 and thinks it owns CR3's target.
The host owns a second radix tree — Intel's EPT (Extended Page Tables, SDM
Vol. 3, Ch. 28), AMD's NPT (Nested Page Tables, APM Vol. 2, Ch. 5). Every
memory reference the guest issues — including the reads made by its own page
walker — is itself an address that must be translated guest-physical to
host-physical:

```text
 guest linear address
        |
        v   guest walk (4 dependent reads)
 guest physical address (GPA)
        |                     each of the 5 guest reads
        v                     (4 walk reads + 1 data read)
 host EPT/NPT walk (4 dependent reads)   <--- multiplied by host depth
        |
        v
 host physical address (HPA)
```

Before EPT/NPT, hypervisors used *shadow page tables*: the host built a fused
guest-linear-to-host-physical tree and kept it coherent with the guest's CR3
by trapping all guest writes to page-table pages (see
[hypervisors](../../cloud/virtualization/hypervisors.md)). The fused tree made
misses cheap (one flat walk) but coherence expensive and complex. EPT/NPT
invert the trade: coherence is free (the guest edits its own tables; nothing is cached
except TLB entries), but every TLB miss can cost up to **24 translation
references** (4 guest reads x 5 host refs each + 4 EPT refs for the data read).
[Agile Paging (ISCA 2016)](https://doi.org/10.1109/ISCA.2016.67) analyzes this
balance and shows hybrid schemes (fusing levels, caching intermediate
translations) recovering most of the gap. Real processors add exactly such
caches: page-walk caches and combined EPT caches that memoize upper levels.

The two vendors differ at the fault path, and this is what makes nested-walk
misses disproportionately painful:

| Property | Intel EPT | AMD NPT |
|----------|-----------|---------|
| Fault on host walk miss | EPT violation (or EPT misconfig) | Nested Page Fault (#NPF) |
| Fault injected to guest? | Only if the *guest* PTEs lack rights; host-miss faults go to the hypervisor | Same split, via #NPF error code |
| Walk state on exit | Guest walk restarts after fix | AMD can resume the interrupted walk |
| Information leak to guest scheduler | Exits are visible timing events | Same (#NPF) |

An EPT violation is not a page fault the guest can handle — it is a VM-exit.
Every guest TLB miss whose host translation is not cached can therefore become
a thousands-of-cycles exit instead of a hundreds-of-cycles walk. This is why
EPT-violation storms (huge sparse guest memory, ballooning, live-migration
remapping) show up as 10-50x slowdowns rather than the ~2% the steady-state
model suggests, and why the [KVM page](../../linux/virtualization/kvm.md)
treats huge-page-backed guest memory as a first-line optimization. Each extra
translation dimension also compounds with [page-table isolation](../../linux/performance/page-table-isolation.md)
overheads on the same CPUs.

## TLB entry lifetimes and PCID/ASID tag caching

A TLB entry lives until one of five events removes it:

| Event | Scope | Notes |
|-------|-------|-------|
| Capacity/associativity eviction | one entry | normal cache behavior |
| `INVLPG m` | one page, one CPU | the per-page invalidation primitive |
| `MOV CR3` (no PCID) | all non-global entries, one CPU | context switch = full flush |
| `MOV CR3` with PCID (bit 63 clear) | only entries with that PCID | selective flush |
| `INVPCID` type 0-3 | per-PCID or all, one CPU | kernel-managed range ops |
| Global-page bit (PGE) | survives CR3 writes | kernel-mapped entries only |

PCID (x86) and ASID (ARM/RISC-V) tag each entry with a 12-bit (x86) address-space
identifier, so a context switch that writes CR3 to a *new* PCID leaves other
address spaces' entries intact — the flush-on-switch penalty becomes a
PCID-recycling problem instead. [The TLB page](../../os/memory/tlb.md) covers
the entry format and reach math; the subtlety here is the interaction with
walk cost: without PCID, every context switch resets the miss rate to ~100%
for the first touches of the new address space, so the *effective* miss rate
is a weighted mix of steady-state and post-switch cold misses. With PCID the
cold-miss spike survives only across PCID recycling (12 bits = 8192 address
spaces before reuse).

Kernel page-table isolation (PTI) multiplies this: user/kernel split doubles
the CR3-write count per syscall crossing, which is precisely why PTI's
overhead collapsed on PCID-capable CPUs — CR3 switches between user and kernel
PCIDs keep both TLB halves warm.

## invlpg, shootdowns, and the invalidation decision tree

`INVLPG` acts on one CPU. The moment a page is unmapped while other CPUs may
hold TLB entries for it, the kernel must reach every CPU that ever walked that
mapping — an IPI-based *TLB shootdown* (send interrupt, each target flushes,
then acknowledges; the sender cannot free the page until all acks arrive).
The invalidation decision tree a kernel walks through:

```text
unmap/change a mapping
        |
        v
 can a remote CPU hold an entry?
    |-- no  --> local INVLPG only (or defer: lazy TLB, mmu_gather batching)
    |-- yes --> is the mm multi-threaded / remote-referenced?
                |-- no  --> local flush suffices
                |-- yes --> IPI shootdown: mask = mm_cpumask
                            cost = latency of slowest target CPU + queueing
```

Shootdown storms (fork-heavy workloads, mprotect-heavy JITs, NUMA migration)
are therefore not page-table problems but *interrupt-latency* problems — the
walk is cheap compared to the IPI round trip, and batching invalidations
(mmu_gather) exists purely to amortize the shootdown against many unmapped
pages. On virtualized guests each such IPI can additionally cost a VM-exit,
so paravirtual TLB flushes (KVM_PV_TLB_FLUSH hint) replace IPI storms with
hypercalls.

## Cost-accounting drills

Drill-style questions this page is built to answer precisely — the numbers come
straight from the model above, and they are the ones interviewers probe:

| Question | Answer from the model |
|----------|----------------------|
| References for a 4 KiB TLB miss, bare metal? | 4 walk reads + 1 data read = 5 |
| Same, but 2 MiB page? | 3 + 1 = 4 (PS=1 at the PDE) |
| Worst case per guest data access under EPT? | 24 translation refs (+1 data) = 25 |
| Why can a walk *write* memory? | Walker sets accessed/dirty PTE bits (RMW) |
| Why did LA57 barely move benchmarks? | v=1%: 1.050 vs 1.040 refs — +1% steady state |
| What keeps EPT misses off the exit path? | EPT TLB caching + page-walk caches (keep `e` small) |
| Why is PTI cheap on PCID CPUs? | User/kernel CR3 switches reuse tagged entries |

The general lesson: walk depth is a *tail* cost, not an average cost.
Steady-state benchmarks over resident memory hide every effect this page
models; the effects appear on start-up, fork/exit, migration, ballooning, and
cold caches — the tails.

## References

- [Intel 64 and IA-32 Architectures SDM, Vol. 3: System Programming Guide](https://cdrdv2-public.intel.com/812391/325384-sdm-vol-3abcd.pdf) — Ch. 4 "Paging" (walk mechanics, PS bit, PCID/INVPCID) and Ch. 28 "VMX Support for Address Translation" (EPT). (Landing page intel.com/sdm is bot-blocked; PDF curl-verified.)
- [AMD64 Architecture Programmer's Manual, Vol. 2: System Programming](https://docs.amd.com/v/u/en-US/24593_3.45_APM_Vol2) — Ch. 5 "Nested Paging and Nested TLB". (curl-verified)
- [Linux kernel: x86_64 memory layout](https://docs.kernel.org/arch/x86/x86_64/mm.html) — 4-level vs 5-level VA split, `CONFIG_X86_5LEVEL`. (curl-verified)
- [Linux kernel: hugetlbpage administration](https://docs.kernel.org/admin-guide/mm/hugetlbpage.html) — huge-page sizing and management. (curl-verified)
- Panagiotis et al., *Agile Paging: Exceeding the Best of Nested and Shadow Paging*, ISCA 2016, [DOI 10.1109/ISCA.2016.67](https://doi.org/10.1109/ISCA.2016.67). (DOI metadata crossref-verified)
