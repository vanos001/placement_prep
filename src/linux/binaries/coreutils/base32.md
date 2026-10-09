# base32 — binary-to-text encoder using the RFC 4648 32-character alphabet

## Overview

`base32` encodes arbitrary binary data as printable ASCII text and decodes it back. It is the little sibling of `base64`: the alphabet is the 32 uppercase letters `A–Z` plus the digits `2–7`, chosen by RFC 4648 so that encoded output is case-insensitive-safe, contains no visually ambiguous characters (`0`, `1`, `8`, `9` are absent), and survives channels that mangle case, spaces, or line wrapping.

On Debian and Ubuntu the binary ships in the `coreutils` package (the same package that provides `ls`, `cat`, `head`), is installed at `/usr/bin/base32`, and comes from upstream GNU coreutils. On minimal containers without coreutils (distroless-style images) it is absent, which surprises people who treat it as "always there".

Reach for `base32` when the transport is case-insensitive or human-transcribed — hostnames, DNS-adjacent contexts, printed handout codes, systems that uppercase everything. When bandwidth matters more than transcription safety, use `base64` instead: base32 expands data by 60% (8 output chars per 5 input bytes) versus base64's 33%. It is frequently confused with `base64` (different alphabet, different expansion) and with `basenc` (the unified encoder that subsumes it).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/base32` |
| First appeared / lineage | GNU coreutils 5.3.0 (2004), inspired by RFC 3548 (now RFC 4648) |
| Standards | RFC 4648 base 32 encoding; not in POSIX |

## Synopsis

```
base32 [OPTION]... [FILE]
```

Main forms:

```
base32 file.bin              # encode a file
base32 < file.bin            # encode stdin
base32 -d encoded.txt        # decode a file back to binary
base32 -w 0 file.bin         # encode, no line wrapping
```

With no FILE, or when FILE is `-`, input is read from standard input. Output goes to standard output.

## How It Works

### The 5-to-8 bit remap

base32 works on groups of 5 input bytes (40 bits), which it splits into eight 5-bit values. Each 5-bit value (0–31) indexes one character of the alphabet `ABCDEFGHIJKLMNOPQRSTUVWXYZ234567`:

```
Input:  "foobar" = bytes 66 6F 6F 62 61 72  (hex)

Group of 5 bytes: 66 6F 6F 62 61
Bits:  01100110 01101111 01101111 01100010 01100001
Split into 5-bit chunks:
       01100 11001 10111 10110 11110 11000 10011 00001
Value:   12    25    23    22    30    24    19     1
Char:     M     Z     X     W     6     Y     T     B

$ printf 'fooba' | base32
MZXW6YTB
```

### Padding rules

Input is rarely an exact multiple of 5 bytes. The final partial group is padded with `=` characters to a multiple of 8 output characters:

| Leftover bytes | Output chars | Padding |
|---|---|---|
| 0 | 0 | none |
| 1 | 2 | `======` (6) |
| 2 | 4 | `====` (4) |
| 3 | 5 | `===` (3) |
| 4 | 7 | `=` (1) |

```
$ printf 'foobar' | base32      # 6 bytes = one full group + 1 leftover
MZXW6YTBOI======                # 8 chars for 'fooba', then 'OI' + 6 '='
```

Encoding is deterministic and reversible: the decoder uses the padding length to reconstruct exactly how many trailing bits to discard.

### Line wrapping

Encoded output is wrapped at 76 columns by default (RFC 4648 recommends this so encoders remain compatible with mail-era transports). `base64 -w`-style control applies here too: `-w 0` disables wrapping entirely, producing one long line. Decoding always accepts arbitrary newlines between characters regardless of how the data was wrapped.

### Decoding

`-d` reverses the process. The decoder tolerates newlines inside the input (since the encoder produces them) but rejects every other non-alphabet character; `--ignore-garbage` drops other stray bytes instead of failing:

```
$ printf 'aGVsbG8=\n' | base32 -d 2>/dev/null; echo "rc=$?"   # base64 input into base32
rc=1                                                          # wrong alphabet -> error
$ printf 'foobar' | base32 | base32 -d
foobar
```

```
┌──────────────┐   groups of 5    ┌───────────────┐
│ raw bytes    │ ───────────────> │ 8×5-bit index │
│ (file/stdin) │                  └──────┬────────┘
└──────────────┘                         │ alphabet[A-Z2-7]
                                         v
                               ┌──────────────────┐
                               │ chars + '=' pad  │
                               │ wrapped at 76    │
                               └──────────────────┘
```

## Options That Matter

| Option | Effect |
|---|---|
| `-d`, `--decode` | Decode input instead of encoding |
| `-i`, `--ignore-garbage` | When decoding, discard non-alphabet characters instead of aborting |
| `-w`, `--wrap=COLS` | Wrap encoded output after COLS chars; `0` disables wrapping (default 76) |
| `-z`, `--zero` | Terminate output lines with NUL instead of newline |
| `--help`, `--version` | Self-explanatory |

There is no "URL-safe" base32 flag here: the base32 alphabet already contains no `+` or `/`, so it is URL- and filename-safe by construction. The extended-hex variant (`0–9`, `A–V`, useful for case-insensitive hex-like sorting) lives in `basenc --base32hex`.

## Usage Patterns

```bash
# Encode a file and inspect it
base32 /etc/hostname
```

```bash
# Encode a short string with no trailing wrap (one line out)
printf 'secret-seed' | base32 -w 0
# ONSWG4TFOQWXGZLFMQ======
```

