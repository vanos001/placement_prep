# head — print the first lines or bytes of each file

## Overview

`head` copies the beginning of each input to standard output: by default the
first 10 lines, or a caller-chosen number of lines or bytes. It is the
front-half of the classic "look at a slice of data" pair — `head` takes the
top, [`tail`](./tail.md) takes the bottom — and it doubles as a flow-control
device in pipelines, because it stops reading as soon as it has enough output,
which typically kills the upstream producer with `SIGPIPE`.

Day-to-day it shows up in three roles: previewing large files and command
output (`dmesg | head`), bounding expensive pipelines (`seq 1000000 | head -n
5`), and surgical trimming such as "print everything except the last line"
(`head -n -1`), which the negative-count GNU extension makes a one-liner.
Its header block (`==> file <==`) when given multiple operands is also the
standard way to peek at the first line of many files at once.

`head` is often confused with `sed -n '1,10p'` (same result, more overhead),
with `more`/`less` (interactive pagers, not filters), and with `tail` (the
mirror operation, but with subtly different flag conventions).

| Field | Value |
|---|---|
| Package | Debian `coreutils` (bookworm; Essential package) |
| Upstream | GNU coreutils |
| Section (man) | 1 |
| Path | `/usr/bin/head` |
| First appeared / lineage | PWB/UNIX (1977); GNU implementation shipped in fileutils, merged into GNU coreutils (2003) |
| Standards | POSIX.1-2018 mandatory utility; POSIX standardizes only `-n` and marks the obsolete `-N` form obsolescent |

## Synopsis

```
head [OPTION]... [FILE]...
```

Common forms:

```
head file                     # first 10 lines
head -n 25 file               # first 25 lines
head -c 1K file               # first 1024 bytes (K = 1024)
head -n -5 file               # everything except the last 5 lines
head file1 file2              # both files, with ==> file <== headers
command | head -n 5           # first 5 lines of a stream
```

## How It Works

### Selection semantics

`head` needs exactly one *count*: either lines (`-n`) or bytes (`-c`).
When both are given, **the last one on the command line wins** — there is no
"first N lines AND M bytes" mode. The GNU count argument may carry a leading
sign, and the sign changes the meaning:

```
             ┌─────────────────────────────────────────────┐
             │  head -n K / head -c K — what is printed    │
             ├─────────────────────────────────────────────┤
             │                                             │
             │  K > 0:   first K units                     │
             │           head -n 3     → lines 1..3        │
             │           head -c 512   → bytes 1..512      │
             │                                             │
             │  K = 0:   nothing (but exit status 0)       │
             │                                             │
             │  K < 0:   all input EXCEPT the last |K|     │
             │           units (GNU extension)             │
             │           head -n -3    → all but last 3    │
             │           head -c -4    → all but last 4    │
             │                                             │
             │  Mirror image in tail:                      │
             │  tail -n +K   → from line K to the end      │
             │  tail -c +K   → from byte K to the end      │
             └─────────────────────────────────────────────┘
```

Verified behavior on a 10-line file:

```bash
# A negative line count prints all but the last K lines
$ seq 1 10 > ten.txt
$ head -n -3 ten.txt
1
2
3
4
5
6
7

# Same idea for bytes: all but the last 4 bytes
$ head -c -4 ten.txt
1
2
3
4
5
6
7
8
9
```

Note the byte form's output ends mid-stream: `head -c` performs **no line
accounting at all**, so the last "line" it prints may be a partial line.
This is exactly what you want for binary data and a subtle trap for text
(see Nuances).

### Old and new count syntax

Historically `head` accepted the count as a bare option argument —
`head -3 file` means "first 3 lines". GNU coreutils still accepts this
"obsolete syntax" but only under a strict rule: **the obsolete option must be
the last (trailing) option** on the command line. The moment another option
follows it, parsing fails:

```bash
# Obsolete form: works, count is trailing
$ head -3 ten.txt
1
2
3

# Modern, unambiguous form — use this in scripts
$ head -n 3 ten.txt

# Obsolete count followed by another option: rejected
$ head -q -1 ten.txt
head: invalid trailing option -- 1

# The modern equivalent works fine
$ head -q -n 1 ten.txt /etc/hostname
1 c-6ac89cf4-14810412-394312c537f8
```

`tail` is even stricter — its obsolete `-1` form must also appear first in
its own option group, and it fails with
`tail: option used in invalid context -- 1` when misplaced. The portable,
future-proof habit is `-n K` everywhere.

### Multi-file operation

With more than one operand (or with `-v`), each file is preceded by a header:

```bash
$ head -n 1 ten.txt /etc/hostname
==> ten.txt <==
1

==> /etc/hostname <==
c-6ac89cf4-14810412-394312c537f8
```

With exactly one file operand and no `-v`, no header is printed — this is why
`head file` output can be piped without cleanup, while `head file1 file2`
output cannot. `-q` suppresses headers unconditionally, `-v` forces them even
for a single file. A `FILE` operand of `-` means standard input.

