# dir — list directory contents, always in columns

## Overview

`dir` is GNU `ls` wearing an MS-DOS costume: it is built from the same coreutils source as `ls` with a different set of compiled-in defaults, so that by default it lists entries **in columns** with **backslash-escaped quoting**, no matter whether stdout is a terminal or a pipe. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/dir`, next to `ls` and the third sibling `vdir`. The name exists for users arriving from MS-DOS, where `DIR` was *the* directory command; on Unix it found a second life as a way to get stable, pipe-independent columnar output.

`dir` is often confused with `ls` (same engine, terminal-adaptive defaults) and with `vdir` (the long-format twin). `dir` is equivalent to `ls -C -b`: same options, same sorting, same color support — only the defaults differ. It is not standardized by POSIX and is absent from macOS, the BSDs, and BusyBox, so scripts that call `dir` are silently GNU-only.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/dir |
| First appeared | GNU fileutils, early 1990s (modeled on the MS-DOS `DIR` command) |
| Standards | None — GNU extension, not in POSIX |

## Synopsis

```
dir [OPTION]... [FILE]...
```

Common one-line forms:

```
dir                     # columns, escaped names, current directory
dir -l [file...]        # long format (same layout as ls -l)
dir -a /etc | head      # include dot entries, pipe-stable output
dir --color /usr/bin    # same LS_COLORS palette as ls
```

## How It Works

### One engine, three front doors

`ls`, `dir`, and `vdir` share one implementation; each binary just pins different default options. Everything documented for `ls` — sorting keys, `-d`, `-a`, `-R`, `--time-style`, `--color`, `--quoting-style`, exit codes — applies to `dir` verbatim. The full option matrix lives on the [ls](./ls.md) page; this page concentrates on what makes `dir` different.

### The default-format decision

The only thing that separates everyday `dir` from everyday `ls` is how the output format is chosen:

```
                 ┌─────────────────────┐
                 │ stdout is a tty?    │
                 └──────┬───────┬──────┘
                 yes    │       │    no
                        ▼       ▼
   ls:      columns (-C),    one per line (-1),
            shell-escape     literal quoting,
            quoting, color   no color
            ────────────────────────────────
   dir:     columns (-C) and backslash escapes (-b) —
            unconditionally, on tty or pipe alike
            (color still only with --color)
