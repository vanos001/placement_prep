# ptx — produce a permuted index (keyword-in-context)

## Overview

`ptx` builds a **permuted index**, also known as a KWIC index ("keyword in context"). It reads text, treats (almost) every word as a keyword, and emits one output line per keyword occurrence: the keyword plus its surrounding context, rotated so the keyword starts near the middle of the line. The lines are then sorted by keyword — which is what makes it an *index*: to find every place a word occurs, you look up the word and read the contexts in one alphabetical run.

This is a very old idea — KWIC indexes were standard fare for technical documentation in the 1960s–80s, and the classic Unix `ptx` fed groff/Texinfo macro packages that typeset book-style back-of-the-book indexes. Today `ptx` is a niche curiosity inside GNU coreutils: it is not POSIX, absent from most BSD base systems, and virtually nobody builds printed indexes with it anymore. It survives as a teaching example of text rotation and as a self-contained tool for quick concordances.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/ptx`, from upstream GNU coreutils. Do not confuse it with `grep` (which finds lines but does not rotate or sort them), with `look`-style dictionary lookup, or with the `apropos`/`whatis` database, which is a different (man-page) use of the same KWIC idea.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/ptx` |
| First appeared / lineage | Unix `ptx` (System V era); rewritten for GNU by François Pinard; `-G` keeps System V compatibility |
| Standards | None — GNU extension (not in POSIX.1-2018) |

## Synopsis

```
ptx [OPTION]... [INPUT]...
ptx -G [OPTION]... [INPUT [OUTPUT]]
```

Main forms:

```
ptx FILE                     # permuted index, plain format, width 72
ptx -A FILE                  # add file:line references to each entry
ptx -w 40 FILE               # narrower output width
ptx -O FILE                  # roff macro output (.xx "..." ...) for typesetting
```

With no FILE, or when FILE is `-`, input is read from standard input.

## How It Works

### A worked example

Take a three-line file with no sentence punctuation:

```
$ printf 'apple\nbanana\ncherry\n' > fruit.txt
$ ptx fruit.txt
                                       apple banana cherry
                               apple   banana cherry
                        apple banana   cherry
```

One output line per keyword occurrence, sorted by keyword:

```
apple   →  "apple banana cherry"     keyword first; context follows it
banana  →  "apple   banana cherry"   left context, gap, keyword, following context
cherry  →  "apple banana   cherry"   all preceding words stack up as left context
```

The layout rule: the **keyword is the first word after the middle of the page width**. With defaults (width 72, gap 3) the left-context field is right-aligned around column 36 and the keyword begins at column 40. Context words are printed with their original single spaces; the only widened gaps are between the left field and the keyword. Because the input had no sentence-ending punctuation, all three lines form one context stream, so `cherry` (the last word) still shows `apple banana` as its left context.

### Words, sorting, and the context stream

- **Every word is a keyword by default.** Words are runs of non-break characters; hyphens and most punctuation are break characters, so `a-b c` yields keywords `a`, `b`, and `c`.
- **Sorting is by keyword, byte order** — `Dogs` sorts before `bark` (uppercase before lowercase). `-f` folds case for sorting.
- **The context is one "sentence"** whose boundaries default to end-of-line *when the line ends with sentence punctuation* (`.` `!` `?`). A line like `One two. Three four.` does not end a sentence (the punctuation is mid-line), but `One two.` on its own line does. Inside a sentence, context wraps around circularly: the entry for the last word of the file can show the file's first words as its following context, with a `/` flagging where the wrap occurred.
- **Truncation is flagged with `/`** (changeable via `-F`). Narrow the width and you see the flags appear:

```
$ ptx -w 30 fruit.txt | cat -A
        apple/$
     /   banana/$
     /   cherry$
```

### Restricting and widening the keyword set

Real documents produce enormous indexes because function words become keywords. `ptx` offers three filters, all file-based:

- `-i IGNORE-FILE` — stop list: words listed there never become keywords (one per line).
- `-o ONLY-FILE` — inverse: *only* listed words become keywords.
- `-W REGEXP` — replace the word definition entirely with a regexp match.

```
$ printf 'the\nquick\n' > stop.txt
$ ptx -i stop.txt ptx_in.txt       # 'the' and 'quick' no longer produce entries
```

### Machine-readable output

The default format is meant for humans — but the keyword is not visually emphasized, so tools consuming it must rely on the column position. `-O` emits groff macro calls instead, with the fields quoted explicitly:

```
$ ptx -O fruit.txt
.xx "" "" "apple banana cherry" ""
.xx "" "apple" "banana cherry" ""
.xx "" "apple banana" "cherry" ""
```

