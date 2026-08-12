# Storage Overview

## Introduction

Storage is one of the most complex subsystems in the Linux kernel. From the moment an application issues a `write()` syscall to the instant data lands on persistent media, it traverses multiple layers—each with its own abstractions, optimizations, and failure modes. This chapter provides a comprehensive map of the Linux storage stack, covering block devices, the SCSI layer, NVMe, and storage topology.

Understanding the full I/O stack is essential for performance tuning, debugging, and capacity planning. A misconfigured I/O scheduler, a suboptimal queue depth, or a poorly designed storage topology can turn a fast NVMe drive into a bottleneck.

## The Linux I/O Stack

The Linux I/O stack is a layered architecture. Each layer adds its own abstraction and processing overhead:

```mermaid
graph TD
    A[Application / VFS] --> B["Filesystem (ext4, XFS, Btrfs)"]
    B --> C[Page Cache / Direct I/O]
    C --> D["Block I/O Layer (bio, request_queue)"]
    D --> E["I/O Scheduler (mq-deadline, BFQ, kyber)"]
    E --> F["Device Driver (SCSI, NVMe, virtio-blk)"]
    F --> G[Block Device /dev/sdX, /dev/nvme0n1]
    G --> H["Hardware (HDD, SSD, NVMe, SAN)"]
```

### Layer Descriptions

| Layer | Role | Key Data Structures |
|-------|------|---------------------|
| Application | Issues `read()`/`write()`/`open()` | File descriptors |
| VFS | Unified filesystem interface | `inode`, `dentry`, `file` |
| Filesystem | On-disk format, journaling, allocation | `super_block`, `bio` |
| Page Cache | Caches file data in RAM | `address_space`, `page` |
| Block I/O | Queues and dispatches I/O | `bio`, `request`, `request_queue` |
| I/O Scheduler | Reorders and merges I/O | Scheduler-specific queues |
| Device Driver | Talks to hardware | `Scsi_Host`, `nvme_ns` |
| Hardware | Persistent storage | Controller, NAND platters |

## Block Devices

A **block device** is a storage device that reads and writes data in fixed-size blocks (typically 512 bytes or 4096 bytes). Linux exposes block devices as device nodes under `/dev/`:

```bash
# List block devices
lsblk
# NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
# sda      8:0    0 465.8G  0 disk
# ├─sda1   8:1    0   512M  0 part /boot
# └─sda2   8:2    0 465.3G  0 part /
# nvme0n1 259:0   0 931.5G  0 disk
# └─nvme0n1p1 259:1 0 931.5G 0 part /data
```

### Device Numbers

Every block device has a **major** and **minor** number:
- **Major number**: Identifies the device driver (e.g., `8` for SCSI/SATA, `259` for NVMe)
- **Minor number**: Identifies the specific device or partition

```bash
ls -la /dev/sda /dev/nvme0n1
# brw-rw---- 1 root disk 8, 0 Jul 21 10:00 /dev/sda
# brw-rw---- 1 root disk 259, 0 Jul 21 10:00 /dev/nvme0n1
```

### Device Registration

Block devices register with the kernel through the `gendisk` structure:

```c
struct gendisk {
    int major;              /* major number */
    int first_minor;        /* first minor number */
    int minors;             /* maximum number of minors */
    const char *disk_name;  /* disk name */
    struct request_queue *queue; /* request queue */
    struct block_device_operations *fops;
    /* ... */
};
```

## The SCSI Layer

The SCSI (Small Computer Systems Interface) subsystem in Linux is remarkably broad. It handles not only actual SCSI hardware but also SATA, USB storage, and Fibre Channel devices. The kernel's SCSI layer provides a unified abstraction over diverse transport protocols.

