# pr — paginate and columnate text files for printing

## Overview

`pr` prepares plain text for a line printer: it slices input into pages of a fixed line length, writes a page header (date, title, page number) on each one, and can arrange the text in multiple columns. It never talks to a printer itself — it is a pure text filter whose output you would traditionally pipe to `lp` or `lpr`. The defaults encode 1980s hardware: a page is 66 lines (an 11-inch fanfold sheet at 6 lines per inch) and 72 characters wide.

Two things keep `pr` on modern systems despite the death of the line printer. First, it is a POSIX-standard tool with a very compact grammar for columnating text — `pr -t -3` is the fastest way to pour a list into three columns. Second, its `-m` mode merges several files side by side, which remains a handy poor-man's comparison view.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/pr`, from upstream GNU coreutils. It is frequently confused with `nl` (line numbering — `pr -n` overlaps it), with `fold` (which wraps long lines instead of truncating them), and with the actual print spoolers (`lp`, `lpr`), which do the hardware part `pr` deliberately leaves out.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/pr` |
| First appeared / lineage | Version 7 UNIX (1979); BSD and System V lineages, GNU implementation in coreutils |
| Standards | POSIX.1-2018 (`pr`) |

## Synopsis

```
pr [+FIRST_PAGE[:LAST_PAGE]] [-COLUMN] [OPTION]... [FILE]...
```

Main forms:

```
pr -t -3 FILE            # three columns, filled down the page, no header
pr -t -a -3 FILE         # three columns, filled across, no header
pr -l 60 -h TITLE FILE   # print-style pages with a custom centered title
pr -m FILE1 FILE2        # several files merged in parallel columns
pr +2:5 -l 50 FILE       # only pages 2 through 5
```

With no FILE, or when FILE is `-`, input is read from standard input.

## How It Works

### Anatomy of a page

By default a page is `PAGE_LENGTH` (66) lines tall. The first 5 lines form the header block and the last 5 lines are the trailer; what remains is text. With `-F` (form feed), pages are separated by a form feed character, the header shrinks to 3 lines, and there is no trailer.

```
$ pr -l 20 /tmp/pr12.txt | cat -A | head -8
$
$
2026-10-09 11:04                  /tmp/pr12.txt                   Page 1$
$
$
alpha$
bravo$
```

Reading the anatomy out of that output (the date is the run time, so it varies):

```
line 1-2   blank
line 3     <date/time>   <centered title>          Page <N>
line 4-5   blank
line 6..   text (PAGE_LENGTH - 10 lines by default; 56 of 66)
last 5     blank trailer padding the page to exactly PAGE_LENGTH
```

The title defaults to the input file name. For standard input there is no name, so the center of the header stays blank. The date is the *current* date and time, not the file's mtime; `-D FORMAT` overrides it with a strftime format string.

### Column modes

`-COLUMN` (a bare number, e.g. `-3`) produces that many columns. By default lines are distributed *down* each column first; `-a` fills *across* instead; `-m` merges whole files, one file per column:

```
$ pr -t -3 /tmp/pr12.txt          # down: 12 lines become 4 rows of 3
alpha			echo			india
bravo			foxtrot			juliet
charlie			golf			kilo
delta			hotel			lima

$ pr -t -a -3 /tmp/pr12.txt       # across: consecutive lines share a row
alpha			bravo			charlie
delta			echo			foxtrot
golf			hotel			india
juliet			kilo			lima
```

With `-t` the header/trailer machinery is switched off, which is the form you almost always want when using `pr` as a columnator rather than a paginator.

Column separators and truncation interact in a way that surprises people:

- In multi-column output, lines are truncated at the page width (`-w`, default 72; `-W` sets it unconditionally).
- `-s[CHAR]` replaces the padded columns with a single separator character (TAB by default) *and turns truncation off*.
- `-J` joins full lines (no column alignment, no truncation), typically with `-S STRING` as separator.

```
$ printf 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\n' \
    | pr -t -W 20 | cat -A
abcdefghijklmnopqrst$          # silently cut at 20 columns
```

### Pagination control

`+FIRST_PAGE[:LAST_PAGE]` selects a page range of the *paginated* output — the header itself confirms the page number:

```
$ seq 1 100 | pr +2 -l 20 | head -4


2026-10-09 11:04                                                  Page 2
```

(No title appears because the input came from a pipe.) `-F` emits a form feed between pages instead of padding with blank lines; `-T` additionally ignores form feeds already present in the input.

