# rmdir — Remove empty directories only

## Overview

`rmdir` deletes directories, and nothing else — a directory must be empty
(no files, no subdirectories, not even hidden dotfiles) or the call fails.
That restriction is its feature: `rmdir` can never cascade into deleting
data, which makes it the safe tool for pruning directory skeletons,
cleaning up empty trees after a move, and scripting "remove if empty"
logic without guarding against accidents.

It ships in Debian package `coreutils` and lives at `/usr/bin/rmdir` on
modern Debian/Ubuntu systems. The tool is as old as Unix directory trees
themselves and is POSIX-standardized, so its behavior — including the
strict "empty only" rule — is identical across GNU, BSD, and busybox
implementations apart from the GNU extras (`-p`, `--ignore-fail-on-non-empty`,
`-v`).

`rmdir` is often confused with `rm -r` (which empties *and* removes) and
with `rm -d` (which is exactly `rmdir` re-implemented as an `rm` option).
Its niche is deliberate: remove the shell of a directory once its contents
are already gone.

| Field | Value |
|---|---|
| Package | coreutils (Debian bookworm) |
| Section (man) | 1 — User Commands |
| Path | /usr/bin/rmdir |
| First appeared / lineage | first editions of AT&T Research Unix (early 1970s); GNU implementation in GNU coreutils |
| Standards | POSIX 2018 (rmdir utility) |

## Synopsis

```
rmdir [OPTION]... DIRECTORY...
```

```bash
rmdir empty/                       # remove one empty directory
rmdir dir1 dir2 dir3               # remove several; stop reporting at first failure
rmdir -p a/b/c                     # remove c, then b, then a — any that become empty
rmdir --ignore-fail-on-non-empty a/b/c   # tolerate non-empty levels while pruning
```

## How It Works

`rmdir` performs one `rmdir(2)` system call per operand. The kernel
refuses the call with `ENOTEMPTY` (or `EEXIST`) unless the directory
contains nothing but the two fixed entries `.` and `..`. Because the
check is done atomically in the kernel — not by listing and comparing —
there is no race window where a file created between a check and the
removal would silently disappear with it:

```
   rmdir(2) decision path
   ┌─────────────────────────────┐
   │ is operand a directory?     │──no──► ENOTDIR
   ├─────────────────────────────┤
   │ is it empty (only . ..) ?   │──no──► ENOTEMPTY / EEXIST
   ├─────────────────────────────┤
   │ may we write to its parent? │──no──► EACCES / EPERM
   ├─────────────────────────────┤
   │ remove entry, free inode    │──ok──► exit 0
   └─────────────────────────────┘
```

Note the third check: deleting a directory requires write + execute
permission on its **parent**, not on the directory itself. An empty,
mode-000 directory is removable; a mode-777 directory inside a read-only
parent is not.

### The -p chain walk

`-p` ("parents") removes the operand, then each ancestor that has just
become empty, walking upward until one refuses:

```bash
$ mkdir -p a/b/c && rmdir -pv a/b/c
rmdir: removing directory, 'a/b/c'
rmdir: removing directory, 'a/b'
rmdir: removing directory, 'a'
```

The moment an ancestor is non-empty (or does not exist, or is a symlink),
the walk stops there with an error — which is why
`--ignore-fail-on-non-empty` exists. With it, `rmdir -p` becomes a
pruning tool: "walk up as long as levels are empty, don't complain once
they are not":

```bash
$ mkdir -p a/b/c && touch a/keep.txt
$ rmdir -p --ignore-fail-on-non-empty a/b/c
$ ls a            # 'a' survived because it still holds keep.txt
keep.txt
```

### Relationship to other removal tools

```
                  does it delete file data?
                       │yes              │no
                       ▼                 ▼
                 rm [-r] [-f]         rmdir
                 (tree removal)      (empty dirs only)
                       │                 │
            rm -d = rmdir re-exported as an rm option
```

`rm -d emptydir` and `rmdir emptydir` are equivalent; `rm -r dir` will
happily destroy a full tree, which is precisely what `rmdir` cannot do.

## Options That Matter

| Option | Effect |
|---|---|
| `-p`, `--parents` | remove DIRECTORY, then each ancestor that becomes empty |
| `--ignore-fail-on-non-empty` | suppress the error (and the failure) when a directory still has contents |
| `-v`, `--verbose` | print a line per directory processed |

There are no permission, owner, or filter options — by design the tool
has exactly one behavior.

## Usage Patterns

```bash
# Safe cleanup: delete empty build directories without touching data
find . -type d -name 'obj*' -empty -exec rmdir {} +
```

```bash
# Prune an empty directory chain left by a packaging step
rmdir -p --ignore-fail-on-non-empty usr/local/lib/myapp
```

```bash
# "Remove if empty" idiom in scripts — rely on the exit status, not a test
if rmdir "$LOCK_DIR" 2>/dev/null; then
  echo "lock released"
fi
```

```bash
# Unmount-and-remove pattern for mountpoint directories
umount /mnt/iso && rmdir /mnt/iso
```

