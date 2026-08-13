# iomap

**iomap** is a generic I/O mapping framework in the Linux kernel that provides
a unified interface for mapping logical file offsets to physical storage
locations. It replaces the legacy buffer-head-based I/O path for filesystems
that adopt it, offering cleaner abstractions for buffered I/O, direct I/O,
FIEMAP, and file-backed memory (DAX).

> **Introduced:** Linux 4.8 (initial direct I/O support)  
> **Expanded:** Linux 5.x+ (buffered write, readahead, FIEMAP)  
> **Key files:** `fs/iomap/`, `include/linux/iomap.h`

---

## Why iomap Exists

The traditional Linux I/O path relies on `struct buffer_head` to represent
disk blocks. This design has limitations:

1. **Buffer heads are tied to block-device semantics** — awkward for
   extent-based filesystems (XFS, ext4, btrfs).
2. **Buffered and direct I/O use different code paths** — duplicated logic.
3. **DAX (direct access)** needs yet another path for persistent memory.
4. **FIEMAP** (`ioctl` to map file extents) required filesystem-specific code.

iomap solves these by introducing `struct iomap` — a generic description of a
mapped region — and providing shared implementations for all I/O types.

### Before and After iomap

```
BEFORE (buffer_head):
  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
  │ Buffered I/O │     │  Direct I/O  │     │    DAX       │
  │ get_block()  │     │ get_block()  │     │ get_block()  │
  └──────┬──────┘     └──────┬───────┘     └──────┬───────┘
         │                   │                     │
         ▼                   ▼                     ▼
  ┌──────────────────────────────────────────────────────┐
  │              buffer_head / block I/O                  │
  └──────────────────────────────────────────────────────┘

AFTER (iomap):
  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
  │ Buffered I/O │     │  Direct I/O  │     │    DAX       │
  └──────┬──────┘     └──────┬───────┘     └──────┬───────┘
         │                   │                     │
         ▼                   ▼                     ▼
  ┌──────────────────────────────────────────────────────┐
  │                    iomap core                         │
  │   iomap_apply() / iomap_iter()                       │
  ├──────────────────────────────────────────────────────┤
  │           Filesystem iomap_ops                       │
  │   .iomap_begin()  /  .iomap_end()                   │
  └──────────────────────────────────────────────────────┘
```

---

## Core Data Structures

### `struct iomap`

This is the central structure — a description of a contiguous mapped region:

```c
struct iomap {
    u64             addr;       /* physical start (or IOMAP_NULL_ADDR for holes) */
    loff_t          offset;     /* file offset of the mapping */
    u64             length;     /* length of the mapping */
    u16             type;       /* IOMAP_* type */
    u16             flags;      /* IOMAP_F_* flags */
    struct block_device *bdev;  /* block device for I/O */
    struct dax_device *dax_dev; /* DAX device (if applicable) */
    void            *inline_data; /* small data embedded in inode */
    /* ... */
};
```

#### Mapping Types

| Type | Meaning |
|------|---------|
| `IOMAP_MAPPED` | Data is mapped to physical blocks |
| `IOMAP_UNWRITTEN` | Allocated but not yet written (preallocation) |
| `IOMAP_HOLE` | No allocation; read zeros |
| `IOMAP_DELALLOC` | Delayed allocation (buffered write pending) |
| `IOMAP_INLINE` | Data stored inline in the inode |

#### Mapping Flags

| Flag | Meaning |
|------|---------|
| `IOMAP_F_NEW` | Newly allocated extent |
| `IOMAP_F_DIRTY` | Needs writeback |
| `IOMAP_F_SHARED` | Shared extent (reflink/CoW) |
| `IOMAP_F_BUFFER_HEAD` | Legacy buffer_head compatibility |
| `IOMAP_F_MERGED` | Merged with adjacent mapping |
| `IOMAP_F_ZONE_APPEND` | Use zone append for writes (ZNS SSDs) |

### `struct iomap_ops`

Filesystem implements this to provide mappings:

```c
struct iomap_ops {
    int (*iomap_begin)(struct inode *inode, loff_t pos, loff_t length,
                       unsigned flags, struct iomap *iomap,
                       struct iomap *srcmap);
    int (*iomap_end)(struct inode *inode, loff_t pos, loff_t length,
                     ssize_t written, unsigned flags,
                     struct iomap *iomap);
};
```

