# Buffer Cache

## Introduction

The buffer cache is a kernel subsystem that caches disk block contents in memory. Historically, it was the primary caching mechanism in Linux (and traditional Unix) for filesystem I/O. In modern Linux kernels (2.4+), the buffer cache has been largely merged with the page cache — disk blocks are cached as pages, and `buffer_head` structures provide metadata about those pages.

Understanding the buffer cache requires understanding its relationship to the page cache: in modern Linux, they are not separate caches but rather two views of the same data. The page cache stores data pages; `buffer_head` structures describe the block-to-page mapping for filesystems that need block-level metadata.

## Historical Context

### Evolution of Disk Caching in Linux

```mermaid
timeline
    title Linux Disk Cache Evolution
    1991 : Linux 0.01
         : Simple buffer cache for block devices
    1995 : Linux 1.2
         : Separate page cache for file data
    2000 : Linux 2.4
         : Unified page cache + buffer_heads
         : Buffer cache merged into page cache
    2004 : Linux 2.6
         : bio layer replaces buffer_head for I/O
    2018 : Linux 4.18+
         : buffer_head usage reduced
         : Folio-based page cache
    Present : Modern kernels
          : buffer_head used for metadata only
          : Data I/O via bio/iov_iter
```

### The Three Eras

1. **Pre-2.4**: Separate buffer cache (block-sized) and page cache (page-sized). Data could be duplicated in both.
2. **2.4-2.6**: Unified architecture. Buffer heads describe block-to-page mapping, but actual data lives in the page cache.
3. **Modern (4.x+)**: Further reduction of buffer_head usage. Data I/O uses `bio` structures directly. Buffer heads primarily for metadata (superblocks, inode tables, directory blocks).

## `buffer_head` Structure

### Definition

```c
/* Simplified from include/linux/buffer_head.h */
struct buffer_head {
    unsigned long b_state;          /* Buffer state flags */
    struct buffer_head *b_this_page; /* Circular list of buffers in page */
    struct page *b_page;            /* The page this buffer belongs to */
    sector_t b_blocknr;             /* Block number on disk */
    size_t b_size;                  /* Block size */
    char *b_data;                   /* Pointer to data within page */
    struct block_device *b_bdev;    /* Block device */
    bh_end_io_t *b_end_io;         /* I/O completion callback */
    void *b_private;                /* Private data for b_end_io */
    struct list_head b_assoc_buffers; /* Associated buffers (journal) */
    struct address_space *b_assoc_map; /* Mapping for association */
    atomic_t b_count;               /* Reference count */
};
```

### Key Fields

| Field | Purpose |
|-------|---------|
| `b_state` | Bit flags: `BH_Uptodate`, `BH_Dirty`, `BH_Lock`, `BH_Mapped`, etc. |
| `b_page` | The page containing this block's data |
| `b_blocknr` | Logical block number on the block device |
| `b_size` | Block size (typically 4096, but can be smaller for some filesystems) |
| `b_data` | Pointer into the page's data area where this block's data resides |
| `b_bdev` | Block device this buffer is associated with |
| `b_end_io` | Callback function called when I/O completes |

### Buffer State Flags

```c
enum bh_state_bits {
    BH_Uptodate,    /* Buffer contains valid data */
    BH_Dirty,       /* Buffer is dirty (needs writeback) */
    BH_Lock,        /* Buffer is locked for I/O */
    BH_Mapped,      /* Buffer has a disk mapping (b_blocknr valid) */
    BH_New,         /* Buffer is newly allocated */
    BH_Async_Read,  /* Async read in progress */
    BH_Async_Write, /* Async write in progress */
    BH_Delay,       /* Buffer not yet allocated on disk */
    BH_Boundary,    /* Block at boundary of contiguous extent */
    BH_Write_EIO,   /* I/O error on write */
    BH_Unwritten,   /* Allocated but not written (ext4) */
    BH_Quiet,       /* Suppress error messages */
};
```

### Buffer State Transitions

