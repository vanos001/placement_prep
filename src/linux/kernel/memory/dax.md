# DAX: Direct Access Without the Page Cache

> File I/O through the page cache is a beautiful optimization for slow
> block devices — and pure overhead when the "device" is persistent
> memory or CXL-attached byte-addressable memory sitting on the memory
> bus. DAX (Direct Access) lets `mmap()` map *storage* directly into a
> process address space: no page cache copy, no `struct page` per 4 KiB
> of medium (in devdax), no interrupt-driven block I/O. This page covers
> fsdax vs devdax, what happens on a DAX fault, and why DAX quietly
> became niche — and what kept it alive on the CXL path.

## The Two Worlds

```text
 traditional mmap of a file:
   fault -> xfs/ext4 -> read block into PAGE CACHE (struct page) ->
   map THAT page into userspace. Two copies exist: file block + cache.

 DAX mmap (fsdax):
   fault -> file system translates offset -> DEVICE PHYSICAL ADDRESS ->
   map device memory DIRECTLY. The page cache is bypassed entirely;
   writes go straight to the medium. 1 copy exists: the file itself.

 devdax (/dev/dax0.0):
   a character device exposing pmem as raw 2 MiB/1 GiB-aligned
   addressable ranges. No file system at all; the application
   (or a library like libpmem) manages layout. Used by DBs that
   want full control (e.g., the pmem-aware versions of SAP HANA-era
   engines) and by DPDK-style memory pools.
```

The kernel flag `-o dax` (ext4/XFS) or `dax=always` mounts switch a
filesystem into fsdax. `struct page` still exists for fsdax (needed for
rmap/GUP — "struct page backed DAX"), but the page cache is not
involved; the memory node's driver (pmem) provides the backing.

## What a DAX Fault Actually Does

On a first touch of a DAX-mapped page:

1. The file system looks up the block mapping (extent) for the offset.
2. Instead of readahead-allocating a cache page, it returns the device
   offset; the pmem driver computes the physical address.
3. The PTE is built pointing at *device* memory (via `vmf_insert_pfn_pmd`
   — PMD-level entries for 2 MiB DAX mappings, giving huge-page TLB
   behavior for free).
4. Writes by the CPU hit the medium directly; durability is the
   application's job (cache-line flushes + fences, historically
   `clwb`/`sfence` — the reason `libpmem` exists).

The subtle bits interviewers probe:

- **GUP interplay**: DAX pages get pinned by RDMA/O_DIRECT; the fsdax
  "struct page" path added a page-refcount model that mostly tracks
  the *block mapping* being stable. A truncation with long-term pins
  is the classic hazard (see the dax.md entry in GUP discussions).
- **No CoW**: reflinks/remap_file_pages-style CoW and DAX disagreed
  for years; XFS gained reflink+DAX coexistence only after the block
  mapping invalidation protocol was fixed. Snapshot-capable pmem
  filesystems are the workaround.
- **pmem vs CXL**: Intel Optane DC PMM's 2022 discontinuation removed
  the primary DAX medium. What keeps DAX relevant is CXL: type-3
  (memory) devices expose byte-addressable ranges, and CXL.mem hot
  path wants the same "map it, don't copy it" treatment — devdax-style
  allocation is the low-friction path for CXL memory pools (see
  [CXL memory pooling](./cxl.md)).

## When NOT to DAX

| Situation | Why plain page cache wins |
|---|---|
| Read-mostly data shared by many processes | page cache amortizes one copy across everyone; DAX mmap is per-process VA work too |
| Streaming large sequential reads | readahead + huge folios in the cache are already near-linear |
| Need page-granted durability semantics | fsync machinery is well-trodden; DAX durability is app-managed |
| Memory below RAM-bus latency | copying from a slow device to DRAM cache costs little relative to app work |

DAX is for *fast non-DRAM* memory where a copy is measurable — the
inverse condition of spinning disks.

## Worked Demo: Copy Elimination Accounting

The demo compares a 4 KiB-page cached read path vs a DAX path with a
stated cost model (DRAM copy bandwidth vs interconnect read), then
computes the break-even medium latency where DAX stops paying.

