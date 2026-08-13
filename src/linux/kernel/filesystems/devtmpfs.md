# devtmpfs

## Introduction

devtmpfs is a kernel-maintained virtual filesystem that provides automatic device node creation. It was introduced in Linux 2.6.32 (2009) by Kay Sievers and Greg Kroah-Hartman to solve the coldplug problem: the need for device nodes to exist before userspace (udev) starts. devtmpfs is mounted at `/dev` and the kernel itself creates and removes device nodes as drivers register and unregister devices.

Before devtmpfs, the system relied on `devfs` (deprecated, removed in 2.6.13) or static `/dev` entries created by `MAKEDEV`, or a userspace daemon (udev/mdev) that reacted to kernel uevents. devtmpfs moved this responsibility back into the kernel, ensuring `/dev` is populated from the earliest boot stage.

## How devtmpfs Works

### Kernel Driver Model Integration

devtmpfs hooks into the Linux device model (`drivers/base/`). When a device driver calls `device_register()` or similar functions, the kernel's driver core calls `devtmpfs_create_node()`:

```mermaid
sequenceDiagram
    participant Driver as Device Driver
    participant DM as Device Model (core)
    participant DT as devtmpfs
    participant UE as Uevent → Udev

    Driver->>DM: device_add()
    DM->>DT: devtmpfs_create_node(dev)
    Note over DT: Creates /dev/<name><br>with correct major/minor<br>permissions, uid, gid
    DM->>UE: kobject_uevent(KOBJ_ADD)
    Note over UE: Udev receives uevent,<br>applies rules,<br>may rename/symlink
    UE->>UE: Apply udev rules
```

### Device Node Creation

When a device is registered:

1. The kernel driver core determines the device name (from `devt` and subsystem)
2. `devtmpfs_create_node()` creates a device node in the devtmpfs mount
3. Permissions, uid, and gid are set from the device's `devtmpfs_devs` list
4. A uevent is sent to userspace (udev) for additional processing

```c
/* Simplified from drivers/base/devtmpfs.c */
int devtmpfs_create_node(struct device *dev) {
    const char *tmp = NULL;
    char *name;

    /* Determine device name */
    name = device_get_devnode(dev, &mode, &uid, &gid, &tmp);
    if (!name)
        return 0;

    /* Create the device node */
    err = vfs_mknod(&init_user_ns, d_inode(root),
                    dentry, mode, dev->devt);

    /* Set ownership */
    err = notify_change(idmap, dentry, &newattrs, NULL);
    return err;
}
```

### Device Node Removal

```c
int devtmpfs_delete_node(struct device *dev) {
    const char *tmp = NULL;
    char *name;

    name = device_get_devnode(dev, &mode, &uid, &gid, &tmp);
    if (!name)
        return 0;

    /* Remove the device node from devtmpfs */
    err = vfs_unlink(&init_user_ns, d_inode(root), dentry, NULL);
    return err;
}
```

## devtmpfs Internals

### Memory Model

devtmpfs is built on the tmpfs infrastructure but with significant restrictions. It uses a dedicated tmpfs-like filesystem type (`devtmpfs_fs_type`) that prevents non-kernel code from creating files. The memory overhead is minimal:

```mermaid
graph LR
    subgraph "devtmpfs Memory Usage"
        A[Superblock] --> B[Inode per device node]
        B --> C[Dentry per device node]
        C --> D[No page cache entries]
        D --> E[Typical: < 2MB total]
    end
```

Key memory characteristics:
- **No data pages**: Device nodes are zero-size; only metadata (inode + dentry) consumes memory
- **Inode cache**: Each device node requires one inode (~500-1000 bytes)
- **Dentry cache**: Each name requires one dentry (~200-400 bytes)
- **No swap**: devtmpfs pages are not swappable (kernel memory)

### Security Model

devtmpfs has a strict security model that evolved over time:

| Kernel Version | Security Change |
|----------------|------------------|
| 2.6.32 | Initial: nodes created with default mode 0600 |
| 2.6.34 | `devtmpfs_set_node_perms()` callback added |
| 3.x | udev can override permissions via uevent handler |
| 5.x | `CONFIG_DEVTMPFS_SAFE` option for restrictive defaults |

