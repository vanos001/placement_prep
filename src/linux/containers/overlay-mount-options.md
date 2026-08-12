# Overlay Mount Options

## Overview

OverlayFS (also called overlayfs) is a union mount filesystem that combines multiple directory trees (layers) into a single merged view. It is the basis for container image layers in Docker, Podman, and OCI-compatible runtimes. The overlay mount has numerous options that control caching, metadata handling, copy-up behavior, and performance characteristics.

This page covers the advanced mount options available in modern kernels (5.x+), including `index`, `metacopy`, `redirect_dir`, `xino`, and `volatile`.

## Basic Mount

```bash
# Basic overlay mount
mount -t overlay overlay \
    -o lowerdir=/lower,upperdir=/upper,workdir=/work \
    /merged

# Multiple lower layers (colon-separated, leftmost is highest priority)
mount -t overlay overlay \
    -o lowerdir=/lower2:/lower1,upperdir=/upper,workdir=/work \
    /merged
```

| Option | Required | Description |
|--------|----------|-------------|
| `lowerdir` | Yes | Read-only lower layer(s), colon-separated |
| `upperdir` | No* | Read-write upper layer (not needed for read-only mounts) |
| `workdir` | No* | Working directory for atomic operations (required with upperdir) |

*`upperdir` and `workdir` are optional for read-only mounts (no upper layer).

## index

```bash
mount -t overlay overlay -o index=on ...
```

### Purpose

The `index` option enables overlay's **directory index** feature, which tracks the origin of files that have been copied up. This is essential for **NFS export** support and improves **inode number stability**.

### How It Works

When a file in a lower layer is modified (triggering a copy-up), overlay creates an **index entry** in `<workdir>/index/`. This entry maps the lower layer's file identifier (origin inode) to the upper layer's new inode:

```
/work/index/<xattr-based-key> → upper layer file
```

The index key is derived from the lower file's origin (device + inode number + UUID).

### Benefits

1. **NFS export**: The index allows overlay to map file handles to the correct layer, enabling NFS export of overlay mounts.
2. **Hard link preservation**: When a lower file has hard links, the index ensures all links are correctly copied up and remain linked in the upper layer.
3. **Inode stability**: File handles (used by NFS and some applications) remain valid across copy-up operations.

### Behavior

| Value | Effect |
|-------|--------|
| `index=on` | Enable index (default when NFS export is possible) |
| `index=off` | Disable index (saves disk space, prevents NFS export) |
| `index=auto` | Enable index only if the filesystem supports xattrs |

### Trade-offs

- **Disk usage**: Index entries consume space in the work directory
- **Performance**: Maintaining the index has a small overhead per copy-up
- **NFS requirement**: NFS export requires `index=on`

### Checking Index

```bash
# View index entries
ls -la /workdir/index/

# Each entry is a named file (the key) pointing to the upper inode
stat /workdir/index/<key>
```

## metacopy

```bash
mount -t overlay overlay -o metacopy=on ...
```

### Purpose

The `metacopy` option optimizes copy-up operations by copying **only metadata** (not file data) when a file's metadata changes but its data doesn't. This is a significant optimization for container workloads where metadata operations (chmod, chown, setxattr) are common.

### How It Works

Without `metacopy`, any modification to a lower file triggers a **full copy-up**: both metadata and data are copied from the lower to the upper layer. With `metacopy=on`:

1. **Metadata-only change** (e.g., `chmod`): only the inode attributes are copied to the upper layer. The data blocks remain in the lower layer.
2. **Data change** (e.g., `write`): full copy-up (data + metadata) occurs.
3. The upper layer inode is marked with a special xattr (`overlay.metacopy`) indicating it has no data in the upper layer.

### Copy-Up Decision Matrix

| Operation | metacopy=off | metacopy=on |
|-----------|-------------|-------------|
| chmod | Full copy-up | Metadata only |
| chown | Full copy-up | Metadata only |
| setxattr | Full copy-up | Metadata only |
| write | Full copy-up | Full copy-up |
| truncate | Full copy-up | Full copy-up |
| rename | Full copy-up | Full copy-up |

### Xattr Marker

