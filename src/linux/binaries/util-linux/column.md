# column — columnate lists and build tables from text

## Overview

`column` formats its input into multiple columns or, in the mode most people
actually use, into an aligned **table**: split each line on separator characters,
treat the first line as a header, and pad every cell to its column's width. It is
the standard answer to "how do I pretty-print /etc/passwd, CSV-ish output, or a
long word list" and one of the most quietly powerful tools in the BSD-derived
set. Debian bookworm ships the modern util-linux rewrite in the `bsdextrautils`
package at `/usr/bin/column` (it replaced the older `bsdmainutils` version).

Two personalities live in one binary:

- **Fill mode** (BSD classic, and the default): spreads input lines across
  multiple columns like `ls` does — one item per line in, N columns out.
- **Table mode** (`-t`): splits rows on separators and aligns them like a
  spreadsheet. Since the util-linux rewrite it also supports right alignment,
  hidden/reordered/renamed columns, truncation, tree layouts, and JSON output.

It reads files given as operands or standard input. Confusions: with `paste`
(merges files, does not align), with `fmt`/`fold` (re-wrap paragraph text, not
tables), and with `colrm`/`col` (name-adjacent, different jobs).

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/column |
| Lineage | 4.3BSD-Reno; rewritten in util-linux (2.30, 2017) on libsmartcols |
| Standards | None — not in POSIX; BSD/util-linux convention |

## Synopsis

```
column [options] [file ...]
```

Common one-line forms:

```
ls | column                     # fill mode: multi-column list, rows first
column -t -s, file.csv          # table mode, comma-separated
column -ts: /etc/passwd         # table mode, colon-separated
column -J -N a,b,c < data       # JSON output with named columns
```

## How It Works

### Fill mode: the ls-like layout

Without `-t`, each input line is one cell. `column` computes the widest cell and
the number of columns that fit in the output width, then fills **rows before
columns** (down the first column first, like `ls`). `-x` flips this to fill
columns before rows (across). The layout is deterministic given the width, so
scripts can rely on it — but note that stdout-to-a-terminal versus a pipe can
change the assumed width if `-c` is not given.

```bash
$ ls /usr/share/doc | head | column -c 60   # down-the-first-column layout
$ ls /usr/share/doc | head | column -x -c 60  # across-the-row layout
```

### Table mode: the spreadsheet pipeline stage

With `-t`, every line is split on any of the characters given with `-s`
(space-separated list; default: whitespace runs), the first line supplies the
header, and all cells are padded so columns align. The number of columns is
derived from the widest row. Cells are separated by two spaces by default;
`-o` changes the output separator.

```bash
$ printf 'name,uid\nroot,0\ndaemon,1\n' | column -t -s,
name    uid
root    0
daemon  1
```

```
raw lines ──► split on -s chars ──► widest-cell per column ──► pad + join with -o
              (no quoting rules!)   (header = first line)     (default: 2 spaces)
```

### What the rewrite added

The util-linux rewrite (2017) rebuilt `column` on libsmartcols — the same table
engine `findmnt`, `lsblk`, and `lslogins` render with. That brought:

- **Named columns** (`-N a,b,c`) instead of relying on the first input line.
- **Ordering** (`-O`), **hiding** (`-H`), **right alignment** (`-R`),
  **truncation** (`-T`) of over-wide columns.
- **JSON output** (`-J`) — rows become objects keyed by column names.
- **Tree layout** (`-r`/`-i`/`-p`) — render parent/child relations with box
  characters, like `lsblk` does.

This is why `column -J` is a legitimate poor-man's JSON encoder for delimited
logs, and why modern `column` behaves differently from the BSD/macOS `column`
(whose option set is much smaller).

## Options That Matter

### Layout modes

| Option | Effect |
| --- | --- |
| `-t, --table` | Table mode: split rows on `-s` separators and align columns |
| `-x, --fillrows` | Fill mode: fill columns before rows (default fills rows first) |
| `-c, --output-width <w>` | Output width in characters |
| `-o, --output-separator <str>` | String between table cells (default: two spaces) |
| `-s, --separators <chars>` | Input separator characters for table mode |

### Table shaping (util-linux rewrite)

| Option | Effect |
| --- | --- |
| `-N, --table-columns <names>` | Comma-separated column names (replaces first-line header) |
| `-d, --table-noheadings` | Don't print the header line |
| `-O, --table-order <cols>` | Output column order |
| `-H, --table-hide <cols>` | Hide columns (still parsed) |
| `-R, --table-right <cols>` | Right-align these columns |
| `-T, --table-truncate <cols>` | Truncate over-wide cells in these columns |
| `-J, --json` | JSON output; `-n` sets the table name |
| `-r, --tree <col>` / `-i, --tree-id` / `-p, --tree-parent` | Tree rendering from an id/parent relation |

## Usage Patterns

```bash
# Align /etc/passwd fields on the colon separator
column -t -s: /etc/passwd | less -S
```