```c
/* Security: devtmpfs refuses non-kernel file creation */
static int devtmpfs_mount_called;

/* Only the kernel can create files in devtmpfs */
static const struct super_operations devtmpfs_ops = {
    .statfs     = simple_statfs,
    .show_options = generic_show_options,
    /* No .create, .mkdir, etc. — kernel creates nodes directly */
};
```

### Device Naming Convention

devtmpfs follows a hierarchical naming scheme:

```bash
# Block devices: subsystem + index
/dev/sda        # First SCSI/SATA disk
/dev/sda1       # First partition on first disk
/dev/nvme0n1    # First NVMe namespace
/dev/nvme0n1p1  # First partition on first NVMe namespace

# Character devices: subsystem + index
/dev/tty0       # First virtual terminal
/dev/ttyS0      # First serial port
/dev/input/event0  # First input event device

# Special naming: subsystem:device_type:index
/dev/vga_arbiter    # VGA arbitration
/dev/autofs         # Automount device
```

### Kernel Thread: devtmpfsd

devtmpfs runs a kernel thread (`devtmpfsd`) that handles node creation requests:

```mermaid
sequenceDiagram
    participant Driver as Device Driver
    participant Core as Driver Core
    participant Queue as Request Queue
    participant Thread as devtmpfsd
    participant VFS as VFS Layer

    Driver->>Core: device_add()
    Core->>Queue: enqueue request
    Core->>Thread: wake_up(andrequest)
    Thread->>Queue: dequeue request
    Thread->>VFS: vfs_mknod() or vfs_unlink()
    VFS->>Thread: result
    Thread->>Core: complete(anddone)
    Core->>Driver: continue
```

The thread processes requests sequentially, ensuring proper ordering of device node operations.

### On-Disk Format

devtmpfs has no traditional on-disk format — it exists entirely in memory. However, it maintains a consistent internal structure:

```
devtmpfs Internal Layout:
┌─────────────────────────────────────┐
│ Superblock (devtmpfs_fs_type)       │
│  - s_magic: 0x01021994              │
│  - s_op: devtmpfs_ops               │
├─────────────────────────────────────┤
│ Root inode (/)                      │
│  - mode: 0755                       │
│  - children: device nodes           │
├─────────────────────────────────────┤
│ Device nodes                        │
│  - /dev/sda (blk 8:0)              │
│  - /dev/tty (chr 5:0)              │
│  - /dev/null (chr 1:3)             │
│  - ...                              │
└─────────────────────────────────────┘
```

### Request Queue

The devtmpfs daemon processes requests from a linked list:

```c
struct req {
    struct list_head list;      /* Link in request queue */
    struct completion *done;    /* Completion for synchronous requests */
    const char *name;           /* Device name (e.g., "sda1") */
    umode_t mode;               /* File mode (0 = delete) */
    struct device *dev;         /* Device structure pointer */
};
```

Requests are processed in FIFO order, ensuring that devices are created in the order they are registered.

## devtmpfs vs udev

```mermaid
graph TB
    subgraph "devtmpfs (kernel)"
        K1[Device registered] --> K2[Kernel creates /dev/node]
        K2 --> K3[Basic permissions set]
        K3 --> K4[Ready for immediate use]
    end
    subgraph "udev (userspace)"
        U1[Uevent received] --> U2[Match udev rules]
        U2 --> U3[Create symlinks]
        U3 --> U4[Set extended attributes]
        U4 --> U5[Run udev scripts]
    end
    K2 -->|uevent| U1
```

| Aspect | devtmpfs | udev |
|--------|----------|------|
| **Runs in** | Kernel space | User space |
| **Timing** | Immediate (at device registration) | After uevent processing (slight delay) |
| **Capabilities** | Device nodes only | Symlinks, permissions, tags, scripts |
| **Persistence** | No (rebuilt at each boot) | udev rules in `/etc/udev/rules.d/` |
| **Complex naming** | Simple (subsystem + index) | Complex rules (MAC, serial, path) |
| **Coldplug** | ✅ Works before init | ❌ Needs to be running |
| **Sysfs attributes** | Cannot read | Can read and match |

### Why Both Exist

devtmpfs provides the **base layer** — device nodes exist as soon as the driver loads. udev provides the **policy layer** — complex naming, permissions, symlinks, and trigger scripts.