The macro name defaults to `xx` (`-M` changes it); `-T` produces TeX-style `\xx {...}` output instead. These are the hooks the historical Texinfo/groff index pipelines consumed. `-G` switches to the traditional System V mode, which takes `[INPUT [OUTPUT]]` operands and reproduces old `ptx` behavior for compatibility.

### References

`-A` automatically prefixes each entry with `file:line`, turning the index into a navigable concordance — pipe an entry's line number straight into `sed -n '3p'` to jump back to the source. `-r` is the manual variant: it treats the first whitespace-delimited field of each input line as the reference (useful when your input already carries section numbers or IDs). `-R` moves references to the right margin, excluded from the width computation.

```
$ ptx -A fruit.txt
fruit.txt:1:                               apple banana cherry
fruit.txt:2:                       apple   banana cherry
fruit.txt:3:                apple banana   cherry
```

## Options That Matter

| Option | Effect |
|---|---|
| `-A` | Auto-references: prefix every entry with `input-file:line-number` |
| `-w NUMBER` | Output width in columns (default 72), references excluded |
| `-g NUMBER` | Gap size between the output fields (default 3) |
| `-f` | Fold lowercase to uppercase for sorting (case-insensitive ordering) |
| `-i FILE` | Ignore list: words in FILE never become keywords |
| `-o FILE` | Only list: restrict keywords to words in FILE |
| `-W REGEXP` | Use REGEXP to match keywords instead of the default break-character rule |
| `-b FILE` | Read break characters (word-boundary characters) from FILE |
| `-S REGEXP` | Regexp marking end of sentence / end of line for the context stream |
| `-F STRING` | String flagging truncation (default `/`) |
| `-r` | First field of each input line is a reference, not index text |
| `-R` | Put references at the right side, not counted in `-w` |
| `-O` | Output as roff macro calls (`.xx "..." "..." "..." "..."`) |
| `-T` | Output as TeX macro calls (`\xx {...}{...}{...}{...}`) |
| `-M NAME` | Macro name to emit instead of `xx` |
| `-G` | Traditional System V mode (also changes operand grammar) |
| `-t` | "Typeset mode" — documented but **not implemented** (the help says so) |

## Usage Patterns

```bash
# Build a KWIC concordance of a document, jumping back via file:line
ptx -A design.txt | less
```

```bash
# Only index domain terms, not every word of English
printf 'retries\ntimeout\ncircuit\n' > terms.txt
ptx -o terms.txt runbook.txt
```

```bash
# Drop stop words: 'the', 'a', 'of' stop polluting the index
printf 'the\na\nof\nand\nto\n' > stopwords.txt
ptx -i stopwords.txt chapter1.txt
```

```bash
# Index identifiers in source code, not language keywords
printf '[A-Za-z_][A-Za-z_0-9]*' > /dev/null   # concept shown with -W below
ptx -W '\w+' parser.c | head -20
```

```bash
# Case-insensitive ordering so 'Cache' and 'cache' sort together
ptx -f glossary.txt
```

```bash
# Narrow index for a terminal pane
ptx -w 50 -g 2 notes.txt
```

```bash
# One-line-per-word input: each word becomes its own entry with stream context
printf 'apple\nbanana\ncherry\n' | ptx
```

```bash
# Feed a permuted index through grep: find every context of 'timeout'
ptx -A system.log.summary | grep -i timeout
```

```bash
# Machine-readable roff output for a downstream typesetter
ptx -O -M ptxentry essay.txt > essay.ptx.roff
```

```bash
# Combine filters: only these words, case-folded, with references
ptx -A -f -o terms.txt runbook.txt
```

```bash
# Use it as a quick 'every word rotated' view of a headline
printf 'faster than the speed of night\n' | ptx -w 60
```

```bash
# Count how many distinct keyword entries a file would produce
ptx thesis.txt | wc -l
```

## Nuances and Gotchas

