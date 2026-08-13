# Memory Zones

## Introduction

Memory zones are the kernel's way of categorizing physical memory into regions with different properties and constraints. The Linux kernel defines several zones — `ZONE_DMA`, `ZONE_DMA32`, `ZONE_NORMAL`, `ZONE_HIGHMEM`, and `ZONE_MOVABLE` — each representing a range of physical addresses with specific characteristics. The buddy allocator, page cache, and slab allocator all operate within these zones.

The zone system exists primarily because not all physical memory is equal. Some devices can only DMA to low addresses. 32-bit systems can't directly address all physical memory. And some allocations need movable pages for compaction. Zones ensure that allocations are satisfied from appropriate memory regions.

## Zone Types

### Overview

```mermaid
graph TB
    subgraph "Physical Memory Layout (x86-64)"
        Z0["Zone DMA<br>0 - 16MB<br>Legacy ISA DMA"]
        Z1["Zone DMA32<br>16MB - 4GB<br>32-bit DMA devices"]
        Z2["Zone Normal<br>4GB - 64GB+<br>General purpose"]
        Z3["Zone Movable<br>Variable<br>For hotplug/compaction"]
    end
    subgraph "32-bit System"
        Z4["Zone DMA<br>0 - 16MB"]
        Z5["Zone Normal<br>16MB - 896MB"]
        Z6["Zone Highmem<br>896MB - 4GB+<br>Not directly mapped"]
    end
```

### ZONE_DMA

```c
/* Zone DMA: 0 to 16MB on x86 */
/* Some ISA devices can only access the first 16MB of physical memory */

/* Typical use: old ISA network cards, sound cards, floppy controllers */
struct page *page = alloc_pages(GFP_DMA, order);

/* Modern systems rarely need ZONE_DMA */
/* Most PCI devices support 32-bit DMA (ZONE_DMA32) */
```

**Why 16MB?** The original IBM PC AT (1984) had a 24-bit address bus on the ISA bus, limiting DMA to the first 16MB. Modern PCI/PCIe devices typically support 32-bit or 64-bit DMA, but the zone persists for legacy compatibility.

### ZONE_DMA32

```c
/* Zone DMA32: 0 to 4GB on x86-64 */
/* 32-bit DMA devices can access this zone */
/* Most modern devices use this zone */

struct page *page = alloc_pages(GFP_DMA32, order);
```

**Why 4GB?** 32-bit PCI devices can only address memory below 4GB. This zone exists only on 64-bit systems (on 32-bit, ZONE_NORMAL covers this range).

### ZONE_NORMAL

```c
/* Zone Normal: directly mapped kernel memory */
/* On x86-64: typically 4GB to end of physical memory */
/* This is where most allocations come from */

struct page *page = alloc_pages(GFP_KERNEL, order);  /* Usually from ZONE_NORMAL */
```

ZONE_NORMAL is the workhorse zone — most kernel allocations, page cache entries, and user pages come from here. The kernel maintains a direct mapping (`page_offset_base` to `page_offset_base + memory_size`) where every physical page in ZONE_NORMAL has a fixed virtual address.

### ZONE_HIGHMEM (32-bit only)

```c
/* Zone Highmem: above 896MB on 32-bit x86 */
/* Cannot be permanently mapped in kernel address space */
/* 32-bit kernels have ~1GB of kernel virtual address space */
/* Only 896MB can be directly mapped */

/* Pages in HIGHMEM must be kmap()'d before use */
void *vaddr = kmap(highmem_page);
memcpy(vaddr, data, PAGE_SIZE);
kunmap(highmem_page);

/* 64-bit kernels don't have HIGHMEM — all memory is directly mapped */
```

```mermaid
graph TB
    subgraph "32-bit Kernel Virtual Address Space (1GB)"
        KV["0xC0000000 - 0xFFFFFFFF<br>Kernel Space"]
        DM["Direct mapping<br>0xC0000000 - 0xF8000000<br>(896MB)"]
        VMALLOC["vmalloc area"]
        PKMAP["Persistent kmap<br>(4MB)"]
        FIXMAP["Fixmap area"]
    end
    subgraph "Physical Memory"
        PM_LOW["0 - 896MB<br>(ZONE_DMA + ZONE_NORMAL)"]
        PM_HIGH["896MB - 4GB+<br>(ZONE_HIGHMEM)"]
    end
    DM --> PM_LOW
    PKMAP -->|"kmap()"| PM_HIGH
```