```mermaid
graph TD
    A[Block Layer] --> B[SCSI Core - scsi_mod]
    B --> C[SCSI Upper Drivers]
    C --> D[sd - SCSI Disk]
    C --> E[sr - SCSI CD-ROM]
    C --> F[st - SCSI Tape]
    C --> G[sg - SCSI Generic]
    B --> H[SCSI Mid-Layer]
    H --> I[SCSI Low-Level Drivers]
    I --> J[ahci - SATA]
    I --> K[mpt3sas - SAS]
    I --> L[lpfc - Fibre Channel]
    I --> M[iscsi_tcp - iSCSI]
```

### SCSI Command Lifecycle

1. The block layer constructs a `struct request` and submits it to the SCSI layer
2. The SCSI mid-layer translates it into a SCSI command (`scsi_cmnd`)
3. The low-level driver sends the command to the hardware
4. The hardware completes the command and raises an interrupt
5. The completion handler propagates back up the stack

```bash
# View SCSI devices
cat /proc/scsi/scsi
# Attached devices:
# Host: scsi0 Channel: 00 Id: 00 Lun: 00
#   Vendor: ATA      Model: Samsung SSD 870  Rev: 1B6Q
#   Type:   Direct-Access                    ANSI  SCSI revision: 05

# Detailed SCSI info
lsscsi -v
# [0:0:0:0]    disk    ATA      Samsung SSD 870  1B6Q  /dev/sda
#   dir: /sys/devices/pci0000:00/0000:00:17.0/ata1/host0/target0:0:0/0:0:0:0
```

### SCSI Host Template

Each SCSI driver registers a `scsi_host_template`:

```c
static struct scsi_host_template my_scsi_template = {
    .module         = THIS_MODULE,
    .name           = "my_scsi_driver",
    .queuecommand   = my_queue_command,
    .eh_abort_handler = my_abort,
    .eh_device_reset_handler = my_device_reset,
    .can_queue      = 32,
    .this_id        = -1,
    .sg_tablesize   = 256,
    .cmd_per_lun    = 32,
};
```

## NVMe

NVMe (Non-Volatile Memory Express) is a protocol designed specifically for flash storage. Unlike SCSI, which was designed for spinning disks and tape drives, NVMe exploits the parallelism and low latency of solid-state media.

### Key NVMe Advantages

| Feature | SCSI/SATA | NVMe |
|---------|-----------|------|
| Queue depth | 32 (TCQ) or 1 (NCQ) | 65,535 queues × 65,535 commands |
| Protocol overhead | High (SCSI CDBs) | Low (simple 64-byte commands) |
| Interrupt model | Single IRQ | Per-CPU MSI-X vectors |
| Latency | ~100μs | ~10μs |
| Parallelism | Limited | Massive |

### NVMe Device Nodes

```bash
# NVMe character device
ls -la /dev/nvme0
# crw------- 1 root root 10, 154 Jul 21 10:00 /dev/nvme0

# NVMe namespace block devices
ls -la /dev/nvme0n1*
# brw-rw---- 1 root disk 259, 0 Jul 21 10:00 /dev/nvme0n1
# brw-rw---- 1 root disk 259, 1 Jul 21 10:00 /dev/nvme0n1p1

# NVMe admin character device per namespace
ls -la /dev/nvme0n1
```

### NVMe Controller Information

```bash
nvme id-ctrl /dev/nvme0
# VID       : 0x144d
# SSVID     : 0x144d
# MN        : Samsung SSD 970 EVO Plus 2TB
# FR        : 2B2QEXM7
# MDTS      : 9
# CAP       : ...
# SQES      : 0x66
# CQES      : 0x44
# NN        : 1         # Number of namespaces

nvme id-ns /dev/nvme0n1
# NSZE   : 3907029168   # Namespace size in blocks
# NCAP   : 3907029168   # Namespace capacity
# NUSE   : 1234567890   # Namespace utilization
# LBAF0  : 0x9009200    # LBA format: 512 bytes
```

## Storage Topology

Understanding storage topology means understanding the physical and logical path from CPU to persistent media.

