# LVM — Logical Volume Manager

LVM (Logical Volume Manager) provides a flexible layer of abstraction between physical storage devices and the filesystem. It allows dynamic resizing, snapshots, striping, mirroring, and thin provisioning — capabilities impossible with traditional partitioning.

## LVM Architecture

```
┌─────────────────────────────────────────────────────────┐
│  LVM Architecture                                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Filesystem:  ext4    xfs    btrfs    swap              │
│  ───────────────────────────────────────────────────    │
│  LV:          /dev/vg0/lv_root                           │
│               /dev/vg0/lv_home                           │
│               /dev/vg0/lv_swap                           │
│  ───────────────────────────────────────────────────    │
│  VG:          vg0      (Volume Group)                    │
│  ───────────────────────────────────────────────────    │
│  PV:          /dev/sda2  /dev/sdb1  /dev/sdc1           │
│               (Physical Volumes)                         │
│  ───────────────────────────────────────────────────    │
│  Disks:       /dev/sda  /dev/sdb  /dev/sdc              │
│                                                         │
│  Advantages:                                            │
│  - Resize volumes without data loss                     │
│  - Span multiple physical disks                         │
│  - Snapshots for backups                                │
│  - Thin provisioning                                    │
│  - RAID and striping                                    │
│  - Move data between physical disks online              │
└─────────────────────────────────────────────────────────┘
```

### LVM Terminology

| Term | Description |
|------|-------------|
| **PV** (Physical Volume) | Physical disk or partition used by LVM |
| **VG** (Volume Group) | Pool of storage from one or more PVs |
| **LV** (Logical Volume) | Virtual partition carved from a VG |
| **PE** (Physical Extent) | Smallest allocatable unit in a VG |
| **LE** (Logical Extent) | Same size as PE, mapped 1:1 |

## Creating Physical Volumes

```bash
# Create PV on partition
sudo pvcreate /dev/sdb1

# Create PV on whole disk (not recommended, but works)
sudo pvcreate /dev/sdc

# Create multiple PVs at once
sudo pvcreate /dev/sdb1 /dev/sdc1 /dev/sdd1

# View PVs
sudo pvs
# PV         VG   Fmt  Attr PSize   PFree
# /dev/sdb1       lvm2 ---  100.00g 100.00g
# /dev/sdc1       lvm2 ---  200.00g 200.00g

sudo pvdisplay
# --- Physical volume ---
# PV Name               /dev/sdb1
# VG Name
# PV Size               100.00 GiB
# Allocatable           NO
# PE Size               0
# Total PE              0
# Free PE               0
# PV UUID               xxxx-xxxx-xxxx

# PV details
sudo pvdisplay /dev/sdb1

# Remove PV (must have no allocated extents)
sudo pvremove /dev/sdb1

# Resize PV (after expanding partition)
sudo pvresize /dev/sdb1

# Move extents from one PV to another (online!)
sudo pvmove /dev/sdb1 /dev/sdc1

# Move specific extents
sudo pvmove /dev/sdb1:0-99 /dev/sdc1

# Check PV for errors
sudo pvck /dev/sdb1
```

### Preparing Disks for LVM

```bash
# Create partition table (GPT recommended)
sudo parted /dev/sdb mklabel gpt

# Create partition for LVM
sudo parted /dev/sdb mkpart primary 0% 100%

# Or with fdisk
sudo fdisk /dev/sdb
# n → new partition
# p → primary
# 1 → partition number
# (default) → first sector
# (default) → last sector
# t → change type
# 8e → Linux LVM
# w → write

# Or with sgdisk (non-interactive)
sudo sgdisk -n 1:0:0 -t 1:8e00 /dev/sdb

# Refresh partition table
sudo partprobe /dev/sdb
```

## Creating Volume Groups

