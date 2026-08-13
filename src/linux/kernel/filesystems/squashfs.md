# SquashFS

## Overview

SquashFS is a compressed, read-only filesystem for Linux. It compresses files, inodes, and directories using zlib, lz4, lzo, xz, or zstd compression. SquashFS is widely used for live CDs, embedded systems, container images, and firmware because it achieves very high compression ratios while allowing random access to files.

SquashFS stores everything in a single file (the "squashfs image") that can be loopback-mounted or embedded in a partition. The filesystem is designed for read-only workloads — it cannot be modified after creation (use `mksquashfs` to create new images).

> **Introduced:** Linux 2.6.29 (commit `c9c9c4`)  
> **Source:** `fs/squashfs/`  
> **Maintainer:** Phillip Lougher

---

## Architecture

```mermaid
flowchart TD
    subgraph Mount["squashfs_mount()"]
        SUPER["Superblock<br>(magic, flags, compression)"]
        INODE["Inode table<br>(compressed blocks)"]
        DIR["Directory table<br>(compressed entries)"]
        FRAG["Fragment table<br>(tail-end packing)"]
        ID["ID table<br>(UID/GID mapping)"]
        XATTR["Xattr table<br>(extended attributes)"]
    end

    subgraph Data["Data Blocks"]
        BLOCK1["Compressed block 1<br>(up to 1MB)"]
        BLOCK2["Compressed block 2"]
        BLOCK3["..."]
        FRAG_BLOCK["Fragment blocks<br>(small files packed)"]
    end

    SUPER --> INODE
    INODE --> DIR
    INODE --> FRAG
    INODE --> ID
    INODE --> XATTR
    INODE --> BLOCK1
    INODE --> BLOCK2
    INODE --> BLOCK3
    INODE --> FRAG_BLOCK
```

---

## On-Disk Format

### Superblock

```c
/* fs/squashfs/squashfs_fs.h */
struct squashfs_super_block {
    __le32 s_magic;              /* 0x73717368 ("sqsh") */
    __le32 inodes;               /* Number of inodes */
    __le32 mkfs_time;            /* Creation time */
    __le32 block_size;           /* Data block size (4K-1M) */
    __le32 fragments;            /* Number of fragments */
    __le16 compression;          /* Compression algorithm */
    __le16 block_log;            /* log2(block_size) */
    __le16 flags;                /* Filesystem flags */
    __le16 no_ids;               /* Number of UID/GID entries */
    __le16 s_major;              /* Major version */
    __le16 s_minor;              /* Minor version */
    __le64 root_inode;           /* Root inode block + offset */
    __le64 bytes_used;           /* Bytes used in image */
    __le64 id_table_start;       /* UID/GID table start */
    __le64 xattr_id_table_start; /* Xattr table start */
    __le64 inode_table_start;    /* Inode table start */
    __le64 directory_table_start;/* Directory table start */
    __le64 fragment_table_start; /* Fragment table start */
    __le64 export_table_start;   /* NFS export table start */
};
```

### Inode Types

SquashFS has specialized inodes for different file types:

| Inode Type | Description |
|-----------|-------------|
| Basic File | Regular file (data blocks or fragments) |
| Basic Directory | Directory (directory table entries) |
| Extended File | File with xattrs, sparse blocks |
| Extended Directory | Directory with xattrs, large count |
| Symlink | Symbolic link (inline target) |
| Block Device | Block device (major/minor) |
| Character Device | Character device (major/minor) |
| FIFO | Named pipe |
| Socket | Unix socket |

### File Data Storage

```mermaid
flowchart TD
    A[File data] --> B{Size > fragment threshold?}
    B -->|Yes| C["Store in data blocks<br>(compressed, up to 1MB each)"]
    B -->|No| D["Store in fragment block<br>(packed with other small files)"]
    C --> E[Block index stored in inode]
    D --> F[Fragment block + offset stored in inode]
```

---

## Compression

### Supported Algorithms

| Algorithm | Speed | Ratio | CPU Usage | Default |
|-----------|-------|-------|-----------|---------|
| gzip | Moderate | Good | Moderate | Legacy default |
| lz4 | Fastest | Lower | Low | Speed-optimized |
| lzo | Fast | Lower | Low | Speed-optimized |
| xz | Slow | Best | High | Size-optimized |
| zstd | Fast | Very good | Moderate | Modern default |

