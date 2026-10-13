# expand — convert tabs to spaces (tabstop-aware)

## Overview

`expand` reads text and replaces each tab character with the right number of spaces to reach the next tab stop — by default every 8th column, or a custom stop list given with `-t`. Its inverse `unexpand` converts runs of spaces back into tabs. Together they arbitrate the oldest formatting war in Unix: tabs or spaces in Makefiles, source code, and data files.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/expand`, from upstream GNU coreutils. The tool is tiny, POSIX-standardized, and decades old, yet it still earns its keep: normalizing pasted code, debugging column alignment in fixed-width reports, and preparing text for tools that measure columns but not tabs (or vice versa).

Common confusions: `expand` is not `tr '\t' ' '` — `tr` replaces one tab with one space and destroys alignment; `expand` preserves the visual column of every following character. It is also not a general reformatter (that is `fmt`) and not a column calculator (that is `column`).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/expand` |
| First appeared / lineage | Unix heritage (POSIX-standardized); GNU coreutils implementation |
| Standards | POSIX.1-2018 (`expand`: `-t`, `-i`) |

## Synopsis

```
expand [OPTION]... [FILE]...
```

Main forms:

```
expand file.txt              # tabs to spaces, stops every 8 columns
expand -t 4 file.txt         # stops every 4 columns
expand -t 1,9,17 src.txt     # explicit stop list
expand -i file.txt           # only leading whitespace
```

With no FILE, or when FILE is `-`, standard input is read.

## How It Works

### Column arithmetic, one character at a time

