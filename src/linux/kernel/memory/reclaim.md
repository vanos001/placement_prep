# Page Reclaim

## Overview

Page reclaim is the kernel mechanism that frees physical memory pages when the system runs low on free memory. It decides which pages to evict, writes dirty pages to swap or disk, and returns freed pages to the page allocator. Page reclaim is one of the most complex and performance-critical subsystems in the Linux memory manager.

The reclaim subsystem has two entry points: **kswapd** (background, asynchronous) and **direct reclaim** (synchronous, in the allocating context). Both operate on **LRU (Least Recently Used) lists** to identify pages that haven't been accessed recently.

> **Source:** `mm/vmscan.c` — the core reclaim engine  
> **Key functions:** `kswapd()`, `shrink_node()`, `shrink_lruvec()`, `try_to_free_pages()`

---

## Two Paths to Reclaim

### 1. Background Reclaim (kswapd)

Each NUMA node runs a `kswapd` kernel thread that proactively frees pages when memory drops below the **low watermark**. kswapd runs in the background and doesn't block allocation paths:

```c
/* mm/vmscan.c */
static int kswapd(void *p)
{
    pg_data_t *pgdat = (pg_data_t *)p;
    struct task_struct *tsk = current;

    for (;;) {
        /* Sleep until woken by zone watermark */
        wait_event_freezable(pgdat->kswapd_wait,
                             kswapd_work_requested(pgdat));

        /* Reclaim pages from all zones */
        balance_pgdat(pgdat, order, highest_zoneidx);
    }
}
```

kswapd is woken when:
- A zone's free pages drop below the **low watermark** during allocation
- A cgroup hits its memory limit
- A node needs reclaim for compaction

### 2. Direct Reclaim

When kswapd cannot keep up with allocation demand, the allocating process enters **direct reclaim** and frees pages synchronously. This blocks the caller until enough pages are freed:

```c
/* mm/page_alloc.c */
static struct page *
__alloc_pages_direct_reclaim(gfp_t gfp_mask, unsigned int order,
                             unsigned int alloc_flags,
                             const struct alloc_context *ac,
                             unsigned long *did_some_progress)
{
    struct page *page = NULL;
    unsigned long nr_reclaimed;

    nr_reclaimed = try_to_free_pages(ac->zonelist, order, gfp_mask, ac);
    if (nr_reclaimed) {
        /* Try allocation again after reclaim */
        page = __alloc_pages_slow(gfp_mask, order, alloc_flags, ac);
    }
    return page;
}
```

### Reclaim Path Selection

```mermaid
flowchart TD
    A[Memory allocation request] --> B{Free pages above high watermark?}
    B -->|Yes| C[Direct allocation -- no reclaim]
    B -->|No| D{Free pages above low watermark?}
    D -->|Yes| E[Wake kswapd -- background reclaim]
    D -->|No| F{Free pages above min watermark?}
    F -->|Yes| G[kswapd reclaim + allocation proceeds]
    F -->|No| H[Direct reclaim -- synchronous]
    H --> I{Enough pages freed?}
    I -->|Yes| J[Allocation succeeds]
    I -->|No| K[OOM killer invoked]
```

---

## Watermarks

Each memory zone has three watermarks that control reclaim behavior:

| Watermark | Purpose | Default |
|-----------|---------|---------|
| **min** | Critical threshold — direct reclaim forced | `min_free_kbytes / 4` per zone |
| **low** | kswapd wake-up threshold | `min + min / 4` |
| **high** | kswapd goes back to sleep | `min + min / 2` |

### Watermark Configuration

```bash
# Set minimum free memory (affects all watermarks)
sysctl vm.min_free_kbytes=65536

# Scale watermarks (percentage of zone size * 10000)
sysctl vm.watermark_scale_factor=10   # default: 10 = 0.1%

# Boost watermarks for anti-fragmentation
sysctl vm.watermark_boost_factor=15000  # default: 15000 = 150%

# Check current watermarks
cat /proc/zoneinfo | grep -E "Node|min|low|high"
```

### Watermark Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Alloc as Page Allocator
    participant Kswapd as kswapd
    participant Zone as Zone

    App->>Alloc: alloc_pages(GFP_KERNEL)
    Alloc->>Zone: Check free pages
    Zone-->>Alloc: Free < low watermark
    Alloc->>Kswapd: wake_up(kswapd_wait)
    Alloc->>Alloc: Proceed with allocation (may fail)
    Kswapd->>Zone: balance_pgdat()
    Zone-->>Kswapd: Reclaim until high watermark
    Kswapd->>Kswapd: Sleep (wait_event)
