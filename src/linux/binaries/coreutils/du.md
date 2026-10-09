# du — estimate file and directory disk usage

## Overview

`du` ("disk usage") answers a subtree-level question: for each directory or
file you name, how much space does it actually consume? Unlike `df`, which
instantly reads mount-point counters, `du` walks the directory tree with
`fts`, calls `stat`/`lstat` on every entry, and sums allocated blocks — the
tool for "where did my disk go" forensics, and the reason it can take minutes
on large or remote trees.

The central distinction `du` forces you to learn is **apparent size vs disk
usage**: `ls -l` reports `st_size`, the logical byte count; `du` reports
`st_blocks * 512`, the physically allocated storage. Sparse files and
filesystem overhead make these numbers diverge, and `du` has flags for either
view.

It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at
`/usr/bin/du`. It is often confused with `df` (filesystem-level, instant,
mount-point counters) and with `ls -s` (per-file allocated blocks). `du`
reports *usage*, not *free space* — pairing it with the sibling [df](./df.md)
page is standard practice.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section | 1 |
| Path | `/usr/bin/du` |
| First appeared | Version 1 AT&T UNIX (1971) |
| Standards | POSIX.1-2018 (`du`); `-h`, `-d`, `--exclude`, `--files0-from` etc. are GNU extensions |

## Synopsis

```
du [OPTION]... [FILE]...
du [OPTION]... --files0-from=F
```

Common forms:

```
du -sh DIR                 # one human-readable total per argument
du -h --max-depth=1 DIR    # breakdown one level deep
du -sh --apparent-size DIR # logical byte count instead of blocks
```

## How It Works

### What gets counted

For every file it reaches, `du` adds `st_blocks` (512-byte units allocated on
the device) to the running total of the enclosing directory. Directory sizes
are the rollup of everything beneath them; the line for a directory appears
only after its whole subtree has been processed. Display units default to
1024-byte blocks (`-k` behavior); with `POSIXLY_CORRECT` set, 512-byte
blocks. `DU_BLOCK_SIZE`/`BLOCK_SIZE`/`BLOCKSIZE` (in that precedence order)
override the unit — see Nuances.

```
┌──────────── fts walk of each FILE argument ────────────────┐
│  entry → --exclude match?         → drop                   │
│        → -x and st_dev changed?   → skip                   │
│        → (st_dev, st_ino) seen?   → skip (hard link)       │
│        → else: add st_blocks * 512 to the running total    │
└─────────► directory line printed when subtree closes ◄─────┘
```

### Apparent size vs disk usage

`--apparent-size` (or `-b`) switches the sum from `st_blocks` to `st_size`.
The views agree for ordinary full files and diverge for sparse files.
Grounded example (4 MiB sparse file plus a real 2 MiB file):

```bash
$ dd if=/dev/zero of=sparse1 bs=1 count=0 seek=4M   # 4 MiB hole
$ dd if=/dev/zero of=f1 bs=1M count=2
$ du -h .                    # disk usage view
2.0M    ./f1
0       ./sparse1
$ du -h --apparent-size .    # logical size view
6.0M    .
$ du -b sparse1; du -k sparse1
4194304 sparse1   # st_size: what ls -l shows
0       sparse1   # st_blocks: what the device actually holds
```

Neither view is "wrong": disk usage predicts `df` movement and raw-block
backups; apparent size predicts `tar`/`scp` content volume.

### Hard links: counted once

`du` keeps a hash of `(st_dev, st_ino)` pairs: a file with N hard links
contributes its blocks only the first time it is encountered; other names are
skipped — and, notably, with `-a` they are not even listed. That is the
correct semantic for "space used". `-l` (`--count-links`) defeats the dedup
and sums every name — useful to estimate "what would a copy cost", wrong for
"what does it use now".

```bash
$ dd if=/dev/zero of=big bs=1M count=3; ln big big2
$ ls -li big big2
269786 -rw-rw-r-- 2 z z 3145728 big
269786 -rw-rw-r-- 2 z z 3145728 big2     # same inode
$ du -a -B1 .
1048576 ./f1
3145728 ./big2                           # inode counted under ONE name
4198400 .                                # big itself: omitted, not printed as 0
$ du -s -l .
7172     .                               # 3 MiB x2 + f1 + dir overhead
```

