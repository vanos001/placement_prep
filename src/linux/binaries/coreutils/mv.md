# mv — move or rename files and directories

## Overview

`mv` relocates or renames files: on the same filesystem it is an instant, atomic rename syscall; across filesystems it silently falls back to copy-then-delete. That duality is the whole mental model — `mv` is either free or it is a hidden `cp -Rp` plus `rm`, and knowing which one you triggered explains every performance cliff and partial-failure story. It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at `/usr/bin/mv`.

`mv` is often confused with `cp` (which leaves the source), `ln` (which adds a name instead of relocating one), and the symlink-flip deploy pattern, where `mv -T` is the atomic primitive. POSIX standardized `mv` early; GNU adds backup options, update modes, and the `-t`/`-T` target plumbing shared across the file utilities.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/mv |
| First appeared | AT&T UNIX, Version 1 (1971) |
| Standards | POSIX.1-2018 (`mv`) |

## Synopsis

```
mv [OPTION]... [-T] SOURCE DEST
mv [OPTION]... SOURCE... DIRECTORY
mv [OPTION]... -t DIRECTORY SOURCE...
```

Common one-line forms:

```
mv old new                    # rename
mv file1 file2 dir/           # move several into a directory
mv -T build current           # atomic flip of a directory name
mv -t dir *.log               # target-first form (xargs-friendly)
```

## How It Works

### Same filesystem: rename(2), all the way down

Within one filesystem, GNU `mv` calls `rename(2)`. The kernel rewrites a directory entry and the inode never moves: no data is copied, no blocks are touched, and the operation is **atomic** with respect to other processes — a reader sees either the old name or the new one, never an absence. Cost is O(1) regardless of file size; renaming a 100 GB file costs the same as renaming a 1 KB one. Renaming *directories* is likewise O(1) — as long as the destination is not inside the source tree (the kernel rejects that with `EINVAL`; `mv` reports "cannot move ... into itself").

### Across filesystems: emulate with copy + delete

When source and destination are on different devices, `mv` cannot rename and switches strategy:

```
                 ┌───────────────────────────────┐
  mv SRC DST ──▶ │ same filesystem / device?     │
                 └──────┬─────────────────┬──────┘
                   yes  │                 │  no
              ┌─────────▼────────┐  ┌─────▼───────────────────┐
              │ rename(2)        │  │ 1. copy data + metadata │
              │ atomic, O(1)     │  │ 2. remove source        │
              └──────────────────┘  │    (dirs: recursive)    │
                                    └─────────────────────────┘
```

The copy phase behaves like `cp -Rp`: mode, ownership (as far as privileges allow), and timestamps are preserved, directories are traversed recursively. If the copy fails mid-way (disk full, permission), GNU `mv` removes the partial destination file it was writing and leaves the source intact — but there is no atomicity across the whole operation: a reader can observe a half-populated destination directory mid-move, and the window scales with data size.

### Destination semantics

Same operand rules as `cp`: with two operands and DEST not an existing directory, DEST is the new name; otherwise sources move *into* the directory. `-T` forbids the into-directory interpretation, `-t DIR` forces it — and `-T` is what makes the atomic-deploy flip work:

```
$ mv -T /srv/releases/2024-10-09 /srv/current   # replaces dir symlink/dir atomically
```

Overwrite control composes POSIX-style: `-i` prompts, `-n` never overwrites, `-f` overwrites without prompting — and if more than one is given, **only the final one takes effect**. `--update` (`-u`) replaces destinations only when the source is newer; recent coreutils expose explicit modes (`all`, `none`, `none-fail`, `older`) so scripts can fail loudly instead of silently skipping. `--exchange` (coreutils 9.5-era, not in bookworm) swaps SOURCE and DEST in place — the missing primitive for A/B swaps. Same-file protection: moving a file onto itself (same inode via any path, including hard links) is refused:

```
$ mv a3 h3
mv: 'a3' and 'h3' are the same file
```

### Backups and verbosity

