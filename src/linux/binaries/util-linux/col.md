# col — filter reverse line feeds out of a text stream

## Overview

`col` is a one-purpose filter from the BSD toolchest: it reads a stream that may contain
*reverse line feeds*, *half-line movements*, *backspace overstriking*, and alternate-charset
shift codes, and re-emits the same text so that a dumb output device can print it by moving
**forward only** — line by line, column by column. Along the way it compacts runs of spaces
into tabs (or the reverse, with `-x`). It reads standard input and writes standard output;
it accepts no file operands.

In Debian bookworm it ships in the `bsdextrautils` package at `/usr/bin/col`, built from the
util-linux source tree, which absorbed the historical BSD implementation. Its classic role is
the last stage of the `man` pipeline: troff/nroff produce device-independent output that uses
reverse half-line motion for subscripts and superscripts and overstriking for bold and
underlined text; `col` flattens that into something a terminal or line printer can render.

It is often confused with `colcrt` (same family — converts underlining to dashes for CRT
previewing), with `colrm` (similar name, completely unrelated — it deletes column ranges),
and with `cat -v` (which *displays* control characters instead of interpreting them).

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/col |
| Lineage | BSD heritage (4.3BSD era); implementation now lives in util-linux |
| Standards | None — not in POSIX; BSD convention |

## Synopsis

```
col [options]
```

Common one-line forms:

```
man ls | col -b          # classic: strip backspace overstriking from man output
col -bx < messy.txt      # no backspaces, tabs expanded to spaces
col -l 5000 < tbl.out    # raise the line buffer for deep reverse motion
```

## How It Works

### The problem: text streams that move backwards

Old typesetter output is a *script* of motions, not lines. To print an underlined word,
nroff writes `w`, backspace, `_`, per character — the terminal or printer strikes `_`
over `w`. To place a subscript, it moves **down half a line**; superscripts move **up
half a line**; tables move the platen **upwards whole lines**. None of that survives on
a terminal that can only advance.

`col` simulates the motions on a two-dimensional grid of character cells and then drains
the grid in strict reading order:

```
            input stream                col                      output
  ┌───────────────────────────────┐   ┌──────────────┐   ┌───────────────────┐
  │ "x" ESC-9 "i" (half reverse)  │   │ play motions │   │ one line at a     │
  │ VT      (reverse linefeed)    │──►│ on a cell    │──►│ time, forward     │
  │ "w" BS "_" (overstrike)       │   │ grid + buffer│   │ motion only,      │
  │ SO ... SI  (alt charset)      │   │              │   │ tabs where space  │
  └───────────────────────────────┘   └──────────────┘   └───────────────────┘
```

Everything that cannot be expressed as "next column" or "next line" is resolved in the
grid: overstrikes collapse to one character per cell, half-line motion becomes whole
lines, and reverse motion is absorbed by the buffer.

### Control sequences it interprets

| Input sequence | Meaning |
| --- | --- |
| `ESC-7` | reverse line feed (move up one full line) |
| `ESC-8` | forward half line feed (move down half a line) |
| `ESC-9` | reverse half line feed (move up half a line) |
| `VT` (0x0B) | reverse line feed |
| backspace (0x08) | move one column left (for overstriking) |
| carriage return (0x0D) | move to column 1 |
| newline (0x0A) | end the line, move down |
| `SI` (0x0F) | shift in — return to the normal character set |
| `SO` (0x0E) | shift out — switch to the alternate (e.g. greek) character set |
| tab (0x09), space (0x20) | advance, with tab-stop semantics |

Any *other* control character or escape sequence is discarded. `-p` relaxes this and
passes unrecognized escape sequences through unchanged.

### The line buffer

Reverse motion requires remembering lines that were already emitted. `col` keeps a
buffer of at least **128 lines** (`-l num` raises it). Input that walks further back
than the buffer holds makes the filter abort with an error — this is the classic
failure mode with pathological `tbl` output that jumps many lines upwards.

### Whitespace policy

By default (`-h`) the output compacts multiple spaces into tabs where tab stops allow,
which is what line printers wanted. `-x` forces *spaces only* — important when the
result will be reprocessed by column-counting tools such as `colrm` or `cut`.

### `-b` and overstriking

Bold on old output devices was `c BS c` (strike `c` twice); underline was `c BS _`.
Without `-b`, `col` preserves the backspaces so an overstriking device can still
render them. With `-b` it emits **only the last character written to each column
position** — the backspaces disappear and the text is clean. This is why
`man ... | col -b` was the canonical incantation for a long time.

### `-f` and half lines