```bash
# Check if a file has a metacopy marker
getfattr -n overlay.metacopy /merged/file.txt
# Returns the lower file's origin information
```

### Benefits

- **Reduced disk usage**: metadata changes don't waste space copying data
- **Faster operations**: chmod, chown, setxattr are much faster
- **Container optimization**: many container operations are metadata-only

### Limitations

- Requires `index=on` (or `index=auto` which enables it when xattrs are supported)
- If the lower layer becomes unavailable (e.g., unmounted), files with metacopy markers become inaccessible
- Some older kernels may not support reading metacopy files

### Trade-offs

```bash
# Check current metacopy state
cat /sys/module/overlay/parameters/metacopy
```

## redirect_dir

```bash
mount -t overlay overlay -o redirect_dir=on ...
```

### Purpose

The `redirect_dir` option controls how **directory renames** are handled across layers. When a directory from a lower layer is renamed in the overlay, the new directory location must be recorded so that subsequent lookups find it.

### How It Works

When `redirect_dir=on`:

1. A directory rename triggers a copy-up of the directory to the upper layer.
2. A **redirect xattr** (`overlay.redirect`) is set on the copied-up directory, recording the original path.
3. During lookup, if overlay encounters a redirect xattr, it follows it to find the original directory location.

Without `redirect_dir`, directory renames across the lower→upper boundary are not supported (operation fails with `EXDEV`).

### Redirect Xattr

```bash
# View redirect xattr
getfattr -n overlay.redirect /merged/renamed_dir
# Returns: "/original/path/in/lower"
```

### Values

| Value | Effect |
|-------|--------|
| `redirect_dir=on` | Enable directory redirects |
| `redirect_dir=off` | Disable (renames fail with EXDEV) |
| `redirect_dir=follow` | Follow redirects but don't create new ones |
| `redirect_dir=nofollow` | Don't follow or create redirects |
| `redirect_dir=on+follow` | Both create and follow (most permissive) |

### Use Cases

- **Container filesystem modifications**: when a container modifies a directory from the image layer
- **Atomic renames**: ensures directory renames work correctly across layers
- **NFS export**: directory redirects must be enabled for correct NFS behavior

### Limitations

- Renaming a directory from lower to upper creates a redirect; subsequent lower-layer modifications to the original directory won't be visible through the new name
- Multiple renames of the same directory create chains of redirects

## xino (Extended Inode Numbers)

```bash
mount -t overlay overlay -o xino=on ...
```

### Purpose

The `xino` option controls **extended inode number** handling. OverlayFS needs unique inode numbers for all files in the merged view, but multiple lower layers may have conflicting inode numbers.

### The Inode Number Problem

Each filesystem assigns its own inode numbers. When overlay combines multiple layers:

- Lower layer A: inode 100 = `foo.txt`
- Lower layer B: inode 100 = `bar.txt`
- These must have different inode numbers in the merged view

Without `xino`, overlay allocates inode numbers dynamically, which can change between mounts (breaking file handle stability).

### How xino Works

When `xino=on`:

1. Overlay uses **64-bit inode numbers** by combining the layer identifier with the original inode number.
2. The high bits encode the layer (or a per-inode xattr), the low bits encode the original inode.
3. This provides stable, unique inode numbers without a separate inode allocation table.

```c
/* Conceptual encoding (simplified) */
ino_t merged_ino = (layer_id << 48) | (orig_ino & 0x0000FFFFFFFFFFFF);
```

### Values

| Value | Effect |
|-------|--------|
| `xino=on` | Enable 64-bit extended inode numbers |
| `xino=off` | Disable (use dynamic inode allocation) |
| `xino=auto` | Enable if the underlying filesystem supports 64-bit inodes |

### Benefits

- **Stable file handles**: inode numbers don't change between mounts
- **NFS compatibility**: NFS relies on stable inode numbers
- **No extra storage**: encoded in the inode number itself

### Limitations

- Requires underlying filesystem to support 64-bit inode numbers (ext4, XFS, btrfs do; tmpfs may not)
- 64-bit inode numbers may break 32-bit applications that assume 32-bit inodes
- Some userspace tools may not handle 64-bit inodes correctly

