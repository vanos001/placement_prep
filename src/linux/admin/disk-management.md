# Disk Management

## Introduction

Disk management is one of the most critical responsibilities of a Linux system administrator. It encompasses everything from partitioning raw disks and creating filesystems to mounting storage, monitoring disk health, and troubleshooting I/O issues. Mismanagement of storage can lead to data loss, system downtime, and cascading failures across dependent services.

This page covers the essential disk management tools and workflows: discovering block devices, partitioning disks, creating filesystems, mounting storage, and verifying filesystem integrity.

## Discovering Block Devices

### `lsblk` — List Block Devices

`lsblk` is the primary tool for viewing the block device tree, showing disks, partitions, and their relationships:

```bash
# Basic listing
lsblk
# NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
# sda      8:0    0   500G  0 disk
# ├─sda1   8:1    0   512M  0 part /boot/efi
# ├─sda2   8:2    0     1G  0 part /boot
# └─sda3   8:3    0   498G  0 part
#   ├─vg0-root  253:0    0    50G  0 lvm  /
#   ├─vg0-home  253:1    0   200G  0 lvm  /home
#   └─vg0-swap  253:2    0     8G  0 lvm  [SWAP]
# sdb      8:16   0     2T  0 disk
# └─sdb1   8:17   0     2T  0 part /data
# nvme0n1  259:0  0   1TB  0 disk
# ├─nvme0n1p1 259:1 0   512M  0 part
# └─nvme0n1p2 259:2 0   999G  0 part

# Detailed output with filesystem info
lsblk -f
# NAME   FSTYPE FSVER LABEL UUID                                 FSAVAIL FSUSE% MOUNTPOINTS
# sda
# ├─sda1 vfat   FAT32      ABCD-1234                             450M    12% /boot/efi
# ├─sda2 ext4   1.0         12345678-abcd-efgh-ijkl-123456789abc 700M    25% /boot
# └─sda3 LVM2_member        87654321-dcba-hgfe-lkjih-987654321abc

# Show device permissions and owners
lsblk -m
# NAME         SIZE OWNER GROUP MODE
# sda         500G root  disk  brw-rw----
# ├─sda1      512M root  disk  brw-rw----

# JSON output (useful for scripting)
lsblk -J

# Show SCSI devices
lsblk -S
# NAME HCTL       TYPE VENDOR   MODEL             REV TRAN
# sda  0:0:0:0    disk ATA      Samsung SSD 870   0A  sata
```

### `blkid` — Block Device Identification

`blkid` shows filesystem types, labels, and UUIDs:

```bash
# List all block devices with UUIDs
blkid
# /dev/sda1: LABEL="EFI" UUID="ABCD-1234" TYPE="vfat" PARTUUID="1234abcd-..."
# /dev/sda2: LABEL="boot" UUID="12345678-abcd-..." TYPE="ext4" PARTUUID="..."
# /dev/sda3: UUID="87654321-dcba-..." TYPE="LVM2_member" PARTUUID="..."

# Specific device
blkid /dev/sda1
# /dev/sda1: LABEL="EFI" UUID="ABCD-1234" TYPE="vfat" PARTUUID="1234abcd-01"

# Output for /etc/fstab
blkid -o list
# Device           LABEL   UUID                                 TYPE  MOUNT
# /dev/sda1        EFI     ABCD-1234                            vfat  /boot/efi
# /dev/sda2        boot    12345678-abcd-...                    ext4  /boot

# Export format
blkid -o export /dev/sda1
# DEVNAME=/dev/sda1
# LABEL=EFI
# UUID=ABCD-1234
# TYPE=vfat
# PARTUUID=1234abcd-01
```

## Partitioning Disks

### `fdisk` — MBR and GPT Partitioning

`fdisk` is the classic partitioning tool. Modern `fdisk` supports both MBR and GPT:

```bash
# Interactive mode
fdisk /dev/sdb

# Common fdisk commands:
# m    - help
# p    - print partition table
# n    - new partition
# d    - delete partition
# t    - change partition type
# w    - write changes and exit
# q    - quit without saving

# Create a new GPT partition table
# (in fdisk interactive mode)
# g    - create new GPT disk label
# n    - new partition (accept defaults for full disk)
# t    - change type (83 = Linux, 8e = LVM, fd = RAID)
# w    - write

# Non-interactive: create GPT with one partition
echo -e "g\nn\n\n\n\nw" | fdisk /dev/sdb

# List partitions without entering interactive mode
fdisk -l /dev/sdb
# Disk /dev/sdb: 2 TiB, 2199023255552 bytes, 4294967296 sectors
# Disk model: ST2000DM008-2FR1
# Units: sectors of 1 * 512 = 512 bytes
# Sector size (logical/physical): 512 bytes / 4096 bytes
# I/O size (minimum/optimal): 4096 bytes / 4096 bytes
# Disklabel type: gpt
# Disk identifier: 12345678-ABCD-...
#
# Device     Start        End    Sectors  Size Type
# /dev/sdb1  2048 4294967262 4294965215    2T Linux filesystem
```

### `parted` — Advanced Partitioning

`parted` is more powerful than `fdisk`, supporting scripting and advanced features:

```bash
# Interactive mode
parted /dev/sdb

# Non-interactive: create GPT with partitions
parted -s /dev/sdb mklabel gpt
parted -s /dev/sdb mkpart primary ext4 1MiB 100GiB
parted -s /dev/sdb mkpart primary xfs 100GiB 100%

# Show partition info
parted /dev/sdb print
# Model: ATA ST2000DM008-2FR1 (scsi)
# Disk /dev/sdb: 2199GB
# Sector size (logical/physical): 512B/4096B
# Partition Table: gpt
# Disk Flags:
#
# Number  Start   End     Size    File system  Name     Flags
#  1      1049kB  100GB   100GB   ext4         primary
#  2      100GB   2199GB  2099GB  xfs          primary

# Resize a partition
parted /dev/sdb resizepart 1 200GiB

# Align partitions for SSD performance
parted -s /dev/nvme0n1 mklabel gpt
parted -s /dev/nvme0n1 --align optimal mkpart primary 1MiB 100%
```

### GPT vs MBR

| Feature | MBR | GPT |
|---------|-----|-----|
| Max disk size | 2 TiB | 8 ZiB |
| Max partitions | 4 primary (or 3 + 1 extended) | 128 (default) |
| Boot | BIOS only | UEFI (with BIOS compat) |
| Redundancy | None | Backup header at disk end |
| Partition names | No | Yes |
| GUID identifiers | No | Yes |

## Creating Filesystems

### `mkfs` — Make Filesystem

```bash
# ext4 (most common for Linux)
mkfs.ext4 /dev/sdb1
# mke2fs 1.47.0 (5-Feb-2023)
# Creating filesystem with 244190592 4k blocks and 61054976 inodes
# Filesystem UUID: 12345678-abcd-...
# Superblock backups stored on blocks:
#     32768, 98304, 163840, 229376, 294912, 819200, 884736, ...
#
# Allocating group tables: done
# Writing inode tables: done
# Creating journal (262144 blocks): done
# Writing superblocks and filesystem accounting information: done

# With label
mkfs.ext4 -L "data" /dev/sdb1

# With specific block size and inode ratio
mkfs.ext4 -b 4096 -i 8192 /dev/sdb1

# XFS (better for large files, databases)
mkfs.xfs /dev/sdb2
# meta-data=/dev/sdb2              isize=512    agcount=4, agsize=128000000 blks
#          =                       sectsz=4096  attr=2, projid32bit=1
#          =                       crc=1        finobt=1, sparse=1, rmapbt=0
#          =                       reflink=1    bigtime=1 inobtcount=1
# data     =                       bsize=4096   blocks=512000000, imaxpct=5
#          =                       sunit=0      swidth=0 blks
# naming   =version 2              bsize=4096   ascii-ci=0, ftype=1
# log      =internal log           bsize=4096   blocks=2560000, version=2
#          =                       sectsz=4096  sunit=1 blks, lazy-count=1
# realtime =none                   extsz=4096   blocks=0, rtextents=0

# Btrfs (copy-on-write, snapshots, compression)
mkfs.btrfs -L "pool" /dev/sdb1

# With RAID1 profile for metadata
mkfs.btrfs -d raid1 -m raid1 -L "mirror" /dev/sdb1 /dev/sdc1

# Swap
mkswap /dev/sdb3
# Setting up swapspace version 1, size = 8 GiB
# UUID: abcd1234-...
```

### Filesystem Comparison

