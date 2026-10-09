# od — octal/byte-level dump of files and streams

## Overview

`od` ("octal dump") is the POSIX-standard tool for looking at data the way the
machine sees it: bytes, with addresses, in any of several numeric and
character formats. It is the original binary inspector of Unix — predating
hex editors, `hexdump`, and `xxd` — and it is still the right answer in
scripts and servers where nothing else is installed. Every byte is rendered,
nothing is summarized: that unambiguous, verifiable view is the point.

It ships in Debian's `coreutils` package at `/usr/bin/od`. You reach for it
when debugging binary file formats, checking what a program actually wrote,
extracting magic bytes for file-type identification, or decoding network
protocol captures by hand. It is often confused with `hexdump` (util-linux
lineage, prettier default, not POSIX) and `xxd` (ships with vim; uniquely able
to *reverse* a hex dump back to binary). `od` is the only one of the three
guaranteed by POSIX and present on minimal systems.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 (User commands) |
| Path | `/usr/bin/od` |
| First appeared / lineage | Early AT&T Unix (1970s, V7-era ancestor `od`) |
| Standards | POSIX.1-2018 |

## Synopsis

```
od [OPTION]... [FILE]...
od [-abcdfilosx]... [FILE] [[+]OFFSET[.][b]]
od --traditional [OPTION]... [FILE] [[+]OFFSET[.][b] [+][LABEL][.][b]]
```

Main forms:

```
od file.bin                          # classic octal dump, 16 bytes per line
od -A x -t x1z file.bin              # canonical hex dump with ASCII sidebar
head -c 8 file | od -An -tx1         # magic bytes only, no address column
od -j 512 -N 64 disk.img             # skip 512 bytes, dump the next 64
```

## How It Works

`od` streams the input (files concatenated in argument order, or stdin),
groups bytes into fixed-size output lines (`-w`, default 16), and formats each
group with the selected type(s). Every line starts with the address of its
first byte in the chosen radix; after the final line, `od` prints one last
address: the offset one past the end of the data — a built-in file-size probe.

```
        bytes from input
  ┌──────────────────────────────────────────┐
  │ 7f 45 4c 46 02 01 01 00 ...              │
  └──────────────────────────────────────────┘
        │  chunk by width (default 16)
        ▼
  0000000 7f 45 4c 46 02 01 01 00  ...
  ▲ address in radix -A (default: octal)
```

### Address radix: -A

`-A d` decimal, `-A o` octal (default), `-A x` hex, `-A n` none. `-An` is the
workhorse when the bytes are all you want:

```bash
$ head -c 8 /usr/bin/od | od -An -tx1
 7f 45 4c 46 02 01 01 00
```

Those are the ELF magic bytes: `7f` `E` `L` `F`, then ELF class/version —
the standard "is this really an executable?" probe.

### Type codes: -t

The `-t TYPE` option is the modern, precise selector. TYPE combines a format
letter and an optional byte size:

| Code | Meaning | Common forms |
|---|---|---|
| `a` | named characters (`del`, `bs`, `nl`) | `-ta` |
| `c` | printable chars, backslash escapes | `-tc` |
| `d` | signed decimal | `-td1`, `-td2`, `-td4`, `-td8` |
| `u` | unsigned decimal | `-tu1` (byte values 0-255) |
| `o` | octal | `-to1`, `-to2` |
| `x` | hexadecimal | `-tx1`, `-tx2`, `-tx4` |
| `f` | floating point | `-tf4` (float), `-tf8` (double) |

Verified examples — note how the same two bytes `41 42` read differently by
type, which is exactly the forensic value of the tool:

```bash
$ printf 'ABCD' | od -tx2                # 16-bit words, little-endian host
0000000 4241
$ printf 'ABCD' | od -td4
0000000  1145258561                # 0x44434241 as one signed int
$ printf 'ABCD' | od -tu1
0000000  65  66  67  68            # 'A'=65 ... 'D'=68
$ printf '\0\0\0\0\0\0@@' | od -tf8      # 8 bytes as an IEEE double
0000000                      32          # a clean 32.0
```

The GNU `z` suffix appends a printable-character sidebar to any hex type —
the canonical forensics view:

```bash
$ printf 'hello' | od -A d -t x1z
0000000 68 65 6c 6c 6f                                   >hello<
0000005
```