```bash
# devtmpfs creates the basic node:
/dev/sda         # Created by kernel immediately

# udev creates symlinks and sets permissions:
/dev/disk/by-uuid/abc123...  → /dev/sda1
/dev/disk/by-label/DATA      → /dev/sda2
/dev/disk/by-id/ata-Samsung_SSD_870... → /dev/sda
```

### udev Rules Example

```bash
# /etc/udev/rules.d/99-custom.rules
# These rules supplement what devtmpfs already provides

# Create a persistent symlink for a specific USB device
SUBSYSTEM=="tty", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678", \
    SYMLINK+="mydevice"

# Set permissions for a specific device
SUBSYSTEM=="usb", ATTRS{serial}=="ABC123", MODE="0666"

# Run a script when a specific device appears
SUBSYSTEM=="block", ACTION=="add", KERNEL=="sd*", \
    RUN+="/usr/local/bin/on-disk-added.sh"
```

## Mount and Configuration

### Mount Point

```bash
# devtmpfs is mounted automatically during boot
$ mount | grep devtmpfs
devtmpfs on /dev type devtmpfs (rw,nosuid,noexec,size=4096k,nr_inodes=1048576,mode=755)

# Typical mount options
mount -t devtmpfs devtmpfs /dev \
    -o size=8192k,nr_inodes=2097152,mode=755
```

### Mount Options

| Option | Description | Default |
|--------|-------------|---------|
| `size=<bytes>` | Maximum filesystem size | 4096k |
| `nr_inodes=<count>` | Maximum number of inodes | Half of available RAM in pages |
| `mode=<octal>` | Default directory permissions | 755 |

### Boot-Time Mount

devtmpfs is mounted very early in the boot process, before udev starts:

```bash
# In initramfs / init
mount -t devtmpfs devtmpfs /dev

# In systemd, this is done by the kernel itself
# CONFIG_DEVTMPFS_MOUNT=y in kernel config

# Check if CONFIG_DEVTMPFS_MOUNT is enabled
$ zcat /proc/config.gz | grep DEVTMPFS
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
```

### Kernel Configuration

```bash
# Required kernel config options
CONFIG_DEVTMPFS=y          # Enable devtmpfs
CONFIG_DEVTMPFS_MOUNT=y    # Auto-mount at /dev during boot

# Without CONFIG_DEVTMPFS_MOUNT, init must mount it manually
```

## devtmpfs in initramfs

During early boot, the initramfs must mount devtmpfs before any userspace tools can access devices:

```bash
#!/bin/sh
# Typical initramfs init script

# Mount devtmpfs first — everything else depends on device nodes
mount -t devtmpfs devtmpfs /dev

# Now we can access /dev/console, /dev/null, etc.
exec 0</dev/console 1>/dev/console 2>/dev/console

# Continue with boot...
```

### Systemd's Early Mount

Systemd mounts devtmpfs very early in its initialization:

```mermaid
graph TD
    A[Kernel boots] --> B[devtmpfsd starts]
    B --> C[Mount devtmpfs on /dev]
    C --> D[systemd starts]
    D --> E[udev starts]
    E --> F[udev processes events]
    F --> G[Symlinks/permissions applied]
```

With `CONFIG_DEVTMPFS_MOUNT=y`, the kernel mounts devtmpfs automatically before init runs.

## devtmpfs vs tmpfs

While devtmpfs shares code with tmpfs, they have fundamental differences:

| Aspect | devtmpfs | tmpfs |
|--------|----------|-------|
| **Purpose** | Device nodes only | General-purpose in-memory FS |
| **File creation** | Kernel only | Any process with permissions |
| **Data storage** | None (zero-size files) | Actual file data in RAM |
| **Swap** | No (kernel memory) | Yes (can be swapped) |
| **Mount options** | Limited (size, nr_inodes, mode) | Extensive (size, nr_inodes, mode, mpol, etc.) |
| **Security** | Kernel-controlled | Standard UNIX permissions |
| **Typical mount** | /dev | /tmp, /run, /dev/shm |

## Practical Usage

### Examining Device Nodes