- **The keyword is not marked.** In the default output you locate the keyword by column position (first word after the center gap) — there is no bolding or marker. That is exactly why `-O`/`-T` exist for downstream tools. Do not parse the plain format with naive string splitting; count columns or use `-O`.
- **Not POSIX, not everywhere.** `ptx` is a GNU extension: absent from busybox, absent from some BSD base installs, and its traditional `-G` mode exists only for System V compatibility. Scripts using it need a GNU userland guarantee.
- **Sentence-boundary defaults are subtle.** Context breaks only at end-of-line *with* trailing sentence punctuation; mid-line periods do not break the stream, and punctuation-less files become one giant circular context. For structured input (logs, CSV), set `-S` or preprocess — otherwise entries will smear across records exactly as in the examples above.
- **Identical entries collapse.** Two occurrences of a word with byte-identical surrounding context render as one output line (verified: `Dogs bark` / `dogs run` yields four entries, not five — the two `dogs` occurrences share the same context). Do not equate "one output line per word occurrence" too strictly.
- **Punctuation breaks words.** Default break characters include hyphens, so `state-of-the-art` contributes keywords `state`, `of`, `the`, `art` — multiplying index noise. Use `-W` for code or token-style input.
- **Sorting is byte order by default.** Mixed-case input sorts all uppercase words before all lowercase ones; add `-f` or preprocess with `sort` yourself if human-alphabetical order matters.
- **`-t` is a trap.** It is documented as "typeset mode" but prints `- not implemented -` in its own help text; do not build anything on it.
- **Scale is modest by design.** `ptx` holds the text and builds every rotation in memory; that is fine for documents, hopeless for gigabyte logs. For large corpora, generate the index with `awk`/`grep -o` pipelines instead.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Index produced successfully |
| 1 | Error — unreadable input file, bad option argument, or unusable output |

## Related Commands

- [`sort`](./sort.md) — the underlying ordering primitive; `ptx` output is sorted keyword-first
- [`grep`](../../shell/grep.md) — finds occurrences in place; `ptx` additionally rotates and sorts them
- [`fold`](./fold.md) — wraps lines to a width; complementary when massaging index text
- [`fmt`](./fmt.md) — paragraph reflow for the input side of index building
- [`comm`](./comm.md) — set operations on sorted word lists (complement a stop list yourself)
- [`csplit`](./csplit.md) — split a document into sections before indexing them separately
- [`sed-awk`](../../shell/sed-awk.md) — awk builds custom concordances when `ptx`'s fixed format does not fit
- [`man-pages`](../../reference/man-pages.md) — `apropos`/`whatis` apply the same KWIC idea to man pages
- [`overview`](./overview.md) — GNU Coreutils collection hub

## Interview Questions

### Q: What is a permuted index, and how does ptx construct one?

A permuted index (KWIC index) lists every word of a text as a lookup key, with the surrounding text shown in place: each output line is the text rotated so that one keyword occurrence sits at a fixed position near the middle of the line. `ptx` tokenizes the input into words, emits one line per occurrence — left context right-aligned, keyword and following context after the center gap — then sorts the lines by keyword so all occurrences of the same word are adjacent alphabetically. Truncation of context is flagged with `/` by default.

### Q: How do you stop function words like "the" and "of" from dominating a ptx index?

Three mechanisms: `-i FILE` supplies a stop list of words that never become keywords; `-o FILE` inverts the logic and whitelists exactly the words that may become keywords; `-W REGEXP` redefines what a word is altogether (e.g. identifier characters for source code). In practice the stop list is the classic approach and mirrors what printed KWIC indexes did by hand.

### Q: Explain the context "sentence" model in ptx and when it surprises you.

Context does not simply span the current line: by default, a sentence boundary exists only at end-of-line when the line ends with `.`/`!`/`?`. So a file of punctuation-less lines is one giant context stream — entries for the first words show later lines as context and vice versa, wrapping circularly within the sentence. Mid-line periods do not break anything. For logs or record-structured data this smears entries across records; you either add proper sentence punctuation, pass a custom `-S` regexp, or preprocess the input.

### Q: Why does ptx have -O and -T output modes instead of just text?

Because the original consumer of `ptx` output was a typesetting pipeline, not a human: groff or TeX macro packages (macro name `xx`, overridable with `-M`) read the quoted-field output and typeset a book-style index with proper fonts, hanging indents, and page references. The plain format cannot reliably tell the consumer where the keyword starts — column counting is fragile — so the machine-readable modes mark the fields explicitly. This is also why `-O` output is the safe format to parse programmatically.

### Q: ptx vs grep: when would either be the right tool for "show me every place this word appears"?

`grep -n` answers it directly and streams in one pass — right tool for one word, one file, right now. `ptx -A` precomputes a sorted concordance for *every* word at once, so repeated lookups (or reviewing a document's vocabulary in context) become a single `less` session or a `grep` over the index. The cost: `ptx` is GNU-only, memory-bound, rotates context across line boundaries by its sentence rules, and renders duplicates of identical context as a single entry — so it is a documentation tool, not a search primitive.

### Q: What does -G do and why is it still there?

`-G` selects the traditional System V `ptx` compatibility mode, which also changes the command grammar to `[INPUT [OUTPUT]]` and reproduces older word-break and formatting behavior. It exists so decades-old scripts and documentation toolchains keep working unchanged on GNU systems — a small, self-contained fossil in coreutils, and a good interview illustration of why GNU tools carry compatibility shims for pre-POSIX Unix behavior.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/ptx.1.en.html)