```mermaid
stateDiagram-v2
    [*] --> New: alloc_buffer_head()
    New --> Mapped: map buffer to disk block
    Mapped --> Uptodate: read from disk completes
    Uptodate --> Dirty: modify buffer contents
    Dirty --> Lock: submit for writeback
    Lock --> Uptodate: write completes
    Lock --> WriteEIO: write fails
    Dirty --> Mapped: writeback completes
    Uptodate --> [*]: brelse() / free
```

## Buffer Cache and Page Cache Relationship

### How They Connect

```mermaid
graph TB
    subgraph "Page Cache"
        PAGE["struct page<br>4096 bytes of data"]
        PC["page->mapping → address_space"]
    end
    subgraph "Buffer Heads (metadata)"
        BH1["buffer_head 1<br>block 100, size 1024"]
        BH2["buffer_head 2<br>block 101, size 1024"]
        BH3["buffer_head 3<br>block 102, size 1024"]
        BH4["buffer_head 4<br>block 103, size 1024"]
    end
    subgraph "Block Device"
        BD["/dev/sda"]
    end

    PAGE --> BH1
    PAGE --> BH2
    PAGE --> BH3
    PAGE --> BH4
    BH1 --> BD
    BH2 --> BD
    BH3 --> BD
    BH4 --> BD
```

A single 4096-byte page can hold multiple buffer heads. For a filesystem with 1024-byte blocks, one page holds 4 buffer heads, each pointing to a different disk block:

```c
/* Creating buffer heads for a page */
struct page *page = find_or_create_page(mapping, index, GFP_KERNEL);
struct buffer_head *head = page_buffers(page);  /* First buffer head */

/* Iterate through buffer heads */
struct buffer_head *bh = head;
do {
    /* bh->b_data points into the page's data area */
    /* bh->b_blocknr is the disk block number */
    /* bh->b_size is the block size (e.g., 1024) */
    bh = bh->b_this_page;  /* Next buffer in circular list */
} while (bh != head);
```

### Data Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant VFS as VFS
    participant PC as Page Cache
    participant BH as Buffer Heads
    participant BIO as bio Layer
    participant Disk as Disk

    App->>VFS: read(fd, buf, 4096)
    VFS->>PC: find_get_page(mapping, index)
    alt Cache hit (BH_Uptodate)
        PC-->>VFS: Page data ready
        VFS-->>App: copy_to_user()
    else Cache miss
        PC->>BH: Get buffer_heads for page
        BH->>BIO: Create bio for each buffer
        BIO->>Disk: Submit I/O
        Disk-->>BIO: I/O complete
        BIO-->>BH: Set BH_Uptodate
        BH-->>PC: Page uptodate
        PC-->>VFS: copy_to_user()
    end
```

## Buffer Head Operations

### Creating Buffer Heads

```c
/* Allocate buffer heads for a page */
int create_page_buffers(struct page *page, struct inode *inode,
                        unsigned long blocksize) {
    struct buffer_head *head, *bh;
    int nr;

    /* Already has buffers? */
    if (page_has_buffers(page))
        return 0;

    /* Number of blocks per page */
    nr = PAGE_SIZE / blocksize;

    /* Create circular list of buffer heads */
    head = alloc_buffer_head(GFP_NOFS);
    head->b_page = page;
    head->b_blocknr = 0;
    head->b_size = blocksize;
    head->b_data = page_address(page);

    bh = head;
    for (int i = 1; i < nr; i++) {
        bh->b_this_page = alloc_buffer_head(GFP_NOFS);
        bh = bh->b_this_page;
        bh->b_page = page;
        bh->b_size = blocksize;
        bh->b_data = head->b_data + (i * blocksize);
    }
    bh->b_this_page = head;  /* Circular */

    attach_page_buffers(page, head);
    return 0;
}
```

### Reading Blocks

```c
/* Read a block into the buffer cache */
struct buffer_head *sb_bread(struct super_block *sb, sector_t block) {
    struct buffer_head *bh;

    /* Look up in cache */
    bh = __getblk(sb->s_bdev, block, sb->s_blocksize);

