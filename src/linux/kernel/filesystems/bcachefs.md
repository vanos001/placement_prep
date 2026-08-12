# Bcachefs — Copy-on-Write Filesystem for Linux

## Overview

Bcachefs is a modern, general-purpose, POSIX-compliant Linux filesystem designed
for robustness, performance, and flexibility. It uses a **copy-on-write (CoW)**
B-tree architecture and integrates features traditionally found in volume managers
and RAID controllers — such as compression, encryption, snapshots, and tiered
storage — directly into the filesystem layer.

Bcachefs was developed by **Kent Overstreet**, building on his earlier work with
bcache (block cache). After years of out-of-tree development, bcachefs was merged
into the **Linux 6.7** mainline kernel in late 2023.

## Design Philosophy

Bcachefs aims to combine the best features of existing CoW filesystems (ZFS, Btrfs)
while avoiding their architectural limitations:

- **Simplicity over complexity**: cleaner internal architecture, fewer layers of
  abstraction
- **Performance**: designed for both HDDs and SSDs with minimal tuning
- **Data integrity**: checksums, CoW semantics, and atomic operations throughout
- **Unified storage management**: no separate volume manager needed

## Architecture

### B-Tree Structure

Bcachefs uses a single, unified **extents-based B-tree** (called the "btree") as
its core data structure. Unlike Btrfs, which uses multiple specialized trees,
bcachefs stores all metadata in a hierarchy of btrees with different node types:

- **Inodes**: file metadata (permissions, timestamps, xattrs)
- **Extents**: file data mappings (with optional inline data for small files)
- **Dirents**: directory entries
- **Xattrs**: extended attributes
- **Alloc**: allocation and bucket state information
- **Snapshots**: snapshot topology

Each btree node is a sorted array of keys with an interior fan-out. Nodes are
CoW — modifications create new nodes rather than updating in place.

### B-Tree Node Structure

```c
/* Simplified btree node layout */
struct btree_node {
    struct btree_node_header {
        __le64 flags;           /* Node type, level, etc. */
        __le64 seq;             /* Sequence number for locking */
        __le64 journal_seq;     /* Journal sequence */
        struct bversion version; /* Version */
        struct bpos min_key;    /* Minimum key in this node */
        struct bpos max_key;    /* Maximum key in this node */
        __le32 csum;            /* CRC32 checksum */
    };
    /* Followed by sorted keys and values */
    struct bkey_format format;  /* Key format descriptor */
    /* ... keys and values ... */
};
```

### Extent-Based Allocation

Bcachefs divides storage into **buckets** (typically 512 KiB to several MiB).
An allocator manages bucket state:

- **Available**: free for allocation
- **Dirty**: contains live data
- **Clean**: data has been flushed to stable storage
- **Stale**: data is no longer referenced (can be reclaimed)

This bucket-based approach simplifies garbage collection and supports multi-device
tiered storage natively.

### Journal

The journal provides atomicity for metadata operations. Bcachefs uses a
**log-structured journal** that records all metadata changes before they are
committed to btrees:

```
Journal → Btree nodes → Buckets on disk
```

On crash recovery, the journal is replayed to restore consistency. The journal
itself is checksummed and CoW.

## Copy-on-Write (CoW) Semantics

Every write in bcachefs follows CoW discipline:

1. Data is written to a **new** location (a fresh bucket or extent)
2. The btree is updated to point to the new location
3. The old location is marked stale and eventually reclaimed

This ensures that interrupted writes never corrupt existing data. CoW also
enables efficient snapshots — snapshot and source share the same extents until
a write diverges them.

### Overwrite Behavior

For in-place modifications (e.g., appending to a file), bcachefs may:

- **Append**: write new data to a new extent, extend the inode
- **Partial overwrite**: split the extent, write the modified portion to a new
  location, update btree pointers
- **Inline data**: very small files (< ~1 KiB) are stored directly in the btree
  node, avoiding separate data extents

## Compression

Bcachefs supports transparent compression with multiple algorithms:

