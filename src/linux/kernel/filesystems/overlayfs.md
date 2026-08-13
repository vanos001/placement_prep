# OverlayFS

## Introduction

OverlayFS (also written as "overlayfs") is a union filesystem for Linux that merges two directory trees — a read-only **lower** layer and a writable **upper** layer — into a single coherent view presented as the **merged** mount. First merged into the mainline kernel in version 3.18 (2014), OverlayFS has become the dominant storage driver for container runtimes (Docker, Podman, containerd) and is widely used in Live CDs, embedded systems, and package management overlays.

The key insight of OverlayFS is that it operates at the directory level rather than the block level. It doesn't virtualize block devices or maintain its own on-disk format — instead, it wraps existing filesystems (ext4, XFS, btrfs, etc.) and presents their contents through a merged directory view.

## Architecture

### Layers

OverlayFS uses three directories on the underlying filesystem:

```mermaid
graph TB
    subgraph "OverlayFS Mount (/merged)"
        M["Merged View<br>read-write"]
    end
    subgraph "Upper Layer (read-write)"
        U["upper/<br>Only modified/new files"]
    end
    subgraph "Lower Layer(s) (read-only)"
        L1["lower1/ (base)"]
        L2["lower2/ (optional overlay)"]
        L3["lower3/ (optional overlay)"]
    end
    subgraph "Work Directory"
        W["work/<br>Temporary state for atomic operations"]
    end

    M --> U
    M --> L1
    M --> L2
    M --> L3
    U -.-> W
```

- **Lower layer(s)**: One or more read-only directory trees. Multiple lower layers are stacked with the first listed being the topmost (highest priority). Typically contains the base OS image.
- **Upper layer**: A single read-write directory tree. All modifications (writes, creates, deletes) are captured here.
- **Work directory**: A temporary directory on the same filesystem as the upper layer, used internally for atomic operations (must not be shared between overlays).
- **Merged view**: The mount point that combines all layers into a single coherent tree.

### Mount Syntax

```bash
# Single lower layer
mount -t overlay overlay \
    -o lowerdir=/lower,upperdir=/upper,workdir=/work \
    /merged

# Multiple lower layers (topmost first)
mount -t overlay overlay \
    -o lowerdir=/lower2:/lower1,upperdir=/upper,workdir=/work \
    /merged
```

**Important**: The `workdir` must be on the same filesystem as `upperdir`, and must be empty. It cannot be shared between different overlay mounts.

## Upper and Lower Layers in Detail

OverlayFS combines two filesystem layers into a single merged view:

- **Lower layer(s)**: One or more read-only directory trees. Multiple lower layers are stacked with the first listed being topmost (highest priority). The lower filesystem does not need to be writable and can even be another OverlayFS. It can be any filesystem supported by Linux that has the necessary features.
- **Upper layer**: A single read-write directory tree that must support the creation of `trusted.*` and/or `user.*` extended attributes and must provide valid `d_type` in `readdir` responses (NFS is not suitable as upper). For a read-only overlay of two read-only filesystems, any filesystem type may be used.

When a name exists in both upper and lower, the upper object is visible. For non-directories, the lower object is hidden. For directories, the upper and lower are **merged** — their name lists are combined, though only the upper directory's metadata and extended attributes are reported.

### Merged Directory Behavior

At mount time, the directories specified by `lowerdir` and `upperdir` are combined:

```bash
mount -t overlay overlay -o lowerdir=/lower,upperdir=/upper,workdir=/work /merged
```

On lookup in a merged directory, OverlayFS searches both actual directories and caches the combined result in the overlay dentry. If both lookups find directories, both are stored and a merged directory is created; otherwise only one is stored (upper takes priority).

### Whiteouts and Opaque Directories

Since lower layers are read-only, OverlayFS uses **whiteouts** and **opaque directories** to record deletions:

- A **whiteout** is created as a character device with 0/0 device number (legacy) or a zero-size regular file with the `trusted.overlay.whiteout` xattr (Linux 5.11+). When found in the upper level, any matching name in the lower level is ignored.
- A directory is made **opaque** by setting `trusted.overlay.opaque=y`. An opaque upper directory completely hides any same-named lower directory.

### rename() and redirect_dir

Renaming a lower-layer or merged directory is handled in two ways:

