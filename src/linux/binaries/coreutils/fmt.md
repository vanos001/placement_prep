# fmt — reflow (fill and wrap) paragraphs of text

## Overview

`fmt` is a paragraph reformatter: it reads text, joins the lines of each
paragraph into one long word stream, then re-emits the words on lines as
close as it can get to a target width. It is the tool for normalizing
prose — README files, commit messages, comment blocks, quoted mail —
where lines were wrapped at the wrong column and you want them wrapped at
the right one *without losing the paragraph structure*.

The key word is **reflow**: unlike [`fold`](./fold.md), which cuts lines at
a fixed column and never joins anything, `fmt` both joins and splits. That
makes it powerful and destructive in equal measure — run it on a source
file or a config and it will happily weld lines together. It is often
reached for in pipelines: `git log --format=%B | fmt -w 72`,
`fmt -p '# ' -w 78` over a comment block, or `fmt -s` as a line-length
enforcer that only touches too-long lines.

Debian ships it in `coreutils` at `/usr/bin/fmt`. It is not a POSIX
utility; it descends from BSD and was rewritten for GNU textutils, so
GNU and BSD implementations agree on the core flags but diverge in the
corners (see gotchas).
| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/fmt` on modern Debian/Ubuntu |
| First appeared / lineage | BSD heritage; rewritten for GNU textutils (early 1990s) |
| Standards | Not in POSIX; GNU/BSD implementations with compatible cores |

## Synopsis

```
fmt [-WIDTH] [OPTION]... [FILE]...
```

Main forms:

```bash
fmt -w 80 file.txt          # refill paragraphs to 80 columns
fmt -s -w 100 long.txt      # split long lines, never join
fmt -p '# ' -w 78 code.py   # reflow only lines starting with '# '
fmt -c -w 72 reply.txt      # preserve first-two-lines indentation
```

`-WIDTH` is an accepted abbreviation for `--width=DIGITS` (`fmt -72 file`),
a convenience dating to the BSD days. With no FILE, or FILE being `-`,
fmt reads stdin.

## How It Works

### Paragraph detection

fmt groups input into paragraphs before doing anything: a **blank line**
ends a paragraph, and so does a **change in leading whitespace** — an
indented line begins a new paragraph of its own. This is why code and
text with intentional indentation survive better than you'd fear, and
why every line of a bullet list needs the same indent to be refilled as
one block.

```bash
$ printf 'aaa bbb ccc\nddd eee fff\n  indented line starts\n  new paragraph here\n' | fmt -w 15
aaa bbb ccc
ddd eee fff
  indented
  line
  starts new
  paragraph
  here
```

### Fill: goal width, not just max width

fmt's target is not the `-w` maximum but the **goal**, defaulting to 93%
of the width (`-g` to set it). Break points are chosen to land lines near
the goal without ever exceeding the width — and fmt rebalances rather
than greedily packing, which sometimes means it declines to join lines
that a naive filler would weld together:

```bash
$ printf 'aaa bbb ccc\nddd eee fff\n' | fmt -w 15
aaa bbb ccc          # greedy fill would produce "aaa bbb ccc ddd" (15)
ddd eee fff          # fmt prefers the balanced 11/11 split
```

```bash
$ printf 'The quick brown fox jumps over the lazy dog and then keeps running through the meadow\n' | fmt -w 20
The quick brown fox
jumps over the lazy
dog and then keeps
running through
the meadow
```

### Split-only mode: -s

`-s` (split-only) never joins: too-long lines are wrapped at the width,
short lines pass through byte-for-byte. This is the mode for enforcing a
maximum line length where joining could damage meaning — prose files with
deliberate short lines, generated text, or anywhere "refill" would erase
structure:

```bash
$ printf 'one two three four five six\n\nalpha beta gamma delta epsilon zeta\n' | fmt -s -w 20
one two three four
five six

