# tac — concatenate files in reverse, record by record

## Overview

`tac` is `cat` backwards: it writes each input file's *records* to standard output in reverse order. With the default record separator — the newline — that means "last line first". The name is the giveaway: `cat` spelled backwards, and the description in its man page is exactly "concatenate and print files in reverse".

It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/tac`, from upstream GNU coreutils. Beyond simple line reversal, its separator options make it a general record-order inverter: `-s SEP` treats any string as the record terminator (so it can reverse "sentences", paragraphs, or entries delimited by a marker), `-b` attaches separators before records instead of after, and `-r` interprets the separator as a regular expression.

You reach for it when the *order of records* is the problem: reading a growing log newest-first, getting the last N matches in their original order, reversing generated SQL/batch statements so the undo comes first, or flipping a one-record-per-line dataset. It is often confused with `rev` (reverses *characters within each line*), with `sort -r` (sorts descending — order depends on collation, not on input order), and with BSD `tail -r`, which does the plain newline case but does not exist in GNU tail.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/tac` |
| First appeared / lineage | GNU fileutils-era utility (Jay Lepreau, David MacKenzie); upstream GNU coreutils |
| Standards | Not POSIX; GNU coreutils convention (also a BusyBox applet; absent from macOS/BSD base) |

## Synopsis

```
tac [OPTION]... [FILE]...
```

Main forms:

```
tac app.log                      # whole log, last line first
tac app.log | grep ERROR         # newest matches first
tac -s ';' script.sql            # reverse ;-terminated records
tac -b -s '}' chunks.txt         # separators lead their record
tac -r -s ' ' sentence.txt       # separator is a regex (here: spaces)
tac - input.pipe                 # reverse a stream on stdin
```

With no `FILE`, or when `FILE` is `-`, standard input is read. Multiple files are reversed record-wise in argument order — file 1's records reversed, then file 2's — not interleaved into one global sequence.

## How It Works

### The record model

`tac` does not know about "lines". It reads its input as a sequence of records, where a record is *text followed by its separator* (by default, a newline). The output is simply the records concatenated in reverse order:

```
input:   [alpha\n][bravo\n][charlie\n][delta]
                                        └─ last record: unterminated
                                         (no trailing newline)

output:  delta charlie\n bravo\n alpha\n   →   "delta charlie" on line 1!
```

That model explains every tac behavior, including the two most surprising ones. First, an unterminated final chunk is a record in its own right and therefore comes *first* in the output, separator-less:

```bash
$ printf 'a:b:c' | tac -s :
cb:a:                          # records were a:, b:, c (dangling)
$ printf 'l1\nl2\nl3' | tac
l3l2
l1                             # records: l1\n, l2\n, l3 (dangling)
```

Second, a *fully terminated* input has no dangling record, so plain reversal is clean:

```bash
$ printf 'one\ntwo\nthree\n' | tac
three
two
one
```

Multiple files concatenate in argument order, each reversed internally:

```bash
$ printf '1\n2\n' > m1.txt; printf '3\n4\n' > m2.txt
$ tac m1.txt m2.txt
2
1
4
3
```

### `-s`: an arbitrary separator string

`-s STRING` replaces the newline as the record terminator. The terminator itself stays attached to the record it ended (that is the default "after" attachment):

```bash
$ printf 'a:b:c:' | tac -s :
c:b:a:                          # records a:, b:, c: — reversed, colons intact
$ printf 'END1END2' | tac -s END
21ENDEND                        # records: END, 1END, 2 (dangling) — reversed
```

The second example is the record model working exactly as documented: the input *begins* with a separator, so the first record is the empty text plus its terminator `END`; reversing emits the dangling `2` first, then `1END`, then the leading `END`.

### `-b`: attach the separator before

`-b/--before` flips the attachment: a record is *separator followed by text*. This matters when the separator is a prefix by design — JSON-ish braces, list bullets, section markers — and it changes the dangling-record bookkeeping: a fully terminated input ends with one extra record consisting of the final separator and empty text, which surfaces at the *start* of the output. Byte-exact:

```bash
$ printf 'x!y!z!' | tac -b -s '!' | od -c
0000000   !   !   z   !   y   x
$ printf 'A-B-C-' | tac -b -s '-' | od -c
0000000   -   -   C   -   B   A
$ printf 'one\ntwo\nthree\n' | tac -b | od -c
0000000  \n  \n   t   h   r   e   e  \n   t   w   o   o   n   e
```

Reading the last one through the model: records are `one`, `\ntwo`, `\nthree`, `\n` (the trailing newline plus empty text); reversed, that concatenates to `\n`, `\nthree`, `\ntwo`, `one` — which is why `tac -b` on a text file looks "broken" while `tac -b -s '}'` on brace-delimited records looks exactly right. The tool is consistent; the separator choice decides whether the result reads naturally.

### `-r`: regex separators