| Feature | ext4 | XFS | Btrfs | ZFS |
|---------|------|-----|-------|-----|
| Max file size | 16 TiB | 8 EiB | 16 EiB | 16 EiB |
| Max volume | 1 EiB | 8 EiB | 16 EiB | 256 ZiB |
| Snapshots | No (LVM needed) | No | Yes (native) | Yes (native) |
| Compression | No | No | Yes (zstd, lzo) | Yes (lz4, zstd) |
| Checksums | Metadata only | Metadata only | Full | Full |
| RAID | No (mdadm) | No (mdadm) | RAID 0/1/10/5/6 | RAID-Z1/2/3 |
| Online resize | Grow only | Grow only | Grow + shrink | N/A |
| Best for | General purpose | Large files, DB | Flexible storage | Enterprise |

## Mounting Filesystems

### `mount` and `umount`

```bash
# Mount a filesystem
mount /dev/sdb1 /mnt/data

# Mount with specific filesystem type
mount -t ext4 /dev/sdb1 /mnt/data

# Mount with options
mount -o rw,noatime,nodiratime /dev/sdb1 /mnt/data

# Common mount options
# rw/noatime        - Read-write, no access time updates
# noexec            - Don't allow execution
# nosuid            - Ignore SUID/SGID bits
# nodev             - Don't interpret device files
# discard           - SSD TRIM support
# compress=zstd     - Btrfs compression

# Bind mount
mount --bind /source/dir /mnt/point

# Mount all filesystems in /etc/fstab
mount -a

# Show mounted filesystems
mount | grep sdb
# /dev/sdb1 on /mnt/data type ext4 (rw,noatime,nodiratime)

# Or with findmnt (preferred)
findmnt
# TARGET        SOURCE     FSTYPE  OPTIONS
# /             /dev/sda3  ext4    rw,relatime
# ├─/boot       /dev/sda2  ext4    rw,relatime
# └─/home       /dev/sda3[/home] ext4 rw,relatime

# Unmount
umount /mnt/data
# Or: umount /dev/sdb1

# Force unmount busy filesystem
umount -l /mnt/data  # Lazy unmount (detach now, cleanup later)
umount -f /mnt/data  # Force (for NFS)
```

### `/etc/fstab` — Persistent Mounts

```bash
# /etc/fstab format:
# <device>  <mount>  <type>  <options>  <dump>  <fsck>

# Example /etc/fstab:
# <UUID>                              <mount>     <type>  <options>              <dump> <fsck>
UUID=12345678-abcd-efgh-ijkl-...     /           ext4    errors=remount-ro      0      1
UUID=ABCD-1234                        /boot/efi   vfat    umask=0077             0      1
UUID=87654321-dcba-hgfe-...           /data       ext4    defaults,noatime       0      2
UUID=abcd1234-...                     none        swap    sw                     0      0
tmpfs                                 /tmp        tmpfs   defaults,size=2G       0      0

# Find UUID for fstab
blkid /dev/sdb1
# /dev/sdb1: UUID="87654321-dcba-..." TYPE="ext4"

# Test fstab without rebooting
mount -a
# If no errors, fstab is correct

# Validate fstab syntax
findmnt --verify
```

## Checking and Repairing Filesystems

### `fsck` — Filesystem Check

```bash
# IMPORTANT: Never run fsck on a mounted filesystem!
# Always unmount first, or boot to rescue mode

# Check ext4 filesystem
fsck /dev/sdb1
# fsck from util-linux 2.39.3
# e2fsck 1.47.0 (5-Feb-2023)
# /dev/sdb1: clean, 123456/61054976 files, 98765432/244190592 blocks

# Force check even if clean
fsck -f /dev/sdb1

# Auto-repair (answer yes to all questions)
fsck -y /dev/sdb1

# Check only (no repair)
fsck -n /dev/sdb1

# Check specific filesystem type
fsck.ext4 -f /dev/sdb1
fsck.xfs /dev/sdb1     # XFS uses xfs_repair instead

# XFS repair
xfs_repair /dev/sdb2

# Btrfs check
btrfs check /dev/sdb1
btrfs check --repair /dev/sdb1  # DANGEROUS — use with caution
```

### When to Run fsck

