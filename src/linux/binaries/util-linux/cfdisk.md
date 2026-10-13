# cfdisk — curses-based interactive partition editor

## Overview

`cfdisk` is a full-screen, menu-driven partition table editor built on
libfdisk: it edits MBR (DOS), GPT, SGI, and SUN disk labels through a
curses interface that works over plain SSH and in rescue environments. It
ships in Debian's `fdisk` package (alongside `fdisk` and `sfdisk`) at
`/usr/sbin/cfdisk` — on bookworm systems it may need
`apt install fdisk`, as the minimal container images often omit the
package.

You reach for it when partitioning interactively: first-time setup of a
disk, fixing a table after a careless `dd`, resizing GPT partitions before
a filesystem grow. It is often confused with `fdisk` (same library,
line-oriented conversation), `sfdisk` (script-driven, dump/replay), and
`parted` (a different project entirely, different semantics — and the only
one of the three families that historically resized filesystems too).

| Field | Value |
| --- | --- |
| Package | fdisk (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/cfdisk |
| First appeared | util-linux lineage, early 1990s (libfdisk rewrite in 2.29, 2016) |
| Standards | GPT and MBR on-disk formats; UEFI spec for GPT layout rules |

## Synopsis

```
cfdisk [options] [device]
```

Main one-line forms:

```
cfdisk /dev/sdb              # edit the disk's partition table
cfdisk -r /dev/sdb           # read-only browse of the current table
cfdisk -z /dev/sdb           # start from an empty in-memory table
cfdisk                       # ask which device to open
```

## How It Works

### The edit-then-write model

`cfdisk` loads the current table into memory and every keystroke only
edits that copy. Nothing touches the disk until you select `Write`:

```
   open device ──► parse table (libfdisk) ──► in-memory model
        │                                          │  UI edits:
        │                                          ▼  New / Delete /
        │                                     recompute geometry,
        │                                     alignment, types, UUIDs
        │                                          │
        └── -z: skip parsing, empty model ◄────────┘
                                                   │  Write (W)
                                                   ▼
                                    commit table to disk (MBR/GPT)
                                                   │
                                                   ▼
                                    ask kernel to rescan partitions
```

After a write, cfdisk instructs the kernel to re-read the table and
displays the resulting partition devices. If partitions are in use the
rescan may fail — the usual `partx -u` follow-up applies.

### The UI, mapped to concepts

```
  Device: /dev/sdb
  Size: 100 GiB, 209715200 sectors, 512 bytes/sector
  Label: gpt, identifier: 9F2A-...

      Device          Start          End   Sectors    Size Type
  >>  Free space      2048    209715166  209713119    100G Free space

  [ New ]  [ Dump ]  [ Delete ]  [ Resize ]  [ Write ]  [ Quit ]
```

- `New` — create a partition in the selected free space; asks for size
  (accepts `+20G` style), then for GPT asks the type (Linux fs, EFI
  System, swap, ...).
- `Delete` / `Resize` — operate on the in-memory model; Resize on GPT
  only moves the end (start stays), which is why filesystem growing works
  cleanly afterwards.
- `Dump` — print the table in `sfdisk` script format, the hand-off point
  to scripted tooling.
- `Write` — the only destructive moment; requires typing `yes`.

### Alignment and the free-space rows

cfdisk aligns new partitions to 1 MiB (2048 sectors) by default and
applies GPT alignment rules automatically; `Free space` rows show gaps you
can partition. For GPT it manages the protective MBR, the backup header at
the disk end, and partition UUIDs without user input.

## Options That Matter

| Option | Effect |
| --- | --- |
| `[device]` | Disk to edit; interactive picker when omitted |
| `-r, --read-only` | Browse the table, disable all destructive actions |
| `-z, --zero` | Ignore the on-disk table; start with an empty in-memory one |
| `-L, --color[=<when>]` | Colorize output (`auto`/`never`/`always`) |
| `-h, --help` | Usage |
| `-V, --version` | Version |

`-z` is the rescue feature for a destroyed or foreign table: you define
the layout from scratch and write it, leaving the old bytes irrelevant.
Upstream releases newer than bookworm add sector-size overrides and
extra locking options; the three flags above are the stable core.

## Usage Patterns

```bash
# First-time partitioning of a new disk, 1MiB-aligned GPT
cfdisk /dev/sdb          # New -> 100G -> Linux filesystem -> Write -> yes
```

```bash
# Look at a table without any risk of writing
cfdisk -r /dev/sdb
```

```bash
# Table destroyed by a bad dd: rebuild from scratch
cfdisk -z /dev/sdb       # create ESP + root as needed, then Write
```

```bash
# Script the same layout instead (sfdisk consumes the Dump format)
cfdisk -r /dev/sdb       # use Dump to get the starting point
sfdisk /dev/sdb <<'EOF'
label: gpt
start=2048, size=1048576, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=1050624, size=208663296, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4
EOF
```

```bash
# Grow a GPT partition after enlarging the underlying volume
cfdisk /dev/vdb          # select partition -> Resize -> accept new end -> Write
# then, inside the OS:
partx -u /dev/vdb && resize2fs /dev/vdb1
```

```bash
# Create an EFI System Partition before installing a bootloader
cfdisk /dev/nvme0n1      # New -> 512M -> EFI System -> Write
```

```bash
# Non-interactive checks before/after the interactive session
blkid /dev/sdb1          # signature probe of what you just created
```

```bash
# Give the kernel the new partition if its rescan was refused
partx -a /dev/sdb
```

## Nuances and Gotchas

- **Delete + Write is the classic footgun.** Deleting a partition row does
  not erase data, but writing a smaller overlapping partition on top of an
  old filesystem produces silent corruption. Repartition from Free space,
  not on top of existing partitions, unless you intend to.
- **GPT only moves partition ends.** `Resize` cannot move a partition's
  start; moving data requires backup/restore or btrfs/LVM-level tools.
  On MBR the story is worse: geometry changes are free-form and
  data-destroying.
- **The kernel rescan can silently fail.** Busy partitions block the
  reread; cfdisk shows a warning that is easy to miss over SSH. Always
  verify with `lsblk`/`cat /proc/partitions` and `partx -u` if needed.
- **It writes tables, not filesystems.** Creating a "Linux filesystem"
  partition gives you a range, not an ext4 — `mkfs` (or `wipefs` first, if
  reusing) is a separate step.
- **MBR limits.** Four primary partitions (or 3 + extended), 2 TiB
  ceiling; cfdisk will happily create extended/logical partitions, but new
  work belongs on GPT except for legacy boot media.
- **Terminals.** Needs a reasonable terminfo; over weird serial consoles
  the UI may render unusably — `sfdisk` is the fallback that never needs
  curses.
- **Package presence.** Minimal cloud/container images often lack the
  `fdisk` package; `apt install fdisk` before reaching for cfdisk in a
  rescue shell.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Session ended normally (including Quit without Write) |
| 1 | Cannot open device, libfdisk error, failed write, or terminal failure |

## Related Commands

- [`addpart`](./addpart.md) — teach the kernel one partition entry without a table write
- [`blockdev`](./blockdev.md) — `--rereadpt`, size and sector-size checks around the edit
- [`blkid`](./blkid.md) — probe what the new partitions contain before formatting
- [util-linux overview](./overview.md) — the disk-tools family: fdisk, sfdisk, partx

## Interview Questions

### Q: Compare cfdisk, fdisk, and sfdisk — when is each the right tool?

All three are libfdisk frontends over the same model. `cfdisk` is
interactive curses — best for humans at a console. `fdisk` is a
line-oriented dialogue — scriptable with heredocs but archaic. `sfdisk`
is dump/replay: `sfdisk -d` exports a table as a script, `sfdisk` applies
it, making it the provisioning and automation choice. Rescue environments
often have all three; pick by operator, not capability.

### Q: You enlarged a VM disk. Walk through resizing the last GPT partition and its filesystem.

In cfdisk, select the partition and Resize to the new end — GPT edits the
end only, so no data moves. Write, then update the kernel's view
(`partx -u`). Finally grow the filesystem online (`resize2fs` for ext4,
`xfs_growfs` for XFS). The interview point: the table edit, the kernel
view, and the filesystem are three separate layers that each need an
explicit step.

### Q: What does cfdisk -z do and when would you use it?

It skips parsing the on-disk table and starts from an empty in-memory
model — for a destroyed/foreign table or when you want a clean layout
uninfluenced by what is there. The on-disk table is only replaced when
you Write. It is also the standard recipe for a disk with a corrupt GPT
backup header that would otherwise make libfdisk refuse to edit.

### Q: Why is a partition created in cfdisk not usable until you also run mkfs?

cfdisk manipulates the partition table: it defines address ranges and
type GUIDs. A filesystem is a data structure living inside that range;
until `mkfs` writes its superblock, `blkid` sees no signature and no
filesystem can mount the device. Conversely, `wipefs` removes that
signature without touching the table — the two layers are independent.

### Q: How does cfdisk prevent the classic misaligned-partition performance problem?

It aligns new partitions to 1 MiB (2048 sectors) by default and follows
the device's topology (minimum/optimal I/O sizes) rather than the CHS
notions of the 1990s. This is why every modern table starts the first
partition at sector 2048 — matching SSD erase blocks and 4Kn geometries —
and why manually typing `1` as a start sector is a red flag.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/fdisk/cfdisk.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
