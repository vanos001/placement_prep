# wc — count lines, words, and bytes

## Overview

`wc` (word count) tallies the fundamental size metrics of text: newlines, words, characters, and bytes — from files, from stdin, or across lists of files with a total. It looks like the simplest tool in coreutils, and that simplicity is exactly why it is everywhere: `wc -l` is the standard way to ask "how many?" of anything that can be printed, from processes to matches to users.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/wc`, from upstream GNU coreutils. It is among the oldest Unix tools and is POSIX.1-2018-standardized: `-l`, `-w`, `-c`, and `-m`. GNU adds `-L` (maximum line display width), `--total`, and `--files0-from`.

`wc` is often confused at exactly two points, and both are interview gold. First, `-c` counts **bytes** while `-m` counts **characters** — identical in ASCII/C locales, different under UTF-8, and each with its own performance profile. Second, `-l` counts **newline characters**, not "lines" in the visual sense — a file's last line without a trailing newline does not exist as far as `wc -l` is concerned.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/wc` |
| First appeared / lineage | Earliest AT&T UNIX (1970s); every Unix since |
| Standards | POSIX.1-2018 (`wc`: `-l`, `-w`, `-c`, `-m`); GNU adds `-L`, `--total`, `--files0-from` |

## Synopsis

```
wc [OPTION]... [FILE]...
wc [OPTION]... --files0-from=F
```

Counts are always printed in the fixed order **newline, word, character, byte, max-line-length** — a column order you cannot change by flag order:

```
wc -l file              # lines only
wc -l -w file           # lines, then words
wc -c -m file           # chars, then bytes (fixed column order, not arg order)
wc f1 f2                # per-file counts + a total line
wc                      # stdin when no FILE (no filename in output)
```

With no FILE, or FILE `-`, standard input is read — the pipeline form.

## How It Works

### What each metric actually is

- **Lines (`-l`):** the number of `\n` bytes. Not "lines of text" — newline *terminators*. A final unterminated line is invisible to `-l` (see below).
- **Words (`-w`):** maximal runs of non-whitespace, delimited by whitespace or the start/end of input. Whitespace is locale-defined (space, tab, newline under C; plus Unicode spaces in UTF-8 locales).
- **Characters (`-m`):** decoded via the locale's character set (mbrtowc per byte sequence). UTF-8 locale: `é` is 1. C locale: every byte is a "character", so `-m` equals `-c`.
- **Bytes (`-c`):** raw byte count, locale-independent.
- **Max line length (`-L`, GNU):** the longest line's *display width* — tabs expand to the next multiple of 8, double-width CJK glyphs count as 2 columns. It is a terminal-columns measure, not a character count.

```
$ printf 'héllo wörld\n' | wc -c -m
     12      14                        # 12 characters, 14 bytes (2 two-byte letters)
$ printf 'a\tb\n' | wc -L
9                                      # tab advances to column 8, 'b' sits at column 9
```

Note the fixed column order in the first example: `-c -m` printed characters (12) before bytes (14), because the output order is characters-then-bytes regardless of how you typed the flags.

### The missing-trailing-newline gotcha

POSIX defines a line as a sequence ending in `\n`. `wc -l` implements that definition literally:

```
$ printf 'a\nb\nc\n' | wc -l
3
$ printf 'a\nb\nc' | wc -l
2                                      # 'c' has no newline → not counted
$ printf 'abc' | wc -l -w -c
      0       1       3                # 0 "lines", 1 word, 3 bytes
```

Any `wc -l` on data produced by tools that omit the final newline (some editors, `echo -n`, concatenated fragments) undercounts by one relative to the visual line count. The reverse also trips people: a file of exactly one line plus its newline counts 1 — correct — but "one empty file" counts 0 while "one newline only" counts 1:

```
$ printf '' | wc -l; printf '\n' | wc -l
0
1
```

### Output shape: columns, filenames, totals