### ZONE_MOVABLE

```c
/* Zone Movable: pages that can be migrated/compacted */
/* Used for memory hotplug and anti-fragmentation */
/* Not all pages in this zone are movable, but the zone is
   created with the expectation that pages can be moved */

/* Set up via kernel command line or sysfs */
/* kernelcore=1G movablecore=2G */
```

ZONE_MOVABLE was introduced to improve memory hotplug support and reduce fragmentation. Pages in this zone are expected to be movable (user pages, page cache), allowing the kernel to migrate them for compaction or hot-remove.

### Zone Selection Summary

| Zone | Address Range (x86-64) | GFP Flag | Primary Use |
|------|----------------------|----------|-------------|
| ZONE_DMA | 0-16 MB | `GFP_DMA` | Legacy ISA devices |
| ZONE_DMA32 | 16 MB-4 GB | `GFP_DMA32` | 32-bit PCI devices |
| ZONE_NORMAL | 4 GB+ | `GFP_KERNEL` | General kernel allocations |
| ZONE_HIGHMEM | N/A (64-bit) | `GFP_HIGHMEM` | 32-bit only |
| ZONE_MOVABLE | Variable | `__GFP_MOVABLE` | Hotplug, anti-fragmentation |

## Zone Structure

```c
/* Simplified from include/linux/mmzone.h */
struct zone {
    unsigned long _watermark[NR_WMARK];  /* Watermark levels */
    long lowmem_reserve[MAX_NR_ZONES];   /* Reserve for higher zones */

    struct pglist_data *zone_pgdat;      /* Back-pointer to node */
    struct per_cpu_pages __percpu *per_cpu_pageset;  /* Per-cpu page caches */

    unsigned long zone_start_pfn;        /* First page frame in zone */
    atomic_long_t managed_pages;         /* Pages managed by buddy */
    unsigned long spanned_pages;         /* Total pages (including holes) */
    unsigned long present_pages;         /* Physical pages present */

    const char *name;                    /* "DMA", "Normal", etc. */

    /* Free area: buddy allocator lists */
    struct free_area free_area[NR_PAGE_ORDERS];

    unsigned long flags;                 /* Zone flags */
    spinlock_t lock;                     /* Protects the zone */

    /* Statistics */
    unsigned long nr_saved_writeback;    /* Writeback pages */
    unsigned long nr_unaccepted;         /* Unaccepted pages */
};
```

### Per-CPU Page Cache (PCP)

```mermaid
graph TD
    subgraph "Zone"
        BUDDY["Buddy Allocator<br>(order 0 to MAX_ORDER)"]
    end
    subgraph "Per-CPU Pageset (PCP)"
        PCP0["CPU 0: hot/cold page lists"]
        PCP1["CPU 1: hot/cold page lists"]
        PCP2["CPU 2: hot/cold page lists"]
    end
    PCP0 -->|"drain/allocate"| BUDDY
    PCP1 -->|"drain/allocate"| BUDDY
    PCP2 -->|"drain/allocate"| BUDDY
```

The per-cpu page cache (PCP) caches small (order-0) allocations per CPU to avoid contending on the zone lock:

```c
struct per_cpu_pages {
    int count;          /* Number of pages in list */
    int high;           /* High watermark for draining */
    struct list_head lists[MIGRATE_TYPES]; /* Per-migrate-type lists */
};
```

**PCP allocation fast path:**

```c
/* mm/page_alloc.c — simplified */
static struct page *rmqueue_pcplist(struct zone *zone, gfp_t gfp)
{
    struct per_cpu_pages *pcp;
    struct list_head *list;
    struct page *page;

    /* Get per-CPU list */
    pcp = this_cpu_ptr(zone->per_cpu_pageset);
    list = &pcp->lists[MIGRATE_UNMOVABLE];  /* or MOVABLE, RECLAIMABLE */

    /* Try per-CPU list first */
    if (!list_empty(list)) {
        page = list_first_entry(list, struct page, lru);
        list_del(&page->lru);
        pcp->count--;
        return page;  /* Fast path — no zone lock needed */
    }

    /* Per-CPU list empty — refill from buddy */
    return rmqueue_bulk(zone, order, pcp);
}
```

### PCP Draining

