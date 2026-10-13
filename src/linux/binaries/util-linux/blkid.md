# blkid — locate and print block device attributes (UUID, LABEL, TYPE)

## Overview

`blkid` is the command-line face of libblkid, the util-linux library that
probes block devices and identifies what is on them: filesystem type,
filesystem UUID and label, swap signature, RAID superblock, partition-table
kind, and the per-partition PARTUUID/PARTLABEL from GPT. Debian ships it in
the `util-linux` package at `/usr/sbin/blkid`. It is the tool behind many
`/dev/disk/by-uuid/` and `/dev/disk/by-label/` symlinks you see populated at
boot (via udev's use of the same library).

You reach for it to answer "which device is this filesystem?", to resolve a
UUID from `fstab` into a device name, to script device discovery (`-o
export` gives shell-sourceable output), and to debug why the kernel's view
of a disk differs from what you expect. It is often confused with `lsblk -f`
(presentation-oriented tree of the same metadata), `findmnt` (mount-point
oriented), `wipefs` (removes the signatures blkid detects), and `udevadm
info` (the udev database view of the same probe results).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/blkid |
| First appeared | util-linux 2.15 era (replaced the separate libblkid binary) |
| Standards | Reads superblock formats (ext, xfs, btrfs, GPT, ...), not POSIX |

## Synopsis

```
blkid --label <label> | --uuid <uuid>

blkid [--cache-file <file>] [-ghlLv] [--output <format>] [--match-tag <tag>]
      [--match-token <token>] [<device> ...]

blkid -p [--match-tag <tag>] [--offset <offset>] [--size <size>]
       [--output <format>] <device> ...

blkid -i [--output <format>] <device> ...
```

The three chunks are distinct modes: token lookup, the default cached
listing, and the two explicit scan modes (`-p` low-level probe, `-i` I/O
information).

## How It Works

### Probing in one picture

```
          /dev/sda1
              │ read superblock / header magic at known offsets
              ▼
   ┌───────────────────────┐
   │ libblkid probe chain  │   ext superblock @1024+56:  magic 0xEF53
   │  (superblocks.o)      │   xfs  magic "XFSB" @0
   │                       │   swap "SWAP-SPACE" @pagesize-10
   │  + partitions.o       │   GPT header "EFI PART" @LBA1
   └───────────┬───────────┘
               │ tags: TYPE=, UUID=, LABEL=,
               │       PARTUUID=, PARTLABEL=, USAGE=
               ▼
   output formats: full | value | device | export | json
```

The library knows the magic numbers and layout of every supported
filesystem, RAID, and partition-table format, probes *read-only*, and
emits NAME=value tags. `blkid` adds the parts applications actually need:
a cache, output formatting, and token→device search.

### The cache

Without `-p`, results come from (and update) a cache file,
`/run/blkid/blkid.tab` on Debian — a memory-only tmpfs that root maintains.
This is why plain `blkid` is instant even on a box with dozens of disks:

```
$ blkid                                    # default: cached, all devices
/dev/sda1: UUID="d7b0c9e2-..." TYPE="ext4" PARTUUID="2e21c509-01"
/dev/sda2: UUID="a1b2c3d4-..." TYPE="swap" PARTUUID="2e21c509-02"

$ blkid -c /dev/null /dev/sdb1             # bypass cache, probe live
/dev/sdb1: UUID="2023-07-01-11-22-33-00" TYPE="vfat" PARTLABEL="EFI"
```

Bypassing the cache is mandatory whenever you have just created or changed
a filesystem — a freshly `mkfs`-ed device is in no cache yet. The two
lookup shortcuts always search uncached when given a device explicitly,
and search the cache when not.

### Output formats

```
$ blkid -o full /dev/sda1        # default, NAME="value" pairs per line
$ blkid -o device /dev/sda?      # just the device path(s)
/dev/sda1
$ blkid -o value -s UUID /dev/sda1
d7b0c9e2-4a1b-4f8e-9c2d-6f5e4d3c2b1a
$ blkid -o export /dev/sda1      # shell-sourceable, no quoting
DEVNAME=/dev/sda1
UUID=d7b0c9e2-4a1b-4f8e-9c2d-6f5e4d3c2b1a
TYPE=ext4
PARTUUID=2e21c509-01
$ blkid -o json /dev/sda1        # machine-readable (util-linux >= 2.36)
```

`export` is the format to `eval` in scripts; `json` for anything modern.
The old `-o list` human table still works but is deprecated.

### Token search

```
$ blkid -L mydata               # LABEL= lookup -> device (exit 2 if absent)
/dev/sdb1
$ blkid -U 1234-abcd            # UUID lookup (case-insensitive)
/dev/sdc1
$ blkid -t TYPE=swap -o device  # arbitrary NAME=value token search
/dev/sda2
```

`-l` restricts a token search to the first match, which matters when two
devices share a label (copied filesystems).

## Options That Matter

| Option | Effect |
| --- | --- |
| `<device>...` | Probe only these devices instead of the whole system |
| `-p, --probe` | Low-level mode: bypass cache and udev, deep superblock probing |
| `-i, --info` | Print I/O limits (sector sizes, minimum/optimal I/O) instead of signatures |
| `-o, --output <fmt>` | `full`, `device`, `value`, `export`, `json` (default `full`) |
| `-s, --match-tag <tag>` | Show only this tag; repeatable (`-s TYPE -s UUID`) |
| `-t, --match-token NAME=val` | Search devices for a matching tag |
| `-l, --list-one` | With `-t`: return only the first matching device |
| `-L, --label <label>` | Shorthand: resolve a filesystem LABEL to a device |
| `-U, --uuid <uuid>` | Shorthand: resolve a filesystem UUID to a device |
| `-c, --cache-file <file>` | Use another cache; `/dev/null` disables caching |
| `-g, --garbage-collect` | Remove non-existent devices from the cache |
| `-k, --list-filesystems` | List all known filesystems/RAIDs libblkid can detect, then exit |
| `-d, --no-encoding` | Do not escape non-printing characters in values |

## Usage Patterns

```bash
# Inventory every device with a signature
blkid
```

```bash
# fstab debugging: which device is UUID=... pointing at today?
blkid -U $(awk '$2=="/data" {print $1; exit}' /etc/fstab | sed 's/UUID=//')
```

```bash
# Source the tags of a device into the shell
eval "$(blkid -o export /dev/sdb1)"
echo "$TYPE $UUID"
```

```bash
# Find all swap devices, ready for swapon (pipe to xargs)
blkid -o device -t TYPE=swap | xargs -r -n1 swapon
```

```bash
# Fresh mkfs not visible yet? Probe without the cache
mkfs.ext4 -L data /dev/sdb1
blkid -p /dev/sdb1
```

```bash
# Only the UUID, no decoration (assignment-friendly)
uuid=$(blkid -s UUID -o value /dev/sdb1)
```

```bash
# What can this build of libblkid detect?
blkid -k | column -c 80
```

```bash
# Hardware sanity check: I/O limits of an NVMe namespace
blkid -i /dev/nvme0n1
```

```bash
# Script guard: does the disk have anything on it before we partition?
if blkid -p /dev/sdc >/dev/null 2>&1; then echo "signatures present"; fi
```

```bash
# Duplicate-label hunt (cloned disks): all devices with the same LABEL
blkid -t LABEL=data -o device
```

## Nuances and Gotchas

- **The cache lies after changes.** Plain `blkid` reports the last cached
  probe; a new `mkfs` or `wipefs` will not show up until a fresh probe
  (`blkid -p`, explicit device argument, or `-c /dev/null`). Non-root users
  get the cache read-only and cannot update it.
- **Exit code 2 means "not found" — on purpose.** `blkid -U <uuid>` exits 0
  with a device on match and 2 on no match, making `blkid -U x >/dev/null`
  a clean boolean in scripts. Any other failure (permissions, probe error)
  is a different nonzero path.
- **PARTUUID/PARTLABEL come from the partition table, not the filesystem.**
  They exist for GPT disks (and reflect the table, surviving `mkfs`). An
  MBR partition has no stable PARTUUID in this sense; `blkid` reports it
  only when the table type provides one.
- **Permissions.** Unprivileged probing requires readable device nodes —
  typically root or a `disk` group member. In containers, missing device
  nodes make `blkid` return nothing at all, which is not an error.
- **`-o export` values are unquoted.** If a label contains spaces or shell
  metacharacters, the `NAME=value` lines must still be parsed as
  assignments; libblkid escapes control characters (disable with `-d`), but
  labels with spaces are legal and will happily bite naive parsers.
- **RAID and LVM signatures.** blkid reports TYPE like
  `linux_raid_member` or `LVM2_member` for member devices — these are not
  mountable directly, and tools keyed on `TYPE=` filtering need to expect
  them.
- **lsblk vs blkid.** `lsblk -f` shows the same filesystem tags in a tree
  plus mountpoints; `blkid` remains the scriptable one and the one with
  low-level `-p` semantics.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Requested information found and printed |
| 2 | The requested device, label, UUID, or token was not found |
| 4 | (Probe error paths) probing failed for other reasons — usage, permissions, I/O |

## Related Commands

- [`blockdev`](./blockdev.md) — device geometry/limits from the kernel side; blkid's `-i` shows the same family of values
- [`addpart`](./addpart.md) — entries it creates have no PARTUUID; blkid is how you check that
- [`cfdisk`](./cfdisk.md) — writes partition tables whose PARTUUIDs blkid later reports
- [`../../shell/xargs.md`](../../shell/xargs.md) — piping `blkid -o device` results into commands safely
- [util-linux overview](./overview.md) — the rest of the disk/filesystem toolset

## Interview Questions

### Q: What is the difference between filesystem UUID, PARTUUID, and the label?

Filesystem UUID/LABEL live inside the filesystem superblock and change
whenever you reformat or `dd` the filesystem elsewhere. PARTUUID/PARTLABEL
live in the partition table (GPT) and identify the *range*, surviving
reformats. fstab entries choose accordingly: `UUID=` follows the data, and
`PARTUUID=` follows the partition slot. MBR has no meaningful PARTUUID,
which is why old disks could not use that fstab style.

### Q: Why does `blkid` show nothing right after `mkfs` on a new partition, and how do you fix it?

Plain `blkid` reads its cache, which was populated by earlier scans and
never saw the new superblock. Run a real probe against the device —
`blkid -p /dev/sdb1` or `blkid -c /dev/null /dev/sdb1` — or trigger the
udev/system rescan. The general lesson: blkid's default mode answers from
a cache; only explicit probing is guaranteed current.

### Q: How would you write a script that unconditionally swaps on every swap-formatted partition?

`blkid -o device -t TYPE=swap | xargs -r -n1 swapon`. The key details: `-o
device` yields one clean path per line; `-t TYPE=swap` filters by probed
signature; `-r` on xargs avoids running `swapon` with no arguments when the
list is empty. Using `-o export` parsing instead would be overkill and
quoting-fragile for this task.

### Q: Explain why `blkid -U <uuid>` is a better existence test than grepping output.

The exit status is the interface: 0 on found, 2 on not-found, independent
of output formatting which has changed across versions. Grepping the
default format couples you to quoting and column changes; the exit code is
a stable contract and avoids parsing entirely.

### Q: What does the -p (low-level probe) mode change semantically?

It bypasses both the cache and any udev-provided results and performs a
direct, deep probe of the device: reading superblocks at multiple
offsets, tolerating/ignoring cache state, and optionally probing at a
given offset/size. It is the mode to use in filesystem-creation tools and
recovery scripts where answers must reflect the bytes on disk *right now*.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/blkid.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