```mermaid
graph LR
    subgraph CPU
        CORE[CPU Core]
        CACHE[L1/L2/L3 Cache]
    end
    subgraph Interconnect
        PCIE[PCIe Bus]
        QPI[QPI/UPI]
    end
    subgraph Storage
        NVME[NVMe Controller]
        SATA[AHCI Controller]
        HBA[SAS HBA]
        FC[FC HBA]
    end
    subgraph Media
        NAND[NAND Flash]
        PLATTER[HDD Platters]
        SAN_LUN[SAN LUN]
    end

    CORE --> CACHE --> PCIE
    PCIE --> NVME --> NAND
    PCIE --> SATA --> PLATTER
    PCIE --> HBA --> PLATTER
    PCIE --> FC --> SAN_LUN
```

### NUMA-Aware Storage

On multi-socket systems, storage devices are attached to specific NUMA nodes. Accessing storage from a remote NUMA node adds latency:

```bash
# Find which NUMA node a device is on
cat /sys/block/nvme0n1/device/../numa_node
# -1 (means not set or all nodes)

# More reliable method
readlink -f /sys/block/nvme0n1/device
# /sys/devices/pci0000:40/0000:40:01.1/0000:41:00.0/nvme/nvme0

# Check PCIe NUMA node
cat /sys/devices/pci0000:40/numa_node
# 0

# Use numactl to bind I/O to the correct node
numactl --cpunodebind=0 --membind=0 dd if=/dev/nvme0n1 of=/dev/null bs=1M count=1000
```

### SCSI vs NVMe Topology Comparison

```mermaid
graph TD
    subgraph "SCSI Topology"
        SC[SCSI Controller] --> SH[SCSI Host]
        SH --> ST[SCSI Target]
        ST --> SL[SCSI LUN]
        SL --> SD["/dev/sdX"]
    end
    subgraph "NVMe Topology"
        NC[NVMe Controller] --> NN[NVMe Namespace]
        NN --> NB["/dev/nvmeXnY"]
    end
```

## sysfs Block Device Information

The sysfs filesystem exposes extensive information about block devices:

```bash
# Device size (in 512-byte sectors)
cat /sys/block/sda/size
# 976773168

# Queue parameters
cat /sys/block/sda/queue/scheduler
# [mq-deadline] kyber bfq none

cat /sys/block/sda/queue/nr_requests
# 256

cat /sys/block/sda/queue/max_sectors_kb
# 1280

cat /sys/block/sda/queue/rotational
# 0

cat /sys/block/sda/queue/logical_block_size
# 512

cat /sys/block/sda/queue/physical_block_size
# 512
```

## The Multi-Queue Block Layer (blk-mq)

Linux 3.13 introduced the multi-queue block layer (`blk-mq`) to replace the legacy single-queue design. The old model used a single `request_queue` protected by a spinlock, creating a bottleneck on systems with many CPU cores and fast NVMe devices. `blk-mq` eliminates this by distributing I/O across per-CPU or per-node hardware submission queues.

### blk-mq Architecture

```mermaid
graph TD
    subgraph Software Queues
        SQ0["Software Queue CPU 0"]
        SQ1["Software Queue CPU 1"]
        SQ2["Software Queue CPU 2"]
        SQ3["Software Queue CPU 3"]
    end
    subgraph Hardware Queues
        HWQ0["Hardware Queue 0"]
        HWQ1["Hardware Queue 1"]
    end
    SQ0 --> HWQ0
    SQ1 --> HWQ0
    SQ2 --> HWQ1
    SQ3 --> HWQ1
    HWQ0 --> NVME0["NVMe Controller 0"]
    HWQ1 --> NVME1["NVMe Controller 1"]
```

Each CPU has a **software staging queue** (lock-free). The I/O scheduler operates on these queues. When the hardware is ready, requests are dispatched to **hardware submission queues** (SQs) that map directly to the device's NVMe queues or SCSI per-CPU queues.

### blk-mq Data Structures