`-r/--regex` interprets the separator as a POSIX extended regular expression, matched against the input to find record boundaries:

```bash
$ printf 'foo bar baz\n' | tac -r -s '[ ]'
baz
bar foo                        # records: "foo ", "bar ", "baz\n"
$ printf 'a1b2c\n' | tac -r -s '[0-9]'
c
b2a1                           # digits were the separators
```

Note in the first example that the trailing newline rides along inside the last record — the regex `[ ]` only claims spaces, so the record order flips but the newline stays glued to `baz`. Regex separators are the sharpest tool in tac's box and the easiest to misuse: patterns that match the empty string, or that swallow more than you intend (greedy quantifiers, `.*`), yield silently garbled output rather than an error.

### Memory behavior

A reversing tool cannot emit its first record until it has seen the input's end — so what tac never does is stream output as it reads. What it also does *not* do is load the whole input into RAM. For a regular file it reads backwards in place, block by block; for a pipe it first spools the entire stream to an unnamed temporary file and then reads that backwards (observable as a deleted `/tmp/cutmp…` file among tac's open file descriptors while it runs). In both cases, what must fit in memory is a single record: under a 50 MB memory cap, tac reverses a 100 MB file of short lines — but dies with `tac: memory exhausted` on a 100 MB file containing one newline-less record. Two consequences: pipe-fed tac costs disk, not RAM; and a stream with huge separator-free stretches costs RAM proportionally.

```
pipe input:  stdin ─► (spool to /tmp/tacXXXX) ─► read backwards ─► stdout
file input:             regular file ─► read backwards in place ─► stdout
memory:                 bounded by the largest single record
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-b`, `--before` | Attach the separator before its record instead of after |
| `-r`, `--regex` | Interpret the separator as a POSIX ERE |
| `-s`, `--separator=STRING` | Use STRING as the record separator instead of newline |

That is the entire manual — three flags. All the real variation comes from choosing the separator, which is why the record model above matters more than option trivia.

## Usage Patterns

```bash
# Read a growing log newest-first (the classic)
tac /var/log/syslog | less
```

```bash
# Rotate-and-read pattern: snapshot the log, then read it newest-first
tac app.log.1 | less
```

```bash
# Last 10 errors in chronological order: reverse, filter, reverse back
tac app.log | grep ERROR | head -n 10 | tac
```

```bash
# Undo-first scripts: reverse generated statements so rollback lines precede
tac -s ';' migration.sql > rollback-first.sql
```

```bash
# Reverse one field-per-line export back into the original record order
tac records.txt
```

```bash
# Reverse word order of a sentence (spaces as regex separators)
printf 'the quick brown fox\n' | tac -r -s ' '
```

```bash
# Reverse order of JSON-ish records delimited by a leading brace
tac -b -s '{' stream.ndjson | less
```

```bash
# Reverse marker-delimited chunks (### acts as the separator regex)
printf '### alpha body1 ### beta body2' | tac -r -s '###'
```

```bash
# Reverse the output of a generator without a temp file
seq 1 5 | tac
```

```bash
# Feed newest-first into a pipeline that assumes newest-last input
tac metrics.log | analyzer --stream
```

```bash
# Sanity-check the record model on a toy input
printf 'a:b:c:' | tac -s : ; printf '\n'
```

## Nuances and Gotchas

- **`tail -r` is BSD-only.** GNU tail rejects the flag outright (`tail: invalid option -- 'r'`), and macOS/BSD ship `tail -r` but no `tac` (GNU coreutils installs as `gtac` via package managers). A "reverse these lines" one-liner that works on Linux (`tac`) breaks on macOS and vice versa (`tail -r`). Portable scripts either require coreutils or hand-roll with `awk '{a[NR]=$0} END{for(i=NR;i>0;i--) print a[i]}'`.
- **`rev` is not `tac`.** `rev` reverses characters within each line and keeps line order; `tac` reverses record order and keeps characters intact. `printf 'abc\ndef\n' | rev` gives `cba` / `fed`; `tac` gives `def` / `abc`. The man pages even cross-reference each other (SEE ALSO) because the names invite exactly this mix-up.
- **The unterminated final record comes first.** With no trailing separator, the last chunk is a record and leads the output *without* its separator (`a:b:c` → `cb:a:`). Piping tac output into a parser that expects every line terminated will chew on that first line. The fix is input hygiene: guarantee a trailing newline upstream.
- **`-b` on fully terminated input emits a leading separator.** The trailing separator becomes the empty final record, which reverses to the very front of the output (`x!y!z!` → `!!z!yx`). This is correct-by-model but routinely read as a tac bug; strip or account for the leading separator downstream.
- **`-r` regexes are POSIX ERE, and empty matches are poison.** A separator pattern that can match the empty string (e.g. `x*`) does not error — it just shreds the input into nonsense records. Keep separator patterns non-empty, concrete, and as short as possible; test on a two-record toy file first.
- **`-s` attaches to the *end* of each record by default.** People expecting "split on separator, reverse chunks, separators stay with the *next* chunk" get `-b` instead. Re-derive from the model: default record = text + sep; `-b` record = sep + text.
- **Memory scales with the longest record; disk scales with the stream.** tac holds at most one record in RAM — but on a pipe it first spools the *entire* input to an unnamed temp file (watch for a deleted `/tmp/cutmp…` among its file descriptors) before reading it backwards. One giant record — a multi-GB single-line file, a separator-less feed — must be buffered whole; the failure is `tac: memory exhausted` mid-run, not a clean startup error.
- **Sorting is not reversing.** `sort -r` orders by collation; `tac` preserves the input's record order exactly, mirrored. For logs, where timestamps are already ordered and equal timestamps must keep their arrival order, `tac` is the only correct "newest first".

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All records reversed and written successfully, including empty input |
| 1 | Any failure: unreadable/missing file (`tac: failed to open '...' for reading`), or memory exhaustion on a giant record |

