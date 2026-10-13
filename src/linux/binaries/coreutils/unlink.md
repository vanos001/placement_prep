# unlink — remove a file by calling the unlink system call

## Overview

`unlink` removes exactly one file by calling the `unlink(2)` system call —
nothing more. No options, no recursion, no prompting, no globbing of its
own, no `-f` to silence errors. It is the thinnest possible command-line
wrapper around the kernel operation that deletes a directory entry and
decrements the file's link count.

It ships in the Debian `coreutils` package at `/usr/bin/unlink` and is
POSIX-standardized. Its niche is precision: scripts that must delete a
single known path and *fail loudly* if that fails — atomic-replace
bookkeeping, stale lockfile cleanup, `trap` handlers — reach for `unlink`
because `rm`'s convenience features (recursion, `-f`, alias-driven prompts)
are exactly the behaviours a careful script does not want.

It is often confused with `rm` (the general-purpose remover) and with
`rename`-based atomic replacement (which `unlink` alone cannot provide).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/unlink` |
| First appeared / lineage | Unix v1-era `rm`/`unlink` split; in GNU coreutils |
| Standards | POSIX.1-2017 |

## Synopsis

```text
unlink FILE
```

```bash
unlink /tmp/lockfile        # remove one path, period
unlink /tmp/stale-link      # removes the symlink, never its target
```

## How It Works

A Unix file's data survives until its link count reaches zero *and* no
process holds it open. `unlink(2)` performs the first half: it removes one
directory entry (name) and decrements the inode's link count. When the
count hits zero and the last open descriptor closes, the kernel frees the
inode and data blocks. `unlink` the command simply marshals one path
argument into that syscall.

```text
   before                        unlink("/tmp/data")         after