```python
# Cost model: cached read (device->DRAM copy + DRAM->user copy on
# first touch) vs DAX (device read directly on fault).
# Assumptions: 4 KiB granularity; CPU-side memcpy ~ 20 GB/s effective;
# device random-read costs are stated per 4 KiB block.

BLOCK = 4096
COPY_BW = 20e9            # bytes/s effective for page-cache copies

def cached_read_cost(device_ns):
    # two copies: device->cache, cache->user (4 KiB each)
    copy_s = 2 * BLOCK / COPY_BW
    return device_ns + copy_s * 1e9

def dax_read_cost(device_ns):
    return device_ns      # no copies; the fault maps device memory

print(f"{'device read (ns/4KiB)':>22} {'cached path':>12} {'dax path':>10}  winner")
for dev in (100, 500, 1000, 2000, 5000, 10000, 20000):
    c, d = cached_read_cost(dev), dax_read_cost(dev)
    w = 'dax' if d < c else 'page cache'
    print(f"{dev:>22} {c:>12.0f} {d:>10.0f}  {w}")

# break-even device latency where both cost the same
be = cached_read_cost(0) - 0   # copy cost alone = the difference
print(f"\ncopy overhead per 4 KiB block: {be:.0f} ns "
      f"(= 2 x {BLOCK/COPY_BW*1e9:.0f} ns)")
print("DAX wins whenever device_ns is within ~copy overhead of the "
      "cached path's device_ns + overhead.")
```

Real output:

```text
 device read (ns/4KiB)  cached path   dax path  winner
                   100          510        100  dax
                   500          910        500  dax
                  1000         1410       1000  dax
                  2000         2410       2000  dax
                  5000         5410       5000  dax
                 10000        10410      10000  dax
                 20000        20410      20000  dax

copy overhead per 4 KiB block: 410 ns (= 2 x 205 ns)
DAX wins whenever device_ns is within ~copy overhead of the cached path's device_ns + overhead.
```

The table reads monotonic because the copy overhead (409 ns) is
constant: DAX wins by exactly that constant whenever both paths pay
the same device cost. The real-world nuance the model hides: the
*cached* path amortizes the device read across repeated accesses
(page cache hits cost ~0), so DAX wins per-access but loses on
re-access unless the medium itself is fast enough to act as its own
cache — which byte-addressable pmem/CXL is, and NAND-based SSDs are
not. That is the precise boundary of DAX's domain.

## Interview Questions

1. What two things does DAX eliminate compared with mmap-of-file?
   (The page-cache copy and the block-I/O interrupt path; faults map
   device memory directly.)
2. Why does fsdax still have `struct page` while devdax can skip it?
   (rmap, GUP pinning, and KSM-style machinery need pages; devdax
   avoids the file layer so raw PFN mapping suffices.)
3. What breaks if an application long-term-pins a DAX page and the
   file is truncated? (The block mapping vanishes under the pin; the
   DAX pin-count model exists to defer exactly this.)
4. Why did DAX survive Optane's death? (CXL type-3 memory is
   byte-addressable and copy-averse; devdax-style pooling is the
   low-friction consumer interface.)
5. Why is DAX a poor fit for read-mostly shared files? (Page cache
   gives one shared copy for everyone; per-process DAX mappings
   duplicate VA work and lose the amortization.)

## References

- Kernel docs, *DAX* (filesystem DAX overview):
  https://docs.kernel.org/filesystems/dax.html (probed 200)
- Kernel docs, *Memory Mapping* / GUP with DAX notes:
  https://docs.kernel.org/core-api/pin_user_pages.html (probed 200)
- LWN: Corbet, J. *DAX and the filesystem boundary* series background:
  https://lwn.net/Articles/650884/ (probed 200)
- Williams, D. et al., NVDIMM/pmem driver architecture (kernel source
  `drivers/nvdimm/`): https://github.com/torvalds/linux/tree/master/drivers/nvdimm
  (probed 200)
- CXL consortium specifications (type-3 memory devices):
  https://www.computeexpresslink.org/spec-landing (bot-walls some
  automated probes; official source)

## Cross-References

- [Transparent Huge Pages](./thp.md) — PMD-level DAX faults reuse the
  same TLB arithmetic.
- [CXL memory pooling](./cxl.md) — where DAX-style mapping goes next.
- [Memory internals](../../../os/advanced/memory-internals.md) — the
  page-cache machinery DAX bypasses.
