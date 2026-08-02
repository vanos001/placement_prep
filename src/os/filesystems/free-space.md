# Free Space Management

## Overview

The filesystem must track which disk blocks are free and which are allocated. Efficient free-space management is critical: a bad scheme wastes time searching for free blocks, leads to fragmentation, or consumes excessive metadata space. This page covers the main techniques used by real filesystems.

## The Problem

Given a disk with millions of blocks:
- How do we know which blocks are free?
- How do we quickly find a contiguous run of N free blocks?
- How do we efficiently mark blocks as allocated/freed?

## Method 1: Bit Vector (Bitmap)

Each block is represented by a single bit: 0 = free, 1 = allocated.

```
Block:  0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15
Bit:    1  1  0  0  1  0  0  1  0  0  0  1  0  0  0  0
        ↑     ↑        ↑     ↑              ↑
      alloc  free    alloc free           free
```

**Storage**: A 1 TB disk with 4 KB blocks has 268 million blocks → 268 million bits ≈ **32 MB** of bitmap.

### Operations
- **Find free block**: Scan bitmap for a 0 bit → O(n) worst case, but hardware popcount helps
- **Allocate block k**: Set bit k to 1 → O(1)
- **Free block k**: Set bit k to 0 → O(1)
- **Find N contiguous free blocks**: Scan for N consecutive 0s → O(n)

### Example: ext4 block bitmap

```
$ dumpe2fs /dev/sda1 | grep "Block bitmap"
  Block bitmap at 33

$ debugfs -R 'stat <2>' /dev/sda1
  (Shows inode bitmap location and usage)
```

### Advantages
- Simple and fast for single-block operations
- Easy to implement
- Compact representation

### Disadvantages
- Scanning for contiguous free space is slow without optimizations
- Bitmap must fit in memory for efficiency (usually not a problem for modern systems)

### Optimizations
- **Grouping**: Divide blocks into groups; track free count per group in a summary. Skip full groups during allocation.
- **Weight tree**: Balanced tree over bitmap words for O(log n) search

## Method 2: Linked List (Free List)

Free blocks are chained together. A pointer in each free block points to the next free block.

```
Head → Block 2 → Block 5 → Block 6 → Block 8 → Block 9 → Block 10 → Block 12 → NULL

Disk:
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│ A │ B │ . │ A │ B │ . │ . │ B │ . │ . │ . │ B │ . │ . │ . │ . │
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘

. = free, linked together
```

### Operations
- **Allocate**: Remove head of list → O(1)
- **Free**: Add to head of list → O(1)
- **Find N contiguous**: Requires scanning → O(n)

### Advantages
- O(1) allocate and free (for single blocks)
- No extra space for bitmap

### Disadvantages
- **No contiguous allocation**: Free blocks are scattered
- **Wastes space in free blocks**: Pointer stored in each free block
- **Reliability**: One corrupted pointer breaks the entire chain
- **Random I/O for metadata**: Reading the free list requires seeking to scattered blocks

## Method 3: Grouping

A variation of the linked list: instead of one block pointer per free block, store **N pointers** in the first free block, pointing to N other free blocks.

```
Block 2 (free, group leader):
  → [Block 5, Block 6, Block 8, Block 9, Block 10, ...]

Block 5 (free, group leader):
  → [Block 12, Block 15, Block 20, ...]
```

### Advantage
- Can find multiple free blocks per disk read
- Better locality than simple free list

## Method 4: Counting (Extent-Based Free Space)

Store runs of consecutive free blocks as (start, length) pairs.

```
Free space extents:
  (2, 2)    → blocks 2-3 are free
  (5, 3)    → blocks 5-7 are free
  (9, 4)    → blocks 9-12 are free
```

### Operations
- **Allocate N contiguous**: Search extents for one with length ≥ N → efficient with balanced tree
- **Free**: Merge with adjacent free extents

### Advantages
- Efficient for contiguous allocation
- Compact representation when free space is clustered

### Used by: XFS, Btrfs (free space tree)

## Method 5: Free Space B-Tree (XFS)

XFS uses a B+ tree to track free space, indexed by block number. Each entry records a free extent.

```
B+ Tree root
├── Leaf: [(2,2), (5,3), (9,4)]
├── Leaf: [(20,10), (50,5), (100,50)]
└── Leaf: [(200,3), (300,20)]
```

- **Lookup**: O(log n) for any block range
- **Insertion/Deletion**: O(log n) with tree rebalancing
- Excellent for large, fragmented disks

## Method 6: Free Space Tree (Btrfs)

Btrfs uses a dedicated B-tree to track all allocation, including free space. There's no separate bitmap — the allocator tree knows both allocated and free extents.