1. **EXDEV** (default): `rename()` returns EXDEV, and applications (like `mv`) handle it by recursive copy
2. **redirect_dir**: The directory is copied up and a `trusted.overlay.redirect` xattr stores the original path. Configurable via:
   - Kernel config: `OVERLAY_FS_REDIRECT_DIR`
   - Module param: `redirect_dir=BOOL`
   - Mount option: `redirect_dir=on|follow|nofollow|off`

### xino (Extended Inode Numbers)

On 64-bit systems, the `xino` feature composes unique inode identifiers from the real `st_ino` and an underlying fsid, using high inode number bits for fsid. This makes overlay inodes distinguishable from underlying inodes:

```bash
# Enable xino
mount -t overlay overlay -o xino=on,lowerdir=/lower,upperdir=/upper,workdir=/work /merged

# Auto-enable only if persistent st_ino is guaranteed
mount -t overlay overlay -o xino=auto,...
```

## Copy-Up Mechanism

The central operation in OverlayFS is **copy-up**: when a file in a lower layer is modified, OverlayFS first copies it to the upper layer, then applies the modification there. This preserves the read-only nature of lower layers.

### Copy-Up Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant OFS as OverlayFS
    participant Upper as Upper Layer
    participant Lower as Lower Layer

    App->>OFS: write() to file "data.txt"
    OFS->>Upper: Check if file exists in upper
    Upper-->>OFS: Not found
    OFS->>Lower: Find "data.txt" in lower
    Lower-->>OFS: Found (with metadata)
    OFS->>Upper: Copy-up: create "data.txt" in upper
    Note over Upper: Full file data copied<br>Metadata copied (uid, gid, mode, xattrs)
    OFS->>Upper: Apply write to upper copy
    Upper-->>OFS: Write complete
    OFS-->>App: Write success
```

### Copy-Up Behavior Details

1. **Data copy**: The entire file content is copied, not just the modified bytes. This is a known performance consideration.
2. **Metadata preservation**: Permissions, ownership, timestamps, and extended attributes are copied.
3. **Directory copy-up**: Directories are "created" in the upper layer with `opaque` xattr (`trusted.overlay.opaque=y`) to indicate the directory should completely replace the lower version.
4. **Character/block devices**: Metadata-only copy-up; no data copy needed.
5. **Hard links**: Maintained within the upper layer after copy-up.

### Partial Copy-Up (Linux 4.19+)

For large files, copy-up is expensive. OverlayFS supports **data-only copy-up** where only the metadata layer is created in the upper directory, and the data pages are shared via reflinks or the page cache:

```bash
# With XFS (supports reflinks), copy-up is nearly instant
# The upper file gets a reflink to the lower file's data blocks
# Only modified pages trigger actual data copy
```

## Whiteouts and Deletion

Since lower layers are read-only, "deleting" a lower file requires special markers:

### Whiteout Entries

- **Character device whiteout** (legacy): A character device with 0/0 major/minor in the upper directory at the path of the deleted file.
- **Overlayfs whiteout xattr** (Linux 5.11+): Uses `trusted.overlay.whiteout` extended attribute, avoiding the need for character devices.

```bash
# Create a whiteout manually (educational; don't do this in practice)
mknod /upper/deleted_file c 0 0

# Opaque directory (marks a directory that masks lower layers)
setfattr -n trusted.overlay.opaque -v y /upper/dir
```

### Directory Opaque Flag

When a directory exists in both upper and lower, OverlayFS merges their contents. But if the upper directory should completely replace (hide) the lower one, it's marked `opaque`:

```bash
# This happens automatically when:
# 1. A lower directory is renamed over
# 2. A lower directory is removed and recreated
# 3. OverlayFS needs to mask a lower directory entirely
```

## Container Use Cases

### Docker Storage Driver

Docker's `overlay2` storage driver uses OverlayFS to implement container image layering:

```mermaid
graph TB
    subgraph "Container Layer (upper)"
        CL["/var/lib/docker/overlay2/<id>/diff"]
    end
    subgraph "Image Layers (lower, read-only)"
        L3["Layer 3: App code"]
        L2["Layer 2: Dependencies"]
        L1["Layer 1: Base OS"]
    end
    subgraph "Merged View"
        MV["/var/lib/docker/overlay2/<id>/merged"]
    end
    subgraph "Work Dir"
        WD["/var/lib/docker/overlay2/<id>/work"]
    end

    MV --> CL
    MV --> L3
    MV --> L2
    MV --> L1
