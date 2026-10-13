# sort — sort, merge, or check lines of text

## Overview

`sort` orders lines of text. That one-sentence job description hides the fact that it is one of the most feature-dense programs in coreutils: four different numeric comparison modes, a field/key grammar with per-key options, locale-aware collation, a check mode, a merge mode, and an external merge engine that can sort files far larger than RAM. It is half of the most famous pipeline in Unix — `sort | uniq` — and the standard pre-processing step for `comm`, `join`, and every "group and count" one-liner.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/sort`, from upstream GNU coreutils. `sort` is as old as Unix itself (it appears in the first editions of Research Unix) and is POSIX-standardized; GNU has layered the options that matter in practice (`-g`, `-h`, `-V`, `-s`, `-S`, `--parallel`, `-z`) on top of the POSIX core.

What it is often confused with: `uniq` (only removes *adjacent* duplicates, needs sorted input, has counting modes `sort` lacks), `tsort` (topological sort of a dependency graph — an entirely different beast), `awk`'s array sorting (fine for in-memory data, no external merge), and `shuf` (random order). `sort -R` overlaps with `shuf` but groups equal keys.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/sort` |
| First appeared / lineage | Research Unix v1 (early 1970s); GNU rewrite since 1988 era |
| Standards | POSIX.1-2018 (`sort`: `-b -c -d -f -i -k -m -n -o -r -t -u`) |

## Synopsis

```
sort [OPTION]... [FILE]...
sort [OPTION]... --files0-from=F
```

With no FILE, or when FILE is `-`, standard input is read. Three operation modes:

```
sort -k2,2n -t: data.txt          # sort mode: order and write lines
sort -m chunk.000 chunk.001       # merge mode: k-way merge of presorted files
sort -c archive.log               # check mode: verify sortedness, diagnose
sort -u -o out.txt in.txt         # -o writes to a file (may be the input)
```

## How It Works

### Three modes, one comparison engine

`sort` runs in one of three modes — sort (default), merge (`-m`), check (`-c`/`-C`) — and all three share the same key-extraction and comparison machinery:

```
            ┌──────────── input (files, stdin, --files0-from) ───────────┐
            v                                                            │
      read a line ──> extract keys (-k F[.C][OPTS]..., default: whole line)
            │
      compare line pairs: keys in -k order; equal? -> last-resort
            │   whole-line byte compare (disabled by -s)
            v
      sort mode:  in-memory sort (threads via --parallel)
            │        │ buffer full
            │        └──> write sorted RUN to temp file (-T, --compress-program)
            │              ...at EOF: k-way merge of runs (--batch-size)
            v
      merge mode:  skip the sort; assume inputs presorted, merge directly
      check mode:  scan until the first out-of-order pair, report, exit
```

The memory story is the part interviewers probe: `sort` fills an internal buffer (size set by `-S`), sorts it, spills it as a *run* to a temporary file, and at the end performs a k-way merge over all runs. A `-S 100M` sort of a 10 GB file therefore costs disk I/O, not an OOM. Temporaries go to `$TMPDIR` or `/tmp` unless `-T DIR` redirects them; `--compress-program=PROG` (e.g. `gzip`, `zstd`) shrinks runs at CPU cost.

### Fields and the -k grammar

By default the key is the whole line. `-k KEYDEF` restricts it, with the grammar:

```
KEYDEF = F[.C][OPTS][,F[.C][OPTS]]
```

- `F` is the field number, `C` the character position *within* the field; both count from 1.
- A one-sided key `-k2` runs from field 2 **to the end of the line** (delimiters included); `-k2,2` stops at the end of field 2. This distinction is the single most common `-k` bug.
- `OPTS` are one or more ordering letters `b d f g i M n R r V` that override the global ordering options for that key only — this is how you build multi-type sorts like `-k2,2n -k3,3r`.

Field splitting has two different models:

- **Default (blank transition):** fields are runs of non-blanks; leading blanks belong to the *following* field's start, and `-kN` characters are counted from the beginning of the preceding whitespace. `--debug` warns about exactly this.
- **`-t SEP`:** fields are split on each single occurrence of `SEP`; consecutive delimiters produce empty fields (like `cut -d`), and leading blanks are just part of field 1.

```
$ printf '  a  b  c\n' | sort --debug -k2
sort: text ordering performed using simple byte comparison
sort: leading blanks are significant in key 1; consider also specifying 'b'
  a  b  c
   ______
_________
```

The underscore lines show the key extent: field 2 begins *before* its preceding blanks, and because `-k2` is one-sided the key extends to end of line. Appending `b` to the key (`-k2b`) or pinning a character position (`-k2.1`) starts the key at the first non-blank.

