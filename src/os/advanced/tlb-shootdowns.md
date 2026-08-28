# TLB Shootdowns: The Multiprocessor Protocol Behind Every munmap

`munmap()` has a deceptively small contract: when it returns, no CPU in the
system may still translate addresses in the unmapped range. On a
multiprocessor, honoring that contract is a distributed agreement problem.
Each core owns a private, cached view of the page tables -- its TLB -- and
there is no hardware mechanism that invalidates another core's entries
(until very recently, see *Broadcast Invalidation* below). The kernel must
therefore *ask* every CPU that might hold a stale translation to discard
it, synchronously, before the pages it guards can be repurposed. That ask
is the TLB shootdown: inter-processor interrupts (IPIs), rendezvous
semantics, generation counters, and a surprising amount of bookkeeping --
all so that page-table writes can become visible.

This page is the multiprocessor protocol story. The single-CPU story --
TLB structure, entries, hit-rate math, ASID basics -- lives in
[TLB](../memory/tlb.md); page-table mechanics in
[Page Tables](../memory/page-tables.md); the syscall surface in
[mmap](../memory/mmap.md) and [mmap Internals](../../linux/kernel/memory/mmap.md).

## Why Unmapping Needs Interrupts at All

Consider two threads on different cores. Thread A calls `munmap(addr)`;
thread B is about to read `addr`. The kernel's invariant is: **after the
unmapping syscall returns, no subsequent access on any CPU faults on the
old mapping's stale entry -- or rather, any access must see the new
state**. Translations cached in B's TLB before the unmap are exactly the
stale entries that violate this, and B's core has no idea they aged.

The classic two-phase protocol falls out:

```text
   unmapper (CPU 0)                     victims (CPUs 1..n)
   ----------------                     -------------------
   1. write PTEs: clear/replace
      entries for the range
      (holds page-table lock)
   2. ensure memory ordering            3. IPI arrives; handler runs
      (smp_mb before the IPI)              with interrupts disabled:
   4. send IPI to every CPU                - drain any pagetable writes
      that may have the mm                 - invalidate stale TLB entries
      loaded (mm_cpumask)                  - ack and return
   5. wait for all acks                 6. only now: free pages /
      before freeing pages                 page-table pages may be reused
```

Two ordering facts make this correct rather than merely polite. First, the
unmapper's PTE writes must be globally visible *before* the IPI fires, or
a victim could invalidate, return, and re-walk the old PTE. Second, the
free must wait for the *last* ack: the moment a page is returned to the
allocator and reused, a stale translation is not just wrong but
dangerous -- writing through it corrupts someone else's memory. The
mmu_gather code states the rule plainly in its header comment: never free
a page before ensuring there are no live TLB entries for it.

ASIDs/PCIDs sharpen the problem. With tagged TLB entries
([PCID](../memory/tlb.md) on x86, ASID on ARM/RISC-V), a CPU caches
translations from *several* address spaces simultaneously, so "which CPUs
must be interrupted" is not simply "who runs this process": kernel-side
translations and other contexts can be affected by full-flush operations,
and per-context flushing must key on the right PCID. PCID also changes the
*cost model*: because a context switch no longer flushes, translations
survive longer, shootdowns are relatively more frequent, and the flush
itself can be made precise (per-PCID `INVPCID` instead of a global CR3
write).

## The Unmapper's Half: mmu_gather Batching

The kernel does not unmap and flush page by page. `unmap_region()` and its
siblings wrap the work in an **mmu_gather** (`struct mmu_gather`,
`tlb_gather_mmu()` ... `tlb_finish_mmu()`), which reorders the naive loop
into three phases across the whole (or per-VMA) range:

```text
phase 1  GATHER  walk PTEs: zap entries, queue pages and page-table
                 pages on per-CPU batch lists (do NOT free yet)
phase 2  FLUSH   one TLB invalidation for the accumulated range
                 (range-encoded; skips nothing-was-unmapped VMAs)
phase 3  FREE    now release batched pages to the allocator and
                 page-table pages to their RCU/batch queues
```