```bash
# Create VG
sudo vgcreate vg_data /dev/sdb1

# Create VG with multiple PVs
sudo vgcreate vg_data /dev/sdb1 /dev/sdc1 /dev/sdd1

# Create VG with custom PE size (default: 4MB)
sudo vgcreate -s 8M vg_data /dev/sdb1

# View VGs
sudo vgs
# VG      #PV #LV #SN Attr   VSize   VFree
# vg_data   2   0   0 wz--n- 299.99g 299.99g

sudo vgdisplay
# --- Volume group ---
# VG Name               vg_data
# System ID
# Format                lvm2
# Metadata Areas        2
# Metadata Sequence No  1
# VG Access             read/write
# VG Status             resizable
# MAX LV                0
# Cur LV                0
# Open LV               0
# Max PV                0
# Cur PV                2
# Act PV                2
# VG Size               299.99 GiB
# PE Size               4.00 MiB
# Total PE              76798
# Alloc PE / Size       0 / 0
# Free  PE / Size       76798 / 299.99 GiB
# VG UUID               xxxx-xxxx-xxxx

# Add PV to existing VG
sudo vgextend vg_data /dev/sdd1

# Remove PV from VG (move data first!)
sudo pvmove /dev/sdb1
sudo vgreduce vg_data /dev/sdb1

# Remove VG
sudo vgremove vg_data

# Rename VG
sudo vgrename vg_data vg_storage

# Check VG for consistency
sudo vgck vg_data

# Activate VG
sudo vgchange -ay vg_data

# Deactivate VG
sudo vgchange -an vg_data
```

## Creating Logical Volumes

```bash
# Create LV with size
sudo lvcreate -L 50G -n lv_root vg_data

# Create LV using percentage of VG
sudo lvcreate -l 100%FREE -n lv_data vg_data
sudo lvcreate -l 50%VG -n lv_half vg_data
sudo lvcreate -l 25%VG -n lv_quarter vg_data

# Create LV with specific number of extents
sudo lvcreate -l 1000 -n lv_test vg_data

# View LVs
sudo lvs
# LV      VG      Attr       LSize   Pool Origin Data%
# lv_root vg_data -wi-a-----  50.00g
# lv_data vg_data -wi-a----- 249.99g

sudo lvdisplay
# --- Logical volume ---
# LV Path                /dev/vg_data/lv_root
# LV Name                lv_root
# VG Name                vg_data
# LV UUID                xxxx-xxxx-xxxx
# LV Write Access        read/write
# LV Creation host, time server, 2024-01-01 00:00:00 +0000
# LV Status              available
# # open                 0
# LV Size                50.00 GiB
# Current LE             12800
# Segments               1
# Allocation             inherit
# Read ahead sectors     auto
# - currently set to     256
# Block device           253:0

# Activate LV
sudo lvchange -ay vg_data/lv_root

# Deactivate LV
sudo lvchange -an vg_data/lv_root

# Remove LV (destructive!)
sudo lvremove vg_data/lv_root

# Rename LV
sudo lvrename vg_data lv_root lv_system
```

### Creating Filesystems on LVs

```bash
# Create filesystem
sudo mkfs.ext4 /dev/vg_data/lv_root
sudo mkfs.xfs /dev/vg_data/lv_data

# Create swap
sudo mkswap /dev/vg_data/lv_swap
sudo swapon /dev/vg_data/lv_swap

# Mount
sudo mount /dev/vg_data/lv_root /mnt/root

# Device paths
ls -la /dev/vg_data/lv_root
# lrwxrwxrwx 1 root root 7 Jan 1 00:00 /dev/vg_data/lv_root -> ../dm-0

# Also available as:
ls -la /dev/mapper/vg_data-lv_root
# lrwxrwxrwx 1 root root 7 Jan 1 00:00 /dev/mapper/vg_data-lv_root -> ../dm-0
```

## Resizing Logical Volumes

### Extending (Growing)