## Related Commands

- [`cat`](./cat.md) — the forward direction; same concatenation semantics, multiple files, stdin.
- [`tail`](./tail.md) — BSD `tail -r` covers tac's newline case; GNU `tail -n` grabs the last records without reversing.
- [`sort`](./sort.md) — `sort -r` is collation-based ordering, not order reversal.
- [`wc`](./wc.md) — count records before reversing when downstream tooling assumes terminated lines.
- [`head`](./head.md) — `tac | head` = last records first; `tac | head | tac` restores chronological order.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [sed-awk](../../shell/sed-awk.md) — awk's two-pass array idiom is the portable fallback for reversal.

## Interview Questions

### Q: How do you show the last 10 lines of a log file that match a pattern, in chronological order?

`tac app.log | grep PATTERN | head -n 10 | tac`. The first `tac` flips the file so the newest records arrive first; `grep` keeps matching ones in newest-first order; `head -10` caps it; the final `tac` restores chronological order. It is O(file) but pipeline-parallel, avoids temp files, and works on any POSIX system with GNU tools. The follow-up an interviewer wants: `tac` in the middle, not `sort -r` — sorting would reorder equal timestamps and destroy the arrival sequence.

### Q: Explain exactly what `tac` does with an input whose last line has no trailing newline.

The model is records = text + separator. A dangling final chunk is a record without its separator, so it comes first in the output, unterminated: `printf 'l1\nl2\nl3' | tac` produces `l3l2\nl1\n` — the first output line is "l3l2" glued together. Any pipeline that parses tac's output line-by-line must account for that first line. The defensive fix is upstream: guarantee the trailing newline before reversing.

### Q: What is the difference between `tac`, `rev`, and `tail -r`?

Three different axes: `tac` reverses *record order* (records are separator-delimited chunks — usually lines); `rev` reverses *characters within each line*, preserving order; `tail -r` (BSD/macOS only) reverses lines, i.e. tac's newline case, but has no separator or regex options. Portability-wise, GNU systems have tac but not `tail -r`; BSD/macOS have `tail -r` and, via GNU coreutils package managers, `gtac`.

### Q: When would you use `tac -s` or `tac -b -s` instead of plain tac?

When records are not newline-delimited. `-s ';'` reverses semicolon-terminated statements (SQL migrations, protocol messages); `-s '}'` or `-b -s '{'` handles brace-delimited chunks, with `-b` when the delimiter *leads* its record rather than trailing it; `-r -s ' '` with a regex reverses space-separated fields. The rule of thumb: plain tac for lines, `-s` when the grammar has one fixed delimiter, `-r` only when the delimiter genuinely needs pattern power — and never with a pattern that can match empty.

### Q: A teammate says "tac loads the whole file into memory, so we can't use it on our 50 GB logs." Evaluate the claim.

Wrong on the memory axis, worth a caveat on two others. tac never holds the whole input in RAM: regular files are read backwards in place, and pipe input is spooled to an unnamed temp file first, then read backwards — a 100 MB file of short lines reverses comfortably under a 50 MB memory cap (verified with `ulimit -v`). What must fit in memory is a single record: a 50 GB newline-less file needs 50 GB of RAM because the first output byte cannot be emitted until the record's start is known. Caveats for the pipeline design review: the first output byte only appears after the whole input is consumed, and pipe input pays a disk-spool cost — so live streams are out either way.

### Q: Why is `tac` not in POSIX, and does that matter?

POSIX standardized the tool set as it existed across AT&T and BSD systems in the late 80s; `tac` was a GNU addition (its authors are from the BSD academic side, but the tool shipped with GNU fileutils), so it never entered the standard. It matters practically on macOS and the BSDs, where base installs lack it (`gtac` via package managers, or `tail -r`/awk fallbacks); on Linux and busybox-based minimal images it is effectively universal. The interview point: know which of your "obvious" tools are POSIX and which are GNU conventions.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/tac.1.en.html)
