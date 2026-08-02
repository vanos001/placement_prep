# XFS

## Overview

**XFS** is a high-performance, 64-bit journaling filesystem originally developed by SGI in 1993 for IRIX and ported to Linux in 2001. It excels at parallel I/O, large files, and scalability. XFS is the default filesystem on RHEL/CentOS 7+ and is widely used for data-intensive workloads.

## Key Design Principles

1. **Allocation Groups (AGs)**: The disk is divided into independent regions, each with its own structures. This enables parallel allocation without global locks.
2. **B+ Tree indexing**: Both free space and directory entries use B+ trees for O(log n) operations.
3. **Extent-based allocation**: Files are tracked as runs of contiguous blocks.
4. **Delayed allocation**: Like ext4, blocks are allocated at writeback time.
5. **Online resizing**: Filesystems can grow while mounted.

## On-Disk Layout

```
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│   AG 0  │   AG 1  │   AG 2  │   AG 3  │   ...   │   AG N  │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘

Each Allocation Group:
┌──────────┬──────────────┬──────────────────────────────────┐
│ AG Header│  AG Free List│  B+ Trees │ Data Blocks          │
│ (super)  │  (B+ tree)   │ (inodes)  │                      │
└──────────┴──────────────┴──────────────────────────────────┘
```

### Allocation Group (AG)

Each AG is essentially an independent filesystem:

| Structure | Purpose |
|-----------|---------|
| AG Superblock | AG metadata, AG number, size |
| AG Free Space B+ Tree | Tracks free extents in this AG |
| Inode B+ Tree | Tracks allocated inodes |
| Inode Chunk | 64 inodes allocated together |
| Data Blocks | File data |

**Parallelism**: Threads allocating from different AGs don't contend with each other.

## B+ Tree Free Space Management

XFS uses two B+ trees per AG for free space:

1. **By-block B+ Tree**: Keys are starting block numbers, values are extent lengths
2. **By-size B+ Tree**: Keys are extent lengths, values are starting blocks

```
By-block tree:                 By-size tree:
┌────────────────────┐         ┌────────────────────┐
│ (2,5) (10,3) (20,8)│         │ (3,10) (5,2) (8,20)│
└────────────────────┘         └────────────────────┘

Block 2: 5 free blocks         Length 3 at block 10
Block 10: 3 free blocks        Length 5 at block 2
Block 20: 8 free blocks        Length 8 at block 20
```

**Allocation**: To find 4 contiguous free blocks, search the by-size tree for the smallest extent ≥ 4 → O(log n).

**Deallocation**: Remove from both trees, then re-insert with updated extents (merging with neighbors if adjacent).

## Inode Structure

XFS inodes are **256 bytes** or larger and use a B+ tree for tracking.

```
XFS inode (256 bytes):
┌────────────────────────────────────────────────┐
│ di_magic  │ di_mode │ di_uid │ di_gid          │
│ di_version│ di_format│ di_onlink│ di_nlink      │
│ di_atime  │ di_mtime │ di_ctime │ di_size       │
│ di_nblocks│ di_extsize│ di_nextents│ di_forkoff │
│ di_aformat│ di_dmevmask│ di_dmstate│ di_flags   │
│ ──────────────────────────────────────────────── │
│ Data Fork: extent entries or B+ tree root       │
│ Attribute Fork: extended attributes             │
└────────────────────────────────────────────────┘
```

### Fork Structure

Each XFS inode has two **forks**:
- **Data fork**: file data extents or B+ tree
- **Attribute fork**: extended attributes (xattrs)

For small files, extent entries are inline in the inode. For large files, the fork becomes a B+ tree (called a "bmap" tree).

## Delayed Allocation

Like ext4, XFS delays block allocation until writeback:

1. `write()` → data goes to page cache, no blocks allocated
2. Memory pressure or `fsync()` triggers writeback
3. Allocator sees the full extent of dirty data → better allocation decisions

**Result**: Reduced fragmentation compared to immediate allocation.

## Journaling (Log)

XFS uses a circular **log** (journal) for metadata consistency:

```
┌──────────────────────────────────────┐
│              XFS Log                 │
│ ┌──────┬──────┬──────┬──────┬──────┐ │
│ │ Log  │ Log  │ Log  │ Log  │ ...  │ │
│ │Entry1│Entry2│Entry3│Entry4│      │ │
│ └──────┴──────┴──────┴──────┴──────┘ │
└──────────────────────────────────────┘
```

- **Metadata-only journaling** (data is not journaled by default)
- Log can be on a separate device for performance
- Log is circular: old entries are overwritten after checkpointing

```bash
# View log location
xfs_info /dev/sda1
# log stripe unit = 0, log stripe width = 0

# External log device
mkfs.xfs -l logdev=/dev/sdc1 /dev/sdb1
```