```bash
# After unclean shutdown (power failure, kernel panic)
# The kernel checks /etc/fstab's last field (fsck order)
# 0 = skip, 1 = check first (root), 2 = check after root

# Force fsck on next boot (ext4)
touch /forcefsck
# Or tune2fs
tune2fs -C 20 /dev/sda2  # Set mount count high to trigger check

# Check filesystem stats
tune2fs -l /dev/sdb1 | grep -E "Mount count|Last checked|Check interval"
# Mount count:              5
# Maximum mount count:      30
# Last checked:             Mon Jul 15 02:00:00 2025
# Check interval:           15552000 (6 months)

# Set automatic check interval
tune2fs -c 25 /dev/sdb1           # Check every 25 mounts
tune2fs -i 6m /dev/sdb1           # Check every 6 months
tune2fs -c 0 -i 0 /dev/sdb1      # Disable automatic checks
```

## Disk Usage Analysis

```bash
# Overall disk usage
df -h
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/sda3        498G   50G  423G  11% /
# /dev/sda2        974M  256M  651M  29% /boot
# /dev/sdb1        2.0T  1.5T  500G  75% /data

# Inode usage (can fill up even with free space!)
df -i
# Filesystem      Inodes  IUsed   IFree IUse% Mounted on
# /dev/sda3      32768000 123456 32644544    1% /

# Directory usage
du -sh /var/*
# 2.1G    /var/log
# 800M    /var/cache
# 150M    /var/lib

# Find largest directories
du -h --max-depth=2 / | sort -rh | head -20

# Find largest files
find / -type f -exec du -h {} + 2>/dev/null | sort -rh | head -20

# Disk I/O monitoring
iotop -aoP        # Show accumulated I/O by process
iostat -xz 1      # Extended I/O statistics
```

## Disk Health Monitoring

```bash
# SMART disk health (requires smartmontools)
smartctl -a /dev/sda
# Key attributes to watch:
# ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE
#   5 Reallocated_Sector_Ct   0x0033   100   100   010    Pre-fail
#   9 Power_On_Hours          0x0032   097   097   000    Old_age
# 197 Current_Pending_Sector  0x0012   100   100   000    Old_age
# 198 Offline_Uncorrectable   0x0030   100   100   000    Old_age

# Quick health check
smartctl -H /dev/sda
# SMART overall-health self-assessment test result: PASSED

# Run self-test
smartctl -t short /dev/sda  # Short test (~2 min)
smartctl -t long /dev/sda   # Long test (~hours)

# Monitor with smartd
systemctl enable --now smartd
```

## LVM — Logical Volume Manager

LVM adds a flexible abstraction layer between physical disks and filesystems, enabling online resizing, snapshots, and spanning multiple disks:

### LVM Architecture

```mermaid
graph TB
    subgraph Physical
        P1["/dev/sda1<br>PV"]
        P2["/dev/sdb1<br>PV"]
        P3["/dev/nvme0n1p1<br>PV"]
    end
    subgraph Volume_Group["Volume Group: vg0"]
        VG["Physical Extents<br>4MB each"]
    end
    subgraph Logical_Volumes
        LV1["lv_root<br>50G / "]
        LV2["lv_home<br>200G /home"]
        LV3["lv_swap<br>8G"]
        LV4["lv_data<br>500G /data"]
    end
    P1 --> VG
    P2 --> VG
    P3 --> VG
    VG --> LV1
    VG --> LV2
    VG --> LV3
    VG --> LV4
```

### Creating LVM Volumes

```bash
# 1. Create physical volumes
pvcreate /dev/sda1 /dev/sdb1 /dev/nvme0n1p1
pvs
#  PV             VG  Fmt  Attr PSize   PFree
#  /dev/sda1      vg0 lvm2 a--  499.00g 499.00g
#  /dev/sdb1      vg0 lvm2 a--   <2.00t  <2.00t
#  /dev/nvme0n1p1 vg0 lvm2 a--  999.00g 999.00g

# 2. Create volume group
vgcreate vg0 /dev/sda1 /dev/sdb1 /dev/nvme0n1p1
vgs
#  VG  #PV #LV #SN Attr   VSize   VFree
#  vg0   3   0   0 wz--n- <3.46t <3.46t

# 3. Create logical volumes
lvcreate -L 50G -n lv_root vg0
lvcreate -L 200G -n lv_home vg0
lvcreate -L 8G -n lv_swap vg0
lvcreate -l 100%FREE -n lv_data vg0

lvs
#  LV      VG  Attr       LSize   Pool Origin Data%  Meta%
#  lv_data vg0 -wi-a-----  <3.20t
#  lv_home vg0 -wi-a----- 200.00g
#  lv_root vg0 -wi-a-----  50.00g
#  lv_swap vg0 -wi-a-----   8.00g

# 4. Create filesystems
mkfs.ext4 /dev/vg0/lv_root
mkfs.ext4 /dev/vg0/lv_home
mkswap /dev/vg0/lv_swap
mkfs.xfs /dev/vg0/lv_data

# 5. Mount
mount /dev/vg0/lv_root /mnt/root
mount /dev/vg0/lv_home /mnt/root/home
swapon /dev/vg0/lv_swap
mount /dev/vg0/lv_data /mnt/root/data
```

