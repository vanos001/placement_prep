# hardlink — consolidate duplicate files by hardlinking them

## Overview

`hardlink` walks directory trees, finds files with identical content, and replaces the duplicates with hard links to a single canonical inode — a transparent, filesystem-level deduplication. Space is saved because one copy of the data blocks now serves every path; applications see no difference (same size, same content), only a higher link count. Typical targets: backup trees, package caches, media collections, git object stores, and container/VM image farms.

It ships in the `util-linux` package at `/usr/bin/hardlink` (the util-linux rewrite of the older standalone `hardlink` tool; Debian builds it from the util-linux source). Reach for it as a batch dedup: `hardlink -n -l -v` to audit, `hardlink -c -t -p -o` (or plain `hardlink dir/`) to consolidate. It is often confused with `cp -l`/`ln` (which link *specific* files, not whole trees), with reflinks (`--reflink` here: copy-on-write clones instead of shared inodes), and with symlink-based dedup (which breaks when the original moves).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/hardlink |
| First appeared | Early-2000s standalone tool; rewritten and merged into the util-linux tree |
| Standards | None (Linux-specific tool) |

## Synopsis

```
hardlink [options] <directory>|<file> ...
```

Common one-line forms:

```
hardlink -n -v /backups          # dry run with details
hardlink -c /srv/media           # consolidate identical content
hardlink -l /data                # just list duplicate groups
hardlink -f -d /cache /pool      # only files with identical names/dirs
```

## How It Works

### The matching pipeline

Content comparison is expensive, so `hardlink` filters in cheap-first order:

```
walk tree (fstat every regular file)
   │ 1. size differ?        → not duplicates, skip (no I/O)
   │ 2. already same inode? → already linked, skip
   │ 3. content compare     → memcmp (default) or digest (-y sha256...)
   │    with cache of size/digest data (-r cache-size)
   ▼ 4. all checks pass → unlink loser, link winner under its name
```

Step 4 is where semantics matter: the *winner* keeps its inode — its owner, mode, timestamps, and xattrs — and every loser path is recreated as a directory entry pointing at the winner's inode. The loser's metadata is therefore discarded, which is why the tool by default only links files whose ownership, mode, and timestamps already match, with flags to relax each.

```bash
$ printf 'identical content 123\n' > a.txt && cp a.txt b.txt
$ printf 'other\n' > c.txt && hardlink .
Mode:                     real
Method:                   memcmp
Files:                    3
Linked:                   1 files
Compared:                 1 files
Saved:                    22 B
Duration:                 0.000143 seconds
$ stat -c '%h %i %n' *
2 270010 a.txt
2 270010 b.txt     # same inode, link count 2 — one copy on disk
1 270012 c.txt
```

### Which copy survives

When several files match, one becomes the canonical inode. The choice is configurable: `-m, --maximize` prefers the file with the *highest* existing hard-link count (fewest relinks); `-M, --minimize` inverts that; `-O, --keep-oldest` prefers the oldest file; `-F, --prioritize-trees` gives precedence to files found in earlier command-line directories (for "originals first, backups second" layouts). Precedence: minimize/maximize outrank keep-oldest and prioritize-trees.

### Selection controls

- `-f, --respect-name` / `-d, --respect-dir`: only link files with identical filenames / relative directory paths — safe defaults for trees where "same name" implies "same logical file".
- `-p, --ignore-mode`, `-o, --ignore-owner`, `-t, --ignore-time`, `-X, --respect-xattrs`: relax or tighten the metadata equality precondition (the `-c, --content` shortcut is exactly `-pot`).
- `-x/-i <regex>`: exclude/include paths; `--exclude-subtree <regex>` prunes directories.
- `-s/-S <size>`: process only files within a size window (dedup only the big ones).
- `--mount`: stay on one filesystem (hard links cannot cross filesystems anyway; this avoids pointless traversal).
- `-y <method>`: comparison strategy — `memcmp` is exact; hash methods speed up large trees by comparing digests first.
- `--reflink[=<when>]`: instead of hard links, create CoW clones (`FICLONE`) on btrfs/XFS — files stay independent but share extents until written.

### The comparison engine, precisely

Candidates reach content I/O only after the cheap filters pass: dev+inode identity (already linked — skip), then size equality. Within a size-equal group the tool compares content — full byte comparison (`memcmp`) or a digest method (`-y sha256`/`sha1`/`crc32`/`crc32c`, ...). The digest methods run through the kernel crypto API (AF_ALG sockets — the method names are kernel algorithm names); when the kernel lacks the requested algorithm, hardlink silently falls back to full comparison. The method therefore changes speed, never correctness — the summary's `Method:` line shows what actually ran. The `-r` cache keeps recently read content (or digest data) inside a RAM budget so size-equal groups compare without re-reading from disk.