| Algorithm    | Library         | Characteristics                |
|--------------|-----------------|--------------------------------|
| LZ4          | lz4             | Fast, moderate ratio           |
| ZSTD         | zstd            | Good ratio, configurable level |
| gzip         | zlib            | Legacy, broad compatibility    |

### Compression Configuration

```bash
# Set compression on a directory
bcachefs set-compression --compression=zstd /mnt/bcachefs/data

# Set compression with level
bcachefs set-compression --compression=zstd:3 /mnt/bcachefs/data
```

### How Compression Works

1. Data blocks are compressed before writing to extents
2. The extent records the compression algorithm and original size
3. Reads decompress transparently
4. Compression is per-extent — small extents that don't compress well are stored
   uncompressed

### Inline Compression

Small files can be stored compressed directly within btree nodes, eliminating
the data extent entirely and improving both space efficiency and read performance.

## Encryption

Bcachefs provides **full-disk encryption** (FDE) using the kernel's crypto API.
Encryption is configured at filesystem creation time and is transparent to
applications.

### Encryption Modes

- **XChaCha20 + Poly1305**: authenticated encryption (AEAD), recommended default.
  Uses a 192-bit extended nonce to prevent nonce reuse across extents.
- **AES-256-XTS**: block cipher mode, traditional FDE approach (confidentiality
  only, no authentication)

### Key Management

```bash
# Create encrypted filesystem
bcachefs format --encrypted /dev/sdb1
# Prompts for passphrase

# Unlock at mount time
bcachefs unlock /dev/sdb1  # prompts for passphrase
mount -t bcachefs /dev/sdb1 /mnt/secure
```

Bcachefs uses a two-level key hierarchy:

1. **Master key**: derived from the user's passphrase (via scrypt or argon2 KDF)
2. **Per-extent keys**: derived from the master key + extent nonce

Each extent has a unique nonce, preventing ciphertext reuse even for identical
plaintext blocks.

### Encryption vs. LUKS

Unlike dm-crypt/LUKS, bcachefs encryption is filesystem-aware:

- Metadata is encrypted alongside data
- Snapshots inherit encryption
- Compression can be applied before encryption (more effective than encrypting
  compressed data at the block layer)
- No need for a separate device-mapper layer

## Snapshots

Bcachefs supports **subvolume snapshots** — point-in-time, read-only copies of
directory trees that share unchanged extents with the source.

### Creating Snapshots

```bash
# Create a snapshot of a subvolume
bcachefs subvolume snapshot /mnt/bcachefs/data /mnt/bcachefs/snapshots/data-2024-01-15
```

### How Snapshots Work

1. A snapshot creates a new inode tree that references the same extents as the
   source
2. Extents are reference-counted — each extent tracks how many snapshots (and
   the source) reference it
3. When the source modifies a referenced extent, the CoW mechanism creates a
   new copy for the source (the snapshot retains the old version)
4. Unchanged extents remain shared, consuming no additional space

### Snapshot Operations

```bash
# List snapshots
bcachefs subvolume list /mnt/bcachefs

# Delete a snapshot (frees unreferenced extents)
bcachefs subvolume delete /mnt/bcachefs/snapshots/data-2024-01-15

# Rollback to a snapshot (destructive to source changes)
bcachefs subvolume rollback /mnt/bcachefs/data /mnt/bcachefs/snapshots/data-2024-01-15
```

### Snapshot Topology

Bcachefs tracks snapshot relationships in a dedicated btree. This enables:

- **Snapshot trees**: nested snapshots with parent-child relationships
- **Efficient deletion**: when a snapshot is deleted, only extents exclusively
  referenced by that snapshot are freed
- **Snapshot groups**: batch operations on related snapshots

## Tiered Storage

One of bcachefs's distinctive features is **native multi-device support** with
automatic data placement across storage tiers.

### Device Types

```bash
bcachefs format \
    --data_allowed=ssd_hdd \
    --foreground_target=ssd \
    --background_target=hdd \
    --promote_target=ssd \
    /dev/nvme0n1 /dev/sda
```

| Target          | Purpose                                        |
|-----------------|------------------------------------------------|
| `foreground_target` | New writes go here first (fast SSD)         |
| `background_target` | Data migrated here during GC (slow HDD)     |
| `promote_target`    | Frequently read data promoted here (SSD)    |
| `metadata_target`   | Btree nodes placed here (SSD recommended)   |

