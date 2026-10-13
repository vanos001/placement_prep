# join — relational join of two sorted text files

## Overview

`join` is the classic Unix relational operator for flat files: it reads two text
files that are sorted on a common key field and emits one output line for every
pair of input lines whose keys match. Think of it as SQL's `NATURAL JOIN`
implemented as a filter: the key becomes the first output column, followed by
the remaining fields of FILE1, then the remaining fields of FILE2.

It ships in Debian's `coreutils` package, lives at `/usr/bin/join` on modern
Debian/Ubuntu, and is standardized by POSIX, so it is available on every Linux,
BSD, and macOS installation. You reach for it whenever two datasets share a key
(user ID in `/etc/passwd` and `/etc/group`, a request ID in two log extracts, a
SKU in two CSV exports) and the data is already sorted or cheap to sort. It is
often confused with `paste`, which merges files positionally (line 1 with line
1) and ignores keys entirely, and with `comm`, which compares sorted files line
by line instead of field by field.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 (User commands) |
| Path | `/usr/bin/join` |
| First appeared / lineage | Version 7 Unix (1979); GNU rewrite since early GNU times |
| Standards | POSIX.1-2018 |

## Synopsis

```
join [OPTION]... FILE1 FILE2
```

Main forms:

```
join sorted_a.txt sorted_b.txt          # join on field 1 of both files
join -1 2 -2 1 users.txt logins.txt     # key = field 2 of FILE1, field 1 of FILE2
join -a1 -o 1.1,1.2,2.2 -e NA a b       # left outer join, explicit output format
join -t, -o auto a.csv b.csv            # comma-separated files, auto width
```

## How It Works

Because both inputs are sorted, `join` does not need to buffer anything: it
walks both files in lockstep like a merge, advancing whichever file's current
key is smaller. That makes the algorithm linear in the total input size — the
sort you do beforehand is the expensive part, the join itself is O(n + m).

```
        sorted on key            sorted on key
   ┌──────────────────┐     ┌──────────────────┐
   │ a  1             │     │ a  X             │
   │ b  2             │     │ b  Y             │
   │ c  3             │     │ d  Z             │
   └──────────────────┘     └──────────────────┘
            │                        │
            ▼                        ▼
      ┌─────────────  merge on equal keys  ─────────────┐
      │  a 1 X      b 2 Y        (c and d unpairable)   │
      └─────────────────────────────────────────────────┘
```

Key extraction rules matter and trip people up:

```bash
# Default: field 1 of each file, fields delimited by blank runs,
# leading blanks ignored (blank run belongs to the following field)
$ printf 'a 1\nb 2\n' | join <(printf 'a X\nb Y\n') -
a 1 X
b 2 Y

# Default output layout: key, remaining fields of FILE1, remaining fields of FILE2
$ printf 'a 1 2\n' | join <(printf 'a X\n') -
a 1 2 X
```

Pairing with `sort` is the one trap worth memorizing. `join` and `sort` have
different default field models: `sort`'s default key is the whole line, while
`join`'s default key is the first blank-delimited field with leading blanks
ignored. The GNU documentation states the two consistent recipes directly:

```bash
# join with no -t  →  sort with -k1b,1
sort -k1b,1 names.txt > names.s
sort -k1b,1 phones.txt > phones.s
join names.s phones.s

# sort with no -t    →  join with -t ''  (whole line is the key)
sort a.txt | join -t '' - b.txt
# or keep both sides symmetrical:  sort -t$'\t' ... | join -t$'\t' ...
```

If the input is not sorted and some lines fail to pair, `join` warns:

```bash
$ join <(printf 'a 1\nb 2\n') <(printf 'b 1\na 2\n')
join: file 2 is not in sorted order
```

Duplicate keys behave like a SQL join too: every key in FILE1 pairs with every
matching key in FILE2, so m duplicates on one side and n on the other emit m×n
lines.

The `-o` format controls which fields survive, as `FILENUM.FIELD` items or `0`
for the join field, and `-e STRING` fills in a placeholder for fields that are
missing because a line is unpairable:

```bash
$ join -a1 -o 1.1,1.2,2.2 -e NA <(printf 'a 1\nb 2\nc 3\n') <(printf 'a X\nb Y\n')
a 1 X
b 2 Y
c 3 NA
```

`-a1`/`-a2` keep unpairable lines from the given side (outer join); `-v1`/`-v2`
keep *only* unpairable lines (anti-join). `--header` treats the first line of
each file as a header and passes it through unpaired — handy for CSVs.

## Options That Matter

| Option | Effect |
|---|---|
| `-1 FIELD` / `-2 FIELD` | Join on this field of FILE1 / FILE2 (default 1 and 1) |
| `-j FIELD` | Shorthand for `-1 FIELD -2 FIELD` |
| `-t CHAR` | Use CHAR as input *and* output separator; `-t ''` = whole line is the key |
| `-a FILENUM` | Also print unpairable lines from FILE1 (`-a1`) or FILE2 (`-a2`); both allowed |
| `-v FILENUM` | Print only the unpairable lines from FILENUM (suppress joined lines) |
| `-e STRING` | Replace missing (unpairable) fields with STRING — only affects fields named via `-o` |
| `-o FORMAT` | Output format: comma/space list of `0` or `FILENUM.FIELD`; `auto` sizes output per first line |
| `-i` | Ignore case when comparing keys |
| `--header` | First line of each file is a header, printed without pairing |
| `--check-order` | Insist the inputs are sorted even if everything pairs |
| `-z` | NUL-terminated input lines and output fields |

## Usage Patterns