Multiple `-t` options stack: `od -tx1 -tc` prints each chunk twice, hex then
characters. The traditional single-letter flags are shorthands — `-b` = `-to1`,
`-c` = `-tc`, `-x` = `-tx2`, `-d` = `-tu2`, `-o` = `-to2`, `-i` = `-tdI`,
`-f` = floats — and they accumulate the same way.

### Duplicate suppression: -v

Runs of identical 16-byte output lines collapse into a single `*`. This keeps
large dumps of zero-filled regions tiny, but it is a trap when you are counting
offsets or parsing output — `-v` disables it:

```bash
$ printf 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' | od -An -tc
   A   A   A   A   A   A   A   A   A   A   A   A   A   A   A   A
*
$ printf 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' | od -v -An -tc   # both lines shown
```

### Offsets: -j, -N, and the old positional syntax

`-j N` skips N input bytes, `-N N` dumps only N bytes. Numbers accept the
same suffixes as elsewhere in coreutils (`K`/`M`), a `0x` prefix for hex, a
`.` suffix for octal, and `b` for 512-byte blocks:

```bash
$ od -j 2 -N 4 -An -tx1 <<< 'abcdef'
 63 64 65 66                             # 'cdef' — skipped 'ab'
```

The second synopsis form is the traditional one: `od file +512` (an offset
operand) or the pre-POSIX flag soup `od -c file`. `--traditional` forces the
third form with the LABEL pseudo-address feature. Prefer the modern options
in anything a human will read next year.

### -w width and --endian

`-w N` sets bytes per output line (e.g. `-w4` to align a dump with 32-bit
words). `--endian=big|little` byte-swaps input units, letting you read
big-endian file formats on a little-endian x86 without hand-swapping:

```bash
$ printf 'ABCD' | od --endian=big -td4
0000000 1094861636                       # 0x41424344, not 0x44434241
```

## Options That Matter

| Option | Effect |
|---|---|
| `-A RADIX` | Address radix: `d`, `o` (default), `x`, `n` |
| `-t TYPE` | Output format(s): `a c d f o u x` plus size (`x1`, `d4`, `f8`) and `z` sidebar |
| `-j BYTES` | Skip BYTES input bytes first (supports `0x`, `.`, `b`, `K`/`M` suffixes) |
| `-N BYTES` | Limit the dump to BYTES input bytes |
| `-v` | Do not collapse duplicate lines into `*` |
| `-w[N]` | Bytes per output line (default 16; bare `-w` = 32) |
| `-S[N]` | Output only NUL-terminated strings of at least N (default 3) printable chars |
| `--endian=big\|little` | Swap input bytes for multi-byte units |
| `-b -c -d -f -i -l -o -s -x` | Traditional shorthand types (note: `-s` here means signed 2-byte, *not* strings) |

## Usage Patterns

```bash
# Identify a file by magic bytes — no file(1) needed
head -c 4 unknown.bin | od -An -tx1     # 89 50 4e 47 = PNG; 1f 8b = gzip
```

```bash
# Canonical forensics view: hex + addresses + ASCII sidebar
od -A x -t x1z suspicious_attachment > dump.txt
```

```bash
# Inspect a file-format header field: 4-byte little-endian length at offset 4
od -A d -j 4 -N 4 -t u4 frame.bin
```

```bash
# Check exactly what bytes a program wrote (trailing NUL? CRLF? BOM?)
printf '%s\n' "$VALUE" | od -An -tx1
```

```bash
# Find a byte-offset into a large file for later -j jumps
grep -abo 'MAGIC' image.raw              # then: od -j OFFSET -N 32 image.raw
```

```bash
# Extract printable strings with offsets — POSIX answer to strings(1)
od -A d -S 6 core.dump | head
```

```bash
# Verify a binary patch: compare regions of two files at the same offset
od -A x -j 4096 -N 16 -t x1 v1.bin > a; od -A x -j 4096 -N 16 -t x1 v2.bin > b; diff a b
```

```bash
# Debug terminal weirdness: show control characters by name
printf 'col1\tcol2\r\n' | od -t a
```

```bash
# Round-trip check that a copy is byte-identical, then show the first divergence
cmp a.img b.img || od -A d -j $(( $(stat -c%s a.img) / 2 )) -N 32 -t x1z a.img
```

```bash
# Double-check a checksum tool's input: dump the exact bytes being hashed
cat payload | tee >(od -An -tx1 | md5sum) | md5sum
```

```bash
# Read a big-endian 32-bit field from a network capture header
od -A d -N 4 -t x1 --endian=big packet.bin
```

