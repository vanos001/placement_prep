# link — hard link creation via the raw link(2) syscall

## Overview

`link` is the thinnest utility in coreutils: it wraps the `link(2)` syscall
(one call, no fallbacks, no post-processing) to create a second directory
entry — a hard link — that refers to the same inode as an existing file.
It takes exactly two path operands and essentially no options: there is no
`-f` to force, no `-s` for symbolic links, no `-i` to prompt. If the second
name already exists, the syscall fails with `EEXIST` and that is the whole
story. This refusal to overwrite is exactly why some scripts prefer `link`
over `ln`: an accidental `link important.db backup.db` can never clobber
`backup.db`.

It ships in the Debian `coreutils` package on bookworm and lives at
`/usr/bin/link` on modern merged-`/usr` systems. You reach for it when you
need a hard link and want the operation to be explicit and fail-closed, or
when teaching scripts what `ln` is actually doing underneath. It is often
confused with `ln` (the general-purpose linking tool, also in coreutils)
and with `symlink`/`readlink` (its soft-link siblings).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/link` |
| First appeared | early AT&T Unix; standalone `link(2)` wrapper |
| Standards | POSIX 2018 utility; kernel interface `link(2)`/`linkat(2)` |

## Synopsis

```
link FILE1 FILE2
link OPTION
```

Main forms:

```
link data.db data.db.2        # new name data.db.2 -> same inode as data.db
link --help                   # usage text
link --version                # version information
```

There are no other forms. No mode flags, no recursion, no environment
sensitivity beyond locale for error messages.

## How It Works

`link` resolves both operands, calls `link(2)` (or `linkat(2)` on modern
glibc without `AT_SYMLINK_FOLLOW`), reports any error, and exits. The
syscall itself is the atomic unit: the kernel inserts a directory entry
pointing at the existing inode and bumps its link count. There is no
window where the destination exists with partial content — either the new
name appears complete, or the syscall returns an error and nothing changes.

```bash
# Two names, one inode: link count goes 1 -> 2
$ echo hi > f.txt && link f.txt h.txt
$ ls -li f.txt h.txt
269436 -rw-rw-r-- 2 z z 3 Oct  9 09:33 f.txt
269436 -rw-rw-r-- 2 z z 3 Oct  9 09:33 h.txt
```

The inode number (first column) is identical and the link count is `2`.
Both names are peers: there is no "original" — metadata (permissions,
owner, timestamps, contents) lives on the inode and is shared. Removing
one name with `rm` just decrements the count.

```bash
# Failure modes are all pre-checked by the kernel, never resolved by flags
$ link f.txt f.txt
link: cannot create link 'f.txt' to 'f.txt': File exists
$ touch e1 e2 && link e1 e2
link: cannot create link 'e2' to 'e1': File exists
$ mkdir dd && link dd out
link: cannot create link 'out' to 'dd': Operation not permitted
$ link /nope /nope2
link: cannot create link '/nope2' to '/nope': No such file or directory
```

Key kernel-level restrictions that `link` inherits verbatim:

```
                +---------------------------+
  FILE1 source  | regular file / any file   |
                | (same filesystem only)    |
                +------------+--------------+
                             |
                     link(2) atomic
                             |
                +------------v--------------+
  FILE2 target  | must NOT exist            |
                | must be on same fs        |
                | directory part must exist |
                +---------------------------+