```

```bash
# Inspect Docker's overlay mounts
$ docker run -d --name test nginx:alpine
$ mount | grep overlay
overlay on /var/lib/docker/overlay2/abc123.../merged type overlay
  (rw,lowerdir=/var/lib/docker/overlay2/l/L1:/var/lib/docker/overlay2/l/L2,
   upperdir=/var/lib/docker/overlay2/abc123.../diff,
   workdir=/var/lib/docker/overlay2/abc123.../work)

# View the layers
$ docker inspect test --format '{{.GraphDriver.Data}}'
```

### Container Image Sharing

Multiple containers can share the same lower layers (image), with each having its own upper layer:

```bash
# Two containers from the same image share the lower layers
$ docker run -d --name c1 nginx:alpine
$ docker run -d --name c2 nginx:alpine
# Both c1 and c2 have the same lowerdir, different upperdir
```

### Live CDs and Embedded Systems

```bash
# SquashFS as lower (read-only compressed image), tmpfs as upper
mount -t squashfs /dev/sr0 /lower
mount -t tmpfs -o size=1G tmpfs /upper
mkdir /upper/data /upper/work
mount -t overlay overlay \
    -o lowerdir=/lower,upperdir=/upper/data,workdir=/upper/work \
    /merged
```

## Performance Considerations

### Copy-Up Overhead

The biggest performance concern is copy-up:

- **Small files**: Negligible overhead.
- **Large files (GBs)**: First write triggers full file copy. Mitigation: use XFS with reflinks.
- **Metadata operations** (chmod, chown): Also trigger copy-up even if data doesn't change.

### Directory Operations

Merging multiple layers for `readdir()` requires OverlayFS to:
1. Read all lower directories
2. Read the upper directory
3. Remove whiteouts from the result
4. Deduplicate entries
5. Return the merged listing

This is slower than native filesystems for directories with many entries across layers.

### Optimization Tips

```bash
# Use XFS with reflinks for upper layer (fast copy-up)
mkfs.xfs -m reflink=1 /dev/sdb1

# Use noatime to reduce metadata copy-ups
mount -t overlay overlay -o noatime,lowerdir=/lower,upperdir=/upper,workdir=/work /merged

# Limit lower layers (fewer = faster merges)
# Each additional lower layer adds overhead
```

## Mount Options

| Option | Description | Default |
|--------|-------------|---------|
| `lowerdir=<dir>` | Lower layer directory(s), colon-separated | Required |
| `upperdir=<dir>` | Upper layer directory | Required (for R/W) |
| `workdir=<dir>` | Work directory (same FS as upperdir) | Required |
| `redirect_dir={on,off,follow,nofollow}` | Directory rename policy | off |
| `redirect_follow` | Follow redirects on lookup | off |
| `index={on,off}` | Enable inode index for NFS export | off |
| `nfs_export={on,off}` | Enable NFS export support | off |
| `xino={on,off,auto}` | Extended inode numbers | auto |
| `metacopy={on,off}` | Copy only metadata on write | off |
| `volatile` | Skip fsync (data loss risk) | off |

```bash
# Example with all options
mount -t overlay overlay \
    -o lowerdir=/lower,upperdir=/upper,workdir=/work,\
redirect_dir=on,index=on,nfs_export=on,xino=auto \
    /merged
```

## Nested Overlays

OverlayFS supports nesting: an overlay mount can be used as a lower layer of another overlay.

### Restrictions

```bash
# Linux < 5.8: nesting was NOT supported for the upper layer
# Linux >= 5.8: upper can also be an overlay

# Example: overlay as lower layer
mount -t overlay overlay -o lowerdir=/base /overlay1
mount -t overlay overlay -o lowerdir=/overlay1,upperdir=/upper2,workdir=/work2 /merged

# Example: overlay as both lower and upper (5.8+)
mount -t overlay overlay -o lowerdir=/base /overlay1
mount -t overlay overlay -o lowerdir=/base,upperdir=/overlay1,workdir=/work2 /nested
```

### Verification

```bash
# Check kernel version for nesting support
$ uname -r
5.15.0

