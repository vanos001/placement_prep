# rev — reverse the characters of each line

## Overview

`rev` copies files to stdout with the characters of each line reversed: the last byte of the line comes first. It ships in the `util-linux` package at `/usr/bin/rev`, has essentially no options, and is one of the smallest tools in the collection — a BSD-heritage filter that survived because it is occasionally the right answer to odd text-processing problems (mirror demos, palindrome checks, quick field flips) and because `tac | rev` composes into a full 180° rotation of a text block.

It is often confused with `tac` (reverses the *order of lines*, keeps characters intact — the exact complement), with `sort -r` (reverses sort order, not content), and with `sed`/awk one-liners doing the same job verbosely. Reaching for `rev` is a judgment call: it is byte-oriented, which is either exactly what you want or a UTF-8 corruption waiting to happen.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/rev |
| First appeared | BSD lineage (late 1970s) |
| Standards | Not POSIX; BSD/util-linux tradition |

## Synopsis

```
rev [file]...
```

Main one-line forms:

```
rev file.txt              # reverse each line of a file
rev                       # reverse stdin, line by line
tac file | rev            # full 180° rotation: lines and characters
printf '%s\n' word | rev  # inline check
```

## How It Works

### The filter loop

`rev` reads each input line up to `\n`, reverses its bytes, and writes it followed by the newline. Newlines stay in place (each line reverses independently); the newline itself is not reversed into the front:

```
$ printf 'abc\ndef\n' | rev
cba
fed
```

### The filter loop, as pseudocode

```
per record (terminated by \n — or \0 with -0 — or end of input):
    accumulate bytes into a buffer that grows as needed
    emit the buffer's bytes in reverse order
    emit the terminator unchanged
```

The algorithm cannot stream byte-by-byte: the first output byte is the *last* input byte of the record, so a full record must be buffered. Everything observable — unterminated final lines, multibyte shredding, memory on pathological lines — follows from those four lines.

Without operands it reads stdin; with multiple operands it processes them in order, concatenating the results. Two small observable behaviors verified locally:

- **A final line without `\n` stays unterminated**: `printf 'abc' | rev` emits `cba` with no trailing newline (`od -c` shows `c b a` and nothing else).
- **It is byte-reversal, not character reversal.** `printf 'h\xc3\xa9llo\n' | rev` yields bytes `o l l \303 \251 h` — the two-byte UTF-8 `é` is split, producing mojibake (verified with `od -c`). There is no locale-aware mode; `rev` predates multibyte text.

### NUL mode (-0) in recent util-linux

Recent util-linux releases added `-0, --zero`: NUL becomes the record separator on *both* input and output, and trailing NULs are preserved symmetrically:

```bash
$ printf 'abc\0de\0' | rev -0 | od -c
0000000   c   b   a  \0   e   d  \0
```

Each NUL-delimited segment is reversed byte-wise within itself; segment order is kept. This composes with the NUL-safe toolchain (`find -print0`, `sort -z`, `xargs -0`, `head -z`, `cut -z`) and extends rev's usable domain to path lists and binary-adjacent streams where newlines are just ordinary bytes. On older util-linux (and BusyBox) the flag does not exist — feature-test rather than assume (`rev --help 2>&1 | grep -q -- -0`).

### What reversal means for line structure

Leading and trailing whitespace swap sides, CR bytes move from line end to line start (which is why `rev` can make CRLF damage visible as a stray `\r` at the beginning of the reversed output), and fixed-width columns reverse as whole fields only if you pre-split. Compositions fix that:

```
tac file            # reverse line order only
rev file            # reverse characters within lines only
tac file | rev      # rotate the whole block 180 degrees
rev file | tac      # same rotation, other axis first
```

### Compositions as primitives

rev is cheapest to reason about as one axis-flip; everything else is composition:

```
goal                            recipe
last K characters of a line     rev | cut -c1-K | rev
strip trailing whitespace       rev | sed 's/^[[:space:]]*//' | rev
reverse line order              tac (rev does not reorder lines)
rotate a text block 180°        tac | rev (either axis first)
```

