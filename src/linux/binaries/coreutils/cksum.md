# cksum — checksums and CRCs: POSIX CRC plus the modern digest front-end

## Overview

`cksum` computes checksums of files or stdin and prints them with the input length. Historically it is the POSIX-specified CRC-32 utility — the tool behind the famous `4294967295 0` output for an empty file. In recent GNU coreutils (9.x era) it was promoted to the *family front-end*: `-a` selects the algorithm, and `cksum -a md5`, `-a sha256`, `-a blake2b`, `-a sm3` and friends now subsume what used to require separate binaries (`md5sum`, `sha256sum`, `b2sum`).

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/cksum`, from upstream GNU coreutils. Default (no flags) behavior remains byte-for-byte the POSIX CRC: `CRC length filename`.

You reach for it when you need a quick integrity fingerprint without picking a digest tool, when a spec or exam question says "POSIX CRC", or when you want one tool that speaks every checksum format. It is often confused with `sum` (the older BSD/System V checksums, now `cksum -a sysv` / `-a bsd`), with `md5sum`/`sha256sum` (the dedicated digest binaries), and with `crc32`-style tools — whose output is *not* the same as cksum's despite the shared polynomial.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/cksum` |
| First appeared / lineage | 4.4BSD-era `cksum` (1990), standardized by POSIX.2; `-a` digest selection added in recent GNU coreutils |
| Standards | POSIX.1-2018 (`cksum` default CRC); digest modes are GNU extensions |

## Synopsis

```
cksum [OPTION]... [FILE]...
```

Main forms:

```
cksum file                     # POSIX CRC-32 + length
cksum -a sha256 file           # SHA-256, tagged output
cksum --untagged -a md5 file   # md5sum-style output
cksum -c sums.txt              # verify checksums written by cksum/digest tools
cksum -a crc32b < archive.bin  # reflected CRC-32 (zlib/gzip compatible value)
```

With no FILE, or when FILE is `-`, input is read from standard input.

## How It Works

### The POSIX CRC-32, precisely

The default algorithm is fixed by POSIX: a CRC with polynomial `0x04C11DB7`, processed bit by bit most-significant-bit first, initial value 0, with the final register complemented. The length of the input (in bytes) is fed into the CRC calculation after the data, as most-significant-octet-first octets, so the length participates in the fingerprint — which is why the output always ends in a length field, and why two different-length files rarely collide by accident.

```
$ printf 'foobar' | cksum
2606601686 6
$ printf '' | cksum
4294967295 0      # empty input: complement of the initial register
```

A nuance interviewers like: this is **not** the same CRC-32 that `gzip` or zlib produce, even though both use polynomial `0x04C11DB7`. zlib's CRC-32 (used in gzip, PNG, zip) is the *reflected* variant with a different initialization (`0xFFFFFFFF`) and final XOR. Same polynomial, different bit plumbing, entirely different numbers. coreutils exposes the zlib-compatible value as `cksum -a crc32b`, and the classic POSIX one as `crc` (or default).

```
$ printf 'x' | cksum            # POSIX CRC
12738659 1
$ printf 'x' | cksum -a crc32b  # reflected/zlib-compatible CRC
2363233923 1
```

### From CRC to the digest family

`-a` selects an algorithm; the output is a BSD-style tagged line by default:

```
$ cksum -a sha256 /etc/hostname
SHA256 (/etc/hostname) = ecdf9139c2caaa34b6572db508dc346de765e0f8a1943dd57257e28e339b645e
$ cksum -a sha256 --untagged /etc/hostname
ecdf9139c2caaa34b6572db508dc346de765e0f8a1943dd57257e28e339b645e  /etc/hostname
```

The full menu in recent GNU coreutils: `sysv` and `bsd` (the old `sum` algorithms), `crc` (default), `crc32b`, `md5`, `sha1`, `sha224`, `sha256`, `sha384`, `sha512`, `blake2b` (with `-l` to pick the digest length), and `sm3`. Equivalences are documented: `sysv` = `sum -s`, `bsd` = `sum -r`, `md5` = `md5sum`, `sha256` = `sha256sum`, and so on — `cksum` is the superset command.

### Check mode (digest algorithms only)

`-c` reads checksum lines and verifies the referenced files. It understands tagged formats from `cksum` and the digest utilities:

```
$ cksum -a sha256 file.iso > file.sha256
$ cksum -c file.sha256
file.iso: OK
```

Two important limits discovered by experiment:

