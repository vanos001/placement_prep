# delpart — tell the kernel to forget a partition

## Overview

`delpart` asks the *running kernel* to drop one partition from its in-memory view
of a disk. It does not edit anything on the storage medium: no partition table
sector is read, written, or erased. The command wraps the `BLKPG_DEL_PARTITION`
ioctl on the whole-disk device and exits.

Syntax is minimal and positional: the whole disk and the partition *number*.
`delpart /dev/sdb 3` removes kernel partition `/dev/sdb3` (the in-memory
object) — the on-disk table still describes it, and the next table re-read will
bring it back. To change what is on disk you use `fdisk`/`sfdisk`/`parted`; to
reload the kernel view from disk you use `partx -u`, `partprobe`, or
`blockdev --rereadpt`.

It is one of a trio of thin util-linux wrappers around the BLKPG interface —
`addpart` (create a kernel partition), `resizepart` (change its size), and
`delpart` — used by installers, `kpartx`-style tooling, scripts driving LVM or
loop setups, and anyone hot-managing partition views without a full table edit.
In Debian bookworm it ships in the `util-linux` package at `/usr/sbin/delpart`,
man section 8.

It is often confused with `fdisk`'s delete (`d`) command — same word, totally
different target: fdisk edits the on-disk table and only *later* informs the
kernel, while `delpart` informs the kernel only.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Section (man) | 8 |
| Path | /usr/sbin/delpart |
| Lineage | util-linux original (BLKPG wrapper family) |
| Standards | None — Linux-specific ioctl interface |

## Synopsis

```
delpart device partition
```

Both call shapes:

```
delpart /dev/sdb 3        # kernel forgets /dev/sdb3 (in-memory only)
delpart /dev/nvme0n1 2    # same for the NVMe namespace
```

## How It Works

### Two tables: disk and kernel

A block device exists twice: as on-disk partitioning metadata (MBR/GPT sectors)
and as kernel objects — device nodes like `/dev/sdb3` backed by the block layer
partition structures (visible in `/sys/block/sdb/sdb3/`). Editors like `fdisk`
write the on-disk copy and then trigger a re-read; the BLKPG trio manipulates
the kernel copy *directly*, sector by sector untouched:

```
   on-disk layout                kernel in-memory partition table
  ┌─────────────────┐            ┌──────────────────────────────┐
  │ MBR/GPT sectors │            │ sdb1 sdb2 sdb3 (sysfs nodes) │
  └────────┬────────┘            └───────▲──────────────┬───────┘
           │ read/verify                 │ BLKPG_ADD    │ BLKPG_DEL
           ▼                             │ BLKPG_RESIZE │ (delpart)
     fdisk / sfdisk / parted ────────────┴──── partx -u / partprobe / blockdev
     (writes table, then re-reads)              (direct kernel-view surgery)
```

`delpart` performs exactly one ioctl: `BLKPG_DEL_PARTITION` with the partition
number. Success means the block device node and sysfs entry disappear until
something re-adds them — either another `addpart`/`partx -u` or a full table
re-read that discovers the partition is still described on disk.

### Arguments are literal

The `device` argument must be the **whole-disk** node (`/dev/sdb`, not
`/dev/sdb3`), and `partition` is the bare number (not a device name). The
partition must currently exist in the kernel's view, or the ioctl fails with
`ENXIO`/`EINVAL`.

### Busy partitions fail

The kernel refuses to delete a partition that is in use — a mounted filesystem,
active swap, an open block descriptor, or a partition claimed by device-mapper.
This is a hard safety property of the same kind that protects `partx`/`resizepart`
operations; the fix is to unmount/stop the consumer first (`umount`, `swapoff`,
`dmsetup remove`, close the loop device).

### The BLKPG trio

The three wrappers share one shape — disk node plus partition number — and one
philosophy: kernel-view surgery without on-disk edits.

| Tool | Signature | Effect |
| --- | --- | --- |
| `addpart` | `addpart <disk> <nr> <start> <size>` | Create a kernel partition object at sector range |
| `resizepart` | `resizepart <disk> <nr> <size>` | Change an existing partition's size in the kernel view |
| `delpart` | `delpart <disk> <nr>` | Remove the kernel partition object |

(Start/size are in 512-byte sectors regardless of the device's real sector
size — a detail that bites on 4K-sector disks.) The same operations exist
inside `partx` (`-a`, `-u`, `-d` operate on ranges) and in
`blockdev --rereadpt`, so production scripts often prefer `partx -u` for
resync and reserve the wrappers for single-partition precision work.

### Why this exists at all

Scripts that assemble storage dynamically — LVM helper tools, multipath,
`kpartx`, container/VM image tooling — need to add/remove partition objects
without rewriting a table, including cases where there *is* no on-disk table
(e.g. partitions carved out of a raw image mapped onto a loop device, or
metadata-driven setups). The BLKPG ioctls are that API; the three wrappers are
its human interface.

## Options That Matter

`delpart` takes no options (besides `--help`/`--version`); its interface is two
positional arguments:

| Argument | Meaning |
| --- | --- |
| `device` | Whole-disk device node, e.g. `/dev/sdb` |
| `partition` | Partition number currently known to the kernel (1-based; 1, 2, 3…) |

## Usage Patterns

```bash
# See what the kernel currently believes before touching anything
lsblk /dev/sdb
cat /proc/partitions | grep sdb
```

```bash
# Kernel-forget a partition that is no longer needed (unmounted!)
sudo delpart /dev/sdb 3
```

```bash
# Confirm the device node is gone from the kernel view
ls /dev/sdb* 2>/dev/null; ls /sys/block/sdb/
```

```bash
# Bring it back: re-read the on-disk table into the kernel
sudo partx -u /dev/sdb         # or: sudo partprobe /dev/sdb
lsblk /dev/sdb                 # confirm the view matches the table
```

```bash
# Add a partition object out of thin air (start/size in 512-byte sectors)
sudo addpart /dev/sdb 5 2048 4096000
sudo delpart /dev/sdb 5        # ... and remove it again
```

```bash
# Hot-plug cleanup script fragment: drop stale partitions after device churn
for p in $(lsblk -rno MAJ:MIN,TYPE /dev/sdb | awk '$2=="part"{print $1}'); do
    : # decide per your policy; delpart takes the number, not MAJ:MIN
done
```

```bash
# Failure case: partition is mounted — kernel refuses
sudo delpart /dev/sdb 1        # delpart: failed to remove partition: Device or resource busy
```

```bash
# NVMe example — same interface, namespace device as the disk node
sudo delpart /dev/nvme0n1 2 && partx --show /dev/nvme0n1
```

```bash
# Loop-device image work: partitions added by losetf -P can be dropped likewise
sudo losetup -fP disk.img && losetup -l
sudo delpart /dev/loop0 1       # kernel-forgets loop0p1; image bytes untouched
```

## Nuances and Gotchas

- **It does not delete data.** The on-disk table still lists the partition;
  any re-read (`partx -u`, reboot, `partprobe`) resurrects it. Interview trap:
  "delpart" is kernel-view surgery, not partition deletion.
- **Whole disk + bare number.** `delpart /dev/sdb1 1` is wrong; the tool wants
  the containing disk and the index.
- **Busy is fatal.** Mounted filesystems, swap, dm claims and open descriptors
  block the ioctl with `EBUSY`. Nothing lazy happens — no "force".
- **udev may race you.** Device removal/addition triggers udev events; nodes can
  reappear or lag. In scripts, `udevadm settle` around the operation beats
  naive sleeps.
- **No dry run.** One syscall, one effect. Combine with `lsblk`/`partx --show`
  checks in scripts.
- **Everything is root-only.** The BLKPG ioctls require `CAP_SYS_ADMIN`; there
  is no unprivileged variant, and inside containers the kernel may refuse
  operations on devices the container's cgroup/device rules do not expose.
- **The trio is uniform.** `addpart` and `resizepart` take the same disk+number
  shape (add needs start/size in 512-byte sectors); learning one is learning all.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | The kernel removed the partition |
| 1 | Failure — wrong usage, no such partition, or device busy |

## Related Commands

- [`overview`](./overview.md) — index of all util-linux collection pages
- [permissions](../../admin/permissions.md) — why the BLKPG ioctls need root/CAP_SYS_ADMIN

## Interview Questions

### Q: What does delpart actually change?

Only the kernel's in-memory partition table: it issues `BLKPG_DEL_PARTITION` for
the given disk+number, so the partition device and its sysfs entry disappear.
The on-disk partition table is untouched; the next re-read (partx -u, partprobe,
reboot) restores the partition if the disk still describes it.

### Q: How is delpart different from pressing 'd' in fdisk?

fdisk's `d` removes the partition *from the edited on-disk table*, which is then
written with `w` (and only afterwards reflected into the kernel). `delpart`
never touches the disk; it removes the kernel's view immediately. One edits
metadata at rest, the other metadata in RAM.

### Q: A delpart call fails with "Device or resource busy". What now?

The kernel protects in-use partitions: find the consumer (`findmnt`,
`swapon --show`, `dmsetup ls`, `losetup -l`, `fuser`), stop it — unmount,
`swapoff`, remove the mapping — and retry. There is no force flag; the refusal
is the safety net.

### Q: Why would a script want to remove a kernel partition without touching the disk?

Dynamic storage assembly: LVM/multipath/kpartx-style tools create and destroy
partition views on demand (for example partitions carved from a VM image on a
loop device, or renumbered partitions during reprovisioning). Direct BLKPG
manipulation via `addpart`/`delpart` avoids rewriting tables or rebooting to
resync the kernel.

### Q: How do you restore what delpart removed?

Re-read the table from disk with `partx -u <disk>` or `partprobe <disk>` (or
`blockdev --rereadpt`), which re-adds every partition the on-disk table still
describes. If the partition was added out of thin air with `addpart` and has no
on-disk entry, recreate it with `addpart` using the same start/size.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/delpart.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