### Bytes vs lines, and why -c is fast

For `-c K`, `head` reads at most ceil(K / blocksize) blocks from the input
and stops — it never scans for `\n`. For `-n K` on a seekable file, recent
GNU `head` also avoids reading the whole file: it can seek near the beginning
and copy forward. The important pipeline consequence: **`head` exits as soon
as it has its quota**, it does not drain its input. When the input is a pipe,
the upstream writer then gets `SIGPIPE` (signal 13) on its next write:

```bash
# The producer is killed as soon as head has had enough
$ seq 1 100000 | head -2
1
2
$ echo "${PIPESTATUS[0]} ${PIPESTATUS[1]}"
141 0
```

Exit code 141 is 128+13, the shell's convention for "died by SIGPIPE".
`head` itself still exits 0. This is the mechanism that makes
`yes | head -n 3` terminate instead of running forever — the two commands
form a self-cleaning loop:

```bash
# yes would never end on its own; head's early exit is the kill switch
$ yes | head -n 3
y
y
y
```

## Options That Matter

| Option | Effect |
|---|---|
| `-n K`, `--lines=K` | Print first K lines; `K < 0` prints all but the last K lines |
| `-c K`, `--bytes=K` | Print first K bytes; `K < 0` prints all but the last K bytes; no line awareness |
| `-q`, `--quiet`, `--silent` | Never print `==> file <==` headers |
| `-v`, `--verbose` | Always print the header, even for a single file |
| `-z`, `--zero-terminated` | Units are NUL-separated records, not newline lines — pairs with `find -print0` |
| `K` suffixes | `b`=512, `k`/`K`=1024 (k is 1000 in `kB`), `M`, `G`, ... — apply to both `-n` and `-c`, line counts included |
| `--` | End of options; lets you inspect files whose names begin with `-` |

`-n` and `-c` are mutually exclusive in effect — the last one given wins;
there is no combined "first N lines and M bytes" mode, so compose `head` and
`tail` for a bounded middle slice. `-q`/`-v`/`-z` change only output framing,
never selection; `-z` pairs with `find -print0` NUL streams.

## Usage Patterns

```bash
# Preview the start of a big log without opening a pager
$ head -n 20 /var/log/syslog
```

```bash
# Top of an expensive pipeline: seq is killed by SIGPIPE after ~6 writes
$ seq -f '%.10g' 1e9 | head -n 5
```

```bash
# First line of every CSV — the classic multi-file header trick
$ head -n 1 *.csv
==> customers.csv <==
id,name,joined
==> orders.csv <==
order_id,customer_id,total
```

```bash
# Same but header-free, e.g. to build a combined schema line
$ head -q -n 1 *.csv | tr ',' '\n' | sort -u
```

```bash
# Drop the last line of a file (e.g. a trailing summary row) — GNU extension
$ head -n -1 report.txt > report.body
```

```bash
# Sample the first 64 KiB of a binary for file-type identification
$ head -c 64K image.bin | od -A x -t x1z | head -n 4
```

```bash
# First 10 lines of stdin explicitly with the '-' operand
$ printf 'a\nb\nc\n' | head -n 2 -
a
b
```

```bash
# NUL-delimited records: first 2 filenames from find, newline-safe
$ find . -name '*.tmp' -print0 | head -z -n 2 | xargs -0 rm -f
```

```bash
# Obsolete-but-common form you will meet in old scripts (trailing only)
$ head -5 ten.txt
```

```bash
# Copy the first 1 MiB of a large transfer to sanity-check a download
$ head -c 1M big.iso > sample.iso
```

## Nuances and Gotchas

- **SIGPIPE is a feature and a hazard.** Upstream commands killed by `head`'s
  early exit show status 141. Under `set -o pipefail`, a normal
  `find ... | head -n 10` becomes a *failing* pipeline; guard it or reset
  `PIPESTATUS`. Programs that intercept SIGPIPE (some Python/Node runtimes
  print `BrokenPipeError` traces instead of dying quietly) can spew errors
  after `head` leaves.
- **The producer may not stop instantly.** `head` exits, but the upstream only
  dies on its *next write*. A command that computes for a minute between
  writes keeps running after `head` is gone; add `timeout` if the side
  effects (not just the output) must stop.
- **Obsolete `-N` must trail.** `head -q -1 f` fails with
  `invalid trailing option -- 1`; `head -1 -q f` fails too. Only
  `head -1 f`-shaped commands are accepted. Prefer `-n K` unconditionally.
- **Last count wins.** `head -n 5 -c 100 f` prints 100 *bytes*, not the first
  100 bytes of 5 lines. Scripts that build the command dynamically can
  accidentally swap the selection mode.
- **Negative counts are a GNU extension.** POSIX.1-2018 standardizes only
  `-n` with a positive count; `head -n -3` and `head -c -3` will not behave
  the same in every lightweight `head` (BusyBox in minimal containers, for
  example). Also verify multi-file header behavior there.
