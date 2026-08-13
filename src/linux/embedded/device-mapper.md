# Device Mapper

## Overview

The device mapper (DM) is a kernel framework that provides a generic way to create virtual block devices by mapping physical block devices. It is the foundation for LVM (Logical Volume Manager), dm-crypt (full disk encryption), dm-raid (software RAID), and many other storage technologies. The device mapper intercepts I/O requests to virtual devices and transforms them before passing them to underlying physical devices.

The device mapper operates through **targets** — kernel modules that implement specific mapping strategies. Each virtual device (called a **DM device** or **mapped device**) is configured with one or more targets that define how I/O is translated.

## Architecture

```
┌──────────────────────────────────────────┐
│            Filesystem / Application       │
│            (ext4, xfs, btrfs, etc.)      │
└──────────────────┬───────────────────────┘
                   │ /dev/dm-N or /dev/mapper/name
┌──────────────────┴───────────────────────┐
│           Device Mapper Core              │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐  │
│  │ linear  │ │ striped  │ │  crypt   │  │
│  │ target  │ │ target   │ │  target  │  │
│  └────┬────┘ └────┬─────┘ └────┬─────┘  │
│       │           │            │         │
├───────┴───────────┴────────────┴─────────┤
│         Physical Block Devices            │
│         /dev/sda, /dev/nvme0n1, etc.     │
└──────────────────────────────────────────┘
```

### Key Concepts

- **Mapped device**: Virtual block device visible to userspace (`/dev/dm-N`)
- **Table**: Mapping rules that define how I/O is translated
- **Target**: Kernel module implementing a specific mapping type
- **Target type**: The kind of mapping (linear, striped, crypt, etc.)

## dmsetup Utility

`dmsetup` is the low-level command-line tool for managing device mapper devices:

### Basic Operations

```bash
# List all DM devices
dmsetup ls
dmsetup ls --tree

# Show device status
dmsetup status
dmsetup status my_device

# Show device table
dmsetup table
dmsetup table my_device

# Show device info
dmsetup info my_device

# Create a device
dmsetup create my_device <<EOF
0 2097152 linear /dev/sda 0
EOF

# Remove a device
dmsetup remove my_device

# Remove all devices
dmsetup remove_all
```

### Table Format

A DM table consists of lines with three fields:

```
<start_sector> <num_sectors> <target_type> <target_args...>
```

- `start_sector`: Starting sector of the mapping (in 512-byte sectors)
- `num_sectors`: Number of sectors in this mapping
- `target_type`: Name of the target module
- `target_args`: Target-specific arguments

Multiple table lines create a device with different regions mapped differently.

## Linear Target

The **linear** target maps a range of sectors on a virtual device to a range on a physical device, optionally with an offset. This is the simplest and most common mapping.

### Basic Linear Mapping

```bash
# Map entire /dev/sdb as a DM device
echo "0 $(blockdev --getsz /dev/sdb) linear /dev/sdb 0" | dmsetup create my_linear

# Read and write to /dev/mapper/my_linear
dd if=/dev/zero of=/dev/mapper/my_linear bs=1M count=100
```

### Offset Mapping

```bash
# Map only a portion of /dev/sdb (starting at sector 1024, length 2048 sectors)
echo "0 2048 linear /dev/sdb 1024" | dmsetup create partial
```

### Spanning Multiple Devices

```bash
# Concatenate two devices
dmsetup create concat <<EOF
0 2097152 linear /dev/sda 0
2097152 2097152 linear /dev/sdb 0
EOF
```

### LVM and Linear

LVM logical volumes are built on linear mappings:

```bash
# LVM creates linear mappings internally
lvcreate -L 10G -n mylv myvg

# View the underlying DM table
dmsetup table myvg-mylv
# 0 20971520 linear 8:2 2048
```

## Striped Target

The **striped** target distributes I/O across multiple physical devices in a RAID-0-like pattern, improving throughput for sequential workloads.

### Configuration