### Compression Configuration

```bash
# Create with specific compression
mksquashfs /source /image.squashfs -comp zstd
mksquashfs /source /image.squashfs -comp xz
mksquashfs /source /image.squashfs -comp lz4

# Check compression of existing image
unsquashfs -s /image.squashfs
# Compression: zstd
# Block size: 131072
```

### Block Size

SquashFS compresses data in fixed-size blocks (default 128KB):

```bash
# Create with custom block size
mksquashfs /source /image.squashfs -b 262144  # 256KB blocks
mksquashfs /source /image.squashfs -b 1048576 # 1MB blocks

# Larger blocks = better compression, slower random access
# Smaller blocks = worse compression, faster random access
```

---

## Key Data Structures (In-Kernel)

### struct squashfs_sb_info

```c
/* fs/squashfs/squashfs.h */
struct squashfs_sb_info {
    struct squashfs_super_block *sblk; /* Superblock */
    int block_size;                     /* Block size */
    int block_log;                      /* log2(block_size) */
    int flags;                          /* Filesystem flags */
    struct squashfs_decompressor *decompressor; /* Decompressor */
    void *stream;                       /* Decompression stream */
    __le64 *id_table;                   /* UID/GID lookup table */
    __le64 *fragment_index;             /* Fragment index table */
    unsigned int fragments;             /* Number of fragments */
    int next_fragment;                  /* Next fragment index */
    u64 next_meta_inode;                /* Next metadata inode */
    /* ... */
};
```

### struct squashfs_inode_info

```c
/* fs/squashfs/squashfs.h */
struct squashfs_inode_info {
    struct inode vfs_inode;          /* VFS inode */
    u64 start;                       /* Start of inode on disk */
    int offset;                      /* Offset in metadata block */
    u64 xattr;                       /* Xattr block + offset */
    unsigned int block_start;        /* Start of file data */
    unsigned int fragment_block;     /* Fragment block number */
    unsigned int fragment_offset;    /* Offset in fragment block */
    unsigned int fragment_size;      /* Fragment size */
    unsigned short block_list[];     /* Block size list */
};
```

---

## Operations

### File Operations

```c
/* fs/squashfs/file.c */
const struct file_operations squashfs_file_ops = {
    .read_iter = squashfs_read_iter,   /* Read file data */
    .mmap = squashfs_file_mmap,        /* Memory-mapped I/O */
    .llseek = generic_file_llseek,      /* Seek */
};

const struct address_space_operations squashfs_aops = {
    .readahead = squashfs_readahead,    /* Readahead */
    .read_folio = squashfs_read_folio,  /* Read single page */
};
```

### Directory Operations

```c
/* fs/squashfs/dir.c */
const struct file_operations squashfs_dir_ops = {
    .iterate_shared = squashfs_readdir, /* Read directory */
    .llseek = generic_file_llseek,
};
```

### Symlink Operations

```c
/* fs/squashfs/symlink.c */
const struct inode_operations squashfs_symlink_inode_ops = {
    .get_link = squashfs_get_link,      /* Read symlink target */
    .getattr = squashfs_getattr,        /* Get attributes */
};
```

---

## Fragment Packing

SquashFS packs small files (less than one block) into **fragment blocks**:

```mermaid
block-beta
    columns 1
    block:frag["Fragment Block (128KB)"]
        columns 4
        F1["File A<br>512 bytes"] F2["File B<br>2KB"] F3["File C<br>8KB"] F4["File D<br>1KB"]
        F5["Free space<br>116KB"] F6[" "] F7[" "] F8[" "]
    end
```

This dramatically improves compression ratio because many small files are compressed together.

---

## Usage Examples

### Creating Images

```bash
# Basic image creation
mksquashfs /source /image.squashfs

# With specific compression and block size
mksquashfs /source /image.squashfs -comp zstd -b 256K

# Append to existing image
mksquashfs /newfiles /image.squashfs -noappend

# Exclude patterns
mksquashfs /source /image.squashfs -e "*.tmp" -e ".git"

# With reproducible timestamps
mksquashfs /source /image.squashfs -all-time 0

# Parallel compression (faster)
mksquashfs /source /image.squashfs -processors 8
```

