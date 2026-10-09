# cut — extract fields, characters, or bytes from each line of input

## Overview

`cut` slices a fixed portion out of every input line: bytes (`-b`), characters (`-c`), or delimited fields (`-f`). It is the standard tool for "give me column 3 of every line" and the first thing most admins reach for when chewing through `/etc/passwd`, CSV-ish data, `ps` output, or log lines — before they graduate to `awk` for anything fancier.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/cut`, from upstream GNU coreutils. The tool dates to AT&T System III (early 1980s) and is POSIX-standardized; every Unix has it, with GNU adding conveniences (`--complement`, `--output-delimiter`, `-z`) that you must not rely on in portable scripts.

`cut` is deliberately dumb — one delimiter, one selection list, no reordering, no logic. That dumbness is its speed and its limitation. It is often confused with `awk` (full language, regex fields, reordering), `colrm` (column removal by position), and `paste` (the inverse-ish: joins columns). The "why can't cut reorder fields" question is an interview staple, and this page gives the honest answer.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/cut` |
| First appeared / lineage | AT&T System III (1982); BSD and GNU reimplementations since |
| Standards | POSIX.1-2018 (`cut`: `-b`, `-c`, `-f`, `-d`, `-s`, `-n`) |

## Synopsis

```
cut OPTION... [FILE]...
```

Exactly one of `-b`, `-c`, `-f` must be given. Main forms:

```
cut -d: -f1 /etc/passwd          # first colon-field of every line
cut -d, -f2-4,7 data.csv         # several comma fields
cut -c1-8,15- access.log         # fixed-position character slices
cut -b1-16 file.bin              # byte slices (binary-safe with -z care)
cut --complement -d: -f3 file    # everything except field 3
```

With no FILE, or when FILE is `-`, standard input is read.

## How It Works

### One pass, three selection modes

`cut` reads lines and, for each, copies the selected byte/character/field ranges to output in ascending order. The three modes are mutually exclusive — `cut -c1 -f2` fails with "only one type of list may be specified" (the last `-b/-c/-f` wins on repeats):

