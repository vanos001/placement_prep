# base64 — binary-to-text encoder (RFC 4648 base64, 33% overhead)

## Overview

`base64` encodes binary data as printable ASCII using the 64-character alphabet `A–Z`, `a–z`, `0–9`, `+`, `/` with `=` padding, and decodes such data back to bytes. It is the workhorse binary-to-text transform on Linux: mail attachments (MIME), embedded credentials in HTTP `Authorization: Basic` headers, PEM certificates, JWT segments, Kubernetes secrets, and copy-paste transfer of binary blobs through text channels all use this exact encoding.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/base64`, from upstream GNU coreutils. It is one of the most frequently used tools in shell glue and one of the most frequently misused: people reach for it to "encode" passwords thinking of it as security, or expect it to produce URL-safe output (it does not — see `basenc --base64url`).

Compared to `base32` it is one-third more compact (4 output chars per 3 input bytes, +33% expansion) at the cost of a case-sensitive, URL-hostile alphabet. It is often confused with `openssl base64` (same format, different tool with its own flag set) and with the `base64` subcommand found in Python, Perl, and `openssl enc -base64`.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/base64` |
| First appeared / lineage | GNU textutils/coreutils lineage (GNU `base64` added 2002, coreutils 5.0 era); encoding itself from PEM/MIME (RFC 1421 → RFC 4648) |
| Standards | RFC 4648 section 4; not in POSIX |

## Synopsis

```
base64 [OPTION]... [FILE]
```

Main forms:

```
base64 file.bin             # encode a file, wrapped at 76 columns
base64 -w 0 file.bin        # encode as a single line
base64 -d encoded.txt       # decode a file back to binary
base64 -d -i dirty.txt      # decode, tolerating junk between alphabet chars
```

With no FILE, or when FILE is `-`, input is read from standard input. Output goes to standard output.

## How It Works

### The 3-to-4 bit remap

base64 consumes groups of 3 bytes (24 bits) and re-splits them into four 6-bit values (0–63). Each value indexes one character of the alphabet `ABC...XYZabc...xyz0123456789+/`:

```
Input: "foobarbaz" = 9 bytes = 3 exact groups of 3

Group 1: 'f','o','o' = 66 6F 6F
Bits:  01100110 01101111 01101111
6-bit:  011001 100110 111101 101111
Value:     25     38     61     47
Char:       Z      m      9      v

$ printf 'foobarbaz' | base64 -w 0
Zm9vYmFyYmF6
```

### Padding rules

A partial final group is padded with `=` to a 4-character boundary. The padding count tells the decoder how many trailing bits to discard:

| Leftover bytes | Output chars | Padding |
|---|---|---|
| 0 | 0 | none |
| 1 | 2 | `==` |
| 2 | 3 | `=` |

```
$ printf 'foobar' | base64 -w 6   # 6 bytes = foob | ar
Zm9vYm
Fy
$ printf 'a' | base64             # 1 leftover byte
YQ==
```

### Line wrapping

The default output wraps at 76 columns — the MIME convention. `-w 0` disables wrapping (common when the output goes into a JSON field, a URL parameter, or a single-line config value). Wrapping is purely cosmetic: the decoder accepts newlines anywhere between alphabet characters.

### Decoding and error handling

`-d` decodes. The decoder's tolerance is a common interview topic:

- Newlines are always accepted (the encoder itself emits them).
- Any other non-alphabet byte (`space`, tab, `-`, `_`, BOM, CR) is fatal by default — exit 1, message `invalid input`.
- `-i` / `--ignore-garbage` silently discards such bytes. This "recovers" data from transports that mangle whitespace, but it also silently corrupts output when the mistake is something meaningful.

```
$ printf 'aGVs bG8=\n' | base64 -d      # space inside the stream
base64: invalid input
$ printf 'aGVs bG8=\n' | base64 -di
hello
```

```
$ printf '\x00\x01\x02' | base64        # binary in
AAEC
$ printf 'AAEC' | base64 -d | od -An -tx1   # binary out
 00 01 02
```

```
┌─────────────┐  groups of 3   ┌──────────────┐  alphabet      ┌────────────┐
│ raw bytes   │ ─────────────> │ 4×6-bit idx  │ ─────────────> │ A-Za-z0-9+/│
└─────────────┘                └──────────────┘                └─────┬──────┘
                                                                     │ + '=' pad
                                                                     v
                                                        wrap at 76 (-w 0 to stop)
```

### Why there is no URL-safe flag in this tool

RFC 4648 also defines a URL- and filename-safe alphabet where `+` becomes `-` and `/` becomes `_`. GNU `base64` deliberately implements only the standard alphabet; if you need the safe variant you must use `basenc --base64url` (or `openssl base64` plus `tr '+/' '-_'`). This is a recurring trap when people paste base64 into URLs and discover `+` decodes as a space server-side.

## Options That Matter

| Option | Effect |
|---|---|
| `-d`, `--decode` | Decode input instead of encoding |
| `-i`, `--ignore-garbage` | When decoding, discard non-alphabet characters instead of aborting |
| `-w`, `--wrap=COLS` | Wrap encoded output after COLS chars; `0` disables wrapping (default 76) |
| `--help`, `--version` | Self-explanatory |

Note the flag set is smaller than `base32`'s (no `-z` NUL-line option here) and smaller than `basenc`'s (no alphabet selection). Every base64 operation is also expressible as `basenc --base64` / `basenc --base64url`; the standalone tool exists for muscle memory and POSIX-era scripting habits.

## Usage Patterns

```bash
# Encode a short string on one line (the config-file idiom)
printf 'user:password' | base64 -w 0
# dXNlcjpwYXNzd29yZA==
```

```bash
# Build an HTTP Basic auth header without extra tools
printf 'Authorization: Basic %s\n' "$(printf 'user:password' | base64)"
```

