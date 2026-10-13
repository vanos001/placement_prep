# basenc — the unified binary-to-text encoder (base64/32/16/2, URL-safe, z85)

## Overview

`basenc` is GNU coreutils' "one encoder to rule them all": a single binary that performs base64, URL/filename-safe base64, standard base32, extended-hex base32, base16 (hex), two bit-string encodings, and ZeroMQ's z85 — selected by long option. Each `--baseXX` mode matches the equivalent RFC 4648 encoding exactly, so `basenc --base64` produces byte-identical output to `base64`.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/basenc`, from upstream GNU coreutils. It was added to coreutils (8.22 era, 2013) precisely because the alphabet zoo was growing — `base64`, `base32`, `md5sum`-style hex dumps, `xxd -b` bit strings, z85 — and scripting against five different tools with five different flag styles was error-prone.

Reach for `basenc` when you need an alphabet that the standalone tools do not offer: URL-safe base64 (`--base64url`), extended-hex base32 (`--base32hex`), raw hex (`--base16`), or z85. For plain base64/base32 the standalone binaries do the same job with shorter commands. It is often confused with `xxd` (hex editor/dumper with its own flag universe) and with OpenSSL's `base64` subcommand.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/basenc` |
| First appeared / lineage | GNU coreutils 8.22 (2013); consolidates RFC 4648 encodings plus z85 |
| Standards | RFC 4648 (sections 4–8), ZeroMQ Z85 spec; not in POSIX |

## Synopsis

```
basenc [OPTION]... [FILE]
```

Main forms:

```
basenc --base64 file.bin            # classic base64
basenc --base64url -w 0 file.bin    # URL-safe alphabet, single line
basenc --base32hex -d data.txt      # decode extended-hex base32
basenc --base16 < file.bin          # hex encode (like xxd -p output)
```

With no FILE, or when FILE is `-`, input is read from standard input. Output goes to standard output.

## How It Works

### One binary, seven alphabets

The tool reads the input in binary, applies the selected encoding, and prints text. The alphabet table is the whole story:

| Option | Alphabet | Chars per bytes | RFC |
|---|---|---|---|
| `--base64` | `A–Z a–z 0–9 + /` | 4 : 3 | 4648 §4 |
| `--base64url` | `A–Z a–z 0–9 - _` | 4 : 3 | 4648 §5 |
| `--base32` | `A–Z 2–7` | 8 : 5 | 4648 §6 |
| `--base32hex` | `0–9 A–V` | 8 : 5 | 4648 §7 |
| `--base16` | `0–9 A–F` | 2 : 1 | 4648 §8 |
| `--base2msbf` | `0` `1`, MSB first | 8 : 1 | — |
| `--base2lsbf` | `0` `1`, LSB first | 8 : 1 | — |
| `--z85` | ZeroMQ 85-char set | 5 : 4 | Z85 spec |

```
$ printf 'foobar' | basenc --base64
Zm9vYmFy
$ printf 'foobar' | basenc --base16
666F6F626172
$ printf 'foobar' | basenc --base32hex
CPNMUOJ1E8======
$ printf 'foobar' | basenc --base2msbf
011001100110111101101111011000100110000101110010
```

The two base2 variants encode the same bits in opposite order per byte — `--base2msbf` prints each byte most-significant-bit first (how humans write binary), `--base2lsbf` least-significant first (how some hardware documentation and serial protocols order bits). Comparing the two outputs of the same file is a quick way to debug endianness-of-bits questions:

```
$ printf 'abcd' | basenc --base2msbf
01100001011000100110001101100100
$ printf 'abcd' | basenc --base2lsbf
10000110010001101100011000100110
```

### z85 — the compact outlier

z85 packs 4 bytes into 5 printable characters (85^5 ≈ 2^32), giving only 25% expansion — better than base64 — with an alphabet chosen to be safe in JSON, XML, and source code. Its asymmetry is a favorite gotcha: **encode requires input length ≡ 0 (mod 4); decode requires input length ≡ 0 (mod 5)**. There is no padding character, so lengths must line up exactly:

```
$ printf 'abcd' | basenc --z85
vpA.S
$ printf 'HelloZ' | basenc --z85        # 6 bytes: not a multiple of 4
basenc: invalid input (length must be multiple of 4 characters)
```

### Wrap, decode, and error model

Everything behaves like `base64`/`base32`: output wrapped at 76 columns by default (`-w 0` disables), `-d` decodes, newlines are tolerated on decode, other junk is fatal unless `-i` is given. Padding is emitted exactly as the underlying RFC specifies (base64: `=`; base32: up to six `=`; base16 and base2: none; z85: none).

## Options That Matter

### Encoding selection (mutually exclusive; last one wins on the command line)

| Option | Effect |
|---|---|
| `--base64` | Same as the `base64` program |
| `--base64url` | File- and URL-safe base64 (`-` `_` instead of `+` `/`) |
| `--base32` | Same as the `base32` program |
| `--base32hex` | Extended-hex base32 (`0–9 A–V`); sorts numerically |
| `--base16` | Hex, uppercase, no prefix |
| `--base2msbf` | Bit string, most significant bit first |
| `--base2lsbf` | Bit string, least significant bit first |
| `--z85` | ZeroMQ z85; strict length rules, no padding |

### Common options

| Option | Effect |
|---|---|
| `-d`, `--decode` | Decode input back to binary |
| `-i`, `--ignore-garbage` | When decoding, discard non-alphabet characters |
| `-w`, `--wrap=COLS` | Wrap after COLS chars; `0` disables (default 76) |
| `-z`, `--zero` | End output lines with NUL instead of newline |

Note the naming trap: there is **no `--base2` option** — the long option is ambiguous and the tool refuses it:

```
$ basenc --base2 </dev/null
basenc: option '--base2' is ambiguous; possibilities: '--base2msbf' '--base2lsbf'
```

## Usage Patterns

```bash
# URL-safe token from random bytes (safe in query strings and filenames)
head -c 18 /dev/urandom | basenc --base64url -w 0
```

```bash
# Hex encode exactly like `xxd -p | tr -d '\n'` but uppercase and padded-free
basenc --base16 -w 0 < firmware.bin
```

```bash
# Decode hex back to bytes (handy for reconstructing binary from logs)
printf 'deadbeef' | basenc --base16 -d | od -An -tx1
# de ad be ef
```

```bash
# base32hex when the encoded value must sort in numeric order
printf 'foobar' | basenc --base32hex
# CPNMUOJ1E8======
```

```bash
# Round-trip check any alphabet: encode then decode, compare with original
printf 'payload' | basenc --base64url | basenc --base64url -d
# payload
```

```bash
# Show the bit pattern of a file header (msb-first) for protocol debugging
head -c 4 /bin/ls | basenc --base2msbf
# ELF magic: 01111111010001010100110001000110  (0x7F 'E' 'L' 'F')
```

```bash
# Compact 25%-overhead embedding when input is a multiple of 4 bytes
basenc --z85 -w 0 < block4k.bin
```

```bash
# Same data through every alphabet - verify size cost per encoding
printf 'the quick brown fox' > /tmp/s
for enc in base64 base64url base32 base32hex base16 base2msbf; do
  printf '%-10s %s bytes\n' "$enc" "$(basenc --$enc /tmp/s | wc -c)"
done
```

```bash
# Decode a wrapped, multi-line base64 stream (newlines are free)
basenc --base64 -d < wrapped.b64 > payload.bin
```

## Nuances and Gotchas

