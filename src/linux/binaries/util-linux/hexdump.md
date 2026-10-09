# hexdump — ASCII, decimal, hexadecimal, octal dump of input

## Overview

`hexdump` displays file or stdin data in a choice of formats: canonical hex+ASCII (the famous `-C`), octal/decimal/hex words, or fully custom formats via a mini-language of `-e` format strings. It is the BSD heritage dump tool — the tool people picture when they say "hexdump something" — used for inspecting binary files, protocol payloads, file signatures, and encoding problems.

Debian ships it in the `bsdextrautils` package (built from the util-linux source) at `/usr/bin/hexdump`. Reach for it when you need to see bytes, not lines: checking a magic number, finding BOMs and control characters, diffing two binary files, or decoding wire formats in a pinch. It is often confused with `od` (the POSIX-standard dump, different default format and flags), with `xxd` (the vim-world hex tool with its reversible `-r`), and with the `hd` alias, which is just `hexdump -C`.

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/hexdump |
| First appeared | BSD lineage (4.4BSD-era tool), maintained in util-linux today |
| Standards | None (BSD; `od` is the POSIX counterpart) |

## Synopsis

```
hexdump [options] [<file>...]
```

Common one-line forms:

```
hexdump -C file.bin      # canonical: hex bytes + ASCII sidebar
hexdump -n 64 file       # first 64 bytes only
hexdump -s 512 file      # start at offset 512
hexdump -e '16/1 "%02x " "\n"' file   # custom format
```

## How It Works

### Format selection: the flag ladder

With no format flags, `hexdump` defaults to two-byte hexadecimal words (`-x`-like). Each standard flag is shorthand for a builtin format string:

```
default / -x   two-byte hex words          0000000 6568 6c6c 0a6f
-b             one-byte octal              0000000 150 145 154 ...
-c             one-byte characters         0000000   h   e   l ...
-d             two-byte unsigned decimal   0000000 25960 27756 2670
-o             two-byte octal              0000000 62550 66154 05157
-C             hex bytes + ASCII sidebar   (the canonical format, see below)
```

The multi-byte formats read native-endian shorts: on x86/ARM (little-endian), `hello\n` comes out byte-swapped — `6568` is the bytes `68 65` ("he") read backwards. This is the number-one "hexdump is broken" report; it is not broken, it is words. Use `-C` for byte-granular truth.

### The canonical format, annotated

```
$ printf 'hello\n' | hexdump -C
00000000  68 65 6c 6c 6f 0a                                 |hello.|
00000006
│        │  │  │  │  │  │  │                              │
│        └──┴──┴──┴──┴──┴──┴  hex bytes, 16 per line         │
│                                    ASCII sidebar ─────────┘
└── 8-hex-digit offset (decimal by default; -e can change it)
                                    '.' = non-printable byte
```

Final line = total byte count. Non-printable bytes render as `.`; the classic `hello.` is `hello` plus the newline.

### Duplicate suppression

Identical consecutive output lines are folded into a single `*` to compress long runs:

```
00000010  41 41 41 41 41 41 41 41  41 41 41 41 41 41 41 41  |AAAAAAAAAAAAAAAA|
*
00000030
```

Great for humans, hostile for scripts and byte-level diffs — `-v, --no-squeezing` (sic: the long option) prints every line.

### Custom format strings (`-e`)

Each `-e 'format'` consists of whitespace-separated units: an optional iteration/byte-count pair, a quoted printf-style format, and an optional quoted literal to append after each iteration:

```
16/1 "%02x " "\n"     16 iterations of 1 byte, two-digit hex + space, newline
"[%08_ax] "           address (hex) of the next byte to be printed
8/1 "%_p" " "         printable-ASCII rendering of 8 bytes
4/2 "%04x "           4 iterations of 2-byte words
```

Multiple `-e` units compose; a `\n` in the last unit starts a new line. The escape repertoire includes `%%` (literal %), `%_ax`/`%_ad` (offset hex/decimal), `%_p` (printable), `%_u` (US-ASCII names for control chars).