`expand` walks each line keeping a column counter. A tab is replaced by spaces up to the next tab stop — under the default, the next multiple of 8. All other characters (including backspaces in POSIX's model) advance the counter; bytes are counted as one column each, so multibyte UTF-8 text inflates columns — a legacy behavior worth knowing when aligning non-ASCII data.

```
$ printf 'a\tb\n' | expand | cat -A
a       b$          # 'a' at col 1, tab fills to col 8, 'b' at col 9
$ printf 'a\tb\n' | expand -t 4 | cat -A
a   b$              # tab fills to col 4
```

### Tab stop lists

`-t` accepts a single number (stops every N columns) or a comma/space-separated list of absolute column positions. Two rules matter:

- Positions must be ascending; a value of 0 or a descending list is an error.
- **Tabs beyond the last listed stop expand to a single space** — the list is finite, not repeating:

```
$ printf 'a\tb\tc\td\n' | expand -t 2,5 | cat -A
a b  c d$           # stops at 2 and 5; the last tab becomes ONE space
```

If your data has tabs after the listed region and you need periodic stops thereafter, list enough stops or use a single repeating number instead.

### Leading-only mode

`-i` / `--initial` converts only tabs that appear before the first non-blank character — tabs inside the line survive. This is the safe mode for source code, where interior tabs may be inside string literals or alignment that should not move:

```
$ printf '\tcode\t here\n' | expand -i | cat -A
    code^Ihere$     # leading tab expanded; interior tab untouched
```

### The inverse: unexpand

`unexpand` turns spaces into tabs, but only where the swap is column-preserving. By default it touches only *leading* whitespace (`-i` is its default stance); `-a` extends it to interior runs. A run of spaces becomes a tab only if the run reaches a tab stop:

```
$ printf 'a   b\n' | unexpand -t 4 -a | cat -A
a^Ib$               # 3 spaces reached stop 4 -> one tab
$ printf 'a    b\n' | unexpand -t 4 -a | cat -A
a^I b$              # tab to col 4 + one leftover space
```

```
   tabs (with columns)          spaces
   ┌────────────────────┐  expand   ┌──────────────┐
   │ a^I b^Ic           │ ────────> │ a    b   c   │
   └────────────────────┘  unexpand <──────────────┘
        (-i to restrict to leading whitespace on both sides)
```

## Options That Matter

| Option | Effect |
|---|---|
| `-t, --tabs=N` | Tab stops every N columns (default 8) |
| `-t, --tabs=LIST` | Explicit stop list, e.g. `4,8,16` (ascending; beyond the last stop a tab becomes one space) |
| `-i, --initial` | Convert only leading tabs (before first non-blank) |
| `--tabsize=N` | GNU alias; deprecated spelling of `-t N` |

For `unexpand` the flag set differs: `-a` (convert all whitespace, not just leading), `-t`, `--first-only` (opposite of `-a`).

## Usage Patterns

```bash
# Normalize pasted code that mixes tabs and spaces (leading whitespace only)
expand -i -t 4 messy_script.sh > clean_script.sh
```

```bash
# See what a tab-heavy file really looks like in a fixed-width context
expand -t 8 file.tsv | head
```

```bash
# Make a file safe for a tool that treats tabs as field separators
expand -t 4 config > config.expanded
```

```bash
# 4-column style for Python-ish indentation cleanup
expand -t 4 legacy.py | sed 's/ $//' > legacy.clean.py
```

```bash
# Explicit stops matching a report's column layout
expand -t 10,20,40 report.prn > aligned.txt
```

```bash
# Convert tab-indented YAML to spaces for a linter that forbids tabs
expand -t 2 playbook.yml > playbook.spaces.yml
```

```bash
# Round-trip check: expand then unexpand restores the original columns
expand -t 8 in.txt | unexpand -t 8 -a | cmp - in.txt
```

```bash
# Detect files that still contain tabs (CI lint step)
grep -Pn '\t' file && expand -i -t 4 file
```

```bash
# Convert leading spaces to tabs to shrink a huge indented dataset
unexpand -t 4 -a big_indented.log > compact.log
```

## Nuances and Gotchas

- **`expand` changes bytes, not just appearance.** Any byte-exact process after it (checksums, patches, hashes, string comparisons) sees a different file. Never expand files under version control "for convenience" — diffs explode.
- **Tabs past the last `-t` stop become a single space.** With `-t 2,5`, a tab at column 6+ is one space, not a repeat of the last interval. This silently shifts columns of late-tab lines; prefer `-t N` (repeating) unless you truly want a finite list.
- **Multibyte characters count as one column.** UTF-8 text with accented or CJK characters misaligns under expand's byte-based column counter; alignment of non-ASCII columns needs a locale-aware tool (or `sed`/`perl`).
- **`-i` is the code-safe mode.** Expanding interior tabs can break string literals and column-aligned comments; when cleaning source, use `-i` and handle interior tabs deliberately.
- **`tr '\t' ' '` is the classic mistake.** It replaces every tab with exactly one space, destroying column alignment — the output "looks fine" until anything depends on columns. Say this out loud in interviews; it is a real-world damage report.
- **unexpand's default is leading-only.** People expect `unexpand` to convert every run of spaces; without `-a` it converts only leading whitespace, so interior runs survive. Conversely `-a` can convert alignment spaces inside lines, subtly changing nothing visually (columns preserved) but changing bytes.
- **A tab-stop list must be strictly ascending**; `expand -t 8,4` errors out. Generated stop lists (e.g. from data) need sorting first.
- **Makefiles:** never expand a Makefile — tab indentation is *syntax* to make(1). `expand` on a Makefile is a build-breaking one-liner.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Invalid tab-stop list, unreadable file, or write error |

## Related Commands

- [`fmt`](./fmt.md) — reflows paragraphs; often the next step after de-tabbing.
- [`fold`](./fold.md) — wraps long lines at fixed width; the width logic pairs with expand's columns.
- [`unexpand`](./overview.md) — the inverse tool (spaces to tabs); covered in the collection overview.
- [`cat`](./cat.md) — `cat -A`/`-T` to *see* tabs (`^I`) before deciding what to convert.
- [`sed-awk`](../../shell/sed-awk.md) — regex-driven whitespace normalization beyond fixed tab stops.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: What is the difference between `expand` and `tr '\t' ' '`?

`expand` is column-preserving: it replaces each tab with however many spaces are needed to reach the next tab stop, so text after the tab stays in the same visual column. `tr '\t' ' '` swaps every tab for exactly one space, collapsing alignment — `a<TAB>b` becomes `a b` instead of `a       b`. Any workflow that depends on column position (reports, code comments, diffing aligned data) must use expand.

### Q: Explain the two forms of -t and the behavior past the end of a stop list.

`-t N` sets periodic stops every N columns. `-t LIST` sets absolute positions (must be ascending); once input passes the last listed position, subsequent tabs expand to a single space — the list does not repeat. That asymmetry is a favorite trap: `-t 10,20,40` does not give you stops at 50, 60; it gives single spaces after 40. Use a single N when data extends past your layout.

### Q: Why does expand -i exist, and when would you refuse to use plain expand on a file?

`-i` limits conversion to leading whitespace, which is what you want for source code: interior tabs may live in string literals, regexes, or deliberate column alignment that must not move. Refuse plain expand on Makefiles (tab indentation is syntactic — expansion breaks make), on files under byte-exact comparison or patching, and on data where tabs are field separators (TSV) — expanding them destroys the parseability that the format depends on.

### Q: How would you find and fix tab/space mixing across a repository in CI?

Detect with grep for tab characters (`grep -Pn '\t'` or `git grep -n $'\t'` scoped to sources), fix with `expand -i -t 4` per file (or `unexpand` for tab-style projects), and make the round-trip idempotent in CI (`expand -i -t 4 f | cmp - f`). Mention that style tools (editorconfig, prettier) supersede ad-hoc shell fixes in real projects — the shell one-liners are the diagnosis and escape hatch.

### Q: What happens on `printf 'a\tb\tc\td\n' | expand -t 2,5` and why?

Stops at columns 2 and 5: `a b  c d`. The first tab fills to column 2, the second to column 5, and the third — past the last stop — becomes a single space. The finite-list semantics (single space beyond the end) is the answer being probed; a candidate who expects periodic repetition from the last value describes unexpand's behavior or their own mental model, not expand's.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/expand.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