```c
/* include/linux/blk-mq.h */
struct blk_mq_ops {
    blk_status_t (*queue_rq)(struct blk_mq_hw_ctx *,
                              const struct blk_mq_queue_data *);
    void (*commit_rqs)(struct blk_mq_hw_ctx *);
    void (*complete)(struct request *);
    /* ... */
};

struct blk_mq_tag_set {
    const struct blk_mq_ops *ops;
    unsigned int nr_hw_queues;   /* Number of hardware queues */
    unsigned int queue_depth;     /* Commands per queue */
    unsigned int numa_node;       /* NUMA affinity */
    /* ... */
};
```

### Verifying blk-mq Status

```bash
# Check if a device uses blk-mq (all modern devices do)
ls /sys/block/sda/mq/
# 0/  1/  2/  3/  (one directory per hardware queue)

# View queue mapping
ls /sys/kernel/debug/block/sda/
# state  tags  sched

# Number of hardware queues
ls /sys/block/nvme0n1/mq/ | wc -l
# 8 (matches NVMe queue count)
```

## I/O Schedulers

The I/O scheduler (also called the I/O elevator) reorders and merges requests in the software queues before dispatching them to hardware queues. Linux 5.0 removed all legacy single-queue schedulers; the modern choice is between three multi-queue schedulers (or none).

### Available Schedulers

```bash
# View available and active scheduler
$ cat /sys/block/sda/queue/scheduler
[mq-deadline] kyber bfq none

# Change scheduler
echo bfq > /sys/block/sda/queue/scheduler
```

### mq-deadline

The **mq-deadline** scheduler assigns a deadline to each request. It maintains sorted queues for both read and write operations, plus a **fifo queue** for aging. Requests approaching their deadline get priority to prevent starvation.

```mermaid
graph LR
    subgraph "mq-deadline Queues"
        RQ["Read Queue (sorted by sector)"]
        WQ["Write Queue (sorted by sector)"]
        FQ["FIFO Queue (deadline order)"]
    end
    DISPATCH["Dispatch"] --> RQ
    DISPATCH --> WQ
    DISPATCH --> FQ
    FQ -->|"Deadline approaching"| HW["Hardware"]
```

**Best for**: Database servers, general-purpose workloads where latency fairness matters.

```bash
# mq-deadline tunables
$ ls /sys/block/sda/queue/iosched/
read_expire  write_expire  writes_starved  fifo_batch  front_merges

# Default: reads expire in 500ms, writes in 5s
echo 250 > /sys/block/sda/queue/iosched/read_expire
echo 2000 > /sys/block/sda/queue/iosched/write_expire
```

### BFQ (Budget Fair Queueing)

**BFQ** provides proportional-share bandwidth allocation. Each process gets a "budget" of sectors, and BFQ distributes I/O time fairly among active processes. It excels at interactive workloads.

**Best for**: Desktop systems, mixed interactive + background workloads, USB drives (low queue depth).

```bash
# BFQ tunables
$ ls /sys/block/sda/queue/iosched/
back_seek_max  back_seek_penalty  fifo_expire_async  fifo_expire_sync
low_latency  slice_idle  slice_idle_us  slice_sync  slice_async  timeout_sync

# Enable low-latency mode (default: on)
echo 1 > /sys/block/sda/queue/iosched/low_latency
```

### Kyber

**Kyber** is a token-based scheduler designed for fast devices (NVMe). It limits the number of in-flight requests per direction (reads/writes) and adjusts based on latency targets. It has minimal CPU overhead.

**Best for**: Fast NVMe SSDs where the device queue is the bottleneck, not the scheduler.

```bash
# Kyber tunables
$ ls /sys/block/nvme0n1/queue/iosched/
read_lat_nsec  write_lat_nsec

# Target latency for reads (default: 2ms)
echo 1000000 > /sys/block/nvme0n1/queue/iosched/read_lat_nsec
# Target latency for writes (default: 10ms)
echo 5000000 > /sys/block/nvme0n1/queue/iosched/write_lat_nsec
```