alpha beta gamma
delta epsilon zeta
```

### Prefix mode: -p

`-p STRING` reformats only lines beginning with STRING and reattaches the
prefix to every output line; lines without the prefix are left untouched.
This makes comment-block reflow safe inside mixed files:

```bash
$ printf '# This is a long comment line that should be reflowed nicely with prefix kept\n' | fmt -p '# ' -w 30
# This is a long comment line
# that should be reflowed
# nicely with prefix kept
```

### Crown margin and tagged paragraphs: -c, -t

Both flags exist for the shapes mail and man pages produce. `-c` (crown
margin) preserves the indentation of the first two lines of a paragraph
and refills the body under it — the classic email quote shape. `-t`
(tagged paragraph) treats the first line as a "tag" whose indentation
differs from the rest; continuation lines follow the *second* line's
indent:

```bash
$ printf '  First line indented\n  second line also indented and this paragraph is long enough to be wrapped by fmt so crown margin shows\n' | fmt -c -w 40
  First line indented second line also
  indented and this paragraph is long
  enough to be wrapped by fmt so crown
  margin shows
```

```bash
$ printf 'first line here\n  tagged second line of the same paragraph which is long enough to wrap around a bit\n' | fmt -t -w 30
first line here tagged second
  line of the same paragraph
  which is long enough to
  wrap around a bit
```

### Uniform spacing: -u

`-u` rewrites whitespace: one space between words, two after sentence
endings (`.` `!` `?`). Note the asymmetry with plain fmt — a short
pass-through paragraph normally keeps its original spacing, but `-u`
normalizes every paragraph it touches:

```bash
$ printf 'Hello   world.  Two  spaces   everywhere,\n  odd  indent.\n' | fmt -u -w 30
Hello world.  Two spaces
everywhere,
  odd indent.
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-w`, `--width=WIDTH` | Maximum line width; default 75 columns (`-WIDTH` is shorthand) |
| `-g`, `--goal=WIDTH` | Preferred width, default 93% of `-w`; fmt balances lines toward it |
| `-s`, `--split-only` | Wrap too-long lines but never join — structure-preserving mode |
| `-p`, `--prefix=STRING` | Reflow only lines starting with STRING; reattach STRING to output |
| `-c`, `--crown-margin` | Keep first two lines' indentation, refill the rest of the paragraph |
| `-t`, `--tagged-paragraph` | First line indented differently from the body; body follows line two |
| `-u`, `--uniform-spacing` | One space between words, two after sentence end |

## Usage Patterns

```bash
# Normalize a README's paragraphs to a modern 80-column layout
fmt -w 80 README.txt
```

```bash
# Re-wrap commit messages to the conventional 72 columns
git log -1 --format=%B | fmt -w 72
```

```bash
# Reflow only the comment block in a script, leaving code untouched
fmt -p '# ' -w 78 deploy.sh > deploy.sh.new
```

```bash
# Enforce a max line length without joining anything (linter pre-pass)
fmt -s -w 100 notes.md | diff - notes.md
```

```bash
# Clean up ragged spacing in prose: single spaces, two after periods
fmt -u -w 75 draft.txt
```

```bash
# Email-quote-shaped text keeps its crown margin while refilling
fmt -c -w 72 quoted-reply.txt
```

```bash
# Reflow a quoted mail block by its '> ' prefix only
fmt -p '> ' -w 72 reply.eml
```

## Nuances and Gotchas

- **fmt is destructive by design.** It joins lines; ASCII tables, code,
  diffs, poetry, and `.ini`-style files are casualties. `fmt -s` limits
  the blast radius to splitting, but plain `fmt` on anything structured is
  a bug waiting for a cron job to find it.
- **No dot-line or header protection in GNU fmt.** Lines starting with `.`
  (nroff requests) and mail headers get joined like any other text —
  verified: `.TH test 1` merges into the next sentence. BSD fmt's `-m`
  guards mail headers; ported scripts lose that safety net.
- **fmt is not POSIX.** GNU and BSD agree on the core `-c/-s/-w/-p` but
  diverge elsewhere — GNU's `-u` uniform spacing has no BSD equivalent,
  BSD adds `-m` for mail headers, and goal semantics differ. For scripts,
  prefer `fold` (standardized) or test the flag on the target platform.
- **Width counting is byte-ish for multibyte text.** GNU fmt treats
  multibyte characters loosely: `héllo wörld` measures 11 columns but 13
  bytes, and at `-w 12` fmt wraps it — UTF-8 and CJK text comes out
  narrower than the width you asked for. Very long non-ASCII words are
  the mid-split edge case.
- **Goal-width balancing surprises people.** fmt optimizes line lengths
  toward the 93% goal and may *refuse to join* short adjacent lines when
  the balanced split looks better (the `aaa bbb ccc / ddd eee fff`
  behavior above). If you expected a greedy fill, the output looks
  "unjoined" — that is the algorithm, not a bug.
- **Whitespace is only normalized where filling happens.** A short
  paragraph that fits on one line passes through with its original
  spacing (tabs and all) unless `-u` is given. Mixing "untouched" and
  "refilled" paragraphs in one file yields inconsistent spacing.
- **Blank-line boundaries are semantic.** Collapsing or removing blank
  lines changes paragraph structure and thus the output — never
  pre-`cat -s` a file you are about to fmt if the blank lines matter.
- **`-p` anchors at line start.** Indented comments (`  # note`) do not
  match a `-p '# '` prefix and are skipped; the prefix must literally
  begin the line.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | All files processed and reflowed successfully |