```

- **Directories cannot be linked.** Hard-linking directories would allow
  cycles in the filesystem tree; `EPERM` is returned (even for root, on
  modern kernels — historically only `superuser` could, and `fs.protected_hardlinks`
  plus common sense keep it closed).
- **Cross-device links fail** with `EXDEV`. An inode lives on exactly one
  filesystem; a name on another mount point cannot reference it.
- **The destination must not exist.** No `O_TRUNC`-style surprises, no
  rename semantics — that is `mv`'s job, not `link`'s.
- **Symlink behavior:** on Linux, `link` creates a link to the symlink
  inode itself (does not follow), matching `linkat()` without
  `AT_SYMLINK_FOLLOW`. POSIX leaves this unspecified for `link(1)`, so
  portable scripts avoid hard-linking symlinks entirely.

`ln` with no options produces the same result for the plain file case; the
difference is policy, not mechanics. `ln` grows flags (`-f`, `-s`, `-i`,
`-b`, `-L`, `-P`, `-T`, `-v`), which is convenient interactively and
dangerous in scripts precisely because `-f` can destroy data.

## Options That Matter

There are no behavior options — only the two GNU-standard informational ones:

| Option | Effect |
|---|---|
| `--help` | Print usage and exit |
| `--version` | Print version and exit |

That is the entire surface. Any other argument is treated as one of the two
file operands, so quoting mistakes become syscall errors, not silent
misbehavior. Compare `ln`, whose option parsing (`ln -s -f -T ...`) must be
audited before you can predict what a command line does.

## Usage Patterns

```bash
# Create an atomic "marker" that shares content with a status file
link /var/lib/service/running /var/run/service.marker
```

```bash
# Space-efficient snapshot before an in-place edit (same fs, same inode)
link config.toml config.toml.pre-edit && nano config.toml
```

```bash
# Fail-closed deduplication step in a backup script: refuse to overwrite
link "$src" "$dst" 2>/dev/null || echo "dst exists or cross-device: $dst"
```

```bash
# Verify two paths are the same inode (link count trick, no stat dependency)
ls -i "$a" "$b" | awk '{print $1}' | uniq -d
```

```bash
# Crash-safe append log rotation: readers keep the old inode while the
# writer switches to a fresh file
link app.log app.log.1 && : > app.log
```

```bash
# Guard against the classic ln trap: this can NEVER truncate the target
link "$1" "$1.bak" || exit 1
```

```bash
# Reference-count a cache entry: drop the link, inode dies with last name
link "$cache_dir/blob" "$work_dir/blob"   # checkout
rm "$work_dir/blob"                        # release
```

```bash
# Pair with find to hardlink duplicates reported by fdupes-like tools
# (only within one filesystem — see Gotchas)
link "$orig" "$dup" 2>/dev/null && rm "$dup_done_marker"
```

## Nuances and Gotchas

- **`link` never overwrites, `ln` might.** `ln a b` also refuses when `b`
  exists, but scripts accumulate `-f` over time. `link` has no `-f` to
  abuse; reviewers can grep for it and know the semantics instantly.
- **Cross-filesystem failure is the #1 production surprise.** `/home` and
  `/tmp` on different mounts → `EXDEV` ("Invalid cross-device link").
  Unlike `mv` or `cp`, `link` has no fallback: hard links are an inode
  relationship, not a copy.
- **Directories are always refused**, even as root. If you think you need
  a directory hard link, you want a symlink or a bind mount (`mount --bind`).
- **Symlink semantics differ between implementations.** GNU `link` links
  the symlink inode itself; BSD `link` historically followed symlinks;
  POSIX calls the result unspecified. Portable code: `readlink -f` first,
  then link the resolved path.
- **No diagnostic of *why* beyond errno.** `EPERM` can mean a directory
  source, `fs.protected_hardlinks` sysctl (linking files you don't own in
  world-writable dirs), or a filesystem that forbids hard links (FAT, some
  network filesystems, sshfs).
- **Exit code is binary.** `0` or `1` (plus `125`-style wrapper codes only
  if a run-command wrapper is involved). Scripts checking `2` or `>1` are
  wrong.
- **Busybox `link` exists** on minimal images and matches the two-operand
  form, but test error messages before parsing them.
- **Link counts are per-inode, not per-name-content.** Editors that save
  via rename (`vim`, `sed -i`) silently break hard links: the new file is
  a fresh inode. `link`-based "snapshots" must account for that.

## Exit Status

| Code | Meaning |
|---|---|
| `0` | Link created successfully |
| `1` | Any failure: missing operand, `EEXIST`, `EPERM`, `EXDEV`, `ENOENT`, bad usage |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./printf.md`](./printf.md) — same "scripting primitive, no surprises" philosophy.
- [`./pathchk.md`](./pathchk.md) — validate pathname shape before syscall-heavy scripts.
- [`../../shell/bash.md`](../../shell/bash.md) — scripting idioms where fail-closed primitives pay off.

## Interview Questions

### Q: What does `link file1 file2` do that `ln file1 file2` does not?

Nothing at the kernel level — both end in `link(2)`. The difference is
surface area: `link` has no options, so it cannot force, follow, symlink,
or overwrite. It is the "weakest tool that can do the job," which makes it
predictable in scripts: if `file2` exists the command fails and nothing on
disk changes.

### Q: Why can't you hard link a directory?

Directory hard links would let the filesystem graph form cycles and would
make `..` ambiguous — the kernel could no longer guarantee a tree. `link(2)`
returns `EPERM` for directories on modern Linux even for root. Bind mounts
achieve the same goal (a directory visible at two paths) at the mount layer.

### Q: A script runs `link /tmp/a /home/b/a` and fails. Why, and what are the escape hatches?

`/tmp` and `/home` are presumably different filesystems, and an inode can
only be referenced by names on its own filesystem, so the kernel returns
`EXDEV`. Options: link within the same filesystem, copy (`cp -al` clones a
tree as hard links when it works), or use bind mounts. `mv` hides this
because it degrades to copy+delete, which `link` deliberately never does.

### Q: You hard-linked `report.txt` to `report.txt.bak`, then ran `sed -i` on `report.txt`. Is the backup still a backup?

No. `sed -i` creates a new file and renames it over the original name, so
`report.txt` now refers to a fresh inode while `report.txt.bak` keeps the
old contents and old inode — which here happens to be what you wanted, but
the two files are no longer linked. Editors like `vim` behave the same way;
understanding "names point at inodes, save-by-rename replaces the pointer"
is the point of the question.

### Q: What error do you get linking to an existing destination, and what exit code?

The kernel returns `EEXIST` and the utility prints
`link: cannot create link 'dest' to 'src': File exists` and exits `1`.
There is no `--force`. This fail-closed behavior is the main argument for
using `link` in automation where an existing destination means something
went wrong and silence would be a bug.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/link.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — link](https://pubs.opengroup.org/onlinepubs/9699919799/)