The one-sided vs two-sided difference is observable in both directions — deduplication and stable ordering:

```
$ printf '1 a\n1 b\n' | LC_ALL=C sort -k1,1 -u
1 a                        # key is just "1" -> the two lines are equal, "1 b" dropped
$ printf '1 a\n1 b\n' | LC_ALL=C sort -k1 -u
1 a
1 b                        # key is "1 a"/"1 b" -> unequal, both kept

$ printf 'b 1 9\na 1 0\n' | LC_ALL=C sort -s -k2,2
b 1 9                      # equal field-2 keys, -s keeps input order
a 1 0
$ printf 'b 1 9\na 1 0\n' | LC_ALL=C sort -s -k2
a 1 0                      # one-sided key includes " 9"/" 0" -> real order flip
b 1 9
```

### The comparison families

All ordering is a choice between comparison functions; the letters stack onto keys or apply globally:

- **Byte/character (default):** locale collation sequence. Under `LC_ALL=C` this is raw byte order.
- **`-n`:** parse an optional sign, digits, and the locale decimal point, convert to the numeric value of that *prefix*; anything after the first non-numeric character is ignored. `10 apples` sorts as 10.
- **`-g`:** general numeric — full `strtold` conversion including exponents, `inf`, `nan`, hex floats. Slowest numeric mode; use when scientific notation or huge ranges exist, not for plain integers.
- **`-h`:** human-numeric — numbers with 1024-based suffixes `K M G T P E Z Y` (case-insensitive), as printed by `du -h`, `ls -lh`, `numfmt`.
- **`-V`:** version sort — digit runs compare numerically, non-digit runs bytewise (natural order, `strverscmp` semantics). Not semver-aware, but handles `a-1.10` vs `a-1.2` correctly.
- **`-M`:** month sort — leading blanks then a month abbreviation, case-folded, compared `JAN < FEB < ... < DEC`; non-months compare lowest. Only the first three letters are examined, so `JANUARY` sorts as `JAN`.
- **Modifiers:** `-r` reverse (applies to the whole comparison, last-resort included), `-f` fold case, `-d` dictionary order (blanks + alphanumerics only), `-i` ignore non-printing, `-b` ignore leading blanks in a key.

```
$ printf '1024\n512\n1K\n2M\n' | LC_ALL=C sort -h
512
1024                       # 1024 and 1K are numerically equal
1K                         # tie broken by last-resort byte compare
2M
$ printf 'a-1.5\na-1.10\na-1.2\na-2\n' | LC_ALL=C sort -V
a-1.2
a-1.5
a-1.10                     # a-1.10 > a-1.2, unlike plain byte order
a-2
```

### Locale: the LC_ALL=C decision

The default comparison goes through the locale's collation rules (`strcoll`) — case is folded into a secondary weight, punctuation is ignored at the primary level, accented letters interleave with base letters. Two consequences matter operationally:

1. **Output order depends on the machine's locale settings.** A sort run under `en_US.UTF-8` produces a different order than under `C`, and the same command can produce different output on two servers or CI images. If anyone downstream byte-compares, hashes, or diffs the output, sort under `LC_ALL=C` (or `LC_ALL=C sort -u`) so the order is a pure function of the input.
2. **Speed.** Collation through `strcoll` costs far more than `memcmp`. Even the lean multibyte locale available in this book's reference container shows the gap; real full-collation locales (e.g. `en_US.UTF-8`) typically make sort several times slower still:

```
$ # 2,000,000 lines, 48 MB, warm cache
$ time LC_ALL=C sort -S 500M big.txt >/dev/null          # ~0.7 s
$ time LC_ALL=C.utf8 sort -S 500M big.txt >/dev/null     # ~0.9 s
```

Rule of thumb: `LC_ALL=C sort` for machine-to-machine data (keys, IDs, paths), locale-aware sort only when humans will read the result and expect dictionary order.

### -u, stability, and the last-resort comparison

GNU `sort` is *not* stable by default, and the reason is subtle: when all keys compare equal, it performs a **last-resort comparison of entire lines** (as if only `-r` were in effect). Two fixes:

- `-s` / `--stable` disables the last-resort comparison, so equal-key lines keep input order (the merge-based internals preserve it).
- Or add explicit secondary keys: `-k2,2n -k1,1`.

