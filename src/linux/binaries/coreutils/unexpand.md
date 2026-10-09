# unexpand — Convert spaces to tabs

## Overview

`unexpand` rewrites runs of blanks into tab characters, compressing text toward a tab-stop grid. It is the mirror image of [`expand`](./expand.md) (tabs → spaces): `expand` normalizes text for display and tools that assume columns, `unexpand` compresses it back toward the compact canonical form editors and old printers assumed. Despite the odd name — it "un-expands" tabs — the direction is always *spaces in the file become tabs in the output*.

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/unexpand`. It is a genuine Unix fossil — `expand`/`unexpand` predate POSIX by years and are both POSIX-standardized today — so it behaves identically on GNU, busybox and BSD systems for the common flags.

When do you actually reach for it? Three real occasions: (1) normalizing files whose convention is tab-indented — most famously **Makefile recipes, where the POSIX grammar *requires* a literal tab** and pasted-from-web spaces are the classic build failure; (2) shrinking whitespace-heavy text (logs with aligned columns, TSV-ish output) toward the tab-stop economy the original writers intended; (3) reversing a careless `expand` pass that destroyed someone's tabs. It is often confused with `sed 's/  +/\t/g'`-style one-liners (which ignore tab stops) and with editor "retab" functions (which `unexpand -a` mimics, defaulting to 8-column stops).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/unexpand` |
| First appeared / lineage | Early Unix text tooling (with `expand`); long POSIX-standardized |
| Standards | POSIX |

## Synopsis

```
unexpand [OPTION]... [FILE]...
```

```bash
unexpand file                    # compress leading blanks to tabs (8-col stops)
unexpand -a file                 # compress ALL blanks, not just leading runs
unexpand -t 4 file               # 4-column tab stops (implies -a)
unexpand --first-only -a file    # force leading-runs-only despite -a
```

With no `FILE`, or when `FILE` is `-`, standard input is read. Output goes to standard output; files are never edited in place — redirect if you mean to replace.

## How It Works

### The tab-stop column model

Everything `unexpand` does follows from one rule: a tab character advances the output column to the **next tab stop** (every 8 columns by default; configurable with `-t`). Converting a run of spaces into a tab is only done when the tab lands the following character at the *same or earlier* column than the spaces did — `unexpand` never widens text. The mechanics on an 8-column grid:

```
input:    x        y          (x at col 0, 8 spaces, y at col 9)
stops:    0123456789
                   ├── next stop after col 1 is col 8
output:   x⇥ y                (tab advances to col 8, +1 space, y at col 9 — same y, fewer bytes)
```

A run that does not reach a tab stop stays untouched:

```bash
$ printf ' a\n    a\n        a\n' | unexpand | cat -A
 a$
    a$
^Ia$
```

One space and four spaces don't reach column 8, so only the eight-space run compresses to `⇥a`. This "only convert when it shortens" discipline is the difference between `unexpand` and a blind regex.

### Default mode: leading blanks only

Without flags, `unexpand` converts only *initial* blank runs on each line — precisely the use case of indentation. Interior alignment (the padding between columns of a table) is left alone:

```bash
$ printf '        a\nx        y\n' | unexpand | cat -A
^Ia$
x        y$
```

This conservative default exists because interior spaces often carry meaning (aligned columns in plain text) while leading ones carry indentation — and because historical behavior is contractual here. `-a`/`--all` lifts the restriction; `--first-only` restores it and **overrides `-a`** when both are given (making it the escape hatch in scripts that receive `-a` from a caller).

### `-a` and the interior-run economics

With `-a`, interior runs convert too — but the same economy rule applies. A run converts only when a tab reaches at least as far:

```bash
$ printf 'x        y\nx     y\nab    cd\n' | unexpand -a | cat -A
x^I y$
x     y$
ab    cd$
```

