# csplit — split a file into pieces determined by context (patterns and offsets)

## Overview

`csplit` ("context split") cuts one input file into multiple output files at *content-determined* boundaries: the line matching a regular expression, a specific line number, a byte offset, or a repetition of any of these. It is the tool for "give me one file per `BEGIN:` block", "split the log at every `### day marker`", or "keep the header separate from the body".

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/csplit`, from upstream GNU coreutils. Its sibling `split` cuts by size or line count, blind to content; `csplit` is the content-aware one, and also the one whose argument grammar (`/re/`, `%re%`, `{*}`, `-N` offsets) confuses newcomers — this page is deliberately concrete about it.

Every piece is written to its own file, named by default `xx00`, `xx01`, … and csplit prints each piece's byte count to stdout as it goes. On error it deletes what it created unless `-k` is given — a behavior that regularly surprises people debugging failed splits.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/csplit` |
| First appeared / lineage | BSD/POSIX lineage; long-standing POSIX utility, GNU implementation in coreutils |
| Standards | POSIX.1-2018 (`csplit`) |

## Synopsis

```
csplit [OPTION]... FILE PATTERN...
```

Pattern grammar — the heart of the tool:

```
N            split before line N (1-based, absolute)
/REGEX/      split before the next line matching REGEX
/REGEX/+N    split N lines after the matching line
/REGEX/-N    split N lines before the matching line
%REGEX%      like /REGEX/, but do not create a file for the skipped part
{*}          repeat the previous pattern as many times as possible
{N}          repeat the previous pattern at most N times
```

Main forms:

```
csplit file '/^CHAPT/' '{*}'     # one file per chapter heading
csplit file 100                  # first 99 lines, then the rest
csplit file '%^BEGIN%' '/^END/' '{*}'   # skip preamble, one file per block
```

## How It Works

### Pieces are the gaps between split points

`csplit` evaluates patterns left to right, walking the file once. Each pattern advances the position; every time the position moves, the bytes traversed since the last split point become one output file. The matched line itself starts the *next* piece (the split is before the match):

```
input:  ┌────────────┬──────────────┬──────────────┬──────────┐
        │ preamble   │ CHAPT1 block │ CHAPT2 block │ CHAPT3.. │
        └────────────┴──────────────┴──────────────┴──────────┘
csplit book.txt '/^CHAPT/' '{*}'
            → xx00 = preamble (may be empty)
            → xx01 = CHAPT1 block
            → xx02 = CHAPT2 block
            → xx03 = everything from CHAPT3 on
```

Verified end-to-end:

```
$ printf 'CHAPT1\nline a\nline b\nCHAPT2\nline c\nCHAPT3\nline d\n' > book.txt
$ csplit -f chap- -b '%02d.txt' book.txt '/^CHAPT/' '{*}'
0
21
14
21
$ ls chap-*
chap-00.txt  chap-01.txt  chap-02.txt  chap-03.txt
```

The four numbers on stdout (`0 21 14 21`) are the byte counts of `chap-00` through `chap-03` — csplit echoes one count per piece; `-s` silences them.

### `/regex/` versus `%regex%` — suppress the gap

Both split before the matching line. The difference is what happens to the *skipped* content: `/re/` writes the gap as its own output file (often an unwanted empty or header file), while `%re%` discards it silently — no file is created for the skipped region:

```
$ printf '1\n2\n3\n4\n5\n6\n7\n8\n9\n' > num.txt
$ csplit -s -f pct- num.txt '/3/' '%5%'
$ ls pct-*
pct-00  pct-01        # 00 = lines 1-2; lines 3-4 suppressed; 01 = lines 5-9
```

A leading `%re%` is the standard idiom for "throw away the preamble and start the real split at the first marker". Note the suppressed part is bounded by the *next* pattern, so `'%re%'` alone with nothing following has nothing to output.

### Offsets: {N}, {*}, and ±N

- `{N}` / `{*}` repeat the immediately preceding pattern. `{*}` means "as many times as possible" and is what you want for marker-split logs. If a repeated pattern stops matching before the end of input, the trailing remainder becomes the last piece anyway.
- Integer operands are absolute line numbers; `+N`/`-N` are relative to the previous split point, and `/re/+N` shifts the boundary N lines past the match — useful when a record starts a few lines before or after its header line.
- Plain numbers after the first are interpreted as before-line-N splits; when a line number is already behind the current position you get `line number out of range` and (without `-k`) all created files are deleted.