```

---

## LRU Lists

The kernel uses LRU (Least Recently Used) lists to track page age and decide which pages to reclaim first.

### Classic LRU (Two-List)

The classic LRU uses **5 lists** per LRU vector (one per zone or cgroup):

| LRU List | Contents | Reclaim Priority |
|----------|----------|-----------------|
| `LRU_INACTIVE_ANON` | Old anonymous pages | Swap candidates |
| `LRU_ACTIVE_ANON` | Young anonymous pages | Protected |
| `LRU_INACTIVE_FILE` | Old file-backed pages | Reclaim candidates |
| `LRU_ACTIVE_FILE` | Young file-backed pages | Protected |
| `LRU_UNEVICTABLE` | mlocked pages | Never reclaimed |

```c
/* include/linux/mmzone.h */
enum lru_list {
    LRU_INACTIVE_ANON = LRU_BASE,
    LRU_ACTIVE_ANON   = LRU_BASE + LRU_ANON,
    LRU_INACTIVE_FILE  = LRU_BASE + LRU_FILE,
    LRU_ACTIVE_FILE    = LRU_BASE + LRU_FILE + LRU_ANON,
    LRU_UNEVICTABLE,
    NR_LRU_LISTS
};

struct lruvec {
    struct list_head lists[NR_LRU_LISTS];  /* The 5 LRU lists */
    atomic_long_t anon_cost;                /* Anonymous page access cost */
    atomic_long_t file_cost;                /* File page access cost */
    spinlock_t lru_lock;                    /* LRU list lock */
    /* ... */
};
```

### LRU Promotion and Demotion

Pages move between active and inactive lists based on access patterns:

```mermaid
flowchart LR
    ALLOC["New allocation"] --> IL["Inactive List<br>(young, protected)"]
    IL -->|Accessed again| AL["Active List"]
    AL -->|Not accessed for a while| IL
    IL -->|Reclaim scan| FREE["Free page"]
```

- **Promotion**: When a page on the inactive list is accessed (PTE Accessed bit set), it's promoted to the active list.
- **Demotion**: When the active list grows too large relative to the inactive list, pages are moved back to inactive.
- **Reclaim**: Pages at the tail of the inactive list are reclaimed first.

### Multi-Gen LRU (MGLRU, Linux 6.1, 2022)

MGLRU replaces the classic two-list approach with **multiple generations** of pages, providing better age tracking and reducing scanning overhead:

```c
/* include/linux/mmzone.h — MGLRU */
struct lru_gen_folio {
    unsigned long max_seq;           /* Newest generation */
    unsigned long min_seq[ANON_AND_FILE]; /* Oldest generation */
    struct list_head folios[MAX_NR_GENS][ANON_AND_FILE][MAX_NR_ZONES];
    /* ... */
};
```

MGLRU advantages:
- **Better age granularity**: Pages are sorted into multiple generations (typically 4+), not just active/inactive.
- **Reduced scanning**: Only scans pages that changed generation, not entire LRU lists.
- **Better THP handling**: Works at folio granularity, not individual pages.
- **Improved workload-adaptive behavior**: Automatically adjusts to different access patterns.

```bash
# Enable MGLRU (default on in most distros)
echo Y > /sys/kernel/mm/lru_gen/enabled

# MGLRU parameters
cat /sys/kernel/mm/lru_gen/enabled
# 00000000 00000000 00000000 00000001  (bit 0 = MGLRU enabled)