- `x        y`: the 8-space run crosses stop 8 → `x⇥ y` (tab + leftover space).
- `x     y`: 5 spaces end before stop 8 → tab would overshoot; untouched.
- `ab    cd`: 4 spaces starting at column 2 end at column 6, before stop 8 → untouched.

### `-t`: new grid, and it switches on `-a`

`-t N` moves the stops to every N columns — and **enables `-a`**, a documented surprise: with a non-8 grid, interior conversion is on by default. Tab-stop *lists* (`-t 1,4,10` or the `+N`/`/N` relative forms shared with `expand`) pin stops at absolute columns:

```bash
$ printf '    a\n' | unexpand -t 4 | cat -A
^Ia$
$ printf '      a\n' | unexpand -t 4 | cat -A
^I  a$
$ printf 'ab    cd\n' | unexpand -t 4 | cat -A
ab^I  cd$
```

Six spaces under 4-wide stops become tab-to-4 plus two leftover spaces — the leftover is what keeps columns identical. Note the last example: `-t 4` converted an *interior* run without `-a`, because `-t` implies it.

### What it counts as a column

Columns are counted in characters (per the locale), not display cells: multibyte UTF-8 characters advance one column per character, so text containing CJK wide glyphs or emoji will "unexpand" to a grid that looks misaligned on screen. For pure-ASCII code and config files — the overwhelmingly common case — this distinction never bites.

## Options That Matter

| Option | Effect |
|---|---|
| `-a`, `--all` | Convert all blank runs (not just leading ones) that a tab would not widen |
| `--first-only` | Convert only leading runs (the default behavior); overrides `-a` |
| `-t N`, `--tabs=N` | Tab stops every N columns instead of 8; **implies `-a`** |
| `-t LIST`, `--tabs=LIST` | Explicit stop positions, comma-separated; `+N`/`/N` relative forms as in `expand` |

No `-z`, no check modes, no header options — this tool has four concepts total, and the interplay of `--first-only`/`-a`/`-t` is the whole interview surface.

## Usage Patterns

```bash
# Repair space-indented Makefile recipes (recipes MUST start with a tab)
sed -n '/^\t/p' Makefile              # find what's already right
unexpand --first-only -t 8 < broken.mk > fixed.mk
```

```bash
# Re-tabs a file edited by someone whose editor inserted spaces
unexpand -a --tabs=4 src/legacy.c > src/legacy.c.new && mv src/legacy.c.new src/legacy.c
```

```bash
# Shrink verbose aligned logs before archival
unexpand -a service.log | gzip > service.log.gz
```

```bash
# Undo an accidental expand(1) pass on the whole tree
find . -name '*.tsv' -print0 | xargs -0 -I{} sh -c 'unexpand -a "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {}
```

```bash
# Pipe mode: compress leading indentation on streamed SQL output
mysql -e 'SELECT ...' | unexpand --first-only
```

```bash
# Verify a file's leading whitespace is tab-canonical for a style gate
diff <(unexpand --first-only file.py) file.py && echo 'indentation canonical'
```

```bash
# Round-trip sanity check: unexpand then expand must preserve columns
unexpand -a file | expand | diff - file && echo 'lossless'
```

```bash
# Match a project's 2-space grid explicitly
unexpand -a -t 2 notes.txt
```

## Nuances and Gotchas