- **CRC-family algorithms cannot be checked.** `cksum -c` on a classic `2606601686 6`-style line fails with `no properly formatted checksum lines found`; explicitly, the tool refuses: `--check is not supported with --algorithm={bsd,sysv,crc,crc32b}`. Store CRC outputs for eyeball comparison or `awk` comparison, not for `-c`.
- **`md5sum`-style untagged lines are rejected by cksum -c** but accepted by `md5sum -c`; tagged lines (`MD5 (file) = ...`) are accepted. When generating lists for cross-tool verification, generate them tagged (`cksum --tag` / the digest tools' `--tag`) or use each tool's own `-c`.

```
┌─────────────┐  -a sysv / -a bsd    ┌────────────────────┐
│  cksum      │ ───────────────────> │ sum-compat values  │
│  (front-end)│  -a crc / crc32b     │ POSIX / zlib CRC   │
│             │  -a md5..sha512      │ digest family      │
│             │  -a blake2b -l N     │ variable-length    │
│             │  -a sm3              │ Chinese standard   │
└─────────────┘                      └────────────────────┘
        │  -c verifies tagged lines (digest modes only)
        v
   file.iso: OK / FAILED / no such file
```

## Options That Matter

| Option | Effect |
|---|---|
| `-a`, `--algorithm=TYPE` | Select algorithm: `sysv`, `bsd`, `crc`, `crc32b`, `md5`, `sha1`, `sha224`, `sha256`, `sha384`, `sha512`, `blake2b`, `sm3` |
| `-c`, `--check` | Verify checksums from FILEs (digest algorithms only) |
| `-l`, `--length=BITS` | Digest length in bits (for `blake2b`; multiple of 8, ≤ max) |
| `--tag` / `--untagged` | BSD-style `ALGO (name) = hex` output / reversed `hex  name` output |
| `--raw` | Emit the raw binary digest instead of hex |
| `--base64` | Emit base64-encoded digest instead of hex |
| `-z`, `--zero` | NUL-terminate lines (safe for filenames with newlines) |
| `--ignore-missing`, `--quiet`, `--status`, `--strict`, `-w` | Verify-mode refinements: skip missing files, suppress OK lines, print nothing, fail on malformed lines, warn about malformed lines |

## Usage Patterns

```bash
# Quick integrity check of a download (the classic form)
cksum debian-12.5.0-amd64-netinst.iso
# 1848441598 632291328 debian-12.5.0-amd64-netinst.iso
```

```bash
# Compare two directory trees' contents by fingerprint
find . -type f -exec cksum {} + | sort -k3 > /tmp/tree-a.cks
```

```bash
# Modern: one tool, any digest, tagged lines ready for -c
cksum -a sha256 *.tar.zst > SHA256SUMS
cksum -c SHA256SUMS
```

```bash
# Produce md5sum-compatible output from cksum
cksum -a md5 --untagged file > file.md5
md5sum -c file.md5
```

```bash
# CRC of a file in the zlib/gzip sense (matches python zlib.crc32)
cksum -a crc32b < payload.bin
```

```bash
# Variable-length BLAKE2b digest (256-bit) via the -l knob
cksum -a blake2b -l 256 file
```

```bash
# Verify a manifest but skip files you deleted on purpose
cksum -c --ignore-missing SHA256SUMS
```

```bash
# Silent verification in scripts - exit code is the answer
cksum --status -c SHA256SUMS && echo "all good" || echo "corrupt"
```

```bash
# Digest of a stream (no temp file): checksum exactly what will be sent
tar -c dir | cksum -a sha256
```

```bash
# Feed a checksum into a text protocol safely
cksum -a sha256 --base64 key.bin
```

## Nuances and Gotchas

- **cksum's CRC ≠ zlib's CRC ≠ `sum`'s output.** Same polynomial for the first two, different bit order and initialization; different algorithm entirely for `sum`. Cross-checking files between tools (`cksum` vs a Python `zlib.crc32`) fails by design — match the algorithm: `cksum -a crc32b` equals `zlib.crc32`.
- **`-c` cannot verify CRC lines.** Check mode works for digest algorithms only; feeding it classic cksum output yields `no properly formatted checksum lines found`. This surprises people who assumed symmetry between compute and verify.
- **Untagged digest output looks like `md5sum` but the toolset is picky.** `cksum -c` rejects untagged md5 lines while `md5sum -c` accepts them. Use tagged output (`--tag`, now the default for cksum) for anything that will be machine-verified later.
- **CRC-32 is not tamper-resistant.** It detects accidental corruption. An adversary can forge a CRC collision trivially (it's linear); SHA-256 or BLAKE2b are the minimum for adversarial settings. Saying "cksum is a security tool" in an interview is the trap.
- **The length is part of the CRC input** in POSIX mode — that's why the second field exists and why you cannot "fix up" a mismatching length separately from the checksum.
- **`--untagged` and `-z` interact with filenames.** Filenames containing spaces/newlines break space-separated parsing; use `-z` (NUL-terminated) plus `xargs -0` for hostile names.
- **Empty input edge case:** `printf '' | cksum` prints `4294967295 0` — the complement of the initial register. Not a bug; a common "is my tool broken" question on forums.
- **Portability:** POSIX guarantees only the default CRC behavior and the `cksum` name; `-a`, `--tag`, `--raw`, `-c` are GNU extensions absent in busybox/older BSD cksum. Scripts depending on `-a sha256` should check support or call `sha256sum` directly.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Success: all files processed (or, with `-c`, all lines verified OK) |
| 1 | Failure: unreadable file, malformed checksum line, or at least one verification mismatch |

## Related Commands

- [`md5sum`](./md5sum.md) — the dedicated MD5 tool; `cksum -a md5` is its superset equivalent.
- [`sha256sum`](./sha256sum.md) — the dedicated SHA-256 tool and the de-facto standard for release manifests.
- [`sum`](./sum.md) — the legacy BSD/System V checksums, preserved as `cksum -a bsd` / `cksum -a sysv`.
- [`base64`](./base64.md) — encode digests or files when the checksum travels through a text channel.
- [`b2sum`](./overview.md) — standalone BLAKE2b tool (see the collection overview).
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: What exactly does `cksum` compute by default, and what is special about the length in the output?

A POSIX-specified CRC-32: polynomial 0x04C11DB7, MSB-first processing, zero initial value, complemented final register — with the file's byte length folded into the CRC as trailing big-endian octets. The printed second field is that length, which is why `printf '' | cksum` yields `4294967295 0` (complement of the initial register, zero bytes) and why two files with the same bytes but different lengths cannot share a cksum value.

### Q: A teammate compares `cksum` output against Python's `zlib.crc32` and the values never match. Why?

They are different CRC-32 variants sharing one polynomial. POSIX cksum's CRC is non-reflected, initialized to zero, final complement, plus the length folded in. zlib's is the reflected variant (init 0xFFFFFFFF, final XOR) without the length term. `cksum -a crc32b` produces the zlib-compatible value. The fix is matching algorithms, not hunting for a bug.

### Q: Why does `cksum -c` reject a checksum file created by plain `cksum file > sums.txt`?

Because check mode only supports the digest algorithms; the CRC family (sysv, bsd, crc, crc32b) has no check implementation, and the classic two-field `crc bytes name` line is not one of the tagged formats `-c` parses. Recent coreutils make this explicit: `--check is not supported with --algorithm={bsd,sysv,crc,crc32b}`. If you want verifiable manifests, generate them with a digest algorithm (`cksum -a sha256`) or the dedicated `sha256sum`.

### Q: You need to verify 10,000 files nightly where three may legitimately be absent. Design the command.

Generate a tagged manifest (`cksum -a sha256 --tag * > SHA256SUMS`), then run `cksum -c --ignore-missing SHA256SUMS` and inspect the exit code (0 = all present files verified; 1 = any failure), optionally with `--quiet` to reduce log volume. `--ignore-missing` prevents absent files from being reported as errors while still verifying everything present — the combination that distinguishes "planned absence" from corruption.

### Q: When would you choose CRC over SHA-256, and vice versa?

CRC for speed and accidental-error detection: it's a few instructions per byte in hardware terms, ideal for link-layer checks, quick diff-by-fingerprint, and non-adversarial integrity. SHA-256/BLAKE2b when the threat model includes deliberate tampering — CRC is linear and trivially forgeable, so it provides zero security. The classic wrong answer is using CRC to verify a downloaded binary from an untrusted mirror: the attacker just recomputes it.

### Q: What changed recently in GNU coreutils regarding cksum, and why does it matter for scripts?

`cksum` gained `-a` (algorithm selection), `--tag`/`--untagged`, `--raw`, `--base64`, and `-c` — effectively becoming the front-end for the whole digest family. Scripts can target one binary instead of md5sum/sha256sum/b2sum variants; but the features are GNU extensions, so portable scripts should either verify availability or keep calling the standalone digest tools, which are the portable subset with their own well-known output formats.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/cksum.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