```bash
# Merge a username map into a metrics dump on field 1 (classic two-sorted-files join)
sort -k1b,1 users.txt > users.s
sort -k1b,1 metrics.txt > metrics.s
join users.s metrics.s
```

```bash
# Left outer join: keep all users, NA when no matching group entry exists
join -a1 -e NA -o auto groups.txt memberships.txt
```

```bash
# Anti-join: IDs present in yesterday's export but missing from today's
join -v1 <(sort today.ids) <(sort yesterday.ids)
```

```bash
# CSV-ish files: comma separator, headers passed through untouched
join -t, --header -o auto orders.csv customers.csv
```

```bash
# Join on different field numbers: users keyed by UID in /etc/passwd field 3,
# group file keyed by GID in field 3 — join password entries to their group
join -t: -1 4 -2 3 /etc/passwd /etc/group
```

```bash
# Case-insensitive keys
join -i <(sort -f names.txt) <(sort -f emails.txt)
```

```bash
# Rebuild the join into a specific column order for downstream awk
join -o '1.1 1.3 2.2' a.s b.s | awk '{sum += $3} END {print sum}'
```

```bash
# NUL-safe variant for filenames or arbitrary text
find . -name '*.conf' -print0 | sort -z > confs.z
join -z confs.z owners.z
```

```bash
# Sanity-check pairing before trusting a big join (disorder reports line numbers)
join --check-order big_a.s big_b.s >/dev/null
```

```bash
# Join a file with itself to expand a parent/child table (key = field 2 of FILE2)
join -1 1 -2 2 tree.txt tree.txt
```

## Nuances and Gotchas

- **Both files must be sorted on the join field — under the same collation.**
  Sort one file with `LC_ALL=C` and join under a different locale and keys stop
  matching. Pin `LC_ALL=C sort` for both sides of a join in scripts.
- **The default-field mismatch with `sort`.** `join` ignores leading blanks;
  `sort`'s default key is the whole line. Use `sort -k1b,1` before a default
  `join`, or `join -t ''` after a default `sort`. Mixing the two models
  silently loses pairs.
- **`-e` is narrower than it looks.** It only fills fields that `-o` asked for
  and that are missing on an unpairable line; it does not substitute for empty
  fields that exist in the input. Empty-string keys also never match anything.
- **Duplicate keys produce a cross product.** One stray duplicated ID in a
  million-row file can inflate output by that ID's match count. Dedup first
  (`sort -u` on the key) if you want at most one pair per key.
- **`-t CHAR` changes output too**, not just parsing: output fields are glued
  with the same CHAR. That is usually what you want for CSV/TSV, but it means
  you cannot parse on `\t` while emitting spaces without a post-formatting step.
- **Field numbers are 1-based** and `0` in `-o` means "the join field" — easy
  to mix up when converting an `awk '{print $0}'` habit.
- **Portability:** BSD/macOS `join` lacks `--header`, `--check-order`, and `-o
  auto` (GNU extensions). The POSIX core (`-a`, `-e`, `-j`, `-o`, `-t`, `-1`,
  `-2`) is portable. Busybox `join` is minimal.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Success (all requested pairing done; warnings about disorder still exit 0 unless `--check-order`) |
| 1 | Trouble: I/O error, unsorted input detected with `--check-order`, malformed `-o` format |

## Related Commands

- [`sort`](./sort.md) — join requires sorted input; `sort -k1b,1` is its standard upstream
- [`paste`](./paste.md) — positional column merge with no key concept; the "wrong tool" join is done with
- [`overview`](./overview.md) — the coreutils collection hub: other filters that pair with join
- [`../../shell/sed-awk.md`](../../shell/sed-awk.md) — awk can emulate joins with arrays; useful when files are too dirty for `join`

## Interview Questions

### Q: Why does join demand sorted input, and what is the complexity?

The sorted order lets both files be consumed as streams with a single forward
pass — a merge join. Total work is O(n + m) time and O(longest key run) memory,
versus the hash join O(n + m) memory an awk emulation needs. On files larger
than RAM this is the difference between working and thrashing; the sort that
feeds the join is external and spills to disk in a controlled way.

### Q: You run `sort a.txt | join - b.txt` and get only a few pairs. What is wrong?

The two tools disagree about keys: default `sort` compares whole lines,
default `join` extracts the first blank-delimited field with leading blanks
ignored. Any difference in leading whitespace breaks pairing. Fix by making
the sides symmetric: `sort -k1b,1` upstream of a default `join`, or `join -t
''` to make the whole line the key, or give both tools the same `-t`.

### Q: How do you emulate a LEFT OUTER JOIN with join?

`join -a1 -e NA -o auto file1 file2`. `-a1` emits unpairable FILE1 lines after
the paired ones, `-o auto` pads each such line's missing fields with the `-e`
string so every output line has the same column count. `-a1 -a2` gives a full
outer join, and `-v1`/`-v2` produce the anti-joins (rows with no match).

### Q: What does join do when the same key appears multiple times in both files?

It emits the Cartesian product for that key: m lines on the left and n on the
right yield m·n output lines, just like SQL. Interviewers use this to test
whether you have been bitten by duplicate keys inflating a report — the fix is
deduplicating on the key (`sort -u`) or aggregating duplicates before joining.

### Q: When would you choose join over awk for combining two files?

When the join key logic is exactly "equal fields on sorted input": join is a
battle-tested one-liner with outer/anti-join switches, header support, and
streaming memory behavior. awk wins when keys need normalization (trimming,
case folding beyond `-i`), when you need aggregation during the join, or when
inputs cannot be sorted cheaply. Knowing both and saying *why* is the point.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/join.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