```
$ csplit -s num.txt '/9/' '5'
csplit: '5': line number out of range      # position already past line 5
$ echo $?
1
$ ls xx*                                   # default: cleaned up on error
ls: cannot access 'xx*': No such file or directory
$ csplit -k -s num.txt '/9/' '5' 2>/dev/null; ls xx*
xx00  xx01                                 # -k keeps partial output
```

### Naming and counting

Piece names are prefix (default `xx`) + suffix. The suffix is a counter rendered with `-b` (printf format, default `%02d`) or `-n` (digit count, default 2). `-f` changes the prefix. `-z` elides empty pieces so you never ship zero-byte files. The stdout byte-count stream (one number per piece) is itself scriptable: `csplit ... | wc -l` tells you how many pieces were made.

## Options That Matter

| Option | Effect |
|---|---|
| `-f PREFIX` | Output file name prefix (default `xx`) |
| `-b FORMAT` | Suffix as a printf format, e.g. `'%03d.txt'` (overrides `-n`) |
| `-n DIGITS` | Number of digits in the suffix counter (default 2) |
| `-s`, `--quiet` | Suppress the per-piece byte counts on stdout |
| `-k`, `--keep-files` | Do not delete created files when an error occurs |
| `-z`, `--elide-empty-files` | Do not create empty output files |
| `--suppress-matched` | GNU extension: omit the matched (marker) lines from the output pieces |

`--suppress-matched` is worth knowing: without it, marker lines (e.g. `CHAPT2`) begin the following piece; with it, the markers vanish and pieces contain only content.

## Usage Patterns

```bash
# One file per chapter: markers stay with the following chunk
csplit -s -f chap- -b '%02d.txt' book.txt '/^CHAPT/' '{*}'
```

```bash
# Log file: split at each day boundary, drop the boundary line from output
csplit -s --suppress-matched -f day- -b '%02d.log' app.log '/^== 2025-/' '{*}'
```

```bash
# Skip the preamble, then split per BEGIN/END block
csplit -s -f blk- '%^BEGIN%' '/^END/' '{*}'
```

```bash
# Header (first 10 lines) separate from body
csplit -s config.conf 11
# xx00 = lines 1-10 (header), xx01 = rest
```

```bash
# Split a SQL dump per INSERT statement for surgical inspection
csplit -s -f ins- dump.sql '/^INSERT INTO/' '{*}'
```

```bash
# Byte-offset split: first 512 bytes (MBR) and the rest
csplit -s disk.img 513
```

```bash
# Keep marker with the PREVIOUS record instead: offset the boundary
csplit -s -f rec- -b '%02d' access.log '/^2025-06-01/+1' '{*}'
```

```bash
# Name pieces after their order with a stable extension for later globbing
csplit -s -n 3 -f shard- -b 'shard-%03d.csv' data.csv '/^# ---/' '{*}'
```

```bash
# Free split statistics: piece count and total bytes from the count stream
csplit -f st- book.txt '/^CHAPT/' '{*}' | awk '{n++; s+=$1} END{print n" pieces, "s" bytes"}'
rm -f st-*
```

```bash
# Fail loudly if a marker never matched (trailing piece would swallow the rest)
csplit -k -f chk- input '/^EXPECTED MARKER$/' '{1}' || echo "marker missing"
```

## Nuances and Gotchas

