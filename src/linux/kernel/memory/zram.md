# zram

`zram` is a compressed, in-RAM block device driver in the Linux kernel (`drivers/block/zram/`). It exposes a `/dev/zramN` device that can be used as a swap target, a `tmpfs` backend, or a generic block device. Unlike swap-on-disk, a zram device's backing store is a slab of compressed pages in physical RAM, so writes fill memory but consume it at the (typically 3×–5×) compression ratio of the workload.

## Why zram Exists

The original 2010 motivation (Nitin Gupta's `compcache`) was: netbooks with 1 GB of RAM and slow spinning disks spent seconds in direct reclaim. Compressing cold anonymous pages in memory lets the system satisfy the same workload with less physical RAM, at the cost of CPU for compression/decompression. Modern phones, embedded boards, and small cloud instances face the same constraint.

In 2013, zram became the default swap backend for Chrome OS. In 2014, it landed in Android's `init.rc`. By 2020, the LXD/LXC ecosystem offered zram-backed `tmpfs` for fast ephemeral storage, and Fedora's installer offered a 50%-of-RAM zram swap by default.

## Device Lifecycle

A zram device is created by writing the number of devices (max 32, default 1) to `/sys/block/zram/` controls:

```bash
# Create device /dev/zram0 (or use the auto-created one)
modprobe zram num_devices=1

# Reset before use (also clears statistics)
echo 1 > /sys/block/zram/0/reset

# Choose a compressor: lzo, lz4, zstd, deflate
echo zstd > /sys/block/zram/0/comp_algorithm

# Set the disksize (capped by available RAM, but the device is sparse)
echo 2G > /sys/block/zram/0/disksize

# Optionally set a memory limit for the compressed pool
echo 1G > /sys/block/zram/0/mem_limit

# Use as swap
mkswap /dev/zram0
swapon -p 100 /dev/zram0   # priority 100 > default
```

The disksize is virtual: writing 8 GB of uncompressed pages to a 1 GB zram device will store them in (at most) 1 GB of compressed RAM or evict them — depending on the `mem_limit` setting.

## Compression Algorithms

The compressor choice dominates the trade-off. As of kernel 6.10, the supported algorithms are:

| Algorithm | Codec | Throughput (MB/s, single core) | Ratio (kernel/squashfs) |
|-----------|------|--------------------------------:|------------------------:|
| lzo-rle   | Default since 4.x | 500 | 2.2× |
| lz4       | 4.0+ | 950 | 2.0× |
| lz4hc     | 4.4+ | 350 (compress), 1100 (decompress) | 2.3× |
| zstd      | 4.14+ | 80 (compress), 600 (decompress) | **2.9×** |
| deflate   | 6.x (with config) | 50 / 250 | 2.8× |
| 842       | PowerPC + select x86 | 30 / 600 | 2.1× |

`zstd` is the recommended choice for swap: it has the best compression ratio in the standard kernel `page-table` workload (a Linux 6.x bzImage compresses to 37% with zstd vs 51% with lzo) and is fast enough for swap. `lz4` is faster on both paths and preferred for very high I/O rate devices with random access patterns.

The kernel ships with the corresponding `lib/lzo/*`, `lib/lz4/`, `crypto/zstd.c`, and `lib/zlib_deflate/*` implementations. Each page (4 KB on x86_64 and ARM64; 16 KB or 64 KB on some ARM kernels) is compressed independently, so random reads and writes are O(1) per page.

## Internal Data Structures

Each zram device holds:

- A `struct zram` per device, containing an `xarray` of `struct zram_entry *` indexed by page number. The xarray was migrated from a radix tree in 5.x.
- Each `zram_entry` is the handle returned by `zs_malloc()` from the `zsmalloc` allocator (`mm/zsmalloc.c`), which packs compressed objects of varying size into 4 KB `struct page`s.
- A `table_entry` flag bit distinguishes "same-element page" (when every byte in the page is the same — a common pattern for zero pages and pages full of one byte) from a compressed entry.

`zsmalloc` is the reason zram's compression ratio exceeds 4 KB granularity: many compressed pages fit in ~300 bytes, and `zsmalloc` packs ~13 of them into one 4 KB page, eliminating the per-page internal fragmentation that `slab`/`slub` would impose.

## Swap Frontend and the Frontswap Hook

When `zram` is bound as swap, the kernel's `swap_state.c` and `swapfile.c` call into the block device. The fast path is:

```text
Reclaim path                       zram device
-----------                        ------------
shrink_folio_list()
  -> try_to_unmap()
  -> pageout()
     -> __swap_writepage()        swp_entry = encode (zram_type, idx)
        -> submit_bio(swap_bio)    -> zram_write_page()
                                      1. compress 4 KB page
                                      2. zs_malloc(cstr_size)
                                      3. update xarray[idx]
                                      4. update stats
                                      5. return 0  ← done, page is now on zram

Reclaim path on fault:
do_swap_page()
  -> swap_readpage()
     -> submit_bio                -> zram_read_page()
                                      1. xarray[idx] -> entry
                                      2. zs_map_object(entry)
                                      3. zstrm_decompress(page, src)
                                      4. zs_unmap_object(entry)
                                      5. return 0
```

There is no I/O scheduler, no NVMe driver, and no DMA: everything happens synchronously in the calling task's context.

## Memory Limit and Writeback

Three memory controls protect the system from a zram device consuming all of RAM:

- `disksize` — virtual block device size (compressed data may exceed this in pathological cases).
- `mem_limit` — maximum bytes of physical RAM the compressed pool may consume. When reached, the oldest compressed entries are evicted; the swap layer then sees an I/O error and falls back to the next swap device (if any).
- `backing_dev` (kernel 5.15+) — write cold compressed pages out to a real block device. The zram-writeback daemon (`zram-writeback` script in `tools/`) walks the `xarray` and ages out the coldest entries, similar to a swap-on-disk tiered layout.

The writeback path is enabled with:

```bash
echo /dev/sdb1 > /sys/block/zram0/backing_dev
echo huge > /sys/block/zram0/writeback      # write back pages marked "huge"
echo idle > /sys/block/zram0/               # mark all entries idle
echo 1m > /sys/block/zram0/idle             # mark entries idle for >1 min
echo huge_idle > /sys/block/zram0/writeback # write back idle huge pages
```

The `huge` flag indicates a compressed size above the page size threshold (default 3/4 page), meaning compression did not help — these are the most valuable to write out to disk.

## The same-page-filled optimization

A common case is a page where every byte is identical: zero pages, pages filled with `0xCC` in uninitialized memory, etc. zram detects this with `page_filled_value()` and stores only the fill byte and length, returning a tiny handle. The decompress path reconstructs the page with `memset()`. This optimization alone reduces the compressed pool size by 15–30% on typical desktop workloads.

## Pitfalls

1. **Setting `disksize` > physical RAM.** This makes the device advertise more capacity than RAM, which is fine because pages compress, but if the workload is incompressible (e.g., encrypted disk images, video files), the system can hit `mem_limit` and start failing writes — surfacing as `ENOSPC` from swap.
2. **Using `tmpfs` on zram without size limits.** A `tmpfs` mounted on `/dev/zram0` will fill the device like any block device, but the write-back is asymmetric: a 100 MB file written sequentially fills 100 MB / compression_ratio of zram. Once zram is full, all writes fail.
3. **Putting zram on a NUMA-confined node.** zram memory is allocated from the same node as the writing CPU by default. A 4-socket server with 1 GB zram per socket and one socket running a memory-intensive job will OOM-kill on that socket before touching the others. Bind zram devices per-node with `numa_node`.
4. **Choosing `lzo` on a CPU-bound device.** The default `lzo-rle` was selected because it has stable throughput on every CPU. On modern x86, `lz4` decompresses 2× faster with only marginally worse ratio. Switch.
5. **Forgetting `comp_algorithm` is set-before-disksize.** Once the device is sized, the algorithm is locked. Changing the algorithm requires `reset`.

## Statistics

`/sys/block/zram/0/mm_stat` reports (space-separated):

| Field | Meaning |
|------|---------|
| `orig_data_size` | Uncompressed bytes stored |
| `compr_data_size` | Compressed bytes stored |
| `mem_used_total` | Total memory used by zs_pool |
| `mem_limit`       | Configured mem_limit (bytes) |
| `mem_used_max`    | Maximum memory used historically |
| `same_pages`      | Number of same-element pages |
| `pages_compacted` | Pages successfully compressed |
| `huge_pages`      | Pages that didn't compress usefully (>3/4 page) |
| `huge_pages_since`| Counter of huge pages since reset |

The compression ratio is `orig_data_size / mem_used_total` — typically 2.5×–4× on desktop workloads and 1.5×–2× on database engines.

## Comparison to Other Compressed Memory

| Mechanism | What it compresses | When it fires | Notes |
|-----------|-------------------|---------------|-------|
| **zram** (swap) | Anonymous + file-backed pages written to swap | During reclaim, on demand | The original. Best for cold pages |
| **zswap** | Pages already on their way to disk swap | Before disk write | Cache in front of swap device |
| **zbud** | Internal allocator for zswap | (zswap only) | 2× worst-case compression; used for OOM safety |
| **z3fold** | Internal allocator for zswap | (zswap only) | 3-way packing; better density than zbud |
| **MGLRU** | Reclaims page by LRU generation | Before swap | Complementary; reduces reclaim pressure |

`zram` vs. `zswap` — the canonical question. `zswap` is a cache in front of swap-on-disk: it absorbs compressed pages and writes them out to the swap device when full, transparently. `zram` is a swap device itself: there is no disk fallback. `zswap` is preferred on systems with a real swap device; `zram` is preferred on systems without (Chrome OS, Android, embedded).

## References

- [kernel.org: zram documentation](https://docs.kernel.org/admin-guide/blockdev/zram.html)
- [LWN: "zram and zswap" (2013)](https://lwn.net/Articles/547249/)
- Nitin Gupta, "Compcache: In-memory compressed swapping" (PhD thesis, Stony Brook, 2010)
- Sergey Senozhatsky, "[zsmalloc & zram updates](https://lpc.events/)" (LPC 2017 storage talk)
- Chris Mason, "zram: writeback feature" (Linux Plumbers 2018, [commit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=9d4022d3c30391e0d6860334098b7a0e5c8c4f6e))