### Mounting

```bash
# Mount squashfs image
mount -t squashfs /image.squashfs /mnt

# Loopback mount
mount -o loop /image.squashfs /mnt

# Mount from compressed offset (e.g., embedded in firmware)
mount -t squashfs -o offset=1024 /firmware.bin /mnt

# Mount with specific decompressor
mount -t squashfs -o compressor=zstd /image.squashfs /mnt
```

### Inspecting Images

```bash
# List contents
unsquashfs -l /image.squashfs

# Extract all files
unsquashfs /image.squashfs

# Extract specific files
unsquashfs -f /image.squashfs /path/to/file

# Show superblock info
unsquashfs -s /image.squashfs
# Found a valid SQUASHFS 4:0 superblock on image.squashfs.
# Compression: zstd
# Block size: 131072
# Filesystem size: 12345678 bytes
# Number of inodes: 1234
```

---

## SquashFS in Practice

### Live CDs and USB

SquashFS is the standard format for Linux live systems:

```bash
# Typical live CD structure
# /casper/filesystem.squashfs — compressed root filesystem
# Boot loader mounts squashfs as root via overlayfs

# Extract live CD root
unsquashfs /casper/filesystem.squashfs
```

### Container Images

Docker and OCI container images use squashfs layers:

```bash
# Docker image layers can be squashfs
# Build squashfs-based container
buildah bud --format squashfs .

# Container runtimes can mount squashfs directly
```

### Embedded Systems

SquashFS is ideal for embedded devices with limited storage:

```bash
# Create minimal firmware image
mksquashfs /rootfs /firmware.squashfs \
    -comp xz -b 256K \
    -noappend -all-time 0 \
    -no-xattrs -no-exports
```

### Snap Packages

Ubuntu Snap packages use squashfs for application packaging:

```bash
# Snap packages are squashfs images
file /var/lib/snapd/snaps/core_12345.snap
# Squashfs filesystem, little endian, version 4.0, zstd compressed

# Mount snap
mount -t squashfs /var/lib/snapd/snaps/core_12345.snap /snap/core/current
```

---

## Performance

### Compression Ratio

Typical compression ratios by algorithm:

| Algorithm | Ratio (mixed data) | Ratio (binaries) | Ratio (text) |
|-----------|-------------------|-------------------|--------------|
| gzip | 2.5:1 | 2.0:1 | 3.5:1 |
| lz4 | 2.0:1 | 1.8:1 | 2.5:1 |
| lzo | 2.1:1 | 1.9:1 | 2.8:1 |
| xz | 3.0:1 | 2.5:1 | 4.5:1 |
| zstd | 2.8:1 | 2.3:1 | 4.0:1 |

### Read Performance

SquashFS read performance depends on:
- **Compression algorithm**: lz4/lzo are faster to decompress
- **Block size**: Larger blocks = slower random access
- **Cache**: Page cache helps with repeated reads
- **Storage**: SSD vs HDD affects I/O latency

### Optimization Tips

```bash
# For speed-critical applications
mksquashfs /source /image.squashfs -comp lz4 -b 64K

# For size-critical applications
mksquashfs /source /image.squashfs -comp xz -b 1M

# Balanced (recommended)
mksquashfs /source /image.squashfs -comp zstd -b 256K

# Parallel creation for large images
mksquashfs /source /image.squashfs -processors $(nproc) -mem 2G
```

---

## Troubleshooting

### Mount Fails

```bash
# Check if squashfs module is loaded
modprobe squashfs

# Check image validity
unsquashfs -s /image.squashfs

# Check dmesg for errors
dmesg | grep squashfs

# Try forcing specific compressor
mount -t squashfs -o compressor=gzip /image.squashfs /mnt
```

### Corrupted Image

```bash
# Check image integrity
unsquashfs -test /image.squashfs

# Force extract (skip errors)
unsquashfs -f /image.squashfs

# Check for truncated image
ls -la /image.squashfs
# Compare with expected size from mksquashfs output
```

### Performance Issues

```bash
# Check compression algorithm
unsquashfs -s /image.squashfs

# Check cache hit rate
cat /proc/fs/squashfs/cache_hits

# Profile read latency
fio --name=test --filename=/mnt/file --rw=randread --bs=4k --runtime=30
```