The batching amortizes the most expensive part -- the shootdown -- across
an entire munmap or madvise: one flush covers a range that touched
thousands of PTEs, and `tlb_remove_table()` queues page-table pages so
they are freed only after the flush (and, on some architectures, after an
RCU grace period protects lockless page-table walkers, including the
gUP fast path). Batches have a bounded size (`MAX_GATHER_BATCH_COUNT`);
when the queue fills mid-range, an intermediate `tlb_flush_mmu()` drains
it -- a multi-megabyte munmap still issues a handful of flushes, not
thousands. The user-visible consequence: `munmap` cost is dominated by
one shootdown per call (or per batch), which is why churning many *small*
mappings is far worse than churning few large ones.

## The Victim's Half: tlb_gen, Queues, and What "Done" Means

x86's `arch/x86/mm/tlb.c` implements the victim side with a **generation
counter per address space** (`mm->context.tlb_gen`, an atomic64) and a
per-CPU copy of the last generation that CPU's PCID has loaded
(`cpu_tlbstate.ctxs[asid].tlb_gen`). The flush protocol becomes
compare-and-flush rather than blind invalidate:

- The unmapper bumps `tlb_gen` and calls `flush_tlb_mm_range()`, which
  builds a `flush_tlb_info` (range, freed-tables flag) and targets
  `mm_cpumask(mm)` -- the set of CPUs that have run this mm.
