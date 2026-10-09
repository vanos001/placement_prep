# rm — Remove files and directories by unlinking them

## Overview

`rm` deletes directory entries. Despite the everyday phrasing "delete a
file", `rm` never erases file data; it unlinks the *name* from a directory
and lets the kernel decide when the inode and its data blocks are actually
reclaimed. That distinction — name vs inode vs data — explains nearly every
surprising behavior of `rm`: files that stay open after being removed, space
that does not come back, and the impossibility of undeleting.

It ships in Debian package `coreutils`, lives at `/usr/bin/rm` on modern
Debian/Ubuntu systems, and is one of the oldest Unix utilities, dating to
the first editions of Research Unix. It is POSIX-standardized, so its
core behavior (including the need for `-r` before removing directories) is
portable across GNU, BSD, and busybox implementations.

`rm` is often confused with `unlink` (the one-argument wrapper around the
system call), `rmdir` (empty directories only), and `shred` (which
overwrites data *before* unlinking). The single most important safety
concept is that recursive deletion is a tree walk executed with your
permissions — there is no trash can, no undo, and only one built-in
failsafe (`--preserve-root`) between you and a wiped filesystem.

| Field | Value |
|---|---|
| Package | coreutils (Debian bookworm) |
| Section (man) | 1 — User Commands |
| Path | /usr/bin/rm |
| First appeared / lineage | first editions of AT&T Research Unix (early 1970s); GNU implementation in GNU coreutils |
| Standards | POSIX 2018 (rm utility) |

## Synopsis

```
rm [OPTION]... [FILE]...
```

```bash
rm file.txt                    # unlink a file
rm -r dir/                     # recursive: directory and everything below
rm -rf --one-file-system /mnt/oldroot   # aggressive, bounded to one filesystem
rm -d emptydir/                # like rmdir: only if empty
rm -I -r build/                # prompt once before large/recursive removal
```

## How It Works

### The unlink call chain

For a regular file, `rm` issues `unlinkat(2)` (or `unlink(2)`). The system
call removes one directory entry and decrements the inode's hard-link
count. Nothing else happens immediately:

```
   before                          after rm file.txt
┌──────────────────────┐        ┌──────────────────────────┐
│ dir entry:           │        │ (entry gone)             │
│   "file.txt" -> 42   │  rm    │                          │
├──────────────────────┤ ─────► ├──────────────────────────┤
│ inode 42: nlink=1    │ unlink │ inode 42: nlink=0        │
│   blocks: [a b c]    │        │   blocks: [a b c]        │
├──────────────────────┤        ├──────────────────────────┤
│ data on disk         │        │ data still on disk       │
└──────────────────────┘        └──────────────────────────┘

inode 42 + blocks are freed only when:
   nlink == 0  AND  no process holds the file open
   (open fd, mmap, or the file as cwd/executable)
```

That "open file survives unlink" property is a feature: processes never
see their files yanked away mid-read. It is also why a log file removed
while a daemon keeps writing it does not return space — the daemon holds
an fd, so the inode lives on (the classic `du` vs `df` mismatch). Fix it
by restarting the writer or by truncating (`: > file` or `truncate -s 0`)
instead of removing.

### Recursive removal

`rm -r` walks the tree depth-first using the `fts` library, deleting
children before their parents, so `rmdir` succeeds at each level:

```bash
$ find t -print 2>/dev/null | sort
t
t/a.txt
t/sub
t/sub/b.txt
$ rm -rv t
removed 't/a.txt'
removed directory 't/sub'
removed 't/sub/b.txt'
removed directory 't'
```

Note the post-order: contents first, then the directory itself. `rm` uses
`unlinkat` for non-directories and `rmdir` for directories; a directory
that becomes non-empty *during* the walk (a racing writer) fails that
level only.

Symlinks encountered during recursion are unlinked, never followed —
`rm -r` will not climb out of a tree through a symlinked directory.
Command-line arguments are the exception the `-H/-L/-P`-style rules govern
in other coreutils tools; `rm` does not traverse symlink arguments at all.

### Safety rails

`rm` has exactly three prompt styles and one structural failsafe:

- default: no prompts at all (silence is a design decision, not a bug)
- `-i`: prompt before every removal
- `-I`: prompt once if removing more than three files, or always when
  recursive — the recommended middle ground for interactive shells
- `--preserve-root` (default): refuse to recurse into `/` itself. The
  kernel cannot stop `rm -rf /`; only this convention can, and it is
  defeated by `--no-preserve-root`:

```bash
$ rm -rf /
rm: it is dangerous to operate recursively on '/'
rm: use --no-preserve-root to override this failsafe
$ echo $?
1
```

The failsafe does not stop near-misses such as `rm -rf /usr`: only the
literal root is protected. `rm -rf /*` happily expands the glob and deletes
everything *under* `/`, because each argument is a separate path.
`--preserve-root=all` (GNU extension) additionally refuses
command-line arguments that live on a different filesystem from their
parent, which contains some cross-mount accidents.

### What removal does NOT do

`rm` does not shred, wipe, or randomize. The data blocks are released to
the filesystem free list and their contents linger until overwritten by
later allocation. On copy-on-write filesystems and SSDs, old copies and
worn remaps can persist even longer (see `shred` for why, and for the
limits of in-place overwriting). If deletion must mean "data is gone",
the design answer is encryption with key destruction — not `rm`.

## Options That Matter

| Option | Effect |
|---|---|
| `-f`, `--force` | ignore nonexistent operands, never prompt; suppresses "No such file" errors |
| `-r`, `-R`, `--recursive` | remove directories and their contents recursively |
| `-d`, `--dir` | remove empty directories (rmdir-equivalent) |
| `-i` | prompt before every removal |
| `-I` | prompt once if >3 files or when recursive |
| `--interactive=WHEN` | never / once / always — spell out the prompt policy |
| `-v`, `--verbose` | print each removal as it happens |
| `--one-file-system` | during recursion, skip directories on other filesystems |
| `--preserve-root` | default: refuse recursive removal of `/` |
| `--preserve-root=all` | also refuse operands on a different device from their parent |
| `--no-preserve-root` | disable the root failsafe (mostly used by OS installers) |

### Option combinations worth memorizing

```bash
rm -rf dir/        # no prompts, ignore missing — the dangerous default of scripts
rm -rI  dir/       # one confirmation, still errors on missing
rm -rfv dir/       # verbose: the audit trail you wish you had captured
```

## Usage Patterns

```bash
# Remove a file and never care whether it existed (idempotent cleanup)
rm -f /var/run/app.pid
```

```bash
# Clean a directory's contents but keep the directory itself
rm -rf /tmp/build/* /tmp/build/.[!.]*
```

```bash
# Delete everything older than 30 days from a spool (find composes better than globs)
find /var/spool/mail -type f -mtime +30 -delete
```

```bash
# Interactive-by-default alias to stop fat-fingered recursion
alias rm='rm -I'
```

```bash
# Remove only files, keep directory structure (find + rm batch)
find . -name '*.pyc' -type f -exec rm -v {} +
```

```bash
# Nuke a chroot's old root without crossing into /proc or /dev bind mounts
rm -rf --one-file-system /mnt/oldroot
```

```bash
# Delete a file whose name begins with a dash (never rm - -foo; use --)
rm -- -foo
rm ./-foo
```

```bash
# Free space held by a still-open log file without restarting the daemon
: > /var/log/app/debug.log        # truncate, not rm
```

```bash
# Dry-run habit: list before you delete with the same glob
echo rm -rf build-[0-9]*/         # echo expands the glob exactly as rm would see it
```

```bash
# Remove empty directories left behind after a cleanup pass
find . -depth -type d -empty -exec rmdir {} \;
```

## Nuances and Gotchas

- **Space does not return while the file is open.** Removed-but-open files
  are invisible in directory listings yet still occupy space; find them via
  `/proc/*/fd` (fd links shown as `(deleted)`) or `lsof +L1`. This is the
  number-one "I deleted the log but `df` did not improve" scenario.
- **No undelete.** There is no recycle bin and no inode resurrection tool
  in general use. ext4 erases the inode structure, and on SSDs the TRIM
  path may release blocks long before recovery software would look at
  them. Recovery is backups and snapshots; plan accordingly.
- **Unquoted or empty variables are catastrophic.** `rm -rf "$DIR/"*` with
  `DIR` empty becomes `rm -rf /*`-adjacent behavior; `rm -rf $DIR/*`
  unquoted word-splits on spaces. Prefer `rm -rf -- "${DIR:?}/"*`, which
  aborts if `DIR` is unset or empty.
- **`-f` hides two different failures.** It suppresses nonexistent-file
  errors (intended) and permission-denied prompts (rarely intended).
  Scripts checking exit status should not assume `-f` turned a real
  failure into success — errors other than ENOENT still surface.
- **NFS silly rename.** On NFS servers, removing a file that some client
  still holds open cannot complete, so the server renames it to
  `.nfsXXXXXX` until the last close. These ghosts show up in listings,
  keep space allocated, and vanish on their own — do not "clean them up"
  while the owning process runs.