```

Verified on this system: `diff <(dir /usr/bin) <(ls -C -b /usr/bin)` is empty — the two are byte-identical. Piped output proves the point:

```bash
$ printf 'abc\ndef\n' > a1; printf 'x' > b2
$ ls | head -2        # ls in a pipe: one per line
a1
b2
$ dir | head -2       # dir in a pipe: still columns
a1  b2
```

### Escaped names by default

`-b` (`--escape`) prints C-style escapes for nongraphic characters, so a file containing a tab or newline shows as `tab\tfile` and `nl\nfile` even in scripts, while bare `ls` in a pipe prints the raw bytes:

```bash
$ touch $'tab\tfile' $'nl\nfile'
$ dir | cat -A | tail -2      # cat -A makes the $ end-of-line visible
tab\tfile$
nl\nfile$
```

This is the practical reason `dir` exists beyond MS-DOS nostalgia: filenames cannot silently inject control characters into your terminal or log files.

### Sorting and selection

Default sort is alphabetical under the current locale's collation ("Sort entries alphabetically if none of `-cftuvSUX` nor `--sort` is specified", as `--help` puts it). `-t`, `-S`, `-v`, `-U`, `-r` and friends behave exactly as in `ls`. `-a` includes dot entries, `-A` drops only `.` and `..`, `-d` describes directories themselves, `-R` recurses.

## Options That Matter

### Format (dir's reason to exist)

| Option | Effect |
| --- | --- |
| `-C` (default) | Fill columns vertically, like `ls -C`, forced even into pipes |
| `-b` (default) | C-style escapes for nongraphic characters, forced even into pipes |
| `-l` | Long format — makes `dir` behave like `vdir` |
| `-1`, `-m`, `-x` | One per line / comma-separated / across rows |
| `-F` | Append type indicators (`/`, `*`, `@`, `\|`, `=`) |
| `-h` | Human-readable sizes with `-l`/`-s` |

### Selection, sorting, display

| Option | Effect |
| --- | --- |
| `-a`, `-A` | Include dot entries / minus `.` and `..` |
| `-d` | List directories themselves, not contents |
| `-R` | Recurse into subdirectories |
| `-t`, `-S`, `-v`, `-U`, `-r` | mtime / size / version / directory-order / reverse sort |
| `-i`, `-s` | Inode numbers / allocated blocks |
| `--color[=WHEN]` | Colorize via `LS_COLORS` (see [dircolors](./dircolors.md)) |
| `--quoting-style=WORD` | Override the forced `-b` escaping (literal, shell, c, ...) |
| `-I PATTERN` | Ignore matching entries |

## Usage Patterns

```bash
# MS-DOS muscle memory: plain directory listing in columns
dir
```

```bash
# Stable columnar output into a pipe or log — identical to on-screen
dir /usr/bin | head -20
```

```bash
# Long format without changing binary: same layout as ls -l
dir -lh /var/log | head
```

```bash
# Newest entries first, columnar, escaped — a quick "what changed here"
dir -t /etc | head
```

```bash
# Include hidden files
dir -a ~ | head
```

```bash
# Describe directories themselves, not their contents
dir -d /etc/* | head
```

```bash
# Recursion with classification markers
dir -FR /opt | head -30
```

```bash
# Same palette as ls: colors driven by LS_COLORS from dircolors
dir --color /usr/lib | head
```

```bash
# Control-character-proof listing for a suspicious directory
dir /tmp/upload | cat -A | head
```

```bash
# Natural version order for release artifacts
dir -v releases/ | head
```

```bash
# Reproducible ordering regardless of locale
LC_ALL=C dir /usr/bin | head
```

## Nuances and Gotchas

- **Not portable.** `dir` is a GNU extension: no macOS, no BSD, no BusyBox. A script using `dir` breaks the moment it meets a non-GNU system, while `ls -C` works everywhere. POSIX specifies `ls`, not `dir`/`vdir`.
- **It is still `ls` underneath.** Every `ls` parsing trap applies: locale collation reorders names, column formats wrap at terminal width, and parsing `dir` output in scripts is as wrong as parsing `ls`. Machine-readable listing belongs to globs, `find -print0 | xargs -0`, or `for f in *`.
- **Escapes are display, not round-trip.** `dir` prints `nl\nfile` but that string is not a shell-quoting of the name; you cannot `eval` it back. For safe re-reading use `ls -Q` (double-quote style) or, better, don't parse listings at all.
- **Color does not turn on by itself.** Unlike interactive `ls` setups that alias `--color=auto`, `dir` ships colorless; pass `--color` explicitly and configure the palette via [dircolors](./dircolors.md).
- **Exit codes match `ls`.** 1 for minor problems (unreadable subdirectory during `-R`), 2 for serious trouble (an inaccessible command-line operand). Scripts that only test `"$?" -eq 0` miss partial failures.
- **`-b` vs `--quoting-style=escape`.** The default forced quoting is C escapes; filenames with spaces stay bare (no quotes added), so word-splitting on output is still a hazard.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Listed everything requested |
| 1 | Minor problems (e.g. an unreadable subdirectory encountered during `-R`) |
| 2 | Serious trouble (e.g. cannot access a command-line argument) |

## Related Commands

- [`ls`](./ls.md) — the terminal-adaptive parent command; `dir` ≡ `ls -C -b`.
- [`vdir`](./vdir.md) — the long-format sibling; `vdir` ≡ `ls -l -b`.
- [`dircolors`](./dircolors.md) — generates the `LS_COLORS` database `--color` consumes.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [find](../../shell/find.md) — recursive, predicate-based listing when one level isn't enough.
- [xargs](../../shell/xargs.md) — the correct way to consume filename lists (instead of parsing listings).
- [man pages](../../reference/man-pages.md) — where the complete shared option matrix is documented.

## Interview Questions

### Q: Why do `dir` and `vdir` exist when `ls` can do everything they do?

They are the same code with different compiled-in defaults, created for MS-DOS converts (`dir` = columns) and for a guaranteed long format (`vdir` = `ls -l -b`). The modern justification is determinism: their output format does not change when stdout stops being a terminal, whereas `ls` silently switches from columns to one-per-line and from shell-escape to literal quoting. That said, the better scripting answer is to pass explicit flags to `ls` — or not parse listings at all.

### Q: What exactly does `dir` print by default, and how do you prove it?

`dir` defaults to `ls -C -b`: entries sorted alphabetically by locale collation, filled into columns vertically, nongraphic characters shown as C escapes — on a terminal and in a pipe alike. The proof is a byte comparison: `diff <(dir /usr/bin) <(ls -C -b /usr/bin)` produces no output. Colors are not part of the deal; `--color` must be requested explicitly.

### Q: Is `dir` POSIX? What breaks if a build script depends on it?

No. POSIX.1-2018 specifies `ls` but not `dir` or `vdir`; they are GNU coreutils extensions. macOS and the BSDs do not ship them, and BusyBox does not either, so a script calling `dir` fails on those platforms with "command not found". Portable scripts use `ls -C` (or `ls -l`) with explicit flags.

### Q: A colleague says "dir output is safe to parse because it escapes weird characters." What's wrong with that?

Escaping only neutralizes nongraphic bytes; it does not make the output structurally parseable. Names with spaces are not quoted, locale collation can reorder entries, columns wrap at terminal width, and the escape format (`nl\nfile`) is for human eyes — not a shell-safe quoting you can eval back to the original name. Filename-safe automation still requires globs, `find -print0 | xargs -0`, or NUL-delimited data.

### Q: What are `dir`'s exit codes and when does it return 1 vs 2?

Same contract as `ls`: 0 when everything listed, 1 for minor problems such as an unreadable subdirectory encountered during a recursive listing (the rest of the output is still produced), and 2 for serious trouble such as an inaccessible command-line operand. Checking only for nonzero status conflates "partial listing" with "total failure".

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/dir.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
