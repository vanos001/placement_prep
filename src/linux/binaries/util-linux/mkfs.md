# mkfs — front-end dispatcher for filesystem builders (mkfs.<type>)

## Overview

`mkfs` does not create filesystems itself. It is the generic front end that maps a requested filesystem type to the real builder program `mkfs.<type>`, found on `PATH`, and executes it with the remaining arguments. `mkfs -t ext4 /dev/sdb1` is exactly equivalent to running `mkfs.ext4 /dev/sdb1` (itself a symlink to e2fsprogs' `mke2fs`). The util-linux package also ships a small built-in family of builders — `mkfs.bfs`, `mkfs.cramfs`, `mkfs.minix` — while the mainstream filesystems come from their own packages: `mkfs.ext2/3/4` from e2fsprogs, `mkfs.vfat` from dosfstools, `mkfs.ntfs` from ntfs-3g, `mkfs.xfs` from xfsprogs, `mkfs.btrfs` from btrfs-progs.

It lives at `/usr/sbin/mkfs` and has been part of util-linux since the earliest Linux distributions (the dispatcher concept dates to the 0.9x/1.x kernel era). It is often confused with `mke2fs` (the real ext-family builder), with `parted`/`fdisk` (partition tables — mkfs only ever writes a filesystem *inside* an existing partition), and with `fsck`, its mirror-image front end for checking.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/mkfs |
| First appeared | earliest Linux userspace (0.9x era); util-linux ever since |
| Standards | None — Linux-specific convention |

## Synopsis

```
mkfs [options] [-t <type>] [fs-options] <device> [<size>]
```

Common one-line forms:

```
mkfs -t ext4 /dev/sdb1        # dispatch to mkfs.ext4 (mke2fs)
mkfs /dev/sdb1                # no -t: defaults to ext2
mkfs -t vfat -n LABEL /dev/sdc1   # fs-options pass through to the builder
mkfs -V -V -t minix /tmp/x.img    # double -V: dry run, print the command
```

## How It Works

### The dispatch rule

With `-t <type>`, mkfs searches `PATH` for an executable named `mkfs.<type>` and `exec`s it as:

```
mkfs.<type> [fs-options] <device> [<size>]
```

`fs-options` (everything between the options and the device in mkfs's own argument list) is forwarded verbatim — mkfs does not understand or validate it. Everything interesting (labeling, block size, features) belongs to the builder's own man page. The whole flow:

```
$ mkfs -t TYPE [fs-opts] DEV [SIZE]
        │
        ▼
 search PATH for mkfs.TYPE
        │ found                          │ missing
        ▼                                ▼
 exec mkfs.TYPE [fs-opts] DEV SIZE   "mkfs: failed to execute
        │                             mkfs.TYPE: No such file..."
        ▼
 exit status = builder's exit status
```

A real failure transcript (helper absent, verified):

```
$ mkfs -t bogus /tmp/e2.img
mkfs: failed to execute mkfs.bogus: No such file or directory
```

### The exec mechanics

mkfs parses its own arguments with getopt, stops at the first non-mkfs token, and builds a new argv for the helper: `mkfs.<type> [fs-options...] [device] [size]`. It then performs a PATH search (execvp semantics) for the helper and execs it — process-image replacement, no shell in between. Because the child inherits the built argv verbatim, quoting is the caller's job; because the search is PATH-based, an environment whose PATH lacks `/usr/sbin` cannot dispatch at all. mkfs itself never touches the device and knows nothing about mounted state or fs internals: those checks belong to the helpers (mke2fs refuses a mounted target unless forced with `-F`; mkfs.xfs has `-f` for the same purpose).

### Default type and the -V trick

Without `-t`, the default is `ext2` — a fact that surprises people who assumed modern defaults. The `-V` flag asks mkfs to explain itself; given twice, it turns into a dry run that prints the would-be command without executing it (verified):

```
$ mkfs -V -V -t ext2 /tmp/e2.img
mkfs from util-linux 2.41.5
mkfs.ext2 /tmp/e2.img
```

(Here mkfs.ext2 was not installed, so a real run would fail — the dry run still shows the exact dispatch.)

### The device and size operands

`<device>` is whatever the builder accepts: a partition node, a loop device, or a regular file for image creation. The trailing `<size>` (in 1 KiB blocks) is a legacy operand forwarded to builders that still accept an explicit block count (the minix family does; e2fsprogs takes it as an optional filesystem-size override). Because different builders interpret it differently, modern practice is to omit it and size the container (partition or file) beforehand.

### Why the dispatcher exists at all

It gives scripts and humans one stable spelling — `mkfs -t <type>` — across builders from five different packages with wildly different option vocabularies. The cost is discoverability: every meaningful option lives in the specific builder, so serious work always ends at `man mkfs.ext4` or `mkfs.vfat --help`.

### The helper landscape

What `-t` resolves to, per ecosystem segment:

| Type | Helper binary | Owning package | Notes |
| --- | --- | --- | --- |
| ext2/3/4 | mkfs.ext2/3/4 → mke2fs | e2fsprogs | the mainstream Linux default |
| vfat/fat | mkfs.vfat, mkfs.fat | dosfstools | USB sticks, EFI partitions |
| ntfs | mkfs.ntfs | ntfs-3g | Windows interop volumes |
| xfs | mkfs.xfs | xfsprogs | RHEL-lineage default |
| btrfs | mkfs.btrfs | btrfs-progs | subvolume-based, CoW |
| f2fs | mkfs.f2fs | f2fs-tools | flash-native |
| minix | mkfs.minix | util-linux | built-in family (own page) |
| cramfs | mkfs.cramfs | util-linux | built-in family (own page) |
| bfs | mkfs.bfs | util-linux | built-in family (own page) |

The dispatcher knows none of this table — it only concatenates `mkfs.` + type and searches PATH. That is why installing the right package is a prerequisite for `-t` to work at all, and why the same command can succeed on one host and print "failed to execute" on another.

### Dispatcher or direct helper in scripts?

Both work; they differ in indirection and failure mode. `mkfs -t "$type"` shines when the type is a variable; `mkfs.ext4` (or better, `mke2fs -t ext4`) removes a lookup step and gives clearer errors. One subtlety: root's PATH traditionally includes `/usr/sbin`, but unprivileged callers or stripped environments (cron with minimal PATH, containers with trimmed PATH) may not find sbin helpers — the dispatcher inherits that fragility. Robust scripts either call the helper by absolute path or verify with `command -v` first.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-t, --type=<type>` | Filesystem type; selects the `mkfs.<type>` helper (default: ext2) |
| `fs-options` | Arbitrary arguments passed through to the helper, unchanged |
| `<device>` | Target: partition, loop device, or image file |
| `<size>` | Optional block count (1 KiB blocks) forwarded to the helper |
| `-V, --verbose` | Explain what is being done; `-V -V` performs a dry run (print command, do not execute) |

Note the double `-V` dry-run — a dispatcher-level safety net that exists independently of whatever the helper supports.

One more argument-shape detail: options *before* `-t`/fs-options belong to mkfs; options after the type belong to the helper. `mkfs -t vfat -n KEYS ...` forwards `-n KEYS` (a dosfstools label flag), while `mkfs -V -t vfat ...` keeps `-V` for itself. The boundary is the first non-mkfs token — which is why the synopsis orders options, fs-options, then device.

## Usage Patterns

```bash
# The everyday case: ext4 on a fresh partition
mkfs -t ext4 /dev/sdb1
```

```bash
# Equivalent — and what actually runs:
mkfs.ext4 /dev/sdb1
```

```bash
# FAT32 USB stick, label set through pass-through options
mkfs -t vfat -n KEYS -F 32 /dev/sdc1
```

```bash
# XFS on a data volume (xfsprogs installed)
mkfs -t xfs /dev/vg0/data
```

```bash
# Dry-run: print the command that would execute, change nothing
mkfs -V -V -t ext4 /dev/sdb1
```

```bash
# Create an ext2 filesystem on a regular file (image building)
dd if=/dev/zero of=/tmp/e2.img bs=1M count=64
mkfs -t ext2 /tmp/e2.img
```

```bash
# One of util-linux's built-in helpers (see its own page)
mkfs -t minix /tmp/m.img
```

```bash
# Script that picks the helper by type and fails loudly if absent
type="xfs"; command -v "mkfs.$type" >/dev/null || { echo "mkfs.$type missing"; exit 1; }
mkfs -t "$type" /dev/nvme0n1p3
```

```bash
# What happens with an unknown type (real error output)
mkfs -t zol /dev/sdb1    # mkfs: failed to execute mkfs.zol: No such file or directory
```

```bash
# Verify what a helper actually is before trusting it
ls -l "$(command -v mkfs.ext4)"   # symlink to mke2fs
```

```bash
# FAT image file for a VM/firmware that expects a bare FAT filesystem
truncate -s 64M fat.img && mkfs -t vfat fat.img
```

```bash
# Show the failure mode of fs-options validation: mkfs forwards, helper complains
mkfs -t ext2 --not-a-real-flag /tmp/e2.img
```

```bash
# Guard concurrent formatting: two runs on one device corrupt silently
flock /var/lock/mkfs-nvme0n1p3.lock mkfs -t ext4 /dev/nvme0n1p3
```

```bash
# Wipe stale signatures so blkid sees the new filesystem, not the old one
wipefs -a /dev/sdb1 && mkfs -t xfs /dev/sdb1
```

```bash
# Before/after identity check: what does the kernel see on the partition?
lsblk -f /dev/sdb1 && mkfs -t ext4 /dev/sdb1 && lsblk -f /dev/sdb1
```

## Nuances and Gotchas

- **No type means ext2 — on a whole disk, that is a mistake generator.** `mkfs /dev/sdb` (forgot partition number *and* type) builds an old-style ext2 across the entire device, destroying the partition table and any data. Slow down at exactly this command.
- **mkfs never partitions.** Running it on the whole-disk node instead of a partition (`/dev/sdb` vs `/dev/sdb1`) "works" and ruins layouts. Partition first (`fdisk`/`parted`), then format the partition.
- **The helper, not mkfs, decides everything.** Feature sets, defaults, and options differ per builder; `-t ext4` on one distro era can mean different mke2fs defaults. Read the specific builder's man page; treat mkfs as plumbing.
- **fs-options are not validated.** A misspelled pass-through option surfaces as the *helper's* error, possibly after it has started writing. The double-`-V` dry run shows dispatch but not the helper's argument interpretation.
- **Exit status passthrough.** mkfs returns the helper's exit status, so `mkfs -t xfs /dev/sdb1 && swapon...` style chains behave correctly; a missing helper is exit 1 with the "failed to execute" message.
- **`mkfs.ext4` etc. are often symlinks.** On Debian, `mkfs.ext2/3/4` all point to `mke2fs`, which switches personality by program name. That is why `man mkfs.ext4` may land on the mke2fs page.
- **Size operand is legacy.** Builders disagree on its meaning; sizing via partition table or image file is the robust path.
- **Helpers are exec'd, not forked shells.** There is no quoting layer between mkfs and the helper: fs-options arrive as verbatim argv. Arguments with spaces or glob characters must be quoted by *you* at the mkfs call site, exactly as if calling the helper directly.
- **The banner line is a version tell.** `mkfs -V` prints "mkfs from util-linux <version>" — occasionally the fastest way to answer "which util-linux is this box running" during an incident, without touching dpkg.
- **No locking.** Two concurrent `mkfs -t` runs on the same device interleave writes with no warning; both "succeed" and the result is a corrupt hybrid. Provisioning scripts should hold a lock (`flock`) keyed on the device.
- **Stale signatures outlive reformatting.** A fresh superblock does not always erase leftovers of the previous filesystem's structures; `wipefs -a` first is the hygiene step that keeps `blkid`'s type/UUID reporting honest after reformatting.
- **Refusals differ per helper.** mke2fs needs `-F` to proceed on mounted targets, mkfs.xfs needs `-f`; a generic wrapper can promise uniform dispatch but not uniform guard rails — check the helper's own safety flags.

## Exit Status

- Builder's own exit status — `0` success, non-zero per that builder's conventions — passed through unchanged.
- `1` — mkfs itself failed to find/execute the helper (or usage error; verified for the missing-helper case).

## Related Commands

- [`mkfs.minix`](./mkfs.minix.md) — built-in Minix builder dispatched by this front end.
- [`mkfs.bfs`](./mkfs.bfs.md) — built-in boot-filesystem builder of the same family.
- [`mkfs.cramfs`](./mkfs.cramfs.md) — built-in compressed-ROM image builder.
- [`mkswap`](./mkswap.md) — sibling initializer for swap areas (same "write a header" pattern).
- [`fsck`](./fsck.md) — the mirror-image front end dispatching to `fsck.<type>` checkers.
- [`fdisk`](./fdisk.md) — creates the partitions mkfs formats.
- [`blkid`](./blkid.md) — confirms afterwards what filesystem/UUID landed on the device.

## Interview Questions

### Q: What does running plain `mkfs /dev/sdb1` do?

With no `-t`, the dispatcher defaults to ext2 and looks for `mkfs.ext2` on PATH. So you get an ext2 filesystem — not ext4 — with all that implies (no extents, no journal). Interviewers use this to test whether people know mkfs is a dispatcher with a default, not a smart formatter.

### Q: Explain what `mkfs -V -V -t xfs /dev/sdb1` does.

First `-V` turns on explanation; the second turns it into a dry run: mkfs prints the exact command it would execute (`mkfs.xfs /dev/sdb1`) and does not run it. Nothing touches the device. It is the dispatcher-level preview, useful to confirm which helper a type maps to before a destructive operation.

### Q: You run mkfs and get "failed to execute mkfs.zfs: No such file or directory". Diagnose.

mkfs searched PATH for `mkfs.zfs`, found nothing — ZFS has no such helper (its own tooling formats pools). The exit status is 1 and no data was touched. Generally: this error means either the type string is wrong or the package owning the helper (e2fsprogs, dosfstools, xfsprogs, ...) is not installed.

### Q: Why do mkfs and fsck both exist as front ends rather than one monolithic tool?

Filesystem builders/checkers are huge, package-specific codebases with independent release cycles; a monolith would couple util-linux to all of them. The dispatcher keeps the kernel-adjacent package tiny while giving users one spelling (`-t type`) and giving packages a stable hook (`mkfs.<type>` on PATH). The same pattern explains `/sbin/fsck.<type>`.

### Q: Is `mkfs -t ext4` or `mkfs.ext4` preferable in scripts, and why?

`mkfs.ext4` (or directly `mke2fs -t ext4`) is preferable: it has no dispatch indirection, its errors are unambiguous, and it works even where PATH for root differs. `mkfs -t` is for generic tooling that takes the type as a variable. Also note exit-status passthrough makes both scriptable — the difference is indirection and discoverability, not capability.

### Q: What exactly does mkfs do with fs-options like `-n LABEL`, and who validates them?

Nothing, and the helper does. mkfs's argv handling treats everything between its own options and the device as opaque fs-options and forwards them verbatim to the exec'd helper. Validation is entirely the helper's problem — a typo surfaces as the helper's error, possibly mid-format. This is why the double `-V` dry run plus a check of the target helper's man page is the professional pre-flight, and why generic wrappers around mkfs cannot promise option safety across types.

### Q: How would you add support for `mkfs -t myfs` across a fleet?

Ship an executable named `mkfs.myfs` on PATH (conventionally `/usr/sbin`, via a package). That is the entire contract: accept `[fs-options] <device> [<size>]`, do your own validation (mounted check, size sanity), write errors to stderr, exit nonzero on failure — mkfs forwards everything verbatim and passes the exit status through. A matching `fsck.myfs` completes the integration for the checking side. There is no central registry to edit, which is also why typos surface as "failed to execute" rather than a helpful list of known types.

### Q: A provisioning script formats devices in parallel and intermittently produces a broken filesystem. The devices are different. Diagnose.

Different devices rule out write contention on one node, so look at shared state: a lockless step upstream (partitioning the whole disk with sfdisk while formatting partitions of it), a shared config file the helper reads (mke2fs.conf), or PATH dispatching to different helper binaries in the two environments (cron's reduced PATH). Add `command -v mkfs.$type` logging, use `mkfs -V -V` dry runs in CI to see the exact dispatch, and serialize disk-level steps with `flock` while keeping per-device steps parallel. The dispatcher itself is stateless — the bug lives one layer down.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mkfs.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