`-b`/`--backup[=CONTROL]` and `-S SUFFIX` rename each overwritten destination aside (`~` by default; `--backup=numbered` for `file.~1~` style). `-v` prints each action — `'d1' -> 'd2'` for renames, `'a' -> 'dir/a'` for moves — with shell-style quoting in recent releases.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f`, `-i`, `-n` | Overwrite always / prompt / never (last one given wins) |
| `-u`, `--update[=MODE]` | Replace only older destinations (all/none/none-fail/older) |
| `-T` | DEST is always a plain name — never "into the directory" |
| `-t DIR` | Move all SOURCEs into DIR |
| `-b`, `--backup[=C]`, `-S SUF` | Back up overwritten destinations |
| `-v` | Print each move/rename |
| `--strip-trailing-slashes` | Drop trailing `/` from SOURCE arguments |
| `-Z` | Set default SELinux security context on destinations |
| `--exchange` | Swap SOURCE and DEST (coreutils 9.5-era, not in bookworm) |
| `--no-copy` | Refuse to fall back to copy when rename fails (9.5-era) |

## Usage Patterns

```bash
# Plain rename
mv draft-v3.txt final.txt

# Move files into a directory (dest must exist)
mv a.log b.log c.log /var/tmp/
```

```bash
# Target-first form, safe with find/xargs pipelines
find . -name '*.old' -print0 | xargs -0 mv -t /srv/archive/