`-u` outputs only the first of an equal run — but "equal" means *the compared keys are equal*, not the lines. With `-k1,1 -u`, `1 a` and `1 b` collide and only the first survives; with whole-line keys, `-u` dedupes whole lines and equals the `LC_ALL=C sort | uniq` idiom (uniq needs its input sorted and only collapses *adjacent* duplicates).

```
$ printf 'a b\na c\nb c\n' | sort -k1,1 -u
a b                        # "a c" suppressed: the KEY matched, not the line
b c
```

### Checking and merging

- `sort -c` scans for the first out-of-order pair, prints `sort: -:2: disorder: a`, and exits 1; `sort -C` / `--check=silent` does the same scan quietly. `sort -cu` additionally treats duplicates as violations (strict ordering) — the cheap way to assert an index/ID column is unique before `join`.
- `-m` merges presorted inputs without sorting. It does **not** verify sortedness (use `-c` first if it matters) and never spills: memory cost is one input buffer per file. Merging N pre-sorted logs is O(n log N) instead of O(n log n) and is how you combine per-hour chunks: `sort -m h00 h01 h02`.
- `--batch-size=NMERGE` caps how many files merge at once (more inputs are merged in passes through temp files); `-z` makes both sort and merge NUL-line-aware for `find -print0` pipelines.

## Options That Matter

### Ordering options

| Option | Effect |
|---|---|
| `-n` | Numeric: compare the numeric value of the line/key prefix |
| `-g` | General numeric: full float parse (exponents, inf, nan, hex) |
| `-h` | Human-numeric: 1024-suffixed sizes (`2K`, `1G`), as `du -h` prints |
| `-V` | Version/natural sort: numeric digit runs, `strverscmp` style |
| `-M` | Month order `(unknown) < JAN < ... < DEC`, first three letters |
| `-r` | Reverse the result of comparisons |
| `-f` | Fold case (treat lower as upper) |
| `-d` | Dictionary order: only blanks and alphanumerics considered |
| `-i` | Ignore non-printing characters |
| `-b` | Ignore leading blanks when finding keys |
| `-R` | Random sort: shuffle, grouping equal keys (see `shuf`) |

### Key and field options

| Option | Effect |
|---|---|
| `-k F[.C][OPTS][,F[.C][OPTS]]` | Define a key; OPTS `bdfgiMhnRrV` override globals per key |
| `-t SEP` | Field separator: one character; empty fields possible (default: blank transition) |
| `--debug` | Annotate which bytes each key uses; warn about suspect key specs |

### Mode, memory, output

| Option | Effect |
|---|---|
| `-m` | Merge presorted inputs; never sorts, never spills |
| `-c`, `-C` | Check sortedness; `-C` silent; `-cu` also rejects duplicates |
| `-u` | Output first of equal-key lines; with `-c` require strict order |
| `-s` | Stable: disable the last-resort whole-line comparison |
| `-S SIZE` | Main buffer size; `%` = percent of RAM, suffixes K M G T P E Z Y, `b` = bytes |
| `--parallel=N` | Sort threads (default: processor count capped at 8) |
| `-T DIR` | Temporary directory (else `$TMPDIR`/`/tmp`); repeatable |
| `--compress-program=PROG` | Compress temp runs with PROG (e.g. `gzip`, `zstd`) |
| `--batch-size=N` | Max files merged at once; extra files merge in passes |
| `-o FILE` | Write output to FILE — safe even when FILE is the input |
| `-z` | Lines terminated by NUL, not newline (pairs with `find -print0`) |
| `--files0-from=F` | Read the list of input file names from F (NUL-separated) |
| `--random-source=FILE` | Bytes feeding `-R` (fixed file → reproducible shuffle) |

## Usage Patterns

```bash
# Reproducible, fast, byte-order sort for pipeline consumption
LC_ALL=C sort access.log
```

```bash
# Biggest directories first: human-numeric reverse sort on du output
du -h /var/* 2>/dev/null | LC_ALL=C sort -h -r | head
```

```bash
# UID order from passwd: field sort with -t and a per-key numeric flag
sort -t: -k3,3n /etc/passwd
```

```bash
# Multi-type keys: by department (numeric), salary descending, then name
sort -t, -k2,2n -k3,3nr -k1,1 employees.csv
```

```bash
# ISO dates sort correctly field-by-field with numeric keys
sort -t- -k1,1n -k2,2n -k3,3n events.txt
```

```bash
# Keep the first line per user ID (dedupe on a key, not the whole line)
sort -t: -k1,1 -u dupes.txt
```

```bash
# Version-number sort for package names or release files
ls dists/*.list | sort -V
```

```bash
# Assert sortedness + uniqueness of a join key before join/comm (CI guard)
sort -c -u -t, -k1,1 keys.csv || { echo "keys not unique/sorted"; exit 1; }
```