Relinking is `unlink(loser)` followed by `link(winner, loser_path)` — two syscalls, not an atomic rename. A crash between them loses the loser's *name* (its content lives on at the winner's inode). The window is microseconds but nonzero, which is why dry-run-plus-backup is the standing advice for irreplaceable trees.

### Reading the run summary

The summary block is the audit artifact: `Files` (scanned), `Compared` (content comparisons performed), `Linked` (relinks done), `Saved` (bytes reclaimed). `Compared` far below `Files` means size/identity filters did their work; `Saved` is the number for the change ticket, and it should be visible as a `df`/`du` delta on the same filesystem afterward.

### What counts as a candidate

Only regular files participate, and the equality precondition is the conjunction of checks the flags control: same name (`-f`), same relative directory path (`-d`), same mode/owner/timestamps (each relaxable), same xattrs when `-X` is given. The conjunction is deliberately conservative because the survivor's metadata is what *both* paths get afterward. Two practical consequences: trees restored by tools that did not preserve mtimes (plain `cp`, unzip) dedup only with `-t` added, and trees holding root-owned and user-owned copies of identical content stay separate unless `-o` merges them.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-c, --content` | Compare content only, same as `-p -o -t` (ignore mode/owner/time) |
| `-n, --dry-run` | Report what would be linked, change nothing |
| `-l, --list-duplicates` | Print every group of duplicate files, link nothing |
| `-m, --maximize` / `-M, --minimize` | Prefer highest / lowest link count as survivor |
| `-O, --keep-oldest` | Prefer the oldest equal file as survivor |
| `-F, --prioritize-trees` | Earlier command-line directories win survivor precedence |
| `-f, --respect-name` / `-d, --respect-dir` | Require identical filename / directory path |
| `-p, --ignore-mode` / `-o, --ignore-owner` | Don't require equal mode / ownership |
| `-t, --ignore-time` | Don't require equal timestamps |
| `-X, --respect-xattrs` | Also compare extended attributes |
| `-y, --method <name>` | Content comparison method (e.g. memcmp, sha256) |
| `-s/-S, --minimum/maximum-size` | Size window for candidates |
| `-b, --io-size` / `-r, --cache-size` | Read buffer and in-memory comparison cache bounds |
| `-x/-i, --exclude/include <regex>` | Path filters; `--exclude-subtree` for dirs |
| `--reflink[=<when>]` | Create CoW clones instead of hard links (auto/always/never) |
| `-z, --zero` | NUL-delimit output for `xargs -0` pipelines |
| `-q/-v` | Quiet / verbose (repeat `-v` for more) |

## Usage Patterns

```bash
# Audit before acting: list duplicate groups, touch nothing
hardlink -l /srv/media

# Dry run with verbose detail to preview the consolidation
hardlink -n -v /srv/media

# Straight dedup of a media collection
hardlink /srv/media

# Conservative dedup: same name, same relative dir, metadata must match
hardlink -f -d /backups/2024 /backups/2025

# Dedup only large files (skip millions of tiny configs)
hardlink -s 100M -v /var/cache/packages

# Keep the "originals" tree's copies, link the backup tree into them
hardlink -F -n /srv/orig /srv/backup     # drop -n when satisfied

# Prefer the file already shared by the most paths as survivor
hardlink -m -t /srv/images

# Exclude volatile and small pseudo trees
hardlink -x '/proc|/sys|\.git/' --exclude-subtree 'tmp' /srv

# Zero-delimited list for downstream tooling
hardlink -l -z /data | xargs -0 -n1 stat

# Reflink dedup on btrfs (files stay independent, extents shared)
hardlink --reflink=always /srv/vm-images

# Quiet cron job with a sizeable comparison cache
hardlink -q -r 512M /var/cache/pacman

# Post-run audit: the merged population, with inodes and link counts
find /srv/media -type f -links +1 -printf '%i %n %s %p\n' | sort

# Digest-first comparison for huge trees (kernel crypto via AF_ALG)
hardlink -y sha256 -v /srv/isos

# Reflink-first dedup: CoW clones on btrfs/XFS, hard links as fallback
hardlink --reflink=auto -v /srv/vm-images

# Scheduled pass with bounded RAM and a log line for the ticket
hardlink -q -r 128M /srv/media && logger -t hardlink "dedup pass done"

# The strictest, safest profile: same name, same relative dir, xattrs equal
hardlink -f -d -X -n -v /srv/www    # drop -n after reviewing the report

# Per-user dedup without root (protected_hardlinks allows your own files)
hardlink -n -v "$HOME/builds" "$HOME/shared"

# Coverage metric for the ticket: how much of the tree now shares inodes
total=$(find /srv/media -type f | wc -l); linked=$(find /srv/media -type f -links +1 | wc -l)
echo "$linked / $total files share inodes"
```