### LVM Snapshots

```bash
# Create a snapshot (COW-based, space-efficient)
lvcreate -L 10G -s -n snap_root /dev/vg0/lv_root
# Snapshots use space only for changed blocks

# Mount snapshot (read-only view of filesystem at snapshot time)
mount -o ro /dev/vg0/snap_root /mnt/snapshot

# View snapshot usage
lvs
#  snap_root vg0 swi-aos---  10.00g      lv_root 2.34

# Merge snapshot back (revert to snapshot state)
# WARNING: merges into origin, destroying current data
umount /mnt/root
lvconvert --merge /dev/vg0/snap_root
mount /dev/vg0/lv_root /mnt/root

# Thin-provisioned snapshots (more flexible)
lvcreate -L 100G --thinpool thin_pool vg0
lvcreate -V 50G --thin -n thin_vol vg0/thin_pool
lvcreate -s --name thin_snap /dev/vg0/thin_vol
```

### Online LVM Resize

```bash
# Extend logical volume (no downtime)
lvextend -L +50G /dev/vg0/lv_data
resize2fs /dev/vg0/lv_data     # ext4
# Or: xfs_growfs /data           # XFS

# Shrink ext4 (must unmount first!)
umount /mnt/home
e2fsck -f /dev/vg0/lv_home
resize2fs /dev/vg0/lv_home 100G
lvreduce -L 100G /dev/vg0/lv_home
mount /dev/vg0/lv_home /mnt/home

# Move data between physical volumes (online)
pvmove /dev/sda1 /dev/nvme0n1p1
```

### LVM Cache (dm-cache)

```bash
# Use SSD as cache for HDD
lvcreate -L 50G -n cache_data vg0 /dev/nvme0n1p1
lvcreate -L 1G -n cache_meta vg0 /dev/nvme0n1p1

# Convert to cached LV
lvconvert --type cache --cachepool cache_data --cachevol cache_meta vg0/lv_data

# Monitor cache hit rate
dmsetup status vg0-lv_data
lvs -o +cache_read_hits,cache_read_misses
```

## Disk Encryption with LUKS

```bash
# Create encrypted partition
cryptsetup luksFormat /dev/sdb1
# WARNING: Destroys all data. Enter passphrase.

# Open (unlock) encrypted partition
cryptsetup luksOpen /dev/sdb1 encrypted_data
# Creates /dev/mapper/encrypted_data

# Create filesystem on decrypted device
mkfs.ext4 /dev/mapper/encrypted_data
mount /dev/mapper/encrypted_data /mnt/secure

# Close (lock) encrypted partition
umount /mnt/secure
cryptsetup luksClose encrypted_data

# Add additional key slot
cryptsetup luksAddKey /dev/sdb1

# Auto-unlock with keyfile
dd if=/dev/urandom of=/root/.luks-key bs=4096 count=1
chmod 400 /root/.luks-key
cryptsetup luksAddKey /dev/sdb1 /root/.luks-key

# /etc/crypttab entry for auto-unlock:
# encrypted_data  UUID=<uuid>  /root/.luks-key  luks

# LUKS2 with Argon2id (modern, recommended)
cryptsetup luksFormat --type luks2 --pbkdf argon2id /dev/sdb1

# Benchmark PBKDF options
cryptsetup benchmark
# PBKDF2-sha1       N/A
# PBKDF2-sha256     N/A
# PBKDF2-sha512     N/A
# Argon2i           N/A
# Argon2id       N/A
```

## Swap Management