┌──────────────┐            ┌─────────────────────┐   ┌──────────────┐
│ dir /tmp     │            │ remove dir entry    │   │ dir /tmp     │
│  data → 4210 │  ────────▶ │ inode 4210 count    │──▶│  (no 'data') │
│ inode 4210: 3 links       │ 3 → 2               │   │ inode 4210: 2 links
│ (hard links elsewhere survive)                        │
└──────────────┘            └─────────────────────┘   └──────────────┘
```

Consequences that follow directly from the syscall semantics:

```bash
$ echo x > /tmp/target; ln -s /tmp/target /tmp/lnk
$ unlink /tmp/lnk          # the symlink itself, not /tmp/target
$ cat /tmp/target          # target untouched
x
```

Directories are refused: `unlink(2)` on a directory fails (`EISDIR` on
Linux); the dedicated syscall for directories is `rmdir(2)`, which `rm`
uses internally. Deleting a name requires **write permission on the
containing directory** (plus, on sticky directories like `/tmp`, ownership
of the file or the directory) — not write permission on the file itself, a
permission model surprise that predates this utility.

The practical payoff of such a minimal tool is failure honesty. There is no
`-f`, so every failure surfaces:

```bash
$ unlink /tmp/no-such-file
unlink: cannot unlink '/tmp/no-such-file': No such file or directory
$ echo $?
1
```

## Options That Matter

| Option | Effect |
|---|---|
| (none) | Only `--help` and `--version` exist; there are no operational flags |

Exactly one operand is accepted; a second is a usage error. If a shell glob
expands to several names, `unlink` rejects the invocation rather than
guessing — the shell expands globs *before* unlink runs, so `unlink *.log`
with multiple matches is an error, which is usually the safety property the
script author wanted.

## Usage Patterns

```bash
# Precise single-file removal in a script — no aliases, no prompts, no -f
unlink "$WORKDIR/result.tmp"
```

```bash
# Stale lockfile cleanup on startup
[ -f /var/run/myjob.lock ] && unlink /var/run/myjob.lock
```

```bash
# trap-based temp cleanup that can never over-delete
TMP=$(mktemp /tmp/job.XXXXXX)
trap 'unlink "$TMP"' EXIT
```

```bash
# Atomic-ish publish: write to temp, then swap names with mv (rename(2))
( generate > "$DIR/.draft" ) && mv -f "$DIR/.draft" "$DIR/published"
```

```bash
# Rotating a single file without rm's option parsing
unlink /var/log/app.log.9
```

```bash
# Removing a dangling symlink safely (never follows the link)
unlink /var/run/service.pid   # if it happens to be a symlink, still fine
```

```bash
# Fail-loud deletion where rm -f would hide a path bug
unlink "$DIR/$FILE" || { echo "cleanup failed for $DIR/$FILE" >&2; exit 1; }
```

```bash
# Deleting one entry from a generated list, one call per name (xargs -n1)
find . -name '*.partial' -print0 | xargs -0 -n1 unlink
```

## Nuances and Gotchas

- **Globs are a shell thing.** `unlink *.tmp` passes every match as
  separate operands and fails on the first extra one. This surprises people
  who expect rm-like glob handling; it is also the guardrail that makes
  unlink safe in scripts.
- **Deleted-but-open files keep consuming space.** If a process holds the
  file open (a log being written), unlinking succeeds but the disk is freed
  only when the descriptor closes — the classic "df says full, du says
  empty" mystery with fat log files.
- **No `-f`, no `-r`, no prompts.** Removal of a read-only file succeeds if
  the *directory* is writable — permission checks target the directory, not
  the file. Conversely, unwritable directory means failure with a clear
  errno message.
- **Directories always fail** with `EISDIR`; use `rmdir` (or `rm -d`) for
  empty directories. Nothing in unlink will recurse, ever.
- **Atomic replacement is rename's job.** `unlink` + recreate is a
  two-step window where readers see no file; the atomic pattern is
  write-to-temp + `mv` (which calls `rename(2)`). Unlink belongs to the
  cleanup half of such schemes.
- **NFS and sticky-bit oddities**: deleting an open file on NFS can leave
  `.nfsXXXX` zombies, and on sticky directories (`/tmp`) you can only
  unlink files you own — both are kernel behaviours, not unlink options.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | The file was unlinked successfully |
| 1 | Failure: nonexistent path, permissions, directory operand, wrong argument count |

Diagnostics come verbatim from errno via coreutils' standard error
formatting, which is why the failure message is as precise as the syscall.

## Related Commands

- [`true`](./true.md) — the exit-status contract style (0 on success, nonzero diagnostics) unlink follows.
- [`timeout`](./timeout.md) — bounds cleanup loops that repeatedly unlink lockfiles.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: What is the difference between unlink and rm, and when does the difference matter?

`rm` is the user-facing remover: globs, `-r` for trees, `-f` to suppress
errors, `-i` prompting, and internal delegation to `rmdir` for directories.
`unlink` is one syscall with one operand and no flags. The difference
matters in scripts: unlink fails loudly on any surprise (extra operand,
missing file), which converts silent cleanup bugs into visible errors;
`rm -f` in a script can hide path bugs that delete the wrong file *or* fail
to delete at all.

### Q: Explain what happens to file data when you unlink an open file.

The directory entry disappears immediately — new opens fail with ENOENT —
but the inode's link count simply drops; data blocks are freed only when
the link count reaches zero *and* the last open file descriptor closes.
Processes with the file open continue reading and writing a file that no
longer has a name. This is the mechanism behind both the
"deleted the log but disk stayed full" mystery and the
create-temp-then-unlink-while-open pattern used for scratch files.

### Q: Why does deleting a file sometimes require no permission on the file itself?

Unlinking modifies the *directory* (removing an entry), so the kernel
checks write (and search) permission on the containing directory, not the
file. On directories with the sticky bit set (`/tmp`), an additional rule
applies: only the file's owner, the directory's owner, or root may unlink a
given entry. File mode bits like `-w` are irrelevant to whether the name
can be removed.

### Q: Describe the atomic file-replacement pattern and where unlink fits.

Write the new content to a temporary file in the same directory, fsync it,
then `mv` it over the target — `rename(2)` replaces the directory entry
atomically, so readers see either the old or the new file, never a partial
one. `unlink` is not part of the atomic step itself; it handles the
surrounding bookkeeping: removing stale temporaries, old rotated
generations, and failed drafts. Using `unlink` + recreate for the swap
instead of rename would expose a window with no file at all.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/unlink.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