### Data Migration

Bcachefs implements a background garbage collector that can migrate data between
devices:

- **Write allocation**: new data is placed on the foreground target
- **GC migration**: during garbage collection, data can be moved to the
  background target if the foreground target is full or if the data is cold
- **Promotion**: frequently accessed data on the background target can be
  promoted to the foreground target

### RAID and Replication

Bcachefs supports multiple redundancy schemes:

- **Replication**: data written to N devices simultaneously
- **Erasure coding**: parity-based redundancy (RAID-like)

```bash
# RAID-1 (mirroring)
bcachefs format --data_replicas=2 /dev/sda /dev/sdb

# Erasure coding (4+2)
bcachefs format --data_replicas=1 --erasure_coding /dev/sda /dev/sdb /dev/sdc /dev/sdd /dev/sde /dev/sdf
```

## Scrubbing and Data Integrity

Bcachefs includes a background **scrub** mechanism that periodically reads all
data and verifies checksums:

```bash
# Trigger a scrub
bcachefs fsck /mnt/bcachefs
```

When scrub detects corruption:

1. If replicas exist, the good copy is used to repair the corrupted copy
2. If erasure coding is enabled, parity data is used for reconstruction
3. If no redundancy exists, the error is reported to userspace

## Operational Commands

### Filesystem Creation

```bash
# Basic
bcachefs format /dev/sdb1

# Multi-device with options
bcachefs format \
    --label=ssd.ssd1 /dev/nvme0n1 \
    --label=hdd.hdd1 /dev/sda /dev/sdb \
    --data_allowed=ssd_hdd \
    --foreground_target=ssd \
    --background_target=hdd \
    --compression=zstd \
    --encrypted \
    --block_size=4k
```

### Mounting

```bash
mount -t bcachefs /dev/sdb1 /mnt/bcachefs

# Multi-device (all members)
mount -t bcachefs /dev/nvme0n1:/dev/sda:/dev/sdb /mnt/bcachefs
```

### Filesystem Status

```bash
bcachefs fs usage /mnt/bcachefs    # Space usage by device and tier
bcachefs device list /mnt/bcachefs # Device status
```

## Performance Characteristics

### Strengths

- **Small random I/O**: CoW + B-tree provides excellent random read/write
- **Compression**: reduces I/O bandwidth for compressible workloads
- **Multi-device**: automatic tiering reduces need for manual data placement
- **Small file handling**: inline data storage avoids extent overhead

### Trade-offs

- **Write amplification**: CoW inherently writes more than in-place filesystems
  (ext4, XFS) for random overwrites
- **Fragmentation**: long-lived CoW filesystems can fragment over time (similar
  to Btrfs)
- **Journal overhead**: the journal adds latency to metadata-heavy workloads
- **Maturity**: as of Linux 6.7+, bcachefs is stable but lacks the decade of
  battle-testing that ext4 or XFS have

## Comparison with Other CoW Filesystems

| Feature          | Bcachefs      | Btrfs          | ZFS            |
|------------------|---------------|----------------|----------------|
| License          | GPL-2.0       | GPL-2.0        | CDDL           |
| Mainline Linux   | Yes (6.7+)    | Yes (3.x+)     | No (ZFS on Linux) |
| B-tree           | Single unified| Multiple trees | Merkle tree    |
| RAID             | Built-in      | Built-in       | Built-in       |
| Encryption       | Native        | Native (2.6+)  | Native         |
| Compression      | Native        | Native         | Native         |
| Deduplication    | Planned       | Native         | Native         |
| Snapshots        | Subvolume     | Subvolume      | Dataset        |
| Tiered storage   | Native        | No             | ZFS tiering    |
| Maturity         | New           | Mature         | Very mature    |

## B-Tree Locking Protocol

Bcachefs uses a sophisticated locking protocol for concurrent btree access:

### Six Lock Types

Bcachefs defines six lock types for btree nodes, ordered by strength:

```c
enum btree_node_locked_type {
    BTREE_NODE_UNLOCKED      = 0,
    BTREE_NODE_READ_LOCKED   = 1,  /* Shared read lock */
    BTREE_NODE_INTENT_LOCKED = 2,  /* Intent to modify (upgradeable) */
    BTREE_NODE_WRITE_LOCKED  = 3,  /* Exclusive write lock */
};
```

The intent lock is a key innovation — it signals "I intend to modify this node" without blocking other readers, allowing optimistic concurrency.

### Sequence-Based Locking

Each btree node has a `seq` counter. Readers read the seq before and after accessing node data to detect concurrent modifications:

```c
/* Simplified reader pattern */
unsigned seq = READ_ONCE(b->seq);
if (seq & 1)
    goto retry;  /* Node is locked for writing */
/* Read data ... */
if (READ_ONCE(b->seq) != seq)
    goto retry;  /* Node was modified, retry */
```

This seqlock approach allows lockless reads while maintaining consistency.

## B-Tree Iterator Pattern

The btree iterator is the primary interface for traversing and modifying the btree:

```c
struct btree_trans {
    struct btree_iter    iters[BTREE_ITER_MAX];
    unsigned             nr_iters;
    struct journal_res   journal_res;
    /* ... */
};

/* Example: iterate over inodes */
for_each_btree_key(trans, iter, BTREE_ID_inodes,
                   POS_MIN, 0, k, ret) {
    struct bch_inode_unpacked inode;
    bch2_inode_unpack(k, &inode);
    /* Process inode ... */
}
```

The iterator supports:
- Forward and backward traversal
- Automatic node splitting and merging
- Journal-aware snapshotting (consistent reads)
- Nested transactions for multi-key modifications

## Filesystem Creation Internals

When `bcachefs format` runs, it creates the initial on-disk layout:

```
Offset 0:      Superblock (with UUID, label, device info)
After SB:      Journal (initial empty journal)
Then:          B-tree root nodes (empty initial trees)
Then:          Bucket allocation bitmap
Then:          Data area (all buckets marked free)
```

The initial btree setup creates these empty trees:
- `BTREE_ID_inodes` — inode tree
- `BTREE_ID_dirents` — directory entry tree
- `BTREE_ID_xattrs` — extended attribute tree
- `BTREE_ID_extents` — file data extent tree
- `BTREE_ID_alloc` — bucket allocation tree
- `BTREE_ID_snapshots` — snapshot topology tree
- `BTREE_ID_lru` — LRU tree (for GC)
- `BTREE_ID_freespace` — free space tree
- `BTREE_ID_need_discard` — discard queue tree
- `BTREE_ID_backpointers` — backpointer tree
- `BTREE_ID_subvolumes` — subvolume tree
- `BTREE_ID_snapshot_trees` — snapshot tree metadata

## Multi-Device Internals

### Device Group and Target System

Bcachefs organizes devices into groups identified by labels:

```bash
# Labels format: type.name
--label=ssd.ssd1 /dev/nvme0n1
--label=ssd.ssd2 /dev/nvme1n1
--label=hdd.hdd1 /dev/sda
```

Target options control data placement:

| Option | Default | Effect |
|--------|---------|--------|
| `foreground_target` | (auto) | Where new data writes go |
| `background_target` | (none) | Where cold data migrates |
| `promote_target` | (none) | Where hot data gets promoted |
| `metadata_target` | (auto) | Where btree nodes go |

### Replication Internals

When replication is configured (`data_replicas=2`), each write is sent to multiple devices:

```
Write request
  ├── Allocate extent on device A
  ├── Allocate extent on device B (replica)
  ├── Write data to both
  └── Update btree with both pointers
```

The replicas entry in the btree records all device positions:

```c
struct bch_extent {
    /* ... extent flags, checksum, compression ... */
    struct bch_extent_ptr {
        __le64 offset;
        __u8   dev;
        __u8   gen;
    } ptrs[];  /* One per replica */
};
```

### Erasure Coding

Bcachefs implements Reed-Solomon erasure coding for space-efficient redundancy:

```bash
# Create filesystem with erasure coding (4 data + 2 parity = 6 devices)
bcachefs format \
    --data_replicas=1 \
    --erasure_coding \
    /dev/sda /dev/sdb /dev/sdc /dev/sdd /dev/sde /dev/sdf
```

Erasure coding stripes data across N devices with M parity devices, tolerating up to M device failures while using less space than full replication.

## Journal Replay and Crash Recovery

On mount after an unclean shutdown, bcachefs performs journal replay:

1. **Read journal** — scan the journal area for valid entries (verified by checksum)
2. **Find last checkpoint** — locate the most recent consistent journal entry
3. **Replay entries** — apply all journal entries from the last checkpoint to the current end
4. **Rebuild in-memory state** — reconstruct btree caches, allocator state, etc.

```bash
# The journal is automatically replayed on mount
mount -t bcachefs /dev/sdb1 /mnt/bcachefs
# Kernel logs show journal replay progress:
# bcachefs: (sdb1): journal read done, replaying entries 1234-1250
# bcachefs: (sdb1): starting with version 1250
```

If the journal itself is corrupted, bcachefs can attempt recovery:

```bash
# Force fsck with journal replay
bcachefs fsck --journal-recovery /dev/sdb1
```

## Kernel Version History

| Kernel | Release | Key Changes |
|--------|---------|-------------|
| 6.7    | Jan 2024 | Initial mainline merge |
| 6.8    | Mar 2024 | Performance improvements, bug fixes |
| 6.9    | May 2024 | Erasure coding, improved GC |
| 6.10   | Jul 2024 | Snapshots improvements |
| 6.11   | Sep 2024 | Send/receive groundwork, stability |
| 6.12   | Nov 2024 | Multi-device improvements |
| 6.13   | Jan 2025 | Performance optimizations |
| 6.14   | Mar 2025 | Continued stability work |

## Known Limitations (as of Linux 6.14)

- **No online fsck**: repair requires unmounting
- **No deduplication**: planned for future releases
- **Limited tooling**: bcachefs-tools is still evolving
- **No send/receive**: incremental replication not yet implemented
- **Upgrade path**: no in-place conversion from ext4/Btrfs
- **No reflink/clone**: cross-file extent sharing not yet supported

## Troubleshooting

### Filesystem Check

```bash
bcachefs fsck /dev/sdb1
```

### Debugging

```bash
# Enable debug logging
bcachefs set-option /mnt/bcachefs log_level=debug

# Dump btree structure
bcachefs dump /dev/sdb1

# Check device status
bcachefs device list /mnt/bcachefs

# View filesystem errors
bcachefs fs errors /mnt/bcachefs
```

### Common Issues

1. **"device already registered"**: multi-device filesystem requires all
   devices to be passed at mount time
2. **Slow mount**: large filesystems may take time to read the journal and
   rebuild in-memory state
3. **ENOSPC on "free" space**: bcachefs reserves space for CoW operations;
   `bcachefs fs usage` shows the actual situation
4. **"btree node needs repair"**: run `bcachefs fsck` offline
5. **Device missing**: multi-device mount fails if a device is missing;
   use `bcachefs device remove` to gracefully remove a device first

## Implementation Details

### Key Source Files

- **`fs/bcachefs/`** — Main bcachefs implementation
  - `btree.c` — B-tree operations
  - `btree_gc.c` — B-tree garbage collection
  - `btree_iter.c` — B-tree iterator
  - `btree_trans.c` — Transaction management
  - `btree_update.c` — B-tree modification operations
  - `buckets.c` — Bucket allocator
  - `checksum.c` — Checksumming
  - `compression.c` — Compression support
  - `dirent.c` — Directory entries
  - `ec.c` — Erasure coding
  - `extents.c` — Extent management
  - `fs.c` — VFS interface
  - `inode.c` — Inode operations
  - `io.c` — I/O path
  - `journal.c` — Journal management
  - `keylist.c` — Key list operations
  - `move.c` — Data movement (GC)
  - `movinggc.c` — Moving GC
  - `replicas.c` — Replica management
  - `snapshot.c` — Snapshot implementation
  - `super.c` — Superblock operations
  - `subvolume.c` — Subvolume management

### B-Tree Node Format