# MGLRU debug stats
cat /sys/kernel/debug/lru_gen
```

---

## What Gets Reclaimed

### File Pages (Page Cache)

File-backed pages (page cache) are reclaimed first because:
- **Clean pages** can be freed immediately (data is on disk)
- **Dirty pages** must be written back first (expensive)
- File pages are often re-accessable from disk

Reclaim order: clean file pages → dirty file pages → anonymous pages

### Anonymous Pages

Anonymous pages have no disk backing store, so they must be **swapped out** before reclaim:
- Requires a swap device to be configured
- Swap-out is expensive (compression + I/O)
- Pages in swap can be swapped back in on demand

### Slab Caches

Kernel slab caches (dentry, inode, etc.) are reclaimed via **shrinkers**:
- Each shrinker provides `count_objects()` and `scan_objects()` callbacks
- Shrinkers are called during reclaim to free kernel objects
- Dentry and inode caches are the most common targets

```c
/* include/linux/shrinker.h */
struct shrinker {
    unsigned long (*count_objects)(struct shrinker *, struct shrink_control *);
    unsigned long (*scan_objects)(struct shrinker *, struct shrink_control *);
    long batch;        /* Objects to free per scan */
    int seeks;         /* Cost of recreating objects */
    /* ... */
};
```

### Swappiness

The `vm.swappiness` sysctl controls the balance between reclaiming file pages vs. anonymous pages:

```bash
# 0 = strongly prefer file page reclaim (avoid swap)
# 100 = equal preference for file and anon
# 200 = strongly prefer anonymous page reclaim (use swap aggressively)
sysctl vm.swappiness=60   # default: 60
```

---

## The Reclaim Algorithm

### shrink_node()

The core reclaim function for a NUMA node:

```c
/* mm/vmscan.c */
static void shrink_node(struct pglist_data *pgdat, struct scan_control *sc)
{
    struct lruvec *lruvec;

    /* Scan each memory cgroup's LRU lists */
    mem_cgroup_iter(NULL, NULL, NULL);
    do {
        lruvec = mem_cgroup_lruvec(sc->target_mem_cgroup, pgdat);
        shrink_lruvec(lruvec, sc);
    } while (mem_cgroup_iter(NULL, sc->target_mem_cgroup, &reclaim));

    /* Also call shrinkers (slab reclaim) */
    shrink_slab(sc);
}
```

### shrink_lruvec()

Scans the inactive LRU list and reclaims pages:

```c
/* mm/vmscan.c */
static void shrink_lruvec(struct lruvec *lruvec, struct scan_control *sc)
{
    unsigned long nr[NR_LRU_LISTS];
    /* ... */
    /* Calculate how many pages to scan from each list */
    get_scan_count(lruvec, sc, nr);

    /* Scan each list */
    for_each_evictable_lru(lru) {
        if (nr[lru]) {
            shrink_list(lru, nr[lru], lruvec, sc);
        }
    }
}
```

### Reclaim Decision Flow

```mermaid
flowchart TD
    A[shrink_node] --> B[Calculate scan targets per LRU]
    B --> C[Scan inactive LRU lists]
    C --> D{Page is mapped?}
    D -->|Yes| E[try_to_unmap -- remove page table entries]
    E --> F{Page dirty?}
    D -->|No| F
    F -->|Yes| G[pageout -- write to swap/disk]
    F -->|No| H[Free page immediately]
    G --> I{Write succeeded?}
    I -->|Yes| H
    I -->|No| J[Keep page on LRU, skip]
    H --> K[Add to free list]
```

---

## OOM Killer

When reclaim fails to free enough memory, the OOM (Out of Memory) killer selects and kills a process to free memory:

### OOM Score

Each process has an OOM score based on its memory usage:

```bash
# Check a process's OOM score (0-1000)
cat /proc/<pid>/oom_score

# Set OOM score adjustment (-1000 to 1000)
echo -500 > /proc/<pid>/oom_score_adj
# -1000 = never kill, 1000 = always kill first
```

### OOM Selection Criteria

The OOM killer selects the process that:
1. Has the highest `oom_score` (proportional to memory usage)
2. Is not in the same cgroup that triggered the OOM (for cgroup OOM)
3. Doesn't have `oom_score_adj = -1000` (OOM-immune)
4. Has the least impact on the system when killed

```bash
# View OOM events
dmesg | grep -i "oom\|killed process"
journalctl -k | grep -i oom
```

---

## Reclaim Behavior Tunables

| Sysctl | Default | Effect |
|--------|---------|--------|
| `vm.swappiness` | 60 | Balance between anon and file reclaim (0-200) |
| `vm.vfs_cache_pressure` | 100 | Shrinker aggressiveness for dentry/inode |
| `vm.min_free_kbytes` | ~65536 | Minimum free memory per zone |
| `vm.watermark_scale_factor` | 10 | Watermark gap as % of zone size |
| `vm.watermark_boost_factor` | 15000 | Anti-fragmentation watermark boost |
| `vm.dirty_ratio` | 20 | Max dirty pages before sync writeback |
| `vm.dirty_background_ratio` | 10 | Max dirty pages before background writeback |
| `vm.zone_reclaim_mode` | 0 | Per-node reclaim policy (0=off) |
| `vm.extfrag_threshold` | 500 | Compaction vs reclaim preference |

---

## Observability

### Monitor Reclaim Activity

```bash
# Reclaim counters from /proc/vmstat
grep -E "pgscan|pgsteal|pgrefill|pgactivate|pgdeactivate" /proc/vmstat
# pgscan_kswapd      12345    — Pages scanned by kswapd
# pgscan_direct      678      — Pages scanned by direct reclaim
# pgsteal_kswapd     12000    — Pages freed by kswapd
# pgsteal_direct     600      — Pages freed by direct reclaim