- **`-c` output can end mid-line.** `head -c 10` of a text file may emit a
  partial line with no trailing newline; a following command in the pipeline
  then processes a corrupt last record.
- **`K` is 1024 but `kB` is 1000.** `head -c 1K` reads 1024 bytes;
  `head -c 1kB` reads 1000. The `b` suffix is 512-byte blocks — three
  different "kilo" conventions in one flag.
- **No header with a single operand.** `head f` is clean to pipe;
  `head f1 f2` is not. Adding a second operand silently changes output
  framing — use `-q` when combining outputs.
- **Exit status hides partial failure.** `head a.txt missing.txt` still
  prints `a.txt`'s head but exits 1. A `head "$@" | ...` pipeline over a glob
  that may include unreadable files can fail non-obviously.
- **`head -` reads stdin, not a file named `-`.** For files whose names begin
  with a dash, use `head -- ./-f` (the `./` prefix also disarms the dash).

## Exit Status

| Status | When |
|---|---|
| 0 | Selection completed (including `-n 0` / `-c 0`, which produce no output) |
| 1 | Any operand could not be read (missing file, permission denied) or a count was invalid; remaining operands are still processed |
| 141 | Not produced by `head` itself: seen on the *upstream* side of a pipe when it is killed by SIGPIPE after `head` exits |

## Related Commands

- [`tail`](./tail.md) — the mirror operation: last lines/bytes, `-n +K` from a line onward, and live `-f`/`-F` following.
- [`cat`](./cat.md) — the unbounded version of the same stream-copy job; `head`/`tail` exist because you usually want only a slice.
- [`wc`](./wc.md) — counts lines/bytes across the whole input; combine with `head` when a "how many" answer needs a sample too.
- [`cut`](./cut.md) — slice *within* a line where `head` slices across the stream.
- [`od`](./od.md) — the natural consumer for `head -c` byte samples of binary data.
- [`csplit`](./csplit.md) — splits a file into context-defined pieces, a heavier cousin of head/tail slicing.
- [Overview — GNU Coreutils collection](./overview.md) — hub page for the collection.
- [`grep`](../../shell/grep.md) — the other half of `build | head` triage pipelines.
- [`sed-awk`](../../shell/sed-awk.md) — `sed -n '1,Np'` and `awk 'NR<=N'` overlap with `head`; head is faster and clearer.

## Interview Questions

### Q: What does `head -n -5 file` do, and will it work everywhere?

It prints the whole file except the last five lines — the negative count
inverts the selection. This is a GNU extension: POSIX.1-2018 only defines
`-n` with a positive count, so strictly POSIX or minimal (BusyBox) `head`
implementations may reject it or treat `-5` differently. In scripts that must
run on minimal images, the portable replacement is
`total=$(wc -l < file); head -n $((total - 5)) file`, or use `sed '$d'`
repeatedly for single-line deletion.

### Q: `seq 1 1000000 | head -n 3` returns instantly. Why doesn't the shell wait for seq?

`head` exits as soon as it has printed 3 lines and stops reading the pipe.
The next time `seq` writes, the kernel returns `EPIPE` and delivers `SIGPIPE`,
which kills it; the shell reports exit status 141 (128+13). This is why
unbounded generators terminate when piped into `head`, and it is also the
classic `pipefail` trap: with `set -o pipefail`, this perfectly normal
pipeline exits non-zero because one member died by signal.

### Q: A teammate wrote `head -q -1 fileA fileB` and got `head: invalid trailing option -- 1`. Explain.

The `-1` is obsolete `head` syntax: a bare number as an option. GNU coreutils
accepts it only when it is the trailing (last) option; here `-q` precedes it
and file operands follow, so the parser rejects it. The modern spelling is
`head -q -n 1 fileA fileB`. The broader lesson is that the short-digit
syntax is a compatibility shim, not a first-class option — always use the
long-era `-n K`/`-c K` forms in anything you keep.

### Q: Why is `head -c 1M file` dramatically faster than `head -n 10000 file` on a 10 GB text file?

`-c 1M` stops reading after exactly one mebibyte — a single bounded read of
the file's front. `-n` must count 10 000 newline characters, and in the worst
case (very long lines) that can force reading gigabytes before the count is
satisfied. Byte mode also needs no line bookkeeping at all, so for binary or
machine-generated data it is the natural sampling tool. If you need "about
the first N lines fast", cap with `-c` plus a tolerant consumer, or accept
the line-scan cost.

### Q: How would you print lines 1000 through 1009 of a 20 GB file, and why is `head`+`tail` the right shape?

`head -n 1009 huge | tail -n 10` — head stops after 1009 lines so the work is
proportional to 1009 lines, and tail buffers only the last 10 of those; the
reverse order would read the *whole* file first. This head-then-tail
composition is the standard idiom for a bounded middle slice and shows an
interviewer you understand that each stage's early-exit behavior determines
total I/O, not just correctness.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/head.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