```bash
# PCP lists are drained when:
# 1. Count exceeds high watermark
# 2. Memory pressure occurs
# 3. CPU goes offline

# Manually drain PCP lists (rarely needed)
$ echo 1 > /proc/sys/vm/compact_memory

# View PCP statistics
$ cat /proc/vmstat | grep pcp
nr_mlock 0
# (PCP stats are per-CPU and not directly exposed)
```

## Watermarks

### Three Watermark Levels

```mermaid
graph LR
    subgraph "Memory Zone"
        direction TB
        HIGH["High watermark<br>kswapd wakes up"]
        LOW["Low watermark<br>kswapd may not keep up"]
        MIN["Min watermark<br>Direct reclaim triggered"]
        FREE["Free pages"]
    end
```

| Watermark | Behavior |
|-----------|----------|
| **High** | `kswapd` goes back to sleep (enough free memory) |
| **Low** | `kswapd` wakes up to reclaim pages |
| **Min** | Allocations block and do direct reclaim |

### Watermark Calculation

```bash
# View current watermarks
$ cat /proc/zoneinfo | grep -A 5 "Node 0, zone   Normal"
Node 0, zone   Normal
  pages free     234567
        boost    0
        min      4096
        low      5120
        high     6144
        spanned  8388608
        present  8388608
        managed  8123456

# Watermarks are in pages (4KB each)
# min = 16MB, low = 20MB, high = 24MB (for this zone)

# Tune watermarks
$ sysctl vm.watermark_boost_factor
vm.watermark_boost_factor = 15000

$ sysctl vm.watermark_scale_factor
vm.watermark_scale_factor = 10

# watermark_min = min_free_kbytes / zone_size * zone_managed_pages
$ sysctl vm.min_free_kbytes
vm.min_free_kbytes = 67584
```

### Watermark Internals

```c
/* mm/page_alloc.c */
static void __setup_per_zone_wmarks(void)
{
    unsigned long pages_min = min_free_kbytes >> (PAGE_SHIFT - 10);
    unsigned long lowmem_pages = 0;
    struct zone *zone;
    unsigned long flags;

    for_each_zone(zone) {
        if (!managed_zone(zone))
            continue;

        /* Calculate proportional watermark */
        zone->_watermark[WMARK_MIN] = ...;
        zone->_watermark[WMARK_LOW] = ... + (zone->_watermark[WMARK_MIN] * watermark_scale_factor / 10000);
        zone->_watermark[WMARK_HIGH] = ... + (zone->_watermark[WMARK_MIN] * watermark_scale_factor / 10000) * 2;
    }
}
```

### Watermark Boost

The `watermark_boost_factor` temporarily increases watermarks when fragmentation is detected:

```bash
# Default: 15000 (150% boost)
$ sysctl vm.watermark_boost_factor
vm.watermark_boost_factor = 15000

# When boosted, the effective watermarks are:
# min_boosted = min * boost_factor / 10000
# This triggers more aggressive reclaim to reduce fragmentation

# Disable watermark boosting
$ echo 0 > /proc/sys/vm/watermark_boost_factor
```

## GFP Flags and Zone Selection

### GFP (Get Free Pages) Flags

```c
/* Zone modifiers */
#define __GFP_DMA       0x01u   /* Allocate from ZONE_DMA */
#define __GFP_HIGHMEM   0x02u   /* Allocate from ZONE_HIGHMEM */
#define __GFP_DMA32     0x04u   /* Allocate from ZONE_DMA32 */
#define __GFP_MOVABLE   0x08u   /* Allocate from ZONE_MOVABLE */

/* Action modifiers */
#define __GFP_RECLAIM   0x400000u  /* Can trigger reclaim */
#define __GFP_NORETRY   0x0400000u /* Don't retry on failure */
#define __GFP_NOFAIL    0x0800000u /* Never fail (retry forever) */

/* Common combinations */
#define GFP_KERNEL      (__GFP_RECLAIM | __GFP_IO | __GFP_FS)
#define GFP_ATOMIC      (__GFP_HIGH)
#define GFP_USER        (__GFP_RECLAIM | __GFP_IO | __GFP_FS | __GFP_HARDWALL)
#define GFP_DMA         (__GFP_DMA)
#define GFP_DMA32       (__GFP_DMA32)
#define GFP_HIGHUSER    (__GFP_RECLAIM | __GFP_IO | __GFP_FS | __GFP_HARDWALL | __GFP_HIGHMEM)
```

### GFP Flag Reference