## Directory Structure

XFS directories use a **data structure** that adapts:

1. **Short form**: Small directories stored entirely in the inode
2. **Leaf block**: Medium directories — linear list of entries + leaf block with sorted names for binary search
3. **B+ tree**: Large directories — entries indexed by hash of filename

```
B+ Tree Directory:
┌─────────────────────────┐
│  Header: magic, level   │
├─────────────────────────┤
│  Hash → (block, offset) │  ← Leaf entries
│  "file1" → inode 1001   │
│  "file2" → inode 1002   │
│  "subdir" → inode 2001  │
└─────────────────────────┘
```

## Useful Commands

```bash
# Create XFS filesystem
mkfs.xfs -f -d agcount=8 /dev/sdb1

# Tune parameters
xfs_info /dev/sdb1                    # Show filesystem geometry
xfs_growfs /mnt                       # Online resize
xfs_repair /dev/sdb1                  # Repair filesystem
xfs_db /dev/sdb1                      # Debug filesystem

# Quotas
xfs_quota -x -c "limit bsoft=5g bhard=6g alice" /mnt

# Defragmentation
xfs_fsr /dev/sdb1                     # Filesystem reorganizer

# Backup/restore
xfsdump -L "backup" -M "media" -f /backup/dump /mnt
xfsrestore -f /backup/dump /mnt
```

## XFS vs ext4 Comparison

| Feature | XFS | ext4 |
|---------|-----|------|
| Max volume size | 8 EB | 1 EB |
| Max file size | 8 EB | 16 TB |
| Allocation | B+ trees per AG | Bitmaps per block group |
| Directories | B+ tree hash | Htree hash |
| Parallel allocation | Per-AG locks (excellent) | Per-group locks (good) |
| Journal | External log device possible | Inline journal |
| Online resize | Grow only | Grow only |
| Best for | Large files, parallel I/O | General purpose, small files |
| Default on | RHEL 7+, Fedora | Ubuntu, Debian |

## Interview Questions

**Q1: Why does XFS use allocation groups?**

Allocation groups partition the filesystem into independent regions, each with its own free space and inode tracking. This allows multiple threads to allocate blocks in different AGs simultaneously without contending for a global lock. It's the key to XFS's excellent parallel I/O performance.

**Q2: How does XFS's free space management differ from ext4's?**

ext4 uses a bitmap per block group. XFS uses two B+ trees per AG — one indexed by block number, one by extent size. This allows O(log n) allocation of contiguous extents vs. O(n) bitmap scanning. The B+ tree approach scales better for very large, fragmented filesystems.

**Q3: What happens during XFS log recovery after a crash?**

On mount after a crash, XFS replays the log to recover metadata operations that were committed to the log but not yet written to their final disk locations. Uncommitted transactions are discarded. Since XFS journals metadata only (by default), file data written before the crash may or may not be present.

**Q4: Why is XFS better than ext4 for large file workloads?**

XFS was designed from the start for large files and parallel I/O. Its B+ tree extent map scales better than ext4's extent tree, allocation groups enable true parallel allocation, and the directory B+ tree handles millions of entries efficiently. XFS also supports larger maximum file sizes (8 EB vs. 16 TB).

**Q5: What is XFS's delayed allocation strategy and why is it beneficial?**

XFS delays block allocation until writeback time. When `write()` is called, data goes to the page cache but no blocks are assigned. When the dirty pages are flushed (after 30-60 seconds or on `fsync()`), the allocator sees the full write extent and can allocate contiguous blocks. This reduces fragmentation significantly.

## Common Mistakes

- Assuming XFS is always faster than ext4 — for small files and metadata-heavy workloads, ext4 can be faster
- Not realizing XFS can't shrink (reduce size) — only grow
- Forgetting that XFS's log can be on a separate device for performance
- Thinking XFS doesn't support TRIM — it does (`discard` mount option)

## Summary

- XFS is a high-performance, scalable journaling filesystem
- Allocation groups enable parallel block allocation with minimal contention
- B+ trees for free space, directories, and extent mapping
- Delayed allocation reduces fragmentation
- Metadata-only journaling with optional external log device
- Best suited for large files, parallel I/O, and data-intensive workloads

## Cross-References

- [ext4](ext4.md) — comparison filesystem
- [Disk Allocation](disk-allocation.md) — extent-based allocation theory
- [Free Space Management](free-space.md) — B+ tree approach
- [Journaling](journaling.md) — crash consistency
- [VFS](vfs.md) — kernel filesystem abstraction


## Cross References

- [Journaling](journaling.md)
- [VFS](vfs.md)
- [Disk Allocation](disk-allocation.md)