One interaction to memorize: **a page length of 10 or less implies `-t`** — the header vanishes. People set `-l 10`, wonder where the header went, and blame everything else.

### Numbering and spacing

`-n[SEP[DIGITS]]` prefixes each text line with a line number — 5 digits wide, followed by TAB unless you supply a separator character (`-n:` gives `1:`). With multiple columns, numbering continues down each column. `-N` shifts the starting number, `-d` double-spaces, `-o MARGIN` indents every line, and `-e`/`-i` expand or restore tabs.

```
$ printf 'one\ntwo\n' | pr -n: -t | cat -A
    1:one$
    2:two$
```

## Options That Matter

| Option | Effect |
|---|---|
| `+FIRST[:LAST]` | Begin (stop) printing at the given page; header shows the real page number |
| `-COLUMN` | Number of text columns, filled down; `-a` fills across; `-m` merges files in parallel |
| `-a` | Fill columns across (row-major) instead of down |
| `-m` | Print all files in parallel, one per column |
| `-l LINES` | Page length (default 66; text area = length − 10; length ≤ 10 implies `-t`) |
| `-h HEADER` | Centered page title instead of the file name; `-h ""` prints a blank line |
| `-t` | Omit header and trailer entirely (the "just columnate" switch) |
| `-T` | Also ignore form feeds present in the input |
| `-F`, `-f` | Separate pages with form feeds; 3-line header, no trailer |
| `-D FORMAT` | strftime format for the header date |
| `-d` | Double-space the output |
| `-n[SEP[DIGITS]]` | Number lines (5 digits, TAB separator by default) |
| `-N NUM` | First line number on the first page |
| `-o MARGIN` | Indent each line by MARGIN spaces |
| `-s[CHAR]` | Single-character column separator (TAB default); disables truncation |
| `-S STRING` | Column separator string; pairs with `-J` |
| `-J` | Merge full lines; no truncation, no column alignment |
| `-w WIDTH` | Page width for multi-column output (default 72) |
| `-W WIDTH` | Page width always; truncates long lines |
| `-r` | Omit the warning when a file cannot be opened (exit status stays 1) |
| `-v`, `-c` | Show non-printing characters (octal / hat notation) |

## Usage Patterns

```bash
# Pour a word list into 3 balanced columns, no header noise
pr -t -3 /usr/share/dict/words 2>/dev/null | head
```

```bash
# Across-fill when reading order matters: item 1,2,3 on row one
pr -t -a -4 candidates.txt
```

```bash
# Print-style pages for a report, custom title, 58-line page
pr -l 58 -h "Q3 Sales Report" report.txt | lp -d office
```

```bash
# Side-by-side merge of two short files for eyeball comparison
pr -m -t -w 100 old.conf new.conf
```

```bash
# Numbered output where the number is part of the layout, not the text
pr -t -n: -3 roster.txt
```

```bash
# Extract just pages 3-4 of a long paginated document
pr +3:4 -l 50 manual.txt
```

```bash
# Double-spaced, 4-space indent manuscript draft
pr -d -t -o 4 draft.txt
```

```bash
# Narrow terminal: two columns of 40 characters with visible separator
pr -t -2 -s'|' -W 80 team.txt
```

```bash
# Merge three files in parallel columns, never truncate, tab between them
pr -m -t -J -S $'\t' a.txt b.txt c.txt
```

```bash
# Form-feed separated pages for a troff/Groff downstream consumer
pr -F -l 60 -h MEMO memo.txt
```

```bash
# Deterministic columnation of command output for a screenshot or report
kubectl get pods --no-headers -o name | pr -t -2
```

```bash
# Sanity-check how pr splits your data before piping it on
pr -t -3 data.txt | head -5
```

## Nuances and Gotchas

