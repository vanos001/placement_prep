# Memory Internals

This section covers the production Linux memory subsystem beyond the [basics of page tables](../memory/page-tables.md), [paging](../memory/paging.md), and [huge pages](../memory/huge-pages.md). We examine the mechanisms that keep systems running under memory pressure: page cache internals, memory compaction, Transparent Huge Pages (THP), KPTI, PSI, OOM killing, zswap/zram, DAMON, NUMA migration, and per-CPU allocators.

## KPTI — Kernel Page Table Isolation

KPTI (Kernel Page-Table Isolation, Linux 4.15, 2018) was introduced to mitigate the **Meltdown** CPU vulnerability (CVE-2017-5754). Meltdown allowed user-space processes to read kernel memory through speculative execution of privileged memory accesses that faulted but leaked data via side channels.

KPTI works by maintaining **two separate sets of page tables** per process:

1. **Kernel page tables**: Full kernel mapping (all of kernel text, data, and direct-mapped physical memory). Used when executing in kernel mode.
2. **User page tables**: Only the minimal kernel mappings needed for syscall entry/exit (the trampoline, interrupt stubs, and signal delivery). The rest of the kernel address space is unmapped (not present in the page tables).

```
User mode (Ring 3):
  - Uses USER page tables
  - Kernel space almost entirely unmapped
  - Speculative reads into kernel space → page fault (no data leak)

System call entry:
  - Trampoline switches to KERNEL page tables
  - CR3 reload (TLB flush!)
  - Execute syscall in full kernel mapping

Return to user:
  - Switch back to USER page tables
  - CR3 reload (TLB flush!)
```

The cost: every syscall and interrupt now requires **two CR3 switches** (entry and return), each flushing the non-global TLB entries. On a system doing 1M syscalls/sec, this adds ~2M TLB flushes. Linux mitigates the TLB impact by marking the kernel trampoline pages as **global** (PCD bit set, not flushed by CR3 reload) and using `PCID` (Process-Context Identifiers) to avoid full TLB flushes — PCID allows the TLB to tag entries with a process ID, so switching CR3 only invalidates entries for the previous PCID.

## ASLR Internals

Address Space Layout Randomization places key memory regions at randomized offsets at process load time. Linux implements ASLR for five regions: stack, heap, `mmap` base, executable base (PIE), and `vDSO`. Each region's base address is shifted by a random offset within a configurable range (`/proc/sys/kernel/randomize_va_space`).

```bash
cat /proc/self/maps | head -20
# Each run of a PIE binary loads at a different address
# 55a1b2c34000-55a1b2c35000 r--p ... /usr/bin/ls  (randomized)
# 7f8a12345000-7f8a12346000 r--p ... libc.so.6    (randomized mmap)
# 7ffc12a34000-7ffc12a36000 rw-p ... [stack]       (randomized)
```

ASLR entropy is limited by the address space layout. On 64-bit Linux, PIE gets ~28-30 bits of entropy (TB-range randomization), but the stack and heap get less due to alignment requirements and the address space hole between user and kernel. The kernel randomizes once at `execve` time — there is no runtime re-randomization. KASLR randomizes the kernel text base at boot, providing ~30 bits of entropy on x86-64.

## Transparent Huge Pages (THP)

[Regular huge pages](../memory/huge-pages.md) require explicit `mmap` with `MAP_HUGETLB` or `shmget` with `SHM_HUGETLB`. **THP** (Transparent Huge Pages, Linux 2.6.38) automatically promotes frequently-used 4 KB pages into 2 MB huge pages without application changes.

THP operates through **khugepaged**, a kernel thread that periodically scans process page tables for contiguous runs of 4 KB pages that are:
- All present (not swapped out)
- All in the same NUMA node
- Not shared (refcount == 1)
- Not `mprotect`'d with different permissions
- Backed by the same anonymous or file-backed region

When such a run is found, `khugepaged` allocates a 2 MB huge page, copies the data, and atomically swaps the page table entries. The benefit: one TLB entry covers 2 MB instead of 512 entries for 4 KB pages, dramatically reducing TLB misses for large working sets (databases, JVM heaps, large graph structures).

```bash
# Check THP status
cat /sys/kernel/mm/transparent_hugepage/enabled
# Output: always [madvise] never

# Recommended for most servers: madvise (opt-in per-app via MADV_HUGEPAGE)
# Some databases (Redis, PostgreSQL) benefit from always

# THP statistics
cat /proc/meminfo | grep -i huge
# AnonHugePages:    1048576 kB   ← THP pages in use
```