    /* Already uptodate? */
    if (buffer_uptodate(bh))
        return bh;

    /* Read from disk */
    ll_rw_block(REQ_OP_READ, 1, &bh);
    wait_on_buffer(bh);

    if (buffer_uptodate(bh))
        return bh;

    brelse(bh);
    return NULL;
}
```

### Writing Dirty Buffers

```c
/* Mark a buffer as dirty */
mark_buffer_dirty(struct buffer_head *bh);

/* Write back a specific buffer */
int sync_dirty_buffer(struct buffer_head *bh) {
    int ret = 0;

    if (!buffer_dirty(bh))
        return 0;

    lock_buffer(bh);
    if (buffer_dirty(bh)) {
        bh->b_end_io = end_buffer_write_sync;
        submit_bh(REQ_OP_WRITE, bh);
        wait_on_buffer(bh);
    } else {
        unlock_buffer(bh);
    }
    return ret;
}
```

### Asynchronous I/O

```c
/* Submit async read */
void submit_bh_async(int op, struct buffer_head *bh)
{
    bh->b_end_io = end_buffer_async_read;
    set_bh_async_read(bh);
    submit_bh(op, bh);
}

/* Async completion callback */
static void end_buffer_async_read(struct buffer_head *bh, int uptodate)
{
    if (uptodate) {
        set_buffer_uptodate(bh);
    } else {
        /* Handle read error */
        clear_buffer_uptodate(bh);
    }
    unlock_buffer(bh);
    
    /* Check if all buffers in page are uptodate */
    struct page *page = bh->b_page;
    if (page_uptodate(page))
        unlock_page(page);
}
```

## bdflush / pdflush / writeback

### Historical Writeback Daemons

```mermaid
graph LR
    subgraph "Linux 2.0-2.4"
        BDF["bdflush<br>(/sbin/bdflush)"]
    end
    subgraph "Linux 2.6-3.0"
        PDF["pdflush<br>(kernel threads)"]
    end
    subgraph "Linux 3.0+"
        WB["Per-BDI writeback<br>(bdi_writeback)"]
    end
    BDF --> PDF --> WB
```

### Modern Writeback (per-BDI)

```bash
# View writeback threads
$ ps aux | grep kworker | grep flush
root   123  0.0  0.0  0  0 ?  I<  Jul21  0:00 [kworker/u8:1-flush-8:0]

# Each backing device info (BDI) has its own writeback thread
# This avoids the bottleneck of a single flusher thread

# Writeback tunables
$ sysctl vm.dirty_ratio
vm.dirty_ratio = 20

$ sysctl vm.dirty_background_ratio
vm.dirty_background_ratio = 10

$ sysctl vm.dirty_expire_centisecs
vm.dirty_expire_centisecs = 3000

$ sysctl vm.dirty_writeback_centisecs
vm.dirty_writeback_centisecs = 500
```

### Per-BDI Writeback Structure

```c
struct bdi_writeback {
    struct backing_dev_info *bdi;   /* Backing device */
    unsigned long last_old_flush;   /* Last old data flush */
    struct delayed_work dwork;      /* Delayed work for periodic flush */
    struct list_head b_dirty;       /* Dirty inodes */
    struct list_head b_io;          /* Inodes under writeback */
    struct list_head b_more_io;     /* More I/O pending */
    struct list_head b_dirty_time;  /* Dirty-time inodes */
    spinlock_t list_lock;           /* Protects the above lists */
};
```

### Writeback Triggers

Writeback is triggered by several conditions:

| Trigger | Threshold | Tunable |
|---------|-----------|---------|
| **Periodic** | Every `dirty_writeback_centisecs` (5s default) | `vm.dirty_writeback_centisecs` |
| **Dirty ratio** | `dirty_ratio`% of total RAM (20% default) | `vm.dirty_ratio` |
| **Background ratio** | `dirty_background_ratio`% of total RAM (10% default) | `vm.dirty_background_ratio` |
| **Dirty expiry** | Pages dirty for `dirty_expire_centisecs` (30s default) | `vm.dirty_expire_centisecs` |
| **Explicit sync** | `sync()`, `fsync()`, `msync()` | N/A |
| **Memory pressure** | When free memory is low | `vm.dirty_background_ratio` |

```mermaid
graph TD
    A[Dirty pages accumulate] --> B{dirty_ratio exceeded?}
    B -->|Yes| C["Direct writeback, blocking"]
    B -->|No| D{dirty_background_ratio exceeded?}
    D -->|Yes| E["Background writeback, async"]
    D -->|No| F{dirty_writeback_centisecs elapsed?}
    F -->|Yes| G[Periodic writeback]
    F -->|No| H[Continue]