### Depth, scope, and selection modifiers

`-s` (`--summarize`) prints only each argument's total; `-d N`
(`--max-depth=N`) prints totals up to N levels below the arguments, with
`-d0` equal to `-s`. `-a` additionally lists non-directories. `-S`
(`--separate-dirs`) rolls subdirectory sizes *out* of the parent line. `-x`
(`--one-file-system`) freezes traversal at the first `st_dev` change — the
reflex flag when `/proc`, `/dev`, or bind mounts must not be pulled in.

### Exclude patterns and thresholds

`--exclude=PATTERN` and `-X FILE` (patterns, one per line) filter entries
during traversal. Patterns are shell globs matched against the *base name*
(`*.log`, `node_modules`), and excluding a directory name prunes its entire
subtree. Two sharp edges, both verified:

```bash
$ dd if=/dev/zero of=a/big bs=1M count=1; ln a/big a/big2; ln a/big a/big3
$ du -s --exclude=a/big .        # excludes the NAME, not the inode
1028    .                        # data still counted under a/big2, a/big3
$ du -s a
1028    a
```

`--exclude` filters names, so a hard-linked file excluded under one name
still lands in the total under another. It is *not* a size filter — that is
`-t/--threshold`: positive values drop entries smaller than the size,
negative values drop entries larger. Thresholds compare *disk* usage, so a
4 MiB sparse file with 0 allocated blocks disappears under `-t 1M` and
survives under `-t -1M`.

### Symlinks

By default (`-P`) symlinks are never followed and cost the few bytes of the
link itself. `-D/--dereference-args` follows only symlinks named on the
command line; `-L/--dereference` follows every symlink found while walking.
Measured on this container where `/bin -> usr/bin`:

```bash
$ du -s /bin     # 0      : the link alone
$ du -sD /bin    # 479144 : /usr/bin's contents, counted once
$ du -sL /bin    # 479976 : plus anything reached only via inner links
```

`-L` risks double counting and loops through symlink cycles; prefer `-D`.

### Cost model: NFS and huge trees

`du` is `O(files)`: one `readdir` per directory and one `stat` per entry. On
a local SSD that is fast; over NFS every stat is a wire round-trip, so a tree
with millions of files can take hours and hammer the server. Mitigations:

- run `du` *on* the NFS server (or in the container whose volume it is);
- prune early with `--exclude` so whole branches are never stat'ed;
- feed precomputed paths from `find -print0` via `--files0-from=-`;
- scope with `-x`; `--inodes` changes the unit but not the stat cost.

### Containers and overlayfs

Inside a container `/` is typically an `overlay` mount. `du -x /` stays on
that overlay device and skips every bind-mounted volume (different `st_dev`)
— verified here: `du -sx /` reported 99900 blocks, excluding proc/dev/tmpfs
mounts. Three overlay-specific caveats:

- `du` sees the *merged* view; a deleted lower-layer file vanishes from `du`
  but its blocks may still sit in the host's upperdir/lowerdir until the
  layer is squashed, so host-side `df` can exceed container-side `du`.
- Volumes and tmpfs mounts are separate filesystems: plain `du /var` may
  silently cross into them, or (with `-x`) silently skip them — decide which
  you want.
- `du` on `/proc`/`/sys` produces `cannot access` errors and exit status 1
  even though output is otherwise fine — a `set -e` script killer.

## Options That Matter

### Size semantics

| Option | Effect |
|---|---|
| `--apparent-size` | Sum `st_size` (logical bytes) instead of allocated blocks |
| `-b` | `--apparent-size --block-size=1`: exact bytes, no rounding |
| `-h` | Human units (1K 234M 2G, powers of 1024), rounded **up** |
| `-k` / `-m` | Force 1 KiB / 1 MiB units (`--si` for powers of 1000) |
| `-B SIZE` | Scale to SIZE (`-BM`, `-B1`); integer units round up |