- **Page length ≤ 10 silently implies `-t`.** `-l 10` (or less) switches the header off; there is no warning. If you are tuning `-l` to make the header fit somewhere, jump straight past 10.
- **Multi-column output truncates at 72 columns by default.** Long lines are cut without any marker (verified: `-W 20` just drops the tail). That is data loss if you pipe the output onward. Use `-s` (separator mode turns truncation off) or `-J` (join lines) whenever the content matters more than the grid.
- **The header date is the current date/time, not the file's.** Anyone parsing `pr` output for a timestamp gets the moment of printing. `-D` fixes the format, not the semantics.
- **`-h ""` needs the separated argument.** `-h ""` prints a blank title line; `-h""` is parsed as no header option argument and consumes your next argument (the help text explicitly warns about it).
- **Piped input has no title.** The centered header field comes from the file name; from stdin it is blank. Give `-h` a title if the output must be self-describing.
- **`-r` silences the warning but not the failure.** `pr -r nofile` prints nothing and still exits 1 — scripts checking `$?` are safe, scripts checking stderr are not.
- **Portability.** BSD/macOS `pr` is a different implementation with divergent behavior in edge options; busybox builds usually omit `pr` entirely. The POSIX core (`-l`, `-h`, `-t`, `-COLUMN`, `-a`, `-m`, `-d`, `-n`, `-o`, `-s`, `-w`, `+page`) behaves the same everywhere; GNU extensions (`-D`, `-S`, `-J`, `-W`, `-N`, `-T`, `-F` semantics) may not.
- **Column balancing.** With `-COLUMN`, `pr` balances the columns so each is roughly equal; with `-a` it does not pad short rows. Mixing up the two modes is a classic "why is my data transposed" bug.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All requested pages produced successfully |
| 1 | At least one input file could not be opened (warning suppressed by `-r`, exit code unchanged) |

## Related Commands

- [`nl`](./nl.md) — richer line numbering; `pr -n` is the print-layout variant of it
- [`fold`](./fold.md) — wraps long lines to a width instead of truncating them
- [`fmt`](./fmt.md) — reflows paragraphs to a target width before columnating
- [`cat`](./cat.md) — plain concatenation, no pagination or columns
- [`paste`](./paste.md) — juxtaposes lines from multiple files line-by-line (vs `pr -m`'s column filling)
- [`cut`](./cut.md) — extracts columns of a different kind: character/field positions
- [`csplit`](./csplit.md) — splits a file into pieces at content boundaries
- [`sed-awk`](../../shell/sed-awk.md) — awk can emit columnar output programmatically when `pr`'s fixed grid is not enough
- [`overview`](./overview.md) — GNU Coreutils collection hub

## Interview Questions

### Q: What does default `pr` output actually look like — how many lines does the header take, and where does the text start?

The header block is five lines: two blanks, one header line (left: date/time, center: title — the file name by default, right: `Page N`), two blanks. With the default page length of 66 that leaves 56 lines of text, and the page is padded to exactly 66 with a blank trailer. With `-F` the header is three lines, pages end at a form feed, and there is no trailer. Text lines beyond the width (72 by default for columns) are truncated unless `-s` or `-J` disables truncation.

### Q: Why does `-l 10` make the header disappear?

A page length of 10 or less implies `-t`, so headers and trailers are omitted entirely. It is documented behavior, not a bug — a page too short to hold a 5-line header plus meaningful text is treated as "no pagination wanted". The practical consequence is that scripts which shrink `-l` for quick tests silently lose the header they were debugging.

### Q: How do `-COLUMN`, `-a -COLUMN`, and `-m` differ?

`-COLUMN` fills columns down: the input is split into N vertical slices and the first slice occupies column one. `-a -COLUMN` fills across: consecutive input lines share a row, which preserves reading order. `-m` is different again — it takes several *files* and prints one per column, line k of each file forming row k, like a manual side-by-side diff. Choosing wrongly transposes or interleaves your data.

### Q: `pr` is from the line-printer era — give a realistic modern use.

Fast, dependency-free columnation and pagination of plain text: turning a long list into N balanced columns (`pr -t -3`), producing numbered side-by-side output (`pr -m -t -J`), or slicing a paginated report into specific pages (`+3:4`). It also still appears in build pipelines that emit printable reports. Knowing its page anatomy (66/56/72) matters mainly so you can recognize and undo its effects when it shows up uninvited in output.

### Q: How does `pr` interact with long lines in multi-column mode, and how do you avoid losing data?

In `-COLUMN` mode, lines are truncated at the page width (72 by default) so the columns align. Three escapes: `-s[CHAR]` switches to a one-character separator and disables truncation; `-J` merges full lines with no column alignment (combine with `-S` for the separator string); or raise `-W`/`-w` to a width large enough for the longest line. For lossless transformations prefer `fold`/`fmt` upstream or awk downstream; `pr` is a formatter, not a safe transformer.

### Q: You see paginated output with `Page 2` in the header but you wanted content starting at line 50. What happened?

You used `+2`, which selects page 2 of the paginated stream — with a 66-line page that is text lines 57–112, not 50. Page selection works in pages, not lines: `+FIRST[:LAST]` with the effective page geometry (length minus the 10 header/trailer lines). To start at a specific line, filter with `sed -n '50,$p'` or `tail -n +50` first, then paginate.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/pr.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
