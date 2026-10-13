# colcrt — filter nroff output for CRT previewing

## Overview

`colcrt` is the screen-oriented sibling of `col`: it takes nroff/troff output —
complete with backspace overstriking and half-line motion — and rewrites it for
previewing on a CRT terminal. Its two signature behaviors are converting
**underlining into a separate row of dashes** (because CRTs of the era could not
overstrike) and optionally printing **half-lines as full blank-line spacing** with
`-2`, which keeps superscripts and subscripts legible on a device that cannot move
the cursor by half a line.

Like `col` it reads standard input and writes standard output and has no file
operands. In Debian bookworm it ships in the `bsdextrautils` package at
`/usr/bin/colcrt`, built from the util-linux source tree's BSD-derived code.

It is easily confused with `col` (the general reverse-linefeed filter — `colcrt`
adds the underline-to-dash and double-spacing transformations) and with `colrm`
(name only). Historically it was invoked by `man`-style preview scripts on
dumb terminals; today groff's UTF-8 output makes it a curiosity, but it still
works and still shows up in pipeline archaeology questions.

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/colcrt |
| Lineage | BSD heritage (3BSD era); implementation now lives in util-linux |
| Standards | None — not in POSIX; BSD convention |

## Synopsis

```
colcrt [options]
```

The two historical one-letter options:

```
nroff -man page.1 | colcrt -      # suppress all underlining
nroff -man page.1 | colcrt -2     # print half-lines, i.e. double-space
```

## How It Works

### What nroff output looks like before colcrt

nroff encodes underline as `c BS _` (character, backspace, underscore) and bold as
`c BS c`. It positions subscripts by emitting a *reverse half-line feed* and
superscripts via half-line movement. A terminal that can neither overstrike nor
move vertically by fractions of a line shows this as garbage: stray underscores
between letters, text drifting up and down.

```
input (logical)            colcrt output on a CRT
Underlined word            Underlined word
 w  w  w  w  w  w           ----------- (dash row below the text)
x2 where 2 is a sup        x2 ... with -2: the raised "2" gets its own line
```

### The underline transformation

`colcrt` scans for backspace-overstrike sequences. Character–underscore pairs
become plain characters on the text line plus a dash at the matching column of a
*shadow line* printed after the text line. Back-to-back underlined text produces
a continuous dash row. This is the feature that distinguishes it from plain
`col -b`, which would simply throw the underscores away.

### Half-lines and `-2`

Without `-2`, a half-line boundary is "adopted": content that sits above or below
the baseline is merged onto the current line, which is fine for subscripts but can
crowd superscripts into the previous line. With `-2`, every half-line boundary
becomes a real line break — effectively **double spacing** the output — so raised
or lowered characters land on their own lines and remain readable.

### Suppressing underlines entirely: `-`

The lone `-` option suppresses all underlining: no dashes, and the underscore
overstrikes are dropped. The BSD documentation calls out the special case this
was designed for: previewing `tbl(1)` tables with the `allbox` option, where the
dense grid of underlines would otherwise flood the screen.

### What it does not do

`colcrt` is not faithful to the printed page. Composite overstruck glyphs are
reduced (it is a preview filter, not a typesetter), and it does not attempt the
full cell-grid simulation `col` does. When in doubt about exact edge behavior on
pathological input, prefer `groff -Tutf8` or `mandoc` today — or verify
experimentally, since the tool predates modern Unicode handling.

### Where it sat in the pipeline

The classical documentation workflow had two output paths from one roff source:
the *printer* path (`nroff | col | lpr`) and the *screen preview* path
(`nroff | colcrt | more`). Understanding that split explains the tool's design:
previewing had to be cheap and terminal-friendly, fidelity was checked on paper.

```
 doc.ms ──► nroff ──► ┬── col ────► line printer  (overstrikes preserved)
                      └── colcrt ─► CRT terminal  (dashes for underlines)
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-` | Suppress all underlining — designed for previewing `tbl` `allbox` tables |
| `-2` | Print all half-lines, effectively double spacing — keeps superscripts/subscripts readable |

That is the entire option set. There are no file operands; input is stdin.

## Usage Patterns

```bash
# Historical: preview a formatted man page on a dumb terminal
zcat /usr/share/man/man1/ls.1.gz | nroff -man | colcrt | less
```

```bash
# Same, but underlines suppressed for a cleaner screen
groff -man -Tascii page.1 | colcrt -
```

```bash
# Read superscripts/subscripts: let -2 turn half-lines into real lines
nroff -ms paper.ms | colcrt -2 | more
```

```bash
# Preview an allboxed tbl table without the underline flood
tbl doc.roff | nroff | colcrt - | more
```

```bash
# Compare with the print-oriented sibling filter
nroff -man page.1 | col -b | lpr     # overstrikes resolved for the printer
nroff -man page.1 | colcrt | more    # dashes for the screen
```