## Nuances and Gotchas

- **In-place modification propagates.** After linking, editing one path with a tool that writes in place (e.g. `dd`, some appenders) changes *all* paths. Editors that write-temp-and-rename silently break the link (leaving the other path stale) — both behaviors surprise people; dedup is for content-stable files.
- **The survivor's metadata wins.** Linking "identical content" files with different mtimes/modes/owners discards the loser's metadata unless you relax with `-p/-o/-t`. Restores then look odd (all files share the winner's timestamp) — prefer `-f/-d` name matching for backup trees.
- **`protected_hardlinks` (default on modern kernels) blocks linking files you don't own** — hardlink run as non-root simply skips or fails on foreign files. Run as root, or per-owner.
- **Cross-filesystem is impossible.** Candidates on different mounts can never be linked (EXDEV); `--mount` avoids wasting traversal time. Run once per filesystem.
- **Symlinks are not followed or deduplicated.** Only regular files participate; symlink farms and device nodes pass through untouched.
- **Backups must preserve links.** `rsync` without `-H` materializes duplicates again (and doubles the transfer); `tar` preserves links within an archive by default; `cp -a` preserves links among its arguments. Verify restored trees with `stat -c %h`.
- **I/O cost is real.** Every size-equal pair gets a full content read (or digest). On cold multi-TB trees, budget for it; `-r <cache-size>` keeps digest data in RAM to avoid re-reads, `-b` tunes the read buffer, `-s/-S` prune candidates.
- **`du` and `df` see through links, `ls -l` shows the truth in nlink.** After dedup, `du` counts shared blocks once (per-tree), while `find -links +1` lists the linked population — useful for verifying the run.
- **Dry-run first, always.** `-n -v` is cheap; an unintended `hardlink /` is not undoable (un-merging requires re-materializing copies).
- **`--reflink` changes the semantics.** Clones are *not* hard links: writes diverge (CoW), link counts stay 1. Use it when consumers may modify files and you only want to share the initial blocks.
- **The relink is two syscalls, not one.** `unlink` then `link` — a crash between them loses the duplicate's name (content survives on the winner's inode). Keep backups for irreplaceable trees; the dry run costs nothing.
- **Merging is one-way.** Un-merging means re-materializing a full copy (`cp --reflink=auto` is the cheap route); there is no "unhardlink". Decide the survivor policy (`-m/-M/-O/-F`) before the first real run, not after.
- **Digest methods fall back silently.** `-y sha256` on a kernel without that crypto algorithm quietly degrades to full byte comparison — same result, much slower. The `Method:` line in the summary shows what actually ran; do not assume the flag made the run fast.
- **Anything tracking files by (device, inode) sees a relink as a new file.** Indexer databases and incremental-backup catalogs record the old inode; after dedup they re-scan (or re-send) the linked paths. Expect a one-time re-scan cost, and schedule dedup before heavy catalog runs rather than after.
- **The `-r` cache size is a trade, not a win button.** Too small → re-reads from disk; too large → page-cache eviction for the very files being compared (and OOM exposure on small hosts). A few hundred MB suits TB-scale trees; watch RSS, not the flag's promise.
- **`--skip-reflinks` exists because reflink runs are re-runnable.** Already-cloned files are skipped so a second pass is cheap and idempotent — plain hardlink runs have no such memory: rerunning a completed merge just re-verifies and changes nothing, which is the safer default.

## Exit Status

- `0` — success: all candidates scanned, linking (or the dry-run listing) completed.
- Nonzero — an error occurred (unreadable files, I/O failure, bad options); with `-n`/`-l` no tree changes were made regardless.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`fallocate`](./fallocate.md) — the mirror-image operation: creating space, not reclaiming it.
- [`fincore`](./fincore.md) — which files share page cache; complements block-level dedup analysis.
- [`find`](../../shell/find.md) — `-links +1`, `-samefile` predicate for auditing hard links.
- [`permissions`](../../admin/permissions.md) — ownership rules and `protected_hardlinks` behavior.
- [`internals`](../../internals.md) — inodes, link counts, and the directory-entry model making this possible.