### none (No Scheduler)

Passes requests directly to the hardware queue without reordering. Appropriate when the hardware itself handles scheduling (e.g., NVMe with multiple hardware queues). Lowest CPU overhead.

### Scheduler Selection Guide

```mermaid
flowchart TD
    A["Choose I/O Scheduler"] --> B{"Device type?"}
    B -->|"NVMe SSD"| C{"Multi-process?"}
    B -->|"SATA SSD"| D["mq-deadline"]
    B -->|"HDD"| E{"Desktop or Server?"}
    B -->|"USB/SD card"| F["bfq"]
    C -->|"Yes (databases)"| G["mq-deadline"]
    C -->|"No (single app)"| H["none"]
    E -->|"Desktop"| I["bfq"]
    E -->|"Server"| D
```

## Write-Back vs Write-Through Caching

The block layer and filesystem manage a **page cache** that buffers writes. Understanding the cache modes is critical for data integrity:

| Mode | Behavior | Performance | Safety |
|------|----------|-------------|--------|
| **Write-back** | Writes go to cache, flushed later | Best | Data loss on power failure |
| **Write-through** | Writes go to cache and disk simultaneously | Moderate | Safe |
| **Sync** (`O_SYNC`) | Each write waits for disk completion | Slowest | Strongest guarantee |

```bash
# View current cache mode
cat /sys/block/sda/queue/write_cache
# [write back]

# Switch to write-through (if supported)
echo 'write through' > /sys/block/sda/queue/write_cache

# Force cache flush
sync
hdparm -F /dev/sda  # For SATA drives
nvme flush /dev/nvme0n1  # For NVMe drives
```

### The fsync() Journey

```mermaid
sequenceDiagram
    participant App
    participant VFS
    participant FS as Filesystem (ext4)
    participant PC as Page Cache
    participant BL as Block Layer
    participant HW as Hardware

    App->>VFS: fsync(fd)
    VFS->>FS: vfs_fsync()
    FS->>PC: Find dirty pages for inode
    FS->>BL: Submit flush/FUA requests
    BL->>HW: Cache flush command
    HW-->>BL: Flush complete
    BL-->>FS: Completion
    FS-->>App: fsync() returns
```

## Discard and TRIM

SSDs and thin-provisioned storage need the operating system to inform them when blocks are no longer in use. The **discard** mechanism sends `TRIM` (SATA) or `Deallocate` (NVMe) commands to the device:

```bash
# Enable continuous discard (filesystem-level)
mount -o discard /dev/nvme0n1p1 /data

# Or use periodic fstrim (preferred — less overhead)
fstrim /data
fstrim -v /data
# /data: 120.5 GiB (129387499520 bytes) trimmed

# Check discard support
lsblk -D
# NAME   DISC-ALN DISC-GRAN DISC-MAX DISC-ZERO
# sda           0      512B       2G         0
# nvme0n1       0        4K       2G         0

# Test discard at block layer
blkdiscard --secure /dev/sdX  # DANGEROUS: erases all data
```

### Discard vs Secure Erase

| Operation | Scope | Effect |
|-----------|-------|--------|
| `discard` (TRIM) | Specific block range | Marks blocks as unused |
| `blkdiscard` | Entire device or range | Erases data, may trigger secure erase |
| `ATA Secure Erase` | Entire drive | Firmware-level wipe |
| `NVMe Format` | Entire namespace | Cryptographic erase or user-data erase |

## Block I/O Tracing

### blktrace and blkparse

`blktrace` captures low-level block I/O events. It uses debugfs to hook into the block layer:

```bash
# Trace I/O on /dev/sda for 10 seconds
blktrace -d /dev/sda -o trace &
sleep 10
kill %1

# Parse the trace
blkparse -i trace -o trace.txt

# Output shows each I/O event:
# 8,0    1        1     0.000000000  2645  Q   R 2048 + 8 [cat]
# 8,0    1        2     0.000010000  2645  G   R 2048 + 8 [cat]
# 8,0    1        3     0.000020000  2645  I   R 2048 + 8 [cat]
# 8,0    1        4     0.000030000  2645  D   R 2048 + 8 [cat]
# 8,0    1        5     0.000100000     0  C   R 2048 + 8 [0]

# Event types:
# Q = queued, G = get request, I = inserted, D = dispatched
# C = complete, M = merged, A = remapped

# Generate timeline and statistics
btt -i trace.blktrace.0
```

### bpftrace for Block I/O

Modern tracing with BPF:

```bash
# Trace block I/O latency histogram
bpftrace -e '
tracepoint:block:block_rq_complete {
    @usecs = hist((nsecs - @start[args->dev, args->sector]) / 1000);
}
tracepoint:block:block_rq_issue {
    @start[args->dev, args->sector] = nsecs;
}
'

# Count I/O by type
bpftrace -e '
tracepoint:block:block_rq_issue {
    @[args->rwbs] = count();
}
'
```

## Device Mapper

The device-mapper is a kernel framework that provides a generic way to create virtual block devices. It sits between the filesystem and the actual block device, enabling:

- **LVM** (Logical Volume Manager)
- **dm-crypt** (LUKS encryption)
- **dm-raid** (software RAID)
- **multipath** (multiple paths to a SAN)
- **dm-cache** (SSD caching)

```bash
# View device-mapper targets
dmsetup targets
# linear           v1.1.0
# striped          v1.6.0
# mirror           v1.14.0
# crypt            v2.3.0
# thin-pool        v1.21.0
# cache            v2.3.0

# List device-mapper devices
dmsetup ls --tree
# vg0-root (253:0)
# ├─vg0-root_tdata (253:2)
# │ └─ (...) 
# └─vg0-root_tmeta (253:1)
#   └─ (...)
```

## Putting It All Together

When an application writes data, the I/O traverses these layers:

```mermaid
sequenceDiagram
    participant App
    participant VFS
    participant FS as Filesystem (ext4)
    participant PC as Page Cache
    participant BL as Block Layer
    participant IO as I/O Scheduler
    participant DRV as Device Driver
    participant HW as Hardware

    App->>VFS: write(fd, buf, len)
    VFS->>FS: vfs_write()
    FS->>PC: Copy to page cache
    FS->>BL: Submit bio
    BL->>IO: Insert into scheduler queue
    IO->>DRV: Dispatch request
    DRV->>HW: Send command to hardware
    HW-->>DRV: Completion interrupt
    DRV-->>BL: End request
    BL-->>FS: bio completion callback
    FS-->>VFS: Mark pages clean
    Note over App,HW: fsync() forces all pending writes to disk
```

## References

- [Linux Block I/O Documentation](https://www.kernel.org/doc/html/latest/block/)
- [NVMe Specification](https://nvmexpress.org/specifications/)
- [SCSI Documentation](https://www.kernel.org/doc/html/latest/scsi/)
- [Linux Storage Stack Diagram](https://www.thomas-krenn.com/en/wiki/Linux_Storage_Stack_Diagram)
- [Device Mapper Documentation](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- Bovet, D. P., & Cesati, M. *Understanding the Linux Kernel*, 3rd Edition. O'Reilly Media.
- Love, R. *Linux Kernel Development*, 3rd Edition. Addison-Wesley.
- <https://kernel.dk/sstor.pdf> - Jens Axboe's storage stack overview
- <https://lwn.net/Articles/738918/> - NVMe and the Linux block layer

## Related Topics

- [SCSI and NVMe Deep Dive](scsi-nvme.md)
- [Block I/O Layer](block-io.md)
- [Multipath I/O](multipath.md)
- [Storage Area Networks](san.md)
- [I/O Performance](../performance/io.md)
