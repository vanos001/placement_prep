# cp — copy files and directories

## Overview

`cp` is the standard Unix tool for copying files and directory trees. It takes one or more SOURCE operands and a DEST (or a target directory), and produces independent copies of the data — new inodes, new timestamps, fresh file content. It is the tool you reach for backups-in-place, staging build artifacts, duplicating configuration trees, and snapshotting data before an edit. It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) and lives at `/usr/bin/cp` on modern merged-usr Debian/Ubuntu systems.

`cp` is often confused with three siblings. `mv` moves (renames or copies-and-deletes) instead of duplicating. `install` is a copy with built-in mode/owner control, designed for Makefiles. `dd` copies raw blocks rather than file contents with file semantics. Within coreutils, GNU `cp` is also the base for `cp -al` tricks (hard-link farms) and CoW clones via `--reflink`.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/cp |
| First appeared | AT&T UNIX, Version 1 (1971); GNU implementation via fileutils, merged into coreutils (2003) |
| Standards | POSIX.1-2018 (`cp`) |

## Synopsis

```
cp [OPTION]... [-T] SOURCE DEST
cp [OPTION]... SOURCE... DIRECTORY
cp [OPTION]... -t DIRECTORY SOURCE...
```

Common one-line forms:

```
cp file backup                 # two-operand file copy
cp file1 file2 dir/            # multiple sources into a directory
cp -a srcdir dstdir            # recursive archive copy
cp -t dir file1 file2          # target-first form (xargs-friendly)
```

## How It Works

### Form resolution

With two operands that are not both directories, `cp` copies SOURCE to DEST. If the last operand is an existing directory (and `-T` was not given), every SOURCE is copied *into* that directory keeping its basename. `-t DIR` forces the directory interpretation, `-T` forces the file interpretation. Getting this decision wrong is the single most common `cp` bug in scripts:

```
$ mkdir d && cp -r src d        # d now contains src/           (nesting)
$ rm -rf d && cp -r src/. d     # d contains src's contents      (flat)
$ rm -rf d && cp -rT src d      # d IS the copy of src           (no nesting)
```

### The copy itself

For a regular file, GNU `cp` opens the source, creates the destination with mode `source-mode & ~umask`, and streams data in a read/write loop (or via a faster kernel path — see below). Unless told otherwise, the destination is a genuinely new file:

- **mode**: source mode minus the umask bits (copying a 0644 file under umask 022 stays 0644; copying a 0777 script under umask 022 yields 0755).
- **ownership**: the invoking user and their primary group. Root gets real `chown` behavior only with `-p`/`-a`.
- **timestamps**: new file gets the current time as mtime/atime/ctime.