```bash
# Create a striped device with 2 stripes
# Format: <stripes> <chunk_size> <dev1> <offset1> <dev2> <offset2>
dmsetup create striped <<EOF
0 4194304 striped 2 128 /dev/sda 0 /dev/sdb 0
EOF
# 2 stripes, 128 sectors (64KB) chunk size
```

### Stripe Layout

```
Stripe 0 (sda): [chunk 0] [chunk 2] [chunk 4] ...
Stripe 1 (sdb): [chunk 1] [chunk 3] [chunk 5] ...

Each chunk = chunk_size sectors (128 sectors = 64KB in the example)
```

### Performance Considerations

- **Chunk size**: Smaller chunks distribute I/O more evenly but increase seek overhead
- **Alignment**: Chunk boundaries should align with filesystem block size
- **Number of stripes**: More stripes = more parallelism, but also more points of failure
- **No redundancy**: Striped target provides no fault tolerance (unlike RAID-1/5/6)

### Performance Testing

```bash
# Create striped device
dmsetup create fast_stripe <<EOF
0 4194304 striped 4 256 /dev/nvme0n1p1 0 /dev/nvme2n1p1 0 /dev/nvme3n1p1 0 /dev/nvme4n1p1 0
EOF

# Benchmark
fio --name=seq_write --rw=write --bs=1M --size=4G \
    --filename=/dev/mapper/fast_stripe --direct=1 --numjobs=4
```

## Crypt Target (dm-crypt)

The **crypt** target provides transparent disk encryption. It is the backend for LUKS (Linux Unified Key Setup) and is used by most Linux full-disk encryption implementations.

### Basic dm-crypt

```bash
# Create an encrypted device
dmsetup create encrypted <<EOF
0 2097152 crypt aes-xts-plain64 <key> 0 /dev/sdb 0
EOF
# aes-xts-plain64: cipher and mode
# <key>: hex-encoded encryption key
# 0: IV offset
# /dev/sdb 0: underlying device and offset
```

### LUKS Integration

```bash
# Format with LUKS
cryptsetup luksFormat /dev/sdb

# Open LUKS volume (creates DM device)
cryptsetup luksOpen /dev/sdb my_encrypted

# View the DM table
dmsetup table my_encrypted
# 0 2097152 crypt aes-xts-plain64 <key_hash> 0 /dev/sdb 0 1 sector_size

# Mount
mount /dev/mapper/my_encrypted /mnt/secure

# Close
cryptsetup luksClose my_encrypted
```

### Cipher Modes

| Cipher | Mode | Key Size | Description |
|---|---|---|---|
| `aes` | `xts-plain64` | 256/512 | Recommended default |
| `aes` | `cbc-essiv:sha256` | 256 | Legacy, weaker |
| `serpent` | `xts-plain64` | 256/512 | Alternative cipher |
| `twofish` | `xts-plain64` | 256/512 | Alternative cipher |

### Multi-Key Support

```bash
# dm-crypt with multiple keys (LUKS2)
cryptsetup luksAddKey /dev/sdb

# Detached header
cryptsetup luksFormat --header /path/to/header.img /dev/sdb
cryptsetup luksOpen --header /path/to/header.img /dev/sdb my_encrypted
```

## Mirror Target

The **mirror** target provides RAID-1 mirroring, maintaining identical copies of data on two or more devices.

### Configuration

```bash
# Create a 2-way mirror
dmsetup create mirror <<EOF
0 2097152 mirror core 2 512 2 /dev/sda 0 /dev/sdb 0
EOF
# core: log type (core = in-memory, disk = persistent)
# 2: number of mirrors
# 512: region size (sectors)
# 2: number of devices
# /dev/sda 0 /dev/sdb 0: mirror devices with offsets
```

### Mirror with Persistent Log

```bash
# Use a separate device for the mirror log
dmsetup create mirror_persistent <<EOF
0 2097152 mirror disk 2 512 2 /dev/sda 0 /dev/sdb 0 /dev/sdc 0
EOF
# disk: persistent log type
# /dev/sdc: device for the mirror log
```

### Mirror States