### A fully self-built canonical dump

The unit grammar can rebuild `-C` by hand — the classic exercise for understanding it:

```bash
$ hexdump -e '"%08_ax  " 16/1 "%02x " "  |" 16/1 "%_p" "|\n"' payload.bin
00000000  68 65 6c 6c 6f 0a                          |hello.|
```

Four units per line-group: an address unit with no byte count (fires once per cycle), 16 single-byte hex iterations with a space each, a once-per-group pipe separator, then 16 printable bytes closed by a pipe and newline. Line breaks come *only* from explicit `\n` — the whole unit list is applied to the same 16-byte chunk before the stream advances, which is exactly why the hex column and the sidebar show the same bytes. Getting the widths to agree (16+16) is the exercise; when they disagree, columns drift out of phase after the first line.

### Offsets and lengths

`-n <length>` stops after N bytes of output input; `-s <offset>` skips ahead first. Offsets accept decimal, `0x` hex, and `b/k/m/g` suffixes (512/1024/1048576/2^30); a leading `+` makes the offset relative to the current position in stdin rather than absolute.

### Multiple file operands are one stream

Like `od`, hexdump concatenates its operands and formats them as a single stream — the offset gutter does not reset between files:

```bash
$ printf abc > a && printf def > b
$ hexdump -C a b
00000000  61 62 63 64 65 66                    |abcdef|
00000006
```

The two files are indistinguishable in the output. If you need per-file dumps, loop over the operands; if you are *expecting* one file, note that a glob expanding to several binaries silently dumps them concatenated, with duplicate suppression possibly folding the boundary.

## Options That Matter

### Format flags

| Option | Effect |
| --- | --- |
| `-b` | One-byte octal display |
| `-c` | One-byte character display |
| `-C, --canonical` | Hex bytes + ASCII sidebar (the everyday choice) |
| `-d` | Two-byte unsigned decimal |
| `-o` | Two-byte octal |
| `-x` | Two-byte hexadecimal (the default) |
| `-e, --format <fmt>` | Custom format unit; repeatable |

### Stream control

| Option | Effect |
| --- | --- |
| `-n, --length <n>` | Interpret only the first N bytes |
| `-s, --skip <offset>` | Skip offset bytes first (suffixes `b/k/m/g`; `+` = relative) |
| `-v, --no-squeezing` | Print all lines; disable `*` duplicate folding |

## Usage Patterns

```bash
# Inspect a file header / magic number
hexdump -C -n 32 image.iso
# 00000000  43 44 30 30 31  ...  |CD001...|

# Find a UTF-8 BOM or CRLF contamination in a "text" file
hexdump -C notes.txt | head -3

# Compare two binaries by their first divergence
cmp -l a.bin b.bin | head          # byte-level; hexdump -C for context

# Decode a fixed-offset field: 4-byte little-endian length at 0x18
hexdump -s 0x18 -n 4 -e '"%08x"' file

# Every byte as two-digit hex, one line per 16 bytes (own canonical layout)
hexdump -e '16/1 "%02x " "\n"' payload.bin

# Printable sidebar only, for strings hidden in binaries
hexdump -e '16/1 "%_p" "\n"' firmware.rom | grep -i password

# Skip a 1 KiB header, show the next 256 bytes
hexdump -C -s 1k -n 256 capture.pcap

# Script-friendly full dump (no '*' folding)
hexdump -v -C blob.bin > blob.hex

# Byte frequency of a file, hexdump doing the byte splitting
hexdump -v -e '1/1 "%02x\n"' data.bin | sort | uniq -c | sort -rn | head

# The hd way (identical to -C)
printf 'hello\n' | hd
```

```bash
# Peek at the GPT header: LBA 1 of a 512-byte-sector disk, magic "EFI PART"
hexdump -C -s 512 -n 96 disk.img
```