# Test nesting
$ mkdir -p /base/{a,b} /upper1/{data,work} /upper2/{data,work}
$ echo "base file" > /base/a/base.txt
$ mount -t overlay overlay -o lowerdir=/base,upperdir=/upper1/data,workdir=/upper1/work /mnt/layer1
$ echo "layer1 file" > /mnt/layer1/a/layer1.txt

# Use layer1 as lower for layer2
$ mount -t overlay overlay -o lowerdir=/mnt/layer1,upperdir=/upper2/data,workdir=/upper2/work /mnt/merged
$ ls /mnt/merged/a/
base.txt  layer1.txt
```

## Limitations

1. **No copy-down**: Deleting or modifying files in lower layers is impossible; only upper is writable.
2. **Stale NFS file handles**: After copy-up, lower-layer file handles become stale.
3. **fanotify/inotify**: File watching on overlay mounts has limitations (events from lower layers may not be fully reported).
4. **No page cache sharing between layers**: Files accessed through the overlay get their own page cache entries, separate from direct access to the underlying layers.
5. **xattr support**: Requires the underlying filesystem to support extended attributes.
6. **Filesystem quotas**: Not supported on overlay mounts.
7. **Lower layer modification**: Changing lower layer contents while overlay is mounted can cause inconsistencies.

## Implementation Details

### Key Source Files

- **`fs/overlayfs/super.c`** — Mount/unmount, superblock operations
- **`fs/overlayfs/dir.c`** — Directory operations (lookup, readdir, rename)
- **`fs/overlayfs/file.c`** — File operations (read, write, mmap)
- **`fs/overlayfs/copy_up.c`** — Copy-up implementation
- **`fs/overlayfs/util.c`** — Utility functions
- **`fs/overlayfs/inode.c`** — Inode operations
- **`fs/overlayfs/namei.c`** — Name lookup and resolution

### OVL Inode Structure

```c
/* Simplified from fs/overlayfs/ovl_entry.h */
struct ovl_inode {
    struct inode vfs_inode;        /* VFS inode */
    struct dentry *upperdentry;    /* Upper layer dentry (NULL if lower only) */
    struct ovl_entry *oe;          /* Lower layer entries */
    loff_t i_size;                 /* Cached size */
    unsigned long flags;           /* OVL_* flags */
    struct inode *lowerdata;       /* Real inode for data (if redirected) */
};
```

## Overlay Security

### Security Context Labeling

OverlayFS inherits security contexts from the underlying filesystem:

```bash
# Check security contexts on overlay
ls -Z /merged/

# SELinux MCS labels are preserved through copy-up
# Each container gets unique categories for isolation

# Docker assigns unique MCS labels
docker run -Z myimage

# Verify container isolation
ls -Z /var/lib/docker/overlay2/*/merged/
```

### AppArmor and Overlay

```bash
# AppArmor profiles apply to overlay mounts
# Docker default profile restricts overlay access

# View AppArmor status for container
docker inspect --format '{{.AppArmorProfile}}' <container>

# AppArmor profile stacking (Linux 5.1+)
# Multiple profiles can apply to overlay-mounted containers
```

## Advanced Container Patterns

### Development Overlays

```bash
# Development overlay: base image + local changes
mount -t overlay overlay \
    -o lowerdir=/opt/base-image,upperdir=/home/dev/overlay-upper,workdir=/tmp/overlay-work \
    /opt/dev-env

# Changes captured in upper, base unchanged
# Easy reset: rm -rf /home/dev/overlay-upper/*
```

### Multi-Stage Overlays

```bash
# Stage 1: Build
mount -t overlay overlay \
    -o lowerdir=base,upperdir=build-upper,workdir=build-work \
    /merged-build
# Install build tools, compile application

# Stage 2: Runtime (copy only needed artifacts)
mount -t overlay overlay \
    -o lowerdir=base,upperdir=runtime-upper,workdir=runtime-work \
    /merged-runtime
```

## Overlay Performance Deep Dive

### Reducing Copy-Up Overhead

```bash
# Use XFS with reflinks for instant copy-up
mkfs.xfs -m reflink=1 /dev/sdb1
mount /dev/sdb1 /var/lib/overlay

# Verify reflink support
xfs_info /var/lib/overlay | grep reflink
# reflink=1 means reflinks enabled
```

### Volatile Mode for Build Containers

```bash
# Enable volatile for faster writes (no fsync)
mount -t overlay overlay \
    -o lowerdir=/lower,upperdir=/upper,workdir=/work,volatile \
    /merged

# Warning: data loss on crash
# Ideal for: CI/CD, build containers, ephemeral workloads
# Don't use for: databases, persistent storage
```

### Monitoring Overlay Performance

```bash
# Monitor copy-up operations
inotifywait -m -r /var/lib/docker/overlay2/*/upper &

