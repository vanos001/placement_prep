# fold — hard-wrap input lines at a fixed width

## Overview

`fold` is a filter that wraps every input line so no output line exceeds a
given width — by default 80 columns. It is deliberately dumb: it never
joins lines, never balances anything, never interprets words. Each output
line is simply the next chunk of the input line; where the cut lands is
decided by the width, the `-s` "prefer blanks" flag, and (without `-b`)
tab-stop arithmetic.

That simplicity is the feature. Where [`fmt`](./fmt.md) reflows *prose*,
fold processes *text*: logs, fixed-width reports, protocol payloads, long
URLs and tokens — anything where you need a hard per-line budget and
cannot afford a tool that edits the content between words. It is also the
older sibling historically: fold dates to BSD and was written for a world
of line printers and fixed-width media, which is why its default is 80
and why it remains the standardized choice for "make every line fit".

Debian ships it in `coreutils` at `/usr/bin/fold`. It is one of the
text utilities standardized by POSIX, so `fold` behavior is portable
across GNU, BSD, macOS, and BusyBox in a way `fmt` is not.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/fold` on modern Debian/Ubuntu |
| First appeared / lineage | BSD origin (around 1990); standardized in POSIX.2 |
| Standards | POSIX.1-2018 (`fold`) |

## Synopsis

```
fold [OPTION]... [FILE]...
```

Main forms:

```bash
fold -w 40 file.txt         # hard wrap at 40 columns
fold -s -w 72 mail.txt      # wrap at 72, break after blanks when possible
fold -b -w 260 data.bin     # count bytes, not columns (tab stops off)
```

With no FILE, or FILE being `-`, fold reads stdin.

## How It Works

### Default mode: cut at the width

Every input line is emitted in chunks of at most `-w` columns; a newline
is written wherever the next character would overflow. No state is kept
between lines, nothing is joined, and the output line count is
`ceil(len/width)` per input line:

```bash
$ printf 'The quick brown fox jumps over the lazy dog\n' | fold -w 10
The quick
brown fox
jumps over
 the lazy
dog
```

Note the cut after `jumps over` — fold does not care that a space sits at
the boundary; without `-s` it cuts exactly at the column, even mid-word
or one character before the space, which is why the next line can begin
with a blank.

### Column counting: what -b actually changes

Without `-b`, fold counts "columns" the old typewriter way: a **tab**
advances to the next multiple-of-8 tab stop and a **backspace** moves one
column left. With `-b`, every byte — including tabs and backspaces —
counts as exactly one column. This is the documented, standardized
difference, and it is about tab arithmetic, not (in GNU's case) about
multibyte characters:

```bash
$ printf 'ab\tcd\n' | fold -w 5 | od -c
0000000   a   b  \n  \t  \n   c   d  \n          # tab jumps to column 9 → wraps
$ printf 'ab\tcd\n' | fold -b -w 5 | od -c
0000000   a   b  \t   c   d  \n                # tab = 1 byte, line fits
```

### Multibyte (UTF-8) input: the byte trap

GNU fold counts bytes for ordinary characters, so multibyte UTF-8 text
can be cut **inside a character**, producing invalid sequences. `-b`
makes no difference for this — both modes split the same way here:

```bash
$ printf '日本語\n' | fold -w 4 | od -c
0000000 346 227 245 346  \n 234 254 350 252  \n 236  \n
```

`日本語` is 3 characters (6 display columns, 9 bytes); the cut after 4
bytes lands in the middle of the second character. For multibyte-aware
wrapping you need awk/Perl/Python, not POSIX fold — a favorite
interview gotcha.

### Spaces mode: -s

`-s` breaks after the **last blank** that fits within the width, which
keeps words intact when possible. Two consequences worth memorizing: the
blank itself stays at the end of the line (trailing whitespace appears),
and a run of non-blanks longer than the width is still cut — `-s` degrades
to hard splitting rather than overflowing:

```bash
$ printf 'The quick brown fox jumps over the lazy dog\n' | fold -s -w 10
The quick
brown fox
jumps
over the
lazy dog
$ printf 'supercalifragilisticexpialidocious x\n' | fold -s -w 8
supercal
ifragili
sticexpi
alidocio
us x
```

```
   input line ──► walk chars, count columns ──► width reached?
                    │            │                 │
                    │   -s: last blank ≤ width     │
                    │            ▼                 ▼
                    │      break after it    break here (hard cut)
                    ▼
             emit line, continue with remainder
