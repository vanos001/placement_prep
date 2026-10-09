# comm — compare two sorted files line by line (three-column set difference)

## Overview

`comm` reads two text files that are both sorted (with `LC_COLLATE`-consistent collation, e.g. via `sort`) and prints their lines arranged in three columns:

- column 1 — lines unique to FILE1,
- column 2 — lines unique to FILE2,
- column 3 — lines common to both.

Suppressing columns with `-1`, `-2`, `-3` turns it into a set calculator: intersection (`-12`), difference (`-23`), symmetric difference (no flags). It is the line-oriented, exact-membership cousin of `diff` (which reports *how* lines differ, with edit context) and `grep -Fxf` (which checks set membership against a pattern file).

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/comm`, from upstream GNU coreutils. It is ancient — present since early Unix precisely because sorted tape files made column suppression cheap — and it remains the cleanest tool for "which user IDs are in group A but not group B" style questions.

Common confusions: using it on unsorted input (garbage out, plus in modern coreutils a diagnostic and exit 1), confusing its columns with diff's markers, and forgetting that "sorted" means the same collation `comm` uses — which is why `LC_ALL=C sort` on both inputs is the standard belt-and-braces pattern.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/comm` |
| First appeared / lineage | Early Unix (Version 1 era); a fixture of every Unix since |
| Standards | POSIX.1-2018 (`comm`) |

## Synopsis

```
comm [OPTION]... FILE1 FILE2
```

Main forms:

```
comm -12 a.txt b.txt      # intersection: lines in both
comm -23 a.txt b.txt      # lines only in a.txt
comm -13 a.txt b.txt      # lines only in b.txt
comm a.txt b.txt          # all three columns, tab-separated
```

Either FILE can be `-` (standard input), but only one of them.

## How It Works

### A two-pointer merge

`comm` walks both files simultaneously with one read position per file, comparing the current lines with the same collation `sort` used. At each step:

```
             FILE1 pointer                FILE2 pointer
                 │                            │
                 v                            v
   line1 < line2 ?  emit line1 -> col 1, advance FILE1
   line1 > line2 ?  emit line2 -> col 2, advance FILE2
   line1 = line2 ?  emit line  -> col 3, advance BOTH
```

This is a linear merge — O(n+m) — which is why sorted input is not just a suggestion: the algorithm *is* the sortedness. Duplicates within a file are handled by counting: if a line appears twice in FILE1 and once in FILE2, the extra copy is emitted in column 1.

### The three-column layout

Output is tab-separated; absent columns render as empty fields, so the eye can read membership directly:

```
$ printf 'apple\nbanana\ncherry\n' > f1
$ printf 'apple\ndate\nbanana\n' | sort > f2
$ comm f1 f2
		date
apple		banana
	cherry
```

Reading it: `date` only in f2 (col 2), `apple` in both (col 3), `banana` in both, `cherry` only in f1 (col 1). The tab padding makes this confusing until you internalize the column positions — which is exactly what the suppress flags are for.

```
$ comm -12 f1 f2          # intersection
apple
banana
$ comm -23 f1 f2          # only in f1
cherry
$ comm -13 f1 f2          # only in f2
date
```

### Sortedness and modern diagnostics

In recent GNU coreutils, `comm` checks its inputs' ordering and, on a violation, prints diagnostics like `file 1 is not in sorted order` to stderr, exits nonzero, and the output is not trustworthy. `--nocheck-order` restores the historical lenient behavior (silent, possibly wrong output); `--check-order` is the explicit form. Either way the fix is the same: sort both inputs with a collation that matches the comparison — the portable idiom is:

```
$ comm -12 <(LC_ALL=C sort a.txt) <(LC_ALL=C sort b.txt)
```

`LC_ALL=C` matters: under a UTF-8 locale, `sort` and `comm` may agree with each other but disagree with scripts hard-coded to byte order (or vice versa). Pinning the locale on *both* sides of the pipeline is what makes the trick deterministic.

## Options That Matter

| Option | Effect |
|---|---|
| `-1` | Suppress column 1 (lines unique to FILE1) |
| `-2` | Suppress column 2 (lines unique to FILE2) |
| `-3` | Suppress column 3 (lines common to both) |
| `--check-order` | Explicitly demand sorted input (default behavior in recent coreutils) |
| `--nocheck-order` | Skip the sortedness check; output undefined on unsorted input |
| `--total` | Print a summary line with counts per column (GNU extension) |
| `-z`, `--zero` | NUL-terminate output lines instead of newline |

Combinations to memorize: `-12` = intersection, `-23` = FILE1 minus FILE2, `-13` = FILE2 minus FILE1, no flags = symmetric difference (in three labeled groups).

## Usage Patterns

```bash
# Which packages are installed here but not on the reference host?
comm -23 <(dpkg --get-selections | awk '{print $1}' | sort) \
         <(ssh ref dpkg --get-selections | awk '{print $1}' | sort)
```

```bash
# Common members of two lists (intersection)
comm -12 <(sort team-a.txt) <(sort team-b.txt)
```

```bash
# Users in /etc/passwd missing from the LDAP export
comm -23 <(cut -d: -f1 /etc/passwd | LC_ALL=C sort) <(LC_ALL=C sort ldap-users.txt)
```

```bash
# Lines that changed membership either way (symmetric difference)
comm <(LC_ALL=C sort old.txt) <(LC_ALL=C sort new.txt)
```

```bash
# Sanity-check that two sorted files are identical as sets (empty output = same)
comm -3 <(LC_ALL=C sort a) <(LC_ALL=C sort b)
```

