# /sys/class/block

| Field | Value |
|---|---|
| Subsystem | Block layer core; block/genhd.c (block_class, disk_attrs), block/blk-sysfs.c (queue attributes), block/partitions/core.c (partition attributes) |
| Config gate | CONFIG_BLOCK (block/Kconfig menuconfig, default y; core files are obj-y in block/Makefile in master) |
| ABI documentation | Documentation/ABI/stable/sysfs-block (76 What: entries) + Documentation/ABI/testing/sysfs-block-device (8, ata/scsi device subtree) |
| Since | ABI entries span July 2003 (queue/nr_requests) to 2026; the class core predates the ABI file |
| Live (5.10.134 host) | 4 devices: vda 254:0, pmem0 259:0, pmem0p1 259:1, zram0 253:0 |
| Ledger ID | SYSC-block |

## What it represents

Block devices (disks and their partitions) registered by the block layer:
gendisk objects created by drivers such as virtio-blk, pmem and zram. The
sysfs ABI documentation spells the paths /sys/block/`<disk>`/ because genhd.c
also creates a legacy top-level kobject (block_depr, "create top-level block
dir" in genhd_device_init) and links every disk into it. The ledger counts the
76 stable/sysfs-block What: entries against this class precisely because the
file uses the /sys/block spelling of the same kobjects (worklog 2-a correction
(a)). On the live host /sys/class/block/vda and /sys/block/vda are both
symlinks into /sys/devices/virtio-mmio-cmdline/virtio-mmio.0/virtio0/block/vda.

## Relationship to the device model

Each gendisk is a struct device in block_class, parented under the physical
device (live: vda -> virtio0, pmem0 -> ndbus0/region0/namespace0.0 under
virtio2, zram0 under /sys/devices/virtual/block). The disk directory carries
the disk attributes, a queue/ subdirectory from blk_register_queue(), an mq/
subtree for blk-mq queues, and one directory per partition. A bdi symlink
points at the writeback state in /sys/class/bdi/<major:minor>. uevent carries
DEVNAME, DEVTYPE=disk or partition and DISKSEQ (block/genhd.c block_uevent).

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| dev | RO | major:minor, e.g. 254:0 | genhd.c disk_attrs[] |
| size | RO | sectors of 512 bytes; live vda = 20971520 | genhd.c (0444), part_size_show |
| ro | RO | 0 or 1; live vda = 0 | genhd.c (0444); set via ioctl, not this file |
| capability | RO | genhd capability mask | genhd.c |
| stat | RO | 17-field I/O counter line | ABI stable/sysfs-block, February 2008 |
| inflight | RO | 2 fields: reads, writes in flight | ABI, October 2009 |
| diskseq | RO | u64 monotonically increasing disk sequence | ABI, February 2021 |
| hidden | RO | 1 hides device from userspace (multipath members) | ABI, March 2023; newer than live host |
| alignment_offset | RO | bytes offset from natural alignment | ABI, April 2009 |
| events, events_async, events_poll_msecs | mixed | media event mask and polling control | genhd.c disk_attrs[] |
| queue/scheduler | RW | active in brackets; live: [mq-deadline] kyber bfq none | ABI, October 2004 |
| queue/rotational | RW | 1 for vda, 0 for pmem0 (live) | ABI, January 2009 |
| queue/read_ahead_kb | RW | KiB; live 128 | ABI, May 2004 |
| queue/max_sectors_kb | RW | KiB upper request bound | ABI, September 2004 (max_hw_sectors_kb RO) |
| queue/nomerges | RW | merge attempts disable bits | ABI, January 2010 |
| queue/nr_requests | RW | allocated requests per blk_mq_tags instance | ABI, July 2003 |
| queue/iostats | RW | on/off disk accounting | ABI, January 2009 |
| queue/wbt_lat_usec | RW | writeback throttle target latency, microseconds | ABI, November 2016 |
| queue/write_cache | RW | "write back" or "write through" | ABI, April 2016 |
| queue/dax | RO | 1 if CPU-addressable (pmem0) | ABI, June 2016 |
| hang | RO | host-specific attr seen live on vda; absent from master sources | live check (5.10.134), not ABI/source-verified |
| device/* (cdl_enable, ncq_prio_enable, ...) | RW | ata/scsi driver subtree | ABI testing/sysfs-block-device, driver-specific |

Entries added in master after the live kernel (atomic_write_* 2024, crypto/,
independent_access_ranges/, max_write_streams, write_zeroes_unmap_*,
iostats_passthrough, async_depth, zoned_qd1_writes) exist on newer kernels
only; queue/ contents differ per driver and queue type (blk_mq_queue_attrs[]
are hidden on bio-based queues).

## Safety and writes

Reads are safe. Writes to queue/* retune the live queue: read_ahead_kb,
nr_requests, nomerges, wbt_lat_usec and iostats take effect immediately for
all users of the disk. Writing queue/scheduler switches the elevator and
autoloads the scheduler module on demand. ro is read-only through sysfs; the
set-ro path is an ioctl. Some queue files exist only when the hardware
supports the feature (dax, zoned group). Do not write values into a queue
while the disk is under load from a filesystem that assumes the old limits.

## References

- Documentation/ABI/stable/sysfs-block and Documentation/ABI/testing/sysfs-block-device (cached at source-cache/linux-sparse)
- block/genhd.c, block/blk-sysfs.c, block/partitions/core.c, fetched from raw.githubusercontent.com/torvalds/linux/master
- Documentation/block/stat.rst and queue-sysfs.rst (named by the ABI file)
- Live enumeration /sys/class/block, /sys/block/vda/queue (read-only, kernel 5.10.134)
- Sibling pages: [bdi](./bdi.md), [nvme](./nvme.md); coverage: [ledger](../ledger.md)