```bash
# Check mirror status
dmsetup status my_mirror
# 0 2097152 mirror 2 25/4096 1 AA

# Status codes:
# AA = both mirrors in sync
# AD = second mirror dead
# DA = first mirror dead
```

### Resynchronization

When a mirror is created or a failed leg is restored, data must be resynchronized:

```bash
# Force resync
dmsetup create mirror --table "0 2097152 mirror core 2 512 2 /dev/sda 0 /dev/sdb 0"

# Monitor resync progress
dmsetup status my_mirror
# Shows progress as fraction of regions synced
```

## Snapshot Target

The **snapshot** target provides copy-on-write (COW) snapshots of block devices.

### Creating Snapshots

```bash
# Original device
echo "0 2097152 linear /dev/sda 0" | dmsetup create origin

# Create snapshot (COW device stores differences)
dmsetup create snapshot <<EOF
0 2097152 snapshot /dev/mapper/origin /dev/sdb P 8
EOF
# /dev/mapper/origin: origin device
# /dev/sdb: COW device
# P: persistent (survives reboot)
# 8: chunk size in sectors

# Or merge snapshot back to origin
dmsetup create snapshot_merge <<EOF
0 2097152 snapshot-merge /dev/mapper/origin /dev/sdb P 8
EOF
```

### Thin Provisioning

The **thin** target provides thin provisioning and efficient snapshots:

```bash
# Create a thin pool
dmsetup create thin_pool <<EOF
0 4194304 thin-pool /dev/sda /dev/sdb 128 0
EOF
# /dev/sda: data device
# /dev/sdb: metadata device
# 128: block size in sectors (64KB)
# 0: low water mark (no discard)

# Create thin volumes
dmsetup message thin_pool 0 "create_thin 0"
dmsetup create thin_vol1 <<EOF
0 2097152 thin /dev/mapper/thin_pool 0
EOF

# Create snapshot of thin volume
dmsetup message thin_pool 0 "create_snap 1 0"
dmsetup create thin_snap1 <<EOF
0 2097152 thin /dev/mapper/thin_pool 1
EOF
```

## Other Targets

### Error Target

Returns I/O errors for all requests. Useful for testing:

```bash
echo "0 2097152 error" | dmsetup create blackhole
```

### Zero Target

Returns zeros for reads, discards writes:

```bash
echo "0 2097152 zero" | dmsetup create null_device
```

### Delay Target

Adds artificial latency. Useful for testing slow storage:

```bash
# Delay reads by 10ms, writes by 5ms
echo "0 2097152 delay /dev/sda 0 10 /dev/sda 0 5" | dmsetup create slow_device
```

### Flakey Target

Intermittently fails I/O. Useful for testing error handling:

```bash
# Fail 50% of writes, corrupt reads 10% of the time
echo "0 2097152 flakey /dev/sda 0 1 2 5 drop_writes 1 corrupt_bio_byte 1 255 0" \
    | dmsetup create flakey
```

### Switch Target

Maps different regions to different devices:

```bash
dmsetup create switch_dev <<EOF
0 1024 linear /dev/sda 0
1024 1024 linear /dev/sdb 0
2048 1024 linear /dev/sda 1024
EOF
```

### Integrity Target

Provides data integrity checking using dm-integrity:

```bash
# Format integrity
integritysetup format /dev/sdb

# Open
integritysetup open /dev/sdb my_integrity

# With dm-crypt (authenticated encryption)
cryptsetup luksFormat --type luks2 --integrity hmac-sha256 /dev/mapper/my_integrity
```

## LVM2 and Device Mapper

LVM2 is the primary userspace tool built on the device mapper:

### LVM Architecture

```
Physical Volumes (PV)  →  Volume Group (VG)  →  Logical Volumes (LV)
/dev/sda, /dev/sdb          my_vg               my_lv → /dev/mapper/my_vg-my_lv
```

### LVM Operations