### Scope and selection

| Option | Effect |
|---|---|
| `-s` | One total per argument (`-d0`) |
| `-d N` | Totals to depth N below each argument |
| `-a` | List files too, not just directories |
| `-S` | Directory lines exclude subdirectory totals |
| `-x` | Stay on one filesystem (`st_dev` guard) |
| `-D` / `-L` | Dereference command-line symlinks only / all symlinks |

### Counting and filtering

| Option | Effect |
|---|---|
| `-l` | Count hard links once per *name*, not per inode |
| `--inodes` | Report inode counts instead of block usage |
| `-t SIZE` | Skip entries smaller (+) or larger (−) than SIZE |
| `--exclude=PAT` | Glob match on base name; prunes subtrees |
| `-X FILE` | Exclusion patterns read from FILE |
| `--files0-from=F` | Arguments from NUL-separated list (`-` = stdin) |

## Usage Patterns

```bash
# The reflex: how big is this directory, human units
du -sh /var/lib/docker
```

```bash
# Breakdown one level deep, sorted worst-first (sort -h eats K/M/G suffixes)
du -h -d1 /var | sort -h | tail
```

```bash
# Biggest individual files in a tree, byte-precise
du -a -B1 /home | sort -n | tail -20
```

```bash
# What will tar/scp actually move? logical size, not blocks
du -sh --apparent-size dataset.tar
```

```bash
# Estimate copy cost despite hardlink dedup
du -sh -l /usr | tail -1
```

```bash
# Skip the vendored trees nobody audits
du -sh --exclude=node_modules --exclude=.git .
```

```bash
# Root sweep that never leaves the root filesystem (containers, rescue shells)
du -xh -d2 / | sort -h | tail
```

```bash
# Only weight-class contenders: drop everything under 100 MiB
du -ah -t 100M /var/log | sort -h
```

```bash
# Inode pressure check for a maildir host
du --inodes -s /var/spool
```

```bash
# Machine-readable per-file byte counts straight from find
find /workspace -name '*.tar' -print0 | du -sb --files0-from=-
```

## Nuances and Gotchas

- **`-h` rounds up, always.** A 2052-block (2.0039 MiB) total prints as
  `2.1M`; a 1025-byte file under `-BM` prints as `1M`. GNU refuses to
  under-report, so parsed `du -h` output overestimates; scripts should use
  `-k`, `-B1`, or `-b`.
- **Environment units ambush scripts.** `DU_BLOCK_SIZE`/`BLOCK_SIZE`/
  `BLOCKSIZE` in the environment rescale plain `du -s` output, and cron/CI
  environments differ from interactive shells. Pin with `-k`.
- **`du` counts disk, `ls` counts bytes.** Sparse files show `du 0` /
  `ls 4.0G`; copying without sparse support materializes the holes. Never
  reconcile `du` against `ls -l` sums.
- **Hard links: counted once, listed once.** With `-a`, subsequent names of
  an already-counted inode are omitted entirely (not printed as `0`), which
  surprises anyone diffing `du -a` against `find` output.
- **`--exclude` filters names, not inodes.** Excluding one hard-link name
  leaves the data in the total under the other names. Patterns are base-name
  globs — `--exclude=/abs/path` does not do what it looks like it does.
- **Partial failure still writes output and exits 1.** Unreadable
  directories (root-squashed NFS, `chmod 000`) print an error per entry and
  return exit 1 *with* the totals it managed. `set -e` scripts that treat
  exit 1 as "no data" throw away good output.
- **`du` vs `df` never reconcile exactly.** Deleted-but-open files count in
  `df` and are invisible to `du`; metadata/journal/reserved blocks count in
  `df` but not `du`. A large gap plus `lsof +L1` hits means a process holds
  a deleted file open.
- **BSD/busybox deltas.** BSD `du` shares most flags but lacks
  `--exclude`/`--files0-from`; minimal busybox builds drop `--exclude`,
  `--time`, and long options. POSIX guarantees only `-a`, `-k`, `-s`, `-x`.