```bash
# Extend LV by size
sudo lvextend -L +20G /dev/vg_data/lv_root

# Extend LV to specific size
sudo lvextend -L 100G /dev/vg_data/lv_root

# Extend LV and resize filesystem in one step
sudo lvextend -L +20G --resizefs /dev/vg_data/lv_root
# Works for ext4, xfs, btrfs

# For ext4 only:
sudo lvextend -L +20G /dev/vg_data/lv_root
sudo resize2fs /dev/vg_data/lv_root

# For xfs (online, always):
sudo lvextend -L +20G /dev/vg_data/lv_root
sudo xfs_growfs /dev/vg_data/lv_root

# Extend using percentage
sudo lvextend -l +100%FREE /dev/vg_data/lv_root --resizefs

# Check before and after
sudo lvs /dev/vg_data/lv_root
```

### Shrinking (Reducing)

```bash
# WARNING: Shrinking can cause data loss!
# Always backup first!

# For ext4 (must unmount first):
sudo umount /mnt/data
sudo e2fsck -f /dev/vg_data/lv_data
sudo resize2fs /dev/vg_data/lv_data 50G    # Resize filesystem first
sudo lvreduce -L 50G /dev/vg_data/lv_data  # Then reduce LV
sudo mount /dev/vg_data/lv_data /mnt/data

# For xfs: CANNOT SHRINK!
# XFS filesystems can only grow, never shrink.
# To "shrink" an XFS volume, you must:
# 1. Create a new, smaller LV
# 2. Create XFS filesystem on it
# 3. Copy data
# 4. Remove old LV

# Safe workflow:
sudo umount /mnt/data
sudo e2fsck -f /dev/vg_data/lv_data
sudo lvreduce --resizefs -L 50G /dev/vg_data/lv_data
# --resizefs handles the order (resize FS first, then LV)
sudo mount /dev/vg_data/lv_data /mnt/data
```

## Snapshots

LVM snapshots create point-in-time copies of logical volumes.

### Creating Snapshots

```bash
# Create snapshot (COW — Copy-On-Write)
sudo lvcreate -L 10G -s -n lv_root_snap /dev/vg_data/lv_root

# Snapshot with specific size (percentage of origin)
sudo lvcreate -l 20%ORIGIN -s -n lv_root_snap /dev/vg_data/lv_root

# View snapshots
sudo lvs
# LV            VG      Attr       LSize   Pool Origin  Data%
# lv_root       vg_data owi-aos--- 50.00g
# lv_root_snap  vg_data swi-aos--- 10.00g      lv_root  0.00

# Mount snapshot (read-only by default)
sudo mount -o ro /dev/vg_data/lv_root_snap /mnt/snapshot

# Use snapshot for backup
sudo mount -o ro /dev/vg_data/lv_root_snap /mnt/snapshot
sudo tar -czf /backup/root_backup.tar.gz -C /mnt/snapshot .
sudo umount /mnt/snapshot

# Remove snapshot
sudo lvremove vg_data/lv_root_snap
```

### Snapshot Behavior

```
┌─────────────────────────────────────────────────────┐
│  LVM Snapshot Mechanism (COW)                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Origin LV:     [A][B][C][D][E]                     │
│  Snapshot LV:   [ ] [ ] [ ] [ ] [ ]  (empty)       │
│                                                     │
│  When block C is modified in origin:                 │
│  1. Original C is copied to snapshot                │
│  2. New C is written to origin                      │
│                                                     │
│  Origin LV:     [A][B][C'][D][E]                    │
│  Snapshot LV:   [ ] [ ] [C] [ ] [ ]  (holds old C) │
│                                                     │
│  Snapshot size determines how many changed blocks   │
│  can be stored before snapshot becomes invalid.     │
│                                                     │
│  If snapshot fills up → snapshot is dropped!        │
│  Monitor with: lvs (Data% column)                   │
└─────────────────────────────────────────────────────┘
```

### Writable Snapshots

