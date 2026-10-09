# resizepart — tell the kernel a partition is now a different size

## Overview

`resizepart` updates the size of one in-memory partition entry in the kernel: `resizepart /dev/sdb 3 41943040` declares that partition 3 of `/dev/sdb` now spans `41943040` sectors. It is a command-line wrapper around the `BLKPG_RESIZE_PARTITION` ioctl (kernel 3.6+) and shares its plumbing — and its philosophy — with `addpart` and `delpart`: the operator states the fact, the kernel records it, and **nothing on disk is touched**. It ships in the `util-linux` package (bookworm: `/usr/sbin/resizepart`).

You reach for it when the kernel's partition view is stale while the disk's layout already changed: an online-resized virtual disk or NVMe namespace, a loop image you `truncate -s +2G`-ed, a table rewritten by another host or tool while partitions were attached. It is often confused with `partx -u` (re-reads the *table on disk* and syncs the kernel to it — usually the better tool), `parted resizepart` (edits the on-disk table interactively), `growpart` (cloud-utils wrapper that rewrites the table with sfdisk and then lets the kernel follow), and `resize2fs`/`xfs_growfs` (the *filesystem* step that must follow any partition grow).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/resizepart |
| First appeared | util-linux 2.23 era (2013), on kernel 3.6 `BLKPG_RESIZE_PARTITION` |
| Standards | Linux `BLKPG` ioctl interface; not POSIX |

## Synopsis

```
resizepart [options] <diskdev> <partnr> <length>
```

Main one-line forms:

```
resizepart /dev/sdb 3 41943040          # partition 3 is now 41943040 sectors
resizepart /dev/nvme0n1 1 209715200     # NVMe namespace grew; kernel told
resizepart /dev/loop0 1 104857600       # loop image grew by 50 GiB
```

`length` is the new total size of the partition in **512-byte sectors** (not the delta), consistent with `addpart`/`delpart` in the same family.

## How It Works

### Kernel view vs disk truth

The kernel keeps partition entries as (number, start, length) records attached to the parent device; it only learns changes when told. Three ioctls mutate that list:

```
BLKPG_ADD_PARTITION     addpart / partx -a    "a partition exists at X, length Y"
BLKPG_DEL_PARTITION     delpart / partx -d    "forget partition N"
BLKPG_RESIZE_PARTITION  resizepart / partx -u "partition N now has length Z"
```

`resizepart` fills the ioctl with your three arguments and issues it. The kernel adjusts the partition's size — `/sys/block/<dev>/<dev>N/size` changes, the device node reflects it, and a udev change event fires — but the on-disk table is never read or written.

```
on-disk table:  part3: start=2048 len=OLD        (unchanged!)
kernel view:    part3: start=2048 len=NEW        (after resizepart)
filesystem:     must still be resized to use the space (resize2fs / xfs_growfs)
```

That triangle — table, kernel view, filesystem — is the whole mental model. `resizepart` moves exactly one vertex.

### Growing vs shrinking

- **Grow** is the intended use and is safe online: enlarge the backing store (hypervisor disk, NVMe namespace rescan, `truncate -s +N` on an image), tell the kernel the partition's new length, then grow the filesystem into it (`resize2fs` ext*, `xfs_growfs` XFS — both handle a live grow).
- **Shrink** is order-critical and rarely legitimate through this tool: the filesystem must be shrunk *first* (ext4 offline via `resize2fs`), then the partition; shrinking the kernel view first invites the fs writing beyond its new container. The kernel will typically still obey the ioctl — the safety ordering is on you.

### Getting the numbers right

```
$ blockdev --getsz /dev/sdb          # whole device, in 512-byte sectors
976773168
$ cat /sys/block/sdb/sdb3/start      # partition start, same units
2099200
```

New length = (desired end sector − start + 1). Cloud flows usually avoid hand-arithmetic by using `growpart` (which rewrites the table properly) — `resizepart` is the low-level tool for cases where the table is already correct or deliberately stale.

### The ioctl, byte for byte

The kernel-side contract (`linux/blkpg.h`):

```
struct blkpg_ioctl_arg { int op; int flags; int datalen; void *data; };
struct blkpg_partition { long long start;    /* bytes */
                         long long length;   /* bytes */
                         int pno;            /* partition number */ };
```