- **On error, output vanishes.** Default behavior deletes every file it created when a later pattern fails (`line number out of range`, unreadable input). Use `-k` while developing the pattern list, and only drop it once the command is proven.
- **The split is before the match, and markers travel with the next piece.** People expect the matched line to *end* a piece; it starts the next one. Use `--suppress-matched` when you want the markers gone, or `/re/-1` to pull the boundary above the marker.
- **`{*}` means zero-or-more.** If the pattern matches nothing after the first application, csplit does not fail — the remaining tail becomes the final piece. Validate expected piece counts (`ls xx* | wc -l`) when the split must be exact.
- **Regex flavor is basic (BRE) by default.** `/re/` uses POSIX basic regular expressions unless compiled otherwise; `?re?` is the historical extended-hint spelling in POSIX but GNU uses BRE — escape groups with `\(...\)` and alternation carefully, or pre-test with `grep`.
- **Patterns are positional.** `csplit file a b c` applies a, then b, then c, in that order — each pattern resumes from the previous split point. Reordering arguments changes the split completely, and a pattern whose target lies before the current position is a fatal out-of-range error.
- **Line numbers, not bytes, for integer patterns** — except that a *bare first* integer is still a line number; byte offsets require the offset forms. `csplit disk.img 513` means line 513 of a text file, which is why the byte-split example above used a binary file where "lines" are whatever bytes happen to be there — prefer `split -b` or `dd` for byte-accurate binary cutting.
- **Empty first piece is normal.** A file starting with its first marker produces a leading empty `xx00`; add `-z` if that bothers downstream tooling.
- **stdout byte counts are part of the contract.** Piping csplit's stdout anywhere (or running it in a command substitution) without `-s` injects numbers into your pipeline.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All patterns applied successfully |
| 1 | Error: out-of-range pattern, no match where required, I/O failure (created files removed unless `-k`) |

## Related Commands

- [`split`](./overview.md) — content-blind splitting by size or line count (see the collection overview).
- [`cat`](./cat.md) — the inverse operation: `cat xx*` reassembles what csplit produced.
- [`grep`](../../shell/grep.md) — find the markers first when debugging the pattern list.
- [`head`](./head.md) — quick "first N lines" extraction without creating the tail piece.
- [`sed-awk`](../../shell/sed-awk.md) — awk can emit per-record files too (redirection per match), often at the cost of more code.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: What is the difference between csplit and split?

`split` divides by quantity — size in bytes or lines — and never looks at content, which is right for chunking archives for transfer. `csplit` divides at content boundaries (regex matches, line numbers, offsets) with a pattern grammar, which is right for records, chapters, and blocks. `cat` reverses both. The names are similar; the mental models are "band saw" (split) versus "follow the dotted lines" (csplit).

### Q: Explain the four argument forms of csplit patterns.

A bare integer N splits before line N. `/REGEX/` splits before the next matching line, optionally offset by ±N lines. `%REGEX%` does the same but suppresses creation of the file that would hold the skipped content (ideal for preamble removal). `{N}` and `{*}` repeat the preceding pattern — bounded or unbounded. Patterns apply sequentially, each continuing from the previous split point.

### Q: You ran a csplit command, it failed halfway, and the output files are gone. What happened and how do you debug?

Default coreutils behavior: when any pattern fails (commonly `line number out of range` after a repeated pattern stops matching), csplit removes all files it created in that run. Re-run with `-k` to keep partial output, `-s` off to watch the byte counts, and check stderr for the exact failing pattern. Once the pattern list is validated, decide whether production should keep `-k` (recover partial results) or drop it (all-or-nothing semantics).

### Q: How would you split a log into one file per day when each day starts with a `^==== 2025-` line?

`csplit -s -f day- -b '%02d.log' app.log '/^==== 2025-/' '{*}'`. The first (pre-marker) piece is typically empty — add `-z` to elide it; add `--suppress-matched` if the separator lines should not appear in the day files. If you want the marker to stay with the *previous* day instead, shift the boundary with a negative offset (`'/^==== 2025-/-1'`).

### Q: Why do people get confused by % versus / in csplit, and what is your rule of thumb?

Because both split at the same place; the difference is only whether the skipped gap becomes a file. The rule: use `/re/` when every byte of the input must appear in exactly one output piece (lossless partitioning — cat of all pieces reproduces the input); use `%re%` when the gap is garbage you want dropped (preamble, separators). If the reassembled output must equal the input, you never use `%`.

### Q: csplit prints numbers to stdout — what are they and why can they break scripts?

One byte count per created piece, in order. Scripts that capture csplit's stdout in a variable or feed it into a pipeline get those numbers instead of file content, a classic silent bug. Add `-s`/`--quiet` in any non-interactive context; parse the counts deliberately (e.g. `| awk '{s+=$1} END{print s}'`) when you want split statistics for free.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/csplit.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