```bash
# Merge hourly pre-sorted chunks without re-sorting (cheap k-way merge)
sort -m -t, -k1,1 h00.csv h01.csv h02.csv > day.csv
```

```bash
# NUL-safe: sort filenames from find without newline breakage
find . -name '*.conf' -print0 | sort -z | xargs -0 sha256sum
```

```bash
# 20 GB file on a small box: cap RAM, compress temp runs, fast /scratch disk
sort -S 512M -T /scratch --compress-program=zstd huge.tsv -o huge.sorted.tsv
```

```bash
# In-place sort — -o may overwrite its own input (unlike > redirect)
sort -o hosts.txt hosts.txt
```

```bash
# Deterministic shuffle for fair test sampling (fixed random bytes)
sort -R --random-source=seed.bin entries.txt
```

```bash
# Case-insensitive sort for humans with a machine-stable secondary key
LC_ALL=C sort -f -k1,1 names.txt
```

## Nuances and Gotchas

- **The last-resort comparison silently reorders equal-key lines.** `sort -k1,1` on `a 2\na 1` yields `a 1, a 2` — the whole lines are compared byte-wise after the key ties. Use `-s` when input order is meaningful (event logs, timestamps inside equal groups) or make every tiebreaker an explicit key.
- **`-u` dedupes on keys, not lines.** `sort -k1,1 -u` can drop lines that differ in every other field. This is a feature (top-1-per-group) and a bug source (expecting `sort | uniq` semantics). Whole-line `-u` equals `LC_ALL=C sort | uniq`; `uniq` alone only collapses adjacent duplicates.
- **Locale changes output order.** A default-locale sort is not portable between machines; diffable/hashable pipelines pin `LC_ALL=C`. Conversely, "dictionary order" for humans comes free from the locale — under `C` you must spell it out with `-f`.
- **`-t` changes the field model, not just the separator.** Default blank-transition never yields empty fields and lets `-kN` start at the preceding whitespace; `-t` splits on every delimiter, creating empty fields and shifting numbering. `sort -k2` on `a  b` and `sort -t' ' -k2` on `a  b` disagree.
- **`-n` is a prefix parse.** `sort -n` on `1,000` reads just `1` under a C numeric locale (no thousands-separator awareness there), and `10 apples` sorts as 10 — handy and hazardous. Empty or garbage prefixes all compare as 0 and tie into the last-resort compare.
- **`-k2` is not `-k2,2`.** One-sided keys run to end of line, silently dragging later fields into the comparison (see the `-s` example above). Reviewers should treat one-sided keys in scripts with suspicion.
- **`-h` understands only 1024-based suffixes** (`K`…`Y`). Decimal-suffixed data (`100 MB`, SI `kB`) and percentages are foreign to it; normalize with `numfmt` first.
- **`-V` is not semver.** It is digit-run natural ordering; pre-release conventions like `1.0-rc1 < 1.0` follow `strverscmp` quirks, not the semver spec. Fine for filenames, risky for release-ordering guarantees.
- **`-m` trusts you.** Merging unsorted input produces unsorted output with no diagnostic. The cheap contract check is `sort -c` with identical options before the merge.
- **Check mode has two volumes and a strict twin.** `-c` prints `sort: file:N: disorder: <line>` and exits 1; `-C` is silent; `-cu` also fails on duplicates. Note plain `-c` does *not* flag duplicate lines — only disorder.
- **Memory knobs interact.** Tiny `-S` values create many small temp runs (slow merge, I/O bound); `-S 100%` invites OOM on spiky systems. `--parallel` beyond ~8 threads buys little (the manual caps the default at 8) and multiplies memory by log N. If `/tmp` is a small tmpfs, a huge sort can fill it — point `-T` at real disk.
- **Portability.** `-g -h -V -R -s -S -T -z --parallel --compress-program --batch-size --debug` are GNU extensions; POSIX defines only the `-b -c -d -f -i -k -m -n -o -r -t -u` core. BusyBox sort is a small subset. `sort -o file file` overwriting the input is POSIX-guaranteed — the `> file` redirect is not.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Input was sorted / merged / written successfully |
| 1 | `-c`/`-C` used and the input was out of order (or contained duplicates with `-u`) |
| 2 | Serious trouble: unreadable file, I/O error, out of memory, bad option |

## Related Commands