| Flag | Can Sleep | Can Reclaim | Can I/O | Zone | Use Case |
|------|-----------|-------------|---------|------|----------|
| `GFP_KERNEL` | ✅ | ✅ | ✅ | Normal | Process context |
| `GFP_ATOMIC` | ❌ | ❌ | ❌ | Any | Interrupt context |
| `GFP_DMA` | ❌ | ❌ | ❌ | DMA | ISA DMA devices |
| `GFP_DMA32` | ❌ | ❌ | ❌ | DMA32 | 32-bit DMA devices |
| `GFP_HIGHUSER` | ✅ | ✅ | ✅ | Highmem | User pages (32-bit) |
| `GFP_NOIO` | ✅ | ✅ | ❌ | Normal | I/O paths (avoid recursion) |
| `GFP_NOFS` | ✅ | ✅ | ❌ | Normal | FS paths (avoid recursion) |
| `GFP_NOWAIT` | ❌ | ❌ | ❌ | Any | Best-effort, no reclaim |
| `GFP_ZERO` | — | — | — | Any | Zero the allocated page |

### Zone Selection Flow

```mermaid
flowchart TD
    A[Allocation request] --> B{GFP flag analysis}
    B -->|"__GFP_DMA"| C[ZONE_DMA only]
    B -->|"__GFP_DMA32"| D["ZONE_DMA32, ZONE_DMA"]
    B -->|"__GFP_HIGHMEM"| E["ZONE_HIGHMEM, ZONE_NORMAL, ZONE_DMA"]
    B -->|"GFP_KERNEL"| F["ZONE_NORMAL, ZONE_DMA"]
    B -->|"GFP_HIGHUSER"| G["ZONE_HIGHMEM, ZONE_NORMAL, ZONE_DMA"]
    C --> H{Pages available?}
    D --> H
    E --> H
    F --> H
    G --> H
    H -->|Yes| I[Allocate from preferred zone]
    H -->|No| J[Fallback to other zones]
    J --> K{Still no pages?}
    K -->|Yes| L[Direct reclaim / compaction]
    K -->|No| I
    L --> M{Allocation succeeds?}
    M -->|Yes| I
    M -->|No| N[Allocation fails / OOM]
```

### Zone Fallback Order

When a zone can't satisfy an allocation, the kernel falls back to other zones:

```mermaid
graph TD
    subgraph "Fallback Order (GFP_KERNEL)"
        A["Preferred: ZONE_NORMAL"] --> B["Fallback: ZONE_DMA32"]
        B --> C["Fallback: ZONE_DMA"]
    end
    subgraph "Fallback Order (GFP_HIGHUSER)"
        D["Preferred: ZONE_HIGHMEM"] --> E["Fallback: ZONE_NORMAL"]
        E --> F["Fallback: ZONE_DMA32"]
        F --> G["Fallback: ZONE_DMA"]
    end
```

The fallback order is defined by the `zonelist` structure, which is built at boot time based on the system's NUMA topology and zone layout.

### Lowmem Reserve

To prevent lower zones from being exhausted by higher-zone fallbacks, the kernel maintains **lowmem reserves**:

```c
/* Each zone reserves pages that cannot be used by higher-zone fallbacks */
/* This ensures DMA allocations can always succeed */

$ cat /proc/zoneinfo | grep protection
        protection: (0, 2045, 3852, 3852, 3852)
# (DMA: 0, DMA32: 2045, Normal: 3852, Movable: 3852, Highmem: 3852)
# Values in pages — DMA32 reserves 2045 pages from Normal
```

## /proc/zoneinfo

```bash
$ cat /proc/zoneinfo
Node 0, zone      DMA
  pages free     3968
        boost    0
        min      16
        low      20
        high     24
        spanned  4096
        present  3975
        managed  3968
        protection: (0, 2045, 3852, 3852, 3852)
  nr_free_pages 3968
  nr_zone_active_anon 0
  nr_zone_inactive_anon 0
  nr_zone_active_file 0
  nr_zone_inactive_file 0
  # ... many more counters ...

Node 0, zone    DMA32
  pages free     234567
        boost    0
        min      8192
        low      10240
        high     12288
        spanned  1048576
        present  524288
        managed  520000
        protection: (0, 0, 1804, 1804, 1804)

Node 0, zone   Normal
  pages free     1234567
        boost    0
        min      32768
        low      40960
        high     49152
        spanned  8388608
        present  8388608
        managed  8123456
        protection: (0, 0, 0, 0, 0)
```

### Key Fields