- `iomap_begin`: Called before I/O; fills in the `iomap` for the given range.
- `iomap_end`: Called after I/O; allows cleanup (e.g., transaction commits).

---

## The Iteration Model: `iomap_iter()`

Modern iomap (Linux 6.0+) uses an iterator pattern. Filesystems call
`iomap_iter()` which handles the loop over contiguous mappings:

```c
int xfs_file_buffered_write(struct kiocb *iocb, struct iov_iter *from)
{
    struct iomap_iter iter = {
        .inode   = iocb->ki_filp->f_inode,
        .pos     = iocb->ki_pos,
        .len     = iov_iter_count(from),
        .flags   = IOMAP_WRITE,
    };
    ssize_t ret;

    while ((ret = iomap_iter(&iter, &xfs_iomap_ops)) > 0) {
        iter.processed = iomap_write_iter(&iter, from);
    }

    return ret ? ret : iter.pos - iocb->ki_pos;
}
```

The iterator calls `iomap_begin()` and `iomap_end()` automatically, simplifying
filesystem code.

### Legacy `iomap_apply()`

Older code uses `iomap_apply()`, which takes callback functions:

```c
iomap_apply(inode, pos, length, IOMAP_WRITE, ops, &ctx,
            iomap_write_actor);
```

This model is being phased out in favor of `iomap_iter()`.

---

## Buffered I/O

iomap provides shared implementations for buffered reads and writes.

### Buffered Read Path

```
File read request
    │
    ▼
generic_file_read_iter()
    │
    ▼
iomap_readahead() / iomap_read_folio()
    │
    ├── iomap_iter() → filesystem .iomap_begin()
    │       returns: mapping type, physical addr, length
    │
    ├── For MAPPED: submit bio to read from disk into folio cache
    ├── For HOLE: zero the folio range
    ├── For UNWRITTEN: zero (data not yet written)
    ├── For DELALLOC: zero (no on-disk data yet)
    │
    └── iomap_iter() → filesystem .iomap_end()
```

### Buffered Write Path

Buffered writes are more complex because they involve delayed allocation:

```
File write request
    │
    ▼
iomap_write_iter()
    │
    ├── iomap_iter() → .iomap_begin() with IOMAP_WRITE
    │       Filesystem may return:
    │       - IOMAP_DELALLOC: mark page dirty, allocate later
    │       - IOMAP_MAPPED:   write directly to allocated block
    │
    ├── For DELALLOC:
    │       Grab folio, copy user data, mark dirty
    │       (actual allocation happens at writeback time)
    │
    └── iomap_iter() → .iomap_end()
```

### Writeback

When dirty pages are flushed:

```
writeback → iomap_writepages() → iomap_writepage_map()
    │
    ├── Allocate blocks for DELALLOC ranges
    ├── Issue bios for dirty data
    └── Clear folio dirty bits on completion
```

---

## Direct I/O

Direct I/O bypasses the page cache, reading/writing directly from/to storage.

### Direct I/O Path

```c
/* Simplified direct read */
iomap_dio_rw(iocb, from, &xfs_iomap_ops, &xfs_dio_write_ops, 0);
```

```
Direct I/O request
    │
    ▼
iomap_dio_rw()
    │
    ├── iomap_iter() → .iomap_begin()
    │
    ├── For each mapping:
    │   ├── MAPPED:   build bio, submit to block layer
    │   ├── HOLE:     (read) zero-fill; (write) allocate + write
    │   ├── UNWRITTEN: (read) zero-fill; (write) convert to written
    │   └── DELALLOC:  allocate first, then I/O
    │
    ├── Wait for all bios to complete
    │
    ├── iomap_iter() → .iomap_end()
    │
    └── Return bytes transferred
```

### Alignment Requirements

Direct I/O requires alignment to logical block size:

```
CONFIG_IMA_DIO=y   # Integrity Measurement Architecture support for DIO

Alignment:
  offset % logical_block_size == 0
  length % logical_block_size == 0
  user buffer aligned to logical_block_size (for O_DIRECT)
```

