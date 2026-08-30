# memblock: Early Boot Memory Allocation

Before the buddy allocator can hand out a single page, it needs pages of its own: `struct page` arrays, zone descriptors, per-node `pg_data_t`, and the free-area lists themselves all have to be allocated by something simpler. That something is **memblock** -- a two-array, first-fit region allocator that runs from the moment the architecture code knows the RAM layout until `mem_init()` hands every unreserved page to the buddy. This page is the boot-time sibling of [Bootloaders](./bootloaders.md) (which ends at the `boot_params` handoff), [Kernel Boot](../core/kernel-boot.md) (where `setup_arch()` and `mem_init()` sit), and [Page Allocation](../mm/page-allocation.md) / [Page Allocator (Buddy System)](../memory/page-allocator.md) (the allocator that takes over). Node topology questions belong to [NUMA](../mm/numa.md); the `mem=` and `movable_node` parameters are documented in [Kernel Command Line Parameters](../cmdline-params.md).

## 1. The chicken-and-egg problem

The page allocator cannot bootstrap itself: initializing free lists, zones and the `struct page` array for every RAM page requires memory to put them in, and `kmalloc()` needs slab, which needs pages from the buddy. Worse, some of those allocations have hard address constraints -- DMA-capable ranges below 4 GiB, NUMA-local memory, mirrored (more-reliable) firmware regions -- long before the topology is fully known. Memblock solves this with an intentionally dumb design: two sorted arrays of `(base, size, node, flags)` tuples and a first-fit search, so allocator metadata costs a few dozen bytes per region instead of one bit per page. The kernel's own documentation (`Documentation/core-api/boot-time-mm.rst`) frames it exactly this way: early initialization "cannot use normal memory management simply because it is not set up yet".

## 2. Boot timeline

```text
   firmware                          kernel: setup_arch()                 handoff
 --------------   ----------------------------------------------------------------   ------------
 e820 table in    [1] memblock_add() x N: memory[] <- RAM ranges                    mem_init():
 boot_params,         (mem= clamps the map first; movable_node sets                     memblock_free_all():
 UEFI GetMemoryMap,    bottom-up direction)                                             for_each_free_mem_range():
 DT "memory" nodes [2] memblock_reserve() x M: kernel image, initrd,                    __free_pages_core()
        |              EBDA/BIOS ranges, ACPI tables, DT reserved-memory                 -> buddy free lists
        +------------>[3] early page tables: BRK pgt_buf, fallback                     memblock_discard():
                           memblock_phys_alloc_range()                                  region arrays freed
                       [4] per-cpu areas, NUMA node data, sparse vmemmap,                        |
                           direct-map staging (top-down from current_limit)                      v
                       [5] free_area_init(): zones + struct page arrays              buddy owns every
                           -- the buddy's own metadata, paid from memblock           page; slab is up;
                                                                                     memblock APIs WARN
```

## 3. The data model: memory[] vs reserved[]

Memblock tracks two (sometimes three) arrays, wrapped in one statically-initialized struct (`include/linux/memblock.h`):

```c
struct memblock {
    bool bottom_up;              /* allocation direction */
    phys_addr_t current_limit;   /* ceiling for MEMBLOCK_ALLOC_ACCESSIBLE */
    struct memblock_type memory;   /* RAM the kernel may use */
    struct memblock_type reserved; /* what early code has taken */
};
struct memblock_type { unsigned long cnt, max; phys_addr_t total_size;
                       struct memblock_region *regions; char *name; };
struct memblock_region { phys_addr_t base, size; enum memblock_flags flags;
                         int nid; }; /* nid under CONFIG_NUMA */
```

`memory` describes what the kernel may use (after `mem=` and hotplug restrictions), `reserved` what early code has claimed; free space is always the set difference, computed on the fly by `for_each_free_mem_range()`. Some architectures also carry a `physmem` array -- installed RAM regardless of `mem=`. Both arrays start as static `__initdata_memblock` buffers of `INIT_MEMBLOCK_REGIONS` (128) entries and double via `memblock_double_array()` when they overflow; the replacement array is allocated with memblock itself (or `kmalloc` if slab is up), page-aligned so it can be freed cleanly later. Region flags (`include/linux/memblock.h`):