# Reclaim efficiency = pgsteal / pgscan
# If ratio is low, reclaim is struggling (pages are unevictable)

# OOM statistics
grep oom_kill /proc/vmstat
```

### Trigger Memory Pressure

```bash
# Create memory pressure for testing
# Using stress-ng:
stress-ng --vm 4 --vm-bytes 2G --timeout 60s

# Using memfill (tools/mm):
echo 2G > /sys/fs/cgroup/memory/test/memory.limit
dd if=/dev/zero of=/dev/null bs=1M count=2048

# Using cgroup v2:
echo 2G > /sys/fs/cgroup/test/memory.max
```

### Trace Reclaim Events

```bash
# Enable reclaim tracepoints
echo 1 > /sys/kernel/debug/tracing/events/vmscan/mm_vmscan_lru_isolate/enable
echo 1 > /sys/kernel/debug/tracing/events/vmscan/mm_vmscan_lru_shrink_active/enable
echo 1 > /sys/kernel/debug/tracing/events/vmscan/mm_vmscan_direct_reclaim_begin/enable
echo 1 > /sys/kernel/debug/tracing/events/vmscan/mm_vmscan_direct_reclaim_end/enable

# View traces
cat /sys/kernel/debug/tracing/trace_pipe
```

### Check Zone Pressure

```bash
# PSI memory pressure (Linux 4.20+)
cat /proc/pressure/memory
# some avg10=0.00 avg60=0.00 avg300=0.00 total=0
# full avg10=0.00 avg60=0.00 avg300=0.00 total=0

# Per-cgroup pressure
cat /sys/fs/cgroup/<cgroup>/memory.pressure
```

---

## zswap and zram

### zswap

zswap is a compressed write-back cache for swap. It intercepts pages
being swapped out and stores them compressed in a memory pool. If the
pool fills up, the least recently used pages are written to the actual
swap device.

```bash
# Enable zswap
echo 1 > /sys/module/zswap/parameters/enabled

# Configure zswap
echo z3fold > /sys/module/zswap/parameters/zpool   # Compression allocator
echo lz4hc > /sys/module/zswap/parameters/compressor  # Compression algorithm
echo 20 > /sys/module/zswap/parameters/max_pool_percent  # Max 20% of RAM

# Check zswap statistics
cat /sys/kernel/debug/zswap/
pool_total_size  # Total compressed size
stored_pages     # Number of pages stored
pool_limit_hit   # Times pool was full
reject_compress  # Pages that didn't compress well
reject_reclaim   # Pages evicted from pool
reject_kmemcache # Slab allocation failures
```

```mermaid
flowchart LR
    SWAP["Page to swap out"] --> ZSWAP{"zswap enabled?"}
    ZSWAP -->|Yes| COMP["Compress page"]
    COMP --> POOL{"Pool has space?"}
    POOL -->|Yes| STORE["Store in pool"]
    POOL -->|No| EVICT["Evict LRU to disk"]
    EVICT --> STORE
    ZSWAP -->|No| DISK["Write to swap disk"]
```

### zram

zram creates a compressed block device in RAM, used as swap:

```bash
# Create zram device
modprobe zram num_devices=1

# Configure zram
echo lz4 > /sys/block/zram0/comp_algorithm
echo 4G > /sys/block/zram0/disksize   # 4GB compressed swap

# Create and enable swap
mkswap /dev/zram0
swapon -p 100 /dev/zram0  # Higher priority than disk swap

# Check zram statistics
cat /sys/block/zram0/mm_stat
# orig_data_size compr_data_size mem_used_total mem_limit mem_used_max
# 1073741824      268435456       301989888      0        301989888