```bash
# Create swap file
fallocate -l 4G /swapfile       # Or: dd if=/dev/zero of=/swapfile bs=1M count=4096
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# /etc/fstab entry:
# /swapfile  none  swap  sw  0  0

# Swap partition
mkswap /dev/vg0/lv_swap
swapon /dev/vg0/lv_swap

# Monitor swap
swapon --show
# NAME       TYPE  SIZE  USED  PRIO
# /swapfile  file    4G  1.2G    -2

free -h
#               total   used   free  shared  buff/cache  available
# Mem:           16Gi   8.0Gi  2.0Gi  512Mi   6.0Gi       7.5Gi
# Swap:         4.0Gi   1.2Gi  2.8Gi

# Tune swappiness (0-100)
sysctl vm.swappiness=10  # Lower = prefer to keep data in RAM
# For databases: 1-10
# Default: 60

# Zswap: compressed swap cache
# CONFIG_ZSWAP=y
# Writes compressed pages to swap, reducing I/O
sysctl vm.swappiness=30
echo zstd > /sys/module/zswap/parameters/compressor
echo 200 > /sys/module/zswap/parameters/max_pool_percent

# ZRAM: compressed RAM-based block device
modprobe zram
echo zstd > /sys/block/zram0/comp_algorithm
echo 4G > /sys/block/zram0/disksize
mkswap /dev/zram0
swapon -p 100 /dev/zram0  # Higher priority = used first
```

## tmpfs — RAM-Based Filesystem

```bash
# Mount tmpfs (RAM-backed, volatile)
mount -t tmpfs -o size=512M,nr_inodes=100k tmpfs /mnt/ramdisk

# Common uses:
# /tmp — temporary files
# /run — runtime data (PID files, sockets)
# /dev/shm — shared memory

# /etc/fstab entries:
tmpfs  /tmp     tmpfs  defaults,size=2G,mode=1777  0  0
tmpfs  /var/log tmpfs  defaults,size=256M          0  0

# Monitor tmpfs usage
df -h /tmp
mount | grep tmpfs

# tmpfs is backed by both RAM and swap
# Actual usage can exceed RAM if swap is available
```

## Disk Quotas

```bash
# Enable quotas on filesystem
# Add usrquota,grpquota to /etc/fstab:
# /dev/vg0/lv_home  /home  ext4  defaults,usrquota,grpquota  0  2

mount -o remount /home
quotacheck -cugm /home
quotaon /home

# Set user quota (soft=warn, hard=block)
edquota -u myuser
# Filesystem   blocks   soft   hard   inodes  soft  hard
# /dev/vg0/lv_home  500000  1000000  1200000   5000  8000  10000

# Set group quota
edquota -g developers

# Check quotas
repquota /home
quota -u myuser

# Grace period (before soft limit becomes hard)
edquota -t
# Filesystem  Block grace period  Inode grace period
# /dev/vg0/lv_home  7days            7days
```

## Disk Management Workflow

```mermaid
graph TD
    A["1. Discover devices<br>lsblk, blkid"] --> B["2. Partition disk<br>fdisk / parted"]
    B --> C["3. Create filesystem<br>mkfs.ext4 / mkfs.xfs"]
    C --> D["4. Create mount point<br>mkdir /mnt/data"]
    D --> E["5. Mount filesystem<br>mount /dev/sdb1 /mnt/data"]
    E --> F["6. Add to fstab<br>UUID → /etc/fstab"]
    F --> G["7. Verify<br>mount -a, df -h"]
    G --> H["8. Monitor<br>smartctl, df, iostat"]
    
    style A fill:#3182ce,color:#fff
    style C fill:#38a169,color:#fff
    style F fill:#d69e2e,color:#fff
    style H fill:#e53e3e,color:#fff
```

## References

- [mount(8) man page](https://man7.org/linux/man-pages/man8/mount.8.html)
- [fstab(5) man page](https://man7.org/linux/man-pages/man5/fstab.5.html)
- [fdisk(8) man page](https://man7.org/linux/man-pages/man8/fdisk.8.html)
- [mkfs(8) man page](https://man7.org/linux/man-pages/man8/mkfs.8.html)
- [fsck(8) man page](https://man7.org/linux/man-pages/man8/fsck.8.html)
- [ArchWiki: Partitioning](https://wiki.archlinux.org/title/Partitioning)
- [ArchWiki: File systems](https://wiki.archlinux.org/title/File_systems)

## Related Topics

- [RAID](./raid.md) — Disk redundancy with mdadm
- [System Rescue](./rescue.md) — Filesystem repair and recovery
- [Disk I/O Scheduling](../kernel/processes/deadline-scheduling.md) — I/O scheduler design
