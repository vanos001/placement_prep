# ext4 (Fourth Extended Filesystem)

## Overview

**ext4** is the default filesystem for most Linux distributions. It's a mature, high-performance journaling filesystem that evolved from ext2 → ext3 → ext4. It supports extents, delayed allocation, journaling, and scales to volumes up to 1 EB with files up to 16 TB.

## History

| Version | Year | Key Feature |
|---------|------|-------------|
| ext | 1992 | First Linux extended filesystem |
| ext2 | 1993 | POSIX permissions, no journaling |
| ext3 | 2001 | Journaling (data=ordered/writeback/journal) |
| ext4 | 2006 | Extents, delayed allocation, 64-bit, flex_bg |

## On-Disk Layout

```
┌────────────┬──────────────┬──────────────┬──────────────┬─────────────┐
│ Boot Block │ Block Group 0│ Block Group 1│ Block Group 2│    ...      │
│ (1 block)  │              │              │              │             │
└────────────┴──────────────┴──────────────┴──────────────┴─────────────┘
```

### Block Group Layout

```
┌──────────┬────────────┬──────────────┬────────────┬──────────────────┐
│Superblock│ Group Desc │ Block Bitmap │ Inode Bitmap│ Inode Table  │ Data Blocks │
│(copy)    │ (copy)     │              │             │              │             │
└──────────┴────────────┴──────────────┴─────────────┴──────────────────┘
```

**Key structures:**

| Structure | Purpose |
|-----------|---------|
| **Superblock** | Filesystem metadata: block size, inode count, mount count, state |
| **Group Descriptor** | Per-group: free blocks, free inodes, bitmap locations |
| **Block Bitmap** | 1 bit per block in group (0=free, 1=used) |
| **Inode Bitmap** | 1 bit per inode in group |
| **Inode Table** | Array of on-disk inodes |
| **Data Blocks** | Actual file data |

## Inode Structure

Each ext4 inode is **256 bytes** (default) and contains:

```c
struct ext4_inode {
    __le16 i_mode;          // File type + permissions
    __le16 i_uid;           // Owner UID (low 16 bits)
    __le32 i_size_lo;       // File size (low 32 bits)
    __le32 i_atime;         // Access time
    __le32 i_ctime;         // Change time
    __le32 i_mtime;         // Modification time
    __le32 i_dtime;         // Deletion time
    __le16 i_gid;           // Group ID (low 16 bits)
    __le16 i_links_count;   // Hard link count
    __le32 i_blocks_lo;     // 512-byte blocks used
    __le32 i_flags;         // File flags (immutable, append-only, etc.)
    __le32 i_block[15];     // Block pointers (see below)
    __le32 i_generation;    // NFS file version
    __le32 i_file_acl_lo;   // Extended attributes block
    __le32 i_size_high;     // File size (high 32 bits)
    // ... more fields up to 256 bytes
};
```

### Block Pointers: Extent Tree vs. Classic

**Classic (ext2/ext3)**: `i_block[15]` contains direct + indirect pointers.

**ext4 Extent Tree**: `i_block[15]` contains an extent tree header + up to 4 extent entries.

```
i_block[0..14]:
┌──────────────────────────────────────────────────────────┐
│ magic(0xF30A) │ entries │ max │ depth │ generation       │
│ ──────────────────────────────────────────────────────── │
│ ee_block | ee_start_lo | ee_start_hi | ee_len            │  ← Extent 1
│ ee_block | ee_start_lo | ee_start_hi | ee_len            │  ← Extent 2
│ ee_block | ee_start_lo | ee_start_hi | ee_len            │  ← Extent 3
│ ee_block | ee_start_lo | ee_start_hi | ee_len            │  ← Extent 4
└──────────────────────────────────────────────────────────┘
```

**Extent entry fields:**
- `ee_block`: Logical block number in the file
- `ee_start_lo/hi`: Physical block number on disk (48-bit)
- `ee_len`: Number of contiguous blocks (up to 32768)

For large files, the tree grows with internal nodes pointing to more extent blocks.

## Block Groups and Flex_bg

### Block Groups
The disk is divided into block groups, each containing:
- Its own bitmap copies
- Its own inode table segment
- Data blocks

**Purpose**: Keep related metadata close to data (locality).

### Flex_bg (Flexible Block Groups)
Introduced in ext4: multiple block groups share a single set of bitmaps and inode table.

```
Flex Group 0:
  Block Group 0: [bitmaps + inode table for groups 0-3] [data blocks]
  Block Group 1: [data blocks only]
  Block Group 2: [data blocks only]
  Block Group 3: [data blocks only]
```

**Benefit**: Reduces seeks for metadata reads; one read gets bitmaps for 4+ groups.

## Journaling

ext4 supports three journaling modes:

| Mode | Data | Metadata | Performance | Safety |
|------|------|----------|-------------|--------|
| **journal** | Journaled | Journaled | Slowest | Most safe |
| **ordered** | Written first | Journaled | Medium | Default; data consistent before metadata |
| **writeback** | Not journaled | Journaled | Fastest | Metadata safe, data may be stale |