```bash
# Native-endian 32-bit words with addresses (firmware/register dumps)
hexdump -e '"%_ax  " 8/4 "%08x " "\n"' regs.bin
```

```bash
# Count newlines without reading the file as text (binary-safe)
hexdump -v -e '1/1 "%02x\n"' stream.bin | grep -c '^0a$'
```

```bash
# Prove a file is all zeros: no output means no nonzero byte
hexdump -v -e '1/1 "%02x\n"' blank.img | grep -v '^00$' | head
```

## Variants

### `hd` — the canonical alias

`hd` is provided alongside `hexdump` and behaves exactly like `hexdump -C` — same output, same options, shorter to type:

```bash
$ printf 'hello\n' | hd
00000000  68 65 6c 6c 6f 0a                                 |hello.|
00000006
```

Debian documents it with its own `hd(1)` man page in the same `bsdextrautils` package. Scripts that want canonical output regardless of host defaults should call `hexdump -C` explicitly (or `hd` where available), never bare `hexdump`, whose default two-byte-word format surprises everyone.

## Nuances and Gotchas

- **The default format byte-swaps.** Bare `hexdump` shows native-endian 2-byte words: `hello` appears as `6568 6c6c 0a6f`. Anyone expecting byte order must use `-C` (or `-b`/`-c`). This is the tool's most common misreading.
- **`*` hides identical lines.** Offsets after a `*` are implied; grepping for a byte pattern in squeezed output fails. Scripts and diffs must pass `-v`.
- **`od` is the portable one.** POSIX defines `od`, not `hexdump`; busybox's `hexdump` supports the common flags but the full `-e` mini-language differs across implementations. For portable scripts, prefer `od -A x -t x1z` or gate on availability.
- **`-s`/`-n` accept `k`/`m`/`g` suffixes but not arbitrary `-e` interplay.** Combining skip/length with custom formats is fine; remember the `+offset` form reads from the *current* stdin position — meaningful only when input is stdin.
- **Offsets are decimal by default** in the printed gutter; format them yourself with `%_ax`/`%_ad` when a tool downstream expects a specific base.
- **Very large files**: hexdump streams, so it is memory-safe, but a full `-v -C` dump of a multi-GB file produces ~10x its size in text — pipe through `head`/`less` or bound with `-n`.
- **`hexdump` output is not reversible.** Unlike `xxd -r`, there is no built-in decode-back path; if you need round-tripping, use `xxd`/`base64`.
- **`%_u` renders control characters as C escapes (`\0`, `\a`)** — handy for protocol analysis, but it is a hexdump extension, absent from `od`.
- **Locale traps.** The ASCII sidebar renders bytes `0x20-0x7e` as-is regardless of locale; multibyte UTF-8 shows as separate `.`-bytes. To *see* UTF-8 text, use `iconv` or `less -U`, not hexdump's sidebar.
- **Custom formats need their own newline.** If no `-e` unit emits `\n`, the entire output is one endless line — the classic bug is adding an address unit and forgetting the closing newline appendix. Keep the `\n` unit last.
- **Squeezing applies to custom output too.** `*` folding happens at the output-line level regardless of `-e`; a parser consuming custom-formatted dump lines still needs `-v` or it will misattribute offsets after any repeated line.
- **`-s` past EOF is a silent success.** `hexdump -s 1G smallfile` prints nothing and exits 0 — a script computing offsets from a wrong sector size gets empty output, not an error. Validate the offset against the file size when scripting.
- **Format flags accumulate rather than replace.** Passing `-C` together with `-e` units runs all the conversions over the same stream; you get both layouts, not a merge. Clean the flag list when scripting generic wrappers.

## Exit Status

- `0` — input processed and dumped successfully (including empty input).
- Nonzero — I/O failure (unreadable file), malformed format string, or bad options.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`look`](./look.md) — sibling BSD-lineage text tool from the same package family.
- [`rev`](./rev.md) — reverses characters per line; pairs with byte-level inspection.
- [`col`](./col.md) — strips reverse linefeeds before you hexdump legacy formatter output.
- [`man-pages`](../../reference/man-pages.md) — reading section-5 formats you are decoding by hand.
- [`regex`](../../shell/regex.md) — patterns for the string extractors built on top of hexdump output.