```bash
# Create physical volume
pvcreate /dev/sda /dev/sdb

# Create volume group
vgcreate my_vg /dev/sda /dev/sdb

# Create logical volume
lvcreate -L 100G -n my_lv my_vg

# View DM table behind LV
dmsetup table my_vg-my_lv

# Resize
lvextend -L +50G /dev/mapper/my_vg-my_lv
resize2fs /dev/mapper/my_vg-my_lv
```

### LVM Thin Provisioning

```bash
# Create thin pool
lvcreate -L 200G --thinpool thin_pool my_vg

# Create thin volume
lvcreate -V 100G --thin -n thin_lv my_vg/thin_pool

# Create snapshot
lvcreate -s --name snap my_vg/thin_lv
```

## I/O Stack with Device Mapper

A typical I/O path through the device mapper:

```
1. Application writes to /dev/mapper/my_encrypted
2. VFS passes bio to DM mapped device
3. DM core looks up table for the sector range
4. Target (e.g., crypt) processes the bio:
   a. Encrypts the data
   b. Remaps to underlying device sector
   c. Submits modified bio to underlying device
5. Underlying device driver handles I/O
6. Completion propagates back through DM
7. Target completion handler runs (e.g., decrypt data for reads)
8. Original bio completion called
```

### Per-CPU Data and Performance

The device mapper uses per-CPU data structures for performance:

```c
/* include/linux/device-mapper.h */
struct mapped_device {
    /* ... */
    struct dm_stats *stats;
    struct percpu_counter pending_io;
    /* ... */
};
```

## Monitoring and Statistics

```bash
# Device mapper status
dmsetup status

# Detailed statistics (if dm-stats enabled)
dmsetup create my_dev --table "0 2097152 linear /dev/sda 0"
dmsetup stats create my_dev
dmsetup stats print my_dev

# I/O counters
cat /sys/block/dm-0/stat
# reads reads_merged sectors_read time_reading
# writes writes_merged sectors_writen time_writing
# ios_in_progress time_io weighted_time_io

# Device-mapper specific info
ls /sys/block/dm-0/dm/
# name uuid suspended
```

## Debugging Device Mapper

### DM Messages

```bash
# Send messages to DM targets
dmsetup message my_device 0 "some message"
# Target-specific: e.g., thin pool resize, cache settings

# Suspend/resume for maintenance
dmsetup suspend my_device
# Perform operations
dmsetup resume my_device
```

### Common Issues

| Issue | Cause | Solution |
|---|---|---|
| Device not found | Not created or removed | `dmsetup ls` to check |
| I/O errors | Underlying device failure | Check `dmesg` for disk errors |
| Slow performance | Misaligned partitions | Ensure sector alignment |
| LVM activation fails | Missing PVs | `vgreduce --removemissing` |
| dm-crypt slow | No AES-NI | Check `/proc/cpuinfo` for aes flag |
| Snapshot full | COW device too small | Extend COW volume |

### Tracing

```bash
# Enable DM tracing
echo 1 > /sys/kernel/debug/tracing/events/block/block_bio_queue/enable

# Or use blktrace
blktrace -d /dev/mapper/my_device -o trace
blkparse -i trace -o parsed.txt
```

## Further Reading

- **Kernel documentation**: `Documentation/admin-guide/device-mapper/`
- **DM design doc**: `Documentation/driver-api/device-mapper/`
- **dm-crypt**: `Documentation/admin-guide/device-mapper/crypt.rst`
- **dm-thin**: `Documentation/admin-guide/device-mapper/thin-provisioning.rst`
- **LVM documentation**: https://sourceware.org/lvm2/
- **Source**: `drivers/md/dm.c` — device mapper core
- **Source**: `drivers/md/dm-linear.c` — linear target
- **Source**: `drivers/md/dm-crypt.c` — crypt target
- **Source**: `drivers/md/dm-striped.c` — striped target
- **Related**: [LVM](../admin/lvm.md) — logical volume management
- **Related**: [LUKS/dm-crypt](../kernel/drivers/dm-crypt.md) — disk encryption
- **Related**: Block Layer — block I/O subsystem
- **Related**: RAID — software RAID