- **`-t` silently turns on `-a`.** Scripts that expect `-t 4` to touch only indentation will see interior alignment rewritten. If you need leading-only semantics with a custom grid, add `--first-only` explicitly.
- **`unexpand` is not a byte-inverse of `expand`.** `expand` is deterministic; `unexpand` chooses *a* representation that lands on the same columns. Tabs followed by spaces (the classic mixed-indentation mess) may be rewritten differently than the original, so round-trip with `expand | diff` before overwriting anything.
- **Makefiles need tabs, and `unexpand` is the repair tool — but target the right columns.** Recipe lines must begin with a literal tab; `unexpand --first-only` fixes leading runs, while `-a` could rework whitespace inside recipe command lines where spaces were intentional.
- **Columns are characters, not display cells.** Wide (CJK/emoji) or combining characters make visual alignment diverge from the counted columns; the output stays *logically* consistent but may *look* ragged in a terminal.
- **Conversion never widens.** A blank run shorter than the distance to the next stop is preserved as spaces. If you expected aggressive compression, you wanted a different tab-stop grid (`-t`), not more force.
- **No in-place editing.** Like most coreutils filters, `unexpand` writes to stdout; the `> tmp && mv` dance (or `sponge` from moreutils) is required, and scripting `unexpand file > file` truncates the input before reading.
- **POSIX portability is real here.** `-a`, `--first-only` semantics and the 8-column default are standard; busybox and BSD match for the common cases. The `-t LIST` relative forms (`+N`, `/N`) are GNU extensions — avoid them in portable scripts.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All inputs processed successfully |
| 1 | An input could not be opened or read; a malformed `-t LIST` is also an error |

No content-dependent failure modes exist — the tool cannot fail on valid text.

## Related Commands

- [`expand`](./expand.md) — the mirror twin (tabs → spaces); read together, they define the tab-stop model.
- [`wc`](./wc.md) — measure what the compression bought (`wc -c` before/after).
- [`uniq`](./uniq.md) — another whitespace-sensitive text filter; pairs in normalization pipelines.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: What's the difference between `unexpand` and `sed 's/    /\t/g'`?

The tab-stop model. `unexpand` tracks the current output column and replaces a blank run with a tab only when the following character lands on the same or an earlier column — it compresses toward an 8-column (or `-t`-defined) grid without ever changing layout. A fixed-width `sed` substitution fires anywhere, changes effective columns, and mangles interior alignment. The question tests whether a candidate understands that tabs are column jumps, not four-space tokens.

### Q: A teammate runs `unexpand -a -t 4` over your source tree and indentation inside string literals changes. What happened?

Two flags compounded: `-t 4` *implies `-a`*, so interior runs — including blanks inside string literals or aligned comments — were eligible for conversion, and any run reaching a stop got tabbed. The result is still column-identical as text, but string content changed bytes, which can break parsers, golden tests, and hashes (see [`md5sum`](./md5sum.md) for why content hashes would shift). The safe recipe is `unexpand --first-only -t 4` — indentation only.

### Q: Why does Makefile repair keep coming up as unexpand's flagship use case?

Because the POSIX make grammar *requires* recipe lines to begin with a literal tab, and tab is invisible — pasted or auto-indented spaces produce the infamous "missing separator" error. `unexpand --first-only` converts exactly leading blank runs, which is the minimal, layout-safe repair. It's also the interview-ready example of a file *format* whose whitespace is syntax, unlike programming-language sources where whitespace is style.

### Q: When is `unexpand` the wrong tool even though the goal is "make it use tabs"?

When the text mixes tabs and spaces with intent (tables, code where a tab's meaning is "next multiple of 8" but the file assumed 4), when content is byte-sensitive (fixtures, protocol payloads, hashes are recorded over the current bytes), or when columns must stay visually aligned under wide-character locales — unexpand counts characters, not display cells. In those cases, an editor-level "retab" with a visible preview, or no tool at all, is safer than a batch rewrite.

### Q: Explain the economy rule — why does unexpand refuse to convert some runs even with -a?

Because a tab only advances to the next stop: replacing a run whose end falls short of that stop would push the following text *further right*, changing the layout. `unexpand`'s contract is column preservation, so it converts only when the substitution is column-neutral or narrowing. That's why `x     y` (five spaces, ending before stop 8) survives `unexpand -a` untouched — and why widening `-t` grids convert more: closer stops mean runs more often reach one.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/unexpand.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — unexpand](https://pubs.opengroup.org/onlinepubs/9699919799/)