### Checking

```bash
# Check if xino is enabled
mount | grep overlay
# Look for xino=on in the options

# Check inode numbers
ls -i /merged/file.txt
stat /merged/file.txt
```

## volatile

```bash
mount -t overlay overlay -o volatile ...
```

### Purpose

The `volatile` option disables **fsync** for the upper layer, significantly improving write performance at the cost of data durability. This is designed for **container workloads** where data persistence across container restarts is not required.

### How It Works

When `volatile` is set:

1. `fsync()` and `fdatasync()` on overlay files become **no-ops** for the upper layer.
2. `sync` and `syncfs` skip the upper layer.
3. Data is still written to the page cache and will eventually reach disk, but there's no guarantee it's durable on crash.

### Performance Impact

Without `volatile`:

```bash
# Every fsync triggers:
# 1. Flush upper layer data to disk
# 2. Flush upper layer metadata to disk
# 3. Potential sync of work directory
# This is expensive on slow storage (HDD, network storage)
```

With `volatile`:

```bash
# fsync is a no-op — immediate return
# Writes are buffered and flushed asynchronously
# Significant speedup for fsync-heavy workloads (databases, package managers)
```

### Container Usage

```bash
# Docker uses volatile for non-persistent container storage
docker run --mount type=overlay,source=lower,target=/app \
           --storage-opt overlay.volatile=true \
           myimage

# Or in storage driver configuration
# /etc/docker/daemon.json
{
    "storage-driver": "overlay2",
    "storage-opts": ["overlay2.volatile=true"]
}
```

### Data Loss Risk

With `volatile`:

- **Crash recovery**: Data written before the last successful `sync` (by the host) may be lost on kernel crash.
- **Container restart**: Unflushed data is lost when the container is removed.
- **Not suitable for**: databases that require durability, persistent storage volumes.

### When to Use

| Scenario | Use volatile? |
|----------|--------------|
| Ephemeral container workloads | Yes |
| CI/CD build containers | Yes |
| Database containers with volumes | No (use volumes for persistence) |
| Persistent application storage | No |
| Read-heavy containers | Doesn't matter |

## nfs_export

```bash
mount -t overlay overlay -o nfs_export=on ...
```

### Purpose

Enables NFS export support for the overlay mount. This allows the overlay to be exported via NFS server.

### Requirements

- `index=on` (required for file handle mapping)
- `redirect_dir=on` (required for directory operations)
- `xino=auto` or `on` (recommended for stable inode numbers)

### Values

| Value | Effect |
|-------|--------|
| `nfs_export=on` | Enable NFS export |
| `nfs_export=off` | Disable NFS export (default) |

## Combined Options Example

```bash
# Full-featured container overlay mount
mount -t overlay overlay \
    -o lowerdir=/var/lib/container/lower \
    -o upperdir=/var/lib/container/upper \
    -o workdir=/var/lib/container/work \
    -o index=on \
    -o metacopy=on \
    -o redirect_dir=on \
    -o xino=auto \
    -o volatile \
    /var/lib/container/merged
```

```bash
# NFS-exportable overlay
mount -t overlay overlay \
    -o lowerdir=/srv/images/base \
    -o upperdir=/srv/exports/upper \
    -o workdir=/srv/exports/work \
    -o index=on \
    -o redirect_dir=on \
    -o nfs_export=on \
    /srv/exports/merged
```

```bash
# Minimal read-only overlay (no upper layer)
mount -t overlay overlay \
    -o lowerdir=/lower2:/lower1 \
    /merged
```

## Option Compatibility Matrix

| Option | Requires | Conflicts With | Default |
|--------|----------|---------------|---------|
| `index=on` | xattr support | — | auto |
| `metacopy=on` | `index=on` | — | off |
| `redirect_dir=on` | — | — | off |
| `xino=on` | 64-bit inodes | — | auto |
| `volatile` | upperdir | — | off |
| `nfs_export=on` | `index=on`, `redirect_dir=on` | — | off |

## Runtime Information

### /proc/mounts

```bash
# Check overlay mount options
mount | grep overlay
# overlay on /merged type overlay (rw,relatime,lowerdir=...,upperdir=...,workdir=...,index=on,metacopy=on)
```

