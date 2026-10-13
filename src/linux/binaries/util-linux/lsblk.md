# lsblk — list block devices

## Overview

`lsblk` lists all block devices — disks, partitions, LVM volumes, RAID members, loop devices, NVMe namespaces, CD drives — as a tree showing how they nest (`disk → part`, `disk → lvm → filesystems`). It reads the kernel's sysfs topology and, for filesystem metadata, udev's hardware database (and `blkid`-style probing with `-f`). Default output is a compact tree; column selection makes it a structured probe for scripts. Ships in the `util-linux` package (Debian bookworm) at `/usr/bin/lsblk`.

Reach for it as the first command on any box: "what storage do we have, what is mounted where, which UUID belongs to which partition?" It is often confused with `blkid` (filesystem *metadata* probing: TYPE/UUID/LABEL — heavier, cache-backed), `fdisk -l` (partition tables, needs root for full detail), `df` (mounted filesystem usage), and `findmnt` (mount tree). `lsblk` shows *devices*, mounted or not — which is why it sees swap partitions, unmounted volumes, and fresh disks that `df` cannot show.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/lsblk |
| First appeared | util-linux addition (early 2010s) |
| Standards | None (Linux sysfs/udev; no command standard) |

## Synopsis

```
lsblk [options] [<device>...]
```

Common one-line forms:

```
lsblk                       # tree of all block devices
lsblk -f                    # + filesystem type, UUID, label
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
lsblk -J -o NAME,SIZE,TYPE  # JSON for scripts
```

## How It Works

### Data sources

`lsblk` assembles its rows from three places:

1. **sysfs** (`/sys/class/block/`) — device existence, parent/child topology (`holders`/`slaves` links), sizes, read-only, removable flags. Always available, even in a bare initramfs.
2. **udev database** (`/dev/disk/by-*` symlinks, udev property DB) — model, serial, WWN, filesystem labels where udev already probed them.
3. **blkid probing** — when you ask for columns udev has not filled (explicit `FSTYPE`/`UUID` requests on odd devices), lsblk reads superblocks directly.

Implication: `lsblk` works without root (sysfs is world-readable) but some columns can be empty when udev data is missing (chroot, minimal rescue environments, right after a device was created before udev settled).

### The default tree

```bash
$ lsblk
NAME      MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
zram0     253:0    0    0B  0 disk
vda       254:0    0   10G  0 disk
pmem0     259:0    0  384M  0 disk
└─pmem0p1 259:1    0  383M  0 part
```

- **NAME** — kernel name, indented by topology (`└─` = child of the row above).
- **MAJ:MIN** — kernel device numbers; `-e`/`-I` filter on them.
- **RM** — removable; **RO** — read-only; **TYPE** — `disk`, `part`, `lvm`, `crypt`, `loop`, `rom`, `md`, `raid…`.
- **MOUNTPOINTS** — every mountpoint (a btrfs with multiple subvolume mounts repeats the device per mount).

### Column selection is the real interface

```bash
$ lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS
```

Column names match sysfs/udev concepts: `MODEL`, `SERIAL`, `WWN`, `STATE`, `ALIGNMENT`, `ROTA` (rotational flag), `DISC-GRAN`/`DISC-MAX` (trim capability), `PKNAME` (parent kernel name), `PATH` (full /dev path), `PARTLABEL`/`PARTUUID` (GPT). The exact set varies by version; `lsblk --help` ends with the available-columns list of the installed build. Scripts prefer JSON or raw over screen formatting:

```bash
lsblk -J -o NAME,SIZE,TYPE,MOUNTPOINTS
lsblk -n -r -o NAME,SIZE        # raw rows, no tree decorations
```

### Device views

`-S` lists SCSI devices (`/dev/sd*`) with vendor/model; `-N` lists NVMe controllers and namespaces; `-d --nodeps` drops children (one row per device — the fast, clean inventory); `-s --inverse` flips the tree to answer "this partition hangs off what?" from the bottom; `-a` includes devices with no media (empty card readers, detached-but-reserved).

### The stacked-device graph: slaves and holders