| Flag | Meaning |
|------|---------|
| `MEMBLOCK_HOTPLUG` | firmware-marked hotpluggable RAM; avoided under `movable_node` |
| `MEMBLOCK_MIRROR` | mirrored, more-reliable memory; preferred by allocations |
| `MEMBLOCK_NOMAP` | RAM kept out of the direct map (DT reserved regions) |
| `MEMBLOCK_DRIVER_MANAGED` | detected by a driver (CXL/pluggable), never by firmware map |
| `MEMBLOCK_RSRV_KERN` | reserved for kernel use; every allocation sets it |
| `MEMBLOCK_KHO_SCRATCH` | kexec-handover scratch; the only source while `kho_scratch_only` |

(`MEMBLOCK_RSRV_NOINIT` and `MEMBLOCK_RSRV_HUGETLB` cover `struct page`-skipping reservations and early hugetlb reservations.)

## 4. The allocation API

| Call | Role |
|------|------|
| `memblock_add(base, size)` | add RAM to `memory[]`; merges adjacent same-node regions |
| `memblock_remove(base, size)` | cut RAM out; splits and trims regions |
| `memblock_reserve(base, size)` | claim a range in `reserved[]`; never reaches the buddy |
| `memblock_phys_alloc(size, align)` | allocate, return a physical address (top-down, any node) |
| `memblock_alloc(size, align)` | allocate, return a virtual address (wraps `alloc_try_nid`) |
| `memblock_alloc_try_nid(size, align, min, max, nid)` | node-aware; falls back to any node unless `exact_nid` |
| `memblock_alloc_low(size, align)` | confined below `ARCH_LOW_ADDRESS_LIMIT` (0xffffffff) |
| `memblock_alloc_or_panic(size, align)` | must-succeed variant; panics naming the caller |

Search lives in `memblock_find_in_range_node()` (mm/memblock.c): candidates start at `PAGE_SIZE` (page 0 is never handed out), the end is `memblock.current_limit` when the caller passes `MEMBLOCK_ALLOC_ACCESSIBLE` (`MEMBLOCK_ALLOC_ANYWHERE` means no ceiling), and the direction switch picks `__memblock_find_range_top_down()` -- the default, which takes the highest aligned gap and keeps legacy low memory untouched -- or `__memblock_find_range_bottom_up()`, which fills from the first free byte. Direction is sticky state set by `memblock_set_bottom_up()`; x86 flips it on when `movable_node` is on the command line. The flags for each request come from `choose_memblock_flags()`: `MEMBLOCK_MIRROR` when the platform reports mirrored memory, and on failure the request is retried without the flag (with a rate-limited warning). Every allocation is `memblock_reserve()`d internally, traced for kmemleak (unless `MEMBLOCK_ALLOC_NOLEAKTRACE`, used by high-volume callers like `early_pgtable_alloc()`), and passed through `accept_memory()` so TDX/SEV-SNP guests accept the pages before use. Calling any of this after slab is up trips `WARN_ON_ONCE(slab_is_available())`, because `memblock_discard()` may already have freed the arrays.

## 5. Firmware maps, reservations, and the mem= clamp

On x86 the bootloader fills the E820 table inside `boot_params` (the zeropage, per the x86 boot protocol); `e820__memblock_setup()` adds the `E820_TYPE_RAM` ranges with `memblock_add()`. Device-tree ports do the same from `memory` nodes, and the EFI stub converts `GetMemoryMap()` output before ExitBootServices. The `mem=` parameter is applied before most consumers run: `parse_memopt()` calls `e820__range_remove()`, deleting RAM above the requested size (memblock later offers `memblock_enforce_memory_limit()` / `memblock_cap_memory_range()` for other clamping paths), and `memmap=` splices in exact ranges. `setup_arch()` then reserves everything that must survive: the kernel image (`memblock_reserve_kern(_text.._end)`), the initrd whose physical address and size the bootloader left in `hdr.ramdisk_image`/`hdr.ramdisk_size` (`early_reserve_initrd()`), BIOS areas via `reserve_bios_regions()` (including the Extended BIOS Data Area) plus the first 64 KiB -- a low-memory corruption guard that also keeps L1TF from leaking page 0 -- ACPI tables, and DT `reserved-memory` nodes. Early page tables on x86-64 come first from the BRK area (`early_alloc_pgt_buf()` via `extend_brk()`), and `alloc_low_pages()` falls back to `memblock_phys_alloc_range(PMD_SIZE, PMD_SIZE, ...)` for the direct map once the BRK budget is exhausted (or immediately when `memmap=` overlaps it, disabling `can_use_brk_pgt`). Everything else early -- per-cpu areas, NUMA node maps, sparse vmemmap -- is a memblock allocation, usually node-aware.