### AIO / io_uring Integration

iomap direct I/O supports asynchronous completion:

```c
/* Submit async DIO */
struct iomap_dio *dio = iomap_dio_rw(iocb, from, ops, dio_ops,
                                       IOMAP_DIO_PARTIAL);
if (IS_ERR_OR_NULL(dio))
    return PTR_ERR_OR_ZERO(dio);

/* Completion via kiocb callback or io_uring CQE */
```

---

## FIEMAP Support

FIEMAP is an `ioctl` that maps file offsets to physical disk locations. iomap
provides a shared implementation:

```bash
# User-space tool to view file extents
filefrag -v /path/to/file

# Output example:
# ext: logical_offset  physical_offset  length  flags
#   0:        0..    4095:     10240..    14335:      4096
#   1:     4096..    8191:     20480..    24575:      4096
```

### iomap FIEMAP Implementation

```c
int iomap_fiemap(struct inode *inode, struct fiemap_extent_info *fieinfo,
                 u64 start, u64 len, const struct iomap_ops *ops)
{
    /* Iterates over mappings, fills in fiemap extents */
    /* Handles: MAPPED, UNWRITTEN, HOLE (as FIEMAP_EXTENT_UNWRITTEN, etc.) */
}
```

Filesystem registers this in `inode_operations`:

```c
static const struct inode_operations xfs_inode_operations = {
    .fiemap     = iomap_fiemap,
    /* ... */
};
```

### FIEMAP Extent Flags

| Flag | Meaning |
|------|---------|
| `FIEMAP_EXTENT_LAST` | Final extent in the file |
| `FIEMAP_EXTENT_UNWRITTEN` | Preallocated, no data |
| `FIEMAP_EXTENT_SHARED` | Shared with another file (reflink) |
| `FIEMAP_EXTENT_MERGED` | Merged with adjacent extent |
| `FIEMAP_EXTENT_ENCODED` | Encoded/inline data |

---

## Seek Data/Hole

iomap also provides `seek_data`/`seek_hole` support for finding data and hole
regions:

```bash
# Find next data region from offset 0
lseek(fd, 0, SEEK_DATA)

# Find next hole from offset 0
lseek(fd, 0, SEEK_HOLE)
```

Implementation:

```c
loff_t iomap_seek_data(struct inode *inode, loff_t offset,
                       const struct iomap_ops *ops);
loff_t iomap_seek_hole(struct inode *inode, loff_t offset,
                       const struct iomap_ops *ops);
```

---

## DAX (Direct Access) Integration

DAX bypasses the page cache entirely, mapping persistent memory directly into
user address spaces. iomap is the foundation:

```
User mmap() on DAX file
    │
    ▼
dax_iomap_fault()
    │
    ├── iomap_iter() → .iomap_begin()
    │       Returns: type=MAPPED, dax_dev set
    │
    ├── Insert PTE mapping directly to persistent memory
    │
    └── iomap_iter() → .iomap_end()
```

Key DAX + iomap functions:

```c
vm_fault_t dax_iomap_fault(struct vm_fault *vmf, ...);
int dax_iomap_pfn(struct iomap *iomap, ...);
```

---

## Filesystems Using iomap

| Filesystem | Status | Notes |
|-----------|--------|-------|
| **XFS** | Full iomap | Primary adopter; most complete integration |
| **ext4** | Partial iomap | Direct I/O uses iomap; buffered uses buffer_heads |
| **btrfs** | Experimental | iomap-based DIO in progress |
| **FUSE** | Yes | virtio-fs uses iomap for DIO |
| **NFSD** | Yes | iomap for export operations |
| **erofs** | Yes | Read-only filesystem |

### XFS iomap Operations

```c
const struct iomap_ops xfs_read_iomap_ops = {
    .iomap_begin = xfs_file_iomap_begin,
    .iomap_end   = xfs_file_iomap_end,
};

const struct iomap_ops xfs_write_iomap_ops = {
    .iomap_begin = xfs_file_iomap_begin,
    .iomap_end   = xfs_buffered_write_iomap_end,  /* transaction handling */
};
```

---

## Kernel Config