```bash
# List device nodes
$ ls -la /dev/sda*
brw-rw---- 1 root disk 8, 0 Jul 21 10:00 /dev/sda
brw-rw---- 1 root disk 8, 1 Jul 21 10:00 /dev/sda1
brw-rw---- 1 root disk 8, 2 Jul 21 10:00 /dev/sda2

# Character devices
$ ls -la /dev/tty*
crw-rw-rw- 1 root tty 5, 0 Jul 21 10:00 /dev/tty
crw--w---- 1 root tty 4, 0 Jul 21 10:00 /dev/tty0
crw------- 1 root root 4, 1 Jul 21 10:00 /dev/tty1

# View device major/minor numbers
$ cat /proc/devices
Character devices:
  1 mem
  4 tty
  5 /dev/tty
 10 misc
 13 input
 29 fb

Block devices:
  8 sd
  9 md
 11 sr
253 device-mapper
254 mdp
259 blkext
```

### devtmpfs in Containers

```bash
# Containers typically mount their own devtmpfs or use a minimal /dev
$ docker run --privileged alpine mount | grep devtmpfs
devtmpfs on /dev type devtmpfs (rw,nosuid,size=65536k,nr_inodes=16384,mode=755)

# Docker creates a minimal /dev for containers
$ docker run alpine ls /dev
console  fd       mqueue   ptmx     random   stderr   stdout   urandom
core     full     null     pts      shm      stdin    tty      zero
```

### Manual Device Node Creation

```bash
# devtmpfs handles this automatically, but for understanding:
$ mknod /dev/mydevice c 240 0
$ chmod 666 /dev/mydevice

# Remove when done
$ rm /dev/mydevice
```

## Performance Characteristics

devtmpfs has minimal performance overhead:

```mermaid
graph LR
    subgraph "Operation Latency"
        A[Create device node] -->|~1μs| B[In-memory only]
        C[Lookup device] -->|~100ns| D[Hash table lookup]
        E[Delete device] -->|~1μs| F[In-memory only]
    end
```

### Benchmarks

| Operation | devtmpfs | udev (userspace) |
|-----------|----------|------------------|
| Node creation | ~1μs | ~100μs (uevent + rule processing) |
| Node deletion | ~1μs | ~100μs |
| Coldplug 1000 devices | ~1ms | ~100ms |
| Memory per node | ~1KB | ~1KB (same) |

The performance advantage is most visible during:
- **Coldplug**: System boot with hundreds of devices
- **Hotplug**: Rapid device insertion (USB hubs with many devices)
- **Embedded systems**: Where udev may not run

### Memory Usage

```bash
# Check devtmpfs memory usage
$ cat /proc/mounts | grep devtmpfs
devtmpfs /dev devtmpfs rw,nosuid,noexec,size=4096k,nr_inodes=1048576,mode=755 0 0

# Count device nodes
$ ls -la /dev | wc -l
# Typical: 200-500 nodes

# Memory usage calculation:
# Each node: ~1KB inode + ~0.5KB dentry = ~1.5KB
# 500 nodes × 1.5KB = ~750KB total
```

## Implementation Details

### Key Source Files

- **`drivers/base/devtmpfs.c`** — Core devtmpfs implementation (~400 lines)
- **`drivers/base/core.c`** — Device model core (calls devtmpfs)
- **`drivers/base/devtmpfs.c`** — `devtmpfs_create_node()`, `devtmpfs_delete_node()`
- **`include/linux/devtmpfs.h`** — Header declarations

### Initialization

```c
/* From drivers/base/devtmpfs.c */
static int devtmpfsd(void *p) {
    /* This runs as a kernel thread during boot */
    char options[] = "mode=0755";

    /* Mount devtmpfs on /dev */
    err = kern_mount_data(devtmpfs_fs_type, options);

    /* Signal init that devtmpfs is ready */
    complete(&setup_done);

    /* Process requests from device drivers */
    while (!kthread_should_stop()) {
        /* Wait for device add/remove requests */
        wait_for_completion(&request);
        /* Process each request */
    }
    return 0;
}

static int __init devtmpfs_init(void) {
    /* Start the devtmpfs daemon */
    thread = kthread_run(devtmpfsd, NULL, "devtmpfsd");
    return 0;
}
subsys_initcall(devtmpfs_init);
```

### Request Processing

When a device is added or removed, the driver core posts a request to the devtmpfs daemon:

