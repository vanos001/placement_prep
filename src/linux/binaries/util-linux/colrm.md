# colrm — remove columns from each line of input

## Overview

`colrm` is a filter with exactly one behavior: it deletes a range of columns from
every input line. With a start argument it removes everything from that column to
the end of the line; with start *and* stop it removes just that inclusive range;
with no arguments it is an identity filter. Columns are numbered from 1, and the
counting is strictly per input *character* — there is no tab-stop expansion, no
backspace interpretation, no terminal emulation.

It reads standard input and writes standard output (no file operands). In Debian
bookworm it ships in the `bsdextrautils` package at `/usr/bin/colrm`; the
implementation is BSD-derived and now lives in the util-linux source tree.

Despite the name it is not part of the `col`/`colcrt` rendering family — it shares
only the "col-" prefix. It predates and parallels `cut -c` (coreutils); the two
cover overlapping ground with different syntax, and `awk substr()` is the usual
heavy-duty alternative. Interviewers like it as a test of "do you actually know
what a filter is" and as a segue into column counting versus tab handling.

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/colrm |
| Lineage | BSD heritage (early BSD); implementation now lives in util-linux |
| Standards | None — not in POSIX; BSD convention |

## Synopsis

```
colrm [start [stop]]
```

The three modes:

```
colrm                 # identity: passes input through unchanged
colrm 5               # delete column 5 through end of line
colrm 3 7             # delete columns 3..7 inclusive, keep the rest
```

## How It Works

### Column arithmetic

Columns are counted in input characters starting at 1. For each line, `colrm`
copies characters `1 .. start-1`, skips characters `start .. stop` (or
`start .. end-of-line` when stop is absent), then copies the remainder. There is
no state between lines: every line is processed identically, which makes the
filter streamable and cheap.

```
line:      a  b  c  d  e  f
column:    1  2  3  4  5  6

colrm 3 5  →  a  b        f      →  "abf"
colrm 4    →  a  b  c             →  "abc"
colrm      →  a  b  c  d  e  f    →  "abcdef" (identity)
```

### Verified behavior

```bash
$ printf 'abcdef\n' | colrm 3 5
abf
$ printf 'abcdef\n' | colrm 4
abc
$ printf 'abcdef\n' | colrm
abcdef
```

A trailing fragment: if `stop` exceeds the line length the result is simply the
prefix before `start`; no padding is added. Because the filter is stateless,
every line of a multi-line stream gets the identical treatment — there is no
header special case, no continuation logic, no per-line conditionals.

### Tabs and backspaces are ordinary characters

`colrm` does not know what a terminal would do with a tab. A tab is one column;
a backspace is one column. So a line containing `a<TAB>b` counts as `a`=1,
`<TAB>`=2, `b`=3 — *not* as "b at column 9". If your data has tabs and you want
visual columns, expand first (`expand`) and unexpand after (`unexpand`), or do
the surgery in `awk`. This is the single most common wrong mental model.

### Compare with cut and awk

| Tool | Selection | Tabs | Notes |
| --- | --- | --- | --- |
| `colrm 3 7` | character columns 3-7 deleted | counted as 1 char | delete a range |
| `cut -c1-2,8-` | character columns kept | counted as 1 char | *keep* ranges, inverse style |
| `awk '{print $1 $NF}'` | fields | splits on runs of blanks | field, not column, oriented |

`colrm` expresses "remove this slice"; `cut` expresses "keep these slices". For a
single range they are duals: `colrm 3 7` ≡ `cut -c1-2,8-` on the same input.

### Fixed-width data: the natural habitat

`colrm` earned its keep in an era of fixed-width records: `ps`, `ls -l`, `who`,
`netstat`, compiler listings, mainframe exports. The workflow was: print with
fixed columns, delete the unwanted slice. The modern equivalents prefer field
splitting (`awk`, `cut -f`), which is why `colrm` faded — but fixed-width
formats never fully died (banking exports, Cobol legacy, `dpkg-query` output):

```bash
# dpkg-query prints fixed-width; drop the architecture column
dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' \
  | expand -t 40 | colrm 40 52
```

The lesson generalizes: when you must delete a *position* rather than a *field*,
`colrm` is still the most direct expression of the intent.

## Options That Matter

`colrm` has no options besides its two positional arguments:

| Argument | Effect |
| --- | --- |
| (none) | Identity filter — pass input through |
| `start` | Delete from column `start` to end of line |
| `start stop` | Delete columns `start` through `stop` inclusive |

## Usage Patterns

```bash
# Strip a fixed-width header field: drop the first 8 characters of each line
ps -ef | tail -n +2 | colrm 1 8
```

