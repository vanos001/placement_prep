# addpart — tell the kernel a partition exists

## Overview

`addpart` asks the kernel to create an in-memory partition table entry on a
block device, without reading any partition table from disk. It is a
command-line wrapper around the `BLKPG_ADD_PARTITION` ioctl and exists for
the cases where you — the operator, a script, or another tool — already know
exactly which partition should exist at which offset, and the kernel either
does not know yet or refused to guess. Its mirror image is `delpart` (remove
one entry) and their big sibling is `partx` (scan a real table and add or
delete many entries at once). All three come from the util-linux project and
share the same libfdisk/libblkid-era plumbing.

On Debian the binary ships in the `util-linux` package and lives at
`/usr/sbin/addpart`, because it is a system-administration tool rather than
something a normal user session needs. You reach for it in recovery and
provisioning flows: creating a partition entry the kernel skipped, wiring up
a partition you just wrote with `dd` or `sfdisk`, or handing a specific
partition to a hotplug environment where a full table reread would be
disruptive. It is often confused with `partx -a` (which parses an actual
partition table) and with `blockdev --rereadpt` (which re-reads the whole
table but fails if the device is busy).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/addpart |
| First appeared | util-linux 2.13 era, as part of the partx family |
| Standards | Linux kernel `BLKPG` ioctl interface; not POSIX |

## Synopsis

```
addpart [options] <diskdev> <partnr> <start> <count>
```

Main one-line forms:

```
addpart /dev/sdb 3 2048 2097152        # add partition 3 at sector 2048
addpart /dev/loop0 1 16384 32768       # wire a partition into a loop device
```

`start` and `count` are in 512-byte sectors regardless of the device's real
sector size. Newer upstream releases also accept named options
(`--start`, `--count`) instead of the positional arguments, but the
positional form works everywhere and is what scripts use.

## How It Works

### The kernel's partition model

The kernel does not continuously watch disks for partition tables. It parses
the table once (at scan time, or when explicitly asked) and keeps the result
as a list of partition block devices: `/dev/sda1`, `/dev/sda2`, ... Each
entry is just a range — partition number, start sector, length — attached to
the parent device. Three ioctls manage that list:

```
BLKPG_ADD_PARTITION   -> kernel: "there is a partition at X, length Y"
BLKPG_DEL_PARTITION   -> kernel: "forget partition number N"
BLKPG_RESIZE_PARTITION-> kernel: "partition N now ends elsewhere"  (partx/growpart)
```

`addpart` fills four ioctl fields from its arguments and calls the kernel:

```
$ addpart /dev/sdb 3 2048 2097152
#  ioctl(BLKPG_ADD_PARTITION):
#      .start  = 2048  * 512 bytes
#      .length = 2097152 * 512 bytes
#      .pno    = 3
#  -> /dev/sdb3 now exists as a valid block device node target
```

Nothing on disk is read or written. If the on-disk table later says
something different, the kernel's live view and the table simply disagree
until you rescan (`partx -u`, `blockdev --rereadpt`) or fix the entry
yourself. That divergence is the tool's whole point: you can make the kernel
agree with reality you created out-of-band.

### Where the numbers come from

`start` and `count` are sectors — LBA units of 512 bytes:

```
# 1 MiB-aligned first partition, 4 GiB long
$ addpart /dev/sdb 1 2048 8388608
#                 | |    └── count: 4 GiB / 512 = 8388608 sectors
#                 | └────── start: 2048 sectors = 1 MiB
#                 └──────── partition number (becomes /dev/sdb1)
```

Two sources for the numbers in practice:

```
# sfdisk dump shows exactly these values (start/size are already sectors)
$ sfdisk -d /dev/sdb
...
/dev/sdb1 : start=      2048, size=   8388608, type=83

# /sys exposes the live view of every partition
$ cat /sys/block/sdb/sdb1/start /sys/block/sdb/sdb1/size
2048
8388608
```

### Why not just reread the table

`blockdev --rereadpt` (the `BLKRRPART` ioctl) re-reads the whole table, but
the kernel refuses when any partition of the device is open (mounted,
swapped, held by LVM...). `BLKPG` operations are incremental: adding one new
entry does not disturb entries the kernel already has, so it succeeds even
on a partially-in-use disk. `partx -a /dev/sdb` uses the same mechanism in a
loop over the on-disk table; `addpart` is that machinery with the table
reading removed.

```
typical recovery flow:

  dd image onto /dev/sdb        # image contains a table, kernel didn't notice
  partx -a /dev/sdb             # parse table, add entries          <- table-driven
  # or, for one known partition:
  addpart /dev/sdb 1 2048 8388608                                  <- operator-driven
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `<diskdev>` | Parent block device (`/dev/sdb`, `/dev/nvme0n1`, `/dev/loop0`) |
| `<partnr>` | Partition number; the kernel will expose `<diskdev><partnr>` |
| `<start>` | First sector of the partition, in 512-byte units |
| `<count>` | Length in 512-byte sectors; 0 is rejected |
| `--start <num>`, `--count <num>` | Named variants of the positional args in newer upstream releases |
| `-h`, `--help` | Usage summary |
| `-V`, `--version` | Version string |

There is deliberately no "dry run" and no force flag: the operation is a
single ioctl, and the kernel itself rejects out-of-range or overlapping
requests (`EINVAL`, `ENOTTY`, `EBUSY`).

## Usage Patterns

```bash
# Add a partition the kernel skipped after sfdisk wrote a new table
addpart /dev/sdb 2 8390656 10485760