---

## Extended Attributes (Xattrs)

SquashFS stores extended attributes in a dedicated table, shared across inodes to save space:

```mermaid
flowchart LR
    subgraph XattrTable["Xattr Table"]
        IDX["Xattr ID table<br>(index by ID)"]
        BLK["Xattr entry blocks<br>(compressed)"]
    end

    subgraph XattrEntry["Xattr Entry"]
        PREFIX["Type prefix<br>(user/system/security)"]
        NAME["Attribute name"]
        VALUE["Attribute value"]
    end

    IDX --> BLK
    BLK --> XattrEntry
```

Each inode that has xattrs stores an `xattr` field pointing into the xattr ID table. Multiple inodes sharing identical xattr sets point to the same ID, deduplicating storage.

```bash
# Create image with xattrs
mksquashfs /source /image.squashfs -xattrs

# Create image without xattrs (smaller)
mksquashfs /source /image.squashfs -no-xattrs

# Preserve specific xattr prefixes
mksquashfs /source /image.squashfs -xattrs -xattrs-exclude '!user.*'

# Check xattrs on mounted image
getfattr -d /mnt/file
# user.mime_type="text/plain"
```

The xattr table header stores the number of xattr IDs and the lookup table offset:

```c
/* On-disk xattr ID table header */
struct squashfs_xattr_id_table {
    __le64 xattr_table_start; /* Start of xattr entries */
    __le32 xattr_ids;          /* Number of xattr IDs */
    __le32 unused;             /* Reserved */
};

/* Per-xattr-ID entry */
struct squashfs_xattr_id {
    __le64 xattr;      /* Start of xattr block */
    __le32 count;      /* Number of xattr entries */
    __le32 size;       /* Total size of xattr block */
};
```

## NFS Export Support

SquashFS supports NFS file handle export, allowing squashfs-mounted directories to be shared over NFS:

```c
/* fs/squashfs/export.c */
const struct export_operations squashfs_export_ops = {
    .fh_to_dentry  = squashfs_fh_to_dentry,
    .fh_to_parent  = squashfs_fh_to_parent,
    .get_parent    = squashfs_get_parent,
};
```

```bash
# Create image with NFS export support
mksquashfs /source /image.squashfs -exports

# Export via NFS (in /etc/exports)
# /mnt/squashfs 192.168.1.0/24(ro,fsid=0)
```

The export table is an array of inode-to-disk-location mappings:

```c
/* Export table entry: maps inode number to block + offset */
struct squashfs_export_entry {
    __le64 inode_number;     /* Inode number */
    __le64 start;            /* Block start of inode */
    __le32 offset;           /* Offset within block */
};
```

## Pseudo File Support

`mksquashfs` supports pseudo file definitions that allow injecting files with specific content, ownership, or permissions without them existing on the host:

```bash
# Pseudo file definition file (pseudo_defs.txt)
# Format: path type [mode uid gid] content
/dev/null  c  666 0 0
/dev/zero  c  666 0 0
/dev/random c  666 0 0
/tmp       d  1777 0 0
/etc/hostname f 0644 0 0 "myhost\n"

# Use pseudo definitions
mksquashfs /source /image.squashfs -pf pseudo_defs.txt

# Dynamic pseudo files (generate at creation time)
mksquashfs /source /image.squashfs -pf - <<'EOF'
/etc/hostname f 0644 0 0 "$(hostname)\n"
EOF
```

Pseudo file types:

| Type | Description | Example |
|------|-------------|---------|
| `d` | Directory | `/tmp d 1777 0 0` |
| `f` | Regular file | `/etc/hostname f 0644 0 0 "text"` |
| `l` | Symlink | `/var/run l /run` |
| `c` | Character device | `/dev/null c 666 0 0` |
| `b` | Block device | `/dev/sda b 666 0 0` |
| `p` | FIFO | `/dev/fifo p 666 0 0` |
| `s` | Socket | `/dev/socket s 666 0 0` |
| `e` | Empty entry (skip path) | `/tmp/e e` |

## mksquashfs Internals

`mksquashfs` builds the image in passes:

```mermaid
flowchart TD
    A["Pass 1: Scan source tree"] --> B["Build inode + directory metadata"]
    B --> C["Pass 2: Compress data blocks"]
    C --> D["Pack small files into fragment blocks"]
    D --> E["Compress inode table"]
    E --> F["Compress directory table"]
    F --> G["Build fragment index table"]
    G --> H["Build xattr table"]
    H --> I["Build ID table"]
    I --> J["Write superblock + tables"]
```

Key internal parameters:

```bash
# Parallel compression threads
mksquashfs /source /image.squashfs -processors $(nproc)

# Memory limit for compression (prevents OOM on large images)
mksquashfs /source /image.squashfs -mem 2G

# Sort files by type for better compression
# (puts similar files together in the image)
mksquashfs /source /image.squashfs -sort sort_file.txt
# sort_file.txt format:
# 10 *.so        # High priority (early in image)
# 5  *.py        # Medium priority
# 1  *.txt       # Low priority (late in image)

# Reproducible builds (deterministic output)
mksquashfs /source /image.squashfs \
    -all-time 0 \
    -all-root \
    -no-xattrs \
    -noappend
```

## Read Path Internals

When a process reads a file from SquashFS:

```mermaid
sequenceDiagram
    participant App as Application
    participant VFS as VFS
    participant SQFS as SquashFS
    participant Cache as Page Cache
    participant Disk as Block Device

    App->>VFS: read(fd, buf, count)
    VFS->>SQFS: squashfs_read_iter()
    SQFS->>Cache: Check page cache
    alt Cache hit
        Cache-->>SQFS: Cached pages
    else Cache miss
        SQFS->>Disk: Read compressed block
        SQFS->>SQFS: Decompress block
        SQFS->>Cache: Populate page cache
    end
    SQFS-->>VFS: Data pages
    VFS-->>App: Copy to userspace
```

### Inode Lookup Path

```c
/* Simplified inode lookup */
struct inode *squashfs_iget(struct super_block *sb, u64 ino)
{
    struct inode *inode;
    long long start;
    int offset;

    /* Convert inode number to block + offset */
    start = squashfs_ino_blk(ino);
    offset = squashfs_ino_offset(ino);

    /* Read compressed inode from the inode table */
    inode = squashfs_read_inode(sb, ino, start, offset);
    return inode;
}
```

### Decompression Pipeline

```c
/* Each decompressor implements this interface */
struct squashfs_decompressor {
    void *(*init)(struct squashfs_sb_info *, void *);
    void (*free)(void *);
    int (*decompress)(void *, void **, unsigned int,
                      void *, unsigned int, int);
    int id;
    char *name;
    int supported;
};

/* Registered decompressors */
static const struct squashfs_decompressor *decompressor[] = {
    &squashfs_zstd_comp,
    &squashfs_xz_comp,
    &squashfs_lz4_comp,
    &squashfs_lzo_comp,
    &squashfs_gzip_comp,
    NULL
};
```

## Compression Algorithm Details

### Per-Block Compression Headers

Each data block in SquashFS has a header indicating whether the data is compressed:

```c
/* Block header (stored as part of the block size field) */
/* If bit 24 is set: data is uncompressed */
/* If bit 24 is clear: data is compressed */
#define SQUASHFS_COMPRESSED_BIT    (1 << 24)
#define SQUASHFS_COMPRESSED_SIZE(B) ((B) & ~SQUASHFS_COMPRESSED_BIT)
```

```bash
# SquashFS falls back to storing uncompressed if compression
# doesn't reduce size (e.g., already-compressed media files)

# Force uncompressed blocks (for random-access workloads)
mksquashfs /source /image.squashfs -noI -noD -noF
# -noI: don't compress inodes
# -noD: don't compress data blocks
# -noF: don't compress fragments
```

### zstd Compression Tuning

```bash
# zstd compression levels (1-22, default 15 for mksquashfs)
mksquashfs /source /image.squashfs -comp zstd -Xcompression-level 1   # Fast
mksquashfs /source /image.squashfs -comp zstd -Xcompression-level 15  # Default
mksquashfs /source /image.squashfs -comp zstd -Xcompression-level 22  # Max (slow)

# xz compression levels (1-9, default 8)
mksquashfs /source /image.squashfs -comp xz -Xcompression-level 9
```

## Security Considerations

### Image Validation

