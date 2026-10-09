# partx — tell the kernel about partitions listed in a partition table

## Overview

`partx` reads a real partition table from a block device (or image) and updates the kernel's in-memory partition list accordingly: adding entries the kernel does not know, deleting stale ones, updating changed sizes, or simply displaying the table. It ships in the `util-linux` package (bookworm: `/usr/sbin/partx`) and is the table-driven generalization of its single-entry siblings `addpart` and `delpart`, which just shout one ioctl each with operator-supplied numbers.

You reach for it when the kernel's view and the disk's truth diverge: after `dd`-ing an image with a partition table onto a live disk, after `losetup` of a partitioned image without `-P`, after resizing a table with `sfdisk` while partitions are attached, or to display a table without mounting anything. It is often confused with `partprobe` (parted's equivalent, external dependency), `kpartx` (multipath-tools' mapper-based variant that creates `/dev/mapper` entries), `blockdev --rereadpt` (whole-table reread that fails hard when the device is busy), and `lsblk` (pure display of kernel state, no table parsing).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/partx |
| First appeared | util-linux 2.11 era (early 2000s), libfdisk rewrite in 2.26 |
| Standards | Linux `BLKPG`/`BLKRRPART` ioctls; not POSIX |

## Synopsis

```
partx [-a|-d|-s|-u] [--nr <n:m> | <partition>] <disk>
```

Main one-line forms:

```
partx -s /dev/sdb               # show the table as read from the disk
partx -a /dev/sdb               # add all table partitions the kernel lacks
partx -d --nr 3:5 /dev/sdb      # delete kernel partitions 3..5
partx -u /dev/loop0             # update sizes/offsets from the table
```

## How It Works

### Kernel view vs disk truth

The kernel parses a partition table once (device scan, hotplug, or explicit request) and keeps the result as partition objects (`/dev/sdb1`, ...) — number, start sector, length. It never re-reads the disk on its own. Two ioctl families manage that list:

```
BLKPG_ADD_PARTITION     one entry: number, start, length   (addpart, partx -a)
BLKPG_DEL_PARTITION     one entry: number                  (delpart, partx -d)
BLKPG_RESIZE_PARTITION  one entry: number, new length      (resizepart, partx -u)
BLKRRPART               reread the whole table             (blockdev --rereadpt)
```

`partx` parses the on-disk table with libfdisk (MBR/dos, GPT, BSD, Sun, SGI...) and then issues the per-partition `BLKPG` ioctls. Because each ioctl targets one partition, partial updates succeed where `BLKRRPART` would fail with `EBUSY` (it refuses if *any* partition of the disk is in use). That selective behavior is partx's main reason to exist.

### The BLKPG structures, concretely

Each operation is one `ioctl(fd, BLKPG, &blkpg_ioctl_arg)` where the argument carries an op code (`BLKPG_ADD_PARTITION`, `BLKPG_DEL_PARTITION`, `BLKPG_RESIZE_PARTITION`) and a pointer to:

```c
struct blkpg_partition {
    long long start;   /* byte offset into the disk  */
    long long length;  /* partition length in BYTES  */
    int pno;           /* partition number           */
};
```

Note the units: BLKPG speaks bytes while partx's display and `--nr` math speak 512-byte sectors — the same byte/sector seam behind the classic `losetup -o` bug. The kernel validates each request against the disk's capacity and the existing partition map (overlap → EINVAL; deleting an in-use partition → EBUSY), then instantiates the partition in the disk's in-memory partition table; devtmpfs creates the `/dev/sdbN` node and udev processes the uevent after the ioctl returns, which is why nodes appear asynchronously.

### The four modes

```
-s, --show     display the table (default display when no add/del/update given)
-a, --add      for each table entry the kernel lacks: create the partition
-d, --delete   remove kernel partitions (all, or the --nr range)
-u, --update   update start/size of existing partitions from the table
```

`-s` alone never touches the kernel — it is a table reader (with libblkid superblock awareness to avoid false partition detection inside filesystems). Without `-a/-d/-u` and without `-s`, partx also just lists.