## ext4: Combined Approach

ext4 uses a **bitmap per block group** plus a **group descriptor** with free counts.

```
Block Group 0:
  ┌─────────────────────────────────────────────┐
  │ Superblock | Group Descriptors | Block Bitmap │ Inode Bitmap │ Inode Table │ Data Blocks │
  └─────────────────────────────────────────────┘

Block Group N:
  ┌─────────────────────────────────────────────┐
  │ Block Bitmap │ Inode Bitmap │ Inode Table │ Data Blocks │
  └─────────────────────────────────────────────┘
```

**Group descriptor** stores:
- Free block count
- Free inode count
- Used directory count
- Bitmap block numbers

**Allocation strategy**:
1. Try to allocate in the same block group as the file's inode (locality)
2. For new inodes, prefer block groups with fewer directories (even directory distribution)
3. For new blocks, prefer block groups with higher free counts

## Comparison Table

| Method | Allocate | Free | Find Contiguous | Extra Space | Used By |
|--------|----------|------|-----------------|-------------|---------|
| Bitmap | O(1) | O(1) | O(n) | 1 bit/block | ext4, NTFS |
| Linked List | O(1) | O(1) | O(n) | pointer/block | FAT (via FAT table) |
| Grouping | O(1)* | O(1) | O(n) | pointer/group | Old UNIX |
| Counting | O(log n) | O(log n) | O(log n) | extent entries | XFS, Btrfs |
| B-tree | O(log n) | O(log n) | O(log n) | tree nodes | XFS free space |

*Grouping amortizes: one read gives N free block pointers.

## Interview Questions

**Q1: How much space does a bitmap take for a 1 TB disk with 4 KB blocks?**

Number of blocks = 1 TB / 4 KB = 2^40 / 2^12 = 2^28 = 268,435,456 blocks.
Bitmap size = 268,435,456 bits = 33,554,432 bytes ≈ **32 MB**.

**Q2: Why is a bitmap preferred over a free list for most modern filesystems?**

Bitmaps allow fast contiguous allocation scanning (hardware popcount instructions help), don't waste space in free blocks for pointers, and are more resilient to corruption (one bad bit affects one block; one corrupted pointer breaks the entire chain).

**Q3: What is the problem with using a free list for a filesystem that needs contiguous allocation?**

A free list tracks individual free blocks, not contiguous runs. Finding N consecutive free blocks requires scanning the entire list and checking adjacency — O(n) and not guaranteed to find the best fit.

**Q4: How does ext4 decide which block group to allocate from?**

ext4 tries to keep a file's data blocks in the same block group as its inode (data locality). For new files, it distributes inodes across groups with fewer directories. It uses the group descriptor's free block count to avoid full groups.

**Q5: Why might a counting/extent-based approach be better than a bitmap for very large, fragmented disks?**

With extents, free space is represented compactly as (start, length) pairs in a B-tree. Finding a contiguous run of N blocks is a tree search — O(log n) — instead of scanning a bitmap for N consecutive zeros — O(n). On a 100 TB disk, this difference matters.

## Common Mistakes

- Thinking the bitmap must always be in memory — modern OSes cache it, but it can be paged out
- Confusing inode bitmap with block bitmap — they're separate (one tracks free inodes, the other free data blocks)
- Not realizing that ext4's block groups provide both bitmap management AND locality optimization
- Assuming all free space tracking uses the same method — real filesystems often combine approaches

## Summary

| Technique | Key Insight |
|-----------|------------|
| Bitmap | Simple, fast single-block ops, compact |
| Linked list | No extra metadata space but terrible for contiguous allocation |
| Grouping | Amortizes list overhead by batching pointers |
| Counting/Extents | Compact for clustered free space, fast contiguous search |
| B-tree | Scalable to very large disks, O(log n) everything |

Modern filesystems primarily use **bitmaps** (ext4, NTFS) or **extent-based B-trees** (XFS, Btrfs, ZFS), with block group structures to optimize locality.

## Cross-References

- [Disk Allocation](disk-allocation.md) — how allocated blocks are assigned to files
- [ext4](ext4.md) — block groups and allocation strategy
- [XFS](xfs.md) — B+ tree free space management
- [Btrfs](btrfs.md) — extent-based allocation tree
- [Disk Scheduling](../io/disk-scheduling.md) — I/O order optimization


## Cross References

- [Disk Allocation](../os/filesystems/disk-allocation.md)
- [File Concepts](../os/filesystems/file-concepts.md)
- [Bitmap Index](../dbms/indexing/bitmap-index.md)