The tree is not cosmetic — it is read directly from sysfs: each block device exposes `slaves/` (devices feeding it) and `holders/` (devices consuming it). A typical LUKS-on-partition stack as lsblk renders it (top-down, `-s` shows the same chain bottom-up):

```
nvme0n1p2      part   LUKS2
└─luks-root    crypt  dm-crypt target (slave: nvme0n1p2)
  └─vg0-root   lvm    LVM2_member (slave: luks-root)
    └─(fs mounted at /)
```

Every dm-crypt target and LVM logical volume is a block device with its physical backing listed under `slaves`; md arrays, btrfs multi-device pools, and loop files appear the same way. `-s` follows holders upward, `-d` prunes the view downward, and the parent/child arrows in default output are just this graph drawn from the root. Scripts that must answer "which physical disks back this logical volume?" are querying exactly this sysfs graph, whether through lsblk or by walking `/sys/block/*/slaves/*` by hand.

Recent util-linux also exposes `--properties-by` to control the probing order across the three sources above (file, udev, blkid) — useful when udev data is stale and you want lsblk to force its own superblock reads. `lsblk -H/--list-columns` prints the column vocabulary of the installed build, which is the authoritative answer to "what can go in `-o`".

Where each kind of information physically comes from:

```
column family        source             example
NAME/SIZE/TYPE/      sysfs files        /sys/class/block/vda/{dev,size}
MAJ:MIN,RO,RM        (always present)
MODEL/SERIAL/WWN     udev property DB   /run/udev/data/b254:0
FSTYPE/UUID/LABEL    udev, else blkid   superblock magic scan of the device
MOUNTPOINTS          /proc/self/mountinfo
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --fs` | Add FSTYPE, FSVER, LABEL, UUID, FSAVAIL, FSUSE% columns |
| `-m, --perms` | Owner/group/mode of the device nodes |
| `-t, --topology` | Alignment, min/max I/O, scheduler, discard geometry |
| `-D, --discard` | TRIM/discard capability columns |
| `-d, --nodeps` | Top-level devices only, no children |
| `-a, --all` | Include empty/unused devices (default hides RAM disks, media-less) |
| `-e, --exclude <majors>` | Filter out device types (default: RAM disks, major 1) |
| `-I, --include <majors>` | Show only these major numbers |
| `-o, --output <list>` | Choose columns (`+COL` appends) |
| `-n, --noheadings` | Drop header row |
| `-r, --raw` | Raw rows, no tree art (parsable) |
| `-J, --json` | JSON output |
| `-p, --paths` | Full `/dev/...` paths instead of kernel names |
| `-x, --sort <col>` | Sort output by a column |
| `-b, --bytes` | Sizes in plain bytes (no KiB rounding) |
| `-S` / `-N` | SCSI view / NVMe view instead of the default tree |

## Usage Patterns

```bash
# First look at any machine: what storage exists and what is mounted
lsblk

# Which filesystem/UUID/label is on each partition?
lsblk -f

# Find the UUID of the root device (fstab debugging)
lsblk -no UUID "$(findmnt -no SOURCE /)"

# Clean inventory: one row per disk, model and serial included
lsblk -d -o NAME,SIZE,ROTA,MODEL,SERIAL

# Script-friendly: raw, bytes, no headers
lsblk -bnr -o NAME,SIZE /dev/vda

# JSON for automation
lsblk -J -o NAME,SIZE,TYPE,MOUNTPOINTS | jq -r '.blockdevices[] | select(.type=="disk") | .name'

# Who uses this device? (is it safe to reformat?)
lsblk /dev/vda

# Show the tree the other way: partition → disk → holder
lsblk -s /dev/dm-0

# NVMe and SCSI device inventories
lsblk -N
lsblk -S -o NAME,MODEL,VENDOR,SIZE,STATE

# Detect SSD/TRIM capability before enabling fstrim
lsblk -D -o NAME,DISC-GRAN,DISC-MAX

# Device node permissions sanity check
lsblk -m
```