```bash
# Count how many entries the two lists share
comm -12 <(LC_ALL=C sort a.txt) <(LC_ALL=C sort b.txt) | wc -l
```

```bash
# Process-name diff after an upgrade
ps -eo comm | LC_ALL=C sort -u > now.txt
comm -23 before.txt now.txt    # processes that disappeared
```

```bash
# NUL-safe variant for filenames from find
comm -z <(find dir1 -type f -printf '%f\0' | LC_ALL=C sort -z) \
        <(find dir2 -type f -printf '%f\0' | LC_ALL=C sort -z)
```

```bash
# Summary counts per column (GNU extension)
comm --total <(LC_ALL=C sort a) <(LC_ALL=C sort b) | tail -1
```

## Nuances and Gotchas

- **Unsorted input is the #1 failure mode.** In recent coreutils it produces stderr diagnostics and a nonzero exit; under `--nocheck-order` it silently produces wrong columns. Always `sort` both sides, in the same locale, immediately before `comm`.
- **"Sorted" is collation-dependent.** `sort` under `en_US.UTF-8` ignores punctuation differently than under `C`. If the inputs were sorted in one locale and comm runs in another, valid-looking input is "out of order". Pin `LC_ALL=C` (or `sort -z` for NUL) on both ends.
- **Trailing newlines and trailing whitespace count.** A file whose last line lacks `\n`, or lines with trailing spaces/CR (Windows files!), are different strings to `comm`. `cat -A` or `sed 's/\r$//'` first when mixing sources.
- **Duplicates are counted, not deduplicated.** `comm -12` prints a line twice if it occurs twice in both files. `sort -u` both inputs if you want set semantics; keep duplicates if you want multiset (counting) semantics.
- **Only one operand may be `-`.** `comm -12 <(cmd1) <(cmd2)` via process substitution is the idiomatic workaround for streams; it also avoids temp files.
- **Column output confuses copy-paste.** The tabs are literal; scripts that parse raw three-column output should use the suppress flags instead of cutting by field number.
- **`comm` compares whole lines, not fields.** For "same value in column 3 of CSVs", extract the field first (`cut -d, -f3 | sort`), then compare — or move to `join`, which matches on a key field.
- **Exit status:** modern GNU `comm` exits 1 when the order check fails — scripts that treat nonzero as "no common lines" conflate a data property with an input error.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Both files processed (order valid when checking is on) |
| 1 | Input failed the sortedness check (recent coreutils), or an I/O error occurred |

## Related Commands

- [`cut`](./cut.md) — field extraction; typical upstream of `comm` when comparing one column of structured files.
- [`diff`](./overview.md) — line-by-line edit report with context, when you need *how* files differ rather than set membership.
- [`join`](./overview.md) — relational join of two sorted files on a common field (see the collection overview).
- [`sort`](./overview.md) — mandatory preprocessing partner; collation must match comm's comparison.
- [`grep`](../../shell/grep.md) — `grep -Fxf patterns.txt` answers "lines of file X that appear in the pattern file" with unsorted input, at higher cost.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why does comm require sorted input, unlike diff?

`comm` implements a linear two-pointer merge whose correctness depends entirely on order — it never looks back, giving O(n+m) time and constant memory, which mattered for tape-era files and still matters for multi-GB lists. `diff` computes a full edit-distance-style alignment (approximate LCS), which needs arbitrary lookahead and more memory but tolerates any input. Sortedness is not a requirement bolted on; it is the algorithmic assumption that makes comm cheap.

### Q: Explain what `comm -23 a b` and `comm -13 a b` compute and why the two together reconstruct the difference.

`-23` suppresses the b-only and common columns, leaving lines only in a (a minus b). `-13` leaves lines only in b (b minus a). Together they form the symmetric difference, split by side; with no flags, comm shows all three groups in columns 1, 2, 3. The flag numbers literally name the columns to suppress, so reading any comm invocation aloud starts from "which columns remain".

### Q: A script's comm output is correct on one server and wrong on another. The command includes `sort` on both inputs. Diagnose.

Locale drift. `sort` and `comm` both use the current collation; if one host sorts under `en_US.UTF-8` and the other under `C`, the byte order of the two inputs differs from the order comm's comparison expects, tripping the order check or silently misplacing lines. Pin the locale explicitly on both sides: `LC_ALL=C sort` feeding `LC_ALL=C comm` (or make both use the same UTF-8 collation). Also check for CR-LF inputs — `\r` changes every line's value.

### Q: How do duplicates interact with comm, and how do you force pure set behavior?

comm counts duplicates: a line appearing twice in FILE1 and once in FILE2 yields one common-column line plus one column-1 line. For pure set semantics, `sort -u` both inputs first (or `awk '!seen[$0]++'` when re-sorting is undesirable). Keeping duplicates gives multiset semantics, occasionally wanted for count reconciliation — knowing the difference is the point of the question.

### Q: When is `grep -Fxf` preferable to `comm`, and when is comm preferable?

`grep -Fxf patterns.txt file` reports lines of file matching any fixed string from the pattern file — no sortedness needed, works on streams, but costs a full scan per line (hash-optimized in GNU grep, still O(n·m) worst case, and it deduplicates nothing about order). `comm` needs both inputs sorted but runs in linear time and gives you the three-way membership (only-a, only-b, both) in one pass. Large sorted datasets → comm; small unsorted streams or when only intersection matters → grep -Fxf.

### Q: What does `comm --total` add, and give a use case.

It appends a summary line with the number of lines in each column and a total — turning comm into a reconciliation report in one invocation. For example, comparing yesterday's and today's package lists: the total line instantly answers "how many packages were added, removed, and unchanged" without piping each column through `wc -l` separately.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/comm.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