# Move only what's newer — cheap sync for staged uploads
mv -u staging/*.html /srv/www/
```

```bash
# Atomic deployment flip: readers never see a missing 'current'
ln -sfn /srv/releases/2024-10-09 /srv/releases/current.tmp
mv -T /srv/releases/current.tmp /srv/releases/current

# Same primitive for directories
mv -T /opt/app-2.0.1 /opt/app
```

```bash
# Rename with a safety net: keep the overwritten file as new.txt~
mv -b new.txt config.xml

# Never clobber, but notice the skips in recent coreutils
mv --update=none-fail incoming/*.csv processed/ || echo "some existed"
```

```bash
# Bulk rename with a loop (mv does no pattern rewriting)
for f in IMG*.png; do mv -- "$f" "vacation-${f#IMG}"; done

# Lowercase everything in a directory
for f in *; do mv -- "$f" "$(printf '%s' "$f" | tr 'A-Z' 'a-z')"; done
```

```bash
# Moving across filesystems: watch the copy happen (same command, different path)
mv -v /mnt/nvme/dataset /mnt/archive/           # instantaneous if same fs
mv -v /tmp/bigfile /home/z/bigfile              # copy+delete if devices differ
```

```bash
# Handle names starting with '-' (never let an option eat your file)
mv -- -weird-name weird-name

# Dry-run discipline: -v with a temp destination you control
mv -v -- "$src" "$dst"
```

## Nuances and Gotchas

- **Same-FS vs cross-FS is invisible until it isn't.** A move that was instant in testing becomes a multi-terabyte copy in production when the destination is a different mount. Check with `df`/`stat -c %m` before moving large trees; `mv` gives no "are you sure".
- **Cross-device moves are not atomic.** Directories are copied file by file; a failure (disk full, network drop) leaves a partial destination — GNU removes its own partials, but readers during the window see incomplete data. For big cross-device relocations prefer `cp -a` + verify + `rm`, where you control each phase.
- **`mv dir dest` nests or renames depending on dest's existence** — the identical trap as `cp`. `-T` removes the ambiguity.
- **`-i`/`-f`/`-n`: last one wins** (POSIX). `mv -fn` silently overwrites nothing; `mv -nf` overwrites everything. Aliased `mv -i` in interactive shells changes script behavior — bypass with `command mv` or `\mv`.
- **`-n` exits 0 on skips.** A "protected" move reports success while doing nothing; recent coreutils' `--update=none-fail` is the loud variant. Scripts that must know need explicit checks (`[ -e dst ]`) or the newer mode.
- **Atomic flip needs `-T`.** `mv new old` when `old` is a directory moves `new` *inside* it instead of replacing it. The deploy idiom is `mv -T`; without it, symlinks get "renamed into" the directory they point to.
- **`mv` preserves data, not environment.** It preserves mode/mtime/ownership on the copy path but does not create destination directories (`mv a b/c` fails unless `b` exists) and never asks before destroying a cross-device half-finished destination of its own.
- **Portability.** `-t`, `-T`, `--update` modes, `--exchange`, `-b`-style backups are GNU; BSD `mv` shares the core flags; BusyBox `mv` is minimal (`-f`, `-i`, `-u`). POSIX defines `-f`, `-i`, `-n` (last-wins), `-t` is actually not in POSIX — scripts for minimal systems use the two/three-operand forms.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All sources moved |
| 1 | Any failure: missing source, denied permission, self-move refusal, failed cross-device copy |

## Related Commands

- [`cp`](./cp.md) — the copy path `mv` silently invokes across filesystems.
- [`ln`](./ln.md) — add a name without removing one; the symlink-flip primitive's other half.
- [`install`](./install.md) — copy-with-attributes when the source should stay.
- [`ls`](./ls.md) — verify results (nlink, timestamps) after scripted moves.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [Linux internals](../../internals.md) — what rename(2) does to dentries and inodes.
- [bash](../../shell/bash.md) — parameter expansion and loops that pair with `mv` for bulk renames.

## Interview Questions

### Q: Why is `mv` instant for a huge file on one filesystem but slow across filesystems?

Same filesystem: `mv` is a single `rename(2)` — the kernel rewrites a directory entry and the inode's data never moves, so cost is independent of size and the operation is atomic. Cross filesystem: hard links can't span devices, so there is no rename path; `mv` falls back to copying data (recursively for directories), then deleting the source. The performance cliff and the non-atomic window are both properties of that fallback.

### Q: What is the difference between `mv -f`, `mv -n`, and `mv -i`, and what if you pass two of them?

They select overwrite behavior and POSIX says the *last* one on the command line wins: `-f` overwrites without prompting, `-n` never overwrites, `-i` prompts. `mv -nf` overwrites; `mv -fn` does not. This surprises people who assume the "safest" flag wins. GNU `-n` is also flagged deprecated in favor of `--update=none`, which composes with `none-fail` for scripts that want loud behavior.

### Q: How do you atomically swap a service's "current" symlink to a new release?

Create the new link under a temporary name (`ln -sfn /srv/rel-2024-10-09 /srv/current.tmp`), then `mv -T /srv/current.tmp /srv/current`. `rename(2)` replaces the existing name atomically — no moment where `/srv/current` is missing or half-updated. The `-T` is essential: without it, if `current` is a symlink to a directory, `mv` would move the temp link *inside* it rather than replacing it.

### Q: `mv src dst` printed "are the same file". When does that happen and why is it a feature?

When source and destination resolve to the same inode — identical path, or two names hard-linked to one inode. Overwriting would be a no-op at best and a truncation hazard at worst, so GNU `mv` refuses (exit 1). It's a feature because it catches scripts that expand globs onto themselves (`mv *.log .` with a destination glob that includes the sources) before data is destroyed.

### Q: What happens to metadata when `mv` copies across filesystems?

GNU `mv` emulates `cp -Rp`: it preserves mode and timestamps and attempts ownership (successful if you have the privileges), then deletes the source. Attributes that the destination filesystem cannot represent are lost or warned about — the same degradation class as `cp -a` onto FAT/CIFS. If you need verification between the phases, do the copy yourself (`cp -a` + `diff`/hashes) and delete explicitly rather than trusting the fused move.

### Q: A script does `mv /tmp/upload/$f /srv/incoming/` and intermittently loses files when two jobs run at once. What's happening?

Two failure classes to check. First, cross-device: if `/tmp` and `/srv` are different filesystems, the move is copy+delete, and a failed copy (space, quota, path race) destroys neither but leaves no file at the destination — check exit codes and partial-cleanup behavior. Second, races: two jobs moving the *same* filename overwrite each other atomically (last rename wins) — there's no "merge". The fixes are unique temp names (`mktemp`), `-n`/`--update` policies, or a rename-into-place design where the destination name encodes the job ID.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/mv.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — mv](https://pubs.opengroup.org/onlinepubs/9699919799/)