```bash
# Append columns to the DEFAULT view: leading + means "add to defaults"
lsblk -o +PARTTYPENAME,PARTUUID

# KNAME vs NAME: dm devices keep their kernel name (dm-0) in KNAME
lsblk -o NAME,KNAME,TYPE,MAJ:MIN

# Filter out snap/docker loop spam on a workstation
lsblk -e 7 -o NAME,SIZE,TYPE,MOUNTPOINTS

# Device-owner view for udev/group debugging (needs udev data; empty in chroots)
lsblk -m -o NAME,OWNER,GROUP,MODE

# GPT partition taxonomy: what each partition claims to be
lsblk -o NAME,PARTTYPENAME,PARTUUID

# Every column the build knows, dumped once for exploration
lsblk -O | head -5
```

## Nuances and Gotchas

- **`MOUNTPOINT` vs `MOUNTPOINTS`.** Recent util-linux renamed the column; `MOUNTPOINTS` repeats a device line per mount (btrfs subvolumes, bind mounts). Scripts expecting the old singular column get surprising row counts — select columns explicitly.
- **Default output hides RAM disks and media-less devices** (excluded by major number). `-a` reveals them; "my loop/zram is missing from lsblk" is usually this filter, or the device is unattached (`losetup -a` territory).
- **Sizes are human-rounded** — `SIZE` shows `10G`-style approximations; for byte-exact comparisons use `-b`. `10G` in lsblk is GiB-graded, not the marketing decimal GB.
- **Empty columns ≠ missing data.** In chroots/rescue shells without udev, MODEL/SERIAL/FSTYPE can be blank; filesystem columns may require blkid probing. Do not conclude "no filesystem" from an empty FSTYPE on exotic setups — verify with `blkid <dev>`.
- **udev lag.** A device created milliseconds ago (fresh loop attach) may lack properties until `udevadm settle`; lsblk reads the current databases, it does not trigger probing.
- **ZFS is invisible.** ZFS volumes are not block devices in sysfs (the pool consumes the disks); you will see the member disks with TYPE `disk` but no ZFS filesystem rows. Same for some software stacks that bypass block-device exports.
- **`-r`/`-J` are the only stable machine formats.** The tree art (`└─`) is for humans; never parse default output.
- **MAJ:MIN filtering** (`-e`, `-I`) is the fastest way to slice device classes (1 = RAM, 7 = loop, 8 = sd, 253/254 = device-mapper/virtio), but major numbers are kernel-dynamic for some drivers — prefer `-S`/`-N`/`-d` for inventories.
- **NAME vs KNAME.** For most devices they coincide, but dm/multipath stacks differ: NAME shows the friendly mapped name, KNAME the kernel's actual node (`dm-0`). Tooling that builds `/dev/...` paths from NAME alone can point at a symlink that doesn't exist on minimal systems; `-p` (PATH) is the column meant for path construction.
- **OWNER/GROUP/MODE come from udev, not the filesystem.** They describe the *device node's* ownership as udev would create it, so they are blank exactly when MODEL/SERIAL are — another chroot/rescue trap. Do not use them to audit file permissions inside a mounted filesystem; use `stat`/`find` on the mountpoint.
- **Filtering loop noise is `-e 7`, not `-a`.** Container-heavy or snap-heavy hosts show dozens of `loopX` rows; `lsblk -e 7` removes them (and `-e 1,7` also drops RAM disks) while keeping real devices — cleaner than piping through grep because it never misfires on names containing "loop".
- **A device with a filesystem but no mount shows an empty MOUNTPOINTS.** That is not an error and not "no filesystem" — it is exactly the case `lsblk -f` exists for. `findmnt`/`df` answer "what is mounted"; lsblk answers "what exists, mounted or not".

## Exit Status

- `0` — listing produced (empty result still exits 0).
- `1` — error: unknown column, unreadable sysfs, invalid device operand, or allocation failure.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`blkid`](./blkid.md) — deep filesystem probing (UUID/TYPE) that `-f` summarizes.
- [`findmnt`](./findmnt.md) — the mount-tree view (what is mounted, with options) vs lsblk's device tree.
- [`fdisk`](./fdisk.md) — partition tables themselves, and where lsblk's `part` rows come from.
- [`losetup`](./losetup.md) — where `loop`-type rows originate and how to clean them up.
- [`blockdev`](./blockdev.md) — raw block-device ioctls (size, reread PT, flush) beneath the listing.
- [`internals`](../../internals.md) — sysfs block topology: slaves, holders, and device numbering.