- **Trailing slashes and glob misses.** `rm -r dir/` and `rm -r dir` are
  equivalent, but `rm -r dir/*` misses dotfiles; `dir/.[!.]*` catches
  most of them. A glob that matches nothing is passed through literally
  when `nullglob` is off, producing a confusing "No such file" error.
- **`.` and `..` are always refused.** Any attempt to remove a final
  component of `.` or `..` fails with a diagnostic — a guard inherited
  from the kernel's rule that directories cannot shrink below empty.
- **Portability.** `-I`, `--one-file-system`, and `--preserve-root=all`
  are GNU extensions; busybox `rm` implements a subset and BSD `rm` has
  different prompt flags. Core scripts should stick to POSIX `-f`, `-i`,
  `-r`, `-d`.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | every operand was removed (or did not exist under `-f`) |
| 1 | some removal failed: missing file, EPERM, traversal error, usage error, or the root failsafe fired |

The GNU manual also reserves 2 for serious trouble; in practice nearly all
interactive failures, including unreadable-directory recursion errors,
report 1. When any operand fails, remaining operands are still processed.

## Related Commands

- [`shred`](./shred.md) — overwrite file data before the unlink
- [`rmdir`](./rmdir.md) — remove strictly empty directories
- [`unlink`](./unlink.md) — minimal single-operand wrapper around unlink(2)
- [`truncate`](./truncate.md) — shrink files to zero instead of removing them
- [`du`](./du.md) — measure what `rm -rf` is about to release
- [Collection overview](./overview.md) — all pages in the GNU Coreutils collection

## Interview Questions

### Q: A service writes to a log; someone runs `rm` on it, but `df` shows no space freed. Why, and what are two fixes?

`rm` unlinked the directory entry, but the daemon still holds an open file
descriptor, so the inode and its blocks remain allocated until the last
close. Fixes: restart or signal the writer so it closes and reopens the
path, or truncate the file in place (`: > /path` or `truncate -s 0`),
which keeps the same inode and releases the data. You can observe the
ghost as a `(deleted)` entry in `/proc/<pid>/fd`.

### Q: What exactly does `rm -rf /`'s failsafe protect, and what does it not?

`--preserve-root` (the default) only refuses a recursive operation whose
argument is `/` itself. It does not protect `rm -rf /*`, `rm -rf /usr`,
or bind mounts and other filesystems reached during traversal. Hardening
options are `--preserve-root=all` (reject cross-device operands) and
`--one-file-system` (stop recursion at mount boundaries); containers rely
on them because a root shell can always bypass the failsafe.

### Q: Explain the inode lifecycle after `rm` and when data is truly gone.

`unlink(2)` drops one directory entry and decrements `st_nlink`. The inode
is marked free when the link count reaches zero and no process holds it
open (fds, mmaps, or as a cwd). Its block pointers are then released to
the filesystem's free list, making the blocks *available*, not *erased*;
old contents persist until reallocation overwrites them. On COW
filesystems, SSDs with wear leveling, and journaled filesystems, stale
copies may persist well beyond that, which is why `rm` alone is not data
destruction.

### Q: Why does `rm -r` never follow symlinks it encounters during traversal, and why does that matter?

If recursion followed symlinked directories, `rm -r dir/` could climb
out of `dir` through any symlink inside it and delete an unrelated tree —
for instance `dir/latest -> /`. Instead, symlinks found during traversal
are unlinked as entries. Command-line symlink arguments are also not
traversed. This is a deliberate safety invariant of fts-based walks and a
frequent interview check for understanding traversal order.

### Q: What is NFS silly rename and how do you recognize it?

When an NFS client removes a file that is still open (by itself or another
client), the protocol cannot keep the inode alive the way a local VFS
can, so the server renames the file to `.nfsXXXXXX` and keeps it until the
last close. Symptoms: `.nfs*` entries that reappear after deletion, space
not freed, and `rmdir` failing with "directory not empty" on a directory
that looks empty. The fix is to close the holding process first.

### Q: When would you choose `find -delete` over `rm -rf`?

`find -delete` removes entries itself during its own depth-first walk
(with implicit `-depth`), so you can filter precisely by type, age, size,
or name and it fails safely on huge trees where a shell glob would exceed
argument limits. `rm -rf` is faster and simpler when you want everything
below a point, but it is all-or-nothing per tree. For scheduled cleanups,
`find ... -delete` (after a `-print` dry run) is the reviewable choice.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/rm.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