```bash
# Create writable snapshot
sudo lvcreate -L 10G -s -n lv_snap_rw /dev/vg_data/lv_root

# Mount read-write
sudo mount /dev/vg_data/lv_snap_rw /mnt/snapshot_rw

# Modify snapshot independently
echo "test" > /mnt/snapshot_rw/test.txt

# Merge snapshot back to origin (revert to snapshot state)
sudo umount /mnt/snapshot_rw
sudo lvconvert --merge vg_data/lv_snap_rw
# Origin reverts to snapshot state after deactivation/activation

# After merge, deactivate and reactivate origin
sudo lvchange -an vg_data/lv_root
sudo lvchange -ay vg_data/lv_root
```

### Snapshot-Based Backup Workflow

```bash
#!/bin/bash
# Consistent backup using LVM snapshots

set -euo pipefail

VG="vg_data"
LV="lv_data"
SNAP_NAME="${LV}_snap"
SNAP_SIZE="10G"
BACKUP_DIR="/backup"
MOUNT_POINT="/mnt/snapshot"

# Create snapshot
sudo lvcreate -L "$SNAP_SIZE" -s -n "$SNAP_NAME" "/dev/$VG/$LV"

# Mount snapshot
sudo mkdir -p "$MOUNT_POINT"
sudo mount -o ro "/dev/$VG/$SNAP_NAME" "$MOUNT_POINT"

# Backup
sudo tar -czf "$BACKUP_DIR/${LV}_$(date +%Y%m%d).tar.gz" -C "$MOUNT_POINT" .

# Cleanup
sudo umount "$MOUNT_POINT"
sudo lvremove -f "/dev/$VG/$SNAP_NAME"

echo "Backup complete: $BACKUP_DIR/${LV}_$(date +%Y%m%d).tar.gz"
```

## Thin Provisioning

Thin provisioning allocates storage on demand, allowing over-allocation.

### Thin Pool and Thin LVs

```bash
# Create thin pool
sudo lvcreate -L 100G --thinpool thin_pool vg_data

# Create thin LV (can be larger than pool!)
sudo lvcreate -V 200G --thin -n thin_lv1 vg_data/thin_pool
sudo lvcreate -V 300G --thin -n thin_lv2 vg_data/thin_pool
# Total allocated: 500G, but pool is only 100G
# This works as long as actual usage stays under 100G

# View thin volumes
sudo lvs
# LV        VG      Attr       LSize   Pool      Origin Data%
# thin_pool vg_data twi-aotz-- 100.00g                    10.00
# thin_lv1  vg_data Vwi-a-tz-- 200.00g thin_pool          5.00
# thin_lv2  vg_data Vwi-a-tz-- 300.00g thin_pool          3.33

# Check thin pool usage
sudo lvs -o +data_percent,metadata_percent
# Shows actual usage percentage

# Extend thin pool
sudo lvextend -L +50G vg_data/thin_pool

# Auto-extend thin pool (lvm.conf)
# thin_pool_autoextend_threshold = 80
# thin_pool_autoextend_percent = 20
```

### Thin Provisioning Snapshots

```bash
# Thin snapshots are space-efficient and instant
sudo lvcreate -s -n thin_snap1 vg_data/thin_lv1
# No size needed — thin snapshots share pool space

# View thin snapshots
sudo lvs -o +origin
```

## Striping

Striping distributes data across multiple PVs for improved performance.

```bash
# Create striped LV (RAID 0)
sudo lvcreate -L 100G -n lv_striped \
    --type striped \
    --stripes 3 \
    --stripesize 64K \
    vg_data

# --stripes 3: data distributed across 3 PVs
# --stripesize 64K: chunk size (default: 64K)

# View stripe info
sudo lvs -o +stripes,stripe_size

# How striping works:
# Data is split into chunks and written across PVs:
# PV1: [chunk1] [chunk4] [chunk7] ...
# PV2: [chunk2] [chunk5] [chunk8] ...
# PV3: [chunk3] [chunk6] [chunk9] ...
# → Parallel I/O for sequential reads/writes
```