Half-line motion is *down* (forward) or *up* (reverse). Reverse half-lines are always
handled; forward half-lines are only honored with `-f`. Without it, a forward
half-line feed is rounded up to a whole-line feed, losing sub/superscript placement —
acceptable on terminals, not on film recorders, which is what `-f` was for.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-b` | Do not emit backspaces; print only the last character per column (drops overstrike bold/underline) |
| `-f` | Allow forward half-line feeds instead of rounding them to whole lines |
| `-h` | Convert runs of spaces to tabs where possible (default) |
| `-x` | Output spaces instead of tabs |
| `-p` | Pass unknown escape sequences through instead of discarding them |
| `-l num` | Buffer at least `num` lines (default 128) — raise for deep reverse motion |

## Usage Patterns

```bash
# The classic: clean troff backspace overstriking out of a man page dump
man ls | col -b > ls.txt
```

```bash
# Capture of an old terminal session full of overstrikes — make it readable
col -b < typescript > typescript.clean
```

```bash
# No backspaces AND no tabs: pure space-based output for column tools
groff -man -Tlatin1 foo.1 | col -bx | cut -c1-60
```

```bash
# Feed the device-independent troff output the way printers used to get it
troff -ms report.ms | col | lpr
```

```bash
# Pathological tbl output that jumps upward across many lines
tbl bigtable.roff | nroff | col -l 5000 > out.txt
```

```bash
# Keep unknown escape sequences (e.g. your own ESC sequences) alive
cat -v input | col -p
```

```bash
# Inspect what col actually receives (control chars made visible)
printf 'a\bb x\x0by\n' | cat -A        # see the BS and VT before filtering
```

```bash
# tabs stay tabs by default; force spaces when reprocessing
printf 'a\tb\n' | col -x
```

```bash
# Compare: colcrt converts underlines to dashes for screen previewing
nroff -man page.1 | colcrt | less      # screen preview variant
nroff -man page.1 | col -b | lpr       # print variant
```

## Nuances and Gotchas

- **stdin only.** `col` has no file operands; `col file` is a usage error. Redirect
  (`col < file`) or pipe.
- **It silently eats unknown control characters.** Piping binary data through `col`
  destroys it. `-p` only rescues *escape sequences*, not arbitrary control bytes.
- **128-line buffer cliff.** Deep reverse motion (large `tbl` tables, some macro
  packages) aborts the filter. The fix is `-l`, but you must notice the error —
  output is truncated, not marked.
- **Default tab compaction surprises processors.** Piping `col` output into
  byte-counting tools gives shifted columns; use `-x` when the next stage counts
  characters.
- **Multibyte text is a weak spot.** `col` reasons in output columns; wide CJK
  glyphs, combining characters and other UTF-8 edge cases have historically been
  mishandled. Verify with your real locale before trusting alignment.
- **Modern `man` output rarely needs it.** groff's `-Tutf8` output is already clean
  and forward-only; the `man | col -b` habit survives from the `-Tlatin1`/`-Tnroff`
  era. It is harmless, just usually a no-op.
- **Not portable semantics.** macOS/BSD `col` and util-linux `col` are cousins but
  not identical (message text, edge-case handling). Scripts relying on exact
  overstrike behavior should be tested per platform.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success |
| nonzero | Usage or I/O error, or the line buffer was exhausted (not formally documented in the man page) |

## Related Commands

- [`colcrt`](./colcrt.md) — same filter family; converts underlining to dash rows for CRT previewing
- [`colrm`](./colrm.md) — similar name, different job: deletes a column range from input
- [`column`](./column.md) — the modern columnating filter for tables and lists
- [`overview`](./overview.md) — index of all util-linux collection pages
- [man-pages](../../reference/man-pages.md) — where `col` historically sat in the man rendering pipeline

## Interview Questions

### Q: What problem does `col` solve that `cat` does not?

`cat` is a byte pipe; `col` interprets motion control characters (reverse and half line
feeds, backspace overstrikes, charset shifts) and re-renders the text so it can be
printed with forward motion only. It is essentially a tiny page-layout engine over a
character grid, which is why troff output for old terminals and line printers had to
pass through it.

### Q: Why did `man | col -b` use to be ubiquitous, and why is it less needed today?

nroff `-Tlatin1`/`-Tnroff` output encoded bold and underline as backspace overstrikes
and used reverse half-line motion for sub/superscripts; terminals needed `col` to
linearize it. Modern man pages render through groff `-Tutf8` (or mandoc), whose output
is already terminal-ready, so `col` is usually a harmless no-op kept for old scripts.

### Q: What exactly does `col -b` do with `a<BS>b`?

It keeps only the last character written to each column position, so the output is `b`
with the backspace dropped. Without `-b` the backspace would be passed through so that
an overstriking device (or an overstrike-aware viewer) could still show the composite.

### Q: Name two concrete failure modes of `col`.

First, the 128-line default buffer: input whose reverse motion references earlier
lines beyond that depth aborts the filter mid-stream — cured with `-l num`. Second,
silent discarding of unrecognized control characters, which mangles binary or
escape-decorated input unless `-p` is used. Both produce no diagnostic in the output
itself, only on stderr.

### Q: How do `col`, `colcrt`, and `colrm` differ?

`col` generalizes the stream (removes reverse motion, manages overstrikes and tabs);
`colcrt` is a preview filter that converts underlining into rows of dashes for CRTs
and can double-space half-lines with `-2`; `colrm` deletes a column *range* from each
input line. The names suggest a family; the jobs are different.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/col.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