# Disable and remove zram
swapoff /dev/zram0
echo 1 > /sys/block/zram0/reset
```

### zswap vs zram

| Feature | zswap | zram |
|---------|-------|------|
| Type | Swap cache | Block device |
| Requires swap | Yes (write-back) | No (is swap) |
| Compression | On swap-out path | On all writes |
| Eviction | To backing swap | Cannot evict |
| Use case | Systems with disk swap | Systems without swap |

## Memory Compaction

Memory compaction moves pages to create contiguous free regions needed
for higher-order allocations (THP, slab). It runs alongside reclaim:

```bash
# Trigger compaction manually
echo 1 > /proc/sys/vm/compact_memory

# Check compaction statistics
grep compact /proc/vmstat
# compact_stall    — Direct compaction stalls
# compact_success  — Successful compactions
# compact_fail     — Failed compactions

# Proactive compaction (Linux 5.9+)
echo 20 > /proc/sys/vm/compaction_proactiveness
# 0 = disabled, 100 = very aggressive
```

### Compaction vs Reclaim

```mermaid
flowchart TD
    A["High-order allocation fails"] --> B{"Enough free pages?"}
    B -->|No| C["Reclaim: free pages"]
    B -->|Yes| D["Compaction: move pages"]
    C --> E{"Contiguous region?"}
    D --> E
    E -->|Yes| F["Allocation succeeds"]
    E -->|No| G["Try harder or fail"]
```

## Cgroup Memory Reclaim

### Per-Cgroup Reclaim

Each cgroup has its own memory limit and reclaim behavior:

```bash
# Set memory limit
echo 2G > /sys/fs/cgroup/myapp/memory.max

# Set memory high (throttle, not OOM)
echo 1.5G > /sys/fs/cgroup/myapp/memory.high

# Set memory low (protected, won't be reclaimed)
echo 512M > /sys/fs/cgroup/myapp/memory.low

# Set memory min (hard protected)
echo 256M > /sys/fs/cgroup/myapp/memory.min

# Check cgroup memory events
cat /sys/fs/cgroup/myapp/memory.events
# low 0
# high 0
# max 0
# oom 0
# oom_kill 0
```

### Memory Pressure Notifications

```bash
# PSI-based pressure monitoring (Linux 4.20+)
cat /proc/pressure/memory
# some avg10=0.00 avg60=0.00 avg300=0.00 total=0
# full avg10=0.00 avg60=0.00 avg300=0.00 total=0

# Per-cgroup pressure
cat /sys/fs/cgroup/myapp/memory.pressure

# Monitor with systemd
systemd-run --scope -p MemoryMax=2G \
    --property=MemoryPressureWatch=on \
    stress-ng --vm 2 --vm-bytes 1G --timeout 60s
```

## Advanced Reclaim Tuning

### Per-Zone Reclaim Mode

On NUMA systems, `vm.zone_reclaim_mode` controls whether the kernel
reclaims from the local zone or accesses remote nodes:

```bash
# 0 (default): Don't reclaim from local zone, access remote memory
# 1: Reclaim from local zone before going remote
# 2: Write dirty pages from local zone
# 4: Swap from local zone
sysctl vm.zone_reclaim_mode=0

# For most workloads, 0 is optimal (allows remote access)
# For HPC with strict NUMA locality, use 1
```

### Huge Pages and Reclaim

THP (Transparent Huge Pages) interact with reclaim:

```bash
# Check THP settings
cat /sys/kernel/mm/transparent_hugepage/enabled
# always [madvise] never

# THP can increase reclaim latency (2MB pages vs 4KB)
# For latency-sensitive workloads, use madvise mode
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled

# Check THP stats
grep thp /proc/vmstat
# thp_fault_alloc — THP allocated on fault
# thp_collapse_alloc — THP allocated during collapse
# thp_split — THP split to 4KB pages
```

### Reclaim Latency Monitoring

```bash
# Enable reclaim latency tracing
echo 1 > /sys/kernel/debug/tracing/events/vmscan/mm_vmscan_direct_reclaim_begin/enable
echo 1 > /sys/kernel/debug/tracing/events/vmscan/mm_vmscan_direct_reclaim_end/enable

# View with timestamps
cat /sys/kernel/debug/tracing/trace_pipe | grep direct_reclaim