```bash
# Remove a checksum column (last 32 chars) by deleting from a computed start
colrm $(( $(head -1 sums.txt | wc -c) - 32 )) < sums.txt
```

```bash
# Cut the middle of fixed-width records: keep serial + message, drop pad zone
cat records | colrm 20 39
```

```bash
# Identity mode as a no-op placeholder in a pipeline you will extend later
grep ERROR app.log | colrm
```

```bash
# Delete the filename part of 'ls -l' style fixed columns (chars 21+)
ls -l | colrm 55
```

```bash
# Pre-expand tabs so deletion is visual-column accurate
expand data.tsv | colrm 10 20 | unexpand --first-only - 
```

```bash
# Age-old trick: remove ANSI-ish trailing junk from fixed reports
who | colrm 40
```

```bash
# Inverse using cut for the same result (know both idioms)
printf 'abcdef\n' | colrm 3 5      # abf
printf 'abcdef\n' | cut -c1-2,6-   # abf
```

```bash
# Truncate every line to its first 12 columns (delete 13..end)
printf '%s\n' one-line-here another-line-here | colrm 13
```

## Nuances and Gotchas

- **Tabs count as one column.** Every veteran gets bitten once. For tab-heavy data
  run `expand` first or use field-oriented tools (`cut -f`, `awk`).
- **Backspaces count as one column** and are not interpreted; combining `colrm`
  with overstruck output produces surprises. Clean with `col -b` first if the data
  came from troff-era sources.
- **Column counting is per character, not per display cell.** With UTF-8 input,
  each byte of a multibyte character is... counted as input characters in modern
  implementations, but historically byte-oriented behavior varies — do not trust
  `colrm` for multibyte column math; use `awk` with `substr` under a UTF-8 locale.
- **Nonsense ranges are not diagnosed.** A `start` greater than `stop` does not
  produce a helpful error; test edge cases before scripting.
- **stdin only.** No file operands, no options like `-d` — a hard filter with two
  integers is its entire interface.
- **Deletion, not extraction.** People reach for `colrm` wanting `cut -c` behavior;
  the mental flip (remove vs keep) causes off-by-one selection bugs.
- **It is stateless between lines.** No header awareness, no continuation
  handling: quoted CSV rows that span lines are cut per physical line, which
  silently corrupts them. Restrict `colrm` to line-oriented record formats.
- **Streams, not files: buffering is unbuffered-ish line I/O.** Performance on
  gigabyte inputs is fine (it is a trivial filter), but there is no seek or
  mmap trickery — column deletion always means a full copy of the prefix and
  suffix of every line.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success |
| nonzero | Usage error (malformed integers) or I/O failure (not formally documented) |

## Related Commands

- [`col`](./col.md) — name-sibling, different job: filters reverse line feeds
- [`colcrt`](./colcrt.md) — name-sibling, different job: CRT preview filtering
- [`column`](./column.md) — the columnating filter of the same collection
- [`overview`](./overview.md) — index of all util-linux collection pages
- [sed-awk](../../shell/sed-awk.md) — substr/field processing as the heavy-duty alternative

## Interview Questions

### Q: What does `colrm 5` do versus `colrm 5 9`?

`colrm 5` deletes column 5 through the end of every line (a suffix deletion).
`colrm 5 9` deletes exactly columns 5-9 inclusive and keeps everything after
column 9. Columns count from 1, per character.

### Q: Why can colrm results be wrong on tab-containing data?

Because `colrm` counts a tab as a single column instead of advancing to the next
tab stop. Visual columns and character columns diverge from the first tab onward.
Fix by pre-processing with `expand` (then `unexpand` after) or by using
field-oriented tools such as `awk` or `cut -f`.

### Q: How do you express colrm 3 7 with cut?

`cut -c1-2,8-` — `cut` selects the ranges to *keep*, `colrm` selects the range to
*delete*. The two are duals for a single range; for multiple disjoint deletions,
`cut`'s keep-lists compose more naturally than chained `colrm` stages.

### Q: Is colrm locale/UTF-8 safe for column surgery?

Treat it as character/byte oriented with no display-width awareness: wide CJK
glyphs and combining marks do not occupy the visual columns their bytes suggest.
For multibyte-correct column slicing use `awk` with `substr()` under a UTF-8
locale (or Python), and verify with a real sample.

### Q: Where does colrm sit historically and why does it still ship?

It is one of the oldest BSD filters, kept for compatibility with decades of
scripts and because it is a trivially correct streaming filter. Modern work
usually uses `cut`/`awk`, but `colrm` survives in the BSD-derived `bsdextrautils`
package and in interview questions about column versus field semantics.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/colrm.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