# Wire up the first partition of a raw disk image served over a loop device
losetup /dev/loop0 disk.img
addpart /dev/loop0 1 16384 32768
mkfs.ext4 /dev/loop0p1
```

```bash
# Recover one partition of a busy disk where BLKRRPART would fail with EBUSY
# (sdb1 is mounted, sdb3 is the new one)
addpart /dev/sdb 3 20971520 20971520
```

```bash
# Numbers lifted straight from an sfdisk dump
sfdisk -d /dev/sdb | awk '$1 ~ /sdb3/ {print $4, $5}'   # start= size=
addpart /dev/sdb 3 8390656 20971520
```

```bash
# Create an entry matching what the on-disk GPT claims, after a failed rescan
partx -a /dev/sdb 2>/dev/null || addpart /dev/sdb 4 41945088 10485760
```

```bash
# Remove the experiment afterwards (the mirror tool)
delpart /dev/sdb 3
```

```bash
# Provisioning script: add partitions 1..2 from a spec file, then format
addpart /dev/vdb 1 2048 1048576 && mkswap /dev/vdb1
addpart /dev/vdb 2 1050624 20971520 && mkfs.ext4 /dev/vdb2
```

```bash
# Sanity-check the live entry you just created
cat /sys/block/sdb/sdb3/start /sys/block/sdb/sdb3/size
blkid /dev/sdb3    # probe it for a filesystem superblock
```

```bash
# Testing partition-aware tooling against a loop device, no real disk needed
truncate -s 64M img.bin
losetup /dev/loop1 img.bin
addpart /dev/loop1 1 2048 100352
```

## Nuances and Gotchas

- **Sector size trap.** `start`/`count` are *always* 512-byte units in the
  util-linux interface, even on 4Kn drives where the hardware sector is 4096
  bytes. Converting a byte offset from a spec sheet without dividing by 512
  puts the partition in the wrong place by 8x.
- **Nothing is written to disk.** The entry lives only in the kernel. A
  reboot, a `partx -u`, or a `blockdev --rereadpt` will replace it with
  whatever the table says — possibly nothing. If you needed it persistently,
  write a real table (`sfdisk`, `cfdisk`).
- **Partition number vs device naming.** On `sd`/`vd`/`loop` devices the
  node is `<disk>p<partnr>` only when the disk name ends in a digit
  (`loop0p1`); `sdb3` has no `p`. `addpart` does not create the node itself;
  the kernel + udev do. In minimal containers with no udev, the node may
  never appear — `mknod` it yourself.
- **EBUSY/EINVAL are the kernel's opinion.** Overlap with an existing
  partition, a start beyond the disk end, or a duplicate number all come
  back as `EINVAL`; the ioctl fails, nothing is half-added.
- **BLKRRPART wipes your work.** A later whole-table reread by another tool
  silently deletes kernel-side entries you added by hand.
- **GPT partitions get UUIDs only from a table.** An `addpart`-created entry
  has no PARTUUID/PARTLABEL, so tools keyed on those (`blkid -t
  PARTUUID=...`, `mount PARTUUID=`) will not see it.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | The ioctl succeeded; the partition entry exists in the kernel |
| 1 | Usage error, or the ioctl failed (`EINVAL`, `EBUSY`, permissions) |

## Related Commands

- [`blockdev`](./blockdev.md) — `--rereadpt` is the whole-table alternative; `--getsz` to size disks
- `partx` / `delpart` — the table-driven bulk add/delete and resize siblings of the same ioctl family
- [`cfdisk`](./cfdisk.md) — interactive editor that *writes* a real table to disk
- [`blkid`](./blkid.md) — probe the partition you just added for filesystems/UUIDs
- [util-linux overview](./overview.md) — the other block-device and disk tools in this collection

## Interview Questions

### Q: What does addpart actually do, and what does it not do?

It performs a `BLKPG_ADD_PARTITION` ioctl, which inserts one partition-range
entry (number, start, length in 512-byte sectors) into the kernel's in-memory
list for a disk. It does not read the on-disk partition table, does not write
anything to disk, and does not create device nodes itself — kernel and udev
do that in response. The result is volatile: any table rescan replaces it.

### Q: When would you use addpart instead of blockdev --rereadpt or partx -a?

`--rereadpt` re-reads the entire table and fails with `EBUSY` when any
partition of the disk is open; `partx -a` parses the table on disk. Use
`addpart` when the disk is partially in use (one partition mounted, so a full
reread would fail), or when you know the intended geometry out-of-band — for
example after `dd`-ing an image or in provisioning scripts — and want to add
exactly one entry without a table parse.

### Q: Why are start and count specified in 512-byte sectors, and what breaks because of that?

The `BLKPG` interface predates widespread 4Kn drives and fixed 512 bytes as
the unit. On a 4Kn drive, a byte offset taken from documentation must be
divided by 512, not 4096, or the partition lands at one-eighth of the
intended position — usually as an `EINVAL` overlap, occasionally as silent
data confusion with whatever occupies that LBA range.

### Q: A script does `dd` of a partition image onto /dev/sdb3, and the size of the on-disk partition differs. How do the tools interact here?

`dd` changes bytes, not kernel metadata. If the backing partition entry is
too small, use `partx -u`/`growpart`-style resizing (the `BLKPG_RESIZE_PARTITION`
ioctl) — or `addpart` a correctly sized entry on a spare disk. The key
interview point: `addpart` can create a *different* live geometry than the
table, and tools like `blkid`, `fsck`, and the filesystem driver will then
trust the live entry, not the disk.

### Q: Why does the new partition sometimes not appear as /dev/sdb3 even though addpart exited 0?

The ioctl only updated kernel state. Device nodes are created by devtmpfs and
renamed/permissioned by udev. In chroots, minimal containers, or rescue
environments without udev, no node appears; you `mknod /dev/sdb3 b 8 19`
yourself (major 8, minor = base + partition number) and everything works.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/addpart.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
