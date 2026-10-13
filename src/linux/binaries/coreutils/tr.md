# tr — translate, squeeze, or delete characters

## Overview

`tr` maps characters to characters. It reads a byte stream, transforms individual bytes according to two character-set operands, and writes the result — nothing more. That narrowness is the point: there is no regex engine, no fields, no state between bytes, so `tr` is one of the fastest filters in the toolbox and the standard answer to "uppercase this", "strip the carriage returns", "collapse these blank runs", and "rot13 this".

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/tr`, from upstream GNU coreutils. It descends from Research Unix and is POSIX-standardized, with GNU adding `-t` (truncate-set1), `-C` as an alias for `-c`, and the `[\n*]`-style repeat in SET2.

What it is often confused with: `sed`'s `y///` command (per-character translation embedded in a stream editor with regex addressing and in-place editing), `awk`'s `gsub` (string/regex replacement, not 1:1), and `expand`/`unexpand` (tab↔space alignment, which requires column arithmetic `tr` cannot do). `tr` also has no file operands at all — it is a pure filter — and the "`tr a b file`" habit picked up from `sed` fails with `tr: extra operand`.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/tr` |
| First appeared / lineage | Research Unix v4 era (early 1970s); BSD/System V/GNU lineages |
| Standards | POSIX.1-2018 (`tr`: `-c -d -s`; short-SET2 behavior unspecified) |

## Synopsis

```
tr [OPTION]... STRING1 [STRING2]
```

Exactly two strings mean translate; one string requires `-d` or `-s`. Main forms:

```
tr 'a-z' 'A-Z'                 # translate: 1:1 byte mapping
tr -d '\r'                     # delete every byte in SET1
tr -s ' \n'                    # squeeze repeated SET1 bytes to one
tr -cs '[:alnum:]' '[\n*]'     # delete+squeeze combo: one word per line
tr -t 'abc' 'xy'               # translate with SET1 truncated to |SET2|
```

SET1/SET2 are **sets of single bytes**, not strings or regexes; see the grammar below. Input and output are always stdin/stdout.

## How It Works

### A byte filter, not a line editor

`tr` has no concept of lines, records, or fields. It moves a byte at a time through a 256-entry translation table:

```
 stdin (any bytes, NUL included)
   │
   v
 byte == 0x63 ──> lookup table[0x63] ──> table says 'X' ──> write 'X'
   │                                                    (delete mode: write nothing;
   │                                                     squeeze mode: collapse runs
   v                                                     of the target byte)
 stdout
```

Because there is no line discipline, `tr` is fully NUL-transparent — one of the few classic tools that handles binary-ish data and NUL-separated streams without special flags (`tr '\0' ' '` works; `sed` historically does not). And because the mapping is 1:1, translation **never changes the stream length** — only `-d` (delete bytes) and `-s` (squeeze runs) can.

Translation table construction is where all the intelligence lives: the operand grammar below expands into byte sets, and translate mode zips SET1 with SET2 positionally.

### The SET grammar: five shorthand families

```
syntax          expands to                       legal in
--------------  -------------------------------  --------------
C               the byte C itself                SET1, SET2
\NNN            byte with octal value NNN        SET1, SET2
                (1-3 octal digits; \400 -> \0400,
                a documented GNU quirk)
\a \b \f \n     BEL BS FF NL CR TAB VT           SET1, SET2
\r \t \v \\
M-N             bytes M through N, in the        SET1, SET2
                locale's collation order; error
                if M collates after N
[:CLASS:]       bytes of a character class       SET1; SET2 only
                (alnum alpha blank cntrl digit    upper<->lower case
                graph lower print punct space     conversion, or any
                upper xdigit)                     class with -d AND -s
[=C=]           characters equivalent to C       SET1 (and SET2 with
                                                 -d AND -s)
[C*N]           N copies of C (N octal if it     SET2 only — a repeat
                starts with 0)                   construct, never SET1
[C*]            as many copies of C as needed    SET2 only
```

Details that separate users from debuggers:

- **Repeats are SET2-only.** `tr '[a*]' x` is rejected outright: `tr: the [c*] repeat construct may not appear in string1`. Their purpose is padding SET2 to SET1's length: `tr 'xyz' '[a*2]b'` produces `aab`.
- **Classes in SET2 are restricted.** Outside of `-d`+`-s` combos, only `[:upper:]` and `[:lower:]` may appear in SET2, and only position-matched against `[:lower:]`/`[:upper:]` in SET1 — that pair is how case conversion is spelled.
- **Equivalence classes are a no-op on GNU/glibc.** The manual states each character's equivalence class "consists only of that character, which is of no particular use". `tr '[=e=]' X` maps only `e`; `E` and `é` pass through untouched.
- **Unknown escapes are literal.** As a GNU extension, `\q` means `q` (this also lets you escape `[` and `-`). Consequently `\x62` is *not* hex 0x62 — it is the three bytes `x62`. GNU `tr` has no hex escapes; build such operands with shell quoting instead.
- **Brackets are not syntax around ranges.** `tr -d '[0-9]'` deletes `[`, `]`, *and* the digits — the System V bracket convention is unsupported, and the manual warns exactly this.