## 6. The handoff: memblock_free_all()

`free_area_init()` sizes zones and `struct page` arrays from the memblock ranges (this is the buddy's own metadata bill). Then `mem_init()` calls `memblock_free_all()`, which trims unused memmap (`free_unused_memmap()`), resets `managed_pages` accounting, and walks `for_each_free_mem_range()` -- memory minus reserved -- calling `__free_pages_core()` to feed each page-range into the buddy free lists, finally adding the count via `totalram_pages_add()`. Reservations are honored forever: early allocations stay out of the buddy unless explicitly `memblock_free()`d (the initrd is a common case, after unpacking). With `!CONFIG_ARCH_KEEP_MEMBLOCK` the region arrays are then released by `memblock_discard()`; keeping memblock around (for `memblock_is_memory()` style queries and the debugfs view) costs those arrays. Debugfs exposes `/sys/kernel/debug/memblock/` with `memory`, `reserved` and, on some architectures, `physmem` region dumps via the `memblock_init_debugfs()` initcall; the `memblock=debug` kernel parameter additionally makes every allocation print itself (`memblock_dbg()`) and triggers `memblock_dump_all()`.

## 7. From bootmem to memblock

Early kernels had no allocator at all -- just a global pointer to the single free block handed to `start_kernel()` (LWN, "A quick history of early-boot memory allocators"). That became **bootmem**: a one-bit-per-page bitmap with first-fit scans that scaled poorly on big NUMA machines. The **LMB** allocator (imported from PPC/PA-RISC, "logical memory blocks") was adopted by x86 in the 2.6.35 cycle ("Moving x86 to LMB"), driven by Yinghai Lu's `CONFIG_NO_BOOTMEM` patches ("The NO_BOOTMEM patches", LWN 2010), and renamed lmb -> memblock the same year so the name described the concept, not the PPC heritage. For eight years bootmem and memblock coexisted behind shims until Mike Rapoport's "mm: remove bootmem allocator" series deleted the old code -- `mm/bootmem.c` is present in the v4.19 tree and gone from v4.20 -- making memblock the single generic early allocator with thin per-arch glue (`memblock_init()`, `e820__memblock_setup()`).

## 8. Worked model: a memblock simulator in Python

The model below reimplements the core algorithm -- sorted arrays, free intervals as memory-minus-reserved, top-down/bottom-up search, node fallback, `PFN_UP`/`PFN_DOWN` rounding at handoff -- then replays a scaled-down x86 boot: a 3-range firmware map, a `mem=` clamp, the classic `setup_arch()` reservations, four early allocations (including an empty-node fallback), and `memblock_free_all()`.

```python
# Memblock simulator: firmware map -> reservations -> early allocs -> free_all.
# Free intervals = memory[] minus reserved[]; top-down or bottom-up search;
# NUMA nid fallback; PFN_UP/PFN_DOWN rounding when pages are handed off.
PAGE = 4096
mem = {"regions": []}
rsv = {"regions": []}
state = {"bottom_up": False}                       # default: top-down

def add(arr, base, size, nid):                     # sorted [base, size, nid]
    arr["regions"].append([base, size, nid])
    arr["regions"].sort()
    out = []                                       # memblock_merge_regions()
    for r in arr["regions"]:
        if out and out[-1][0] + out[-1][1] == r[0] and out[-1][2] == r[2]:
            out[-1][1] += r[1]
        else:
            out.append(r)
    arr["regions"] = out

def intervals(nid=None):                           # memory[] minus reserved[]
    out = []
    for m in mem["regions"]:
        chunks = [(m[0], m[0] + m[1], m[2])]
        for r in rsv["regions"]:                   # carve out reservations
            nxt = []
            for (s, e, n) in chunks:
                if r[0] + r[1] <= s or r[0] >= e:
                    nxt.append((s, e, n)); continue
                if r[0] > s: nxt.append((s, r[0], n))
                if r[0] + r[1] < e: nxt.append((r[0] + r[1], e, n))
            chunks = nxt
        out += chunks
    return [c for c in out if nid is None or c[2] == nid]

def alloc(size, align, nid=None):                  # memblock_alloc_try_nid()
    for want in ([nid] if nid is not None else []) + [None]:
        order = intervals(want)                    # exact nid, then fallback
        if not state["bottom_up"]:
            order = list(reversed(order))
        for (s, e, n) in order:
            lo = max(s, PAGE)                      # never hand out page 0
            a = lo // align * align if state["bottom_up"] else (e - size) // align * align
            if lo <= a and a + size <= e:
                add(rsv, a, size, n)
                return a, n
    return None, None

def free_all_chunks():
    chunks = []
    for (s, e, n) in intervals():
        start, end = -(-s // PAGE) * PAGE, e // PAGE * PAGE  # PFN_UP/PFN_DOWN
        if end > start:
            chunks.append((start, end, (end - start) // PAGE))
    return chunks

def dump(label, base, size, extra=""):
    print(("  0x%08X-0x%08X  %-26s%s" % (base, base + size - 1, label, extra)).rstrip())

print("== firmware map -> memblock_add() (e820__memblock_setup) ==")
for base, size, nid in [(0x00000000, 0x000A0000, 0), (0x00100000, 0x3FF00000, 0),
                        (0x40000000, 0x40000000, 1)]:
    add(mem, base, size, nid)
    dump("RAM node %d" % nid, base, size)

print("== mem=0x70000000 (parse_memopt -> e820__range_remove) ==")
was = sum(r[1] for r in mem["regions"])
for r in mem["regions"]:                           # clamp: nothing above limit
    if r[0] + r[1] > 0x70000000:
        r[1] = max(0, 0x70000000 - r[0])
mem["regions"] = [r for r in mem["regions"] if r[1]]
print("  memory: %d regions, %d MiB total (was %d MiB)"
      % (len(mem["regions"]), sum(r[1] for r in mem["regions"]) >> 20, was >> 20))

print("== setup_arch() reservations ==")
for base, size, label in [(0x00000000, 0x00010000, "first 64 KiB (BIOS)"),
                          (0x0009FC00, 0x00000400, "EBDA"),
                          (0x00100000, 0x01400000, "kernel image 20 MiB"),
                          (0x3F000000, 0x00800000, "initrd 8 MiB")]:
    add(rsv, base, size, 0)
    dump(label, base, size)

print("== early allocations ==")
a, n = alloc(0x100000, 0x1000)
print("  memblock_phys_alloc(1 MiB)             -> 0x%08X node %d (top-down)" % (a, n))
a, n = alloc(0x1000000, 0x1000, nid=0)
print("  memblock_alloc_try_nid(16 MiB, node 0) -> 0x%08X node %d" % (a, n))
state["bottom_up"] = True                          # x86: movable_node cmdline
a, n = alloc(0x200000, 0x1000, nid=1)
print("  set_bottom_up(True) [movable_node]")
print("  memblock_alloc_try_nid(2 MiB, node 1)  -> 0x%08X node %d (bottom-up)" % (a, n))
a, n = alloc(0x100000, 0x1000, nid=2)
print("  memblock_alloc_try_nid(1 MiB, node 2)  -> 0x%08X node %d (empty node, fallback)" % (a, n))

print("== memblock_free_all() -> buddy handoff ==")
total = 0
for (s, e, pages) in free_all_chunks():
    total += pages
    print("  0x%08X-0x%08X  %7d pages" % (s, e - 1, pages))
print("  handed to buddy: %d pages (%d MiB)" % (total, total * PAGE >> 20))
print("  still reserved:  %d KiB in %d regions"
      % (sum(r[1] for r in rsv["regions"]) >> 10, len(rsv["regions"])))
```

Real output (byte-identical across two reruns):

```text
== firmware map -> memblock_add() (e820__memblock_setup) ==
  0x00000000-0x0009FFFF  RAM node 0
  0x00100000-0x3FFFFFFF  RAM node 0
  0x40000000-0x7FFFFFFF  RAM node 1
== mem=0x70000000 (parse_memopt -> e820__range_remove) ==
  memory: 3 regions, 1791 MiB total (was 2047 MiB)
== setup_arch() reservations ==
  0x00000000-0x0000FFFF  first 64 KiB (BIOS)
  0x0009FC00-0x0009FFFF  EBDA
  0x00100000-0x014FFFFF  kernel image 20 MiB
  0x3F000000-0x3F7FFFFF  initrd 8 MiB
== early allocations ==
  memblock_phys_alloc(1 MiB)             -> 0x6FF00000 node 1 (top-down)
  memblock_alloc_try_nid(16 MiB, node 0) -> 0x3E000000 node 0
  set_bottom_up(True) [movable_node]
  memblock_alloc_try_nid(2 MiB, node 1)  -> 0x40000000 node 1 (bottom-up)
  memblock_alloc_try_nid(1 MiB, node 2)  -> 0x01500000 node 0 (empty node, fallback)
== memblock_free_all() -> buddy handoff ==
  0x00010000-0x0009EFFF      143 pages
  0x01600000-0x3DFFFFFF   248320 pages
  0x3F800000-0x3FFFFFFF     2048 pages
  0x40200000-0x6FEFFFFF   195840 pages
  handed to buddy: 446351 pages (1743 MiB)
  still reserved:  49217 KiB in 6 regions
```

Reading it interview-first: the 16 MiB node-0 request lands at `0x3E000000`, *below* the initrd, because top-down search walks free gaps from the highest end and the initrd reservation splits node 0's big region; the empty-node fallback lands low (`0x1500000`) because the bottom-up direction -- sticky, like `movable_node` in real kernels -- is still in effect, so it fills the first gap above the kernel image. The buddy receives only the memory-minus-reserved page counts (446,351 pages here); the reserved 49,217 KiB, including every early allocation, never reaches it.

## References

All URLs below were probed with curl and returned HTTP 200.

- Boot time memory management, kernel documentation (memblock overview, memory/reserved/physmem types, INIT_MEMBLOCK_* sizing): https://docs.kernel.org/core-api/boot-time-mm.html
- mm/memblock.c (kernel source: find_in_range_node, alloc_range_nid, double_array, free_all, debugfs, `memblock=debug`): https://raw.githubusercontent.com/torvalds/linux/master/mm/memblock.c
- include/linux/memblock.h (structs, enum memblock_flags, MEMBLOCK_ALLOC_* constants, inline wrappers): https://raw.githubusercontent.com/torvalds/linux/master/include/linux/memblock.h
- M. Rapoport, "A quick history of early-boot memory allocators", LWN (July 2018): https://lwn.net/Articles/761215/
- J. Corbet, "The NO_BOOTMEM patches", LWN (April 2010): https://lwn.net/Articles/382559/
- J. Corbet, "Moving x86 to LMB", LWN (May 2010): https://lwn.net/Articles/387083/
- "mm: remove bootmem allocator" (patch series announcement, LWN, 2018): https://lwn.net/Articles/764807/
- bootmem presence/absence proof: https://raw.githubusercontent.com/torvalds/linux/v4.19/mm/bootmem.c (HTTP 200) vs https://raw.githubusercontent.com/torvalds/linux/master/mm/bootmem.c (HTTP 404)
- Kernel command line parameters (`mem=`, `memmap=`, `movable_node`, `memblock=debug`): https://docs.kernel.org/admin-guide/kernel-parameters.html
- x86 boot protocol (boot_params zeropage, E820 table, ramdisk_image fields): https://docs.kernel.org/arch/x86/boot.html
- arch/x86/kernel/setup.c (kernel image, initrd, `reserve_bios_regions()`, `memblock_reserve(0, SZ_64K)`): https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/kernel/setup.c
- arch/x86/mm/init.c (`early_alloc_pgt_buf()`, `alloc_low_pages()` BRK-then-memblock fallback): https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/mm/init.c
