# uniq — report or filter repeated adjacent lines

## Overview

`uniq` compares **adjacent** lines and collapses, counts, or filters the repeats. Used on a sorted file it produces unique values, duplicate lists, and frequency counts — the standard ingredient of the `sort | uniq -c | sort -rn` top-N idiom that appears in every sysadmin's toolbox. Used deliberately on *unsorted* input it does something nothing else does: squeeze consecutive repeats while preserving the original order (deduplicating a chronological log where only back-to-back retries should collapse).

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/uniq`, from upstream GNU coreutils. It dates to early AT&T UNIX and is POSIX.1-2018-standardized with `-c`, `-d`, `-u`, `-f`, and `-s`; GNU adds `-i`, `-w`, `-z`, `-D`, `--group`, and friends.

The name is the trap: `uniq` does **not** mean "make unique". Without sorting, `a b a` survives untouched because the two `a`s are not adjacent. The entire interview value of this tool hangs on that one sentence — plus the precision field/character-skipping flags that decide *which part* of a line is compared.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/uniq` |
| First appeared / lineage | Early AT&T UNIX (1970s); BSD and GNU reimplementations since |
| Standards | POSIX.1-2018 (`uniq`: `-c`, `-d`, `-u`, `-f`, `-s`); GNU adds `-i`, `-w`, `-z`, `-D`, `--group` |

## Synopsis

```
uniq [OPTION]... [INPUT [OUTPUT]]
```

POSIX style: optional input file first, optional output file second (rarely used; prefer pipes). GNU accepts the usual stdin/file conventions. Main forms:

```
sort data | uniq              # drop adjacent duplicates
sort data | uniq -c           # prefix each line with its count
sort data | uniq -d           # print only lines that repeated (once per group)
sort data | uniq -u           # print only lines that appeared exactly once
uniq -f2 -w8 access.log       # compare an 8-char slice starting after 2 fields
```

With no INPUT, standard input is read; with no OUTPUT, standard output is written.

## How It Works

### Adjacency is the whole model

`uniq` keeps exactly one "current group": it reads a line, compares it to the previous line's comparison key, and either extends the group or flushes it. There is no memory of lines further back:

```
┌─────────────┐   key(line) vs key(prev)?
│ line in     │────────────── equal ──────► grow current group
└─────────────┘        │
                       └── differ ──► flush old group (maybe print)
                                       start new group
```

Consequences, all verified:

```
$ printf 'a\nb\na\nc\na\n' | uniq -c     # three 'a's, none adjacent
      1 a
      1 b
      1 a
      1 c
      1 a
$ printf 'a\nb\na\nc\na\n' | sort | uniq -c
      3 a                                # sort first → adjacency achieved
      1 b
      1 c
```

This is why the canonical pipeline is `sort ... | uniq ...` — and why the alternative, `sort -u`, usually replaces the pair entirely (see below).

### The comparison key: fields, then characters

By default the *entire line* (newline excluded) is compared. `-f`, `-s`, and `-w` carve a smaller key out of each line, applied in a fixed order:

1. `-f N` — skip the first N **fields**, where a field is a maximal run of non-blank characters and blanks are spaces/tabs (runs of blanks act as one separator; leading blanks belong to the field being skipped).
2. `-s N` — then skip N more **characters**.
3. `-w N` — then compare **at most N characters** of what remains.

```
$ printf 'a b\na c\nb c\n' | uniq -f1 -c     # key = everything after field 1
      1 a b
      2 a c                                  # 'a c' and 'b c' share key 'c'
$ printf 'xx12\nyy12\nzz\n' | uniq -s2 -c    # key = from char 3 on
      2 xx12                                 # xx12/yy12 share key '12'
      1 zz
$ printf 'aaa\naab\naac\n' | uniq -s1 -w2 -c # skip 1, compare 2
      1 aaa                                  # keys aa/ab/ac → all distinct
      1 aab
      1 aac
```

Two sharp edges in the field model, both real:

```
$ printf '  apple\n  apricot\nx apple\n' | uniq -f1 -c
      2   apple                # leading blanks swallowed with field 1:
      1 x apple                # '  apple' → key '' ; 'x apple' → key ' apple'
```

After `-f1`, `  apple` and `  apricot` both reduce to an *empty* key — the skipped field consumed the words too — so they compare equal. And whatever was skipped is still *printed*: output shows the group's first line verbatim, spaces and all. Counting says what matched; the text says what was printed.

### Output modes

The flags select what gets flushed per group; they combine freely:

```
$ printf 'a\na\nb\nb\nb\nc\n' | uniq -c       # count prefix (right-aligned)
      2 a
      3 b
      1 c
$ printf 'a\na\nb\nb\nb\nc\n' | uniq -d       # duplicated groups only
a
b
$ printf 'a\na\nb\nb\nb\nc\n' | uniq -u       # singleton groups only
c
$ printf 'a\na\nb\nb\nb\nc\n' | uniq -D       # every line of dup groups
a
a
b
b
b
```

`--group[=separate|prepend|append|both]` (GNU) adds blank-line separators for human reading; `--all-repeated[=none|prepend|separate]` is `-D` with optional blank-line padding. `-i` folds case in the comparison (`A` matches `a` — the printed line is still the first occurrence's spelling), and `-z` switches input to NUL-separated records for `find -print0`/`grep -Z` pipelines.

### sort | uniq vs sort -u

For plain deduplication, `sort -u` is equivalent and cheaper — one process, single pass, no intermediate stream:

```
$ printf 'b\na\nB\na\n' | LC_ALL=C sort | uniq -u
B
b                          # B < a < b in byte order; 'a' deduped
$ printf 'b\na\nB\na\n' | LC_ALL=C sort -u
B
b                          # identical result, same comparison rules
```

`uniq` stays on the table for three reasons: `-c` counts (sort -u cannot count), `-d`/`-u` filtering (which sort cannot express), and pipelines where the input is *already* adjacent-grouped without a full sort. There is also a subtle efficiency point: `sort | uniq` sorts the whole stream then walks it again; `sort -u` dedupes inside the sort's merge passes and uses less I/O on huge inputs.

## Options That Matter

| Option | Effect |
|---|---|
| `-c, --count` | Prefix each output line with the group's occurrence count, right-aligned in a padded column |
| `-d, --repeated` | Print one line per group that occurred 2+ times (first line of the group) |
| `-D, --all-repeated[=METHOD]` | Print *all* lines of duplicated groups (GNU; METHOD adds blank-line separators) |
| `-u, --unique` | Print only groups that occurred exactly once |
| `-i, --ignore-case` | Case-insensitive comparison (locale-aware folding) |
| `-f N, --skip-fields=N` | Skip the first N blank-separated fields before comparing |
| `-s N, --skip-chars=N` | Additionally skip N characters after field skipping |
| `-w N, --check-chars=N` | Compare no more than N characters of the remainder (GNU) |
| `-z, --zero-terminated` | Lines end with NUL, not newline (GNU; pairs with `find -print0`) |
| `--group[=METHOD]` | Separate groups with blank lines for readability (GNU) |

POSIX guarantees `-c -d -u -f -s` only. `-i` exists on GNU *and* the BSDs but is not in POSIX; `-w`, `-z`, `-D`, and `--group` are GNU — macOS/BSD `uniq` has no `-w`.

## Usage Patterns

```bash
# Frequency ranking: the workhorse pipeline
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head
```

```bash
# How many distinct values?
cut -d: -f7 /etc/passwd | sort | uniq | wc -l
```

```bash
# Which shells are actually in use? (counts + labels)
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn
```

```bash
# Lines that appear in a file more than once (duplicates, sorted input)
LC_ALL=C sort names.txt | uniq -d
```

```bash
# Strictly-unique lines only (anything repeated is noise)
LC_ALL=C sort words.txt | uniq -u > singles.txt
```

```bash
# Collapse back-to-back duplicate log lines but keep chronological order
uniq app.log > squeezed.log
```

```bash
# Case-insensitive dedup of sorted input (print first spelling seen)
LC_ALL=C sort tags.txt | uniq -i
```

```bash
# Ignore the changing timestamp: dedupe log lines by their message
uniq -f3 syslog.err                          # fields: MON DAY TIME MSG...
```

```bash
# Compare only the user column (first 8 chars after the host field)
last -n 50 | uniq -f2 -w8 -c
```

```bash
# NUL-safe dedup of filenames
find . -name '*.log' -print0 | sort -z | uniq -z | xargs -0 rm -v
```

```bash
# Grouped report with blank lines for humans
cut -d: -f1 /etc/group | sort | uniq --group
```

```bash
# Sanity check: count of counted lines equals distinct value count
sort -u data.txt | wc -l                     # equals: sort data.txt | uniq | wc -l
```

## Nuances and Gotchas

- **Adjacent-only, always.** `uniq` never scans backwards; unsorted repeats pass through untouched. Any pipeline that "deduplicated" without a sort silently didn't. If output order must be preserved *and* full dedup is needed, that is `awk '!seen[$0]++'`, not `uniq`.
- **Comparison key ≠ printed text.** With `-f`/`-s`/`-w`, the skipped parts still appear in the output (first line of each group, verbatim). Two visually different lines can merge (`-i`, `-w`) or two visually similar lines can stay apart (trailing whitespace, CR).
- **CRLF files split groups.** `a\r` and `a` are different keys — files edited on Windows produce phantom "duplicates". `dos2unix` or `tr -d '\r'` before `uniq`; with `-c` the count halves and the lines list doubles.
- **`-f` fields are blank-delimited, and leading blanks attach to the skipped field.** GNU's rule (field = blanks + non-blanks) means `-f1` on `  apple` consumes the word, leaving an empty key — single-field lines then all compare equal. Don't use `-f` to "skip an indent"; that's `-s`'s job.
- **`-s` has no field awareness.** It counts characters (GNU uniq decodes multibyte characters under UTF-8 locales; historical/BusyBox builds count bytes) — don't ship `-s` against non-ASCII data in portable scripts.
- **The count column's width is variable.** `-c` pads to 7 by default and grows for larger counts — downstream `cut -c`-style parsers break; use `awk '{print $1, $2}'` to re-shape reliably.
- **`sort -u` vs `sort | uniq`:** same result set under the same locale rules, one process less. Reach for `uniq` only when you need counts (`-c`), duplicate/singleton selection (`-d`/`-u`/`-D`), or order-preserving adjacent squeezing. Conversely `uniq -c | sort -rn | head` has no sort-only equivalent.
- **Locale determines equality and order.** Under a UTF-8 locale, `sort` (and thus adjacency) uses collation rules where case and accents fold; under `LC_ALL=C`, byte order. The `sort` and `uniq` stages must share the locale — exporting `LC_ALL=C` for the whole pipeline is the deterministic convention (and matches `comm`'s requirements).
- **POSIX operand order:** `uniq in out` writes filtered output to `out` — easy to misread as a second input file. Prefer explicit redirection; it's also the only operand form BusyBox supports fully.
- **Exit-status quirk:** GNU `uniq` exits 0 even when nothing printed; there is no "found duplicates" status. Detecting duplicates requires inspecting output, not `$?`.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Input processed (whether or not any output was produced) |
| 1 | Usage error (bad option, missing argument) or unreadable input |

## Related Commands

- [`sort`](./sort.md) — the prerequisite: `uniq` is nearly meaningless without adjacency; `sort -u` is the one-process dedup.
- [`comm`](./comm.md) — set operations on two *sorted* files; consumes the same sorted-input discipline.
- [`cut`](./cut.md) — extracts the field that `uniq -c` should count.
- [`paste`](./paste.md) — recombines counted columns after `uniq -c`.
- [`grep`](../../shell/grep.md) — content *selection* by pattern; uniq does repetition, grep does matching.
- [`cat`](./cat.md) — and its `-s` flag, the special case "squeeze repeated blank lines".
- [`overview`](./overview.md) — GNU Coreutils collection hub.
- [Regex](../../shell/regex.md) — when dedup needs normalization first, awk/sed with regex do the reshaping.

## Interview Questions

### Q: Why does `uniq` fail to deduplicate an unsorted file, and what are your options when sort order must be preserved?

`uniq`'s algorithm keeps only the current run: each line is compared solely to its predecessor, so non-adjacent repeats are independent groups and survive. That's why the standard pipeline sorts first. When sorted order is unacceptable (chronological logs, first-appearance order), `uniq` cannot do the job — use `awk '!seen[$0]++'`, which hashes every line ever seen, or `sort -u` if order can be defined by the sort itself. The honest design statement: `uniq` is an *adjacency compressor*, and deduplication is only its most common application.

### Q: When is `sort | uniq` actually better than `sort -u`?

Three cases: counting (`sort -u` has no equivalent of `-c`, and the frequency-rank pipeline `sort | uniq -c | sort -rn` is built on it), selection (`-d` lists duplicated lines, `-u` isolates singletons, `-D` prints full duplicate groups — none expressible in sort), and pipelines where input is *already* grouped without sorting. Otherwise `sort -u` wins: one process, one pass, and on very large inputs it dedupes during the merge phase instead of re-reading the sorted stream. Knowing *both* directions of the trade-off is the point of the question.

### Q: `uniq -f1` on a file of single-word lines collapses everything into one group. Why?

GNU's field model: a field is blanks-then-non-blanks, and the skip consumes both. For a line like `  apple`, `-f1` skips the leading blanks *and* the word, leaving an empty comparison key — every single-field line becomes equal. For `x apple`, the key is ` apple` (different). The lesson generalizes: `-f`/`-s`/`-w` define a comparison key, not an extraction; verify with `uniq -c` on a sample, and do "compare column N" with `cut`/`awk` upstream instead (`cut -d' ' -f1 | sort | uniq -c`), which makes the key explicit and testable.

### Q: Explain the difference between `-d`, `-D`, `-u`, and `--group`.

Per group (runs of adjacent equal lines): `-d` prints one line per duplicated group (count ≥ 2, printed once); `-D` prints *every* line of duplicated groups; `-u` prints one line per singleton group (count exactly 1); `--group` prints all groups with blank-line separators, filtering nothing — a formatting mode for reports. They compose with `-c` (counting) and the key-carving flags. A classic mapping: `-d` answers "which values repeat?", `-D` answers "show me the evidence", `-u` answers "which values are unique?" — three different questions people conflate.

### Q: A colleague runs `uniq -c userlist.txt | sort -rn | head` and gets wrong-looking rankings. Name the likely defects.

First, no sort before uniq: unless userlist happens to be grouped, counts are fragmentary — the dominant defect. Second, locale mismatch: without `LC_ALL=C`, sort's collation and uniq's equality follow locale rules; deterministic byte-order pipelines export `LC_ALL=C` across all stages (and `comm` would require it anyway). Third, if userlist has Windows line endings, `\r` taints every key and splits identical names into separate groups. Fourth, `-c`'s padded count column breaks `cut -c`-style parsers; parse with `awk`. The headline answer is the missing adjacency sort; the rest separates the careful from the casual.

### Q: Which uniq options are POSIX, and which GNU/BSD extensions would break a portable script?

POSIX.1-2018 fixes `-c`, `-d`, `-u`, `-f N`, `-s N` plus the two-operand input/output form. GNU additions: `-i` (also present on the BSDs, but not POSIX), `-w N` (GNU only — absent on macOS and FreeBSD), `-z` NUL records, `-D`, `--all-repeated`, `--group`, and the long option names. BusyBox covers a subset of the POSIX set. A portable dedup script sticks to `sort | uniq -d`-level features; anything needing `-w` should be expressed with `cut`/`awk` preprocessing instead, which also makes the comparison key explicit and testable.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/uniq.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