```c
struct req {
    struct list_head list;
    struct completion *done;
    const char *name;
    umode_t mode;    /* 0 means delete */
    struct device *dev;
};
```

The daemon (kernel thread) processes these requests, calling VFS operations to create or delete nodes.

## Historical Context

```mermaid
timeline
    title /dev Device Node Evolution
    1970s : Static /dev entries
          : Created by mknod during install
    1998 : devfs (Linux 2.3.46)
         : Kernel-managed, complex naming
    2000 : devfsd
         : Userspace helper for devfs
    2003 : udev
         : Userspace device manager
    2006 : devfs removed (Linux 2.6.13)
    2004 : sysfs
         : /sys exposes device topology
    2009 : devtmpfs (Linux 2.6.32)
         : Kernel-maintained /dev nodes
    Present : devtmpfs + udev
            : Best of both worlds
```

### devfs vs devtmpfs

| Aspect | devfs (1998-2006) | devtmpfs (2009+) |
|--------|-------------------|------------------|
| **Naming** | Complex (devfs naming rules) | Simple (subsystem + index) |
| **Permissions** | devfs config file | Standard UNIX permissions |
| **Hotplug** | devfsd daemon | udev (standard) |
| **Stability** | Problematic | Rock solid |
| **Maintainer** | Richard Gooch | Kay Sievers, Greg KH |
| **Kernel version** | 2.3.46 - 2.6.13 | 2.6.32+ |

devfs was removed because it tried to do too much — it had its own naming policy, permission system, and userspace daemon (devfsd). devtmpfs does one thing well: create device nodes. Policy (udev) is separate.

## Troubleshooting

```bash
# Check if devtmpfs is mounted
mount | grep devtmpfs

# Check kernel config
zcat /proc/config.gz | grep DEVTMPFS

# Verify device nodes exist
cat /proc/devices
ls -la /dev/ | head -20

# Check for missing device nodes
dmesg | grep -i "devtmpfs"

# Common issues:
# 1. CONFIG_DEVTMPFS not enabled
# 2. devtmpfs not mounted in initramfs
# 3. Permissions wrong (udev not running)
# 4. Device node not created (driver issue)
```

### Debugging Device Creation

```bash
# Watch devtmpfs events
$ udevadm monitor --kernel --property

# Check if device is registered
$ ls /sys/class/block/sda
# If exists, devtmpfs should have /dev/sda

# Force udev to reprocess
$ udevadm trigger --subsystem-match=block
$ udevadm settle
```

### Common Problems

| Problem | Cause | Solution |
|---------|-------|----------|
| No /dev nodes | devtmpfs not mounted | Check CONFIG_DEVTMPFS_MOUNT=y |
| Wrong permissions | udev not running | Start systemd-udevd |
| Missing symlinks | udev rules not loaded | Check /etc/udev/rules.d/ |
| Container /dev empty | Not mounting devtmpfs | Use --privileged or mount devtmpfs |
| Coldplug slow | Too many devices | Consider CONFIG_DEVTMPFS_MOUNT=y |

## References

- [devtmpfs kernel documentation](https://www.kernel.org/doc/html/latest/driver-api/driver-model/devres.html)
- [devtmpfs.c source](https://github.com/torvalds/linux/blob/master/drivers/base/devtmpfs.c)
- [LWN: devtmpfs](https://lwn.net/Articles/330985/)
- [LWN: The final word on devfs](https://lwn.net/Articles/250662/)
- [kernel.org: devtmpfs commit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=devtmpfs)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- https://man7.org/linux/man-pages/man5/udev.7.html
- https://man7.org/linux/man-pages/man7/udevadm.8.html
- https://lwn.net/Articles/330985/ — "Devtmphs: a new approach to /dev"
- https://lwn.net/Articles/250662/ — "The final word on devfs"
- https://www.kernel.org/doc/html/latest/driver-api/early-userspace/early_userspace_support.html

## Related Topics

- [tmpfs](./tmpfs.md) — devtmpfs is based on tmpfs infrastructure
- [mounting](./mounting.md) — How devtmpfs is mounted during boot
- [superblock](./superblock.md) — devtmpfs superblock management
- [inode](./inode.md) — Device node inodes in devtmpfs