## Interview Questions

### Q: What exactly happens to a duplicate file when hardlink consolidates it?

Nothing is copied: the tool unlinks the duplicate path and creates a new directory entry pointing at the surviving inode. The file's link count rises, the loser path disappears as an independent inode, and its blocks are freed. The survivor's owner/mode/timestamps/xattrs apply to both paths afterward — which is why the tool by default requires metadata equality before linking.

### Q: A customer complains that after dedup, editing one file changed "another unrelated file". Explain.

The paths share one inode. A writing tool that modifies in place (append, truncate-write, mmap stores) edits the single underlying copy, visible at every linked path. Tools that replace by rename (most editors, `mv new over old`) instead break the link and leave the other path at the old content. Deduplication is only safe for content-stable files, or you must accept CoW semantics via `--reflink` on btrfs/XFS.

### Q: How does hardlink decide which of several equal files survives?

Ranking flags: `-m/-M` maximize/minimize the surviving link count, `-O` keeps the oldest, `-F` prefers files from earlier command-line directories (originals over backups). Minimize/maximize take precedence over the softer preferences. Without any preference flag the tool links duplicates to the file it considers best by its default ordering — for reproducible runs on important trees, set the flags explicitly.

### Q: Why did your rsync-based restore double the disk usage of a deduplicated tree?

rsync treats each path independently and does not preserve cross-file hard links unless told to (`-H`). The restore materialized one full copy per path. tar preserves links within an archive; GNU `cp -a` preserves them among its arguments. Always restore deduplicated trees with link-preserving tools and verify with `find -type f -links +1 | wc -l`.

### Q: Compare hard-link dedup with reflink dedup.

A hard link is one inode with multiple names: zero extra space, but any in-place write affects all paths. A reflink (FICLONE on btrfs/XFS) gives each path its own inode whose extents are shared copy-on-write: same immediate space saving, but later writes diverge cleanly. hardlink supports both via `--reflink=always`; choose hard links for immutable content, reflinks for files that may be modified later (VM images, snapshots).

### Q: What does /proc/sys/fs/protected_hardlinks do and how does it interact with this tool?

It restricts hard-link creation to files the user owns or has read/write access to, closing a tmp-race attack class. For hardlink it means non-root runs can only consolidate files belonging to (or writable by) the invoking user; system-wide dedup of foreign files needs root. The tool either fails or skips such candidates — a common "why did it skip half the tree" question.

### Q: How does hardlink avoid O(n²) comparisons on a million-file tree?

Cheap keys first: candidates bucket by size, so content I/O happens only inside size-equal groups; dev+inode identity removes already-linked pairs immediately; digest methods (`-y`) reduce comparisons to digest equality, with results held in a bounded RAM cache (`-r`). The cost model is the size distribution: trees with many exact copies are cheap; trees with many *distinct* files of identical size are the pathological case — that is where `-s`/`-S` windows and `--exclude` filters earn their keep.

### Q: Where does hardlink dedup lose to deduplicating storage (ZFS/VDO) or to reflinks?

hardlink is an offline batch job: it only sees duplicates within the trees you pass, pays one full read, and its work is undone the moment a writer replaces a file (rename-based updates create fresh inodes). Block-layer dedup (ZFS, VDO) is continuous and transparent but taxes every write and complicates recovery. Reflinks (btrfs/XFS `FICLONE`) split the difference — shared extents that diverge safely on write. Match the mechanism to the write pattern: static content tolerates batch dedup; churny workloads want in-storage dedup or reflinks.

### Q: What does `find -links +1` prove after a run, and what does it not prove?

It lists files with more than one hard link — the merged population, with link counts and inodes. It does not prove content correctness end-to-end: sample merged files against a pre-run checksum manifest (`sha256sum -c`) to confirm no path serves different bytes than before, and reconcile the `Saved:` figure against the filesystem's `df`/`du` delta. The summary is the tool's self-report; the find/cmp sweep is the independent audit.

### Q: Why does the default (no flags) refuse to link files with different timestamps, and when do you override it?

Because the survivor's metadata becomes the metadata of *both* paths: merging files with different mtimes would silently rewrite history for the loser — backup tools that select by mtime would then re-copy or mis-order restores. The default is the conservative contract; override with `-t` only when content identity is what matters (media caches, compiled artifacts) and consumers demonstrably never read timestamps. Mode and owner are protected the same way (`-p`/`-o` to relax).

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/hardlink.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