- [`uniq`](./uniq.md) — collapse/count adjacent duplicates; the other half of the `sort | uniq` idiom, with `-c -d -u` reporting modes.
- [`shuf`](./shuf.md) — random permutations and random sampling; the right tool for pure shuffles (`sort -R` groups equal keys).
- [`tsort`](./tsort.md) — topological sort of dependency pairs; different problem, different algorithm.
- [`comm`](./comm.md) — set ops on two sorted files; its sortedness precondition is exactly `LC_ALL=C sort`.
- [`join`](./join.md) — relational join on a sorted key column; same precondition, same `LC_ALL=C` rule.
- [`numfmt`](./numfmt.md) — converts to/from human-readable sizes; normalize data so `sort -h` (or plain `-n`) applies.
- [`awk`](../../shell/sed-awk.md) — when keys need computation first (`asort`, formatted output), the job outgrows `sort`.
- [overview](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why do so many pipelines say `LC_ALL=C sort`? Give two independent reasons.

Reason 1 is correctness: default collation depends on the machine's locale, so byte-level outputs (hashes, diffs, `join`/`comm` pairing) are only reproducible if the order is a pure function of input bytes — C locale gives raw byte order. Reason 2 is performance: C-locale comparison is a memcmp-like byte compare, while `strcoll` with multi-level collation rules is typically several times slower; the gap compounds on the huge inputs where sort's speed matters. The same pinning fixes `join` and `comm`, which compare bytes.

### Q: Explain the difference between sort -k2 and sort -k2,2, and where each bites.

`-k2` starts at field 2 and runs to end of line, so trailing fields join the comparison; `-k2,2` stops at field 2. It bites in three places: with `-u` (keys "1 a" vs "1 b" differ, so no dedupe, while `-k1,1 -u` dedupes), with `-s` (one-sided keys make equal-looking keys actually differ, defeating stability), and in multi-key sorts where a later field must carry its own ordering flag — with `-k2` it is stuck with key 1's type. The `--debug` option prints the exact byte ranges of each key and is the reviewer's tool for this class of bug.

### Q: A colleague reports sort is slow and outputs differently on two servers. Diagnose.

Both symptoms have one likely root cause: locale collation. Without `LC_ALL=C`, sort calls strcoll per comparison — far slower than byte comparison at scale — and the collation order (case weighting, punctuation) differs between machines with different locale settings, so "identical" pipelines diverge. Fix: `LC_ALL=C sort` (or `LC_COLLATE=C`). If speed is still short after that, check the memory knob: a small default buffer on a big file spills many temp runs to `/tmp`; raise `-S`, move temporaries with `-T`, and add `--compress-program` if the disk is the bottleneck.

### Q: When do you use -n, -g, -h, and -V — and what does each do with "1024", "1K", "2M"?

`-n` for plain integers/decimals as a prefix parse (stops at the first non-numeric character); `-g` for full floating-point text — exponents, `inf`, `nan`, hex floats — at the cost of long-double conversion; `-h` for 1024-based human suffixes as printed by `du -h` and `ls -lh`; `-V` for version-like strings, comparing digit runs numerically ("a-1.10" after "a-1.2"). For `1024, 1K, 2M`: `-h` orders them correctly (512 < 1024 = 1K < 2M, ties broken by last-resort byte compare); `-n` and `-g` read them as 1024, 1, 2; `-V` treats them as digit/suffix runs and gets a plausible but numeric-unaware order. Only `-h` is correct there.

### Q: How does sort handle a 50 GB file on a 16 GB machine — and what would you tune?

GNU sort is an external merge sort: it fills an in-memory buffer, sorts it, and writes it out as a sorted run; when input ends, it k-way merges all runs. Defaults size the buffer from system memory and run threads per CPU (capped at 8). Tuning: `-S` to spend more RAM (fewer, larger runs), `-T` to point temporaries at the fastest large disk instead of a small `/tmp`, `--compress-program=zstd` to cut run I/O at CPU cost, and `--parallel` to match cores. If inputs are already sorted chunks, skip the sort entirely with `-m`.

### Q: What exactly does sort -u do when combined with -k, and how does that differ from sort | uniq?

`-u` suppresses all but the first line of every run whose *compared keys* are equal — with `-k1,1`, lines `1 a` and `1 b` are "equal" and only the first survives; it is the standard top-1-per-group tool. `sort | uniq` compares whole lines (uniq has no key concept), so it only removes full-line duplicates, and uniq itself can only collapse *adjacent* lines, which is why it requires sorted input. They coincide exactly when the sort key is the whole line; they diverge the moment a `-k` restricts the key. A related trap: `sort -c -u` checks for duplicates (strict order) while plain `sort -c` checks only for disorder.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sort.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