| Field | Meaning |
|-------|---------|
| `free` | Current free pages |
| `min/low/high` | Watermark levels |
| `boost` | Current watermark boost factor |
| `spanned` | Total pages (including holes in physical address space) |
| `present` | Physical pages actually present |
| `managed` | Pages managed by the buddy allocator |
| `protection` | Lowmem reserve from other zones |

### Analyzing /proc/zoneinfo

```bash
# Check zone health
$ awk '/^Node/ { zone=$4 } /pages free/ { free=$3 } /high/ { high=$3 } 
       /min/ { min=$3 } END { 
           if (free < min) print "CRITICAL: " zone " below minimum watermark"
           else if (free < high) print "WARNING: " zone " below high watermark"
           else print "OK: " zone
       }' /proc/zoneinfo

# Monitor zone free pages over time
$ watch -n1 'cat /proc/zoneinfo | grep -E "^Node|pages free|min:|low:|high:"'

# Check if ZONE_DMA is being depleted
$ cat /proc/zoneinfo | awk '/zone.*DMA$/{p=1} p && /pages free/{print $3; exit}'
```

## NUMA and Zones

On NUMA systems, each NUMA node has its own set of zones:

```bash
# View NUMA topology
$ numactl --hardware
available: 2 nodes (0-1)
node 0 cpus: 0 1 2 3 4 5 6 7
node 0 size: 32768 MB
node 0 free: 16384 MB
node 1 cpus: 8 9 10 11 12 13 14 15
node 1 size: 32768 MB
node 1 free: 16384 MB

# Each node has its own zones
$ cat /proc/zoneinfo | grep "Node"
Node 0, zone      DMA
Node 0, zone    DMA32
Node 0, zone   Normal
Node 1, zone   Normal
```

### NUMA Zone Interaction

```mermaid
graph TB
    subgraph "NUMA Node 0"
        N0_DMA["Zone DMA (0-16MB)"]
        N0_DMA32["Zone DMA32 (16MB-4GB)"]
        N0_NORMAL["Zone Normal (4GB+)"]
    end
    subgraph "NUMA Node 1"
        N1_NORMAL["Zone Normal"]
    end
    N0_DMA --> N0_DMA32 --> N0_NORMAL --> N1_NORMAL
```

### NUMA-Aware Allocation

```c
/* Allocate from specific NUMA node */
struct page *alloc_pages_node(int nid, gfp_t gfp, unsigned int order);

/* Allocate from current node (preferred) */
struct page *alloc_pages(gfp_t gfp, unsigned int order);

/* Allocate from preferred node with fallback */
struct page *alloc_pages_preferred(gfp_t gfp, unsigned int order, int preferred_nid);
```

```bash
# View per-node allocation statistics
$ cat /proc/vmstat | grep numa
numa_hit 12345678
numa_miss 0
numa_foreign 0
numa_interleave 1234
numa_local 12345678
numa_other 0

# High numa_miss indicates cross-node allocations (performance penalty)
```

## Zone Compaction

Memory compaction operates within zones to reduce fragmentation:

```bash
# Trigger manual compaction
$ echo 1 > /proc/sys/vm/compact_memory

# View compaction statistics
$ cat /proc/vmstat | grep compact
compact_success 1234
compact_fail 56
compact_stall 0
compact_skip 789
compact_migrate_scanned 1234567
compact_free_scanned 2345678

# Compaction works by:
# 1. Scanning from the bottom of the zone for free pages
# 2. Scanning from the top of the zone for movable pages
# 3. Migrating movable pages to consolidate free space
```

### Compaction Flow

```mermaid
graph TD
    A[Large allocation fails] --> B[Zone compaction]
    B --> C[Scan from bottom: find free pages]
    B --> D[Scan from top: find movable pages]
    C --> E[Create free block]
    D --> F[Migrate movable pages]
    F --> G[Consolidate free space]
    E --> H[Retry allocation]
```

## Implementation Details

### Key Source Files

- **`mm/page_alloc.c`** — Buddy allocator and zone management (~8000 lines)
- **`include/linux/mmzone.h`** — Zone and zone-related structures
- **`mm/vmstat.c`** — Zone statistics (`/proc/zoneinfo`)
- **`mm/page-writeback.c`** — Writeback watermarks

### Zone Initialization