## Mirroring

```bash
# Create mirrored LV (RAID 1)
sudo lvcreate -L 50G -n lv_mirror \
    --type raid1 \
    --mirrors 1 \
    vg_data

# Create with specific PVs
sudo lvcreate -L 50G -n lv_mirror \
    --type raid1 \
    --mirrors 1 \
    vg_data /dev/sdb1 /dev/sdc1

# View mirror status
sudo lvs -a -o +devices
sudo lvs -o +mirror_log

# Add mirror log (if using old-style mirror, not raid1)
# Not needed with --type raid1 (uses MD RAID internally)

# Convert linear to mirror
sudo lvconvert --type raid1 --mirrors 1 vg_data/lv_linear

# Remove mirror (convert to linear)
sudo lvconvert --type linear vg_data/lv_mirror

# Repair mirror (replace failed PV)
sudo lvconvert --repair vg_data/lv_mirror
```

## RAID Levels

```bash
# RAID 0 (striping, no redundancy)
sudo lvcreate -L 100G -n lv_raid0 --type raid0 --stripes 3 vg_data

# RAID 1 (mirroring)
sudo lvcreate -L 50G -n lv_raid1 --type raid1 --mirrors 1 vg_data

# RAID 5 (striping with parity)
sudo lvcreate -L 100G -n lv_raid5 --type raid5 --stripes 3 vg_data

# RAID 6 (striping with double parity)
sudo lvcreate -L 100G -n lv_raid6 --type raid6 --stripes 4 vg_data

# RAID 10 (mirror of stripes)
sudo lvcreate -L 100G -n lv_raid10 --type raid10 --stripes 2 --mirrors 1 vg_data

# View RAID status
sudo lvs -o +raid_sync_percent
sudo lvs -a -o +devices
```

## lvmcache

lvmcache uses fast SSDs to cache slow HDDs.

```bash
# Create cache pool from SSD
sudo lvcreate -L 10G -n cache_pool vg_data /dev/ssd_pv
sudo lvcreate -L 1G -n cache_meta vg_data /dev/ssd_pv

# Convert to cache pool
sudo lvconvert --type cache-pool \
    --poolmetadata vg_data/cache_meta \
    vg_data/cache_pool

# Attach cache to slow LV
sudo lvconvert --type cache \
    --cachepool vg_data/cache_pool \
    vg_data/lv_slow

# View cache status
sudo lvs -o +cache_read_hits,cache_read_misses

# Cache modes:
# writethrough: writes go to both cache and origin (safe, slower)
# writeback: writes go to cache only (faster, risk of data loss on power failure)
sudo lvchange --cachesettings "cache_mode=writeback" vg_data/lv_slow

# Remove cache
sudo lvconvert --uncache vg_data/lv_slow
```

### dm-cache Architecture

```
┌─────────────────────────────────────────────────────┐
│  lvmcache (dm-cache) Architecture                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐                                    │
│  │  Logical     │  ← Application sees one device    │
│  │  Volume      │                                    │
│  └──────┬──────┘                                    │
│         │                                           │
│    ┌────┴────┐                                       │
│    │  Cache   │  ← Frequently accessed blocks       │
│    │  (SSD)   │     served from fast storage         │
│    └────┬────┘                                       │
│         │                                           │
│    ┌────┴────┐                                       │
│    │  Origin  │  ← All blocks live here              │
│    │  (HDD)   │     (slow but large)                │
│    └─────────┘                                       │
│                                                     │
│  Cache modes:                                        │
│  writethrough: read cache only                       │
│  writeback: read + write cache (faster, less safe)  │
└─────────────────────────────────────────────────────┘
```

## LVM Configuration

### `/etc/lvm/lvm.conf`

