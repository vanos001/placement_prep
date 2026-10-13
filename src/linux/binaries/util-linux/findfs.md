# findfs — find a filesystem by label or UUID

## Overview

`findfs` searches the system's block devices for a filesystem or partition
matching a given tag and prints the device name. It understands four tags:
`LABEL=<label>`, `UUID=<uuid>`, `PARTUUID=<uuid>` (partition UUID, e.g. from
GPT), and `PARTLABEL=<label>` (partition name, e.g. GPT's label field). It is
the single-lookup member of the libblkid family: `blkid` prints a table of
*everything* it finds, `lsblk --fs` renders a tree, `findfs` answers exactly
one query and is therefore what fstab-style resolution boils down to.

A small documented quirk makes it double as a no-op: an argument not in
`NAME=value` form is copied to stdout unchanged — a passthrough used by scripts
to accept both UUID tags and plain device paths.

Debian bookworm ships it in the `util-linux` package at `/usr/sbin/findfs`
(man section 8). It was originally written for e2fsprogs (by Theodore Ts'o)
and later reimplemented in util-linux, which is why it shares zero code with
the e2fsprogs `findfs` of the 1990s.

Typical context: debugging `/etc/fstab` entries, writing `mount` wrapper
scripts that accept `UUID=…`, rescue shells where you must locate the root
filesystem manually, and initramfs/boot logic that mounts by identity rather
than by device name (which changes with every hardware reshuffle).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Section (man) | 8 |
| Path | /usr/sbin/findfs |
| Lineage | originally e2fsprogs (T. Ts'o); rewritten in util-linux (2.15, 2009) |
| Standards | None — libblkid probing of on-disk superblocks |

## Synopsis

```
findfs NAME=value
```

The four tag forms:

```
findfs UUID=5f3a...          # filesystem UUID (ext4/xfs/btrfs/…)
findfs LABEL=ROOT            # filesystem label
findfs PARTUUID=1234-abcd    # GPT/MBR partition UUID
findfs PARTLABEL="EFI sys"   # GPT partition name
```

## How It Works

### Probing, not reading config files

`findfs` uses **libblkid** to probe block devices for on-disk superblock
signatures (ext*, xfs, btrfs, vfat, ntfs, swap, LUKS, LVM, …). The scan walks
the devices the kernel knows about, reads each one's identifying sectors, and
matches the requested tag. That means it sees what is *on the media* — not
what udev currently chose to name:

```
            ┌──────────── kernel: /proc/partitions, sysfs ────────────┐
            │  sda   sdb   sdc   nvme0n1 …                            │
            └───────────────────────┬─────────────────────────────────┘
                                    ▼
                 libblkid probes each device's superblock area
                                    ▼
        sdb2: UUID=5f3a-… LABEL=ROOT   PARTUUID=… PARTLABEL="root"
                                    ▼
                 findfs UUID=5f3a-…  ──stdout──►  /dev/sdb2
```

A subtlety worth internalizing: the filesystem-level tags (`UUID`, `LABEL`)
live in the *filesystem superblock*, while `PARTUUID`/`PARTLABEL` live in the
*partition table entry* (GPT). They are independent identifiers that can
disagree — cloning a partition copies the FS UUID but, with `dd`, also the
PARTUUID; with table-aware tools, only the FS UUID.

### Passthrough mode

If the argument is not of the form `NAME=value`, it is echoed unmodified:

```bash
$ findfs /dev/sda2
/dev/sda2
$ findfs hello
hello
```

This is documented behavior, letting one script accept either `UUID=…` strings
or device paths and always end with a usable device argument for `mount`.

### Exit codes are the interface

| Code | Meaning |
| --- | --- |
| 0 | Tag resolved (or passthrough) — device printed on stdout |
| 1 | Label/UUID cannot be found on any device |
| 2 | Usage error — wrong argument count or unknown tag |

Verified on this system:

```bash
$ findfs UUID=not-a-real-uuid-00000000
findfs: unable to resolve 'UUID=not-a-real-uuid-00000000'   # exit 1
$ findfs hello
hello                                                        # exit 0 (passthrough)
```

### Where the resolution also happens elsewhere

The same libblkid logic underlies `mount UUID=…` handling, udev's
`/dev/disk/by-{uuid,label,partuuid,partlabel}` symlinks, and `grub`'s
`search --fs-uuid`. When "the device changed but fstab still works", it is
this identity resolution doing its job — `findfs` merely exposes one query of
it for scripts.

## Options That Matter

`findfs` is nearly option-free — the argument *is* the interface:

| Argument | Effect |
| --- | --- |
| `LABEL=<string>` | Match a filesystem label (case sensitivity depends on the filesystem) |
| `UUID=<uuid>` | Match a filesystem UUID |
| `PARTUUID=<uuid>` | Match a partition-table UUID (MBR id or GPT GUID) |
| `PARTLABEL=<string>` | Match a partition-table label (GPT name; MBR: none) |
| `-h`, `-V` | Help / version |

Beyond that, environment variable `LIBBLKID_DEBUG=all` turns on libblkid
debugging — occasionally the only way to see *why* a probe misses.

## Usage Patterns

```bash
# Resolve a fstab UUID entry to its current device (has the disk moved again?)
findfs UUID=e5ff2a3d-1c9e-4c19-a5b2-8b1d2c4e7f01
```

```bash
# Mount by label in a script that also accepts plain device paths
dev=$(findfs LABEL=BACKUP); mount "$dev" /mnt/backup
```

```bash
# Generic resolver: tag or path both work, passthrough handles paths
mount "$(findfs "$1")" /mnt
```

```bash
# Rescue shell: find the root filesystem when /etc/fstab is unreachable
mount "$(findfs LABEL=rootfs)" /mnt
```

```bash
# Distinguish filesystem identity from partition identity
findfs UUID=... ; findfs PARTUUID=...
```

```bash
# Debug why a probe fails
sudo LIBBLKID_DEBUG=all findfs LABEL=nosuchlabel 2>&1 | tail -20
```

```bash
# Cross-check against the udev view of the same truth
ls -l /dev/disk/by-uuid/ | grep -i "$(findfs UUID=... )"
```

```bash
# Sanity-check a clone: duplicate UUIDs make findfs return an arbitrary match
findfs UUID=e5ff2a3d-... ; blkid | grep e5ff2a3d
```

## Nuances and Gotchas

- **Duplicate UUIDs are legal and findfs picks one.** Cloned disks, LVM
  snapshots copied with `dd`, or restored images can present the same
  filesystem UUID on two devices; the resolution order is not a stable API.
  Run `blkid` to see all matches and fix the duplicate (tune2fs/xfs_admin,
  or wiper the clone's signature with `wipefs`).
- **Unprivileged probing may fail.** Reading superblocks requires read access
  to the device nodes; a non-root user outside the `disk` group typically gets
  nothing (or a warning), not a graceful answer. Scripts should run it with
  the privileges they will use for the mount anyway.
- **`UUID=` strings are filesystem-specific in format.** FAT/exFAT print short
  UUIDs (`5F3A-1C9E`), ext/xfs/btrfs print full hyphenated UUIDs. Copy them
  verbatim from `blkid`/`lsblk -f`; hand-typing them is an error source.
- **PARTUUID ≠ UUID.** Re-partitioning (fdisk/sfdisk) regenerates PARTUUIDs
  while the filesystem UUID survives; re-formatting (mkfs) does the reverse —
  unless `mkfs -U` pins the UUID. fstab mixes both styles, so debugging "why
  did the root device change" requires knowing which identity the entry uses.
- **Labels are not unique either.** Two "BACKUP" labels coexist happily;
  findfs will match one of them. Identity tags are conveniences, not unique
  keys — uniqueness is a deployment discipline.
- **Passthrough is easy to misuse.** `findfs "$X"` with an unset/typo variable
  happily echoes garbage; validate that output looks like a device before
  mounting it.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Found (or passthrough); device path on stdout |
| 1 | No device with that label/UUID |
| 2 | Usage error (wrong argument count, unknown tag) |

## Related Commands

- [`blkid`](./blkid.md) — the full table of what findfs queries one tag at a time
- [`fdisk`](./fdisk.md) — where PARTUUID/PARTLABEL come from (GPT partition entries)
- [`overview`](./overview.md) — index of all util-linux collection pages

## Interview Questions

### Q: What is the difference between UUID and PARTUUID?

`UUID` is the filesystem's own identifier, stored in its superblock — it
survives re-partitioning and changes when you reformat. `PARTUUID` belongs to
the partition-table entry (GPT GUID, or MBR disk-signature-derived id) — it
survives reformatting and changes when you re-partition. Two independent
identity layers, which is why fstab debugging must know which one an entry
uses.

### Q: How does findfs resolve tags, and what does that imply about duplicates?

It probes devices via libblkid, reading on-disk superblocks and partition
tables — not a config file. Duplicates (cloned filesystems) are legal, and the
match order is not contractual; the safe workflow on suspect systems is
`blkid | grep <tag>` to enumerate all matches and fix or avoid the ambiguity.

### Q: Why does findfs copy unknown arguments to stdout?

Documented passthrough: anything not shaped like `NAME=value` is echoed
unchanged. This lets scripts accept a mix of `UUID=…` tags and device paths
and uniformly feed the result to `mount` — with the caveat that garbage input
becomes garbage output, so validate the result.

### Q: A machine boots fine via fstab UUID entries even after you moved the disk from sda to sdc. Why, and how would you check which device it became?

Because fstab resolution uses libblkid identity lookup (same machinery as
findfs) rather than device names. `findfs UUID=<that-uuid>` — or `lsblk -f` —
prints the current device node. This indirection is exactly why UUID-based
fstab survives hardware reshuffles that break /dev/sdX-based entries.

### Q: findfs as non-root returns nothing though the disk clearly has that label. What is going on?

Probing opens device nodes read-only; without read permission (not in the
`disk` group, restrictive udev rules, containerized /dev), libblkid cannot
inspect superblocks. Run with the same privileges the subsequent mount will
use, or check `ls -l /dev/disk/by-uuid/` as a symlink-level alternative that
udev maintains.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/findfs.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