```
CONFIG_FS_IOMAP=y          # Core iomap library
CONFIG_XFS_FS=y            # XFS (full iomap user)
CONFIG_EXT4_FS=y           # ext4 (partial iomap user)
CONFIG_FS_DAX=y            # DAX support
CONFIG_DAX_DRIVER=y        # DAX device drivers
```

---

## Performance Considerations

| Aspect | Impact |
|--------|--------|
| **Extent merging** | iomap merges adjacent mappings to reduce bio count |
| **Folio batching** | Modern iomap uses folios for larger contiguous I/O |
| **Zero-copy DIO** | Pin user pages, map directly to bio vectors |
| **DAX** | Eliminates page cache overhead for persistent memory |
| **Writeback coalescing** | `iomap_writepages()` merges dirty ranges |

---

## Relation to Other Subsystems

- **iomap** is a *library* used by filesystems, not a filesystem itself.
- **buffer_head** is the legacy alternative; iomap is replacing it.
- **[DAX](/kernel/filesystems/dax)** depends on iomap for persistent memory mapping.
- **[io_uring](/kernel/io)** async I/O integrates with iomap direct I/O.
- **[Block layer](/kernel/block)** receives bios built by iomap.
- **[Folio](/kernel/memory/folios)** is the modern page-cache unit used by iomap.

---

## Debugging iomap Issues

### Common iomap Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `EIO` on write | Block allocation failure | Check disk space, filesystem errors |
| `ENOSPC` | No free extents | Defragment filesystem |
| Stale data after write | Writeback not flushed | Call fsync() or wait for writeback |
| DAX page fault | Misaligned access | Check DAX alignment requirements |
| Corrupted FIEMAP | Filesystem corruption | Run fsck |

### Tracing iomap Operations

```bash
# Trace iomap function calls
sudo trace-cmd record -p function -l iomap_* sleep 5
sudo trace-cmd report

# Trace specific iomap operations
echo 1 > /sys/kernel/debug/tracing/events/iomap/iomap_iter/enable
cat /sys/kernel/tracing/trace_pipe

# Use bpftrace to trace iomap
sudo bpftrace -e 'k:iomap_iter { @[comm, kstack] = count(); }'

# Trace copy-up operations in overlay
sudo bpftrace -e 'k:ovl_copy_up { @[comm] = count(); }'
```

### Checking iomap Status

```bash
# View filesystem iomap configuration
cat /proc/fs/xfs/stat  # XFS-specific stats

# Check DAX status
mount | grep dax
cat /sys/fs/xfs/*/options | grep dax

# View file extent mapping
filefrag -v /path/to/file

# Example output:
# ext: logical_offset  physical_offset  length  flags
#   0:        0..    4095:     10240..    14335:      4096
#   1:     4096..    8191:     20480..    24575:      4096
```

## iomap Performance Analysis

### Profiling iomap Paths

```bash
# Profile iomap write path
perf record -g -e cycles -p $(pidof myapp) sleep 5
perf report --call-graph

# Look for iomap functions in the call graph:
# - iomap_write_iter (buffered write)
# - iomap_dio_rw (direct I/O)
# - iomap_readahead (readahead)

# Measure iomap latency
sudo bpftrace -e '
    kprobe:iomap_write_iter { @start[tid] = nsecs; }
    kretprobe:iomap_write_iter /@start[tid]/ {
        @latency = hist(nsecs - @start[tid]);
        delete(@start[tid]);
    }
'
```

### Benchmarking iomap vs buffer_head

```bash
# Compare XFS (iomap) vs ext4 (buffer_head) for direct I/O
# Both use iomap for DIO now, but the comparison shows
# the performance characteristics

# Test direct I/O throughput
fio --name=seqwrite --rw=write --bs=1M --size=1G \
    --direct=1 --numjobs=1 --runtime=30 \
    --filename=/mnt/xfs/testfile

fio --name=seqwrite --rw=write --bs=1M --size=1G \
    --direct=1 --numjobs=1 --runtime=30 \
    --filename=/mnt/ext4/testfile

# Test random I/O
fio --name=randread --rw=randread --bs=4k --size=1G \
    --direct=1 --numjobs=4 --runtime=30 \
    --filename=/mnt/xfs/testfile
```

## iomap and io_uring