```

### Writeback Decision Logic

```c
/* mm/page-writeback.c — simplified */
static void balance_dirty_pages(struct bdi_writeback *wb)
{
    unsigned long nr_dirty = global_node_page_state(NR_FILE_DIRTY);
    unsigned long nr_writeback = global_node_page_state(NR_WRITEBACK);
    unsigned long dirty_thresh;
    unsigned long bg_thresh;

    /* Calculate thresholds */
    dirty_thresh = vm_dirty_ratio * totalram_pages / 100;
    bg_thresh = vm_dirty_background_ratio * totalram_pages / 100;

    if (nr_dirty + nr_writeback > dirty_thresh) {
        /* Exceeded dirty_ratio: block and write back */
        wb_do_writeback(wb, WB_REASON_DIRTY_THREASHOLD);
    } else if (nr_dirty + nr_writeback > bg_thresh) {
        /* Exceeded background ratio: async writeback */
        wb_start_background_writeback(wb);
    }
}
```

## Buffer Cache Statistics

```bash
# View memory usage
$ free -h
              total        used        free      shared  buff/cache   available
Mem:           16Gi       4.2Gi       2.1Gi       128Mi       9.7Gi        11Gi

# 'buff/cache' includes both buffer cache and page cache

# Detailed breakdown via /proc/meminfo
$ grep -E "Buffers|Cached|SwapCached" /proc/meminfo
Buffers:          234568 kB
Cached:          9567890 kB
SwapCached:            0 kB

# 'Buffers' = buffer heads (metadata blocks)
# 'Cached'  = page cache (file data)

# Drop caches
$ echo 1 > /proc/sys/vm/drop_caches  # Free page cache only
$ echo 2 > /proc/sys/vm/drop_caches  # Free buffer cache + dentries/inodes
$ echo 3 > /proc/sys/vm/drop_caches  # Free both
```

### Cache Hit Rate Monitoring

```bash
# Monitor cache hit rate using /proc/vmstat
$ cat /proc/vmstat | grep -E "pgpgin|pgpgout|pswpin|pswpout"
pgpgin 1234567
pgpgout 2345678
pswpin 0
pswpout 0

# Calculate hit rate (approximate)
# Use cachestat BPF tool
$ sudo cachestat 1
    HITS   MISSES  DIRTIES HITRATIO   BUFFERS_MB  CACHED_MB
   12345      234     5678    98.1%         234       9567

# Or use perf
$ sudo perf stat -e 'cache-references,cache-misses' -a sleep 5
# Performance counter stats for 'system wide':
#     cache-references    12345678
#     cache-misses          234567 (1.90%)
```

### Cache Pressure

```bash
# vm.vfs_cache_pressure controls inode/dentry cache reclaim
$ sysctl vm.vfs_cache_pressure
vm.vfs_cache_pressure = 100

# Lower values: keep cache longer
# Higher values: reclaim cache more aggressively
# 0: never reclaim (OOM risk)
# 200: reclaim twice as aggressively