```bash
# Quick sanity check of the dash-row conversion
printf 'a\b_\nb\n' | colcrt          # "a" plus a dash row
```

```bash
# Clean a captured typescript that contains underline sequences
colcrt - < typescript > typescript.noul
```

```bash
# Chain with col when input also needs tab compaction
nroff -man page.1 | col | colcrt - | head -40
```

```bash
# Batch-convert a directory of roff sources into previewable text
for f in docs/*.ms; do nroff -ms "$f" | colcrt -2 > "${f%.ms}.txt"; done
```

```bash
# Diff two renderings: underline-on vs underline-off isolates the dash rows
nroff -man page.1 | colcrt    > /tmp/with-ul
nroff -man page.1 | colcrt -  > /tmp/no-ul
diff /tmp/no-ul /tmp/with-ul | head
```

## Nuances and Gotchas

- **stdin only, no operands.** `colcrt file` fails; use redirection.
- **The dash rows are extra lines.** Output line numbers do not match the input —
  any `sed`/`awk` line math over `colcrt` output must account for the shadow lines.
- **Not Unicode-faithful.** Like its siblings it predates careful multibyte
  handling; feed it groff `-Tutf8` output and results may be odd. Modern practice:
  let groff/mandoc emit terminal-ready UTF-8 directly and skip `colcrt`.
- **Overstrike composites are lossy.** Bold (`c BS c`) and multiple overstrikes are
  reduced rather than rendered; do not use `colcrt` output where fidelity matters.
- **`-2` changes line counts drastically.** Double-spaced output is fine for
  `more`, wrong for diffing or line-addressed processing.
- **Portability.** Present on BSD/macOS and in util-linux's bsdextrautils build;
  minimal-embeddings (busybox, containers) often omit it entirely.
- **It assumes input, not output, is the roff dialect.** Feeding `colcrt`
  already-rendered UTF-8 text is harmless but pointless; its backspace parsing
  only pays off on real nroff/troff intermediate output.
- **Combined options are positional-convention, not documented combos.** Old
  scripts write `colcrt -2 -` or `colcrt - -2`; behavior on unusual orderings
  is not specified — keep to one option per invocation when scripting.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success |
| nonzero | Usage or I/O failure (not formally documented in the man page) |

## Related Commands

- [`col`](./col.md) — the general reverse-linefeed filter `colcrt` grew out of
- [`colrm`](./colrm.md) — name-sibling; deletes column ranges instead
- [`column`](./column.md) — columnating filter, unrelated job but same collection
- [`overview`](./overview.md) — index of all util-linux collection pages
- [man-pages](../../reference/man-pages.md) — the roff/man pipeline this filter served

## Interview Questions

### Q: What does colcrt do that col -b does not?

`col -b` simply keeps the last character per column and discards the overstrike
machinery — underlines vanish. `colcrt` *preserves the underline information* by
emitting a row of dashes below the underlined text, and it can turn half-line motion
into real spacing (`-2`) or suppress underlines entirely (`-`). It is a rendering
filter tuned for screens, not just a cleaner.

### Q: Why would a 1980s admin prefer colcrt over col when reading documentation?

CRT terminals could not overstrike, so bold/underline encoded as backspace
sequences was unreadable; `colcrt` converted underline to dashes the terminal could
show, and `-2` made superscripts legible by giving them their own lines. `col`
outputs were aimed at overstrike-capable line printers.

### Q: In what situation is `colcrt -` specifically recommended?

Previewing `tbl(1)` tables with the `allbox` option: such tables underline every
cell, so the dash rows would dominate the screen. Suppressing underlining shows the
content; the box structure is checked later on paper or with a real typesetter.

### Q: Is colcrt still relevant operationally?

Mostly as literacy: you will meet it in old shell scripts, Makefiles, and
documentation pipelines. Functionally, `groff -Tutf8`/`mandoc` produce clean
terminal output and `less` renders overstrikes itself, so new pipelines should not
introduce `colcrt` — but knowing what it does explains what those old pipelines
were compensating for.

### Q: A script does `nroff ... | colcrt | awk 'NR>5'` and gets wrong lines. Why?

`colcrt` inserts additional dash rows for underlined text (and doubles lines with
`-2`), so line numbers in its output no longer correspond to the formatted document.
Line-based post-processing must run before `colcrt`, or on `col -b` output that
contains no shadow lines.

### Q: How would you reconstruct the underline information colcrt adds?

Generate two renderings — `colcrt` (dashes kept) and `colcrt -` (underlines
suppressed) — and diff them: every added line is a dash row, and its column
positions map back to the underlined words. It is also a neat demonstration
that `colcrt -` is strictly a subset transformation of plain `colcrt`.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/colcrt.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