iomap integrates with io_uring for high-performance async I/O:

```c
#include <liburing.h>

int main(void) {
    struct io_uring ring;
    io_uring_queue_init(256, &ring, 0);

    int fd = open("/mnt/xfs/file", O_DIRECT | O_RDWR);
    void *buf;
    posix_memalign(&buf, 4096, 4096);

    /* Submit async direct I/O via io_uring */
    struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);
    io_uring_prep_read(sqe, fd, buf, 4096, 0);
    io_uring_submit(&ring);

    /* Wait for completion */
    struct io_uring_cqe *cqe;
    io_uring_wait_cqe(&ring, &cqe);
    printf("Read %d bytes\n", cqe->res);
    io_uring_cqe_seen(&ring, cqe);

    io_uring_queue_exit(&ring);
    return 0;
}
```

### io_uring + iomap Benefits

| Feature | Traditional AIO | io_uring + iomap |
|---------|----------------|------------------|
| Setup | Complex | Simple API |
| Completion | poll/eventfd | Built-in CQE ring |
| Batching | Limited | Full batching |
| Fixed files | No | Yes (reduces fd overhead) |
| Buffer rings | No | Yes (zero-copy) |

## iomap Filesystem Implementation Guide

For filesystem developers adopting iomap:

### Step 1: Implement iomap_ops

```c
static const struct iomap_ops myfs_read_ops = {
    .iomap_begin = myfs_iomap_begin,
    .iomap_end   = myfs_iomap_end,
};

static const struct iomap_ops myfs_write_ops = {
    .iomap_begin = myfs_iomap_begin,
    .iomap_end   = myfs_write_iomap_end,  /* Handle transactions */
};
```

### Step 2: Implement iomap_begin

```c
static int myfs_iomap_begin(struct inode *inode, loff_t pos,
                            loff_t length, unsigned flags,
                            struct iomap *iomap, struct iomap *srcmap)
{
    struct myfs_inode *mi = MYFS_I(inode);
    struct myfs_extent *ext;

    /* Look up extent for this offset */
    ext = myfs_extent_lookup(mi, pos);
    if (!ext) {
        /* Hole */
        iomap->type = IOMAP_HOLE;
        iomap->addr = IOMAP_NULL_ADDR;
        iomap->length = length;
    } else {
        /* Mapped extent */
        iomap->type = IOMAP_MAPPED;
        iomap->addr = ext->physical_block << inode->i_blkbits;
        iomap->offset = ext->logical_block << inode->i_blkbits;
        iomap->length = ext->length << inode->i_blkbits;
        iomap->bdev = inode->i_sb->s_bdev;
    }

    return 0;
}
```

### Step 3: Wire Up VFS Operations

```c
static const struct inode_operations myfs_inode_ops = {
    .fiemap = iomap_fiemap,
    /* ... */
};

static const struct address_space_operations myfs_aops = {
    .readahead = iomap_readahead,
    .write_begin = iomap_write_begin,
    .write_end = iomap_write_end,
    .direct_IO = noop_direct_IO,  /* Uses iomap_dio_rw */
    /* ... */
};
```

## Further Reading

- [Kernel docs: iomap](https://www.kernel.org/doc/html/latest/filesystems/iomap.html)
- [LWN: iomap — a new block-mapping layer (2016)](https://lwn.net/Articles/677950/)
- [LWN: iomap buffered I/O (2020)](https://lwn.net/Articles/814956/)
- [Darrick Wong's iomap talk (LSFMM 2022)](https://lpc.events/event/16/contributions/1253/)
- [XFS wiki: iomap](https://xfs.wiki.kernel.org/)
- See also: [Block I/O](/kernel/block), [DAX](/kernel/filesystems/dax), [Folios](/kernel/memory/folios), [io_uring](/kernel/io)

## References

- [iomap kernel documentation](https://www.kernel.org/doc/html/latest/filesystems/iomap.html)
- [LWN: iomap — a new block-mapping layer](https://lwn.net/Articles/677950/)
- [LWN: iomap buffered I/O](https://lwn.net/Articles/814956/)
- [Linux source: fs/iomap/](https://github.com/torvalds/linux/tree/master/fs/iomap)