### Four operating modes (plus the complement flag)

`tr` performs one of four operations, selected by flags; `-c`/`-C` complements SET1 (and thus every mode):

```
mode            operands          action
--------------  ----------------  --------------------------------------
translate       SET1 SET2         byte in SET1 -> byte at same index in SET2
squeeze (-s)    SET1              runs of a SET1 byte -> one copy of it
delete (-d)     SET1              remove SET1 bytes entirely
delete+squeeze  SET1 SET2         delete SET1 bytes, then squeeze SET2 bytes
```

- **`-s` squeezes the LAST specified array.** With `tr -s 'ab'` that is SET1; in translate+squeeze mode (`tr -s 'a' ' '`) it is SET2 — you translate first, then squeeze the *result* characters. Squeezing is per-byte: `tr -s '[:space:]'` turns `a   \t\tb` into `a \tb` — a three-space run collapses to one space, a tab run to one tab, but a mixed ` \t` run does not become a single character.
- **`-c` inverts SET1.** `tr -cd '[:print:]\n'` deletes everything except printable bytes and newline — the classic binary-juju scrubber. `tr -cs '[:alnum:]' '[\n*]'` is the canonical word-per-line filter: complement (non-alphanumeric) bytes become newlines, then repeats squeeze to one.
- **Operand-count rules are enforced.** `tr -d 'a' 'b'` aborts (`Only one string may be given when deleting without squeezing repeats`), plain `tr 'ab' ''` aborts (`when not truncating set1, string2 must be non-empty`), and `tr 'a' 'b' somefile` aborts with `extra operand` — there are no file arguments, period.

### Short SET2: pad, truncate, or error?

What happens when SET2 is shorter than SET1 split an entire family of Unixes:

```
$ printf 'abc\n' | tr 'abc' 'xy'
xyy        # GNU follows BSD: pad SET2 by repeating its last character

$ printf 'abcdef\n' | tr -t 'abc' 'xy'
xycdef     # -t: truncate SET1 to 2 bytes first; only a->x, b->y happen
```