- **`--base2` does not exist.** It is a deliberately ambiguous abbreviation; use `--base2msbf` or `--base2lsbf`. Scripts that guess the option name fail with an ambiguity error, not a decode mistake — at least it fails loudly.
- **z85 length rules are asymmetric and unforgiving.** Encode: input must be a multiple of 4 bytes. Decode: input must be a multiple of 5 characters. No padding exists to fix a mismatch; you must align data upstream. Most "z85 produces garbage" bugs are off-by-a-few-bytes inputs.
- **base16 output is uppercase.** `basenc --base16` prints `666F...` — byte-for-byte different from `xxd -p` lowercase output even though the information is identical. Compare hex values case-insensitively or normalize with `tr 'A-F' 'a-f'` first.
- **`--base64url` changes bytes, not just safety.** `-` and `_` sort differently from `+` and `/`; two encodings of the same data compare unequal as strings. Always decode before comparing or hashing.
- **Decoding mixed alphabets fails or corrupts.** There is no autodetection. Feeding base64url text to `basenc --base64 -d` either errors (on `-`/`_`) or, with `-i`, silently drops characters producing wrong bytes.
- **Padding differs per mode.** base64 pads to 4, base32 to 8, base16/base2/z85 never pad. Token generators that "trim the `=`" must remember decode requires the padding back.
- **Portability.** `basenc` is GNU-specific. BusyBox and BSD systems generally lack it; scripts using it should check availability (`command -v basenc`) or restrict themselves to `base64`, which is more universal.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Encode or decode completed successfully |
| 1 | Invalid input, bad option combination, unreadable file, or write error |

## Related Commands

- [`base64`](./base64.md) — the standalone classic encoder (`basenc --base64` is equivalent).
- [`base32`](./base32.md) — the standalone base32 encoder (`basenc --base32` is equivalent).
- [`cat`](./cat.md) — the other "pass data through a transform" filter in this family.
- [`cksum`](./cksum.md) — digests; pair with an encoder to embed checksums in text protocols.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why did coreutils add basenc when base64 and base32 already existed?

Because the encoding alphabet zoo kept growing and each standalone tool would need its own flags, docs, and maintenance. basenc centralizes the alphabet choice in one long option, guarantees identical wrap/decode behavior across alphabets, and adds encodings (base64url, base32hex, base16, base2, z85) that did not justify standalone binaries. It is an API-design answer as much as a tools answer.

### Q: What is the practical difference between --base32 and --base32hex?

Alphabet and sort order. `--base32` uses `A–Z 2–7` (RFC 4648 §6); `--base32hex` uses `0–9 A–V` (§7), which maps each 5-bit value to a character in ascending order — so lexicographic sort of the encoded text equals numeric sort of the underlying values. That property matters for databases, DNS-adjacent tooling, and any place binary-sorted encoded keys are required. The two alphabets are not interchangeable.

### Q: A pipeline emits z85 to a service that replies "length must be multiple of 5". What happened?

The service is trying to decode, and z85 decode requires the encoded text length to be a multiple of 5 (5 chars per 4 bytes, no padding). The pipeline probably fed data whose original length was not a multiple of 4, so the encoder output (or an error message) leaked through, or something stripped/added characters downstream. Fix the upstream alignment — pad the input to a 4-byte boundary with a defined scheme — because z85 has no padding mechanism of its own.

### Q: Which encoding from basenc would you pick to embed a 2 KB binary blob inside a JSON string, and why?

`--base64url`: the alphabet (`A–Z a–z 0–9 - _`) needs no JSON escaping, unlike standard base64 whose `+` and `/` are fine in JSON but whose embedded `=` padding and case sensitivity can interact badly with URL/form layers downstream. Expansion is 33%. base32 (60%) and z85 (25%) are the compactness extremes; z85 needs 4-byte alignment which a 2 KB blob satisfies (2048 = 512×4), making z85 a legitimate smaller alternative if the consumer speaks z85.

### Q: How do the two base2 modes differ, and when does anyone care?

`--base2msbf` prints each byte most-significant bit first; `--base2lsbf` least-significant first. Same bytes, mirrored bit order per byte. It matters when reading hardware datasheets, serial protocol captures, or CRC documentation that specify "bit 0 first" — encoding a known byte pattern both ways and comparing against the doc resolves the ordering question in seconds without hand-drawing bit tables.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/basenc.1.en.html)