```

### fold vs fmt at a glance

| | `fold` | [`fmt`](./fmt.md) |
| --- | --- | --- |
| Joins lines | never | yes (unless `-s`) |
| Line content | exact byte chunks | reflowed, whitespace may change |
| Width | hard maximum | hard max + 93% goal balancing |
| Tabs/backspaces | tab-stop logic (without `-b`) | ordinary whitespace |
| Standardized | POSIX.1-2018 | no (GNU/BSD divergence) |
| Reversible within a line | yes | no |

## Options That Matter

| Option | Effect |
| --- | --- |
| `-w`, `--width=WIDTH` | Use WIDTH columns instead of the default 80 |
| `-s`, `--spaces` | Break after the last blank that fits; long words still get cut |
| `-b`, `--bytes` | Count bytes instead of columns: no tab-stop expansion, no backspace logic |

That is the entire option surface — three flags. Everything else is how
you combine them with the width.

## Usage Patterns

```bash
# Wrap long URLs or tokens in a report so they print without overflow
fold -s -w 78 links.txt
```

```bash
# Hard-wrap a log file with pathological one-line JSON blobs
fold -w 120 app.log | less
```

```bash
# Mail-body convention: keep lines under 80 for ancient MTAs
fold -s -w 78 body.txt
```

```bash
# Byte-accurate splitting of data for fixed-size record slots
fold -b -w 256 payload.txt
```

```bash
# Demo or kiosk output on a narrow terminal column
fold -s -w 40 banner.txt
```

```bash
# Wrap, then rejoin with tr to see exactly what fold added
fold -s -w 10 input.txt | tr -d '\n' | diff - <(tr -d '\n' < input.txt)
```

```bash
# Break a single very long line (no blanks at all) into width chunks
fold -w 16 giant_token.txt
```

```bash
# Pipe-friendly: wrap the output of a generator before archiving
./generate-report | fold -s -w 100 > report.txt
```

## Nuances and Gotchas

- **UTF-8 is folded mid-character.** GNU fold counts bytes for regular
  characters, so `fold -w N` on non-ASCII text can emit invalid byte
  sequences (verified with `日本語`). `-b` does not save you; for
  multibyte-aware wrapping use awk with `mblen`-style logic, `sed`, or a
  scripting language. POSIX talks about columns, but GNU's implementation
  is byte-oriented — classic portability-question trap.
- **Tabs expand, and that is usually not what you wanted.** Without `-b`,
  a tab advances to the next 8-column tab stop, so text with tabs can
  wrap "early" in confusing ways (`ab\tcd` at width 5 becomes three
  lines). `-b` turns the tab into one byte for counting. Neither mode
  converts tabs to spaces in the output.
- **`-s` introduces trailing blanks.** Breaking after the last fitting
  blank leaves that blank at the end of the line — visible with
  `cat -A` and fatal for formats where trailing whitespace matters
  (some protocols, fixed-width records, diff hygiene).
- **`-s` does not overflow-proof long words.** A token longer than the
  width is still cut at the width (`supercalifragilistic...` splits into
  8-char chunks). If a hard per-line budget matters, test with a long
  token, not with friendly prose.
- **fold never removes information, but it is not reversible.** Within a
  line the bytes are preserved verbatim; however, fold's inserted
  newlines are indistinguishable from the original ones afterwards, so
  the original line boundaries cannot be recovered from the output alone.
  `fmt` is worse — it rewrites inter-word whitespace too.
- **Default widths differ across the family.** fold defaults to 80,
  fmt to 75 — scripts that assume "the default" produce differently
  wrapped output. Always pass `-w` explicitly in automation.
- **POSIX but minimal.** fold is standardized, so behavior is portable,
  but the standard's column model (tab stops, backspaces) plus GNU's byte
  orientation makes "columns" a fuzzy notion beyond plain ASCII. BusyBox
  fold implements the same core flags.
- **It is a filter, not a file editor.** fold has no in-place mode; the
  safe edit pattern is `fold -w N f > f.new && mv f.new f`, ideally via a
  [`mktemp`](./mktemp.md) temp in the same directory for an atomic rename.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | All input folded successfully |
| 1 | Error: invalid width or option, unreadable input, write failure |

## Related Commands

- [`fmt`](./fmt.md) — the reflowing counterpart: joins lines and balances to a goal width
- [`expand`](./expand.md) — convert tabs to spaces first so fold's column math is predictable
- [`unexpand`](./unexpand.md) — reverse tab conversion after wrapping
- [`od`](./od.md) — inspect exactly where multibyte folds cut, byte by byte
- [`sed-awk`](../../shell/sed-awk.md) — multibyte-aware wrapping when fold's byte logic is insufficient
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages

## Interview Questions

### Q: fold and fmt both "wrap text" — how do you choose between them?

By whether joining is acceptable. fold only shortens lines: output lines
are exact chunks of input, nothing between words changes, and it is the
tool when a hard per-line budget exists. fmt reflows paragraphs: it joins
short lines and re-splits, changing whitespace and line structure to hit
a 93%-of-width goal. Reflowing prose → fmt; protocol text, logs, and
anything with a line-length constraint → fold. fold is also the
POSIX-standardized one, so it is the portable default.

### Q: What does `fold -b` really change? Most people answer wrong.

It does not primarily switch to "bytes instead of multibyte characters" —
it switches the column *accounting*: without `-b`, tabs advance to the
next multiple-of-8 tab stop and backspaces step back one column; with
`-b`, every byte counts one. The classic demo is `ab\tcd` at width 5:
without `-b` the tab's jump to column 9 forces wraps; with `-b` the five
bytes fit on one line. GNU fold counts ordinary characters as bytes in
both modes, so `-b` neither fixes nor causes the UTF-8 mid-character
splitting — that is a separate limitation.

### Q: A teammate ran `fold -s -w 40` over UTF-8 markdown and the output contains broken characters. What happened and what are the options?

GNU fold counted bytes: multibyte characters near the width boundary got
split mid-sequence, producing invalid UTF-8 (`日本語` at width 4 splits
inside the second character). Options: use a multibyte-aware wrapper
(awk/Perl/Python), pre-convert the text, or accept the damage only where
the format is byte-oriented anyway. The underlying lesson: POSIX fold's
"columns" model predates multibyte encodings, and GNU's implementation
never adopted display-width counting.

### Q: With `fold -s`, what two behaviors can still surprise you?

First, `-s` breaks *after* the last fitting blank, so the blank itself
remains as trailing whitespace on the output line — a hygiene problem in
protocols and diffs. Second, when a run of non-blanks exceeds the width,
`-s` falls back to a hard cut at the column; it never overflows the
width to preserve a word. So `-s` gives you word-aware wrapping *where
possible*, not a guarantee of whole words.

### Q: Is fold's transformation reversible? Compare with fmt.

Not in general. fold preserves the bytes within each line, but its
inserted newlines are indistinguishable from the original ones — after
folding, the input's line boundaries are unrecoverable (you can only join
everything back into one stream). fmt is strictly lossier: it also
rewrites the whitespace *between* words when filling. Neither writes any
metadata about what it changed, which is why both should run through a
temp file with a diff review, not in-place on originals.

### Q: Where does fold still earn its keep in a modern pipeline?

Anywhere a hard per-line budget exists: wrapping oversized log lines
before archival or display, splitting byte streams into fixed-size
records (`fold -b`), enforcing RFC-style body width for mail, preparing
text for devices or protocols with line limits, and as a quick
"what would change if the limit were N" diff probe. Its worth is exactly
its stupidity: three flags, no interpretation, standardized across every
UNIX-like system.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/fold.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