### /sys/module/overlay/parameters/

```bash
# Global overlay parameters
ls /sys/module/overlay/parameters/

# Check specific parameter
cat /sys/module/overlay/parameters/metacopy
```

### Debugfs

```bash
# Overlay-specific debug info (if available)
cat /sys/kernel/debug/overlayfs/*/info
```

## Implementation Notes

### Copy-Up Process

When a file needs to be copied up:

1. Create the target in the upper layer (preserving metadata)
2. Copy data blocks from lower to upper
3. Copy xattrs from lower to upper
4. If `metacopy=on` and only metadata changed, skip step 2
5. If `index=on`, create an index entry
6. If the file has hard links in lower, copy all linked files and preserve links

### Atomic Operations

The `workdir` is used for atomic operations:

- **Copy-up**: file is created in `workdir` first, then moved to `upperdir` atomically
- **Whiteout**: opaque directories and deleted files are marked with whiteout entries in `upperdir`
- **Index**: index entries are created in `workdir/index/`

### Whiteouts

When a file in a lower layer is "deleted" in the overlay:

- A **whiteout** (character device 0,0) is created in the upper layer
- During lookup, whiteouts cause the lower file to be hidden
- Opaque directories use the `overlay.opaque` xattr

## Performance Tuning

### Benchmarking Overlay Options

```bash
#!/bin/bash
# benchmark_overlay.sh - Compare overlay mount options

UPPER=/tmp/overlay-upper
LOWER=/tmp/overlay-lower
WORK=/tmp/overlay-work
MERGED=/tmp/overlay-merged

mkdir -p $UPPER $LOWER $WORK $MERGED

# Create test data in lower layer
for i in $(seq 1 1000); do
    echo "file $i content" > $LOWER/file_$i.txt
done

# Test 1: Default options
echo "=== Default ==="
mount -t overlay overlay -o lowerdir=$LOWER,upperdir=$UPPER,workdir=$WORK $MERGED
time (for i in $(seq 1 1000); do cat $MERGED/file_$i.txt > /dev/null; done)
umount $MERGED
rm -f $UPPER/*

# Test 2: With metacopy
echo "=== metacopy=on ==="
mount -t overlay overlay -o lowerdir=$LOWER,upperdir=$UPPER,workdir=$WORK,metacopy=on $MERGED
time (for i in $(seq 1 1000); do chmod 644 $MERGED/file_$i.txt; done)
umount $MERGED
rm -f $UPPER/*

# Test 3: With volatile
echo "=== volatile ==="
mount -t overlay overlay -o lowerdir=$LOWER,upperdir=$UPPER,workdir=$WORK,volatile $MERGED
time (for i in $(seq 1 1000); do echo "new" > $MERGED/file_$i.txt; done)
umount $MERGED
```

### Optimal Options for Different Workloads

| Workload | Recommended Options | Reason |
|----------|-------------------|--------|
| Container runtime | `metacopy=on,volatile` | Fast metadata ops, no durability needed |
| NFS export | `index=on,redirect_dir=on,nfs_export=on` | Required for NFS support |
| Build containers | `volatile` | Fast fsync-heavy operations |
| Database containers | Default (no volatile) | Durability required |
| Read-heavy workloads | `xino=on` | Stable inodes for caching |
| Live CD | Default | Read-only lower, minimal upper |

### Copy-Up Optimization

```bash
# Use XFS with reflinks for near-instant copy-up
mkfs.xfs -m reflink=1 /dev/sdb1
mount /dev/sdb1 /var/lib/overlay-upper

# Verify reflink support
xfs_info /var/lib/overlay-upper | grep reflink
# reflink=1 means reflinks are enabled

# Without reflinks, copy-up copies entire file
# With reflinks, copy-up creates a reference (CoW)
# Modified pages are copied on demand
```

## Debugging Overlay Issues

### Checking Mount Options

```bash
# View current overlay mount options
mount -t overlay
cat /proc/mounts | grep overlay
findmnt -t overlay -o TARGET,OPTIONS

# Check specific option values
grep -o 'metacopy=[^,]*' /proc/mounts
grep -o 'index=[^,]*' /proc/mounts
```