Note the units: the ioctl speaks **bytes** — `resizepart`'s sector argument is multiplied by 512 in userspace before the call. The kernel's resize handler validates against reality: the new end must not exceed the parent disk and must not collide with the next partition's start; violations fail the ioctl, a missing partition fails with "no such device or address"-class errors. On success the partition's `/sys/block/<dev>/<dev>N/size` (512-byte sectors) updates and a change uevent fires.

### Why this layer exists at all

Kernel partition objects are more than numbers: device nodes, holder links (dm/md/LVM PVs register against them), and udev consumers all hang off them. A full table re-read (BLKRRPART) tears that state down and rebuilds it — disruptive, and it fails while any partition is open. The BLKPG family mutates **one** entry atomically without touching siblings, which is why online grow works even with other partitions of the same disk mounted.

### Verifying the triangle after the call

```
table:   sfdisk -d /dev/sdb                 (unchanged by resizepart!)
kernel:  cat /sys/block/sdb/sdb3/size       (512B sectors, updated immediately)
         lsblk -b -o NAME,SIZE /dev/sdb
fs:      df -h /data                        (moves only after resize2fs/xfs_growfs)
         xfs_info /data                     (XFS: data blocks = fs size in blocks)
```

### Getting the numbers right, NVMe edition

NVMe namespaces are the modern cloud case: after the provider grows the namespace, the *device* itself must be told to re-read its capacity — `echo 1 > /sys/class/block/nvme0n1/device/rescan` on most drivers, or `nvme ns-rescan /dev/nvme0n1`. Only then does `blockdev --getsz` report the new total, and only then is there space for `resizepart` to declare. Skipping the rescan and running resizepart with a length beyond the kernel's idea of the disk is a guaranteed EINVAL. SATA/virtio disks expose the same idea as a rescan on the device node; loop devices take `losetup -c` instead.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Usage |
| `-V`, `--version` | Version |

There are no behavioral flags; all semantics live in the three positional arguments and the ioctl's error codes.

## Usage Patterns

```bash
# Cloud disk grew: rescan the device, then declare the new partition size
echo 1 > /sys/class/block/nvme0n1/device/rescan
resizepart /dev/nvme0n1 1 419430400
resize2fs /dev/nvme0n1p1
```

```bash
# Same flow for SCSI/virtio disks
echo 1 > /sys/class/block/sdb/device/rescan
resizepart /dev/sdb 2 838860800
xfs_growfs /data
```

```bash
# Loop image enlarged; expose the growth to the kernel
truncate -s +10G disk.img
losetup -c /dev/loop0                 # reflect new backing size on the loop device
resizepart /dev/loop0 1 210000000
mount -o remount,resize /mnt          # or umount+resize2fs per filesystem support
```

```bash
# Verify what the kernel believes now
partx -s /dev/sdb
cat /sys/block/sdb/sdb3/size
```

```bash
# Reconcile kernel view from the on-disk table instead (alternative to resizepart)
partx -u --nr 3 /dev/sdb
```

```bash
# Order for a deliberate shrink: filesystem first, then the kernel entry
resize2fs /dev/sdb3 80G
resizepart /dev/sdb 3 167772160
```

```bash
# Pre-flight geometry read: disk size (bytes and sectors) and partition start
blockdev --getsize64 /dev/sdb; blockdev --getsz /dev/sdb
cat /sys/block/sdb/sdb3/start

# Compute the length from a target end sector, then apply (length, not end!)
START=$(cat /sys/block/sdb/sdb3/start); END=419430400
resizepart /dev/sdb 3 $((END - START + 1))

# After the ioctl, wait for the change event before the next step in scripts
udevadm settle; partx -s /dev/sdb | tail -n +1 | head -5
```

```bash
# NVMe namespace grow: rescan the device first, then declare, then grow fs
nvme ns-rescan /dev/nvme0n1 2>/dev/null || echo 1 > /sys/class/block/nvme0n1/device/rescan
resizepart /dev/nvme0n1 1 "$(blockdev --getsz /dev/nvme0n1)"
xfs_growfs /data
```