THP can cause **latency spikes**: the page table collapse (`collapse_huge_page`) holds the mmap_lock for write and does a 2 MB copy. This can stall other threads accessing the same mm. The `madvise` mode (default in most distros) avoids this by only collapsing pages in regions where the application explicitly requests it (`MADV_HUGEPAGE`). `defrag` options control whether THP will trigger memory compaction to find a 2 MB contiguous block.

## Memory Compaction

The Linux buddy allocator allocates contiguous physical pages. Over time, external fragmentation scatters free pages throughout the physical address space. Even if 100 MB of memory is free, it might be in thousands of non-contiguous 4 KB chunks, preventing 2 MB huge page allocation.

Memory compaction reorganizes physical memory to create large contiguous free blocks. The algorithm has two phases:

1. **Isolation**: Migratable pages are identified and their migration types are recorded. Non-migratable pages (kernel text, mlock'd, pinned DMA) are skipped — they form "unmovable" obstacles.

2. **Migration**: Movable pages are copied to free pages at the low end of a compaction region, freeing up contiguous space at the high end. Page table entries are updated to point to the new physical addresses.

```
Before compaction:
[Free][Used][Free][Free][Used][Free][Used][Free][Free][Free]

After compaction:
[Free][Free][Free][Free][Free][Free][Used][Used][Used]
                                          ^^^^^^^^^^^^^^
                                          3 contiguous free pages
```

Compaction is triggered by: THP allocation failures (most common), `mlock` of large regions, CMA (Contiguous Memory Allocator) for DMA, and `echo 1 > /proc/sys/vm/compact_memory`. The cost is CPU-intensive page copying and TLB invalidation. On a system with 64 GB of RAM, full compaction can take seconds and cause significant latency spikes.

## Page Cache

The page cache is the kernel's in-memory cache of file data. Every `read()` and `write()` for buffered I/O goes through the page cache. Pages are identified by `(inode, offset)` — the **address space** (`address_space` struct) associated with each inode provides the page cache management.

```c
struct address_space {
    struct radix_tree_root i_pages;  // maps page offset → struct page
    // ... (replaced by xarray in modern kernels)
    unsigned long nrpages;           // number of cached pages
    // ...
};
```

Read path: `read()` → VFS → filesystem → `generic_file_buffered_read()` → looks up page in `i_pages` xarray. If found (cache hit), copies to userspace. If not (cache miss), submits a block I/O read, waits, then copies.

Write path: `write()` → VFS → filesystem → copies data into page cache pages (marks them dirty) → returns to userspace. The actual disk write happens later, asynchronously, by:
1. **pdflush/flush workers**: Kernel threads that periodically write back dirty pages (`writeback`)
2. **`sync()` / `fsync()`**: Synchronous flush requested by the application
3. **Memory pressure**: The page reclaim path writes dirty pages before evicting them

**Dirty page limits**: `/proc/sys/vm/dirty_ratio` (percentage of total memory that can be dirty, default 20%) and `dirty_background_ratio` (10%) control when writeback is triggered. If dirty pages exceed `dirty_ratio`, the writing process blocks until writeback catches up. This is critical for database write-ahead logs — if the writeback thread can't keep up, the application stalls.

## Memory Reclaim

When free memory falls below a threshold (`watermark`), the kernel's **kswapd** daemon reclaims pages. The reclaim path in `vmscan.c` operates on **LRU lists** (Least Recently Used), split into two types:

- **Anonymous LRU**: Pages backed by `malloc`/`mmap(ANONYMOUS)`. Can only be reclaimed by swapping (if swap is enabled) or discarding (if MADV_FREE).
- **File LRU**: Pages from the page cache. Can be reclaimed simply by dropping them (the data is on disk, can be re-read). File LRU is split into **active** and **inactive** lists to protect frequently-accessed pages.

```
Reclaim decision:
  Page on File Inactive LRU?
    YES → clean: evict immediately (free!)
         → dirty: write back, then evict
  Page on Anon LRU?
    YES → swap enabled: write to swap, evict
         → no swap: cannot reclaim (pinned in memory)
```

**Direct reclaim** occurs when an allocation (even with `__GFP_DIRECT_RECLAIM`) fails and the calling context is in the page allocator. The allocating thread itself performs reclaim (walks the LRU, evicts pages) and retries. This is more urgent than kswapd and can stall the allocating thread for milliseconds.

## Per-CPU Allocators

The Linux `percpu` allocator provides per-CPU copies of data structures to avoid cache-line bouncing and lock contention. Each CPU has its own private copy of the data, accessed without any synchronization.

```c
// Kernel per-CPU variable
DEFINE_PER_CPU(struct statistics, stats);

// Access (no lock needed!)
struct statistics *s = this_cpu_ptr(&stats);
s->count++;  // only this CPU touches this copy
```

The allocator manages a set of per-CPU memory regions. On x86-64, per-CPU memory is allocated in the first 2 TB of the kernel virtual address space, with a per-CPU offset applied. The `percpu` allocator supports both statically-allocated (`DEFINE_PER_CPU`) and dynamically-allocated (`alloc_percpu()`) per-CPU variables, as well as per-CPU reference counting (`percpu_ref`) for scalable resource tracking.

Per-CPU variables are used for: scheduler statistics, VM event counters, networking statistics (`per-CPU packet counters`), RCU per-CPU data, and the slab allocator's per-CPU partial slabs.

## Memory Cgroups

Memory cgroups (part of [cgroups v2](../containers/cgroups.md)) limit and account for memory usage per cgroup. When a cgroup exceeds its `memory.max` limit, the kernel triggers reclaim on that cgroup's pages only — not globally. This enables multi-tenant isolation: one cgroup's memory pressure doesn't evict another cgroup's page cache.

```bash
# Set 1 GB memory limit for a cgroup
echo 1G > /sys/fs/cgroup/myapp/memory.max

# Current usage
cat /sys/fs/cgroup/myapp/memory.current

# Swap limit (v2)
echo 512M > /sys/fs/cgroup/myapp/memory.swap.max
```

Memory cgroups add overhead: every `struct page` gains a pointer to its owning cgroup (`page->mem_cgroup`), and every page allocation/inc/dec involves atomic operations on the cgroup's counter. On systems with millions of cgroups (Kubernetes pods), this atomic contention on shared counters can be measurable (~2-5% overhead). The kernel mitigates this with **per-CPU batched counter updates** (`percpu_counter`): each CPU batches counter updates locally and periodically flushes to the global counter.

## PSI — Pressure Stall Information

PSI (Linux 5.2+) provides fine-grained metrics on resource contention by measuring the **wall-clock time** processes spend waiting for CPU, memory, or I/O. Unlike traditional load averages (which conflate everything), PSI distinguishes the type of stall.

```bash
cat /proc/pressure/memory
# some avg10=0.00 avg60=0.00 avg300=0.00 total=0
# full avg10=0.00 avg60=0.00 avg300=0.00 total=0

# some = at least one task waiting (partial stall, some work proceeding)
# full  = ALL tasks waiting (no work proceeding — severe pressure)
```

PSI works by tracking time in the scheduler where no runnable tasks exist on a CPU (memory stall) or all runnable tasks are in D-state waiting for I/O. The `psi` infrastructure integrates with the page allocator (memory pressure detection), the block layer (I/O pressure), and the scheduler (CPU pressure). Kubernetes uses PSI for its `Vertical Pod Autoscaler` and OOM score calculations.

## OOM Killer

When the kernel cannot reclaim enough memory to satisfy an allocation, the **Out-of-Memory (OOM) killer** selects a process to terminate, freeing its memory. The selection uses an **OOM score** (`/proc/<pid>/oom_score`) based on:

- Memory usage (RSS, swap, page tables, file mappings)
- OOM score adjustment (`/proc/<pid>/oom_score_adj`, range -1000 to +1000)
- Whether the process is privileged (root processes get lower scores)
- Whether the process has been running for a long time

```bash
# Mark a critical process as OOM-immune
echo -1000 > /proc/$(pidof myapp)/oom_score_adj

# The kernel will kill other processes first
```

The `oom_kill_process()` function in `mm/oom_kill.c` walks all processes, computes scores, and kills the highest-scoring one. `panic_on_oom=1` causes a kernel panic instead of killing a process (used in embedded/hardened systems). The OOM killer is controversial: it makes an irreversible decision based on heuristics. Better approaches (PSI-driven throttling, memory cgroup limits) are preferred in well-designed systems.

## NUMA Migration

On NUMA systems, a task's pages may be spread across multiple memory nodes. The kernel's **automatic NUMA balancing** (`numa_balancing`) migrates pages to the node where the task most frequently accesses them. This is driven by the **NUMA fault** mechanism:

1. Pages are initially allocated on the task's home node (determined by `cpuset`/`numactl`).
2. The kernel periodically **unmaps** a subset of the task's pages (protection fault injection).
3. When the task accesses an unmapped page, a NUMA fault is recorded — the kernel notes which CPU/node the fault occurred on.
4. After enough samples, the kernel estimates the task's preferred node and migrates its pages there.

This is enabled by default (`numa_balancing=true` in sysfs). The cost: periodic page unmapping causes spurious page faults (protection faults, ~100 ns each). For latency-sensitive workloads, disable it with `numactl --interleave=all` or `echo 0 > /proc/sys/kernel/numa_balancing`.

## DAMON — Data Access Monitor

DAMON (Linux 5.15+) is a kernel subsystem that monitors the access patterns of user-space processes at fine granularity without requiring code changes. It works by periodically:

1. Splitting the target region into fixed-size regions (default 4 KB, configurable)
2. Installing PTE access-bit monitoring (or using hardware PMU sampling)
3. Aggregating access frequency per region

```
DAMON access heatmap for a 1 GB heap:
Region     Access Freq    Action
0x000-0x040    0/interval  (cold → candidate for swap)
0x040-0x080  100/interval  (hot → keep in memory, maybe THP)
0x080-0x100   50/interval  (warm → monitor)
...
```

DAMON drives **proactive reclaim** (PR): it can be configured to automatically cold-page-evict regions that haven't been accessed recently, reducing memory pressure before it becomes critical. This is used by Meta and Google for large fleet memory management. DAMON also supports **huge-page application** (identifying hot regions and applying THP or explicit huge pages) and **NUMA-aware placement**.

## zswap and zram — Compressed Swap

### zswap

zswap is a **compressed cache for swap pages** in main memory. When a page is swapped out, instead of writing it to disk immediately, zswap compresses it and keeps it in a per-CPU compressed memory pool (using zstd, lz4, or zbud). Only when the compressed pool is full does the page get written to the actual swap device.

```
Swap path with zswap:
1. Page selected for swap
2. zswap compresses page (2-10x compression ratio)
3. Store compressed page in RAM (zswap pool)
4. If pool full → write to swap device (disk)

Swap-in path:
1. Check if page is in zswap pool
2. YES → decompress in RAM (fast, ~µs)
3. NO → read from swap device (slow, ~ms)
```

zswap is particularly effective for: idle application memory (Java heap with many cold objects), systems without swap devices (containers), and memory-overcommitted cloud VMs. Enable with `zswap.enabled=1` on the kernel command line (default on many distros).

### zram

zram creates a **compressed RAM block device** that acts as a swap device entirely within RAM. Unlike zswap (a cache in front of swap), zram *is* the swap device.

```bash
# Create a 4 GB compressed swap in RAM (uses ~1-2 GB actual memory)
modprobe zram
zramctl --find --size 4G
echo lz4 > /sys/block/zram0/comp_algorithm
mkswap /dev/zram0
swapon /dev/zram0 -prio 100  # higher priority than disk swap
```

zram is used by default in Android (as compressed swap for low-memory devices) and Chrome OS. The compression ratio depends on the data: typically 2-3x for general workloads, up to 10x for highly compressible data (zeroed pages, repeated patterns). The trade-off: compression/decompression uses CPU cycles (~1-5 µs per 4 KB page), but this is far cheaper than disk I/O (~5-10 ms per page).

## Interview Questions

1. **"What is KPTI and why does it impact syscall performance?"** Answer hint: KPTI maintains separate user and kernel page tables. Every syscall entry switches from user to kernel page tables (CR3 reload), and every return switches back. Each CR3 reload flushes non-global TLB entries, causing TLB misses on the first memory access after the switch. PCID mitigates this by tagging TLB entries, but there's still the CR3 write overhead (~100-200 cycles per syscall).

2. **"When would you disable THP?"** Answer hint: When latency spikes from `khugepaged` compaction are unacceptable (real-time workloads, low-latency trading). When the working set is small and doesn't benefit from reduced TLB pressure. When memory fragmentation makes THP promotion fail repeatedly, wasting CPU. Databases like Redis with `save`/`bgsave` may see latency spikes from THP collapse.

3. **"zswap vs zram — which would you choose for a Kubernetes node?"** Answer hint: zswap on a node with a disk swap device — it caches compressed pages in RAM and falls through to disk. zram on a node without disk swap — it provides swap entirely in RAM. For Kubernetes, zswap with a small disk swap partition provides the best safety net: cold pages compress in RAM first, only spilling to disk under severe pressure.

4. **"How does PSI help with OOM management?"** Answer hint: PSI provides early warning of memory pressure before OOM. An application (or orchestrator like Kubernetes) can monitor `memory.full` (time all tasks are stalled on memory) and proactively reduce memory usage — shed load, evict caches, scale down — before the OOM killer triggers. This is far better than reacting to OOM kills.

## References
- Linux source: `mm/vmscan.c`, `mm/compaction.c`, `mm/page-writeback.c`, `mm/zswap.c`, `mm/zram.c`, `mm/damon/`
- Corbet, J. "Kernel address space layout randomization." LWN.net, 2005.
- Corbet, J. "PSI: a framework for real-time pressure stall information." LWN.net, 2018.
- Hwang et al. "DAMON: Data Access Monitor." Linux Plumbers Conference, 2019.