### Output columns

```
$ partx -s /dev/sdb
NR   START      END  SECTORS   SIZE NAME UUID
 1      2048  1050623  1048576   512M      8f5e...
 2   1050624  3145727  2097152     1G      12ab...
```

Columns (`-o` selects, `--output-all` shows everything): `NR`, `START`, `END`, `SECTORS`, `SIZE`, `NAME`, `UUID`, `TYPE`, `FLAGS`, `SCHEME`. `-b` prints SIZE in bytes instead of human units; `-P` gives `key="value"` pairs; `-r` raw; `-g` suppresses headers. `START`/`END` are in 512-byte sectors unless `-S` overrides the sector size assumption.

### Probing and forcing

Table discovery goes through libfdisk: it reads the first sectors, tries each supported scheme (`partx --list-types` prints the set: `dos`, `gpt`, `sun`, `sgi`, `bsd`, `mac`, `aix`, `ultrix`, `unixware`, `PMBR`), and uses libblkid's superblock detection to avoid "finding" partitions inside filesystem data. `-t <type>` short-circuits probing when you know the answer (RAID-member disks with leftover vendor metadata are the usual case), and `-S` fixes the sector-size assumption when 4Kn disks or DM layers make the 512-byte default wrong.

### A full reconcile workflow

The production sequence for "disk changed underneath the system":

```bash
partx -s /dev/sdb                 # what the DISK says (libfdisk read)
cat /proc/partitions              # what the KERNEL knows
partx -u /dev/sdb                 # update sizes of entries that exist
partx -a /dev/sdb                 # add entries the kernel lacks
partx -d --nr 6: /dev/sdb         # drop stale high-numbered entries
lsblk /dev/sdb                    # confirm kernel view == disk truth
```