# Check overlay disk usage
du -sh /var/lib/docker/overlay2/*

# View overlay mount options
mount -t overlay
findmnt -t overlay -o TARGET,OPTIONS

# Check for overlay warnings
dmesg | grep -i overlay
```

## Testing and Debugging

### Verifying Overlay Mount

```bash
# Check overlay mount details
$ mount | grep overlay
overlay on /merged type overlay (rw,relatime,lowerdir=/lower,upperdir=/upper,workdir=/work)

# View mount info with propagation
$ findmnt -t overlay
TARGET   SOURCE   FSTYPE OPTIONS
/merged  overlay  overlay rw,relatime,lowerdir=/lower,upperdir=/upper,workdir=/work

# Check file origin (upper vs lower)
$ stat /merged/file.txt
  File: /merged/file.txt
  Size: 1024        Blocks: 8          IO Block: 4096   regular file
  # If in upper: shows upper device/inode
  # If in lower: shows lower device/inode

# Check overlay debugfs (if available)
cat /sys/kernel/debug/overlayfs/*/info

# View overlay mount options in detail
grep overlay /proc/mounts
```

### Debugging Copy-Up

```bash
# Watch copy-up operations
$ inotifywait -m /upper &
echo "test" > /merged/newfile.txt
# inotify shows CREATE event in /upper

# Check whiteouts
$ ls -la /upper/deleted_file
c--------- 1 root root 0, 0 ... /upper/deleted_file  # Whiteout

# Verify opaque directory
$ getfattr -n trusted.overlay.opaque /upper/dir
# file: upper/dir
trusted.overlay.opaque="y"

# Check metacopy xattr
$ getfattr -n overlay.metacopy /upper/file.txt
```

### Tracing Overlay Operations

```bash
# Trace overlay function calls
sudo trace-cmd record -p function -l ovl_* sleep 5
sudo trace-cmd report

# Use bpftrace to trace copy-up
sudo bpftrace -e 'kprobe:ovl_copy_up { @[comm] = count(); }'

# Trace whiteout creation
sudo bpftrace -e 'kprobe:ovl_do_whiteout { @[comm] = count(); }'

# Monitor overlay layer access
sudo bpftrace -e '
    kprobe:ovl_lookup { @[comm, str(arg1)] = count(); }
'
```

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| EBUSY on mount | workdir not empty | Clean workdir or use fresh dir |
| Files not visible | Whiteout hiding lower | Check for whiteout markers |
| Stale file handles | Copy-up invalidates lower handles | Reopen files after modification |
| Permission denied | Missing xattr support | Use filesystem with xattr support |
| Performance slow | Many lower layers | Reduce layer count |

## References

- [OverlayFS kernel documentation](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html)
- [Docker overlay2 storage driver](https://docs.docker.com/storage/storagedriver/overlayfs-driver/)
- [OverlayFS design document](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/Documentation/filesystems/overlayfs.rst)
- [LWN: An union filesystem for Linux](https://lwn.net/Articles/396439/)
- [LWN: Overlayfs improvements](https://lwn.net/Articles/612930/)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html
- https://docs.kernel.org/filesystems/overlayfs.html — Official kernel OverlayFS documentation
- https://man7.org/linux/man-pages/man5/overlayfs.5.html (mount options)
- https://lwn.net/Articles/396439/ — "An union filesystem for Linux"
- https://lwn.net/Articles/612930/ — "Overlayfs: improvements and more"
- https://docs.docker.com/storage/storagedriver/select-storage-driver/

## Related Topics

- [tmpfs](./tmpfs.md) — Often used as the upper layer for ephemeral overlays
- [mounting](./mounting.md) — Mount system calls and mount namespaces used by overlay
- [superblock](./superblock.md) — How OverlayFS manages its superblock
- [inode](./inode.md) — OVL inode management and VFS integration
