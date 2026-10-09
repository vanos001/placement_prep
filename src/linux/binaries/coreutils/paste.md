# paste — merge lines of files side by side

## Overview

`paste` merges files horizontally: it takes line N from each input file,
glues them with a delimiter (TAB by default), and emits the result as one
line. Where `join` is relational and requires sorted keys, `paste` is purely
positional — line 1 pairs with line 1 because it is line 1, nothing more. It
also has a second personality: `-s` (serial) concatenates *all* lines of one
file into a single line, turning a column into a row.

It ships in Debian's `coreutils` package at `/usr/bin/paste` and is a
POSIX-standard tool from the Version 7 era. You reach for it to build TSV
output from parallel streams, to interleave command outputs for comparison,
to serialize a column for `xargs`-style consumption, or to pair up lines for
further processing. It is often confused with `join` (key-based, sorted,
different tool entirely) and with `cat`, which concatenates files *vertically*
while `paste` does it *horizontally*.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 (User commands) |
| Path | `/usr/bin/paste` |
| First appeared / lineage | Version 7 Unix (1979) |
| Standards | POSIX.1-2018 |

## Synopsis

```
paste [OPTION]... [FILE]...
```

Main forms:

```
paste names.txt phones.txt        # parallel merge, TAB-separated columns
paste -d, a.csv b.csv             # same, comma-separated
paste -sd+ numbers.txt            # serial mode: whole file on one line
seq 5 | paste - -                 # pair up lines from one stream
```

## How It Works

In the default parallel mode, `paste` opens every file and copies line by
line, inserting a delimiter after each file's field — including after the
last column. A shorter input simply stops contributing, and its column
position becomes empty (the delimiter is still written, so columns stay
aligned):

```
   file A          file B          paste A B
   a        ┐      1        ┐      a TAB 1
   b        │      2        │      b TAB 2
   c        │               ┘      c TAB
            ┘
```

Verified behavior, including the trailing tab on the short side:

```bash
$ printf 'a\nb\nc\n' > A; printf '1\n2\n' > B; paste A B | cat -A
a^I1$
b^I2$
c^I$
```

The delimiter list in `-d` is a cycle: with more files than delimiters, the
list repeats; with one file, the list cycles across successive lines.

```bash
$ printf 'a\nb\nc\n' > A; paste -d',|' A A A | cat -A
a,1|a$
b,2|b$
c,3|c$
```

Two delimiters are special: an empty list (`-d ''`) means "no delimiter at
all" (columns are glued), and `\0` (backslash-zero) inside the list also
means the empty string — the POSIX way to write "no separator", since a
literal NUL cannot appear in a shell argument:

```bash
$ printf 'a\nb\nc\n' | paste -sd'\0' - | cat -A
abc$
$ printf 'a\nb\nc\n' | paste -d '' A B | cat -A
a1$
b2$
c$
```

In serial mode (`-s`), each *file* becomes one output line: its lines are
joined with cycling delimiters, and no delimiter follows the last line:

```bash
$ printf 'x\ny\nz\n' | paste -sd':;:' -
x:y;z
```

The `-` operand reads standard input in the file list, and can appear more
than once — `paste - -` splits one stream into two columns:

```bash
$ seq 1 5 | paste - -
1       2
3       4
5
```

`paste` never buffers a whole file (parallel mode walks all inputs
simultaneously), so it is safe on large inputs — but see the FIFO caveat
below for multiple `-` streams.

## Options That Matter

| Option | Effect |
|---|---|
| `-d LIST` | Delimiter cycle instead of TAB; `\n` `\t` `\\` `\0` escapes recognized; empty item = no separator |
| `-s` | Serial mode: paste all lines of each file into one line, one file per output line |
| `-z` | NUL instead of newline as the line terminator (GNU) |

## Usage Patterns

```bash
# Build a TSV from two generated lists (usernames + generated passwords)
paste <(pwgen-style-list) <(awk '{print $1}' users.txt) > initial_creds.tsv
```

```bash
# Serialize a column into a comma list for an IN clause
cut -d: -f1 /etc/passwd | paste -sd,
```

```bash
# Sum a column of numbers with bc, thanks to serial mode
paste -sd+ prices.txt | bc
```

```bash
# Pair lines for diffing: even/odd split via double stdin
paste - - < request_log | awk -F'\t' '$1 != $2'
```