```bash
# Pretty-print mount output: multiple separator characters at once
findmnt -rno TARGET,SOURCE,FSTYPE,OPTIONS | column -t
```

```bash
# CSV-style data without a real CSV parser (watch out for quoted commas)
column -t -s, < orders.csv
```

```bash
# Keep empty cells visible in table mode: choose an explicit separator
column -t -s'|' -o '|' < fixed.log
```

```bash
# Right-align numeric columns, hide an internal one
column -t -s, -R size,inodes -H internal < df-dump.txt
```

```bash
# JSON out of a colon-separated dump
column -J -N user,pass,uid,gid,gecos,home,shell -s: < /etc/passwd | jq .
```

```bash
# Multi-column word list, filled across instead of down
printf '%s\n' word1 word2 word3 word4 word5 | column -x -c 40
```

```bash
# Width-bounded table for 80-column reports
column -t -s: -c 80 /etc/group
```

```bash
# Tree rendering from parent/child columns
printf 'id,pid,name\n1,,root\n2,1,child\n3,1,other\n' \
  | column -t -s, -r name -i id -p pid
```

```bash
# Show a table without its header (names given on the command line)
column -t -s, -N day,count -d < counts.csv
```

```bash
# Long list into columns for quick visual scanning
ls /usr/bin | column -c "$COLUMNS"
```

```bash
# Rename/reorder columns without editing the file
column -t -s, -N a,b,c -O c,a < data.csv
```

## Nuances and Gotchas

- **Table mode is not CSV-aware.** Splitting happens on *any* occurrence of the
  separator characters; quoted commas, escaped separators, or embedded newlines
  will mangle rows. Use a real CSV tool for real CSV.
- **First line becomes the header.** A classic surprise: piping data straight
  into `column -t` swallows the first data row as a header. Either supply `-N`
  names or accept the convention deliberately.
- **Empty cells vanish with the default separator.** The default output
  separator is *two spaces*, so `a,,b` renders indistinguishably from `a,b`.
  Set `-o` to a visible string to debug, and remember empty input fields are
  legal but easy to miscount.
- **Fill mode depends on width.** Without `-c` the assumed width may differ
  between terminal and pipe, changing the layout between interactive and scripted
  runs — pin `-c` when output must be stable.
- **BSD/macOS column is a different beast.** The `-N`, `-O`, `-J`, `-R`, `-T`,
  `-H`, tree flags do not exist there; portable scripts should use only
  `-t -s -o -c -x`.
- **UTF-8 widths are handled by the libsmartcols rewrite** (better than the
  BSD original), but combining characters and emoji width remain edge cases in
  any terminal-based alignment.
- **`-t` vs `-x` confusion.** `-t` is a mode (table), `-x` is a fill direction
  (columns before rows). They are not opposites and can even combine.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Usage error, cannot open input, or allocation failure (not formally documented) |

## Related Commands

- [`col`](./col.md) — filters reverse line feeds; same BSD-derived collection
- [`colcrt`](./colcrt.md) — CRT preview filter; same collection
- [`colrm`](./colrm.md) — deletes a column range instead of aligning
- [`overview`](./overview.md) — index of all util-linux collection pages
- [bash](../../shell/bash.md) — pipelines where `column -t` is the presentation stage

## Interview Questions

### Q: What is the difference between column's fill mode and table mode?

Fill mode treats each input line as one cell and spreads them into N columns like
`ls` does (down-then-across by default, `-x` to flip). Table mode (`-t`) splits
each line on separator characters and aligns the fields into a padded table with
a header. Fill mode is for lists; table mode is for structured records.

### Q: Why does column -t sometimes drop what looks like a data row?

Because in table mode the first input line is interpreted as the header row. If
your data has no header, the first record disappears from the cells. Fix by
providing `-N name1,name2` to name the columns explicitly (optionally with `-d`
to hide the header), or prepend a dummy header line.

### Q: How do you make empty fields visible in column -t output?

Set the output separator explicitly with `-o` (e.g. `-o '|'`); the default
two-space separator renders an empty cell and a short cell identically. Also
choose a single-character input separator with `-s` so you can count fields by
counting separators.

### Q: A script uses column -J -N a,b on macOS and fails. Why?

The JSON/table-shaping options are part of the util-linux rewrite (2.30-era, on
libsmartcols). macOS ships the BSD column, which supports only the classic
options (`-t`, `-s`, `-o`, `-c`, `-x`). Cross-platform scripts must limit
themselves to that subset or detect the implementation.

### Q: What replaced the older Debian column and why does it matter?

Debian used to ship `column` from `bsdmainutils`; bookworm ships the util-linux
rewrite in `bsdextrautils`. The rewrite unified rendering with `lsblk`/`findmnt`
via libsmartcols, added JSON/tree/alignment controls, and fixed several layout
bugs — meaning outputs (column widths, header handling) can differ between
distributions, which matters for regression-sensitive scripts.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/column.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