The "last K characters" idiom is what earns rev its keep in scripts: `cut`/`awk` count from the left, many legacy formats (fixed-width reports, log lines, mainframe exports) anchor their interesting field at the *right*, and rev converts a right-anchored problem into a left-anchored one and back. The whitespace idiom is the portable trick for stripping trailing blanks when the surrounding sed dialect makes `\s` classes unreliable.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-0`, `--zero` | Use NUL as the line separator on input and output (recent util-linux) |
| `-h`, `--help` | Usage |
| `-V`, `--version` | Version |

There is nothing else: no separator flag, no locale flag, no binary flag. Any real transformation beyond byte-reversal belongs to `sed`/awk/perl. (The `-0` row above is the one modern exception — a recent util-linux addition; on releases that predate it, the historical "nothing else" statement holds exactly.)

## Usage Patterns

```bash
# Check a palindrome without writing code
[ "$(printf '%s' racecar | rev)" = racecar ] && echo palindrome
```

```bash
# 180° rotation of a small ASCII diagram (both axes)
tac diagram.txt | rev
```

```bash
# Flip the last field to the front when lines end with the key you sort on
rev data.txt | cut -d' ' -f1 | rev | sort | uniq -c
```

```bash
# Reveal trailing-whitespace or CRLF damage at line ends (junk jumps to the front)
cat -A file.txt
```

```bash
# Read a file bottom-up with right-aligned text (demo/tricks)
rev file | tac
```

```bash
# Reverse a hostname chain in a pipeline (byte-safe because ASCII)
echo www.example.com | rev | cut -d. -f1 | rev   # -> com ... via reversed tokens
```

```bash
# Quick-and-dirty reverse of each token, keeping line order
while read -r line; do printf '%s\n' "$line" | rev; done < words.txt
```

```bash
# Take the last 12 columns of each fixed-width line (right-anchored fields)
rev report.txt | cut -c1-12 | rev
```

```bash
# Strip trailing whitespace when the sed dialect makes \s classes unreliable
rev file.txt | sed 's/^[[:space:]]*//' | rev
```

```bash
# NUL-delimited reversal inside a byte-safe pipeline
find . -maxdepth 1 -print0 | rev -0 | sort -z | head -z -n 3
```

```bash
# Involution sanity check: rev twice restores input byte-for-byte
printf '%s\n' 'pipeline test' | rev | rev
```

```bash
# Mirror ASCII art / banner text for layout testing
rev banner.txt
```

```bash
# Reverse-complement a DNA sequence: rev + tr compose (classic bio-shell)
echo GATTACA | rev | tr 'ACGTacgt' 'TGCAtgca'
```

```bash
# Feed fixed-width reversed lines to a left-to-right column extractor
rev wide-report.txt | cut -c1-8 | rev | sort | uniq -c | sort -rn | head
```

```bash
# The classic "last field with cut" trick (cut has no -1 from-the-right)
rev access.log | cut -d' ' -f1 | rev
```

## Nuances and Gotchas

- **Multibyte text is corrupted.** UTF-8 characters are multi-byte; reversing bytes reverses them individually. For human-language text use `perl -CSD -pe '$_=reverse'` or `python3 -c` with proper unicode handling — `rev` is for ASCII/byte data.
- **No separator concept.** Reversing `a,b,c` gives `c,b,a` — character order, not field order. Field-level reversal is awk: `awk '{for(i=NF;i;i--)printf "%s ",$i; print ""}'`.
- **Final-newline preservation is asymmetric.** Input without a trailing newline produces output without one — harmless in most pipelines, but a diff-visible difference if you round-trip files.
- **Binary input is processed "fine" and output garbage.** `rev` has no binary detection (unlike `less`); NUL bytes are just bytes, and the result is usually useless — do not let it near archives or images.
- **`rev` vs `sort -r` vs `tac`:** three different reversals (characters within lines / sort order / line order). Interviewers like asking for all three precisely because the names invite confusion.
- **BusyBox and BSD variants exist** and behave equivalently for ASCII; BSD `rev` is the ancestor. Not in POSIX — a minimal BusyBox rescue image may lack it where `sed` is guaranteed.
- **`-0` availability is version-dependent.** Added in recent util-linux; older bundles and BusyBox reject it as an invalid option. Feature-test in scripts rather than assuming.
- **Reversal is not field reversal.** `a/b/c` reversed is `c/b/a` only because each field is one character; multi-character fields interleave. Token-level reversal is awk's reverse loop or a `tr`/`tac`/`tr` split-join.
- **A pathological single line forces a whole-line buffer.** rev accumulates each line before writing it (verified locally: a 10 MB one-line input reverses fine, meaning the buffer scales); a multi-gigabyte "line" costs proportional memory. Line-at-a-time filters are not streaming-safe against pathologically long lines.
- **Pipeline position changes semantics.** `sort | rev` gives sorted lines with reversed characters; `rev | sort` sorts reversed text. Both "work" and answer different questions — decide the axis before composing.
- **Locale is ignored entirely.** LC_ALL/LANG have no effect — no multibyte decoding, no collation. Predictable, and the reason rev output can look "wrong" next to locale-aware tools in the same pipeline.
- **Composes cleanly only with byte-oriented stages.** Column selectors may count characters or bytes depending on implementation and locale (`cut -c` and awk `substr()` disagree across builds); rev is always bytes. Pipelines mixing rev with column tools are only reliable on ASCII — know which contract each stage honors.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Error: operand cannot be opened/read |

## Related Commands

- [`tac`](https://manpages.debian.org/bookworm/coreutils/tac.1.en.html) — the line-order complement; `tac | rev` rotates fully.
- [`sed-awk`](../../shell/sed-awk.md) — proper tools for field-aware or multibyte reversal.
- [`col`](./col.md) — sibling util-linux display filter; same "text munging for terminals" family.
- [`overview`](./overview.md) — hub page of the util-linux collection.

## Interview Questions

### Q: What exactly does rev reverse, and what breaks on UTF-8 input?

Bytes within each line, up to but not including the newline. UTF-8 encodes non-ASCII characters as multi-byte sequences, so byte reversal shreds them (verified: `héllo` becomes bytes `o l l \303 \251 h`). For text you must reverse *characters*, which means decoding first — `perl -CSD -pe '$_=reverse'` or an explicit Python one-liner. `rev` remains correct for ASCII, fixed-width data, and byte-level inspections.

### Q: Explain the difference between rev, tac, and sort -r.

`rev` reverses the characters inside each line, keeping line order. `tac` reverses the order of the lines, keeping characters. `sort -r` reverses the sort order — a completely different permutation that depends on the collation rules. They compose: `tac | rev` produces a 180° rotation of a monospaced text block. The trio is a compact test of whether someone actually knows what each filter permutes.

### Q: How would you reverse each *field* of a CSV line, and why is rev the wrong tool alone?

`rev` has no field awareness — `a,b,c` becomes `c,b,a` at the character level, which happens to work for single-character fields but destroys any field containing a comma or different widths. The right tool is awk with a reverse loop (`awk -F, '{for(i=NF;i;i--)printf "%s%s",$i,i==1?ORS:OFS}'`), or `rev` per field after splitting. The question tests knowing when a byte filter is sufficient versus when structure requires a parsing tool.

### Q: In a pipeline you pipe data through rev twice and get the original back. When does that property fail?

It holds exactly when the reversal is an involution on the data: pure bytes, line-terminated, no locale transformation — `rev | rev` restores input byte-for-byte (including a missing final newline, since rev neither adds nor removes one). It fails if anything in the pipeline normalizes text (DOS↔Unix conversion, locale-aware tools), if the data contains NUL bytes that some intermediate stage truncates (C-string handling), or if you mistakenly use `tac | rev | tac | rev`-style compositions where order of operations changes the result for non-rectangular data.

### Q: How would you reverse each line while preserving UTF-8 characters?

You cannot with rev — it has no decoding step. The character-preserving one-liners are `perl -CSD -pe '$_=reverse'` (decode to code points, reverse, re-encode) or a Python `str[::-1]` per line. And even code-point reversal is not full correctness: combining marks, ZWJ emoji sequences, and Indic conjuncts are grapheme clusters that reverse badly at code-point granularity — production text reversal needs a grapheme-aware library. The interview ladder is bytes (rev) → code points (perl -CSD) → graphemes (ICU); most answers stop one rung too low.

### Q: Where is rev genuinely the right production tool rather than a trick?

Right-anchored access to fixed-width ASCII: legacy reports, bank/EDI exports, log lines whose key field sits at the end, generated column layouts. There it beats sed/awk on clarity (`rev | cut -c1-8 | rev` is self-explanatory) and on cost (one pass, no parsing). With `-0` on recent util-linux it also slots into byte-safe pipelines around `find -print0`/`xargs -0`. Wrong domains: human-language text, multibyte encodings, anything field-structured — that is parsing territory, not byte-reversal territory.

### Q: What does rev -0 change, and why does NUL matter to the rest of the pipeline?

NUL replaces newline as the record separator on both input and output, aligning rev with the text-processing convention for "data that may contain any byte except NUL" — filenames (`find -print0`), `xargs -0`, `sort -z`. It makes rev composable in byte-safe pipelines without inventing escaping schemes. The costs: output is no longer line-oriented for humans, and the flag is a recent util-linux addition absent from BusyBox and older installs, so portability requires feature-testing.

### Q: rev is not POSIX. What is the portable fallback, and what are its tradeoffs?

The byte-reversal itself is easy in awk: `awk '{n=split($0,c,""); for(i=n;i;i--)printf "%s",c[i]; print ""}'` — `split` with an empty separator yields single characters (bytes in the C locale). It is slower than rev's C loop and equally byte-oriented (same UTF-8 caveat), but it exists everywhere awk does, including minimal initramfs images that lack rev. Knowing *which property* you actually need — byte order reversal, not rev-the-binary — is the point of the question.

### Q: Implement rev yourself for a pipeline library. What are the edge cases, and why can't you stream?

You cannot stream byte-by-byte — the first output byte depends on the last input byte of the record — so you buffer one record, which forces decisions on: growth policy for unbounded line lengths, the final record when input ends without a terminator (emit it unterminated, as rev does), the separator choice (newline vs NUL for `-0`-style operation), and NUL bytes themselves (fine as bytes, fatal if any downstream stage is C-string based). Memory is O(longest record), not O(stream) — the honest trade versus, say, a two-pass approach over a seekable file that reverses from the end.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/rev.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
