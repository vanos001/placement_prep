# vdir — list directory contents in long format

## Overview

`vdir` is the third member of the `ls`/`dir`/`vdir` trio: the same GNU coreutils engine compiled with the long format forced on. By default it behaves exactly like `ls -l -b` — one entry per line with permissions, owner, group, size, timestamp, and name — and it does so whether stdout is a terminal or a pipe. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/vdir`. Like `dir`, the name exists for MS-DOS-era familiarity (`DIR` showed a detailed listing; `vdir` was GNU's long-format counterpart), and like `dir` it is absent from macOS, the BSDs, and BusyBox.

`vdir` is often confused with `ls -l` (identical output, different defaults policy), with `dir -l` (the same thing reached from the columnar sibling), and with `stat` (per-file structured metadata rather than a formatted listing). For anything automated, the rule from the [ls](./ls.md) page still applies: listings are for humans; the shell, globs, and `find` are for machines.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/vdir |
| First appeared | GNU fileutils, early 1990s (long-format counterpart of `dir`) |
| Standards | None — GNU extension, not in POSIX |

## Synopsis

```
vdir [OPTION]... [FILE]...
```

Common one-line forms:

```
vdir                    # long listing of the current directory
vdir -h /var/log        # human-readable sizes
vdir -t | head          # newest entries first
vdir -an /etc | head    # numeric IDs, include dot entries
```

## How It Works

### vdir ≡ ls -l -b, byte for byte

Verified on this system: `diff <(vdir /usr/bin) <(ls -l -b /usr/bin)` is empty. Where `ls` decides its format from whether stdout is a tty, `vdir` pins the long format and backslash-escaped quoting:

```
ls (piped):        one name per line, literal quoting, no metadata
ls (tty):          columns, shell-escape quoting, color if configured
dir (always):      columns + C escapes          (ls -C -b)
vdir (always):     long format + C escapes      (ls -l -b)
```

### The long format, field by field

```bash
$ vdir | head -2
total 8
-rw-rw-r-- 1 z z 8 Oct  9 10:04 a1
```

```
-rw-rw-r-- 1 z z 8 Oct  9 10:04 a1
│  │  │  │ │ │ │  │ └── mtime (style from --time-style)
│  │  │  │ │ │  └──── size in bytes (-h for human units)
│  │  │  │ │ └─────── group (-o hides; -G suppresses; -n numeric)
│  │  │  │ └───────── owner (-g hides; -n numeric)
│  │  │  └─────────── hard-link count
│  └──┴──┴─────────── mode: type + user/group/other bits
└──────────────────── type: - file, d dir, l symlink, p FIFO, b/c device, s socket
```

The leading `total N` line is the sum of allocated blocks (1 KiB units) for the listed entries. Mode-string decorations and the `-F` indicator set match `ls` exactly — see the [ls](./ls.md) page for the full walk-through.

### Sorting, time, and selection

Default sort is alphabetical under the current locale's collation; `-t`/`-c`/`-u` switch to mtime/ctime/atime, `-S` sorts by size, `-v` uses natural version order, `-U` skips sorting entirely, `-r` reverses. `-a`/`-A` control dot-entry visibility, `-d` describes directories themselves, `-R` recurses. All of it is inherited from the shared implementation — nothing is new in `vdir`.

### Operands and per-operand behavior

As in `ls`: a file operand is described directly; a directory operand has its contents listed (a heading line `dirname:` precedes each directory's listing when more than one operand is given). Nonexistent operands produce a diagnostic on stderr, set exit status 2, and do not stop the remaining operands from being processed — same contract as `ls`.

### What piping changes — and what it doesn't

For `ls`, piping flips format and quoting. For `vdir` the answer is deliberately boring: *nothing visible changes* except color, which is only emitted with `--color`. That stability is the binary's entire selling point; it exists so that an MS-DOS-trained reflex (`DIR` always shows details) produces the same bytes on a terminal and in a file.

## Options That Matter

| Option | Effect |
| --- | --- |
| (default) | Long format, one entry per line — no flag needed |
| `-b` (default) | C-style escapes for nongraphic characters in names |
| `-h` | Human-readable sizes (1K 234M 2G) |
| `-n` | Numeric UIDs/GIDs instead of names (locale- and NSS-stable) |
| `-g`, `-o`, `-G` | Omit owner / omit group / omit group column |
| `-a`, `-A` | Include dot entries / minus `.` and `..` |
| `-t`, `-c`, `-u`, `-S`, `-v`, `-r` | Sort keys: mtime / ctime / atime / size / version / reverse |
| `--time-style=STYLE` | long-iso, full-iso, iso, or +FORMAT |
| `-F`, `-p` | Type indicators / trailing slash for directories |
| `-i`, `-s` | Inode numbers / allocated blocks |
| `--color[=WHEN]` | LS_COLORS palette, same as `ls` (see [dircolors](./dircolors.md)) |

## Usage Patterns

```bash
# The default: long format without typing -l
vdir /etc | head
```

```bash
# Human sizes for a quick disk glance
vdir -h /var/lib/docker | head
```

```bash
# Newest first — "what changed in here?"
vdir -t /etc | head
```

```bash
# Numeric IDs and ISO timestamps: stable for logs and diffs
vdir -ln --time-style=long-iso /etc | head
```

```bash
# Permission audit of a suspicious directory, escaped names included
vdir -la /tmp/upload | head
```

```bash
# Largest last
vdir -lSh /var/backups | tail
```

```bash
# Track ownership changes via ctime
vdir -lc /etc | head
```

```bash
# Directories themselves, long format
vdir -ld /etc/* | head
```

```bash
# Full ISO timestamps for an audit trail
vdir -l --full-time /var/log/audit | head
```

```bash
# Recursion: long listing of a whole tree
vdir -R /opt/app | head -40
```

```bash
# Reproducible ordering regardless of locale
LC_ALL=C vdir /usr/bin | head
```

```bash
# Columnar output from the long-format tool: cross into dir's territory
vdir -C /usr/bin | head
```

```bash
# Classify entries while keeping the long format
vdir -lF /usr/bin | head
```

```bash
# Verify the identity yourself: no output means byte-identical
diff <(vdir /usr/bin) <(ls -l -b /usr/bin) && echo identical
```

## Nuances and Gotchas

- **Not portable.** GNU-only, like `dir`: no macOS, no BSDs, no BusyBox, and POSIX.1-2018 does not define it. `ls -l` is the portable spelling.
- **Same parsing trap as `ls`.** Long format is friendlier to eyeballs but not a data format: names with spaces occupy multiple columns, `total` lines interleave, locale collation reorders, and a filename containing a newline makes line-based parsing ambiguous or malicious. Use globs or `find -print0 | xargs -0` for machines.
- **Escaping is the only quoting.** Default `-b` shows `tab\tfile`, but names with spaces are printed bare — no quotes, no escape — so `awk '{print $NF}'`-style field picking still breaks. `ls -Q` quotes whole names; `--quoting-style` can override.
- **mtime vs ctime vs atime.** `-t` sorts by content modification; `-c` by inode status change (chmod, chown, link count, rename). A file whose permissions changed "looks unchanged" to `-lt` but shows under `-ct`.
- **Locale collation.** `[A-Z]` range expectations fail in UTF-8 locales; prefix with `LC_ALL=C` when the ordering matters.
- **Color is opt-in.** `vdir` ships colorless; `--color` plus an `LS_COLORS` palette from [dircolors](./dircolors.md) is required.
- **Exit codes match `ls`:** 1 for minor problems, 2 for serious trouble (see [dir](./dir.md) for the table).

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Listed everything requested |
| 1 | Minor problems (e.g. an unreadable subdirectory encountered during `-R`) |
| 2 | Serious trouble (e.g. cannot access a command-line argument) |

## Related Commands

- [`ls`](./ls.md) — the parent command; `vdir` ≡ `ls -l -b`.
- [`dir`](./dir.md) — the columnar sibling; `vdir -C` ≈ `dir` back again.
- [`dircolors`](./dircolors.md) — generates the `LS_COLORS` database `--color` consumes.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [find](../../shell/find.md) — predicate-based tree walking for scripts, instead of parsed listings.
- [xargs](../../shell/xargs.md) — safe filename consumption with `-print0`/`-0`.
- [man pages](../../reference/man-pages.md) — the complete shared option matrix.

## Interview Questions

### Q: What is the exact relationship between vdir, ls, and dir?

All three are built from one coreutils source with different compiled-in defaults: `vdir` ≡ `ls -l -b`, `dir` ≡ `ls -C -b`, and bare `ls` chooses columns or one-per-line depending on whether stdout is a tty. Any `ls` option works with any of them. Verified equivalence: `diff <(vdir /usr/bin) <(ls -l -b /usr/bin)` is empty.

### Q: Why would anyone type vdir instead of ls -l?

History and determinism. The name eases the MS-DOS-to-Unix transition (a `DIR`-like command that showed full details), and pinning the format removes the tty-vs-pipe behavior switch that makes bare `ls` output unpredictable between interactive and scripted use. In practice it is a curiosity today: portable scripts should spell out `ls -l` explicitly rather than depend on a GNU-only binary.

### Q: Is vdir standardized? What happens on macOS or in a minimal container?

No — POSIX.1-2018 lists `ls` but not `vdir` or `dir`. macOS and the BSDs do not ship them and BusyBox omits them, so `vdir` fails with "command not found" outside GNU userland, including slim Docker images based on busybox or alpine (alpine uses busybox `ls` unless coreutils is installed).

### Q: How do you make vdir output suitable for diffing across machines?

Freeze everything locale- and environment-dependent: `LC_ALL=C vdir -ln --time-style=long-iso` gives numeric UIDs/GIDs, ISO timestamps, C-collation order, and C-escaped names. Without that, user-name resolution, locale collation, and timestamp formats silently differ between hosts and make diffs noisy.

### Q: What does the `total N` line at the top of a vdir listing mean, and why does it disagree with du?

It is the sum of allocated 1 KiB blocks for the listed entries (512-byte units if `POSIXLY_CORRECT` is set). Sparse files and differing block-size conventions make it disagree with both apparent byte sizes and `du`'s default unit — the same duality the `ls -s` vs `du` comparison shows.

### Q: A filename with a newline is in a directory. What do vdir and ls -l show, and what do you do about it?

Both print the name with the newline escaped by default (`nl\nfile` in `vdir`/`dir`, since `-b`-style quoting is forced; modern `ls` on a tty uses shell-escape quoting, in a pipe raw bytes). The long-format line structure survives, but any line-based parser reading the listing will treat one file as two names — which is exactly why filename-safe automation uses `find -print0 | xargs -0` or shell globs instead of listing output.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/vdir.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