```c
/* Simplified zone initialization */
static void __meminit zone_init_free_lists(struct zone *zone) {
    unsigned int order, t;

    for_each_migratetype_order(order, t) {
        INIT_LIST_HEAD(&zone->free_area[order].free_list[t]);
        zone->free_area[order].nr_free = 0;
    }
}

/* Boot-time zone setup */
void __meminit free_area_init_node(int nid, unsigned long *zones_size,
                                    unsigned long node_start_pfn,
                                    unsigned long *zholes_size) {
    pg_data_t *NODE_DATA(nid) = ...;
    /* Initialize each zone in this NUMA node */
    for (i = 0; i < MAX_NR_ZONES; i++) {
        struct zone *zone = NODE_DATA(nid)->node_zones + i;
        zone->name = zone_names[i];
        zone_init_free_lists(zone);
    }
}
```

### Buddy Allocator

```c
/* Buddy allocator: power-of-2 page allocation */
struct free_area {
    struct list_head free_list[MIGRATE_TYPES];
    unsigned long nr_free;
};

/* Allocate 2^order pages from a zone */
struct page *__alloc_pages(gfp_t gfp, unsigned int order, int preferred_nid,
                           nodemask_t *nodemask) {
    struct page *page;
    struct zonelist *zonelist;
    struct zone *zone;

    /* Try each zone in the zonelist */
    for_each_zone_zonelist_nodemask(zone, zonelist, preferred_nid, nodemask) {
        /* Try the buddy allocator */
        page = __alloc_pages_slow(gfp, order, zone);
        if (page)
            return page;
    }
    return NULL;  /* All zones exhausted */
}
```

### Buddy Allocator Internals

```mermaid
graph TD
    A["alloc pages, order 2"] --> B["Check free area list"]
    B -->|Found| C[Remove from list, return page]
    B -->|Not found| D[Split order-3 block]
    D --> E[2 order-2 blocks]
    E --> F["Return one, put other in free area list"]
    D -->|No order-3| G[Split order-4 block]
    G --> H[Continue splitting until order-2 available]
    H -->|No blocks| I[Reclaim / compaction / OOM]
```

## Zone-Specific Diagnostics

### Zone Pressure Analysis

```bash
# Calculate zone pressure
#!/bin/bash
while read -r line; do
    if [[ $line =~ "Node" ]]; then
        zone=$(echo $line | awk '{print $4}')
    fi
    if [[ $line =~ "pages free" ]]; then
        free=$(echo $line | awk '{print $3}')
    fi
    if [[ $line =~ "min" ]]; then
        min=$(echo $line | awk '{print $3}')
        pct=$((free * 100 / min))
        if [ $pct -lt 100 ]; then
            echo "CRITICAL: $zone free=$free min=$min (${pct}%)"
        elif [ $pct -lt 200 ]; then
            echo "WARNING:  $zone free=$free min=$min (${pct}%)"
        else
            echo "OK:       $zone free=$free min=$min (${pct}%)"
        fi
    fi
done < /proc/zoneinfo
```

### Zone Fragmentation Index

```bash
# View fragmentation index per zone
$ cat /proc/buddyinfo
Node 0, zone      DMA      1      1      0      1      1      0      1      0      1      1      3
Node 0, zone    DMA32    234    156     89     45     23     12      6      3      1      0      0
Node 0, zone   Normal  12345   8901   5678   3456   1234    567    234    123     56     12      3

# Columns: order 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
# Values: number of free blocks of each order

# Calculate fragmentation
# High order-0 with few high-order blocks = fragmented
# Many high-order blocks = healthy
```

## References

- [Linux kernel mm/mmzone.h](https://github.com/torvalds/linux/blob/master/include/linux/mmzone.h)
- [Linux kernel mm/page_alloc.c](https://github.com/torvalds/linux/blob/master/mm/page_alloc.c)
- [Kernel documentation: Memory Management](https://www.kernel.org/doc/html/latest/admin-guide/mm/index.html)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html
- https://man7.org/linux/man-pages/man5/proc.5.html — /proc/zoneinfo
- https://lwn.net/Articles/712460/ — "Folios and the page cache"
- https://www.kernel.org/doc/html/latest/mm/page_alloc.html
- https://lwn.net/Articles/152347/ — "The zone allocator"

## Related Topics

- [numa](./numa.md) — NUMA nodes contain zones
- [compaction](./compaction.md) — Compaction operates within zones
- [buffer-cache](./buffer-cache.md) — Page cache uses zone-based allocation
- [aslr](./aslr.md) — ASLR interacts with zone-based allocation