- `-b LIST` — bytes. Position-defined, binary-safe, locale-free. `1-3` means bytes 1 through 3.
- `-c LIST` — characters. POSIX means "characters", but GNU `cut`'s `-c` has historically been byte-oriented; even under a UTF-8 locale, `cut -c1-2` on `héllo` yields `h` plus the first byte of `é`, splitting the character. Treat `-c` as `-b` in practice and use `awk`/`sed` for character-accurate slicing of multibyte text.
- `-f LIST` — fields, split on the `-d` delimiter (default TAB). Fields are numbered from 1; consecutive delimiters create *empty fields* (`a::b` has field 2 empty — cut does not collapse runs, unlike awk's default whitespace splitting).

### The list grammar — memorize the five forms

The same `LIST` syntax serves all three modes:

```
N      the Nth unit (1-based)
N-M    units N through M inclusive
N-     unit N to end of line
-M     unit 1 through M
N,M-P  comma-joined combinations
```

GNU normalizes the list: order is irrelevant (`-f3,1` behaves like `-f1,3`), overlaps and repeats are collapsed (`-f2,2,1-4` = `-f1-4`). Selection is a *mask*, not a sequence:

```
$ printf 'a:b:c:d\n' | cut -d: -f4,2
b:d                      # ascending, always
$ printf 'a:b:c:d\n' | cut -d: -f2,4
b:d                      # identical output
```

That single observation answers the classic question: **cut cannot reorder fields.** The implementation copies ranges in ascending order — it has no data structure to hold a permutation. If order matters, that is `awk`'s job (`awk -F: '{print $4, $2}'`) or `join`/`paste` round-trips.

### Field mode semantics: the forgiving parts

Two behaviors in `-f` mode are lenient by design, and both surprise people:

1. **Lines with no delimiter are printed whole** (with no delimiter, the "line" is field 1 — the fallback is pass-through, not drop). `-s` / `--only-delimited` suppresses such lines instead.
2. **A missing field is an error-free empty string.** Asking for field 5 of a 3-field line prints an empty line and exits 0 — there is no "field not found" concept.

```
$ printf 'foo:bar:baz\n' | cut -d: -f5
                         # empty line
$ echo $?
0
$ printf 'header\nfoo:bar\n' | cut -d: -f2
header                   # undelimited line printed whole
bar
$ printf 'header\nfoo:bar\n' | cut -sd: -f2
bar                      # -s dropped 'header'
```

### Delimiters: single character, last one wins

`-d` takes exactly one character; `cut -d'ab'` aborts with "the delimiter must be a single character" (exit 1). Repeating `-d` silently takes the last. There is no multi-character, regex, or quoted-CSV delimiter support — for `", "` separators or real CSV quoting rules, use `awk -F', *'` or a CSV-aware tool. Tabs as delimiter: `cut -f` alone already implies tab; use `-d$'\t'` only when also setting `--output-delimiter`.

```
┌────────┐   -b/-c: byte positions      ┌──────────────────────┐
│  line  │ ───────────────────────────> │ selected ranges, in  │
│        │   -f: split on -d (1 char)   │ ascending order, out │
└────────┘   missing fields = empty     │ delimiter: same or   │
                                        │ --output-delimiter   │
                                        └──────────────────────┘
```

### Complement and output delimiter

`--complement` inverts the mask — "all fields except 3" — which is the closest cut gets to deletion. `--output-delimiter=STR` replaces the input delimiter on output (only meaningful with `-f`); a common trick is `--output-delimiter=$'\n'` to explode fields onto separate lines.

## Options That Matter

| Option | Effect |
|---|---|
| `-b, --bytes=LIST` | Select byte positions |
| `-c, --characters=LIST` | Select character positions (byte-oriented in GNU practice) |
| `-f, --fields=LIST` | Select fields split on the delimiter |
| `-d, --delimiter=DELIM` | Field delimiter: exactly one character (default TAB) |
| `-s, --only-delimited` | Drop lines that contain no delimiter (only with `-f`) |
| `-n` | With `-b`: don't split multibyte characters (POSIX no-op in GNU) |
| `--complement` | Invert the selection set |
| `--output-delimiter=STR` | Use STR instead of the input delimiter on output |
| `-z, --zero-terminated` | Lines are NUL-terminated (GNU extension) |

## Usage Patterns

```bash
# Usernames from /etc/passwd - the canonical cut
cut -d: -f1 /etc/passwd
```

```bash
# Username and shell together, pretty-printed
getent passwd | cut -d: -f1,7 --output-delimiter=' -> '
```

```bash
# Everything except the password field (mask inversion)
cut -d: --complement -f2 /etc/passwd | head -3
```

```bash
# Fixed-width log slicing: timestamp column from a formatted log
cut -c1-19 /var/log/syslog | sort -u | tail
```

```bash
# Second column of space-separated output - quote the delimiter!
ps -eo user,comm | cut -d' ' -f1 | sort -u
```

```bash
# CSV: extract fields 2 through 4
cut -d, -f2-4 sales.csv
```

```bash
# Explode a PATH onto separate lines (output-delimiter may be a newline)
printf '%s\n' "$PATH" | cut -d: --output-delimiter=$'\n' -f1-
```

```bash
# Keep only lines that actually have the delimiter (drop comments/headers)
cut -sd, -f1,3 data.csv
```

```bash
# NUL-safe: first field of find's NUL-separated filenames
find . -type f -print0 | cut -z -d/ -f2-
```

```bash
# Byte-level work: chop a fixed 16-byte prefix off every line
cut -b17- firmware.hex
```

```bash
# Intersect with comm: compare the username columns of two passwd files
comm -12 <(cut -d: -f1 a.passwd | LC_ALL=C sort) <(cut -d: -f1 b.passwd | LC_ALL=C sort)
```

```bash
# First 8 bytes of a random token (hex-safe slicing, not base64)
head -c 16 /dev/urandom | basenc --base16 -w 0 | cut -c1-8
```

## Nuances and Gotchas

- **No reordering, ever.** Output is always in ascending list order. `cut -f3,1` prints field 1 then field 3. Scripts that "sort of worked" with reordered lists were silently getting ascending order.
- **Missing fields are empty, not errors.** `cut -d: -f9` on a 3-field line exits 0 with empty output — combined with `set -e` scripts this silently produces nothing. Validate field counts with `awk -F: 'NF<9{print NR}'` when the structure matters.
- **`-s` changes semantics, not just cosmetics.** Without it, undelimited lines pass through; with it they vanish. That is exactly what you want for "drop the header" and exactly wrong when the header was load-bearing.
- **Delimiter is one character, no regex, no CSV quoting.** `cut -d', '` fails; `cut -d' '` collapses nothing — `a  b` (two spaces) makes field 2 empty. Real CSV (quoted commas) breaks cut entirely; use `awk` with `FPAT` or a CSV tool.
- **`-c` is byte-ish.** Multibyte characters get split mid-sequence, producing mojibake or invalid UTF-8 downstream. For UTF-8 columns, `awk '{print substr($0,1,10)}'` handles characters correctly in UTF-8 locales.
- **Whitespace delimiters need quoting and produce empty fields.** `cut -d' ' -f2` on `ps` output full of aligned columns yields empties; either squeeze spaces first (`tr -s ' '`) or use awk's default field splitting, which treats runs of whitespace as one separator.
- **`--complement` with `-f` re-numbers nothing:** it selects the complement mask — with `-d: -f2 --complement` the output still uses the input delimiter; combine with `--output-delimiter` when reformatting.
- **Binary data and cut:** `cut -b` works on bytes and does not require text, but a missing final newline or NUL bytes interact with `-z` and terminal display; checksum or `od` the result when slicing binaries.
- **Portability:** `--complement`, `--output-delimiter`, `-z` are GNU extensions. POSIX only guarantees `-b -c -f -d -s -n`. BusyBox cut implements a subset; scripts for appliances should stick to the POSIX flags.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Input processed (even when selected fields were missing or empty) |
| 1 | Usage error (multiple list types, multi-character delimiter), unreadable file, or write error |

## Related Commands

- [`awk`](../../shell/sed-awk.md) — the general-purpose alternative: reordering, regex fields, per-line logic, arithmetic.
- [`paste`](./overview.md) — merges columns (the column-*joining* counterpart; see the collection overview).
- [`comm`](./comm.md) — set comparisons that typically consume cut's field output.
- [`colrm`](./overview.md) — positional column removal (see the collection overview).
- [`sed-awk`](../../shell/sed-awk.md) — when the delimiter is a regex or fields need transformation.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why can't cut reorder fields, and what's the workaround?

`cut`'s list is a mask: the implementation walks each line once and copies selected ranges in ascending index order — there is no buffer that could hold a permutation, and the POSIX spec fixes ascending output. `-f4,2` therefore prints field 2 then 4. When order matters, use awk (`awk -F: '{print $4":"$2}'`), or two cut passes joined by paste. Recognizing "mask vs permutation" is the interview point.

### Q: A script extracts field 5 with `cut -d: -f5` and downstream JSON assembly emits empty entries for some lines. What's happening and name two fixes?

Those lines have fewer than 5 colon-delimited fields — cut returns the empty string for missing fields and exits 0, so nothing looks wrong to the shell. Fix 1: filter first with `awk -F: 'NF>=5'` (or validate and log bad lines). Fix 2: use awk to do the extraction with a guard (`awk -F: 'NF>=5{print $5}'`), making the structural requirement explicit. The root cause is cut's deliberately lenient field model: missing means empty, never error.

### Q: Explain the difference between cut -f and awk's default field splitting.

cut -f splits on exactly one literal character (default TAB), preserving empty fields between consecutive delimiters — `a::b` has three fields. awk's default splitting treats any run of whitespace (space/tab) as a single separator and ignores leading/trailing whitespace, so empty fields cannot occur. Consequences: for TSV, `cut -f` and awk agree; for space-aligned output like `ps`, cut -d' ' produces phantom empty fields while awk does not; for `a::b`-style data, awk needs `-F:` (which, unlike its default mode, does create empty fields like cut).

### Q: What does -s do and when would it bite you?

`-s`/`--only-delimited` (with -f) suppresses lines that contain no delimiter. It bites in two directions: forgetting it makes header/comment lines pass through as whole-line output mixed into your column data; overusing it silently deletes lines you assumed had data — e.g., a CSV where a malformed row lost its commas now disappears instead of erroring. Defensive practice: pair `-s` with a count check (`cut -sd, -f1 file | wc -l` vs `wc -l < file`).

### Q: Compare cut and awk for extracting column 3 from a 10 GB log. Which and why?

For a hot single-purpose extraction, `cut -d' ' -f3` (or `cut -f3` on TSV) wins: it is a small C program that streams bytes with one delimiter comparison per character and negligible startup, typically several times faster than awk on the same input. awk wins the moment logic appears — filtering, regex delimiters, reordering, aggregation — and `awk '{print $3}'` is fast enough when the condition exists anyway. Also mention `-z` for NUL-safe pipelines and that neither handles quoted CSV.

### Q: Is cut POSIX-standardized, and which popular flags are GNU-only?

Yes — `cut` is in POSIX.1-2018 with `-b`, `-c`, `-f`, `-d`, `-s`, and `-n`. GNU extensions that will break portable scripts on busybox/BSD: `--complement`, `--output-delimiter`, `-z` (NUL-terminated lines), and the tolerance of list quirks like overlaps. A portable script uses only the POSIX six and treats ascending-order output as the contract.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/cut.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