## Nuances and Gotchas

- **Endianness is a display illusion.** `-tx2`/`-td4` format multi-byte units
  in host byte order — `printf 'AB' | od -tx2` shows `4241` on x86. Nothing in
  the file changed; use `-tx1` when you mean raw bytes, or `--endian=` when
  you mean a specific file-format byte order.
- **`-s` is not "strings" in `od`.** Traditional `-s` means signed 2-byte
  decimals. Strings are `-S`/`--strings`. This bites everyone coming from
  `hexdump -s` (offset) or `strings(1)`.
- **`*` hides data.** Duplicate-line suppression means naive `od` parsers miss
  bytes and miscount addresses. Always pass `-v` when output feeds another
  program; keep the suppression only for eyeballing.
- **The default is octal.** `od file` without `-t` prints octal 2-byte units —
  historically faithful, useless for modern hex-oriented work. Say `-t x1`
  explicitly unless you enjoy translating `141 142 143`.
- **`-tc` renders `\n` and friends as escapes** but the `a` type names them
  (`nl`, `cr`, `del`); pick per consumer. Both operate on the high-bit-stripped
  view only in the `a` type — `-ta` *ignores* the 8th bit, another surprise.
- **The final address line is not data.** Scripts that slurp all output must
  drop the last line; it is the end offset, present even with `-An` (one bare
  offset line).
- **od vs hexdump vs xxd:** `hexdump -C` gives the same canonical layout with
  less typing (Debian: `bsdextrautils`/util-linux family, not POSIX); `xxd`
  is the only one that *reverses* (`xxd -r` rebuilds binary from dump text)
  and ships with vim; `od` is the POSIX-portable baseline found on every
  minimal container. For files under a few hundred KB, any of them works;
  for pipelines on servers, `od` is the one you can bet on.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Trouble: unreadable input, bad option or type specification |

## Related Commands

- [`tr`](./tr.md) — transform the same byte stream; pair `od` before and after to prove the change
- [`split`](./split.md) — `-b` slices binary input into byte-sized pieces od can inspect
- [`tac`](./tac.md) — record-reversal companion for log-style dumps
- [`overview`](./overview.md) — the coreutils collection hub
- [`../../internals.md`](../../internals.md) — how bytes map to files, inodes, and formats underneath

## Interview Questions

### Q: Why is od still shipped everywhere when hexdump and xxd exist?

POSIX guarantees it, coreutils ships it, and it runs on minimal containers and
rescue systems where util-linux extras and vim are absent. Its output format
is stable across decades, which makes it the tool for scripts that must parse
their own dumps. hexdump is prettier and xxd can reverse, but neither is a
safe portability assumption.

### Q: You dump a PNG header and see `89504e47 0d0a1a0a`. What just happened, and why is it meaningful?

You read the PNG magic number: `89 50 4e 47` (`\x89` + "PNG") followed by
`0d 0a 1a 0a`. It is meaningful twice over: it proves file-type identification
works from the first 8 bytes (the `\x89` high bit catches 7-bit-mangling
transfers, the `1a` catches lost trailing newlines), and it demonstrates that
od's hex view catches bytes no text tool would show you.

### Q: Explain the duplicate-line suppression and when it becomes dangerous.

`od` collapses consecutive identical output lines into a single `*` to keep
dumps of padded or zero-filled regions readable. It is dangerous whenever the
dump is consumed by a script: offsets can no longer be derived by counting
lines, and byte counts change silently. The fix is `-v` ("output duplicates")
in any mechanical context.

### Q: How do you inspect a specific 32-bit little-endian integer at offset 4096 of a disk image?

`od -A d -j 4096 -N 4 -t u4 disk.img`. `-j` seeks past 4096 bytes, `-N 4` reads
exactly the 4-byte field, `-t u4` formats it as one unsigned 32-bit unit in
host order. If the format were big-endian (network order), add `--endian=big`
instead of eyeballing swapped bytes. Know the `-j`/`-N`/`-t` trio — it is the
whole file-format-forensics workflow in one command.

### Q: What does the trailing line of od output mean, and why is it there?

The last line is a lone address — the offset one past the final byte dumped.
It exists so the dump is self-describing: the difference between the last
data address and that final address gives the byte count, and the address
itself doubles as a file-size probe (`od -An file | tail -1`). Tools that
parse od output must special-case it.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/od.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