```bash
# Check journaling mode
dmesg | grep "ext4"
# [    2.456] EXT4-fs (sda1): mounted filesystem with ordered data mode

# Mount with specific journaling mode
mount -o data=journal /dev/sda1 /mnt
```

## Delayed Allocation

ext4 delays allocating actual disk blocks until the data is flushed to disk (writeback). This allows:
- Better block allocation decisions (knowing the full write size)
- Reduced fragmentation
- Fewer partial writes

**Risk**: More data can be lost on crash (data in memory but not yet allocated).

## Special Features

### Inline Data
Small files (< ~60 bytes) store data directly in the inode, avoiding a separate data block.

### bigalloc
Clusters multiple blocks (e.g., 16 × 4 KB = 64 KB) into one allocation unit. Reduces bitmap size for very large volumes but increases internal fragmentation.

### Project Quotas
Limit disk usage per project (not just per user/group).

### Metadata Checksums
CRC32 checksums on metadata structures (inodes, directory entries, bitmaps) for corruption detection.

```bash
# Enable metadata checksums
mkfs.ext4 -O metadata_csum /dev/sda1
```

## Useful Commands

```bash
# Create ext4 filesystem
mkfs.ext4 -L "mydata" -b 4096 /dev/sdb1

# Tune parameters
tune2fs -l /dev/sda1                # Show superblock info
tune2fs -c 30 -i 7d /dev/sda1       # Force fsck every 30 mounts or 7 days
tune2fs -m 1 /dev/sda1              # Reserve 1% for root (default 5%)

# Debug/repair
e2fsck -f /dev/sda1                 # Force filesystem check
debugfs /dev/sda1                   # Interactive filesystem debugger
dumpe2fs /dev/sda1                  # Dump all metadata

# Defragment
e4defrag /dev/sda1                  # Online defragmentation
```

## Interview Questions

**Q1: What is the difference between ext3 and ext4?**

ext4 adds: extent-based allocation (replaces indirect blocks), delayed allocation, 64-bit support, flex_bg (shared bitmaps), metadata checksums, inline data, and support for up to 1 EB volumes and 16 TB files. ext3 uses indirect block pointers and has a 16 TB volume / 2 TB file limit.

**Q2: What does `data=ordered` mean in ext4?**

In ordered mode (the default), file data is written to disk **before** the corresponding metadata is committed to the journal. This ensures that after a crash, the journal replay won't make metadata point to garbage data. It's a middle ground between `journal` (slowest, most safe) and `writeback` (fastest, metadata safe but data may be inconsistent).

**Q3: What is delayed allocation and why is it useful?**

Delayed allocation defers block allocation until data is flushed to disk (up to 30-60 seconds). This lets ext4 see the full extent of a write and allocate contiguous blocks, reducing fragmentation. The risk is that more data can be lost on a crash since it exists only in memory.

**Q4: How many block pointers fit in an ext4 inode with extent tree?**

The inode has 60 bytes (15 × 4 bytes) for `i_block[]`. With extent tree, this holds a 12-byte header + 4 × 12-byte extent entries = 4 extents, each covering up to 32768 blocks. So directly addressable: 4 × 32768 × 4 KB ≈ 512 MB without indirection. Larger files need internal tree nodes.

**Q5: Why does ext4 keep copies of the superblock in each block group?**

If the primary superblock is corrupted, the copies can be used for recovery. Not every group has a copy — only groups 0, 1, and powers of 3, 5, 7 (sparse superblock). This saves space while still providing redundancy.

## Common Mistakes

- Confusing ext4's 256-byte inode with ext2's 128-byte inode — ext4 uses extra space for extended attributes, nanosecond timestamps, and extent tree
- Thinking delayed allocation is unsafe — `data=ordered` mode ensures data reaches disk before metadata
- Not realizing that `tune2fs -m 0` can be used to reclaim reserved space on non-root partitions
- Assuming ext4 can't handle SSDs well — ext4 supports TRIM (`discard` mount option or `fstrim`)

## Summary

- ext4 is the default Linux filesystem, evolved from ext2/ext3
- Uses extent-based allocation with up to 48-bit physical block addressing
- Block groups with bitmaps, inode tables, and data blocks
- Three journaling modes: journal, ordered (default), writeback
- Delayed allocation reduces fragmentation
- Flex_bg, metadata checksums, inline data, and bigalloc are modern additions
- Scales to 1 EB volumes, 16 TB files, and billions of inodes

## Cross-References

- [File Concepts](file-concepts.md) — inodes and file types
- [Disk Allocation](disk-allocation.md) — extent vs. indexed allocation
- [Free Space Management](free-space.md) — bitmaps and block groups
- [Journaling](journaling.md) — crash consistency mechanisms
- [VFS](vfs.md) — how ext4 plugs into the kernel


## Cross References

- [Journaling](journaling.md)
- [VFS](vfs.md)
- [Disk Allocation](disk-allocation.md)