```bash
# Decode back to binary and verify round-trip
printf 'secret-seed' | base32 | base32 -d
# secret-seed
```

```bash
# Decode data with junk lines around it (e.g. pasted from a mail client)
base32 -i -d < mail-attachment.txt > payload.bin
```

```bash
# Produce a compact single-line shareable checksum of a file
sha256sum image.iso | cut -d' ' -f1 | xxd -r -p | base32 -w 0
```

```bash
# Keep a wrapped copy exactly as RFC 4648 recommends (76 columns)
base32 seed.bin > seed.b32
```

```bash
# Compare expansion: base32 grows data 60%, base64 grows it 33%
ls -l /etc/hostname
base32 < /etc/hostname | wc -c
base64 < /etc/hostname | wc -c
```

```bash
# Sort base32 strings: uppercase alphabet sorts lexicographically by design
printf 'MZXW6YTB\nMZXW6YQ=\n' | LC_ALL=C sort
```

```bash
# Generate a human-transcribable 20-byte token (no 0/1/8/9 ambiguity)
head -c 20 /dev/urandom | base32 -w 0
# e.g. R7GFKM2QXC4YJVNJ3TBQJZK5NU======
```

## Nuances and Gotchas

- **60% size overhead is real.** Every byte of input costs 1.6 bytes of output (before newlines). For large payloads piped through mail or URLs this is a measurable regression versus base64's 1.33×.
- **It is not encryption.** base32 is a reversible encoding with no key. Interviewers occasionally probe whether "base32-encoding secrets" hides anything — it does not.
- **Wrong-alphabet input fails with exit 1.** Piping base64 data into `base32 -d` (or vice versa) errors out; the alphabets share no usable mapping. With `-i` the decoder silently drops offending characters, which can mask the mistake and "successfully" produce garbage.
- **`-i` is a data-loss switch.** `--ignore-garbage` deletes everything that is not alphabet or newline. Use it only for recovery from known-dirty transports, never on data whose integrity you need.
- **Padding is part of the format.** Some hand-rolled decoders (and some protocols) strip or forbid the `=` padding. GNU `base32 -d` requires correct padding; trimming it manually breaks decode.
- **Portability.** `base32` is present in GNU coreutils and BusyBox, but historically missing from BSD/macOS toolsets (macOS only gained a `base32` recently, and it is not the GNU one — flags like `-w 0` may differ). In scripts that must run anywhere, check availability or fall back to `basenc`.
- **Newlines count as data only when decoding.** The decoder skips newlines; every other whitespace character (space, tab) is "garbage" and needs `-i`. Data pasted from column-oriented sources usually trips on this.
- **`-w 0` output has no trailing newline** beyond the data itself — an encoded stream not ending in `\n` can confuse naive `while read` loops downstream.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Encode or decode completed successfully |
| 1 | Invalid input (bad alphabet, bad padding), unreadable file, or write error |

## Related Commands

- [`base64`](./base64.md) — the standard 33%-overhead encoder; the default choice unless case-insensitivity is required.
- [`basenc`](./basenc.md) — unified encoder exposing base32 plus base32hex, base16, base2, z85 in one binary.
- [`basenc --base16`](./basenc.md) — hex encoding without leaving the base family.
- [`cksum`](./cksum.md) — checksums; combine with base encoders when embedding digests in text protocols.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why does base32 exist when base64 is more compact?

Because some transports are case-insensitive or hostile to mixed-case data. base32's alphabet is all uppercase letters plus digits 2–7, so encoding survives DNS-label handling, systems that uppercase input, and human transcription. The 0/1/8/9 exclusion also removes glyph ambiguity in handwriting and some fonts. The trade is deliberate: 60% expansion for robustness.

### Q: How many output characters does encoding N bytes produce?

Group math: 8 characters per 5 bytes, plus padding to the next multiple of 8 for the final partial group. So the length is `ceil(N/5)*8` characters: 6 bytes → `ceil(6/5)=2` groups → 16 chars (`MZXW6YTBOI======`); 5 bytes → 8 chars with no padding at all. With `-w 0` no newlines are added; otherwise count line breaks too.

### Q: A script decodes a config value with `base32 -d` and works on one host, fails on another with "invalid input". Diagnose.

First compare the input bytes (`cat -A` on the input) — trailing whitespace, CR-LF, or a UTF-8 BOM would put non-alphabet bytes in the stream. GNU base32 skips newlines only; a `\r` or space makes it exit 1 unless `-i` is used. Second, check that both hosts run the same tool: a BSD/macOS `base32` or busybox variant may have different padding strictness. The portable fix is normalizing the input (`tr -d ' \r'`) before decode or adding `-i` where data loss is acceptable.

### Q: Why did the RFC authors exclude 0, 1, 8, 9 from the alphabet instead of just using 0–9?

The alphabet must have exactly 32 characters (5 bits each). Digits 0–9 plus 26 letters is 36; four characters must go. Removing 0, 1, 8, 9 (the most confusable glyphs in print and handwriting) leaves 32 and makes base32 friendly to human transcription — the same reasoning that shaped earlier encodings for serial numbers and license keys.

### Q: Is base32 output a valid filename component? Why?

Yes — it contains only `A–Z`, `2–7`, `=`, and (if wrapped) newlines. No `/`, no NUL, no spaces. Base64 needs a URL-safe variant (`-` and `_` substituting `+` and `/`) to be filename-safe; base32 needs nothing. That is why tools that derive filesystem-safe names from binary hashes often use base32 (or base32hex) rather than base64.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/base32.1.en.html)