`-u` before `-a` matters on grow workflows: an existing entry that changed size cannot be "added" (it exists), only updated; stale high entries keep old device nodes alive, so delete them explicitly. `--nr 6:` is an open-ended range — from partition 6 to the end.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a`, `--add` | Add missing partitions to the kernel |
| `-d`, `--delete` | Delete kernel partition entries |
| `-u`, `--update` | Update sizes/offsets of existing entries |
| `-s`, `--show` | List the table (read-only) |
| `-n`, `--nr <n:m>` | Restrict to a partition number or range (`3`, `2:4`, `:6`) |
| `-o`, `--output <list>` | Choose columns; `--output-all` for everything |
| `-g`, `--noheadings` | Headerless output for scripts |
| `-P` / `-r` | key="value" pairs / raw single-line format |
| `-b`, `--bytes` | Sizes in bytes, not human-readable |
| `-S`, `--sector-size <num>` | Override sector size for start/end math |
| `-t`, `--type <type>` | Force table type (dos, gpt, ...) instead of probing |
| `-v`, `--verbose` | Say what is being added/deleted and why |

## Usage Patterns

```bash
# Kernel missed partitions after dd of an image onto a live disk
dd if=tiny.img of=/dev/sdb && partx -u /dev/sdb
```

```bash
# Make kernel aware of a partitioned image attached without -P
losetup /dev/loop0 disk.img
partx -a /dev/loop0
```

```bash
# Show the table without touching the kernel (safe on mounted disks)
partx -s -o NR,START,SIZE,UUID /dev/nvme0n1
```

```bash
# Remove stale kernel entries for partitions you are about to rewrite
partx -d --nr 3:4 /dev/sdb
```

```bash
# Machine-readable output for provisioning code
partx -sgo NR,SIZE,UUID --pairs /dev/sdb
```

```bash
# After sfdisk resized partition 2 online, sync the kernel view
sfdisk /dev/sdb <<EOF && partx -u --nr 2 /dev/sdb
...
EOF
```

```bash
# Clean slate before re-imaging: drop every kernel partition entry
partx -d /dev/sdb
```

```bash
# Force a table type when probing is ambiguous (RAID superblocks etc.)
partx -s -t gpt /dev/sdc
```

```bash
# List supported partition table types
partx --list-types
```

```bash
# Verify kernel view vs disk truth (the disagreement IS the diagnosis)
partx -s /dev/sdb; cat /proc/partitions
```

```bash
# After a cloud disk grew and sfdisk/parted rewrote the last partition online
partx -u --nr 1 /dev/sdb          # then grow the fs itself (resize2fs/xfs_growfs)
```

```bash
# Pair format for config management (no awk gymnastics)
partx -g -P -o NR,START,SECTORS /dev/nvme0n1
```

```bash
# Drop stale entries after shrinking a table, verify via lsblk (kernel view)
partx -d /dev/sdb && lsblk /dev/sdb
```

```bash
# Add one specific missing partition only (scoped, fast, no other changes)
partx -a --nr 3 /dev/sdb
```

## Nuances and Gotchas

- **`partx -a` does not renumber around you.** Adding entry 5 when 5 exists fails (`BLKPG` refuses overlap/duplicates); delete first (`-d --nr 5`) then add. Numbering follows the *table*, and shrinking/re-writing tables can leave stale high-numbered devices (`sdb7` for a table that now has 3 partitions) — those stale entries keep working until deleted.
- **In-use partitions resist deletion.** A mounted or open partition yields `EBUSY` on `-d`; that is the kernel protecting data, the same rule `umount` obeys.
- **`-s` reads the disk, `/proc/partitions` reads the kernel.** When they disagree, that *is* the diagnosis; don't "fix" display differences by adding `-f`-style hacks — decide which side is right.
- **Sector size assumptions.** 4K-sector drives and DM/loop setups make `-S` relevant; mixing 512-byte math with a 4096-byte geometry produces starts that are silently wrong but table-legal.
- **False partitions inside filesystems.** Old filesystems/data can contain MBR-like garbage; libblkid's superblock detection filters most, but `-t` forcing or wiping (`wipefs`) is the honest fix.
- **busybox/old versions differ.** Old util-linux partx had fewer columns and no `-u`; scripts relying on `--pairs` or `UUID` columns need a modern util-linux (Debian bookworm is fine).
- **It never writes the table.** partx is kernel-notification only. Changing the on-disk table is `fdisk`/`sfdisk`/`parted` territory; partx just reconciles the kernel with whatever is there.
- **BLKPG is bytes, partx display is sectors.** When scripting raw `addpart`/ioctl calls alongside partx, remember `blkpg_partition.start/length` are byte values; mixing the vocabularies shifts everything by 512×, silently.
- **Nodes appear asynchronously.** The ioctl returns before udev finishes the uevent; a `mkfs /dev/sdb1` on the next line can race node creation. `udevadm settle` (or a retry loop) closes the gap.
- **dm/multipath stacks use a different mechanism.** On device-mapper, "partitions" are separate dm table entries (kpartx's job), so partx's BLKPG route targets native kernel partition objects; running the wrong mechanism for the stack either no-ops or duplicates state.
- **`-u` is the gentle mode for online growth.** Update-in-place keeps existing open block devices valid; delete+add on a mounted partition fails outright with EBUSY. Resize workflows should always prefer `-u --nr N`.
- **`-u` only touches entries the kernel already has.** It never creates missing ones — that is `-a`'s job. Production reconcile runs pair them (`-u` then `-a`), as in the workflow above; running `-u` alone after adding partitions to the disk silently does nothing for the new entries.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success (all requested operations applied / table listed) |
| 1 | Error: cannot read device or table, ioctl refused (EBUSY, overlap), usage error |

## Related Commands

- [`addpart`](./addpart.md) — assert one partition entry by raw numbers, no table parsing.
- [`delpart`](./delpart.md) — remove one kernel partition entry.
- [`resizepart`](./resizepart.md) — resize one kernel entry to an explicit length.
- [`fdisk`](./fdisk.md) / `sfdisk` — create and modify the on-disk table that partx then syncs.
- [`losetup`](./losetup.md) — loop devices for images; `losetup -P` vs `partx -a` are the two ways to expose image partitions.
- [`blkid`](./blkid.md) — filesystem/`PARTUUID` identification used for fstab sources.
- [`overview`](./overview.md) — hub page of the util-linux collection.

## Interview Questions

### Q: What is the practical difference between `partx -a`, `blockdev --rereadpt`, and `partprobe`?

All three sync kernel state from a disk table, with different granularity and failure behavior. `blockdev --rereadpt` issues `BLKRRPART`: whole-table reread that fails outright if any partition on the disk is open. `partx -a` walks the table and issues per-partition `BLKPG_ADD_PARTITION` calls, so it can succeed selectively around busy partitions and can be scoped with `--nr`. `partprobe` does the same job as partx but comes from parted (extra package dependency). Interviewers expect "BLKRRPART is all-or-nothing, BLKPG is per-partition".

### Q: After rewriting the partition table on a disk that has mounted partitions, what sequence keeps the system consistent?

You cannot resize or move mounted partitions safely. If only *new* partitions were appended: `partx -a` (or `partprobe`) to register them, then mkfs/mount. If an existing partition shrank/moved: umount (and stop users) first, `partx -u` or delete+add the entry, then fix filesystems. If the table shrank overall, delete stale high-numbered entries (`partx -d`) so no stale device nodes keep exposing data. Anything touching in-use partitions returns EBUSY by design.

### Q: Why does `losetup -P` exist if `partx -a` works on loop devices?

They act at different layers: `losetup -P` has the kernel's loop driver scan the table at attach time and create `loop0p1...` nodes immediately; `partx -a` is the generic post-attach sync for any device, including loop. `-P` is the convenient one-shot for images; partx wins when the image changes while attached, when you need selective ranges/columns, or when you are on a kernel path without per-loop partition scanning.

### Q: How does partx avoid misdetecting partitions inside filesystem or RAID signatures?

It uses libblkid's superblock detection: before trusting an MBR/GPT parser, it checks for known filesystem/RAID signatures, which would indicate the "table" is actually data. Ambiguous devices (wiped partially, vendor metadata) can still confuse probing — hence `-t` to force a scheme and `wipefs` to clear stale signatures before repartitioning. This is the same probing layer `blkid` and `mount` use for type detection.

### Q: Walk through what the kernel does when `partx -a` succeeds on one new partition.

libfdisk parses the table from the device; partx compares it with the kernel's current partition set and issues `BLKPG_ADD_PARTITION` with byte-precise start/length for the missing entry. In the kernel the request is bounds-checked (fits on the disk, no overlap with existing partitions), then the partition is instantiated in the disk's partition table and registered as a block device; devtmpfs creates the node and udev handles the uevent (symlinks, mkfs hooks). Failure modes are equally explicit: overlap → EINVAL, in-use delete → EBUSY. No filesystem metadata is touched at any point — the kernel learns geometry, nothing more.

### Q: Why does BLKPG exist alongside BLKRRPART when both update kernel partitions?

History and semantics. BLKRRPART is the old whole-table reread: the kernel discards and rebuilds the entire partition set, so any open partition makes it fail with EBUSY — correct but coarse on live systems. BLKPG came from the LVM/RAID world to assert individual entries with explicit geometry, enabling online grow/resize flows where most of the table is valid and busy. partx exposes the per-entry model sensibly (`-a/-d/-u`, `--nr` scoping), leaving whole-table semantics to `blockdev --rereadpt` for cases where a full reset is genuinely wanted.

### Q: What happens to the NAME and UUID columns on an MBR-partitioned disk, and why?

They come out empty: per-partition names and GUIDs are GPT constructs stored in the partition entries themselves; an MBR has only a 32-bit disk signature (which `blkid` reports at disk level, not per partition). Scripts that key off `partx -o NR,UUID` therefore need the GPT path — or PARTUUID-style identification via blkid — and this is one more reason modern provisioning standardizes on GPT. `partx -s -o NR,START,SECTORS,SCHEME` stays meaningful on both schemes.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/partx.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