```bash
# SquashFS has no built-in integrity verification
# For untrusted images, use dm-verity:

# 1. Generate verity hash tree
veritysetup format /image.squashfs /image.hash

# 2. Mount with dm-verity
mount -o ro /dev/mapper/verity_device /mnt
```

### Mount Options for Security

```bash
# Read-only (always, since squashfs is read-only)
mount -t squashfs /image.squashfs /mnt -o ro

# nosuid - prevent SUID/SGID exploitation
mount -t squashfs /image.squashfs /mnt -o nosuid

# nodev - prevent device file access
mount -t squashfs /image.squashfs /mnt -o nodev

# noexec - prevent code execution
mount -t squashfs /image.squashfs /mnt -o noexec

# Typical secure mount for untrusted images
mount -t squashfs /image.squashfs /mnt -o ro,nosuid,nodev,noexec
```

### UID/GID Handling

```bash
# SquashFS stores numeric UIDs/GIDs, not names
# The ID table maps small indices to actual UIDs/GIDs

# Create image with specific ownership
mksquashfs /source /image.squashfs -all-root  # All files owned by root
mksquashfs /source /image.squashfs -force-uid 1000
mksquashfs /source /image.squashfs -force-gid 1000

# The ID table deduplicates: if only root(0) and user(1000)
# exist, the table has 2 entries (indices 0 and 1)
```

## Kernel Configuration

```bash
# View SquashFS module parameters
modinfo squashfs

# Module is built-in on most distros; check:
grep SQUASHFS /boot/config-$(uname -r)
# CONFIG_SQUASHFS=m or CONFIG_SQUASHFS=y
# CONFIG_SQUASHFS_DECOMP_MULTI=y (per-CPU decompressors)
# CONFIG_SQUASHFS_ZSTD=y
# CONFIG_SQUASHFS_XZ=y
# CONFIG_SQUASHFS_LZ4=y
# CONFIG_SQUASHFS_LZO=y
# CONFIG_SQUASHFS_GZIP=y
```

## SquashFS vs Other Read-Only Formats

| Feature | SquashFS | EROFS | CramFS | ISO 9660 |
|---------|----------|-------|--------|----------|
| Compression | zstd/xz/lz4/lzo/gzip | lz4/lz4hc | zlib | None (external) |
| Max file size | 2^64 | 2^36 | 16MB | 4GB |
| Read-only | Yes | Yes | Yes | Yes |
| Random access | Yes | Yes | Limited | Sequential |
| Xattrs | Yes | Yes | No | ISO 9660 ext |
| NFS export | Yes | Yes | No | No |
| Primary use | Live CDs, containers, firmware | Android, containers | Embedded (legacy) | Optical media |

---

## Source Files

| File | Contents |
|------|----------|
| `fs/squashfs/super.c` | Mount/unmount, superblock |
| `fs/squashfs/inode.c` | Inode operations |
| `fs/squashfs/file.c` | File read operations |
| `fs/squashfs/dir.c` | Directory operations |
| `fs/squashfs/symlink.c` | Symlink operations |
| `fs/squashfs/decompressor.c` | Decompression framework |
| `fs/squashfs/decompressor_zstd.c` | zstd decompressor |
| `fs/squashfs/decompressor_xz.c` | xz decompressor |
| `fs/squashfs/page_actor.c` | Page cache integration |
| `include/uapi/linux/magic.h` | SquashFS magic number |

---

## Further Reading

- **Kernel documentation**: `Documentation/filesystems/squashfs.html`
- **SquashFS project**: [squashfs.sourceforge.net](https://squashfs.sourceforge.net/)
- **LWN**: ["Squashfs: lessons in filesystem upstreaming"](https://lwn.net/Articles/393825/)
- **Chris Down**: [The curious case of stalled squashfs reads](https://chrisdown.name/2018/04/17/kernel-adventures-the-curious-case-of-squashfs-stalls.html)
- **man pages**: `mksquashfs(1)`, `unsquashfs(1)`, `squashfs(5)`

---

## See Also

- Filesystems Overview — Linux filesystem landscape
- [OverlayFS](./overlayfs.md) — used with squashfs for live CDs
- [Compression](../memory/zpool.md) — kernel compression algorithms
- [Block I/O](../../storage/block-io.md) — block layer interaction
- [initramfs](../../embedded/initramfs.md) — early boot filesystem