### Tracing Copy-Up Operations

```bash
# Watch copy-up in real time (requires inotifywait)
inotifywait -m -r /upper &

# Trigger a copy-up
echo "test" > /merged/file.txt
# inotifywait shows CREATE event in /upper

# Check metacopy xattr
getfattr -n overlay.metacopy /upper/file.txt

# Check redirect xattr
getfattr -n overlay.redirect /upper/renamed_dir
```

### Common Error Patterns

```bash
# Error: "mount: /merged: wrong fs type, bad option, bad superblock"
# Cause: workdir not empty or on different filesystem
# Fix: Clean workdir, ensure same filesystem as upperdir
rm -rf /work/*
mount -t overlay overlay -o lowerdir=/lower,upperdir=/upper,workdir=/work /merged

# Error: "Invalid argument"
# Cause: Incompatible options
# Fix: Check kernel version supports the options
uname -r
grep OVERLAY_FS /boot/config-$(uname -r)

# Error: Files not visible in merged view
# Cause: Whiteout hiding lower files
# Fix: Check for whiteout markers
ls -la /upper/missing_file
c--------- 1 root root 0, 0 ... /upper/missing_file  # Whiteout
```

### Overlay Debugfs

```bash
# View overlay debug information (if available)
cat /sys/kernel/debug/overlayfs/*/info

# Example output:
# lowerdir=/lower
# upperdir=/upper
# workdir=/work
# mount time: Mon Jan 15 10:30:00 2024
# metacopy=on
# index=on
```

## Kernel Version Compatibility

| Feature | Minimum Kernel | Notes |
|---------|---------------|-------|
| Basic overlay | 3.18 | Initial mainline merge |
| Multiple lower layers | 3.18 | Colon-separated lowerdir |
| index | 4.13 | Directory index for NFS export |
| metacopy | 4.19 | Metadata-only copy-up |
| redirect_dir | 4.12 | Directory rename support |
| xino | 4.15 | Extended inode numbers |
| volatile | 5.0 | Skip fsync |
| nfs_export | 5.10 | NFS export support |
| Whiteout xattr | 5.11 | Non-device whiteouts |
| Nested overlay (upper) | 5.8 | Overlay as upper layer |
| FUSE passthrough | 6.2 | Direct I/O bypass |

```bash
# Check kernel overlay features
grep OVERLAY_FS /boot/config-$(uname -r)
# CONFIG_OVERLAY_FS_REDIRECT_DIR=y
# CONFIG_OVERLAY_FS_REDIRECT_ALWAYS_FOLLOW=y
# CONFIG_OVERLAY_FS_INDEX=y
# CONFIG_OVERLAY_FS_METACOPY=y
# CONFIG_OVERLAY_FS_NFS_EXPORT=y
```

## Source Files

- `fs/overlayfs/super.c` — mount option parsing
- `fs/overlayfs/copy_up.c` — copy-up implementation
- `fs/overlayfs/dir.c` — directory operations
- `fs/overlayfs/inode.c` — inode operations
- `fs/overlayfs/util.c` — utility functions
- `fs/overlayfs/namei.c` — name lookup
- `fs/overlayfs/file.c` — file operations
- `Documentation/filesystems/overlayfs.rst` — comprehensive documentation

## Further Reading

- **Documentation/filesystems/overlayfs.rst** — kernel documentation
- **Documentation/filesystems/overlayfs-options.rst** — mount options reference
- **LWN: OverlayFS** — <https://lwn.net/Articles/642905/>
- **Docker storage driver documentation** — overlay2 driver details
- **OCI image spec** — image layer format
- **containers/storage** — <https://github.com/containers/storage>

## See Also

- [OverlayFS](../kernel/filesystems/overlayfs.md) — OverlayFS overview
- [VFS](../kernel/filesystems/vfs.md) — Virtual File System layer
- [Container Runtime](runtime-internals.md) — container execution
- Docker Storage — container storage drivers
- [tmpfs](../kernel/filesystems/tmpfs.md) — temporary filesystem (often used for workdir)
