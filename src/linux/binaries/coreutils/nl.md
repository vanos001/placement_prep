# nl — line numbering filter with styles and logical pages

## Overview

`nl` writes its input back out with line numbers attached — but unlike the
blunt `cat -n`, it is a formatting tool: you choose *which* lines get numbers
(all lines, non-empty lines, lines matching a regex), *how* they are rendered
(left/right aligned, zero padded, custom width and separator), and *which
logical section* of the input they belong to (header, body, footer, delimited
by marker lines).

It ships in Debian's `coreutils` package at `/usr/bin/nl` and is a POSIX
standard utility with a lineage in the System V text tools of the early 1980s.
You reach for it when preparing text for review, quoting code with defensible
line references, or generating numbered listings where blank lines and header
blocks must stay unnumbered. It is often confused with `cat -n`, which always
numbers every line with a fixed format and has no notion of sections, and with
`grep -n`, which reports original file line numbers during a search rather
than adding numbers as a formatting pass.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 (User commands) |
| Path | `/usr/bin/nl` |
| First appeared / lineage | System V text tools lineage (early 1980s); GNU rewrite |
| Standards | POSIX.1-2018 |

## Synopsis

```
nl [OPTION]... [FILE]...
```

Main forms:

```
nl file.txt                       # number non-empty lines (default style t)
nl -ba file.txt                   # number every line (cat -n equivalent)
nl -bp'^#' script.sh              # number only lines starting with #
nl -w3 -s' | ' -nrz log.txt       # zero-padded width-3 numbers, custom separator
```

## How It Works

`nl` splits the input into *logical pages*. Each logical page has up to three
sections — **header**, **body**, **footer** — and each section restarts the
line counter. Section boundaries are marker lines: the input line
`\:\:\:` (the two section-delimiter characters `\:` around an empty middle)
starts a header section, `\:\:` starts a body section, and `\:` starts a
footer section. Markers themselves are replaced by empty lines in the output.

```
   input                    nl output (defaults)
   \:\:\:  ────────────►    (blank)          header section:
   HEADER LINE        ───►  HEADER LINE        NOT numbered
   \:\:   ────────────►    (blank)          body section:
   first body line    ───►      1	first body line
   second body line   ───►      2	second body line
   \:\:\:  ────────────►    (blank)          footer section:
   FOOTER LINE        ───►  FOOTER LINE        NOT numbered
```

Numbering styles are chosen independently per section with `-h` (header),
`-b` (body), and `-f` (footer):

| Style | Lines numbered |
|---|---|
| `a` | all lines |
| `t` | only non-empty lines (this is the body default) |
| `n` | no lines (header and footer default) |
| `pRE` | only lines matching the basic regular expression RE |

The number's appearance is controlled by `-n` format (`ln` left-justified, `rn`
right-justified, `rz` right-justified zero padded), `-w` field width (default
6), and `-s` separator string (default TAB). The counter itself starts at `-v
NUMBER` (default 1) and steps by `-i NUMBER` (default 1).

Verified behaviors:

```bash
$ printf 'alpha\nbeta\ngamma\ndelta\n' | nl -ba -w3 -s' | '
  1 | alpha
  2 | beta
  3 | gamma
  4 | delta

$ printf 'alpha\nbeta\n' | nl -nln            # left-justified, no padding
1     	alpha

$ printf 'alpha\nbeta\n' | nl -nrz -w4         # zero padded
0001	alpha
```

With the default `-bt` style, blank lines pass through unnumbered but keep
their column alignment (the number field is emitted as blanks):

```bash
$ printf 'a\n\n\nb\n' | nl
     1	a
       
       
     2	b
```

The `pRE` style is the power feature: number only lines matching a pattern
while printing everything else untouched.

```bash
$ printf 'HEAD\n1\ntail\n2\ntail\n3\n' | nl -bp'^[0-9]'
       HEAD
     1	1
       tail
     2	2
       tail
     3	3
```

## Options That Matter

| Option | Effect |
|---|---|
| `-b STYLE` / `-h STYLE` / `-f STYLE` | Numbering style (`a`, `t`, `n`, `pRE`) for body / header / footer |
| `-d CC` | The two section-delimiter characters (default `\:`); `-d ''` disables sections |
| `-n FORMAT` | `ln`, `rn`, or `rz` number rendering |
| `-w N` | Number field width (default 6) |
| `-s STRING` | String printed between number and text (default TAB) |
| `-v N` | First line number of each section (default 1) |
| `-i N` | Line number increment (default 1) |
| `-l N` | Count a run of N consecutive empty lines as one (only with `a` style) |
| `-p` | Do not restart numbering at each section delimiter |

## Usage Patterns

```bash
# Number every line — the "cat -n" equivalent people actually mean
nl -ba script.sh | head -20
```

```bash
# Quote a specific line into a bug report, zero padded for alignment
nl -ba -nrz -w4 app.log | sed -n '123p'
```