- **Interrupting `du` loses everything.** One pass, no checkpointing —
  Ctrl-C mid-walk means starting over; cache the `-d1` snapshot for repeated
  audits. `--time` shows the *newest file's* mtime per subtree, not the
  directory's own.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Every requested subtree was fully read and counted |
| 1 | Minor problems: unreadable directory, vanished file — output up to that point is still produced |

## Related Commands

- [`df`](./df.md) — the mount-point counterpart: free space and inode counts without walking anything.
- [`stat`](./stat.md) — the per-file primitives (`st_size`, `st_blocks`, `st_ino`) `du` aggregates.
- [`ls`](./ls.md) — `ls -s` shows allocated blocks per file; `ls -l` shows the apparent size `du` does not.
- [`truncate`](./truncate.md) — manufactures the sparse files that make the two size views diverge.
- [`numfmt`](./numfmt.md) — converts `du -B1` output to any human unit without `-h`'s rounding.
- [`sort`](./sort.md) — `sort -h` is the standard companion for ranking `-h`-scaled `du` output.
- [find](../../shell/find.md) — `find -print0 | du --files0-from=-` selects exactly what to measure.
- [xargs](../../shell/xargs.md) — batched invocation for per-file sizing on huge lists.
- [Linux filesystem internals](../../internals.md) — inodes, blocks, and hard links behind the count.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [Linux Userland Binaries](../overview.md) — the part this page belongs to.

## Interview Questions

### Q: `df` says the filesystem is 90% full but `du` on the mount point only accounts for half of it. What are your hypotheses?

Deleted-but-open files top the list: `df` reads kernel counters, `du` walks
names, and a process holding an unlinked 50 GB log keeps the blocks counted
in `df` while `du` cannot see it — `lsof +L1` or restarting the suspect
process confirms it. Other standard causes: another filesystem (or bind
mount) shadowing part of the tree, `df`-counted metadata and journal
overhead, sparse-file mismatches, and on overlayfs, host-side layers `du`'s
merged view cannot attribute.

### Q: A user insists a 4 GiB file occupies no space. Explain both mechanisms at play.

The file is sparse: `st_size` near 4 GiB but `st_blocks` near 0, because
whole regions were never written (`dd ... seek=`) or were punched out
(`fallocate --punch-hole`). `ls -l` and `du --apparent-size` report the
logical size; plain `du` reports allocated blocks — zero. Consequences:
backups and copies without sparse support materialize the full 4 GiB, while
`cp --sparse=always` and tar with `-S` preserve the holes.

### Q: Why does `du` report a directory of hard-linked files as smaller than the sum of the files' sizes, and how do you get the larger number?

`du` keys counted files on `(st_dev, st_ino)`, so an inode with N links
contributes its blocks exactly once — which is the truth about disk usage.
`du -l` (`--count-links`) disables that dedup and adds the size once per
name, approximating what a naive copy would consume. Follow-up: `du -a`
lists only the first-encountered name of each inode, which is why `du -a`
line counts don't match `find | wc -l` on linked trees.

### Q: `du -sh` on an NFS-mounted home directory takes 40 minutes. What do you do?

Recognize the cost model first: one stat round-trip per file means millions
of files are millions of RPCs, and `-h`/`--apparent-size` change nothing
about that. Mitigations: run `du` on the fileserver itself; prune branches
with `--exclude` so they are never stat'ed; scope with `-x`; pre-select
paths with `find -print0 | du --files0-from=-` when only some subtrees
matter. If the answer is "cache it or schedule it", that is also correct —
`du` has no incremental mode.

### Q: Inside a container, `du -sh /` reports far less than the host's `df` for the same container. Why?

`du` sees the overlay's merged view of visible files, while the host's `df`
covers the whole overlay device including upperdir metadata, lowerdir
layers, whiteouts of deleted files, and everything else sharing that device.
Add `-x` semantics on top: volumes and tmpfs are different `st_dev` values,
so `du -x /` skips data a host-side audit would count. When the question is
image footprint, image-layer analysis (`docker history`) is the real tool.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/du.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — du](https://pubs.opengroup.org/onlinepubs/9699919799/)