```bash
# Decode back and prove the round trip
printf 'user:password' | base64 | base64 -d
# user:password
```

```bash
# Copy a small binary through a text-only channel (chat, ticket, paste)
base64 -w 76 < photo.jpg > photo.b64     # send photo.b64
base64 -d photo.b64 > photo.jpg          # on the receiving side
```

```bash
# Decode data pasted with junk (indentation, tabs, CR-LF) - best effort
base64 -di < pasted.txt > recovered.bin
```

```bash
# Embed a binary payload inside a shell script heredoc
{ echo "PAYLOAD_B64:"; base64 -w 0 payload.tar.gz; } > installer.sh
```

```bash
# Single-line SHA-256 digest in base64 (common in container image specs)
printf '%s' "$(sha256sum file.iso | cut -d' ' -f1)" | xxd -r -p | base64 -w 0
```

```bash
# Generate a 24-character random token from 18 bytes of entropy
head -c 18 /dev/urandom | base64 | tr '+/' 'A_'    # keep it shell-safe
```

```bash
# Show exactly where + and / hurt: encode a value containing both
printf 'a+b/c?' | base64        # YStiL2M/
printf 'a+b/c?' | basenc --base64url   # YStiL2M_  (same bits, safe alphabet)
```

## Nuances and Gotchas

- **Encoding is not encryption.** `base64 -w0 "$PASSWORD"` in scripts exposes the password to anyone who can read the script, the process list (`ps -ef` shows arguments), or the output. Real secret handling needs key material (see the collection overview for crypto tools).
- **`printf`, not `echo`, for strings with trailing data.** `echo "user:pass" | base64` includes the newline in the input (18 bytes → different output than 17 bytes). The classic debugging session "why is my token different on each host" is an `echo -n` missing somewhere.
- **No URL-safe mode.** `+`, `/`, and `=` all break URLs and path segments. `basenc --base64url` exists precisely for this; the standalone `base64` will never produce it.
- **`-i` hides corruption.** Decoding with `--ignore-garbage` can succeed while producing different bytes than the original. Never use it in verification paths; use it only for scraping base64 out of messy text.
- **Whitespace sensitivity differs between implementations.** GNU tolerates newlines only; some other implementations (openssl's, various libraries) tolerate more whitespace or none. Piping GNU-encoded output with `-w 76` into a strict consumer is the usual interop failure.
- **Trailing padding is optional for some consumers, never for GNU.** Unpadded base64 (common in JWT: `eyJhbGci...` segments) fails GNU `base64 -d` unless you re-add `=` padding to a multiple of 4. `base64 -d` on a JWT segment is a well-known one-liner that needs `tr`/`sed` fixing first.
- **Size math**: 4 chars per 3 bytes plus padding — `ceil(N/3)*4` characters. Count line breaks when `-w` is on. A 1 MiB file becomes ~1.37 MiB of text.
- **Newlines in `-w` output are real characters.** Tools that checksum the encoded output see different bytes for `-w 0` versus `-w 76` runs of the same input.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Encode or decode completed successfully |
| 1 | Invalid input, unreadable file, or write error |

## Related Commands

- [`base32`](./base32.md) — same RFC, case-insensitive alphabet, 60% overhead instead of 33%.
- [`basenc`](./basenc.md) — the unified encoder; adds `--base64url`, base32hex, base16, base2, z85.
- [`cat`](./cat.md) — often seen pointlessly wrapped around files before `base64`; see the discussion there.
- [`cksum`](./cksum.md) — checksum family for verifying what you just encoded.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why does base64 output often end in one or two '=' characters?

The encoding processes 3 bytes into 4 characters. When the input length is not a multiple of 3, the final group has 1 or 2 leftover bytes producing 2 or 3 data characters; `=` fills the remaining slots so the total length is a multiple of 4. The padding count also encodes how many unused bits to discard, making the transform exactly reversible.

### Q: What happens if you pipe a 76-column-wrapped base64 file into a service expecting single-line tokens?

The service sees the newlines as either invalid characters or (worse, if it tolerates whitespace) as part of a different token. Regenerate with `base64 -w 0`, or strip newlines with `tr -d '\n'` before sending. The reverse failure also happens: single-line input into a consumer whose parser expects MIME wrapping — rare, since GNU decode accepts unwrapped input fine.

### Q: Is `base64 -d` on this output safe: `echo "$USER_INPUT" | base64 -d > /tmp/f`?

Mostly, but two traps: first, `-d` without `-i` exits 1 on any stray character, so `/tmp/f` may be empty or partial — check the exit code. Second, base64 decoding is a pure data transform; if `$USER_INPUT` is attacker-controlled, the output bytes can be anything (including a shell script someone will later execute from `/tmp/f`). The encoding neither sanitizes nor authenticates.

### Q: How would you decode a JWT payload segment with coreutils only?

JWT segments are unpadded URL-safe base64. Steps: take the middle segment, translate `-`→`+` and `_`→`/` with `tr '_-' '/+'`, append `=` until length is a multiple of 4, then `base64 -d`. One-liner: `sed 's/-/+/g; s/_/\//g' <<< "$seg" | awk '{l=length($0); printf "%s%*s", $0, (4-l%4)%4}' | base64 -d`. Knowing why each step exists (alphabet, padding) is the interview point.

### Q: A teammate says "we base64 the API key so it's not stored in plaintext" — evaluate.

base64 is trivially reversible with no key; it obfuscates against shoulder-surfing at best and adds a decode step. Real protection requires a secrets manager, encrypted storage, or at minimum filesystem permissions — plus not passing the value as a process argument where `ps` reveals it. The claim confuses encoding (format conversion) with encryption (confidentiality).

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/base64.1.en.html)