## Interview Questions

### Q: Why does `printf 'AB' | hexdump` show `4241` instead of `41 42`?

The default format prints native-endian two-byte words, so on little-endian machines the byte pair comes out reversed. It is a word-oriented format, not a bug. For byte-granular output use `hexdump -C`, `-b`, or `-c`; interviewers use this to check whether candidates understand endianness rather than just trusting the tool.

### Q: What does the `*` in hexdump output mean and when is it a problem?

It folds any number of consecutive identical output lines into one line, compressing repetitive binary data. It is a problem whenever output is consumed programmatically — offsets are implied, grep misses content, and binary diffs break. Pass `-v, --no-squeezing` (or `hd -v`) for machine consumption.

### Q: How would you extract the 4-byte little-endian value at offset 0x18 of a binary?

```bash
# Endianness-neutral: read the four bytes individually, decode yourself
hexdump -s 0x18 -n 4 -e '4/1 "%02x" " "' file

# Native-endian shortcut: one 4-byte word, hex
hexdump -s 0x18 -n 4 -e '"%08x\n"' file
```

The key point: `-e` byte counts let you choose 1-byte iteration (endianness-neutral) vs multi-byte words (native order) — know which one your field needs.

### Q: Compare hexdump, od, and xxd: when would you pick each?

`od` is the POSIX-guaranteed tool — choose it for portable scripts (`od -A x -t x1z` approximates `-C`). `hexdump`/`hd` is the BSD-lineage interactive favorite with the friendliest canonical format and a compact `-e` mini-language. `xxd` is reversible (`xxd -r`) and ubiquitous with vim — pick it when the dump must convert back to bytes. All three stream; none should be parsed from squeezed (`*`) output.

### Q: A script greps hexdump output for a string and intermittently fails. Diagnose.

Two likely causes: duplicate-line squeezing (`*`) removed the line containing the match — fix with `-v`; or the match crosses a 16-byte line boundary, so the string never appears contiguous in the sidebar — fix by searching the file directly (`grep -a`) or reformatting with a custom `-e` layout (e.g. 1/1 iteration with no sidebar). Both are classic hexdump-output-parsing bugs.

### Q: Why is hexdump in bsdextrautils on Debian rather than util-linux proper?

Debian groups the BSD-derived utilities (hexdump, hd, col, more, ...) in the `bsdextrautils` package, which since the bsdmainutils consolidation is built *from the util-linux source* — the tools moved between binary packages without leaving the upstream project. It is a packaging fact worth knowing: the binary's man page and its source tree are util-linux even though `dpkg -S` says bsdextrautils.

### Q: Write a hexdump format that prints each line as: 8 bytes in hex, then the same 8 bytes as ASCII.

`hexdump -e '"%_ax  " 8/1 "%02x" " " 8/1 "%_p" "\n"'`. The two counted units both consume the same 8-byte chunk per cycle — that is the core rule making hex-plus-sidebar layouts possible — and the stream advances only after every unit has had its turn on the chunk. The newline must be the appendix of the final unit; put it anywhere else and you either break mid-chunk or never break at all. The exercise tests whether someone understands unit composition versus mere flag recall.

### Q: hexdump or od for a portable script that must parse byte values?

`od` — it is the POSIX tool. `od -An -v -t u1` yields clean decimal tokens with no address gutter, trivially consumed by `while read`/awk; `od -A x -t x1z` approximates the canonical view. hexdump's strengths (`-C`, the `-e` mini-language) are BSD extensions, and BusyBox implements only a subset of the format language — so anything that must run on minimal images or across Unixes writes against od and reserves hexdump for interactive use on full GNU/BSD hosts.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/hexdump.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