- `native_flush_tlb_multi()` sends the IPIs and, since the concurrent
  flush rework (Amit's series merged in 2021), flushes the *local* TLB
  concurrently with the remote ones instead of locally first, then
  waiting.
- On each victim, `flush_tlb_func()` compares its stored generation
  against the mm's: **three** generations are involved (`mm_tlb_gen`, the
  victim's `local_tlb_gen`, and `next_tlb_gen`), and a victim whose
  `local_tlb_gen` is already current does nothing. Coalescing for free:
  ten flush requests that arrived while the victim was busy collapse into
  one increment.
- Range flushes issue `INVLCID`/`INVLPG` per page; large ranges or
  `freed_tables` switch to a full `CR3`/`INVPCID` rewrite, which is
  cheaper than many single-address invalidations.

`mm_cpumask` itself is managed lazily and *trimmed*: a CPU is added when
it loads the mm, and `should_trim_cpumask()` prunes CPUs that have since
switched away (on a roughly once-per-second cadence), because the mask
only ever says "may still have translations".

```text
   CPU0 (unmapper)                CPU1 (active)         CPU2 (lazy idle)
   tlb_gen: 41 -> 42
   flush_tlb_mm_range
     info = {start,end,freed=0}
     __flush_tlb_multi(mm_cpumask) --> IPI --> flush_tlb_func():
                                              local_tlb_gen 41 < 42
                                              -> INVLPG range, set 42
                concurrently: local flush on CPU0
                    |                                   (lazy CPU2:
                    v                                    should_flush_tlb()
   return to caller                                       returns false --
   only after all acks                                    flushed at its
                                                          next switch)
```

The **lazy TLB** optimization is visible in `should_flush_tlb()`: a CPU
running a kernel thread that has *borrowed* the previous process's
mm (`is_lazy`) is skipped entirely -- it holds no user translations it is
using, and its TLB state will be re-validated by the generation compare at
its next context switch. This is why an idle or kernel-thread-dominated
machine shoots down cheaply while a busy multithreaded process pays full
freight.

## The IPI Storm: Anatomy of a multithreaded munmap

Put the halves together and the failure mode of, say, a JVM heap
shrink, an allocator trimming arenas, or a database dropping a buffer
pool becomes predictable. One thread unmaps; every other thread of the
process is a victim; each victim stalls in an interrupt handler with
interrupts disabled while it walks an INVLPG loop. Worse:

- **Syscall-rate storms**: many small `munmap`/`madvise(MADV_DONTNEED)`
  calls each pay their own shootdown round. Throughput collapses from
  page-count-bound to IPI-round-bound.
- **Virtualization amplification**: on a hypervisor, each IPI is a VM
  exit or an emulated interrupt; measured IPI latencies in cloud VMs run
  an order of magnitude above bare metal (Amit and Tai quantify this --
  their EuroSys 2020 measurements put shootdown overheads at double-digit
  percentages of unmap-heavy workloads in virtualized environments).
- **NUMA skew**: victims on remote sockets see longer interrupt delivery
  and colder page-table pages, so the ack wait stretches to the slowest
  node -- a tail effect, not an average one (see
  [NUMA](../memory/numa.md)).

The kernel's own counter-pressure: `flush_tlb_mm_range` heuristics
trade range precision for a single full flush when the mask is wide,
mmu_gather merges adjacent zaps, and the (relatively recent) **global
ASID / broadcast invalidation** path (`mm_active_cpus_exceeds()` in
tlb.c) assigns wide-running processes a global ASID so invalidation
becomes a hardware broadcast instead of an IPI fan-out -- the AMD
broadcast-invalidation feature landing across x86 trees. LWN's 2025
coverage tracks both that and the **LUF (lazy unmap flush)** proposal,
which defers unmap-time flushes to allocation time: pages are handed to
the allocator still translated, and the *next* mapper absorbs the
invalidation, converting N shootdowns into roughly N flush-when-reused
events with allocator-side batching.

## userfaultfd Interplay

Userfaultfd reshapes where page-table state changes happen, and not always
for the better. The missing-page mode is shootdown-free by construction:
`UFFDIO_COPY`/`UFFDIO_ZEROPAGE` install PTEs that never existed, so no
stale translations exist anywhere. But **uffd-wp** (write-protect mode)
clears write bits on *present* PTEs to trap writes -- which is a
modification of live translations and requires the same IPI flush
protocol as an unmap. Memory-management-heavy users of userfaultfd
(live migration, post-copy, checkpoint/restore in the CRIU tradition)
therefore alternate between "free" install faults and "expensive"
write-protect rounds; batching write-protect operations and scoping them
to VMA-sized ranges matters as much as batching munmaps (see
[userfaultfd](../../linux/kernel/memory/userfaultfd.md) and the
checkpoint/restore page [CRIU](criu-checkpoint-restore.md)).

## Worked Simulation: Shootdown Cost Model

The model below prices the strategies on one munmap of P pages against a
process active on A of C CPUs (bare-metal IPI round-trip `IPI_US`,
per-page victim invalidation `INVLPG_US`, full-flush rewrite `CR3_US`;
the VM column multiplies only the IPI term, modeling hypervisor-emulated
interrupt delivery):

```python
IPI_US = 2.0     # bare-metal IPI round-trip (initiator -> victim -> ack)
INVLPG_US = 0.1  # per-page INVLPG on a victim
CR3_US = 0.5     # full CR3/INVPCID rewrite on a victim
VM_MULT = 12     # hypervisor amplification of IPI round-trips

def shootdown(pages, active, strategy, lazy_idle=0):
    victims = max(active - 1 - lazy_idle, 1)  # unmapper is one of the active
    if strategy == "per_page":            # naive: one IPI per page
        rounds, victim_us = pages, pages * INVLPG_US
    elif strategy == "range_batch":       # mmu_gather: 1 round, range
        rounds, victim_us = 1, pages * INVLPG_US
    elif strategy == "full_mm":           # wide mask: one round, CR3 rewrite
        rounds, victim_us = 1, CR3_US
    elif strategy == "lazy_tlb":          # range_batch, idle cores skipped
        rounds, victim_us = 1, pages * INVLPG_US
    elif strategy == "broadcast":         # global-ASID hardware broadcast
        rounds, victim_us = 0, pages * INVLPG_US
    bare = rounds * victims * IPI_US + victim_us
    vm = rounds * victims * IPI_US * VM_MULT + victim_us
    return rounds * victims, bare, vm

P, ACTIVE = 512, 9
rows = [
    ("per-page IPIs (no batching)", "per_page", 0),
    ("mmu_gather range batch",      "range_batch", 0),
    ("full-mm CR3 rewrite",         "full_mm", 0),
    ("range batch + lazy TLB skip", "lazy_tlb", 3),
    ("global-ASID broadcast",       "broadcast", 0),
]
print(f"{'strategy':30s} {'IPIs':>6s} {'us (bare)':>10s} {'us (VM)':>10s}")
for name, strat, lazy in rows:
    n, bare, vm = shootdown(P, ACTIVE, strat, lazy)
    print(f"{name:30s} {n:6d} {bare:10.1f} {vm:10.1f}")
```

Output (Python 3.12):

```text
strategy                         IPIs  us (bare)    us (VM)
per-page IPIs (no batching)      4096     8243.2    98355.2
mmu_gather range batch              8       67.2      243.2
full-mm CR3 rewrite                 8       16.5      192.5
range batch + lazy TLB skip         5       61.2      171.2
global-ASID broadcast               0       51.2       51.2
```

Reading it: unbatched per-page invalidation is two orders of magnitude
worse than anything else -- the IPI count (4096 = 512 pages x 8 receiving
CPUs, the unmapper excluded) dominates everything, and virtualization
amplifies exactly that term into ~98 ms of pure interrupt traffic. The
mmu_gather row shows batching removing 511 of 512 IPI rounds while keeping
the victim's INVLPG loop; the full-mm row shows why the kernel *abandons*
range precision when the mask is wide -- a single 0.5 us rewrite per
victim beats 51.2 us of per-page invalidation. Lazy-TLB skipping and
broadcast invalidation then attack the remaining terms (receivers and
round-trips, respectively); the VM column for broadcast is deliberately
unchanged because the invalidation no longer crosses the guest/hypervisor
boundary as per-CPU IPIs.

## Mitigations Checklist

- Batch at the syscall level: prefer one large `madvise(MADV_DONTNEED)` or
  `MADV_FREE` over per-object unmapping; arena allocators that munmap per
  free are shootdown generators.
- Size-addressed `MAP_HUGETLB`/[huge pages](../memory/huge-pages.md):
  one INVLPG per 2 MiB instead of per 4 KiB, fewer PTEs to zap.
- Keep the working set of *frequently-remapped* memory on few CPUs --
  `mm_cpumask` breadth is the multiplier (NUMA pinning helps; see
  [scheduler internals](scheduler-internals.md) for placement).
- Watch `tlb:` tracepoints (`tlb_flush` event class) and perf's
  `itlb`/`dtlb` miss deltas around unmap-heavy phases; in guests, compare
  IPI latency (`ipi_irq_lat` style metrics) against bare metal.
- In guests, coalesced paravirtual TLB flushes and fewer, larger
  unmaps beat everything per-page -- the VM row above is the budget.

## References

- [Kernel documentation: page tables and TLB](https://docs.kernel.org/mm/page_tables.html) -- the abstractions mmu_gather maintains
- [torvalds/linux `arch/x86/mm/tlb.c`](https://github.com/torvalds/linux/blob/master/arch/x86/mm/tlb.c) -- tlb_gen, flush_tlb_multi, should_flush_tlb, global-ASID selection (primary source, file cited at master)
- Nadav Amit, "Optimizing the TLB Shootdown Algorithm with Page Access Tracking", USENIX ATC 2017 -- [presentation page](https://www.usenix.org/conference/atc17/technical-sessions/presentation/amit)
- Amit, Tai and Wei, "Don't Shoot Down TLB Shootdowns!", EuroSys 2020, [DOI 10.1145/3342195.3387518](https://doi.org/10.1145/3342195.3387518)
- [LWN, "x86/tlb: Concurrent TLB flushes" (Amit patch series, 2021)](https://lwn.net/Articles/847043/)
- [LWN, "LUF (Lazy Unmap Flush): reducing tlb numbers over 90%" (2025)](https://lwn.net/Articles/973209/)