# Measure reclaim latency distribution
# Using bpftrace:
bpftrace -e '
tracepoint:vmscan:mm_vmscan_direct_reclaim_begin {
    @start[tid] = nsecs;
}
tracepoint:vmscan:mm_vmscan_direct_reclaim_end {
    if (@start[tid]) {
        @usecs = hist((nsecs - @start[tid]) / 1000);
        delete(@start[tid]);
    }
}'
```

## Reclaim Decision Tree

```mermaid
flowchart TD
    A["Memory allocation"] --> B{"Order > 0?"}
    B -->|Yes| C["Try compaction first"]
    B -->|No| D{"Below low watermark?"}
    C --> E{"Compaction successful?"}
    E -->|Yes| F["Allocate"]
    E -->|No| G["Reclaim + compact"]
    D -->|No| H{"Below min watermark?"}
    D -->|Yes| I["Wake kswapd"]
    H -->|No| J["Direct reclaim"]
    H -->|Yes| K["kswapd + direct reclaim"]
    J --> L{"Enough pages freed?"}
    K --> L
    L -->|Yes| F
    L -->|No| M["OOM killer"]
```

## Common Issues

### Direct Reclaim Stalls

**Symptom**: Application latency spikes when memory is low.

**Cause**: The allocating thread enters direct reclaim and blocks for milliseconds while scanning LRU lists and writing dirty pages.

**Solutions**:
- Increase `vm.min_free_kbytes` to trigger kswapd earlier
- Use `vm.watermark_boost_factor` for anti-fragmentation
- Set `vm.zone_reclaim_mode=0` on NUMA systems (default)
- Use cgroup memory limits to isolate workloads

### kswapd CPU Usage

**Symptom**: kswapd consuming 100% CPU.

**Cause**: Constant memory pressure causing kswapd to never sleep.

**Solutions**:
- Add more physical memory
- Reduce application memory usage
- Enable zswap for compressed swap
- Use cgroup memory limits

### OOM Kills Despite Free Memory

**Symptom**: OOM kills when `free` shows available memory.

**Cause**: Memory is in use by page cache, slab, or is fragmented (not enough contiguous pages for the requested order).

**Solutions**:
- Check `/proc/zoneinfo` for fragmentation
- Use `cat /sys/kernel/debug/extfrag/extfrag_index`
- Consider compaction tuning
- Check for memory leaks in slab (`/proc/slabinfo`)

---

## History

| Version | Change |
|---------|--------|
| v2.4 | Initial page reclaim with simple LRU |
| v2.5 | rmap (reverse mapping) — reclaim mapped pages |
| v2.6.28 | Split LRU — separate anon/file lists |
| v2.6.35 | Memory compaction integrated with reclaim |
| v3.8 | vmpressure notifications |
| v4.20 | PSI (Pressure Stall Information) |
| v5.9 | Proactive compaction |
| v6.1 | MGLRU (Multi-Gen LRU) |

---

## Source Files

| File | Contents |
|------|----------|
| `mm/vmscan.c` | Core reclaim engine: kswapd, shrink_node, shrink_lruvec |
| `mm/oom_kill.c` | OOM killer implementation |
| `mm/memcontrol.c` | cgroup memory reclaim |
| `mm/swap.c` | LRU list management |
| `mm/workingset.c` | Working set detection |
| `include/linux/mmzone.h` | LRU list definitions |
| `include/linux/memcontrol.h` | Memory cgroup structures |

---

## Further Reading

- **Kernel documentation**: `Documentation/admin-guide/sysctl/vm.rst`
- **kernel-internals.org**: [Page Reclaim](https://kernel-internals.org/mm/reclaim/)
- **LWN**: ["The Multi-Gen LRU"](https://lwn.net/Articles/856931/) — MGLRU design
- **LWN**: ["A new approach to LRU"](https://lwn.net/Articles/495543/) — Original LRU redesign
- **Mel Gorman**: "Understanding the Linux Virtual Memory Manager"
- **Source**: `mm/vmscan.c` — reclaim implementation

---

## See Also

- [Memory Management Overview](./overview.md) — page allocator, zones
- [Page Types](./page-types.md) — what gets reclaimed
- [Swap](./swap.md) — swap subsystem for anonymous pages
- [zswap](./zswap.md) — compressed swap cache
- [zpool](./zpool.md) — compressed memory pool
- [OOM Killer](./oom-killer.md) — last-resort memory recovery
- [Memory Compaction](./compaction.md) — compaction during reclaim
- [vmpressure](./vmpressure.md) — pressure notifications
- [Idle Page Tracking](./idle-page-tracking.md) — identifying cold pages
- [GUP](./gup.md) — pinned pages affect reclaim
- [Page Cache](./page-cache.md) — file-backed page management
- [Slab Allocator](./slab-allocator.md) — kernel object reclaim