# For file servers with many files:
$ echo 50 > /proc/sys/vm/vfs_cache_pressure
```

## Buffer Cache vs Page Cache

| Aspect | Buffer Cache (buffer_head) | Page Cache |
|--------|---------------------------|------------|
| **Unit** | Block (512B-4KB) | Page (4KB) |
| **Caches** | Block device metadata, superblocks, journal | File data |
| **Data structure** | `buffer_head` | `page` / `folio` |
| **Modern use** | Metadata only | All file data |
| **I/O submission** | Via `bio` (or legacy `ll_rw_block`) | Via `bio` |
| **Lookup** | `(bdev, blocknr)` | `(address_space, index)` |

### The Convergence

```c
/* Modern: file data goes through page cache */
/* Buffer heads are used for: */
/* 1. Filesystem metadata (superblock, inode table, etc.) */
/* 2. Filesystems that need block-level mapping (ext4 indirect blocks) */
/* 3. Journal blocks */

/* File data: always page cache */
struct address_space *mapping = inode->i_mapping;
struct page *page = find_get_page(mapping, index);

/* Metadata: buffer cache via page cache */
struct buffer_head *bh = sb_bread(sb, block_number);
/* This finds/creates a page in the page cache for the block device,
   then returns the appropriate buffer_head within that page */
```

## Implementation Details

### Key Source Files

- **`fs/buffer.c`** — Buffer cache implementation (~3000 lines)
- **`include/linux/buffer_head.h`** — `buffer_head` structure and API
- **`mm/page-writeback.c`** — Writeback mechanisms
- **`mm/backing-dev.c`** — Backing device info and writeback threads
- **`block/bio.c`** — bio layer (replaces direct buffer_head I/O)

### Block-to-Page Mapping

```c
/* How sb_bread() works internally */
struct buffer_head *sb_bread(struct super_block *sb, sector_t block) {
    struct buffer_head *bh;

    /* __find_get_block: look up in page cache by (bdev, block) */
    bh = __find_get_block(sb->s_bdev, block, sb->s_blocksize);
    if (bh) {
        if (buffer_uptodate(bh))
            return bh;  /* Cache hit */
    } else {
        /* Create new buffer_head (may allocate page) */
        bh = __getblk(sb->s_bdev, block, sb->s_blocksize);
    }

    /* Read from disk */
    bh->b_end_io = end_buffer_read_sync;
    submit_bh(REQ_OP_READ, bh);
    wait_on_buffer(bh);
    return buffer_uptodate(bh) ? bh : NULL;
}
```

### __getblk Internal Flow

```mermaid
graph TD
    A[__getblk] --> B{Buffer in cache?}
    B -->|Yes| C{Uptodate?}
    C -->|Yes| D[Return buffer_head]
    C -->|No| E["Return buffer head, needs read"]
    B -->|No| F[Find/create page in page cache]
    F --> G[Create buffer_head for this block]
    G --> H[Link buffer_head to page]
    H --> D
```

### Folio Transition

Modern kernels are transitioning from `struct page` to `struct folio`:

```c
/* folio = page that is guaranteed to be the head of a compound page */
/* Or a single page that is not part of a compound page */

/* Old way: */
struct page *page = find_get_page(mapping, index);

/* New way: */
struct folio *folio = filemap_get_folio(mapping, index);

/* buffer_head integration with folio: */
struct buffer_head *folio_buffers(struct folio *folio)
{
    return folio->private;  /* buffer_head list stored in folio's private data */
}
```

## References

- [buffer.c source](https://github.com/torvalds/linux/blob/master/fs/buffer.c)
- [buffer_head.h header](https://github.com/torvalds/linux/blob/master/include/linux/buffer_head.h)
- [Linux kernel writeback documentation](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html
- https://lwn.net/Articles/712460/ — "Folios and the page cache"
- https://lwn.net/Articles/264459/ — "A new approach to kernel writeback"
- https://man7.org/linux/man-pages/man5/proc.5.html — /proc/meminfo
- https://www.thomas-krenn.com/en/wiki/Linux_Page_Cache_Basics

## Related Topics

- [file-ops](../filesystems/file-ops.md) — File operations use buffer cache and page cache
- [inode](../filesystems/inode.md) — Inodes use address_space for caching
- [superblock](../filesystems/superblock.md) — Superblock metadata cached via buffer heads
- [compaction](./compaction.md) — Memory compaction affects cached pages