```bash
# Side-by-side compare of sorted outputs before reaching for diff
paste <(ls dir_a) <(ls dir_b) | grep -vP '^(.*)\t\1$'
```

```bash
# Pad a single-column file into a two-column layout (classic /dev/null trick)
paste notes.txt /dev/null
```

```bash
# Turn a word-per-line list back into one space-separated line
tr ' ' '\n' < phrase | paste -sd ' ' -
```

```bash
# Cycle separators across three columns: comma, then pipe, then comma again
paste -d',|' probe1 probe2 probe3 | head
```

```bash
# NUL-safe pairing for filenames (GNU)
find . -name '*.png' -print0 | paste -z -d ' ' - -
```

```bash
# Merge pre-sorted key/value streams positionally for eyeballing (NOT for logic)
paste <(sort keys.txt) <(sort values.txt) | less
```

## Nuances and Gotchas

- **Positional, not relational.** Any reordering upstream (a parallel `sort`,
  an async producer) breaks the row alignment silently. If correctness
  depends on keys, you want `join`, not `paste`.
- **Every line gets a trailing delimiter** in parallel mode — even when the
  other file already ended. Downstream CSV parsers will see an empty last
  field; strip with `sed 's/\t$//'` or accept it.
- **`-d LIST` cycles also in serial mode**, and the cycle position carries
  across the whole line, not per file. Count your list length if delimiters
  must be positional.
- **Empty delimiters:** `-d ''` and `-d '\0'` both mean *no* delimiter —
  there is no way to pass a real NUL byte as a separator via `-d` (use `-z`
  to change the line terminator instead).
- **Every `-` operand is the same stream.** `paste - -` alternates lines from
  one stdin into two columns; you cannot attach two different pipes to two
  dashes. For genuinely independent live streams, use FIFOs or
  process-substitution files as the operands.
- **Not byte-column aware.** Tabs in the *input* are just data; `paste` never
  aligns columns visually. For display alignment, pipe through `column -t`
  or `pr -T`.
- **Portability:** `-d`, `-s`, and `-` are POSIX; `-z` is a GNU extension
  missing on BSD/macOS. Busybox `paste` covers the core.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Trouble: unreadable input file |

## Related Commands

- [`join`](./join.md) — the relational sibling: merge on a sorted key instead of line position
- [`pr`](./pr.md) — paginated multi-column layout for print, not data merging
- [`split`](./split.md) — the inverse operation: one file into many, positionally
- [`overview`](./overview.md) — the coreutils collection hub
- [`../../shell/xargs.md`](../../shell/xargs.md) — serial mode often feeds xargs-style batch building

## Interview Questions

### Q: What is the difference between paste and join?

`paste` merges positionally — line N of every input becomes output line N,
no keys, no sorting, no matching. `join` requires both inputs sorted on a
common key and emits only matching pairs (plus optional unpaired lines).
Quick heuristic: "same line number" → paste; "same ID" → join.

### Q: How does the -d delimiter list behave when it runs out of characters?

It cycles. With three files and `-d',|'` the separators are comma, pipe,
comma, pipe... — and with a single file in serial mode, the list walks
character by character along the line. Special items: `\\` is a literal
backslash, `\n`/`\t` are newline/tab, and `\0` (or an empty list) means an
empty separator, which is how you glue columns with nothing between them.

### Q: Why does paste output a trailing tab after the last column, and when does it matter?

In parallel mode `paste` writes a delimiter after every file's field,
including the final one; when another input has already run dry the line ends
with the delimiter and an empty field. It matters for CSV consumers that
reject ragged rows and for byte-exact regression tests. The behavior is
POSIX-specified, so the fix is normalization downstream, not flags.

### Q: How would you turn a one-column file into a comma-separated single line?

`paste -sd, file`. Serial mode concatenates all lines of the file, joining
with the delimiter cycle, with no trailing delimiter. It composes well:
`cut -d: -f1 /etc/passwd | paste -sd,` produces a comma list of usernames,
and `paste -sd+ | bc` sums a column without an awk script.

### Q: What is the classic use of /dev/null with paste?

`paste file /dev/null` appends an empty second column to every line (the
trailing-tab behavior puts the delimiter there), which is a quick way to
reserve a column for later filling. Conversely, `paste - file` merges a
stream alongside a file without touching the file's order — reading stdin in
the middle of an operand list is the other classic trick.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/paste.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