Counts print right-aligned with a default width that grows as counts grow (historically 7 columns; wider values simply extend). When *files* are named, each gets its filename appended and — with more than one file — a `total` line comes last:

```
$ wc /etc/passwd /etc/group
     45     82    3120 /etc/passwd
     70     70    1287 /etc/group
    115    152    4407 total
```

`--total=WHEN` (GNU) controls that line: `auto` (default), `always`, `only`, `never` — `only` prints just the total, `never` suppresses it for per-file scripting. Reading from stdin prints bare counts with no filename, which is exactly why `wc -l < file` and `cmd | wc -l` produce clean numbers while `wc -l file` appends the name:

```
$ wc -l /etc/passwd
45 /etc/passwd
$ wc -l < /etc/passwd
45
```

### Performance: the byte-count fast path

GNU `wc` has a significant optimization: when *only* byte counts are requested and the input is a regular file, it takes the size from `fstat()` without reading the file at all:

```
$ truncate -s 2G sparse.bin
$ time wc -c < sparse.bin
2147483648
real    0m0.001s                        # stat, not read
$ time cat sparse.bin > /dev/null
real    0m1.670s                        # actually touching the data
```

The same trick applies to byte counts only: any request involving lines, words, or characters requires reading every byte, because newlines and word boundaries must be found. So the ladder of cost is: `-c` (free on files) < `-l` (scan, branch per byte) < `-m` (scan + multibyte decode, measurably slower under UTF-8) < `-L` (decode + width tables). On pipelines, `-c` must read everything too — the fast path exists only for seekable regular files.

```
$ time cat big.log | wc -c        # through a pipe: every byte must be read
$ wc -c < big.log                 # redirect or operand: stat fast path applies
```

### Multibyte decoding and invalid input

Under a UTF-8 locale, `-m` decodes sequences with mbrtowc; invalid bytes (binary data, truncated sequences) count as one each rather than failing:

```
$ printf '\xff\n' | wc -m
1                                       # invalid byte → counted as 1
$ LC_ALL=C printf 'héllo\n' | wc -m
6                                       # C locale: bytes are characters
```

`LC_ALL=C` therefore makes `-m` a synonym for `-c` — and incidentally much faster on large multibyte files, a real-world optimization for "I only need line counts anyway".

## Options That Matter

| Option | Effect |
|---|---|
| `-l, --lines` | Count newline characters |
| `-w, --words` | Count whitespace-delimited words |
| `-c, --bytes` | Count bytes (the POSIX `-c`; NOT "characters" despite the letter) |
| `-m, --chars` | Count characters via locale decoding (≈ `-c` in C locale) |
| `-L, --max-line-length` | Longest line's display width in columns; tabs expand, wide glyphs count 2 (GNU) |
| `--files0-from=F` | Read the list of input files from F, NUL-separated (GNU; pairs with `find -print0`) |
| `--total=WHEN` | `auto` / `always` / `only` / `never` — control the total line (GNU 9.x-era) |

Column order in output is fixed — newline, word, character, byte, max-line-length — no matter the flag order on the command line.

## Usage Patterns

```bash
# The universal "how many?" — count lines of any command output
ps aux | wc -l
```

```bash
# Clean count from a file (redirect suppresses the filename)
wc -l < /etc/passwd
```

```bash
# Fast byte count of big files (stat fast path, no read)
wc -c < /var/log/syslog
```

```bash
# Byte vs character difference = "how much non-ASCII is in here?"
wc -c -m README.md
```

```bash
# Count matches without spawning grep twice: grep -c or wc -l both work
grep -c ERROR app.log            # per-file, exits 1 on zero matches
grep ERROR app.log | wc -l       # stream-friendly
```

```bash
# Word count of documentation (the original 'wc' use case)
wc -w README.md
```

```bash
# Longest line in a source tree — lint for overly wide lines
wc -L src/*.py | tail -1
```

```bash
# Per-file counts across a tree, NUL-safe filenames
find . -name '*.log' -print0 | wc --files0-from=- -l
```