```bash
# GPT disk grown in place: relocate the backup header, then sync the kernel
sgdisk -e /dev/sdb
resizepart /dev/sdb 3 "$(blockdev --getsz /dev/sdb)"
```

## Nuances and Gotchas

- **It never edits the on-disk table.** After reboot, the kernel re-reads the table and the "new" size is gone (or wrong). If the table is supposed to change, change it (`sfdisk`, `parted`); `resizepart` is for live reconciliation only.
- **`partx -u` is usually the better tool.** If the on-disk table already says the right size, `partx -u` syncs from truth instead of trusting an operator-computed number. `resizepart` exists for the cases where the table is *not* the source you trust.
- **Sector units, always 512.** Even on 4Kn drives the interface works in 512-byte sectors; mixing up `--getsize` (512B) and `--getsize64` (bytes) is the classic off-by-4096 error.
- **The filesystem does not follow automatically.** A grown partition shows free space no filesystem will use until `resize2fs`/`xfs_growfs` runs; a shrunk one can make the fs refuse to mount (or corrupt it if you force the order backwards).
- **Mounted partitions can be resized online** — that is the point of `BLKPG_RESIZE_PARTITION` — but shrinking below the filesystem's current end is data loss with no confirmation dialog. Script it defensively: read the fs size, compute, verify, then act.
- **Busy/absent partitions.** The partition number must exist in the kernel (`addpart` first if not), and some setups (device-mapper layered storage) route the request to the mapper rather than the disk — on LVM you resize the *LV*, not the partition.
- **udev races.** The size change triggers uevents; scripts that immediately mkfs/mount should wait on the expected node (`udevadm settle` or `partx -s` verification) rather than sleeping.
- **resizepart trusts your arithmetic.** A length that fits the disk but truncates a live filesystem does not error — the kernel checks only against the disk and neighbor partitions. Always derive lengths from `blockdev --getsz` and the partition's `start`, never from memory or a runbook's hardcoded numbers.
- **Device-mapper partitions are off-limits.** On dm-linear/LVM devices the "partitions" are dm targets, not blkpg entries — the ioctl does not apply; resize the LV (`lvextend`). `lsblk`'s TYPE column (`part` vs `lvm`) tells you which tool applies.
- **Boot-time consumers read the table, not your resize.** systemd-gpt-auto-generator, initramfs partition scanners, and other OS installs all parse the on-disk table; a kernel-only resize desynchronizes the next boot. If the change is meant to persist, write the table (sfdisk/parted) in the same change window.
- **GPT disks grown in place need the backup header moved first.** The backup GPT header sits at the old end-of-disk; until `sgdisk -e` (or parted) relocates it, the last partition cannot extend to the true end. Cloud "disk grew" guides that skip this step hit a mysterious ceiling below the new size.
- **RAID members: the array does not follow.** Growing the partition under an md member changes nothing at the RAID layer until `mdadm --grow` consumes the space — partition, array, LV, and filesystem each hold their own size, and no layer propagates automatically.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Kernel accepted the new size |
| 1 | Error: bad arguments, partition absent, ioctl refused (EINVAL for impossible sizes, ENXIO for a missing device) |

## Related Commands

- [`partx`](./partx.md) — table-driven sync (`-u`) and display; usually the first tool to try.
- [`addpart`](./addpart.md) — create a kernel partition entry by raw numbers.
- [`delpart`](./delpart.md) — delete one kernel partition entry.
- [`fdisk`](./fdisk.md) — interactive on-disk table editing (what resizepart deliberately avoids).
- [`losetup`](./losetup.md) — loop backing-file resize (`-c`) in the image workflows above.
- [`overview`](./overview.md) — hub page of the util-linux collection.

## Interview Questions

### Q: An EC2 instance's EBS volume was resized. Walk through making the extra space usable.

Rescan the block device (`echo 1 > /sys/class/block/<dev>/device/rescan` or NVMe namespace rescan) so the kernel sees the bigger disk; then make the partition bigger. The common path is `growpart /dev/nvme0n1 1` (rewrites the table) — `resizepart /dev/nvme0n1 1 <new-sector-count>` is the equivalent low-level declaration when you manage the table yourself; verify with `partx -s`. Finally grow the filesystem (`resize2fs` or `xfs_growfs`). All steps run online; only the *shrink* direction is dangerous and order-dependent.