## Interview Questions

### Q: What is the difference between lsblk, blkid, and df?

`lsblk` lists *block devices* and their topology from sysfs/udev — mounted or not. `blkid` probes *filesystem metadata* on devices (TYPE, UUID, LABEL) and caches it. `df` reports *mounted filesystem usage* (capacity, free space) from the VFS — devices without a mount are invisible to df. Together: `lsblk -f` ≈ device tree + blkid columns; `df` answers "how full", `lsblk` answers "what exists".

### Q: A partition was reformatted, but lsblk still shows the old UUID. Explain and fix.

lsblk consulted udev's cached properties (or blkid cache) that predate the reformat. Fix by letting udev rescan: `udevadm settle`, or `partprobe /dev/vda` / `blockdev --rereadpt` after partition changes, and `blkid <dev>` for the authoritative current superblock. The general lesson: lsblk reports the *databases*, which lag in-flight kernel changes.

### Q: How do you reliably script "the size of /dev/vda in bytes"?

`lsblk -bnr -o SIZE /dev/vda` — `-b` for bytes, `-n` no header, `-r` no tree art. Alternatives: `blockdev --getsize64 /dev/vda`, or reading `/sys/block/vda/size` × 512. Avoid parsing default `lsblk` output (`10G` is rounded) or `df` (filesystem, not device, and only when mounted).

### Q: Why does a btrfs with three subvolume mounts produce multiple rows for one device?

The `MOUNTPOINTS` column lists every mountpoint, and lsblk renders one row per mount for the same device — correct, but breaks line-per-device assumptions. Use `MOUNTPOINT` (singular, first mount) or parse `-J`/`-r` output keyed by device name. It mirrors reality: one block device, many mounted subvolumes.

### Q: You need to know whether it is safe to run fstrim on a device. Which lsblk view answers that?

`lsblk -D` (discard columns: DISC-GRAN/DISC-MAX/DISC-ZERO): non-zero discard geometry means the device/driver supports TRIM (typical SSDs, thin-provisioned virtio); zeros mean no. Also check `ROTA` (rotational) as a hint. Combining `-d -D -o NAME,ROTA,DISC-MAX` gives the quick per-disk verdict before enabling `fstrim.timer`.

### Q: In a minimal rescue initramfs, lsblk shows devices but empty MODEL/SERIAL columns. Why, and what still works?

The udev database is absent or unpopulated in the minimal environment; hardware-identity columns come from udev properties, while topology (NAME, SIZE, TYPE, MAJ:MIN, parents) comes from sysfs — which always works. `FSTYPE`/`UUID` may still appear if lsblk probes the superblock directly. Rely on topology columns for rescue logic; re-derive hardware details after udev starts.

### Q: How does lsblk build its tree for stacked storage, and how would you script "which physical disks back /dev/dm-3?"

The tree is sysfs's graph: each device directory has `slaves/` (what feeds it) and `holders/` (what consumes it); dm-crypt, LVM, md, and btrfs members all appear through these links. `lsblk -s /dev/dm-3` prints the chain bottom-up, and `lsblk -no PKNAME /dev/dm-3` gives the immediate parent — for the full physical set, `lsblk -s -no NAME,TYPE /dev/dm-3 | awk '$2=="disk"'`. It is one open+read of sysfs per link, so the query costs microseconds — the reason inventory scripts prefer it over probing every superblock.

### Q: A colleague parses lsblk's default tree output in a deployment script. What do you change and why?

Default output is a rendering: tree art, truncated/rounded sizes, columns that shifted between releases (MOUNTPOINT → MOUNTPOINTS, repeated rows per mount), and a width that depends on the terminal. Replace it with `lsblk -J` consumed by jq, or `lsblk -rno` for line-oriented values, and request the exact columns. If the script needs udev-only columns (MODEL, SERIAL), add a fallback to sysfs/`-o` columns that exist everywhere, because the column vocabulary differs across util-linux builds — `lsblk -H` lists what the target host actually supports.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/lsblk.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