```bash
# Batch removal where some operands may legitimately be non-empty
rmdir --ignore-fail-on-non-empty /tmp/jobs/*/ || true
```

```bash
# Verify a tree is fully empty before removing its root (audit-friendly)
find tree -mindepth 1 | head; rmdir tree
```

```bash
# Undo a mkdir -p in a test teardown
rmdir -p "$TMP/a/b/c" 2>/dev/null || true
```

```bash
# Show what is happening when auditing a cleanup script's behavior
rmdir -v logs/2024/q1 logs/2024/q2
```

```bash
# Guard against NFS ghosts: list -A before concluding a directory is empty
ls -A "$d" || true; rmdir "$d" 2>/dev/null || echo "$d not empty or in use"
```

```bash
# Tear down a scratch tree but keep the top-level mount point
rm -rf "$WORK"/* ; rmdir -p --ignore-fail-on-non-empty "$WORK/sub/deep" 2>/dev/null
```

## Nuances and Gotchas

- **Hidden files make directories non-empty.** `.gitkeep`, `.nfsXXXX`
  ghosts on NFS, and editor droppings like `.#file` all block removal.
  `ls` without `-A` hides them — use `ls -A dir` before blaming the tool.
- **`-p` semantics surprise people.** Without
  `--ignore-fail-on-non-empty`, `rmdir -p a/b/c` exits nonzero the first
  time an ancestor refuses, even though `c` was already removed; partial
  success still yields a failing exit status.
- **Absolute operands make `-p` climb all the way up.** A relative operand
  stops at the current directory (`dir_name("a")` is `.`, and `.` is never
  removed), but `rmdir -p /tmp/rvx/a/b/c` will attempt `/tmp/rvx`, then
  `/tmp`, then `/` itself — every attempt fails on non-empty levels, but
  the walk does not know your intended root. Root-owned scripts should
  name the lowest component and let `-p` stop there via a deliberate
  non-empty parent.
- **Ancestors that are symlinks fail.** `rmdir -p` errors if an
  intermediate level is a symlink (`ENOTDIR`), which is correct but
  confusing when a path like `lib -> /usr/lib` sits in the chain.
- **No `-f` exists.** Unlike `rm`, there is no force flag; scripts must
  use `--ignore-fail-on-non-empty` for the "don't care" case and shell
  redirection for the "quiet" case.
- **Permission model.** Removal needs write+search on the parent
  directory; the sticky bit on a shared parent (e.g. `/tmp`) additionally
  requires ownership of the directory or of the parent.
- **busybox differences.** busybox `rmdir` supports `-p` and
  `--ignore-fail-on-non-empty` but not always `-v`; POSIX defines only
  `-p`, so portable scripts should not depend on verbose output.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | every operand was removed successfully |
| 1 | any operand failed: non-empty, missing, not a directory, permission denied, or usage error |

With multiple operands, removal continues past failures; the exit status
still reports the first error class encountered.

## Related Commands

- [`rm`](./rm.md) — full tree removal; `rm -d` is the rmdir-equivalent option
- `mkdir` (not covered here) — creates the directories rmdir removes; `rmdir -p` mirrors `mkdir -p`
- [`unlink`](./unlink.md) — same one-entry-at-a-time philosophy for files
- [Collection overview](./overview.md) — all pages in the GNU Coreutils collection

## Interview Questions

### Q: Why would a script use `rmdir` instead of `rm -r` for cleanup?

`rmdir` is structurally incapable of deleting data, so an empty-directory
cleanup pass cannot destroy anything by mistake — wrong glob, race, or
bad variable notwithstanding. It is also a cheap atomic test: "rmdir as a
lock" is a classic pattern because the kernel guarantees only one caller
wins. `rm -r` belongs where content deletion is the explicit intent.

### Q: What conditions make `rmdir(2)` fail, and which permission matters?

Failures: the operand is not a directory (`ENOTDIR`), it still contains
entries (`ENOTEMPTY`/`EEXIST`), the caller lacks write+execute on the
*parent* (`EACCES`), or a sticky-bit parent is owned by someone else
(`EPERM`). The parent's permissions matter, not the directory's own
mode — an empty mode-000 directory is trivially removable by its
parent's writer.

### Q: Explain exactly what `rmdir -p a/b/c` does when `a` contains a file.

It removes `c`, then `b` (now empty), then attempts `a`, fails with
"Directory not empty", and exits nonzero — the earlier removals stand.
Adding `--ignore-fail-on-non-empty` turns that failure into silence,
making the command a pure "prune empty tail of this path" operation.
Without the flag, partial success is indistinguishable from total
failure by exit status alone.

### Q: An NFS directory looks empty but rmdir says it is not. What is happening?

The directory almost certainly holds an `.nfsXXXXXX` silly-rename ghost:
another client has the file open, so the server renamed it instead of
deleting it, and it remains a real directory entry. `ls -A` reveals it.
The ghost disappears when the holder closes the file; deleting it by
force just produces another ghost until then.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/rmdir.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