`-p` preserves mode, ownership (as far as the caller's privileges allow) and timestamps. `--preserve=ATTR_LIST` selects individual attributes: `mode`, `ownership`, `timestamps`, `links` (hard-link relationships between sources), `context` (SELinux), `xattr`, `all`. `--attributes-only` copies metadata and drops the data entirely.

### Recursive copies and symlinks

`-R` (and `-a`, `-r`) descends into source directories, creating corresponding destination directories. GNU `cp`'s symlink rules are asymmetric and worth memorizing (from the GNU manual):

- When copying **from** a symlink, `cp` follows the link *only when not copying recursively* (or with `-l`). So plain non-recursive `cp` dereferences, while inside a `-R` tree, symlinks are copied as symlinks by default.
- `-H`, `-L`, `-P` override the default: `-H` follows only command-line symlinks, `-L` follows all symlinks encountered, `-P` never dereferences. If several are given, **the last one wins silently**.
- When copying **to** a symlink, `cp` follows the link only if it refers to an existing regular file; copying onto a *dangling* symlink fails by default (set `POSIXLY_CORRECT` for historical behavior).

`cp -a` (`--archive`) equals `-dR --preserve=all`: never dereference, recurse, and preserve every attribute the filesystem lets you. This is the canonical "exact duplicate" switch for backups and root-filesystem copies.

Special files (FIFOs, device nodes, sockets) are *not* read as data during recursion; `cp -R` copies them as special files of the same type. `--copy-contents` is the unusual switch that actually reads their contents.

### Trailing slashes and target-directory plumbing

GNU `cp` strips one trailing slash from SOURCE arguments (`--strip-trailing-slashes` does this explicitly), so `cp -r src/ dst` and `cp -r src dst` are the same. This matters for tool pipelines that pass directory names with trailing separators. The `-t`/`-T` pair mirrors the rest of the file utilities (`mv`, `install`, `ln`), which is what makes idioms like this safe regardless of glob results:

```bash
# -t: sources come second — no ambiguity, works with zero or many files
find . -name '*.conf' -print0 | xargs -0 cp -t /etc/staging/
```

POSIX defines no `-t`; `-T` is also GNU (and BSD follows suit on most systems). Scripts targeting BusyBox-only environments should rely on the classic two/three-operand forms.

### Backups of overwritten destinations

With `-b` or `--backup[=CONTROL]`, every destination that would be overwritten is renamed aside first. The suffix is `~` by default, overridable with `-S SUFFIX` or `SIMPLE_BACKUP_SUFFIX`; `VERSION_CONTROL` (or the CONTROL argument) selects the scheme:

```
none, off       never make backups (even if --backup is given)
numbered, t     numbered backups: file.conf.~1~, file.conf.~2~
existing, nil   numbered if numbered backups already exist, else simple
simple, never   always the simple suffix: file.conf~
```

The documented edge case worth knowing: `cp --force --backup file file` — copying a file onto itself — is refused normally, but with this combination it makes a backup of the file instead, which is a quick way to snapshot before an in-place edit.

### Fast copy paths

Modern GNU `cp` avoids the read/write loop when it can:

```
$ cp --debug big.bin big2
'big.bin' -> 'big2'
copy offload: yes, reflink: unsupported, sparse detection: no
```

- `--reflink[=WHEN]` requests a copy-on-write clone (FICLONE ioctl on Linux — btrfs, XFS, ZFS). `--reflink=auto` is the default in recent GNU coreutils: clone when the filesystem supports it, else fall back to a normal copy. Source and dest share data blocks until either is modified.
- `--sparse=auto` (default) detects runs of NUL bytes in the source and seeks instead of writing, so sparse files stay sparse; `=always` converts dense holes too; `=never` materializes everything.
- `copy offload` covers server-side/copy_file_range-style offload on supported filesystems.

### Overwrite and identity checks

By default an existing DEST is opened and truncated — silently. `-i` prompts, `-n` skips, `-f` unlinks an unopenable destination, and among `-i`/`-n`/`-f` the **last one given wins**. `--update` (or `-u`) only replaces destinations older than the source; recent coreutils add explicit modes (`all`, `none`, `none-fail`, `older`). `cp` refuses to copy a file onto itself (same inode check), with the documented exception of `--force --backup` on an identical path, which makes a backup instead.

```
$ cp a3 copy3            # normal copy: new inode
$ cp a3 a3               # cp: 'a3' and 'a3' are the same file
$ cp -l a3 farm1         # hard link instead of copy (same inode)
$ cp -al srctree dst     # hard-link farm: dedupe without disk usage
```

Mode decision at a glance:

```
                     ┌─────────────────────────────┐
 SOURCE(s) + DEST ──▶│ last operand is a directory? │
                     └──────┬───────────────┬──────┘
                       yes  │               │  no (-T or 2 ops)
                  ┌─────────▼────────┐ ┌────▼─────────────┐
                  │ copy each SOURCE │ │ DEST must be the │
                  │ into DIRECTORY   │ │ copied file name │
                  └──────────────────┘ └──────────────────┘
```

## Options That Matter

### Copy scope and metadata

| Option | Effect |
| --- | --- |
| `-R`, `-r` | Copy directories recursively |
| `-a` | `-dR --preserve=all`: archive copy, the backup/export default |
| `-p` | Preserve mode, ownership, timestamps |
| `--preserve=LIST` | Fine-grained: mode, ownership, timestamps, links, context, xattr, all |
| `-d` | `--no-dereference --preserve=links`: copy symlinks as symlinks |
| `--attributes-only` | Copy metadata, not data |

### Overwrite control

| Option | Effect |
| --- | --- |
| `-i` | Prompt before overwriting (last of -i/-n/-f wins) |
| `-n` | Never overwrite (deprecated in favor of `--update=none`) |
| `-f` | If destination can't be opened, remove it and retry |
| `-u`, `--update[=MODE]` | Replace only older destinations (all/none/none-fail/older) |
| `-b`, `--backup[=C]`, `-S SUF` | Back up each overwritten destination (default suffix `~`) |
| `--remove-destination` | Delete existing destinations before opening them |

### Layout and performance

| Option | Effect |
| --- | --- |
| `-T` | Treat DEST as a file — no "copy into directory" surprise |
| `-t DIR` | Copy all SOURCEs into DIR (pairs with xargs) |
| `--parents` | Rebuild the source's full path under the target dir |
| `-l` | Hard link instead of copying (same filesystem only) |
| `-s` | Make symlinks instead of copying |
| `--reflink[=W]` | CoW clone: always/auto/never (auto is default in recent coreutils) |
| `--sparse=W` | Sparse handling: auto/always/never |
| `-x` | Stay on one filesystem (skip mount points during -R) |
| `-Z` | Set default SELinux security context on destinations |

## Usage Patterns

```bash
# Quick in-place backup before editing a config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# Copy several files into an existing directory
cp a.conf b.conf /etc/app/
```

```bash
# Exact tree duplicate: preserves symlinks, modes, owners, timestamps
sudo cp -a /var/www /var/www.snap

# Duplicate a tree flatly into an existing dir (no src/ nesting)
cp -rT src/ dst/
```

```bash
# Mirror only changed files into a staging dir
cp -ru /srv/releases/stable/ /srv/releases/live/

# Keep full source paths: cp src/a/b.txt → tgt/src/a/b.txt
cp --parents src/a/b.txt tgt/
```

```bash
# Never clobber: leave existing files alone (and see what happened)
cp -v -n incoming/* ./ || true

# Same, but recent coreutils can fail loudly instead of silently skipping
cp --update=none-fail incoming/* ./
```

```bash
# Hard-link farm: "copy" a 40 GB dataset at zero extra disk cost
cp -al /vol/dataset /vol/dataset.pre-import

# CoW clone on btrfs/XFS — instant, space-efficient snapshot
cp --reflink=always db.img db.before-load
```

```bash
# Backup a whole mounted system without crossing into /proc, /sys, other mounts
sudo cp -ax / /mnt/rootcopy

# Copy preserving timestamps for a diff-friendly test artifact
cp -p target/app.jar artifacts/
```

```bash
# Numbered backups instead of one tilde file
cp --backup=numbered app.conf app.conf   # creates app.conf.~1~

# Script-friendly target-first form straight from find/xargs output
find . -name '*.png' | xargs cp -t /srv/gallery/
```

```bash
# Preserve extended attributes (capabilities!) when copying a binary
cp --preserve=xattr /usr/bin/ping ./bin/ping

# Stream stdin into a destination file — same read/write loop, no source name
printf 'config=on\n' | cp /dev/stdin /etc/app/current.conf
```

```bash
# Destination symlink semantics: cp follows the link when it points to
# an existing regular file, but refuses to write through a dangling link
cp data.bin /var/run/live.bin   # OK if live.bin -> real file; fails if dangling
```

```bash
# Sparse-aware copy of a large virtual-disk file (keeps the holes)
cp --sparse=always /var/lib/vms/vm1/disk.raw /backups/disk.raw

# Inspect which copy strategy was actually used
cp --debug --sparse=always disk.raw /tmp/disk.copy
```

## Nuances and Gotchas

- **`cp` does not preserve timestamps or ownership by default.** A plain copy looks identical in `diff -r` but has fresh mtimes — enough to break make, rsync-like syncs, and cache invalidation. Use `-p` or `-a` when metadata matters.
- **The trailing-operand trap.** `cp -r src dst` behaves differently depending on whether `dst` already exists (copies inside it) or not (renames the copy). `-T` removes the ambiguity; `-r src/. dst` is the flat-copy idiom.
- **`-n` silently skips and still exits 0.** Scripts that "protected" themselves with `-n` overwrite nothing but report success; recent coreutils offer `--update=none-fail` for loud behavior.
- **`-f` is not "force overwrite" in the writable-directory case.** It only unlinks the destination when opening it fails; an ordinary writable dest is truncated regardless. The classic failure it fixes: copying over a file you cannot write (but whose directory you can write).
- **Aliases bite scripts.** A user alias `cp -i` (common on Debian interactive shells) prompts inside non-interactive-looking pipelines; `command cp` or `\cp` bypasses aliases.
- **Partial-failure exit codes.** If one of many sources fails (e.g. a file vanished mid-copy, or xattrs unsupported on NFS), `cp` continues and exits 1, having copied the rest. Check the exit status, not the absence of stderr.
- **`-a` across filesystems can degrade.** Owner/xattr/context restoration needs privileges and support; on FAT/exFAT or some NFS mounts, `-a` copies succeed but emit per-file diagnostics and lose metadata.
- **`--reflink` shares data blocks.** A CoW clone is not a backup against disk-level corruption; an I/O error in the shared extents hits both files.
- **Portability.** `--reflink`, `--sparse`, `--parents`, `--update` are GNU extensions; BSD/macOS `cp` has `-c` (APFS clonefile) instead of `--reflink`, and BusyBox `cp` supports only a small subset (`-a`, `-r`, `-p`, `-f`, `-i`...). POSIX defines `-f`, `-i`, `-p`, `-R`, `-H`, `-L`, `-P` semantics.
- **Copy-onto-hardlink surprise.** If DEST already exists as a hard link to SOURCE, `cp` replaces the data in place — every name pointing at that inode sees the new content. Tools that "copy over" shared files can silently corrupt a hard-link farm; unlink DEST first or use `--remove-destination`.
- **`-v` output is quoted, not parseable.** Recent coreutils print `'a' -> 'b'` with shell-style quoting; earlier releases used bare `a -> b`. Never grep `cp -v` output in scripts — process the sources list instead.
- **Glob emptiness.** `cp *.log /dst/` with no matches passes the literal `*.log` to `cp` and fails with `cannot stat '*.log'` (exit 1). Enable `nullglob` or check matches first; this is the most common non-bug bug report about `cp`.
- **Directories are never created for you.** `cp a b/c/d` fails unless `b/c` exists. Compose with `mkdir -p` (or `install -D`, which creates leading components itself).
- **Copying a directory into itself is refused.** `cp -r src src/backup` detects the descent and errors out; constructing a copy target inside the tree you copy needs care (copy to a temp name outside, then move).
- **`--parents` and absolute paths.** `cp --parents /etc/hosts tgt/` wants to rebuild `tgt/etc/hosts` — fine — but the same command with a source outside the working tree surprises people who expected a flat copy.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All sources copied successfully |
| 1 | Any failure: missing source, denied permission, partial tree copy, refused self-copy |

## Related Commands

- [`mv`](./mv.md) — rename/move instead of duplicate; atomic on one filesystem.
- [`install`](./install.md) — copy plus explicit mode/owner/group; the Makefile workhorse.
- [`ln`](./ln.md) — hard and symbolic links; what `cp -l`/`cp -s` delegate to.
- [`dd`](./dd.md) — block-level copying with conversions; the raw-device sibling.
- [`mkdir`](./mkdir.md) — create destination directories `cp` will not make for you.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [File permissions](../../admin/permissions.md) — how mode/umask shape every copy `cp` makes.
- [Linux internals](../../internals.md) — inodes, hard links, and copy-on-write mechanics.

## Interview Questions

### Q: What exactly does `cp -a` preserve that plain `cp -r` does not?

`cp -a` expands to `-dR --preserve=all`. Versus plain `-r` it (1) never dereferences symlinks — links are copied as links; (2) preserves hard-link relationships between source files; (3) restores mode without umask subtraction, ownership (needs privileges), timestamps, and where supported xattrs, ACLs and SELinux contexts. Plain `cp -r` dereferences nothing about metadata: fresh mtimes, umask-filtered modes, and the invoking user as owner.

### Q: You ran `cp -r project /backup` twice. The second run complains or nests — why?

If `/backup` did not exist, the first run creates `/backup` *as* the copy. The second run sees an existing directory and copies `project` *into* it, yielding `/backup/project`. Guard scripts with `cp -rT project /backup` (or create the destination first with `mkdir -p`), which treats the destination strictly as the copy target.

### Q: Explain what `cp -al` achieves and when it breaks.

`cp -al` recursively hard-links instead of copying: every destination file shares the source inode, so the "snapshot" costs almost no disk. It breaks across filesystems (hard links are inode-local), on directories (never hard-linkable), and semantically — any in-place edit of a file through either path is visible in the other; only write-and-replace edits (editors that save via rename) fork the data.

### Q: What is the difference between `-i`, `-n` and `-f`, and what happens if you give all three?

They all control destination clobbering, and the last one on the command line wins. `-i` prompts, `-n` never overwrites, `-f` removes an unopenable destination and retries. `cp -n -i -f` behaves like `-f`; `cp -f -n` like `-n`. This last-wins rule (POSIX) differs from tools where the "most destructive" flag always wins, and it's a favorite interview trap.

### Q: How would you copy a log file that is actively being written, and what goes wrong with a naive `cp`?

A naive `cp` reads with ordinary reads while the writer appends: you can get a torn tail (data written between your read and the stat-based size), and with the default non-`-p` copy you also lose the original timestamps. Options: copy with `cp -p` while the writer is quiesced, use `dd` with a fixed block count, or snapshot first (`--reflink=always` on CoW filesystems, or an LVM/btrfs snapshot) so you copy a frozen point in time. Any interview answer should mention that `cp` gives no consistency guarantee for concurrently modified files.

### Q: How does `cp` handle a sparse 10 GB log file that occupies 50 MB of disk?

With the default `--sparse=auto`, `cp` detects all-NUL blocks and seeks in the destination, reproducing a sparse file. `--sparse=never` would materialize 10 GB of real blocks; `--sparse=always` also punches holes in dense regions. Combined with `--reflink=auto` (default in recent coreutils), `cp` first tries a filesystem clone (btrfs/XFS), then offload, then the sparse-aware read/write loop — that's exactly the ladder `cp --debug` prints.

### Q: Why might `cp -a /etc /mnt/nfs/etc` exit 1 even though the tree was copied?

Attribute restoration on the destination filesystem: `chown` to arbitrary owners, POSIX ACLs, or SELinux/xattr restoration can all fail on NFS/FAT/CIFS. GNU `cp` completes the copy of remaining files, prints a diagnostic per failed attribute, and exits 1. On backup media where ownership is meaningless, `cp -rp` (or stripping the failing attribute from `--preserve=`) is the pragmatic choice.

### Q: Your deploy script does `cp app.conf /etc/app/app.conf` and systemd unit file modes end up wrong. What happened and what are two fixes?

`cp` creates the destination with the source's mode filtered through the caller's umask — and if the destination already existed, its mode is left untouched entirely (an overwrite truncates, it does not chmod). Fix one: set the intended mode explicitly at creation (`umask`, `chmod` after, or `install -m 644`). Fix two: drop the stale destination first (`cp --remove-destination`) or use `install`, which enforces mode/owner on every run — one reason `install` is preferred in Makefiles.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/cp.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — cp](https://pubs.opengroup.org/onlinepubs/9699919799/)