| 1 | Error: invalid width/option, unreadable input file, write failure |

## Related Commands

- [`fold`](./fold.md) — the non-reflowing sibling: cuts at a fixed width, never joins; POSIX-standardized
- [`expand`](./expand.md) — tabs to spaces before reflowing so fmt sees uniform whitespace
- [`unexpand`](./unexpand.md) — restore tabs after reflow for tab-indented formats
- [`sed-awk`](../../shell/sed-awk.md) — awk reflow recipes when fmt's paragraph rules don't fit
- [`cut`](./cut.md) — column-wise extraction when you want fields, not prose
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages

## Interview Questions

### Q: What is the fundamental difference between fmt and fold?

fmt **reflows**: it joins the lines of a paragraph and re-splits them to
approach a goal width, which changes both line count and line content
(whitespace between words can shift). fold **cuts**: every output line is
a prefix of the original line at a fixed column, nothing is ever joined,
and the transformation is nearly reversible by deleting the newlines. Use
fmt for prose you want to rewrap, fold for text where lines must only get
shorter — and note fold is the POSIX-standardized one.

### Q: When would you use `fmt -s` instead of plain fmt?

When too-long lines need wrapping but existing short lines must not move:
`-s` disables joining entirely. Typical cases are enforcing a line-length
budget on text with deliberate structure, post-processing generated files
where reflow could corrupt meaning, and diff-friendly fixes — only the
offending lines change, so the diff shows exactly the wrapped lines.

### Q: Explain fmt's goal width and why output lines are not all the same length.

The goal (default 93% of `-w`) is the *target* length fmt balances lines
toward, while `-w` is the hard maximum it never exceeds. Because fmt
optimizes rather than greedily packs, it may leave a line at 11 characters
instead of welding one more word to hit 15 — it prefers balanced lines
close to the goal over ragged right edges pushed to the limit. `-g` lets
you tune that target independently (a low goal yields narrower, airier
text).

### Q: How do you reflow comment blocks inside a source file safely?

`fmt -p '# ' -w 78` reformats only lines that begin with the prefix and
reattaches the prefix to each output line; every non-prefixed line (the
code) passes through untouched. The prefix must start at column zero —
indented comments don't match — and the file should be written via a
temp output (`fmt ... > f.new && mv f.new f`), which is also where
[`mktemp`](./mktemp.md) earns its keep.

### Q: Why can fmt damage mail or roff files, and what mitigations exist?

fmt joins any adjacent short lines, including mail headers
(`Subject: ...` followed by continuation lines) and nroff requests
(lines starting with `.`), producing corrupted output — GNU fmt verified
to merge `.TH test 1` into the next sentence. Mitigations: BSD fmt's `-m`
avoids mail headers; GNU-side, split the file first (header/body), use
`-p` to restrict processing, or use `-s` so nothing is ever joined.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/fmt.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