### Q: What is the difference between `resizepart`, `partx -u`, and `parted resizepart`?

They touch different layers of the same triangle. `resizepart` asserts a size into the kernel via `BLKPG_RESIZE_PARTITION` and touches nothing on disk. `partx -u` reads the on-disk table and syncs the kernel's entries to it — kernel follows disk. `parted resizepart` rewrites the on-disk table itself (and triggers kernel sync). Pick by which side is the source of truth: disk already right → partx -u; disk intentionally stale/absent (loop images, operator math) → resizepart; disk wrong → parted/sfdisk.

### Q: Why does the kernel allow resizing a partition that is mounted, and what still makes shrinking dangerous?

`BLKPG_RESIZE_PARTITION` only changes the size metadata of a partition object; growing is non-destructive and the filesystem grows into space that was never part of it, so online growth is safe. Shrinking is the reverse: the kernel happily shrinks the container, but an ext4/XFS still occupying the old sectors will be truncated logically — corruption or fsck storms — unless the filesystem was shrunk first (ext4 offline; XFS cannot shrink at all). The ioctl is a blunt primitive by design; the safety ordering is policy, not enforcement.

### Q: After your resizepart call, df still shows the old size. Why?

Nothing is wrong yet: df reports the *filesystem*, and the partition grow does not propagate into it. You must run the filesystem grow step (`resize2fs /dev/...` for ext-family, `xfs_growfs /mountpoint` for XFS). Also verify the layer stack: on LVM the partition feeds a PV, so you need `pvresize` and `lvextend` before the filesystem; on loop devices `losetup -c` must refresh the backing size first. Interviewers use this to see whether you model the stack (disk → table → kernel view → PV/LV → fs) instead of assuming one command does it all.

### Q: Why does BLKPG_RESIZE_PARTITION exist when a full table re-read already worked?

BLKRRPART tears down and rebuilds every partition of the disk, which fails or disrupts while any is open — unusable for online growth. The BLKPG family mutates exactly one kernel entry (add/del/resize) atomically: one ioctl, no disturbance to sibling partitions, no table parsing in the kernel. resizepart and `partx -u` are userspace frontends choosing between "operator asserts the fact" (BLKPG) and "disk is the truth" (re-read paths).

### Q: A script runs resizepart, then immediately mkfs — and intermittently mkfs sees the old size. What is the race?

The ioctl returns after the kernel updates the entry, but the next tool may have raced the change uevent or read a cached capacity. Fix by synchronizing on observable state: wait until `/sys/block/.../size` reads the expected value (or `udevadm settle`), then proceed; and have the follow-up tool open the node after the resize, not before. Classic TOCTOU between kernel state change and userspace re-reading.

### Q: Where do resizepart and growpart differ, and when must you use the low-level tool?

growpart (cloud-utils) rewrites the on-disk table entry via sfdisk *and* triggers the kernel sync — it assumes the table is what needs fixing. resizepart only asserts kernel state, for cases where the table must not be touched or is already correct: loop images, tables written out-of-band by another host, or recovery flows where writing the table is impossible. The decision is "which layer is wrong": table → sfdisk/growpart; kernel view only → resizepart.

### Q: You grew the partition under an md RAID member, but the array still shows the old size. What completes the flow?

The array's component size is metadata fixed at creation/reshape; the kernel partition grow does not change it. Complete it layer by layer: confirm the member partitions grew (resizepart), then `mdadm --grow /dev/md0 --size=max` so the array claims the space, then grow whatever sits above (PV/LV, filesystem). Each layer has its own size knob and nothing propagates automatically — a one-line answer that doubles as the checklist.

### Q: Why is the length argument a total size in sectors, and not an end offset or a delta?

Consistency with its siblings: addpart and delpart speak the same (partnr, start, length) language as the BLKPG ioctls underneath, and BLKPG's struct carries absolute start+length in bytes. Total-size semantics make the call idempotent under retry (same arguments, same result), whereas a delta would double-apply on re-run — the failure mode automation fears most. The 512-byte sector unit is the block layer's convention; only the ioctl's bytes-vs-sectors conversion happens hidden inside the tool.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/resizepart.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