```c
/* Simplified btree node format */
struct btree_node {
    /* Header */
    __le64 flags;           /* Node type, level, etc. */
    __le64 seq;             /* Sequence number */
    struct bpos min_key;    /* Minimum key */
    struct bpos max_key;    /* Maximum key */
    __le32 csum;            /* CRC32 checksum */
    
    /* Key format descriptor */
    struct bkey_format format;
    
    /* Keys and values */
    /* ... variable length ... */
};
```

### Bucket Allocator

The bucket allocator manages storage allocation:

```c
/* Bucket states */
enum bucket_state {
    BUCKET_FREE,        /* Available for allocation */
    BUCKET_DIRTY,       /* Contains live data */
    BUCKET_CLEAN,       /* Data flushed to disk */
    BUCKET_STALE,       /* Data no longer referenced */
};

/* Bucket allocation */
struct bucket *bcachefs_alloc_bucket(struct bch_fs *c, 
                                      enum bucket_state state);
```

### Journal Structure

```c
/* Journal entry format */
struct journal_entry {
    __le64 seq;             /* Journal sequence number */
    __le32 csum;            /* CRC32 checksum */
    __le32 flags;           /* Entry flags */
    __le64 last_seq;        /* Last committed sequence */
    /* Followed by journal keys */
    struct journal_key keys[];
};
```

## Performance Tuning

### Mount Options

```bash
# Bcachefs mount options
mount -t bcachefs /dev/sdb1 /mnt/bcachefs

# Common options:
# -o compression=zstd         # Enable compression
# -o compression_level=3      # Compression level
# -o data_replicas=2          # Number of data replicas
# -o metadata_replicas=2      # Number of metadata replicas
# -o gc_reserve_percent=15    # GC reserve percentage
# -o target_reserve_percent=20 # Target reserve percentage
```

### Benchmarking

```bash
# Basic benchmark
fio --name=bcachefs-test \
    --filename=/mnt/bcachefs/testfile \
    --size=1G \
    --rw=randrw \
    --bs=4k \
    --numjobs=4 \
    --time_based \
    --runtime=60

# Check compression ratio
bcachefs fs usage /mnt/bcachefs
# Shows: compressed, uncompressed, ratio
```

### Performance Characteristics

| Workload | Bcachefs | ext4 | XFS | Btrfs |
|----------|----------|------|-----|-------|
| Sequential read | Good | Good | Good | Good |
| Sequential write | Good | Good | Good | Good |
| Random read | Good | Good | Good | Good |
| Random write | Good | Good | Good | Good |
| Metadata heavy | Good | Good | Good | Good |
| Compression | Good | N/A | N/A | Good |
| Snapshots | Good | N/A | N/A | Good |

## Cross-References

- [superblock](./superblock.md) — Bcachefs superblock operations and VFS integration
- [zfs](./zfs.md) — Comparison filesystem with similar CoW and integrity features
- [mounting](./mounting.md) — Mount API and filesystem registration

## References

- [bcachefs kernel documentation](https://www.kernel.org/doc/html/latest/filesystems/bcachefs.html)
- [bcachefs.org](https://bcachefs.org/)
- [LWN: A new filesystem for Linux](https://lwn.net/Articles/747355/)
- [LWN: Bcachefs makes progress](https://lwn.net/Articles/934689/)
- [Linux Plumbers Conference talk](https://lpc.events/event/16/contributions/1253/)
- [bcachefs Principles of Operation (PDF)](https://bcachefs.org/bcachefs-principles-of-operation.pdf)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- **Kernel source**: `fs/bcachefs/`
- **Documentation**: `Documentation/filesystems/bcachefs/`
- **Bcachefs wiki**: https://bcachefs.org/
- **LWN article**: ["A new filesystem for Linux"](https://lwn.net/Articles/747355/) — design overview
- **LWN article**: ["Bcachefs makes progress"](https://lwn.net/Articles/934689/) — merge status and feature summary
- **Kent Overstreet's talk**: "bcachefs: a new COW filesystem for Linux" — Linux Plumbers Conference
- **Comparison**: https://bcachefs.org/Status/ — current feature status and known issues
