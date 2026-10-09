# df — report filesystem free space and usage

## Overview

`df` ("disk free") answers a layout-level question: for each mounted
filesystem — or the one holding a given path — how much space and how many
inodes exist, how many are used, and how many can actually still be
consumed. It reads the kernel's `statfs(2)`/`statvfs(2)` counters per mount
point, so it is an instant, filesystem-scoped report: it does not walk any
directories.

It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at
`/usr/bin/df`, maintained upstream as part of GNU coreutils. `df` is one of
the oldest Unix tools still in daily service, present since Version 1 UNIX,
and POSIX pins its behavior — which is why `-P` exists to enforce the
portable output format on top of GNU niceties.

`df` is most often confused with `du` (which *aggregates per-file usage* by
walking trees — the two disagree in interesting ways, see gotchas), with
`free` (RAM/swap, not filesystems), and with `lsblk`/`mount` (block device
topology and mount table, not usage). In containers both the question and
the answer twist: the `overlay` root reports the backing store's numbers,
not a per-container quota.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/df` |
| First appeared | AT&T UNIX, Version 1 (1971) |
| Standards | POSIX.1-2018 (`df`, including `-P`) |

## Synopsis

```
df [OPTION]... [FILE]...
```

Common one-line forms:

```
df -h                 # all filesystems, human sizes
df -h /var            # just the filesystem holding /var
df -i                 # inode inventory instead of blocks
df -T -x tmpfs        # with fs type, minus pseudo filesystems
df -P                 # POSIX-stable one-line-per-fs format (for scripts)
```

## How It Works

### Where the numbers come from

For each FILE operand, `df` resolves the filesystem that contains it and
calls `statfs` on that mount point. With no operands, it reads the mount
table (`/proc/self/mounts` via the classic mount-list machinery), picks one
entry per filesystem, and stats each. Three filtering behaviors are built
in: pseudo filesystems of size 0 are hidden unless `-a`, duplicate mounts of
the same filesystem are collapsed to the first entry unless `-a` (bind
mounts are the usual casualties), and inaccessible or exotic entries are
silently skipped. Everything printed is a direct projection of the statfs
fields:

```
Filesystem                 1K-blocks     Used    Available  Use%  Mounted on
overlay                    10284308   180196     9563440     2%    /
│                          │          │          │           │     │
│                          │          │          │           │     └─ mount point statted
│                          │          │          │           └─ used/(used+avail)
│                          │          │          └─ f_bavail: free to non-root users
│                          │          └─ f_blocks − f_bfree
│                          └─ f_blocks scaled to 1 KiB units (512 B under POSIXLY_CORRECT)
└─ device or fs identifier from the mount table
```

`Available` is deliberately *not* `Size − Used`: the difference is the
reserved-block pool of the next section. `Use%` is computed as
`used / (used + avail)`, so it reaches 100% exactly when the non-root
view runs dry — which is the number that actually matters for your
application, and the reason a "100% full" filesystem can still accept
root's writes.

### Reserved blocks: why Available < Size − Used

Classic filesystems (the ext family by default) reserve a percentage of
blocks for the superuser — historically 5%, tunable with `tune2fs -m` — so
that root retains headroom to log in, clean up, and run fsck when
unprivileged usage hits the ceiling, and so that heavy allocation doesn't
fragment the tail of the disk. XFS keeps a similar dynamic reserve. The
kernel reports both views, and `df` shows the non-root one:

```bash
# Real arithmetic from a live container root (overlay):
#   Size − Used − Available = 10284308 − 180196 − 9563440 = 540672 KiB
#   ≈ 5.3% of the device is allocated-but-not-user-available
df -k /
```

On that overlay filesystem the gap comes from the kernel's internal
accounting of the backing store rather than `tune2fs`, but the shape is
identical everywhere: `stat -f` exposes the same split as its `Free` versus
`Available` lines (`f_bfree` vs `f_bavail`), which is the kernel-level proof
that "free" and "available to you" are different numbers.

### Inodes: the other exhaustion cliff

`df -i` swaps the block counters for the inode counters:

```bash
$ df -i /
Filesystem        Inodes   IUsed    IFree IUse% Mounted on
overlay           655360     7465   647895    2% /
```

Every file, directory, symlink, and fifo consumes one inode regardless of
size, and on ext-family filesystems the inode count is fixed at `mkfs` time.
A directory of millions of tiny files can exhaust inodes while `df -h`
cheerfully reports gigabytes free — and writes then fail with
`No space left on device` anyway. ext4 can't grow its inode table in place;
XFS allocates inodes dynamically; tmpfs sizes its inode pool from RAM. The
hunting companion is `du --inodes` to find which subtree ate them.

### Units and scaling

The default unit is 1 KiB blocks (`1K-blocks`); `--block-size=SIZE` or
`-B` rescales, with `K,M,G,...` meaning powers of 1024 and `KB,MB,...`
powers of 1000. `-h` picks unit suffixes per value (powers of 1024), `-H`
does the same in marketing gigabytes (powers of 1000) — a 1023M vs 1.1G
kind of difference that trips up screenshots-vs-logs comparisons. The
environment can override units (`DF_BLOCK_SIZE`, `BLOCK_SIZE`,
`BLOCKSIZE`, in that precedence), and setting `POSIXLY_CORRECT` silently
drops the default to 512-byte units. All of this argues for `-P` plus
explicit expectations in anything automated.

### The portable format and column selection

GNU `df` wraps long device names across two lines on narrow terminals and
localizes headers — hostile to scripts. `-P` forces the POSIX contract: one
line per filesystem, fixed headers (`1024-blocks`, `Capacity`), no
wrapping:

```bash
$ df -P /
Filesystem                     1024-blocks     Used Available Capacity Mounted on
overlay                          10284308   180196   9563440       2% /
```

`--output=FIELD_LIST` builds custom columns (`source,fstype,size,used,
avail,pcent,target` among others) and is mutually exclusive with both `-i`
and `-P` — enforced with an error, which is itself a portability trap when
scripts mix the flags. `-T` adds the Type column, `-t TYPE` and
`-x TYPE` include/exclude filesystem types (repeatable), `-l` restricts to
local filesystems — GNU's test is device-name based, so NFS-style
host-qualified mounts drop but a FUSE mount named `ossfs` passes — and
`--total` appends a grand-total row.

### Container and pseudo-filesystem quirks

A running container's `df /` describes the `overlay` filesystem — the host's
backing store, not any container quota. That is why `df -h /` inside Docker
shows the host-sized root no matter how small the container's write layer
is, why K8s ephemeral-storage accounting walks files instead of trusting
`df`, and why a size-limited `overlay` (podman `--storage-opt size=`) shows
up only because the limit was imposed at the filesystem level. `tmpfs`
mounts report their *configured* size (RAM/swap backed), and network or FUSE
filesystems may report fiction — a grounded example from this very class of
mounts: an object-storage FUSE mount reports `18014398509465600` 1K-blocks,
≈ 2⁶⁴ bytes (16 EiB): "unknown capacity" rendered as full-scale, with
`df -i` showing `0 0 0 -` for its inode row.

## Options That Matter

### Units and layout

| Option | Effect |
| --- | --- |
| `-h` | Human-readable sizes, powers of 1024 |
| `-H` | Human-readable, powers of 1000 (`--si`) |
| `-B SIZE` / `--block-size` | Fixed unit: `-BM` prints 1M-blocks; `KB` suffixes mean 1000 |
| `-k` | Force 1 KiB blocks |
| `-P` | POSIX format: one line per fs, stable headers, no wrapping |
| `--output=FIELDS` | Custom column list; mutually exclusive with `-i` and `-P` |

### Selection and scope

| Option | Effect |
| --- | --- |
| `-a` | Include pseudo, duplicate, and inaccessible entries |
| `-l` | Local filesystems only (no NFS/FUSE/network) |
| `-t TYPE` | Only filesystems of TYPE (repeatable) |
| `-x TYPE` | Exclude TYPE (repeatable) — `df -x tmpfs -x devtmpfs` |
| `-T` | Add the filesystem Type column |
| `--total` | Append a grand-total row |
| `--sync` / `--no-sync` | Flush before reporting (default is no-sync on recent coreutils) |

## Usage Patterns

```bash
# The reflex: how full is everything, human units
df -h
```

```bash
# Will this path hold a 4 GiB artifact? (resolves the holding fs)
df -h /var/lib/build
```

```bash
# Inode exhaustion check for a maildir-style workload
df -i /var/spool
```

```bash
# Container-safe listing: drop the pseudo filesystems
df -h -x tmpfs -x devtmpfs -x shm -x overlay
```

```bash
# Script-grade threshold check: one line per fs, POSIX headers
df -P | awk 'NR>1 && $5+0 >= 90 {print $6" at "$5}'
```

```bash
# Decide "enough free?" numerically before a download (avail in KiB)
need=$((8*1024*1024))   # 8 GiB in KiB
have=$(df -Pk /opt | awk 'NR==2 {print $4}')
[ "$have" -gt "$need" ] || echo "insufficient space" >&2
```

```bash
# What filesystem type serves this path? (branch script logic)
df --output=fstype /home | tail -1
```

```bash
# Machine-readable custom report: source, type, usage, target
df --output=source,fstype,size,used,avail,pcent,target / /tmp
```

```bash
# Capacity rollup across the fleet's volumes
df -h --total | tail -1
```

```bash
# Which fs holds this bind-mounted file? (goes by the path, not the name)
df /etc/hostname | tail -1
```

```bash
# Compare 1024-based vs 1000-based marketing numbers on one line each
df -h / && df -H /
```

```bash
# Show duplicate/bind-mounted views too, not just first-per-fs
df -a | head
```

## Nuances and Gotchas

- **`Use%` is not `Used/Size`.** It is `used/(used+avail)`, so reserved
  blocks never push it past 100% — and conversely a fs can read `2%` while
  root's own quota tools scream. When the numbers look inconsistent,
  compute `Size − Used − Available` yourself; a few percent of "missing"
  space is the reserve pool, not a bug.
- **df and du disagree by design.** `du` walks visible files; `df` reports
  kernel counters. Deleted-but-open files (log rotated while the daemon
  still holds the fd) count for `df`, not `du` — the classic "I deleted
  logs but df didn't move" — find them with `lsof +L1`. Sparse files and
  mounted-over directories widen the gap further.
- **overlayfs in containers lies helpfully.** `df` inside a container shows
  the underlying store's capacity, not the container's writable-layer
  limit; two containers on one host report identical numbers. Per-container
  accounting must come from cgroups or project quotas, not `df`.
- **tmpfs "free space" is free RAM.** `df /dev/shm` reports the tmpfs
  *size*, and filling it is memory pressure by another name. A 0%-used
  tmpfs is still costless; a 99% one is an OOM risk, not a disk problem.
- **FUSE and network filesystems invent values.** Capacities of ≈2⁶⁴ bytes
  (16 EiB), `0` inode counts, and `-` percentage cells (all observed on an
  object-storage FUSE mount) mean "unknown". `-l` won't save you — GNU
  treats that FUSE mount as local — filter by type (`-x fuse.ossfs`)
  instead, and never alert on their percentages.
- **`-a` is the only way to see bind mounts and duplicates.** GNU `df`
  collapses repeat mounts of the same filesystem to the first entry by
  default — debugging a bind-mount puzzle on a bare `df` misleads.
- **`POSIXLY_CORRECT` flips units to 512.** The same script on the same
  host can parse different numbers when the variable leaks into the
  environment; `-k` or `-B` pins the unit explicitly.
- **`--output` fights `-i` and `-P`.** Combining them is a hard error
  (`options -i and --output are mutually exclusive`); scripts that want
  both custom columns and POSIX stability must pick one.
- **`-t`/`-x` match the fs *type string*** (`tmpfs`, `ext4`, `nfs4`,
  `fuse.ossfs`), not the device name — filter by `df -T` output, not by
  guesswork, and remember they are repeatable for multi-type filters.
- **Exit codes are coarse.** 0 means every requested filesystem reported;
  1 covers both a missing FILE operand and the `no file systems processed`
  case when `-x` filters everything — the message differs, the code doesn't.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | All requested filesystems reported successfully |
| 1 | Any FILE operand failed to resolve, or no filesystem survived the filters (`df: no file systems processed`) |

## Related Commands

- [`du`](./du.md) — per-directory usage aggregation; the other half of every "where did my disk go" session.
- [`stat`](./stat.md) — per-file and per-filesystem facts (`stat -f`) for a single path.
- [`ls`](./ls.md) — `ls -s` shows allocated blocks per file; the per-file sliver of df's story.
- [`truncate`](./truncate.md) — manufactures the sparse files that make df/du comparisons interesting.
- [`numfmt`](./numfmt.md) — reformats raw byte counts into the human units df prints natively.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [find](../../shell/find.md) — pairs with `du` to locate the subtrees that filled the filesystem.
- [man pages](../../reference/man-pages.md) — where `df(1)` and `statvfs(2)` are documented.

## Interview Questions

### Q: Why does Size minus Used not equal Available in df output?

Because classic filesystems reserve a block pool for the superuser — 5% by
default on ext2/3/4, adjustable with `tune2fs -m` — and `df`'s Available
column reports `f_bavail`, the non-root view, while Used + Available skips
the reserve. The reserve guarantees root can still log in and clean up when
users hit the ceiling, and mitigates fragmentation. `df`'s Use% is
`used/(used+avail)`, so it hits 100% exactly when ordinary users run out,
even though `stat -f` (or root) can still see truly free blocks.

### Q: I deleted a 50 GB log file but `df` shows no change. What's going on?

The space is still held because some process keeps the file open — the
directory entry is gone (so `du` and `ls` can't see it), but the inode
survives until the last fd closes, and `df` counts it as used. `lsof +L1`
lists open files with a link count of 0, which identifies the culprit;
restarting or signaling the daemon releases the space. The same df/du
disagreement also arises from sparse files, hard links counted once by du,
and directories mounted over.

### Q: Users report "No space left on device" but `df -h` shows gigabytes free. Diagnose.

Check `df -i` first: the filesystem is out of *inodes*, not blocks. Every
file, symlink, and directory consumes one inode, ext-family inode tables are
fixed at mkfs time, and a tree of millions of small files (mail, cache,
session stores) exhausts them while free bytes remain. `du --inodes` finds
the offending subtree; the durable fixes are clearing it, moving the
workload to a filesystem with dynamic inode allocation (XFS), or reformatting
ext with a larger inode count — inodes cannot be grown in place on ext4.

### Q: What does `df /` inside a Docker container actually report, and why?

The `overlay` filesystem's numbers: the host's backing store capacity and
the aggregate usage of the whole overlay, not the container's writable-layer
quota. Every container on that host shows the same figures, which is why
"df says I have 900 GB" coexists with write failures under a 10 GB
`--storage-opt size=` limit — the limit is enforced by the filesystem, and
only a quota-aware overlay shows it in df. Kubernetes therefore accounts
ephemeral storage by walking files, not by trusting df.

### Q: Why do scripts insist on `df -P`, and what changes under it?

POSIX's portable format is a stable contract: one line per filesystem, fixed
headers (`1024-blocks`, `Capacity`), no localized column names, and no
device-name wrapping when a mount identifier is longer than the terminal —
all of which GNU df does differently in its default layout, silently
shifting field positions that `awk`/`cut` depend on. `-P` also sidesteps
the `POSIXLY_CORRECT` 512-byte unit flip when paired with explicit units.
The cost is losing GNU-only niceties like `-h` on the same invocation,
hence the `-Pk` + awk idiom.

### Q: When does a tmpfs filesystem become a memory problem rather than a disk one?

Always — tmpfs consumes RAM (and swap) for every page it holds, and its df
"size" is just the configured ceiling, not preallocated storage. A busy
`/dev/shm` or a full `tmpfs /tmp` converts file writes into memory pressure,
ending in the OOM killer rather than ENOSPC, and its usage vanishes on
unmount/reboot. Sizing matters: the classic case is PostgreSQL requiring
`/dev/shm` ≥ its shared-memory setting, which Docker's default 64 MB
famously violates.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/df.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