```bash
# Global settings
global {
    # Metadata backup
    backup = 1
    backup_dir = "/etc/lvm/backup"
    archive = 1
    archive_dir = "/etc/lvm/archive"

    # Device scanning
    scan = [ "/dev" ]
    obtain_device_list_from_udev = 1

    # Thin provisioning auto-extend
    thin_pool_autoextend_threshold = 80
    thin_pool_autoextend_percent = 20

    # Snapshot auto-extend
    snapshot_autoextend_threshold = 80
    snapshot_autoextend_percent = 20
}

# Device filter (important for multipath or USB devices)
devices {
    filter = [ "a|^/dev/sd[a-z]|", "a|^/dev/nvme[0-9]|", "r|.*|" ]
    # a = accept, r = reject
    # Processed left to right, first match wins
}
```

### LVM Metadata Backup and Restore

```bash
# Backup VG metadata
sudo vgcfgbackup vg_data
# Saved to /etc/lvm/backup/vg_data

# Restore VG metadata
sudo vgcfgrestore vg_data

# List metadata backups
sudo vgcfgbackup --list vg_data

# Archive management
sudo vgcfgrestore --list vg_data
# Shows archived versions

# Restore specific version
sudo vgcfgrestore -f /etc/lvm/archive/vg_data_00001.vg vg_data
```

## Practical LVM Scenarios

### Add Disk to Full System

```bash
# 1. Add new disk and create partition
sudo parted /dev/sdd mklabel gpt
sudo parted /dev/sdd mkpart primary 0% 100%

# 2. Create PV
sudo pvcreate /dev/sdd1

# 3. Extend VG
sudo vgextend vg_data /dev/sdd1

# 4. Extend LV and filesystem
sudo lvextend -L +200G --resizefs /dev/vg_data/lv_root
```

### Move Data Off Disk

```bash
# Move all extents from /dev/sdb1 to other PVs
sudo pvmove /dev/sdb1

# Remove PV from VG
sudo vgreduce vg_data /dev/sdb1

# Remove PV label
sudo pvremove /dev/sdb1
```

### Replace Failed Disk

```bash
# 1. If using RAID/mirror, check status
sudo lvs -a -o +devices

# 2. Move data off failed disk
sudo pvmove /dev/sdb1    # May fail if disk is dead

# 3. If disk is dead and using RAID:
sudo vgreduce --removemissing vg_data

# 4. Add replacement disk
sudo pvcreate /dev/sde1
sudo vgextend vg_data /dev/sde1

# 5. Recreate any lost LVs from backup or RAID reconstruction
```

### View LVM Summary

```bash
# Full system overview
sudo pvs && echo "---" && sudo vgs && echo "---" && sudo lvs

# Detailed hierarchy
sudo lvmdiskscan
sudo dmsetup ls
sudo dmsetup status

# LVM event monitoring
sudo dmeventd -l
sudo lvs -o +devices,segtype
```

## Cross-References

- [systemd](systemd.md) — Mount units and automounts for LVM volumes
- [File Permissions](permissions.md) — Filesystem permissions on LVM volumes
- [Cron and Systemd Timers](cron.md) — Scheduled snapshot and backup tasks
- [Users and Groups](users-groups.md) — Volume ownership and access

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [LVM2 Man Pages](https://man7.org/linux/man-pages/man8/lvm.8.html) — Official LVM documentation
- [Red Hat LVM Guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_logical_volumes/index) — Comprehensive RHEL LVM guide
- [Arch Wiki: LVM](https://wiki.archlinux.org/title/LVM) — Arch Linux LVM documentation
- [LVM Thin Provisioning](https://www.sourceware.org/lvm2/wiki/Thinly_Provisioned_Volumes) — Thin provisioning details
- [Linux Storage Stack Diagram](https://www.thomas-krenn.com/en/wiki/Linux_Storage_Stack_Diagram) — Visual overview of Linux storage layers
