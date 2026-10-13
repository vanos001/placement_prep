# sfdisk — scriptable partition table editor

## Overview

`sfdisk` is the non-interactive, script-driven partition editor of the
util-linux family. It creates, dumps, verifies, clones and modifies MBR
(DOS) and GPT partition tables from the command line or from a stdin
script, and it is the tool of choice whenever layouts must be reproduced
or changed without a human at a prompt — provisioning, golden images,
recovery. It ships in the `fdisk` package (Debian bookworm) at
`/usr/sbin/sfdisk`.

`sfdisk` is often confused with `fdisk` (the interactive sibling: same
libfdisk core, conversational UI), with `cfdisk` (curses UI), and with
`parted` (a separate GNU project with its own script format and
`parted -s` mode). Within util-linux the division of labor is: `sfdisk`
automates, `fdisk`/`cfdisk` put a human in the loop.

| Field | Value |
| --- | --- |
| Package | fdisk (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/sfdisk |
| First appeared / lineage | classic util-linux tool; rewritten on libfdisk for util-linux 2.26 (2015) |
| Standards | None — Linux/PC MBR and GPT specific |

## Synopsis

```
sfdisk [options] <device> [<partition>...]
sfdisk [options] -d <device>          # dump layout as a script
sfdisk [options] -l <device>          # human-readable listing
sfdisk <device> < layout.script       # apply a script to the device
```

Common one-line forms:

```
sfdisk -d /dev/sda > layout.txt       # backup a layout
sfdisk /dev/sdb < layout.txt          # clone it onto another disk
sfdisk -F /dev/sda                    # show unallocated space
sfdisk -V /dev/sda                    # verify table consistency
```

## How It Works

### The script format

Feeding `sfdisk <device>` from stdin (or a redirected file) replaces the
partition table with what the script describes. Each line defines one
partition as comma-separated `key=value` fields:

```
# fields (any may be omitted; sensible defaults are applied)
start=2048, size=512M, type=83, bootable
       size=2G,  type=82
                 type=8e
```

- `start=` in 512-byte sectors (default: first aligned free sector).
- `size=` in sectors, or with `K`/`M`/`G` suffixes; omitted size means
  "the rest".
- `type=` is the partition type — MBR hex codes (`83` Linux, `82` swap,
  `8e` LVM, `c12a7328-f1f2-...`-style GUIDs or shorthands on GPT).
- `bootable` sets the MBR boot flag; GPT uses `attrs=` for attribute
  bits and `uuid=`/`name=` for partition UUID/label.

An empty script (`echo | sfdisk /dev/sdX`) wipes the table; a script
with fewer entries than before deletes the leftovers. Everything goes
through libfdisk, the same engine behind `fdisk` and `cfdisk`, so
alignment rules (1 MiB default), label detection and GPT details match
across the family.

```
 script on stdin ──► libfdisk parser ──► label backend (dos | gpt | ...)
        │                                    │
        │                          wipe signatures (--wipe)
        │                                    │
        ▼                                    ▼
 -n dry run prints the plan      write table → re-read kernel
                                  (BLKRRPART / partx update)
```

### Reading: dump, list, free space

`-d` prints the table *as a valid sfdisk script* — the canonical way to
back up and clone layouts. `-l` prints a human-oriented listing, `-F`
reports unpartitioned gaps (the quick sanity check before growing a
partition), and `-J` emits JSON for programs. `-T` lists the type codes
the current build knows.

### Changes take two steps: disk, then kernel

Writing the sectors is only half the job; the kernel keeps its own
in-memory copy of partitions. `sfdisk` triggers the re-read
(`BLKRRPART`, or a `partx` update on devices that cannot be re-read
whole). If any partition of the disk is mounted, the re-read may refuse
or produce stale sizes until the holder releases it — the reason resize
procedures say "unmount, resize, `partprobe`".

## Options That Matter

| Option | Effect |
| --- | --- |
| `-d, --dump` | Dump the table as an sfdisk script (backup/clone format). |
| `-l, --list` | Human-readable listing of partitions. |
| `-F, --list-free` | Show unpartitioned space on the device. |
| `-V, --verify` | Check the table for inconsistencies (overlaps, geometry). |
| `-n, --no-act` | Parse and plan everything, write nothing. |
| `-f, --force` | Override refusals (e.g. mounted-volume heuristics). |
| `-N, --partno <n>` | Restrict an operation (script, activate) to partition *n*. |
| `--delete <partno>...` | Remove the listed partitions from the table. |
| `-a, --append` | Do not truncate the existing table; append new partitions. |
| `-A, --activate <dev> [<partno>...]` | Toggle the bootable flag (MBR) / legacy-boot attribute (GPT). |
| `-b, --backup` / `-O, --backup-file <f>` | Back up the sectors about to be modified (default file `sfdisk-<device>.bak`). |
| `-B, --move-data[=<path>]` | When resizing, physically move data into newly available space (slow, offline). |
| `-X, --label <name>` | Create this label type (`dos`, `gpt`, ...). |
| `-Y, --label-nested <name>` | Create a nested label (e.g. GPT inside MBR). |
| `-w, --wipe <when>` | Control signature wiping (`auto`, `always`, `never`). |
| `-o, --output <cols>` | Column selection for `-l`/`-d`-style output. |
| `-J, --json` | Machine-readable dump. |
| `-q, --quiet` | Suppress informational messages. |

## Usage Patterns

```bash
# Back up a disk layout before touching it (root)
sfdisk -d /dev/sda > /root/sda.layout.txt
```

```bash
# Clone the exact layout onto a replacement disk of equal or larger size
sfdisk /dev/sdb < /root/sda.layout.txt
```

```bash
# Create a fresh GPT with three partitions from a script (root)
cat <<'EOF' | sfdisk /dev/sdb
label: gpt
start=0, size=512M, type=uefi
       size=4G,   type=swap
                  type=linux
EOF
```

```bash
# Preview what a script would do, without writing anything
sfdisk -n /dev/sdb < layout.txt
```

```bash
# Grow the last partition to fill the disk after a VM disk expansion
echo ", +" | sfdisk -N 3 /dev/sdb
partx -u /dev/sdb    # then resize the filesystem on top
```

```bash
# Delete partition 2 and list the resulting free gap
sfdisk --delete /dev/sdb 2
sfdisk -F /dev/sdb
```

```bash
# Mark a partition bootable (MBR flag; legacy-boot attribute on GPT)
sfdisk -A /dev/sdb 1
```

```bash
# Verify a suspect table before trusting a rescue
sfdisk -V /dev/sdc
```

```bash
# JSON dump for an inventory script
sfdisk -J /dev/sda
```

```bash
# Keep a sector-level backup of whatever you are about to overwrite
sfdisk -b -O /root/sdb-sectors.bak /dev/sdb < layout.txt
```

```bash
# Append one Linux partition using all remaining space, no wipe prompts
echo 'type=linux' | sfdisk --append -w always /dev/sdb
```

## Nuances and Gotchas

- **Instantly destructive.** Applying a script rewrites the table; old
  partitions and their start points are forgotten. Take `-d` output or a
  `-b`/`-O` sector backup first — the file is small and the regret is
  not.
- **Pre-2.26 syntax is gone.** The 2015 libfdisk rewrite removed the old
  unit/type options (`-u`, `-t`, `-s`, multi-command stdin sessions).
  Decade-old tutorials and docs produce parse errors on modern sfdisk;
  the script format (`start=, size=, type=`) is the current language.
- **Units are 512-byte sectors** in `-N` contexts and script `start=`
  fields even on 4Kn drives; prefer `size=` with `M`/`G` suffixes to
  avoid mental arithmetic.
- **`-A` means different bits on different labels.** On MBR it toggles
  the bootable flag; on GPT it toggles the *legacy BIOS bootable*
  attribute — it is not the ESP flag, and bootloaders that read GPT
  attributes differ.
- **Kernel view vs disk view.** sfdisk re-reads the table, but mounted
  partitions pin the old geometry; if sizes look stale, `partx -u` or a
  reboot finishes the update.
- **Wiping is a feature and a hazard.** `--wipe=auto` (default) clears
  stale filesystem/LVM signatures from newly defined partition areas; on
  recovery jobs use `--wipe=never` to preserve evidence.
- **`--move-data` is a convenience, not a backup strategy.** It copies
  data blocks when a resize relocates content — offline, slow, and a
  bad place to discover a failing disk.
- **Alignment defaults to 1 MiB** (2048 sectors) so partitions are safe
  for SSD erase blocks and old CHS expectations; hand-picked `start=`
  values can undo that.
- **Reading is cheap, writing needs root.** `-d`/`-l`/`-F`/`-V` work
  with read access to the node; only script application, `--delete` and
  `-A` need root.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | The requested operation completed (including successful `-n` dry runs). |
| non-zero | Any failure: parse error in the script, refused unsafe write without `--force`, device not writable, verify failures with `-V`. |

The man page documents no per-failure code table; script against 0 vs
non-zero and capture stderr for the reason.

## Related Commands

- [`fdisk`](./fdisk.md) — the interactive sibling over the same libfdisk engine.
- [`cfdisk`](./cfdisk.md) — curses UI for the same operations.
- [`partx`](./partx.md) — tell the kernel about table changes; the finish line of every sfdisk edit.
- [`resizepart`](./resizepart.md) — grow/shrink a partition in the kernel's view after table edits.
- [`blockdev`](./blockdev.md) — `--rereadpt` and friends for the disk/kernel sync step.
- [`mkswap`](./mkswap.md) — format the swap partitions your scripts create (type `82`/swap).
- [`lsblk`](./lsblk.md) — verify the resulting tree of devices and sizes.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: How do you replicate one disk's partition layout onto another disk, and what can go wrong?

`sfdisk -d /dev/sda > layout.txt; sfdisk /dev/sdb < layout.txt`. The
script preserves start/size/type, so it works only if the target is at
least as large; on a smaller target, writes fail or truncate. GPT also
stores a disk UUID, so two disks with cloned tables share identifiers
until you regenerate them — fine for mirror targets, confusing for
inventory tools. Finally the kernel must re-read the table on the target
before its partitions appear with correct sizes.

### Q: Explain the difference between sfdisk, fdisk and parted.

sfdisk and fdisk share util-linux's libfdisk core and semantics; they
differ in interface — fdisk is conversational, sfdisk takes scripts and
subcommands. parted is GNU software with its own implementation, its own
script mode (`parted -s`) and extra features (filesystem-aware resize
hints). Mixing tools on one disk is fine sequentially but a script mix
must agree on alignment and label type to avoid surprises.

### Q: What does sfdisk -F show and why is it more reliable than eyeballing -l output?

`-F` reports the unpartitioned gaps between and after partitions — the
space a new or grown partition can actually use. `-l` lists partitions
from which free space must be derived by arithmetic, including alignment
holes; `-F` gives the authoritative answer before you write a `start=`
value.

### Q: A VM's disk was grown from 10G to 20G. Walk through making the extra space usable.

Identify the last partition (`lsblk`); grow its table entry — for
GPT/MBR, recreate it with the same start and size `+` (or
`sfdisk --delete` + append, or grow with `echo ',+' | sfdisk -N n`);
update the kernel view (`partx -u` or `partprobe` — the filesystem must
not be mounted for a size change on most setups); then resize the
filesystem (`resize2fs`, `xfs_growfs`) or the PV (`pvresize`). The table
edit, kernel re-read and filesystem resize are three distinct layers.

### Q: Why did the 2015 rewrite matter for existing scripts?

util-linux 2.26 replaced the old sfdisk engine with libfdisk and dropped
legacy command-line forms (unit selection, the old multi-line prompt
protocol). Scripts written against 1990s sfdisk syntax fail to parse;
the portable form is the modern script format (`start=, size=, type=`)
plus explicit flags like `--append` and `-N`. Recognizing pre-2.26
examples in documentation is a practical skill.

### Q: What does --wipe do and when would you turn it off?

When defining a new partition area, sfdisk can erase stale signatures
(leftover filesystem/LVM/RAID headers) so the kernel does not
accidentally recognize old content. `auto` (default) wipes only where it
looks safe; `always`/`never` force the behavior. On forensics or
recovery you choose `--wipe=never` — wiping the RAID superblock you were
about to analyze is an unrecoverable mistake.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/fdisk/sfdisk.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