```bash
# Total only across many files (GNU)
wc -l --total=only *.c
```

```bash
# Count users with a login shell (pipeline of field extractors)
awk -F: '$7 !~ /(false|nologin)$/' /etc/passwd | wc -l
```

```bash
# Measure pipeline throughput: bytes per second of a generator
timeout 5 seq 0 inf | wc -c
```

```bash
# Verify a download size matches the manifest exactly
wc -c < image.iso
```

## Nuances and Gotchas

- **`-l` counts newlines, not lines.** The missing-trailing-newline case undercounts by one; worse, *comparisons* silently skew: `grep -c pattern` vs `grep pattern | wc -l` agree only because grep always terminates its output. Data from `echo -n`, partial writes, or editors without final newlines needs a decision: fix the file (`sed -i -e '$a\'`) or accept the convention.
- **`-c` is bytes — the letter is a trap.** The flag originally meant "characters" back when one character was one byte; today every mainstream `wc` (GNU, BSD, BusyBox) defines `-c` as bytes and reserves characters for `-m`. Scripts that "compensated" by adding locale tricks instead of just using `-m` are the bug source; assert byte sizes with `-c`, character counts with `-m`, and remember GNU `-w`'s word definition is locale-whitespace-based (a UTF-8 locale counts non-breaking spaces as separators, C does not).
- **`-m` performance under multibyte locales is real.** UTF-8 decoding per byte makes `-m`/default (all four counts) noticeably slower than `LC_ALL=C wc -l` on gigabyte logs. If you only need lines, ask for only lines — requesting fewer metrics is also faster, and `LC_ALL=C` is legitimate when the input is known ASCII.
- **The fast path exists only for `-c` on regular files.** `wc -c < file` and `wc -c file` are O(1) via `fstat()`, but any pipeline invocation (`cat file | wc -c`) must read the stream. For pure file size, `stat -c %s file` is the direct expression of the same metadata.
- **Filenames with newlines break `wc file1 file2`-style listings** and, more subtly, `ls | wc -l` is not "count of files" for such names (nor for `ls` column packing). The NUL-safe pair is `find ... -print0 | wc --files0-from=- -l`.
- **Column width drift:** count columns are right-aligned and grow past 7 digits; scripts that slice fixed columns (`cut -c1-7`) from `wc` output break on huge counts — parse with `awk '{print $1}'` or use `wc -l < f`.
- **`-L` measures display width, not length.** Tabs blow it up to the next tab stop, ANSI color escape sequences count as visible columns (making "line length" wrong for colored output), and it is GNU-only — absent on macOS/BSD wc.
- **Exit status:** 0 on success, 1 on any error (unreadable file, bad option). Note `wc` on a directory prints an error for the directory but still counts other files, exiting 1 — inside `set -e` pipelines this is a surprise.
- **Portability:** POSIX guarantees `-l -w -c -m` (with `-m`'s exact behavior locale-dependent). `-L`, `--total`, `--files0-from` are GNU. BusyBox `wc` covers the POSIX four.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All requested counts computed |
| 1 | Any error: unreadable/missing file (including directories), bad option, bad `--files0-from` list |

## Related Commands

- [`overview`](./overview.md) — GNU Coreutils collection hub.
- [`stat`](./stat.md) — file size as metadata (`stat -c %s`), the no-read alternative to `wc -c`.
- [`head`](./head.md) / [`tail`](./tail.md) — the bounds checkers that share wc's newline semantics.
- [`cut`](./cut.md) — feeds single fields to `wc -l` in counting pipelines.
- [`sort`](./sort.md) — its `-u` output length is what `sort | uniq | wc -l` measures.
- [`uniq`](./uniq.md) — distinct-value counting: `sort | uniq | wc -l` vs `sort -u | wc -l`.
- [`grep`](../../shell/grep.md) — `grep -c` counts matches per file; wc counts the stream.
- [`numfmt`](./numfmt.md) — humanize the byte counts wc produces (`wc -c | numfmt`).

## Interview Questions

### Q: What does `wc -l` actually count, and when does that differ from "number of lines"?

It counts `\n` bytes. POSIX defines a line as newline-terminated, so a final line lacking its terminator does not count: `printf 'a\nb' | wc -l` is 1, not 2. The difference surfaces whenever data loses its final newline — `echo -n`, binary-ish logs, concatenated file fragments — and it matters for correctness checks (`wc -l < file` as a row count) and for round-trips with tools that count *records* instead (`awk 'END{print NR}'` counts the unterminated last line). Knowing both numbers can differ — and why — is the expected answer.

### Q: Explain the difference between `wc -c` and `wc -m`, including performance implications.

`-c` counts bytes; `-m` counts characters by decoding input with the current locale's character set. Under `LC_ALL=C` they're identical; under UTF-8, `é` is 2 bytes but 1 character. Performance: `-c` on a regular file can be answered from `fstat()` without reading — GNU wc's fast path makes `wc -c < 2G.file` near-instant. `-m` must read and decode every byte (mbrtowc), making it the slowest count on multibyte data; `LC_ALL=C wc -m` collapses back to byte counting when the data is ASCII. The design point: byte counts are I/O-bound-at-worst, character counts are CPU-bound by decoding.

### Q: Why is `wc -c < file` sometimes instant while `cat file | wc -c` always reads the whole file?

GNU wc optimizes byte-count-only requests on regular, seekable files by taking the size from the file's metadata (`fstat`/`lseek`) and skipping the read entirely — the same information `stat -c %s` reports. Through a pipe, the input is a stream with no knowable size, so every byte must be read and counted; the fast path is structurally unavailable. The lesson generalizes: where you place the file in the pipeline (operand or redirect vs. intermediate stage) changes the asymptotic cost of even "trivial" tools.

### Q: You need "number of files in /var/log". Compare `ls | wc -l` and the NUL-safe alternative.

`ls | wc -l` is the quick-and-dirty answer and is wrong in edge cases: filenames containing newlines are counted as multiple lines, `ls` may emit multi-column output when stdout is a terminal (never in a pipe — that part is safe), and hidden files are excluded by default. The robust form is `find /var/log -maxdepth 1 -type f -print0 | wc --files0-from=- -l` — NUL-separated names cannot split mid-name, `-type f` states the intent (files, not directories), and GNU wc consumes the list directly. Mention `ls -1 | wc -l` as the common half-fix and dotfile inclusion via `find` as the semantic difference.

### Q: A script does `wc -l *.log` and processes the output with `cut -d' ' -f1`, then breaks on large files. Diagnose.

Two interacting issues. First, `wc` with file arguments appends filenames and adds a `total` line — field positions shift, and the total pollutes the stream. Second, count columns are right-aligned with a width that grows once counts exceed the default field width, so `cut -c`/`-d' '` slicing grabs padded spaces or truncated numbers. Fixes: use `wc -l < f` per file (bare number), parse with `awk '{print $1}'`, or use `--total=never` plus awk field extraction (GNU). The interview point is that wc's output is formatted for humans; scripts should either request minimal metrics via stdin redirection or parse with field-aware tools.

### Q: Why might an interviewer prefer `grep -c pattern file` over `grep pattern file | wc -l`, or vice versa?

`grep -c` exits after counting internally — no match lines cross the pipe — and reports per-file counts plus filenames, which `wc -l` cannot attribute; but it exits 1 when nothing matched, which trips `set -e` and pipeline error handling. `grep pattern | wc -l` streams uniformly, composes with other filters between grep and wc, and keeps a clean 0-exit semantic on "no matches". Performance differs by data: `-c` avoids writing matches out, while the pipe form pays for the extra process and the copied data. The answer should show awareness that exit codes, attribution, and stream composition — not just the number — are what differ.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/wc.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