```bash
# Number only the statements in a SQL dump: lines ending in semicolon
nl -bp';$' dump.sql
```

```bash
# Restart the visible counter at 42 to match a caller's frame numbering
nl -v 42 -ba handoff.md
```

```bash
# Steps of 10, like a BASIC listing — leave room for inserted lines
nl -i 10 -w3 -ba notes.txt
```

```bash
# Number only non-empty lines but count blanks in the sequence (proofreading)
nl -ba -l2 draft.txt
```

```bash
# Two-paragraph document where only the body should carry numbers
printf '\\:\\:\\:\nTitle Page\n\\:\\:\nChapter 1\nChapter 2\n' | nl
```

```bash
# Pipe-friendly: number command output as it streams
journalctl -u nginx --no-pager | nl | tail -50
```

```bash
# Disable section handling entirely (treat \: lines as ordinary text)
nl -d '' -ba file_with_backslash_colon_content.txt
```

```bash
# Right-align numbers under a wider width with a fixed separator for columns
nl -ba -w5 -s'  ' source.c | paste - source_comments.txt | head
```

## Nuances and Gotchas

- **`nl` is not `cat -n`.** `cat -n` numbers every line, always width 6, with a
  tab, and never renumbers. `nl`'s default is *non-empty* lines only (`-bt`),
  restarts numbering at every section marker, and treats input lines starting
  with `\:` as control markers. Scripts that blindly substitute `nl` for
  `cat -n` corrupt input containing backslash-colon lines.
- **Section markers are consumed.** A line `\:\:\:` in the input disappears
  from the output (replaced by a blank line). Processing already-numbered or
  TeX-ish files with stray `\:` prefixes silently mutates them; use `-d ''` to
  disable marker handling.
- **The regex in `pRE` is a basic regular expression**, interpreted per
  locale's `LC_CTYPE` — but unlike `grep`, there is no `-E` switch, so
  alternation means escaping: `p'foo\|bar'` under GNU.
- **Header and footer are not numbered by default** (`-hn`, `-fn`). People
  expecting `nl` ≈ `cat -n` are confused when a leading block never gets
  numbers; that block is a header section only if the file *starts* with a
  `\:\:\:` marker.
- **Width interplay:** if numbers grow wider than `-w` (say `-w3` past line
  999), `nl` silently widens the field; the format is a minimum, not a cap.
- **Portability:** POSIX `nl` covers styles, formats, sections, `-v`, `-i`,
  `-l`, `-p`, `-w`, `-s`, `-d`. GNU adds `-d ''` to disable delimiters. BSD
  and busybox `nl` are faithful to the POSIX core; very old busybox builds
  lacked `-p`.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Trouble: unreadable file, invalid style/format/width option value |

## Related Commands

- [`pr`](./pr.md) — page-oriented cousin: pagination, headers, footers, and `-n` line numbering for print
- [`paste`](./paste.md) — merge numbered output side by side with other columns
- [`tac`](./tac.md) — the other line-order transformer in the coreutils text set
- [`overview`](./overview.md) — the coreutils collection hub

## Interview Questions

### Q: What is the difference between nl and cat -n?

`cat -n` unconditionally numbers every line with a fixed width-6 right-aligned
format and a tab. `nl` has three numbering styles per section (all lines,
non-empty lines, regex-matching lines), configurable width/separator/padding,
and a logical-page model with header/body/footer sections that restart the
counter. Roughly: `cat -n` ≈ `nl -ba` plus immunity to `\:` markers.

### Q: How would you number only the lines of a file that contain a function definition?

`nl -bp'^function ' file` (or whatever the pattern is). The `p` style numbers
only matching lines but prints every line, so the file stays intact apart from
the added number column. This is a one-liner that would otherwise need an awk
filter that remembers the original line context.

### Q: Explain nl's logical pages. When do they bite?

The input is divided by `\:\:\:` (header), `\:\:` (body), and `\:` (footer)
marker lines; the counter restarts at `-v` for each section and header/footer
are unnumbered by default. They bite in two ways: files that legitimately
contain those sequences are silently reformatted (markers become blank lines),
and people who expected continuous numbering see the counter reset. `-p`
suppresses the reset and `-d ''` disables marker detection.

### Q: Why does nl print blank padding for lines it does not number?

The number field is a fixed-width column (`-w`, default 6) plus separator
(default TAB); unnumbered lines still get the field rendered as spaces so the
text column lines up. This is a deliberate layout decision — it makes numbered
and unnumbered lines visually comparable, unlike grep -n where unmatched lines
simply have no prefix.

### Q: How would you produce zero-padded four-digit line numbers?

`nl -ba -nrz -w4 file`. `-nrz` selects right-justified zero-padded rendering
and `-w4` the field width. If the file exceeds 9999 lines the field silently
widens, so downstream parsers should not hard-code the column width.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/nl.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