POSIX leaves the short-SET2 case undefined; System V `tr` truncated SET1 (what GNU `-t` does now) and BSD padded with the last character (GNU's default). Portable scripts should not depend on either — pad SET2 explicitly with `[C*]` instead.

### Locale reality: one byte, one character

GNU `tr` fully supports only *safe single-byte locales*, where every byte is one character. In a UTF-8 locale it is still a byte filter, with predictable consequences — all verified in this book's reference container (`LC_CTYPE=C.UTF-8`):

```
$ printf 'café\n' | tr '[:lower:]' '[:upper:]'
CAFé       # ASCII bytes map fine; é is two bytes (0xC3 0xA9), neither
           # is a member of the single-byte [:lower:] class -> unchanged

$ printf 'eEé\n' | tr '[=e=]' 'X'
XEé        # equivalence class [=e=] contains only 'e' on GNU/glibc
```

The manual's own example: `tr ö Ł` in a UTF-8 encoding is really `tr '\303\266' '\305\201'` — every `0xC3` byte becomes `0xC5` and every `0xB6` becomes `0x81`, mangling any byte sequence that happens to contain them. The documented remedy is also the simplest habit: **`LC_ALL=C tr`** whenever the data is ASCII — which makes ranges literal byte spans (`a-z` = 0x61–0x7A), classes predictable, and behavior identical on every machine.

Range operands inherit another locale dependency: `M-N` expands in *collation order*, so what `a-z` contains can vary by locale (and EBCDIC hosts famously have non-contiguous letters — the manual's counter-example). Prefer `[:lower:]`/`[:upper:]` classes, or `LC_ALL=C`, over hand-written ranges.

### Idioms worth memorizing

```
rot13:        tr 'A-Za-z' 'N-ZA-Mn-za-m'     # self-inverse; apply twice
CRLF -> LF:   tr -d '\r' < win.txt > unix.txt
word-per-line: tr -cs '[:alnum:]' '[\n*]' < doc | sort | uniq -c | sort -rn
NUL -> sep:   tr '\0' '\n' < find-output     # NUL-transparent filter
count bytes:  tr -cd 'a' < file | wc -c      # occurrences of 'a'
scrub binary: tr -cd '[:print:]\n' < mixed.bin
squeeze runs: tr -s ' \t' < table.txt        # per-byte, not mixed-run aware
```

The rot13 set works because the two 13-shifted ranges tile the alphabet: `A-M -> N-Z` and `N-Z -> A-M`. Under `LC_ALL=C` the ranges are plain byte spans; in other locales the same command may map unexpected bytes, which is why the locale section matters even for party tricks.

### A worked trace: one pipeline, every construct

The word-frequency one-liner uses translate, complement, delete, squeeze, and a SET2 repeat in a single `tr` stage. First, what that stage alone does:

```
$ printf 'the quick brown fox jumps over the lazy dog. the end.\n' \
    | tr -cs '[:alnum:]' '[\n*]'
the
quick
brown
...
the
end
```

Reading it against the mode table:

1. `-c` complements SET1: the effective SET1 is every byte except alphanumerics — spaces, periods.
2. Translation maps those bytes to SET2, which is `\n` padded by the `[*]` repeat to SET1's length.
3. `-s` then squeezes runs of the *last specified array* — SET2, the newlines — so `" .  "`-style runs become one `\n` each.
4. Delete (`-d`) is not in play here; had it been (`tr -ds ...`), the SET1 bytes would vanish entirely before the squeeze.

Complete pipeline, ending on `sort | uniq -c | sort -rn`:

```
$ printf 'the quick brown fox jumps over the lazy dog. the end.\n' \
    | tr -cs '[:alnum:]' '[\n*]' | tr 'A-Z' 'a-z' \
    | sort | uniq -c | sort -rn | head -1
      3 the
```

### Diagnostics: operand validation before streaming

Every SET is fully parsed — and every option combination checked — before the first input byte is read, so grammar failures are clean: no partial output, exit 1. The exact diagnostics from this page's experiments:

```
tr: extra operand 'file'                        # third operand; tr takes no files
tr: extra operand 'b'
Only one string may be given when deleting      # -d with SET2 and no -s
tr: when not truncating set1, string2 must be   # translate with empty SET2
    non-empty
tr: invalid character class 'bogus'             # [:bogus:] is not a class
tr: the [c*] repeat construct may not appear    # repeat in SET1
    in string1
```

Two situations are downgraded to *warnings* in recent GNU coreutils and processing continues (exit 0):

```
tr: warning: an unescaped backslash at end of   # SET ends with '\'; the
    string is not portable                      # backslash is ignored
tr: warning: the ambiguous octal escape \400    # \400 overflows a byte:
    is being interpreted as the 2-byte          # parsed as \040 (space)
    sequence \040, 0                            # plus a literal '0'
```

The second warning is worth internalizing: octal escapes are capped at three digits, so an out-of-range value silently splits into an escape plus literal trailing digits — a great way to translate spaces by accident.

## Options That Matter

| Option | Effect |
|---|---|
| `-c`, `-C`, `--complement` | Use the complement of SET1 (identical aliases; both GNU) |
| `-d`, `--delete` | Delete SET1 bytes; no translation; SET2 forbidden unless `-s` also given |
| `-s`, `--squeeze-repeats` | Collapse runs of a byte listed in the LAST specified set to one copy |
| `-t`, `--truncate-set1` | Truncate SET1 to the length of SET2 instead of padding SET2 (GNU extension) |

And the implicit rules that act like options:

- No file operands: input is always stdin, output always stdout.
- `STRING2` is optional only for `-d` or `-s`; for translation it must be non-empty.
- `[C*n]` repeats, `[:class:]`-in-SET2 restrictions, and `[=c=]` positions are grammar constraints, violations of which exit 1 with a specific message.

## Usage Patterns

```bash
# Windows line endings off a log before diffing (delete every CR byte)
tr -d '\r' < report.win.csv > report.unix.csv
```

```bash
# Uppercase a user-supplied code, locale-proof
printf '%s' "$code" | LC_ALL=C tr 'a-z' 'A-Z'
```

```bash
# The portable case conversion spelled with classes
tr '[:lower:]' '[:upper:]' < names.txt
```

```bash
# Collapse every run of spaces and tabs to a single blank in ps output
ps aux | LC_ALL=C tr -s ' ' | cut -d' ' -f1,11
```

```bash
# Squeeze blank lines: runs of newlines become one newline
tr -s '\n' < draft.md
```

```bash
# One word per line, then a frequency count — the tr/sort/uniq trinity
tr -cs '[:alnum:]' '[\n*]' < essay.txt | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head
```

```bash
# Delete everything except digits: phone number normalization
printf 'tel: +1 (555) 010-1234\n' | tr -cd '[:digit:]'
```

```bash
# Scrub non-printing bytes (keep newlines) from a suspicious file
tr -cd '[:print:]\n' < dump.bin > dump.txt
```

```bash
# Delete uppercase letters, then squeeze runs of lowercase to one
tr -ds 'A-Z' 'a-z' < mixed.txt      # 'abABab' -> 'ab'
```

```bash
# Make a NUL-separated stream human-diffable (NUL is an ordinary byte here)
tr '\0' ' ' < blob.raw | od -c | head
```

```bash
# NUL bytes from find -print0 into newlines for eyeballing (lossy, display only)
find . -print0 | tr '\0' '\n'
```

```bash
# Count occurrences of a single byte in a stream (here: field separator)
tr -cd ':' < /etc/passwd | wc -c    # total colons = separators across the file
```

```bash
# rot13 with a self-inverse mapping
printf 'Confidential\n' | tr 'A-Za-z' 'N-ZA-Mn-za-m'
```

```bash
# Translate forbidden filename characters into safe ones, 1:1
printf 'report: final?\n' | tr ':?*' '---'
```

## Nuances and Gotchas

- **`tr` has no file operands.** `tr -d '\r' file` errors with `tr: extra operand 'file'` (exit 1) and does nothing — a habit imported from `sed`. Always redirect.
- **SET2 is padded, not truncated, by default.** `tr 'abc' 'xy'` maps `c -> y` because GNU repeats SET2's last character (BSD behavior); System V and GNU `-t` instead truncate SET1. If you meant to leave `c` alone, you wanted `-t` — and truly portable scripts pad with `[C*]` instead of relying on either.
- **It is a byte filter even in UTF-8 locales.** Accented characters are 2+ bytes and are invisible to `[:upper:]`, `[a-z]`, and `[=e=]`; the manual's `tr ö Ł` example shows byte mangling instead of character translation. Use `LC_ALL=C tr` for ASCII and reach for `sed`, `iconv`, or Perl for real multibyte case mapping.
- **`\xNN` does not exist.** GNU `tr`'s escapes are octal `\NNN` plus the named C escapes; `\x62` parses as literal `x62`. Write `\142` for byte 0x62, or use shell quoting `tr a $'\142'` to keep hex thinking out of the operand.
- **Octal escapes that overflow a byte split silently.** `\400` (octal 256 > 0xFF) is parsed as `\040` (space) plus a literal `0` — with a warning, but the command still runs and builds the wrong set. Only a trailing backslash degrades to the milder end-of-string portability warning; nothing here aborts the run.
- **Unknown escapes are silently literal.** `\q` means `q` (GNU extension, also the way to escape `[` and `-`), so a typo like `\d` for "digit" quietly becomes a byte `d` — the command succeeds and does the wrong thing.
- **`[c*]` repeats are SET2-only**, and brackets never group ranges: `tr -d '[0-9]'` deletes the brackets too. There is no System V bracket syntax in GNU tr.
- **Squeeze is per-byte.** `tr -s '[:space:]'` will not turn a space-tab-newline run into a single character — each byte's run is squeezed independently. For cross-character collapse you need `sed 's/[[:space:]]\+/ /g'` or awk.
- **`-s` targets the last array.** In `tr -s 'a' 'b'` the squeeze applies to `b` (post-translation), not `a` (pre-translation); forgetting this produces "why didn't it squeeze" bug reports.
- **`-c` complements bytes, not characters.** In a UTF-8 world the complement of an ASCII set includes the 0x80–0xFF bytes inside multibyte sequences — `tr -cd '[:alpha:]'` deletes "non-letter" *bytes*, tearing multibyte letters apart. Fine for ASCII data, destructive otherwise.
- **Range operands are collation-ordered.** `M-N` errors if M collates after N (e.g. `tr 'Z-A' x` in some locales), and what a range includes can shift with the locale; `LC_ALL=C` makes ranges deterministic byte spans.
- **Length never changes under pure translation.** There is no way to map one byte to two or to strings — that is `sed`'s job (`s/./XY/`), and it is why "replace every space with `<wbr>`" fails in tr by design.
- **Portability.** `-t`, `-C`, and the GNU repeat/class extensions are not in POSIX; `-c -d -s` and the basic grammar are. BusyBox tr implements the core; scripts for minimal images should pad SET2 explicitly and avoid `-t`.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All input processed and written successfully |
| nonzero (1 observed) | Any error: bad or illegal operand grammar (`[c*]` in SET1, invalid class, empty SET2), extra operands, trailing backslash, read/write failure |

Every failure mode checked on this page exits 1 with a specific `tr:` diagnostic; the info manual only promises "zero indicates success, nonzero indicates failure".

## Related Commands

- [`expand`](./expand.md) — tab-to-space conversion with column arithmetic; the correct tool for alignment jobs `tr`'s 1:1 mapping cannot do.
- [`fold`](./fold.md) — wrap long lines at a width; another length-changing text job outside tr's reach.
- [`sed-awk`](../../shell/sed-awk.md) — `sed`'s `y///` is per-character translation with file operands, addressing, and in-place editing; awk's `gsub` generalizes to strings.
- [`grep`](../../shell/grep.md) — shares the `[:class:]` character-class notation, with the same locale semantics worth knowing.
- [overview](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why does tr have no file arguments, and what happens if you give it one?

Because it is designed as a pure byte filter — a stage in a pipeline, symmetric with cat/grep — not a file editor; that design is what lets it be NUL-transparent and streaming with no buffering semantics. Give it a third operand and it aborts before reading anything: `tr: extra operand 'file'`, exit 1. The fix is always `tr ... < file > out` or embedding it mid-pipeline; there is no in-place mode.

### Q: What does `tr 'abc' 'xy'` output for input `abc`, and why? Name two ways to get only a->x, b->y.

It outputs `xyy`: when SET2 is shorter than SET1, GNU tr (following BSD) extends SET2 by repeating its last character, so `c` maps to `y`. Option 1: `tr -t 'abc' 'xy'` — the GNU `-t` flag truncates SET1 to two bytes, so `c` passes through unchanged (System V behavior). Option 2: pad SET2 explicitly with the repeat construct — `tr 'abc' 'xy[c*]'` — which is also the only portable choice, since POSIX leaves the short-SET2 case undefined.

### Q: Why does `tr '[:lower:]' '[:upper:]'` leave `é` unchanged in a UTF-8 locale?

GNU tr only fully supports single-byte locales; in a UTF-8 encoding `é` is the two bytes 0xC3 0xA9, and neither byte belongs to the single-byte `[:lower:]` class, so both pass through untouched — the ASCII letters around it convert fine. The manual documents this as "GNU tr fully supports only safe single-byte locales" and recommends `LC_ALL=C tr` for ASCII data. For genuine multibyte case mapping you need `sed`, `iconv`, or Perl, not tr. This is also why `-c` complement operations are byte-wise and can shred multibyte characters.

### Q: Write rot13 with tr and explain why the ranges are written that way.

`tr 'A-Za-z' 'N-ZA-Mn-za-m'`. SET1 is `A..Z a..z`; SET2 concatenates `N..Z A..M n..z a..m`, so each range of 13 letters maps onto the other 13 — shifting by 13 twice returns the original, making the command self-inverse. The fragility is the ranges: they expand in the locale's collation order, so on non-C setups the letters inside `A-Z` may not be what ASCII assumed. Ground it with `LC_ALL=C tr` (or use the `[:lower:]`/`[:upper:]` class pair, which cannot express a 13-shift — this is the case where ranges are the right grammar).

### Q: You need every non-printing byte stripped from a mixed text/binary file. Give the command and explain the role of -c and -d.

`tr -cd '[:print:]\n' < mixed.bin > clean.txt`. `-c` complements SET1, so the effective set is "every byte except printable ASCII and newline"; `-d` then deletes those bytes from the stream. The two flags compose into a whitelist: complement the set you want to keep, then delete the rest. The `[:print:]` class is single-byte, so in UTF-8 data this also removes the high bytes of accented characters — for multibyte-safe scrubbing the set must be spelled in terms of the target encoding, usually with a different tool.

### Q: Compare tr with sed's y/// translation command. When is each the better choice?

Both do 1:1 character substitution, and `sed 'y/abc/xyz/'` mirrors `tr 'abc' 'xyz'`. sed wins when you need file operands, in-place editing (`-i`), regex addressing (translate only lines matching a pattern), or translation as one step in a larger substitution pipeline. tr wins on pure filters: it is faster (no regex engine, no line buffering), simpler to reason about, NUL-transparent (sed's line model historically chokes on NUL bytes), and available on minimal systems where only coreutils exist. The interview point is that they are not interchangeable at the edges: tr cannot touch stream length or address lines, and sed's y/// cannot run standalone on a byte stream as cheaply.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/tr.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
